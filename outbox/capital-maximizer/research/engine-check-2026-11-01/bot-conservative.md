# Conservative tier: my blind top 3 ("Dollars only. No borrowing.", USDC/USDT, 1x)

5,000 USDC from Ethereum, DefiLlama snapshot 2026-11-01 08:32 UTC, their rules. I did not open `top3-*.json`, `cm.js`, `cm.css`, `tiers.json`, cymetica.com or their API.
The full numbers per leg are in `bot-conservative.json`.

**Rate rule as applied:** `apyBase7d` is null on every lending and vault row, so each rate here is min(apyBase, apyMean30d). Rewards are left out.
**Costs:** Ethereum route = 3 tx x $1. Remote route = 3 x $1 on Ethereum (approve, CCTP burn, CCTP mint home) + 6 x $0.05.

## Top 3

| # | Route | Pool (DefiLlama) | TVL | apyBase / 30d | Used | Cost | $/month | %/month |
|---|---|---|---|---|---|---|---|---|
| 1 | Morpho vault **RockawayX USDC Yield**, Ethereum | caa9ffc0-2983-4c18-9556-4e3ad4dfe6ac | 32.81M | 9.029 / 8.125 | **8.125%** | $3.00 | **$30.39** | 0.608% |
| 2 | CCTP to Monad, Morpho vault **August USDC V2** | 0b033747-3a22-486b-a600-9958b878bef7 | 9.78M | 7.660 / 9.575 | **7.660%** | $3.30 | **$28.18** | 0.564% |
| 3 | Morpho vault **RockawayX Tori Ecosystem**, Ethereum | ea5f40b9-0d0e-5b99-a967-040a93abc9f6 | 14.39M | 9.882 / 7.581 | **7.581%** | $3.00 | **$28.15** | 0.563% |

None of these routes borrows, so the user has nothing to liquidate (leverage 1.0x). #2 and #3 differ by 3 cents, so treat them as a tie.
Checked on the Morpho API, 10-20 minutes after the snapshot: all three have no deposit gate and are listed in the Morpho app. Withdrawable liquidity was 13.5M, 0.95M and 1.2M.

