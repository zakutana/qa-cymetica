# ET-31466 Build a Company owner view: verification

Read 2026-10-15 19:47-20:11 UTC, after Nexus's Telegram message "owner view is live" and its follow-up that the 1440 px fix is live. The ticket still reads `stage building`, 3 messages (BB-REQUEST, BB-SPEC, BB-ACCEPT), no delivery message, `our_url` none, deadline 2026-10-15 15:07 UTC passed (`bb.py get`, 19:47 and 20:11). Their files changed today: `company-office.js` and `build-company.css` at 19:42:46 GMT (the 1440 block is in the CSS), `build-company.js` and `company-office-3d.js` at 19:18:05 GMT. Reads only, our X-API-Key: `/company/mine` (4 times), `/13/plan`, `/13/tasks` and `/tasks/30,31,32,37`, `/memory`, `/events`, `/messages`, `/audits`, `/nexus/plans`, `/nexus/usage`, `/openapi-public.json`, `/llms.txt`, MCP `tools/list`. `GET /company/13` answers 405 (only DELETE is defined). The MCP call `company_status` is refused at SAFE (classified `unknown`) and stays refused. Spec: `outbox/company-office/request.md` (35 lines, 13 "Done when"). Phone and fonts are out of scope.

**The built-in pane is not signed in** (`data-signed-in="false"`; the served HTML has no owner shell), so the owner view could not be opened and no screenshot of the real owner page exists. What I did instead, called the harness below: ran their live `build-company.css`, `company-office.js` and `build-company.js` inside the live /company page, on a skeleton of the owner shell that I built from their element ids and class names, fed our real `/mine`, with every non-GET blocked (0 sent) and the socket stubbed. Widths come from their CSS and the page's real ancestors. Heights depend on the site chrome above the grid, which is the page's own (header 88, paste bar 65, Back 33, page head, company bar, tabs: the grid starts at y 399). Anything that needs the real shell is marked NOT CHECKABLE.

## The look, beside desktop-1920.png and desktop-1440.png (harness)

| | Read |
|---|---|
| Palette | PASS: 19 distinct hex colours across the CSS and JS, all cyan, green, red, blue or slate-blue neutrals (one white, `#fff`, on a hover); 0 purple, orange, amber, yellow or plain gray |
| Blocks | PASS on what their scripts and CSS draw: counter numbers 3 / 0 / 24, two bars with resets, at-zero line, heartbeat, Paused pill and Resume, department rows with the totals tiles, TURNS TODAY 2 / 40 strip with 40 cells, Next up, Manager chat, live feed: the blocks of the mockup. Tab names and static labels live in the shell: NOT CHECKABLE |
| The office | Not the picture: a flat top-down 4 x 3 floor plan (world 1620 x 890), vector at the device pixel ratio, not isometric; the spec allows "any dense, detailed 2D style". All seven "dense" parts are drawn. With one department (ours) 6 of 12 floor cells are empty |
| Size, 1920 x 1080 | **FAIL on the look**: stage 1,173 x 532 px, the drawing is height-limited to 968 x 532 (fit 0.598), so labels (world 10-15 px) render at 6-9 px and 102 px of stage stay empty each side |
| Size, 1440 x 900 | **FAIL on the look**: stage 1,111 x 296 px, drawing 539 x 296 (fit 0.333), labels 3-5 px. The mockup's labels read at 1440; these do not |

The size is by construction, not a chrome accident: the world is 1620 x 890 (aspect 1.82), the stage 1,173 x 532 at 1920 (2.2) and 1,111 x 296 at 1440 (3.75), and `fit()` takes the smaller ratio, so the drawing is height-limited at both widths. A shell a few tens of px different from my skeleton does not change that.

**Their 1440 claim, checked:**

| Claim | Read |
|---|---|
| Departments fold into a one-line strip above the office | PASS: rail 1,113 x 48 px, row direction. It drops each department's experts and its "Queued: reason" line (`display: none` from 1181 to 1600 px), which line 11 asks for |
| Right column narrows | PASS: 280 px (was 320) |
| Office area 1,126 px wide (was 768) | PASS as a container: stage 1,111.3 px with this pane's 15 px scrollbar, 1,126 without one (derived: 1440 - 64 + 48 - 8 - 280 - 8 - 2, from the CSS); the old 240 / 1fr / 320 grid gives about 768, derived. **But the drawing did not grow**: it is limited by the 296 px height, so it is 539 px wide before and after. The fix widened the empty margins, not the office |
| Page still fits one screen | PASS: `sizeGrid` ends the grid at y 829 of 900 (the ask bar starts at 839); the page is 1,248 px high counting the footer |

## Done when

Evidence tiers: **API** (our key), **code** (their live JS and CSS), **harness** (rendered, shell reconstructed).

