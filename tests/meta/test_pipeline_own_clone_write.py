"""`update_bot_indicators`: the one MCP write on a clone's algorithm, and what the guard holds it to.

2026-10-03, bot research (docs/bots-research-plan.md). Skills and models cannot be equipped with an API
key, so the one lever on a clone's algorithm a key reaches is the parameters of the indicators it runs:
`update_bot_indicators(instance_id, indicator_name, params)`, "Override one indicator's parameters on one of
YOUR clones", `destructiveHint: true`, and NO `paper` argument -- so `paper_gated` cannot carry it, and until
today it was in no list and refused everywhere. Its read sibling `get_bot_indicators` (readOnlyHint: true)
is classified read, so a change is read back through the same guarded client.

The write is opened here and only here, at MUTATE, and only with exactly the arguments the tool documents:

* the three arguments and no fourth (a stray `force` or `paper` is refused, not ignored);
* `indicator_name` one of the seven the tool's description names;
* `params` a non-empty object of plain numbers (a string, a bool or a nested object is not a parameter).

That is all the CALL can say about itself. That the clone is a PAPER clone of ours is not in the call, so
it is the caller's floor, as it is for the settings PATCH: `scripts/clone.py indicators()` asks our record
and their row (`is_paper` twice) before it sends anything. Below MUTATE nothing changed: SAFE refuses by
name, PROBE forces empty arguments.

Split out of `test_guard_is_real.py` on purpose: that file is pinned by hash in `test_pipeline_abort.py`,
and this is a new gate, tested by its own file. A negative control must not need the thing it controls, so
every client here carries a transport that refuses to carry anything. Two functions, folded on the deep pass
of 2026-10-04 from eleven here and two in test_pipeline_bot_indicators_tools.py (tests/meta grows only by
replacement); every case they held is still a case.
"""

from __future__ import annotations

import httpx
import pytest

from qa.client import build_mcp_client
from qa.config import Identity
from qa.marks import qa
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier, SafetyViolation

ANON = Identity(name="anon")
TOOL = "update_bot_indicators"
GOOD = {"instance_id": "f6af3fd1-9532-4783-9a02-737f4c40fca7", "indicator_name": "rsi",
        "params": {"period": 21}}


class _Unsendable(httpx.BaseTransport):
    """Carries nothing. Reaching it means the guard let the call through."""

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        raise AssertionError(f"THE GUARD LET IT THROUGH: {request.method} {request.url}. Nothing was sent.")


def _call(tier: SafetyTier, arguments: dict, mutate: bool = True, tool: str = TOOL):
    registry = EndpointRegistry.load()
    registry.mutate_enabled = mutate
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    client = build_mcp_client(ANON, registry, None, inner=_Unsendable())
    token = CURRENT_TIER.set(tier)
    try:
        return client.call_raw(tool, arguments)
    finally:
        CURRENT_TIER.reset(token)
        client.http.close()


def _case_the_write_opens_only_at_mutate_and_only_for_this_tool():
    registry = EndpointRegistry.load()
    # The read is classified read; the write stays in no list (its gate is own_clone_write, beside the lists).
    assert registry.tool_class("get_bot_indicators") == "read"
    assert registry.tool_class(TOOL) == "unknown"

    # Below MUTATE, and at MUTATE without --allow-mutate: refused.
    for tier in (SafetyTier.SAFE, SafetyTier.PROBE):
        with pytest.raises(SafetyViolation):
            _call(tier, GOOD)
    with pytest.raises(SafetyViolation):
        _call(SafetyTier.MUTATE, GOOD, mutate=False)

    # The documented calls reach the transport.
    for arguments in (GOOD,
                      {**GOOD, "indicator_name": "macd", "params": {"fast": 8, "slow": 21, "signal": 9}},
                      {**GOOD, "indicator_name": "bollinger", "params": {"period": 20, "std_dev": 2.5}}):
        with pytest.raises(AssertionError, match="THE GUARD LET IT THROUGH"):
            _call(SafetyTier.MUTATE, arguments)

    # The gate opens this tool and no other, with the same arguments.
    for other in ("update_bot_settings", "toggle_bot_trading", "clone_bot", "fund_clone_bot",
                  "bb_file_request", "place_order"):
        with pytest.raises(SafetyViolation):
            _call(SafetyTier.MUTATE, dict(GOOD), tool=other)


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("arguments", [
    # a fourth argument is refused, not ignored
    {**GOOD, "paper": False}, {**GOOD, "paper": True}, {**GOOD, "force": True}, {**GOOD, "live": 1},
    # a missing one
    {k: v for k, v in GOOD.items() if k != "instance_id"},
    {k: v for k, v in GOOD.items() if k != "indicator_name"},
    {k: v for k, v in GOOD.items() if k != "params"},
    # an indicator the tool does not document
    *({**GOOD, "indicator_name": name} for name in ("adx", "vwap", "RSI ", "", None, 3, "rsi; drop")),
    # params that are not a non-empty object of plain numbers
    *({**GOOD, "params": params} for params in (
        {}, [], "period=21", None, {"period": "21"}, {"period": True}, {"period": None},
        {"period": [21]}, {"period": {"n": 21}})),
    # an instance id that is not a non-empty string
    *({**GOOD, "instance_id": bad} for bad in ("", None, 7, ["f6af3fd1"])),
])
def test_the_write_refuses_every_argument_it_does_not_document(arguments):
    with pytest.raises(SafetyViolation):
        _call(SafetyTier.MUTATE, arguments)


def _case_a_number_that_is_not_a_setting_never_leaves():
    # JSON cannot carry NaN or infinity, so the client refuses to serialise it before the transport is
    # reached; the guard refuses it too if that ever changes. The one thing that must not happen is the
    # transport being reached.
    for number in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises((SafetyViolation, ValueError)):
            _call(SafetyTier.MUTATE, {**GOOD, "params": {"period": number}})


# Folded on the deep pass of 2026-10-04 (tests/meta grows only by replacement): the gate's two plain tests became one; the parametrized refusal list stays its own test.


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_the_write_is_opened_at_mutate_only_and_refuses_what_it_does_not_document():
    _case_the_write_opens_only_at_mutate_and_only_for_this_tool()
    _case_a_number_that_is_not_a_setting_never_leaves()
