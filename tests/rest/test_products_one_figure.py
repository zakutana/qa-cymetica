"""After ET-33672: "one definition everywhere" for a product's people, and where it does not hold yet (2026-11-02).

Their fix defines Unique visitors as "Distinct people who used the product in the period", and says so on all
three pages: `/api/v1/app-usage` -> `definitions.users` says "The Products tab of /company and /traffic/mine
show this same figure for a product", and the Products tab says "the same figure as on /app-usage and
/traffic/mine". Read 2026-11-02 at 07:12 UTC, 30 days, four things do not fit that:

1. /traffic/mine: Build a Company 96 against 130, Airdrop Farmer 26 against 23, neither with Uses.
2. A product given another's people: Supply Analyzer and Gem Screener have the same 30 daily figures and the
   same 195; Team Dump Radar reads 433, the figure of the group "Crypto Radars", on 31 page views.
3. /traffic/mine: the tile Unique visitors is below a row under it (14 days: 214 against Team Dump Radar's 338).
4. Infiltrator: 0 people and 18 uses, while a use is a page load in which a visitor clicked.

**The rules**, each passing on either fix a vendor could pick:
1. While /app-usage promises the same figure, a product's row on /traffic/mine carries it, within SAME, and its
   uses. Passed also when the promise is gone.
2. No two products share a daily list with DISTINCT_DAYS or more active days; no product carries, under its own
   name, the figure of a differently named /app-usage row on its path when that is over MARGIN times the page
   views of its row. Passed when the counts part, or when the product takes the group's name.
3. No row's Unique is over the tile by more than SAME. Passed when the tile is recounted or the column is the
   page's own count again.
4. No product has uses and no people. Passed when the people are counted or the uses go.

Inconclusive: a failed read, an unexpected body, nothing to compare.
NOT asserted: which count is right. SAFE: GETs only; the key is sent in the header and never recorded.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

PRODUCTS = "/api/v1/company/products"
USAGE = "/api/v1/app-usage"
MINE_30 = "/api/v1/traffic/mine?days=30"
MINE_14 = "/api/v1/traffic/mine?days=14"
SAME = 2
SAME_SHARE = 0.05
DISTINCT_DAYS = 5
MARGIN = 2


def same_figure(a: int, b: int) -> bool:
    """The endpoints are cached minutes apart; a near miss is not the claim."""
    return abs(a - b) <= max(SAME, SAME_SHARE * max(a, b))


def row_for(path: str, items: list[dict]) -> dict | None:
    """A product's own row on /traffic/mine: the app row, or the shipped page. A feature request is another page."""
    rows = [r for r in items if r.get("path") == path and r.get("kind") in ("app", "feature_page")]
    return next((r for r in rows if r.get("kind") == "app"), rows[0] if rows else None)


def three_pages(products: list[dict], items: list[dict], usage_definition: str) -> tuple[str | None, str, list]:
    """Rule 1."""
    if "/traffic/mine" not in (usage_definition or ""):
        return "passed", "/app-usage no longer promises the same figure on /traffic/mine", []
    compared, off = [], []
    for product in products:
        row = row_for(product.get("path"), items)
        if row is None:
            continue
        beacon = row.get("app_beacon") or {}
        people = beacon.get("visitors") if "visitors" in beacon else row.get("unique_visitors")
        entry = {"name": product.get("name"), "products_tab": product["unique_visitors"], "traffic_mine": people,
                 "uses_products_tab": product.get("uses"), "uses_traffic_mine": beacon.get("uses")}
        compared.append(entry)
        if not same_figure(product["unique_visitors"], people) or ((product.get("uses") or 0) > 0 and "uses" not in beacon):
            off.append(entry)
    if not compared:
        return None, "no product has a row on /traffic/mine", compared
    if off:
        return "failed", "; ".join(f"{e['name']}: {e['products_tab']} unique visitors and {e['uses_products_tab']} uses "
                                   f"on the Products tab, {e['traffic_mine']} and {e['uses_traffic_mine']} on /traffic/mine"
                                   for e in off), compared
    return "passed", f"all {len(compared)} products read the same on both pages", compared


def anothers_people(products: list[dict], items: list[dict], humans: list[dict]) -> tuple[str | None, str, list]:
    """Rule 2."""
    if not products:
        return None, "no products", []
    off = []
    for i, a in enumerate(products):
        days = a.get("daily") or []
        if sum(1 for d in days if d) < DISTINCT_DAYS:
            continue
        off += [{"name": a["name"], "same_days_as": b["name"], "people": a["unique_visitors"]}
                for b in products[i + 1:] if b.get("path") != a.get("path") and b.get("daily") == days]
    for product in products:
        row, listed = row_for(product.get("path"), items), next(
            (h for h in humans if h.get("path") == product.get("path")), None)
        if row and listed and listed.get("app") != product.get("name") and listed.get("users") == product["unique_visitors"] \
                and product["unique_visitors"] > MARGIN * (row.get("visits") or 0):
            off.append({"name": product["name"], "figure_of": listed["app"], "people": product["unique_visitors"],
                        "page_views": row.get("visits")})
    if off:
        return "failed", "; ".join(
            f"{e['name']} has the same daily figures as {e['same_days_as']} ({e['people']} people)" if "same_days_as" in e
            else f"{e['name']} reads {e['people']}, the figure of \"{e['figure_of']}\" on /app-usage, on {e['page_views']} page views"
            for e in off), off
    return "passed", "every product has its own people", off


