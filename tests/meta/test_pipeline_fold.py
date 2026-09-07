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

    # Green requires our check to PASS. Nothing else does, and no combination
    # of things the vendor said can produce it.
    verified = [pair for pair, text in DISPLAY.items() if text == "VERIFIED FIXED"]
    assert {check for check, _ in verified} == {"PASSING"}, verified
    assert set(verified) == {("PASSING", "RAISED"), ("PASSING", "REPLIED"),
                             ("PASSING", "FIX_CLAIMED")}, verified

    assert DISPLAY[("INCONCLUSIVE", "FIX_CLAIMED")] == "OUR CHECK CANNOT TELL"
    # Renamed 2026-09-05. The old label, "NOT REPRODUCIBLE", read as a
    # measurement -- we ran it and it did not happen -- when it means we
    # could not run it to a conclusion. The operator read it as "then it
    # is fixed or it was never real", which are indeed the only honest
    # destinations; the state is a waiting room, so it now names whose
    # problem it is.
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
def test_a_full_run_can_say_a_check_is_gone_and_a_partial_one_cannot():
    """Six rows name reconciliation pairs that no longer exist -- a claim was
    renamed, a source dropped. They sat as "not checked", indistinguishable
    from a row a partial run skipped, wearing a stale-figures tag nobody could
    act on. A full run that did not COLLECT the check has established it is
    gone, and that is nameable and fixable: rebind it, or retire it.

    A partial run must never draw that conclusion, which is why the run
    records whether it offered the whole suite."""
    from qa.fold import fold

    state = ledger(row("CYM-a", check_state="REPRODUCING", checks=[CHECK_A], pinned=FP1))

    partial = run("run-partial", [result(CHECK_B, "passed")], collected=[CHECK_B])
    partial["selector_full"] = False
    after = fold(state, run=partial, events=[])
    assert after["findings"]["CYM-a"]["check"]["state"] == "REPRODUCING"
    assert after["findings"]["CYM-a"]["check"]["not_checked_in"] == "run-partial"

    full = run("run-full", [result(CHECK_B, "passed")], collected=[CHECK_B])
    full["selector_full"] = True
    after = fold(state, run=full, events=[])
    r = after["findings"]["CYM-a"]["check"]
    assert r["state"] == "UNVERIFIABLE"
    assert r["unverifiable_reason"] == "check_missing"
    assert r["missing_checks"] == [CHECK_A]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_evidence_only_check_verifies_nothing():
    """conclude() never raises for an evidence-role measurement, so such a
    check passes whatever it observes. Letting that pass establish PASSING
    would verify a fix on the strength of a check that cannot fail --
    precisely the defect the role split was introduced to prevent.

    CYM-clob_pair_count is the live case: one marketing sentence against
    another, neither of which counts a single CLOB pair."""
    from qa.fold import display_state, fold

    ev = result(CHECK_A, "passed")
    ev["role"] = "evidence"
    ev["measurement"] = {"verdict": "passed", "reason": "9 vs 568", "role": "evidence"}

    state = ledger(row("CYM-a", check_state="REPRODUCING", checks=[CHECK_A], pinned=FP1))
    after = fold(state, run=run("run-v", [ev]), events=[])

    r = after["findings"]["CYM-a"]
    assert r["check"]["state"] == "REPRODUCING", "an unfailable check verified something"
    assert r["check"]["evidence_only"] == "run-v"
    assert display_state(r) != "VERIFIED FIXED"
    assert [t for t in r["transitions"] if t["axis"] == "check"] == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_passing_run_re_measures_the_row_too():
    """Only failures used to refresh a row's numbers, because only failures
    produce a candidate. So a row whose check started passing kept the figures
    from the day it broke and wore "figures not re-measured" for ever -- on
    exactly the rows that were fine. Measuring and proposing a defect are two
    different acts, and a run that ran the check has measured it."""
    from qa.fold import fold

    state = ledger(row("CYM-a", check_state="REPRODUCING", checks=[CHECK_A], pinned=FP1))
    state["findings"]["CYM-a"]["detail"] = {"left": 46, "right": 46}
    state["findings"]["CYM-a"]["provenance"] = {"source": "legacy", "measured_at": None}

    passing = result(CHECK_A, "passed")
    passing["measurement"] = {"verdict": "passed", "reason": "25 of 46, as declared",
                              "left": 25, "right": 46, "role": "verdict"}
    after = fold(state, run=run("run-v", [passing]), events=[])

    r = after["findings"]["CYM-a"]
    assert r["provenance"]["measured_at"], "a passing run left the row unmeasured"
    assert r["provenance"]["run_id"] == "run-v"
    assert r["detail"]["left"] == 25, "the row still quotes the figures from the day it broke"
    assert "25 of 46" in r["detail"]["reason"]


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


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_journal_only_fold_keeps_the_run_that_last_judged_the_rows():
    """A fold that adjudicated nothing must not un-adjudicate what came before.

    `ledger.py --events-only` over a single appended event dropped `run_id`
    and `run_level` from the header, so the console read "none admissible"
    while every row still named the level-V run that had judged it. No row had
    moved. The rows were right and the header was wrong, and the operator's
    fix for a wrong header is to re-fold -- which is how a header bug turns
    into a state change nobody wanted.

    Carried, not composed: `run_carried` marks the difference so the CLI can
    say "rows still stand on X" rather than claiming this fold judged it.
    """
    from qa.fold import fold

    cand = [candidate("CYM-a", checks=[CHECK_A], severity="S1-INTEGRITY")]
    state = ledger(row("CYM-a", check_state="REPRODUCING", checks=[CHECK_A], pinned=FP1))

    judged = fold(state, run=run("run-v", [result(CHECK_A, "failed")]),
                  candidates=cand, events=[])
    assert judged["run_id"] == "run-v"
    assert not judged.get("run_carried"), "a fold that composed a run did not carry it"

    carried = fold(judged, events=[])
    assert carried["run_id"] == judged["run_id"], \
        "a journal-only fold erased the run that last judged the rows"
    assert carried["run_level"] == judged["run_level"]
    assert carried["updated_at"] == judged["updated_at"]
    assert carried["run_carried"] is True, "carried attribution was not marked as carried"
    assert carried["findings"] == judged["findings"], \
        "a journal-only fold over no events moved a row"

    # Nothing to carry is still nothing: a first fold must not invent one.
    assert "run_id" not in fold(None, events=[])


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_failed_read_marks_every_row_and_a_clean_one_clears_it():
    """Rule 8's mark has to be able to go out again.

    A failed read of their tracker marks every row stale, so "they have said
    nothing since" is never read as "we could not hear them". It was written
    and never cleared: the first non-ok read in the journal's history would
    have marked every row in every fold from then on, forever. That is the
    badge nobody can clear -- the same defect the reply dating in render.py
    was fixed for, one axis over. It had never fired only because all 33
    vendor_read events so far are ok.

    A read that records no class at all speaks neither way: it is not evidence
    that the tracker was readable, and not evidence that it was not.
    """
    from qa.fold import fold

    state = ledger(row("CYM-a", check_state="REPRODUCING", checks=[CHECK_A]))
    read = lambda at, klass: {                                    # noqa: E731
        "type": "vendor_read", "at": at, "by": "agent",
        "source": "scripts/bounty.py", "klass": klass,
    }

    def stale(events):
        return fold(state, events=events)["findings"]["CYM-a"]["filing"].get("stale_from")

    bad = read("2026-09-05T10:00:00+00:00", "unauthorized")
    good = read("2026-09-05T11:00:00+00:00", "ok")

    assert stale([bad]) == "2026-09-05T10:00:00+00:00", "a failed read did not mark the row"
    assert stale([bad, good]) is None, "a clean read afterwards did not clear the mark"
    assert stale([good]) is None
    assert stale([good, bad]) == "2026-09-05T10:00:00+00:00", \
        "a failure after a clean read must mark again"

    unknown = {"type": "vendor_read", "at": "2026-09-05T12:00:00+00:00",
               "by": "agent", "source": "scripts/bounty.py"}
    assert stale([bad, unknown]) == "2026-09-05T10:00:00+00:00", \
        "a classless read cleared a mark it is no evidence against"


