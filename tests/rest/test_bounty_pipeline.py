"""Does a report filed through the API arrive where the work is done?

Three findings sat UNVERIFIABLE for days -- raised in a Telegram message that
was never delivered, never turned into a check, and so never able to be
settled either way. A finding with no check is not open; it is unfalsifiable,
which is worse, because it occupies a row and cannot earn one.

They are checks now. Two of the three read `my-reports`, which is answering
with nothing at all today, so they report Inconclusive with the reason rather
than a verdict -- an honest "we cannot see" instead of a guess in either
direction.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

TRACKER = "/api/v1/bounty/reports"
MINE = "/api/v1/bounty/my-reports"
WORK_TRACKER = "/leaderboard/bugs"

# Sent on every submission. The finding is that some are accepted and then
# not stored, so what comes back is compared against what went out.
SUBMITTED_FIELDS = ("hunter_name", "steps_to_reproduce", "expected_behavior",
                    "actual_behavior", "url")


def _our_submissions() -> list[dict]:
    """What we have filed, from the journal.

    Not from state/submissions.json: that file stopped being written when
    filing became two events, so it ends at #56 and this check would have
    measured a shrinking, stale population without saying so.
    """
    from qa.state import read_events

    titles: dict[str, str] = {}
    out: list[dict] = []
    for event in read_events():
        if event.get("type") == "filing_intent":
            titles[event["key"]] = event.get("title") or ""
        elif (event.get("type") == "filing_outcome"
              and event.get("outcome") == "accepted"
              and event.get("report_id") is not None):
            out.append({"report_id": event["report_id"],
                        "title": titles.get(event.get("key"), "")})
    return out


def _mine(rest_trusted):
    """Our own reports as the platform returns them, or why we cannot see."""
    wallet = os.environ.get("QA_WALLET_ADDRESS", "")
    if not wallet:
        return None, "QA_WALLET_ADDRESS is not set"
    response = rest_trusted.get(MINE, params={"wallet_address": wallet})
    if response.status_code != 200:
        return None, f"my-reports answered HTTP {response.status_code}"
    rows = response.json().get("reports") or []
    if not rows:
        return None, ("my-reports returned zero rows for our wallet, so there "
                      "is nothing to compare what we sent against")
    return rows, None


@qa(component="rest.support", tier=SafetyTier.SAFE, surface="rest",
    claim="bounty-pipeline-deadend")
def test_filed_reports_reach_the_work_tracker(rest_anon):
    """A report accepted by the API has to arrive where triage happens.

    /leaderboard/bugs is the tracker that carries pending / qa_testing /
    implementing / resolved and the Linear ticket links -- the place where
    work is actually visible. If a filing lands only in the API's own list,
    the channel accepts reports into somewhere nobody works.

    Matched on TITLE, not on id: a bare number matches by chance in 250KB of
    markup, and a check that can pass by coincidence is not a check.
    """
    submissions = _our_submissions()
    if not submissions:
        conclude(Measurement(
            verdict="inconclusive",
            reason="we have filed nothing, so there is nothing to look for",
            claim_id="bounty-pipeline-deadend"))
        return

    page = rest_anon.get(WORK_TRACKER)
    if page.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"the work tracker answered HTTP {page.status_code}",
            right=page.status_code, claim_id="bounty-pipeline-deadend"))
        return

    haystack = page.text.lower()
    missing = [s["report_id"] for s in submissions
               if (s.get("title") or "").strip()[:45].lower() not in haystack]

    conclude(Measurement(
        verdict="failed" if missing else "passed",
        reason=(f"{len(missing)} of {len(submissions)} reports we filed through "
                f"the API do not appear in the tracker where work happens"),
        left=sorted(missing), right=len(submissions),
        sources={"filed_via": f"POST {TRACKER}", "looked_in": WORK_TRACKER},
        population={"submitted": len(submissions), "page_bytes": len(page.text)},
        claim_id="bounty-pipeline-deadend"))


@qa(component="rest.support", tier=SafetyTier.SAFE, surface="rest",
    claim="bounty-fields-dropped")
def test_submitted_fields_are_stored(rest_trusted):
    """Fields the filing endpoint accepts and then does not keep.

    Accepting a field and discarding it is worse than rejecting it: the
    sender believes the information arrived.
    """
    rows, why = _mine(rest_trusted)
    if rows is None:
        conclude(Measurement(
            verdict="inconclusive", reason=f"cannot tell: {why}",
            claim_id="bounty-fields-dropped"))
        return

    ours = {s["report_id"] for s in _our_submissions()}
    theirs = [r for r in rows if r.get("id") in ours]
    if not theirs:
        conclude(Measurement(
            verdict="inconclusive",
            reason="none of our own reports came back, so nothing can be compared",
            claim_id="bounty-fields-dropped"))
        return

    dropped = sorted({field for field in SUBMITTED_FIELDS
                      for row in theirs if not row.get(field)})
    conclude(Measurement(
        verdict="failed" if dropped else "passed",
        reason=(f"{len(dropped)} of the {len(SUBMITTED_FIELDS)} fields we send "
                f"come back empty on every one of our reports: "
                f"{', '.join(dropped) or 'none'}"),
        left=dropped, right=list(SUBMITTED_FIELDS),
        population={"reports_compared": len(theirs)},
        sources={"sent_to": f"POST {TRACKER}", "read_from": MINE},
        claim_id="bounty-fields-dropped"))


@qa(component="rest.support", tier=SafetyTier.SAFE, surface="rest",
    claim="bounty-hunter-name-lost")
def test_hunter_name_is_retained(rest_trusted):
    """Named separately from the other dropped fields because it is the one
    that decides who gets credit for a finding."""
    rows, why = _mine(rest_trusted)
    if rows is None:
        conclude(Measurement(
            verdict="inconclusive", reason=f"cannot tell: {why}",
            claim_id="bounty-hunter-name-lost"))
        return

    sent = os.environ.get("QA_HUNTER_NAME", "")
    if not sent:
        conclude(Measurement(
            verdict="inconclusive",
            reason="QA_HUNTER_NAME is not set, so we do not know what we sent",
            claim_id="bounty-hunter-name-lost"))
        return

    ours = {s["report_id"] for s in _our_submissions()}
    theirs = [r for r in rows if r.get("id") in ours]
    kept = [r["id"] for r in theirs if (r.get("hunter_name") or "") == sent]

    conclude(Measurement(
        verdict="failed" if len(kept) < len(theirs) else "passed",
        reason=(f"hunter_name survives on {len(kept)} of {len(theirs)} of our "
                f"reports; we send {sent!r} on every one"),
        left=len(kept), right=len(theirs),
        population={"reports_compared": len(theirs)},
        sources={"sent_to": f"POST {TRACKER}", "read_from": MINE},
        claim_id="bounty-hunter-name-lost"))
