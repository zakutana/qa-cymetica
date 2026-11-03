# ET-33342 (Build a Company, round 5): verification

Shipped again 2026-11-03 01:12 UTC after our Fail of 2026-11-01. Read on 2026-11-03 ~04:10 UTC from `GET /api/v1/company/season` and `/company/app#universe`, signed in as the owner of company 14. Their reply (REPLY-0244, from Nexus) is data: every line below is what the page and the API say, not what it says.

| Item | Result | Evidence |
|---|---|---|
| Our Fail 1: the board is the API's | PASS | Universe board and Full leaderboard read the six rows of `/season`; no "revenue share", "5 %", "not measured yet" left anywhere on the page |
| Pictures 1-2: board with top 3 and prizes, full leaderboard | PASS | SEASON 1 · TOP 3, November 2026, 28 d left, 100 pts to qualify; leaderboard: podium, WHAT COUNTS, Who gets a place, every company with users, visitors, agents and total |
| Our Fail 4: no prize below 100 points | PASS | `qualify_points` 100; top company has 10.0001; all six `qualifies` false, `prize_et10` 0; the page says "All 3 places are open" |
| Test companies not ranked | PASS | six rows, no QA Stranger Co |
| B1-B5 points rules | PASS (1 Nov) | `what_counts` on the API: user 10 +1 from day 3 max 20, visitor 1 +0.25 max 25 %, agents 1 per 100 USDC no cap |
| B7 land 5 per account, B8-B9 Products tab | PASS (1 Nov) | as in the 1 Nov verdict; the tab still lists 11 products with points each |
| B6 prizes 500k / 250k / 100k | NOT BUILT | still 50,000 / 30,000 / 10,000; they call it Cymetica's setting, on the ticket for a decision |
| C free company creation | NOT BUILT | /company still says "Pro plan or higher and a one-time ET10 fee"; they say the switch exists and is off |
| B10 points back from before the season | EXPLAINED | they say per-person days were recorded only from 1 Nov, so earlier days cannot count; the API says so |
| B11 anti-farming | NOT ANSWERED | their reply does not mention it; needs our own run |
| A work without waiting | OPEN | company 14 is paused (`status: paused`), nothing can be queued |
