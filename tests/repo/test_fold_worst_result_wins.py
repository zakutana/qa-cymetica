"""One check, two results: the worst one is what the run measured.

Deep pass 2026-10-25, X02 (3/3). qa/fold.py keyed a run's results by nodeid
with a dict comprehension, so the LAST result for a check won. pytest reports
a check's call and its teardown separately, and qa/report_plugin.py records
both when the teardown fails: a call `failed` followed by a teardown `error`
for one nodeid. The error came last, the fold read "not checked in", and the
failure the call measured -- a regression, and the reopen it owes -- was lost.
Latent (0 of 562 records on 2026-10-25 hold two results for one check), so the
committed ledger refolds the same.

The worst outcome wins: failed > error > inconclusive > skipped > passed, the
call phase on a tie, since it is the one carrying the measurement. Every pair
that is not a failed call keeps what last-wins gave. scripts/withdraw.py pins a
fingerprint "exactly as the fold computes it", so it reads the same selection.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from qa.marks import SafetyTier, qa
from tests.meta.test_pipeline_fold import CHECK_A, FP1, ledger, result, row, run

REPO = Path(__file__).resolve().parent.parent.parent
FP_AST = "sha256:teardown-ast-hash"


def _teardown_error():
    r = result(CHECK_A, "error", fingerprint=FP_AST, phase="teardown")
    r["measurement"] = None
    return r


def _failed_call():
    r = result(CHECK_A, "failed")
    r["measurement"] = {"verdict": "failed", "reason": "the regression", "left": 2,
                        "right": 0, "role": "verdict"}
    return r


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_failed_call_stays_failed_whatever_its_teardown_did():
    from qa.fold import fold

    passing = ledger(row("CYM-a", check_state="PASSING", checks=[CHECK_A], pinned=FP1))
    after = fold(passing, run=run("run-v", [_failed_call(), _teardown_error()]), events=[])
    r = after["findings"]["CYM-a"]

    assert r["check"]["state"] == "REPRODUCING", r["check"]
    assert "not_checked_in" not in r["check"], "the teardown's error hid the call's failure"
    assert r["check"]["pinned_fingerprint"] == FP1, "pinned the teardown's AST hash"
    assert r["detail"]["reason"] == "the regression"
    assert [g["run_id"] for g in r["regressions"]] == ["run-v"], "the regression was lost"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_passing_call_with_a_failed_teardown_still_checks_nothing():
    """The control, and the behaviour that stays: an error measured nothing."""
    from qa.fold import fold

    passing = ledger(row("CYM-a", check_state="REPRODUCING", checks=[CHECK_A], pinned=FP1))
    after = fold(passing, run=run("run-v", [result(CHECK_A, "passed"), _teardown_error()]),
                 events=[])
    check = after["findings"]["CYM-a"]["check"]
    assert check["state"] == "REPRODUCING" and check["not_checked_in"] == "run-v", check


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_withdraw_pins_what_the_fold_reads():
    spec = importlib.util.spec_from_file_location("withdraw_worst", REPO / "scripts" / "withdraw.py")
    withdraw = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(withdraw)

    record = run("run-v", [_failed_call(), _teardown_error()])
    assert withdraw.fingerprint_from_run(record, [CHECK_A]) == FP1
