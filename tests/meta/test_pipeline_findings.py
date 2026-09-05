"""FIND: findings.py proposes candidates from one run and holds no state.

Three defects live in this file today and each has produced visible damage:

  * The state machine at :539-550 set a finding's state from the vendor's
    tracker alone -- not one branch read a check result. That is where
    FIX CLAIMED came from without anyone re-running anything.
  * `_parse_failure` regexes the whole pytest traceback for the finding's
    detail. One of those details reached the vendor with a line of OUR source
    in it, offered as evidence about THEIR platform.
  * Nothing distinguished a call-phase failure from a fixture blowing up in
    setup, so a broken harness on the trust ladder test would have been filed
    as an S0.

After this phase findings.py answers exactly one question: given this run
record, what does it propose? States belong to the fold.

Fails at 11e43ea: findings.candidates does not exist.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _findings():
    path = REPO / "scripts" / "findings.py"
    spec = importlib.util.spec_from_file_location("findings_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _run(results):
    return {
        "schema": 2, "run_id": "run-1", "started_at": "2026-09-05T10:00:00+00:00",
        "finished_at": "2026-09-05T10:00:00+00:00",
        "collected": [r["nodeid"] for r in results],
        "results": results, "exit_status": 1,
    }


def _result(nodeid, outcome, phase="call", **over):
    base = {
        "nodeid": nodeid, "outcome": outcome, "phase": phase,
        "component": "discovery", "surface": "rest",
        "check_fingerprint": "sha256:aaaa",
        "measurement": {
            "verdict": outcome, "reason": "documented count 46 != live count 25",
            "left": 46, "right": 25, "role": "verdict",
            "sources": {"a": "llms.txt", "b": "live"},
            "claim_id": "mcp_tool_count", "evidence_ids": ["ev-1"],
        },
    }
    base.update(over)
    return base


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_findings_only_from_call_phase_failed_results():
    """A candidate is a call-phase failure of a verdict-role measurement.
    Setup errors are harness faults, skips are not evidence, and an
    evidence-role measurement can never mint a finding on its own."""
    findings = _findings()

    run = _run([
        _result("tests/a.py::test_real_failure", "failed"),
        _result("tests/a.py::test_setup_blew_up", "failed", phase="setup"),
        _result("tests/a.py::test_inconclusive", "inconclusive"),
        _result("tests/a.py::test_skipped", "skipped"),
        _result("tests/a.py::test_passed", "passed"),
        _result("tests/a.py::test_prose_vs_prose", "failed",
                measurement={"verdict": "failed", "reason": "r", "role": "evidence"}),
    ])

    ids = {c["id"]: c for c in findings.candidates(run)}
    checks = {c for cand in ids.values() for c in cand["checks"]}
    assert checks == {"tests/a.py::test_real_failure"}, checks


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_finding_detail_never_scraped_from_traceback():
    """The detail comes from the measurement the check deliberately built.
    Fed a result whose traceback is full of our own source, none of it may
    appear in the candidate."""
    findings = _findings()

    poison = (
        'tests/reconciliation/test_reconcile.py:88: in test_sources_agree\n'
        '    assert left == right, f"{pair.claim}: {left} != {right}"\n'
        'E   AssertionError: mcp_tool_count: 46 != 25\n'
    )
    run = _run([_result("tests/a.py::test_x", "failed", failure_repr=poison)])

    cand = findings.candidates(run)
    assert len(cand) == 1
    blob = repr(cand[0])
    for leak in ("test_reconcile.py:88", "assert left == right", "AssertionError"):
        assert leak not in blob, f"our own source leaked into the candidate: {leak}"
    assert cand[0]["detail"]["left"] == 46 and cand[0]["detail"]["right"] == 25


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_candidates_carry_no_state():
    """findings.py may not decide RAISED, FIX CLAIMED or anything else. It
    does not read the tracker; it does not know what the vendor said."""
    findings = _findings()

    run = _run([_result("tests/a.py::test_x", "failed")])
    for cand in findings.candidates(run):
        assert "state" not in cand, "a candidate carries a state again"
        assert "filed" not in cand and "thread" not in cand

    # Read the code, not the prose: the module's docstring names these states
    # precisely because it explains why they no longer live here.
    import ast

    tree = ast.parse((REPO / "scripts" / "findings.py").read_text(encoding="utf-8"))
    docstrings = {ast.get_docstring(n) for n in ast.walk(tree)
                  if isinstance(n, (ast.Module, ast.ClassDef, ast.FunctionDef))}
    literals = {n.value for n in ast.walk(tree)
                if isinstance(n, ast.Constant) and isinstance(n.value, str)} - docstrings

    for gone in ("FIX CLAIMED", "NOT RAISED YET", "THEY REPLIED", "VERIFIED FIXED"):
        assert gone not in literals, f"findings.py still assigns the display state {gone!r}"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_check_is_collectible_or_row_is_unverifiable():
    """Five ledger rows list scripts/inventory.py as their check. pytest never
    collects a script, so those rows sat outside the verification machinery
    entirely -- permanently un-adjudicated while displaying a state."""
    from qa.fold import fold

    from tests.meta.test_pipeline_fold import ledger, row

    state = ledger(
        row("CYM-script", checks=["scripts/inventory.py"]),
        row("CYM-none", checks=[]),
        row("CYM-ok", checks=["tests/a.py::test_x"]),
    )
    after = fold(state, run=None, events=[])

    assert after["findings"]["CYM-script"]["check"]["state"] == "UNVERIFIABLE"
    assert after["findings"]["CYM-script"]["check"]["unverifiable_reason"] == "check_not_a_nodeid"
    assert after["findings"]["CYM-none"]["check"]["unverifiable_reason"] == "no_checks"
    assert after["findings"]["CYM-ok"]["check"]["state"] == "UNVERIFIED"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_inconclusive_on_filed_row_opens_repair_obligation():
    """Critique gap 3. mcp_resource_count is filed as #50 and its check has
    never measured anything. Composed as INCONCLUSIVE x FIX_CLAIMED it renders
    NOT REPRODUCIBLE -- a broken check reading as a resolved defect. It must
    instead show a debt: repair the check, or correct the report."""
    from qa.fold import fold

    from tests.meta.test_pipeline_fold import _filed, ledger, row

    state = ledger(row("CYM-mcp_resource_count", check_state="INCONCLUSIVE",
                       checks=["tests/a.py::test_x"]))
    after = fold(state, events=_filed("CYM-mcp_resource_count", 50, "fixed"))

    r = after["findings"]["CYM-mcp_resource_count"]
    assert r["obligations"]["repair_check"] is True
    assert r["obligations"]["reverify"] is True


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_regression_after_closed_report_opens_reopen_obligation():
    """Critique gap 4. A row that regresses after the vendor closed its report
    is not just a red badge -- it is something we owe them a message about."""
    from qa.fold import fold

    from tests.meta.test_pipeline_fold import CHECK_A, FP1, _filed, fold_run, ledger, row

    state = ledger(row("CYM-a", check_state="REPRODUCING", checks=[CHECK_A], pinned=FP1))
    events = _filed("CYM-a", 46, "fixed")

    passing = fold(state, run=fold_run("run-v", [(CHECK_A, "passed")]), events=events)
    assert passing["findings"]["CYM-a"]["obligations"]["reopen"] == []

    regressed = fold(passing, run=fold_run("run-w", [(CHECK_A, "failed")],
                                           at="2026-09-05T11:00:00+00:00"), events=events)
    assert regressed["findings"]["CYM-a"]["obligations"]["reopen"] == [46]
