---
name: qa-sweep
description: Re-check the open Cymetica findings, take the one action each one's status calls for, and report what changed. Use when the operator says /qa-sweep, "projdi bugy", "udelej sweep", or asks for the current state of the QA work. Say "full sweep" / "cely sweep" to re-verify all 31 rows instead.
effort: medium
---

# QA sweep

One command, one pass over what is open, one short report at the end.

The operator's complaint that produced this: the work felt chaotic — each
session picked up whatever was in front of it. A sweep is the same sequence
every time, so what changed between two sweeps is a fact rather than an
impression.

Work in the repository root. The skill used to say `../qa-cymetica`, from
when it lived in a sibling project that has since been deleted.

## Two widths, and which one you were asked for

| The operator said | Selector | Cost |
|---|---|---|
| "sweep", "projdi bugy", `/qa-sweep` | **open rows only**, plus `tests/meta` | ~25s |
| "full sweep", "cely sweep", "over vsechno" | the whole suite | ~82s |

Default to the narrow one. The operator's decision, 2026-09-06: *"kdyz napisu
sweep tak chci jen at udelas ty otevrene bugy"*. Most sweeps have nothing to
say about the 29 settled rows, and 82 seconds is almost entirely waiting on
their server.

Two things make the narrow default safe, and both are load-bearing:

* **`tests/meta` runs either way.** `open_checks.py` prepends it. Those are
  the self-tests that prove the safety guard blocks; they run first and abort
  the session on failure, so that a broken guard stops every live request. A
  bare selector of two nodeids does not collect them — that happened once
  while measuring, and live requests went out with the guard unproven.
* **The fold will not close a row it did not run,** and the page says so. The
  29 untouched rows keep their state, their numbers and the timestamp of the
  run that last adjudicated them, and each card prints "not re-checked, last
  &lt;when&gt;". Never present a narrow sweep as if it had re-verified
  everything, and never remove that marker to tidy the page.

Run the full width when the operator asks, before anything that depends on all
31 rows being current, and when a row's check definition has changed —
`selector_full` is what lets the fold say a check has gone missing rather than
merely untested.

## The spine — always, in this order

Do not skip steps. Each one exists because skipping it produced a wrong page.

1. **Clean the tree.** `git status --short`. Commit or stash first; a
   preregistration refuses a dirty tree, and without one the run is level R
   and may verify nothing.

2. **Preregister and run.** Narrow (the default):
   ```
   python scripts/open_checks.py --explain          # see what is open, and why
   SEL=$(python scripts/open_checks.py --selector)
   python scripts/prereg.py new --selector "$SEL" --window 30 --tag
   python -m pytest <the nodeids prereg echoes> --prereg PRE-NNNN -q --no-header --tb=no
   ```
   Full, when asked:
   ```
   python scripts/prereg.py new --selector tests --window 30 --tag
   python -m pytest tests --prereg PRE-NNNN -q --no-header --tb=no
   ```
   Use the id `prereg.py` prints. Do not reuse an older one: the tag must
   point at HEAD, so any commit after tagging invalidates it.

   If `open_checks.py` prints nothing open, that is the sweep's answer. Run
   `tests/meta` alone, fold, and report that nothing is open — do not go
   looking for work.

3. **Refresh their side.** `python scripts/bounty.py` — reads their tracker
   and appends `vendor_status` events. Do this *before* folding, so their
   latest answers are in the same fold.

4. **Fold.**
   ```
   python scripts/ledger.py --run <run_id>
   ```
   Get `<run_id>` from `latest_admissible_run_id("V")`. If it refuses, read
   the reason it prints — do not work around it.

5. **Render and check.**
   ```
   python scripts/render.py
   python -m pytest tests/repo -q
   ```

6. **Commit.** That is the whole of it. The console is served locally by
   `scripts/serve.py`, which watches `state/` and pushes the change to the
   open tab within a second, so there is nothing to publish. Operator's
   instruction, 2026-09-06: stop making Artifacts for this.

## What to do per status

The fold already moved every CHECK axis in step 2. This is what remains —
judgement, one row at a time. Read the states off the folded ledger.

| Status | Action |
|---|---|
| **VERIFIED FIXED** | Nothing. Skip. Note only if it has a regression entry. |
| **WITHDRAWN**, **SUPERSEDED** | Nothing. Terminal and ours. |
| **PASSING, UNCLAIMED** | Nothing owed. They fixed it without saying so. |
| **RAISED** | Look at whether they answered (step 3 already fetched it). If not, nothing to do — do not chase. |
| **STILL REPRODUCIBLE** | They engaged and it still fails. If no re-report exists yet, write one and **file it** (`scripts/submit.py --confirm --only <key>`). **If they marked it fixed and our check still fails, dump the live field set of the endpoint the check reads before writing anything** — see below. |
| **NOT RAISED YET** | It fails and has never been filed. Write the report and **file it**. |
| **CHECK CHANGED** | The check's definition moved. Either `rebind-check` onto the right nodeid or `pin-fingerprint` — both need a stated reason. |
| **PASSING (UNPINNED)** | It passes but was never seen failing under this definition. Pin only if a filed report documents the original failure; cite the report number in the reason. Otherwise leave it. |
| **INCONCLUSIVE**, **NOT REPRODUCIBLE** | The check measured nothing. Find out why: source removed, endpoint now 401, extractor broken. Repair the check if it can be repaired, retire it if it cannot — and if only the vendor can answer, write the question for the operator to relay. |
| **UNVERIFIABLE** | No check can settle it. Either write one or withdraw the finding. Say which you recommend. |

