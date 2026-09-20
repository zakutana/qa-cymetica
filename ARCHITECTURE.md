# ARCHITECTURE.md — the system as the code has it

Read from the source on 2026-09-08, at commit `702a65c`, deliberately **without**
taking CLAUDE.md's word for anything. Where the two disagree, the disagreement is
recorded in the last section rather than silently resolved.

> **Superseded in part on 2026-09-09** by `docs/UPGRADE-PLAN.md`, which was built
> from this document and then acted on. This file was not rewritten — it is a
> dated reading, and rewriting it would destroy the record of what was true when
> the plan was made. What has since changed, so nothing here is believed twice:
>
> * §6's red guard is fixed. Rule 12's comparison is `scripts/ledger.py::drift`,
>   shared with `--check`; `events_head` is checked as a citation and the rows
>   against a refold over the whole journal. Its `UNCERTAIN` is resolved: the
>   deep pass had been tolerating the red inside its step-6 prereg run.
> * `scripts/migrate_ledger.py`, `tests/meta/test_pipeline_migration.py`,
>   `qa/messages.py`, three dead functions in `render.py`, the
>   `allow_stale_head` flag and `tests/boundaries/` are gone; `render.py` is
>   1899 lines. Three duplicate meta tests were merged or deleted.
> * §7's `UNCERTAIN` is resolved: `consolidate-memory` had never run here. The
>   deep pass now prunes as well as adds, may change a rule under the operator's
>   three conditions, and looks back weekly.
> * §7's fourth layer was measured and this document's own figure was wrong in
>   composition: `evidence/` is written mostly by the test suite, not the
>   console. See the plan's Context section.
> * Decisions attributed to the operator now carry an `[operator YYYY-MM-DD]`
>   tag and are pinned by `tests/meta/test_pipeline_decisions.py`.
>
> §8's list of documentation that lies was acted on: 8.2, 8.4 and 8.5 are fixed
> in place, 8.1 and 8.3 are not.

> **Re-measured on 2026-09-20 at `5fd7968`, and largely overtaken.** Four
> independent readers took one section each and put every claim to the tree,
> with the sharpest ones repeated by hand afterwards. The body below is left
> exactly as it was: a dated reading rewritten is a record destroyed. What the
> audit established:
>
> * **Scale.** Python 79 files / 26.8k lines → **167 / 68.6k**. Test functions
>   283 → **763**, collected 473 → **1015**, and the share guarding our own
>   machinery went 89% → **92%** — the imbalance §6 is about got worse. Ledger
>   41 rows → **62**, with two display states the body never names (`RAISED`,
>   `OUR CHECK CANNOT TELL`). Journal 1429 → **2364**. Commits 332 → **763**.
>   `scripts/render.py` 1986 → **5039** lines (the note above says 1899; that is
>   stale too).
> * **A whole subsystem is absent.** The laboratory and the retention machinery
>   landed after this reading: 14 scripts and 9 `qa/` modules §1 does not list,
>   among them `scripts/lab.py` (2463 lines, the most-churned script after
>   `render.py`) and `qa/lab.py` (1283). §6's per-mechanism table is missing 25
>   rows — its own current size — and one row describes
>   `scripts/migrate_ledger.py`, deleted on 2026-09-09. Harness: 3 hooks → 8,
>   3 skills → 6, 24 allowlisted Bash patterns → 32.
> * **§4's table cannot be completed by its own method.** It names `write_text`
>   / `open(...,'w')` / `os.replace` / `json.dump`; nine of today's twelve
>   non-`qa/state.py` writers under `state/` are append-mode JSONL
>   (`lab.jsonl`, `rooms.jsonl`, `samples.jsonl`, `nexus.jsonl`, `paper.jsonl`,
>   `clones.jsonl`, `fomo_signals.jsonl`, `backtests.jsonl`) and one is
>   `Path.replace`. "Four other modules" is wrong; twelve is the number. The
>   sentence that table protects — `qa/state.py` is the only module that writes
>   the ledger and the journal — was re-derived independently and still holds.
>
> **Seven claims were wrong when written, not merely stale:**
>
> 1. `qa/fold.py <── scripts/ledger.py only`. Five scripts imported the module
>    at `702a65c`, six call sites do today. Only `fold()` itself is called from
>    one place (`scripts/ledger.py:187`), which is the claim that survives.
> 2. "httpx (all network, only through `qa/client.py` factories)".
>    `qa/fingerprint.py:83` constructs a client directly while holding the
>    guard's private `_FACTORY_SENTINEL`, so the corpus reads run with no
>    `SafetyTransport`, no evidence capture and no rate-limit budget — the one
>    thing the guard's own refusal message tells a caller not to do. Present at
>    this reading's own commit.
> 3. `message(origin=a2a)` is written by `scripts/bounty.py:389`. The file the
>    FILING table credits, `scripts/a2a.py`, has never emitted that type.
> 4. `scripts/render.py` as "the most volatile file in the repository". By the
>    stated command it ranked behind `dashboard/index.html` then (144 vs 44)
>    and behind four generated files now (340 / 273 / 184 / 182 vs 82). It is
>    the most-churned hand-written source file, which is the interesting claim.
> 5. `scripts/withdraw.py` "9 commits" — 3 then, 3 now; the Fired column's "9
>    withdrawals" leaked one cell to the left.
> 6. "Journal 1429 events" — the commit holds 1427.
> 7. Two edges in §3: the `open_threads` hook reaches `scripts/correspond.py`
>    and not `qa/channels.py`, and `tests/meta/test_pipeline_abort.py` was
>    never a `components.yaml` consumer.
>
> **Resolved since, in the tree rather than here.** §6's red guard is green:
> `events_head` left `drift`'s comparison on 2026-09-09, and the test passes
> today with the journal four events ahead of the ledger's head — the exact
> condition that used to make it red. §2's `UNCERTAIN` about 654
> `vendor_status` events resolves as a duplicate-write path in
> `scripts/bounty.py`: 556 of today's 701 repeat the previous status of the
> same report, 641 of them landed before this reading's commit, and the path
> has since been hardened. `never_fired` says **4 of 55**, not 7 of 54 —
> `a2a_intent`, `a2a_outcome` and `reopen` have fired. Of §8: 8.2 and 8.5 are
> fixed, 8.7's subject was deleted, 8.4 is fixed in three of its four places,
> 8.1 and 8.3 survive intact. And `qa/channels.py` has read a **fourth**
> channel since 2026-09-11 — the console's rooms, which do not come from the
> journal at all — so §2's heading names one fewer than the reader returns.

