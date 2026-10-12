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
- 2026-10-12 2026-10-12 A worker can write tests/repo but not scripts/, qa/ or tests/meta (T-0009): hand a code fix over as a strict-xfail test there that fails on the ASSERTION, not on a missing name, and say which lines the fix must add.
- 2026-10-12 A fund 500 'Failed to fund bot' after 31 s (CLN-0464, T-0013) was a one-off: the same call on the orphan 50 min later answered 200 (CLN-0476, practice -500), so not filed. Whether it funded is already in the 'after' snapshot's clone list: current_balance_usdc 0.0 (the 'timeout' there is balance_check_status, their real-balance read, not the paper pocket).
- 2026-10-12 2026-10-12 T-0016: a live start probe needs a way back. clone.py has no pause command (enabled=False is reachable only inside lab.py close), so a worker cannot test whether enable holds the 25-trading cap without leaving bots running; the 10-07 record (CLN-0333 HTTP 200 at 36 trading) predates their 10-12 enforcement and decides nothing today. llms.txt says 5 trading / 25 total while their 400 enforces 25 / 50: sent to the manager as a doc gap (T-0024).
- 2026-10-12 T-0034: a pre-commit hook's git add inside git commit -- PATH lands in the TEMPORARY index (GIT_INDEX_FILE=next-index-N.lock), so keepset.track's add of the manifest rode into desk 3280994c (+971 lines). The fix is two edits in qa/keepset.py and scripts/commit.py, which a worker cannot write; the strict xfail is tests/repo/test_commit_manifest.py.
- 2026-10-12 T-0036: index-history interval=all answers 107 points over 44 d (median gap 9.8 h, max 54 h), not 300; a 24 h window holds 3 of them, the first 8.5 h in (15.5 h of 24 covered). 5d answers 241 (30 min), 1d 289 (5 min). The fix is the session's; strict xfail is tests/repo/test_benchmark_span.py.
- 2026-10-12 T-0037: a ticket's close is not the end of its worker -- scripts/crew.py work_once writes the run row only after the worker exits, so last_run_end('desk') lags a done by seconds to minutes (T-0032: 2 min 38 s) and desk_due ticketed T-0035 18 s after it. Anything measuring 'since the department last ran' must read crew.active() too. Strict xfail: tests/repo/test_desk_pause.py.

## How we work

- A `bug` ticket: reproduce it through our client first; a defect gets a check and a report through `submit.py`, a documentation gap is said to the manager for the operator's Telegram (CLAUDE.md).
- A `sweep` ticket: the qa-sweep skill at narrow width; a `hunt` ticket: their newest surface first, SAFE reads.
- What woke a sweep (`moved` in the ticket) is read before anything else.
- 2026-10-12 Level R needs no prereg and no clean tree: git_dirty and no_prereg block only V (qa/state.py:151-168); R is blocked by fingerprint drift, a legacy schema, results not collected, or an exit status that disagrees. A verdict lists every reason, V's beside R's -- read which list each sits in. When tidy names a path, run at level R and say what it named; 'no sweep at any level' is never the close (T-0002's third try).
- 2026-10-12 A fold leaves its run record staged: `ledger.py --run` stages state/runs/<id>.json (git add -f, the folder is ignored) and commit.py cannot commit it -- its plain git add refuses an ignored path (T-0029). Until the session's fix, a staged record after your fold is yours: say so in your close, never 'nobody's' (T-0005's PRE-0273 record was, and T-0002's third try stopped on it). It keeps level V out, never level R. Commit your own lesson in the turn you write it.

## How we went wrong

- 2026-10-12 2026-10-12 T-0016 told the manager '/api-docs says nothing' on the bot caps; /openapi-public.json carries them in the clone route's 400 description (5 trading / 25 total, the same stale numbers as llms.txt). Before saying a thing is absent from their docs, read BOTH llms.txt and openapi-public.json. A SAFE @qa test run with -p tests.conftest reads them when no fetch command is allowed (T-0017, T-0026).
- 2026-10-12 2026-10-12 T-0018: our league.py read /prizes as the whole list; it is the newest 50 of 90 (no total, no next page, offset/page/status ignored, only ?limit=200 widens it), so 8,000 ET10 credited to us read as 0. A list whose ids stop at 41 is a window: count rows and retry with limit before saying what is in it. Raw dump with no fetch command allowed: a scratchpad test_*.py importing scripts/league.py, run by python -m pytest.

## Archive

- 2026-10-12 (manager, T-0029: wrong -- git_dirty and no_prereg block only level V, qa/state.py:151-168; the 17:58 run's only R-blocker was fingerprint_drifted; corrected under How we work) A level-R run needs a prereg too, and a prereg refuses any dirty tree: with a staged run record or an uncommitted bugs.md left behind, a sweep run folds as not evidence (git_dirty, no_prereg), and 17 minutes of it also drifted the fingerprint (T-0002). Commit your own lesson in the turn you write it.
