"""The Gem Screener agrees with itself where it has published the rule.

Five things it says about itself that any redesign has to keep true, because
the ranking, the picks and the altseason reading all stand on them:

1. **A Degen pick opens the coin it names.** `GET /api/v1/gem-screener/picks`
   lists each pick with its symbol and a link `?coin=<SYMBOL>`; the symbol route
   `GET /api/v1/gem-screener/coins/{symbol}` must answer that coin. On
   2026-09-30 it did not for one of eight: the pick "Definitive" (EDGE) linked to
   `?coin=EDGE`, and both the route and the page opened edgeX -- a different
   token, six times the market cap, which fails the very gates the pick passed.
   Four tickers are shared by two apps each (INDEX, MET, EDGE, UP), and the
   symbol route can answer only one of them. The contract-address request they
   have been given for the Chart Analyzer is the same idea.

2. **The upside is the benchmark's multiple over the coin's own.**
   `potential_raw = bench.mult / ps`, shown as `min(raw, cap)`, and the
   benchmark's multiple is its market cap over its run-rate revenue. All 215 rows
   held on 2026-09-30.

3. **The altseason numbers follow the rules the snapshot publishes**: the
   composite is the weighted mean of rotation and euphoria with the weights in
   `altseason_cycle.rules`; the headline breadth is the 4-week mean of the weekly
   history; `beat / n` is the latest reading.

4. **Every derived figure is a function of the figures beside it**: price/revenue,
   earnings after emissions, the 30x test, slippage, the Degen gates, a theme's
   edge over BTC, a chain's upside.

5. **The run-rate uses the multiplier its own page states.** It says x 12 on the
   30-day estimate; the code applies x 365 / 30 (2026-09-30: 45 of 45 rows, +1.4 %).

NOT asserted: that the formula is a good one (their own backtest says the rank
has no skill, and that is the audit's finding, not this check's), or that a pick
is worth buying. A field that cannot be read is INCONCLUSIVE, never agreement.

SAFE: GETs only, anonymous.
"""

from __future__ import annotations

import httpx

