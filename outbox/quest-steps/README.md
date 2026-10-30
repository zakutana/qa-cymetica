# The Cymetica Quest, step by step: our mock

Asked for by the operator on 2026-10-29: a new page for the Cymetica Quest, explained in steps. The intro (join the
quest, win up to 500,000 ET10 every month), then how. It stands beside `outbox/quest` (the scroll film, still on the 5 %
revenue share), which is unchanged.

## Seven takes

1. **a1cb3cf5, 7/10**: real screenshots, each in a glass browser frame. "Nedavej to do panelu ... at to splyva."
2. **60da77f5, 4/10**: everything full screen, a flight in to the sun, the orbit with its companies. "Predchozi verze
   byla mnohem lepsi a cistsi, hlavne ty velke cislice na pozadi ... nedavej nikde tu obeznou drahu."
3. **fdfd575d**: the first take's layout, in every step a picture plus a piece of their web as a hologram.
4. **e66d68dc**: the first screen as our flyer on its side, five steps in his words, no link in a step.
5. **46cd5e1e**: Capital Maximizer's bar, a sharp sky, and an animation in every step.
6. **000eb3e8, 7.5/10**: glass, icons on tiles, the station dive into step 1, steps 2 and 3 on one screen with a slider.
7. **This one** (2026-10-30), after the sixth:
   - **Crystal glass** for the bar, the prize board, the departments, the leaderboard and the two calls at the end:
     clear, glossy, a rim of light ("ne ta tvoje zakalena plocha").
   - **The words under every heading are much smaller.** No point stands on a tile of an icon ("vsude takove stejne
     kostky").
   - **The companies by the sun** stand still, are bigger and are grey.
   - **The board** says who wins each slot (most points), with no "could be yours". The first screen's five steps
     are a list, not links.
   - **Step 1:** the HQ only, without the zoom or the station. Under it, the four departments with their agents' roles
     and pictures; no "7 rooms".
   - **The slider is gone.** Breed your hero agent is its own step again, so there are five.
   - **Step 2**, "Build your own products": the Cymetica pipeline as a machine. An idea is typed in, six chambers
     (Spec, Design, Build, Security, Deploy, Hosting) light one after another, and your app comes out live, a real
     product of Build it Better each time. Beside it, a ring of the built products' marks as holograms, turned by
     dragging.
   - **Step 3:** the Quant Lab's reactor from `outbox/quant-lab-v2` (another session's page, its Coming soon mode).
   - **Step 5**, "Farm your points": the leaderboard with each company's station as its mark, and a Universe of 18
     companies with Cymetica's sun.

## Open it

The `quest-steps` entry in `.claude/launch.json` (http://127.0.0.1:8800/). Wide first (2000 px), works on a phone.
The clips are not in git: `python outbox/quest-steps/record.py` makes them into `clips/` (~55 MB). Without them each
clip shows its poster. The lab clip needs `outbox/quant-lab-v2` served on 8801.

## What is here

| File | What |
|---|---|
| `index.html`, `quest.css`, `quest.js` | the page; `QUEST` in quest.js holds every figure, both addresses, the departments and the ideas |
| `anim.js` | everything that moves: the clips' loops, the pipeline, the ring of products, the users, the leaderboard |
| `logos.js` | the products' marks for the ring and the pipeline's output |
| `record.py` | the five clips into `clips/` and their posters into `pics/` (its docstring says how and from where) |
| `scenes/tools.html` | the robot-arm workshop (three.js), a 10 s loop drawn frame by frame by record.py |
| `capture.py` | the still pictures into `pics/`: the sky, the sun, the five companies, the builder's card, the Promo Market |

`pics/crew/` and `pics/board/` are copies of our Universe mock's renders (`outbox/company-live/shots`): its rooms, its
agents by role, its stations.

No test suite: a design page is judged by the operator's eye (2026-10-30), and looked at, wide and on a phone, before it
goes to him.

## What is live and what is ours

| Step | What | From |
|---|---|---|
| top | the sun and five companies | our Universe mock, each cut out |
| 01 | the HQ, astronauts at work | LIVE cymetica.com/company/app/builder, recorded; the departments and roles are the live builder's pre-build (builder.js PRE), pictured by our mock |
| 02 | the workshop and the pipeline | our three.js scene and anim.js; the ideas map to real Build it Better products |
| 02 | the products' marks | Gem Screener's is its own icon; every other product has no logo yet, so its mark is ours (logos.js) |
| 03 | the Quant Lab's reactor | outbox/quant-lab-v2's Coming soon mode, filmed: a simulation, and it says so on screen |
| 04 | the Promo Market and the Airdrop Farmer | their page through our read-only mirror with three sample briefs; our Universe mock, composed |
| 05 | the Universe and the leaderboard | our Universe mock with 18 of its sample companies (the live one has six); the leaderboard's names and points are samples (QUEST.board) |

## Decided here, the veto open

- **Five steps again:** the hero list and the rail have five. His "3 bring in users, 4 compete in the Universe and earn
  points" are its 4th and 5th, now that the agent has its own step.
- **The departments' cards** show the four of the pre-build. NEXUS (Command) and the supervisor (Operations) are left
  out, so as not to crowd them.
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
