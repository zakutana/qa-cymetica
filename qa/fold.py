"""The fold: ledger = f(previous rows, one run record, the whole journal).

This module replaces `merge()` in scripts/ledger.py, which the audit found
responsible for most of the 71 self-inflicted state changes an operator
watched. The difference is not that the rules are stricter; it is that there
are rules at all, and that nothing here can write a state without also writing
what caused it.

Two axes, never overwriting each other:

    CHECK    moved only by an admissible run record that adjudicated every
             check the row declares -- and, to UNVERIFIABLE only, by an
             operator's retire/rebind event that leaves the row nothing to
             adjudicate (RC02, deep pass of 2026-09-24), or the split that
             made a row whose one check is no nodeid (X03, 2026-10-25)
    FILING   moved only by an event in the append-only journal

The state you read on the dashboard is the composition of the two, computed at
render time from the table below. It is not stored, so it cannot be assigned,
and there is no field to hand-edit. `VERIFIED FIXED` occupies exactly one cell:
our own check passing under the fingerprint it last failed under, next to the
vendor's claim that they fixed it. Everything else that mentions a fix names
whose claim it is.

The whole module is pure: same inputs, same output, no clock, no filesystem.
Timestamps come from the run record and the events, which is what makes a
transition's `at` the moment the evidence was produced rather than the moment
somebody happened to re-run the script.
"""

from __future__ import annotations

import copy
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Iterable, Sequence

from qa.state import admissibility, event_id

CHECK_STATES = ("UNVERIFIED", "REPRODUCING", "PASSING", "PASSING_UNPINNED",
                "CHECK_CHANGED", "INCONCLUSIVE", "UNVERIFIABLE")

# SUPERSEDED is terminal and ours, like WITHDRAWN. Critique gap 6: renaming a
# claim retires the old row as UNVERIFIABLE(check_removed) and opens a new one
# for the same defect, so without this the deferred rename-gap counts the
# defect twice and both halves show in the filter.
FILING_STATES = ("NOT_RAISED", "RAISED", "REPLIED", "FIX_CLAIMED", "WITHDRAWN",
                 "SUPERSEDED")

# How far along the vendor conversation a filing state is. The axis moves
# forward only -- a later `pending` does not undo an earlier `fixed`, because
# a tracker that forgets is not evidence that they changed their mind.
_FILING_RANK = {"NOT_RAISED": 0, "RAISED": 1, "REPLIED": 2, "FIX_CLAIMED": 3}

# Terminal states, ours to declare. Neither can be moved by anything the
# vendor subsequently says.
_TERMINAL = ("WITHDRAWN", "SUPERSEDED")

# Their REPORT statuses, and which of ours each one means.
#
# Read off the enum the platform publishes at
# GET /api/v1/bounty/my-reports -> status_vocabulary.report_status, verified
# live on 2026-09-07. There is a second vocabulary, ticket_status (open,
# investigating, in_progress, resolved, closed, wont_fix), which belongs to the
# ET-number ticket rather than the bounty report and answers a different
# question: the report status is the bounty state, the ticket status is the fix
# state. Only the report status reaches this fold -- scripts/bounty.py emits
# vendor_status from my-reports alone.
#
# The rule here used to be `FIX_CLAIMED if status in {fixed, resolved,
# completed, closed} else RAISED`. Every part of that was wrong. `resolved` and
# `closed` are ticket statuses, so they could not arrive; `completed` is in
# neither enum and was invented; and everything the API actually sends other
# than "fixed" fell through to RAISED, the state that means "filed, and they
# have not answered". Being told our report is invalid read as silence, 45
# times. tests/rest/test_status_vocabulary_is_mapped.py now holds these sets
# against the published enum, so a value they add cannot land here unmapped.
_FIX_CLAIMED_STATUSES = frozenset({"fixed", "paid"})

# They looked and said no. Their answer, not their silence -- and against a
# check of ours that still fails, a disagreement one of us has to settle.
_REJECTED_STATUSES = frozenset({"invalid", "duplicate", "wontfix"})

# They engaged with the report without claiming a fix. openclaw_testing and
# ready_for_review are their own QA stages, which is work on the report and not
# a claim about it.
#
# NOT consulted by the fold. This names what we KNOW means engagement; the
# FILING axis does not move on it, because that axis is a replay and reading a
# status differently rewrites history the forward-only guard protects. It is
# used to tell a status we understand from one we have never seen -- which is
# what tests/rest/test_status_vocabulary_is_mapped.py holds against their
# published enum. See the vendor_status branch below for the whole of it.
_REPLIED_STATUSES = _REJECTED_STATUSES | frozenset({
    "triaging", "validated", "in_progress", "openclaw_testing",
    "ready_for_review",
})

# Filed, and nothing has happened yet.
_RAISED_STATUSES = frozenset({"pending"})


def _display_cell(check: str, filing: str) -> str:
    if filing == "SUPERSEDED":
        # Replaced by another row for the same defect. Terminal, excluded from
        # the tiles, and kept visible so the report ids filed under the old id
        # still lead somewhere.
        return "SUPERSEDED"
    if filing == "WITHDRAWN":
        # Ours and terminal. Whatever the check now says about a finding we
        # retracted, the retraction is the fact of record.
        return "WITHDRAWN"
    if check == "UNVERIFIABLE":
        return "UNVERIFIABLE"
    if check == "PASSING":
        # Our own check passes under the fingerprint it last failed under.
        # That is the verification, and whether they also claimed a fix does
        # not change whether the thing is broken. Splitting it into
        # "PASSING, UNCLAIMED" added a state without adding an action: both
        # mean nothing to do. Who gets the credit is still visible inside the
        # row, where it belongs, rather than as a colour on the list.
        #
        # NEVER RAISED stays separate: it passes and they were never told, so
        # there is no conversation to read and no report to point at.
        return {
            "NOT_RAISED": "PASSING, NEVER RAISED",
            "RAISED": "VERIFIED FIXED",
            "REPLIED": "VERIFIED FIXED",
            "FIX_CLAIMED": "VERIFIED FIXED",
        }[filing]
    if check == "PASSING_UNPINNED":
        # Was "PASSING (UNPINNED)", which named the mechanism rather than the
        # situation, so it read as jargon and hid two rows that should have
        # been withdrawn. The situation is: it passes, and we have no record of
        # ever having seen it fail, so there is no fix to credit anyone with.
        return "NEVER SEEN BROKEN"
    if check == "CHECK_CHANGED":
        return "CHECK CHANGED"
    if check == "INCONCLUSIVE":
        # Was "NOT REPRODUCIBLE", which sounds like a result -- we ran it and
        # it did not happen -- when it means the opposite: we could not run it
        # to a conclusion at all. The operator read it as "so it is fixed, or
        # it was never real" and was right to: those ARE the only two honest
        # destinations. This state is a waiting room, not an answer, so it now
        # says whose problem it is. Ours: repair the check or retire it.
        return "OUR CHECK CANNOT TELL"
    if check == "REPRODUCING":
        # Once they have engaged -- replied, or claimed a fix -- the fact worth
        # showing is that it still breaks. "THEY REPLIED" beside a failing
        # check hid exactly that: #47 read as a conversation in progress while
        # the check said filing was still ungated.
        return {
            "NOT_RAISED": "NOT RAISED YET",
            "RAISED": "RAISED",
            "REPLIED": "STILL REPRODUCIBLE",
            "FIX_CLAIMED": "STILL REPRODUCIBLE",
        }[filing]
    return {  # UNVERIFIED -- no admissible run has ever adjudicated this row
        "NOT_RAISED": "UNVERIFIED",
        "RAISED": "RAISED",
        "REPLIED": "THEY REPLIED",
        "FIX_CLAIMED": "FIX CLAIMED",
    }[filing]