This file is for sessions, not for the operator. It is descriptive only: no
proposals, no fixes. Claims marked `UNCERTAIN:` were not established from the
source and must not be built on. Claims marked `UNCONFIRMED (triage)` failed the
verification pass described at the end.

Scale, for orientation:

| | |
|---|---|
| Python | 79 files, ~26.8k lines — `qa/` 4.4k, `scripts/` 7.7k, `tests/` 14.4k |
| Tests | 283 test *functions*; `pytest --collect-only` reports **473** items after parametrisation |
| Ledger | 41 rows: 31 VERIFIED FIXED, 9 WITHDRAWN, 1 STILL REPRODUCIBLE |
| Journal | 1429 events, 20 types, 2026-09-04 → 2026-09-08 |
| Run records | 610 under `state/runs/` |
| Commits | 332, all on `main` |

---

## 1. Components

### The core: three modules that own the contract

| Module | Lines | Responsibility |
|---|---|---|
| `qa/state.py` | 794 | The I/O boundary for `state/ledger.json` and `state/journal/events.jsonl`. Admissibility (`admissibility`, `run_integrity`), the monotonic ledger write (`write_ledger`), the hash-chained append-only journal (`append_event`, `read_events`, `head`), cross-process locking (`file_lock`), and the `QA_STATE_DIR` seam (`state_dir`). |
| `qa/fold.py` | 739 | Pure. `fold(previous, run, events)` → new ledger. Two axes moved independently (`_apply_run` for CHECK, `_apply_events` for FILING), display composed at render time (`_display_cell`, `display_state`), obligations derived (`_obligations`). Imports nothing that writes. |
| `qa/measure.py` | 168 | `Measurement` + `conclude()`. A check's verdict and pytest's outcome are one value. `required` / `field_of_every` / `collection_size` return Inconclusive rather than raising when a source lacks data. |

### The suite's machinery

| Module | Lines | Responsibility |
|---|---|---|
| `qa/safety.py` | 417 | `SafetyTier` (SAFE/PROBE/MUTATE), `EndpointRegistry` loaded from `components.yaml`, `SafetyTransport` enforcing tier at the transport layer, `RateLimitBudget`. Default-deny: an endpoint with no rule refuses any non-read method. |
| `qa/client.py` | 395 | The only sanctioned constructor of HTTP and MCP clients. `install_client_guard` makes constructing an `httpx` client outside these factories raise; `assert_client_guard_blocks` is the negative control. |
| `qa/report_plugin.py` | 413 | First-party pytest plugin, registered by `-p qa.report_plugin` in `pyproject.toml`. Turns a session into a schema-2 run record under `state/runs/`. Classification is a `tryfirst` hookwrapper so it runs last. |
| `qa/fingerprint.py` | 161 | The platform fingerprint: a hash over documents that change when the vendor ships. Corpus spec comes from `components.yaml` via `EndpointRegistry.load().raw["fingerprint"]`. `QA_OFFLINE=1` short-circuits it to `None`. |
| `qa/evidence.py` | 178 | Content-addressed request/response capture under `evidence/sha256/`, with redaction before write. |
| `qa/sources.py` | 179 | One fetch per source per session, with `Date`/`X-Cache-Status`, so a reconciliation whose sources drifted outside the window is INCONCLUSIVE rather than a contradiction. |
| `qa/extractors.py` | 352 | Hand-rolled extractor DSL for `tests/reconciliation/claims.yaml`. Deliberately not jsonpath-ng. |
| `qa/channels.py` | 284 | The one reader across all three vendor channels, over the journal. `inbound`, `pairs`, `state`, `compare`. |
| `qa/marks.py` | 63 | The `@qa` decorator — one marker carrying component, tier, surface. |
| `qa/config.py` | 99 | `.env` loading, `Identity` registry, `base_urls()` (reads `components.yaml`). |
| `qa/messages.py` | 105 | Parses archived message files for the dashboard's Correspondence panel. Library only. |

