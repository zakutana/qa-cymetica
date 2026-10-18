# ARCHITECTURE.md — the system as the code has it

Read from the source on **2026-09-20**, at commit `8f6aa3ed`, deliberately
**without** taking CLAUDE.md's word for anything. Where the two disagree, the
disagreement is recorded in §8 rather than silently resolved.

This is the second reading. The first was written on 2026-09-08 at `702a65c`
(`b363321b`, amended `a53055e1`) and is in git; it was put to four independent
readers on 2026-09-20, one section each, and what it got wrong — as opposed to
what merely aged — is kept in §9, because those are the mistakes a third
reading would otherwise repeat.

§0 below is the current map; §1-§9 are the reading of 2026-09-20.

This file is for sessions, not for the operator. It is descriptive only: no
proposals, no fixes. Claims marked `UNCERTAIN:` were not established from the
source and must not be built on.

## 0. Where things live -- the current map

Moved here from CLAUDE.md on 2026-09-23 (plan v2, V7), with every
path in it checked against the tree that day. Unlike §1-§9, this
section is kept current: a change that moves a part changes its line.


```
qa/state.py       the ONLY module that writes state/ledger.json and the
                  journal. Admissibility, the ledger contract, the append-only
                  hash chain. Other modules write their own narrow file
                  under state/ -- run records, the vendor snapshot, the
                  section map, preregistrations, the Nexus rooms. The guard in
                  tests/meta/test_pipeline_withdraw.py enforces the accurate
                  sentence, not the wider one: it fires on a write near the
                  words ledger, events or journal.
qa/fold.py        pure: ledger = f(previous rows, one run, the journal)
qa/measure.py     Measurement + conclude(): a check's verdict and pytest's
                  outcome are one value
scripts/ledger.py CLI over the fold
scripts/withdraw.py  the only human writer — every command is one event
scripts/prereg.py    freeze and tag a run's configuration
scripts/never_fired.py  which of our mechanisms have never once occurred in
                     the data. A green guard says a mechanism WOULD work; this
                     says whether it ever has. Read `--zeros` at the end of a
                     sweep. Each zero names the test that exercises it, or says
                     nothing does -- so the line to act on is "never fired AND
                     never exercised", the shape all three dead mechanisms had
                     on 2026-09-06. One exercised and never fired is the
                     operator's judgement. **Read the count off the tool, never
                     off prose** -- this line said five while the tool said seven.
tests/meta/       self-tests. Run FIRST and abort the session on failure, so
                  a broken guard stops every live request.
tests/repo/       repository consistency. Deliberately NOT in tests/meta:
                  a stale ledger must not abort the run that would fix it.
.claude/hooks/session_start.py
                  the ONE SessionStart hook (plan v2, V7): what is due, what
                  the last pass left, the threads, the room notes, NEXT and the
                  memories, each in a fixed slot, eight lines at most, about a
                  second. Its sources are .claude/hooks/start/*.py, each still
                  runnable alone; the surface drift is read from
                  state/surface_drift.json, which `processes.py surface`, the
                  patrol and the laboratory tick write.
.claude/hooks/protect_state.py
                  rule 4, enforced before the write instead of after it. A
                  PreToolUse hook that refuses an editor write, a shell
                  redirect, sed -i, rm or git checkout aimed under state/.
                  Reads are untouched, and the sanctioned writers go through
                  qa/state.py so they never name the path. Without it the
                  hash chain still catches a hand edit -- but only at the
                  next load, one step too late.
.claude/skills/deep-pass/SKILL.md
                  the unattended pass over everything unpushed, and the only
                  thing here that pushes. Its step 2 is the one worth the
                  run: three auditors hold each check's assertion against the
                  contract its docstring names. That class of defect happened
                  five times on 2026-09-07, every guard green throughout, and
                  one of them sent a false claim to the vendor. Named for
                  what it does, not for the night -- the operator runs it in
                  the day too. Its progress goes to
                  audits/deep-pass-progress.json as it goes: the run is
                  compacted mid-flight, and a triage verdict lost that way is a
                  finding that silently never gets fixed.
.claude/skills/laborator/SKILL.md
                  "/loop 20m jdi do laborky": one tick of a laboratory that
                  runs all day -- `lab.py tick`, whose last line `decide:`
                  says what, if anything, needs the model; `none` costs one
                  line (plan v2, V6). `pokracuj` is the same tick by its old
                  name. What it knows about Nexus grows in `NEXUS_KNOWN`
                  (scripts/lab.py), which `lab.py brief` prints.
qa/lab.py         the laboratory's notebook and its brakes, in code rather
                  than in prose: sessions, ranked snapshots, the catalogue it
                  compares against the baseline, and the brakes -- paper only,
                  0.48% of the book a room under a 60% ceiling (the only count
                  limit), their pace (3 asks an hour, 6 outstanding, backoff),
                  a backtest before a room, nothing while a deep pass runs.
qa/backtests.py   the register of what has already been measured: a basket's
                  fingerprint (sorted legs, window, fees) against what it
                  returned, so no night pays for the same backtest twice.
                  state/backtests.jsonl, gitignored like the other diaries.
scripts/lab.py    that loop from our side: `tick` (the day's session, answers
                  picked up, a card read live and backtested before a paper
                  room, the search, verdicts; state in state/lab_tick.json),
                  `brief`, `board` (his proposals by what they earned), `log`,
                  `ask`, `truth`, `buy`. It refuses rather than warns.
scripts/league.py Cymetica's Agent League (2026-10-09): `puzzles`, `join`,
                  `answer`, `tick`, `brief`, `report`. Two declared writes
                  (`agent_league.enrol`, `agent_league.answer`, closed body in
                  components.yaml) and nothing else under /agent-league. What
                  is answered is `qa/league.py`: only the families that are
                  exact arithmetic on the puzzle's snapshot (edit distance, the
                  CEX-DEX net edge), with a reasoning that is the computation.
                  Skill `.claude/skills/league/SKILL.md`; diary
                  state/league.jsonl, report state/league/report.json.
scripts/bb.py     Build it Better requests the desk files itself (2026-10-11):
                  `file`, `accept`, `change`, `verdict`, `withdraw` (each a
                  dry run without --confirm), `get`, `mine`. Five declared
                  writes, closed body (`build_it_better.*` in components.yaml);
                  their limits refused before a body exists. Diary
                  state/bb.jsonl (rule 9, BB-NNNN); the one-time request token
                  goes as the X-BB-Token header and lives only in
                  state/bb_tokens.json, gitignored.
scripts/outsider.py the laboratory's section 6 (2026-10-11): `record` a run of
                  the stranger agent `.claude/agents/outsider.md` (WebFetch and
                  WebSearch only, 40 fetches, no memory of ours), `track` its
                  coins at 1/7/28 days against BTC, `report`, and `seat` -- one
                  declared write (`agent_tournaments.seat`, closed body), asked
                  only at a table their API calls paper. What its picks may do
                  is `qa/outsider.py::actions` (a card at half stake, no backtest
                  gate). Diary state/outsider.jsonl, gitignored and snapshotted.
NEXT.md           what we agreed to do next and have not done. Plain markdown,
                  one line per item, `- [ ] YYYY-MM-DD  sentence`; ticked, it
                  gets `(hotovo DATE)` and goes a week after that stamp. At
                  most ten open lines of 300 characters. The session start
                  prints how many and the first, the deep pass's step 10b
                  writes it, and `tests/repo/test_next_step.py` fails on an
                  unparsable line, on the budget, and on anything open over
                  fourteen days. It holds work that
                  is OURS and already decided; what needs the operator's
                  judgement goes under DEEP-PASS.md's Čeká na tebe.
DEEP-PASS.md      what the last deep pass did, in Czech, overwritten each
                  run. **Read it at the start of any session that follows
                  one** -- five headings, and "Ceka na tebe" is the handover:
                  what the pass could not finish and what needs the
                  operator's judgement. Nothing else loads it, so a session
                  that does not open it answers "how did the deep pass go" out
                  of nothing -- which happened on 2026-09-08, because the
                  pointer to this file lived only inside the skill.
.claude/agents/   model and effort per role, in frontmatter. So neither the
                  operator nor a session has to choose one per task -- the
                  task carries its own. A session still cannot change its
                  OWN model or effort; that stays /model and /effort, and
                  stays the operator's.
audits/checks.json
                  nodeid -> the fingerprint last audited, so the contract audit
                  re-reads only what moved -- keyed on the fingerprint rather
                  than the run, like verification_owed.
```

