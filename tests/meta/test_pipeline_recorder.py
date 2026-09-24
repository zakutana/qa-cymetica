"""REC: the run record is a faithful, three-valued account of what ran.

Phase 1 of the hardening plan. These tests are written BEFORE the recorder is
changed and several of them fail at commit 6aa0517 on purpose -- that failure
is the evidence that the defect they pin was real:

  test_inconclusive_survives_to_run_record   fails: outcome 'failed', reason None
      The recorder was a trylast hookwrapper, so it resumed BEFORE the conftest
      wrapper that marks Inconclusive, and wrote every inconclusive check as
      failed. 53 committed results carry that contamination.
  test_phase_and_skip_are_distinct_outcomes  fails: setup error recorded as failed
  test_exit_status_agrees_with_results       fails: exit 0 beside totals {failed:1}
  test_records_collected_nodeids...          fails: no 'collected' key
  test_evidence_ids_are_linked_at_call_time  fails: 0 ids (read at teardown)
  test_measurement_conclude...               fails: qa.measure does not exist

Every inner session is a subprocess with the REAL conftest, offline
(QA_OFFLINE), redirected (QA_STATE_DIR), and never touches the committed
state/. Inner tests live under tests/t/, not tests/meta/, so a failing one
does not trigger the guard's abort.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import textwrap
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parents[2]
CONFTEST = REPO / "tests" / "conftest.py"

INNER_HEADER = """
from qa.marks import Inconclusive, SafetyTier, qa
import pytest

