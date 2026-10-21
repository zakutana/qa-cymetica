# Build a Company, round 2: land in the Universe, and fixes after the first build

A follow-up to the first brief (`outbox/company-spec/SPEC.md`, built and live at https://cymetica.com/company/app).
Thank you for taking the design as it was drawn: the 3D office, the Universe, the stations and the entry came over almost
unchanged. This round asks for one new feature and seven fixes, and two things missing from the first build. What is live was read on 2026-10-21 (the pages, and
`GET /api/v1/company/mine`, `/office`, `/creation`, `/company/14/messages` on the account expire76).

The clickable mockup is `outbox/company-live` (open `index.html#universe`; `?visit=101` is the visit view). The pictures
of this round are in `screenshots/`. As before, **the look of the mockup is binding; the logic is yours**: where your
backend cannot do what is drawn, change the design as little as it takes and name each change in your BB-SPEC.

## A. New: the Universe is land for sale, with two ads on it

**1. No companies on the map; land instead** (`screenshots/01`, `02`). Cymetica's sun in the middle and **34 slots** along
the seven orbits (the number is the layout's: each orbit holds as many as its length allows, the places in front of the two ads
left free). A free slot shows only while the owner has turned on **Buy land** (a button beside Create company): a ring
with a plus, dashed. A slot you own is always drawn: a solid green ring, a beam of light and the plate YOUR LAND. Slots
turn with their orbit like the stations did. Where 3D cannot start, the flat map draws the same (design `universe.js`).

**2. Buying a slot** (`03`). A click on a free slot, in Buy land, opens a card: the slot's address (orbit and number), the
price in ET10 and a button. The server takes the ET10 from the owner's balance in the same transaction that records the
slot, and fails closed. **The price is yours to set**: the mockup's 1,000 ET10 is a placeholder (one number). A click on
a free slot with Buy land off does nothing.

**3. At most three slots to an account, for now** (`04`). So nobody buys the whole map. At three, the card says so and offers
no button. The server enforces it; the page only mirrors it. One constant, so it can be raised later.

**4. What a slot is for.** A bought slot is kept on the account (the mockup keeps it in the browser, which is not the
design). Its card says: *Add a building with Build it Better* and links to `/build-it-better`. **Products from Build it Better
will stand on slots later; nothing more is asked of that here.**

**5. Two ads** (`01`). Our two top products stand on the map, **larger than any station and smaller than the sun**: Gem
Screener as a floating cut diamond in its logo's greens, Agent Casino as an orbital chip, a ring station in neon magenta
and violet with a hologram of the Agent Tournaments logo over its mast. Each has a plate with AD over it and opens its live
page in a new tab (`/gem-screener/app?view=apps`, `/agent-tournaments`). The two are a list Cymetica controls, so more ads
can come. The builders are `adGem` and `adCasino` in `design/u3d.js`; they are code, not pictures.

**Not part of this round:** how a visitor finds a public company now that companies do not stand on the map. The visit view
itself stays (`?visit=<id>`, see item 8).

## B. Fixes and what is missing after the first build

Each is something read on the live page on 2026-10-21 against what the design shows. Items 11 and 12 are pages the design has and
the build does not.

**6. NEXUS does not know the Operations room.** On 2026-10-21 at 20:48:55 and again at 20:50:26 (`/company/14/messages`) the
owner asked what Operations does; NEXUS answered that no such department exists and that it had only four. The page has the
Operations room, the Audit tab and a stored audit (`last_audit` id 18), so the answer was wrong about the owner's own company.
NEXUS's context needs the built-in Supervisor, the weekly audit and its findings, so it can say what Operations does and read
the last audit. The same for anything else the page shows that is not a department.

**7. The usage bar says nothing about extra usage** (`08`). The bar reads 100% used, red, "Resets in 4h 35m", while work
goes on. `GET /company/mine` says why: the five-hour window is 3.66 of 1.00 units, the week 6.99 of 6.00, extra usage is on
and **22.50 of the 25.00 USDC monthly cap is spent, 3 turns left**; turns past the plan are paid from the owner's own USDC. The bar
must say that, with the numbers (the design: *on extra usage · 22.50 of 25.00 USDC this month*), and say plainly when it has
run out and work waits.

**8. A public company's visit hides its private tabs** (`05`). **Tasks, Memory, Waits for owner and Audit are not in a visit**, nor
the panel of what waits for the owner. The office, the departments, their charters and the processes stay, read only. This
**replaces section 12 of the first brief**, which said a visitor sees everything inside.

**9. The Vault shows the whole balance** (`06`). It must show all the ET10 and USDC the owner holds on their Cymetica account,
not only what the company earned. Today the tile reads "0 ET10 paid" (`bugs.paid_et10`) while the same `/office` response carries
`vault.et10_balance` = 521,650.54: the number exists and is not shown. There is **no USDC balance in that payload**; please add
one. What the company earned is listed under the balance, by department and by app.

**10. Pictures in the chat with NEXUS** (`07`). Pasting a screenshot (Ctrl+V after a print screen) or picking an image with the
clip puts a small card above the box, with a cross to take it back; at most four, each under 5 MB, PNG or JPEG. It goes with the
message and shows in the thread. NEXUS must be able to read it. Neither is possible today: there is no paste handler and no
file field in the chat.

**11. Experiments exactly as drawn** (`09`, `10`). The live page is a bare list that **cannot be clicked into**: its script has
only two handlers, New experiment and close, so a card does nothing; the card is one narrow column (about 250 px) in which the
title wraps one word to a line, and it shows no return, no line and no bots. The design (first brief section 7;
`design/experiments.html`) has per experiment one big return, a line from start to now, the bots as green and red squares and
the instructions; a click opens it: the bots ranked with return, P&L and trades, Run / Pause, add and remove bots, rename, edit
the instructions; and a New experiment card. It is a scope cut (the design's `experiments.js` is 19.7 KB and `xp.css` 11.4 KB,
the live ones 6.9 and 2.0). Please build the page as drawn.

**12. The Products tab is missing** (`11`). The live tab bar is Headquarters, Tasks, Approvals, Memory, Audit, Processes; the design
has **Products** after Headquarters (first brief section 10). It lists **every product the owner owns**: an app counts as the
owner's when the owner was the first to put it into Build it Better and it did not exist before. Per product: its page, visitors,
uses, views and likes (30 days, as `GET /api/v1/build-it-better/apps/leaderboard` counts them), and what it earned (the rewards
are your rates). Neither the leaderboard (no owner on a row) nor the public request list (only `requester_kind`, no requester)
says whose an app is, so **please add the owner's own list** to the API; the tab reads it.

## What stays as it is

Everything not named above stays as the first brief and your first build have it; this round asks only for what is listed.
