# Capital Maximizer: platforms and chains review

2026-10-28. DefiLlama files from today, plus each platform's own docs. GET only. Every platform has its sources in `platforms-proposed.json`.

| | |
|---|---|
| Platforms recommended | **62**: 34 of the 36 kept, plus 28 new |
| New beyond the 36 | **28**: 10 pass today's rule, **18 need a rule change** |
| Dropped from the 36 | **2**: Falcon and Solstice (KYC and retail terms) |
| Chains | **21** CCTP chains with a recommended venue. **6** are core: Ethereum, Arbitrum, Base, Solana, HyperEVM/HyperCore, Avalanche |
| Rule changes proposed | **6**. One tightens the rule (R5). One swaps an audit for a track record (R6) |
| Priced from DefiLlama | **49 of 62**. Its funding-rate feed (`/perps`) now returns HTTP 402 (paid) |
| Links checked | 169 GET: 158 return 200. 8 stale DefiLlama audit links (404), 2 bot blocks (403), 1 rate limit (429) |

## Top 10 must-adds

1. **GMX V2** (R3): audited perps plus GM/GLV pools on Arbitrum and Avalanche, with a free GET funding feed.
2. **Jupiter** Lend, Perps/JLP and Aggregator (R2, R1): Solana's Multiply loops, perps, perp LP and swaps. Ten Lend audits on Jupiter's page.
3. **Velora, 0x, Circle CCTP** (R1): the swap and USDC layer every route already assumes.
4. **Lighter** (R2): perps with no KYC (geo-blocked). Its GET API also carries Hyperliquid, Binance and Bybit funding.
5. **Spark Savings** (R2): $1.5B of stablecoin savings (sUSDC, sUSDS, Spark Vaults) on 6 CCTP chains.
6. **Kinetiq kHYPE** (R2): HYPE loops on HyperLend (a $229M kHYPE market).
7. **Meteora DLMM and Orca** (R2): Solana concentrated LP.
8. **Hyperliquid perps and HLP** (R6, OG Gambler only): the deepest perps and funding. Its published audits (Zellic, 2023) cover the bridge, not the engine.
9. **Uniswap V4** (passes as is): hook pools and router.
10. **Lombard LBTC** (R4): BTCfi loops on Aave ($217M market, LTV 70%), bought and sold only.

Also worth adding: Yield Basis, Sanctum INF, crvUSD, Liquity V2, Exponent, Beefy and Kamino Liquidity, EigenCloud and Symbiotic, USD.AI, Fluid DEX (LP only), Origami.

## Strategy map

