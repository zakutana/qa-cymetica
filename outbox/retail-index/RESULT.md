# Retail index v5: rules written down before the first run

Registered 2026-11-05, before `index.py` or `backtest.py` has produced a single number. Nothing below is fitted to
data: every choice is a stated principle, so there is little to overfit with four cycle tops.

Why: Cymetica's retail v4 (turnover / market cap) fails its own back-test (B1 2021 autumn 68.2, B2 2018/19 50.0 and
2022 51.8, Spearman with BTC price -0.39), and v3 (dollar volume) tracks price (+0.65). We want a measure of people
and leverage, price-controlled, that wakes before a run and peaks at the tops.

**Amended the same day, still before any run (the first commit is in git).** Reading the operator's own design notes
(`gem-screener/ARCHITECTURE.md` section 19, "Rejected") removed three inputs: Wikipedia pageviews ("nikdo tam
nechodi": lookups moved to chatbots, so the series decays for reasons unrelated to crypto), stablecoin growth as a
scored row (it peaks early in a cycle, not at the tops; a fact, not a score) and Fear & Greed (mostly computed from
price; retail is only what people do: it stays a baseline). A family of on-chain users replaces them, and B9 below
copies Cymetica's own acceptance rule that the top zone holds at most 10% of weeks, because a percentile scale
fills its own top quartile by construction unless the families have to agree.

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
| users | BTC | Coin Metrics active addresses (AdrActCnt), weekly mean | 2015 |
| users | ETH | Coin Metrics active addresses (AdrActCnt), weekly mean | 2015-08 |

Alt pairs: the Binance USDT spot pairs with the 100 largest 24 h quote volume today, minus stablecoins, leveraged
tokens, BTC and wrapped coins; a pair counts in a week only if it has the history, and breadth and froth need at
least 15 pairs that week. **Known bias, stated up front:**
the list is of survivors, so alt returns and breadth read better than they were. It is applied to every version of
every test the same way.

Left out of v5.0 on the plan's own rule (a family joins with at least 104 weeks of history): new rails (DEX share,
memecoin launchpad revenue, 2024-03 on) and Hyperliquid perps. They are read at the next review.

Baselines: Cymetica's v3 (`series.retail_euphoria`), v4 (`series.retail`), Fear & Greed (alternative.me, 2018-02 on),
BTC price percentile, funding alone. Fear & Greed is a baseline only, never an input.

## The index

1. **Detrend** turnover and user members: divide by the trailing 104-week median of their own past values
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
- **B9 top zone** the scored weeks at 75 and over are at most 10% of all scored weeks (Cymetica's own acceptance
  rule), and no "saturated" run is longer than 26 weeks.
- **A/A** `index.py` and `backtest.py` run twice give byte-identical output before a number is believed.

Every baseline gets the same B1, B2, B3 and B6.

## Done-when (operator may change)

- [ ] A/A holds.
- [ ] Ours passes B1, B2, B3 and B9; their v4 is shown failing on our own run.
- [ ] On 2024 to now ours is not worse than every baseline on B1, B2 and B6; if it is, the report says so.
- [ ] Charts (ours; theirs; overlay) rendered and looked at, then given to the operator.
- [ ] Forward log started with the first reading.

## Result, read 2026-11-05 (`python -I backtest.py`, digest 9302544b10deac10, run twice with identical output)

Weekly table 588 weeks from 2015-08-03, 511 scored; every source answered. The numbers are in `data/backtest.json`.

| | B1 tops (4) | B2 lows (3) | B3 vs BTC price | B9 weeks at 75+ | capture p (permutation) | extended events | 2024-now extended |
|---|---|---|---|---|---|---|---|
| **v5 (ours)** | **FAIL** 98* 80 **54** 74 | PASS 8 30 23 | +0.29 PASS | 9.8% PASS | 0.036 | 73% of 15 | 83% of 6 |
| Cymetica v4 | PASS 75 98 70 74 | **FAIL** 49 55 22 | -0.39 | 14.6% FAIL | 0.235 | 53% | 83% |
| Cymetica v3 | PASS | PASS | **+0.65 FAIL** | 21.3% FAIL | 0.009 | 67% | 67% |
| Fear & Greed | FAIL | FAIL | +0.24 | 9.8% | 0.362 | 93% | 100% |
| Funding percentile alone | PASS (2 windows n/s) | PASS (2 n/s) | +0.13 | 10.2% FAIL | 0.037 | 100% of 10 | 100% |
| BTC price percentile | PASS | FAIL | +0.36 | 68.5% FAIL | 0.751 | 47% | 50% |

