"""A FAIL we owe is held when our own record says it is no longer true.

Deep pass 2026-10-25, O01 (3/3). `verify.owed()` built a FAIL from the pinned
fingerprint and the run that last adjudicated the row, and read nothing else.
Live on 2026-10-25: #217 (paid) owed a correction from level-R run 8a403f54,
which failed under pin 0bb1b3db -- while run 631598c5, a day later, PASSED the
check as repaired in c47f1e55, under a new fingerprint. The fold recorded that
pass beside the row (`check.last_exploratory_pass`: a level-R pass verifies
nothing, rule 6) and the obligation stood, so the next `verify.py --confirm`
would have told them our check still fails when our newest reading says it
passes. The repair was ours: the old check read "ignores t=" off a preview that
draws the right title.

So a FAIL is held, with the reason printed, when
  * a run of ours newer than the failing one passed the row's check, or
  * the definition differs from the one that failed: a newer run of ours ran it
    under another fingerprint, or the fingerprint pinned now is not the one the
    failing run ran (CHECK_CHANGED territory -- the repair is verified first).
The obligation stays in the ledger; a run that re-adjudicates the row settles it.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
NODE = "tests/rest/test_x.py::test_the_preview_draws_its_title"


def _verify():
    spec = importlib.util.spec_from_file_location("verify_holds_fail", REPO / "scripts" / "verify.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run(run_id, outcome, fingerprint, at):
    return {"run_id": run_id, "git_head": "8a403f54", "prereg_id": None,
            "started_at": at, "finished_at": at,
            "results": [{"nodeid": NODE, "outcome": outcome, "phase": "call", "role": "verdict",
                         "check_fingerprint": fingerprint,
                         "measurement": {"reason": f"{outcome} reading", "left": 1, "right": 0}}]}


def _ledger(pinned="fp-old", **check):
    return {"schema": 2, "findings": {"CYM-p": {
        "id": "CYM-p", "title": "t", "checks": [NODE],
        "provenance": {"run_id": "run-fail", "measured_at": "2026-10-23T17:14:36+00:00"},
        "check": {"state": "REPRODUCING", "pinned_fingerprint": pinned,
                  "failed_under": ["fp-old"],
                  "adjudicated_by": {"run_id": "run-fail", "at": "2026-10-23T17:14:36+00:00",
                                     "started_at": "2026-10-23T16:39:54+00:00"},
                  **check},
        "filing": {"state": "FIX_CLAIMED", "reports": [{"report_id": 217, "status": "paid"}],
                   "refused": [], "verifications": []},
        "obligations": {"correction_owed": [217], "reopen": [], "verification_owed": []}}}}


def _wire(verify, monkeypatch, runs):
    class Level:
        level, reasons = "R", ["git_dirty", "no_prereg"]

    def load(run_id):
        if run_id not in runs:
            raise KeyError(run_id)
        return runs[run_id]

    monkeypatch.setattr(verify, "load_run", load)
    monkeypatch.setattr(verify, "admissibility", lambda run: Level())
    monkeypatch.setattr(verify, "read_events", lambda: [])


FAILED = _run("run-fail", "failed", "fp-old", "2026-10-23T17:14:36+00:00")
PASSED_REPAIRED = _run("run-pass", "passed", "fp-new", "2026-10-24T09:21:26+00:00")
EXPLORATORY = {"run_id": "run-pass", "at": "2026-10-24T09:21:26+00:00"}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_fail_is_held_when_our_newer_run_passed_the_repaired_check(monkeypatch, capsys):
    """#217's own shape: failed under the pin, then passed, newer and repaired."""
    verify = _verify()
    _wire(verify, monkeypatch, {"run-fail": FAILED, "run-pass": PASSED_REPAIRED})

    work = verify.owed(_ledger(last_exploratory_pass=EXPLORATORY), None)

    assert work == [], "a FAIL went out although our newer run passed the check"
    said = capsys.readouterr().out
    assert "HOLD" in said and "CYM-p" in said and "#217" in said, said
    assert "run-pass" in said, "the hold names the run that passed"
    assert "definition" in said, "and says the definition moved under it"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_fail_is_held_when_our_newer_run_passed_the_same_definition(monkeypatch, capsys):
    """A pass of ours after the failure, same fingerprint: a level-R pass verifies
    nothing, and it is still not a reading we can send a FAIL against."""
    verify = _verify()
    same = _run("run-pass", "passed", "fp-old", "2026-10-24T09:21:26+00:00")
    _wire(verify, monkeypatch, {"run-fail": FAILED, "run-pass": same})

    assert verify.owed(_ledger(last_exploratory_pass=EXPLORATORY), None) == []
    assert "run-pass" in capsys.readouterr().out


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_fail_is_held_when_the_check_changed_under_it(monkeypatch, capsys):
    """No pass at all, but the definition moved: a newer run ran it under another
    fingerprint and could not conclude (not_checked_in), or the pin now is a hand pin
    on a definition the failing run never ran."""
    verify = _verify()
    errored = _run("run-new", "skipped", "fp-new", "2026-10-24T09:21:26+00:00")
    _wire(verify, monkeypatch, {"run-fail": FAILED, "run-new": errored})

    assert verify.owed(_ledger(not_checked_in="run-new"), None) == []
    said = capsys.readouterr().out
    assert "HOLD" in said and "definition" in said and "run-new" in said, said

    assert verify.owed(_ledger(pinned="fp-pin"), None) == []
    said = capsys.readouterr().out
    assert "HOLD" in said and "fp-pin" in said, said


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_fail_nothing_newer_contradicts_is_still_owed(monkeypatch, capsys):
    """The controls. Without them the tests above pass on a verify.py that holds
    every FAIL."""
    verify = _verify()
    older = _run("run-pass", "passed", "fp-new", "2026-10-22T08:00:00+00:00")
    same_skip = _run("run-new", "skipped", "fp-old", "2026-10-24T09:21:26+00:00")
    _wire(verify, monkeypatch, {"run-fail": FAILED, "run-pass": older, "run-new": same_skip})

    # Nothing beside the failure.
    [item] = verify.owed(_ledger(), None)
    assert (item["finding_id"], item["report_id"], item["verdict"]) == ("CYM-p", 217, "fail")
    # A pass OLDER than the failure is what the failure superseded.
    [item] = verify.owed(_ledger(last_exploratory_pass={"run_id": "run-pass",
                                                        "at": "2026-10-22T08:00:00+00:00"}), None)
    assert item["verdict"] == "fail"
    # A newer run that did not conclude, under the same definition, contradicts nothing.
    [item] = verify.owed(_ledger(not_checked_in="run-new"), None)
    assert item["verdict"] == "fail"
    assert "HOLD" not in capsys.readouterr().out
