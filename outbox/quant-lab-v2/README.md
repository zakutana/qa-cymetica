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
* **Coming soon** (ET-33142): one small simulation (`simModel()` in `ql.js`) of how it is meant to work: today's 16 rules plus 8
  setups built from models / Named Combinations and skills (24 x 12 x 27 = 7,776 tried), the bar from their own method
  (one-sided 5% split over every combination, z = 4.36 at 7,776, never below 1%), one winner, born as a paper bot that
  carries the winner's chips. Marked SIMULATED on the reactor.

## The page, top to bottom

Their crumb; the mark and the wordmark in the family of our Airdrop Farmer and Agent Casino (the operator: the old one
"zaostava" beside them): a round head with a dashed ring and two green eyes that blink, here a flask's bulb, its neck
and two bubbles on top where the farmer has his hat and sprout, the liquid's surface an equity line going up; QUANT
small, cyan and spaced over LAB in Archivo Black, the tagline a tooltip; six numbers with an icon each; the **reactor** (BUILD, BLAST, BLIND, THE BAR, FOUND: click a stage to jump;
⏸ or space pauses, and paused, a stage click or ← → shows that stage finished);

The reactor shows the lab's state, named in the badge beside the stages:

* **Replay**: no search running, so it plays the last finished one (`REPLAY · 27 OCT`).
* **Failed**: the newest searches failed, so the badge turns red and counts them first (`⚠️ LAST 3 FAILED · ↻ REPLAY ·
  27 OCT`); its tooltip names them and the reason as a label, never their raw error (#232). A failure is not a step of
  a search, so it has no stage and no screen: round 5 put one first in the rail and the operator could not read it
  ("TO NECHAPU TU FAILED ZALOZKU"). This is our real state today: #5, #7 and #9.
* **Live**: a search is running. It reads the fields their WebSocket sends (`done_jobs`, `total_jobs`, `percent`,
  `eta_seconds`): the cells fill as the jobs do, with the count, percent and time left. Search now (their button, with
  their cost line as its tooltip) is the only way into it here, and it is a preview: a timer at #3's real pace (32 min
  for 1,728), marked `LIVE · PREVIEW · NOTHING SENT`. When it finishes it becomes the replay.
* Not drawn: a "best so far" agent for a replay with no winner (there has never been a winner to show), the time of
  the next daily search, and a phone layout.
the **blind test** rows (setup chips, coin, settings, search % to blind %, a gauge against the bar, a tick or a cross);
**bots** with the owner's rule as chips; a foot with *What was tested*, *Log* and *Can tune / can't* (their own
`can_tune` / `cannot_tune` lists, cut to the part before the colon; the full sentences are tooltips).

The last stage, FOUND: the winning setup crushed into a core, a flash and shockwaves, the agent (our own picture from
the Quest steps page, `pics/agent.webp`, its edges faded to transparent so it sits in the grid with no frame) built
from the floor up as a hologram under a scan beam, its eyes burning, PROFITABLE AGENT FOUND, then its card trading the
same setup on paper. With no winner the agent stays dark: NO PROFITABLE AGENT. No "hero agent" anywhere (the operator,
2026-10-30). Coin logos are CoinGecko's (`assets.coingecko.com`), the source their own /perpetual pages load BTC and
ETH from; the tile and stage icons are the colourful emoji he preferred. Every name and model / skill icon is theirs: models and
combinations from `/adm`, skills from `/skills-n-tools`, the method and the limits from `/api/v1/company/{id}/quant-lab/search`. The premium models (PRION, SYNAPSE, TELOMERE) stay out of the
simulated setups, because their own list says the lab never equips them. Their `style.css` and `xp.css` are loaded live
from cymetica.com; every class of ours starts `q2-` because theirs styles short global names (`.on`, `.n`, `.bar`, `.up`).
The page sends nothing: no fetch, no form; the buttons are pictures.

No test suite: a design page is judged by the operator's eye (2026-10-30). Desktop first; under 1100 px the rows fold,
a phone layout is not drawn.
