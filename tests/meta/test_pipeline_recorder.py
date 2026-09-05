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
        cwd=pytester.path, env=env, capture_output=True, text=True, timeout=180,
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
    """)
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
