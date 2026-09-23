# Laboratoř, která vydělává, a systém, který se stará sám — plán 2026-09-23

## Pro tebe

**Jak se mnou budeš pracovat**
- Ráno napíšeš `/loop jdi do laborky`, večer „jdu spát". Nic jiného. Připomenu ti jen tyhle dvě věci, a jen když jsou na řadě.
- Deep pass nech každý večer. Sám si určí, jak velký bude, podle toho, co se změnilo a kolik zbývá z tvého limitu. V klidný den trvá pár minut.
- Revizi po 10 dnech nemusíš hlídat. Udělá ji týdenní ohlédnutí uvnitř deep passu, a kdyby bylo potřeba víc, připomenu ti to.
- Chceš, aby stačilo říct jen „jdi do laborky" (bez `/loop`)? Řekni. Je to změna tvého pravidla z 12. 9., proto to sám neudělám.

**Zbytek aplikace nechávám**
- Hlášení bugů, ledger i deep pass fungují a vydělávají. Včera deep pass našel 27 skutečných chyb, mezi nimi díru, kudy mohl projít živý obchod.
- Navíc měním dvě věci:
  - systém přestane bobtnat: 864 testů hlídá nás a jen 97 jejich platformu, takže nový hlídač přibude jen výměnou za starý;
  - deep pass si sám určí velikost (viz výš) a CLAUDE.md se zkrátí, protože se čte při každém kroku.

**Co je teď špatně (změřeno)**
- **Memecoiny +21 972 % je chyba v datech.** Všech pět „nejlepších" má cenu z jiného páru. Po opravě vychází **−6,4 % na obchod po nákladech** (n = 1 447). Hot signál informaci nese (3× za 72 h: 13 % vs 7 % u kontroly), ale po nákladech zatím prodělává.
- **Laborka za 12 dní: 42 pokusů, 4 verdikty, 0 úspěchů.** Z velké části kvůli našim chybám v měření:
  - boti se počítají od špatného bodu (Bollinger je +3 %, ukazuje −9,7 %);
  - Nexusovy TP/SL se nikam nezapsaly;
  - pokusy zastavené ručně dostanou verdikt.
- **Boti:** mají ~20 nastavení (SL/TP, velikost pozice, trhy), která jsme nikdy nezkusili. Dva se sami vypnuli (MACD Hunter na −10 %, Bollinger po propadu zisku z +33,6 na +7,1) a nikdo si toho nevšiml.
- **Tvůj plán Pro je týdně na 80 %.** Všech 206 tiků laborky běželo na Opusu, ne na Sonnetu. To je teď skutečný strop, ne naše limity.

**Co se změní**
- **Jeden tab „Laboratoř"** s roomy Karty · Boti · Memecoiny · Fondy. Arena a každý nový produkt Cymetiky přibudou samy. V roomu uvidíš jen tři věci: kolik to vydělalo po nákladech, na kolika pokusech, jak jisté to je. Neúspěchy půjdou do archivu. Data z nich držím, bez nich by analýza neviděla, co nefunguje.
- **Pás bez našich stropů.** Platí jen papír, peníze v papírové knize a tempo Cymetiky. Laboranti jsou Python procesy (tokeny nestojí). Já rozhoduju a spotřebu hlídám sám.
- **Memecoiny poctivě:** „10 $ do každého hot signálu = X % po nákladech, stihli bychom Y %". Y změří rychlé čtení radaru (1 min) za ~týden.
- **Data, paměť, NEXT.md hlídají testy a stropy.** Úklid běží sám (první tik dne + deep pass) a archiv se zrcadlí na OneDrive. Ty nic.
- **Učení z chyb:** hooky mě za 10 dní zastavily 36× (24× stejná chyba) a nezlepšuje se to. Co se zopakuje dvakrát, dostane mechanismus, ne další poznámku.
- **Nové oddělení (propagační centrum):** skill + skript + deník. Údržba, deep pass, paměť i konzole ho najdou samy. Tweet vždy jen navrhnu, pošleš ho ty.
- **Podle plánu:**
  - každá fáze má „hotovo, když" s testy;
  - když fáze visí, připomínka se ozve sama;
  - každou noc deep pass (3 nezávislí čtenáři);
  - na konci jeden nezávislý audit celého plánu.

