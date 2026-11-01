"""A Products tile and the "People per day" chart under it disagree: Agent Casino 94 against 22 (2026-11-01).

`static/company/app.js` draws both from one object of `GET /api/v1/company/products`: the tile from
`visitors`, the sparkline and the panel's "People per day · last 30 days" bars from `daily`. Their own
definition makes `visitors` the sum of its days, and 8 of 9 products do add up. Agent Casino read
visitors 94 and a `daily` list adding up to 22, with nothing before 2026-10-26. The likely cause is the
page's move from /agent-tournaments to /agent-casino: the total kept the old path's days and the
list did not. Likely only: nothing we can read names it.

**The rule.** Over one response, a product's `visitors` equals the sum of its `daily`, within TOLERANCE.

VERDICTS. failed: a product with visitors differs from its sum by more than TOLERANCE. passed: at least
one product with visitors and none differs. inconclusive: a failed read, no product with visitors, or
any `daily` that is not a list of numbers.

NOT asserted: which of the two is right, or that the daily figures count people rightly (see
test_products_tile_people_are_people, which reads the word over the total).
SAFE: one GET; the key is sent by the client in the header and never printed or recorded.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

CLAIM = "products-tile-and-its-chart-agree"
PRODUCTS = "/api/v1/company/products"
TOLERANCE = 2


def disagreeing(products: list[dict]) -> list[dict]:
    """The products with visitors whose total is not the sum of their days."""
    return [{"name": p.get("name"), "visitors": p["visitors"], "sum_of_daily": sum(p["daily"])}
            for p in products
            if (p.get("visitors") or 0) > 0 and abs(p["visitors"] - sum(p["daily"])) > TOLERANCE]


@qa(component="rest.company", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_products_tile_and_its_chart_agree(rest_trusted):
    """Every product's total against its own days, in one response."""
    try:
        got = rest_trusted.get(PRODUCTS)
    except Exception as exc:  # noqa: BLE001 - a failed read is not an empty read (rule 8)
        raise Inconclusive(f"{PRODUCTS} could not be read ({type(exc).__name__})")
    if got.status_code != 200:
        raise Inconclusive(f"{PRODUCTS} answered HTTP {got.status_code}")
    try:
        products = got.json()["products"]
        with_visitors = [p for p in products if (p.get("visitors") or 0) > 0]
        off = disagreeing(products)
    except Exception as exc:  # noqa: BLE001
        raise Inconclusive(f"the body was not the JSON expected ({type(exc).__name__})")
    if not with_visitors:
        raise Inconclusive(f"no product on {PRODUCTS} has visitors")
    conclude(Measurement(
        verdict="failed" if off else "passed",
        reason=("; ".join(f"{r['name']}: the tile reads {r['visitors']} and its chart's days add up to "
                          f"{r['sum_of_daily']}" for r in off)
                or f"all {len(with_visitors)} products add up"),
        left={"disagreeing": len(off)},
        right={"disagreeing": 0},
        population={"products_with_visitors": len(with_visitors), "off": off},
        sources={"products": f"{PRODUCTS} products[].visitors, .daily",
                 "credential": "X-API-Key, trusted tier (value never recorded)"},
        claim_id=CLAIM))
