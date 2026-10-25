"""Tell them a check of ours passes under the fingerprint it last failed under.

The second write this project performs on purpose, and the first that is not a
report. Cymetica published POST /api/v1/bounty/reports/{id}/verification on
2026-09-07 and asked for the evidence we were holding; until then a fix we had
verified was a fact that existed only on our own dashboard.

What it sends is deliberately small. Not "the bug is fixed" -- that is their
claim to make -- but: this check, under this definition, passed in this
preregistered run against this tree, at this time.

It used to close by telling them to reproduce it from github.com/zakutana/
qa-cymetica. That repository is PRIVATE and they are not on it, so the line
inviting them to check us for themselves pointed at a door that does not open.
What goes now is what we can stand behind: the request and the response are
kept, under an id, and we send them if asked.

    python scripts/verify.py --dry-run     compose, send nothing
    python scripts/verify.py --confirm     send, up to MAX_PER_RUN
    python scripts/verify.py --only CYM-x  one finding

It sends both verdicts, and the second one is why this is not a one-off
script. `pass` says a check of ours passes under the fingerprint it last
failed under. `fail` corrects the record: either they claimed a fix our
re-check does not agree with, or WE sent a pass we can no longer stand behind.
The second case is not hypothetical -- it happened within hours of the first
batch, when CYM-a2a-first-pass-contract turned out to assert that a field was
present while the contract it named was about that field's value.

WHAT IT SENDS IS NOT A LIST IT KEEPS. The selection is the `verification_owed`
and `correction_owed` obligations in qa/fold.py, both keyed on the check's
fingerprint: a row owes a verdict we have never told them about for the
definition it currently stands on. So re-running after a partial batch resumes
exactly where it stopped, running it when nothing is owed sends nothing, and a
pass that stops being true becomes a correction that is owed rather than a
mistake that quietly disappears. There is no cursor to corrupt and no list to
get out of date.

Modelled on scripts/submit.py, which is the other outbound writer, and
deliberately unlike it in four places where its behaviour was found wanting
while planning this one:

  * a failed evidence capture stops the batch here rather than becoming a
    silent None, but the outcome event is written FIRST. submit.py returns
    None and the fold then refuses the outcome it produced -- a request that
    went out and cannot be folded. The first version of this file was worse:
    it raised between the POST and the event, so the attempt left no outcome
    at all and the obligation could never clear. Three triage agents found
    that on 2026-09-07; settle() is the exit.
  * the rate-limit break says what did not go, per item, instead of dropping
    the remainder with no event and no line of output.
  * the per-run cap is applied after deduplication, not before, so requests we
    were never going to make do not consume it.
  * a response's status is read before its body (rule 8).
"""

from __future__ import annotations

import argparse
import json
import sys
import time

import httpx
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa.client import build_client, install_client_guard  # noqa: E402
from qa.config import identities, load_dotenv  # noqa: E402
from qa.fold import _fingerprint_of, _instant, results_by_nodeid  # noqa: E402
from qa.fold import correction_reason as fold_correction_reason  # noqa: E402
from qa.report_plugin import HELPERS_FORMULA  # noqa: E402
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier  # noqa: E402
from qa.state import (admissibility, append_event, journal_path,  # noqa: E402
                      load_ledger, load_run, read_events)

# Their cap is unresolved -- they said 20/hour, the header advertises 60 -- so
# submit.py takes the stricter and this follows it. 27 verifications is three
# runs, and re-running is free because the obligation is the selection.
MAX_PER_RUN = 12
PAUSE_SECONDS = 4


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _path(report_id: int) -> str:
    return f"/api/v1/bounty/reports/{report_id}/verification"


def _capture(response, tier: SafetyTier = SafetyTier.MUTATE) -> str:
    """The evidence id, or raise.

    submit.py swallows a capture failure into None, and qa/fold.py then refuses
    the outcome for having no evidence_id -- so the request went out, the
    journal recorded it, and the ledger cannot use it. Here the capture is part
    of the transaction: if their answer cannot be preserved, we do not get to
    keep the claim that they answered.
    """
    from qa.evidence import EvidenceStore

    try:
        evidence_id = EvidenceStore("script-verify").capture(
            response.request, response, tier)
    except Exception as exc:  # noqa: BLE001
        evidence_id, why = None, f"{type(exc).__name__}: {exc}"
    else:
        why = "the store returned no id"
    if not evidence_id:
        raise SystemExit(
            f"the response to {response.request.method} {response.request.url} "
            f"was not captured ({why}), so nothing can stand on it. Nothing "
            f"further will be sent; the journal already records the intent."
        )
    return evidence_id


