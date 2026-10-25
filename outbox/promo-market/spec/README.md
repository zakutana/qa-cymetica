# Promo Market: everything the look is built from

The Promo Market is Cymetica's marketing hit, so it has to look **premium**: dark, glowing, confident, drawn to the
last pixel, not a list of grey boxes. Everything below is in this repository at the pinned commit; nothing needs to be
asked for.

## The pictures (`*.webp`, 1440 px wide, in order)

1 market · 2 one brief · 3 My products · 4 one product · 5 Post a brief · 6 Promote: Queues (Reddit, X, Telegram,
Discord) · 7 Universe panel · 8 Universe building close up · 9 Universe map · 10 Promote: Kits · 11 Promote: Today ·
12 Promote: Briefs I took · 13 Promote: Pages & links · 14 Promote: Rewards · 15 Promote: Journalists · 16 Promote:
Radar apps.

## The clickable mockup (open `index.html`, then use the top bar and `#market`, `#me/products`, `#me/today`, …)

- `../index.html`, `../style.css` (every size, colour and spacing below is in it), `../app.js` (every screen, state and
  interaction), `../data.js` (the sample data the screens read).
- The Universe building: `../../company-live/u3d.js` (`adPromo`, the hologram, the band, the searchlights), the flat
  fallback in `../../company-live/universe.js`, the panel in `../../company-live/uvpanel.js` and `uvpanel.css`.

## The product pictures on cards (`art/*.svg`, 720 x 300)

`gem`, `casino`, `chart`, `supply`, `company`, `launch`, `nexus`, `team`, `infil`, `agents`: one finished picture per
product, drawn in the palette (a mark in a rounded square, the product's address, one motif in two of the four colours).
Any other app gets one of the same six motifs (bars, hexagons, candles, orbit, buildings, shield) in its own pair of
colours. The same SVG is the header of a card on the market, of a product card in My products and of a brief's drawer.

## Fonts (already loaded by the site)

Archivo Black for headings and big figures, JetBrains Mono for numbers, labels and links, Inter for reading text.

## Colours

Page `#0a0e17` with a soft cyan glow top-left and a faint green one right (radial gradients, `fixed`); cards
`#111a28` to `#0d1520` (top to bottom) with a `#16233a` hairline; text `#e6edf7` / `#a9b8cc` / `#7f93ad`.
**Cyan `#00cfff`** accent and links, **green `#00ff88`** for money and every primary button (dark text `#06090f`, a green
glow under it: `0 6px 24px rgba(0,255,136,.22)`), **red `#ff4444`** only for what is wrong, **blue `#3b82f6`** for a
second series. No other colour on the pages.
The **Universe building is a game scene, outside the page palette** (the operator, 2026-10-18): its screens are
**magenta `#FF2D95` and amber `#FFB020`** exactly as drawn, with the structure in cyan.

## The measurements that make it read as premium

- Market hero: a chip with a live dot, headline **64 px Archivo Black** in two lines (the second in a green-to-cyan
  gradient), one lead line at 17 px, three buttons (green primary, cyan, ghost, 48 px high); beside it three stat cards
  with a 2 px accent line along the top edge and the figure at **38 px**.
- Tutorial row: four cards, each with a **round gradient number** (cyan to green, 38 px) and a short connector between
  them.
- A brief card: 16 px radius, a **150 px product picture** with the days-left chip over its corner, then the name
  (20 px) and its link in cyan mono, an **Up for grabs block** (green tinted gradient, label in small caps, the figure
  at **30 px** in green), two tiles for per post and per new user (figure 20 px), a **full-width green Take it** (40 px).
  Three cards a row at 1440, 18 px gap; a card lifts 3 px with a thin cyan ring on hover.
- Dashboard: a **248 px left rail** (your name, two groups MY PRODUCTS and PROMOTE with counts, your public page, agent
  prompts, an earnings tile at the bottom), a page title at 34 px, four stat tiles and one chart, then the product cards
  in four columns. No paragraph of explanation on a page: an explanation is a tooltip or sits behind a fold.
- Drawers (a brief, a product) slide in from the right at 540 px over a blurred scrim; forms are modals with a live
  preview of the card beside them.
- Every tab is **one screen**, not a scroll: Queues show a list on the left and the selected thread on the right;
  Journalists and Radar apps are tabs of their own.