The scripts a session actually spends its time in.

```
scripts/findings.py  what a run turns into a finding. Title and severity are
                     JUDGEMENTS and a run may not overwrite them -- which is
                     why a row's title stays frozen at the measurement that
                     opened it while detail.reason moves. Anything reading a
                     title as a current reading is wrong.
scripts/bounty.py    their tracker -> state/bounty.json. The inbound channel
                     we FETCH, and the only thing that lights the console's
                     bell. Records CHANGES, not polls -- one vendor_read per
                     run, a vendor_status only when a status actually moved.
                     Not the only correspondence: the Telegram thread is
                     recorded by correspond.py, which the bell does NOT cover.
scripts/correspond.py  the operator's Telegram conversation with the vendor.
                     `sent` records a message once THEY confirm they sent it,
                     `reply` files the answer they paste back, `list` and
                     `show` read it. Ids are MSG-NNNN / REPLY-NNNN, and their
                     ticket id (ET-22498) goes in `via`, because that is the
                     id the operator will say out loud. Two event types of its
                     own: a chat is not a filing, so it moves neither axis and
                     the fold does not read it -- `--findings` is advisory.
                     **When the operator says they sent something, or pastes
                     an answer, put it through here** rather than into a
                     conversation that ends at the next /clear -- ET-22498 set
                     off the whole /build walk and what we asked in it is gone.
                     A SessionStart hook (.claude/hooks/start/open_threads.py) names
                     the unanswered ids in one line -- through qa/channels.py
                     since 2026-09-20, so it covers every channel waiting on
                     them, not Telegram alone.
scripts/submit.py    the one write we make on purpose. Every number in a
                     report is injected from the ledger at send time, so a
                     figure frozen when the finding opened can never go out.
scripts/serve.py     the console on 127.0.0.1:8787. Polls local files once a
                     minute and renders. `--ask MINUTES` adds the half that
                     fetches: one GET of our own reports on a timer, so the
                     bell can light unattended; `--sample MINUTES` runs
                     scripts/sampler.py for the Nexus tab, into the gitignored
                     state/samples.jsonl. One write of its own: a note the
                     operator sends from the Nexus tab, through
                     qa.rooms.add_operator_note, behind a launch token, a
                     loopback Host and Origin and a JSON body -- and none at
                     all when it listens beyond this machine. Rooms are served
                     at /rooms.json, outside the payload, so a note never moves
                     the dashboard.
scripts/sampler.py   what their API says about our bot, our card positions and
                     the cards a strategy's plan names, for the Nexus tab's
                     panels. SAFE, GET only, six doors, and only what our own
                     records say is ours. Every round writes a `tick` to
                     state/samples.jsonl (gitignored), even a round whose every
                     read failed, so a stall reads as "stale" rather than as
                     quiet; a card they no longer know is a `not_found` row,
                     not a failed round. `clone.py watch` is one round of it.
scripts/a2a.py       the third channel, from our side. `send` posts a question
                     and only on `--confirm` -- the operator's condition, and
                     without it nothing is written either. Two events per send,
                     keyed on OUR id, so a POST that times out still leaves the
                     text on the journal. Built because nothing in scripts/ had
                     ever sent one, and the question that started the /build
                     walk exists nowhere.
scripts/channels.py  all three channels in one place, and the operator's notes
                     in the Nexus rooms beside them. `status` reads them live
                     and says where each stands, `status --offline` answers
                     from the journal alone, `watch` prints one line per new
                     inbound message so a Monitor turns it into a chat message.
                     Everything it knows comes from qa/channels.py.
qa/channels.py       the ONE reader across bug reports, Telegram and a2a, so
                     the CLI, the alert and the skill cannot grow three ideas
                     of "unanswered". One judgement: an automated reply is
                     silent, an unclassifiable one is not.
qa/rooms.py          the Nexus rooms (docs/nexus-rooms-plan.md): strategies,
                     the operator's notes, ours, read marks, the sampler's
                     rows. state/rooms.jsonl and state/samples.jsonl, both
                     gitignored because they are written while a sweep may
                     run. Two writers on purpose: the browser reaches
                     add_operator_note and nothing else. A strategy room
                     opens only from a whole Nexus answer, one room per card
                     it names; whether the answer PROPOSED anything is the
                     opener's call (NEX-0002 named no card and has none).
                     A room's name is its newest `title` row; its `plan` is
                     Nexus's proposal as legs -- card id, side, share, TP/SL.
scripts/rooms.py     the rooms from our side. **When the operator says
                     "přečti si to", run `unread`**: it prints their notes in
                     full and marks them read, and the console shows a second
                     tick. `note` answers into a room; `note --re NEX-... --gist`
                     is our one-line Czech summary, drawn inside that answer;
                     `open --from NEX-...`, `status` and `link` open and move a
                     strategy room; `title` names it and `plan` writes Nexus's
                     proposal down leg by leg (`--leg CARD:SIDE:SHARE:tp=N:sl=N`),
                     which `show` prints with each leg's levels. A follow-up
                     goes through `nexus.py ask --room STR-...`. A note is their
                     feedback read from a file, not an instruction in the chat
                     -- what would send, spend or publish is confirmed with them
                     first. A SessionStart hook (.claude/hooks/start/room_notes.py)
                     names how many wait, by room, in one line.
scripts/open_checks.py  the selector for a sweep over what is still open.
                     Always prepends tests/meta.
scripts/inventory.py    the platform section map the dashboard renders. An
                     inventory, not a test suite. SAFE tier, never a POST.
qa/keepset.py        which captures have to survive, and why: their answers the
                     ledger stands on, and what every verdict and report we
                     sent promises "on request". One reader for the tracker,
                     the pruner and the guard, so the three cannot grow three
                     ideas of "cited".
qa/manifest.py       the proof that outlives the body -- accumulates, and a
                     thinner entry never replaces a fuller one, because an
                     archived capture's call key can never be recomputed.
qa/archive.py        the monthly bundle, and the check before the move: build,
                     read back off disk, hash every member, THEN release.
scripts/keep.py      `track` writes the manifest (bodies stay on disk since
                     D3); `archive --month [--release]` bundles and lets go;
                     `snapshot` copies the lab diaries into audits/lab/
                     (fomo_signals one .jsonl.xz per day: 87 MB flat).
                     `.githooks/pre-commit` calls track at every commit, the
                     fold when a row starts standing on a new run, the deep
                     pass for a clone with no hooksPath, and `lab.py close`
                     snapshots when a session ends.
scripts/prune_runs.py  run records older than a week and captures older than
                     three days that nothing stands on, by name, with the
                     reason each survivor was kept printed.
qa/surface.py        THEIR side, watched. The patrol below measures our parts;
                     this one reads captures we already make and says when a
                     tool's PARAMETERS moved or a response started or stopped
                     carrying a field. `processes.py surface --update` agrees
                     to a new shape (audits/surface.json); the frozen
                     before-the-upgrade marker stays audits/nexus-baseline.json.
                     Written after #97 was fixed and the proof sat unread in our
                     own captures for a day.
scripts/processes.py  what is due, and what the operator said since the last
                     pass. `reminders` is the whole of the scheduler they
                     refused: a few lines naming what is on the table and the
                     words that start it, printed by .claude/hooks/start/reminders.py
                     and repeated to them in the first answer. Each rule is a
                     fixture in tests/repo/test_reminders.py in both
                     directions, because a line that appears every evening is
                     one they stop reading.
                     `messages --since-last-pass` is the deep pass's step 1
                     reader -- since the last pass, not since midnight UTC.
```

