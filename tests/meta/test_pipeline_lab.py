"""The laboratory's brakes, in code rather than in the skill's prose.

A limit written in a skill is a limit the next session talks itself out of at
three in the morning. These are the ones that matter, each with the incident
behind it:

  * **paper only.** CLAUDE.md: Nexus's advice may not spend without `paper`. On
    2026-09-11 it asked us to send `mode=live` to prove the server would force
    paper back, and the answer was no.
  * **nothing while a deep pass is running.** The pass measures #85, #86 and
    #87 -- the newest Nexus answer, the last five questions, the newest trade.
    A question asked mid-run changes the subject the pass is verifying, and the
    verdict it sends the vendor is then about something else.
  * **a missing number is missing.** `get_strategy_returns` promises "a
    strategy with no runs returns a note, never a fabricated number". Ranking
    it as a zero would be us fabricating what they refused to.
  * **a cap on questions and rooms.** Nexus's own guide: an open-ended night
    "drifts, burns calls, and gives you no way to judge what it found".

The tools the ground-truth lane calls are checked against components.yaml
rather than by calling them: a test that reaches the vendor to prove a
classification would be the thing the classification exists to stop.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qa import lab
from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude
from qa.safety import EndpointRegistry

REPO = Path(__file__).resolve().parent.parent.parent

TRUTH_TOOLS = ("list_backtest_surfaces", "get_backtest_models",
               "get_strategy_returns")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_ground_truth_tools_are_read_and_an_unknown_one_is_refused():
    """The lane Nexus's guide starts with, and the floor under it.

    Two of the three were absent from every list in components.yaml until
    2026-09-12, which means the transport refused them: 0 calls in the whole
    evidence store, to the first step of the loop the vendor themselves told us
    to run.
    """
    registry = EndpointRegistry.load()
    missing = [tool for tool in TRUTH_TOOLS
               if registry.tool_class(tool) != "read"]
    unknown_allowed = registry.tool_class("definitely_not_a_tool") != "unknown"

    conclude(Measurement(
        verdict="failed" if missing or unknown_allowed else "passed",
        reason=(f"{', '.join(missing)} is not classified read, so the "
                f"transport refuses it" if missing else
                "a tool nobody classified is served at SAFE"
                if unknown_allowed else
                "all three ground-truth tools are read, and an unlisted tool "
                "is not"),
        left={"tools": list(TRUTH_TOOLS)}, right={"missing": missing},
        sources={"floor": "components.yaml: mcp_tools.read"}))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_missing_sharpe_is_not_a_zero():
    ranked = lab.rank([
        {"strategy": "bt-cryptobull-blue", "sharpe": 5.16, "max_drawdown": 1.8},
        {"strategy": "bt-nothing-ran"},
        {"strategy": "bt-hybrid2-red", "sharpe": 2.81, "max_drawdown": 3.7},
        {"strategy": "bt-hybrid2-blue", "sharpe": 2.81, "max_drawdown": 1.7},
    ])
    assert [r["strategy"] for r in ranked[:3]] == [
        "bt-cryptobull-blue", "bt-hybrid2-blue", "bt-hybrid2-red"], ranked
    assert ranked[-1]["strategy"] == "bt-nothing-ran"
    assert "unranked" in ranked[-1], "a strategy with no runs is not a zero"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_notebook_keeps_at_most_three_lessons_and_knows_an_open_session(
        tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    import importlib

    import qa.state

    importlib.reload(qa.state)
    importlib.reload(lab)

    opened = lab.open_session(mode="session")
    assert lab.open_sessions() == [opened["session"]]

    with pytest.raises(lab.LabError):
        lab.close_session(opened["session"],
                          lessons=["one", "two", "three", "four"], nextup=[])
    with pytest.raises(lab.LabError):
        lab.close_session("LAB-9999", lessons=[], nextup=[])

    lab.close_session(opened["session"], lessons=["one"],
                      nextup=["ask Nexus about STR-0001"])
    assert lab.open_sessions() == []
    assert lab.last_close()["next"] == ["ask Nexus about STR-0001"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_nothing_is_asked_or_bought_while_a_deep_pass_is_running():
    may, why = lab.may_ask(asked=0, pass_running=True)
    assert not may and "deep pass" in why.lower(), why

    may, why = lab.may_ask(asked=lab.CAPS["questions_per_session"],
                           pass_running=False)
    assert not may and "8" in why, why

    may, _ = lab.may_ask(asked=1, pass_running=False)
    assert may


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_order_is_capped_at_a_share_of_what_is_free():
    free = 89_000.0
    ok, why = lab.affordable(10_000, free_cash=free, running=2)
    assert ok, why

    ok, why = lab.affordable(20_000, free_cash=free, running=2)
    assert not ok and "15" in why, why

    ok, why = lab.affordable(1_000, free_cash=free,
                             running=lab.CAPS["running_experiments"])
    assert not ok and "running" in why.lower(), why

    ok, why = lab.affordable(1_000, free_cash=None, running=0)
    assert not ok and "could not" in why.lower(), (
        "an unreadable book is not an empty one -- rule 8")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_question_with_no_answer_is_what_the_next_cycle_finishes():
    """A foreground ask is killed at ten minutes by the tool that runs it,
    while nexus.py waits fifteen. The question is on their server either way;
    what is missing is our end of it, and the cycle is what closes that."""
    from datetime import datetime, timezone

    now = datetime(2026, 9, 12, 8, 0, tzinfo=timezone.utc)
    rows = [
        {"type": "question", "id": "NEX-0030", "at": "2026-09-12T06:00:00+00:00"},
        {"type": "answer", "id": "NEX-0030", "at": "2026-09-12T06:03:00+00:00"},
        {"type": "question", "id": "NEX-0031", "at": "2026-09-12T07:00:00+00:00"},
        {"type": "poll", "id": "NEX-0031", "at": "2026-09-12T07:01:00+00:00",
         "status": "running"},
        # Asked with --no-wait on the 10th and never picked up. Their
        # investigations take one to five minutes; this job id is gone, and a
        # cycle that polls it for ever is a loop that cannot finish.
        {"type": "question", "id": "NEX-0013", "at": "2026-09-10T21:50:00+00:00"},
    ]
    assert lab.outstanding(rows, now=now) == ["NEX-0031"]


def _series(start: str, values, hours: float = 1.0):
    """A card's index history: their shape, `[{t, index}, ...]`."""
    from datetime import datetime, timedelta, timezone

    first = datetime.fromisoformat(start.replace("Z", "+00:00"))
    if first.tzinfo is None:
        first = first.replace(tzinfo=timezone.utc)
    return [{"t": (first + timedelta(hours=hours * i)).isoformat(),
             "index": float(value)} for i, value in enumerate(values)]


