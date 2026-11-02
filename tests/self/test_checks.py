"""A run record into one word per check. Rule 10 lives here: what could not be measured is no verdict."""

from __future__ import annotations

from pathlib import Path

import pytest

from qa import checks


def _result(nodeid, outcome, phase="call", role="verdict", reason=None):
    return {"nodeid": nodeid, "outcome": outcome, "phase": phase, "reason": reason,
            "measurement": {"role": role, "reason": reason, "left": 1, "right": 0}, "failure_repr": None}


def test_each_outcome_reads_as_one_word():
    record = {"results": [_result("a", "passed"), _result("b", "failed"), _result("c", "inconclusive"),
                          _result("d", "skipped"), _result("e", "error", phase="setup"),
                          _result("f", "passed", role="evidence")]}
    read = checks.classify(record, ["a", "b", "c", "d", "e", "f", "gone"])
    assert {k: v["result"] for k, v in read.items()} == {
        "a": "pass", "b": "fail", "c": "inconclusive", "d": "inconclusive", "e": "inconclusive",
        "f": "inconclusive", "gone": "inconclusive"}


def test_a_failing_teardown_does_not_turn_a_passing_check_into_a_failure():
    record = {"results": [_result("a", "passed"), _result("a", "error", phase="teardown")]}
    assert checks.classify(record, ["a"])["a"]["result"] == "pass"


def test_a_row_passes_only_when_every_check_passes():
    assert checks.overall([{"result": "pass"}, {"result": "pass"}]) == "pass"
    assert checks.overall([{"result": "pass"}, {"result": "inconclusive"}]) == "inconclusive"
    assert checks.overall([{"result": "fail"}, {"result": "inconclusive"}]) == "fail"
    assert checks.overall([]) == "inconclusive"


def test_a_check_that_crashed_measured_nothing():
    """A KeyError is our check, not their defect: as a `fail` it would go to them as a verdict."""
    crashed = {**_result("a", "failed"), "exception": "KeyError", "failure_repr": "KeyError: 'rows'",
               "measurement": None}
    asserted = {**_result("b", "failed"), "exception": "AssertionError"}
    read = checks.classify({"results": [crashed, asserted]}, ["a", "b"])
    assert read["a"]["result"] == "inconclusive" and "KeyError" in read["a"]["reason"]
    assert read["b"]["result"] == "fail"


def test_a_real_pytest_run_is_recorded_with_its_outcomes(pytester, monkeypatch, tmp_path):
    from qa.paths import REPO_ROOT

    monkeypatch.setenv("PYTHONPATH", str(REPO_ROOT))
    out = tmp_path / "record.json"
    monkeypatch.setenv("QA_RUN_FILE", str(out))
    pytester.makepyfile(test_inner="""
        from qa.marks import Inconclusive
        from qa.measure import Measurement, conclude

        def test_ok():
            pass

        def test_red():
            conclude(Measurement(verdict="failed", reason="two is not three", left=2, right=3))

        def test_unsure():
            raise Inconclusive("the page did not answer")

        def test_crash():
            return {}["rows"]
    """)
    run = pytester.runpytest_subprocess("-p", "qa.report_plugin", "test_inner.py")
    assert run.ret == 1
    read = checks.classify(checks.load_record(out), ["test_inner.py::test_ok", "test_inner.py::test_red",
                                                     "test_inner.py::test_unsure", "test_inner.py::test_crash"])
    assert read["test_inner.py::test_crash"]["result"] == "inconclusive"
    assert read["test_inner.py::test_ok"]["result"] == "pass"
    assert read["test_inner.py::test_red"]["result"] == "fail"
    assert read["test_inner.py::test_red"]["reason"] == "two is not three"
    assert read["test_inner.py::test_unsure"]["result"] == "inconclusive"
    assert "did not answer" in read["test_inner.py::test_unsure"]["reason"]


def test_the_reason_is_never_our_traceback():
    repr_ = ("tests\\rest\\test_x.py:12: in test_x\n    assert helper(a) == 0\n"
             "E   assert 5 == 0\nE    +  where 5 = helper('secret path')\n")
    row = {**_result("a", "failed"), "exception": "AssertionError", "failure_repr": repr_, "measurement": None}
    reason = checks.classify({"results": [row]}, ["a"])["a"]["reason"]
    assert reason == "assert 5 == 0"


def test_a_volatile_check_that_fails_is_inconclusive():
    row = {**_result("a", "failed"), "exception": "AssertionError", "volatile": True}
    assert checks.classify({"results": [row]}, ["a"])["a"]["result"] == "inconclusive"


class _Done:
    def __init__(self, code, out=""):
        self.returncode, self.stdout, self.stderr = code, out, ""


def test_a_pytest_that_could_not_start_says_so(monkeypatch):
    monkeypatch.setattr(checks.subprocess, "run", lambda *a, **k: _Done(3, "SAFETY GUARD SELF-CHECK FAILED"))
    monkeypatch.setattr(checks, "REPO_ROOT", checks.REPO_ROOT)
    with pytest.raises(checks.CannotRun, match="SAFETY GUARD"):
        checks.vendor_checks()


def test_no_record_at_all_is_not_an_empty_run(monkeypatch):
    monkeypatch.setattr(checks.subprocess, "run", lambda *a, **k: _Done(1, "boom"))
    with pytest.raises(checks.CannotRun):
        checks.vendor_checks()


def test_a_collect_pass_leaves_no_run_record(monkeypatch):
    from qa.paths import state_dir

    def fake(argv, **kwargs):
        Path(kwargs["env"]["QA_RUN_FILE"]).write_text('{"collected": ["a::b"]}', encoding="utf-8")
        return _Done(0)

    monkeypatch.setattr(checks.subprocess, "run", fake)
    assert checks.vendor_checks() == ["a::b"]
    assert list((state_dir() / "runs").glob("*.json")) == []
