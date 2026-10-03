"""`clone.py indicators()`: the parameters of the indicators a paper clone runs, changed one variant at a time.

2026-10-03, bot research (docs/bots-research-plan.md). Skills and models cannot be equipped with an API key
(their routes want a browser session), so the one lever on a clone's algorithm a key reaches is the
parameters of the indicators it already runs, through the MCP tool `update_bot_indicators`. The gate in
qa/safety.py holds what the CALL can say (exactly three arguments, a documented indicator, plain numbers --
tests/meta/test_pipeline_own_clone_write.py). This file holds what the call CANNOT say, which is the
caller's floor, the same three as the settings PATCH:

  * the parameters are inside bounds written down here, per indicator (a macd whose fast is not below its
    slow, an rsi period of 1, a bool, a string, an unknown name are refused before anything is built);
  * OUR record made the instance as a paper clone, and no room of ours is running on it -- a variant is a new
    room, never a change under the one being measured;
  * THEIR row says paper twice over (`startable`).

And a clone whose indicators changed after our pause has had its variant, so it may start again
(`restart_refusal`): without that, an indicator-only variant could never run.

Every refusal is proved with a second barrier: a client that fails the test if it is built.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import httpx
import pytest

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent

PAPER_ROW = {"id": "inst-1", "is_paper": True, "is_trading": False,
             "execution_economics": {"execution_class": "PAPER_SIMULATION"}}


def _clone(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    spec = importlib.util.spec_from_file_location("clone_indicators_under_test", REPO / "scripts" / "clone.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ours(mod, instance="inst-1", is_paper=True, outcome="accepted"):
    cid = mod._next_id(mod.load())
    mod._append({"id": cid, "type": "intent", "source_type": "wta_species", "source_id": "sp-1", "paper": True})
    mod._append({"id": cid, "type": "outcome", "outcome": outcome, "http_status": 200,
                 "clone_instance_id": instance, "is_paper": is_paper})


def _no_clients(mod, monkeypatch):
    def refuse(*args, **kwargs):
        raise AssertionError("the refusal did not hold: a live client was built")
    monkeypatch.setattr(mod, "build_client", refuse)
    monkeypatch.setattr(mod, "build_mcp_client", refuse)


class _Response:
    def __init__(self, status, body=None):
        self.status_code, self._body = status, body
        self.text = ""

    def json(self):
        return self._body


class _Rest:
    def __init__(self, rows, status=200):
        self.rows, self.status = rows, status

    def get(self, path, params=None):
        return _Response(self.status, self.rows)

    def close(self):
        pass


class _Mcp:
    """Their MCP, where the write is the thing under test. `effective` is what a read-back says."""

    def __init__(self, effective, update=None):
        self.effective, self.update, self.calls = effective, update, []
        self.http = self

    def call(self, tool, arguments=None):
        self.calls.append((tool, arguments))
        if tool == "get_bot_indicators":
            return {"success": True, "indicators": [{"name": "RSI", "effective": self.effective}]}
        if tool == "update_bot_indicators":
            if self.update is None:
                raise AssertionError(f"an indicator write was sent: {arguments}")
            return self.update
        raise AssertionError(f"unexpected tool {tool}")

    def close(self):
        pass


def _offline(mod, monkeypatch, rest, mcp):
    for name, value in (("load_dotenv", lambda: None), ("install_client_guard", lambda: None),
                        ("identities", lambda: {"trusted": None}),
                        ("build_client", lambda *a, **k: rest),
                        ("build_mcp_client", lambda *a, **k: mcp),
                        ("_snapshot", lambda c: {}), ("_capture", lambda *a, **k: None)):
        monkeypatch.setattr(mod, name, value)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_parameters_are_inside_bounds_written_down_per_indicator(tmp_path, monkeypatch):
    mod = _clone(tmp_path, monkeypatch)
    assert mod.safe_indicator("rsi", {"period": 21}) == {"period": 21}
    assert mod.safe_indicator("rsi", {"period": 7, "overbought": 75, "oversold": 25}) == {
        "period": 7, "overbought": 75, "oversold": 25}
    assert mod.safe_indicator("macd", {"fast": 8, "slow": 21, "signal": 9}) == {"fast": 8, "slow": 21, "signal": 9}
    assert mod.safe_indicator("bollinger", {"period": 20, "std_dev": 2.5}) == {"period": 20, "std_dev": 2.5}
    assert mod.safe_indicator("ema", {"period": 50}) == {"period": 50}
    for indicator, params, said in (
            ("adx", {"period": 14}, "adx"),                  # not an indicator the tool documents
            ("stochastic", {"period": 14}, "stochastic"),    # documented, but its parameter names are not read yet
            ("rsi", {}, "nothing"),
            ("rsi", {"periods": 14}, "periods"),             # an unknown name is a typo, not a setting
            ("rsi", {"period": 1}, "period"),
            ("rsi", {"period": 500}, "period"),
            ("rsi", {"period": True}, "period"),
            ("rsi", {"period": "14"}, "period"),
            ("rsi", {"overbought": 30, "oversold": 70}, "overbought"),   # the zones cross
            ("macd", {"fast": 30, "slow": 12}, "fast"),                  # fast must be below slow
            ("macd", {"fast": 12, "slow": 12}, "fast"),
            ("bollinger", {"std_dev": 9}, "std_dev"),
            ("ema", {"period": 0}, "period")):
        with pytest.raises(SystemExit, match=said):
            mod.safe_indicator(indicator, params)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_indicator_change_needs_our_paper_record_theirs_and_no_running_room(tmp_path, monkeypatch):
    mod = _clone(tmp_path, monkeypatch)
    change = ("rsi", {"period": 21})

    _no_clients(mod, monkeypatch)
    with pytest.raises(SystemExit, match="our record"):
        mod.indicators("inst-1", *change, confirm=True)
    _ours(mod, instance="inst-live", is_paper=False)
    with pytest.raises(SystemExit, match="our record"):
        mod.indicators("inst-live", *change, confirm=True)
    _ours(mod, instance="inst-refused", outcome="rejected")
    with pytest.raises(SystemExit, match="our record"):
        mod.indicators("inst-refused", *change, confirm=True)

    _ours(mod)
    import qa.rooms as qa_rooms
    rows = [{"type": "strategy", "id": "STR-0001", "origin": "NEX-0001", "title": "bot", "kind": "bot",
             "ref": "sp-1", "at": "2026-10-03T00:00:00+00:00"},
            {"type": "plan", "room": "STR-0001", "legs": [{"kind": "bot", "ref": "inst-1", "side": "bull", "share": 1.0}],
             "at": "2026-10-03T00:00:01+00:00"},
            {"type": "status", "room": "STR-0001", "status": "running", "why": "x", "at": "2026-10-03T00:00:02+00:00"}]
    (tmp_path / qa_rooms.path().name).write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    with pytest.raises(SystemExit, match="STR-0001"):
        mod.indicators("inst-1", *change, confirm=True)
    with open(tmp_path / qa_rooms.path().name, "a", encoding="utf-8") as handle:
        handle.write(json.dumps({"type": "status", "room": "STR-0001", "status": "stopped", "why": "window closed",
                                 "at": "2026-10-03T00:00:03+00:00"}) + "\n")

    # Their row: not paper, a live class, unreadable, not listed. The write is never sent.
    for rows_, status in (([{**PAPER_ROW, "is_paper": False}], 200),
                          ([{**PAPER_ROW, "execution_economics": {"execution_class": "LIVE_ONCHAIN"}}], 200),
                          (None, 503), ([], 200)):
        _offline(mod, monkeypatch, _Rest(rows_, status), _Mcp({"period": 14}))
        with pytest.raises(SystemExit):
            mod.indicators("inst-1", *change, confirm=True)
    assert not [r for r in mod.load() if r.get("kind") == "indicators"], "a refused change left a record"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_accepted_change_is_written_intent_outcome_after_and_read_back(tmp_path, monkeypatch):
    mod = _clone(tmp_path, monkeypatch)
    _ours(mod)
    mcp = _Mcp({"period": 14}, update={"success": True, "message": "RSI overridden"})
    _offline(mod, monkeypatch, _Rest([PAPER_ROW]), mcp)

    # Without --confirm: shown, nothing sent, nothing recorded.
    mod.indicators("inst-1", "rsi", {"period": 21}, confirm=False)
    assert not [t for t, _ in mcp.calls if t == "update_bot_indicators"]
    assert not [r for r in mod.load() if r.get("kind") == "indicators"]

    mcp.effective = {"period": 21}          # the read-back after the write says what they now run
    mod.indicators("inst-1", "rsi", {"period": 21}, confirm=True)
    sent = [a for t, a in mcp.calls if t == "update_bot_indicators"]
    assert sent == [{"instance_id": "inst-1", "indicator_name": "rsi", "params": {"period": 21}}], sent
    chain = [r for r in mod.load() if r.get("kind") == "indicators"]
    assert [r["type"] for r in chain] == ["intent", "outcome", "after"], chain
    assert chain[0]["body"] == {"indicator": "rsi", "params": {"period": 21}}
    assert chain[0]["their_is_paper"] is True
    assert chain[1]["outcome"] == "accepted"
    assert chain[2]["reread"] == "ok" and chain[2]["effective_matches"] is True


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_change_the_read_back_does_not_show_is_flagged_not_assumed(tmp_path, monkeypatch):
    mod = _clone(tmp_path, monkeypatch)
    _ours(mod)
    mcp = _Mcp({"period": 14}, update={"success": True})     # accepted, but the bot still runs 14
    _offline(mod, monkeypatch, _Rest([PAPER_ROW]), mcp)
    mod.indicators("inst-1", "rsi", {"period": 21}, confirm=True)
    after = [r for r in mod.load() if r.get("kind") == "indicators" and r["type"] == "after"][0]
    assert after["effective_matches"] is False


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_refused_write_is_recorded_rejected_and_a_failed_one_unknown(tmp_path, monkeypatch):
    mod = _clone(tmp_path, monkeypatch)
    _ours(mod)
    mcp = _Mcp({"period": 14}, update={"success": False, "error": "unknown indicator"})
    _offline(mod, monkeypatch, _Rest([PAPER_ROW]), mcp)
    mod.indicators("inst-1", "rsi", {"period": 21}, confirm=True)
    outcome = [r for r in mod.load() if r.get("kind") == "indicators" and r["type"] == "outcome"]
    assert outcome[-1]["outcome"] == "rejected"

    class Dies(_Mcp):
        def call(self, tool, arguments=None):
            if tool == "update_bot_indicators":
                raise httpx.ReadTimeout("read timed out")
            return super().call(tool, arguments)

    _offline(mod, monkeypatch, _Rest([PAPER_ROW]), Dies({"period": 14}))
    with pytest.raises(httpx.ReadTimeout):
        mod.indicators("inst-1", "rsi", {"period": 7}, confirm=True)
    outcome = [r for r in mod.load() if r.get("kind") == "indicators" and r["type"] == "outcome"]
    assert outcome[-1]["outcome"] == "unknown", "rule 9: a call that may have landed is unknown, never absent"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_indicator_change_after_our_pause_is_the_variant_that_lets_a_clone_start_again(tmp_path, monkeypatch):
    mod = _clone(tmp_path, monkeypatch)
    _ours(mod)

    def step(kind, outcome="accepted"):
        cid = mod._next_id(mod.load())
        mod._append({"id": cid, "type": "intent", "kind": kind, "instance_id": "inst-1"})
        mod._append({"id": cid, "type": "outcome", "kind": kind, "outcome": outcome, "http_status": 200})

    step("enable")
    step("disable")
    assert "no accepted settings" in (mod.restart_refusal("inst-1") or "") or "settings" in (mod.restart_refusal("inst-1") or "")
    step("indicators", outcome="rejected")
    assert mod.restart_refusal("inst-1"), "a refused indicator change is no variant"
    step("indicators")
    assert mod.restart_refusal("inst-1") is None, mod.restart_refusal("inst-1")
