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

## Third build (shipped 2026-11-03 09:36 UTC, read 09:39 to 10:00)

| Point of the second FAIL | Result | Evidence |
|---|---|---|
| 1 Nexus pitches | PARTLY | `picked_by: nexus`, `by: nexus`, 4 picks from what rose this week, each argued. That Nexus really wrote them is their label; from here it cannot be proved. One reason is false of its basket (luxury goods); installment loans' "steady demand" has no source on the page |
| 2 real money | NOT BUILT | note unchanged, third time no ticket or date |
| 3 reach | NOT DONE | no link from /, /agent-casino, /fund-performance, /events/universe/movers, /build-it-better |
| 4 sort both ways | FIXED | all three headers reverse on a second click |
| 5 chart #297 | FIXED | check passes, lines end at the big number |
| 6 date | FIXED | "since it went live, 22 Aug" |

Invest on a theme lands on a row with "Hold this basket with your own funds" (checked, there is a way in). Six checks pass.

New, the operator's: a click on the card's name, number, chart or sentence does nothing, and the card has no links. Not in our mock or spec either.

## Fourth build (shipped 2026-11-04 06:13 UTC, read 08:30 to 09:00): real-money Invest

| Point of the third FAIL | Result | Evidence |
|---|---|---|
| 1 real money (C1) | BUILT, NOT TESTED | pc.js reads /me/buying-power, asks /quote, confirms, then /invest; a 72h card has no Invest. We placed nothing: our rule is no live money. Signed out: `GET /me/buying-power` and `/me/deals` answer 401, Invest says "Sign in...", and goes to /login?next=...pitch=<key>. Not seen: balance, fees, a placed order, My deals with a real position |
| 2 reach | NOT DONE | no link from /, /agent-casino, /fund-performance, /events/universe/movers, /build-it-better, /themes/performance |
| 3 reasons | PARTLY | luxury goods now names Marriott, Hyatt, IHG (rose 4 %); AMF-WhiteSwan names PERI, CEVA, INTU (its top three legs). The polkadot Security Token basket is credited to Vultisig and Matrixdock Gold, both down over 5 days: #304. #299 is paid |
| 4 tap on a card | NOT DONE | tap on name, number, chart, sentence: no change, no link |

New, ours: `/api/v1/pitch-cards`, `me/buying-power`, `me/deals`, `quote`, `invest` are in none of /api-docs, /openapi-public.json, /llms.txt. Seven checks run; the credit check fails, six pass. Nothing else on the board changed (15 funds, 39 event cards, 318 company cards, 13 themes, 100 72h cards, none at a loss).

## Fifth build (shipped 2026-11-10 06:46 UTC, read 06:50 to 07:40)

| Point of the fourth FAIL | Result | Evidence |
|---|---|---|
| 1 reach | NOT DONE | no link from /, /agent-casino, /fund-performance, /events/universe/movers, /build-it-better, /themes/performance, /airdrop-farmer |
| 2 tap on a card | FIXED | a tap opens Details (4 figures, the holdings with weight and 5-day return, what the number is, a link to the basket page); Escape or Back returns to the same card; a drag does not open it; phone works, the list scrolls inside the card |
| 3 reasons | FIXED | both pitches' reasons match the legs: PLBY +13.56, ABNB +12.91, RBLX +12.61, basket +5.0 % on the week; XNCR +19.89, MIRM +10.26. The credit check passes; #304 passes |
| 4 documentation | FIXED | /api-docs, /openapi-public.json and /llms.txt list pitch-cards, me/buying-power, me/deals, quote, invest |
| real money (C1) | UNTESTED | signed out: Invest goes to /login?next=...pitch=<key>; nothing placed by us |

The deck holds 2 pitches. The board: 317 company, 41 event, 13 funds, 15 themes, 3 72h cards (8 closed in the last 30 days: the platform has not minted 72h cards since about 8 Oct); none at a loss. /fund-performance changed its table (an Outside holders column, funds without outside money gone); two of our checks skipped until the parser followed it, now they pass. All seven checks pass and #289 to #297 and #304 read pass.

## Not checked

The /ws/pitch-cards push in a held-open tab. The card going behind Nexus frame by frame: stills and the unchanged code only.

## Reports

#289, #290, #291, #292, #293, checks in `tests/rest/test_profit_board.py`.
