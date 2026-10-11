# ET-30773 Agent Tournaments: the 32 lines read against the live page

Read 2026-10-11 05:40-06:30 UTC, anonymous (the page, its API, llms.txt, the agent card, /apps, /build, /api-docs, the OpenAPI, the MCP tool list) plus the repo's own client for the MCP read. BB-SHIPPED 2026-10-10 22:50 UTC, on time; the deadline is 2026-10-11 21:38 UTC. **The verdict is the operator's; nothing was posted.**
Not done, on purpose: a seat request (POST /tables/{id}/seat is a write), anything signed in, anything that needs a running table, phone width (operator, 2026-10-08). Pixel spacing is left out too (operator, 2026-10-04).

**The look comes first, and it fails (operator, 2026-10-11: "to je nepripustne").** Put beside `design/screenshots/1-lobby.png` and `3-take-a-seat.png` at 1440 px, the live page has the structure and the colours of the design and none of its look: the site's plain header instead of the chip logo and the Lobby / Top agents / How it works bar; a small hero instead of the three-line display headline, with no PICK A TABLE button; tables as thin ellipses with dots instead of poker-table cards with robot avatars, a crown, YOU and a large POT; no All / $5 / $50 / Mine filters; Top agents as a plain table instead of five rating cards; the prompts in small scrolling boxes; Manual setup without the bot list. The Gem Screener came out as drawn; this did not.

**Tally: 7 PASS, 8 PARTIAL, 7 FAIL, 8 NOT CHECKED, 1 skipped (29), 1 n/a (31).** (Lines 1 and 15 are graded FAIL on the look.)

