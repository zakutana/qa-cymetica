# Quant Lab v2: the experiments page for degens (mock)

Asked for by the operator on 2026-10-30: a new design of `cymetica.com/company/app/experiments`, maximum degen-friendly
(almost no text, icons and animation), a brutal animation of how the search runs, then what happened, and it must
match what Cymetica is building in **ET-33142** (Nexus, 2026-10-29): the search unit becomes a whole bot setup (a model
or a Named Combination, plus skills), and a setup that passes the held-back check starts as a paper bot with exactly
that setup.

**Open:** `python -m http.server 8801 --bind 127.0.0.1 --directory outbox/quant-lab-v2` (the `quant-lab-v2` entry in
`.claude/launch.json`), then http://127.0.0.1:8801/. `?mode=sim` opens on the ET-33142 view.

## Two modes (the pill top right)

* **Real**: our company 14's Quant Lab exactly as their owner-only API returned it (`data.js`, written by
  `refresh.py`, GET only): 4 searches (#3 done, #5/#7/#9 failed), 16 rules x 12 markets x 9 settings = 1,728 tried,
  5 blind-tested, 0 cleared the bar, 0 bots.
* **ET-33142**: one small simulation (`simModel()` in `ql.js`) of how it is meant to work: today's 16 rules plus 8
  setups built from models / Named Combinations and skills (24 x 12 x 27 = 7,776 tried), the bar from their own method
  (one-sided 5% split over every combination, z = 4.36 at 7,776, never below 1%), one winner, born as a paper bot that
  carries the winner's chips. Marked SIMULATED on the reactor.

## The page, top to bottom

Their crumb; six numbers with an icon each; the **reactor** (BUILD, BLAST, BLIND, THE BAR, BOT: click a stage to jump);
the **blind test** rows (setup chips, coin, settings, search % to blind %, a gauge against the bar, a tick or a cross);
**bots** with the owner's rule as chips; a foot with *What was tested*, *Log* and *Can tune / can't* (their own
`can_tune` / `cannot_tune` lists, cut to the part before the colon; the full sentences are tooltips).

Every name and icon is theirs: models and combinations from `/adm`, skills from `/skills-n-tools`, the method and the
limits from `/api/v1/company/{id}/quant-lab/search`. The premium models (PRION, SYNAPSE, TELOMERE) stay out of the
simulated setups, because their own list says the lab never equips them. Their `style.css` and `xp.css` are loaded live
from cymetica.com; every class of ours starts `q2-` because theirs styles short global names (`.on`, `.n`, `.bar`, `.up`).
The page sends nothing: no fetch, no form; the buttons are pictures.

Tests: `python -m pytest outbox/quant-lab-v2/tests -o addopts="" -p no:cacheprovider` (both modes run, the real numbers
equal `data.js`, the simulation comes from one model, glance-length text, no type under 11 px, the site palette, nothing sent).
Desktop first; under 1100 px the rows fold, a phone layout is not drawn.
