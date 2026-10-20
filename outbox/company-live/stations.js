/* The seven stations, drawn again (the operator, 2026-10-20: "vzhled tech firem je nic moc ... uplne top brutalni
 * designy ... prvky nebo lode ze star wars nebo stargate"). Capital ships and gates in that spirit, none of them a
 * copy of a film's ship: a wedge dreadnought, a ring gate, a pyramid carrier, a ring habitat, a lancer, a citadel orb,
 * a monolith. Each keeps the station's rules: one deck per department, a deck's windows light while it works
 * (b.win, deck f), b.top / b.bot / b.foot frame it, b.busy makes it burn brighter.
 *
 * A module of its own, run after u3d.js: it puts its builders into u3d.js's own table (CO.U3.SKIN), so the Universe,
 * the previews and the station tiles all draw these, and nothing in u3d.js changes. The keys stay (a saved company
 * keeps its pick); the names change. It says so with the event co3d-skins. */
import * as THREE from 'three/webgpu';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

const CO = window.CO;
const NAMES = { tower: 'Dreadnought', dome: 'Gateway', pyramid: 'Pyramid Carrier', orbital: 'Ring Habitat', rocket: 'Lancer', vault: 'Citadel', stack: 'Monolith' };
const TS = 2.2;               // world units per tile of the hull's plating
const G = {}, T = {};         // geometries and textures, made once

