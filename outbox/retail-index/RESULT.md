# Retail index v5: rules written down before the first run

Registered 2026-11-05, before `index.py` or `backtest.py` has produced a single number. Nothing below is fitted to
data: every choice is a stated principle, so there is little to overfit with four cycle tops.

Why: Cymetica's retail v4 (turnover / market cap) fails its own back-test (B1 2021 autumn 68.2, B2 2018/19 50.0 and
2022 51.8, Spearman with BTC price -0.39), and v3 (dollar volume) tracks price (+0.65). We want a measure of people
and leverage, price-controlled, that wakes before a run and peaks at the tops.

## The week

A row is labelled by a Monday 00:00 UTC, `W`, and holds only what was known at `W`: the days `[W-7d, W)`. The last
row is the Monday after the last full week, as in Cymetica's series, so rows line up one to one.

## Inputs (public, anonymous GET, through `build_source_client`)

| Family | Member | Series | From |
|---|---|---|---|
| turnover | Coinbase | BTC-USD + ETH-USD daily volume x close, weekly sum, / (BTC + ETH market cap, Coin Metrics) | 2015 |
| turnover | Upbit | KRW-BTC + KRW-ETH weekly KRW traded value / USDKRW (Frankfurter) / same market cap | 2017-10 |
| turnover | Binance spot | BTCUSDT + ETHUSDT weekly quote volume / same market cap | 2017-08 |
| premia | Kimchi | Upbit KRW-BTC weekly close / (Binance BTCUSDT close x USDKRW) - 1 | 2017-10 |
| premia | Coinbase | (Coinbase BTC-USD close - Binance BTCUSDT close) / Binance close | 2017-08 |
| leverage | Funding | Binance perp funding rate, BTCUSDT and ETHUSDT, weekly mean | 2019-09 |
| chase | Breadth | share of the alt pairs whose 13-week return beats BTC's | 2017-11 |
| chase | Froth | share of the alt pairs up 50% or more in 4 weeks | 2017-11 |
| fuel | Stablecoins | 13-week change of total stablecoin supply, % (DefiLlama) | 2017-11 |
| attention | Wikipedia | weekly views of Bitcoin, Ethereum, Cryptocurrency (en, user) | 2015 |

Alt pairs: the Binance USDT spot pairs with the 100 largest 24 h quote volume today, minus stablecoins, leveraged
tokens, BTC and wrapped coins; a pair counts in a week only if it has the history. **Known bias, stated up front:**
the list is of survivors, so alt returns and breadth read better than they were. It is applied to every version of
every test the same way.

Left out of v5.0 on the plan's own rule (a family joins with at least 104 weeks of history): new rails (DEX share,
memecoin launchpad revenue, 2024-03 on) and Hyperliquid perps. They are read at the next review.

Baselines: Cymetica's v3 (`series.retail_euphoria`), v4 (`series.retail`), Fear & Greed (alternative.me, 2018-02 on),
BTC price percentile, funding alone.

## The index

1. **Detrend** turnover members and Wikipedia: divide by the trailing 104-week median of their own past values
   (at least 26 weeks), so a slow structural slide does not read as sleep, which is what sinks v4.
2. **Percentile** every member: its rank (ties half) among the trailing 208 weeks, itself included, at least 52
   weeks, scaled 0 to 100. No fitted weights.
3. A **family** is the mean of its members' percentiles. The **index** is the mean over the families that have a
   value that week, equal weight. At least 3 families = scored; exactly 2 = **thin** (shown, flagged); fewer = empty.
4. **Zones** as Cymetica's panel: under 25 asleep, 25 to 40 waking, 40 to 75 active, 75 and over saturated.
   **Awake** event: the index crosses up through 40 having been under 25 in the prior 26 weeks.

## Events (dates from public history, set before the first run; window = date +/- 6 weeks)

- Tops: 2018-01-15, 2021-05-17, 2021-11-08, 2024-12-16.
- Lows: 2018-12-17, 2022-11-21, 2023-09-04.
- Extended set: every turning point of the alt basket (equal-weight, weekly, log) with a 40% reversal (zig-zag).

## Checks

- **B1** in every scorable top window the highest week is at least 70. A window with fewer than 2 families is "not
  scorable", never a pass; one with 2 is marked thin.
- **B2** in every low window the lowest week is at most 35.
- **B3** |Spearman with the BTC weekly close|, 2018-01 to now, is at most 0.40.
- **B4 robustness** leaving out any one family moves the latest reading by at most 15 points, and B1 and B2 do not
  change for any single left-out family. Leaving out one cycle (its windows) changes no other cycle's verdict.
- **B5 forward** 13-week forward return of the alt basket in saturated weeks (75 and over) against all other weeks,
  difference with a 95% block-bootstrap interval (13-week blocks, 2000 draws, seed 1). Same for BTC. Reported, not a
  pass/fail: the sample is four tops.
- **B6 episodes** of saturated (75 and over): the share followed within 26 weeks by an alt-basket fall of 30% or
  more from its running maximum. Of Awake events: the share followed within 26 weeks by a 50% rise.
- **B7 segments** every number above is also given for 2018 to 2023 and for 2024 to now; nothing was fitted, so the
  second segment is a clean look, and it is read as one.
- **B8 permutation** event capture (the share of top windows with a 70+ week and of low windows with a 35- week) against
  2000 shuffles of the same weeks in 13-week blocks (seed 1).
- **A/A** `index.py` and `backtest.py` run twice give byte-identical output before a number is believed.

Every baseline gets the same B1, B2, B3 and B6.

## Done-when (operator may change)

- [ ] A/A holds.
- [ ] Ours passes B1 and B2 and B3; their v4 is shown failing on our own run.
- [ ] On 2024 to now ours is not worse than every baseline on B1, B2 and B6; if it is, the report says so.
- [ ] Charts (ours; theirs; overlay) rendered and looked at, then given to the operator.
- [ ] Forward log started with the first reading.

## What is not claimed

Four tops cannot prove the next two to three years. If ours fails B1, B2 or B3, or does not beat the baselines on
2024 to now, the result is "no better" and it is reported that way, with the table.
