# Build it Better: Gem Screener -- the smiley, an "Established" stage, the growth warning, the funds (draft, not filed)

Collected from the operator on 2026-10-13: *"smajlik ma byt kdekoliv kde projekt dava komunite cokoliv, kde je proste mechanismus na miste, nevadi ze je to malo"*; Collector Crypt reads "Slowing" and "Watch out: the business is no longer growing" while it makes millions a month (*"neco jako Established coz je velmi pozitivni znamka"*); the funds do not work, so *"tu sekci radeji zrusit"*. The goals are theirs; the thresholds below ($1M a month, 80 % of the high, 12 months) are ours, their veto open.

Figures from Cymetica's own snapshot of 2026-10-13 07:36 UTC (`GET /api/v1/gem-screener`), `/coins/{slug}`, `/funds` and DefiLlama's holders revenue, read the same morning. No open Gem Screener ticket blocks it (ET-29379 verdict pass, 2026-10-10; ET-31267 is the Supply Analyzer's).

Not a bug report: the exit flag "the business is no longer growing" and the smiley rule are the design the page was specified with (the original `exit_flags`: phase Slowing, Flat or Declining, or 6-month growth at or below zero; ET-29379 item 8: the smiley only when the Holders paid guardian is green). This changes the design.

On the form: "I have a link" with `https://cymetica.com/gem-screener/app`, the block below in "What should it do better?", one item per line.

```
Follow-up to ET-29379: upgrade the live Gem Screener itself, not a new page beside it; it keeps its name, logo and copy, and the template lines about rebuilding someone else's app do not apply. Six changes; goals, not methods. Figures are from your own snapshot of 2026-10-13 07:36 UTC.
1. The green smiley in the Apps table marks every project that gives its holders anything in the last 12 months: a buyback, a burn, or a payout to stakers or lockers, however small the share. A mechanism in place is what it says, not its size.
Today it shows only when the Holders paid guardian is green, so 72 of the 113 apps whose holders got money in the last 30 days have none: Curve 97% of revenue (to veCRV lockers), Aerodrome 100%, dYdX 100%, Pharaoh 99.8% ("how is not checked"), Collector Crypt 0.3%, Graphite 0.24%.
12 months, not 30 days: Graphite burns every few weeks or months (DefiLlama holders revenue: Mar 24, Apr 4, May 8 and Oct 4, 2026), so a 30-day window would switch its smiley on and off.
The smiley's tooltip says how much and how, in one line: "Holders get 97% of revenue, paid to lockers", "Holders get 0.2% of revenue, bought back and burned", "Holders get 100% of revenue, how is not checked yet".
The Holders paid guardian keeps judging the size as today (Bad under 5%); only the smiley changes.
2. The trajectory gets a stage "Established": revenue of $1M or more in 30 days, at 80% or more of its 1-year high, and not shrinking over 90 days. It is a good sign and reads as one (green), not as a warning.
Today the stage compares recent growth with earlier growth only, never size or level: Collector Crypt ($15.2M in 30 days, 100% of its 1-year high, revenue +12% a month over 90 days and +18% a month over a year) reads "Slowing" because +4.5% a month is less than +8.4%. With the rule above Collector Crypt, World Liberty Financial, GMX and Maple read "Established"; Ignition and Accelerating stay as they are.
On the coin detail the stage strip gets "Established" after "Steady", and its tooltip says in one line what it means.
3. "Watch out: the business is no longer growing" (pick card, exit flag) and "Revenue growth is slowing" (Earnings guardian) appear only when revenue actually falls: 90-day growth below zero, or revenue under half of its 1-year high. An Established business never gets them.
Today the flag is on 4 of the 10 picks, all growing over 90 days. Under this rule it leaves Collector Crypt (+12% a month, at its 1-year high), GMX (+5.5%, 99% of its high) and Bankr (+14.3%, 52%), and stays on Solv (+13.1%, but 48% of its high). Slower growth of a growing business is not a reason to sell.
4. Funds: a fund that cannot be bought is not shown. Today every sector fund and the Top Picks fund read "Fund off the public list since 2026-10-08: not open to buy" (/api/v1/gem-screener/funds: 11 sector funds unlisted, Privacy has none), on every Hot sectors card and in the Top Picks fund bar.
So the Hot sectors cards carry no fund line and the Top Picks fund bar is gone while its fund is unlisted or does not exist; each comes back by itself when its fund is open to buy again. Nothing else in the panel moves.
5. Top Picks, Degen picks: the sentence beside the gate row, "Backtest of the old gates: inconclusive. A shortlist, not a signal. details", goes. The same sentence and the backtest verdict are already further down the page; once is enough.
6. Pick cards: the blue warning triangle in the card's head goes; the "Watch out:" line under the chips already says the same. What the triangle says that the line does not (today: "Only 77 days of history" on StonkFun, "Only 91 days of history" on Pons, the dilution caution on Solv) joins the "Watch out:" line, so nothing is said twice and nothing is lost.
Done when:
[ ] 1 Every Apps row whose holders received anything in the last 12 months has the smiley, whatever the share; a row with nothing in 12 months has none.
[ ] 1 Curve, Aerodrome, dYdX, Pharaoh, Collector Crypt and Graphite have the smiley.
[ ] 1 The smiley's tooltip is one line with the share and how it is paid, or "how is not checked yet".
[ ] 1 The Holders paid guardian's verdicts are unchanged.
[ ] 2 Collector Crypt, World Liberty Financial, GMX and Maple read "Established" on the snapshot of the day they are checked, if they still meet the rule; no app under $1M a month or under 80% of its high reads "Established".
[ ] 2 "Established" is on the stage strip after "Steady", green, with a one-line tooltip.
[ ] 3 No app whose 90-day revenue growth is zero or above, and whose revenue is at half of its 1-year high or more, carries "the business is no longer growing" or "Revenue growth is slowing".
[ ] 3 An app whose 90-day growth is below zero still gets the warning.
[ ] 4 While /funds lists a fund as unlisted or missing, its Hot sectors card has no fund line and the Top Picks fund bar is not on the page; with a fund open to buy, both show as before.
[ ] 5 The backtest sentence is no longer beside the Degen picks gate row; it and the verdict still stand once further down.
[ ] 6 No pick card has the warning triangle; every warning it carried today is in that card's "Watch out:" line, each once.
```