DISPLAY = {
    (check, filing): _display_cell(check, filing)
    for check in CHECK_STATES for filing in FILING_STATES
}


def display_state(row: dict) -> str:
    """What the dashboard shows for this row. Composed, never stored."""
    return DISPLAY[(row["check"]["state"], row["filing"]["state"])]


# ---------------------------------------------------------------------------
# CHECK axis
# ---------------------------------------------------------------------------
def _fingerprint_of(results: Sequence[dict]) -> str | None:
    """One check's fingerprint, or a combined one for a multi-check row."""
    fps = [r.get("check_fingerprint") for r in results]
    if len(fps) == 1:
        return fps[0]
    if any(f is None for f in fps):
        return None
    joined = "\n".join(f"{r['nodeid']}={r.get('check_fingerprint')}"
                       for r in sorted(results, key=lambda r: r["nodeid"]))
    return "sha256:" + hashlib.sha256(joined.encode("utf-8")).hexdigest()[:32]


def _measurement_detail(results: Sequence[dict]) -> dict:
    """What these results actually measured, from the Measurement objects.

    Never from the traceback. That scrape is how a line of our own source once
    reached the vendor as evidence about their platform.
    """
    detail: dict = {}
    for result in results:
        measurement = (result or {}).get("measurement") or {}
        for field in ("left", "right", "sources", "population"):
            if measurement.get(field) is not None and field not in detail:
                detail[field] = measurement[field]
        if measurement.get("reason") and "reason" not in detail:
            detail["reason"] = measurement["reason"]
    return detail


def _structural_reason(checks: Sequence[str]) -> str | None:
    """Why this row can never be adjudicated, if it cannot.

    This is a property of the row, not an outcome of a run, so it carries no
    transition: `checks` itself only changes through a rebind_check or
    retire_check event, and that event is the cause. Five ledger rows list
    scripts/inventory.py here -- pytest does not collect scripts, so they sat
    outside the verification machinery while still displaying a state.
    """
    if not checks:
        return "no_checks"
    if any("::" not in c for c in checks):
        return "check_not_a_nodeid"
    return None


def _structural_pass(rows: Iterable[dict], events: Sequence[dict]) -> None:
    """Without a run, a row that can never be adjudicated says so.

    Only an event changes what a row declares without a run: a rebind or a
    retirement, or the split that made the row with its one check (X03, deep
    pass of 2026-10-25). The last of them for this row is the cause. None means
    the row was already so from its run, and already here.
    """
    for row in rows:
        reason = _structural_reason(row.get("checks") or [])
        if not reason:
            continue
        defining = [e for e in events
                    if (e.get("finding_id") == row.get("id")
                        and e.get("type") in ("rebind_check", "retire_check"))
                    or (e.get("type") == "split_report" and e.get("to_id") == row.get("id"))]
        if defining:
            _unverifiable(row, reason, {"event_id": event_id(defining[-1])},
                          defining[-1].get("at"))
        else:
            row["check"]["state"] = "UNVERIFIABLE"
            row["check"]["unverifiable_reason"] = reason


def _unverifiable(row: dict, reason: str, cause: dict, at) -> None:
    """Enter UNVERIFIABLE with the transition that says why. A4 of the review
    of 2026-09-23 (3/3): it was the one state entered without one, so the
    history could not say which run or event took a row there."""
    check = row["check"]
    prior = check.get("state")
    check["state"] = "UNVERIFIABLE"
    check["unverifiable_reason"] = reason
    if prior != "UNVERIFIABLE":
        row["transitions"].append({"axis": "check", "from": prior,
                                   "to": "UNVERIFIABLE", "cause": cause, "at": at})


def _standing(row: dict, prior: str) -> str:
    """The last state a run ESTABLISHED: an INCONCLUSIVE reading measured
    nothing, so the state before it is still the one a fall is from. Read
    off the row's own transitions, which record every `from`."""
    standing = prior
    for t in reversed(row.get("transitions") or []):
        if standing != "INCONCLUSIVE":
            break
        if t.get("axis") == "check" and t.get("to") == "INCONCLUSIVE":
            standing = t.get("from") or standing
    return standing


# How bad an outcome is, for choosing one result per check (X02).
_OUTCOME_RANK = {"failed": 4, "error": 3, "inconclusive": 2, "skipped": 1, "passed": 0}


def results_by_nodeid(run: dict) -> dict[str, dict]:
    """One result per check: the worst outcome its run recorded for it.

    X02 (deep pass of 2026-10-25, 3/3): a dict comprehension kept the LAST
    result per nodeid, and qa/report_plugin.py records a failed call and then
    its teardown's `error` for the same nodeid -- so the error won, the fold
    read "not checked in", and the failure the call measured was lost. A failed
    call stays failed whatever its teardown did; on a tie the call phase wins,
    being the one that carries the measurement, then the later result. Any
    other call-then-teardown pair comes out as last-wins did. scripts/withdraw.py and
    scripts/verify.py read the same selection, so a pin is what the fold reads.
    """
    chosen: dict[str, tuple] = {}
    for index, result in enumerate(run.get("results") or []):
        key = (_OUTCOME_RANK.get(result.get("outcome"), 0),
               result.get("phase", "call") == "call", index)
        nodeid = result["nodeid"]
        if nodeid not in chosen or key > chosen[nodeid][0]:
            chosen[nodeid] = (key, result)
    return {nodeid: result for nodeid, (_, result) in chosen.items()}


