"""STATE (runs): a run record is evidence only if it is admissible, and it is
selected by its id, never by filename order.

Phase 2 of the hardening plan. Fails at 517731f: qa.state has no
admissibility, load_run, list_runs or latest_admissible_run_id.

The 13 committed run records are the fixtures. Every one of them is
inadmissible for a reason the record itself names -- that is the honest
reading of yesterday, and the reason the dashboard will show 0 verified on
day one until a clean, tagged, full run exists.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa

FIX = Path(__file__).resolve().parent / "fixtures"
RUNS = FIX / "runs"

# Computed from the fixtures at 517731f; see the phase-2 commit message.
EXPECTED = {
    "run-20260904T100429Z-nogit":   {"legacy_schema", "no_prereg", "git_dirty"},
    "run-20260904T100559Z-nogit":   {"legacy_schema", "no_prereg", "git_dirty"},
    "run-20260904T101515Z-nogit":   {"legacy_schema", "no_prereg", "git_dirty"},
    "run-20260904T102903Z-nogit":   {"legacy_schema", "no_prereg", "git_dirty"},
    "run-20260904T102937Z-nogit":   {"legacy_schema", "no_prereg", "git_dirty"},
    "run-20260904T123402Z-acf86e7": {"legacy_schema", "no_prereg", "git_dirty"},
    "run-20260904T125841Z-57d3e34": {"legacy_schema", "no_prereg", "git_dirty"},
    "run-20260904T125947Z-57d3e34": {"legacy_schema", "no_prereg", "git_dirty", "fingerprint_drifted"},
    "run-20260904T130132Z-57d3e34": {"legacy_schema", "no_prereg", "git_dirty"},
    "run-20260904T131102Z-9a729ed": {"legacy_schema", "no_prereg", "git_dirty", "fingerprint_drifted"},
    "run-20260904T131713Z-7518e8e": {"legacy_schema", "no_prereg", "exit_status_disagrees"},
    "run-20260904T131813Z-7518e8e": {"legacy_schema", "no_prereg", "git_dirty"},
    "run-20260904T131842Z-7518e8e": {"legacy_schema", "no_prereg", "git_dirty"},
}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("run_id", sorted(EXPECTED), ids=lambda r: r[4:19])
def test_every_committed_run_is_inadmissible_for_a_named_reason(run_id):
    from qa.state import admissibility, load_run

    run = load_run(run_id, runs=RUNS)
    verdict = admissibility(run)
    assert verdict.level == "none", (run_id, verdict)
    assert set(verdict.reasons) == EXPECTED[run_id], (run_id, verdict.reasons)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_legacy_inconclusive_results_are_relabelled_at_read_time_only():
    """53 committed results say `failed` because the old recorder resumed
    before the Inconclusive classifier. Loading relabels them, with the
    original kept beside; the file on disk is never rewritten (methodology
    §1.5: label contaminated data, do not recompute it)."""
    from qa.state import load_run

    before = {p.name: p.read_bytes() for p in RUNS.glob("run-*.json")}

    one = load_run("run-20260904T131713Z-7518e8e", runs=RUNS)
    assert len(one["results"]) == 1
    r = one["results"][0]
    assert r["outcome"] == "inconclusive" and r["reclassified_from"] == "failed", r

    relabelled = sum(
        1 for rid in EXPECTED for x in load_run(rid, runs=RUNS)["results"]
        if x.get("reclassified_from") == "failed"
    )
    assert relabelled == 53, relabelled

    after = {p.name: p.read_bytes() for p in RUNS.glob("run-*.json")}
    assert after == before, "load_run rewrote a run record"


def _admissible(run_id: str, started_at: str, **over) -> dict:
    base = {
        "schema": 2, "run_id": run_id, "started_at": started_at,
        "finished_at": started_at, "git_head": "abc123", "git_dirty": False,
        "prereg_id": "PRE-0001", "prereg_tag_sha": "t", "prereg_commit": "abc123",
        "platform_fingerprint": "sha256:f", "fingerprint_drifted": False,
        "collected": ["tests/x.py::test_a"], "exit_status": 0,
        "results": [{"nodeid": "tests/x.py::test_a", "outcome": "passed"}],
        "record_integrity": {"consistent": True},
    }
    base.update(over)
    return base


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_run_is_selected_by_id_not_filename_order(tmp_path):
    """The three copies of sorted(glob(...))[-1] are gone. A run is found by
    its run_id FIELD, and 'latest' means latest started_at among admissible
    runs -- a file named to sort last does not win."""
    from qa.state import latest_admissible_run_id, list_runs, load_run

    runs = tmp_path / "runs"
    runs.mkdir()
    # Filename order is the REVERSE of started_at order, and neither filename
    # matches its run_id field.
    (runs / "zzz-last-by-name.json").write_text(json.dumps(
        _admissible("run-early", "2026-09-05T01:00:00+00:00")), encoding="utf-8")
    (runs / "aaa-first-by-name.json").write_text(json.dumps(
        _admissible("run-late", "2026-09-05T02:00:00+00:00")), encoding="utf-8")
    (runs / "mmm-inadmissible.json").write_text(json.dumps(
        _admissible("run-latest-but-dirty", "2026-09-05T03:00:00+00:00", git_dirty=True)),
        encoding="utf-8")

    assert load_run("run-early", runs=runs)["run_id"] == "run-early"
    assert [r["run_id"] for r in list_runs(runs=runs)] == ["run-early", "run-late", "run-latest-but-dirty"]
    assert latest_admissible_run_id("V", runs=runs) == "run-late"
    assert latest_admissible_run_id("R", runs=runs) == "run-latest-but-dirty"
    with pytest.raises(KeyError):
        load_run("run-does-not-exist", runs=runs)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_tree_that_moved_during_the_run_is_not_a_verification():
    """`git_dirty` is sampled once, at pytest_sessionstart. So a run can record
    a clean tree and then have the code edited under it while it runs, and the
    record still says level V.

    That happened on 2026-09-12, to this session, during a seven-minute
    verification: `qa/evidence.py` at 10:09:00 and `scripts/prune_runs.py` at
    10:09:19, inside a run that started 10:03:39 and finished 10:10:33. The
    record said `git_dirty: false` and meant it -- at 10:03:39 it was true.

    Rule 6 says verification is a clean tree. A tree that is clean only at the
    starting pistol is not one, so the second sample is what makes the rule
    executable. It is scoped to the code because a run legitimately writes
    tracked state under itself -- a repo-wide sample at the end would refuse
    every verification we have ever made.
    """
    from qa.state import admissibility

    clean = admissibility(_admissible("r", "2026-09-05T00:00:00+00:00",
                                      code_dirty_after=False))
    assert (clean.level, clean.reasons) == ("V", [])

    moved = admissibility(_admissible("r", "2026-09-05T00:00:00+00:00",
                                      code_dirty_after=True))
    assert moved.level == "R", moved.reasons
    assert "code_moved_during_run" in moved.reasons, moved.reasons

    # Silence is not innocence, but an old record cannot be judged by a field
    # that did not exist when it was written: absent stays admissible, and the
    # runs already in the ledger keep the level they were folded at.
    old = admissibility(_admissible("r", "2026-09-05T00:00:00+00:00"))
    assert old.level == "V", old.reasons


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_two_levels_reproduce_vs_verify():
    """R may open a defect; V may also verify a fix. Reasons are named."""
    from qa.state import admissibility

    v = admissibility(_admissible("r", "2026-09-05T00:00:00+00:00"))
    assert (v.level, v.reasons) == ("V", [])

    r = admissibility(_admissible("r", "2026-09-05T00:00:00+00:00", git_dirty=True))
    assert r.level == "R" and r.reasons == ["git_dirty"]

    r = admissibility(_admissible("r", "2026-09-05T00:00:00+00:00", prereg_id=None, prereg_commit=None))
    assert r.level == "R" and r.reasons == ["no_prereg"]

    r = admissibility(_admissible("r", "2026-09-05T00:00:00+00:00", prereg_commit="other"))
    assert r.level == "R" and r.reasons == ["prereg_commit_mismatch"]

    none = admissibility(_admissible("r", "2026-09-05T00:00:00+00:00", fingerprint_drifted=True))
    assert none.level == "none" and "fingerprint_drifted" in none.reasons

    none = admissibility(_admissible("r", "2026-09-05T00:00:00+00:00", exit_status=1))
    assert none.level == "none" and "exit_status_disagrees" in none.reasons

    none = admissibility(_admissible("r", "2026-09-05T00:00:00+00:00",
                                     results=[{"nodeid": "tests/x.py::test_b", "outcome": "passed"}]))
    assert none.level == "none" and "results_not_collected" in none.reasons

    none = admissibility(_admissible("r", "2026-09-05T00:00:00+00:00", platform_fingerprint=None))
    assert none.level == "none" and "no_fingerprint" in none.reasons
