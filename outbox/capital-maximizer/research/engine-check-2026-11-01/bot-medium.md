# Medium tier: blind top 3 (snapshot 2026-11-01 08:32 UTC, 5,000 USDC from Ethereum)

**Blindness:** `tiers.json` was printed during orientation, before any scoring. It carries each tier's `best` route, so Cymetica's #1 for medium was seen. `top3-*.json`, `cm.js` and `cm.css` were not opened. The ranking below is purely the computed numbers. Full data: `bot-medium.json`.

Rules used as briefed. Each earn rate is the lowest of apyBase / apyBase7d / apyMean30d; rewards are left out. Borrow is the current apyBaseBorrow. Gas is $1 per Ethereum tx with approvals counted, $0.05 per L2 tx, and a CCTP round trip costs $3.15. Known swap fees are USDC<->USDT 0.01 % and USDC<->USDS 0 (LitePSM, read on-chain); unknown swaps use 0.05 % stable or 0.10 % volatile, each way.

## Top 3

| # | Route | Chain | L | Net APY | Costs | Profit / 30 d |
|---|---|---|---|---|---|---|
| 1 | stUSDS 3x loop against USDC: Sky stUSDS as collateral on the Morpho stUSDS/USDC market | Ethereum | 3.0 | 10.09 % | $4.00 | **$37.47 (0.75 %)** |
| 2 | USDC in RockawayX USDC Yield (Morpho Vault V2 roxUSDCy) | Ethereum | 1.0 | 8.12 % | $3.00 | **$30.39 (0.61 %)** |
| 3 | USDC in August USDC V2 (Morpho vault), via CCTP | Eth -> Monad -> Eth | 1.0 | 7.66 % | $3.30 | **$28.18 (0.56 %)** |

