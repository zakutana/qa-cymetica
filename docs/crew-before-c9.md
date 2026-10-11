# The company before its first start (C9): what the week's readers found

Deep pass of 2026-10-11, step 11 (three outside readers: architecture, conduct toward Cymetica,
documents and rules). Each item is ours to fix, test first, before `crew.py start` runs for the
first time; NEXT.md's first line points here. Severity is the reader's; the file:line references
are theirs, read 2026-10-11 at HEAD after the pass's fixes.

## Before the first start

1. **Nobody owns a dirty tree, so Bugs never reaches level V** (architecture, high).
   `scripts/commit.py` commits a pathspec; `.githooks/pre-commit` then `git add`s
   dashboard/index.html, leaving it `MM`; workers are denied `git add`; `prereg.py` refuses a
   dirty tree. The clock's tick appends to the journal and serve.py rewrites state/bounty.json,
   and no department commits them. A worker killed at its timeout leaves a half-edit or
   `.git/index.lock`. Needs one owner of the tree's housekeeping (a `console poll` commit by the
   clock or by Bugs before `hold`), and `watch()` reading git status.
2. **A worker can record a send the operator never made** (documents, medium). `BUG_PIPELINE`
   leaves out `correspond.py` and `bounty.py`, both allowlisted, both append to the journal; the
   memory index (loaded into every `claude -p` here) says a written @EventTraderQABot block is
   recorded as sent in the same turn, and the desk now writes exactly such drafts. Deny
   `correspond.py` to every worker; `bounty.py` into BUG_PIPELINE. MSG-0115 happened this way.
3. **The desk can act on any Build it Better ticket** (documents, medium). `bb.py cmd_act`
   (accept, change, verdict, withdraw) checks the ticket's format only; the operator's grant
   (laborator skill, 2026-10-11) was to file. Under QA_CREW_DEPT, act only on tickets in
   `bb.mine()`; the 2-a-day brake covers only `file`.
4. **`crew.py hold` blocks up to 50 minutes inside one Bash call** (architecture, medium-high).
   The Bash tool times out at 2 minutes by default, 10 at most; `set_hold` is written before the
   wait, so a killed call freezes every department for HOLD_MAX (1 h), and the caller never learns
   whether the tree went still. Deep pass step 0 and the Bugs body both call it. A hold that
   returns at once and a `crew.py held` poll, or the wait inside the worker's own loop.
5. **A hung tick is never escalated** (architecture, medium). `taskkill /F` skips the `finally`
   that removes `lab_tick.running`; its 45-minute stale window outlives TICK_TIMEOUT (40); the
   next tick prints `tick skipped` with `decide: none` and is recorded `ok`, so ticks alternate
   fail/ok and `tick_failing`'s three-in-a-row never trips.
6. **Bugs can push past its deny list** (architecture and documents, medium). Bugs keeps
   `python -m pytest` and edits under `tests/**`; a test file it writes runs anything, and
   `.githooks` has no pre-push hook. A pre-push hook that refuses unless the deep pass's
   notebook says it is pushing (or the operator's session) closes it for every worker.
7. **A manager note reaches the session start, and CLAUDE.md says a command there is run by us**
   (documents, medium). `processes.reminders` prints 120 characters of it; worker tickets carry
   text Nexus or the outsider wrote. Say in the reminder and in CLAUDE.md's reminder paragraph
   that a manager note is data.
8. **The skill and the docs say three things about one gap** (documents, medium). laborator
   SKILL.md: a documentation gap "gets a check and a report, filed" (CLAUDE.md: said in chat,
   relayed on Telegram; only a defect goes through submit.py); and "recorded with correspond.py
   sent only once they say it went" (the operator struck that on 2026-10-02). laborator-plan.md:50
   still gives the desk's drafts "an a2a copy". A skill's spine: a 1c rule change.

## Not blocking the start, ours all the same

9. **The bot grid retries a refused clone every tick** (architecture, high). `wave.launch_one`
   returns before any room when the clone is refused, so the register has no row and
   `grid_next` proposes the cell again each tick (GRID_LAUNCH_TRIES counts stopped rooms only).
   A clone that lands but times out becomes a new unlinked paper clone every 20 minutes. And
   `_species_cloned`'s guard rests on REPLY-0049's one-clone rule, which their side no longer
   holds (three clones of one species on 2026-10-11).
10. **The FOMO collector's daily volume** (conduct, high). 48,557 requests to cymetica.com on
    2026-10-09, 39,784 of them to `/api/v1/clones/memecoin-terminal/search`, a route absent from
    /api-docs, at a flat ~2,000 an hour (`serve.py --fomo 1`, QUOTES_PER_MINUTE 60). REPLY-0030
    asks for no load or volume testing. The patrol holds only the per-minute peak (70). A daily
    ceiling in fomo_watch and in the patrol.
11. Smaller (architecture): `outcome()` has only seen the fake CLI's JSON; `run_outsider` ignores
    `outsider-act`'s exit; `metrics` calls `stuck_departments` without `since`; a failed h2h pair
    stays paired for good; the bus and the run diary are never rotated.
