# Build it Better: Agent Tournaments v4 becomes Agent Casino (6 seats, top 2 paid, Paper | Live Flash tables, outside agents with a wallet, a coach and a Risk that work)

**Drawn 2026-10-26 from the operator's words on the live page (table 15, our seat 87). Not filed, not sent: filing is the operator's.** Follow-up to ET-31702 (v3, `../tournaments-v3/request.md`). Goals are theirs; the design is ours, their veto open.

## Run it

The pictures are screenshots of THEIR live pages with only the v4 changes on them, so the operator sees exactly what the spec asks for and can tune it:

```
python outbox/tournaments-v4/live/serve.py       # http://127.0.0.1:8790/agent-casino
```

A read-only local copy: it fetches their pages anonymously (GET, no cookies, no key) and refuses every other method, so nothing can reach their platform. It serves them at `/agent-casino` and redirects the old `/agent-tournaments` addresses there, as the spec asks. Use the PAPER | LIVE switch at the top of the lobby (or their header pill); click a Live table for the wallet panel; on `/agent-casino/table/15` the owner column opens on the Coach tab, and moving Risk rewrites the Settings tab's stop loss and take profit. `live/render.py` retakes the pictures, `tests/repo/test_tournaments_v4_mirror.py` holds the changes in place.

## What the live read found (2026-10-26)

- Seats are 10 everywhere; `modes` says `paper: open, live: not_open`; `live_note` says live tables wait for entry and prize terms. Their header already has a PAPER | LIVE pill, and the lobby shows a "Live tables are not open yet" note in LIVE. Outside venues exist (a wallet signs a message, its swaps are read from the chain) but buy-ins and prizes stay paper.
- NEXUS Tune on seat 87: 1,000 ET10 locked 19 Oct, one tune in seven days (21 Oct 07:56), then "waiting for closed trades: 0 of 5 since the last tune". Our bot's last closed trade is 20 Oct 14:10 UTC; it is silent for six days at -20.27 %, rank 5 of 10. The gate counts trades, so a bot that stops trading is never tuned again. It also touched only markets (stop loss 5, take profit 20 untouched).
- The table's changelog has two rows, both "changed markets", with no who. 21 Oct 07:56 is the NEXUS tune; 23 Oct 20:53 is not in the lock's tune list (`tune_count` 1) and put BTC back, so it came from the owner's side. The owner's "Your changes" lists both, the NEXUS one too.
- The dots on the race are YOUR TRADES: 17 circles that overlap where trades are minutes apart, none after Tuesday.
- Where agents look: `/llms.txt`, `/.well-known/agent-card.json` and `/.well-known/mcp.json` describe it as "10 AI agents ... best ROI takes it", the top three paid, paper tables only, Live USDC "not open"; MCP `agent_tournaments_open_tables` needs no key, `agent_tournament_join` needs one (free register) and the owner approves every seat.
- The owner's Settings tab has Stop loss (1-20 %, now 5) and Take profit (5-100 %, now 20) sliders and a fixed 10 % max position; nothing links them to a risk level today.

## Real / invented

Real: everything on their pages, and our seat's bot settings, lock and 17 closed trades (`live/fixtures/owner.json`, `fetch.py`). The operator's: the name Agent Casino and its address, the top-2 split ($1: $4 and $2). Invented: the Risk levels' values (ours, anchored on today's 5 % / 20 %, `owner.RISK_SET`), the three Live tables' ids and seat counts, the wallet and its record, the bands' thresholds, the Tune triggers (2 losses, 15 min, 6 h) as examples, and the Tune log rows (the 20 Oct 14:00 and 14:05 rows replay our real trades of 13:55 -2.54, 14:00 -1.88, 14:10 -1.05 USDC as the new rule would have read them; the others are examples).

## The pictures (the form takes at most 6), in `pictures/`

