# Gem Screener, the review's changes on their live page

Local copy for the operator to compare with the original: http://127.0.0.1:8847/gem-screener/app (preview `gem-screener-review`
in `.claude/launch.json`, or `python outbox/gem-screener-review/serve.py`). The original: https://cymetica.com/gem-screener/app

Their live page and snapshot, read anonymously, with `patch.js` and `patch.css` on top: every figure is theirs or computed from
their fields. Nothing is sent from the copy (every method but GET is refused). The box at the bottom right lists the ten changes;
a click opens the tab and marks the place. The blue numbers on the page are the same ten; "numbers" hides them.
The benchmark is unchanged (the operator, 10 Nov).

| # | Tab | Change |
|---|---|---|
| 1 | Top Picks | Growing fails an app whose own card says "Not growing" (their exit rule): Pump, Usual, Meteora leave the picks |
| 2 | Top Picks | Tier List: a coin cheap enough to be a pick says which gate held it back |
| 3 | Top Picks, Apps | Upside on what holders get (Hyperliquid pays 100%) |
| 4 | Apps | Upside after the next 12 months of new tokens, where they are 25% or more |
| 5 | Apps | Strength 3M against the market cap (price times the schedule's new tokens), not the price |
| 6 | Chains | Upside by fees on the row; red where the two measures are 5x or more apart |
| 7 | Chains | "shrinking" where DEX volume and stablecoins both fell 30% or more in a year |
| 8 | Chains | Nothing held back: the four inputs count as DeFiLlama gives them |
| 9 | Sectors | Ahead of the median sector counts from 3 points; Hot also has to beat BTC; a new stage "Holding up" for ahead of the others but behind BTC |
| 10 | Sectors | Talked about says how many people it rests on |

Not a spec: the operator decides from the picture which of these go into a request.
