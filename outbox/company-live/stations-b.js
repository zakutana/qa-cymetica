/* Two of the ten newer stations, built the way the seven are (the operator, 2026-10-24: "ty spodni modely sou jakoby
 * udelane v jinem stylu ... predelat vsechny ty spodni modely na zpusob vrchnich ... at to udelaji stejne a mame jen
 * jeden zpusob"): a Solar Sail and a Deep Array. Their design is outbox/company-skins/SPEC.md (03 and 04, to the
 * number); their finish is stations.js's: a dark plated hull from mats(A), the company's colour only in lights
 * (neon lines, hot dots, halos), a window row on every deck lit while its department works, small surface detail,
 * nothing that pulses (what moves turns or sweeps slowly). Everything goes through CO.ST, the parts stations.js
 * publishes, and one material per look.
 *
 * What turns is a dyn group (u3d.js's bake leaves those alone), so each is merged here by material into a handful of
 * meshes; everything that stands still is baked by b.bake() as the seven are. */
import * as THREE from 'three/webgpu';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

const CO = window.CO;
const TAU = Math.PI * 2, PI = Math.PI;

/* ---------------- geometry: plated cylinders and lathes whose plating keeps its size, parts merged by material ---------------- */
// a cylinder whose plating keeps its size whatever the cylinder's size (CylinderGeometry's uv run 0..1 round it)
function pcyl(rt, rb, h, seg) {
  const { G, TS, key } = CO.ST, k = key('stBc', [rt, rb, h, seg]);
  if (G[k]) return G[k];
  const g = new THREE.CylinderGeometry(rt, rb, h, seg, 1, false), uv = g.attributes.uv, nr = g.attributes.normal;
  const rm = Math.max(rt, rb), cu = TAU * rm / TS, cv = Math.hypot(rt - rb, h) / TS;
  for (let i = 0; i < uv.count; i++) {
    if (Math.abs(nr.getY(i)) > 0.99) uv.setXY(i, uv.getX(i) * 2 * rm / TS, uv.getY(i) * 2 * rm / TS);
    else uv.setXY(i, uv.getX(i) * cu, uv.getY(i) * cv);
  }
  return (G[k] = g);
}
// a profile [[r, y], ...] turned about y, its outside to the right of the way the list runs (bottom to top for a hull);
// plating in tiles of the hull's size, k tiles per TS along the way and round
function plathe(name, prof, seg, dens) {
  const { G, TS, key } = CO.ST, k = key('stBl' + name, [seg, dens || 1]);
  if (G[k]) return G[k];
  const g = new THREE.LatheGeometry(prof.map((p) => new THREE.Vector2(p[0], p[1])), seg), uv = g.attributes.uv;
  let len = 0, rm = 0; prof.forEach((p, i) => { rm = Math.max(rm, p[0]); if (i) len += Math.hypot(p[0] - prof[i - 1][0], p[1] - prof[i - 1][1]); });
  const d = dens || 1;
  for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * TAU * rm * d / TS, uv.getY(i) * len * d / TS);
  return (G[k] = g);
}
const UB = new THREE.BoxGeometry(1, 1, 1);   // a unit box: scaled into a thin bar, a dot, a slit
const _q = new THREE.Quaternion(), _e = new THREE.Euler(), _v = new THREE.Vector3(), _s = new THREE.Vector3(), _a = new THREE.Vector3(), _b = new THREE.Vector3(), Z = new THREE.Vector3(0, 0, 1);
function push(bins, mat, geom, m) {
  let l = bins.get(mat); if (!l) bins.set(mat, l = []);
  const g = geom.clone(); g.applyMatrix4(m);
  if (g.index) { l.push(g.toNonIndexed()); g.dispose(); } else l.push(g);
}
// a part at x, y, z turned by o.rx/ry/rz (o.s: scale), into the bins of a group that moves
function at(bins, mat, geom, x, y, z, o) {
  o = o || {}; _e.set(o.rx || 0, o.ry || 0, o.rz || 0, o.order || 'XYZ'); _q.setFromEuler(_e);
  const s = o.s || [1, 1, 1];
  push(bins, mat, geom, new THREE.Matrix4().compose(_v.set(x, y, z), _q, _s.set(s[0], s[1], s[2])));
}
// a thin square bar from point a to point b (a strut, a boom, a line of light)
function rod(bins, mat, a, b, th) {
  _a.set(a[0], a[1], a[2]); _b.set(b[0], b[1], b[2]); const len = _a.distanceTo(_b); if (len < 1e-5) return;
  _v.copy(_a).add(_b).multiplyScalar(0.5); _q.setFromUnitVectors(Z, _b.clone().sub(_a).normalize());
  push(bins, mat, UB, new THREE.Matrix4().compose(_v, _q, _s.set(th, th, len)));
}
function line(bins, mat, pts, th) { for (let i = 0; i < pts.length - 1; i++) rod(bins, mat, pts[i], pts[i + 1], th); }
// the bins, merged: one mesh per material, under a group that moves (their geometry is theirs, so release() lets it go)
function flush(bins, group) {
  bins.forEach((list, mat) => {
    const g = mergeGeometries(list, false); list.forEach((x) => x.dispose());
    if (!g) return;
    const m = new THREE.Mesh(g, mat); m.userData.own = true; group.add(m);
  });
}
// a grid of points P(u, v) as a surface, its front face up (+y)
function surface(P, nu, nv) {
  const pos = [], uv = [], idx = [];
  for (let i = 0; i <= nu; i++) for (let j = 0; j <= nv; j++) { const p = P(i / nu, j / nv); pos.push(p[0], p[1], p[2]); uv.push(i / nu, j / nv); }
  const ix = (i, j) => i * (nv + 1) + j;
  for (let i = 0; i < nu; i++) for (let j = 0; j < nv; j++) { const a = ix(i, j), c = ix(i + 1, j), d = ix(i + 1, j + 1), e = ix(i, j + 1); idx.push(a, e, c, c, e, d); }
  const g = new THREE.BufferGeometry();
  g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); g.setIndex(idx);
  g.computeVertexNormals();
  const ny = g.attributes.normal.getY(ix(Math.floor(nu / 2), Math.floor(nv / 2)));
  if (ny < 0) { const ia = g.index.array; for (let i = 0; i < ia.length; i += 3) { const t = ia[i + 1]; ia[i + 1] = ia[i + 2]; ia[i + 2] = t; } g.computeVertexNormals(); }
  return g;
}
// one slow clock for what turns: it runs at its own speed, x1.6 while a department works, without a jump when that changes
function clock(b, apply) {
  let last = null, ph = 0;
  b.anim.push((t) => { if (last == null) ph = t; else ph += Math.min(0.25, Math.max(0, t - last)) * (b.busy ? 1.6 : 1); last = t; apply(ph); });
}
const ring = (b, M, r, y, mat, tube) => CO.ST.put(b, CO.ST.torus(r, tube, 6, Math.max(48, Math.round(r * 46))), mat, 0, y, 0, { rx: PI / 2 });
// slits of light round a drum's wall, facing out: the hangar mouths of the seven
function slits(b, M, r, y, count, w, h, off) {
  for (let k = 0; k < count; k++) { const a = (k + (off || 0.5)) / count * TAU; CO.ST.box(b, w, h, 0.02, Math.cos(a) * (r + 0.004), y, Math.sin(a) * (r + 0.004), M.hot, { ry: PI / 2 - a }); }
}

