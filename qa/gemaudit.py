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
import urllib.parse
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
    """The benchmark's multiple is its market cap over its run-rate revenue.

    A benchmark whose market cap, run-rate or multiple cannot be read is
    `SnapshotUnreadable`, as a missing multiple is in `upside_breaches`: an
    unread field is not a broken formula (C06, deep pass of 2026-09-30)."""
    bench = snap.get("bench") or {}
    mcap, rr, mult = num(bench.get("mcap")), num(bench.get("rr")), num(bench.get("mult"))
    if not (mcap and rr and mult):
        raise SnapshotUnreadable("the benchmark has no market cap, run-rate or multiple to check")
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

def shown_cap(snap: dict) -> float | None:
    """The upside cap: the value most capped rows show. Taking the largest would
    let one row that shows too much define the cap it is judged against (found by
    the negative control: a capped row showing 80 beside rows showing 50). One
    rule for the check and for the report's table (R06, deep pass of 2026-09-30)."""
    shown = [round(v, 3) for v in (num(a.get("potential")) for a in snap["apps"]
                                     if a.get("bench_capped")) if v is not None]
    counts: dict[float, int] = {}
    for v in shown:
        counts[v] = counts.get(v, 0) + 1
    return min(counts, key=lambda v: (-counts[v], v)) if counts else None


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
    cap = shown_cap(snap)
    breaches, checked = [], 0
    for app in snap["apps"]:
        ps, raw, shown = num(app.get("ps")), num(app.get("potential_raw")), num(app.get("potential"))
        if not ps or ps <= 0 or shown is None:
            continue
        checked += 1
        expected = mult / ps
        if raw is None:
            # A row that shows an upside without its raw value is still held to
            # min(bench.mult / ps, cap) -- the contract is "every row that has a ps"
            # (deep pass 2026-10-02, T08); it used to be skipped.
            raw = expected
        elif abs(expected - raw) > max(abs_tol, rel_tol * abs(raw)):
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
    * the breadth line in the headline is the 4-week mean of the weekly series the
      CYCLE publishes (`altseason_cycle.series.breadth`), and its value is that
      series' last point;
    * `beat / n` is that latest breadth.
    NOT held: `altseason.index` equal to the breadth component. It is a second,
    older block on another basis and runs 2-4 points above the cycle's series every
    week; nothing the snapshot publishes says the two are one number (2026-10-04).
    A field that is missing is reported as unread, never as agreeing."""
    cyc = snap.get("altseason_cycle") or {}
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
    series = (cyc.get("series") or {}).get("breadth")
    history = [v for v in series] if isinstance(series, list) else []
    mean4, shown4 = mean_of_last(history), num(breadth.get("mean4"))
    if mean4 is None or shown4 is None:
        unread.append("breadth: no 4-week series or no mean4")
    elif abs(mean4 - shown4) > 1.0:
        breaches.append({"what": "breadth mean4 is not the mean of the last four weeks",
                         "mean4": shown4, "expected": round(mean4, 1)})

    beat, n, value = num(breadth.get("beat")), num(breadth.get("n")), num(breadth.get("value"))
    if None in (beat, n, value) or not n:
        unread.append("breadth: beat, n or value missing")
    elif abs(100.0 * beat / n - value) > 0.51:
        breaches.append({"what": "breadth value is not beat / n",
                         "value": value, "expected": round(100.0 * beat / n, 2)})

    last = next((v for v in reversed(history) if isinstance(v, (int, float))), None)
    if last is not None and value is not None and abs(last - value) > 0.51:
        breaches.append({"what": "breadth value is not the last point of its own series",
                         "value": value, "last": last})
    return {"breaches": breaches, "unread": unread}


# --- the panels beside the rank: Sectors, the Altseason words, Retail (2026-10-02) -------------
#
# Three independent audits of the Altseason panel, the Retail panel and the Sectors tab found
# the numbers faithful to their sources and four places where the page says two things at once.
# They are held here as pure functions over what the page publishes; NOT asserted is how
# Cymetica fixes any of them.

SNAPSHOT_API = "/api/v1/gem-screener"
ALTSEASON_API = "/api/v1/gem-screener/altseason"

LIVE_COVERAGE_FLOOR = 0.95
"""A theme is priced on one date when every member has a live point, none does (the
fallback their own warning names: "no live point: last weekly close"), or at least this
share of its weight does. 0.95 leaves room for a delisted coin; 0.05 (one Zebec in a
twelve-coin RWA basket) is a basket priced on two dates."""

ALTS_MAJORITY = 60.0
"""A week in which at least this share of the top 50 beat BTC is not one in which "only
BTC runs"."""


def theme_live_coverage(api: dict) -> dict:
    """Which themes were priced on two dates. `theme_prices.live` is the live point per
    coin (empty for a coin whose price call failed); a theme whose weight is covered
    only in part has a return that carries the live move of the coins that had one and
    the weekly close of the rest. On 2026-10-02 (snapshot 1790921065) CoinGecko answered
    403 and 429, 11 of 320 coins had a live point, and RWA (1 of 12) and DePIN (1 of 15)
    each showed about twice what their weekly closes give. Returns every theme read,
    those below the floor under `partial`, and what could not be read under `unread`."""
    live = (api.get("theme_prices") or {}).get("live")
    themes = api.get("themes")
    if not isinstance(live, dict) or not isinstance(themes, list):
        return {"themes": [], "partial": [], "unread": ["theme_prices.live or themes missing"]}
    rows, partial, unread = [], [], []
    for theme in themes:
        members = [m for m in theme.get("members") or [] if isinstance(m, dict) and m.get("id")]
        weights = [(m["id"], num(m.get("w"))) for m in members]
        total = sum(w for _, w in weights if w)
        if not members or total <= 0:
            unread.append(f"{theme.get('key')}: no members with a weight")
            continue
        covered = sum(w for member_id, w in weights if w and member_id in live)
        share = covered / total
        row = {"theme": theme.get("key"), "members": len(members),
               "with_live": sum(1 for member_id, _ in weights if member_id in live),
               "weight_share": round(share, 3)}
        rows.append(row)
        if 0 < share < LIVE_COVERAGE_FLOOR:
            partial.append(row)
    return {"themes": rows, "partial": partial, "unread": unread}


def hot_definitions(snap: dict) -> dict:
    """The table and "Hot right now" read `stage == 'hot'`; the theme
    panel prints "This theme is hot." from the older `hot` flag. On 2026-10-02: 4 themes
    against 8. Returns both sets and the themes on which they differ; a snapshot that
    has lost either field is unread -- there is no second definition left to compare."""
    themes = snap.get("themes")
    if not isinstance(themes, list) or not themes:
        return {"flag_hot": [], "stage_hot": [], "disagree": [], "unread": ["themes missing"]}
    if not any("hot" in t for t in themes) or not any("stage" in t for t in themes):
        return {"flag_hot": [], "stage_hot": [], "disagree": [],
                "unread": ["a theme field the two definitions need is gone: "
                           + ("hot" if not any("hot" in t for t in themes) else "stage")]}
    flag = [t["key"] for t in themes if t.get("hot") is True]
    stage = [t["key"] for t in themes if t.get("stage") == "hot"]
    disagree = [t["key"] for t in themes if (t.get("hot") is True) != (t.get("stage") == "hot")]
    return {"flag_hot": flag, "stage_hot": stage, "disagree": disagree, "unread": []}


def phase_word_breaches(alt: dict) -> dict:
    """The Altseason panel prints a phase word and, beside it, the share of the top 50
    that beat BTC that week. "Only BTC runs" over a week in which most of them did is
    false on the panel's own data. Reads `GET /api/v1/gem-screener/altseason`
    (`altseason.series.phase` and `.breadth`, one value per week). On 2026-10-02: 17 of
    155 such weeks, one of them 2024-12-02 at 74 % with OTHERS up from $198bn to $397bn
    in four weeks. A week with no breadth reading is neither agreement nor a breach."""
    block = alt.get("altseason") if isinstance(alt, dict) else None
    series = (block or {}).get("series") or {}
    phases, breadth = series.get("phase"), series.get("breadth")
    if not isinstance(phases, list) or not isinstance(breadth, list) or not phases:
        return {"breaches": [], "weeks_read": 0, "only_btc_weeks": 0,
                "unread": ["altseason.series.phase or .breadth missing"]}
    if len(phases) != len(breadth):
        return {"breaches": [], "weeks_read": 0, "only_btc_weeks": 0,
                "unread": [f"phase has {len(phases)} weeks and breadth {len(breadth)}"]}
    weeks = (block or {}).get("weeks") or list(range(len(phases)))
    read = btc_only = 0
    breaches = []
    for week, phase, value in zip(weeks, phases, breadth):
        reading = num(value)
        if phase is None or reading is None:
            continue
        read += 1
        if phase != "btc_only":
            continue
        btc_only += 1
        if reading >= ALTS_MAJORITY:
            breaches.append({"week": week, "breadth": reading})
    return {"breaches": breaches, "weeks_read": read, "only_btc_weeks": btc_only, "unread": []}


FORMING_MAX_AGE_S = 3600.0
FORMING_TOLERANCE = 0.02


