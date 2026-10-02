# Supply Analyzer: the page, and what it says about Hyperliquid (notes, 2026-10-02)

The operator's idea: a standalone app like the Chart Analyzer (`cymetica.com/chart-analyzer`), later wired into the Gem Screener. Same input as the Chart Analyzer; the result has **a vertical meter on the left that pumps up on load** (the strength of the pressure) and **a pie of the supply with numbered callouts beside it**. Hyperliquid is the example. **Not a spec yet and not filed.** This file is the working notes for the request we write when the operator says how he wants it.

Files: `supply-analyzer/input-page.svg` (the input page, Chart Analyzer's own layout) and `supply-analyzer/result-hyperliquid.svg` (the result; the meter's segments pump up on load and fall back to the range, an animation in browsers). Both in Cymetica's palette and fonts, the Chart Analyzer's chrome. The Gem Screener's version of the same idea is the pie card in `gem-screener-pipe-pressure.md`.

## The meter and the formula

10 segments, bottom to top; **it fills upward with pressure**: 10 = buyers squeeze the pipe, 1 = new tokens flood it. Bands: 8 to 10 Squeezing, 4 to 7 Balanced, 1 to 3 Flooding. Dashed segments show the range when something is unknown, as the Degen meter does.

- free part = tokens in circulation minus tokens locked for 7 days or more (unknown terms count half)
- pull = what buybacks and burns take off the market in a year, % of market cap
- push = new tokens in a year, % of market cap: scheduled unlocks plus emissions plus staking rewards, gross, the same definition as Dilution
- net = (pull − push) ÷ free part, % a year
- **pressure = 6 + floor(net ÷ 2.5%), between 1 and 10**
- unknown pull counts 0; unknown push counts as the typical app (5% a year); the range shows the better and worse case

The orientation changed from the first Gem Screener sketch (there 10 was bad, to match the Degen meter). In an analyzer whose meter pumps up, a tall bar must mean strong pull, so the Gem Screener card follows the same number.

## Hyperliquid: what the pressure is

**1 of 10 by the team's schedule, up to 5 if the unlocked team tokens stay where they are.** Read 2026-10-02.

| Figure | Value | Where it comes from |
|---|---|---|
| Market cap, FDV | $19.7B, $84.7B; price $88.62 | DefiLlama token page |
| In circulation | 222.4M HYPE = 22.2% of 1B max | DefiLlama, CoinGecko, Tokenomist agree |
| Unlocked by schedule | 325.0M HYPE | the screener's own unlock data (DefiLlama) |
| **Unlocked, not in circulation** | **102.5M HYPE = 10.3%, ten monthly tranches** | 325.0M minus 222.4M; one tranche is 9.92M |
| Not unlocked yet | 675M HYPE = 67.5% | 1B minus 325.0M |
| Team schedule | 238M HYPE for core contributors over 24 monthly tranches, about 9.92M a month, next on 6 Oct 2026 | CryptoTicker and Tokenomist; another tracker says 6.4M a month and dates differ, so the amount is not settled |
| Team unlock as % of market cap | 9.92M × $88.62 = $879M a month = 4.5%, 53.5% a year | computed |
| Staking | 437.5M HYPE staked (44% of the max supply, more than the 222M in circulation, so it overlaps tokens that are not circulating); 7 days to unstake, 1-day delegation lock | Hyperliquid's public validator list, its docs |
| Staking rewards | about 9.5M HYPE a year = $843M = 4.3% of market cap; they come from the emissions reserve, not from revenue | validator list (stake-weighted APR 2.18%), DefiLlama Token Rights |
| Bought back | $145.3M in Q3 2026, so $581M a year = 2.95% of market cap (about $1.6M a day) | DefiLlama income statement, "Token Buy Back" |
| Burned | all of it: the Assistance Fund's HYPE was formally recognised as burned by a validator vote | DefiLlama Token Rights |

By schedule: push = 53.5% + 4.3% = 57.8% a year against pull 2.95%, **20 to 1**, net about −55% a year, pressure **1**. If the team keeps what it has unlocked so far (none of the 102.5M has entered circulation), push is the 4.3% of staking rewards, net about −1.3% a year, pressure **5**. One analysis (CryptoTicker) says only 1.75% of a tranche was claimed in March; we did not verify it.

**What it says about Ran's picture.** He prices the pipe at $20B and the buyback at $3 to 5 million a day. DefiLlama's measured buyback is about $1.6M a day, and his pipe leaves out the 102M unlocked tokens that stand outside it and the 9.9M that unlock every month. His point stands that the pipe is narrow; the pressure inside it is not clearly in the buyers' favour.

## A gap in the live Gem Screener, said now (not filed)

On Hyperliquid's detail the card "Market cap & supply" reads **"0% new tokens a week · emissions 30d: $0 · none in 90 days"**. DefiLlama's emissions dataset carries nothing for it (all windows 0), the screener's unlock record marks **61.2% of the supply "TBD"**, and the screener's own supply card has 325.0M unlocked against 222.4M circulating, a gap of ten team tranches. So "none in 90 days" is not what the source knows about this token: it is an absence read as zero, against ET-28821 item 11 ("none in 90 days is shown only when the source says so"). It matters twice: Hyperliquid is the **benchmark of the Dilution flag** (0.0% a week, which sets the 0.5% and 1.0% lines), and a gross-dilution gate that read it right would show about 1% a week, red. To file it by the sweep's rules it needs a check on the unlock record (`tbd_pct` large while `next_unlock.kind` is "none" and the unlocked supply exceeds circulating) and a report; the operator has not said yet, and it can go into the next request as a line under item 3 of the pipe spec ("unknown is never zero").

## What the Analyzer would need that the Gem Screener does not have

Per token: the staking contract and its exit rule, the burn route, the buyback wallet if one is published, and the unlock schedule with who receives it. Nexus said (REPLY-0115) that staked supply and burns are buildable from addresses with a public source, buybacks and unlock schedules partly, and wallet movements only where the project published the wallets. Hyperliquid has most of it public: the validator list, the Assistance Fund address, a published vesting schedule.
