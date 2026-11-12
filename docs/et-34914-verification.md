# ET-34914 verification (Capital Maximizer: the look of the top 3, Plan notes, Leverage route, four faults)

Shipped 2026-11-12 12:30 UTC (deadline 09:59 UTC). Read 2026-11-12 12:55-13:10 UTC, signed out, in a fresh Chromium tab at 1440 px
and 390 px: OG Gambler, High Risk and Conservative, 5,000 USDC, FIND TOP 3, each card's SELECT STRATEGY; `/tiers`, `/top3`; the V4
Quoter by eth_call. Page script and stylesheet `capital-maximizer.{js,css}?v=20261112-1`: our patch.js and patch.css, nearly as drawn.
Mock: `outbox/capital-maximizer/look/` (pictures 1-4).

| Done when | Result | Evidence |
|---|---|---|
| 1-2 Rows at one height, order of 1, trees at one scale (1440) | PASS | OG: profit 523, facts 612, steps 1017, chips 1159, button 1247, Details 1295 on all three cards; names 428/428/418 (a two-line name, as in the mock). Trees at scale 0.899, 0.897, 0.899. Order as drawn. |
| 3-4 No note paragraph with Details closed; every note in Details; chips | PASS | No paragraph over 90 characters outside a closed Details on any card (OG, High). Details hold the notes, the fresh-wallet checks, the rate basis and the risk line (OG #1 4 rows, #3 7). Chips: Fresh wallet ✓, Range, Full range, Past loss, Matures in. |
| 5 Plan shows chips and Details, no boxed notes | FAIL | The Plan never opens. SELECT STRATEGY on each of 6 cards (OG, Conservative) throws "ruleHtml is not defined": renderPlan (line 519) calls a function the build removed. No START. Bug #348. |
| 6 OG's Leverage route one band | PASS | Name and venue; LEVERAGE 4.25x, MAX PROFIT +$181, PRICE +20% +$2,306, PRICE −20% −$5,000 "liquidated, the deposit is lost", LIQUIDATED AT ETH down 2.6%; the scale with its red line; chips; Details 8. |
| 7 No NaN; borrow plate at its own row; no plate overrun; 4.25x inside its diamond | PASS | No plate reads NaN (OG, High); no two nodes share a spot; no plate text longer than its plate; diamond 36 wide, "4.25x" 33. |
| 8 LIQUIDATED AT names the ETH move (about 2.6%); no loop sentence | PASS | "ETH down 2.6%"; `/tiers` scenarios now `liquidation_move_pct 2.6`, `position_liquidation_move_pct 1.3`, `price_basis "underlying"`, so the loop sentence is not added. |
| 9 A Fluid smart vault route, or a row saying why none | FAIL | Not built; Nexus: "we do not have a rate source for them that we can check yet". No row on the page or in `/route` says so. |
| 10 Looks like the pictures at 1440 and 390 | PASS | Side by side with pictures 1, 2 and 4: same layout, sizes, colours and order; at 390 the name beside its rank, TOP PICK under it, facts two by two, the Leverage band two by two; no sideways scroll. The Plan screen could not be seen (5). |

Also found: High Risk #2 and #3 start again with "Swap 5,000 USDC to sUSDfr" on Uniswap V4, a pool holding only USDC (buying reverts
at 1 USDC, selling works); their fresh-wallet tick counts the pool's value on the wrong side. Bug #349, the defect of #338 back.

Score: 6 of 8 pass, 2 fail (5: SELECT STRATEGY broken; 9: Fluid not built). Verdict: the operator's word.
