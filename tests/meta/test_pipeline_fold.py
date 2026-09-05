"""FOLD: the ledger is a pure function of (previous rows, one run, the journal).

Phase 3 of the hardening plan, and the test file the audit's headline number
exists for. 71 of 109 state changes an operator watched were self-inflicted --
produced by `merge()` in scripts/ledger.py, not by the platform. Every one of
those seven mechanisms has a test here that fails if it returns:

  * `absence-is-verification`   -- merge() stamped VERIFIED FIXED on any row
    missing from findings.json (ledger.py:158-160), so a run that never looked
    closed everything it did not touch.
  * `sticky-verified-latch-precedes-guard` -- the sticky branch (:144-146) ran
    BEFORE the did-it-actually-run guard, making that guard unreachable.
  * `regression-self-reverses` -- REGRESSED was driven off a timestamp field,
    so it flipped back on the next merge.
  * `state-derived-from-vendor-tracker` -- findings.py:539-550 set state from
    the vendor's status alone; no branch read a check result.
  * `run-admissibility-never-checked` and the three copies of "take the last
    file by name".

The rule, stated once and tested here: a row moves on the CHECK axis only when
an admissible run record adjudicated every check the row declares, and on the
FILING axis only when a journal event says so. Nothing else moves anything.

Fails at 11e43ea: there is no qa.fold.
"""

from __future__ import annotations

import itertools
import random

import pytest

from qa.marks import SafetyTier, qa

CHECK_A = "tests/reconciliation/test_reconcile.py::test_sources_agree[a]"
CHECK_B = "tests/reconciliation/test_reconcile.py::test_sources_agree[b]"
CHECK_C = "tests/mcp/test_trust_ladder.py::test_trusted_receives_nothing_above_its_tier"

FP1 = "sha256:1111"
FP2 = "sha256:2222"


# ---------------------------------------------------------------------------
# Builders
# ---------------------------------------------------------------------------
def run(run_id="run-1", results=(), collected=None, level="V", at="2026-09-05T10:00:00+00:00"):
    """A run record at the requested admissibility level.

    level "V": clean tree, tagged prereg resolving to HEAD -- may verify.
    level "R": dirty tree -- may reproduce, may never verify.
    level "none": legacy schema -- may not move anything.
    """
    results = [dict(r) for r in results]
    nodeids = [r["nodeid"] for r in results]
    record = {
        "schema": 2,
        "run_id": run_id,
        "started_at": at,
        "finished_at": at,
        "git_head": "abc123",
        "git_dirty": level == "R",
        "prereg_id": None if level == "R" else "PRE-0001",
        "prereg_commit": None if level == "R" else "abc123",
        "platform_fingerprint": "sha256:platform",
        "fingerprint_drifted": False,
        "collected": list(collected if collected is not None else nodeids),
        "exit_status": 1 if any(r.get("outcome") in ("failed", "error") for r in results) else 0,
        "results": results,
        "record_integrity": {"consistent": True},
        "identities_present": {"anon": True, "trusted": True},
    }
    if level == "R":
        record["prereg_id"] = "PRE-0001"
        record["prereg_commit"] = "abc123"
        record["git_dirty"] = True
    if level == "none":
        record["schema"] = 1
        record.pop("collected")
    return record


def result(nodeid, outcome, fingerprint=FP1, phase="call"):
    return {"nodeid": nodeid, "outcome": outcome, "phase": phase,
            "check_fingerprint": fingerprint,
            "measurement": {"verdict": outcome, "reason": "r", "role": "verdict"}}


def fold_run(run_id, pairs, at="2026-09-05T10:00:00+00:00", level="V", fingerprint=FP1):
    """run() from (nodeid, outcome) pairs -- the common shape in other files."""
    return run(run_id, [result(n, o, fingerprint=fingerprint) for n, o in pairs],
               level=level, at=at)


