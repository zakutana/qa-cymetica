"""HTTP and MCP clients -- the only sanctioned way to reach the network.

Layer 1 of the safety guard lives here: constructing an httpx client outside
these factories raises. Without that, a helper function could quietly build its
own client, bypass SafetyTransport, and send anything it liked. With it, the
only path to the network runs through the tier check.
"""

from __future__ import annotations

import json
from typing import Any

import httpx

from qa import ratelimit
from qa.config import DEFAULT_TIMEOUT, USER_AGENT, Identity, base_urls
from qa.marks import Inconclusive
from qa.safety import EndpointRegistry, SafetyTransport, SafetyViolation

_FACTORY_SENTINEL = object()

_ORIGINALS: dict[str, Any] = {}
_GUARD_INSTALLED = False


def install_client_guard() -> None:
    """Ban client construction outside this module. Idempotent."""
    global _GUARD_INSTALLED
    if _GUARD_INSTALLED:
        return

    _ORIGINALS["Client"] = httpx.Client.__init__
    _ORIGINALS["AsyncClient"] = httpx.AsyncClient.__init__

    def _guarded(original, label):
        def __init__(self, *args, _qa_factory=None, **kwargs):
            if _qa_factory is not _FACTORY_SENTINEL:
                raise SafetyViolation(
                    f"Direct httpx.{label} construction is forbidden. Every "
                    f"request must go through SafetyTransport, so use the "
                    f"rest_client / mcp_client fixtures instead. If you need a "
                    f"client shape they do not offer, add a factory to "
                    f"qa/client.py rather than bypassing the guard."
                )
            return original(self, *args, **kwargs)
        return __init__

    httpx.Client.__init__ = _guarded(_ORIGINALS["Client"], "Client")
    httpx.AsyncClient.__init__ = _guarded(_ORIGINALS["AsyncClient"], "AsyncClient")

    try:
        import requests

        _ORIGINALS["Session"] = requests.Session.__init__

        def _session_init(self, *args, **kwargs):
            raise SafetyViolation(
                "requests.Session is forbidden: it does not route through "
                "SafetyTransport. Use the rest_client fixture."
            )

        requests.Session.__init__ = _session_init
    except ImportError:
        pass

    _GUARD_INSTALLED = True


def remove_client_guard() -> None:
    global _GUARD_INSTALLED
    if not _GUARD_INSTALLED:
        return
    httpx.Client.__init__ = _ORIGINALS["Client"]
    httpx.AsyncClient.__init__ = _ORIGINALS["AsyncClient"]
    if "Session" in _ORIGINALS:
        import requests
        requests.Session.__init__ = _ORIGINALS["Session"]
    _GUARD_INSTALLED = False


class GuardBreached(RuntimeError):
    """The guard failed to refuse something it exists to refuse."""


# The subject of layers 2 and 3: a declared, money-moving POST. Which endpoint
# it is does not matter to them -- only that it is a write.
WITHDRAW = "/api/v1/funding/withdraw"


def _probe_only_path(registry: EndpointRegistry) -> str:
    """Any endpoint the corpus declares probe_only, for layer 4 to bounce off.

    Naming one endpoint made a config change lethal: take `probe_only` off
    funding.withdraw for a good reason and layer 4 stops being refused, so
    pytest_configure aborts EVERY session -- including the ones that would
    explain the change -- with a message blaming the floor rather than the
    corpus. Asking the registry instead means one endpoint leaving the floor
    is a config change, and the floor being gone everywhere is what stops the
    suite, which is the condition actually worth stopping for.
    """
    floors = [r for r in sorted(registry.rules, key=lambda r: r.id)
              if r.probe_only and "POST" in r.methods]
    for rule in floors:
        if rule.path == WITHDRAW:  # the usual subject, so failures read alike
            return rule.path
    if floors:
        return floors[0].path
    raise GuardBreached(
        "layer 4 has nothing to test: components.yaml declares no probe_only "
        "POST endpoint at all, so the floor that keeps MUTATE tests off the "
        "money loop does not exist. Restore it before running anything."
    )