### Scripts, by what they do

**Compose and render (run after every state change):**
`ledger.py` (300) CLI over the fold · `render.py` (1986) state → `dashboard/index.html` · `serve.py` (529) the same render served on 127.0.0.1:8787, watching `state/`, with `--ask MINUTES` polling the vendor.

**Write to the vendor (the only deliberate outbound):**
`submit.py` (524) files reports, every number injected from the ledger at send time · `verify.py` (572) posts a verification that a check passes under the fingerprint it last failed under · `a2a.py` (286) sends an a2a question, only on `--confirm`.

**Read from the vendor:**
`bounty.py` (680) their tracker → `state/bounty.json`, recording changes not polls · `inventory.py` (564) the platform section map, SAFE tier only · `channels.py` (197) all three channels in one place (`status`, `compare`, `watch`).

**Operator writes:**
`withdraw.py` (280) the only human writer — every command is one event with a reason · `correspond.py` (320) the Telegram thread as a record with ids · `prereg.py` (179) freeze and tag a run's configuration.

**Derivation and inspection:**
`findings.py` (268) run record → candidate findings, holds no state · `never_fired.py` (387) which vocabulary symbols have never occurred in the data · `open_checks.py` (145) the selector for a sweep over what is open · `migrate_ledger.py` (447) one-shot, refuses to run twice.

### Harness

| | |
|---|---|
| Hooks | `protect_state.py` (PreToolUse — refuses hand-writes under `state/`), `open_threads.py` (SessionStart — one line of unanswered Telegram ids), `deep_pass_handover.py` (SessionStart — prints the last handover) |
| Skills | `deep-pass` (300 lines), `qa-sweep` (204), `channels` (76) |
| Agents | `check-auditor`, `finding-triage` — both `model: opus, effort: high`, both read-only (`disallowedTools: Write, Edit, NotebookEdit`) |
| Settings | `.claude/settings.json` — 24 allowlisted Bash patterns, 2 SessionStart hooks, 1 PreToolUse hook |

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
                         → collected, exit_status, consistency block
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

### The FILING axis — three channels, one journal

| Channel | Direction | Written by | Event types | Does the fold read it? |
|---|---|---|---|---|
| Bug reports | both | `submit.py`, `bounty.py`, `verify.py` | `filing_intent`, `filing_outcome`, `vendor_read`, `vendor_status`, `verification_intent`, `verification_outcome` | **Yes** — this is the FILING axis |
| Telegram | both | `correspond.py` | `telegram_sent`, `telegram_reply` | **No** |
| a2a | both | `a2a.py` | `a2a_intent`, `a2a_outcome`, `message(origin=a2a)` | **No** |

Verified by inspection: `qa/fold.py` contains no occurrence of `telegram` or
`a2a`. `qa/channels.py` is the only module that reads all three, and it is a
library — the CLI, the SessionStart hook and the skills all go through it.

Journal composition today (1429 events):

```
654 vendor_status      158 run_recorded       147 vendor_read
 75 verification_intent  75 verification_outcome  53 retire_check
 52 message             43 pin_fingerprint     41 rebind_check
 36 filing_outcome      35 filing_intent       20 backfill
 10 legacy_verification  9 withdraw             5 telegram_reply
  4 retraction_sent      4 note                 4 telegram_sent
  3 migrated             1 reply
```

`UNCERTAIN:` 654 `vendor_status` events in four days over 41 rows is high for a
type that `scripts/bounty.py` documents as written "only when a status actually
moved". Not investigated here; it may be the pre-hardening backfill, the
migration, or a genuine duplicate-write path. Anyone reading the journal as a
record of vendor behaviour should establish this first.

---

## 3. Dependencies

**External:** `httpx` (all network, only through `qa/client.py` factories),
`pytest` 8 + the first-party plugin, `PyYAML` (`components.yaml`,
`claims.yaml`, `reports.yaml`). No jsonpath library, by decision
(`qa/extractors.py`). No database — every store is a JSON or JSONL file under
`state/`.

