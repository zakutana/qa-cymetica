# High Risk: our blind top 3

5,000 USDC, 30 days, snapshot 2026-11-03 04:19 UTC. Lowest of apyBase / 7d / 30d. Impermanent loss not counted, by their rule, on every LP route here.

| # | Route | Lev | Net APY | Costs | Profit/month | % | Liq. distance |
|---|---|---|---|---|---|---|---|
| 1 | Uniswap V3 WETH-USDT 0.05% LP, Ethereum | 1x | 36.87% | $9.0 | **$142.51** | 2.85% | none |
| 2 | PT-USD3-17DEC2026 loop against USDT, Morpho LLTV 91.5%, 4.5x | 4.5x | 41.72% | $30.0 | **$141.44** | 2.83% | 15.0% |
| 3 | PT-USD3-17DEC2026 loop against USDC, Morpho LLTV 86%, 4.5x | 4.5x | 36.86% | $26.5 | **$124.97** | 2.5% | 9.6% |

## Each route

**1. Uniswap V3 WETH-USDT 0.05% LP, Ethereum.** Ethereum only: USDC to USDT on one half, USDC to WETH on the other, mint the position; reverse on exit.
- LP, stable against volatile: `f7dd8768-77be-4f91-96d6-dd563ac23dd5`, uniswap-v3 Ethereum WETH-USDT, TVL $10,094,304; apyBase 36.86685, 7d 80.75124, 30d 38.00814; used 36.86685.
- Costs: swap_half_to_weth_pool_fee_0_05pct_both_ways $2.5, swap_half_to_usdt_uniswap_0_01pct_both_ways $0.5, gas_6_tx_ethereum $6.0. Total $9.0.
- Liquidation: no liquidation, no debt.
- Sensitivity: Rank 1 over rank 2 is $1.07, a coin flip. With the brief flat 0.3% for a volatile LP in place of the known 0.05% tier: costs $21.50, profit $130.01, and rank 2 leads.
- Risk: Half the position is ETH and impermanent loss is NOT counted, by their rule. The rate is pool-wide fees / TVL for one day; a range you pick earns its own share only while in range.

**2. PT-USD3-17DEC2026 loop against USDT, Morpho LLTV 91.5%, 4.5x.** Ethereum only: buy PT-USD3 on Pendle, pledge on Morpho, borrow USDT, swap to USDC and buy more PT, up to 4.5x.
- collateral yield, PT bought on Pendle: `b6490fe9-b16a-4ccf-8701-cbded659b397`, pendle-v2 Ethereum USD3, TVL $6,023,545; apyBase 15.52817, 7d None, 30d 15.09271; used 15.09271.
- Borrow USDT: `888aaa18-499e-5af3-a001-44a3db046553`, apyBaseBorrow 7.48593, LLTV 0.915, row collateral $11,921,521, free liquidity $394,810 (Morpho API, read after the snapshot) against $17,500 needed.
- Costs: swap_to_pt_on_notional_0_05pct_default_both_ways $22.5, usdt_to_usdc_on_borrowed_part_uniswap_0_01pct_both_ways $3.5, gas_4_tx_ethereum $4.0. Total $30.0.
- Liquidation: PT-USD3 oracle value in USDT terms (Morpho ChainlinkOracleV2 0xcb21E8fA3Eac83De7f7ACC194705E746f189c180; what feeds it not read). Market LLTV 91.5%, no e-mode on Morpho. Distance 15.0%.
- 30-day borrow: Very different: market exists since 2026-10-17, daily borrow APY mean 2.89%, range 0.59-8.15%; 0.6-1.9% in the five days before the last five, 7.5% now (Morpho API). Current rate used, as the rule says.
- Exit: Pendle PT-USD3 AMM $6.02M; USD3 on Curve frxUSD-USD3 $2.01M (1-day volume $436k). $54.9M of PT-USD3 is pledged across the three Morpho rows against that $6.02M AMM. PT matures 2026-12-17, 44 days, so the 30 days fit.
- Sensitivity: At the 0.05% default on the USDT swap in place of the known Uniswap USDC-USDT 0.01% ($34.36M TVL): costs $44, profit $127.44. Entry path fork: costed as one swap to PT, which holds if USD3 is minted from USDC at 3Jane (then the user deals with 3Jane directly). If USDC to USD3 is a further stable swap (Curve frxUSD-USD3 $2.01M), add $22.50: profit $118.94.
- Risk: Unsecured credit: 3Jane is on no list of theirs, USD3 redeems only up to the tranche ratio; PT pays 15.1% where USD3 itself pays 6.2%. Borrow market only since 2026-10-17 and 96.4% used.

