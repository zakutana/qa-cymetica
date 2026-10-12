# Agent Tournaments, next release: spec in progress (draft, not filed)

Started 2026-10-12 on the operator's word ("dem tvorit novy spec na dalsi release"). Items are added as the operator names them; filing is the operator's step, on the Build it Better form as "It exists" with `https://cymetica.com/agent-tournaments` (a follow-up to ET-30773). Pictures: `pick-the-winner.png` from this folder (the form takes at most six). The mock's source is `pick-the-winner.html`, drawn in the site's palette (navy, cyan, green, red, blue; none of the colours their "Colors -- mandatory" rule forbids) and the site's fonts.

## Items so far

1. **Flash tables (1 day).** The operator does not want to wait a week for a result.
2. **ET10 tables, no paper money.** Buy-in 100 ET10 or 1,000 ET10.
3. **Top agents: "now" runs out of the card.** On the live lobby (2026-10-12) the ROI line "+132.95% now" spills past each card's right edge.
4. **Pick the winner: a nicer design.** Mock: `pick-the-winner.png`.

## Request text (paste into "What should it do better?", one item per line)

```
Agent Tournaments (live at /agent-tournaments), follow-up to ET-30773: two new kinds of table and two fixes on the page. The mockup is attached; where the page and the mockup differ, the mockup wins. How you build it is your call.
Flash tables: tables that run 1 day instead of 7, so an owner knows the result the next day. Same seats, approval and rules as today, with the volume and prize rules scaled to one day as you see fit; on the lobby with a FLASH chip, a Flash filter beside All / $5 / $50 / Mine, the countdown in hours, and Results the moment the day ends. A new Flash table opens whenever one fills, like the 7-day tiers.
ET10 tables, no paper money: tournaments whose buy-in, pot and prizes are ET10, at two buy-ins, 100 ET10 and 1,000 ET10. The pot is paid to the top three in ET10 and credited to the owner's balance the way the Agent League pays its prizes; the deal panel, the table card and Results say ET10 wherever they say USDC today.
Top agents (lobby): the ROI line runs out of the card -- on 12 Oct "+132.95% now" spills past the right edge of every card at 1440 px. Keep the ROI and "now" inside the card at every width (mockup, top row: the ROI on its own line under a divider, "NOW" small beside it, long names cut with an ellipsis, the medal on the avatar's corner).
Pick the winner, a new design (mockup, table 2's real picks): the ten bots as cards ranked by ROI now, each with its ROI, a bar for its share of the pool, its picks and stake, and what a correct pick pays (1.06x, 17.00x, or WHOLE POOL when nobody has picked it); a deleted bot dimmed and tagged; clicking a card selects it (green border, YOUR PICK). Above them the pool and the number of picks, and a countdown chip "PICKS CLOSE IN 21H 14M"; the rule in one line with a tooltip. Below them one slip: the chosen bot, amount chips 10 / 50 / 100 / 250 / other, and before the click "If it wins: +$170 -- you take $220: your 50 back and the whole pool", then PICK.
```

## Notes

- Item 2 is real value: ET10 is credited and withdrawable (the Agent League's terms). Their own line today is that live-money tables wait on "entry and prize terms that still have to be set" (REPLY-0154); whether an ET10 buy-in counts as one is theirs to decide, and the request does not argue it.
- Numbers in the mock are table 2's on 2026-10-12 (pool 170 paper USDC from 4 picks: 3 on House Ichimoku Empress for 160, 1 on PaperRSI for 10); the countdown and the selected bot are sample state.
