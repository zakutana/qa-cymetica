# Promo Market: /creator-dashboard as a market that pays only for results, and a creator dashboard you can read

Draft, not filed. The clickable mockup is `outbox/promo-market/index.html` (three pages: `#market`, `#me`, `#profile`),
and the Universe building is in `outbox/company-live/index.html#universe`. **The look of the mockup is binding; the logic
is yours**: where your backend cannot do what is drawn, change the design as little as it takes and name each change
in your BB-SPEC.

Asked by a community member: *"could this handle marketing/socials/sales?"* This is the answer we would like to build:
a company shows its product, locks a budget, and anybody (creators, AI agents, marketing firms) competes to bring it
users, **paid only for results**.

## A. The market, at /creator-dashboard

Today /creator-dashboard is a page of text that sends you to Telegram for a login link. It becomes the market's front
door: anyone can read it without logging in. A creator's own dashboard stays at `/<username>` (part B).

**1. A brief is a product, a budget and what one result is.** Anyone with something on Cymetica may post one: a
company from /company, the owner of a Build it Better app, an outside firm, Cymetica itself. Fields: the product (a
cymetica.com page), the ask (one line, up to 120 characters), **what one result is** (below), the price per result
(USDC or ET10), the hold (14 or 30 days), the budget, how long it runs (7, 14 or 30 days) and whether it takes post
offers (and up to what price). The budget is locked from the poster's balance when the brief opens; what is not spent
returns when it ends. A brief written by a company's department waits for the owner's approval, as every spend does.

**2. What one result is: a new user, never a click.** The poster picks one:
- *new active user*: a new account that uses the product on 3 different days within 14;
- *new funded user*: a new account that deposits $20 or more of its own funds (and, for Agent Tournaments, seats a bot);
- *new paying user*: a new account that starts a paid plan and keeps it 30 days.

**3. The rules that make a result cheaper to earn than to fake.** Checked by the platform for every result, before
anything is paid. These are requirements; how each is measured is yours.
- *A new person*: a first account, first visit through the promoter's link, within 7 days.
- *One person, one result*: device, network, wallet and phone are matched across every result.
- *A real action*: the brief's own (above).
- *Proof of person*: a Telegram account or a wallet with on-chain history, one per result.
- *Held, then paid*: 14 or 30 days in escrow, clawed back if it turns out fake. Self-referrals and wallets the
  promoter funded never count.
- *Promoters stake*: AI agents and new promoters stake ET10 to take a brief; a farmed result burns the stake.

**4. Taking a brief is one click.** The taker gets a tracked link (`cymetica.com/c/<slug>`) for the brief, and one per
thread it replies in, as reply links work today. No form.

**5. Post offers, beside results.** An influencer quotes a price for one post (platform, the account, its audience
read from the linked account, the price). The poster accepts or declines. An accepted offer is paid from the same
budget once the post has stayed up 7 days (the checker that confirms displayed posts today).

**6. Every brief shows its numbers.** On its card: the price per result, results paid, sign-ups rejected, the hold,
the budget left, post offers. Opened: the funnel (clicks, new accounts, qualified, in hold, paid), the rejected
sign-ups by reason, what counts as a result, the offers and a form to make one.

**7. Cymetica's own programme stays as it is**: 1,000 ET10 + 1,000 ETLP per displayed post, any tool, in the thread
that asks for it. It is shown below the briefs as the per-post programme.

**8. Agents take briefs through the API.** "Promote from your own AI agent" is a prompt to copy, beside today's
"Trade from your own AI agent". New routes (our names, your shapes): `GET /api/v1/promo/briefs`,
`POST /api/v1/promo/briefs`, `POST /api/v1/promo/briefs/{id}/take`, `POST /api/v1/promo/briefs/{id}/offers`,
`GET /api/v1/promo/briefs/{id}/results`. Please add them to /api-docs.

## B. The creator's dashboard, at /<username>

Same data as today, **one screen per tab** instead of one page: the live /mumtaz at 1440 px is 126,515 px tall with
244,627 characters of text (read 2026-10-22). Nothing the live page shows is dropped (our render script checks the
list); paragraphs become tooltips.

- **Today**: the five counters (links, clicks, reads, likes, unique visitors) with their 14-day gains and one 14-day
  chart; *Post this on X today* (the priority post, Copy, Open in X, Mark posted, the reward, the graphic); briefs that
  pay per result; the queues as four counts (Reddit, X, Press, Radar apps); the best pages with a sparkline each.
- **Briefs**: the briefs this creator took, each with its link, its funnel and what it earned; its post offers; the board.
- **Queues**: Reddit, X, Press and Radar apps as one list with the selected thread beside it (Reply with this page,
  Skip, the post kit's rule for that outlet); Press with hours left; Radar with the X, Reddit and Telegram posts to copy.
- **Pages & links**: one table, sortable (clicks, reads, likes, unique, 14 days, top source, replies); a row opens its
  replies and Open page, Download HTML, Also on claude.ai, the tracked link to copy. *Create a page* (tool, headline up
  to 120, why it matters up to 600) and *Track a link* (where it goes, title, kind) are dialogs, with your current fields.
- **Rewards**: paid, pending, unverifiable, failed, what was earned, and each post with its state.
- **A creator's public page** shows the counters, the chart and the table, read only, with "Are you … ? Log in".
- *Start an app and a company* (the Cayman guide) leaves this page: one link.

## C. The Universe at /company: Cymetica's Promo Market building

Cymetica's own building, not a company's or a product: a relay spire on a hex platform, three signal rings turning,
a band carrying the market's numbers, and an emitter sending rings of light out (mockup `u3d.js` `adPromo`, the flat
map in `universe.js`). It stands on **Orbit 5 · slot 3**, bigger than a station and smaller than the sun, and is not
counted among the products in the map's summary line. A click flies to it and opens its panel (`uvpanel.js`): briefs
open, USDC on offer, users paid for; "Paid only for verified new users"; the best paid briefs; the company's own
briefs; **Post a brief** and **Open the market**. The panel reads the same data as the market, so the two never differ.

## D. A Marketing department for /company

`GET /api/v1/company/templates` (2026-10-22) has Development, Design studio, Testing, Testing lab and Trading desk,
and no expert who could market anything. Please add a **Marketing** department template with a **Marketer** expert:
it writes briefs for the company's products and reads what each brought; posting a brief (a spend) waits for the
owner's approval; its computer opens the Promo Market filtered to its own briefs.

## What is a sample

Every brief, its price, budget, funnel, rejections and offers is a **sample** from one model (`make_data.py`, `BRIEFS`);
the prices, holds, the $20 deposit and the stake are **placeholders**, yours to set. Real, as read on 2026-10-22: our
own account's links, rewards and queues (expire76), Mumtaz's public links, the priority post, the Radar apps and the
all-creators measure. The product pictures on the cards are drawn in the mockup.

## Left to you

How escrow, clawback and the stake work; how disputes are handled; the exact anti-fraud measurements; any fee. The
look is not left open.
