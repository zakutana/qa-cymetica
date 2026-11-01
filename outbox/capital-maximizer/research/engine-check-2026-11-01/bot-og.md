# Capital Maximizer, tier og: blind top 3

5,000 USDC, home chain Ethereum. Snapshot: DefiLlama pools + lendBorrow, 2026-11-01 08:32 UTC. Full numbers: `bot-og.json`. Scripts: `work-og/score.py`, `work-og/build.py`. All 586 scored routes: `work-og/candidates.json`.

**Blindness:** I read the first 2,500 bytes of `tiers.json` while getting oriented. That showed their best route for conservative (Fluid USDC 5.89%) and medium (Ethena sUSDe 4.98%), plus the name of high's best (ETH-USDC house pool). I did not reach the og entry. I did not open `top3-*.json`, `cm.js` or the rest of `tiers.json`.

## 1. Top 3: their rule applied literally, after costs

| # | Route | Pool (DefiLlama) | TVL | base / 7d / 30d → used | Net APY | Costs | $/month | % |
|---|---|---|---|---|---|---|---|---|
| 1 | Uniswap V3 WETH/USDT 0.05%, Ethereum | f7dd8768-77be-4f91-96d6-dd563ac23dd5 | $10.05M | 27.33 / 81.07 / 37.93 → **27.33** | 27.33% | $29.00 | **$71.27** | 1.43% |
| 2 | Uniswap V3 AAVE/WETH 0.3%, Ethereum | 472f422f-f809-4764-8169-b3e40e532bb3 | $6.69M | 40.30 / 85.81 / 29.94 → **29.94** | 29.94% | $46.00 | **$62.80** | 1.26% |
| 3 | Uniswap V3 USDC/WETH 0.01%, Ethereum | 8b3ed515-5e6f-449a-9b64-25113cda7a29 | $9.53M | 48.24 / 22.23 / 28.87 → **22.23** | 22.23% | $25.50 | **$57.68** | 1.15% |

