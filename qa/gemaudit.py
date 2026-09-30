"""The Gem Screener, audited as a degen would rely on it -- as code, so the whole
audit can be repeated (2026-09-30).

The operator asked for the app to be walked through as someone who means to lean
on its numbers in the next altseason, and for every place that looks wrong or
that they would be afraid to trust. The first pass was done by hand. This file is
what that pass became: pure functions over the page's own published snapshot and
over what independent sources say, so `scripts/gem_audit.py` can redo the audit
on any day and the checks in `tests/rest/test_gem_screener_*.py` can hold the
parts that will not change.

What was found, in one line each, so the code below has a reason:

  * The numbers are faithful copies of public sources (market cap vs CoinGecko
    median 1.4 %, revenue vs DefiLlama 0.9 %, pool liquidity vs DexScreener
    0.9 %). The risk is not in the copying; the checks keep it that way.
  * `potential_raw` is exactly `bench.mult / ps`, capped at 50x, for all 215
    apps -- a formula worth holding still, because every ranking stands on it.
  * The altseason composite is `(rot_weight * rotation + euph_weight * euphoria)
    / (rot_weight + euph_weight)`, with both weights published in its own rules.
  * A Degen pick's own link (`?coin=EDGE`) opened a different token (edgeX, not
    Definitive): four tickers are shared by two apps each, and the symbol route
    answers with one of them.

Nothing here writes anywhere or decides what is a defect. The functions return
numbers and lists; the test or the script says what they mean. A failed read of a
source is `SourceUnavailable`, never an empty answer (rule 8).
"""

from __future__ import annotations

import json
import re
import statistics
import time
from typing import Callable, Iterable

APP_PAGE = "/gem-screener/app?view=apps"
PICKS = "/api/v1/gem-screener/picks"
COIN = "/api/v1/gem-screener/coins/{symbol}"

COINGECKO = "https://api.coingecko.com/api/v3/coins/markets"
LLAMA_REVENUE = ("https://api.llama.fi/overview/fees?excludeTotalDataChart=true"
                 "&excludeTotalDataChartBreakdown=true&dataType=dailyRevenue")
DEXSCREENER = "https://api.dexscreener.com/latest/dex/pairs/{chain}/{addresses}"

SNAPSHOT_BLOCK = re.compile(
    r'<script id="snapshot-data" type="application/json">(.*?)</script>', re.S)

HOUR = 3600.0


class SnapshotUnreadable(Exception):
    """The app page carries no snapshot we can read."""


class SourceUnavailable(Exception):
    """A source did not answer, or answered something we cannot read. Never
    treated as "the source has nothing": a read that failed is not an empty one."""


# -- reading ------------------------------------------------------------------

def parse_snapshot(html: str) -> dict:
    """The snapshot the page is drawn from, out of the page's own HTML."""
    found = SNAPSHOT_BLOCK.search(html or "")
    if not found:
        raise SnapshotUnreadable("no snapshot-data block in the app page")
    try:
        snap = json.loads(found.group(1))
    except ValueError as exc:
        raise SnapshotUnreadable(f"the snapshot is not JSON: {exc}") from exc
    apps = snap.get("apps") if isinstance(snap, dict) else None
    if not isinstance(apps, list) or not apps:
        raise SnapshotUnreadable("the snapshot holds no apps")
    return snap


def num(value) -> float | None:
    """A number, whether the API sent 4.1 or {"value": 4.1, "unit": "x"}."""
    if isinstance(value, dict):
        value = value.get("value")
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value)


def label(app: dict) -> str:
    return f"{app.get('symbol')}({app.get('key')})"


def age_hours(snap: dict, now: float) -> float | None:
    made = snap.get("generated_at")
    return (now - made) / HOUR if isinstance(made, (int, float)) else None


# -- third-party sources (the caller passes `get`, so a test and a script use
#    the same code through whichever guarded client each has) -------------------

def _json(response, who: str):
    if response.status_code != 200:
        raise SourceUnavailable(f"{who} answered HTTP {response.status_code}")
    try:
        return response.json()
    except ValueError:
        raise SourceUnavailable(f"{who} answered 200 with a body that is not JSON")


def fetch_coingecko(get: Callable, ids: Iterable[str], *, chunk: int = 100,
                    pause: float = 2.0, sleep: Callable = time.sleep) -> list[dict]:
    wanted = sorted({i for i in ids if i})
    rows: list[dict] = []
    for start in range(0, len(wanted), chunk):
        if start:
            sleep(pause)
        part = _json(get(COINGECKO, params={
            "vs_currency": "usd", "ids": ",".join(wanted[start:start + chunk]),
            "per_page": 250, "page": 1, "sparkline": "false",
            "price_change_percentage": "7d,30d"}), "CoinGecko markets")
        if not isinstance(part, list):
            raise SourceUnavailable("CoinGecko markets did not answer a list")
        rows += part
    if not rows:
        raise SourceUnavailable("CoinGecko markets answered no rows")
    return rows


