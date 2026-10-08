# ET-29379 "Gem Screener Better": line-by-line verification

Read 2026-10-08 05:05-05:40 UTC, live https://cymetica.com/gem-screener/app (snapshot generated 2026-10-08 00:19:57 UTC), 1360x900 and 390x844 (touch emulated). Spec: `zakutana/gem-screener@e5b5770` `docs/followup-2026-10-04/SPEC.md`, checklist lines C1-C59 in order. GET reads only.

**Totals: 45 PASS · 1 FAIL · 13 CANNOT TELL** (+3 BB-SPEC boilerplate lines, all PASS)

Item 12 (the tray) could not be tested: in this session, ticking a project was blocked by the permission classifier.

## FAIL

| # | requirement (short) | verdict | evidence |
|---|---|---|---|
| C57 (22) | every tap target at 640 px and below is at least 44 px | FAIL | Three `tabindex=0` tooltip triggers have no larger hit area at 390 px: status line "5 h ago" 48x14 and "Live" `#liveState` 39x14 (every tab), and Top Picks backtest tag "judges the old gates" 131x15. All three were there before this ticket. Everything else passes: 675 targets across 4 tabs plus 69 in the open coin detail, including the pick "+" (44 px `::after`), Legend, launch chip, estimate tag 77x44 and the 6 guardian rows 311x44 |

## CANNOT TELL

| # | requirement (short) | verdict | evidence |
|---|---|---|---|
| C2 (1) | nothing else on Top Picks moved | CANNOT TELL | Altseason `#startAlt` 1281x218 (spec: 1281x219). No earlier measurements of the funnel or pick cards to compare against |
| C3 (2) | sector card: name, number, action; the return is the biggest text | CANNOT TELL | Name 20 px, ▲ HOT pill and outlined "Fund →" are all present. No fund shows a return today: all 3 cards show "not invested yet" at 15 px. In the CSS, `.hs-ret` is 2rem, larger than the 20 px name |
| C4 (2) | stage colour never on a return; red real minus as large as positive | CANNOT TELL | No return is rendered (all funds `invested:false`), so the colour of a return can't be seen. No sparkline. The stage colour is only on the card's top edge (`hs-st-hot`) |
| C10 (5) | pick card meter: the existing tooltip | CANNOT TELL | Everything else on the line passes: "DEGEN METER" label, bar 272 px wide, "5/10" at its right end (number right edge 323 = bar right edge 323), no band word, "Blue chip" / "Casino". Hovering the bar shows the card's tooltip ("Solv Protocol · $22.0M today…"). The meter has no tooltip of its own and no (i). Unknown whether it had one before |
| C32 (12) | the tray comes in at the first tick, with a short entrance and highlight; no motion with reduced motion | CANNOT TELL | Ticking was not exercised (blocked). Code: `@keyframes trayIn/trayDock .45s`, and `prefers-reduced-motion` sets `animation:none` |
| C33 (12) | sticky under the header on desktop, docked at the bottom on a phone | CANNOT TELL | Not exercised. Code: `.pickfloat.dock` |
| C34 (12) | ring "N of 30", chips, "Launch a fund with these N", Clear; never covers a row | CANNOT TELL | Not exercised. Code: `'Launch a fund with these ' + n`, `pb-launch` |
| C35 (12) | at 30: caution blue, the limit line, unpicked controls disabled | CANNOT TELL | Not exercised. Code: `pb-limit` "30 is the limit: remove one to add another" |
| C42 (17) | every data source reviewed and moved off rate-limited free APIs | CANNOT TELL | Can't be seen from outside. `fetch_warnings`: 2 × `source_warning` |
| C43 (17) | 7 days: "not refreshed / via DeFiLlama" warning almost never shows; no audit-failed refresh | CANNOT TELL | Day 0: status line "Updated 5 h ago · 232 apps · 33 chains · Live", with no warning. `/status` `last_attempt ok:true stage published`, all 4 audits exit 0. The window ends 2026-10-15 |
| C47 (18c) | a pending rebalance shows "Rebalance proposed, waiting for approval since <date>" | CANNOT TELL | `/funds` has `pending:null` on all 12 funds. The string is in the code of both the app and the fund page |
| C49 (18d) | 7 days: holdings differ from picks only by a pending, dated, disclosed rebalance | CANNOT TELL | **Day 0 already diverges:** the fund holds CARDS, SOLV, MNDE, O, GMX, EDGE, MET. `/picks` (00:19Z) are SOLV, CARDS, BNKR, GMX, EDGE, O, SPK. MNDE and MET are held but no longer picks; BNKR and SPK are picks but not held. `pending:null`, next rebalance Oct 12. Picks move every 6 h and the rebalance is weekly, with nothing pending in between, so this line will likely fail |
| C58 (22) | pick controls and tray work on a phone; minus kept; nothing loops; reduced motion; no label changed | CANNOT TELL | Tray not exercised. Minus signs kept (e.g. "↓ −5%"). The ET-29379 CSS has no `infinite` animation and two `prefers-reduced-motion` rules. No baseline to check "no label changed" |

