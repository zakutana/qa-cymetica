# ET-33759 (Gem Screener: what a reader needs to trust a pick): verification

Verdict: pass, the operator's word, sent 2026-11-03 04:39 UTC, with the two faults below in its note. Shipped 2026-11-02 23:48 UTC. Read on 2026-11-03 from a browser at 1440 and 1920 px and on a phone, snapshot 02:57 UTC; the numbers below are from the page unless the line says otherwise.

| Done when | Result | Evidence |
|---|---|---|
| 1 exploit on the card | FAIL, 2 of 4 | Meteora "$1.5M, 17 Jan 2026", Trust Wallet "$8.5M, 25 Dec 2025" shown, red. Aero ($700K, 21 Nov 2025) and CoWSwap ($1.2M, 14 Apr 2026) read "Exploit in the last year" in their own check and show none on the card, because `dlevel.exploit_1y` is empty. Filed as #287. |
| 2 slip over 3% | PASS | GMX 8.3%, Dolomite 7.1%, CoWSwap 5.3%, Trust Wallet 4.2%, Lido 3.8% show slip, then "passes on $X a day, all venues". 0.4 to 1.8% unchanged. |
| 3-4 Watch out | PASS, but for item 1 | Own warnings and own figures (20, 21, 31, 43% of its best). None on Pump, GMX, Dolomite, Lido. No card mentions the theme. Red only with an exploit, so the Aero and CoWSwap blocks are cyan through the item 1 fault. |
| 5 both windows | PASS | Lido "last 30 days 0% · 12 months 20%", tooltip "Holders got 20% over 12 months, 0% in the last 30 days". Aave 0% and 22%, same tooltip form. Jupiter "50.0%", unchanged. |
| 6 Rug power line | PASS | Of the 49 apps passing or one gate away: 27 with a reading have the source to draw the line, 22 have none, 0 have a reading without it. Stargate's sentence is word for word. Lido and Aave have no line because their check reads "Not scanned". |
| 7 Picks log | PASS, one case unseen | Route answers without an account, 202 changes since 22 Sept. Refresh of 3 Nov 01:38: 3 in, 3 out, by name, reason "still passes, outside the top 10 by upside", true of Orca, Rhea and Sky (13 pass). Rows before the ship read "not recorded · today: X", said honestly. A pick that leaves on a failed gate since the ship has not happened yet. |
| 8 count | PASS | "6 of 36"; 36 apps have exactly one `degen_fail`. |
| 9 backtest line | PASS | Words as drawn. In the code: date from `backtest_summary.generated_at`, days from `picks_ledger.since` against the snapshot, so both move. 18 days and 12 Nov are right. |
| 10 near-miss card | PASS, one fault | All 6 have their own card on hover and focus, 5 / 6 in red, failed gate marked, no pick card covered at 1440 and 1920, pointer not taken, click opens the panel, touch keeps the click only. Fault: when the row is low on the screen the card runs off the bottom (below). |
| Look, phone | PASS | Cards and near-miss card as pictures 1 and 4. Phone: one column, no overflow. |

## The near-miss card off the screen

At 1440x900, cube at y 600: 261 px of the 584 px card below the screen; at y 770: 431 px, only the name and upside visible, failed gate not. The same at 800 and 1000 px tall. Scrolling down from the picks, this is where the row first appears. It follows our own line "does not cover the pick cards", which leaves no room upward, so this goes in the verdict note and not in a bug.

## The operator's look, after the verdict

The Picks log is too big and too loud: they pictured a quiet line like the blue Backtest line. Our picture 4 drew an open panel and the build follows it, so this is a change of our design. The near-miss card must stay whole on screen, even over the pick cards. Both went out by Telegram with #287.

## Worth saying, not faults of the build

* "Dilution unknown: no schedule published" is our own mock's wording. On Collector Crypt it is not true: its Streamflow schedule is public. The unfiled Supply Analyzer request fixes the cause.
* "Not growing: 30-day revenue is 96% of its best" (Securitize, a near miss): the flag came from its 90-day growth, so our line's figure does not explain it. Our wording too.
