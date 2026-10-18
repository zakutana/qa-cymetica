"""The VAIX orderbook's arbitrage leg is not a venue the same response excluded (2026-10-13, T-0053).

`GET /api/v1/vaix/orderbook` is a new shape since 2026-10-12: beside the merged ladder it carries
`excluded_venues` -- the chains whose mid price diverged from the reference and so were left out of
the book, each with `mid`, `divergence_pct` and `reason: "price_divergence"` -- and `arbitrage`, a
buy leg, a sell leg and a `potential_profit_pct`.

**What was seen when this was written** (2026-10-12 22:32 UTC, anonymous): `excluded_venues` named
base (mid 0.00031077, -83.75 %), arbitrum (-54.91 %) and solana (-80.54 %), each `price_divergence`;
`arbitrage` read `buy_chain: base`, `buy_price: 0.00031077`, `sell_chain: ethereum`,
`potential_profit_pct: 514.48`. The buy leg is the same figure, from the same chain, that the line
above calls a divergence from the reference price. Base held $164 of liquidity, arbitrum $13 and
solana $7 against ethereum's $25,128, all of it from their own `chains`.

**The rule.** An `arbitrage` whose buy or sell chain is a key of `excluded_venues` offers a price
the response itself withheld from its book. NOT asserted: that `arbitrage` must be computed from
the book's venues only (it may be meant as a signal over all chains), the size of
`potential_profit_pct`, or the liquidity figures -- the route is in llms.txt as one line and in
neither `openapi-public.json` nor `/api-docs`, so what either block means is undocumented and that is
said in the report as a question, not an accusation. The check fails only when two reads, a pause
apart, both show the overlap (a rotating venue is sampling); passes when `arbitrage` is absent or
neither leg is excluded; is inconclusive when the book cannot be read.

If Cymetica publishes that `arbitrage` ranges over excluded venues on purpose, this check is
retired by an event.

SAFE: GETs, anonymous.
"""

from __future__ import annotations

import time

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

BOOK = "/api/v1/vaix/orderbook"
CLAIM = "vaix-orderbook-arbitrage-does-not-use-an-excluded-venue"
SECOND_LOOK_S = 30.0


def excluded_legs(orderbook) -> dict | None:
    """The arbitrage legs that sit on a venue the same book excluded, with that venue's own words.

    None when the book is unreadable (not a dict, `arbitrage` or `excluded_venues` of the wrong
    shape); {} when it reads and no leg is excluded."""
    if not isinstance(orderbook, dict):
        return None
    arb, excluded = orderbook.get("arbitrage"), orderbook.get("excluded_venues")
    if arb is not None and not isinstance(arb, dict):
        return None
    if excluded is not None and not isinstance(excluded, dict):
        return None
    if not arb or not excluded:
        return {}
    found = {}
    for leg in ("buy_chain", "sell_chain"):
        chain = arb.get(leg)
        if isinstance(chain, str) and chain in excluded:
            venue = excluded[chain] if isinstance(excluded[chain], dict) else {}
            found[leg] = {"chain": chain, "price": arb.get(leg.replace("_chain", "_price")),
                          "excluded_mid": venue.get("mid"), "divergence_pct": venue.get("divergence_pct"),
                          "reason": venue.get("reason")}
    if not found and not all(isinstance(arb.get(leg), str) for leg in ("buy_chain", "sell_chain")):
        # A leg not where this check reads it is unread, so the book is not clean (B08; one leg
        # renamed, B05 2026-10-18). An excluded leg the other one shows is still named.
        return None
    return found


def _read(rest_anon) -> dict:
    response = rest_anon.get(BOOK)
    if response.status_code != 200:
        raise Inconclusive(f"{BOOK} answered HTTP {response.status_code}")
    body = response.json()
    book = body.get("orderbook") if isinstance(body, dict) else None
    legs = excluded_legs(book)
    if legs is None:
        raise Inconclusive(f"{BOOK} no longer carries `orderbook.arbitrage` / `excluded_venues` "
                           "in a shape this check reads")
    return {"timestamp": book.get("timestamp"), "legs": legs,
            "arbitrage": book.get("arbitrage"),
            "excluded": sorted((book.get("excluded_venues") or {}))}


@qa(component="rest.markets", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_the_vaix_orderbook_arbitrage_does_not_use_an_excluded_venue(rest_anon):
    """arbitrage.buy_chain / sell_chain against excluded_venues, on two reads."""
    first = _read(rest_anon)
    time.sleep(SECOND_LOOK_S)
    second = _read(rest_anon)
    both = sorted(set(first["legs"]) & set(second["legs"]))
    failed = bool(both)
    seen = second if second["legs"] else first
    named = "; ".join(
        f"{leg}: {seen['legs'][leg]['chain']} at {seen['legs'][leg]['price']} while excluded_venues says "
        f"mid {seen['legs'][leg]['excluded_mid']}, {seen['legs'][leg]['divergence_pct']} % from the reference "
        f"({seen['legs'][leg]['reason']})" for leg in both) if failed else ""
    conclude(Measurement(
        verdict="failed" if failed else "passed",
        reason=(f"the VAIX orderbook's arbitrage uses a venue its own excluded_venues withheld, on both "
                f"reads ({first['timestamp']}, {second['timestamp']}): {named}; "
                f"potential_profit_pct {seen['arbitrage'].get('potential_profit_pct')}" if failed else
                f"no arbitrage leg sat on an excluded venue (reads {first['timestamp']}, "
                f"{second['timestamp']}; excluded {second['excluded']}, "
                f"legs {(second['arbitrage'] or {}).get('buy_chain')}/{(second['arbitrage'] or {}).get('sell_chain')})"),
        left={"arbitrage_legs_on_an_excluded_venue": len(both)},
        right={"arbitrage_legs_on_an_excluded_venue": 0},
        population={"reads": [first, second]},
        sources={"book": f"{BOOK} orderbook.arbitrage.buy_chain / sell_chain, orderbook.excluded_venues"},
        claim_id=CLAIM))