def forming_candle_staleness(analysis: dict, source_close, now: float, *,
                             max_age_s: float = FORMING_MAX_AGE_S,
                             tolerance: float = FORMING_TOLERANCE) -> dict:
    """Is the candle still forming in a Chart Analyzer answer both OLD and wrong?

    `analysis` is `GET /api/v1/chart-analyzer/analyze?...&include_candles=true` for a
    contract; `source_close` the same pool's current candle close at its source (the
    page says "LIVE"). Verdict `old_and_off` when the cache was fetched more than
    `max_age_s` ago and the forming close is more than `tolerance` away from the
    source; `ok` otherwise (a fresh candle that drifted, or an old one that still
    agrees, is no defect); `unread` when a field or the source is missing, or the last
    candle is not forming. On 2026-10-02: fetched 12:24 UTC, read at 14:38 (134 min),
    0.2567 against 0.2707, 5.2% off, with `candles_stale: false` and a LIVE label."""
    import datetime as _dt

    candles = analysis.get("candles") or []
    fetched = analysis.get("candles_fetched_at")
    close = num(candles[-1][4]) if candles and len(candles[-1]) > 4 else None
    ref = num(source_close)
    if not analysis.get("last_candle_forming") or close is None or not ref or not fetched:
        return {"verdict": "unread", "age_s": None, "deviation": None,
                "last_close": close, "source_close": ref}
    try:
        when = _dt.datetime.fromisoformat(str(fetched).replace("Z", "+00:00"))
        if when.tzinfo is None:
            when = when.replace(tzinfo=_dt.timezone.utc)
    except ValueError:
        return {"verdict": "unread", "age_s": None, "deviation": None,
                "last_close": close, "source_close": ref}
    age = now - when.timestamp()
    deviation = abs(close / ref - 1.0)
    verdict = "old_and_off" if (age > max_age_s and deviation > tolerance) else "ok"
    if verdict == "old_and_off" and analysis.get("candles_stale") is True:
        # An old candle that SAYS it is stale is flagged honestly: one of the ways to
        # fix this named in the check's docstring. Only an explicit true counts -- a
        # missing field or `false` beside an old, wrong candle is the defect itself.
        verdict = "ok"
    return {"verdict": verdict, "age_s": age, "deviation": deviation,
            "last_close": close, "source_close": ref, "fetched_at": fetched}


META_TAG = re.compile(r"<meta\b[^>]*>", re.I)
META_ATTR = re.compile(r'([a-zA-Z:_-]+)\s*=\s*"([^"]*)"')
SHARE_TAGS = ("og:image", "twitter:image")


def share_images(page_html: str) -> dict:
    """The preview image a page names for a link posted on X or anywhere else:
    `{"og:image": url, "twitter:image": url}` for the tags it has. On 2026-10-02
    /gem-screener/app named /static/images/og-default.png, which answers 404, and
    the tweet that carried the link showed a grey placeholder instead of a card.
    HTML entities in the URL (&amp;) are undone, as a crawler does."""
    import html as htmllib

    found = {}
    for tag in META_TAG.findall(page_html or ""):
        attrs = {k.lower(): v for k, v in META_ATTR.findall(tag)}
        name = (attrs.get("property") or attrs.get("name") or "").lower()
        if name in SHARE_TAGS and attrs.get("content"):
            found[name] = htmllib.unescape(attrs["content"]).strip()
    return found


SURE_RULE = re.compile(r"Sure:\s*(\d+)\+\s*rows that agree within\s*(\d+)\s*points\.\s*"
                       r"Fairly sure:\s*(\d+)\+\s*rows within\s*(\d+)")


# The wording from 2026-10-02 15:30 UTC, after the report: one JS string, split by a join.
SURE_RULE_WHOLE = re.compile(
    r"Sure:\s*(\d+)\+\s*rows scored and no more than\s*(\d+)\s*points between the highest and the lowest of them\.\s*"
    r"[\s'\"+]*Fairly sure:\s*(\d+)\+\s*rows,\s*no more than\s*(\d+)\s*points")


def _most_within(scores: list[float], span: float) -> int:
    ordered = sorted(scores)
    return max((sum(1 for s in ordered if low <= s <= low + span) for low in ordered), default=0)


def retail_sure_breach(snap: dict, page_text: str) -> dict:
    """"How sure" follows the rule its own tooltip states: Sure = N+ rows that agree
    within S points, Fairly sure = M+ rows within F, otherwise unsure. On 2026-10-02 five
    of six rows sat between 4 and 14 and the panel said unsure, because the code took the
    spread of all six (84). The rule is read from the page's words, never remembered."""
    rule = SURE_RULE.search(page_text or "")
    whole = None if rule else SURE_RULE_WHOLE.search(page_text or "")
    retail = ((snap.get("altseason_cycle") or {}).get("components") or {}).get("retail") or {}
    scores = [s for s in (num((p or {}).get("score")) for p in (retail.get("parts") or {}).values())
              if s is not None]
    shown = (retail.get("sure") or {}).get("code")
    unread = []
    if not rule and not whole:
        unread.append("the page no longer words the 'How sure' rule as 'Sure: N+ rows that agree within S points' "
                      "or 'Sure: N+ rows scored and no more than S points between the highest and the lowest'")
    if not scores or not shown:
        unread.append("retail.parts scores or retail.sure.code missing")
    if unread:
        return {"breach": None, "unread": unread}
    if whole:
        # 2026-10-02: their re-worded tooltip -- every scored row, the spread of all of them.
        sure_n, sure_span, fair_n, fair_span = (int(x) for x in whole.groups())
        spread = max(scores) - min(scores)
        sure_n_ok, fair_n_ok = len(scores) >= sure_n and spread <= sure_span, len(scores) >= fair_n and spread <= fair_span
    else:
        sure_n, sure_span, fair_n, fair_span = (int(x) for x in rule.groups())
        sure_n_ok = _most_within(scores, sure_span) >= sure_n
        fair_n_ok = _most_within(scores, fair_span) >= fair_n
    if sure_n_ok:
        expected = "sure"
    elif fair_n_ok:
        expected = "fairly_sure"
    else:
        expected = "unsure"
    if expected == shown:
        return {"breach": None, "unread": []}
    return {"breach": {"expected": expected, "shown": shown, "scores": sorted(scores),
                       "rule": {"sure": [sure_n, sure_span], "fairly": [fair_n, fair_span]}},
            "unread": []}


SCATTER_RENDERER = re.compile(r"function\s+renderThemeScatter\s*\(")
SCATTER_CAPTION_VAR = re.compile(
    r"(?:var|let|const)\s+([A-Za-z_$][\w$]*)\s*=\s*document\.getElementById\(\s*['\"]scatterSub['\"]\s*\)")
JS_STRING = re.compile(r"'((?:[^'\\\n]|\\.)*)'|\"((?:[^\"\\\n]|\\.)*)\"")
ONE_CLICK = re.compile(r"\b(?:click|tap)(?:\s+or\s+(?:click|tap))?(?:\s+on)?\s+(?:a|any|the)\s+"
                       r"(?:bubble|point|dot)s?\b", re.I)
TWO_STEP = re.compile(r"\b(?:twice|again|second|double|2nd|two\s+clicks|then)\b", re.I)
CLICK_LISTENER = re.compile(r"\.addEventListener\(\s*['\"]click['\"]")
ANY_LISTENER = re.compile(r"\.addEventListener\(")
POINTS_SELECTOR = re.compile(r"closest\(\s*['\"][^'\"]*#themeScatter[^'\"]*['\"]")
PINS_A_CARD = re.compile(r"\b(?:pinHost|pinTipTo|togglePopover)\s*\(")
# A first-click card held to touch: a hover/pointer media query, the event's pointer
# type, or a touch probe -- in the listener, in the statement that registers it, or
# through a name the page computes from one of them.
HOVER_GATE = re.compile(r"matchMedia\(\s*['\"][^'\"]*(?:hover|pointer)[^'\"]*['\"]|pointerType|"
                        r"maxTouchPoints|ontouchstart|firesTouchEvents")
HOVER_GATE_NAME = re.compile(
    r"(?:(?:var|let|const)\s+([A-Za-z_$][\w$]*)\s*=[^;\n]*?|function\s+([A-Za-z_$][\w$]*)\s*\([^)]*\)\s*\{"
    r"[^{}]{0,400}?)(?:" + HOVER_GATE.pattern + ")")


def _js_text(expression: str) -> str:
    """The string literals of a JS expression, joined: what a `+` chain of quoted text
    shows a visitor, less the variables spliced into it."""
    return "".join(a or b for a, b in JS_STRING.findall(expression or "")).replace("\\'", "'")


