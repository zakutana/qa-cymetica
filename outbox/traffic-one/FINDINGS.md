# /traffic, /traffic/mine, /app-usage: what does not add up (for the spec)

Read from their own APIs on 2026-11-06 09:26 UTC (snapshot/ in this folder). Each line: the figures, then what is wrong.
Not sent; goes into the one-page Traffic spec when the operator says so.

## Numbers that contradict each other

1. **Unique visitors grew ~10x on 2-5 Nov while arrivals stayed flat.** /traffic, 14 days, per Pacific day:
   arrivals 219 / 186 / 184 / 166, unique visitors 900 / 1,560 / 2,674 / 2,520. Their own definition says every
   visit lands on exactly one page, yet 9,047 unique visitors against 1,926 arrivals. On /app-usage "Usage over time"
   nearly every app (Creator Pages, Crypto Dashboard, Build it Better, Native Perps, AI Funds, Agent League, Agent
   Casino) jumps the same days. One counting change, not traffic. (Nexus on ET-34299: 98 % of these "people" made
   one request and never ran the page's script.)
2. **A whole product has fewer people than one of its own pages.** /traffic/mine, "Whole product, all its pages and
   tools" against the page's Unique: 14 days Team Dump Radar 70 < 71, Agent Casino 300 < 301; 30 days Chart Analyzer
   148 < 149, Airdrop Farmer 28 < 31, Supply Analyzer 27 < 28, Infiltrator 20 < 21. Two identities on one row:
   Unique = hashed IP, whole product = account or browser.
3. **Capital Maximizer: 8 uses by 0 people** (every range). Already filed as #252, FAIL sent.
4. **"Same figure" that is not the same.** /app-usage says Users is "the same figure the Products tab of /company and
   /traffic/mine show". True only on its People tab, and off by one even there (Agent Casino 364 vs 365, Team Dump
   Radar 89 vs 90). The tab shown first is Everyone (people + agents): Agent Casino 424, Gem Screener 464 vs 417.
5. **Two different counts both called AI agents.** /traffic "Unique AI agents" 30 days = 2,787; /app-usage "Outside
   AI agents" 30 days = 1,270. /app-usage drops training and search crawlers, /traffic counts them as agents.
6. **/company Products lists 11 products, /traffic/mine lists 14 apps.** My Agents, Events and Build Usage are apps
   on /traffic/mine and are missing from /company Products.
7. **Events (our ET-32333 on /events) gets the whole Event Cards audience**: whole product 403 people (14 days),
   came back 25 %, #2 on /app-usage, while its own page has 76 unique.

## The same thing counted or cut differently

8. **Four names for "distinct people", two identities**: Unique visitors (/traffic, hashed IP), Unique (/traffic/mine,
   hashed IP), Users (/app-usage), Whole product people (/traffic/mine, /company: account or browser).
9. **Two day cuts**: /traffic and /traffic/mine cut at Pacific midnight, /app-usage, /company products and the season
   at UTC. The same app on the same "day" shows two numbers (Gem Screener 87 vs 63, Nexus confirmed on ET-34299).
10. **Two ways to show today**: /traffic charts end on today's few hours (every line dives to ~0 on the right);
    /app-usage cuts the partial day off.
11. **Three range sets**: /traffic and /traffic/mine 7/14/30/90; /app-usage tables fixed at 30 days; its history
    30/60/90.
12. **Top pages counts arrivals, beside a Unique visitors tile 9x larger.** The 12 rows hold 547 of 1,926 arrivals.
    This is why the operator never understood it: the page puts it under 9,047 people.
13. **Duplicate-looking rows on /app-usage**: Native Perps (/perp) and Perpetual (/perpetual) are two apps; CLOB Order
    Book has no page; the Promo Market product lives at /creator-dashboard while /promo-market is a separate top page.

## Undefined

14. **Bots filtered** (169,157) and **From another page here** have no definition anywhere on the pages.

## Broken behaviour

15. **The range switch takes 3-20 s and shows nothing meanwhile.** Each chip click refetches with `no-store`:
    /api/v1/traffic/public 2.9-18.7 s (two runs), /api/v1/traffic/activity 21 s (7 d), 22 s (14 d), 41 s (30 d),
    **503 after 60 s for 90 days**; /api/v1/traffic/mine 2.5-5.7 s. The chip turns on at once, the old chart stays
    up, then it redraws. In the mock every range is in memory and the switch takes 23-56 ms.
16. **"People per day by page" has no legend** once there are more than 8 pages (`legend: { display: sets.length <= 8 }`
    in traffic_mine.js); ours has 13, so the colours cannot be told apart.