- **Path:** swap USDC into the pair, add the liquidity on Ethereum, and reverse it on exit. No borrowing, so no leverage and no liquidation. About half the capital is ETH (on #2, AAVE and ETH). Price moves and impermanent loss are not counted, as the rule says.
- **Costs** are swaps in and out at the known Uniswap fee tiers, plus the brief's 0.3% to enter and leave an LP ($15), plus gas at $1 per Ethereum transaction (11 / 11 / 8 transactions). The $15 may double-count on Uniswap V3, where the swap is already priced. Without it every LP gains $15 and the ranking does not change.
- **Risk:**
  - **#1:** the rate is the pool average over concentrated liquidity. A full-range position earns less; a tight range earns it only while ETH stays inside the range.
  - **#2:** see the spike line below.
  - **#3:** $126M a day trades through $9.5M of liquidity. That makes it a JIT/MEV venue, and a retail LP takes a fraction of the average.
- **Next two:**
  - **#4:** Uniswap V3 USDC/WETH 0.3% on OP Mainnet (b2cca178), 21.21%, **$56.12**. Its TVL is $5.05M, right at the floor.
  - **#5:** Uniswap V3 LINK/WETH 0.3% on Ethereum (3025b6b3), 26.01%, **$49.90**.

**Spike line (the main caveat):** #2 and #5 make the list chiefly because of a one-day fee spike. AAVE/WETH had one day at 448.9% on 2026-10-29, and LINK/WETH one at 368.7% on 2026-10-30. That day sits inside all three of the rule's readings. Their 30-day medians are 9.81% and 11.37%. At those rates they net **-$7.40** and **-$1.56** in month 1. #1 and #3 are robust: their medians are 26.27% and 23.53%. If each rate is capped at its 30-day median, the top 3 becomes WETH/USDT 0.05% ETH **$67.78**, USDC/WETH 0.01% ETH **$57.68** and USDC/WETH 0.3% OP **$56.12**. That set holds only WETH and stables, which is the tier's own asset list. The medians come from DefiLlama `/chart/<pool>`, which is not in the snapshot.

## 2. Families searched (502 routes on passed platforms, 84 outside)

| Family | Scored | Best | $/month |
|---|---|---|---|
| Volatile LP (Uniswap V2/V3/V4) | 76 | WETH/USDT 0.05% Ethereum | 71.27 |
| LST/LRT loops vs ETH (Aave e-mode, Morpho, Fluid, Compound, Spark, Euler) | 55 (12 negative spread, 22 too small/illiquid) | Morpho wstETH/WETH LLTV 94.5%, Ethereum, 5x, net 5.89%, liquidation 15.3% away on wstETH/ETH | 5.59 |
| Stable loops (sUSDe, sUSDS, stUSDS, sUSDai, wsrUSD, stcUSD, sDOLA vs stables) | 54 (24 negative) | Morpho stUSDS/USDC LLTV 86%, 5x, net 14.39%, liquidation 7.0% away on stUSDS/USDC | 22.57 |
| SOL LST loops (Kamino) | 5 (3 negative) | mSOL/SOL 1.25x | 0.60 |
| Perps house pools (GMX V2 GM) | 5 | ETH-USDC GM 3.91% | -2.58 |
| Curve/Convex volatile / stable | 34 / 30 | crvUSD-WBTC / apyUSD-apxUSD | -20.22 / 16.04 |
| Kamino Liquidity | 4 | syrupUSDC-USDC | -3.81 |
| Stable LP (Uniswap) | 13 | USDC/USDT Ethereum | 18.82 |
| Stable lending (Aave, Morpho vaults, Kamino, Fluid, Compound...) | 121 + 9 Morpho markets | Morpho API3-DCOMP-USDC 9.91% | 35.98 |
| Savings stables / LST hold / volatile lending | 11 / 11 / 74 | sUSDai 6.20% / mSOL 5.04% / Morpho ROXTORI 7.58% | 16.28 / 6.76 / 13.12 |

Loops earn little in month 1 because the brief charges swap fees in and out on the whole leveraged amount. I could not check the 30-day borrow history: DefiLlama's lendBorrow chart is a paid endpoint.

## 3. Outside their passed set (max 3)

| # | Route | Numbers | $/month | Platform verdict |
|---|---|---|---|---|
| 1 | Pendle PT-USD3-17DEC2026 looped on Morpho (USDT debt), Ethereum, 5x | PT fixed 15.03% (b6490fe9, $6.02M). Borrow 2.45% (888aaa18, $8.28M, $0.96M free). LLTV 0.915, so liquidation is 12.6% away on PT-USD3/USDT. Net 65.33%, costs $33 | **$177.94** | Pendle should pass. DefiLlama shows TVL since 2021-06-16 (api.llama.fi/protocol/pendle, read 2026-11-01), so the fail reason, "launch date could not be read", is the checker's gap. I did not check audits. |
| 2 | Pendle PT-reUSD-10DEC2026 looped on Morpho (USDT), Ethereum, 5x | PT 12.05% (7abaf885). Borrow 8.63% (c1e92dcc, $18.56M). Liquidation 12.6% away. Net 25.73% | **$61.99** | Same platform as #1. |
| 3 | Orca SOL/USDC LP, Solana | 14.47 / 51.27 / 52.30 → 14.47 (a5c85bc8, $25.83M). Costs $23.55, including the CCTP round trip | **$32.31** | Orca should pass. DefiLlama shows TVL since 2021-04-14 (api.llama.fi/protocol/orca), and it failed only on the launch-date read. I did not check audits. |

- **#1 caveats:**
  - **Market age:** the 2.45% borrow is on a Morpho market whose history starts 2026-10-26, so it is 6 days old.
  - **Sibling markets:** the two other PT-USD3 markets borrow at 5.72% and 10.09%. On the 10.09% market (LLTV 0.86) the 5x loop nets 34.8% ($91.17), with liquidation 7.0% away.
  - **USD3:** 3Jane's dollar, which lends to identity-verified borrowers. Holding the PT showed no identity check in the snapshot; I did not verify it.
- **Dropped:**
  - **PT-sUSDfr hold:** 26.91%, $87.89. I cannot identify the issuer of sUSDfr from the snapshot.
  - **Yield Basis YB-WETH:** treated as a data artifact; see section 4.

## 4. What looks wrong in the data

- **The rule does not remove a one-day spike.** Once the spike is inside "now", the 7-day and the 30-day mean, it passes through. Examples: AAVE/WETH and LINK/WETH above. Their engine will rank them the same way if it applies the rule literally.
- **Reward rows pass as base rates.** A row with no apyBase and a non-zero apyReward passes the literal rule, because DefiLlama's apyMean30d includes rewards. Examples: Convex cvxCRV 11.97%, Sky SKY staking 5.76%, Sky USDS GROVE farm 5.70%. I excluded them.
- **Their finder searches less than their passed list.** `platforms.json` marks 36 platforms as passed, but only 10 are `in_finder`, and `routable_chains` has 6 of 17 chains (Base, Monad, HyperEVM and Plasma are missing). Morpho, Curve, Convex, Kamino Liquidity and Sky pass but are not searched, so both family-best loops (each on Morpho) are outside their finder. My top 3 are on Uniswap V3 Ethereum, which the finder does reach.
- **The launch-date check fails old platforms.** Pendle, Orca, QuickSwap, Beefy, Stake DAO, StakeWise and BENQI all fail on "launch date could not be read". DefiLlama's first TVL days for them are 2021-06-16, 2021-04-14, 2020-10-08, 2021-05-26, 2021-03-01, 2021-01-26 and 2021-08-19 (api.llama.fi/protocol/{slug}, read 2026-11-01).
- **Yield Basis YB-WETH Unstaked #10:** apyBase 731.10% now and 56.53% over 30 days, with 43 days of history. Its sibling pools read 0–2%.
- **Origami SUSDS-S:** apyMean30d 2391.87%.
- **Sky stUSDS:** 10.70% now against a 30-day mean of 5.79%.
- **Morpho API3-DCOMP-USDC:** 58.44% now against a 30-day mean of 9.91%.
- **Uniswap V3 Base WETH/USDC 0.3%:** 6.84% now against a 30-day mean of 55.12%.
- **Kamino SOL LST loops are negative today:** JitoSOL earns 4.77% and SOL costs 4.92% to borrow.
- **One collateral, three borrow rates:** the same PT-USD3 collateral borrows at 2.45%, 5.72% and 10.09% across three Morpho markets.
- **GMX slug:** DefiLlama's slug for GMX V2 is `gmx-evm`, not `gmx-v2-perps`.

**Method:**
- Each earn rate is the lowest of base, 7-day and 30-day mean.
- 30-day profit = 5,000 × ((1+APY)^(30/365) − 1) − costs. The linear figure is in the JSON.
- Loop leverage is picked for the highest profit after costs, with liquidation at least 5% away.
- Liquidation thresholds: Morpho uses its LLTV. Aave e-mode values come from api.v3.aave.com. Fluid, Compound, Kamino and Spark use their LTV as the threshold, which is conservative.
