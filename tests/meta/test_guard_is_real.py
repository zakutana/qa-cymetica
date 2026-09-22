"""Proof that the safety guard blocks.

These run first and abort the session on failure. If the guard cannot be shown
to stop a SAFE POST, a probe carrying executable parameters, and an ungated
MUTATE, then zero live requests are issued for the rest of the run.

Every test here asserts a REFUSAL, and nothing in this file reaches the
network -- not because the violation is raised before the transport delegates,
which is only true while the guard works, but because the transport underneath
these clients cannot carry a request at all. That distinction was not academic:
mutating the probe_only floor off, to check this suite could feel it, sent a
real POST to /api/v1/funding/withdraw.
"""

from __future__ import annotations

from contextlib import contextmanager

import httpx
import pytest

from qa.client import build_client, build_mcp_client
from qa.config import Identity
from qa.marks import qa
from qa.safety import (
    CURRENT_TIER,
    EndpointRegistry,
    SafetyTier,
    SafetyTransport,
    SafetyViolation,
)

ANON = Identity(name="anon")


# ---------------------------------------------------------------------------
# Layer 1 -- client construction is banned outside our factories
# ---------------------------------------------------------------------------
@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_direct_httpx_client_is_forbidden():
    with pytest.raises(SafetyViolation, match="Direct httpx.Client construction"):
        httpx.Client()


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_direct_async_client_is_forbidden():
    with pytest.raises(SafetyViolation, match="Direct httpx.AsyncClient construction"):
        httpx.AsyncClient()


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_requests_session_is_forbidden():
    requests = pytest.importorskip("requests")
    with pytest.raises(SafetyViolation, match="requests.Session is forbidden"):
        requests.Session()


# ---------------------------------------------------------------------------
# Every negative control below asks the guard to refuse something, and until
# 2026-09-06 its only protection against actually DOING that thing was the
# code it was testing. Mutating the probe_only floor off, to check this suite
# could feel it, sent a real POST to /api/v1/funding/withdraw with
# {"amount": "1"}. It came back 401 because the client was anonymous, and
# nothing moved -- but it left, and the list these tests iterate also holds
# deposit, register and prop/signup.
#
# So they carry a transport that refuses to carry anything. Guard correct: the
# SafetyViolation is raised before the transport is ever reached and the test
# passes exactly as it did. Guard broken: the request dies here with a
# distinctive error, the test fails, and nothing leaves the machine. A
# negative control must not depend on the thing it is controlling for.
# ---------------------------------------------------------------------------
class _Unsendable(httpx.BaseTransport):
    """Carries nothing. Reaching it means the guard let something through."""

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        raise AssertionError(
            f"THE GUARD LET IT THROUGH: {request.method} {request.url} would "
            f"have gone to the live platform. Nothing was sent."
        )


def _deaf_client(evidence_store=None, **kwargs):
    registry = kwargs.pop("registry", None) or EndpointRegistry.load()
    return build_client(ANON, registry, evidence_store,
                        inner=_Unsendable(), **kwargs)


def _deaf_mcp_client(registry=None, evidence_store=None):
    """The same deafness for the MCP controls, which did not have it.

    The 2026-09-06 remediation stopped at `_deaf_client`, so the four MCP
    negative controls below kept performing `tools/call` on a live transport --
    including one that sets `mutate_enabled` and raises the tier to MUTATE
    before asking the guard to refuse `place_order`. The refusal was the only
    thing between the test and a real order. That is the shape the whole file
    exists to rule out, and it survived here for a day because the constructor
    took no `inner`.
    """
    return build_mcp_client(ANON, registry or EndpointRegistry.load(),
                            evidence_store, inner=_Unsendable())


