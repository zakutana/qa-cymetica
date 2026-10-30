# The Cymetica Quest, step by step: our mock

Asked for by the operator on 2026-10-29: a new page for the Cymetica Quest, explained in steps. The intro (join the
quest, win up to 500,000 ET10 every month), then how. It stands beside `outbox/quest` (the scroll film, still on the 5 %
revenue share), which is unchanged.

## Four takes

1. **a1cb3cf5, 7/10**: real screenshots, each in a glass browser frame. "Nedavej to do panelu ... at to splyva."
2. **60da77f5, 4/10**: everything full screen, a flight in to the sun, the orbit with its companies, the prizes as plain
   type. "Predchozi verze byla mnohem lepsi a cistsi, hlavne ty velke cislice na pozadi ... nedavej nikde tu obeznou
   drahu."
3. **fdfd575d**: the first take's layout, in every step a picture plus a piece of their web as a hologram.
4. **This one** (2026-10-30). The first screen was "nahovno, opet roztahly od kraje do kraje" and its title "jak nejaky
   marketingovy letak". So now:
   - **The first screen** is our flyer laid on its side: its glass board of open slots on the left, the words on the
     right in the type of cymetica.com/company/app/start, its sun behind. All of it is held in the middle of the screen,
     with no button.
   - **Five steps** in his words, each with a green line. No link in any of them; the two links are at the end.

## Open it

The `quest-steps` entry in `.claude/launch.json` (http://127.0.0.1:8800/). Wide first (2000 px), works on a phone.

## What is here

| File | What |
|---|---|
| `index.html`, `quest.css`, `quest.js` | the page; `QUEST` in quest.js holds every figure and both addresses |
| `capture.py` | every picture into `pics/`, and where each comes from (its docstring) |
| `pics/` | what the page loads (kept in git, ~1.6 MB) |
| `tests/test_quest_steps.py` | his five steps with their pictures, his words and their green line, no link in a step and two at the end, the first screen as the flyer (board left, words right, held in from the edges), the card where the builder puts it, the pipeline on the workshop, nothing full screen, no picture in a box, the cut-outs clear at their corners, the prize from one config, the rail, type size, the palette (`python -m pytest outbox/quest-steps/tests -o addopts="" -p no:cacheprovider`) |

## Which pictures are what

| Step | Picture | From |
|---|---|---|
| 01 Start an AI-native company | the builder's Start as it stands: the office in 3D and its card in its own place | LIVE cymetica.com/company/app/builder, 1920 x 1080 |
| 02 Build products | the robot-arm workshop, the Build it Better pipeline laid over it (your spec, production-grade apps, top security, deployment & hosting, you own it) | our three.js scene of the second take |
| 03 Breed your hero agent | the Hero Agent, the Agent Casino's building cut out under it | Antigravity (outbox/quest/gen); our Universe mock (u3d.js adCasino) |
| 04 Get seen | the Promo Market with three briefs up for grabs; the Airdrop Farmer close in the Universe, the Gem Screener behind it | their live page through our read-only mirror, with sample briefs (their market has none open today); our Universe mock, composed |
| 05 Climb the leaderboard | the podium and the leaderboard's rows | our Universe mock (?season0): the monthly ET10 board is not live |

## Decided here, the veto open

- **Step 4**, "your own slots (tady asi nejake lepsi slovo)": the page says **your own land**, Cymetica's own word for a
  slot of the Universe (`GET /company/land`, the flyer's "land · Promo Market").
- **Step 5**, the glass board again or the leaderboard's detail: **the detail**. The first screen already has the board.
- **Step 3**, "pod to": the Agent Casino stands **under the hero agent's picture, on its dark left**. It does not sit
  over the robot, and it is next to the words.

## Notes

- "Breed your hero agent" and "equip your most profitable strategies to your hero agent" are the operator's wording
  (2026-10-30). On 2026-10-28 Nexus said the lab-to-bot bridge was not built yet (ET-33133), and the Quest guide then
  changed "Breed a Hero Agent" to "Find a Hero Agent".
- The prize, 500,000 / 250,000 / 100,000 ET10, is the operator's figure (uv-data.js `CO.SEASON`); Cymetica has not
  confirmed it. The flyer and `outbox/quest` still say up to 5 % of revenue.
- The flat "2D" office he saw in the builder on 2026-10-30 is their fallback for a browser where the 3D cannot start
  (builder.js `flat()`). In our Chrome the live builder drew the 3D office every time: four runs, including 2 Mbps
  and a 6× slower CPU.
