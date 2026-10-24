# Build a Company on a weak computer

The owner opened https://cymetica.com/company/app on a laptop with a Ryzen 5 5500U, 8 GB of memory and the Radeon
graphics built into that processor (496 MB). It loaded about 70 % longer than on his desktop, the loading screen's
longest word was OFFICE, the entry page was loading an office he had not asked for, turning the Universe stuttered, and
the company he then opened loaded slowly again and stuttered too.

This folder is the whole change, ready to apply: `company-perf.patch` against your live files (`/static/company/*`,
`?v=6adb7183`), the three pictures in `new/`, and below what each part does, where, and what it buys, measured. On a
strong computer the 3D draws the same picture as today (section 5). A weak one gets a cheaper drawing of the same
pictures, and nothing is built before someone asks for it. What it does not shorten is an office's own loading: that is
three.js making shaders (section 1), and section 7 says where that time could go.

## 1. What we found

All of it on your live pages, offline (section 2 says how).

- **The entry page loads the whole 3D engine for two pictures.** A visitor who is not signed in is sent to
  `/company/app/start`. It loads three.js (2.3 MB) and `u3d.js` (0.7 MB), opens three WebGPU devices (the sun with its
  companies, the Universe tile, and the turning office room of the Start-a-company tile, which is the loading screen's
  OFFICE), holds its loading screen until all three have drawn, then draws all three on every frame the browser offers
  with nobody touching them (362 frames a second together on the strong machine, 89 on the weak one), and keeps 255 MB of
  GPU textures.
- **Opened on the Universe with a company, the page builds the office behind it.** `boot()` builds the 3D office as soon
  as the engine is there, whatever tab is open: an owner (or a `?visit=`) opening `/company/app#universe` pays for an
  office nobody looks at. Without a company `boot()` builds none, so the entry page's door to the Universe does not.
- **After the office shows, two more scenes are built behind it** (signed in): `warmDialog` starts a second WebGPU device
  2.5 s after the office's first frame and builds the Add-department dialog with every room and look, and
  `prebuildUniverse` builds the whole Universe on a third. On the weak machine that is 4.0 s of the main thread held in
  the first 20 s after the loading screen (49 pieces), the office at 21 frames a second meanwhile, and 389 MB of GPU
  textures, against the owner's 496 MB.
- **A frame of the office on a weak computer is the processor's, not the graphics card's.** Turning company 14's office
  (4 departments): the weak chip with the processor at full speed draws 58 frames a second; a strong card with the
  processor slowed 3x draws 42, and the weak chip with the slowed processor 41. A CPU profile of that turn: 90 % of the
  main thread inside three.js's per-object rendering (`renderObject`, `_renderObjectDirect`, bindings, draw encoding).
  A frame is 1,272 draws: 825 in the main pass, 361 in the sun's shadow map (drawn again every frame), 80 in the floors'
  mirror. Drawing fewer pixels, no multisampling or a smaller glow did not change that frame rate (one run each, inside
  the noise); drawing the shadow once a second did.
- **An office's loading is three.js making shaders.** On the weak machine about 70 % of the main thread's time while an
  office loads goes to three.js's `NodeBuilder.build`, which turns a material into shader code (three runs with a counter
  on it, `harness/nodebuilds.js`: 71 to 73 %, for instance 6.4 of 9.1 s; a plain CPU profile agrees, three.webgpu.js's
  node functions on top). For company 14's office it runs 113 times (40 for `MeshStandardMaterial`, 35
  `MeshBasicMaterial`, 24 TSL `NodeMaterial`), and the 113 builds make 70 different pairs of vertex and fragment code: 43
  of them make code an earlier build had made. three.js r172 keeps a build by the render object's key
  (`RenderObject.getMaterialCacheKey`: the material's type, the id of every node in it, each property as on or off, the
  geometry's attributes, `receiveShadow`), not by the code it makes, so anything in that key that differs (a node made
  anew instead of shared, a property set on one material and not the other, a geometry with one attribute more) costs a
  build of its own, even where the code comes out the same. This package does not change that.