def owed(ledger: dict, only: list[str] | None) -> list[dict]:
    """Every (finding, report) pair that owes a verification, with its evidence.

    Reads the obligation rather than re-deriving who is owed one. The rule
    lives in qa/fold.py where it is tested; a second copy here would be a
    second rule.
    """
    work: list[dict] = []
    for fid, row in sorted(ledger["findings"].items()):
        if only and fid not in only:
            continue
        obligations = row.get("obligations") or {}
        corrections = list(obligations.get("correction_owed") or [])
        # `reopen` -- the row passed after their fix and now fails again -- was
        # sent by nothing until 2026-10-07, so a recurrence became a NEW report
        # (six duplicate groups, all paid). A fail on the ORIGINAL report is what
        # reopens their ticket ([operator 2026-10-07] "mas otevrit stary bug").
        reopened = [r for r in obligations.get("reopen") or [] if r not in corrections]
        due = ([(r, "pass") for r in obligations.get("verification_owed") or []]
               + [(r, "fail") for r in corrections]
               + [(r, "fail") for r in reopened])
        if not due:
            continue
        reports = [r for r, _ in due]

        provenance = row.get("provenance") or {}
        if not provenance.get("measured_at"):
            raise SystemExit(
                f"{fid} owes a verification but carries no provenance."
                f"measured_at, so the figures behind it were never measured by "
                f"an admissible run. Run the checks first."
            )
        adjudicated = (row["check"].get("adjudicated_by") or {})
        run_id = adjudicated.get("run_id")
        if not run_id:
            raise SystemExit(f"{fid} is PASSING with no run that adjudicated it")
        run = load_run(run_id)

        # A FAIL says our check still fails. Not when our own newer reading
        # says otherwise (O01, deep pass of 2026-10-25): held, said, and left
        # owed in the ledger for the run that re-adjudicates the row.
        held = fail_held(row, run)
        if held and any(v == "fail" for _, v in due):
            for report_id, verdict in due:
                if verdict == "fail":
                    print(f"  HOLD  {fid} on #{report_id} (fail): {held}. Not sent.")
            due = [(r, v) for r, v in due if v != "fail"]
            if not due:
                continue

        # Rule 6, applied where the claim leaves the building. The two verdicts
        # are different claims and need different levels: `pass` verifies a fix
        # and needs V -- clean tree, tagged preregistration at HEAD -- while
        # `fail` says the defect still reproduces, which is what opens a defect
        # in the first place and needs only R. Sending either on less would be
        # a statement our own rules do not let us make about ourselves.
        level = admissibility(run).level
        floor = "V" if any(v == "pass" for _, v in due) else "R"
        if not (level == "V" or (floor == "R" and level == "R")):
            raise SystemExit(
                f"{fid} was adjudicated by {run_id}, which is level {level}: "
                f"{', '.join(admissibility(run).reasons) or 'no reason given'}.\n"
                f"A {floor}-level run is the floor for a {floor == 'V' and 'pass' or 'fail'}. "
                f"Nothing sent."
            )

        by_id = {r.get("report_id"): r for r in row["filing"]["reports"]}
        for report_id, verdict in due:
            work.append({
                "finding_id": fid,
                "report_id": report_id,
                "verdict": verdict,
                # Why a correction is owed, read from the fold rather than
                # worked out again here: the obligation and the sentence that
                # carries it have to come from one reading, or they drift the
                # way the two a2a readers did.
                "correction_reason": (
                    "regressed" if report_id in reopened else
                    fold_correction_reason(by_id.get(report_id) or {},
                                           row["filing"].get("verifications")
                                           or [])
                    if verdict == "fail" else None),
                "fingerprint": row["check"]["pinned_fingerprint"],
                "run_id": run_id,
                "level": level,
                "level_reasons": list(admissibility(run).reasons),
                "checked_at": adjudicated.get("at"),
                "tree_sha": run.get("git_head"),
                "prereg_id": run.get("prereg_id"),
                "checks": row.get("checks") or [],
                "title": row.get("title") or fid,
                "pin": pin_reason(fid, row["check"]["pinned_fingerprint"]),
                "helpers_same": helpers_match(row, run),
                "identity": identity_kind(run, row.get("checks") or []),
                "evidence_ids": sorted({
                    str(e) for result in (run.get("results") or [])
                    if result.get("nodeid") in set(row.get("checks") or [])
                    for e in (result.get("evidence_ids") or [])}),
                "failing_readings": (failing_readings(run, row.get("checks") or [])
                                     if verdict == "fail" else []),
            })
    return work


def _ran_under(run: dict, checks: list[str]) -> str | None:
    """The definition `run` ran these checks under, computed as the fold pins it,
    or None when the record cannot say (a check it did not run, no fingerprint).
    Call phase only: a setup or teardown result carries the AST hash whatever the
    check declares."""
    results = results_by_nodeid({"results": [r for r in run.get("results") or []
                                             if r.get("phase", "call") == "call"]})
    mine = [results.get(c) for c in checks]
    if not checks or any(r is None for r in mine):
        return None
    return _fingerprint_of(mine)


def fail_held(row: dict, run: dict) -> str | None:
    """Why a FAIL on this row must not go out now, or None.

    O01 (deep pass of 2026-10-25, 3/3). The obligation is the fold's, keyed on
    the pin and the run that adjudicated the row; the fold also records, beside
    it, runs of ours that touched the row WITHOUT adjudicating it -- a level-R
    pass (`last_exploratory_pass`, rule 6), a run that could not conclude
    (`not_checked_in`), an evidence-only reading. Nothing read those here, and
    #217 owed "our check still fails" a day after our own run passed the check
    as repaired, under a new fingerprint. Held when
      * a run of ours newer than the failing one passed the check, or
      * the definition is not the one that failed: a newer run of ours ran it
        under another fingerprint, or the pin now is one the failing run did
        not run (CHECK_CHANGED territory: the repair is verified first).
    A record we cannot read is not a record that agrees: the pass is still read
    off the row, and only the comparison it would have allowed is skipped.
    """
    check = row.get("check") or {}
    checks = row.get("checks") or []
    adjudicated = check.get("adjudicated_by") or {}
    failed_at = _instant(adjudicated.get("at"))
    pinned = check.get("pinned_fingerprint")
    failed_under = _ran_under(run, checks)
    why: list[str] = []

    if failed_under is not None and pinned and failed_under != pinned:
        why.append(f"the definition pinned now ({pinned[:12]}) is not the one "
                   f"{run.get('run_id')} failed under ({failed_under[:12]})")

    explored = check.get("last_exploratory_pass") or {}
    explored_at = _instant(explored.get("at"))
    if explored.get("run_id") and explored_at and failed_at and explored_at > failed_at:
        why.append(f"our own run {explored['run_id']} passed this check at "
                   f"{explored.get('at')}, after {run.get('run_id')} failed it")

    newer = [check.get(k) for k in ("last_exploratory_pass", "not_checked_in", "evidence_only")]
    newer = [n.get("run_id") if isinstance(n, dict) else n for n in newer]
    for other_id in dict.fromkeys(n for n in newer if n and n != run.get("run_id")):
        try:
            other = load_run(other_id)
        except Exception:  # noqa: BLE001 -- pruned or unreadable: cannot compare
            continue
        other_at = _instant(other.get("finished_at") or other.get("started_at"))
        if not (other_at and failed_at and other_at > failed_at):
            continue
        ran = _ran_under(other, checks)
        if ran is not None and ran != (failed_under or pinned):
            why.append(f"the check's definition changed since: {other_id} ran it "
                       f"under {ran[:12]}, not the {(failed_under or pinned or '')[:12]} "
                       f"it failed under -- the repair is verified first")
            break
    return "; ".join(why) or None


