# ET-33648 (Agent Casino follow-up): verification

Shipped 2026-11-03 00:25 UTC. Read 2026-11-03 and 2026-11-04 from the lobby, the ask panel, tables 71, 73, 77 (started after the ship and finished) and the API. Their numbering follows their shipping message (the BB-SPEC is shifted by one).

| Item | Result | Evidence |
|---|---|---|
| 1-2 allowance with the table, trades left at the ask | FAIL in part | the ask shows "0 trades left today (of 20...)"; but 2 of 8 new seats sat 24 h at 0 trades, "daily allowance used up" across the reset: #306 |
| 3 one loss does not pause | PASS | table 73: "3 losses in a row" before a pause; stop 2-3 stakes at Risk 1, 2 at Risk 10. "until HH:MM" on the panel not seen: no paused bot at the read |
| 4-5 how often a bot trades, length that suits it | PASS | "about 1 trade every 2 hours ... a 5 hours table suits it better" |
| 6 house seats trade | PASS, thin | 6 of 40 house seats on the 8 new tables made no trade (it was 15 of 45) |
| 7 one-member warning before Approve | PASS | ask text and the table's "One member" box |
| 8 no-trade seat tagged, ranked last; WINNER names the taker | PASS | no NO TRADES seat above a trader on the 8 tables; table 77 WINNER is the prize-taker, "finished #1 but is a house bot" |
| 9 ET10 labelled | PASS | table 77: "+85 ET10 · best-member reward #1 (table rank #6)" |
| 10 shared-bot line | PASS | table 71: "This bot also plays tables #47, #72: it has one set of settings, shared there" |
| 11 coach loosens and resizes | PASS | table 73: "trade size 1 → 2 % · stop loss 2 → 3 % · 7 wins in a row" and back |
| 12 end-of-table line, coach on/off | PASS | table 73: "The coach made 5 tunes ... coach on: 48 tables, -2.85 %; coach off: 4 tables, -14.13 %" |
| 13-14 no late tunes, aims, limits named | PASS | "the table ends in 8 min; no tune this late"; "aims to cap the next loss"; "inside Risk 1's limits (...)" |
| 15-16 lengths, NEXUS TUNES | PASS | NEXUS TUNES counts tunes only |
| 17 Changelog "Risk 8 → 10" | PASS | table 77 changes: owner_text "Risk 8 → 10 (trade size, stop loss and take profit)" |
| 18 lobby counts follow the filter | PASS | 5H: Live now 0, open 4 |
| 19 Create offers 1 H / 5 H / 1 D | PASS | the form |
| 20 won/lost/flat | PASS | table 73: "20 closed · 11 won · 9 lost" |
| 21 paid / waiting header | PASS | table 77: "PAID OUT · $50 PRIZE PAID · 85 ET10 PAID"; a waiting amount not seen |
| 22 trade list opened → closed | PASS | "OPENED · CLOSED (UTC)", "11-04 01:22 → 01:25" |

15 pass, 1 fail in part. What I would say: **fail on line 1-2 only, #306 named**; the rest stands. The verdict is the operator's.
