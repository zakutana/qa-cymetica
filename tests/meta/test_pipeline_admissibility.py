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
def test_the_writer_sees_a_commit_made_during_the_run(monkeypatch):
    """V16, deep pass of 2026-09-19 (3/3). The test above feeds admissibility
    a record that already carries the flag; nothing drove the WRITER, so
    deleting it stayed green. And the writer sampled `git status` only -- an
    edit COMMITTED mid-run leaves the tree clean at the end and HEAD was read
    once, at the start, so the run stayed level V over code that moved.

    Driven through the writer, with git answering from a script: HEAD moved
    and the move touched code -> moved; HEAD moved over tracked state only (a
    console poll during the run) -> not; porcelain dirty -> moved.

    The stub answered on the subcommand alone, so it told the writer "no code
    moved" whatever the writer asked -- and dropping `"--", *CODE_PATHS` from
    either call stayed green, while against a real repository a state-only
    commit would then read as code moving (B14, deep pass of 2026-09-21). It
    now answers the way git does: a pathspec after `--` narrows what status
    and diff report, and without one they report every path.
    """
    import qa.report_plugin as plugin

    def git(head, committed=(), dirty=()):
        def within(path, args):
            if "--" not in args:
                return True
            spec = args[args.index("--") + 1:]
            return any(path == p or path.startswith(p + "/") for p in spec)

        def _git(*args):
            if args[0] == "rev-parse":
                return head
            if args[0] == "status":
                return "\n".join(f" M {p}" for p in dirty if within(p, args))
            if args[0] == "diff":
                return "\n".join(p for p in committed if within(p, args))
            return ""
        return _git

    monkeypatch.setattr(plugin, "_git", git(
        "bbb", committed=["qa/evidence.py", "state/ledger.json"]))
    assert plugin.code_moved_since("aaa") is True

    monkeypatch.setattr(plugin, "_git", git(
        "bbb", committed=["state/ledger.json", "dashboard/index.html"]))
    assert plugin.code_moved_since("aaa") is False, (
        "a commit of tracked state during the run is not the code moving")

    monkeypatch.setattr(plugin, "_git", git("aaa", dirty=["qa/fold.py"]))
    assert plugin.code_moved_since("aaa") is True

    monkeypatch.setattr(plugin, "_git", git("aaa", dirty=["state/ledger.json"]))
    assert plugin.code_moved_since("aaa") is False, (
        "a run writes state/ under itself on purpose; that is not the code "
        "being dirty at the end")

    monkeypatch.setattr(plugin, "_git", git("aaa", committed=["qa/fold.py"]))
    assert plugin.code_moved_since("aaa") is False, "HEAD did not move"

    import inspect
    source = inspect.getsource(plugin)
    assert 'run["code_dirty_after"] = code_moved_since(' in source, (
        "the session's end no longer asks the writer this test drives")


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


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_default_run_has_to_have_judged_something_in_the_ledger(tmp_path):
    """Admissible is not the same as relevant.

    On 2026-09-12 `ledger.py` with no `--run` took my own `tests/meta
    tests/repo` run: admissible, newest, and it measured nothing from their
    platform at all. No row moved -- the fold never closes what it did not
    run -- but the page describes the run the ledger was composed from, so
    every section tile emptied, and `test_a_tile_lists_the_tests_behind_its_count`
    passed by a single check (1 -> 0).

    So the default walks back to the newest admissible run that settled at
    least one row: every check a row declares, present in what the run
    collected. A partial overlap is not enough -- that is rule 1, and a run
    that collected half a row's checks adjudicates none of it. When nothing
    qualifies it returns None and the caller refuses rather than composing
    from a run about something else.
    """
    import importlib.util

    path = Path(__file__).resolve().parents[2] / "scripts" / "ledger.py"
    spec = importlib.util.spec_from_file_location("ledger_pick", path)
    ledger_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ledger_mod)

    prev = {"findings": {
        "CYM-a": {"checks": ["tests/rest/test_a.py::test_one",
                             "tests/rest/test_a.py::test_two"]},
        "CYM-b": {"checks": ["tests/mcp/test_b.py::test_three"]},
    }}

    runs = tmp_path / "runs"
    runs.mkdir()
    def _write(name, run):
        (runs / f"{name}.json").write_text(json.dumps(run), encoding="utf-8")

    def _over(run_id, at, collected):
        return _admissible(
            run_id, at, collected=collected,
            results=[{"nodeid": n, "outcome": "passed"} for n in collected])

    # A COLLECTED nodeid is not an adjudicated one. `pytest --collect-only`
    # writes a schema-2 record with every nodeid in `collected`, zero results
    # and exit 0 -- admissible by every rule in qa/state.py. On 2026-09-20
    # there were 113 such records of 496 and the default selection took one:
    # 1053 collected, 0 results, 59 of 63 rows passing `checks <= collected`
    # and not one of them adjudicated. So the first version of this walked
    # back from one empty run to another and changed nothing, which is the
    # 2026-09-12 defect it was written to close, still open.
    _write("z", {**_admissible("run-collect-only", "2026-09-12T23:00:00+00:00",
                               collected=["tests/rest/test_a.py::test_one",
                                          "tests/rest/test_a.py::test_two",
                                          "tests/mcp/test_b.py::test_three"]),
                 "results": []})
    # And a run that COLLECTED the row but skipped every one of its checks.
    _write("y", {**_admissible("run-all-skipped", "2026-09-12T22:00:00+00:00",
                               collected=["tests/mcp/test_b.py::test_three"]),
                 "results": [{"nodeid": "tests/mcp/test_b.py::test_three",
                              "outcome": "skipped"}]})

    _write("a", _over("run-platform", "2026-09-12T10:00:00+00:00",
                      ["tests/mcp/test_b.py::test_three"]))
    # Newest, admissible, and about us rather than about them.
    _write("b", _over("run-ourselves", "2026-09-12T18:00:00+00:00",
                      ["tests/meta/test_pipeline_fold.py::test_x"]))

    assert ledger_mod._run_that_adjudicates(prev, runs=runs) == "run-platform", (
        "the newest admissible run judged nothing in the ledger and was taken "
        "anyway -- either the `--collect-only` record, which collected every "
        "check and ran none, or the one that collected a row and skipped it")

    # Half a row is none of it: rule 1.
    _write("c", _over("run-half", "2026-09-12T20:00:00+00:00",
                      ["tests/rest/test_a.py::test_one"]))
    assert ledger_mod._run_that_adjudicates(prev, runs=runs) == "run-platform"

    _write("d", _over("run-whole", "2026-09-12T21:00:00+00:00",
                      ["tests/rest/test_a.py::test_one",
                       "tests/rest/test_a.py::test_two"]))
    assert ledger_mod._run_that_adjudicates(prev, runs=runs) == "run-whole"

    # Nothing qualifies -> None, so the caller can refuse with a reason
    # instead of composing from a run about something else.
    empty = tmp_path / "none"
    empty.mkdir()
    _write_only = _over("run-ourselves", "2026-09-12T18:00:00+00:00",
                        ["tests/meta/test_pipeline_fold.py::test_x"])
    (empty / "b.json").write_text(json.dumps(_write_only), encoding="utf-8")
    assert ledger_mod._run_that_adjudicates(prev, runs=empty) is None

    # An empty ledger has no rows to judge, so the newest admissible run is
    # the only sensible answer -- the first fold must not be unfoldable.
    assert ledger_mod._run_that_adjudicates({"findings": {}}, runs=empty) \
        == "run-ourselves"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_older_run_is_not_folded_over_a_newer_one_without_replay(
        tmp_path, monkeypatch):
    """A1 of the 2026-09-23 review (3/3). Nothing compared a run's time with
    the ledger's: `ledger.py --run <id>` folded whatever it was named, so a
    stale id moved a row BACKWARDS -- here from passing, as the newer run
    judged it, to reproducing, as an older one had -- and a row moved that
    way can owe the vendor a false pass or fail. The pin path has had a date
    guard since 2026-09-22; this path had none.

    So the write path refuses a run older than the newest the ledger stands
    on, before it attests anything, unless the run is named `--replay`. The
    same run again is not older, and folds as before. The read-only paths
    (`--check`, rule 12's refold) are untouched: they refold the run the
    ledger cites, which is never newer than itself."""
    import importlib.util

    state = tmp_path / "state"
    (state / "journal").mkdir(parents=True)
    (state / "runs").mkdir(parents=True)
    monkeypatch.setenv("QA_STATE_DIR", str(state))

    path = Path(__file__).resolve().parents[2] / "scripts" / "ledger.py"
    spec = importlib.util.spec_from_file_location("ledger_order", path)
    ledger_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(ledger_mod)
    # Nothing here may reach the repository's own git index.
    monkeypatch.setattr(ledger_mod, "_track_run_record", lambda run_id: None)
    monkeypatch.setattr(ledger_mod.keepset, "track", lambda **k: None)
    monkeypatch.setattr(ledger_mod.keepset, "untrack", lambda **k: None)

    from qa.state import read_events

    check = "tests/rest/test_a.py::test_one"
    old_at, new_at = "2026-09-20T10:00:00+00:00", "2026-09-22T10:00:00+00:00"

    def run(run_id, at, outcome):
        return _admissible(run_id, at, collected=[check],
                           exit_status=0 if outcome == "passed" else 1,
                           results=[{"nodeid": check, "outcome": outcome}],
                           prereg_id=None, prereg_commit=None,
                           prereg_tag_sha=None)
    for run_id, at, outcome in (("run-old", old_at, "failed"),
                                ("run-new", new_at, "passed")):
        (state / "runs" / f"{run_id}.json").write_text(
            json.dumps(run(run_id, at, outcome)), encoding="utf-8")

    (state / "ledger.json").write_text(json.dumps({
        "schema": 2, "run_id": "run-new", "run_level": "R",
        "updated_at": new_at,
        "findings": {"CYM-a": {
            "id": "CYM-a", "title": "t", "severity": "S3-CONTRACT",
            "checks": [check],
            "first_seen": {"at": old_at, "cause": {"run_id": "run-first"}},
            "reproductions": 1, "reproduced_in": ["run-first"],
            "check": {"state": "PASSING_UNPINNED", "pinned_fingerprint": None,
                      "adjudicated_by": {"run_id": "run-new", "at": new_at}},
            "filing": {"state": "NOT_RAISED", "adjudicated_by": None,
                       "reports": [], "refused": [], "verifications": []},
            "transitions": [{"axis": "check", "from": "UNVERIFIED",
                             "to": "PASSING_UNPINNED",
                             "cause": {"run_id": "run-new"}, "at": new_at}],
            "regressions": []}}}), encoding="utf-8")
    before = (state / "ledger.json").read_bytes()

    with pytest.raises(SystemExit) as refused:
        ledger_mod.main(["--run", "run-old"])
    said = str(refused.value)
    assert "run-old" in said and "--replay" in said, said
    assert (state / "ledger.json").read_bytes() == before, "the ledger moved"
    assert not [e for e in read_events() if e.get("type") == "run_recorded"], (
        "the refused run was attested in the journal anyway")

    # The same run the ledger stands on is not older than itself.
    assert ledger_mod.main(["--run", "run-new"]) == 0

    # Named as a replay, it folds -- and moves the row, which is why it
    # has to be named.
    assert ledger_mod.main(["--run", "run-old", "--replay"]) == 0
    folded = json.loads((state / "ledger.json").read_text(encoding="utf-8"))
    assert folded["run_id"] == "run-old"
    assert folded["findings"]["CYM-a"]["check"]["state"] == "REPRODUCING"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_collect_only_run_is_not_the_last_full_run(tmp_path, monkeypatch):
    """2026-09-22 17:50 UTC: `open_checks.py --explain` said "last full run
    0h ago" about run-20260922T174253Z-d7c8c4c3 -- a `pytest --collect-only
    tests` that tests/repo/test_audit_scope.py spawns, 1207 collected, 0
    results. `selector_full` is true of it, and that was the only thing the
    line asked. The ledger's default stopped taking such records on
    2026-09-20; this reader did not, so the one line that says whether a
    settled row could have regressed unseen could be reset by any tests/repo
    run while nothing had been re-checked."""
    import importlib.util

    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    runs = tmp_path / "runs"
    runs.mkdir()
    (runs / "a.json").write_text(json.dumps(_admissible(
        "run-full", "2026-09-20T10:00:00+00:00", selector_full=True)),
        encoding="utf-8")
    (runs / "b.json").write_text(json.dumps(_admissible(
        "run-collect-only", "2026-09-22T17:42:58+00:00", selector_full=True,
        collected=["tests/x.py::test_a"], results=[])), encoding="utf-8")

    path = Path(__file__).resolve().parents[2] / "scripts" / "open_checks.py"
    spec = importlib.util.spec_from_file_location("open_checks_under_test", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    said = mod.since_last_full_run()
    assert "run-full" in said and "run-collect-only" not in said, said

    # R01, deep pass of 2026-09-22 evening (3/3): a full run the meta gate
    # aborted has results -- tests/meta only -- and not one settled row was
    # re-checked. Judged something means judged something on THEIR side.
    (runs / "c.json").write_text(json.dumps(_admissible(
        "run-meta-aborted", "2026-09-22T19:00:00+00:00", selector_full=True,
        collected=["tests/meta/test_x.py::test_a", "tests/rest/test_y.py::test_b"],
        results=[{"nodeid": "tests/meta/test_x.py::test_a", "outcome": "failed"}])),
        encoding="utf-8")
    said = mod.since_last_full_run()
    assert "run-full" in said and "run-meta-aborted" not in said, said

    # B09 (deep pass of 2026-09-24): a full run in an outage where every one
    # of their checks came back inconclusive judged nothing either -- rule
    # 10: an inconclusive measured nothing -- and still read as the last one.
    (runs / "d.json").write_text(json.dumps(_admissible(
        "run-outage", "2026-09-23T03:00:00+00:00", selector_full=True,
        collected=["tests/meta/test_x.py::test_a", "tests/rest/test_y.py::test_b"],
        results=[{"nodeid": "tests/meta/test_x.py::test_a", "outcome": "passed"},
                 {"nodeid": "tests/rest/test_y.py::test_b",
                  "outcome": "inconclusive"}])), encoding="utf-8")
    said = mod.since_last_full_run()
    assert "run-full" in said and "run-outage" not in said, said