def sector_click_promise(page_html: str | None) -> dict:
    """Does one click on a Sectors-chart bubble do what the chart's caption says?

    2026-10-04: the caption ends "Click a bubble for the sector.", and a capture-phase
    click listener (their ET-28990 #3) takes `#themeScatter g.pt`, pins the dark card
    that hover already shows and stops the event, so the bubble's own
    `openThemePanel` runs only on the second click. Read from the page's served
    script, never from a browser, so the verdict is about the code a browser runs:

      two_clicks  the caption promises one click AND that listener intercepts the first
                  click on a chart point with no hover/pointer/touch gate
      ok          the caption no longer promises one click, or every such listener is
                  held to touch
      unread      the renderer, its caption or its bubble click is not where it was read,
                  or the listener is gone: whether one click now opens the sector is then
                  a question for a browser, and a static read does not answer it

    NOT read: which way a hover gate points (a gate is taken as the fix it would be),
    or anything the browser does that the served script does not say.
    """
    out = {"verdict": "unread", "why": "", "caption": None, "caption_at": None,
           "interceptor": None, "interceptor_at": None}
    page = page_html or ""
    found = SCATTER_RENDERER.search(page)
    if not found:
        out["why"] = "the page has no renderThemeScatter, so the Sectors chart was not read"
        return out
    end = page.find("\nfunction ", found.end())
    region = page[found.start(): end if end != -1 else found.start() + 40000]

    names = {m.group(1) for m in SCATTER_CAPTION_VAR.finditer(region)} | {"sub"}
    captions = []
    for name in names:
        for m in re.finditer(r"\b" + re.escape(name) + r"\.textContent\s*=(?!=)\s*([^;]*);(\s*return\b)?", region):
            if not m.group(2):                       # `...; return;` is the not-enough-data branch
                captions.append((found.start() + m.start(), _js_text(m.group(1))))
    if not captions:
        out["why"] = "renderThemeScatter no longer writes the chart's caption as textContent"
        return out
    if not re.search(r"\.addEventListener\(\s*['\"]click['\"][^;]*?openThemePanel\s*\(", region):
        out["why"] = "no click on a chart bubble opens openThemePanel any more"
        return out
    out["caption_at"], text = captions[-1]
    sentences = [s.strip() for s in re.findall(r"[^.]*\.?", text) if s.strip()]
    promise = next((s for s in sentences if ONE_CLICK.search(s)), None)
    out["caption"] = promise or text.strip()
    if not promise or TWO_STEP.search(promise):
        out["verdict"], out["why"] = "ok", "the caption does not promise that one click opens the sector"
        return out

    gate_names = {a or b for a, b, *_ in HOVER_GATE_NAME.findall(page)} - {""}
    intercepting = []
    for m in CLICK_LISTENER.finditer(page):
        nxt = ANY_LISTENER.search(page, m.end())
        stop = min(nxt.start() if nxt else len(page), m.start() + 2500)
        body = page[m.start(): stop]
        closed = body.find("}, true)")                  # the listener ends here, not at the next one
        if closed > 0:
            body = body[: closed + len("}, true)")]
        if not (POINTS_SELECTOR.search(body) and PINS_A_CARD.search(body)
                and re.search(r"stopPropagation\s*\(", body)):
            continue
        before = page[max(0, m.start() - 300): m.start()]
        cut = max(before.rfind(";"), before.rfind("}"), before.rfind("*/"))
        statement = before[cut + 1:] + body
        gated = bool(HOVER_GATE.search(statement)) or any(
            re.search(r"(?<![\w$.])" + re.escape(n) + r"(?![\w$])", statement) for n in gate_names)
        line_start = page.rfind("\n", 0, m.start()) + 1
        code = page[line_start: m.start() + len(body)]
        close = code.rfind("}, true)")
        code = code[: close + len("}, true);")] if close > 0 else code
        intercepting.append({"at": line_start, "gated": gated, "code": code.strip()[:700]})
    if not intercepting:
        out["why"] = ("the first-click listener on #themeScatter points is no longer on the page; "
                      "whether one click now opens the sector needs a browser")
        return out
    bare = [i for i in intercepting if not i["gated"]]
    first = (bare or intercepting)[0]
    out["interceptor"], out["interceptor_at"] = first["code"], first["at"]
    if bare:
        out["verdict"] = "two_clicks"
        out["why"] = ("the caption promises one click, and a capture-phase click listener pins the hover "
                      "card on a chart point and stops the event, on every device")
    else:
        out["verdict"], out["why"] = "ok", "the first-click card is held to touch"
    return out


# --- the Supply line under "Dilution, 12 months" names its source (2026-10-18) ------------------

DILUTION_LINE = re.compile(
    r"month_tokens\)\s*\+\s*' new '.{0,80}?' a month\s*·\s*'\s*\+\s*"
    r"(?P<wrap>\(\s*)?\(\s*[\w$]+\.kinds\s*\|\|\s*\[\]\s*\)\.join\(", re.S)
"""The served line under the 12-month figure, "N new X a month · " + kinds joined: the Supply
column's tooltip (saDilLine) and the drawer card's tile. What follows the join is read by
`_dilution_fallback` (A07, deep pass 2026-10-25: the match stopped at `.join(`, so a fallback drawn
after it was never seen)."""
DILUTION_GATED = re.compile(
    r"month_tokens\)\s*\+\s*' new '.{0,80}?' a month(?:\s*·\s*)?'\s*\+\s*(?=\()", re.S)
"""The same line with the source drawn in place of the join, behind a test of the list -- the form
the vendor's fix took (served 2026-10-25): `' a month' + ((d.kinds || []).length ? ' · ' +
d.kinds.join(' + ') : '')`. Read by `_gated_fallback`; a bracket there that is no ternary over
`kinds` is not this form."""
_GATED_SOURCE = re.compile(r"\s*(?:(['\"])[^'\"]*\1\s*\+\s*)?\(?\s*[\w$]+\.kinds(?:\s*\|\|\s*\[\]\s*\))?"
                           r"\s*\.join\(\s*(['\"])[^'\"]*\2\s*\)\s*", re.S)
MIN_DILUTION_ROWS = 5


def _is_number(value) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _js_close(text: str, at: int) -> int:
    """The index of the bracket closing the one opened at `at` (strings skipped), or -1."""
    depth, i = 0, at
    while i < len(text):
        ch = text[i]
        if ch in "'\"`":
            j = i + 1
            while j < len(text) and text[j] != ch:
                j += 2 if text[j] == "\\" else 1
            i = j + 1
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def _js_terms(text: str) -> list[str]:
    """The `+`-joined terms of the expression `text` starts with, up to where that expression ends
    (a `;`, `,` or closing bracket at its own level)."""
    terms, depth, start, i = [], 0, 0, 0
    while i < len(text):
        ch = text[i]
        if ch in "'\"`":
            j = i + 1
            while j < len(text) and text[j] != ch:
                j += 2 if text[j] == "\\" else 1
            i = j + 1
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            if depth == 0:
                break
            depth -= 1
        elif depth == 0 and ch in ";,":
            break
        elif depth == 0 and ch == "+":
            terms.append(text[start:i])
            start = i + 1
        i += 1
    terms.append(text[start:i])
    return terms


def _dilution_fallback(page: str, found: re.Match) -> tuple[str | None, str | None]:
    """What the line prints after the join when `kinds` is empty: ("length", text) for a term like
    `((d.kinds || []).length ? '' : 'vesting schedule')`, shown when the list is empty; ("or", text)
    for `((d.kinds || []).join(' + ') || 'text')`, shown when the join is ''; ("unread", None) when
    something after the join reads `kinds` in a way not read; (None, None) when nothing does -- a
    blank fallback included, since it names nothing (A07)."""
    close = _js_close(page, found.end() - 1)
    if close < 0:
        return "unread", None
    tail = page[close + 1:close + 600]
    if found.group("wrap"):
        alt = re.match(r"\s*\|\|\s*(['\"])(.*?)\1\s*\)", tail, re.S)
        if alt:
            return ("or", alt.group(2)) if alt.group(2).strip() else (None, None)
        if re.match(r"\s*\|\|", tail):
            return "unread", None
        shut = re.match(r"\s*\)", tail)
        tail = tail[shut.end():] if shut else tail
    # Unparenthesised, `join(...) || 'x'` binds to the whole non-empty line and never shows.
    return _kinds_after(tail)


def _kinds_after(tail: str) -> tuple[str | None, str | None]:
    """A fallback for an empty `kinds` among the `+` terms of `tail` (see `_dilution_fallback`)."""
    for term in _js_terms(tail)[1:]:
        if not re.search(r"\bkinds\b", term):
            continue
        split = re.fullmatch(r"\s*\(?\s*(.+?)\?\s*(['\"])(.*?)\2\s*:\s*(['\"])(.*?)\4\s*\)?\s*", term, re.S)
        if not split:
            return "unread", None
        cond, yes, no = split.group(1), split.group(3), split.group(5)
        negated = re.match(r"\s*\(*\s*!", cond) or re.search(r"\.length\s*(?:===?\s*0|<\s*1|<=\s*0)", cond)
        shown = yes if negated else no
        return ("length", shown) if shown.strip() else (None, None)
    return None, None


def _split_ternary(expr: str) -> tuple[str, str, str] | None:
    """COND, THEN, ELSE of `COND ? THEN : ELSE` at the expression's own level, or None."""
    depth, i, ask, nested = 0, 0, None, 0
    while i < len(expr):
        ch = expr[i]
        if ch in "'\"`":
            j = i + 1
            while j < len(expr) and expr[j] != ch:
                j += 2 if expr[j] == "\\" else 1
            i = j + 1
            continue
        if ch in "([{":
            depth += 1
        elif ch in ")]}":
            depth -= 1
        elif depth == 0 and ch == "?" and expr[i + 1:i + 2] not in (".", "?"):
            if ask is None:
                ask = i
            else:
                nested += 1
        elif depth == 0 and ch == ":" and ask is not None:
            if not nested:
                return expr[:ask], expr[ask + 1:i], expr[i + 1:]
            nested -= 1
        i += 1
    return None


def _gated_fallback(page: str, found: re.Match) -> tuple[tuple[str | None, str | None], int] | None:
    """For DILUTION_GATED's bracket, (fallback, where the bracket closes): the branch shown for a
    list that is not empty must be the join (with its dot), and the other branch a string -- what an
    empty list prints, ("length", text), or (None, None) when it is blank. ("unread", None) when the
    ternary reads `kinds` in a way not read. None when the bracket is no ternary over `kinds`: not
    this form (the join form's own `(d.kinds || [])` lands here too)."""
    close = _js_close(page, found.end())
    if close < 0:
        return None
    split = _split_ternary(page[found.end() + 1:close])
    if split is None or not re.search(r"\bkinds\b", "".join(split)):
        return None
    cond, yes, no = split
    if not (re.search(r"\bkinds\b", cond) and re.search(r"\.length\b", cond)):
        return ("unread", None), close
    negated = re.match(r"\s*\(*\s*!", cond) or re.search(r"\.length\s*(?:===?\s*0|<\s*1|<=\s*0)", cond)
    full, empty = (no, yes) if negated else (yes, no)
    said = re.fullmatch(r"\s*(['\"])(.*?)\1\s*", empty, re.S)
    if not _GATED_SOURCE.fullmatch(full) or not said:
        return ("unread", None), close
    after = _kinds_after(page[close + 1:close + 600])
    if after != (None, None):
        return ("unread", None), close
    text = said.group(2).strip(" ·")
    return (("length", text) if text.strip() else (None, None)), close


def _prints_nothing(kinds: list, fallback: tuple[str | None, str | None]) -> bool:
    """Whether a row with `kinds` reads nothing after "a month · " where the line has `fallback`:
    a kind that is empty, blank or not a string names nothing (A07: [''] passed as a source)."""
    if any(isinstance(k, str) and k.strip() for k in kinds):
        return False
    kind, _ = fallback
    if kind == "length":
        return len(kinds) > 0
    if kind == "or":
        return " + ".join("" if k is None else str(k) for k in kinds) != ""
    return True


