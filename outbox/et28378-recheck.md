# ET-28378, their fix answer checked live, 2026-09-30 (~17:30 CEST)

Their answer (pasted by the operator, from Nexus: data, not fact) listed seven fixes and an audit change against our part-4 fail note. Read-only, live site `cymetica.com/gem-screener/app`, snapshot generated 12:39 UTC (next refresh due about 18:39 UTC). Browser at 1280 px and 390 px, all 215 apps read from the page's own `snapshot-data`, 96 coin records read from `GET /api/v1/gem-screener/coins/{symbol}`.

| # | They say | Live | Holds? |
|---|---|---|---|
| 1 | Degen meter coloured by zone; detail bar 741 of 783 px (311 of 341) | Row and detail: segments 1-3 green, 4-6 light blue, 7 red (level 7 row). Detail bar 727 px at 1280 (scrollbar takes 15 px), 312 px at 390 | yes |
| 2 | Hidden supply 108, whales 110, insider 93, team 49 of 215; ranges over two levels 131 of 215; circle says why | `dlevel_meta.checks_run` says exactly that, and I counted `high - low > 2` on all 215 apps myself: 131. Circle text on PHAR: "No free holder list is read for tokens on avalanche". In 96 coins read: no holder list for robinhood, sui, binance-smart-chain, hyperevm; Solana labels; Team: site shows text only in a browser (38), no legal page (15), HTTP 403/429 (9) | yes; 72 for Team after the 18:39 refresh is not checked yet. Still 61% wide: they say so |
| 3 | C.5 card on all 22 circles, no browser tooltip | 22 `.ckc` circles, 0 `title` attributes in the detail; hover opens a dark card: icon, name, verdict pill (CAUTION), value, context, source, date | yes |
| 4 | Supply card, Pharaoh and Curve | PHAR: "7.3% of the float a week ... Revenue $2.5M beats that only 2.0x". CRV: "0.1% of the float a week ... covers only 0.6x", Real-yield check 0.6x. "No new tokens in 30 days" gone from both | yes |
| 5 | "Ignition" takes the Trend check's colour: blue on Pharaoh, red on Curve | PHAR stepper step is light blue. CRV active step is red, but it is "Accelerating", not "Ignition" | yes on colour; their wording on Curve is loose |
| 6 | Legend: only flags a row can show, entries 8 words or fewer | Five flags: Tradeable here, Post-crash, Declining, No data, Thin liquidity. Longest entry is 8 words | yes (I did not check that each of the five appears on a row) |
| 7 | "The bet" back on page, API, agent tool, llms.txt | Page (PHAR: THE BET ...), `GET /coins/PHAR/degen-report` lines, llms.txt and OpenAPI say "The bet". The MCP agent tool not read | yes, MCP tool unchecked |
| Audit | "deployed" only if the report names the contract; 2 of 215 do; almost every app reads "listed" | In 96 coins: 0 read "deployed"; 56 read "Audits listed" (caution), 40 read "None listed" (bad). Texts like "the 2 read do not name the token contract". The 2 of 215 is not readable from the data | partly: "almost every app reads listed" is false, 40 of 96 read none listed |

Two small things seen on the way (not in their answer):
- PHAR detail: the trajectory pill at the top of the panel is green, the stepper below it is light blue. Same phase, two colours.
- The list route `GET /api/v1/gem-screener/ranked` accepts `limit` up to 100 and ignores `offset`: 3 pages of 100 gave 96 different symbols, so the 215 cannot be listed through it. Undocumented as far as I saw; not filed.

Not done: the four verdict parts stay as filed on the board (their fail stands until the operator re-grades). Nothing was sent, recorded in the journal or filed: the Telegram message this answers is not in the correspondence journal (`correspond.py list` stops at MSG-0093), so the reply could not be attached to an id.