| # | Done when | Read |
|---|---|---|
| 1 | One screen at 1920 x 1080 and 1440 x 900 | PART (harness). Real data (0 approvals, 2 plan items): everything is in view at both sizes (grid ends y 1009 of 1080 and y 829 of 900; chat box y 812-856 and y 731-775); the live feed is partly below the fold at 1440 (right column 490 of 430 px). In the mockup's own case (2 approvals, 3 plan items) at 1440: right column 572 of 430 px, chat box y 813-857 against a column that ends at 829, so the Manager chat box needs scrolling; approvals show 102 of 293 px, Next up 69 of 158. At 1920: 719 of 610, approvals 164 of 226, Next up 116 of 158, chat box in view, feed below |
| 2 | Three turns-left numbers = units left / measured average | PASS (API, harness). 3 / 0 / 24 = floor(0.720739 / 0.186176 = 3.87), floor(0 / 0.186176), floor(13.662219 / 0.558528 = 24.46). `units_per_turn` 0.186176 = 0.930880 units / 5 measured turns (the basis says "last 5", the OpenAPI says "last 20"; n is 5); `usdc_per_turn` 0.558528 = 0.186176 x markup 3. The page prints the same three. "Changes after a turn without a reload" is line 20 |
| 3 | Bars with used / cap and resets; at-zero line | PART (harness, code). Session 0.28/1.00, resets in 4h 37m (2026-10-16 00:39 UTC); week 6.13/6.00, "Sat 18:00" local (2026-10-17 16:00 UTC), bar clamps at 100% and turns red; the week's 0 is red. At zero with extra usage on: "At 0: keeps running on extra usage (on)". The off line ("pauses until the reset") is in the code; showing it needs a setting change, not made |
| 4 | `/mine` budget carries the counter's figures | PASS (API). `budget` has `units_per_turn`, `units_per_turn_basis`, `turns_measured`, `windows.five_hour`, `weekly`, `extra` (used, cap, left, `turns_left`, `resets_at`), `at_zero`, `extra_usage`; identical in the 19:47, 19:52 and 20:07 reads, and the page reads `windows.*.turns_left` directly. MCP `company_status` could not be called (refused at SAFE); its `tools/list` description names budget and plan |
| 6 | Office at least 1,100 px at 1920, sharp on 2x | PART (harness). The drawing is 968 px wide (fit 0.598, height-bound), below 1,100; the canvas holding it is 1,172.9 px (about 1,188 without a scrollbar, derived); backing store 1760 x 798 for 1172.9 x 532 css at ratio 1.5, so css x ratio (code caps at 3): sharp |
| 7 | Plate, desk and agent per expert, current task, notes; Manager, owner, audit, add lot | PASS (code, harness). Drawn for our Testing room: plate (2 open, 2 done, 0 failed), desk and QA tester, wall screen, 4 notes (2 queued, 2 done, as the API's `notes`), Manager hub "2", owner room, weekly audit, "+ Add department" lot. Caps in the code: 4 desks per room, 12 notes per board, the lot only while a slot is free (up to 7 departments) |
| 9 | Charter editable in place; next task starts from it | NOT CHECKABLE: a save is a write, and "the next task starts from it" needs a turn. Read: the panel opens with the charter (1,449 chars), "1,449 / 2,000 - saved Tue 19:14" from `charter_updated_at`, tiles open 2, done 2, failed 0, 0.53 u, memory 6, "Queued: Company paused", tasks with a one-line result, memory by kind, waiting approvals (harness). Save is `PATCH /departments/{id}` {"charter"}, `maxLength` 2000 in the OpenAPI |
| 13 | Next up in run order; removed never runs, moved runs in its place | PART. `GET /plan` lists task 32 then 37, each with `why`, `turns_expected` 1, `units_expected` 0.186176, `waits` {paused}. OpenAPI: `POST /plan/{id}/move` up \| down \| top, `DELETE /plan/{id}` (409 once started). The page has up, down and remove buttons (no "top", which Nexus's message names). Nothing moved or removed: writes |
| 15 | Paused: no department reads Working, every queued task says why | PASS (API, harness). Department `status: "queued"`, `waits` {paused, "Company paused"}, `running` null, `run_state.open.running` 0; plan items carry `waits`; rail "Queued: Company paused" at 1920 (hidden at 1440), Next up "Company paused - ~1 turn", panel "Queued: Company paused". The Tasks ledger gives no reason on queued rows (#37 empty; #32 "next try 13 Oct 21:28", two days old) |
| 16 | Message while paused says "answers on Resume" | NOT CHECKABLE: a message is a write. See "Also off", item 1: this company answered one while paused |
| 17 | Office tab shows nothing of Investable or Legal entity | NOT CHECKABLE: needs the signed-in shell (the scripts read here do not touch those tabs; `company-office-3d.js` exists) |
| 18 | Every task shows outcome, turns and units | **FAIL**. Tasks 30 and 31 are `done` with `turns: 1` and `units: null` in `/tasks`, `/tasks/30`, `/tasks/31` and `/mine` `tasks_recent`, and the ledger prints "-" in Units. The units exist: `/nexus/usage` has two `company_turn` items, 0.210212 (ref `13:testing:1791919085`, at 2026-10-13 19:18:37.96 UTC, 20 ms before task 30's `finished_at`) and 0.323559 (ref `13:testing:1791919118`, at 19:20:01.85, 60 ms before task 31's), and the department's `units_7d` 0.533771 is their sum. The OpenAPI task schema has no `turns` or `units` either |
| 20 | Untouched page: counter, bars, counts, feed, Manager reply move without a reload | NOT CHECKABLE: the owner socket needs a signed-in pane and a finished turn; the company is paused and the week is at 0. Code: `/ws/company/{id}` `state` messages become `bc:state`, which re-renders everything from the pushed state |

**13 lines: 4 PASS, 4 PART, 1 FAIL, 4 NOT CHECKABLE.** Plus the look: FAIL at both widths (drawing 968 and 539 px wide, labels 3-9 px). Needing a signed-in pane: look at the real owner page, 1, 6, 7 (exact), 9, 16, 17, 20, the 2D/3D control, the Upgrade link, the order of the right column.

## Also off

1. **A paused company answered and was charged.** Our diary records the pause (`state/company.jsonl` CO-0002, 2026-10-13 19:28:37 UTC) and no resume; `run_state` at 20:07 still says "Paused: nothing runs and nothing is charged until you resume." Yet owner message 72 ("tak co se deje", 2026-10-15 19:39:01) got Manager replies 73 (19:39:23) and 74 (19:39:35), and `/nexus/usage` has two `company_turn` items for them, 0.171520 and 0.107741 units, both flagged `overage: true` (the week stands at 6.13 of 6.00). The page's Pause and Resume leave no event, so the operator may have resumed and paused again; he should say. If not, this contradicts the page's own line and Done-when 16.
2. The Manager's reply 74 says "now running #32"; task 32 is `queued`, `running` 0, and no `task_running` event exists after 2026-10-13 19:25. The same reply queued task 37 with `origin: owner` (event 1844) for a status question.
3. `heartbeat.next_pass_at` for the paused company is always the read time plus 31-32 s (19:47:25 to 19:47:56, 19:52:27 to 19:52:59, 20:06:55 to 20:07:27) while `last_pass_at` stays 19:41:17 and `pass_every_s` says 120. The page hides it while paused; the API promises a pass that does not come.
4. The company-creation form caps a charter at `maxlength="1500"` (`build-company.js` line 147) where the page, llms.txt and the OpenAPI say 2,000.
5. The page's visitor text, its JSON-LD and llms.txt still say "pixel-art office"; the office is now vector drawing.
6. Code read, not observed: the heartbeat's "last turn" reads today's `turn_strip` only, so after 00:00 UTC it will say "no turn yet" with yesterday's turns behind it.

## Documentation gaps

- llms.txt Build a Company entry: none of `GET /plan`, `POST /plan/{id}/move`, `DELETE /plan/{id}`, nor the new `/mine` fields (`budget`, `plan`, `turn_strip`, `heartbeat`, `run_state`, `totals_7d`, `message_notice`, `waits`, `units_7d`).
- OpenAPI: task schema without `turns` and `units`; department items in `/mine` are untyped; the department `status` text says "idle, working or blocked" while the live value is `queued`; `message_notice` has no fields; the page reads `wait` from the message answer, the schema lists only `notice`.

## Re-read 2026-10-16 ~04:00 UTC, after REPLY-0179

| Item of MSG-0174 | Read |
|---|---|
| 1 Task units (Done-when 18) | FIXED: tasks 30 and 31 read units 0.210212 and 0.323559 in /tasks/{id} and /mine tasks_recent |
| 2 Office size | IN THE CODE: company-office.js now lays the floor plan 6 wide on a wide stage; not rendered here (no signed-in pane) |
| 3 1440 strip | FIXED in the CSS: the 1181-1600 px rules no longer hide experts or the queued reason |
| 4 "top" | FIXED: Next up draws a `data-a="top"` button beside up, down and remove |
| 5 #211, #212 | VERIFIED FIXED by PRE-0281 (run-20261016T035402Z-d7bb5d7b, level V); #212's check was corrected first (d21fb0e8: a paused company that promises no pass now passes, as its docstring said) and pinned; pass verifications sent on both reports |
| 6 Docs | FIXED: llms.txt names /plan, /move, run_state, turn_strip, units_7d and a "floor plan", no "pixel-art"; the OpenAPI task route carries turns and units |

Verdict: the operator's.
