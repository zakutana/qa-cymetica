# Build request: Gem Screener, changes after ET-28378 (cymetica.com/gem-screener)

**For:** the lead agent of the Cymetica SDLC pipeline
**From:** Adam (product owner, Gem Screener)
**Scope:** the open changes to the Gem Screener app after ET-28378. Everything here is about what a degen sees and can rely on. Build or change only what is named; leave the rest of the app as it is.

> **HOW TO READ THIS SPEC**
> 1. **Goals, not methods.** How you build it is your call: data, formulas, thresholds, components. Where an item gives a rule or a number, it is a good default, and you may improve it; say what you changed and why in your spec.
> 2. **Every number is read from the live site on 2026-09-30** (snapshot of 18:50 UTC, 215 apps, 26 chains, 12 sectors). They are there so you can check that a change took effect; they are not the requirement.
> 3. **English only**, degen-friendly: the number first, plain short words, no statistics jargon on the page, every explanation in a tooltip or behind an expand.
> 4. **Keep the look.** The owner likes the current design: the circles, the tooltip card (C.5), the check rows by area, the Degen meter, the tables and the layout. Change only what an item names. Where an item is about the circles and their tooltips (43, 44, 45), the look stays exactly as it is: what changes is which checks there are, what their texts say, and the caution colour.
> 5. **Item numbers are stable** (the list was worked on before it was written down here); 26 and 27 were merged into 37 and do not appear.

## What is already done from ET-28378 part 4 (do not redo)

The Degen meter colours and width (A.1), the check circles with the C.5 card (A.3), the Supply card agreeing with the page for Pharaoh and Curve (A.4), the trajectory stepper colour (A.5), "The bet" section name (A.7), and the new checks: hidden supply, whales, insider flow and team now run (after the 18:50 refresh: hidden supply on 113, insider flow on 97 and team on 72 of 215 apps). What remains of that part is in items 38, 39 and 42.

---

## 1. Apps tab and Top Picks

**[10] Apps table fits a 1360 px window without sideways scrolling** (live: 1593 px in a 1294 px box, still scrolling at 1920). Idea from the product owner: the long blue "32x if all tokens were out" text under Upside becomes a small symbol with a tooltip. Fewer columns is the other half: the Growth 6M column goes (the 12-month revenue chart shows the growth and the Trajectory column, Ignition and so on, already says it).

**[17] The Trajectory cell in the Apps table uses the same colour as the detail** (today: a green glow in the table, and light blue in the detail).

**[23] The price-tag lines** on Apps ("Hyperliquid is priced at 33x its yearly revenue...") and on Chains become a bigger, dense stamp with the explanation in a tooltip.

**[22] Top Picks fund line: remove "CyMetica-managed"** (it stands twice on one line).

**[24] Top Picks, the chart "Revenue over 12 months, start = 100. Top 10 by upside":** on a wide screen (about 2000 px) the lines stop halfway and leave a large empty space before the legend on the right. The chart uses the full width, or the legend sits next to it.

**[30] An upside a holder can rely on.** A coin with 4 % of its tokens out shows 44x (UP) and is 8x with all tokens out (PHAR 50x, 31x). The headline must not flatter a coin with few tokens out. The 11 apps at the 50x cap stand at 72x to 2,291x; keep their order.

**[31] Top Picks show their warnings on the pick, not only in its detail:** an exit flag (NEST, SOLV), earnings below emissions (NEST -$213K, UP -$762K a month), under 180 days of history (UP, 81 days).

**[32] Liquidity a degen can use.** SOLV, MNDE and LISTA pass the liquidity gate on 24-hour volume while their on-chain pools hold $20K to $31K (a $10K buy moves the price 64 to 100 %). Say where the liquidity is and how deep.

**[33] Data age on every row.** The supply behind 168 of 215 rows is 43 hours old and no row shows its age. A market cap a fifth off is how a degen overpays (PHAR $4.1M, $3.3M at CoinGecko). Read supply fresh and show each row's age.

**[38] Degen level.** 124 of 215 ranges span more than two steps (PHAR 5 to 9) and an unchecked item counts as half a risk. A low level must not hide a high one: show the worst case and what is unchecked.

