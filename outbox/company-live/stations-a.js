/* Two of the ten newer stations, built the way the seven are (the operator, 2026-10-24: "ty spodni modely sou jakoby
 * udelane v jinem stylu ... predelat vsechny ty spodni modely na zpusob vrchnich ... at to udelaji stejne a mame jen
 * jeden zpusob"): Armillary Core (three gimbal rings turning round a glass capsule of decks) and Helix Spire (square
 * glass floors, each turned a little on the one below). The design is outbox/company-skins/SPEC.md, sections 01 and 02;
 * the parts, the materials and the finish are stations.js's own, through CO.ST: a plated hull in slate and steel, the
 * company's colour only in lights (neon lines, hot dots, halos, beacons), a deck's windows lit while its department
 * works (b.win), surface detail, a crown. What moves, moves slowly, and nothing pulses.
 *
 * A module of its own, run after stations.js: it puts its builders into u3d.js's table (CO.U3.SKIN) and says so with
 * the event co3d-skins, as stations.js does; CO.skinBuilt then turns true and Settings draws the real 3D station.
 *
 * Where it differs from SPEC.md, and why: the rings' tubes are 0.10 / 0.084 / 0.07 (the spec's 0.075 / 0.062 / 0.052 read
 * as wire at map distance) and b.top / bot / foot follow the outer ring's measured reach; the spine is a rod of light through
 * both caps (the spec's, inside the glass, hid behind the decks); the Helix's beacon stands at H + 0.91 so its sphere keeps
 * under top <= 4.01. Added for the seven's density: deck floors, ribs, clamps, modules and hubs (Armillary); a plinth with
 * hangar mouths, docked craft and a keel engine, and a lit slab at each deck's foot (Helix). */
import * as THREE from 'three/webgpu';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

const CO = window.CO;
const PI = Math.PI;
const GA = {};                                  // geometries made once
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const fx = (v) => (+v).toFixed(3);

/* ---------------- small helpers ---------------- */
const _q = new THREE.Quaternion(), _e = new THREE.Euler(), _s = new THREE.Vector3(1, 1, 1);
function mx4(x, y, z, rx, ry, rz) {
  _e.set(rx || 0, ry || 0, rz || 0); _q.setFromEuler(_e);
  return new THREE.Matrix4().compose(new THREE.Vector3(x, y, z), _q, _s);
}
// what moves is merged by hand, one mesh a material: parts are collected with their matrices and flushed into a group
// that turns (u3d.js's bake leaves a userData.dyn group and everything under it as it is)
function makeBin() {
  const by = new Map();
  return {
    add(geom, mat, m) { let a = by.get(mat); if (!a) by.set(mat, a = []); a.push(geom.clone().applyMatrix4(m)); },
    flush(parent) {
      by.forEach((geos, mat) => {
        const g = mergeGeometries(geos, false); geos.forEach((q) => q.dispose());
        if (!g) return;
        const m = new THREE.Mesh(g, mat); m.userData.own = true; parent.add(m);
      });
    }
  };
}
// the rotation of a point about y, as Object3D.rotation.y does it
const rotXZ = (x, z, a) => { const c = Math.cos(a), s = Math.sin(a); return [x * c + z * s, -x * s + z * c]; };
// a clock that keeps its own angle, so a station speeding up while it works (x1.6) does not jump
function clock(b, rates, start) {
  let last = null; const ang = start.slice();
  return (t, apply) => {
    const dt = last == null ? 0 : clamp(t - last, 0, 0.1); last = t;
    const k = b.busy ? 1.6 : 1;
    for (let i = 0; i < ang.length; i++) ang[i] += rates[i] * dt * k;
    apply(ang);
  };
}
// plating tiles on a lathe's surface, uv in the hull texture's tiles
function lathe(key, pts, seg, ku, kv) {
  if (GA[key]) return GA[key];
  const g = new THREE.LatheGeometry(pts.map((p) => new THREE.Vector2(p[0], p[1])), seg), uv = g.attributes.uv;
  for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * ku, uv.getY(i) * kv);
  return (GA[key] = g);
}
// a cylinder whose plating keeps its size (CO.ST.cyl stretches one tile round the whole drum)
function cylp(rt, rb, h, seg, open) {
  const ST = CO.ST, k = 'cp' + [rt, rb, h, seg, open ? 1 : 0].map(fx).join(',');
  if (GA[k]) return GA[k];
  const g = new THREE.CylinderGeometry(rt, rb, h, seg, 1, !!open), uv = g.attributes.uv, r = (rt + rb) / 2;
  const ku = 2 * PI * r / ST.TS, kv = Math.max(h, 0.1) / ST.TS;
  for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * ku, uv.getY(i) * kv);
  return (GA[k] = g);
}
// a band: a torus pressed flat along its axis (ax > 1 wider than thick), lying in the x-y plane, with the plating's uv
function band(R, tube, ax, seg) {
  const ST = CO.ST, k = 'bd' + [R, tube, ax, seg].map(fx).join(',');
  if (GA[k]) return GA[k];
  const g = new THREE.TorusGeometry(R, tube, 12, seg || 120), uv = g.attributes.uv;
  for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * 2 * PI * R / ST.TS, uv.getY(i) * 2 * PI * tube * (1 + ax) / 2 / ST.TS);
  g.scale(1, 1, ax);
  return (GA[k] = g);
}