def dilution_source_breaches(batch: dict | None, page_html: str | None) -> dict:
    """Does every 12-month dilution the Supply column shows name where its new tokens come from?

    2026-10-18: Rainbow reads "Dilution, 12 months +64.3%" and under it "0 new RNBW a month · "
    with nothing after the dot. `tiles.dilution_12m` holds `new_tokens_12m` 115.8M (69.5M of
    vesting for Investors and Team on 2027-02-05, then 5.79M a month) and `kinds` [], because
    `kinds`, like `month_tokens`, counts only the first of the 12 months, which has nothing.

      failed  the page joins `kinds` after "a month · " and a row with new tokens in its next 12
              months prints nothing there: no kind that is a non-blank string, and no fallback
              the line draws after the join for it
      ok      every such row names at least one kind, or is empty and gets the line's fallback
      unread  the line is not on the page in that form (reworded, a fallback in place of the
              join, something after the join that reads `kinds` in a way not read): what a
              visitor reads is then a question for a browser; or the batch could not be read, a
              row's `kinds` is missing, or fewer than MIN_DILUTION_ROWS rows were judged

    A07, deep pass 2026-10-25: a fallback drawn after the join (`+ ((d.kinds || []).length ? '' :
    'vesting schedule')`) was not read, so the repaired page FAILED; and kinds [''] counted as a
    source while the page printed nothing. Every place the line is drawn is read; a row prints
    nothing if it does in any of them.

    NOT judged: the monthly figure (the 0 is October's inflow, as our ET-31267 mockup drew it),
    whether the 12-month figure is right, a row with no new tokens ("0 new COMP a month · " beside
    0.0% has nothing to name), a row with no figure ("—"), or whether a fallback's words are the
    row's true source.
    """
    out = {"verdict": "unread", "why": "", "judged": 0, "breaches": [], "unread": [],
           "as_of": (batch or {}).get("as_of") if isinstance(batch, dict) else None, "line": None,
           "fallback": None, "by_fallback": []}
    page_html = page_html or ""
    places = [(m.start(), m.end(), _dilution_fallback(page_html, m)) for m in DILUTION_LINE.finditer(page_html)]
    for m in DILUTION_GATED.finditer(page_html):
        gated = _gated_fallback(page_html, m)
        if gated is not None:
            places.append((m.start(), gated[1] + 1, gated[0]))
    if not places:
        out["why"] = ("the page no longer joins the 12-month tile's kinds after 'a month' "
                      "in a form this reads; what the line says is a question for a browser")
        return out
    places.sort()
    out["line"] = page_html[places[0][0]:places[0][1]]
    fallbacks = [fallback for _, _, fallback in places]
    if any(kind == "unread" for kind, _ in fallbacks):
        out["why"] = ("after joining the 12-month tile's kinds the page reads them again in a way this "
                      "does not read; what the line says is a question for a browser")
        return out
    shown = {text for kind, text in fallbacks if kind}
    out["fallback"] = shown.pop() if len(shown) == 1 else (sorted(shown) or None)
    items = (batch or {}).get("items") if isinstance(batch, dict) else None
    items = list(items.values()) if isinstance(items, dict) else list(items or [])
    seen = set()
    for item in items:
        token = item.get("token") or {}
        ident = (str(token.get("slug") or "").lower(), str(token.get("gecko_id") or "").lower())
        if ident in seen:
            continue
        seen.add(ident)
        tile = (item.get("tiles") or {}).get("dilution_12m")
        if not isinstance(tile, dict) or not _is_number(tile.get("pct")):
            continue                                    # "—": no figure, no line under it
        label = f"{token.get('symbol')}({token.get('slug')})"
        new, kinds = tile.get("new_tokens_12m"), tile.get("kinds")
        if not _is_number(new) or not isinstance(kinds, list):
            out["unread"].append(label)
            continue
        if new <= 0:
            continue
        out["judged"] += 1
        if any(_prints_nothing(kinds, fallback) for fallback in fallbacks):
            nxt = item.get("next_unlock") or {}
            out["breaches"].append({
                "row": label, "pct": tile.get("pct"), "new_tokens_12m": new,
                "month_tokens": tile.get("month_tokens"), "schedule_known": tile.get("schedule_known"),
                "emissions_known": tile.get("emissions_known"), "next_unlock_ts": nxt.get("ts"),
                "next_unlock_tokens": nxt.get("tokens"), "next_unlock_who": nxt.get("who")})
        elif not any(isinstance(k, str) and k.strip() for k in kinds):
            out["by_fallback"].append(label)            # named by the line's fallback, not by its data
    if out["breaches"]:
        out["verdict"] = "failed"
        out["why"] = (f"{len(out['breaches'])} of {out['judged']} rows with new tokens in their next 12 "
                      f"months name no source after 'a month · '")
    elif out["unread"]:
        out["why"] = f"{len(out['unread'])} rows with a 12-month figure carry no readable kinds: {out['unread'][:5]}"
    elif out["judged"] < MIN_DILUTION_ROWS:
        out["why"] = f"only {out['judged']} rows have new tokens in their next 12 months"
    else:
        out["verdict"] = "ok"
        out["why"] = (f"all {out['judged']} rows with new tokens in their next 12 months name their source"
                      + (f" ({len(out['by_fallback'])} through the line's fallback {out['fallback']!r}: "
                         f"{out['by_fallback'][:5]})" if out["by_fallback"] else ""))
    return out


# --- the Chains tab against its sources and its own words (2026-10-04) --------------------------
#
# Verified over all 33 chains of the 08:47 UTC snapshot: daily users, DEX volume, TVL, market cap
# and every derived figure (held-back caps, adoption, price tag, the median benchmark, Upside)
# follow DeFiLlama, CoinGecko and the page's own rules. What did not is held here.

LLAMA_STABLECOIN_CHART = "https://stablecoins.llama.fi/stablecoincharts/{chain}"
STABLECOIN_TOLERANCE = 0.03
"""A chain's stablecoins against DeFiLlama's dollar figure for the input's own day. On
2026-10-04 every chain showed DeFiLlama's token count exactly; it was within 0.9 % of the
dollar figure on 27 chains and 2.5 % on 31 (Avalanche +2.5 %, Filecoin -1.8 %, BSC -1.6 %),
while Stellar (-7.5 %) and Sei (-10.7 %) hold USDY, priced at $1.147. 3 % leaves the small
depegs alone and catches a coin that is not worth a dollar."""


def chain_stablecoin_gaps(chains: list, charts: dict, *, tol: float = STABLECOIN_TOLERANCE,
                          generated_at=None) -> dict:
    """The page's "Stablecoins: dollars parked on the chain" (`adoption.inputs.stablecoins`)
    against DeFiLlama's dollar value of the USD-pegged coins on that chain, on the day the
    snapshot says the input is from (`adoption.as_of.stablecoins`).

    `charts` maps a chain's slug to DeFiLlama's stablecoin chart for it (a list of daily
    points), or None when the read failed. A failed read, or no point on the input's day, is
    unread, never agreement. EUR-, CHF- and other non-dollar coins are not dollars and are not
    counted. Each gap also says whether the figure shown is DeFiLlama's token count
    (`totalCirculating`) instead. When the input's day is the chart's newest, still-open point,
    a figure between it and the closed day before is listed under `moving`, not as a gap."""
    judged, gaps, unread, ok_gaps, moving = 0, [], [], [], []
    for chain in chains or []:
        if not isinstance(chain, dict):
            continue
        name = chain.get("name") or chain.get("slug")
        ad = chain.get("adoption") or {}
        shown = num((ad.get("inputs") or {}).get("stablecoins"))
        as_of = (ad.get("as_of") or {}).get("stablecoins")
        points = (charts or {}).get(chain.get("slug"))
        if points is None:
            unread.append(f"{name}: DeFiLlama's stablecoin chart was not read")
            continue
        if shown is None or not isinstance(as_of, (int, float)):       # a shown $0 is a figure: a -100 % gap
            unread.append(f"{name}: no stablecoin figure or date in the snapshot")
            continue
        point = next((p for p in points if isinstance(p, dict) and str(p.get("date")).isdigit()
                      and int(p["date"]) == int(as_of)), None)
        if point is None:
            unread.append(f"{name}: DeFiLlama has no point on {time.strftime('%Y-%m-%d', time.gmtime(as_of))}")
            continue
        usd = num((point.get("totalCirculatingUSD") or {}).get("peggedUSD"))
        tokens = num((point.get("totalCirculating") or {}).get("peggedUSD"))
        if not usd:
            unread.append(f"{name}: DeFiLlama's point carries no USD-pegged dollar value")
            continue
        judged += 1
        gap = shown / usd - 1.0
        if abs(gap) > tol and _within_open_day(shown, int(as_of), points, usd, tol, generated_at):
            # 2026-10-10: the input's day is DeFiLlama's latest, still-open point, and the
            # figure lies between it and the closed day before -- a value the source passed.
            moving.append({"name": name, "shown": shown, "usd": usd, "gap_pct": round(100.0 * gap, 2)})
            continue
        if abs(gap) > tol:
            gaps.append({"name": name, "slug": chain.get("slug"), "shown": shown, "usd": usd, "tokens": tokens,
                         "gap_pct": 100.0 * gap, "as_of": int(as_of),
                         "tokens_match": bool(tokens) and abs(shown / tokens - 1.0) <= 0.005})
        else:
            ok_gaps.append(abs(gap))
    return {"judged": judged, "gaps": gaps, "unread": unread, "moving": moving,
            "max_ok_gap_pct": round(100.0 * max(ok_gaps), 3) if ok_gaps else None}


