# Agent Tournaments, follow-up: the look (drafts, nothing sent, nothing filed)

Operator, 2026-10-11: the delivered page keeps our structure and colours but not the look of the design we sent; the Gem Screener came out as drawn, so this one has to as well. *"To je nepripustne."*

Two things go out, both his to send:

1. **The verdict on ET-30773** (`POST .../requests/{ticket}/verdict`, needs the request token that the form showed once): `fail` with the note below. Their answer of 2026-09-30: a fail note is kept as the record but schedules no build work.
2. **A new request on the form** ("It does not exist yet" is wrong here: it is an existing app, `https://cymetica.com/agent-tournaments`), which opens a follow-up ticket linked to ET-30773. Its text is the second block below: 17 lines, 4,994 characters (the limit is 8,000), one item per line. The form takes at most six pictures: upload `1-lobby.png`, `2-lobby-10-agents.png`, `3-take-a-seat.png`, `4-manual-setup.png`, `5-live-table.png`, `6-results.png` from `design/screenshots/` of `zakutana/agent-tournaments` (pinned: commit `1f9566a23319b5d942cb8a64e0e22825824c60f4`).

## 1. Verdict note (fail)

```
Fail on the look. The page follows the structure and the colours of the design in the brief but not its look, and the look is what the request was for. Side by side at 1440 px with the mockups (1-lobby.png, 3-take-a-seat.png): no header with the chip logo and Lobby / Top agents / How it works, no large display hero and no PICK A TABLE button, tables are plain ellipses with dots instead of poker-table cards with robot avatars, crown and YOU, no filters, Top agents is a plain table instead of five rating cards, the prompts sit in small scrolling boxes, Manual setup offers our own bots instead of Cymetica's 11 by backtest, and the How it works and Results pages do not exist (404). The numbers and rules read from the live page are right. A follow-up request lists every screen.
```

## 2. Follow-up request (paste into "What should it do better?")

```
Agent Tournaments (live at /agent-tournaments), follow-up to ET-30773: build the LOOK of the design. The page has the structure and the colours of the brief, but not its look, and the look is what was asked for. The mockups are the template. Brief: https://github.com/zakutana/agent-tournaments/blob/1f9566a23319b5d942cb8a64e0e22825824c60f4/SPEC.md (sections 5 and 7). Clickable mockup of all seven screens: https://htmlpreview.github.io/?https://github.com/zakutana/agent-tournaments/blob/1f9566a23319b5d942cb8a64e0e22825824c60f4/design/preview.html . Pictures are attached. Where the page and the mockup differ, the mockup wins.
Header on every screen (brief 5.0): the chip logo with bot eyes and AGENT TOURNAMENTS, links Lobby / Top agents / How it works, "LIVE" with the money in the pots, and the owner's pill with avatar, rank and ROI. No action button. Today the page shows the plain site header only.
Fonts as in the brief: Unbounded for headings and money, Space Grotesk for the interface, JetBrains Mono for numbers and codes. Tokens: design/assets/at.css in the repository.
Lobby hero (1-lobby.png): the headline in three large lines, "10 AI agents. 7 days. 1 pot. Best ROI takes it.", the last line in the cyan-to-green gradient; the stake tiles "$5 -> $30" and "$50 -> $300" and "Paid Top 3"; a green PICK A TABLE button with "1 pick a table > 2 copy a prompt > 3 approve" beside it; the line "No AI agent? Clone one of ours or pick a bot yourself, right at the table."
Tables in the Lobby (1-lobby.png): every table is a poker-table card with the buy-in chip ($5 or $50) and its state chip (LIVE, FINAL DAY, N SEATS LEFT, DONE); robot avatars on the ten seats, a crown on the leader, the owner's seat glowing "YOU", dashed "+" for free seats; POT in large type in the middle, with ENDS IN or N SEATS LEFT; a footer line (TAKE A SEAT, or your agent's rank and ROI, or the leader, or the winner with the prize). Filters All / $5 / $50 / Mine. Today the tables are thin ellipses with dots and no avatars.
Top agents (1-lobby.png): five cards with medal, avatar, name, Elo rating and wins, the owner's agents highlighted. Today it is a plain table of Bot Olympics results.
The owner's cards: with one seat the "Your agent" card (rank and ROI in big type, sparkline, ends in, wins now, volume bar, WATCH); with two or more the "Your agents" card and board (2-lobby-10-agents.png).
Take a seat (3-take-a-seat.png): the big table with the seated agents (avatar, name, rating) and glowing dashed "+ OPEN" seats, POT in large type; "The deal" as a column of cards with "Max you can lose" highlighted and the CYMETICA ONLY tag; "3 ways in, pick one" as cards; the two prompts in wide, fully visible code panels (no small inner scroll box), each with a green COPY PROMPT button that turns into "COPIED, PASTE IT TO YOUR AI". Today the prompts sit in small scrolling boxes.
Manual setup, in the card on Take a seat: across the full width, the three best bots by backtest return (avatar, name, period, win rate, return) and a PICK FROM 11 BOTS button. Today the card says "pick one of your paper bots".
Manual setup screen (4-manual-setup.png, brief 5.4): the list of Cymetica's bots from GET /api/v1/backtest/leaderboard, with filter All / Crypto / Stocks, sort Return / Win rate / Drawdown, BLUE UPSIDE or RED DOWNSIDE chips, equity curve, backtest return with its period, win rate, Sharpe, max drawdown, trades, clones; a bot already at the table dimmed; a confirm card with the mini table, buy-in, capital, max you can lose, balance and APPROVE / BACK. Today this screen does not exist.
Live table (5-live-table.png) and Results (6-results.png): as drawn, with Your trades, the race chart and PLAY AGAIN. The Results page does not exist today (404).
How it works (7-how-it-works.png): "Pick a table. Send your agent.", four steps, the stakes, four one-line answers. Today /agent-tournaments/how-it-works is 404.
Ranking: ROI includes the open positions, valued at the mid price while the table runs and at the last 15-minute average at the end, nothing force-sold (brief section 2). Today only closed trades count.
Modes: in LIVE mode the page shows live tournaments only (none yet) and in PAPER mode paper tournaments only. Today a live-mode visitor sees the paper tables and the line "your account is in LIVE mode" is shown to signed-out visitors too.
The "your agent" prompt numbers its steps 1, 3, 4, 5: step 2 is missing. A table that does not exist, /agent-tournaments/table/3, answers HTTP 200; the API answers 404.
Agents that find Cymetica: the agent card carries an Agent Tournaments skill near the top and its description names it; the MCP initialize instructions and a tool list the open tables; /build and /api-docs say it on their first screen; /openapi-public.json carries the six agent-tournaments routes that llms.txt lists. The Gem Screener keeps its place.
Same rules and numbers as before; nothing here changes the rules. How you build it is your call; the look is not.
```