**Internal, the load-bearing edges:**

```
components.yaml ──> qa/safety.py (EndpointRegistry) ──> qa/client.py
                                 └──> qa/fingerprint.py (via registry.raw)
                └──> qa/config.py (base_urls)
                └──> tests/conftest.py (tag validation)

qa/state.py  <── everything that touches state/ledger.json or the journal
qa/fold.py   <── scripts/ledger.py only (pure; imports no writer)
qa/channels.py <── scripts/channels.py, .claude/hooks/open_threads.py (via
                   scripts/correspond.py), the channels skill
```

Real consumers of `components.yaml`, from the source: `qa/safety.py:44`,
`qa/config.py:91`, `tests/conftest.py:104`, `qa/fingerprint.py` (indirectly,
through `EndpointRegistry.load().raw["fingerprint"]`), plus
`tests/meta/test_guard_is_real.py`, `tests/meta/test_pipeline_abort.py`,
`tests/repo/test_state_guard.py`. `qa/marks.py` and `qa/client.py` only mention
it in prose.

**The `QA_STATE_DIR` seam.** Every read and write of `state/` is supposed to
resolve through `qa.state.state_dir()` at call time, so a test can redirect the
whole store to a tmp tree. Honoured by `qa/state.py`, `qa/evidence.py`,
`qa/report_plugin.py` (resolved at write time, with a comment saying why),
`scripts/bounty.py` (`out_path()`), `scripts/open_checks.py`,
`scripts/render.py:272`, `scripts/serve.py`. **Not honoured** by
`scripts/inventory.py:35`, which builds `OUT` from `REPO_ROOT` at import time —
see section 8.

---

## 4. Where state changes

Every write under `state/`, established by walking every `write_text` /
`open(...,'w')` / `os.replace` / `json.dump` call site in `qa/`, `scripts/` and
`.claude/hooks/`:

| Writer | Writes | Sanctioned by |
|---|---|---|
| `qa/state.py:488` | `state/ledger.json` (tmp + `os.replace`) | the contract — the only ledger writer |
| `qa/state.py` `append_event` | `state/journal/events.jsonl` | the contract — the only journal writer |
| `qa/report_plugin.py:402` | `state/runs/<run_id>.json` | run records; path resolved at write time |
| `scripts/bounty.py:269, :659` | `state/bounty.json` | vendor snapshot, under `file_lock` |
| `scripts/inventory.py:557` | `state/inventory.json` | section map; **`__main__` only** |
| `scripts/prereg.py:108` | `state/preregistrations/PRE-NNNN` | preregistration |
| `qa/evidence.py:148` | `evidence/sha256/…` | not under `state/` |
| `scripts/render.py:1977`, `scripts/serve.py:179` | `dashboard/index.html` | not under `state/` |
| `scripts/migrate_ledger.py:439` | `state/ledger.seed.json` | one-shot, refuses twice |

So the accurate sentence is: **`qa/state.py` is the only module that writes the
ledger and the journal.** Four other modules write other files under `state/`,
each with a narrow, single-purpose artefact. The guard test
(`tests/meta/test_pipeline_withdraw.py:169`) enforces exactly the accurate
sentence — it greps a 6-line window around each write call for `ledger`,
`events` or `journal`, and its own comment explains that widening it to `state`
would fire on the run recorder and the dashboard writer and "would be relaxed
within a day."

Three enforcement layers, in order of when they act:

1. **Before the write** — `.claude/hooks/protect_state.py`, PreToolUse on
   `Write|Edit|MultiEdit|NotebookEdit|Bash|PowerShell`. Refuses editor writes to
   paths under `state/` and shell redirects / `sed -i` / `rm` / `git checkout`
   aimed there. Reads pass.
2. **At the write** — `write_ledger` refuses a non-monotonic ledger;
   `append_event` validates and hash-chains.
3. **At the next read** — the chain check raises "chain mismatch (payload
   edited?)"; `tests/repo/test_repo_consistency.py` refolds the committed inputs
   and compares.

---

## 5. Key decisions visible in the code

* **The displayed state is composed, not stored** (`fold.py:_display_cell`).
  Removes the field a hand-edit would target. `VERIFIED FIXED` maps PASSING
  beside RAISED, REPLIED *and* FIX_CLAIMED — whether the thing is broken does
  not depend on whether they said anything.
* **The FILING axis is replayed from zero on every fold** (`_apply_events`).
  Consequence, and it is load-bearing: improving the mapping rewrites the past,
  so a better rule is a migration rather than an edit.
