"""Tell them a check of ours passes under the fingerprint it last failed under.

The second write this project performs on purpose, and the first that is not a
report. Cymetica published POST /api/v1/bounty/reports/{id}/verification on
2026-09-07 and asked for the evidence we were holding; until then a fix we had
verified was a fact that existed only on our own dashboard.

What it sends is deliberately small. Not "the bug is fixed" -- that is their
claim to make -- but: this check, under this definition, passed in this
preregistered run against this tree, at this time. Every field is a fact
somebody else can re-derive from the public repository.

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
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa.client import build_client, install_client_guard  # noqa: E402
from qa.config import identities, load_dotenv  # noqa: E402
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
        due = ([(r, "pass") for r in obligations.get("verification_owed") or []]
               + [(r, "fail") for r in obligations.get("correction_owed") or []])
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

        # Rule 6, applied where the claim leaves the building. The two verdicts
        # are different claims and need different levels: `pass` verifies a fix
        # and needs V -- clean tree, tagged preregistration at HEAD -- while
        # `fail` says the defect still reproduces, which is what opens a defect
        # in the first place and needs only R. Sending either on less would be
        # a statement our own rules do not let us make about ourselves.
        run = load_run(run_id)
        level = admissibility(run).level
        floor = "V" if any(v == "pass" for _, v in due) else "R"
        if not (level == "V" or (floor == "R" and level == "R")):
            raise SystemExit(
                f"{fid} was adjudicated by {run_id}, which is level {level}: "
                f"{', '.join(admissibility(run).reasons) or 'no reason given'}.\n"
                f"A {floor}-level run is the floor for a {floor == 'V' and 'pass' or 'fail'}. "
                f"Nothing sent."
            )

        for report_id, verdict in due:
            work.append({
                "finding_id": fid,
                "report_id": report_id,
                "verdict": verdict,
                "fingerprint": row["check"]["pinned_fingerprint"],
                "run_id": run_id,
                "checked_at": adjudicated.get("at"),
                "tree_sha": run.get("git_head"),
                "prereg_id": run.get("prereg_id"),
                "checks": row.get("checks") or [],
                "title": row.get("title") or fid,
            })
    return work


def body(item: dict) -> dict:
    checks = "\n".join(f"  {c}" for c in item["checks"])
    verdict = item["verdict"]
    headline = (
        "VERDICT pass -- the check that recorded this defect now passes, "
        "under the same definition it failed under."
        if verdict == "pass" else
        "VERDICT fail -- the check that recorded this defect still fails. "
        "This corrects the record: either a fix was claimed and our re-check "
        "does not agree, or we sent you a pass we can no longer stand behind. "
        "Read the run below rather than the earlier verification."
    )
    why_fingerprint = (
        "Because it matches the one recorded at the failure, this is the same "
        "test, not a rewritten one that happens to pass."
        if verdict == "pass" else
        "It is quoted so you can tell a check we repaired from one we did not: "
        "if this differs from a fingerprint we sent you before, the definition "
        "moved and the earlier verdict was made under the old one."
    )
    evidence = (
        f"Independent re-check by the QA agent for hunter expire76.\n\n"
        f"{headline}\n\n"
        f"WHAT THE FINGERPRINT IS: a SHA-256 of the check function's parsed "
        f"syntax tree. It changes when the check's logic changes and not when "
        f"its comments or formatting do. {why_fingerprint}\n\n"
        f"RUN: {item['run_id']}, preregistration {item['prereg_id']}, on a clean "
        f"working tree at commit {item['tree_sha']}. The selector was frozen and "
        f"git-tagged BEFORE the run, so the set of checks could not be narrowed "
        f"after seeing the results.\n\n"
        f"CHECK(S) THIS COVERS:\n{checks}\n\n"
        f"REPRODUCE: github.com/zakutana/qa-cymetica at {item['tree_sha']}, then\n"
        f"  pytest {item['checks'][0] if item['checks'] else ''}\n\n"
        f"FINDING {item['finding_id']}: {item['title']}"
    )
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
    for event in read_events():
        if (event.get("type") == "verification_outcome"
                and event.get("outcome") == "accepted"
                and event.get("finding_id") == item["finding_id"]
                and event.get("report_id") == item["report_id"]
                and event.get("fingerprint") == item["fingerprint"]
                and event.get("verdict") == item["verdict"]):
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


def already_sent(client, report_id: int) -> tuple[set, str | None]:
    """(fingerprint, verdict) pairs their server holds, and the read's evidence.

    Rule 8, and the reason submit.py reads the tracker before filing: a read
    that failed is not a server with nothing on it. Refusing here costs one
    verification; guessing costs a duplicate that neither side can tell from a
    real second opinion.
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
        return set(), evidence_id
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
    return ({((r or {}).get("fingerprint"), (r or {}).get("verdict"))
             for r in (rows or [])}, evidence_id)


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
                # and the next run's dedup read will settle it.
                print(f"  STOP  {capture_error}")
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
        print("nothing is owed a verification.")
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
            held: dict[int, set] = {}
            evidence: dict[int, str | None] = {}
            for item in work:
                rid = item["report_id"]
                if rid not in held:
                    held[rid], evidence[rid] = already_sent(client, rid)
        finally:
            CURRENT_TIER.reset(token)

        fresh = []
        for item in work:
            if (item["fingerprint"], item["verdict"]) in held[item["report_id"]]:
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
                continue
            fresh.append(item)

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
