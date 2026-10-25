"""A row a split makes is judged structurally at once, with the split as cause.

Deep pass 2026-10-25, X03 (3/3). Without a run, the fold's structural pass
(a row whose check is no pytest nodeid can never be adjudicated) ran BEFORE the
journal replay -- and `split_report` is the one event that brings a row into
being, inside that replay. So a split naming `scripts/inventory.py` made a row
that came out UNVERIFIED on the first fold and UNVERIFIABLE check_not_a_nodeid
on the second, with no transition: a CHECK move with neither run_id nor
event_id, and two folds of the same inputs disagreeing.

Two halves. The journal refuses such a split (scripts/withdraw.py goes through
it), and the fold, which is pure and may be handed one directly, judges a row
the replay made in the same fold, citing the split -- as it cites a rebind or a
retirement that leaves a row nothing to adjudicate.
"""

from __future__ import annotations

import pytest

from qa.marks import SafetyTier, qa
from tests.meta.test_pipeline_fold import CHECK_A, FP1, event, ledger, result, row, run

NOT_A_NODEID = "scripts/inventory.py"


def _source():
    src = row("A", check_state="REPRODUCING", checks=[CHECK_A], pinned=FP1)
    src["filing"].update({"refused": [], "verifications": []})
    return ledger(src)


def _events(nodeid=NOT_A_NODEID):
    return [
        event("filing_outcome", at="2026-09-01T00:00:00+00:00", key="k5", outcome="accepted",
              report_id=5, findings=["A"], evidence_id="e1"),
        event("filing_outcome", at="2026-09-01T00:00:01+00:00", key="k6", outcome="accepted",
              report_id=6, findings=["A"], evidence_id="e2"),
        event("split_report", at="2026-10-01T00:00:00+00:00", by="operator",
              source="scripts/withdraw.py", finding_id="A", to_id="B", report_id=6,
              nodeid=nodeid, reason="x"),
    ]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_journal_refuses_a_split_onto_a_check_that_is_no_nodeid():
    from qa.state import JournalError, _validate_event

    good = _events(nodeid="tests/rest/test_x.py::test_y")[-1]
    _validate_event(good)
    with pytest.raises(JournalError, match="nodeid"):
        _validate_event(dict(good, nodeid=NOT_A_NODEID))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_split_row_is_unverifiable_from_its_first_fold_citing_the_split():
    from qa.fold import fold
    from qa.state import event_id

    events = _events()
    once = fold(_source(), None, (), events)
    b = once["findings"]["B"]
    assert b["check"]["state"] == "UNVERIFIABLE", b["check"]
    assert b["check"]["unverifiable_reason"] == "check_not_a_nodeid"
    moves = [t for t in b["transitions"] if t["axis"] == "check"]
    assert [(t["from"], t["to"], t["cause"]) for t in moves] == [
        ("UNVERIFIED", "UNVERIFIABLE", {"event_id": event_id(events[-1])})], moves

    twice = fold(once, None, (), events)
    assert twice["findings"] == once["findings"], "two folds of the same inputs disagree"

    # And with a run in the same fold, as rule 12 refolds it: the run judges it.
    ran = fold(_source(), run("run-v", [result(CHECK_A, "failed")]), (), events)
    again = fold(ran, run("run-v", [result(CHECK_A, "failed")]), (), events)
    assert ran["findings"]["B"]["check"]["state"] == "UNVERIFIABLE"
    assert again["findings"] == ran["findings"]