def failing_readings(run: dict, checks: list[str]) -> list[dict]:
    """What the run read where this row's checks failed: per failing check, its nodeid, what it
    expected (`right`), what it read (`left`) and the reason it gave.

    Week finding of 2026-10-18: a FAIL went out as "the check ... still fails" and no more, so
    the vendor could neither act on it nor correct us -- the #93 FAIL of 2026-10-21 rested on a
    route its own documentation calls session-only, and the text never named the route.
    """
    wanted, out = set(checks), []
    for result in run.get("results") or []:
        if (result.get("nodeid") not in wanted or result.get("outcome") != "failed"
                or result.get("role", "verdict") != "verdict"):
            continue
        measured = result.get("measurement") or {}
        out.append({"check": result["nodeid"],
                    "expected": measured.get("right"), "read": measured.get("left"),
                    "reason": measured.get("reason") or result.get("failure_repr") or ""})
    return out


# Their `evidence` field holds 8000 characters (422 on #130, 2026-09-28).
EVIDENCE_LIMIT = 8000
READINGS_SHOWN = 3


def _what_failed(item: dict, reason_cap: int) -> str:
    """The paragraph naming the failing reading(s), with each reason cut to `reason_cap`."""
    readings = item.get("failing_readings") or []
    if not readings:
        return ("WHAT FAILED: the run recorded no reading for this check beyond its failure; "
                "the request and response are provided on request.")

    def shown(value) -> str:
        return json.dumps(value, default=str, ensure_ascii=False)[:240]

    parts = []
    for reading in readings[:READINGS_SHOWN]:
        reason = str(reading.get("reason") or "").strip()
        if len(reason) > reason_cap:
            reason = reason[:reason_cap].rstrip() + " [...]"
        parts.append(f"  {reading.get('check')}\n"
                     f"  expected: {shown(reading.get('expected'))}; "
                     f"read: {shown(reading.get('read'))}\n"
                     f"  {reason}")
    more = len(readings) - READINGS_SHOWN
    return ("WHAT FAILED:\n" + "\n\n".join(parts)
            + (f"\n  ... and {more} more failing check(s)" if more > 0 else ""))


def identity_kind(run: dict, checks: list[str]) -> str | None:
    """Where this row's fingerprint came from: a declared claim, or the AST.

    qa/report_plugin.py:311 takes the Measurement's own fingerprint when the
    check offers one and hashes the function's syntax tree otherwise, so the
    two kinds are indistinguishable by the time the fold has them -- both are
    `check_fingerprint`. The run record still holds the measurement, so the
    provenance is read there rather than guessed.

    None when the checks in this row disagree or none of them ran: the
    verification then says the smaller true thing instead of picking one.
    """
    wanted = set(checks)
    kinds = {
        "declared" if ((result.get("measurement") or {}).get("fingerprint")) else "ast"
        for result in (run.get("results") or [])
        if result.get("nodeid") in wanted and result.get("role") == "verdict"
    }
    return kinds.pop() if len(kinds) == 1 else None


def helpers_match(row: dict, run: dict) -> bool | None:
    """Whether the helpers this row's checks call are the ones they called
    when the row last reproduced: True, False, or None when either run did
    not record them (they are recorded since 2026-09-23, A8) or the failing
    run's record is gone. Only True lets the pass say "the same test"."""
    checks = set(row.get("checks") or [])

    def helpers(record: dict):
        # Only this formula's hashes: an older run's hash of the same check
        # differs because the formula did, not the check (B02, 2026-09-25).
        found = {r.get("helpers_fingerprint")
                 for r in (record.get("results") or [])
                 if r.get("nodeid") in checks and r.get("role", "verdict") == "verdict"
                 and r.get("helpers_formula") == HELPERS_FORMULA}
        found.discard(None)
        return found or None

    now = helpers(run)
    if not now:
        return None
    for run_id in reversed(row.get("reproduced_in") or []):
        try:
            failed = load_run(run_id)
        except Exception:  # noqa: BLE001 -- pruned or unreadable: unknown
            continue
        then = helpers(failed)
        return None if then is None else then == now
    return None


def pin_reason(finding_id: str, fingerprint: str) -> str | None:
    """Why this definition was pinned by hand, or None if it was not.

    qa/fold.py:293 pins the fingerprint a row failed under by itself, inside
    the run that failed. Nothing else writes that field except a
    `pin_fingerprint` event, so an event carrying the fingerprint we are about
    to send means a human replaced the definition after the failure -- there is
    no innocent reading of it.

    Matched on the value as well as the finding: a row can be repaired twice,
    and only the pin naming THIS fingerprint describes the definition this
    verification is about.
    """
    latest = None
    for event in read_events():
        if (event.get("type") == "pin_fingerprint"
                and event.get("finding_id") == finding_id
                and event.get("value") == fingerprint):
            latest = event.get("reason") or None
    return latest