def _acceptance(**over):
    base = {
        "at": "2026-09-05T00:00:00+00:00",
        "window_days": 2,
        "stop_pct": 5.0,
        "legs": [{"card": "card-a", "side": "bull", "share": 1.0,
                  "tp": 8.0, "sl": -5.0}],
        "benchmark_card": None,
    }
    base.update(over)
    return base


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_strategy_that_made_money_inside_its_stop_survives():
    now = "2026-09-07T01:00:00+00:00"
    series = {"card-a": _series("2026-09-05T00:00:00+00:00",
                                [100, 101, 102, 103, 104], hours=12)}
    said = lab.verdict(_acceptance(), series, now)
    assert said["verdict"] == "survived", said
    # Five points twelve hours apart over a two-day window: the last one falls
    # exactly on the closing edge and is inside it. This test said 3.0 first,
    # from counting four steps and assuming the edge was exclusive -- the code
    # was right and the expectation was not.
    assert round(said["return_pct"], 2) == 4.0, said
    assert said["max_drawdown_pct"] <= 5.0
    assert said["formula"], "a verdict records the formula that produced it"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_strategy_that_lost_is_refuted_and_says_by_how_much():
    now = "2026-09-07T01:00:00+00:00"
    series = {"card-a": _series("2026-09-05T00:00:00+00:00",
                                [100, 99, 97, 96, 95], hours=12)}
    said = lab.verdict(_acceptance(), series, now)
    assert said["verdict"] == "refuted", said
    assert said["return_pct"] < 0


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_stop_nexus_named_is_taken_when_the_index_crosses_it():
    """His own exit rule, applied to his own proposal. A strategy that would
    have been stopped out on day one is not rescued by the index coming back
    -- reading only the last point is how a backtest flatters itself."""
    now = "2026-09-07T01:00:00+00:00"
    series = {"card-a": _series("2026-09-05T00:00:00+00:00",
                                [100, 94, 97, 103, 104], hours=12)}
    said = lab.verdict(_acceptance(), series, now)
    assert said["legs"][0]["exit"] == "sl", said
    assert said["return_pct"] < 0, said
    assert said["verdict"] == "refuted"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_gap_in_the_data_is_inconclusive_and_never_a_loss():
    """Rule 8 in the laboratory: the console stopped sampling, so we do not
    know -- and "we do not know" may not be written into the record as a
    strategy that failed."""
    now = "2026-09-07T01:00:00+00:00"
    series = {"card-a": _series("2026-09-05T00:00:00+00:00", [100, 101],
                                hours=1)}
    said = lab.verdict(_acceptance(), series, now)
    assert said["verdict"] == "inconclusive", said
    assert said["coverage"] < 0.8


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_beating_nothing_is_not_beating_the_benchmark():
    """Cymetica's own guide asks whether a strategy beats BTC, not whether it
    is positive. A card that rose 1% while the benchmark rose 4% is refuted."""
    now = "2026-09-07T01:00:00+00:00"
    series = {
        "card-a": _series("2026-09-05T00:00:00+00:00",
                          [100, 100.25, 100.5, 100.75, 101], hours=12),
        "btc-card": _series("2026-09-05T00:00:00+00:00",
                            [100, 101, 102, 103, 104], hours=12),
    }
    said = lab.verdict(_acceptance(benchmark_card="btc-card"), series, now)
    assert said["benchmark_pct"] is not None and said["benchmark_pct"] > 3
    assert said["verdict"] == "refuted", said
    assert "benchmark" in said["why"].lower()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_window_that_has_not_closed_has_no_verdict_yet():
    now = "2026-09-05T06:00:00+00:00"
    series = {"card-a": _series("2026-09-05T00:00:00+00:00", [100, 101])}
    said = lab.verdict(_acceptance(), series, now)
    assert said["verdict"] == "open", said


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_room_goes_running_only_with_a_criterion_written_first(tmp_path,
                                                                 monkeypatch):
    """Preregistration, in the laboratory. A criterion written after the
    numbers are in is a criterion that fits them -- which is the whole reason
    this repository preregisters a run before it measures anything."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    import importlib

    import qa.rooms
    import qa.state

    importlib.reload(qa.state)
    rooms = importlib.reload(qa.rooms)

    # Long enough that the tab would call it answered, which is the same bar a
    # room opens on (qa/rooms.py::ANSWERED_CHARS).
    answer = ("Buy card-a, bull, 20% of the bankroll, take profit at 8%, stop "
              "at -5%. Backtest Sharpe 5.16 over 90 days, with a max drawdown "
              "of 1.8% and 275 trades. The basket is dominated by one asset, "
              "so size it against the headline rather than the coins, and do "
              "not add to it while the index is inside the stop. Reassess when "
              "the card resolves or the window closes, whichever is first.")
    (tmp_path / "nexus.jsonl").write_text(json.dumps({
        "type": "answer", "id": "NEX-1", "at": "2026-09-05T00:00:00+00:00",
        "text": answer}) + "\n", encoding="utf-8")

    room = rooms.open_strategy("NEX-1", "Karta A")["id"]
    with pytest.raises(rooms.RoomError):
        rooms.set_status(room, "running", "bought it")

    # A claim may only carry numbers his answer actually says.
    with pytest.raises(rooms.RoomError):
        rooms.set_claim(room, {"sharpe": "7.77"})
    rooms.set_claim(room, {"sharpe": "5.16", "take_profit": "8%"})

    rooms.set_acceptance(room, window_days=7, stop_pct=5.0,
                         why="his own stop, over his own horizon")
    rooms.set_status(room, "running", "TRD-0001 placed")

    # And it cannot be moved while it runs.
    with pytest.raises(rooms.RoomError):
        rooms.set_acceptance(room, window_days=30, stop_pct=20.0,
                             why="it would look better over a month")

    rows = rooms.load()
    kinds = [r["type"] for r in rows]
    assert "claim" in kinds and "acceptance" in kinds
    claim = [r for r in rows if r["type"] == "claim"][-1]
    assert claim["quoted"]["sharpe"] == "5.16"
    assert claim["numbers"]["sharpe"] == 5.16


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_notebook_is_outside_git():
    """It is appended to while a run may be in flight, and a dirty tree is a
    tree no run can reach level V from -- the reason nexus.jsonl and
    paper.jsonl are outside git too. scripts/keep.py snapshot is what stops
    that meaning "one disk"."""
    ignored = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert "state/lab.jsonl" in ignored, (
        "the laboratory's notebook would dirty the tree mid-run")
