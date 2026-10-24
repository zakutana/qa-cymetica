/* Two more stations, built the way the seven are (the operator, 2026-10-24: "predelat vsechny ty spodni modely na zpusob
 * vrchnich ... at to udelaji stejne a mame jen jeden zpusob"): a Glass Arcology and a Pylon Crown, from
 * outbox/company-skins/SPEC.md (05 and 06). Same parts and same finish as stations.js (CO.ST: plated hull from mats(),
 * windows lit deck by deck with wins() / b.win, greebles, engines, halos, b.beacon, merged by b.bake()), the company's
 * colour only in lights. Nothing pulses: the tram travels, the crown's core floats and its beads circle.
 *
 * A module of its own, run after stations.js: it puts its builders into u3d.js's table (CO.U3.SKIN) and says so with
 * the event co3d-skins. */
import * as THREE from 'three/webgpu';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

const CO = window.CO;
const V = THREE.Vector3;
const TAU = Math.PI * 2;

/* ---------------- geometry the parts of stations.js do not make, cached in its table ---------------- */
// a cylinder whose plating keeps its size: the caps tile by their diameter, the side by its circumference and height
function pcyl(rt, rb, h, seg, open) {
  const { G, TS, key } = CO.ST, k = key('c-cy', [rt, rb, h, seg, open ? 1 : 0]);
  if (G[k]) return G[k];
  const g = new THREE.CylinderGeometry(rt, rb, h, seg, 1, !!open), uv = g.attributes.uv, nr = g.attributes.normal, r = Math.max(rt, rb);
  for (let i = 0; i < uv.count; i++) {
    if (Math.abs(nr.getY(i)) > 0.99) uv.setXY(i, uv.getX(i) * 2 * r / TS, uv.getY(i) * 2 * r / TS);
    else uv.setXY(i, uv.getX(i) * TAU * r / TS, uv.getY(i) * h / TS);
  }
  return (G[k] = g);
}
// a profile turned about the y axis; pts run so that (dy, -dx) of each step points out of the solid; plating in tiles
function lathe(k, pts, seg) {
  const { G, TS } = CO.ST;
  if (G[k]) return G[k];
  const g = new THREE.LatheGeometry(pts.map((p) => new THREE.Vector2(p[0], p[1])), seg), uv = g.attributes.uv;
  let len = 0, rm = 0;
  for (let i = 1; i < pts.length; i++) len += Math.hypot(pts[i][0] - pts[i - 1][0], pts[i][1] - pts[i - 1][1]);
  pts.forEach((p) => { rm = Math.max(rm, p[0]); });
  for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * TAU * rm / TS, uv.getY(i) * len / TS);
  return (G[k] = g);
}
// a box that narrows: wb x db at the foot, wt x dt at the top, h high, standing on y = 0 (x thin, z wide for a blade)
function taper(wb, db, wt, dt, h) {
  const { G, TS, key } = CO.ST, k = key('c-tp', [wb, db, wt, dt, h]);
  if (G[k]) return G[k];
  const g = new THREE.BoxGeometry(1, 1, 1), p = g.attributes.position;
  for (let i = 0; i < p.count; i++) { const top = p.getY(i) > 0; p.setXYZ(i, p.getX(i) * (top ? wt : wb), (p.getY(i) + 0.5) * h, p.getZ(i) * (top ? dt : db)); }
  g.computeVertexNormals();
  const uv = g.attributes.uv, nr = g.attributes.normal, aw = (wb + wt) / 2, ad = (db + dt) / 2;
  for (let i = 0; i < uv.count; i++) {
    const sp = Math.abs(nr.getX(i)) > 0.5 ? [ad, h] : Math.abs(nr.getZ(i)) > 0.5 ? [aw, h] : [aw, ad];
    uv.setXY(i, uv.getX(i) * sp[0] / TS, uv.getY(i) * sp[1] / TS);
  }
  return (G[k] = g);
}
// a small round bead: lights and bulbs
function bead(r, seg) { const { G, key } = CO.ST, k = key('c-bd', [r, seg || 10]); return G[k] || (G[k] = new THREE.SphereGeometry(r, seg || 10, Math.max(6, (seg || 10) * 0.7 | 0))); }
// a thin round rod from one point to another
function rod(p0, p1, r) {
  const d = p1.clone().sub(p0), len = d.length(), g = new THREE.CylinderGeometry(r, r, len, 5, 1);
  g.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(new V(0, 1, 0), d.normalize()));
  g.translate((p0.x + p1.x) / 2, (p0.y + p1.y) / 2, (p0.z + p1.z) / 2);
  return g;
}
// The two glasses these stations want beyond u3d.js's A.glass (too faint to read as a pane, and one-sided): hung on the
// colour's own set, like stations.js's A.ns, so release() keeps them and a rebuilt station finds them again
function glasses(A) {
  if (A.nsC) return A.nsC;
  const c = A.c;
  A.nsC = {
    pane: new THREE.MeshStandardMaterial({ color: c.clone().multiplyScalar(0.3), transparent: true, opacity: 0.28, roughness: 0.1, metalness: 0.2, emissive: c.clone(), emissiveIntensity: 0.13, depthWrite: false, side: THREE.DoubleSide }),
    dome: new THREE.MeshStandardMaterial({ color: c.clone().multiplyScalar(0.3), transparent: true, opacity: 0.11, roughness: 0.06, metalness: 0.2, emissive: c.clone(), emissiveIntensity: 0.07, depthWrite: false, side: THREE.DoubleSide })
  };
  return A.nsC;
}
// a geometry of its own, placed in station space (b.bake() merges it away; one that stays is let go with the station)
function addG(b, geom, mat) { const m = new THREE.Mesh(geom, mat); m.userData.own = true; b.g.add(m); return m; }
// a part that travels: turns about y at `rate` radians a second (x1.6 while a deck works), never jumping when the rate changes
function turner(b, g, rate, sign) {
  let ang = b.phase, last = null;
  b.anim.push((t) => {
    // (a clock that ran backwards, or a tab that woke after a long sleep, moves it no more than a quarter second)
    const dt = last == null ? 0 : Math.max(0, Math.min(0.25, t - last)); last = t;
    ang += dt * rate * (b.busy ? 1.6 : 1);
    g.rotation.y = sign * ang;
  });
}