def _within_open_day(shown: float, as_of: int, points: list, usd: float, tol: float,
                     generated_at=None) -> bool:
    """True when the input's day was still open when THEY read it, and `shown` lies, within
    `tol`, between that day's point and the closed day before. Open means: `generated_at` (the
    snapshot's own time) falls inside the input's UTC day; with no `generated_at`, that the
    day is still DeFiLlama's newest point. The first version only had the second reading, so
    the same snapshot passed before midnight UTC and failed after it (deep pass 2026-10-10, A01)."""
    dated = [(int(p["date"]), p) for p in points
             if isinstance(p, dict) and str(p.get("date")).isdigit()]
    if not dated:
        return False
    made = num(generated_at)
    if made is not None:
        if not as_of <= made < as_of + 86400:
            return False
    elif max(d for d, _ in dated) != as_of:
        return False
    before = [p for d, p in dated if d == as_of - 86400]
    prev = num(((before[0].get("totalCirculatingUSD") or {}) if before else {}).get("peggedUSD"))
    if not prev:
        return False
    low, high = min(prev, usd), max(prev, usd)
    return low * (1.0 - tol) <= shown <= high * (1.0 + tol)


PRICE_TAG_CLAIMS = (
    ("fees_multiple", "fees", re.compile(
        r"a chain'?s (?:multiple |price tag )?is market cap\s*/\s*(?:yearly|annual) activity fees", re.I)),
    ("named_leader", "leader", re.compile(r"compared with a named leader chain", re.I)),
    ("pvr_fees", "fees", re.compile(r"chains:\s*market cap\s*/\s*(?:yearly|annual) activity fees", re.I)),
    ("benchmark_leader", "leader", re.compile(r"`benchmark` names the leader chain", re.I)),
)


def _chain_measure(bench: dict) -> tuple[str | None, str | None]:
    """(what a chain's price tag divides by, how the benchmark is made) as the snapshot says."""
    bench = bench or {}
    basis = str(bench.get("basis") or "")
    measure = bench.get("measure") or (basis.split("/", 1)[1] if "/" in basis else None)
    return measure, bench.get("kind")


def chain_price_tag_claims(llms_text: str, bench: dict) -> dict:
    """Sentences in llms.txt's Gem Screener section that describe a chain's price tag as
    something the live snapshot does not compute.

    2026-10-04: the snapshot's `bench_chains` says market cap / adoption against the median
    of the large chains (and llms.txt says so too, under "Chains from ET-28821"), while the
    section's opening ("What it is"), the `price_vs_revenue` field line and the older Chains
    line still say market cap / yearly activity fees against a named leader chain. A claim is
    stale only against a snapshot that computes something else: the same words beside a
    snapshot on fees and a leader are true. Only the Gem Screener section is read."""
    out = {"stale": [], "unread": [], "measure": None, "kind": None}
    measure, kind = _chain_measure(bench)
    out["measure"], out["kind"] = measure, kind
    if not measure:
        out["unread"].append("the snapshot's bench_chains names no measure")
        return out
    text = (llms_text or "").replace("’", "'")
    # A heading line starts the section; the file also names it in quotes long before
    # ('see the "## Gem Screener" section below'), which is not the section.
    heading = re.search(r"(?m)^## Gem Screener[ \t]*\r?$", text)
    if not heading:
        out["unread"].append("llms.txt has no '## Gem Screener' section")
        return out
    following = re.compile(r"(?m)^## ").search(text, heading.end())
    section = text[heading.start(): following.start() if following else len(text)]
    for key, kind_of_claim, pattern in PRICE_TAG_CLAIMS:
        if kind_of_claim == "fees" and "activity" in str(measure):
            continue
        # A "named leader" sentence is true only beside a snapshot on a leader; stale beside
        # ANY other kind, not only "median" (deep pass 2026-10-08, T07, 3/3). With no kind
        # named, whether it is stale cannot be read.
        if kind_of_claim == "leader" and kind in (None, "leader"):
            if kind is None and "the snapshot's bench_chains names no kind" not in out["unread"]:
                out["unread"].append("the snapshot's bench_chains names no kind")
            continue
        found = pattern.search(section)
        if found:
            line_start = section.rfind("\n", 0, found.start()) + 1
            line_end = section.find("\n", found.end())
            line = section[line_start: line_end if line_end > 0 else len(section)].strip()
            out["stale"].append({"claim": key, "said": found.group(0), "line": line[:400]})
    return out


def _join_js(page_html: str) -> str:
    """The page source with adjacent quoted pieces of a `+` chain joined, so a sentence
    split over two source lines reads as one."""
    joined = re.sub(r"'\s*\+\s*'", "", page_html or "")
    return re.sub(r'"\s*\+\s*"', "", joined)


AGENT_PROMPT = re.compile(r"tell me about[^\n]{0,200}?its adoption \(([^)]*)\)", re.I)
AGENT_AGAINST = re.compile(r"its upside against (the [a-z ]+?)(?= and |[.,;])", re.I)


def chain_agent_prompt_claims(page_html: str, bench: dict) -> dict:
    """The chain detail's "Paste into your agent" prompt against the snapshot's measure.

    2026-10-04 it asked an agent for a chain's "adoption (daily users and fees)" and "its
    upside against the benchmark chain", while the page defines adoption as four inputs with
    "no fees in it" and the benchmark as the median of the large chains. Unread when the
    prompt is not on the page."""
    out = {"stale": [], "unread": [], "prompt": None}
    joined = _join_js(page_html)
    found = AGENT_PROMPT.search(joined)
    if not found:
        out["unread"].append("the chain agent prompt ('tell me about ... its adoption (...)') is not on the page")
        return out
    measure, kind = _chain_measure(bench)
    window = joined[found.start(): found.start() + 600]
    out["prompt"] = window[:300]
    four_inputs = bool((bench or {}).get("adoption_version")) or measure == "adoption"
    if four_inputs and re.search(r"\bfees?\b", found.group(1), re.I):
        out["stale"].append(f"adoption ({found.group(1)})")
    against = AGENT_AGAINST.search(window)
    if against and kind not in (None, "leader") and re.search(r"\b(?:benchmark|leader) chain\b", against.group(1), re.I):
        out["stale"].append(against.group(1))
    return out


ADOPTION_READINGS = ("Adoption (stablecoins and DEX volume)", "Adoption growth 6M")
ADOPTION_VETTING_TAGS = (
    ("vetting tag 'Adoption falling ... a month'", re.compile(r"Adoption falling\b[^<'\"]{0,60}month")),
    ("vetting tag 'Adoption is at ...%'", re.compile(r"Adoption is at \d[\d.,]*\s*%")),
)
"""The vetting tags that read a monthly adoption trajectory: found by their own words, so a
page that renames the two labels above but keeps the tags is still caught (deep pass 2026-10-05)."""
NO_ADOPTION_HISTORY = re.compile(r"adoption[^.<]{0,80}?has no (?:monthly|3-month|three-month) (?:history|series)",
                                 re.I)


def chain_adoption_two_measures(page_html: str | None, chains: list) -> dict:
    """Does "Adoption" on the Chains tab name one measure?

    2026-10-04: the Adoption column, its tooltip and the Upside are the four-input measure,
    which the page says "has no monthly history"; the detail's "Adoption growth 6M", the
    trajectory sentence and the vetting tags ("Declining: Adoption falling 12.8% a month",
    "Post-crash") read a stablecoins-and-DEX-volume index the page also calls Adoption, and
    vetting decides which chains "Vetted only" shows.

      two_measures  the page defines adoption as four inputs and calls a reading Adoption that
                    its own text says is stablecoins and DEX volume, or that it says adoption
                    cannot have (no history)
      ok            no reading is called Adoption, or nothing says it measures something else
      unread        the four-input definition is not on the page (its shape changed)"""
    out = {"verdict": "unread", "readings": [], "no_history": False, "rows": [], "why": ""}
    joined = _join_js(page_html or "")
    if "four inputs together" not in joined:
        out["why"] = "the four-input definition of adoption ('four inputs together') is not on the page"
        return out
    out["readings"] = ([label for label in ADOPTION_READINGS if label in joined]
                       + [label for label, rx in ADOPTION_VETTING_TAGS if rx.search(joined)])
    out["no_history"] = bool(NO_ADOPTION_HISTORY.search(joined))
    out["rows"] = [{"name": c.get("name"), "reliable_fail": c.get("reliable_fail")}
                   for c in chains or [] if isinstance(c, dict) and not c.get("reliable")
                   and set(c.get("reliable_fail") or []) & {"declining_trend", "far_below_peak"}]
    other = ADOPTION_READINGS[0] in out["readings"]
    if out["readings"] and (other or out["no_history"]):
        out["verdict"] = "two_measures"
        out["why"] = ("readings the page calls Adoption measure stablecoins and DEX volume"
                      if other else "a reading is called Adoption growth while the page says adoption has no history")
    else:
        out["verdict"], out["why"] = "ok", "Adoption names one measure"
    return out


def chain_left_out_reason_breaches(universe: dict, markets: dict) -> dict:
    """Chains the tab leaves out "for no market data" while CoinGecko has a market cap at
    least the listing floor for that token.

    2026-10-04: the page's Chains note said "Not listed, no market data: BCH, ETC." and
    `chains_universe.left_out` gave both `missing: []`, while CoinGecko's markets answered
    Bitcoin Cash $6.4bn and Ethereum Classic $1.4bn (on DeFiLlama, Bitcoin Cash has no
    stablecoin chart and Ethereum Classic no DEX volume). `markets` maps a CoinGecko id to
    the market cap CoinGecko answered (None or 0 = it has none); an id not in it was not
    read. No row left out for that reason is the fix, not an unread list."""
    rows = (universe or {}).get("left_out")
    if not isinstance(rows, list):
        return {"judged": 0, "breaches": [], "unread": ["chains_universe.left_out is missing"], "with_reason": 0}
    floor = num((universe or {}).get("min_mcap")) or 0.0
    judged, breaches, unread = 0, [], []
    with_reason = [r for r in rows if isinstance(r, dict) and r.get("reason") == "no_market_data"]
    for row in with_reason:
        gid = row.get("gecko_id")
        if gid not in (markets or {}):
            unread.append(row.get("symbol") or gid)
            continue
        judged += 1
        cap = num(markets[gid])
        if cap and cap >= floor:
            breaches.append({"symbol": row.get("symbol"), "gecko_id": gid, "chain": row.get("chain"),
                             "coingecko_market_cap": cap, "missing_stated": row.get("missing")})
    return {"judged": judged, "breaches": breaches, "unread": unread, "with_reason": len(with_reason)}


