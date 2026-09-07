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

import html
import json
import os
import re
from pathlib import Path

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

REPO_ROOT = Path(__file__).resolve().parent.parent.parent

TRACKER = "/api/v1/bounty/reports"
MINE = "/api/v1/bounty/my-reports"
WORK_TRACKER = "/leaderboard/bugs"

# How many characters of a title have to be found before we believe the page
# is showing that report. Long enough that no two of our titles collide,
# short enough to survive a truncated heading.
_PROBE_CHARS = 38


_JSON_ESCAPE = re.compile(r"\\u([0-9a-fA-F]{4})")


def _squash(text: str) -> str:
    """Decode how the text was quoted, then keep letters and digits only.

    The page carries our titles inside an embedded JSON blob, so an apostrophe
    reaches it as `\\u0027`: report #73's title is published as "The bounty
    programme\\u0027s own reward totals disagree...". A raw substring of the
    title we sent therefore stopped matching at character 21, and on
    2026-09-07 this check reported a report as missing from the tracker while
    the tracker was displaying it. The defect was in the punctuation, and
    punctuation is not what the check is about.

    Dropping punctuation is not enough on its own, which the guard in
    tests/meta/test_pipeline_check_quality.py caught before this shipped: an
    escape sequence is mostly alphanumeric, so `&#39;` leaves a `39` and
    `\\u0027` a `u0027` sitting in the middle of the word. The escapes have to
    be decoded first, and only then does squashing ask the question the check
    means to ask -- is this title on the page -- without asserting anything
    about how the page chose to write a quote.
    """
    decoded = html.unescape(
        _JSON_ESCAPE.sub(lambda m: chr(int(m.group(1), 16)), text))
    return "".join(c for c in decoded.lower() if c.isalnum())


def _probe(title: str) -> str:
    return _squash(title)[:_PROBE_CHARS]

# The stages they publish, stated by them on 2026-09-05 when this was fixed:
# validated -> "Awaiting Review", in progress, testing, fixed, paid. Anything
# before validation is deliberately withheld, because an open report can name
# an unpatched issue; `invalid` never reaches validation at all.
PUBLISHED = frozenset({"validated", "in_progress", "in progress", "testing",
                       "qa_testing", "implementing", "fixed", "resolved",
                       "paid", "verified"})

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
def test_filed_reports_reach_the_work_tracker(rest_anon, rest_trusted):
    """A report accepted by the API has to arrive where triage happens.

    /leaderboard/bugs is the tracker that carries pending / qa_testing /
    implementing / resolved and the Linear ticket links -- the place where
    work is actually visible. If a filing lands only in the API's own list,
    the channel accepts reports into somewhere nobody works.

    Matched on TITLE, not on id: a bare number matches by chance in 250KB of
    markup, and a check that can pass by coincidence is not a check.

    Scoped to reports that have reached a PUBLISHED stage, which is the
    invariant they actually owe. Their stated posture, given when they fixed
    this on 2026-09-05, is that the page merges bounty reports from validated
    onwards -- an unvalidated report is deliberately never published, because
    it can name an unpatched issue. Demanding every filing appear would have
    kept this red forever on the two they closed as invalid, including our own
    correction #62, and a check that no possible behaviour can satisfy is not
    a check on them; it is a check on our own expectations.
    """
    submissions = _our_submissions()
    if not submissions:
        conclude(Measurement(
            verdict="inconclusive",
            reason="we have filed nothing, so there is nothing to look for",
            claim_id="bounty-pipeline-deadend"))
        return

    rows, why = _mine(rest_trusted)
    if rows is None:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"cannot tell which of our reports are publishable: {why}",
            claim_id="bounty-pipeline-deadend"))
        return

    stage = {r.get("id"): (r.get("status") or "").lower() for r in rows}
    due = [s for s in submissions if stage.get(s["report_id"]) in PUBLISHED]
    withheld = sorted(s["report_id"] for s in submissions
                      if stage.get(s["report_id"]) not in PUBLISHED)
    if not due:
        conclude(Measurement(
            verdict="inconclusive",
            reason=("none of our reports has reached a stage they publish, so "
                    "their absence from the page proves nothing"),
            left=withheld, claim_id="bounty-pipeline-deadend"))
        return

    page = rest_anon.get(WORK_TRACKER)
    if page.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"the work tracker answered HTTP {page.status_code}",
            right=page.status_code, claim_id="bounty-pipeline-deadend"))
        return

    # An empty probe is inside every haystack, so a title too short to
    # discriminate would pass silently rather than fail to be measured.
    unmeasurable = sorted(s["report_id"] for s in due
                          if len(_probe(s.get("title") or "")) < _PROBE_CHARS)
    if unmeasurable:
        conclude(Measurement(
            verdict="inconclusive",
            reason=(f"{len(unmeasurable)} report(s) have titles shorter than "
                    f"{_PROBE_CHARS} characters, which is too short to tell "
                    f"presence on the page from coincidence: {unmeasurable}"),
            left=unmeasurable, right=len(due),
            sources={"looked_in": WORK_TRACKER, "stages_from": MINE},
            claim_id="bounty-pipeline-deadend"))
        return

    haystack = _squash(page.text)
    missing = [s["report_id"] for s in due
               if _probe(s.get("title") or "") not in haystack]

    conclude(Measurement(
        verdict="failed" if missing else "passed",
        reason=(f"{len(missing)} of the {len(due)} reports of ours that have "
                f"reached a published stage are absent from the tracker where "
                f"work happens"
                + (f" (not counted: {withheld}, which they have not validated)"
                   if withheld else "")),
        left=sorted(missing), right=len(due),
        sources={"filed_via": f"POST {TRACKER}", "looked_in": WORK_TRACKER,
                 "stages_from": MINE},
        population={"filed": len(submissions), "publishable": len(due),
                    "withheld_pre_validation": withheld,
                    "page_bytes": len(page.text)},
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
