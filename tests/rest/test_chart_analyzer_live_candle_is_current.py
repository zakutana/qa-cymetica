"""The Chart Analyzer's "LIVE" candle is current (2026-10-02).

The operator opened Collector Crypt on the daily timeframe at 14:36 UTC: the page said
"LIVE - DEX POOL" and drew a forming candle at 0.257, while DEXTools showed 0.273. The
answer's own `candles_fetched_at` was 12:24 UTC -- the Gem Screener's six-hourly batch
fills a shared cache (llms.txt: "kept fresh in a shared cache") -- and `candles_stale`
was false, a field no document defines. The pool's own candle at GeckoTerminal read
0.2707, 5.2% above the forming candle the score was computed on, on a day the token
was up about 28%.

Held here: for the Gem Screener coins with a deep pool, a forming candle is not BOTH
more than an hour old AND more than 2% from the pool's current candle at its source.
Fresh-but-drifting and old-but-agreeing both pass; so does any way you fix it (a
shorter cache, a refresh on open, an honest "stale" flag).

NOT asserted: what the cache's age should be, or that the score is right.

SAFE: GETs only, anonymous, to them and to GeckoTerminal.
"""

from __future__ import annotations

import time

import httpx

from qa import gemaudit as g
from qa.client import build_source_client
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from qa.safety import CURRENT_TIER
from tests.rest.test_gem_screener_numbers_match_their_sources import get_patiently

BATCH = "/api/v1/chart-analyzer/batch/gem-screener?timeframe=1d"
ANALYZE = "/api/v1/chart-analyzer/analyze"
NETWORKS = {"solana": "solana", "ethereum": "eth", "bsc": "bsc", "base": "base", "arbitrum": "arbitrum"}
MIN_POOL_LIQUIDITY = 500_000.0
WANTED = 3
TRIES = 10


@qa(component="rest.chart_analyzer", tier=SafetyTier.SAFE, surface="rest")
def test_the_forming_candle_of_a_gem_screener_coin_is_current_or_agrees_with_its_pool(rest_anon):
    """Not both older than an hour and more than 2% from the pool's current candle."""
    try:
        batch = get_patiently(rest_anon, BATCH)
    except httpx.HTTPError as exc:
        raise Inconclusive(f"{BATCH} could not be read: {type(exc).__name__}")
    if batch.status_code != 200:
        raise Inconclusive(f"{BATCH} answered HTTP {batch.status_code}")
    items = [i for i in (batch.json().get("items") or [])
             if i.get("status") == "scored" and (i.get("input") or {}).get("chain") in NETWORKS
             and (i.get("input") or {}).get("contract")]
    source = build_source_client(timeout=30.0)
    judged = []
    try:
        for item in items[:TRIES * 3]:
            if len(judged) >= WANTED:
                break
            entry = item["input"]
            try:
                said = get_patiently(rest_anon, ANALYZE, params={
                    "contract": entry["contract"], "chain": entry["chain"], "timeframe": "1d",
                    "include_candles": "true"})
            except httpx.HTTPError:
                continue
            if said.status_code != 200:
                continue
            body = said.json()
            ident = body.get("identity") or {}
            pool, liquidity = ident.get("pool"), g.num(ident.get("pool_liquidity_usd")) or 0.0
            if not pool or liquidity < MIN_POOL_LIQUIDITY:
                continue
            token = CURRENT_TIER.set(SafetyTier.SAFE)
            try:
                url = (f"https://api.geckoterminal.com/api/v2/networks/{NETWORKS[entry['chain']]}"
                       f"/pools/{pool}/ohlcv/day?limit=1")
                response = source.get(url)
                rows = (((response.json().get("data") or {}).get("attributes") or {}).get("ohlcv_list")
                        if response.status_code == 200 else None) or []
            except (httpx.HTTPError, ValueError):
                rows = []
            finally:
                CURRENT_TIER.reset(token)
            ref = rows[0][4] if rows and len(rows[0]) > 4 else None
            read = g.forming_candle_staleness(body, ref, time.time())
            if read["verdict"] == "unread":
                continue
            judged.append(dict(read, symbol=ident.get("symbol"), pool=pool, liquidity_usd=liquidity,
                               candles_stale=body.get("candles_stale")))
    finally:
        source.close()
    if len(judged) < 2:
        raise Inconclusive(f"only {len(judged)} Gem Screener coin(s) with a deep pool could be compared "
                           f"with their pool's current candle")
    bad = [j for j in judged if j["verdict"] == "old_and_off"]
    conclude(Measurement(
        verdict="failed" if bad else "passed",
        reason=("; ".join(f"{b['symbol']}: candles fetched {b['fetched_at']} ({b['age_s'] / 60:.0f} min old), "
                          f"forming close {b['last_close']:.6g} against the pool's {b['source_close']:.6g} "
                          f"({100 * b['deviation']:.1f}% off), candles_stale {b['candles_stale']}"
                          for b in bad[:3])
                if bad else
                f"{len(judged)} coins compared: none is both older than {g.FORMING_MAX_AGE_S / 60:.0f} min and "
                f"more than {100 * g.FORMING_TOLERANCE:.0f}% from its pool"),
        left={"coins_old_and_off": len(bad), "coins_compared": len(judged)},
        right={"coins_old_and_off": 0},
        population={"judged": [{k: v for k, v in j.items() if k != "pool"} for j in judged]},
        sources={"batch": BATCH, "pool": "GeckoTerminal ohlcv/day"}))