* **Attestation is a flag, not a side effect** (`ledger.py:149,210`). `compose`
  appends `run_recorded` only when `attest=True`; `--check` writes nothing and
  therefore attests nothing. The comment names the defect this replaced: every
  fold attesting whatever run it read, filling the journal with attestations of
  runs nothing stood on.
* **Safety is enforced in the transport, not in helpers** (`safety.py`). Four
  layers: client construction banned outside the factories; a request with no
  tier in scope refused outright (no default); the transport checks the running
  test's tier; `probe_only` is a hard floor no `--allow-mutate` can lift.
* **Inconclusive is a first-class verdict** (`measure.py`, `sources.py`). A
  missing field or a drifted source is never a defect. This is what keeps a
  false contradiction from reaching the vendor.
* **One reader per concept.** `qa/channels.py` exists so the CLI, the hook and
  the skills cannot grow three definitions of "unanswered"; `serve.py` imports
  `render()` rather than reimplementing it, because "a second renderer would be
  a second truth".
* **Evidence before claim** (`evidence.py`, `submit.py`). Numbers in an outgoing
  report are injected from the ledger at send time; a finding whose figures no
  admissible run has measured is refused rather than sent stale.
* **`--confirm` on every outbound write** (`submit.py`, `verify.py`, `a2a.py`).
  Composing and sending are separate steps, and the compose step writes the
  journal first, so a POST that times out still leaves the text behind.

---

## 6. The weight of each mechanism

Evidence per row: **spouštěč** = what invokes it; **čtenář** = who reads its
output; **commits** = how many commits touched the file (`git log --name-only`);
**fired** = whether the mechanism has ever occurred in real data
(`scripts/never_fired.py`).

### The headline imbalance

Two counts, because they differ and both were checked: `def test_` functions,
and what `pytest --collect-only -q` actually collects after parametrisation.

| Directory | Functions | Collected | What it tests |
|---|---|---|---|
| `tests/meta` | **219** | **370** | our own pipeline |
| `tests/repo` | 18 | 49 | our own repository |
| `tests/rest` | 28 | 28 | the vendor |
| `tests/mcp` | 8 | 10 | the vendor |
| `tests/discovery` | 4 | 4 | the vendor |
| `tests/reconciliation` | 4 | 8 | the vendor |
| `tests/pinned` | 2 | 4 | the vendor |
| `tests/boundaries` | **0** | **0** | — (empty directory) |
| **total** | **283** | **473** | |

**419 of 473 collected tests (89%) test us. 54 test Cymetica.** By function
count the ratio is 237 of 283 (84%). Either way: the project exists to find
defects in the vendor's platform, and roughly five sixths of its test mass
guards the machinery that records them. Each individual meta test is justified
by an incident — that is not in dispute and the incidents are real. What no
single test can answer is the ratio.

`OVERKILL — tests/meta as a whole (ratio, not any one test).` Evidence: 219
functions / 370 collected, ~7.5k lines, growing every deep pass; the suite they
guard is 46 functions. `tests/meta/test_pipeline_fold.py` alone is 1151 lines,
larger than `qa/fold.py` (739) which it tests.

`PODHODNOCENÉ — the vendor-facing suite.` 46 functions across 5 directories, and
`tests/boundaries/` is an empty directory that has never held a committed file
(`git log --all --diff-filter=A -- 'tests/boundaries/*'` is empty). Tier
distribution over the 283 decorated functions: 273 SAFE, 10 PROBE, 0 MUTATE.
(A raw grep gives 276 SAFE; three of those are non-decorator uses such as the
`TAG` constant at `tests/meta/test_pipeline_recorder.py:43`.)

### Individual mechanisms

