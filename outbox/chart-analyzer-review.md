# Chart Analyzer (ET-27875): the ten BB-SPEC lines against the live build

Read-only GETs on 2026-09-29 (~12:30 UTC). Shipped 2026-09-29 11:47 UTC, deadline was 2026-09-28
16:56 UTC (about 19 h late). The requester's verdict on the board is still empty and is theirs.

| # | Line | Live |
|---|---|---|
| 1 | One number 1-100 from price data | PASS. BTC 1d = 71, matches their message. |
| 2 | Symbol + timeframe, or upload | PASS. GET/POST `analyze`, POST `upload`, `format.csv` served. Symbols: crypto USDT pairs only, said on the page. |
| 3 | Study over as many charts as it can | PASS, with a stated limit: 16 patterns, 292 Binance USDT pairs, only pairs still trading (`survivorship_note`). |
| 4 | Best pattern = 100, worst = 1 | PASS as built (bull flag 55.3% -> 100, descending triangle 35.9% -> 1), but on the TRAIN period. Held-out: the "1" pattern rose 52.7%, the "100" pattern 47.1%, base 44.4%. |
| 5 | Strong bullish scores high, broken chart low | PASS by construction; see line 8. |
| 6 | Same framework for any chart | PASS. One frozen table (`study_version: v1`). |
| 7 | Patterns drawn, each bullish or bearish | PASS on the mechanism; the marks contradict the names, see N1. |
| 8 | Proof: higher scores rose more often | **FAIL, and the page says so.** Matches their message: 81-100 rose 45.6% (n=2,208), 1-20 rose 55.4% (n=433), Spearman -0.018. |
| 9 | REST + MCP in /api-docs | PASS. `chart_analyzer_score` and `chart_analyzer_study` in tools/list (86 tools), 15 mentions in /api-docs. Not in llms.txt, see N3. |
| 10 | Big number, red to green | Not re-tested visually. |

## Notes (not part of the ten lines)

N1. **Marks contradict names.** 6 of 15 counted patterns are marked against their textbook name:
head and shoulders, bearish engulfing, bear flag, breakdown on volume (all "bullish"), higher highs
and lows, bullish engulfing ("bearish"). BTC's live reading is "Bullish: Bearish engulfing after a
rise, Break of structure up, ...". Disclosed in the MCP description ("marked by its measured
success rate"), but a reader of the chart sees a bearish name under a bullish mark.
N2. **Marks flip out of sample.** For 6 of 15 patterns the held-out rate lies on the other side of
the base rate from the train rate (break of structure up and down, double bottom, inverse head and
shoulders, bearish engulfing, descending triangle). The score is built from the train side only.
N3. **llms.txt has no Chart Analyzer entry** (0 mentions), although agents start there and line 9
names Gem Screener, Tickeron and Nexus as callers. It is in /api-docs and MCP.
N4. **1h and 1w are scored with the daily table, silently.** `timeframe=1h` and `1w` return a score
with the daily `base_rate` (0.4635) and no note; the study proves only 1d and 4h. Their message
says "Rates were measured on daily candles"; the response and the page do not, for 1h and 1w.
N5. **Errors are readable** for a bad symbol (404 `UNKNOWN_SYMBOL`), `1m` (400 `INVALID_TIMEFRAME`)
and an empty call (400 `MISSING_INPUT`), all declared in OpenAPI. `timeframe=banana` returns FastAPI's
422 `string_too_long` (max 4 characters) instead of the allowed list.

Not filed: the verdict is the requester's, and filing needs the `.env` that a cloud session lacks.
N3 and N4 are the ones that mislead a stranger; N1 is a wording question.
