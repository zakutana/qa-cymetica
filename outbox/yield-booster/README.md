# Yield Booster

Demo of a Cymetica product idea (the operator, 2026-10-28): the yield loops people ran by hand — lock USDC, buy BTC or ETH, post it as collateral, borrow, buy more — automated, with a finder that looks for the best route right now. Verified DeFi only, no KYC.

Four steps on one page: **Risk** (Conservative, Medium, High Risk, OG Gambler, each with its good and bad month) → **Amount** (USDC) → **Find** (reads the pools, builds every route, turns down what breaks the tier's promise, keeps the best) → **Route** (the money flowing through pipes, the month's result, Start).

## Run it

```
python -m http.server 8799 --bind 127.0.0.1 --directory outbox/yield-booster
```

then open http://127.0.0.1:8799/mock.html. Opening `mock.html` straight from disk works too. Nothing is sent anywhere; Start only shows a running state.

`?step=1..4&tier=conservative|medium|high|og&amount=5000&move=0.1|0.2|0.3` opens a state, `&shot=1` freezes it, `?logo=1` shows the mark large.

## The numbers

One model (`yb-core.js`) makes every figure: the cards, the amount screen, the finder's rows and the end of the pipe (`tests/repo/test_yield_booster.py`; `render.py` checks the page shows the same number on every screen).

- Rates are today's DefiLlama pools, each by pool id (`data.js`, written by `rates.py`): the lowest of today's, 7-day and 30-day APY. A month is (1 + APY)^(1/12).
- **Good month**: ETH and BTC up by the move (±10/20/30 %, the switch on step 1), rates as today. **Bad month**: down by the move, every yield halved, borrowing costs the same.
- A loop is liquidated where its debt reaches the market's LTV; Morpho's liquidation bonus from its LLTV, Aave 5 %.
- What each tier promises: Conservative — stablecoins in three protocols, no leverage, never a loss. Medium — loses at most 15 %, never liquidated. High Risk — up to 3×, loses at most half, never liquidated in the bad month. OG Gambler — up to 5×, may be liquidated, never closer than a 5 % move.

The protocol list (Aave, Compound, Morpho, Spark, Sky, Lido, ether.fi, Rocket Pool, Ethena, Uniswap, Curve, GMX on Ethereum, Arbitrum and Base) is ours for the demo; Cymetica makes its own selection.

## Files

- `mock.html` the page and its styles · `yb-core.js` the model and the finder · `yb-ui.js` the four views and the pipes
- `data.js` the rate snapshot · `rates.py` refreshes it · `render.py [dir] [width]` pictures every state and checks the figures agree
