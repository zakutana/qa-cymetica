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
from typing import Any, Iterable, Sequence

from qa.state import admissibility, event_id

CHECK_STATES = ("UNVERIFIED", "REPRODUCING", "PASSING", "PASSING_UNPINNED",
                "CHECK_CHANGED", "INCONCLUSIVE", "UNVERIFIABLE")

FILING_STATES = ("NOT_RAISED", "RAISED", "REPLIED", "FIX_CLAIMED", "WITHDRAWN")

# How far along the vendor conversation a filing state is. The axis moves
# forward only -- a later `pending` does not undo an earlier `fixed`, because
# a tracker that forgets is not evidence that they changed their mind.
_FILING_RANK = {"NOT_RAISED": 0, "RAISED": 1, "REPLIED": 2, "FIX_CLAIMED": 3}

_FIX_CLAIMED_STATUSES = frozenset({"fixed", "resolved", "completed", "closed"})


def _display_cell(check: str, filing: str) -> str:
    if filing == "WITHDRAWN":
        # Ours and terminal. Whatever the check now says about a finding we
        # retracted, the retraction is the fact of record.
        return "WITHDRAWN"
    if check == "UNVERIFIABLE":
        return "UNVERIFIABLE"
    if check == "PASSING":
        return {
            "NOT_RAISED": "PASSING, NEVER RAISED",
            "RAISED": "PASSING, UNCLAIMED",
            "REPLIED": "PASSING, UNCLAIMED",
            "FIX_CLAIMED": "VERIFIED FIXED",
        }[filing]
    if check == "PASSING_UNPINNED":
        return "PASSING (UNPINNED)"
    if check == "CHECK_CHANGED":
        return "CHECK CHANGED"
    if check == "INCONCLUSIVE":
        # Their claim plus a check that measures nothing is not a fix. It is
        # the one case where we genuinely do not know, and it says so.
        return "NOT REPRODUCIBLE" if filing == "FIX_CLAIMED" else "INCONCLUSIVE"
    if check == "REPRODUCING":
        return {
            "NOT_RAISED": "NOT RAISED YET",
            "RAISED": "RAISED",
            "REPLIED": "THEY REPLIED",
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

    # Rule 2. A check that did not run tells us nothing. This is the branch
    # merge() reached only after its sticky-verified latch had already
    # returned, which is how partial runs closed rows they never touched.
    if any(r is None or r.get("outcome") in ("skipped", "error") for r in mine):
        check["not_checked_in"] = run_id
        return
    check.pop("not_checked_in", None)

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
    if current == "WITHDRAWN":
        return
    if to != "WITHDRAWN" and _FILING_RANK[to] <= _FILING_RANK.get(current, 0):
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
                         "reports": [], "refused": []}
        row["transitions"] = [t for t in row.get("transitions", [])
                              if t.get("axis") != "filing"]
        row.pop("retracted_reports", None)

    retracted: dict[str, set[int]] = {}

    for event in events:
        etype = event.get("type")

        if etype == "vendor_read" and event.get("klass") not in (None, "ok"):
            # Rule 8: a failed read is not an empty read. bounty.py could not
            # tell 401 from "the tracker is empty", so an expired key read as
            # the vendor having closed everything.
            for row in rows.values():
                row["filing"]["stale_from"] = event["at"]
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
        if etype in ("filing_outcome", "vendor_status", "reply"):
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
                to = "FIX_CLAIMED" if status in _FIX_CLAIMED_STATUSES else "RAISED"
                _move_filing(rows[fid], to, event)

        elif etype == "reply":
            for fid in targets:
                _move_filing(rows[fid], "REPLIED", event)

    for fid, row in rows.items():
        row["_retracted"] = sorted(r for r in retracted.get(fid, set()) if r is not None)


# ---------------------------------------------------------------------------
# Obligations -- what each row still owes somebody
# ---------------------------------------------------------------------------
def _obligations(row: dict) -> dict:
    check, filing = row["check"]["state"], row["filing"]["state"]
    filed = [r["report_id"] for r in row["filing"]["reports"]]
    retracted = set(row.pop("_retracted", []))

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
                                  "reports": [], "refused": []})

    out: dict[str, Any] = {"schema": 2, "findings": rows}

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
                               "reports": [], "refused": []},
                    "transitions": [], "regressions": [],
                }
            row["reproductions"] = row.get("reproductions", 0) + 1
            for field in ("title", "severity", "component", "section", "tag",
                          "kind", "checks", "detail"):
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

    _apply_events(rows, events)
    for row in rows.values():
        row["obligations"] = _obligations(row)

    out["counts"] = {}
    for row in rows.values():
        state = display_state(row)
        out["counts"][state] = out["counts"].get(state, 0) + 1
    return out
