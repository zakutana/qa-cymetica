# Build a Company, round 4

Started 2026-10-22, to be filed as one Build it Better request (`build-it-better/improvements.txt`). The clickable mockup is `outbox/company-live`;
its look is binding where an item says *drawn*. Where the mockup still shows dollars, item A wins: units.

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

## C. The Supervisor works as the owner expects (asked in MSG-0212 / MSG-0214; REPLY-0197: the audit still reads only work records, no date given)

The company's Manager says today that the Supervisor only lists repeated work, unfinished tasks and stuck flows with a proposed fix each, does not read
the chats, does not touch the app and passes nothing to Cymetica; the one audit so far (id 18) ran a minute after the company was set up and found
nothing. **That is not what the owner expected from the start.** The Supervisor has **two layers** (the owner, 2026-10-23):

**1. The engine layer: the platform improving itself, in the background.** The owner has watched your Telegram bot since the start of the year and seen
it improve massively, again and again, from the conversations it has with people. The Supervisor should do the same for Build a Company: **instead of the
Telegram chats it follows every chat with NEXUS in every company**, the tasks and what came of them, what the owners approved, rejected and complained
about, and from that it **keeps improving the engine that runs all companies**: how NEXUS plans and answers, how departments pick up and finish work, how
tasks, passes, approvals and processes behave, what breaks and what is missing. (One evening of the owner reading his own chat found five such faults,
MSG-0211 / MSG-0213: a charter "rewritten" that was not, monitoring that ran once, replies that do not say which message they answer, no sign that NEXUS
is working, task numbers that point nowhere; an engine reading every company's chats finds these without anyone spending an evening.) **This is the
backend and owners never see it**: it is in no company's audit log, it asks nothing of the owner and files nothing under his name. Owners only notice
that the company works better week by week. (What it may read is yours to set under your terms.)

**2. The company layer: what the owner sees in his Audit tab.** On top of the engine, a review of **this one company**: it reads its chats, tasks,
processes and decisions and **optimizes what is specific to it**: its processes, its departments' charters, how its departments are set up, what its
Manager keeps getting wrong for this owner. Safe changes it applies itself (a reworded charter, a fixed process), each one listed and undone with one
click; anything that spends units or money, or adds or removes a department, waits for the owner as an approval.

**Where the owner sees the company layer: the Operations room** (the Audit tab). Each review: when it ran, what it read (chats, tasks, processes,
counts), and its findings, each with a link to the message or task it came from and what was done with it: *applied: … (undo)* or *waits for you*. The
next review's date is shown; the owner can also run one now. Nothing of the engine layer appears there.

## D. (dropped) The chat

Fixed as the bugs we reported (MSG-0211, MSG-0213): their answer REPLY-0197 (2026-10-23) and the live app.js / live.js (v=6adb7183) have the working
bubble, replies that say which message they answer and task numbers as links. Nothing asked here.

## E. How the company runs: the countdown to the next pass, and a Max 5x window that lasts (one item, because the two halves pull against each other; the choice is yours)

**What went wrong on Max 5x.** Read from the owner's company on 2026-10-23 (`GET /company/mine`, `budget`, `turn_strip`): the 5-hour window ran out after 11 turns in
23 minutes (4.94 of 5 units) and the company was blocked for three hours (*"You've hit your session build limit. It resets at 11:55pm UTC"*). 8 of those 11 turns
were the Manager answering the owner in the chat (2.84 units in all); only 3 were department work. The same price buys Claude Code a day of work on Opus at the
highest effort. What we ask: (a) a window that carries a real working session on Max 5x; (b) a chat turn that costs a fraction of a department turn (a short
answer needs no full pass); (c) work that continues while tasks are queued, instead of waiting for the next pass. Asked on Telegram and a2a as MSG-0219; the
owner's own words are in that message.

**What the owner cannot see today.** The company works in passes (`pass_every_s` 120: every 2 minutes, up to two agent turns a pass, a daily ceiling `turns_cap`),
and the owner cannot see when the next one is. The page says *NEXUS answers on the next pass (every 2 minute(s), oldest message first)* under a waiting message,
which helps only once a message is sent. We drew the pulse where the owner looks all the time: a small *next pass in 1:12* that counts down, becomes
*running now* while a pass runs and *paused* / *waiting for the window* when none will start, with *turns today 21 of 40* beside it. The data is served:
`GET /company/mine` has `heartbeat.last_pass_at`, `heartbeat.next_pass_at` (null while paused), `heartbeat.pass_every_s`, `run_state.turns_today` and `turns_cap`.

**The two pull against each other, so how the company runs is yours to decide.** The countdown counts passes and turns; (c) removes the wait for a pass, and with it
the thing to count down to. We do not know which suits your engine:
1. **You keep passes and turns:** the chip as drawn (below), with *next pass*, the ring and *2/40 turns*.
2. **You drop them** (work starts when it is queued, limited by the window's units): there is no pass to count and no turn ceiling to show, so apply the same chip
   with only what stays true: *running now* (green, a pulsing dot), *waiting for the window · 14:05* and *paused* (grey); no ring, no *next pass*, no turns.

Either way the place and the look are binding; what it counts is yours.

**One place only**, never per department: at the foot of the office, first in the bar of the plan's windows (This session, This week; the owner first had it by Pause, then: *"bych dal spis nekde dolu"*) (the owner, 2026-10-23: *"to ma byt nekde na 1 miste"*).
Drawn in the mockup as one chip (`index.html` `.strip #co-pass`, `app.js` `clock`, `style.css` `.pass`): a small cyan ring that empties as the pass comes,
*next pass 0:12*, and after a thin divider *2/40 turns*; green with a pulsing dot and *running now* while a turn runs; grey *paused* or *waiting for the
window · 14:05* when nothing will start. A tooltip says what a pass is.

## F. Play and pause for each department (settled, drawn)

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

## H. The revenue share: the top 3 companies get a share of Cymetica's revenue (a sketch; the look is drawn, the terms are yours)

**This item is a sketch, and how the revenue share really works is Cymetica's decision, all of it.** We draw what it could look like and propose one
way it could work; every term (the shares, how many places are paid, the floor, the payout, the measure, a cap, whether it pays at all as
sketched) is yours to set, and the board, the leaderboard and the pulse show whatever you decide. Nothing below is a requirement on the terms.
What is binding is only the look, as drawn.

**Wording (the owner, 2026-10-24): *revenue*, not *fees*, and a place is a *slot*, not a seat.** A plan's subscription is Cymetica's revenue too, and
*up to 5% of Cymetica revenue* is what he promises companies (only the first place gets 5%). So wherever this item below says *fees*, read
*revenue* (what counts as revenue is yours to set), and *seat* means *slot*. The mockup's board, leaderboard, pulse and Products tab use these words
now (*Open slot*, *Who gets a slot*, *Revenue brought · 30 d*, *+5% of revenue*), and the promo flyer for degens shows the same board:
`outbox/revenue-share-flyer/` (*JOIN THE CYMETICA QUEST · Build the best company in the Universe and earn up to 5% of Cymetica revenue*).

**The numbers in this item are an example for the design, not our terms.** The shares (5% / 3% / 1%), how many places are paid, the floor
to qualify ($10,000), the payout (monthly, in USDC) and any cap are **yours to set**: decide your own conditions, who gets how many percent and
what it takes to qualify, and the board, the leaderboard and the pulse show whatever you set. What is asked is the feature, its measure (below)
and its look; the terms are yours.

Every company in the Universe is ranked, and the top three get a share of **all fees on the whole platform**; in the mockup 1st 5%, 2nd 3%, 3rd 1%.

**The measure: the fees the company brought Cymetica in the last 30 days (USD)** (the owner, 2026-10-23: the top 3 are the companies that
make Cymetica the most revenue). A company's products bring people to the platform; those people trade, play and subscribe, and Cymetica takes
its fees on that volume. **Those fees are the company's number**: the share is paid from fees, so it goes to whoever brings them. This replaces
the first measure (what the platform paid the company: bounties, rewards, prizes), which rewarded taking money out, not bringing it in.
- **Whose fees they are:** a user who comes through a company's product or its link counts for that company (for a window you set, for example
  12 months), and so does every fee on volume that runs through the company's products (its bots, its tables, its apps), whoever the user is.
- **Not counted:** fees paid by the owner's own accounts and wallets, and by accounts linked to them (otherwise a company could trade with itself
  to climb); bounties, rewards and prizes paid to the company.
