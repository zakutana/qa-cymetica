# Laborka v3: sedm sekcí — plán, 2026-10-11

v2 (2026-09-23, fáze V0–V11, všechny hotové) je v gitu: `git show 7122f3d3:docs/laborator-plan.md`.

## Pro tebe

| # | Sekce (na stránce) | Co dělá | Kdo vybírá |
|---|---|---|---|
| 1 | Our cards | 10 nejlepších event karet podle našeho backtestu po poplatcích, doplňuje se, jak roomy končí | my, bez Nexuse |
| 2 | Nexus cards | jako dnes, jen karty | Nexus |
| 3 | Bots | všech 22 druhů × 6 nastavení systematicky, nejlepší dostanou druhé okno | my i Nexus |
| 4 | Head-to-head | vylepšený bot (vítěz ze sekce 3) proti původnímu nastavení | my |
| 5 | Memecoins | FOMO Radar + Hot headlines (Hot dnes na stránce chybí) | studie |
| 6 | Outsider | jednou denně cizí agent bez naší paměti objeví Cymeticu, řekne „wow" nebo ne, sám vybere, co by koupil a jestli si sedne k turnaji; jeho tipy měříme | cizí agent |
| 7 | Desk | moje volná laboratoř: jediný cíl, prokázat, jak se na Cymetice vydělá; návrhy a feedback pro Cymeticu jdou přes tebe | já |

**Paměť ve všech sekcích, i v mojí:** zčásti už v laborce je. Je tu deník, lekce a „co dál" a Nexusovy tipy ani varianty botů se neopakují. Nové sekce 1, 4, 6 a 7 ji ale nemají, každá část si pamatuje po svém a lekce nejsou rozdělené po sekcích. Nestavím ji tedy znovu, jen ji rozšiřuju na všech sedm sekcí: každá sekce bude mít záznam „co už jsme zkusili a jak to dopadlo". Než něco spustí, podívá se do něj a stejnou věc nezopakuje. Výjimka je, když výsledek potřebuje druhé okno nebo se platforma změnila, a to se napíše. Ke každé sekci se navíc vede krátké „co víme" (nejvýš 10 řádků), které se po každém výsledku doplní nebo opraví. Odtud vychází „co dál", které uvidíš v sekci i v ranním přehledu. Outsider je výjimka: má být pokaždé čerstvý. Jeho běhy si zapisujeme my a sledujeme, jak se jeho dojem mění.

**Na bod 3 „to už děláš, ne?":** zčásti. Všech 22 druhů jsme naklonovali, ale z kombinací druh × nastavení jsme měli jen 65 a indikátory jednou. Mřížka to dodělá.

