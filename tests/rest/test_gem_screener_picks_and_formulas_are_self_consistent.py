"""The Gem Screener agrees with itself where it has published the rule.

Six things it says about itself that any redesign has to keep true, because
the ranking, the picks and the altseason reading all stand on them:

1. **A Degen pick opens the coin it names.** `GET /api/v1/gem-screener/picks`
   lists each pick with its symbol and a link (`detail_url`, `?coin=<key>`);
   the coin route `GET /api/v1/gem-screener/coins/{key}` must answer that coin
   for the key the link carries -- since their fix of #140 (2026-10-01) a slug,
   before it the symbol. On
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

6. **A run-rate states only the days its revenue has.** `runrate.cov30` is
   held to the row's own daily series (2026-10-10: KNC 30 of 30 stated, 19 held).

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
from tests.rest.test_gem_screener_panels_say_what_their_data_says import read_api


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_a_degen_pick_opens_the_coin_it_names(rest_anon):
    """Every pick's link, read through the coin route, is the same coin: the
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
            # What the pick's own link opens (#140, fixed 2026-10-01 by
            # linking by slug), not the ticker two apps may share.
            symbol = g.pick_key(pick)
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
                    f"{b['row']} is {b['pick']!r} (market cap {b['pick_market_cap']:,.0f}) but its link "
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
    try:
        # C06, deep pass of 2026-09-30: an unreadable benchmark field is not a
        # broken formula -- the same colour as a missing multiple above.
        bench = g.benchmark_arithmetic(snap)
    except g.SnapshotUnreadable as exc:
        raise Inconclusive(str(exc))
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
    """Price/revenue, the market cap (price x circulating supply), earnings after
    emissions, the 30x test, slippage, the Degen gates, a theme's edge over BTC
    and a chain's upside are each a function of
    other figures the snapshot publishes. Recomputed on every row that carries
    the inputs: a row where they disagree is a breach. (The level a coin opens
    with is held by the audit script, which reads one coin route per pick.)"""
    snap = read_snapshot(rest_anon)
    identities = g.derived_identities(snap)
    total = len(snap["apps"])
    # R02/C05, deep pass of 2026-09-30: every figure must have been recomputed
    # on some rows -- a figure read on none is unread, never agreement.
    verdict, why = g.identities_verdict(identities, total)
    if verdict == "inconclusive":
        raise Inconclusive(why)
    breaches = [{"figure": i["name"], "rows": i["breaches"][:8], "count": len(i["breaches"])}
                for i in identities if i["breaches"]]
    conclude(Measurement(
        verdict=verdict,
        reason=why,
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
def test_a_runrate_states_only_the_days_its_revenue_has(rest_anon):
    """`runrate.cov30` names how many of the last 30 days a row's revenue rests
    on; its own `rev_series` holds the days. On 2026-10-10 KNC said 30 with 11
    absent (between 12 and 24 September, absent from DeFiLlama too) and `sparse` false, so
    the 30-day sum, the run-rate and price/revenue counted them as zero.
    ET-28597 item 5, asked 2026-09-30 and not explained since. The series is in
    the snapshot API only; the page's embedded copy leaves it out."""
    snap = read_api(rest_anon, g.SNAPSHOT_API, dated=True)
    said = g.coverage_breaches(snap)
    if said["checked"] < 10:
        raise Inconclusive(f"only {said['checked']} rows state a 30-day coverage beside a revenue series")
    breaches = said["breaches"]
    conclude(Measurement(
        verdict="failed" if breaches else "passed",
        reason=(f"{len(breaches)} of {said['checked']} rows state more days of revenue in the last 30 than their "
                f"own daily series holds, and count the absent days as zero: "
                + "; ".join(f"{b['row']} cov30 {b['cov30']:g} with {b['present']} days present "
                            f"(run-rate basis {b['basis']}, sparse {b['sparse']})" for b in breaches[:5])
                if breaches else
                f"all {said['checked']} rows state no more days than their revenue series holds"),
        left={"rows_overstating": len(breaches), "checked": said["checked"]},
        right={"rows_overstating": 0},
        population={"breaches": breaches[:10], "generated_at": snap.get("generated_at")},
        sources={"api": g.SNAPSHOT_API}))


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_the_dilution_caution_band_lies_below_the_red_band(rest_anon):
    """`dilution_meta` states `caution_line` and `red_line` in % of market cap a week; the page
    says "Caution above 1.5% a week, red above 1%". A caution line at or above the red line
    leaves "caution" empty: a coin passes red first. 2026-10-10: 1.5253 against 1.0, 0 of 233
    apps at caution (10 at ET-28821 on 2026-10-02), 19 at red."""
    snap = read_api(rest_anon, g.SNAPSHOT_API, dated=True)
    meta = snap.get("dilution_meta")
    if not isinstance(meta, dict) or meta.get("caution_line") is None or meta.get("red_line") is None:
        raise Inconclusive("the snapshot states no caution_line and red_line")
    seen = g.dilution_band_breach(meta)
    conclude(Measurement(
        verdict="failed" if seen else "passed",
        reason=(f"dilution_meta puts the caution line at {seen['caution_line']:g}% a week and the red line at "
                f"{seen['red_line']:g}%: a coin over {seen['red_line']:g}% is red before it can be caution, "
                f"so {seen['caution_n']} apps read caution and {seen['red_n']} read red"
                if seen else
                f"caution starts at {meta['caution_line']:g}% a week, below the red line at {meta['red_line']:g}%"),
        left={"caution_line": meta.get("caution_line"), "red_line": meta.get("red_line")},
        right={"caution_below_red": True},
        population={"dilution_meta": {k: meta.get(k) for k in ("caution_line", "red_line", "gate_pct", "caution_pts",
                                                               "red_pts", "bench_week_pct", "levels")},
                    "generated_at": snap.get("generated_at")},
        sources={"api": g.SNAPSHOT_API}))


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_every_gem_screener_route_llms_txt_names_is_in_the_openapi(rest_anon):
    """llms.txt names `GET /api/v1/gem-screener/report-access`; /openapi-public.json, which
    /api-docs is built from, does not describe it. Their reply of 2026-10-10 (ET-28821 point 4)
    says it is "in both"."""
    pages = {}
    for path in ("/llms.txt", "/openapi-public.json"):
        response = get_patiently(rest_anon, path)
        if response.status_code != 200:
            raise Inconclusive(f"{path} answered HTTP {response.status_code}; a failed read is not an empty document")
        pages[path] = response
    try:
        spec = pages["/openapi-public.json"].json()
    except ValueError:
        raise Inconclusive("/openapi-public.json is not JSON")
    if not isinstance(spec, dict) or not spec.get("paths"):
        raise Inconclusive("/openapi-public.json carries no paths")
    missing = g.paths_missing_from_openapi(pages["/llms.txt"].text, spec)
    conclude(Measurement(
        verdict="failed" if missing else "passed",
        reason=(f"/llms.txt names {len(missing)} Gem Screener route(s) that /openapi-public.json does not "
                f"describe: {', '.join(missing)}" if missing else
                "every /api/v1/gem-screener route /llms.txt names is in /openapi-public.json"),
        left={"routes_missing_from_openapi": len(missing)},
        right={"routes_missing_from_openapi": 0},
        population={"missing": missing},
        sources={"llms": "/llms.txt", "openapi": "/openapi-public.json"}))


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_the_altseason_numbers_follow_their_own_published_rules(rest_anon):
    """The composite, the 4-week breadth mean and `beat / n`, each against the
    rule the snapshot itself publishes.

    Read from the API snapshot, not the page's embedded copy: the page trims
    `altseason_cycle.series` (the weekly history the mean is taken over), the API
    carries it (checked 2026-10-04)."""
    try:
        response = get_patiently(rest_anon, g.SNAPSHOT_API)
    except httpx.HTTPError as exc:
        raise Inconclusive(f"{g.SNAPSHOT_API} could not be read: {type(exc).__name__}")
    if response.status_code != 200:
        raise Inconclusive(f"{g.SNAPSHOT_API} answered HTTP {response.status_code}; a failed "
                           f"read is not an empty snapshot")
    try:
        snap = response.json()
    except ValueError:
        raise Inconclusive(f"{g.SNAPSHOT_API} answered 200 with a body that is not JSON")
    if not isinstance(snap, dict):
        raise Inconclusive(f"{g.SNAPSHOT_API} answered a {type(snap).__name__}, not an object")
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
        sources={"api": g.SNAPSHOT_API, "cycle": "altseason_cycle"}))
