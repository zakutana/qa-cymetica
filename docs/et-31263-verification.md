# ET-31263 Agent Tournaments follow-up: verification

Read 2026-10-14 ~07:30 UTC, after Nexus's Telegram message "Your Agent Tournaments follow-up from Build it Better is live". Reads only: `/api/v1/agent-tournaments/lobby`, `/openapi-public.json`, `/.well-known/agent.json`, MCP `initialize` and `tools/list`, the lobby at 1440 and 1920 in headless Chrome and the built-in browser, table pages 11 and 14 (scratchpad `tour_check.py`, `tour_page.py`). The spec is `outbox/agent-tournaments-next/request.md` (five items, no "Done when"; each item is read as its own check).

| # | Item | Result |
|---|---|---|
| 1 | Flash tables: 1 day, FLASH chip, Flash filter, countdown in hours, Results at the end, a new one when one fills | PASS on what can be read: Flash Micro #13 ($5) and Flash Pro #14 ($50) open, `days: 1`, FLASH chip, filter All / $5 / $50 / Flash / ET10 / Mine, "runs 1 day"; rules scaled (min volume $10.71 / $107.14 = 3/7 of capital, ET10 85 / 42 / 14). Results and the refill need a table to finish or fill |
| 2 | ET10 tables at 100 and 1,000 ET10; pot to the top three in ET10; deal panel, table card and Results say ET10 | FAIL in part: the tables exist (ET10 100 #15, ET10 1K #16) and their cards read "1,000 ET10" / "0 ET10", but the lobby's hero card shows ET10 1K #16 with a buy-in badge of **"$1,000"** (`.at-hero .at-buyin`). The API carries the same mix-up: on both ET10 tiers and tables `buyin_usdc`, `pot_when_full_usdc` and `prizes_usdc` hold the ET10 amounts (et1k: `buyin_usdc` 1000, `prizes_usdc` [6000, 3000, 1000], `pot_when_full_usdc` 10000), so an agent reading `buyin_usdc` sees a $1,000 seat |
| 3 | Top agents: ROI and "now" inside the card at every width | PASS: ROI on its own line, NOW beside it, names cut with an ellipsis, the medal on the avatar's corner; nothing past a top-agent card at 1440 or 1920. But the new table cards repeat the old spill: on ET10 1K, ET10 100, Flash Pro and Flash Micro the "Open · 10 seats left" chip runs 77, 74, 44 and 56 px past the card's right edge at 1440 |
| 4 | Pick the winner, simpler | NOT TESTED: picks are open only while a table is open and for its first 24 hours; every running table is past that and the open ones have no seats, so no pick panel renders (tables 11 and 14 read) |
| 5 | AI agent front door | PASS: MCP `initialize` instructions open "Agent Tournaments: 10 AI agents, 7 days or 1 day, best ROI takes the pot ..." with how to join; tools `agent_tournaments_open_tables`, `agent_tournament_join`, `agent_tournament_take_seat`, `agent_tournament_seat_status`; the agent card's first skill is `agent-tournaments`; `POST /api/v1/agent-tournaments/join` is in the OpenAPI ("one call for an agent with a fresh API key ... returns the approve link") |

Not a platform defect, for the record: Nexus's message says the Flash figures are "3/7 of the week's figures"; they are 1/7 of them (3/7 of the capital), as the API's own rules text says.

Verdict: the operator's.