class _NeverSends(httpx.BaseTransport):
    """The self-check's floor. Reaching it IS the failure being looked for."""

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        raise GuardBreached(
            f"{request.method} {request.url} reached the transport. The guard "
            f"let it through; on a live transport it would have been sent."
        )


def assert_client_guard_blocks() -> None:
    """Prove the guard refuses, before anything is allowed to ask it to.

    `tests/conftest.py` sorts `tests/meta` first and aborts the session when
    one of them fails, so a broken guard stops every live request -- but only
    when the meta tests are IN the selector. A bare `pytest
    tests/rest/test_x.py` collects none of them, and that has happened: live
    requests went out with the guard unproven. Policing the selector would
    treat the symptom. The guard is installed in `pytest_configure`, so this
    is where it should also be made to demonstrate itself.

    Four claims, each one an enforcement layer, none of them touching the
    network: every client here carries `_NeverSends` underneath, so a layer
    that has stopped working raises instead of performing the act it exists to
    prevent. That distinction is not theoretical -- mutating the probe_only
    floor off to see whether the suite could feel it sent a real POST to
    /api/v1/funding/withdraw.

    Costs about a millisecond. Raises `GuardBreached` naming the layer that
    let go; the caller decides what to do about it.
    """
    from qa.safety import CURRENT_TIER, SafetyTier

    # 1 -- construction ban: nothing may build a client outside this module.
    #      Tested by behaviour, never by the _GUARD_INSTALLED flag, which is
    #      the thing that would be wrong if the ban were half-applied. The
    #      flag only words the message.
    try:
        probe = httpx.Client()
    except SafetyViolation:
        pass
    else:
        probe.close()  # or the breach path leaks the pool it just opened
        raise GuardBreached(
            "layer 1: httpx.Client() was constructed without going through "
            "qa/client.py -- "
            + ("the construction ban was never installed" if not _GUARD_INSTALLED
               else "the ban is installed and did not fire")
            + ". Anything could now build its own client and skip "
            "SafetyTransport entirely."
        )

    registry = EndpointRegistry.load()
    anon = Identity(name="guard-self-check")

    def _refuses(path: str, tier: SafetyTier | None, layer: str, reg=registry):
        token = CURRENT_TIER.set(tier)
        client = None
        try:
            # Inside the try: the tier is already set, so anything that raises
            # between here and the reset leaves it set for the process. At
            # layer 4 that would be a leaked MUTATE.
            client = build_client(anon, reg, inner=_NeverSends())
            client.post(path, json={"amount": "1"})
        except SafetyViolation:
            return
        except GuardBreached as exc:
            raise GuardBreached(f"{layer} let it through. {exc}") from None
        finally:
            if client is not None:
                client.close()
            CURRENT_TIER.reset(token)
        raise GuardBreached(
            f"{layer} let it through: POST {path} returned without reaching "
            f"the transport, so something answered it early."
        )

    # 2 -- no tier in scope: a request from outside a test is nobody's.
    _refuses(WITHDRAW, None, "layer 2: no safety tier in scope")

    # 3 -- the tier ladder: a SAFE test may not write.
    _refuses(WITHDRAW, SafetyTier.SAFE, "layer 3: SAFE tier")

    # 4 -- the probe_only floor, which is the one that has actually come off.
    #      A private registry copy: the session's own must keep whatever
    #      --allow-mutate said.
    mutating = EndpointRegistry.load()
    mutating.mutate_enabled = True
    mutating.mutate_allowed_hosts = frozenset({"cymetica.com"})
    _refuses(_probe_only_path(mutating), SafetyTier.MUTATE,
             "layer 4: probe_only floor", reg=mutating)


