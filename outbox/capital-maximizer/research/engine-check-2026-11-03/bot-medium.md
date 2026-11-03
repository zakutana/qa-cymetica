# Capital Maximizer, Medium tier: independent finder

5,000 USDC, Ethereum, snapshot 2026-11-03 04:19 UTC. 580 candidate routes scored. Modest answer: about $35 a month. #1 and #2 are $1.19 apart, and the order depends on Sky's USDC-USDS swap being free. #2 and #3 are largely the same trade.

| # | Route | Net APY | Costs | Max profit/month | Liquidation |
|---|---|---|---|---|---|
| 1 | stUSDS / USDC loop, 3x, on Morpho | 9.78% | $5.00 | **$35.17** (0.70%) | 22.48% |
| 2 | Pendle Ecosystem High Yield USDC vault (pendleUSDChy) | 9.00% | $3.00 | **$33.98** (0.68%) | none |
| 3 | RockawayX USDC Yield vault (roxUSDCy) | 7.52% | $3.00 | **$27.92** (0.56%) | none |

## Top 3
**1. stUSDS / USDC loop, 3x, on Morpho.** USDC to USDS (Sky PSM), USDS to stUSDS (Sky), supply on Morpho stUSDS/USDC (LLTV 0.86), borrow USDC, repeat with a flash loan to 3x. Leverage 3.0x. 3x is the tier cap. LLTV 0.86 would allow 7.14x, and the 5% liquidation rule is not binding (22.48% at 3x).
  - collateral yield: pool `9f71f0fd-cfac-54b1-865e-37338f481708`, sky-lending, Ethereum, STUSDS, TVL $180.8M, apyBase 7.19, 7d None, 30d 6.03482, used 6.0348
  - collateral supply (market row): pool `bc861b66-6c05-412f-9540-6ead2b7fb6c7`, morpho-blue, Ethereum, STUSDS, TVL $8.1M, apyBase 0, 7d None, 30d 0, used 0
  - borrow USDC: pool `bc861b66-6c05-412f-9540-6ead2b7fb6c7`, morpho-blue, apyBaseBorrow 4.16463, supply $8.07M, free $2.13M
  - costs: swap $0.0, gas $5.0; gross $40.17
  - liquidation against: stUSDS oracle value vs USDC (LLTV 0.86, no e-mode on Morpho); oracle type not read
  - risk: stUSDS reads as funding Sky's staking-engine USDS loans against SKY (one report; another source describes it as a savings vault). In the snapshot those loans are about $161M (lendBorrow 370a27ed: $553.87M supply, $392.60M free) against $180.8M stUSDS: if that link holds, about 89% used and about $19M idle, so a $15k exit is small unless use reaches 100%. Not verified on Sky's own docs. The Morpho market is small ($8.07M).
  - check: Swap fee 0 for USDC-USDS-stUSDS (Sky states one-to-one without exchange fees; stUSDS no contract-level fee from a third-party doc). At the brief's default 0.05% each way the cost is $20.00 and the month $20.17, and it falls below the vaults: top 3 would become pendleUSDChy, roxUSDCy, Re Ecosystem vault ($25.91). So #1 and #2 are a tie within this one assumption ($1.19 apart). stUSDS used 6.03 by the rule; its 30-day low was 5.07, at which net is 6.88% and the month $23.28. Borrow: Morpho API: now 4.16, week 4.61, month 4.65; at 4.65 net 8.80%, $31.18/month. Not very different.

**2. Pendle Ecosystem High Yield USDC vault (pendleUSDChy).** Deposit USDC in the Morpho V2 vault 0xcf609F83..., curator Armitage by Wintermute; no swap. Leverage 1.0x. No leverage.
  - earn: pool `de80de60-a80f-5634-a0b2-1fb16335ce18`, morpho-blue, Ethereum, PENDLEUSDCHY, TVL $11.1M, apyBase 8.99915, 7d None, 30d 13.17634, used 8.9992
  - costs: swap $0.0, gas $3.0; gross $36.98
  - liquidation against: None: no borrow
  - risk: A 3-week-old vault (first seen 2026-10-14) that lends almost only against PT-reUSD ($7.12M) and PT-USD3 ($4.82M), one borrower type; rate is volatile: last 7 days 6.79, 6.23, 17.43, 5.68, 6.83, 8.81, 9.11, and a 114.41 day inside 30 days.
  - check: apyReward 1.20 excluded. Median of the last 7 days is 6.83: at that rate the month is $25.07. Morpho's own net APY reads 8.47 incl. rewards, below DefiLlama's 8.99 base. Deposit gate unset but not abdicated: the curator could add one.