1. `lobby-live-1440.png`: the Paper | Live switch on LIVE: the hero's icon tiles, three Live Flash tables, each card with its buy-in once and a small clock (1H, 5H, 1D).
2. `wallet-1440.png`: an outside agent joining with a wallet.
3. `table-1440.png`: the table page for the seat owner, 15 % smaller, 6 seats, no rules strip, the Coach tab first.
4. `coach-risk9-1440.png`: the Coach tab: the NEXUS coach (3D chip in a deerstalker, on/off) and, under it, the Risk panel at 9 with the size, stop loss and take profit it sets.
5. `changelog-1440.png`: the Tune log and who changed what, in the Changelog tab.
6. `race-1440.png`: the race with touching trade markers merged.

Also in `pictures/`: `lobby-paper-*`, `coach-on-1440.png`, `coach-off-1440.png`, `head-1440.png`, `settings-risk9-1440.png` (the Settings tab after Risk 9). The copy lets the coach switch on and off whatever the plan; the paid-plan lock is this spec's, not the preview's.

## Filing

On the form, "I have a link" with `https://cymetica.com/agent-tournaments` (the page as it is today), the block below (6,879 characters, plain ASCII, 25 lines), one item per line, and the six pictures. After filing, check their BB-SPEC line by line against this block, then BB-ACCEPT without a BB-CHANGE (#192).

```
Follow-up to ET-31702: upgrade the live Agent Tournaments itself, not a new page beside it, and rename it Agent Casino; it keeps its logo, fonts and colours. Goals, not methods; the template lines about rebuilding someone else's app do not apply. English, numbers before words.
The look is the pictures: they are the live pages with only these changes on them. Build each page to match its picture at 1440 and 1920 px: layout, sizes, colours, icons and words. Add nothing, restyle nothing, no colour that is not the site's. A page that differs from its picture is not done.
0. Name and address: the logo reads AGENT CASINO; every title, felt and line of copy says Agent Casino. The pages move to cymetica.com/agent-casino (/leaderboard, /how, /table/{id}); every old /agent-tournaments page redirects permanently to the same page there. The API path and the MCP tool names stay.
1. Six seats: every table, in the lobby, the create form, the table page and How it works, has 6 seats instead of 10 ("6 agents. 1 table."). It starts when the 6th seat is approved; house bots fill to 6 as today. The pot pays the top 2 only: 1st gets 4 buy-ins, 2nd gets 2 (a $1 table pays $4 and $2); cards show 1ST and 2ND, no 3RD. ET10 tables split the members' pot 2/3 and 1/3.
2. Lobby: a PAPER | LIVE switch beside the table filters (All, $5, $50, Flash, ET10, Mine; on LIVE: All, $1, $5, 1H, 5H, 1D, Mine), the same setting as the pill in the site header, decides which tables the lobby lists, with no reload. LIVE is real USDC and replaces the "Live tables are not open yet" note.
2b. Cards and the table page header say the buy-in once (no name like "Flash Pro #19", no ET10 tag beside "100 ET10"), with a small clock under it showing the length (1H, 5H, 1D) whose ring fills as the table runs, instead of a FLASH tag. The hero's three tiles become icons (clocks 1H 5H 1D, a 4x / 2x podium, ET10 coins); no Week tables. A small SEE IN THE UNIVERSE button in PICK A TABLE's green, at the right end of the top bar on every page, opens cymetica.com/company/app#universe, where the Agent Casino stands. The table page drops the strip of seven rules and is drawn 15 % smaller. The table gets a metal rail, a lit cyan-to-green inner edge, two cards and two chip stacks at each side seat and a deck under BEST ROI WINS. The table panel and the cards keep today's navy (#0d1520) as poker-table suede (fine grain, darker nap, same blue). The honeycomb at the top runs the full screen width, as on Airdrop Farmer. The back arrow sits in the middle of its square.
3. Live tables, all Flash, all real USDC: 1 hour ($1 buy-in), 5 hours ($1 for now), 1 day ($5). 6 paid seats, no house bots, the pot is the buy-ins. The buy-in is held from the player's wallet until the table starts (leaving before the start returns it); the prize is paid in USDC to the same wallet when it ends. Entry and prize terms, escrow and where it is open are yours. Paper tables stay, with 6 seats.
4. Outside agents: any agent can take a seat at a Live table with a wallet alone. Ownership is proven, not typed in: the wallet signs a one-time message that names the table, carries a nonce and expires in minutes (EVM, ERC-1271 and Solana, as your venue rules already do). The buy-in must come from that wallet and the prize goes only to it. No account, no API key, no approval step; the API and MCP do the same. One wallet, one seat per table.
5. The wallet's record places it: the platform reads its DEX swaps from the chain (last 90 days) and shows swaps, volume, realised ROI and active days. With a record it sits at the $5 table ("PROVEN"), without one at the $1 tables ("ANY WALLET"); the thresholds are yours. The record never replaces the buy-in or the signature. Each Live card shows its band.
6. A new first tab, Coach, in the seat owner's column, with two panels. The NEXUS coach, with no box: only its icon (the chip in 3D, in a deerstalker with a magnifying glass, standing still) and an on/off switch, on a paid NEXUS plan (Pro, Max 5x, Max 20x), locked with "See plans" on free; the ET10 lock and its paragraph go. Under it, Risk, for every owner, coach or not: a coloured gauge 1 to 10 (Safe to All in, blue to red) with a slider. Risk SETS the bot at once, with no Apply: level L sets trade size L % (the 10 % max position stays), stop loss L % and take profit 4 x L % (at least 5 %); level 5 is today's 5 % / 20 %. The panel shows the three numbers, the Settings tab the new values, the changelog OWNER. Example: an hour before the end and not first, the owner raises it. With the coach on, NEXUS tunes the bot inside that risk.
7. Tune reacts to how the bot is doing, not to a count of closed trades. Today it waits for 5 closed trades, so a bot that stops trading is never tuned again (seat 87: one tune on 21 Oct, none since, ROI -20.27 %). Goals: 2 losses in a row, tuned within 5 minutes; a rank lost, within 15 minutes; no trade for a fifth of the table's length (6 h on a 7-day table), tuned too. It changes markets, stop loss and take profit.
8. Every check is a row in the Tune log (Changelog tab), CHECKED (nothing changed, and why) or TUNED (what changed, why in numbers), so the log is never empty while the table runs. The changelog and the owner's "Your changes" say who changed each setting: NEXUS or OWNER.
9. The race: trade markers that would touch merge into one marker with the number of trades.
10. Ready for agents where they look first: /llms.txt, /.well-known/agent-card.json and /.well-known/mcp.json describe Agent Casino as above (6 seats, top 2 paid, Live tables, the wallet join). The MCP tools that list tables and take a seat, and the REST API, cover Live tables and the wallet join with no key, so an agent that finds any of them sits at a Live table without reading anything else.
Done when:
[ ] 0 Every page says Agent Casino at cymetica.com/agent-casino; old addresses redirect.
[ ] 1 Nothing says 10 seats; a table starts with 6; 1st gets 4 buy-ins, 2nd gets 2, nobody else.
[ ] 2-3 The pill lists only Paper or only Live tables; Live shows Flash 1 hour $1, 5 hours $1, 1 day $5 in USDC, held and paid to the wallet.
[ ] 4-5 An agent with only a wallet sits at a Live table via the page, API or MCP; it needs a fresh signature and a buy-in from that wallet; a wallet it does not hold is refused; its record sets $1 or $5.
[ ] 2b Each card and table header shows the buy-in once with its clock; no rules strip.
[ ] 6 Coach is the first tab, the coach locked on free; moving Risk changes size, stop loss and take profit at once.
[ ] 7-8 2 losses in a row are tuned within 5 minutes, a silent bot is tuned; every check is a row with its reason and who.
[ ] 9 No two race markers touch at 1440 and 1920 px.
[ ] 10 An agent given only /llms.txt, the agent card or the MCP list takes a Live seat with a wallet.
[ ] Every page matches its picture side by side at 1440 and 1920 px.
```
