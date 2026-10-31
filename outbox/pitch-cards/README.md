# Pitch Cards (mock): Nexus pitches, you swipe

Asked for by the operator on 2026-10-31 (replacing Prove It, which he threw out): a room like a TV investors' show where
Nexus brings its pitches and the user, with credit loaded on the platform ($100 in his example), swipes left to pass or
right to give it an amount; then follows how the deal does. A pitch is short and backed by data shown first; a
notification on Cymetica says when Nexus has one; every pitch Nexus ever made goes on a public pitchboard with its
result since. Nexus pitches only high-confidence ideas with results behind them, or truly big news (a mega deal or
IPO), never a fresh untested event card.

**Open:** `python outbox/pitch-cards/serve.py` (the `pitch-cards` entry in `.claude/launch.json`), then
http://127.0.0.1:8802/pitch-cards. `?view=board` or `?view=deals` opens those tabs.

## How it is built

Their live `/agent-casino` page (our family's app on their site), read anonymously and cached 60 s, with only the casino
app replaced by `app.html`; their header, agent prompt card, Nexus chat bar, footer and the Agent Casino stylesheet
(`.at`, `.at-bar`, `.at-btn`, `.at-tag`, `.at-ktag`, `.at-seg`) stay and `app.html` is built on them. `pc.css` holds the
deck, card, amount sheet, deals and board only. Every method except GET is refused by `serve.py`. Their mobile CSS
makes any `[role=dialog]` fill the screen, so the role sits on the sheet's overlay.

## Nexus's bar (refresh.py)

* **A fund**: live 8+ weeks, +5% or more since it went live, up over the last 30 days. Today: Molecular only
  (+23.5% since 14 Aug, +10.4% in 30 days, worst dip -12.3%).
* **A big deal**: $10B or more, in the last 7 days, with a live ripple card. Today: EQT buys Range Resources ($13.0B),
  MSCI card +2.0%; the card also says 6 of 11 $10B+ deal cards are up so far.

## Numbers

`data.js` is written by `refresh.py` (GET only): `/fund-performance` and each fund's page (its `var pts` index history
and "Live since"), `/api/v1/ma-fund/history`, every live event card, and the chosen deal card's index history. The
pitchboard is Cymetica AI's picks so far, 38: 16 funds since they went live and 22 deal-ripple cards since they were
minted (22 up, -1.69% on average); the 557 one-per-company "SAIB: ZTS — Zoetis" cards are not picks and stay off.
The $100 balance is his example; investing moves only the page's own counters, and a new deal reads 0.00% until
the real product tracks it.
