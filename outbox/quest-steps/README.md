# The Cymetica Quest, step by step: our mock

Asked for by the operator on 2026-10-29: a new page for the Cymetica Quest, explained in steps. The intro (join the
quest, win up to 500,000 ET10 every month), then how. It stands beside `outbox/quest` (the scroll film, still on the 5 %
revenue share), which is unchanged.

## Nine takes

1. **a1cb3cf5, 7/10**: real screenshots, each in a glass browser frame. "Nedavej to do panelu ... at to splyva."
2. **60da77f5, 4/10**: everything full screen, a flight in to the sun, the orbit with its companies. "Predchozi verze
   byla mnohem lepsi a cistsi, hlavne ty velke cislice na pozadi ... nedavej nikde tu obeznou drahu."
3. **fdfd575d**: the first take's layout, in every step a picture plus a piece of their web as a hologram.
4. **e66d68dc**: the first screen as our flyer on its side, five steps in his words, no link in a step.
5. **46cd5e1e**: Capital Maximizer's bar, a sharp sky, and an animation in every step.
6. **000eb3e8, 7.5/10**: glass, icons on tiles, the station dive into step 1, steps 2 and 3 on one screen with a slider.
7. **e4cbe7a5**: crystal glass, the HQ with its departments, the pipeline as a machine, the ring of marks, the
   Quant Lab's reactor, 18 companies in the Universe.
8. **5f837999**: the glass polished clear, the first screen only its slogan, the HQ larger with its nine agents named,
   the arms and the pipeline one machine, the ring of live pages, the reactor beside its words, the Promo Market
   tilted far back, the start tutorial's two cards at the end.
9. **This one** (2026-10-30), after the eighth ("na takovych detailech zalezi"):
   - **The sky's stars glow** (capture.py sky): thousands with a soft glow, dozens bright with a halo, a dozen with
     spikes, over the flyer's nebula; no more "trapne tecky".
   - **The sun and the companies round it are the live start tutorial's own scene** (capture.py hero: six stations on
     two orbits in its perspective), screened onto the sky where the sun stands; the slogan stands under the orbits.
   - **The top bar floats**: a sheet of crystal off the top edge, the quest's path across it as Capital Maximizer's
     rail, hexagons joined by lines that light as far as you have come; the faintest tint, no band.
   - **The step numbers** are faint again (the first take's stroke) and stand above the words, so a heading crosses
     only their foot.
   - **Step 1:** the HQ alone, close, as his own screenshot framed it (record.py office, the camera at 0.72); the Start
     card gone; the nine agents named in one quiet line, no chips.
   - **Step 2:** the ring lower, beside the words; the step on one screen; the workshop clip preloaded whole, asked to
     play again a second after it comes on screen, its poster behind it (the one thing not reproduced: in his browser
     the clip did not start).
   - **Step 3:** the Quant Lab's page whole, heading, tiles and reactor; its first four stages in 5 s on a bent clock
     (record.py LAB_WARP), then the agent found at the reactor's own pace.
   - **Step 5:** the LIVE Universe, big, its sky, sun, six companies and four products; the leaderboard smaller, over
     its foot.
   - **The two doors** are smaller (420 px).
   - **serve.py** serves the page on 8800 with Range requests; the stock server answered every seek with the whole file.

## Open it

The `quest-steps` entry in `.claude/launch.json` (`python outbox/quest-steps/serve.py 8800`, http://127.0.0.1:8800/).
Wide first (2000 px); the phone is not looked at this round ("na phone zatim kasli"). The clips are not in git:
`python outbox/quest-steps/record.py` makes them into `clips/` (~65 MB). Without them each clip shows its poster. The
lab clip serves `outbox/quant-lab-v2` itself; the office, the Universe and the doors read live pages.

## What is here

| File | What |
|---|---|
| `index.html`, `quest.css`, `quest.js` | the page; `QUEST` in quest.js holds every figure, both addresses, the departments and the ideas |
| `anim.js` | everything that moves: the clips' loops, the pipeline, the ring of products, the users, the leaderboard |
| `record.py` | the seven clips into `clips/` and their posters into `pics/` (its docstring says how and from where) |
| `scenes/tools.html` | the robot-arm workshop (three.js), a 10 s loop drawn frame by frame by record.py |
| `capture.py` | the still pictures into `pics/`: the sky, the sun with its companies (`hero.webp`), the Promo Market, the built products' live pages (`pics/apps/`) |
| `serve.py` | the page on 8800 with Range requests, for the clips' seeks |

`pics/board/` holds copies of our Universe mock's station renders (`outbox/company-live/shots`).

No test suite: a design page is judged by the operator's eye (2026-10-30), and looked at, wide and on a phone, before it
goes to him.

## What is live and what is ours

| Step | What | From |
|---|---|---|
| top | the sky | ours (capture.py sky) |
| top | the sun and the companies round it | LIVE cymetica.com/company/app/start, its own scene, cut round the sun |
| 01 | the HQ, astronauts at work | LIVE cymetica.com/company/app/builder, recorded; the nine agents and their roles are the live builder's pre-build (builder.js PRE) |
| 02 | the workshop and the pipeline | our three.js scene and anim.js; the ideas map to real Build it Better products |
| 02 | the ring of products | LIVE: each product's own page, captured (capture.py apps) |
| 03 | the Quant Lab's page | outbox/quant-lab-v2's Coming soon mode, filmed on a bent clock: a simulation, and it says so on screen |
| 04 | the Promo Market and the Airdrop Farmer | their page through our read-only mirror with three sample briefs; our Universe mock, composed |
| 05 | the Universe | LIVE cymetica.com/company/app#universe, recorded: its six companies and four products today |
| 05 | the leaderboard | samples (QUEST.board), with our mock's stations as marks |
| end | the two cards | LIVE cymetica.com/company/app/start, its room and its Universe, recorded; our sun over the Universe, as their poster shows none |

## Decided here, the veto open

- **Five steps again:** the rail has five. His "3 bring in users, 4 compete in the Universe and earn
  points" are its 4th and 5th, now that the agent has its own step.
- **The nine agents** are named by role (Developer, Lab scientist, Trader, QA tester, Auditor, Supervisor, three
  Researchers), as the pre-build has them; NEXUS leads them and is said in the line above.
- **The companies by the sun** are their own start page's, at its sizes, since "realistic" is what that page is.
- **Step 5 is the live Universe**, six companies today; the seventh take's eighteen were our mock's samples
  (record.py universe-mock still makes that clip). His words this round were about the sky, and the live sky is the
  one he called better.
- **The Quant Lab's clock** runs 3.3 times faster through its first four stages so the agent is found at the fifth
  second, then at its own pace; nothing in the lab's page was changed.
- **The clips** stay out of git. Their posters are kept.

## The contest

`outbox/quest-gemini/BRIEF.md` gives Gemini Antigravity the operator's requirements to build its own guide in
`outbox/quest-gemini/`. It is fenced off from this page's code. The operator picks the better one.

## Notes

- "Breed your hero agent" is the operator's wording. On 2026-10-28 Nexus said the lab-to-bot bridge was not built yet
  (ET-33133).
- The prize, 500,000 / 250,000 / 100,000 ET10, is the operator's figure (uv-data.js `CO.SEASON`); Cymetica has not
  confirmed it.
