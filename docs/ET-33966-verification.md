# ET-33966 Quant Lab windows, checked 4 Nov 2026 (script v=6aea1ee9), company 14, search #19

Search #19 (started by Cymetica 3 Nov 18:06 UTC, done 23:51, 33,312 combinations, n tried 45,952, z 4.74): 94 shortlisted, 4 passed, all long, all on AVAX. Corrected 4 Nov: the 4 paper bots (experiments 1 to 4) were created but not started: `pending`, no instance, no start time, 8 hours later. Company 14 is `paused` ("nothing runs and nothing is charged until you resume", last pass 30 Oct), which is the likely reason, and likely the reason for the 2 Nov gap in the daily search too. The verdict note said "started".

Display, measured at 1235 x 1206: page 22,052 px (18 screens), blind-test block 19,357 px for 94 rows, first winner row 32 at y 8,312, bots at y 21,473, one run row 378 px. FOUND draws only `botList[0]` and "LIVE · PAPER 0.00%" while the bot is queued. BLIND still says "60% SEEN", "24H", "90 DAYS · HOURLY". THE BAR draws 94 overlapping labels. Their fix proposal: `outbox/quant-lab-method/change-1.txt`.

| # | Done when | Result |
|---|---|---|
| 1 | At least 4 non-overlapping 36-day windows, dates, search period, 12-coin move, falling and rising | PASS. 12 Jun, 18 Jul, 23 Aug, 28 Sep; moves -2.7, +23.3, +20.3, -20.5 (Binance closes gave -3.7, +24.1, +14.9, -16.4; same kinds); 235 days loaded for all 12 markets |
| 2 | "N of M windows made money" with pooled result, bar, trades; under 20 trades, a losing window or under the bar never reads passed | PASS. Labels lost_windows 52, below_bar 33, too_few_trades 4, lost 1, won 4; the bar is 8.9 to 37.7 per row, applied once to the pooled result |
| 3 | Shortlist holds more than one model and a short rule; a passing short starts a bot or says why | PASS as built: 94 shortlisted, 11 short, 16 models. No short passed (best: cryptobull_red AVAX, 2 of 4 windows, +6.47%), so the "says why" path was not seen |
| 4 | Date of every input; a repeat run does not test a setup on a window it failed | PARTLY. `inputs_dated: true`, cutoff per window. The repeat run was not tested: it needs a second search of several hours. And see below: the windows a setup is counted on are not all blind |
| 5 | Skills and Named Combinations among the candidates | PASS. 16 models, 5 skills, 5 combinations; the others listed as not replayable with a reason; skills and combinations reached the shortlist |
| 6 | RUNS shows the windows, the market's move beside each result, any market not loaded | PASS on the page: window chips with the hold beside each result, "inputs dated ✓", long 83 / short 11. No market was missing in this run, so the naming of a missing market was not seen |

## What is wrong: a setup is counted on windows it was chosen on

How the shortlist is built (their `shortlist_rule`): each window takes the best setup per model from that window's own search period (the 54 days before it), then "every shortlisted setup is then replayed on every window". Windows follow each other every 36 days and a search period is 54 days, so the search period of window k always contains window k-1 and most of window k-2. A setup chosen for window k has already seen those windows.

Counted from the API: 71 of the 94 shortlisted rows count at least one window that lies inside the search period they were chosen on. All four winners do:

| Winner | Chosen on | Counted but not blind | All 4 windows | Only the blind windows |
|---|---|---|---|---|
| enzyme AVAX, SL 8 TP 10, rsi_14 < 25 | search period of 18 Jul | 12 Jun | +11.08% on 31 trades, bar 8.91% | +6.08% on 19 trades, bar about 6.97%: fails, and under the 20-trade floor |
| immune AVAX, SL 8 TP 30, rsi_14 < 30, volume 1.8 | 18 Jul | 12 Jun | +7.97% on 33, bar 5.40% | +4.61% on 22, bar about 4.41%: marginal pass |
| cryptobull_blue AVAX, SL 6.4 TP 8, rsi_14 < 25, volume 1.8 | 18 Jul | 12 Jun | +4.38% on 25, bar 3.65% | +2.64% on 13 trades: under the floor |
| cryptobull_blue AVAX, SL 8 TP 10 | 23 Aug | 12 Jun (part), 18 Jul | +7.35% on 48, bar 5.64% | +2.76% on 16 trades: under the floor |

The bar for the blind windows alone is scaled by the square root of the trades, as their formula does; an estimate, not their replay.

Their method text says "the search never sees them". For these setups it did.

Also seen: the four winners are one finding, not four (same coin, buy a deep RSI dip). A window counts as "made money" at +0.36% on 3 trades or +0.54% on 2 trades, so in the two rising windows (AVAX +45%) a winner trades 2 to 4 times and a tiny gain counts as a won window.

## Draft verdict note (not posted)

See the end of the chat answer of 4 Nov; the operator decides pass or fail.
