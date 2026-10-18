# Laborka jako firma: manažer a oddělení

Stavím od 11. 10. na tvoje „stav firmu“. Spustí se až na „zapni laborku“.

## Pro tebe

**Jak to funguje**
- **Manažer** (Opus, nejvyšší úsilí) je šéf. Mluví jen s tebou a s odděleními a rozhoduje, kdo co dělá.
- **Oddělení** spolu nemluví napřímo. Každé dostává práci od manažera a hlásí jen jemu.
- Mezi odděleními chodí jen **lístky**: „tady je bug", „hotovo", „potřebuju rozhodnutí". Každý lístek má majitele, stav a počet pokusů, takže se nic neztratí a nic se neudělá dvakrát.

| Oddělení | Model | Co dělá |
|---|---|---|
| **Bugy** | Sonnet, high | jediné oddělení, které bugy ověřuje, podává a hlídá (dnešní linka beze změny). Ostatní mu bug jen předají lístkem a dál se o něj nestarají. Kromě toho samo hledá a dělá sweepy. |
| **Laborka** | kód + Sonnet, high | roomy (karty, boti, mřížka, h2h, memecoiny, outsider). Každých 20 minut běží tick jako obyčejný kód; AI se zavolá jen tehdy, když je co rozhodnout (Nexus, lekce). Jeden agent stačí, dělá to hlavně kód. |
| **Desk** | Opus, max | sám na sebe, jediný cíl: prokázat, že se na Cymetice vydělá. |
| **Outsider** | Sonnet | jednou denně cizí pohled, mimo náš repozitář. |

**Auditor procesů (hlídá celou firmu)**
Samostatná role, ne manažer: kdo řídí, neměl by sám sobě dávat známku.

**Hodnotí všechny procesy firmy**, nejen nová oddělení: deep pass, sweepy, kontroly kódu, ticky laborky, podávání, ranní přehled a Desk. Najde je sám, stejně jako dnes `processes.py patrol` najde každou část. U každého se ptá, jestli stojí za to, co stojí. Třeba:
- celý sweep se spouští zbytečně často;
- deep pass dělá trojí kontrolu i u malé změny kódu;
- jedna práce se dělá dvakrát.

Ke každému takovému místu navrhne, jak ho zefektivnit.
- **Denně, kódem a zdarma:** změří tok lístků (jak dlouho čekají, kolik jich selhalo, kde se hromadí), kdo stojí, co se dělá dvakrát a kolik tokenů stál jeden užitečný výsledek.
- **Jednou týdně, Opus:** přečte tato čísla a záznamy práce a najde špatné toky, zbytečnou práci a zaseklá místa. Ke každému navrhne konkrétní vylepšení s čísly, třeba: „Tester udělal 14 sweepů, 11 nenašlo nic nového, stačí každý druhý.“
- **Komu hlásí:** tobě i manažerovi. Manažer provede, co je jeho. Co se týká tvých pravidel, je na tobě.
- Staví na tom, co už máme: denní kontrole `processes.py patrol`, deep passu a týdenním ohlédnutí.

**Kontrola po stavbě, víckrát**
Je to velký zásah do kódu, proto celá firma projde několika kontrolami, než ji pustíš:
1. Po každé fázi kontrola jejího kódu.
2. Na konci nezávislá kontrola celé architektury: jeden čtenář (Opus, max) projde návrh i kód a zeptá se, jestli celá firma dává smysl. Hledá nelogické toky, dvojí práci, mrtvý kód a role, které si lezou do práce.
3. Každý jeho nález ověří tři rozhodčí nezávisle. Platí jen to, na čem se shodnou aspoň dva.
4. Opravy.
5. Druhá celá kontrola, jestli opravy něco nerozbily.
6. Zkušební provoz na nečisto (falešný Claude, žádná skutečná AI), celý den firmy za pár minut: lístky tečou, nic se nezasekne.

Teprve pak „zapni laborku“.