- **A cap, so that wash trading can never pay:** a company's share is never more than the fees it brought that month. Fees the company pays to
  itself do not count, and even if some slipped through, it could never get back more than it put in.
- One number per company, from the platform's own records, never typed in.

**A floor: a company qualifies at $10,000 of fees brought in 30 days** (the mockup's example; the number is yours to set, as with the slot
price), so a company that brings $5 a month never takes a share of everyone's fees. A place nobody reaches stays empty and its share is not
paid. Paid monthly in USDC, from that month's fees, by the ranking at the month's end; a tie goes to the company that got there first. Private
companies are on the board too, with name, station and fees brought: the share comes from everyone's fees, so who receives it is public.

**The board** (`uvboard.js`, styles in `uvpanel.css`): one big pane of frosted glass over the Universe's top-left, under the LIVE line, that
does not move when the map turns or zooms. It is turned away on its left edge like a cockpit panel (rotateY 18.4°, rotateX 3.4°), with wide
margins all round, a cyan rim, a lit top edge and a slow sheen (no thick edge under it); on the glass there is only
type and light: **no row boxes, no tiles round the icons, no frames**. *REVENUE SHARE · TOP 3*, *5% · 3% · 1% of every fee on Cymetica*, then
three rows: a big place numeral in Cymetica's own colours (green, cyan, blue: the share is paid by Cymetica), the company's station glyph in its colour and its name (YOU on ours), the
fees it brought (*$26,840 fees · 30 d*), and the share with about what it pays a month
(platform fees of the last 30 days × the share). Under them *Platform fees · 30 d* and *qualify at*, and *Full leaderboard →*. **A place nobody
holds is an open seat, not a blank**: a dashed ring with a plus breathing in the place's colour, *Open seat*, *bring $10,000 in fees · 30 d*, and what the seat
pays a month (*5% ≈ $19,300 / mo*). **At launch nobody will have reached the floor**, so the board must sell the seats: under the subtitle *All 3 seats
are open. Be the first company to take one.*, the three open seats, and at the foot *Up for grabs ≈ $34,740 / mo · qualify at $10,000* (the mockup shows
it with `?board=empty`). On a stage under
760 px it folds into a *TOP 3* pill. It hides while Buy land is on.

