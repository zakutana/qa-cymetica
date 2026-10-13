# ET-31300 "Chart Analyzer, a chartist for degens": line-by-line verification

Read 2026-10-13 18:02-18:36 UTC, live https://cymetica.com/chart-analyzer for Collector Crypt (CARDS, Solana, 1D), signed out, viewports 1920x1080, 1440x900 and 390x844 by emulation. Spec: the 33 lines of its BB-SPEC (identical to outbox/chart-analyzer-one-number/request.md), "Done when" lines in order. Shipped 17:57 UTC (BB-SHIPPED), 5 h 29 min after BB-ACCEPT. GET reads only; nothing was typed into "Ask the chartist", and nothing was clicked that writes.

**Totals: 8 PASS, 1 FAIL, 2 PARTIAL, 2 NOT TESTED** (13 "Done when" lines). The verdict is the operator's.

| # | requirement (short) | verdict | evidence |
|---|---|---|---|
| 1 | coin bar, chartist, chart, setups, key levels on screen without scrolling at 1440 x 900 and 1920 x 1080 | PARTIAL | 1920 x 1080: all five are in view (chart 210-1000 px, key levels 623-849, live trades start at 885). 1440 x 900: the last key level row, "Support 2", sits at 901-921 px, 21 px under the fold; live trades start at 958. Page height 1229 px. No horizontal scroll at any width |
| 3 | 390 px: chartist first, chart visible while a setup is selected | PASS | Order on the page: chart read (309 px), chart (803-1323), setups as a swipeable strip (1350, 1,780 px wide in a 301 px strip), key levels (1627), live trades (1917), fundamentals (2826). Chart and strip fit one 844 px screen when scrolled to the strip |
| 4 | one gauge and one direction word, nothing repeats the direction, "not a forecast" | PASS | Gauge, "NEUTRAL →", "5 bullish · 4 bearish of 9 signals", "What the chart shows now, not a forecast." The gauge's (i) says the needle counts each setup by its textbook side and each timeframe trend |
| 5 | four timeframe chips by one stated rule | PARTIAL | 1H ↘ 4H ↘ 1D ↗ 1W ↗ are there. The (i) says "each timeframe trend (up or down)" but not the rule that makes a timeframe up or down |
| 6 | three lines, no sentence | PASS | WATCH 0.2545 "below → 0.2468", RISK 0.347 "bearish engulfing", FLOW 15M "$3.1K sold vs $463 bought" |
| 7 | no 44% / 53%, no 1-100 gauge; NO VERDICT with its why in the (i) | PASS | EDGE "NO VERDICT" with a button "Why, and the study's figures"; "44% / 53%" and "49" appear nowhere on the page text |
| 8 | "Ask the chartist" answers about this chart | NOT TESTED | The box is there ("Ask the chartist about this chart"); asking it may cost NEXUS usage, so nothing was sent |
| 9 | one-row toolbar, every toggle in Candles or Layers, no legend | PASS | 1H 4H 1D 5D 1W 2W 1M, 60 120 All Fit, Candles ▾, Layers 11 ▾, Log, Replay, Full screen. Layers: Levels, Signals, Indicators and the ATR and Volume profile settings; no legend text under the chart |
| 12 | setup row: one line of words, one bar, two figures | PASS | Name, kind and age, the two figures. Three rows add "rose first no more often than the average chart" to the sub-line |
| 13 | selecting a setup highlights it on the chart while both are visible | PASS | Row 2 selected: marker 2 lit, a card beside it: "Confirmed 4 candles ago. Textbook: bullish. On exchange charts ↑44% ↓50%, about the average chart" |
| 14 | a bell on a key level sets an alert that fires | NOT TESTED | Bells are on all six levels with "alert me when crossed"; signed out here, and firing needs a price move |
| 16 | the live trades list moves as the pool trades | **FAIL** | Three fresh loads at 18:26, 18:33 and 18:35 UTC each showed the newest trade at 18:17:07 and never moved. The same pool's own trades (GeckoTerminal) at those moments: 18:22:26, 18:29:22 and 18:35:29. The page's rows match the pool's real trades in price and size ($11, $32, $252), so it is this pool, 19 minutes behind at the last read. The header price (0.2844) was current. Their code takes trades over /ws/chart-analyzer ("trades messages"), so the push exists; what arrives is old. The pane was hidden during part of the test, but a fresh load takes its first list from the server, not from the visibility of the tab |
| 17 | "How it's measured" once; no verdict sentence twice; no needless digits | PASS | One closed section; a link of the same name in the setups panel opens it. No sentence is repeated; the chart title no longer carries "196.99767960241462" |

## Differences that are not failures

- The gauge reads NEUTRAL where our mock read BULLISH on the same 5 of 9; the thresholds are theirs to set (the spec said goals, not methods).
- Tier shows "Vetted · all gates passed" where the mock said "S · all 6 gates".
- The WATCH line names the 20-bar average (0.2545) and the trendline (0.2468) as the levels; the mock named the trendline and the 50-bar average.
- The chart's range buttons read 60 / 120 / All / Fit (the spec said 90 / 180).

## Open

- Line 16 is the one to take to Cymetica with the three load times above, if the operator calls it a fail.
- Lines 8 and 14 need the operator, signed in: ask the chartist one question; set a bell and let the price cross.
