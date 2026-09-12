"""The pass reviews the repository and never itself.

Asked on 2026-09-10 whether the deep pass can improve its own process --
*"ze treba casem zjisti ze je zbytecne porad spoustet tu triadu agentu"* --
the honest answer was that nothing could tell: every pass writes down what it
claimed, who voted how and what was fixed, and the next pass overwrites the
file. The series existed only in git history and no step read it.

`scripts/deep_pass_process.py` reads it. These tests hold the two things that
make its numbers worth acting on:

  * the row is counted from the notebook, not recalled -- including the pass
    that never wrote `at_finished`, whose elapsed time must come back None
    rather than as a plausible number;
  * the sentence that would retire the triage triad appears only when three
    finished passes running removed nothing, because a process change made on
    one quiet pass is the same mistake as a finding filed on one reading.

In tests/repo rather than tests/meta: a stale answer here is worth knowing and
is not a reason to abort a session that is about to talk to the vendor.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _module():
    spec = importlib.util.spec_from_file_location(
        "deep_pass_process", REPO / "scripts" / "deep_pass_process.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _pass(run, gaps, at="2026-09-09T20:00:00+00:00", finished=True,
          at_finished="2026-09-09T22:00:00+00:00", **over):
    data = {"run": run, "at": at, "gaps": gaps, "finished": finished,
            "meta_tests": {"start": 200, "end": 201}, "rule_changes": []}
    if at_finished:
        data["at_finished"] = at_finished
    data.update(over)
    return data


def _gap(verdict, votes=("real", "real", "real"), source="audit", fixed=True):
    return {"id": "X", "nodeid": "a::b", "claim": "c", "source": source,
            "votes": {"t1": votes[0], "t2": votes[1], "t3": votes[2]},
            "verdict": verdict, "fixed": fixed}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_row_counts_the_notebook_rather_than_recalling_the_night():
    mod = _module()
    rows = mod.passes([
        _pass("deep-pass A", [
            _gap("real"),
            _gap("dropped", votes=("not-real", "not-real", "real"),
                 source="review", fixed=False),
            _gap("minority", votes=("real", "not-real", "not-real"),
                 fixed=False),
        ]),
        # The pass that died before writing at_finished. Its elapsed time is
        # unknown, and a number here would be invented.
        _pass("deep-pass B", [_gap("real")], at_finished=None),
    ])

    first, second = rows
    assert first["claimed"] == 3
    assert first["real"] == 1
    assert first["overturned"] == 2, (
        "dropped and minority are what the triad removed; that count is the "
        "whole argument for keeping three readers"
    )
    assert first["fixed"] == 1
    assert first["voted"] == 3 and first["unanimous"] == 1
    assert first["by_source"] == {"audit": 2, "review": 1}
    assert first["elapsed_min"] == 120
    assert second["elapsed_min"] is None, \
        "a pass that never said when it finished must not be given a duration"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_triad_is_retired_only_after_three_quiet_passes():
    mod = _module()
    quiet = [_pass(f"deep-pass {n}", [_gap("real")]) for n in "ABC"]
    assert mod.condition(mod.passes(quiet)), (
        "three passes in which the readers rejected nothing is the stated "
        "condition, and it must be sayable"
    )

    # One rejection anywhere in the window, and the question is not open.
    noisy = list(quiet)
    noisy[-1] = _pass("deep-pass C", [_gap("dropped")])
    assert mod.condition(mod.passes(noisy)) is None

    # Two passes cannot answer it either way.
    assert mod.condition(mod.passes(quiet[:2])) is None

    # An unfinished pass is not evidence: it may not have run its readers yet.
    unfinished = list(quiet)
    unfinished[-1] = _pass("deep-pass C", [_gap("real")], finished=False)
    assert mod.condition(mod.passes(unfinished)) is None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_committed_history_reads():
    """Over the real notebooks, so a schema change here shows up as red.

    It did not. All three assertions were true for ANY input -- `real` counts a
    subset of `claimed`, `unanimous` a subset of `voted`, and the header is a
    constant format string. A reader renamed the `gaps` key this reads and ran
    it against the real committed history: every row went to zeros and every
    assertion still held. An all-zero row already existed. 3/3 on triage.

    What a schema change actually looks like is a row of zeros where the
    commit body says work happened, so that is what is asserted: at least one
    committed pass must have CLAIMED something. That is a fact about the
    history rather than an arithmetic identity, and it is the one the tool's
    whole output rests on -- `deep_pass_process.py` exists to say whether the
    triad is still paying for itself, and it cannot say that from zeros.
    """
    from qa.marks import Inconclusive

    mod = _module()
    rows = mod.passes()
    if not rows:
        raise Inconclusive(
            "no committed deep-pass notebook could be read; git is either "
            "absent or the file has never been committed")
    assert all(row["claimed"] >= row["real"] for row in rows)
    assert all(row["voted"] >= row["unanimous"] for row in rows)
    assert mod.render(rows).splitlines()[0].startswith("pass")

    # The assertion a rename cannot survive -- on the NEWEST committed pass.
    # It asked whether ANY pass had claimed something, so a writer-side rename
    # of `gaps` zeroed every new row while the older notebooks kept the test
    # green (V15, deep pass of 2026-09-11, triage 3/3). passes() reads the
    # history oldest first.
    newest = rows[-1]
    assert newest["claimed"] > 0, (
        f"the newest committed pass, {newest['run']}, reads as zero gaps "
        f"claimed. Passes do not run for hours and find nothing, so the reader "
        f"has stopped finding the field it counts -- which is exactly what this "
        f"test says it catches: {[r['run'] for r in rows]}")

    # And its votes. A schema change that left `gaps` intact but moved
    # `votes` would slip past the line above.
    assert newest["voted"] > 0, (
        f"the newest committed pass, {newest['run']}, records no triage vote, "
        f"so the column the whole tool is FOR -- claims the readers rejected "
        f"-- is being read from nothing: {[r['run'] for r in rows]}")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_notebook_on_disk_is_the_newest_state_of_its_own_run():
    """A pass cannot be finished at the moment it renders the page about it.

    The dashboard read `versions()`, which is COMMITTED states only, so the
    newest row for the run in flight was always its second-to-last commit. The
    Stats panel is built from these rows and `payload_hash` covers them, so on
    2026-09-12 the pass rendered at 23:04 with `finished: false` and no
    `elapsed_min`, finalised its notebook at 23:15, and left rule 12's guard --
    `test_committed_dashboard_matches_the_committed_ledger` -- red on `main`
    until the next session happened to run it. By construction every pass ends
    that way: the row is about the run doing the rendering.

    The file on disk is that run's newest state whether or not it has been
    committed, so it goes on top. Both directions, because the unsafe one is
    quiet: an unreadable or run-less working copy must leave the history alone
    rather than shadow it.
    """
    mod = _module()
    history = {"deep-pass 2026-09-11": _pass("deep-pass 2026-09-11", []),
               "deep-pass 2026-09-12": _pass("deep-pass 2026-09-12", [],
                                             finished=False, at_finished=None)}

    same = mod.overlay_working(dict(history), None)
    assert [d.get("finished") for d in same.values()] == [True, False], (
        "a working copy that cannot be read is not a pass that never finished")
    assert mod.overlay_working(dict(history), {"gaps": []}) == history, (
        "a notebook naming no run cannot shadow one that does")

    finished = _pass("deep-pass 2026-09-12", [], finished=True,
                     at_finished="2026-09-12T23:15:00+00:00")
    merged = mod.overlay_working(dict(history), finished)
    assert len(merged) == 2, "the disk copy replaced its own run, not added one"
    assert list(merged) == list(history), "and it kept its place in the series"

    row = [r for r in mod.passes(list(merged.values()))
           if r["run"] == "deep-pass 2026-09-12"][0]
    assert row["finished"] is True and row["elapsed_min"] is not None, (
        "the row the page renders is still the one from before the pass ended")

    fresh = _pass("deep-pass 2026-09-13", [], finished=False, at_finished=None)
    started = mod.overlay_working(dict(history), fresh)
    assert list(started)[-1] == "deep-pass 2026-09-13", (
        "a pass that has not committed its notebook at all belongs at the end")

    # And the split that keeps the fix out of the series. `versions()` is the
    # committed history the retrospective judges and
    # `test_the_committed_history_reads` asserts against; only `series()` puts
    # the working copy on top, and only the page reads `series()`. Two names
    # rather than one flag: a default argument the test alone ever passes is
    # how a brake ends up off on the one path that matters.
    on_disk = mod.working_copy()
    if isinstance(on_disk, dict) and mod._run_key(on_disk):
        run = mod._run_key(on_disk)
        assert run in {mod._run_key(d, "") for d in mod.series()}, (
            "the page cannot see the pass that is rendering it")

        # Driven through render itself, not asserted about `series()` and
        # hoped for: the defect was never in this module, it was in which of
        # the two answers the page asked for. A grep of render.py would pass
        # on a call that had been commented out.
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "render_for_process_rows", REPO / "scripts" / "render.py")
        render = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(render)
        drawn = {str(r.get("run") or "") for r in render._process_rows()}
        assert run in drawn, (
            f"the Stats panel draws {sorted(drawn)} and not {run}, the pass "
            f"that is rendering it -- so the page it writes cannot match the "
            f"payload the guard rebuilds one commit later")