**The first look** stands 20% farther back than the original frame, the whole galaxy in view, right of the middle and low (aimed 7% of the frame's width to
the left and 6.5% of its height up: on a 2.2-to-1 stage the outer orbit spans 25% to 92% of the width and 12% to 92% of the height), so the board
covers open space and not the orbits (`u3d.js`, `home()`); a stage under 760 px, where the board folds, keeps the old frame.

**The full leaderboard** (a dialog from the board): every company ranked, the fees it brought (column *Fees brought · 30 d*), and for the top three the share and the month's
amount, for the rest *qualifies* or *$X to qualify*; our row highlighted. **On top of it, big, who gets a seat** (the owner, 2026-10-23: explain it
more clearly, bigger): the three seats as tiles (*1 · 5% · ≈ $19,300 / mo*, nothing under it: who holds a seat is the list's first rows), and beside them *Who gets a seat* in three
numbered lines: *Top 3* by fees brought to Cymetica in the last 30 days; *$10,000+* of fees in those 30 days, or the seat stays open; *Month end*: the ranking then
decides, paid in USDC from that month's fees; and one small line on what counts (the users the products brought, their volume, plays and subscriptions; not the owner's own accounts). In the list a dashed line marks
the floor (*$10,000 · the line to qualify*, *nobody above it yet* when that is so); rows under it are dimmed. **The dialog is the board's own
glass** (the owner: as beautiful as the board): the same frosted pane, cyan rim and lit top edge, flat and without the sheen; the same head (*REVENUE SHARE*
in the glowing gradient, *LEADERBOARD* beside it); and only type and light on it: no boxes round rows, seats or icons, big gradient place numerals,
thin glowing lines between rows.

