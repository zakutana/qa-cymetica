# Build it Better: Agent Tournaments, a control panel at the table

**Filed by the operator on the form, 2026-10-14.** Their BB-SPEC carries all 27 lines word for word (diffed, numbering aside) and the five pictures as design references; its closing template paragraph is the #192 clause, which line 1 overrides. BB-ACCEPT without a BB-CHANGE. ET-31263 is closed (shipped, verdict pass, read 2026-10-14), so a new request on `cymetica.com/agent-tournaments` is possible.

The operator, 2026-10-14, after ET-31263: *"ta hlaska uz neplati vymysli novou. to pod tim taky nevypada moc pekne uz moc kosticek. U stolu jim precnivaji stitky. Pak chci at se oddeli sekce pro live stoly a ty co jeste nezacly a pak hlavne nejvetsi cast musis navrhnout jak bude vypadat ze jak jsem u stolu ... behem turnaje budu moct upravovat strategii botu. ted jede jen ty BTC a ETH trejdy coz je trapny ... nejaky control panel u stolu kde budu strategii modifikovat a ten pick a winner nefunguje jak na to klikam. Pak jeste sam projdi celou apku"*. Goals are theirs; the design is ours, their veto open.

What we read (reads only, 2026-10-14 ~08:00 UTC): table 5's bots trade 5-minute BTC and ETH rounds; a clone's own page, /clone/{id}, already sets which market lanes it trades and its stop loss and take profit (`PATCH /api/v1/cloned-bots/{instance_id}/settings`: `perpetual_markets`, `custom_markets`, `event_card_trading_enabled`, `arena_trading_enabled`, `catalog_trading_enabled`, `stop_loss_pct`, `take_profit_pct` and 24 more); table 5's picks closed 13 Oct 18:49 UTC (`picks.open: false`) while the page shows "CLOSES IN NOW" over ten disabled radios (`docs/et-31263-verification.md`, item 4).

**Corrected the same morning.** The first draft said an owner could change only a bot's name and avatar and drew a panel of invented strategy sliders; that came off the species route (`PATCH /backtest/bots/{slug}/settings`), not the clone's. The operator sent screenshots of /clone/{id} and asked for the panel to be only what already works: the market lanes on or off, stop loss and take profit. Rebuilt so.

Item 9: changes count forward only and are logged publicly (that, not what); house bots stay fixed as the benchmark. A daily cap of 3 changes was in the draft; the operator removed it: *"zmen si muze delat kazdy kolik chce behem turnaje ... zadna omezeni"*. The headline is theirs too ("10 agents, 1 table ..."), kept true: the pot is split 60 / 30 / 10, so "winner takes the whole pot" would not be. The operator asked that the pictures not turn into a new look for the page: the first line of the block says the look stays theirs.

## The pictures

Drawn by `make_mockup.py`, rendered and colour-scanned by `render.py`. Real: table 5's standings, pot, volume and picks, the lobby's tables, the species' indicators, the assets with a market. Sample: which seat is "yours" (our key owns none at table 5), its open position, last trades, the preview figures and the change log.

- `table-1920.png`: a seated owner at table 5, 1920 x 1080: table and leaderboard, the control panel, the bot live.
- `table-1440.png`: the same at 1440 x 900.
- `table-390.png`: a phone; the panel first.
- `lobby-1920.png`: the new headline, one strip of kinds, Live now and Open apart.
- `lobby-390.png`: the lobby on a phone.
- `table.html`, `lobby.html`: the same pages, live at any width.

## Filing