Done-when, line by line: A/A holds (index.csv and backtest output identical on two runs) **yes**; ours passes B1, B2, B3 and B9
**no, B1 fails at 2021-11** (54); their v4 shown failing on our own run **yes** (B2: 49 and 55, and it is no better than shuffled weeks, p 0.24);
on 2024-now ours is not worse than every baseline **no, it is level with v4 and below funding and Fear & Greed on extended events**
(one top window, 74 against 87 to 100).

What the numbers say, and what they do not:

- v4 cannot be used: it never sleeps below 49 at the 2018/19 and 2022 lows and has slid to 14 because the market cap grew, not because retail left.
  v3 finds every dated top but is a price proxy (+0.65) and sits at 75+ for 21% of weeks (a 64-week run).
- v5 fixes both faults (B2, B3, B9 pass) but does not time the tops better than a single input. At 2021-11 three of its five families
  (turnover, users, chase) were below their spring-2021 level: retail activity peaked in April to May 2021 and the November top was a price and
  leverage top (funding percentile 77). That is read, not tuned away.
- Funding percentile alone is the best top timer in this sample (every scorable dated window, every extended event) and is one number, so it
  is not retail: it is leverage. It misses B9 by 0.2 points.
- No measure, ours or theirs, is a reliable "sell" at 75+: in 2018-2023 the alt basket went up on average in the 13 weeks after 75+ weeks
  (ours +152%, interval -48 to +358, 11 weeks), and the interval holds zero for all of them. The 75+ zone is "hot", not "over".
- B6 (a 30% fall within 26 weeks) is not informative: the base rate for ANY week is 83%, so 85% to 100% after a signal proves nothing. It is
  reported, not used. Awake events of v5 are followed by a 50% rise 63% of the time (19 events) against 46% for any week; in 2024-now 33% against 33%.
- v5 is noisy: median weekly move 5.1 points (v4 2.5, v3 2.3). A 4-week mean reads like Cymetica's tile but is worse at the tops
  (dated capture 57%, p 0.28), so it is for the eye only and is logged beside the weekly value.

Post-hoc, outside the rules above and marked so wherever shown: the "precision" column (share of 75+ runs that contain a confirmed alt top)
and the 4-week mean. Both were added after the first run.

Limits that stay: four tops; the alt basket is of survivors (alt returns read better than they were, breadth and froth start in late 2019 for lack
of 15 pairs earlier, so the 2018/19 and the 2018-01 windows have only two or three families); Coinbase and Binance dollar volume include
whatever wash trading they have. The 2024-now segment was not fitted, but it is one top and one cycle of lows' worth of data.

Forward: `state/retail_index/forward.jsonl` logs the weekly reading, the 4-week mean and the baselines (funding percentile, Fear & Greed, BTC
price percentile, Cymetica v3 and v4) every time `tick.py` is run (the operator starts it). `tick.py --read` shows what the alt basket and BTC
did 13 and 26 weeks after each logged week. That is the only test left that history cannot spend.

## What is not claimed

Four tops cannot prove the next two to three years. If ours fails B1, B2 or B3, or does not beat the baselines on
2024 to now, the result is "no better" and it is reported that way, with the table.

---

# Retail index v6: social attention only (second registered attempt)

Registered 2026-11-05, **before** `fetch.py` has read Wikimedia or the Reddit archive. This is the second try at the same
question, so it is not a clean one: v5's table is known (v5 reads 54 at 2021-11 because turnover, users and chase were below
spring 2021). The operator's brief is that retail is people, not price: v3 (+0.65 with BTC) is mostly price, v4 (-0.39) is its
inverse, and neither holds a social series. Every choice below is a stated principle; no weight or threshold is tuned.

**What the operator named and I looked at first.** Kryptomagazin's Social Metrics page (YouTube, App Store, Wikipedia) and
Cowen's Social Risk (YouTube, X, Coinbase app rank, Google Trends). Both depend on series with no history for YouTube and the
App Store; Kryptomagazin says so on its page. Only Wikipedia has a long history. Its own maxima (5-year page) are Cryptocurrency
2021-11-26, Ethereum 2021-11-13, Bitcoin 2024-12-11: **expected, not fitted**, that an attention family peaks in the 2021-11 window,
where v5 was low.

## Sources that can be tested on the past (public, anonymous GET, `build_source_client`)

| Source | Series | From |
|---|---|---|
| Wikimedia pageviews (CC0) | daily views, agent `user`, all-access, of en.wikipedia `Bitcoin`, `Cryptocurrency`, `Ethereum`, `Dogecoin`; weekly sum | 2015-07 |
| Reddit, Arctic Shift archive of Pushshift | submissions per week in r/CryptoCurrency, r/Bitcoin, r/ethtrader; comments per week if the archive answers the aggregate | 2015 |
| the same | submissions per week in r/CryptoMoonShots, r/SatoshiStreetBets, r/altcoin | each sub's first month |