**The pulse**: every 10 seconds a cyan arc carrying a dollar sign leaves Cymetica's sun to each of the three, one after another, and
*+5% of fees* / *+3% of fees* / *+1% of fees* rises over each in the same cyan. Only the top three get it. The flat map shows the line of text.

What the build needs from you: per company the fees its users and products brought in 30 days (attributed as above), the platform's fees for the month so far
and for the last 30 days, and the payout itself. Left to you, as said at the top: every term (shares, places, measure, floor, payout, a cap if you want
one; we propose: never more than the fees the company brought). The figures in the mockup are samples from one model (`CO.uvBoard` in
`uv-data.js`).

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

**Added 2026-10-24: a paused company's station goes dark on the map** (the owner: *"budou zhasnute firmy co zrovna nemakaji a jsou pauznute ...
zmizi ty barvy"*). A company that is paused (its owner's pause, or the company paused as a whole) is drawn in plain steel: its windows out, its
ring and halo (almost) off, and the colour that lives in its lights gone, until it runs again; the flat map draws it grey. A company that is
active stays as it is, lit deck by deck while a department works. It follows the pause switch at once, ours included. Mockup: `u3d.js`
(`makeStation`, `PAUSED_HEX`), `uv.css` (`.plot.paused`).

## J. The owner writes the line his product shows in the Universe (settled, drawn)

The live map's tooltip for Gem Screener reads *made by BJ Ironstar Capital · Which apps earn money, ranked by upside.*, and its panel repeats the
line: a sentence the owner never wrote and does not want. **Each product on the Products tab gets an *In the Universe* line with an Edit button**
(in the product's panel, item N; the tile shows the line under the name): a small dialog with one field (up to 70 characters, a counter) and Save; an
empty field removes the line. That line, and only that line, shows under the product's name in its map tooltip and in its panel. **Until the owner
writes one, no line shows**: nothing is generated for him. Cymetica's own buildings (the Promo Market) keep their own line. Mockup: `app.js`
(`uvLineModal`, `renderProdPanel`), `uv-data.js` (`CO.uvLine`, `CO.setUvLine`), `universe.js` (the tooltip), `uvpanel.js` (the panel).

## K. Airdrop Farmer on Orbit 5 · slot 5: its logo as a robot's head of green woven willow, under a straw hat (settled, drawn)

The owner bought a third slot on 2026-10-22 (`GET /company/land` lists `slot-5-5` taken, with no product on it). **Put Airdrop Farmer on it**, as
round 3 put Gem Screener and Agent Casino on theirs: the same click (the map flies to it, the panel opens), the same MADE BY plate, the owner's
own Universe line (item J).

**The building is the product's logo turned into a 3D head**, its shapes and proportions as the logo has them (the head 34 across, the brim 59, the
crown 13.5 high and dented on top, in the logo's 64 units), **a robot's head, not a face, and no metal** (the owner, 2026-10-24: *"ja nechci at je to
kovove"*, a farmer's material, a straw hat is great; the farmer is an agent, and a round brown head with eyes reads as a person's skin, so do not
draw one; and no visor over the face, which reads as a balaclava): a head of **green woven willow**, a basket weave in relief; a braid of hemp rope round
the face, which is also the logo's rim; the logo's dotted ring as eighteen small warm amber lights, each in a wooden collar; two pill eyes of warm
white light in walnut rims, blinking now and then; a walnut peg with a warm light on either side where ears would be;
a straw hat (a woven texture, light against the green head) with a dark-brown band, its brim turned up a little at the edge; a sprout of two leaves
on the crown, lime and gold. It floats over a ring, leans back a little so the face shows under the brim from above, and turns
toward the viewer, looking about a little. As big as the other two products, smaller than the sun. Mockup: `u3d.js` (`adFarmer`), the flat map `universe.js` (the logo
itself, recoloured), the data `uv-data.js` (`CO.ADS`).

**Its panel** shows the three numbers the live page leads with: *23 airdrop farms*, *1 USDC deposit*, *10% of realized profit* (the fee; tooltip:
nothing on a loss), the date they were read, and *Visit Airdrop Farmer* to `/airdrop-farmer`. Read them live from the page's own data, not typed in.

## L. The MADE BY plate in a product's panel as the mockup draws it (settled, drawn)

Round 3 (C9) asked for the maker's plate at the top of a product's panel; the live build has one, but not the mockup's (the owner's screenshot,
2026-10-23: *"nas vypada lepe"*). Today it is a cyan *MADE BY* pill whatever the company's colour, over a plain dark box with a thin frame and a dot.
**Draw it as the mockup does** (`style.css`, `.mkrow` and `.mkb`; `uvpanel.js`, `productView`), everything in **the company's colour** (gold for
BJ Ironstar Capital, green for ours):
- the *MADE BY* pill in the company's colour with a soft glow of it (not always cyan);
- the plate as a station's plate on the map: dark riveted glass (a rivet in each corner), squared caps, a frame of the company's colour mixed toward
  steel, an outer glow of the colour, the name in large white letter-spaced capitals with the colour's dot before it;