/* ---------------- 01 Armillary Core ---------------- */
// Three gimbal rings, each on its own axis, turn round a glass capsule of decks with a spine of light. The rings float,
// pinned only to each other: the outer ring (vertical, turning about y) carries the middle one on its x axis, the middle
// one carries the inner on its z axis, and the capsule clears the inner ring, so nothing crosses a ring's path.
function armillary(b, n) {
  const ST = CO.ST, A = b.A, M = ST.mats(A);
  const { put, box, torus, pbox, sprite } = ST;
  const Hc = 1.2 + 0.2 * n, yc = 1.2, rc = 0.55, y0 = yc - Hc / 2, y1 = yc + Hc / 2;
  const R3 = Math.max(1.6, Hc / 2 + 0.45), R2 = R3 + 0.3, R1 = R2 + 0.3;
  const T1 = 0.1, T2 = 0.084, T3 = 0.07, AX = 1.4;   // (the spec's tubes, 0.075 / 0.062 / 0.052, read as wire at map distance)

  /* the capsule: collars, a glass shell and its two domes, a deck a department, a spine of light */
  const cup = (key, pts) => lathe(key, pts, 36, 1, 1);
  const dome = []; for (let i = 0; i <= 10; i++) { const a = i / 10 * PI / 2; dome.push([rc * Math.cos(a), 0.28 * Math.sin(a)]); }
  for (const s of [1, -1]) {
    const yy = s > 0 ? y1 : y0;
    // a collar at each end, a line of light where it meets the glass, eight lamps round its face, plated blocks on it
    put(b, cylp(rc + 0.08, rc + 0.08, 0.14, 40), M.mid, 0, yy - s * 0.07, 0);
    put(b, torus(rc + 0.09, 0.02, 5, 64), M.neon, 0, yy - s * 0.14, 0, { rx: PI / 2 });
    put(b, torus(rc + 0.085, 0.012, 4, 64), M.neonSoft, 0, yy, 0, { rx: PI / 2 });
    for (let k = 0; k < 8; k++) {
      const a = (k + 0.5) / 8 * PI * 2;
      box(b, 0.16, 0.05, 0.03, Math.cos(a) * (rc + 0.085), yy - s * 0.07, Math.sin(a) * (rc + 0.085), M.hot, { ry: PI / 2 - a });
      box(b, 0.12, 0.06, 0.1, Math.cos(a + PI / 8) * (rc + 0.04), yy + s * 0.03, Math.sin(a + PI / 8) * (rc + 0.04), k % 2 ? M.dark : M.mid, { ry: -a - PI / 8 });
    }
    // the glass dome on the collar (its lower half sunk in it, so the ends stay inside the inner ring's sphere)
    put(b, cup('ad' + fx(rc), dome), A.glass, 0, yy - s * 0.14, 0, { rx: s > 0 ? 0 : PI });
  }
  const shell = Hc - 0.28;
  put(b, ST.cyl(rc, rc, shell, 40, true), A.glass, 0, yc, 0);
  // ribs framing the windows, outside the glass
  for (let k = 0; k < 8; k++) { const a = (k + 0.5) / 8 * PI * 2; box(b, 0.04, shell, 0.04, Math.cos(a) * (rc + 0.02), yc, Math.sin(a) * (rc + 0.02), M.dark); }
  // inside: four struts; the decks; a halo of the spine's light
  for (let k = 0; k < 4; k++) { const a = k * PI / 2 + PI / 4; box(b, 0.035, shell, 0.035, Math.cos(a) * 0.3, yc, Math.sin(a) * 0.3, M.dark); }
  put(b, cylp(0.22, 0.22, shell - 0.04, 24), M.dark, 0, yc, 0);
  sprite(b, M.halo, 0, yc, 0, 2.4);
  // the decks: a disc a department (more of them where there are few), a line of light round its edge, its windows
  // (only the lit ones: on glass a dark pane reads as a hole)
  const pitch = (Hc - 0.4) / n, FLa = Math.max(1, Math.round(pitch / 0.24)), fp = pitch / FLa, nw = 16;
  for (let f = 0; f < n; f++) for (let k = 0; k < FLa; k++) {
    const yf = y0 + 0.2 + f * pitch + k * fp, wy = yf + fp / 2 + 0.03;
    put(b, ST.cyl(rc - 0.05, rc - 0.05, 0.05, 40), M.mid, 0, yf + 0.025, 0);
    put(b, torus(rc - 0.045, 0.012, 4, 48), M.neonSoft, 0, yf + 0.055, 0, { rx: PI / 2 });
    for (let i = 0; i < nw; i++) {
      if (b.R() > 0.85) continue;
      const t = (i + 0.5) / nw * PI * 2;   // (halfway between the eight ribs, which stand at (k + 0.5) / 8)
      b.win(Math.cos(t) * (rc + 0.014), wy, Math.sin(t) * (rc + 0.014), PI / 2 - t, 0.12, Math.min(0.1, fp * 0.46), f, true);
    }
  }
  // the ends, inside the inner ring's sphere: the spine, a rod of light, runs out through the caps to a beacon above and a
  // bright tip below; a hub round it at each cap, and a dark emitter housing under the lower one
  const room = R3 - T3 - 0.05 - (Hc / 2 + 0.14), ml = clamp(room - 0.08, 0.08, 0.2), yT = y1 + 0.17 + ml, yB = y0 - 0.17 - ml;
  put(b, new THREE.CylinderGeometry(0.04, 0.04, yT - yB, 10), M.hot, 0, (yT + yB) / 2, 0);
  put(b, cylp(0.13, 0.17, 0.06, 20), M.dark, 0, y1 + 0.14 + 0.03, 0);
  put(b, new THREE.CylinderGeometry(0.06, 0.07, 0.04, 14), M.mid, 0, y1 + 0.2, 0);
  b.beacon(0, yT, 0, 0.05);
  put(b, cylp(0.17, 0.13, 0.06, 20), M.dark, 0, y0 - 0.14 - 0.03, 0);
  put(b, new THREE.CylinderGeometry(0.09, 0.05, ml * 0.7, 12), M.dark, 0, y0 - 0.17 - ml * 0.35, 0);
  put(b, new THREE.SphereGeometry(0.05, 10, 8), M.hot, 0, yB, 0);

  /* the rings: plated bands, a line of light round each one's rim, clamps and lamps round it, two modules riding on it;
   * carried by one another, so each is a group inside the one before */
  const g1 = new THREE.Group(); g1.position.set(0, yc, 0); g1.userData.dyn = true; b.g.add(g1);
  const g2 = new THREE.Group(); g1.add(g2);
  const g3 = new THREE.Group(); g2.add(g3);
  const ring = (bin, R, tube, mat, orient, nClamp, seed, line) => {
    const Rm = mx4(0, 0, 0, orient[0], orient[1], orient[2]);
    const loc = (x, y, z, rx, ry, rz) => Rm.clone().multiply(mx4(x, y, z, rx, ry, rz));
    bin.add(band(R, tube, AX), mat, loc(0, 0, 0));
    bin.add(torus(R + tube * 1.02, 0.02, 5, 96), line, loc(0, 0, 0));
    const aw = tube * AX * 2.3;
    for (let k = 0; k < nClamp; k++) {
      const a = k / nClamp * PI * 2 + seed;
      bin.add(pbox(tube * 2 + 0.06, 0.13, aw), M.dark, loc(Math.cos(a) * (R + 0.03), Math.sin(a) * (R + 0.03), 0, 0, 0, a));
      if (k % 4 === 0) bin.add(pbox(0.02, 0.05, aw * 0.5), M.hot, loc(Math.cos(a) * (R + tube + 0.06), Math.sin(a) * (R + tube + 0.06), 0, 0, 0, a));
    }
    for (let k = 0; k < 2; k++) {
      const a = seed * 1.7 + k * PI + 0.4;
      bin.add(pbox(0.1, 0.32, aw * 1.15), M.mid, loc(Math.cos(a) * (R + tube + 0.01), Math.sin(a) * (R + tube + 0.01), 0, 0, 0, a));
      bin.add(pbox(0.02, 0.12, aw * 0.4), M.hot, loc(Math.cos(a) * (R + tube + 0.07), Math.sin(a) * (R + tube + 0.07), 0, 0, 0, a));
    }
  };
  const b1 = makeBin(), b2 = makeBin(), b3 = makeBin();
  // (the outer ring, farthest from the capsule, carries the bright line, as Citadel's one neon line; the two inside it a soft one)
  ring(b1, R1, T1, M.mid, [0, 0, 0], 16, 0.2, M.neon);
  ring(b2, R2, T2, M.mid, [PI / 2, 0, 0], 12, 0.9, M.neonSoft);
  ring(b3, R3, T3, M.mid, [0, PI / 2, 0], 8, 1.7, M.neonSoft);
  // pins: outer to middle on the outer ring's x axis, middle to inner on the middle ring's z axis; a bearing at each
  // end, and a light in the cap of each outer one
  const pins = (bin, Ro, Ri, axis, dots) => {
    const len = Ro - 0.06 - (Ri + 0.04), c = (Ro - 0.06 + Ri + 0.04) / 2;
    for (const s of [1, -1]) {
      const p = (d) => axis === 'x' ? [s * d, 0, 0] : [0, 0, s * d], rr = axis === 'x' ? [0, 0, PI / 2] : [PI / 2, 0, 0];
      bin.add(axis === 'x' ? pbox(len, 0.1, 0.1) : pbox(0.1, 0.1, len), M.dark, mx4(...p(c)));
      bin.add(ST.cyl(0.075, 0.075, 0.07, 14), M.dark, mx4(...p(Ro - 0.04), ...rr));
      bin.add(ST.cyl(0.07, 0.07, 0.06, 14), M.dark, mx4(...p(Ri + 0.06), ...rr));
      if (dots) {
        bin.add(ST.cyl(0.05, 0.05, 0.05, 12), M.dark, mx4(...p(Ro + (axis === 'x' ? T1 : T2) + 0.02), ...rr));
        bin.add(new THREE.SphereGeometry(0.04, 10, 8), M.hot, mx4(...p(Ro + (axis === 'x' ? T1 : T2) + 0.065)));
      }
    }
  };
  pins(b1, R1, R2, 'x', true);
  pins(b2, R2, R3, 'z', true);
  b1.flush(g1); b2.flush(g2); b3.flush(g3);
  // the motion: a real gimbal chain, F1 = RY(0.12 t), F2 = F1 RX(0.21 t), F3 = F2 RZ(-0.33 t)
  const step = clock(b, [0.12, 0.21, -0.33], [0.6 + b.phase * 0.5, 1.1 + b.phase * 0.3, 0.4]);
  b.anim.push((t) => step(t, (a) => { g1.rotation.y = a[0]; g2.rotation.x = a[1]; g3.rotation.z = a[2]; }));
  // the frame: the outer ring's reach (its tube, the clamps and lamps on it), above and below the capsule's middle
  const reach = R1 + T1 + 0.11;
  b.top = yc + reach; b.bot = yc - reach; b.foot = reach;
}