# qa.state.admissibility's reasons for a V-less run, in the vendor's words.
_LEVEL_R_SAID = {
    "git_dirty": "the working tree was not clean",
    "code_moved_during_run": "our code changed while it ran",
    "prereg_commit_mismatch": "it did not run at the commit the "
                              "preregistration was made at",
    "budget_truncated": "our own rate-limit budget cut it short",
    "no_prereg": "it was not preregistered",
}


def _level_r_said(item: dict, leave_out: tuple = ()) -> str:
    """The reasons a run is level R, in the vendor's words, never our keys."""
    return "; ".join(_LEVEL_R_SAID.get(r, "it fell short of the level our rules "
                                          "require to verify")
                     for r in dict.fromkeys(item.get("level_reasons") or [])
                     if r not in leave_out)


def _run_line(item: dict) -> str:
    """How the run was made, said at the level it actually has. B2 of the
    review of 2026-09-23 (3/3): a `fail` may go out from an R-level run --
    no clean tree, no preregistration -- and this line described every run as
    the V-level one. Absent a level, the V wording stands: a pass cannot go
    out below V (work() refuses it)."""
    if item.get("level") == "R" and item.get("prereg_id"):
        # R is also a PREREGISTERED run that fell short (RO06, deep pass of
        # 2026-09-24): PRE-0084 and PRE-0092 on a dirty tree, PRE-0128 with
        # our code moving under it. "Not preregistered" was false of those.
        why = _level_r_said(item)
        return (f"RUN: {item['run_id']} at commit {item['tree_sha']}, under "
                f"preregistration {item['prereg_id']}, but "
                f"{why or 'it fell short of the level our rules require to verify'}"
                f" -- so it is a run our rules admit to show that a defect "
                f"reproduces, not the kind of run that verifies a fix.")
    if item.get("level") == "R":
        # And WHY, as the branch above says it (O02, deep pass of 2026-10-25):
        # "at commit X" alone described a run on a dirty tree -- every level-R
        # run adjudicating a row that day -- as that commit.
        why = _level_r_said(item, leave_out=("no_prereg",))
        return (f"RUN: {item['run_id']} at commit {item['tree_sha']}"
                + (f", but {why}" if why else "")
                + ". It is a run our rules admit to show that a defect "
                  "reproduces; it was not preregistered, so it is not the kind "
                  "of run that verifies a fix.")
    return (f"RUN: {item['run_id']}, preregistration {item['prereg_id']}, on a "
            f"clean working tree at commit {item['tree_sha']}. The selector was "
            f"frozen and git-tagged BEFORE the run, so the set of checks could "
            f"not be narrowed after seeing the results.")


EVIDENCE_IDS_SHOWN = 10


def _evidence_offer(item: dict) -> str:
    """How they can check this, said truthfully.

    The repository is private, so "reproduce it from github" was never an
    offer they could take up. The evidence store is real, addressed by the
    hash of its content, and one message away.
    """
    ids = [str(i) for i in (item.get("evidence_ids") or []) if i]
    # Their `evidence` field is max_length 8000 (422 on #130, 2026-09-28): a
    # check citing a capture per page read listed ~200 ids and never arrived.
    shown = ids[:EVIDENCE_IDS_SHOWN]
    rest = len(ids) - len(shown)
    named = (f" under evidence id(s) {', '.join(shown)}"
             + (f" and {rest} more ({len(ids)} in all)" if rest else "")
             if ids else "")
    # An R-level run without a preregistration has none to offer (B2); one
    # that carried a preregistration has it (RO06).
    tail = ("as is the check's definition"
            if item.get("level") == "R" and not item.get("prereg_id") else
            "as are the check's definition and the preregistration named above")
    return ("EVIDENCE: the request and response behind this verdict are "
            f"retained{named} and are provided on request, {tail}.")