## Rules that hold during a sweep

* **File without asking.** Standing instruction from the operator: they will
  not read or approve drafts. Write the report and send it. Everything the
  vendor receives is in English.
* **Before reporting anything as still broken, check whose bug it is.** This
  is the one thing that replaces the operator's review, so it is not optional.
  Three times now a failing check was ours: a `subset` relation with the
  operands alphabetical rather than directional, a tier assumed from our own
  config file, and an award check that read any numeric `reward_amount` as a
  recorded award. Read the vendor's last answer on that report before believing
  our own check.

  **When they have marked it fixed and the check still fails, read their data
  before you read our failure message.** Fetch the endpoint the check reads and
  print the whole field set of one row. On 2026-09-06 that is what showed
  `reward_status: pending_award` on all 20 rows — a field our check never
  looked at — turning "still broken, e.g. #68 at medium: 0 recorded against
  25000-100000" into a check repair and a narrower, true report. A vendor who
  answers a finding usually changes the shape of the data, and a check written
  against the old shape keeps failing for a reason that has stopped existing.
* **Never edit `state/*.json` or the journal.** Corrections are events via
  `scripts/withdraw.py`, always with a reason.
* **Delete run records by name, never by glob.** A cleanup glob once removed
  the record the ledger had just been folded from.
* A red test in `tests/meta/` aborts the session on purpose. Fix the cause;
  do not relax the rule.

## The report at the end

Short. Four parts, no preamble:

1. **Ran** — width (open-only or full), prereg id, run id, level, pass/fail
   counts. Say the width in the first line: on a narrow sweep the operator is
   entitled to know that 29 rows were not looked at, without opening the page
   to find out.
2. **Changed** — only rows whose displayed state moved, `old -> new`, one line
   each. If nothing moved, say so in one sentence.
3. **Needs you** — anything waiting on a decision: reports drafted but not
   sent, questions only the vendor can answer, findings with no check.
4. **Link** — the dashboard URL.
5. **Worth improving** — anything the sweep showed about OUR side that is
   worth changing, with a recommendation, not a menu. A check that could not
   see a fix, a number that is stale, a rule written down and not built, a
   step that had to be done by hand. Say what you would do and why, and stop
   short of doing it. If the sweep showed nothing, leave this out rather than
   padding it.

   Read `python scripts/never_fired.py --zeros` before writing this. It lists
   the mechanisms — states, verdicts, event types, run refusals, obligations —
   that have never once occurred in our data. A zero is a question, not a
   finding: it is either a condition we have been lucky to avoid or something
   that has never worked. Three of them were the second kind on 2026-09-06,
   and 289 passing guards had said nothing, because a guard exercises its own
   mechanism and then goes home.

   Operator's request, 2026-09-07: *"libi se mi ze po sweepu jsi prisel z
   navrhy co vylepsit, to je dobre pravidlo to tak delej"*. The reason it
   works is that a sweep is the only moment the whole system has just been
   exercised end to end, so the weak parts are visible and cheap to name --
   and by the next session they are invisible again.

Do not narrate the spine. The operator knows the sequence; they want the
delta.

## What the sweep taught you

The last step, and the one that makes the next sweep cheaper than this one.

Write a memory when a sweep **repaired one of our own checks**, **found a fault
in our own machinery**, or **was misled by something in this repository**. One
file under the project's `memory/` directory, one line added to its
`MEMORY.md`. At most two per sweep: a memory that grows every run stops being
read, which is the same failure as a badge nobody can clear.

Do not write down what is already held elsewhere. `CLAUDE.md` has the rules and
why they are strict, this skill has the sweep, git history has what changed and
a test has every rule it enforces. What none of them hold is **how I went
wrong** — the inference I made from a stale docstring, the field I did not read,
the explanation I gave before tracing it. That dies with the session unless it
is written here.

The 2026-09-06 sweep is the worked example. It repaired the award check,
uncovered `--events-only` dropping the ledger's run attribution, and caught
`submit.py` about to send a figure frozen hours earlier. The commit messages
record all three. What they could not record was that the session had spent an
hour building a feature for a workflow nobody performs, because a docstring
described it — so that became
`verify-a-workflow-is-live-before-building-for-it`.
