# Conservative tier: our blind top 3

5,000 USDC, home Ethereum, snapshot 2026-11-03 04:19 UTC. Tier: stablecoin only, 1x, no price exposure, no IL, blue-chip only.
The honest answer is modest: about $20 a month, 0.4%. Full data: `bot-conservative.json`.

## Top 3

| # | Route | Rate used | Gross 30d | Costs | Max profit / month |
|---|---|---|---:|---:|---:|
| 1 | Aave V3 USDC, Avalanche (via CCTP) | 5.725% | $23.53 | $3.30 | **$20.23** (0.405%) |
| 2 | Fluid Lending fUSDC, Ethereum | 5.200% | $21.37 | $3.00 | **$18.37** (0.367%) |
| 3 | Aave V3 USDC, Base (via CCTP) | 5.078% | $20.87 | $3.30 | **$17.57** (0.351%) |

All three: 1.0x, no borrow leg, no liquidation, no swap, no IL.

| # | Pool id | tvlUsd | apyBase | apyBase7d | apyMean30d | Risk |
|---|---|---:|---:|---:|---:|---|
| 1 | `c4b05318-88af-4536-a834-f5fc8940d2d3` | $5.16M | 5.80167 | none | 5.72493 | 92.5% utilised. $5.2M free of $68.6M supplied, barely over the floor. |
| 2 | `4438dabc-7f0c-430b-8136-2722711ae663` | $132.0M | 5.2 | none | 6.25588 | Smallest venue over our bar. Its DEX sibling fails their audit check. $16.6M withdrawable. |
| 3 | `7e0661bf-8cf3-45e6-9424-31916d4c7b84` | $16.37M | 5.07824 | none | 5.50764 | Base-only 30-day mean is 4.54; on that it earns $15.35 and #3 becomes Fluid Base. |

Gross = 5000 x rate x 30/365. Costs: Ethereum route: 3 tx at $1. Bridged route: 3 Ethereum tx plus 6 at $0.05.
30-day base range (DefiLlama chart): Avalanche 3.36 to 8.72, Fluid 4.42 to 11.59, Base 3.75 to 8.04.

Next: Fluid Base $17.17, Morpho Gauntlet Prime Base $17.05, Steakhouse Prime Base $16.98.

## Decided by us: what "blue-chip" means

The tier wording does not define it, so:
- **Venue:** passed, and platform TVL of at least $500M in `platforms.json`.
- **Morpho vault:** curator Steakhouse, Gauntlet or Spark, no deposit gate, at least 90% lent against BTC/ETH majors. Allocation read from Morpho's API.
- **Product:** no first-loss stake, PT or LP, and it must have an `apyBase`.

If Fluid is vetoed: #2 Aave Base $17.57, #3 Gauntlet Prime Base $17.05.

## Higher dollars we rejected

If their engine shows one of these, this is the argument. This is a selection: Pendle PTs (up to $97.58) and vaults from other curators (up to $52.84) also pay more and fail the same test. All 268 rows with their reasons are in `work-conservative/scored.json`.

| Route | Rate | $/month | Why not |
|---|---:|---:|---|
| Kamino Institutional Commodity Yield | 7.892% | $29.23 | Off-chain trade finance |
| Fluid GHO, Plasma | 9.053% | $28.71 | 2-day spike in the mean; $21k of $7.6M withdrawable; no USDC/GHO venue on Plasma |
| Steakhouse High Yield USDC, Ethereum | 6.328% | $23.00 | 91% outside majors: wFalconX, mF-ONE, PT-reUSD |
| Smokehouse USDC, Ethereum | 5.963% | $21.50 | Same book |
| Wintermute USDC Select, Ethereum | 5.764% | $20.69 | Curator; 38% PT and USD3 |
| Steakhouse High Yield USDC, Base | 5.781% | $20.46 | 92% cbXRP |
| Gauntlet USDC Frontier, Ethereum | 5.646% | $20.20 | 44% outside majors |
| Aave USDC Umbrella, Ethereum | 5.604% | $20.03 | Slashable first-loss stake; rate is an artefact |
| Steakhouse Confidential Prime USDC | 5.336% | $18.93 | Clean book, but deposits are gated: cUSDC via Zama only |
| Uniswap V4 USDC-USDT hook | 6.386% | $14.24 | LP |
| Sky stUSDS | 6.035% | $12.80 | First loss on SKY-backed loans; $17.80 if the swap is free |
| Sky USDS GROVE | 5.739% | $11.58 | No base rate: the figure is a reward |

