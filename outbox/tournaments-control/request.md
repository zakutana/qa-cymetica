# Build it Better: Agent Tournaments, a control panel at the table

**To be filed by the operator on the form.** ET-31263 is closed (shipped, verdict pass, read 2026-10-14), so a new request on `cymetica.com/agent-tournaments` is possible.

The operator, 2026-10-14, after ET-31263: *"ta hlaska uz neplati vymysli novou. to pod tim taky nevypada moc pekne uz moc kosticek. U stolu jim precnivaji stitky. Pak chci at se oddeli sekce pro live stoly a ty co jeste nezacly a pak hlavne nejvetsi cast musis navrhnout jak bude vypadat ze jak jsem u stolu ... behem turnaje budu moct upravovat strategii botu. ted jede jen ty BTC a ETH trejdy coz je trapny ... nejaky control panel u stolu kde budu strategii modifikovat a ten pick a winner nefunguje jak na to klikam. Pak jeste sam projdi celou apku"*. Goals are theirs; the design is ours, their veto open.

What we read (reads only, 2026-10-14 ~08:00 UTC): the 11 bot species all carry `pure_ta` indicators (`/api/v1/backtest/bots/{slug}`), and every tournament bot trades 5-minute up/down rounds on BTC or ETH (#204); `PATCH /backtest/bots/{slug}/settings` takes only `name` and `avatar_url`; `/cloned-bots/backtest/available-assets` lists markets for BTC, ETH, SOL, DOGE, VAIX and eight stocks; table 5's picks closed 13 Oct 18:49 UTC (`picks.open: false`) while the page shows "CLOSES IN NOW" over ten disabled radios (`docs/et-31263-verification.md`, item 4).

The fairness rules in item 6 are ours, decided so the panel can be built in a day: changes count forward only, a daily cap, a public log of that a change happened, house bots fixed as the benchmark.

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
Follow-up to ET-31263: upgrade the live Agent Tournaments itself, not a new page beside it; it keeps its name, logo and copy, and the template lines about rebuilding someone else's app do not apply. The pictures are the template and the spirit is the requirement; shape and wording are yours to improve. Colours: the site's cyan, green, red, blue and slate-blue neutrals; no purple, orange, amber, yellow or plain gray. English, numbers before words; explanations in a tooltip.
1. Lobby headline: "10 AI agents. 7 days. 1 pot. Best ROI takes it." is no longer true (Flash runs 1 day, ET10 tables pay ET10). New: "10 AI bots. 1 table. Best ROI wins." Under it one strip of the three kinds instead of today's six boxes: Week, 7 days, $5 to $30 and $50 to $300; Flash, 1 day, the same; ET10, 7 days, 100 to 600 and 1,000 to 6,000 ET10. One line under it: the top 3 split the pot 60 / 30 / 10, plus 1,000 ET10 on every USDC table (85 / 42 / 14 on Flash).
2. Two sections: "Live now" (running tables: pot, time left, the leader and its ROI) and "Open, starts when full" (buy-in, kind, length, pot, seats left, Take a seat). The filters All, $5, $50, Flash, ET10, Mine apply to both.
3. Table cards: nothing past the card's edge at any width. Today "Open · 10 seats left" runs 44 to 77 px past the right edge at 1440 px on ET10 1K, ET10 100, Flash Pro and Flash Micro. The name alone in the head; buy-in, kind and length on the line under it; seats left under the pot.
4. The featured card shows the table next to fill, priced in its own currency. Today ET10 1K #16 reads "$1,000" there.
5. The table page gets a control panel for the owner of a seat, usable while the tournament runs. Today every bot trades 5-minute up/down rounds on BTC or ETH only (#204), the stake is fixed at 10% of capital, and an owner can change only the name and avatar. The panel changes the owner's own bot:
6. Strategy: the species with its indicators as /backtest/bots/{slug} lists them (RSI 14; SMA 20 / 50; Bollinger 20, 2; MACD 12 / 26 / 9; Volume MA 20, EMA 21, ATR 14; Hybrid), and each indicator's numbers as sliders (RSI length, buy below, sell above, SMA, ATR stop, MACD fast / slow / signal).
7. Markets: every asset that has a market, grouped as /cloned-bots/backtest/available-assets groups them (crypto, perps, stocks), several at once; one without a market shows greyed with "no market yet". Then timeframe (5m, 15m, 1h, 4h) and direction (long, short, both).
8. Size and risk: stake per trade 2 to 20% of capital, positions open at once 1 to 5, stop for the day at a drawdown, take profit.
9. Preview: the last 7 days with the new settings (ROI against today's, trades, max drawdown, win rate), from the cloned-bot backtest the platform already runs. Then "This change", the difference from what runs now in one line, and Apply.
10. Fair play, stated on the panel: a change applies only to trades opened after it, never back; ROI stays on the table's capital; at most 3 changes per UTC day; every change is a public row on the table ("08:02 Perceptron Oracle changed markets and stake"), that it changed, not to what, until the table ends; house bots never change, they are the benchmark; the 20 new trades a day and the 2x leverage cap stay.
11. Your bot, live, beside the panel: ROI against the leader as a line, ROI, volume against the minimum, trades, today's allowance as 20 cells (resets 00:00 UTC), open positions with the time to close, the last trades with their result, all updating live.
12. Layout at 1920 x 1080: the table and the leaderboard left, the panel in the centre and largest, your bot right. A visitor without a seat sees the race in the centre. Leaderboard: a house bot carries a small H, not the word beside its name, and no name is cut to two letters.
13. Rules: one strip of seven values (buy-in, capital, minimum volume, payout, ET10, leverage, ranked by) instead of ten boxes in two rows.
14. Pick the winner has two states. Open: ET-31263's mockup (radio, ROI, what a pick pays, chips 10 / 50 / 100, the win before the click, PICK). Closed: "Picks closed" with the time, the pool and the picks per bot, read only, no radios. Today, on table 5 after picks closed on 13 Oct 18:49 UTC: "CLOSES IN NOW" over ten disabled radios, no chips and no PICK, a click does nothing, and every house bot's name is doubled ("House Fibonacci Phoenix House").
15. Phone, 390 px: the panel first for a seated owner, then your bot, the table, the leaderboard; nothing scrolls sideways.
16. Agents get the same control over the API and MCP (strategy, markets, size, preview), under the same caps, and the change log is in /tables/{id}.
Done when:
[ ] 1 The lobby's headline and kinds strip are true for Week, Flash and ET10 tables; the six boxes are gone.
[ ] 2 Running and open tables stand in two sections, and the filters apply to both.
[ ] 3 At 1440 and 1920 px no chip or label runs past a table card's edge.
[ ] 4 An ET10 table is priced in ET10 everywhere, the featured card included.
[ ] 5 A seated owner can change strategy numbers, markets, timeframe, direction, stake and risk during the tournament, and the bot trades the new markets.
[ ] 9 The preview shows the last 7 days with the new settings before Apply.
[ ] 10 A change counts only for trades opened after it; the 4th change in a UTC day is refused; each change is a public row; house bots cannot be changed.
[ ] 11 Your bot's ROI, volume, allowance, open positions and last trades update without a reload.
[ ] 14 After picks close the panel reads "Picks closed" with no radios; while open, a pick can be placed; no name is doubled.
[ ] 16 The same changes work through the API and MCP, with the same caps.
```
