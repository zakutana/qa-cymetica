/* Two of the ten newer stations, built the way the seven are (the operator, 2026-10-24: "ty spodni modely sou jakoby
 * udelane v jinem stylu ... predelat vsechny ty spodni modely na zpusob vrchnich ... at to udelaji stejne a mame jen
 * jeden zpusob"): Rift Hold (an asteroid split in two, a glass deck a department bridging the lit rift) and Tesseract
 * Frame (a cube of struts balanced on a corner, a glass cube of decks turning the other way inside it). The design is
 * outbox/company-skins/SPEC.md, sections 07 and 08; the parts, the materials and the finish are stations.js's own,
 * through CO.ST: a plated hull in slate and steel, the company's colour only in lights (neon lines, hot dots, halos,
 * beacons), a deck's windows lit while its department works (b.win), surface detail, a crown. What moves, moves
 * slowly, and nothing pulses.
 *
 * A module of its own, run after stations.js: it puts its builders into u3d.js's table (CO.U3.SKIN) and says so with
 * the event co3d-skins, as stations.js does; CO.skinBuilt then turns true and Settings draws the real 3D station. */
import * as THREE from 'three/webgpu';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

const CO = window.CO;
const PI = Math.PI;
const V3 = THREE.Vector3;
const GD = {};                                  // geometries and the rock, made once
const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
const fx = (v) => (+v).toFixed(3);

/* ---------------- small helpers ---------------- */
const _q = new THREE.Quaternion(), _e = new THREE.Euler(), _s = new V3(1, 1, 1);
function mx4(x, y, z, rx, ry, rz) {
  _e.set(rx || 0, ry || 0, rz || 0); _q.setFromEuler(_e);
  return new THREE.Matrix4().compose(new V3(x, y, z), _q, _s);
}
// parts that move are merged by hand, one mesh a material, and flushed into the group that turns (u3d.js's bake leaves
// a userData.dyn group and everything under it as it is); static ones go through it too, to keep the call count small
function makeBin() {
  const by = new Map();
  return {
    add(geom, mat, m) {
      const key = mat.uuid + (geom.index ? 'i' : 'n');
      let a = by.get(key); if (!a) by.set(key, a = { mat, geos: [] });
      a.geos.push(geom.clone().applyMatrix4(m));
    },
    flush(parent) {
      by.forEach((a) => {
        const g = mergeGeometries(a.geos, false); a.geos.forEach((q) => q.dispose());
        if (!g) return;
        const m = new THREE.Mesh(g, a.mat); m.userData.own = true; parent.add(m);
      });
      by.clear();
    }
  };
}
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
// plating tiles on a lathe's surface, uv in the hull texture's tiles (points run from the bottom up)
function lathe(key, pts, seg, ku, kv) {
  if (GD[key]) return GD[key];
  const g = new THREE.LatheGeometry(pts.map((p) => new THREE.Vector2(p[0], p[1])), seg), uv = g.attributes.uv;
  for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * ku, uv.getY(i) * kv);
  return (GD[key] = g);
}
// a cylinder whose plating keeps its size (CO.ST.cyl stretches one tile round the whole drum)
function cylp(rt, rb, h, seg, open) {
  const ST = CO.ST, k = 'cp' + [rt, rb, h, seg, open ? 1 : 0].map(fx).join(',');
  if (GD[k]) return GD[k];
  const g = new THREE.CylinderGeometry(rt, rb, h, seg, 1, !!open), uv = g.attributes.uv, r = (rt + rb) / 2;
  const ku = 2 * PI * r / ST.TS, kv = Math.max(h, 0.1) / ST.TS;
  for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * ku, uv.getY(i) * kv);
  return (GD[k] = g);
}

/* ================================================================================================================
 * 07  Rift Hold
 * An asteroid split in two, the halves held apart (a gap of 1.0), a glass deck per department bridging the lit rift.
 * Each half is a rock with a flat, plated cut face turned to the rift; what is built on the rock is a fortress: bastions,
 * hangar mouths, turrets, domes, dishes; heavy tie beams cross the rift; two shuttles fly a slow circuit round it.
 * ================================================================================================================ */
const RC = 0.55, SX = 2.1, SY = 1.45, SZ = 1.8, GAP = 0.5;      // the rock: centre height, half sizes, half the gap

// the rock's own plate: noise, cracks and tone; a material kept on the colour's set (A.ndRock), so release() keeps it
function rockTex() {
  const T = CO.ST.T; if (T.rock) return T.rock;
  const R = CO.ST.rnd(31), S = 256;
  const c = CO.ST.canvas(S, S, (g) => {
    g.fillStyle = '#d4dae2'; g.fillRect(0, 0, S, S);
    const wrap = (fn) => { for (const dx of [-S, 0, S]) for (const dy of [-S, 0, S]) fn(dx, dy); };
    for (let i = 0; i < 320; i++) {
      const x = R() * S, y = R() * S, rx = 4 + R() * 26, ry = 3 + R() * 18, v = 176 + Math.round(R() * 70), a = 0.18 + R() * 0.3, rot = R() * PI;
      g.fillStyle = 'rgba(' + (v - 6) + ',' + v + ',' + (v + 8) + ',' + a + ')';
      wrap((dx, dy) => { g.beginPath(); g.ellipse(x + dx, y + dy, rx, ry, rot, 0, PI * 2); g.fill(); });
    }
    g.lineCap = 'round';
    for (let i = 0; i < 46; i++) {
      let x = R() * S, y = R() * S, a = R() * PI * 2; g.lineWidth = 0.8 + R() * 1.4; g.strokeStyle = 'rgba(26,32,42,' + (0.35 + R() * 0.4) + ')';
      g.beginPath(); g.moveTo(x, y);
      for (let k = 0; k < 6; k++) { a += (R() - 0.5) * 1.3; x += Math.cos(a) * (6 + R() * 16); y += Math.sin(a) * (6 + R() * 16); g.lineTo(x, y); }
      g.stroke();
    }
    for (let i = 0; i < 700; i++) { g.fillStyle = 'rgba(' + (R() < 0.5 ? '20,26,34' : '236,240,246') + ',' + (0.12 + R() * 0.3) + ')'; g.fillRect(R() * S, R() * S, 1 + R() * 2.4, 1 + R() * 2.4); }
  });
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 8;
  return (T.rock = t);
}
function rockMat(A) {
  if (A.ndRock) return A.ndRock;
  const ST = CO.ST, P = ST.plating(), c = A.c;
  // the plating's own lights as a rock's habitation lights, in the company's colour
  A.ndRock = new THREE.MeshStandardMaterial({ color: new THREE.Color(0xc4cdd9).lerp(c, 0.05), map: rockTex(), roughness: 0.9, metalness: 0.04, flatShading: true, emissive: c.clone(), emissiveMap: P.lights, emissiveIntensity: 1.1 });
  return A.ndRock;
}