def body(item: dict) -> dict:
    checks = "\n".join(f"  {c}" for c in item["checks"])
    verdict = item["verdict"]
    # A hand-pinned definition may not be sold as the one that failed. The
    # check still passes and the fix is still real -- what must not go out is
    # "this is the same test, not a rewritten one", on a row where we cannot
    # know that. That is the single claim they cannot check for themselves, and
    # it is why they are being asked to believe the rest.
    #
    # It says PINNED, not REPAIRED, and the difference is the whole care here.
    # The 27 rows affected split two ways: some were repaired (the definition
    # moved and we say so), and some were pinned because the pre-contract runs
    # recorded no fingerprint at all, so there is nothing to have matched. A
    # blanket "we repaired this check" would be false for the second group --
    # the same overclaim in the other direction, made an hour after finding the
    # first. Both are true under one sentence: the pin was ours, here is why.
    pin = item.get("pin")
    if verdict == "pass" and pin:
        headline = (
            "VERDICT pass -- the check that recorded this defect now passes, "
            "under the definition PINNED for this row. That pin was written by "
            "us rather than taken from the failing run, so this is not "
            "automatically the identical test; our reason is below, judge it."
        )
        why_fingerprint = (
            "It is the pinned definition, which is not necessarily the one "
            "recorded at the failure. Why this row carries a pin, in our own "
            f"words: {pin}"
        )
    elif verdict == "pass" and item.get("helpers_same") is True:
        headline = (
            "VERDICT pass -- the check that recorded this defect now passes, "
            "under the same definition it failed under."
        )
        # H01 (deep pass of 2026-09-24): helpers_fingerprint hashes the
        # helpers in the check's own file, so that is what this says it
        # compared -- not everything the check calls.
        why_fingerprint = (
            "It matches the one recorded at the failure, and so do the helper "
            "functions and constants in the check's own file that it uses, so "
            "the check was not rewritten to pass. Code it imports from other "
            "modules is not part of this comparison."
        )
    elif verdict == "pass" and item.get("helpers_same") is False:
        # A8: a helper the check calls was rewritten after the failure. The
        # recorded definition matches; the whole of the test does not.
        headline = (
            "VERDICT pass -- the check that recorded this defect now passes. "
            "Its recorded definition is the one that failed, but a helper "
            "function or constant the check uses has changed since, so this "
            "is not automatically the identical test."
        )
        why_fingerprint = (
            "The recorded definition matches the one at the failure; a helper "
            "function or constant the check uses does not. Judge the change, "
            "provided on request."
        )
    elif verdict == "pass":
        # A8: the failure's run predates helper fingerprints, or is gone.
        # The strongest TRUE sentence is about the recorded definition alone.
        headline = (
            "VERDICT pass -- the check that recorded this defect now passes, "
            "under the same recorded definition it failed under."
        )
        why_fingerprint = (
            "That definition matches the one recorded at the failure. The "
            "helper functions the check calls were not fingerprinted then, so "
            "we do not claim more than that."
        )
    elif item.get("correction_reason") == "regressed":
        headline = (
            "VERDICT fail -- this defect is back. After your fix the check that "
            "recorded it passed; it now fails again. We are reopening this report "
            "instead of filing a new report for the same defect."
        )
    elif item.get("correction_reason") == "accepted":
        # The third case, and the reason two paid reports sat with them under
        # nothing at all. The two sentences below are both false of a report
        # they accepted and PAID without claiming a fix, and a sentence we
        # cannot stand behind does not get sent. `qa.fold.correction_reason`
        # is the one reader that tells the three apart.
        headline = (
            "VERDICT fail -- you accepted and paid this report, and the check "
            "that recorded the defect still fails under the definition now "
            "pinned for it. This is not a response to a claim of yours: it is "
            "our own re-reading, sent so your record shows where the defect "
            "actually stands."
        )
    elif item.get("correction_reason") == "our_pass":
        headline = (
            "VERDICT fail -- we sent you a pass on this report and can no "
            "longer stand behind it: the check that recorded the defect fails "
            "again. Read the run below rather than the earlier verification."
        )
    elif item.get("correction_reason") == "fix_claimed":
        headline = (
            "VERDICT fail -- the check that recorded this defect still fails, "
            "and a fix was claimed for it. This corrects the record: our "
            "re-check does not agree. Read the run below rather than the "
            "earlier verification."
        )
    else:
        # No reason recorded. The three sentences above each assert something
        # specific about what YOU did, and the narrowest of them is the wrong
        # default: the old disjunction is true whichever of the three it was,
        # so an unknown reason says less rather than saying something false.
        headline = (
            "VERDICT fail -- the check that recorded this defect still fails. "
            "This corrects the record: either a fix was claimed and our re-check "
            "does not agree, or we sent you a pass we can no longer stand behind. "
            "Read the run below rather than the earlier verification."
        )
    if verdict != "pass":
        # One paragraph for all three corrections. It lived inside the last
        # branch, so adding the other two left it unbound and `body()` raised
        # before a single byte was composed -- caught by the test that drives
        # the wording, which is the sibling of the UnboundLocalError of
        # 2026-09-07 one function along.
        why_fingerprint = (
            "It is quoted so you can tell a check we repaired from one we did "
            "not: if this differs from a fingerprint we sent you before, the "
            "definition moved and the earlier verdict was made under the old one."
        )
    # Two kinds of check produce two kinds of fingerprint, and this paragraph
    # used to describe only one of them. qa/report_plugin.py:311 prefers the
    # Measurement's own fingerprint and falls back to the AST hash only when a
    # check offers none -- so for every reconciliation row the value in this
    # payload is a hash of the claim declared in claims.yaml, and editing the
    # check function does not move it. Sending "a SHA-256 of the check
    # function's parsed syntax tree" beside such a value was false in both
    # halves, in the one paragraph whose whole job is to say how to read it.
    what_it_is = {
        "ast": (
            "a SHA-256 of the check function's parsed syntax tree. It changes "
            "when the check's logic changes and not when its comments or "
            "formatting do."
        ),
        "declared": (
            "a SHA-256 of the claim's declared definition in claims.yaml -- "
            "the two documents compared, the extractor read from each, and "
            "the relation and its direction. It changes when any of those "
            "change and not when the wording of the question does; the check "
            "function is a loop over the claims and is not part of it."
        ),
    }.get(item.get("identity"), (
        "a SHA-256 of this check's definition: the claim it is declared from "
        "where there is one, the check's own parsed source otherwise. It "
        "changes when that definition changes and not when comments or "
        "formatting do."
    ))
    def compose(failed: str) -> str:
        return (
            f"Independent re-check by the QA agent for hunter expire76.\n\n"
            f"{headline}\n\n"
            + (f"{failed}\n\n" if failed else "")
            + f"WHAT THE FINGERPRINT IS: {what_it_is} {why_fingerprint}\n\n"
            f"{_run_line(item)}\n\n"
            f"CHECK(S) THIS COVERS:\n{checks}\n\n"
            f"{_evidence_offer(item)}\n\n"
            f"FINDING {item['finding_id']}: {item['title']}"
        )

    # A fail says what failed (week finding of 2026-10-18), cut until it fits their field.
    evidence = compose("")
    if verdict != "pass":
        for cap in (1500, 700, 300, 100, 0):
            evidence = compose(_what_failed(item, cap))
            if len(evidence) <= EVIDENCE_LIMIT:
                break
    return {
        "verdict": verdict,
        "test_run_id": item["run_id"],
        "fingerprint": item["fingerprint"],
        "tree_sha": item["tree_sha"],
        "checked_at": item["checked_at"],
        "evidence": evidence,
    }


