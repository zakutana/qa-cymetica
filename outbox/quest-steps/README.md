# The Cymetica Quest, step by step: our mock

Asked for by the operator on 2026-10-29: a new page for the Cymetica Quest, explained in steps. The intro (join the
quest, win up to 500,000 ET10 every month), then how. It stands beside `outbox/quest` (the scroll film, still on the 5 %
revenue share), which is unchanged.

## Thirteen takes

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
11. **b7891eca** (2026-10-31): deep space behind the whole page with twinkling stars (as Gemini's guide has it), the
   first screen's words big on the left, the top a quest track with no panel, hexagon bullets, the Promo Market's cube
   turning, fourteen companies in the Universe. "To uz je husty 1 screen."
13. **This one** (2026-10-31), after the twelfth:
   - **No hexagon** in the mark or the track ("nelibi se mi ten hexagon co pouzivas v logu a stepech"): the mark a
     green sun with a world going round it on its orbit, the track's steps round lights, the pipeline's mark a ring.
   - **One space everywhere** ("pozadi za headquarters je divne, ma byt stejne jako vsude jinde v questu"; "musi to
     ve vsech prohlizecich byt stejne"): the HQ, the Universe and the Airdrop Farmer filmed with their own skies hidden,
     on black (record.py), and the black keyed away in the page through WebGL (anim.js keyed), so the page's own sky
     stands behind them; the same in Firefox, Chrome and WebKit (a video's own alpha would not play in Safari).
   - **Spacing** ("vsude jsou odrazky moc blizko sebe ... urcit idealni rozestupy delky"): lines 1.7 high, points 26
     px apart, the heading 40 px above them, a measure of about sixty characters, every ray 46 px; no word left alone
     on a line.
   - **Step 3**: the Promo Market on the left, the Universe with its products on the right ("ten promo market screen
     musi byt vlevo a vpravo ten universe s produkty"; it stood so before, so now they stand apart, turned less, bigger).
   - **Step 5**: the board beside the Universe in its space, clear of the orbits and the companies ("nema prekryvat
     ten vesmir ... at nestini universe").
   - The links' arrow drawn, not a character (WebKit drew another glyph).
12. **a43a4494** (2026-10-31), after the eleventh:
   - **His order**: start, build, market, the hero agent, climb ("po build produkt bude market it ... a az pak bude
     breed your agent"); **every step's words on the left** ("vsechno ma byt nalevo"), wide ("proc je to v takovem
     uzkem sloupci?"), the picture to the right and lower ("na preskacku").
   - **Rays for bullets**, as the MADE BY plate in the Universe has its two, a glint running along each.
   - **Each step names its department** ("na kazdem stepu ... spojitost s nejakym departmentem"): Development takes
     your idea to Build it Better, Marketing writes your briefs for the Promo Market, the Quant Lab searches. **Every
     product named links to it**, lit: Build it Better, the Promo Market, the Agent Casino, the Universe.
   - **Points**: for your products' use and your agent's trades (his words, 2026-10-31).
   - **Step 1:** the whole HQ with space round it ("proc ty headquarters mas useknute nahore a dole?"), "4 departments ·
     9 AI agents, led by NEXUS", no roles named, no "You approve what goes out".
   - **Step 2:** the arms higher, beside the words, apart from the pipeline; a new workshop (scenes/tools.html):
     Build it Better's name in neon on an island of its hexagons, a drone bringing the idea down a beam, pistons,
     cables and running lights on the arms, fingers that close on each panel, a seam welded white-hot and cooling,
     sparks that fall and bounce, each panel drawing what it shows as it locks, a scan up the finished app. The
     pipeline: numbered chambers, a ring filling round each icon, the working one lifted and swept by light, its own
     line ("Writing the code · 52%", "Live · Gem Screener"), a comet on its rail, Build it Better's hexagons in its
     glass. No "134 apps already built" anywhere.
   - **Step 4:** the Quant Lab at its own pace (record.py lab: 23.6 s, the agent born at 17.72 s), started far enough
     in that the agent is born two seconds after the step's words are read: anim.js counts the words (45 today), reads
     them at five a second from when the picture is a third on screen, so it starts at 6.7 s and the agent comes 11 s
     after you arrive.
   - **Step 5:** the Universe bigger, the board in it on its right as the first screen's, yours passing over each
     company it beats (they stood on top of each other mid-pass before).
   - **The doors**: "Start a company and compete" over step 1's HQ, "Explore the Universe" over step 5's Universe,
     each a big picture with its words under it and a round lit arrow. The brand says only CYMETICA QUEST; the first
     screen's sun further right.

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
| 01 | the HQ, astronauts at work | LIVE cymetica.com/company/app/builder, recorded without its sky and drifting rocks, keyed; its four departments and nine agents are the live builder's pre-build (builder.js PRE, data.js TEMPLATES) |
| 02 | the workshop and the pipeline | our three.js scene and anim.js; Build it Better's name and hexagons from its own picture (og/app/build-it-better.png); the ideas map to real Build it Better products |
| 02 | the ring of products | LIVE: each product's own page, captured (capture.py apps) |
| 03 | the Promo Market and the Airdrop Farmer | their page through our read-only mirror with three sample briefs, its own cube turning (their CSS, filmed frame by frame); our Universe mock, composed |
| 04 | the Quant Lab's page | outbox/quant-lab-v2's Coming soon mode, at its own pace: a simulation, and it says so on screen |
| 05 | the Universe | LIVE cymetica.com/company/app#universe, recorded without its sky, keyed: its six companies and four products today, and the leaderboard's eight sample companies added to its answer in our browser |
| 05 | the leaderboard | samples (QUEST.board), with our mock's stations as marks |
| end | the two doors | step 1's HQ and step 5's Universe, the same clips |

## Decided here, the veto open

- **Five steps, in his order of 2026-10-31**: start, build, market, the hero agent, climb.
- **"Na preskacku"** is read as the picture standing lower than the words, to their right; the words stay on the
  left in every step, as he said in the same message ("vsechno ma byt nalevo").
- **Marketing** is not in the pre-build (Cymetica QA, Development, Quant Lab, Trading desk): it is a department the
  owner adds (data.js, ET-32484). Step 3 still says "your Marketing department", as the step is the owner's next
  move; step 1's "4 departments" is the pre-build's.
- **The links**: every product a step names links to its live page (QUEST.links), each answering 200 on 2026-10-31.
  Until the twelfth take the two doors at the end were the only links ("to bude az na konci"); he asked for them.
- **The Quant Lab's timing**: five words a second (a skim) from when its picture is a third on screen, then two
  seconds; with a longer text it starts earlier, never before its first frame.
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
- **The clips** stay out of git. Their posters are kept.
- **Keyed clips** (the HQ, the Universe, the farmer, both doors): filmed on black and keyed in the page, alpha from
  each pixel's brightest channel (0.025 to 0.12), so the darkest metal stays whole and the black goes. A browser
  without WebGL shows them on black. Playwright's WebKit on Windows never finishes loading a WebM (the twelfth take
  hangs it the same way), so WebKit was looked at with the posters, which are keyed by the same shader.

## The contest

`outbox/quest-gemini/BRIEF.md` gives Gemini Antigravity the operator's requirements to build its own guide in
`outbox/quest-gemini/`. It is fenced off from this page's code. The operator picks the better one.

## Notes

- "Breed your hero agent" is the operator's wording. On 2026-10-28 Nexus said the lab-to-bot bridge was not built yet
  (ET-33133).
- The prize, 500,000 / 250,000 / 100,000 ET10, is the operator's figure (uv-data.js `CO.SEASON`); Cymetica has not
  confirmed it. So are the points for your products' use and your agent's trades (2026-10-31).
- What each department does is the live builder's own words: Development "drafts a Build it Better request" (it does
  not build; the pipeline does), Marketing "write briefs for my own Build it Better apps", the Quant Lab "keeps
  searching for a profitable agent", the Trading desk drafts "a seat at an Agent Casino table".