def fetch_llama_revenue(get: Callable) -> list[dict]:
    body = _json(get(LLAMA_REVENUE), "DefiLlama fees overview")
    protocols = body.get("protocols") if isinstance(body, dict) else None
    if not isinstance(protocols, list) or not protocols:
        raise SourceUnavailable("DefiLlama fees overview listed no protocols")
    return protocols


def fetch_dexscreener(get: Callable, wanted: Iterable[tuple[str, str]], *,
                      chunk: int = 25, pause: float = 0.4,
                      sleep: Callable = time.sleep) -> tuple[dict, list[str]]:
    """{(chain, pair address lower-cased): DexScreener pair}, and the chains
    whose request failed -- named, so a partial read is never mistaken for a
    full one."""
    by_chain: dict[str, list[str]] = {}
    for chain, address in wanted:
        by_chain.setdefault(chain, []).append(address)
    found: dict = {}
    failed: list[str] = []
    first = True
    for chain, addresses in sorted(by_chain.items()):
        for start in range(0, len(addresses), chunk):
            if not first:
                sleep(pause)
            first = False
            url = DEXSCREENER.format(chain=chain,
                                     addresses=",".join(addresses[start:start + chunk]))
            try:
                body = _json(get(url), f"DexScreener {chain}")
            except SourceUnavailable:
                failed.append(chain)
                continue
            for pair in (body.get("pairs") or []) if isinstance(body, dict) else []:
                if isinstance(pair, dict) and pair.get("pairAddress"):
                    found[(chain, str(pair["pairAddress"]).lower())] = pair
    if by_chain and not found:
        raise SourceUnavailable("DexScreener answered no pairs at all")
    return found, sorted(set(failed))


# -- joins: what the page says against what a source says ----------------------

Pair = tuple  # (label, page value, source value)


def supply_pairs(snap: dict, cg_rows: Iterable[dict]) -> list[Pair]:
    by_id = {r.get("id"): r for r in cg_rows}
    out = []
    for app in snap["apps"]:
        row = by_id.get(app.get("gecko_id"))
        if row:
            out.append((label(app), num((app.get("cg") or {}).get("circ")),
                        num(row.get("circulating_supply"))))
    return out


def price_pairs(snap: dict, cg_rows: Iterable[dict]) -> list[Pair]:
    by_id = {r.get("id"): r for r in cg_rows}
    out = []
    for app in snap["apps"]:
        row = by_id.get(app.get("gecko_id"))
        if row:
            out.append((label(app), num(app.get("price")), num(row.get("current_price"))))
    return out


def benchmark_pairs(snap: dict, cg_rows: Iterable[dict]) -> list[Pair]:
    """The benchmark's market cap against CoinGecko's for the same asset. Every
    upside on the page is this coin's multiple divided by another's, so a wrong
    benchmark is wrong everywhere at once. The asset is found by the benchmark's
    own label among the apps; if it is not there, there is nothing to compare
    and the list is empty (the caller says so)."""
    bench = snap.get("bench") or {}
    wanted = str(bench.get("label") or "").casefold()
    app = next((a for a in snap["apps"] if str(a.get("name") or "").casefold() == wanted), None)
    row = next((r for r in cg_rows if app and r.get("id") == app.get("gecko_id")), None)
    if not app or not row:
        return []
    return [(f"benchmark {bench.get('label')}", num(bench.get("mcap")), num(row.get("market_cap")))]


def benchmark_arithmetic(snap: dict, *, tol: float = 0.005) -> list[dict]:
    """The benchmark's multiple is its market cap over its run-rate revenue."""
    bench = snap.get("bench") or {}
    mcap, rr, mult = num(bench.get("mcap")), num(bench.get("rr")), num(bench.get("mult"))
    if not (mcap and rr and mult):
        return [{"what": "the benchmark has no market cap, run-rate or multiple to check"}]
    expected = mcap / rr
    if abs(expected / mult - 1.0) > tol:
        return [{"what": "bench.mult is not bench.mcap / bench.rr", "mult": mult, "expected": round(expected, 3)}]
    return []