def verification_id(body) -> int | str | None:
    """The id their server assigned, or None.

    Rule 9: "`accepted` needs 2xx **and** a server report id". verify.py
    shipped taking the status alone, which submit.py has never done -- so a
    200 that is not a created verification (a proxy page, `success: false`, a
    202 queued) recorded as accepted, cleared verification_owed, and left the
    dashboard showing them holding something their server never made. There is
    no path back from that: the obligation is the only thing the sender reads.

    Their shape, captured: {"success": true, ..., "verification": {"id": 19}}.
    """
    if not isinstance(body, dict):
        return None
    if body.get("success") is False:
        return None
    nested = body.get("verification")
    if isinstance(nested, dict) and nested.get("id") is not None:
        return nested["id"]
    for key in ("verification_id", "id"):
        if body.get(key) is not None:
            return body[key]
    return None


def settle(item: dict, evidence_id: str | None) -> bool:
    """Record a verification their server holds and our journal does not.

    Not a new mechanism, and deliberately not a flag. `already_sent()` is
    already a read of their server -- the same evidence submit.py's
    `--reconcile` goes and fetches -- and we were simply not writing down what
    it found.

    Without this, one failure mode has no exit. If evidence capture fails
    between the POST and the outcome event, they hold the verification and we
    hold only an intent; the obligation is computed from accepted outcomes, so
    it stays owed for ever, and every later run's dedup read sees their copy
    and SKIPs. Nothing is sent and nothing clears: a badge nobody can clear,
    with rule 4 forbidding a hand fix.

    Returns True when it wrote something.
    """
    if not evidence_id:
        raise SystemExit(
            "refusing to settle a verification without the evidence of the "
            "read that found it -- the fold rejects an outcome that cites "
            "nothing, so this would record a fact with no support."
        )
    # Idempotent against the JOURNAL, not against the second hand. The
    # natural key for an outcome ends in |outcome|at, deliberately, so that a
    # timeout and its later settlement are two facts -- which means two
    # settlements a second apart are two events unless something looks. The
    # first version relied on append_event's dedup and its test passed only
    # because both calls fell inside one wall-clock second.
    # THE NEWEST accepted word for this definition, not any of them. Matching
    # every mark ever was consistent with `_told` while `_told` asked whether
    # a verdict had EVER been sent; since the #85 repair it reads the newest,
    # and the two disagreed on one path: pass at T1, fail at T2, then a
    # re-sent pass whose POST was accepted and whose `_capture` raised, so the
    # outcome went down as `unknown` and no mark was written. Every later run
    # saw their server's newest was a pass, called it a duplicate, and settle
    # found the T1 pass and wrote nothing -- an obligation that can never
    # clear, which is the badge settle() exists to prevent.
    marks = [e for e in read_events()
             if e.get("type") == "verification_outcome"
             and e.get("outcome") == "accepted"
             and e.get("finding_id") == item["finding_id"]
             and e.get("report_id") == item["report_id"]
             and e.get("fingerprint") == item["fingerprint"]]
    if marks:
        # Journal order breaks a tie, as it does in the fold: their
        # timestamps are truncated to the second.
        newest = max(enumerate(marks), key=lambda p: (str(p[1].get("at") or ""),
                                                      p[0]))[1]
        if newest.get("verdict") == item["verdict"]:
            return False
    wrote = append_event({
        "type": "verification_outcome", "at": _now(), "by": "agent",
        "source": "scripts/verify.py", "finding_id": item["finding_id"],
        "report_id": item["report_id"], "fingerprint": item["fingerprint"],
        "verdict": item["verdict"], "run_id": item["run_id"],
        "tree_sha": item["tree_sha"], "checked_at": item["checked_at"],
        "outcome": "accepted", "evidence_id": evidence_id,
        "reconciled_from": "verifications",
    })
    return wrote == "appended"


def already_sent(client, report_id: int) -> tuple[dict, str | None]:
    """Their LAST word per fingerprint, and the read's evidence.

    Rule 8, and the reason submit.py reads the tracker before filing: a read
    that failed is not a server with nothing on it. Refusing here costs one
    verification; guessing costs a duplicate that neither side can tell from a
    real second opinion.

    It used to return the SET of (fingerprint, verdict) pairs they hold, and
    `partition_by_what_they_hold` skipped anything in it. That makes a verdict
    unrepeatable: #85 held a pass at 20:08 and a fail at 21:46 under one
    definition, so when our check passed again the pass was "already held" --
    three hours older than the correction that had superseded it -- and their
    tracker kept the fail as the final reading for ten days. What matters is
    what a reader of their report sees last, so this ranks the rows.

    Ranked by `created_at`, then by numeric id. A row carrying neither cannot
    be ranked and never displaces a dated one; if NO row can be ranked, every
    verdict they hold is kept, which degrades to the old, duplicate-averse
    behaviour rather than to a re-send.
    """
    response = client.get(f"/api/v1/bounty/reports/{report_id}/verifications")
    evidence_id = None
    try:
        # SAFE, because that is what this read runs at. Passing MUTATE wrote
        # "MUTATE GET .../verifications" into the durable evidence archive --
        # cosmetic to the machinery, which enforces from CURRENT_TIER, and
        # misleading to anyone reading the archive as a record of what we did.
        evidence_id = _capture(response, SafetyTier.SAFE)
    except SystemExit:
        # A read we could not keep still tells us what to skip; it just cannot
        # settle anything, and settle() refuses without it.
        evidence_id = None
    if response.status_code == 404:
        # No verifications yet is a legitimate shape for a report nobody has
        # verified, and it is distinguishable from a failed read.
        return {}, evidence_id
    if response.status_code != 200:
        raise SystemExit(
            f"  ! verifications for #{report_id} answered HTTP "
            f"{response.status_code}, so what they already hold cannot be "
            f"known. Refusing to send blind."
        )
    try:
        payload = response.json()
    except ValueError:
        raise SystemExit(f"  ! verifications for #{report_id} was not JSON")
    rows = payload.get("verifications") if isinstance(payload, dict) else payload
    return _newest_per_fingerprint(rows or []), evidence_id


