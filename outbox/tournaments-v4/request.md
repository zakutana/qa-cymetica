# Build it Better: Agent Tournaments v4 (6 seats, Paper | Live Flash tables, outside agents with a wallet, NEXUS Tune that works)

**Drawn 2026-10-26 from the operator's words on the live page (table 15, our seat 87). Not filed, not sent: filing is the operator's.** Follow-up to ET-31702 (v3, `../tournaments-v3/request.md`). Goals are theirs; the design is ours, their veto open.

## Run it

The pictures are screenshots of THEIR live pages with only the v4 changes on them, so the operator sees exactly what the spec asks for and can tune it:

```
python outbox/tournaments-v4/live/serve.py       # http://127.0.0.1:8790/agent-tournaments
```

A read-only local copy: it fetches their pages anonymously (GET, no cookies, no key) and refuses every other method, so nothing can reach their platform. Use the PAPER | LIVE switch at the top of the lobby (or their header pill); click a Live table for the wallet panel; on `/agent-tournaments/table/15` the owner column opens on the Coach tab (Pro | Free preview at its foot). `live/render.py` retakes the pictures, `tests/repo/test_tournaments_v4_mirror.py` holds the changes in place.

## What the live read found (2026-10-26)

- Seats are 10 everywhere; `modes` says `paper: open, live: not_open`; `live_note` says live tables wait for entry and prize terms. Their header already has a PAPER | LIVE pill, and the lobby shows a "Live tables are not open yet" note in LIVE. Outside venues exist (a wallet signs a message, its swaps are read from the chain) but buy-ins and prizes stay paper.
- NEXUS Tune on seat 87: 1,000 ET10 locked 19 Oct, one tune in seven days (21 Oct 07:56), then "waiting for closed trades: 0 of 5 since the last tune". Our bot's last closed trade is 20 Oct 14:10 UTC; it is silent for six days at -20.27 %, rank 5 of 10. The gate counts trades, so a bot that stops trading is never tuned again. It also touched only markets (stop loss 5, take profit 20 untouched).
- The table's changelog has two rows, both "changed markets", with no who. 21 Oct 07:56 is the NEXUS tune; 23 Oct 20:53 is not in the lock's tune list (`tune_count` 1) and put BTC back, so it came from the owner's side. The owner's "Your changes" lists both, the NEXUS one too.
- The dots on the race are YOUR TRADES: 17 circles that overlap where trades are minutes apart, none after Tuesday.

## Real / invented

Real: everything on their pages, and our seat's bot settings, lock and 17 closed trades (`live/fixtures/owner.json`, `fetch.py`). Invented: the three Live tables' ids and seat counts, the wallet and its record, the bands' thresholds, the Tune triggers (2 losses, 15 min, 6 h) as examples, and the Tune log rows (the 20 Oct 14:00 and 14:05 rows replay our real trades of 13:55 -2.54, 14:00 -1.88, 14:10 -1.05 USDC as the new rule would have read them; the others are examples).

## The pictures (the form takes at most 6), in `pictures/`

1. `lobby-live-1440.png`: the Paper | Live switch on LIVE: the hero's icon tiles, three Live Flash tables, each card with its buy-in once and a small clock (1H, 5H, 1D).
2. `wallet-1440.png`: an outside agent joining with a wallet.
3. `table-1440.png`: the table page for the seat owner, 15 % smaller, 6 seats, no rules strip, the Coach tab first.
4. `coach-risk9-1440.png`: the Coach tab: the NEXUS coach (3D chip in a deerstalker, on/off) and, under it, the Risk panel at 9.
5. `changelog-1440.png`: the Tune log and who changed what, in the Changelog tab.
6. `race-1440.png`: the race with touching trade markers merged.

Also in `pictures/`: `lobby-paper-*`, `coach-on-1440.png`, `coach-off-1440.png`, `head-1440.png`. The copy lets the coach switch on and off whatever the plan; the paid-plan lock is this spec's, not the preview's.

## Filing

