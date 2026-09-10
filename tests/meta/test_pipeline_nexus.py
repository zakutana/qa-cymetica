"""NEXUS: the stopwatch the operator reads, not the one the check reads.

The deep pass of 2026-09-10 found `waited_seconds` starts when a POLL LOOP is
entered, and `nexus.py answer` enters a second one -- so a question asked at
10:00, given up on at 10:15 and picked up at 11:00 recorded "0 seconds". It
fixed the CHECK, which now times from the question's own timestamp.

It did not fix the LINE. On 2026-09-10 at 20:02, NEX-0009 was answered 14.3
minutes after it was asked and `nexus.py answer` printed:

    answered after 0.0 min, 1 polls -- within their published 1-5 min

Same false reassurance, same cause, one layer up -- and this is the layer a
person reads before deciding whether the channel is worth a message to the
vendor. A check nobody has run yet does not stop that sentence being wrong.

So the elapsed time is derived from the two recorded timestamps, which cannot
restart, and the printed verdict is computed from that. `waited_seconds` stays
in the record as what it always was -- how long THIS loop waited -- because
rewriting it would change the meaning of rows already written.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _nexus(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    spec = importlib.util.spec_from_file_location(
        "nexus_under_test", REPO / "scripts" / "nexus.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_elapsed_is_measured_from_the_question_not_from_this_poll_loop(
        tmp_path, monkeypatch):
    """NEX-0009, exactly: asked 19:48:11, answered 20:02:32, one poll."""
    mod = _nexus(tmp_path, monkeypatch)

    rows = [
        {"id": "NEX-0009", "type": "question",
         "at": "2026-09-10T19:48:11+00:00"},
        {"id": "NEX-0009", "type": "poll", "at": "2026-09-10T20:02:32+00:00",
         "waited_seconds": 0.0, "status": "done"},
    ]
    elapsed = mod.elapsed_since_asked(rows, "NEX-0009",
                                      "2026-09-10T20:02:32+00:00")
    assert elapsed is not None
    assert round(elapsed) == 861, (
        "14.35 minutes between the two recorded moments; the poll loop's own "
        "stopwatch said 0.0 and it had been entered a second time")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_late_answer_is_never_printed_as_within_their_window(
        tmp_path, monkeypatch):
    """The sentence a person reads before deciding to write to the vendor."""
    mod = _nexus(tmp_path, monkeypatch)
    low, high = mod.PUBLISHED_MINUTES

    assert mod.window_verdict(861) == "OVER", (
        f"14.3 minutes against a published {low}-{high}: printing 'within' "
        f"here is how a broken channel reads as a working one")
    assert mod.window_verdict(high * 60 - 1) == "within"

    # An unknown elapsed is not a fast one. The question's timestamp can be
    # missing on rows written before it was recorded, and the honest answer
    # there is that we cannot say -- not the reassuring half.
    assert mod.window_verdict(None) == "unknown"
