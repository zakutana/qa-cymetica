# Why the Gem Screener loads slowly, and what to change (2026-09-30)

Read-only. Measured from Czechia (RTT about 280 ms to `172.234.90.113`, nginx, no CDN in front: no `cf-ray` or `via`). Cold browser load in the built-in browser, then repeated plain GETs.

## What a cold visit does

| Step | When | Cost |
|---|---|---|
| `/gem-screener` (wrapper page) | 0 to 1.5 s | TTFB 1.3 s, 35 kB gzip, then 31 scripts incl. `accounts.google.com/gsi/client` and Google Fonts; DOM interactive at 2.0 s |
| iframe `/gem-screener/app?view=apps` | starts 2.0 s (only after the wrapper's JS runs), done 5.1 s | 2,124 kB raw, 411 kB gzip (gzip only, no brotli); 1,689 kB of it is one inline JSON blob; `Cache-Control: no-cache` + ETag |
| then 3 API calls, only after the app HTML has loaded | `/funds` 5.4 s, `/exchange/pairs` 2.3 s, `/page-extras` 2.3 s (675 kB raw, 134 kB gzip) | everything is on screen at about 10 s cold |
| repeat visit | about 1 s | 304 revalidation plus disk cache |

JSON parsing is not the problem (5 ms for the 1.7 MB blob).

## The cause of the really bad loads: origin stalls

With a reused connection, `/api/v1/gem-screener/status` answered in 0.4 s and then once in **5.25 s**. Other tiny requests: `/funds` TTFB **11.1 s** once (2.8 s and 1.1 s otherwise), `/exchange/pairs` 3.4 s, `/status` 3.0 s. Eight cold GETs each: medians 1.1 to 2.4 s, maxima 3 to 5 s. So a normal request costs about 0.3 to 0.6 s of network plus server time, and every few requests one stalls for 3 to 11 s. A page that makes 4 sequential dependent requests meets one of those nearly every visit. It is the same pattern as the slowness reported under ET-28064 (MSG-0089 to 0092).

## What I would change, in this order

1. **Put a CDN or an nginx cache in front.** `picks`, `ranked`, `coins/{symbol}` and `funds` already send `Cache-Control: public, max-age=60` (and stale-while-revalidate on `funds`), but nothing in front honours it, so every visitor hits the app server. A cache that serves stale during a stall removes most of the 3 to 11 s spikes for public reads.
2. **Find the stall on the origin.** Random multi-second waits on a 2 kB `no-store` route look like worker starvation (a 2 MB page render, the 6-hourly snapshot build or audits sharing workers with live traffic). Their own logs would show which.
3. **Take the 1.7 MB blob out of the HTML.** Serve it as its own versioned URL (`/api/v1/gem-screener/snapshot?v=<generated_at>`, `Cache-Control: public, max-age=31536000, immutable`), with brotli. The shell becomes tens of kB and paints a skeleton at once; a revisit within the 6 hours downloads nothing.
4. **Remove the waterfall.** Start `funds`, `page-extras` and `exchange/pairs` in parallel with the snapshot (a preload in the wrapper's head, or inline bootstrap) instead of after it. Load `page-extras` (134 kB gzip) only when the tab that uses it opens.
5. **Start the app HTML from the wrapper's head** (`<link rel="preload" as="fetch">`) and load Google sign-in and fonts with `async`/`defer`, so the iframe does not wait 2 s for the wrapper's scripts.

Not done: nothing filed. The slowness thread ET-28064 is open with them; this is new evidence for it.