## 2. Chains tab

**[11] Readable columns.** The number columns are 80 to 95 px and their headers break over two or three lines, while Trajectory takes 369 px at 1360. The Growth 6M column goes here too, for the same reason as on Apps.

**[12] Drop the share from the Layer, Share, Theme cell** (Apps keep theirs).

**[13] Chains are priced on adoption, Apps on revenue.** Design the best algorithm you can to show a chain's TRUE adoption (method and data are yours): say how it resists wash trading and incentives, and how chains with very low fees are treated. Yearly activity fees say what users paid, not how many use the chain. The price-tag line and the Upside of chains follow that measure.

## 3. Coin detail

**[14] Supply card: degen-friendly.** Fewer words, no "not available" paragraphs, the number first. And in colour: today the card is all grey. Colour the float and not-out parts, the weekly mint and the revenue cover.

**[15] Degen report.** The one way to get a report is "Ask for Degen report" on the page, which researches, fills the dashed circles and narrows the level's range. Remove the "Ask NEXUS about this coin" chat prompt from the card; a Nexus answer never fills anything. Today "Ask for Degen report" shows only on coins without a report (YFI, XVS); on coins that already have one (PHAR, NEST, UP, MNDE) the card carries only the Nexus button, so the visitor sees no way to ask. The card also sits about 3,200 px down the detail, at the very bottom.

**[16] Asking for a Degen report needs a Pro plan or higher** (NEXUS build plans). Reading a finished report stays free.

**[18] Chart card: remove the Copy button;** "Open in Chart Analyzer" stays.

**[25] The report status icon in the detail header.** A ready report glows green (today it is a plain grey outline, hard to tell from "not researched" except for dashed against solid). Not researched stays a dashed grey outline; outdated is a solid outline in light blue with a dot, as in the reference. Spec 4 C.1 names only dashed, solid and solid with a dot; the reference draws ready in its accent colour with a soft fill. Clicking the icon scrolls to the report card (it does today, for every state); when nothing is researched the card it lands on carries the "Ask for Degen report" button, and the tooltip says so, not "Opens the report below."