1. **stUSDS loop.** Legs:
   - collateral yield: sky-lending STUSDS `9f71f0fd`, TVL $167.8M; apyBase 10.70, 7d none, m30 **5.79 used**.
   - collateral: Morpho market `bc861b66` (collateral supply APY 0), LLTV 0.86, market $7.08M with $2.06M free.
   - borrow: USDC in the same market, apyBaseBorrow **3.64**.

   Net APY is 3×5.79 − 2×3.64. Costs are 4 Ethereum tx through a flash-loan bundle and no swap fees: USDC<->USDS on LitePSM has tin=tout=0, and stUSDS deposit and redeem are fee-free. **Liquidation is 22.5 % away** (LTV 0.667 against LLTV 0.86). The distance is measured against the Morpho oracle: stUSDS share rate × USDS/USD ÷ USDC/USD.

   **#1 vs #2 turns on one unverified routing fact.** The 4-tx cost assumes a Morpho Bundler3 flow (a direct call or a front end; Morpho app one-click leverage on this market not checked) that converts USDC->USDS on LitePSM. If the bundle swaps on a DEX instead (Curve USDS-stUSDS, $2.3M, 0.05 % default), fees are $15 and the route earns **$22.47, below #2 and #3**. Done by hand (no fees) it takes ~20 tx each way and also loses to #2.

   **30-day picture is different.** Morpho's 30-day average for this borrow is 4.63, which gives $29.31. The live rate about 15 minutes later was 5.18, which gives $24.79. Free liquidity fell from $2.06M to $0.57M, still far above the $10k borrow.

   Risk: stUSDS funds loans to SKY stakers (Sky's "Expert" product), so it can take bad debt.
2. **roxUSDCy.** Morpho-blue `caa9ffc0`, TVL $32.8M; apyBase 9.03, 7d none, m30 **8.12 used**. The 0.12 USDC reward is excluded. The Morpho API shows no gates, $13.5M withdrawable and a 5 % fee. No liquidation for the user. Risk: 79 % of the vault is lent against PT-reUSD (Pendle PT of Re's KYC-minted reUSD).
3. **AugustUSDCv2 (Monad).** Morpho-blue `0b033747`, TVL $9.8M; apyBase **7.66 used**, m30 9.58; the 1.50 reward is excluded. No gates. Risk: 100 % lent against one collateral (earnAUSD), and only $0.95M is withdrawable.

Next best: Re Ecosystem USDC $26.10, Huma USDC $25.10, Keyrock USDC $24.55, Reservoir USDC $23.85. Under a strict reading with no plain USDC lending, the top 3 would be:
- the stUSDS loop: $37.47
- the Uniswap V4 USDC-USDT hook LP: $19.67, IL not counted
- sUSDai hold: $17.08, exit is a 30-day unlock

## Families searched (218 routes scored, 184 admissible)

| Family | Scored | Best admissible |
|---|---|---|
| Stable lending (Aave, Morpho vaults, Compound, Spark, Fluid, Euler, Kamino, HyperLend, Dolomite; all 17 chains) | 118 | roxUSDCy $30.39 |
| Savings dollars (sUSDe, sUSDS, stUSDS, sDAI, wsrUSD, stcUSD, sDOLA, scrvUSD, sGHO, BOLD SP, sUSDai) | 13 | sUSDai $17.08 (30-day unlock); stUSDS $16.79; sUSDe $9.46 |
| Stable LP (Curve, Uniswap V2/V3/V4, Convex, Kamino Liquidity) | 46 | Uni V4 USDC-USDT hook $19.67 |
| Liquid staking held (stETH, rETH, weETH, ETHx, ezETH, JitoSOL, mSOL, sAVAX) | 8 | ETH LSTs lose money in month one (stETH −$5.19 after 0.10 % volatile swaps) |
| Light stable loops (sUSDe, sUSDS, stUSDS, wsrUSD, sUSDai × Morpho, Fluid, Aave e-mode, Dolomite) | 33 | stUSDS/USDC $37.47 |

Only two loops pay in month one: stUSDS/USDC at 3x, and sUSDS/USDT at 3x ($16.22). Every sUSDe loop collapses to plain holding (L=1), because its spread is 0.35–0.78 %/yr against ≥0.10 % swap fees on each extra 1x. Every sUSDai loop is undoable in the passed set, because its only exit is Fluid DEX, which failed.

## Outside their passed set

| Route | Net APY | Profit / 30 d | Should it pass? |
|---|---|---|---|
| Pendle PT-siUSD-07JAN2027 3x loop on Morpho (PT `0757d64d` 9.36 used, borrow `e06f8a2f` 7.51, LLTV 0.86, liquidation 22.5 % away against PT oracle/USDC) | 13.08 % | $34.75 | Pendle yes: its fail is "launch date could not be read", a data miss. infiniFi is young, and its permissionless status is per Yield.xyz only |
| Yearn V3 USDC vault `90cb9575` | 7.03 % | $25.88 | Yes (permissionless since 2020), but adds little |
| Jupiter Lend USDC Earn (Solana) `d783c8df` | 6.32 % | $22.68 | Re-check: the fail is "no audit on record" on a $442M pool |

The highest raw number in the whole search is a **PT-reUSD 3x loop on Morpho at 17.92 % ($54.64)**. It is excluded because reUSD minting requires KYC/AML (docs.re.xyz).

## Suspicious in the data

- `platforms.json`: 36 platforms passed, but `in_finder` = 10 and `routable_chains` = 6. Morpho, Sky, Compound, Spark, Euler, Curve, Convex, Cap, Reservoir and USD.AI are passed but not routed, and Monad/Base are not routable. **All three of my routes are outside what their finder can see.**
- DefiLlama rows show no Morpho deposit gates:
  - roxcUSDC (8.85 %, the top raw USDC rate), m1USDC and steakcUSDC are gated.
  - hyperUSDCa on Monad ($46M) has $1,983 withdrawable, and satUSDC has $0.
- Some fails are lookup misses, not findings:
  - "Launch date could not be read": Pendle, Orca, QuickSwap, Beefy, Stake DAO, BENQI, StakeWise.
  - "No audit on record": Jupiter Lend, Fluid DEX, LlamaLend, Spark Savings.
- Reward-only rows (Sky GROVE 5.70 %, Spark SPK) have apyBase null. Their apyMean30d includes the reward, so the lowest-of-three rule lets reward yield in.
- Reservoir, Cap and BOLD stability pools have no apyBase, only m30. Origami SUSDS-S shows m30 = 2,391.87 %.
- Spark Savings (failed) and Sky (passed) list the same Arbitrum sUSDS ($476.2M) — one product, two verdicts.
- Dolomite USDC shows borrowable=false while $113M is borrowed. Kamino "Institutional Commodity Yield" USDC (7.84 %) has unknown lender KYC and is excluded; it would rank #3 ($28.91) if permissionless.
