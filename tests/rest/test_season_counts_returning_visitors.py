"""The season counts no returning visitor on Gem Screener, which had 62, 63 and 55 people on three days (2026-11-05).

The Products tab says: "Returning visitor (signed out, same browser on 2+ days): 1 point, +0.25 per further
day from the 3rd; at most 25 % of your signed-in points." `GET /api/v1/company/14/season-breakdown` says
`visitors: 0` for all eleven products on 2026-11-05 06:51 UTC. `GET /api/v1/company/products` has Gem
Screener at 62, 63 and 55 distinct people on its last three days (from 11 on the day before), and
`GET /api/v1/app-usage` says 14 % of its 341 people in 30 days came back.

**The rule.** If Gem Screener's last three daily counts are each at least FLOOR people and the breakdown
counts no returning visitor on it, while /app-usage says at least CAME_BACK_PCT % of its people came back,
the count is not reading the visits the site itself reports.

VERDICTS. failed: those three readings. passed: the breakdown counts at least one returning visitor on it.
inconclusive: any read failed, the product is missing from a document, or its last three days do not reach
FLOOR (nothing to count) or /app-usage reports fewer than CAME_BACK_PCT % (a population that does not return).

NOT asserted: how many returning visitors there should be, or that the points are capped wrongly (the cap is
25 % of signed-in points, and Gem Screener has none; that is why points can be 0 where visitors are not).
SAFE: three GETs; the key is sent by the client in the header and never printed or recorded.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

CLAIM = "season-counts-returning-visitors"
PATH = "/gem-screener"
FLOOR = 30
CAME_BACK_PCT = 5


def verdict_for(visitors: int, last3: list, came_back_pct: float) -> str:
    """failed / passed / inconclusive from the season's visitors and the site's own readings."""
    if visitors > 0:
        return "passed"
    if len(last3) < 3 or min(last3) < FLOOR or came_back_pct < CAME_BACK_PCT:
        return "inconclusive"
    return "failed"


def _json(client, url: str):
    try:
        got = client.get(url)
    except Exception as exc:  # noqa: BLE001 - a failed read is not an empty read (rule 8)
        raise Inconclusive(f"{url} could not be read ({type(exc).__name__})")
    if got.status_code != 200:
        raise Inconclusive(f"{url} answered HTTP {got.status_code}")
    try:
        return got.json()
    except Exception as exc:  # noqa: BLE001
        raise Inconclusive(f"{url} did not answer JSON ({type(exc).__name__})")


@qa(component="rest.company", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_season_counts_returning_visitors(rest_trusted):
    """The breakdown's visitors against the product's own daily people and the site's came-back share."""
    breakdown = _json(rest_trusted, "/api/v1/company/14/season-breakdown")
    products = _json(rest_trusted, "/api/v1/company/products")
    usage = _json(rest_trusted, "/api/v1/app-usage")
    row = next((p for p in breakdown.get("products") or [] if p.get("path") == PATH), None)
    prod = next((p for p in products.get("products") or [] if p.get("path") == PATH), None)
    use = next((u for u in usage.get("humans") or [] if u.get("path") == PATH), None)
    if row is None or prod is None or use is None:
        raise Inconclusive(f"{PATH} is missing from one of the three documents")
    daily = prod.get("daily")
    try:
        visitors = int(row["visitors"])
        last3 = [int(x) for x in daily[-3:]]
        pct = float(use["came_back_pct"])
    except Exception as exc:  # noqa: BLE001
        raise Inconclusive(f"visitors, daily or came_back_pct could not be read ({type(exc).__name__})")
    verdict = verdict_for(visitors, last3, pct)
    if verdict == "inconclusive":
        raise Inconclusive(f"nothing to count: last three days {last3}, came back {pct}%")
    conclude(Measurement(
        verdict=verdict,
        reason=(f"season-breakdown counts {visitors} returning visitors on {PATH}; its last three days are "
                f"{last3} people and /app-usage says {pct:g} % of its people came back"),
        left={"returning_visitors_in_season": visitors},
        right={"daily_people_last_3_days": last3, "came_back_pct_30_days": pct},
        population={"computed_at": breakdown.get("computed_at"), "season": breakdown.get("season"),
                    "app_usage_window": usage.get("window")},
        sources={"count": "GET /api/v1/company/14/season-breakdown products[path].visitors",
                 "daily": "GET /api/v1/company/products products[path].daily",
                 "came_back": "GET /api/v1/app-usage humans[path].came_back_pct",
                 "credential": "X-API-Key, trusted tier (value never recorded)"},
        claim_id=CLAIM))
