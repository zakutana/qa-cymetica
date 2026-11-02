"""What the Gem Screener states is true of the coin it states it about.

The operator's bar, 2026-11-02: if the app got famous tomorrow there must be no
false information on it. The numbers are held by
test_gem_screener_numbers_match_their_sources.py; these checks hold the words: a
label, a window, a reason, a denial. A false label on a correct number counts.

Each check names the property a reader relies on and goes green on any fix that
gives it: a sentence reworded, a figure recomputed, a row dropped. None of them
wants a particular wording, and where a sentence can go, its going is a pass.

NOT asserted: that the gates are the right gates, that a pick is worth buying, or
anything about how the page looks. Degen report lines are cached for up to a week
and say so (`lines_as_of`), so a fix to a report sentence reaches them within days.

SAFE: GETs only, anonymous; third parties through `build_source_client`.
"""

from __future__ import annotations

import json
import re

import httpx

from qa import gemaudit as g
from qa.client import build_source_client
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_gem_screener_numbers_match_their_sources import get_patiently, read_page

YEAR_S = 365 * 86400
# An app DefiLlama's hacks list names without the suffix the app's own record has.
HACK_NAME = {"osmosis-dex": "Osmosis"}
THREE_PCT_POOL_USD = 2 * 10_000 * 100 / 3  # the page's own formula: impact = 2 x ticket / pool


def _json(client, url: str) -> dict:
    response = get_patiently(client, url)
    if response.status_code != 200:
        raise Inconclusive(f"{url} answered HTTP {response.status_code}; a failed read is not an empty one")
    try:
        return response.json()
    except ValueError:
        raise Inconclusive(f"{url} answered 200 with a body that is not JSON")


def _source_json(client, url: str):
    try:
        response = client.get(url)
    except httpx.HTTPError as exc:
        raise Inconclusive(f"{url} could not be read: {type(exc).__name__}")
    if response.status_code != 200:
        raise Inconclusive(f"{url} answered HTTP {response.status_code}")
    return response.json()


def _coin(client, slug: str) -> dict:
    return _json(client, g.COIN.format(symbol=slug))


def _report_text(client, slug: str) -> str:
    return json.dumps(_json(client, g.COIN.format(symbol=slug) + "/degen-report"), ensure_ascii=False)


def _gate(snap: dict, gate_id: str) -> str:
    for gate in (snap.get("degen_gates") or {}).get("gates") or []:
        if gate.get("id") == gate_id:
            return gate.get("rule_long") or ""
    raise Inconclusive(f"the snapshot has no gate {gate_id!r}")


def _check(coin: dict, check_id: str) -> dict:
    for check in (coin.get("degen_level") or {}).get("checks") or []:
        if check.get("id") == check_id:
            return check
    return {}


def _norm(name) -> str:
    return re.sub(r"[^a-z0-9]", "", str(name or "").lower())


