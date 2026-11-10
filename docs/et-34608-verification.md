# ET-34608 (Agent Casino v9): verification

Shipped 2026-11-10 07:55 UTC ("Live: /agent-casino"), 11 h 40 min past its deadline (BB-LATE 2026-11-09). Read 2026-11-10 08:05-08:25 UTC: `/rules`, `/lobby`, `/lobby?mode=live`, `/llms.txt`; the lobby at 1440 px and 390 px signed out (full-page shots) and signed in; the approve page; table 100 (finished 7 Nov); and two paper tables we started for this: #105 (MACD Hunter, coach off) and #106 (RSI Sniper, Risk 10), both Flash Micro 1D, running, ending Wed 11 Nov 08:11 UTC. A third request (#107) was left unapproved.

| Done when | Result | Evidence |
|---|---|---|
| 1 live tables at $1 | FAIL | `/lobby?mode=live` still `not_open`, tables []; `/rules` `modes.live = not_open`. Their `coming` list has l1h and l5h at $1, but l1d at $5. Goal 1 went to the human slot (C1): not shipped |
| 2-4 running tables drawn, prize box | PASS in part | Live now cards are drawn tables: six heads, buy-in on the felt, 1D stopwatch, LIVE, d/h/m/s pill with a bar, YOU label on our bot, one PRIZE box "your buy-in back + 85 ET10", foot "YOU casino RSI Sniper #1 . +0.00%". Same at 390 px (matches picture 6). **House heads are not grey with an H**: the CSS class `house` desaturates but tints them blue, and no H badge is drawn on the lobby cards (the table page has an H next to the name) |
| 5 IDLE red | NOT SEEN | no bot of ours is idle yet (tables started minutes ago); table 100 shows "IDLE 4 H" |
| 6-7 Open as one large table with switches, arrows, rail; Finished folded | FAIL | Open is a grid of 12 equal cards under 1H/5H/1D headings, still under their old filter row (All, $5, $50, Flash, 1H, 5H, 1D, ET10, Mine), not our switches (how long, buy-in, paper or live) beside one large table; no "Table 1 of N", no arrows, no rail (the operator, 2026-11-10: "porad ten stary filtr"). The hero "Next to fill" is one large table with TAKE A SEAT, no switches. Signed out, "Finished tables 28" has an empty body, no one-line summary; signed in, not re-checked |
| 8 Your agents | FAIL | There is **no Your agents tab**: the header still reads Lobby, Leaderboard, How it works (the operator's screenshot, 2026-11-10). The section exists only as a block reached by `/agent-casino#agents`, which I opened by URL. It has rows with IDLE-less tag, buy-in, rank, ROI, red "needs $10.71 more volume to qualify", ENDED rows. **The time left is a line of text under the table name ("LIVE . 24H LEFT"), not a column with the cards' pill and bar, and no length icon** |
| 9 table page layout | PASS | no "Your bot" panel; header has back arrow, $5 #106, 1D stopwatch, LIVE, "6/6 seats . $0 traded" and the pill; larger table with names beside heads, no overlap at 1440 px |
| 10 ELO, Not trading | FAIL | "1,500 ELO" on every standings row, and "NO TRADES" tags on every house row |
| 11 ET10 top 2 | FAIL | lobby "Extra for the top 3."; `/rules` `et10_prizes` "top three ... 600 / 300 / 100", 141 per table |
| 12 no 20/day cap | FAIL | `/rules` `daily_entries`: "20 per UTC day for every current strategy"; approve page "20 trades left today of 20"; standings "0/20 today" |
| 13-14 coach volume, own pause | NOT SEEN | table 105/106 coach has not acted yet ("has not changed anything yet"); table 100's older log already named the volume still needed (#316 open) |
| 15 Changelog owner changes only, tag once | NOT SEEN | no tune yet |
| 16 ask warns under one trade | PASS | approve page: "about 0 trades over this 1 day table; this bot will likely not trade at this table", no length recommended |
| looks like the pictures | PARTLY | running cards match pictures 2 and 6; Open and Finished do not match picture 3. On a phone the "Approve all . total max loss $30" button text overlaps itself |

**Score: 3 pass or pass in part (2-4, 9, 16), 6 fail (1, 6-7, 8, 10, 11, 12), 4 not seen yet (5, 13-14, 15).** What the shipped look is, in one line: the cards' oval table, stopwatch and prize boxes, the robot heads on running tables, the table page without its Your bot panel; the structure (Your agents tab, Open as one table with our switches, Finished folded) is not built. What I would say: **fail**: live tables, ET10 for the top 2 and the 20/day cap are untouched, Open, Finished and the Your agents tab are not what the pictures draw, house heads are not grey with an H, ELO is still on the table page. The verdict is the operator's.

**To finish:** read tables 105 and 106 once they have traded and when they end (Wed 11 Nov 08:11 UTC): IDLE red, the coach's volume line, the Changelog, "PAUSED" once. Not filed as bugs: an unbuilt goal is the verdict's business.

## Second read: new build, 2026-11-10 12:30-13:00 UTC

After our FAIL (BB-0059, resolved 12:20 UTC) the page changed (HTML 470 KB to 489 KB, a Your agents link in the header, `/agent-casino/agents` is now a page). `/rules` is byte-identical to the first read; `/lobby?mode=live` still `not_open`. Read signed in on tables 105, 106, 107 and at 1440 / 390 px.

| Done when | First read | Now | Evidence |
|---|---|---|---|
| 1 live tables | FAIL | FAIL | `?mode=live` not_open, tables [] |
| 2-4 drawn tables, house heads, prize | PASS in part | PASS | house heads grey with an H badge, YOU ring, one PRIZE "your buy-in back + 85 ET10", pill and bar; 390 px the same |
| 5 IDLE red | NOT SEEN | PASS in part | red `#ff4444` IDLE on the lobby card and "IDLE 3 H" in Your agents; table page IDLE line not seen (no idle bot there) |
| 6-7 Open, Finished | FAIL | PASS | one large table, switches (how long, buy-in, paper/live), "Table 1 of 2" arrows, TAKE A SEAT, rail of small tables, + Create a table right of the heading; Finished folded under "26, 10 won by your agents, net $0, +850 ET10"; rows say HOUSE $0, $50 refund, $50 won +85 ET10 |
| 8 Your agents | FAIL | PASS | header tab, `/agent-casino/agents`: time-left column, ENDED rows, rank, ROI, TO QUALIFY, WAITING row |
| 9-10 table page | PASS / FAIL | PASS | no Your bot panel, header with pill, names beside heads, no ELO, no Not trading on house rows (ours shows it at 20/20) |
| 11 ET10 top 2 | FAIL | FAIL | lobby still "Extra for the top 3."; pot line +141 ET10 (85 + 42 + 14), `/rules` `et10_prizes` still top three 600/300/100; only the 1ST/2ND boxes changed |
| 12 20/day | FAIL | FAIL | cap stays: `/rules` 20 per UTC day, approve page "20 trades left today of 20", table 106 "20/20 today, resumes 00:00 UTC". Our RSI Sniper made its 20 and then sits "NOT TRADING" with 19 h left |
| 13-14, 15 | NOT SEEN | NOT SEEN | tables 105/106 end 11 Nov 08:11 UTC |
| 16 ask warns | PASS | PASS | approve/551: "Under one trade is expected over this table: this bot will likely not trade at this table" |

**Score now: 7 pass or pass in part (2-4, 5, 6-7, 8, 9-10, 16), 3 fail (1, 11, 12), 3 not seen (13-14, 15).** Our FAIL went out on the first read; the structure (Your agents tab, Open as one table, Finished folded, grey house heads) was shipped after it. Not re-checked: the phone "Approve all" text overlap.

## Third read: build of 2026-11-10 13:58 UTC (BB-SHIPPED), read 14:00-14:15 UTC

`/rules` changed: `et10_prizes` is "top 2 ... 85 / 42 = 127 ET10 at a 1-day table"; `daily_entries` is "No daily trade cap at a table: a paper bot seated at an Agent Casino table can open new trades for the whole table". `/lobby?mode=live` is still `not_open`, tables [].

| Done when | Now | Evidence |
|---|---|---|
| 1 live tables | FAIL | `?mode=live` not_open, tables [] (human slot) |
| 11 ET10 top 2 | PASS | lobby "Extra for the top 2", no "+141" or 14 ET10 left on the lobby, rules 85 / 42 = 127 |
| 12 no cap | PASS | rules say no daily cap at a table; table 106 seats at 22, 21 and 20 trades, no "20/20 today" line |
| rest | as in the second read | 2-4, 5 (in part), 6-7, 8, 9-10, 16 pass; 13-14, 15 not seen |

**New defect from this build:** the approve page (`/agent-casino/approve/551`) now reads "trades left today of , resets 00:00 UTC", the numbers gone from the sentence the cap used to fill. The Your agents icons are still the old round ones.

**Score now: 8 pass or pass in part, 1 fail (1), 2 not seen (13-14, 15).**

**Old icons (the operator's screenshots, 2026-11-10):** the new robot heads are on the lobby cards, but Your agents rows, the Your agents card header and the Leaderboard still show the old round species icons. Picture 4 draws the robot head on every Your agents row, so row 8 matches the pictures only in its columns, not in its icons. The Leaderboard is in no goal or picture. Not in the second verdict.
