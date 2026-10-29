# The Cymetica Quest, step by step: our mock

Asked for by the operator on 2026-10-29: a new page for the Cymetica Quest, explained in steps. The intro (join the
quest, win up to 500,000 ET10 every month), then how: start a company in the Universe; build products OR a trading
agent; promote it on the Promo Market; climb the leaderboard. It stands beside `outbox/quest` (the scroll film, still on
the 5 % revenue share), which is unchanged.

## Three takes, the same day

1. **a1cb3cf5, 7/10**: real screenshots, each in a glass browser frame. "Nedavej to do panelu ... at to splyva."
2. **60da77f5, 4/10**: everything full screen, a flight in to the sun, the orbit with its companies, the prizes as plain
   type. "Predchozi verze byla mnohem lepsi a cistsi, hlavne ty velke cislice na pozadi ... nedavej nikde tu obeznou
   drahu."
3. **This one**: the first take's layout (title and prize chips over the flyer's space, the big hollow step numbers,
   words beside the picture), no frames, and in every step a picture plus a piece of Cymetica's own web as a hologram
   in the dark, never a rectangle (his words: "v kazdem kroku nejaky zaber z webu nejak huste holograficky zobrazeny
   ... a k tomu zaroven vzdy ten obrazek"). The Promo Market is its cube, not the building.

## Open it

The `quest-steps` entry in `.claude/launch.json` (http://127.0.0.1:8800/). Wide first (2000 px), works on a phone.

## What is here

| File | What |
|---|---|
| `index.html`, `quest.css`, `quest.js` | the page; `QUEST` in quest.js holds every figure and address |
| `capture.py` | every picture into `pics/`, and where each comes from (its docstring); the pieces of web are keyed to light (their page's dark made clear) |
| `pics/` | what the page loads (kept in git, ~2 MB) |
| `tests/test_quest_steps.py` | his steps in his order with their picture and piece of web, nothing full screen and no orbit, each hologram a cut-out, no picture in a box, the prize from one config, the rail, the word budget, type size, the palette (`python -m pytest outbox/quest-steps/tests -o addopts="" -p no:cacheprovider`) |

## Which pictures are what

| Step | Picture | Piece of web |
|---|---|---|
| 01 | the HQ, LIVE builder step 2 (cymetica.com/company/app/builder) | the builder's Start card, LIVE |
| 02 A | the Development room, LIVE builder's tour | Build it Better's top, LIVE |
| 02 B | the Hero Agent (Antigravity, outbox/quest/gen) | an Agent Casino table, LIVE |
| 03 | the Promo Market's cube, LIVE /promo-market | an open brief: our mirror's picture of their market, 2026-10-27 (their market has no open brief today) |
| 04 | the podium, our Universe mock (?season0) | the leaderboard's rows, the same mock; its companies are samples. The monthly ET10 board is not live |

## Notes

- "Breed your agent" is the operator's wording (2026-10-29). On 2026-10-28 the Quest guide had changed "Breed a Hero
  Agent" to "Find a Hero Agent" after Nexus said the lab-to-bot bridge was not built (ET-33133); their live tour now says
  the lab "keeps searching for a profitable agent ... and sends the best to the Trading desk".
- The prize, 500,000 / 250,000 / 100,000 ET10, is the operator's figure (uv-data.js `CO.SEASON`); Cymetica has not
  confirmed it. The flyer and `outbox/quest` still say up to 5 % of revenue.
