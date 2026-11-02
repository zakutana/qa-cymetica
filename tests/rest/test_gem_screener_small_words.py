"""The smaller false statements the mega-check of 2026-11-02 found, on top of
test_gem_screener_says_only_what_is_true.py: same bar, lower stakes. Each goes green on any fix that gives the reader
the true statement, a sentence that goes included.

NOT asserted: the design of a screen, or that a coin is worth anything. SAFE: GETs only, anonymous; third parties through
`build_source_client`.
"""

from __future__ import annotations

import re

import httpx

from qa import gemaudit as g
from qa.client import build_source_client
from qa.marks import Inconclusive, SafetyTier, qa
from tests.rest.test_gem_screener_numbers_match_their_sources import get_patiently, read_page
from tests.rest.test_gem_screener_says_only_what_is_true import _check, _coin, _json, _report_text, _source_json, _verdict


def _text(client, url: str) -> str:
    response = get_patiently(client, url, headers={"Accept": "text/html"})
    if response.status_code != 200:
        raise Inconclusive(f"{url} answered HTTP {response.status_code}")
    return response.text


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_the_docs_name_what_is_served(rest_anon):
    """The counts the docs state, and the route an agent is sent to first."""
    llms, docs = _text(rest_anon, "/llms.txt"), _text(rest_anon, "/api-docs")
    total = _json(rest_anon, "/api/v1/gem-screener/ranked?limit=1").get("total")
    total = total.get("value") if isinstance(total, dict) else total
    breaches = []
    said = re.search(r"about (\d+) apps", llms)
    if said and total and abs(int(said.group(1)) - total) > 0.05 * total:
        breaches.append({"what": f"llms.txt says about {said.group(1)} apps, /ranked total is {total}"})
    if "gem-screener" in docs and "gem-screener/picks" not in docs:
        breaches.append({"what": "/api-docs has Gem Screener rows and none for GET /api/v1/gem-screener/picks, the route llms.txt starts from"})
    if "gem-screener/page-extras" not in llms and "gem-screener/page-extras" not in _text(rest_anon, "/openapi-public.json"):
        breaches.append({"what": "GET /api/v1/gem-screener/page-extras, which carries the excluded names and the altseason series, is in neither llms.txt nor the OpenAPI"})
    _verdict(breaches, 3, "the docs name what is served", {"llms": "/llms.txt", "docs": "/api-docs"})


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_one_word_means_one_number(rest_anon):
    """Where the page uses one word for two things, or quotes a number for something else."""
    snap, html = read_page(rest_anon)
    breaches = []
    for theme in snap.get("themes") or []:
        f = theme.get("fundament") or {}
        if f.get("last30") and f.get("rev30d") and abs(f["last30"] / f["rev30d"] - 1) > 0.03 and "isNum(f.last30) ? f.last30" in html:
            breaches.append({"what": f"theme {theme.get('key')}: revenue over 30 days is ${f['last30']:,.0f} in the table and ${f['rev30d']:,.0f} in its panel"})
    index = (snap.get("altseason") or {}).get("index")
    breadth = (((snap.get("altseason_cycle") or {}).get("components") or {}).get("breadth") or {}).get("value")
    if "% on the old card" in html and index is not None and breadth is not None and abs(index - breadth) > 1:
        breaches.append({"what": f"the Altseason (i) says {breadth:.0f}% on the old card; the old card's figure, altseason.index, is {index:.0f}"})
    if re.search(r"hot\.slice\(0, ?3\)", html) and ((snap.get("sector_stages") or {}).get("counts") or {}).get("hot", 0) > 3:
        breaches.append({"what": f"'Hot right now' names 3 sectors; {snap['sector_stages']['counts']['hot']} are marked Hot in the table beneath it, and it does not say more exist"})
    heat = " ".join(a.get("line") or "" for a in (_coin(rest_anon, "stonkfun").get("degen_level") or {}).get("areas") or [])
    if "Price vs revenue: needs history" in heat:
        breaches.append({"what": "'Price vs revenue: needs history' is the Strength 3M check, on a coin whose Price vs revenue figure is shown"})
    young = sum(1 for a in snap["apps"] if (a.get("hist_days") or 999) < 365)
    marked = sum(1 for a in snap["apps"] if (a.get("hist_days") or 999) < 180)
    if "are marked young in the table" in _text(rest_anon, "/gem-screener") and young > marked:
        breaches.append({"what": f"/gem-screener: apps under a year 'are marked young in the table'; {young} are under a year, the New tag marks {marked}"})
    _verdict(breaches, 5, "each word holds one number")


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_the_picks_route_warns_what_the_card_says(rest_anon):
    """The card says a pick's 12-month dilution is unknown; /picks, which agents are told to repeat, says the same."""
    snap, _ = read_page(rest_anon)
    apps = {a.get("slug"): a for a in snap["apps"]}
    breaches, read = [], 0
    for pick in _json(rest_anon, g.PICKS).get("picks") or []:
        app = apps.get(pick.get("slug")) or {}
        read += 1
        if app.get("sa_dilution_12m_pct") is None and not any("dilution" in w.lower() for w in pick.get("warnings") or []):
            breaches.append({"what": f"{pick.get('symbol')}: 12-month dilution unknown on the card, no word of it among /picks warnings {pick.get('warnings')}"})
    _verdict(breaches, read, "/picks warns of what the cards show as unknown", {"picks": g.PICKS})


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_vetted_is_not_passed_on_a_level_it_could_not_read(rest_anon):
    """Vetted asks for 35 % of the best quarter. A row with no such reading has not met it."""
    snap, _ = read_page(rest_anon)
    rows = [a for a in snap["apps"] if a.get("reliable") and (a.get("traj") or {}).get("level_vs_peak") is None]
    breaches = [{"what": f"{a['symbol']}: Vetted with no level_vs_peak; 30-day revenue ${a.get('rev30d'):,.0f} is {a.get('rev30d_vs_high', 0):.0%} of its best"} for a in rows]
    _verdict(breaches, len(snap["apps"]), "no Vetted row lacks the level the rule reads")


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_bonk_fun_is_labelled_from_its_own_money(rest_anon):
    """Named: the row's route and its quoted proof come from the part of the family that earns it."""
    snap, _ = read_page(rest_anon)
    app = next((a for a in snap["apps"] if a.get("slug") == "bonk.fun"), None)
    if not app:
        raise Inconclusive("bonk.fun is not served today")
    reaches = _check(_coin(rest_anon, "bonk.fun"), "reaches_you")
    source = build_source_client()
    try:
        whole = _source_json(source, "https://api.llama.fi/summary/fees/bonk.fun?dataType=dailyHoldersRevenue").get("total30d") or 0
        quoted = _source_json(source, "https://api.llama.fi/summary/fees/bonkswap?dataType=dailyHoldersRevenue").get("total30d") or 0
    finally:
        source.close()
    breaches = []
    if "bonkswap" in str(reaches.get("source_url")) and whole and quoted < 0.05 * whole:
        breaches.append({"what": f"BONK.fun 'Directly' quotes Bonkswap's adapter, {quoted / whole:.2%} of the family's holders revenue (${quoted:,.0f} of ${whole:,.0f})"})
    if app.get("holders_how") == "burn" and re.search(r"SBR|BonkRewards", str(app.get("holders_how_src"))):
        breaches.append({"what": f"BONK.fun {app.get('holders_line')!r}; its source splits it: {app.get('holders_how_src')!r}"})
    _verdict(breaches, 2, "the row's route and proof are its own", {"coin": "/api/v1/gem-screener/coins/bonk.fun"})


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_a_chart_says_which_market_it_read(rest_anon):
    """Named: a chart on another chain than the pool the row prices says so, or reads that pool."""
    breaches, read = [], 0
    for slug in ("saucerswap", "usd-ai"):
        coin = _coin(rest_anon, slug)
        contract, pool = (coin.get("contract") or {}).get("chain"), (coin.get("liquidity") or {}).get("chain")
        url = str(coin.get("chart_analyzer_url") or "")
        if not contract or not pool or not url:
            continue
        read += 1
        if contract != pool and f"chain={contract}" in url and pool not in str(coin.get("chart") or {}):
            breaches.append({"what": f"{coin.get('symbol')}: the chart is read on {contract}, the row's liquidity and price on {pool}, and nothing says so"})
    if not read:
        raise Inconclusive("neither named coin carries a contract, a pool and a chart today")
    _verdict(breaches, read, "each chart reads the row's market or says it does not")


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_a_report_reads_as_the_coin_it_is_on(rest_anon):
    """A chain is priced on adoption; a description ends as a sentence."""
    breaches = []
    tron = _report_text(rest_anon, "tron")
    if "cheap for its revenue" in tron and _coin(rest_anon, "tron").get("kind") == "chains":
        breaches.append({"what": "Tron's report: 'cheap for its revenue'; a chain's price tag is market cap over adoption, its row carries no revenue test"})
    said = re.search(r"What it is: [^.\"\\]*\b(?:a|an|the) \w+\.", _report_text(rest_anon, "sudoswap"))
    if said:
        breaches.append({"what": f"Sudoswap's report: {said.group(0)!r}, a sentence cut short"})
    _verdict(breaches, 2, "the reports read as their coins", {"coin": "/api/v1/gem-screener/coins/tron/degen-report"})


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_the_float_tag_follows_its_own_line(rest_anon):
    """`risk_rules.float_tag` is the line under which the row is tagged; a row showing under it is tagged."""
    snap, _ = read_page(rest_anon)
    line = (snap.get("risk_rules") or {}).get("float_tag")
    if not isinstance(line, (int, float)):
        raise Inconclusive("the snapshot carries no float_tag")
    rows = [a for a in snap["apps"] if isinstance((a.get("supply") or {}).get("out_pct"), (int, float))]
    tagged = [a for a in rows if "float" in (a.get("risks") or [])]
    missed = [a for a in rows if a["supply"]["out_pct"] < 100 * line and a not in tagged]
    breaches = []
    if tagged and len(missed) >= 3:
        breaches.append({"what": f"{len(missed)} rows show under {line:.0%} of tokens out with no float tag: "
                                 + ", ".join(f"{a['symbol']} {a['supply']['out_pct']:.1f}%" for a in missed[:6])})
    _verdict(breaches, len(rows), "every row under the line is tagged")


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_a_trailing_slash_stays_on_https(rest_anon):
    """Their redirect for a trailing slash keeps the scheme it was asked on."""
    source = build_source_client()
    try:
        response = source.get("https://cymetica.com/api/v1/gem-screener/ranked/", follow_redirects=False)
    except httpx.HTTPError as exc:
        raise Inconclusive(f"the route could not be read: {type(exc).__name__}")
    finally:
        source.close()
    where = response.headers.get("location") or ""
    breaches = [{"what": f"HTTP {response.status_code} to {where}"}] if where.startswith("http://") else []
    _verdict(breaches, 1, f"the answer stays on https ({response.status_code} {where})", {"route": "/api/v1/gem-screener/ranked/"})


