# /company mockup: where it stuttered, and what it does now

Measured 2026-10-20 in headless Chromium with WebGPU on this machine's GPU (ANGLE d3d11), 2000x1100, the CDN and the
fonts from a local cache. One scripted walk through every place (`perf.py`), at full speed and with the CPU slowed
4x; a "frame" is the gap between two animation frames, so a long one is a stall the eye sees.
Before = bc690b01. After = the same pages with the changes below (they went in with da5e32b7).

## The numbers

| Place | worst frame, ms (1x) | frames over 100 ms (1x) | worst frame, ms (4x CPU) | frames over 100 ms (4x) |
|---|---|---|---|---|
| Department added (rebuild) | 2361 -> 347 | 2 -> 2 | 12882 -> 2097 | 4 -> 3 |
| Department removed (rebuild) | 250 -> 195 | 3 -> 1 | 3410 -> 764 | 6 -> 3 |
| Add department: the dialog opens | 417 -> 195 | 8 -> 4 | 2750 -> 632 | 29 -> 51 * |
| Add department: rooms, looks, experts, drag | 0 -> 0 | 0 -> 0 | 167 -> 167 | 2 -> 4 |
| Universe opened directly (back from a visit) | 868 -> 320 ** | 5 -> 11 ** | 3521 -> 2278 | 7 -> 24 ** |
| Room open / back | 167 -> 153 | 3 -> 2 | 604 -> 111 | 6 -> 2 |
| Universe: open, Mine, fit, zoom, drag | 83 -> 83 | 0 -> 0 | 562 -> 139 | 6 -> 1 |
| Back to the Office tab | 0 -> 0 | 0 -> 0 | 180 -> 111 | 25 -> 1 |
| Tabs (Portfolio ... Token) | 0 -> 0 | 0 -> 0 | 146 -> 97 | 3 -> 0 |
| Settings (station pictures) | 118 -> 132 | 2 -> 1 | 389 -> 326 | 8 -> 3 |
| Orbit, drag, zoom | 0 -> 0 | 0 -> 0 | 97 -> 63 | 0 -> 0 |
| NEXUS chat | 63 -> 63 | 0 -> 0 | 56 -> 56 (re-run; one walk had a 340 ms frame) | 0 -> 0 |
| 3D -> 2D | 257 -> 243 | 1 -> 1 | 264 -> 250 | 2 -> 2 |
| 2D -> 3D | 0 -> 0 | 0 -> 0 | 181 -> 132 | 1 -> 1 |
| Office 3D, first load (before its first frame) | 423 -> 375 | 10 -> 10 | 1931 -> 1840 | 25 -> 21 |
| Visit (?visit=101), load | 451 -> 445 | 11 -> 11 | 2528 -> 1903 | 24 -> 22 |

\* At 4x the dialog's room now keeps drawing (each frame ~100 ms there) while its shaders are made, instead of one
2.7 s freeze. \*\* All before the map's first frame (nothing on screen moves yet); after it, none over 90 ms (before:
an 868 ms first frame, then a 160 ms one during the flight in). The map shows 1.1 s later (2.4 s instead of 1.3 s), with
its whole flight in.

## Second pass (the same day, against da5e32b7: the page without its top bar, so a taller 3D stage)

| Place | worst frame, ms (1x) | worst frame, ms (4x CPU, two walks) |
|---|---|---|
| Department added (rebuild) | 563 -> 278 | 2174, 2361 -> 1576, 1417 |
| everything else | within the walk's own spread (about +-50 ms at 1x run to run) | |

- **The spare lamps are seen by the floors' mirror too** (layer 1, as a room's own lamp). Seen by the main view
  alone, a spare a new room took up changed the mirror's set of lights, and every material the mirror draws was
  built again: 11 shaders in the existing rooms after Create, now 0.
- Tried and taken out (672b80d4, then out): making the room a pick would add ready while the dialog is open. Create
  went to 229 ms (1.1 s at 4x), but building that room in the office while the dialog is browsed made the dialog's
  own frames 360-530 ms at 4x where they were 56-180.

## Third pass: the Add-department dialog froze the browser (against bb32b014)

The operator, opening Add department: "proc mi to zaseklo prohlizec?". Measured with `dlgperf.py` (the dialog opened
on a settled office, then every room and six looks clicked) and Chrome traces of the GPU process (`trace.py dlg`,
`tsync.py`), each twice:

