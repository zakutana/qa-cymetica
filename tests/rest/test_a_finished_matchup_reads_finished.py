"""A head-to-head matchup whose window has closed does not read as running.

`GET /api/v1/head-to-head/mine` is the one place an agent can read its own
matchups: a private matchup's page (/h2h/{slug}) answers 404 to the API key,
and so does `/api/v1/head-to-head/{slug}`. Each item carries `status` and a
`result` with `window: {start, end, as_of, live}` and a scoreboard per side.

**What was seen when this was written** (2026-09-28 ~09:40 UTC): ten
matchups of ours created 2026-09-24 19:10 UTC with `days: 3` -- `window.end`
2026-09-27 19:10 -- still read `status: running`, `window.live: true`, and
their `result.window.as_of` is the creation second itself: every scoreboard
shows 0 trades a side, while the same bots' my-clones rows read 4 to 8
trades executed. The window ended a day ago and the only record an agent can
read never moved past its first second.

**The claim:** a matchup whose `window.end` is in the past does not read
`status: running` or `window.live: true`. Measured on our own matchups only,
with an hour of grace after `end` for a settle job.

SAFE: GETs only.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

GRACE = timedelta(hours=1)


def _at(text):
    try:
        stamp = datetime.fromisoformat(str(text).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)


def stale(items: list[dict], now: datetime) -> tuple[list[dict], int]:
    """(matchups past their end that still read running or live, how many were past their end)."""
    past, out = 0, []
    for item in items:
        window = (item.get("result") or {}).get("window") or {}
        end = _at(window.get("end"))
        if end is None or now < end + GRACE:
            continue
        past += 1
        if item.get("status") == "running" or window.get("live") is True:
            out.append({"slug": item.get("slug"), "title": item.get("title"),
                        "end": window.get("end"), "as_of": window.get("as_of")})
    return out, past


@qa(component="rest.agents", tier=SafetyTier.SAFE, surface="rest")
def test_a_matchup_past_its_window_does_not_read_running(rest_trusted):
    """Our matchups past their window end, against the status they report."""
    response = rest_trusted.get("/api/v1/head-to-head/mine")
    if response.status_code != 200:
        raise Inconclusive(f"/head-to-head/mine answered HTTP {response.status_code}")
    items = (response.json() or {}).get("items") or []
    wrong, past = stale(items, datetime.now(timezone.utc))
    if not past:
        raise Inconclusive(
            f"none of our {len(items)} matchup(s) is an hour past its window "
            f"end yet; nothing to judge")
    conclude(Measurement(
        verdict="failed" if wrong else "passed",
        reason=(
            f"{len(wrong)} of {past} matchup(s) past their window end still "
            f"read running/live, their scoreboard as of their creation: "
            + "; ".join(f"{w['title']} (ended {w['end'][:16]}, as_of "
                        f"{str(w['as_of'])[:19]})" for w in wrong[:4])
            + (f" (+{len(wrong) - 4} more)" if len(wrong) > 4 else "")
            if wrong else
            f"all {past} matchup(s) past their window end read finished"),
        left={"stale": len(wrong), "past_end": past},
        right={"stale": 0},
    ))
