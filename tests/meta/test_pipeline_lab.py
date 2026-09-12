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


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_notebook_is_outside_git():
    """It is appended to while a run may be in flight, and a dirty tree is a
    tree no run can reach level V from -- the reason nexus.jsonl and
    paper.jsonl are outside git too. scripts/keep.py snapshot is what stops
    that meaning "one disk"."""
    ignored = (REPO / ".gitignore").read_text(encoding="utf-8")
    assert "state/lab.jsonl" in ignored, (
        "the laboratory's notebook would dirty the tree mid-run")
