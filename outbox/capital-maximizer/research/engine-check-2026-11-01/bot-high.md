# High tier, blind top 3

Staked-asset loops and house vaults, up to 3x. 5,000 USDC from Ethereum, snapshot 2026-11-01 08:32 UTC, their rules. The honest answer is modest: under 0.4% in month one.

| # | Route | Chain | L | Net APY | Costs | $/month | % | Liquidation |
|---|---|---|---|---|---|---|---|---|
| 1 | GMX V2 BTC/USD [WBTC.b-WBTC.b] GM (single-token) | Arbitrum | 1.00x | 6.474% | $7.50 | **$19.11** | 0.382% | none (no debt) |
| 2 | Aave V3 Avalanche e-mode 2 "AVAX correlated" sAVAX/WAVAX | Avalanche | 3.00x | 8.074% | $16.20 | **$16.98** | 0.34% | 29.82% (sAVAX vs AVAX, as the market's oracle prices it) |
| 3 | GMX V2 ETH/USD [ETH-USDC] GM | Arbitrum | 1.00x | 3.907% | $9.50 | **$6.56** | 0.131% | none (no debt) |

Third place is close: mSOL hold $5.79, JitoSOL hold $4.65, wstETH 3x on Morpho $1.01. Sensitivities are under each route.

## 1. GMX V2 BTC/USD [WBTC.b-WBTC.b] GM (single-token)
CCTP USDC to Arbitrum; swap USDC to WBTC on Uniswap V3 (0.05%); buy the single-token GM; 30 days; sell GM, swap back, CCTP home.

- GM pool (house of the perps market): gmx-evm WBTC.B-WBTC.B `ffb4e407-6507-4615-b776-a0d99cfc1bbb` TVL $9,704,736; base 8.50492 / 7d None / 30d 6.47428; used 6.47428
- costs: swaps $5.00, gm_fees $0.00, gas $0.40, cctp $2.10; total $7.50
- risk: Full BTC price exposure and the pool is the counterparty of BTC perps traders; apyBase 8.50% is above the 6.47% used, but GMX's own API says 30-day 66.1%, so the fee history is lumpy.
- Snapshot row matched to GMX market 0x7C11F78C... by tokens and size: 124.66 WBTC is the $9.7M TVL. DefiLlama gives no market address.
- GM buy and sell fees read 0.00% on-chain for this single-token market (GMX DataStore, eth_call).
- Market open and under its cap: 124.66 WBTC in pool, cap 1,500 (eth_call).
- Exit room: open interest $2.16M long and $2.13M short on a $9.7M pool, available liquidity about $2.7M each side (GMX API), far above $5,000. A sale can still be blocked if reserved tokens or the PnL limit are hit (docs.gmx.io).
- Keeper execution fee in ETH is not modelled above the $0.05/tx gas figure; the user needs a little ETH on Arbitrum.
- Impermanent loss: not applicable (one token); trader PnL against the pool is not counted, as their rule leaves price moves out.

## 2. Aave V3 Avalanche e-mode 2 "AVAX correlated" sAVAX/WAVAX
CCTP USDC to Avalanche; swap USDC to WAVAX on Uniswap V3 (0.05%); stake AVAX to sAVAX at BENQI (no fee); supply on Aave in e-mode 2; borrow WAVAX, stake, resupply until 3x; exit: sell sAVAX to WAVAX, repay, swap the rest to USDC, CCTP home.

- staking yield of sAVAX: benqi-staked-avax SAVAX `3790c3e5-8644-4f6b-8feb-12434d8b99f9` TVL $213,687,409; base 4.98299 / 7d 6.61081 / 30d 4.86313; used 4.86313
- collateral (supply APY of sAVAX): aave-v3 SAVAX `1914a267-f123-46ed-baa0-d1474d33c399` TVL $80,025,199; base 0 / 7d None / 30d 0; used 0
- borrow aave-v3 WAVAX `a1e18d7d-9a5f-4251-acb4-a87e005fe2c5` apyBaseBorrow 3.25769 (TVL $91,237,590, free $91,242,912)
- maxLTV 0.93, LT 0.95: Aave API per-reserve eModeInfo (api.v3.aave.com, fetched 2026-11-01)
- costs: swaps $12.50, gas $1.60, cctp $2.10; total $16.20
- risk: The exit is the weak point: no passed DEX lists sAVAX and the snapshot shows only about $0.3M of sAVAX DEX liquidity elsewhere (joe-v2.2 $0.105M, pharaoh-v3 $0.038M and $0.179M), or BENQI's 15-day cooldown per round; AVAX exposure.
- E-mode confirmed on chain: category 2 "AVAX correlated", LTV 93%, LT 95%, sAVAX collateral, WAVAX borrowable (Aave V3 Pool, eth_call).
- Exit swap is charged at the 0.05% default on $15,000 sold. If slippage on that sale is 0.11% above the fee, the first month is flat.
- Unlevered version with no DEX in the exit (BENQI cooldown): $12.54 a month, money back about 15 days later. Same asset, so not given its own slot.
- Leverage sweep rises from $10.04 at 1x to $16.98 at 3x; the 3x tier cap binds, not LTV or the 5% rule.
- Gas counts 32 transactions: BENQI staking cannot sit inside a flash-loan swap, so the loop is built by hand in 3 rounds and unwound the same way.
- 30-day borrow picture: Aave API mean 3.117% (range 2.21 to 4.46) against the 3.258% used, not very different.
- Aave sAVAX supply cap is 99.6% full: 6,973,769 of 7,000,000, about $298k left (api.v3.aave.com).

## 3. GMX V2 ETH/USD [ETH-USDC] GM
CCTP USDC to Arbitrum; buy GM with USDC single-sided; 30 days; sell GM to USDC, CCTP home.

- GM pool (house of the perps market): gmx-evm ETH-USDC `61b4c35c-97f6-4c05-a5ff-aeb4426adf5b` TVL $48,132,145; base 9.75951 / 7d None / 30d 3.90681; used 3.90681
- costs: swaps $0.00, gm_fees $7.00, gas $0.40, cctp $2.10; total $9.50
- risk: About half ETH and the pool is the counterparty of ETH perps traders; impermanent loss not counted, under their rule; apyBase 9.76% now against 3.91% used, so today's rate is well above the lasting one.
- Snapshot row matched to GMX market 0x70d95587... by tokens and size: 10,967 ETH plus $24.9M USDC is the $48.1M TVL.
- GM buy fee 0.07% read on-chain (0.05% if the deposit improves balance). GM sell fee reads 0.00% on-chain; I charge 0.07% anyway. If 0 holds this route is $10.06.
- Market open and under its caps (eth_call). No swap needed: USDC is the short token.
- Exit room: open interest $6.29M long and $8.19M short, available liquidity about $61M and $58M (GMX API), far above $5,000.

## Only the assets they list (ETH, wstETH, WBTC.B)

1. GMX V2 BTC/USD [WBTC.b-WBTC.b] GM (single-token): $19.11
2. GMX V2 ETH/USD [ETH-USDC] GM: $6.56
3. Morpho Blue wstETH/WETH LLTV 94.5%: $1.01

- With the Uniswap V3 wstETH-WETH 0.01% pool (ecd0c563-8aa2-423e-b8e9-d3259a316df9, TVL $4.23M, $5.6M/day, just under the $5M bar) instead of the 0.05% default, costs fall $6.00 and it reads $7.01.
- 30-day borrow picture is very different: Morpho API monthly 2.314%, live 2.566%, against the 1.814% used. At 2.314% net is 3.26%, about -$3.10 a month at the fees above.

## Families searched

| Family | Routes | Result |
|---|---|---|
| LST/LRT loops against native (wstETH, weETH, rETH, sAVAX, JitoSOL, mSOL) on Aave V3, Morpho Blue, Compound V3, Fluid, SparkLend, Kamino | 24 | Only sAVAX pays for leverage after costs at more than a dollar. wstETH on Ethereum 3x: $1.01. On L2s every swap in and out costs more than the spread earns, so they settle at 1x and lose money ($-1.64 best). |
| Loops against stables or USD debt (LST and BTC collateral) | 7 | Borrow is 4.6 to 5.7% on these routes, above the collateral yield on every one, so all settle at 1x. |
| BTC collateral loops (eBTC/WBTC; cbBTC and WBTC against USDC) | 4 | No positive route: BTC collateral pays 0.00 to 0.21%, so each is a loss equal to its costs. Three of these four are counted in the row above. |
| Perps house vaults (GMX V2 GM on Arbitrum and Avalanche) | 4 | 138 snapshot rows, 5 with TVL at or above $5M. 4 scored; USDG-USDG ($5.73M, 0.12%) left out because direct purchase is whitelist-only per docs.gmx.io. All Avalanche GM pools are under $5M. GLV vaults have no snapshot row (see suspicious). |
| LST/LRT holds (ETHx, ezETH; other LSTs are the 1x point of their loop route) | 2 | Negative in month one. |
| Staked-asset LPs (Curve and Convex ETH/stETH, Kamino SOL/JitoSOL) | 4 | Negative: lasting rates of 0.5 to 2.0% below a plain hold. |
| Searched, nothing eligible | 0 | Euler V2 (no staked or BTC vault at $5M; ewstETH-2 is $3.3M). HyperLend (its staked HYPE collateral is Kinetiq, not passed, or unlisted issuers). Dolomite (WETH not borrowable on Ethereum). Inverse FiRM (wstETH $1.4M). Origami (lov-wstETH-a about $0). Symbiotic (base 0). Aave Plasma and Sonic (ETH reserves frozen). Aave Linea (under $5M). Compound WETH comets on L2 (collateral under $5M). Morpho on Monad wstETH/WETH scored but marked not routable: no passed DEX lists wstETH on Monad. |
| Coverage screen |  | 369 staked-asset and BTC rows in passed lending projects on passed chains read, 108 at TVL >= $5M; those not scored are stable-debt markets that settle at 1x, or issuers not passed or not listed. |
| Totals | 42 | 42 routes in the passed set, 298 leverage points, plus 5 outside routes. Stable loops are outside this tier's asset list and not ranked. For reference, sUSDe hold on Ethereum is about $9.46 a month and a 3x sUSDe loop on Morpho about $4. |

## Outside their passed set

| Route | L | Net APY | Costs | $/month | Should it pass |
|---|---|---|---|---|---|
| Sanctum INF hold (Solana) | 1.00x | 5.225% | $17.45 | $4.02 | Sanctum Infinity: not passed for no audit on record. $184M TVL; it should pass only if an audit of the code a route would use is found. |
| JupSOL hold (Solana) | 1.00x | 5.149% | $17.45 | $3.71 | Jupiter staked SOL: not listed at all; $484M SPL stake pool, permissionless; should be screened like Jito/Marinade. |
| Hyperliquid HLP (4-day lockup) | 1.00x | 0% | $2.10 | $-2.10 | HLP: not passed for no audit on record; its snapshot base rate is 0 today, so it scores nothing under their rule anyway. |

Nothing outside beats the passed top 3. Left out: BENQI Lending sAVAX/AVAX loop (AVAX borrow pool TVL $3.82M < $5M (sanity); also BENQI Lending not passed (launch date unread). 3x would be 3*(4.863+0.001)-2*3.203 = 8.19% net, same exit-liquidity problem as the Aave route.); Pendle PT-wstETH-30DEC2027 (TVL $4.75M < $5M); Jupiter Lend JupSOL/WSOL loop (SOL borrow 5.24% > JupSOL yield 5.15%: leverage loses; collapses to the JupSOL hold); GMX on Solana (gmx-solana) GM pools (every pool < $2M TVL); Yield Basis BTC/ETH pools (staked yield is YB emissions (apyBase null); unstaked base 0-1.8%; not passed (no audit on record)).

## Looks wrong or suspicious

- GMX GLV vaults are missing from the snapshot, though GMX V2 is passed. GMX API (arbitrum-api.gmxinfra.io, fetched 2026-11-01): GLV [ETH-USDC] about $14.4M, 7d 16.27%, 30d 16.15%. Not ranked, no snapshot row. At 16.15% it would gross about $66 a month and take first place by far. Whoever claims the best high-tier route needs an answer for it.
- GMX BTC/USD [WBTC.b-WBTC.b]: GMX API 30d APY 66.1%, 7d 14.5%; DefiLlama 30-day mean 6.47%, now 8.50%. Route #1 rests on the 6.47%.
- platforms.json passes GMX with "No exploit losses over $1M in 2 years". DefiLlama hacks lists GMX V1 on Arbitrum, 2025-07-09, $42M taken, $40M returned, so $2M net inside the 2 years. It was V1, not V2, but it is the same protocol.
- Aave API (api.v3.aave.com): market-level eModeCategories.reserves is wrong for Avalanche. Category 2 reads "ETH correlated" with WETH.e, sAVAX, USDe there, while per-reserve eModeInfo reads "AVAX correlated" with sAVAX and WAVAX. The Pool contract settles it (eth_call on 0x794a...14aD): category 2 is "AVAX correlated", LTV 93%, LT 95%, collateral WAVAX and sAVAX, borrowable WAVAX. An engine reading the market-level list would miss the sAVAX loop.
- DefiLlama Morpho rows give only the collateral symbol, not the loan asset. I matched them to blue-api.morpho.org by LLTV, size and rate. Three snapshot borrow rates differ a lot from live: wstETH/WETH 96.5% 1.845 against 2.236, wstETH/WETH 94.5% 1.814 against 2.566, weETH/WETH 94.5% 1.869 against 3.898.
- One-day spikes the lowest-of rule correctly removes: Origami SUSDS-S apyMean30d 2391.9%, GMX USDC-USDG apyMean30d 80.8%, Yield Basis YB-WETH apyBase 731%.
- DefiLlama chartLendBorrow is now behind a paid plan, so 30-day borrow history came from the Aave and Morpho APIs, for those markets only.
- GMX docs: trading in NEAR/USD and XRP/USD [WETH-USDC] and ZEC/USD and HYPE/USD [BTC-USDC] is moving to USDG pools, with size stops from 2026-11-02 00:00 UTC. The two GM pools in my top 3 are not named, but fee income can shift.

## Assumptions

- month: 30/365 of the net APY on 5,000 USDC, less all costs in and out.
- rates: Snapshot only (2026-11-01 08:32 UTC). Earn = lowest of apyBase, apyBase7d, apyMean30d. Borrow = current apyBaseBorrow. Live APIs were used only for LTV, LT, caps and fee factors, and for the 30-day borrow notes.
- bridged_lst_yield: wstETH and weETH on an L2 earn the Ethereum staking rate, read from the Lido and ether.fi Ethereum rows.
- swap_fees: A known fee only where a passed DEX pool for that pair on that chain has TVL >= $5M: Ethereum USDC-WETH 0.01%, Arbitrum and Base USDC-WETH 0.05%, Avalanche USDC-WAVAX 0.05%, Arbitrum USDC-WBTC 0.05%, Ethereum weETH-WETH 0.05%. Otherwise the brief default: 0.10% volatile, 0.05% for LST to native.
- mints: Free native-to-LST mint where the issuer mints on that chain: Lido, ether.fi, Stader, Renzo on Ethereum; BENQI on Avalanche; Jito and Marinade on Solana. Exit is always a swap.
- loop_swaps: Entry C at the USDC rate plus L*C at the LST rate unless minted. Exit L*C at the LST rate plus C at the USDC rate.
- gas: 7 tx for a 1x route, 8 for a loop with flash-loan leverage or a GM route, more for a hand-built loop off Ethereum (11 + 7 per borrow round); $1 per tx on Ethereum, $0.05 elsewhere. CCTP $2.10 round trip off Ethereum. On Ethereum the only loops that settle above 1x are Morpho wstETH/WETH, and Morpho Bundler3 has stakeEth and wrapStEth actions (github.com/morpho-org/bundler3, EthereumGeneralAdapter1), so the free Lido mint fits inside the one flash-loan tx.
- liquidation: Distance = 1 - (L-1)/(L*LT). Where LT was not read (Compound, Fluid, Spark, Kamino) maxLTV stands in for it, which understates the distance; none of those routes makes the top 3.
- free_liquidity: Borrow leg passes if our borrow is at most 2% of free liquidity.
- scope: Top 3 are distinct routes; each asset and market appears once, at its own best leverage. Tier cap 3x.
