# ET-28606, the points still open (2026-10-01, live app)

Board, read 15:49 UTC: stage shipped 07:11 UTC, `verdict: "pass"`, `verdict_note: null`. The record does not say who set the verdict; our journal has no event for it.
Page snapshot read: generated 2026-10-01 13:42:57 UTC, i.e. after the 12:40 refresh and 6.5 h after the ship.

| Point | Result | What was read |
|---|---|---|
| 35 altseason universe has no asset priced at a currency unit | **fail** | `altseason.alt50` (50 ids) still holds `figure-heloc`, `hashnote-usyc`, `spiko-amundi-overnight-swap-fund-eur`. Price / 30-day change at our 08:31 UTC tick: 1.027 / +2.52 %, 1.14 / +0.27 %, 1.15 / −2.32 %. 6 % of the universe, as the spec says. |
| 45 caution is orange everywhere | **fail** | `--caution`, `--caution-line` and `--warn` are all `#3b82f6` (blue); the Degen meter zone 4 to 6 is blue on Pharaoh. Their team is holding orange for ET-28688. |
| 17 / 40 one phase, one colour | holds on what was read | One style per phase class across the 76 Apps rows; Ignition is the same filled `#3b82f6` in the table and in the Pharaoh detail stepper. Other phases not opened in a detail. |
| 390 px | holds | No horizontal overflow on Top Picks, Apps, Chains, Sectors, Legend (scrollWidth 390 = viewport). |
| 25 report status icon | partly | "Ready" shows the green icon on Pharaoh. "Not researched" and "outdated" not looked at. |
| 37 Sectors | partly | Table columns are Stage, Theme, 1M, 3M, Talked about, Fundamentals, Growth 3M. The quadrant chart not looked at. |
| 24, 21, 42 | not checked | At 2000 px the page fills the width (main 1985 px); no revenue chart found on Top Picks to measure. |

Speed while reading (shell, so support only): 15:47 UTC board 200 in 4.5 s; 15:49 UTC `GET /api/v1/build-it-better/requests/ET-28606` 200 in 6.4 s (3.7 KB, first byte 6.4 s) -- after their stated 15:41 recovery.
