# ET-34608 (Agent Casino v9): verification

Shipped 2026-11-10 07:55 UTC ("Live: /agent-casino"), 11 h 40 min past its deadline (BB-LATE 2026-11-09). Read 2026-11-10 08:05-08:25 UTC: `/rules`, `/lobby`, `/lobby?mode=live`, `/llms.txt`; the lobby at 1440 px and 390 px signed out (full-page shots) and signed in; the approve page; table 100 (finished 7 Nov); and two paper tables we started for this: #105 (MACD Hunter, coach off) and #106 (RSI Sniper, Risk 10), both Flash Micro 1D, running, ending Wed 11 Nov 08:11 UTC. A third request (#107) was left unapproved.

| Done when | Result | Evidence |
|---|---|---|
| 1 live tables at $1 | FAIL | `/lobby?mode=live` still `not_open`, tables []; `/rules` `modes.live = not_open`. Their `coming` list has l1h and l5h at $1, but l1d at $5. Goal 1 went to the human slot (C1): not shipped |
| 2-4 running tables drawn, prize box | PASS in part | Live now cards are drawn tables: six heads, buy-in on the felt, 1D stopwatch, LIVE, d/h/m/s pill with a bar, YOU label on our bot, one PRIZE box "your buy-in back + 85 ET10", foot "YOU casino RSI Sniper #1 . +0.00%". Same at 390 px (matches picture 6). **House heads are not grey with an H**: the CSS class `house` desaturates but tints them blue, and no H badge is drawn on the lobby cards (the table page has an H next to the name) |
| 5 IDLE red | NOT SEEN | no bot of ours is idle yet (tables started minutes ago); table 100 shows "IDLE 4 H" |
| 6-7 Open as one large table with switches, arrows, rail; Finished folded | FAIL | Open is a grid of 12 equal cards under 1H/5H/1D headings, no "Table 1 of N", no arrows, no rail. The hero "Next to fill" is one large table with TAKE A SEAT, no switches. Signed out, "Finished tables 28" has an empty body, no one-line summary; signed in, not re-checked |
| 8 Your agents | PASS in part | `/agent-casino#agents` has rows with IDLE-less tag, buy-in, rank, ROI, red "needs $10.71 more volume to qualify", ENDED rows. **The time left is a line of text under the table name ("LIVE . 24H LEFT"), not a column with the cards' pill and bar, and no length icon** |
| 9 table page layout | PASS | no "Your bot" panel; header has back arrow, $5 #106, 1D stopwatch, LIVE, "6/6 seats . $0 traded" and the pill; larger table with names beside heads, no overlap at 1440 px |
| 10 ELO, Not trading | FAIL | "1,500 ELO" on every standings row, and "NO TRADES" tags on every house row |
| 11 ET10 top 2 | FAIL | lobby "Extra for the top 3."; `/rules` `et10_prizes` "top three ... 600 / 300 / 100", 141 per table |
| 12 no 20/day cap | FAIL | `/rules` `daily_entries`: "20 per UTC day for every current strategy"; approve page "20 trades left today of 20"; standings "0/20 today" |
| 13-14 coach volume, own pause | NOT SEEN | table 105/106 coach has not acted yet ("has not changed anything yet"); table 100's older log already named the volume still needed (#316 open) |
| 15 Changelog owner changes only, tag once | NOT SEEN | no tune yet |
| 16 ask warns under one trade | PASS | approve page: "about 0 trades over this 1 day table; this bot will likely not trade at this table", no length recommended |
| looks like the pictures | PARTLY | running cards match pictures 2 and 6; Open and Finished do not match picture 3. On a phone the "Approve all . total max loss $30" button text overlaps itself |

**Score: 6 pass or pass in part (2-4, 8, 9, 16), 5 fail (1, 6-7, 10, 11, 12), 4 not seen yet (5, 13-14, 15).** What I would say: **fail**: live tables, ET10 for the top 2 and the 20/day cap are untouched, Open and Finished are not what picture 3 draws, house heads are not grey with an H, ELO is still on the table page. The verdict is the operator's.

**To finish:** read tables 105 and 106 once they have traded and when they end (Wed 11 Nov 08:11 UTC): IDLE red, the coach's volume line, the Changelog, "PAUSED" once. Not filed as bugs: an unbuilt goal is the verdict's business.
