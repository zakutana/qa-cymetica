# ET-34607 (Traffic) — check of the live page after Cymetica's answer of 11 Nov (REPLY-0282)

Read 2026-11-11 08:03 to 09:00 UTC on https://cymetica.com/traffic: anonymous Chromium at 1440 and 390 px, GET with our key on `public`, `activity`, `app-usage`, `mine` and `company/products` for 7, 14, 30, 90 days, and the HTML of the page. The signed-in pane had lost its session at first, so Your apps, the green "yours" mark and People per day by page were first read from `traffic/mine`; after the operator logged it in they were read on the page too (see lines 1 and 5). Nothing was written to their platform. The verdict stays the pass of 10 Nov (BB-0052).

**Score: 10 of 12 pass, 1 partly, 1 fail** (10 Nov: 9 / 2 / 1).

| # | Done when | Result | Evidence |
|---|---|---|---|
| 1 | Basic, Advanced, old routes land on it | **pass** | Page renders; "FOMO Radar" now names the row in Apps (was "Crypto Radars"); `mine` has 13 apps and no Traffic, Events, My Agents or Build Usage (Pitch Cards is new). Signed in (the operator logged the pane in, 11 Nov): Your apps lists the same 13 apps; 8 rows of the 40-row Apps table carry the green name and "yours" tag (rgb(0, 255, 136)) and every own app that has an Apps row is marked; Your pages and Users you brought heads all have a `?` |
| 2 | Same columns, Came back and Uses on every row | **pass** | `mine` apps all have Came back except Infiltrator at 7 days (0 people) |
| 3 | Every tile and column head has a tooltip, hover and tap | **pass** | 13 and 21 `?` tested at 1440 and 390 px, Basic and Advanced: all shown in full, none clipped, no head or tile without one. App head and names now left-aligned (#325 fixed live: head and cells `text-align: left`, # head on one line, 36 px high) |
| 4 | Loading within 100 ms, charts within 2 s, activity 90 d 200 | **partly** | Loading at 1 ms. Panels redraw in 0.4 to 2.1 s for 30 and 90 days, but Apps and App totals took 3.3 s at 7 days (one sample). Cold `traffic/mine` (first read, in order): 7 d 2.8 s, 14 d 7.2 s, 30 d 7.3 s, 90 d 10.7 s, all 200 (10 Nov: 15 s, 503, 503). Their "4 to 8 s" is right except at 90 days |
| 5 | Legend with 13 pages | **pass** | Signed in: `tm-stack` has 13 datasets, `legend.display` true; no Traffic, Events, My Agents or Build Usage. Two entries are shipped feature pages named with their whole request title ("Memecoin Mining" — budget-funded autonomous AI launchpad ..., "Info tooltips for /flows page boxes ...") |
| 6 | Unique visitors and arrivals move together or the chart marks the day | **pass** | The mark landed: 90 days shows a red point on 12 Oct and a note ("more than 2.5 times their usual ratio of 1.2 people per arrival: 2026-10-12 (985 people, 138 arrivals)"). 14 and 30 days: no day over the 2.5 limit (11 Nov data: ratio up to 2.5) |
| 7 | No product below one of its pages | **pass** | None at 7, 14, 30, 90 days |
| 8 | People tab = Products tab for the same app and period | **pass** | `company/products?days=D` now answers `"days": D` and equals Your apps for all 13 apps at 7, 14, 30, 90 (30 days: Chart Analyzer 105 against 105, Agent Casino 209, Gem Screener 152). One 1-person difference (Chart Analyzer 9 against 8 at 7 days, People tab) did not repeat in two later reads. `tz` is not echoed in the answer, and Chart Analyzer reads 22 for `tz=pacific`, `tz=utc` and none, so the parameter could not be tested |
| 9 | The two AI-agent counts carry different names | **pass** | Unchanged |
| 10 | /company Products and Your apps list the same apps; Events; Capital Maximizer | **pass** | 13 and 13 names, identical, at all four ranges; no app has uses without people |
| 11 | One day cut stated, today on every chart or none | **fail** | The page is back on Pacific: it requests `traffic/public?days=14&tz=pacific` and `activity?...&tz=pacific` (10 Nov: `tz=utc`), the footer says "Days end at midnight Pacific time (PT) ... The Apps section is the one exception: its figures come from daily records cut at midnight UTC", the tile reads "ARRIVALS TODAY (PACIFIC)", and the "One day cut ... UTC" sentence is gone from the HTML → **#342** |
| 12 | Each app once in Apps | **pass** | 40 rows, no repeated name |

## Cymetica's five answers against what we read

1. One name: confirmed live (Apps shows FOMO Radar).
2. Whose app: confirmed in the API and on the page signed in (Your apps, Apps marks, People per day by page); Products without Traffic is from the API, the /company page itself was not opened.
3. App column left-aligned: confirmed live, although the answer says "next deploy".
4. Products `days` and `tz`: `days` confirmed live; the Pacific/UTC explanation of the old difference is theirs, and Products now equals Your apps; `tz` not testable.
5. Cold read: 2.8 to 10.7 s, no 503 in four reads; confirmed better, not "4 to 8 s" at 90 days.
6. The chart mark: confirmed at 90 days.

## What the page did not say

The answer talks about the cut only for Products. The page's own cut went the other way (#342); the answer does not mention it.
