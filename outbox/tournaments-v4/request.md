# Build it Better: Agent Tournaments v4 (6 seats, Paper | Live Flash tables, outside agents with a wallet, NEXUS Tune that works)

**Drawn 2026-10-26 from the operator's words on the live page (table 15, our seat 87). Not filed, not sent: filing is the operator's.** Follow-up to ET-31702 (v3, `../tournaments-v3/request.md`). Goals are theirs; the design is ours, their veto open.

## What the live read found (2026-10-26, our key, GET only: `fetch.py`, `data.json`)

- Seats are 10 everywhere; `modes` says `paper: open, live: not_open`; `live_note` says live tables wait for entry and prize terms. Outside venues exist (a wallet signs a message, its swaps are read from the chain) but buy-ins and prizes stay paper.
- NEXUS Tune on seat 87: 1,000 ET10 locked 19 Oct, one tune in seven days (21 Oct 07:56), then "waiting for closed trades: 0 of 5 since the last tune". Our bot's last closed trade is 20 Oct 14:10 UTC; it is silent for six days at -20.27 %, rank 5 of 10. The gate counts trades, so a bot that stops trading is never tuned again. It also touched only markets (stop loss 5, take profit 20 untouched).
- The table's changelog has two rows, both "changed markets", with no who. 21 Oct 07:56 is the NEXUS tune; 23 Oct 20:53 is not in the lock's tune list (`tune_count` 1) and put BTC back, so it came from the owner's side. Nothing on the page says so.
- The dots on the race are YOUR TRADES (the legend's second entry): 17 circles that overlap where trades are minutes apart, none after Tuesday.

## Drawn from real data / invented

Real: table 15's standings, race lines, pot and split (cut to its six best-ranked seats to show six); our seat's bot settings, lock and 17 closed trades. Invented: the Live tables' ids and seat counts, the wallet and its record, the bands' thresholds, the trigger numbers (2 losses, 15 min, 6 h) as examples, and the Tune log rows (the 20 Oct 14:00 and 14:05 rows replay our real trades of 13:55 -2.54, 14:00 -1.88, 14:10 -1.05 USDC as the new rule would have read them; the others are examples).

## The pictures (the form takes at most 6)

`make_mockup.py` draws them, `render.py` palette-scans and checks spills and overlaps at 1440 and 1920.

1. `lobby-1440.png`: Paper | Live switch, Live selected, three Flash cards (1 hour, 5 hours, 1 day) with 6 seats.
2. `table-1440.png`: the table page for the seat owner, 6 seats, the Tune switch under the bot panel.
3. `tune-1440.png`: the Tune panel on a paid plan (triggers, the log) and locked on the free plan.
4. `join-1440.png`: an outside agent joining with a wallet (the signed message, its record, the three tables).
5. `race-1440.png`: the race with touching markers merged.

## Filing

On the form, "I have a link" with `https://cymetica.com/agent-tournaments`, the block below, one item per line, and the five pictures. After filing, check their BB-SPEC line by line against this block, then BB-ACCEPT without a BB-CHANGE (#192).

```
Follow-up to ET-31702: upgrade the live Agent Tournaments itself, not a new page beside it; it keeps its name, logo, copy, fonts and colours. The pictures show layout and content, not a new visual style. Goals, not methods; the template lines about rebuilding someone else's app do not apply. Colours: the site's cyan, green, red, blue and slate-blue neutrals only. English, numbers before words.
1. Six seats: every table, in the lobby, the create form, the table page and How it works, has 6 seats instead of 10 (headline: "6 agents. 1 table."). It starts when the 6th seat is approved; house bots fill to 6 as today. The pot still splits 60 / 30 / 10 to the top 3.
2. Lobby: a Paper | Live switch beside the tabs. The lobby lists only the tables of the chosen mode. Paper is today's tables; Live is real USDC.
3. Live tables, all Flash, all real USDC: Flash 1 hour ($1 buy-in), Flash 5 hours ($1 for now), Flash 1 day ($5). 6 paid seats, no house bots, the pot is the buy-ins. The buy-in is held from the player's wallet until the table starts (leaving before the start returns it); the prize is paid in USDC to the same wallet when the table ends. Entry and prize terms, escrow and where it is open are yours. Paper tables stay as they are, with 6 seats.
4. Outside agents: any agent can take a seat at a Live table with a wallet alone. Ownership is proven, not typed in: the wallet signs a one-time message that names the table, carries a nonce and expires in minutes (Ethereum wallets, smart-contract wallets by ERC-1271, Solana by ed25519, as your venue rules already do), so nobody can enter a wallet they do not hold. The buy-in must arrive from that same wallet, and the prize is paid only to it. No account, no API key, no approval step; the API and MCP do the same. One wallet, one seat per table.
5. The wallet's record places it: the platform reads the wallet's DEX swaps from the chain (last 90 days) and shows swaps, volume, realised ROI and active days. A wallet with a record sits at the $5 table ("PROVEN"), one without sits at the $1 tables ("ANY WALLET"); the thresholds are yours. The record places a wallet, it never replaces the buy-in or the signature. Each Live card shows its band.
6. NEXUS Tune becomes a switch in the seat owner's column, on a paid NEXUS plan (Pro, Max 5x, Max 20x); the ET10 lock goes. On the free plan the switch shows locked with "See plans".
7. Tune reacts to how the bot is doing, not to a count of closed trades. Today the seat above waits for "5 closed trades since the last tune" and, once its bot stops trading, is never tuned again (seat 87: one tune on 21 Oct, no closed trade since 20 Oct 14:10, ROI -20.27 %). Goals: a bot with 2 losses in a row is tuned within 5 minutes; a bot that falls a rank within 15 minutes; a bot with no trade for a fifth of the table's length is tuned too (6 hours is the example on a 7-day table; the same rules apply on Flash). It changes markets, stop loss and take profit.
8. Every check is a row in the Tune log, CHECKED (nothing changed, and why) or TUNED (what changed, and why in numbers), so the log is never empty while the table runs. The table's changelog says who changed each setting: NEXUS or OWNER.
9. The race: markers that would touch merge into one marker with the number of trades; nothing overlaps.
Done when:
[ ] 1 No page, card or text says 10 seats; a table starts with 6.
[ ] 2-3 The switch lists only Paper or only Live tables; Live shows three Flash tables (1 hour $1, 5 hours $1, 1 day $5) in USDC, held and paid back to the wallet.
[ ] 4-5 An agent with only a wallet can sit at a Live table through the page, the API or MCP; a signature over a fresh message and a buy-in from the same wallet are both needed, and a wallet it does not hold is refused; its record sets $1 or $5.
[ ] 6 The switch works on a paid plan and shows locked on the free one.
[ ] 7-8 A bot with 2 losses in a row is tuned within 5 minutes; a bot with no trade for 6 hours is tuned; every check is a row with its reason and who.
[ ] 9 No two race markers touch at 1440 and 1920 px.
[ ] The pages keep today's look; only layout and content change.
```
