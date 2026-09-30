# The 18 checks, looked at as a degen: which ones tell you something

2026-09-30 evening · Pharaoh (PHAR) detail read from `GET /api/v1/gem-screener/coins/pharaoh-exchange`; populations from the 96 coin records read at the 12:39 UTC snapshot (indicative: the 18:50 refresh moved some checks from "Not scanned" to scanned).

## How the level is made (yes, the circles are the meter)

18 checks → 6 areas → level = round(10 × the weighted mean of the six area scores). Weights out of 10: Control 2.5, Supply 2, Earnings 2, Liquidity 1.5, Heat 1, History 1. PHAR: 0.48, 0.68, 0.47, 0.55, 0.99, 0.67 → 5.97 → level 6. A check that was not scanned counts as half a risk and widens the range (PHAR 5 to 9: 7 of its 18 are "Not scanned"). The line at the end of each row is the text of the area's worst check.

## The three sentences

| Shown | What it means | Why it reads wrong |
|---|---|---|
| Supply: "Unlocks 0.0% unlocks in 90 days, 6.8% of tokens out" (red) | Nothing unlocks in the next 90 days, **but only 6.8 % of all tokens are out** (FDV is 14.7× the market cap), so 93 % can still arrive. The red comes from the 6.8 %. In the 62 scanned coins "bad" is: under about 10 % of tokens out (PHAR, UP, GIGA, TITN, SPRK), or roughly 10 % or more unlocking within 90 days (DUST, STREAM, SOLV; the exact cut is theirs, read from where caution ends at 6.3 % and bad starts at 11.3 %). | The text leads with the 0.0 %, which reads as good news, and says "unlocks" twice. |
| Earnings: "Trend Ignition, 3.6× spike" (orange-blue) | Last month's revenue was 3.6× a usual month, and it is one month so far. | Jargon; "Ignition" is the phase name. It is the worst of the three checks in the row, so it stands for the whole row. |
| Earnings circles are blue, not green, for $2.5M a month | "Real yield" is revenue over new tokens emitted: $2.5M against $1.3M is **1.96×** and the circle shows "2.0×". On the 96 coins the lowest green is 2.19× and the highest caution 1.97×, so green starts about 2×. "Ignition" is never green (9 caution and 2 bad of 11). "Reaches you" is "Not scanned" although its value is 99.9 %. | The page rounds to 2.0× and paints it the colour of 1.96×; the row never says the business nets +$1.2M a month after emissions. |

## Which checks say something (96 coins; not scanned = did not run)

| Check | Good | Caution | Bad | Not scanned | For a degen |
|---|---|---|---|---|---|
| Admin key | 31 | 5 | 6 | 54 | Matters only with the two below: merge into "Can the owner rug it" |
| Timelock | 1 | 0 | 21 | 50 (24 n/a) | Green on 1 coin: merge |
| Admin powers ("can mint") | 30 | 32 | 12 | 22 | Flagged on 44 of 74 scanned coins: common, not a warning alone; merge |
| Hidden supply | 39 | 3 | 1 | 53 | Keep; show only when scanned |
| Emission rate | 42 | 5 | 2 | 47 | Keep, together with unlocks |
| Insider flow | 35 | 0 | 0 | 61 | Never flagged on the 35 that ran: keep for when it runs |
| Unlocks | 22 | 26 | 14 | 34 | Keep; reword |
| Real yield | 21 | 9 | 19 | 47 | Core. Show the dollars |
| Trend | 10 | 29 | 46 | 11 | Keep; plain words |
| Reaches you | 13 | 14 | 43 | 26 | Keep: does the token earn from the business |
| Slippage on $10K | 7 | 28 | 54 | 7 | Core: can I get out |
| Market cap | 24 | 35 | 37 | 0 | Under $20M on 72 of 96: the screener is for small caps, so it is a constant. A plain number, not a verdict; slippage says the rest |
| Whales | 38 | 3 | 2 | 53 | Keep; show only when scanned |
| Price run 30 d | 64 | 16 | 5 | 11 | Core: already pumped |
| Strength 3M | 30 | 36 | 16 | 14 | Keep, in words ("price +199%, revenue growth a third of that") |
| Team | 23 | 4 | 0 | 69 | Keep; show only when scanned |
| Audit | 1 | 55 | 40 | 0 | Green on 1 coin: say what it covers |
| Track record (hacks) | 75 | 10 | 7 | 4 | Keep: one small icon |

On average 5.9 of the 18 are not scanned per coin and 5.3 are green. Control weighs most (2.5 of 10) while two of its three checks are not scanned on about half the coins: the biggest weight sits on the least known area.

## What I propose (goals, in the spec as 43 to 45)

1. **Ten questions instead of 18**: can the owner rug it (owner type, timelock, mint power as one); what new tokens are coming (emissions, unlocks, share out); does it earn after emissions; is it growing; do holders get a share; can I get out; already pumped; price against revenue; audit; hacks. Whales, insider flow, hidden supply and team stay but as one dashed group "Not checked yet" with the "Ask for Degen report" button.
2. **One plain line per row with the key number**, in the colour of its worst check. Supply: "7 % of tokens out (FDV 15× market cap), 0 % unlocks in 90 days". Earnings: "Earns $2.5M a month, $1.3M goes out as new tokens: +$1.2M". Trend: "Revenue 3.6× its usual month, one month so far". The reason for the colour goes in the tooltip.
3. **Orange for caution**, not light blue (light blue also means "does not apply" in the Legend): green, orange, red, blue-grey for neutral. The Degen meter's 4 to 6 zone follows.
