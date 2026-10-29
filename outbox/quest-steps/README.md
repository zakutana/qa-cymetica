# The Cymetica Quest, step by step: our mock

Asked for by the operator on 2026-10-29: a new page for the Cymetica Quest, explained in steps. The intro (join the
quest, win up to 500,000 ET10 every month), then how: start a company in the Universe; build products OR a trading
agent; promote it on the Promo Market; climb the leaderboard. Real pictures of each. It stands beside `outbox/quest`
(the scroll film, still on the 5 % revenue share), which is unchanged.

## Open it

The `quest-steps` entry in `.claude/launch.json` (http://127.0.0.1:8800/). Wide first (2000 px), works on a phone.

## What is here

| File | What |
|---|---|
| `index.html`, `quest.css`, `quest.js` | the page; `QUEST` in quest.js holds every figure, address and hotspot |
| `capture.py` | the pictures, into `pics/` as webp: Cymetica's live pages read anonymously, clipped to the step's part (no header, no counters that read zero today); prints each hotspot's box |
| `pics/` | what the page loads (kept in git, ~1 MB) |
| `tests/test_quest_steps.py` | his steps in his order with their pictures, the prize from one config, the rail, the word budget, type size, the palette (`python -m pytest outbox/quest-steps/tests -o addopts="" -p no:cacheprovider`) |

## Which pictures are not live

- `season.webp` (the hero) and `leaderboard.webp` (step 4) are our Universe mock (`outbox/company-live`, `?season0`):
  the monthly ET10 board is not live on cymetica.com yet. Everything else is their live page of 2026-10-29.
- The prize, 500,000 / 250,000 / 100,000 ET10, is the operator's figure (uv-data.js `CO.SEASON`); Cymetica has not
  confirmed it. The flyer and `outbox/quest` still say up to 5 % of revenue.
