"""Proof that the safety guard blocks.

These run first and abort the session on failure. If the guard cannot be shown
to stop a SAFE POST, a probe carrying executable parameters, and an ungated
MUTATE, then zero live requests are issued for the rest of the run.

Every test here asserts a REFUSAL. Nothing in this file reaches the network:
each violation is raised before the transport delegates.
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
# Layer 2 -- the transport enforces the tier of the running test
# ---------------------------------------------------------------------------
@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_safe_tier_blocks_post(rest_client):
    with pytest.raises(SafetyViolation, match="SAFE test attempted POST"):
        rest_client.post("/api/v1/clob/orders", json={})


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_safe_tier_blocks_withdraw_entirely(rest_client):
    with pytest.raises(SafetyViolation, match="SAFE test attempted POST"):
        rest_client.post("/api/v1/funding/withdraw", json={})


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_unknown_write_path_is_default_denied(rest_client):
    with pytest.raises(SafetyViolation, match="matches no rule in components.yaml"):
        rest_client.post("/api/v1/some/undeclared/endpoint", json={})


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_request_without_tier_context_is_denied(registry, evidence_store):
    """A request issued outside any test must be refused, not silently allowed."""
    client = build_client(ANON, registry, evidence_store)
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
def test_probe_blocks_executable_params(rest_client):
    """The exact shape of the request we must never send."""
    with pytest.raises(SafetyViolation, match="carries executable parameters"):
        rest_client.post(
            "/api/v1/funding/withdraw",
            json={"token": "USDC", "amount": "1", "destination_address": "0xdead"},
        )


@qa(component="meta.guard", tier=SafetyTier.PROBE, surface="meta")
def test_probe_blocks_a_single_executable_param(rest_client):
    with pytest.raises(SafetyViolation, match="carries executable parameters"):
        rest_client.post("/api/v1/funding/withdraw", json={"amount": "0.0001"})


@qa(component="meta.guard", tier=SafetyTier.PROBE, surface="meta")
def test_probe_blocks_undeclared_keys(rest_client):
    """The guard cannot reason about parameters it has never seen."""
    with pytest.raises(SafetyViolation, match="undeclared keys"):
        rest_client.post("/api/v1/funding/withdraw", json={"surprise_field": "x"})


@qa(component="meta.guard", tier=SafetyTier.PROBE, surface="meta")
def test_probe_blocks_order_params(rest_client):
    with pytest.raises(SafetyViolation, match="carries executable parameters"):
        rest_client.post(
            "/api/v1/clob/orders",
            json={"side": "buy", "price": "0.01", "size": "1"},
        )


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
    return build_client(ANON, registry, evidence_store, base_url=base_url)


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
    client = _mutating_client(
        evidence_store, mutate_enabled=True, base_url="https://evil.example.com"
    )
    try:
        with as_mutate_tier(), pytest.raises(SafetyViolation, match="unlisted host"):
            client.post("/api/v1/clob/orders", json={"side": "buy"})
    finally:
        client.close()


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_mutate_never_executes_trade_or_provision_mcp_tools(registry, evidence_store):
    """Even fully enabled, the suite never places an order or creates a fund."""
    reg = EndpointRegistry.load()
    reg.mutate_enabled = True
    reg.mutate_allowed_hosts = frozenset({"cymetica.com"})
    mcp = build_mcp_client(ANON, reg, evidence_store)
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
    mcp = build_mcp_client(ANON, registry, evidence_store)
    try:
        with pytest.raises(SafetyViolation, match="classified 'trade'"):
            mcp.call_raw("place_order", {})
        with pytest.raises(SafetyViolation, match="classified 'contribute'"):
            mcp.call_raw("submit_observation", {})
    finally:
        mcp.http.close()


@qa(component="meta.guard", tier=SafetyTier.PROBE, surface="meta")
def test_probe_of_non_read_tool_must_send_empty_arguments(registry, evidence_store):
    mcp = build_mcp_client(ANON, registry, evidence_store)
    try:
        with pytest.raises(SafetyViolation, match="carries arguments"):
            mcp.call_raw("place_order", {"pair": "BTC-USD", "side": "buy"})
    finally:
        mcp.http.close()


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_unknown_mcp_tool_is_denied_at_safe(registry, evidence_store):
    """A tool we have not classified is denied, not assumed harmless."""
    mcp = build_mcp_client(ANON, registry, evidence_store)
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