**Paměť**
Každý agent začíná každou práci s čistou hlavou a čte si paměť svého oddělení: co ví, jak pracuje a kde se už spletl. Na konci si zapíše, co se naučil. Manažer jednou denně paměti všech oddělení pročistí: sloučí, opraví a staré dá do archivu. Díky tomu se zlepšují a nebobtnají.

**Aby nic nezamrzlo**
- Každá práce má časový limit. Co ho přetáhne, kód ukončí.
- Lístek, který třikrát selže, jde manažerovi.
- Oddělení, které 24 hodin nic neposune, manažer přezkoumá a změní mu postup, případně ti napíše.
- Kontrolka „žije" u každého oddělení.

**Šetrnost**
Většinu času běží jen kód. Drahé modely se volají jen při rozhodování: Opus jen manažer a Desk, rutina na Sonnetu.

**Zapnutí**
„Zapni laborku" pustí oddělení jako samostatné procesy. Jedou nonstop, i když zavřeš okno. „Vypni laborku" je zastaví.
- Mění to tvoje pravidlo z 12. 9. („žádné automatické schedulery"), proto ho zapíšu jako tvoje nové rozhodnutí.
- Jednou se musíš přihlásit k `claude` na tomhle počítači.

---

## For implementation

### Context
Operator, 2026-10-11 (verbatim vision, to be pinned): a main manager, Opus at the highest effort, the orchestrator through which every department talks and who talks with them; a bugs department -- the only one that tests, verifies and files bugs (today's pipeline), every other department hands it a bug and stops caring; laboratory room department(s), one agent or more as we judge, efficient without losing quality; the desk, Opus alone, one goal; each department with memory management so it keeps improving, possibly curated by the manager; built to current multi-agent standards so it does not collapse and agents do not get stuck. Claude Code fits as the manager's conversational face; departments run as headless `claude -p` processes (per-process `--model`, `--effort`, `--permission-mode`, fresh context, repo CLAUDE.md loaded; code.claude.com/docs/en/headless.md).

### Architecture (orchestrator-workers, deterministic shell, LLM at decision points)
- **Supervisor (code, no LLM)**: `scripts/crew.py start|stop|status`; one detached loop per department; per-run timeout and `--max-turns`; exponential backoff on failure; heartbeat rows in `state/crew.jsonl`.
- **Ticket bus (files)**: `state/crew/tickets.jsonl`, append-only; a ticket = {id, from, to, kind (bug, decision, report, help), payload, status open/claimed/done/failed, attempts, created}; claimed under a file lock; idempotent keys (a bug's key) so a retry never files twice (submit.py's intent/outcome already holds the filing side).
- **Manager (Opus xhigh/max)**: woken by the supervisor on manager tickets (escalations, failed x3, decisions), on a daily review (progress per department, memory curation) and by the operator in chat (this app session reads the board and the manager's notes). Its notes to the operator go to `state/crew/to-operator.jsonl`, printed at session start.
- **Bugs department (Sonnet high)**: claims bug tickets first, then hunts/sweeps on its cadence; the ONLY writer of the bug pipeline (submit.py, ledger fold, render, journal) -- one writer per resource removes the commit races there.
- **Laboratory department**: `lab.py tick` as code every 20 min; one Sonnet high run only for decide items (answer, question, learn, outsider); a bug found becomes a ticket to Bugs, never a filing.
- **Desk (Opus max)**: continuous steps with a pause; its brakes: at most 2 Build it Better filings a day (a filing costs 0.5 units of their build plan); a question to Cymetica is a draft the operator sends (no worker runs a2a, deep pass 2026-10-11, R04); a bug it meets becomes a ticket.
- **Outsider**: daily, its own process outside the repo (existing `outsider.py probe|run`); its stumbles become tickets to Bugs.
- **Memory**: per department `docs/dept/<name>.md` (what we know, how we work, how we went wrong; ten lines a heading), read at the start of every run, written via `lab.py log --lesson --section`-style commands at the end; the manager's daily review merges, corrects and retires (archive at the bottom, never silently deleted). Laboratory sections keep `docs/lab-knowledge.md`.
- **Process auditor (independent of the manager)**: operator, 2026-10-11: someone who monitors the whole company daily or weekly for bad flows -- and "musi hodnotit vsechny procesy a zjistit neefektivnosti", every process, not only the crew's: e.g. a full sweep run too often, a deep pass running its triple review on a small diff. Its scope is everything `processes.py patrol` finds by glob (skills, agents, scripts, hooks, the crew's roles); for each it weighs cost (runs, minutes, tokens) against what it produced (findings filed, rooms judged, fixes verified, lessons kept). Daily in code: `scripts/processes.py patrol` extended to the crew -- ticket lead time and age, failures and retries per department, idle departments, duplicate work (two tickets on one key), tokens per useful outcome (from `--output-format json` cost fields in `state/crew.jsonl`). Weekly, one Opus run (the existing weekly `ohlednuti` skill, widened): reads those numbers and the week's transcripts, names bad flows, waste and stuck places, proposes concrete changes. Reports to the operator AND the manager (it audits the manager too); the manager carries out what is its own, the operator's rules stay theirs. The nightly deep pass keeps reviewing the code.
- **Anti-stuck**: timeouts and max-turns per run; a ticket failed 3 times escalates; a department with no progress in 24 h (progress = tickets closed, rooms opened/judged, desk hypotheses moved) gets a manager review; a supervisor heartbeat per department, shown by `crew.py status` and on /lab.
- **Safety**: `--permission-mode acceptEdits`, `--disallowedTools "Bash(git push:*),Bash(git tag:*)"` on every worker; Bash only through the project allowlist; a commit lock (`scripts/commit.py`) for everything outside the Bugs department's own paths; paper only; push never; starting only on the operator's word, pinned as their decision beside `[operator 2026-09-12]`.

### Phases (each test-first, commit on main; nothing starts until the operator says so)
C0 pins and design doc -> C1 supervisor + ticket bus + status (fake `claude` in tests) -> C2 Bugs department (tickets in, single writer) -> C3 Laboratory department routing -> C4 Desk under the crew -> C5 Manager: escalations, daily review, memory curation, operator channel -> C6 anti-stuck watchdog -> C7 process auditor (patrol metrics daily, weekly Opus review via ohlednuti) -> C8 reviews -> C9 first live start on "zapni laborku".

Building since 2026-10-11 ("stav firmu podle docs/crew-plan.md"). The status column is what
`processes.py plan_phases` reads: a phase is done when it names a commit this repository has.

| Phase | What | Status |
|---|---|---|
| C0 | design decisions below, memory files for Bugs and Manager; the operator's decision in CLAUDE.md, the `crew` skill and the allowlist (on their word in chat, "ano zapis to") | hotovo ba2108d7 |
| C1 | `qa/crew.py` (bus, departments, argv, outcome), `scripts/crew.py` (loops, start, stop, status), `scripts/commit.py` | hotovo 2c64db05 |
| C2 | Bugs department: tickets in, the one writer of the bug pipeline, the tree held still for level V | hotovo 6e4956e7 |
| C3 | the clock: the laboratory's tick routed to lab, bugs and outsider; the outsider's code run | hotovo 179cc957 |
| C4 | Desk under the company: its own pace, its snooze, its brakes in code | hotovo fb0eebe4 |
| C5 | Manager: escalations, daily review, memory curation, operator channel | hotovo 4277ae18 |
| C6 | watchdog: leases, three failures, a stuck department, a dead loop restarted | hotovo 5506421d |
| C7 | process auditor: the day's numbers on the clock and in the patrol (b5def5f3), the week in deep pass step 11 | hotovo ba2108d7 |
| C8 | reviews and the dry run: a reader, three triage agents (8 of 11 stood), fixes, a second reader (5 more, 4 from the fixes), fixes; the dry run green three times; tests/meta + tests/repo 1452 passed | hotovo 627f4a3e |
| C9 | first live start on "zapni laborku" | hotovo 9acfae86 (started 2026-10-12 16:15 UTC, state/crew.jsonl line 1; that commit is the company's first, its manager's; points 9-11 of docs/crew-before-c9.md stay in NEXT.md) |

### Implementation decisions (2026-10-11, while building)
- **Files ride the department shape** (`qa/departments.py`): `state/crew.jsonl` (runs, loop events, the day's numbers), `state/crew_tickets.jsonl` (the bus), `state/crew_operator.jsonl` (to the operator), `state/crew/report.json` (the /lab report). The patrol counts them as `crew.py`'s records and `keep.py snapshot` copies the diaries; `state/crew/tickets.jsonl` would have been missed by both. All gitignored: tracked, a loop's write would cost a sweep its level V.
- **Loops**: one per department (bugs, lab, desk, outsider, manager) plus **the clock**, each a detached process holding a lock for its life, so a name runs once and a dead loop frees its name by itself. Departments only consume tickets; the clock makes them: the laboratory's tick every 20 min (its `decide:` items routed: lab items to lab, hunts to bugs, `outsider` to outsider, `desk` dropped because the desk keeps its own pace), the desk's next step, the manager's daily review, the watchdog and the day's numbers. So the laboratory's tick stays the company's one clock for vendor news and hunts -- no second cadence for Bugs.
- **Tickets**: idempotent by key (a key never makes a second ticket); claimed under `qa.state.file_lock` with a lease (timeout + 10 min); `done`, `fail` (an attempt spent), `release` (none spent). Three failures end a ticket and the watchdog gives it to the manager; a failed manager ticket goes to the operator. A failure of the machinery (not logged in, overloaded) releases the ticket without spending an attempt, and consecutive failed runs back a loop off 1, 2, 4 ... 60 minutes.
- **Git**: a worker commits only through `scripts/commit.py` (one lock, named paths, a `Crew: <dept> <ticket>` trailer); `git add`, `git commit`, `git push`, `git tag`, `git revert`, `crew.py start|stop`, cron and wakeups are denied in every worker's argv. No script here pushes (grep, 2026-10-11).
- **The deep pass**: no loop claims a ticket while `processes.pass_in_flight()`; a running worker finishes within its timeout.
- **Memory**: lab = `docs/lab-knowledge.md` + `docs/lab-manager.md`, desk = `docs/lab-desk.md` (both existing), bugs and manager = `docs/dept/*.md`; the outsider reads none.
- **The weekly auditor is the deep pass's step 11** (the one weekly look back, one checkpoint), widened with the company's numbers; no second weekly run. The daily auditor is code on the clock.
- **The operator channel** reaches the session start through `processes.reminders()`: the hook's eight-line cap leaves no new slot.
- **No budget brake**: `--max-budget-usd` would stand a worker down on cost, which CLAUDE.md bars (2026-09-25); turns and timeouts bound a run.

### C8, reviews (operator, 2026-10-11: "nekolikanasobne review celeho kodu a vseho ... cela firma musi davat smysl")
1. Per phase: `/code-review` over that phase's diff before its commit (state/fold-adjacent code at high-xhigh, as CLAUDE.md asks for qa/state.py, fold.py, measure.py).
2. After C7: one independent architecture reader (Opus, max effort, fresh context, given only the design section above and the code) answers: does every role have one job, does every resource have one writer, does every ticket have an owner and an end, is any flow circular or dead, is anything built twice, does any role reach what it must not (push, tags, the vendor outside its brakes).
3. Each finding goes to the existing `finding-triage` agent three times, no shared context; a finding stands when two of three agree (the deep pass's own rule).
4. Fixes, test-first.
5. A second full reader after the fixes, same questions, to catch what the fixes broke.
6. A dry run of the whole company with a fake `claude` executable: a simulated day (ticks, a bug ticket from the desk closed by Bugs, an escalation after three failures, the auditor's daily metrics, a stop) in minutes; every ticket reaches an end, no role idles without saying why.
Only then C9.

### Verification
Pure tests for routing, tickets (claim, retry, escalate after 3), memory curation rules; the supervisor with a fake `claude` executable (start, cycle, timeout kill, backoff, stop); the deny of push/tag in every argv; then, after the operator's word, `crew.py status` showing each department alive with a run and the ticket flow (a bug from the Desk closed by Bugs).
