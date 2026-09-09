# Upgrade plan — balance, three rhythms, the red guard, model/effort

> **Provedeno 2026-09-09.** All twelve steps, from `ee1c5e5` onward, on `main`,
> not pushed. `pytest tests/meta tests/repo` was green after every step and is
> 458 passed / 1 skipped now; 513 collected across the whole suite.
> `/code-review` at high over the branch returned five findings, all fixed in
> `83724f0` -- the first of them serious and in this plan's own step 10: the
> decision guard promised a hash it never compared, so rewording an operator's
> decision passed green.
>
> **Three numbers this plan predicted wrongly**, recorded here rather than
> quietly left standing. The evidence store's composition: the test suite
> writes about 94% of it, not the console (corrected in Context, on the
> operator's challenge). "Test functions about even": they grew by 40 collected
> items, and the self-test ratio went 419/473 to 459/513, 88.6% to 89.5% -- the
> wrong direction. "About -870 lines, +160": actually -1059 and +1584 across
> `scripts qa tests .claude .githooks CLAUDE.md`, a net **+525**. The deletions
> landed as planned (447 + 178 + 105 + 87 for the migration script, its test,
> `qa/messages.py` and render's dead code); the additions were three times the
> estimate, nearly all of it the guards this plan itself required -- the
> boundary pin, the loop's promises, `drift`'s cases and the trailer test.
> That is the imbalance the brief was about, and the answer to it is not a
> better estimate: it is `meta_tests` in the progress file, which makes the
> growth report itself every night.
>
> The five things this plan left open were decided on 2026-09-09 and are
> at the end, under Rozhodnuto.

Written 2026-09-09 from ARCHITECTURE.md (commit `702a65c`), CLAUDE.md, DEEP-PASS.md and
the source. UNCONFIRMED / UNCERTAIN claims in ARCHITECTURE.md were not used; three of
them were resolved from the source and are recorded below. The draft was put to one
adversarial Plan agent (68 tool uses over the source); its 18 breakages are folded in
and the items it refuted are marked "dropped". **Chosen: V1 "Nůžky"** — the operator,
2026-09-09, one word, from the three Czech summaries in the chat. This file is saved
as `docs/UPGRADE-PLAN.md` and committed alone before anything is implemented (step 0).
Not pushed.

## Context

The system is five days old, 333 commits, and every mechanism in it was justified by
an incident. What nothing in it answers is proportion: 419 of 473 collected tests
guard our own machinery, `scripts/render.py` is the most rewritten file and is a
presentation layer, `scripts/migrate_ledger.py` is spent, and rule 12's guard is red
by construction whenever the console has polled since the last compose. The night
pass only adds. There is no weekly look back, and nothing records which effort did
what.

Goal (the operator's): a system that stays balanced as it grows and improves from its
own work. Day = work under guards; night = prune and consolidate; week = look back.
Nothing may be added without something being removed.

### Facts established from the source (not from ARCHITECTURE.md)

* **The red guard.** `tests/repo/test_repo_consistency.py::test_committed_ledger_is_what_its_inputs_fold_to`
  refolds the committed ledger's run over the **working** journal (`scripts/ledger.py:compose`
  → `qa.state.read_events`) and compares every top-level key (`:124-137`), including
  `events_head`, which `scripts/ledger.py:216` stamps from `qa.state.head()` = `{seq, chain}`.
  `serve.py --ask 15` appends **two** `vendor_read` events per tick (`bounty.py:469`
  my-reports, `:340` a2a-inbox), unconditionally by design (`bounty.py:486-494`, rule 8).
  The fold reads `vendor_read` only to set or clear `stale_from` (`qa/fold.py:410-429`);
  it never moves a filing state on it. Fold-inert types: `telegram_*`, `a2a_*`, `note`,
  `run_recorded`, `message`. After any of those the refolded rows and counts are
  byte-identical and only `events_head` differs. Committed head: seq 1427; working head
  at the time of writing: 1441, all `vendor_read klass=ok`. Only the ledger guard is
  red; the dashboard guard is green. `qa/state.py:472-478` (`write_ledger` refuses a
  ledger whose head is not the journal's head **at write time**) is a different, correct
  invariant and stays. `ledger.py --check` composes `run_id=None` today — the newest
  admissible run, the self-poisoning the test's own comment at `:103-111` describes.
* **The deep pass has been tolerating this red** inside its step-6 prereg run, which
  runs `tests/repo` before composing (`SKILL.md:214-220`). Resolves ARCHITECTURE §6's
  UNCERTAIN.
* **`consolidate-memory` has never run here** (no Skill call in any transcript; one
  attempt typed into PowerShell). Resolves §7's UNCERTAIN. The memory dir has 22 files,
  append-only. Its delete half cannot run unattended (`rm` is not allowlisted); retiring
  a memory = dropping its `MEMORY.md` line and leaving the file.
* **tests/meta has three genuine near-duplicates** (agent inventory over 21 files):
  `tamper::test_a_single_test_run_closes_nothing` ≈ `fold::test_partial_run_cannot_close_anything`;
  `tamper::test_a_state_change_without_a_cause_is_refused` ⊂ `schema::test_load_rejects_transitions_without_a_cause`;
  `fold.py:700 test_failed_read_marks_stale_and_does_not_move_filing` overlaps
  `fold.py:755` **but is not a subset** — `:713` asserts FILING stays `FIX_CLAIMED` across
  a failed read, which `:755` never exercises (its row stays NOT_RAISED). Constraints:
  every meta test aborts the session (`tests/conftest.py:120-131`);
  `test_pipeline_abort.py:143-152` pins meta file names to `test_pipeline_*.py`;
  `tests/meta/test_pipeline_never_fired.py:220-230` requires
  `guards_for("supersede")[0]` to be a test named `test_supersede*` (file order matters);
  `test_pipeline_fold.py` is a fixture library imported by 8 files.
* **Dropped from the draft**: widening `fold::test_axes_are_independent` to the event
  vocabulary. `pin_fingerprint` writes `check.pinned_fingerprint` and `rebind_check`/
  `retire_check` rewrite `checks` (`qa/fold.py:344-356`), a non-ok `vendor_read` writes
  `filing.stale_from`, and five types move FILING — the widened test is a ~23-row
  expectation table, larger than the two tests it would delete, and naming `supersede`
  in it breaks the never-fired name pin above. The two "subsumed" tests also assert
  more than axis independence (`fold.py:958-960`, `correspond.py:148-152`). Both stay.
* **`scripts/render.py`**: 10 Python functions, 3 dead (`_message_bodies` :138-168 — the
  **only importer of `qa/messages.py`**, 105 lines, which goes with it; `_excerpt_for`
  :230-266; `latest_run` :276-286). The stale-head refusal at :354-359 is bypassed by
  every real caller: `serve.py:151`, `test_repo_consistency.py:182`,
  `test_live_server.py:274`, `test_pipeline_render.py:638-639` all pass
  `allow_stale_head=True`; only the CLI refuses. Churn was 2/3 presentation during
  09-05/09-06 and has stopped (+14/−2 on 09-08). **Dropped**: replacing the
  `display_counts` recompute with `ledger["counts"]` — the render tests' `_ledger()`
  fixture (`test_pipeline_render.py:73-80`) carries no `counts`, and the three lines
  hold the one-bucket assertion the file's docstring names as its rule 2.
* **Migration leftovers** beyond the script: `compose(seed=)` / `--seed` in
  `scripts/ledger.py` (:149-155, :172, :240-249) had one caller, the migration test;
  three nodeids of that test sit in `audits/checks.json:1229-1245`;
  `test_repo_consistency.py:96` names the script in a message; `state/ledger.seed.json`
  (36 KB) is git-tracked, under `state/`, and the hook refuses `git rm` there
  (`protect_state.py:73`) — a session cannot remove it. `tests/meta/fixtures/ledger/*`
  are **not** orphaned (read by `test_pipeline_schema.py:23`, `test_pipeline_checks.py:39`,
  `test_pipeline_admissibility.py:22`).
* **Model/effort**: a session sees its model in its system prompt and `CLAUDE_EFFORT` in
  the environment of every Bash command and hook (verified: `CLAUDE_EFFORT=max` here).
  Skill frontmatter honours `model:`/`effort:` for the skill's turn (`qa-sweep: medium`,
  `channels: low`, `deep-pass: opus xhigh`); agents are `opus high`. Commit trailers name
  the model on 255 of 333 commits (`Co-Authored-By: Claude Opus 5` ×251, Fable ×3,
  Sonnet ×1); the other 78 are unattributed and stay so. `git config` is not
  allowlisted; `core.hooksPath` is unset.
* **Operator decisions** (dated, quoted or paraphrased): CLAUDE.md:33, :36-37, :48,
  :133-136, :157, :276, :353; `qa-sweep/SKILL.md:26-27`, `:118-119` (the standing "file without
  asking" instruction — undated in the text, 2026-09-06 by `git blame`), `:172-173`; `channels/SKILL.md:9-11`, `:61`; `deep-pass/SKILL.md:17-19`
  ("Their reason"), `:192-196` ("Their reply"). CLAUDE.md:184 ("that one is the
  operator's") delegates a judgement rather than recording a decision and stays
  untagged, with that reason in the test. `deep-pass/SKILL.md:159-164` records the
  skill **departing** from an operator instruction (the minority report vs "discard
  everything below two votes") — under the new boundary that needs the operator's
  word, one way or the other; decided 2026-09-09, see Rozhodnuto at the end.
* **A fourth imbalance the brief did not list**: `evidence/` — 5 346 files, 196 MB,
  +729 files / +52 MB on 09-08 alone. Measured by writer, and the first answer was
  wrong: the console is **not** the main writer. ~5 000 files (~170 MB) are written by
  the **test suite** — every check stores the whole request and response of every call
  it makes, on every run, and a sweep runs every check
  (`tests/pinned/test_documented_404.py` alone: 1 927 files;
  `tests/rest/test_bounty_pipeline.py`: 36 MB). Content addressing does not dedupe them
  because the vendor's bodies carry changing timestamps and ids. Scripts, the console
  among them, wrote 321 files / 28 MB. Only 279 of the 5 346 are cited by the journal at
  all; the rest are cited by run records. Second store, on disk: `state/runs/` — 645
  records, 57 MB, of which 305 are tracked (`scripts/ledger.py::_track_run_record`
  force-adds the one a fold stands on; the rest are gitignored and never pruned). Not
  acted on here (retention is a decision); named for the operator.

## The three variants

Each states what it adds, what it removes, which of the twelve rules it touches, and
what it costs. None changes a vendor check definition (nothing under `tests/rest`,
`tests/mcp`, `tests/discovery`, `tests/reconciliation`, `tests/pinned` is touched, and
the ledger cites zero `tests/meta` checks), so no `CHECK_CHANGED`, no rebind, and none
needs a `state/` migration.

### V1 "Nůžky" — prune first, minimal machinery (RECOMMENDED)

**Adds**
* one function in `scripts/ledger.py` (`drift()`) that both `--check` and the repo
  guard call — one definition of "is the committed ledger what its inputs fold to";
* one meta test file `tests/meta/test_pipeline_decisions.py` (~80 lines) pinning the
  operator's decisions by hash, with its own negative control;
* three keys in `audits/deep-pass-progress.json` (`retrospective`, `rule_changes`,
  `meta_tests`) and three assertions in `tests/repo/test_deep_pass_finished.py`;
* two headings the handover hook prints (`Týden`, `Změněná pravidla`);
* skill text: the prune half, the rule-change procedure, the weekly step;
* a six-row table and one sentence in CLAUDE.md for model/effort;
* optionally, after a verification step, a versioned git hook adding an `Effort:`
  commit trailer.

**Removes** (≈ −870 lines, +≈160; test functions about even, one subprocess test fewer)
* `scripts/migrate_ledger.py` (447) and `tests/meta/test_pipeline_migration.py` (178,
  one subprocess per run), the `seed`/`--seed` path in `ledger.py`, the three stale
  `checks.json` entries, and the by-name exemption that made the state-writer guard
  weaker than its message;
* `tests/boundaries/` (empty, untracked);
* `qa/messages.py` (105) and the three dead functions in `render.py` (~79), the
  `allow_stale_head` parameter (four call sites) and the CLI-only refusal;
* three meta tests (the duplicates), one meta test replaced 1:1 (the refusal test);
* the stale rationale at `render.py:294-301` and `test_repo_consistency.py:176-182`
  (both cite a per-session `run_recorded` append that stopped when `attest` became
  default-off).

**Rules touched**: 12 (the guard's comparison changes — see step 1; the invariant "the
committed ledger is what its inputs fold to" is kept exactly; what goes is the
incidental claim "the ledger cites the newest head", which no reader consumes and
which `write_ledger` proves at write time), 4 (the writer guard gets stricter), 8
(untouched — `vendor_read` stays as it is). No other.

**Costs / what is lost**: the page may stand on a head older than the journal; the
guard, not the page, says whether that matters. The one genuine relaxation: a ledger
whose `events_head` was hand-rolled to an **older valid** `(seq, chain)` passes the
anchor (today's guard would be red) — it then over-reports "events since head" and
nothing else, because rows are still compared against the whole journal; stated in the
test docstring. The night loop's pruning is judgement bounded by text and by the
`meta_tests` assertion, not by a ratio guard. The weekly retrospective's quality is the
model's. The ratio (89 %) barely moves — it is bounded by rule 10 (vendor tests only
for what is visible) and by incidents; V1 acts on **growth** and prints the ratio weekly.

### V2 "Váhy" — V1 plus fixing the noise at its source and thinning the renderer

Everything in V1, plus:
* `bounty.py` writes `vendor_read` only when the read's `klass` changes per source.
  Rule 8 still holds — a failure after ok is written, the ok after it is written, ok
  after ok is not — but the fold's output is **not** identical for every history:
  `stale_from` is overwritten per event (`qa/fold.py:426-428`), so with two consecutive
  failures today marks the *latest*, change-only marks the *first*. Arguably better
  ("stale since we lost them"); it must be pinned in `fold.py:755` with a two-failure
  case **before** `bounty.py` changes. `bounty.py:486-494` argues the opposite ("that a
  read happened … is the fact rule 8 rests on"); the reply is that rule 8 rests on the
  failure and the clearing read being recorded, and both still are. What is lost: "when
  did we last look" leaves the journal (`bounty.json` keeps only the latest `read_at`).
  Adapter tests `test_pipeline_adapters.py:104-107` and `:786-799` still pass but their
  docstrings ("the read itself is still recorded") become false — rewrite them and add
  an ok→ok case asserting one event. CLAUDE.md:248-249 ("one vendor_read per run")
  changes. Cuts ~96 journal events and ~96 evidence files (~17 MB) per console day —
  evidence capture must move **after** the decision to write (`bounty.py:325, :449`
  capture before classification, and `test_pipeline_adapters.py:250-263` requires
  every emitted event to carry `evidence_id`), never write-then-delete.
* `TEMPLATE` (1 366 lines) moves to `dashboard/template.html`, read at import and kept
  as the module attribute `render.TEMPLATE` (eight tests read it); `dashboard/` is
  already watched by `serve.py`, so no `WATCHED` change. `render.py` drops to ~600
  Python lines. Optional: `_api_conversation` (a second journal fold, :59-135) moves
  beside `qa/channels.py:pairs()`.

**Removes additionally**: the poll noise from the journal and the evidence store; 1 366
lines of markup from a Python file; optionally a duplicate journal reader.
**Rules touched additionally**: 8 (the journal's future shape and the stale-mark
timestamp). Needs `/code-review` and the rule-change procedure because `bounty.py` and
the fold's reading of `vendor_read` are load-bearing. Costs a day; the console must be
restarted (a running process holds the code it started with).

### V3 "Přestavba" — restructure

V2 plus: move non-safety meta files (`handover`, `correspond`, `a2a`, `channels`,
`render`, `never_fired`) from `tests/meta` to `tests/repo` so that only safety guards
abort a session; extract the fold fixture library to a shared module; a `scripts/retro.py`
that computes the weekly numbers.

**Removes additionally**: session-abort semantics from ~40 tests that never guarded a
live request; the fixture coupling between 9 files.
**Why not**: relocation also removes those tests from every **sweep** —
`scripts/open_checks.py:49` prepends `tests/meta` only and excludes `tests/repo` on
purpose — so they would run only in full-suite runs; the downgrade is invisible in a
diff; `test_pipeline_abort.py:143-152` and the byte-pinned `conftest.py` must change
with it. Fixture extraction touches seven files for zero behaviour. `retro.py` is four
one-liners plus, by this repo's rule, a test file — it grows the thing it measures, the
operator's own warning about a ritual that produces five proposals a week. Overkill
for a five-day-old project whose platform changes weekly.

## Recommendation: V1, with V2's `vendor_read` change offered as the next decision

V1 removes far more than it adds, touches the contract in exactly one place (the
guard's comparison, made explicit and anchored), and leaves every vendor-facing check
untouched. The evidence-store growth is the one thing V1 does not fix; it is a
retention decision and goes to the operator as a question, not a step.

---

## Migration path (V1) — one commit per step, suite green after each

Conventions:

* **Baseline is not green.** At HEAD, `pytest tests/meta tests/repo` fails exactly one
  test — the guard step 1 repairs — because the console has polled (14 events past the
  cited head at the time of writing). Step 1 is first for that reason: the pre-step-1
  baseline is red on exactly the test step 1 repairs, and from step 1 on the guard is
  green regardless of the console.
* **Every step's verification is** `python -m pytest tests/meta tests/repo -q` and
  `python scripts/ledger.py --run run-20260908T150954Z-95f0a70 && python scripts/render.py`.
  The compose re-stamps `events_head` (attestation is idempotent by run id —
  `qa/state.py:581-582` — so no new `run_recorded`) and the render rewrites the page;
  each commit therefore includes `state/ledger.json`, `state/journal/events.jsonl`,
  `state/bounty.json`, `dashboard/index.html` and whatever evidence the console captured
  meanwhile — rule 12, "commit the ledger, the journal and the dashboard together".
* **Test before code.** Where a step is a deletion or prose, that is impossible; each
  such step says what stands in for it.
* `python scripts/never_fired.py --zeros` after every step that deletes a test: it
  credits guards by substring over test source, so no zero may lose its sole guard.
* **Commit to `main`, do not push.** The only pusher is the deep pass.
* Every meta test touched changes its fingerprint, so the next deep pass will re-audit
  all of them (`audits/checks.json`). Expected; say so in that pass's handover.
* Attribution: `Co-Authored-By: Claude Fable 5.1 <noreply@anthropic.com>`.
* Propose `/code-review` after steps 1 and 3 (the guard, the writer guard); nowhere
  else.

### Step 0 — save this plan
`docs/UPGRADE-PLAN.md` (this file), committed alone. Test: none (prose).

### Step 1 — C: the guard compares by effect and anchors the head
*Test first*, in `tests/meta/test_pipeline_tamper.py` (the negative-control file over
the committed inputs; no new meta file), over a temp `QA_STATE_DIR` with a small ledger
written through `write_ledger`:
1. an appended fold-inert event (`note`) → `drift()` reports `anchored=True`,
   `since_head={"note": 1}`, no row or key drift → verdict passed;
2. an appended `withdraw` (moves a row) → row drift → failed, and the reason names the
   type pending since the head;
3. a ledger citing a chain the journal does not have at that seq → `anchored=False` → failed;
4. `seq` greater than the journal's length → failed.
All red before the function exists (`AttributeError: drift`).

*Code*: `scripts/ledger.py::drift(committed, refolded, events) -> dict` with keys
`rows` (drifted ids), `keys` (drifted top-level keys **except** `events_head`),
`anchored`, `since_head` (Counter by type), `reason`. Anchor: `seq == 0 and chain == ""`,
or `1 <= seq <= len(events) and events[seq-1]["chain"] == chain`. The refold runs over
the whole working journal, so "none moved a row" is proven by row and count equality,
never by a type list. `main(--check)` composes `committed["run_id"]` (not `None`) and
calls `drift()`; `test_repo_consistency.py::test_committed_ledger_is_what_its_inputs_fold_to`
calls the same function, and routes `RunIntegrityError` (a clone without prereg tags —
today it escapes the `SystemExit` catch at `:113` and errors the guard) to
`inconclusive`. Docstring and the comment at `:130-133` name the decision reversed: the
2026-09-07 widening conflated "behind the journal" with "not what the inputs fold to";
the anchor keeps the first as a verified citation, the equality keeps the second
exactly, and the one relaxation (an older valid head passes) is written there.
`write_ledger`'s chain check is untouched.

*Scenarios* (none weaker): hand-edited row with a valid head → rows differ → red;
journal rewritten or truncated below the head → anchor fails → red; ledger composed
from a different journal → chain differs → red; a fold-relevant event after the head
(any FILING mover, a check-definition event, `retraction_sent`, `verification_outcome`,
a non-ok `vendor_read`) → a compared key differs → red; only inert events after the
head → green with the count — the intended change.

*Verify*: suite green with the console running; `python scripts/ledger.py --check`
prints "anchored at seq N of M; K events since (…), none moved a row".

### Step 2 — C: the page names its head instead of refusing
*Test first*, `tests/meta/test_pipeline_render.py`: replace
`test_render_refuses_stale_ledger_head` with
`test_the_page_says_which_journal_head_it_stands_on` — `re.search(r"\bD\.events_head\b", TEMPLATE)`
and the payload's head equals the ledger's; render with the journal ahead of the ledger
and assert `build_payload` does **not** raise. Red until the code changes.

*Code*: delete the refusal at `render.py:354-359`, the parameter and every
`allow_stale_head=True` (`render.py:291`, `serve.py:151`, `test_repo_consistency.py:182`,
`test_live_server.py:274`, `test_pipeline_render.py:638-639`), the docstring at
`render.py:294-301` and the "rule 3" sentence at `test_pipeline_render.py:19-21`; the
masthead (`render.py:1313-1320`, which reads `D.run_id`) gains "state as of journal
event #N" from `D.events_head.seq` — outside the legend slices, so the vocabulary test
is untouched. The journal's **current** head and "events since" are **not** put in the
payload: it is hashed, and a poll-dependent field would turn guard (b) red on every
tick and make `serve.py` rewrite the page every 15 minutes. Rewrite the comment at
`test_repo_consistency.py:176-182`. TEMPLATE changed → re-render → commit the page.
Restart the console after this step (`serve.py` itself changed).

### Step 3 — A: retire the migration script, and tighten the guard that exempted it
*Test first*: remove `"scripts/migrate_ledger.py"` from the exemption at
`tests/meta/test_pipeline_withdraw.py:187`; `test_only_state_module_writes_state_files`
goes red at `migrate_ledger.py:439` (the `ledger.seed.json` write sits in a 6-line
window containing "ledger"). That red is demonstrated, not committed.

*Code, same commit*: `git rm scripts/migrate_ledger.py tests/meta/test_pipeline_migration.py`;
delete `seed`/`--seed` from `scripts/ledger.py`; drop the three nodeids from
`audits/checks.json`; reword the inconclusive reason at `test_repo_consistency.py:95-96`;
CLAUDE.md "Where things live" entry becomes one line — migration done 2026-09-05,
script removed 2026-09-09, the three `migrated` events and `state/ledger.seed.json`
are the record. `rmdir tests/boundaries` on disk — untracked, so no commit can carry
it; the commit message records it. `state/ledger.seed.json` stays: the hook refuses a
session's `git rm` under `state/`, so its removal is the operator's (listed below).

### Step 4 — A: render.py loses its dead code, and the module only it imported
*Test first*: impossible (deletion); stand-in:
`grep -rn "_message_bodies\|_excerpt_for\|latest_run\|qa.messages\|from qa import messages"`
returns only the definitions and `render.py:148`.
*Code*: delete the three functions, `qa/messages.py`, and the CLAUDE.md line at
:296-297 that describes it as live. TEMPLATE unchanged.

### Step 5 — A: three duplicate meta tests, three commits
Deletions; stand-in for test-first is the commit message naming the surviving test that
holds the incident, plus `never_fired.py --zeros` after each:
* 5a `tamper::test_a_single_test_run_closes_nothing` → survives as
  `fold::test_partial_run_cannot_close_anything` (same fold call, same assertion; the
  tamper framing is added to the survivor's docstring; rule 1).
* 5b `tamper::test_a_state_change_without_a_cause_is_refused` → survives as
  `schema::test_load_rejects_transitions_without_a_cause` (strict superset; rule 3).
  Its parametrised sibling `test_a_hand_written_key_is_refused` stays.
* 5c **merge, then delete**: add the FIX_CLAIMED-survives-a-failed-read case from
  `fold.py:713` to `fold.py:755` (green at once — a re-homing, said so in the commit),
  then delete `fold.py:700` (rule 8).

### Step 6 — B: the handover prints the two new headings
*Test first*, `tests/meta/test_pipeline_handover.py`: the `REPORT` fixture gains
`## Týden` and `## Změněná pravidla`, each with one list item carrying a bold lead;
assert both leads are printed. `test_the_hook_does_not_paste_the_whole_report` caps
output at 12 lines — raise to 16 and set `PER_SECTION=2` for the two new sections, in
the same test.
*Code*: `.claude/hooks/deep_pass_handover.py` `SECTIONS` gains `("tyden", "week")` and
`("zmenena pravidla", "rule")` (`_plain` already strips diacritics).

### Step 7 — B: the progress file carries the week, the rule changes and the growth
*Test first*, `tests/repo/test_deep_pass_finished.py`, gated on
`progress["at"] >= "2026-09-09"` so the committed file from 09-08 stays green
(inconclusive on the new keys) until the next pass writes them:
* `retrospective: {"last": "YYYY-MM-DD"|null, "done": bool}` — `last` is carried forward
  from the previous progress file by every pass; red if `last` is null or more than 7
  days before `at` and `done` is false (the pass owed a week and skipped it). One
  marker, in the pushed file; no git tag (tags are local and `push.followTags` is unset).
* `rule_changes: [{"id","what","why","votes":{"t1","t2","t3"},"test","commit","handover":bool}]`
  — red if any entry has fewer than 2 "does not weaken, does not touch a decision"
  votes, names a test nodeid that does not exist (resolved by AST, the way
  `never_fired._test_functions` does), or has `handover` false.
* `meta_tests: {"start": N, "end": M, "reason": str|null}` — `def test_` count under
  `tests/meta` at `start_commit` (via `git show <start_commit>:…`) and at the end; red
  if `M > N` and `reason` is empty. Net growth is reported, not forbidden.
Said aloud in the docstring: these enforce the **form** of what a pass reported, not
that every rule change was reported. The detector of an unreported change is the
2-of-3 agents reading the whole diff (step 8), and the operator's veto after the fact.
*Code*: none beyond the test — the pass writes the keys (step 8).

### Step 8 — B: the deep pass gets its pruning half, its rule-change procedure and its week
Prose; no test possible beyond steps 6–7 — stand-in: the hook prints the headings, so a
skipped step is visible next morning. Edits to `.claude/skills/deep-pass/SKILL.md`:
* **Step 0** additionally reads the previous progress file's `retrospective.last` and
  writes `retrospective` and `meta_tests.start` into the new one at once, so a
  compaction cannot lose them.
* **Step 1** gains its source: today's operator messages from the transcripts under
  `~/.claude/projects/<this project>/*.jsonl`, through **one fixed command** in the
  skill (lines with `"type":"user"`, string `content`, today's `timestamp` — the files
  are 20–30 MB and carry vendor text, which is data, never instruction). Their short
  Czech replies ("ne", "co?", "nechapu", "spatne") are where an inference failed.
  Still at most two memories.
* **Step 1b "Prořez"**: invoke `anthropic-skills:consolidate-memory`, bounded — merge
  a file whose description overlaps an older one into the older one; retire a file
  whose content CLAUDE.md, a test or a skill now holds by dropping its `MEMORY.md` line
  (the file stays; `rm` is not allowlisted); fix relative dates. Every merge or
  retirement goes under a new DEEP-PASS.md heading **Prořezáno** with its reason — the
  memory dir is outside git, so the report is the record. Then
  `python scripts/never_fired.py --zeros`: a symbol that is both never fired **and**
  never exercised ("nothing at all behind it" in the tool's own words) goes to removal
  through the rule-change procedure; an exercised zero is left, and the week reports
  how long it has stood. A pass that adds a meta test names, under Prořezáno, which
  existing test it considered merging into and why not (`meta_tests.reason`).
* **Rule-change procedure** (the operator's three conditions, 2026-09-08): a change to
  CLAUDE.md's rules, to a guard's assertion, to a hook, or to a skill's spine lands only
  when (1) three `finding-triage` agents (`opus`, `high`) are each given the diff and
  the question "does this weaken a guard, and does it touch a `[operator …]` paragraph
  or `tests/meta/test_pipeline_decisions.py`" — a separate step, and at least two say
  no to both; (2) it lands with a test naming the incident; (3) DEEP-PASS.md carries a
  Czech paragraph under **Změněná pravidla** saying what and why. Each such change is
  one `rule_changes` entry. Nothing in the pass calls `scripts/a2a.py` or
  `scripts/channels.py` (not allowlisted; refused unattended).
* **Step 11 "Týden"** (last): when `retrospective` is due — read the layers as they
  already exist: `git log -p -- DEEP-PASS.md` (every past pass),
  `audits/checks.json` (what was audited when), `git log --since='7 days ago' --stat --format='%h %s%n%(trailers)'`
  (churn per file; the `Co-Authored-By` trailer for the model; the `Effort:` trailer if
  step 11 lands), the memory dir (count, merged, retired). The transcripts are the
  night step's material, not the week's (too large). Answer three questions in Czech
  under **Týden**: what repeated; what was overkill or under-built, with the one line
  `pytest --collect-only -q` gives (tests of us vs of the vendor); which model and
  effort ran what and whether the CLAUDE.md table still fits. "Nic neměnit" is a valid
  answer and is written as such. Then `retrospective.last = today`, `done = true`. No
  archive: the pointer is this step.
* **The push is the pass's last action.** The skill's step 8 ("Commit and push") moves
  after Týden: DEEP-PASS.md, the progress file and the Týden paragraph are committed
  first, then pushed together. That is what the last pass actually did (`a424502`, the
  report commit, is `origin/main`); the text now says it, so no post-push commit is
  left behind to become the next pass's review scope by accident. The push rule in
  CLAUDE.md is untouched.
* The **first pass after this lands** has no `last`, so the first weekly retrospective
  happens on the next deep pass — the mechanism is exercised at once.
* The **skill's step 6 order** stays (prereg run before compose); with plan step 1 in
  place a red guard inside that run means a fold-relevant event is pending, which the
  `bounty.py` + compose lines of the same step resolve.
DEEP-PASS.md headings become: **Co se stalo · Opraveno · Prořezáno · Minority report ·
Změněná pravidla · Čeká na tebe · Týden · Co mě to naučilo** (Týden only when it ran).

### Step 9 — D: what a task needs, said at the start
Prose; no test (said aloud). CLAUDE.md gains, under "How to work with me":

| Task class | Needs |
|---|---|
| sweep, filing, verification (`qa-sweep`) | Sonnet 5 · high — the operator's table; the skill carries it |
| correspondence written to the vendor (`correspond.py`, `a2a.py send`) | Sonnet 5 · high |
| channel status (`/channels`) | Sonnet 5 · low — a status read; deviates from the table on purpose, see below |
| `qa/state.py`, `qa/fold.py`, `qa/measure.py`, guards, review | Opus 5 · high–xhigh |
| deep pass | Opus 5 · xhigh (the skill carries it) |
| architecture, plans like this one | Fable 5.1 or Opus 5 · max |

and one rule: the first line of any task names its class, what it needs and what the
session runs on (model from the system prompt, effort from `CLAUDE_EFFORT`); if over
or under, it says so in that line and continues — it never blocks on it, and it cannot
switch itself (`/model`, `/effort` are the operator's). Skill frontmatters aligned:
`qa-sweep` → `model: sonnet`, `effort: high` (was `medium`, no model); `channels` →
`model: sonnet`, `effort: low` kept (the operator's table says high for
correspondence; a status read is not correspondence — one word from them changes it);
`deep-pass` unchanged. The week reads whether reports filed by Sonnet sweeps were
later corrected (`correction_owed`, `withdraw`) — that is the evidence for or against
the table, not an opinion. Fix the stale sentences while there: "the ONLY module that
writes `state/`" → "the only module that writes the ledger and the journal" (§8.2), and
"the five standing on 2026-09-08" → the current `--zeros` count.

### Step 10 — BOUNDARY: mark the operator's decisions, and pin them
Placed **after** the prose edits of steps 8–9 on purpose: the hashes pin verbatim
text, and pinning before the CLAUDE.md table lands beside the push-rule bullet would
trip the new guard on the plan's own reflow.
*Test first*, new `tests/meta/test_pipeline_decisions.py` (meta on purpose: a session
that has touched a decision should neither issue live requests nor run an unattended
pass — step 0 of the deep pass stops on red meta):
* a pure parser `decisions(text)` returns every block that starts with
  `[operator YYYY-MM-DD]`, hash unit = the tag line to the next blank line, verbatim;
* the test iterates **its own pinned list** of `(file, date, sha256)` and asserts each
  is present — a deleted paragraph fails; then iterates the tags found in CLAUDE.md and
  `.claude/skills/*/SKILL.md` and asserts each is pinned — an added or altered paragraph
  fails; a hash mismatch fails;
* a tripwire: any italic quote `\*"[^"]{8,}"\*` (multi-line) or
  `(operator|they|their)[^.]{0,60}\d{4}-\d\d-\d\d` outside a tagged block fails as "an
  unmarked decision", with the one deliberate exception (CLAUDE.md:184) listed with its
  reason;
* a negative control: the parser over a copy with one tagged block removed must fail.
Red until the tags exist (pins are computed from the tagged text, so strict test-first
is impossible; the negative control stands in).
*Code*: tag the paragraphs listed under Facts (CLAUDE.md ×7; three SKILL.md files ×7,
the undated `qa-sweep` standing instruction among them, tagged with its blame date
2026-09-06; `deep-pass/SKILL.md:159-164` is not tagged until the operator settles it);
a sentence in CLAUDE.md under "How to work with me": a paragraph tagged
`[operator DATE]` is a decision, not a rule — no session changes it; the night loop
must not touch `tests/meta/test_pipeline_decisions.py`, and the 2-of-3 agents are told
to check the diff for exactly that. The test's own hash is **not** added to
`test_pipeline_abort.py`'s pinned list (seven decisions in five days would mean
re-pinning daily); the morning check is the `Změněná pravidla` heading plus
`git log -p -- tests/meta/test_pipeline_decisions.py`.

### Step 11 — D (optional): an `Effort:` trailer on every commit
*Verify first*: inside a skill turn that carries `effort:` (invoke `/channels`,
`effort: low` — it makes the same two live GETs the console makes every tick, nothing
more), run `echo $CLAUDE_EFFORT`. If it prints the skill's `low`, the variable
reflects the effective effort and the trailer is worth having; if it prints the
session's setting, **drop this step** and say so in the handover.
*Install first* (only if kept): `git config core.hooksPath .githooks` — repo-local and
reversible, not allowlisted, so it prompts once in this attended session — before the
test lands, so the deep pass never meets an unresolvable red and reverts the run.
*Test*, `tests/repo/test_state_guard.py` gains `test_the_effort_trailer_hook_is_installed`:
inconclusive when `core.hooksPath` is unset (not installed on this machine), failed
when it is set and `.githooks/prepare-commit-msg` is missing or not executable. It does
not scan commit history (the operator's own commits would make it red for nothing).
*Code*: `.githooks/prepare-commit-msg` appends `Effort: $CLAUDE_EFFORT` when the
variable is set and the trailer absent.

### Step 12 — the memory this plan owes
If anything in this session misled the operator or built something to throw away, one
memory file, in the moment. Candidate from this session: the draft's "widen the
property test and delete the two it subsumes" — a subset claim made from a summary
before the assertions were read; the adversarial agent refuted it. Write it only if
the pattern is not already held by `read-the-whole-path-before-explaining-it`.

## Verification, end to end

1. Console running (`console.cmd`, `--ask 15`). Wait one tick. `python -m pytest tests/repo -q`
   → green; `python scripts/ledger.py --check` → "anchored … none moved a row".
2. On a temp state dir, append a `withdraw` through `scripts/withdraw.py` → `--check`
   is red and names the type; compose → green.
3. `python -m pytest tests/meta tests/repo -q` → all green; `pytest --collect-only -q | tail -1`
   → about 473 − 3 (migration) − 3 (duplicates) + the new tests (≈ 8) — functions about
   even, lines −700, one subprocess fewer.
4. `python scripts/never_fired.py --zeros` → 7 of 54, every one still exercised.
5. `git rev-list --count HEAD` grows by 12–14 commits, each with the ledger, journal and
   page together.
6. Run `/deep-pass` once with the operator away: expect Prořezáno, a first Týden,
   `retrospective.last` set, `meta_tests` filled, `test_deep_pass_finished` green.
7. Next morning: the SessionStart hook prints Čeká na tebe, Minority report, Změněná
   pravidla and Týden leads.

## Rozhodnuto 2026-09-09 -- taken here, veto open

This was a list of five questions for the operator. They answered four with
questions of their own and the fifth with *"nechtel po me zadna takova
rozhnodnuti, ja vubec tomu systemu jeste nerozumim"*, now a pinned decision in
CLAUDE.md. So they are decided below, each on the fact it rests on, and any of
them reverses on one word.

* **Evidence: stop committing new ones, keep every existing file.** The fact
  that settles it is that **nothing reads the store by machine.**
  `EvidenceStore.load()` has exactly one caller in the repository and it is a
  meta test; `render.py` mentions evidence zero times; the report that goes to
  the vendor carries none; 1 of 41 ledger rows carries an `evidence_id`; 279 of
  5346 files are cited by the journal. `git rm` would also shrink nothing --
  207 MB is in git history and stays there -- so the only live question was the
  future rate, about 700 files and 50 MB a day. Not built here, because it wants
  test-first and a commit of its own. The shape, so the next session does not
  re-derive it: gitignore `evidence/`; a `_track_evidence` beside
  `scripts/ledger.py::_track_run_record`; called where the journal attests an
  event carrying an `evidence_id` (`qa/state.py:763 append_event`, or its
  callers in `submit.py` / `bounty.py`); then `git rm --cached` the uncited.
  Check first which repo test asserts a cited evidence file exists -- that is
  the guard that goes red.
* **The three dead files: remove them.** Confirmed unread -- nothing in `.py`,
  `.md`, `.html`, `.cmd` or `.sh` opens `state/thread.json`,
  `state/ledger.seed.json` or `state/inventory.before-fix.json`. The one hit
  that looked like a reader, `tests/meta/test_pipeline_checks.py:383`, reads
  `tests/meta/fixtures/inventory.before-fix.json`, a separate copy. The hook
  refuses a session's `rm` under `state/`, correctly, so the command runs in the
  operator's own terminal once and nothing here waits on it. CLAUDE.md's
  migration entry was reworded first, so it is true either way.
* **`state/runs/`: keep all of it. The item should not have been on the list.**
  The operator's objection is right, and it is the point of the whole week step:
  history is what a retrospective is computed from. `never_fired.py` parses every
  record to say what has ever fired. The split is already correct -- 305 of 697
  are tracked in git because the ledger stands on them, the other 392 are
  gitignored local debug output that adjudicated nothing and costs local disk
  only.
* **The minority report stands, on evidence rather than on a ruling.** `A3-09`
  had one vote of three on 2026-09-08, was real, and was fixed the next morning
  in `702a65c`. Recorded in `deep-pass/SKILL.md` beside the departure, and
  deliberately not tagged `[operator ...]`: the loop decided it, so the loop can
  be told otherwise.
* **`/channels` stays at low effort.** Reading three channels' status is not
  writing to the vendor, which is what the table's "high" row is about. If a
  report filed off a low-effort read is ever corrected, the week says so --
  `correction_owed`, `withdraw` -- and that is the evidence that would move it.