def row_over_tile(mine: dict) -> tuple[str | None, str, list]:
    """Rule 3."""
    tile = (mine.get("totals") or {}).get("unique_visitors")
    rows = [r for r in mine.get("items") or [] if isinstance(r.get("unique_visitors"), int)]
    if not isinstance(tile, int) or not rows:
        return None, "no tile or no rows", []
    over = [{"label": r.get("label"), "unique": r["unique_visitors"], "page_views": r.get("visits")}
            for r in rows if r["unique_visitors"] > tile + SAME]
    if over:
        return "failed", (f"the tile Unique visitors reads {tile:,} and rows under it read more: "
                          + ", ".join(f"{e['label']} {e['unique']:,}" for e in over)), over
    return "passed", f"no row is over the tile ({tile:,})", over


def uses_without_people(products: list[dict]) -> tuple[str | None, str, list]:
    """Rule 4."""
    with_uses = [p for p in products if (p.get("uses") or 0) > 0]
    if not with_uses:
        return None, "no product has uses", []
    off = [{"name": p["name"], "uses": p["uses"], "unique_visitors": p["unique_visitors"]}
           for p in with_uses if not p.get("unique_visitors")]
    if off:
        return "failed", "; ".join(f"{e['name']}: {e['uses']} uses by 0 unique visitors" for e in off), off
    return "passed", f"all {len(with_uses)} products with uses have people", off


def _body(client, url: str) -> dict:
    try:
        got = client.get(url)
        if got.status_code != 200:
            raise Inconclusive(f"{url} answered HTTP {got.status_code}")
        return got.json()
    except Inconclusive:
        raise
    except Exception as exc:  # noqa: BLE001 - a failed read is not an empty read
        raise Inconclusive(f"{url} could not be read ({type(exc).__name__})")


def _conclude(claim: str, judged: tuple[str | None, str, list], sources: dict) -> None:
    verdict, why, rows = judged
    if verdict is None:
        raise Inconclusive(why)
    conclude(Measurement(verdict=verdict, reason=why, left={"off": len(rows) if verdict == "failed" else 0},
                         right={"off": 0}, population={"rows": rows}, sources=sources, claim_id=claim))


def _products(client) -> list[dict]:
    body = _body(client, PRODUCTS)
    try:
        return [p for p in body["products"] if isinstance(p["unique_visitors"], int)]
    except (KeyError, TypeError) as exc:
        raise Inconclusive(f"{PRODUCTS} has no unique_visitors ({type(exc).__name__})")


@qa(component="rest.company", tier=SafetyTier.SAFE, surface="rest", claim="products-traffic-mine-same-figure")
def test_traffic_mine_carries_the_products_figure(rest_anon, rest_trusted):
    """Rule 1, over 30 days."""
    products, mine, usage = _products(rest_trusted), _body(rest_trusted, MINE_30), _body(rest_anon, USAGE)
    _conclude("products-traffic-mine-same-figure",
              three_pages(products, mine.get("items") or [], (usage.get("definitions") or {}).get("users") or ""),
              {"products": PRODUCTS, "mine": MINE_30, "promise": f"{USAGE} definitions.users"})


@qa(component="rest.company", tier=SafetyTier.SAFE, surface="rest", claim="products-have-their-own-people")
def test_a_product_has_its_own_people(rest_anon, rest_trusted):
    """Rule 2, over 30 days."""
    products, mine, usage = _products(rest_trusted), _body(rest_trusted, MINE_30), _body(rest_anon, USAGE)
    _conclude("products-have-their-own-people", anothers_people(products, mine.get("items") or [], usage.get("humans") or []),
              {"products": PRODUCTS, "mine": MINE_30, "usage": f"{USAGE} humans[]"})


@qa(component="rest.traffic", tier=SafetyTier.SAFE, surface="rest", claim="traffic-mine-no-row-over-the-tile")
def test_no_row_is_over_the_unique_visitors_tile(rest_trusted):
    """Rule 3, over the 14 days the page opens on."""
    _conclude("traffic-mine-no-row-over-the-tile", row_over_tile(_body(rest_trusted, MINE_14)),
              {"mine": f"{MINE_14} totals.unique_visitors, items[].unique_visitors"})


@qa(component="rest.company", tier=SafetyTier.SAFE, surface="rest", claim="products-no-uses-without-people")
def test_no_product_has_uses_and_no_people(rest_trusted):
    """Rule 4."""
    _conclude("products-no-uses-without-people", uses_without_people(_products(rest_trusted)),
              {"products": f"{PRODUCTS} products[].uses, .unique_visitors"})
