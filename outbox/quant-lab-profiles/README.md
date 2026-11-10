# Quant Lab, profiles by horizon and risk, today's market, Flash (spec, no mock)

Asked for by the operator on 2026-11-10, in their words: *"ale dyt my chteji na zacatku at si clovek rpece vybere ten timframe a riziko ne? ... co kdyz hledame jen short bota do bear trhu"*, and on 2026-11-04: *"ne viteze at nespousti v pepr modu, to muze dat jen navrh ale ja to musim schvalit pak"*.

Rests on Nexus's Flash design (REPLY-0269), his answers to our six questions (REPLY-0279, to MSG-0358), search #22 (`docs/ET-33966-verification-2.md`) and the operator's decisions since: the bot is measured alone, not against casino tables; search without a stop-loss, stop set afterwards; a signal measured as a direction call and as a candle trade; research not limited to platform markets.

Decided by us, veto open: horizon choices Flash 1 h, Flash 5 h, long term (no 1-day Flash, as for casino seating); low risk = no window below -15% (the owner rule's drawdown); more than half of the unseen windows plus the pooled bar; 12 long-term 7-day windows, 200 Flash windows; a paper short lane asked for (REPLY-0279: none exists).

Dropped since MSG-0358: Approve as a new item (REPLY-0279: shipped 10 Nov; the button is in quant-lab.js, not seen used, no winner yet).

**request.txt:** about 5,000 of 8,000 characters, 20 of 40 lines, 0 of 6 pictures.

| | |
|---|---|
| Ticket | not filed |
| Review | |
| Filed | |
| Accepted, deadline | |
| Shipped | |
| Verdict | |