---

## Pro implementaci (číst nemusíš)

### Context
Operator, 2026-09-23: the lab is the main work (manager + technicians, product rooms, impact-only presentation, conveyor with no limits of ours, Nexus mainly but our ideas too, failures archived, data kept for later pattern-finding; bugs a side quest; idle → platform testing); memecoin numbers distrusted ("$10 into every hot signal — liquidity and time?"); the system must run itself (data, memory, deep pass, self-improvement as manager/developer/tester), reminders welcome; later departments (a promotion centre) must inherit all of it.

Measured this session (read-only):
- Lab: 42 STR experiments (cards 29, bots 6, funds 7), 4 verdicts / 0 survived, +419 on 21 421 staked. Bot verdicts baseline at first sample (qa/lab.py:880, 993). TP/SL never reach the criterion (scripts/lab.py:1914-1927). `verdicts()` ignores status (scripts/lab.py:1074-1078). STR-0008 has no position and its card is the BTC benchmark. 1 960 USDC parked in paused bots counts as deployed. samples.jsonl is not snapshotted. clones.jsonl is committed yet written mid-tick. board/brief ignore bots. Our caps never bound. The real limits are Nexus throughput, 242 "names nothing" re-reads and 5-day windows.
- Bots: PATCH `/cloned-bots/{id}/settings` has 31 fields; components.yaml declares 4 (L518-522); our code calls none. One clone per species (#119). No documented bot-config backtest: `run-backtest` is absent from openapi-public.json (capture 1904bd9e…, 2026-09-23), and `/backtest-labs/run` covers arb/funding/dex_replay only. Self-stops: MACD Hunter at exactly −10 % of 240; Bollinger at +33.6 → +7.1; Perceptron at ~−5 %. eae9b830 and c9d638ab were disabled by us (CLN-0018/0019).
- Memecoins: headline = mean of per-signal % (qa/fomo.py:450) over 1 611 positions / 251 tokens. PUMP alone is 19 987 of 21 973 points. `pair_changed`/`round_trip_cost` are used only by `stop_study`. The depth filter uses the newest reading (look-ahead, pinned by test_pipeline_fomo.py:553). The radar row carries price_usd, max_buy_5pct_usd, first_buy_seconds_ago, exit_signal and exit_reason (the response adds updated_at); RADAR_FIELDS keeps max_buy_5pct_usd but none of the others. There is no hot-since timestamp. The console polls FOMO every 20 min while hot rows live 2-3 min.
- Upkeep:
  - evidence 916/1000 MB, of which 345 MB/day spikes come from two listing walkers;
  - tracked tree +5 MB/day; pack 77 MB (+1.4/day, ceiling 150); audits/lab/fomo_signals.jsonl 20.7 MB re-committed per pass;
  - the archive bundle exists only on this disk; .claude/worktrees is 460 MB (branches with unmerged commits);
  - CLAUDE.md 750/750; memories 48/48;
  - NEXT.md 42.7 KB (61 ticked lines carry 32.5 k chars);
  - processes.py:1151 globs `*cymetica*`, which reads the web-qa-agent transcripts too (bug);
  - hook denials over 10 days: heredoc 24, backtick 7, state 5 (not counted by patrol);
  - get_usage: Pro plan, weekly 80 %; transcripts show the lab loop ran on Opus despite `model: sonnet`.

### Decisions (pinned verbatim, PINNED rows in the same commit, our reading in a separate paragraph)
In `.claude/skills/laborator/SKILL.md`, four tagged paragraphs:
1. *"Ja uz chci jen te posilat do laborky a o nic se nestarat, Proste chci se uz jen soustredit na hledani vydelecnych strategii. Takze jak pujdes do laborky musi se z tebe stat top laboratorni manager chapes. musis si to tam umet top zorganizovat tu praci, klidne si muzes spustit i laboranty (subagenty) na ruzne jine prace, protoze CyMetica ma vice produktu a porad budou pribyvat."*
2. *"Me zajimaji pouze impact data, podle kterych se muzu dal rozhodovat, jasne vysledky a zaden sum."* + *"TO je jedna skupina v laborce, to si spis predstavuji ze by mel byt jeden room. Dalsi sekce, room kde budem operovat a testovat jsou ti jejich boti, tam se mi zda ze zaostavame, musime vic otestovat jejich boty a ruzne kombinace atd."*
3. *"ty by nam mel poskytnout Hlavne Nexus, a ty jako manager s nim o tom diskutovat a klidne navrhnout i jine navrhy"* + *"Ale melo by to odsypat jako na pasu, zadne limity, proste co je slibne a dava smysl to se jde hend otestvoat."* + *"A neuspesne pokusy proste zahazujes at tam neni bordel, das je treba doa rchivu nebo enco"*. Our reading: this narrows "a strategy of ours never becomes a room" (skill L32, rooms.py:344). The 2026-09-10 CLAUDE.md pin stays untouched.
4. *"musis se ujistit ze ty data sedi a kdybychg se pak treba rozhodnul dat 10$ do kazdeho hot signaluz e na to je likvidita i cas vse koupit, ze proste ta strategie je realne a pujde exekuovat chapes."*

In CLAUDE.md, two tagged paragraphs:
5. *"Pamatuj muj cil je uz nikdy se o tyto veci nestart, chci uz si s teobu jen psat o cymetice a hledani strategii a neresit kod"* + *"Muzes mi klidne jako pripomionat veci jak s teobu rpacovat, ze treba ted spust deep pass, nebo uz je to 10 dnu melibychom udelat nejake review atd. atd. chapes. to klidne delat budu, poslouchat tvoje insturkce ale nechci na ne myslet ja."*
6. *"chci aby to vse automaticky platilo co jsme pospal i pro budouci vyvoj at uz je jakykoliv"*

Kept as they are: every existing pin; paper only; nothing starts by itself except a `/loop` they typed; pushing only in the deep pass.

### Phases

| Fáze | Co | Hotovo, když | Stav |
|---|---|---|---|
| L0 | Úklid a rozdělaná práce | patrol bez vlajky stropu; evidence ≤ 700 MB; ≤ 42 živých pamětí; oba reporty v žurnálu jako `accepted` | otevřená |
| L1 | Plán, rozhodnutí, místo v CLAUDE.md, revize celé architektury a jádra (brána před L2) | meta+repo zelené; CLAUDE.md ≤ 640 ř.; čerstvá session ukáže ≤ 1 řádek za plán; revize má verdikt po oblastech a každý její nález prošel triáží 2 ze 3 | otevřená |
| L2 | Poctivá čísla laborky (před 26. 9.) | Bollinger ≈ +3 % v `lab.py status`; ručně zastavený pokus bez pozice nemá verdikt; TP/SL z Nexusovy odpovědi v kritériu | otevřená |
| L3 | Memecoiny: pravda o číslech | stránka už nezávisí na deníku (fomo na `/lab.json`); `fomo_watch.py report` řekne „10 $ do každého hot signálu = X % po nákladech, n; stihli bychom Y %"; pět bývalých „nejlepších" je vyřazených | otevřená |
| L4 | Jeden tab „Laboratoř" | screenshot 2000 px viděný: roomy podle produktů, žádné titulky zpráv na dlaždicích; poznámka z tabu se objeví v `rooms.py unread` | otevřená |
| L5 | Pás | tik spustí variantu bota s jiným nastavením; jediný limit v `lab.py status` je 60 % knihy; odpověď se čte jednou | otevřená |
| L6 | Manažer | den `/loop` má ≥ 3× méně LLM kol než 72 při stejném počtu spuštění; hlášení ≤ 3 řádky; tempo podle limitu | otevřená |
| L7 | Údržba sama | `patrol --flags` tichý 7 dní; klidný deep pass v minutách; přepisy se čtou jen nové a jen z tohoto projektu | otevřená |
| L8 | Oddělení do budoucna | testovací skill + skript + deník se objeví v hlídce, zálohách a dlaždicích bez jediné úpravy | otevřená |

Each phase: tests first (red), then code, `pytest tests/meta tests/repo`, commit on `main`, no push. Its row names its done-when test ids and gets `hotovo <hash>`. First line of each phase session: class · needs · running (CLAUDE.md). Run `get_usage` before each phase and wait for the reset when the weekly figure is over 85 %. L0 is today; the rest start after the 15:00 UTC reset, one phase per session.

### Phase details

**L0 · Úklid a rozdělaná práce** (Sonnet · high)
- Record the Telegram message the operator confirmed sent on 2026-09-23 (bots stopping, several clones per species, bot backtest, memecoin pair switch, hot_since) with `correspond.py sent`, handle included.
- Run `keep.py archive --month 2026-09 --release`, then `prune_runs.py --apply`.
- Copy the bundle to `C:\Users\adamz\OneDrive\qa-cymetica-archive\` and compare hashes.
- `git cherry` the four `.claude/worktrees` branches. Name their unmerged commits, then clean them up.
- `prune_runs.py`: uncited captures of the bulky listing calls kept 1 day instead of 3. Test first in `tests/repo/test_prune_runs.py`.
- consolidate-memory down to ≤ 42 live memories. Shorten the retired lines to "— RETIRED date" (test_memories.py contract unchanged).
- One memory: the headline lacked the pair-change exclusion its sibling `stop_study` applied. Merge it into `a-correct-number-can-be-untradeable`.
- File the AIB paper-buy report: fresh prereg → full `tests` → `ledger.py --run` → `render.py` → `submit.py`.
- Memecoin pair switch: new check → commit → tag → run → ledger → `submit.py` (rule 5). Needs Opus for the check.
- Close LAB-0013 on the first lab tick.

**L1 · Plán, rozhodnutí, místo v CLAUDE.md** (Opus · high)
- Commit this plan alone as `docs/laborator-plan.md`.
- Move CLAUDE.md's descriptive file maps (~L397-634) into ARCHITECTURE.md. Keep in CLAUDE.md:
  - the sentences that drive behaviour (correspond.py, `rooms.py unread`, a2a `--confirm`);
  - `## What a task needs`, which render parses.
- Pins 1-6 as above.
- `reminders()` prints one line per plan, not per phase: a fixture in both directions in `test_reminders.py`.
- NEXT.md gets one line per phase, dated and written the day that phase starts, so the 14-day rule (`test_next_step.py:88`) counts each phase separately and budget pauses between phases cannot turn it red.
- A review of the whole architecture and core, and the gate before L2. The operator asked on 2026-09-23 how the plan could promise anything about a core this session had not read; the honest answer was that it could not. Five independent read-only readers, one per area:
  - the QA core (state, fold, measure, fingerprint, ledger, withdraw, prereg);
  - outbound and safety (submit, verify, bounty, a2a, correspond, channels, safety, client, components.yaml);
  - the lab and trading (lab, rooms, nexus, paper, clone, sampler, backtests, fomo, hot);
  - the console and data upkeep (render, serve, keep, prune, archive, manifest, keepset, evidence);
  - self-maintenance (processes, memories, never_fired, review, hooks, the deep-pass skill).
  Each holds its area against CLAUDE.md's twelve rules, the operator's goals and the records of what has actually fired. Every finding goes to three `finding-triage` agents; only two of three makes it real. The verdict goes to the operator by area, in a few lines.

**L2 · Poctivá čísla laborky** (Opus · high)
- `verdict()`/`_early()`: a bot leg enters at 100 = funding (`bot_series` is already indexed so). The formula fingerprint moves; old verdicts keep theirs.
- `verdicts()` checks status first:
  - stopped by hand with a position → judged up to the stop;
  - never held a position → "archivováno, bez pokusu".
- STR-0008 closed with its reason via `rooms.set_status`.
- `night_promote` writes Nexus's TP/SL into the plan legs before `set_acceptance` (parser beside `proposed_cards`). Forward only; existing rooms are not edited.
- Bot stop cause: join the sampler's `is_trading` flips with clones.jsonl intents into one of three causes:
  - ours;
  - their guard (the loss fits the settings, read by GET);
  - unexplained → check + report.
  - Never re-enable a stopped bot.
- `_deployed()`/`_in_clones()`: parked money counted separately from active.
- clones.jsonl untracked via a `keep.py` subcommand (protect_state refuses `git rm state/`). The monthly bundle takes clones, samples and hot_watch.
- `board_rows()`/`brief()` include bot and fund rooms.
- Tests first:
  - Bollinger fixture: 240 funded, +33.6 → +7.1 gives +2.96 %;
  - a stopped room with and without a position;
  - TP/SL from a NEX-text fixture;
  - the stop-cause join.

**L3 · Memecoiny** (Opus · high)
- First, the payload loses `fomo`: `_fomo_stats()` is served at `/lab.json` by serve.py, the way `/rooms.json` is, and the existing Memecoiny tab fetches it. Today the committed page hashes a gitignored diary (render.py:406, 5166), which is why "console poll" commits exist; with `--fomo 1` it would go stale every minute and prereg would refuse the dirty tree. This must land before `--fomo 1`. L4 then builds on the same endpoint.
- Headline = `stop_study()` at a $10 clip: no stop, 24 h hold, pair-clean. Swap fee per side with sensitivity at 0.5/1/2 %.
- Depth at entry decides the buy; depth at exit caps the sell. Split test L553 and keep its case-blind half.
- Suspect jumps with an unknown pair are counted and excluded.
- Per-token rows.
- The conviction ≥ 70 split stays (pinned quotes at fomo.py:260/466/489 stay verbatim).
- Fix the mislabeled "no price when it fired".
- `RADAR_FIELDS` += price_usd, first_buy_seconds_ago, exit_signal, exit_reason, updated_at.
- `console.cmd --fomo 1`, only after the `/lab.json` step above and only together with:
  - new-signal horizons 0.25/1/4/24 h;
  - a quote cap per round;
  - bulky captures pruned after 1 day.
- `fomo_watch.py report` prints the $10 answer and "stihli bychom Y % (od data)".
- Out-of-sample rule: a rule or pattern is dated and judged only on data after its date.

**L4 · Tab Laboratoř** (Sonnet · high)
- `build_lab()` in render.py extends the `/lab.json` endpoint from L3 with the rooms, backtests and samples.
- The tab replaces Nexus + Memecoiny and becomes the default.
- A KPI strip: best verified strategy · running · verdicts this week · book.
- Tiles by product come from a pure `register()` over rooms + backtests + fomo + samples. A new leg kind gets its tile with no wiring.
- Room view:
  - leaderboard: short label from legs, source (Nexus / naše), net %, n, verdict/ETA;
  - archive folded;
  - a Nexus hit-rate line (questions → concrete picks → verified wins);
  - the note box unchanged.
- The render.py:4931 quote stays verbatim.
- Tests first: rewrite test_pipeline_render.py:312-485/1876-1945 and test_pipeline_rooms.py:1359. Add a both-ways field guard for `/lab.json` and test_live_server for the endpoint.

**L5 · Pás** (Opus · high)
- Drop ours: questions/day, rooms/day, running_experiments, the 20-min spacing, IN_FLIGHT_HOURS.
- Keep theirs: OUTSTANDING_BOUND 6, ASKS_PER_HOUR 3, backoff, plus the `pass_in_flight` interlock.
- Stake = a fixed share of the book, so 60 % exposure is the only limit on how many run.
- Answers are read once; only answers with pending legs are re-read.
- `clone.py settings()`:
  - reuses `enable()`'s paper check;
  - components.yaml declares the safe fields (no arb/custodial/onchain);
  - each variant is a new room, and a PATCH is refused while its room runs.
- A bot grid per species: SL/TP/max_position/max_open_positions/min_ai_confidence/market toggles.
- Own lane last:
  - origin `OUR-…`, labelled „naše";
  - each also put to Nexus as a question;
  - never ranked above his picks;
  - correlated rooms from one seed count as one.
- Rewrite the tests the Plan review named first: test_pipeline_lab.py:375/411/825/1273/1336/1519, test_pipeline_lab_loop.py:87/555/692/1665, test_pipeline_night_spend.py:186.

**L6 · Manažer** (Sonnet · high)
- laborator SKILL.md ≤ 150 lines, pins verbatim. "What we know about Nexus" moves into `lab.py brief`.
- The tick's last line is `next: N min (why)`, which drives ScheduleWakeup.
- The skill reads `get_usage` → `lab.py tick --usage` → a pure `qa/lab.py::pace()` → normal / economy (≥ 90 min, no agents, no hunts) / minimal (deterministic tick only).
- Report: ≤ 3 Czech lines, plus a ready Telegram block when needed.
- Idle → sweep or bug hunt, with at most one Sonnet agent, normal mode only.
- Measure the model the loop actually runs on (transcript `message.model`). If it is not Sonnet, set the lab session's model (one approval).
- Add `clone.py`/`paper.py`/`hot_watch.py` to the allowlist; paper-only stays enforced in code.

**L7 · Údržba sama** (Sonnet · high)
- processes.py: transcripts from this project only (fixes the `*cymetica*` leak), reading only new bytes.
- A separate hook-denial counter per hook and day, with a flag.
- Policy "twice → mechanism". The first mechanism: a commit helper that takes the message from a file.
- The deep-pass reminder fires on risk, volume or the week being due, not every 36 h.
- The deep pass sizes itself:
  - full: state/fold/measure, a check or vendor-facing code changed, ≥ 15 commits unpushed, or the week is due;
  - light: Sonnet triad;
  - minimal at ≥ 85 % weekly: tidy + report, no push;
  - usage before and after goes into the notebook;
  - this changes the deep pass's spine, which step 1c counts as a rule: it lands with a test naming the incident (the Pro week at 80 %) and a paragraph under `Změněná pravidla`.
- NEXT.md: a per-line cap (≤ 300 chars) in `test_next_step.py`; the lab agenda lives in the lab's own queue.
- `keep.py archive --mirror`.
- Housekeeping in the first tick of each UTC day, unless a pass or prereg is in flight.
- The dead `night_running` rule is removed.
- New budget keys are emitted by `sizes()`.
- A standing re-read against slow rot, triggered rather than weekly (the operator, 2026-09-23: weekly is probably too often). An area of the five above is read in full by an independent reader when it has taken ≥ 15 commits since its last full read, or when 30 days have passed, whichever comes first. So a quiet area is re-read monthly and a busy one where it is busy. A diff review cannot see what decays without changing (the transcript glob that started reading another project is the example). This is a rule, in the 1c form.
- Growth budget: `meta_tests` (the `def test_` count under tests/meta) is emitted by `sizes()` with a ceiling at today's count + 20. A new guard replaces or merges an existing one. This is a rule, so it lands in the 1c form: a test naming the incident (225 → 709 in 13 days, 864 guarding us vs 97 testing them) and a paragraph under `Změněná pravidla`.

**L8 · Oddělení do budoucna** (Sonnet · high)
- Discovery by convention, not a declared registry (2026-09-11 pin):
  - `PART_RECORDS` derived from `state/<script>.jsonl` + the journal source;
  - memory class from skill names;
  - tiles from leg kind.
- CLAUDE.md "Nové oddělení", ≤ 8 lines.
- Outward writes stay denied by default (an unlisted host raises SafetyViolation). A tweet is a draft the operator posts.
- Test: a fixture skill + script + diary is picked up everywhere with no edits.

### Assurance
- Rows name test ids. A `tests/repo` test fails when a `hotovo` row's tests don't exist (`plan_phases()` already rejects unknown hashes).
- The existing reminder fires when an open phase has no NEXT line.
- The nightly deep pass reviews the whole diff with three independent readers.
- `/code-review` only where CLAUDE.md requires it.
- After L8: one independent conformance audit (one Opus agent) reads this plan against the repo, and any false done-when reopens its row.

### Verification (end to end)
1. `python -m pytest tests/meta tests/repo -q` is green.
2. A fresh session prints ≤ 1 plan line, and its first answer repeats what is due, in Czech.
3. A `/loop jdi do laborky` day:
   - ≤ 3-line reports;
   - rooms per product in `lab.py status`;
   - no stopped-without-position room has a verdict;
   - Bollinger ≈ +3 %.
4. Console screenshot at 2000 px, actually looked at.
5. `fomo_watch.py report` gives the $10 answer with n.
6. `patrol --flags` is quiet; evidence ≤ 700 MB; memories ≤ 42; CLAUDE.md ≤ 640 lines.
7. The conformance audit passes.

### Not doing
- No scheduler or cron. No timer that trades: console timers only read.
- No real money.
- Run records stay in git (rule 12 needs the cited ones).
- The listing checks keep their captures (they stand behind filed findings).
- No standing AI technician. No per-phase agent reviews.
