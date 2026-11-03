# Quant Lab: is it the market or the setup? (3 Nov 2026, company 14)

Sources, GET only: `/quant-lab/search/results`, `/quant-lab/search/memory` (11,232 rows), `/how-it-fits.txt` (window rules, rule sizes), Binance hourly bars for the 12 USDT pairs (not their own price feed). Windows rebuilt from their worked example: 2,160 bars ending at the run's start hour, first 1,296 search, 24 skipped, last 840 blind. #3 reproduces their stated dates exactly.

## The windows

| Search | Search period | 12 coins, mean | Up | Blind period | 12 coins, mean | Up |
|---|---|---|---|---|---|---|
| #3 | 29 Jul to 21 Sep | +46.5% | 12/12 | 22 Sep to 27 Oct | -14.5% | 0/12 |
| #10 | 1 Aug to 24 Sep | +48.2% | 12/12 | 25 Sep to 30 Oct | -17.8% | 0/12 |
| #15 | 5 Aug to 28 Sep | +45.2% | 12/12 | 29 Sep to 3 Nov | -17.6% | 0/12 |

The three searches overlap almost entirely, so the 15 blind tests are one bull-to-bear turn seen three times, not 15 trials.

## The 15 blind rows

| Search | Rule | Coin | Search % | Coin % | Blind % | Coin % | Trades |
|---|---|---|---|---|---|---|---|
| #3 | stockbull_blue | AVAX | +20.90 | +76.0 | -6.87 | -20.4 | 74 |
| #3 | stockbull_blue | DOT | +29.60 | +55.4 | -3.09 | -17.0 | 59 |
| #3 | helix | DOT | +16.39 | +55.4 | -1.94 | -17.0 | 43 |
| #3 | stockbull_blue | LINK | +23.25 | +56.2 | -12.30 | -13.6 | 74 |
| #3 | stockbull_blue | SOL | +20.24 | +60.1 | -10.01 | -15.1 | 90 |
| #10 | stockbull_blue | AVAX | +18.06 | +63.0 | -14.79 | -19.3 | 88 |
| #10 | stockbull_blue | DOT | +26.61 | +50.5 | -10.97 | -17.9 | 65 |
| #10 | stockbull_blue | LINK | +23.00 | +57.8 | -15.10 | -20.1 | 75 |
| #10 | stockbull_blue | SOL | +20.86 | +59.8 | -14.57 | -21.0 | 105 |
| #10 | stockbull_blue | XRP | +22.73 | +42.5 | -8.78 | -20.4 | 79 |
| #15 | crispr | ADA | +12.21 | +31.2 | -1.54 | -22.5 | 2 |
| #15 | hybrid2_blue | ATOM | +19.09 | +34.8 | -6.43 | -16.6 | 25 |
| #15 | stockbull_blue | DOT | +29.31 | +47.7 | -9.70 | -18.6 | 60 |
| #15 | prion | DOT | +10.23 | +47.7 | -2.03 | -18.6 | 14 |
| #15 | helix | LINK | +14.23 | +71.6 | -7.77 | -24.5 | 53 |

* 15 of 15 lost, and the coin fell in 15 of 15. Mean blind -8.39%, mean coin -18.84%.
* Lost less than the coin in 15 of 15. This is not protection: a rule holds 10% of capital per position, at most 50% in the market for StockBot Blue.
* The ten stockbull_blue rows took 41% of the coin's rise (+23.46 of +56.9) and 58% of its fall (-10.62 of -18.34), the best picks of the grid included. A timing skill would show the opposite. A ratio only: no trade-by-trade replay.
* Rank correlation of search return against blind return: -0.43.

## What explains a search-period return

| Search | Model x market | Stop | Take-profit | Entry | Long rules positive | Short rules positive |
|---|---|---|---|---|---|---|
| #3 (1,728) | 94% | 5% | 0% | 0% | 83% | 0% |
| #10 (4,752) | 85% | 6% | 0% | 1% | 82% | 4% |
| #15 (4,752) | 85% | 6% | 0% | 1% | 82% | 6% |

Share of variance, one factor at a time. Stop levels are multiples of each rule's own stop, so part of that 5-6% is the rule itself.

First half against second half of the search period, 8+ trades, rank correlation in #10 and #15: different settings of the same rule and coin +0.05 and +0.06; between rule-and-coin pairs +0.54 and +0.49. A setting does not persist. Which rule on which coin does, inside one bull run.

## Why StockBot Blue

In #15, mean search return by rule: stockbull_blue +9.14 (50% max exposure, 118 trades), helix +7.06 (30%), hybrid2_blue +5.16 (50%), mitosis +4.34 (20%), then the rest under +3.1. The three short rules -2.91 to -7.91. Rank correlation of max exposure against mean return over the 13 long rules: +0.74 in #15, +0.69 in #3. It held the most in a rising market. 13 rules, one market turn: an association, not a proof.

## Structural consequences

1. Shortlisting needs a gain on the search period. In a bull search period that excludes nearly every short rule, so the rules most likely to have made money on this blind period are never tested there.
2. A winning short rule starts no bot (the spot lane is long-only).
3. The grid tunes stop, take-profit and entry, which barely move the result. What moves it (direction, exposure, market state) cannot be tuned.

## Open

* CIRCADIAN's entry per /how-it-fits needs a Bollinger width "in price" below 500. On a coin under a few hundred dollars that is always true. Not checked against a replay.
