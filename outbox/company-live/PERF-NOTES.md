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

## What changed (u3d.js, app.js)

- **Two dark lamps more than the rooms need, from the office's first build** (`lampsBack`, `LAMP_SPARE`). A new room's
  lamp was a new light, and three.js r172 builds every lit shader again for a new set of lights: 2.2 s of one frame.
  Now the new room takes a dark one. A lamp at intensity 0 adds nothing to any surface.
- **Instanced meshes taken up again by a rebuild** (`imesh`, `imKeep`, `imDrop`). r172 builds an instanced mesh's
  shaders for that mesh alone, so every rebuild built 29-31 of them again; now 0 on a removal, 11 (the new room's own)
  on an addition.
- **The Add-department dialog's renderer makes its shaders a piece at a time** (`RoomPreview.prepare`, `ahead1`,
  `compileInPieces` with `only`, `around`, `skip`), before its first frame and for every room it builds ahead; the
  floors that catch the mirror are left to the first real frame (made ahead in that renderer, the mirror came out
  empty). The cards' pictures and Settings' station pictures are encoded off the main thread (`toBlob`, the same PNG
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
rooms after a department is added, the cards' strip in the dialog (its scroll).

Scripts (Python + Playwright): in the session notes folder `harness/` (perf, pix, diff, prof, trace).