def build_client(
    identity: Identity,
    registry: EndpointRegistry,
    evidence=None,
    budget=None,
    base_url: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
    inner: httpx.BaseTransport | None = None,
) -> httpx.Client:
    """`inner` replaces the transport underneath the guard. It exists for the
    guard's own negative controls.

    Those tests assert that a forbidden request is refused, and their only
    protection against actually making it was the code they are testing. With
    the probe_only floor mutated off, one of them sent a real POST to
    /api/v1/funding/withdraw. Giving them a transport that refuses to carry
    anything means a broken guard fails the test instead of performing the
    action it was supposed to prevent.
    """
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    headers.update(identity.headers())
    if identity.scope != "read":
        # Read by the transport to refuse trade-scoped credentials on
        # non-MUTATE tests. Stripped from evidence by the redactor.
        headers["X-API-Key-Scope"] = identity.scope

    transport = SafetyTransport(
        inner=inner if inner is not None else httpx.HTTPTransport(retries=0),
        registry=registry,
        evidence=evidence,
        budget=budget,
        # The shared brake, on the real network only (qa/ratelimit.py).
        pacer=ratelimit.shared() if inner is None else None,
    )
    kwargs = dict(
        base_url=base_url or base_urls()["rest"],
        headers=headers,
        transport=transport,
        timeout=timeout,
        follow_redirects=False,  # a redirect is a finding, not a detail
    )
    # The construction ban is installed by pytest_configure. Scripts run
    # without it, and the sentinel is only a valid keyword while it is on.
    if _GUARD_INSTALLED:
        kwargs["_qa_factory"] = _FACTORY_SENTINEL
    return httpx.Client(**kwargs)


def build_mock_client(
    handler,
    registry: EndpointRegistry | None = None,
    evidence=None,
    budget=None,
    base_url: str = "https://cymetica.com",
    timeout: float = 5.0,
) -> httpx.Client:
    """A client whose network is a function, for testing the adapter scripts.

    It exists so that testing bounty.py and submit.py does not mean bypassing
    the construction guard -- the guard's own message says to add a factory
    here rather than reach around it. The mock transport is wrapped in the
    same SafetyTransport as a live client, so a call that would have violated
    a tier rule still violates it.
    """
    transport = SafetyTransport(
        inner=httpx.MockTransport(handler),
        registry=registry if registry is not None else EndpointRegistry.load(),
        evidence=evidence,
        budget=budget,
    )
    kwargs = dict(
        base_url=base_url,
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        transport=transport,
        timeout=timeout,
        follow_redirects=False,
    )
    if _GUARD_INSTALLED:
        kwargs["_qa_factory"] = _FACTORY_SENTINEL
    return httpx.Client(**kwargs)


def build_fingerprint_client(
    registry: EndpointRegistry | None = None,
    timeout: float = 20.0,
    inner: httpx.BaseTransport | None = None,
) -> httpx.Client:
    """The client `qa/fingerprint.py` reads the platform corpus with.

    It exists because that module used to import `_FACTORY_SENTINEL` and build
    its own `httpx.Client`, which is exactly what the guard's refusal message
    tells a caller not to do -- so the corpus was read every session with no
    SafetyTransport under it. The reads are SAFE GETs of public documents and
    the tier is granted by hand in `compute()`, so nothing was at risk; what
    was missing was the guard. Architecture audit, 2026-09-20.

    Three arguments are deliberate and none of them is a default to tidy up:

    * **The request shape is the corpus's shape.** `Accept: */*`,
      `follow_redirects=True` and a 20 s timeout are what the recorded
      fingerprints were taken under, and the hash is over response bytes --
      normalising any of them to `build_client`'s values would move the
      fingerprint and demote every GREEN row to AMBER on the next run
      (`qa/fold.py` pins rows to `pinned_fingerprint`).
    * **`evidence=None`.** `EvidenceStore` is keyed by run id, and
      `session.qa_run_id` is assigned two lines AFTER `compute()` runs at
      `qa/report_plugin.py:118-120`. There is no store to write into yet.
    * **`budget=None`.** A budget here would register itself as the session's
      active one and overwrite what `run["ratelimit"]` means; and an exhausted
      budget raises inside `compute()`, whose per-part handler swallows it --
      so every part would become an error, the fingerprint would come back
      None, and `fingerprint_drifted` would read False on a run that measured
      nothing at all.

    `inner` is for the negative controls, the same as `build_client`'s.
    """
    transport = SafetyTransport(
        inner=inner if inner is not None else httpx.HTTPTransport(retries=0),
        registry=registry if registry is not None else EndpointRegistry.load(),
        evidence=None,
        budget=None,
        pacer=ratelimit.shared() if inner is None else None,
    )
    kwargs = dict(
        headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
        transport=transport,
        timeout=timeout,
        follow_redirects=True,
    )
    if _GUARD_INSTALLED:
        kwargs["_qa_factory"] = _FACTORY_SENTINEL
    return httpx.Client(**kwargs)


