# ET-34608 (Agent Casino v9): verification

Shipped 2026-11-10 07:55 UTC ("Live: /agent-casino"), 11 h 40 min past its deadline (BB-LATE 2026-11-09). Read 2026-11-10 08:05-08:30 UTC from the live lobby at 1440 px and 390 px (full-page shots), table 100 (finished 7 Nov), `/rules`, `/lobby`, `/lobby?mode=live`, `/llms.txt`. The browser pane is signed out, so Your agents, a running table and the ask were not seen; no table of ours is running (casino.py tick: 0 running).

| Done when | Result | Evidence |
|---|---|---|
| 1 live tables at $1 | FAIL | `/lobby?mode=live` still `not_open`, tables []; `/rules` `modes.live = not_open`, `not_done` "live USDC tables are not open". Their `coming` list has l1h and l5h at $1, but l1d at $5, not $1. Goal 1 went to the human slot (C1): not shipped |
| 2-4 running tables drawn, heads, H, YOU, PRIZE | NOT SEEN | "No table is running right now" on the lobby; the open cards are drawn as an oval with stopwatch, OPEN and 1ST/2ND boxes (the look is there). A one-member PRIZE box exists on the finished table 100 ("buy-in back $50") |
| 5 IDLE red | NOT SEEN in colour | table 100 shows "IDLE 4 H" on our row; colour and the lobby ring not checked |
| 6-7 Open as one large table with switches, arrows, rail; Finished folded | FAIL | Open is a grid of 12 equal cards under 1H/5H/1D headings, no "Table 1 of N", no arrows, no rail. The hero "Next to fill" is one large table with TAKE A SEAT, no switches. "Finished tables 28" is a heading with an empty body, no one-line summary |
| 8 Your agents | NOT SEEN | signed out |
| 9-10 table page | FAIL in part | 1,516 / 1,503 ELO still on every standings row (goal 10: no ELO); no Your bot panel seen (PASS); header not compared against picture 5 |
| 11 ET10 top 2 | FAIL | lobby "Extra for the top 3."; `/rules` `et10_prizes` "top three ... 600 / 300 / 100"; `et10_per_table` 141 / 1000, `et10_prizes` [85, 42, 14] |
| 12 no 20/day cap | FAIL | `/rules` `daily_entries`: "20 per UTC day for every current strategy"; table 100 log: "the daily allowance of 20 trades leaves 16 more trades" |
| 13-14 coach and volume | NOT SEEN on a new table | table 100's log names the volume still needed ("$97.15 still to trade"), but that sentence is older than the ship (#316 is the open bug) |
| 15-16 changelog, ask | NOT SEEN | signed out |
| looks like the pictures | PARTLY | the cards match picture 2's open cards; Open and Finished do not match picture 3 |

**Score: 1 look change in, 5 fail (1, 6-7, 10 in part, 11, 12), the rest not seen.** What I would say: **fail**: live tables, ET10 for the top 2 and the 20/day cap are untouched, Open and Finished are not what picture 3 draws, ELO is still on the table page. The verdict is the operator's.

Not filed as bugs: an unbuilt goal is the verdict's business, not a defect.