/* ================= 05 Glass Arcology: a shallow glass dome over a lit city, a tower a department, a tram circling ================= */
function arcology(b, n) {
  const { mats, put, box, wins, sprite, rnd, torus, cyl, engine, G } = CO.ST;
  const A = b.A, M = mats(A), R = rnd(31), DR = 2.72, DH = 2.0, F = 0.04;
  const sq = (v) => v * v;
  // the disc the city stands on: plated rim wall, its edge lit, a second line of light low on it; the keel under it
  put(b, pcyl(2.9, 2.9, 0.4, 72), M.mid, 0, -0.2, 0);
  put(b, pcyl(2.93, 2.93, 0.05, 72), M.metal, 0, -0.025, 0);
  put(b, torus(2.93, 0.028, 6, 112), M.neon, 0, 0.0, 0, { rx: Math.PI / 2 });
  put(b, torus(2.9, 0.02, 6, 112), M.neonSoft, 0, -0.3, 0, { rx: Math.PI / 2 });
  put(b, lathe('c5-keel', [[0.34, -1.08], [0.55, -1.0], [1.1, -0.98], [2.2, -0.74], [2.8, -0.4]], 72), M.dark, 0, 0, 0);
  // (a keel's ribs: plates down its flank, one under each tower seat of the city above)
  for (let k = 0; k < 12; k++) {
    const a = k / 12 * TAU + 0.26, r = 1.7;
    box(b, 1.1, 0.07, 0.16, Math.cos(a) * r, -0.87, Math.sin(a) * r, M.mid, { ry: -a, rz: 0.215 });
  }
  // the windows of the disc's rim: a row all round, a share to each department (by the sector it sits in)
  const mouths = 8, mAng = (k) => (k + 0.5) / mouths * TAU;
  for (let i = 0, m = Math.round(TAU * 2.9 / 0.2); i < m; i++) {
    const t = (i + 0.5) / m * TAU;
    if (Array.from({ length: mouths }, (_, k) => k).some((k) => Math.abs(Math.atan2(Math.sin(t - mAng(k)), Math.cos(t - mAng(k)))) < 0.1)) continue;
    b.win(Math.cos(t) * (2.9 + 0.014), -0.11, Math.sin(t) * (2.9 + 0.014), Math.PI / 2 - t, 0.1, 0.07, Math.floor(t / TAU * n) % n, b.R() < 0.7);
  }
  // the hangar mouths, glowing in the rim wall
  for (let k = 0; k < mouths; k++) { const a = mAng(k); box(b, 0.34, 0.13, 0.02, Math.cos(a) * 2.9, -0.2, Math.sin(a) * 2.9, M.hot, { ry: Math.PI / 2 - a }); }
  // the keel's drive, and four thruster pods hanging off its flank (no plume: a lit mouth and its halo)
  engine(b, M, 0, -0.9, 0, 0.3, 0, 1.0).rotation.x = -Math.PI / 2;
  for (let k = 0; k < 4; k++) { const a = k * Math.PI / 2 + Math.PI / 4; engine(b, M, Math.cos(a) * 2.05, -0.8, Math.sin(a) * 2.05, 0.15, 0, 0.7).rotation.x = -Math.PI / 2; }
  // the city floor, and the parapet it is held in, a pier at the foot of every rib of the dome
  put(b, pcyl(2.7, 2.7, F, 72), M.dark, 0, F / 2, 0);
  put(b, lathe('c5-par', [[2.84, 0], [2.84, 0.17], [2.7, 0.17], [2.7, F]], 72), M.mid, 0, 0, 0);
  put(b, torus(2.77, 0.02, 5, 112), M.neonSoft, 0, 0.175, 0, { rx: Math.PI / 2 });
  for (let k = 0; k < 12; k++) { const a = k / 12 * TAU; box(b, 0.22, 0.26, 0.2, Math.cos(a) * 2.76, 0.13, Math.sin(a) * 2.76, M.metal, { ry: -a }); }
  // the city's streets in light: a ring road in, a ring road at the edge
  put(b, torus(0.64, 0.012, 4, 64), M.neonSoft, 0, F + 0.01, 0, { rx: Math.PI / 2 });
  put(b, torus(2.02, 0.012, 4, 112), M.neonSoft, 0, F + 0.01, 0, { rx: Math.PI / 2 });
  put(b, torus(2.58, 0.012, 4, 112), M.neonSoft, 0, F + 0.01, 0, { rx: Math.PI / 2 });
  for (let k = 0; k < 8; k++) { const a = k / 8 * TAU + 0.2; box(b, 1.3, 0.012, 0.016, Math.cos(a) * 1.35, F + 0.008, Math.sin(a) * 1.35, M.neonSoft, { ry: -a }); }
  // the towers, a department each: the first at the heart of the city, the rest on two rings, spread by the golden angle
  const spots = [];
  for (let f = 0; f < n; f++) {
    const r = f ? (f % 2 ? 1.05 : 1.6) : 0, a = 2.4 * f + 0.5, x = Math.cos(a) * r, z = Math.sin(a) * r, w = f ? 0.4 : 0.56;
    const hmax = DH * Math.sqrt(Math.max(0, 1 - sq((r + w * 0.75) / DR))) - 0.25, h = Math.min(hmax, f ? 1.25 - 0.07 * f : 1.6);
    spots.push([x, z]);
    const hp = 0.07, hs = (h - hp) * 0.72, hu = h - hp - hs - 0.08, y0 = F;
    box(b, w + 0.1, hp, w + 0.1, x, y0 + hp / 2, z, M.mid);
    box(b, w, hs, w, x, y0 + hp + hs / 2, z, M.light);
    box(b, w + 0.04, 0.03, w + 0.04, x, y0 + hp + hs + 0.015, z, M.metal);
    box(b, w * 0.8, hu, w * 0.8, x, y0 + hp + hs + 0.03 + hu / 2, z, M.mid);
    box(b, w * 0.8 + 0.05, 0.05, w * 0.8 + 0.05, x, y0 + h - 0.025, z, M.metal);
    // a deck's windows up all four faces, every row of the shaft and of its setback
    const rs = Math.max(1, Math.floor((hs - 0.08) / 0.16)), ru = Math.max(1, Math.floor((hu - 0.04) / 0.14));
    wins(b, f, x, y0 + hp + hs / 2, z, w, w, rs, Math.min(0.16, (hs - 0.08) / rs), 0.12, 0.64);
    wins(b, f, x, y0 + hp + hs + 0.03 + hu / 2, z, w * 0.8, w * 0.8, ru, Math.min(0.14, (hu - 0.04) / ru), 0.12, 0.7);
    // a light line up two corners, a mast, a roof light
    for (const [sx, sz] of [[1, 1], [-1, -1]]) box(b, 0.025, hs, 0.025, x + sx * w / 2, y0 + hp + hs / 2, z + sz * w / 2, M.neonSoft);
    put(b, cyl(0.012, 0.016, f ? 0.2 : 0.3, 6), M.metal, x, y0 + h + (f ? 0.1 : 0.15), z);
    put(b, bead(0.035, 8), A.glow, x, y0 + h + (f ? 0.22 : 0.33), z);
  }
  // the fill: low blocks between the towers (windows on the taller, a few lit roofs), and a band of the lowest at the edge
  for (let i = 0, tries = 0; i < 40 && tries < 600; tries++) {
    const r = 0.45 + R() * 1.55, a = R() * TAU, x = Math.cos(a) * r, z = Math.sin(a) * r;
    if (spots.some(([sx, sz]) => Math.hypot(sx - x, sz - z) < 0.55)) continue;
    const w = 0.14 + R() * 0.2, d = 0.14 + R() * 0.2, h = 0.06 + R() * R() * 0.34;
    box(b, w, h, d, x, F + h / 2, z, [M.mid, M.metal, M.dark][i % 3]);
    if (h >= 0.2 && w >= 0.2) { const rows = Math.max(1, Math.floor((h - 0.04) / 0.12)); wins(b, Math.floor(R() * n), x, F + h / 2, z, w, d, rows, Math.min(0.12, (h - 0.04) / rows), 0.12, 0.6); }
    else if (i % 3 === 0) box(b, w * 0.5, 0.02, d * 0.5, x, F + h + 0.01, z, M.hot);
    i++;
  }
  for (let i = 0, tries = 0; i < 16 && tries < 200; tries++) {
    const a = R() * TAU, r = 2.46 + R() * 0.16, w = 0.12 + R() * 0.12, h = 0.05 + R() * 0.07;
    box(b, w, h, 0.12 + R() * 0.1, Math.cos(a) * r, F + h / 2, Math.sin(a) * r, i % 2 ? M.metal : M.mid, { ry: -a }); i++;
  }
  // the tram's track: a rail on posts, a line of light along it; three cars ride it (below, in the moving part)
  put(b, torus(2.3, 0.026, 6, 112), M.metal, 0, 0.3, 0, { rx: Math.PI / 2 });
  put(b, torus(2.3, 0.011, 4, 112), M.neonSoft, 0, 0.332, 0, { rx: Math.PI / 2 });
  for (let k = 0; k < 16; k++) { const a = k / 16 * TAU; box(b, 0.04, 0.26, 0.04, Math.cos(a) * 2.3, F + 0.13, Math.sin(a) * 2.3, M.metal); }
  // the dome: a quarter ellipse of glass, 12 ribs from foot to crown, rings of metal at 31 and 57 degrees, a light at each crossing
  const prof = [];
  for (let i = 0; i <= 12; i++) { const ph = i / 12 * Math.PI / 2; prof.push([i === 12 ? 0 : DR * Math.cos(ph), F + DH * Math.sin(ph)]); }
  put(b, lathe('c5-dome', prof, 72), glasses(A).dome, 0, 0, 0);
  for (let k = 0; k < 12; k++) put(b, torus(DR, 0.02, 6, 28, Math.PI / 2), M.metal, 0, F, 0, { ry: k / 12 * TAU, s: [1, DH / DR, 1] });
  const rings = [31, 57].map((d) => d * Math.PI / 180);
  for (const ph of rings) {
    put(b, torus(DR * Math.cos(ph), 0.024, 6, 84), M.metal, 0, F + DH * Math.sin(ph), 0, { rx: Math.PI / 2 });
    for (let k = 0; k < 12; k++) { const g = k / 12 * TAU; put(b, bead(0.034, 8), A.glow, Math.cos(g) * DR * Math.cos(ph), F + DH * Math.sin(ph), Math.sin(g) * DR * Math.cos(ph)); }
  }
  // the oculus at 81 degrees: a ring of light, the hub that gathers the ribs, a mast and the beacon
  const po = 81 * Math.PI / 180;
  put(b, torus(DR * Math.cos(po), 0.022, 6, 48), M.neon, 0, F + DH * Math.sin(po), 0, { rx: Math.PI / 2 });
  put(b, pcyl(0.36, 0.3, 0.12, 24), M.mid, 0, F + DH - 0.02, 0);
  put(b, cyl(0.014, 0.022, 0.12, 6), M.metal, 0, F + DH + 0.06, 0);
  b.beacon(0, F + DH + 0.14, 0, 0.045);
  // the tram: three cars on the rail, a light on each, travelling slowly round it
  const tram = new THREE.Group(); tram.userData.dyn = true; b.g.add(tram);
  if (!G['c5-cars']) {
    const hull = [], lamps = [], lights = [];
    for (let k = 0; k < 3; k++) {
      // (a third larger than the spec's 0.12 x 0.09 x 0.32: at the map's distance those are a speck)
      const a = k / 3 * TAU, x = Math.cos(a) * 2.3, z = Math.sin(a) * 2.3, car = new THREE.BoxGeometry(0.16, 0.12, 0.44), lamp = new THREE.BoxGeometry(0.17, 0.03, 0.28);
      car.rotateY(-a); car.translate(x, 0.385, z); hull.push(car);
      lamp.rotateY(-a); lamp.translate(x, 0.4, z); lamps.push(lamp);
      lights.push(new THREE.SphereGeometry(0.04, 8, 6).translate(x, 0.47, z));
    }
    G['c5-cars'] = [mergeGeometries(hull, false), mergeGeometries(lamps, false), mergeGeometries(lights, false)];
  }
  tram.add(new THREE.Mesh(G['c5-cars'][0], M.light), new THREE.Mesh(G['c5-cars'][1], M.hot), new THREE.Mesh(G['c5-cars'][2], A.glow));
  turner(b, tram, 0.15, -1);
  // the city's glow under the glass
  sprite(b, M.halo, 0, 0.7, 0, 3.0);
  b.top = 2.2; b.bot = -1.2; b.foot = 2.95;
}

