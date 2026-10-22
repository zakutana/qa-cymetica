# Build a Company, round 3: our two products on the Universe, with a panel

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

## What stays as it is

Everything not named above stays as the second brief and your build have it.
