# Build a Company, round 5 (draft, not filed)

Started 2026-10-28 at the operator's word. Two items so far; more are added here as they are agreed. The operator files the
request text himself on Build it Better, and its ET number goes in README.md. Not written yet: the request text, the pictures.

## A. The company works while work is queued (not built, said by them)

**What we have:** on 2026-10-23 Cymetica confirmed (a2a reply to MSG-0219) that the company runner ticks every 120 seconds
(`pass_every_s 120`) and that between ticks it waits even when a department has work queued and the plan has units left. They
called "working while queued instead of waiting for the next pass" **not built**, and said the way to move it up is a feature
request with an ET10 bid. That is this item.

**What we ask:** while a department has a queued task and the owner's plan has units left, the next turn starts at once, not at the
next 120-second tick. How the runner schedules itself is theirs to decide; the owner-visible result is binding:
- done when a task queued while units remain starts within seconds (we measure it from `/tasks` and `/mine`: queued_at to the first turn);
- an empty queue costs nothing (no turns spent looking for work);
- the countdown chip to the next pass (round 4, item E) disappears or changes meaning when passes stop being the rule: Cymetica decides, the
  mockup draws only what stays true.

**Asked separately, same complaint (MSG-0280, 2026-10-28):** the Max 5x window emptied in 23 minutes (11 turns, 4.94 of 5 units) and chat
turns to Command cost like department turns. That is a question to them, not part of this item; a plan decision is theirs.

## B. The leaderboard becomes Season 0: points, a month, a threshold (their build spec, ET-33050)

**What we have:** their answer of 2026-10-28 (REPLY-0233) to our monthly-points proposal (MSG-0276), recorded by them as the build
spec under **ET-33050**; they will post the ticket when it ships. So this is already being built; this item is our notes for the check
and for the guide at `cymetica.com/quest` (outbox/quest), not a new request. Their rules, as they wrote them:

| | Rule |
|---|---|
| Words | "points", a "season" = one calendar month (Season 1 = November 2026), "users", "active user". No invented words. |
| Threshold | 100 points in the month to be placed on the board |
| A user | a signed-in account that used a company's product on 2 different days in the month = 1 active user. A use is the product's own completed action (a screener run, a chart analysed, a casino seat taken or table watched for 1+ minute, a brief posted, a bot cloned), not a page view |
| Points per user | 10 for an active user, +1 per further active day in the month, at most 20 per user per month |
| Signed-out visitors | returning visitors only (same IP hash on 2 different days), only for products that work signed out; 1 point each, in total at most 25 % of the company's signed-in points |
| Trading agents | 1 point per 100 USDC of fee-paying traded volume on the company's agents in the month, at most 30 % of the company's points; nothing for profit or ROI |
| Against farming | the owner's own accounts and test accounts earn nothing; one account is an active user of at most 5 companies a month; accounts created in the month need a verified deposit or 7 days of age; the board shows the breakdown users / visitors / agents |

**The operator's decisions, 2026-10-29 (his words; they change Cymetica's wording, so they are for him to put to Cymetica, not yet sent):**
1. The further days count **from the 3rd active day**: 2 days = 10 points, 3 days = 11, 12 days = 20.
2. **No cap on the trading agents' points**: a company that only trades collects points too (their rule as written gave it 0).
3. **Every product counts separately** for a user: 10 points for each product the user uses. (The 20 cap is read per user per product; he did not say.)
4. **A signed-out visitor who keeps coming back keeps earning**, as an active user does: 1 point, then **+0.25 for every further day from the
   3rd** (a user gets +1). Their rule as written gave a visitor 1 point once. The 25 % cap on the visitors' total stays.
5. **The prize we propose: 500,000 / 250,000 / 100,000 ET10 for 1st / 2nd / 3rd** (their sample was 50,000 / 30,000 / 10,000). At the ET10 price
   of 2026-10-29 (0.001144 USDC) that is about 572 / 286 / 114 USD, 972 USD in all. The size is Cymetica's operator's to set, by 31 October.
6. **We would really like the prizes to stay at 500k / 250k / 100k**: if the points rules look too generous to them, tighten the conditions
   (the thresholds, the caps, the anti-farming rules) rather than take from the prizes.
7. **Which agent is a company's agent** (the operator, 2026-10-29): a company is tied to a Cymetica account, so every agent cloned under that
   account is that company's agent, and its fee-paying volume counts for the company. Not stated by them; an account that owns several
   companies would count the same agent for each.
The Universe mock (`?season0`) draws these; the sample figures come from one model (uv-data.js, `CO.uvPoints`).

**What their answer does not say (to settle before we check the build):**
1. **The prize.** The answer names a winner above a threshold but no prize. Earlier (REPLY-0229): ET10 only, the 5 : 3 : 1 split, a
   pool in the 50,000 / 30,000 / 10,000 range, a USDC prize is a treasury decision they cannot promise. Is that still the Season 1 prize,
   how many places are paid, and when (half at the month end, half after 60 days?).
2. **Paid places versus "the winner".** The guide and the board say the top 3 take a slot; the answer says "monthly winner". How many places?
3. **Is it per company or per product?** Points are the company's; a user of three of its products counts once (one user, 10 points)? Not stated.
4. **When the counting runs and what the board shows in between:** live running totals per company for the month, a cut-off hour, the
   day the season closes (UTC)? The Season 1 board in November must show whose points are rising.
5. **Where a company reads its own breakdown** (users / visitors / agents) and the API for it; and that the board's three figures and
   the quest page's say the same thing (one source).
6. **The revenue share:** when the real 5 % / 3 % / 1 % replaces the pool (at a revenue level, REPLY-0229), and whether Season points stop then.

**Our checks when it ships (ET-33050):** the board shows points, the breakdown and the threshold; a company with 10 active users on 2 days
reaches 100; a page view alone gives nothing; the owner's own account gives nothing; a signed-out visitor counts at most 25 % in total; agents'
volume counts at most 30 %; one account counts for at most 5 companies.

**For the guide (outbox/quest):** the prize line and step 4 change from "up to 5 % of revenue" to Season points once the prize is settled
(item 1). The draft Build it Better request `outbox/quest/season0/request.txt` is superseded by ET-33050 and is not filed.