| The dialog | bb32b014 | now |
|---|---|---|
| Opening, worst frame (1x) | 243-257 ms | 70-90 ms |
| Opening, frames over 100 ms (1x) | 2-3 | 0 |
| Opening, long tasks (1x) | 6-7, the longest 118-128 ms | 0-2, the longest 52-56 ms |
| Pipelines made inside a frame, on the GPU process's main thread (1x) | 16, 221 ms | 11, 62 ms (the bloom's) |
| Opening, worst frame (4x CPU) | 688-702 ms | 299-333 ms |
| Opening, frames over 100 ms (4x) | 26-27 | 39 |
| Switching rooms / looks, worst frame (4x) | 202-208 / 188 ms | 56-70 / 0-56 ms |
| Every room ahead ready (1x / 4x) | 2.2 s / 9.3 s | 2.3 s / 17-18 s |

- **Why the whole browser stopped, not just the page:** the dialog's first frame drew the floors' mirror for the
  first time, and a pipeline made inside a frame is compiled on the GPU process's main thread, the thread that draws
  every tab and the browser itself: 126 + 58 ms there, a 115 ms frame on the page. Now the mirror's pass is made
  ahead (`RoomPreview.prepare`, `ahead1`: the scene from the mirror's own camera into its own target), its pipelines
  compiled on the GPU's worker threads.
- **Why the floors had been left out of that:** three.js r172's mirror, asked to draw from a camera under its floor,
  returns without resetting its "inside a mirror" flag, and every mirror in the page stays empty from then on. The
  dialog's camera sat at the origin, under the floor, until its first frame. It is placed first now (`place`).
  bb32b014 hit this too: a room picked in the first half second of the dialog came up with an empty mirror.
- **Small pieces** (`compileInPieces` with a `budget`): one new shader per piece, as many pieces in a task as fit in
  16 ms. A shader is 15-50 ms of work and cannot be cut, so that is the longest task left.
- **A room built ahead in two moments** (`pvRoom` raw, `get`): its parts, then after the next frame its merge (one
  task of 50 ms, 200 at 4x, before).
- **A room picked while the dialog is still being made ready waits for that, then is made ready the same way.**
  Swapped in between two pieces, its hull came out lit differently (14,552 px).
- Every room ahead is ready later at 4x (17-18 s, before 9.3 s): its work comes in small pieces with the turning
  room drawn between them, and every room gets the mirror's pass too. At full speed it is ready at the same time as
  before (2.3 s). Once a room is ready, switching to it costs nothing.

Pixel check: `pix.py` (11 states, twice) against two runs of bb32b014: the dialog open, a look, the office (home, a
room, Command, 2D, back, after Create and Delete) are 0 px. The expert card, the office after Create and the 2D
dialog differ as much as two runs of bb32b014 do. start.html's room tile: 0 px. A room clicked 400, 900, 1500 and
2500 ms after opening (two rooms) and one clicked half-built: 0 px against the same room on bb32b014 settled.

## Fourth pass: the dialog made ready before it opens (against a4f3efd3)

The dialog's renderer now lives for the page (`RoomPreview.dialog`, `warmUp`, `attach`, `detach`; app.js `warmDialog`,
`warmRooms`). 2.5 s after the office's first frame, while nobody is at the page, it makes everything ready behind
the office: the room Add department opens on, every room a click brings, every department's own room as Edit shows
it, the mirror, and one frame nobody sees (the bloom's and the output's pipelines, the studio's reflections). Opening
the dialog puts it in the stage and resets it the way a new one starts. A hand on the page pauses the work.

| | a4f3efd3 / d54f27f6 | now |
|---|---|---|
| Add department opens, worst frame (1x / 4x) | 63-83 / 229 ms | 69-70 / 97-111 ms |
| Add department opens, frames over 100 ms (4x) | 21 | 0-1 |
| Edit opens, worst frame (4x) | 195 ms, 11 over 100 | 132-139 ms, 1 over 100 |
| Switching rooms, worst frame (4x) | 146 ms | 56-70 ms |
| Pipelines made as the dialog opens (1x) | 11 in a frame (the bloom's) | none |
| The office meanwhile, nobody at it (4x) | 11 frames over 100 ms | 59-61 over 100 ms, for ~25 s |

At full speed the dialog is ready 4.3-4.7 s after the office's first frame, and the office meanwhile has a few
frames of 50-67 ms. At 4x it takes ~25 s, and the office stutters while it does: a piece's length is its one new
shader (50-200 ms there), so the work moved from the dialog's first seconds to a quiet moment rather than went away.
Opened before it is ready, the dialog takes it from where it got to. The rest of the opening at full speed (60-70 ms
frames) is the dialog's own HTML drawn for the first time.

Pixel check, each state frozen on its own page load: Add department opened 1, 2.8, 3.6, 4.6 and 12 s after the office's
first frame (the early ones while it is still being made ready), Edit on each of the three departments, a look of
your own and an expert opened: 0 px against a4f3efd3. start.html's room tile: 0 px. `pix.py`'s walk froze the page
state after state, and its look and expert pictures differed by a 1-level card glow and an artefact of its own
(a hull rail drawn askew, in both versions); captured on their own they are identical.

What is left over 100 ms at full speed, and why it stays:
- **Opening or closing a room (one or two frames of 100-170 ms):** the columns slide for 0.5 s and the 3D stage
  changes size every frame, and three.js makes its render targets again at each size. Measured: with the size held
  for the slide there are none, but the picture would be stretched for those frames.
- **3D -> 2D (~250 ms once):** the flat office is drawn for the first time (browser rasterisation of its SVG).
- **Settings' station pictures (~130 ms):** a renderer of their own; making their shaders ahead changed the
  Shipyard's picture, so it was taken out.
- **Before the first frame of a page** (office, visit, the Universe opened directly): pieces of the first frame's
  shaders; nothing on the stage moves yet.
- start.html and builder.html are not measured here: they were still being changed by the entry's session.
- **The dialog's first frame still makes its bloom's 7 pipelines inside the frame** (62 ms on the GPU process's main
  thread) -- only when the dialog opens before it was made ready (fourth pass).
- **The dialog's own HTML is drawn for the first time** (68 ms on the GPU process's main thread, the browser's
  raster). It was there before too.

## What changed (u3d.js, app.js)

- **Two dark lamps more than the rooms need, from the office's first build** (`lampsBack`, `LAMP_SPARE`). A new room's
  lamp was a new light, and three.js r172 builds every lit shader again for a new set of lights: 2.2 s of one frame.
  Now the new room takes a dark one. A lamp at intensity 0 adds nothing to any surface.
- **Instanced meshes taken up again by a rebuild** (`imesh`, `imKeep`, `imDrop`). r172 builds an instanced mesh's
  shaders for that mesh alone, so every rebuild built 29-31 of them again; now 0 on a removal, 11 (the new room's own)
  on an addition.
- **The Add-department dialog's renderer makes its shaders a piece at a time** (`RoomPreview.prepare`, `ahead1`,
  `compileInPieces` with `only`, `around`, `skip`), before its first frame and for every room it builds ahead (the
  floors that catch the mirror as well since the third pass, above). The cards' pictures and Settings' station pictures are encoded off the main thread (`toBlob`, the same PNG
  bytes as `toDataURL`, checked: 0 values differ): `toDataURL` waited ~90 ms a picture on the GPU.
- **The Universe shows once its shaders are made** (`whenWarm` in app.js): opened directly, its first frame built
  them all at once.

Tried and taken out because the picture changed: keeping three.js's node builder states past their materials (a
rebuilt room's glass-sign icon stayed undrawn), and making Settings' station pictures' shaders ahead (the Shipyard's
picture changed).

## Pixel-identical

`pix.py`: every state drawn with the clock frozen (Date fixed, Math.random seeded, the simulation and the timers
stopped, every renderer's clock, node time and performance.now held, one fresh frame), before and after compared
pixel by pixel. 0 pixels differ in the office (home, a room, Command, zoom, after a department added and removed, 2D
and back, after the Universe), the Universe (home and a station), every tab, the visit, all seven station pictures
and every expert's card picture. What differs also differs between two runs of the old page, in the same places:
the rooms' card pictures (drawn while their people move), a 1 px GPU speck, the code wall and the crystal in two
rooms after a department is added, the cards' strip in the dialog (its scroll). The second pass was checked the same
way against da5e32b7, with the same result.

Scripts (Python + Playwright): in the session notes folder `harness/` (perf, pix, diff, prof, trace).
