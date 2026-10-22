# Build a Company, round 3: our two products on the Universe, a /clear, and two fixes

Draft, not filed (it waits for Cymetica's answer on round 2; see NEXT.md). The clickable mockup is `outbox/company-live`:
open `index.html?ads#universe` (the `?ads` is what shows the two products; round 2 held them back). As before, **the look
of the mockup is binding; the logic is yours**: where your backend cannot do what is drawn, change the design as little as
it takes and name each change in your BB-SPEC.

## A. Our two products stand on two bought slots

**1. Two of the 36 slots are taken by us.** The owner bought them: **Gem Screener on Orbit 2 · slot 4** and **Agent Casino on
Orbit 4 · slot 2**. Each stands where its slot stood, turns with its orbit, and carries a plate: AD, the product's name.
The two slots are no longer for sale. The mockup draws them bigger than a station and smaller than the sun
(`u3d.js` adGem, adCasino); a free slot that would stand inside one's reach is left out. Where 3D cannot start, the flat map
draws the same (`universe.js`).

**2. A click flies to the product and opens its panel.** The camera flies to the building (as it does to a station), the
building stays in the middle of what is left of the stage, and a panel slides in over the right side, 420 px wide. The
× or Esc closes it and the camera flies back to the whole map. A click on the other product while one is open changes
the panel. A narrow stage (under 760 px) puts the panel over its lower part. Mockup: `uvpanel.js`, `uvpanel.css`, `app.js`
(`openAd`, `closeAd`), and `flyTo(id, done, ms, shiftPx)` in `u3d.js` and `universe.js`.

## B. What each panel shows

Numbers first; an explanation is a tooltip. **Both panels are live**: the mockup reads a copy dated 2026-10-22 (`uv-snap.js`,
because your APIs send no CORS header to another origin), the build reads your own data.

**3. Gem Screener: the Gem Tier List, as its page has it.** The rows S, A, B, C, D, F over the vetted apps with $100K+
revenue in 30 days, **the same rule and the same numbers as the Gem Screener's Start view** (`tierModel` there): S is the
Degen picks, A to F by upside, each app in one row, a row at most two lines with a "+N" tile for the rest, the logo, the
symbol and (S, A, B) the upside under it, a tooltip with name, market cap and revenue. Above it: "79 vetted apps · $100K+
revenue in 30 days · ranked by upside" and the segment bar. Below it: a green **Visit Gem Screener** button to
`/gem-screener/app`. The panel must never show a different number from the page, so please draw it from the same source.

**4. Agent Casino: how busy it is.** Three numbers (**agents trading**, **live tables**, **open seats**), one line with the
money **in the pots** (ET10 and USDC apart, and PAPER while the tables are paper), **one live table's ranking** (the table with
the most in its pot; rank, bot, return; the first six, then "+N more" to its page), the **open tables** as chips that open
each table, and a cyan **Go play** button to `/agent-tournaments`. Source: `GET /api/v1/agent-tournaments/lobby` (`agents_trading`,
`live_tables`, `open_seats`, `in_pots_et10`, `in_pots_usdc`, the running table's `seats`, `open_tables`). When no table is running the
panel says so and still shows the open ones.

## C. Fixes, a command and a correction

**5. The Read button on an approval does nothing** (read on the live build, 2026-10-22: on a Headquarters card and on the
Approvals tab, `/static/company/app.js?v=6ad98487`). The click is caught, but `readModal(id)` finds nothing: it looks the
approval up with `x.id === id`, where `id` is the card's `data-id` (always text). If the approval's id is a number, the
comparison is false and the function returns without opening anything; that is what we read in the code (we cannot call `/office`
as the owner here, so please confirm the type). Your own `decide(id, how)` already compares `String(x.id) === String(id)` and `live.js`
uses `==`, which fits Approve and Reject working while only Read is dead. After the fix a click opens
the approval's full text with Approve, Reject and Close (the mockup's `readModal` does, and is the design).

