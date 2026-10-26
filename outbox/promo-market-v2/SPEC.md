# Promo Market v2 — build spec

**What is binding: the look of every screen, exactly.** The clickable mockup (`index.html` with `style.css` and
`app.js` beside it) and pictures 1–17 (`build-it-better/pictures/`) are the design. Every size, colour, font, radius,
shadow, spacing, order and animation in `style.css` is part of it. Build it so that each screen, opened at 1920 × 1080,
looks like its picture.

**What does not change: the functionality.** Every route, endpoint, field, rule, check, count, flow, button action and
text of today's Promo Market (`/creator-dashboard?view=market`) and creator dashboard (`/<username>`) stays exactly as
it is. This request moves them into the new look. The only new functionality is on the **brief** (section 11).

**How to build it so it matches.** Copy `style.css` as it is (it uses the site's own palette and fonts only). Each
screen is one render function in `app.js` that reads your live endpoint's own answer with its field names unchanged:
`data.js` holds what those endpoints answered for expire76 on 2026-10-26, keyed by path, and `api(path)` reads it.
On cymetica.com, `api(path)` becomes `fetch(path).then(r => r.json())` and the renders stay as they are.
`README.md` lists screen → endpoint → fields.

## 1. Tokens

| Token | Value |
|---|---|
| Ground | `#0a0e17`, deeper `#06090f`; cards `#0d1520` → `#111a28`; lines `#16233a`, `#1e3050` |
| Text | `#e6edf7`, `#a9b8cc`, `#7f93ad` |
| Colours | cyan `#00cfff` (accent), green `#00ff88` (money, primary buttons, positive), red `#ff4444` (negative, deadlines), blue `#3b82f6`. Tints: `#33ffa0` (green hover), `#e8fbff` (cube light), `#0f1c2e`, `#05070c` (loader ground). Nothing else |
| Fonts | Archivo Black (headings, big figures), JetBrains Mono (numbers, labels, chips), Inter (reading) |
| Column | content centred, max 1400 px, 32 px side padding |
| Radii | cards 16–18, tiles 14, buttons 10 (small 8, large 12), chips round |
| Buttons | 40 px (small 32, large 50); primary green with its glow `0 8px 26px rgba(0,255,136,.28)`; secondary cyan outline; ghost |
| Explanations | in a tooltip (`i`) or a fold, never a paragraph on the page |

## 2. One app (all pictures)

`/creator-dashboard` and `/<username>` are one page: a sticky top bar (66 px) with the mark and **Promo Market**, two
tabs **Market | My dashboard**, the live chip, **Post a brief** (green) and the account. No second header, no link in
the browser's visited purple. What a signed-out visitor and another creator's visitor see stays as today, in the new look.

## 3. Speed and the loader (picture 10)

The page sends its shell at once and draws each tab from its own read (today, signed in, `/expire76` sends nothing
for 6–8 s, then 787 KB with every old tab rendered and hidden). While the reads come back the loader covers the page:
the cube (150), the percentage (Archivo Black 54 px) that moves only as reads return and never reaches 100 early, the
read it waits for in capitals, a 2 px bar, and one chip per read (page, the market, your products, the briefs, your
visitors) turning green as each returns. Each face of the cube lights as its read returns. It fades out in 0.7 s.

## 4. The cube: the Promo Market's mark

Glass, standing on one corner, in the page's colours. Exactly as `style.css` `.holo`:
- six faces, each a screen showing a product's page shot, four of six lit at a time, changing every 2.4 s;
- edges are light, not lines: no hairline, a rim glow fading inward and outward; corners nearly square; only the faces
  turned to the viewer are drawn (no back faces showing through, no cube inside it);
- it does not spin: it sways ±35° over 18 s and floats up and down over 6.5 s; faint scan lines, a sheen passing now
  and then, a soft light inside, a glow breathing out, a pool of light under it and a soft beam;
- sizes: hero 150, empty market 54, loader 150, the mark in the header and on the loader 16 (no screens, no light).

## 5. Market (pictures 1, 2)

1. Hero, two columns: chip **PROMO MARKET** with the live dot; the headline in Archivo Black 64 px, its second line
   **Get paid in USDC.** in solid green; the lead 17 px; three large buttons (**Earn: take a brief** green,
   **Promote my product** cyan, **From your AI agent** ghost); under them **one row of three tiles**: USDC up for
   grabs (green), Open briefs, Top pay per new user. The cube on the right, and under it one large green button
   **See in the Universe ↗** to `https://cymetica.com/company/app#universe`, where the Promo Market's building stands.
2. Four steps in one row, round numbered badges, joined by short lines.
3. **Open briefs** with the count and the three sorts (Most up for grabs, Best per new user, Ending soon); three cards
   a row. With none open: the empty state (small cube, one line, **Post the first brief**).
4. Two cards side by side: For builders (three numbered lines, Post a brief, the wallet note) and For AI agents (the
   prompt, Copy prompt).
5. Two folds: how a new user and a new visitor are counted (your seven rules as tiles), and what this does not do yet.

**The brief card:** the product's page shot 150 px high with the materials count and days left on it; name (19 px)
and link; the owner's line; **Up for grabs** in green 30 px; only the pays the brief offers, one tile each (per post,
per new user, per new visitor); a full-width green **Take it**.

