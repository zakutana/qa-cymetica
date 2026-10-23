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

## B. The Quant Lab tests cloned bots (built by them; nothing asked here)

Asked in MSG-0206; their answer REPLY-0193 (2026-10-23) says it is built, and it is live: `GET /api/v1/company/14/quant-lab` returns the owner's rule
(at least 10 closed trades, a return of at least 2% and a drawdown under 15% in each 3-day window, 2 windows in a row; the lab varies a bot itself, 6 a
day, and tries another bot after 3 misses; hand-off to a tournament seat or a live copy), the backtest board (11 bots), our 70 bots, and no experiment
yet. The Experiments page (`/company/app/experiments`, `quantlab.js`) has the Bots section, *Your rule* and *+ Add bot*. Nothing to request until a first
experiment has run; one gap: these endpoints are not in `/llms.txt`.

## C. The Supervisor works as the owner expects (waits for their answer to MSG-0212 / MSG-0214)

The weekly review reads all chats, tasks and processes, finds what bothers the owner, reports it to Cymetica as feedback and improves the company with
what exists. Their Manager says it does not. Asked in MSG-0214.

## D. The chat (reported as bugs in MSG-0211 and MSG-0213; drawn here only if they do not fix them as bugs)

A bubble in the thread while NEXUS works, with the queued task's number; every reply says which message it answers; a task number in a message is a link
to that task.

## E. A countdown to the next pass (settled)

The company works in passes (`pass_every_s` 120: every 2 minutes, up to two agent turns a pass), and the owner cannot see when the next one is. The page now
says *NEXUS answers on the next pass (every 2 minute(s), oldest message first). Approvals that wait do not hold a message. (about 22:37)* under a waiting message,
which helps once a message is sent. **Show the pulse where the owner looks all the time**: next to the company's name and the Pause button, a small
*next pass in 1:12* that counts down, becomes *running now* while a pass runs and *paused* / *waiting for the window* when none will start, with *turns today 21 of 40*
beside it. The data is served: `GET /company/mine` has `heartbeat.last_pass_at`, `heartbeat.next_pass_at` (null while paused) and `heartbeat.pass_every_s`, and
`run_state.turns_today` and `turns_cap`.

## F. Play and pause for each department (settled)

Each department row gets a small play / pause button (icon, in the department's colour, with a tooltip *Pause Development* / *Resume Development*). It stops or
starts **that department only**: its queued tasks wait, the other departments and Command go on. The row says why it is stopped: *Paused by you* against
*Paused: the company is paused*, so the two are not mixed (today every row reads just "Paused"). It survives a reload. Command, the Manager, has no button: it answers
the owner. While a department is paused its `units` stop and the daily cap does not matter. Please tell us if the API cannot pause one department; then the
button is drawn and the rest is yours.

**A paused room goes dark in the office** (the owner, 2026-10-23: *"kdyz je neco pauznute tak tam zhasnes v mistnosti svetla vsechna"*): once its last turn has
finished, its lamp is off, its neon outline and floor wash are out, its name on the glass is dimmed, its wall screen reads *Paused · by you* (or *the company is
paused*), and everything inside is seen as in a room with the lights off. When the whole company is paused, every department's room goes dark; Command stays
lit. Resume, and the lights come back. The row of a paused department dims with it, and its button turns into a filled play. Drawn in the mockup:
`sim.js` (`CO.deptPaused`, `CO.act.deptPause`), `app.js` (the button), `u3d.js` (`tint`, state *dark*), `office.js` and `style.css` (the flat office).

## G. The Universe's top line says what it counts (settled)

The live line reads *8 companies · 34 free slots · 0 yours · 2 products* and the owner, who has one company, asked why *yours* is 0. It counts land, not companies:
the owner's two slots now hold the two products, so no slot counts as his. **Say *your land* and count the slots the owner holds, products on them included**:
*8 companies · 34 free slots · 2 your land · 2 products*. The word *yours* alone is not used.

## H. The revenue share: the top 3 companies get 5%, 3% and 1% of every fee on Cymetica (settled, drawn)

Every company in the Universe is ranked, and the top three get a share of **all fees on the whole platform**: 1st 5%, 2nd 3%, 3rd 1%.

**The measure: Revenue, last 30 days (USD)**, what the platform itself paid the company in that time: bug bounties (ET10 at the day's
price), its products' rewards, Agent Tournaments and League prizes. Not counted: trading P&L (it can be faked between two accounts and goes
negative) and money moved between one owner's own accounts. One number per company, from the platform's own records, never typed in.

