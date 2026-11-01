"""The Products tab's 30-day figure is lower than the distinct people /app-usage counts for the same product (2026-11-01).

`GET /api/v1/company/products` -> `visitors` is, by their own definition, distinct daily visitors summed
over the range, so one person on three days is three. A sum of days can only be at least the number of
distinct people over those days. `GET /api/v1/app-usage` -> `humans[].users` is distinct people over its
30 days. Read 2026-11-01: Build a Company 40 against 126, Agent Casino 94 against 148, while Gem Screener
(248 against 206) and Chart Analyzer (182 against 121) sit the way the arithmetic says they must. So the
Products tab misses most of the people on those two products. Signed in, /traffic/mine says the same for
Build a Company: 94 unique visitors over 30 days against 40.

**The rule.** For a product that /app-usage lists under the same path and the same name, over the same
number of days, visitors * MARGIN is at least users. MARGIN is 1.25 because /app-usage calls its figures
estimates; the claim is a figure far under the floor, not a near miss.

VERDICTS. failed: at least one comparable product is under the floor. passed: at least one comparable
product and none under it. inconclusive: a failed read, a window that is not 30 days on either side,
or no product comparable (the same path under another name is a group, e.g. "Crypto Radars" on
/team-dump-radar, and is not compared).

NOT asserted: which of the two counts is right about the product's real audience, or why they differ;
/app-usage may count more of a product's pages than the Products tab does, and that would be this defect.
SAFE: two GETs; the key is sent by the client in the header and never printed or recorded.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

CLAIM = "products-people-not-below-app-usage"
PRODUCTS = "/api/v1/company/products"
USAGE = "/api/v1/app-usage"
DAYS = 30
MARGIN = 1.25


def comparable(products: list[dict], humans: list[dict]) -> list[dict]:
    """Same path and same name on both sides; the rest are groups or are not listed."""
    rows = []
    for product in products:
        for row in humans:
            if row.get("path") == product.get("path") and row.get("app") == product.get("name"):
                rows.append({"name": product["name"], "visitors": product.get("visitors") or 0,
                             "users": row.get("users") or 0})
    return rows


def under_floor(rows: list[dict]) -> list[dict]:
    """The rows whose sum of days cannot be a count of that many distinct people."""
    return [r for r in rows if r["visitors"] * MARGIN < r["users"]]


@qa(component="rest.company", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_products_people_not_below_app_usage(rest_anon, rest_trusted):
    """Both 30-day figures for every product listed on both sides."""
    try:
        products = rest_trusted.get(PRODUCTS)
        usage = rest_anon.get(USAGE)
    except Exception as exc:  # noqa: BLE001 - a failed read is not an empty read (rule 8)
        raise Inconclusive(f"a read failed ({type(exc).__name__})")
    for name, resp in ((PRODUCTS, products), (USAGE, usage)):
        if resp.status_code != 200:
            raise Inconclusive(f"{name} answered HTTP {resp.status_code}")
    try:
        left, right = products.json(), usage.json()
        days = (left["days"], right["window"]["days"])
        rows = comparable(left["products"], right["humans"])
    except Exception as exc:  # noqa: BLE001
        raise Inconclusive(f"a body was not the JSON expected ({type(exc).__name__})")
    if days != (DAYS, DAYS):
        raise Inconclusive(f"the windows are {days}, not {DAYS} days on both sides")
    if not rows:
        raise Inconclusive("no product is listed under the same path and name on both sides")
    low = under_floor(rows)
    conclude(Measurement(
        verdict="failed" if low else "passed",
        reason=("; ".join(f"{r['name']}: {r['visitors']} on the Products tab, a sum of days, against "
                          f"{r['users']} distinct people on /app-usage" for r in low)
                or f"all {len(rows)} comparable products are at or above the floor"),
        left={"under_floor": len(low)},
        right={"under_floor": 0},
        population={"compared": rows, "margin": MARGIN},
        sources={"products": f"{PRODUCTS} products[].visitors", "usage": f"{USAGE} humans[].users",
                 "credential": "X-API-Key, trusted tier (value never recorded)"},
        claim_id=CLAIM))
