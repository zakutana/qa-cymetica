# Bugs department -- memory

The one department that tests, verifies and files (docs/crew-plan.md). Read at the start
of every run. Ten lines a heading at most; the manager curates it once a day, and a line
that stops being true moves to the archive, never silently away. Write with
`python scripts/crew.py lesson bugs --heading know|work|wrong "..."`.

## What we know

- Every other department hands a bug over as a ticket and stops caring; the filing, the check, the ledger and the dashboard are ours alone (`submit.py`, `ledger.py`, `render.py`).
- A narrow sweep is 8 to 25 minutes; a level-V run needs a clean tree: `crew.py hold`, then `crew.py held --wait 90` until 0, then `crew.py tidy`, then prereg.
- 2026-10-12 A worker's sweep aborts on tests/meta/test_pipeline_league.py when QA_CREW_DEPT leaks into bb accept (T-0007, 2026-10-12); workers cannot edit tests/meta, so say it to the manager and fail the ticket, never unset the variable.
- 2026-10-12 #117's check treats a 4xx with a reason as satisfied; a 4xx on a card still reading tradeable_now true is its own finding (#200, T-0005): one card, two refusals 23 min apart.
- 2026-10-12 2026-10-12 A level-R run needs a prereg too, and a prereg refuses any dirty tree: with a staged run record or an uncommitted bugs.md left behind, a sweep run folds as not evidence (git_dirty, no_prereg), and 17 minutes of it also drifted the fingerprint (T-0002). Commit your own lesson in the turn you write it.

## How we work

- A `bug` ticket: reproduce it through our client first; a defect gets a check and a report through `submit.py`, a documentation gap is said to the manager for the operator's Telegram (CLAUDE.md).
- A `sweep` ticket: the qa-sweep skill at narrow width; a `hunt` ticket: their newest surface first, SAFE reads.
- What woke a sweep (`moved` in the ticket) is read before anything else.

## How we went wrong

## Archive