A week `W` holds the days `[W-7, W)`, as in v5. The archive times out on long ranges, so Reddit is read one day at a time (see
Amendment 1 below). If a member cannot be read for a subreddit, the **member is dropped for every subreddit**, never filled; that is
why comments are not read: they are ten times the rows of submissions and the archive already refuses submissions in bulk. A subreddit with fewer than 78 weeks of history is not scored that week (26 to detrend,
52 to rank), so the degen family is absent or thin before 2019.

**Left out, and why:** YouTube (public RSS lists the last 15 videos, no history) and the App Store chart (Wayback has a gap from 2020
to mid-2022) are collected from now on and join only after 52 weeks, never in a back-test. X and TikTok have no licence-free history.
Google Trends answered 429 twice on 2026-11-05 and is unofficial: out. LunarCrush (about $90 a month, from 2020-01) only on the
operator's word. The Block shows YouTube, tweets and subreddit growth, but its terms forbid automated collection: looked at by
hand, never read by script.

**Known limits, stated up front:** Wikipedia attention has been decaying since chatbots took lookups, which the 104-week detrend
is there to absorb; Reddit membership grows and its rules and bots change; both are English-language, and neither is X or TikTok,
where much of today's retail talks.

**Amendment 1, 2026-11-05, still before any v6 number exists (no index, no table row has been looked at).** The archive answers
about 1.5 thousand rows a second and times out on bigger asks, so reading every day of six subreddits for eleven years would take
most of a day (r/Bitcoin 2017 alone: ten days a minute). **A Reddit member is therefore sampled: the submissions on the Tuesday and
the Friday (Prague days, the archive buckets in local time) of each week, times 3.5.** Both days must be read or the week is empty
for that subreddit. Wikipedia stays every day. The cost is noise: two days of seven are a rougher weekly count than seven, so
v6's weekly line is expected to be jumpier than a full read would be; the 4-week mean the peak signal uses smooths that, and the
report says so wherever the weekly line is shown. Same members, same detrend and percentile, no other change.

## The index, v6

Same machinery as v5 (`qa/retailindex.py`): every member is divided by the trailing 104-week median of its own past values
(at least 26), then ranked among the trailing 208 weeks (at least 52), equal weight inside a family and between families.

| Family | Members |
|---|---|
| attention | Wikipedia Bitcoin, Cryptocurrency, Ethereum, Dogecoin |
| crowd | submissions (and comments) in r/CryptoCurrency, r/Bitcoin, r/ethtrader |
| degen | submissions (and comments) in r/CryptoMoonShots, r/SatoshiStreetBets, r/altcoin |

**Index = mean of the families that exist; at least 2, exactly 2 is "thin".** Zones as v5: under 25 asleep, 25 to 40 waking, 40 to
75 active, 75 and over saturated. No price, turnover, funding or Fear & Greed enters.

**Written now, shown only if v6 fails below: v6b** = the three social families plus v5's `turnover` and `premia` (+0.09 and 0.00
with BTC price), equal weight per family. If v6 passes, v6b is not shown.

## The peak signal (written now, not tuned)

At week `i`, with `m` the 4-week mean of the index: **signal** = the index was at least 75 in some of the last 13 weeks, and
`m[i]` is at least 15 points under the highest `m` of the last 26 weeks. A signal fires on the first week that holds after one that
did not; none fires within 26 weeks of the previous one. It is read late by construction: it says the peak is behind us, it does not
forecast one. Scored identically on v6, v3 and v4:
- a dated top is **caught** if a signal fires within 8 weeks either side of it, and the signed delay is reported;
- a **false alarm** is a signal with neither a dated top nor an alt-basket top of the extended set (v5's zig-zag set) within 8 weeks.

## Done-when for v6 (the operator may change; their v3 is the bar)

- [ ] **B1' every top window holds a week at 75 or more** (stricter than v5's 70; B1 at 70 is printed too). The 2018-01 window is
  thin (two families at most) and is marked, as in v5.
- [ ] B2 every low window holds a week at 35 or less (v3 passes with 3, 25, 13).
- [ ] B3 |Spearman with the BTC weekly close|, 2018-01 to now, at most 0.40 (v3: +0.65).
- [ ] B9 weeks at 75 or more are at most 10% of scored weeks, no run over 26 weeks (v3: 21%, 64 weeks).
- [ ] B8 permutation p for the dated windows at most 0.05.
- [ ] Of the runs at 75 or more, at least 75% contain a confirmed alt-basket top (v3: 75%).
- [ ] The peak signal's table: tops caught, signed delay, false alarms, against the same rule on v3 and v4.
- [ ] B4, B5, B7 as in v5, A/A byte-identical, charts looked at, forward log started with the new code hash.