/* ================= 06 Pylon Crown: glass pylons round a ring, a pylon a department, a core of light floating in the middle ================= */
function crown(b, n) {
  const { mats, put, box, greebles, rnd, torus, cyl, engine, G } = CO.ST;
  const A = b.A, M = mats(A), RP = 1.85, SEATS = 8;
  const seatAng = (k) => (k + 0.5) * Math.PI / 4 + 0.2;
  // seat -> the department that sits on it: department f takes seat floor(8 f / n), so a crown is balanced at any n
  const taken = new Map();
  for (let f = 0; f < Math.min(n, SEATS); f++) taken.set(Math.floor(SEATS * f / n), f);
  // the ring: plated top and walls, its outer edge lit, its inner edge in a softer line, bowl-shaped skirts under it
  put(b, lathe('c6-ring', [[2.25, -0.3], [2.25, 0], [1.45, 0], [1.45, -0.3], [2.25, -0.3]], 72), M.mid, 0, 0, 0);
  put(b, lathe('c6-skO', [[1.65, -0.8], [2.0, -0.68], [2.23, -0.3]], 72), M.dark, 0, 0, 0);
  put(b, lathe('c6-skI', [[1.45, -0.3], [1.65, -0.8]], 72), M.dark, 0, 0, 0);
  put(b, torus(1.65, 0.02, 5, 72), M.metal, 0, -0.8, 0, { rx: Math.PI / 2 });
  put(b, torus(2.25, 0.03, 6, 112), M.neon, 0, 0.0, 0, { rx: Math.PI / 2 });
  put(b, lathe('c6-lip', [[1.62, 0], [1.62, 0.07], [1.45, 0.07], [1.45, 0]], 72), M.light, 0, 0, 0);
  put(b, torus(1.46, 0.022, 6, 96), M.neonSoft, 0, 0.07, 0, { rx: Math.PI / 2 });
  put(b, torus(2.0, 0.016, 5, 112), M.neonSoft, 0, -0.5, 0, { rx: Math.PI / 2 });
  // the outer wall: a lip below its lit edge, ribs between the windows, a light mast between each pair of seats
  put(b, torus(2.26, 0.026, 5, 112), M.metal, 0, -0.3, 0, { rx: Math.PI / 2 });
  for (let k = 0, m = Math.round(TAU * 2.25 / 0.2); k < m; k += 3) { const t = k / m * TAU; box(b, 0.05, 0.26, 0.07, Math.cos(t) * 2.265, -0.15, Math.sin(t) * 2.265, M.metal, { ry: -t }); }
  for (let k = 0; k < 4; k++) {
    const a = k * Math.PI / 2 + 0.2, x = Math.cos(a) * 2.08, z = Math.sin(a) * 2.08;
    put(b, cyl(0.014, 0.02, 0.34, 6), M.metal, x, 0.17, z);
    put(b, bead(0.035, 8), A.glow, x, 0.36, z);
  }
  // the ring's top: machinery between the seats, clear of the pylons' feet
  greebles(b, [M.mid, M.dark, M.light, M.mid], 0, -2.2, 2.2, -2.2, 2.2, 90, (x, z) => {
    const r = Math.hypot(x, z); if (r < 1.57 || r > 2.12) return false;
    const th = Math.atan2(z, x);
    for (let k = 0; k < SEATS; k++) { const d = Math.atan2(Math.sin(th - seatAng(k)), Math.cos(th - seatAng(k))); if (Math.abs(d) * r < 0.66) return false; }
    return true;
  }, 61);
  // the windows round the ring's outer wall: each seat's stretch belongs to the department on it; between the seats, hangar mouths
  for (let i = 0, m = Math.round(TAU * 2.25 / 0.2); i < m; i++) {
    const t = (i + 0.5) / m * TAU, s = ((t - 0.2) / (Math.PI / 4) % SEATS + SEATS) % SEATS, k = Math.floor(s), fr = s - k;
    if (fr < 0.14 || fr > 0.86) continue;
    b.win(Math.cos(t) * (2.25 + 0.014), -0.14, Math.sin(t) * (2.25 + 0.014), Math.PI / 2 - t, 0.1, 0.07, taken.has(k) ? taken.get(k) : k % n, b.R() < 0.7);
  }
  for (let k = 0; k < SEATS; k++) { const a = k * Math.PI / 4 + 0.2; box(b, 0.34, 0.13, 0.02, Math.cos(a) * 2.25, -0.15, Math.sin(a) * 2.25, M.hot, { ry: Math.PI / 2 - a }); }
  // under the ring: four drives on the skirt and, in the hole, the emitter the column of light stands on
  for (let k = 0; k < 4; k++) { const a = k * Math.PI / 2 + Math.PI / 4; engine(b, M, Math.cos(a) * 1.95, -0.66, Math.sin(a) * 1.95, 0.15, 0, 0.7).rotation.x = -Math.PI / 2; }
  put(b, pcyl(0.72, 0.6, 0.1, 40), M.dark, 0, -0.5, 0);
  put(b, pcyl(0.5, 0.5, 0.02, 40), M.neonSoft, 0, -0.44, 0);
  put(b, pcyl(0.2, 0.2, 0.026, 28), M.hot, 0, -0.44, 0);
  put(b, torus(0.62, 0.02, 5, 56), M.neon, 0, -0.45, 0, { rx: Math.PI / 2 });
  for (let k = 0; k < 4; k++) { const a = k * Math.PI / 2 + Math.PI / 4; box(b, 0.8, 0.06, 0.06, Math.cos(a) * 1.12, -0.5, Math.sin(a) * 1.12, M.metal, { ry: -a }); }
  engine(b, M, 0, -0.65, 0, 0.17, 0, 0.8).rotation.x = -Math.PI / 2;
  // the pylons, and on a seat with no department a low plinth with a lit lid
  const Q = new THREE.Quaternion(), T = new THREE.Matrix4(), one = new V(1, 1, 1), eu = new THREE.Euler(0, 0, 0, 'YZX');
  for (let k = 0; k < SEATS; k++) {
    const a = seatAng(k), x = Math.cos(a) * RP, z = Math.sin(a) * RP;
    if (!taken.has(k)) {
      box(b, 0.3, 0.2, 0.52, x, 0.1, z, M.mid, { ry: -a });
      box(b, 0.22, 0.04, 0.44, x, 0.22, z, M.metal, { ry: -a });
      box(b, 0.04, 0.025, 0.12, x, 0.25, z, M.hot, { ry: -a });
      continue;
    }
    const f = taken.get(k), H = k % 2 ? 2.45 : 2.95, Hg = H * 0.95;
    box(b, 0.5, 0.1, 1.0, x, 0.05, z, M.mid, { ry: -a });
    for (const s of [-1, 1]) box(b, 0.4, 0.18, 0.12, x - Math.sin(a) * s * 0.56, 0.09, z + Math.cos(a) * s * 0.56, M.metal, { ry: -a });
    box(b, 0.025, 0.025, 1.0, x + Math.cos(a) * 0.25, 0.1, z + Math.sin(a) * 0.25, M.neonSoft, { ry: -a });
    eu.set(0, -a, -0.1); Q.setFromEuler(eu); T.compose(new V(x, 0.02, z), Q, one);
    const at = (geo, mat) => addG(b, geo.clone().applyMatrix4(T), mat), P = (px, py, pz) => new V(px, py, pz).applyMatrix4(T);
    at(taper(0.12, 0.26, 0.08, 0.12, H), M.mid);
    at(taper(0.26, 0.82, 0.16, 0.36, Hg), glasses(A).pane);
    // the blade's edges in light, outer ones bright; the decks seen through the glass
    const tx = (y) => 0.26 - 0.1 * y / Hg, dz = (y) => 0.82 - 0.46 * y / Hg;
    for (const s of [1, -1]) {
      addG(b, rod(P(0.13, 0.02, s * 0.41), P(0.08, Hg, s * 0.18), 0.016), M.neon);
      addG(b, rod(P(-0.13, 0.02, s * 0.41), P(-0.08, Hg, s * 0.18), 0.01), M.neonSoft);
    }
    for (let y = 0.38; y < Hg - 0.2; y += 0.38) { const w = Math.round(tx(y) * 0.8 / 0.02) * 0.02, d = Math.round(dz(y) * 0.92 / 0.02) * 0.02; at(CO.ST.pbox(w, 0.03, d).clone().translate(0, y, 0), M.metal); }
    // a deck's windows, two columns on both broad faces, every 0.19 up the blade
    const yaw = Math.PI / 2 - a;
    for (let y = 0.2; y < Hg - 0.15; y += 0.19) for (const s of [1, -1]) for (const c of [-1, 1]) {
      const p = P(s * (tx(y) / 2 + 0.015), y, c * dz(y) * 0.2);
      b.win(p.x, p.y, p.z, s > 0 ? yaw : yaw + Math.PI, 0.1, 0.07, f, b.R() < 0.78);
    }
    // the cap, a light on its crown (a beacon on the tall ones)
    at(CO.ST.pbox(0.14, 0.06, 0.32).clone().translate(0, H + 0.03, 0), M.metal);
    const tip = P(0, H + 0.14, 0);
    if (k % 2 === 0) b.beacon(tip.x, tip.y, tip.z, 0.045); else put(b, bead(0.04, 8), A.glow, tip.x, tip.y, tip.z);
  }
  // the core: a glass sphere round a sphere of light, a halo, a ring with three beads, floating in the middle
  const yc = 1.45, core = new THREE.Group(); core.userData.dyn = true; core.position.y = yc; b.g.add(core);
  const mk = (geo, mat, y) => { const m = new THREE.Mesh(geo, mat); if (y) m.position.y = y; core.add(m); return m; };
  const sph = (r, u, v) => { const k = 'c6-sp' + r; return G[k] || (G[k] = new THREE.SphereGeometry(r, u, v)); };
  mk(sph(0.5, 28, 16), glasses(A).pane);
  mk(sph(0.24, 20, 12), A.glow);
  const halo = new THREE.Sprite(M.halo); halo.scale.setScalar(2.8); halo.userData.dyn = true; core.add(halo);
  const ring = mk(torus(0.86, 0.014, 5, 72), M.neonSoft); ring.rotation.x = Math.PI / 2;
  const beads = new THREE.Group(); beads.userData.dyn = true; core.add(beads);
  if (!G['c6-beads']) {
    const gs = [];
    for (let k = 0; k < 3; k++) gs.push(new THREE.SphereGeometry(0.05, 10, 7).translate(Math.cos(k / 3 * TAU) * 0.86, 0, Math.sin(k / 3 * TAU) * 0.86));
    G['c6-beads'] = mergeGeometries(gs, false);
  }
  beads.add(new THREE.Mesh(G['c6-beads'], A.glow));
  turner(b, beads, 0.5, -1);
  b.anim.push((t) => { core.position.y = yc + 0.08 * Math.sin(0.9 * t + b.phase); });
  // the column of light from the emitter in the ring's hole up to the core
  const col = (rt, rb, y0, y1) => { const k = 'c6-col' + [rt, rb, y0, y1].join(','); return G[k] || (G[k] = new THREE.CylinderGeometry(rt, rb, y1 - y0, 28, 1, true).translate(0, (y0 + y1) / 2, 0)); };
  put(b, col(0.16, 0.62, -0.44, yc - 0.4), A.beam, 0, 0, 0);
  put(b, col(0.08, 0.3, -0.44, yc - 0.4), A.beam, 0, 0, 0);
  b.top = 3.1; b.bot = -0.8; b.foot = 2.3;
}

/* ---------------- into u3d.js's table ---------------- */
function install() {
  const U = CO.U3;
  if (!U || !U.ok || !U.SKIN || !CO.ST || U.skinsC === '1') return;
  U.SKIN.arcology = arcology;
  U.SKIN.crown = crown;
  U.skinsC = '1';
  window.dispatchEvent(new Event('co3d-skins'));
}
if (CO.U3 && CO.ST) install(); else window.addEventListener('co3d', install, { once: true });