**6. `/clear` in the chat with NEXUS.** Typing `/clear` on its own and sending it empties the chat window, as `/clear` does in
Claude Code. **It empties what the owner sees, not what the account holds**: the messages stay stored, so the Supervisor's weekly audit
(and anything NEXUS reads of the conversation) still sees all of them, and the command is not sent to NEXUS and costs no turn. In the
window a thin line stays where it happened: *Cleared 07:42 · history kept for the audit* (tooltip: what `/clear` does). New messages
go on below it; a reload keeps the window cleared, so the line and the cut-off must be stored on the account (one timestamp). The box's
placeholder names it: *Message NEXUS… (Ctrl+V a screenshot · /clear)*. Mockup: `app.js` (`sendMessage`, `chatHTML`), `sim.js` (`act.clear`).

**7. Correction to round 2: companies stay on the map.** Round 2 said *No companies on the map; land instead*. **That was our
mistake and is withdrawn**: the Universe must keep showing every company that exists, private and public, as the first build did,
and the land comes in addition to them. A company stands as its station on an orbit as in round 1 (a public one opens its visit,
a private one its card); free slots and the owner's own land stand between them. The summary line reads *N companies · N free slots · N
yours* (and *N ads*). Where the first build drew it is the reference for the companies (mockup `outbox/company-live` before commit
`e5921b39`, which removed them); this round's mockup shows the land and the two products. The mockup will carry both once you have
answered, so that the two can be seen together.

**8. The Products tab shows every build, not every product** (the owner's screenshot of the live tab, 2026-10-22). It shows 32
cards for about ten products: Gem Screener 11 (six on `/gem-screener` with identical numbers, four on `/gem-screener/app` with zeros,
one marked *closed*), Chart Analyzer 5, Agent Tournaments 5 (two of them titled with the request's own words, *Add
https://cymetica.com/agent-tournaments to main menu*), Build a Company 4 (one *closed*), Supply Analyzer 2, Team Dump Radar 2, Infiltrator,
My Agents and Events. Each Build it Better request that touched a page became a card of its own. Round 2 asked for *every product the
owner owns*, and a product is one page, not one request: **one card per product**, named by the product, with its numbers once; the
builds that made it can be listed inside it (a small "6 builds" count that opens them). A request that was closed or never shipped is
not a product and has no card. **The totals are wrong for the same reason**: the strip reads 32 products, 2,970 visitors, 4,016 uses and
31 likes, which is exactly the cards added up (243 visitors six times, 206 five times, and so on), where the products' own numbers are about
599 visitors, 822 uses and 8 likes (read off the screenshot): a page's visitors must not be counted once for every request that touched
it. The mockup's Products tab draws it as meant: one card per product.

**9. Every product says whose it is.** Wherever a product is shown (a Products card, a product's panel on the map, a list of what a
company owns) it names the company that owns it: *by Moonshot Labs*, a link to the company when it is public, plain text when it is private.
The mockup draws it as one small line under the product's name on a Products card and in the products' panel (*by Cymetica* on our two).

**10. A click on a company flies to it and opens its panel**, as a click on a product does (item 2; round 1 flew to a public company
and went straight into its visit). The camera flies to the station, the station stays in the middle of what is left of the stage, and a
panel slides in on the right, 420 px, with the same × and Esc. It shows the basics, numbers first: the company's name, its owner (@name), status and
days on Cymetica, its mission, how many departments and how many are working now, what it has earned in ET10 (a public company), and
**the products it owns** (name, page, and its visitors in 30 days), each a link to the product's page. A **public** company has a
*Look inside* button to its visit; a **private** one shows what its card showed in round 1 (name, station, mission) and its products, and
no button. (The products of a private company are public pages already, and item 9 names their owner, so listing them leaks nothing the
page does not; if you see a reason to hide them, say so.) The panel is the same one as the products', so one component draws all
three. The company's own station opens its office as before.

## What stays as it is

Everything not named above stays as the second brief and your build have it.
