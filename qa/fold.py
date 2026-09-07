"""The fold: ledger = f(previous rows, one run record, the whole journal).

This module replaces `merge()` in scripts/ledger.py, which the audit found
responsible for most of the 71 self-inflicted state changes an operator
watched. The difference is not that the rules are stricter; it is that there
are rules at all, and that nothing here can write a state without also writing
what caused it.

Two axes, never overwriting each other:

    CHECK    moved only by an admissible run record that adjudicated every
             check the row declares
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


def _apply_run(row: dict, run: dict, level: str) -> None:
    """Move the CHECK axis of one row according to one admissible run."""
    check = row["check"]
    checks = row.get("checks") or []

    reason = _structural_reason(checks)
    if reason:
        check["state"] = "UNVERIFIABLE"
        check["unverifiable_reason"] = reason
        return
    check.pop("unverifiable_reason", None)

    at = run.get("finished_at") or run.get("started_at")
    run_id = run["run_id"]
    results = {r["nodeid"]: r for r in run.get("results", [])}
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
            check["state"] = "UNVERIFIABLE"
            check["unverifiable_reason"] = "check_missing"
            check["missing_checks"] = sorted(missing)
            return
    check.pop("missing_checks", None)

    # Rule 2. A check that did not run tells us nothing. This is the branch
    # merge() reached only after its sticky-verified latch had already
    # returned, which is how partial runs closed rows they never touched.
    if any(r is None or r.get("outcome") in ("skipped", "error") for r in mine):
        check["not_checked_in"] = run_id
        return
    check.pop("not_checked_in", None)

    # This run looked at every check the row declares, so whatever it measured
    # is now the row's current reading -- pass or fail. Only failures used to
    # refresh it, via candidates(), so a row whose check started passing kept
    # the numbers from the day it broke and wore "figures not re-measured"
    # forever. Measuring is measuring; proposing a defect is the separate act.
    measured = _measurement_detail(mine)
    if measured:
        row["detail"] = measured
    row["provenance"] = {"run_id": run_id, "measured_at": at}

    # An evidence-role measurement can never fail -- conclude() returns rather
    # than raising, because comparing one sentence against another says
    # nothing about behaviour. So its "pass" is not evidence of anything and
    # must not establish PASSING: that is a check which passes because of how
    # it asks, which is the whole class this plan exists to stop. It measures
    # (above) and adjudicates nothing.
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
        if prior == "PASSING":
            row.setdefault("regressions", []).append({
                "at": at, "run_id": run_id,
                "from_run": (check.get("adjudicated_by") or {}).get("run_id"),
            })
    elif "inconclusive" in outcomes:
        new = "INCONCLUSIVE"
    else:
        if level != "V":
            # Rule 6: verification needs a clean tree and a tagged
            # preregistration. A pass without them is evidence, and is
            # recorded as such so the operator can see it -- but it verifies
            # nothing and moves no state.
            check["last_exploratory_pass"] = {"run_id": run_id, "at": at}
            return
        pinned = check.get("pinned_fingerprint")
        observed = _fingerprint_of(mine)
        if pinned is None:
            new = "PASSING_UNPINNED"
        elif observed == pinned:
            new = "PASSING"
        else:
            new = "CHECK_CHANGED"

    check["adjudicated_by"] = {"run_id": run_id, "at": at}
    if new != prior:
        check["state"] = new
        row["transitions"].append({
            "axis": "check", "from": prior, "to": new,
            "cause": {"run_id": run_id}, "at": at,
        })


# ---------------------------------------------------------------------------
# FILING axis
# ---------------------------------------------------------------------------
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
            row.setdefault("check", {})["pinned_fingerprint"] = event.get("value")


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

    retracted: dict[str, set[int]] = {}

    for event in events:
        etype = event.get("type")

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
            klass = event.get("klass")
            if klass == "ok":
                for row in rows.values():
                    row["filing"].pop("stale_from", None)
            elif klass is not None:
                for row in rows.values():
                    row["filing"]["stale_from"] = event["at"]
            continue

        if etype == "supersede":
            # Handled before the target lookup: this event names its two rows
            # directly rather than through finding_id or a report.
            old_id, new_id = event.get("from_id"), event.get("to_id")
            if old_id in rows:
                rows[old_id]["superseded_by"] = new_id
                _move_filing(rows[old_id], "SUPERSEDED", event)
            if new_id in rows:
                # Reports filed under the old id still lead here, so the
                # replacement carries the debt rather than starting clean.
                supersedes = rows[new_id].setdefault("supersedes", [])
                if old_id not in supersedes:
                    supersedes.append(old_id)
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
            for fid in targets:
                for report in rows[fid]["filing"]["reports"]:
                    if report["report_id"] == event.get("report_id"):
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
                if not any(v["report_id"] == mark["report_id"]
                           and v["fingerprint"] == mark["fingerprint"]
                           for v in sent):
                    sent.append(mark)

    for fid, row in rows.items():
        row["_retracted"] = sorted(r for r in retracted.get(fid, set()) if r is not None)


# ---------------------------------------------------------------------------
# Obligations -- what each row still owes somebody
# ---------------------------------------------------------------------------
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
        "reopen": (filed if row.get("regressions") and check == "REPRODUCING"
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
        "verification_owed": ([r for r in filed
                               if not any(v["report_id"] == r
                                          and v["fingerprint"] == pinned
                                          for v in verified)]
                              if check == "PASSING" and pinned else []),
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
                          "kind", "checks", "detail", "note"):
                if field in cand:
                    row[field] = cand[field]
            row["provenance"] = {"run_id": run["run_id"], "measured_at": at}

        for row in rows.values():
            _apply_run(row, run, level)
        out["run_id"] = run["run_id"]
        out["run_level"] = level
        out["updated_at"] = at
    else:
        for row in rows.values():
            reason = _structural_reason(row.get("checks") or [])
            if reason:
                row["check"]["state"] = "UNVERIFIABLE"
                row["check"]["unverifiable_reason"] = reason

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

    _apply_events(rows, events)
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
