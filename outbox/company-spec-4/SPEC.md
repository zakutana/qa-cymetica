# Build a Company, round 4 (draft, open)

Started 2026-10-22 so nothing is forgotten; **the operator adds more items before it is filed**, and the mockup (`outbox/company-live`)
is drawn only for what is settled. Not filed, not pushed. Items marked *waits for their answer* depend on a Telegram question to Cymetica.

## A. Units, not dollars (settled)

**1. The company shows units, not dollars.** The page prints "$2.13 today" on every department row, "$2.13 today / $3.32 last 7 days" on the
Spend card and a daily cap in dollars. Read on the owner's company 14 on 2026-10-22 (`GET /company/mine`, `/office`): for every department
`cost_usd_7d` and `units_7d` are the same number (Cymetica QA 3.3249 and 3.324890, Development 0.3791 and 0.379142, Trading desk 0.4812 and
0.481207), and what limits the work is the plan's windows (5 units in 5 hours, 30 units a week); `at_zero` says *Nothing is charged while it
waits*, and extra usage was off. So the dollar sign is a relabelled unit and says the owner is paying when he is not. **Show units wherever spend is
shown** (department rows, the Spend card, the cap), with the window beside them (*0.6 of 5 in the 5-hour window, 8.6 of 30 this week*).
Dollars (USDC) appear only for extra usage, where money really moves.

**2. Units per task.** Each task shows the units it used: on the Tasks tab, in a department's room and in the task's detail, and the list can be sorted
by units. The data is already served: `tasks[].units` (task 63 *Stranger sken* 1.060236, task 67 *Hlídej podané bugy* 0.475597, task 65 0.433106) and
`turn_strip[]` (one entry per turn with `task_id` and `units`; the Manager's own turns have none). A task that has no units yet (task 66 shows null)
says *not measured* and not zero.

**3. The Products tab lists only what the owner created, not every page he improved** (the owner's screenshot of the live tab, 2026-10-22: 13 products,
38 builds). Pages that already existed on the platform before the owner's first request, and that he only improved through Build it Better, are not
his products and must not carry his name: the owner names **My Agents** and **Events**, both platform pages that existed already. Round 2 (item 12) set the
rule: *an app counts as the owner's when the owner was the first to put it into Build it Better and it did not exist before*. The platform has both dates
(when the page first existed, when the owner's first request on it was filed); please apply the rule from them and do not list the exceptions by hand.
The same cards also show three requests that have no page: **Usage**, **Creator rewards: register a post you wrote yourself...** and **Build it Better for
crypto communities...**, marked *funded*, and **Airdrop Farmer** marked *building*; a request with no page is not a product (round 3 asked the same: no card
for a request that was closed or never shipped).

## B. The Quant Lab tests cloned bots (waits for their answer to MSG-0206)

An experiment is a cloned bot, or two head to head, judged on paper results; the lab runs combinations of skills, models and indicator settings until
a profitable clone is found, proposes new algorithms and skills when none is, and hands a promising clone to the Trading desk (live, or a tournament
seat), always with the owner's approval. Their REPLY-0191 says the last step is not built and the experiments today are price rules. What this item
asks is fixed after they answer the three questions in MSG-0206 (what the company's own tools can do with clones today).

## C. The Supervisor works as the owner expects (waits for their answer to MSG-0212 / MSG-0214)

The weekly review reads all chats, tasks and processes, finds what bothers the owner, reports it to Cymetica as feedback and improves the company with
what exists. Their Manager says it does not. Asked in MSG-0214.

## D. The chat (reported as bugs in MSG-0211 and MSG-0213; drawn here only if they do not fix them as bugs)

A bubble in the thread while NEXUS works, with the queued task's number; every reply says which message it answers; a task number in a message is a link
to that task.

## What stays as it is

Everything not named above stays as rounds 1 to 3 and your builds have it.
