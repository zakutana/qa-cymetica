# Promo Market v2 — the new coat on today's live data

A clickable mockup of the Promo Market and the creator dashboard as **one app**: two tabs, **Market** and **My dashboard**,
everything on a centred column like the live site. Open `index.html` (any static server; the corner switch shows
**Live data** or **Sample briefs**).

It is built to be copied, not redrawn: **every screen reads the live API's own answer, field names unchanged**.
`data.js` holds what each endpoint answered for expire76 on 2026-10-26 (`snap.py`, our key). In `app.js` all reads go
through one function, `api(path)`; on cymetica.com it becomes `fetch(path).then(r => r.json())` and every render
function stays as it is. `style.css` is self-contained (the site's palette, Archivo Black, JetBrains Mono, Inter).

Colours: cyan `#00cfff`, green `#00ff88`, red `#ff4444`, blue `#3b82f6` and the site's greys. Four tints of those
are used and nothing else: `#33ffa0` (green button hover), `#e8fbff` (the cube's lit core), `#0f1c2e` and `#05070c`
(the loader's ground). `render.py` refuses any other hex.

## What changed against the live build (2026-10-26)

| Live today | v2 |
|---|---|
| Market (`/creator-dashboard?view=market`) and the dashboard (`/expire76`) are two pages with two headers | One app; the top bar switches **Market / My dashboard** |
| The signed-in dashboard sends nothing for 6–8 s (4 reads), then 787 KB: every old tab is rendered and hidden | The shell arrives first with the **loader**; each tab draws from its own read |
| Dark screen with "Loading your products…" | **Loader**: the Promo Market's hologram cube, a real percentage from the reads it waits for (page, `/promo/house`, `/promo/mine`, `/promo/briefs`, the creator's links) |
| Today still has the old blocks stacked | The post of the day first; the agent prompt behind **Agent prompts**; "Why post" and the steps in a fold |
| Pages & links: 5,913 px of nested blocks | **One sortable table**; a row opens the links under it |
| My products: plain cards, 5 of 13 with another product's picture | Each product its own picture (`art/`, 4 new: Events, Airdrop Farmer, Build it Better hub, Usage; Agent Tournaments uses `casino.svg`) |
| "See the Promo Market" in visited purple | Gone: the Market is a tab |
| Post a brief: a popup you scroll | **A page that fits one 1080 screen**: product and pay · materials · the card as promoters see it |
| No brief detail | **The brief's own page**: spent, visitors, new visitors, new users, posts, by day, click → user funnel, promoters with Pay, where visitors came from, not counted with reasons, materials used, quotes |

## Screen → endpoint → fields

| Screen | Reads | Fields used |
|---|---|---|
| Market hero, stats | `GET /api/v1/promo/briefs` | `stats.up_for_grabs_usdc`, `open_briefs`, `top_per_user_usdc`, `top_per_user_name`, `as_of` |
| Brief card | `GET /api/v1/promo/briefs` | `briefs[].name, path, url, say_line, up_for_grabs_usdc, per_post_usdc, per_user_usdc, per_visitor_usdc, days_left` + **`materials`** (new) |
| Brief drawer (promoter) | same + `POST …/briefs/{id}/take`, `POST …/posts` | `budget_usdc`, `owner_funds.checked_at`, `tracked_url` |
| How counted | `GET /api/v1/promo/how-counted` | `rules[]`, `not_counted_reasons` |
| My products | `GET /api/v1/promo/mine` | `products.products[].name, path, url, issue_id, traffic_30d{visitors,views,uses}, brief`, `totals`, `series`, `payouts`, `day_labels`, `days_choices`, `min_budget_usdc` |
| Briefs I took | `GET /api/v1/promo/mine` | `taken.takes[]`, `earned_usdc` |
| Post a brief | `POST /api/v1/promo/briefs` (`BriefIn`) | `product_path, per_post_usdc, per_user_usdc, per_visitor_usdc, budget_usdc, days, say_line` + **`materials`** (new) |
| A brief's own page | `GET /api/v1/promo/briefs/{id}/results`, `PATCH …/briefs/{id}`, `/payouts/preview`, `/payouts/approve`, `…/quotes/{id}` | `promoters, visitors_14d, visitors_by_day, new_users{counted,checking,not_counted}, new_visitors{counted,held,not_counted,not_counted_by_reason}, posts, spent_usdc` + **new** below |
| Today | `GET /api/v1/creator/expire76/links`, `GET /api/v1/creator/posts` | `summary{links,clicks,reads,likes,unique_visitors,likes_excluded,likes_correction}`, `links[].series`, `posts[]`, `daily_cap`, `rule`; the post of the day as the page has it |
| Queues | `GET /api/v1/creator/reddit-leads`, `…/twitter-leads`, `…/channel-posts` | `leads[]` (subreddit/group, title, body, relevance, tool_name, posted_at), `artifacts[]` (the page picker), `targets[]` (Telegram, Discord) |
| Journalists | `GET /api/v1/creator/journalist-requests` | `stats{open,open_all_topics,pitched,published}`, `requests[]` |
| Kits | `GET /api/v1/creator/post-kit` | `kit.hashtags`, `kit.{x,reddit,telegram,discord}.rule`, `playbook[]` |
| Pages & links | `GET /api/v1/creator/expire76/links` | `links[].title, kind, slug, clicks, reads, likes, unique_visitors, last_activity, top_referrers, children[]` |
| Rewards | `GET /api/v1/creator/rewards` | `summary{paid,unverifiable,pending,et10,etlp,per_post}`, `recent[]` |
| Radar apps, Agent key, Start an app and a company | the page's own texts | as the live page shows them (`page.json`, read 2026-10-26; the queue prompt on Agent key was read 2026-10-22) |

## New fields this needs (nothing else is new)

* **Materials on a brief.** `POST /api/v1/promo/uploads` (multipart, image or video, up to 50 MB) → `{file_id, url, size}`.
  `BriefIn.materials: [{kind: "image"|"video"|"text"|"link", title, file_id?, body?, url?}]`; every brief object
  carries `materials[]` (`kind, title, url, size, body`). The promoter downloads or copies them from the brief.
* **On `…/results`:** `clicks` (clicks on the promoters' links), `users_by_day` (beside `visitors_by_day`),
  `sources: [[referrer, visitors]]`, `by_promoter: [{slug, posts, visitors, new_visitors, new_users, earned_usdc, paid}]`,
  `materials_used: [[title, promoters]]`, and the quotes (`audience_url, audience_size, price_usdc, status`).

## The sample briefs

Today no brief is open, so the switch in the corner loads five sample briefs (four on expire76's own products, one
on Safe Launch Check). Every figure comes from one model in `make_data.py`: spent = posts × per post + users × per user
+ new visitors × per new visitor; the promoters' rows add up to the brief, and the market's total to its briefs.

## Files

`index.html`, `style.css`, `app.js` (the app) · `data.js` (written by `make_data.py` from `snap/` and `page.json`) ·
`art/*.svg` (`art.py`) · `render.py` (palette scan, everything the live page shows still present, no overflow, Post a
brief fits 1080, screenshots) · `snap.py` (reads the live answers; `snap/` and `shots/` stay out of git).
