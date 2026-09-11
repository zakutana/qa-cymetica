"""NEXUS: the stopwatch the operator reads, not the one the check reads.

The deep pass of 2026-09-10 found `waited_seconds` starts when a POLL LOOP is
entered, and `nexus.py answer` enters a second one -- so a question asked at
10:00, given up on at 10:15 and picked up at 11:00 recorded "0 seconds". It
fixed the CHECK, which now times from the question's own timestamp.

It did not fix the LINE. On 2026-09-10 at 20:02, NEX-0009 was picked up 14.3
minutes after it was asked and `nexus.py answer` printed:

    answered after 0.0 min, 1 polls -- within their published 1-5 min

That "0.0" was wrong, and so was the first fix, which printed "OVER" for the
same row. The one poll already found the job done, so 14.3 minutes is when we
LOOKED, not how long it ran -- their job table says 155 s. Both readings
reported our own clock as theirs. What a poll record can prove is a pair of
bounds, and the second test below pins that.

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


def _asked_then(qid, asked, *polls):
    """A question and its polls, as nexus.py records them: (offset_s, status)."""
    from datetime import datetime, timedelta

    t0 = datetime.fromisoformat(asked)
    rows = [{"id": qid, "type": "question", "at": t0.isoformat()}]
    for offset, status in polls:
        rows.append({"id": qid, "type": "poll", "status": status,
                     "at": (t0 + timedelta(seconds=offset)).isoformat()})
    return rows


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_first_look_that_finds_it_done_is_an_upper_bound_not_a_latency(
        tmp_path, monkeypatch):
    """What the first version of this file got wrong, pinned the right way.

    It said NEX-0009 took 14.3 minutes and asserted `window_verdict(861) ==
    "OVER"`. NEX-0009 was asked with --no-wait at 19:48:11 and polled ONCE, at
    20:02:32, and that one poll already said done. So 861 s is when we LOOKED;
    the job could have finished at any moment before. Their job table,
    2026-09-10 21:27: that job completed in 155 s. The same mistake made
    NEX-0016's 13 minutes, and both went into the night report and two commit
    messages as their slowness.

    What a poll record can prove is a pair of bounds. The last poll still
    `running` is a lower bound on how long the job took; the first poll that
    found it `done` is an upper bound. A job is inside the window only if the
    upper bound is; it is late only if the lower bound is past it; anything
    else we did not measure, and says so.
    """
    mod = _nexus(tmp_path, monkeypatch)
    ceiling = mod.PUBLISHED_MINUTES[1] * 60

    # NEX-0009, exactly: one look, already done, 861 s after asking.
    looked_late = _asked_then("NEX-0009", "2026-09-10T19:48:11+00:00",
                              (861, "done"))
    assert mod.latency_bounds(looked_late, "NEX-0009") == (None, 861.0)
    assert mod.bounds_verdict(None, 861.0) == "unknown", (
        "one look that finds the job done says it took AT MOST 861 s. That "
        "is not a measurement of 861 s, and calling it OVER sent the vendor "
        "our own pickup delay as their latency")

    # NEX-0017, exactly: polled from the start, running at 103 s, done at 130.
    watched = _asked_then("NEX-0017", "2026-09-10T22:33:57+00:00",
                          (24, "running"), (50, "running"), (76, "running"),
                          (103, "running"), (130, "done"))
    lower, upper = mod.latency_bounds(watched, "NEX-0017")
    assert (lower, upper) == (103.0, 130.0)
    assert mod.bounds_verdict(lower, upper) == "within"

    # Genuinely late: we SAW it still running past their ceiling.
    slow = _asked_then("NEX-9001", "2026-09-10T10:00:00+00:00",
                       (ceiling + 100, "running"), (ceiling + 160, "done"))
    assert mod.bounds_verdict(*mod.latency_bounds(slow, "NEX-9001")) == "OVER"

    # Watched early, then looked away: running at 60 s, done by 900 s.
    gap = _asked_then("NEX-9002", "2026-09-10T10:00:00+00:00",
                      (60, "running"), (900, "done"))
    assert mod.bounds_verdict(*mod.latency_bounds(gap, "NEX-9002")) == "unknown"

    # A poll we could not read is not evidence that the job was running.
    blind = _asked_then("NEX-9003", "2026-09-10T10:00:00+00:00",
                        (400, "unread: ReadTimeout"), (420, "done"))
    assert mod.latency_bounds(blind, "NEX-9003") == (None, 420.0)

    # And nothing recorded at all is unknown, never the reassuring half.
    assert mod.bounds_verdict(None, None) == "unknown"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_failed_investigation_keeps_the_reason_they_gave(tmp_path, monkeypatch):
    """Five deep investigations ended `failed` on 2026-09-11 afternoon, and our
    timeline said only that word. Their poll answer carried the rest: an
    error sentence, `retryable`, `retry_after_s` and a fallback -- read by hand
    for NEX-0023, after the fail on #86 had already gone out saying "(NEX-0020:
    failed)". The check reads `error` off the give-up row; nothing wrote it."""
    mod = _nexus(tmp_path, monkeypatch)

    class Failed:
        def call(self, tool, arguments):
            assert tool == mod.POLL
            return {"success": True, "tool": "get_deep_answer", "result": {
                "success": True, "job_id": arguments["job_id"], "status": "failed",
                "error": "The deep-answer run could not be completed. Retry "
                         "ask_nexus_deep after retry_after_s seconds, or POST "
                         "https://cymetica.com/api/v1/bounty/qa-agent/ask for "
                         "an immediate shallower answer.",
                "retryable": True, "retry_after_s": 30,
                "fallback": {"sync": "POST https://cymetica.com/api/v1/bounty/qa-agent/ask"}}}

    mod._poll(Failed(), {"id": "NEX-9004", "job_id": "job-9004"})
    gave_up = [r for r in mod.load() if r.get("type") == "gave_up"]
    assert len(gave_up) == 1
    assert gave_up[0]["status"] == "failed"
    assert gave_up[0].get("error", "").startswith(
        "The deep-answer run could not be completed"), (
        "their reason for the failure is not on the give-up row")
    assert (gave_up[0].get("retryable"), gave_up[0].get("retry_after_s")) == (True, 30)
