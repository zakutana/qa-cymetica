# ET-31459 Agent Tournaments control panel: verification

Read 2026-10-15 18:10-18:30 UTC, after Nexus's Telegram message "ET-31459 Agent Tournaments update is live". The ticket itself still read `stage: building` (`bb.py get ET-31459`, 18:15 UTC); Nexus called it shipped later the same evening. Reads only, our X-API-Key: `/lobby`, `/rules`, `/my-bots`, `/tables/{1,2,5,11..17}`, `/tables/{id}/changes`, `/seats/{29,33,57,58}`, `/seats/{id}/bot-settings`, `/openapi-public.json`, MCP `tools/list`, llms.txt; the lobby at 1920 and 1440 and tables 5 and 13 at 1920 in the built-in browser (not signed in, so a visitor's view). Phone width is out of scope. The spec is `outbox/tournaments-control/request.md` (15 lines, 10 "Done when").

We hold two seats: 29 at table 5 ("tournament Perceptron Oracle") and 57 at table 13 ("lab Wave 2 Fibonacci Phoenix"); their bot-settings answer our key 200.

| Done when | Result |
|---|---|
| 1 Headline and kinds strip true; six boxes gone | PASS: "10 agents. 1 table. Best ROI wins."; one strip Week 7 days $5-$30 / $50-$300, Flash 1 day the same, ET10 7 days 100-600 / 1,000-6,000 ET10; "top 3 split the pot 60 / 30 / 10, plus 1,000 ET10 on every USDC table (600 / 300 / 100; 85 / 42 / 14 on Flash)" |
| 2 Live and open tables apart, filters drive both | PASS: "Live now 4" (13, 11, 5, 2 with pot, time left, leader and ROI) and "Open, starts when full 6"; each filter tried: ET10 leaves #16 and #15, Flash leaves #13, #17, #14, $50 leaves #11, #5, #2, #12, across both sections |
| 3 Nothing past a card's edge at 1440 and 1920 | PASS: 11 cards measured at each width, 0 px past either edge (was 44-77 px at 1440) |
| 4 ET10 priced in ET10 everywhere | PASS: ET10 1K #16 reads "1,000 ET10", pot "0 ET10"; the API now carries `buyin_et10` 1000 with `buyin_usdc` null on ET10 tables (MSG-0166 item 1) |
| 5 Owner switches lanes and SL/TP at the table; the bot then trades the lanes switched on | NOT CHECKED: the panel needs a signed-in owner, and a change is a write. The API twin is there: `GET /seats/57/bot-settings` returns lanes (perpetual on, BTC ETH VAIX SBIO ET10 ETLP CYM42 TBIG TBIGS; clob off; event cards off; arena on; catalog off), stop loss 10 %, take profit 20 %, ranges 1-20 / 5-100, fixed limits (10 % position, 5 open, 2x, 20 a day), `can_change: true` |
| 9 Forward-only, unlimited, a public row each; house bots fixed | PART: the rules text says so in those words; `/tables/{id}/changes` and `changes` in `/tables/{id}` exist and are empty on every table (no change made yet, so no row to see); a house seat's bot-settings answers 403 `house_bot`; another owner's seat answers 403 `not_your_seat` |
| 10 Your bot updates without a reload | NOT CHECKED: owner-only, needs a signed-in pane |
| 13 Picks closed: no radios; open: a pick can be placed; no doubled name | PASS: table 5 "PICKS CLOSED 10/13 18:49 UTC", $50 pool, picks per bot, 0 radios, no PICK; table 13 open: 10 radios, chips 10 / 50 / 100, "+$10 if House Trend Titan wins", PICK; no "House X House" anywhere |
| 15 Same changes through API and MCP; the log in /tables/{id} | PASS on presence: `GET/POST /seats/{seat_id}/bot-settings` and `GET /tables/{table_id}/changes` in the OpenAPI; MCP `agent_tournament_bot_settings`, `agent_tournament_change_bot` (lanes, stop_loss_pct 1-20, take_profit_pct 5-100), `agent_tournament_table` with `changes`. Not exercised (a write) |
| The page keeps today's look | PASS: oval table, avatars, site colours; the visitor's room at 1920 is table and leaderboard left, the race centre, changes and "If it ended now" right, as the mockup's visitor case |

Also read: the rules strip is one row of seven (buy-in, capital, min volume, payout, ET10, leverage, ranked by); the leaderboard marks house bots with H and cuts no name to two letters. Table 5's "If it ended now" ($80 to the first member, $20 to PaperX) is the rules working, not a defect: PaperX is short of the $750 volume, so places 2 and 3 ($40) go back to the two members in equal parts.

**Defect, filed as a report:** the table does not know its owner. With our key, `/tables/5` and `/tables/13` read `my_seat: null` and `mine: false` on seats 29 and 57, and `/lobby` reads `my_seat: null` on all ten tables and `my_agents: null`, while the same key's `/seats/{id}/bot-settings` ("Owner only") answers 200 for exactly those seats. Check: `tests/rest/test_agent_tournaments_table_knows_its_owner.py`.

**Documentation gap:** the llms.txt Agent Tournaments entry still names four MCP tools and none of ET-31459's routes (`/seats/{id}/bot-settings`, `/tables/{id}/changes`, `agent_tournament_bot_settings`, `agent_tournament_change_bot`, `agent_tournament_table`); the OpenAPI has them.

Verdict: the operator's.
