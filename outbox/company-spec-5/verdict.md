# Build a Company, round 5: what is live (read 2026-11-01 07:55 to 08:20 UTC)

Read in the operator's signed-in browser pane on company 14 (Ironstar Capital), nothing changed, nothing created (the Create company wizard was opened
and left at its first step). The build is most likely ET-33496 (the Products API names it as Build a Company's latest build, submitted 2026-10-30 20:16 UTC);
the ET number of the round-5 request itself is not written down yet.

| Item | Asked | Live |
|---|---|---|
| B1 further days from the 3rd | 10 / 11 / .. / 20 | **yes**: `/season-breakdown` rules: "2 active days = 10 points, +1 for each further day from the 3rd, up to 20 per user per product" |
| B2 no cap on agents | none | **yes**: "1 point per 100 USDC of fee-paying volume, no cap" |
| B3 every product counts, no 5-company limit | every product separately | **yes**: "Every product counts separately"; the rules list no 5-company limit |
| B4 returning visitor +0.25 | 1, +0.25 from day 3, 25 % cap | **yes**, word for word, "same browser on 2+ days" |
| B5 an account's agents are the company's | | **yes**: "Fee-paying volume of your account's agents (clones included), shared by the whole company" |
| B6 prizes 500k / 250k / 100k | keep | **no**: `prizes_et10` is 50,000 / 30,000 / 10,000 (their own sample) |
| B7 land 5 per account | 5 | **yes**: `/company/land` `max_per_account` 5 (was 3) |
| B8 Products shows what each product brings | active users, visitors, points | **yes**: each tile "season points"; the side panel active users, returning visitors, points from users, points from visitors, agent volume |
| B9 product list | no Build Usage, no Build it Better, Agent Casino once | **yes**: 10 products, all built through Build it Better, Agent Casino once |
| B10 Season 1 in November, counted back | | season starts 2026-11-01, `window.from` is 2026-09-20; **every product is at 0 points** (8 h into the season; 246 people on Gem Screener over 30 d): a back-count cannot be told from "nobody was active 2 days yet" |
| Season 1 board in the Universe | the picture: top 3 with points | **no**: the Universe board and its full leaderboard are still REVENUE SHARE (5 / 3 / 1 %, "not measured yet"); `uvboard.js` has no "season" in it. The data is only in `GET /api/v1/company/season` |
| 100-point threshold | to be placed | not seen: that API hands `prize_et10` 50,000 / 30,000 / 10,000 to companies with 1.011, 0.0202 and 0.0001 points |
| C free company creation | registration only | **no**: `/company` still says "Creating a company takes the Pro plan or higher and a one-time ET10 fee" |
| A the runner works while work is queued | | not checkable: the company is paused |
| B11 anti-farming | stronger | not tested (needs a new run of the proxy bot) |

Recommended verdict: **Fail**. **The main defect (the operator, 2026-11-01): the board was not changed.** Season 1 is running (`/api/v1/company/season`: season 2026-11,
prizes, a ranking) while the Universe board and its leaderboard, the centre of the request (pictures 1 and 2), still say REVENUE SHARE, "not measured yet, so
nobody is ranked and nothing is paid". The page and the API contradict each other. Besides: prizes were not changed and company creation is not free; what is
live is the rules in the API and the Products tab.