def revenue_pairs(snap: dict, protocols: Iterable[dict]) -> list[Pair]:
    """A parent app is the sum of its children's 30-day revenue, a leaf is the
    one protocol with its id -- DefiLlama's own grouping, which the page copies."""
    protocols = list(protocols)
    children: dict[str, float] = {}
    by_id: dict[str, float] = {}
    for p in protocols:
        total = num(p.get("total30d")) or 0.0
        if p.get("parentProtocol"):
            children[p["parentProtocol"]] = children.get(p["parentProtocol"], 0.0) + total
        if p.get("defillamaId") is not None:
            by_id[str(p["defillamaId"])] = total
    out = []
    for app in snap["apps"]:
        key = str(app.get("key") or "")
        if key.startswith("parent#"):
            source = children.get(key)
        elif key.startswith("leaf#"):
            source = by_id.get(key.split("#", 1)[1])
        else:
            source = None
        if source is not None:
            out.append((label(app), num(app.get("rev30d")), source))
    return out


def pair_addresses(snap: dict) -> list[tuple[str, str]]:
    out = []
    for app in snap["apps"]:
        pair = (app.get("links") or {}).get("pair") or {}
        if pair.get("chain") and pair.get("address"):
            out.append((str(pair["chain"]), str(pair["address"])))
    return out


def liquidity_pairs(snap: dict, dex_pairs: dict) -> list[Pair]:
    out = []
    for app in snap["apps"]:
        pair = (app.get("links") or {}).get("pair") or {}
        if not (pair.get("chain") and pair.get("address")):
            continue
        source = dex_pairs.get((str(pair["chain"]), str(pair["address"]).lower()))
        if source is not None:
            out.append((label(app), num((app.get("liq") or {}).get("pair_liq_usd")),
                        num((source.get("liquidity") or {}).get("usd"))))
    return out


# -- judging a column of pairs --------------------------------------------------

def deviation_summary(pairs: Iterable[Pair], *, tail: float) -> dict:
    """How far the page is from the source, over the rows where both are real
    positive numbers. A row with a zero or missing side is not comparable and is
    counted, not dropped: a source that lost rows is a finding of its own."""
    compared, skipped = [], []
    for name, page, source in pairs:
        if page is None or source is None or page <= 0 or source <= 0:
            skipped.append(name)
            continue
        compared.append((abs(page / source - 1.0), name, page, source))
    compared.sort(reverse=True)
    devs = [d for d, *_ in compared]
    n = len(devs)
    return {
        "n": n,
        "skipped": len(skipped),
        "median": statistics.median(devs) if devs else None,
        "p90": sorted(devs)[int(0.9 * (n - 1))] if devs else None,
        "tail": tail,
        "over_tail": sum(1 for d in devs if d > tail),
        "worst": [{"row": name, "page": page, "source": source, "dev": round(d, 4)}
                  for d, name, page, source in compared[:8]],
    }


def judge_deviation(summary: dict, total: int, *, min_compared_share: float,
                    max_median: float, max_tail_share: float) -> tuple[str, str]:
    """("passed" | "failed" | "inconclusive", why). A column is judged as a
    population: one coin off by 30 % is the world moving or a source correcting
    itself (CoinGecko re-estimated PHAR's supply down by a fifth the day this was
    written); a median that has moved, or a tenth of the rows off, is a pipeline."""
    n = summary["n"]
    if total <= 0 or n < min_compared_share * total:
        return "inconclusive", (f"only {n} of {total} rows could be compared "
                                f"({summary['skipped']} had no usable side); "
                                f"needs {min_compared_share:.0%}")
    share = summary["over_tail"] / n
    where = (f"median {summary['median']:.1%}, p90 {summary['p90']:.1%}, "
             f"{summary['over_tail']} of {n} rows off by more than {summary['tail']:.0%}")
    if summary["median"] > max_median:
        return "failed", f"median deviation above {max_median:.0%}: {where}"
    if share > max_tail_share:
        return "failed", f"more than {max_tail_share:.0%} of rows far off: {where}"
    return "passed", where


# -- the page against itself ----------------------------------------------------

