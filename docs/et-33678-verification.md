# ET-33678 (Pitch Cards, Profit Board): verification

Shipped 2026-11-03 00:37 UTC. Read on 2026-11-03 ~04:10 to 04:50 UTC, at 2560, 1920, 1440 and 390 px, not logged in. Their shipped `pc.js` and `pc.css` are ours plus their data and My deals changes (diffed); the motion code is unchanged.

| Done when | Result | Evidence |
|---|---|---|
| 1-3 entry screen, 1440 and 1920, in their shell, sharp, finger on card | PASS | card 400 x 530, headline 58 px at 1920 and 52 at 1440 (our layout() shrinks it), scene.webp 5120 x 2880, nexus.webp 1840 x 2320, no sideways scroll. The first card's chart is flat: #293 |
| 4-9 animation and swipe | PASS | tilt and INVEST fill, flip to $25 with chips $10 $25 $50 $100, Invest, next pitch, left swipe, "That's all for now". "All" became $100: no balance is held, theirs to decide (item 16) |
| 10 phone | PASS | matches picture 6, swipe to the amount face at 390 px, no sideways scroll |
| Pitches reach every user | FAIL | reachable at its address only; no link from /, /agent-casino, /airdrop-farmer or /fund-performance. They say: not in the menu while the product freeze holds |
| 11 Profit Board look | PASS | tags in colour, three columns, Days line with the peak marked. Wrong dots on 72h rows: #292 |
| One page, every profitable thing, up to date, nothing at a loss | FAIL | 6,854 rows, 10,323 more "being measured". Losers shown as up: #289 (Quantum Frontier, Project Omega), #290 (DeFi Undercurrent Short). Missing: #291 (FTA Cryptos) |
| 12 nothing overlaps | PASS, one note | the toast covers PASS for 6 s after Invest |
| C1 real money from day one (BB-CHANGE, accepted) | NOT BUILT | they call it "a separate build in the human-reviewed slot"; no ticket or date named. Nothing on the page moves money |

## Their statements against the page

- "Invest opens the product's own page": it does not open. It shows a toast with a link for 6 s, then the link is gone (My deals keeps it). The page's own note says the same false thing. The link does lead somewhere: Molecular's page has "Invest in Molecular now — it's LIVE".
- Nexus writes nothing: the pitch sentence is our mock's template (their `pc.js:81`, our `pc.js:73`), and "Still climbing" sits on Molecular, +30.03 % five days ago, +15.8 % now. The operator's point, 2026-11-03: it should reason for itself.
- The board's kinds and the pitch bar are our mock's: `TABS` and `TAGS` identical, bar 8 weeks, 5 %, $10B, 7 days. Theme baskets (/themes/performance, named in the request) have no tag or row. The operator, 2026-11-03: they should have decided all of it themselves.
- "the board refreshes every 5 minutes": as_of moved 04:09, 04:14, 04:28 while read. Holds.
- 72h rows measured at the close: rows agree with `current_index` on the 15 cards sampled. The peak is understated on some live cards, by 1 to 4 points against the card's history (nuclear +130.77 against +134.52). Not filed.
- Row counts changed from their message (2,497 and 14,673) to 6,854 and 10,323: the measuring is running.

## Second build (shipped 2026-11-03 07:26 UTC, read 07:33 to 07:50)

| Point of the FAIL | Result | Evidence |
|---|---|---|
| 1 real money | NOT BUILT | the page's note is unchanged; no ticket or date |
| 2 reach | NOT DONE | no link from /, /agent-casino, /fund-performance, /events/universe/movers |
| 3 board #289-#292 | FIXED | checks pass, passes sent; 484 rows: 318 company, 100 72h (best 100), 43 event, 12 themes, 11 funds |
| 4 #293 | FIXED | the reading is gone from the fund's page |
| 5 Invest opens the page | FIXED | navigates to the product in Firefox and Chromium; MRNA's page has Buy |
| 6 Nexus writes | NOT FIXED | sentences vary between reads and match their numbers, but only repeat the returns; "Want a piece?" remains. Whether a model writes them is not visible from here |
| 7 their own choice | PARTLY | themes and M&A deals added, pitch bar changed (`bar.rule`), still "what is up". Other things on the platform not added; theirs to decide |

New: the line on a card ends far from its big number (`test_a_pitch_chart_ends_where_its_big_number_does`). Header sort goes one way only; our mock's code too (`pc.js:350`).

## Not checked

The /ws/pitch-cards push in a held-open tab. The card going behind Nexus frame by frame: stills and the unchanged code only.

## Reports

#289, #290, #291, #292, #293, checks in `tests/rest/test_profit_board.py`.
