# ET-28606, the points still open (2026-10-01, live app)

Board, read 15:49 UTC: stage shipped 07:11 UTC, `verdict: "pass"`, `verdict_note: null`. The record does not say who set the verdict; our journal has no event for it.
Page snapshot read: generated 2026-10-01 13:42:57 UTC, i.e. after the 12:40 refresh and 6.5 h after the ship. Everything below is read from the live page (DOM, computed styles, the page's own snapshot), 15:3x to 17:2x UTC.

| Point | Result | What was read |
|---|---|---|
| 35 altseason universe has no asset priced at a currency unit | **fail** | `altseason.alt50` (50 ids) still holds `figure-heloc`, `hashnote-usyc`, `spiko-amundi-overnight-swap-fund-eur`. Price / 30-day change at our 08:31 UTC tick: 1.027 / +2.52 %, 1.14 / +0.27 %, 1.15 / −2.32 %. 6 % of the universe, as the spec says. |
| 45 caution is orange everywhere | **fail** | `--caution`, `--caution-line` and `--warn` are all `#3b82f6` (blue); the Degen meter zone 4 to 6 is blue on Pharaoh. Their team is holding orange for ET-28688. |
| 17 / 40 one phase, one colour | holds on what was read | One style per phase class across the 76 Apps rows; Ignition is the same filled `#3b82f6` in the table and in the Pharaoh detail stepper. Other phases not opened in a detail. |
| 24 chart on a wide screen | holds | At 2000 px the page content is 1400 px wide; the legend sits next to the chart (22 px gap) and the lines end 78 px before the chart's right edge. Checked on the Apps tab's "Top 10 by upside" chart. |
| 21 sector tags are small icons | holds in Sectors | Theme column: 18 px svg icons with a `title` tooltip, no text tag wider than an icon on all 16 rows. The Legend and the "Hot sectors" cards on Top Picks not looked at. |
| 37 / 50 Sectors | holds | Four named quadrants (Emerging, Hot, Fading, Falling), 12 bubbles and 12 tails (caption: "Tail = where it stood 4 weeks ago"); table columns are Stage, Theme, 1M, 3M, Talked about, Fundamentals, Growth 3M, grouped by stage. At 2000 × 1000 no name overlaps another name, a bubble or a tail. |
| 42 Legend shows only what the open tab shows | holds | The Apps and Top Picks Legend has none of Post-crash, Declining, No data, Thin liquidity, "Tradeable here"; the Chains Legend has the first four; "Tradeable here" is on no Legend. Whether Apps and Chains mark warnings the same way not looked at. |
| 25 report status icon | partly | 60 of 60 coins opened show "ready": solid green border, green glow, tooltip "Degen report: ready. Click to read the report below." No coin showed "not researched" or "outdated", so those two styles were not seen. |
| 390 px | holds | No horizontal overflow on Top Picks, Apps, Chains, Sectors, Legend (scrollWidth 390 = viewport). |

Speed while reading (shell, so support only): 15:47 UTC board 200 in 4.5 s; 15:49 UTC `GET /api/v1/build-it-better/requests/ET-28606` 200 in 6.4 s (3.7 KB, first byte 6.4 s). 16:58 UTC: `/gem-screener/app` 12.8 s (2.3 MB, first byte 1.5 s), `/api/v1/gem-screener/picks` first byte 3.9 s for 5.4 KB, `/llms.txt` 2.6 s.