- **a small arrow under the plate**, pointing down at the product, in the frame's colour (missing on the live build);
- **a line of the company's colour running out of either side of the plate** to the panel's edges, fading outward (missing on the live build);
- on hover the frame takes the full colour and the glow grows; a click opens the company's office.

**Cymetica's own buildings carry the same plate: *MADE BY · CYMETICA***, in Cymetica's cyan (the owner, 2026-10-23: *"u firemnich budov jako treba
PROMO market at je tam made by CYMETICA"*); it opens nothing, since the platform has no office to visit. A company's product never says Cymetica
(round 3, C9).

## M. Ten new station skins to choose from (settled, designed)

A company picks its station's look in Settings (*In the Universe*) and when it is created; today there are seven (tower, dome, pyramid,
orbital, rocket, vault, stack). **Add ten more**, every one drawn and specified:

1. **Armillary Core**: three gimbal rings, each turning on its own axis, round a glass capsule of decks.
2. **Helix Spire**: thin glass floors, each turned on the one below; lit corners climb a 90° twist.
3. **Solar Sail**: four glass sail panels form a square of light and turn slowly round a mast of decks.
4. **Deep Array**: a giant dish on a turret of decks sweeps the sky slowly, its focus lit.
5. **Glass Arcology**: a shallow glass dome over a lit city, one tower per department, a tram circling inside.
6. **Pylon Crown**: tapered glass pylons round a ring, one per department, a core of light floating in the middle.
7. **Rift Hold**: an asteroid split in two, a glass deck per department bridging the glowing rift.
8. **Tesseract Frame**: a cube of struts balanced on one corner and turning, a glass cube of decks turning the other way inside.
9. **Nautilus Shell**: chambers on a two-turn spiral round a glass heart; each department adds one chamber.
10. **Halo Vortex**: floating rings widen upward round a column of light, alternate ones turning the other way.

**See them:** `outbox/company-skins/index.html`: each drawn in 3D from its own numbers, at the map's look-down and one scale, with a switch
for 1 / 4 / 8 departments (how each one grows) and the eight company colours; a card moves while hovered. **Build them:**
`outbox/company-skins/SPEC.md`: per skin its silhouette and proportions, the parts with the helpers `u3d.js` and `stations.js` already have, where
the company's colour lives, what moves and how fast, its footprint and height, and its line icon for Settings.

The same rules as the seven: **the hull stays steel and slate, the company's colour lives only in its lights** (never the accent-blended hull
materials: that is the washed look of item I); one deck per department, lit while that department works; each under 30% of the sun's diameter
on the map; nothing pulses (no plumes, no beams out of a prow), what moves only turns, runs along a track or bobs slowly.