def candidate(fid="CYM-a", checks=(CHECK_A,), **over):
    base = {"id": fid, "title": "t", "severity": "S3-CONTRACT", "checks": list(checks),
            "component": "discovery", "section": "Discovery", "detail": {}}
    base.update(over)
    return base


def row(fid="CYM-a", check_state="UNVERIFIED", filing_state="NOT_RAISED",
        checks=(CHECK_A,), pinned=None, **over):
    base = {
        "id": fid, "title": "t", "severity": "S3-CONTRACT", "checks": list(checks),
        "first_seen": {"at": "2026-09-04T00:00:00+00:00", "cause": {"run_id": "run-0"}},
        "reproductions": 1,
        "check": {"state": check_state, "adjudicated_by": None, "pinned_fingerprint": pinned},
        "filing": {"state": filing_state, "adjudicated_by": None, "reports": []},
        "transitions": [],
        "regressions": [],
    }
    base.update(over)
    return base


def ledger(*rows):
    return {"schema": 2, "findings": {r["id"]: r for r in rows}}


def _key(transition):
    t = transition
    return (t["axis"], t["from"], t["to"], t["at"], tuple(sorted((t.get("cause") or {}).items())))


def event(type_, at="2026-09-05T09:00:00+00:00", **fields):
    base = {"type": type_, "at": at, "by": "agent", "source": "scripts/submit.py"}
    base.update(fields)
    return base


def _filed(fid="CYM-a", report_id=46, status="pending", at="2026-09-05T09:00:00+00:00"):
    """The events that put a finding in front of the vendor."""
    return [
        event("filing_intent", at=at, key=f"k-{report_id}", intent_at=at,
              title="t", findings=[fid]),
        event("filing_outcome", at=at, key=f"k-{report_id}", outcome="accepted",
              report_id=report_id, findings=[fid], evidence_id="ev-1"),
        event("vendor_status", at=at, report_id=report_id, status=status,
              evidence_id="ev-2"),
    ]


def events_for(fid, filing_state, report_id=46):
    """The journal that produces a given FILING state.

    There is no other way to get one. A row cannot simply be handed a filing
    state, here or anywhere else -- the axis is a replay of the journal, so a
    test that wants FIX_CLAIMED has to produce the events that claim it.
    """
    if filing_state == "NOT_RAISED":
        return []
    status = "fixed" if filing_state == "FIX_CLAIMED" else "pending"
    return _filed(fid, report_id=report_id, status=status)