# ---------------------------------------------------------------------------
# Layer 2 -- the transport enforces the tier of the running test
# ---------------------------------------------------------------------------
@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_safe_tier_blocks_post(evidence_store):
    client = _deaf_client(evidence_store)
    try:
        with pytest.raises(SafetyViolation, match="SAFE test attempted POST"):
            client.post("/api/v1/clob/orders", json={})
    finally:
        client.close()


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_safe_tier_blocks_withdraw_entirely(evidence_store):
    client = _deaf_client(evidence_store)
    try:
        with pytest.raises(SafetyViolation, match="SAFE test attempted POST"):
            client.post("/api/v1/funding/withdraw", json={})
    finally:
        client.close()


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_unknown_write_path_is_default_denied(evidence_store):
    client = _deaf_client(evidence_store)
    try:
        with pytest.raises(SafetyViolation, match="matches no rule in components.yaml"):
            client.post("/api/v1/some/undeclared/endpoint", json={})
    finally:
        client.close()


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_the_fingerprint_client_is_wrapped_and_keeps_the_corpus_shape():
    """The session's own reads go through the guard, and unchanged.

    `qa/fingerprint.py` built its own client with the guard's private
    sentinel until 2026-09-20, so the corpus was read every session with no
    SafetyTransport under it -- the one thing the guard's refusal message
    forbids. `build_fingerprint_client` closed that, and this proves the
    transport is really underneath: with no tier in scope the request must be
    refused, which only the wrapper can do.

    The second half pins what the factory may NOT normalise. The fingerprint
    is a hash of response bytes, so moving `Accept` to application/json or
    turning redirects off would change the corpus and demote every GREEN row
    to AMBER -- a tidy-up that would look like the platform shipping.
    """
    from qa.client import build_fingerprint_client

    client = build_fingerprint_client(inner=_Unsendable())
    token = CURRENT_TIER.set(None)
    try:
        with pytest.raises(SafetyViolation, match="No safety tier is in scope"):
            client.get("https://cymetica.com/llms.txt")
    finally:
        CURRENT_TIER.reset(token)
        client.close()

    client = build_fingerprint_client(inner=_Unsendable())
    try:
        assert client.headers["Accept"] == "*/*", (
            "the corpus is read with Accept: */* and the fingerprint is a "
            "hash of what comes back")
        assert client.follow_redirects is True, (
            "the recorded fingerprints were taken with redirects followed")
    finally:
        client.close()


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_request_without_tier_context_is_denied(registry, evidence_store):
    """A request issued outside any test must be refused, not silently allowed."""
    # Deaf like the rest: if the `tier is None` branch goes, this is a READ and
    # the guard returns, so a live GET would leave the machine from the one test
    # that says that is impossible.
    client = _deaf_client(evidence_store, registry=registry)
    token = CURRENT_TIER.set(None)
    try:
        with pytest.raises(SafetyViolation, match="No safety tier is in scope"):
            client.get("/llms.txt")
    finally:
        CURRENT_TIER.reset(token)
        client.close()


# ---------------------------------------------------------------------------
# Layer 3 -- declared executable parameters, never inferred
# ---------------------------------------------------------------------------
@qa(component="meta.guard", tier=SafetyTier.PROBE, surface="meta")
def test_probe_blocks_executable_params(evidence_store):
    """The exact shape of the request we must never send."""
    client = _deaf_client(evidence_store)
    try:
        with pytest.raises(SafetyViolation, match="carries executable parameters"):
            client.post(
                "/api/v1/funding/withdraw",
                json={"token": "USDC", "amount": "1", "destination_address": "0xdead"},
            )
    finally:
        client.close()


@qa(component="meta.guard", tier=SafetyTier.PROBE, surface="meta")
def test_probe_blocks_a_single_executable_param(evidence_store):
    client = _deaf_client(evidence_store)
    try:
        with pytest.raises(SafetyViolation, match="carries executable parameters"):
            client.post("/api/v1/funding/withdraw", json={"amount": "0.0001"})
    finally:
        client.close()


@qa(component="meta.guard", tier=SafetyTier.PROBE, surface="meta")
def test_probe_blocks_undeclared_keys(evidence_store):
    """The guard cannot reason about parameters it has never seen."""
    client = _deaf_client(evidence_store)
    try:
        with pytest.raises(SafetyViolation, match="undeclared keys"):
            client.post("/api/v1/funding/withdraw", json={"surprise_field": "x"})
    finally:
        client.close()


@qa(component="meta.guard", tier=SafetyTier.PROBE, surface="meta")
def test_probe_blocks_order_params(evidence_store):
    client = _deaf_client(evidence_store)
    try:
        with pytest.raises(SafetyViolation, match="carries executable parameters"):
            client.post(
                "/api/v1/clob/orders",
                json={"side": "buy", "price": "0.01", "size": "1"},
            )
    finally:
        client.close()


# ---------------------------------------------------------------------------
# MUTATE gating, and the per-endpoint floor beneath it
# ---------------------------------------------------------------------------
@contextmanager
def as_mutate_tier():
    """Exercise the MUTATE branch of the transport from a SAFE-tier test.

    These proofs must run on EVERY session -- they are the abort gate. Tagging
    them MUTATE would make them skip without --allow-mutate, i.e. the tests
    that prove MUTATE gating works would be absent exactly when the flag is
    off. So they stay SAFE and raise the tier only around the assertion.
    """
    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        yield
    finally:
        CURRENT_TIER.reset(token)