def _apply_run(row: dict, run: dict, level: str) -> None:
    """Move the CHECK axis of one row according to one admissible run."""
    check = row["check"]
    checks = row.get("checks") or []

    at = run.get("finished_at") or run.get("started_at")
    run_id = run["run_id"]

    reason = _structural_reason(checks)
    if reason:
        _unverifiable(row, reason, {"run_id": run_id}, at)
        return
    results = results_by_nodeid(run)
    mine = [results.get(nodeid) for nodeid in checks]

    # A run that offered the whole suite and did not COLLECT this check has
    # established that the check is gone -- a claim was renamed, a source
    # dropped, a parametrisation changed. That is a fact about the row, not a
    # gap in this run, and saying so is the difference between a row that
    # merely looks stale and one whose problem is nameable and fixable
    # (rebind it, or retire it).
    if run.get("selector_full"):
        collected = set(run.get("collected") or [])
        missing = [c for c in checks if c not in collected]
        if missing:
            check["missing_checks"] = sorted(missing)
            _unverifiable(row, "check_missing", {"run_id": run_id}, at)
            return

    # Rule 2. A check that did not run tells us nothing. This is the branch
    # merge() reached only after its sticky-verified latch had already
    # returned, which is how partial runs closed rows they never touched.
    if any(r is None or r.get("outcome") in ("skipped", "error") for r in mine):
        check["not_checked_in"] = run_id
        return
    check.pop("not_checked_in", None)

    # What this run measured; it becomes the row's reading where the run
    # adjudicates the row (below), and rides beside it where it does not.
    measured = _measurement_detail(mine)

    def _measured_here() -> None:
        if measured:
            row["detail"] = measured
        row["provenance"] = {"run_id": run_id, "measured_at": at}

    # An evidence-role measurement can never fail -- conclude() returns rather
    # than raising, because comparing one sentence against another says
    # nothing about behaviour. So its "pass" is not evidence of anything and
    # must not establish PASSING: that is a check which passes because of how
    # it asks, which is the whole class this plan exists to stop. It measures
    # and adjudicates nothing -- so its reading does not become the row's
    # either (X01, deep pass of 2026-10-25): `_measured_here()` here replaced
    # the row's detail and provenance at any level, and an a2a row read "not
    # asked ... QA_ALLOW_A2A_SEND" as what a level-R run had measured. The
    # reading rides beside, in the record `evidence_only` names.
    roles = {(r.get("role") or (r.get("measurement") or {}).get("role") or "verdict")
             for r in mine}
    if roles == {"evidence"}:
        check["evidence_only"] = run_id
        return
    check.pop("evidence_only", None)

    outcomes = [r["outcome"] for r in mine]
    prior = check["state"]

    if "failed" in outcomes:
        new = "REPRODUCING"
        # Pin the fingerprint the row failed under. A later pass counts as a
        # verification only under this same definition.
        check["pinned_fingerprint"] = _fingerprint_of(mine)
        # And remember it was SEEN failing under it: a hand pin on a definition
        # in this list is no longer only our word (see _mark_repins).
        failed_under = check.setdefault("failed_under", [])
        if check["pinned_fingerprint"] not in failed_under:
            failed_under.append(check["pinned_fingerprint"])
        # Every state a level-V pass establishes, not PASSING alone (A7 of
        # the review of 2026-09-23, 3/3): failing after a pass under a
        # changed or never-failed definition is a regression too. Read
        # through any INCONCLUSIVE in between (RC04, deep pass of
        # 2026-09-24): one transport error erased the regression and its
        # reopen.
        standing = _standing(row, prior)
        if standing in ("PASSING", "PASSING_UNPINNED", "CHECK_CHANGED"):
            row.setdefault("regressions", []).append({
                "at": at, "run_id": run_id,
                "from_run": (check.get("adjudicated_by") or {}).get("run_id"),
                # Only a fall from PASSING is their fix regressing; the other
                # two passes prove no fix, so `reopen` reads this (review).
                "from_state": standing,
            })
    elif "inconclusive" in outcomes:
        new = "INCONCLUSIVE"
    else:
        if level != "V":
            # Rule 6: verification needs a clean tree and a tagged
            # preregistration. A pass without them is evidence, and is
            # recorded as such so the operator can see it -- but it verifies
            # nothing and moves no state.
            # Nor does it become what the row says it measured (RO02, deep
            # pass of 2026-09-24): a report composed on the REPRODUCING row
            # printed the passing reading while offering the failing run's
            # captures. Its reading rides with it here.
            check["last_exploratory_pass"] = {"run_id": run_id, "at": at,
                                              **({"detail": measured}
                                                 if measured else {})}
            return
        pinned = check.get("pinned_fingerprint")
        observed = _fingerprint_of(mine)
        if pinned is None:
            new = "PASSING_UNPINNED"
        elif observed == pinned:
            new = "PASSING"
        else:
            new = "CHECK_CHANGED"

    # This run adjudicated the row, so whatever it measured -- pass or fail --
    # is the row's current reading. Only failures used to refresh it, via
    # candidates(), so a row whose check started passing kept the numbers
    # from the day it broke and wore "figures not re-measured" forever.
    _measured_here()
    # `started_at` beside `at` (S01, deep pass of 2026-09-24): results carry
    # no time of their own, so only the run's start bounds when its checks
    # read the row -- which is what a correction owed after their word needs.
    check["adjudicated_by"] = {"run_id": run_id, "at": at,
                               "started_at": run.get("started_at")}
    # Only a run that adjudicated the row stops it being unverifiable for the
    # reason it was: popped any earlier, a partial run that never touched it
    # (RC06) or a pass that could not move it (S05, deep pass of 2026-09-24)
    # erased WHY while the state stayed.
    check.pop("unverifiable_reason", None)
    check.pop("missing_checks", None)
    if new != prior:
        check["state"] = new
        row["transitions"].append({
            "axis": "check", "from": prior, "to": new,
            "cause": {"run_id": run_id}, "at": at,
        })


# ---------------------------------------------------------------------------
# FILING axis
# ---------------------------------------------------------------------------
def _retired_checks(events: Iterable[dict]) -> dict[str, set[str]]:
    """Per row, the checks an operator event took away -- retired, or the
    old nodeid a rebind replaced -- so a run cannot add them back."""
    out: dict[str, set[str]] = {}
    for event in events:
        fid = str(event.get("finding_id") or "")
        if event.get("type") == "retire_check" and event.get("nodeid"):
            out.setdefault(fid, set()).add(str(event["nodeid"]))
        elif event.get("type") == "rebind_check":
            if event.get("value"):
                out.setdefault(fid, set()).add(str(event["value"]))
            # A rebind that brings a check back restores it (rule 10: a
            # subject that comes back is restored the same way) -- review.
            if event.get("nodeid"):
                out.setdefault(fid, set()).discard(str(event["nodeid"]))
    return out