// the rock, once: an icosphere pushed in and out by waves, fitted to the spec's box, cut at x = 0 into two halves that
// are moved apart; `surf` finds a point on a half's outside and its normal, `faceFrac` how far inside a half's cut face
// a point is (1 at its rim), `topY` the height of a half's top at a place
function rockKit() {
  if (GD.kit) return GD.kit;
  const ST = CO.ST, Rn = ST.rnd(23), k = []; for (let i = 0; i < 8; i++) k.push(Rn() * 6.2832);
  const rho = (x, y, z) => 1 + 0.12 * Math.sin(3.1 * x + k[0]) * Math.cos(2.7 * y + k[1]) + 0.085 * Math.sin(5.3 * z + 1.9 * x + k[2]) + 0.055 * Math.cos(7.1 * y + k[3]) +
    0.04 * Math.sin(11 * x + 4.1 * z + k[4]) * Math.sin(9 * y + k[5]) + 0.022 * Math.cos(17 * z + 13 * x + k[6]) + 0.035 * (1 - Math.abs(Math.sin(6.3 * x + 4.4 * y + 5.1 * z + k[7])));
  const base = new THREE.IcosahedronGeometry(1, 7), bp = base.attributes.position, nv = bp.count;
  const px = new Float32Array(nv), py = new Float32Array(nv), pz = new Float32Array(nv);
  let mx = 0, my = 0, mz = 0;
  for (let i = 0; i < nv; i++) {
    const x = bp.getX(i), y = bp.getY(i), z = bp.getZ(i), l = Math.hypot(x, y, z), r = rho(x / l, y / l, z / l);
    px[i] = x / l * r; py[i] = y / l * r; pz[i] = z / l * r;
    mx = Math.max(mx, Math.abs(px[i])); my = Math.max(my, Math.abs(py[i])); mz = Math.max(mz, Math.abs(pz[i]));
  }
  // fitted so the rock reaches exactly the spec's size: x to 2.1 (each half from the gap's edge, 0.5, to 2.6), y to 1.45, z to 1.8
  const fit = { x: SX / mx, y: SY / my, z: SZ / mz };
  const half = {};
  for (const sx of [1, -1]) {
    const g = new THREE.BufferGeometry(), pos = new Float32Array(nv * 3), uv = new Float32Array(nv * 2), ku = 1 / (ST.TS * 0.7);
    for (let i = 0; i < nv; i++) {
      let x = px[i] * fit.x; x = sx > 0 ? Math.max(x, 0) + GAP : Math.min(x, 0) - GAP;
      pos[i * 3] = x; pos[i * 3 + 1] = RC + py[i] * fit.y; pos[i * 3 + 2] = pz[i] * fit.z;
    }
    // uv from the dominant axis of each triangle's normal, so the plate keeps its size on every slope
    const a = new V3(), bb = new V3(), cc = new V3(), nn = new V3();
    for (let t = 0; t < nv; t += 3) {
      a.fromArray(pos, t * 3); bb.fromArray(pos, t * 3 + 3); cc.fromArray(pos, t * 3 + 6);
      nn.crossVectors(bb.clone().sub(a), cc.clone().sub(a));
      const ax = Math.abs(nn.x), ay = Math.abs(nn.y), az = Math.abs(nn.z), ix = ax >= ay && ax >= az ? 0 : ay >= az ? 1 : 2;
      for (let j = 0; j < 3; j++) {
        const o = (t + j) * 3, X = pos[o], Y = pos[o + 1], Z = pos[o + 2];
        const u = ix === 0 ? Z : X, v = ix === 1 ? Z : Y;
        uv[(t + j) * 2] = u * ku; uv[(t + j) * 2 + 1] = v * ku;
      }
    }
    g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('uv', new THREE.BufferAttribute(uv, 2));
    g.computeVertexNormals();
    g.computeBoundingBox(); g.computeBoundingSphere();
    half[sx] = g;
  }
  const dirOf = (sx, az, el) => new V3(sx * Math.cos(el) * Math.cos(az), Math.sin(el), Math.cos(el) * Math.sin(az));
  const P = (sx, az, el) => { const d = dirOf(sx, az, el), r = rho(d.x, d.y, d.z); return new V3(fit.x * r * d.x + sx * GAP, RC + fit.y * r * d.y, fit.z * r * d.z); };
  const kit = {
    half, rho, fit,
    surf(sx, az, el) {
      const e = 0.02, p = P(sx, az, el), pa = P(sx, az + e, el).sub(P(sx, az - e, el)), pe = P(sx, az, el + e).sub(P(sx, az, el - e));
      const n = new V3().crossVectors(pa, pe).normalize();
      if (n.dot(p.clone().sub(new V3(sx * GAP, RC, 0))) < 0) n.negate();
      return { p, n, t: pa.normalize() };
    },
    // how far inside the cut face (x = 0 plane) a point at (z, y) is: 1 at its rim
    faceFrac(z, y) {
      const qy = (y - RC) / fit.y, qz = z / fit.z, r = Math.hypot(qy, qz); if (r < 1e-6) return 0;
      return r / rho(0, qy / r, qz / r);
    },
    // the top of half sx at distance xh from its cut face, at z; null where there is no rock
    topY(sx, xh, z) {
      const x = sx * xh, inside = (y) => { const qx = x / fit.x, qy = (y - RC) / fit.y, qz = z / fit.z, r = Math.hypot(qx, qy, qz); return r < rho(qx / r, qy / r, qz / r); };
      for (let y = 2.7; y > RC; y -= 0.02) if (inside(y)) { let lo = y, hi = y + 0.02; for (let i = 0; i < 12; i++) { const m = (lo + hi) / 2; if (inside(m)) lo = m; else hi = m; } return lo; }
      return null;
    }
  };
  return (GD.kit = kit);
}
// a frame sitting on the rock at (az, el) of half sx: its y along the surface normal, turned by yaw about it
function frameAt(kit, sx, az, el, yaw) {
  const s = kit.surf(sx, az, el), e1 = s.t.clone().applyAxisAngle(s.n, yaw || 0), e3 = new V3().crossVectors(e1, s.n);
  return { F: new THREE.Matrix4().makeBasis(e1, s.n, e3).setPosition(s.p), p: s.p, n: s.n };
}

