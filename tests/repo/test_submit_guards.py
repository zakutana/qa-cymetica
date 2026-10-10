"""What submit.py refuses to compose, in code rather than in prose.

B5 of the review of 2026-09-23 (3/3): `compose()` built a report for a
finding whatever its check said now -- INCONCLUSIVE, PASSING, UNVERIFIABLE --
while rule 10 ("inconclusive is never a defect") lived only in CLAUDE.md. A
report is filed about a defect our check reproduces; anything else is refused
by name before a word is composed.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _submit():
    spec = importlib.util.spec_from_file_location("submit_guards", REPO / "scripts" / "submit.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _findings(state: str, filing: str = "NOT_RAISED") -> dict:
    return {"findings": [{"id": "CYM-a", "title": "t", "checks": ["t::c"],
                          "provenance": {"measured_at": "2026-09-23T10:00:00+00:00"},
                          "check": {"state": state}, "filing": {"state": filing}}]}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("state", ["INCONCLUSIVE", "PASSING", "PASSING_UNPINNED",
                                   "UNVERIFIABLE", "UNVERIFIED", "CHECK_CHANGED"])
def test_a_report_is_composed_only_about_a_defect_our_check_reproduces(state):
    submit = _submit()
    report = {"key": "k", "findings": ["CYM-a"], "body": "b", "title": "t"}
    with pytest.raises(SystemExit) as refused:
        submit.compose(report, _findings(state), "footer")
    assert "REPRODUCING" in str(refused.value) and state in str(refused.value)

    # A report already filed is the archive's record of what we sent, composed
    # on every run and skipped by its title: not refused by this rule.
    try:
        submit.compose(report, _findings(state, filing="RAISED"), "footer")
    except SystemExit as other:
        assert "REPRODUCING" not in str(other), other
    except Exception:  # noqa: BLE001 -- the fixture is thin past this guard
        pass


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_finding_already_reported_is_reopened_never_filed_again():
    """[operator 2026-10-07] "mas otevrit stary bug kdyz je stejne a ne tvorit
    duplicitni". Six groups of paid reports shared one finding each (#49/#59,
    #53/#60/#74, #94/#96, #112/#136, #132/#137, #89/#98): the sweep wrote a new
    report for a recurrence because its skill said so. A finding that already
    has a report is refused here, whatever a skill or a session says, and the
    refusal names the way that does reopen it: a FAIL verification on the
    original (scripts/verify.py), which their server answers `reopened`."""
    submit = _submit()
    findings = {"findings": [
        {"id": "CYM-old", "filing": {"state": "FIX_CLAIMED",
                                     "reports": [{"report_id": 112}]}},
        {"id": "CYM-new", "filing": {"state": "NOT_RAISED", "reports": []}}]}
    reports = [{"key": "again", "findings": ["CYM-old"]},
               {"key": "mixed", "findings": ["CYM-new", "CYM-old"]},
               {"key": "fresh", "findings": ["CYM-new"]}]
    payloads = [(r["key"], {"title": r["key"]}) for r in reports]

    items, skipped = submit.select_items(payloads, reports, findings, seen=set())

    assert [i["key"] for i in items] == ["fresh"]
    assert {k for k, _ in skipped} == {"again", "mixed"}
    why = dict(skipped)["again"]
    assert "#112" in why and "verify.py" in why, why

    # The title dedupe still applies to what is left.
    items, skipped = submit.select_items(payloads, reports, findings, seen={"fresh"})
    assert items == [] and "title" in dict(skipped)["fresh"]

    # Deep pass 2026-10-10, B03: the ledger's reports are filled only by a FOLDED accepted
    # outcome. A filing whose outcome is unknown, accepted and not yet folded, or not written
    # at all, is in the journal only -- and a new key under another title citing the same
    # finding was filed again. The journal is read too; a rejected filing is not a report.
    def filing(key, fid, outcome=None, report_id=None):
        rows = [{"type": "filing_intent", "key": key, "findings": [fid]}]
        if outcome:
            rows.append({"type": "filing_outcome", "key": key, "findings": [fid],
                         "outcome": outcome, "report_id": report_id})
        return rows
    for events, why in ((filing("first", "CYM-new", "unknown"), "unknown"),
                        (filing("first", "CYM-new", "accepted", 201), "#201"),
                        (filing("first", "CYM-new"), "no outcome")):
        items, skipped = submit.select_items(payloads, reports, findings, seen=set(), events=events)
        assert "fresh" not in [i["key"] for i in items], (why, items)
        assert why in dict(skipped)["fresh"], (why, skipped)
    items, _ = submit.select_items(payloads, reports, findings, seen=set(),
                                   events=filing("first", "CYM-new", "rejected"))
    assert [i["key"] for i in items] == ["fresh"], "a rejected filing is not a report"