| # | Line | Read | Why |
|---|---|---|---|
| 1 | Page at /agent-tournaments "to match the attached design" | FAIL | Exists and carries the structure and colours, but not the look (see above); six of the seven screens in the brief are not there as screens (10, 19, 21, 22, 28). |
| 2 | The idea | PASS | Hero, tables of 10 seats, 7 days, best ROI %, stakes $5 and $50. |
| 3 | Rules numbers | PARTIAL | Every number matches: buy-in 5/50, capital 25/250, max loss 30/300, prizes 30/15/5 and 300/150/50, 60/30/10, volume 75/750, starts at the 10th seat. "No rake in the pilot" is not stated anywhere. |
| 4 | Cymetica only | PASS | "Where it trades: Cymetica only"; "only the seated bot's own closed trades on Cymetica count". Live mode is closed (C1). |
| 5 | Owner approves, limits | PARTIAL | Owner approves every seat, one seat per owner, one copy of each bot, 2x cap (as "a trade larger than 2x the bot's capital is not counted"). Missing: the monthly auto limit; "same-owner or same-table trades do not count as volume". |
| 6 | Privacy while it runs | PASS (stated) | Rules say it; no table is running, so it cannot be tested. |
| 7 | Paper mode follows the switch | PARTIAL | Paper tables only, paper wording in the prompts. In LIVE mode the page still lists the paper tables and says "switch the pill to Paper to take a seat"; the brief says live mode shows live tournaments only. |
| 8 | Flow | PARTIAL | Lobby, table page (take a seat is merged into it), prompt: yes. Manual setup picks YOUR paper bots, not Cymetica's (19). Live table and results need a running table. |
| 9 | Look | PARTIAL | Colours read from the live page: only cyan, green, blue and slate, no amber, orange or yellow. Fonts are the site's Archivo Black and JetBrains Mono, not Unbounded and Space Grotesk. |
| 10 | Header | FAIL | The site's own header. No poker-chip logo, no Lobby / Top agents / How it works links, no pots figure, no "your pill". |
| 11 | Lobby hero | PARTIAL | "10 AI agents. 7 days. Best ROI takes it." ("1 pot." dropped), 5 to 30 and 50 to 300 tiles, "1 pick a table / 2 copy a prompt / 3 approve". No PICK A TABLE button seen. |
| 12 | One seat: Your agent card, filters, top 5 by Elo | NOT CHECKED / PARTIAL | Signed-in card not read. No All / $5 / $50 / Mine filter. Top agents are ranked by return and come from the Bot Olympics (our own "lab Wave 2 ..." clones lead it), not by Elo and not from the tournaments. |
| 13 | 2+ seats hero | NOT CHECKED | Needs seats. |
| 14 | Your agents board | NOT CHECKED | Needs seats. |
| 15 | Table cards | FAIL | A thin ellipse with ten dots, pot, "10 seats left"; the brief draws poker-table cards with robot avatars, a crown, YOU and a large POT. Live, final-day and done states need a running table. |
| 16 | Take a seat | PASS | The deal (buy-in, capital, max loss, prizes when full, volume for a prize, Cymetica only), "3 ways in, pick one". |
| 17 | Way 1, your agent | PASS | Prompt block, "Copy prompt". No invite code and no 24 h: their own design (API key plus an approve link), which the brief left to them. |
| 18 | Way 2, clone | PASS | No picker on the page; the prompt tells the AI to read the backtests, pick one not at the table, clone it in paper mode and seat it. |
| 19 | Way 3, manual setup | FAIL | "Pick one of your paper bots", sign-in needed. The brief asked for Cymetica's bots, the best three by backtest and PICK FROM 11 BOTS. |
| 20 | Prompts | PARTIAL | Written by them, one block per table with link, stakes, max loss, min volume; the owner approves once through approve_url; never asks for a password or key; daily rank and ROI; paper wording. **Defect: the "your agent" prompt numbers its steps 1, 3, 4, 5.** |
| 21 | Manual setup, bot list | FAIL | No list, filters, sort, equity curves or team chips. |
| 22 | Manual setup, confirm | FAIL | No confirm card with the mini table, balance and APPROVE / BACK seen. |
| 23 | Live table | NOT CHECKED | "Standings start when the 10th seat is approved." The table API carries `standings` and `your_trades`. |
| 24 | Leaderboard | NOT CHECKED | Needs a running table. |
| 25 | Your trades | NOT CHECKED | `your_trades` is null with no seat. |
| 26 | Race chart | NOT CHECKED | Needs a running table. |
| 27 | Results | NOT CHECKED | No results page exists yet (/agent-tournaments/results is 404). |
| 28 | How it works | FAIL | /agent-tournaments/how and /how-it-works are 404; no link to one. |
| 29 | Phone | skipped | Operator, 2026-10-08. |
| 30 | Agents find it on their own | PARTIAL | Yes: llms.txt has an entry (8 % in, with the rules), /apps lists it, the API flow is rules, lobby, table, prompt, my-bots, POST seat, approve_url; a keyless POST is refused with 401; the Gem Screener keeps its place. **No:** the agent card has no skill and its description does not say it; MCP has no tournament tool (141 tools) and `initialize` is silent; /build and /api-docs do not mention it; `/openapi-public.json` has no `agent-tournaments` path although llms.txt lists them. |
| 31 | Left to you | n/a | |
| 32 | Check early | PASS | Live tables closed until entry and prize terms are set and published (the legal point). |
| C1 | Human slot, paper first | PASS | Paper tables run, live tables are "not open yet". |
| C2 | Name and logo are ours | PARTIAL | The name is. No poker-chip logo on the page. |

## Defects worth reporting (each needs a check first)

1. `/openapi-public.json` has no `agent-tournaments` path while llms.txt lists six of them.
2. The "your agent" prompt skips step 2.
3. `/agent-tournaments/table/3` answers HTTP 200 for a table that does not exist; the API answers 404 `not_found`.
4. A signed-out visitor reads "Your account is in LIVE mode".

## What to tell Cymetica (their call, not defects)

The ranking counts closed trades only (the brief valued open positions at the end); manual setup is own bots only; no How it works, results, or custom header; MCP and the agent card do not mention it.

## Their Telegram message of 2026-10-11 ("live in paper mode")

Matches the page and the rules API on every number it gives: 10 bots, 7 days, 60/30/10, 5 with 25 and 50 with 250, 3x volume, one seat per owner, 2x, Cymetica books only, three ways in, the API address. Recorded as REPLY-0154.