## 6. A brief, opened (picture 3)

A drawer from the right, 560 px: the page shot; days left and the funds check; name, link, the owner's line; Up for
grabs of the budget, spent so far as a bar; the pay tiles; **Take it · get my link**, after which the promoter's link
with Copy and **Register post**; **Materials to post** (pictures and video to download, texts and links to copy);
the counting rules in a fold.

## 7. My dashboard (pictures 4, 7–9, 11–17)

A left rail 252 px beside the content: the account; MY PRODUCTS: My products; PROMOTE: Today, Briefs I took, Queues,
Journalists, Radar apps, Kits, Pages & links, Rewards, Agent key, Start an app and a company (counts as drawn); links
Promo Market, Your public page, Agent prompts; the earned box. Each tab is one screen with its title (34 px):
- **My products (4):** four tiles, the visitors chart, one card per app with its page shot, Live badge while a brief
  runs, 30-day visitors · views · uses, then either Create brief or the brief's three numbers and Open the brief; the
  wallet note at the bottom.
- **Today (7):** five tiles; the post of the day with its graphic and actions; the 14-day chart beside *Wrote your own
  post?*; the all-creators measure; Why post and the steps in a fold.
- **Briefs I took (11), Queues (8)** as a list with the thread beside it, one screen high, **Journalists (14)** the
  same way, **Radar apps (12), Kits (13), Pages & links (9)** as one sortable table whose rows open their links,
  **Rewards (15), Agent key (16)** with the three agent prompts, **Start an app and a company (17)** as ten steps.

## 8. Post a brief (picture 5)

A page, not a popup, that fits one 1080 screen without scrolling: three columns (1 : 1.05 : 0.92).
1. **Product and pay:** the products as rows with their page shots; per post, per new user, per new visitor, each
   switched on or off; budget with 50/100/250/500; 7/14/30 days; the owner's line (280).
2. **Materials for promoters:** drop pictures or a video; the list, first the **picture for posts** (the page shot by
   default); ready-made texts; links; Add a text, Add a link.
3. **As promoters will see it:** the card, live; what the budget buys; *One budget for every promoter who takes it:
   once it is spent, nothing more is counted or owed*; the funds note; **Post the brief**, Cancel.

## 9. A brief's own page (picture 6)

The owner's: page shot, name, status and days left, funds covered, the prices, the owner's line, Pause / Add budget /
Edit prices / Share; six tiles (spent of budget, up for grabs, visitors, new visitors, new users, posts paid);
visitors by day beside *from click to user*; promoters with Pay beside where visitors came from and what was not
counted with the reasons; materials used beside the quotes.

## 10. Words

English, as drawn; the labels and texts are your live page's own. *One budget for every promoter* is said on the card
(Up for grabs tooltip), on Post a brief and on the brief's page, as your `budget_spent` rule already works.

## 11. The only new functionality: the brief

- **Materials on a brief:** an upload route (`POST /api/v1/promo/uploads`, image or video up to 50 MB →
  `{file_id, url, size}`); `BriefIn.materials: [{kind, title, file_id?, body?, url?}]`; every brief carries
  `materials[]`. The first is the picture for posts, the product's page shot by default.
- **The brief's own page:** on `/api/v1/promo/briefs/{id}/results` add `clicks`, `users_by_day`, `sources`,
  `by_promoter` (slug, posts, visitors, new visitors, new users, earned, paid), `materials_used`.
- **Page shots:** add `preview_url` (Build it Better's) to the products in `promo/mine` and the briefs in `promo/briefs`.

## 12. How we check it

Each screen at 1920 × 1080, signed in, against its picture: layout, sizes, colours, the cube, the page shots, one
screen per tab, Post a brief without scrolling, the loader within the first second. Any visible difference from the
picture is a difference to fix. Functionality is checked to be unchanged.
