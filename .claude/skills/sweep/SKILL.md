---
name: sweep
description: Re-check the open Cymetica bugs, send what our checks found, and say what changed. Use when the operator says /sweep, /qa-sweep, "projdi bugy", "udelej sweep", or asks where the QA work stands. "full sweep" / "cely sweep" re-checks every row.
model: sonnet
effort: high
---

# Sweep

```bash
python scripts/sweep.py                       # read tracker and inbox, run the checks of open reports, print the table
python scripts/sweep.py --all                 # every report, and every vendor check no filed bug holds
python scripts/sweep.py --send --only 7       # post what is owed on the reports you have read; --only repeats
```

[operator 2026-09-06] *"kdyz napisu sweep tak chci jen at udelas ty otevrene bugy"*. Default to open rows.

A row is open when it is not withdrawn, they did not reject it, and we have not told them it passes (or it failed since we did). A verdict is per report and rests on every check of it. A sweep takes 8 to 25 minutes, mostly waiting on their server; `--only` takes a minute.

## What to do with each line

| Table says | Do |
|---|---|
| `owes pass`, `owes fail` | Read it first (below), then `--send --only` those reports, 12 at most per run. It re-runs the check right before posting, and holds a verdict that changed. |
| `held: <why>` | The row's `hold` in `state/filed.json`: the operator's word is awaited. Nothing goes. Delete the field when it comes. |
| `fail`, nothing owed | Filed and failing, or they already have our fail. Nothing to do; do not chase. |
| `inconclusive` | The check measured nothing: source gone, 401, extractor broken. Repair it or delete it. Never a verdict. |
| `no check: look by hand` | The check went with the lab. Open the page or API once; if it is plainly fixed or plainly broken say so in the report, and write a check only if it is still worth one. Rows we already passed show here only under `--all`. |
| `fails, and no filed bug holds it` (`--all`) | Whose bug is it? If theirs, write it in `outbox/reports.yaml` with `check:`, and `python scripts/submit.py <key>`. Unasked: [operator 2026-09-06] *File without asking.* |
| `filing X: outcome unknown` | A filing may have landed. Look on their tracker; re-running the same key settles it. |

**A recurrence reopens the original, never a new report.** [operator 2026-10-07] *"mas otevrit stary bug kdyz je stejne a ne tvorit duplicitni"*. `submit.py` refuses a key that already holds a report; a fail on the old one reopens it.

## Before saying anything is still broken

**Check whose bug it is.** This replaces the operator's review. Three times a failing check was ours. When they marked it fixed and the check still fails, read their data before our failure message: fetch the endpoint, print the whole field set of one row. A vendor who answers a finding usually changes the shape of the data, and a check against the old shape keeps failing for a reason that is gone.

A pixel-level defect in a product we did not design stays out. Wrong numbers, false statements, broken behaviour and lying docs stay in.

## What Cymetica asked us to look at

REPLY-0030, on the operator's instruction, in their order: Build it Better end to end; Fund Launcher and the fund pages; the advisor connector and the discovery documents; anywhere a page, its markdown and its API disagree. Leave alone: load or volume testing, the deep lane while it is short of capacity, anything writing outside paper mode, real deposits or withdrawals. One surface all the way through as a stranger beats a pass over ten. At low severity, file what would mislead a stranger; pure style goes in one report per surface.

## The report

A few Czech lines: how many reports, how many fail, pass, inconclusive; what changed; what was sent; what needs a look by hand; and anything on our side worth improving, with what you would do. [operator 2026-09-07] *"libi se mi ze po sweepu jsi prisel z navrhy co vylepsit"*.
