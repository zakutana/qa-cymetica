# Build it Better: Build a Company, the owner's office

**Filed by the operator on the form, 2026-10-14, as ET-31420 (BB-SPEC 34/34, accepted), then withdrawn by mistake the same day; filed again with this block the same day: their BB-SPEC carries all 35 lines word for word (diffed, numbering aside) and the four pictures; BB-ACCEPT without a BB-CHANGE.** Nexus's feedback of the same day (journal, threaded to MSG-0160) asked for the work ledger, approvals first, the Manager's plan and charters as the main lever; the ledger and approvals were already in, so the refiling adds Next up (item 13) and opens a department with its charter, editable in place (item 9), and trims elsewhere to stay under 8,000 characters. No other open request on `cymetica.com/company` (board read 2026-10-13); the page was built as feature #911 (ET-30909 in its own source).

The operator, 2026-10-13, on the owner view of our company (id 13): *"sekce legal entity a investable je zbytecne velka to budou jen nejaky taby. musi byt uprostred ta 2D mapa nejaka husta hezci ted je to jak gta 1 hnus, chci at je to husty 2D grafika, pak tam musi byt jednoznacny counter nekde tahu at vime kolik zbyva jeste tokenu a cele to nejak huste navrhni"*. Goals are theirs; the design is ours, their veto open.

Why the counter matters: the page shows `turns_today / turns_cap` (4 / 40), which says nothing about the plan. Our first six minutes ran three turns metered 0.12, 0.21 and 0.32 units (`/api/v1/nexus/usage`, 19:16-19:20 UTC), 0.65 of a Pro session's 1.00, while `/api/v1/nexus/plans` lists `company_turn` at 0.05 ("the estimate reserved before a turn"). The owner could not see that until the session was two-thirds gone.

Then the operator pasted a complaint and asked for its fix in this spec: *"agents have been showing 'Working' with queued tasks for quite some time, but the daily agent turn counter remains at 0/40. The Manager also hasn't responded to my latest status request ... I can't seem to find a way to inspect individual task statuses either."* Reproduced on our own company at 20:19 UTC (`GET /api/v1/company/mine`, `/tasks/32`): the company `paused` since ~19:22, Testing `status: working` with `running: 0, queued: 1`, task 32 `queued` after `last_error: "no answer"` with `next_attempt_at` 19:28 UTC, 51 minutes past. Nothing on the page says why nothing runs. Items 13 to 15 below. Not filed as a bug report: the operator routed it here, and the complaint's author has raised it already.

## The pictures

Drawn by `make_mockup.py` (this folder), rendered and colour-scanned by `render.py`. Sample data in one coherent state on the Pro plan (counter, room plates and department rows agree); the Manager's first message and the two Testing tasks are ours, the rest is illustrative. Their current office was rendered from their own `company-office.js` with our data for comparison (scratchpad, not attached).

- `desktop-1920.png`: 1920 x 1080, the Office tab.
- `desktop-1440.png`: a laptop, 1440 x 900.
- `phone-390.png`: a phone, 390 px; the office opens zoomed on the Manager.
- `department-1920.png`: a room clicked: Testing, with its real tasks, memory and charter from our company (id 13).
- `mockup.html`: the same page, live at any width.

## Filing