# ---------------------------------------------------------------------------
# BNT: their status vocabulary, and the half of it that read as silence
# ---------------------------------------------------------------------------
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_rejected_report_is_not_the_same_as_no_answer():
    """`invalid` moved the axis exactly as far as hearing nothing did.

    Two vocabularies exist for one programme. The bounty API's status field has
    carried four values across 608 observations -- fixed, invalid, pending,
    validated -- while their public tracker uses a disjoint set (resolved,
    completed, wont_fix, qa_testing, implementing, rejected, pending). Only the
    API reaches this fold: scripts/bounty.py emits vendor_status from
    my-reports and from nothing else.

    The old rule was `FIX_CLAIMED if status in {fixed, resolved, completed,
    closed} else RAISED`, written against the tracker. So of the two values the
    API actually sends that are not "fixed", `invalid` (45 occurrences) and
    `validated` (10) both landed on RAISED -- the state that means "filed, no
    answer". Being told our report is worthless read as silence.

    **And the axis still reads them that way, deliberately.** Mapping `invalid`
    onto REPLIED was written on 2026-09-07 and the fold refused to write it:
    this axis is a replay of the journal, so a change to how a status is READ
    rewrites the history of every row that ever carried it -- five rows would
    have grown a REPLIED between transitions already recorded, and write_ledger
    refuses a ledger whose transitions are not an extension of the ones on
    disk. That guard is correct. RAISED is what we believed on 2026-09-04, and
    a transition log records what we believed, not what we later learned.

    So this test pins the shape of the compromise, in both directions: the
    status vocabulary does not move the axis beyond a fix claim, REPLIED is
    reachable only through an explicit `reply` event, and the answer we were
    missing is delivered by the `disputed` obligation instead -- which reads
    the report's current status and touches no transition. The next test is
    that half. Do not "fix" this one by mapping the statuses; fix it by
    freezing the history first, and then it is a migration, not a rule.
    """
    from qa.fold import fold

    def filing(status, events=None):
        state = ledger(row("CYM-a", check_state="REPRODUCING"))
        out = fold(state, events=events or _filed("CYM-a", 46, status))
        return out["findings"]["CYM-a"]["filing"]

    assert filing("pending")["state"] == "RAISED",         "pending is the vendor not having answered yet"
    assert filing("fixed")["state"] == "FIX_CLAIMED"
    assert filing("paid")["state"] == "FIX_CLAIMED",         "they paid for it, which is a fix claim with money behind it"

    for engaged in ("validated", "invalid", "triaging", "ready_for_review"):
        assert filing(engaged)["state"] == "RAISED", (
            f"{engaged!r} moved the axis past RAISED. That reading is more "
            f"accurate and it is also retroactive -- see this docstring before "
            f"changing it back")
        assert filing(engaged)["reports"][0]["status"] == engaged,             "the status itself is recorded on the report, which is what disputed reads"

    replied = fold(ledger(row("CYM-a", check_state="REPRODUCING")),
                   events=_filed("CYM-a", 46, "invalid") + [
                       event("reply", at="2026-09-05T10:00:00+00:00",
                             report_id=46, findings=["CYM-a"],
                             evidence_id="ev-3")])
    assert replied["findings"]["CYM-a"]["filing"]["state"] == "REPLIED",         "an explicit reply event is the one route to REPLIED, and it still works"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_rejection_we_still_reproduce_owes_a_decision():
    """Their `invalid` against our failing check is ours to settle, not theirs.

    One of the two has to give: either we withdraw the finding because they are
    right, or we answer them because we are. Neither happens by itself, and
    without an obligation the row sits looking filed and quiet.

    Nothing is owed while our own check passes -- then the disagreement is
    academic and the row is closing anyway.
    """
    from qa.fold import fold

    def owed(status, check_state):
        state = ledger(row("CYM-a", check_state=check_state))
        out = fold(state, events=_filed("CYM-a", 46, status))
        return out["findings"]["CYM-a"]["obligations"]["disputed"]

    assert owed("invalid", "REPRODUCING") == [46],         "a rejected report we still reproduce owes a decision"
    assert owed("invalid", "PASSING") == [],         "nothing is owed once our own check agrees with them"
    assert owed("fixed", "REPRODUCING") == []
    assert owed("pending", "REPRODUCING") == []

    # The other way the disagreement ends, and the one this got wrong on its
    # first firing in the project's life: we gave them the point. The fold
    # printed "OWED: disputed" beside CYM-trusted-receives-nothing-above-its-
    # tier, a WITHDRAWN row -- a decision demanded of somebody who had already
    # made it, on a terminal state, which is precisely the badge nobody can
    # clear that CLAUDE.md forbids. Withdrawal owes a retraction (rule 11),
    # not a decision.
    # The two events name their rows differently -- withdraw through
    # `findings`, supersede through from_id/to_id, which the fold handles
    # before the target lookup. Getting that wrong is why the precondition
    # below is asserted separately: written as one, this test passed a
    # SUPERSEDED case that had never left RAISED.
    settlements = {
        "WITHDRAWN": {"findings": ["CYM-a"]},
        "SUPERSEDED": {"from_id": "CYM-a", "to_id": "CYM-b"},
    }
    for terminal, naming in settlements.items():
        evt = "withdraw" if terminal == "WITHDRAWN" else "supersede"
        out = fold(ledger(row("CYM-a", check_state="REPRODUCING")),
                   events=_filed("CYM-a", 46, "invalid") + [
                       event(evt, at="2026-09-05T11:00:00+00:00",
                             reason="they were right", **naming)])
        settled = out["findings"]["CYM-a"]
        assert settled["filing"]["state"] == terminal, \
            f"the {evt} event did not reach the axis; the case below proves nothing"
        assert settled["obligations"]["disputed"] == [], (
            f"a {terminal} row is still asked to settle a dispute it closed by "
            f"being {terminal}")


