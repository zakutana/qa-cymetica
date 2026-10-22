# Airdrop Farmer: rebuild spec

The design and a working test version of **Airdrop Farmer** for `cymetica.com/airdrop-farmer`. Everything here runs in a browser on test data: open `mock.html` (see README.md). The pictures in `pictures/` are the target; this file says what is on them, how every part behaves, and the exact numbers behind them. Farm names and figures are examples.

| Picture | What it shows |
|---|---|
| `pictures/1-farms.jpg` | Farms tab at 1440 px: the amount, the farm from above, the ranked list |
| `pictures/2-farm-list.jpg` | The top of the list at 100% |
| `pictures/3-start-farming.jpg` | The one confirmation before anything starts |
| `pictures/4-live-farms.jpg` | Live farms, 23 days into the same plan |
| `pictures/5-logo.jpg` | The logo |

---

## 1. Why a rebuild

The live build (read 2026-10-22 from `GET /api/v1/airdrop-farm/config` and `/programs`) misses the idea:

- **It farms nothing anyone is going to airdrop.** 7 of its 8 programs are chains whose token is already live (ETH, ARB, OP, HYPE, BNB, AVAX, POL); the 8th is LI.FI routing.
- **Its activity is the sybil pattern.** It bridges and swaps stablecoins "on a jittered human cadence", and every farm wallet is created, funded and driven by Cymetica on the same routes, so the wallets can read as one cluster. Airdrop programs filter exactly that out.
- **Fees can eat the deposit.** `daily_cost_budget_pct` is 0.35% a day on Balanced and 1% on Degen: up to 63% of a deployment in 6 months on Balanced, all of it in 100 days on Degen. Deployments are open (`open: true`).
- **The user cannot pick farms or amounts and sees no estimate.**

**The idea:** one amount of USDC, split across the real points programs, testnets and task farms of protocols that have **no token yet**, and a live view of what each farms.

**Keep from the live build:** one farm wallet per person, never pooled; every step a real transaction; stop any time, back to USDC; the 10% of realized profit fee.

---

## 2. Farms tab (pictures 1-3)

### Header
The logo (picture 5: an AI agent's round head with two green eyes under a farmer's wide-brim hat, a sprout growing from the crown, cyan to green), "AIRDROP" small over "FARMER". The two tabs **Farms** and **Live farms** are one segmented control: the active tab is solid green, Live farms carries the number of live farms. At the right: `FARMING · 10 farms · $5,000 in`, or `NOT FARMING` with a grey dot.

### Left: the amount
- Pill `412 FARMS · ONE DEPOSIT` (live count of listed farms).
- Slogan in three lines: **Deploy USDC. / Farm every airdrop. / Cymetica does the rest.** (last line green), then `Chatbots explain airdrops. Cymetica farms them.`
- The plan panel (glowing border):
  - `HOW MUCH USDC?` and, top right, `BEST SPLIT ✓` (or `↺ BEST SPLIT` once the user has changed a farm by hand; a click restores the best split).
  - One big amount input with a USDC pill and `MAX`; the balance under it.
  - `YOU FARM ≈` and the estimate **$900 – $3,890** big and green. When it changes it counts to the new value (about 0.4 s, ease-out).
  - `in airdrops over 6 months · 10 farms · $5,000 planted`.
  - One big green **START FARMING** (it reads **UPDATE FARMS** while farms are running).
  - Small: `Costs and fees are shown before anything starts · stop any farm any time`.

### Right: the farm from above (the signature)
An isometric field of plots, **one pillar of light per farm that is switched on**, as tall as the USDC in it, with the farm's own logo floating on top. It redraws on every change of any amount. One line under it: `Your farm from above: one pillar per farm, as tall as the USDC you plant.`

How it is drawn (`fieldSvg()` in `farm-ui.js`):
- Plot (tile) 116 x 58 px, 4 columns, `max(3, ceil(n/4))` rows, at most 16 plots; beyond that a small `+N more farms`.
- Plot centre: `x = ox + (c - r) * 58`, `y = oy + (c + r) * 29`. Plots are filled back to front (sorted by `c + r`), and farms are sorted by amount, **tallest first**, so tall pillars stand at the back and never hide short ones.
- Pillar footprint 52 x 26 px (half sizes 26 and 13). Height `16 + sqrt(amount / largest amount) * 134` px (square root, so small farms still show). Left face cyan, right face green, both fading downward; the top face solid green with a soft glow; a dashed stem up to the logo.
- Logo: a 34 px disc 32 px above the top face, ringed in cyan; a farm without a logo shows its initials.
- Free farms (testnets, tasks): a short cyan pillar, 16 px.
- Under the field a soft green ground glow; each plot has a faint inner diamond.