def _rank(row: dict):
    """(created_at, numeric id) -- or None when the row carries neither."""
    at = str((row or {}).get("created_at") or "")
    raw = str((row or {}).get("id") or "")
    number = int(raw) if raw.isdigit() else None
    if not at and number is None:
        return None
    return (at, number if number is not None else -1)


def _newest_per_fingerprint(rows: list) -> dict:
    """fingerprint -> the set of verdicts that count as theirs.

    One verdict where the rows can be ranked: their last word, which is the
    whole of #85's repair. A SET rather than a value because of the other
    half of the docstring above -- when no row under a fingerprint can be
    ranked, every verdict they hold is kept, and a dict of one could not say
    that. The first version returned whichever row happened to come first in
    their list and called the other one fresh, so with neither `created_at`
    nor a numeric id a pass and a fail under one definition meant re-POSTing
    one of them. Found by two readers on 2026-09-20.
    """
    newest: dict = {}
    ranks: dict = {}
    for row in rows:
        fingerprint = (row or {}).get("fingerprint")
        verdict = (row or {}).get("verdict")
        rank = _rank(row)
        if fingerprint not in newest:
            newest[fingerprint] = {verdict}
            ranks[fingerprint] = rank
            continue
        if rank is None:
            if ranks[fingerprint] is None:
                # Neither can be ranked, so neither is the last word: keep
                # both, which is the duplicate-averse reading this promises.
                newest[fingerprint].add(verdict)
            # Undatable against a dated row: it cannot claim to be the last
            # word, and it must not make the dated one disappear either.
            continue
        if ranks[fingerprint] is None or rank > ranks[fingerprint]:
            newest[fingerprint] = {verdict}
            ranks[fingerprint] = rank
    return newest


def send(client, items: list[dict], pause: int = PAUSE_SECONDS) -> list[dict]:
    results: list[dict] = []
    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        for index, item in enumerate(items):
            payload = body(item)
            at = _now()
            common = {
                "at": at, "by": "agent", "source": "scripts/verify.py",
                "finding_id": item["finding_id"], "report_id": item["report_id"],
                "fingerprint": item["fingerprint"], "run_id": item["run_id"],
                "verdict": item["verdict"], "tree_sha": item["tree_sha"],
                "checked_at": item["checked_at"],
            }
            append_event({**common, "type": "verification_intent"})

            try:
                response = client.post(_path(item["report_id"]), json=payload)
            except Exception as exc:  # noqa: BLE001
                append_event({**common, "type": "verification_outcome",
                              "at": _now(), "outcome": "unknown",
                              "reason": f"{type(exc).__name__}: {exc}"})
                results.append({**item, "outcome": "unknown", "error": str(exc)})
                continue

            # The outcome is written whatever happens next. _capture used to
            # raise SystemExit here, between the POST and this event, leaving
            # an intent with nothing to settle it -- and the obligation is
            # computed from accepted outcomes, so it could never clear.
            status = response.status_code
            try:
                evidence_id = _capture(response)
                capture_error = None
            except SystemExit as exc:
                evidence_id, capture_error = None, str(exc)

            # NOT `body` -- that is the module-level function that composed
            # the payload three lines up, and a local binding shadows it for
            # the whole of send(). The first draft of this hunk did exactly
            # that and send() raised UnboundLocalError before any POST, with
            # both suites green because no test called it.
            try:
                answer = response.json()
            except ValueError:
                answer = None
            server_id = verification_id(answer)

            # Rule 9: 2xx AND an id from their server. A 2xx without one is
            # not a created verification, whatever it looks like.
            if capture_error or not (200 <= status < 300 and server_id is not None):
                outcome = "unknown"
            else:
                outcome = "accepted"

            append_event({**common, "type": "verification_outcome",
                          "at": _now(), "outcome": outcome,
                          "http_status": status, "evidence_id": evidence_id,
                          **({"reason": capture_error} if capture_error else {})})
            results.append({**item, "outcome": outcome, "http_status": status,
                            **({"error": capture_error} if capture_error else {}),
                            **({} if server_id is not None or outcome == "accepted"
                               else {"error": f"HTTP {status} carried no "
                                              f"verification id"})})
            if capture_error:
                # Their answer could not be kept, so nothing further may be
                # sent on its authority -- but the attempt is now on record,
                # and the next run's dedup read will settle it. The rest is
                # named, as the rate-limit stop below names it (RO07).
                print(f"  STOP  {capture_error}")
                for skipped in items[index + 1:]:
                    results.append({**skipped, "outcome": "not attempted",
                                    "error": f"stopped: {capture_error}"})
                break

            remaining = response.headers.get("x-ratelimit-remaining")
            if remaining is not None and int(remaining) < 10:
                # Named, not dropped. submit.py breaks here and the rest of the
                # batch vanishes with no event and no line of output.
                for skipped in items[index + 1:]:
                    results.append({**skipped, "outcome": "not attempted",
                                    "error": f"stopped: {remaining} requests "
                                             f"left in their rate limit"})
                break
            if pause and index < len(items) - 1:
                time.sleep(pause)
    finally:
        CURRENT_TIER.reset(token)
    return results


def partition_by_what_they_hold(work, held):
    """Split the owed verifications into the ones to send and the ones they hold.

    A named function because it was five lines inside main(), reachable by no
    test: tests/meta/test_pipeline_adapters.py asserts what already_sent()
    PARSES and never that anything acts on it, so replacing the filter with
    `fresh = work` left the whole suite green while the vendor received a
    duplicate verification for every pair they already hold. Their server is
    the authority on what they have, and this is where that is honoured.
    """
    fresh, duplicates, later = [], [], []
    going: set[tuple] = set()
    for item in work:
        # Their newest word under this definition. Membership over everything
        # they hold made a verdict unrepeatable -- see already_sent -- so a
        # pass superseded by a fail could never be restored.
        theirs = held[item["report_id"]].get(item["fingerprint"]) or set()
        key = (item["report_id"], item["fingerprint"], item["verdict"])
        if item["verdict"] in theirs:
            duplicates.append(item)
        elif key in going:
            # Another row of ours sends this very verdict in this batch (RO03,
            # deep pass of 2026-09-24: #51 got two identical passes, twice).
            # The next run's read finds it held and settles this one.
            later.append(item)
        else:
            going.add(key)
            fresh.append(item)
    return fresh, duplicates, later