class _Uncounted(httpx.BaseTransport):
    """Carries a request without `SafetyTransport` writing it to the timings
    diary. That diary is evidence about THEIR host -- `scripts/timeouts.py` reads
    every row as theirs -- and a CoinGecko timeout in it would be blamed on them.
    `SafetyTransport` only times what reaches an `httpx.HTTPTransport`, so
    wrapping it is enough; nothing else about the request changes."""

    def __init__(self, inner: httpx.BaseTransport):
        self.inner = inner

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        return self.inner.handle_request(request)

    def close(self) -> None:
        self.inner.close()


def build_source_client(
    evidence=None,
    timeout: float = 60.0,
    inner: httpx.BaseTransport | None = None,
) -> httpx.Client:
    """The client the Gem Screener audit reads public third-party sources with:
    CoinGecko, DefiLlama and DexScreener, the places their numbers come from.

    It exists so a check can ask "is this number what the source says?" without
    building its own client, the thing the construction ban refuses. Every layer
    of the guard is underneath it, as under `build_client`: no tier in scope is
    refused, and a write to any host is refused because no rule declares one.

    Three arguments are deliberate:

    * **`budget=None`.** `RateLimitBudget` reads `x-ratelimit-*` from every
      response and stops the whole session at 60 % of a quota. A third party's
      rate-limit headers are not Cymetica's quota, and one of them tripping it
      would turn a run partial and cost it level V -- the reason
      `build_fingerprint_client` has no budget either.
    * **No credential.** These are anonymous reads of public APIs. An identity's
      key must never be sent to a host that is not theirs.
    * **Not timed.** See `_Uncounted`.

    `evidence` is kept: the body of what a source said is what backs a finding
    made from it. `inner` is for the negative controls.
    """
    transport = SafetyTransport(
        inner=_Uncounted(inner if inner is not None else httpx.HTTPTransport(retries=0)),
        registry=EndpointRegistry.load(),
        evidence=evidence,
        budget=None,
        pacer=ratelimit.shared() if inner is None else None,
    )
    kwargs = dict(
        headers={"User-Agent": USER_AGENT, "Accept": "application/json"},
        transport=transport,
        timeout=timeout,
        follow_redirects=False,
    )
    if _GUARD_INSTALLED:
        kwargs["_qa_factory"] = _FACTORY_SENTINEL
    return httpx.Client(**kwargs)