def _close(value, expected, *, rel: float = 0.01, abs_tol: float = 0.0) -> bool:
    if value is None or expected is None:
        return False
    return abs(value - expected) <= max(abs_tol, rel * abs(expected))


def derived_identities(snap: dict, coins: dict | None = None) -> list[dict]:
    """Every derived figure the snapshot publishes that is an exact function of
    other figures it publishes, recomputed. All of these held on 2026-09-30, on
    every row that carries the inputs; a breach is a row where they did not.

    Returns one dict per identity: name, the definition, rows checked, breaches
    (each naming its row) and the largest relative deviation seen. A row that
    lacks an input is skipped, not passed: `checked` says how many were read.
    """
    rules, risk = (snap.get("degen") or {}).get("rules") or {}, snap.get("risk_rules") or {}
    alt4 = num((snap.get("altseason") or {}).get("alt_4w_median"))
    out: list[dict] = []

    def run(name: str, definition: str, rows, test):
        checked, breaches, worst = 0, [], 0.0
        for row in rows:
            verdict = test(row)
            if verdict is None:
                continue
            checked += 1
            ok, dev = verdict
            worst = max(worst, dev or 0.0)
            if not ok:
                breaches.append(row.get("symbol") or row.get("key") or row.get("name"))
        out.append({"name": name, "definition": definition, "checked": checked,
                    "breaches": breaches, "max_dev": round(worst, 5)})

    apps = snap["apps"]

    def dev(a, b):
        return abs(a / b - 1.0) if a is not None and b else None

    def ps_test(a):
        rr, ps, mcap = num((a.get("runrate") or {}).get("value")), num(a.get("ps")), num(a.get("mcap"))
        if not rr or rr <= 0 or ps is None or not mcap:
            return None
        return _close(ps, mcap / rr, rel=0.01, abs_tol=0.0006), dev(ps, mcap / rr)
    run("ps", "price/revenue = market cap / run-rate revenue", apps, ps_test)

    # C04, deep pass of 2026-09-30: the market cap every P/S and upside stands
    # on is price x circulating supply. The supply and the price are held to
    # CoinGecko elsewhere; this holds the product. Within 1.02 % on all 214
    # comparable rows of 2026-09-30, so 2 % is a breach, not a timing wobble.
    def mcap_test(a):
        mcap, price, circ = num(a.get("mcap")), num(a.get("price")), num((a.get("cg") or {}).get("circ"))
        if not (mcap and price and circ):
            return None
        return _close(mcap, price * circ, rel=0.02), dev(mcap, price * circ)
    run("market cap", "market cap = price x circulating supply", apps, mcap_test)

    def earn_test(a):
        e, r, n = num(a.get("emissions30d")), num(a.get("rev30d")), num(a.get("earnings30d"))
        if e is None or r is None or n is None:
            return None
        return (abs((r - e) - n) <= max(1.0, 0.001 * abs(r)) and bool(a.get("printed")) == (e > r)), None
    run("earnings", "earnings after emissions = revenue - emissions; 'printed' = emissions > revenue", apps, earn_test)

    def t30_test(a):
        t = a.get("test30") or {}
        if not t.get("implied") or not num(a.get("mcap")):
            return None
        ok = _close(t["implied"], t["mult"] * a["mcap"], rel=0.001)
        if t.get("ceiling") and t.get("room_x") is not None:
            ok = ok and _close(t["room_x"], t["ceiling"] / a["mcap"], rel=0.01)
        if t.get("ceiling") is not None and t.get("size_ok") is not None:
            ok = ok and ((t["implied"] <= t["ceiling"]) == bool(t["size_ok"]))
        return ok, dev(t["implied"], t["mult"] * a["mcap"])
    run("30x test", "implied = 30 x market cap; room = rival / market cap; size ok = implied <= rival", apps, t30_test)

    def liq_test(a):
        liq = a.get("liq") or {}
        pool, impact, ticket = num(liq.get("pair_liq_usd")), num(liq.get("impact_pct")), num(liq.get("ticket"))
        if not pool or impact is None or not ticket:
            return None
        ok = _close(impact, 100.0 * ticket / (pool / 2.0), rel=0.01)
        if liq.get("ok") is not None and risk.get("max_impact_pct") is not None:
            passes = impact <= risk["max_impact_pct"] or (num(liq.get("vol24h")) or 0) >= (risk.get("vol_pass") or 0)
            ok = ok and bool(liq["ok"]) == bool(passes)
        return ok, dev(impact, 100.0 * ticket / (pool / 2.0))
    run("liquidity", "slippage = 100 x ticket / (pool / 2); passes if <= 3 % or 24 h volume >= 2M", apps, liq_test)

    def gate_test(a):
        fails = set(a.get("degen_fail") or [])
        if not rules or a.get("rev30d") is None or a.get("potential") is None:
            return None
        ok = (("small_business" in fails) == (a["rev30d"] < rules["min_rev30"])
              and ("not_cheap" in fails) == (a["potential"] < rules["min_potential"])
              and ("not_vetted" in fails) == (not (a.get("reliable") or a.get("young")))
              and bool(a.get("degen_ok")) == (not fails))
        if (a.get("liq") or {}).get("ok") is not None:
            ok = ok and ("thin_liquidity" in fails) == ((a["liq"]["ok"]) is False)
        return ok, None
    run("degen gates", "small business, not cheap, not vetted, thin liquidity and 'pick' follow the published rules", apps, gate_test)

    themes = [t for t in snap.get("themes") or [] if isinstance(t, dict)]

    def theme_test(t):
        pairs = (("rs1m", "theme_4w", "btc_4w"), ("rs3m", "theme_13w", "btc_13w"))
        ok, read = True, False
        for target, theme, btc in pairs:
            if None in (t.get(target), t.get(theme), t.get(btc)):
                continue
            read = True
            ok = ok and abs((1 + t[theme]) / (1 + t[btc]) - 1 - t[target]) <= 0.0015
        if t.get("hot") is not None and t.get("stage") is not None:
            # Since 2026-10-03 (their statement on #144) `hot` MEANS the stage: the hot flags
            # and the hot count agree. A theme with a stage is held to that; the older
            # rule below is only for a snapshot that carries no stage.
            read = True
            ok = ok and bool(t["hot"]) == (t["stage"] == "hot")
        elif alt4 is not None and t.get("theme_4w") is not None and t.get("hot") is not None:
            read = True
            ok = ok and bool(t["hot"]) == (t["theme_4w"] > alt4 and (t.get("rs1m") or 0) > 0)
        return (ok, None) if read else None
    run("themes", "vs BTC = (1 + theme) / (1 + BTC) - 1; 'hot' is the stage (older snapshots: beat BTC and the median alt over four weeks)", themes, theme_test)

    chains = [c for c in snap.get("chains") or [] if isinstance(c, dict)]
    bench = snap.get("bench_chains") or {}

    def chain_test(c):
        # Since 2026-10-01 (ET-28606) a chain is priced on adoption (daily
        # users x fees); a chain with no user count has no price tag. Before
        # that the base was the fees alone, which a snapshot without an
        # `adoption` block still is.
        def value(block):
            return num(block.get("value")) if isinstance(block, dict) else None
        act = value(c.get("adoption")) or value(c.get("activity"))
        mcap, ps = num(c.get("mcap")), num(c.get("ps"))
        raw, mult = num(c.get("potential_raw")), num(bench.get("mult"))
        if not (act and mcap and ps and raw is not None and mult):
            return None
        ok = _close(ps, mcap / act, rel=0.002) and _close(raw, mult / ps, rel=0.02, abs_tol=0.002)
        fee, fm, pf = num((c.get("fee_runrate") or {}).get("value")), num(bench.get("fee_mult")), num(c.get("potential_fees_raw"))
        if fee and fm and pf is not None:
            ok = ok and _close(pf, fm / (mcap / fee), rel=0.02, abs_tol=0.002)
        return ok, dev(ps, mcap / act)
    run("chains", "price/activity = market cap / yearly activity fees; upside = benchmark / that; fee upside likewise", chains, chain_test)

    if coins:
        def level_test(record):
            level = (record or {}).get("degen_level") or {}
            areas = level.get("areas") or []
            if not areas or level.get("level") is None:
                return None
            weight = sum(a["weight"] for a in areas)
            score = sum(a["weight"] * a["value"] for a in areas) / weight if weight else None
            low, high = level.get("low"), level.get("high")
            ok = score is not None and round(10 * score) == level["level"] and (low is None or high is None or low <= level["level"] <= high)
            return ok, None
        rows = [dict(record, symbol=symbol) for symbol, record in coins.items() if isinstance(record, dict)]
        run("degen level", "level = round(10 x weighted mean of the six area scores), inside its own range", rows, level_test)
    return out


# Identities computed on apps: each must read at least half of them before it
# says anything. The others (themes, chains, earnings, liquidity) run over
# fewer rows by nature and must read at least one.
PER_APP_IDENTITIES = ("ps", "market cap", "30x test", "degen gates")


def identities_verdict(identities: list[dict], total: int) -> tuple[str, str]:
    """("passed" | "failed" | "inconclusive", why) over `derived_identities`.

    A figure recomputed on no row at all is unread, never agreement (R02/C05,
    deep pass of 2026-09-30: themes and chains could pass on zero rows)."""
    unread = [i["name"] for i in identities
              if i["checked"] == 0
              or (i["name"] in PER_APP_IDENTITIES and i["checked"] < 0.5 * total)]
    if unread:
        return "inconclusive", (f"too few of the {total} rows carry the inputs for: "
                                f"{', '.join(unread)}")
    broken = [i for i in identities if i["breaches"]]
    if broken:
        return "failed", "; ".join(
            f"{i['name']}: {len(i['breaches'])} row(s) disagree with their own inputs "
            f"({', '.join(map(str, i['breaches'][:4]))})" for i in broken)
    return "passed", ("; ".join(f"{i['name']} {i['checked']}" for i in identities)
                      + " rows recomputed, none disagree")


