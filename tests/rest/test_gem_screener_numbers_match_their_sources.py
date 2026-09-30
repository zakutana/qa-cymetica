"""The numbers the Gem Screener shows are the numbers its sources report.

Every figure on the page is copied from somewhere else: market cap from
CoinGecko (and DefiLlama prices when CoinGecko did not answer), revenue from
DefiLlama, pool liquidity from DexScreener. The page says so in its own footer.
A degen leaning on it in a fast market is leaning on the copy being faithful.

What was measured when this was written (2026-09-30, all 215 apps, snapshot 8 h
old): supply against CoinGecko median 0.0 % and 2 of 214 rows beyond 25 %; price
median 1.4 %, none beyond 30 %; revenue against DefiLlama median 0.9 %, 3 of 214
beyond 25 %; pool liquidity against DexScreener median 0.9 %, 2 of 176 beyond
50 %. So the copying is sound, and these checks hold it that way: a pipeline that
started to misread a unit, pair the wrong token or go stale would move a median.

Each column is judged as a population, not coin by coin. One coin 40 % off is the
world moving or a source correcting itself -- the day this was written CoinGecko
cut PHAR's circulating supply by a fifth -- and the snapshot is up to six hours
old. What a pipeline fault looks like is a moved median or a tenth of the rows
far off. The thresholds are in the constants and were set above what the live
data showed, like every ceiling here.

NOT asserted: that the numbers mean what a degen needs (that is the audit's
narrative), that any single row is right, or anything about how the page looks.
A snapshot older than 12 hours measures drift, not fidelity, so it is
inconclusive here; the refresh having stalled is another check's finding
(test_gem_screener_refresh_keeps_its_own_cadence.py).

SAFE: GETs only. The page and CoinGecko, DefiLlama and DexScreener are read
anonymously, the third parties through `build_source_client`, which carries the
whole guard and none of Cymetica's credentials or budget.
"""

from __future__ import annotations

import time

import httpx

from qa import gemaudit as g
from qa.client import build_source_client
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

MAX_SNAPSHOT_AGE_H = 12.0

# (tail, max_median, max_tail_share, min_compared_share)
SUPPLY = (0.25, 0.02, 0.05, 0.90)
PRICE = (0.30, 0.08, 0.05, 0.90)
REVENUE = (0.25, 0.05, 0.05, 0.90)
LIQUIDITY = (0.50, 0.05, 0.05, 0.80)
BENCHMARK_TOL = 0.10


def get_patiently(client, url, *, tries: int = 3, pause: float = 3.0, **kw):
    """`client.get` that tries again when their server stalls. It stalls for 3 to
    11 seconds every few requests (ET-28064, measured again 2026-09-30), so one
    timeout is weather and three in a row is a finding -- of a different check's.
    Raises Inconclusive when every try timed out: a read that failed is not an
    empty one."""
    last = None
    for attempt in range(tries):
        if attempt:
            time.sleep(pause)
        try:
            return client.get(url, **kw)
        except httpx.TimeoutException as exc:
            last = exc
    raise Inconclusive(f"{url} timed out on all {tries} tries ({type(last).__name__})")


def read_snapshot(rest_anon) -> dict:
    return read_page(rest_anon)[0]


def read_page(rest_anon) -> tuple[dict, str]:
    """The page's own snapshot and the page's own words (its tooltips say what each
    figure is), or Inconclusive: a read that failed, a page with no snapshot, or
    one too old to say anything about fidelity."""
    try:
        response = get_patiently(rest_anon, g.APP_PAGE, headers={"Accept": "text/html"})
    except httpx.HTTPError as exc:
        raise Inconclusive(f"{g.APP_PAGE} could not be read: {type(exc).__name__}")
    if response.status_code != 200:
        raise Inconclusive(f"{g.APP_PAGE} answered HTTP {response.status_code}; a failed "
                           f"read is not an empty page")
    try:
        snap = g.parse_snapshot(response.text)
    except g.SnapshotUnreadable as exc:
        raise Inconclusive(f"{g.APP_PAGE}: {exc}")
    age = g.age_hours(snap, time.time())
    if age is None or age > MAX_SNAPSHOT_AGE_H:
        raise Inconclusive(f"the snapshot is {age if age is None else round(age, 1)} h old; past "
                           f"{MAX_SNAPSHOT_AGE_H:.0f} h a comparison measures drift, not fidelity")
    return snap, response.text


def from_source(evidence_store, fetch):
    """Run `fetch(get)` with a source client, turning an unreadable source into
    Inconclusive. The client is closed whatever happens."""
    client = build_source_client(evidence=evidence_store)
    try:
        return fetch(client.get)
    except g.SourceUnavailable as exc:
        raise Inconclusive(str(exc))
    except httpx.HTTPError as exc:
        raise Inconclusive(f"a source could not be read: {type(exc).__name__}")
    finally:
        client.close()


