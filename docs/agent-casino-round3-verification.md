# Agent Casino round 3: live build read line by line

Read 2026-10-31 on https://cymetica.com/agent-casino, signed in as the operator (paper only), against `outbox/tournaments-v5/request.md`. Method: four new seat asks at #33 and #34, Approve (one by one, then Approve all), fill #33 with house bots, two more asks at #35 then Decline all. 1440 px, 1920 px and 390 px for the leaderboard.

| # | Line | Result |
|---|---|---|
| 1 | Approvals loud; Decline per row; Approve all with total; Decline all; every ask listed | PASS. "Waiting for your OK" panel, blue Approve, red-outline Decline per row, "Approve all (total max loss $930)", "Decline all". Two asks by one bot (Perceptron Oracle at #33 and #34) are two rows. Approve all and Decline all acted on asks at two tables. |
| 2 | Time left; lapsed ask gone or tagged | PARTLY. Waiting rows say "lapses in 24 h". The lapsed asks of 28-29 Oct are no longer listed. The Lapsed tag itself was not seen: needs an ask older than 24 h. |
| 3 | "N agents" counts running only | PASS. 0 agents + 4 waiting; 4 seated at open tables still 0; table started: "3 agents"; the seat at the open #34 not counted. |
| 4 | Risk starts at the middle, coach on | PASS on level and coach: Risk 5, "NEXUS COACH ON" at seat time. The numbers differ from the spec's parenthesis: their level 5 is size 5 %, stop loss 2.5 %, take profit 15 % (the spec's 5 / 5 / 20 was our mirror's own map, not theirs). |
| 5 | Coach explains itself | PASS for the start state ("What it did", "Why Risk reads so"). The idle-with-full-slots sentence not seen (no bot idle yet). |
| 6 | IDLE icon at the seat and in standings | NOT SEEN. All six bots read "Trading" at 0 trades; needs a bot that stops. |
| 7 | Leader short of volume is told | PASS at the table: "needs $4.46 more volume to qualify". The rows of "Your agents" carry `volume_short_usdc`, empty until trades. |
| 8 | Coach panel leads; time left small; "in pots" stands out | PASS. Coach panel is the top block, TIME LEFT one line beneath; "$155 IN POTS" in a blue box, 21 px. |
| 9 | Open tables grouped | PASS. Six headed groups: 1H, 5H, 1D, each USDC ($5, $50) then ET10 (100, 1,000). |
| 10 | Paper dollars blue | PASS. Paper cards rgb(59,130,246); the Live USDC cards (COMING) stay green. |
| 11 | Leaderboard columns aligned | PASS. Header and cell rects identical at 1440, 1920 and 390 px, numbers right-aligned. At 390 px the Bot column is 44 px wide. |

Open: 2 (Lapsed tag), 5 (idle sentence), 6 (idle marker). Table #33 (1H, ends 22:55 UTC) is the place to look if a bot goes idle.