def holders_clipped(snap: dict) -> list[dict]:
    """Rows whose 'share of revenue to holders' the page shows as 100 % while
    DefiLlama's own holders revenue is larger than its total revenue. A row that
    shows its true share above 100 % is not clipped (R08, deep pass of
    2026-09-30)."""
    out = []
    for a in snap["apps"]:
        holders, total, share = num(a.get("holders30d")), num(a.get("total30d")), num(a.get("holders_share"))
        if holders and total and share is not None and abs(share - 1.0) <= 0.001 \
                and holders > total * 1.001:
            out.append({"row": label(a), "holders30d": holders, "total30d": total, "shown_share": share})
    return out


RUNRATE_FACTOR = re.compile(r"last\s+(\d+)\s+days\s*[×x]\s*(\d+)(?:\s*/\s*(\d+))?", re.I)


RUNRATE_DAILY = re.compile(
    r"last\s+(\d+)\s+days,?\s+(?:a\s+)?day['’]s\s+average\s*[×x]\s*(\d+)", re.I)


def stated_runrate_factors(text: str) -> dict[int, float]:
    """{30: 12.0, 90: 4.0}: the multipliers the page's own words give the two
    estimates ("last 30 days x 12, last 90 days x 4"), read from its text."""
    out = {}
    plain = re.sub(r"<[^>]+>", " ", text or "")
    # #141, fixed 2026-10-01: the page now says "a day's average over the last
    # 30 days x 365" -- 365 is the multiplier on a DAY's average, so on the
    # window's revenue it is 365 / 30. Read as "x 365" it failed their fix.
    for match in RUNRATE_FACTOR.finditer(plain):
        days, top, bottom = match.groups()
        daily = re.search(r"(?:(?:day|daily)['’]?s?\s+average[^.;]{0,30}|the\s+same\s+over(?:\s+the)?)\s*$",
                          plain[max(0, match.start() - 60):match.start()], re.I)
        out[int(days)] = (float(top) / int(days) if daily and not bottom
                          else float(top) / float(bottom) if bottom else float(top))
    for days, top in RUNRATE_DAILY.findall(plain):
        out[int(days)] = float(top) / int(days)
    return out


def runrate_factor_breaches(snap: dict, stated: dict[int, float], *, tol: float = 0.003) -> dict:
    """Rows whose run-rate rests on the 30-day estimate: the value over the
    30-day revenue is the multiplier, and it should be the one the page states.
    2026-09-30: stated x 12, applied x 365 / 30 = 12.167 (1.4 % higher) on all 45."""
    want = stated.get(30)
    if want is None:
        return {"stated": None, "checked": 0, "breaches": []}
    # Since #141's fix the page words it "a day's average over the last 30 days x 365", and since
    # the coverage fix (a_runrate_states_only_the_days_its_revenue_has) a day's average is taken
    # over the days the row has: on a row whose `runrate.cov30` is under 30 the multiplier on the
    # 30-day sum is 365 / cov30, not 365 / 30. 2026-10-15: FUL, 24 days, x 15.2083 -- the stated
    # rule, read by the check as a breach (deep pass 2026-10-15, 0b).
    daily = abs(want - 365.0 / 30.0) < 1e-3
    checked, breaches = 0, []
    for a in snap["apps"]:
        rr = a.get("runrate") or {}
        value, revenue = num(rr.get("value")), num(a.get("rev30d"))
        if rr.get("basis") != "30d" or not value or not revenue or revenue <= 0:
            continue
        checked += 1
        # The days the row's own series holds in the window, where it carries one; its claimed
        # cov30 otherwise. A cov30 below the days present would inflate the multiplier and pass
        # (A13, deep pass 2026-10-15); coverage_breaches bounds cov30 only from above.
        held = _present_days(a)
        cov = held if held is not None else num(rr.get("cov30"))
        expected = 365.0 / cov if daily and cov and 0 < cov < 30 else want
        ratio = value / revenue
        if abs(ratio / expected - 1.0) > tol:
            breaches.append({"row": label(a), "applied": round(ratio, 4), "stated": round(expected, 4)})
    return {"stated": want, "checked": checked, "breaches": breaches}


def paths_missing_from_openapi(llms_text: str, openapi: dict, prefix: str = "/api/v1/gem-screener") -> list[str]:
    """Paths under `prefix` that llms.txt names and the OpenAPI does not describe, with every
    `{x}` or `<x>` placeholder read as one parameter. 2026-10-10: report-access, which their
    own reply called "in both llms.txt and the OpenAPI"."""
    norm = lambda p: re.sub(r"\{[^}]*\}|<[^>]*>", "{}", p.rstrip("/"))  # noqa: E731
    have = {norm(p) for p in (openapi or {}).get("paths") or {}}
    named = {norm(m) for m in re.findall(re.escape(prefix) + r"(?:/[A-Za-z0-9_\-{}<>]+)*", llms_text or "")}
    return sorted(p for p in named if p not in have)


def dilution_band_breach(meta: dict | None) -> dict | None:
    """The dilution bands in the wrong order: a caution line at or above the red line leaves
    "caution" empty, because a coin reaches red first. None when the order is right or a line is
    not stated. 2026-10-10: caution_line 1.5253, red_line 1.0; 0 caution, 19 red."""
    meta = meta or {}
    caution, red = num(meta.get("caution_line")), num(meta.get("red_line"))
    if caution is None or red is None or caution < red:
        return None
    levels = meta.get("levels") or {}
    return {"caution_line": caution, "red_line": red,
            "caution_n": levels.get("caution"), "red_n": levels.get("red")}


def _present_days(app: dict, window: int = 30) -> int | None:
    """How many of the last `window` days the row's own `rev_series` holds, counted back from the
    series' last day (a day present at 0 has data); None when the row carries no series."""
    day = 86400
    days = {int(p[0]) for p in app.get("rev_series") or []
            if isinstance(p, (list, tuple)) and len(p) == 2 and num(p[0])}
    if not days:
        return None
    last = max(days)
    return sum(1 for i in range(window) if last - i * day in days)


def coverage_breaches(snap: dict, *, window: int = 30) -> dict:
    """Rows whose `runrate.cov30` names more of the last 30 days than their own
    `rev_series` holds, counted back from the series' last day (the window
    `rev30d` sums). A day present at 0 has data; an absent day has none.
    2026-10-10: KNC said 30 with 11 days absent (DeFiLlama has none for them
    either), so the 30-day sum, the run-rate and P/S counted them as zero."""
    day = 86400
    checked, breaches = 0, []
    for a in snap["apps"]:
        rr = a.get("runrate") or {}
        stated = num(rr.get("cov30"))
        series = a.get("rev_series") or []
        days = {int(p[0]) for p in series if isinstance(p, (list, tuple)) and len(p) == 2 and num(p[0])}
        if stated is None or not days:
            continue
        checked += 1
        last = max(days)
        missing = [last - i * day for i in range(window) if last - i * day not in days]
        present = window - len(missing)
        if stated > present:
            breaches.append({"row": label(a), "cov30": stated, "present": present, "basis": rr.get("basis"),
                             "sparse": rr.get("sparse"), "missing": sorted(missing)})
    return {"checked": checked, "breaches": breaches}


def recompute_from_series(app: dict, chart: list) -> dict:
    """The page's revenue figures recomputed from DefiLlama's own daily series.

    All of these reproduced on 2026-09-30 for 25 apps: `rev30d` is the sum of
    the last 30 calendar days to the dollar; each calendar month is its days;
    the run-rate on the median basis is 12 x the median of the three latest
    30-day windows (30-day and 90-day bases are annualised x 365 / days); and
    growth over six months is a log-linear regression of weekly sums in which
    only weeks with all seven days present are kept and the kept weeks are
    numbered 0, 1, 2 ... -- so a gap in time is closed, not measured.
    Missing days count as zero in the sums and as "not known" in the weeks."""
    import datetime as dt
    import math

    days = {}
    for ts, value in chart or []:
        days[dt.datetime.fromtimestamp(ts, dt.timezone.utc).date()] = float(value or 0.0)
    if not days:
        return {"error": "no daily series"}
    last = max(days)
    day = dt.timedelta(days=1)

    def window(end, n):
        return sum(days.get(end - i * day, 0.0) for i in range(n))

    def ratio_dev(mine, page):
        return abs(mine / page - 1.0) if mine is not None and page else None

    out = {"last_day": str(last)}
    mine30 = window(last, 30)
    out["rev30d"] = {"page": num(app.get("rev30d")), "mine": mine30, "dev": ratio_dev(mine30, num(app.get("rev30d")))}

    worst = 0.0
    for m in app.get("monthly") or []:
        try:
            year, month = map(int, str(m.get("m")).split("-"))
        except ValueError:
            continue
        page = num(m.get("v"))
        if page:
            total = sum(v for d, v in days.items() if d.year == year and d.month == month)
            worst = max(worst, abs(total / page - 1.0))
    out["monthly_worst_dev"] = round(worst, 5)

    rr = app.get("runrate") or {}
    basis, page_rr = rr.get("basis"), num(rr.get("value"))
    mine_rr = None
    if basis == "med3":
        windows = [window(last - 30 * k * day, 30) for k in range(3)]
        mine_rr = 12.0 * sorted(windows)[1]
    elif basis == "30d":
        mine_rr = mine30 * 365.0 / 30.0
    elif basis in ("90d", "90d-sparse") and len(days) >= 90:
        mine_rr = window(last, 90) * 365.0 / 90.0
    out["runrate"] = {"basis": basis, "page": page_rr, "mine": mine_rr, "dev": ratio_dev(mine_rr, page_rr)}

    weeks = []
    for i in range(26):
        end = last - 7 * i * day
        present = sum(1 for j in range(7) if (end - j * day) in days)
        if present == 7:
            total = window(end, 7)
            if total > 0:
                weeks.append(total)
    weeks = weeks[::-1]
    growth = app.get("growth6m") or {}
    if len(weeks) >= 4:
        n = len(weeks)
        xs, ys = list(range(n)), [math.log(w) for w in weeks]
        mx, my = sum(xs) / n, sum(ys) / n
        sxx = sum((x - mx) ** 2 for x in xs)
        b = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sxx
        r2 = 0.0
        ss_tot = sum((y - my) ** 2 for y in ys)
        if ss_tot:
            a0 = my - b * mx
            r2 = 1 - sum((y - (a0 + b * x)) ** 2 for x, y in zip(xs, ys)) / ss_tot
        out["growth6m"] = {"page": num(growth.get("g")), "mine": 100.0 * (math.exp(b * 30.0 / 7.0) - 1.0),
                           "weeks_page": growth.get("weeks"), "weeks_mine": n, "r2_page": num(growth.get("r2")), "r2_mine": round(r2, 3)}
    return out