**3. PT-USD3-17DEC2026 loop against USDC, Morpho LLTV 86%, 4.5x.** Ethereum only: buy PT-USD3 on Pendle, pledge on Morpho, borrow USDC, buy more PT, up to 4.5x.
- collateral yield, PT bought on Pendle: `b6490fe9-b16a-4ccf-8701-cbded659b397`, pendle-v2 Ethereum USD3, TVL $6,023,545; apyBase 15.52817, 7d None, 30d 15.09271; used 15.09271.
- Borrow USDC: `032bee19-6763-4f4d-862f-f4cf0e1774c3`, apyBaseBorrow 8.87445, LLTV 0.86, row collateral $23,017,121, free liquidity $2,029,370 (Morpho API, read after the snapshot) against $17,500 needed.
- Costs: swap_to_pt_on_notional_0_05pct_default_both_ways $22.5, gas_4_tx_ethereum $4.0. Total $26.5.
- Liquidation: PT-USD3 oracle value in USDC terms (Morpho ChainlinkOracleV2 0xe5E6Ec063E63A9D0c6Ac041d0AD2bd03F7f08d72; what feeds it not read). Market LLTV 86%, no e-mode on Morpho. Distance 9.56%.
- 30-day borrow: Close: 30-day mean 9.34% against 8.90% now (Morpho API), range 6.85-35.75%, so a spike day would turn the carry negative while it lasts.
- Exit: As rank 2.
- Sensitivity: Same entry path fork as rank 2: a further stable swap to reach USD3 adds $22.50, profit $102.47, and USDC-WETH 0.01% LP at $111.00 takes rank 3.
- Risk: Same token as rank 2, so not an independent choice. 9.6% from liquidation at the cap, and the borrow rate spiked to 35.7% for a day in the last ten.

## Decisions I made
- PT-USD3 is inside: both platforms they name, Pendle and Morpho, pass, and their rule is by platform. The issuer 3Jane is on neither list. If every issuer must be listed too, the top 3 is WETH-USDT 0.05% $142.51, USDC-WETH 0.01% $111.00, WETH-USDT 0.3% $108.07.
- reUSD and reUSDe are dropped as KYC: Re's docs say the tokens are 'subject to KYC/AML requirements'. Unfiltered, PT-reUSD at 4.5x would be about $57-69 and not in the top 3 anyway.
- USD3 is treated as non-KYC: 3Jane's docs say suppliers 'can permissionlessly deposit USDC'. Forest Road (PT-sUSDfr, rank 7, $99.58) and USDx/Axis issuers are not vetted.
- Ranks 1 to 3 sit within $18; rank 2 and 3 are one token twice. The next distinct routes: USDC-WETH 0.01% $111.00, WETH-USDT 0.3% $108.07, PT-sUSDfr hold $99.58 (issuer not vetted).
- Swap fees: known tiers on LP legs (poolMeta) and on the USDC-USDT hop (Uniswap V3 0.01%); every other loop swap leg uses the brief's defaults except where a line says otherwise.
- Pendle swap fee: the brief's 0.05% default per swap is used. Pendle's API gives feeRate 0.286% for this market but I did not confirm how it scales with time to maturity, so it is not applied. Price impact is not counted.
- Aave e-mode: read by GET for Avalanche and Ethereum Prime only; other chains' e-modes need a POST, which the brief forbids. It changes nothing: at 4.5x with any e-mode an L2 Aave LST loop nets under 4.1% and stays negative in month 1.
- A PT or Pendle LP maturing inside 30 days is scored for its remaining days only (PT-apyUSD-05NOV2026 has 2).

## Families searched: 647 routes scored