/* ---------------- textures: plating, its lights, a gate's horizon, a soft glow ---------------- */
function canvas(w, h, draw) { const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h); return c; }
function rnd(seed) { let s = seed >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296; }; }
// The hull's plating, grey so a material's colour tints it: plates of slightly different tone, dark seams between
// them, small dark greebles; the same pattern's lights in a map of their own (lit by the material's emissive colour)
function plating() {
  if (T.plate) return T;
  const R = rnd(7), S = 512, rects = [];
  const split = (x, y, w, h, d) => {
    if (d > 4 || (w < 70 && h < 70) || (d > 1 && R() < 0.18)) { rects.push([x, y, w, h]); return; }
    if (w > h ? R() < 0.8 : R() < 0.2) { const k = Math.round(w * (0.3 + R() * 0.4)); split(x, y, k, h, d + 1); split(x + k, y, w - k, h, d + 1); }
    else { const k = Math.round(h * (0.3 + R() * 0.4)); split(x, y, w, k, d + 1); split(x, y + k, w, h - k, d + 1); }
  };
  split(0, 0, S, S, 0);
  const plate = canvas(S, S, (g) => {
    // light plates (the material's colour darkens them where a hull is darker): a texture is multiplied in, and
    // plates at mid grey left every hull a shade of slate under these scenes' light
    g.fillStyle = '#bcc5d0'; g.fillRect(0, 0, S, S);
    rects.forEach(([x, y, w, h]) => {
      const v = 196 + Math.round((R() - 0.5) * 36), tone = 'rgb(' + (v - 8) + ',' + v + ',' + Math.min(255, v + 10) + ')';
      g.fillStyle = tone; g.fillRect(x + 1, y + 1, w - 2, h - 2);
      if (R() < 0.35) { g.fillStyle = 'rgba(40,48,60,.45)'; g.fillRect(x + 6, y + 6, Math.max(6, (w - 12) * R()), Math.max(4, 8 * R())); }
      if (R() < 0.25) { g.fillStyle = 'rgba(255,255,255,.08)'; g.fillRect(x + 2, y + 2, w - 4, 3); }
    });
    g.strokeStyle = 'rgba(30,36,46,.85)'; g.lineWidth = 2;
    rects.forEach(([x, y, w, h]) => g.strokeRect(x + 0.5, y + 0.5, w - 1, h - 1));
    for (let i = 0; i < 90; i++) { g.fillStyle = 'rgba(28,34,44,' + (0.4 + R() * 0.4) + ')'; g.fillRect(R() * S, R() * S, 3 + R() * 14, 2 + R() * 6); }
  });
  const lights = canvas(S, S, (g) => {
    g.fillStyle = '#000'; g.fillRect(0, 0, S, S);
    for (let i = 0; i < 70; i++) {
      const x = R() * S, y = R() * S, n = 1 + Math.floor(R() * 6), a = 0.5 + R() * 0.5;
      g.fillStyle = 'rgba(255,255,255,' + a + ')';
      for (let k = 0; k < n; k++) g.fillRect(x + k * 6, y, 3, 2);
    }
  });
  const tex = (c) => { const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.wrapS = t.wrapT = THREE.RepeatWrapping; t.anisotropy = 8; return t; };
  T.plate = tex(plate); T.lights = tex(lights);
  return T;
}
function horizonTex() {
  if (T.horizon) return T.horizon;
  const S = 512, c = canvas(S, S, (g) => {
    const m = S / 2, gr = g.createRadialGradient(m, m, 0, m, m, m);
    gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.25, 'rgba(190,235,255,.85)'); gr.addColorStop(0.75, 'rgba(90,170,255,.55)'); gr.addColorStop(0.97, 'rgba(160,220,255,.9)'); gr.addColorStop(1, 'rgba(160,220,255,0)');
    g.fillStyle = gr; g.fillRect(0, 0, S, S);
    // ripples: rings a little off round, brighter and darker in turn
    const R = rnd(31);
    for (let i = 0; i < 26; i++) {
      const r = 10 + i * 9.5 + R() * 5;
      g.strokeStyle = 'rgba(255,255,255,' + (0.05 + R() * 0.16) + ')'; g.lineWidth = 2 + R() * 5;
      g.beginPath(); for (let a = 0; a <= 64; a++) { const t = a / 64 * Math.PI * 2, rr = r * (1 + 0.035 * Math.sin(t * 3 + i) + 0.02 * Math.sin(t * 7 - i * 2)); g.lineTo(m + Math.cos(t) * rr, m + Math.sin(t) * rr); } g.stroke();
    }
  });
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return (T.horizon = t);
}
function softTex() {
  if (T.soft) return T.soft;
  const c = canvas(128, 128, (g) => { const gr = g.createRadialGradient(64, 64, 0, 64, 64, 64); gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.35, 'rgba(255,255,255,.35)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, 128, 128); });
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return (T.soft = t);
}

/* ---------------- materials: one set per colour, kept on u3d.js's own colour set (A.ns), so release() keeps them ---------------- */
const ENGINE = 0x8fdcff;
function mats(A) {
  if (A.ns) return A.ns;
  const c = A.c, P = plating(), tint = (hex, k) => new THREE.Color(hex).lerp(c, k);
  const plate = (color, rough, metal, glow) => new THREE.MeshStandardMaterial({ color, map: P.plate, roughness: rough, metalness: metal, emissive: c.clone(), emissiveMap: P.lights, emissiveIntensity: glow });
  // Matte, as the stations before them: these scenes have nothing for a metal to mirror, so metal reads as black
  A.ns = {
    light: plate(tint(0xf2f5fa, 0.04), 0.62, 0.1, 1.25),          // the capital ships' pale armour
    mid: plate(tint(0xaab4c2, 0.07), 0.6, 0.12, 0.9),
    dark: plate(tint(0x56616f, 0.1), 0.55, 0.15, 1.1),
    black: new THREE.MeshStandardMaterial({ color: 0x10151d, roughness: 0.22, metalness: 0.35 }),
    metal: new THREE.MeshStandardMaterial({ color: tint(0x8893a3, 0.06), roughness: 0.45, metalness: 0.25 }),
    bronze: plate(new THREE.Color(0xe0cfa8).lerp(c, 0.1), 0.5, 0.2, 1.1),
    neon: new THREE.MeshStandardMaterial({ color: 0x000000, emissive: c.clone(), emissiveIntensity: 2.2, roughness: 1 }),
    neonSoft: new THREE.MeshStandardMaterial({ color: 0x000000, emissive: c.clone(), emissiveIntensity: 0.9, roughness: 1 }),
    glass: new THREE.MeshStandardMaterial({ color: 0x0a1622, roughness: 0.08, metalness: 0.4, emissive: c.clone(), emissiveIntensity: 0.25 }),
    core: new THREE.MeshBasicMaterial({ color: new THREE.Color(ENGINE).multiplyScalar(2.6) }),
    // an engine's plume: faint, a shimmer behind the nozzle (brighter, it read as a solid tube under the bloom)
    plume: new THREE.MeshBasicMaterial({ color: new THREE.Color(ENGINE).multiplyScalar(0.9), transparent: true, opacity: 0.08, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }),
    hot: new THREE.MeshBasicMaterial({ color: c.clone().multiplyScalar(3.2) }),
    halo: new THREE.SpriteMaterial({ map: softTex(), color: c.clone(), transparent: true, opacity: 0.55, blending: THREE.AdditiveBlending, depthWrite: false }),
    engHalo: new THREE.SpriteMaterial({ map: softTex(), color: new THREE.Color(ENGINE), transparent: true, opacity: 0.45, blending: THREE.AdditiveBlending, depthWrite: false }),
    // a gate's horizon: water-blue ripples (a little of the station's colour in them), never a white blot under the bloom
    horizon: new THREE.MeshBasicMaterial({ map: horizonTex(), color: new THREE.Color(0x3d8fe0).lerp(c, 0.22).multiplyScalar(0.62), transparent: true, opacity: 0.85, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }),
    horizon2: new THREE.MeshBasicMaterial({ map: horizonTex(), color: new THREE.Color(0x8fd0ff).lerp(c, 0.3).multiplyScalar(0.35), transparent: true, opacity: 0.6, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }),
    deep: new THREE.MeshBasicMaterial({ color: 0x061a33, side: THREE.DoubleSide })
  };
  return A.ns;
}

/* ---------------- geometry: plated boxes, wedges, rings, all with UVs in plating tiles ---------------- */
const key = (p, v) => p + v.map((x) => (+x).toFixed(3)).join(',');
// a box whose plating keeps its size whatever the box's size (BoxGeometry's faces are 0..1 each, so they are scaled)
function pbox(w, h, d) {
  const k = key('pb', [w, h, d]); if (G[k]) return G[k];
  const g = new THREE.BoxGeometry(w, h, d), uv = g.attributes.uv, span = [[d, h], [d, h], [w, d], [w, d], [w, h], [w, h]];
  for (let f = 0; f < 6; f++) for (let i = 0; i < 4; i++) { const j = f * 4 + i; uv.setXY(j, uv.getX(j) * span[f][0] / TS, uv.getY(j) * span[f][1] / TS); }
  return (G[k] = g);
}
function scaleUV(g, k) { const uv = g.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * k, uv.getY(i) * k); return g; }
// a shape in the x-z plane raised to height h, its edges chamfered by bev (ExtrudeGeometry, turned so it stands up)
function slab(k, shape, h, bev) {
  if (G[k]) return G[k];
  const g = new THREE.ExtrudeGeometry(shape, { depth: Math.max(0.001, h - 2 * bev), bevelEnabled: bev > 0, bevelThickness: bev, bevelSize: bev, bevelSegments: 2, curveSegments: 24 });
  g.rotateX(-Math.PI / 2); g.translate(0, bev, 0);
  return (G[k] = scaleUV(g, 1 / TS));
}
function cyl(rt, rb, h, seg, open) { const k = key('cy', [rt, rb, h, seg, open ? 1 : 0]); return G[k] || (G[k] = scaleUV(new THREE.CylinderGeometry(rt, rb, h, seg, 1, !!open), 1)); }
function torus(r, t, rs, ts, arc) { const k = key('to', [r, t, rs, ts, arc || 6.2832]); if (G[k]) return G[k]; const g = new THREE.TorusGeometry(r, t, rs, ts, arc || Math.PI * 2); const uv = g.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * Math.PI * 2 * r / TS, uv.getY(i) * Math.PI * 2 * t / TS); return (G[k] = g); }
function sphere(r) { const k = key('sp', [r]); if (G[k]) return G[k]; const g = new THREE.SphereGeometry(r, 48, 32); const uv = g.attributes.uv; for (let i = 0; i < uv.count; i++) uv.setXY(i, uv.getX(i) * Math.PI * 2 * r / TS, uv.getY(i) * Math.PI * r / TS); return (G[k] = g); }