def _apply_check_definition(rows: dict, events: Iterable[dict]) -> None:
    """Operator events that change WHICH checks adjudicate a row.

    Applied before the run, so a rebind takes effect in the same fold rather
    than a run later. These are the only way `checks` moves: five rows named
    scripts/*.py, which pytest never collects, so they sat outside the
    verification machinery while still displaying a state.
    """
    for event in events:
        row = rows.get(event.get("finding_id") or "")
        if row is None:
            continue
        etype = event.get("type")

        if etype == "rebind_check":
            checks = [c for c in (row.get("checks") or []) if c != event.get("value")]
            nodeid = event.get("nodeid")
            if nodeid and nodeid not in checks:
                checks.append(nodeid)
            row["checks"] = sorted(checks)

        elif etype == "retire_check":
            row["checks"] = sorted(
                c for c in (row.get("checks") or []) if c != event.get("nodeid"))

        elif etype == "pin_fingerprint":
            # Only a pin newer than the run that last adjudicated the row. The
            # journal is replayed whole on every fold, so a pin from before
            # that run -- which a failing run has since re-pinned -- came back
            # on every fold without a run and undid it (2026-09-22: 09-11's pin
            # over 09-21's, and a correction owed on #98 vanished).
            # As moments, not strings (architecture review, 2026-10-07): a pin in
            # another offset sorted after the run it preceded and undid its pin.
            check = row.setdefault("check", {})
            judged = _instant((check.get("adjudicated_by") or {}).get("at"))
            pinned_at = _instant(event.get("at"))
            if judged is not None and (pinned_at is None or pinned_at < judged):
                continue
            check["pinned_fingerprint"] = event.get("value")


def _mark_repins(rows: dict, events: Sequence[dict]) -> None:
    """Say which rows stand on a definition pinned by hand and never seen failing.

    Architecture review, 2026-10-07: `pin-fingerprint --from-run` can make a
    changed check's own passing run read VERIFIED FIXED -- legitimately when the
    change was a refactor, and with nothing on the record to tell the two apart.
    The state is unchanged; the row carries `check.repinned` (when, by whom, why)
    so the page can say "re-pinned" beside it, until a run sees that definition
    fail (`failed_under`), after which the pin is the failure's. `failed_under`
    is recorded from 2026-10-07 on, so an older row may be marked although a run
    once failed under the same value: the mark says "pinned by hand", never
    "never seen failing"."""
    latest: dict[tuple, dict] = {}
    for event in events:
        if event.get("type") == "pin_fingerprint":
            latest[(event.get("finding_id"), event.get("value"))] = event
    for fid, row in rows.items():
        check = row.get("check") or {}
        pinned = check.get("pinned_fingerprint")
        pin = latest.get((fid, pinned)) if pinned else None
        if pin is not None and pinned not in (check.get("failed_under") or []):
            check["repinned"] = {"at": pin.get("at"), "by": pin.get("by"),
                                 "reason": str(pin.get("reason") or "")[:300]}
        else:
            check.pop("repinned", None)


def _filing_targets(event: dict, rows: dict) -> list[str]:
    """Which finding ids this event speaks about."""
    if event.get("finding_id"):
        return [event["finding_id"]]
    if event.get("findings"):
        return list(event["findings"])
    report_id = event.get("report_id")
    if report_id is not None:
        return [fid for fid, row in rows.items()
                if any(r["report_id"] == report_id for r in row["filing"]["reports"])]
    return []


def _move_filing(row: dict, to: str, event: dict) -> None:
    filing = row["filing"]
    current = filing["state"]
    if current in _TERMINAL:
        return
    if to not in _TERMINAL and _FILING_RANK[to] <= _FILING_RANK.get(current, 0):
        return
    at = event["at"]
    filing["state"] = to
    filing["adjudicated_by"] = {"event_id": event_id(event), "at": at}
    row["transitions"].append({
        "axis": "filing", "from": current, "to": to,
        "cause": {"event_id": event_id(event)}, "at": at,
    })


def _claimed(report: dict, ever_claimed: set) -> bool:
    """Did they ever claim a fix on this report? The axis moves forward only,
    so a claim they later walked back (fixed, then in_progress: #67, #80 and
    #87) still earned the FIX_CLAIMED it moved the row to (S04)."""
    return (report.get("report_id") in ever_claimed
            or (report.get("status") or "").lower() in _FIX_CLAIMED_STATUSES)


def _live_end(rows: dict, fid: str) -> dict:
    """The row a supersede chain ends on: a claim carried onto a row that is
    itself superseded was owed to nobody (S03, deep pass of 2026-09-24)."""
    seen = {fid}
    row = rows[fid]
    while row["filing"]["state"] == "SUPERSEDED":
        onward = row.get("superseded_by")
        if onward not in rows or onward in seen:
            break
        seen.add(onward)
        row = rows[onward]
    return row


def _carry_reports(old: dict, new: dict, event: dict, ever_claimed: set) -> None:
    """The replacement holds what the superseded row filed (RC05, deep pass
    of 2026-09-24): the comment said it carried the debt and nothing did --
    the old row went terminal owing nothing, the new one held no report, and
    a fix claimed on a defect that still failed was owed to nobody. The old
    row keeps its reports too, so the ids still lead somewhere; a later word
    of theirs on one reaches both, and only the live row owes on it."""
    held = {r["report_id"] for r in new["filing"]["reports"]}
    carried = [dict(r) for r in old["filing"]["reports"] if r["report_id"] not in held]
    if not carried:
        return
    new["filing"]["reports"].extend(carried)
    ids = {r["report_id"] for r in carried}
    new["filing"]["verifications"].extend(
        dict(v) for v in old["filing"].get("verifications") or []
        if v.get("report_id") in ids)
    claimed = any(_claimed(r, ever_claimed) for r in new["filing"]["reports"])
    _move_filing(new, "FIX_CLAIMED" if claimed else "RAISED", event)


