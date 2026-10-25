"""A tools/list reply that is not a JSON-RPC result is a failed read, never an empty catalogue (B03).

Deep pass 2026-10-25 (3 of 3): `McpClient.tools_list()` raised only for a JSON-RPC `error` and
returned `payload.get("result", {}).get("tools", [])` for anything else -- so a 401, 429 or 5xx
`{"detail": ...}` came back as []. In tests/mcp/test_trust_ladder.py an anonymous read that failed
then passed on a list nobody read ("anonymous sees nothing above its tier"), and a trusted read that
failed reported every anonymous tool as lost by authenticating: a red row made of a failed read.
`refusal_class` in the same file already names that shape ("result" and "error" both absent).

Offline: a real McpClient over a stub transport answering each shape.
"""

import contextvars
import json

import pytest

from qa.client import McpClient, McpError
from qa.marks import Inconclusive, SafetyTier, qa

SELF = qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")

TOOLS = [{"name": "get_event_card_info"}, {"name": "list_event_cards"}, {"name": "register_agent"}]
LISTED = {"jsonrpc": "2.0", "id": 1, "result": {"tools": TOOLS}}


class _Answer:
    def __init__(self, status, body=None, text=None):
        self.status_code, self._body = status, body
        self.text = text if text is not None else json.dumps(body)

    def json(self):
        if self._body is None:
            raise json.JSONDecodeError("Expecting value", self.text, 0)
        return self._body


class _Http:
    def __init__(self, answer):
        self.answer = answer

    def post(self, path, json=None):
        return self.answer


def _mcp(status, body=None, text=None):
    return McpClient(_Http(_Answer(status, body, text)), identity=None)


FAILED_READS = {
    "401 detail": (401, {"detail": "Not authenticated"}, None),
    "429 detail": (429, {"detail": "Rate limit exceeded"}, None),
    "503 detail": (503, {"detail": "Service Unavailable"}, None),
    "JSON-RPC error": (200, {"jsonrpc": "2.0", "id": 1, "error": {"code": -32000, "message": "busy"}}, None),
    "result without tools": (200, {"jsonrpc": "2.0", "id": 1, "result": {}}, None),
    "tools not a list": (200, {"jsonrpc": "2.0", "id": 1, "result": {"tools": None}}, None),
    "non-JSON 502": (502, None, "<html>Bad Gateway</html>"),
}


@SELF
def test_a_json_rpc_result_is_read_as_the_catalogue():
    assert _mcp(200, LISTED).tools_list() == TOOLS
    assert _mcp(200, LISTED).tool_names() == {t["name"] for t in TOOLS}
    assert _mcp(200, {"jsonrpc": "2.0", "id": 1, "result": {"tools": []}}).tools_list() == [], (
        "a result that lists no tools is an empty catalogue, read")


@SELF
@pytest.mark.parametrize("shape", sorted(FAILED_READS))
def test_any_other_reply_is_a_failed_read_that_is_inconclusive(shape):
    status, body, text = FAILED_READS[shape]
    with pytest.raises(McpError) as caught:
        _mcp(status, body, text).tools_list()
    # McpError for every caller that already catches it; Inconclusive for a check that does not, so
    # report_plugin records the row as unmeasured (rule 8) instead of red.
    assert isinstance(caught.value, Inconclusive), f"{shape}: a failed read must read as inconclusive"
    assert "tools/list" in str(caught.value)


def _ladder():
    from tests.mcp import test_trust_ladder
    return test_trust_ladder


@SELF
def test_a_failed_anonymous_read_does_not_pass_the_superset_check():
    check = _ladder().test_higher_tier_is_a_superset_of_lower
    with pytest.raises(Inconclusive):
        contextvars.copy_context().run(check, _mcp(401, {"detail": "Not authenticated"}), _mcp(200, LISTED))


@SELF
def test_a_failed_trusted_read_is_not_every_tool_lost():
    check = _ladder().test_higher_tier_is_a_superset_of_lower
    with pytest.raises(Inconclusive):
        contextvars.copy_context().run(check, _mcp(200, LISTED), _mcp(503, {"detail": "Service Unavailable"}))
    # And the read itself still judges: both listed, nothing lost, it passes.
    assert contextvars.copy_context().run(check, _mcp(200, LISTED), _mcp(200, LISTED)) is None


class _Rest:
    def get(self, path, **_):
        manifest = {"tools": [{"name": t["name"], "trust_tier": "unknown"} for t in TOOLS]}
        return _Answer(200, manifest)


@SELF
def test_a_failed_anonymous_read_does_not_pass_the_46_regression_check():
    check = _ladder().test_anonymous_receives_only_public_tools
    with pytest.raises(Inconclusive):
        contextvars.copy_context().run(check, _mcp(429, {"detail": "Rate limit exceeded"}), _Rest())
