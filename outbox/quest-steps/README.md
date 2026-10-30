# The Cymetica Quest, step by step: our mock

Asked for by the operator on 2026-10-29: a new page for the Cymetica Quest, explained in steps. The intro (join the
quest, win up to 500,000 ET10 every month), then how. It stands beside `outbox/quest` (the scroll film, still on the 5 %
revenue share), which is unchanged.

## Five takes

1. **a1cb3cf5, 7/10**: real screenshots, each in a glass browser frame. "Nedavej to do panelu ... at to splyva."
2. **60da77f5, 4/10**: everything full screen, a flight in to the sun, the orbit with its companies. "Predchozi verze
   byla mnohem lepsi a cistsi, hlavne ty velke cislice na pozadi ... nedavej nikde tu obeznou drahu."
3. **fdfd575d**: the first take's layout, in every step a picture plus a piece of their web as a hologram.
4. **e66d68dc**: the first screen as our flyer on its side, five steps in his words, no link in a step.
6. **This one** (2026-10-30, after the fifth's "ted je na urovni asi 7.5/10"):
   - **Glass:** the bar and the end's two buttons are made of our board's glass. The slogan at the end is gone.
   - **The sun:** its five companies stand still, floating, about twice as big.
   - **Icons:** every point is said with the company's own department icons. The first screen lists the four steps.
   - **Step 1** starts at the company's station (Rift Hold, the operator's picture), dives into it, and its HQ comes in
     once and holds. The card holds still.
   - **Steps 2 and 3 are one step** with two ways on one screen and a slider between them ("to bude hit").
   - **Way A:** the pipeline's skill tree has icons, chips of glass and light running along it. A strip of the
     products already built scrolls sideways.
   - **Way B:** the lab tells its story in under 7 s, then holds.
   - **Get seen:** the users walk.
   - **The Universe:** Cymetica's sun at its middle.
   - **No test suite** ("jediny tester jsem ja").
5. **46cd5e1e**, after "top panel je pekne trapnej ... styl jak to mame v capital maximizeru", "ten vesmir ... ma
   spatne rozliseni", "kazdy krok musi mit top animaci":
   - **The top bar** is Capital Maximizer's: its brand, its hexagon rail, a pill.
   - **The sky** is re-made sharp, and five small companies float round the sun, none bigger than an eighth of it.
   - **Every step moves:**
     1. the LIVE builder's office, the camera in and out so its astronauts are seen at work, its card a tilted hologram;
     2. the robot arms take an idea and build the product, the Build it Better pipeline running beside them as a skill
        tree;
     3. the Quant Lab backtests strategies, the best becomes the hero agent, who wins the Agent Casino's race;
     4. users run from the Promo Market's briefs to the Airdrop Farmer;
     5. the whole LIVE Universe, your company climbing the leaderboard.

## Open it

The `quest-steps` entry in `.claude/launch.json` (http://127.0.0.1:8800/). Wide first (2000 px), works on a phone.
The clips are not in git: `python outbox/quest-steps/record.py` makes them into `clips/` (~45 MB). Without them each
clip shows its poster.

## What is here

| File | What |
|---|---|
| `index.html`, `quest.css`, `quest.js` | the page; `QUEST` in quest.js holds every figure and both addresses |
| `anim.js` | everything that moves: the clips' loops, the sun's companies, the pipeline, the Quant Lab, the users, the leaderboard |
| `record.py` | the four clips into `clips/` and their posters into `pics/` (its docstring says how and from where) |
| `scenes/tools.html` | the robot-arm workshop (three.js), a 10 s loop drawn frame by frame by record.py |
| `capture.py` | the still pictures into `pics/`: the sky, the sun, the five companies, the builder's card, the agent, the Promo Market, and the built products' previews (`pics/apps/`, Build it Better's own list) |

No test suite: a design page is judged by the operator's eye (2026-10-30), and looked at, wide and on a phone, before it
goes to him.

## What is live and what is ours

| Step | What moves | From |
|---|---|---|
| top | the sun and five companies | our Universe mock, each cut out |
| 01 | the station, then the office, astronauts at work | LIVE cymetica.com/company/app/builder, its two steps, recorded |
| 02 | the workshop and the pipeline | our three.js scene and anim.js |
| 03 | the Quant Lab and the race | anim.js; the strategies, the counts and the rivals are examples (QUEST.lab) |
| 04 | the Promo Market and the Airdrop Farmer | their page through our read-only mirror with three sample briefs; our Universe mock, composed (the Gem Screener brought behind the farmer) |
| 05 | the Universe and the leaderboard | LIVE cymetica.com/company/app#universe (six companies on it on 2026-10-30); the leaderboard's names and points are our mock's samples (QUEST.board) |

## Decided here, the veto open

- **The podium** is gone from step 5: the whole Universe took its place, and the first screen keeps the prizes.
- **The casino chip** is gone from step 3: the Agent Casino is the race the hero agent wins.
- **The clips** stay out of git (~45 MB, and git is over its ceiling). Their posters are kept.
- **Step 4 says "your own land"**, Cymetica's own word for a slot of the Universe.
- **Four steps** (his "1. 2. 3. 4. ... 2. build products or hero agents"): the rail has four; step 2 is "Way A" and "Way
  B" on the slider, which opens on way A.
- **The strip's products:** Build it Better's 13 most visited, leaving out the platform's own pages (capture.py
  `BUILT_SKIP`).

## The contest

`outbox/quest-gemini/BRIEF.md` gives Gemini Antigravity the operator's requirements, all takes included, to build its
own guide in `outbox/quest-gemini/`. It is fenced off from this page's code, so the two are built apart. The operator
picks the better one.

## Notes

- "Breed your hero agent" and "equip your most profitable strategies" are the operator's wording. On 2026-10-28 Nexus
  said the lab-to-bot bridge was not built yet (ET-33133).
- The prize, 500,000 / 250,000 / 100,000 ET10, is the operator's figure (uv-data.js `CO.SEASON`); Cymetica has not
  confirmed it.
- The flat "2D" office he once saw in the builder is their fallback for a browser where the 3D cannot start
  (builder.js `flat()`); record.py refuses to film it.