def _split_report(rows: dict, event: dict, ever_claimed: set,
                  replied: set) -> None:
    """Move one report off a row that holds two, onto a row of its own.

    2026-09-22: CYM-one_credential_carries_a_clone_from_creation_to_funding
    held #89 (fixed, paid) and #98 (still broken), and its one check fails on
    #98's route -- so the row owed a `fail` on #89 as well. A report is moved
    WITH its status and with what we already told them about it, at the
    event's own place in the replay, so everything before it stays as it was
    and the old row loses no transition.

    The one place an event brings a row into being, and only out of a row
    that holds the report: the new row inherits the old one's `first_seen`
    (the run that first saw the defect), is adjudicated by the check the
    event names, and starts UNVERIFIED with no pin. A split of a row that
    does not exist, or of a report it does not hold, moves nothing.
    """
    src = rows.get(event.get("finding_id") or "")
    new_id, report_id = event.get("to_id"), event.get("report_id")
    if src is None or not new_id or new_id == src.get("id"):
        return
    moving = [r for r in src["filing"]["reports"] if r["report_id"] == report_id]
    if not moving:
        return
    dst = rows.get(new_id)
    if dst is None:
        dst = rows[new_id] = {
            "id": new_id,
            "title": f"{src.get('title') or src.get('id')} -- #{report_id}",
            "first_seen": copy.deepcopy(src.get("first_seen")),
            "reproductions": 0,
            "checks": [event["nodeid"]] if event.get("nodeid") else [],
            "check": {"state": "UNVERIFIED", "adjudicated_by": None,
                      "pinned_fingerprint": None},
            "filing": {"state": "NOT_RAISED", "adjudicated_by": None,
                       "reports": [], "refused": [], "verifications": []},
            "transitions": [], "regressions": [],
        }
        for field in ("severity", "component", "section", "tag", "kind",
                      "provenance"):
            if field in src:
                dst[field] = copy.deepcopy(src[field])
    src["filing"]["reports"] = [r for r in src["filing"]["reports"]
                                if r["report_id"] != report_id]
    for report in moving:
        if not any(r["report_id"] == report_id for r in dst["filing"]["reports"]):
            dst["filing"]["reports"].append(dict(report))
    told = [v for v in src["filing"]["verifications"] if v["report_id"] == report_id]
    src["filing"]["verifications"] = [
        v for v in src["filing"]["verifications"] if v["report_id"] != report_id]
    dst["filing"]["verifications"].extend(told)
    _move_filing(dst, "FIX_CLAIMED" if _claimed(moving[0], ever_claimed)
                 else "RAISED", event)
    # The row that gave the report away keeps no FIX_CLAIMED that report
    # earned (RC08, deep pass of 2026-09-24): it displayed STILL REPRODUCIBLE
    # and owed a re-verify on a fix nobody claimed for what it still holds.
    # The one move back the axis makes, caused by the split event, appended.
    # Only if nothing it keeps EVER claimed one, and only as far back as what
    # was earned: their reply names the row, not the report (S04) -- read off
    # the reply itself, which after the claim left no transition (Q02).
    left = src["filing"]["reports"]
    if src["filing"]["state"] == "FIX_CLAIMED" and not any(
            _claimed(r, ever_claimed) for r in left):
        answered = src.get("id") in replied
        target = ("REPLIED" if answered else "RAISED") if left else "NOT_RAISED"
        src["filing"]["state"] = target
        src["filing"]["adjudicated_by"] = {"event_id": event_id(event),
                                           "at": event["at"]}
        src["transitions"].append({
            "axis": "filing", "from": "FIX_CLAIMED", "to": target,
            "cause": {"event_id": event_id(event)}, "at": event["at"]})
    src.setdefault("split_to", [])
    if new_id not in src["split_to"]:
        src["split_to"].append(new_id)
    dst["split_from"] = src.get("id")


def _apply_events(rows: dict, events: Iterable[dict]) -> None:
    """Replay the journal onto the FILING axis of every row.

    A full replay each time, so the axis cannot drift from the events and
    cannot be nudged in place -- the failure mode behind a ledger whose
    filing statuses were refreshed by mutating them where they sat.
    """
    for row in rows.values():
        row["filing"] = {"state": "NOT_RAISED", "adjudicated_by": None,
                         "reports": [], "refused": [], "verifications": []}
        row["transitions"] = [t for t in row.get("transitions", [])
                              if t.get("axis") != "filing"]
        row.pop("retracted_reports", None)
        # Rebuilt from the journal on every fold, like the axis itself.
        row.pop("superseded_by", None)
        row.pop("supersedes", None)
        row.pop("split_to", None)
        row.pop("split_from", None)

    retracted: dict[str, set[int]] = {}
    # Which door's read failed last and has not read cleanly since (A5).
    failing: dict[str, str] = {}
    # Every report they have ever claimed a fix on, so far in the replay (S04),
    # and every row they replied on -- a reply after the claim writes no
    # transition, the axis only moving forward (Q02).
    ever_claimed: set = set()
    replied: set = set()

    for event in events:
        etype = event.get("type")

        if etype == "split_report":
            _split_report(rows, event, ever_claimed, replied)
            continue

        if etype == "vendor_read":
            # Rule 8: a failed read is not an empty read. bounty.py could not
            # tell 401 from "the tracker is empty", so an expired key read as
            # the vendor having closed everything.
            #
            # A clean read afterwards clears it. Marking without clearing made
            # the first failed read in the journal's history mark every row
            # stale in every fold from then on -- a badge nobody can clear,
            # the same defect the reply-date logic in render.py was fixed for.
            # Only an explicit klass speaks: "ok" clears, a named failure
            # marks, and a read that recorded no class does neither, because
            # it is not evidence either way.
            #
            # Per door (A5 of the review of 2026-09-23, 3/3): a clean read
            # clears only the failure of the SAME source. The a2a inbox
            # answering is no evidence about the tracker, and it cleared the
            # tracker's failure in the same run. `stale_from` is the oldest
            # failure still standing.
            klass = event.get("klass")
            source = str(event.get("source") or "")
            if klass == "ok":
                failing.pop(source, None)
            elif klass is not None:
                # The OLDEST failure still standing: a new failure class on a
                # door that never read cleanly in between is the same outage
                # (RC07, deep pass of 2026-09-24).
                failing.setdefault(source, event["at"])
            else:
                continue
            since = min(failing.values()) if failing else None
            for row in rows.values():
                if since is None:
                    row["filing"].pop("stale_from", None)
                else:
                    row["filing"]["stale_from"] = since
            continue

        if etype == "supersede":
            # Handled before the target lookup: this event names its two rows
            # directly rather than through finding_id or a report.
            old_id, new_id = event.get("from_id"), event.get("to_id")
            was = rows[old_id]["filing"]["state"] if old_id in rows else None
            if old_id in rows:
                rows[old_id]["superseded_by"] = new_id
                _move_filing(rows[old_id], "SUPERSEDED", event)
            if new_id in rows:
                # Reports filed under the old id still lead here, so the
                # replacement carries the debt rather than starting clean.
                supersedes = rows[new_id].setdefault("supersedes", [])
                if old_id not in supersedes:
                    supersedes.append(old_id)
                # Only out of a row that was live (S03, deep pass of
                # 2026-09-24): a withdrawn row's reports are owed a
                # retraction, not a pass, and a row superseded before has
                # carried its own already. Onto where the chain is live.
                if old_id in rows and old_id != new_id and was not in _TERMINAL:
                    _carry_reports(rows[old_id], _live_end(rows, new_id), event,
                                   ever_claimed)
            continue

        targets = [fid for fid in _filing_targets(event, rows) if fid in rows]
        if not targets:
            continue

        if etype == "withdraw":
            for fid in targets:
                _move_filing(rows[fid], "WITHDRAWN", event)
            continue

        if etype == "retraction_sent":
            for fid in targets:
                retracted.setdefault(fid, set()).add(event.get("report_id"))
            continue

        # Everything below is the vendor conversation, and gap 2 applies: the
        # strongest thing the dashboard says rests on their words, so their
        # words must have been captured.
        if etype in ("filing_outcome", "vendor_status", "reply",
                     "verification_outcome"):
            if not event.get("evidence_id"):
                for fid in targets:
                    rows[fid]["filing"]["refused"].append(
                        f"{etype} at {event['at']} carries no evidence_id -- "
                        f"the response it reports was never captured"
                    )
                continue

        if etype == "filing_outcome":
            if event.get("outcome") != "accepted" or event.get("report_id") is None:
                continue
            for fid in targets:
                filing = rows[fid]["filing"]
                if not any(r["report_id"] == event["report_id"] for r in filing["reports"]):
                    filing["reports"].append(
                        {"report_id": event["report_id"], "status": "pending"})
                _move_filing(rows[fid], "RAISED", event)

        elif etype == "vendor_status":
            status = (event.get("status") or "").lower()
            if status in _FIX_CLAIMED_STATUSES:
                ever_claimed.add(event.get("report_id"))
            for fid in targets:
                for report in rows[fid]["filing"]["reports"]:
                    if report["report_id"] == event.get("report_id"):
                        if report.get("status") != event.get("status"):
                            # When their word last changed: a correction is
                            # owed only on a measurement after it (RO01).
                            report["status_at"] = event.get("at")
                        report["status"] = event.get("status")
                # _REPLIED_STATUSES is deliberately NOT consulted here. Reading
                # `invalid` as REPLIED is more accurate, and it is also
                # retroactive: this axis is rebuilt from the journal on every
                # fold, so changing how a status is read rewrites the history
                # of every row that ever carried it. Rows that recorded
                # RAISED -> FIX_CLAIMED would gain a REPLIED in between, and
                # write_ledger refuses a ledger whose transitions are not an
                # extension of the ones already written. That guard is right:
                # RAISED is what we believed at the time, and the transition
                # log says what we believed, not what we later learned.
                #
                # The value that mattered is delivered instead by the
                # `disputed` obligation, which reads the report's CURRENT
                # status and touches no transition.
                to = "FIX_CLAIMED" if status in _FIX_CLAIMED_STATUSES else "RAISED"
                _move_filing(rows[fid], to, event)

        elif etype == "reply":
            for fid in targets:
                replied.add(fid)
                _move_filing(rows[fid], "REPLIED", event)

        elif etype == "verification_outcome":
            # Outbound, so it moves NEITHER axis. CHECK has one mover, an
            # admissible run; FILING has one mover, something the vendor did.
            # This is us telling them what our run already decided, and the
            # only honest effect is a record that we said it.
            #
            # Reusing filing_outcome would have been the cheap route and would
            # have fabricated filings: the branch above moves any accepted
            # outcome with a report_id to RAISED and attaches the report,
            # with no notion of which endpoint it went to.
            if event.get("outcome") != "accepted":
                continue
            for fid in targets:
                sent = rows[fid]["filing"]["verifications"]
                mark = {"report_id": event.get("report_id"),
                        "fingerprint": event.get("fingerprint"),
                        "run_id": event.get("run_id"),
                        "verdict": event.get("verdict"),
                        "at": event["at"]}
                # The VERDICT is part of what makes two marks the same, and it
                # was missing here while _told() below already required it.
                # A `fail` correcting a `pass` at the SAME fingerprint -- the
                # vendor regresses, our check's code unchanged, _apply_run
                # re-pins what it failed under -- collided with the pass and
                # was dropped, so correction_owed could never clear and every
                # later run re-sent a correction their server already held.
                # Found by all three triage agents on 2026-09-07; the test
                # above it had exercised only the repaired-check case, where
                # the two carry different fingerprints.
                #
                # Re-sending the same verdict under the same definition keeps
                # ONE mark, whose `at` moves to the newer send. Dropping the
                # newer one outright was safe while `_told` asked whether a
                # verdict had ever gone; it stopped being safe when `_told`
                # started reading the newest mark, because pass -> fail ->
                # pass then left `fail` as the newest thing on record and the
                # row went on owing a pass it had just sent.
                #
                # What this projection therefore cannot answer is how MANY
                # times a verdict went out; the journal holds every send and
                # is where that question belongs.
                same = next((v for v in sent
                             if v["report_id"] == mark["report_id"]
                             and v["fingerprint"] == mark["fingerprint"]
                             and v.get("verdict") == mark["verdict"]), None)
                if same is None:
                    sent.append(mark)
                elif str(mark.get("at") or "") > str(same.get("at") or ""):
                    same.update(mark)

    for fid, row in rows.items():
        row["_retracted"] = sorted(r for r in retracted.get(fid, set()) if r is not None)


