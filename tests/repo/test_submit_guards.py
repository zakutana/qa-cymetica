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