| Mechanism | Spouštěč | Čtenář | Commits | Fired | Verdict |
|---|---|---|---|---|---|
| `qa/state.py` | every state change | everything | 17 | constantly | V ROVNOVÁZE |
| `qa/fold.py` | `ledger.py` | the dashboard | 18 | constantly | V ROVNOVÁZE |
| `scripts/render.py` | after every state change | the operator | **44** | constantly | see below |
| `scripts/ledger.py` | every compose | — | 12 | 158 `run_recorded` | V ROVNOVÁZE |
| `scripts/bounty.py` | sweep, channels, `serve --ask` | the bell | 10 | 147 reads | V ROVNOVÁZE |
| `scripts/submit.py` | qa-sweep | the vendor | 8 | 35 filings | V ROVNOVÁZE |
| `scripts/verify.py` | deep-pass step 6 | the vendor | 7 | 75 intents | V ROVNOVÁZE |
| `scripts/withdraw.py` | the operator | the journal | 9 | 9 withdrawals | V ROVNOVÁZE |
| `scripts/prereg.py` | before a verifying run | admissibility | ? | every level-V run | V ROVNOVÁZE |
| `scripts/correspond.py` | operator pastes | `open_threads` hook | ? | 4 sent / 5 replies | V ROVNOVÁZE |
| `scripts/a2a.py` | operator, `--confirm` | the vendor | ? | **never** | see below |
| `scripts/channels.py` | channels skill | the operator | ? | — | PODHODNOCENÉ (no tests) |
| `scripts/inventory.py` | manual | the dashboard | ? | — | V ROVNOVÁZE (but see §8) |
| `scripts/never_fired.py` | deep-pass, qa-sweep | a session | 8 | reports 7 zeros | V ROVNOVÁZE |
| `scripts/open_checks.py` | qa-sweep default | pytest | ? | — | V ROVNOVÁZE |
| `scripts/findings.py` | `ledger.py` | the fold | 9 | every compose | V ROVNOVÁZE |
| `scripts/migrate_ledger.py` | **spent** | — | ? | 3 `migrated` | OVERKILL (dead weight) |
| `protect_state.py` hook | every write tool call | the writer | 1 | UNCERTAIN | V ROVNOVÁZE |
| `open_threads.py` hook | SessionStart | the session | 1 | 5 open threads | V ROVNOVÁZE |
| `deep_pass_handover.py` hook | SessionStart | the session | 1 | this session | V ROVNOVÁZE |
| `deep-pass` skill | operator | everything | ? | 2+ runs | V ROVNOVÁZE |
| `qa-sweep` skill | operator | — | 7 | — | V ROVNOVÁZE |
| `channels` skill | operator | — | 1 | — | UNCERTAIN (new) |
| `check-auditor` agent | deep-pass step 2 | the pass | ? | 5 defects found | PODHODNOCENÉ |
| `finding-triage` agent | deep-pass step 4 | the pass | ? | used ×3 | V ROVNOVÁZE |

**`scripts/render.py` — 1986 lines, 44 commits, by both measures the most
volatile file in the repository.** More churn than `qa/fold.py` and
`qa/state.py` combined (18+17), and it is a presentation layer. Three test files
touch it. `PODHODNOCENÉ v testech, OVERKILL v rozsahu` — a single function
emitting an entire HTML+JS application inline (the JS template runs from
line ~1270 to ~1800).

~~**`scripts/verify.py` — named in no skill.**~~ `UNCONFIRMED (triage)`, and in
fact false: all three agents found `.claude/skills/deep-pass/SKILL.md:224` —
"`verify.py --confirm` sends it" — as step 6's action. It is routine. The
allowlist entry and the 572 lines were right; the conclusion drawn from them
was not.

**`scripts/a2a.py` — built 2026-09-08, and `a2a_intent` / `a2a_outcome` are two
of the seven never-fired symbols.** Refined by triage: the *channel* does carry
messages from our side — `tests/rest/test_qa_agent_channel.py:398` POSTs to
`/api/v1/bounty/a2a/send` on every run of that PROBE check, which is exactly
what `scripts/a2a.py`'s own docstring describes ("the only sender in the
repository was one check posting one fixed sentence"). What has never fired is
the **deliberate, journalled** send path, the one that keeps our question on
disk. It is exercised by `tests/meta/test_pipeline_a2a.py` (4 functions), so it
is not known-broken; it has simply never been used for its purpose. Neither
`a2a.py` nor `channels.py` is in the `.claude/settings.json` allowlist, so every
invocation costs a permission prompt — a plausible reason a session reaches for
something else.

**The MUTATE tier is not dead**, despite zero MUTATE-tier tests: `submit.py:287`
and `verify.py:85` set `CURRENT_TIER` to MUTATE for the two real writes. The
tier machinery gates the outbound path, not a test class.

### A guard that cannot stay green while the console runs

Found by running `pytest tests/meta tests/repo -q` during this audit:
**417 passed, 1 failed.** The failure is
`tests/repo/test_repo_consistency.py::test_committed_ledger_is_what_its_inputs_fold_to`
— "the committed rows fold correctly, but 1 top-level key(s) of the ledger do
not: `['events_head']`".

Nothing in this audit wrote to `state/`. What moved is the journal, and the
numbers say who moved it:

```
committed journal   1427 lines      ledger.events_head.seq = 1427
working journal     1433 lines      6 new vendor_read events
                                    17:34 · 17:49 · 18:04  — 15-minute spacing
127.0.0.1:8787      open            console.cmd runs serve.py --ask 15
```

The console polls the vendor every fifteen minutes and appends `vendor_read`.
`events_head` is pinned into the ledger at compose time. So from the first poll
after any `ledger.py` compose until the next compose, the committed ledger and
the live journal disagree by construction, and rule 12's guard is red.

That is not a bug in either component; both do what they document. It is a
structural consequence of one writer being on a timer and the other being on a
human. Its cost is the one thing this repository is most careful about
elsewhere: a red test that is usually red for an uninteresting reason is a
signal that stops being read. The rest of `tests/repo` and all of `tests/meta`
were green in the same run.

