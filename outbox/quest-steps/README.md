# The Cymetica Quest, step by step: our mock

Asked for by the operator on 2026-10-29: a new page for the Cymetica Quest, explained in steps. The intro (join the
quest, win up to 500,000 ET10 every month), then how. It stands beside `outbox/quest` (the scroll film, still on the 5 %
revenue share), which is unchanged.

## Ten takes

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
9. **827a4b4a**: the floating bar with the quest's path, the HQ alone and close, the whole Quant Lab with the agent by
   the fifth second, the live Universe big, smaller doors; a glowing-star sky and the start tutorial's sun with its
   companies on the first screen, both taken back in the tenth.
10. **This one** (2026-10-30), after the ninth, looked at in Firefox, his browser:
   - **The first screen's sky is the eighth take's again** ("vesmir na uvodni strane ... byl predtim top"), and the
     sun stands alone, smaller and further off, no companies round it ("ty tam nedavej").
   - **Every step as step 2 was**: STEP 0N, the words, and under them the big number; nothing beside the words.
   - **Step 2:** the ring of products beside the number, under the words' level ("moc vysoko").
   - **Step 3:** the Quant Lab's page stands in space as the Promo Market does ("jen placka na tme"): turned towards
     its words, its edges melting into the dark, a light behind it and a pool of light under it.
   - **Step 5:** Cymetica's sun over the live Universe where theirs stands; the live page draws its sun on canvases of
     its own, which the map's recording left out, so the clip showed only a star ("co to ma byt to slunce?").
   - **The clips load only when their step is near** and let go when it is far: in Firefox a playing clip's time stood
     still (never paused) while the page's other clips were loading. That was step 2's "animace se nespusti";
     measured in Firefox, every step's clip now plays there and in Chrome, down the page and back.

## Open it

The `quest-steps` entry in `.claude/launch.json` (`python outbox/quest-steps/serve.py 8800`, http://127.0.0.1:8800/).
Wide first (2000 px), in Firefox (his browser) and Chrome; the phone is not looked at for now ("na phone zatim kasli"). The clips are not in git:
`python outbox/quest-steps/record.py` makes them into `clips/` (~65 MB). Without them each clip shows its poster. The
lab clip serves `outbox/quant-lab-v2` itself; the office, the Universe and the doors read live pages.

## What is here

| File | What |
|---|---|
| `index.html`, `quest.css`, `quest.js` | the page; `QUEST` in quest.js holds every figure, both addresses, the departments and the ideas |
| `anim.js` | everything that moves: the clips' loops, the pipeline, the ring of products, the users, the leaderboard |
| `record.py` | the seven clips into `clips/` and their posters into `pics/` (its docstring says how and from where) |
| `scenes/tools.html` | the robot-arm workshop (three.js), a 10 s loop drawn frame by frame by record.py |
| `capture.py` | the still pictures into `pics/`: the sky, the sun, the Promo Market, the built products' live pages (`pics/apps/`) |
| `serve.py` | the page on 8800 with Range requests, for the clips' seeks |

`pics/board/` holds copies of our Universe mock's station renders (`outbox/company-live/shots`).

No test suite: a design page is judged by the operator's eye (2026-10-30), and looked at, wide and on a phone, before it
goes to him.

## What is live and what is ours

| Step | What | From |
|---|---|---|
| top | the sky | ours (capture.py sky) |
| top | the sun | our Universe mock's sun, alone (capture.py sun); also over step 5's live Universe |
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
- **The first screen's sun** is about a third smaller than the eighth take's (its ball about 106 px at 2000 px wide),
  for "too close".
- **The Quant Lab** carries the Promo Market's scan lines too, faintly; he once said not to make it holographic, and
  this round asked for it set into space as the Promo Market is.
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