- **The Universe on its own did not stutter on our weak machine** (72 frames a second while turned, 95 % of them within
  20 ms of the one before). What in this package most plausibly made it stutter on the laptop: the scenes built behind
  the office while he turned it (signed in), the GPU memory of three scenes at once on a 496 MB chip, and two blurs the
  browser redoes on every frame the map moves (the top bar's frosted glass and the sun painting's glow). Not in it: a
  Chrome whose WebGPU is off for that chip's driver, where three.js draws through WebGL2 with only a console warning
  (`chrome://gpu` says which). On the laptop, `/company/app?q=low` against `?q=high` is the test.

## 2. Measured

The weak machine, today's page and the changed one at each level, set by hand (two runs each, ± half their spread; high
one run). "On screen" is from the click to the loading screen gone (the changed entry page has none: to its
DOMContentLoaded); "turned" is the scene's own frames a second while dragged round, and in brackets the time 95 % of them
came within.

| weak machine | today | low | medium | high |
|---|---|---|---|---|
| **Entry page** (`/company/app`, signed out): on screen | 7.7 s | 0.8 s | 0.8 s | 0.8 s |
| main thread held: before it shows · in the 8 s after | 5.2 s · 0.03 s | 0 · 0 | 0 · 5.0 s | 0 · 5.3 s |
| its first 3D frame · GPU textures | 2.2 s · 255 MB | none · 0 | 2.3 s · 231 MB | 2.4 s · 255 MB |
| **Universe** (`#universe`, signed out): on screen | 2.8 s | 2.9 s | 2.6 s | 2.5 s |
| turned | 72 (20 ms) | 81 (18 ms) | 71 (19 ms) | 94 (16 ms) |
| left alone: frames a second · GPU textures | 64 · 118 MB | 29 · 47 MB | 29 · 118 MB | 70 · 118 MB |
| **An office as a visitor sees it** (`?visit=14`): on screen | 9.4 s | 8.3 s | 9.7 s | 9.0 s |
| turned · GPU textures | 39 (32 ms) · 146 MB | 60 (22 ms) · 92 MB | 47 (29 ms) · 121 MB | 37 (34 ms) · 147 MB |
| **Our own office, signed in** (company 14): on screen | 10.9 s | 10.1 s | 11.0 s | 10.9 s |
| the 20 s after it: main thread held · the office's frames a second | 4.0 s · 21 | 0 · 30 | 0 · 28 | 4.0 s · 20 |
| turned | 36 (34 ms) | 53 (26 ms) | 50 (28 ms) | 37 (34 ms) |
| then the Universe tab: opens in · turned | 0.5 s · 76 | 1.7 s · 79 | 1.8 s · 80 | 0.5 s · 75 |
| WebGPU devices · GPU textures at most | 3 · 389 MB | 2 · 142 MB | 2 · 234 MB | 3 · 389 MB |

- **Auto** chose low on the weak machine by the chip's name (its runs: the entry page 0.8 s; our office on screen 10.2 s,
  0 s held after it, turned 58) and high on the strong one.
- **The office's own loading is hardly faster**: about a second less at low (where, with no mirror, three.js makes 104
  shader builds instead of 113), the same at medium and high. Most of it is three.js building shader code (section 1);
  section 7 says where that could go.
- **What building on demand costs**: below high the Universe tab takes 1.7 s to open the first time, under the loading
  screen it already has, instead of 0.5 s, because nothing built it in the background.
- **The entry page at medium** is on screen at 0.8 s, and then its three scenes are built: on this machine that holds the
  main thread 5 s in the next 8 (26 pieces, the longest 1.1 s), and a click meanwhile waits for the piece under way.
  The owner's chip gets low, where nothing is built there.
- **At high the weak machine measures as today** within the runs' spread, except the entry page: it is today's page.

On the strong machine (one run each) Auto chose high, and every place but the entry page measured as today within a
run's spread: the Universe on screen 1.5 / 1.4 s and turned at 144 frames a second both; a visitor's office 3.3 / 3.1 s,
144 both; our own office 3.25 s both, turned at 142 / 143, its Universe tab open in 0.15 / 0.19 s. The entry page: on
screen 3.7 s, now 0.6 s; its 0.9 s of main-thread work moves from before the page to the 8 s after it; left alone it
draws 69 frames a second, all three scenes together, instead of 362.

