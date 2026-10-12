# The company before its first start (C9): what the week's readers found

Deep pass of 2026-10-11, step 11 (three outside readers: architecture, conduct toward Cymetica,
documents and rules). Each item is ours to fix, test first, before `crew.py start` runs for the
first time; NEXT.md's first line points here. Severity is the reader's; the file:line references
are theirs, read 2026-10-11 at HEAD after the pass's fixes.

**2026-10-12: items 1 to 8 fixed, test first, on the operator's word ("oprav vse, uz ji chci
zapnout").** 1 `crew.py tidy` (Bugs commits the housekeeping under its hold), commit.py
commits the page a pathspec commit left staged, the watchdog removes a stale index.lock and
sends an old half-edit to the manager; 2 correspond.py denied to every worker, bounty.py in
the pipeline; 3 bb.py acts only on the company's own tickets under QA_CREW_DEPT; 4 `hold`
returns at once, `held --wait` asks (100 s at most), a hold ends with the run that set it; 5 a
skipped tick is a failure, a killed tick's marker goes with it, a dead pid's marker is stale;
6 `.githooks/pre-push` refuses under QA_CREW_DEPT; 7 the reminder and CLAUDE.md say a manager
note is data; 8 the laborator skill and plan say one thing about gaps and written blocks.
Tests: `tests/meta/test_pipeline_crew.py`, `tests/repo/test_reminders.py`. Items 9 to 11 stay open.

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

   **2026-10-12, the manager (T-0019, folding T-0009, T-0013's code half, T-0014 and OP-0004):
   one build, and its tests land in the same commit as its code.** Their 400 names two caps,
   both in force (REPLY-0122 said the same, 25 trading / 50 in all): CLN-0461 at 17:01,
   "Maximum 25 trading Paper bots per user (paused bots do not count) — pause one before cloning
   another"; CLN-0465..0471 at 17:27 and 17:46, seven refusals, "Maximum 50 Paper bots per user
   including paused ones — delete one before cloning another". Our record: 60 accepted clones
   less 10 accepted releases = 50 owned. The grid counts trading only (22-25), so it finds free
   slots and sends up to GRID_PER_TICK (4) refused clones a tick, held as "not accepted (HTTP
   400, rejected)". The 50th clone (CLN-0462) was accepted and its fund answered 500 "Failed to
   fund bot" (CLN-0464; the platform half is Bugs', T-0013): unfunded, never started, it holds a
   slot. Nothing releases a finished clone but the three-stop-loss rule in the manual `wave.py
   resume`, so at 50 owned the grid starts no cell again (83 of 132 tried, LAB-0038 17:16).

   a. **The caps.** The spec is Bugs' `tests/repo/test_grid_capacity.py` (T-0009, written
      18:07, untracked; later than T-0019's text, so it governs: `_capacity_cap(rows)` with its
      id, both wordings, a fresh refusal holds even when our count shows a slot, one probe
      after 6 h, an accepted clone after a refusal clears it). Plus: the newest refusal of
      EACH wording binds its own count -- trading against the sampler (`_trading_now`), all
      against owned (accepted and not released, the orphan included). `wave.MAX_TRADING` = 25
      (REPLY-0122, CLN-0461; the 34 trading of 10-08 is T-0016's defect lead, never a limit)
      and a new `MAX_PAPER` = 50, comments true; `resume_wave` inherits the 25. `launch_one`
      marks a capacity 400 `result["capacity"]`, why "cap reached: <their message>";
      `bot_grid` breaks on it, and `grid["cap"]` names both ("trading 25/25, all 50/50").
   b. **Freeing slots, so the grid moves again** (the manager's decision; the operator's veto).
      When the all-cap binds, before each clone, release (`clone.release`, its guards as they
      are) the oldest paper clone of ours that nothing will start again: no room running on it,
      and every room on it judged, or it never started (no accepted enable: CLN-0462's orphan,
      after one fresh read of its balance). Never one whose stop was a finding (`resume_wave`'s
      `findings`), nor one an open report names. And OP-0004: a running room whose bot reads
      balance 0 and has not traded in its window (19 of the 22 trading at 16:54) measures
      nothing; the tick closes it with a verdict, the one close that pauses the bot
      (docs/lab-manager.md), and its clone is then releasable.
   c. **Tests**, beside `_the_grid_starts_untried_cells_on_paper_up_to_its_limit` or where Bugs
      put them: the two wordings fresh at once -> no clone call; 50 owned with one finished
      clone -> one release, then one clone; a running room's clone or a finding's clone -> never
      released; a balance-0 running room -> closed with a verdict. The untracked file dirties
      the tree `prereg` reads (`git status --porcelain`, item 1) until it is committed with the
      code; committed alone, it turns HEAD red.
10. **The FOMO collector's daily volume** (conduct, high). 48,557 requests to cymetica.com on
    2026-10-09, 39,784 of them to `/api/v1/clones/memecoin-terminal/search`, a route absent from
    /api-docs, at a flat ~2,000 an hour (`serve.py --fomo 1`, QUOTES_PER_MINUTE 60). REPLY-0030
    asks for no load or volume testing. The patrol holds only the per-minute peak (70). A daily
    ceiling in fomo_watch and in the patrol.
11. Smaller (architecture): `outcome()` has only seen the fake CLI's JSON; `run_outsider` ignores
    `outsider-act`'s exit; `metrics` calls `stuck_departments` without `since`; a failed h2h pair
    stays paired for good; the bus and the run diary are never rotated.
