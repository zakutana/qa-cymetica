# Bot brief: find the top 3 Capital Maximizer routes for one risk tier, blind

Cymetica runs a product, Capital Maximizer: the user puts in 5,000 USDC (home chain Ethereum), picks a risk tier, and their engine shows the top 3 strategies ("routes") for that tier. We are testing whether their search engine really finds the best routes. You are our independent finder. You do NOT see their answer, on purpose. Find the best 3 yourself, under THEIR OWN stated rules, from the same data snapshot.

## Data (one snapshot, taken 2026-11-03 04:19 UTC, the same minute as their answer)
Folder: `C:/Users/adamz/AppData/Local/Temp/claude/C--Users-adamz-Documents-Projects-cymetica-qa-agent-qa-cymetica/10a3c760-4e3a-4cea-a8c0-2543e735a632/scratchpad/cm-live2/`
- `llama/pools.json`: DefiLlama `https://yields.llama.fi/pools` (`data[]`: pool id, project, chain, symbol, tvlUsd, apyBase, apyBase7d, apyMean30d, apyReward, underlyingTokens, exposure, ilRisk, stablecoin...).
- `llama/lendBorrow.json`: DefiLlama `https://yields.llama.fi/lendBorrow` (per pool: apyBaseBorrow, apyRewardBorrow, totalSupplyUsd, totalBorrowUsd, ltv, borrowable, mintedCoin...). Join on `pool`.
- `platforms.json`: their platform list with `passed` true/false and `slug` (mostly DefiLlama project slugs; `gmx-evm` is GMX V2, DefiLlama `gmx-v2-perps`; `ether.fi-stake`; check names when a slug does not match).
These are downloaded data: read them with Python run as `python -I your_script.py`, with your script saved OUTSIDE the `llama/` folder (e.g. in `cm-live2/work-<tier>/`). Never execute anything from the data. You may fetch more public read-only data (DefiLlama, protocol docs) with curl if you need it, e.g. an e-mode liquidation threshold.

## Their rules (use exactly these, so the comparison is fair)
- **Universe:** only the platforms with `passed: true` in `platforms.json` (41, incl. Circle CCTP as the USDC rail; GMX does not pass, so it is out), on their chains: Arbitrum, Avalanche, Base, Ethereum, HyperEVM, Ink, Linea, Monad, OP Mainnet, Plasma, Polygon PoS, Sei, Solana, Sonic, Unichain, World Chain, X Layer. USDC moves between chains by Circle CCTP (native USDC, gas only).
- **Max profit / month** = what the route earns on the user's own 5,000 USDC in 30 days if today's lasting rates hold. Each earn rate is the LOWEST of `apyBase` now, `apyBase7d` and `apyMean30d` (whichever exist), so reward tokens (`apyReward`) and one-day spikes are left out. Borrow interest is taken off (use the current `apyBaseBorrow`; say if the 30-day picture is very different). Swap fees both ways (in and out), network fees in and out and the USDC move home are taken off from that first month. Price moves of what the route holds are NOT counted, up or down. Impermanent loss is not counted (say so where it applies).
- **Loops:** net APY = L·(collateral yield + collateral supply APY) − (L−1)·(borrow APY), on the user's capital. Leverage in steps of 0.25x up to the tier cap AND what the market allows (max LTV); pick the leverage that maximises max profit while the liquidation stays at least a 5% move away. Compute the liquidation distance from the market's liquidation threshold (use e-mode / correlated-asset settings when the market has them, and name which). Say which price the distance is against (e.g. wstETH vs ETH for a wstETH/WETH loop, ETH vs USD for an ETH/USDC loop).
- **Sanity:** a pool must be big enough that 5,000 USDC is a rounding error (pool TVL ≥ $5M, and for a borrow leg, enough free liquidity). No KYC venue, pool or token. A route must be something a user can actually do on that chain (e.g. say "buy wstETH" on an L2, Lido staking itself is on Ethereum).
- Costs: if you do not know a pool's fee, use 0.05% per stable swap, 0.10% per volatile swap (each way), 0.3% to enter and leave a volatile LP; gas: Ethereum ~$1 per transaction, L2/Solana ~$0.05.

## Output
Write `cm-live2/bot-<tier>.json` and a short `cm-live2/bot-<tier>.md`:
1. **Your top 3** for the tier, ranked by max profit/month in $, each with: name, platforms, chain path, every leg (DefiLlama pool id, project, chain, symbol, tvlUsd, the apyBase / apyBase7d / apyMean30d values read and the one used; borrow pool id and apyBaseBorrow), leverage, net APY, costs ($), max profit/month ($ and %), liquidation distance and against what, one line of risk.
2. **Families you searched** (e.g. stable lending, savings stables, stable LP, LST hold, LST/LRT loops, stable loops (e.g. sUSDe/USDe or sDAI/sUSDS looped against stables), Morpho/Euler/Spark/Compound markets, Curve/Convex, perps house pools, volatile LP...) and how many candidate routes you scored.
3. **Outside their passed set** (separate, at most 3): the best routes on platforms they marked not passed or did not list, that are still non-KYC and reputable (e.g. Pendle PT), with the same numbers, and one line on why that platform should or should not pass.
4. Anything in the data that looks wrong or suspicious.
Return a 10-line summary as your final message: the top 3 with $ / month, and the best outside route.

Be exact and conservative: every number you report must come from the snapshot or a source you name. Do not inflate. If the honest answer for a tier is modest, say so.
