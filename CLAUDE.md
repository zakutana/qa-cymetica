# Operating rules for qa-cymetica

Read this before touching anything in `state/`.

On 2026-09-05 an audit classified every finding-state change an operator had
watched. **71 of 109 were self-inflicted** — produced by our own code
re-deriving state, not by the platform changing. The rules below are what
replaced that, and each one has a test that names the incident it prevents.
A red test here is the system working. Do not fix it by relaxing the rule.

## The rule, said once

> A row in the ledger changes **only** when `ledger.py --run <id>` composes an
> *admissible* run record (CHECK axis), or when an event with an id is
> appended to the journal (FILING axis). Every change writes a transition
> naming its cause. There is no field a state can be written into by hand, and
> the loader refuses a file that contains one.

`tests/meta/test_pipeline_fold.py::test_no_state_change_without_run_id_or_event_id`
is that sentence, executable, over 200 random sequences.

## The two axes

| Axis | Moved only by | States |
|---|---|---|
| CHECK | an admissible run that adjudicated **every** check the row declares | UNVERIFIED · REPRODUCING · PASSING · PASSING_UNPINNED · CHECK_CHANGED · INCONCLUSIVE · UNVERIFIABLE |
| FILING | a journal event | NOT_RAISED · RAISED · REPLIED · FIX_CLAIMED · WITHDRAWN · SUPERSEDED |

The displayed state is the **composition** of the two, computed at render
time. It is never stored, so it cannot be assigned. `VERIFIED FIXED` occupies
exactly one cell: our check passing under the fingerprint it last failed
under, beside their claim of a fix.

## Run admissibility

| Level | Requires | May |
|---|---|---|
| **R** | schema 2 with `collected`; fingerprint did not drift; `exit_status` agrees with the results; every result was collected | open a defect |
| **V** | R **+** clean tree **+** a `prereg` tag whose commit is HEAD | additionally verify a fix |

Make one with:

```bash
python scripts/prereg.py new --selector tests --window 30 --tag
```

then `pytest tests --prereg PRE-NNNN`, then `python scripts/ledger.py --run <run_id>`.

## The twelve rules

1. **Never merge a partial run as verification.** A partial run may open
   `REPRODUCING`; the fold never closes what it did not run.
2. **Never "the latest file".** Use `ledger.py --run <id>`. Without `--run` it
   takes the newest *admissible* run and, if there is none, prints what is
   wrong with each candidate instead of guessing.
3. **Never set a state by hand.** There is nowhere to write one. If the state
   looks wrong, fix the run or the event, not the state.
4. **Never edit `state/*.json` or `events.jsonl`.** Corrections are events via
   `scripts/withdraw.py`, always with a reason.
5. **Never change a check definition and compose a verifying run in one
   commit.** Change → commit → tag → run. A changed check reads
   `CHECK_CHANGED` and wants a justified `rebind-check` or `pin-fingerprint`.
6. **Verification = clean tree + tagged preregistration + full selector.**
   Anything else is exploratory evidence and moves nothing.
7. **Their "fixed" is a claim.** It moves the FILING axis only, and opens a
   re-verify obligation. Only a level-V run under the pinned fingerprint
   clears it.
8. **A failed read is not an empty read.** The fold refuses to move a filing
   state on a non-ok read and marks the row stale.
9. **A submission is two events.** Intent before the POST, outcome after.
   `accepted` needs 2xx **and** a server report id. Unclear is `unknown` and
   is settled with `--reconcile`, never by editing.
10. **Inconclusive is never a defect.** An empty measurement is not filed. A
    check that stops reading its source is retired by an *event*, and on a
    filed row it opens a `repair_check` obligation.
11. **A withdrawal prints its debts.** The row shows "retraction owed on #N"
    until a `retraction-sent` event clears it.
12. **A test enforces this, not memory.** `tests/repo/test_repo_consistency.py`
    checks that the committed ledger is what its inputs fold to and that the
    committed dashboard is a render of it.

## After any change to state

Standing instruction from the operator: **republish the dashboard every time
anything changes.**

```bash
python scripts/ledger.py --run <run_id> && python scripts/render.py
```

then publish `dashboard/index.html` to the existing artifact URL
(`https://claude.ai/code/artifact/cc437012-e1dd-4df0-9b2e-25c9fd4bf3da`) —
the same URL every time, so the operator's bookmark keeps working. Commit the
ledger, the journal and the dashboard together; rule 12's test fails if the
page and the ledger disagree.

## Where things live

```
qa/state.py       the ONLY module that writes state/. Admissibility, the
                  ledger contract, the append-only hash-chained journal.
qa/fold.py        pure: ledger = f(previous rows, one run, the journal)
qa/measure.py     Measurement + conclude(): a check's verdict and pytest's
                  outcome are one value
scripts/ledger.py CLI over the fold
scripts/withdraw.py  the only human writer — every command is one event
scripts/prereg.py    freeze and tag a run's configuration
scripts/migrate_ledger.py  one-shot, already run; refuses to run twice
tests/meta/       self-tests. Run FIRST and abort the session on failure, so
                  a broken guard stops every live request.
tests/repo/       repository consistency. Deliberately NOT in tests/meta:
                  a stale ledger must not abort the run that would fix it.
```

## Reading the numbers honestly

Day one after the migration showed **23 findings and zero verified**. That was
correct. Nothing counts as verified until an admissible run says so, and none
of the 13 pre-hardening run records is admissible — each names its own reason.
A zero here is not a regression to be fixed; it is the difference between
"we checked" and "they said".

## File writes on this workspace

The bash sandbox is Linux, the workspace is Windows. Writing UTF-8 through
bash heredocs silently corrupts files (truncation, embedded null bytes). Use
the Write and Edit tools for file content; bash is fine for running things.
