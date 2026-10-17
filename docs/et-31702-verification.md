# ET-31702 Agent Tournaments v3: verification

Read 2026-10-17 ~00:30 UTC, after Nexus's Telegram message "ET-31702 is built and live, all 13 items" (REPLY-0181). Spec: `outbox/tournaments-v3/request.md` (13 lines, 9 "Done when"). Reads only: our X-API-Key on `/leaderboard` (window all / 7d, mine), `/lobby`, `/tables/5`, `/tables/13`, `/seats/29/nexus-lock` (GET), `/openapi-public.json`, MCP `tools/list`, `/llms.txt`; a signed-out browser at 1440 x 900 and 1920 x 1080 on the lobby, `/agent-tournaments/leaderboard`, `/table/5`, `/table/2`, `/table/14`, `/table/13/results`, with every page scrolled through first and an overlap scan over the text boxes actually painted. Nothing was created, locked or picked.

| # | Line | Read |
|---|---|---|
| 1 | Lobby strip: three tiles, nothing else changes | PASS: HOW LONG (Week 7 days, Flash 1 day chips), THE POT 60 / 30 / 10, ON TOP + ET10; no prices; chip, headline, PICK A TABLE and the line under it as before |
| 2 | Status corner, countdown, DAY n/N, bar; open "starts when full" | PASS: LIVE with d/h/m and DAY 5/7 or 6/7 and a bar; OPEN cards "starts when full · 10 seats left · runs N days" |
| 3 | Pool in the oval, 1st / 2nd / 3rd cells | PASS: e.g. Pro #5 $100 + 1,000 ET10, cells $60 / $30 / $10 + 600 / 300 / 100; open Flash Micro #17 $50 + 141 ET10, 85 / 42 / 14; all 60 / 30 / 10 of the pool |
| 4 | Nothing overlaps at 1440 and 1920 | PART: lobby, leaderboard and table pages 0 text-box overlaps, no sideways scroll at either width. **On the table page the oval's rim crosses the top-centre seat's "1,500 ELO" line** (table 5, tournament Perceptron Oracle, both widths). Your agents (signed-in only): NOT CHECKABLE |
| 5 | Top agents gone | PASS |
| 6 | Leaderboard tab | PASS on content and order: podium, 16 bots / 3 tables live / $5 + 85 ET10 paid, won / wins / avg ROI / tables, ranked by wins then avg ROI (Trend Titan 1 win first, then by ROI 85.00, 50.00, 49.56 ...), house strategy one row; All time / 7 days and All / Mine work (`window`, `mine=true` gives our 3 bots). **One thing the spec left out on purpose is back: a row shows "1,509 ELO"** (lab Wave 2 Fibonacci Phoenix); the operator cut Elo from the leaderboard while drawing it |
| 7 | Create a table: lobby, API, MCP | PASS on presence: "Create a table" beside Open (signed out it goes to login, so form and preview NOT CHECKED); `POST /tables` (CreateTableIn) and MCP `agent_tournament_create_table` (kind week/flash, buy-in 5/50 USDC or 100/1000 ET10, week only for ET10). Their addition: at most two open tables per member |
| 8 | Table top: name, buy-in, kind, LIVE, countdown, 7 rules | PASS: "Pro #5 · $50 · WEEK · LIVE · 2d 14h 29m left · DAY 5/7"; BUY-IN, CAPITAL, MIN VOLUME, PAYOUT, ET10, LEVERAGE, RANKED BY |
| 9 | Big table, standings, race; "If it ended now" gone | PASS: every seat with name and ROI, pool in the middle, cells under it; standings rank / bot / ROI / volume vs min / prize now / pick; the race; no "If it ended now" |
| 10 | Picks in the standings | PASS closed state (tables 5 and 2: one bar "$50 pool · 1 pick · closed", each row its picks and stake); open state NOT SEEN (no live table had picks open) |
| 11 | Owner column only for the owner; visitor full width | PASS for the visitor (main column full width, no "Your bot, live"); owner column NOT CHECKABLE signed out |
| 12 | No venue form on the table page | PASS for the visitor: no link / connect / exchange / wallet; the venue routes stay in the API under `/seats/{id}/venue` |
| 13 | NEXUS tunes it | PASS on presence: `GET/POST /seats/{id}/nexus-lock` (seat 29 reads unlocked, terms "your ET10 stays yours ... comes back when the table ends"), MCP `agent_tournament_nexus_lock`; the owner-column button NOT CHECKABLE |
| | The pages keep today's look | PASS: same oval, avatars, colours and fonts |

Also seen, outside the spec: our bot at table 5 reads "NO CAPITAL · Not trading: no capital" with ROI +50.00% frozen; table 13's results page draws the house "H" badge 10 px over "House Trend Titan".

Verdict: the operator's.

## 2026-10-17 evening: the two follow-ups and the 7-item bug report (REPLY-0184, REPLY-0183)

Read signed out at 1920 and 1440 on /agent-tournaments/table/2 and /leaderboard, and GET /api/v1/agent-tournaments/leaderboard (no-cache, 19:30 UTC). The 7-item report was drafted in another session and sent by the operator; recorded late as MSG-0184. Our answer: MSG-0185, a2a A2A-0109.

| Item | Verdict |
|---|---|
| ET-31702 follow-up 1: no Elo on the leaderboard | PASS: none on the page, `elo: null` in the API |
| ET-31702 follow-up 2: top seat's label off the rim | PASS: its own panel above the rim |
| 1 countdown units | PASS: units 15px beside 30px digits; LEFT · DAY 7/7 at 12px |
| 2 progress bar fills | PASS: an `<i>` at 87% on day 7 of 7 (6 d 2.7 h of 7 d) |
| 3 wins and winnings, one rule | FAIL: House Trend Titan wins 1, won $0 (podium #1); lab Wave 2 Fibonacci Phoenix wins 0, won $5 + 85 ET10; page and API agree |
| 4 wide table | PASS: 1760px at 1920; race chart and change log span it |
| 5 room below the bottom seats | PASS: the bottom seat ends ~70px above the prize cards |
| 6 no ELO on seats | PASS: 0 of 10 seats; ELO only in the standings rows |
| 7 ROI floor -100% | PASS on the text: the ROI definition says it; the lowest seat reads -96.34% |