def _verdict(parts: list[tuple[str, str, str]]) -> tuple[str, str]:
    """Combine named (name, verdict, why): any failed fails, else any
    inconclusive is inconclusive, else passed."""
    text = "; ".join(f"{name}: {why}" for name, _, why in parts)
    verdicts = {v for _, v, _ in parts}
    return ("failed" if "failed" in verdicts else
            "inconclusive" if "inconclusive" in verdicts else "passed"), text


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_the_market_caps_rest_on_the_supply_and_price_coingecko_reports(rest_anon, evidence_store):
    """Market cap is price times circulating supply (the page's own arithmetic
    holds within 1 % on every row), so it is checked as its two parts against
    CoinGecko, plus the benchmark's market cap, which every upside is divided by."""
    snap = read_snapshot(rest_anon)
    rows = from_source(evidence_store, lambda get: g.fetch_coingecko(
        get, [a.get("gecko_id") for a in snap["apps"]]))
    total = len(snap["apps"])

    parts = []
    for name, pairs, (tail, max_median, max_tail, min_share) in (
            ("supply", g.supply_pairs(snap, rows), SUPPLY), ("price", g.price_pairs(snap, rows), PRICE)):
        summary = g.deviation_summary(pairs, tail=tail)
        parts.append((name, *g.judge_deviation(summary, total, min_compared_share=min_share,
                                               max_median=max_median, max_tail_share=max_tail)))
    bench = g.benchmark_pairs(snap, rows)
    if bench:
        dev = abs(bench[0][1] / bench[0][2] - 1.0) if bench[0][1] and bench[0][2] else None
        parts.append(("benchmark market cap", "passed" if dev is not None and dev <= BENCHMARK_TOL else
                      "failed" if dev is not None else "inconclusive",
                      f"{dev:.1%} from CoinGecko" if dev is not None else "no usable value"))
    else:
        parts.append(("benchmark market cap", "inconclusive", "the benchmark asset is not among the apps"))

    verdict, why = _verdict(parts)
    if verdict == "inconclusive":
        raise Inconclusive(why)
    conclude(Measurement(
        verdict=verdict, reason=why,
        left={"rows": total, "snapshot": snap.get("generated_at")},
        right={"source": "CoinGecko /coins/markets"},
        population={"supply_worst": g.deviation_summary(g.supply_pairs(snap, rows), tail=SUPPLY[0])["worst"][:5],
                    "price_worst": g.deviation_summary(g.price_pairs(snap, rows), tail=PRICE[0])["worst"][:5]},
        sources={"page": g.APP_PAGE, "coingecko": g.COINGECKO}))


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_the_revenue_is_what_defillama_reports(rest_anon, evidence_store):
    """The denominator of every upside: 30-day revenue per app against
    DefiLlama's fees-and-revenue overview, a parent app being the sum of its
    child protocols and a leaf the protocol with its id."""
    snap = read_snapshot(rest_anon)
    protocols = from_source(evidence_store, g.fetch_llama_revenue)
    total = len(snap["apps"])
    tail, max_median, max_tail, min_share = REVENUE
    summary = g.deviation_summary(g.revenue_pairs(snap, protocols), tail=tail)
    verdict, why = g.judge_deviation(summary, total, min_compared_share=min_share,
                                     max_median=max_median, max_tail_share=max_tail)
    if verdict == "inconclusive":
        raise Inconclusive(why)
    conclude(Measurement(
        verdict=verdict, reason=why, left={"rows": total, "compared": summary["n"]},
        right={"source": "DefiLlama /overview/fees dailyRevenue"},
        population={"worst": summary["worst"]},
        sources={"page": g.APP_PAGE, "defillama": g.LLAMA_REVENUE}))


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_the_pool_liquidity_is_what_dexscreener_reports(rest_anon, evidence_store):
    """What a degen can actually buy: the pool liquidity the slippage figure is
    computed from, against DexScreener's for the same pair. A chain whose
    request failed is named and the comparison still has to cover 80 % of pairs."""
    snap = read_snapshot(rest_anon)
    wanted = g.pair_addresses(snap)
    if not wanted:
        raise Inconclusive("the snapshot names no pair addresses to compare")
    found, failed = from_source(evidence_store, lambda get: g.fetch_dexscreener(get, wanted))
    tail, max_median, max_tail, min_share = LIQUIDITY
    summary = g.deviation_summary(g.liquidity_pairs(snap, found), tail=tail)
    verdict, why = g.judge_deviation(summary, len(wanted), min_compared_share=min_share,
                                     max_median=max_median, max_tail_share=max_tail)
    if verdict == "inconclusive":
        raise Inconclusive(why + (f"; DexScreener failed for: {', '.join(failed)}" if failed else ""))
    conclude(Measurement(
        verdict=verdict, reason=why + (f" (DexScreener failed for {', '.join(failed)})" if failed else ""),
        left={"pairs": len(wanted), "compared": summary["n"]},
        right={"source": "DexScreener /latest/dex/pairs"},
        population={"worst": summary["worst"], "chains_failed": failed},
        sources={"page": g.APP_PAGE, "dexscreener": g.DEXSCREENER}))