# ---------------------------------------------------------------------------
# The rule, stated as a test
# ---------------------------------------------------------------------------
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_no_state_change_without_run_id_or_event_id():
    """200 random sequences of runs and events. Every state change that comes
    out the far end cites an admissible run (CHECK) or a journal event
    (FILING). A change with no cause is the class of defect that produced 71
    of the 109 transitions in the audit."""
    from qa.fold import display_state, fold

    rng = random.Random(20260905)
    for seed in range(200):
        state = ledger(row("CYM-a", checks=[CHECK_A]), row("CYM-b", checks=[CHECK_B]))
        events: list[dict] = []
        for step in range(rng.randint(1, 6)):
            before = {fid: display_state(r) for fid, r in state["findings"].items()}
            # Compared as sets: the FILING half is rebuilt from the journal on
            # every fold, so positions move even when nothing changed.
            before_tx = {fid: {_key(t) for t in r["transitions"]}
                         for fid, r in state["findings"].items()}

            if rng.random() < 0.5:
                outcome = rng.choice(["passed", "failed", "inconclusive", "skipped"])
                nodes = rng.sample([CHECK_A, CHECK_B], rng.randint(1, 2))
                level = rng.choice(["V", "R", "none"])
                r = run(f"run-{seed}-{step}", [result(n, outcome) for n in nodes],
                        level=level, at=f"2026-09-05T10:{step:02d}:00+00:00")
                state = fold(state, run=r, events=events)
            else:
                events = events + _filed("CYM-a", report_id=100 + step,
                                         at=f"2026-09-05T09:{step:02d}:00+00:00")
                state = fold(state, run=None, events=events)

            for fid, row_ in state["findings"].items():
                after = display_state(row_)
                new = [t for t in row_["transitions"] if _key(t) not in before_tx[fid]]
                if after != before[fid]:
                    assert new, (
                        f"seed {seed} step {step}: {fid} display state moved "
                        f"{before[fid]} -> {after} with no transition recorded"
                    )
                for t in new:
                    cause = t.get("cause") or {}
                    key = "run_id" if t["axis"] == "check" else "event_id"
                    assert cause.get(key), (
                        f"seed {seed}: {t['axis']} transition to {t['to']!r} "
                        f"has no {key} -- state was assigned, not caused"
                    )


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_axes_are_independent():
    """A run may never move FILING; an event may never move CHECK. The audit
    found findings.py:539-550 setting the whole state from the vendor tracker
    alone -- no branch read a check result."""
    from qa.fold import fold

    rng = random.Random(11)
    for seed in range(200):
        filing = rng.choice(["NOT_RAISED", "RAISED", "FIX_CLAIMED"])
        events = events_for("CYM-a", filing, report_id=1000 + seed)
        state = ledger(row("CYM-a", check_state=rng.choice(
            ["UNVERIFIED", "REPRODUCING", "PASSING", "INCONCLUSIVE"]), pinned=FP1))

        # Fold the journal alone, so the row's FILING state is one the events
        # actually justify, then fold a run on top of it.
        state = fold(state, run=None, events=events)
        assert state["findings"]["CYM-a"]["filing"]["state"] == filing

        after_run = fold(state, run=run("run-x", [result(CHECK_A, "failed")]), events=events)
        assert after_run["findings"]["CYM-a"]["filing"]["state"] == filing, \
            "a run record moved the FILING axis"

        check_before = dict(state["findings"]["CYM-a"]["check"])
        after_evt = fold(state, run=None, events=events + _filed("CYM-a", 900 + seed, "fixed"))
        assert after_evt["findings"]["CYM-a"]["check"] == check_before, \
            "a journal event moved the CHECK axis"


# ---------------------------------------------------------------------------
# The three mechanisms that closed rows nobody checked
# ---------------------------------------------------------------------------
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_partial_run_cannot_close_anything():
    """Modelled on the real run-20260904T131713Z: one result, three open rows.

    merge() read that run and closed the two rows it never touched. The fold
    must leave them exactly where they were and say so with not_checked_in."""
    from qa.fold import display_state, fold

    events = (events_for("CYM-a", "RAISED", 46)
              + events_for("CYM-b", "RAISED", 47)
              + events_for("CYM-c", "FIX_CLAIMED", 48))
    state = fold(ledger(
        row("CYM-a", check_state="REPRODUCING", checks=[CHECK_A], pinned=FP1),
        row("CYM-b", check_state="REPRODUCING", checks=[CHECK_B], pinned=FP1),
        row("CYM-c", check_state="REPRODUCING", checks=[CHECK_C], pinned=FP1),
    ), events=events)
    before = {fid: display_state(r) for fid, r in state["findings"].items()}

    partial = run("run-partial", [result(CHECK_A, "passed")], collected=[CHECK_A])
    after = fold(state, run=partial, events=events)

    assert display_state(after["findings"]["CYM-a"]) != before["CYM-a"], \
        "the row the run actually adjudicated did not move"
    for fid in ("CYM-b", "CYM-c"):
        r = after["findings"][fid]
        assert display_state(r) == before[fid], f"{fid} moved on a run that never ran its check"
        assert r["check"]["not_checked_in"] == "run-partial"
        assert [t for t in r["transitions"] if t["axis"] == "check"] == [], \
            f"{fid} recorded a CHECK transition for a check that did not run"
        assert "VERIFIED" not in display_state(r)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_absence_is_never_verification():
    """Replays 0d5cd34: a row absent from findings.json was stamped VERIFIED
    FIXED with the current timestamp. Absence is not evidence -- of the two
    things it can mean, only one is a pass, and the run record says which."""
    from qa.fold import display_state, fold

    events = events_for("CYM-gone", "FIX_CLAIMED", 50)
    state = fold(ledger(row("CYM-gone", check_state="REPRODUCING",
                            checks=[CHECK_C], pinned=FP1)), events=events)

    # A full, clean, level-V run in which the row's check simply does not appear.
    empty = run("run-empty", [result(CHECK_A, "passed")], collected=[CHECK_A])
    after = fold(state, run=empty, events=events, candidates=[])

    r = after["findings"]["CYM-gone"]
    assert r["check"]["state"] == "REPRODUCING", r["check"]
    assert display_state(r) != "VERIFIED FIXED"
    assert r["check"]["adjudicated_by"] is None
    assert r["check"]["not_checked_in"] == "run-empty"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_inadmissible_run_moves_nothing_and_says_why():
    """All 13 committed run records are inadmissible. Feeding one to the fold
    must change no row and name the reasons."""
    from qa.fold import fold

    state = ledger(row("CYM-a", check_state="REPRODUCING", checks=[CHECK_A], pinned=FP1))
    legacy = run("run-legacy", [result(CHECK_A, "passed")], level="none")

    after = fold(state, run=legacy, events=[])
    r = after["findings"]["CYM-a"]
    assert r["check"]["state"] == "REPRODUCING"
    assert r["transitions"] == []
    assert "legacy_schema" in after["rejected_run"]["reasons"]
    assert after["rejected_run"]["run_id"] == "run-legacy"