On the form, "I have a link" with `https://cymetica.com/agent-tournaments`, the block below, one item per line, and the six pictures. After filing, check their BB-SPEC line by line against this block, then BB-ACCEPT without a BB-CHANGE (#192).

```
Follow-up to ET-31702: upgrade the live Agent Tournaments itself, not a new page beside it; it keeps its name, logo, copy, fonts and colours. The pictures are the live pages with only these changes on them. Goals, not methods; the template lines about rebuilding someone else's app do not apply. Colours: the site's own. English, numbers before words.
1. Six seats: every table, in the lobby, the create form, the table page and How it works, has 6 seats instead of 10 (headline: "6 agents. 1 table."). It starts when the 6th seat is approved; house bots fill to 6 as today. The pot still splits 60 / 30 / 10 to the top 3.
2. Lobby: a PAPER | LIVE switch beside the table filters (All, $5, $50, Flash, ET10, Mine; on LIVE: All, $1, $5, 1H, 5H, 1D, Mine), the same setting as the pill already in the site header, decides which tables the lobby lists, with no reload. PAPER is today's tables; LIVE is real USDC and replaces the "Live tables are not open yet" note.
2b. Table cards and the table page header say the buy-in once (no name like "Flash Pro #19", no ET10 tag beside "100 ET10"; ET10 gets its own coin icon). Under the buy-in, a small clock with the length (1H, 5H, 1D) whose ring fills as a running table's time goes, instead of a FLASH tag; the corner keeps LIVE and the countdown. The hero's three tiles become icons (three clocks 1H 5H 1D, a 60 / 30 / 10 podium, ET10 coins); there are no Week tables. The table page drops the strip of seven rules and is drawn 15 % smaller. The table gets a metal rail round the felt, a lit inner edge from cyan to green, two face-down cards and two stacks of chips in front of each side seat and the deck under BEST ROI WINS; around the table, the dark space of the Cymetica Quest flyer (a soft light under the table, only a trace of dust, faint orbits round it, a few small stars, a band of light across). The page background gets depth (soft light, the table's honeycomb fading under the top, a fine grain) instead of one flat blue.
3. Live tables, all Flash, all real USDC: Flash 1 hour ($1 buy-in), Flash 5 hours ($1 for now), Flash 1 day ($5). 6 paid seats, no house bots, the pot is the buy-ins. The buy-in is held from the player's wallet until the table starts (leaving before the start returns it); the prize is paid in USDC to the same wallet when the table ends. Entry and prize terms, escrow and where it is open are yours. Paper tables stay as they are, with 6 seats.
4. Outside agents: any agent can take a seat at a Live table with a wallet alone. Ownership is proven, not typed in: the wallet signs a one-time message that names the table, carries a nonce and expires in minutes (Ethereum wallets, smart-contract wallets by ERC-1271, Solana by ed25519, as your venue rules already do), so nobody can enter a wallet they do not hold. The buy-in must arrive from that same wallet, and the prize is paid only to it. No account, no API key, no approval step; the API and MCP do the same. One wallet, one seat per table.
5. The wallet's record places it: the platform reads the wallet's DEX swaps from the chain (last 90 days) and shows swaps, volume, realised ROI and active days. A wallet with a record sits at the $5 table ("PROVEN"), one without sits at the $1 tables ("ANY WALLET"); the thresholds are yours. The record places a wallet, it never replaces the buy-in or the signature. Each Live card shows its band.
6. A new first tab, Coach, in the seat owner's column, with two panels. The NEXUS coach, set straight into the page with no box: only its icon (the Agent Tournaments chip drawn in 3D, in a deerstalker with a magnifying glass, standing still) and an on/off switch beside it, on a paid NEXUS plan (Pro, Max 5x, Max 20x), locked with "See plans" on the free plan; the ET10 lock and its paragraph go. Under it, Risk, for every owner, coach or not: a coloured gauge 1 to 10 (Safe to All in, blue to red) with a slider and one line on what it does (trade size, stop loss, take profit; change it any time). Example: an hour before the end and not first, the owner raises it. With the coach on, NEXUS tunes the bot inside that risk.
7. Tune reacts to how the bot is doing, not to a count of closed trades. Today the seat above waits for "5 closed trades since the last tune" and, once its bot stops trading, is never tuned again (seat 87: one tune on 21 Oct, no closed trade since 20 Oct 14:10, ROI -20.27 %). Goals: a bot with 2 losses in a row is tuned within 5 minutes; a bot that falls a rank within 15 minutes; a bot with no trade for a fifth of the table's length is tuned too (6 hours is the example on a 7-day table; the same rules apply on Flash). It changes markets, stop loss and take profit.
8. Every check is a row in the Tune log (in the Changelog tab, not on the coach), CHECKED (nothing changed, and why) or TUNED (what changed, and why in numbers), so the log is never empty while the table runs. The table's changelog, and the owner's "Your changes", say who changed each setting: NEXUS or OWNER.
9. The race: trade markers that would touch merge into one marker with the number of trades; nothing overlaps.
Done when:
[ ] 1 No page, card or text says 10 seats; a table starts with 6.
[ ] 2-3 The header pill lists only Paper or only Live tables; Live shows three Flash tables (1 hour $1, 5 hours $1, 1 day $5) in USDC, held and paid back to the wallet.
[ ] 4-5 An agent with only a wallet can sit at a Live table through the page, the API or MCP; a signature over a fresh message and a buy-in from the same wallet are both needed, and a wallet it does not hold is refused; its record sets $1 or $5.
[ ] 2b Each card and table header shows its buy-in once and a small clock with its length under it; no rules strip on the table page.
[ ] 6 Coach is the first tab: the coach (icon and switch, paid plan, locked on free) and under it the Risk panel every owner can set.
[ ] 7-8 A bot with 2 losses in a row is tuned within 5 minutes; a bot with no trade for a fifth of the table's length is tuned; every check is a row with its reason and who.
[ ] 9 No two race markers touch at 1440 and 1920 px.
[ ] The pages keep today's look; only layout and content change.
```