| Family | Scored | Pass sanity | Best $/month | Best route |
|---|---|---|---|---|
| LST/LRT loop | 40 | 24 | 0.61 | kamino-lend Solana Jito Market JITOSOL/SOL [base LTV from snapshot] |
| PT loop | 7 | 4 | 141.44 | morpho Ethereum PT-USD3-17DEC2026/USDT LLTV 0.915 |
| PT loop (<30d) | 7 | 1 | 9.89 | morpho Ethereum PT-SUSDE-26NOV2026/USDC LLTV 0.915 |
| Pendle LP | 6 | 6 | 86.56 | pendle-v2 Ethereum SUSDFR For LP / Maturity 28JAN2027 |
| Pendle LP (<30d) | 3 | 3 | 8.67 | pendle-v2 Ethereum SUSDD For LP / Maturity 26NOV2026 |
| Pendle PT hold | 6 | 6 | 99.58 | pendle-v2 Ethereum SUSDFR For buying PT-sUSDfr-28JAN2027 |
| Pendle PT hold (<30d) | 3 | 3 | 6.94 | pendle-v2 Ethereum SUSDD For buying PT-sUSDD-26NOV2026 |
| stable LP | 43 | 43 | 19.74 | curve-dex Ethereum APYUSD-APXUSD  |
| stable lending/savings | 173 | 173 | 30.18 | kamino-lend Solana USDC Kamino Institutional Commodity Yield |
| stable loop | 34 | 12 | 21.88 | fluid Plasma SUSDAI vault ltv 0.88 |
| stable-vs-volatile LP | 49 | 49 | 142.51 | uniswap-v3 Ethereum WETH-USDT 0.05% |
| volatile LP (not this tier) | 63 | 63 | 84.29 | uniswap-v3 Ethereum XAUT-WETH 0.3% |
| volatile single | 213 | 213 | 35.7 | convex-finance Ethereum CVXCRV  |

Also read and scored inside those: Morpho, Euler, Spark, Compound, Aave, Kamino, BENQI, Dolomite, HyperLend markets; Curve, Convex, Stake DAO, Beefy, Origami rows. Euler lendBorrow rows give no collateral pairing, so Euler loops were not scorable from the snapshot; every Euler vault hold is. Perps house pools: GMX fails their list and HLP is not passed.

## LST/LRT loops on L2: modest, negative in month 1 at the default fees

wstETH 2.28%, weETH 2.31%, rETH 2.04%, sAVAX 3.76% against ETH or AVAX debt at 1.3-3.3%. At the brief's default fees, round-trip swaps on the notional cost more than a month's carry at every leverage, so the best leverage is the lowest step (1.25x), still a loss; the carry at 4.5x pays back after about two months.
With the known Uniswap tiers where they exist, two turn slightly positive at 4.5x: Fluid Arbitrum wstETH about +$4.15 (USDC-WETH 0.05%, wstETH-WETH 0.01%, costs $11.80, on only $0.84M of depth) and Morpho Ethereum wstETH/WETH LLTV 96.5% about +$2.22 (both 0.01%, costs $9.50). None is near the top 3.

| Route | Net at 4.5x | Gross $/month | Month 1 at 4.5x | Month 1 at best L (1.25x) | Liq. at 4.5x | Exit depth |
|---|---|---|---|---|---|---|
| Morpho Base wstETH/WETH LLTV 94.5% | 4.24% | 17.41 | -17.39 | -8.61 | 17.7%, wstETH vs WETH | Base: Fluid DEX wstETH-ETH $2.53M (not passed), Aerodrome $0.76M (not listed), no passed-venue row |
| Fluid Arbitrum wstETH vault ltv 95% | 3.88% | 15.95 | -18.85 | -8.72 | 18.1%, wstETH vs ETH, ltv used as the threshold | Arbitrum: Uniswap V3 0.01% $0.84M, thin; Fluid DEX $1.74M (not passed) |
| Morpho Monad wstETH/WETH LLTV 94.5% | 3.86% | 15.86 | -18.94 | -8.72 | 17.7%, wstETH vs WETH | Monad: no wstETH DEX row over $0.2M in the snapshot |
| Morpho Base weETH/WETH LLTV 94.5% | 5.91% | 24.29 | -10.51 | -7.98 | 17.7%, weETH vs WETH | FAILS the $5M line: market TVL $1.38M. Base: Fluid DEX $1.59M only |
| Aave Avalanche sAVAX/WAVAX e-mode 2 AVAX correlated (LTV 93, LT 95, read on-chain) | 5.49% | 22.55 | -12.25 | -2.6 | 18.1%, sAVAX vs AVAX | Avalanche: no sAVAX DEX row over $0.2M in the snapshot; the row itself says 15-day unstaking cooldown |
| Aave OP Mainnet wstETH/WETH (base LTV 0.75 from snapshot; e-mode not read) | 4.08% | 16.75 | -18.05 | -8.66 | not known, needs the unread e-mode, wstETH vs WETH | OP Mainnet: no wstETH DEX row over $0.2M in the snapshot |
| rETH on any listed L2 | | | | | | rETH yield 2.04 is at or under WETH borrow (Arbitrum 2.01, Base 2.04), no carry; Aave Arbitrum rETH has LTV 0 in the row; no rETH DEX row over $0.2M on any listed L2 in the snapshot |

