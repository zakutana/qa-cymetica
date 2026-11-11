# Chart Analyzer: BULL TREND or BEAR TREND

The operator, 2026-11-11: the gauge is chaotic, a clicked setup covers the chart, 1W refuses a young token, and a
degen wants one verdict: is the chart in a bull trend or a bear trend, and how close is it to breaking. Like a
"money line", plus a DeMark count.

Open: `python outbox/chart-analyzer-trend/serve.py` (preview `chart-analyzer-trend`), then
http://127.0.0.1:8849/chart-analyzer?contract=CARDSccUMFKoPRZxt5vt3ksUbxEFEcnZ3H2pd3dKxYjp&chain=solana&tf=1d
(BTC: `?symbol=BTC&tf=1w`). It is their live page with a patch on top; add `&frozen=1` to replay the recordings only.

## What changed on their page

| Where | Before | Now |
|---|---|---|
| Left card | Gauge, NEUTRAL, "3 bullish · 4 bearish of 8 signals", WATCH, RISK, EDGE | **BULL TREND** or **BEAR TREND**, since when, how far from the flip price (% and in average candles), the close that turns it, 1H 4H 1D 1W by the same rule, the 9-13 count, one sentence |
| Chart | Trendlines, averages, numbered markers, SCORED window | The flip line (a step line under the price in a bull trend, over it in a bear trend), its fill, BULL/BEAR tags where it flipped, the flip price on the axis, 9 and 13 marks. Their other layers are still in Layers, off |
| Setups | A list with two percentages; a click opened a box over the chart | Two groups, for the trend and against it; a click opens the row in place and lights the line on the chart |
| 1W, 2W, 1M, 5D on a young token | "27 of 60 weekly candles", no chart | The chart opens on candles built from the daily ones; the trend needs 15 closed candles, under that it says TOO YOUNG and still draws |
| Edge | In the left card | Under "How it's measured" |

## The rule (trend.js, the only place a figure is computed)

- Flip line: an ATR trailing step line, ATR of 10 candles, 3 ATR from the candle's middle. In a bull trend it only
  moves up; a close under it turns the trend bear and the line jumps over the price, and the other way round.
- Distance: `|price - flip| / price`, and the same in average candle ranges: under 1 is AT THE EDGE, under 2.5 CLOSE,
  else ROOM.
- 9-13 count (DeMark-style): 9 closes in a row beyond the close four candles earlier, then a countdown to 13.
  It marks a stretched move and is never the verdict.
- The names "Flip line" and "9-13 count" are plain on purpose: the indicators they resemble are other people's marks.

Checked against an independent Python version on three candle sets: 63 comparisons, all equal.

## Data

`sock.js` stands in for their socket and plays `fixtures/` (their own frames, recorded once per coin and timeframe,
replayed for an hour). A coin with no recording is asked of their socket once. Subscribes spent while building: 14
(CARDS 1h/4h/1d/1w and BTC 1h/4h/1d/1w; CARDS 1h and 4h answered "collecting" every time and were asked again).

Not filed, no request written: that is on the operator's word.