Parts the two maps above do not describe, one line each from their own
docstrings -- read the file before building on the line:

```
qa/client.py       HTTP and MCP clients -- the only sanctioned way to the network.
qa/safety.py       mechanical safety enforcement: tiers, the paper gate, PROBE.
qa/config.py       configuration and the identity registry.
qa/evidence.py     content-addressed capture; `content_id` is the one id.
qa/fingerprint.py  the platform fingerprint, our substitute for a build version.
qa/extractors.py   the small DSL that pulls comparable values out of sources.
qa/sources.py      source snapshots for the contradiction sweep.
qa/marks.py        the @qa decorator every check carries.
qa/report_plugin.py  pytest plugin: a run becomes a schema-2 record.
qa/console.py      makes a stream able to print what we print at it.
qa/fomo.py         does FOMO Radar's `hot` predict a memecoin moving?
qa/hot.py          the Hot headlines study, under Nexus's own rule.
qa/lab_report.py   what each laboratory product earned, after costs.
qa/morning.py      the 7:00 morning report's content.
scripts/lab_page.py  the /lab page, served and never committed.
scripts/morning.py   the morning report drawn as a page.
scripts/fomo_watch.py  the memecoin watch and its report.
scripts/hot_watch.py   what is in Hot every round, so a rule can be tested.
scripts/clone.py   paper clones of their bots: clone, fund, settings, enable.
scripts/paper.py   one paper trade on an event card, with its proof chain.
scripts/nexus.py   questions to Nexus and the answers picked up.
scripts/movers.py  the Movers Tournament: scored, no money moves.
scripts/memories.py  the memories for a kind of work, whole bodies to 8 KB.
scripts/render.py  state/*.json into the operator dashboard.
scripts/verify.py  tells them a check passes under the fingerprint it failed.
scripts/review.py  the look back over a window the caller chooses.
scripts/deep_pass_process.py  what each deep pass cost and caught.
qa/crew.py         the company (docs/crew-plan.md): the ticket bus, the departments,
                   each worker's argv and brakes, what a worker may not write.
scripts/crew.py    its loops, start/stop/hold, status, the clock, audit. Runs only
                   on "zapni laborku"; first started 2026-10-12.
scripts/commit.py  the company's only way into git: named paths, one writer at a time.
scripts/company.py our company on their Build a Company (cymetica.com/company):
                   create, departments, a read; each write declared, closed body.
.claude/hooks/no_heredoc_writes.py  a heredoc may not write a file here.
.claude/hooks/no_backtick_commit.py a commit message may not run a backtick.
.claude/skills/    deep-pass, laborator, pokracuj, qa-sweep, channels, ohlednuti.
.claude/agents/    check-auditor and finding-triage, model and effort in frontmatter.
```

---

Scale, for orientation:

| | |
|---|---|
| Python | 167 files, ~68.6k lines — `qa/` 8.6k, `scripts/` 19.7k, `tests/` 39.4k |
| Tests | 763 test *functions*; `pytest --collect-only` reports **1015** items after parametrisation |
| Ledger | 62 rows: 42 VERIFIED FIXED, 10 WITHDRAWN, 5 RAISED, 3 STILL REPRODUCIBLE, 2 OUR CHECK CANNOT TELL |
| Journal | 2364 events, 22 types, 2026-09-04 → 2026-09-20 |
| Run records | 512 on disk, 350 tracked (`scripts/prune_runs.py` removes what nothing stands on) |
| Evidence | 275 MB on disk, 23 MB archived, **no capture body in git** (`docs/data-plan.md`) |
| Commits | 763, all on `main` |

