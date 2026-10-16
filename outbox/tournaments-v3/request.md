# Build it Better: Agent Tournaments v3 (lobby, leaderboard, create a table, the table page, NEXUS tunes it)

**Drawn with the operator on 2026-10-16, piece by piece, each one approved before the next** ("perfektni", "jo to je top", "ok dobry"). Follow-up to ET-31459 (shipped, re-read 2026-10-16: `docs/et-31459-verification.md`). Goals are theirs; the design is ours, their veto open. What he cut on the way is not in it: Elo and a last-5 strip on the leaderboard ("neprekomplikovavej to"), free / private / practice tables, more than 10 seats and several tables at once ("klasicky stul jak tvori oni, nic navic"), a split bar under the headline ("tu spodni listu uz tam nedavej").

## The pictures (the form takes at most 6)

Each drawn by a `make_mockup.py` beside it from the live API on 2026-10-16, palette-scanned and checked for spills and overlaps at 1440 and 1920 by its `render.py`.

1. `../tournaments-lobby-card/cards-1440.png`: the top of the lobby as it is live, with only the strip under the headline swapped for the three tiles; Live now and Open cards.
2. `../tournaments-create-table/create-1440.png`: Create a table, the button and the form.
3. `../tournaments-leaderboard/leaderboard-1440.png`: the Leaderboard tab.
4. `../tournaments-table-detail/player-1440.png`: the table page for a seat owner (table 5, our seat 29).
5. `../tournaments-table-detail/visitor-1440.png`: the table page for a visitor (table 13, picks open).
6. `../tournaments-create-table/open-1440.png`: the Open section with its new button.

## Filing

On the form, "I have a link" with `https://cymetica.com/agent-tournaments`, the block below, one item per line, and the six pictures. Filing is the operator's. After filing, check their BB-SPEC line by line against this block, then BB-ACCEPT without a BB-CHANGE (#192).

```
Follow-up to ET-31459: upgrade the live Agent Tournaments itself, not a new page beside it; it keeps its name, logo, copy, fonts and colours. The pictures show layout and content, not a new visual style. Goals, not methods; the template lines about rebuilding someone else's app do not apply. Colours: the site's cyan, green, red, blue and slate-blue neutrals only. English, numbers before words.
1. Lobby, top: only the strip under the headline changes; the agents-trading chip, the headline, PICK A TABLE with its three steps, the line under it and the Your agents panel stay exactly as they are. The strip: three tiles instead of today's three price cards and the sentence under them. HOW LONG: one chip per kind (Week 7 days, Flash 1 day; a new kind is a new chip). THE POT: 60 / 30 / 10, the top 3 by ROI split every buy-in. ON TOP: + ET10 for the top 3 on USDC tables; each table shows its amount. No prices in the tiles.
2. Table cards: the status in the top-right corner (LIVE glowing, or OPEN) and under it the time left as a countdown (days, hours, minutes; seconds under a day) with DAY n/N and a progress bar. Open cards say "starts when full" there.
3. Table cards: the oval's centre shows the whole pool that will be split, the pot plus the ET10 on top (live: now; open: when full); under the oval three cells, 1st / 2nd / 3rd, each with its USDC and ET10.
4. Nothing overlaps anything: today the YOU tag sits over POT on a table card, and in Your agents a badge covers the rank "#3/10" on Flash Micro #13.
5. Remove the Top agents section and its tab; the Leaderboard replaces them.
6. New tab Leaderboard, beside Lobby and How it works: every bot that has sat at a table, all time. Per bot: won ($ and ET10), wins (tables finished first), average ROI, tables played. Ranked by wins, then average ROI; a house strategy is one row across its tables. Above it the top 3 as a podium and three counts: bots, tables live, paid to winners. Filters: All time / 7 days; All / Mine.
7. Open section: a "Create a table" button beside its title. It opens a form for one ordinary table like the ones you open: kind (Week, Flash) and buy-in ($5, $50, 100 ET10, 1,000 ET10); 10 seats, starts when full, 60 / 30 / 10 and the same ET10 on top. A preview shows the new table's lobby card. Agents can do the same over the API and MCP.
8. Table page, top: name, buy-in and kind, LIVE and the countdown as on the cards; under it the seven rules (buy-in, capital, minimum volume, payout, ET10, leverage, ranked by) as one strip of tiles.
9. Table page, main column: the table large (every seat with its name and ROI, the pool in the middle, the 1st / 2nd / 3rd cells under it), then the standings (rank, bot, ROI, volume against the minimum, prize now, pick), then the race. "If it ended now" goes: the standings' prize column says it.
10. Pick the winner moves into the standings: one bar over the rows with the pool, the time left and the stake (10 / 50 / 100), and a Pick button on each row while picks are open; once closed, each row shows its picks and stake.
11. Table page, one side column for the seat owner only: their bot (rank, ROI, prize now, today's trades of 20), what it trades, stop loss and take profit, the fixed limits, Reset and Apply, the change count; under it the bot's last 5 trades with a link to all. The right-hand "Your bot, live" column goes. A visitor sees the main column at full width.
12. Trading venue: linking an exchange or a wallet moves off the table page, to the bot's profile or the account settings, wherever fits best; the seat owner's panel shows one line, where the bot trades, with a link there.
13. NEXUS tunes it: in the seat owner's column, a member who locks ET10 (e.g. 1,000) lets NEXUS tune their seated bot while the table runs, with one click; NEXUS changes its markets, stop loss and take profit from its own trades. The amount and the terms are yours.
Done when:
[ ] 1 The three tiles replace the price cards and the sentence, and nothing else at the top of the lobby changes; a new kind needs no new tile.
[ ] 2-3 Every table card shows its status and countdown in the corner, and the whole pool with its 1st / 2nd / 3rd split.
[ ] 4 Nothing overlaps at 1440 and 1920 px.
[ ] 5-6 Top agents is gone; the Leaderboard tab lists every bot that has played, ranked by wins, then average ROI.
[ ] 7 A member or an agent can open one ordinary table from the lobby, the API or MCP.
[ ] 8-11 The table page reads top to bottom: rules, table, standings with picks, race; the seat owner's panel and last trades in one side column; a visitor gets the full width.
[ ] 12 No venue form on the table page.
[ ] 13 A member can lock ET10 and let NEXUS tune their seated bot during a tournament.
[ ] The pages keep today's look; only layout and content change.
```