SUPPLY_BATCH = "/api/v1/supply-analyzer/batch/gem-screener"
LLAMA_SCHEDULE = "https://defillama-datasets.llama.fi/emissions/{slug}"


def _ahead_in_a_year(schedule: dict, now: float) -> float:
    """Tokens DefiLlama's documented schedule still unlocks in the next 365 days."""
    total = 0.0
    for section in (schedule.get("documentedData") or {}).get("data") or []:
        points = section.get("data") or []
        before = [p.get("unlocked") or 0 for p in points if p.get("timestamp", 0) <= now]
        after = [p.get("unlocked") or 0 for p in points if p.get("timestamp", 0) <= now + 365 * 86400]
        if before and after:
            total += max(0.0, after[-1] - before[-1])
    return total


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_dilution_is_not_ok_on_a_coin_with_a_schedule_ahead(rest_anon):
    """Named: Lombard's schedule runs to 2029 on DefiLlama. The row reads it, or stops saying there is none."""
    snap, _ = read_page(rest_anon)
    coin = _coin(rest_anon, "lombard")
    app = next((a for a in snap["apps"] if a.get("slug") == "lombard"), {})
    circ = (app.get("cg") or {}).get("circ")
    source = build_source_client()
    try:
        ahead = _ahead_in_a_year(_source_json(source, LLAMA_SCHEDULE.format(slug="lombard")), snap.get("generated_at") or 0)
    finally:
        source.close()
    if not circ:
        raise Inconclusive("Lombard's circulating supply is not on the row today")
    share = 100 * ahead / circ
    dilution, nxt = coin.get("dilution") or {}, coin.get("next_unlock") or {}
    breaches = []
    if share > 5 and (nxt.get("kind") == "unknown" or dilution.get("flag") == "ok"):
        breaches.append({"what": f"Lombard: dilution flag {dilution.get('flag')!r}, next_unlock {nxt.get('kind')!r}, {nxt.get('note')!r}; DefiLlama's schedule "
                                 f"unlocks {ahead:,.0f} tokens in 12 months, {share:.0f}% of circulating"})
    _verdict(breaches, 1, "the row agrees with the schedule on file", {"schedule": LLAMA_SCHEDULE.format(slug="lombard")})


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_no_schedule_on_any_feed_is_said_only_where_there_is_none(rest_anon):
    """Named: 'No vesting or unlock schedule on any feed we read' on coins whose finished schedule is on DefiLlama."""
    rows = {(r.get("token") or {}).get("slug"): r for r in _json(rest_anon, SUPPLY_BATCH).get("items") or []}
    breaches, read = [], 0
    source = build_source_client()
    try:
        for slug in ("jupiter", "cowswap", "chainlink", "tornado-cash"):
            why = str(((rows.get(slug) or {}).get("next_unlock") or {}).get("why") or "")
            schedule = _source_json(source, LLAMA_SCHEDULE.format(slug=slug))
            sections = (schedule.get("documentedData") or {}).get("data") or []
            read += 1
            if "No vesting or unlock schedule on any feed" in why and sections:
                breaches.append({"what": f"{slug}: {why!r}; DefiLlama holds {len(sections)} sections of its schedule"})
    finally:
        source.close()
    _verdict(breaches, read, "the sentence is said only where no schedule is on file", {"batch": SUPPLY_BATCH})


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_the_supply_pie_does_not_say_free_to_sell_when_it_does_not_know(rest_anon):
    """A pie that is 100 % 'Free to sell' on a coin whose vesting and staking are listed as unknown states what is not known."""
    items = _json(rest_anon, SUPPLY_BATCH).get("items") or []
    if not items:
        raise Inconclusive("the batch is empty")
    rows = []
    for row in items:
        free = next((s.get("share_pct") for s in row.get("slices_today") or [] if s.get("key") == "free"), 0) or 0
        unknown = row.get("unknown_names") or []
        if free >= 99.9 and "vesting schedule" in unknown and "staking" in unknown:
            rows.append((row.get("token") or {}).get("symbol"))
    breaches = [{"what": f"{len(rows)} of {len(items)} rows draw a pie 100% Free to sell with vesting and staking listed as unknown: {rows[:8]}"}] if rows else []
    _verdict(breaches, len(items), "no pie states what the row does not know", {"batch": SUPPLY_BATCH})


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_to_holders_says_none_only_where_it_knows(rest_anon):
    """'None, no payouts, buybacks or burns found' is a finding. The report on the same coin saying its share is unknown
    means it is not one. Either sentence moving clears it."""
    _, html = read_page(rest_anon)
    breaches = []
    if "no payouts, buybacks or burns found" in html:
        coin = _coin(rest_anon, "dolomite")
        report = _report_text(rest_anon, "dolomite")
        if "holders' share unknown" in report and (coin.get("to_holders") or {}).get("value") in (None, 0):
            breaches.append({"what": "Dolomite: the panel's To holders reads None, 'no payouts, buybacks or burns found'; its report reads \"holders' share unknown\" and \"DefiLlama's fee page could not be read\""})
    _verdict(breaches, 1, "None is said only where it is known", {"coin": "/api/v1/gem-screener/coins/dolomite"})
