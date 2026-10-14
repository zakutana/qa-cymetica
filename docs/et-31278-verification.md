# ET-31278 Gem Screener follow-up: verification against its "Done when"

Read 2026-10-14 ~07:00 UTC, after Nexus's Telegram message "Your Gem Screener follow-up from Build it Better is live". GETs only: `/api/v1/gem-screener` (snapshot generated 03:35:19 UTC), `/funds` (as_of 06:55 UTC), `/status` (next refresh due 09:35 UTC), and the app itself, `/gem-screener/app?view=start` and `?view=apps`, rendered in headless Chrome at 1920 x 1080 (scratchpad `gem_check.py`). The spec is `outbox/gem-screener-holders-trajectory-funds/request.md`.

**Items 1 to 3 cannot be checked before the 09:35 UTC snapshot.** The page code is deployed (smiley on `holders_paid_1y` with its one-line `holders_line`; `Zavedený` / "Established" on the stage strip after "Steady", green; the exit flag by the collector), but the snapshot on the page was collected before it: no app carries `holders_paid_1y`, so no smiley shows, and the phases and exit flags are the old rule's (Collector Crypt `slowing` with `business_weakening`; GMX, Bankr and World Liberty Financial `flat` with it). Their message says the same: "the new stage and smileys appear with the next snapshot".

| # | Check | Result |
|---|---|---|
| 1 | Smiley on every row whose holders got anything in 12 months; the six named; one-line tooltip; Holders paid guardian unchanged | PENDING (09:35 UTC snapshot) |
| 2 | Collector Crypt, WLFI, GMX, Maple read "Established" if they meet the rule; none under $1M or 80 %; on the strip after "Steady", green, with a tooltip | PENDING; the strip and its colour are in the code |
| 3 | No growing app at half its high or more carries the two warnings; a falling app still does | PENDING. Today's snapshot, for the record: Bankr's 90-day growth is now -2.0 % (it was +14.3 % in the spec), so under the rule it may keep its warning |
| 4 | While /funds lists a fund unlisted or missing: no fund line on its Hot sectors card, no Top Picks fund bar | PASS: /funds lists every sector fund and Top Picks unlisted; the start view has no fund line, no "not open to buy", no "Fund →", no fund bar. The other half (a fund open to buy shows as before) cannot be tested while none is open |
| 5 | The backtest sentence is gone from beside the gate row; it and the verdict stand once further down | PASS: nothing between the gate row and the cards; the sentence stands once, as the folded verdict line `#startBtLine` (1,537 px further down) |
| 6 | No pick card has the triangle; what it said is in the "Watch out:" line, each once | PASS: no triangle on the 10 cards; StonkFun "only 77 days of history", Pons "only 91 days of history" and Solv's dilution caution are in their Watch out lines, each once |

Verdict: the operator's, after items 1 to 3 are read on the 09:35 UTC snapshot.