# ---------------------------------------------------------------------------
# VER: telling them our check passes -- outbound, and owed until it is sent
# ---------------------------------------------------------------------------
FP = "aee41113b423d34dbb0fb7a237f679ec142e320ffd706e3a3645b1a3b80b4cd5"


def _verification(fid="CYM-a", report_id=46, fingerprint=FP, outcome="accepted",
                  at="2026-09-07T13:00:00+00:00", **over):
    base = {"finding_id": fid, "report_id": report_id, "fingerprint": fingerprint,
            "verdict": "pass", "outcome": outcome, "http_status": 200,
            "run_id": "run-1", "evidence_id": "ev-9"}
    base.update(over)
    return event("verification_outcome", at=at, source="scripts/verify.py", **base)


def _verified_row(fid="CYM-a"):
    """A row that passes under the fingerprint it last failed under."""
    return row(fid, check_state="PASSING", pinned=FP)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_verification_we_send_moves_neither_axis():
    """VER: it is our statement, so it changes nothing about their side.

    The two axes have exactly one mover each -- an admissible run for CHECK, a
    journal event of THEIRS for FILING -- and a reporter verification is
    neither. It is us telling them something we already knew, so the only
    honest effect is a record that we said it.

    The danger this pins is concrete: reusing filing_outcome would have been
    the cheap route, and qa/fold.py moves any accepted outcome carrying a
    report_id to RAISED and attaches the report, with no notion of which
    endpoint it went to. That would have invented filings that never happened
    on rows that were already closed.
    """
    from qa.fold import fold

    before = fold(ledger(_verified_row()), events=_filed("CYM-a", 46, "fixed"))
    after = fold(ledger(_verified_row()),
                 events=_filed("CYM-a", 46, "fixed") + [_verification()])

    b, a = before["findings"]["CYM-a"], after["findings"]["CYM-a"]
    assert a["check"]["state"] == b["check"]["state"] == "PASSING"
    assert a["filing"]["state"] == b["filing"]["state"] == "FIX_CLAIMED"
    assert len(a["transitions"]) == len(b["transitions"]), \
        "sending a verification wrote a transition; it is not a state change"

    sent = a["filing"]["verifications"]
    assert [(v["report_id"], v["fingerprint"], v["verdict"]) for v in sent] == \
        [(46, FP, "pass")], "the verification we sent is not on the row"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_verification_whose_response_was_not_captured_is_refused():
    """Gap 2, and it cuts both ways: our claim rests on their 200.

    The evidence_id gate exists for events reporting what the vendor said.
    An outcome is exactly that -- it says their server accepted the
    verification -- so an uncaptured one is a claim with nothing behind it.
    """
    from qa.fold import fold

    out = fold(ledger(_verified_row()),
               events=_filed("CYM-a", 46, "fixed") + [_verification(evidence_id=None)])
    filing = out["findings"]["CYM-a"]["filing"]
    assert filing["verifications"] == []
    assert any("evidence_id" in r for r in filing["refused"]), \
        "an uncaptured verification was recorded as if the server had answered"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_verification_debt_is_keyed_on_the_fingerprint_not_the_run():
    """VER: the property that stops this becoming 27 POSTs every sweep.

    Every sweep re-adjudicates every PASSING row, so `adjudicated_by.run_id`
    moves on all of them whether or not anything changed. An obligation keyed
    on the run would therefore come due again after each one, and we would
    send Cymetica the same 27 verifications daily -- a badge that clears
    itself into spam, which is worse than a badge nobody can clear.

    Keyed on the fingerprint it is a statement about the CHECK: we have told
    them this check passes under this definition. It comes due once, clears
    when sent, and speaks again only when the definition moves -- which is
    genuinely new information and the one case worth another request.
    """
    from qa.fold import fold

    filed = _filed("CYM-a", 46, "fixed")

    owed = fold(ledger(_verified_row()), events=filed)
    assert owed["findings"]["CYM-a"]["obligations"]["verification_owed"] == [46], \
        "a passing, fix-claimed row owes them the evidence and does not say so"

    cleared = fold(ledger(_verified_row()), events=filed + [_verification()])
    assert cleared["findings"]["CYM-a"]["obligations"]["verification_owed"] == [], \
        "the debt survived the verification that paid it"

    # A later run, same definition: nothing new to tell them.
    again = fold(ledger(_verified_row()),
                 events=filed + [_verification()],
                 run={"run_id": "run-2", "schema": 2})
    assert again["findings"]["CYM-a"]["obligations"]["verification_owed"] == [], \
        "the next sweep asked for the same 27 verifications over again"

    # A changed definition IS new information.
    moved = fold(ledger(row("CYM-a", check_state="PASSING", pinned="a-new-fingerprint")),
                 events=filed + [_verification()])
    assert moved["findings"]["CYM-a"]["obligations"]["verification_owed"] == [46], \
        "the check passes under a definition we have never told them about"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_nothing_is_owed_where_there_is_nothing_to_verify():
    """A debt that comes due on rows we cannot pay is a badge nobody clears."""
    from qa.fold import fold

    def owed(state, events, pinned=FP):
        out = fold(ledger(row("CYM-a", check_state=state, pinned=pinned)), events=events)
        return out["findings"]["CYM-a"]["obligations"]["verification_owed"]

    assert owed("PASSING", []) == [], "never filed, so there is no report to verify on"
    assert owed("REPRODUCING", _filed("CYM-a", 46, "fixed")) == [], \
        "our check still fails; a pass verification would be a false statement"
    assert owed("PASSING", _filed("CYM-a", 46, "fixed"), pinned=None) == [], \
        "never seen failing under this definition, so passing proves no fix"