**A floor: a company qualifies at $10,000 revenue in 30 days** (the mockup's example; the number is yours to set, as with the slot price), so
a company that earns $5 a month never takes a share of everyone's fees. A place nobody reaches stays empty and its share is not paid.
Paid monthly in USDC, from that month's fees, by the ranking at the month's end; a tie goes to the company that got there first. Private
companies are on the board too, with name, station and revenue: the share comes from everyone's fees, so who receives it is public.

**The board** (`uvboard.js`, styles in `uvpanel.css`): one big pane of frosted glass over the Universe's top-left, under the LIVE line, that
does not move when the map turns or zooms. It is turned away on its left edge like a cockpit panel (rotateY 18.4°, rotateX 3.4°), with wide
margins all round, a cyan rim, a lit top edge and a slow sheen (no thick edge under it); on the glass there is only
type and light: **no row boxes, no tiles round the icons, no frames**. *REVENUE SHARE · TOP 3*, *5% · 3% · 1% of every fee on Cymetica*, then
three rows: a big place numeral in Cymetica's own colours (green, cyan, blue: the share is paid by Cymetica), the company's station glyph in its colour and its name (YOU on ours), its
revenue, and the share with about what it pays a month
(platform fees of the last 30 days × the share). Under them *Platform fees · 30 d* and *qualify at*, and *Full leaderboard →*. **A place nobody
holds is an open seat, not a blank**: a dashed ring with a plus breathing in the place's colour, *Open seat*, *reach $10,000 in 30 d*, and what the seat
pays a month (*5% ≈ $19,300 / mo*). **At launch nobody will have reached the floor**, so the board must sell the seats: under the subtitle *All 3 seats
are open. Be the first company to take one.*, the three open seats, and at the foot *Up for grabs ≈ $34,740 / mo · qualify at $10,000* (the mockup shows
it with `?board=empty`). On a stage under
760 px it folds into a *TOP 3* pill. It hides while Buy land is on.

**The first look** stands 20% farther back than the original frame, the whole galaxy in view, right of the middle and low (aimed 7% of the frame's width to
the left and 6.5% of its height up: on a 2.2-to-1 stage the outer orbit spans 25% to 92% of the width and 12% to 92% of the height), so the board
covers open space and not the orbits (`u3d.js`, `home()`); a stage under 760 px, where the board folds, keeps the old frame.

**The full leaderboard** (a dialog from the board): every company ranked, its revenue, and for the top three the share and the month's
amount, for the rest *qualifies* or *$X to qualify*; our row highlighted. **On top of it, big, who gets a seat** (the owner, 2026-10-23: explain it
more clearly, bigger): the three seats as tiles (*1 · 5% · ≈ $19,300 / mo*, nothing under it: who holds a seat is the list's first rows), and beside them *Who gets a seat* in three
numbered lines: *Top 3* by revenue in the last 30 days; *$10,000+* of revenue in those 30 days, or the seat stays open; *Month end*: the ranking then
decides, paid in USDC from that month's fees; and one small line on what counts as revenue (trading P&L does not). In the list a dashed line marks
the floor (*$10,000 · the line to qualify*, *nobody above it yet* when that is so); rows under it are dimmed. **The dialog is the board's own
glass** (the owner: as beautiful as the board): the same frosted pane, cyan rim, lit top edge and slow sheen, flat; the same head (*REVENUE SHARE*
in the glowing gradient, *LEADERBOARD* beside it); and only type and light on it: no boxes round rows, seats or icons, big gradient place numerals,
thin glowing lines between rows.

**The pulse**: every 10 seconds a cyan arc carrying a dollar sign leaves Cymetica's sun to each of the three, one after another, and
*+5% of fees* / *+3% of fees* / *+1% of fees* rises over each in the same cyan. Only the top three get it. The flat map shows the line of text.

What the build needs from you: per company the 30-day revenue from your records (the sources above), the platform's fees for the month so far
and for the last 30 days, and the payout itself. Left to you: the floor, and a cap if you want one (for example, a share never larger than the
company's own revenue). The figures in the mockup are samples from one model (`CO.uvBoard` in `uv-data.js`).

## I. A station on the map looks washed in its colour; in Settings it looks right (a bug, settled)

The owner's screenshots, 2026-10-22: his company FDS (Citadel, green) in **Settings** ("In the Universe" preview) is dark steel plating with green
only in its windows, lights and ring; the same station **on the map** is pale mint all over, walls and roof alike, so the building's detail is gone.
Expected: the map draws every station the way the Settings preview does: the steel stays steel, the company's colour lives in the lights.

Our own mockup does the same (the map's stations come out tinted in their colour, the Settings preview does not), so the design you copied has
the fault; we could not pin it down. What we ruled out in the mockup (`u3d.js`): the lights and tone mapping are the same in both scenes
(ambient 0x1a2230, hemisphere 0xdfe8f2, sun 2.0 to 2.1, rim 0x00cfff, ACES at exposure 1.15); it is not the colour grade (the map at the preview's
saturation, 0.66, is still pale), not the station's halo or its pool of light (both hidden: no change), not the sky, not the bloom (with the post pass
off the hull is greener still) and not the viewing angle (the map's camera brought down to the preview's angle: still pale). Left: how the map builds
or scales a station (`UVSS` 2.7) and its materials there. Please find it on your side and match the preview; tell us what it was, and we fix the mockup.

## J. The owner writes the line his product shows in the Universe (settled, drawn)

The live map's tooltip for Gem Screener reads *made by BJ Ironstar Capital · Which apps earn money, ranked by upside.*, and its panel repeats the
line: a sentence the owner never wrote and does not want. **Each card on the Products tab gets an *In the Universe* line with an Edit button**: a
small dialog with one field (up to 70 characters, a counter) and Save; an empty field removes the line. That line, and only that line, shows under the
product's name in its map tooltip and in its panel. **Until the owner writes one, no line shows**: nothing is generated for him. Cymetica's own
buildings (the Promo Market) keep their own line. Mockup: `app.js` (`uvLineModal`, the Products card), `uv-data.js` (`CO.uvLine`, `CO.setUvLine`),
`universe.js` (the tooltip), `uvpanel.js` (the panel).

## K. Airdrop Farmer on Orbit 5 · slot 5: its logo as a head, in straw and brown (settled, drawn)

The owner bought a third slot on 2026-10-22 (`GET /company/land` lists `slot-5-5` taken, with no product on it). **Put Airdrop Farmer on it**, as
round 3 put Gem Screener and Agent Casino on theirs: the same click (the map flies to it, the panel opens), the same MADE BY plate, the owner's
own Universe line (item J).

**The building is the product's logo turned into a 3D head**, its shapes and proportions as the logo has them (the head 34 across, the brim 59, the
crown 13.5 high and dented on top, in the logo's 64 units), **in yellow, brown and green, and as a robot's helmet, not a face** (the farmer is an
agent; a round brown head with eyes reads as a person's skin, so do not draw one; and no visor over the face, which reads as a balaclava): a head of
polished gold with a seam of dark bronze round it (the logo's stroke); a ring of amber lights set in the gold round the face (the logo's dotted ring);
two pill eyes of warm white light in dark bronze bezels, blinking now and then; a bronze bolt with an amber light on either side where ears would be;
a straw hat (a woven texture) with a dark-brown band, its brim turned up a little at the edge; a sprout of two leaves on the crown, lime and gold. It floats over a gold ring, leans back a little so the visor shows under the brim from above, and turns
toward the viewer, looking about a little. As big as the other two products, smaller than the sun. Mockup: `u3d.js` (`adFarmer`), the flat map `universe.js` (the logo
itself, recoloured), the data `uv-data.js` (`CO.ADS`).

**Its panel** shows the three numbers the live page leads with: *23 airdrop farms*, *1 USDC deposit*, *10% of realized profit* (the fee; tooltip:
nothing on a loss), the date they were read, and *Visit Airdrop Farmer* to `/airdrop-farmer`. Read them live from the page's own data, not typed in.

## What stays as it is

Everything not named above stays as rounds 1 to 3 and your builds have it.
