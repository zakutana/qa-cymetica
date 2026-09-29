# Spec 4 (`87681d3`), section F: Chart Analyzer numbers checked live, 2026-09-29

Read-only, paced under the analyzer's limit (30 per window): 232 tickers of the Apps and Chains
tabs, daily for all, weekly for the 101 that have a daily score.

| Spec F says | Measured |
|---|---|
| 101 of 231 tickers have a daily score | **101 of 232** (84 of 210 distinct app tickers; spec says 85 of 214 apps) |
| 82 also have a weekly score, 19 fewer than 60 weekly candles | **82 and 19** (`TOO_LITTLE_HISTORY`) |
| 43 of the 82 sit in a different band | **43** |
| 60 bullish, 36 neutral, 3 very bullish, 2 bearish | **60, 36, 3, 2** |
| bands are the 20-point buckets | bullish 61-80, neutral 41-60, very bullish 81-82, bearish 32-35 seen |

The numbers in F are right. What is not:

1. **Ticker matching gives the wrong coin for at least 7 of the 101** (Gem Screener price against
   the analyzer's last Binance close, more than 30% apart): ALCX 0.71x, ALPHA 0.39x, BAL 7.1x, BIFI
   0.44x, FUN 0.02x, LIT 0.17x, TREE 0.25x. A stale price cannot explain 0.02x or 7x. So "match by
   CoinGecko id, never by ticker" is right, but the analyzer takes only `symbol` (OpenAPI: symbol,
   timeframe, include_candles), so today the caller must map id to a Binance ticker itself.
2. "The analyzer returns no candles today" is wrong: `include_candles=true` returns 500 candles
   (about 42 kB for BTC). A compact "last N closes" is still missing.
3. The limit is `x-ratelimit-limit: 30` per window, so about 330 calls per refresh (daily + weekly)
   need a batch call or pacing.
4. In the live band names, a score of 61 already reads "bullish" while the scale's midpoint is not
   the base rate (base 46.4% maps to about 54): most charts come out green (60 of 101).
5. The coverage counts include chains (16 of the 101), but the Chart column and card are for Apps only.
6. A.7's column list omits two live columns ("Category - share - theme" and "Trajectory").

Consequence: the analyzer follow-up (contract address + chain as input, DEX-pool candles, batch,
`covered_by_study`) goes first, and section F is rewritten after it ships.