| Strategy | Platforms | Chains | Data feed | Ready today? |
|---|---|---|---|---|
| Stable vault split | Aave, Compound, Morpho vaults, Sky; + Spark Savings, Fluid, Euler, Kamino, Jupiter Lend | ETH, Base, Arb (+SOL, AVAX, Plasma, Monad) | DefiLlama pools | Yes, 8 pools. Add the new vaults |
| Stable stack / basis hold | Ethena sUSDe, Sky sUSDS, Cap stcUSD, Reservoir wsrUSD, USD.AI sUSDai, crvUSD scrvUSD | ETH, Arb | DefiLlama pools | sUSDe yes. Others need adding |
| ETH/BTC loop (borrow USDC) | Aave, Morpho; + Compound, Euler, Spark, Fluid, Kamino, Jupiter Lend | ETH, Base, Arb, SOL | lendBorrow: LTV, borrow APY | **Yes** (today's finder) |
| Correlated LST loop (borrow ETH/SOL/HYPE) | Aave E-mode, Morpho, Spark, Fluid, Euler; Kamino, Jupiter Lend (JitoSOL, INF); HyperLend (kHYPE, stHYPE) | ETH, Base, Arb, SOL, HyperEVM | Pools + lendBorrow; E-mode LTV from Aave's own data; Kamino GET API | **No.** The finder never borrows the staked coin itself |
| Stable loop | Morpho sUSDe/PYUSD; + Spark, Fluid, Euler | ETH | lendBorrow | Yes (Morpho) |
| Pendle PT fixed / PT loop | Pendle, Exponent (SOL); PT collateral on Morpho (PT-reUSD $157M, LLTV 91.5%), Aave, Kamino | ETH, Arb, Monad, Base, Plasma, SOL | DefiLlama: 82 PT rows plus lendBorrow; Pendle GET API (expiry, implied APY) | Data yes; route type missing |
| YT / points | Pendle YT, Exponent; ether.fi, Renzo, EigenCloud, Symbiotic | ETH, Arb, SOL | Pendle API (YT implied). No public points feed | No: points cannot be priced |
| Funding carry (spot long + perp short) | GMX V2, Lighter, Hyperliquid (R6), plus a spot/LST leg | Arb, AVAX, ETH, HyperEVM | GMX GET `/markets/info`; Lighter GET `/funding-rates`. Hyperliquid `/info` is POST only | No perp leg |
| Perp leverage | Hyperliquid (R6), GMX V2, Lighter, Jupiter Perps | HyperEVM, Arb, AVAX, ETH, SOL | Venue APIs: mark, funding, max leverage, OI | No |
| Perp LP (be the house) | GMX GM/GLV, Jupiter JLP, HLP (R6); Lighter LLP (watch) | Arb, AVAX, SOL, HyperEVM | DefiLlama (GMX 138 pools, HLP 1); Jupiter GET `/jlp-info` | No |
| CL LP, manual and auto-ranged | Uniswap v3/v4, Aerodrome, Orca, Meteora, Fluid DEX; Beefy CLM, Kamino Liquidity | ETH, Base, Arb, SOL | DefiLlama fee APY; range and IL need pool tick data | Full-range ETH/USDC only |
| Leveraged farming / margin | Kamino Multiply, Jupiter Lend, Dolomite, Euler, Origami | SOL, Arb, ETH | lendBorrow + Kamino API | No |
| Soft-liquidation, IL-free leverage | crvUSD (LLAMMA), Liquity V2, Yield Basis | ETH | DefiLlama (crvUSD 8 pools, Yield Basis 16) | No |
| BTCfi | cbBTC/WBTC loops; LBTC on Aave; Yield Basis BTC; Symbiotic LBTC | ETH, Base | Pools + lendBorrow | cbBTC/WBTC yes; LBTC to add |
| Delta-neutral vaults | Ethena, Cap, Reservoir held; build-your-own = the funding-carry row | ETH | Pools | sUSDe yes |
| Options vaults | None admissible: Derive V3 is 0.1 years old, Rysk has no DefiLlama audit, Ribbon lost $2.7M | — | — | Not possible today |
| Fixed funding | Pendle Boros: audited, but $7.4M is under the $30M floor | Arb | Boros API | Watch |

## Chains

- **Core six:**
  - Ethereum
  - Arbitrum: GMX, Dolomite, Boros
  - Base: Morpho cbBTC, Aerodrome
  - Solana: Kamino, Jupiter, Orca, Meteora
  - HyperEVM and HyperCore: HyperLend, kHYPE, Hyperliquid
  - Avalanche: GMX, BENQI
- **Breadth, 15 more CCTP chains:** Monad, Polygon PoS, Plasma, OP Mainnet, X Layer, Arc, Unichain, Sui, Linea, Pharos, World Chain, Ink, Sonic, Morph, Sei.
- **HyperCore:** CCTP lands on HyperEVM. Per Circle, HyperCore balances are credits backed by native USDC held in its CoreDepositWallet.
- **Lighter:** its chain is reached through its Ethereum contract. Its docs mark the CCTP route from Arbitrum, Base, Avalanche, Arc or HyperEVM as legacy.
- **Excluded, not on CCTP:** BNB Chain (USYC only), Tron, Robinhood Chain ($1.1B of DeFi), Mantle, Berachain, Katana and the dYdX chain (Noble via IBC). On these, USDC is wrapped.
- **Chain names:**
  - Circle's HyperEVM is DefiLlama's "Hyperliquid L1", OP Mainnet is "Optimism", Polygon PoS is "Polygon".
  - In the JSON, `cctp_native_chains` uses Circle's names and `chains` uses DefiLlama's.

## Rule changes proposed

- **R1 Routers.** A swap router holds no deposits, so it is judged by at least $1B of 30-day volume on CCTP chains instead of $30M TVL. The audit, age and loss tests stay, and approvals are for exact amounts only.
  - Why: their TVL is zero by design. Excerpts of Matcha's post-mortem blame its 01/2026 loss on infinite approvals to a third-party router; the page itself was rate-limited (429) and not read.
  - CCTP is admitted on a different ground. It is Circle's own burn and mint of USDC, so it adds no trust beyond holding USDC. ChainSecurity audited V1 (2023) and V2 (2025).
- **R2 Audits.** When DefiLlama's audit field is empty, accept an audit on the protocol's own page that names the auditor and covers the contract the route uses. Store both.
  - Why: DefiLlama shows no audit for 11 venues that are audited per their own pages.
  - Scope still binds: Fluid's smart vaults and Sanctum's LST fork stay out.
- **R3 Losses.** Count what users lost after funds came back and after the protocol paid restitution, per its post-mortem.
  - Why: GMX V1's 07/2025 exploit was recovered, and the holders of the exploited pool were made whole (GMX, 08/2025). DefiLlama still shows $2M lost.
- **R4 Assets vs platforms.** A token the product only buys and sells on a DEX (cbBTC, WBTC, LBTC, USDe) is judged as an asset, by where it trades. The exchange-issued ban stays for staking tokens an exchange runs.
  - Why: the finder already loops Coinbase's cbBTC, which the rule's wording forbids.
  - LBTC reads $0 only because DefiLlama books its BTC on Bitcoin.
- **R5 Hack matching (tightens).** Hack rows with no protocol id whose name starts like a platform's are flagged, then settled by reading each row's source.
  - Today it flags Loopscale ($5.8M), CoW Swap ($1.2M) and Silo Finance ($546k).
  - Among the 36 it flags only Sky: $721k from two unrelated rows, still under $1M.
- **R6 Hyperliquid only.** This substitutes trust for an audit; it does not interpret the rule. HyperCore perps and HLP would be admitted on an audited bridge, 2.5 years live, $6.6B held and no lost user deposits, for OG Gambler only.
  - Why it is needed: Hyperliquid's audit page holds two Zellic reports on its bridge contract (Bridge2.sol, 2023) plus a link to Circle's contracts. Nothing covers the engine.
  - The cost: HLP lost about $4.9M to a POPCAT manipulation on 2025-11-12.
  - It can be vetoed alone; the rest stands without it.
- **Unchanged:** CCTP-only chains, the 1-year age, the $30M floor, no KYC pools, no exchange staking tokens.

## Rejected

- **Falcon (drop):** USDf mint/redeem requires KYC. Terms 10.2(a) ask for whitelisting and screening to redeem sUSDf through the Platform. Whether the vault redeems on-chain without that was not checked.
- **Solstice (drop):** its Terms make any Retail User a Restricted Person. USX mint/redeem is for KYC'd institutions only.
- **Maple:** "authorization is required for all Syrup deposits". Its KYC page covers all lenders, and the US is excluded.
- **Liquid Collective, cbETH, wBETH:** a KYC pool, and exchange-issued staking tokens.
- **1inch:** $5.7M in DefiLlama hacks; 1inch says no end users were affected. **CoW:** $1.26M (a DNS hijack, with grants voted). Neither is needed.
- **KyberSwap:** its audited router (V3, 11/2025) is under a year old. The V2 router used on 20 chains has no audit on its page.
- **dYdX v4:** its chain is not on CCTP. USDC arrives via Noble, where Circle minting stopped on 2026-10-13 (per Injective).
- **Fluid smart vaults (types 2-4), Sanctum LSTs, JupSOL:** no audit of the code the route would use.
- **Options vaults:** nothing admissible today.
- **Watch, eligible once a year old:**

  | Platform | Eligible from |
  |---|---|
  | Curvance | 2026-11-27 |
  | kmHYPE | 2026-12-11 |
  | Aave V4 | 2027-03-30 |
  | Morpho Midnight | 2027-07-22 |
  | Derive V3 | 2027-10-08 |
  | Hyperliquid Earn, Lighter LLP | 2027-10-21 |

  Boros waits until it holds $30M.
- **Losses:** Drift, Kelp, Cetus, Balancer, Resolv, Ostium, Moonwell, Yearn, NAVI, Venus, Across, Raydium, SolvBTC, Summer.fi, Term, Squid, Ribbon, Loopscale.
- **Under $30M:** Gearbox, Contango, Silo, Felix, Hyperbeat, Liminal, Gains, Neutral Trade.
- **Managed vaults** (Veda, Concrete, Upshift, Lagoon, IPOR Fusion, Mellow): a curator picks the strategy, so the product could not explain the yield.
- **Bridges** (LayerZero/Stargate, Portal, Axelar, CCIP): USDC moves by CCTP only. **Babylon:** stakes native BTC only.
- **BNB-chain venues** (Lista, PancakeSwap v3, Aster): not on CCTP.

## Not verified

- KYC was checked for Ethena, Falcon, Solstice, Cap and Reservoir. The other 31 of the 36 are permissionless by design but were not re-read.
- **Hyperliquid:** its Terms page is JavaScript-rendered and was not read; its geo-blocks come from secondary sources.
- **Matcha post-mortem:** HTTP 429, not read.
- **Lighter:** 2 of its 9 audit files were not identified.
- **USD.AI:** its audit page names no auditors.