Risk, one line each:
1. 79% of the vault is lent against a single collateral, PT-reUSD-10DEC2026 (a Pendle PT on Re's reinsurance-backed dollar), at 91.5% LLTV and ~90% utilisation.
2. 100% is lent against August's earnAUSD vault token, on Monad. A 1.5% reward is left out of the rate.
3. 74% is lent against strUSD; the rest is against trUSD/etrUSD and their PTs. That is synthetic-dollar collateral, in a vault about 4 months old.

**The honest catch:** all three earn their premium by lending to borrowers who post young synthetic dollars as collateral. Large blue-chip venues pay less, under the same rules:

| Venue | $/month |
|---|---|
| Fluid USDC Ethereum, 5.89% | $21.21 (my #15) |
| Aave V3 USDC Base, 5.35% | $18.68 |
| Gauntlet USDC Prime Base, 4.91% | $16.89 |
| Compound V3 USDC Ethereum, 4.50% | $15.49 |
| Aave V3 USDC Ethereum, 3.92% | $13.11 |

Splitting the 5,000 between venues only adds gas, so the best plan is 100% in #1.

**How fragile ranks 2 and 3 are:** I required at least $5,000 of withdrawable liquidity. Raise that floor to $1M and #2 drops out, since it had 0.95M withdrawable. Kamino Private Credit ($27.62, KYC status unverified), Morpho Re Ecosystem ($26.10) and Yearn OG USDC ($25.30) would move up in its place.

## Taken out, though the numbers alone would rank them high
- Morpho **Api3 dCOMP USDC**, 9.91% ($37.72): $0.001 withdrawable. The rate is a 100%-utilisation artefact (apyBase 58.4).
- Morpho **RockawayX Confidential RWA USDC**, 8.85% ($33.39): deposit gate, allow-listed depositors only.
- Kamino **Institutional Commodity Yield**, 7.84% ($28.91): 49.63M supplied and 49.63M borrowed against an off-chain credit token. It has no exit.
- Morpho **Hyperithm USDC Apex** on Monad, 7.82%: $1,983 withdrawable.
- Morpho **Saturn USDC** on Monad: $0.04 withdrawable.
- Morpho **M1 USDC**, Steakhouse Confidential Prime and FCUSDT: gated.

## Families searched
I scored **378** USDC/USDT routes on the passed platforms and their chains. **97** of them hold at least $5M, and **87** remain feasible after the checks.

- **Stable lending and vaults:** 327 scored, 94 at $5M or more.
- **USDC-USDT LP:** 51 scored, 3 at $5M or more. The best is Uniswap V4's hook pool at 6.86%, which leaves $16.67 after LP costs (impermanent loss is not counted).
- **Other dollars:** stUSDai 6.20% (a 30-day unlock), wsrUSD 6.08% and stcUSD 5.86% (30-day figure only), stUSDS 5.79% (first-loss), sDOLA 5.72%, sUSDe 4.98%, sUSDS 3.76%.
  - None of them is plain USDC/USDT. After the 0.05% swap each way, none beats #3 either.
- **Aave Umbrella:** a slashable stake, so I treated it as not supply.
- **Not scored:** LST/LRT, loops, perps house pools and volatile LPs. Each needs borrowing or volatile exposure, which this tier rules out.

## Outside their passed set
1. **Pendle PT-reUSD-10DEC2026**, 12.05% fixed, $14 cost, **$35.54**.
   - Pendle should pass. Its only fail is "launch date could not be read", which is a data gap.
   - I would still not use this route for this tier: the PT holds reUSD, not dollars, and the fixed rate runs only to 10 Dec.
2. **Yearn USDC vault**, Ethereum, 7.03%, **$25.88**. Yearn is not listed at all, but it is non-KYC and has been live since 2020, so it should be listed.
3. **Jupiter Lend USDC Earn**, Solana, $442M, 6.32%, **$22.68**. Its "no audit on record" fail reads as a missing record and should be re-checked.

## Suspicious
- **Their own `platforms.json` counters:** `in_finder` = 10 of the 36 passed platforms, and `routable_chains` = 6 of 17 (Arbitrum, Avalanche, Ethereum, OP Mainnet, Polygon PoS, Solana).
  - Morpho Blue ($11.0B) is not in their finder, and Base and Monad are not routable, so their engine cannot reach any of my top 3.
  - Inside their subset my best would be:
    - Kamino Private Credit USDC: 7.52%, $27.62 (KYC status unverified).
    - Kamino OnRe USDC: 6.43%, $23.12.
    - Fluid USDC Ethereum: 5.89%, $21.21.
  - **If their #1 is Kamino Institutional Commodity Yield, they are recommending a route that cannot be exited.**
- **DefiLlama lists gated and illiquid vaults as ordinary pools.** These are the Api3, Confidential, M1 and Monad vaults named above.
- **Uniswap V4 USDC-USDT hook pool:** 226.7M of volume a day on 6.9M TVL.
- **Origami SUSDS-S:** apyMean30d of 2391.87.
- **GMX USDC-USDG:** apyMean30d of 80.8 against an apyBase of 0.10.
- **Morpho single-USDC vaults tagged `exposure: multi`:** an engine would treat them as LPs.
- **Aave Umbrella stakes carry the plain symbols USDC/USDT.**
- **Data gaps posing as fails:** "no audit on record" for Spark Savings, Jupiter Lend and LlamaLend, and "launch date could not be read" for Pendle, Beefy, StakeWise and Stake DAO.

The scripts and raw reads are in `cm-live/work-conservative/`. The Morpho and Kamino reads were live at 08:40-08:50 UTC, so gates and utilisation may have changed since.