How: your live pages offline, every request answered from one recording of them (2026-10-23; after it nothing reached
your servers and no POST was sent), in Chrome 155 with WebGPU, at the owner's laptop's window (1536 x 730 CSS pixels at
125 %). **Strong** is an RTX 5070 Ti at full speed. **Weak** is the Radeon built into a Ryzen 7 9700X (2 compute units,
fewer than the owner's 7) with the page's processor slowed 3x by Chrome, probably harsher than his 5500U: read its numbers
as a floor. Chrome cannot slow its graphics process, so the weak chip stands in for his. Before and after were run one
after another, place by place; weak numbers are the mean of two runs, ± half their spread. Scripts: `harness/`.

## 3. The change

### A. One level of 3D per computer, chosen before anything is built (`quality.js`, new)

A classic script loaded first on each /company page. It sets `CO.Q3` and the class `q-high`, `q-medium` or `q-low` on
`<html>`; `u3d.js`, `app.js`, `start.js` and the CSS read nothing else.

| | high | medium | low |
|---|---|---|---|
| pixel ratio at most | 2 (as today) | 1.5 | 1.25 |
| pixels drawn at most: office, dialog, previews / Universe | none / 4.5 M (as today) | 2.4 M / 2.4 M | 1.3 M / 1.3 M |
| edge smoothing (the pass's multisampling) | 4x | 4x | none |
| the sun's shadow (office) | 2048, every frame | 1024, 4 times a second | 1024, once a second |
| the floors' mirror | half the screen | a third | none |
| frames while nobody touches the scene | 72-80 a second, 30 when slow (as today) | 30 | 30 |
| a corridor's dashes | a mesh a dash (as today) | one mesh a corridor | one mesh a corridor |
| Universe and Add-department dialog built ahead | yes (as today) | no, when opened | no, when opened |
| the entry page's scenes | live, after the page | live, after the page | pictures only |
| frosted glass over moving 3D | yes | no, a more opaque plate | no, a more opaque plate |

**How a computer gets its level**, in this order: `?q=high|medium|low` in the address; Settings > Graphics (Auto, High,
Medium, Low, kept in the browser); what the frames said last time on this chip; a first guess from the graphics chip's name
(`WEBGL_debug_renderer_info`, which Chrome, Edge and Firefox give). The guess: software renderers and phones low; Intel
HD/UHD, *AMD Radeon(TM) Graphics* (the owner's 5500U), Vega low; Iris Xe, Radeon 680M/780M, Intel Arc integrated, Apple
M1/M2, GeForce MX medium; add-in cards and Apple's Pro/Max high; anything unknown medium with 8 or more threads, else low
(21 chip names checked: `harness/guess_test.js`).

**The frames have the last word** (`u3d.js` `pacer`, `govern`). While a hand is on the office or the Universe, the pacer
already averages the frame time; if it stays over 26 ms (under ~38 a second) for 1.5 s, that scene draws 20 % fewer pixels
(down to 55 %), and after two such steps the next visit on this chip starts one level lower (`localStorage co.q3.auto`).
A level chosen by hand is drawn as chosen. A computer that holds its frames never triggers it, which is why high stays
today's page. Seen working (`harness/govtest.py`): the weak machine with its chip's name given as an add-in card's got
high from the guess; turning an office took its pixels down to 55 % and kept medium for that chip, and the next visit
started at medium.

### B. Build what is shown, when it is shown

**B1. The entry page is its pictures first** (`start.html`, `start.js`, `start.css`, `new/start-*.webp`).
- `start.html` loses the loading screen, the two `<script type="module">` (`u3d.js`, `stations.js`), the three
  `modulepreload` links, the `boot.css` link and the `sun.webp` preload; it preloads `start-space.webp` instead.
- Each scene's place shows a picture of that scene (`start.css`: drawn by the scenes themselves, 98 KB together); the
  page is complete at its first paint.
- At high and medium `start.js` imports `u3d.js` and `stations.js` once the page is idle and starts the scenes as
  before; each draws over its picture from its first frame (a WebGPU canvas is transparent until then), and the picture
  is then taken from under it. At low nothing 3D loads on this page.
- The scenes draw 30 frames a second at most (by the frame's own time, `document.timeline`): nothing there moves fast.

**B2. The 3D office is built when the office is shown** (`app.js` `boot`, `setTab`; `app.html` `#o3load`). Opened on the
Universe, `boot()` no longer builds it; Headquarters builds it the first time it opens, under the loading screen's core on
the office's stage (`#o3load`: the `#uvload` markup with OFFICE as its word, the same CSS).

**B3. Nothing built ahead below high** (`app.js` `ahead()`, checked before `prebuildUniverse` and in `warmDialog`,
`warmRooms`). At high both stay, as the design has them. At medium and low the Universe is built when its tab opens (with
the loading screen it already has) and the dialog when it opens.

### C. Draw what the computer can (`u3d.js`, `uv.css`, `start.css`, `style.css`)

Each value is read from `CO.Q3` where the renderer, pass or light is made; at high each gives today's value.

- **C1. The sun's shadow** (`Office3D`): map `Q3.shadow`; below high `shadow.autoUpdate = false`, drawn again every
  `Q3.shadowMs` (`frame()`) and whenever `layout()` places the rooms. The sun stands still, a turn of the camera does not
  change a shadow map, and only the astronauts move under it (their shadows follow a moment late). This takes the shadow
  pass (361 draws) out of almost every frame.
- **C2. The floors' mirror** (`shRefl`, `shFloor`): its target `Q3.mirror` of the screen, read a mip level finer when
  smaller so the blur on the screen stays as wide; at low none: `shFloor` returns the plain floor material and nothing makes
  the reflector (`pvRoom`, `Office3D.layout`, `RoomPreview.prepare`, `ahead1` ask only when there is one). Takes the mirror
  pass (80 draws, a second drawing of the rooms) out.
- **C3. A corridor's dashes as one mesh** (`Office3D.layout`, below high): one draw a corridor instead of one a dash, 51
  of the office's draws; the same material, so the lane still lights with its department's work.
- **C4. Pixels** (`qPr()`): the screen's ratio, at most the level's, at most its pixel budget, times the frames' scale.
  Used where each renderer gets its ratio: `Office3D` (constructor, `resize`), `RoomPreview` (constructor, `attach`,
  `place`), `Preview`, `Universe3D.resize` (its 4.5 M cap becomes `uvPx`).
- **C5. Edge smoothing**: `Post` makes its pass with `{ samples: Q3.samples }` (4; none at low). Little for the frame
  rate on our machine, about 30 MB of GPU memory for the office.
- **C6. 30 a second while nobody touches it**: the pacer's idle interval is `Q3.idleMs` (12.5 ms today).
- **C7. Frosted glass over moving 3D**: `backdrop-filter` is computed again by the browser on every frame the scene under
  it moves. Below high the office's room plates (`.p3`), the Universe's top bar (`.uvstage .crumb`), the modal's backdrop,
  and at medium the entry page's two doors (`.lp-tile`) get a more opaque plate; the sun painting's glow (`.uvcol .g1`,
  `.lp-col .g1`) is blurred once into its own canvas (`core()`, `painting()`) instead of by the browser every frame.

### D. Smaller ones

- `GTAONode.js` is no longer imported: its only use (`Post` with `opts.ao`) had no caller; 15 KB loaded and parsed on
  every 3D page.
- `u3d.js` takes WebGL2's presence from `quality.js` (`CO.Q3.gl2`) instead of making a context of its own to ask.
- Settings has a Graphics card (Auto · the level Auto chose, High, Medium, Low); a choice reloads the page.

## 4. How to apply

1. Put `new/start-space.webp`, `new/start-room.webp` and `new/start-uv.webp` into `/static/company/`.
2. From the folder that holds `static/`: `git apply company-perf.patch` (or `patch -p1 < company-perf.patch`). It adds
   `static/company/quality.js` and changes `u3d.js`, `app.js`, `start.js`, `start.css`, `uv.css`, `style.css`. Applied to
   the files you serve today it gives, byte for byte, the files every number here was measured with (checked).
3. The three pages are your templates (their nonces change per request), so their edits are listed; `pages.diff` has them
   as rendered.
   - `app.html`: `<script src="/static/company/quality.js?v=…"></script>` as the first script, before `data.js`; inside
     `#stage`, after `<div class="tip" hidden></div>`, the `#o3load` block (the `#uvload` block with OFFICE as its word).
   - `start.html`: `quality.js` as the first script; remove the `#boot` block, the two `<script type="module">`, the three
     `modulepreload` links, the `boot.css` link and the `sun.webp` preload; add
     `<link rel="preload" as="image" href="/static/company/start-space.webp" fetchpriority="high">`. The import map stays:
     `start.js` imports the engine through it.
   - `builder.html`: `quality.js` as the first script.
4. Raise `?v=`.
5. To look at a level: `/company/app?q=low` (`/company/app/start?q=low` for the entry page); Settings > Graphics shows what
   Auto chose.

## 5. What stays as it is

- **At high, the 3D picture.** `harness/pix.py` draws each place with the clock held (time and dates fixed, random seeded,
  CSS animations stopped), today's page twice and the changed one once, and compares them pixel by pixel, on the strong
  machine:

  | place | two loads of today's page differ in | today's against the changed one |
  |---|---|---|
  | the Universe | 12,684 px (3,305 by more than 8 levels) | 8,566 px (92) |
  | the office (company 14, as a visitor sees it) | 9,695 px (1,642): astronauts' random walks | 10,933 px (1,990): the same astronauts |
  | the entry page | 48,127 px (510) | 72,592 px (14,597): the sun's painting |

  The Universe and the office differ only where today's page differs from itself. On the entry page the difference is the
  sun's painting, a page element laid over the 3D scene, which now appears with the scene's first frame instead of before
  it (B1); it differs in its fine lines, not in what it shows. Everything the 3D engine draws there is the same.
- **At high, what the page does**, except: the office is not built behind the Universe when the page opens on it (B2); the
  entry page shows its pictures first, its scenes after it, at 30 frames a second (B1). Its timing at high is today's
  within the runs' spread on both machines, the entry page apart (section 2).
- **Everywhere**: the API and every call to it, `live.js`, the flat office and the flat map, every tab but Settings.

## 6. Tried and left out

- **Recording the rooms' still parts** (a three.js `BundleGroup` per room, replayed instead of drawn object by object):
  about 10 % more frames on the weak machine, but the lab's monitors and a wall screen came out black from the recording
  (it keeps what it was recorded with, and these were drawn differently afterwards). Worth doing with care; not here.
- **A smaller glow** (the bloom's targets at a quarter of the screen): no measurable gain.

## 7. Left for later (not measured)

- **The office's loading** (section 1): 113 shader builds for 70 different pairs of code, about 70 % of the main thread
  while it loads on a weak computer. What would bring the builds toward the pairs: materials and their TSL nodes made
  once and shared across rooms and looks rather than made again per room (a node's id is in the key), the same flags on
  materials that draw alike, geometries with the same attributes. And building the office a room at a time behind its
  loading screen would keep any one piece from holding the page the 1.3 s it does today. A second visit is not faster
  (measured): with the browser's cache warm from a first load, an office on the weak machine came on screen in 8.8 and
  10.7 s today and 7.9 and 10.1 s at low, against 9.4 and 8.3 s the first time. The files are cached already (yours 30
  days, three.js a year); the time is the build, which nothing keeps from one visit to the next.
- **The entry page at medium**: its three scenes, built after the page shows, hold the main thread 5 s on the weak
  machine (section 2). Built in smaller steps, as `prebuildUniverse` builds the Universe, a click would wait less.
- Fewer draws per room: 825 in the main pass for 4 departments, which is what a weak processor pays for on every frame.
  Of the 755 meshes drawn: 158 are the 8 astronauts' parts (already merged per material inside each astronaut), 108 carry
  a material of their own (screens, signs), 325 are still opaque parts whose material other parts in other rooms share
  (66 materials; `bakeRoom` merges only within a room, and a room's tint swaps its own materials).
- A visitor who is not signed in still downloads three.js and `u3d.js` on `/company/app` before `boot()` sends him to
  `/company/app/start` (the page's module scripts start at once). Sending him there from the server, or importing
  `u3d.js` from `boot()` once the mode is known, would save that (the second costs a signed-in owner the overlap).
- Not tried: a newer three.js release.