// The sail's film: u3d.js's A.glass is one-sided and 0.12 clear, which on a square this large vanishes; this is the
// same glass, tinted and two-sided, ONE per colour (on the colour's set, in a bag of its own, where release() keeps it)
function filmMat(A) {
  if (A.stB) return A.stB.film;
  const c = A.c;
  A.stB = { film:new THREE.MeshStandardMaterial({ color: c.clone().multiplyScalar(0.45), emissive: c.clone(), emissiveIntensity: 0.28, transparent: true, opacity: 0.22, roughness: 0.15, metalness: 0.1, side: THREE.DoubleSide, depthWrite: false }) };
  return A.stB.film;
}

/* ---------------- 03 Solar Sail: four panels of light between four booms, turning round a mast of decks ---------------- */
function sail(b, n) {
  const { mats, put, box, greebles, sprite } = CO.ST;
  const A = b.A, M = mats(A), dh = 0.3, ym = 0.02 + n * dh;
  // the hub: a plated drum with a line of light round its top edge and a ring of hangar slits, a keel under it
  put(b, pcyl(0.95, 0.95, 0.24, 64), M.mid, 0, -0.12, 0);
  ring(b, M, 0.955, 0.0, M.neon, 0.03);
  ring(b, M, 0.93, -0.235, M.neonSoft, 0.016);
  slits(b, M, 0.95, -0.12, 20, 0.2, 0.05);
  put(b, pcyl(0.64, 0.64, 0.05, 40), M.dark, 0, 0.015, 0);
  put(b, plathe('sailKeel', [[0, -1.0], [0.45, -0.72], [0.88, -0.24]], 48), M.dark, 0, 0, 0);
  ring(b, M, 0.47, -0.71, M.neonSoft, 0.014);
  for (let k = 0; k < 8; k++) {   // ribs down the keel's slant, and what is bolted on it
    const a = k / 8 * TAU + PI / 8, r = 0.682, y = -0.497;
    put(b, CO.ST.pbox(0.05, 0.66, 0.05), M.mid, Math.cos(a) * r, y, Math.sin(a) * r, { ry: -a, rz: -0.72 });
  }
  const eng = CO.ST.engine(b, M, 0, -0.84, 0, 0.16, 0, 0.8); eng.rotation.x = -PI / 2;
  // the hub's top deck: blocks between the mast and the booms' roots
  greebles(b, [M.mid, M.dark, M.light, M.metal], 0, -0.9, 0.9, -0.9, 0.9, 38, (x, z) => { const r = Math.hypot(x, z); return r > 0.54 && r < 0.84; }, 303);
  // the mast: a deck a drum, a collar between with a thread of light, two rows of windows round each
  for (let f = 0; f < n; f++) {
    const yb = 0.02 + f * dh, yc = yb + (dh - 0.05) / 2;
    put(b, pcyl(0.42, 0.42, dh - 0.05, 32), f % 2 ? M.mid : M.light, 0, yc, 0);
    put(b, pcyl(0.5, 0.5, 0.05, 32), M.metal, 0, yb + dh - 0.025, 0);
    ring(b, M, 0.502, yb + dh - 0.003, M.neonSoft, 0.011);
    b.ringWins(f, 0.42, yc + 0.055, 0.065, 0.2, 0.65, 0.1);
    b.ringWins(f, 0.42, yc - 0.055, 0.065, 0.2, 0.65, 0.1);
  }
  // its crown: a domed cap, a mast, a beacon, a halo round it
  put(b, plathe('sailCap', [[0, 0], [0.42, 0], [0.36, 0.12], [0.2, 0.2], [0, 0.23]], 32), M.metal, 0, ym, 0);
  put(b, CO.ST.cyl(0.025, 0.04, 0.5, 8), M.metal, 0, ym + 0.45, 0);
  box(b, 0.3, 0.025, 0.025, 0, ym + 0.36, 0, M.metal);
  put(b, CO.ST.sphere(0.04), M.hot, 0.15, ym + 0.36, 0); put(b, CO.ST.sphere(0.04), M.hot, -0.15, ym + 0.36, 0);
  b.beacon(0, ym + 0.76, 0, 0.06);
  sprite(b, M.halo, 0, ym + 0.76, 0, 0.9);
  sprite(b, M.halo, 0, ym * 0.5, 0, 1.5 + ym * 0.5);

  // the rotor: four booms, the four sails between them, the square of light at their edge, turning as one
  const rotor = new THREE.Group(); rotor.userData.dyn = true; b.g.add(rotor);
  const bins = new Map(), yS = -0.05, Ri = 0.98, Rt = 3.2, gk = (k) => PI / 4 + k * PI / 2;
  const B = (k, r, dy) => [Math.cos(gk(k)) * r, yS + (r - Ri) * 0.07 + (dy || 0), Math.sin(gk(k)) * r];
  for (let k = 0; k < 4; k++) {
    rod(bins, M.metal, B(k, 0.88), B(k, 3.3), 0.085);                      // the boom
    rod(bins, M.dark, B(k, 0.95, -0.075), B(k, 3.25, -0.075), 0.035);      // its lower chord, laced to it
    for (let i = 0; i < 8; i++) rod(bins, M.dark, B(k, 1.0 + i * 0.29, i % 2 ? -0.075 : 0), B(k, 1.0 + (i + 1) * 0.29, i % 2 ? 0 : -0.075), 0.02);
    rod(bins, M.neonSoft, B(k, 1.0, 0.047), B(k, 3.2, 0.047), 0.02);       // a thread of light along its top
    for (let i = 0; i < 9; i++) {                                           // along it: lamps, and blocks of gear between them
      const r = 1.15 + i * 0.24;
      if (i % 3 === 1) rod(bins, M.hot, B(k, r, 0.056), B(k, r + 0.05, 0.056), 0.05);
      else rod(bins, M.metal, B(k, r, 0.062), B(k, r + 0.09 + (i % 2) * 0.04, 0.062), 0.07 + (i % 2) * 0.025);
    }
    rod(bins, M.metal, B(k, 0.84, -0.02), B(k, 1.0, -0.02), 0.17);         // its root bracket on the hub
    rod(bins, M.metal, B(k, 3.2), B(k, 3.38), 0.15);                       // its tip pod, a lamp on the end
    rod(bins, M.hot, B(k, 3.385, 0.01), B(k, 3.43, 0.01), 0.07);
    const sp = new THREE.Sprite(M.halo); const tp = B(k, 3.4, 0.02); sp.position.set(tp[0], tp[1], tp[2]); sp.scale.setScalar(0.6); rotor.add(sp);
  }
  const NU = 10, NV = 8, films = [];
  for (let k = 0; k < 4; k++) {
    // between boom k and the next: at radius r a chord from one boom to the other, billowed down 0.24 at its middle
    const P = (u, v, lift) => {
      const r = Ri + (Rt - Ri) * u, p0 = B(k, r), p1 = B(k + 1, r);
      return [p0[0] + (p1[0] - p0[0]) * v, p0[1] + (p1[1] - p0[1]) * v - 0.24 * Math.sin(PI * v) * Math.sin(PI * Math.min(1, u * 1.1)) + (lift || 0), p0[2] + (p1[2] - p0[2]) * v];
    };
    films.push(surface(P, NU, NV));
    const cross = (u, lift) => { const pts = []; for (let j = 0; j <= 8; j++) pts.push(P(u, j / 8, lift)); return pts; };
    const along = (v, lift) => { const pts = []; for (let i = 0; i <= 10; i++) pts.push(P(i / 10, v, lift)); return pts; };
    line(bins, M.neon, cross(1, 0.012), 0.034);                             // the square of light
    line(bins, M.neonSoft, cross(0.64, 0.012), 0.026);                      // two battens across the sail
    line(bins, M.neonSoft, cross(0.32, 0.012), 0.026);
    line(bins, M.neonSoft, cross(0.0, 0.012), 0.03);                        // its inner hem
    for (const v of [0.25, 0.5, 0.75]) line(bins, M.neonSoft, along(v, 0.012), 0.014);   // seams of the film
    for (const u of [0.32, 0.64]) for (const v of [0.25, 0.5, 0.75]) { const p = P(u, v, 0.02); at(bins, M.hot, UB, p[0], p[1], p[2], { s: [0.05, 0.05, 0.05] }); }
  }
  flush(bins, rotor);
  const film = new THREE.Mesh(mergeGeometries(films, false), filmMat(A)); film.userData.own = true; rotor.add(film); films.forEach((g) => g.dispose());
  clock(b, (ph) => { rotor.rotation.y = -ph * 0.08 + b.phase; });
  b.top = ym + 0.8; b.bot = -1.0; b.foot = 3.3;
}