### The list: every farm, best first
`Every farm, best first` · `Ranked by what a dollar farms there. Drag to plant more or less.` · a search box. Then one list, one row per farm, columns:

| # | FARM | PLANT | USDC | EST. AIRDROP · 6 MO | ON |
|---|---|---|---|---|---|

- **#**: the farm's global rank; 1-3 in green.
- **FARM**: the farm's logo (46 px rounded square, green ring when on), name, and **one** chip: `TOKEN CONFIRMED`, `TGE Q4 2026`, `POINTS → INK`, `POINTS LIVE`, `PAYS DAILY`, `PAYS WEEKLY`, `FREE`, `SPECULATIVE`.
- **PLANT**: a thick glowing slider (8 px track, cyan-to-green fill, 22 px thumb with a green ring) with a cyan `BEST` notch at the best amount. The scale is the **square root** of the whole balance: position `p` in 0..1000 means `amount = balance * (p/1000)^2`, rounded to $10 below $1,000, $50 below $5,000, $100 above. Small and big bets both read.
- **USDC**: the amount field, two-way with the slider. Under it `best $700` only when the farm is off its best amount; a click sets it.
- **EST. AIRDROP**: the estimate for that amount as a big green range, `est. airdrop in 6 months` under it. It **moves under the finger while dragging**.
- **ON**: a toggle. Switching a farm on gives it its best amount (or the last amount it had, or $300).
- A free farm shows `FREE · NO USDC NEEDED` and `FREE` as the estimate. A speculative farm (no points program) shows `no estimate` with the reason. A farm switched off is dimmed and shows in grey what its best amount would farm (`if you plant $250`).
- Order: farms with an estimate by what a dollar farms there net of costs, then free farms, then speculative ones. **A farm with nothing to farm now** (points cap used up, no points phase) **is not listed.**
- `Showing 12 of 412 farms` and `Show 50 more` under the list.

### Behaviour of the amount
- Typing the amount fills in its **best split at once** (§4), and the field and list follow.
- **Any farm takes any amount up to the whole balance.** Changing one farm changes the total. Once all the USDC is in farms, what is added to one farm comes out of the farms that farm least (lowest rank first), and a short note says `$1,410 moved to Arcus from 5 farms that farm less`.
- `MAX` sets the amount to the whole balance (best split). Typing more than the balance is held to the balance on Enter or leaving the field.

### Start farming (picture 3)
One confirmation, nothing else: `START FARMING`, `10 farms · $5,000`, the estimate big, `See the 10 farms ▾` folded (farm, amount, estimate), `Est. cost (fees, funding, gas)`, the Cymetica fee, one line on what the agent does, `Cancel` and a green `START FARMING`. **Costs and fees appear here and nowhere earlier.**

---

## 3. Live farms tab (picture 4)

- **Left panel:** `EARNED SO FAR` and **$120 – $490** big and green; a green pill `+$13 today`; `day 23 of your 6 months · 10 farms · $5,000 planted`; one big **HARVEST $6** button that claims everything claimable (`NOTHING TO HARVEST YET`, greyed, when there is nothing); a quiet `Stop all farms` (asks once).
- **Right:** the same field, but each pillar is as tall as **what its farm has earned** (`6 + sqrt(earned / largest) * 144` px). A farm with something to claim glows (pulsing halo) and carries a green `HARVEST` tag over its logo. On day 0 every pillar is a short seed. Line under it: `Each pillar grows with what its farm has earned. A lit one is ready to harvest.`
- **YOUR 6 MONTHS:** the whole 6 months on one chart: earned so far as a glowing green area (claims as white dots), then a dashed cyan projection to `6 months ≈ $890 – $3,890` = earned so far plus each farm's planned estimate for its days left, so **on day 0 it equals the number shown at Start**. Labels: start date, `now`, end date.
- **CYMETICA 24/7:** one line with the last three different things the agent did and how long ago (`5h ago Points synced +2,581 on 6 farms`).
- **Your farms:** one row per farm: logo, name, one status chip (`FARMING`, `CLAIMABLE`, `TGE IN 7 D`, `CAP 81% USED`, `EPOCH ENDS IN 5 D`, `NO POINTS YET`, `CLAIMED`), `IN`, a bar of how far into its 6 months it is with its points (or pays, txs, tasks) and today's gain under it, `earned so far` big and green, a green `Harvest 2.2 LIT` when claimable, a quiet `Stop`. Stop claims what is claimable, unwinds the farm and returns the USDC to the balance.
- A claim floats `+$6` up from the button.

---

## 4. The numbers

All of it is in `farm-core.js`; the views never compute a figure of their own.

