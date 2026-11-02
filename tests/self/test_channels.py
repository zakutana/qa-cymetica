"""The three channels in one shape: what waits on us is what sweep would owe, on the status we just read."""

from __future__ import annotations

from qa import channels
from qa.paths import append_event, save_filed


def _row(report=7, status="pending", last_check="fail", verdicts=(), **extra):
    return {"key": f"k{report}", "report_ids": [report], "nodeids": ["x"], "their_status": {str(report): status},
            "last_check": last_check, "verdicts_sent": [{"report_id": report, "verdict": v, "at": "t"} for v in verdicts],
            "withdrawn": False, **extra}


def test_waiting_on_us_reads_the_status_the_journal_just_got():
    save_filed({"rows": [_row(status="pending")]})
    assert channels.state([])["bug"]["unanswered"] == []
    events = [{"type": "vendor_status", "report_id": 7, "status": "fixed", "at": "t"}]
    assert channels.state(events)["bug"]["unanswered"] == ["#7"]


def test_paid_counts_as_a_claimed_fix_like_in_sweep():
    save_filed({"rows": [_row(status="paid")]})
    assert channels.state([])["bug"]["unanswered"] == ["#7"]


def test_a_told_a_held_a_withdrawn_or_a_rejected_report_waits_on_nobody():
    save_filed({"rows": [_row(1, "paid", verdicts=["fail"]), _row(2, "paid", hold="his word"),
                         _row(3, "paid", withdrawn=True), _row(4, "invalid")]})
    state = channels.state([])["bug"]
    assert state["unanswered"] == [] and state["reports"] == 3


def test_a_pass_that_stopped_being_true_waits_on_us():
    save_filed({"rows": [_row(5, "pending", last_check="fail", verdicts=["pass"])]})
    assert channels.state([])["bug"]["unanswered"] == ["#5"]


def test_a_send_never_confirmed_is_named():
    save_filed({"rows": []})
    append_event({"type": "a2a_intent", "msg_id": "A2A-0001", "text": "q"})
    append_event({"type": "a2a_outcome", "msg_id": "A2A-0001", "outcome": "unknown"})
    append_event({"type": "a2a_intent", "msg_id": "A2A-0002", "text": "q"})
    append_event({"type": "a2a_outcome", "msg_id": "A2A-0002", "outcome": "accepted", "via": "theirs"})
    from qa.paths import read_events

    assert channels.state(read_events())["a2a"]["undelivered"] == ["A2A-0001"]