TAG = dict(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
"""


def _run_inner(pytester, tmp_path: Path, body: str, conftest_extra: str = "",
               args: tuple[str, ...] = ()) -> tuple[str, dict]:
    """Run one inner pytest session and return (combined output, run record)."""
    pytester.makefile(".toml", pyproject=(REPO / "pyproject.toml").read_text(encoding="utf-8"))
    pytester.mkpydir("tests")
    (pytester.path / "tests" / "conftest.py").write_text(
        CONFTEST.read_text(encoding="utf-8") + "\n" + textwrap.dedent(conftest_extra),
        encoding="utf-8")
    t = pytester.path / "tests" / "t"
    t.mkdir()
    (t / "test_inner.py").write_text(INNER_HEADER + textwrap.dedent(body), encoding="utf-8")

    state = tmp_path / "state"
    env = dict(os.environ)
    env.update({
        "PYTHONPATH": str(REPO),
        "QA_OFFLINE": "1",
        "QA_STATE_DIR": str(state),
        "QA_EVIDENCE_DIR": str(tmp_path / "evidence"),
        "PYTHONIOENCODING": "utf-8",
    })
    proc = subprocess.run(
        [sys.executable, "-m", "pytest", "tests", "-q", "-p", "no:cacheprovider", *args],
        cwd=pytester.path, env=env, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180,
    )
    out = proc.stdout + proc.stderr
    records = sorted((state / "runs").glob("run-*.json"))
    assert len(records) == 1, f"expected exactly one run record, got {records}\n{out}"
    return out, json.loads(records[0].read_text(encoding="utf-8"))


def _result(run: dict, name: str) -> dict:
    hits = [r for r in run["results"] if r["nodeid"].endswith(f"::{name}")]
    assert len(hits) == 1, f"{name}: {[r['nodeid'] for r in run['results']]}"
    return hits[0]


# ---------------------------------------------------------------------------
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_inconclusive_survives_to_run_record(pytester, tmp_path):
    out, run = _run_inner(pytester, tmp_path, """
        @qa(**TAG)
        def test_cannot_measure():
            raise Inconclusive("window exceeded")
    """)
    r = _result(run, "test_cannot_measure")
    assert r["outcome"] == "inconclusive", f"outcome {r['outcome']!r}, reason {r.get('reason')!r}\n{out}"
    assert r["reason"] == "window exceeded"
    assert run["totals"].get("inconclusive") == 1 and "failed" not in run["totals"]
    # pytest itself must still treat it as a skip, not a failure.
    assert "1 skipped" in out and "failed" not in out.splitlines()[-1]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_phase_and_skip_are_distinct_outcomes(pytester, tmp_path):
    out, run = _run_inner(pytester, tmp_path, """
        @pytest.fixture
        def broken():
            raise RuntimeError("fixture exploded")

        @qa(**TAG)
        def test_setup_error(broken):
            pass

        @qa(**TAG)
        def test_skipped_inside():
            pytest.skip("nope")

        @qa(**TAG)
        def test_passes():
            pass
    """)
    err = _result(run, "test_setup_error")
    assert err["outcome"] == "error" and err["phase"] == "setup", err
    skip = _result(run, "test_skipped_inside")
    assert skip["outcome"] == "skipped" and skip["reason"] == "nope", skip
    ok = _result(run, "test_passes")
    assert ok["outcome"] == "passed" and ok["phase"] == "call", ok
    assert run["totals"] == {"error": 1, "skipped": 1, "passed": 1}, run["totals"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("body,exit_status,expected", [
    ("""
        @qa(**TAG)
        def test_fails():
            assert False
    """, 1, {"failed": 1}),
    ("""
        @qa(**TAG)
        def test_ok():
            pass
    """, 0, {"passed": 1}),
    ("""
        @qa(**TAG)
        def test_inc():
            raise Inconclusive("no source")
    """, 0, {"inconclusive": 1}),
], ids=["failed", "passed", "inconclusive"])
def test_exit_status_agrees_with_results(pytester, tmp_path, body, exit_status, expected):
    """A record must be internally consistent: exit status and totals agree.

    At 6aa0517 the inconclusive case records exit 0 beside totals {failed: 1},
    which is the shape of run-20260904T131713Z-7518e8e.json.
    """
    _, run = _run_inner(pytester, tmp_path, body)
    assert run["exit_status"] == exit_status
    assert run["totals"] == expected, run["totals"]
    assert (run["exit_status"] == 1) == any(r["outcome"] == "failed" for r in run["results"])
    assert run["record_integrity"]["consistent"] is True, run["record_integrity"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_records_collected_nodeids_and_check_fingerprint(pytester, tmp_path):
    _, run = _run_inner(pytester, tmp_path, """
        @qa(**TAG)
        def test_a():
            pass

        @qa(**TAG)
        def test_b():
            '''A docstring must not change the fingerprint.'''
            pass

        def _limit():
            return _floor() + 2

        def _floor():
            return 1

        @qa(**TAG)
        def test_c():
            assert _limit() == 3
    """)
    # A8 of the review of 2026-09-23 (3/3): the helpers a check calls are
    # part of what it asserts, and check_fingerprint never saw them, so
    # verify.py told the vendor "the same test" after a helper was rewritten.
    # They are hashed apart, transitively, beside the unchanged fingerprint --
    # changing check_fingerprint itself would move every row to CHECK_CHANGED.
    helpers = {r["nodeid"].rsplit("::", 1)[-1]: r.get("helpers_fingerprint")
               for r in run["results"]}
    assert all(isinstance(h, str) and len(h) == 64 for h in helpers.values()), helpers
    assert helpers["test_c"] != helpers["test_a"] == helpers["test_b"], helpers
    assert run.get("schema") == 2
    collected = run["collected"]
    assert any(n.endswith("::test_a") for n in collected) and any(n.endswith("::test_b") for n in collected)
    assert set(r["nodeid"] for r in run["results"]) <= set(collected)
    for r in run["results"]:
        fp = r["check_fingerprint"]
        assert isinstance(fp, str) and len(fp) == 64 and int(fp, 16) >= 0, r
    # Different bodies -> different fingerprints; same body -> same. Both pass;
    # test_b's docstring is stripped, so its fingerprint equals test_a's.
    assert _result(run, "test_a")["check_fingerprint"] == _result(run, "test_b")["check_fingerprint"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_evidence_ids_are_linked_at_call_time(pytester, tmp_path):
    """The evidence a check captured is on ITS result, read in the call phase.

    At 6aa0517 evidence ids were read from item.stash_evidence, which the
    autouse fixture sets in its finalizer -- after the call-phase report was
    already written. 0 of 388 committed results carry an evidence id.
    """
    _, run = _run_inner(pytester, tmp_path, """
        import os, pathlib
        import httpx
        from qa.evidence import EvidenceStore
        from qa.safety import EndpointRegistry, SafetyTransport

        @qa(**TAG)
        def test_makes_one_request():
            store = EvidenceStore("run-inner", root=pathlib.Path(os.environ["QA_EVIDENCE_DIR"]))
            transport = SafetyTransport(
                inner=httpx.MockTransport(lambda r: httpx.Response(200, text="hello")),
                registry=EndpointRegistry.load(), evidence=store,
            )
            transport.handle_request(httpx.Request("GET", "https://cymetica.com/llms.txt"))
    """)
    r = _result(run, "test_makes_one_request")
    blobs = list((tmp_path / "evidence" / "sha256").glob("*/*.json"))
    assert len(blobs) == 1, blobs
    digest = blobs[0].stem
    assert r["evidence_ids"] == [digest], r["evidence_ids"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_totals_match_pytest_summary(pytester, tmp_path):
    """All five outcome kinds in one session: our totals and pytest's agree."""
    out, run = _run_inner(pytester, tmp_path, """
        @pytest.fixture
        def broken():
            raise RuntimeError("boom")

        @qa(**TAG)
        def test_passed(): pass

        @qa(**TAG)
        def test_failed(): assert False

        @qa(**TAG)
        def test_inconclusive(): raise Inconclusive("x")

        @qa(**TAG)
        def test_skipped(): pytest.skip("s")

        @qa(**TAG)
        def test_error(broken): pass
    """)
    assert run["totals"] == {"passed": 1, "failed": 1, "inconclusive": 1, "skipped": 1, "error": 1}, run["totals"]
    summary = [l for l in out.splitlines() if l.strip()][-1]
    # pytest counts our inconclusive as a skip.
    for piece in ("1 failed", "1 passed", "2 skipped", "1 error"):
        assert piece in summary, summary


# ---------------------------------------------------------------------------
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_measurement_conclude_couples_verdict_to_outcome():
    """A check's verdict and pytest's outcome are one value, not two."""
    from qa.marks import Inconclusive
    from qa.measure import Measurement, conclude

    ok = Measurement(verdict="passed", left=1, right=1)
    assert conclude(ok) is None

    with pytest.raises(AssertionError) as exc:
        conclude(Measurement(verdict="failed", left=1, right=2, reason="values differ"))
    assert "values differ" in str(exc.value)

    with pytest.raises(Inconclusive) as exc:
        conclude(Measurement(verdict="inconclusive", reason="source unreadable"))
    assert "source unreadable" in str(exc.value)

    with pytest.raises(ValueError):
        Measurement(verdict="maybe")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_transport_failure_is_inconclusive_not_a_defect(pytester, tmp_path):
    """A read timeout means we stopped listening, not that they answered
    wrongly. Recorded as a failure it becomes a finding about their platform
    on the strength of our network -- and one did: a ReadTimeout on
    /api/v1/vaix/prices minted a defect row on the dashboard."""
    _, run = _run_inner(pytester, tmp_path, """
        import httpx

        @qa(**TAG)
        def test_the_network_gave_up():
            raise httpx.ReadTimeout("the read operation timed out")

        @qa(**TAG)
        def test_a_real_disagreement():
            assert 46 == 25, "documented 46, served 25"
    """)

    by_id = {r["nodeid"].rsplit("::", 1)[-1]: r for r in run["results"]}
    assert by_id["test_the_network_gave_up"]["outcome"] == "inconclusive"
    assert "ReadTimeout" in by_id["test_the_network_gave_up"]["reason"]
    assert by_id["test_a_real_disagreement"]["outcome"] == "failed", \
        "a genuine assertion failure must still be a failure"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_ratelimit_budget_reaches_the_run_record(pytester, tmp_path):
    """Critique gap 11. Every committed run record carries `ratelimit: {}`,
    because the recorder read a session attribute nothing ever set. A run the
    quota cut short therefore looked exactly like a complete one -- and a
    partial run may not verify anything."""
    _, run = _run_inner(pytester, tmp_path, """
        from qa.safety import RateLimitBudget

        @qa(**TAG)
        def test_spends_some_quota():
            budget = RateLimitBudget(stop_at_fraction=0.6)
            budget.before_request()
            budget.before_request()
    """)

    assert run["ratelimit"], "the run record still says nothing about the quota"
    assert run["ratelimit"]["requests"] == 2
    assert run["ratelimit"]["exhausted"] is False
    assert run["record_integrity"]["budget_truncated"] is False


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_option_value_is_not_a_test_path():
    """selector_full decided the suite was narrowed by reading --prereg's value.

    It filtered the raw command line on "does not start with a dash", which
    counts OPTION VALUES as positional paths. Level V requires a
    preregistration, so every run that could ever have used this carried
    `--prereg PRE-NNNN`, positional came out as ["tests", "PRE-0045"], and
    selector_full was False. 0 of 39 committed run records have it set.

    What that switched off is not cosmetic. The fold's check_missing branch is
    the only thing that can say a check is GONE -- renamed, reparametrised,
    deleted -- rather than merely not run this time, and it is gated on
    selector_full. It had never once been able to fire, while the sweep skill
    told the operator to run the full width precisely to reach it.

    Reads config.args now, which is what pytest resolved the positional
    arguments to, and which falls back to the testpaths ini value when none
    were given.
    """
    import types

    from qa.report_plugin import _selector_is_full

    def config(raw, resolved, **parsed):
        return types.SimpleNamespace(
            invocation_params=types.SimpleNamespace(args=tuple(raw)),
            args=list(resolved), option=types.SimpleNamespace(**parsed))

    assert _selector_is_full(config(
        ["tests", "--prereg", "PRE-0045", "-q"], ["tests"])), \
        "the preregistration id was read as a test path again"
    assert _selector_is_full(config(["-q"], ["tests"])), \
        "no positional argument means the testpaths default, which is the suite"
    # A4 of the review of 2026-09-23 (3/3): these narrow collection too, and
    # counted as full they let a partial run call a check GONE.
    for narrowing in (["--deselect", "tests/a.py::t"], ["--deselect=tests/a.py::t"],
                      ["--ignore", "tests/rest"], ["--ignore-glob=*x*"],
                      ["--lf"], ["--last-failed"], ["--sw"], ["--stepwise"]):
        assert not _selector_is_full(config(["tests", *narrowing], ["tests"])), narrowing

    assert not _selector_is_full(config(
        ["tests/meta", "a.py::t", "--prereg", "P"], ["tests/meta", "a.py::t"]))
    for narrowing in ("-k", "-m"):
        assert not _selector_is_full(config(
            ["tests", narrowing, "foo"], ["tests"])), \
            f"{narrowing} narrows collection and must not read as full"

    # S02 (deep pass of 2026-09-24, 3/3): a bundled flag is not a prefix
    # (`-qk x`), and PYTEST_ADDOPTS never reaches invocation_params -- a run
    # of 1 of 128 checks recorded itself full. What pytest PARSED says it.
    for bundled in (["-qk", "x"], ["-vm", "slow"], ["-qkx"]):
        assert not _selector_is_full(config(["tests", *bundled], ["tests"])), bundled
    assert not _selector_is_full(config(["tests"], ["tests"], keyword="x")), \
        "a -k from PYTEST_ADDOPTS read as a full run"
    for dest, value in (("markexpr", "slow"), ("deselect", ["a.py::t"]),
                        ("ignore", ["tests/rest"]), ("ignore_glob", ["*x*"]),
                        ("lf", True), ("stepwise", True)):
        assert not _selector_is_full(config(["tests"], ["tests"], **{dest: value})), dest
    assert _selector_is_full(config(["tests"], ["tests"], keyword="", markexpr="",
                                    deselect=None, lf=False)), \
        "pytest's own defaults read as narrowing"

    # And the record carries it, for the preregistration's check to read.
    from qa.report_plugin import _narrowing
    assert _narrowing(config(["tests", "-qk", "x"], ["tests"], keyword="x")) \
        == [["-k", "x"]]
    assert _narrowing(config(["tests"], ["tests"], keyword="", deselect=None)) == []

    # Q01 (deep pass of 2026-09-24, 3/3): the paths it was pointed at, as
    # pytest resolved them -- an option's value is never one of them.
    from qa.report_plugin import _paths
    assert _paths(config(["tests/a.py::t", "--snapshot-window", "60"],
                         ["tests/a.py::t"])) == ["tests/a.py::t"]
    assert _paths(config(["-q"], ["tests"])) == ["tests"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_part_that_could_not_be_read_is_not_a_part_that_changed():
    """The deploy detector must not fire on our own slow morning.

    diff() compared the two `parts` maps, so a corpus part that failed to read
    at the start of a run was absent from `before`, present in `after`, and
    reported as an appearance. On 2026-09-07 one ReadTimeout on /openapi.json
    did exactly that: fingerprint_drifted went true, the run became
    inadmissible for a reason that names a platform change, and 397 passing
    checks were thrown away. Nothing had deployed.

    Rule 8 one layer up. A read that failed is not a measurement, and it is
    certainly not a measurement that differs from the last one.

    The errors and the parts had to start sharing a key namespace for this to
    be possible at all -- errors were keyed by the part's dict repr and parts
    by path, so nothing downstream could match them up.
    """
    from qa.fingerprint import diff

    timed_out = {"parts": {"/llms.txt": "a"},
                 "errors": {"/openapi.json": "ReadTimeout: too slow"}}
    read_fine = {"parts": {"/llms.txt": "a", "/openapi.json": "b"}, "errors": {}}
    assert diff(timed_out, read_fine) == [], \
        "a part that could not be read was reported as a platform change"
    assert diff(read_fine, timed_out) == [], "and the same in the other direction"

    # What it must still catch.
    moved = {"parts": {"/llms.txt": "a", "/openapi.json": "CHANGED"}, "errors": {}}
    assert diff(read_fine, moved) == ["/openapi.json"], "a real change went unseen"

    gone = {"parts": {"/llms.txt": "a"}, "errors": {}}
    assert diff(read_fine, gone) == ["-/openapi.json"], \
        "a part genuinely dropped from the corpus went unseen"