# ---------------------------------------------------------------------------
# The CHECK axis, exhaustively
# ---------------------------------------------------------------------------
# (prior check state, run scenario) -> expected check state.
# Scenarios are named for what the run record actually contains.
SCENARIOS = {
    "all_passed_V":        ("V", [("passed", FP1)]),
    "all_passed_V_drift":  ("V", [("passed", FP2)]),
    "all_passed_R":        ("R", [("passed", FP1)]),
    "one_failed":          ("V", [("failed", FP1)]),
    "one_inconclusive":    ("V", [("inconclusive", FP1)]),
    "failed_and_inconc":   ("V", [("failed", FP1), ("inconclusive", FP1)]),
    "skipped":             ("V", [("skipped", FP1)]),
    "errored":             ("V", [("error", FP1)]),
}

EXPECTED = {
    # prior state is irrelevant to what the run says, EXCEPT for the pinned
    # fingerprint (which the row carries) -- so the table is keyed on both.
    "all_passed_V":       {"pinned": "PASSING", "unpinned": "PASSING_UNPINNED"},
    "all_passed_V_drift": {"pinned": "CHECK_CHANGED", "unpinned": "PASSING_UNPINNED"},
    "all_passed_R":       {"pinned": None, "unpinned": None},   # exploratory: no transition
    "one_failed":         {"pinned": "REPRODUCING", "unpinned": "REPRODUCING"},
    "one_inconclusive":   {"pinned": "INCONCLUSIVE", "unpinned": "INCONCLUSIVE"},
    "failed_and_inconc":  {"pinned": "REPRODUCING", "unpinned": "REPRODUCING"},
    "skipped":            {"pinned": None, "unpinned": None},   # did not run: no transition
    "errored":            {"pinned": None, "unpinned": None},
}

