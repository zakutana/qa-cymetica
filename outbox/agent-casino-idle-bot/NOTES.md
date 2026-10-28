# A seated bot that never traded (Agent Casino, Flash Pro table 24), read 2026-10-28 08:55 UTC

The operator's two observations (screenshot of the table's Standings, and the bot's "NEXUS tunes" change log), checked against the API
the same minute (GETs only, our key; `why0.py`-style reads of `/api/v1/cloned-bots/my-clones`, `/cloned-bots/{id}/activity`,
`/agent-tournaments/lobby`).

**Bot:** "lab Wave 2 Perceptron Oracle" (da83f3d1), seated at table 24 (Flash Pro, 6 seats, started 2026-10-27 09:14 UTC, ends
2026-10-28 09:14 UTC) and table 25 (ET10 100, 7 days).
- `status active`, `is_trading true`, balance 250.00, `readiness.tradeable true` (stake 17.50, stop loss 7 %), no auto-pause.
- Table 24 row: rank 4, ROI 0.00 %, volume $0 of $107.14 to qualify, `qualified false`, `bot_state Trading`, `wins_now_usdc 50`.
- Activity since the table started: ONE trade, a $1.00 event-card buy at 2026-10-27 23:41 UTC (still open). No BTC/ETH epoch
  trade since 2026-10-20 14:10 UTC, the lane this bot (neural_ensemble, YES at score >= 0.60, NO at <= 0.40, else sits out) used before.
- House bots on the same table: 40 trades each, "20/20 today, resumes 00:00 UTC".

**The change log ("NEXUS tunes", 92 rows):** from 2026-10-27 15:59 to 2026-10-28 08:42, every ~16 minutes the same row:
`CHECKED no change · no trade for N h (none yet); change refused: the bot could not be changed right now`, with N growing from 6 to 23.
About 60 identical rows bury the three real tunes of the first hours (stop loss 6 to 5 %, 4 to 3 %, take profit 24 to 5 %). No reason is
given for "could not be changed right now".

**What is not known:** why a funded, tradeable, "Trading" bot made no epoch trade for 24 h (a silent strategy that sits out, a block
in the table, or a fault); what "change refused" means; why rank 4 shows "PRIZE NOW $50" with $0 volume and not qualified (only the
top 2 are paid at this table, so it may be the buy-in coming back, or a wrong label).

**Not done yet:** a check and a report through `submit.py` (the operator also asked for the Telegram text; none written). Capture the table's
final standings after it ends (09:14 UTC) before filing.
