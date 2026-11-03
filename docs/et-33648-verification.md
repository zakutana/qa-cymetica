# ET-33648 (Agent Casino follow-up): verification

Shipped 2026-11-03 00:25 UTC. Read on 2026-11-03 ~04:10 UTC from the lobby, the ask panel and table 68. Table 68 started 2026-11-02 ~08:00 UTC, before the ship, so it shows the page, not the new engine. Their numbering follows their shipping message (the BB-SPEC is shifted by one).

| Item | Result | Evidence |
|---|---|---|
| 1-2 trades left at the ask | PASS | asks #67, #64: "0 trades left today (of 20, resets 00:00 UTC)" |
| 3 one loss does not pause | OPEN | needs a table started after the ship |
| 4-5 how often a bot trades, length that suits it | PASS | "about 1 trade every 2 hours ... a 5 hours table suits it better" |
| 6 house seats trade most | OPEN | table 68 still has a house seat with 0 trades (Ichimoku Empress); it started before the ship |
| 7 one-member warning before Approve | PASS | ask text and table 68 "One member" box |
| 8 no-trade seat tagged and ranked last | PASS (page) | Ichimoku Empress NO TRADES, rank 6 under a -4 % seat that traded; WINNER line not yet seen |
| 9 ET10 labelled "best-member reward" | OPEN | needs a finished table |
| 10 shared-bot line | PASS | table 71 (read 2026-11-03 10:45 local): "This bot also plays tables #47, #72: it has one set of settings, shared there" |
| 11-14 coach loosens, resizes, end line, no late tunes | OPEN | table 68 coach only re-checks ("same check x14") |
| 15-16 lengths, NEXUS TUNES | PASS | NEXUS TUNES 0 beside 5 CHECKED rows |
| 17 Changelog "Risk 5 → 8" | OPEN | needs a Risk move on a new table |
| 18 lobby counts follow the length filter | PASS | 5H: Live now 0, open 4, all 5H |
| 19 Create offers 1 H / 5 H / 1 D | PASS | form shows 1 hour, 5 hours, 1 day |
| 20 won/lost/flat | OPEN | needs a finished table |
| 21 paid / waiting header | OPEN | needs a finished table |
| 22 trade list opened → closed | OPEN | not read yet |

## To read on table 68 or a newer one

Table 68's coach panel says "Risk 1's limits (stop loss 2-3 %)" while the bot runs stop loss 1 %: Risk reads 1 CUSTOM. It was set before the ship, so it does not refute item 3.

Pending asks #67 and #64 lapse at about 07:15 UTC; they are the lapse test. A bot whose allowance reset at 00:00 UTC still reads 0 left at 04:10 UTC (#237, bots spend the allowance away from tables).