`UNCERTAIN:` whether the deep pass sees this too (it composes a run late, so it
may close the gap before it checks) or whether it has been silently tolerating
the same red.

### Never fired — 7 of 54 (`scripts/never_fired.py --zeros`)

| Symbol | Kind | Exercised by a test? |
|---|---|---|
| `SUPERSEDED` | filing state | yes |
| `supersede` | journal event | yes |
| `a2a_intent` | journal event | yes |
| `a2a_outcome` | journal event | yes |
| `results_not_collected` | run refusal | yes |
| `prereg_commit_mismatch` | run refusal | yes |
| `reopen` | obligation | yes |

All seven are exercised, so none is known-broken. The tool's own closing line is
the honest reading: what is left is a judgement about whether a condition we
have never met is one we should have met by now.

---

## 7. The record of our work

Four layers exist. Two are load-bearing and two are unmanaged.

| Layer | Answers | Cannot answer | Managed? |
|---|---|---|---|
| **Journal** (`state/journal/events.jsonl`, 1429 events) | what the *pipeline* did, in order, hash-chained | anything the operator did outside the pipeline — a Telegram message they sent and did not file leaves no trace | append-only, never pruned |
| **Git log** (332 commits) | what changed in the code and why, in prose | why an approach was abandoned before it was committed | permanent |
| **Memory dir** (21 files + `MEMORY.md`) | how *reasoning* failed — the inference from a stale docstring, the field not read | anything not written down in the moment | **grows only**; `consolidate-memory` skill exists but `UNCERTAIN:` whether it has ever run here |
| **Session transcripts** | how a session actually worked, minute by minute | anything after a `/clear` unless written elsewhere | outside the repo |

**What survives a night.** This was the claim this document got most wrong on
the first pass, and the correction matters: `UNCONFIRMED (triage)` was returned
by all three agents on "nothing survives", and re-checking with
`git log --numstat -- DEEP-PASS.md` confirms they were right.

| Artefact | On disk | In git |
|---|---|---|
| `DEEP-PASS.md` (7.8 kB) | only the newest report | **all four**: `ee6ab58` +137, `c4b34d4` +107/−128, `5982e49` +105/−124, `a424502` +101/−111 (the +13, +26 and +2/−2 commits are same-day amendments, not reports) |
| `audits/checks.json` (91 kB) | **accumulates** — 285 entries, 203 dated 2026-09-07 beside 82 dated 2026-09-08 | full history |
| `audits/deep-pass-progress.json` (23 kB) | one run only, overwritten | full history |

So a weekly retrospective is **not** blocked on a missing archive. Every past
report is recoverable with `git log -p -- DEEP-PASS.md`, and the check-audit
cache genuinely accumulates. What is true is narrower: there is no *directory*
of dated reports, so a reader must know to reach for git history — and nothing
in the repo says so. That is a discoverability gap, not a data loss.

The journal records what the pipeline did during those nights; it does not
record what a pass decided or why. That part stands.

`UNCERTAIN:` how many events in the journal were written by test runs rather
than real work. Tests redirect via `monkeypatch.setenv("QA_STATE_DIR", tmp_path)`
— verified in `tests/meta/test_pipeline_a2a.py`, `test_pipeline_adapters.py`,
`test_pipeline_abort.py` — but this was not checked for every test file, and the
project has a documented history of exactly this leak (98 of 137 events, before
the `attest` flag). Establish it before reading the journal as behaviour.

---

## 8. Where the documentation lies

Each item quotes the prose and the code.

### 8.1 `components.yaml` names a consumer that does not exist

> `components.yaml:5` — "`qa/components.py` — the component registry the dashboard renders"

`ls qa/components.py` → no such file. No module imports `qa.components`
(`grep -rn "qa.components\|from qa import components"` → nothing). The header of
the file called SINGLE SOURCE OF TRUTH names a consumer that has never existed
in this tree. The same header omits `qa/config.py:91`, which does read it.

### 8.2 "the ONLY module that writes state/" is not what the guard enforces

> `CLAUDE.md`, Where things live — "`qa/state.py` the ONLY module that writes `state/`."

Four other modules write under `state/`: `qa/report_plugin.py:402`
(`state/runs/`), `scripts/bounty.py:269` (`state/bounty.json`),
`scripts/inventory.py:557` (`state/inventory.json`), `scripts/prereg.py:108`
(`state/preregistrations/`) — five counting `scripts/migrate_ledger.py:438`
(`state/ledger.seed.json`), which the guard exempts by name at
`tests/meta/test_pipeline_withdraw.py:187`. The guard test
(`tests/meta/test_pipeline_withdraw.py:169`) enforces the narrower and correct
contract — the ledger and the journal — and its own comment explains that
widening it would produce a rule "relaxed within a day". The code is right; the
sentence is wrong, and a session that believes the sentence will read
`bounty.py` as a violation.