from qa import gemaudit as g
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_gem_screener_numbers_match_their_sources import get_patiently, read_page, read_snapshot


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_a_degen_pick_opens_the_coin_it_names(rest_anon):
    """Every pick's symbol, read through the coin route, is the same coin: the
    same name, and a market cap within 5 % (two reads, minutes apart)."""
    try:
        listed = get_patiently(rest_anon, g.PICKS)
        if listed.status_code != 200:
            raise Inconclusive(f"{g.PICKS} answered HTTP {listed.status_code}; a failed read "
                               f"is not an empty shortlist")
        try:
            picks = (listed.json() or {}).get("picks") or []
        except ValueError:
            raise Inconclusive(f"{g.PICKS} answered 200 with a body that is not JSON")
        if not picks:
            raise Inconclusive("the picks route listed no picks, so there is nothing to open")
        coins, unread = {}, []
        for pick in picks:
            symbol = pick.get("symbol")
            one = get_patiently(rest_anon, g.COIN.format(symbol=symbol))
            try:
                body = one.json() if one.status_code == 200 else None
            except ValueError:
                body = None
            if isinstance(body, dict):
                coins[symbol] = body
            else:
                unread.append(f"{symbol} (HTTP {one.status_code})")
    except httpx.HTTPError as exc:
        raise Inconclusive(f"the picks could not be read: {type(exc).__name__}")
    if unread:
        raise Inconclusive(f"a pick's coin could not be read, so nothing is concluded: {', '.join(unread)}")

    breaches = g.pick_identity_breaches(picks, coins)
    conclude(Measurement(
        verdict="failed" if breaches else "passed",
        reason=(f"{len(breaches)} of {len(picks)} Degen picks open another coin: " + "; ".join(
                    f"{b['row']} is {b['pick']!r} (market cap {b['pick_market_cap']:,.0f}) but its symbol "
                    f"opens {b['opens']!r} ({b['opens_market_cap']:,.0f})" for b in breaches)
                if breaches else
                f"all {len(picks)} Degen picks open the coin they name"),
        left={"picks": len(picks), "opening_another_coin": len(breaches)},
        right={"opening_another_coin": 0},
        population={"breaches": breaches, "symbols": [p.get("symbol") for p in picks]},
        sources={"picks": g.PICKS, "coin": g.COIN}))


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_the_upside_is_the_benchmarks_multiple_over_the_coins_own(rest_anon):
    """`potential_raw = bench.mult / ps`, `potential = min(raw, cap)`, and
    `bench.mult = bench.mcap / bench.rr`, on every row that has a `ps`."""
    snap = read_snapshot(rest_anon)
    try:
        said = g.upside_breaches(snap)
    except g.SnapshotUnreadable as exc:
        raise Inconclusive(str(exc))
    total = len(snap["apps"])
    if said["checked"] < 0.5 * total:
        raise Inconclusive(f"only {said['checked']} of {total} rows carry the fields the formula needs")
    bench = g.benchmark_arithmetic(snap)
    breaches = said["breaches"] + bench
    conclude(Measurement(
        verdict="failed" if breaches else "passed",
        reason=(f"{len(breaches)} breach(es) of the published upside formula in {said['checked']} rows: "
                + "; ".join(f"{b.get('row', 'benchmark')}: {b['what']}" for b in breaches[:5])
                if breaches else
                f"all {said['checked']} rows follow bench.mult / ps, capped at {said['cap']}; the benchmark's "
                f"multiple is its market cap over its run-rate"),
        left={"checked": said["checked"], "breaches": len(breaches), "cap": said["cap"]},
        right={"breaches": 0},
        population={"breaches": breaches[:10], "multiple": said["multiple"]},
        sources={"page": g.APP_PAGE}))


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_every_derived_figure_follows_its_published_definition(rest_anon):
    """Price/revenue, earnings after emissions, the 30x test, slippage, the Degen
    gates, a theme's edge over BTC and a chain's upside are each a function of
    other figures the snapshot publishes. Recomputed on every row that carries
    the inputs: a row where they disagree is a breach. (The level a coin opens
    with is held by the audit script, which reads one coin route per pick.)"""
    snap = read_snapshot(rest_anon)
    identities = g.derived_identities(snap)
    total = len(snap["apps"])
    thin = [i["name"] for i in identities if i["name"] in ("ps", "30x test", "degen gates")
            and i["checked"] < 0.5 * total]
    if thin:
        raise Inconclusive(f"too few of the {total} rows carry the inputs for: {', '.join(thin)}")
    breaches = [{"figure": i["name"], "rows": i["breaches"][:8], "count": len(i["breaches"])}
                for i in identities if i["breaches"]]
    conclude(Measurement(
        verdict="failed" if breaches else "passed",
        reason=("; ".join(f"{b['figure']}: {b['count']} row(s) disagree with their own inputs ({', '.join(map(str, b['rows'][:4]))})"
                          for b in breaches)
                if breaches else
                "; ".join(f"{i['name']} {i['checked']}" for i in identities) + " rows recomputed, none disagree"),
        left={"breaches": sum(b["count"] for b in breaches), "rows_read": sum(i["checked"] for i in identities)},
        right={"breaches": 0},
        population={"breaches": breaches, "identities": [{k: i[k] for k in ("name", "checked", "max_dev")}
                                                         for i in identities]},
        sources={"page": g.APP_PAGE}))


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_the_runrate_uses_the_multipliers_its_page_states(rest_anon):
    """The page says the run-rate is "last 30 days x 12" (or x 4 over 90); the
    value on a row whose basis is the 30-day estimate over its own 30-day revenue
    is the multiplier the code applies. On 2026-09-30 the page said 12 and the
    code applied 365 / 30 = 12.1667, on all 45 rows of that basis -- 1.4 % more
    than the stated definition, carried into price/revenue and the upside."""
    snap, text = read_page(rest_anon)
    stated = g.stated_runrate_factors(text)
    said = g.runrate_factor_breaches(snap, stated)
    if said["stated"] is None:
        raise Inconclusive("the page no longer words its 30-day multiplier as 'last 30 days x N', so there "
                           "is nothing stated to compare with")
    if said["checked"] < 10:
        raise Inconclusive(f"only {said['checked']} rows rest on the 30-day basis")
    breaches = said["breaches"]
    conclude(Measurement(
        verdict="failed" if breaches else "passed",
        reason=(f"the page states the 30-day run-rate as last 30 days x {said['stated']:g}; "
                f"{len(breaches)} of {said['checked']} rows apply x {sorted({b['applied'] for b in breaches})[0]:g} "
                f"({breaches[0]['row']}: applied {breaches[0]['applied']:g})"
                if breaches else
                f"all {said['checked']} rows on the 30-day basis apply the x {said['stated']:g} the page states"),
        left={"rows_off": len(breaches), "checked": said["checked"], "applied": sorted({b["applied"] for b in breaches})[:3]},
        right={"rows_off": 0, "stated": said["stated"]},
        population={"breaches": breaches[:10], "stated": stated},
        sources={"page": g.APP_PAGE}))


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_the_altseason_numbers_follow_their_own_published_rules(rest_anon):
    """The composite, the 4-week breadth mean and `beat / n`, each against the
    rule the snapshot itself publishes."""
    snap = read_snapshot(rest_anon)
    said = g.altseason_breaches(snap)
    if said["unread"]:
        raise Inconclusive("the altseason block could not be read whole: " + "; ".join(said["unread"]))
    breaches = said["breaches"]
    cyc = snap.get("altseason_cycle") or {}
    conclude(Measurement(
        verdict="failed" if breaches else "passed",
        reason=("; ".join(f"{b['what']} ({ {k: v for k, v in b.items() if k != 'what'} })" for b in breaches)
                if breaches else
                f"the composite {cyc.get('index')}, the breadth mean and beat/n all follow the published rules"),
        left={"breaches": len(breaches), "index": cyc.get("index")},
        right={"breaches": 0},
        population={"breaches": breaches},
        sources={"page": g.APP_PAGE, "cycle": "altseason_cycle"}))
