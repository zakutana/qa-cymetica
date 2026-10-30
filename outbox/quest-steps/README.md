# The Cymetica Quest, step by step: our mock

Asked for by the operator on 2026-10-29: a new page for the Cymetica Quest, explained in steps. The intro (join the
quest, win up to 500,000 ET10 every month), then how. It stands beside `outbox/quest` (the scroll film, still on the 5 %
revenue share), which is unchanged.

## Eleven takes

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
10. **0f21ed9a**, looked at in Firefox, his browser: the eighth take's sky back and the sun alone, every step's big
   number under its words, the Quant Lab set into space, Cymetica's sun over the live Universe, and the clips loaded
   only near their step (in Firefox a playing clip stood still while the others loaded: step 2's "animace se
   nespusti").
11. **This one** (2026-10-31), after the tenth:
   - **Deep space behind the whole page**, still while the page moves over it, its stars twinkling (anim.js), as
     Gemini's guide on 8802 has it ("koukni jak udelal gemini vsude vesmirne pozadi ... vypada to celkem huste").
   - **The first screen**: the words big on the left as the start page's, "Cymetica Quest." first and green, every
     line whole; the prize board on the right, turned the other way; the sun further right and off, whole and bright
     (a glowing core under its strands: "ted v nem jsou diry").
   - **The top has no panel**: the brand, the quest's track (a numbered hexagon a step, the lines filling as you read,
     a spark at the front) and the prize stand on the sky over a dark that fades downwards.
   - **Bullets under every heading**, each on a hexagon, strung on one line of light.
   - **Every picture further from its number** (a wider gap, the page wider); step 1's HQ further right.
   - **Step 2:** the arms beside the number; under them the pipeline, and out of it the ring of products already built,
     which turns your new app to the front as it goes live, tagged yours.
   - **Step 3:** "Quant Lab" is the green words; the Agent Casino is a point under them.
   - **Step 4:** the Promo Market's cube turns as on their page (record.py promo_cube: their CSS animations set frame by
     frame, a seamless 18 s loop, laid where the cube stands in the picture).
   - **Step 5:** the live Universe with the leaderboard's companies on it too (record.py universe: fourteen, the eight
     added in our recording browser only).

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
| 04 | the Promo Market and the Airdrop Farmer | their page through our read-only mirror with three sample briefs, its own cube turning (their CSS, filmed frame by frame); our Universe mock, composed |
| 05 | the Universe | LIVE cymetica.com/company/app#universe, recorded: its six companies and four products today, and the leaderboard's eight sample companies added to its answer in our browser |
| 05 | the leaderboard | samples (QUEST.board), with our mock's stations as marks |
| end | the two cards | LIVE cymetica.com/company/app/start, its room and its Universe, recorded; our sun over the Universe, as their poster shows none |

## Decided here, the veto open

- **Five steps again:** the rail has five. His "3 bring in users, 4 compete in the Universe and earn
  points" are its 4th and 5th, now that the agent has its own step.
- **The nine agents** are named by role (Developer, Lab scientist, Trader, QA tester, Auditor, Supervisor, three
  Researchers), as the pre-build has them; NEXUS leads them and is said in the line above.
- **The first screen's words**: "Cymetica Quest." first and green, then "Join. Earn points. / Climb the leaderboard.
  / Earn up to 500,000 ET10 / every month." with the prize green; he left the opening to us ("CYMETICA QUEST zelene
  nebo join? ... musis to vymyslet").
- **The first screen's sun** is about 80 px across its ball at 2000 px wide, top right over the board.
- **The Quant Lab** carries the Promo Market's scan lines too, faintly; he once said not to make it holographic, and
  this round asked for it set into space as the Promo Market is.
- **Step 5 is the live Universe** with the leaderboard's eight sample companies added in our recording browser, so
  the names on the board stand in the map too; the live one has six today. Nothing is sent to Cymetica: the answer is
  changed as it arrives in our browser (record.py EXTRA_COMPANIES).
- **The top bar** keeps its three parts (brand, track, prize) and drops the panel round them.
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