/* ---------------- 04 Deep Array: a dish on a yoke over a turret of decks, sweeping slowly, its focus lit ---------------- */
function dish(b, n) {
  const { mats, put, box, greebles, sprite } = CO.ST;
  const A = b.A, M = mats(A), dh = 0.17, RD = 1.85, fF = 1.3, py = (r) => r * r / (4 * fF);
  // the platform: a plated drum, its edge lit and hangar mouths in it, a keel under it with one engine
  put(b, pcyl(1.75, 1.75, 0.3, 80), M.mid, 0, -0.15, 0);
  ring(b, M, 1.755, 0.0, M.neon, 0.03);
  ring(b, M, 1.72, -0.295, M.neonSoft, 0.016);
  slits(b, M, 1.75, -0.15, 28, 0.26, 0.06);
  put(b, plathe('dishKeel', [[0, -1.15], [0.35, -1.1], [1.05, -0.72], [1.68, -0.3]], 64), M.dark, 0, 0, 0);
  ring(b, M, 1.06, -0.715, M.neonSoft, 0.014);
  ring(b, M, 0.62, -0.93, M.neonSoft, 0.012);
  for (let k = 0; k < 12; k++) {   // ribs down the keel's upper slant, from (1.68, -0.3) to (1.05, -0.72)
    const a = k / 12 * TAU + PI / 12, r = 1.382, y = -0.535;
    put(b, CO.ST.pbox(0.06, 0.76, 0.06), M.mid, Math.cos(a) * r, y, Math.sin(a) * r, { ry: -a, rz: -0.983 });
  }
  CO.ST.engine(b, M, 0, -0.92, 0, 0.22, 0, 0.9).rotation.x = -PI / 2;
  // the platform's top: blocks round the turret, landing lights along its rim
  // (the dish sweeps over one stretch of the rim, 147 to 188 degrees round from +x, and at one deck its lowest edge
  // brushes the platform: that stretch is kept clear, with its own arc of light on the deck to say what it is for)
  const sweep = (x, z) => { const d = ((Math.atan2(z, x) * 180 / PI) + 360) % 360; return d > 128 && d < 208; };
  greebles(b, [M.mid, M.dark, M.light, M.metal], 0, -1.7, 1.7, -1.7, 1.7, 80, (x, z) => { const r = Math.hypot(x, z); return r > 1.04 && r < 1.62 && !(r > 1.15 && sweep(x, z)); }, 404);
  for (let k = 0; k < 24; k++) { const a = (k + 0.5) / 24 * TAU; if (!sweep(Math.cos(a), Math.sin(a))) box(b, 0.1, 0.02, 0.05, Math.cos(a) * 1.68, 0.011, Math.sin(a) * 1.68, M.hot, { ry: -a }); }
  const ka = CO.ST.key('stBarc', [1.42, 0.72]);
  put(b, CO.ST.G[ka] || (CO.ST.G[ka] = CO.ST.torus(1.42, 0.014, 5, 40, 0.72).clone().rotateX(PI / 2).rotateY(-2.57)), M.neonSoft, 0, 0.012, 0);
  for (const a of [2.57, 2.57 + 0.72]) box(b, 0.12, 0.04, 0.04, Math.cos(a) * 1.42, 0.02, Math.sin(a) * 1.42, M.hot, { ry: -a });
  // the turret: a deck a drum, narrowing upward, a collar between, a row of windows round each
  let y = 0;
  for (let f = 0; f < n; f++) {
    const r = 0.95 - 0.1 * f / Math.max(1, n - 1), yc = y + (dh - 0.03) / 2;
    put(b, pcyl(r, r, dh - 0.03, 40), f % 2 ? M.mid : M.light, 0, yc, 0);
    put(b, pcyl(r + 0.05, r + 0.05, 0.03, 40), M.metal, 0, y + dh - 0.015, 0);
    if (f % 2 === 0) ring(b, M, r + 0.052, y + dh - 0.002, M.neonSoft, 0.01);
    b.ringWins(f, r, yc, 0.06, 0.19, 0.65, 0.1);
    y += dh;
  }
  const yt = y, bt = new Map(), bd = new Map();

  // the turntable (it yaws), its yoke, and on the yoke's axle the dish (it tips): both merged into a few meshes
  const table = new THREE.Group(); table.userData.dyn = true; table.position.y = yt; b.g.add(table);
  at(bt, M.mid, pcyl(0.9, 0.9, 0.14, 56), 0, 0.07, 0);
  at(bt, M.neon, CO.ST.torus(0.905, 0.025, 6, 64), 0, 0.14, 0, { rx: PI / 2 });
  at(bt, M.neonSoft, CO.ST.torus(0.56, 0.012, 5, 56), 0, 0.142, 0, { rx: PI / 2 });
  for (let k = 0; k < 40; k++) { const a = k / 40 * TAU; at(bt, M.metal, UB, Math.cos(a) * 0.9, 0.055, Math.sin(a) * 0.9, { ry: -a, s: [0.05, 0.05, 0.09] }); }
  // its top: hatches and blocks between the arms
  const R5 = CO.ST.rnd(77);
  for (let i = 0, tries = 0; i < 16 && tries < 200; tries++) {
    const x = (R5() * 2 - 1) * 0.72, z = (R5() * 2 - 1) * 0.72, r = Math.hypot(x, z); if (r < 0.34 || r > 0.7) continue;
    const w = 0.07 + R5() * 0.12, d = 0.07 + R5() * 0.12, hh = 0.02 + R5() * R5() * 0.05;
    at(bt, i % 3 ? M.mid : M.metal, UB, x, 0.14 + hh / 2, z, { ry: R5() < 0.5 ? 0 : PI / 2, s: [w, hh, d] }); i++;
  }
  for (const s of [1, -1]) {
    at(bt, M.mid, CO.ST.pbox(0.16, 0.62, 0.34), s * 0.8, 0.14 + 0.31, 0);                     // a yoke arm
    at(bt, M.metal, pcyl(0.12, 0.12, 0.12, 20), s * 0.86, 0.76, 0, { rz: PI / 2 });            // the bearing on its outside
    at(bt, M.metal, UB, s * 0.8, 0.14 + 0.625, 0, { s: [0.2, 0.025, 0.38] });
    at(bt, M.hot, UB, s * 0.885, 0.42, 0.09, { s: [0.02, 0.26, 0.03] }); at(bt, M.hot, UB, s * 0.885, 0.42, -0.09, { s: [0.02, 0.26, 0.03] });
    for (const z of [-0.1, 0.1]) at(bt, M.mid, UB, s * 0.8, 0.14 + 0.66, z, { s: [0.08, 0.04, 0.08] });
    rod(bt, M.neonSoft, [s * 0.718, 0.2, 0.17], [s * 0.718, 0.68, 0.17], 0.014); rod(bt, M.neonSoft, [s * 0.718, 0.2, -0.17], [s * 0.718, 0.68, -0.17], 0.014);
  }
  rod(bt, M.metal, [-0.88, 0.76, 0], [0.88, 0.76, 0], 0.1);                                     // the elevation axle
  flush(bt, table);

  const dishG = new THREE.Group(); dishG.userData.dyn = true; dishG.position.y = 0.76; table.add(dishG);
  // the bowl: a paraboloid y = r^2 / 4f from r 0.3 to 1.85; its inside pale, listed rim to centre so it faces up; its back steel, 0.05 under
  const prof = []; for (let i = 0; i <= 12; i++) { const r = 0.3 + (RD - 0.3) * i / 12; prof.push([r, py(r)]); }
  at(bd, M.light, plathe('dishIn', prof.slice().reverse(), 72, 1.4), 0, 0, 0);
  at(bd, M.mid, plathe('dishBack', prof, 72, 1.4), 0, -0.05, 0);
  at(bd, M.metal, pcyl(0.32, 0.32, 0.18, 28), 0, -0.02, 0);
  at(bd, M.metal, CO.ST.torus(RD, 0.055, 8, 96), 0, py(RD) - 0.02, 0, { rx: PI / 2 });
  at(bd, M.neon, CO.ST.torus(RD + 0.065, 0.028, 6, 96), 0, py(RD) - 0.02, 0, { rx: PI / 2 });
  for (let k = 0; k < 24; k++) { const a = (k + 0.5) / 24 * TAU; at(bd, M.hot, UB, Math.cos(a) * (RD + 0.07), py(RD) - 0.02, Math.sin(a) * (RD + 0.07), { ry: -a, s: [0.07, 0.07, 0.07] }); }
  // inside: ten ribs and two circles of light, and the panels' own seams in dark
  for (let k = 0; k < 10; k++) {
    const g = k / 10 * TAU, pts = [];
    for (let i = 0; i <= 8; i++) { const r = 0.4 + (RD - 0.5) * i / 8; pts.push([Math.cos(g) * r, py(r) + 0.022, Math.sin(g) * r]); }
    line(bd, M.neonSoft, pts, 0.026);
    // under the bowl: a truss rib from the hub to the rim, shallow (the spec's own bowl, at its lowest tilt, el 0.81,
    // dips about 0.04 into the turntable's rim, hidden behind the yoke; nothing of ours hangs lower than that, so
    // the ribs stay thin), and between the ribs a thread of light flush with the back: the dish is seen from
    // behind as often as from the front
    const back = [], lit = [], g2 = g + PI / 10;
    for (let i = 0; i <= 8; i++) { const r = 0.5 + (RD - 0.55) * i / 8; back.push([Math.cos(g) * r, py(r) - 0.068, Math.sin(g) * r]); lit.push([Math.cos(g2) * r, py(r) - 0.058, Math.sin(g2) * r]); }
    line(bd, M.dark, back, 0.036);
    line(bd, M.neonSoft, lit, 0.014);
  }
  for (const r of [1.2, 1.72]) at(bd, M.neonSoft, CO.ST.torus(r, 0.012, 5, 72), 0, py(r) - 0.058, 0, { rx: PI / 2 });
  for (let k = 0; k < 10; k += 2) { const a = k / 10 * TAU + PI / 10; for (const r of [1.2, 1.72]) at(bd, M.hot, UB, Math.cos(a) * r, py(r) - 0.062, Math.sin(a) * r, { s: [0.05, 0.05, 0.05] }); }
  for (let k = 0; k < 8; k++) { const a = (k + 0.5) / 8 * TAU; at(bd, M.hot, UB, Math.cos(a) * 0.36, -0.08, Math.sin(a) * 0.36, { ry: -a, s: [0.04, 0.04, 0.07] }); }
  for (const r of [1.15, 1.7]) at(bd, M.neonSoft, CO.ST.torus(r, 0.013, 5, 72), 0, py(r) + 0.022, 0, { rx: PI / 2 });
  for (let k = 0; k < 10; k++) { const a = (k + 0.5) / 10 * TAU; for (const r of [1.15, 1.7]) at(bd, M.hot, UB, Math.cos(a) * r, py(r) + 0.03, Math.sin(a) * r, { s: [0.05, 0.05, 0.05] }); }
  // the feed: three struts from the rim to the focus on the axis, a horn, the focus itself in light
  const F = [0, fF, 0];
  for (const g of [PI / 2, PI / 2 + TAU / 3, PI / 2 + 2 * TAU / 3]) rod(bd, M.metal, [Math.cos(g) * RD, py(RD), Math.sin(g) * RD], F, 0.04);
  // (the horn's mouth faces the bowl and the focus burns just under it: a horn round the focus hid the light inside it)
  at(bd, M.metal, plathe('dishHorn', [[0.07, 0], [0.2, 0], [0.2, 0.04], [0.1, 0.13], [0.06, 0.25], [0, 0.25]], 20), 0, fF + 0.03, 0);
  const kf = CO.ST.key('stBfocus', [0.105]);
  at(bd, M.hot, CO.ST.G[kf] || (CO.ST.G[kf] = new THREE.SphereGeometry(0.105, 16, 10)), 0, fF - 0.03, 0);
  flush(bd, dishG);
  const halo = new THREE.Sprite(M.halo); halo.position.set(0, fF - 0.03, 0); halo.scale.setScalar(1.9); dishG.add(halo);
  clock(b, (ph) => { table.rotation.y = -1.35 + 0.35 * Math.sin(0.09 * ph + b.phase); dishG.rotation.x = 0.75 + 0.06 * Math.sin(0.05 * ph); });
  table.rotation.y = -1.35 + 0.35 * Math.sin(b.phase); dishG.rotation.x = 0.75;
  // the top of the dish's rim at its mean tilt, as the spec's table has it
  const el = 0.75; b.top = yt + 0.76 + py(RD) * Math.cos(el) + RD * Math.sin(el) + 0.07; b.bot = -1.15; b.foot = 2.3;
}

/* ---------------- into u3d.js's table ---------------- */
function install() {
  const U = CO.U3;
  if (!U || !U.ok || !U.SKIN || !CO.ST || U.skinsB === '1') return;
  U.SKIN.sail = sail; U.SKIN.dish = dish;
  U.skinsB = '1';
  window.dispatchEvent(new Event('co3d-skins'));
}
if (CO.U3 && CO.ST) install(); else window.addEventListener('co3d', install, { once: true });
