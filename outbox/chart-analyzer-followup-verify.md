# Chart Analyzer follow-up (ET-28324), checked live 2026-09-29 (evening)

Read-only. One `GET /batch/gem-screener` per timeframe (daily, weekly), a handful of single calls.

| Line | Live |
|---|---|
| 1 contract input | REST `analyze` takes `contract` + `chain`; the MCP tool `chart_analyzer_score` takes the same (plus `closed_only`); the page reads `contract`, `chain`, `symbol`, `tf`. WebSocket not checked. Your seven by contract: ALCX 54, ALPHA 45, BAL 70, BIFI 76, FUN 53, TREE 45, LIT 66 (its Ethereum contract) -- all match the vendor's numbers. ALPHA resolves to a Sui token, i.e. Gem Screener's ALPHA is not Binance's. |
| 2 tickers still work | BTC 68, ETH 68, SOL 71. ETH and SOL took 1.5 s; the first BTC call took 12 s (cold). The vendor says about half a second. |
| 3 DEX-only coins | 192 of 201 scored coins are scored from DEX pool candles chosen by contract (GeckoTerminal); 39 have no score, each with a status: no_pool 11, no_contract 11, no_candles 10, too_little_history 6, collecting 1. |
| 4 batch | `GET /batch/gem-screener` returned 240 coins in one call (4.5 s for me, 2.8 s server side; the vendor says 1 to 2 s warm). 201 scored: 72 bullish, 122 neutral, 7 bearish -- exact. The batch has its own limit of 6 requests per window. `POST /batch` exists in OpenAPI; not called. |
| 5 coverage next to the score | Every scored item has `coverage` {covered, coin, timeframe, note}: all 192 DEX coins say "not covered", the 9 Binance ones "covered". The note also says how many candles had no trade (thin trading), e.g. 123 of 307. |
| 6 llms.txt | Entry present, including `contract` + `chain`; `GET /gem-screener/coins/{symbol}` now returns `contract`. |
| 7 50 = base rate | The response `scale` and the batch `midpoint` say 50 = 46.35%. The comparison "61 or more fell from 67 to 49 of 106" could not be reproduced (different populations). |
| 8 same input in REST and MCP, in /api-docs | Yes: MCP `chart_analyzer_score` and `chart_analyzer_batch`; /api-docs lists `/batch`. |

## For spec 4 (section F)

- Apps only (214 rows): daily scored 180 (65 bullish, 108 neutral, 7 bearish); not scored: no_pool 11, no_contract 11,
  no_candles 6, too_little_history 5, collecting 1.
- Weekly: only 3 of 214 apps have a weekly score (DEX pools hold about 6 months of candles; weekly needs 60 weeks).
- 173 of the 180 daily scores use a candle that is still open unless `closed_only=true` is sent.
- 15 of the 180 carry the thin-trading note.
