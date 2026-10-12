# Agent Tournaments, next release: spec (ready to file, not filed)

Started 2026-10-12 on the operator's word ("dem tvorit novy spec na dalsi release"); the operator asked to file it the same evening. Filing is the operator's step, on the Build it Better form as "It exists" with `https://cymetica.com/agent-tournaments` (a follow-up to ET-30773). Picture: `pick-the-winner.png` from this folder (the form takes at most six). The mock's source is `pick-the-winner.html`, drawn in the site's palette (navy, cyan, green, red, blue; none of the colours their "Colors -- mandatory" rule forbids) and the site's fonts.

## Items

1. **Flash tables (1 day).** The operator does not want to wait a week for a result.
2. **ET10 tables, no paper money.** Buy-in 100 ET10 or 1,000 ET10.
3. **Top agents: "now" runs out of the card.** On the live lobby (2026-10-12) the ROI line "+132.95% now" spills past each card's right edge.
4. **Pick the winner: a nicer, simpler design.** Mock: `pick-the-winner.png` (the first draft, ten cards, was too busy: the operator, "strasne slozite a preplacane").
5. **An agent that finds Cymetica wants to play at once.** Read 2026-10-12 ~20:55 UTC: the MCP `initialize` instructions and tool list have no tournament (`/.well-known/mcp`), the agent card (`/.well-known/agent.json`, `agent-card.json`) does not mention it, llms.txt names it at line 17 of 1,300; /build and /api-docs do mention it.

## Request text (paste into "What should it do better?", one item per line)

```
Agent Tournaments (live at /agent-tournaments), follow-up to ET-30773: two new kinds of table, two fixes on the page, and a front door for AI agents. The mockup is attached; where the page and the mockup differ, the mockup wins. How you build it is your call.
Flash tables: tables that run 1 day instead of 7, so an owner knows the result the next day. Same seats, approval and rules as today, with the volume and prize rules scaled to one day as you see fit; on the lobby with a FLASH chip, a Flash filter beside All / $5 / $50 / Mine, the countdown in hours, and Results the moment the day ends. A new Flash table opens whenever one fills, like the 7-day tiers.
ET10 tables, no paper money: tournaments whose buy-in, pot and prizes are ET10, at two buy-ins, 100 ET10 and 1,000 ET10. The pot is paid to the top three in ET10 and credited to the owner's balance the way the Agent League pays its prizes; the deal panel, the table card and Results say ET10 wherever they say USDC today.
Top agents (lobby): the ROI line runs out of the card -- on 12 Oct "+132.95% now" spills past the right edge of every card at 1440 px. Keep the ROI and "now" inside the card at every width (mockup, top row: the ROI on its own line under a divider, "NOW" small beside it, long names cut with an ellipsis, the medal on the avatar's corner).
Pick the winner, simpler (mockup, table 2's real picks): the title with the pool ("$170 pool") and "CLOSES IN 21H" on the right; the bots as a short list ranked by ROI now -- a radio, the avatar, the name, the ROI, and what a correct pick pays ("pays 1.06x", or "pays the pool" when nobody has picked it) -- the top five with "SHOW ALL 10"; under it amount chips 10 / 50 / 100, the win before the click ("+$170 if Trend Titan wins") and one PICK button. No other text on the card; the rule (pool shared among correct picks, no fee, stakes back if nobody picked the winner) goes in a tooltip.
AI agents that find Cymetica should want to play at once, and be able to in one step. Today (12 Oct) an agent learns of the tournaments only from llms.txt: the MCP initialize instructions and tool list do not name them, and the agent card (/.well-known/agent.json) does not either. Wanted: the MCP initialize instructions open with the tournaments in one line (10 AI agents, 7 days or 1 day, best ROI takes the pot) and how to join; MCP tools to see the open tables, take a seat and follow the seat's rank and ROI; an Agent Tournaments skill first on the agent card; and one call that does it all for an agent with a fresh API key -- picks an open table of the buy-in it asks for, clones the best bot by backtest when it has none, requests the seat and returns the approve link for its owner. The owner still approves every seat; nothing spends on its own.
```

## Notes

- Item 2 is real value: ET10 is credited and withdrawable (the Agent League's terms). Their own line today is that live-money tables wait on "entry and prize terms that still have to be set" (REPLY-0154); whether an ET10 buy-in counts as one is theirs to decide, and the request does not argue it.
- Numbers in the mock are table 2's on 2026-10-12 (pool 170 paper USDC from 4 picks: 3 on House Ichimoku Empress for 160, 1 on PaperRSI for 10); the countdown and the selected bot are sample state.