class McpError(RuntimeError):
    """A JSON-RPC or tool-level error. Carries the raw payload for evidence."""

    def __init__(self, message: str, payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.payload = payload or {}


class McpReadFailed(McpError, Inconclusive):
    """A read whose reply is not the answer it asked for: rule 8, a failed read is not an empty one.

    An McpError, so every caller that already catches one still does; an Inconclusive, so a check
    that does not catch it is recorded as unmeasured by report_plugin, never as a pass or a fail.
    Raising it can only move a verdict towards Inconclusive, never mint one.
    """


class McpClient:
    """JSON-RPC 2.0 client for https://cymetica.com/mcp/v1.

    Two platform behaviours shape this class, both verified:

      * tool failures return HTTP 200 with result.isError true, so the HTTP
        status says nothing about whether the call succeeded;
      * the error itself is a JSON string nested inside content[0].text, i.e.
        double-encoded.

    unwrap() undoes both so tests read plain data, while raw() keeps the
    envelope for the error classifier, which needs the shape and not just the
    payload.
    """

    def __init__(self, client: httpx.Client, identity: Identity):
        self.http = client
        self.identity = identity
        self._id = 0

    def _next_id(self) -> int:
        self._id += 1
        return self._id

    def rpc(self, method: str, params: dict[str, Any] | None = None) -> httpx.Response:
        body: dict[str, Any] = {"jsonrpc": "2.0", "id": self._next_id(), "method": method}
        if params is not None:
            body["params"] = params
        return self.http.post("", json=body)

    def raw(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        response = self.rpc(method, params)
        try:
            return response.json()
        except json.JSONDecodeError as exc:
            raise McpError(
                f"MCP returned non-JSON for {method} "
                f"(HTTP {response.status_code}): {response.text[:200]!r}"
            ) from exc

    def tools_list(self) -> list[dict[str, Any]]:
        """The served catalogue, or McpReadFailed: never [] for a reply that listed nothing.

        B03, deep pass 2026-10-25 (3 of 3): anything without an `error` key came back as
        `.get("result", {}).get("tools", [])`, so a 401/429/5xx `{"detail": ...}` (rpc() does not
        raise for status) was an empty catalogue. tests/mcp/test_trust_ladder.py then passed an
        anonymous read nobody made, and called every tool lost when the trusted read failed. The
        shape is the one `refusal_class` there already names: neither `result` nor `error`.
        """
        try:
            payload = self.raw("tools/list")
        except McpError as exc:  # a body that is not JSON: a 502 page, a cut connection
            raise McpReadFailed(f"tools/list could not be read: {exc}") from exc
        if not isinstance(payload, dict):
            raise McpReadFailed(f"tools/list answered {type(payload).__name__}, not a JSON-RPC reply")
        if "error" in payload:
            raise McpReadFailed(f"tools/list failed: {payload['error']}", payload)
        result = payload.get("result")
        tools = result.get("tools") if isinstance(result, dict) else None
        if not isinstance(tools, list):
            raise McpReadFailed(
                "tools/list answered no JSON-RPC result listing tools: "
                + json.dumps(payload, ensure_ascii=False, default=str)[:300], payload)
        return tools

    def tool_names(self) -> set[str]:
        return {t["name"] for t in self.tools_list() if "name" in t}

    def call_raw(self, tool: str, arguments: dict[str, Any] | None = None) -> dict[str, Any]:
        return self.raw("tools/call", {"name": tool, "arguments": arguments or {}})

    def call(self, tool: str, arguments: dict[str, Any] | None = None) -> Any:
        return self.unwrap(self.call_raw(tool, arguments))

    @staticmethod
    def unwrap(payload: dict[str, Any]) -> Any:
        """Undo the double encoding. Raises McpError on a tool-level failure."""
        if "error" in payload:
            raise McpError(f"JSON-RPC error: {payload['error']}", payload)

        result = payload.get("result")
        if not isinstance(result, dict):
            return result

        content = result.get("content") or []
        text = None
        if content and isinstance(content[0], dict):
            text = content[0].get("text")

        decoded: Any = text
        if isinstance(text, str):
            try:
                decoded = json.loads(text)
            except json.JSONDecodeError:
                decoded = text

        if result.get("isError"):
            raise McpError(f"tool error: {decoded}", payload)
        return decoded if decoded is not None else result


def build_mcp_client(
    identity: Identity,
    registry: EndpointRegistry,
    evidence=None,
    budget=None,
    inner: httpx.BaseTransport | None = None,
) -> McpClient:
    # `inner` exists for the negative controls, and only for them. Without it
    # the four MCP guard self-tests sat on a live transport while the REST ones
    # had been moved to _Unsendable on 2026-09-06 -- so "assert the guard
    # refuses place_order" was one tool_class regression away from placing one.
    # Found by the contract audit on 2026-09-07; the REST remediation had simply
    # never been carried across to this constructor.
    http = build_client(
        identity, registry, evidence, budget, base_url=base_urls()["mcp"],
        inner=inner,
    )
    http.headers["Content-Type"] = "application/json"
    return McpClient(http, identity)
