# Build it Better: Agent Casino round 3 (approvals, counts, the coach's start, the lobby's order)

**Drawn 2026-10-29 from the operator's own use of the shipped build (ET-32932, tables 23, 24, 31, 32). Not filed, not sent: filing is the operator's.** Follow-up to ET-32932; the source of every line is `next-spec-notes.md`. Goals are theirs to build; our design is only the words.

## Filing

On the form, "I have a link" with `https://cymetica.com/agent-casino`, the block below (one item per line), and the six pictures in `pictures/` (screenshots of their live pages; the line each one shows is named beside it below). After filing, check their BB-SPEC line by line against this block, then BB-ACCEPT. Two lines of the notes have no picture (the coach's start at "10 CUSTOM", the lapsed ask) and are written out in words.

## The pictures

1. `1-approve-box-on-table.png`: the grey "Approve it" line on `/agent-casino/table/31` (line 1).
2. `2-your-agents-waiting.png`: "Your agents", one row per bot, Approve only (lines 1, 2).
3. `3-top-bar-agents-count.png`: "5 agents" with one agent running (line 3).
4. `4-idle-box.png`: the IDLE text, nothing at the table itself (line 6).
5. `5-open-tables-mixed.png`: twelve open tables in no order, green dollars (lines 9, 10).
6. `6-leaderboard-columns.png`: headers not over their figures (line 11).

## Filing block

```
Follow-up to ET-32932 (Agent Casino), written after using the shipped build. Fixes and polish; goals, not methods; the site's own look, colours and fonts. The pictures are screenshots of the live pages, each showing the thing to fix. English, numbers before words.
1. Approvals: a seat waiting for the owner's OK is the loudest thing on its table page and in "Your agents" (colour, size, a real button, not a grey link). Beside every Approve sits a Decline; above the list there is "Approve all" (with the total max loss) and "Decline all". They act on every open ask of the owner at every table, and the list shows each ask (today one row per bot hides a second ask by the same bot).
2. A seat ask lapses after 24 h. A waiting ask shows the time left ("lapses in 5 h"). A lapsed ask leaves the list by itself, or shows a grey "Lapsed" tag with a Remove; it never shows a button-looking bar that does nothing, and it is not counted as an agent.
3. The top bar's "N agents" counts only agents seated at a running table; waiting asks are counted apart (one agent running and one waiting reads "1 agent", not "5 agents").
4. At the start: when a bot takes its seat, Risk is at the middle (level 5: size 5 %, stop loss 5 %, take profit 20 %), not at the bot's own maximums (today "10 CUSTOM": 10 %, 20 %, 100 %), unless the owner already set it. The NEXUS coach is on by default when the plan allows it.
5. The coach explains itself in one line: what it last did and why, and why Risk reads as it does. When open positions fill every slot and the bot is idle, it says so and what closes them (a take profit of 100 % and a stop loss of 20 % keep $1 event-card positions open for hours).
6. An IDLE icon or highlight on the bot's seat at the table and in the standings row, with the reason one tap away.
7. A leader whose volume is under the minimum is told while it can be fixed ("needs $3.46 more volume to qualify"), at the table and in "Your agents".
8. At the top of a table page the coach / bot panel is the dominant thing; the time left (H M S) is smaller beneath it. "$5 in pots" in the top bar stands out.
9. Open tables are grouped, one heading per group: by length (1H, 5H, 1D) and, inside a length, USDC apart from ET10, buy-ins rising. The 1H / 5H / 1D filters stay.
10. Dollar amounts on Paper tables (buy-in, pot, prizes) are blue, like the ET10 amounts; green is kept for Live USDC.
11. Leaderboard: each header sits directly over its figures, every column aligned the same way (numbers right, text left), also on a phone.
Done when:
[ ] 1 Approve, Decline, Approve all, Decline all work on all open asks; each ask is listed.
[ ] 2 A lapsed ask is gone or tagged Lapsed with Remove; a waiting ask shows its time left.
[ ] 3 One running and one waiting agent read "1 agent".
[ ] 4 A bot just seated opens at Risk 5 and the coach is on.
[ ] 5 The coach panel says what it did and why; an idle bot with full slots says so.
[ ] 6 An idle bot is marked at the table and in the standings.
[ ] 7 A leader short of volume sees how much is missing.
[ ] 8-9 The coach panel leads the table page; open tables are grouped by length and currency.
[ ] 10-11 Paper dollars are blue; leaderboard columns line up at 1440 and 1920 px.
```