def sampled_apps(snap: dict, limit: int = 12) -> list[dict]:
    """The apps whose daily revenue is recomputed: the shortlist first (it is what
    a degen would buy), then the rest of the top by stated upside, `limit` in all."""
    by_key = {a.get("key"): a for a in snap["apps"]}
    chosen = [by_key[k] for k in (snap.get("degen") or {}).get("shortlist") or [] if k in by_key]
    rest = sorted((a for a in snap["apps"] if a not in chosen and num(a.get("potential"))),
                  key=lambda a: -(num(a.get("potential")) or 0.0))
    return (chosen + rest)[:limit]


def fetch_llama_series(get: Callable, slug: str) -> list:
    body = _json(get(f"https://api.llama.fi/summary/fees/{slug}", params={"dataType": "dailyRevenue"}),
                 f"DefiLlama fees {slug}")
    chart = body.get("totalDataChart") if isinstance(body, dict) else None
    if not isinstance(chart, list) or not chart:
        raise SourceUnavailable(f"DefiLlama fees {slug} carried no daily series")
    return chart


def duplicate_tickers(snap: dict) -> dict[str, list[dict]]:
    """Tickers shared by more than one app: the ones a symbol route cannot tell
    apart. 2026-09-30: INDEX, MET, EDGE and UP."""
    by_symbol: dict[str, list[dict]] = {}
    for app in snap["apps"]:
        by_symbol.setdefault(str(app.get("symbol")), []).append({
            "key": app.get("key"), "name": app.get("name"), "slug": app.get("slug"),
            "mcap": num(app.get("mcap")), "degen_ok": bool(app.get("degen_ok"))})
    return {s: rows for s, rows in by_symbol.items() if len(rows) > 1}


def pick_key(pick: dict):
    """What a pick's own link opens: the `coin` of its detail_url, else its
    slug, else its symbol. #140 was fixed (2026-10-01) by linking each pick by
    slug, which is what our report said would clear it; the check kept opening
    the ticker, which still answers the other coin a shared ticker names."""
    url = str(pick.get("detail_url") or "")
    hit = re.search(r"[?&]coin=([^&#]+)", url)
    if hit:
        return urllib.parse.unquote(hit.group(1))
    return pick.get("slug") or pick.get("symbol")


def pick_identity_breaches(picks: list[dict], coins: dict[str, dict], *,
                           mcap_tol: float = 0.05) -> list[dict]:
    """A Degen pick's own link must open the coin the pick names. `coins` maps
    a pick's key (`pick_key`: its link's coin, else slug, else symbol) to what
    the coin route answered for it. A pick whose link opens a different name,
    or a market cap another coin would have, is a breach; a coin that could not
    be read at all is reported as such, not as matching."""
    out = []
    for pick in picks:
        symbol = pick_key(pick)
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
    """Ages against the snapshot's own time. A snapshot with no time of its own
    has no ages -- unknown, never fresh (R10, deep pass of 2026-09-30)."""
    gen = snap.get("generated_at")
    dated = isinstance(gen, (int, float)) and not isinstance(gen, bool)
    hours = lambda ts: (gen - ts) / HOUR if dated and isinstance(ts, (int, float)) else None
    prices = [h for h in (hours(a.get("market_price_ts")) for a in snap["apps"]) if h is not None]
    supply = [h for h in (hours(a.get("market_supply_as_of_ts")) for a in snap["apps"]) if h is not None]
    sources: dict[str, int] = {}
    for a in snap["apps"]:
        sources[str(a.get("market_source"))] = sources.get(str(a.get("market_source")), 0) + 1
    excluded = snap.get("excluded") or {}
    return {"price_age_h": _stats(prices), "supply_age_h": _stats(supply),
            "supply_older_than_24h": sum(1 for h in supply if h > 24) if dated else None,
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
    raws = [v for v in (num(a.get("potential_raw")) for a in capped) if v is not None]
    return {"at_cap": len(capped), "cap": shown_cap(snap),
            "raw_range_at_cap": [round(min(raws), 1), round(max(raws), 1)] if raws else None,
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
        # The coin route answers by ticker, and two apps can share one (EDGE,
        # UP): its record counts only when it is this coin (R05, deep pass of
        # 2026-09-30).
        # Picks are addressed by slug since 2026-10-01, and the records are
        # filed under what the pick's link opens; the ticker is the fallback.
        coin = (coins or {}).get(a.get("slug")) or (coins or {}).get(a.get("symbol")) or {}
        if coin and str(coin.get("name") or "").casefold() != str(a.get("name") or "").casefold():
            coin = {}
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
                 coins_api: dict | None = None, page_text: str | None = None,
                 series: dict | None = None, now: float | None = None) -> dict:
    """The whole audit as one dict. Pure: give it the snapshot and whatever was
    fetched, and it says what it can. Missing inputs leave their section empty.

    `page_text` is the app page's own words (for the multipliers it states);
    `series` maps an app key to DefiLlama's daily revenue series for it."""
    now = time.time() if now is None else now
    report = {
        "at": now, "snapshot_generated_at": snap.get("generated_at"),
        "snapshot_age_h": (None if age_hours(snap, now) is None else round(age_hours(snap, now), 2)),
        "freshness": freshness(snap), "coverage": coverage(snap),
        "upside": upside_table(snap), "upside_formula": upside_breaches(snap),
        "picks": picks_table(snap, coins_api), "tickers_shared": duplicate_tickers(snap),
        "backtest": backtest_admission(snap), "themes": themes_facts(snap), "chains": chains_facts(snap),
        "altseason": altseason_facts(snap, (sources or {}).get("altseason_universe")),
        "sources": source_columns(snap, sources),
    }
    if picks_api is not None and coins_api is not None:
        report["pick_identity"] = pick_identity_breaches(picks_api, coins_api)
    report["identities"] = derived_identities(snap, coins_api)
    report["holders_clipped"] = holders_clipped(snap)
    if page_text is not None:
        report["runrate_factors"] = runrate_factor_breaches(snap, stated_runrate_factors(page_text))
    if series:
        by_key = {a.get("key"): a for a in snap["apps"]}
        report["series"] = {label(by_key[k]): recompute_from_series(by_key[k], chart)
                            for k, chart in series.items() if k in by_key}
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
    idents = report.get("identities") or []
    if idents:
        bad = [i["name"] for i in idents if i["breaches"]]
        lines.append(f"{len(idents)} derived figures recomputed, {sum(i['checked'] for i in idents)} rows: "
                     + (f"breaches in {', '.join(bad)}" if bad else "no breaches"))
    rf = report.get("runrate_factors")
    if rf and rf.get("checked"):
        lines.append(f"run-rate: page states x{rf['stated']:g}, applies x{rf['breaches'][0]['applied'] if rf['breaches'] else rf['stated']:g} "
                     f"({len(rf['breaches'])} of {rf['checked']} rows off)")
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
    age = report["snapshot_age_h"]
    out += [f"Snapshot age {'unknown' if age is None else f'{age} h'}. Price age median {fr['price_age_h'].get('median')} h, "
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
    if report.get("identities"):
        out += ["", "## Recomputed from their own inputs", "| figure | definition | rows | breaches | largest deviation |",
                "|---|---|---|---|---|"]
        for i in report["identities"]:
            out.append(f"| {i['name']} | {i['definition']} | {i['checked']} | {len(i['breaches'])} "
                       f"{i['breaches'][:4] if i['breaches'] else ''} | {i['max_dev']:.2%} |")
        clipped = report.get("holders_clipped") or []
        if clipped:
            out.append(f"\nShown as 100 % to holders while DefiLlama's holders revenue exceeds its total: "
                       f"{[c['row'] for c in clipped]}")
        rf = report.get("runrate_factors")
        if rf and rf.get("checked"):
            out.append(f"\nRun-rate on the 30-day basis: the page states x{rf['stated']:g}; "
                       f"{len(rf['breaches'])} of {rf['checked']} rows apply "
                       f"{sorted({b['applied'] for b in rf['breaches']})[:3]}.")
    if report.get("series"):
        out += ["", "## Recomputed from DefiLlama's daily revenue (picks)", "| app | 30-day revenue dev | months worst dev | run-rate (basis, dev) | growth 6M page / mine, weeks |",
                "|---|---|---|---|---|"]
        for name, s in report["series"].items():
            if "error" in s:
                out.append(f"| {name} | {s['error']} | | | |")
                continue
            gr = s.get("growth6m") or {}
            rr = s.get("runrate") or {}
            out.append(f"| {name} | {_pct(s['rev30d']['dev'])} | {_pct(s['monthly_worst_dev'])} | {rr.get('basis')}, {_pct(rr.get('dev'))} | "
                       f"{gr.get('page')} / {round(gr['mine'], 2) if gr.get('mine') is not None else None}, {gr.get('weeks_page')} vs {gr.get('weeks_mine')} |")
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