## PASS

| # | requirement (short) | verdict | evidence |
|---|---|---|---|
| C5 (2) | states "no fund yet", "new, no return yet", loading still show | PASS | Seen live: "Fund: loading…" on first paint. The other two strings are in the shipped code (`hs-ret-w c-na`); no fund is in those states today |
| C1 (1) | Hot sectors in one framed panel like the Altseason Index | PASS | `section#startHot.hspanel` 1281x313. Border `1.33px solid rgba(0,207,255,.45)`, radius 12 px, bg `rgb(13,21,32)` and shadow are identical to `#startAlt.altpanel`. It holds the 3 cards and `#startFund` |
| C6 (3) | trend words next to the icon; tooltips unchanged | PASS | AI and RWA show "Already leading", L2 shows "Beaten down but turning". The icons keep `data-tiplabel` and the aria-label "Already leading: Beat BTC this month…" |
| C7 (4) | flagship has the card's anatomy one size larger, with the one solid button | PASS | Name 24 px (cards 20), return 2.6rem (cards 2rem). The only solid button is "Fund performance →" (bg `#00cfff`, 189x44); the 3 "Fund →" buttons are outlined |
| C8 (4) | "not invested yet" while the fund page says not bought | PASS | The flagship shows "not invested yet". /fund-performance/aib-gs-picks: "This fund has not bought its assets yet (CARDS, SOLV, MNDE, O, GMX, EDGE, MET)" |
| C9 (4) | 390: stacked, no horizontal scroll, flagship is name, number, full-width button | PASS | scrollWidth 390. Cards at x=33, w=324, stacked. Flagship: name at top 1151, number at 1307, button at 1338, 286 px wide (the full content width) |
| C11 (5) | empty segments tinted by zone | PASS | off blue `rgba(59,130,246,.2)`, off red `rgba(255,68,68,.15)`. CSS rule for `i.off.zg` present |
| C12 (5) | Apps table: compact bar + "N/10", same level | PASS | e.g. "7/10" Pharaoh. 119 of 119 rows equal `/api/v1/gem-screener` `dlevel.level` |
| C13 (6) | Supply tooltip: title, one line, small line | PASS | Pharaoh: "Supply pressure 1/10 · Flooding" / "Sellable tokens grow +51% to +66% a year (estimate)" / "1 = most new supply · 3 parts not measured" |
| C14 (6) | Supply card: big figure + estimate, badge, sentence, pie, curve | PASS | "+51% to +66%" ESTIMATE · "1/10 Flooding · 1 = most new supply" · "The pile of tokens that can be sold grows 22.5M a month…" · pie · curve "Oct 2026 · 529M → Sep 2028 · 1.00B" |
| C15 (6) | everything else behind "What we could not measure (N)" | PASS | The `<details>` "What we could not measure (3)" holds: not measured, assumed, $3.3M / +17% a week / unknown next unlock, sources, formula "6 − ceil(…/2.5%)", "Read Oct 8", "SUPPLY SOURCES DISAGREE" |
| C16 (6) | hovering a slice or legend row highlights both and shows a line | PASS | Hovering "Free to sell" highlights the row and the slice, and shows "Free to sell · 30.8M · 5.8% · can be sold now" |
| C17 (6) | four states, red stays red, the Supply Analyzer's figures | PASS | Apps cells: range 104, measured 11, unknown 4, sources-disagree on the Pharaoh card. Figures equal `/api/v1/supply-analyzer/batch/gem-screener` (yearly_range 51.08-66.42, pressure 1, Flooding, free 30.76M, staked 498.5M, reserve 470.7M, dilution 16.85%/wk). The range is red |
| C18 (7) | "Guardians", 6 rows, name + ring + mark | PASS | Rug power, Holders paid, Thin liquidity, Price run, Security, Team. Each row's text is only its name; ring `.ckc` plus a `.gdmark` (?, !, ✓, ✗) |
| C19 (7) | summary line; numbers only in the tooltip | PASS | Collector Crypt "3 red · 2 clear · 1 not checked". Focusing Price run shows the tooltip "Price run BAD +95% in 30 days…" (API price_run 95.08) |
| C20 (7) | Security is the worse of audit/hacks; no green without data (dashed) | PASS | Pharaoh: audit bad + hacks good gives Security red. Not-checked rows have a `dashed` ring. 3 coins checked against API `dlevel.checks`, all match |
| C21 (7) | removed checks are out; no table gained a column | PASS | Exactly 6 rows. Apps 12 columns, Chains 11, Sectors 7 |
| C22 (8) | project cell: no (i), no "No holder share", nothing else; the name still opens the detail | PASS | All 119 rows under "All by upside": the only extra element in the cell is the smiley. Clicking the name opens `?coin=pharaoh-exchange` |
| C23 (8) | smiley is one circle, shown only when `reaches_you` is green | PASS | SVG has one `circle r=6.2` outline + 2 eyes + smile; the span has no border or shadow. 31 of 31 table rows match the API verdict (40 green of 232 records; 31 of them are in the table) |
| C24 (8) | smiley tooltip is one line with the share; nothing otherwise | PASS | e.g. StonkFun "Holders get 50% of revenue" (holders_share 0.5036). Lido 70% (0.6984) |
| C25 (9) | mouse: one click opens the sector | PASS | At 1360, a click on the AI bubble opened the AI sector panel |
| C26 (9) | touch: first tap shows the card, second opens | PASS | At 390 with touch: tap 1 showed "AI · Hot" with no panel; tap 2 opened the AI panel |
| C27 (9) | captions for touch and mouse | PASS | Touch: "…Tap a bubble for its card, tap again to open the sector." Mouse: "…Click a bubble for the sector." |
| C28 (10) | year chart follows the filter (Apps 3, Chains 2) | PASS | Apps: "Top 10 by upside of 93 vetted." / "The 7 Degen picks." / "of 119, vetted or not". Chains: "of 24 vetted." / "of 33, vetted or not"; the legend equals the table's top 10 |
| C29 (10) | title and caption say what is shown; Degen picks shows only the picks | PASS | "The Degen picks: their year": Solv, Collector Crypt, Bankr, GMX, Definitive, o1.exchange, Spark (= `/picks`) |
| C30 (11) | chip with rocket disc and arrow, yellow, opens launchpad in a new tab | PASS | `a.lchip` → https://cymetica.com/launchpad `target=_blank`. Border and label `rgb(255,214,10)`, disc bg `rgb(255,214,10)`, bg `rgb(10,14,23)` |
| C31 (11) | yellow nowhere else; under 560 the chip reads "Launch" | PASS | Hue scan (38-65°) of every visible element on 4 tabs at 1360: 0 hits outside the chip. At 390 the text is "Launch" and aria-label stays "Launch your own memecoin" |
| C36 (13) | shields keep 92:110, about 78 px tall, undistorted | PASS | Apps and Chains SVGs are 101x78 with viewBox 316x244 (ratio 1.295 = 1.295) and `xMidYMid meet`. The shield is 204x244 units, i.e. 92:110 |
| C37 (14) | header and values line up | PASS | th and td `text-align` match in every column: Apps (centre 0 px offset, Chart included), Chains. Widths: no baseline |
| C38 (15) | corner tints in stage colours at 6 %, fading | PASS | radialGradients: hot `#00ff88` cx1 cy0, emerging `#00cfff` 0,0, fading `#3b82f6` 1,1, falling `#ff4444` 0,1; stop-opacity .06 → 0 |
| C39 (15) | lines, bubbles, tails and labels keep their contrast | PASS | The tint rects are drawn first (SVG child 49, before lines 54 and circles 77) |
| C40 (16) | percentage and a neutral arrow; points in the tooltip | PASS | "2.9% ↑" and "3.0% ↓" in `rgb(169,184,204)`. Tooltip: "29 of 1008 people… Change from the week before: +0.5 pts" (29/1008 = 2.88%) |
| C41 (16) | "too few" below 20 people | PASS | 10 of 12 rows show "too few" (DePIN 19, Infrastructure 17 … Prediction 2). Gaming 29 and DEX 30 are shown |
| C44 (18a) | Top Picks fund = Degen picks at equal weight after the rebalance | PASS | Oct 5 rebalance: members CARDS, SOLV, MNDE, O, GMX, EDGE, MET (= the 10-04 picks in the spec), 14.29% each. This rebalance came before shipping; the first one after shipping is Oct 12 |
| C45 (18) | fund page shows last and next date plus the swap history | PASS | aib-gs-picks: "Last rebalance 5 Oct 2026 · next 12 Oct 2026." "5 Oct 2026: out FXN, KNC, NEST, UP · in CARDS, GMX, MET, MNDE, O" |
| C46 (18b) | sector card tooltip = fund page list + rule + dates | PASS | AI NEAR, TAO, ICP, VVV, RENDER; RWA LINK, XLM, QNT, ONDO, ALGO; L2 ARB, STRK, OP, ZK, SOON. Both say "the sector's 5 largest coins by market cap that can be priced and bought on-chain, equal weight" and give Oct 5 / Oct 12 |
| C48 (18e) | "not invested yet" on the fund page and on its Top Picks card | PASS | All 4 funds show "RETURN SINCE INCEPTION not invested yet" with the "has not bought its assets yet" line, and so do all 4 cards. The return still appears in two places: on first paint (L2 "-7.52%" before JS), and in `og:description` (picks "+4.77% since inception", L2 "-7.52%") |
| C50 (19) | 390: picks on the first screen | PASS | First card at top 260 px on Apps and Chains, 360 px on Sectors (the viewport is 844) |
| C51 (19) | charts open on request, fit, don't pan | PASS | "Year in a chart" toggle (aria-expanded false→true) gives a 313x320 chart. "Rotation map" gives 312x470. No scrolling container; scrollWidth 390 |
| C52 (20) | one card per project; the face fields; "More" | PASS | Apps face: 7/10, $3.3M, $2.7M, >50x, IGNITION 98, "More". Chains face: $301.4M, adoption 78.0M, 35x, SLOWING, no meter |
| C53 (20) | sort and filters in one control, one sheet | PASS | "Sort and filter" (44 px) opens `.phsheet`: sort options, Vetted/Degen/All and min revenue |
| C54 (21) | sectors as cards grouped by stage, with 1M/3M vs the median and fundamentals | PASS | Groups EMERGING 2, HOT 4, FADING 2, FALLING 4. A card shows 1M, 3M, Talked about, Fundamentals, Growth 3M |
| C55 (21) | map: tap 1 shows the card, tap 2 opens the sector | PASS | Same as C26 |
| C56 (22) | pinned header plus filters at most 110 px | PASS | Apps 94, Chains 94, Sectors 45, Top Picks 45 |
| C59 (22) | items 19-22 change nothing above 640 px; their CSS is in `@media (max-width:640px)` | PASS | The phone style block's only top-level rule is `@media (max-width:640px)`. Phone controls are hidden at 1360 |
| BB-1 | live data over a real-time connection | PASS | `new WebSocket(…/ws/gem-screener)`; `#liveState.on` "Live" |
| BB-2 | a plain statement of what it does NOT do | PASS | "About this version: … what it does not do"; `/status` `does_not` (8 lines) |
| BB-3 | own names and branding | PASS | Gem Screener · by CyMetica (the requester's own product name) |

## Outside the ticket (seen in passing)

- The Supply Analyzer reports StonkFun as "Sellable tokens shrink -130% to -114% a year": `yearly_range [-129.65, -114.31]` in the batch. A pile cannot shrink by more than 100%. That is the Supply Analyzer's defect, not this page's.
- The smiley on Pons and edgeX reads "Holders get a share of revenue" with no figure, because `holders_share` is null.