// parts placed on a station (b.g); dyn: it moves, never merged
function put(b, geom, mat, x, y, z, o) {
  const m = new THREE.Mesh(geom, mat); m.position.set(x, y, z);
  if (o) { if (o.rx) m.rotation.x = o.rx; if (o.ry) m.rotation.y = o.ry; if (o.rz) m.rotation.z = o.rz; if (o.s) m.scale.set(o.s[0], o.s[1], o.s[2]); if (o.dyn) m.userData.dyn = true; }
  (o && o.to ? o.to : b.g).add(m); return m;
}
const box = (b, w, h, d, x, y, z, mat, o) => put(b, pbox(w, h, d), mat, x, y, z, o);
// windows along a box's faces: rows of lit slots on the faces named (+x -x +z -z), deck f
function wins(b, f, cx, y, cz, w, d, rows, rowH, step, lit, faces) {
  const R = b.R, ww = Math.min(0.16, step * 0.55), wh = Math.min(0.07, rowH * 0.42);
  const run = (len, place) => { const m = Math.max(1, Math.floor((len - 0.12) / step)), s = len / m; for (let i = 0; i < m; i++) place(-len / 2 + s * (i + 0.5)); };
  for (let r = 0; r < rows; r++) {
    const yy = y + (r - (rows - 1) / 2) * rowH;
    (faces || '+x-x+z-z').match(/[+-][xz]/g).forEach((fc) => {
      const s = fc[0] === '+' ? 1 : -1;
      if (fc[1] === 'z') run(w, (u) => b.win(cx + u, yy, cz + s * (d / 2 + 0.012), s > 0 ? 0 : Math.PI, ww, wh, f, R() < lit));
      else run(d, (u) => b.win(cx + s * (w / 2 + 0.012), yy, cz + u, s * Math.PI / 2, ww, wh, f, R() < lit));
    });
  }
}
// an engine pointing along +z rotated by ry: housing, nozzle, glowing core and a plume that burns harder while busy
function engine(b, M, x, y, z, r, ry, len, to) {
  const g = new THREE.Group(); g.position.set(x, y, z); g.rotation.y = ry || 0; (to || b.g).add(g);
  put(b, cyl(r * 1.08, r * 1.12, r * 1.1, 24), M.metal, 0, 0, r * 0.2, { rx: Math.PI / 2, to: g });
  put(b, cyl(r, r * 0.78, r * 0.7, 24, true), M.dark, 0, 0, -r * 0.65, { rx: Math.PI / 2, to: g });
  put(b, cyl(r * 0.82, r * 0.82, 0.02, 24), M.core, 0, 0, -r * 0.98, { rx: Math.PI / 2, to: g });
  const plume = put(b, cyl(r * 0.2, r * 0.75, 1, 20, true), M.plume, 0, 0, 0, { rx: Math.PI / 2, dyn: true, to: g });
  const halo = new THREE.Sprite(M.engHalo); halo.position.set(0, 0, -r * 1.05); halo.userData.dyn = true; g.add(halo);
  const L = (len || r * 3.2) * 0.6, ph = b.phase + x * 3 + y;
  // (the halo tight round the nozzle: wide, from in front it read as a pale balloon behind the ship)
  b.anim.push((t) => { const k = (b.busy ? 1.35 : 1) * (1 + 0.08 * Math.sin(t * 19 + ph)); plume.scale.set(1, L * k, 1); plume.position.z = -r - L * k / 2; halo.scale.setScalar(r * 2.1 * k); });
  return g;
}
// surface detail: small blocks scattered over a deck at height y wherever inside(x, z) holds (sizes in steps of
// 0.02, so a few dozen box shapes serve every station); the station's bake merges them per material
function greebles(b, mats, y, x0, x1, z0, z1, count, inside, seed) {
  const R = rnd(seed || 5), q = (v) => Math.max(0.04, Math.round(v / 0.02) * 0.02);
  for (let i = 0, tries = 0; i < count && tries < count * 8; tries++) {
    const x = x0 + (x1 - x0) * R(), z = z0 + (z1 - z0) * R(); if (inside && !inside(x, z)) continue;
    const w = q(0.06 + R() * 0.24), d = q(0.06 + R() * 0.24), h = q(0.03 + R() * R() * 0.16);
    box(b, w, h, d, x, y + h / 2, z, mats[i % mats.length], R() < 0.5 ? null : { ry: Math.PI / 2 }); i++;
  }
}
function sprite(b, mat, x, y, z, s) { const sp = new THREE.Sprite(mat); sp.position.set(x, y, z); sp.scale.setScalar(s); sp.userData.dyn = true; b.g.add(sp); return sp; }
// a few small craft on a slow circuit round the station, merged into two meshes that turn as one
function escorts(b, M, r, y, count, size) {
  // (uv kept: the hull's material is plated, and a geometry without uv makes its shader warn)
  const hulls = [], glows = [], flat = (g) => (g.index ? g.toNonIndexed() : g);
  for (let i = 0; i < count; i++) {
    // on the circuit at angle a, its nose along the way the group turns (rotation.y falling: the angle rises)
    const a = i / count * Math.PI * 2, x = Math.cos(a) * r, z = Math.sin(a) * r, yy = y + (i % 2 ? 0.25 : -0.2), dir = Math.PI - a;
    const s = size * (0.85 + (i % 3) * 0.12);
    // a delta: a flat wedge body with swept fins (its nose at -z once laid flat), an engine glow at its tail
    const sh = new THREE.Shape(); sh.moveTo(0, 0.9 * s); sh.lineTo(0.55 * s, -0.5 * s); sh.lineTo(0.18 * s, -0.36 * s); sh.lineTo(0, -0.5 * s); sh.lineTo(-0.18 * s, -0.36 * s); sh.lineTo(-0.55 * s, -0.5 * s); sh.closePath();
    const body = new THREE.ExtrudeGeometry(sh, { depth: 0.08 * s, bevelEnabled: true, bevelThickness: 0.03 * s, bevelSize: 0.03 * s, bevelSegments: 1 });
    body.rotateX(-Math.PI / 2); body.rotateY(dir); body.translate(x, yy, z); hulls.push(flat(body));
    const gl = new THREE.SphereGeometry(0.11 * s, 10, 6);
    gl.translate(x + Math.sin(dir) * 0.52 * s, yy + 0.04 * s, z + Math.cos(dir) * 0.52 * s); glows.push(flat(gl));
  }
  const g = new THREE.Group(); g.userData.dyn = true; b.g.add(g);
  g.add(new THREE.Mesh(mergeGeometries(hulls, false), M.mid), new THREE.Mesh(mergeGeometries(glows, false), M.core));
  b.anim.push((t) => { g.rotation.y = -t * 0.22 - b.phase; });
  return g;
}