# ---------------------------------------------------------------------------
# Obligations -- what each row still owes somebody
# ---------------------------------------------------------------------------
def correction_reason(report: dict, verified: list) -> str | None:
    """WHY this report is owed a correction, or None if it is owed none.

    The obligation and the sentence we send have to come from one reading.
    `verify.py` had two headlines for three cases and said, on every one of
    them, "either a fix was claimed and our re-check does not agree, or we
    sent you a pass we can no longer stand behind". Neither half is true of a
    report they ACCEPTED AND PAID without ever claiming a fix -- #89 and #98
    are both `paid`, both still failing -- and a sentence we cannot stand
    behind is one that does not get sent, which is how those two came to sit
    with the vendor under nothing at all.

    `paid` is in _FIX_CLAIMED_STATUSES because paying is engaging with the
    report; it is not a claim that the defect is gone, and this is where the
    difference is finally written down.

      fix_claimed  they said fixed, and our check does not agree
      our_pass     we sent a pass for this report that we can no longer stand
                   behind
      accepted     they accepted and paid it and said nothing about a fix; our
                   check still fails under the definition now pinned

    `our_pass` wins over `fix_claimed` when both hold: a pass of OURS being
    withdrawn is the more serious of the two, and it is the one they cannot
    work out for themselves.
    """
    report_id = report.get("report_id")
    if any(v.get("report_id") == report_id and v.get("verdict") == "pass"
           for v in verified):
        return "our_pass"
    status = (report.get("status") or "").lower()
    if status == "fixed":
        return "fix_claimed"
    if status in _FIX_CLAIMED_STATUSES:
        return "accepted"
    return None


def _measured_since(row: dict, report: dict, verified: list) -> bool:
    """Whether the failure that adjudicated this row was measured AFTER the
    word a correction answers: their status (a claimed fix, a payment), or
    the pass of ours it withdraws.

    RO01 of the deep pass of 2026-09-24 (3/3). The correction says our check
    STILL fails; a failure measured before they paid says nothing about what
    they did after. On 2026-09-23 #117, #119, #122 and #123 were owed one on a
    run that finished at 00:26 -- #123 filed at 00:27, #122 and #123 paid at
    06:48 -- and verify.py would have told them it was "our own re-reading".
    Until a run reads the row after their word, the re-verify (rule 7) is
    what is owed. A row that cannot say when it was measured owes nothing:
    a sentence we cannot date is one we cannot stand behind.

    Dated by the run's START (S01, deep pass of 2026-09-24, 3/3): a run that
    finished after their word may have read the row before it, and results
    carry no time of their own.
    """
    measured = str(((row.get("check") or {}).get("adjudicated_by") or {})
                   .get("started_at") or "")
    if correction_reason(report, verified) == "our_pass":
        said = [str(v.get("at") or "") for v in verified
                if v.get("report_id") == report.get("report_id")
                and v.get("verdict") == "pass"]
        since = max(said) if said else ""
    else:
        since = str(report.get("status_at") or "")
    return bool(measured) and bool(since) and measured > since