def settleable(duplicates, evidence):
    """The duplicates whose read was kept, and the ones whose was not.

    settle() refuses without evidence, rightly, and it raised SystemExit
    inside the loop -- so one read that could not be kept stopped every
    fresh send in the run (RO07, deep pass of 2026-09-24). It is held back
    alone, still owed; the next run's read settles it.
    """
    ready = [i for i in duplicates if evidence.get(i["report_id"])]
    return ready, [i for i in duplicates if not evidence.get(i["report_id"])]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="verify.py", description=__doc__)
    parser.add_argument("--confirm", action="store_true",
                        help="actually send. Without it nothing leaves.")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only", action="append", metavar="FINDING_ID")
    args = parser.parse_args(argv)
    if not (args.confirm or args.dry_run):
        parser.error("pass --dry-run to preview, --confirm to send")

    load_dotenv()
    work = owed(load_ledger(), args.only)
    if not work:
        print("nothing to send: no verification is owed, or each one owed is held above.")
        return 0
    print(f"{len(work)} verification(s) owed across "
          f"{len({w['report_id'] for w in work})} report(s)")

    if args.dry_run:
        for item in work:
            print("=" * 78)
            print(f"POST {_path(item['report_id'])}   "
                  f"[{item['verdict']}] {item['finding_id']}")
            print(json.dumps(body(item), indent=2)[:1400])
        print(f"\n{len(work)} composed. Nothing sent (--dry-run).")
        return 0

    install_client_guard()
    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    client = build_client(identities()["trusted"], registry, timeout=60.0)
    try:
        token = CURRENT_TIER.set(SafetyTier.SAFE)
        try:
            held: dict[int, dict] = {}
            evidence: dict[int, str | None] = {}
            unreadable: list[int] = []
            for item in work:
                rid = item["report_id"]
                if rid in held or rid in unreadable:
                    continue
                try:
                    held[rid], evidence[rid] = already_sent(client, rid)
                except (SystemExit, httpx.HTTPError) as refusal:
                    # One report we cannot read is one report we may not send
                    # blind -- not a run that stops. Their TLS timed out on a
                    # single report at 20:55 on 2026-09-12 and took every
                    # other verdict of that run with it, including ones whose
                    # own read had already succeeded. The refusal is per
                    # report, so the loss should be too.
                    #
                    # BOTH shapes, because the first version of this caught
                    # only SystemExit -- which `already_sent` raises on a bad
                    # status or an unreadable body -- while a TIMEOUT, the
                    # thing the paragraph above names, arrives as
                    # httpx.TransportError straight through SafetyTransport,
                    # which delegates without wrapping. The test used a 503,
                    # so it was green over the one path that already worked.
                    # Two readers found that on 2026-09-20, the same evening.
                    print(f"  ! {type(refusal).__name__} reading what they "
                          f"hold for #{rid}: {str(refusal)[:160]}"
                          if not isinstance(refusal, SystemExit)
                          else str(refusal))
                    unreadable.append(rid)
            if unreadable:
                print(f"  skipping {len(unreadable)} report(s) whose record "
                      f"could not be read: {unreadable}")
                work = [i for i in work if i["report_id"] not in unreadable]
                if not work:
                    return 1
        finally:
            CURRENT_TIER.reset(token)

        fresh, duplicates, later = partition_by_what_they_hold(work, held)
        for item in later:
            print(f"  LATER {item['finding_id']} on #{item['report_id']}: "
                  f"another row sends this {item['verdict']} in this run; "
                  f"the next run's read settles it")
        duplicates, unkept = settleable(duplicates, evidence)
        for item in unkept:
            print(f"  HOLD  {item['finding_id']} on #{item['report_id']}: "
                  f"they hold this {item['verdict']}, but the read that found "
                  f"it was not kept, so it cannot settle; still owed")
        for item in duplicates:
            # They hold it and the obligation says we do not, so this read
            # IS the settlement -- see settle(). Without it a capture that
            # failed after a successful POST leaves a debt nothing can pay.
            if settle(item, evidence[item["report_id"]]):
                print(f"  SETTLED {item['finding_id']} on "
                      f"#{item['report_id']}: their server holds this "
                      f"{item['verdict']}; recorded from the read")
            else:
                print(f"  SKIP  {item['finding_id']} on #{item['report_id']}: "
                      f"they already hold this {item['verdict']} for this "
                      f"fingerprint")

        # After deduplication, not before: requests we were never going to make
        # should not spend the budget.
        batch = fresh[:MAX_PER_RUN]
        if len(fresh) > MAX_PER_RUN:
            print(f"  {len(fresh)} to send, {MAX_PER_RUN} per run -- "
                  f"re-run to continue; the obligation resumes it")

        for result in send(client, batch):
            mark = {"accepted": "SENT ", "unknown": "?    ",
                    "not attempted": "-    "}.get(result["outcome"], "?    ")
            print(f"  {mark} {result['verdict']:<4} {result['finding_id']} "
                  f"on #{result['report_id']}"
                  + (f": {result.get('error') or result.get('http_status')}"
                     if result["outcome"] != "accepted" else ""))
    finally:
        client.close()

    print(f"\n-> {journal_path()}")
    print("   run scripts/ledger.py to fold these events into the ledger")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