/* ---------------- 1. Dreadnought: a wedge of pale armour, its decks stepping up to the bridge ---------------- */
function dreadnought(b, n) {
  // (as long as the stations before it were wide: longer, it ran into its neighbours on an orbit)
  const A = b.A, M = mats(A), L = 4.5 + 0.22 * n, W = L * 0.6, H = 0.38;
  const tri = (len, wid) => { const s = new THREE.Shape(); s.moveTo(0, len * 0.62); s.lineTo(wid / 2, -len * 0.38); s.lineTo(-wid / 2, -len * 0.38); s.closePath(); return s; };
  // the hull: a wide wedge, a narrower one on it, a keel wedge under it; their noses forward (+z after the turn)
  const z0 = -0.05 * L;
  put(b, slab(key('dnA', [L, W]), tri(L, W), H, 0.07), M.light, 0, -H, z0, { ry: Math.PI });
  put(b, slab(key('dnB', [L, W]), tri(L * 0.82, W * 0.62), H * 0.7, 0.05), M.light, 0, 0, z0 - L * 0.06, { ry: Math.PI });
  put(b, slab(key('dnK', [L, W]), tri(L * 0.9, W * 0.5), H * 0.8, 0.05), M.mid, 0, -H * 1.75, z0 + L * 0.02, { ry: Math.PI });
  // (the wedges are turned half round: the nose at +z, the broad stern at -z)
  const back = z0 - L * 0.38, nose = z0 + L * 0.62, side = (x0, z0_, x1, z1_, y, mat) => {
    const dx = x1 - x0, dz = z1_ - z0_, len = Math.hypot(dx, dz);
    box(b, 0.035, 0.035, len, (x0 + x1) / 2, y, (z0_ + z1_) / 2, mat, { ry: Math.atan2(dx, dz) });
  };
  // the trench lines along both flanks and either side of the spine
  for (const s of [1, -1]) { side(s * W / 2 * 0.985, back, 0, nose, -H * 0.5, M.neon); side(s * W * 0.31, back + L * 0.06, 0, nose - L * 0.12, H * 0.36, M.neonSoft); }
  // the hangar's mouth, glowing under the belly
  box(b, W * 0.16, 0.03, L * 0.22, 0, -H * 1.8 - 0.012, z0 + L * 0.02, M.hot);
  // the armour's surface: blocks over the broad deck either side of the spine, and along the spine itself
  const half = (z, nz, len, hw) => hw * (nz - z) / len, nS = z0 - L * 0.06 + 0.62 * 0.82 * L;
  greebles(b, [M.mid, M.light, M.mid, M.dark], 0, -W / 2, W / 2, back + 0.15, nose - 0.4, 70,
    (x, z) => Math.abs(x) < half(z, nose, L, W / 2) * 0.86 && Math.abs(x) > half(z, nS, 0.82 * L, 0.31 * W) + 0.1, 11);
  greebles(b, [M.mid, M.light], H * 0.7, -W * 0.3, W * 0.3, z0 + L * 0.12, nS - 0.4, 22,
    (x, z) => Math.abs(x) < half(z, nS, 0.82 * L, 0.31 * W) * 0.7, 12);
  // the decks: blocks stepping up and back towards the bridge at the stern, a row of windows on each
  const dz = Math.min(0.62, 2.6 / Math.max(1, n));
  let y = H * 0.7, zc = z0 - L * 0.02, w = W * 0.42, d = L * 0.36;
  for (let f = 0; f < n; f++) {
    const hh = 0.24;
    box(b, w, hh, d, 0, y + hh / 2, zc, f % 2 ? M.mid : M.light);
    box(b, w + 0.04, 0.03, d + 0.04, 0, y + hh, zc, M.metal);
    wins(b, f, 0, y + hh * 0.52, zc, w, d, 1, hh, 0.17, 0.7, '+x-x+z');
    y += hh; zc -= dz * 0.32; w *= 0.88; d *= 0.84;
  }
  // the bridge: a neck, a wide flat head with a band of glass across its front, two sensor globes, masts
  const bz = zc - d * 0.15, nh = 0.5;
  box(b, w * 0.32, nh, d * 0.32, 0, y + nh / 2, bz, M.mid);
  const hy = y + nh + 0.13, hw = Math.max(1.1, W * 0.34);
  box(b, hw, 0.26, 0.5, 0, hy, bz, M.light);
  box(b, hw * 0.92, 0.07, 0.02, 0, hy + 0.02, bz + 0.26, M.glass);
  for (let k = -3; k <= 3; k++) b.win(k * hw * 0.12, hy + 0.02, bz + 0.27, 0, hw * 0.08, 0.04, Math.max(0, n - 1), true);
  for (const s of [1, -1]) {
    put(b, sphere(0.15), M.light, s * hw * 0.3, hy + 0.27, bz - 0.05);
    box(b, 0.03, 0.42, 0.03, s * hw * 0.42, hy + 0.32, bz - 0.12, M.metal);
  }
  b.beacon(0, hy + 0.42, bz - 0.1, 0.05);
  // the engines across the stern: three great ones, four small, all burning aft (-z)
  const sz = back - 0.02;
  box(b, W * 0.88, H * 1.2, 0.3, 0, -H * 0.85, sz + 0.05, M.mid);
  [[-W * 0.22, 0.34], [0, 0.4], [W * 0.22, 0.34]].forEach(([x, r]) => engine(b, M, x, -H * 0.4, sz - r * 0.6, r, 0, 1.2 + r * 2));
  [[-W * 0.36, 0.16], [-W * 0.11, 0.15], [W * 0.11, 0.15], [W * 0.36, 0.16]].forEach(([x, r]) => engine(b, M, x, -H * 1.35, sz - 0.12, r, 0, 0.8));
  escorts(b, M, L * 0.62, -0.2, 3, 0.36);
  b.top = hy + 0.6; b.bot = -H * 2.1; b.foot = L * 0.5;
}

