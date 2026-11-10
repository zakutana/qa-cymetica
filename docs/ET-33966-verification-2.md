# ET-33966, second build (the change of 4 Nov), checked 10 Nov 2026

Verdict: PASS with notes (BB-0056), on the operator's word. The 4-coin replay is a note, not a condition: a setup need not hold on all 12 coins (a short bot for a falling market may fit two).

Script v=6af2ba30, shipped 10 Nov 06:36 UTC (deadline was 5 Nov). Search #22, started by us at 06:55 UTC on company 14, done 07:02: searched on ATOM, BNB, DOGE, DOT; 896 combinations new, 80 shortlisted, 0 passed. Page looked at signed in, 1235 px wide.

| # | Done when | Result |
|---|---|---|
| 1 | No passed setup counts a window overlapping the search period it was chosen from | PASS. Every row carries `windows_seen` and `chosen_from_window`; no seen window is marked as made money; a setup chosen on the 3rd or 4th window has 1 or 2 unseen windows and reads "too few windows" (46 of 80) |
| 2 | A window under 5 trades never reads as made money | PASS. `min_window_trades` 5; 0 unseen windows under 5 trades marked as made money |
| 3 | Raw and effective tries shown; the bar uses the effective one | PASS. 49,920 raw, 6,544 effective (12 markets count as 1.57); the bar's z is 4.32, which is the z for 6,544, not for 49,920 (4.75); RUNS shows "tries 49,920 → 6,544" |
| 4 | A finalist's row shows its result on all 12 coins | FAIL. The search ran on 4 coins as asked, but the page says "finalists replayed on all 4 coins": the replay stops at the 4 search coins, not all 12. With no finalist, `by_coin` is empty on every row |
| 5 | One model on one coin is one agent | Not seen: no setup passed, `merged_into` / `same_agent_as` empty |
| 6-8 | Page under 3,500 px with 94 shortlisted, first winner within 2 screens | PASS. 2,203 px with 80 shortlisted; WINNERS, BOTS, RUNS in that order; RUNS 40 px a line, 5 shown; thrown-out rows closed |
| 9-10 | No overlap in BLIND or THE BAR; none of the old labels | PASS for BLIND (four windows) and THE BAR (10 bars, readable). But BUILD still reads "16 RULES · NO SKILLS · NO COMBOS" and BLAST still draws 16 rules on 12 coins, while #22 searched 26 candidates on 4 coins |
| 11 | FOUND shows all winners; no bot starts without Approve; a queued bot never reads LIVE | Not seen: no winner. The three bots started from #19 before the change still read "PAPER · RUNNING 0.00%" with 0 trades in 6 days, and their instances are not in the owner's bots (`my_bots`) or at `/cloned-bots/{id}/profile` (404). FOUND's "NO PROFITABLE AGENT" runs off the right edge at 1235 px |
| 12 | No idea card waits for a problem the latest search no longer has | PASS as far as seen: no approvals are pending |
