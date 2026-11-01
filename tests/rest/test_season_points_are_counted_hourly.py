"""The Products tab says season points are "Counted hourly"; the count stopped at the season's first hour (2026-11-01).

`GET /api/v1/company/14/season-breakdown` (14 is our own company) carries `recomputed_hourly: true`, and
`static/company/app.js` writes "Counted hourly" under the product's points. Read twice on 2026-11-01,
at about 18:45 and at 19:07 UTC, `computed_at` was 2026-11-01T07:55:30Z both times: over eleven hours
old on a figure that says it is at most about one. That is the figure the season's prizes are paid on.

**The rule.** While the endpoint says `recomputed_hourly`, `computed_at` is not more than STALE_AFTER old
by the response's own Date header (their clock, not ours). Three hours is the margin: a late or a
skipped run is not the claim, a count that has stopped is.

VERDICTS. failed: recomputed_hourly is true and computed_at is older than STALE_AFTER. passed: it is
true and computed_at is within STALE_AFTER. inconclusive: any failed read, either field or the Date header
missing or unreadable, or the endpoint no longer says hourly (nothing promised).

NOT asserted: that the points themselves are right, or what they should be on the season's first day.
SAFE: one GET; the key is sent by the client in the header and never printed or recorded.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

CLAIM = "season-points-are-counted-hourly"
BREAKDOWN = "/api/v1/company/14/season-breakdown"
STALE_AFTER = timedelta(hours=3)


def verdict_for(hourly: object, age: timedelta) -> str:
    """failed / passed / inconclusive from the promise and the age of the count."""
    if hourly is not True:
        return "inconclusive"
    return "failed" if age > STALE_AFTER else "passed"


@qa(component="rest.company", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_season_points_are_counted_hourly(rest_trusted):
    """The promise and the count's age, both from one response."""
    try:
        got = rest_trusted.get(BREAKDOWN)
    except Exception as exc:  # noqa: BLE001 - a failed read is not an empty read (rule 8)
        raise Inconclusive(f"{BREAKDOWN} could not be read ({type(exc).__name__})")
    if got.status_code != 200:
        raise Inconclusive(f"{BREAKDOWN} answered HTTP {got.status_code}")
    try:
        body = got.json()
        computed = datetime.fromisoformat(body["computed_at"].replace("Z", "+00:00"))
        now = parsedate_to_datetime(got.headers["date"]).astimezone(timezone.utc)
    except Exception as exc:  # noqa: BLE001
        raise Inconclusive(f"computed_at or the Date header could not be read ({type(exc).__name__})")
    hourly = body.get("recomputed_hourly")
    age = now - computed
    verdict = verdict_for(hourly, age)
    if verdict == "inconclusive":
        raise Inconclusive(f"{BREAKDOWN} no longer says recomputed_hourly: true (reads {hourly!r})")
    conclude(Measurement(
        verdict=verdict,
        reason=(f"{BREAKDOWN} says recomputed_hourly: true, and its count is from {body['computed_at']}, "
                f"{age.total_seconds() / 3600:.1f} hours before the response's Date header"),
        left={"age_hours": round(age.total_seconds() / 3600, 1)},
        right={"age_hours_at_most": STALE_AFTER.total_seconds() / 3600},
        population={"computed_at": body["computed_at"], "date_header": got.headers["date"],
                    "season": body.get("season")},
        sources={"count": f"{BREAKDOWN} computed_at, recomputed_hourly",
                 "clock": "the response's Date header",
                 "credential": "X-API-Key, trusted tier (value never recorded)"},
        claim_id=CLAIM))