/* ---------------- 2. Gateway: a ring gate on a stepped dais, its horizon rippling ---------------- */
function gateway(b, n) {
  const A = b.A, M = mats(A), s0 = 3.0 + 0.22 * n, th = 0.3;
  // the dais: a ziggurat, one tier a deck, windows round each; a ramp up the front
  let y = 0, s = s0;
  for (let f = 0; f < n; f++) {
    box(b, s, th, s, 0, y + th / 2, 0, f % 2 ? M.light : M.mid);
    box(b, s + 0.03, 0.025, s + 0.03, 0, y + th - 0.005, 0, M.neonSoft);
    wins(b, f, 0, y + th * 0.5, 0, s, s, 1, th, 0.24, 0.6);
    const ns = s - Math.min(0.32, (s0 - 1.9) / Math.max(1, n)), lo = ns / 2 + 0.06, hi = s / 2 - 0.06;
    // the ledge each tier leaves round the next: machinery on it, none on the ramp's line
    if (f < n - 1 || n === 1) greebles(b, [M.dark, M.mid], y + th, -hi, hi, -hi, hi, 10 + Math.round(s * 2),
      (x, z) => (Math.abs(x) > lo || Math.abs(z) > lo) && !(Math.abs(x) < 0.45 && z > 0), 20 + f);
    y += th; s = ns;
  }
  // the ramp: from the deck in front of the dais up to its top tier's front edge, lit along both sides
  const top = y, run = s0 / 2 + 0.75 - s / 2, rl = Math.hypot(top, run), ra = Math.atan2(top, run), rz = s / 2 + run / 2;
  box(b, 0.62, 0.05, rl, 0, top / 2 + 0.02, rz, M.light, { rx: ra });
  for (const sx of [1, -1]) box(b, 0.03, 0.04, rl, sx * 0.32, top / 2 + 0.05, rz, M.neon, { rx: ra });
  // under it, the keel and its engines
  put(b, cyl(s0 * 0.42, s0 * 0.2, 0.9, 6), M.dark, 0, -0.45, 0);
  engine(b, M, 0, -0.95, 0, 0.3, 0, 0.9).rotation.x = -Math.PI / 2;
  // the gate: a heavy ring standing on the dais, an inner track, nine chevrons, the horizon inside
  const R = 1.25 + 0.06 * n, gy = top + R + 0.12, g = new THREE.Group(); g.position.set(0, gy, -s * 0.12); b.g.add(g);
  put(b, torus(R, 0.2, 10, 72), M.dark, 0, 0, 0, { to: g });
  put(b, torus(R - 0.12, 0.07, 8, 72), M.metal, 0, 0, 0.09, { to: g });
  put(b, torus(R + 0.17, 0.035, 6, 72), M.neonSoft, 0, 0, 0, { to: g });
  for (let k = 0; k < 9; k++) {
    const a = Math.PI / 2 + k / 9 * Math.PI * 2, x = Math.cos(a) * (R + 0.05), yy = Math.sin(a) * (R + 0.05);
    put(b, pbox(0.2, 0.26, 0.5), M.metal, x, yy, 0, { rz: a - Math.PI / 2, to: g });
    put(b, new THREE.ConeGeometry(0.09, 0.2, 3), M.neon, x * 0.985, yy * 0.985, 0.27, { rz: a + Math.PI / 2, to: g });
  }
  // its feet, and four obelisks on the lowest tier's corners framing it
  for (const sx of [1, -1]) box(b, 0.36, 0.4, 0.62, sx * R * 0.62, top + 0.2, -s * 0.12, M.mid);
  const oh = 1.3 + 0.1 * n, oc = s0 / 2 - 0.28;
  for (const [sx, sz] of [[1, 1], [1, -1], [-1, 1], [-1, -1]]) {
    box(b, 0.26, oh, 0.26, sx * oc, th + oh / 2, sz * oc, M.light);
    box(b, 0.27, 0.05, 0.27, sx * oc, th + oh * 0.82, sz * oc, M.neon);
    put(b, new THREE.ConeGeometry(0.19, 0.3, 4), M.light, sx * oc, th + oh + 0.15, sz * oc, { ry: Math.PI / 4 });
    b.beacon(sx * oc, th + oh + 0.34, sz * oc, 0.05);
  }
  // the dialler: a pedestal with a glowing dome, at the ramp's head
  put(b, cyl(0.16, 0.2, 0.3, 16), M.metal, s * 0.3, top + 0.15, s * 0.3);
  put(b, new THREE.SphereGeometry(0.11, 16, 8, 0, Math.PI * 2, 0, Math.PI / 2), M.hot, s * 0.3, top + 0.3, s * 0.3);
  // the horizon: a deep blue pool, ripples over it turning against each other, a soft light thrown forward
  put(b, new THREE.CircleGeometry(R - 0.1, 64), M.deep, 0, 0, -0.01, { to: g });
  const h1 = put(b, new THREE.CircleGeometry(R - 0.1, 64), M.horizon, 0, 0, 0.02, { dyn: true, to: g });
  const h2 = put(b, new THREE.CircleGeometry(R - 0.1, 64), M.horizon2, 0, 0, 0.05, { dyn: true, to: g });
  const glow = new THREE.Sprite(M.engHalo); glow.scale.setScalar(R * 2.6); glow.position.z = 0.25; glow.userData.dyn = true; g.add(glow);
  b.anim.push((t) => {
    h1.rotation.z = t * 0.35 + b.phase; h2.rotation.z = -t * 0.55;
    const k = 1 + 0.03 * Math.sin(t * 2.3 + b.phase); h2.scale.set(k, k, 1);
    glow.scale.setScalar(R * (b.busy ? 3 : 2.6) * (1 + 0.04 * Math.sin(t * 2)));
  });
  b.top = gy + R + 0.3; b.bot = -1.5; b.foot = s0 / 2 + 0.3;
}