**Settings: the picker is icons and one preview** (the owner, 2026-10-24: *"jen ty ikonky a 1 obrazovka kde se bude zobrazovat aktualni skin a v nem jen
barvy menit, zbytek jen ikonky se bude klikat"*). In *In the Universe* the grid of picture tiles goes. It becomes **one showroom across the card's
whole width** (*"to je divne jak je to cele tak na stredu"*): a wide preview of the current station in the company's colour, over the same space as
the "Create your company" picture (the office's sky, not near glows: *"proc tam jsou ty svetla v pozadi?"*), with its name and decks top left,
the Public / Private pill top right and the colour dots standing down its right edge; joined under it a dock of line icons, **all seventeen in one
row, no divider**, each only an icon with its name as a tooltip. Clicking an icon changes the preview; changing the colour changes the **model only**,
never the icons (they stay one neutral colour, the current one with the selection rim). The plates over the moving 3D are opaque, and the preview
draws at most 1.2 million pixels a frame (O1). **"Create your company" offers all seventeen too**, its arrows going through the new ten as through
the seven. Where a browser cannot draw 3D (and for the moment before 3D starts) the ten have no flat picture yet: the mockup shows each one's line
icon in the company's colour instead of falling back to a Dreadnought (`universe.js`, `iconArt`); a flat drawing of each is yours to add if you
keep the flat fallback. Mockup: `app.js` (`uvCard`), `style.css`, `u3d.js` (`Preview`), `builder.html`.

**All seventeen are built one way** (the owner: *"ty spodni modely jsou udelane v jinem stylu, nejsou osvetlene, nemaji zari, nejsou tak propracovane ...
at to udelaji stejne a mame jen jeden zpusob"*): a dark plated steel hull, the company colour only in the lights, windows lit deck by deck while a
department works, surface detail, a beacon, slow motion only, and the same glow and halo as the seven. The ten are real 3D in the mockup
(`stations-a.js` to `stations-e.js`, on the parts `stations.js` publishes as `CO.ST`), not the flat pictures of `company-skins/index.html`, which stays
as the sheet to build them from.

**Measured: seventeen is not too many for a weak computer, on two conditions** (an independent test of 114 runs on 2026-10-25: this machine's built-in graphics with
the processor slowed 4x, against the mockup before the ten; limits fixed before measuring: no frame over 100 ms while a page runs, no first-view freeze over 500 ms,
the entry page ready within 20 %). On first view the ten freeze nothing over 0.3 s (worst: Rift Hold in Settings, 285 ms); the Universe with 36 companies mixing all
seventeen draws 5.6 % more calls than with the old seven only, at the same frame time; loading their five files costs nothing measurable; they reuse the old
materials, so there are no new shaders. The conditions:
1. **The entry page keeps its six stations** (it loads only the old stations file). With all seventeen on it at once it was ready 30 % later and ran at 19 fps
   against 30.
2. **A station is built once and reused.** Our mockup rebuilds a station's 3D shape on every click, even one already shown: Rift Hold takes 105 ms a build on the slow
   processor (Nautilus 47, Deep Array 42, the old seven 3 to 19), and Settings builds it twice per click (the preview, and the owner's station on the map that is
   hidden behind it), so a repeated click costs up to 139 to 215 ms. Do not copy that: in the builder and the Settings preview keep each station's built shape per skin,
   colour and number of decks, and do not rebuild the hidden map's station while the map is not shown.

The test could not run a real weak laptop; first-view freezes there may be longer.

## N. Products: a tile per product, its panel with the people and the revenue it brought, and its logo (settled, drawn)

(In this item *fees brought* reads *revenue brought* since 2026-10-24, see H; the mockup's tab says *revenue brought*.)

The owner, 2026-10-23: *"kdyz kliknu ankazdy vyjede nejake bocni menu kde uvidim kolik mam visitsoru a kolik to vygenerovlao fee ta aplikace. a
chci moznost taky pridat si ikonku ke kazdemu produktu. nejake logo"* (a click on a product slides out a side panel with its visitors and the fees
it brought; and a logo for each product).

**One word for traffic.** Your pages count it five ways (visits, unique visitors, views, visitors, uses); the owner, on `/traffic` and
`/traffic/mine`, could not tell them apart (*"moc se v tom nevyznam co je co"*). The tab shows one: **People** = `/traffic/mine`'s
`unique_visitors` for the product's page. AI agents are not people and are shown apart.

**The tab.** Four numbers on top: products; **people** (30 days); **new users**, with *+1,000 ET10 each* under it: the referral reward
`/traffic/mine` already serves (`referrals.per_user_et10` 1000, `qualified` 0 on 2026-10-23); and **fees brought** (30 days), item H's measure,
the same figure the company has on the revenue-share board. Under them one tile per product (which ones: A3): its logo, its name, its Universe
line (item J; its path until it has one), **people and fees brought** in large figures, its 30 days of people as a line; the most fees first. The
whole tile is the button.

**Its panel** slides out on the right, in the look of a product's panel in the Universe; on a wide screen the tiles step aside for it. ×, Esc or a
click beside it closes it; another tile switches it. In it, top to bottom: **people** and **fees brought** (30 days), each with a one-line tooltip;
**people per day** over 30 days as bars (a day's figure on hover); **where its visits came from**, one bar: Cymetica's own pages against outside
(Google, X, Telegram, other sites), from `from_site` and `visits`, and under it the AI-agent visits on one line; its logo and its Universe line (Edit
lives here); *Open* the product. Nothing else: no uses, views, likes or builds, and fees as one figure, not split by source.

**The logo.** The owner uploads one (PNG, JPG, SVG or WebP, cut to a square from its middle) and can change or remove it; until then the product
shows its initials in the company's colour. **It is the product's icon wherever Cymetica shows the product**: its tile and panel here, its panel
and tooltip in the Universe, the Build it Better boards. Only the owner changes it; a visitor of a public company sees it.

**Data.** `GET /api/v1/traffic/mine` serves per page people, visits, AI-agent visits and `from_site`, and the account's referrals (read
2026-10-23; the mockup's figures are that read). Missing, and needed: **fees brought per product** (30 days; `/company/products`' `earned` is what
was paid, "0"); **people per day per product** (only the account has `unique_daily`; the mockup spreads each product's total over that shape);
**which product brought each new user** (referrals are account-wide); and a **logo upload** with its URL in the products list. Gem Screener has two
rows (`/gem-screener` 177 people, `/gem-screener/app` 162): one product, people not double-counted. Mockup: `app.js` (`renderPortfolio`,
`renderProdPanel`), `portfolio.js` (`CO.apps`, `CO.appFees`, `CO.REFERRAL`, `CO.prodLogo`, `CO.readLogo`), `style.css` (`.pf`, `.pflogo`, `.pfp`,
`.pfwhere`). The vault's apps follow the referral rule (1,000 ET10 a new user), replacing the placeholder per-visitor rate.

## O. Speed on a weak computer (settled, rules; the plan's window is in item E)

**O1. Drawing: rules for everything new in this spec.** Your performance package (`outbox/company-perf`, branch `company-perf`: `SPEC.md`,
`company-perf.patch`, `request.txt`, the measuring harness) is filed on its own and first; this spec builds on it and changes nothing in it. Every
item above that draws something new obeys its rules:
1. Every new 3D thing reads its quality level from `CO.Q3` (`quality.js`: high / medium / low). On high it looks as drawn here; lower it is drawn cheaper.
2. Below high nothing is built ahead in the background (`CO.Q3.ahead`) and nothing behind another scene: it is built when it is opened.
3. No frosted glass (`backdrop-filter`) over moving 3D: below high an opaque plate instead. This reaches the revenue-share board over the Universe (H),
   the Products panel (N) and the Settings preview (M).
4. New shadows, reflections and passes are drawn less often below high, or not at all (the package's C1 and C2 are the pattern). A paused company's dark
   station (I) is cheaper to draw than a lit one: no halo, no ring.
5. A weak PC is held up by the processor, not the graphics: every new object is one more draw call, so merge. The ten new stations (M) bake into few meshes, as the seven do.
6. Share materials across rooms and stations: one material and one TSL node per look, not per room (the office's load is 70% three.js building shaders:
   113 builds for 70 different shaders, package sections 1 and 7).
7. Build a station once and reuse it (item M, measured): the builder and the Settings preview keep each station's built shape per skin, colour and number of decks
   instead of rebuilding it on every click, and the hidden map's station is not rebuilt while Settings is open; the entry page keeps its six stations.
Our local copy of the mockup does not have the package's patch, nor your fix ET-32470 (the Universe's pixel cap); the measuring harness in
`outbox/company-perf/harness` (`perf.py`, `batch.py`) is the way to measure any of this.

**O2 moved to item E**: the Max 5x window and the countdown to the next pass pull against each other, so they are one item there, with the choice left to you.

## P. The Universe's new look: orbits as lanes of light-dust, a plate for a few, the entry page the same (settled, drawn)

The live Universe draws the orbits as glowing rings. The mockup's Universe has a new look, binding like every item marked *drawn* (the owner, 2026-10-23:
*"ty prstence se mi moc nelibi ... vymysli to nejak top"*, then *"neni tam tech prstencu moc?"*; for the entry page *"uprav ty prstence i na uvodni strane"*):
- **The orbits are lanes of light-dust, not rings.** No line is drawn on the map and no small rings round the sun. Three of the seven orbits (the 2nd, 5th and 7th)
  are streams of drifting dust: a fine thread in broken arcs, thick and thin, a dim haze, now and then a bright star, bent a little off their circles and
  tinted by distance from the sun (white-gold, mint, cyan, blue); the other four are only a faint drift. The stations ride all seven. Under them a soft dust plane
  (written per pixel with its own dither, so zooming in shows no diagonal lines), and the stars of light that ride the orbits carry a tail. Nothing is a closed
  circle and everything moves slowly. The small ring under each station is unchanged; a swarm of embers round the sun was drawn and taken out (*"smazal bych ty
  svitici zlute kulicky"*). All of it runs on the graphics card, so it costs the processor nothing (the mockup keeps 144 Hz also on the weak-GPU setting).
  Compare in the mockup: `?orbits=lines` is the old rings, `?orbits=none` the bare plane; code: `u3d.js`, `dustLane` and `dustMesh`.
- **Names on the map: a plate only for a few.** The dark riveted plate (item L's plate) shows for Cymetica, the owner's company, every one of Cymetica's own products,
  land of the owner's, the ten companies that earn most (the revenue share's ranking, where there is room on the screen) and the one under the pointer; every other
  company has none and its tooltip names it, so a hundred companies are ten plates. A plate carries its place in the ranking as a quiet number in the name's
  line (10 px, grey; the first three in the board's green, cyan and blue as type only, no box).
- **The entry page (`start.html`) has the same space and the same lanes.** On the right Cymetica's sun as the Universe has it, two orbits of dust lanes (the outer one
  paler and flowing against the companies' way) with six companies on them, nose first, in the office's own sky (its navy, nebulae and a sparse sprinkle of dots, not a
  black void); the *Start a company* tile shows a room turning and *Explore the Universe* the same map seen from above, live. Nothing pulses.
- The first look of the map, standing further back with the board over open space, is item H.

## Q. Promo Market's building as the mockup draws it: the PROMO airship and its hologram banner (settled, drawn)

The Promo Market stands on Orbit 5 · slot 3 (ET-32484). The live build has its billboard cube but **not the PROMO airship**: the live `u3d.js` has no airship at all (read
2026-10-25). The mockup draws it (`u3d.js`, the Promo Market's builder, the airship block; the owner, 2026-10-24: *"kolem promo marketu vrat tu PROMO vzducholod ktera
kolem toho krouzila s nejakym holografickym banerem"*): a white airship circling outside the ad cards, nose first, a lamp on its nose, a lit gondola, a cyan band round
the hull; behind its tail a banner of light, held to the fins by two lines of light, reading *PROMO MARKET* and *EARN USDC · GET USERS*, magenta and amber in turn with
the billboard and flickering as it does (two banners back to back, so it reads from both sides). A lap takes 80 seconds (*an airship is slow*), with a slow bob.
**The colours are magenta (#FF2D95) and amber (#FFB020) exactly as drawn**: the Universe is a game scene, outside the site's palette (the owner's decision of 2026-10-18,
as for the Agent Casino building). The Promo Market's page and panel have their own brief (`outbox/promo-market`); that brief does not mention the airship, so this item is
only the airship.

## What stays as it is

Everything not named above stays as rounds 1 to 3 and your builds have it.
