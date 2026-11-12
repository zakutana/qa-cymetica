# Quant Lab, profiles by horizon and risk, today's market, Flash (spec, no mock)

Asked for by the operator on 2026-11-10, in their words: *"ale dyt my chteji na zacatku at si clovek rpece vybere ten timframe a riziko ne? ... co kdyz hledame jen short bota do bear trhu"*, and on 2026-11-04: *"ne viteze at nespousti v pepr modu, to muze dat jen navrh ale ja to musim schvalit pak"*.

Rests on Nexus's Flash design (REPLY-0269), his answers to our six questions (REPLY-0279, to MSG-0358), search #22 (`docs/ET-33966-verification-2.md`) and the operator's decisions since: the bot is measured alone, not against casino tables; search without a stop-loss, stop set afterwards; a signal measured as a direction call and as a candle trade; research not limited to platform markets.

Decided by us, veto open: horizon choices Flash 1 h, Flash 5 h, long term (no 1-day Flash, as for casino seating); low risk = no window below -15% (the owner rule's drawdown); more than half of the unseen windows plus the pooled bar; 12 long-term 7-day windows, 100 Flash windows; a paper short lane asked for (REPLY-0279: none exists).

Changed on 2026-11-10 after measuring (Binance daily closes, the lab's 12 coins, 730 days, weekly grid, 1,236 coin-weeks): the first draft had the lab read today's market and judge on past windows of that kind. A read from before a window does not carry into it: after a week that fell over 5% the next week fell 53% (any week 57%); a 30 or 60-day read gives 54% to 61% for every label. The 9 of 12 falling windows of #22 were known only afterwards. A short that switches itself off above its 7 to 60-day average lost in the first year with every average and made +0.2% to +0.3% a week at best over both years (30 and 60-day average, before fees; always-on +0.08%). So the lab does not guess the market: a winner is all-weather, a bear bot or a bull bot, the card shows both sides, and the bet is the owner's Approve.

Dropped since MSG-0358: Approve as a new item (REPLY-0279: shipped 10 Nov; the button is in quant-lab.js, not seen used, no winner yet).

**request.txt:** about 5,900 of 8,000 characters, 20 of 40 lines, 0 of 6 pictures.

| | |
|---|---|
| Ticket | ET-34884 (BB-0068) |
| Review | |
| Filed | 2026-11-10, on the operator's word; not reviewed by Nexus first |
| Accepted, deadline | 2026-11-10 (BB-0069), 2026-11-11 22:01 UTC |
| Shipped | 2026-11-12 12:30 UTC (BB-LATE 2026-11-11 22:23); verified in `docs/et-34884-verification.md` |
| Verdict | |