def upside_breaches(snap: dict, *, rel_tol: float = 0.01,
                    abs_tol: float = 0.005) -> dict:
    """Every app's upside is the benchmark's multiple divided by its own
    price/revenue multiple, shown capped. All 215 rows held on 2026-09-30.

    `potential_raw = bench.mult / ps`, and `potential = min(potential_raw, cap)`
    where the cap is the value every capped row shows (50). A row is a breach
    only beyond rounding: the smallest numbers are published to three decimals."""
    mult = num((snap.get("bench") or {}).get("mult"))
    if not mult or mult <= 0:
        raise SnapshotUnreadable("the snapshot's benchmark has no multiple")
    # The cap is what most capped rows show. Taking the largest would let one
    # row that shows too much define the cap it is judged against (found by the
    # negative control: a capped row showing 80 beside rows showing 50).
    shown_capped = [round(v, 3) for v in (num(a.get("potential")) for a in snap["apps"]
                                            if a.get("bench_capped")) if v is not None]
    counts: dict[float, int] = {}
    for v in shown_capped:
        counts[v] = counts.get(v, 0) + 1
    cap = min(counts, key=lambda v: (-counts[v], v)) if counts else None
    breaches, checked = [], 0
    for app in snap["apps"]:
        ps, raw, shown = num(app.get("ps")), num(app.get("potential_raw")), num(app.get("potential"))
        if not ps or ps <= 0 or raw is None or shown is None:
            continue
        checked += 1
        expected = mult / ps
        if abs(expected - raw) > max(abs_tol, rel_tol * abs(raw)):
            breaches.append({"row": label(app), "what": "potential_raw is not bench.mult / ps",
                             "raw": raw, "expected": round(expected, 4)})
        want = raw if cap is None else min(raw, cap)
        if abs(want - shown) > max(0.06, rel_tol * abs(want)):
            breaches.append({"row": label(app), "what": "shown upside is not min(raw, cap)",
                             "shown": shown, "expected": round(want, 4)})
    return {"checked": checked, "cap": cap, "multiple": mult, "breaches": breaches}


def mean_of_last(values: list, count: int = 4, minimum: int = 3) -> float | None:
    real = [v for v in values[-count:] if isinstance(v, (int, float))]
    return sum(real) / len(real) if len(real) >= minimum else None


def altseason_breaches(snap: dict) -> dict:
    """The altseason numbers follow their own published rules.

    * the composite index is the weighted mean of rotation and euphoria, with the
      weights the snapshot publishes in `altseason_cycle.rules`;
    * the breadth line in the headline is the 4-week mean of the weekly history;
    * `beat / n` is the latest breadth, and `altseason.index` is the same number.
    A field that is missing is reported as unread, never as agreeing."""
    cyc = snap.get("altseason_cycle") or {}
    alt = snap.get("altseason") or {}
    rules = cyc.get("rules") or {}
    breaches, unread = [], []

    rot, eup, index = num(cyc.get("rotation")), num(cyc.get("euphoria")), num(cyc.get("index"))
    w_rot, w_eup = num(rules.get("rot_weight")), num(rules.get("euph_weight"))
    if None in (rot, eup, index, w_rot, w_eup) or (w_rot + w_eup) <= 0:
        unread.append("composite: rotation, euphoria, index or their weights missing")
    else:
        expected = (w_rot * rot + w_eup * eup) / (w_rot + w_eup)
        if abs(expected - index) > 0.6:
            breaches.append({"what": "the altseason index is not its weighted rotation and euphoria",
                             "index": index, "expected": round(expected, 2)})

    breadth = (cyc.get("components") or {}).get("breadth") or {}
    history = [row[1] for row in alt.get("history") or [] if isinstance(row, list) and len(row) > 1]
    mean4, shown4 = mean_of_last(history), num(breadth.get("mean4"))
    if mean4 is None or shown4 is None:
        unread.append("breadth: no 4-week history or no mean4")
    elif abs(mean4 - shown4) > 1.0:
        breaches.append({"what": "breadth mean4 is not the mean of the last four weeks",
                         "mean4": shown4, "expected": round(mean4, 1)})

    beat, n, value = num(breadth.get("beat")), num(breadth.get("n")), num(breadth.get("value"))
    if None in (beat, n, value) or not n:
        unread.append("breadth: beat, n or value missing")
    elif abs(100.0 * beat / n - value) > 0.51:
        breaches.append({"what": "breadth value is not beat / n",
                         "value": value, "expected": round(100.0 * beat / n, 2)})

    latest = num(alt.get("index"))
    if latest is None or value is None:
        unread.append("altseason.index or breadth.value missing")
    elif abs(latest - value) > 0.51:
        breaches.append({"what": "altseason.index and the breadth component differ",
                         "altseason_index": latest, "breadth_value": value})
    return {"breaches": breaches, "unread": unread}


def duplicate_tickers(snap: dict) -> dict[str, list[dict]]:
    """Tickers shared by more than one app: the ones a symbol route cannot tell
    apart. 2026-09-30: INDEX, MET, EDGE and UP."""
    by_symbol: dict[str, list[dict]] = {}
    for app in snap["apps"]:
        by_symbol.setdefault(str(app.get("symbol")), []).append({
            "key": app.get("key"), "name": app.get("name"), "slug": app.get("slug"),
            "mcap": num(app.get("mcap")), "degen_ok": bool(app.get("degen_ok"))})
    return {s: rows for s, rows in by_symbol.items() if len(rows) > 1}


