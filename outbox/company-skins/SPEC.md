# Station skins: ten new picks, build spec

The pictures in `index.html` are drawn by the page's own small projector from **the numbers below** (the same
camera as the map: 33 degrees down, one scale on every card). Switch 1 / 4 / 8 departments there to see each skin
at any size before building it. Everything is in station units, y up.

## Shared rules (every skin)

| | |
|---|---|
| Scale | map draws a station at `UVSS = 3.8`; Cymetica's sun ball is `14 x 1.7 = 23.8` radius (47.6 across). Every skin here: `foot <= 3.45`, `top <= 4.01`, so at most 13.1 world units from its axis, under 30 % of the sun's diameter. The seven existing ones run foot 2.6 to 4.1. |
| Builder | `(b, n)` with `n` = departments 1..8, put into `CO.U3.SKIN[key]` the way `stations.js` `install()` does; name into `CO.SKINS`, icon into `CO.STATION_ICON`; a flat picture into `universe.js` `SKIN` (it feeds `CO.skinArt`: Settings and "Create your company"). |
| Decks | one per department, its windows `b.win(x, y, z, ry, w, h, f, lit)` / `b.ringWins` / `b.faceWins` with deck `f`, so `paint()` lights it while that department works. |
| Frame | set `b.top`, `b.bot`, `b.foot` as listed; the holo ring then sits at `bot - 0.5`, radius `max(2, 0.72 foot)`. |
| Hull | slate / steel only: `mats(A).light / .mid / .dark / .black / .metal` (stations.js, tint <= 0.1) or `M.hull / M.hull2 / M.trim / M.metal / M.dark / M.rock` (u3d.js). **Never** `amat().hull / .hull2`: they lerp 0.30 / 0.22 into the accent, the washed-out look. |
| Accent | only where light lives: `A.rim` (lines, posts, rims), `A.soft` (secondary lines), `A.glow` (points), `A.glass` (tinted glass, `DoubleSide`), `A.beam` (light sheets / columns), `A.wire` (faint ribs), `glowSprite(A.c, op, size)` (halos). Target: accent under 15 % of the visible surface. |
| Light lines | in 3D a "line of light" is a thin box (0.03 to 0.05 square), a torus (tube 0.02 to 0.03) or a `TubeGeometry` along a curve, in `A.rim`; bloom does the rest. |
| Motion | turn, travel along a track, or a slow bob. **Nothing pulses**: no plumes, no lance out of a prow, no gate ring (the operator, 2026-10-20, quoted in `stations.js`). Glow sprites keep a constant opacity. Moving parts are `userData.dyn` groups driven from `b.anim.push(t => ...)`; every speed below runs x1.6 while `b.busy`. |
| Names in the parts lists | `pale` = `mats(A).light`, `steel` = `mats(A).mid` (or `M.hull2`), `metal` = `M.metal` / `M.trim`, `dark` = `M.dark` / `mats(A).black`, `rock` = `M.rock`. |

---

## 01 Armillary Core (`armillary`)

Three gimbal rings, each on its own axis, turn round a glass capsule of decks with a spine of light.

| n | foot | top | bot | across x high |
|---|---|---|---|---|
| 1-4 | 2.30 | 3.50 | -1.10 | 4.6 x 4.6 |
| 8 | 2.55 | 3.75 | -1.35 | 5.1 x 5.1 |

