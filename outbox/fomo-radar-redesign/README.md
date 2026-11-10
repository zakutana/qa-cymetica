# FOMO Radar for degens (mock)

**For Cymetica:** the request is [request.txt](request.txt), and the pictures are in [pictures/](pictures/). The page is your live /fomo-radar with its header and chat bar, with `.clone-page` replaced by [body.html](body.html), [fomo.css](fomo.css) and [fomo.js](fomo.js). These run on your own `/api/v1/clones/fomo-radar/` endpoints (signals, traders, calibration, entities, backtest) as they are today. Every figure is a field you publish, and nothing is invented. [snapshot/](snapshot/) holds those endpoints as read on 2026-11-08 at 19:18 UTC, which is what the pictures show.

Asked for by the operator on 2026-11-07, in their words: *"musis zachovat veskere info a data co stranka ma jen ji predelat at je total top degen friendly"*. They added Basic and Advanced, each wallet's rank and win rate on the cards, the launchpad promotion, and the headline *"what memecoin whales buy"*. FOMO Radar is theirs: they invented it and asked for it on /duplicate before Build it Better existed, so the request credits it to Ironstar Capital (company 14).

**Open:** `python outbox/fomo-radar-redesign/serve.py` gives http://127.0.0.1:8846/ on your live API. Add `--snap` for http://127.0.0.1:8847/ on the snapshot. `python outbox/fomo-radar-redesign/build.py` rebuilds index.html from your live page.

- **Basic** (pictures 1, 2): the headline, the radar, Smart wallets are buying (12 cards, picture 4), Smart money selling, the launchpad promotion, and Best wallets: what they made (picture 5).
- **Advanced** (picture 3): everything your page shows today, with every paragraph folded behind its i or How it works.

**request.txt:** 5,411 of 8,000 characters, 22 of 40 lines, 5 of 6 pictures (`bb.py` checked it).

| | |
|---|---|
| Ticket | ET-34609 (BB-0047) |
| Filed | 2026-11-08 20:11 UTC on the operator's word ("Podej to"); BB-SPEC proposed |
| Accepted, deadline | BB-CHANGE C1 (change-1.txt: same address, keeps the name FOMO Radar) and BB-ACCEPT (BB-0049) on the operator's word, 2026-11-08 20:13 UTC; deadline 2026-11-09 20:13 UTC |
| Shipped | 2026-11-10 05:13 UTC, 9 hours late. Verified the same day: 8 of 9 Done when lines, bugs #327 to #333 on the data ([docs/ET-34609-verification.md](../../docs/ET-34609-verification.md)) |
| Verdict | FAIL sent on the operator's word 2026-11-10 07:11 UTC (BB-0055; BB-0054 timed out and did not land), note in `verdict-note-et-34609.txt`; ticket back to funded |
| Shipped again | 2026-11-10, `fomo-radar.js?v=20261110-2`. Re-read the same morning ([docs/ET-34609-recheck-2026-11-10.md](../../docs/ET-34609-recheck-2026-11-10.md)): #330 and #329 fixed, 9 of 9 Done-when lines pass; addresses still in full, #327, #328, #331, #332, #333 unchanged. FAIL sent on the operator's word the same day (BB-0060, note in `verdict-note-et-34609-2.txt`); ticket funded again |
| Pass | Third delivery `fomo-radar.js?v=20261110-3` read 11:07 to 11:15 UTC; BB-CHANGE C2 (short addresses) sent, then waived by the owner (full addresses kept). PASS sent on the operator's word 2026-11-10 (BB-0064, note in `verdict-note-et-34609-pass.txt`); ticket shipped |
