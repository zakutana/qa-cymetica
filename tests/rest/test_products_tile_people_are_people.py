"""The Products tab says "people" over a figure that counts one person once per day (2026-11-01).

The Products tab of /company draws a tile per product (`static/company/app.js`, read 2026-11-01):

    (+a.visitors || 0).toLocaleString('en-US') + '</b><span>people</span></div>'

and `a` comes from `GET /api/v1/company/products`, where Gem Screener read `visitors` 247 with a
30-day `daily` list that adds up to exactly 247. Their own definition of that figure is on
`GET /api/v1/build-it-better/apps/leaderboard`, `definitions.visitors`: "Distinct daily visitors.
A range is the sum of its days, so one person on three days counts three times." The same 247 is
"Visitors" on /build-it-better. /traffic/mine, signed in, read 162 unique visitors for the same
app over the same 30 days. So the word on the tile is not what the number counts.

**The rule.** A tile labelled "people" counts people. Either fix passes, and both are written here
on day one: the label stops saying people (say "visitors" or "visits"), or the field stops being
a sum of its days (their definition no longer says so and the rows stop adding up).

VERDICTS. failed: the tile's label is "people", the definition says a range is the sum of its days,
and at least one product with visitors reads visitors == sum(daily). passed: the label says something
else; or the label is "people", the definition no longer says sum and no such row exists.
inconclusive: any read failed or the anchors are gone; the tile is not found; no row has visitors;
the two readings disagree (the definition says one thing and the rows another).

NOT asserted: which distinct count is right (/traffic/mine's and /app-usage's differ and neither page
says why), or the season points.
SAFE: three GETs; the key is sent by the client in the header and never printed or recorded.
"""

from __future__ import annotations

import re

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

CLAIM = "products-tile-people-are-people"
SCRIPT = "/static/company/app.js"
PRODUCTS = "/api/v1/company/products"
BOARD = "/api/v1/build-it-better/apps/leaderboard"

# Anchored on their own markup: the tile's number and the <span> right after it.
TILE = re.compile(r"\(\+a\.visitors\s*\|\|\s*0\)\.toLocaleString\([^)]*\)\s*\+\s*'</b><span>([^<]+)</span>")
SUM_OF_DAYS = re.compile(r"sum of its days", re.I)


def adding_up(products: list[dict]) -> list[dict]:
    """The products with visitors whose figure is exactly the sum of their daily list."""
    return [p for p in products
            if (p.get("visitors") or 0) > 0 and isinstance(p.get("daily"), list)
            and sum(p["daily"]) == p["visitors"]]


def verdict_for(label: str, says_sum: bool, with_visitors: int, adding: int) -> str:
    """failed / passed / inconclusive from the three readings."""
    if label.strip().lower() != "people":
        return "passed"
    if not with_visitors:
        return "inconclusive"
    if says_sum and adding:
        return "failed"
    if not says_sum and not adding:
        return "passed"
    return "inconclusive"


@qa(component="rest.company", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_products_tile_people_are_people(rest_anon, rest_trusted):
    """The tile's label, their definition of the figure, and the rows themselves."""
    try:
        script = rest_anon.get(SCRIPT)
        board = rest_anon.get(BOARD)
        got = rest_trusted.get(PRODUCTS)
    except Exception as exc:  # noqa: BLE001 - a failed read is not an empty read (rule 8)
        raise Inconclusive(f"a read failed ({type(exc).__name__})")
    for name, resp in ((SCRIPT, script), (BOARD, board), (PRODUCTS, got)):
        if resp.status_code != 200:
            raise Inconclusive(f"{name} answered HTTP {resp.status_code}")
    tile = TILE.search(script.text)
    if not tile:
        raise Inconclusive(f"{SCRIPT} no longer draws the tile as (+a.visitors || 0) + <span>label</span>")
    try:
        definition = (board.json().get("definitions") or {}).get("visitors")
        products = got.json().get("products")
    except Exception as exc:  # noqa: BLE001
        raise Inconclusive(f"a body was not the JSON expected ({type(exc).__name__})")
    if not isinstance(definition, str) or not isinstance(products, list):
        raise Inconclusive(f"{BOARD} definitions.visitors or {PRODUCTS} products is missing")
    label = tile.group(1)
    says_sum = bool(SUM_OF_DAYS.search(definition))
    with_visitors = [p for p in products if (p.get("visitors") or 0) > 0]
    adding = adding_up(products)
    verdict = verdict_for(label, says_sum, len(with_visitors), len(adding))
    if verdict == "inconclusive":
        raise Inconclusive(f"label {label!r}, definition says sum: {says_sum}, {len(with_visitors)} products "
                           f"with visitors, {len(adding)} adding up to their days: nothing to judge")
    top = max(adding, key=lambda p: p["visitors"]) if adding else None
    conclude(Measurement(
        verdict=verdict,
        reason=(f"The Products tab labels a.visitors \"{label}\", but {BOARD} defines the figure: "
                f"\"{definition}\" {len(adding)} of {len(with_visitors)} products read visitors == sum(daily), "
                f"e.g. {top['name']}: {top['visitors']}, so one person on three days is three \"people\""
                if verdict == "failed" else
                f"The tile reads \"{label}\" over a figure defined as: \"{definition}\""),
        left={"label": label, "says_sum_of_days": says_sum, "rows_adding_up": len(adding)},
        right={"label": "not people, or a distinct count"},
        population={"products_with_visitors": len(with_visitors),
                    "largest": {"name": top["name"], "visitors": top["visitors"],
                                "days": len(top["daily"])} if top else None},
        sources={"tile": f"{SCRIPT} (the number and the <span> after it)",
                 "definition": f"{BOARD} definitions.visitors",
                 "rows": f"{PRODUCTS} products[].visitors, .daily",
                 "credential": "X-API-Key, trusted tier (value never recorded)"},
        claim_id=CLAIM))
