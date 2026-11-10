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

Filed the same day, all low except 274:

| # | What |
|---|---|
| 274 | Dolomite "To holders: None" while its report says the share is unknown (medium) |
| 275 | CoWSwap's 12-month dilution unknown on the card, no word in /picks |
| 276 | Yield Basis Vetted with no level to read, at 6 % of its best |
| 277 | BONK.fun's route quotes Bonkswap, 0.02 % of the money; "burned" against a split |
| 278 | SaucerSwap and USD AI charts on another chain than the pool, unsaid |
| 279 | Tron's report "cheap for its revenue"; Sudoswap's sentence cut short |
| 280 | 8 apps under 25 % of tokens out without the float tag |
| 281 | llms.txt "about 215 apps"; /picks and /page-extras undocumented |
| 282 | A trailing slash redirects to http |
| 283 | Five small statements against their data |

## Not filed, on purpose

- Run-rate "most cautious of three" on 6 sparse rows: the row's label says it is the 90-day figure, by design.
- FDV basis label on rows: in the data only, shown nowhere.
- "Uncategorized" as a raw word on one unlock: cosmetic.
- /coins/up against /coins/UP, the picks log's refresh count, Stargate's "91% still to come", the two chain medians: could not be settled from what we can read.

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

**Calculations, measured 2026-11-10 (snapshot 23:49 UTC on 9 Nov, 235 apps; not yet the operator's word)**
11. REFUSED by the operator on 10 Nov ("benchmark menit nechci"): the benchmark stays Hyperliquid's multiple today. Kept as a measurement only. Hyperliquid's multiple by the page's own run-rate rule (reproduced: 21.9 against the
    page's 22.05): 7.9 to 41.6 over 12 months, 21.9 to 41.6 over the last 90 days; monthly medians 10.1 (Nov 2025), 33.7 (Sep 2026), 24.5 now.
    With today's prices and revenues the default view has 34 rows at 2.5x or more; at 10x it has 17 and 4 of the 10 picks stay cheap
    (CARDS, GMX, PUMP, DOLO); at 41.6x it has 48. Its 12-month median is 20.0, so a median benchmark moves almost nothing today.
12. Upside beside what reaches the token. Hyperliquid pays 100% of revenue to holders; of the 10 picks CARDS pays 3%, TWT 2%, LDO 0%, MET 16%,
    ORCA 37% (upside times that share: 0.5x, 0.1x, 0.0x, 0.6x, 1.0x), GMX, PUMP and USUAL stay at 8.9x, 3.8x and 2.9x, DOLO and RHEA are unknown.
    Top 30 of the default view: 15 under 5%, 3 unknown. A second figure under the multiple, never a gate or a sort input (the standing decision).
13. Upside beside the year's new tokens. Top 10 of the default view: NEST +286% (31x on market cap, 8x after), ORE +99%, RNBW +68%, SOLV +30%;
    GP, SECZ, CARDS and INV have no schedule. The "If all tokens out" figure is in the detail only.
14. Strength 3M divides by the price, not the market cap (its own tooltip says so); the Supply Analyzer's schedule could correct it.

Checked and left: the Growing gate (all 10 picks have their last 3 full months above the 3 before; 7 of 44 passing rows do not, none a pick);
`earnings30d` and `printed` are legacy fields since ET-28821 (new tokens are the dilution figure); the Meteora coin route answers 200 (the tick's
miss was transient). Doubt, unverified: Collector Crypt's revenue is pack sales net of buybacks; DefiLlama's wording does not mention the cost of the cards kept.

**Every tab, measured 2026-11-10 on the snapshot of 06:52 UTC (237 apps, 32 chains, 11 picks; not yet the operator's word)**

Top Picks
15. A card says both. PUMP, USUAL and MET pass the Growing gate ("+16% / mo, grows over 6 mo") and carry "Not growing" under Watch out
    (revenue fell over the last 90 days, or 30-day revenue is 15% to 26% of its best). 3 of 11 picks.
16. The Tier List grades by upside alone: all 6 coins of tier A and all 7 of tier B failed a gate (thin liquidity 8, heavy dilution 5).
17. Item 12 on this snapshot: on holders' revenue CARDS 0.4x, MET 0.6x, LDO 0.0x, TWT 0.0x, ORCA 0.9x; GMX 8.5x, PUMP 3.6x, USUAL 2.6x, SDT 1.7x; DOLO and RHEA unknown.
18. 5 of 11 picks pass Liquid on all-venue volume with a pool slip of 3.1% to 8.7% (GMX, DOLO, TWT, LDO, USUAL). Said on the card; left.
19. Forward record: picks against BTC -0.7% to +1.5% over the last six cohorts, the control the same. First reading 12 Nov.

Chains
20. The two yardsticks disagree: of 26 chains with both, 7 are 5x or more apart (Sui 2.1x on adoption, 0.01x on fees; Plasma 16x and 1.3x;
    Tron 5.2x and 40x; Starknet 1.6x and 25x). Spearman 0.57. The fee figure is in the detail only.
21. The list is led by chains that shrank: Arbitrum's DEX volume is 71% under a year ago, Plasma's 82%, OP's 31%; Chains have no gate.
22. "Held back" cuts 10 of 32 chains by construction (the 80th percentile of turnover): Solana loses half of its DEX volume (3.2x, 3.8x without)
    and is left out of the benchmark set for it.

Sectors
23. Hot is only "ahead of the median sector". All 12 sectors fell 13% to 32% in four weeks and all 12 lost to BTC; 4 read Hot (RWA at -22%,
    13 points behind BTC, 0.8 ahead of the median). DeFi lending is Hot on +1.1 and +0.1 points. 10 of 12 changed stage in four weeks.
    The page's own arrows call anything within 3 points flat; 7 of 12 sit within 3 points on one axis.
24. Talked about rests on 817 people in a week; 2 of 12 sectors have a figure, the rest read "too few".

Altseason index
25. It rolls on Tuesday: Monday's four refreshes still showed the week of 2 Nov (24.6); 06:52 UTC on Tuesday brought 9 Nov (22.2). CoinMarketCap's
    page for Sunday 8 Nov was there. Their own limit is 10 days, so not filed.
26. #312 stands: the tile reads 15, the index uses 47.

Seen by the operator in the mock outbox/gem-screener-review on 10 Nov and refused: 1/15 (Not growing fails the gate: a big earner may
stall), 2/16 (Tier List reasons), 4/13 (upside after dilution), 6/20 (fee upside on the row); "skoro nic se mi nelibi, vypada hnusne".

Filed from this pass: #334 (the Supply column says "being fetched" after its batch answered 503 and is never asked again).

Refused by the operator on 10 Nov: changing the benchmark. Refused on 2 Nov, seen in the mock: the band word with its range, a flag for a collapsed price, growth with its window and fit, six gate dots on the Apps row, capped upside marked, the theme-lagging flag as one page line.
