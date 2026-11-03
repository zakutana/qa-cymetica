# OG Gambler: independent top 3 (5,000 USDC, snapshot 2026-11-03 04:19 UTC, cap 4.5x)

Full legs and pool ids: `bot-og.json`. Month = APY x 30/365 x 5,000. Price moves and impermanent loss are not counted.

## Top 3

| # | Route | Net APY | Gross | Costs | Max profit / month | Liquidation |
|---|---|---|---|---|---|---|
| 1 | Uniswap V3 WETH-USDT 0.05% LP, Ethereum | 36.87% | $151.51 | $26.00 | **$125.51** (2.51%) | none (range risk) |
| 2 | PT-USD3 17 Dec 2026 / USDT, Morpho, 4.5x, Ethereum | 41.72% | $171.44 | $46.00 | **$125.44** (2.51%) | 15.0%, PT-USD3 vs USDT, LLTV 91.5% |
| 3 | PT-USD3 17 Dec 2026 / USDC, Morpho, 4.5x, Ethereum | 36.86% | $151.47 | $28.50 | **$122.97** (2.46%) | 9.56%, PT-USD3 vs USDC, LLTV 86% |

- **#1 and #2 are a tie, and the order rests on one phrase.** I read "0.3% to enter and leave" as a $15 round trip. Read as 0.3% each way ($30), #1 is $110.51 and #2 leads. With the pool's known fee ($5), #1 is $135.51.
- **#1 is flagged as a one-off.** 25 of 31 daily readings were below the 36.87% used, and the median is 26.56%, which gives $83.15. Today's rate is the lowest field only because 256.6% and 208.0% on 29 and 30 Oct inflated the 7-day and 30-day figures. On the median, the PT loops lead.
- **PT swap cost:** the 0.05% default is kept. Pendle's fee is annual and scaled by time to expiry (0.286% x 44/365 = 0.034% of principal). On that fee alone, #2 is $132.43 and #3 $129.96, before price impact.
- **#1 needs an active range.** The rate is pool-wide fees over TVL; a passive wide position earns less.
- **#2 and #3 are the same token.** The next different routes are WETH-USDT 0.3% Ethereum $101.07, USDC-WETH 0.01% Ethereum $94.50, WETH-USDC 0.3% Arbitrum $87.30.
- **PT-USD3 rate is steady:** implied 14.2 to 15.5% over 31 days, rate used 15.09%. 3Jane says USD3 supply is permissionless; it funds unsecured credit and 3Jane is not on their list.
- **Borrow, 30-day picture** (Morpho API, read after the snapshot; DefiLlama's history answers 402):
  - USDT market: now 7.46%, 7-day 4.75%, no 30-day yet, 96.4% used, $394,814 free.
  - USDC market: now 8.90%, 7-day 13.56%, 30-day 9.32%. At 13.56% route #3 makes $55.57.

## Families searched: 570 candidates scored

| Family | Scored | Best | $ / month |
|---|---|---|---|
| Volatile LP (all their chains) | 78 | WETH-USDT 0.05% Ethereum | 125.51 |
| PT loops | 4 | PT-USD3 / USDT | 125.44 |
| Pendle PT hold | 5 | PT-sUSDx 3 Dec | 58.49 |
| Pendle LP | 5 | sUSDx 3 Dec | 55.17 |
| Morpho vaults labelled multi | 7 | API3-DCOMP-USDC (flagged spike) | 52.84 |
| Stable lending and savings, Morpho, Euler, Spark, Compound, Fluid, Kamino | 138 | Morpho PENDLEUSDCHY 9.0% | 33.98 |
| Stable loops | 35 | sUSDe / BTC.B Aave Avalanche 2.75x | 29.45 |
| LST/LRT loops | 147 | JitoSOL / xBTC Kamino 2.5x | 18.09 |
| Stable and correlated LP, Curve, Convex, Stake DAO | 60 | apyUSD-apxUSD Curve | 17.74 |
| LST and other single | 91 | Morpho ROXTORI 7.64% | 14.42 |

- **The highest ETH loops lose money in month one.** wstETH/WETH Morpho 96.5% LLTV at 4.5x: 2.85% APY, -$26.78 after swaps on $22,500. Only PT collateral pays at 4.5x.
- **Not scored:** Euler loops (no collateral mapping in the snapshot). Perps house pools: none pass.
- **Aave/Spark e-mode:** not in the snapshot; LTV 0.90 / LT 0.93 assumed only to allow the leverage, and these rows rank far below.

## Excluded on their own no-KYC rule, or by maturity

Criterion: a token is out when its issuer's mint or redeem needs identity checks, even where Pendle or a DEX trades it freely. Not checked for sUSDx, sUSDai or siUSD, which rank below the top 3.

- PT-sUSDfr 28 Jan 2027, 26.66%, about $97.58: USDfr is minted by KYC-verified addresses (CoinGecko description).
- PT-reUSD 10 Dec 2026 loops, best about $53.00: docs.re.xyz says KYC/AML, non-U.S. only.
- PT-apyUSD 5 Nov 2026: matures in 2 days.

## Outside their passed set

| Route | Net APY | Max profit / month | Should it pass? |
|---|---|---|---|
| Orca SOL-USDC LP, Solana | 48.96% | **$182.66** | Yes. "No audit on record" is wrong: 11 audit PDFs in orca-so/whirlpools. Rate lasts: median 51.0%. |
| apyUSD / USDC, Morpho, 4.5x (Apyx) | 38.93% | **$131.47** | Doubtful. No KYC on the vault, but dividend-backed, whitelisted mint, terms bar US, EU, UK. Liquidation 9.56%, apyUSD vs USDC. Borrow 5.50% now, 30-day 5.18%. |
| Orca SOL-cbBTC LP, Solana | 28.79% | **$99.63** | Same platform call. Median 32.87%. |

## Suspicious in the data

1. **apyBase7d contradicts its own pool.** Base WETH-USDC 0.3% ($149.8M): 17.94% against 55.15% from its 7-day volume and 54.51% from its daily readings. The rule gives it $55.18; without that field, $176.44, which would top the list. OP USDC-WETH 0.3%: 19.05% against 50.23%; $59.75 vs $233.53, TVL $5.04M.
2. **Morpho `totalSupplyUsd` in lendBorrow is the collateral value, not the loan supply** (3 of 3 checked). Free liquidity from it is overstated: $1.34M against the real $0.39M. Read it from Morpho.
3. **Current spikes:** Morpho API3-DCOMP-USDC 80.31% (median 7.33%), Fluid GHO Plasma 35.9% (30-day 9.05%), Symbiotic Keyrock USDC 238.13%.
4. **Reward money through apyMean30d:** cvxCRV 12.34% and Sky USDS Grove 5.74% have no base rate. Lowest-of alone would count them; I dropped them.
5. **Pendle passes as a platform, its PT issuers are not vetted,** so KYC tokens get through. The brief names Pendle PT as an outside example, but `platforms.json` has it passed, so PT routes are inside here.
6. **Stale or odd rows:** matured PT collateral still listed; Euler vaults at TVL 0, 100% used, 0.2% borrow ($90.7M); XAUT-WETH TVL $0.11M to $7.1M in 30 days.