function rift(b, n) {
  const ST = CO.ST, A = b.A, M = ST.mats(A), R = b.R;
  const { put, pbox, sprite } = ST;
  const kit = rockKit(), rm = rockMat(A), bin = makeBin(), rr = ST.rnd(77);
  const gl = (geom, mat, x, y, z, rx, ry, rz) => bin.add(geom, mat, mx4(x, y, z, rx, ry, rz));
  const box_ = (w, h, d, x, y, z, mat, rx, ry, rz) => gl(pbox(w, h, d), mat, x, y, z, rx, ry, rz);

  // the two halves
  put(b, kit.half[1], rm, 0, 0, 0); put(b, kit.half[-1], rm, 0, 0, 0);

  // the decks: a bridge a department, stacked on y 0.62 and alternately at z +0.42 and -0.42
  const dh = Math.min(0.42, 1.9 / n), ys = [], zs = [];
  for (let f = 0; f < n; f++) { ys.push(0.62 + (f - (n - 1) / 2) * dh); zs.push(f % 2 ? -0.42 : 0.42); }
  const yLo = ys[0] - dh * 0.4, yHi = ys[n - 1] + dh * 0.4;

  /* the cut faces: a rim of light, seams of light, plated panels with their small detail, lit windows */
  const T = 0.025, seamY = [-0.15, 0.55, 1.25];
  for (const sx of [1, -1]) {
    const fxp = sx * GAP;                              // the face's plane
    // the rim of light round the face, at 0.86 of the way to its edge
    const pts = [];
    for (let i = 0; i < 96; i++) { const a = i / 96 * PI * 2, qy = Math.sin(a), qz = Math.cos(a), r = 0.86 * kit.rho(0, qy, qz); pts.push(new V3(fxp - sx * 0.012, RC + kit.fit.y * r * qy, kit.fit.z * r * qz)); }
    gl(new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts, true), 160, 0.022, 6, true), M.neon, 0, 0, 0);
    // the seams: three lines of light across the face, from edge to edge of its lit rim
    for (const y of seamY) {
      let z1 = 0; while (z1 < 2.2 && kit.faceFrac(z1 + 0.02, y) < 0.86) z1 += 0.02;
      if (z1 < 0.2) continue;
      box_(0.03, 0.03, z1 * 2, fxp - sx * 0.02, y, 0, M.neonSoft);
    }
    // plated panels in the bands between the seams
    const bands = [-0.82, -0.15, 0.55, 1.25, 1.92];
    for (let bi = 0; bi < bands.length - 1; bi++) {
      const y0 = bands[bi] + 0.05, y1 = bands[bi + 1] - 0.05, ph = y1 - y0, py = (y0 + y1) / 2;
      let z = -1.75;
      while (z < 1.7) {
        const w = 0.34 + rr() * 0.34, zc = z + w / 2; z += w + 0.05;
        const fits = [[zc - w / 2, y0], [zc + w / 2, y0], [zc - w / 2, y1], [zc + w / 2, y1]].every(([zz, yy]) => kit.faceFrac(zz, yy) < 0.82);
        if (!fits || rr() < 0.12) continue;
        if (zc + w / 2 > -0.84 && zc - w / 2 < 0.84 && y1 > yLo - 0.14 && y0 < yHi + 0.14) continue;   // the bridges' own place
        const mat = rr() < 0.55 ? M.dark : M.mid, px = fxp - sx * T / 2;
        box_(T, ph, w, px, py, zc, mat);
        // a plate's small detail: blocks, a vent, a lit slot
        const cnt = 3 + Math.floor(rr() * 4);
        for (let k2 = 0; k2 < cnt; k2++) {
          const bw = 0.05 + rr() * 0.12, bh = 0.04 + rr() * 0.14, bt = 0.012 + rr() * 0.026, bz = zc + (rr() - 0.5) * (w - bw - 0.05), by = py + (rr() - 0.5) * (ph - bh - 0.06);
          box_(bt, bh, bw, fxp - sx * (T + bt / 2), by, bz, rr() < 0.4 ? M.light : rr() < 0.5 ? M.metal : M.mid);
        }
        if (rr() < 0.55) box_(0.012, 0.022, w * 0.5, fxp - sx * (T + 0.006), py + (rr() - 0.5) * ph * 0.6, zc, M.hot);
      }
    }
    // lit windows: a grid of them up the face either side of the bridges, a band of height a deck (a deck's windows
    // light while its department works)
    const w0 = -0.72, w1 = 1.86;
    for (let y = w0; y <= w1; y += 0.16) {
      const f = clamp(Math.floor((y - w0) / (w1 - w0 + 1e-6) * n), 0, n - 1);
      for (const z of [-1.52, -1.34, -1.16, -0.98, 0.98, 1.16, 1.34, 1.52]) {
        if (kit.faceFrac(z, y) > 0.78) continue;
        b.win(fxp - sx * (T + 0.012), y, z, -sx * PI / 2, 0.11, 0.06, f, R() < 0.72);
      }
    }
  }

  /* the rift: sheets of light in the plane between the halves, spots of light in it */
  const sheet = new THREE.CircleGeometry(1, 56); sheet.rotateY(PI / 2); sheet.scale(1, SY * 0.82, SZ * 0.82); sheet.translate(0, RC, 0);
  for (const x of [-0.24, 0, 0.24]) gl(sheet, A.beam, x, 0, 0);
  for (const y of seamY) sprite(b, M.halo, 0, y, 0, 1.3);

  /* the bridges: a glass box crossing the rift, plates over and under it, abutments where it meets each half, a line
   * of light under its front edge, five windows a face */
  for (let f = 0; f < n; f++) {
    const y = ys[f], z = zs[f], gh = dh * 0.6, sz = Math.sign(z);
    gl(new THREE.BoxGeometry(1.5, gh, 0.52), A.glass, 0, y, z);
    box_(1.6, 0.04, 0.6, 0, y + gh / 2 + 0.02, z, M.mid);
    box_(1.6, 0.04, 0.6, 0, y - gh / 2 - 0.02, z, M.dark);
    box_(1.0, 0.03, 0.03, 0, y - gh / 2 - 0.05, z + sz * 0.3, M.neon);
    box_(1.0, 0.022, 0.4, 0, y - gh / 2 + 0.012, z, M.dark);               // its floor
    box_(1.0, 0.02, 0.02, 0, y + gh / 2 - 0.03, z, M.neonSoft);            // its ceiling light
    for (const s of [1, -1]) {
      box_(0.14, gh + 0.1, 0.66, s * (GAP - 0.01), y, z, M.dark);          // the abutment
      box_(0.03, 0.03, 0.4, s * (GAP - 0.09), y + gh / 2 - 0.02, z, M.hot);
      for (const o of [-1, 1]) box_(0.03, gh * 0.9, 0.03, s * 0.2, y, z + o * 0.26, M.metal);
    }
    for (let k = 0; k < 5; k++) for (const o of [1, -1]) b.win(-0.4 + k * 0.2, y, z + o * (0.26 + 0.012), o > 0 ? 0 : PI, 0.12, Math.min(0.07, gh * 0.55), f, true);
  }

  /* tie beams: heavy girders crossing the rift, clamped to each face, lit along their top */
  const ties = [];
  for (const y of [-0.5, 1.7]) {
    let z1 = 0; while (z1 < 2.2 && kit.faceFrac(z1 + 0.02, y) < 0.74) z1 += 0.02;
    if (z1 > 0.3) ties.push([y, z1 * 0.72], [y, -z1 * 0.72]);
  }
  for (const [y, z] of ties) {
    if (y > yLo - 0.2 && y < yHi + 0.2 && Math.abs(Math.abs(z) - 0.42) < 0.5) continue;
    box_(1.2, 0.1, 0.12, 0, y, z, M.dark);
    box_(1.2, 0.025, 0.04, 0, y + 0.062, z, M.metal);
    box_(0.9, 0.02, 0.02, 0, y + 0.085, z, M.neonSoft);
    for (const s of [1, -1]) { box_(0.12, 0.18, 0.2, s * (GAP - 0.04), y, z, M.mid); box_(0.02, 0.05, 0.12, s * (GAP - 0.11), y, z, M.hot); }
    gl(new THREE.SphereGeometry(0.04, 10, 8), M.hot, 0, y + 0.07, z);
  }

  /* what is built on the outside of the rock: placed on its surface, each on the surface's normal */
  const placed = [], clear = (p, d) => placed.every((q) => q.distanceTo(p) > d);
  const make = {
    hangar(F) {   // a mouth cut into the rock: a frame, its glowing slot, light posts either side
      const add = (g, m, x, y, z, ry) => bin.add(g, m, F.clone().multiply(mx4(x, y, z, 0, ry || 0, 0)));
      add(pbox(0.42, 0.07, 0.3), M.dark, 0, 0.005, 0); add(pbox(0.3, 0.02, 0.18), M.hot, 0, 0.045, 0);
      for (const s of [1, -1]) { add(pbox(0.04, 0.1, 0.34), M.mid, s * 0.22, 0.035, 0); add(new THREE.SphereGeometry(0.025, 8, 6), M.hot, s * 0.22, 0.1, 0.15); add(new THREE.SphereGeometry(0.025, 8, 6), M.hot, s * 0.22, 0.1, -0.15); }
      for (let k = 0; k < 4; k++) add(pbox(0.26, 0.012, 0.02), M.neonSoft, 0, 0.056, -0.08 + k * 0.055);
    },
    turret(F, s) {
      const add = (g, m, x, y, z, rx, ry, rz) => bin.add(g, m, F.clone().multiply(mx4(x, y, z, rx, ry, rz)));
      add(cylp(0.12 * s, 0.14 * s, 0.07, 14), M.dark, 0, 0.02, 0); add(cylp(0.09 * s, 0.1 * s, 0.05, 14), M.mid, 0, 0.075, 0);
      add(pbox(0.16 * s, 0.09 * s, 0.2 * s), M.light, 0, 0.14, 0, 0, 0.6);
      for (const o of [-1, 1]) add(new THREE.CylinderGeometry(0.015 * s, 0.018 * s, 0.34 * s, 8), M.metal, o * 0.045 * s, 0.15, 0.2 * s, PI / 2 - 0.25, 0.6, 0);
      add(new THREE.SphereGeometry(0.022, 8, 6), M.hot, 0, 0.2, 0);
    },
    dome(F, s) {
      const add = (g, m, x, y, z, rx) => bin.add(g, m, F.clone().multiply(mx4(x, y, z, rx || 0, 0, 0)));
      add(cylp(0.17 * s, 0.2 * s, 0.06, 20), M.dark, 0, 0.015, 0);
      add(new THREE.SphereGeometry(0.15 * s, 18, 10, 0, PI * 2, 0, PI / 2), M.light, 0, 0.045, 0);
      add(new THREE.TorusGeometry(0.153 * s, 0.01, 5, 24), M.neon, 0, 0.05, 0, PI / 2);
    },
    armour(F, s) {   // a plate of armour laid on the rock, its edge lit, blocks and a vent on it
      const add = (g, m, x, y, z, ry) => bin.add(g, m, F.clone().multiply(mx4(x, y, z, 0, ry || 0, 0)));
      const w = 0.62 * s, d = 0.46 * s;
      add(pbox(w, 0.05, d), M.mid, 0, 0.0, 0); add(pbox(w * 0.9, 0.025, d * 0.9), M.dark, 0, 0.04, 0);
      add(pbox(w, 0.014, 0.014), M.neonSoft, 0, 0.03, d / 2); add(pbox(0.014, 0.014, d), M.neonSoft, w / 2, 0.03, 0);
      for (let k = 0; k < 4; k++) add(pbox(0.07 + (k % 2) * 0.05, 0.04 + (k % 3) * 0.02, 0.07), k % 2 ? M.light : M.metal, (k - 1.5) * w * 0.2, 0.07, (k % 2 ? 1 : -1) * d * 0.18);
      add(pbox(0.012, 0.012, 0.012), M.hot, -w * 0.4, 0.07, d * 0.3);
    },
    dish(F, s) {
      const add = (g, m, x, y, z, rx, ry, rz) => bin.add(g, m, F.clone().multiply(mx4(x, y, z, rx, ry, rz)));
      add(new THREE.CylinderGeometry(0.02, 0.03, 0.16 * s, 8), M.metal, 0, 0.08 * s, 0);
      add(new THREE.ConeGeometry(0.2 * s, 0.07 * s, 18, 1, true), M.light, 0, 0.2 * s, 0, -0.5, 0.8, 0);
      add(new THREE.CylinderGeometry(0.008, 0.008, 0.2 * s, 6), M.metal, 0, 0.27 * s, -0.04 * s, 0.25, 0.8, 0);
      add(new THREE.SphereGeometry(0.02, 8, 6), M.hot, 0, 0.36 * s, -0.08 * s);
    },
    bastion(F, s) {
      const add = (g, m, x, y, z, ry) => bin.add(g, m, F.clone().multiply(mx4(x, y, z, 0, ry || 0, 0)));
      add(pbox(0.36 * s, 0.1, 0.28 * s), M.dark, 0, 0.0, 0); add(pbox(0.26 * s, 0.13, 0.2 * s), M.mid, 0.02, 0.1, 0.0); add(pbox(0.14 * s, 0.07, 0.12 * s), M.light, -0.04, 0.2, 0.02);
      for (let k = 0; k < 4; k++) add(pbox(0.025, 0.02, 0.012), M.hot, -0.1 * s + k * 0.065 * s, 0.1, 0.1 * s + 0.004);
      add(new THREE.CylinderGeometry(0.01, 0.014, 0.3, 6), M.metal, 0.1 * s, 0.3, -0.05); add(new THREE.SphereGeometry(0.02, 8, 6), M.hot, 0.1 * s, 0.46, -0.05);
    },
    lights(F, s) {   // a string of lamps along a ridge
      for (let k = -3; k <= 3; k++) bin.add(new THREE.SphereGeometry(0.018, 6, 5), M.hot, F.clone().multiply(mx4(k * 0.1 * s, 0.025, (k % 2) * 0.03)));
      bin.add(pbox(0.7 * s, 0.015, 0.03), M.metal, F.clone().multiply(mx4(0, 0.01, 0)));
    }
  };
  // towers stand upright on the rock whatever its slope (their windows face the four ways round), sunk into it on a plinth
  let tw = 0;
  for (const sx of [1, -1]) for (let tries = 0, cnt = 0; cnt < 3 && tries < 200; tries++) {
    const az = (rr() * 2 - 1) * 1.1, el = 0.55 + rr() * 0.8;
    if (Math.cos(el) * Math.cos(az) < 0.34) continue;
    const s = kit.surf(sx, az, el);
    if (s.n.y < 0.6 || Math.abs(s.p.x) < GAP + 0.3 || !clear(s.p, 0.62)) continue;
    if (Math.hypot(s.p.x - sx * 1.45, s.p.z) < 0.95 && sx > 0) continue;
    if (Math.hypot(s.p.x + 1.2, s.p.z - 0.25) < 0.7 && sx < 0) continue;
    placed.push(s.p.clone()); cnt++;
    const tH = 0.45 + rr() * 0.3, tw0 = 0.2 + rr() * 0.06, x0 = s.p.x, z0 = s.p.z, y0 = s.p.y - 0.12;
    box_(tw0 + 0.16, 0.26, tw0 + 0.16, x0, y0 + 0.13, z0, M.dark);
    box_(tw0, tH, tw0, x0, y0 + 0.26 + tH / 2, z0, M.light);
    box_(tw0 + 0.06, 0.04, tw0 + 0.06, x0, y0 + 0.26 + tH + 0.02, z0, M.metal);
    box_(tw0 + 0.02, 0.025, tw0 + 0.02, x0, y0 + 0.26 + tH * 0.5, z0, M.neonSoft);
    // every other tower steps in once more (a lit crown with a dish), the rest carry a mast
    if (tw % 2) {
      box_(tw0 * 0.68, 0.16, tw0 * 0.68, x0, y0 + 0.26 + tH + 0.1, z0, M.mid);
      box_(tw0 * 0.74, 0.016, tw0 * 0.74, x0, y0 + 0.26 + tH + 0.19, z0, M.neon);
      gl(new THREE.ConeGeometry(0.1, 0.05, 14, 1, true), M.light, x0, y0 + 0.26 + tH + 0.27, z0, -0.5, 0.7, 0);
      gl(new THREE.SphereGeometry(0.02, 8, 6), M.hot, x0, y0 + 0.26 + tH + 0.31, z0 - 0.03);
    } else {
      gl(new THREE.CylinderGeometry(0.012, 0.018, 0.3, 6), M.metal, x0, y0 + 0.26 + tH + 0.19, z0);
      gl(new THREE.SphereGeometry(0.022, 8, 6), M.hot, x0, y0 + 0.26 + tH + 0.35, z0);
    }
    const rowsT = Math.max(2, Math.floor(tH / 0.13));
    for (let r = 0; r < rowsT; r++) {
      const wy = y0 + 0.26 + 0.1 + r * (tH - 0.16) / Math.max(1, rowsT - 1), f = (tw * 3 + r) % n;
      for (const [nx, nz, ry] of [[0, 1, 0], [0, -1, PI], [1, 0, PI / 2], [-1, 0, -PI / 2]]) for (const u of [-0.06, 0.06]) {
        b.win(x0 + nx * (tw0 / 2 + 0.012) + (nz ? u : 0), wy, z0 + nz * (tw0 / 2 + 0.012) + (nx ? u : 0), ry, 0.07, 0.05, f, R() < 0.75);
      }
    }
    tw++;
  }
  const kinds = ['armour', 'hangar', 'bastion', 'turret', 'armour', 'dome', 'dish', 'bastion', 'armour', 'turret', 'hangar', 'lights', 'dome', 'armour'];
  let ki = 0;
  for (const sx of [1, -1]) for (let tries = 0, cnt = 0; cnt < 18 && tries < 400; tries++) {
    const az = (rr() * 2 - 1) * 1.2, el = (rr() * 2 - 1) * 1.25;
    const dx = Math.cos(el) * Math.cos(az); if (dx < 0.28) continue;
    const fr = frameAt(kit, sx, az, el, rr() * PI * 2);
    if (fr.p.y < RC - 0.9 + 0.35 && fr.n.y < -0.2) continue;                      // not under the belly
    if (!clear(fr.p, 0.46)) continue;
    // not where the pad and the mast stand
    if (Math.hypot(fr.p.x - sx * 1.45, fr.p.z) < 0.9 && fr.p.y > 1.3) continue;
    if (Math.abs(fr.p.x) < GAP + 0.18) continue;                                  // nor along the cut's edge
    placed.push(fr.p.clone()); cnt++;
    make[kinds[ki++ % kinds.length]](fr.F, 1.0 + rr() * 0.55);
  }

  /* the landing pad on the right half: a column, a deck, a ring of light, four lamps, a cross of light, a ship on it */
  {
    const x0 = 1.45, z0 = -0.15, ty = kit.topY(1, x0 - GAP, z0) || 1.9, py = ty + 0.34, ex = x0;
    box_(0.52, py - ty + 0.5, 0.52, ex, ty - 0.2 + (py - ty + 0.5) / 2 - 0.1, z0, M.mid);           // the column (stood in the rock)
    gl(cylp(0.55, 0.55, 0.08, 36), M.metal, ex, py, z0);
    gl(cylp(0.3, 0.38, 0.18, 24), M.dark, ex, py - 0.12, z0);
    gl(new THREE.TorusGeometry(0.5, 0.02, 6, 48), M.neon, ex, py + 0.045, z0, PI / 2);
    for (let k = 0; k < 4; k++) { const a = k * PI / 2 + PI / 4; gl(new THREE.SphereGeometry(0.035, 8, 6), M.hot, ex + Math.cos(a) * 0.5, py + 0.1, z0 + Math.sin(a) * 0.5); }
    box_(0.6, 0.012, 0.025, ex, py + 0.045, z0, M.neonSoft); box_(0.025, 0.012, 0.6, ex, py + 0.045, z0, M.neonSoft);
    // a small ship parked on it
    box_(0.2, 0.06, 0.36, ex + 0.04, py + 0.1, z0, M.light, 0, 0.5);
    box_(0.1, 0.05, 0.14, ex + 0.04 - Math.sin(0.5) * 0.12, py + 0.15, z0 - Math.cos(0.5) * 0.12, M.dark, 0, 0.5);
    box_(0.34, 0.015, 0.1, ex + 0.04, py + 0.095, z0, M.mid, 0, 0.5);
    gl(new THREE.SphereGeometry(0.03, 8, 6), M.hot, ex + 0.04 + Math.sin(0.5) * 0.19, py + 0.1, z0 + Math.cos(0.5) * 0.19);
    placed.push(new V3(ex, py, z0));
  }
  /* the mast on the left half: a lattice to y 2.7, cross-arms, lamps, its beacon */
  {
    const x0 = -1.2, z0 = 0.25, ty = kit.topY(-1, -x0 - GAP, z0) || 1.8, top = 2.7;
    gl(cylp(0.2, 0.28, 0.14, 12), M.dark, x0, ty + 0.02, z0);
    gl(new THREE.CylinderGeometry(0.03, 0.05, top - ty, 8), M.metal, x0, (top + ty) / 2, z0);
    for (let k = 0; k < 3; k++) {
      const yy = ty + (top - ty) * (0.3 + k * 0.24), w = 0.34 - k * 0.07;
      box_(w, 0.02, 0.02, x0, yy, z0, M.metal); box_(0.02, 0.02, w * 0.7, x0, yy + 0.05, z0, M.metal);
      for (const s of [1, -1]) gl(new THREE.SphereGeometry(0.02, 8, 6), M.hot, x0 + s * w / 2, yy, z0);
    }
    gl(cylp(0.08, 0.08, 0.04, 12), M.mid, x0, top - 0.1, z0);
    b.beacon(x0, top + 0.08, z0, 0.05);
  }

  /* engines under each half, holding it up: two a half, in the rock's belly */
  for (const sx of [1, -1]) for (const az of [-0.5, 0.5]) {
    const s = kit.surf(sx, az, -1.1), eng = ST.engine(b, M, s.p.x, s.p.y + 0.04, s.p.z, 0.18, 0, 0.8); eng.rotation.x = -PI / 2;
  }
  bin.flush(b.g);

  /* two shuttles on a slow circuit round it, at the spec's 3.25: escorts() clears the rock's bounding boxes, whose
   * corners reach farther than the rock does, so it is handed an empty stand-in to measure and its group moved over */
  { const hold = { g: new THREE.Group(), anim: b.anim, phase: b.phase }; ST.escorts(hold, M, 3.25, 0.95, 2, 0.3); hold.g.children.slice().forEach((o) => b.g.add(o)); }
  b.top = 2.85; b.bot = -0.95; b.foot = 3.45;
}