- Core height `Hc = 1.2 + 0.2 n`, centre `yc = 1.2`, radius `rc = 0.55`; ring radii `R3 = max(1.6, Hc/2 + 0.45)`, `R2 = R3 + 0.3`, `R1 = R2 + 0.3` (the capsule always clears the inner ring, so no strut crosses a ring's path: the rings float, pinned only to each other).
- Parts
  - collar at each end: cylinder r `rc + 0.08`, h 0.14 -> `steel`; a torus of light r `rc + 0.09` where it meets the glass -> `A.rim`
  - shell: open cylinder r `rc`, from `y0 + 0.14` to `y1 - 0.14` -> `A.glass`; two domed caps (lathe, 0.28 high) -> `A.glass`
  - decks: disc r `rc - 0.05`, h 0.05 per department, spaced `(Hc - 0.4) / n` -> `pale`; `ringWins` r `rc`, 10 a deck
  - spine: cylinder r 0.045, `Hc - 0.2` long -> `A.glow`; `glowSprite(A.c, 0.5, 2.4)` at `yc`; beacon 0.3 over the top cap
  - rings: `TorusGeometry(R, tube)` tubes 0.075 / 0.062 / 0.052 -> `metal`; on each ring's outer face a torus r `R + 1.05 tube`, tube 0.02 -> `A.rim`
  - pins: outer to middle on the outer ring's x axis (from `R2 + 0.04` to `R1 - 0.06`), middle to inner on the middle ring's z axis -> `metal` boxes 0.09 square; a `A.glow` dot at each outer pin
- Accent: ring lines, collar lines, spine, glass tint. About 9 %.
- Motion (a real gimbal chain): `F1 = RY(0.12 t)` carries the outer ring (vertical plane); `F2 = F1 * RX(0.21 t)` the middle; `F3 = F2 * RZ(-0.33 t)` the inner. Rad/s, x1.6 busy.
- Icon: `<ellipse cx="10" cy="10" rx="4.4" ry="8.2" transform="rotate(18 10 10)"/><ellipse cx="10" cy="10" rx="8.4" ry="3" transform="rotate(-12 10 10)"/><rect x="8.7" y="6.2" width="2.6" height="7.6" rx="1.3"/>`

## 02 Helix Spire (`helix`)

Square glass floors, each turned a little on the one below: lit corners climb as a helix, 90 degrees over the tower.

| n | foot | top | bot | across x high |
|---|---|---|---|---|
| 1 | 1.45 | 2.76 | -1.05 | 2.9 x 3.8 |
| 4 | 1.45 | 3.44 | -1.05 | 2.9 x 4.5 |
| 8 | 1.45 | 4.01 | -1.05 | 2.9 x 5.1 |

- Tower height `H = clamp(0.62 n, 1.8, 3.05)` (one department is still a spire); deck height `dh = H / n`; floors a deck `FL = max(3, round(dh / 0.2))`; floor `j` of `J = n FL` turned `j * 90deg / J`; width tapers 1.3 -> 0.9.
- Parts
  - plinth: cylinder r 1.4, h 0.36 -> `steel`; torus of light r 1.405 on its top edge -> `A.rim`; keel lathe `(0,-1.05) (0.45,-1.0) (1.0,-0.66) (1.35,-0.36)` -> `dark`
  - per floor: slab `w + 0.06` x 0.035 -> `steel`; glass box `w` x `(dh/FL - 0.035)` -> `A.glass`; core box 0.5 square -> `metal`; four corner posts 0.045 square -> `A.rim`
  - windows: `faceWins` step 0.28, 0.14 wide, half the floor high, deck = `floor(j / FL)`; dark panes left out (on glass a dark pane reads as a hole)
  - crown slab -> `steel`; needle lathe r 0.14, 0.88 high -> `metal`; beacon at `H + 0.96`
  - halo: torus r `0.72 w + 0.12`, tube 0.02 -> `A.rim`, with `glowSprite(A.c, 0.18, 1.2)`
- Accent: corner posts, lit windows, halo, glass tint. About 13 %.
- Motion: the halo travels up and down the spire, `y = 0.02 + (H - 0.04)(1 - cos 0.32 t) / 2` (one climb in 9.8 s), its radius following the taper. Nothing else moves.
- Icon: `<path d="M5 17.6h10 M6.4 17.6C7.2 12.4 8.8 8.8 8 4.4h4C11.2 8.8 12.8 12.4 13.6 17.6 M10.6 17.6C9.6 12.6 11.4 8.6 9.8 4.4 M10 4.4V1.8"/>`

## 03 Solar Sail (`sail`)

Four sail panels between four booms make a square of light; it turns slowly round a slim mast of decks.

| n | foot | top | bot | across x high |
|---|---|---|---|---|
| 1 | 3.30 | 1.12 | -1.00 | 6.6 x 2.1 |
| 4 | 3.30 | 2.02 | -1.00 | 6.6 x 3.0 |
| 8 | 3.30 | 3.22 | -1.00 | 6.6 x 4.2 |

- Parts
  - hub: cylinder r 0.95, h 0.24 at y -0.12 -> `steel`; torus of light r 0.955 -> `A.rim`; keel lathe to y -1.0 -> `dark`
  - mast: per department a drum r 0.42, h 0.25 -> `pale` and a collar r 0.5, h 0.05 -> `metal`, pitch 0.3 from y 0.02; `ringWins` 9 a drum
  - cap: lathe r 0.42 -> 0, 0.23 high -> `metal`; antenna 0.5 + beacon
  - rotor group (dyn): four booms, box 0.08 square from r 0.9 to 3.3 on the diagonals, rising 0.07 per unit outward (4 degree dihedral) -> `metal`; an `A.glow` dot at each tip
  - four sails: between neighbouring booms from r 0.98 to 3.2, a `PlaneGeometry` 5 x 4 segments billowed down 0.24 at its middle -> `A.glass` at 0.18 opacity, `DoubleSide`
  - the square of light: thin box from tip to tip along each sail's outer edge -> `A.rim`; two battens across each sail at 32 % and 64 % -> `A.soft`
- Accent: the square of light, battens, tips, sail tint (film, not paint). About 10 % solid.
- Motion: rotor turns 0.08 rad/s about y. Mast still.
- Icon: `<path d="M1.6 12.4 10 8.4l8.4 4L10 16.4Z M1.6 12.4h16.8 M10 8.4v8 M10 5V2.8"/><rect x="8.8" y="5" width="2.4" height="7.4" rx=".8"/>`

## 04 Deep Array (`dish`)

A parabolic dish on a yoke over a turret of decks, sweeping slowly, its focus lit.

| n | foot | top | bot | across x high |
|---|---|---|---|---|
| 1 | 2.30 | 2.74 | -1.15 | 4.6 x 3.9 |
| 4 | 2.30 | 3.25 | -1.15 | 4.6 x 4.4 |
| 8 | 2.30 | 3.93 | -1.15 | 4.6 x 5.1 |

- Parts
  - platform: cylinder r 1.75, h 0.3 -> `steel`; torus of light r 1.755 -> `A.rim`; keel lathe to -1.15 -> `dark`
  - turret: per department a drum r `0.95 -> 0.85` (narrowing upward), h 0.14 -> `pale`, collar r +0.05, h 0.03 -> `metal`, pitch 0.17; `ringWins` 14 a drum
  - turntable (dyn, yaw `az`): cylinder r 0.9, h 0.14 -> `metal`, torus of light -> `A.rim`; two yoke arms box 0.16 x 0.62 x 0.34 at x = +-0.8 -> `steel`; elevation axle 1.76 long -> `metal`
  - dish (dyn, on the axle 0.76 over the turntable, tilted `el` about x): `LatheGeometry` of the parabola `y = r^2 / (4 x 1.3)` from r 0.3 to 1.85; inside face -> `pale`, back face (0.05 behind) -> `steel`; hub cylinder r 0.32 -> `metal`; rim torus r 1.85, tube 0.055 -> `metal` with a torus of light just outside -> `A.rim`
  - on the inside: 10 radial ribs and two circles (r 1.15, 1.7), thin -> `A.soft`
  - feed: three struts from the rim (120 degrees apart) to the focus at 1.3 on the axis -> `metal`; horn lathe -> `metal`; focus `A.glow` sphere + `glowSprite(A.c, 0.75, 1.5)`
- Accent: rim, ribs, focus. About 9 %.
- Motion: `az = -1.35 + 0.35 sin(0.09 t)` (a sweep of +-20 degrees, 70 s a cycle), `el = 0.75 + 0.06 sin(0.05 t)`. With the station's own angle round the sun known, `az` may point at the sun instead.
- Icon: `<path d="M2.8 11.8a8 8 0 0 0 9-9Z M2.8 11.8 5.2 5.2 11.8 2.8 M9.6 9.6l1.6 5.2 M7.4 17.4h8.8 M8.8 17.4l1.6-2.6h2.6l1.4 2.6"/><circle cx="5.2" cy="5.2" r=".9" fill="currentColor"/>`

## 05 Glass Arcology (`arcology`)

A shallow glass dome over a lit city, one tower per department, a tram circling inside.

| n | foot | top | bot | across x high |
|---|---|---|---|---|
| 1-8 | 2.95 | 2.20 | -1.20 | 5.9 x 3.4 |

- Parts
  - disc: cylinder r 2.9, h 0.4 -> `steel`; torus of light on its top edge -> `A.rim`, a second at y -0.3 -> `A.soft`; keel lathe to -1.2 -> `dark`; city floor r 2.78, h 0.04 -> `metal`
  - towers: department 0 at the centre (0.56 square, 1.6 high); department f at r 1.05 (odd f) or 1.6 (even f), angle `2.4 f + 0.5` (the golden angle spreads them), 0.4 square, `min(1.25 - 0.07 f, under the dome - 0.25)` high -> `pale`; cap -> `metal`; windows every 0.2 up all four faces (deck f), a roof light `A.glow`
  - fill: about 40 low blocks 0.14 to 0.34 wide, 0.06 to 0.4 high, seeded, kept 0.5 clear of the towers -> `steel` / `metal`
  - tram: rail torus r 2.3 at y 0.3 -> `metal`; three cars box 0.12 x 0.09 x 0.32 -> `pale`, an `A.glow` light on each
  - dome: lathe of a quarter ellipse, r 2.72, 2.0 high -> `A.glass`, `DoubleSide`; 12 meridian ribs and two rings (at 31 and 57 degrees) -> `A.wire` (or thin `metal` tubes); oculus ring at 81 degrees -> `A.rim`; beacon at the top
- Accent: rims, oculus, windows, dome tint. About 12 %.
- Motion: tram cars travel the rail at 0.15 rad/s (42 s a lap).
- Icon: `<path d="M1.8 15.2h16.4 M3.2 15.2a6.8 6.8 0 0 1 13.6 0 M3.6 17.4h12.8 M8.8 15.2v-4.6h2.4v4.6 M6 15.2v-2.4h1.8v2.4 M12.2 15.2v-3.2h1.8v3.2 M10 8.4V6.2"/>`

## 06 Pylon Crown (`crown`)

Glass pylons round a ring, one per department, a core of light floating in the middle.

| n | foot | top | bot | across x high |
|---|---|---|---|---|
| 1-8 | 2.30 | 3.10 | -0.80 | 4.6 x 3.9 |

- Eight seats at r 1.85, angle `(k + 0.5) 45deg + 0.2`; department f takes seat `floor(8 f / n)` (4 departments: every other seat, so the crown is balanced at any n). An empty seat holds a low plinth.
- Parts
  - ring: annulus r 1.45 to 2.25, 0.3 thick -> `steel`; torus of light on the outer top edge -> `A.rim`, inner -> `A.soft`; skirts below (lathes to -0.8) -> `dark`
  - pylon (a blade: thin outward, wide along the ring, narrowing), tilted 0.1 rad outward, 2.95 high on even seats and 2.45 on odd: spine, tapered box 0.12 x 0.26 -> 0.08 x 0.12 -> `steel`; blade, tapered box 0.26 x 0.82 -> 0.16 x 0.36, 0.95 of the height -> `A.glass`; its two outer vertical edges -> `A.rim` (thin boxes); windows in two columns on both broad faces every 0.19 (deck f); cap -> `metal`, `A.glow` on top
  - empty seat: box 0.3 x 0.2 x 0.52 -> `steel`, lid -> `metal`
  - core: glass sphere r 0.5 -> `A.glass`, inner sphere r 0.22 -> `A.glow`, `glowSprite(A.c, 0.6, 2.8)`; a column of light from the ring's hole up to it (open cone r 0.62 -> 0.16) -> `A.beam`; an orbit ring r 0.86 -> `A.soft` with three `A.glow` beads
- Accent: pylon edges, windows, the core, rims. About 12 %.
- Motion: core bobs `1.45 + 0.08 sin(0.9 t)` (a 7 s float, not a pulse); beads circle at 0.5 rad/s. Pylons still.
- Icon: `<ellipse cx="10" cy="15.4" rx="8" ry="2.4"/><path d="M3.4 14.4V8 M6.6 13.2V4.2 M13.4 13.2V4.2 M16.6 14.4V8"/><circle cx="10" cy="9" r="1.8"/>`

## 07 Rift Hold (`rift`)

An asteroid split in two, the halves held apart, a glass deck per department bridging the lit rift.

| n | foot | top | bot | across x high |
|---|---|---|---|---|
| 1-8 | 3.45 | 2.85 | -0.95 | 6.9 x 3.8 |

- Rock: `rockGeo(seed)` scaled (2.1, 1.45, 1.8), centred at y 0.55. Two clones: in one clamp every vertex `x = max(x, 0)`, in the other `x = min(x, 0)`, recompute normals, move them +0.5 / -0.5 in x -> `rock` (`flatShading`). The clamp makes each half's inner face flat; the gap is 1.0.
- Parts
  - rift sheet: the rock's cross-section (ellipse 0.82 of it) in the plane x = 0 -> `A.beam`, `DoubleSide`; three seams of light along each inner face at y -0.15, 0.55, 1.25 -> `A.soft`; three `glowSprite(A.c, 0.3, 1.9)` in the gap
  - bridges, one a department: deck height `dh = min(0.42, 1.9 / n)`, centred on y 0.62, alternately at z +0.42 and -0.42; glass box 1.5 x `0.6 dh` x 0.52 (0.25 into each half) -> `A.glass`; plates over and under it 1.6 x 0.04 x 0.6 -> `steel`; five windows a face, both faces (deck f); a line of light under its front edge -> `A.rim`
  - landing pad on the right half: column r 0.26 -> `steel`, deck r 0.55, h 0.08 -> `metal`, ring of light -> `A.rim`, four `A.glow` lights; a mast on the left half to y 2.7 with a beacon
  - two shuttles (box 0.14 x 0.07 x 0.36 -> `pale`, `A.glow` tail) on a circuit r 3.25 at y 0.8 and 1.05
- Accent: the rift (sheet, seams, glows), bridge lines, pad. About 8 %, all of it inside the rift or on the pad: the rock stays bare.
- Motion: shuttles circle at 0.2 rad/s. The halves do not move.
- Icon: `<path d="M8.2 4.4 4.6 5.2 2.2 9.2l.8 5 3.4 2.6h1.8Z M11.8 4l4 1 2.2 4.4-1 5.2-3.2 2.4h-2Z M8.2 8.2h3.6 M8.2 11.2h3.6 M8.2 14.2h3.6"/>`

## 08 Tesseract Frame (`tesseract`)

A cube of struts balanced on one corner, turning; inside it a glass cube of decks turning the other way.

| n | foot | top | bot | across x high |
|---|---|---|---|---|
| 1-4 | 2.00 | 3.23 | -2.05 | 4.0 x 5.3 |
| 5-8 | 2.24 | 3.75 | -2.05 | 4.5 x 5.8 |

- Frame edge `a = 2.3` (n <= 4) or 2.6; stood on a corner: rotate the cube `RZ(atan(sqrt 2)) * RY(45deg)` so its (1,1,1) diagonal is vertical; bottom corner at y -0.95, centre `yc = -0.95 + a sqrt(3) / 2`.
- Parts
  - base: disc r 1.25, h 0.22 at y -1.55 -> `steel`; torus of light -> `A.rim`; keel lathe to -2.05 -> `dark`; a cup the corner sits in (lathe r 0.42 -> 0.16 -> 0.3, y -1.44 to -0.98) -> `metal`
  - frame (dyn): 12 struts 0.11 square -> `metal`; on each, a thin box 0.03 square set 4.5 % out from the centre -> `A.rim` (each edge is a line of light); 8 corner nodes 0.2 cube -> `pale`; beacon + `glowSprite(A.c, 0.5, 0.9)` on the top corner
  - inner cube (dyn), upright: edge `c = 1.25` (n <= 4) or 1.45, a glass box -> `A.glass`, its 12 edges -> `A.soft`; inside, per department a slab `c - 0.1` x 0.045 -> `pale`, its windows on all four glass faces (deck f); `glowSprite(A.c, 0.45, 2.2)` at the centre
- Accent: the frame's edges, inner edges, windows, corner light. About 11 %.
- Motion: frame turns about the vertical at 0.1 rad/s, the inner cube at -0.06 rad/s (their corners pass each other; the inner half-diagonal 1.08 to 1.26 stays well inside the frame's edges at 1.63 to 1.84).
- Icon: `<path d="M10 1.4 16.2 5v7.2L10 15.8 3.8 12.2V5Z M3.8 5 10 8.6 16.2 5 M10 8.6v7.2 M10 15.8v2 M6.6 18.6h6.8"/>`

## 09 Nautilus Shell (`nautilus`)

Chambers on a two-turn log spiral round a glass heart: six sealed ones, then one a department, so the shell grows a chamber with every department.

| n | foot | top | bot | across x high |
|---|---|---|---|---|
| 1-8 | 2.95 | 1.75 | -0.85 | 5.9 x 2.6 |

- Spiral: theta from 0 to 12.6 (two turns); inner wall `rin = 0.384 e^(0.12 theta)`, outer wall `rout = 0.64 e^(0.12 theta)`, height `h = 0.2 e^(0.09 theta)`; each whorl's inner wall stands clear of the last one's outer wall (`rout(theta - 2 pi) = 0.30 e^(0.12 theta)`), leaving a groove. `K = 6 + n` chambers share the 12.6 rad, a gap of 0.04 rad between them. The outer n chambers are the departments.
- Parts
  - chamber: a custom `BufferGeometry` (or an `ExtrudeGeometry` of its plan outline) between `rin` and `rout`, 5 steps along theta: top -> `pale`, inner / outer walls and both end walls (septa) -> `steel`
  - septa: a line of light across the top of every septum -> `A.rim`; the outer top edge -> `A.soft` on department chambers, `A.wire` on sealed ones; the inner top edge -> `A.soft`
  - the groove: a tube along `r = (rin(theta) + rout(theta - 2 pi)) / 2`, y 0.01, theta 2 pi to 12.6 -> `A.rim`
  - the mouth (the last chamber's end): a glass wall -> `A.glass` framed -> `A.rim`, `glowSprite(A.c, 0.4, 1.6)`
  - windows: three on each department chamber's outer wall (deck f)
  - heart: glass sphere r 0.3 at y 0.22 -> `A.glass`, inner sphere r 0.13 -> `A.glow`, `glowSprite(A.c, 0.6, 1.6)`; mast to 1.45 + beacon; keel lathe r 1.9 to -0.85 -> `dark`
- Accent: septa, groove, rim lines, mouth, heart. About 10 %.
- Motion: three lights run out along the outer rim, heart to mouth, at 0.35 rad/s of theta (36 s a run), each starting again at the heart. The shell does not turn.
- Icon: `<path d="M7.3 11.6 7.1 10.8 7.4 10.2 8 9.8 8.7 9.7 9.5 10 10.2 10.7 10.4 11.8 10.1 12.9 9.2 13.8 7.9 14.2 6.4 13.9 5 12.9 4.3 11.1 4.5 9.1 5.7 7.2 8 6 10.8 5.9 13.5 7.4 15.4 10.2 15.8 12.1 M7.1 11 4.3 10.2 M8.2 9.8 7.9 6 M10.1 10.6 14.6 8.8"/>`

## 10 Halo Vortex (`vortex`)

Flat rings floating one above another round a column of light, wider as they rise, alternate ones turning the other way.

| n | foot | top | bot | across x high |
|---|---|---|---|---|
| 1-4 | 3.05 | 2.19 | -0.95 | 6.1 x 3.1 |
| 8 | 3.05 | 3.11 | -0.95 | 6.1 x 4.1 |

- `K = max(4, n)` rings (rings past n carry no windows); ring k: inner radius `1.0 + 1.8 k / (K - 1)`, section 0.2 wide x 0.11 high, at `y = 0.15 + k dh`, `dh = min(0.42, 2.15 / (K - 1))`.
- Parts
  - ring (dyn): a rectangle lathed (or `RingGeometry` extruded 0.11): top -> `metal`, walls -> `steel`; torus of light on the outer top edge -> `A.rim`, on the inner -> `A.soft`; `ringWins` on the outer wall, one per 0.3 of its length (deck k, for k < n); two markers on opposite sides, box 0.14 x 0.08 x 0.28 -> `metal` with an `A.glow` light (they show the turn)
  - column: glass cylinder r 0.2 from y -0.05 to 0.45 over the top ring -> `A.glass`; core cylinder r 0.06 the same length -> `A.glow`; collars r 0.28 at both ends -> `metal`; a light at its top, `A.glow` + `glowSprite(A.c, 0.7, 1.6)`; three `glowSprite(A.c, 0.22, 1.3)` along it
  - base: emitter lathe `(0,-0.95) (0.26,-0.88) (0.56,-0.5) (0.62,-0.32) (0.36,-0.16) (0.22,-0.06)` -> `steel`; torus of light r 0.6 at y -0.4 -> `A.rim`
- Accent: ring edges, the column, windows, markers. About 12 %.
- Motion: ring k turns at `+-(0.22 - 0.015 k)` rad/s, sign alternating; each bobs `0.035 sin(0.8 t + 0.7 k)` so a slow wave runs up the stack. The rings touch nothing: no spokes.
- Icon: `<path d="M2 5.4a8 2.2 0 1 0 16 0 8 2.2 0 1 0-16 0 M4.2 9.6a5.8 1.6 0 1 0 11.6 0 5.8 1.6 0 1 0-11.6 0 M6.3 13.4a3.7 1.1 0 1 0 7.4 0 3.7 1.1 0 1 0-7.4 0 M10 18.4V3.2"/>`
