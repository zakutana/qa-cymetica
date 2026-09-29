# Gem Screener (ET-27671) after its release, 2026-09-29 (~15:00 UTC)

Read-only. The vendor's own list: 19 lines pass, 3 pass with a caveat (2, 22, 25), 4 "not true yet"
(10, 17, 20, 27), line 1 a judgement call. Shipped late (deadline 2026-09-27 19:08 UTC).

## What I checked against the live site

| Line | Result |
|---|---|
| 2 first load under 500 kB | Holds. My measure: 336 kB gzipped for the screener's own requests, 920 kB for the whole page (theirs: 453 kB and about 1.1 MB). |
| 7 tooltips at most 20 words, no formulas | **11 of 388 tooltips are longer** (worst 45 words, a chain stablecoin tooltip; 32 words, the DeFiLlama category list; four 24-word breadth tooltips). No formulas found. |
| 10 caution amber | Light blue, as the vendor says. It matches the operator's own later choice (part 4, D: "amber is off Cymetica's palette"). |
| 17 no Trade button | True on the page (UP, PUMP, KNC, HYPE show none). But see F3. |
| 20 fund holds 6 of the 9 picks | True: UP, NEST, SOLV, FXN, KNC, EDGE (PHAR, MNDE and LISTA are not in it). |
| 22 prices | Status shows 237 of 240 refreshed from DeFiLlama; the page says supply and volume are from 15 h ago. |
| 26 agent-ready | Section, small endpoints and MCP tools exist, see F1. |
| Fixed on the way | `?coin=UP` opens UP (also PUMP, KNC, HYPE). The Legend button fits at 390 px. No sideways scroll at 375 or 390 px. |

Not checked: lines 5, 9, 11 to 16, 21, 23 to 25 (only seen in passing) and the sectors chart labels on a phone.

## Findings for one low-severity report (Gem Screener surface)

F1. llms.txt says `GET /api/v1/gem-screener/picks` is "about 2 kB"; it returns 4,091 bytes for 9 picks.
F2. 11 tooltips exceed the 20-word limit of line 7.
F3. `GET /api/v1/gem-screener/coins/{symbol}` returns a `trade_url` for PUMP, KNC, FXN, MNDE and EDGE,
    while the page shows no Trade button ("we do not show a market you cannot buy"). Their books are
    empty (`/exchange/{symbol}/bbo`, null bid and ask) except KNC, which has a dust ask (1.98 KNC).
    `/api/v1/exchange/pairs` and `/markets` (52 pairs) list none of the five, and `/exchange/{symbol}/bbo`
    answers for them.

Not filed: a cloud session has no `.env`. The report is owed from a local session.