**[39] Audit check.** "Audits listed" (yellow) and "None listed" (red) tell a degen little. Say in a few words what an audit actually covers (the token contract, the vault, a fork of someone else's code), and what "None listed" means for this coin. A reader should know at a glance whether the audit is about the thing they are buying.

**[40] Trajectory phase.** On a coin detail the pill at the top of the panel is green while the stepper under it is light blue for the same phase (Pharaoh, Ignition). One phase, one colour, in the table, the pill and the stepper.

**[43] The checks, cut to what a degen needs.** Today 18 checks feed six areas (Control 2.5, Supply 2, Earnings 2, Liquidity 1.5, Heat 1, History 1 of 10) and the level is ten times their weighted mean, so the circles are the level. On 96 coins read on 2026-09-30 an average of 5.9 of the 18 are "Not scanned" and count as half a risk, and several circles light up on nearly every coin and so say nothing: "Admin can mint" on 44 of 74 scanned, "Timelock" green on 1 coin, "Audit" green on 1 of 96, "Market cap" under $20M on 72 of 96 (the screener is for small caps). Cut to the questions a degen asks: can the owner rug it (owner type, timelock and mint power as ONE check; "can mint" alone is not a warning); what new tokens are coming (emissions, unlocks in 90 days and the share of tokens out together); does it earn after paying emissions; is it growing; do holders get a share; can I get out (slippage on $10K; market cap as a plain number, not a verdict); already pumped (30-day price run, and price against revenue); is it legit (audit, hacks). Whales, insider flow, hidden supply and team stay, but as one dashed group "Not checked yet" with the "Ask for Degen report" button, until they run for most coins. Weigh the areas by what a degen can lose on: Control weighs most (2.5) while two of its three checks are not scanned on about half the coins. **The level is recomputed from the new set of checks:** say how (the weights, how a check that was not scanned counts: as today it widens the range and never counts as good) and show before and after for the 215 apps, how many change by two steps or more and why. The level stays display only, as today.

**[44] The line at the end of each check row** says the key number in plain words, in the colour of its worst check, and the reason for the colour is in the tooltip. Today Supply reads "Unlocks 0.0% unlocks in 90 days, 6.8% of tokens out" in red: nothing unlocks in 90 days, but only 6.8 % of tokens are out (FDV is 14.7× market cap), so the red is the 93 % still to come, which the line never says. Say "7% of tokens out (FDV 15× market cap), 0% unlock in 90 days". Earnings reads "Trend Ignition, 3.6× spike" for a business that earns $2.5M a month and nets +$1.2M after $1.3M of new tokens, and its circle shows "2.0×" for a real value of 1.96, just under where green starts. Say "Earns $2.5M a month, $1.3M goes out as new tokens: +$1.2M", and for the trend "Revenue 3.6× its usual month, one month so far". No jargon (Ignition, spike) on the line.

## 4. Altseason panel

**[19] The Expand button is easier to see: make it green.**

**[20] The slider.** "Calm" and "Week of Sep 28" are not understood; say the same thing so anybody gets it. Draw the slider as the three-segment scale with a marker used in the coin's Chart card (bands: below 35, below 70, 70 and up).

**[34] The latest reading beside the mean.** "49 % of the top 50 alts beat BTC" is the mean of the last four weeks; the latest week is 68 %, three months ago 22 %. Show the latest reading beside the mean.

**[35] The universe.** Three of the 50 "alts" are not alts (a home-equity-loan token, USYC, a euro fund), each under 3 % a month, and they shift breadth by up to 6 points. Leave assets priced at a currency unit out.

## 5. Sectors tab

**[36] Where each sector is in its rotation.** In an altseason sectors rotate every few months, and a degen must see the ones starting to rise and the ones fading. Today "Hot now" sits on 10 of 12 because everything beats BTC (10 of 12 beat the median alt too). Compare each sector with the median sector and give it a stage: Emerging (below it over 3 months, above over 1), Hot (above on both), Fading (above over 3, below over 1), Falling (below on both). Show the rule in a tooltip; improve it if you can. On the 2026-09-30 numbers this gives Hot: L2, DEX & perps, DePIN, RWA, Privacy; Emerging: AI; Fading: DeFi lending & staking; Falling: Memecoins, Gaming, Infrastructure, Prediction markets, L1.

**[37] The chart and the table.** The four-quadrant chart shows these stages (3-month strength across, 1-month momentum up), a bubble per sector with a trail to where it stood four weeks ago; its names, quadrants and legend are clear and in colour (today the words in the background and the legend are grey and barely visible, and some labels sit away from their bubble: DEX & perps, DeFi lending & staking, Privacy). The table is sorted by stage, one colour each, with only: stage, 1M, 3M, Talked about, Fundamentals, Growth 3M. The Alt sensitivity column and both vs BTC columns leave the table.

**[21] The wide green text tags** in the Theme column (Hot now, Already leading, Beaten down but turning, Fundamentals rising; L2 carries three side by side) become small icons with a tooltip, as in the coin detail and in Apps. The Legend and the "Hot sectors" cards on Top Picks follow.

## 6. The whole app

**[9] One tooltip style everywhere** (the card of A.3), including tiles, the Revenue tile, table cells and the Legend. No browser-native tooltips left.

**[28] Go through the whole app** and make sure everything is degen friendly: the number first, plain short words, no statistics jargon on the page (beta, alpha, error bars, r-squared), every explanation in a tooltip or behind an expand.

**[29] One look everywhere:** the same tooltip, the same badge and the same symbol style on every tab and in every panel, so the same thing never looks different on another page. Pick one of each and use it throughout.

**[45] Caution is orange, not light blue:** green, orange, red, and blue-grey only for neutral or does not apply. Light blue looks neutral and sits beside "Does not apply" in the Legend. The same colours on the Degen meter (zone 4 to 6), the tags and the Legend. This changes spec 4 A.1, which says light blue for 4 to 6.

**[42] The Legend shows only what the open tab shows.** On Apps it lists Post-crash, Declining, No data and Thin liquidity, which only the Chains tab draws (4, 3, 5 and 1 of 26 chains; none of the 215 Apps rows, whose flags moved into the Degen meter and the checks), and "Tradeable here", which no row carries (the exchange lists 11 pairs, none a listed coin). The two tabs should not mark the same kind of warning in two different ways.

## 7. Agent access

**[41] The full list for an agent.** `GET /api/v1/gem-screener/ranked` takes `limit` up to 100 and ignores `offset`, so an agent cannot list all 215 apps without the 2 MB snapshot. Let it page the full list.

---

## Checklist (one line each; done when all are true)

- [ ] 9 No browser-native tooltip is left anywhere; one card style.
- [ ] 10 Apps table: no sideways scroll at 1360 px; no Growth 6M column; the "if all tokens were out" text is a symbol with a tooltip.
- [ ] 11 Chains table: number-column headers on one line; Trajectory no wider than its content; no Growth 6M column.
- [ ] 12 Chains: no share in the Layer, Share, Theme cell.
- [ ] 13 Chains: adoption measure documented (wash trading, incentives, very low fees); the price-tag line and Upside use it.
- [ ] 14 Supply card: coloured, number first, no "not available" paragraphs.
- [ ] 15 "Ask for Degen report" on every coin, near the top; no "Ask NEXUS" prompt on the card.
- [ ] 16 A Pro plan or higher is needed to ask; reading a finished report is free.
- [ ] 17 Trajectory: same colour in the table and the detail.
- [ ] 18 No Copy button; "Open in Chart Analyzer" stays.
- [ ] 19 Altseason Expand button is green.
- [ ] 20 Altseason slider: plain words; three-segment scale with a marker (35 and 70).
- [ ] 21 Sector tags are small icons with a tooltip (Theme column, Legend, Top Picks cards).
- [ ] 22 "CyMetica-managed" appears once, or not at all, on the fund line.
- [ ] 23 Price-tag lines are a bigger, dense stamp with the explanation in a tooltip.
- [ ] 24 Top Picks revenue chart uses the full width on a 2000 px screen.
- [ ] 25 Report status icon: ready glows green; not researched dashed grey; outdated solid light blue with a dot; the tooltip says what a click does.
- [ ] 28 No statistics jargon on the page; explanations behind a tooltip or an expand.
- [ ] 29 One tooltip, one badge, one symbol style on every tab and panel.
- [ ] 30 The headline upside does not flatter a coin with few tokens out; capped rows keep their order.
- [ ] 31 Top Picks show exit flag, earnings below emissions and young history on the pick itself.
- [ ] 32 A pick says where its liquidity is and how deep.
- [ ] 33 Each row shows the age of its data; supply is read fresh.
- [ ] 34 The altseason panel shows the latest reading beside the four-week mean.
- [ ] 35 The altseason universe has no asset priced at a currency unit.
- [ ] 36 Every sector has one of four stages against the median sector; the rule is in a tooltip.
- [ ] 37 Sectors chart: four quadrants with stage names, a bubble and a four-week trail per sector, readable in colour; the table has only stage, 1M, 3M, Talked about, Fundamentals, Growth 3M, sorted by stage.
- [ ] 38 The level shows the worst case of its range and what is unchecked.
- [ ] 39 The audit check says what the audit covers and what "None listed" means.
- [ ] 40 One phase, one colour: table, pill and stepper.
- [ ] 41 `ranked` pages through all 215 apps.
- [ ] 42 The Legend lists only flags the open tab draws; Apps and Chains mark warnings the same way.
- [ ] 43 The check panel asks about ten questions, not 18; whales, insider flow, hidden supply and team sit in one dashed "Not checked yet" group with the report button; the weights are explained in a tooltip; the level is recomputed with a before and after for the 215 apps.
- [ ] 44 Each check row ends in one plain line with the key number (the Supply and Earnings examples above), in the colour of its worst check, with the reason in the tooltip; no jargon.
- [ ] 45 Caution is orange everywhere (circles, Degen meter zone 4 to 6, tags, Legend); blue-grey is only neutral or does not apply.
- [ ] 43 to 45 The circles, the tooltip card and the row layout look as before: only the set of checks, the texts and the caution colour differ.