def _mutating_client(evidence_store, mutate_enabled: bool, base_url=None):
    registry = EndpointRegistry.load()
    registry.mutate_enabled = mutate_enabled
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    # Deaf, like every negative control here: these ask the guard to refuse a
    # withdrawal, a deposit and a registration, and one of them really sent a
    # withdrawal the day the floor beneath it was mutated off.
    return _deaf_client(evidence_store, registry=registry, base_url=base_url)


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_mutate_without_flag_is_blocked(evidence_store):
    client = _mutating_client(evidence_store, mutate_enabled=False)
    try:
        with as_mutate_tier(), pytest.raises(SafetyViolation, match="without --allow-mutate"):
            client.post("/api/v1/clob/orders", json={"side": "buy"})
    finally:
        client.close()


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize(
    "path,body",
    [
        ("/api/v1/funding/withdraw", {"amount": "1"}),
        ("/api/v1/funding/deposit", {"amount": "1"}),
        ("/mcp/v1/agents/me/upgrade", {"reason": "x"}),
        ("/mcp/v1/register", {"name": "x"}),
        ("/api/v1/prop/signup", {"tier": "10k"}),
    ],
)
def test_probe_only_endpoints_refuse_mutate_even_when_enabled(evidence_store, path, body):
    """The fourth gate: money-moving endpoints are unreachable at every tier.

    --allow-mutate is not enough. probe_only in components.yaml means
    reachability is testable and execution is not, by construction.
    """
    client = _mutating_client(evidence_store, mutate_enabled=True)
    try:
        with as_mutate_tier(), pytest.raises(SafetyViolation, match="is probe_only"):
            client.post(path, json=body)
    finally:
        client.close()


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_mutate_against_unlisted_host_is_blocked(evidence_store):
    """The host allowlist, on an endpoint that reaches it.

    Not clob/orders: the probe_only floor is checked before the host, so an
    endpoint behind that floor tests the floor and never the allowlist. The
    bounty filing channel is the one write this project performs on purpose
    and is deliberately not probe_only, which makes it the right subject --
    and the guard still refuses before anything leaves the process.
    """
    client = _mutating_client(
        evidence_store, mutate_enabled=True, base_url="https://evil.example.com"
    )
    try:
        with as_mutate_tier(), pytest.raises(SafetyViolation, match="unlisted host"):
            client.post("/api/v1/bounty/reports", json={"title": "x"})
    finally:
        client.close()


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_the_money_loop_is_behind_the_probe_only_floor():
    """components.yaml says probe_only is where money-moving endpoints live.

    Deposit and withdrawal were behind it; the middle leg was not. Cymetica's
    own trust ladder names the three together -- "the full money loop with
    your own deposited funds: deposit, spot CLOB trading (REST
    /api/v1/clob/orders), and withdrawal" -- so an order is the same kind of
    thing as the two either side of it, and a MUTATE test could have placed
    one with --allow-mutate. None does today, which is exactly why this is
    worth pinning: the gap was a trap for whoever wrote the first.
    """
    from qa.safety import EndpointRegistry

    registry = EndpointRegistry.load()
    must = {
        "clob.orders", "clob.order_singular", "arena.order",
        "exchange.buy", "exchange.orders", "agents.clone", "bots.clone",
        "cloned_bots.clone",
        # The event-card orders, which are the ones this repository actually
        # places. Left out until the deep pass of 2026-09-11, so `named_wrong`
        # never read their flag: `event_cards.short` standing on [confirm]
        # passed a MUTATE POST with no `paper` and every guard stayed green.
        "event_cards.buy", "event_cards.sell", "event_cards.short",
        "funding.deposit", "funding.withdraw",
    }
    by_id = {rule.id: rule for rule in registry.rules}
    # Two floors, not one. `probe_only` says execution is never permitted;
    # `required_flags` says it is permitted only carrying a flag the platform
    # publishes as the thing that stops money moving, and the transport
    # refuses the request without it. What is forbidden is an endpoint on this
    # list standing behind NEITHER.
    #
    # agents.clone and bots.clone moved to the second floor on 2026-09-10,
    # after CloneBotRequest published `paper`: "true = paper clone, false =
    # live clone, omitted = inherits the account's simulation_mode". The old
    # floor was written when cloning could only spend.
    missing = sorted(i for i in must if i in by_id
                     and not by_id[i].probe_only
                     and not by_id[i].required_flags)
    assert not missing, (
        f"money-moving endpoints reachable by a MUTATE test: {missing}. "
        f"Add `probe_only: true`, or `required_flags` naming the platform's "
        f"own paper control, or argue in components.yaml why this one is not "
        f"spending anything."
    )
    assert not (must - set(by_id)), \
        f"named in this guard but no longer declared: {sorted(must - set(by_id))}"

    # The flag by NAME. Until 2026-09-10 this asserted only that the set was
    # non-empty, and the contract above is about WHICH flag: "the platform's
    # own paper control". Renaming agents.clone's `required_flags` from
    # [paper] to [confirm] left this green, left the two sibling guards green
    # (one pins rule ids, the other posts only to bots.clone), and a MUTATE
    # POST carrying `confirm: true` and no `paper` key then satisfied
    # `_assert_declared_flags` -- while the live schema resolves an absent
    # `paper` against simulation_mode, which is False on this account.
    # Three readers reproduced it. Presence of a declaration is not a contract
    # about its value, which is the defect class this whole file exists for.
    def named_wrong(rules: dict) -> list[str]:
        return sorted(f"{i}={sorted(rules[i].required_flags)}" for i in must
                      if i in rules and rules[i].required_flags
                      and "paper" not in rules[i].required_flags)

    assert not named_wrong(by_id), (
        f"standing on required_flags that do not name the paper control: "
        f"{named_wrong(by_id)}. Only the platform's own paper flag stops money "
        f"moving; a different key satisfies our guard and leaves the order live."
    )

    # The negative control, because the assertion above is green on today's
    # file whatever it checks, and a guard nobody has watched fire is a guard
    # nobody has tested. This is the exact mutation three readers used.
    import dataclasses

    renamed = dict(by_id)
    renamed["agents.clone"] = dataclasses.replace(
        by_id["agents.clone"], required_flags=frozenset({"confirm"}))
    assert named_wrong(renamed) == ["agents.clone=['confirm']"], (
        "the flag-name check does not fire on a renamed flag, so it is not "
        "checking the name")


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_mutate_never_executes_trade_or_provision_mcp_tools(registry, evidence_store):
    """Even fully enabled, the suite never places an order or creates a fund."""
    reg = EndpointRegistry.load()
    reg.mutate_enabled = True
    reg.mutate_allowed_hosts = frozenset({"cymetica.com"})
    mcp = _deaf_mcp_client(reg, evidence_store)
    try:
        for tool in ("place_order", "create_aib_fund", "launchpad_launch_token"):
            with as_mutate_tier(), pytest.raises(SafetyViolation, match="never executes it"):
                mcp.call_raw(tool, {})
    finally:
        mcp.http.close()


