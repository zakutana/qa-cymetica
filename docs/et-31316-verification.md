# ET-31316 Infiltrator: verification against its "Done when"

Read 2026-10-14 ~06:00 UTC, after Nexus's Telegram message "Your Infiltrator from Build it Better is live (cymetica.com/infiltrator)". GETs only: `/api/v1/infiltrator`, `/groups`, `/queue`, `/ideas` (generated_at 1791959859), the page at 1920 x 1080 and 390 px in headless Chrome, and `/build-it-better?idea=237` opened without submitting (the only POSTs either page made were telemetry). Scripts: scratchpad `infil_check.py`, `infil_page.py`, `infil_build.py`. The spec is `outbox/infiltrator/request.md`.

| # | Check | Result |
|---|---|---|
| 1 | Communities and moods from the existing sentiment engine, said on the page | PASS: "Runs on Cymetica's Belief Networks" under the tagline; API `source` names the Belief Networks |
| 2 | One line on how a group is read and when an idea is drafted | PARTIAL: the line is there ("20 or more people on 7 or more different days, from the 3 themes"), but 25 listening groups that meet it read `learning: no theme with 5 people yet` (Piggycell 128 people / 27 days, ROACORE_Chat 92 / 27, IoTeX 65 / 12). A theme needs 5 people; the line does not say so |
| 3 | No message text or member name/handle; groups public; a bot-banning group reads Left with the reason | PASS: group keys carry counts only (no text, author or member fields); all 494 Left rows carry a reason, 12 of them "bots are not allowed there". `@...` occurs only as a group's own name |
| 4 | The four counts agree with the lists | PASS on the counts: 1,959 = 606 + 494 + 747 + 112; 606 listening listed; 206 drafted = 206 ideas listed. But the 206 sit on 182 groups: 24 groups carry two ideas, an older one (04:28) kept beside a newer one (04:38), against "one drafted idea for that group" (Hydration r735: "Support answers in minutes" and "Launch radar with a safety score") |
| 5 | Suggest and bid; queue by bid, then votes | NOT TESTED: needs a signed-in write; the queue is empty and states the rule ("A bid needs 100,000 ET10 held and is never collected") |
| 7 | Each idea card: community, title, three themes, why, votes, Drafted/Shipped | FAIL: 40 of 206 ideas carry fewer than three themes (26 two, 14 one), e.g. #329 Kamino with one theme ("support & withdrawals", 5 people, 17 %) and its group's mood and handle null. The other parts are present on all 206 |
| 8 | Build it opens a pre-filled form and submits nothing | PASS: `/build-it-better?idea=237` fills the idea name ("Launch radar with a safety score for Hydration") and its description (community, members, mood, themes); no POST but telemetry |
| 10 | 1920: steps, queue, groups, ideas on the first screen; 390: ideas first | PASS: at 1920 all four in the first 1,080 px; at 390 ideas start at 1,230 px, the queue at 11,345 and the groups at 11,701 |
| 11 | Groups, queue and ideas as JSON | PASS: all four routes 200 JSON; live over `wss://cymetica.com/ws/infiltrator` |

Also checked: no mood outside -100..+100 (range -88..+43); every idea's group is listening and meets 20 people / 7 days; every "why" percentage matches its first theme's people over the group's speakers.

Verdict: the operator's. Seven pass or partly pass, one fails (#7, 40 ideas short of three themes), one not testable from here (#5).