On the form, "I have a link" with `https://cymetica.com/company`, the block below, one item per line, and the four PNGs as pictures. After filing, check their BB-SPEC line by line against this block, then BB-ACCEPT without a BB-CHANGE (#192).

```
Upgrade the owner's view of the live /company page itself, not a new page beside it; it keeps its name, logo and copy, and the template lines about rebuilding someone else's app do not apply. Goals, not methods. The attached pictures are the template and the spirit is the requirement: shape, proportions and wording are yours to improve. Colours: the site's cyan, green, red, blue and slate-blue neutrals; no purple, orange, amber, yellow or plain gray. English, numbers before words; explanations in a tooltip, not a paragraph.
1. One screen: at 1920 x 1080 and 1440 x 900 the company bar, the turn counter, the office, the departments, what waits for the owner, the Manager's plan and the Manager chat are on the first screen without scrolling.
2. A turn counter in the company bar, always visible: TURNS LEFT as three numbers, this session, this week, and on extra usage. Turns left = plan units left in that window divided by this company's average units per turn over its last 20 turns. Today the page shows turns_today / turns_cap only; our first three turns were metered 0.12, 0.21 and 0.32 units while /api/v1/nexus/plans lists company_turn at 0.05, so the counter uses the measured average, not the reserve.
3. Under the three numbers, two thin bars: session used / cap with the time to its reset, week used / cap with the reset day. One line says what happens at zero: runs on extra usage (on), or pauses until the reset. A number at 2 or less turns red. It updates after every metered turn over the live socket the office already uses, no polling.
4. The same figures in GET /api/v1/company/mine under budget (units per turn, units left and turns left per window, what happens at zero), so the page, agents and the MCP company_status read one number.
5. The daily ceiling stays, labelled as a ceiling: a strip of 40 cells under the office, one per turn today, coloured by outcome (running cyan, done green, failed red), "TURNS TODAY 16 / 40".
6. The office in the centre, filling its stage (at least 1,100 px wide at 1920), drawn sharp at the device pixel ratio: not a 480 px pixel-art canvas scaled up. Our picture is isometric; any dense, detailed 2D style is fine.
7. Dense means, checkably: each department is a room with a plate (name, open, done, failed); a desk with a lit monitor per hired expert, the agent at it with its role; the room's current task on its wall screen; one note per task on a wall board, coloured by state; the Manager's room in the middle with the open count; the owner's desk with the approvals count; the weekly audit; an empty "+ Add department" lot.
8. Alive: a working agent lights up (monitor and a ring); work travels between the Manager and the rooms as packets coloured by outcome; a room glows while it works.
9. Clicking a room or a department row opens that department beside the office. It opens with the charter, editable in place (up to 2,000 characters, with when it was last saved), since every task starts from it; then open, done, failed, units in 7 days, memory; what runs now with its attempt and last error; its tasks with a one-line result each (a click shows the task in full); its latest memory by kind; its waiting approvals.
10. The 2D / 3D switch, zoom and fit stay as small controls on the stage. On a phone the office opens zoomed on the Manager and pans with a finger.
11. Left rail: one compact row per department: status dot, name, units used in 7 days, open, done, failed, memory, experts. Units are the counter's unit (plan units), instead of or beside cost_usd_7d. Under the rows: tasks done and failed in 7 days, the company's units in 7 days, approvals approved in 7 days.
12. Right column: Waiting for you first (department, kind, age, a one-line title, Approve, Reject, Read; Read shows the full drafted report or request), then Next up, then the Manager chat (newest at the bottom, the box always visible), then the live feed.
13. Next up, the Manager's plan: each task it will run next, in the order the runner takes them, with its department, one line on why, and the turns it expects; the owner can remove a task or move it up or down before any turn is spent.
14. Company bar: name, Active or Paused with Pause or Resume, the counter, "N waiting for you" in red when N > 0 (opens Approvals), and Upgrade to /usage. Under the name, the runner's heartbeat: last turn at, next pass in.
15. Honest status: a department reads Working only while one of its turns runs. Otherwise its open tasks read Queued with the reason in a few words: company paused, plan limit until a time, Free plan, next pass in N s, or retry at a time after "no answer". Today a paused company shows Working with nothing running.
16. A message to the Manager that cannot be answered now says so at once under it, with when it will be: paused (on Resume), plan limit (after the reset), or the next pass.
17. Tabs instead of sections: Office, Tasks, Approvals, Memory, Audit, and on the right Investable, Legal entity, Token, Settings. Investable and Legal entity are tabs only: nothing of them on the Office tab; their forms move into their tab unchanged.
18. Tasks tab, the ledger of work: one dense table (status, department, title, started, turns, units, result) with filters by department and status.
19. Phone, 390 px: company bar and counter, tabs scrolling sideways, the office, departments, approvals, Next up, Manager, feed.
20. Live, without a reload: everything on the page updates over the /ws/company socket the office already uses. The counter, both bars and the units climb as each turn is metered; counts, tasks, approvals, the plan, the Manager's replies and the feed arrive as they happen.
Done when:
[ ] 1 At 1920 x 1080 and 1440 x 900 the counter, office, departments, approvals, Next up and chat are visible without scrolling.
[ ] 2 The three turns-left numbers equal units left / the company's measured average units per turn, and change after a turn without reloading.
[ ] 3 Session and week bars show used / cap and their resets; the at-zero line is right for extra usage on and off.
[ ] 4 GET /mine budget carries the same figures the counter shows.
[ ] 6 The office is at least 1,100 px wide at 1920 and sharp on a 2x screen.
[ ] 7 Every room shows its plate, a desk and agent per expert, its current task and its task notes; the Manager, owner, audit and add-department lots are there.
[ ] 9 A department opens with its charter editable in place, and the next task it runs starts from the saved text.
[ ] 13 Next up lists the queued tasks in the order they will run; a removed task never runs and a moved one runs in its new place.
[ ] 15 With the company paused, or the plan limit reached, no department reads Working and every queued task shows why it waits.
[ ] 16 A message sent while paused says at once that the Manager answers on Resume.
[ ] 17 The Office tab shows nothing of Investable or Legal entity; both open as tabs.
[ ] 18 Every task shows its outcome and the turns and units it used.
[ ] 20 With the page open and untouched, a finished turn moves the counter, the bars, the counts and the feed, and a Manager reply appears, all without a reload.
```