**3. RockawayX USDC Yield vault (roxUSDCy).** Deposit USDC in the Morpho V2 vault 0xE0181090..., curator RockawayX; deposit gate abdicated; no swap. Leverage 1.0x. No leverage.
  - earn: pool `caa9ffc0-2983-4c18-9556-4e3ad4dfe6ac`, morpho-blue, Ethereum, ROXUSDCY, TVL $35.4M, apyBase 7.52292, 7d None, 30d 8.14733, used 7.5229
  - costs: swap $0.0, gas $3.0; gross $30.92
  - liquidation against: None: no borrow
  - risk: 65% of it lends against PT-reUSD ($23.13M of $35.4M), rest fxSAVE, mF-ONE, strUSD, USPC, PST: curated credit-like collateral.
  - check: apyReward 0.92 excluded. A 25.33 day inside the last 7; the 7.52 used is the current rate.

## Just outside the top 3, and why
- roxcUSDC: deposit gate set (Morpho API sendAssetsGate 0x51f667..., contract name WhitelistSendAssetsGate on Blockscout), so a user cannot simply deposit. $28.69 on paper.
- m1USDC: a deposit gate is set too (0x34b456...); gate contract not read. $25.79 on paper.
- Fluid GHO on Plasma: base 35.9 is a 2-day spike (last 7 days 3.44, 3.80, 3.84, 5.07, 4.91, 29.23, 35.85); the 30-day mean 9.05 is lifted by those two days, so 9.05 is not a lasting rate. $28.86 by the letter of the rule.
- Kamino Institutional Commodity Yield: off-chain trade-finance fund, KYC listed 'unknown' on DefiLlama, withdrawals beyond the buffer queue for up to about 3 months, 19 days of history. $29.13 by the letter of the rule; it would be #3 if KYC clears.
- Kamino Institutional USDC: same doubt. $27.79.

## Families searched
| Family | Routes |
|---|---|
| Stable lending (Aave, Compound, Spark, Fluid, Euler supply, Kamino, HyperLend, BENQI, Dolomite) | 58 |
| Morpho vaults, including younger ones | 68 |
| Savings stables (sUSDe, sUSDS, stUSDS, sDAI, sDOLA, wsrUSD, stcUSD, sUSDai, sGHO, scrvUSD) | 10 |
| Stable LP (Curve, Convex, Stake DAO, Uniswap V3/V4, Kamino Liquidity) | 41 |
| Pendle PT held, stable (4 of them mature inside 30 days and are dropped) | 10 |
| Pendle LP, stable | 5 |
| LST hold | 9 |
| Stable loops (Morpho, Aave, Fluid, FiRM, Kamino, Dolomite) | 72 |
| PT loops, stable | 6 |
| LST/ETH and LRT/ETH loops | 38 |
| LST against stables (long ETH) | 115 |
| Outside holds, not passed or unlisted | 148 |
| **Total** | **580** |

Leverage paid in 8 of 231 loops; in the rest 1x beat it after first-month costs. Named routes per month, loops forced to 3x:

- sUSDe/PYUSD Morpho 3x: net 6.63%, -$2.73
- sUSDe/USDT Aave e-mode 3x (e-mode 0.90 assumed, not verified): net 6.48%, -$3.37
- sUSDS/USDT Morpho 3x: net 4.70%, +$4.32 (sUSDS held 1x earns more)
- sUSDai/USDT0 Fluid Arbitrum 3x: net 8.27%, +$5.60
- sDOLA/DOLA FiRM 3x: net 7.14%, -$0.68
- wstETH/ETH Fluid Arbitrum 3x: net 3.19%, -$10.27
- wstETH/WETH Spark 3x: net 2.84%, -$13.33
- stETH held: 2.28%, -$4.64

## Outside their passed set
| # | Route | Net APY | Max profit/month | Liquidation |
|---|---|---|---|---|
| 1 | PT-USD3-17DEC2026 / USDT loop, 3x, on Morpho | 30.31% | $87.77 | 27.14% |
| 2 | Axis sUSDx, hold | 15.49% | $54.67 | none |
| 3 | fxSAVE / USDC loop, 3x, on Morpho | 15.21% | $42.49 | 27.14% |