**Co jsem rozhodl za tebe** (stačí slovo a změním to):
- Pravidlo „3× stop-loss po sobě = zahodit" zahodí *to nastavení*, ne celý druh. Ráno jsem psal opak, ale dnes chceš otestovat všechny konfigurace a kód to tak počítal i dřív (pro jednoho bota). Celý druh jsem dnes ráno blokoval jen já. MACD Hunter a RSI Sniper se tedy vrátí s Nexusovým nastavením z NEX-0137. Nastavení, které 3× prodělalo, už nikdy.
- Sekce 1, 6 a 7 obchodují podle našeho úsudku, vedle Nexuse, ne místo něj. Zapsáno jako tvoje rozhodnutí z dneška, tvými slovy (skill laborator, „Seven sections").
- Outsider si k turnaji sedne jen ke stolu, který je podle jejich API papírový a nestojí nic skutečného. Místo u stolu navíc potvrzuješ ty na jejich odkazu (tak to mají v llms.txt).
- Všechno dál jen na papíře. Skutečné peníze jen jako návrh tobě, až něco vydělá dvě okna po sobě.
- Laborku spouštíš dál ty: při stavbě ji jen testuju a čtu, žádný tah sám nepustím.

**Hotovo, když:** /lab má 7 záložek a v každé nahoře čísla (čistý výsledek po nákladech, počet pokusů, jak jisté). V každé sekci běží první pokus a testy jsou zelené. Bude to na 2–3 sezení, po fázích, každá v commitu.

---

## Pro implementaci (číst nemusíš)

### Context
Operator, 2026-10-11, three messages, quoted verbatim in `.claude/skills/laborator/SKILL.md` ("Seven sections") and pinned in `tests/meta/test_pipeline_decisions.py`: clearly separated sections 1–6; a seventh "where you are master", whose sole goal is to prove how money is made on Cymetica, with requests, proposals, feature requests and feedback sent to Cymetica through the operator; and in every section a record so nothing is done twice and a memory that keeps it moving forward. Today a room's section is derived (`qa/lab_report.py:_product`, `KIND_PRODUCT`). /lab has three tabs (`scripts/lab_page.py:1706`). No path opens a card room from our own idea (`scripts/lab.py:2148`; `scripts/paper.py:_guidance` refuses non-Nexus ids). Bots have no grid (44 of 308 variant cells proposed; 1 indicator change ever). H2H has no reader (F4 open). Hot is only in `brief`. The outsider view and the desk do not exist.

### Data model (`qa/rooms.py`)
- `SECTIONS = ("own-cards", "nexus-cards", "bots", "h2h", "memecoins", "outsider", "desk")`. `open_strategy(..., section=None)` stores `section` on new strategy rows and validates it.
- `section_of(row, proposals)`: the stored value, else the mapping today's `_product` already makes (card → nexus-cards, bot → bots, fund → hidden as today). No existing room changes section (memory: improving a derivation rewrites the past).
- `qa/lab.py note_proposal` gains `section` and a card kind (today bot-shaped). `scripts/paper.py _guidance` accepts an `OUR-` id that `rooms.on_record` knows ("ours, proposal OUR-NNNN"), and still refuses anything else.

### Sections
1. **own-cards** (`scripts/lab.py own_cards()`, a new tick step after the backtest search): a top-10 book (the strategy's own parameter, not a brake: the skill's "0.48 % of the book a room under a 60 % ceiling, the only count limit" is reconciled to say so) of the live cards whose basket passes the SAME gate his picks pass (their backtest after fees, longest window priced whole: `gate`/`search` already compute it), best first, refilled as rooms close; same stake (`_leg_stakes`), window 7 d, room stop `NIGHT_STOP_PCT`; no Nexus question. Never called a control for section 2, on the page or in a test (the control group of 2026-09-21 stays refused). `card_rules.py` becomes a second chooser only if its forward verdict passes (~200 cards).
2. **nexus-cards**: `night_promote` cards, unchanged.
3. **bots**: `qa/lab.py grid()` = 22 species × bands {species defaults, 5/20, 10/20, 10/30, 15/40, 20/60}, plus every band Nexus names (`bot_bands`). Walk: fill the untried cells up to the trading cap (`wave.MAX_TRADING` 50), 500 USDC each, 7-day window; cells that survive get a second window (a claim needs two); indicator moves (`clone.indicators`, WTA only) only on the top species. Reuse `wave.launch_one` (clone → room+criterion → settings → read-back → fund → enable) and `bot_variants`' proposal records. ONE walker: `VARIANT_MOVES`/`bot_variants` is retired into the grid (two walkers would propose on the same clone, and `clone.settings` refuses while a room runs). The 3-SL rule (`qa.lab.discarded_bots`, per clone since deep pass T11) retires the CELL: the species-wide `_thrown_species` in `scripts/lab.py` (added 2026-10-11) becomes (species, band). Then `lab.py launch NEX-0137`.
   **Before the grid:** the sampler fix (NEXT.md 2026-10-11): 41 bots already starve cards/positions/history in a 90 s round, and the grid adds more.
4. **h2h** (`scripts/h2h.py`, F4): store the slug (`state/h2h.jsonl`, intent/outcome), `results` reads `/head-to-head/mine`; a section-3 cell that survived a window → matchup improved (that clone) vs original (a clone of the species at defaults), 7 d, one room in h2h with both bot legs, both sides kept trading by `wave.py resume` for the 7 days (wave 0's defaults paused within an hour: without it the matchup is one trade), judged on our own P&L of both; their scoreboard shown beside it (stuck "running" is already a check, `tests/rest/test_a_finished_matchup_reads_finished.py`).
5. **memecoins**: as today; add the Hot reading (`qa/hot.py`, `lab.jsonl hot_reading`) to `qa/lab_report.py` and the page.
6. **outsider**: `.claude/agents/outsider.md` (tools: WebFetch, WebSearch only, no repo, no memory, model sonnet/high). **The first step of P6 proves the independence before anything is built on it:** a throwaway agent from the definition reports what it already knows about Cymetica / Nexus / EventTrader; if anything of ours leaks (CLAUDE.md, the memory index), the outsider runs as a separate process outside the repo (`claude -p` from a cwd with no CLAUDE.md, or a plain API call), never as a subagent. It starts at cymetica.com and its llms.txt and returns JSON: per surface (Gem Screener, Agent Tournaments, Agent League, cards, bots, Nexus) a 0–10 "would I put money here" + why, its picks (coins, cards by id, species + band, a tournament table), where it got stuck. A run is capped at a fixed number of fetches (WebFetch bypasses our client, its brake and its captures) and the count goes in its diary. `qa/outsider.py` (pure: validate, map picks to allowed actions) + `scripts/outsider.py record|report`, diary `state/outsider.jsonl`. Its cards go to paper at half stake WITHOUT the backtest gate (the existing "untested, half stake" path), so the number is its judgement, not gate∩stranger; its bots run its band; its Gem Screener coins are forward-tracked vs BTC at 1/7/28 d (pattern `qa/hot.py forward()`, `qa/fomo.py`). Stumbles → reproduced through our client, then a gap to the operator or a filing. Tournament seat: llms.txt documents it (`POST /api/v1/agent-tournaments/tables/{id}/seat` {"instance_id"}, X-API-Key, paper buy-in, "the seat waits until the owner approves at the returned approve_url"), so the owner's click is the operator's. New `rest.agent_tournaments` rule in `components.yaml` with `closed_body`, written only after `/rules` and `/lobby` are read and the body confirmed; refused unless the table reads paper by their API and the buy-in is paper (pattern `cloned_bots.fund`); otherwise its wish to join is a gap sent through the operator.
7. **desk**: `docs/lab-desk.md` (living: goal, hypotheses, running, next, sent to Cymetica). A desk step = one Opus agent that may open paper experiments in any product (section desk), ask the operator one question, and draft feedback or feature requests (`@EventTraderQABot` block, recorded with `correspond.py sent` + a2a copy; BB requests to `outbox/`). Proof = net after costs over two windows; real money only ever as a proposal to the operator.

### Memory across sections
- **What exists and is kept, not rebuilt:** the diary and its `--lesson` / `--next` (`lab.py log`, `lab.py resume`), `docs/lab-manager.md`, `NEXUS_KNOWN`, the gate's records of his refused picks, `answers_read`, `tried_variants` per clone, `_species_cloned`. What is missing: one view all choosers share (each of those remembers for its own mechanism only, and sections 1, 4, 6, 7 have none), and lessons per section.
- **Register, derived, not a second store** (`qa/lab_register.py register(rooms_rows, lab_rows)`): one row per (section, key) -- key = card id, species+band, matchup pair, outsider run date, desk hypothesis id -- with status (running · survived · refuted · inconclusive · retired), the net after costs, the room and the date. Built from rooms (section, plan legs, verdicts), proposals and the desk's hypothesis rows, so it cannot disagree with them. A register of what was tested, not a diary of sessions.
- **Every chooser asks it first and is tested for it:** own-cards skips a card judged in the last 30 days; the grid skips a cell with a verdict except a survivor's second window; a Nexus pick already tried is not reopened, and the brief tells him how it went (today's "his proposals" lines); the desk does not reopen a refuted hypothesis without a stated change (new window, platform moved). A retry always carries its reason in the room's `why`.
- **What we know, per section** (`docs/lab-knowledge.md`, at most 10 lines a section, the Nexus part being today's `NEXUS_KNOWN`): after a verdict the manager adds or corrects a line (`lab.py log --lesson --section <s>`); a line that stops being true moves to an archive at the bottom with its date, never silently deleted. `lab.py brief`, the desk agent and the morning report read it; the outsider never does (it must stay a stranger: its runs are recorded by us and compared over time).
- **What next, per section**: derived from the register (the grid's next cells, the cards waiting for a slot, the desk's next hypothesis), shown at the top of each tab under its three numbers and in the morning tiles.

### Tick and decide (`qa/lab.py decide`, `scripts/lab.py tick`)
Steps: … promote (2), own_cards (1), grid (3), h2h read (4), fomo/hot (5) … New decide values: `outsider` (once a day) and `desk` (idle, alternating with `hunt bugs`). Priority: report > gap > answer > question > hunt sweep (their side moved: acted on within a tick, CLAUDE.md 2026-09-25) > outsider > desk / hunt bugs.

### Page and morning report
`scripts/lab_page.py`: `SECTORS` → the seven sections in order, English names (Our cards, Nexus cards, Bots, Head-to-head, Memecoins, Outsider, Desk), each tab opening with three numbers (net after costs, experiments, how sure), Live/Done/Archive kept; explanations only in tooltips; Cymetica palette. `qa/morning.py`: one tile per section. Fix the sector lists that disagree (`rooms.SECTORS`, `lab_report.PRODUCTS`, `lab_page.SECTOR_NAMES`, `morning.SECTOR_NAMES`).

### Rules and docs
- `.claude/skills/laborator/SKILL.md`: the seven sections and the three decisions (P0), the new decide values (P5, P6), the top-10 book reconciled with "the only count limit" (P4).
- `CLAUDE.md` "Who decides what to trade": one sentence (not a pin): sections of our own judgement beside Nexus's lane, never in its place (P0).
- NEXT.md: one line carrying the open phases of this plan (the session-start reminder checks it).

### Phases

| Fáze | Co | Hotovo, když | Stav |
|---|---|---|---|
| P0 | rozhodnutí zapsaná a zamčená, plán v3 v repu, řádek v NEXT.md | test pinů zelený se třemi novými rozhodnutími | |
| P1 | `section` + stránka se 7 záložkami + ranní dlaždice + Hot na stránce | screenshoty desktop a 390 px; staré roomy tam, kde byly | |
| P2 | registr + `docs/lab-knowledge.md` + „co dál" v každé záložce | každý existující room v registru pod svou sekcí; test pro každého vybírače, že odmítne, co registr drží; lekce po sekcích čte `brief` | |
| P3 | oprava sampleru, mřížka, 3-SL po buňkách, `launch NEX-0137` | řádek mřížky „buňky X/132, obchoduje N/50"; roomy z NEX-0137 otevřené | |
| P4 | naše karty (sekce 1) | první OUR karetní roomy běží, v jejich stopě žádná otázka Nexusovi | |
| P5 | desk (sekce 7) | `docs/lab-desk.md` se 3+ hypotézami, 1+ pokus běží, první návrh pro Cymeticu předán | |
| P6 | outsider (sekce 6) + zápis místa u turnaje | jeden běh zapsaný: verdikty, tipy, zakopnutí; jeho coiny se sledují | |
| P7 | h2h (sekce 4) | jeden zápas s uloženým slugem a přečteným výsledkem | |

Order: P0 P1 P2 P3 P4 P5 P6 P7. Each phase: tests first (red), then code, `pytest tests/meta tests/repo` to a file with the exit code read, commit on `main`, no push; the row gets `hotovo <hash>` when it ends. The meta-test ceiling stays where it is: the three-sector pins in `tests/meta/test_pipeline_lab_page.py`, `test_pipeline_lab_report.py` and `test_pipeline_morning.py` are rewritten for seven sections in P1, and new cases go into existing tests as helpers. `/lab` checked in the browser at desktop and 390 px after P1 and at the end. No live tick during the build (the loop is off, the operator turned it off): each phase is verified by tests and read-only reads (`lab.py brief`, the served `/lab`, room listings); the first real tick is theirs to start.