/* ---------------- 3. Pyramid Carrier: a stepped pyramid inside a ring of armoured petals ---------------- */
function pyramidCarrier(b, n) {
  const A = b.A, M = mats(A), Ro = 2.6 + 0.16 * n, Ri = Ro * 0.6, hh = 0.36, seg = 8;
  for (let k = 0; k < seg; k++) {
    const a0 = k / seg * Math.PI * 2 + 0.06, a1 = (k + 1) / seg * Math.PI * 2 - 0.06, sh = new THREE.Shape();
    sh.absarc(0, 0, Ro, a0, a1, false); sh.absarc(0, 0, Ri, a1, a0, true); sh.closePath();
    put(b, slab(key('pcP', [Ro, k]), sh, hh, 0.05), M.bronze, 0, -hh * 0.6, 0);
    const am = (a0 + a1) / 2;
    // a light on each petal's outer edge and an engine slot on the back four
    box(b, 0.05, 0.05, Ro * 0.62, Math.cos(am) * (Ro - 0.03), hh * 0.4 - 0.02, -Math.sin(am) * (Ro - 0.03), M.neon, { ry: am });
    // (a petal at shape angle am stands at (cos am, -sin am) once laid flat; an engine there burns outward)
    if (k >= 4 && k <= 7) engine(b, M, Math.cos(am) * (Ro + 0.05), -hh * 0.3, -Math.sin(am) * (Ro + 0.05), 0.17, am - Math.PI / 2, 0.7);
  }
  put(b, torus(Ri * 0.98, 0.05, 6, 64), M.neonSoft, 0, hh * 0.4, 0, { rx: Math.PI / 2 });
  // the petals' backs: machinery, clear of the gaps between them
  greebles(b, [M.bronze, M.dark, M.mid], hh * 0.4, -Ro, Ro, -Ro, Ro, 70, (x, z) => {
    const r = Math.hypot(x, z), a = ((Math.atan2(-z, x) % (Math.PI / 4)) + Math.PI / 4) % (Math.PI / 4);
    return r > Ri + 0.15 && r < Ro - 0.2 && a > 0.12 && a < Math.PI / 4 - 0.12;
  }, 31);
  // the pyramid: one tier a deck, its windows on the risers, a capstone burning in the station's colour
  const base = Ri * 1.42, tierH = Math.min(0.42, 2.4 / Math.max(2, n)); let y = -0.05, w = base;
  for (let f = 0; f < n; f++) {
    box(b, w, tierH, w, 0, y + tierH / 2, 0, M.bronze, { ry: Math.PI / 4 });
    const p = put(b, pbox(w + 0.03, 0.025, w + 0.03), M.neonSoft, 0, y + tierH, 0, { ry: Math.PI / 4 }); void p;
    // windows on the four risers (the tier is turned 45 degrees)
    for (let q = 0; q < 4; q++) {
      const a = Math.PI / 4 + q * Math.PI / 2, m = Math.max(2, Math.floor(w / 0.24));
      for (let i = 0; i < m; i++) { const u = (-w / 2 + w / m * (i + 0.5)), x = Math.cos(a) * (w / 2 + 0.012), z = -Math.sin(a) * (w / 2 + 0.012), px = x + Math.sin(a) * u, pz = z + Math.cos(a) * u; b.win(px, y + tierH * 0.5, pz, a + Math.PI / 2, 0.11, Math.min(0.08, tierH * 0.35), f, b.R() < 0.65); }
    }
    y += tierH; w -= (base - 0.55) / (n + 1.2);
  }
  const cap = Math.max(0.5, w), ch = cap * 0.75;
  put(b, new THREE.ConeGeometry(cap * 0.72, ch, 4), M.bronze, 0, y + ch / 2, 0);
  put(b, new THREE.ConeGeometry(cap * 0.24, ch * 0.32, 4), M.hot, 0, y + ch * 0.84, 0);
  sprite(b, M.halo, 0, y + ch * 0.9, 0, 1.6);
  b.beacon(0, y + ch + 0.08, 0, 0.06);
  // underneath, an inverted pyramid keel
  put(b, new THREE.ConeGeometry(Ri * 0.9, 1.3, 4), M.dark, 0, -hh * 0.6 - 0.65, 0, { rx: Math.PI, ry: Math.PI / 4 });
  b.top = y + ch + 0.25; b.bot = -hh * 0.6 - 1.4; b.foot = Ro + 0.1;
}

/* ---------------- 4. Ring Habitat: a wheel turning round a spindle of decks ---------------- */
function ringHabitat(b, n) {
  const A = b.A, M = mats(A), R = 2.5 + 0.14 * n, rs = 0.5, dh = 0.34;
  // the spindle: a deck a drum, windows round each, a collar between
  let y = -(n * dh) / 2;
  const y0 = y;
  for (let f = 0; f < n; f++) {
    put(b, cyl(rs, rs, dh - 0.05, 24), f % 2 ? M.mid : M.light, 0, y + dh / 2, 0);
    put(b, cyl(rs + 0.06, rs + 0.06, 0.05, 24), M.metal, 0, y + dh, 0);
    b.ringWins(f, rs, y + dh / 2, 0.08, 0.2, 0.65, 0.09);
    y += dh;
  }
  // its ends: a dome and a mast above, a docking spire and the engine below
  put(b, new THREE.SphereGeometry(rs * 0.9, 24, 12, 0, Math.PI * 2, 0, Math.PI / 2), M.light, 0, y, 0);
  put(b, cyl(0.03, 0.05, 1.1, 8), M.metal, 0, y + 0.85, 0);
  b.beacon(0, y + 1.42, 0, 0.06);
  put(b, cyl(rs * 0.9, rs * 0.4, 0.8, 16), M.dark, 0, y0 - 0.4, 0);
  engine(b, M, 0, y0 - 0.85, 0, 0.26, 0, 1.0).rotation.x = -Math.PI / 2;
  // the wheel, its spokes and the hub collar they hang from, turning as one; habitation lights in its plating
  const wheel = new THREE.Group(); wheel.userData.dyn = true; b.g.add(wheel);
  const wy = 0.05;
  put(b, torus(R, 0.3, 14, 96), M.light, 0, wy, 0, { rx: Math.PI / 2, to: wheel });
  put(b, torus(R + 0.31, 0.03, 6, 120), M.neon, 0, wy, 0, { rx: Math.PI / 2, to: wheel });
  put(b, torus(R - 0.31, 0.03, 6, 120), M.neonSoft, 0, wy, 0, { rx: Math.PI / 2, to: wheel });
  put(b, cyl(rs + 0.2, rs + 0.2, 0.3, 24), M.mid, 0, wy, 0, { to: wheel });
  const spokes = [];
  for (let k = 0; k < 6; k++) {
    const a = k / 6 * Math.PI * 2, g = new THREE.CylinderGeometry(0.06, 0.06, R - rs - 0.4, 8);
    g.rotateZ(Math.PI / 2); g.translate((R + rs) / 2, wy, 0); g.rotateY(a); spokes.push(g.toNonIndexed());
  }
  put(b, scaleUV(mergeGeometries(spokes, false), 0.4), M.metal, 0, 0, 0, { to: wheel });
  // docked on the wheel: six modules on its rim
  for (let k = 0; k < 6; k++) { const a = (k + 0.5) / 6 * Math.PI * 2; put(b, pbox(0.42, 0.42, 0.42), M.mid, Math.cos(a) * R, wy + 0.32, Math.sin(a) * R, { ry: -a, to: wheel }); }
  b.anim.push((t) => { wheel.rotation.y = t * (b.busy ? 0.16 : 0.09) + b.phase; });
  b.top = y + 1.6; b.bot = y0 - 1.4; b.foot = R + 0.4;
}

