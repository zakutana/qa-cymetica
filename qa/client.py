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

from qa.config import DEFAULT_TIMEOUT, USER_AGENT, Identity, base_urls
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


def build_client(
    identity: Identity,
    registry: EndpointRegistry,
    evidence=None,
    budget=None,
    base_url: str | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> httpx.Client:
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    headers.update(identity.headers())
    if identity.scope != "read":
        # Read by the transport to refuse trade-scoped credentials on
        # non-MUTATE tests. Stripped from evidence by the redactor.
        headers["X-API-Key-Scope"] = identity.scope

    transport = SafetyTransport(
        inner=httpx.HTTPTransport(retries=0),
        registry=registry,
        evidence=evidence,
        budget=budget,
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


class McpError(RuntimeError):
    """A JSON-RPC or tool-level error. Carries the raw payload for evidence."""

    def __init__(self, message: str, payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.payload = payload or {}


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
        payload = self.raw("tools/list")
        if "error" in payload:
            raise McpError(f"tools/list failed: {payload['error']}", payload)
        return payload.get("result", {}).get("tools", [])

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
) -> McpClient:
    http = build_client(
        identity, registry, evidence, budget, base_url=base_urls()["mcp"]
    )
    http.headers["Content-Type"] = "application/json"
    return McpClient(http, identity)
