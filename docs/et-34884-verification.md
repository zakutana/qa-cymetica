# ET-34884 verification (Quant Lab: two questions, bear/bull/all-weather winners, Flash)

Shipped 2026-11-12 12:30 UTC (deadline 2026-11-11 22:01 UTC, BB-LATE 22:23). Read 2026-11-12 13:00-16:00 UTC: the owner
API (`/quant-lab/search`, `/search/results?limit=200`, `/quant-lab`) with our read key, and the page in the operator's
signed-in browser at 1235 px and 390 px. Searches started from the page's own dialog: #23 and #25 long term · low risk,
then Flash 1 h · high risk. Spec: `outbox/quant-lab-profiles/request.txt`.

Search #23 failed at 99.6% after 67 minutes, "database connection lost", no result (the same reason as daily searches #5,
#7 and #9 in October). The same answers again as #25 finished in 58 minutes with 2,744 setups, 55 shortlisted (49 long,
6 short), one winner: StockBot Blue · BNB · SL 3 / TP 15, a bull bot.

| Done when | Result | Evidence |
|---|---|---|
| 1 Two questions only; the run shows both; a low-risk winner has no window below -15% | PASS | The dialog asks horizon (Flash 1 h, Flash 5 h, long term) and risk (low, high) and nothing else; the POST body is those two. Run #25 reads "Long term · Low risk" on the run row and the winners header. Winner's worst unseen window -4.33% (11 Nov 2025), `drawdown_breached false`; recomputed from its 53 windows: min -4.325%. |
| 2 Long and short searched; every window labelled with the coin's move; winner reads a kind | PASS | Shortlist 49 long, 6 short; "searched on AVAX, BNB, BTC, LTC · long and short". All 53 windows of the winner carry `kind` and `market_move_pct`; 0 of 53 disagree with the ±2% band. Card: BULL BOT. |
| 3 Unseen windows of its kind (≥12) with dates, the other kind, none used to choose it | PASS | "16 unseen windows of its kind (needs 12 windows and 20 closed trades), 4 NOV 2025 – 10 NOV 2026 · chosen on 6 MAY 2025 – 4 NOV 2025, none of them among the judged"; `windows_seen 0`. Other kind: "in 2 of 18 falling, mean -1.31%". Recomputed: 16 rising, 14 won, pooled +21.725% on 241 trades; bar 18.00% at 21,909 effective tries = 7,303 × 3. The run says "53 judged weeks after 26 selection weeks" with the weeks per kind per coin. |
| 4 Flash on BTC and ETH, 5-minute bars, direction hit rate, trade result, stop, volume floor | (Flash) | |
| 5 A short winner's Approve starts a paper short bot that trades | NOT SEEN | No short winner (the only winner is long). The vendor says short winners run on a new paper short lane; nothing on the page or in the API shows one. |
| 6 Card: profile, kind, both counts, today's read and how often it held, coins, where it runs; nothing before Approve; no paper 2x as forecast | PASS | Card shows "Long term · Low risk", BULL BOT, "bull bot: made money in 14 of 16 rising windows, mean +1.36%; in 2 of 18 falling, mean -1.31%", "A bull bot is a bet on a rising market…", "BNB today: read range; the next week stayed in a range in 33.3% of such weeks (9 of 27) information, not a forecast", 12 coins with each result, "Can run on: paper long lane". Proposal `state proposed`, `experiment_ids []`; the edge line says a paper round pays a fixed 2x and a live one shares the pool; "Its bot starts only on Approve". |
| 7 BUILD and BLAST match; no RUNNING without trades; FOUND fits at 1235 and 390 | FAIL | BUILD "16 RULES · 5 SKILLS · 5 COMBOS" = the run's candidates (16 models, 5 skills, 5 combos); BLAST AVAX, BNB, BTC, LTC = `search_markets`. No card reads RUNNING (3 PAUSED, 1 QUEUED). FOUND at 1235: every line inside the canvas (widest ends at 1734 of 1755 px). At 390 it does not fit: "STOCKBOT BLUE · BNB" runs from 355 to 690 px on a 666 px canvas (BNB cut off), and "+21.73%" (331-555 px) is drawn over it on the same line (canvas text measured as drawn, FOUND paused). |

Vendor's own deviations (BB-SHIPPED): Flash findings start no bot; "your own exchange" is not offered; the stop is kept
or dropped on earlier windows only (not the unseen ones, which keeps the unseen result clean).
