# Capital Maximizer

Demo of a Cymetica product idea (the operator, 2026-10-28; first drawn as Yield Booster the same morning): the yield loops people ran by hand — lock USDC, buy BTC or ETH, post it as collateral, borrow, buy more — automated, with a finder that brings the three best strategies right now. Audited DeFi only, no KYC.

**Maximize:** Risk (Conservative, Medium, High Risk, OG Gambler, each with its max profit a month) → Amount (USDC) → Strategies (the finder reads the pools and lays the top 3 side by side as skill trees; leverage is tuned with − / + inside each tree) → Plan (the picked tree full width, a leverage slider, the max profit, Start).
**Platforms:** every supported protocol with its DefiLlama category, TVL, audit status, chains, how many pools were read and what the routes use it for.

## Run it

```
python -m http.server 8799 --bind 127.0.0.1 --directory outbox/capital-maximizer
```

then open http://127.0.0.1:8799/mock.html. Opening `mock.html` straight from disk works too. Nothing is sent anywhere; Start only shows a running state.

`?step=1..4&tier=conservative|medium|high|og&amount=5000&pick=0..2&lev=3` opens a state, `&shot=1` freezes it, `?tab=platforms` the Platforms tab, `?logo=1` the mark large.

## The numbers

One model (`cm-core.js`) makes every figure: the cards, the amount screen, the three trees and the plan, also after the leverage is tuned (`tests/repo/test_capital_maximizer.py`; `render.py` checks the page shows the same number on every screen).

- Rates are today's DefiLlama pools, each by pool id (`data.js`, written by `rates.py`): the lowest of today's, 7-day and 30-day APY. A month is (1 + APY)^(1/12).
- **Max profit**, the one figure shown: the month ETH and BTC rise 20 % and today's rates hold. The bad month (they fall 20 %, yields halve) is never shown; it decides what each tier may offer: Conservative never loses and uses three protocols, Medium loses at most 15 %, High Risk at most half and is never liquidated in it, OG Gambler is never closer than a 5 % move to liquidation.
- The three are the best of different kinds (one per protocol and asset), so three leverages of one loop never fill the list. Leverage tunes in tenths from 1.5× to the tier's cap, while the market would still lend and liquidation stays at least a 5 % move away.
- A loop is liquidated where its debt reaches the market's LTV; Morpho's liquidation bonus from its LLTV, Aave 5 %.

## The platforms

36 platforms on 21 chains, picked 2026-10-28 from DefiLlama by one rule that `rates.py` re-checks on every refresh (a platform that stops passing stops the refresh): audited per DefiLlama; listed a year or more; at most $1M lost and not returned in the last two years (DefiLlama hacks, any version); at least $30M on chains where Circle's CCTP moves native USDC, so a cross-chain move never holds a wrapped dollar (BNB Chain and Tron have no native USDC); permissionless (no exchange-issued token, no KYC pool).

The finder builds routes from 10 of them today (Aave, Compound, Morpho, Sky, Lido, ether.fi, Rocket Pool, Ethena, Uniswap, Curve; a cyan dot on the tab). GMX left the finder by the same rule ($2M of a $42M GMX V1 hack not returned, 07/2025), as did Spark Savings (no audit on DefiLlama; SparkLend passes). Left out, the large ones: Drift, Kelp, Cetus, Balancer, Moonwell, Yearn, Across, NAVI, Venus (lost funds); Jupiter, Orca, Raydium, Hyperliquid HLP, Sanctum (no audit on DefiLlama); Binance, Coinbase and Bybit staked tokens (exchange-issued); Liquid Collective (KYC); Maple (open access not verified). Cymetica makes its own selection.

## Files

- `mock.html` the page and its styles · `cm-core.js` the model, the finder, the leverage range · `cm-ui.js` the views and the skill trees
- `data.js` the snapshot · `rates.py` refreshes it · `render.py [dir] [width]` pictures every state and checks the figures agree