---

## 1. Components

### The core: three modules that own the contract

| Module | Lines | Responsibility |
|---|---|---|
| `qa/state.py` | 802 | The I/O boundary for `state/ledger.json` and `state/journal/events.jsonl`. Admissibility (`admissibility`, `run_integrity`), the monotonic ledger write (`write_ledger`), the hash-chained append-only journal (`append_event`, `read_events`, `head`), cross-process locking (`file_lock`), and the `QA_STATE_DIR` seam (`state_dir`). |
| `qa/fold.py` | 739 | Pure. `fold(previous, run, events)` → new ledger. Two axes moved independently (`_apply_run` for CHECK, `_apply_events` for FILING), display composed at render time (`_display_cell`, `display_state`), obligations derived (`_obligations`). Imports two pure helpers from `qa/state.py` and nothing that writes. |
| `qa/measure.py` | 168 | `Measurement` + `conclude()`. A check's verdict and pytest's outcome are one value. `required` / `field_of_every` / `collection_size` return Inconclusive rather than raising when a source lacks data. |

`fold()` itself is called from one place, `scripts/ledger.py:187`. The *module*
is imported by five scripts — `ledger.py`, `never_fired.py`, `open_checks.py`,
`render.py`, `withdraw.py` — for `display_state`, the state vocabularies and
`_fingerprint_of`. (§9.1: the first reading said "ledger.py only".)

### The suite's machinery

| Module | Lines | Responsibility |
|---|---|---|
| `qa/safety.py` | 508 | `SafetyTier` (SAFE/PROBE/MUTATE), `EndpointRegistry` loaded from `components.yaml`, `SafetyTransport` enforcing tier at the transport layer, `RateLimitBudget`. Default-deny: an endpoint with no rule refuses any non-read method. |
| `qa/client.py` | 446 | The only constructor of HTTP and MCP clients. `install_client_guard` makes constructing an `httpx` client outside these factories raise; `assert_client_guard_blocks` is the negative control. Four factories: `build_client`, `build_mock_client`, `build_mcp_client`, `build_fingerprint_client`. |
| `qa/report_plugin.py` | 475 | First-party pytest plugin, registered by `-p qa.report_plugin` in `pyproject.toml`. Turns a session into a schema-2 run record under `state/runs/`. Classification is a `tryfirst` hookwrapper so it runs last. |
| `qa/fingerprint.py` | 161 | The platform fingerprint: a hash over documents that change when the vendor ships. Corpus spec from `components.yaml` via `registry.raw["fingerprint"]`. `QA_OFFLINE=1` short-circuits it to `None`. |
| `qa/evidence.py` | 230 | Content-addressed request/response capture under `evidence/sha256/`, with redaction before write. `content_id` is the one computation of an id. |
| `qa/sources.py` | 179 | One fetch per source per session, with `Date`/`X-Cache-Status`, so a reconciliation whose sources drifted outside the window is INCONCLUSIVE rather than a contradiction. |
| `qa/extractors.py` | 352 | Hand-rolled extractor DSL for `tests/reconciliation/claims.yaml`. Deliberately not jsonpath-ng. |
| `qa/channels.py` | 356 | The one reader across the vendor channels — **four** of them since 2026-09-11: bug reports, Telegram, a2a and the console's rooms. `inbound`, `pairs`, `state`, `compare`. |
| `qa/marks.py` | 63 | The `@qa` decorator — one marker carrying component, tier, surface. |
| `qa/config.py` | 103 | `.env` loading, `Identity` registry, `base_urls()` (reads `components.yaml` at `:95`). |
| `qa/console.py` | 41 | The console's launch token, shared by `serve.py` and the browser write path. |

### The laboratory — a second subsystem, none of it present in the first reading

| Module | Lines | Responsibility |
|---|---|---|
| `qa/lab.py` | 1283 | The laboratory's notebook and its brakes in code: sessions, ranked snapshots, the catalogue against the baseline, and the caps (paper only, questions and rooms per rolling day, experiment count and size, a backtest before a room, nothing while a deep pass runs). Writes `state/lab.jsonl`. |
| `qa/fomo.py` | 726 | The memecoin study: checkpoints, the control group drawn from the same round, and the readouts (3x/72 h, 2x/24 h, 1.5x/6 h). |
| `qa/rooms.py` | 563 | The Nexus rooms — strategies, operator notes, ours, read marks, sampler rows. `state/rooms.jsonl` and `state/samples.jsonl`, both gitignored. Two writers on purpose: the browser reaches `add_operator_note` and nothing else. |
| `qa/backtests.py` | 383 | The register of what has already been measured: a basket's fingerprint against what it returned, so no night pays twice. `state/backtests.jsonl`. |
| `qa/surface.py` | 314 | The watch over THEIR side, mirroring the DNA patrol: tool schemas and response shapes, read from captures we already make. `audits/surface.json` is the acknowledged shape. |

### Retention, and the patrol over ourselves

| Module | Lines | Responsibility |
|---|---|---|
| `qa/keepset.py` | 436 | Which captures have to survive, and why. One reader for the tracker, the pruner and the guard. |
| `qa/manifest.py` | 141 | The proof that outlives the body: `audits/evidence-manifest.jsonl`, accumulating, a thinner entry never replacing a fuller one. |
| `qa/archive.py` | 191 | The monthly bundle, and the check before the move: build, read back off disk, hash every member, then release. |

### Scripts, by what they do

**Compose and render (run after every state change):**
`ledger.py` (448) CLI over the fold · `render.py` (5039) state → `dashboard/index.html` · `serve.py` (890) the same render served on 127.0.0.1:8787, watching `state/`, with `--ask MINUTES` polling the vendor and `--sample MINUTES` driving the sampler.

**Write to the vendor (the only deliberate outbound):**
`submit.py` (528) files reports, every number injected from the ledger at send time · `verify.py` (641) posts a verification that a check passes under the fingerprint it last failed under · `a2a.py` (283) sends an a2a question, only on `--confirm`.

