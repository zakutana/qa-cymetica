# The Cymetica Quest, step by step: our mock

Asked for by the operator on 2026-10-29: a new page for the Cymetica Quest, explained in steps. The intro (join the
quest, win up to 500,000 ET10 every month), then how: start a company in the Universe; build products OR a trading
agent; promote it on the Promo Market; climb the leaderboard. It stands beside `outbox/quest` (the scroll film, still on
the 5 % revenue share), which is unchanged.

**Second take** (the same day, his verdict on the first "7/10 ... musi to byt grandiozni"): no picture in a panel or a
browser frame, everything melts into the page; the opening not a giant banner but a flight in from deep space; step 1
the tutorial's office (the headquarters), step 2 space robot tools OR "Breed your agent" with the Hero Agent, step 3 the
Promo Market's building close and its page, step 4 the leaderboard. The first take is in git history (a1cb3cf5).

## Open it

The `quest-steps` entry in `.claude/launch.json` (http://127.0.0.1:8800/). Wide first (2000 px), works on a phone.

## What is here

| File | What |
|---|---|
| `index.html`, `quest.css`, `quest.js` | the page; `QUEST` in quest.js holds every figure and address; the opening's flight engine is outbox/quest's, made small |
| `capture.py` | every picture into `pics/`, and where each comes from (its docstring) |
| `scenes/tools.html` | our three.js scene for step 2's way A (two robot arms building an app of glass panels), rendered once by capture.py |
| `pics/` | what the page loads (kept in git, ~1.6 MB) except `pics/fly/`, the flight's 71 frames (5 MB, not in git) |
| `tests/test_quest_steps.py` | his steps in his order, no picture in a box, the opening not a banner, the prize from one config, the flight, the rail, the word budget, type size, the palette (`python -m pytest outbox/quest-steps/tests -o addopts="" -p no:cacheprovider`) |

## Which pictures are what

- **Live, cymetica.com, 2026-10-29:** the office (`/company/app/builder`, step 2, its own 3D with the page hidden) and the
  Promo Market page (`/promo-market`, its backgrounds cleared so it floats).
- **Our Universe mock** (`outbox/company-live`, rendered 2026-10-27 by `outbox/quest/render.py`): the flight, the Promo
  Market tower close, the whole Universe at the end; and the leaderboard (`?season0`, its title cut off), since the
  monthly ET10 board is not live. Its companies (Giga Fund, Bull Club, ...) and "18 days left" are the mock's samples.
- **Made for the page:** the robot arms (our scene) and the Hero Agent (Antigravity, `outbox/quest/gen`).
- The flight's frames come from `outbox/quest/frames`, which is not in git either: a fresh clone shows the first frame
  (`pics/fly-0.webp`) and the tests pass on it (run so, frames moved away, 2026-10-29: 19 green).

## Notes

- "Breed your agent" is the operator's wording (2026-10-29). On 2026-10-28 the Quest guide had changed "Breed a Hero
  Agent" to "Find a Hero Agent" after Nexus said the lab-to-bot bridge was not built (ET-33133); their live tour now says
  the lab "keeps searching for a profitable agent ... and sends the best to the Trading desk". The line under it says
  the lab hunts for the agent that wins.
- The prize, 500,000 / 250,000 / 100,000 ET10, is the operator's figure (uv-data.js `CO.SEASON`); Cymetica has not
  confirmed it. The flyer and `outbox/quest` still say up to 5 % of revenue.
- Scroll timing at 2000 x 1100 with a real GPU: median 7 ms a frame, p90 14 ms with the CPU slowed 4x, 21 ms at 6x.
