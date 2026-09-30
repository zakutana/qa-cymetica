# Gem Screener follow-up: what the operator wants changed (for the agent that writes the spec)

Source: the operator's complaints on the live site after ET-28378, 2026-09-30, each checked against the specs and the live page (`et28378-complaints.md`, `et28378-verify.md`). Goals, not methods: how it is built is the vendor's call. Wording is English so it can go to the spec agent as it stands.

## A. Still open from ET-28378, part 4 (the fail note on the board)

1. The Degen meter is one colour, in the Apps row and in the detail. Spec 4 A.1: segments green 1-3, light blue 4-6, red 7-10, as in the reference screenshots. The detail meter must also be wide, like the reference (live: 216 of 783 px).
2. Four of the 18 checks never run for any app (hidden supply, insider flow, whales, team); 196 of 215 ranges are wider than two levels (91%). Build them, so that most ranges shrink to one or two levels.
3. Check circles: the tooltip is the card of spec 4 C.5 (icon, name, verdict pill, value, context, source and date), never the old light box.
4. The Supply card must agree with the page: Pharaoh (PHAR) says "0.0% of the float a week" and "No new tokens in 30 days" while emissions are $1.26M and net revenue is +$1.1M; Curve the same.
5. Trajectory stepper in the detail takes the colour of the Trend check (light blue for Ignition).
6. The Legend lists only icons that still exist; today it still has Micro, New, Post-crash, Declining, No trend, Stale data, Thin liquidity, Cliff and % in 90d, and no row shows them.
7. Report section names stay as the spec says ("The bet"), or the change is agreed first.
8. As the vendor listed itself: the Curve emission mismatch, Legend entries of 8 words or fewer, and the Audit set as the spec says.

## B. New wishes

9. One tooltip style everywhere in the app (the card of A.3), including tiles, the Revenue tile, table cells and the Legend. No browser-native tooltips left.
10. Apps table: fits a 1360 px window without sideways scrolling (live: 1593 px in a 1294 px box, still scrolling at 1920). Idea from the operator: the long blue "32x if all tokens were out" text under Upside becomes a small symbol with a tooltip.
11. Chains table: readable columns. The number columns are 80 to 95 px and their headers break over two or three lines, while Trajectory takes 369 px at 1360.
12. Chains tab: drop the share from the Layer, Share, Theme cell (Apps keep theirs).
13. Chains are priced on adoption, Apps on revenue. Design the best algorithm you can to measure a chain's adoption (method and data are yours): say how it resists wash trading and incentives, and how chains with very low fees are treated. Yearly activity fees say what users paid, not how many use the chain. The price-tag line and the Upside of chains follow that measure.
14. Supply card: degen-friendly. Fewer words, no "not available" paragraphs, the number first.
15. Degen report: the one way to get a report is "Ask for Degen report" on the page, which researches, fills the dashed circles and narrows the level's range. Remove the "Ask NEXUS about this coin" chat prompt from the card; a Nexus answer never fills anything. Today "Ask for Degen report" shows only on coins without a report (YFI, XVS); on coins that already have one (PHAR, NEST, UP, MNDE) the card carries only the Nexus button, so the visitor sees no way to ask. The card also sits about 3,200 px down the detail, at the very bottom.
16. Asking for a Degen report needs a Pro plan or higher (NEXUS build plans). Reading a finished report stays free.
17. The Trajectory cell in the Apps table uses the same colour as the detail (today: a green glow in the table, and light blue in the detail).
18. Chart card: remove the Copy button; "Open in Chart Analyzer" stays.
19. Altseason panel: the Expand button is easier to see.
20. Altseason slider: "Calm" and "Week of Sep 28" are not understood; say the same thing so anybody gets it. Draw the slider as the three-segment scale with a marker used in the coin's Chart card (bands: below 35, below 70, 70 and up).
21. Sectors: the wide text tags (Hot now, Already leading, Beaten down but turning, Fundamentals rising) become small icons with a tooltip, as in the coin detail and in Apps. The Legend and the "Hot sectors" cards on Top Picks follow.
22. Top Picks fund line: remove "CyMetica-managed" (it stands twice on one line).
23. The price-tag lines on Apps ("Hyperliquid is priced at 33x its yearly revenue...") and Chains become a bigger, dense stamp with the explanation in a tooltip.

24. Top Picks, the chart "Revenue over 12 months, start = 100. Top 10 by upside": on a wide screen (about 2000 px) there is a large empty gap between the end of the lines and the legend on the right. The chart uses the width, or the legend sits next to it.

25. The report status icon in the detail header: a ready report glows green (today it is a plain grey outline, hard to tell from "not researched" except for dashed against solid). Not researched stays a dashed grey outline; outdated is a solid outline in light blue with a dot, as in the reference. Spec 4 C.1 names only dashed, solid and solid with a dot; the reference draws ready in its accent colour with a soft fill. Clicking the icon scrolls to the report card (it does today, for every state); when nothing is researched the card it lands on carries the "Ask for Degen report" button, and the tooltip says so, not "Opens the report below."

## Before it is filed

- The vendor answered (2026-09-30): a fail note is kept as the QA record on the ticket (checked: `verdict_note` is on ET-28378) but does not schedule any build work; a new request is the reliable way, and it opens a follow-up ticket linked to the original. So lines 1 to 8 stay in the new request.
- Check the new spec against this list line by line (as with ET-27671: no line lost), then file. One open request per app: ET-28378 has shipped, so a new one is a follow-up ticket.
- Filing needs `build-it-better.key`, which is not in a cloud session.