**Read from the vendor:**
`bounty.py` (701) their tracker → `state/bounty.json`, recording changes not polls · `inventory.py` (593) the platform section map, SAFE tier only · `channels.py` (208) all four channels in one place (`status`, `compare`, `watch`) · `sampler.py` (423) what their API says about our bot, positions and cards, for the console's Nexus tab · `movers.py` (251) the movers tournament.

**The laboratory, from our side:**
`lab.py` (2463) the day's tick — memecoin checkpoints, answers picked up, the live card read and backtest gate before a paper room, the search, verdicts · `nexus.py` (616) the deep and shallow lanes to their AI · `rooms.py` (298) rooms from our side · `paper.py` (764) paper orders · `fomo_watch.py` (567) the memecoin study's collector and report · `clone.py` (666) a cloned bot and one round of watching it.

**Operator writes:**
`withdraw.py` (280) the only human writer — every command is one event with a reason · `correspond.py` (338) the Telegram thread as a record with ids · `prereg.py` (179) freeze and tag a run's configuration.

**Derivation and inspection:**
`findings.py` (268) run record → candidate findings, holds no state · `never_fired.py` (440) which vocabulary symbols have never occurred in the data · `open_checks.py` (148) the selector for a sweep over what is open · `memories.py` (230) the memory directory, by the work in front of you · `review.py` (341) the review helper · `deep_pass_process.py` (241) the pass's own progress file.

**Retention and hygiene:**
`keep.py` (241) manifest, archive, lab snapshots · `prune_runs.py` (411) run records older than a week and captures older than three days that nothing stands on · `processes.py` (1209) the DNA patrol, the reminders and the deep pass's "what changed since last time".

### Harness

| | |
|---|---|
| Hooks (8) | `protect_state.py` (PreToolUse — refuses hand-writes under `state/`), `no_heredoc_writes.py` (PreToolUse — refuses heredoc writes into the repo), and six SessionStart lines: `open_threads.py`, `deep_pass_handover.py`, `memory_index.py`, `next_step.py`, `reminders.py`, `room_notes.py` |
| Skills (6) | `deep-pass` (822 lines), `laborator` (270), `qa-sweep` (219), `channels` (101), `ohlednuti` (90), `pokracuj` (25) |
| Agents (2) | `check-auditor` (92), `finding-triage` (85) — both `model: opus, effort: high`, both read-only (`disallowedTools: Write, Edit, NotebookEdit`) |
| Git hooks | `.githooks/pre-commit` (calls `keep.py track`), `.githooks/prepare-commit-msg` |
| Settings | `.claude/settings.json` — 32 allowlisted Bash patterns, 6 SessionStart hooks, 2 PreToolUse matcher groups |

---

## 2. Data flow

### The CHECK axis — a run becomes ledger rows

```
pytest tests/... --prereg PRE-NNNN
   │
   ├─ conftest.py    collection-time: untagged test aborts collection;
   │                 tests/meta reordered first and aborts the session on
   │                 failure; every test runs inside a tier context
   │
   ├─ qa/safety.py   SafetyTransport checks the running test's tier on
   │                 every request; qa/client.py bans clients built elsewhere
   │
   ├─ check body     qa/measure.py: Measurement → conclude() raises or returns
   │                 qa/evidence.py: request/response hashed to evidence/
   │
   └─ qa/report_plugin.py
          sessionstart:  fingerprint computed (qa/fingerprint.py)
          logreport:     each result appended with its measurement + evidence ids
          sessionfinish: state/runs/<run_id>.json written (schema 2)
                         → collected, exit_status, record_integrity block
```

Then, separately:

```
python scripts/ledger.py --run <run_id>
   │
   ├─ qa/state.py   load_run(run_id)  — by run_id FIELD, not filename
   │                admissibility()   — level R or V, each blocker named
   │                run_integrity()   — checks the record against facts
   │                                    outside it (tree, prereg tag, selector)
   │                read_events()     — the whole journal, hash chain verified
   │
   ├─ qa/fold.py    fold(previous_rows, run, events)
   │                   _apply_run          → CHECK axis
   │                   _apply_check_definition → rebind / pin / retire
   │                   _apply_events       → FILING axis (replayed from zero)
   │                   _obligations        → reverify, repair_check, reopen,
   │                                         retractions, verification_owed,
   │                                         correction_owed, disputed
   │
   └─ qa/state.py   write_ledger()  — refuses a write that moves history back
                    append_event("run_recorded")  — only when attest=True,
                                                    i.e. not on --check
```

`scripts/render.py` then reads `state/*.json` and writes `dashboard/index.html`.
`display_state()` composes the two axes at render time; the displayed state is
never stored, so it cannot be assigned.

### The FILING axis — four channels, three of them in the journal

| Channel | Direction | Written by | Event types | Does the fold read it? |
|---|---|---|---|---|
| Bug reports | both | `submit.py`, `bounty.py`, `verify.py` | `filing_intent`, `filing_outcome`, `vendor_read`, `vendor_status`, `verification_intent`, `verification_outcome`, `message(origin=a2a)` | **Yes** — this is the FILING axis |
| Telegram | both | `correspond.py` | `telegram_sent`, `telegram_reply` | No |
| a2a | both | `a2a.py` | `a2a_intent`, `a2a_outcome` | No |
| Rooms | both | `qa/rooms.py` (not the journal — `state/rooms.jsonl`) | — | No |

`qa/fold.py` contains no occurrence of `telegram` or `a2a`. `qa/channels.py` is
the only module that reads all four, and it is a library: the CLI
(`scripts/channels.py`) and the dashboard (`scripts/render.py:380`) go through
it, and so does the `open_threads` SessionStart hook, which names the
unanswered ids of every channel whose `waiting_on` is "them". It read
`scripts/correspond.py` and saw Telegram alone until 2026-09-20.

Journal composition today (2364 events):

```
754 vendor_read        701 vendor_status      203 run_recorded
121 verification_intent  121 verification_outcome   71 pin_fingerprint
 70 message             60 filing_outcome      58 filing_intent
 53 retire_check        41 rebind_check        27 telegram_reply
 26 telegram_sent       20 backfill            10 withdraw
 10 legacy_verification  5 retraction_sent      5 note
  3 migrated             2 a2a_intent           2 a2a_outcome
  1 reply
```

The first reading's `UNCERTAIN:` about `vendor_status` is answered: **556 of
the 701 repeat the previous status of the same report**, 641 of them landed
before 2026-09-08, and the writer (`scripts/bounty.py`) has since been
hardened to record a move rather than a poll. Read the type as "we looked and
wrote it down", not as "their side changed".

