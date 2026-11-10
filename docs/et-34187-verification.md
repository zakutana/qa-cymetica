# ET-34187 verification (Airdrop Farmer, 5 free farms)

Shipped 2026-11-10 07:15 UTC (deadline was 2026-11-05 20:03 UTC; BB-LATE). Read 2026-11-10 07:19 to 07:22 UTC: `GET /api/v1/airdrop-farm/farms` (generated_at 07:18:55) and the live page in Chrome at 1440, 1920 and 390 px.

| # | Done when | Result | Evidence |
|---|---|---|---|
| 1 | The five show AGENT RUNS IT and FREE, with the user step; Rialo listed | FAIL | Push Chain, GenLayer, Konnex, Miden: FREE · COMING SOON, route state `tasks`, reason "Coming soon, not run yet". User steps shown. Rialo is not on the list (0 mentions in the API). `agent_runs_count` still 2 (Upshift, Mellow). |
| 2 | Each of the five has a done step with a tx hash on Live farms | FAIL | None runs, so no steps and no transactions. |
| 3 | GenLayer card says terms exclude automated-only accounts; nothing held back but KYC | PARTIAL | Chip "TERMS EXCLUDE AUTOMATED-ONLY ACCOUNTS · YOU DECIDE" is there. But the five are held back by Cymetica's own work: faucet wallet without test PC/GEN, no reviewed adapter, Miden's non-EVM accounts. |
| 4 | The 5 more listed, each checked in the last 24 h | FAIL | Orbinum and vibe/vibe appear only as testnet discovery candidates, not on the list; Psy Protocol, Unicity, DogeOS absent. Last checked on the free cards 2026-11-09 00:09 UTC, 31 h before the read. |
| 5 | A farm whose token trades leaves the same day | NOT MEASURED | Needs a token launch during the window; `removed` lists 17 farms. |

Bug found in the build: #335, on desktop the "YOUR STEP" line is drawn over the reason text, the FREE · COMING SOON chip and "more" on all four free testnet cards (fine at 390 px).

Score: 0 of 5 pass, 1 partial. Verdict is the operator's. FAIL sent 07:26 UTC (BB-0057).

## Re-read 2026-11-10 09:45 to 09:50 UTC, after Nexus's REPLY-0276

- #335 fixed: no overlap on the four cards at 1440, 1920 and 390 px.
- Line 4 now PASS: Orbinum, Psy Protocol, Unicity, Vibe Vibe, DogeOS all on the page, Coming soon with the user's step, checked 7 min to 2 h before. Rialo is on the page too.
- Lines 1 and 2 still FAIL: no free farm runs, the page still says 2 of 2 farms. Nexus says Push Chain and GenLayer wait for test PC and test GEN in their faucet wallet (CAPTCHA faucets a person must claim), and Konnex, Miden and Rialo have no runner.
- Line 3 still PARTIAL, for the same reason.
