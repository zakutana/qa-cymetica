# The Cymetica Quest, step by step: our mock

Asked for by the operator on 2026-10-29: a new page for the Cymetica Quest, explained in steps. The intro (join the
quest, win up to 500,000 ET10 every month), then how. It stands beside `outbox/quest` (the scroll film, still on the 5 %
revenue share), which is unchanged.

## Eight takes

1. **a1cb3cf5, 7/10**: real screenshots, each in a glass browser frame. "Nedavej to do panelu ... at to splyva."
2. **60da77f5, 4/10**: everything full screen, a flight in to the sun, the orbit with its companies. "Predchozi verze
   byla mnohem lepsi a cistsi, hlavne ty velke cislice na pozadi ... nedavej nikde tu obeznou drahu."
3. **fdfd575d**: the first take's layout, in every step a picture plus a piece of their web as a hologram.
4. **e66d68dc**: the first screen as our flyer on its side, five steps in his words, no link in a step.
5. **46cd5e1e**: Capital Maximizer's bar, a sharp sky, and an animation in every step.
6. **000eb3e8, 7.5/10**: glass, icons on tiles, the station dive into step 1, steps 2 and 3 on one screen with a slider.
7. **e4cbe7a5**: crystal glass, the HQ with its departments, the pipeline as a machine, the ring of marks, the
   Quant Lab's reactor, 18 companies in the Universe.
8. **This one** (2026-10-30), after the seventh:
   - **The glass polished clear** ("musi byt uplne pruhledne jako bys ho vylestil"): no fill and no blur anywhere,
     only rims and a glint. The top bar keeps a light dark tint, as in the seventh take.
   - **The first screen is only its slogan** beside the prize board: join the quest, earn points, climb the
     leaderboard, earn up to 500,000 ET10 monthly. The 1 to 5 list is gone.
   - **Step 1:** the HQ larger on the right; under the heading only the nine agents, led by NEXUS, named by role.
     The department cards are gone.
   - **Step 2:** the arms and the Cymetica pipeline are one machine: the pipeline runs under the arms' pad, a column
     of light rises from it while the idea is inside, and the app comes out at its end. The ring above shows the built
     products' live pages as holograms, not marks.
   - **Step 3:** the reactor stands beside its words, not a hologram, nothing over it.
   - **Step 4:** the Promo Market tilted far back as a hologram on the left, the Universe with the Airdrop Farmer and
     the Gem Screener beside it, the words on the right.
   - **The two calls at the end** are the start tutorial's two cards (its live room and its live Universe on top, the
     button below), in crystal glass, each scene moving.

## Open it

The `quest-steps` entry in `.claude/launch.json` (http://127.0.0.1:8800/). Wide first (2000 px), works on a phone.
The clips are not in git: `python outbox/quest-steps/record.py` makes them into `clips/` (~55 MB). Without them each
clip shows its poster. The lab clip needs `outbox/quant-lab-v2` served on 8801.

## What is here

| File | What |
|---|---|
| `index.html`, `quest.css`, `quest.js` | the page; `QUEST` in quest.js holds every figure, both addresses, the departments and the ideas |
| `anim.js` | everything that moves: the clips' loops, the pipeline, the ring of products, the users, the leaderboard |
| `record.py` | the seven clips into `clips/` and their posters into `pics/` (its docstring says how and from where) |
| `scenes/tools.html` | the robot-arm workshop (three.js), a 10 s loop drawn frame by frame by record.py |
| `capture.py` | the still pictures into `pics/`: the sky, the sun, the five companies, the builder's card, the Promo Market, the built products' live pages (`pics/apps/`) |

`pics/board/` holds copies of our Universe mock's station renders (`outbox/company-live/shots`).

No test suite: a design page is judged by the operator's eye (2026-10-30), and looked at, wide and on a phone, before it
goes to him.

## What is live and what is ours

| Step | What | From |
|---|---|---|
| top | the sun and five companies | our Universe mock, each cut out |
| 01 | the HQ, astronauts at work | LIVE cymetica.com/company/app/builder, recorded; the nine agents and their roles are the live builder's pre-build (builder.js PRE) |
| 02 | the workshop and the pipeline | our three.js scene and anim.js; the ideas map to real Build it Better products |
| 02 | the ring of products | LIVE: each product's own page, captured (capture.py apps) |
| 03 | the Quant Lab's reactor | outbox/quant-lab-v2's Coming soon mode, filmed: a simulation, and it says so on screen |
| 04 | the Promo Market and the Airdrop Farmer | their page through our read-only mirror with three sample briefs; our Universe mock, composed |
| 05 | the Universe and the leaderboard | our Universe mock with 18 of its sample companies (the live one has six); the leaderboard's names and points are samples (QUEST.board) |
| end | the two cards | LIVE cymetica.com/company/app/start, its room and its Universe, recorded; our sun over the Universe, as their poster shows none |

## Decided here, the veto open

- **Five steps again:** the rail has five. His "3 bring in users, 4 compete in the Universe and earn
  points" are its 4th and 5th, now that the agent has its own step.
- **The nine agents** are named by role (Developer, Lab scientist, Trader, QA tester, Auditor, Supervisor, three
  Researchers), as the pre-build has them; NEXUS leads them and is said in the line above.
- **The companies by the sun** are about a quarter of its disc. That is over his earlier eighth, because he said they
  were still too small.
- **The clips** stay out of git. Their posters are kept.

## The contest

`outbox/quest-gemini/BRIEF.md` gives Gemini Antigravity the operator's requirements to build its own guide in
`outbox/quest-gemini/`. It is fenced off from this page's code. The operator picks the better one.

## Notes

- "Breed your hero agent" is the operator's wording. On 2026-10-28 Nexus said the lab-to-bot bridge was not built yet
  (ET-33133).
- The prize, 500,000 / 250,000 / 100,000 ET10, is the operator's figure (uv-data.js `CO.SEASON`); Cymetica has not
  confirmed it.