def _instant(value) -> datetime | None:
    """An ISO timestamp as a moment. Compared as strings, a run's finished_at
    with fractions ('...12.481+00:00') sorts AFTER a mark written in the same
    second ('...12+00:00'), because '+' comes before '.'."""
    try:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def _last_fall(row: dict) -> datetime | None:
    """When the row last fell from PASSING -- the only fall that is their fix
    regressing (the other two standings prove no fix) -- or None."""
    falls = [m for r in row.get("regressions") or []
             if r.get("from_state", "PASSING") == "PASSING"
             and (m := _instant(r.get("at"))) is not None]
    return max(falls) if falls else None


def _told_since(verified: list, report_id, since: datetime, verdict: str) -> bool:
    """Did this verdict go to them about this report at or after `since`?

    Any definition, unlike `_told`: what `reopen` owes is the news that it
    broke again, and a fail sent after the fall is that news whichever
    fingerprint it carried -- a check repaired after the fall included."""
    for v in verified:
        sent = _instant(v.get("at"))
        if (v["report_id"] == report_id and v.get("verdict") == verdict
                and sent is not None and sent >= since.replace(microsecond=0)):
            return True
    return False


def _told(verified: list, report_id, fingerprint, verdict: str) -> bool:
    """Is this verdict the LAST thing they heard, for this check definition?

    Keyed on the FINGERPRINT and never on the run: every sweep re-adjudicates
    every row, so a run-keyed debt would come due after each one and send the
    same verifications daily -- a badge that clears itself into spam.

    Newest mark wins, and that is not a detail. This asked whether the verdict
    had EVER been sent, so a pass followed by a fail under one definition left
    the row owing nothing in either direction: the pass was "already told" and
    their server kept our fail as the last word. #85 sat that way from
    2026-09-10 -- a pass at 20:08, a fail at 21:46, our check passing under
    the same pinned definition ever since, and `verification_owed` empty.
    What a debt has to compare is the newest thing we said, because that is
    what a reader of their tracker sees.
    """
    marks = [(i, v) for i, v in enumerate(verified)
             if v["report_id"] == report_id and v["fingerprint"] == fingerprint]
    if not marks:
        return False
    # (at, position) and not `at` alone. Their timestamps are truncated to the
    # second, so a pass and the correction that follows it can share one --
    # and `max` returns the FIRST maximal element, which is the older mark in
    # journal order. That would have read the pass as their last word while
    # the fail sat on their server, the exact inversion this function was
    # being repaired for. Journal order breaks the tie, the way
    # qa/channels.py treats two events recorded in one breath.
    _, newest = max(marks, key=lambda pair: (str(pair[1].get("at") or ""), pair[0]))
    return newest.get("verdict") == verdict


def _obligations(row: dict) -> dict:
    check, filing = row["check"]["state"], row["filing"]["state"]
    filed = [r["report_id"] for r in row["filing"]["reports"]]
    retracted = set(row.pop("_retracted", []))
    pinned = row["check"].get("pinned_fingerprint")
    verified = row["filing"].get("verifications") or []

    return {
        # Rule 7: their claim of a fix is a claim. It opens work, never closes it.
        "reverify": filing == "FIX_CLAIMED" and check != "PASSING",
        # Gap 3: a filed row whose check measures nothing is a broken check
        # wearing a resolved defect's clothes.
        "repair_check": (check in ("INCONCLUSIVE", "UNVERIFIABLE")
                         and filing in ("RAISED", "REPLIED", "FIX_CLAIMED")),
        # Gap 4: regressing after they closed the report is something we owe
        # them a message about, not just a red badge.
        # The message is a `fail` sent after the fall; once it has gone the
        # debt is paid. It never cleared until 2026-09-25, so #52, #86 and #98
        # read "reopen" for days after their fails went out.
        "reopen": ([r for r in filed if not _told_since(verified, r, fell, "fail")]
                   if (fell := _last_fall(row)) is not None
                   and check == "REPRODUCING"
                   and filing == "FIX_CLAIMED" else []),
        # Rule 11: withdrawing a filed finding leaves a correction owed.
        "retractions": ([r for r in filed if r not in retracted]
                        if filing == "WITHDRAWN" else []),
        # We hold evidence they asked for and have not sent it. Keyed on the
        # FINGERPRINT, never on the run: every sweep re-adjudicates every
        # passing row, so a run-keyed debt would come due again after each one
        # and send them the same verifications daily. On the fingerprint it is
        # a statement about the CHECK -- we have told them this definition
        # passes -- so it comes due once, clears when sent, and speaks again
        # only when the definition moves, which is the one case that is new
        # information. PASSING_UNPINNED is excluded on purpose: passing under
        # a definition we never saw fail proves no fix.
        # Not on a terminal row (B3 of the review of 2026-09-23, 3/3): a
        # finding we withdrew owes a retraction, and a pass on it would tell
        # them their fix works on a defect we said was not one.
        "verification_owed": ([r for r in filed
                               if not _told(verified, r, pinned, "pass")]
                              if check == "PASSING" and pinned
                              and filing not in _TERMINAL else []),
        # The other direction, and the one that exists because we can be
        # wrong. A pass we sent stops being true the moment the check is
        # repaired -- and with a pass-only rule it would stop being OWED at
        # the same moment, because verification_owed speaks only for passing
        # rows. That is a debt that vanishes when you discover it. It cost us
        # a false claim on their server on 2026-09-07 (#67).
        #
        # Due when either of us said it was fixed: they claimed one, or we
        # sent a pass under any definition. NOT on a row that is merely filed
        # and failing -- we said that when we filed it, and repeating it down
        # a second channel is noise rather than news.
        # Read per REPORT, not per row. `filing` is the row's state, which is
        # the maximum over its reports, and this then charged the debt to
        # every id on the row: a row where they claimed a fix on one report
        # and we filed a second last night, still failing, owed "this
        # corrects the record" on the second -- about a report whose record
        # already says exactly that. `disputed` below has always read each
        # report's own status; this is the same reading one obligation up.
        # `filing not in _TERMINAL` is not decoration. The row-level read
        # excluded a withdrawn row by accident, because WITHDRAWN is not
        # FIX_CLAIMED; reading each report's own status brought it back, and
        # the recomposed ledger promptly asked us to "correct the record" on
        # #53 -- a finding we had already taken back, whose report is `paid`.
        # What a withdrawn row owes is the retraction above.
        "correction_owed": ([r["report_id"] for r in row["filing"]["reports"]
                             if not _told(verified, r["report_id"], pinned, "fail")
                             and correction_reason(r, verified) is not None
                             and _measured_since(row, r, verified)]
                            if check == "REPRODUCING" and pinned
                            and filing not in _TERMINAL else []),
        # They read the report and said no, and our check still fails. One of
        # the two has to give -- we withdraw because they are right, or we
        # answer because we are -- and neither happens on its own. Nothing is
        # owed once our own check agrees with them, and nothing is owed on a
        # terminal row: withdrawing IS giving them the point, and asking a
        # WITHDRAWN row to settle the dispute again is a badge that can never
        # be cleared. What that row owes is a retraction, below.
        "disputed": ([r["report_id"] for r in row["filing"]["reports"]
                      if (r.get("status") or "").lower() in _REJECTED_STATUSES]
                     if check != "PASSING" and filing not in _TERMINAL else []),
    }