/* ================================================================================================================
 * 08  Tesseract Frame
 * A cube of struts balanced on one corner, turning; inside it a glass cube of decks turning the other way.
 * ================================================================================================================ */
function tesseract(b, n) {
  const ST = CO.ST, A = b.A, M = ST.mats(A), R = b.R;
  const { put, box, pbox, torus, sprite, greebles } = ST;
  const big = n >= 5, a = big ? 2.6 : 2.3, c = big ? 1.45 : 1.25, h = a / 2, yb = -0.95, yc = yb + a * Math.sqrt(3) / 2, yt = yb + a * Math.sqrt(3);
  const tilt = new THREE.Matrix4().makeRotationFromEuler(new THREE.Euler(0, PI / 4, Math.atan(Math.SQRT2), 'ZYX'));
  const lc = (x, y, z, rx, ry, rz) => tilt.clone().multiply(mx4(x, y, z, rx, ry, rz));

  /* the base: a plated disc, its edge lit, lamps and blocks round it, a cup the corner sits in, a keel and an engine */
  put(b, cylp(1.25, 1.25, 0.22, 56), M.mid, 0, -1.55, 0);
  put(b, torus(1.255, 0.024, 6, 120), M.neon, 0, -1.44, 0, { rx: PI / 2 });
  put(b, torus(1.252, 0.014, 6, 120), M.neonSoft, 0, -1.66, 0, { rx: PI / 2 });
  for (let k = 0; k < 12; k++) { const t = (k + 0.5) / 12 * PI * 2; box(b, 0.2, 0.07, 0.02, Math.cos(t) * 1.25, -1.55, Math.sin(t) * 1.25, M.hot, { ry: PI / 2 - t }); }
  put(b, lathe('tsKeel', [[0.22, -2.05], [0.4, -2.02], [0.95, -1.82], [1.22, -1.66]], 48, 3, 1), M.dark, 0, 0, 0);
  ST.engine(b, M, 0, -1.86, 0, 0.2, 0, 0.8).rotation.x = -PI / 2;
  put(b, lathe('tsCup', [[0.3, -1.44], [0.42, -1.44], [0.3, -1.3], [0.16, -1.12], [0.3, -0.98]], 28, 2, 1), M.metal, 0, 0, 0);
  put(b, torus(0.42, 0.018, 6, 40), M.neon, 0, -1.43, 0, { rx: PI / 2 });
  greebles(b, [M.mid, M.dark, M.light, M.mid], -1.44, -1.2, 1.2, -1.2, 1.2, 36, (x, z) => {
    const r = Math.hypot(x, z); if (r < 0.95 || r > 1.2) return false;
    for (let k = 0; k < 4; k++) { const t = k * PI / 2 + 0.4; if (Math.hypot(x - Math.cos(t), z - Math.sin(t)) < 0.34) return false; }
    return true;
  }, 41);
  // a second, smaller tier on the disc (its edge lit), and four pods on the rim with windows of their own
  put(b, cylp(0.82, 0.92, 0.1, 40), M.dark, 0, -1.39, 0); put(b, torus(0.82, 0.014, 6, 80), M.neonSoft, 0, -1.34, 0, { rx: PI / 2 });
  for (let k = 0; k < 4; k++) {
    const t = k * PI / 2 + 0.4, x = Math.cos(t) * 1.0, z = Math.sin(t) * 1.0, ry = PI / 2 - t;
    box(b, 0.34, 0.2, 0.3, x, -1.33, z, k % 2 ? M.mid : M.light, { ry });
    box(b, 0.38, 0.03, 0.34, x, -1.225, z, M.metal, { ry });
    box(b, 0.05, 0.05, 0.02, x + Math.cos(t) * 0.17, -1.31, z + Math.sin(t) * 0.17, M.hot, { ry });
    // (a box turned by ry: its +z face looks along (sin ry, cos ry); a window row on each of the four faces)
    for (let q = 0; q < 4; q++) {
      const phi = ry + q * PI / 2, dd = (q % 2 ? 0.15 : 0.17) + 0.012;
      for (const u of [-0.08, 0.08]) {
        const tx = Math.cos(phi), tz = -Math.sin(phi);
        b.win(x + Math.sin(phi) * dd + tx * u * (q % 2 ? 0.8 : 1), -1.325, z + Math.cos(phi) * dd + tz * u * (q % 2 ? 0.8 : 1), phi, 0.1, 0.06, (k * 2 + (q >> 1)) % n, R() < 0.8);
      }
    }
  }
  for (let k = 0; k < 3; k++) {
    const t = k * PI * 2 / 3 + 1.3;
    put(b, new THREE.CylinderGeometry(0.012, 0.018, 0.34, 6), M.metal, Math.cos(t) * 1.12, -1.27, Math.sin(t) * 1.12);
  }
  b.beacon(Math.cos(1.3) * 1.12, -1.09, Math.sin(1.3) * 1.12, 0.035);
  // the axis: a thin line of light up through the middle of both cubes, bottom corner to top
  put(b, new THREE.CylinderGeometry(0.022, 0.022, yt - yb - 0.4, 8), A.glow, 0, (yt + yb) / 2, 0);

  /* the frame: twelve struts, eight nodes; each edge a line of light; turning about the vertical */
  const spin = new THREE.Group(); spin.position.set(0, yc, 0); spin.userData.dyn = true; b.g.add(spin);
  const fb = makeBin(), sd = [1, -1], SW = 0.13, ND = 0.25;
  for (const sx of sd) for (const sy of sd) for (const sz of sd) {
    fb.add(pbox(ND, ND, ND), M.light, lc(sx * h, sy * h, sz * h));
    // a cap on each of the node's three outer faces, a lamp at its outer tip
    const ct = ND / 2 + 0.01, cs = ND * 0.74;
    fb.add(pbox(0.026, cs, cs), M.dark, lc(sx * (h + ct), sy * h, sz * h)); fb.add(pbox(cs, 0.026, cs), M.dark, lc(sx * h, sy * (h + ct), sz * h)); fb.add(pbox(cs, cs, 0.026), M.dark, lc(sx * h, sy * h, sz * (h + ct)));
    if (!(sx < 0 && sy < 0 && sz < 0) && !(sx > 0 && sy > 0 && sz > 0)) fb.add(new THREE.SphereGeometry(0.045, 10, 8), M.hot, lc(sx * (h + 0.16), sy * (h + 0.16), sz * (h + 0.16)));
  }
  for (let ax = 0; ax < 3; ax++) for (const s1 of sd) for (const s2 of sd) {
    const o = [0, 0, 0], oth = [0, 1, 2].filter((i) => i !== ax); o[oth[0]] = s1 * h; o[oth[1]] = s2 * h;
    const len = a - ND + 0.04, dims = [SW, SW, SW]; dims[ax] = len;
    fb.add(pbox(dims[0], dims[1], dims[2]), (ax + (s1 > 0 ? 1 : 0) + (s2 > 0 ? 1 : 0)) % 2 ? M.light : M.mid, lc(o[0], o[1], o[2]));
    const ou = new V3(o[0], o[1], o[2]).normalize(), put3 = (t, off) => { const p = [o[0] + ou.x * off, o[1] + ou.y * off, o[2] + ou.z * off]; p[ax] += t; return p; };
    // the edge's line of light on its outer corner
    const ld = [0.034, 0.034, 0.034]; ld[ax] = len * 0.88;
    let p = put3(0, SW * 0.707 + 0.012); fb.add(pbox(ld[0], ld[1], ld[2]), M.neon, lc(p[0], p[1], p[2]));
    // clamps along it, a junction at its middle with a lamp
    for (const t of [-0.3, 0.3]) { const cd = [SW + 0.05, SW + 0.05, SW + 0.05]; cd[ax] = 0.09; p = put3(t * len, 0); fb.add(pbox(cd[0], cd[1], cd[2]), M.dark, lc(p[0], p[1], p[2])); }
    const jd = [SW + 0.07, SW + 0.07, SW + 0.07]; jd[ax] = 0.15; p = put3(0, 0); fb.add(pbox(jd[0], jd[1], jd[2]), M.metal, lc(p[0], p[1], p[2]));
    p = put3(0, SW * 0.707 + 0.07); fb.add(new THREE.SphereGeometry(0.032, 8, 6), M.hot, lc(p[0], p[1], p[2]));
  }
  fb.flush(spin);
  // its crown, on the top corner (on the axis, so it stands still while the frame turns): a prism of light, its halo, a beacon
  put(b, new THREE.OctahedronGeometry(0.085), M.hot, 0, yt + 0.27, 0, { s: [0.8, 1.45, 0.8] });
  sprite(b, M.halo, 0, yt + 0.27, 0, 1.3);
  b.beacon(0, yt + 0.42, 0, 0.04);

  /* the inner cube: upright, glass, edges lit, floors with their windows, a core of light; turning the other way */
  const ic = new THREE.Group(); ic.position.set(0, yc, 0); ic.userData.dyn = true; b.g.add(ic);
  const ib = makeBin(), innerH = c - 0.2, FL = Math.max(1, Math.round(innerH / n / 0.17)), J = n * FL, pitch = innerH / J, hc = c / 2;
  ib.add(new THREE.BoxGeometry(c, c, c), A.glass, mx4(0, 0, 0));
  ib.add(pbox(c + 0.08, 0.05, c + 0.08), M.mid, mx4(0, hc + 0.025, 0)); ib.add(pbox(c + 0.08, 0.05, c + 0.08), M.dark, mx4(0, -hc - 0.025, 0));
  ib.add(pbox(c * 0.5, 0.04, c * 0.5), M.light, mx4(0, hc + 0.07, 0)); ib.add(pbox(c * 0.5, 0.04, c * 0.5), M.light, mx4(0, -hc - 0.07, 0));
  for (const sx of sd) for (const sz of sd) {
    ib.add(pbox(0.07, c, 0.07), M.dark, mx4(sx * hc, 0, sz * hc));
    ib.add(pbox(0.03, c - 0.1, 0.03), M.neonSoft, mx4(sx * (hc + 0.045), 0, sz * (hc + 0.045)));
    for (const sy of sd) ib.add(new THREE.SphereGeometry(0.035, 8, 6), M.hot, mx4(sx * (hc + 0.06), sy * (hc + 0.05), sz * (hc + 0.06)));
  }
  for (const sy of sd) for (const s2 of sd) {
    ib.add(pbox(c + 0.06, 0.03, 0.03), M.neonSoft, mx4(0, sy * (hc + 0.055), s2 * hc));
    ib.add(pbox(0.03, 0.03, c + 0.06), M.neonSoft, mx4(s2 * hc, sy * (hc + 0.055), 0));
  }
  // the floors: a slab each (the first of a deck with a line of light round its edge), a core, windows on all four faces
  const wins = [], ww = 0.15, wh = Math.min(0.08, pitch * 0.52), m = Math.max(2, Math.floor((c - 0.2) / 0.24));
  for (let j = 0; j < J; j++) {
    const y = -innerH / 2 + (j + 0.5) * pitch, f = Math.floor(j / FL);
    ib.add(pbox(c - 0.1, 0.045, c - 0.1), j % FL === 0 ? M.mid : M.dark, mx4(0, y - pitch / 2 + 0.03, 0));
    if (j % FL === 0) { ib.add(pbox(c - 0.06, 0.016, 0.016), M.neonSoft, mx4(0, y - pitch / 2 + 0.06, hc - 0.06)); ib.add(pbox(c - 0.06, 0.016, 0.016), M.neonSoft, mx4(0, y - pitch / 2 + 0.06, -hc + 0.06)); }
    ib.add(pbox(0.34, pitch, 0.34), M.dark, mx4(0, y, 0));
    for (let q = 0; q < 4; q++) {
      const phi = q * PI / 2, nx = Math.sin(phi), nz = Math.cos(phi), tx = Math.cos(phi), tz = -Math.sin(phi);
      for (let i = 0; i < m; i++) {
        if (R() > 0.72) continue;
        const u = -(c - 0.2) / 2 + (c - 0.2) / m * (i + 0.5), d = hc + 0.012;
        wins.push({ x: nx * d + tx * u, y, z: nz * d + tz * u, ry: phi, w: ww, h: wh, f });
      }
    }
  }
  // the core: a column of light, a bright heart, the centre's halo
  ib.add(new THREE.CylinderGeometry(0.035, 0.035, c - 0.1, 10), A.glow, mx4(0, 0, 0));
  ib.add(new THREE.SphereGeometry(0.09, 14, 10), M.hot, mx4(0, 0, 0));
  ib.flush(ic);
  sprite(b, M.halo, 0, yc, 0, 2.3);
  // its windows turn with it: they are the station's instanced windows, so their matrices follow the cube each frame
  const first = b.w.length;
  wins.forEach((w) => b.win(w.x, yc + w.y, w.z, w.ry, w.w, w.h, w.f, true));
  const m4 = new THREE.Matrix4(), qq = new THREE.Quaternion(), ee = new THREE.Euler(), pp = new V3(), sc = new V3();
  const place = (ang) => {
    const wm = b.wins; if (!wm) return;
    if (!wm.userData.moves) { wm.userData.moves = true; wm.frustumCulled = false; wm.instanceMatrix.setUsage(THREE.DynamicDrawUsage); }
    const ca = Math.cos(ang), sa = Math.sin(ang);
    wins.forEach((w, i) => {
      pp.set(w.x * ca + w.z * sa, yc + w.y, -w.x * sa + w.z * ca); ee.set(0, w.ry + ang, 0); qq.setFromEuler(ee); sc.set(w.w, w.h, 1);
      m4.compose(pp, qq, sc); wm.setMatrixAt(first + i, m4);
    });
    wm.instanceMatrix.needsUpdate = true;
  };
  const step = clock(b, [0.1, -0.06], [b.phase * 0.5, 0.7 + b.phase * 0.3]);
  b.anim.push((t) => step(t, (an) => { spin.rotation.y = an[0]; ic.rotation.y = an[1]; place(an[1]); }));
  b.top = yt + 0.44; b.bot = -2.05; b.foot = big ? 2.24 : 2.0;
}

/* ---------------- into u3d.js's table ---------------- */
const BUILD = { rift, tesseract };
function install() {
  const U = CO.U3;
  if (!U || !U.ok || !U.SKIN || !CO.ST || U.skinsD === '1') return;
  Object.keys(BUILD).forEach((k) => { U.SKIN[k] = BUILD[k]; });
  U.skinsD = '1';
  window.dispatchEvent(new Event('co3d-skins'));
}
if (CO.U3 && CO.ST) install(); else { window.addEventListener('co3d', install, { once: true }); window.addEventListener('co3d-skins', install, { once: true }); }
