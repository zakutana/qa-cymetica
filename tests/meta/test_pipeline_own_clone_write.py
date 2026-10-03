"""`update_bot_indicators`: the one MCP write on a clone's algorithm, and what the guard holds it to.

2026-10-03, bot research (docs/bots-research-plan.md). Skills and models cannot be equipped with an API
key, so the one lever on a clone's algorithm a key reaches is the parameters of the indicators it runs:
`update_bot_indicators(instance_id, indicator_name, params)`, "Override one indicator's parameters on one of
YOUR clones", `destructiveHint: true`, and NO `paper` argument -- so `paper_gated` cannot carry it, and until
today it was in no list and refused everywhere.

It is opened here and only here, at MUTATE, and only with exactly the arguments the tool documents:

* the three arguments and no fourth (a stray `force` or `paper` is refused, not ignored);
* `indicator_name` one of the seven the tool's description names;
* `params` a non-empty object of plain numbers (a string, a bool or a nested object is not a parameter).

That is all the CALL can say about itself. That the clone is a PAPER clone of ours is not in the call, so
it is the caller's floor, as it is for the settings PATCH: `scripts/clone.py indicators()` asks our record
and their row (`is_paper` twice) before it sends anything. Below MUTATE nothing changed: SAFE refuses by
name, PROBE forces empty arguments.

Split out of `test_guard_is_real.py` on purpose: that file is pinned by hash in `test_pipeline_abort.py`,
and this is a new gate, tested by its own file. A negative control must not need the thing it controls, so
every client here carries a transport that refuses to carry anything.
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


def _client(mutate: bool):
    registry = EndpointRegistry.load()
    registry.mutate_enabled = mutate
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    return build_mcp_client(ANON, registry, None, inner=_Unsendable())


def _call(tier: SafetyTier, arguments: dict, mutate: bool = True):
    client = _client(mutate)
    token = CURRENT_TIER.set(tier)
    try:
        return client.call_raw(TOOL, arguments)
    finally:
        CURRENT_TIER.reset(token)
        client.http.close()


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_the_write_is_refused_below_mutate():
    with pytest.raises(SafetyViolation):
        _call(SafetyTier.SAFE, GOOD)
    with pytest.raises(SafetyViolation):
        _call(SafetyTier.PROBE, GOOD)


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_the_write_is_refused_at_mutate_unless_mutate_is_enabled():
    with pytest.raises(SafetyViolation):
        _call(SafetyTier.MUTATE, GOOD, mutate=False)


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_the_documented_call_reaches_the_transport_at_mutate():
    with pytest.raises(AssertionError, match="THE GUARD LET IT THROUGH"):
        _call(SafetyTier.MUTATE, GOOD)
    with pytest.raises(AssertionError, match="THE GUARD LET IT THROUGH"):
        _call(SafetyTier.MUTATE, {**GOOD, "indicator_name": "macd",
                                  "params": {"fast": 8, "slow": 21, "signal": 9}})
    with pytest.raises(AssertionError, match="THE GUARD LET IT THROUGH"):
        _call(SafetyTier.MUTATE, {**GOOD, "indicator_name": "bollinger",
                                  "params": {"period": 20, "std_dev": 2.5}})


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("extra", [{"paper": False}, {"paper": True}, {"force": True}, {"live": 1}])
def test_a_fourth_argument_is_refused_not_ignored(extra):
    with pytest.raises(SafetyViolation):
        _call(SafetyTier.MUTATE, {**GOOD, **extra})


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("missing", ["instance_id", "indicator_name", "params"])
def test_a_missing_argument_is_refused(missing):
    arguments = {k: v for k, v in GOOD.items() if k != missing}
    with pytest.raises(SafetyViolation):
        _call(SafetyTier.MUTATE, arguments)


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("name", ["adx", "vwap", "RSI ", "", None, 3, "rsi; drop"])
def test_an_indicator_the_tool_does_not_document_is_refused(name):
    with pytest.raises(SafetyViolation):
        _call(SafetyTier.MUTATE, {**GOOD, "indicator_name": name})


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("params", [
    {}, [], "period=21", None,
    {"period": "21"}, {"period": True}, {"period": None}, {"period": [21]}, {"period": {"n": 21}},
])
def test_params_must_be_a_non_empty_object_of_plain_numbers(params):
    with pytest.raises(SafetyViolation):
        _call(SafetyTier.MUTATE, {**GOOD, "params": params})


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("number", [float("nan"), float("inf"), float("-inf")])
def test_a_number_that_is_not_a_setting_never_leaves(number):
    # JSON cannot carry NaN or infinity, so the client refuses to serialise it before the
    # transport is reached; the guard refuses it too if that ever changes. Either way the
    # one thing that must not happen is the transport being reached.
    with pytest.raises((SafetyViolation, ValueError)):
        _call(SafetyTier.MUTATE, {**GOOD, "params": {"period": number}})


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_an_instance_id_must_be_a_non_empty_string():
    for bad in ("", None, 7, ["f6af3fd1"]):
        with pytest.raises(SafetyViolation):
            _call(SafetyTier.MUTATE, {**GOOD, "instance_id": bad})


def _other(tool: str):
    client = _client(True)
    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        client.call_raw(tool, dict(GOOD))
    finally:
        CURRENT_TIER.reset(token)
        client.http.close()


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("other", ["update_bot_settings", "toggle_bot_trading", "clone_bot",
                                   "fund_clone_bot", "bb_file_request", "place_order"])
def test_the_gate_opens_this_tool_and_no_other(other):
    with pytest.raises(SafetyViolation):
        _other(other)


@qa(component="meta.guard", tier=SafetyTier.SAFE, surface="meta")
def test_the_tool_is_still_classified_in_no_read_list():
    assert EndpointRegistry.load().tool_class(TOOL) == "unknown"
