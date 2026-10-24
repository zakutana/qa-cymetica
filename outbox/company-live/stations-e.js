/* Stations 09 and 10 of the ten newer ones, built the way the seven are (stations.js): the Nautilus Shell and the Halo
 * Vortex. The design is outbox/company-skins/SPEC.md, sections 09 and 10; the parts, the materials and the finish are
 * stations.js's own (CO.ST): a plated hull in steel and slate, the company's colour only in lights, a deck's windows lit
 * while its department works (b.win, deck f), small structure and surface detail, a crown, a halo. Nothing pulses.
 *
 * A module of its own, run after u3d.js and stations.js: it puts its builders into u3d.js's table (CO.U3.SKIN) and says so
 * with the event co3d-skins; CO.skinBuilt then turns true and Settings draws the real 3D station instead of the flat
 * preview.
 *
 * What differs from the seven: the Vortex's rings turn and bob, so their windows move with them. b.finish() bakes every
 * window into one instanced mesh whose matrices never change, so the Vortex rewrites the matrices of its own windows each
 * frame (b.wins exists once the station is finished; the first call that finds it does the work). */
import * as THREE from 'three/webgpu';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

const CO = window.CO;
const TAU = Math.PI * 2;
const GE = {};   // this module's own geometries, made once

/* ---------------- small helpers: parts moved into place and merged by material ---------------- */
const M4 = new THREE.Matrix4(), QQ = new THREE.Quaternion(), EE = new THREE.Euler(), PP = new THREE.Vector3(), S1 = new THREE.Vector3(1, 1, 1);
// a fresh copy of a geometry, turned and moved
function placed(g, x, y, z, rx, ry, rz) {
  const c = g.clone(); EE.set(rx || 0, ry || 0, rz || 0, 'YXZ'); QQ.setFromEuler(EE);
  M4.compose(PP.set(x, y, z), QQ, S1); c.applyMatrix4(M4); return c;
}
// what mergeGeometries wants of every part: the same attributes, no index
function flat(g) {
  const n = g.index ? g.toNonIndexed() : g;
  Object.keys(n.attributes).forEach((k) => { if (k !== 'position' && k !== 'normal' && k !== 'uv') n.deleteAttribute(k); });
  return n;
}
function joined(list) { return list.length ? mergeGeometries(list.map(flat), false) : null; }
function tubeAlong(fn, t0, t1, steps, rad) {
  const pts = [];
  for (let i = 0; i <= steps; i++) { const t = t0 + (t1 - t0) * i / steps; pts.push(new THREE.Vector3(...fn(t))); }
  return new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts), steps * 2, rad, 5, false);
}

/* ================= 09 Nautilus Shell: chambers on a two-turn log spiral round a glass heart ================= */
// A chamber a department, the six inside it sealed: the shell grows one chamber with every department. theta 0..12.6 (two
// turns), inner wall 0.384 e^(0.12 t), outer wall 0.64 e^(0.12 t), height 0.2 e^(0.09 t); a groove between whorls.
const NA = { TH: 12.6, GAP: 0.04, BEV: 0.02, MOUTH: -3 * Math.PI / 4 };
const nIn = (t) => 0.384 * Math.exp(0.12 * t), nOut = (t) => 0.64 * Math.exp(0.12 * t), nH = (t) => 0.2 * Math.exp(0.09 * t);
// the plan angle at theta: the mouth (theta = 12.6) faces the camera's side at first; world x = r cos a, z = -r sin a
const nAng = (t) => NA.MOUTH + (t - NA.TH);
const nXZ = (r, t) => { const a = nAng(t); return [r * Math.cos(a), -r * Math.sin(a)]; };
// the outline of the whole footprint, pulled in by d: one turn of the outer wall, closed by the radial edge at the mouth
function nOutline(d) {
  const sh = new THREE.Shape();
  for (let s = 0; s <= 72; s++) { const t = NA.TH - TAU + TAU * s / 72, a = nAng(t), r = nOut(t) - d; sh[s ? 'lineTo' : 'moveTo'](r * Math.cos(a), r * Math.sin(a)); }
  sh.closePath(); return sh;
}