On the form, "I have a link" with `https://cymetica.com/agent-tournaments`, the block below, one item per line, and the five PNGs as pictures. After filing, check their BB-SPEC line by line against this block, then BB-ACCEPT without a BB-CHANGE (#192).

```
Follow-up to ET-31263: upgrade the live Agent Tournaments itself, not a new page beside it; it keeps its name, logo, copy and today's look (the oval tables, the avatars, the fonts and colours). The pictures show layout and content, not a new visual style. Goals, not methods; the template lines about rebuilding someone else's app do not apply. Colours: the site's cyan, green, red, blue and slate-blue neutrals; no purple, orange, amber, yellow or plain gray. English, numbers before words; explanations in a tooltip.
1. Lobby headline: "10 AI agents. 7 days. 1 pot. Best ROI takes it." is no longer true (Flash runs 1 day, ET10 tables pay ET10). New: "10 agents. 1 table. Best ROI wins." Under it one strip of the three kinds instead of today's six boxes: Week, 7 days, $5 to $30 and $50 to $300; Flash, 1 day, the same; ET10, 7 days, 100 to 600 and 1,000 to 6,000 ET10. One line under it: the top 3 split the pot 60 / 30 / 10, plus 1,000 ET10 on every USDC table (85 / 42 / 14 on Flash).
2. Two sections: "Live now" (running tables: pot, time left, the leader and its ROI) and "Open, starts when full" (buy-in, kind, length, pot, seats left, Take a seat). The filters All, $5, $50, Flash, ET10, Mine apply to both.
3. Table cards: nothing past the card's edge at any width. Today "Open · 10 seats left" runs 44 to 77 px past the right edge at 1440 px on ET10 1K, ET10 100, Flash Pro and Flash Micro. The name alone in the head; buy-in, kind and length on the line under it; seats left under the pot.
4. The featured card shows the table next to fill, priced in its own currency. Today ET10 1K #16 reads "$1,000" there.
5. At the table, the owner of a seat gets a control panel for their own bot, usable while the tournament runs, so they need not leave for the bot's page. It holds only what the bot's page /clone/{id} already sets (PATCH /cloned-bots/{instance_id}/settings), nothing new:
6. What it trades: the market lanes on or off, each with its scope as on the bot's page: perpetual 5-minute epochs (BTC, ETH), CLOB pairs (pick pairs), event cards, arena, catalog (pick symbols). Today table 5's bots trade only 5-minute BTC and ETH rounds.
7. Risk: stop loss % and take profit %. Max position, open positions, the 2x leverage cap and the 20 new trades a day stay as they are, shown as fixed for the tournament.
8. "This change": the difference from what runs now in one line, then Apply.
9. Changes, stated on the panel: as many as the owner likes, any time during the tournament; a change applies to trades opened after it, never back; ROI stays on the table's capital; every change is a public row on the table ("08:02 Perceptron Oracle changed markets and stop loss"), that it changed, not to what, until the table ends; house bots never change, they are the benchmark.
10. Your bot, live, beside the panel: ROI against the leader as a line, ROI, volume against the minimum, trades, today's allowance as 20 cells (resets 00:00 UTC), open positions with the time to close, the last trades with their result, all updating live.
11. Layout at 1920 x 1080: the table and the leaderboard left, the panel and the race in the centre, your bot and the change log right. A visitor without a seat sees the race in the centre. Leaderboard: a house bot carries a small H, not the word beside its name, and no name is cut to two letters.
12. Rules: one strip of seven values (buy-in, capital, minimum volume, payout, ET10, leverage, ranked by) instead of ten boxes in two rows.
13. Pick the winner has two states. Open: ET-31263's mockup (radio, ROI, what a pick pays, chips 10 / 50 / 100, the win before the click, PICK). Closed: "Picks closed" with the time, the pool and the picks per bot, read only, no radios. Today, on table 5 after picks closed on 13 Oct 18:49 UTC: "CLOSES IN NOW" over ten disabled radios, no chips and no PICK, a click does nothing, and every house bot's name is doubled ("House Fibonacci Phoenix House").
14. Phone, 390 px: the panel first for a seated owner, then your bot, the table, the leaderboard; nothing scrolls sideways.
15. Agents can make the same changes over the API and MCP, and the change log is in /tables/{id}.
Done when:
[ ] 1 The lobby's headline and kinds strip are true for Week, Flash and ET10 tables; the six boxes are gone.
[ ] 2 Running and open tables stand in two sections, and the filters apply to both.
[ ] 3 At 1440 and 1920 px no chip or label runs past a table card's edge.
[ ] 4 An ET10 table is priced in ET10 everywhere, the featured card included.
[ ] 5 A seated owner can switch market lanes and change stop loss and take profit from the table during the tournament, and the bot then trades the lanes switched on.
[ ] 9 A change counts only for trades opened after it, with no limit on how many; each change is a public row; house bots cannot be changed.
[ ] 10 Your bot's ROI, volume, allowance, open positions and last trades update without a reload.
[ ] 13 After picks close the panel reads "Picks closed" with no radios; while open, a pick can be placed; no name is doubled.
[ ] 15 The same changes work through the API and MCP.
[ ] The page keeps today's look; only layout and content change.
```