# ---------------------------------------------------------------------------
# The fold
# ---------------------------------------------------------------------------
def fold(prev: dict | None = None, run: dict | None = None,
         candidates: Sequence[dict] = (), events: Sequence[dict] = ()) -> dict:
    """Compose one run and the whole journal onto the previous ledger."""
    rows: dict[str, Any] = copy.deepcopy((prev or {}).get("findings", {}) or {})
    for row in rows.values():
        row.setdefault("transitions", [])
        row.setdefault("regressions", [])
        row.setdefault("check", {"state": "UNVERIFIED", "adjudicated_by": None,
                                 "pinned_fingerprint": None})
        row.setdefault("filing", {"state": "NOT_RAISED", "adjudicated_by": None,
                                  "reports": [], "refused": [], "verifications": []})

    out: dict[str, Any] = {"schema": 2, "findings": rows}

    # Which checks adjudicate a row is settled before the run is read, so a
    # rebind takes effect in the same fold that records it.
    _apply_check_definition(rows, events)

    level = "none"
    if run is not None:
        verdict = admissibility(run)
        level = verdict.level
        if level == "none":
            # Not evidence. Naming the reasons is the whole point: all 13
            # committed run records land here, and the operator needs to know
            # it is the record that is inadmissible, not the platform that is
            # fine.
            out["rejected_run"] = {"run_id": run["run_id"], "reasons": verdict.reasons}
            run = None

    if run is not None:
        at = run.get("finished_at") or run.get("started_at")
        retired = _retired_checks(events)
        for cand in candidates:
            row = rows.get(cand["id"])
            if row is None:
                row = rows[cand["id"]] = {
                    "id": cand["id"],
                    "first_seen": {"at": at, "cause": {"run_id": run["run_id"]}},
                    "reproductions": 0,
                    "check": {"state": "UNVERIFIED", "adjudicated_by": None,
                              "pinned_fingerprint": None},
                    "filing": {"state": "NOT_RAISED", "adjudicated_by": None,
                               "reports": [], "refused": [], "verifications": []},
                    "transitions": [], "regressions": [],
                }
            # A default applies only at creation. Refreshing a row with one
            # lets a run restate a judgement it never made, which is how
            # CYM-anon-tool-surface was silently downgraded from S0-CUSTODY to
            # S3-CONTRACT on the first admissible run: no claims.yaml entry
            # matched, so the candidate carried a default severity.
            row.setdefault("severity", cand.get("default_severity", "S3-CONTRACT"))
            row.setdefault("title", cand.get("default_title", cand["id"]))
            # Count RUNS in which it reproduced, not folds. Composing the same
            # run twice must produce the same ledger, or the repo-consistency
            # check reports drift every time it re-folds to compare -- and a
            # counter that grows when nothing happened is the same species as
            # the timestamp that used to drive REGRESSED.
            seen_in = row.setdefault("reproduced_in", [])
            if run["run_id"] not in seen_in:
                seen_in.append(run["run_id"])
                row["reproductions"] = row.get("reproductions", 0) + 1
            for field in ("title", "severity", "component", "section", "tag",
                          "kind", "detail", "note"):
                if field in cand:
                    row[field] = cand[field]
            # A run may ADD a check to a row, never take one away (A3 of the
            # review of 2026-09-23, 3/3): the candidate names only the checks
            # that failed in this run, and copying it over the row dropped the
            # rest, so a later pass on the survivors verified checks nobody
            # read. Rebind and retire events move `checks` (above), and a
            # check they took away does not come back through a run.
            if "checks" in cand:
                gone = retired.get(cand["id"], set())
                row["checks"] = sorted((set(row.get("checks") or [])
                                        | set(cand["checks"])) - gone)
            row["provenance"] = {"run_id": run["run_id"], "measured_at": at}

        for row in rows.values():
            _apply_run(row, run, level)
        out["run_id"] = run["run_id"]
        out["run_level"] = level
        out["updated_at"] = at
    else:
        _structural_pass(rows.values(), events)

        # This fold adjudicated nothing. That does not un-adjudicate what came
        # before, and dropping the attribution said it did: an --events-only
        # fold over a single appended event rewrote a page that read "level V"
        # into one reading "none admissible", while every row still named the
        # run that last judged it. The rows were right and the header was
        # wrong. Carry it, and let the caller say who composed what.
        for field in ("run_id", "run_level", "updated_at"):
            carried = (prev or {}).get(field)
            if carried is not None:
                out[field] = carried
        out["run_carried"] = "run_id" in out

    _mark_repins(rows, events)
    before_events = set(rows)
    _apply_events(rows, events)
    if run is not None:
        # A row the journal brought into being (a split) is read by the run
        # folded with it, as it is by every refold of the same inputs: made
        # after the run had walked the rows, it came out UNVERIFIED once and
        # REPRODUCING on rule 12's refold (RC03, deep pass of 2026-09-24).
        for fid in set(rows) - before_events:
            _apply_run(rows[fid], run, level)
    else:
        # And without a run, by the structural pass, which had already walked
        # the rows too: a split onto a check that is no nodeid came out
        # UNVERIFIED once and UNVERIFIABLE on the next fold, with no
        # transition (X03, deep pass of 2026-10-25).
        _structural_pass([rows[fid] for fid in sorted(set(rows) - before_events)], events)
    for row in rows.values():
        # Chronological, and deterministically so. The FILING half is rebuilt
        # from the journal on every fold while the CHECK half accumulates, so
        # without this the two interleave by construction order and the
        # ledger's monotonic guard sees a history that is not an extension of
        # itself -- correctly refusing a write that was in fact forward-only.
        row["transitions"].sort(
            key=lambda t: (t["at"], t["axis"], str(t.get("from")), t["to"],
                           json.dumps(t.get("cause") or {}, sort_keys=True)))
        row["obligations"] = _obligations(row)

    out["counts"] = {}
    for row in rows.values():
        state = display_state(row)
        out["counts"][state] = out["counts"].get(state, 0) + 1
    return out