# ---------------------------------------------------------------------------
# MCP: safety is decided by the body, not the HTTP method
# ---------------------------------------------------------------------------
@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_safe_tier_blocks_non_read_mcp_tool(registry, evidence_store):
    mcp = _deaf_mcp_client(registry, evidence_store)
    try:
        with pytest.raises(SafetyViolation, match="classified 'trade'"):
            mcp.call_raw("place_order", {})
        with pytest.raises(SafetyViolation, match="classified 'contribute'"):
            mcp.call_raw("submit_observation", {})
    finally:
        mcp.http.close()


@qa(component="meta.guard", tier=SafetyTier.PROBE, surface="meta")
def test_probe_of_non_read_tool_must_send_empty_arguments(registry, evidence_store):
    mcp = _deaf_mcp_client(registry, evidence_store)
    try:
        with pytest.raises(SafetyViolation, match="carries arguments"):
            mcp.call_raw("place_order", {"pair": "BTC-USD", "side": "buy"})
    finally:
        mcp.http.close()


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_unknown_mcp_tool_is_denied_at_safe(registry, evidence_store):
    """A tool we have not classified is denied, not assumed harmless."""
    mcp = _deaf_mcp_client(registry, evidence_store)
    try:
        with pytest.raises(SafetyViolation, match="classified 'unknown'"):
            mcp.call_raw("some_tool_we_have_never_seen", {})
    finally:
        mcp.http.close()


