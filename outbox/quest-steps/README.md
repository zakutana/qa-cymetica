# The Cymetica Quest, step by step: our mock

Asked for by the operator on 2026-10-29: a new page for the Cymetica Quest, explained in steps. The intro (join the
quest, win up to 500,000 ET10 every month), then how. It stands beside `outbox/quest` (the scroll film, still on the 5 %
revenue share), which is unchanged.

## Sixteen takes

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
16. **This one** (2026-11-01), the words made to say what the quest is, his sentences nearly as he wrote them:
   step 1 joins the Universe to battle other companies for points; step 2 turns your idea into real products with the
   Cymetica Pipeline (the link to Build it Better) and earns points when real users use them; step 3 "Market it. Bring
   in more users." with the Promo Market alone, nothing of departments or points; step 4 "Breed your own hero agent in
   Quant Lab.", its researchers finding strategies, more points when those agents trade, tournaments in the Agent
   Casino or trading alone; step 5 "Farm the points.", into the top 3 paid slots. What earns points ("vsude kde se
   vysvetluje to co vydelava pointy musi byt nejak spesl zvyrazneno") is a lit green panel with a "+ pts" tag. The
   leaderboard wider (660 px, a third of the screen below 2000), each company on one line, its points a column apart
   from its name. The Quant Lab's BUILD no longer runs its setup into the grid (outbox/quant-lab-v2 ql.js: the chips
   shrink to fit between 1300 and about 1480 px, the width the clip is filmed at). Step 5's Universe: every company
   turned along its lane until no two ships stand near each other (record.py UV_SPREAD), yours held still on the
   map's left with a YOUR COMPANY tag over it. Its second round: the name plates in steps 3 and 5 are the live
   Universe's own (uv.css .b3, copied), the Promo Market with one of its own over its cube, lit with its building
   while the pointer is on its name in the words; step 3 says again that your products can stand on your own land
   in the Universe; what earns points has no box any more, only its green words and the "+ pts" tag. Its third round:
   step 3's products are links, each lit under the pointer with a thin green line round its whole shape and two lights
   running along it (record.py outlines, outlines.js), the cube's edges green, the plate over the Promo Market gone;
   four of the map's free slots on the lanes (record.py MARKET slots), one in front and three behind, so land is seen
   to be for sale; the pipeline called Build it Better's, each chamber in its own colour with its own coloured icon;
   the prize board turned further (26 degrees); step 3 "Get seen."; what earns points always the last line; the first
   door just "Start a company". Its fifth round, the workshop (scenes/tools.html): the whole forge works in the colour
   of the chamber the panel is in, the same clock: arms, lances, sparks, tethers, laser, lights on the armour, wall and
   floor, a beat across the deck as each starts; the deck's rim is the pipeline's dial, six arcs filling in turn; the name
   real channel letters with a neon tube round every outline, over twice its size, white and green as the page's headings
   and only those ("nedavej do vsech barev to je tragicke"), each striking from half power to full left to right, a surge
   going live; all six on the shockwaves and the launch beam. The gem on the lane inside, back and left, clear of the
   farmer's plate (record.py MARKET gl, gx); the Vault holds its own piles of money (record.py office: u3d.js piles() at
   full, in the recording browser only); step 5 "Farm points. Climb the leaderboard." with three lines; the Universe a
   link in step 1's words only; the last section's kicker "Enter the Universe". Its sixth round ("porad mas to obramovani
   proste blbe, jen u agent casina je to dobre"): the gem bobs and the farmer rocks and the line lay tight on one moment
   of them, the Promo Market's ring of words was left out of its shape; now each line is a sticker's edge round all it
   does (record.py outlines), the casino's kept as it was, and the cube's goes round its outside only, its corners read
   as they turn (anim.js). The bar's figure, the two first buttons and the doors' arrows are the live Universe's riveted
   plate, no pills or balls. Step 1's departments are cards with their real pictures, as the live Add department dialog
   has them (pics/agents, from static/company/shots; the manager's, which has no file, drawn by their renderer in our
   browser). The forge calmer ("asi prehnane barevny"): the chamber's colour only in the arms' lights, what they strike
   with and the rim's dial; deck, wall, light on the armour and the going live in the page's cyan and green. Its seventh
   (of the sixth: "ty nove tlacitka jsou humus ... obramovani porad stejne jeste horsi"): chips as before with the live
   Add department chip's round head; buttons copied from Agent Casino's .at-btn; forge and pipeline panel in cyan and
   green, only the panel's icons coloured; orbit and building clips filmed frame by frame on the page's clock, each
   outline read at the same moments and played by the clip's time, tight and moving with the thing. Then step 3's cube
   over the Universe's Promo Market too, as an object of the scene in our recording browser (record.py UV_CUBE; step 5's
   clip and the door's). The Universe's clip no longer grainy ("takovy zrnity"): filmed frame by frame at 1778 wide, the
   width it is drawn on his screen, 24 Mbit/s, and the key drops the codec's noise in the black. All four outlines move.
15. **Gemini's fork of this page, adopted** (2026-10-31). Antigravity copied this folder at 2201936a
   (the fourteenth take's first round) to `Downloads\cymetica\outbox\quest-steps` and served it on 8765; the operator:
   "NAD TEBOU VYHRAVA ma vse lepsi, jen ten step s market it bych zmenil". Its index.html, quest.css, quest.js,
   anim.js and scenes/tools.html are here byte for byte (its last writes 19:06 to 20:53; read and written, then
   compared with `cmp`), the workshop clip drawn again from its scene by record.py, and only one thing of ours kept
   beside it: the Quant Lab clip of the second round (30 frames a second, none repeated; its fork had the 25 fps one he
   had called "sekana"). So its mark, its hero buttons, its HQ panel, its workshop and its step 5 are the page now;
   the second and third rounds below (the Title logo, the sun moved, step 5 mirrored) are not.
   - **Step 3, the one he changed** ("vyhodil bych proste ten screen ze stranky a nechal bych jen orbitu, v popredi
     bude velka budova Promo marketu co mame ve vesmiru a nad ni bude ta krychle co tam mas ted a v ni viditelne
     produkty v universu co jsou a mensi, a pridat i dozadu nekde agent casino na orbitu"): no page screenshot; the
     orbit across the stage, the farmer and the gem on their lanes, further off than before (read: "a mensi" is the
     products on the orbit, as in the fourteenth take's second round), the Agent Casino behind on the outer lane; our
     Universe's Promo Market (u3d.js adPromo) big in front on the right, its own magenta hologram, cards, searchlights
     and airship hidden, its band without its figure; over its projector the Promo Market's live cube of the third
     round, the Universe's three products on its faces (Gem Screener, Agent Casino, Airdrop Farmer, two faces each),
     12.5 % of the clip a side. Two clips of one camera (record.py market): the orbit keyed as light, the building
     keyed hard over it, so its dark metal does not let the sky through. Users walk from the building to the farmer.
   - **Its second round** ("step 3 tam mas nejake divne slunce, to smaz a chybi ti vzducholod kolem promo marketu a na
     poslednim kroku vylepsi ten leaderboard screen moc male marginy ... a je to cele male"): the sun gone from step
     3's orbit; the PROMO airship back round the building, its clip one lap of the airship long (30 s, the Universe's
     80 s lap would have jumped back at every loop), everything else of the building turned to repeat at that length;
     the picture panned so the airship's far side stays in it (measured over a lap: its hull 58 to 92 % across). The
     leaderboard in step 5 a third bigger: 452 px wide, rows 60 px apart, its names 16 px, more room inside and
     round it, a little lower so it leaves the farmer clear.
14. **c71c5ba3** (2026-10-31), after the thirteenth:
   - **The mark** ("logo je velmi trapne"): made as Cymetica's own product marks are (Agent Casino's, live): a dark
     disc in a ring of their cyan-to-green, a dotted ring inside, two chevrons climbing, cyan under green; the name
     stacked beside it, CYMETICA small over QUEST.
   - **Sharp** ("headquarters mi prijde jeste trochu rozmazane a build it better taky"): the HQ drawn at 1.5 and cut to
     itself when filmed (1500 x 1132, it had about 800 px), the Universe the same (1600 x 862); the workshop at 1920 x
     1080 with no depth of field. Looked at with a pixel ratio of 1.5 too.
   - **The workshop** ("az moc sviti vse", "ta zed na pozadi s napisem ma byt na miste, nema se hybat"): the camera
     still (the wall and its name do not move by a pixel between frames), bloom 0.55 to 0.3, the neon 1.8 to 1.3.
   - **The orbits** ("si nejak smazal ty obezne drahy ... jsou skoro neviditelne"): the lanes are light of 2 to 7 %,
     which the HQ's key cut away; the two Universes get their own key (data-key="glow"), which lays dim light onto the
     page's sky as light, and a dark under them as their own sky was.
   - **Step 3** ("jsou asi moc nahore", "co je to jako za animace nejakeho pruhu pres ty apky"): the farmer and the gem
     each set on a lane, the camera raised over them; the stripe was our Universe mock's arc (work going in to
     Cymetica), now off; the Universe in the middle of the band, the Promo Market at its foot, the users walking into
     the farmer's ring.
   - **Step 4** ("jak najedu na ten slide tak uz chci aby se hned za 2 sekundy zrodil agent"): every time the step
     comes on screen the clip starts two seconds before the birth (measured 2.2 s in Firefox and Chrome), then loops
     whole.
   - **Step 5** ("ma byt vetsi mnohem ten vesmir a ta tabule v nem jakoby mensi, podobne jak to je v live aplikaci"):
     the whole live Universe, filmed with its sun in the middle and its outer lane whole, 1,250 px across; the board
     300 px, tilted, in its bottom-right corner over the outer lane, where no company stands, as the live map has its
     own.
   - **Its second round**, the same evening:
     - **Step 3**: the farmer and the gem filmed from further off ("je zas moc velke na orbite ty produkty"); the
       Promo Market's page gone, its cube in its place, big ("misto screenu ... jen tu 3D krychli a na ni se budou
       promitat ty produkty"): CSS 3D glass on its beam, turning in 32 s, four live product pages on its sides.
     - **Step 4**: the Quant Lab drawn frame by frame on Playwright's clock, 30 frames a second, none repeated ("je
       takova sekana, mela by byt top plynula"); the window's video before was 25 a second, as its screencast came.
     - **Step 5**: the Universe 270 px lower ("dat cely universe dolu niz"), the board beside the words above it,
       turned towards the map, 370 px ("vedle texty na opacnou stranu otoceny ten screen a to vetsi"), clear of every
       company.
     - **The first screen's sun** a ball's length (108 px) right and down; **the doors** a fifth smaller.
   - **Its third round**:
     - **The mark**: the Title logo, his pick of the five in `logos/` ("toto logo je v klidu"); the chip mark before
       it was "ciste claude design template".
     - **Step 3's cube is the Promo Market's own** ("CO TO JE ZA HNUSNOU KOSTKU? MA BYT JAK NA
       https://cymetica.com/promo-market"): their markup (promo_market_v2.js holo()) and their stylesheet's whole cube
       block copied, its .stage renamed .hstage; on a corner, swaying, floating, its faces' pages changing every 2.4 s as
       theirs; only its size is ours (11.5vw a side). The cube drawn here before is gone.
     - **Step 5 as the live map, the board on the other side** ("tak nejak jak je to live ale tu tabuli bych jen dal
       napravo z druhe strany"): the Universe 1,300 px across, its board in the top right corner over its outer lane,
       turned towards the map, as the live map has its own at the top left.
13. **ad9510a3** (2026-10-31), after the twelfth:
   - **No hexagon** in the mark or the track ("nelibi se mi ten hexagon co pouzivas v logu a stepech"): the mark a
     green sun with a world going round it on its orbit, the track's steps round lights, the pipeline's mark a ring.
   - **One space everywhere** ("pozadi za headquarters je divne, ma byt stejne jako vsude jinde v questu"; "musi to
     ve vsech prohlizecich byt stejne"): the HQ, the Universe and the Airdrop Farmer filmed with their own skies hidden,
     on black (record.py), and the black keyed away in the page through WebGL (anim.js keyed), so the page's own sky
     stands behind them; the same in Firefox, Chrome and WebKit (a video's own alpha would not play in Safari).
   - **Spacing** ("vsude jsou odrazky moc blizko sebe ... urcit idealni rozestupy delky"): lines 1.7 high, points 26
     px apart, the heading 40 px above them, a measure of about sixty characters, every ray 46 px; no word left alone
     on a line.
   - **Every picture level with its words**, as step 1's HQ ("proc je to vsude tak nizko dycky vedle toho textu?").
   - **Step 3**: the Universe with its products on the left, the Promo Market on the right ("a proc je porad promo
     market na leve strane a ukazky vesmiru napravo? ma to byt naopak"), apart, the Promo Market turned towards the
     words.
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
| 03 | the orbit, the Promo Market's building and its cube | our Universe mock, composed (record.py market): the farmer, the gem, the Agent Casino, the Promo Market building; the cube LIVE cymetica.com/promo-market's markup and CSS, copied, the products' live pages (capture.py apps) on its faces |
| 04 | the Quant Lab's page | outbox/quant-lab-v2's Coming soon mode, at its own pace: a simulation, and it says so on screen |
| 05 | the Universe | LIVE cymetica.com/company/app#universe, recorded without its sky, keyed: its six companies and four products today, and the leaderboard's eight sample companies added to its answer in our browser |
| 05 | the leaderboard | samples (QUEST.board), with our mock's stations as marks |
| end | the two doors | step 1's HQ and step 5's Universe, the same clips |

## Decided here, the veto open

- **Five steps, in his order of 2026-10-31**: start, build, market, the hero agent, climb.
- **Every picture beside its words, in the middle of their band** (the kicker's top to the big number's foot, about
  760 px at 2000 px wide), as step 1's HQ fills it ("proc je to vsude tak nizko dycky vedle toho textu? jedine
  headquarters je v idealni pozici hned vedle napravo"; "nekde mas velkou mezeru nahore nekde dole, musis to budto dat
  doprostred nebo vychytat tak at to zabira stejnou plochu jak headquarters", 2026-10-31). The HQ, the workshop and the
  Quant Lab fill it; step 3's Universe stands in its middle with the Promo Market at its foot (the fourteenth take: the
  thirteenth's Universe at the top was "moc nahore"); step 5's Universe fills it, the board small in its corner. The
  twelfth take had read "na preskacku" as the picture lower than the words, and that reading was wrong.
- **Marketing** is not in the pre-build (Cymetica QA, Development, Quant Lab, Trading desk): it is a department the
  owner adds (data.js, ET-32484). Step 3 still says "your Marketing department", as the step is the owner's next
  move; step 1's "4 departments" is the pre-build's.
- **The links**: every product a step names links to its live page (QUEST.links), each answering 200 on 2026-10-31.
  Until the twelfth take the two doors at the end were the only links ("to bude az na konci"); he asked for them.
- **The Quant Lab's timing**: the agent is born two seconds after the step is nearly half on screen, every time it
  comes back on screen; the twelfth take's reading time is gone (he looks at the picture first).
- **The first screen's words**: "Cymetica Quest." first and green, then "Join. Earn points. / Climb the leaderboard.
  / Earn up to 500,000 ET10 / every month." with the prize green; he left the opening to us ("CYMETICA QUEST zelene
  nebo join? ... musis to vymyslet").
- **The first screen's sun** is about 108 px across its ball at 2000 px wide, top right over the board, a ball's length
  right and down from where it stood (2026-10-31).
- **The Quant Lab** carries the Promo Market's scan lines too, faintly; he once said not to make it holographic, and
  this round asked for it set into space as the Promo Market is.
- **Step 5 is the live Universe** with the leaderboard's eight sample companies added in our recording browser, so
  the names on the board stand in the map too; the live one has six today. Nothing is sent to Cymetica: the answer is
  changed as it arrives in our browser (record.py EXTRA_COMPANIES).
- **The top bar** keeps its three parts (brand, track, prize) and drops the panel round them. **The mark** is
  Gemini's, as its whole page was picked; the Title logo he had picked from five the same evening stays in `logos/`.
- **The clips** stay out of git. Their posters are kept.
- **Keyed clips** (the HQ, the Universe, the farmer, both doors): filmed on black and keyed in the page, alpha from
  each pixel's brightest channel: the HQ's from 0.025 to 0.12, so the darkest metal stays whole and the black goes;
  the Universe's (data-key="glow") from 0 to 0.45 with its colour kept, so a lane of 3 % adds its light to the sky
  instead of being cut. A browser
  without WebGL shows them on black. Playwright's WebKit on Windows never finishes loading a WebM (the twelfth take
  hangs it the same way), so WebKit was looked at with the posters, which are keyed by the same shader.

## The contest

`outbox/quest-gemini/BRIEF.md` gives Gemini Antigravity the operator's requirements to build its own guide in
`outbox/quest-gemini/`. It is fenced off from this page's code. The operator picks the better one. On 2026-10-31 he
picked Gemini's fork of this page (served from `Downloads\cymetica\outbox\quest-steps` on 8765), and it is this page
now (the fifteenth take); that folder is Antigravity's and is not written to from here.

## Notes

- "Breed your hero agent" is the operator's wording. On 2026-10-28 Nexus said the lab-to-bot bridge was not built yet
  (ET-33133).
- The prize, 50,000 / 30,000 / 10,000 ET10 a month, is Cymetica's own (`GET /api/v1/company/season`, `prizes_et10`,
  season 2026-11, read 2026-11-03; it replaced our earlier 500,000 / 250,000 / 100,000). So are the points for your products' use and your agent's trades (2026-10-31).
- **Weight (2026-11-03, "zlehci to vse ale ne na ukor kvality"):** record.py films at 7 to 18 Mbit/s (the six clips
  the page uses were 151 MB). `slim.py all <name>` re-encodes a clip from `clips/orig/` to VP9 `.webm` and H.264
  `.mp4` (same size, same frame times), at the first crf whose luma SSIM stays >= 0.985 mean / 0.97 worst frame, and
  `keycheck.py` repeats the test after the page's key (black to clear, the dark haze is where a codec bands first).
  Now 30 MB for the six, each about 1 to 8 MB; the page takes the first `<source>` the browser can play (anim.js),
  mp4 first. Needs the imageio-ffmpeg wheel (`pip install imageio-ffmpeg`; Playwright's own ffmpeg is VP8 only), whose
  path is set at the top of slim.py. After a new recording: copy it to `clips/orig/`, run both, copy `slim/final/`
  into `clips/`. Originals stay in `clips/orig/` (not in git).
- What each department does is the live builder's own words: Development "drafts a Build it Better request" (it does
  not build; the pipeline does), Marketing "write briefs for my own Build it Better apps", the Quant Lab "keeps
  searching for a profitable agent", the Trading desk drafts "a seat at an Agent Casino table".