**1. PT-USD3-17DEC2026 / USDT loop, 3x, on Morpho.** Pendle and Morpho are both passed; the yield is 3Jane's, which is not on their list. Their list treats issuers as platforms (Ethena, Sky, Cap, USD.AI), so we keep it out of the top 3. Vaults #2 and #3 do lend against PT-USD3 and PT-reUSD, but there the user holds USDC over-collateralised at LLTV 0.86-0.915, not the token.
  - collateral yield: pool `b6490fe9-b16a-4ccf-8701-cbded659b397`, pendle-v2, Ethereum, USD3, TVL $6.0M, apyBase 15.52817, 7d None, 30d 15.09271, used 15.0927
  - collateral supply (market row): pool `888aaa18-499e-5af3-a001-44a3db046553`, morpho-blue, Ethereum, PT-USD3-17DEC2026, TVL $11.9M, apyBase 0, 7d None, 30d 0, used 0
  - borrow USDT: pool `888aaa18-499e-5af3-a001-44a3db046553`, morpho-blue, apyBaseBorrow 7.48593, supply $11.92M, free $1.34M
  - costs: $36.77; liquidation against: the market's PT-USD3 oracle value vs USDT (LLTV 0.915); oracle type not read
  - risk: USD3 is the senior tranche of 3Jane's fintech and unsecured credit, 15% implied vs 6.23 native says the market prices that risk; DefiLlama marks it not stablecoin. KYC for lenders not confirmed either way: public deposits reported, no statement found.
  - Pendle fee: $87.77 if Pendle's fee scales with time, $8.75 if it is flat; unconfirmed
  - borrow: Morpho API: now 7.46, week 4.75, no month figure yet (young market). Free liquidity 1.34M in the snapshot, 0.39M when read later: fine for $10k.
  - PT-USD3 / USDC (pool 032bee19-6763-4f4d-862f-f4cf0e1774c3), borrow 8.87: net 27.5292%, $86.36/month, 22.48% to liquidation; borrow week 13.56, month 9.32 (very different week); at 9.32 $82.7. PT-USD3 held 1x: 15.09%, $50.77/month.
  - should it pass: Should be looked at, not passed blind: the venues are passed, but 3Jane opened public deposits only recently and its credit book was not checked; a passed Pendle lets this in unless issuers are vetted.

**2. Axis sUSDx, hold.** Axis is not on their list
  - earn: pool `edf44260-d78f-5dab-853a-f89c4f523169`, axis, Ethereum, SUSDX, TVL $53.7M, apyBase 15.49263, 7d None, 30d 16.66335, used 15.4926
  - costs: $9.0; liquidation against: None: no borrow
  - risk: Young synthetic dollar on a market-neutral book; standard redemption up to 7 days, instant about 0.3%: the 0.05% used is the brief's default, at 0.3% out the month is $42.17. KYC not confirmed.
  - PT-sUSDx-03DEC2026 pays 17.15% ($60.25) but matures 29.8 days after the snapshot, so it just misses a 30-day hold; pool 23a70f1a.
  - should it pass: Not yet: thin sourcing, KYC unknown.

**3. fxSAVE / USDC loop, 3x, on Morpho.** f(x) Protocol / Concentrator is not on their list; the Morpho market is
  - collateral yield: pool `ee0b7069-f8f3-4aa2-a415-728f13e6cc3d`, concentrator, Ethereum, FXSAVE, TVL $72.9M, apyBase None, 7d None, 30d 6.85825, used 6.8582
  - collateral supply (market row): pool `9357d127-efb2-55fb-ab2f-005bf18f6d32`, morpho-blue, Ethereum, FXSAVE, TVL $23.0M, apyBase 0, 7d None, 30d 5.03256, used 0
  - borrow USDC: pool `9357d127-efb2-55fb-ab2f-005bf18f6d32`, morpho-blue, apyBaseBorrow 2.68387, supply $22.97M, free $6.51M
  - costs: $20.0; liquidation against: fxSAVE oracle value vs USDC (LLTV 0.915)
  - risk: fxSAVE yield is DefiLlama's 30-day mean only (apyBase null), under project 'concentrator'; the 2.68 borrow is a current low.
  - borrow: Morpho API: now 2.68, week 4.16, month 4.09: very different. At 4.09 net 12.39%, $30.94/month.
  - should it pass: Reasonable candidate: permissionless and live for years, by our knowledge, not checked here.