/* ---------------- 5. Lancer: a spine with accelerator rings and its lance of light ---------------- */
function lancer(b, n) {
  const A = b.A, M = mats(A), L = 4.8 + 0.24 * n, r = 0.38, zt = L / 2;
  // the spine, its prow, the rings that drive the shot down it
  put(b, cyl(r, r * 1.05, L, 8), M.mid, 0, 0, 0, { rx: Math.PI / 2, ry: Math.PI / 8 });
  put(b, new THREE.ConeGeometry(r, 1.2, 8), M.light, 0, 0, zt + 0.6, { rx: Math.PI / 2 });
  const rings = [];
  for (let k = 0; k < 6; k++) {
    const z = zt - 0.35 - k * 0.42;
    put(b, torus(r + 0.12, 0.08, 8, 32), M.dark, 0, 0, z);
    rings.push(put(b, torus(r + 0.13, 0.03, 6, 32), M.neon.clone(), 0, 0, z + 0.06, { dyn: true }));
  }
  // the hull round the spine's back half: two armoured flanks and the decks along its top
  for (const s of [1, -1]) {
    // (a shape's +y lies at -z once laid flat: these run from the stern, -0.42 L, to just past the middle)
    const sh = new THREE.Shape(); sh.moveTo(0, L * 0.42); sh.lineTo(s * 1.15, L * 0.36); sh.lineTo(s * 0.9, -L * 0.08); sh.lineTo(0, -L * 0.18); sh.closePath();
    put(b, slab(key('lnF', [L, s]), sh, 0.28, 0.05), M.light, 0, -0.14, 0);
    box(b, 0.04, 0.04, L * 0.44, s * 1.1, 0.05, -L * 0.16, M.neon, { ry: s * -0.05 });
    greebles(b, [M.mid, M.dark], 0.14, s > 0 ? 0.55 : -0.95, s > 0 ? 0.95 : -0.55, -L * 0.38, L * 0.02, 18, null, 40 + s);
  }
  const dz = Math.min(0.55, (L * 0.5) / Math.max(1, n));
  for (let f = 0; f < n; f++) {
    const z = -L * 0.36 + f * dz, hh = 0.26, w = 0.8 - f * 0.03, d = dz * 0.86;
    box(b, w, hh, d, 0, r + hh / 2 - 0.05, z + d / 2, f % 2 ? M.mid : M.light);
    wins(b, f, 0, r + hh * 0.5 - 0.05, z + d / 2, w, d, 1, hh, 0.16, 0.65, '+x-x');
  }
  // the bridge tower at the back, its glass toward the prow
  const tz = -L * 0.4, ty = r + 0.24;
  box(b, 0.5, 0.7, 0.55, 0, ty + 0.35, tz, M.light);
  box(b, 0.9, 0.22, 0.42, 0, ty + 0.8, tz + 0.04, M.mid);
  box(b, 0.8, 0.06, 0.02, 0, ty + 0.8, tz + 0.26, M.glass);
  b.beacon(0, ty + 1.05, tz, 0.05);
  // engines: four round the stern
  for (const [x, y] of [[0.45, 0.3], [-0.45, 0.3], [0.45, -0.3], [-0.45, -0.3]]) engine(b, M, x, y, -zt - 0.15, 0.26, 0, 1.3);
  // the lance: a core and a sheath of light out of the prow, a bolt running down it
  const zb = zt + 1.15, bl = L * 0.7, beam = new THREE.Group(); beam.userData.dyn = true; b.g.add(beam);
  const core = put(b, cyl(0.035, 0.035, 1, 8, true), M.hot, 0, 0, 0, { rx: Math.PI / 2, to: beam });
  const sheath = put(b, cyl(0.11, 0.11, 1, 16, true), M.plume.clone(), 0, 0, 0, { rx: Math.PI / 2, to: beam });
  sheath.material.color.copy(A.c).multiplyScalar(1.4);
  const bolt = put(b, new THREE.SphereGeometry(0.09, 12, 8), M.hot, 0, 0, 0, { s: [1, 1, 4], to: beam });
  const tip = new THREE.Sprite(M.halo); beam.add(tip);
  b.anim.push((t) => {
    const k = (b.busy ? 1.4 : 1) * (1 + 0.12 * Math.sin(t * 7 + b.phase));
    core.scale.set(k, bl, k); core.position.z = zb + bl / 2; sheath.scale.set(k, bl, k); sheath.position.z = zb + bl / 2;
    bolt.position.z = zb + ((t * (b.busy ? 1.7 : 1) + b.phase) % 1) * bl;
    tip.position.z = zb + bl; tip.scale.setScalar(1.1 + 0.3 * Math.sin(t * 11));
    rings.forEach((m, i) => { m.material.emissiveIntensity = 0.6 + 2.6 * Math.max(0, Math.sin(t * 5 - i * 0.9 + b.phase)); });
  });
  b.top = ty + 1.2; b.bot = -1.0; b.foot = L * 0.5 + 0.6;
}

