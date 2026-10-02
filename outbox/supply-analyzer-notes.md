# Supply Analyzer: the page, and what it says about Hyperliquid (notes, 2026-10-02)

The operator's idea: a standalone app like the Chart Analyzer (`cymetica.com/chart-analyzer`), later wired into the Gem Screener. Same input as the Chart Analyzer. The result page has **a vertical meter on the left that pumps up on load** (the strength of the pressure), **a pie of the supply** beside it, and **a month slider** above both that moves the pie and the meter through time. Hyperliquid is the example. **Not a spec yet and not filed.** These are the working notes for the request we write when the operator says how he wants it.

Files: the spec is `supply-analyzer/SPEC.md`; the look is in `supply-analyzer/reference/`: `input-page.svg` (the input page, the Chart Analyzer's own layout), `supply-analyzer-hyperliquid.html` (the result page, interactive: the slider, a play button, the tank, the pie and the chart move month by month; `?m=15` opens it in the 15th month), two screenshots of it and `gem-screener-integration.svg`. Cymetica's palette and fonts.

## The supply flow: a tank you can watch (2026-10-02)

The vertical meter was replaced by an animated tank (the operator: he understood the outflow of a pipe but wanted to see the speed of the flows in motion). The tank is **the sellable pile**: the free tokens plus the staking that can leave at any time. **Red dots pour in** from two sources, the vesting vault and the reserve (the team's tranche and the staking rewards); **green dots leave** through the buyback pump, which splits to a flame (burned) and a vault (kept). The number of dots a second and their speed follow the monthly amount, so a 10.7M inflow against a 0.55M outflow is a stream against a trickle. The water level follows the pile, a dashed line marks where it stood today and a bracket shows the change since, in M. Staking in and out is drawn as a dashed pipe marked "flat", because it is not measured. The hero number is the yearly change of the pile (+28% for HYPE today); the 1 to 10 number stays as a small pill. Hovering any part (vault, reserve, tank, pump, flame, kept vault, staking) says what it is and what the month's figure is. The slider and the play button move the month; below the pie a chart shows the pile month by month against today's level, with the monthly inflow and buyback bars under it.

## The pie: the tokens in play, seven slices

The pie holds the tokens that exist in someone's hands or are bound to be (623M of the 1,000M max for HYPE). The reserve, the part of the max supply not paid out yet, is **not a slice**: it stands under the pie as one line, because the pie is for reading the pressure and the reserve only says where rewards come from (the operator asked what it was for). The names are generic, so one page works for any token.

| Slice | What it is | Moves with the slider |
|---|---|---|
| Free to sell | in circulation and not staked, including tokens already unlocked that nobody has moved (the operator: "unlocked, not moving" is the same as circulating) | grows with every vesting tranche; shrinks with every buyback |
| Staked, free to unlock | staking without a lock: can leave any time (HYPE: 7 days) | (held constant in the sketch) |
| Staked, locked | staking locked until a date; at that date it turns into Free to sell | for tokens that have such locks; HYPE has none |
| Vesting | locked allocations (team, investors) | a tranche a month moves to Free to sell |
| Newly paid out | emissions and mints since the slider's start: new supply | grows with every reward or mint |
| Bought back, kept | bought with fees and held by the project; it can return to the market | grows with every buyback that is kept |
| Bought back, burned | bought with fees and burned | grows with every buyback that is burned |

Buyback and burn are two slices because a project can do only a buyback (Aave, Collector Crypt are listed as buybacks without a burn). Both take tokens off the market now and both count in the pull; a kept one can come back, which the "firmness" line of the spec covers. For HYPE all of it is burned, so "kept" is 0.

## The release rate is the push of the pressure

The operator asked whether the rate at which tokens become sellable belongs in the pressure. **Yes: it is the push.** Each month the analyzer counts what becomes sellable (vesting tranches + emissions + locks that end) against what is bought back and burned, on the tokens that can be sold within a week:

- net = (burned − becomes sellable) × 12 ÷ (free to sell + staked without a lock + paid out), % a year
- **pressure = 6 + floor(net ÷ 2.5%), between 1 and 10**; 10 = buyers squeeze the pipe, 1 = new tokens flood it
- the meter shows the pressure of the month on the slider; the bars at the bottom show the release and the burn for every month

## Hyperliquid, read 2026-10-02

**Pressure 1 of 10 until Nov 2027, while the team receives about 9.9M HYPE a month; 5 of 10 from Dec 2027, when only staking rewards are paid out.**

| Slice today | HYPE | How we know |
|---|---|---|
| Free to sell | 206.9M (est.) | what is left of the unlocked supply after the burned and the staked tokens below |
| Staked, 7 days to leave | 229.7M (est.) | 437.5M staked in total (Hyperliquid's validator list), minus the 207.8M on the Hyper Foundation's own validators; unstaking takes 7 days (Hyperliquid's docs) |
| Staked with a lock | 0 | HYPE has no time-locked staking |
| Vesting (team) | 138.8M (est.) | 238M for core contributors, about 9.92M a month, 14 tranches left (trackers differ on the day and the amount) |
| Reserve, not paid out | 377.0M (est.) | 388.9M allocated to future emissions and community rewards, minus about 12M paid so far; the 207.8M the Foundation stakes is taken to come from here |
| Bought back & burned | 47.6M | the Assistance Fund's balance on Hyperliquid's own API, formally burned by validator vote |

Flows a month: team +9.92M (until Nov 2027), staking rewards +0.79M (stake-weighted APR 2.18% on 437.5M), bought back and burned −0.55M ($145.3M in Q3 per DefiLlama, at $88.62).

**Not measured, said so on the page:** how the staked tokens split between the Foundation and everyone else; the team's day and amount; future community rewards out of the reserve, which have no schedule; whether stakers leave.

**Correction (2026-10-02).** An earlier version of these notes called the 102.5M between DefiLlama's "unlocked" (325.0M) and CoinGecko's "circulating" (222.4M) "ten team tranches unlocked and not moving". That was inferred from the gap's size alone. DefiLlama's unlock data does not count the team's tranches at all (it carries them as "TBD"), so the gap is something else. The operator then merged "unlocked, not moving" into circulating, and the slice is gone.

**About Ran's picture.** He prices the pipe at $20B with buybacks of $3 to 5 million a day. DefiLlama's measured buyback is about $1.6M a day, and the team's tranches put about 10.7M HYPE a month into the market against 0.55M burned: 20 to 1. His pipe is narrow; until the team is fully vested the pressure in it runs against the holder.

## A gap in the live Gem Screener, said now (not filed)

On Hyperliquid's detail the card "Market cap & supply" reads **"0% new tokens a week · emissions 30d: $0 · none in 90 days"**. DefiLlama's emissions dataset carries nothing for it, and the screener's own unlock record marks **61.2% of the supply "TBD"**, which is the team's 238M and the rewards reserve. The team's monthly tranches are published by the trackers. So "none in 90 days" is not what is known about this token: it is an absence read as zero, against ET-28821 item 11 ("none in 90 days is shown only when the source says so"). It matters twice: Hyperliquid is the **benchmark of the Dilution flag** (0.0% a week sets the 0.5% and 1.0% lines), and with the tranches its dilution is about 1% a week, red. To file it by the sweep's rules it needs a check on the unlock record (a large `tbd_pct` while `next_unlock.kind` is "none") and a report; the operator has not said yet, and it can go into the next request as a line under the rule "unknown is never zero".

## What the Analyzer would need that the Gem Screener does not have

Per token: the staking contracts and their exit rules (lock or not, how long), the vesting schedule with who receives it, the emission schedule, the burn route, and the buyback wallet if one is published. Nexus said (REPLY-0115) that staked supply and burns are buildable from addresses with a public source, buybacks and unlock schedules partly, and wallet movements only where the project published the wallets. Hyperliquid has most of it public: the validator list, the Assistance Fund address, a published vesting schedule.
