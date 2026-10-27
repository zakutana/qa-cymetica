# ET-32932 Agent Casino (v4): verification

Read 2026-10-27, after BB-SHIPPED (09:10 UTC; the deadline was 16:38 UTC). Reads only: their pages signed out in headless Chrome at 390, 1440 and 1920 px (`v32932.py`, `v32932b.py` in the session scratchpad), `/api/v1/agent-tournaments/lobby`, `/llms.txt`, `/.well-known/agent-card.json`, `/.well-known/mcp.json`, and table 15's race through the operator's signed-in pane. Rows are numbered by `request.md` line (0 to 10, then the checks).

**The ticket.** Our BB-CHANGE (real money to the human-reviewed slot, 26 Oct 16:38) changed nothing: they re-issued the same BB-SPEC, we accepted, it built automatically. Their message of 27 Oct says what is out: joining with a wallet, and real-money tables ("COMING", opened only when the team decides). That is the BB-CHANGE scope, so it is not counted as a defect below.

## Look beside the pictures

The lobby is the picture at 1440 and 1920 (chips, headline, three icon tiles, 4x / 2x podium, PICK A TABLE, switch and filters, cards with their clock). Table 21's page is the picture's table: rail, lit edge, six open seats with chips and cards, deck, 1ST / 2ND spots. Four differences:

| | Picture | Live |
|---|---|---|
| SEE IN THE UNIVERSE | 172 x 26 px, small | 179 x 44 px. Their rule in `bb-responsive.css` gives every link in main `min-height: var(--bb-touch)`; `.at-uni` has no `min-height: 0`. It is the "too huge" size the operator cut on 26 Oct. |
| Table page 15 % smaller | `zoom: .85` | `.at` zoom 1, column 1,240 px at 1440 and 1920, same as before |
| Suede on the table panel and cards | fibres + nap in #0d1520 | panel and cards flat `rgb(13, 21, 32)`, no background image; a grain exists on the felt only (`--at-suede` on `.at-tbl`) |
| Table #16 | six seats | still 10 (see line 1) |

## Lines

| # | Result | Evidence |
|---|---|---|
| 0 | OK | Logo AGENT CASINO, titles "Agent Casino: 6 agents, 1 table, best ROI wins", felt, How and Leaderboard copy: no "Agent Tournaments" outside API URLs. 301 for `/agent-tournaments`, `/leaderboard`, `/how`, `/table/15`, with the query kept (`?x=1&lang=en`, `?window=all`). API path and the 11 MCP tool names unchanged. |
| 1 | **Not met** | New tables #21 to #25: 6 seats, 1st 4 buy-ins and 2nd 2 ($5: $20 / $10; $50: $200 / $100; 100 ET10: 400 / 200 = 2/3, 1/3), cards show 1ST and 2ND, no 3RD, How says top 2 take 4x and 2x. But **table #16 (1,000 ET10) is open with 10 seats and 3 paid places 6,000 / 3,000 / 1,000**; the lobby card says "10 seats left" and anyone can seat it (`GET /api/v1/agent-tournaments/tables/16`: `seats_total` 10, `seats_free` 10, `paid_places` 3). Finished tables keep their 10 (history). |
| 2 | OK, Live closed | PAPER \| LIVE switch beside the filters, paper filters hidden on LIVE, live filters All, $1, $5, 1H, 5H, 1D, Mine, no reload. LIVE lists three cards ($1 1H ANY WALLET, $1 5H ANY WALLET, $5 1D PROVEN) marked COMING / NOT OPEN YET; the "Live tables are not open yet" sentence is still there. The header pill being the same setting: not checked (signed out). |
| 2b | Partly | Buy-in once and a small clock with the length on every card and table header, no FLASH word, icon tiles, no rules strip (a new "The deal" card on table pages), rail, deck, chips, honeycomb full width (`.at-shell`, 1,393 px of 1,440), back arrow centred (12 px each side). **Not met:** the Universe button size, 15 % smaller, suede (table above). |
| 3, 4 | Out of this release | As above. |
| 5 | Partly | The bands show on the Live cards; the chain read is part of the wallet join. |
| 6, 7, 8 | Not checked | The Coach tab and Risk are in the page code (CSS "the Coach tab: NEXUS coach on/off, and Risk 1..10") but no table has an owner column open: all five new tables are unseated and table 15 is finished. Tune and its log need a running seat. They say so too. |
| 9 | OK | Table 15's race (signed in): three merged markers carrying 5, 4 and 5 trades and five single ones, none touching at 1440 and 1920. |
| 10 | OK for Paper | `/llms.txt`, the agent card and `mcp.json` say Agent Casino, 6 seats, top 2 paid ($5 table: $20 and $10); no "10 agents" left. The wallet join is not described: it is not built. |

390 px: the lobby does not overflow (`wide: false`).

## Proposed verdict

FAIL with a note on the four items (table #16, the Universe button, 15 % smaller, suede), leaving the money part to the human slot. The note is `outbox/tournaments-v4/bb-verdict-note.txt`. Not sent: the verdict is the operator's.