/* ---------------- 6. Citadel: an armoured orb, its decks in bands, a docking ring round it ---------------- */
function citadel(b, n) {
  const A = b.A, M = mats(A), R = 1.45 + 0.09 * n;
  put(b, sphere(R), M.light, 0, 0, 0);
  // the equatorial band, its trench of light and eight hangar mouths glowing in it
  put(b, cyl(R * 1.035, R * 1.035, 0.34, 64), M.mid, 0, 0, 0);
  put(b, torus(R * 1.04, 0.025, 6, 96), M.neon, 0, 0.0, 0, { rx: Math.PI / 2 });
  for (let k = 0; k < 8; k++) { const a = (k + 0.5) / 8 * Math.PI * 2; box(b, 0.34, 0.12, 0.02, Math.cos(a) * R * 1.04, -0.08, Math.sin(a) * R * 1.04, M.hot, { ry: Math.PI / 2 - a }); }
  // meridian ribs over the armour, pole to pole
  for (let k = 0; k < 6; k++) put(b, torus(R * 1.008, 0.03, 6, 64, Math.PI), M.mid, 0, 0, 0, { ry: k / 6 * Math.PI * 2, rz: Math.PI / 2 });
  // the decks: bands of windows round it, above and below the equator in turn
  for (let f = 0; f < n; f++) {
    const lat = (f % 2 ? -1 : 1) * (0.28 + Math.floor(f / 2) * 0.22), yy = Math.sin(lat) * R, rr = Math.cos(lat) * R;
    put(b, torus(rr + 0.01, 0.022, 6, 64), M.dark, 0, yy + 0.06, 0, { rx: Math.PI / 2 });
    b.ringWins(f, rr - 0.03, yy, 0.07, 0.2, 0.6, 0.1);
  }
  // the poles: a spire with its beacon above, a long antenna below
  put(b, cyl(0.1, 0.32, 1.2, 12), M.mid, 0, R + 0.5, 0);
  put(b, cyl(0.02, 0.05, 0.8, 8), M.metal, 0, R + 1.5, 0);
  b.beacon(0, R + 1.92, 0, 0.06);
  put(b, cyl(0.26, 0.05, 1.5, 12), M.dark, 0, -R - 0.65, 0);
  engine(b, M, 0, -R - 0.15, 0, 0.3, 0, 0.9).rotation.x = -Math.PI / 2;
  // the docking ring on four arms, and what is docked on it
  const D = R * 1.75;
  put(b, torus(D, 0.08, 8, 96), M.mid, 0, -0.05, 0, { rx: Math.PI / 2 });
  put(b, torus(D, 0.02, 6, 120), M.neonSoft, 0, 0.04, 0, { rx: Math.PI / 2 });
  for (let k = 0; k < 4; k++) {
    const a = k * Math.PI / 2 + Math.PI / 4;
    box(b, D - R, 0.1, 0.12, Math.cos(a) * (R + D) / 2, -0.05, Math.sin(a) * (R + D) / 2, M.metal, { ry: -a });
    const x = Math.cos(a) * D, z = Math.sin(a) * D;
    box(b, 0.3, 0.22, 0.6, x, 0.12, z, M.mid, { ry: -a });
    b.beacon(x, 0.3, z, 0.04);
  }
  escorts(b, M, D * 1.35, 0.5, 2, 0.32);
  b.top = R + 2.0; b.bot = -R - 1.5; b.foot = D + 0.3;
}

/* ---------------- 7. Monolith: a black slab of decks, data blocks circling it ---------------- */
function monolith(b, n) {
  const A = b.A, M = mats(A), w = 1.3, d = 0.62, dh = 0.46, H = n * dh + 0.5;
  // the plinth: a hexagon with a line of light round its edge, shards floating under it
  const hex = new THREE.Shape(); for (let k = 0; k < 6; k++) { const a = k / 6 * Math.PI * 2; hex[k ? 'lineTo' : 'moveTo'](Math.cos(a) * 1.9, Math.sin(a) * 1.9); } hex.closePath();
  put(b, slab('mnHex', hex, 0.3, 0.06), M.dark, 0, -0.3, 0);
  put(b, torus(1.86, 0.025, 6, 6), M.neon, 0, -0.02, 0, { rx: Math.PI / 2, rz: 0 });
  for (let k = 0; k < 5; k++) { const a = k / 5 * Math.PI * 2; put(b, new THREE.OctahedronGeometry(0.22 + (k % 2) * 0.1), M.dark, Math.cos(a) * 1.1, -0.75 - (k % 3) * 0.2, Math.sin(a) * 1.1, { s: [0.7, 1.6, 0.7] }); }
  put(b, new THREE.OctahedronGeometry(0.42), M.mid, 0, -0.95, 0, { s: [0.8, 1.9, 0.8] });
  // the slab: black glass, a seam of light up each edge, a deck's windows in bands across its broad faces
  box(b, w, H, d, 0, H / 2, 0, M.black);
  for (const [sx, sz] of [[1, 1], [1, -1], [-1, 1], [-1, -1]]) box(b, 0.03, H, 0.03, sx * w / 2, H / 2, sz * d / 2, M.neon);
  for (let f = 0; f < n; f++) {
    const y = 0.25 + f * dh + dh / 2;
    box(b, w + 0.02, 0.02, d + 0.02, 0, y + dh / 2, 0, M.neonSoft);
    wins(b, f, 0, y, 0, w, d, 2, 0.13, 0.13, 0.7, '+z-z');
  }
  // its crown: a prism of light
  put(b, new THREE.OctahedronGeometry(0.3), M.hot, 0, H + 0.45, 0, { s: [0.8, 1.6, 0.8] });
  sprite(b, M.halo, 0, H + 0.45, 0, 1.4);
  b.beacon(0, H + 0.95, 0, 0.05);
  // the data blocks: rings of them at three heights, one turning one way, the next the other
  const orbit = [];
  for (let r = 0; r < 3; r++) {
    const g = new THREE.Group(); g.userData.dyn = true; b.g.add(g); orbit.push(g);
    const plain = [], lit = [], m = 9 + r * 2, rad = 1.55 + r * 0.32, yy = H * (0.25 + r * 0.3);
    for (let k = 0; k < m; k++) {
      const a = k / m * Math.PI * 2, s = 0.13 + ((k * 7 + r) % 3) * 0.05, q = new THREE.BoxGeometry(s, s, s);
      q.rotateY(a + k); q.rotateX(k * 0.7); q.translate(Math.cos(a) * rad, yy + Math.sin(k * 1.7) * 0.12, Math.sin(a) * rad);
      ((k + r) % 3 ? plain : lit).push(q.toNonIndexed());
    }
    g.add(new THREE.Mesh(mergeGeometries(plain, false), M.metal), new THREE.Mesh(mergeGeometries(lit, false), M.hot));
  }
  b.anim.push((t) => { orbit.forEach((g, i) => { g.rotation.y = (i % 2 ? -1 : 1) * t * (0.18 + i * 0.05) * (b.busy ? 1.6 : 1) + b.phase; }); });
  b.top = H + 1.1; b.bot = -1.4; b.foot = 2.6;
}

/* ---------------- into u3d.js's table ---------------- */
const BUILD = { tower: dreadnought, dome: gateway, pyramid: pyramidCarrier, orbital: ringHabitat, rocket: lancer, vault: citadel, stack: monolith };
function install() {
  const U = CO.U3;
  if (!U || !U.ok || !U.SKIN || U.skins === 'ns1') return;
  Object.keys(BUILD).forEach((k) => { U.SKIN[k] = BUILD[k]; });
  (CO.SKINS || []).forEach((s) => { if (NAMES[s.key]) s.name = NAMES[s.key]; });
  U.skins = 'ns1';
  window.dispatchEvent(new Event('co3d-skins'));
}
if (CO.U3) install(); else window.addEventListener('co3d', install, { once: true });
