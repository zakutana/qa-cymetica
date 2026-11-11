# ET-34229 verification (Capital Maximizer engine)

Shipped 2026-11-10 07:15 UTC (deadline was 2026-11-06 06:30 UTC; BB-LATE). Read 2026-11-10 from 07:17 UTC: one snapshot (`research/finder/snapshot.py`: their `/tiers`, `/platforms`, `/top3` x4, DefiLlama, Morpho, Aave, Fluid, Pendle), `score.py` on it by lasting with DefiLlama's 30-day charts, `/route` for the 32 route ids we have seen in each tier, and the live page in the in-app browser. The page script is still `capital-maximizer.js?v=20261103-3`: the engine changed, the page did not.

| # | Done when | Result | Evidence |
|---|---|---|---|
| 1 | Tier cards read as in 1; lev_max OG lender's limit, High 5, Medium 3; a route liquidated within 5% can show | PARTIAL | The four tier lines match. High wstETH loop lev_max 5, OG 5.5 (lender's limit, liq 0.2%); Revert 4.25x at liq 1.3% shows. Medium 3 cannot be seen: no dollar loop is offered in Medium at all. sUSDfr (Staked Forest Road Dollar, a dollar, Pendle "stables") is classed `pt_hold_other` and offered from High only, so Medium misses a dollar route at $89.87. GMX house pools 404 in High (OG only), though High adds house vaults. |
| 2 | score.py, same minute, by lasting: each tier's #1 within 10% of the finder's best on their list | FAIL | Conservative: $20.52 vs Fluid Ethereum $21.06 (-3%). Medium: $45.97 (PT-apyUSD market) vs PT-USD3/USDT 3x on Morpho $55 at today's PT 15.51% and borrow 5.40% (-16%); 3Jane is on their Platforms with 0 routes. High: $89.87 (PT-sUSDfr) beats our $67 (PT-USD3/USDT 5x). OG: $353.44 (ZEC-USDC) vs Arcadia 7x on Base WETH-USDC 0.3% $455 (-22%); without Base our best is ZEC-USDC $346, so OG fails only through line 4. |
| 3 | Revert Lend, Arcadia, Loopscale on Platforms; OG top 3 or Leverage route holds a levered pool | PASS | All three listed (Revert and Arcadia pass OG only, under the $10M floor elsewhere; Loopscale every tier, 1 route). OG #3 is a Revert Lend levered pool (WETH-USDT 0.05% Ethereum 4.25x, then WETH-USDC 0.3% Arbitrum on a later read). |
| 4 | routable_chains holds Base, and at least one Base route is built | FAIL | `routable_chains` has 16 chains, not Base; `listed_only_chains: ["Base"]`, "no route ends there: accounts are funded on Ethereum mainnet". Veranta (Base) has 0 routes for the same reason. |
| 5 | Each route kind in 5 returns from /route where the tier allows it | PARTIAL | USDC direct into Morpho dCOMP/USDC: yes, Medium #2, $35.12, note "One borrower holds 100%". stUSDS/USDC loop: the old id `radc640001b` answers 404 in every tier and no loop is in any top 3; today stUSDS earns 6.36% and its USDC market borrows at 11.0% (4.5% over the week), so a loop would lose today. Fluid smart vaults: no route found; their API has no route listing, so neither is proven absent. |
| 6 | Veranta, Axis, 3Jane on Platforms, or a row names the KYC that stopped one | PASS | All three on Platforms, passed for Medium, High, OG. But 0 routes each: Veranta "on a chain routes do not go to", Axis and 3Jane "none that a route family uses". The goal (offer them) is not met; the line as written is. |
| 7 | WETH-USDT 0.3% shows within 10% of its median figure | FAIL | Their route `r3d38c31e00` shows $54.95 with `rate_basis: no_chart`. Its DefiLlama 30-day median is 30.44 (read 10 Nov, chart's last day 07:02 UTC); our figure on it is $68.62: theirs is 20% under. Counters: `charts_read` 55 of `charts_needed` 862. |
| 8 | A pool's card states its range, a queued route its exit | FAIL | The API has both (ZEC-USDC +-26%, full range 20%; Kamino Commodity "Slow exit ... 1-3 month loans"). The page never shows them: its script reads no `notes` field (0 occurrences), and the card text has no range. The same hides the platform-loss line (goal 3), the borrower line (goal 5) and the by-the-rule figure the (i) says is "shown beside it". |
| 9 | A fresh wallet can open every top 3 route: deposit simulated, no gate | FAIL | Their own "does not do" says "A deposit is not simulated for you here". Our simulation after the verdict (eth_call / eth_simulateV1 from a keyless fresh address with a USDC override, 5,000 USDC): 8 of 11 routes open with no gate (Fluid Ethereum and Arbitrum, the three Morpho direct supplies, both Pendle sUSDfr routes, Revert Lend's first 3,000 USDC borrow against a fresh position); Jupiter Lend simulated from an existing holder only; the two Orca pools not simulated (pools exist, no warning, ZEC has no freeze authority). Pendle opens only through Pendle's router (KyberSwap USDC to USDfr); the card's step 1 on Uniswap V4 cannot fill 10 USDC: bug #338. USDfr's mint is KYC-gated, buying it is not. Evidence: scratchpad `cm34229/deposit/`. |

Bugs filed from this build: #337, OG's top pick ZEC-USDC reads "The pool's value moves with None" (exposure null); #338, High #1 and #2 start with a Uniswap V4 swap into sUSDfr that cannot fill 10 USDC.

Not judged here: the look (card 3 of a levered route draws its diagram at half size and ends higher, the grid aligns to start); the spec left the look out.

Score: 2 of 9 pass, 3 partial, 4 fail. FAIL sent on the operator's word, 2026-11-10 (BB-0058, `outbox/capital-maximizer/verdict-et-34229.txt`).

## Re-ship, 2026-11-10 09:13 UTC

Read from 09:16 UTC; their engine changed again while we read (top 3 `as_of` moved to 09:24 and route ids for PT-sUSDfr changed), so the numbers below are from a second snapshot at 09:29 UTC, `score.py` by lasting on it, `/route` for 34 route ids in each tier, and the live page (script now `capital-maximizer.js?v=20261110-1`, which renders `notes` and `rate_basis`).

| # | Result | What changed |
|---|---|---|
| 1 | PARTIAL | PT-sUSDfr is now `pt_hold_dollar` and Medium #1; GMX house pools now answer in High. Medium's 3x still cannot be seen: no dollar loop in Medium, and High's top 3 holds no loop (Medium and High show the same three routes). |
| 2 | FAIL | Conservative $20.54 vs $21.11 (-3%); Medium $89.84 and High $89.84 beat our $58.23 and $80.96. OG $353.42 vs Arcadia 7x on Base WETH-USDC 0.3% $454.81 (-22%): fails only through line 4. |
| 3 | PASS | unchanged |
| 4 | FAIL | still `listed_only_chains: ["Base"]` |
| 5 | PARTIAL | unchanged: dCOMP direct answers in Medium ($35.09); no stUSDS loop, no Fluid smart vault |
| 6 | PASS as written | unchanged |
| 7 | FAIL | `r3d38c31e00` now says `median30` (median 30.44) but shows $42.92: the rate used is 19.32% = the rule's 23.18 x 5/6, not the median. Same on every route: ZEC-USDC 133.79% = median 153.78 x 0.87 (median lower), Revert 22.65% = median 27.18 x 5/6. The engine takes the lower of rule and median under the label "30-day median". Our median figure: $70.78. charts_read 79 of 860. |
| 8 | PASS | The card shows RANGE (ZEC-USDC +-23%, full range 18%), BY THE RULE, PAST LOSS, LENDER, ONE BORROWER, MATURITY. No queued route is in any top 3 today; the script labels an EXIT note. |
| 9 | FAIL | Page still says "A deposit is not simulated for you here". Bug #338 now hits Medium #1 and High #1 (step 1 still a Uniswap V4 swap into sUSDfr). |

Bug #337 reads right on the card now ("moves with ZEC"); `exposure` is still null in `/route`. Conservative cards of Fluid now show "OG Gambler does not bar a platform for a past loss".

Score: 3 of 9 pass, 2 partial, 4 fail. FAIL sent on the operator's word, 2026-11-10 (BB-0061, `outbox/capital-maximizer/verdict-et-34229-r2.txt`).

## Re-ship, 2026-11-10 12:20 UTC

Their engine was redeployed again near 12:30 (charts_read fell from 114 to 79; rates switched from the lower of rule and median to the median; both sUSDfr routes left every tier). Figures from the snapshot at 12:34 UTC (top 3 `as_of` 12:30). Page script `v=20261110-2`: one change, a note naming OG Gambler is hidden outside OG; the API now drops that sentence, so Fluid's Conservative cards show the past loss alone.

Our own fix: `score.py`'s lasting figure took `min(rate, median)`, while its docstring and our spec say the 30-day median; it now takes the median. Our BB-0061 line 7 point (the lower of rule and median under a median label) was also how our scorer read it. On the median our Conservative top 3 matches theirs to the cent ($23.09, $23.04, $22.55 against $23.09, $23.03, $22.49).

| # | Result | Evidence |
|---|---|---|
| 1 | PARTIAL | Medium and High show the same three routes; no loop in either top 3, so Medium's 3x and High's 5x cannot be seen. |
| 2 | FAIL | Conservative equal. Medium $37.33 (PT-reUSDe) vs Axis sUSDx $54.76 and PT-USD3/USDT 3x on Morpho $55 (PT 15.5%, borrow 5.01%): -32%. High $37.33 vs the same loop at 5x $67.38: -45%. OG $353.42 vs Arcadia 7x on Base $454.81: -22%, through line 4 only. |
| 3 | PASS | Revert Lend WETH-USDT 0.05% 4.25x is OG #3. |
| 4 | FAIL | `listed_only_chains: ["Base"]`. |
| 5 | PARTIAL | dCOMP direct is Medium #3; no stUSDS loop, no Fluid smart vault. |
| 6 | PASS as written | |
| 7 | PASS | WETH-USDT 0.3% now rates on its median (25.37% = 30.44 x 5/6), gross $93.78, the same as ours, and shows $63.57. Ours reads $78.62 only because `score.py` charges a flat 30 bp round trip on every pool (`score.py:213`, `:451`), where they charge the pool's own 0.3% in and out ($30); both are readings of our spec's "a 1% pool does not cost 0.3%". On their cost the median figure is theirs to the cent. |
| 8 | PASS | unchanged |
| 9 | FAIL | unchanged; #338 still reverts at 10 USDC (12:2x). Both sUSDfr routes are gone (PT 25.42% today, $6.3M liquidity). |

Bug #337: fixed in the API too (`exposure: "ZEC"`). The loop figures in line 2 ($55, $67.38) are hunter rows quoted on 4 Nov; today's PT 15.5% and borrow 5.01% (5.40% then) make them slightly better.

Score: 4 of 9 pass, 2 partial, 3 fail. FAIL sent on the operator's word, 2026-11-10 (BB-0066, `outbox/capital-maximizer/verdict-et-34229-r3.txt`).

## Re-ship, 2026-11-10 23:04 UTC (release 08b7469b8)

Read 2026-11-11 from 08:46 UTC: snapshot, `score.py` by lasting (median), `/route`, on-chain quotes, the page (script still `v=20261110-2`; the fresh-wallet line reaches the card as a NOTE).

| # | Result | Evidence |
|---|---|---|
| 1 | PASS | PT-USD3-17DEC2026/USDT loop is Medium #3 at 3x ($68.93) and High #2 at 5x ($87.10); wstETH loop lev_max 5 High, 5.5 OG. |
| 2 | FAIL | Conservative $23.00 vs $22.98; Medium $89.69 beats our $58.14; High $89.69 vs Veranta on Base $93.53 (-4%). OG $361.05 vs Arcadia 7x on Base $485.78 (-26%); off Base our best is ZEC-USDC $354.03, under theirs. Fails through line 4 only. |
| 3 | PASS | Revert Lend WETH-USDT 0.05% 4.25x is OG #3. |
| 4 | FAIL | `listed_only_chains: ["Base"]`; Nexus: "a standing decision of the team, not because of the engine". |
| 5 | PARTIAL | dCOMP direct ($35.90 Medium) and the stUSDS loop (`radc640001b`: Medium 3x $31.16, High 5x $37.31, OG 7x $43.69) answer; Fluid smart vaults are not read. |
| 6 | PASS | Axis sUSDx routes exist (Nexus); not in a top 3. |
| 7 | PASS | WETH-USDT 0.3%: median 34.80, rate 29.0% = x 5/6, gross $105.75, $75.42 after their $30 costs. |
| 8 | PASS | unchanged |
| 9 | PARTIAL | Every top 3 route carries `fresh_wallet` (pool depth, vault `maxDeposit` for an empty address, no identity step); their page says it is not a simulation. Ours: Uniswap V4 USDC/USDfr (fee 375, spacing 4, pool 0x72ef9130...) quotes 5,000 USDC -> 4,991.97 USDfr and 100,000 -> 99,779.79; sUSDfr `maxDeposit` of an empty address is unlimited; Curve frxUSD/USDT and USD3/frxUSD fill 25,000 USDT -> 20,905.98 USD3 and back -> 24,951.58 USDT ($48 round trip, inside their $55). |

Bug #338: fixed by the new path (USDC to USDfr on the open V4 pool, then the sUSDfr vault); their status paid. No sweep check holds it, so no verdict was posted.

Score: 5 of 9 pass, 2 partial, 2 fail; both fails are Base. Verdict: the operator's word.