If it does not pass, the report says so with the table; nothing is tuned until it does. The index can say "saturated" in the past
top windows and quiet in the lows; whether it does so in 2027 is the only test left, and the forward log is where it is run.

## Result v6, read 2026-11-05 (`python -I backtest.py --v6 [--v6b]`, digests 42bafe1a9c60a1f5 and 0e8c12c77bb989b5, each run twice with identical output)

`data/social_weekly.csv`: Wikimedia every day, six subreddits on the sampled Tuesday and Friday of each week (all sampled days answered
after retries; `data/social_sources.json`). Nothing tuned after the first run.

| | B1 tops at 70 | **B1' at 75** | B2 lows (35-) | B3 rho vs BTC | B9 weeks at 75+, longest run | B8 p | 75+ runs holding a top |
|---|---|---|---|---|---|---|---|
| **v6 (ours)** | PASS 96 92 72 78 | **FAIL** (72 at 2021-11) | **FAIL** 2 8 **38** | **+0.45 FAIL** | **16.0%, 42 wk FAIL** | 0.062 FAIL | 100% of 3 (pass) |
| v6b (written beside it) | FAIL 97 93 **67** 72 | FAIL | PASS 6 18 29 | +0.39 PASS | 13.3%, 24 wk FAIL | 0.041 | 33% |
| Cymetica v3 | PASS | PASS | PASS | +0.65 | 21.3%, 64 wk | 0.009 | 75% |
| Wikipedia only (baseline) | PASS 98 97 80 87 | PASS | PASS 1 4 29 | +0.48 | 17.8%, 32 wk | 0.022 | 64% |
| v5 (earlier) | FAIL (54 at 2021-11) | FAIL | PASS | +0.29 | 9.8%, 14 wk | 0.036 | 50% |

**v6 meets one of its six lines** (the share of 75+ runs holding a top; three runs). It fails B1' at 2021-11 (72), B2 at 2023-09 (38), B3, B9 and B8.
The report says so; nothing is tuned.

**Peak signal** (rule above, same on all three): v6 catches **1 of 4** tops (2018-01, +5 weeks), signals on 2018-02-19 and 2021-08-23, one false alarm;
v3 catches 2 of 4 (+7 and +6 weeks) with 5 signals and 2 false alarms; v4 catches 0 of 4 with 4 false alarms of 5. It misses 2021-05 (its signal fired
in 2021-08, 14 weeks late), 2021-11 and 2024-12 (the index never fell far enough under its high to fire).

What the numbers say, and what they do not:
- **Social attention is not free of price either**: v6 +0.45 and Wikipedia alone +0.48 against the BTC close. People look at and talk about crypto when it is
  going up, so a measure of attention cannot be separated from price by choosing a different source. v3's +0.65 is the same fault, only larger.
- **Wikipedia alone does what v6 asks of the dated windows** (7 of 7, p 0.022) and the Reddit families make it worse (B2 at 2023-09, B9). That was not a
  choice written before the run (it was a baseline), so it is not adopted; it is read, and it is the next thing to test forward.
- **The 4-week mean is worse than the weekly line at the tops** (2021-11: 70 -> fails the 75 bar by more), as in v5; it is for the eye and for the peak signal only.
- **No measure here is a reliable sell at 75+**: alt basket 13 weeks later is up on average in 2018-2023 for v6 (+84%, interval -8 to +293, 33 weeks) as for
  v3 (+79%) and v5 (+185%); the interval holds zero in every case. 75+ means hot, not over.
- **Today (week of 2026-11-02): v6 36 (waking; 4-week mean 23), Wikipedia 54, v5 45, v3 39, v4 14.** All of them say the same thing: retail is not at a top.
- B4: leaving out attention moves the latest reading by -9.3 and changes the B1 verdict (it is flagged); leaving out the 2018 cycle flips 2021-11 to a fail.

Limits that stay: four tops; the Reddit members are two sampled days a week; Reddit membership and rules change; Wikipedia attention has been decaying
since chatbots took lookups; English language only; X, TikTok, YouTube and the App Store chart have no history here (the last two are collected from
2026-11-05 by `collect_live.py` and join after 52 weeks).

Forward: `tick.py` now logs v5 and v6 and whether the peak signal fires that week; read it with `tick.py --read`.
