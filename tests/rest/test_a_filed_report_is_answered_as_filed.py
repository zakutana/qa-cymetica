"""A report the server creates is answered as created.

`llms.txt` documents the one route a hunter files through:

    POST /api/v1/bounty/reports: File a bug report (X-API-Key or session)

An HTTP 5xx says the server could not complete the request. A client that
receives one has to assume nothing was filed -- and retries, which is how a
duplicate ticket is made (their own 409 on a duplicate title within 24 h only
catches a retry that keeps the title).

**What was seen.** Three of our submissions answered HTTP 500 and the report
existed anyway, found only because `scripts/submit.py --reconcile` compares
an unclear outcome against `GET /api/v1/bounty/my-reports`:

    #110  build-stats-window                       2026-09-20 17:40 UTC
    #113  bb-building-tile                         2026-09-20 21:01 UTC
    #122  card-tradeable-now-disagrees-mcp-rest    2026-09-22 23:55 UTC
          (their server_created_at 23:55:08, our 500 at 23:55:18)

Three of about thirteen submissions in those three days, so it is
intermittent, and a check over one submission is a coin flip (the rotating-
population lesson). This one reads the newest TWELVE: at the observed rate a
clean run of twelve would happen by chance under 5% of the time.

**This check files nothing.** It reads what submit.py journalled -- intent,
outcome with its HTTP status, and the reconciled outcome with the server's
report id -- and judges the newest twelve submissions:

  * one answered 5xx whose report exists (a later accepted outcome for the
    same key carries a report id) -- fail;
  * twelve answered 2xx with their report id, none masked -- pass;
  * fewer than twelve and none masked -- inconclusive.

A 5xx whose report does NOT exist is the server failing honestly, not this.

**After their fix only.** Their own record of #123 reads `fixed_at`
2026-09-23T02:41:50 and "Fixed in 3299e580b, live" (the CentCom bridge held
the DB session past its idle reap, and the response read of the saved report
died). The window is the newest twelve submitted AFTER that: a masked 500
from before it is history, named in the population and never judged. Until
2026-09-25 the window reached back past the fix, so #122 of the night before
kept the row "still reproducible" on evidence older than the claim it was
answering.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from qa.state import read_events

WINDOW = 12
ROUTE = "POST /api/v1/bounty/reports"
# Their `fixed_at` on #123, from GET /api/v1/bounty/my-reports.
FIXED_AT = "2026-09-23T02:41:50"
FIX_SOURCE = "#123 fixed_at 2026-09-23T02:41:50 UTC (3299e580b)"


def submissions(events) -> list[dict]:
    """Every filing, oldest first: its key, when, the POST's status, and the
    report id the server gave -- on the answer or on reconciling it."""
    by_key: dict[str, dict] = {}
    for e in events:
        key = e.get("key")
        if not key or e.get("type") not in ("filing_intent", "filing_outcome"):
            continue
        row = by_key.setdefault(key, {"key": key, "at": e.get("at") or "",
                                      "status": None, "report_id": None,
                                      "reconciled": False})
        if e["type"] == "filing_outcome":
            if isinstance(e.get("http_status"), int) and row["status"] is None:
                row["status"] = e["http_status"]
            if e.get("report_id") is not None:
                row["report_id"] = e["report_id"]
                row["reconciled"] = bool(e.get("reconciled_from"))
    return sorted(by_key.values(), key=lambda r: (r["at"], r["key"]))


def _masked(row: dict) -> bool:
    """A 5xx whose report RECONCILING found -- the server made it and said it
    had not. An honest 500 sent again under the same key and answered 201
    with its id is two honest answers, and the first status beside the last
    id read as this defect (B06, deep pass of 2026-09-24)."""
    return isinstance(row["status"], int) and row["status"] >= 500 \
        and row["report_id"] is not None and row["reconciled"]


@qa(component="rest.support", tier=SafetyTier.SAFE, surface="rest")
def test_a_report_the_server_creates_is_answered_as_created():
    """The newest twelve of our filings since their fix, each against the
    report it made."""
    every = submissions(read_events())
    rows = [r for r in every if r["at"][:19] >= FIXED_AT]
    history = [f"#{r['report_id']} ({r['at'][:16]} UTC)"
               for r in every if r["at"][:19] < FIXED_AT and _masked(r)]
    newest = rows[-WINDOW:]
    masked = [r for r in newest if _masked(r)]
    if masked:
        conclude(Measurement(
            verdict="failed",
            reason=(f"{len(masked)} of our newest {len(newest)} submission(s) to "
                    f"{ROUTE} answered HTTP {masked[-1]['status']} and the report "
                    f"was created anyway: "
                    + ", ".join(f"#{r['report_id']} ({r['key']}, {r['at'][:16]} UTC)"
                                for r in masked)
                    + " -- a client told the filing failed retries it"),
            left=[(r["report_id"], r["status"]) for r in masked],
            right="a created report answered 2xx with its id",
            population={"window": [{k: r[k] for k in ("key", "at", "status", "report_id")}
                                   for r in newest]},
            sources={"contract": f"llms.txt: {ROUTE} 'File a bug report'",
                     "log": "state/journal/events.jsonl (filing_intent / "
                            "filing_outcome, reconciled against my-reports)"}))
        return
    clean = [r for r in newest if isinstance(r["status"], int)
             and 200 <= r["status"] < 300 and r["report_id"] is not None]
    if len(newest) < WINDOW or len(clean) < WINDOW:
        raise Inconclusive(
            f"{len(clean)} clean submission(s) of {len(newest)} since {FIX_SOURCE}; "
            f"twelve are needed before an intermittent 500 can be called gone"
            + (f". Before the fix, history and not judged: {', '.join(history)}"
               if history else ""))
    conclude(Measurement(
        verdict="passed",
        reason=(f"the newest {WINDOW} submissions to {ROUTE} since {FIX_SOURCE} "
                f"were each answered 2xx with the id of the report they created"),
        left=len(masked), right=0,
        population={"window": [r["report_id"] for r in newest],
                    "before_fix": history},
        sources={"log": "state/journal/events.jsonl", "fix": FIX_SOURCE}))