function nautilus(b, n) {
  const { mats, put, box, greebles, sprite, slab, cyl, torus, sphere, pbox, key, engine } = CO.ST;
  const A = b.A, M = mats(A), R = b.R, K = 6 + n, { TH, GAP, BEV } = NA, tilt = Math.atan(0.12);
  const L = { neon: [], soft: [], hot: [], dark: [], mid: [], metal: [] };
  const chambers = [];

  for (let i = 0; i < K; i++) {
    const t0 = i * TH / K + GAP / 2, t1 = (i + 1) * TH / K - GAP / 2, tm = (t0 + t1) / 2, h = nH(tm), f = i - (K - n);
    // the plan outline, pulled in by the bevel so the chamfered slab ends where the spiral says
    const e0 = t0 + BEV / ((nIn(t0) + nOut(t0)) / 2), e1 = t1 - BEV / ((nIn(t1) + nOut(t1)) / 2), steps = Math.max(3, Math.ceil((t1 - t0) / 0.12));
    const sh = new THREE.Shape(), P = (r, t) => { const a = nAng(t); return [r * Math.cos(a), r * Math.sin(a)]; };
    for (let s = 0; s <= steps; s++) { const t = e0 + (e1 - e0) * s / steps, p = P(nIn(t) + BEV, t); sh[s ? 'lineTo' : 'moveTo'](p[0], p[1]); }
    for (let s = steps; s >= 0; s--) { const t = e0 + (e1 - e0) * s / steps, p = P(nOut(t) - BEV, t); sh.lineTo(p[0], p[1]); }
    sh.closePath();
    // sealed chambers in dark plating, the departments' in pale and steel by turns, as the seven's decks
    put(b, slab(key('eNc', [K, i]), sh, h, BEV), f < 0 ? M.dark : f % 2 ? M.mid : M.light, 0, 0, 0);
    chambers.push({ i, f, t0, t1, tm, h });

    // a line of light across the top of the septum that starts the chamber
    const rc = (nIn(t0) + nOut(t0)) / 2, ta = t0 + 0.06 / rc, [sx, sz] = nXZ(rc, ta);
    L.neon.push(placed(pbox(0.028, 0.026, nOut(ta) - nIn(ta) - 0.1), sx, h + 0.012, sz, 0, Math.PI / 2 + nAng(ta), 0));
    // the outer top edge (a department's brighter than a sealed one's), the inner top edge softer
    const sub = Math.max(4, Math.ceil((t1 - t0) / 0.1));
    L[f >= 0 ? 'neon' : 'soft'].push(tubeAlong((t) => { const [x, z] = nXZ(nOut(t) - 0.035, t); return [x, h + 0.012, z]; }, e0, e1, sub, f >= 0 ? 0.012 : 0.011));
    L.soft.push(tubeAlong((t) => { const [x, z] = nXZ(nIn(t) + 0.035, t); return [x, h + 0.012, z]; }, e0, e1, sub, 0.009));

    if (f >= 0) {
      // a trench of light along the foot of the outer wall
      L.soft.push(tubeAlong((t) => { const [x, z] = nXZ(nOut(t) + 0.004, t); return [x, 0.065, z]; }, e0, e1, sub, 0.011));
      // windows on the outer wall (two rows where the chamber is tall enough), and a row on the inner wall, deck f
      const rows = h > 0.42 ? 2 : 1, m = Math.max(3, Math.floor(nOut(tm) * (t1 - t0) / 0.21));
      for (let r = 0; r < rows; r++) {
        const yy = rows === 2 ? h * (0.28 + r * 0.34) : h * 0.5;
        for (let j = 0; j < m; j++) {
          const t = t0 + (t1 - t0) * (j + 0.5) / m, a = nAng(t), rr = nOut(t) + 0.012;
          b.win(rr * Math.cos(a), yy, -rr * Math.sin(a), Math.PI / 2 + a - tilt, 0.15, Math.min(0.07, h * 0.17), f, R() < 0.6);
        }
      }
      const mi = Math.max(3, Math.floor(nIn(tm) * (t1 - t0) / 0.27));
      for (let j = 0; j < mi; j++) {
        const t = t0 + (t1 - t0) * (j + 0.5) / mi, a = nAng(t), rr = nIn(t) - 0.012;
        b.win(rr * Math.cos(a), h * 0.5, -rr * Math.sin(a), Math.PI / 2 + a - tilt + Math.PI, 0.13, Math.min(0.06, h * 0.15), f, R() < 0.6);
      }
      // a rib up the outer wall where the chamber starts
      const tr = t0 + 0.07 / nOut(t0), [rx, rz] = nXZ(nOut(tr), tr);
      L.dark.push(placed(pbox(0.06, h + 0.02, 0.09), rx, h / 2, rz, 0, Math.PI / 2 + nAng(tr), 0));
      // a short mast with a lamp on every other department's deck, near the rim
      if (f % 2 === 0) {
        const [mx, mz] = nXZ(nOut(tm) - 0.14, tm);
        L.metal.push(placed(cyl(0.012, 0.016, 0.26, 6), mx, h + 0.13, mz));
        L.hot.push(placed(GE.dot || (GE.dot = new THREE.SphereGeometry(0.034, 8, 6)), mx, h + 0.27, mz));
      }
      // blocks of machinery over the deck, clear of the walls
      const wid = nOut(tm) - nIn(tm);
      if (wid > 0.6) {
        let x0 = 9, x1 = -9, z0 = 9, z1 = -9;
        for (let s = 0; s <= 6; s++) for (const r of [nIn(t0 + (t1 - t0) * s / 6), nOut(t0 + (t1 - t0) * s / 6)]) {
          const [x, z] = nXZ(r, t0 + (t1 - t0) * s / 6); x0 = Math.min(x0, x); x1 = Math.max(x1, x); z0 = Math.min(z0, z); z1 = Math.max(z1, z);
        }
        const inside = (x, z) => {
          const a = Math.atan2(-z, x), r = Math.hypot(x, z); let t = a + 3 * Math.PI / 4 + TH; t -= TAU * Math.round((t - tm) / TAU);
          return t > t0 + 0.07 && t < t1 - 0.07 && r > nIn(t) + 0.2 && r < nOut(t) - 0.2;
        };
        greebles(b, [M.mid, M.light, M.dark], h, x0, x1, z0, z1, Math.min(22, Math.round(wid * nOut(tm) * (t1 - t0) * 7)), inside, 100 + i);
      }
    } else if (nOut(tm) - nIn(tm) > 0.3) {
      // a sealed chamber's hatch: a disc with a ring of light
      const rm = (nIn(tm) + nOut(tm)) / 2, [hx, hz] = nXZ(rm, tm), hr = Math.min(0.13, (nOut(tm) - nIn(tm)) * 0.26);
      L.dark.push(placed(cyl(hr, hr * 1.05, 0.03, 16), hx, h + 0.015, hz));
      L.soft.push(placed(torus(hr * 0.86, 0.01, 5, 20), hx, h + 0.033, hz, Math.PI / 2));
    }
  }

  // the floor under it all and the hull below it: tiers following the spiral, narrowing downward, a trench of light
  // along the first
  put(b, slab('eNp0', nOutline(0.05), 0.1, 0.02), M.dark, 0, -0.1, 0);
  put(b, slab('eNp1', nOutline(0.3), 0.2, 0.02), M.mid, 0, -0.3, 0);
  put(b, slab('eNp2', nOutline(0.6), 0.16, 0.02), M.dark, 0, -0.46, 0);
  put(b, slab('eNp3', nOutline(0.9), 0.14, 0.02), M.mid, 0, -0.6, 0);
  L.soft.push(tubeAlong((t) => { const [x, z] = nXZ(nOut(t) - 0.3 + 0.015, t); return [x, -0.2, z]; }, NA.TH - TAU, NA.TH, 90, 0.012));
  // the groove: a line of light along it, from the second whorl to the mouth, and walkways across it
  L.neon.push(tubeAlong((t) => { const [x, z] = nXZ((nIn(t) + nOut(t - TAU)) / 2, t); return [x, 0.025, z]; }, TAU + 0.05, TH - 0.03, 100, 0.02));
  chambers.forEach((c) => {
    if (c.tm < TAU + 0.3) return;
    const rI = nOut(c.tm - TAU), rO = nIn(c.tm), [bx, bz] = nXZ((rI + rO) / 2, c.tm);
    L.metal.push(placed(pbox(0.07, 0.04, rO - rI + 0.06), bx, 0.07, bz, 0, Math.PI / 2 + nAng(c.tm), 0));
    L.hot.push(placed(pbox(0.03, 0.02, 0.03), bx, 0.1, bz));
  });
  put(b, cyl(0.7, 0.45, 0.1, 32), M.dark, 0, -0.65, 0);

  // the mouth: the last chamber's end, a glass wall on a lit hangar, framed in light
  const last = chambers[K - 1], tE = last.t1, aE = nAng(tE), hM = last.h, rcM = (nIn(tE) + nOut(tE)) / 2, wM = nOut(tE) - nIn(tE);
  const nx = -Math.sin(aE), nz = -Math.cos(aE), ex = Math.cos(aE), ez = -Math.sin(aE), ry = aE + Math.PI;
  const at = (off, u, y) => [rcM * ex + u * ex + nx * off, y, -rcM * Math.sin(aE) + u * ez + nz * off];
  box(b, wM * 0.9, hM * 0.84, 0.012, ...at(0.014, 0, hM / 2), M.glass, { ry });
  for (let k = -2; k <= 2; k++) box(b, 0.012, hM * 0.84, 0.012, ...at(0.022, k * wM * 0.2, hM / 2), M.neonSoft, { ry });
  put(b, new THREE.PlaneGeometry(wM * 0.94, hM * 0.92), A.glass, ...at(0.032, 0, hM / 2), { ry });
  box(b, wM * 0.98, 0.03, 0.03, ...at(0.03, 0, 0.03), M.neon, { ry });
  box(b, wM * 0.98, 0.03, 0.03, ...at(0.03, 0, hM - 0.02), M.neon, { ry });
  for (const s of [1, -1]) box(b, 0.03, hM, 0.03, ...at(0.03, s * wM * 0.49, hM / 2), M.neon, { ry });
  sprite(b, M.halo, ...at(0.3, 0, hM * 0.5), 1.1);

  // the heart: a glass sphere on a cradle, a bright core in it, its halo; the mast over it with its beacon
  put(b, cyl(0.2, 0.3, 0.1, 24), M.dark, 0, 0.05, 0);
  put(b, torus(0.31, 0.025, 6, 40), M.metal, 0, 0.22, 0, { rx: Math.PI / 2 });
  put(b, sphere(0.3), A.glass, 0, 0.22, 0);
  put(b, sphere(0.13), A.glow, 0, 0.22, 0);
  sprite(b, M.halo, 0, 0.22, 0, 1.6);
  for (let k = 0; k < 6; k++) { const a = k / 6 * TAU; box(b, 0.04, 0.02, 0.04, Math.cos(a) * 0.33, 0.13, Math.sin(a) * 0.33, M.hot); }
  put(b, cyl(0.02, 0.03, 0.93, 8), M.metal, 0, 0.99, 0);
  put(b, cyl(0.06, 0.06, 0.05, 12), M.mid, 0, 0.78, 0);
  put(b, cyl(0.12, 0.12, 0.02, 20), M.mid, 0, 1.0, 0);
  put(b, torus(0.12, 0.008, 5, 24), M.neonSoft, 0, 1.012, 0, { rx: Math.PI / 2 });
  put(b, cyl(0.06, 0.06, 0.05, 12), M.mid, 0, 1.2, 0);
  box(b, 0.4, 0.02, 0.02, 0, 1.24, 0, M.metal);
  for (const s of [1, -1]) put(b, new THREE.SphereGeometry(0.03, 8, 6), M.hot, s * 0.2, 1.24, 0);
  put(b, cyl(0.005, 0.02, 0.1, 6), M.metal, 0, 1.5, 0);
  b.beacon(0, 1.56, 0, 0.055);
  sprite(b, M.halo, 0, 1.56, 0, 0.8);

  // the keel's engine, burning down, nothing streaming out of it
  engine(b, M, 0, -0.62, 0, 0.2, 0, 1.0).rotation.x = -Math.PI / 2;

  // all the small lines and blocks, merged by material
  [['neon', M.neon], ['soft', M.neonSoft], ['hot', M.hot], ['dark', M.dark], ['mid', M.mid], ['metal', M.metal]].forEach(([k, mat]) => {
    const g = joined(L[k]); if (g) { const m = new THREE.Mesh(g, mat); m.userData.own = true; b.g.add(m); }
  });

  // three lights run out along the outer rim, heart to mouth, each starting again at the heart
  const bead = GE.bead || (GE.bead = new THREE.SphereGeometry(0.055, 12, 8)), runs = [];
  for (let k = 0; k < 3; k++) {
    const g = new THREE.Group(); g.userData.dyn = true; b.g.add(g);
    g.add(new THREE.Mesh(bead, M.hot));
    const sp = new THREE.Sprite(M.halo); sp.scale.setScalar(0.6); g.add(sp);
    runs.push({ g, th: k * TH / 3 });
  }
  let last0 = null;
  b.anim.push((t) => {
    const dt = last0 == null ? 0 : Math.min(0.25, Math.max(0, t - last0)); last0 = t;
    runs.forEach((r) => {
      r.th = (r.th + 0.35 * (b.busy ? 1.6 : 1) * dt) % TH;
      const [x, z] = nXZ(nOut(r.th) + 0.02, r.th), fade = Math.min(1, r.th / 0.5, (TH - r.th) / 0.5);
      r.g.position.set(x, nH(r.th) + 0.1, z); r.g.scale.setScalar(Math.max(0.001, fade));
    });
  });
  b.top = 1.75; b.bot = -0.85; b.foot = 2.95;
}