- **Estimate** (per farm, over 6 months), always a range, never one number:
  `est. airdrop = points per week x weeks x the user's share of all points x the points pool x the token value at launch (FDV range)`, plus what the farm pays out on the way (Polymarket's daily LP rewards). A bigger wallet gets less per dollar (most airdrops flatten whales). The test version models it as `lo/hi x (amount / reference amount)^0.7`, with each farm's low and high at its reference amount. `no estimate` when a farm publishes no points rate or pool.
- **Best split** of an amount `B`: start every farm with a first ticket of 5% of `B`, then add `B/500` (at least $10) at a time, always to the farm where the next dollar earns most **net of costs** (fees and funding per $1,000) and of $5 gas to enter a farm; at most 20% of `B` in one farm; stop when no farm earns more than $0.05 per dollar; none for a farm without an estimate. Free farms are always on.
- **Rank:** estimated farms by estimate per dollar at their reference amount minus cost per dollar, then free farms, then speculative ones.
- **Live:** each farm earns its 6-month estimate evenly over 180 days from the day it started. A weekly payer (Lighter) pays its estimate out week by week as tokens to claim; a daily payer (Polymarket) accrues claimable rewards every day (claimable from 1 unit); a farm whose token launches turns `CLAIMABLE` with what it earned; a capped farm stops earning at its cap.

---

## 5. Look

- **Colours: the site palette only.** Background `#0a0e17`, deep `#06090f`, panel `#0d1520`, line `#1e3050`, text `#e6edf7`, muted `#a9b8cc`, dim `#7f93ad`; cyan `#00cfff`, green `#00ff88`, red `#ff4444` (Stop on hover, a warning dot in the activity line), blue `#3b82f6` (the USDC pill). No other colour anywhere.
- **Type:** Archivo Black for every big number, name and heading; JetBrains Mono for text and labels; Inter for buttons.
- Behind the top of the page a faint lattice of plots (the field's own diamond, 7% opacity, fading out) and two soft glows. Panels: dark glass, 20 px radius, a thin border; green glow border only on the plan panel, the earned panel and the confirmation.
- **One button per tab:** START FARMING, HARVEST.
- Up to 1100 px wide the hero stacks (amount above the field) and the columns narrow; nothing scrolls sideways.

---

## 6. Data, wallet, money

- **The list is live and complete:** every protocol without a token that runs a points program or has said a token is coming (DefiLlama's list of protocols without a token, and each project's own points page), plus testnets and task farms, each with its rules read from its own page. Logos from the protocol's own icon (the test version uses DefiLlama's icon CDN). A farm that ends or launches its token leaves the list within a day; for users in it, it turns CLAIMABLE.
- **One wallet, the user's own USDC:** never more wallets per user, never activity for its own sake, never wash trades or self-trades, nothing a farm's own terms forbid; a farm whose terms exclude automated participation is not listed. Trading farms are farmed hedged where possible (a long on one venue against a short on another). Projects cancel sybil farms; this keeps the airdrops.
- **Money:** farming moves real USDC into outside protocols, so it is for the human-reviewed slot; until it passes, Start farming runs the plan on paper, marked PAPER.
- **Agents:** llms.txt, the agent card, MCP and /api-docs list the farms with their estimates for an amount, a plan the owner approves with one link, the live farms.

---

## 7. The code

| File | What it holds |
|---|---|
| `mock.html` | the page: styles, SVG gradients and the logo symbol |
| `farm-core.js` | the farms (test data), the maths (§4), the state, the plan, start, harvest, stop, the 6-month clock |
| `farm-ui.js` | the views: header, the field, the list, the confirmation, Live farms, all controls |
| `render.py` | renders the pictures (Playwright) |

`mock.html?shot=1&tab=farms|live|logo` shows the frozen states of the pictures (`&modal=1` the confirmation); Live farms there is the Farms plan run for 23 days by the same code, so the pictures agree by construction. Without `shot` everything works on test data kept in the browser, with a test bar at the top right (1 day = 4 s / 1 s / pause, Reset).

## Done when
- [ ] Header, plan panel and field as drawn; typing an amount fills the best split and redraws the field; any farm takes any amount up to the balance.
- [ ] Every listed farm is one row with exactly rank, logo, chip, slider with BEST notch, field, estimate, toggle; slider, field, plan panel and field always agree; no estimate is one number or made up.
- [ ] The list matches the live points programs; Start runs every farm on (on paper until review) from one wallet after one confirmation; no bridge-and-swap loops.
- [ ] Live farms shows the earned panel with HARVEST, the growing field, the 6-month chart and a row per farm; Harvest, Stop, Stop all work.
- [ ] Both tabs look like the pictures at 1440 and 1920 px; nothing overlaps at any amount.