def pick_identity_breaches(picks: list[dict], coins: dict[str, dict], *,
                           mcap_tol: float = 0.05) -> list[dict]:
    """A Degen pick's own symbol must open the coin the pick names. `coins` maps
    a symbol to what the coin route answered for it. A pick whose symbol opens a
    different name, or a market cap another coin would have, is a breach; a coin
    that could not be read at all is reported as such, not as matching."""
    out = []
    for pick in picks:
        symbol = pick.get("symbol")
        record = coins.get(symbol)
        if not isinstance(record, dict):
            out.append({"row": symbol, "what": "the coin route could not be read"})
            continue
        named, opened = str(pick.get("name") or "").casefold(), str(record.get("name") or "").casefold()
        pick_cap, coin_cap = num(pick.get("market_cap")), num(record.get("market_cap"))
        wrong_cap = (pick_cap and coin_cap and abs(coin_cap / pick_cap - 1.0) > mcap_tol)
        if named != opened or wrong_cap:
            out.append({"row": symbol, "what": "the symbol opens another coin",
                        "pick": pick.get("name"), "pick_market_cap": pick_cap,
                        "opens": record.get("name"), "opens_market_cap": coin_cap})
    return out


# -- the audit itself -----------------------------------------------------------

def _stats(values: list[float]) -> dict:
    return ({"n": len(values), "median": round(statistics.median(values), 2),
             "max": round(max(values), 2)} if values else {"n": 0})


def freshness(snap: dict) -> dict:
    gen = snap.get("generated_at") or 0
    hours = lambda ts: (gen - ts) / HOUR if isinstance(ts, (int, float)) else None
    prices = [h for h in (hours(a.get("market_price_ts")) for a in snap["apps"]) if h is not None]
    supply = [h for h in (hours(a.get("market_supply_as_of_ts")) for a in snap["apps"]) if h is not None]
    sources: dict[str, int] = {}
    for a in snap["apps"]:
        sources[str(a.get("market_source"))] = sources.get(str(a.get("market_source")), 0) + 1
    excluded = snap.get("excluded") or {}
    return {"price_age_h": _stats(prices), "supply_age_h": _stats(supply),
            "supply_older_than_24h": sum(1 for h in supply if h > 24),
            "market_source": sources,
            "market_fetch_failed": excluded.get("market_fetch_failed_count"),
            "market_from_defillama": excluded.get("market_llama_price_count"),
            "fetch_warnings": snap.get("fetch_warning_count")}


def coverage(snap: dict) -> dict:
    apps = snap["apps"]
    meta = snap.get("dlevel_meta") or {}
    chart = snap.get("chart_meta") or {}
    return {"apps": len(apps),
            "checks_run": meta.get("checks_run"),
            "level_range_over_two": meta.get("range_over_two"),
            "emissions_known": sum(1 for a in apps if a.get("emissions30d") is not None),
            "unlock_present": sum(1 for a in apps if a.get("unlock")),
            "chart_scored": (chart.get("daily_status") or {}).get("scored"),
            "pool_thin": sum(1 for a in apps if (a.get("liq") or {}).get("ok") is False),
            "history_under_180d": sum(1 for a in apps if (a.get("hist_days") or 0) < 180),
            "vetted": sum(1 for a in apps if a.get("reliable")),
            "not_vetted_why": _count(r for a in apps for r in (a.get("reliable_fail") or []))}


def _count(items: Iterable) -> dict:
    out: dict = {}
    for item in items:
        out[item] = out.get(item, 0) + 1
    return dict(sorted(out.items(), key=lambda kv: -kv[1]))


def upside_table(snap: dict, top: int = 12) -> dict:
    apps = snap["apps"]
    capped = [a for a in apps if a.get("bench_capped")]
    vetted = sorted((a for a in apps if a.get("reliable")), key=lambda a: -(num(a.get("potential")) or 0))
    rows = []
    for a in vetted[:top]:
        mcap, fdv = num(a.get("mcap")), num(a.get("fdv"))
        rows.append({"row": label(a), "shown": num(a.get("potential")), "raw": num(a.get("potential_raw")),
                     "if_all_tokens_out": num(a.get("potential_fdv")), "mcap": mcap,
                     "float_pct": round(100 * mcap / fdv, 1) if mcap and fdv else None,
                     "picked": bool(a.get("degen_ok"))})
    return {"at_cap": len(capped), "cap": max((num(a.get("potential")) or 0) for a in capped) if capped else None,
            "raw_range_at_cap": ([round(min(num(a.get("potential_raw")) for a in capped), 1),
                                  round(max(num(a.get("potential_raw")) for a in capped), 1)]
                                 if capped else None),
            "top_vetted": rows}