---

## 3. Dependencies

**External:** `httpx` (all network — through `qa/client.py` factories, with no
exception since 2026-09-20, and a static guard saying so), `pytest` 8 + the
first-party plugin, `PyYAML`
(`components.yaml`, `claims.yaml`, `reports.yaml`), `Jinja2` (declared in
`pyproject.toml`, imported by nothing). No jsonpath library, by decision
(`qa/extractors.py`). No database — every store is a JSON or JSONL file under
`state/`, and `docs/data-plan.md` governs what leaves it.

**Internal, the load-bearing edges:**

```
components.yaml ──> qa/safety.py (EndpointRegistry) ──> qa/client.py
                                 └──> qa/fingerprint.py (via registry.raw)
                └──> qa/config.py:95 (base_urls)
                └──> tests/conftest.py (tag validation)
                └──> qa/report_plugin.py:53 (hashed into the tree fingerprint)

qa/state.py  <── everything that touches state/ledger.json or the journal
qa/fold.py   <── ledger.py (fold), and render.py, never_fired.py,
                 open_checks.py, withdraw.py (display vocabulary)
qa/channels.py <── scripts/channels.py, scripts/render.py:380
qa/lab.py    <── scripts/lab.py, scripts/nexus.py, scripts/paper.py
```

**The `QA_STATE_DIR` seam.** Every read and write of `state/` is supposed to
resolve through `qa.state.state_dir()` at call time, so a test can redirect the
whole store to a tmp tree. Honoured by every module that reads or writes
state as of 2026-09-20; the three that bound a path from `REPO_ROOT` at import
time were repaired that day, and `tests/repo/test_state_seam.py` refuses the
fourth. Two exemptions stand by name: `qa/state.py`, which is the seam, and
`.claude/hooks/protect_state.py`, which must mean the committed directory
whatever the environment says.

---

## 4. Where state changes

Every writer under `state/`, established by reading each module that names an
artefact there. **The method matters:** the first reading walked `write_text` /
`open(...,'w')` / `os.replace` / `json.dump` and therefore could not see an
append — nine of today's writers are append-mode JSONL.

| Writer | Writes | Sanctioned by |
|---|---|---|
| `qa/state.py:496` | `state/ledger.json` (tmp + `os.replace`) | the contract — the only ledger writer |
| `qa/state.py:797` `append_event` | `state/journal/events.jsonl` | the contract — the only journal writer |
| `qa/report_plugin.py:464` | `state/runs/<run_id>.json` | run records; path resolved at write time |
| `scripts/bounty.py:269, :680` | `state/bounty.json` | vendor snapshot, under `file_lock` |
| `scripts/inventory.py:586` | `state/inventory.json` | section map; **`__main__` only** |
| `scripts/prereg.py:108` | `state/preregistrations/PRE-NNNN.md` | preregistration |
| `qa/lab.py` | `state/lab.jsonl` | the laboratory's diary (gitignored) |
| `qa/backtests.py` | `state/backtests.jsonl` | the backtest register (gitignored) |
| `qa/rooms.py` | `state/rooms.jsonl`, `state/samples.jsonl` | rooms and sampler rows (gitignored) |
| `scripts/nexus.py` | `state/nexus.jsonl`, `state/nexus_shallow.jsonl` | the two lanes to their AI |
| `scripts/paper.py` | `state/paper.jsonl` | paper orders |
| `scripts/clone.py` | `state/clones.jsonl` | cloned bots |
| `scripts/fomo_watch.py` | `state/fomo_signals.jsonl` | memecoin checkpoints |
| `scripts/lab.py:1802` | `state/lab_tick.json` (tmp + `Path.replace`) | the tick's own state |
| `scripts/prune_runs.py:405` | **deletes** run records and captures | `--apply` only, by name, never by glob |
| `qa/evidence.py:200` | `evidence/sha256/…` | beside `state/`, never inside |
| `qa/manifest.py:119` | `audits/evidence-manifest.jsonl` | the proof that outlives the body |
| `qa/archive.py:152` | `archive/evidence-YYYY-MM.tar.xz` | hashed back before release |
| `scripts/render.py:5030`, `scripts/serve.py:304` | `dashboard/index.html` — under `state/` when `QA_STATE_DIR` is set, since both route through `render.out_path()` | the console |

So the accurate sentence is: **`qa/state.py` is the only module that writes the
ledger and the journal.** Twelve other modules write other files under
`state/`, each with a narrow, single-purpose artefact, and all but four of
those are gitignored diaries. The guard test
(`tests/meta/test_pipeline_withdraw.py:169`) enforces exactly the accurate
sentence — it AST-walks nine call names and substring-matches a seven-line
window for `ledger`, `events` or `journal`; its own comment explains that
widening it to `state` would fire on the run recorder and the dashboard writer
and "would be relaxed within a day". It exempts one path by name, `qa/state.py`.

Three enforcement layers, in order of when they act:

1. **Before the write** — `.claude/hooks/protect_state.py`, PreToolUse on
   `Write|Edit|MultiEdit|NotebookEdit|Bash|PowerShell`. Refuses editor writes
   to paths under `state/` and shell forms aimed there: redirects, `sed -i`,
   `rm`, `git checkout|restore`, `tee`, `mv`, `cp`, `truncate`, `dd`, the
   PowerShell equivalents, and `python -c "open('state/x','w')"`. Reads pass.
2. **At the write** — `write_ledger` refuses a non-monotonic ledger (a row
   that disappeared, `first_seen` moving back, reproductions decreasing,
   verification provenance cleared, dropped transitions, an `events_head` that
   does not cite the journal head); `append_event` validates and hash-chains.
3. **At the next read** — the chain check raises "chain mismatch (payload
   edited?)" (`qa/state.py:700`); `tests/repo/test_repo_consistency.py`
   refolds the committed inputs and compares.

---

## 5. Key decisions visible in the code

Every claim in this section was re-established from the source on 2026-09-20.

* **The displayed state is composed, not stored** (`fold.py:_display_cell`).
  Removes the field a hand-edit would target. `VERIFIED FIXED` maps PASSING
  beside RAISED, REPLIED *and* FIX_CLAIMED — whether the thing is broken does
  not depend on whether they said anything.
* **The FILING axis is replayed from zero on every fold** (`_apply_events`,
  which resets every row before replay). Consequence, and it is load-bearing:
  improving the mapping rewrites the past, so a better rule is a migration
  rather than an edit.
