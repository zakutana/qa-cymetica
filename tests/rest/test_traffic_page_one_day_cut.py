"""/traffic cuts its days at one time zone (2026-11-11, report #342).

Request ET-34607 asks for one day cut on the page. On 9 and 10 Nov the page asked the API for `tz=utc` and said "One day
cut for everything on this page: days end at midnight UTC". On 11 Nov 08:51 UTC the page asked `tz=pacific` four times,
`tz=utc` none, and its footer said days end at midnight Pacific with "The Apps section is the one exception ... UTC".

**The rule.** The page does not say two cuts: its own text may not name both "midnight Pacific" and "midnight UTC" as
the day boundary.

VERDICTS. failed: the HTML says days end at midnight Pacific and also at midnight UTC. passed: it names one cut only.
inconclusive: the page could not be read, or names neither.

NOT asserted: which cut is the right one.
SAFE: one anonymous GET of the page.
"""

from __future__ import annotations

import re

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

CLAIM = "traffic-page-cuts-days-at-pacific-again-two-day-cuts"
PACIFIC = re.compile(r"midnight\s+Pacific", re.I)
UTC = re.compile(r"midnight\s+UTC", re.I)


@qa(component="rest.traffic", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_traffic_page_states_one_day_cut(rest_anon):
    """/traffic: the HTML's own words about where a day ends."""
    try:
        got = rest_anon.get("/traffic", headers={"Accept": "text/html"})
    except Exception as exc:  # noqa: BLE001
        raise Inconclusive(f"/traffic could not be read ({type(exc).__name__})")
    if got.status_code != 200:
        raise Inconclusive(f"/traffic answered HTTP {got.status_code}")
    html = got.text
    pacific, utc = len(PACIFIC.findall(html)), len(UTC.findall(html))
    asks = {"pacific": html.count("tz=pacific"), "utc": html.count("tz=utc")}
    if not pacific and not utc:
        raise Inconclusive("the page names neither 'midnight Pacific' nor 'midnight UTC'")
    conclude(Measurement(
        verdict="failed" if pacific and utc else "passed",
        reason=(f"the page names 'midnight Pacific' {pacific} times and 'midnight UTC' {utc} times; "
                f"tz= in its calls: {asks}"),
        left={"cuts_named": [n for n, c in (("pacific", pacific), ("utc", utc)) if c]},
        right={"cuts_named": 1},
        population={"html_bytes": len(html)},
        sources={"page": "GET /traffic (anonymous)"},
        claim_id=CLAIM))