## Families searched: 268 routes scored, 52 pass the tier

| Family | Scored | Pass |
|---|---:|---:|
| Morpho vaults and markets | 102 | 9 |
| Stable lending (Aave, Compound, Spark, Fluid, Kamino, Euler, Dolomite and others) | 79 | 38 |
| Stable LP (Curve, Uniswap, Convex, Stake DAO) | 49 | 0 |
| Pendle PT / LP | 18 | 0 |
| Savings / staked stables (sUSDS, sUSDe, scrvUSD, BOLD and others) | 15 | 5 |
| Yield wrappers | 5 | 0 |

Not scored, because the tier excludes them: LST/LRT hold and loops, stable loops, perps house pools, volatile LP.

## Outside their passed set

| Route | Rate | Costs | $/month | Should it pass? |
|---|---:|---:|---:|---|
| Jupiter Lend USDC, Solana (`d783c8df`, $481.1M; base 4.59204, 30d 6.31555) | 4.592% | $3.20 | **$15.67** | Yes on their reason. They say no audit on record; [Jupiter's docs list several](https://developers.jup.ag/docs/resources/audits). |
| Aave V4 USDC Core, Ethereum (`4ac1a968`, $5.8M; base 3.9352, 30d 5.44347) | 3.935% | $3.00 | $13.17 | Worth listing, though it would not lead this tier. |
| Spark Savings USDC, Ethereum (`c5c74dd1`, $276.8M; base 3.8, 30d 3.77636) | 3.776% | $3.00 | $12.52 | Yes on their reason: [ChainSecurity audited Spark Vaults V2](https://www.chainsecurity.com/security-audit/spark-vaults-v2). |

None beats our top 3. Yearn OG USDC Compounder pays more (7.07%, $26.06) but holds PT-USD3, siUSD and OETH collateral, so it fails this tier.

## Looks wrong in the data

- **`apyMean30d` tracks total APY, rewards included.** Aave Base: snapshot 5.51, chart base mean 4.54, chart total mean 5.75. So the lowest-of rule strips rewards only when `apyBase` is present and low.
- **Same base rate, two scores.** Aave Ethereum USDC, Umbrella 5.604 and plain 4.380, both with `apyBase` 5.60396.
- **Reward-only rows pass the rule at face value.** Sky USDS GROVE 5.739 and SparkLend USDS SPK 4.087 have a null `apyBase`. 12 scored rows have none.
- **`apyBase7d` is nearly absent:** 14 of 268 scored rows, none in the top 3.
- **Fluid Plasma GHO:** `apyBase` 35.9, up from 4.91 on 1 Nov; chart missing 14 to 27 Oct.
- **Morpho Api3 dCOMP USDC** (`58c04b13`): `apyBase` 80.3 with about zero vault liquidity.
- **Mislabelled rows:** Morpho vaults with a hyphen in the symbol read as multi-asset with IL (GROVE-STEAKUSDC, $541M), and USD₮0 rows read as not stablecoin. None reaches the top 3.
- **Hidden gates:** Confidential Morpho vaults and M1USDC have a deposit gate that DefiLlama does not show.
- **Duplicate verdict:** sUSDS on Arbitrum is $476M at 3.776 under both `sky-lending` (passed) and `spark-savings` (failed).
- **Pendle:** the brief names it as outside, but `pendle-v2` is passed. Scored inside, rejected for this tier. PT-apyUSD-05NOV2026 matures in 2 days.
- **Steakhouse Prime USDC, Base,** fell from $334.7M to $144.6M in 30 days.

## Not verified

- Morpho and Fluid API reads came minutes after the snapshot, not in the same minute.
- The stUSDS risk comes from [ChainSecurity's page](https://www.chainsecurity.com/security-audit/sky-stusds) and third-party summaries, not Sky's own docs.
- Kamino's curated-vault description comes from [Solana Compass](https://solanacompass.com/news/kaminos-institutional-commodity-yield-vault-fills-25m-opening-capacity).
- Kamino Allez USDC ($17.28) and other vaults whose books we did not open cannot reach #3.
- The USDC/USDS swap is at the default 0.05%; Sky's converter may be free. No top 3 route depends on it.
