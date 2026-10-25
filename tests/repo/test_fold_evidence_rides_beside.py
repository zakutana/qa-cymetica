"""An evidence-only reading never becomes the row's reading.

Deep pass 2026-10-25, X01 (3/3). qa/fold.py's evidence branch says an
evidence-role measurement "measures and adjudicates nothing" -- and then called
`_measured_here()`, which replaced the row's `detail` and `provenance` with the
evidence run's, at any level, above the level-V gate that keeps even a real
pass from doing that (RO02). Live on 2026-10-25: CYM-a2a-first-pass-not-grounded
read "not asked ... QA_ALLOW_A2A_SEND" as its detail under a level-R run's
provenance -- which submit.py prints as MEASURED VALUES and verify.py takes as
measured_at. The reading stays beside the row: `check.evidence_only` names the
run whose record holds it.
"""

from __future__ import annotations

import pytest

from qa.marks import SafetyTier, qa
from tests.meta.test_pipeline_fold import CHECK_A, FP1, ledger, result, row, run


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("level", ["V", "R"])
def test_an_evidence_reading_leaves_the_rows_reading_alone(level):
    from qa.fold import fold

    failing = row("CYM-a", check_state="REPRODUCING", checks=[CHECK_A], pinned=FP1)
    failing["detail"] = {"reason": "what the failing run measured", "left": 3, "right": 0}
    failing["provenance"] = {"run_id": "run-fail", "measured_at": "2026-10-20T10:00:00+00:00"}

    ev = result(CHECK_A, "passed")
    ev["role"] = "evidence"
    ev["measurement"] = {"verdict": "passed", "role": "evidence",
                         "reason": "not asked: QA_ALLOW_A2A_SEND is not set"}

    r = fold(ledger(failing), run=run("run-ev", [ev], level=level), events=[])["findings"]["CYM-a"]

    assert r["detail"] == failing["detail"], "an evidence reading replaced the row's reading"
    assert r["provenance"] == failing["provenance"], "and claimed to have measured the row"
    assert r["check"]["evidence_only"] == "run-ev", "the reading rides beside, named by its run"
    assert r["check"]["state"] == "REPRODUCING"