Exit depth is what the snapshot lists; a DEX DefiLlama does not cover is not seen here.

## Outside their passed set

| # | Route | Lev | Net APY | Costs | Profit/month | Their status | Should it pass |
|---|---|---|---|---|---|---|---|
| 1 | Orca SOL-USDC LP, Solana (`a5c85bc8-eb41-45c0-a520-d18d7529c0d8`) | 1x | 48.96% | $17.4 | **$183.81** | orca-dex: passed false: No audit on record for the code a route would use | Should be re-checked: orca-so/whirlpools keeps 11 PDFs in .audits/, newest 2026-09-30 (listed, not read), so their reason looks wrong. Non-KYC. |
| 2 | apyUSD loop against USDC, Morpho LLTV 86%, 4.5x (`cb6139f9-4a68-4efd-8245-0312a92aee55`) | 4.5x | 38.93% | $26.5 | **$133.47** | apyx-protocol: not on their list: not listed | Debatable: apyUSD is 'Permissionless; no KYB/KYC requirement' in Apyx docs, but apxUSD mint and redeem are whitelisted, the reason they failed Falcon. Young. |
| 3 | Raydium WSOL-USDC concentrated 0.04% LP, Solana (`709f121d-d3b4-44da-b3d0-47bc16f5400b`) | 1x | 25.32% | $4.4 | **$99.65** | raydium-amm: not on their list: not listed | Non-KYC and long-running; worth listing beside Orca. Audits not checked by me. |

Left out: Aerodrome WETH-VVV (152) and USDC-AERO (91). Both have no apyBase and rewards of 603 and 215, so their only figure is a reward-carrying 30-day mean, which the rule means to leave out. apyUSD's entry: Uniswap V4 apxUSD-USDC 0.05% $10.11M, then the vault or Curve apyUSD-apxUSD $16.02M; one 0.05% swap is costed.

## Looks wrong or suspicious
- lendBorrow totalSupplyUsd on Morpho market rows is the collateral value, not the loan supply: PT-USD3/USDT row 11.92M = Morpho collateralAssetsUsd 11.92M, loan supply 10.97M. Free liquidity cannot come from supply minus borrow; I read it from Morpho's API (read 5 to 20 minutes after the snapshot, not the snapshot itself).
- Morpho and Fluid lendBorrow rows name only the collateral. Morpho's loan asset I joined from Morpho's API on chain, collateral, LLTV and nearest borrow USD. Fluid's I could not name, so a Fluid rate is the row's and the loan asset is inferred.
- A row's rate can lag its market: PT-USD3/USDC row dcd05050 says 10.54% borrow, Morpho API says 9.33% for the same market minutes later.
- Uniswap apyBase is exactly one-day volume x fee x 365 / TVL (WETH-USDT 0.05%: 36.87 both ways). That row is outlier: true, with apyBase7d 80.75 and one-day volume of $20.4M against a 7-day average of $46.8M.
- apyBase7d disagrees with the row's own volumeUsd7d: Base WETH-USDC 0.3% says 17.94 where the volume gives 55.15; Ethereum WETH-USDT 0.3% says 76.44 where it gives 126.06.
- One-day spikes the min rule correctly drops: Fluid Plasma GHO apyBase 35.9 against 30-day 9.05; Morpho API3-DCOMP-USDC 80.3 against 13.59.
- apyMean30d carries rewards, so the rule's 'whichever exist' lets reward-only rows through: Convex cvxCRV has no apyBase, reward 11.47, scored 12.34; outside, Aerodrome USDC-AERO scored 91. No such row reached a top 3 here; check how their engine treats them.
- PT-USD3 has stablecoin false while PT-sUSD3 has true. Monad PT-strUSD-04FEB2027 has underlying coingecko:universal-btc and stablecoin true. HLP has apyBase 0 with apyMean30d 3.27.
- sky-lending has sUSDS rows on Arbitrum and OP Mainnet where their platform list says Ethereum only; I excluded those rows.
- Fluid weETH vaults show borrow rates of 0.06-0.21% with the loan asset unnamed (TVL under $5M, so excluded); they looked like the best LST loops until filtered.
- platforms.json passes pendle-v2 although the brief gives Pendle PT as an outside example. I treated Pendle as inside, by their list.
