# Gem Screener, mega-check

2026-11-02 · snapshot 06:20 UTC · 236 apps, 33 chains · five readers, each finding re-read against the raw data before filing.

## Bottom line

**The numbers hold. The words do not.** 19 reports filed (#255 to #273), 2 high. No wrong pick, no wrong copied figure.

| Measured | Result |
|---|---|
| Supply vs CoinGecko | median 0.0 %, 0 of 236 outside |
| Price vs CoinGecko | median 0.7 %, 0 of 236 outside |
| 30-day revenue vs DefiLlama | median 0.6 %, 0 of 236 outside |
| Pool liquidity vs DexScreener | median 0.7 %, 0 of 186 outside |
| Derived figures recomputed | 1,321 rows, 0 breaches |
| Six gates recomputed independently, all 236 | 11 pass, 0 false positives; 1 false negative (Tokenlon, on its pool) |
| `reliable_fail` from the published numbers | 236 of 236 |
| Picks across snapshot, /ranked, /coins, /picks, MCP | agree, apart from the cap of 10 |
| 20 random coins, field by field | price, market cap, holder share, emissions, unlock counts: 0 wrong |
| Altseason, themes, chains recomputed | all hold; 33 chains within source tolerance |

## StonkFun

Our #254 was wrong and is retracted (verification 356). It read +367 % a month, a fit over 98 days, and not the months beside it: Aug $1.3M, Sep $28.7M, Oct $7.0M; last week $769K against a peak of $9.6M.

It was the first pick in an older snapshot (read in the page at 08:38 UTC, "Updated 33 h ago"). Its cached report says "not vetted" by 1 Nov 17:25 UTC. What flipped it is printed nowhere (#258): `rev_falling` has been true since the 21 Oct data point, so it is not simply that flag.

## Defects filed

| # | Severity | What |
|---|---|---|
| 255 | high | Exploits under the app's own name called "not tied to this protocol" (pick Dolomite $1.8M; PancakeSwap, Origin $7.7M, Bankr, Zest, BONK.fun) or "No exploit listed" (Osmosis $5M) |
| 256 | high | Aerodrome family, $7.4M a month, excluded as "no token, nothing to buy"; AERO is $502M |
| 257 | medium | "11 pass", 10 shown; Rhea hidden, the cap stated nowhere |
| 258 | medium | Growing and Vetted texts omit what decides a row (31 and 12 rows; StonkFun) |
| 259 | medium | "over 6 months" on 1 to 5 month fits (27 apps) |
| 260 | medium | `level_vs_peak` "% of its 1-year high" is last vs best quarter (66 rows over 30 points off) |
| 261 | medium | Chain rows Sui and Near open apps |
| 262 | medium | Dilution flag and rule describe what is not applied |
| 263 | medium | "Holders get 20 %" on Lido at 0 % in the last 30 days (9 rows) |
| 264 | medium | Five fixed sentences false against the page's data |
| 265 | medium | "Every quarter faster" true of 9 of 68 Accelerating rows |
| 266 | medium | Agents' caveat "estimates came out positive"; gate-passing coins -23 %, interval below zero |
| 267 | medium | Tokenlon fails Liquid on a $130K pool called deepest; a $1.6M v2 pool would pass |
| 268 | medium | Railgun "No power to mint"; owner-only mint, cap 100M, supply 60M |
| 269 | medium | Report's Good and Real-or-printed lines outrun their own checks |
| 270 | medium | After a restart the socket swapped in a 33-hour-old snapshot, picks flipped |
| 271 | low | Category shares sum to 200 % |
| 272 | low | Tornado "burned"; its own source says no TORN is burned |
| 273 | low | "Of the float" on two denominators (GAIB 19 % vs 24 %) |

## Not filed: ours

ET-32311 is our own spec. It took the warnings off the pick card (item 14) and put the 24-hour volume in the "$10K buy" row (item 11). The exit-flag rule and the holders sentence shape are ours too. These are for our next request, not bugs.

## Not checked

Audit, Team, Insider flow and Whales lines (third-party pages). `gem_screener_degen_report` over MCP. Rug power beyond 17 lines of the sample. Stablecoins on chains beyond the same-day check already held by #167.

## Gaps in their docs

- `/picks` has no row in `/api-docs`; `page-extras`, which carries the excluded names and the altseason series, is in neither `/api-docs` nor the OpenAPI.
- `exit_flags`, `young`, `rev_falling`, "main pool" and the cap of 10 are defined nowhere a reader looks.
- `fetch_warnings` carry `source: null`, though llms.txt promises a source.
- "about 215 apps" in llms.txt and the MCP description; live is 236. No picks history by name.

## Improvements

Goals, for the next Build it Better request.

**Top Picks card**
1. An exploit in the last year shows on the card (Meteora, Trust Wallet $8.5M show nothing).
2. Liquid shows the slip beside the volume, labelled all venues (6 of 10 picks: 3.2 to 7.1 %).
3. A pick's own warnings return to the card, without the one on 231 of 236 rows.
4. "Not growing" says why: "30-day revenue is 20 % of its best" (Meteora, CoWSwap).

**Trust**
5. Holders shows 30 days beside 12 months.
6. Each on-chain sentence names its chain (Render, Pear, Stargate are read on another chain than the pool).

**Finding a gem**
7. A public picks log by name, so an exit can be dated.
8. Near misses say how many are one gate away (6 shown of 38; StonkFun, ORE, GMX not among them).
9. Backtest shows its date (22 Sep, old gates) and the weeks of forward record.
10. A near miss on hover shows the same card as a pick, with the gate it fails marked (the operator's, 2 Nov).

Refused by the operator on 2 Nov, seen in the mock: the band word with its range, a flag for a collapsed price, growth with its window and fit, six gate dots on the Apps row, capped upside marked, the theme-lagging flag as one page line.
