---
name: qa-sweep
description: Re-check the open Cymetica findings, take the one action each one's status calls for, and report what changed. Use when the operator says /qa-sweep, "projdi bugy", "udelej sweep", or asks for the current state of the QA work. Say "full sweep" / "cely sweep" to re-verify all 31 rows instead.
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
| **STILL REPRODUCIBLE** | They engaged and it still fails. If no re-report exists yet, write one and **file it** (`scripts/submit.py --confirm --only <key>`). |
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
  Twice
  now a failing check was ours: a `subset` relation with the operands
  alphabetical rather than directional, and a tier assumed from our own config
  file. Read the vendor's last answer on that report before believing our own
  check.
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

Do not narrate the spine. The operator knows the sequence; they want the
delta.
