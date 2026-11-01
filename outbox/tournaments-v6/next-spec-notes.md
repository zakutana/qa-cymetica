# Agent Casino: next spec, collected while testing (from 2026-11-01)

Goals, not methods; each becomes a numbered line of the next Build it Better when the operator says to write it. Bugs with an API reading go through the report channel instead (#210, #234 to #240). The department adds here what only a person looking at the page would see.

## Holes in the game (the operator hears these in chat too)

1. **A bot burns its day before it sits down.** Bots trade away from the tables, so one can arrive with 20/20 trades used and an empty seat for its whole table (#237). Goal: the owner sees "N trades left today" at the ask and at Approve, and a table ending before the reset is not offered to a bot with none. Better still, a seat has its own allowance, so a table is always playable.
2. **The bot that did nothing can win.** On a losing table a bot with 0 trades finishes #1 at +0.00 % over bots that traded (#41, #42: "WINNER tournament Perceptron Oracle" with no trades, no prize). Goal: the WINNER line names whoever takes the prize, and a seat that never traded is shown as such, not as the winner.
3. **Coach on or off, nobody can tell if it helps.** The owner sees tunes but never a result. Goal: at the end of a table, one line: what the coach changed and what it did to ROI; across tables, coach on against off. (We are measuring this now: `casino.py brief`.)
4. **The coach explains the how, not the why it matters.** "stop loss 5 → 4 % · rank 3 → 4" tightened a bot six minutes before its table ended, with no trade after it. Goal: no tune in the last minutes, and each line says what it hopes to change.
5. **A table with one member has no game in it.** With five house bots the member's prize is their own buy-in back ($5 from a $5 pot) whatever they do. Goal: the page says so before Approve ("with house bots the pot is only yours"), or house seats add a small pot.

## Page polish, seen on the live build

6. Table page, The deal block on a 1 H table: "yours, back after 1 day", "the table runs 1 day", "3/7 of 3× the capital (1 day)". Each should follow the table's real length (the How it works page is #235).
7. "NEXUS TUNES 1" counts a CHECKED row that changed nothing. Goal: the count is of tunes; checks apart.
8. After moving Risk the coach panel keeps the old "Risk reads 5" until the page is reloaded, and the Changelog says "changed trade size, stop loss, take profit" with no numbers. Goal: the panel follows at once and the row says Risk 5 → 8.
9. The coach says "nothing left to change inside the limits" and tunes something two minutes later (#33: take profit 15 → 10; #40: PERP BTC off). Goal: the sentence says which limits, or goes.
10. Lobby: "Live now 2" and "Open, starts when full 12" stay the same whichever filter is on. Goal: the counts follow the filter.
11. Create a table offers only "Flash · 1 day", though 1 H and 5 H are the tables people play. Goal: length is a choice.
12. "PAID OUT ... +3 ET10" over "3 ET10 waiting for treasury coverage" (#42, pending at the end, credited later). Goal: the header says what is paid and what waits.
13. Result card with several seats of one owner: "YOUR RESULT" shows the first seat only ("Prize — this time" while two other seats won), only one row is tagged YOU, and the coach, settings and trades exist for the first seat only (#33, #42). Falls away if MSG-0293 is granted (one bot per owner per table); otherwise a seat switcher.
14. "1 won · 3 lost" over "5 closed": a flat trade is in neither. Goal: "1 won · 3 lost · 1 flat".