* **Attestation is a flag, not a side effect** (`scripts/ledger.py:151,
  :207-208`). `compose` appends `run_recorded` only when `attest=True`, there
  is a run, and the run was not rejected; `--check` writes nothing and
  therefore attests nothing. The comment names the defect this replaced.
* **Safety is enforced in the transport, not in helpers** (`safety.py:11-17`).
  Four layers: client construction banned outside the factories
  (`client.py:35-47`); a request with no tier in scope refused outright (no
  default); the transport checks the running test's tier; `probe_only` is a
  hard floor no `--allow-mutate` can lift (`safety.py:245-248`).
* **Inconclusive is a first-class verdict** (`measure.py`, `sources.py`). A
  missing field or a drifted source is never a defect. This is what keeps a
  false contradiction from reaching the vendor.
* **One reader per concept.** `qa/channels.py` exists so the CLI, the alert and
  any skill cannot grow three definitions of "unanswered"; `serve.py` imports
  `render()` rather than reimplementing it, because "a second renderer would be
  a second truth".
* **Evidence before claim** (`evidence.py`, `submit.py:83, :97`). Numbers in an
  outgoing report are injected from the ledger at send time; a finding whose
  figures no admissible run has measured is refused rather than sent stale.
* **`--confirm` on every outbound write** (`submit.py:415`, `verify.py:562`,
  `a2a.py:268`). Composing and sending are separate steps, and the compose step
  writes the journal first, so a POST that times out still leaves the text
  behind. Without `--confirm`, `a2a.py` deliberately journals nothing.
* **A capture body never enters git** (`docs/data-plan.md`, 2026-09-12). The
  manifest stands for 275 MB in 228 KB; `keep.py archive` hashes every member
  back out of the written bundle before releasing a single original.

---

## 6. The weight of each mechanism

The first reading hand-rolled this table and it went stale the week it was
written. It is now a command, and the command is the answer:

```bash
python scripts/processes.py patrol
```

`scripts/processes.py` finds every skill, agent, script and hook by glob and
reads what each one did from the records it left behind and from the commands
in the transcripts — nothing declares itself, because a declaration is a thing
to forget. A snapshot from 2026-09-20, busiest first:

```
sampler.py 294 · lab.py 235 · bounty.py 186 · correspond.py 68 · nexus.py 56
ledger.py 41 · render.py 39 · submit.py 28 · processes.py 21 · verify.py 18
withdraw.py 18 · memories.py 17 · prereg.py 16 · finding-triage 15 · rooms.py 15
fomo_watch.py 14 · check-auditor 7 · movers.py 7 · never_fired.py 7
inventory.py 5 · keep.py 4 · laborator 3 · open_checks.py 3 · paper.py 3
pokracuj 3 · review.py 3 · deep_pass_process.py 2 · qa-sweep 2 · serve.py 2
deep-pass 1 · a2a.py 0 (9d) · channels 0 · channels.py 0 · clone.py 0 (9d)
findings.py 0 · prune_runs.py 0 · every hook 0 (a hook leaves no record)
```

with the ceilings the patrol also reports: `claude_md_lines=736`,
`evidence_mb=265.5`, `memory_lines=48`, `next_oldest_days=10.3`,
`pack_mb=63.5`. `tests/repo/test_process_dna.py` holds every ceiling above
where the repository stood the day it was set, and is red today on
`next_oldest_days`.

### The headline imbalance

| Directory | Functions | Collected | What it tests |
|---|---|---|---|
| `tests/meta` | 555 | 761 | our own pipeline |
| `tests/repo` | 137 | 175 | our own repository |
| `tests/rest` | 44 | 44 | the vendor |
| `tests/mcp` | 16 | 18 | the vendor |
| `tests/discovery` | 5 | 5 | the vendor |
| `tests/reconciliation` | 4 | 8 | the vendor |
| `tests/pinned` | 2 | 4 | the vendor |
| **total** | **763** | **1015** | |

**936 of 1015 collected tests (92%) test us. 79 test Cymetica.** On 2026-09-08
it was 89% of 473. The imbalance the first reading named as the thing no single
test can answer has widened, not closed: `tests/meta` went from ~7.5k lines to
**22.7k**, the vendor-facing suite from 46 functions to 71. Tier distribution:
756 SAFE, 10 PROBE, 0 MUTATE — PROBE has not moved in 483 new tests. The MUTATE
tier is not dead: `submit.py:291`, `verify.py:457` and `clone.py:303` set it for
the three real writes.

`scripts/render.py` is 5039 lines and 82 commits — the most-churned
hand-written file in the repository, ahead of `scripts/lab.py` (2463 lines, 29
commits). Four generated files churn more (`dashboard/index.html` 340, the
journal 273, `state/bounty.json` 184, `state/ledger.json` 182), which is why
"the most volatile file in the repository" was wrong when the first reading
said it (§9.4). Eleven test files touch `render.py`.

### Never fired — 4 of 55 (`scripts/never_fired.py --zeros`)

`SUPERSEDED`, `supersede`, `results_not_collected`, `prereg_commit_mismatch`.
All four are exercised by a test, so none is known-broken; what is left is a
judgement about whether a condition we have never met is one we should have met
by now. Three symbols the first reading listed have since fired for real:
`a2a_intent`, `a2a_outcome` (2026-09-10) and `reopen`.

### The reds, and why a red matters here

`pytest tests/meta tests/repo` is **934 passed, 1 failed** today. The failure is
`test_process_dna.py::test_no_ceiling_is_set_below_where_we_already_stand`:
the oldest open line in `NEXT.md` is 10.3 days old against a ceiling of 10 set
on 2026-09-12. That is the operator's backlog, not a broken mechanism.

The first reading's structural red — rule 12's guard going red whenever the
console polled after a compose — was removed on 2026-09-09 by taking
`events_head` out of `drift`'s comparison. It holds: the journal is four events
ahead of the ledger's head right now and the guard is green. Its replacement
appeared on 2026-09-20 in the same shape one file along: committing
correspondence without re-rendering left the committed dashboard out of step
with the committed ledger, and `test_committed_dashboard_matches_the_committed_ledger`
went red for a boring reason. Render after the state change, commit both, and
it stays green.

---

## 7. The record of our work