### 8.3 `scripts/inventory.py` ignores the seam another module's docstring says it was the last to ignore

> `scripts/bounty.py:35-43` — the module constant built from `REPO_ROOT` was "the one seam the whole project reads state behind and **the only module that ignored it** after `open_checks.py` was fixed", and a test that set `QA_STATE_DIR` "wrote its two-row fixture over the real snapshot".

> `scripts/inventory.py:35` — `OUT = REPO_ROOT / "state" / "inventory.json"`

Same shape, still present — and triage found a second counterexample to the
"only module" claim, `scripts/submit.py:45`, read-only today. The exposure is
narrower than bounty's was: the write at `:557` sits under
`if __name__ == "__main__":`, and the tests that touch this module import
`build`/`compare` rather than running it, so nothing hits it today.
`state/inventory.before-fix.json` sits in the tree as a survivor of a related
incident. Latent, not active.

### 8.4 The row count is stale in three places

Ledger today: **41 rows** — 31 VERIFIED FIXED, 9 WITHDRAWN, 1 STILL
REPRODUCIBLE.

> `scripts/open_checks.py:3` — "A full sweep re-adjudicates all 31 rows and takes 82 seconds"
> `.claude/skills/qa-sweep/SKILL.md:3` — "re-verify all 31 rows"
> `.claude/skills/qa-sweep/SKILL.md:45` — "31 rows being current"
> `.claude/skills/qa-sweep/SKILL.md:28` — "the 29 settled rows"

31 is now the count of *verified* rows, not of rows — which is very likely how
the number survived: it still appears on the dashboard, against a different
label. Settled rows are 40, not 29. `UNCERTAIN:` the 82 seconds was not
re-measured.

### 8.5 CLAUDE.md's never-fired count is two behind

> `CLAUDE.md`, `scripts/never_fired.py` — "The **five** standing on 2026-09-08 are all exercised"

`python scripts/never_fired.py --zeros` → `NEVER FIRED -- 7 of 54`. The
SessionStart handover printed by `deep_pass_handover.py` says 7 as well, so the
two auto-loaded sources of this number disagree with each other in the same
session's context.

### 8.6 A skill named in git history no longer exists

`.claude/skills/night-shift/SKILL.md` appears once in `git log --name-only`;
the directory today holds `channels`, `deep-pass`, `qa-sweep`. This is the
documented rename ("Named for what it does, not for the night"), not a lie —
recorded here only so the next reader does not chase it.

### 8.7 `state/thread.json` is dead and says so

CLAUDE.md and `qa/messages.py` both state it: a projection from 2026-09-04 that
nothing reads, kept because the hook protects the path. It has 5 commits. Not a
contradiction — an accurate label on dead weight, noted because section 6 would
otherwise flag it.

---

## Verification of this document

The `OVERKILL` / `PODHODNOCENÉ` verdicts in section 6 and every claim in
section 8 were put to three independent `finding-triage` agents, each given the
full list separately with no shared context, each asked to reproduce the claim
from the source. This replaces the operator's review: they do not read this
file, so the check is the machine's.

Result — 12 claims, 3 agents:

| Claim | A | B | C | Outcome |
|---|---|---|---|---|
| `components.yaml` names a missing consumer (§8.1) | T | T | T | confirmed |
| "only module that writes state/" (§8.2) | T | T | T | confirmed; two agents added that the list of four is not exhaustive — `scripts/migrate_ledger.py:438` writes `state/ledger.seed.json` too |
| `inventory.py` ignores the seam (§8.3) | T | T | T | confirmed; one agent found a second counterexample, `scripts/submit.py:45` |
| row count stale in three places (§8.4) | T | T | T | confirmed |
| never-fired count stale (§8.5) | T | T | T | confirmed |
| 84% of tests test us (§6) | P | P | P | **corrected** — the figures were `def test_` counts, not collected tests; both are now given, ratio 89% collected |
| `render.py` most-churned file (§6) | T | T | T | confirmed |
| `verify.py` invoked by no skill (§6) | F | F | F | **removed** — deep-pass step 6 invokes it |
| a2a never fired (§6) | T | T | P | confirmed, **refined** — a PROBE check posts to the endpoint every run; the journalled path is what never fired |
| MUTATE tier not dead (§6) | P | T | T | confirmed; tier counts corrected from 276 to 273 SAFE |
| nothing survives a night (§7) | F | P | P | **rewritten** — every past report is in git history |
| the fold does not read chat channels (§2) | T | T | T | confirmed |

Three claims out of twelve did not survive contact with the source. All three
had the same shape: a number or an absence read off one command, and a
conclusion drawn from it that a second command would have refuted.
