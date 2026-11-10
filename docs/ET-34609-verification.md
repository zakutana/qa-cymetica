# ET-34609 FOMO Radar: verification and data audit

Shipped 2026-11-10 05:13 UTC, 9 hours after the deadline (2026-11-09 20:13 UTC, BB-LATE at 20:23). Read 2026-11-10 06:20 to 06:50 UTC,
anonymous, Chromium at 1440 and 390 px, `/static/js/fomo-radar.js?v=20261110-1`. The verdict is the operator's.

## Done when: 8 of 9 pass

| # | Line | Result |
|---|---|---|
| 1 | Basic as picture 1 at 1440, picture 2 at 390, Advanced as picture 3; view survives a reload; chain switch works in both views | **FAIL** on the chain switch: Advanced, Top wallets stays on "Loading wallets…" after Solana and back (#330). The rest passes. Addresses are written in full (42 characters, two lines) where pictures 4 and 5 have the short form. |
| 2 | Headline on three lines at 1440 and 390 | PASS (57.6 px and 28.9 px, three lines) |
| 3 | Cards: order, chance, #rank, SOLD | PASS: order equals the signal rows, 12 of 12 chances equal probability_3x_72h, 29 of 29 wallet lines carry the right rank, win % and IN/SOLD |
| 4 | Exit rows as red chips, never cards | PASS (12 chips, 0 exit rows among the cards) |
| 5 | Promotion with its live count, both links; hidden without PONS rows | PASS ("37 of 40", both links 200, hidden on Solana) |
| 6 | Best wallets, USD = realized_eth × eth_usd | PASS (4 of 4) |
| 7 | Every section, column, tab and paragraph in Advanced | PASS (32 headings and columns found, 9 of 9 sampled paragraphs kept) |
| 8 | No horizontal scroll at 390 | PASS (390 of 390 in both views) |
| 9 | Universe under Ironstar Capital; Products; Your apps | PASS: slot 4-4 of company 14 in `universe.js`, panel "MADE BY" the holder; Products and Your apps list "FOMO Radar" (signed-in read of the same day, see #326: the Apps table still calls it "Crypto Radars") |

The page draws what the API gives: no figure on it differs from the response it was drawn from.

## The data behind it: not reliable yet

| Bug | What |
|---|---|
| #332 | The top "wallets" are router contracts. 0xd6d35b56… (rank 1, "+$5,099 made") took 462 buys for 406 different buyers; 0x65050a9b… 98 buys for 59; 0xb3ea566c… 24 for 19. 52% of the window's buys (1,054 of 2,016) are credited to the contract called, not to the buyer. Plain wallets match the chain to four decimals. |
| #328 | Rank 1 shows +2.41 ETH realized; its only curve shows 10.69 ETH in, 10.10 ETH out, all tokens sold: a loss of 0.59 ETH (chain: -0.588). |
| #327 | Amounts on curves quoted in ORBIO, NVDA, SPCX, DJT, AAPL are added as ETH. POLLY is card 2 with 8,477 ORBIO as 8,477 ETH: conviction 33.9, and 8.0 without that multiplier. |
| #333 | Different windows at the same moment: 9,456 s / 5,909 s / 1,248 s, 242 / 180 / 43 tokens, leaderboard of 25 or 4 rows. The 6-hour target was never reached in any read; 16 of 25 leaderboard rows had one round trip. |
| #329 | /backtest answers 503 after 60 s on both chains, 8 and 10 Nov; the page says WITHHELD. |
| #331 | Solana /traders says a 24-hour window for records held up to 413 hours; the page prints "made in 24.0 h". |

Checked and correct on the snapshot of 06:21 UTC: the trader score formula (25 of 25 rows on each chain), win rate, leaderboard order,
probability = the published isotonic curve at the row's conviction (40 of 40), conviction from the published formula (37 of 40, the
other three list 5 of their 7 buyers), thin, fresh, hot, gone, usd_invested, the credible-exits rule. 3,300 of the chain's 3,329 trade
legs in the window were indexed. Solana's top 10 wallets are ordinary system-owned accounts.

**Solana.** The wallet layer reads a free public RPC: 4 of 40 pools had wallets at 06:22 (87 legs), none from 06:34 (status
"degraded"), when Top wallets and Best wallets show "unavailable". 37 of 40 cards are ranked by buy pressure, which /docs itself calls
wash-tradeable, under the heading "Smart wallets are buying".

**The 3× chance.** It is calibrated (said 1.4 / was 1.7, 3.0 / 3.2, 5.3 / 5.7 out of sample) and nearly flat: Brier 0.02237 against
0.02248 for the plain base rate of 2.07% on Robinhood. On Solana 18.8% of signals are left out of the fit as unmeasurable.

Evidence in `docs/et-34609-audit/`: the two socket snapshots the figures come from, the page DOM, and `live.py`, `checks.py`, `compare.py`, `recount.py`, `window.py`, `chain.py`
(read-only RPC: eth_getLogs, eth_getCode, eth_call, eth_getTransactionByHash, eth_getTransactionReceipt).