def picks_table(snap: dict, coins: dict[str, dict] | None = None) -> list[dict]:
    """The shortlist, read by key -- never by ticker, which two apps can share --
    with what a degen would ask of each: can it be bought at size, where does its
    liquidity live, does it pay after emissions, is there an exit flag."""
    by_key = {a.get("key"): a for a in snap["apps"]}
    rules = snap.get("risk_rules") or {}
    rows = []
    for key in ((snap.get("degen") or {}).get("shortlist") or []):
        a = by_key.get(key)
        if not a:
            rows.append({"row": key, "what": "on the shortlist but not in the snapshot"})
            continue
        liq, level = a.get("liq") or {}, a.get("dlevel") or {}
        mcap, fdv = num(a.get("mcap")), num(a.get("fdv"))
        impact = num(liq.get("impact_pct"))
        coin = (coins or {}).get(a.get("symbol")) or {}
        rows.append({
            "row": label(a), "upside": num(a.get("potential")), "if_all_out": num(a.get("potential_fdv")),
            "mcap": mcap, "float_pct": round(100 * mcap / fdv, 1) if mcap and fdv else None,
            "impact_10k_pct": impact, "pool_liq": num(liq.get("pair_liq_usd")),
            "liquidity_from": liq.get("source"),
            "buyable_on_chain": bool(liq.get("source") == "dex" and impact is not None
                                     and impact <= (rules.get("max_impact_pct") or 3.0)),
            "level": level.get("level"), "level_range": [level.get("low"), level.get("high")],
            "unscanned_checks": level.get("missing"),
            "history_days": a.get("hist_days"), "young": bool(a.get("young")),
            "vetted": bool(a.get("reliable")),
            "earnings_after_emissions_30d": num(a.get("earnings30d")),
            "printed": bool(a.get("printed")),
            "exit_flags": a.get("exit_flags") or [],
            "price_30d_pct": num((a.get("cg") or {}).get("chg30d")),
            "tradeable_here": bool(coin.get("trade_url")) if coin else None})
    return rows


def backtest_admission(snap: dict) -> dict:
    bt = snap.get("backtest_summary") or {}
    h3 = bt.get("h3") or {}
    ledger = snap.get("picks_ledger") or {}
    cohorts = ledger.get("cohorts") or []
    return {"verdict": bt.get("verdict"), "verdict_text": bt.get("verdict_text"),
            "ranking_ic": (bt.get("h1") or {}).get("text"),
            "top_fifth_lift": (bt.get("h2") or {}).get("text"),
            "passing_gates_vs_rest_median": h3.get("diff_median"), "passing_gates_ci90": h3.get("ci90"),
            "passing_tokens": h3.get("n_pass_tokens"),
            "base_rate_3x": (((bt.get("base_rates") or {}).get("all") or {}).get("p3") or {}).get("p"),
            "base_rate_10x": (((bt.get("base_rates") or {}).get("all") or {}).get("p10") or {}).get("p"),
            "live_ledger_ready": ledger.get("ready"),
            "live_cohorts": len(cohorts),
            "live_picks_tracked": sum((c.get("n") or 0) for c in cohorts)}


def pegged_like(rows: Iterable[dict]) -> list[dict]:
    """Members of the altseason universe that cannot be an altcoin beating BTC:
    priced near a currency unit and barely moving over a month (tokenised
    money-market funds, a home-equity-loan token). A heuristic for the audit
    report -- it lists suspects, it does not decide."""
    out = []
    for m in rows:
        price, month = num(m.get("current_price")), num(m.get("price_change_percentage_30d_in_currency"))
        if price is not None and month is not None and 0.9 < price < 1.6 and abs(month) < 3.0:
            out.append({"id": m.get("id"), "price": price, "change_30d_pct": round(month, 2),
                        "mcap": num(m.get("market_cap"))})
    return out


def altseason_facts(snap: dict, universe_rows: Iterable[dict] | None = None) -> dict:
    cyc, alt = snap.get("altseason_cycle") or {}, snap.get("altseason") or {}
    breadth = (cyc.get("components") or {}).get("breadth") or {}
    facts = {"cycle_index": cyc.get("index"), "phase": cyc.get("phase"),
             "rotation": cyc.get("rotation"), "euphoria": cyc.get("euphoria"),
             "breadth_latest_week": breadth.get("value"), "breadth_4w_mean_shown": breadth.get("mean4"),
             "breadth_three_months_ago": alt.get("three_months_ago"),
             "universe_size": len(alt.get("alt50") or []),
             "formula": altseason_breaches(snap)}
    if universe_rows is not None:
        suspects = pegged_like(universe_rows)
        facts["pegged_like_in_universe"] = suspects
        facts["pegged_share"] = round(len(suspects) / max(1, len(alt.get("alt50") or [])), 3)
    return facts