PRIOR = ["UNVERIFIED", "REPRODUCING", "PASSING", "PASSING_UNPINNED",
         "CHECK_CHANGED", "INCONCLUSIVE"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("prior,scenario,pin", [
    (p, s, pin) for p, s, pin in itertools.product(PRIOR, SCENARIOS, ["pinned", "unpinned"])
])
def test_check_axis_transition_table(prior, scenario, pin):
    """Every (prior state x run outcome x pinned) cell, against a written table.

    A pass counts as verification only under the fingerprint the row last
    failed under. This is the cell that would have caught rewriting
    agent_names from set_equal to subset while the nodeid stayed the same."""
    from qa.fold import fold

    level, outcomes = SCENARIOS[scenario]
    pinned = FP1 if pin == "pinned" else None
    state = ledger(row("CYM-a", check_state=prior, checks=[CHECK_A], pinned=pinned))
    results = [result(CHECK_A, o, fingerprint=fp) for o, fp in outcomes]
    # Several outcomes on one nodeid is not expressible; use one per scenario entry.
    results = results[:1] if len(outcomes) == 1 else [
        result(CHECK_A, outcomes[0][0], fingerprint=outcomes[0][1]),
        result(CHECK_B, outcomes[1][0], fingerprint=outcomes[1][1]),
    ]
    checks = [CHECK_A] if len(outcomes) == 1 else [CHECK_A, CHECK_B]
    state["findings"]["CYM-a"]["checks"] = checks

    after = fold(state, run=run("run-t", results, level=level), events=[])
    got = after["findings"]["CYM-a"]["check"]["state"]
    want = EXPECTED[scenario][pin]

    if want is None:
        assert got == prior, f"{scenario}/{pin}: expected no transition from {prior}, got {got}"
        assert after["findings"]["CYM-a"]["transitions"] == []
    else:
        assert got == want, f"{scenario}/{pin} from {prior}: expected {want}, got {got}"
        if got != prior:
            tx = after["findings"]["CYM-a"]["transitions"]
            assert tx and tx[-1]["to"] == want and tx[-1]["cause"]["run_id"] == "run-t"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_exploratory_pass_is_recorded_but_never_verifies():
    """A level-R run (dirty tree, no tag) that passes is evidence, not a
    verdict. It is recorded so the operator can see it, and it moves nothing.
    None of the 13 committed runs reach level V."""
    from qa.fold import display_state, fold

    events = events_for("CYM-a", "FIX_CLAIMED")
    state = fold(ledger(row("CYM-a", check_state="REPRODUCING",
                            checks=[CHECK_A], pinned=FP1)), events=events)
    after = fold(state, run=run("run-r", [result(CHECK_A, "passed")], level="R"), events=events)

    r = after["findings"]["CYM-a"]
    assert r["check"]["state"] == "REPRODUCING"
    assert display_state(r) == "STILL REPRODUCIBLE"
    assert r["check"]["last_exploratory_pass"]["run_id"] == "run-r"
    assert [t for t in r["transitions"] if t["axis"] == "check"] == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_regression_is_permanent_and_requires_backed_passing():
    """REGRESSED was driven off a timestamp field, so the next merge cleared it
    and the row went green again. A regression is an event in the row's
    history: it is appended, never recomputed, and it can only follow a
    PASSING that a level-V run actually established."""
    from qa.fold import fold

    ev = events_for("CYM-a", "FIX_CLAIMED")
    state = ledger(row("CYM-a", check_state="REPRODUCING", checks=[CHECK_A], pinned=FP1))

    verified = fold(state, run=run("run-v", [result(CHECK_A, "passed")],
                                   at="2026-09-05T10:00:00+00:00"), events=ev)
    assert verified["findings"]["CYM-a"]["check"]["state"] == "PASSING"
    assert verified["findings"]["CYM-a"]["regressions"] == []

    broke = fold(verified, run=run("run-w", [result(CHECK_A, "failed")],
                                   at="2026-09-05T11:00:00+00:00"), events=ev)
    reg = broke["findings"]["CYM-a"]["regressions"]
    assert len(reg) == 1 and reg[0]["at"] == "2026-09-05T11:00:00+00:00"
    assert reg[0]["run_id"] == "run-w" and reg[0]["from_run"] == "run-v"

    # Any number of further folds must not erase or duplicate it.
    quiet = fold(broke, run=run("run-x", [result(CHECK_B, "passed")], collected=[CHECK_B]), events=ev)
    assert quiet["findings"]["CYM-a"]["regressions"] == reg

    again = fold(broke, run=run("run-y", [result(CHECK_A, "failed")],
                                at="2026-09-05T12:00:00+00:00"), events=ev)
    assert len(again["findings"]["CYM-a"]["regressions"]) == 1, \
        "a second consecutive failure is not a second regression"

    # A regression can never follow an exploratory pass, because that pass
    # never established PASSING in the first place.
    explor = ledger(row("CYM-b", check_state="REPRODUCING", checks=[CHECK_B], pinned=FP1))
    explor = fold(explor, run=run("run-e", [result(CHECK_B, "passed")], level="R"), events=[])
    explor = fold(explor, run=run("run-f", [result(CHECK_B, "failed")]), events=[])
    assert explor["findings"]["CYM-b"]["regressions"] == []


# ---------------------------------------------------------------------------
# Display is a composition, never a stored field
# ---------------------------------------------------------------------------
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_display_state_composition_table():
    """The displayed state is computed from the two axes at render time.

    VERIFIED FIXED appears in exactly one cell: our own check passing under
    its pinned fingerprint, next to their claim of a fix. Every other cell
    that says anything about a fix says who is making the claim."""
    from qa.fold import CHECK_STATES, DISPLAY, FILING_STATES, display_state

    assert set(DISPLAY) == set(itertools.product(CHECK_STATES, FILING_STATES)), \
        "the composition table has a hole -- every pair must render something"

    verified = [pair for pair, text in DISPLAY.items() if text == "VERIFIED FIXED"]
    assert verified == [("PASSING", "FIX_CLAIMED")], verified

    assert DISPLAY[("INCONCLUSIVE", "FIX_CLAIMED")] == "NOT REPRODUCIBLE"
    assert DISPLAY[("REPRODUCING", "FIX_CLAIMED")] == "STILL REPRODUCIBLE"
    assert DISPLAY[("REPRODUCING", "NOT_RAISED")] == "NOT RAISED YET"
    assert DISPLAY[("REPRODUCING", "RAISED")] == "RAISED"
    assert DISPLAY[("PASSING_UNPINNED", "FIX_CLAIMED")] != "VERIFIED FIXED"
    assert DISPLAY[("CHECK_CHANGED", "FIX_CLAIMED")] != "VERIFIED FIXED"

    for check in CHECK_STATES:
        assert DISPLAY[(check, "WITHDRAWN")] == "WITHDRAWN", \
            "a withdrawal is ours and terminal, whatever the check says"

    # display_state reads the row; there is no state field to read instead.
    r = row("CYM-a", check_state="PASSING", filing_state="FIX_CLAIMED")
    assert display_state(r) == "VERIFIED FIXED"
    assert "state" not in r, "display state must not be stored on the row"


# ---------------------------------------------------------------------------
# Filing axis
# ---------------------------------------------------------------------------
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_filing_axis_is_a_replay_of_the_journal():
    """FILING is folded from the whole journal every time, so it cannot drift
    from the events and cannot be nudged in place. The vendor's own words move
    it; our checks never do."""
    from qa.fold import fold

    state = ledger(row("CYM-a", checks=[CHECK_A]))

    assert fold(state, events=[])["findings"]["CYM-a"]["filing"]["state"] == "NOT_RAISED"

    raised = fold(state, events=_filed("CYM-a", 46, "pending"))
    assert raised["findings"]["CYM-a"]["filing"]["state"] == "RAISED"
    assert raised["findings"]["CYM-a"]["filing"]["reports"] == [
        {"report_id": 46, "status": "pending"}]

    claimed = fold(state, events=_filed("CYM-a", 46, "fixed"))
    assert claimed["findings"]["CYM-a"]["filing"]["state"] == "FIX_CLAIMED"
    tx = [t for t in claimed["findings"]["CYM-a"]["transitions"] if t["axis"] == "filing"]
    assert tx[-1]["to"] == "FIX_CLAIMED" and tx[-1]["cause"]["event_id"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_filing_transition_requires_evidence_id():
    """Critique gap 2: FIX_CLAIMED x PASSING is the strongest thing the
    dashboard says, and half of it rested on an HTTP body nobody stored. A
    filing event without an evidence_id may not move the axis."""
    from qa.fold import fold

    state = ledger(row("CYM-a", checks=[CHECK_A]))
    events = _filed("CYM-a", 46, "fixed")
    for e in events:
        e.pop("evidence_id", None)

    after = fold(state, events=events)
    r = after["findings"]["CYM-a"]
    assert r["filing"]["state"] == "NOT_RAISED"
    assert "evidence_id" in " ".join(r["filing"]["refused"])


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_folding_the_same_run_twice_changes_nothing():
    """Composing one run must be idempotent, or every consistency check that
    re-folds to compare reports drift it created itself. `reproductions` was
    counting folds rather than runs -- the same species as the timestamp that
    used to drive REGRESSED."""
    from qa.fold import fold

    cand = [candidate("CYM-a", checks=[CHECK_A], severity="S1-INTEGRITY")]
    state = ledger(row("CYM-a", check_state="REPRODUCING", checks=[CHECK_A], pinned=FP1))
    r = run("run-v", [result(CHECK_A, "failed")])

    once = fold(state, run=r, candidates=cand, events=[])
    twice = fold(once, run=r, candidates=cand, events=[])
    assert twice == once, "folding the same run twice moved something"

    later = fold(twice, run=run("run-w", [result(CHECK_A, "failed")],
                                at="2026-09-05T11:00:00+00:00"),
                 candidates=cand, events=[])
    assert later["findings"]["CYM-a"]["reproductions"] == \
        once["findings"]["CYM-a"]["reproductions"] + 1, \
        "a second, genuinely different run did not count"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_supersede_merges_rows_and_excludes_from_tiles():
    """Critique gap 6. Renaming a claim retires the old row and opens a new
    one for the same defect, so without a supersede event the deferred
    rename-gap counts one defect twice and both halves sit in the filter."""
    from qa.fold import DISPLAY, display_state, fold

    state = ledger(row("CYM-old", check_state="REPRODUCING", checks=[CHECK_A]),
                   row("CYM-new", check_state="REPRODUCING", checks=[CHECK_B]))
    events = _filed("CYM-old", 46, "pending") + [
        event("supersede", at="2026-09-05T13:00:00+00:00", by="operator",
              source="scripts/withdraw.py", from_id="CYM-old", to_id="CYM-new",
              reason="the claim was renamed; same defect, new id"),
    ]

    after = fold(state, events=events)
    old, new = after["findings"]["CYM-old"], after["findings"]["CYM-new"]

    assert old["filing"]["state"] == "SUPERSEDED"
    assert display_state(old) == "SUPERSEDED"
    assert old["superseded_by"] == "CYM-new"
    assert new["supersedes"] == ["CYM-old"]

    # Terminal: nothing the vendor says afterwards moves it back.
    later = fold(state, events=events + _filed("CYM-old", 46, "fixed"))
    assert later["findings"]["CYM-old"]["filing"]["state"] == "SUPERSEDED"

    # And the composition table still has no holes.
    for check in ("UNVERIFIED", "REPRODUCING", "PASSING"):
        assert DISPLAY[(check, "SUPERSEDED")] == "SUPERSEDED"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_failed_read_marks_stale_and_does_not_move_filing():
    """Operating rule 8. bounty.py could not tell 401 from an empty tracker,
    so an expired key read as "the vendor closed everything"."""
    from qa.fold import fold

    state = ledger(row("CYM-a", checks=[CHECK_A]))
    events = _filed("CYM-a", 46, "fixed")
    events.append(event("vendor_read", at="2026-09-05T12:00:00+00:00",
                        source="scripts/bounty.py", klass="unauthorized",
                        evidence_id="ev-9"))

    after = fold(state, events=events)
    r = after["findings"]["CYM-a"]
    assert r["filing"]["state"] == "FIX_CLAIMED", "a failed read must not undo a good one"
    assert r["filing"]["stale_from"] == "2026-09-05T12:00:00+00:00"