/* ---------------- 02 Helix Spire ---------------- */
// Square glass floors, each turned a little on the one below: the lit corners climb as a helix, ninety degrees over the
// tower, whose width tapers from 1.3 to 0.9. A deck a department, FL floors a deck; a ring of light travels up and down it.
function helix(b, n) {
  const ST = CO.ST, A = b.A, M = ST.mats(A), U = CO.U3;
  const { put, box, torus, pbox, greebles, engine } = ST;
  const H = clamp(0.62 * n, 1.8, 3.05), dh = H / n, FL = Math.max(3, Math.round(dh / 0.2)), J = n * FL, fh = H / J, R = b.R;
  const wAt = (y) => 1.3 - 0.4 * y / H, th = (j) => j * (PI / 2) / J;

  /* the plinth, its edge lit, hangar mouths and lamps round it, craft docked on it, the keel and its engine below */
  put(b, cylp(1.4, 1.4, 0.36, 56), M.mid, 0, -0.18, 0);
  put(b, torus(1.405, 0.022, 6, 120), M.neon, 0, 0, 0, { rx: PI / 2 });
  put(b, torus(1.403, 0.014, 6, 120), M.neonSoft, 0, -0.34, 0, { rx: PI / 2 });
  for (let k = 0; k < 10; k++) { const a = (k + 0.5) / 10 * PI * 2; box(b, 0.26, 0.08, 0.02,Math.cos(a) * 1.4, -0.18, Math.sin(a) * 1.4, M.hot, { ry: PI / 2 - a }); }
  put(b, lathe('hxKeel', [[0.26, -1.0], [0.46, -1.0], [1.0, -0.66], [1.37, -0.36]], 48, 3, 1), M.dark, 0, 0, 0);
  engine(b, M, 0, -0.86, 0, 0.2, 0, 0.8).rotation.x = -PI / 2;
  greebles(b, [M.mid, M.dark, M.light, M.mid], 0, -1.3, 1.3, -1.3, 1.3, 60, (x, z) => { const r = Math.hypot(x, z); return r > 1.05 && r < 1.3; }, 21);
  for (let k = 0; k < 4; k++) {
    const a = k * PI / 2 + PI / 4, x = Math.cos(a) * 1.2, z = Math.sin(a) * 1.2;
    box(b, 0.34, 0.2, 0.5, x, 0.1, z, M.light, { ry: -a + PI / 2 });
    box(b, 0.28, 0.03, 0.4, x, 0.215, z, M.dark, { ry: -a + PI / 2 });
    box(b, 0.05, 0.05, 0.02, x + Math.cos(a) * 0.2, 0.12, z + Math.sin(a) * 0.2, M.hot, { ry: PI / 2 - a });
    put(b, new THREE.CylinderGeometry(0.014, 0.02, 0.34, 6), M.metal, Math.cos(a + 0.5) * 1.3, 0.17, Math.sin(a + 0.5) * 1.3);
  }
  b.beacon(Math.cos(0.5 + PI / 4) * 1.3, 0.37, Math.sin(0.5 + PI / 4) * 1.3, 0.035);

  /* the floors: a slab (a thicker one, lit, at the foot of each deck), a core, glass, four posts of light, windows */
  for (let j = 0; j < J; j++) {
    const y = j * fh, w = wAt(y + fh / 2), a = th(j), f = Math.floor(j / FL), first = j % FL === 0, gh = fh - 0.035;
    box(b, w + (first ? 0.1 : 0.06), first ? 0.05 : 0.035, w + (first ? 0.1 : 0.06), 0, y + (first ? 0.025 : 0.0175), 0, first ? M.mid : M.dark, { ry: a });
    if (first) {
      // the deck's edge, a line of light round the slab
      for (const s of [1, -1]) {
        const [px, pz] = rotXZ(0, s * (w + 0.1) / 2, a), [qx, qz] = rotXZ(s * (w + 0.1) / 2, 0, a);
        box(b, w + 0.1, 0.02, 0.02, px, y + 0.05, pz, M.neonSoft, { ry: a });
        box(b, 0.02, 0.02, w + 0.1, qx, y + 0.05, qz, M.neonSoft, { ry: a });
      }
    }
    const core = 0.5 * (1 - 0.14 * j / (J - 1));
    box(b, core, fh, core, 0, y + fh / 2, 0, M.dark, { ry: a + 0.4 });
    put(b, pbox(w, gh, w), A.glass, 0, y + 0.035 + gh / 2, 0, { ry: a });
    for (const sx of [1, -1]) for (const sz of [1, -1]) { const [px, pz] = rotXZ(sx * w / 2, sz * w / 2, a); box(b, 0.036, fh, 0.036, px, y + fh / 2, pz, M.neon, { ry: a }); }
    // windows on the four faces (a face's normal is at a + k pi/2), dark panes left out: on glass they read as holes
    const m = Math.max(2, Math.floor(w / 0.26)), wy = y + 0.035 + gh / 2, wh = Math.min(0.07, gh * 0.55);
    for (let k = 0; k < 4; k++) {
      const phi = a + k * PI / 2, nx = Math.sin(phi), nz = Math.cos(phi), tx = Math.cos(phi), tz = -Math.sin(phi);
      for (let i = 0; i < m; i++) {
        if (R() > 0.58) continue;
        const u = -w / 2 + w / m * (i + 0.5), d = w / 2 + 0.012;
        b.win(nx * d + tx * u, wy, nz * d + tz * u, phi, 0.13, wh, f, true);
      }
    }
  }
  // the crown: a slab, a dark cap with a band of glass, a mast with collars and lamps, its beacon
  const aT = th(J - 1), wT = wAt(H);
  box(b, wT + 0.2, 0.08, wT + 0.2, 0, H + 0.04, 0, M.mid, { ry: aT });
  box(b, wT + 0.22, 0.02, wT + 0.22, 0, H + 0.075, 0, M.neonSoft, { ry: aT });
  box(b, wT * 0.5, 0.1, wT * 0.5, 0, H + 0.13, 0, M.mid, { ry: aT + 0.4 });
  put(b, lathe('hxMast', [[0.13, 0], [0.09, 0.1], [0.05, 0.3], [0.026, 0.55], [0.014, 0.73]], 12, 1, 1), M.metal, 0, H + 0.18, 0);
  for (const [yy, r] of [[0.3, 0.06], [0.55, 0.04]]) put(b, torus(r, 0.012, 6, 20), M.hot, 0, H + 0.18 + yy, 0, { rx: PI / 2 });
  box(b, 0.34, 0.016, 0.016, 0, H + 0.18 + 0.42, 0, M.metal, { ry: aT });
  box(b, 0.016, 0.016, 0.22, 0, H + 0.18 + 0.58, 0, M.metal, { ry: aT });
  b.beacon(0, H + 0.91, 0, 0.05);   // (the spec puts it at H + 0.96; its sphere then stood 0.05 over the limit top <= 4.01)

  /* the halo: a ring of light climbing the spire and coming down again, one climb in 9.8 s, its radius following the taper */
  const rm = 0.72 * 1.1 + 0.12, hg = new THREE.Group(); hg.userData.dyn = true; b.g.add(hg);
  const ringM = new THREE.Mesh(new THREE.TorusGeometry(1, 0.02 / rm, 6, 96), M.neon); ringM.userData.own = true; ringM.rotation.x = PI / 2; hg.add(ringM);
  const gs = U.glowSprite(A.c, 0.18, 1.2); gs.userData.dyn = true; hg.add(gs);
  const step = clock(b, [0.32], [b.phase * 0.4]);
  const place = (a) => { const y = 0.02 + (H - 0.04) * (1 - Math.cos(a)) / 2, r = 0.72 * wAt(y) + 0.12; hg.position.y = y; ringM.scale.set(r, r, r); };
  place(b.phase * 0.4);
  b.anim.push((t) => step(t, (a) => place(a[0])));
  b.top = H + 0.96; b.bot = -1.05; b.foot = 1.45;
}

/* ---------------- into u3d.js's table ---------------- */
const BUILD = { armillary, helix };
function install() {
  const U = CO.U3;
  if (!U || !U.ok || !U.SKIN || !CO.ST || U.skinsA === '1') return;
  Object.keys(BUILD).forEach((k) => { U.SKIN[k] = BUILD[k]; });
  U.skinsA = '1';
  window.dispatchEvent(new Event('co3d-skins'));
}
if (CO.U3 && CO.ST) install(); else window.addEventListener('co3d', install, { once: true });