# ---------------------------------------------------------------------------
# The guard must also NOT over-block: a false sense of coverage is its own bug
# ---------------------------------------------------------------------------
@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_read_methods_are_permitted_at_safe_tier():
    """Negative control: prove these tests can distinguish allow from deny."""
    registry = EndpointRegistry.load()
    transport = SafetyTransport(inner=httpx.MockTransport(lambda r: httpx.Response(200)),
                                registry=registry)
    request = httpx.Request("GET", "https://cymetica.com/llms.txt")
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        assert transport.handle_request(request).status_code == 200
    finally:
        CURRENT_TIER.reset(token)


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_read_mcp_tools_are_permitted_at_safe_tier():
    registry = EndpointRegistry.load()
    transport = SafetyTransport(
        inner=httpx.MockTransport(lambda r: httpx.Response(200, json={"result": {}})),
        registry=registry,
    )
    request = httpx.Request(
        "POST",
        "https://cymetica.com/mcp/v1",
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/call",
              "params": {"name": "list_markets", "arguments": {}}},
    )
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        assert transport.handle_request(request).status_code == 200
    finally:
        CURRENT_TIER.reset(token)


@qa(component="meta.guard", tier=SafetyTier.PROBE, surface="meta")
def test_empty_probe_body_is_permitted():
    """The canonical probe: an empty body, so only the error class comes back."""
    registry = EndpointRegistry.load()
    transport = SafetyTransport(
        inner=httpx.MockTransport(lambda r: httpx.Response(422)), registry=registry
    )
    request = httpx.Request("POST", "https://cymetica.com/api/v1/funding/withdraw", json={})
    token = CURRENT_TIER.set(SafetyTier.PROBE)
    try:
        assert transport.handle_request(request).status_code == 422
    finally:
        CURRENT_TIER.reset(token)


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_register_floor_names_the_fields_that_actually_create_an_account():
    """mcp.register's floor must be spelled in the SERVER's vocabulary.

    Measured 2026-09-07 while walking the /build onboarding: POST
    /mcp/v1/register with an empty body answers 422 naming exactly three
    required fields -- name, contact_email, intended_use. components.yaml
    declared [name, email, description, agent_name]: right idea, wrong words.

    Nothing was open. `_assert_inert` refuses undeclared keys too, so a probe
    carrying contact_email was already stopped -- by the catch-all, not by the
    floor. That is the whole point of this test. A single
    `inert_params: [contact_email, intended_use]` edit would move those two
    fields out of the catch-all and into the permitted set, and every other
    guard test would stay green while POST /mcp/v1/register became executable.

    A floor that does not name what it is standing on is one edit from not
    being a floor.
    """
    rule = next(r for r in EndpointRegistry.load().rules if r.id == "mcp.register")
    assert rule.probe_only, "account creation is an operator action, not ours"

    required_by_server = {"name", "contact_email", "intended_use"}
    missing = required_by_server - rule.executable_params
    assert not missing, (
        f"POST /mcp/v1/register requires {sorted(required_by_server)} (422, "
        f"measured 2026-09-07); {sorted(missing)} is not in its "
        f"executable_params, so only the undeclared-keys catch-all stops it"
    )
    assert not (rule.inert_params & required_by_server), (
        "a field that creates an account is never inert"
    )


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_an_order_without_its_paper_flag_never_leaves_this_machine():
    """`inert_params` was declared, documented, and enforced nowhere.

    components.yaml says it in as many words at the event-card rules: *"`paper`
    is inert: it is the flag that says no money moves, and marking it
    executable would invert its meaning."* The floor was written on 2026-09-08
    so that it would "name what it is standing on". It named it and did not
    stand on it: `_assert_inert` is called only from the PROBE branch, and the
    MUTATE branch checks `mutate_enabled`, `probe_only` and the host without
    ever reading the body.

    What that costs, exactly. The live schema resolves an absent `paper` as
    *"None (default) -> use user.simulation_mode"*, and this account's
    `simulation_mode` is **False**. So a MUTATE POST carrying `amount_usdc` and
    no `paper` key is a live order against the real balance, and every guard we
    have would pass it. Found on 2026-09-10 while planning the paper campaign,
    before the first order rather than after it.

    The rule is the one the comment already claims: at MUTATE, a request to a
    rule that declares inert parameters must carry every one of them, truthy.
    Only the three event-card orders declare any, so nothing else changes.

    Through a transport that cannot send: a control asserting "this is refused"
    performs the thing the moment the refusal breaks, and mutation-testing a
    guard here once sent a real withdrawal.
    """
    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    client = _deaf_client(registry=registry)

    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        with pytest.raises(SafetyViolation) as refused:
            client.post("https://cymetica.com/api/v1/event-cards/42/buy",
                        json={"amount_usdc": 10})
        assert "paper" in str(refused.value), (
            "the refusal must name the flag that was missing, or the next "
            f"person reads it as a tier problem: {refused.value}"
        )

        # The same order, with the flag the floor exists to require, reaches
        # the transport -- which is where _Unsendable stops it.
        with pytest.raises(AssertionError, match="THE GUARD LET IT THROUGH"):
            client.post("https://cymetica.com/api/v1/event-cards/42/buy",
                        json={"amount_usdc": 10, "paper": True})

        # And a flag that is present but false is not a paper order. This is
        # the shape that would slip past a `"paper" in body` reading.
        with pytest.raises(SafetyViolation):
            client.post("https://cymetica.com/api/v1/event-cards/42/buy",
                        json={"amount_usdc": 10, "paper": False})
    finally:
        CURRENT_TIER.reset(token)
        client.close()


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_a_rule_that_requires_no_flag_is_unaffected():
    """The new refusal must not become a tax on every other MUTATE.

    Filing a report, sending a verification, asking the vendor a question --
    the writes this project performs on purpose -- must go through exactly as
    before.
    """
    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    client = _deaf_client(registry=registry)

    # Pinned, because widening this widens what the refusal blocks. The first
    # attempt hung it on `inert_params` and this assertion is what caught it:
    # nine rules declare that key, and on six of them it means "these are
    # harmless in a probe body" -- bounty.a2a_send declares five and sends
    # three, so requiring them would have refused the a2a writer.
    declares = [rule.id for rule in registry.rules if getattr(rule, "required_flags", None)]
    assert sorted(declares) == ["agents.clone", "bots.clone",
                                "cloned_bots.clone",
                                "event_cards.buy", "event_cards.sell",
                                "event_cards.short"], (
        f"the set of rules requiring a flag has moved: {declares}. Each entry "
        f"is an endpoint whose floor was lowered from probe_only, and each one "
        f"needs its own reason in components.yaml."
    )
    inert_only = sorted(rule.id for rule in registry.rules
                        if rule.inert_params and not rule.required_flags)
    assert "bounty.a2a_send" in inert_only, (
        "a2a_send declares inert params and requires none; if that stops "
        "being true, sending a question to the vendor starts being refused"
    )

    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        with pytest.raises(AssertionError, match="THE GUARD LET IT THROUGH"):
            client.post("https://cymetica.com/api/v1/bounty/reports",
                        json={"title": "x", "description": "y"})
    finally:
        CURRENT_TIER.reset(token)
        client.close()


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_a_money_tool_with_a_paper_flag_is_executable_only_with_it():
    """The floor moves from the endpoint to the flag, for tools as well.

    `trade_event_card` moves money and is classified `trade`, so the guard
    refused it at every tier -- correctly, while the only thing it could do was
    spend. Their 2026-09-10 release made it paper by default: *"Defaults to
    PAPER trading (no real funds move). Live trading only on an explicit
    paper=false AND the platform trading gate."*

    A blanket refusal on a tool that can be told not to spend is the same
    mistake `event_cards.buy` carried until this morning: a floor written for a
    world before the flag existed. So the tool becomes executable at MUTATE and
    only ever with the flag, which is the rule `required_flags` already makes
    for REST.

    What must NOT change: `place_order` has no paper control on this surface
    and stays refused, and neither tool is reachable below MUTATE.
    """
    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    client = _deaf_mcp_client(registry=registry)

    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        # Without the flag: refused, and the refusal names it.
        with pytest.raises(SafetyViolation) as refused:
            client.call_raw("trade_event_card", {"card_id": "c1", "amount_usdc": 1})
        assert "paper" in str(refused.value)

        # With it false: that is a live order wearing the flag's name.
        with pytest.raises(SafetyViolation):
            client.call_raw("trade_event_card",
                            {"card_id": "c1", "amount_usdc": 1, "paper": False})

        # With it true: allowed through to a transport that carries nothing.
        with pytest.raises(AssertionError, match="THE GUARD LET IT THROUGH"):
            client.call_raw("trade_event_card",
                            {"card_id": "c1", "amount_usdc": 1, "paper": True})

        # A tool with no paper control is untouched by any of this.
        with pytest.raises(SafetyViolation) as still:
            client.call_raw("place_order", {"symbol": "BTC", "size": 1})
        assert "trade" in str(still.value)
    finally:
        CURRENT_TIER.reset(token)
        client.http.close()


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_a_paper_gate_reads_the_value_not_that_something_is_there():
    """`place_arena_order` (new 2026-09-22) is stopped by a STRING, not a
    flag: *"PAPER by default (mode='paper'): no real funds move. mode='live'
    passes the fail-closed trading gate first"*, and its schema is
    `mode: enum [paper, live]`. The gate read `not args.get(gate)` -- present
    and truthy -- and `'live'` is a truthy string, so naming this tool in
    paper_gated the old way would have let a live order through wearing the
    gate's own key.

    The same reading had a hole on the gate that already existed: a `paper`
    of `"false"` is truthy, and a server that coerces strings reads it as
    false. A flag gate now needs `True` itself, and a value gate needs the
    value. Omitted is refused on both, although their default is paper: the
    default is theirs to change, the argument is what we sent."""
    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    client = _deaf_mcp_client(registry=registry)
    order = {"team_symbol": "BLUE", "side": "buy", "price": 0.5, "size": 1}

    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        for args in ({**order, "mode": "live"}, dict(order),
                     {**order, "mode": "PAPER"}, {**order, "mode": True}):
            with pytest.raises(SafetyViolation) as refused:
                client.call_raw("place_arena_order", args)
            assert "mode" in str(refused.value), (args, str(refused.value))

        with pytest.raises(AssertionError, match="THE GUARD LET IT THROUGH"):
            client.call_raw("place_arena_order", {**order, "mode": "paper"})

        with pytest.raises(SafetyViolation):
            client.call_raw("trade_event_card",
                            {"card_id": "c1", "amount_usdc": 1, "paper": "false"})
        with pytest.raises(AssertionError, match="THE GUARD LET IT THROUGH"):
            client.call_raw("trade_event_card",
                            {"card_id": "c1", "amount_usdc": 1, "paper": True})
    finally:
        CURRENT_TIER.reset(token)

    # Paper is still not free: below MUTATE the arena order is refused too.
    # (The REST floor and a JSON-RPC batch: the next test.)
    for tier in (SafetyTier.SAFE, SafetyTier.PROBE):
        token = CURRENT_TIER.set(tier)
        try:
            with pytest.raises(SafetyViolation):
                client.call_raw("place_arena_order", {**order, "mode": "paper"})
        finally:
            CURRENT_TIER.reset(token)
    client.http.close()


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_a_string_flag_or_a_batch_does_not_carry_a_live_order_past_the_guard():
    """C01, deep pass of 2026-09-22 evening (3/3). Two doors the MCP paper
    gate's fix of the same afternoon left open.

    The REST floor, `required_flags`, still read `not payload.get(flag)`: a
    `paper` of `"false"` -- or `"0"` -- is truthy, reads as false to a server
    that coerces strings, and passed an event-card buy at MUTATE. The flag has
    to be `True` itself, the rule the MCP gate now holds.

    And `_check_rpc` returned early on any body that was not a JSON object, at
    PROBE and MUTATE alike. A JSON-RPC batch is a list, so
    `[{"method": "tools/call", "params": {"name": "place_arena_order",
    "arguments": {"mode": "live", ...}}}]` reached the transport unread. Every
    call in a batch is held to the rule a single call is."""
    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    rest = _deaf_client(registry=registry)
    mcp = _deaf_mcp_client(registry=registry)
    buy = "https://cymetica.com/api/v1/event-cards/42/buy"

    def call(tool, arguments):
        return {"jsonrpc": "2.0", "id": 1, "method": "tools/call",
                "params": {"name": tool, "arguments": arguments}}

    live = call("place_arena_order", {"team_symbol": "BLUE", "side": "buy",
                                      "price": 0.5, "size": 1, "mode": "live"})
    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        for spelled in ("false", "0", "true", 1):
            with pytest.raises(SafetyViolation):
                rest.post(buy, json={"amount_usdc": 10, "paper": spelled})
        with pytest.raises(AssertionError, match="THE GUARD LET IT THROUGH"):
            rest.post(buy, json={"amount_usdc": 10, "paper": True})

        with pytest.raises(SafetyViolation):
            mcp.http.post("", json=[live])
        with pytest.raises(SafetyViolation):
            mcp.http.post("", json=[call("get_event_card_info", {}), live])
        # A batch of reads is still a read.
        with pytest.raises(AssertionError, match="THE GUARD LET IT THROUGH"):
            mcp.http.post("", json=[call("get_event_card_info", {})])
    finally:
        CURRENT_TIER.reset(token)

    token = CURRENT_TIER.set(SafetyTier.PROBE)
    try:
        with pytest.raises(SafetyViolation):
            mcp.http.post("", json=[live])
    finally:
        CURRENT_TIER.reset(token)
    rest.close()
    mcp.http.close()


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_a_tool_this_registry_has_never_heard_of_is_refused_at_mutate():
    """Default-deny, at the one tier that can spend.

    `_check_rpc` raised for `trade` and `provision` and then fell off the end
    of the function, so a tool in none of `components.yaml`'s four lists was
    PERMITTED at MUTATE with full arguments. SAFE refuses it by name and PROBE
    forces empty arguments; the only tier that can move money was the one that
    let it through. Three readers reproduced it independently, each by calling
    a tool that does not exist and reaching the transport.

    Cymetica publish 62 tools and shipped a changed one this morning, so "a
    tool the registry has not been taught" is the ordinary case after any
    release, not a hypothetical. And `trade_event_card` is itself classified in
    no list at all -- it is reachable only through `mcp_tools.paper_gated`, so
    the moment that entry is removed it would become permitted rather than
    refused, which is the opposite of what removing a gate should do.
    """
    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    client = _deaf_mcp_client(registry=registry)

    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        # No blanket `except AssertionError` here, and that is deliberate: the
        # deaf transport signals a let-through BY raising AssertionError, so
        # catching one would swallow exactly the failure this test is for. The
        # first draft of this test did that and passed against the unfixed
        # guard.
        with pytest.raises(SafetyViolation) as refused:
            client.call_raw("a_tool_shipped_after_this_registry_was_written",
                            {"amount_usdc": 1000, "confirm": True})
        assert "unclassified" in str(refused.value).lower(), (
            f"the refusal must say the tool is unclassified, so a reader knows "
            f"to classify it rather than to hunt a bug: {refused.value}")
    finally:
        CURRENT_TIER.reset(token)

    # A classified read tool is untouched: the point is default-deny for the
    # unknown, not a wider refusal. Reaching the transport is the pass here.
    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        with pytest.raises(AssertionError, match="THE GUARD LET IT THROUGH"):
            client.call_raw("get_event_card_info", {})
    finally:
        CURRENT_TIER.reset(token)
        client.http.close()


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_a_paper_gated_tool_is_still_refused_below_mutate():
    """Paper is not free. Every call still costs a rate limit and creates a
    position on their side, so it stays a deliberate MUTATE."""
    registry = EndpointRegistry.load()
    client = _deaf_mcp_client(registry=registry)
    for tier in (SafetyTier.SAFE, SafetyTier.PROBE):
        token = CURRENT_TIER.set(tier)
        try:
            with pytest.raises(SafetyViolation):
                client.call_raw("trade_event_card",
                                {"card_id": "c1", "amount_usdc": 1, "paper": True})
        finally:
            CURRENT_TIER.reset(token)
    client.http.close()


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_cloning_a_bot_needs_its_paper_flag_too():
    """The operator's hundred bots, and the floor that stood in their way.

    Both clone routes were probe_only because "cloning funds an agent; the gas
    policy bills cloned agents to the user's own balance". CloneBotRequest now
    documents `paper`: *"true = paper clone, false = live clone, omitted =
    inherits the account's simulation_mode."* Omitted is the dangerous one, and
    it is exactly what required_flags refuses.

    **Every clone route, including the one that exists.** Deep-pass finding
    A06 said this test named "both clone paths" and exercised one. The 2026-09-
    10 sweep found the sharper version of the same thing: it exercised the one
    the platform does not serve. `/api/v1/agents/*` is absent from their
    openapi entirely and `/api/v1/bots/clone` is our own reported 404 -- the
    route that clones is `/api/v1/cloned-bots/clone`, and until this commit it
    stood behind no rule at all. Default-deny caught it, so nothing could have
    been spent, but the paper floor was guarding two doors nobody serves while
    the real one was held shut only by not being declared. A floor aimed at
    the wrong door is indistinguishable from a floor, right up until someone
    declares the endpoint to make their request work.
    """
    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    client = _deaf_client(registry=registry)

    routes = ["https://cymetica.com/api/v1/cloned-bots/clone",
              "https://cymetica.com/api/v1/bots/clone",
              "https://cymetica.com/api/v1/agents/clone"]
    source = {"source_type": "wta_species", "source_id": "s1"}

    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        for url in routes:
            with pytest.raises(SafetyViolation) as refused:
                client.post(url, json=source)
            assert "paper" in str(refused.value), url

            # By VALUE, not by presence. `paper: false` is documented as a
            # LIVE clone -- the reading that only asks whether the key exists
            # would wave through the one body on this endpoint that spends.
            with pytest.raises(SafetyViolation) as live:
                client.post(url, json={**source, "paper": False})
            assert "paper" in str(live.value), url

            with pytest.raises(AssertionError, match="THE GUARD LET IT THROUGH"):
                client.post(url, json={**source, "paper": True})
    finally:
        CURRENT_TIER.reset(token)
        client.close()