- apyUSD / USDC 3x (Morpho, unlisted Apyx): $94.17/month on paper, not listed above: about 30-day redemption cooldown, mint licensed to institutions, and a June 2026 depeg per one third-party page.
- Maple syrupUSDC hold (not passed): 5.1051%, $17.98/month, TVL $2489M, pool 43641cf5-a92e-416b-bce9-27113d3c0db6. Worth a re-look at why it fails; a loop does not beat the hold in month one.
- Veranta 22.69%, Growi HF 18.36%, Accountable 12-14%: Above these on paper; not put forward, we could not say they are reputable or KYC-free.

## Looks wrong or suspicious
- Brief vs file: the brief names Pendle PT as an outside example, but pendle-v2 is passed: true in platforms.json (41 passed, as stated). We kept Pendle in.
- A KYC token sits behind a passed venue: PT-sUSDfr 26.66% ($91.13/month, the highest figure on Pendle). USDfr is minted only by KYC-verified addresses (CoinGecko). PT-reUSD ($44.45 at 3x): Re's FAQ makes KYC mandatory and excludes the US. Both are out here; an engine that only checks the venue would show them.
- A pool that looks open but is not: roxcUSDC and m1USDC have deposit gates; DefiLlama lists both as ordinary pools.
- The lowest-of-three rule has two holes. When apyBase is null the 30-day mean is reward money: Sky USDS GROVE farm (5.74, reward 5.69), Spark USDS SPK farm (4.09), Convex cvxCRV (12.34); we skipped 5 such pools. And a 2-day spike lifts the mean: Fluid GHO on Plasma, 9.05 from a normal 3-5%.
- One-day jumps moved together in the vaults lending against PT-reUSD: pendleUSDChy 114.41 and 17.43, roxUSDCy 25.33, roxcUSDC 39.64 in the same week; Morpho's PT-reUSD/USDC borrow week is 12.76 against 9.31 now.
- PT-USD3 is flagged stablecoin false while PT-sUSD3, its junior tranche, is true.
- Vaults #2 and #3 are largely the same trade: lending USDC against PT-reUSD on Morpho (59% and 65%). The top 3 is two bets, not three.
- pendleUSDChy: DefiLlama apyBase 8.99 is above Morpho's own all-in net 8.47 for the same vault, read later in this run. Which is right was not resolved; 8.99 is used because the brief names DefiLlama.
- lendBorrow.ltv means different things: LLTV on Morpho, collateral factor on Fluid, base max LTV on Aave, 0 for e-mode-only collateral such as sUSDe. 423 lendBorrow rows have no match in pools.json.
- Dolomite on Ethereum shows borrowable false on its larger rows (USDC, USD1, WETH) while quoting borrow rates and borrows. Not used.
- Morpho's API read during this run shows smaller markets than the snapshot (stUSDS/USDC $7.04M supply, $1.10M free vs $8.07M, $2.13M). Snapshot figures are the ones used. Clock difference between the two not established.

## Limits of this run
- Pendle fee: feeRate from Pendle's API treated as annualised, scaling with time to expiry (from what we know of its AMM; the docs page returned 404, so unconfirmed). feeRate is about 1.85% of implied APY across markets, which may mean the figure is already scaled. If it were a flat fee, PT-USD3 / USDT at 3x would be $8.75 and 1x would beat it. No top-3 route uses Pendle.
- DefiLlama chartLendBorrow answered 402, so 30-day borrow comes from Morpho's API; none for non-Morpho legs.
- Aave's API could not be read by GET, so Aave e-mode was assumed at 0.90 for e-mode-only collateral. None of these routes reach the top.
- Euler V2 supply was scored; Euler loops were not, lendBorrow has no collateral LTVs there. Its USDC borrow at 5.57% or more would not beat stUSDS at 4.16 unless a cheap vault accepts a good yield token; eUSD0 at 1.5% was not followed.
- Volatile LP and perps house pools are outside the Medium definition (180 pools not scored); GMX, HLP and JLP are not passed anyway. weETH and ezETH are treated as restaking, not Medium.
- KYC checks were done for the routes that reached the top, not for all 580.

Method and full route data: bot-medium.json. Scripts: work-medium/score.py, report.py.