/* ================= 10 Halo Vortex: flat rings one above another round a column of light ================= */
// A ring's body, its panels and clamps, and its lines of light, made once for a radius: the Vortex's rings turn and bob,
// so each is a group of its own (one mesh of three materials: steel top, slate walls, soft light), never baked.
function ringGeo(ri, ro) {
  const k = 'vr' + ri.toFixed(3);
  if (GE[k]) return GE[k];
  const { pbox } = CO.ST, hh = 0.055, c = 0.012, rc = (ri + ro) / 2, seg = Math.max(48, Math.min(96, Math.round(ro * 30)));
  // a profile lathed one segment at a time (a face of its own, so each keeps its own shading and none is wasted on a
  // corner), the plating's tiles kept to size
  const tiles = Math.max(2, Math.round(TAU * ro / 0.9));
  const lathe = (raw) => {
    const out = []; let v = 0;
    for (let j = 0; j + 1 < raw.length; j++) {
      const p = raw[j], q = raw[j + 1], len = Math.hypot(q[0] - p[0], q[1] - p[1]) / 0.9;
      const g = new THREE.LatheGeometry([new THREE.Vector2(p[0], p[1]), new THREE.Vector2(q[0], q[1])], seg), uv = g.attributes.uv;
      for (let i = 0; i <= seg; i++) { uv.setXY(i * 2, i / seg * tiles, v); uv.setXY(i * 2 + 1, i / seg * tiles, v + len); }
      v += len; out.push(g);
    }
    return out;
  };
  // two materials on one mesh: the top in steel, the walls and underside in slate (a deck's windows read on the dark)
  const topL = lathe([[ro, hh - c], [ro - c, hh], [ri + c, hh], [ri, hh - c]]);
  const wallL = [].concat(lathe([[ro, -hh + c], [ro, hh - c]]), lathe([[ri, hh - c], [ri, -hh + c]]), lathe([[ri, -hh + c], [ri + c, -hh], [ro - c, -hh], [ro, -hh + c]]));
  const lamp = [];
  // raised panels along the top, clamps on the outer wall between the windows, the two markers on opposite sides
  const N = Math.max(8, Math.round(TAU * rc / 0.5)), m = Math.max(6, Math.round(TAU * ro / 0.26));
  for (let q = 0; q < N; q++) {
    const t = (q + 0.5) / N * TAU; if (Math.abs(Math.sin(t)) * rc < 0.24) continue;   // (the markers stand at t = 0 and pi)
    topL.push(placed(pbox(TAU * rc / N * 0.72, 0.022, 0.11), rc * Math.cos(t), hh + 0.011, rc * Math.sin(t), 0, Math.PI / 2 - t, 0));
  }
  for (let j = 0; j < m; j += 3) { const t = j / m * TAU; wallL.push(placed(pbox(0.045, 0.125, 0.045), (ro + 0.008) * Math.cos(t), 0, (ro + 0.008) * Math.sin(t), 0, Math.PI / 2 - t, 0)); }
  for (const t of [0, Math.PI]) {
    topL.push(placed(pbox(0.14, 0.08, 0.28), rc * Math.cos(t), hh + 0.04, rc * Math.sin(t), 0, Math.PI / 2 - t, 0));
    lamp.push(placed(pbox(0.1, 0.03, 0.12), rc * Math.cos(t), hh + 0.09, rc * Math.sin(t), 0, Math.PI / 2 - t, 0));
  }
  // the lines of light along the top edges, the outer one brighter (soft light, thin tubes: on rings this thin the bloom
  // round a bright line buries the plating)
  lamp.push(placed(new THREE.TorusGeometry(ro - 0.01, 0.013, 5, seg), 0, hh, 0, Math.PI / 2));
  lamp.push(placed(new THREE.TorusGeometry(ri + 0.01, 0.007, 5, Math.max(40, Math.round(seg * ri / ro))), 0, hh, 0, Math.PI / 2));
  return (GE[k] = { hull: mergeGeometries([joined(topL), joined(wallL), joined(lamp)], true), m });
}