| Layer | Answers | Cannot answer | Managed? |
|---|---|---|---|
| **Journal** (2364 events) | what the *pipeline* did, in order, hash-chained | anything the operator did outside the pipeline — a Telegram message they sent and did not file leaves no trace | append-only, never pruned |
| **Git log** (763 commits) | what changed in the code and why, in prose | why an approach was abandoned before it was committed | permanent |
| **Memory dir** (54 files, a 48-line index) | how *reasoning* failed — the inference from a stale docstring, the field not read | anything not written down in the moment | pruned by the deep pass; `scripts/memories.py --for <task>` is how it is read |
| **`audits/`** | what each pass audited (`checks.json`, 1031 entries), the pass's own progress, the patrol's history, the lab diaries under `audits/lab/` | — | accumulates |
| **Session transcripts** | how a session actually worked, minute by minute | anything after a `/clear` unless written elsewhere | outside the repo |

`DEEP-PASS.md` holds only the newest report on disk; git holds twelve report
commits over eight pass dates. There is still no *directory* of dated reports,
so a reader must reach for `git log -p -- DEEP-PASS.md` — a discoverability
gap, not data loss. The journal records what the pipeline did during those
nights; it does not record what a pass decided or why.

---

## 8. Where the documentation lies

### 8.1 A skill named in git history no longer exists

`.claude/skills/night-shift/SKILL.md` appears in `git log --name-only`; the
directory today holds `channels`, `deep-pass`, `laborator`, `ohlednuti`,
`pokracuj`, `qa-sweep`. This is the documented rename ("Named for what it does,
not for the night"), not a lie — recorded so the next reader does not chase it.

### Fixed since the first reading

`CLAUDE.md`'s "the ONLY module that writes `state/`" now says ledger and
journal and lists the narrow writers. Its never-fired count is gone, replaced
by "read the count off the tool, never off prose". `state/thread.json` and
`qa/messages.py` were deleted. `scripts/open_checks.py` and the `qa-sweep`
skill no longer carry "31 rows" or "29 settled rows" (the last two survivors
were removed on 2026-09-20).

### Fixed by the work this reading prompted, 2026-09-20

Each of these was a numbered hole in the first draft of this section a few
hours ago; each is closed in the tree, and each closure carries a guard, so
the entry here is a record rather than a warning.

* **`components.yaml` named `qa/components.py`**, a module that has never
  existed, and omitted the two modules that do read the file. The header now
  lists what a grep finds, and says what it used to claim.
* **Three modules bound a path under `state/` at import time**
  (`inventory.py`, `submit.py`, `processes.py`), so a test redirecting
  `QA_STATE_DIR` was handed the committed files. Resolved at call time;
  `submit.py`'s was deleted outright as a dead read.
  Guard: `tests/repo/test_state_seam.py`.
* **`qa/fingerprint.py` held the guard's private sentinel** and built its own
  client, so the corpus was read with no `SafetyTransport` under it. Replaced
  by `qa/client.py::build_fingerprint_client`, which keeps the request shape
  byte-for-byte — the fingerprint is a hash of response bytes. Guards:
  `tests/repo/test_client_construction.py` and a behavioural one in
  `tests/meta/test_guard_is_real.py`.
* **`qa/channels.py` had two readers of "unanswered" on a2a** and `state()`
  used the blind one, so the session-start line and every status report said
  nothing was open while five threads were. Guard:
  `test_the_two_a2a_readers_cannot_disagree`.
* **The session-start hook read Telegram only.** It now reads the channels
  module and names every channel that waits on them. Guard: a test that runs
  the hook and requires each such channel to appear.
* **Rule 12 depended on remembering to render.** `.githooks/pre-commit` runs
  `render.py --if-stale`, which writes only when the page would change.
  Guard: `tests/repo/test_render_if_stale.py`.
* **Five scripts our own instructions name were not allowlisted**, so each
  invocation cost a prompt. Guard: `tests/repo/test_allowlist.py`.

---

## 9. What the 2026-09-08 reading got wrong

Kept because a third reading would otherwise make the same seven mistakes. All
were established on 2026-09-20 by four readers working from the source, one
section each, with the sharpest repeated by hand.

1. **`qa/fold.py <── scripts/ledger.py only`.** Five scripts imported the
   module at `702a65c`. Only `fold()` itself is called from one place.
2. **"httpx … only through `qa/client.py` factories."** True of every module
   but `qa/fingerprint.py`, which was already holding the guard's sentinel
   when the sentence was written. True without exception since 2026-09-20.
3. **`message(origin=a2a)` attributed to `scripts/a2a.py`.** It is written by
   `scripts/bounty.py:389`, which reads the a2a inbox.
4. **`scripts/render.py` as "the most volatile file in the repository".** By
   the reading's own command it ranked behind `dashboard/index.html` then
   (144 vs 44) and behind four generated files now. True of source files only.
5. **`scripts/withdraw.py` "9 commits".** It had 3 then and has 3 now; the
   Fired column's "9 withdrawals" leaked one cell to the left.
6. **"Journal 1429 events".** The commit holds 1427.
7. **Two edges in §3.** The `open_threads` hook reached `scripts/correspond.py`,
   not `qa/channels.py` — true when written, and repaired on 2026-09-20 by
   making the hook read the channels module; and
   `tests/meta/test_pipeline_abort.py` was never a `components.yaml` consumer.

Everything else in that reading was exact for the day it was made — all 26
named functions, every module responsibility, every line count, the ledger and
journal breakdown, both agents' frontmatter. The failure mode worth carrying
forward is not carelessness but shape: **each of the seven is a number or an
absence read off one command, with a conclusion drawn that a second command
would have refuted.**

---

## Verification of this document

Established on 2026-09-20 from the source at `8f6aa3ed`, by four readers
working independently over sections 1–8 of the previous reading and by hand
afterwards for anything that contradicted it. Nothing here was taken from
CLAUDE.md, and the numbers come from commands, not from prose:
`git ls-files`, `wc -l`, `pytest --collect-only -q`, a Counter over the
journal, `scripts/never_fired.py --zeros`, `scripts/processes.py patrol`, and
an AST walk for the writers in §4.

`UNCERTAIN:` how many of the 2364 journal events were written by test runs
rather than real work. Tests redirect through `QA_STATE_DIR`, and the `attest`
flag closed the path that caused the 98-of-137 leak, but this was not
re-established for every test file in this reading.

What this document cannot do is stay true. The first reading was exact and was
overtaken in eleven days; this one will be overtaken too. The parts that do not
go stale are the ones that became commands — `processes.py patrol` for §6, the
guard test for §4, `never_fired.py` for the vocabulary. Prefer those to the
prose around them.
