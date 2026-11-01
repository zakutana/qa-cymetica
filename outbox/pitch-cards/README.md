# Pitch Cards (mock): Nexus pitches, you swipe

Asked for by the operator on 2026-10-31 (replacing Prove It, which was thrown out): a room like a TV investors' show where
Nexus brings its pitches and the user, with credit loaded on the platform ($100 in the operator's example), swipes left to
pass or right to give it an amount; then follows how the deal does. A pitch is short and backed by data shown first; a
notification on Cymetica says when Nexus has one. Nexus pitches only high-confidence ideas with results behind them, or truly big news (a mega deal or
IPO), never a fresh untested event card.

**Open:** `python outbox/pitch-cards/serve.py` (the `pitch-cards` entry in `.claude/launch.json`), then
http://127.0.0.1:8802/pitch-cards. `?view=board` or `?view=deals` opens those tabs, `?nopush` leaves the notification off.

## How it is built

The third take, after "jezisi kriste co to je za tragicky design" on the first (their `.at` chips and tags) and "to je snad
jeste hnusnejsi" on the second (Inter on glass, gradient numerals, aurora blobs). The Den is the render of Nexus at a
holographic chart (`outbox/quest-gemini/pics/agent.webp`, an untracked folder, the source for `build_scene.py`):

* `scene.webp`: the room alone, the baked pane painted out and Nexus gone (right of x=1300 it is its left side mirrored).
* `nexus.webp`: Nexus cut out along a hand-traced outline, standing in front of the card, so the live card sits under the
  finger and slides behind Nexus when it is swiped right. On a phone the card covers the body and the face looks over it.
* The sizes do not follow the window, as their own pages' do not: at the operator's 2560 x 1267 /agent-casino has a 58px
  headline and a 1208px column, so here the headline is 58px, the card 400 x 530, Nexus 72% of the render, the group
  centred, and only the room fills the screen ("vse moc obrovske", 2026-11-01, when it all grew with the window).
* `layout()` in `pc.js` places Nexus and the card in the render's own pixels (2560 x 1440), so the finger stays on the card at
  any screen size from 1280 x 720 up, and `drawChart()` ends the line under the fingertip where the data allows (within 3 px on
  the fund card; the deal's own peak above its last point keeps that dot lower). Under 1100 px wide it is the phone layout,
  tabs at the bottom.
* A card holds five things: a label line, the result as the big number, what it is, the chart, one or two sentences. The
  big number is always the result, on a deal too; the deal's size sits in the label and the sentence. The back of the card is
  the same face with the number yours to set, and the two buttons stay under the thumb.
* Two fresh agents read the screenshots after my own look (6/10, then 6 and 7 of 10). Taken from them: strongest pitch
  first, the result as the hero, a flat card (a tilt softened the type), one amount control, no chart labels, no stamps
  over the number. Not taken: replacing the field of peer lines with a band, deleting the arm, renaming the Pitchboard.

The page is their live `/agent-casino`, read anonymously and cached 60 s, with the casino app replaced by `app.html` and
their own embed switch (`html.st-embed`) taking off the header, prompt card, chat bar and footer: a full-screen shell, as
/promo-market has. Their type: Archivo Black, JetBrains Mono, Inter. Every method except GET is refused by `serve.py`, so
their scripts' visit and telemetry POSTs stop here.

The motion is part of it: a new pitch is wiped on from the finger by a line of light, the number runs up, the line draws,
the sentence types out; swiping right turns the card over for the amount, and investing sends it behind Nexus, whose eyes flare.

## Nexus's bar (refresh.py)

* **A fund**: live 8+ weeks, +5% or more since it went live, up over the last 30 days.
* **A big deal**: $10B or more, in the last 7 days, with a live ripple card.

Today (2026-11-01 09:36 UTC): Molecular +24.2% (best of 16 funds since going live, +9.5% in 30 days), and EQT buying Range
Resources for $13.0B (MSCI card +2.8%). The strongest result opens the deck.

## Numbers

`data.js` is written by `refresh.py` (GET only): `/fund-performance` and each fund's page (its `var pts` index history
and "Live since"), `/api/v1/ma-fund/history`, every live event card, and the index history of each $10B+ deal card. On a card
the green line is the pitch, the faint lines are its real peers from each one's own first day: the other funds, or the other
mega deals. Lines are thinned to about 36 evenly spaced means, the last point exact, and drawn straight. A fund page gives its
first day and then nothing for weeks: that stretch is not drawn, so Molecular's line starts at its first real run.

The $100 balance is the operator's example; investing moves only the page's own counters, and a new deal reads 0.0% until the
real product tracks it.

## The Profit Board

Asked for on 2026-11-01: "chci videt jeden seznam a jen veci do kterych se dalo realne zavcasu na zacatku investovat", the one
place to watch for the day Cymetica turns profitable. Headline: **What would have made you money on Cymetica.** It replaces the
pitchboard; a pitch is a tagged row (and a tab).

A graphic design for Cymetica to finish, so the numbers are read as they stand and nothing on it is checked (2026-11-01: "to nemas
overovat zadne data, ma to byt ciste graficky navrh, oni to pak cele dodelaji"). **The look** is their /themes/performance: its
tabs and its table, CSS read off the live page. **The list:** LIVE funds and event cards, only what is up right now and has a peak
to show. **Columns:** Up since start, Peak, Days since peak. **Tags, in their palette:** Fund green, Event Card white, Company Card
blue, 72h Card cyan, Pitch solid green beside its own kind.

`python outbox/pitch-cards/refresh.py --read` is the long pass (every card, then the histories, into `.cache/`, not in git,
resumable); `refresh.py` then writes `data.js`.