function vortex(b, n) {
  const { mats, put, box, sprite, cyl, torus, sphere, engine, scaleUV } = CO.ST;
  const A = b.A, M = mats(A), K = Math.max(4, n), dh = Math.min(0.42, 2.15 / (K - 1)), top = 0.15 + (K - 1) * dh, R = b.R;
  const rings = [];
  for (let k = 0; k < K; k++) {
    const ri = 1.0 + 1.8 * k / (K - 1), ro = ri + 0.2, y0 = 0.15 + k * dh, geo = ringGeo(ri, ro), g = new THREE.Group();
    g.userData.dyn = true; g.position.y = y0; b.g.add(g);
    g.add(new THREE.Mesh(geo.hull, [M.mid, M.dark, M.neonSoft]));
    // a deck's windows round the outer wall and the inner one (rings past n carry none)
    const i0 = b.w.length;
    if (k < n) {
      for (let j = 0; j < geo.m; j++) {
        const t = (j + 0.5) / geo.m * TAU;
        b.win(Math.cos(t) * (ro + 0.014), y0, Math.sin(t) * (ro + 0.014), Math.PI / 2 - t, 0.15, 0.042, k, R() < 0.38);
      }
      const mi = Math.max(6, Math.round(TAU * ri / 0.3));
      for (let j = 0; j < mi; j++) {
        const t = (j + 0.5) / mi * TAU;
        b.win(Math.cos(t) * (ri - 0.014), y0, Math.sin(t) * (ri - 0.014), Math.PI / 2 - t + Math.PI, 0.12, 0.04, k, R() < 0.25);
      }
    }
    rings.push({ g, k, y0, i0, i1: b.w.length, phi: k * 0.9, dir: k % 2 ? -1 : 1, spd: 0.22 - 0.015 * k });
  }

  // the column of light: glass round a core, collars at both ends, rings of light along it, a lamp at its top
  const yc = top + 0.45, len = yc + 0.05, mid = (yc - 0.05) / 2;
  put(b, cyl(0.2, 0.2, len, 32, true), A.glass, 0, mid, 0);
  put(b, cyl(0.15, 0.15, len, 24, true), A.beam, 0, mid, 0);
  put(b, cyl(0.06, 0.06, len, 16), A.glow, 0, mid, 0);
  for (const y of [-0.05, yc]) {
    put(b, cyl(0.28, 0.28, 0.14, 32), M.mid, 0, y, 0);
    put(b, torus(0.285, 0.016, 6, 48), M.neon, 0, y + 0.075, 0, { rx: Math.PI / 2 });
    put(b, cyl(0.31, 0.31, 0.03, 32), M.metal, 0, y + (y < 0 ? -0.085 : 0.085), 0);   // a flange on the outer side of each
  }
  for (let q = 1; q <= 3; q++) {
    const y = -0.05 + (yc + 0.05) * q / 4;
    put(b, torus(0.205, 0.012, 6, 40), M.neonSoft, 0, y, 0, { rx: Math.PI / 2 });
    if (q === 2) sprite(b, M.halo, 0, y, 0, 1.0);   // (one halo mid-column: three of them lit the whole stack)
  }
  put(b, new THREE.SphereGeometry(0.085, 14, 10), M.hot, 0, yc + 0.13, 0);
  sprite(b, M.halo, 0, yc + 0.13, 0, 1.3);
  put(b, cyl(0.012, 0.024, 0.14, 6), M.metal, 0, yc + 0.24, 0);
  b.beacon(0, yc + 0.3, 0, 0.045);
  sprite(b, M.halo, 0, yc + 0.3, 0, 0.6);

  // the emitter under it: a lathed hull in two tones, a ring of light round it, fins, a lens under the column, an engine
  const emit = (pts, mat) => {
    const g = new THREE.LatheGeometry(pts.map((p) => new THREE.Vector2(p[0], p[1])), 48); scaleUV(g, 3);
    return put(b, g, mat, 0, 0, 0);
  };
  emit([[0.0001, -0.95], [0.26, -0.88], [0.56, -0.5], [0.62, -0.32]], M.dark);
  emit([[0.62, -0.32], [0.36, -0.16], [0.22, -0.06]], M.mid);
  put(b, torus(0.6, 0.026, 6, 64), M.neon, 0, -0.4, 0, { rx: Math.PI / 2 });
  put(b, torus(0.37, 0.014, 6, 48), M.neonSoft, 0, -0.16, 0, { rx: Math.PI / 2 });
  put(b, cyl(0.21, 0.21, 0.03, 24), M.core, 0, -0.04, 0);
  for (let q = 0; q < 6; q++) {
    const a = q / 6 * TAU + 0.26, r = 0.5;
    box(b, 0.05, 0.3, 0.16, Math.cos(a) * r, -0.52, Math.sin(a) * r, M.metal, { ry: Math.PI / 2 - a });
    box(b, 0.03, 0.03, 0.03, Math.cos(a) * (r + 0.1), -0.4, Math.sin(a) * (r + 0.1), M.hot);
  }
  engine(b, M, 0, -0.74, 0, 0.18, 0, 1.0).rotation.x = -Math.PI / 2;

  // the rings turn (alternate ones the other way) and bob, a slow wave up the stack; their windows go with them
  let last = null;
  b.anim.push((t) => {
    const dt = last == null ? 0 : Math.min(0.25, Math.max(0, t - last)); last = t;
    const a = b.wins ? b.wins.instanceMatrix.array : null, sp = b.busy ? 1.6 : 1;
    rings.forEach((r) => {
      r.phi += r.dir * r.spd * sp * dt;
      const bob = 0.035 * Math.sin(0.8 * t + 0.7 * r.k);
      r.g.rotation.y = r.phi; r.g.position.y = r.y0 + bob;
      if (!a) return;
      const cp = Math.cos(r.phi), sp2 = Math.sin(r.phi);
      for (let i = r.i0; i < r.i1; i++) {
        const w = b.w[i], ang = w.ry + r.phi, c = Math.cos(ang), s = Math.sin(ang), o = i * 16;
        a[o] = c * w.w; a[o + 1] = 0; a[o + 2] = -s * w.w; a[o + 3] = 0;
        a[o + 4] = 0; a[o + 5] = w.h; a[o + 6] = 0; a[o + 7] = 0;
        a[o + 8] = s; a[o + 9] = 0; a[o + 10] = c; a[o + 11] = 0;
        a[o + 12] = w.x * cp + w.z * sp2; a[o + 13] = w.y + bob; a[o + 14] = -w.x * sp2 + w.z * cp; a[o + 15] = 1;
      }
    });
    if (a) b.wins.instanceMatrix.needsUpdate = true;
  });
  b.top = yc + 0.34; b.bot = -0.95; b.foot = 3.05;
}

/* ---------------- into u3d.js's table ---------------- */
function install() {
  const U = CO.U3;
  if (!U || !U.ok || !U.SKIN || !CO.ST || U.skinsE === '1') return;
  U.SKIN.nautilus = nautilus; U.SKIN.vortex = vortex;
  U.skinsE = '1';
  window.dispatchEvent(new Event('co3d-skins'));
}
if (CO.U3 && CO.ST) install(); else window.addEventListener('co3d', install, { once: true });