def _verdict(breaches: list, checked, passed: str, sources: dict | None = None) -> None:
    conclude(Measurement(
        verdict="failed" if breaches else "passed",
        reason=("; ".join(str(b.get("what", b)) for b in breaches[:8]) if breaches else passed),
        left={"breaches": len(breaches), "checked": checked},
        right={"breaches": 0},
        population={"breaches": breaches[:20]},
        sources=sources or {"page": g.APP_PAGE}))


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_an_exploit_listed_under_the_apps_own_name_is_not_denied(rest_anon):
    """DefiLlama's hacks list names this very app, and the page must not say the
    exploit is not tied to it, that none is listed, or that it is old when one is
    under a year old. 'Listed, not verified' would pass."""
    snap, _ = read_page(rest_anon)
    source = build_source_client()
    try:
        hacks = _source_json(source, "https://api.llama.fi/hacks")
    finally:
        source.close()
    named: dict[str, list] = {}
    for hack in hacks:
        named.setdefault(_norm(hack.get("name")), []).append(hack)
    now = snap.get("generated_at") or 0
    breaches, checked = [], 0
    for app in snap["apps"]:
        own = named.get(_norm(HACK_NAME.get(app.get("slug")) or app.get("name")))
        if not own:
            continue
        checked += 1
        track = _check(_coin(rest_anon, app["slug"]), "track_record")
        report = _report_text(rest_anon, app["slug"])
        dates = [h.get("date") for h in own if h.get("date")]
        recent = [d for d in dates if now - d < YEAR_S]
        said = None
        if "not tied to this protocol" in report:
            said = "the report says the exploit is not tied to this protocol"
        elif track.get("text") == "No exploit listed":
            said = "the check reads 'No exploit listed'"
        elif recent and track.get("text") == "Old exploit":
            said = "the check reads 'Old exploit' though one is under a year old"
        if said:
            breaches.append({"what": f"{app['symbol']} ({app['slug']}): {said}; DefiLlama lists "
                                     + ", ".join(f"{h.get('name')} ${h.get('amount') or 0:,.0f}" for h in own),
                             "pick": bool(app.get("degen_ok"))})
    if not checked:
        raise Inconclusive("no app's own name is on DefiLlama's hacks list, so nothing could be compared")
    _verdict(breaches, checked, f"none of the {checked} apps named on DefiLlama's hacks list has it denied",
             {"page": g.APP_PAGE, "hacks": "https://api.llama.fi/hacks"})


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_the_picks_route_says_when_it_lists_fewer_than_pass(rest_anon):
    """`/picks` says 'apps passing all 6 degen gates'. Listing fewer is fine if it
    says so: all that pass, or a statement of how many pass, is a pass."""
    snap, _ = read_page(rest_anon)
    body = _json(rest_anon, g.PICKS)
    picks = body.get("picks") or []
    passing = sum(1 for a in snap["apps"] if a.get("degen_ok"))
    listed = {p.get("slug") for p in picks}
    left_out = [a["slug"] for a in snap["apps"] if a.get("degen_ok") and a.get("slug") not in listed]
    says = any(v == passing for v in body.values() if isinstance(v, int)) or bool(
        re.search(rf"\b(top|first|up to|at most|highest)\b[^.]*\b{len(picks)}\b|\b{len(picks)} of\b", str(body.get("what") or ""), re.I))
    breaches = []
    if len(picks) != passing and not says:
        breaches.append({"what": f"{passing} apps pass all 6 gates, /picks lists {len(picks)} and does not say so; "
                                 f"left out: {left_out}"})
    _verdict(breaches, passing, f"/picks lists {len(picks)} of {passing} and says what it lists",
             {"picks": g.PICKS, "page": g.APP_PAGE})


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_each_gate_prints_what_decides_it(rest_anon):
    """A row the printed rule passes and the gate fails is a rule not printed. Three
    of them, each cleared by the row's going or by the text saying what decides it."""
    snap, _ = read_page(rest_anon)
    rules = (snap.get("degen") or {}).get("rules") or {}
    vetted = rules.get("vetted") or {}
    tiers = sorted(rules.get("biz_tiers") or [], key=lambda t: -t.get("min_rev30", 0))
    if not vetted or not tiers:
        raise Inconclusive("the snapshot does not carry the gate numbers")
    breaches = []

    growing, printed = [], _gate(snap, "growing")
    for app in snap["apps"]:
        growth = (app.get("growth6m") or {}).get("g")
        if "business_not_growing" not in (app.get("degen_fail") or []) or growth is None:
            continue
        floor = next(t["g6_floor"] for t in tiers if (app.get("rev30d") or 0) >= t["min_rev30"])
        if growth > floor:
            growing.append(app["symbol"])
    if growing and not re.search(r"phase|flat|declin", printed, re.I):
        breaches.append({"what": f"Growing: {len(growing)} apps fail with six-month growth above the printed floor "
                                 f"({growing[:6]}), on a condition the rule does not print: {printed!r}"})

    declining = [a["symbol"] for a in snap["apps"]
                 if a.get("reliable") and (a.get("traj") or {}).get("phase") == "declining"]
    if declining and "trend not declining" in _gate(snap, "vetted"):
        breaches.append({"what": f"Vetted prints 'trend not declining' (the cut is {vetted.get('min_g6m')} % a month) "
                                 f"and {len(declining)} Vetted apps show phase Declining: {declining[:6]}"})

    if re.search(r"Newer apps pass at \$1M\+ a month and growing\.\s*$", _gate(snap, "vetted")):
        for app in snap["apps"]:
            if ((app.get("hist_days") or 999) < vetted["min_days"] and (app.get("rev30d") or 0) >= vetted["young_min_rev30"]
                    and (app.get("growth6m") or {}).get("g", -1) > 0 and app.get("reliable_fail") == ["short_history"]
                    and not app.get("young")):
                failed = (_coin(rest_anon, app["slug"]).get("vetted") or {}).get("failed") or []
                if len(failed) <= 1:
                    breaches.append({"what": f"{app['symbol']} ({app['hist_days']} days, ${app['rev30d']:,.0f} a month, Growing "
                                             f"passed) is not admitted as a newer app, and the only reason given is {failed}: "
                                             f"the condition that kept it out is printed nowhere"})
    _verdict(breaches, len(snap["apps"]), "every row follows the rule its gate prints")


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_a_six_month_figure_says_its_window(rest_anon):
    """A growth fitted on under five months is not stated 'over 6 months'. Any other
    wording passes, and so does a figure that goes."""
    snap, _ = read_page(rest_anon)
    young = sorted((a for a in snap["apps"] if ((a.get("growth6m") or {}).get("days") or 999) < 150),
                   key=lambda a: -(a.get("rev30d") or 0))[:8]
    if not young:
        raise Inconclusive("no app has a growth fit under five months today")
    breaches = []
    for app in young:
        said = re.search(r"[^\"\\]{0,50}a month over 6 months", _report_text(rest_anon, app["slug"]))
        if said:
            breaches.append({"what": f"{app['symbol']}: {said.group(0).strip()!r} on {app['growth6m']['days']} days of data"})
    _verdict(breaches, len(young), f"none of {len(young)} reports states six months on a shorter fit")


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_the_level_against_the_peak_is_what_its_unit_says(rest_anon):
    """`level_vs_peak` carries the unit '% of its 1-year high'. Renaming the unit
    passes, as does a value that is that."""
    snap, _ = read_page(rest_anon)
    pairs = [(a, (a.get("traj") or {}).get("level_vs_peak"), a.get("rev30d_vs_high")) for a in snap["apps"]]
    pairs = [p for p in pairs if p[1] is not None and p[2] is not None]
    if not pairs:
        raise Inconclusive("no row carries both figures")
    unit = (((_coin(rest_anon, pairs[0][0]["slug"]).get("trajectory") or {}).get("level_vs_peak")) or {}).get("unit") or ""
    apart = [p for p in pairs if abs(p[1] - p[2]) > 0.30]
    breaches = []
    if "1-year high" in unit and len(apart) > 0.05 * len(pairs):
        breaches.append({"what": f"unit {unit!r}, and {len(apart)} of {len(pairs)} rows are over 30 points from their 30-day "
                                 "revenue against its 1-year high: "
                                 + ", ".join(f"{p[0]['symbol']} {p[1]:.0%} vs {p[2]:.0%}" for p in apart[:5])})
    _verdict(breaches, len(pairs), f"the unit reads {unit!r}")


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_a_chain_rows_own_link_opens_that_chain(rest_anon):
    """Every row of the Chains list links to itself: its own `api_url` answers a chain."""
    rows = _json(rest_anon, "/api/v1/gem-screener/ranked?kind=chains&limit=100").get("items") or []
    if not rows:
        raise Inconclusive("the chains list is empty")
    breaches = []
    for row in rows:
        path = re.sub(r"^https?://[^/]+", "", row.get("api_url") or "")
        if not path:
            continue
        coin = _json(rest_anon, path)
        if coin.get("kind") != "chains":
            breaches.append({"what": f"chain row {row.get('slug')!r} ({row.get('name')}) opens the {coin.get('kind')} row "
                                     f"{coin.get('slug')!r} ({coin.get('name')})"})
    _verdict(breaches, len(rows), f"all {len(rows)} chain rows open themselves",
             {"ranked": "/api/v1/gem-screener/ranked?kind=chains"})


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_the_dilution_flag_says_what_decides_it(rest_anon):
    """The flag's meaning and the rule's formula are the ones applied."""
    snap, _ = read_page(rest_anon)
    caution = [a for a in snap["apps"] if (a.get("dilution") or {}).get("level") == "caution"]
    breaches = []
    under = [a for a in caution if (a["dilution"].get("over_bench_pts") or 0) <= 0]
    if under:
        meaning = (_coin(rest_anon, under[0]["slug"]).get("dilution") or {}).get("flag_meaning") or ""
        if "over the benchmark" in meaning:
            breaches.append({"what": f"flag_meaning {meaning!r}, while {len(under)} of {len(caution)} caution rows are at or "
                                     f"under the benchmark; the cut is {snap['dilution_meta'].get('caution_line')} % a week"})
    used = (snap.get("dilution_meta") or {}).get("from_supply_analyzer") or 0
    rule = _gate(snap, "dilution")
    if used and "larger of 30d paid out, 30d unlocking" in rule:
        breaches.append({"what": f"the rule prints 'larger of 30d paid out, 30d unlocking', and {used} rows use the "
                                 "Supply Analyzer's schedule instead"})
    _verdict(breaches, len(caution), "the flag and the rule describe what is applied")


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_category_shares_add_up_to_no_more_than_the_category(rest_anon):
    """'Share of its category's revenue' sums to at most 100 % within a category."""
    snap, _ = read_page(rest_anon)
    totals: dict[str, list] = {}
    for app in snap["apps"]:
        share = (app.get("share") or {}).get("30")
        if share is not None:
            totals.setdefault(app.get("category"), []).append((share, app["symbol"]))
    over = {k: v for k, v in totals.items() if sum(s for s, _ in v) > 101.5}
    breaches = [{"what": f"{k}: {sum(s for s, _ in v):.0f} % ("
                         + ", ".join(f"{n} {s:.0f}" for s, n in sorted(v, reverse=True)[:3]) + ")"} for k, v in over.items()]
    _verdict(breaches, len(totals), f"all {len(totals)} categories sum to 100 % or less")


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_the_holders_line_says_its_window(rest_anon):
    """'Holders get N % of revenue' reads as now. Where the last 30 days paid nothing
    the line says the figure is an older one, or it goes."""
    snap, _ = read_page(rest_anon)
    rows = [a for a in snap["apps"] if a.get("holders_share") == 0
            and re.match(r"Holders get [1-9]", str(a.get("holders_line") or ""))
            and not re.search(r"month|year|1y|past|last", str(a.get("holders_line")), re.I)]
    breaches = [{"what": f"{a['symbol']}: {a['holders_line']!r}, 30-day share 0 %, 12-month share {a.get('holders_share_1y'):.0%}",
                 "pick": bool(a.get("degen_ok"))} for a in rows]
    _verdict(breaches, len(snap["apps"]), "no line states an old share as the present one")


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_what_the_page_says_of_itself_holds(rest_anon):
    """The page's fixed sentences against the same page's data. A sentence that goes
    passes; so does data that comes to agree with it."""
    snap, html = read_page(rest_anon)
    apps = {a.get("slug"): a for a in snap["apps"]}
    breaches = []
    if "Stablecoins and DEX volume are shown as context only" in html and any(c.get("adoption") for c in snap.get("chains") or []):
        breaches.append({"what": "About: 'Stablecoins and DEX volume are shown as context only', while a chain's Adoption, "
                                 "price tag and Upside are built from them"})
    solv = ((apps.get("solv-protocol") or {}).get("liq") or {}).get("pair_liq_usd")
    if "pool holds about $20K" in html and solv and not 10_000 <= solv <= 40_000:
        breaches.append({"what": f"About: 'SOLV's deepest reachable pool holds about $20K', its row's pool holds ${solv:,.0f}"})
    priced = (snap.get("sector_stages") or {}).get("priced") or {}
    if ("Prices of the moment were incomplete" in html and priced.get("end") != "live"
            and priced.get("live_coins") == priced.get("coins_asked") and priced.get("coins_asked")):
        breaches.append({"what": f"Sectors: 'Prices of the moment were incomplete ({priced['live_coins']} of "
                                 f"{priced['coins_asked']} coins had one)'; every coin had one, the cause is a basket's weight"})
    mult = (snap.get("bench") or {}).get("mult") or 0
    dearer = [a["symbol"] for a in snap["apps"] if (a.get("mcap") or 0) >= 1e9 and (a.get("ps") or 0) > mult]
    if "most expensive large protocol with revenue" in html and dearer:
        breaches.append({"what": f"Price vs revenue: Hyperliquid is 'the most expensive large protocol with revenue' at "
                                 f"{mult:.1f}x; market cap $1B+ and dearer: {dearer[:6]}"})
    if "the 18 checks" in html:
        count = len((_coin(rest_anon, "aave").get("degen_level") or {}).get("checks") or [])
        if count and count != 18:
            breaches.append({"what": f"'the 18 checks', and a coin answers {count}"})
    _verdict(breaches, 5, "the page's fixed sentences hold on its data")


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_a_phase_is_what_its_help_says(rest_anon):
    """The Accelerating help says every quarter is faster than the one before. It
    should be true of most rows that carry the word, or say something else."""
    snap, html = read_page(rest_anon)
    rows = [a for a in snap["apps"] if (a.get("traj") or {}).get("phase") == "accelerating"]
    if not rows:
        raise Inconclusive("no app is in phase Accelerating")
    rising = 0
    for app in rows:
        periods = app["traj"].get("periods") or {}
        q = [(periods.get(k) or {}).get("g") for k in ("p1", "p2", "p3", "p4")]
        if None not in q and q[0] < q[1] < q[2] < q[3]:
            rising += 1
    breaches = []
    if "every quarter faster than the one before" in html and rising < 0.5 * len(rows):
        breaches.append({"what": f"'every quarter faster than the one before' holds on {rising} of {len(rows)} Accelerating rows"})
    _verdict(breaches, len(rows), f"{rising} of {len(rows)} Accelerating rows; the help text agrees")


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_the_backtest_caveat_holds_for_every_hypothesis(rest_anon):
    """The sentence agents are told to repeat is not contradicted by the backtest it
    sums up: no 'the estimates came out positive' above a result wholly below zero."""
    snap, _ = read_page(rest_anon)
    caveat = str((_json(rest_anon, g.PICKS).get("caveats") or {}).get("backtest") or "")
    h3 = (snap.get("backtest_summary") or {}).get("h3") or {}
    ci = h3.get("ci90") or []
    if len(ci) != 2:
        raise Inconclusive("the backtest publishes no interval for the gate-passing coins")
    breaches = []
    if re.search(r"came out positive|do not exclude zero", caveat) and ci[1] < 0:
        breaches.append({"what": f"caveat {caveat!r}; the gate-passing coins' median difference is {h3.get('diff_median')}, "
                                 f"90 % interval {ci}, wholly below zero"})
    _verdict(breaches, 1, "the caveat agrees with the backtest", {"picks": g.PICKS, "page": g.APP_PAGE})


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_a_coin_does_not_fail_liquid_on_a_shallower_pool_than_it_has(rest_anon):
    """An app whose only failed gate is Thin liquidity, read on a pool the page calls
    the deepest, has no constant-product pool against a major that would pass it.
    Only v2 pools: their depth is what the page's formula means. Calling the pool
    something else, or using the deeper one, passes."""
    snap, _ = read_page(rest_anon)
    only_thin = [a for a in snap["apps"] if a.get("degen_fail") == ["thin_liquidity"]]
    if not only_thin:
        raise Inconclusive("no app fails Liquid alone today")
    source = build_source_client()
    breaches = []
    try:
        for app in only_thin:
            coin = _coin(rest_anon, app["slug"])
            contract = coin.get("contract") or {}
            named = ((coin.get("liquidity") or {}).get("pool_liquidity") or {}).get("value")
            if not contract.get("address") or not named:
                continue
            pairs = _source_json(source, f"https://api.dexscreener.com/token-pairs/v1/{contract.get('chain')}/{contract['address']}")
            deep = [p for p in pairs if "v2" in (p.get("labels") or [])
                    and (p.get("baseToken") or {}).get("address", "").lower() == contract["address"].lower()
                    and (p.get("quoteToken") or {}).get("symbol") in {"WETH", "USDC", "USDT", "WBNB", "SOL", "WSOL"}
                    and ((p.get("liquidity") or {}).get("usd") or 0) >= THREE_PCT_POOL_USD]
            why = " ".join(a.get("why") or "" for a in (coin.get("degen_level") or {}).get("areas") or [])
            if deep and named < THREE_PCT_POOL_USD and "Deepest DEX pool" in why:
                best = max(deep, key=lambda p: p["liquidity"]["usd"])
                breaches.append({"what": f"{app['symbol']}: 'Deepest DEX pool' is ${named:,.0f}; "
                                         f"{best.get('dexId')} {best['baseToken']['symbol']}/{best['quoteToken']['symbol']} v2 "
                                         f"{best.get('pairAddress')} holds ${best['liquidity']['usd']:,.0f}, which passes"})
    finally:
        source.close()
    _verdict(breaches, len(only_thin), f"none of the {len(only_thin)} apps failing only Liquid has a pool that would pass",
             {"page": g.APP_PAGE, "dexscreener": "https://api.dexscreener.com/token-pairs/v1"})


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_no_power_to_mint_is_not_said_of_a_token_that_can_mint(rest_anon):
    """Railgun's verified source has an owner-only mint under a cap above its supply.
    Named, since an ABI read per token is an audit, not a check."""
    coin = _coin(rest_anon, "railgun")
    control = next((a for a in (coin.get("degen_level") or {}).get("areas") or [] if a.get("id") == "control"), {})
    source = build_source_client()
    try:
        code = _source_json(source, "https://eth.blockscout.com/api/v2/smart-contracts/0xe76c6c83af64e4c60245d8c7de953df673a7a33d")
    finally:
        source.close()
    text = code.get("source_code") or ""
    if not text:
        raise Inconclusive("Blockscout returned no verified source")
    breaches = []
    if "No power to mint" in (control.get("line") or "") and re.search(r"function governanceMint[^{]*onlyOwner", text):
        breaches.append({"what": f"Railgun: {control.get('line')!r}, {control.get('why')!r}; the verified token has "
                                 "governanceMint(...) external onlyOwner"})
    _verdict(breaches, 1, "the sentence agrees with the contract", {"coin": "/api/v1/gem-screener/coins/railgun"})


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_the_holders_how_agrees_with_its_own_source(rest_anon):
    """A row that says revenue is burned does not quote a source saying it is not."""
    snap, _ = read_page(rest_anon)
    rows = [a for a in snap["apps"] if a.get("holders_how") == "burn"
            and re.search(r"\bno \w+ is burned\b|\bnot burned\b", str(a.get("holders_how_src") or ""), re.I)]
    breaches = [{"what": f"{a['symbol']}: {a.get('holders_line')!r}; its own source: {a.get('holders_how_src')!r}"} for a in rows]
    _verdict(breaches, sum(1 for a in snap["apps"] if a.get("holders_how")), "every 'burned' agrees with its source")


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_an_excluded_app_with_a_token_is_not_said_to_have_none(rest_anon):
    """'No token of its own ... so there is nothing to buy' is false for the Aerodrome
    family. Listing it, or giving the true reason, passes."""
    snap, _ = read_page(rest_anon)
    reason = ((snap.get("excluded") or {}).get("reasons") or {}).get("no_token") or ""
    extras = _json(rest_anon, f"/api/v1/gem-screener/page-extras?g={snap.get('generated_at')}")
    rows = [e for e in extras.get("excluded_apps") or []
            if e.get("reason") == "no_token" and re.search(r"aerodrome|aero |velodrome", str(e.get("name")), re.I)]
    listed = any(a.get("gecko_id") == "aerodrome-finance" for a in snap["apps"])
    source = build_source_client()
    try:
        market = _source_json(source, "https://api.coingecko.com/api/v3/coins/markets?vs_currency=usd&ids=aerodrome-finance")
    finally:
        source.close()
    cap = (market[0].get("market_cap") if market else None) or 0
    breaches = []
    if rows and not listed and cap > 0 and "nothing to buy" in reason:
        revenue = sum(e.get("revenue_30d") or 0 for e in rows)
        breaches.append({"what": f"{len(rows)} Aerodrome and Velodrome rows, ${revenue:,.0f} of revenue in 30 days, are left out as "
                                 f"{reason!r}; AERO has a ${cap:,.0f} market cap on CoinGecko and no row"})
    _verdict(breaches, len(rows), "the Aerodrome family is listed or given its true reason",
             {"extras": "/api/v1/gem-screener/page-extras"})


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_a_report_says_good_only_of_what_it_checked(rest_anon):
    """A report's Good line and its Real-or-printed line do not outrun the checks on
    the same coin. Named coins that had it on 2026-11-02; one that goes is skipped."""
    breaches, read = [], 0
    for slug in ("bordrless", "pear-interface", "railgun", "the-index", "gaib", "saucerswap", "usd-ai"):
        if get_patiently(rest_anon, g.COIN.format(symbol=slug)).status_code != 200:
            continue
        read += 1
        coin, report = _coin(rest_anon, slug), _report_text(rest_anon, slug)
        reaches = re.search(r"Good: [^\"\\]*?\d+% of revenue reaches holders", report)
        if reaches and _check(coin, "reaches_you").get("verdict") == "not_checked":
            breaches.append({"what": f"{coin.get('symbol')}: {reaches.group(0)!r}, while the check that answers it is 'not checked'"})
        printed = re.search(r"prints \$0 in tokens, so \+[^\"\\.]*real", report)
        yields = _check(coin, "real_yield")
        if printed and yields.get("verdict") == "bad":
            breaches.append({"what": f"{coin.get('symbol')}: {printed.group(0)!r}, while its own check reads {yields.get('text')!r}"})
    if not read:
        raise Inconclusive("none of the named coins is served")
    _verdict(breaches, read, f"the {read} reports read agree with their checks")


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_a_supply_percentage_is_of_what_it_says(rest_anon):
    """'Of the float' and '% of circulating supply' are of the circulating supply the
    row shows, which `next_unlock` uses. Named coins: where the two agree or the
    wording goes, this passes."""
    breaches = []
    gaib = _coin(rest_anon, "gaib")
    why = " ".join(a.get("why") or "" for a in (gaib.get("degen_level") or {}).get("areas") or [])
    shown = ((gaib.get("unlocks") or {}).get("unlock_90d") or {}).get("value")
    total = (gaib.get("next_unlock") or {}).get("total90_pct")
    if "of the float" in why and shown and total and abs(shown - total) / total > 0.10:
        breaches.append({"what": f"GAIB: '{round(shown)}% of the float unlocks within 90 days'; next_unlock.total90_pct is {total:.1f}"})
    lista = _coin(rest_anon, "lista-dao")
    cliff = ((lista.get("unlocks") or {}).get("next_cliff") or {}).get("size") or {}
    pct = (lista.get("next_unlock") or {}).get("pct_of_circ")
    if "circulating" in str(cliff.get("unit")) and cliff.get("value") and pct and abs(cliff["value"] - pct) / pct > 0.10:
        breaches.append({"what": f"Lista: next_cliff.size {cliff['value']} {cliff['unit']!r}; next_unlock.pct_of_circ is {pct:.2f} for the same event"})
    _verdict(breaches, 2, "the percentages agree where both are given")


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_every_vetted_flag_follows_its_numbers(rest_anon):
    """`reliable_fail` from the published numbers, on every row: the gate audit took
    the flag on trust until 2026-11-02. It held on 236 of 236 that day."""
    snap, _ = read_page(rest_anon)
    vetted = ((snap.get("degen") or {}).get("rules") or {}).get("vetted") or {}
    if not vetted:
        raise Inconclusive("the snapshot does not carry the Vetted numbers")
    breaches = []
    for app in snap["apps"]:
        want = set()
        if (app.get("mcap") or 0) < vetted["min_mcap"]:
            want.add("market_cap_under_3m")
        level = (app.get("traj") or {}).get("level_vs_peak")
        if level is not None and level < vetted["min_level_vs_peak"]:
            want.add("far_below_peak")
        if (app.get("hist_days") or 0) < vetted["min_days"]:
            want.add("short_history")
        growth = (app.get("growth6m") or {}).get("g")
        if growth is None:
            want.add("trend_unmeasurable")
        elif growth < vetted["min_g6m"]:
            want.add("declining_trend")
        if (app.get("lag_days") or 0) > vetted["max_lag_days"]:
            want.add("stale_data")
        if want != set(app.get("reliable_fail") or []):
            breaches.append({"what": f"{app.get('symbol')}: reliable_fail {app.get('reliable_fail')}, its numbers give {sorted(want)}"})
    _verdict(breaches, len(snap["apps"]), f"all {len(snap['apps'])} rows follow the published Vetted numbers")