def themes_facts(snap: dict) -> dict:
    """How much the sector tags tell apart: a tag carried by most rows ranks
    nothing. 2026-09-30: 10 of 12 themes were `hot`, and the community data
    behind "talked about" was 460 people and 1,163 messages in seven days."""
    themes = [t for t in snap.get("themes") or [] if isinstance(t, dict)]
    belief = snap.get("belief") or {}
    return {"themes": len(themes), "hot_now": sum(1 for t in themes if t.get("hot")),
            "belief_people": belief.get("total_people"),
            "belief_messages": belief.get("total_messages")}


def chains_facts(snap: dict) -> dict:
    """How much of a big chain's raw fees survive the guards before it is valued:
    for the chains the benchmark rule turns away, `guard_cut_share` is the part
    thrown out. 2026-09-30: over half for 19 of 21."""
    bench = snap.get("bench_chains") or {}
    out = [c for c in bench.get("not_eligible") or [] if isinstance(c, dict)]
    return {"chains": len(snap.get("chains") or []), "priced": bench.get("n_priced"),
            "turned_away_from_benchmark": len(out),
            "fees_mostly_discarded": sum(1 for c in out if (c.get("guard_cut_share") or 0) > 0.5)}


def source_columns(snap: dict, sources: dict | None) -> dict:
    """Each cross-check as a summary. `sources` holds what was fetched:
    {"coingecko": rows, "llama": protocols, "dexscreener": (pairs, failed)};
    a source that was not fetched is absent and its column is "not fetched"."""
    sources = sources or {}
    cols: dict = {}
    if "coingecko" in sources:
        for name, pairs, tail in (("supply_vs_coingecko", supply_pairs(snap, sources["coingecko"]), 0.25),
                                  ("price_vs_coingecko", price_pairs(snap, sources["coingecko"]), 0.30)):
            cols[name] = deviation_summary(pairs, tail=tail)
    if "llama" in sources:
        cols["revenue_vs_defillama"] = deviation_summary(revenue_pairs(snap, sources["llama"]), tail=0.25)
    if "dexscreener" in sources:
        found, failed = sources["dexscreener"]
        cols["pool_liquidity_vs_dexscreener"] = {
            **deviation_summary(liquidity_pairs(snap, found), tail=0.50),
            "pairs_asked": len(pair_addresses(snap)), "chains_failed": failed}
    return cols


def build_report(snap: dict, *, sources: dict | None = None, picks_api: list | None = None,
                 coins_api: dict | None = None, now: float | None = None) -> dict:
    """The whole audit as one dict. Pure: give it the snapshot and whatever was
    fetched, and it says what it can. Missing inputs leave their section empty."""
    now = time.time() if now is None else now
    report = {
        "at": now, "snapshot_generated_at": snap.get("generated_at"),
        "snapshot_age_h": round(age_hours(snap, now) or 0.0, 2),
        "freshness": freshness(snap), "coverage": coverage(snap),
        "upside": upside_table(snap), "upside_formula": upside_breaches(snap),
        "picks": picks_table(snap, coins_api), "tickers_shared": duplicate_tickers(snap),
        "backtest": backtest_admission(snap), "themes": themes_facts(snap), "chains": chains_facts(snap),
        "altseason": altseason_facts(snap, (sources or {}).get("altseason_universe")),
        "sources": source_columns(snap, sources),
    }
    if picks_api is not None and coins_api is not None:
        report["pick_identity"] = pick_identity_breaches(picks_api, coins_api)
    return report


def report_lines(report: dict) -> list[str]:
    """The few lines /lab shows. English, numbers first."""
    lines = []
    src = report.get("sources") or {}
    for name, col in src.items():
        if col.get("n"):
            lines.append(f"{name.replace('_', ' ')}: median off {col['median']:.1%}, "
                         f"{col['over_tail']} of {col['n']} beyond {col['tail']:.0%}")
    identity = report.get("pick_identity")
    if identity is not None:
        lines.append(f"picks that open another coin: {len(identity)}"
                     + (f" ({', '.join(b['row'] for b in identity)})" if identity else ""))
    fm = report.get("upside_formula") or {}
    lines.append(f"upside formula: {len(fm.get('breaches') or [])} breaches in {fm.get('checked', 0)} apps")
    picks = report.get("picks") or []
    if picks:
        lines.append(f"{sum(1 for p in picks if not p.get('buyable_on_chain'))} of {len(picks)} picks "
                     f"cannot be bought on-chain at $10K")
    bt = report.get("backtest") or {}
    lines.append(f"their own backtest: {bt.get('verdict')}; live picks tracked: {bt.get('live_picks_tracked')}")
    alt = report.get("altseason") or {}
    if alt.get("cycle_index") is not None:
        lines.append(f"altseason cycle {alt['cycle_index']} ({alt.get('phase')}); latest breadth "
                     f"{alt.get('breadth_latest_week')}, shown 4w mean {alt.get('breadth_4w_mean_shown')}")
    return lines


