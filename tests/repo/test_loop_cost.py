"""What a day of the laboratory's /loop costs, read off the transcripts.

Plan v2, V6: a quiet firing is one short turn, and a loop day's working
firings stay at twenty or under while the tick still runs on every firing.
That is a claim about the transcripts, so it is measured there: on 2026-09-20
the loop fired 35 times at a median of 11 model calls each, all 533 on Opus,
while the skill's own frontmatter said `model: sonnet`. Nobody had counted.

The reader keeps to THIS project's transcripts. `transcript_rows()` globbed
`*cymetica*` and so also read the web-qa-agent project's (plan v1, L7); new
code does not inherit that.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
T0 = datetime(2026, 9, 24, 8, 0, tzinfo=timezone.utc)


def _module():
    spec = importlib.util.spec_from_file_location(
        "processes_loop", REPO / "scripts" / "processes.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _at(minutes: float) -> str:
    return (T0 + timedelta(minutes=minutes)).isoformat().replace("+00:00", "Z")


def _enqueue(minutes, content):
    return {"type": "queue-operation", "operation": "enqueue",
            "timestamp": _at(minutes), "content": content}


def _assistant(minutes, ident, model="claude-opus-5-5", block="text"):
    return {"type": "assistant", "timestamp": _at(minutes),
            "message": {"model": model, "id": ident, "role": "assistant",
                        "content": [{"type": block}]}}


def _result(minutes, text):
    return {"type": "user", "timestamp": _at(minutes),
            "message": {"role": "user", "content": [
                {"type": "tool_result", "tool_use_id": "t",
                 "content": text}]}}


def _lines(records):
    return [json.dumps(r, separators=(",", ":")) for r in records]


def _day(model="claude-opus-5-5"):
    return [
        _enqueue(0, "jdi do laborky"),
        # One call streamed as two records: counted once.
        _assistant(0.1, "msg_1", model, "thinking"),
        _assistant(0.1, "msg_1", model, "tool_use"),
        # The skill's own text is injected as the user; it quotes the line.
        {"type": "user", "isMeta": True, "timestamp": _at(0.2),
         "message": {"role": "user", "content": [
             {"type": "text", "text": "On `decide: none` write one line."}]}},
        _result(3, "tick LAB-0014 08:00: ...\n  question: not due\ndecide: none"),
        _assistant(3.1, "msg_2", model),
        _enqueue(20, "jdi do laborky"),
        _assistant(20.1, "msg_3", model),
        _enqueue(24, "<task-notification>\n<task-id>b1</task-id>"),
        _result(24.1, "tick ...\ndecide: answer NEX-0090 + question"),
        _assistant(24.2, "msg_4", model),
        _assistant(25, "msg_5", model),
        _assistant(26, "msg_6", model),
        # The operator speaks: what follows is theirs, not the loop's.
        _enqueue(30, "co ted?"),
        _assistant(30.1, "msg_7", model),
        _enqueue(40, "/loop 20m jdi do laborky"),
        _assistant(40.1, "msg_8", model),
        # Typed while the session was idle, it never went through the queue.
        {"type": "user", "timestamp": _at(41),
         "message": {"role": "user", "content": "a jak to vypada?"}},
        _assistant(41.1, "msg_9", model),
    ]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_firing_is_counted_in_calls_with_its_model_and_its_decision():
    procs = _module()
    firings = procs.loop_firings(_lines(_day()))

    assert [f["calls"] for f in firings] == [2, 4, 1], firings
    assert firings[0]["decide"] == [], "the tick said none"
    assert firings[1]["decide"] == ["answer NEX-0090", "question"], firings[1]
    assert firings[0]["model"] == "claude-opus-5-5"
    assert firings[2]["decide"] is None, "a firing whose tick nobody saw"

    # R01 (deep pass of 2026-09-24, 3/3): "pokračuj" TYPED into a plan
    # session is the operator saying carry on, not the laboratory's tick --
    # two plan sessions (101 and 151 Opus calls) were counted as lab firings
    # and fed the /model sonnet reminder. A /loop that queues it is the tick
    # by its old name and still counts.
    typed = [{"type": "user", "timestamp": _at(0),
              "message": {"role": "user", "content": "Pokracuj"}},
             _assistant(0.1, "msg_p1"), _assistant(0.2, "msg_p2")]
    assert procs.loop_firings(_lines(typed)) == [], "a typed carry-on became a lab tick"
    queued = [_enqueue(0, "pokracuj"), _assistant(0.1, "msg_q1")]
    assert len(procs.loop_firings(_lines(queued))) == 1


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_loop_day_says_how_many_firings_worked_and_what_a_quiet_one_cost():
    """The done-when, as numbers: working firings in the day (the tick said
    something other than none) and the calls a quiet firing took."""
    procs = _module()
    day = procs.loop_days(procs.loop_firings(_lines(_day())))
    assert list(day) == ["2026-09-24"]
    row = day["2026-09-24"]
    assert row["firings"] == 3 and row["working"] == 1 and row["quiet"] == 1
    assert row["unknown"] == 1
    assert row["quiet_calls_max"] == 2 and row["calls"] == 7
    assert row["models"] == {"claude-opus-5-5": 7}, row


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_only_this_projects_transcripts_are_read(tmp_path):
    procs = _module()
    ours = tmp_path / ".claude" / "projects" / procs.project_slug()
    other = tmp_path / ".claude" / "projects" / "C--Users-x-cymetica-qa-agent-web-qa-agent"
    ours.mkdir(parents=True)
    other.mkdir(parents=True)
    (ours / "a.jsonl").write_text("\n".join(_lines(_day())), encoding="utf-8")
    (other / "b.jsonl").write_text("\n".join(_lines(_day())), encoding="utf-8")

    found = procs.project_transcripts(home=tmp_path)

    assert [p.name for p in found] == ["a.jsonl"], found
    assert procs.project_slug().endswith("-qa-cymetica")