def _pct(x) -> str:
    return "—" if x is None else f"{x:.1%}"


def _money(x) -> str:
    return "—" if x is None else f"${x:,.0f}"


def render_markdown(report: dict) -> str:
    """The audit's tables, for the operator. Numbers first; no explanation beyond
    the column names -- the explanation belongs in the narrative report."""
    out = ["# Gem Screener audit, generated", ""]
    fr = report["freshness"]
    out += [f"Snapshot age {report['snapshot_age_h']} h. Price age median {fr['price_age_h'].get('median')} h, "
            f"supply age median {fr['supply_age_h'].get('median')} h "
            f"({fr['supply_older_than_24h']} rows over 24 h). "
            f"Market source: {fr['market_source']}. Market fetch failed: {fr['market_fetch_failed']}, "
            f"prices from DefiLlama: {fr['market_from_defillama']}.", ""]
    cv = report["coverage"]
    out += ["## Coverage", f"{cv['apps']} apps; vetted {cv['vetted']}; level range wider than 2: {cv['level_range_over_two']}; "
            f"emissions known {cv['emissions_known']}; unlock schedule {cv['unlock_present']}; chart scored {cv['chart_scored']}; "
            f"history under 180 d: {cv['history_under_180d']}.", f"Checks run: {cv['checks_run']}", ""]
    up = report["upside"]
    out += ["## Upside", f"{up['at_cap']} rows sit at the {up['cap']}x cap (raw {up['raw_range_at_cap']}).", "",
            "| row | shown | raw | if all tokens out | mcap | float | pick |", "|---|---|---|---|---|---|---|"]
    for r in up["top_vetted"]:
        out.append(f"| {r['row']} | {r['shown']} | {r['raw']} | {r['if_all_tokens_out']} | {_money(r['mcap'])} | "
                   f"{r['float_pct']}% | {'yes' if r['picked'] else ''} |")
    fm = report["upside_formula"]
    out += ["", f"Formula `potential_raw = bench.mult / ps`, capped: {len(fm['breaches'])} breaches in {fm['checked']} rows.", "",
            "## Degen picks", "| row | upside | if all out | mcap | float | $10K impact | liquidity from | on-chain | level (range) | "
            "earnings after emissions | exit flags | 30d |", "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for p in report["picks"]:
        if "what" in p:
            out.append(f"| {p['row']} | {p['what']} |")
            continue
        out.append(f"| {p['row']} | {p['upside']} | {p['if_all_out']} | {_money(p['mcap'])} | {p['float_pct']}% | "
                   f"{p['impact_10k_pct']}% | {p['liquidity_from']} | {'yes' if p['buyable_on_chain'] else 'no'} | "
                   f"{p['level']} ({p['level_range'][0]}-{p['level_range'][1]}) | {_money(p['earnings_after_emissions_30d'])} | "
                   f"{', '.join(p['exit_flags']) or '—'} | {p['price_30d_pct']}% |")
    if "pick_identity" in report:
        out += ["", f"Picks whose symbol opens another coin: {report['pick_identity'] or 'none'}"]
    out += ["", f"Tickers shared by two apps: {sorted(report['tickers_shared'])}", "", "## Against independent sources"]
    for name, col in (report["sources"] or {}).items():
        out.append(f"- {name}: n {col['n']}, median {_pct(col.get('median'))}, p90 {_pct(col.get('p90'))}, "
                    f"{col['over_tail']} beyond {col['tail']:.0%}; worst {[(w['row'], w['dev']) for w in col['worst'][:3]]}")
    bt = report["backtest"]
    out += ["", "## Their own backtest", f"{bt['verdict']}: {bt['verdict_text']}", f"Ranking: {bt['ranking_ic']}; top fifth: {bt['top_fifth_lift']}.",
            f"Gate-passing coins vs the rest, median over six months: {bt['passing_gates_vs_rest_median']} "
            f"(90% CI {bt['passing_gates_ci90']}, {bt['passing_tokens']} coins). 3x base rate {_pct(bt['base_rate_3x'])}, "
            f"10x {_pct(bt['base_rate_10x'])}. Live ledger ready: {bt['live_ledger_ready']}, picks tracked {bt['live_picks_tracked']}.", "",
            "## Altseason", json.dumps(report["altseason"], ensure_ascii=False)[:1500], ""]
    return "\n".join(out)
