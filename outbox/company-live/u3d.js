/* The /company mockup's 3D engine. The Universe is a galaxy: Cymetica the star at its heart, every company a
 * station on one of its spiral arms, ONE DECK PER DEPARTMENT, a deck lit while its department works. three.js with
 * its WebGPU renderer (WebGL2 where a browser has no WebGPU), bloom on everything that glows, an orbit camera that
 * zooms to the cursor. Banners and the tooltip are HTML over the canvas, so they stay sharp and clickable. If the
 * renderer cannot start, the page keeps the flat map. The office in 3D is the second half of this file. */
import * as THREE from 'three/webgpu';
import { pass, renderOutput, vec4, vec3, mrt, output, normalView, dot, mix } from 'three/tsl';
import { bloom } from 'three/addons/tsl/display/BloomNode.js';
import { ao } from 'three/addons/tsl/display/GTAONode.js';
import { RoundedBoxGeometry } from 'three/addons/geometries/RoundedBoxGeometry.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { mergeGeometries, mergeVertices } from 'three/addons/utils/BufferGeometryUtils.js';

const CO = window.CO;
const FH = 0.82;

/* ---------------- shared geometry, materials and textures ---------------- */
const G = {}, M = {}, AM = {}, TX = {};
function geo() {
  if (G.box) return;
  G.box = new THREE.BoxGeometry(1, 1, 1);
  G.cyl = new THREE.CylinderGeometry(1, 1, 1, 40);
  G.cyl8 = new THREE.CylinderGeometry(1, 1, 1, 8);
  G.cone = new THREE.ConeGeometry(1, 1, 32);
  G.cone4 = new THREE.ConeGeometry(1, 1, 4);
  G.bell = new THREE.CylinderGeometry(0.5, 1, 1, 24, 1, true);
  G.sphere = new THREE.SphereGeometry(1, 32, 16);
  G.hemi = new THREE.SphereGeometry(1, 48, 24, 0, Math.PI * 2, 0, Math.PI / 2);
  G.hemiWire = new THREE.SphereGeometry(1, 16, 6, 0, Math.PI * 2, 0, Math.PI / 2);
  G.plane = new THREE.PlaneGeometry(1, 1);
  G.beam = new THREE.CylinderGeometry(0.05, 0.3, 1, 20, 1, true);
  G.pole = new THREE.CylinderGeometry(1, 1, 1, 16, 1, true);
  G.ring = new THREE.TorusGeometry(1, 0.016, 8, 140);
  G.ringT = new THREE.TorusGeometry(1, 0.03, 8, 120);
  G.wheel = new THREE.TorusGeometry(1, 0.085, 14, 120);
  G.holo = new THREE.TorusGeometry(1, 0.02, 6, 160);
  G.holoDash = dashedRing(30, 0.55);
  G.rock = rockGeo(3);
  // Hulls in the site's slate-navy, never a plain gray, and mostly matte: space has nothing for a mirror to
  // reflect, so a metal hull would read as a black hole with lit edges.
  M.hull = new THREE.MeshStandardMaterial({ color: 0x2b3646, roughness: 0.55, metalness: 0.32 });
  M.hull2 = new THREE.MeshStandardMaterial({ color: 0x344152, roughness: 0.58, metalness: 0.3 });
  M.trim = new THREE.MeshStandardMaterial({ color: 0x4a5970, roughness: 0.42, metalness: 0.45 });
  M.metal = new THREE.MeshStandardMaterial({ color: 0x5a6b82, roughness: 0.38, metalness: 0.55 });
  M.dark = new THREE.MeshStandardMaterial({ color: 0x0a0e14, roughness: 0.4, metalness: 0.5 });
  M.rock = new THREE.MeshStandardMaterial({ color: 0x2a313c, roughness: 0.92, metalness: 0.02, flatShading: true });
  M.leaf = new THREE.MeshStandardMaterial({ color: 0x0f7a4c, roughness: 0.85, emissive: 0x00ff88, emissiveIntensity: 0.06 });
  M.win = new THREE.MeshBasicMaterial({ color: 0xffffff });
  M.hit = new THREE.MeshBasicMaterial({ visible: false });
  M.solar = new THREE.MeshStandardMaterial({ map: solarTex(), roughness: 0.3, metalness: 0.45, emissive: 0x3b82f6, emissiveIntensity: 0.08 });
}
// one set per colour: what glows in it, from a window to a beam of light
function amat(hex) {
  if (AM[hex]) return AM[hex];
  const c = new THREE.Color(hex), cells = panelTex();
  AM[hex] = {
    c, hex,
    rim: new THREE.MeshStandardMaterial({ color: 0x000000, emissive: c, emissiveIntensity: 1.3, roughness: 1 }),
    soft: new THREE.MeshStandardMaterial({ color: 0x000000, emissive: c, emissiveIntensity: 0.7, roughness: 1 }),
    glow: new THREE.MeshBasicMaterial({ color: c.clone().multiplyScalar(4) }),
    glass: new THREE.MeshStandardMaterial({ color: c.clone().multiplyScalar(0.55), transparent: true, opacity: 0.12, roughness: 0.05, metalness: 0.2, emissive: c, emissiveIntensity: 0.05, depthWrite: false }),
    wire: new THREE.MeshBasicMaterial({ color: c.clone().multiplyScalar(0.85), wireframe: true, transparent: true, opacity: 0.16 }),
    beam: new THREE.MeshBasicMaterial({ color: c.clone().multiplyScalar(1.3), transparent: true, opacity: 0.14, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }),
    atmo: new THREE.MeshBasicMaterial({ color: c.clone().multiplyScalar(0.9), transparent: true, opacity: 0.12, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.BackSide }),
    fin: new THREE.MeshStandardMaterial({ color: 0x0a111d, emissive: c, emissiveIntensity: 0.55, roughness: 0.6 }),
    hull: new THREE.MeshStandardMaterial({ color: new THREE.Color(0x2b3646).lerp(c, 0.3), roughness: 0.55, metalness: 0.3 }),
    hull2: new THREE.MeshStandardMaterial({ color: new THREE.Color(0x344152).lerp(c, 0.22), roughness: 0.58, metalness: 0.28 }),
    panel: new THREE.MeshStandardMaterial({ color: 0x9fb2c8, map: cells, emissive: c, emissiveMap: cells, emissiveIntensity: 0.5, roughness: 0.25, metalness: 0.55 }),
    lit: c.clone().multiplyScalar(0.8), hot: c.clone().multiplyScalar(2.2), dim: new THREE.Color(0.012, 0.02, 0.035)
  };
  return AM[hex];
}
// The scene, its bloom, then tone mapping, drawn through a quad of its own. three.js's PostProcessing (r172)
// keeps ONE material for every instance on the page, so with the map and a preview both running, whichever
// updated last would draw into both canvases. This one owns its material.
const PASTEL = 0.66;   // how much colour the 3D keeps: 1 is the site's neon, the pictures sit about two thirds
class Post {
  constructor(renderer, scene, camera, strength, radius, threshold, opts) {
    this.renderer = renderer;
    const sp = pass(scene, camera, { samples: 4 });
    let col = sp.getTextureNode('output');
    // ambient occlusion (the office): where things meet -- a desk on the floor, a wall in a corner -- the light is
    // softer, as in a render. The scene writes its normals beside its colour in the same pass.
    if (opts && opts.ao) {
      sp.setMRT(mrt({ output, normal: normalView }));
      const a = ao(sp.getTextureNode('depth'), sp.getTextureNode('normal'), camera);
      a.resolutionScale = 0.5; a.radius.value = opts.ao.radius; a.scale.value = opts.ao.scale; a.thickness.value = opts.ao.thickness || 1;
      col = vec4(col.rgb.mul(a.getTextureNode().r), col.a); this.ao = a;
    }
    this.material = new THREE.NodeMaterial();
    let out = col.add(bloom(col, strength, radius, threshold));
    // Pastel, as in the operator's pictures ('mene razici pastelove'): every colour pulled part of the way to its
    // own grey after the bloom, so the site's green, cyan, blue and red read soft instead of neon.
    const sat = opts && opts.sat != null ? opts.sat : PASTEL;
    if (sat !== 1) out = vec4(mix(vec3(dot(out.rgb, vec3(0.2126, 0.7152, 0.0722))), out.rgb, sat), out.a);
    this.material.fragmentNode = renderOutput(out, renderer.toneMapping, renderer.outputColorSpace);
    this.quad = new THREE.QuadMesh(this.material);
  }
  render() {
    const r = this.renderer, tm = r.toneMapping, cs = r.outputColorSpace;
    r.toneMapping = THREE.NoToneMapping; r.outputColorSpace = THREE.LinearSRGBColorSpace;
    this.quad.render(r);
    r.toneMapping = tm; r.outputColorSpace = cs;
  }
}
// the map's model lives in universe.js, which the flat map draws too: one copy, so the two pictures cannot drift
const rng = CO.uvRng, floorsOf = CO.floorsOf, fpOf = CO.fpOf;
function rotXZ(x, z, a) { const c = Math.cos(a), s = Math.sin(a); return [x * c + z * s, -x * s + z * c]; }

// a lump of rock: an icosphere pushed in and out by a few waves, faceted
function rockGeo(seed) {
  const g = new THREE.IcosahedronGeometry(1, 2), p = g.attributes.position, v = new THREE.Vector3(), R = rng(seed), k = [R() * 6, R() * 6, R() * 6, R() * 6];
  for (let i = 0; i < p.count; i++) {
    v.fromBufferAttribute(p, i);
    v.multiplyScalar(1 + 0.13 * Math.sin(v.x * 3.1 + k[0]) * Math.cos(v.y * 2.7 + k[1]) + 0.08 * Math.sin(v.z * 5.3 + v.x * 1.9 + k[2]) + 0.05 * Math.cos(v.y * 7.1 + k[3]));
    p.setXYZ(i, v.x, v.y, v.z);
  }
  g.computeVertexNormals();
  return g;
}
// a ring of dashes in one geometry: what a private station floats over
function dashedRing(n, fill) {
  const parts = [];
  for (let i = 0; i < n; i++) { const t = new THREE.TorusGeometry(1, 0.02, 6, 8, Math.PI * 2 / n * fill); t.rotateZ(i * Math.PI * 2 / n); parts.push(t); }
  const g = mergeGeometries(parts, false); parts.forEach((x) => x.dispose()); return g;
}
// solar cells: a dark grid whose lines carry the station's colour
function panelTex() {
  if (TX.panel) return TX.panel;
  const c = document.createElement('canvas'); c.width = 256; c.height = 128; const g = c.getContext('2d');
  g.fillStyle = '#0a121c'; g.fillRect(0, 0, 256, 128);
  g.fillStyle = '#122033';
  for (let x = 0; x < 16; x++) for (let y = 0; y < 8; y++) g.fillRect(x * 16 + 1.5, y * 16 + 1.5, 13, 13);
  g.fillStyle = 'rgba(255,255,255,.75)';
  for (let x = 0; x <= 256; x += 64) g.fillRect(x - 1, 0, 2, 128);
  g.fillRect(0, 63, 256, 2);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; TX.panel = t; return t;
}
function radialTex(rgb, a) {
  const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d');
  const gr = g.createRadialGradient(128, 128, 0, 128, 128, 128);
  gr.addColorStop(0, 'rgba(' + rgb + ',' + a + ')'); gr.addColorStop(0.45, 'rgba(' + rgb + ',' + (a * 0.35) + ')'); gr.addColorStop(1, 'rgba(' + rgb + ',0)');
  g.fillStyle = gr; g.fillRect(0, 0, 256, 256);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
function glowTex() { return TX.glow || (TX.glow = radialTex('255,255,255', 1)); }
function glowSprite(color, opacity, size) {
  const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: glowTex(), color, transparent: true, opacity, blending: THREE.AdditiveBlending, depthWrite: false }));
  s.scale.setScalar(size); return s;
}
// stars on a shell round a scene: points that never fog, mostly white, a few in the site's cyan and green
function starField(n, r, spread, k, seed) {
  const pos = new Float32Array(n * 3), col = new Float32Array(n * 3), R = rng(seed || 42), cc = new THREE.Color();
  for (let i = 0; i < n; i++) {
    const u = R() * 2 - 1, th = R() * Math.PI * 2, s = Math.sqrt(1 - u * u), rad = r + R() * spread;
    pos.set([Math.cos(th) * s * rad, u * rad, Math.sin(th) * s * rad], i * 3);
    const hue = R();
    cc.set(hue < 0.12 ? 0x00cfff : hue < 0.17 ? 0x00ff88 : 0xe6edf7).multiplyScalar((0.22 + R() * R() * 1.5) * k);
    col.set([cc.r, cc.g, cc.b], i * 3);
  }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.BufferAttribute(pos, 3)); g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  return new THREE.Points(g, new THREE.PointsMaterial({ vertexColors: true, size: 1, sizeAttenuation: false, fog: false }));
}
// a flat band round the centre, r wide by w either side, its texture's v running across it: an orbit's glow
function bandGeo(r, w, n = 360) {
  const pos = [], uv = [], idx = [];
  for (let k = 0; k <= n; k++) {
    const a = k / n * Math.PI * 2, s = Math.sin(a), c = Math.cos(a);
    pos.push(s * (r - w), 0, c * (r - w), s * (r + w), 0, c * (r + w)); uv.push(k / n, 0, k / n, 1);
    if (k < n) { const i = k * 2; idx.push(i, i + 1, i + 2, i + 1, i + 3, i + 2); }
  }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2)); g.setIndex(idx);
  return g;
}
// bright in the middle of the band, gone at its edges
function bandTex() {
  return TX.band || (TX.band = (() => {
    const c = document.createElement('canvas'); c.width = 4; c.height = 64; const g = c.getContext('2d'), gr = g.createLinearGradient(0, 0, 0, 64);
    gr.addColorStop(0, 'rgba(255,255,255,0)'); gr.addColorStop(0.5, 'rgba(255,255,255,1)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 4, 64);
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
  })());
}
// Static parts merged by material: a station is a handful of draw calls instead of a hundred. A part marked
// userData.dyn (it moves) and everything under it stays as it is; so do the instanced windows.
function bakeGroup(root) {
  root.updateMatrixWorld(true);
  const inv = root.matrixWorld.clone().invert(), bins = new Map();
  (function walk(o) {
    o.children.slice().forEach((ch) => {
      if (ch.userData.dyn || ch.isInstancedMesh) return;
      if (ch.isMesh && ch.material && !Array.isArray(ch.material)) {
        const key = ch.material.uuid + (ch.geometry.index ? 'i' : 'n');
        let bin = bins.get(key); if (!bin) bins.set(key, bin = { mat: ch.material, geos: [], objs: [] });
        bin.geos.push(ch.geometry.clone().applyMatrix4(new THREE.Matrix4().multiplyMatrices(inv, ch.matrixWorld))); bin.objs.push(ch);
      }
      walk(ch);
    });
  })(root);
  bins.forEach((bin) => {
    if (bin.objs.length < 2) { bin.geos.forEach((x) => x.dispose()); return; }
    const merged = mergeGeometries(bin.geos, false); bin.geos.forEach((x) => x.dispose());
    if (!merged) return;
    bin.objs.forEach((o) => o.parent.remove(o));
    const m = new THREE.Mesh(merged, bin.mat); m.userData.own = true; root.add(m);
  });
}

/* ---------------- a station: its parts, its windows, its decks ---------------- */
class Building {
  constructor(acc, seed) {
    this.g = new THREE.Group(); this.A = amat(acc); this.R = rng(seed); this.phase = (seed % 97) / 7;
    this.w = []; this.beacons = []; this.anim = []; this.top = 2; this.bot = 0; this.foot = 3; this.busy = false;
  }
  // dyn: it moves, so it is never merged with the rest
  part(geom, mat, sx, sy, sz, x, y, z, dyn) {
    const m = new THREE.Mesh(geom, mat); m.scale.set(sx, sy, sz); m.position.set(x, y, z);
    if (dyn) m.userData.dyn = true;
    this.g.add(m); return m;
  }
  box(w, h, d, x, y, z, mat, dyn) { return this.part(G.box, mat, w, h, d, x, y, z, dyn); }
  cyl(r, h, x, y, z, mat, dyn) { return this.part(G.cyl, mat, r, h, r, x, y, z, dyn); }
  // a window: where, which way it faces, its size, its deck, and whether its light is on by default
  win(x, y, z, ry, w, h, f, lit) { this.w.push({ x, y, z, ry, w, h, f, lit }); }
  beacon(x, y, z, r) { const m = this.part(G.sphere, this.A.glow, r, r, r, x, y, z, true); this.beacons.push(m); return m; }
  rimSquare(s, y, mat, dashed) {
    const t = 0.05, h = s / 2;
    const edge = (len, f) => {
      if (!dashed) return f(len, 0);
      for (let a = -len / 2; a < len / 2 - 0.2; a += 0.75) f(Math.min(0.45, len / 2 - a), a + 0.225);
    };
    edge(s + t, (l, o) => this.box(l, t, t, o, y, h, mat)); edge(s + t, (l, o) => this.box(l, t, t, o, y, -h, mat));
    edge(s + t, (l, o) => this.box(t, t, l, h, y, o, mat)); edge(s + t, (l, o) => this.box(t, t, l, -h, y, o, mat));
  }
  // windows round a box turned by rot about its axis
  faceWins(f, w, d, y, h, step, lit, rot = 0) {
    const ww = 0.2, wh = Math.min(0.46, h * 0.56), R = this.R;
    const put = (len, place) => { const m = Math.max(1, Math.floor((len - 0.25) / step)), s = len / m; for (let i = 0; i < m; i++) place(-len / 2 + s * (i + 0.5)); };
    const at = (x, z, ry) => { const p = rotXZ(x, z, rot); this.win(p[0], y, p[1], ry + rot, ww, wh, f, R() < lit); };
    put(w, (x) => at(x, d / 2 + 0.014, 0));
    put(w, (x) => at(x, -d / 2 - 0.014, Math.PI));
    put(d, (z) => at(w / 2 + 0.014, z, Math.PI / 2));
    put(d, (z) => at(-w / 2 - 0.014, z, -Math.PI / 2));
  }
  ringWins(f, r, y, h, step, lit, ww = 0.17) {
    const m = Math.max(6, Math.round(2 * Math.PI * r / step));
    for (let i = 0; i < m; i++) { const t = i / m * Math.PI * 2; this.win(Math.cos(t) * (r + 0.014), y, Math.sin(t) * (r + 0.014), Math.PI / 2 - t, ww, h, f, this.R() < lit); }
  }
  // all the windows as one instanced mesh, coloured per window: off, on, or the whole deck at work
  finish() {
    const n = this.w.length; if (!n) return;
    const mesh = new THREE.InstancedMesh(G.plane, M.win, n), q = new THREE.Quaternion(), e = new THREE.Euler(), m4 = new THREE.Matrix4();
    this.w.forEach((w, i) => {
      e.set(0, w.ry, 0); q.setFromEuler(e);
      m4.compose(new THREE.Vector3(w.x, w.y, w.z), q, new THREE.Vector3(w.w, w.h, 1));
      mesh.setMatrixAt(i, m4);
      mesh.setColorAt(i, w.lit ? this.A.lit : this.A.dim);
    });
    mesh.instanceMatrix.needsUpdate = true; mesh.instanceColor.needsUpdate = true;
    this.wins = mesh; this.g.add(mesh);
  }
  bake() { bakeGroup(this.g); }
  // The base every station stands on, as in the operator's orrery: a square deck in its hull colour with corner
  // blocks and a line of its colour round its foot, a keel under it with engines that glow, solar wings out to
  // two or four sides.
  chassis(s, wings) {
    const A = this.A, h = 0.55, y0 = -0.05;
    this.box(s, h, s, 0, y0 - h / 2, 0, A.hull2);
    this.box(s + 0.12, 0.08, s + 0.12, 0, y0, 0, M.trim);
    this.rimSquare(s + 0.14, y0 - h + 0.06, A.rim);
    for (const [sx, sz] of [[1, 1], [1, -1], [-1, 1], [-1, -1]]) this.box(0.46, h + 0.18, 0.46, sx * (s / 2 - 0.1), y0 - h / 2 + 0.06, sz * (s / 2 - 0.1), M.trim);
    this.box(s * 0.6, 0.36, s * 0.6, 0, y0 - h - 0.18, 0, A.hull);
    (wings > 2 ? [[1, 1], [-1, -1], [1, -1], [-1, 1]] : [[1, 0], [-1, 0]]).forEach(([ex, ez]) => flame(this, y0 - h - 0.38, 0.5, 1.0, ex * s * 0.18, ez * s * 0.18));
    const axes = wings > 2 ? [[1, 0], [-1, 0], [0, 1], [0, -1]] : [[1, 0], [-1, 0]], pw = Math.max(1.1, s * 0.36), pd = Math.max(0.95, s * 0.32), y = y0 - h * 0.45;
    axes.forEach(([ax, az]) => {
      const out = s / 2;
      this.box(ax ? 0.8 : 0.09, 0.09, ax ? 0.09 : 0.8, ax * (out + 0.4), y, az * (out + 0.4), M.metal);
      for (let k = 0; k < 2; k++) {
        const d = out + 0.8 + pw / 2 + k * (pw + 0.1), pn = this.box(ax ? pw : pd, 0.05, ax ? pd : pw, ax * d, y, az * d, M.solar);
        pn.rotation[ax ? 'x' : 'z'] = 0.32 * (ax || az);
      }
    });
    this.bot = Math.min(this.bot, y0 - h - 1.3);
    this.foot = Math.max(this.foot, s / 2 + 0.8 + 2 * pw + 0.2);
  }
  paint(on, mode) {
    if (!this.wins) return;
    const A = this.A, set = new Set(on || []), priv = mode === 'priv', paused = mode === 'paused';
    const lit = priv ? A.lit.clone().multiplyScalar(0.55) : A.lit;
    this.w.forEach((w, i) => {
      const c = paused ? A.dim : set.has(w.f) ? A.hot : w.lit ? lit : A.dim;
      this.wins.setColorAt(i, c);
    });
    this.wins.instanceColor.needsUpdate = true;
    this.busy = set.size > 0;
  }
  tick(t) {
    this.beacons.forEach((b, i) => { const s = 0.6 + 0.4 * Math.max(0, Math.sin(t * 2.6 + this.phase + i)); b.scale.setScalar(b.userData.r || (b.userData.r = b.scale.x)); b.scale.multiplyScalar(s); });
    this.anim.forEach((f) => f(t));
  }
}
// an engine's flame under a station: a beam pointing down from y0 that grows while a deck works
function flame(b, y0, w, len, x = 0, z = 0) {
  b.part(G.sphere, b.A.glow, w * 0.26, 0.05, w * 0.26, x, y0, z, true);
  const p = b.part(G.beam, b.A.beam, w, len, w, x, y0 - len / 2, z, true); p.rotation.x = Math.PI;
  b.anim.push((t) => { const k = (b.busy ? 1.3 : 0.82) + 0.12 * Math.sin(t * 17 + b.phase + x); p.scale.set(w * k, len * k, w * k); p.position.y = y0 - len * k / 2; });
}

/* ---------------- the six stations, n decks each ---------------- */
const SKIN = {};
// Spire: glass decks on a slight twist, a docking ring round the first, a keel and its thruster, a mast
SKIN.tower = (b, n) => {
  const A = b.A, fp = fpOf(n) * 0.9, half = fp / 2, tw = 0.13;
  b.chassis(fp + 1.0, 4);
  const dock = b.part(G.ringT, A.rim, half * 1.6, half * 1.6, half * 1.6, 0, 0.32, 0); dock.rotation.x = Math.PI / 2;
  for (let k = 0; k < 4; k++) { const a = k * Math.PI / 2 + Math.PI / 4; b.box(half * 0.62, 0.05, 0.05, Math.cos(a) * half * 1.28, 0.32, Math.sin(a) * half * 1.28, M.metal).rotation.y = -a; }
  let y = 0;
  for (let f = 0; f < n; f++) {
    const h = FH - 0.08, rot = f * tw;
    b.box(fp, h, fp, 0, y + h / 2, 0, f % 2 ? A.hull2 : A.hull).rotation.y = rot;
    b.box(fp + 0.16, 0.06, fp + 0.16, 0, y + h + 0.03, 0, M.trim).rotation.y = rot;
    b.faceWins(f, fp, fp, y + h / 2, h, 0.36, 0.45, rot);
    for (const [sx, sz] of [[1, 1], [1, -1], [-1, 1], [-1, -1]]) { const p = rotXZ(sx * (half + 0.035), sz * (half + 0.035), rot); b.box(0.07, h, 0.07, p[0], y + h / 2, p[1], A.rim).rotation.y = rot; }
    y += FH;
  }
  b.box(fp * 0.62, 0.36, fp * 0.62, 0, y + 0.18, 0, M.trim).rotation.y = n * tw;
  // a landing pad on the roof, ringed in light, a lamp at each corner
  b.part(G.ringT, A.soft, fp * 0.38, fp * 0.38, fp * 0.38, 0, y + 0.02, 0).rotation.x = Math.PI / 2;
  for (const [sx, sz] of [[1, 1], [1, -1], [-1, 1], [-1, -1]]) { const p = rotXZ(sx * half * 0.86, sz * half * 0.86, (n - 1) * tw); b.part(G.sphere, A.glow, 0.05, 0.05, 0.05, p[0], y + 0.05, p[1]); }
  b.cyl(0.035, 1.5, 0, y + 1.11, 0, M.metal);
  b.beacon(0, y + 1.91, 0, 0.11);
  const dish = b.part(G.hemi, M.trim, 0.34, 0.14, 0.34, half * 0.32, y + 0.52, -half * 0.2); dish.rotation.z = 0.9;
  b.top = y + 2.1; b.foot = Math.max(b.foot, half * 1.7, 2.2);
};
// Biodome: a drum of decks on a small planetoid, a glass dome with a garden and a light in it, a moonlet
SKIN.dome = (b, n) => {
  const A = b.A, r = fpOf(n) / 2 + 0.5, rr = r * 1.45, cy = -rr * 0.62;
  b.chassis(2 * r + 0.9, 4);
  b.cyl(r + 0.3, 0.16, 0, 0, 0, M.trim);
  let y = 0.08;
  for (let f = 0; f < n; f++) {
    const h = FH - 0.06;
    b.cyl(r, h, 0, y + h / 2, 0, f % 2 ? A.hull2 : A.hull);
    b.cyl(r + 0.05, 0.05, 0, y + h + 0.025, 0, M.trim);
    b.ringWins(f, r, y + h / 2, h * 0.52, 0.42, 0.45);
    y += FH;
  }
  b.cyl(r, 0.04, 0, y + 0.02, 0, M.trim);
  b.part(G.ringT, A.rim, r + 0.03, r + 0.03, r + 0.03, 0, y + 0.03, 0).rotation.x = Math.PI / 2;
  for (let k = 0; k < 4; k++) { const a = k / 4 * Math.PI * 2 + 0.4; b.part(G.sphere, M.leaf, 0.24, 0.3, 0.24, Math.cos(a) * r * 0.52, y + 0.22, Math.sin(a) * r * 0.52); }
  b.part(G.hemi, A.glass, r, r * 0.95, r, 0, y, 0);
  const wire = b.part(G.hemiWire, A.wire, r * 1.006, r * 0.956, r * 1.006, 0, y, 0, true);
  const core = b.part(G.sphere, A.soft, r * 0.22, r * 0.22, r * 0.22, 0, y + r * 0.42, 0, true);
  b.anim.push((t) => {
    core.position.y = y + r * 0.42 + Math.sin(t * 1.3 + b.phase) * 0.05; wire.rotation.y = t * 0.08;
  });
  b.beacon(0, y + r * 0.95 + 0.06, 0, 0.08);
  b.top = y + r * 0.95 + 0.6; b.foot = Math.max(b.foot, r * 1.3);
};
// Ziggurat: a tier per deck on a floating island of rock, stones drifting under it, a beam from its temple
SKIN.pyramid = (b, n) => {
  const A = b.A, b0 = fpOf(n) + 1.0, inset = Math.min(0.3, (b0 - 1.1) / (2 * n)), kh = b0 * 1.05;
  b.chassis(b0 + 0.7, 2);
  b.rimSquare(b0 + 0.04, 0.0, A.soft);
  let y = 0;
  for (let f = 0; f < n; f++) {
    const s = b0 - 2 * inset * f, h = FH - 0.05;
    b.box(s, h, s, 0, y + h / 2, 0, f % 2 ? A.hull2 : A.hull);
    b.rimSquare(s, y + h, A.rim);
    b.faceWins(f, s, s, y + h / 2, h, 0.62, 0.3);
    y += FH;
  }
  b.box(0.8, 0.5, 0.8, 0, y + 0.25, 0, M.trim);
  const beam = b.part(G.beam, A.beam.clone(), 1, 6, 1, 0, y + 3.5, 0, true);
  b.anim.push((t) => { beam.material.opacity = (b.busy ? 0.3 : 0.16) + 0.05 * Math.sin(t * 2 + b.phase); });
  b.beacon(0, y + 0.62, 0, 0.13);
  b.top = y + 1.5; b.foot = Math.max(b.foot, b0 * 0.85 + 0.4);
};
// Ring station: a spindle of disc decks, a great wheel round it on four spokes, turning slowly, an engine below
SKIN.orbital = (b, n) => {
  const A = b.A, rd = 0.75 + fpOf(n) * 0.15, spineH = 0.4 + n * FH, RR = rd + 1.9;
  b.cyl(0.22, spineH + 1.6, 0, (spineH - 0.4) / 2, 0, M.metal);
  b.part(G.bell, M.trim, 0.42, 0.55, 0.42, 0, -1.25, 0);
  flame(b, -1.55, 0.75, 1.3);
  let y = 0.2;
  for (let f = 0; f < n; f++) {
    b.cyl(rd, 0.3, 0, y + 0.15, 0, f % 2 ? A.hull2 : A.hull);
    b.part(G.ringT, A.rim, rd + 0.01, rd + 0.01, rd + 0.01, 0, y + 0.3, 0).rotation.x = Math.PI / 2;
    b.ringWins(f, rd, y + 0.15, 0.14, 0.38, 0.5, 0.15);
    y += FH;
  }
  const wheel = new THREE.Group(); wheel.position.y = 0.2 + n * FH / 2 - 0.25; wheel.userData.dyn = true; b.g.add(wheel);
  const tor = new THREE.Mesh(G.wheel, A.hull2); tor.scale.setScalar(RR); tor.rotation.x = Math.PI / 2; wheel.add(tor);
  const off = 0.085 * RR * 0.7;
  for (const dy of [off, -off]) { const l = new THREE.Mesh(G.ring, A.rim); l.scale.setScalar(RR + off); l.rotation.x = Math.PI / 2; l.position.y = dy; wheel.add(l); }
  for (let k = 0; k < 4; k++) {
    const a = k * Math.PI / 2, s = new THREE.Mesh(G.cyl8, M.metal); s.scale.set(0.06, RR - 0.3, 0.06); s.rotation.set(0, a, Math.PI / 2);
    s.position.set(Math.cos(a) * (RR + 0.3) / 2, 0, -Math.sin(a) * (RR + 0.3) / 2); wheel.add(s);
  }
  bakeGroup(wheel);
  b.anim.push((t) => { wheel.rotation.y = t * 0.2 + b.phase; });
  b.beacon(0, spineH + 0.68, 0, 0.1);
  b.top = spineH + 1.1; b.bot = -2.6; b.foot = RR + 0.5;
};
// Starship: a hull section per deck, lying along x; a nose and a bridge, three engines whose flames grow while it works
SKIN.rocket = (b, n) => {
  const A = b.A, rr = 0.5 + Math.min(n, 8) * 0.05, L = 1.0, len = n * L, x0 = -len / 2, cy = rr + 0.3;
  for (let f = 0; f < n; f++) {
    const x = x0 + f * L + L / 2;
    b.part(G.cyl, f % 2 ? A.hull2 : A.hull, rr, L - 0.05, rr, x, cy, 0).rotation.z = Math.PI / 2;
    b.part(G.cyl, A.rim, rr * 1.035, 0.05, rr * 1.035, x + L / 2 - 0.025, cy, 0).rotation.z = Math.PI / 2;
    for (const s of [1, -1]) for (const dx of [-0.22, 0.2]) b.win(x + dx, cy + 0.06, s * (rr + 0.014), s > 0 ? 0 : Math.PI, 0.17, 0.19, f, b.R() < 0.55);
  }
  b.part(G.cone, A.hull, rr, rr * 2.3, rr, len / 2 + rr * 1.15, cy, 0).rotation.z = -Math.PI / 2;
  b.part(G.hemi, A.glass, rr * 0.5, rr * 0.42, rr * 0.75, len / 2 - 0.4, cy + rr * 0.88, 0);
  // a strip of light down its back, seen from above, and its running lights along the keel
  b.box(len - 0.3, 0.05, 0.08, 0, cy + rr + 0.01, 0, A.rim);
  for (let k = 0; k < n; k++) b.part(G.sphere, A.glow, 0.05, 0.05, 0.05, x0 + k * L + L / 2, cy - rr - 0.02, 0);
  b.part(G.cyl, M.trim, rr * 1.12, 0.5, rr * 1.12, x0 - 0.25, cy, 0).rotation.z = Math.PI / 2;
  const fl = [];
  [[0.36, 0], [-0.22, 0.34], [-0.22, -0.34]].forEach(([dy, dz], i) => {
    const yy = cy + dy * rr, zz = dz * rr;
    b.part(G.bell, M.metal, rr * 0.34, 0.5, rr * 0.34, x0 - 0.75, yy, zz).rotation.z = -Math.PI / 2;
    b.part(G.sphere, A.glow, 0.05, rr * 0.3, rr * 0.3, x0 - 0.99, yy, zz, true);
    const p = b.part(G.beam, A.beam, rr * 0.9, 1.6, rr * 0.9, x0 - 1.8, yy, zz, true); p.rotation.z = Math.PI / 2; fl.push(p);
  });
  b.anim.push((t) => fl.forEach((p, i) => { const k = (b.busy ? 1.35 : 0.8) + 0.14 * Math.sin(t * 19 + i * 2 + b.phase); p.scale.set(rr * 0.9 * k, 1.6 * k, rr * 0.9 * k); p.position.x = x0 - 1.0 - 0.8 * k; }));
  b.box(0.95, 0.75, 0.05, x0 + 0.35, cy + rr + 0.3, 0, A.fin);
  for (const s of [1, -1]) b.box(0.95, 0.05, 0.75, x0 + 0.35, cy - rr * 0.35, s * (rr + 0.3), A.fin).rotation.x = s * 0.35;
  b.beacon(len / 2 + rr * 2.3, cy, 0, 0.06);
  b.beacon(x0 + 0.35, cy + rr + 0.7, 0, 0.07);
  b.top = cy + rr + 0.9; b.bot = cy - rr - 0.2; b.foot = len / 2 + rr * 2;
};
// Vault: an armoured block of decks with its round door, two solar wings, a dish, an engine pod underneath
SKIN.vault = (b, n) => {
  const A = b.A, fp = fpOf(n), w = fp + 0.7, d = Math.max(1.9, fp * 0.82);
  b.box(w * 0.46, 0.42, d * 0.46, 0, -0.29, 0, M.trim);
  flame(b, -0.52, 0.9, 1.3);
  let y = 0;
  for (let f = 0; f < n; f++) {
    const h = (f === 0 ? FH * 1.35 : FH) - 0.05;
    b.box(w, h, d, 0, y + h / 2, 0, f % 2 ? A.hull2 : A.hull);
    b.box(w + 0.1, 0.06, d + 0.1, 0, y + h + 0.03, 0, M.trim);
    for (const [sx, sz] of [[1, 1], [1, -1], [-1, 1], [-1, -1]]) b.box(0.13, h, 0.13, sx * w / 2, y + h / 2, sz * d / 2, M.trim);
    if (f === 0) {
      b.part(G.cyl, M.dark, 0.44, 0.05, 0.44, -w * 0.18, y + h * 0.5, d / 2 + 0.02).rotation.x = Math.PI / 2;
      b.part(G.ringT, A.rim, 0.46, 0.46, 0.46, -w * 0.18, y + h * 0.5, d / 2 + 0.05);
      b.box(0.62, 0.04, 0.02, -w * 0.18, y + h * 0.5, d / 2 + 0.06, A.soft); b.box(0.04, 0.62, 0.02, -w * 0.18, y + h * 0.5, d / 2 + 0.06, A.soft);
      b.box(w * 0.36, h * 0.28, 0.02, w * 0.22, y + h * 0.55, d / 2 + 0.02, A.soft);
    } else {
      const R = b.R, step = 0.42, m = Math.max(1, Math.floor((w - 0.3) / step)), s = w / m;
      for (let i = 0; i < m; i++) {
        b.win(-w / 2 + s * (i + 0.5), y + h / 2, d / 2 + 0.014, 0, 0.24, h * 0.5, f, R() < 0.5);
        b.win(-w / 2 + s * (i + 0.5), y + h / 2, -d / 2 - 0.014, Math.PI, 0.24, h * 0.5, f, R() < 0.5);
      }
    }
    b.box(0.02, 0.05, d * 0.7, w / 2 + 0.015, y + h * 0.5, 0, A.rim);
    b.box(0.02, 0.05, d * 0.7, -w / 2 - 0.015, y + h * 0.5, 0, A.rim);
    y += h + 0.05;
  }
  const wy = Math.min(y * 0.5, 1.6), pw = 3.2, pd = 1.7, tilt = 0.3;
  for (const s of [1, -1]) {
    b.box(1.1, 0.09, 0.09, s * (w / 2 + 0.55), wy, 0, M.metal);
    const px = s * (w / 2 + 1.1 + pw / 2);
    b.box(pw, 0.04, pd, px, wy, 0, A.panel).rotation.x = tilt;
    for (const e of [1, -1]) b.box(pw + 0.06, 0.05, 0.05, px, wy - e * Math.sin(tilt) * pd / 2, e * Math.cos(tilt) * pd / 2, A.rim);
    b.box(0.05, 0.05, pd, px + s * pw / 2, wy, 0, A.rim).rotation.x = tilt;
  }
  b.box(0.5, 0.3, 0.5, -w / 2 + 0.6, y + 0.15, -d / 2 + 0.55, M.trim);
  b.box(0.5, 0.3, 0.5, -w / 2 + 1.3, y + 0.15, -d / 2 + 0.55, M.trim);
  b.cyl(0.04, 0.6, w / 2 - 0.7, y + 0.3, d / 2 - 0.6, M.metal);
  const dish = b.part(G.hemi, M.metal, 0.42, 0.18, 0.42, w / 2 - 0.7, y + 0.66, d / 2 - 0.6); dish.rotation.x = Math.PI * 0.85; dish.rotation.z = 0.4;
  b.beacon(w / 2 - 0.7, y + 0.95, d / 2 - 0.6, 0.07);
  b.top = y + 1.15; b.bot = -1.9; b.foot = w / 2 + 1.1 + pw;
};

// A whole station: the body (it bobs and turns), the holo-ring it floats over -- solid when public, dashed when
// private, our own in green -- a pool of its light, and its hit box. RING: how brightly the ring burns.
const RING = { pub: 0.7, priv: 0.45, hover: 2.6 }, SS = 2.7;   // SS: how much larger a station is drawn on the map
function makeStation(c, seed, opts) {
  geo();
  const n = floorsOf(c), A = amat(CO.accentHex(c.accent)), root = new THREE.Group(), body = new THREE.Group();
  const b = new Building(A.hex, seed);
  (SKIN[c.skin] || SKIN.tower)(b, n);
  b.finish(); b.bake();
  body.add(b.g); root.add(body);
  const own = !!opts.mine, pub = !!c.public || own, RA = own ? amat('#00ff88') : A;
  const rimMat = RA.rim.clone(); rimMat.emissiveIntensity = RING[pub ? 'pub' : 'priv'];
  const ringR = Math.max(2.0, b.foot * 0.72), ringY = b.bot - 0.5;
  const ring = new THREE.Mesh(pub ? G.holo : G.holoDash, rimMat); ring.scale.setScalar(ringR); ring.rotation.x = Math.PI / 2; ring.position.y = ringY; root.add(ring);
  const pool = new THREE.Mesh(G.plane, new THREE.MeshBasicMaterial({ map: glowTex(), color: RA.c, transparent: true, opacity: pub ? 0.1 : 0.05, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
  pool.scale.setScalar(ringR * 2.3); pool.rotation.x = -Math.PI / 2; pool.position.y = ringY; root.add(pool);
  // seen from far off, a station is a point of light in its own colour among the galaxy's stars; close up the
  // light gives way to the station itself (Universe3D fades it with distance)
  const halo = glowSprite(RA.c, own ? 0.5 : pub ? 0.32 : 0.18, 7 + b.foot); halo.position.y = (b.top + b.bot) / 2; body.add(halo);
  const hw = Math.max(3, b.foot * 1.5), hit = new THREE.Mesh(G.box, M.hit); hit.scale.set(hw, b.top - ringY + 0.6, hw); hit.position.y = (b.top + ringY) / 2; root.add(hit);
  return { root, body, b, rimMat, ring, pool, ringR, hit, halo, haloBase: halo.material.opacity, top: b.top, bot: ringY, n, pub, spin: (seed % 13) / 13 * Math.PI * 2 };
}

/* ---------------- the map: a galaxy ---------------- */
class Universe3D {
  constructor(el, stage, h) {
    this.el = el; this.stage = stage; this.h = h || {};
    this.tip = stage.querySelector('.tip'); this.bans = stage.querySelector('.uvbans');
    this.items = []; this.live = {}; this.mineKey = ''; this.fitted = false; this.pops = []; this.arcs = [];
    this.mouse = new THREE.Vector2(); this.ray = new THREE.Raycaster(); this.hover = null; this.mouseIn = false; this.lastUse = 0;
    geo();
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x010204);
    this.camera = new THREE.PerspectiveCamera(36, 2, 0.5, 9000);
    // no antialias on the renderer itself: three.js resolves it through ONE quad shared by every renderer on the
    // page, so a second renderer (a preview) would take this canvas over. The pass multisamples instead.
    this.renderer = new THREE.WebGPURenderer({ antialias: false });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.15;
    el.appendChild(this.renderer.domElement);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    // a map first: the left button moves it over the galaxy's disc, the right one turns it, the wheel zooms where it points
    Object.assign(this.controls, { enableDamping: true, dampingFactor: 0.06, minDistance: 7, maxDistance: 900, minPolarAngle: 0.06, maxPolarAngle: Math.PI - 0.06,
      autoRotate: false, screenSpacePanning: false, zoomToCursor: true, zoomSpeed: 1.1, rotateSpeed: 0.55, panSpeed: 1.1,
      mouseButtons: { LEFT: THREE.MOUSE.PAN, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.ROTATE },
      touches: { ONE: THREE.TOUCH.PAN, TWO: THREE.TOUCH.DOLLY_ROTATE } });
    this.controls.addEventListener('start', () => { this.tw = null; this.used = true; this.follow = null; this.lastUse = performance.now(); });
    this.world();
    this.bind();
    this.resize();
    this.clock = new THREE.Clock();
    this.renderer.init().then(() => {
      try { this.post = new Post(this.renderer, this.scene, this.camera, 0.6, 0.5, 0.74); } catch (e) { console.warn('bloom off:', e); this.post = null; }
      this.renderer.setAnimationLoop(() => this.frame());
      this.ready = true;
    }).catch((e) => { console.error('3D map could not start:', e); if (this.h.onFail) this.h.onFail(e); });
    setInterval(() => { if (this.visible()) this.pulse(); }, 1700);
    if (window.ResizeObserver) new ResizeObserver(() => this.resize()).observe(el);
  }
  visible() { return this.el.clientWidth > 0 && this.el.clientHeight > 0; }

  // light, the sky, the orbits and what runs along them, and Cymetica in the middle
  world() {
    const S = this.scene;
    S.add(new THREE.AmbientLight(0x1a2230, 0.7));
    S.add(new THREE.HemisphereLight(0xdfe8f2, 0x05070a, 0.75));
    const sun = new THREE.DirectionalLight(0xf4f8fc, 2.1); sun.position.set(-300, 280, 220); S.add(sun);
    const rim = new THREE.DirectionalLight(0x00cfff, 0.5); rim.position.set(240, -60, -260); S.add(rim);
    // the office's sky, as far again as this map is big, turned so its teal nebula sits up and to the left of this
    // map's first look as well
    this.sky = spaceSky(); this.sky.scale.setScalar(12); this.sky.rotation.y = CO.uvGalaxy.AZ - Math.PI / 4; S.add(this.sky);
    this.sky.traverse((o) => { if (o.isMesh && !o.isInstancedMesh && o.material.map) o.material.opacity *= 0.55; });
    this.fades = [];
    this.lanes();
    this.core();
  }
  // The orbits, as in the operator's picture: a crisp line of light each in green, cyan or blue, a soft glow round
  // it, a faint second line and a dashed one beside some; lights that run along them faster than the stations.
  lanes() {
    const Gx = CO.uvGalaxy, R = rng(3), cols = [0x00ff88, 0x00cfff, 0x00ff88, 0x00cfff, 0x3b82f6, 0x00cfff, 0x3b82f6];
    const line = (r, col, op, dash) => {
      const n = 720, pts = [];
      for (let k = 0; k <= n; k++) { const a = k / n * Math.PI * 2; pts.push(new THREE.Vector3(Math.sin(a) * r, 0, Math.cos(a) * r)); }
      const mat = new THREE.LineBasicMaterial({ color: new THREE.Color(col).multiplyScalar(1.6), transparent: true, opacity: op, blending: THREE.AdditiveBlending, depthWrite: false });
      if (!dash) return new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), mat);
      const seg = []; for (let k = 0; k < n; k += 3) if ((k / 3) % 3 !== 2) seg.push(pts[k], pts[k + 1]);
      return new THREE.LineSegments(new THREE.BufferGeometry().setFromPoints(seg), mat);
    };
    this.laneDefs = Gx.ORBITS.map((r, i) => {
      const col = cols[i % cols.length];
      this.scene.add(line(r, col, 0.85));
      const band = new THREE.Mesh(bandGeo(r, 0.9), new THREE.MeshBasicMaterial({ map: bandTex(), color: new THREE.Color(col).multiplyScalar(1.2), transparent: true, opacity: 0.38, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
      this.scene.add(band);
      if (i % 3 === 1) { this.scene.add(line(r + 3, col, 0.28)); this.scene.add(line(r - 3, col, 0.4, true)); }
      if (i === Gx.ORBITS.length - 1) this.scene.add(line(r + 5, 0x00cfff, 0.18));
      return { r, col, speed: Gx.omega(r) * 7 };
    });
    // the lights that run along the orbits: a bright head and a short trail
    this.ships = [];
    this.laneDefs.forEach((L, i) => { const n = 1 + (i % 3); for (let k = 0; k < n; k++) this.ships.push({ L, a: k / n * Math.PI * 2 + R() * 2, head: null }); });
    this.ships.forEach((s) => { s.head = glowSprite(new THREE.Color(s.L.col).lerp(new THREE.Color(0xffffff), 0.5), 0.9, 4); this.scene.add(s.head); });
    this.trailMesh = new THREE.InstancedMesh(G.box, new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.45, blending: THREE.AdditiveBlending, depthWrite: false }), this.ships.length);
    this.ships.forEach((s, i) => this.trailMesh.setColorAt(i, new THREE.Color(s.L.col).multiplyScalar(1.4)));
    this.trailMesh.instanceColor.needsUpdate = true; this.trailMesh.frustumCulled = false; this.scene.add(this.trailMesh);
  }
  // Cymetica, a collider: a white-hot heart inside a sphere of light filaments that turn and flicker, beams shot
  // out of it, sparks flying off, a ring of machinery round it turning slowly with a gyroscope across it, a cone
  // of rings over it and rings of light on the orbits' plane. White, cyan, blue and a little green; nothing warm.
  core() {
    const g = new THREE.Group(), R = rng(77), cy = amat('#00cfff');
    G.plume = G.plume || new THREE.CylinderGeometry(0.42, 0.05, 1, 24, 1, true);
    const star = new THREE.Mesh(G.sphere, new THREE.MeshBasicMaterial({ color: new THREE.Color(0xffffff).multiplyScalar(2.6) })); star.scale.setScalar(1.3); g.add(star);
    this.corona = [[5, 0.75, 0xeafcff], [12, 0.22, 0x9feeff], [30, 0.07, 0x00cfff], [70, 0.03, 0x3b82f6]].map(([s, o, c]) => { const sp = glowSprite(c, o, s); g.add(sp); return sp; });
    // the filaments: arcs round the heart, each set in its own colour, turning its own way
    this.fil = [[0xffffff, 1.8, 90, 2.4, 7.0], [0x9feeff, 1.8, 110, 2.8, 8.0], [0x3b82f6, 2.2, 70, 3.4, 8.6], [0x00ff88, 1.6, 24, 3.8, 7.6]].map(([col, k, n, r0, r1]) => {
      const pos = [];
      for (let i = 0; i < n; i++) {
        const ax = new THREE.Vector3(R() * 2 - 1, R() * 2 - 1, R() * 2 - 1).normalize();
        const u = new THREE.Vector3(0.3, 1, 0.2).cross(ax).normalize(), v = ax.clone().cross(u).normalize();
        const rr = r0 + R() * (r1 - r0), a0 = R() * Math.PI * 2, len = 0.8 + R() * 2.8, wob = R() * 0.7, f = 2 + Math.floor(R() * 4), seg = 30;
        let prev = null;
        for (let s = 0; s <= seg; s++) {
          const a = a0 + len * s / seg, rad = rr * (1 + wob * 0.22 * Math.sin(a * f));
          const p = u.clone().multiplyScalar(Math.cos(a) * rad).addScaledVector(v, Math.sin(a) * rad).addScaledVector(ax, wob * Math.sin(a * f * 0.7) * 1.3);
          if (prev) pos.push(prev.x, prev.y, prev.z, p.x, p.y, p.z);
          prev = p;
        }
      }
      const geo = new THREE.BufferGeometry(); geo.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3));
      const ls = new THREE.LineSegments(geo, new THREE.LineBasicMaterial({ color: new THREE.Color(col).multiplyScalar(k), transparent: true, opacity: 0.8, blending: THREE.AdditiveBlending, depthWrite: false }));
      g.add(ls); return ls;
    });
    // beams shot out of the heart, narrowing as they go
    this.beams = [];
    for (let i = 0; i < 10; i++) {
      const dir = new THREE.Vector3(R() * 2 - 1, (R() - 0.5) * 1.1, R() * 2 - 1).normalize(), len = 14 + R() * 26;
      const m = new THREE.Mesh(G.plume, new THREE.MeshBasicMaterial({ map: plumeTex(), color: new THREE.Color(R() < 0.6 ? 0xffffff : 0x9feeff).multiplyScalar(1.4), transparent: true, opacity: 0.4, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
      m.scale.set(0.45 + R() * 0.5, len, 0.45 + R() * 0.5); m.quaternion.setFromUnitVectors(new THREE.Vector3(0, -1, 0), dir); m.position.copy(dir.clone().multiplyScalar(len / 2));
      g.add(m); this.beams.push({ m, ph: R() * 6 });
    }
    // sparks flying off the heart
    const NS = 420, sp = new Float32Array(NS * 3), spCol = new Float32Array(NS * 3), cc = new THREE.Color();
    this.sparks = { N: NS, dir: [], speed: [], ph: [] };
    for (let i = 0; i < NS; i++) {
      this.sparks.dir.push(new THREE.Vector3(R() * 2 - 1, (R() - 0.5) * 0.8, R() * 2 - 1).normalize()); this.sparks.speed.push(0.25 + R() * 0.6); this.sparks.ph.push(R());
      cc.set(R() < 0.7 ? 0xeafcff : 0x00cfff).multiplyScalar(1.6); spCol.set([cc.r, cc.g, cc.b], i * 3);
    }
    const sg = new THREE.BufferGeometry(); sg.setAttribute('position', new THREE.BufferAttribute(sp, 3)); sg.setAttribute('color', new THREE.BufferAttribute(spCol, 3));
    this.sparkPts = new THREE.Points(sg, new THREE.PointsMaterial({ vertexColors: true, size: 1, sizeAttenuation: false, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
    this.sparkPts.frustumCulled = false; g.add(this.sparkPts);
    // the machine round it: plates with lit seams between them, a coil every fourth, tilted, turning slowly
    this.machine = new THREE.Group(); this.machine.rotation.set(0.38, 0, 0.16); g.add(this.machine);
    const RR = 11.5, NSEG = 28;
    for (let i = 0; i < NSEG; i++) {
      const a = i / NSEG * Math.PI * 2, coil = i % 4 === 0, p = new THREE.Mesh(G.box, coil ? M.metal : M.hull2);
      p.scale.set(coil ? 1.5 : 2.2, coil ? 2.1 : 1.3, coil ? 1.9 : 1.1); p.position.set(Math.sin(a) * RR, 0, Math.cos(a) * RR); p.rotation.y = a + Math.PI / 2; this.machine.add(p);
      const b = a + Math.PI / NSEG, lamp = new THREE.Mesh(G.box, cy.glow); lamp.scale.set(0.12, 0.95, 1.2); lamp.position.set(Math.sin(b) * RR, 0, Math.cos(b) * RR); lamp.rotation.y = b + Math.PI / 2; this.machine.add(lamp);
    }
    const inner = new THREE.Mesh(G.wheel, M.metal); inner.scale.setScalar(RR - 0.95); inner.rotation.x = Math.PI / 2; this.machine.add(inner);
    this.gyro = new THREE.Group(); g.add(this.gyro);
    const gy = new THREE.Mesh(G.wheel, M.trim); gy.scale.set(9, 9, 5); this.gyro.add(gy);
    const gyl = new THREE.Mesh(G.ringT, cy.rim); gyl.scale.setScalar(9.6); this.gyro.add(gyl);
    // rings of light on the orbits' plane, and a cone of rings over the heart as over the Manager's dais
    this.coreRings = [[15, G.ringT, cy.rim], [17.5, G.holoDash, cy.soft], [20.5, G.holo, cy.rim], [24, G.holo, cy.soft]].map(([r, geo, mat]) => {
      const m = new THREE.Mesh(geo, mat); m.scale.setScalar(r); m.rotation.x = Math.PI / 2; g.add(m); return m;
    });
    this.coneRings = [[4.5, 7.2], [7.5, 5.8], [10.5, 4.4], [13.5, 3.0]].map(([y, s], i) => {
      const m = new THREE.Mesh(i % 2 ? G.holoDash : G.holo, cy.rim); m.scale.setScalar(s); m.rotation.x = Math.PI / 2; m.position.y = y; g.add(m); return m;
    });
    g.add(new THREE.PointLight(0xa8ecff, 2600, 0, 2));
    const hit = new THREE.Mesh(G.sphere, M.hit); hit.scale.setScalar(13); hit.userData.id = 'core'; g.add(hit); this.coreHit = hit;
    g.scale.setScalar(2.4); this.coreAt = new THREE.Vector3(0, 40, 0);
    this.scene.add(g);
  }
  // every company on its orbit; ours on the second, in front of Cymetica where the camera first looks
  layout() {
    this.items = CO.uvPlan(this.h.mine());
    CO.uvSeed(this.items, this.live);
    this.items.forEach((it) => this.place(it));
    this.coreBanner();
    this.stats();
    // zoomed all the way out, the orrery still fills most of the view: not a speck in the dark
    const h = this.home(); this.controls.maxDistance = h.pos.distanceTo(h.tgt) * 1.6;
  }
  place(it) {
    this.built = (this.built || 0) + 1;
    if (it.plot) { this.scene.remove(it.plot.root); release(it.plot.root); }
    const c = it.c, p = makeStation(c, it.mine ? 7 : c.id, { mine: it.mine });
    // larger than a deck's height makes it: in the picture a station reads at a glance, orbit by orbit
    p.root.scale.setScalar(SS);
    // only ours keeps its ring of light; the others ride their orbits, as in the picture
    if (!it.mine) { p.ring.visible = false; p.pool.visible = false; }
    p.hit.userData.id = c.id;
    if (it.mine) p.meRing = p.ring;
    this.scene.add(p.root);
    it.plot = p;
    it.anchor = new THREE.Vector3(); this.orbit(it, this.clock ? this.clock.getElapsedTime() : 0);
    it.size = (p.top - p.bot) * SS;
    this.paint(it);
    this.banner(it);
  }
  // where a station is on its orbit at a moment, and where its banner hangs
  orbit(it, t) {
    const o = it.orbit, p = it.plot; if (!o || !p) return;
    const a = o.a + o.w * t; p.root.position.set(Math.sin(a) * o.r, 0, Math.cos(a) * o.r);
    it.anchor.set(p.root.position.x, (p.top + 0.5) * SS, p.root.position.z);
  }
  paint(it) {
    const on = it.mine ? (it.c.working || []) : (this.live[it.c.id] || []);
    it.plot.b.paint(on, it.c.status === 'paused' ? 'paused' : !it.c.public && !it.mine ? 'priv' : '');
  }
  banner(it) {
    const c = it.c, acc = CO.accentHex(c.accent);
    if (!it.el) { it.el = document.createElement('div'); this.bans.appendChild(it.el); it.el.addEventListener('pointerenter', () => this.setHover(c.id, true)); it.el.addEventListener('pointerleave', () => this.setHover(null, true)); it.el.addEventListener('click', () => this.open(c.id)); }
    let name = String(c.name || '').toUpperCase(); if (name.length > 22) name = name.slice(0, 21) + '…';
    it.el.className = 'b3' + (!c.public && !it.mine ? ' priv' : '') + (c.status === 'paused' ? ' paused' : '') + (it.mine ? ' mine' : '');
    it.el.style.setProperty('--acc', acc);
    it.el.setAttribute('data-id', c.id);
    it.el.innerHTML = (it.mine ? '<span class="you">YOU</span>' : '') + '<span class="rib">' + (!c.public && !it.mine ? '<i class="lk"></i>' : '') + esc(name) + '</span><span class="teth"></span>';
    it.el._bw = 0;
  }
  coreBanner() {
    if (this.coreEl) return;
    const el = document.createElement('div'); el.className = 'b3 core'; el.style.setProperty('--acc', '#00cfff');
    el.innerHTML = '<span class="rib">CYMETICA</span><span class="teth"></span>';
    el.addEventListener('pointerenter', () => this.setHover('core', true)); el.addEventListener('pointerleave', () => this.setHover(null, true));
    this.bans.appendChild(el); this.coreEl = el;
  }
  // our own company: its station follows Settings, its decks follow its departments, its ET10 pops
  setMine(m) {
    const it = this.items.find((x) => x.mine); if (!it) return;
    const key = [m.name, m.skin, m.accent, m.public, m.status, floorsOf(m)].join('|');
    const gain = it.c.et10 != null && m.et10 > it.c.et10 ? m.et10 - it.c.et10 : 0;
    it.c = m;
    if (key !== this.mineKey) { this.mineKey = key; this.place(it); } else this.paint(it);
    if (gain) this.pop(it, '+' + gain.toLocaleString('en-US') + ' ET10');
    this.stats();
  }
  pulse() {
    CO.uvStep(this.items, this.live).forEach(({ it, on, was, bug }) => {
      this.paint(it);
      // a deck that starts work sends it to Cymetica: an arc of light to the star in the middle
      if (on.length && !was) this.arc(it, false);
      if (bug) { this.arc(it, true); setTimeout(() => this.pop(it, '+1,000 ET10'), 1300); }
    });
    this.stats();
  }
  // work goes in to Cymetica in the company's colour; ET10 comes back out in green
  arc(it, back) {
    if (!it.plot || this.arcs.length > 12) return;
    const core = new THREE.Vector3(0, 0, 0), top = it.plot.root.position.clone().add(new THREE.Vector3(0, it.plot.top * 0.6 * SS, 0));
    const a = back ? core : top, b = back ? top : core, mid = a.clone().lerp(b, 0.5);
    mid.y += 8 + a.distanceTo(b) * 0.16;
    const A = back ? amat('#00ff88') : amat(CO.accentHex(it.c.accent)), curve = new THREE.QuadraticBezierCurve3(a, mid, b);
    const head = new THREE.Mesh(G.sphere, A.glow); head.scale.setScalar(0.42);
    const halo = new THREE.Mesh(G.sphere, A.atmo); halo.scale.setScalar(2.6); head.add(halo);
    // the streak: a thin tube along the arc, drawn as the light travels and let go behind it
    const tube = new THREE.TubeGeometry(curve, 64, 0.12, 6, false);
    const mat = new THREE.MeshBasicMaterial({ color: A.c.clone().multiplyScalar(2.6), transparent: true, opacity: 0.85, blending: THREE.AdditiveBlending, depthWrite: false });
    // hidden while there is nothing of it to draw: a draw of zero indices is a warning on WebGPU
    const streak = new THREE.Mesh(tube, mat); tube.setDrawRange(0, 0); streak.visible = false;
    this.scene.add(head, streak);
    this.arcs.push({ curve, head, streak, tube, mat, t0: performance.now(), dur: 1600 + a.distanceTo(b) * 12 });
  }
  pop(it, label) {
    const el = document.createElement('div'); el.className = 'b3pop'; el.textContent = label; this.bans.appendChild(el);
    const p = { el, it, t0: performance.now() }; this.pops.push(p);
    setTimeout(() => { el.remove(); this.pops = this.pops.filter((x) => x !== p); }, 2600);
  }
  stats() { if (this.h.onStats) this.h.onStats(CO.uvStats(this.items, this.live)); }
  find(id) { return this.items.find((it) => String(it.c.id) === String(id)) || null; }
  open(id) { const it = this.find(id); if (it && this.h.onOpen) { this.hideTip(); this.h.onOpen(it); } }

  /* ---------------- camera ---------------- */
  // the whole orrery, from above its plane on our side of Cymetica, as near as the outer orbit allows (a margin at
  // the top for the stage's own bar)
  home() {
    const Gx = CO.uvGalaxy, R = Gx.R1 + 16, dir = new THREE.Vector3().setFromSpherical(new THREE.Spherical(1, 1.06, Gx.AZ)), cam = this.camera.clone(), tgt = new THREE.Vector3(0, -4, 0), pts = [];
    if (this.el.clientWidth && this.el.clientHeight) { cam.aspect = this.el.clientWidth / this.el.clientHeight; cam.updateProjectionMatrix(); }
    for (let k = 0; k < 64; k++) { const a = k / 64 * Math.PI * 2; pts.push(new THREE.Vector3(Math.sin(a) * R, 0, Math.cos(a) * R), new THREE.Vector3(Math.sin(a) * R, 16, Math.cos(a) * R)); }
    pts.push(new THREE.Vector3(0, 48, 0));
    const fits = (d) => { cam.position.copy(tgt).addScaledVector(dir, d); cam.lookAt(tgt); cam.updateMatrixWorld(); return pts.every((p) => { const v = p.clone().project(cam); return Math.abs(v.x) < 0.98 && v.y < 0.82 && v.y > -0.96; }); };
    let d = 400;
    for (let pass = 0; pass < 2; pass++) {
      let lo = 40, hi = 6000; for (let i = 0; i < 26; i++) { const mid = (lo + hi) / 2; if (fits(mid)) hi = mid; else lo = mid; }
      d = hi; cam.position.copy(tgt).addScaledVector(dir, d); cam.lookAt(tgt); cam.updateMatrixWorld();
      // aim at the middle of the picture, not of the plane: the near half of an orbit seen from above is the bigger one
      let y0 = 1, y1 = -1; pts.forEach((p) => { const v = p.clone().project(cam); y0 = Math.min(y0, v.y); y1 = Math.max(y1, v.y); });
      const up = new THREE.Vector3().setFromMatrixColumn(cam.matrixWorld, 1), hh = 2 * d * Math.tan(THREE.MathUtils.degToRad(cam.fov) / 2);
      tgt.addScaledVector(up, ((y0 + y1) / 2 + 0.05) * hh / 2);
    }
    return { pos: tgt.clone().addScaledVector(dir, d), tgt };
  }
  fit(anim) {
    const h = this.home(); this.follow = null; this.followAt = null;
    if (!this.fitted && anim === false) {
      // the first look: from far outside, flying in
      this.fitted = true;
      this.camera.position.copy(h.pos.clone().multiplyScalar(2.3).add(new THREE.Vector3(0, 380, 0))); this.controls.target.copy(h.tgt);
      this.tween(h.pos, h.tgt, 3400); this.tw.home = true;
      return;
    }
    this.fitted = true;
    this.tween(h.pos, h.tgt, anim === false ? 0 : 1100);
  }
  zoom(f) {
    const t = this.controls.target, off = this.camera.position.clone().sub(t);
    const len = Math.max(this.controls.minDistance, Math.min(this.controls.maxDistance, off.length() * f));
    this.tween(t.clone().add(off.setLength(len)), t.clone(), 380);
  }
  flyTo(id, done, ms) {
    const it = this.find(id); if (!it || !it.plot) { if (done) done(); return; }
    const p = it.plot.root.position, tgt = new THREE.Vector3(p.x, p.y + (it.plot.top + it.plot.bot) * 0.5 * SS, p.z);
    const dir = this.camera.position.clone().sub(this.controls.target); if (dir.lengthSq() < 1e-6) dir.set(1, 0.6, 1);
    dir.y = Math.max(dir.y, dir.length() * 0.35); dir.normalize();
    const dist = (16 + (it.plot.top - it.plot.bot) * 1.4 + it.plot.b.foot * 0.9) * SS;
    this.follow = null; this.followAt = null;
    this.tween(tgt.clone().add(dir.multiplyScalar(dist)), tgt, ms == null ? 1300 : ms, () => { this.follow = it; this.followAt = null; if (done) done(); });
  }
  tween(pos, tgt, ms, done) {
    this.controls.autoRotate = false; this.lastUse = performance.now();
    if (!ms) { this.camera.position.copy(pos); this.controls.target.copy(tgt); this.controls.update(); this.tw = null; if (done) done(); return; }
    this.tw = { p0: this.camera.position.clone(), t0: this.controls.target.clone(), p1: pos.clone(), t1: tgt.clone(), s: performance.now(), ms, done };
  }
  resize() {
    const w = this.el.clientWidth, h = this.el.clientHeight; if (!w || !h) return;
    this.camera.aspect = w / h; this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h, false);
  }

  /* ---------------- the frame ---------------- */
  frame() {
    if (!this.visible()) return;
    // a page opened in a hidden tab learns its size late, and not always through ResizeObserver
    if (this.el.clientWidth !== this._cw || this.el.clientHeight !== this._ch) {
      this._cw = this.el.clientWidth; this._ch = this.el.clientHeight; this.resize();
      if (this.fitted && !this.used) { if (!this.tw) this.fit(false); else if (this.tw.home) { const h2 = this.home(); this.tw.p1 = h2.pos; this.tw.t1 = h2.tgt; } }
    }
    const t = this.clock.getElapsedTime(), now = performance.now();
    if (this.tw) {
      const k = Math.min(1, (now - this.tw.s) / this.tw.ms), e = k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
      this.camera.position.lerpVectors(this.tw.p0, this.tw.p1, e); this.controls.target.lerpVectors(this.tw.t0, this.tw.t1, e);
      if (k >= 1) { const d = this.tw.done; this.tw = null; if (d) d(); }
    }
    this.controls.update();
    // every station on its orbit: it moves on, bobs, turns slowly, and our own ring breathes; a station's halo,
    // what makes it a point of light from far off, gives way as the camera comes close
    const cam = this.camera.position, ss = THREE.MathUtils.smoothstep;
    this.items.forEach((it) => {
      const p = it.plot; if (!p) return;
      this.orbit(it, t);
      p.b.tick(t); p.body.position.y = Math.sin(t * 0.45 + p.b.phase) * 0.22; p.body.rotation.y = p.spin + t * 0.035;
      if (p.meRing) p.meRing.scale.setScalar(p.ringR * (1 + Math.sin(t * 2.4) * 0.05));
      p.halo.material.opacity = p.haloBase * 0.15 * ss(cam.distanceTo(p.root.position), 40, 160);
    });
    // a station the camera flew to: the camera goes along with it on its orbit
    if (this.follow && this.follow.plot) {
      const p = this.follow.plot.root.position;
      if (this.followAt && !this.tw) { const d = p.clone().sub(this.followAt); this.camera.position.add(d); this.controls.target.add(d); }
      this.followAt = (this.followAt || new THREE.Vector3()).copy(p);
    }
    // Cymetica: the filaments turn each their own way and flicker, the beams breathe, the sparks fly, the machine turns
    this.fil.forEach((f, i) => { f.rotation.set(t * (0.13 + i * 0.07) * (i % 2 ? -1 : 1), t * (0.21 + i * 0.05), t * 0.05 * i); f.material.opacity = 0.6 + 0.3 * Math.sin(t * (5 + i * 2.3) + i) * Math.sin(t * 1.7 + i); });
    this.beams.forEach((b) => { b.m.material.opacity = 0.15 + 0.3 * Math.max(0, Math.sin(t * 2.2 + b.ph)); });
    const sp = this.sparkPts.geometry.attributes.position, S2 = this.sparks;
    for (let i = 0; i < S2.N; i++) { const f = (t * S2.speed[i] * 0.35 + S2.ph[i]) % 1, r = 2.5 + f * 30, d = S2.dir[i]; sp.setXYZ(i, d.x * r, d.y * r, d.z * r); }
    sp.needsUpdate = true;
    this.machine.rotation.y = t * 0.06; this.gyro.rotation.set(1.15 + Math.sin(t * 0.2) * 0.1, t * 0.18, 0.3);
    this.coreRings.forEach((r, i) => { r.rotation.z = t * (0.05 + i * 0.03) * (i % 2 ? -1 : 1); });
    this.coneRings.forEach((r, i) => { r.rotation.z = t * (0.4 + i * 0.2) * (i % 2 ? -1 : 1); r.position.y = 4.5 + i * 3 + Math.sin(t * 1.3 + i) * 0.3; });
    this.corona[0].material.opacity = 0.65 + 0.12 * Math.sin(t * 2.1);
    this.moveShips(t);
    if (this.arcs.length) {
      this.arcs = this.arcs.filter((a) => {
        const f = (now - a.t0) / a.dur;
        if (f >= 1.25) { this.scene.remove(a.head, a.streak); a.tube.dispose(); a.mat.dispose(); return false; }
        const e = Math.min(1, f < 0.5 ? 2 * f * f : 1 - Math.pow(-2 * Math.min(f, 1) + 2, 2) / 2);
        a.head.position.copy(a.curve.getPoint(e)); a.head.visible = f < 1;
        const n = a.tube.index.count, seg = n / 64, from = Math.max(0, Math.min(f, 1.25) - 0.4) / 0.85, to = e, cnt = Math.max(0, Math.floor((to - from) * 64)) * seg;
        a.tube.setDrawRange(Math.floor(from * 64) * seg, cnt); a.streak.visible = cnt > 0;
        a.mat.opacity = 0.85 * (f > 1 ? 1 - (f - 1) / 0.25 : 1);
        return true;
      });
    }
    // the sky goes where the camera goes: it is as far as a sky is
    this.sky.position.copy(this.camera.position);
    if (this.mouseMoved) { this.mouseMoved = false; this.pick(); }
    // a GPU that cannot run a shader says so on the first frames: stop, and let the flat map take over
    try { if (this.post) this.post.render(); else this.renderer.render(this.scene, this.camera); this.frames = (this.frames || 0) + 1; }
    catch (e) { console.error('3D map stopped:', e); this.renderer.setAnimationLoop(null); if (this.h.onFail && !(this.frames > 30)) this.h.onFail(e); return; }
    this.overlay();
  }
  // the lights along the orbits: a head that glows and a short trail behind it
  moveShips(t) {
    const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), p = new THREE.Vector3(), dir = new THREE.Vector3(), fwd = new THREE.Vector3(0, 0, 1), s2 = new THREE.Vector3(0.2, 0.14, 7);
    this.ships.forEach((s, i) => {
      const L = s.L, a = s.a + t * L.speed;
      p.set(Math.sin(a) * L.r, 0, Math.cos(a) * L.r); s.head.position.copy(p);
      dir.set(Math.cos(a), 0, -Math.sin(a));
      q.setFromUnitVectors(fwd, dir); p.addScaledVector(dir, -3.6); m4.compose(p, q, s2); this.trailMesh.setMatrixAt(i, m4);
    });
    this.trailMesh.instanceMatrix.needsUpdate = true;
  }
  // The banners follow their stations. Ours, the hovered one and Cymetica's always show; the rest nearest first,
  // each only where no nearer one stands and only while its station is big enough on screen to be worth a name.
  overlay() {
    const w = this.el.clientWidth, h = this.el.clientHeight, v = new THREE.Vector3(), placed = [];
    // a still camera moves no banner: restyle them only when the view, the size, the hover or a station changed
    const key = this.camera.matrixWorld.elements.join(',') + '|' + w + 'x' + h + '|' + this.hover + '|' + this.items.length + '|' + this.built + '|' + Math.floor(performance.now() / 66);
    if (key === this.ovKey && !this.pops.length) return;
    this.ovKey = key;
    const f = h / (2 * Math.tan(THREE.MathUtils.degToRad(this.camera.fov) / 2)), cam = this.camera.position;
    const list = this.items.map((it) => {
      v.copy(it.anchor).project(this.camera); const d = cam.distanceTo(it.anchor);
      return { el: it.el, x: (v.x + 1) / 2 * w, y: (1 - v.y) / 2 * h, z: v.z, d, px: it.size * f / d, mine: it.mine, keep: it.mine || String(this.hover) === String(it.c.id) };
    });
    if (this.coreEl) { v.copy(this.coreAt).project(this.camera); list.push({ el: this.coreEl, x: (v.x + 1) / 2 * w, y: (1 - v.y) / 2 * h, z: v.z, d: cam.distanceTo(this.coreAt), px: 200, keep: true, core: true }); }
    list.sort((a, b) => (b.keep - a.keep) || a.d - b.d);
    // a galaxy with a name on every star reads as a list: at most this many names besides ours, Cymetica and the hovered
    let named = 0;
    list.forEach((o) => {
      const el = o.el; if (!el) return;
      if (!el._bw) el._bw = el.offsetWidth || 160;
      const s = o.core ? 1 : Math.max(0.86, Math.min(1, 0.6 + o.px / 120));
      const off = o.z > 1 || o.x < -80 || o.x > w + 80 || o.y < -40 || o.y > h + 60;
      const bw = el._bw * s, bh = (o.mine ? 48 : o.core ? 42 : 30) * s, r = { l: o.x - bw / 2, r: o.x + bw / 2, t: o.y - bh, b: o.y };
      const clash = placed.some((p) => r.l < p.r + 6 && r.r > p.l - 6 && r.t < p.b + 4 && r.b > p.t - 4);
      const show = !off && (o.keep || (!clash && o.px >= 24 && named < 14));
      if (show && !o.keep) named++;
      el.classList.toggle('hidden', !show);
      if (show) placed.push(r);
      el.style.transform = 'translate(' + o.x.toFixed(1) + 'px,' + o.y.toFixed(1) + 'px) translate(-50%,-100%) scale(' + s.toFixed(3) + ')';
      el.style.zIndex = String(o.keep ? 3000 : 2000 - Math.round(o.d));
    });
    this.pops.forEach((p) => {
      v.copy(p.it.anchor).project(this.camera);
      p.el.style.transform = 'translate(' + ((v.x + 1) / 2 * w).toFixed(1) + 'px,' + ((1 - v.y) / 2 * h - 46).toFixed(1) + 'px) translate(-50%,-100%)';
    });
  }

  /* ---------------- input ---------------- */
  bind() {
    const cv = this.renderer.domElement;
    let down = null;
    cv.addEventListener('pointerdown', (e) => { down = { x: e.clientX, y: e.clientY }; this.lastUse = performance.now(); });
    cv.addEventListener('pointermove', (e) => { this.setMouse(e); this.mouseMoved = true; this.lastEv = e; });
    cv.addEventListener('pointerenter', () => { this.mouseIn = true; });
    cv.addEventListener('pointerleave', () => { this.mouseIn = false; this.setHover(null); this.hideTip(); });
    cv.addEventListener('pointerup', (e) => {
      if (!down) return;
      const moved = Math.abs(e.clientX - down.x) + Math.abs(e.clientY - down.y) > 5; down = null;
      if (moved) return;
      this.setMouse(e); const id = this.pickId();
      if (id != null && id !== 'core') this.open(id);
    });
    cv.addEventListener('wheel', () => { this.tw = null; this.lastUse = performance.now(); }, { passive: true });
  }
  setMouse(e) { const r = this.renderer.domElement.getBoundingClientRect(); this.mouse.set((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1); }
  pickId() {
    this.ray.setFromCamera(this.mouse, this.camera);
    const hits = this.ray.intersectObjects(this.items.filter((it) => it.plot).map((it) => it.plot.hit).concat([this.coreHit]), false);
    return hits.length ? hits[0].object.userData.id : null;
  }
  pick() {
    const id = this.pickId();
    this.setHover(id);
    if (id == null) return this.hideTip();
    const html = this.tipHTML(id); if (!html || !this.lastEv) return this.hideTip();
    this.showTip(html, this.lastEv);
  }
  setHover(id, fromBanner) {
    if (String(this.hover) === String(id)) return;
    const old = this.hover != null && this.find(this.hover);
    if (old && old.plot) { old.plot.rimMat.emissiveIntensity = RING[old.plot.pub ? 'pub' : 'priv']; if (old.el) old.el.classList.remove('hov'); }
    if (this.coreEl) this.coreEl.classList.toggle('hov', id === 'core');
    this.hover = id;
    const it = id != null && this.find(id);
    if (it && it.plot) { it.plot.rimMat.emissiveIntensity = RING.hover; if (it.el) it.el.classList.add('hov'); }
    this.renderer.domElement.style.cursor = id != null && id !== 'core' ? 'pointer' : '';
    if (fromBanner) {
      if (id == null) this.hideTip();
      else { const el = id === 'core' ? this.coreEl : it && it.el, html = this.tipHTML(id), r = el && el.getBoundingClientRect(); if (html && r) this.showTip(html, { clientX: r.left + r.width / 2, clientY: r.bottom + 6 }); }
    }
  }
  tipHTML(id) { return CO.uvTip(id, id === 'core' ? null : this.find(id), this.live); }
  showTip(html, e) {
    const r = this.stage.getBoundingClientRect();
    this.tip.innerHTML = html; this.tip.hidden = false;
    let x = e.clientX - r.left + 16, y = e.clientY - r.top + 16;
    if (x + this.tip.offsetWidth > r.width - 8) x = e.clientX - r.left - this.tip.offsetWidth - 16;
    if (y + this.tip.offsetHeight > r.height - 8) y = e.clientY - r.top - this.tip.offsetHeight - 16;
    this.tip.style.left = x + 'px'; this.tip.style.top = y + 'px';
  }
  hideTip() { if (this.tip) this.tip.hidden = true; }
}
function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }

/* ---------------- one station, turning slowly in space: Settings, Create your company, a private company's card ---------------- */
const PREVIEWS = [];
class Preview {
  constructor(el) {
    geo();
    this.el = el; this.wrap = document.createElement('div'); this.wrap.className = 'pv3';
    this.ban = document.createElement('div'); this.ban.className = 'b3 pvb'; this.wrap.appendChild(this.ban);
    el.appendChild(this.wrap);
    this.scene = new THREE.Scene(); this.scene.background = new THREE.Color(0x020306);
    this.camera = new THREE.PerspectiveCamera(30, 1, 0.1, 600);
    this.renderer = new THREE.WebGPURenderer({ antialias: false });   // see Universe3D: the pass multisamples
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping; this.renderer.toneMappingExposure = 1.15;
    this.wrap.insertBefore(this.renderer.domElement, this.ban);
    this.scene.add(new THREE.HemisphereLight(0xdfe8f2, 0x05070a, 0.8), new THREE.AmbientLight(0x1a2230, 0.7));
    const sun = new THREE.DirectionalLight(0xf4f8fc, 2.0); sun.position.set(-8, 12, 6); this.scene.add(sun);
    const rim = new THREE.DirectionalLight(0x00cfff, 0.6); rim.position.set(9, 2, -9); this.scene.add(rim);
    // space behind it: stars, and the site's colours glowing far off
    this.scene.add(starField(1400, 140, 90, 1.0, 21));
    [[0x00cfff, 0.18, [-22, 6, -26], 46], [0x00ff88, 0.09, [16, -8, -30], 40], [0x3b82f6, 0.08, [-30, -10, 8], 36]].forEach(([c, o, p, s]) => {
      const sp = glowSprite(c, o, s); sp.position.set(p[0], p[1], p[2]); this.scene.add(sp);
    });
    this.turn = new THREE.Group(); this.scene.add(this.turn);
    this.clock = new THREE.Clock(); this.key = '';
    this.renderer.init().then(() => {
      try { this.post = new Post(this.renderer, this.scene, this.camera, 0.8, 0.45, 0.7); } catch (e) { this.post = null; }
      this.renderer.setAnimationLoop(() => this.frame());
      el.classList.add('has3d');
    }).catch(() => { this.dead = true; });
  }
  set(o) {
    const key = [o.skin, o.accent, o.floors, o.public, o.name, o.you].join('|');
    if (key === this.key) return; this.key = key;
    if (this.plot) { this.turn.remove(this.plot.root); release(this.plot.root); }
    const c = { skin: o.skin, accent: o.accent, public: !!o.public || !!o.you, departments: new Array(Math.max(1, o.floors || 1)).fill(0), status: 'active' };
    this.plot = makeStation(c, o.seed || 7, { mine: !!o.you });
    this.plot.b.paint([], o.public || o.you ? '' : 'priv');
    this.plot.halo.material.opacity = 0.1;   // up close: an aura, not a fog
    this.turn.add(this.plot.root);
    // framed with room above it for the name
    const top = this.plot.top, bot = this.plot.bot, size = Math.max(top - bot, this.plot.b.foot * 1.5), dist = size * 2.4 + 5;
    this.target = new THREE.Vector3(0, (top + bot) / 2 + size * 0.13, 0);
    this.camera.position.copy(new THREE.Vector3().setFromSpherical(new THREE.Spherical(dist, 1.16, Math.PI / 4)).add(this.target));
    this.camera.lookAt(this.target);
    this.anchor = new THREE.Vector3(0, top + 0.3, 0);
    let name = String(o.name || '').toUpperCase(); if (name.length > 22) name = name.slice(0, 21) + '…';
    this.ban.className = 'b3 pvb' + (!o.public && !o.you ? ' priv' : '');
    this.ban.style.setProperty('--acc', CO.accentHex(o.accent));
    this.ban.innerHTML = name ? (o.you ? '<span class="you">YOU</span>' : '') + '<span class="rib">' + (!o.public ? '<i class="lk"></i>' : '') + esc(name) + '</span><span class="teth"></span>' : '';
    this.ban.hidden = !name;
  }
  frame() {
    const w = this.wrap.clientWidth, h = this.wrap.clientHeight;
    if (!w || !h || !document.body.contains(this.el)) return;
    if (this.w !== w || this.h !== h) { this.w = w; this.h = h; this.camera.aspect = w / h; this.camera.updateProjectionMatrix(); this.renderer.setSize(w, h, false); }
    const t = this.clock.getElapsedTime();
    this.turn.rotation.y = t * 0.28;
    if (this.plot) { this.plot.b.tick(t); this.plot.body.position.y = Math.sin(t * 0.6) * 0.15; }
    if (this.post) this.post.render(); else this.renderer.render(this.scene, this.camera);
    if (this.anchor) {
      const v = this.anchor.clone().project(this.camera);
      this.ban.style.transform = 'translate(' + ((v.x + 1) / 2 * w).toFixed(1) + 'px,' + ((1 - v.y) / 2 * h).toFixed(1) + 'px) translate(-50%,-100%)';
    }
  }
  dispose() { try { this.renderer.setAnimationLoop(null); this.renderer.dispose(); } catch (e) { /* gone */ } this.wrap.remove(); this.dead = true; }
}
// The six stations as still pictures for the picker, in the colour asked for: drawn once by a renderer of their
// own that is let go afterwards, read back from a render target, kept as images. Width 320 keeps every row of the
// read-back on WebGPU's 256-byte boundary. Until they are ready (or where they cannot be drawn) the flat
// pictures stay.
const THUMBS = {}, THUMB_Q = {};
function thumbs(hex, done) {
  if (THUMBS[hex]) return done(THUMBS[hex]);
  if (THUMB_Q[hex]) return THUMB_Q[hex].push(done);
  THUMB_Q[hex] = [done];
  geo();
  const W = 320, H = 200, renderer = new THREE.WebGPURenderer({ antialias: false });
  renderer.setPixelRatio(1); renderer.setSize(W, H, false);
  renderer.toneMapping = THREE.ACESFilmicToneMapping; renderer.toneMappingExposure = 1.2;
  const scene = new THREE.Scene(); scene.background = new THREE.Color(0x03060b);
  scene.add(new THREE.HemisphereLight(0xdfe8f2, 0x05070a, 0.9), new THREE.AmbientLight(0x1a2230, 0.8));
  const sun = new THREE.DirectionalLight(0xf4f8fc, 2.1); sun.position.set(-8, 12, 6); scene.add(sun);
  const rim = new THREE.DirectionalLight(0x00cfff, 0.6); rim.position.set(9, 2, -9); scene.add(rim);
  scene.add(starField(900, 90, 60, 0.9, 31));
  [[0x00cfff, 0.14, [-16, 6, -20], 34], [0x00ff88, 0.07, [14, -6, -24], 30]].forEach(([c, o, p, s]) => { const sp = glowSprite(c, o, s); sp.position.set(p[0], p[1], p[2]); scene.add(sp); });
  const camera = new THREE.PerspectiveCamera(30, W / H, 0.1, 400), rt = new THREE.RenderTarget(W, H);
  const acc = CO.ACCENTS.find((a) => a.hex === hex), key = acc ? acc.key : 'green';
  const out = {}, finish = () => { THUMBS[hex] = out; const q = THUMB_Q[hex]; delete THUMB_Q[hex]; q.forEach((f) => f(out)); try { rt.dispose(); renderer.dispose(); } catch (e) { /* gone */ } };
  renderer.init().then(async () => {
    let post = null; try { post = new Post(renderer, scene, camera, 0.85, 0.45, 0.7); } catch (e) { post = null; }
    for (const s of CO.SKINS) {
      const p = makeStation({ skin: s.key, accent: key, public: true, departments: [0, 0, 0], status: 'active' }, 11, {});
      p.b.paint([1], ''); p.halo.material.opacity = 0.08; p.b.tick(1.2);
      p.root.rotation.y = s.key === 'rocket' ? -0.5 : 0.25; scene.add(p.root);
      const size = Math.max(p.top - p.bot, p.b.foot * 1.55), tgt = new THREE.Vector3(0, (p.top + p.bot) / 2, 0);
      camera.position.copy(new THREE.Vector3().setFromSpherical(new THREE.Spherical(size * 1.5 + 2.5, 1.12, Math.PI / 4)).add(tgt)); camera.lookAt(tgt);
      // the bloom pass draws the scene once a frame: two frames between pictures, or on a fast GPU all six are the first
      await new Promise((r) => requestAnimationFrame(() => requestAnimationFrame(r)));
      renderer.setRenderTarget(rt);
      if (post) post.render(); else renderer.render(scene, camera);
      renderer.setRenderTarget(null);
      const px = await renderer.readRenderTargetPixelsAsync(rt, 0, 0, W, H), flip = !(renderer.backend && renderer.backend.isWebGPUBackend);
      const c = document.createElement('canvas'); c.width = W; c.height = H; const g = c.getContext('2d'), img = g.createImageData(W, H);
      for (let y = 0; y < H; y++) { const sy = flip ? H - 1 - y : y; img.data.set(px.subarray(sy * W * 4, (sy + 1) * W * 4), y * W * 4); }
      for (let i = 3; i < img.data.length; i += 4) img.data[i] = 255;
      g.putImageData(img, 0, 0); out[s.key] = c.toDataURL('image/png');
      scene.remove(p.root); release(p.root);
    }
    finish();
  }).catch(() => finish());
}
// a preview lives as long as its element: one left behind by a closed card or a re-render is let go
setInterval(() => {
  for (let i = PREVIEWS.length - 1; i >= 0; i--) {
    const p = PREVIEWS[i];
    if (p.dead || !document.body.contains(p.el)) { if (!p.dead) p.dispose(); PREVIEWS.splice(i, 1); }
  }
}, 1500);
function preview(el, o) {
  if (!el) return null;
  let p = el.__pv;
  if (!p || p.dead) { p = new Preview(el); el.__pv = p; PREVIEWS.push(p); }
  p.set(o);
  return p;
}

/* ---------------- the office in 3D: the same floor plan, rooms you can walk the camera into ---------------- */
// What a room is doing, in light. Blue is only "up next", and only on the room's edge line: the floor, the walls,
// the furniture and the light itself are the site's navy-black under white light, the structure Cymetica green.
const STC = { working: 0x00cfff, queued: 0x3b82f6, waiting: 0xff4444, idle: 0x7f93ad };
const TONEC = { cyan: '#00cfff', red: '#ff4444', blue: '#dfe6ee', dim: '#a9b8cc' };   // "Up next" white on a plate; its dot stays blue
const OFFICE = { bg: 0x020409, lamp: 0xf2f6fa, mon: 0x6f8f80 };
const WH = 2.3;   // a room's glass walls: a third of its width, as in the picture
const OM = {};

/* ---------------- space: the sky the office floats in ---------------- */
function ctex(w, h, draw) {
  const c = document.createElement('canvas'); c.width = w; c.height = h; draw(c.getContext('2d'), w, h);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
}
const sstep = (a, b, x) => { const t = Math.min(1, Math.max(0, (x - a) / (b - a))); return t * t * (3 - 2 * t); };
// value noise in octaves, seeded: what nebulae, rock and dust are drawn from
function vnoise(seed) {
  const h = (x, y) => { let n = Math.imul(x, 374761393) ^ Math.imul(y, 668265263) ^ Math.imul(seed + 1, 982451653); n = Math.imul(n ^ (n >>> 13), 1274126177); return ((n ^ (n >>> 16)) >>> 0) / 4294967296; };
  const n2 = (x, y) => {
    const xi = Math.floor(x), yi = Math.floor(y), xf = x - xi, yf = y - yi, u = xf * xf * (3 - 2 * xf), v = yf * yf * (3 - 2 * yf);
    const a = h(xi, yi), b = h(xi + 1, yi), c = h(xi, yi + 1), d = h(xi + 1, yi + 1);
    return a + (b - a) * u + (c - a) * v + (a - b - c + d) * u * v;
  };
  return (x, y, oct = 5) => { let s = 0, a = 0.5, f = 1, n = 0; for (let i = 0; i < oct; i++) { s += a * n2(x * f, y * f); n += a; a *= 0.5; f *= 2.03; } return s / n; };
}
// a direction in the sky, measured from the office's home view: azimuth (+ right) and elevation, in degrees
function skyDir(az, el) {
  const a = az * Math.PI / 180, e = el * Math.PI / 180, f = new THREE.Vector3(-1, 0, -1).normalize(), r = new THREE.Vector3(1, 0, -1).normalize();
  return f.multiplyScalar(Math.cos(a)).addScaledVector(r, Math.sin(a)).multiplyScalar(Math.cos(e)).add(new THREE.Vector3(0, Math.sin(e), 0)).normalize();
}
// a nebula: warped noise inside a ragged edge, deep colour where it is thin, bright filaments where it is dense,
// dark dust lanes across it. Alpha carries the density, so it adds onto the black.
function nebTex(seed, deep, mid, hi) {
  const key = 'neb' + seed; if (TX[key]) return TX[key];
  const N = 384, f = vnoise(seed), f2 = vnoise(seed + 11), c = document.createElement('canvas'); c.width = c.height = N;
  const g = c.getContext('2d'), img = g.createImageData(N, N), d = img.data;
  for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) {
    const x = i / N * 2 - 1, y = j / N * 2 - 1, rr = Math.sqrt(x * x + y * y); if (rr > 1.05) continue;
    const edge = sstep(1.0, 0.15, rr + 0.5 * (f(x * 1.6 + 3, y * 1.6 + 1, 3) - 0.5)); if (edge <= 0) continue;
    const q = f(x * 2.1 + 1.7, y * 2.1 + 9.2, 4), n = f(x * 2.7 + q * 2.2, y * 2.7 + q * 2.2 + 3.1, 5);
    let den = edge * sstep(0.3, 0.66, n);
    den *= 1 - 0.6 * sstep(0.5, 0.72, f2(x * 4.5 + 2, y * 4.5 + 7, 4));
    const hh = sstep(0.56, 0.8, n) * edge, k = (j * N + i) * 4;
    for (let ch = 0; ch < 3; ch++) d[k + ch] = Math.min(255, deep[ch] + (mid[ch] - deep[ch]) * den + hi[ch] * hh);
    d[k + 3] = Math.min(255, (den * 1.1 + hh * 0.7) * 255);
  }
  g.putImageData(img, 0, 0);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; TX[key] = t; return t;
}
function starTex() {
  return TX.star || (TX.star = ctex(64, 64, (g) => {
    const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.1, 'rgba(255,255,255,.95)'); gr.addColorStop(0.28, 'rgba(200,235,255,.2)'); gr.addColorStop(1, 'rgba(200,235,255,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
  }));
}
// The sky: a group that rides with the camera (frame() moves it), so all of it is at infinity. Teal nebulae up
// and to the left of the home view as in the operator's picture, fainter blue and green ones round the rest; faint
// stars are points (one pixel), the bright ones small quads, since WebGPU draws every point one pixel wide.
function spaceSky() {
  const g = new THREE.Group(), R = rng(31), D = 380;
  const PAL = { teal: [[0, 40, 55], [0, 112, 122], [80, 190, 185]], blue: [[6, 26, 80], [30, 95, 200], [140, 190, 255]], green: [[0, 60, 45], [0, 150, 110], [120, 250, 190]] };
  [[-36, -12, 66, 8, 0.4, 'teal'], [-62, -32, 56, 3, 0.55, 'teal'], [-6, -8, 44, 37, 0.12, 'blue'], [34, -52, 60, 13, 0.1, 'blue'],
    [150, -15, 80, 17, 0.55, 'teal'], [95, -35, 60, 23, 0.35, 'green'], [-130, -30, 70, 29, 0.45, 'blue']].forEach(([az, el, size, seed, op, tone]) => {
    const m = new THREE.Mesh(G.plane, new THREE.MeshBasicMaterial({ map: nebTex(seed, ...PAL[tone]), transparent: true, opacity: op, blending: THREE.AdditiveBlending, depthWrite: false, fog: false }));
    const s = 2 * D * Math.tan(size * Math.PI / 360);
    m.scale.set(s, s, 1); m.position.copy(skyDir(az, el).multiplyScalar(D)); m.lookAt(0, 0, 0); m.rotateZ(R() * 6.28); m.renderOrder = -10; m.frustumCulled = false; g.add(m);
  });
  const rnd = () => { const u = R() * 2 - 1, th = R() * Math.PI * 2, s = Math.sqrt(1 - u * u); return new THREE.Vector3(Math.cos(th) * s, u, Math.sin(th) * s); };
  const N = 3200, pos = new Float32Array(N * 3), col = new Float32Array(N * 3), cc = new THREE.Color();
  for (let i = 0; i < N; i++) {
    pos.set(rnd().multiplyScalar(360).toArray(), i * 3);
    cc.set(R() < 0.1 ? 0x9fe8ff : 0xeef4fa).multiplyScalar(0.25 + R() * R() * 1.1); col.set([cc.r, cc.g, cc.b], i * 3);
  }
  const pg = new THREE.BufferGeometry(); pg.setAttribute('position', new THREE.BufferAttribute(pos, 3)); pg.setAttribute('color', new THREE.BufferAttribute(col, 3));
  pg.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(N * 3).map((v, i) => (i % 3 === 1 ? 1 : 0)), 3));
  const pts = new THREE.Points(pg, new THREE.PointsMaterial({ vertexColors: true, size: 1, sizeAttenuation: false, fog: false, depthWrite: false })); pts.frustumCulled = false; g.add(pts);
  const B = 240, im = new THREE.InstancedMesh(G.plane, new THREE.MeshBasicMaterial({ map: starTex(), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, fog: false }), B), o = new THREE.Object3D();
  for (let i = 0; i < B; i++) {
    o.position.copy(rnd().multiplyScalar(350)); o.lookAt(0, 0, 0); o.scale.setScalar(0.9 + R() * R() * 2.8); o.updateMatrix(); im.setMatrixAt(i, o.matrix);
    im.setColorAt(i, cc.set(R() < 0.14 ? 0x9fe8ff : 0xffffff).multiplyScalar(0.55 + R() * 0.75));
  }
  im.frustumCulled = false; g.add(im);
  return g;
}
// what shiny surfaces see: a dark room with soft panels of light overhead and a cyan one low on a side
function envTex() {
  if (TX.env) return TX.env;
  const t = ctex(512, 256, (g, W, H) => {
    const gr = g.createLinearGradient(0, 0, 0, H); gr.addColorStop(0, '#46525f'); gr.addColorStop(0.42, '#121820'); gr.addColorStop(1, '#040609'); g.fillStyle = gr; g.fillRect(0, 0, W, H);
    [[0.18, 0.16, 0.18, 0.08, 'rgba(255,255,255,.95)'], [0.55, 0.1, 0.22, 0.07, 'rgba(255,255,255,.8)'], [0.82, 0.22, 0.1, 0.1, 'rgba(255,255,255,.6)'], [0.36, 0.4, 0.12, 0.1, 'rgba(0,207,255,.45)']].forEach(([x, y, w, h, c]) => {
      g.fillStyle = c; g.filter = 'blur(6px)'; g.fillRect(x * W, y * H, w * W, h * H); g.filter = 'none';
    });
  });
  t.mapping = THREE.EquirectangularReflectionMapping; TX.env = t; return t;
}

/* ---------------- the office's surfaces ---------------- */
function deckTex() {
  return TX.deck || (TX.deck = ctex(512, 512, (g, W) => {
    const R = rng(23), s = W / 8;
    g.fillStyle = '#16191e'; g.fillRect(0, 0, W, W);
    for (let i = 0; i < 8; i++) for (let j = 0; j < 8; j++) { const v = 46 + Math.floor(R() * 9); g.fillStyle = 'rgb(' + v + ',' + (v + 4) + ',' + (v + 9) + ')'; g.fillRect(i * s + 1.5, j * s + 1.5, s - 3, s - 3); }
    g.fillStyle = 'rgba(255,255,255,.05)'; for (let i = 0; i < 8; i++) for (let j = 0; j < 8; j++) g.fillRect(i * s + 2, j * s + 2, s - 4, 2);
  }));
}
function tileTex() {
  return TX.tile || (TX.tile = ctex(512, 512, (g, W) => {
    const R = rng(29), s = W / 7;
    g.fillStyle = '#121519'; g.fillRect(0, 0, W, W);
    for (let i = 0; i < 7; i++) for (let j = 0; j < 7; j++) { const v = 36 + Math.floor(R() * 6); g.fillStyle = 'rgb(' + v + ',' + (v + 4) + ',' + (v + 9) + ')'; g.fillRect(i * s + 1, j * s + 1, s - 2, s - 2); }
    g.strokeStyle = 'rgba(255,255,255,.04)'; g.lineWidth = 1; for (let i = 0; i < 7; i++) for (let j = 0; j < 7; j++) { g.strokeRect(i * s + 8, j * s + 8, s - 16, s - 16); }
  }));
}
// the hull's plates: four to a side, each with its recess, its seams and vents; some carry a lit blue window and
// every one a row of small lights (the glow map holds only what shines)
function hullTex() {
  if (TX.hull) return TX.hull;
  const W = 1024, H = 200, R = rng(41), lit = [0, 1, 2, 3].map(() => R() < 0.5);
  const draw = (glow) => (g) => {
    g.fillStyle = glow ? '#000000' : '#18202b'; g.fillRect(0, 0, W, H);
    for (let p = 0; p < 4; p++) {
      const x = p * 256;
      if (!glow) {
        g.fillStyle = '#222c39'; g.fillRect(x + 8, 10, 240, H - 20);
        g.fillStyle = '#151c26'; g.fillRect(x + 26, 30, 204, H - 82);
        g.fillStyle = 'rgba(255,255,255,.12)'; g.fillRect(x + 8, 10, 240, 3);
        g.fillStyle = '#0b0f15'; g.fillRect(x, 0, 6, H);
        for (let k = 0; k < 6; k++) g.fillRect(x + 40 + k * 30, H - 40, 18, 4);
      }
      if (lit[p]) { g.fillStyle = glow ? '#3b82f6' : '#1d3a6a'; g.fillRect(x + 36, 42, 184, 24); g.fillStyle = glow ? '#173a75' : '#1a2f55'; g.fillRect(x + 36, 72, 184, 14); }
      for (let k = 0; k < 4; k++) { g.fillStyle = k % 3 ? (glow ? '#00cfff' : '#0b4c63') : (glow ? '#e6f4ff' : '#5b6876'); g.fillRect(x + 36 + k * 56, H - 24, 9, 6); }
    }
  };
  TX.hull = ctex(W, H, draw(false)); TX.hullGlow = ctex(W, H, draw(true)); return TX.hull;
}
function rackTex() {
  if (TX.rack) return TX.rack;
  const draw = (glow) => (g, W, H) => {
    g.fillStyle = glow ? '#000000' : '#13171c'; g.fillRect(0, 0, W, H);
    const n = 12, step = (H - 20) / n;
    for (let i = 0; i < n; i++) {
      const y = 10 + i * step, h = step - 4, k = (i * 37) % 5;
      if (!glow) { g.fillStyle = '#1e242b'; g.fillRect(8, y, W - 16, h); g.fillStyle = '#0c0f13'; for (let x = 14; x < W - 44; x += 6) g.fillRect(x, y + 3, 3, h - 6); }
      g.fillStyle = k < 2 ? '#00ff88' : k < 4 ? '#00cfff' : '#3b82f6';
      g.fillRect(W - 32, y + h / 2 - 2, 6, 4); if (k % 2) g.fillRect(W - 21, y + h / 2 - 2, 6, 4);
    }
    if (!glow) { g.strokeStyle = '#2b333c'; g.lineWidth = 5; g.strokeRect(2, 2, W - 4, H - 4); }
  };
  TX.rack = ctex(128, 320, draw(false)); TX.rackGlow = ctex(128, 320, draw(true)); return TX.rack;
}
function solarTex() {
  return TX.solar || (TX.solar = ctex(256, 256, (g, W) => {
    g.fillStyle = '#7f93ad'; g.fillRect(0, 0, W, W);
    const n = 4, s = (W - 12) / n;
    for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
      const x = 6 + i * s, y = 6 + j * s, gr = g.createLinearGradient(x, y, x + s, y + s);
      gr.addColorStop(0, '#1d55bb'); gr.addColorStop(1, '#12387f'); g.fillStyle = gr; g.fillRect(x + 2, y + 2, s - 4, s - 4);
      g.strokeStyle = 'rgba(120,170,255,.3)'; g.lineWidth = 1;
      for (let k = 1; k < 4; k++) { const o = 2 + k * (s - 4) / 4; g.beginPath(); g.moveTo(x + o, y + 2); g.lineTo(x + o, y + s - 2); g.moveTo(x + 2, y + o); g.lineTo(x + s - 2, y + o); g.stroke(); }
    }
  }));
}
// 3D gradient noise (Perlin's improved noise), seeded: the asteroids' shape, craters and colour come from it
function perlin3(seed) {
  const R = rng(seed), perm = Array.from({ length: 256 }, (_, i) => i), p = new Uint8Array(512);
  for (let i = 255; i > 0; i--) { const j = Math.floor(R() * (i + 1)), t = perm[i]; perm[i] = perm[j]; perm[j] = t; }
  for (let i = 0; i < 512; i++) p[i] = perm[i & 255];
  const fade = (t) => t * t * t * (t * (t * 6 - 15) + 10), lerp = (a, b, t) => a + t * (b - a);
  const grad = (h, x, y, z) => { h &= 15; const u = h < 8 ? x : y, v = h < 4 ? y : (h === 12 || h === 14 ? x : z); return ((h & 1) ? -u : u) + ((h & 2) ? -v : v); };
  return (x, y, z) => {
    const fx = Math.floor(x), fy = Math.floor(y), fz = Math.floor(z), X = fx & 255, Y = fy & 255, Z = fz & 255;
    x -= fx; y -= fy; z -= fz;
    const u = fade(x), v = fade(y), w = fade(z);
    const A = p[X] + Y, AA = p[A] + Z, AB = p[A + 1] + Z, B = p[X + 1] + Y, BA = p[B] + Z, BB = p[B + 1] + Z;
    return lerp(lerp(lerp(grad(p[AA], x, y, z), grad(p[BA], x - 1, y, z), u), lerp(grad(p[AB], x, y - 1, z), grad(p[BB], x - 1, y - 1, z), u), v),
      lerp(lerp(grad(p[AA + 1], x, y, z - 1), grad(p[BA + 1], x - 1, y, z - 1), u), lerp(grad(p[AB + 1], x, y - 1, z - 1), grad(p[BB + 1], x - 1, y - 1, z - 1), u), v), w);
  };
}
// An asteroid, to the operator's picture: a lumpy body, crags on it, craters with raised rims pressed in, fine grit
// over all of it; smooth-shaded (the sphere's vertices welded, so the light runs over it instead of breaking on
// facets) and coloured per vertex -- dark charcoal, a little lighter on the crests, darkest in the hollows.
function asteroidGeo(seed, detail = 64, flatTop = true) {
  let g = new THREE.IcosahedronGeometry(1, detail);
  g.deleteAttribute('normal'); g.deleteAttribute('uv'); g = mergeVertices(g);
  const P = perlin3(seed), pos = g.attributes.position, v = new THREE.Vector3(), n = pos.count, col = new Float32Array(n * 3), R = rng(seed + 7);
  const fbm = (x, y, z, o) => { let s = 0, a = 0.5, f = 1; for (let i = 0; i < o; i++) { s += a * P(x * f, y * f, z * f); a *= 0.5; f *= 2.03; } return s; };
  const ridge = (x, y, z, o) => { let s = 0, a = 0.5, f = 1; for (let i = 0; i < o; i++) { const r = 1 - Math.abs(P(x * f + 31.7, y * f + 7.1, z * f)); s += a * r * r; a *= 0.5; f *= 2.1; } return s; };
  const craters = [];
  for (let i = 0; i < 30; i++) craters.push({ c: new THREE.Vector3(R() * 2 - 1, R() * 2 - 1, R() * 2 - 1).normalize(), r: 0.05 + Math.pow(R(), 2.2) * 0.3, d: 0.35 + R() * 0.45 });
  const dark = [0.008, 0.008, 0.009], mid = [0.034, 0.032, 0.031], light = [0.1, 0.094, 0.088];
  for (let i = 0; i < n; i++) {
    v.fromBufferAttribute(pos, i);
    let h = 0.34 * fbm(v.x * 1.15, v.y * 1.15, v.z * 1.15, 4) + 0.17 * (ridge(v.x * 2.4, v.y * 2.4, v.z * 2.4, 5) - 0.45) + 0.05 * (ridge(v.x * 7, v.y * 7, v.z * 7, 3) - 0.45) + 0.03 * fbm(v.x * 16, v.y * 16, v.z * 16, 2);
    let pit = 0;
    for (const k of craters) {
      const x = Math.acos(Math.max(-1, Math.min(1, v.dot(k.c)))) / k.r;
      if (x < 1) { const d = -k.r * k.d * (1 - x * x); h += d; pit = Math.max(pit, 1 - x); }
      else if (x < 1.6) h += k.r * k.d * 0.28 * Math.pow(1 - (x - 1) / 0.6, 2);
    }
    v.multiplyScalar(1 + h);
    if (flatTop && v.y > 0.22) v.y = 0.22 + (v.y - 0.22) * 0.25; else if (flatTop) v.y *= 1.12;
    pos.setXYZ(i, v.x, v.y, v.z);
    // colour: crests a little lighter, hollows and crater floors darker, a speckle of lighter grit
    const t = Math.max(0, Math.min(1, 0.5 + h * 1.4 + 0.35 * fbm(v.x * 6 + 11, v.y * 6, v.z * 6, 3) - pit * 0.35));
    const s = R() < 0.04 ? 0.35 : 0, a = t < 0.5 ? t * 2 : (t - 0.5) * 2, lo = t < 0.5 ? dark : mid, hi = t < 0.5 ? mid : light;
    for (let ch = 0; ch < 3; ch++) col[i * 3 + ch] = lo[ch] + (hi[ch] - lo[ch]) * a + s * light[ch];
  }
  g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  g.computeVertexNormals();
  return g;
}
function monTex() {
  return TX.mon || (TX.mon = ctex(256, 144, (g, W) => {
    g.fillStyle = '#04140e'; g.fillRect(0, 0, W, 144);
    g.strokeStyle = '#00ff88'; g.lineWidth = 3; g.beginPath();
    let y = 96; for (let x = 12; x < W - 10; x += 12) { y = Math.max(40, Math.min(112, y + Math.sin(x * 0.13) * 13 + (x % 36 ? -5 : 9))); if (x === 12) g.moveTo(x, y); else g.lineTo(x, y); } g.stroke();
    g.fillStyle = 'rgba(0,255,136,.35)'; for (let i = 0; i < 8; i++) g.fillRect(14 + i * 29, 120, 18, 14 - (i % 3) * 4);
    g.fillStyle = '#00ff88'; g.fillRect(14, 12, 64, 8); g.fillStyle = 'rgba(0,255,136,.5)'; g.fillRect(14, 26, 104, 5);
  }));
}
// a hologram's face: a faint cyan field, a border, a trace and bars
function holoTex() {
  return TX.holo || (TX.holo = ctex(256, 176, (g, W, H) => {
    g.fillStyle = 'rgba(0,207,255,.12)'; g.fillRect(0, 0, W, H); g.strokeStyle = 'rgba(0,207,255,.95)'; g.lineWidth = 4; g.strokeRect(3, 3, W - 6, H - 6);
    g.strokeStyle = 'rgba(0,255,136,.95)'; g.lineWidth = 3; g.beginPath(); for (let x = 14; x < W - 14; x += 6) { const y = H * 0.42 + Math.sin(x * 0.09) * 18 * Math.sin(x * 0.021); if (x === 14) g.moveTo(x, y); else g.lineTo(x, y); } g.stroke();
    g.fillStyle = 'rgba(0,207,255,.8)'; for (let i = 0; i < 9; i++) g.fillRect(16 + i * 25, H - 20 - (i * 13 % 34), 14, 8 + (i * 13 % 34));
  }));
}
// a grid of light that wraps round a cylinder: the Add department pad's wall
function gridTex() {
  if (TX.grid) return TX.grid;
  const t = ctex(256, 64, (g, W, H) => {
    g.fillStyle = 'rgba(0,207,255,.10)'; g.fillRect(0, 0, W, H);
    g.strokeStyle = 'rgba(0,207,255,.75)'; g.lineWidth = 1.5;
    for (let x = 0; x <= W; x += 8) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, H); g.stroke(); }
    for (let y = 0; y <= H; y += 8) { g.beginPath(); g.moveTo(0, y); g.lineTo(W, y); g.stroke(); }
    g.fillStyle = 'rgba(0,207,255,1)'; g.fillRect(0, 0, W, 4); g.fillRect(0, H - 4, W, 4);
  });
  t.wrapS = THREE.RepeatWrapping; t.repeat.set(8, 1); TX.grid = t; return t;
}
// the Manager's floor: rings and arcs of light round the dais, with ticks
function hubFloorTex() {
  return TX.hubf || (TX.hubf = ctex(512, 512, (g, W) => {
    const c = W / 2; g.fillStyle = '#000000'; g.fillRect(0, 0, W, W); g.lineCap = 'round';
    [[0.95, 3, 0.5, 0, 360], [0.84, 3, 0.75, 15, 150], [0.84, 3, 0.75, 195, 330], [0.72, 7, 0.28, 0, 360], [0.61, 2, 0.7, 100, 260], [0.61, 2, 0.7, 280, 420], [0.5, 12, 0.2, 0, 360]].forEach(([rr, lw, a, s0, s1]) => {
      g.strokeStyle = 'rgba(0,207,255,' + a + ')'; g.lineWidth = lw; g.beginPath(); g.arc(c, c, rr * c, s0 * Math.PI / 180, s1 * Math.PI / 180); g.stroke();
    });
    g.strokeStyle = 'rgba(0,207,255,.55)'; g.lineWidth = 2;
    for (let i = 0; i < 96; i++) { const a = i / 96 * Math.PI * 2, r0 = c * (i % 4 ? 0.9 : 0.87); g.beginPath(); g.moveTo(c + Math.cos(a) * r0, c + Math.sin(a) * r0); g.lineTo(c + Math.cos(a) * c * 0.93, c + Math.sin(a) * c * 0.93); g.stroke(); }
  }));
}
// an engine's exhaust: bright at the nozzle, gone at the tail
function plumeTex() {
  return TX.plume || (TX.plume = ctex(32, 256, (g, W, H) => { const gr = g.createLinearGradient(0, 0, 0, H); gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.35, 'rgba(255,255,255,.45)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, W, H); }));
}
function std(o) { return new THREE.MeshStandardMaterial(o); }
// a rounded box, one geometry per size: shared, so a layout's release never frees it
const RB = new Map();
function rboxGeo(w, h, d, r) {
  const k = [w, h, d, r].map((v) => v.toFixed(3)).join(',');
  let g = RB.get(k); if (!g) { g = new RoundedBoxGeometry(w, h, d, 2, Math.max(0.001, Math.min(r, w / 2 - 0.001, h / 2 - 0.001, d / 2 - 0.001))); RB.set(k, g); }
  return g;
}
function omats() {
  if (OM.tile) return;
  // matte where it is painted, a little gloss on the floors: the office is lit, it does not have to mirror anything
  OM.deck = std({ map: deckTex(), roughness: 0.6, metalness: 0.2 });
  OM.tile = std({ map: tileTex(), roughness: 0.5, metalness: 0.25 });
  OM.hubTile = std({ map: tileTex(), color: 0x8fd6ea, roughness: 0.2, metalness: 0.3, emissive: 0x00cfff, emissiveIntensity: 0.04 });
  OM.rim = std({ color: 0x3b4450, roughness: 0.42, metalness: 0.4 });
  OM.rimDark = std({ color: 0x1b222b, roughness: 0.5, metalness: 0.35 });
  OM.hull = std({ map: hullTex(), emissiveMap: TX.hullGlow, emissive: 0xffffff, emissiveIntensity: 1.1, roughness: 0.5, metalness: 0.35 });
  OM.hullLow = std({ color: 0x141b25, roughness: 0.55, metalness: 0.35 });
  OM.glass = std({ color: 0xa9b8c6, envMapIntensity: 0.55, transparent: true, opacity: 0.055, roughness: 0.04, metalness: 0.2, depthWrite: false, side: THREE.DoubleSide });
  OM.wallDark = std({ color: 0x161b21, roughness: 0.5, metalness: 0.3 });
  OM.frame = std({ color: 0x2e3641, roughness: 0.42, metalness: 0.45 });
  OM.desk = std({ color: 0x1b2026, roughness: 0.45, metalness: 0.3 });
  OM.deskTop = std({ color: 0x2a3038, roughness: 0.28, metalness: 0.3 });
  OM.dark = std({ color: 0x0b0e12, roughness: 0.35, metalness: 0.45 });
  OM.plinth = std({ color: 0x1a2028, roughness: 0.45, metalness: 0.4 });
  OM.white = std({ color: 0xd6dce3, roughness: 0.42, metalness: 0.12 });
  OM.white2 = std({ color: 0x9aa7b6, roughness: 0.48, metalness: 0.2 });
  OM.rack = std({ color: 0x14181d, roughness: 0.4, metalness: 0.45 });
  OM.rackFace = std({ map: rackTex(), emissiveMap: TX.rackGlow, emissive: 0xffffff, emissiveIntensity: 1.3, roughness: 0.35, metalness: 0.4 });
  OM.solar = std({ map: solarTex(), roughness: 0.22, metalness: 0.5, emissive: 0x3b82f6, emissiveIntensity: 0.08 });
  OM.engine = std({ color: 0x4a5462, roughness: 0.32, metalness: 0.6 });
  OM.engineDark = std({ color: 0x1a2028, roughness: 0.4, metalness: 0.5, side: THREE.DoubleSide });
  OM.rock = std({ vertexColors: true, roughness: 0.93, metalness: 0.04 });
  OM.pot = std({ color: 0x232a33, roughness: 0.5, metalness: 0.3 });
  OM.bush = std({ color: 0x1f6b45, roughness: 0.85, emissive: 0x00ff88, emissiveIntensity: 0.04 });
  OM.holo = new THREE.MeshBasicMaterial({ map: holoTex(), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
  OM.plume = new THREE.MeshBasicMaterial({ map: plumeTex(), color: new THREE.Color(0x00cfff).multiplyScalar(0.9), opacity: 0.8, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
  OM.dash = emis('#dfe6ee', 0.55);
  // the vault's coins: ET10 green, USDC blue, both metal with their own light
  OM.coinG = std({ color: 0x16a36a, emissive: 0x00ff88, emissiveIntensity: 0.22, metalness: 0.8, roughness: 0.25 });
  OM.coinB = std({ color: 0x2f6fd8, emissive: 0x3b82f6, emissiveIntensity: 0.3, metalness: 0.8, roughness: 0.25 });
  G.coin = new THREE.CylinderGeometry(1, 1, 1, 28);
  // astronauts: a white suit, a helmet, a pack
  OM.suit = std({ color: 0xe6ebf0, roughness: 0.5, metalness: 0.08 });
  OM.pack = std({ color: 0x8a99ab, roughness: 0.5, metalness: 0.25 });
  OM.torso = new THREE.CapsuleGeometry(0.16, 0.26, 4, 14); OM.limb = new THREE.CapsuleGeometry(0.055, 0.2, 3, 10); OM.leg = new THREE.CapsuleGeometry(0.07, 0.36, 3, 10);
  OM.chair = std({ color: 0x1d242c, roughness: 0.5, metalness: 0.25 });
  OM.green = amat('#00ff88'); OM.cyan = amat('#00cfff'); OM.blue = amat('#3b82f6'); OM.red = amat('#ff4444');
  G.bigRock = asteroidGeo(11, 64); G.smallRock = asteroidGeo(27, 14, false);
  G.plume = new THREE.CylinderGeometry(0.42, 0.05, 1, 24, 1, true);
}
// what a layout, a selection or a station built for itself goes back to the GPU when it is cleared; the shared
// geometries (G, OM.torso and the limbs, the rounded boxes), materials (M, AM, OM) and textures (TX) stay, since the next one draws with them
// again. A station's merged parts (userData.own) are its own geometry.
function release(root) {
  const shared = new Set(Object.values(TX));
  [M, OM].concat(Object.values(AM)).forEach((bag) => Object.values(bag).forEach((v) => {
    if (v && v.isMaterial) { shared.add(v); if (v.map) shared.add(v.map); } else if (v && typeof v === 'object') Object.values(v).forEach((m) => { if (m && m.isMaterial) shared.add(m); });
  }));
  root.traverse((o) => {
    if ((o.isLight || o.isInstancedMesh) && o.dispose) o.dispose();
    if (o.userData.own && o.geometry) o.geometry.dispose();
    (o.material ? [].concat(o.material) : []).forEach((m) => {
      if (shared.has(m)) return;
      ['map', 'emissiveMap', 'alphaMap'].forEach((k) => { if (m[k] && !shared.has(m[k])) m[k].dispose(); });
      m.dispose();
    });
  });
}
function emis(hex, k) { return new THREE.MeshStandardMaterial({ color: 0x000000, emissive: new THREE.Color(hex), emissiveIntensity: k == null ? 1.4 : k, roughness: 1 }); }
// a screen on a wall: a canvas the room writes on, redrawn only when what it says changes
function screen(w, h) {
  const c = document.createElement('canvas'); c.width = Math.round(w * 160); c.height = Math.round(h * 160);
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
  return { c, g: c.getContext('2d'), tex, key: '' };
}
function drawWall(s, title, sub, col, mode) {
  const key = [title, sub, col, mode].join('|'); if (s.key === key) return; s.key = key;
  const { c, g } = s, W = c.width, H = c.height;
  g.fillStyle = '#070a0f'; g.fillRect(0, 0, W, H);
  g.strokeStyle = col; g.lineWidth = 6; g.strokeRect(3, 3, W - 6, H - 6);
  g.fillStyle = col; g.font = '700 ' + Math.round(H * 0.2) + 'px JetBrains Mono, monospace'; g.textBaseline = 'top';
  const fit = (t) => { let s2 = String(t || ''); while (s2.length > 3 && g.measureText(s2).width > W - 40) s2 = s2.slice(0, -2); return s2 !== t ? s2.replace(/.$/, '…') : s2; };
  g.fillText(fit(title), 20, H * 0.14);
  g.fillStyle = '#7f93ad'; g.font = '500 ' + Math.round(H * 0.14) + 'px JetBrains Mono, monospace';
  g.fillText(fit(sub), 20, H * 0.44);
  g.fillStyle = '#18212b'; g.fillRect(20, H * 0.76, W - 40, H * 0.08);
  if (mode === 'run') { g.fillStyle = col; g.fillRect(20, H * 0.76, (W - 40) * (0.25 + 0.5 * Math.random()), H * 0.08); }
  if (mode === 'full') { g.fillStyle = col; g.globalAlpha = 0.75; g.fillRect(20, H * 0.76, W - 40, H * 0.08); g.globalAlpha = 1; }
  s.tex.needsUpdate = true;
}
function drawBars(s, title, bars) {
  const key = title + JSON.stringify(bars); if (s.key === key) return; s.key = key;
  const { c, g } = s, W = c.width, H = c.height;
  g.fillStyle = '#070a0f'; g.fillRect(0, 0, W, H); g.strokeStyle = '#00cfff'; g.lineWidth = 6; g.strokeRect(3, 3, W - 6, H - 6);
  g.fillStyle = '#00cfff'; g.font = '700 ' + Math.round(H * 0.15) + 'px JetBrains Mono, monospace'; g.textBaseline = 'top'; g.fillText(title, 20, H * 0.1);
  const top = Math.max(1, ...bars.map((b) => b[1])), bw = (W - 40) / Math.max(1, bars.length);
  bars.forEach((b, i) => { const h = (H * 0.55) * b[1] / top; g.fillStyle = b[0]; g.fillRect(20 + i * bw, H * 0.88 - h, bw - 10, Math.max(3, h)); });
  s.tex.needsUpdate = true;
}
function drawKanban(s, counts) {
  const key = JSON.stringify(counts); if (s.key === key) return; s.key = key;
  const { c, g } = s, W = c.width, H = c.height, cols = [['queued', '#3b82f6'], ['running', '#00cfff'], ['done', '#00ff88'], ['failed', '#ff4444']];
  g.fillStyle = '#06080c'; g.fillRect(0, 0, W, H); g.strokeStyle = '#18212b'; g.lineWidth = 6; g.strokeRect(3, 3, W - 6, H - 6);
  const cw = (W - 30) / 4;
  cols.forEach(([k, col], i) => {
    const x = 15 + i * cw; g.fillStyle = col; g.fillRect(x + 6, 14, cw - 12, 10);
    for (let n = 0; n < Math.min(counts[k] || 0, 4); n++) { g.globalAlpha = 0.85; g.fillRect(x + 10, 40 + n * (H - 60) / 4.4, cw - 20, (H - 60) / 5.5); g.globalAlpha = 1; }
  });
  s.tex.needsUpdate = true;
}
function candleTex() {
  if (TX.candle) return TX.candle;
  const c = document.createElement('canvas'); c.width = 512; c.height = 256; const g = c.getContext('2d');
  g.fillStyle = '#06100c'; g.fillRect(0, 0, 512, 256); g.strokeStyle = '#00ff88'; g.lineWidth = 5; g.strokeRect(3, 3, 506, 250);
  let v = 140; for (let i = 0; i < 16; i++) { const up = [1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1][i], o = v; v = Math.max(60, Math.min(210, v + (up ? -16 : 13))); g.fillStyle = up ? '#00ff88' : '#ff4444'; g.fillRect(24 + i * 29, Math.min(o, v), 17, Math.max(6, Math.abs(o - v))); g.fillRect(31 + i * 29, Math.min(o, v) - 10, 3, Math.abs(o - v) + 20); }
  g.fillStyle = '#00ff88'; g.font = '700 22px JetBrains Mono, monospace'; g.fillText('BASKET H2 · +1.1%', 22, 34);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; TX.candle = t; return t;
}
// a holographic pad: a grid inside a circle, fading to its rim
function padTex() {
  if (TX.pad) return TX.pad;
  const c = document.createElement('canvas'); c.width = c.height = 512; const g = c.getContext('2d');
  g.save(); g.beginPath(); g.arc(256, 256, 250, 0, Math.PI * 2); g.clip();
  const gr = g.createRadialGradient(256, 256, 0, 256, 256, 250); gr.addColorStop(0, 'rgba(0,207,255,.14)'); gr.addColorStop(1, 'rgba(0,207,255,.3)');
  g.fillStyle = gr; g.fillRect(0, 0, 512, 512);
  g.strokeStyle = 'rgba(0,207,255,.5)'; g.lineWidth = 2;
  for (let p = 16; p < 512; p += 24) { g.beginPath(); g.moveTo(p, 0); g.lineTo(p, 512); g.stroke(); g.beginPath(); g.moveTo(0, p); g.lineTo(512, p); g.stroke(); }
  g.restore();
  g.strokeStyle = 'rgba(0,207,255,.95)'; g.lineWidth = 8; g.beginPath(); g.arc(256, 256, 246, 0, Math.PI * 2); g.stroke();
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; TX.pad = t; return t;
}
function moodTex() {
  const c = document.createElement('canvas'); c.width = 512; c.height = 256; const g = c.getContext('2d');
  g.fillStyle = '#0b1016'; g.fillRect(0, 0, 512, 256); g.strokeStyle = '#18212b'; g.lineWidth = 5; g.strokeRect(3, 3, 506, 250);
  ['#00cfff', '#00ff88', '#3b82f6', '#ff4444'].forEach((col, i) => { g.fillStyle = col; g.fillRect(24 + i * 58, 28, 46, 46); });
  g.strokeStyle = '#7f93ad'; g.lineWidth = 3; g.strokeRect(24, 96, 220, 70); g.fillStyle = '#7f93ad'; g.fillRect(36, 110, 90, 10); g.fillStyle = '#18212b'; g.fillRect(36, 132, 160, 8);
  g.strokeStyle = '#00cfff'; g.setLineDash([10, 8]); g.strokeRect(270, 28, 214, 200);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

/* The office in 3D, drawn to the operator's picture of it (2026-10-18): a platform on a rock in space, its hull
 * plated and lit, engines and solar wings off its sides, asteroids drifting past a teal nebula; on it, rooms of
 * glass with neon edges (green at rest, cyan at work, red when they wait for the owner), server racks, lab
 * machines, desks with astronauts at them; the Manager's dais of rings in the middle; Add department a
 * holographic pad on the open deck; the vault at the front. */
class Office3D {
  constructor(el, stage, tipFor) {
    geo(); omats();
    this.el = el; this.stage = stage; this.tipFor = tipFor;
    this.tip = stage.querySelector('.tip'); this.layer = stage.querySelector('.o3layer');
    this.sel = null; this.cells = {}; this.paths = {}; this.packets = []; this.rooms = {}; this.fitted = false; this.hover = null;
    this.mouse = new THREE.Vector2(); this.ray = new THREE.Raycaster();
    this.scene = new THREE.Scene(); this.scene.background = new THREE.Color(OFFICE.bg); this.scene.fog = new THREE.Fog(OFFICE.bg, 140, 360);
    this.camera = new THREE.PerspectiveCamera(36, 2, 0.3, 700);
    this.renderer = new THREE.WebGPURenderer({ antialias: false });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping; this.renderer.toneMappingExposure = 1.35;
    this.renderer.shadowMap.enabled = true; this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    el.appendChild(this.renderer.domElement);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    Object.assign(this.controls, { enableDamping: true, dampingFactor: 0.08, minDistance: 6, maxDistance: 140, maxPolarAngle: Math.PI * 0.47, minPolarAngle: 0.2,
      screenSpacePanning: false, zoomSpeed: 0.9, rotateSpeed: 0.55 });
    this.controls.addEventListener('start', () => { this.tw = null; this.moved = true; });
    const S = this.scene;
    S.environment = envTex();
    // white light from the camera's side, so the faces you see are lit; a cool one from below for the hull and the
    // rock; a cyan rim from behind
    S.add(new THREE.HemisphereLight(0xdfe8f1, 0x0a0d12, 0.95), new THREE.AmbientLight(0x1b222b, 0.5));
    this.sun = new THREE.DirectionalLight(0xf4f8fc, 2.4); this.sun.castShadow = true; this.sun.shadow.mapSize.set(2048, 2048);
    this.sun.shadow.normalBias = 0.02; this.sun.shadow.bias = -0.0005; S.add(this.sun); S.add(this.sun.target);
    const rim = new THREE.DirectionalLight(0x00cfff, 0.5); rim.position.set(-30, 12, -40); S.add(rim);
    const under = new THREE.DirectionalLight(0xcfe6f5, 0.55); under.position.set(20, -22, 42); S.add(under);
    this.sky = spaceSky(); S.add(this.sky);
    this.world = new THREE.Group(); S.add(this.world);
    this.pk = new THREE.Group(); S.add(this.pk);
    this.clock = new THREE.Clock();
    this.bind();
    this.renderer.init().then(() => {
      try { this.post = new Post(this.renderer, this.scene, this.camera, 0.45, 0.45, 0.84, { ao: { radius: 0.8, scale: 1.6 } }); }
      catch (e) { console.warn('office: no ambient occlusion', e); try { this.post = new Post(this.renderer, this.scene, this.camera, 0.45, 0.45, 0.84); } catch (e2) { this.post = null; } }
      this.renderer.setAnimationLoop(() => this.frame());
    }).catch((e) => { console.error('3D office could not start:', e); if (this.onFail) this.onFail(e); });
    if (window.ResizeObserver) new ResizeObserver(() => this.resize()).observe(el);
    setInterval(() => this.wander(), 2600);
  }
  shape() { return CO.S.departments.map((d) => d.id + ':' + d.slot + ':' + d.key + ':' + d.experts.join(',')).join('|') + (CO.RO ? 'ro' : ''); }
  V(x, y, z = 0) { return new THREE.Vector3(x - this.cx, z, y - this.cy); }
  part(g, geom, mat, sx, sy, sz, x, y, z, shadow = true) {
    const m = new THREE.Mesh(geom, mat); m.scale.set(sx, sy, sz); m.position.copy(this.V(x, z, y)); if (shadow) { m.castShadow = true; m.receiveShadow = true; } g.add(m); return m;
  }
  // a box from the 2D plan's corner and sizes: x0,y0 the plan's corner, w,d its sizes, z0 and h up
  box(g, x0, y0, z0, w, d, h, mat, shadow) { return this.part(g, G.box, mat, w, h, d, x0 + w / 2, z0 + h / 2, y0 + d / 2, shadow); }
  // a cylinder standing on the plan: centre x,y, radius, from z0 up h
  cyl(g, x, y, z0, rad, h, mat, geom) { return this.part(g, geom || G.cyl, mat, rad, h, rad, x, z0 + h / 2, y); }
  // a box with soft edges, at its real size: furniture whose edges catch the light
  rb(g, x0, y0, z0, w, d, h, mat, r = 0.05, shadow = true) {
    const m = new THREE.Mesh(rboxGeo(w, h, d, r), mat); m.position.copy(this.V(x0 + w / 2, y0 + d / 2, z0 + h / 2)); if (shadow) { m.castShadow = true; m.receiveShadow = true; } g.add(m); return m;
  }

  layout(opts) {
    const S = CO.S, L = CO.iso, born = opts && opts.born;
    this.shapeKey = this.shape();
    const cells = { hub: L.HUB, audit: L.AUDIT, vault: L.VAULT }, used = {};
    S.departments.forEach((d) => { cells['d' + d.id] = L.SLOTS[d.slot]; used[d.slot] = 1; });
    let lot = 0; while (used[lot]) lot++;
    if (lot < L.SLOTS.length && !CO.RO) cells.lot = L.SLOTS[lot];
    this.cells = cells;
    const all = Object.keys(cells).map((k) => cells[k]);
    let maxX = 0, maxY = 0; all.forEach((c) => { maxX = Math.max(maxX, c[0] + L.RS); maxY = Math.max(maxY, c[1] + L.RS); });
    this.cx = maxX / 2; this.cy = maxY / 2; this.size = Math.max(maxX, maxY);
    // clear the old floor, rooms and labels
    release(this.world); this.world.clear(); this.layer.innerHTML = ''; this.rooms = {}; this.hits = []; this.pcs = [];
    const RS = L.RS, W = this.world;
    // The deck: a plated slab under every room (the Manager's, the audit, the vault and the free lot included), one
    // platform where cells meet. The fit frames the deck and what hangs under it.
    const pad = 0.5, T = 0.35, have = {}, kc = (x, y) => x + ',' + y;
    all.forEach((c) => { have[kc(c[0], c[1])] = 1; });
    this.corners = []; const outer = [];
    all.forEach((c) => {
      const s = new THREE.Mesh(G.box, [OM.rimDark, OM.rimDark, OM.deck, OM.rimDark, OM.rimDark, OM.rimDark]);
      s.scale.set(RS + 2 * pad, T, RS + 2 * pad); s.position.copy(this.V(c[0] + RS / 2, c[1] + RS / 2, -T / 2)); s.receiveShadow = true; W.add(s);
      const x0 = c[0] - pad, y0 = c[1] - pad, x1 = c[0] + RS + pad, y1 = c[1] + RS + pad;
      // a side is the outside when no room's slab meets it there
      [[x0, y0, x1, y0, !have[kc(c[0], c[1] - 8)], 0, -1], [x0, y1, x1, y1, !have[kc(c[0], c[1] + 8)], 0, 1], [x0, y0, x0, y1, !have[kc(c[0] - 8, c[1])], -1, 0], [x1, y0, x1, y1, !have[kc(c[0] + 8, c[1])], 1, 0]].forEach(([ax, ay, bx, by, out, nx, ny]) => {
        if (out) outer.push({ ax, ay, bx, by, nx, ny });
      });
      [[x0, y0], [x1, y0], [x0, y1], [x1, y1]].forEach(([x, y]) => { this.corners.push(this.V(x, y, -T - 2.4), this.V(x, y, WH + 0.1)); });
    });
    this.exterior(all, outer, have, pad, T);
    // corridors: from every room's door to the Manager's, the 2D office's own routes, painted as a dashed lane that
    // lights cyan while work runs along it
    this.paths = {}; this.conduits = {};
    Object.keys(cells).forEach((k) => {
      if (k === 'hub' || k === 'lot') return;
      const p = L.route(all, cells[k], L.HUB); if (!p) return;
      this.paths[k] = p;
      const mat = emis('#dfe6ee', 0.3), segs = [];
      for (let i = 1; i < p.length; i++) {
        const a = p[i - 1], b = p[i], len = Math.hypot(b[0] - a[0], b[1] - a[1]); if (len < 0.01) continue;
        const n = Math.max(1, Math.round(len / 0.7)), ang = -Math.atan2(b[1] - a[1], b[0] - a[0]);
        for (let j = 0; j < n; j++) {
          const f = (j + 0.5) / n, m = new THREE.Mesh(G.box, mat); m.scale.set(Math.min(0.4, len / n * 0.6), 0.02, 0.07);
          m.position.copy(this.V(a[0] + (b[0] - a[0]) * f, a[1] + (b[1] - a[1]) * f, 0.012)); m.rotation.y = ang; W.add(m); segs.push(m);
        }
      }
      this.conduits[k] = { mat, segs };
    });
    const sz = this.size;
    this.sun.position.copy(new THREE.Vector3(-sz * 0.35, sz * 1.5, sz * 1.05)); this.sun.target.position.set(0, 0, 0);
    Object.assign(this.sun.shadow.camera, { left: -sz * 0.85, right: sz * 0.85, top: sz * 0.85, bottom: -sz * 0.85, near: 1, far: sz * 4 }); this.sun.shadow.camera.updateProjectionMatrix();
    // rooms
    Object.keys(cells).forEach((k) => {
      const c = cells[k], g = new THREE.Group(); W.add(g);
      const room = { key: k, g, x0: c[0], y0: c[1], agents: [], screens: [], mons: [], born: born && k === 'd' + born };
      this.rooms[k] = room;
      if (k === 'lot') return this.lotRoom(room);
      this.shell(room);
      if (k === 'hub') this.hubRoom(room); else if (k === 'audit') this.auditRoom(room); else if (k === 'vault') this.vaultRoom(room); else this.deptRoom(room, CO.dept(+k.slice(1)));
      const hit = new THREE.Mesh(G.box, M.hit); hit.scale.set(RS, WH, RS); hit.position.copy(this.V(c[0] + RS / 2, c[1] + RS / 2, WH / 2)); hit.userData.key = k; g.add(hit); this.hits.push(hit);
      if (room.born) { g.scale.set(1, 0.01, 1); room.grow = performance.now(); }
    });
    this.selRing = new THREE.Group(); W.add(this.selRing);
    this.update();
    if (!this.fitted) { this.fit(false); }
  }
  // Under and round the deck, what makes it a station in space: a rim, a plated hull with its lights, a stepped
  // keel, the rock it is built on, engines, two solar wings, asteroids drifting past. Static parts merged per
  // material.
  exterior(all, outer, have, pad, T) {
    const W = this.world, RS = CO.iso.RS, ext = new THREE.Group(), HD = 1.6, R = rng(17), kc = (x, y) => x + ',' + y; W.add(ext);
    all.forEach((c) => {
      const Lf = !have[kc(c[0] - 8, c[1])], Rt = !have[kc(c[0] + 8, c[1])], Bk = !have[kc(c[0], c[1] - 8)], Fr = !have[kc(c[0], c[1] + 8)];
      const x0 = c[0] - pad, y0 = c[1] - pad, x1 = c[0] + RS + pad, y1 = c[1] + RS + pad;
      const tier = (ins, z0, h, mat) => this.box(ext, x0 + (Lf ? ins : 0), y0 + (Bk ? ins : 0), z0, x1 - x0 - (Lf ? ins : 0) - (Rt ? ins : 0), y1 - y0 - (Bk ? ins : 0) - (Fr ? ins : 0), h, mat, false);
      tier(0.12, -T - 0.12 - HD, HD, OM.hull);
      tier(0.75, -T - 0.12 - HD - 0.45, 0.45, OM.hullLow);
      tier(1.5, -T - 0.12 - HD - 0.75, 0.3, OM.hullLow);
    });
    // the rim: a lighter lip round the outside of the deck, a little proud of it
    outer.forEach((e) => {
      const len = Math.hypot(e.bx - e.ax, e.by - e.ay) + 0.44, mx = (e.ax + e.bx) / 2 + e.nx * 0.11, my = (e.ay + e.by) / 2 + e.ny * 0.11, along = e.ax === e.bx;
      this.box(ext, mx - (along ? 0.11 : len / 2), my - (along ? len / 2 : 0.11), -T - 0.14, along ? 0.22 : len, along ? len : 0.22, T + 0.16, OM.rim, false);
    });
    let mnx = 1e9, mxx = -1e9, mny = 1e9, mxy = -1e9;
    all.forEach((c) => { mnx = Math.min(mnx, c[0]); mxx = Math.max(mxx, c[0] + RS); mny = Math.min(mny, c[1]); mxy = Math.max(mxy, c[1] + RS); });
    const cxp = (mnx + mxx) / 2, cyp = (mny + mxy) / 2, span = Math.max(mxx - mnx, mxy - mny), keel = -T - HD - 0.9;
    // the rock: wider than the deck where it shows, hanging well below it
    const rock = new THREE.Mesh(G.bigRock, OM.rock); rock.scale.set(span * 0.5, span * 0.3, span * 0.45); rock.position.copy(this.V(cxp - span * 0.04, cyp + span * 0.02, keel - span * 0.02)); rock.rotation.set(0.05, 0.6, 0.04); ext.add(rock);
    const rock2 = new THREE.Mesh(G.bigRock, OM.rock); rock2.scale.set(span * 0.26, span * 0.2, span * 0.24); rock2.position.copy(this.V(cxp + span * 0.2, cyp + span * 0.16, keel - span * 0.12)); rock2.rotation.set(0.5, 2.1, 0.3); ext.add(rock2);
    // engines on up to six of the outside walls, exhaust that breathes
    this.flames = [];
    const pick = outer.length <= 6 ? outer : [0, 1, 2, 3, 4, 5].map((i) => outer[Math.floor((i + 0.5) * outer.length / 6)]);
    pick.forEach((e, i) => {
      const f = i % 2 ? 0.3 : 0.7, g = new THREE.Group();
      g.position.copy(this.V(e.ax + (e.bx - e.ax) * f + e.nx * 0.2, e.ay + (e.by - e.ay) * f + e.ny * 0.2, -T - 0.12 - HD * 0.5)); g.rotation.y = Math.atan2(e.nx, e.ny); ext.add(g);
      const housing = new THREE.Mesh(G.cyl, OM.engine); housing.scale.set(0.62, 1.3, 0.62); housing.rotation.x = Math.PI / 2; housing.position.z = 0.5; g.add(housing);
      const cap = new THREE.Mesh(G.cyl, OM.engineDark); cap.scale.set(0.5, 0.5, 0.5); cap.rotation.x = Math.PI / 2; cap.position.z = -0.25; g.add(cap);
      [0.0, 0.62, 1.12].forEach((z) => { const ring = new THREE.Mesh(G.wheel, OM.rim); ring.scale.setScalar(0.64); ring.position.z = z; g.add(ring); });
      [[0.5, 0], [-0.5, 0], [0, 0.5], [0, -0.5]].forEach(([x, y]) => { const s = new THREE.Mesh(G.box, OM.frame); s.scale.set(0.1, 0.1, 0.7); s.position.set(x, y, -0.25); g.add(s); });
      const bell = new THREE.Mesh(G.bell, OM.engineDark); bell.scale.set(0.56, 0.5, 0.56); bell.rotation.x = -Math.PI / 2; bell.position.z = 1.38; g.add(bell);
      const disc = new THREE.Mesh(G.cyl, OM.cyan.glow); disc.scale.set(0.44, 0.04, 0.44); disc.rotation.x = Math.PI / 2; disc.position.z = 1.22; disc.userData.dyn = true; g.add(disc);
      const fl = new THREE.Mesh(G.plume, OM.plume); fl.scale.set(0.85, 2.2, 0.85); fl.rotation.x = -Math.PI / 2; fl.position.z = 1.3 + 1.1; fl.userData.dyn = true; g.add(fl);
      const halo = glowSprite(0x00cfff, 0.55, 2.4); halo.position.z = 1.4; halo.userData.dyn = true; g.add(halo);
      this.flames.push({ fl, ph: R() * 6 });
    });
    // two solar wings: off the far right side and the near right side, as in the picture
    [[0, -1], [1, 0]].forEach(([nx, ny]) => {
      const es = outer.filter((o) => o.nx === nx && o.ny === ny); if (!es.length) return;
      const e = es[nx ? es.length - 1 : es.length - 1], mx = (e.ax + e.bx) / 2, my = (e.ay + e.by) / 2, g = new THREE.Group();
      g.position.copy(this.V(mx, my, -T - 0.7)); g.rotation.y = Math.atan2(nx, ny); ext.add(g);
      const boom = new THREE.Mesh(G.box, OM.engine); boom.scale.set(0.16, 0.16, 10.2); boom.position.z = 5.2; g.add(boom);
      const joint = new THREE.Mesh(G.cyl, OM.engineDark); joint.scale.set(0.34, 0.5, 0.34); joint.position.z = 0.3; g.add(joint);
      for (let i = 0; i < 4; i++) [-1, 1].forEach((side) => {
        const p = new THREE.Mesh(G.box, [OM.engine, OM.engine, OM.solar, OM.engineDark, OM.engine, OM.engine]);
        p.scale.set(2.3, 0.05, 2.0); p.position.set(side * 1.32, 0, 1.6 + i * 2.15); p.rotation.z = side * 0.28; g.add(p);
        const strut = new THREE.Mesh(G.box, OM.frame); strut.scale.set(0.5, 0.06, 0.06); strut.position.set(side * 0.3, 0, 1.6 + i * 2.15); g.add(strut);
      });
    });
    bakeGroup(ext);
    ext.traverse((o) => { if (o.isMesh && o.material === OM.rock) { o.castShadow = true; o.receiveShadow = true; } });
    // asteroids drifting round it, never between it and the camera; one large and lit up to the right
    this.drift = [];
    const big = new THREE.Mesh(G.smallRock, OM.rock); big.scale.set(2.2, 1.9, 2.0);
    big.position.copy(this.V(cxp, cyp, 0)).add(skyDir(32, 0).multiplyScalar(span * 0.9)).add(new THREE.Vector3(0, span * 0.32, 0)); W.add(big); this.drift.push({ m: big, sp: 0.05 });
    for (let i = 0; i < 12; i++) {
      const a = R() * Math.PI * 2; if ((Math.cos(a) + Math.sin(a)) / Math.SQRT2 > 0.2) { i--; continue; }
      const d = span * (0.85 + R() * 0.7), s = 0.3 + R() * R() * 1.4, m = new THREE.Mesh(G.smallRock, OM.rock);
      m.scale.set(s, s * 0.8, s * 0.9); m.position.copy(this.V(cxp + Math.cos(a) * d, cyp + Math.sin(a) * d, -9 + R() * 12)); m.rotation.set(R() * 3, R() * 3, R() * 3);
      W.add(m); this.drift.push({ m, sp: 0.06 + R() * 0.18 });
    }
  }
  // a room: a glossy floor, glass on all four sides with neon on every edge, a dark panel along the two back walls
  shell(r) {
    const { g, x0, y0 } = r, RS = CO.iso.RS, H = WH, t = 0.04, z0 = 0.08;
    this.box(g, x0, y0, 0, RS, RS, z0, r.key === 'hub' ? OM.hubTile : OM.tile);
    r.glow = new THREE.Mesh(G.plane, new THREE.MeshBasicMaterial({ map: radialTex('255,255,255', 0.9), transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, color: 0x00cfff }));
    r.glow.scale.set(RS * 1.15, RS * 1.15, 1); r.glow.rotation.x = -Math.PI / 2; r.glow.position.copy(this.V(x0 + RS / 2, y0 + RS / 2, z0 + 0.01)); g.add(r.glow);
    [[x0, y0, RS, t], [x0, y0 + RS - t, RS, t], [x0, y0, t, RS], [x0 + RS - t, y0, t, RS]].forEach(([x, y, w, d]) => this.box(g, x, y, z0, w, d, H, OM.glass, false));
    if (r.key !== 'hub') { this.box(g, x0 + t, y0 + t, z0, RS - 2 * t, 0.1, 0.62, OM.wallDark); this.box(g, x0 + t, y0 + t, z0, 0.1, RS - 2 * t, 0.62, OM.wallDark); }
    r.edgeM = emis('#00ff88', 0.75);
    const e = 0.05, z1 = z0 + H - e;
    [[x0, y0, RS, e], [x0, y0 + RS - e, RS, e], [x0, y0, e, RS], [x0 + RS - e, y0, e, RS]].forEach(([x, y, w, d]) => { this.box(g, x, y, z1, w, d, e, r.edgeM, false); this.box(g, x, y, z0, w, d, e, r.edgeM, false); });
    [[x0, y0], [x0 + RS - e, y0], [x0, y0 + RS - e], [x0 + RS - e, y0 + RS - e]].forEach(([x, y]) => this.box(g, x, y, z0, e, e, H, r.edgeM, false));
    // a lamp over the room in the colour of what it is doing: it lights the desks, the people and the floor
    r.lamp = new THREE.PointLight(OFFICE.lamp, 9, 11, 1.6); r.lamp.position.copy(this.V(x0 + RS / 2, y0 + RS / 2, 2.5)); g.add(r.lamp);
  }
  // a wall screen on the back wall: what runs now, or why it waits
  wallScreen(r, u0, u1) {
    const s = screen(u1 - u0, 0.62), mat = new THREE.MeshBasicMaterial({ map: s.tex, toneMapped: false });
    const m = new THREE.Mesh(G.plane, mat); m.scale.set(u1 - u0, 0.62, 1); m.position.copy(this.V(r.x0 + (u0 + u1) / 2, r.y0 + 0.1, 1.45)); r.g.add(m);
    this.box(r.g, r.x0 + u0 - 0.05, r.y0 + 0.05, 1.09, u1 - u0 + 0.1, 0.04, 0.72, OM.dark, false);
    r.wall = s; return s;
  }
  kanban(r, v0 = 1.5, v1 = 5.8) {
    const s = screen(v1 - v0, 0.62), mat = new THREE.MeshBasicMaterial({ map: s.tex, toneMapped: false });
    const m = new THREE.Mesh(G.plane, mat); m.scale.set(v1 - v0, 0.62, 1); m.rotation.y = Math.PI / 2; m.position.copy(this.V(r.x0 + 0.1, r.y0 + (v0 + v1) / 2, 1.45)); r.g.add(m);
    this.box(r.g, r.x0 + 0.05, r.y0 + v0 - 0.05, 1.09, 0.04, v1 - v0 + 0.1, 0.72, OM.dark, false);
    r.kb = s;
  }
  // a desk facing the room: a top on two side panels and a drawer unit, two screens on stands (green charts; cyan
  // while its astronaut works), a keyboard, a mug
  desk(r, x, y, i) {
    const g = r.g;
    this.rb(g, x + 0.02, y + 0.06, 0.08, 0.12, 0.72, 0.42, OM.desk, 0.03);
    this.rb(g, x + 1.76, y + 0.06, 0.08, 0.12, 0.72, 0.42, OM.desk, 0.03);
    this.rb(g, x + 1.12, y + 0.08, 0.08, 0.6, 0.68, 0.4, OM.desk, 0.03);
    for (let k = 0; k < 3; k++) this.box(g, x + 1.18, y + 0.76, 0.15 + k * 0.12, 0.48, 0.012, 0.09, OM.frame, false);
    this.rb(g, x - 0.03, y - 0.03, 0.5, 1.96, 0.91, 0.06, OM.deskTop, 0.025);
    const scr = new THREE.MeshBasicMaterial({ map: monTex(), color: new THREE.Color(OFFICE.mon), toneMapped: false });
    [x + 0.12, x + 0.98].forEach((mx) => {
      this.cyl(g, mx + 0.39, y + 0.26, 0.56, 0.13, 0.02, OM.frame);
      this.box(g, mx + 0.36, y + 0.2, 0.58, 0.06, 0.05, 0.14, OM.frame, false);
      this.rb(g, mx, y + 0.12, 0.68, 0.8, 0.06, 0.46, OM.dark, 0.025);
      const face = new THREE.Mesh(G.plane, scr); face.scale.set(0.72, 0.38, 1); face.position.copy(this.V(mx + 0.4, y + 0.185, 0.91)); g.add(face);
    });
    this.rb(g, x + 0.66, y + 0.48, 0.56, 0.6, 0.2, 0.03, OM.frame, 0.01);
    this.cyl(g, x + 1.62, y + 0.6, 0.56, 0.05, 0.1, OM.white);
    r.mons[i] = scr;
  }
  // An astronaut: a white suit, a helmet with a dark visor, a pack, arms to the keyboard. At a desk it sits on its
  // chair; it stands up to walk (wander) and the Manager stands at its dais. Visor and chest light go cyan at work.
  agent(r, x, y, i, label, opts) {
    const at = this.V(x, y, 0.08), S = 1.25, standing = !!(opts && opts.stand);
    const cm = (geom, mat, px, py, pz, rx) => { const m = new THREE.Mesh(geom, mat); m.position.set(px, py, pz); if (rx) m.rotation.x = rx; m.castShadow = true; m.receiveShadow = true; return m; };
    if (!standing) {
      const chair = new THREE.Group(); chair.position.copy(at); chair.scale.setScalar(S); r.g.add(chair);
      const pole = cm(G.cyl, OM.frame, 0, 0.21, 0.06), base = cm(G.cyl, OM.dark, 0, 0.03, 0.06);
      pole.scale.set(0.035, 0.36, 0.035); base.scale.set(0.26, 0.03, 0.26);
      chair.add(cm(rboxGeo(0.5, 0.08, 0.48, 0.03), OM.chair, 0, 0.42, 0.06), cm(rboxGeo(0.48, 0.5, 0.07, 0.03), OM.chair, 0, 0.74, 0.3, -0.12), pole, base);
    }
    const g = new THREE.Group(); g.position.copy(at); g.scale.setScalar(S); r.g.add(g);
    const up = new THREE.Group(); g.add(up);
    up.add(cm(OM.torso, OM.suit, 0, 0.75, 0.04));
    const helmet = cm(G.sphere, OM.suit, 0, 1.13, 0.02); helmet.scale.setScalar(0.19); up.add(helmet);
    const visorM = std({ color: 0x05080c, emissive: 0x00cfff, emissiveIntensity: 0.06, roughness: 0.08, metalness: 0.85 });
    const vz = cm(G.sphere, visorM, 0, 1.13, -0.1); vz.scale.set(0.15, 0.11, 0.1); up.add(vz);
    up.add(cm(rboxGeo(0.3, 0.38, 0.14, 0.04), OM.pack, 0, 0.8, 0.21));
    const chest = cm(G.box, OM.pack, 0, 0.84, -0.13); chest.scale.set(0.1, 0.06, 0.02); up.add(chest);
    [-1, 1].forEach((s) => {
      up.add(cm(OM.limb, OM.suit, s * 0.21, 0.82, -0.04, 0.45), cm(OM.limb, OM.suit, s * 0.19, 0.67, -0.22, 1.45));
      const hand = cm(G.sphere, OM.pack, s * 0.17, 0.66, -0.36); hand.scale.setScalar(0.055); up.add(hand);
    });
    const sit = new THREE.Group(), stand = new THREE.Group(); g.add(sit, stand);
    [-1, 1].forEach((s) => {
      sit.add(cm(OM.limb, OM.suit, s * 0.09, 0.5, -0.12, Math.PI / 2), cm(OM.limb, OM.suit, s * 0.09, 0.27, -0.27), cm(rboxGeo(0.12, 0.08, 0.18, 0.03), OM.pack, s * 0.09, 0.04, -0.31));
      stand.add(cm(OM.leg, OM.suit, s * 0.09, 0.3, 0.04), cm(rboxGeo(0.12, 0.08, 0.18, 0.03), OM.pack, s * 0.09, 0.04, 0));
    });
    sit.visible = !standing; stand.visible = standing;
    const ringM = emis('#00cfff', 0); const ring = new THREE.Mesh(G.ring, ringM); ring.rotation.x = Math.PI / 2; ring.scale.setScalar(0.4); ring.position.y = 0.02; g.add(ring);
    const el = document.createElement('div'); el.className = 'a3'; el.textContent = label; this.layer.appendChild(el);
    const a = { g, b: up, by: standing ? 0.1 : 0, standing, sit, stand, visorM, chest, ring, ringM, el, home: g.position.clone(), phase: (i + r.x0 * 0.37) % 6.28, key: r.key + ':' + i, room: r, label };
    r.agents.push(a); return a;
  }
  plate(r, cls) {
    const el = document.createElement('div'); el.className = 'p3' + (cls ? ' ' + cls : ''); el.setAttribute('data-key', r.key); this.layer.appendChild(el);
    el.addEventListener('click', () => CO.emit('office:click', r.key));
    el.addEventListener('pointerenter', () => this.setHover(r.key)); el.addEventListener('pointerleave', () => this.setHover(null));
    r.plate = el; r.plateAt = this.V(r.x0 + 4.4, r.y0 + 5.75, 1.7); return el;
  }
  // A department's room: its computer in the back corner, its screens on the back walls, what it works with in
  // the back right (racks, lab machines, a league table), a row of desks with an astronaut at each.
  deptRoom(r, d) {
    const k = d.key, x0 = r.x0, y0 = r.y0, g = r.g; let u1 = 6.6;
    if (k === 'development' || k === 'testing') { u1 = 4.3; this.racks(r, x0 + 4.55, y0 + 0.3, 3); this.racks(r, x0 + 4.55, y0 + 1.4, 3); }
    else if (k === 'testing_lab') { u1 = 4.0; this.labMachine(r, x0 + 4.15, y0 + 0.3); this.labMachine(r, x0 + 5.55, y0 + 0.3); this.canisters(r, x0 + 6.45, y0 + 1.6); }
    else if (k === 'trading_desk') { u1 = 4.1; this.boardTex(r, 4.3, 6.75, candleTex()); }
    else if (k === 'design') { u1 = 4.5; this.boardTex(r, 4.7, 6.75, moodTex()); }
    else if (d.run_kind === 'league') { u1 = 4.1; this.leagueTable(r, x0 + 5.3, y0 + 1.25); }
    else if (d.run_kind === 'stranger') { u1 = 4.1; this.lounge(r, x0 + 4.4, y0 + 0.3); }
    else { u1 = 4.6; this.racks(r, x0 + 5.2, y0 + 0.3, 2); }
    this.wallScreen(r, 1.75, u1); this.kanban(r);
    const ex = d.experts.slice(0, 3), xs = ex.length === 1 ? [2.4] : ex.length === 2 ? [1.0, 3.7] : [0.35, 2.55, 4.75];
    ex.forEach((e, i) => { this.desk(r, x0 + xs[i], y0 + 2.75, i); if (k === 'trading_desk') this.sideScreens(r, x0 + xs[i], y0 + 2.75); });
    ex.forEach((e, i) => this.agent(r, x0 + xs[i] + 0.95, y0 + 4.05, i, CO.expertName(e)));
    this.terminal(r, x0 + 0.3, y0 + 0.32, d.link || CO.DEPT_LINK[k] || CO.DEPT_LINK.custom);
    this.cabinet(r, x0 + 6.45, y0 + 3.0, 0.45, 2.3, 0.72);
    this.plant(r, x0 + 0.42, y0 + 6.5); this.plant(r, x0 + 6.55, y0 + 6.55, 0.8);
    this.plate(r);
  }
  boardTex(r, u0, u1, tex) {
    const m = new THREE.Mesh(G.plane, new THREE.MeshBasicMaterial({ map: tex, toneMapped: false })); m.scale.set(u1 - u0, 0.7, 1); m.position.copy(this.V(r.x0 + (u0 + u1) / 2, r.y0 + 0.1, 1.45)); r.g.add(m);
    this.box(r.g, r.x0 + u0 - 0.05, r.y0 + 0.05, 1.05, u1 - u0 + 0.1, 0.04, 0.8, OM.dark, false);
  }
  // the department's computer: a console whose screen opens its page on cymetica.com
  terminal(r, x, y, link) {
    const g = r.g;
    this.rb(g, x, y, 0.08, 1.25, 0.8, 0.5, OM.desk, 0.04);
    this.rb(g, x + 0.08, y + 0.1, 0.58, 1.09, 0.08, 0.76, OM.dark, 0.03);
    const scr = new THREE.MeshBasicMaterial({ map: this.pcTex(), toneMapped: false });
    const face = new THREE.Mesh(G.plane, scr); face.scale.set(1.0, 0.68, 1); face.position.copy(this.V(x + 0.625, y + 0.185, 0.96)); g.add(face);
    const hit = new THREE.Mesh(G.box, M.hit); hit.scale.set(1.35, 1.4, 1.0); hit.position.copy(this.V(x + 0.62, y + 0.4, 0.75)); hit.userData.pc = link; g.add(hit);
    this.pcs.push(hit); r.pcFace = scr;
  }
  pcTex() {
    if (this._pc) return this._pc;
    const c = document.createElement('canvas'); c.width = 256; c.height = 176; const g = c.getContext('2d');
    g.fillStyle = '#06261f'; g.fillRect(0, 0, 256, 176); g.strokeStyle = '#00ff88'; g.lineWidth = 8; g.strokeRect(4, 4, 248, 168);
    g.fillStyle = '#00ff88'; g.font = '700 96px JetBrains Mono, monospace'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('↗', 128, 92);
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; this._pc = t; return t;
  }
  plant(r, x, y, k = 1) {
    this.cyl(r.g, x, y, 0.08, 0.25 * k, 0.4 * k, OM.pot);
    this.cyl(r.g, x, y, 0.08 + 0.4 * k, 0.27 * k, 0.04, OM.frame);
    [[0, 0, 0.72, 0.27], [-0.13, 0.09, 0.84, 0.21], [0.14, -0.06, 0.88, 0.2], [0.03, 0.12, 1.02, 0.17], [-0.05, -0.1, 0.98, 0.16]].forEach(([dx, dy, z, s]) => {
      const m = new THREE.Mesh(G.sphere, OM.bush); m.scale.set(s * k, s * 1.1 * k, s * k); m.position.copy(this.V(x + dx * k, y + dy * k, 0.08 + (z - 0.08) * k)); m.castShadow = true; r.g.add(m);
    });
  }
  // a low cabinet against a wall, its doors marked, a lit strip along its top
  cabinet(r, x, y, w, d, h) {
    this.rb(r.g, x, y, 0.08, w, d, h, OM.desk, 0.04);
    this.rb(r.g, x - 0.02, y - 0.02, 0.08 + h, w + 0.04, d + 0.04, 0.04, OM.deskTop, 0.015);
    const along = d > w, n = Math.max(1, Math.round((along ? d : w) / 0.6));
    for (let k = 1; k < n; k++) this.box(r.g, along ? x - 0.01 : x + k * w / n, along ? y + k * d / n : y - 0.01, 0.14, along ? 0.012 : 0.012, along ? 0.012 : 0.012, h - 0.12, OM.frame, false);
  }
  // server racks in a row, fronts to the room: slots, vents, lights; a few lights blink on their own
  racks(r, x, y, n) {
    for (let i = 0; i < n; i++) {
      const rx = x + i * 0.72, m = new THREE.Mesh(rboxGeo(0.64, 1.62, 0.74, 0.035), [OM.rack, OM.rack, OM.frame, OM.rack, OM.rackFace, OM.rack]);
      m.position.copy(this.V(rx + 0.32, y + 0.37, 0.89)); m.castShadow = true; m.receiveShadow = true; r.g.add(m);
      for (let k = 0; k < 3; k++) { const col = ['#00ff88', '#00cfff', '#3b82f6'][(i + k) % 3]; const l = new THREE.Mesh(G.box, amat(col).glow); l.scale.set(0.05, 0.03, 0.01); l.position.copy(this.V(rx + 0.12 + k * 0.08, y + 0.745, 1.5 - k * 0.38)); l.userData.blink = (i * 7 + k * 3) % 11; r.g.add(l); (r.leds = r.leds || []).push(l); }
    }
  }
  // a white lab machine: a rounded cabinet, a dark window onto a lit chamber, a hologram floating over it
  labMachine(r, x, y) {
    const g = r.g;
    this.rb(g, x, y, 0.08, 1.15, 0.8, 0.66, OM.white, 0.08);
    this.rb(g, x + 0.06, y + 0.05, 0.74, 1.03, 0.62, 0.44, OM.white, 0.08);
    this.rb(g, x + 0.13, y + 0.62, 0.79, 0.89, 0.07, 0.3, OM.dark, 0.03);
    const ch = new THREE.Mesh(G.plane, OM.cyan.soft); ch.scale.set(0.8, 0.22, 1); ch.position.copy(this.V(x + 0.575, y + 0.695, 0.94)); g.add(ch);
    this.rb(g, x + 0.1, y + 0.1, 1.18, 0.95, 0.5, 0.07, OM.white2, 0.03);
    const holo = new THREE.Mesh(G.plane, OM.holo); holo.scale.set(0.9, 0.6, 1); holo.position.copy(this.V(x + 0.575, y + 0.4, 1.66)); holo.rotation.x = -0.25; g.add(holo);
    for (let k = 0; k < 3; k++) { const m = new THREE.Mesh(G.box, (k % 2 ? OM.green : OM.cyan).glow); m.scale.set(0.08, 0.035, 0.01); m.position.copy(this.V(x + 0.3 + k * 0.2, y + 0.81, 0.36)); m.userData.blink = k * 3; g.add(m); (r.leds = r.leds || []).push(m); }
  }
  // a white console with a green screen: what the weekly audit reads its logs on
  console3(r, x, y) {
    const g = r.g;
    this.rb(g, x, y, 0.08, 1.2, 0.75, 0.6, OM.white, 0.06);
    const top = new THREE.Mesh(rboxGeo(1.2, 0.08, 0.55, 0.03), OM.white); top.position.copy(this.V(x + 0.6, y + 0.5, 0.8)); top.rotation.x = 0.4; top.castShadow = true; g.add(top);
    this.rb(g, x + 0.08, y + 0.05, 0.7, 1.04, 0.22, 0.66, OM.white, 0.06);
    const scr = new THREE.Mesh(G.plane, new THREE.MeshBasicMaterial({ map: monTex(), toneMapped: false })); scr.scale.set(0.86, 0.48, 1); scr.position.copy(this.V(x + 0.6, y + 0.275, 1.04)); g.add(scr);
    const key = new THREE.Mesh(G.plane, OM.green.soft); key.scale.set(0.7, 0.16, 1); key.rotation.x = -Math.PI / 2 + 0.4; key.position.copy(this.V(x + 0.6, y + 0.52, 0.85)); g.add(key);
  }
  canisters(r, x, y) {
    [[0, 0, 0.5], [0.0, 0.55, 0.42], [0.0, 1.1, 0.5], [-0.45, 0.3, 0.36]].forEach(([dx, dy, h]) => {
      this.cyl(r.g, x + dx, y + dy, 0.08, 0.2, h, OM.white);
      this.cyl(r.g, x + dx, y + dy, 0.08 + h, 0.12, 0.06, OM.cyan.soft);
    });
  }
  // a round table with a hologram turning over it: where the league's round is watched
  leagueTable(r, x, y) {
    const g = r.g;
    this.cyl(g, x, y, 0.08, 0.95, 0.42, OM.desk); this.cyl(g, x, y, 0.5, 1.0, 0.05, OM.deskTop);
    const top = new THREE.Mesh(G.cyl, OM.cyan.soft); top.scale.set(0.8, 0.02, 0.8); top.position.copy(this.V(x, y, 0.56)); g.add(top);
    r.spin = new THREE.Group(); r.spin.position.copy(this.V(x, y, 1.15)); g.add(r.spin);
    [0.55, 0.38].forEach((s, i) => { const ring = new THREE.Mesh(G.ringT, OM.cyan.rim); ring.scale.setScalar(s); ring.rotation.x = i ? 0.9 : Math.PI / 2; r.spin.add(ring); });
    const core = new THREE.Mesh(G.sphere, OM.green.glow); core.scale.setScalar(0.12); r.spin.add(core);
  }
  // somewhere to sit and look at the site as a stranger would
  lounge(r, x, y) {
    const g = r.g;
    this.box(g, x, y, 0.08, 2.2, 0.75, 0.32, OM.frame); this.box(g, x, y, 0.4, 2.2, 0.2, 0.42, OM.frame);
    this.box(g, x + 0.5, y + 1.15, 0.08, 1.2, 0.6, 0.3, OM.deskTop);
  }
  // two more screens on a trading desk, turned in a little: charts, green and red
  sideScreens(r, x, y) {
    [[x - 0.35, 0.5], [x + 1.83, -0.5]].forEach(([sx, rot]) => {
      this.box(r.g, sx, y + 0.12, 0.58, 0.48, 0.05, 0.36, OM.dark);
      const f = new THREE.Mesh(G.plane, new THREE.MeshBasicMaterial({ map: candleTex(), toneMapped: false })); f.scale.set(0.44, 0.32, 1);
      f.position.copy(this.V(sx + 0.24, y + 0.15, 0.76)); r.g.add(f);
    });
  }
  // The Manager's room: a dais of light in the middle, rings rising over it round a white-hot core, arcs of light
  // on the floor; the turns-by-department board on a console at the back.
  hubRoom(r) {
    const g = r.g, x0 = r.x0, y0 = r.y0, cy = OM.cyan, c = this.V(x0 + 3.6, y0 + 3.4, 0);
    this.box(g, x0 + 0.5, y0 + 0.25, 0.08, 3.6, 0.7, 0.55, OM.desk);
    const s = screen(3.4, 0.62), m = new THREE.Mesh(G.plane, new THREE.MeshBasicMaterial({ map: s.tex, toneMapped: false })); m.scale.set(3.4, 0.62, 1); m.position.copy(this.V(x0 + 2.3, y0 + 0.1, 1.3)); g.add(m); r.bars = s;
    this.box(g, x0 + 0.55, y0 + 0.05, 0.94, 3.5, 0.04, 0.72, OM.dark, false);
    this.kanban(r, 1.4, 5.4);
    const floor = new THREE.Mesh(G.plane, new THREE.MeshBasicMaterial({ map: hubFloorTex(), color: new THREE.Color(0x00cfff).multiplyScalar(1.2), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
    floor.scale.set(6.4, 6.4, 1); floor.rotation.x = -Math.PI / 2; floor.position.set(c.x, 0.1, c.z); g.add(floor); r.floor = floor;
    [[1.75, 0.2, 0.08], [1.4, 0.34, 0.28]].forEach(([rad, h, z0]) => {
      const d = new THREE.Mesh(G.cyl, OM.plinth); d.scale.set(rad, h, rad); d.position.set(c.x, z0 + h / 2, c.z); d.castShadow = true; d.receiveShadow = true; g.add(d);
      const lip = new THREE.Mesh(G.ringT, cy.rim); lip.scale.setScalar(rad); lip.rotation.x = Math.PI / 2; lip.position.set(c.x, z0 + h, c.z); g.add(lip);
    });
    const core = new THREE.Mesh(G.sphere, cy.glow); core.scale.setScalar(0.34); core.position.set(c.x, 1.25, c.z); g.add(core);
    const halo = glowSprite(0x00cfff, 0.7, 3.2); halo.position.set(c.x, 1.25, c.z); g.add(halo);
    const beam = new THREE.Mesh(G.beam, cy.beam); beam.scale.set(0.9, 3.2, 0.9); beam.position.set(c.x, 2.4, c.z); g.add(beam);
    r.holo = [[0.85, 1.45], [1.25, 1.22], [1.65, 1.0], [2.05, 0.8], [2.45, 0.62], [2.85, 0.46]].map(([y, s], i) => {
      const h = new THREE.Mesh(i % 2 ? G.holoDash : G.ringT, cy.rim); h.scale.setScalar(s); h.rotation.x = Math.PI / 2; h.position.set(c.x, y, c.z); h.userData.y = y; g.add(h); return h;
    });
    r.core = core; r.coreAt = new THREE.Vector3(c.x, 3.4, c.z);
    const light = new THREE.PointLight(0x00cfff, 16, 13, 1.6); light.position.set(c.x, 1.8, c.z); g.add(light);
    this.agent(r, x0 + 3.7, y0 + 5.9, 0, 'Manager', { stand: true });
    this.plant(r, x0 + 6.4, y0 + 0.5);
    this.plate(r, 'hubp'); r.plateAt = this.V(x0 + 6.1, y0 + 6.75, 1.45);
    r.need = document.createElement('div'); r.need.className = 'p3need'; r.need.addEventListener('click', () => CO.emit('office:click', 'hub')); this.layer.appendChild(r.need);
  }
  // the weekly audit: two consoles with green screens, a desk, a printer for the report
  auditRoom(r) {
    const g = r.g, x0 = r.x0, y0 = r.y0;
    this.console3(r, x0 + 0.3, y0 + 0.3); this.console3(r, x0 + 1.7, y0 + 0.3);
    this.wallScreen(r, 3.4, 6.6);
    this.desk(r, x0 + 3.0, y0 + 2.75, 0);
    this.agent(r, x0 + 3.95, y0 + 4.05, 0, 'Supervisor');
    this.rb(g, x0 + 0.35, y0 + 4.4, 0.08, 1.0, 0.8, 0.6, OM.white, 0.06); this.rb(g, x0 + 0.45, y0 + 4.5, 0.68, 0.8, 0.6, 0.07, OM.white2, 0.03);
    this.cabinet(r, x0 + 6.45, y0 + 2.6, 0.45, 2.2, 0.72);
    this.plant(r, x0 + 6.5, y0 + 6.5);
    this.plate(r, 'auditp');
  }
  // The vault: its round door in the back wall, a lit plinth where ET10 (green) and USDC (blue) pile up in stacks of
  // coins under glass. A visitor finds the door shut and the plinth bare: it is always private.
  vaultRoom(r) {
    const g = r.g, x0 = r.x0, y0 = r.y0, A = OM.green, dc = this.V(x0 + 3.5, y0 + 0.17, 1.0);
    const door = new THREE.Mesh(G.cyl, OM.engine); door.scale.set(0.8, 0.1, 0.8); door.rotation.x = Math.PI / 2; door.position.copy(dc); g.add(door);
    const rim = new THREE.Mesh(G.ringT, A.rim); rim.scale.setScalar(0.84); rim.position.copy(dc).add(new THREE.Vector3(0, 0, 0.06)); g.add(rim);
    r.wheel = new THREE.Group(); r.wheel.position.copy(dc).add(new THREE.Vector3(0, 0, 0.08)); g.add(r.wheel);
    for (let k = 0; k < 3; k++) { const s = new THREE.Mesh(G.box, M.metal); s.scale.set(0.95, 0.06, 0.05); s.rotation.z = k * Math.PI / 3; r.wheel.add(s); }
    const hubc = new THREE.Mesh(G.sphere, A.glow); hubc.scale.set(0.08, 0.08, 0.03); r.wheel.add(hubc);
    this.box(g, x0 + 1.4, y0 + 2.2, 0.08, 4.2, 2.6, 0.24, OM.plinth);
    const lip = emis('#00ff88', 0.7);
    [[x0 + 1.4, y0 + 4.8 - 0.03, 4.2, 0.05], [x0 + 1.4, y0 + 2.2 - 0.02, 4.2, 0.05]].forEach(([x, y, w, d]) => this.box(g, x, y, 0.32, w, d, 0.03, lip, false));
    r.pileG = new THREE.Group(); g.add(r.pileG);
    this.plant(r, x0 + 0.42, y0 + 6.5);
    this.plate(r, 'vaultp'); r.plateAt = this.V(x0 + 4.4, y0 + 5.75, 1.45);
    if (r.glow) { r.glow.material.color.set(0x00ff88); r.glowBase = CO.RO ? 0 : 0.14; }
  }
  // the piles, rebuilt only when what they hold changes: five stacks each, taller with every order of magnitude
  piles(r, V, priv) {
    release(r.pileG); r.pileG.clear(); this.vaultPiles = [];
    if (priv) return;
    const x0 = r.x0, y0 = r.y0, o = new THREE.Object3D(), R = rng(5);
    [[V.et10, OM.coinG, x0 + 2.3, 0x00ff88], [V.usdc * 100, OM.coinB, x0 + 4.3, 0x3b82f6]].forEach(([amt, mat, px, col]) => {
      const lvl = Math.max(0, Math.log10(1 + amt / 50)), coins = [];
      [[0, 0, 1], [0.48, 0.12, 0.8], [-0.08, 0.52, 0.7], [0.46, 0.6, 0.55], [0.2, 0.3, 0.9]].forEach(([dx, dy, k], i) => {
        if (lvl <= 0 && i) return;
        const n = Math.max(1, Math.round(lvl * 0.2 * k / 0.04));
        for (let c = 0; c < n; c++) coins.push([px + dx + (R() - 0.5) * 0.035, y0 + 3.0 + dy + (R() - 0.5) * 0.035, 0.34 + c * 0.04, 0]);
      });
      // and a few lying loose on the plinth
      for (let c = 0; c < (lvl > 1 ? 4 : 0); c++) coins.push([px - 0.25 + R() * 1.1, y0 + 2.55 + R() * 1.5, 0.34, 0.25 + R() * 0.3]);
      const im = new THREE.InstancedMesh(G.coin, mat, coins.length);
      coins.forEach(([x, y, z, tilt], i) => { o.position.copy(this.V(x, y, z)); o.rotation.set(tilt, R() * 6, 0); o.scale.set(0.19, 0.034, 0.19); o.updateMatrix(); im.setMatrixAt(i, o.matrix); });
      im.castShadow = true; im.receiveShadow = true; r.pileG.add(im);
      const case_ = new THREE.Mesh(G.box, OM.glass); case_.scale.set(1.25, Math.max(0.5, lvl * 0.2 + 0.25), 1.25); case_.position.copy(this.V(px + 0.25, y0 + 3.35, 0.32 + case_.scale.y / 2)); r.pileG.add(case_);
      const halo = glowSprite(col, 0.09, 2.0); halo.position.copy(this.V(px + 0.25, y0 + 3.35, 0.6 + lvl * 0.2)); halo.userData.y = halo.position.y; r.pileG.add(halo); this.vaultPiles.push(halo);
    });
  }
  // the free lot: open deck marked out with white dashes, a holographic pad on it (a grid of light inside a short
  // wall of light, a dashed ring turning inside, two still ones round it); the label lies inside the ring
  lotRoom(r) {
    const RS = CO.iso.RS, g = r.g, c = this.V(r.x0 + RS / 2, r.y0 + RS / 2, 0.05), ins = 0.35;
    for (let a = ins; a < RS - ins - 0.2; a += 0.75) {
      const w = Math.min(0.42, RS - ins - a);
      [[r.x0 + a, r.y0 + ins], [r.x0 + a, r.y0 + RS - ins]].forEach(([x, y]) => this.box(g, x, y - 0.035, 0.0, w, 0.07, 0.025, OM.dash, false));
      [[r.x0 + ins, r.y0 + a], [r.x0 + RS - ins, r.y0 + a]].forEach(([x, y]) => this.box(g, x - 0.035, y, 0.0, 0.07, w, 0.025, OM.dash, false));
    }
    const pad = new THREE.Mesh(G.plane, new THREE.MeshBasicMaterial({ map: padTex(), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
    pad.scale.set(4.5, 4.5, 1); pad.rotation.x = -Math.PI / 2; pad.position.set(c.x, 0.03, c.z); g.add(pad);
    const wall = new THREE.Mesh(G.pole, new THREE.MeshBasicMaterial({ map: gridTex(), color: new THREE.Color(0x00cfff).multiplyScalar(1.3), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
    wall.scale.set(2.25, 0.5, 2.25); wall.position.set(c.x, 0.27, c.z); g.add(wall);
    [0.03, 0.52].forEach((y) => { const ring = new THREE.Mesh(G.ringT, OM.cyan.rim); ring.scale.setScalar(2.25); ring.rotation.x = Math.PI / 2; ring.position.set(c.x, y, c.z); g.add(ring); });
    r.plus = new THREE.Mesh(G.holoDash, OM.dash); r.plus.scale.setScalar(1.9); r.plus.rotation.x = Math.PI / 2; r.plus.position.set(c.x, 0.05, c.z); g.add(r.plus);
    [2.75, 3.15].forEach((s) => { const ring = new THREE.Mesh(G.holoDash, OM.dash); ring.scale.setScalar(s); ring.rotation.x = Math.PI / 2; ring.position.set(c.x, 0.02, c.z); g.add(ring); });
    const halo = glowSprite(0x00cfff, 0.12, 6); halo.position.set(c.x, 0.4, c.z); g.add(halo);
    const hit = new THREE.Mesh(G.box, M.hit); hit.scale.set(RS, 1.6, RS); hit.position.set(c.x, 0.8, c.z); hit.userData.key = 'lot'; g.add(hit); this.hits.push(hit);
    const el = document.createElement('div'); el.className = 'p3lot'; el.innerHTML = '<b>+</b>ADD DEPARTMENT'; el.addEventListener('click', () => CO.emit('office:click', 'lot')); this.layer.appendChild(el);
    r.plate = el; r.plateAt = new THREE.Vector3(c.x, 0.15, c.z);   // the label lies inside its ring
  }
  /* ---------------- what changes: colours, screens, people, plates ---------------- */
  update() {
    if (!this.cells || this.shape() !== this.shapeKey) { if (this.cells && this.shapeKey) return this.layout(); }
    const S = CO.S, turnsBy = {};
    S.strip.forEach((c) => { turnsBy[c.dept_id] = (turnsBy[c.dept_id] || 0) + 1; });
    let anyWork = false;
    S.departments.forEach((d) => {
      const r = this.rooms['d' + d.id]; if (!r) return;
      const v = CO.deptView(d), ln = CO.deptLine(d, v), st = ln.tone === 'red' ? 'waiting' : v.status;
      if (v.status === 'working') anyWork = true;
      this.tint(r, st);
      // up next is a blue dot on the plate, nothing more: its screen and its plate's frame stay slate
      const dot = '#' + new THREE.Color(STC[st]).getHexString();
      let title, sub, mode, col = st === 'queued' ? '#a9b8cc' : dot;
      if (v.running) { title = v.running.title; sub = CO.expertName(v.running.expert) + ' is on it'; mode = 'run'; }
      else if (v.waiting) { title = 'Needs you'; sub = 'approve or reject on the right'; mode = 'full'; col = '#ff4444'; }
      else if (v.queued.length) { title = 'Up next: ' + v.queued[0].title; sub = ''; mode = ''; }
      else { title = d.schedule && d.next_run ? 'Next run at ' + CO.hhmm(d.next_run) : 'Idle'; sub = ''; mode = ''; }
      if (r.wall) drawWall(r.wall, title, sub, col, mode);
      if (r.kb) drawKanban(r.kb, { queued: v.queued.length, running: v.running ? 1 : 0, done: v.done, failed: v.failed });
      v.experts.slice(0, 3).forEach((e, i) => { const a = r.agents[i]; if (a) a.working = e.state === 'working'; if (r.mons[i]) r.mons[i].color.set(e.state === 'working' ? new THREE.Color(0x00cfff).multiplyScalar(2.2) : new THREE.Color(OFFICE.mon)); });
      const n = d.et10 || 0, et = d.files_as ? '<span class="et' + (n ? ' lit' : '') + '">' + (n ? '+' : '') + n.toLocaleString('en-US') + ' ET10</span>' : '';
      const html = '<div class="p3h"><i style="background:' + (ln.tone === 'red' ? '#ff4444' : dot) + '"></i><b>' + esc(d.name.toUpperCase()) + '</b>' + et + '</div><div class="p3l" style="color:' + (TONEC[ln.tone] || '#a9b8cc') + '">' + esc(ln.short) + '</div>';
      if (r.plate && r.plate._h !== html) { r.plate._h = html; r.plate.innerHTML = html; }
      if (r.plate) { r.plate.classList.toggle('work', v.status === 'working'); r.plate.style.setProperty('--c', ln.tone === 'red' ? '#ff4444' : col); }
      if (this.conduits['d' + d.id]) { const cm = this.conduits['d' + d.id].mat; cm.emissive.set(v.status === 'working' ? 0x00cfff : 0xdfe6ee); cm.emissiveIntensity = v.status === 'working' ? 1.6 : 0.3; }
    });
    const hub = this.rooms.hub;
    if (hub) {
      const paused = S.company.status === 'paused';
      this.tint(hub, paused ? 'idle' : 'working');
      if (hub.bars) drawBars(hub.bars, 'TURNS BY DEPT TODAY', S.departments.map((d) => { const v = CO.deptView(d); return ['#' + new THREE.Color(v.status === 'idle' ? STC.queued : STC[v.status]).getHexString(), turnsBy[d.id] || 0]; }));
      if (hub.kb) drawKanban(hub.kb, { queued: S.plan.length, running: S.tasks.filter((t) => t.status === 'running').length, done: S.strip.filter((c) => c.state === 'done').length, failed: S.strip.filter((c) => c.state === 'failed').length });
      if (hub.agents[0]) hub.agents[0].working = !paused;
      const html = '<div class="p3h"><i style="background:' + (paused ? '#7f93ad' : '#00cfff') + '"></i><b>MANAGER</b></div><div class="p3l" style="color:' + (paused ? '#a9b8cc' : '#00cfff') + '">' + (paused ? 'Paused' : (CO.RO ? 'Its chat' : 'Your chat') + ' · runs it all') + '</div>';
      if (hub.plate._h !== html) { hub.plate._h = html; hub.plate.innerHTML = html; }
      hub.plate.classList.toggle('work', !paused && anyWork); hub.plate.style.setProperty('--c', paused ? '#7f93ad' : '#00cfff');
      const na = S.approvals.length;
      hub.need.hidden = !na; hub.need.textContent = na + (CO.RO ? ' WAIT FOR ITS OWNER' : na === 1 ? ' NEEDS YOU' : ' NEED YOU');
    }
    const au = this.rooms.audit;
    if (au) {
      const A = S.audit, days = Math.max(0, Math.ceil((A.next_at - S.clock) / 86400000)), nf = A.last ? A.last.findings.length : 0;
      this.tint(au, 'idle');
      drawWall(au.wall, 'Weekly audit: next in ' + days + 'd', nf + ' findings last week', '#7f93ad', '');
      const html = '<div class="p3h"><i style="background:#7f93ad"></i><b>WEEKLY AUDIT</b></div><div class="p3l" style="color:#a9b8cc">next in ' + days + (days === 1 ? ' day' : ' days') + '</div>';
      if (au.plate._h !== html) { au.plate._h = html; au.plate.innerHTML = html; }
      au.plate.style.setProperty('--c', '#7f93ad');
    }
    // the vault: two numbers on its plate, the piles behind it; a visitor reads only that it is private
    const vr = this.rooms.vault;
    if (vr) {
      const VT = CO.vaultTotals(), priv = !!CO.RO, key = priv ? 'priv' : Math.round(VT.et10) + '|' + VT.usdc.toFixed(2);
      if (vr.pkey !== key) { vr.pkey = key; this.piles(vr, VT, priv); }
      this.tint(vr, 'idle'); if (vr.edgeM) { vr.edgeM.emissive.set(0x00ff88); vr.edgeM.emissiveIntensity = 0.7; }
      const html = '<div class="p3h"><i style="background:#00ff88"></i><b>VAULT</b></div>' +
        (priv ? '<div class="p3l" style="color:#a9b8cc">Private</div>' : '<div class="p3l"><span class="g">' + CO.fmtEt(VT.et10) + ' ET10</span> · <span class="u">' + CO.fmtUsd(VT.usdc) + ' USDC</span></div>');
      if (vr.plate._h !== html) { vr.plate._h = html; vr.plate.innerHTML = html; }
      vr.plate.style.setProperty('--c', '#00ff88');
    }
    this.paused = S.company.status === 'paused';
    this.drawSel();
  }
  // a room in the colour of what it does: working cyan and waiting red light the room; up next and idle keep a
  // slate edge under plain white light (up next says itself on the plate and the wall screen)
  tint(r, st) {
    if (r.st === st) return; r.st = st;
    // a room at rest keeps a dim green edge: green is the office's structure, cyan and red what its rooms do
    const lit = st === 'working' || st === 'waiting', c = new THREE.Color(lit ? STC[st] : 0x00ff88);
    if (r.edgeM) { r.edgeM.emissive.copy(c); r.edgeM.emissiveIntensity = lit ? 1.6 : st === 'queued' ? 0.85 : 0.7; }
    if (r.sillM) { r.sillM.emissive.copy(c); r.sillM.emissiveIntensity = lit ? 0.6 : 0.1; }
    if (r.glow) { r.glow.material.color.copy(lit ? c : new THREE.Color(0xdfe6ee)); r.glowBase = st === 'working' ? 0.3 : st === 'waiting' ? 0.5 : 0.06; }
    if (r.lamp) { r.lamp.color.copy(lit ? c : new THREE.Color(OFFICE.lamp)); r.lamp.intensity = st === 'working' ? 16 : st === 'waiting' ? 18 : 9; }
  }
  drawSel() {
    release(this.selRing); this.selRing.clear();
    const c = this.sel && this.cells[this.sel]; if (!c) return;
    const RS = CO.iso.RS, m = emis('#00cfff', 1.2), x0 = c[0] - 0.15, y0 = c[1] - 0.15, s = RS + 0.3;
    [[x0, y0, s, 0.08], [x0, y0 + s - 0.08, s, 0.08]].forEach(([x, y, w, d]) => this.box(this.selRing, x, y, 0.12, w, d, 0.04, m, false));
    [[x0, y0, 0.08, s], [x0 + s - 0.08, y0, 0.08, s]].forEach(([x, y, w, d]) => this.box(this.selRing, x, y, 0.12, w, d, 0.04, m, false));
  }
  select(key) { this.sel = key; this.update(); }

  /* ---------------- packets along the corridors ---------------- */
  packet(from, to, colour, delay) {
    let p;
    if (from === 'hub' && this.paths[to]) p = this.paths[to].slice().reverse();
    else if (to === 'hub' && this.paths[from]) p = this.paths[from].slice();
    else if (this.paths[from] && this.paths[to]) p = this.paths[from].concat(this.paths[to].slice().reverse().slice(1));
    if (!p) return;
    const hex = { cyan: '#00cfff', green: '#00ff88', red: '#ff4444', blue: '#3b82f6' }[colour] || '#00cfff', A = amat(hex);
    const g = new THREE.Group(), core = new THREE.Mesh(G.sphere, A.glow); core.scale.setScalar(0.12); g.add(core);
    const halo = new THREE.Mesh(G.sphere, A.atmo); halo.scale.setScalar(0.32); g.add(halo);
    const trail = [0.09, 0.07, 0.05, 0.035].map((s) => { const t = new THREE.Mesh(G.sphere, A.glow); t.scale.setScalar(s); this.pk.add(t); return t; });
    g.visible = false; this.pk.add(g);
    let len = 0; for (let i = 1; i < p.length; i++) len += Math.abs(p[i][0] - p[i - 1][0]) + Math.abs(p[i][1] - p[i - 1][1]);
    this.packets.push({ g, trail, p, len, t0: performance.now() + (delay || 0), dur: Math.max(900, len * 150), to });
  }
  along(p, f, len) {
    let d = f * len;
    for (let i = 1; i < p.length; i++) { const s = Math.abs(p[i][0] - p[i - 1][0]) + Math.abs(p[i][1] - p[i - 1][1]); if (d <= s || i === p.length - 1) { const k = s ? Math.min(1, d / s) : 0; return [p[i - 1][0] + (p[i][0] - p[i - 1][0]) * k, p[i - 1][1] + (p[i][1] - p[i - 1][1]) * k]; } d -= s; }
    return p[p.length - 1];
  }
  // now and then an idle agent gets up and walks a few steps, then goes back
  wander() {
    if (document.hidden || !this.rooms) return;
    const idle = []; Object.values(this.rooms).forEach((r) => r.agents.forEach((a) => { if (!a.working && !a.walk) idle.push(a); }));
    if (!idle.length || Math.random() < 0.4) return;
    const a = idle[Math.floor(Math.random() * idle.length)], r = a.room, to = this.V(r.x0 + 2.2 + Math.random() * 1.8, r.y0 + 4.4 + Math.random() * 0.8, 0.1);
    a.walk = { from: a.home.clone(), to, t0: performance.now(), dur: 2200, stay: 1600 + Math.random() * 1600 };
  }

  /* ---------------- camera ---------------- */
  // The whole office, as large as the stage allows: the camera's angle is fixed, its distance is the nearest at which
  // every slab's corners fit (a margin at the top for the stage's own bar), and it aims at the middle of what it sees.
  home() {
    const dir = new THREE.Vector3().setFromSpherical(new THREE.Spherical(1, 1.0, Math.PI / 4)), cam = this.camera.clone(), pts = this.corners || [];
    const tgt = new THREE.Vector3(); pts.forEach((p) => tgt.add(p)); if (pts.length) tgt.divideScalar(pts.length); tgt.y = 0;
    const fits = (d, t) => { cam.position.copy(t).addScaledVector(dir, d); cam.lookAt(t); cam.updateMatrixWorld(); return pts.every((p) => { const v = p.clone().project(cam); return Math.abs(v.x) < 1.02 && v.y < 0.86 && v.y > -0.97; }); };
    let d = 30;
    for (let k = 0; k < 2; k++) {
      let lo = 8, hi = 300;
      for (let i = 0; i < 22; i++) { const mid = (lo + hi) / 2; if (fits(mid, tgt)) hi = mid; else lo = mid; }
      d = hi;
      // aim at the middle of the picture, not of the plan: shift the target by the bounds' offset on screen
      cam.position.copy(tgt).addScaledVector(dir, d); cam.lookAt(tgt); cam.updateMatrixWorld();
      let x0 = 1, x1 = -1, y0 = 1, y1 = -1; pts.forEach((p) => { const v = p.clone().project(cam); x0 = Math.min(x0, v.x); x1 = Math.max(x1, v.x); y0 = Math.min(y0, v.y); y1 = Math.max(y1, v.y); });
      const right = new THREE.Vector3().setFromMatrixColumn(cam.matrixWorld, 0), up = new THREE.Vector3().setFromMatrixColumn(cam.matrixWorld, 1);
      const h = 2 * d * Math.tan(THREE.MathUtils.degToRad(cam.fov) / 2), w = h * cam.aspect;
      tgt.addScaledVector(right, (x0 + x1) / 2 * w / 2).addScaledVector(up, ((y0 + y1) / 2 + 0.06) * h / 2);
    }
    return { pos: tgt.clone().addScaledVector(dir, d), tgt };
  }
  fit(anim) { const h = this.home(); this.fitted = true; this.tween(h.pos, h.tgt, anim === false ? 0 : 750); }
  zoom(f) {
    const t = this.controls.target, off = this.camera.position.clone().sub(t);
    const len = Math.max(this.controls.minDistance, Math.min(this.controls.maxDistance, off.length() * f));
    this.tween(t.clone().add(off.setLength(len)), t.clone(), 300);
  }
  focus(key, leftPx, tight) {
    const c = this.cells[key]; if (!c) return;
    const RS = CO.iso.RS, tgt = this.V(c[0] + RS / 2, c[1] + RS / 2 + 0.4, 0.5);
    const dir = new THREE.Vector3().setFromSpherical(new THREE.Spherical(1, 0.88, Math.PI / 4));
    this.tween(tgt.clone().add(dir.multiplyScalar(tight ? 23 : 27)), tgt, 750);
  }
  tween(pos, tgt, ms, done) {
    if (!ms) { this.camera.position.copy(pos); this.controls.target.copy(tgt); this.controls.update(); this.tw = null; if (done) done(); return; }
    this.tw = { p0: this.camera.position.clone(), t0: this.controls.target.clone(), p1: pos.clone(), t1: tgt.clone(), s: performance.now(), ms, done };
  }
  resize() {
    const w = this.el.clientWidth, h = this.el.clientHeight; if (!w || !h) return;
    this.camera.aspect = w / h; this.camera.updateProjectionMatrix(); this.renderer.setSize(w, h, false);
    if (this.fitted && !this.moved && !this.sel && !this.tw) this.fit(false);
  }

  /* ---------------- the frame ---------------- */
  frame() {
    const w = this.el.clientWidth, h = this.el.clientHeight; if (!w || !h) return;
    if (w !== this._cw || h !== this._ch) { this._cw = w; this._ch = h; this.resize(); }
    const t = this.clock.getElapsedTime(), now = performance.now();
    if (this.tw) {
      const k = Math.min(1, (now - this.tw.s) / this.tw.ms), e = k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
      this.camera.position.lerpVectors(this.tw.p0, this.tw.p1, e); this.controls.target.lerpVectors(this.tw.t0, this.tw.t1, e);
      if (k >= 1) { const d = this.tw.done; this.tw = null; if (d) d(); }
    }
    this.controls.update();
    this.sky.position.copy(this.camera.position);
    if (this.drift) this.drift.forEach((d, i) => { d.m.rotation.y = t * d.sp + i; d.m.rotation.x = t * d.sp * 0.6 + i * 2; });
    if (this.flames) this.flames.forEach((f) => { const k = 0.85 + 0.15 * Math.sin(t * 13 + f.ph) + 0.05 * Math.sin(t * 31 + f.ph); f.fl.scale.set(0.85 * k, 2.2 * (0.9 + 0.1 * k), 0.85 * k); });
    if (this.vaultPiles) this.vaultPiles.forEach((p, i) => { p.position.y = p.userData.y + Math.sin(t * 1.2 + i) * 0.03; });
    Object.values(this.rooms).forEach((r) => {
      if (r.grow) { const k = Math.min(1, (now - r.grow) / 1200), e = 1 - Math.pow(1 - k, 3); r.g.scale.set(1, Math.max(0.01, e), 1); if (k >= 1) r.grow = 0; }
      if (r.glow) r.glow.material.opacity = (r.glowBase || 0) * (r.st === 'working' ? 0.75 + 0.25 * Math.sin(t * 2.4 + r.x0) : 1);
      if (r.leds) r.leds.forEach((m, i) => { m.visible = ((Math.floor(t * 3 + m.userData.blink)) % 3) !== 0; });
      if (r.holo) { r.holo.forEach((hh, i) => { hh.rotation.z = t * (0.6 + i * 0.35) * (i % 2 ? -1 : 1); hh.position.y = hh.userData.y + Math.sin(t * 1.3 + i) * 0.05; }); r.core.position.y = 1.25 + Math.sin(t * 1.7) * 0.06; }
      if (r.spin) r.spin.rotation.y = t * 0.6;
      if (r.floor) r.floor.rotation.z = t * 0.05;
      if (r.plus) r.plus.rotation.z = t * 0.25;
      if (r.wheel) r.wheel.rotation.z = t * 0.12;
      r.agents.forEach((a) => {
        if (a.walk) {
          const W2 = a.walk, f = (now - W2.t0) / W2.dur;
          if (a.working) { a.walk = null; a.g.position.copy(a.home); }
          else if (f < 1) a.g.position.lerpVectors(W2.from, W2.to, f < 0.5 ? 2 * f * f : 1 - Math.pow(-2 * f + 2, 2) / 2);
          else if (now < W2.t0 + W2.dur + W2.stay) a.g.position.copy(W2.to);
          else if (!W2.back) { W2.back = true; W2.from = W2.to.clone(); W2.to = a.home.clone(); W2.t0 = now; W2.stay = 0; }
          else { a.walk = null; a.g.position.copy(a.home); }
        }
        const walking = !!a.walk && !a.standing;
        if (a.sit && !a.standing) { a.sit.visible = !walking; a.stand.visible = walking; }
        if (a.walk) { const W3 = a.walk, dx = W3.to.x - W3.from.x, dz = W3.to.z - W3.from.z; a.g.rotation.y = (now - W3.t0) < W3.dur && Math.hypot(dx, dz) > 0.01 ? Math.atan2(-dx, -dz) : a.g.rotation.y; } else a.g.rotation.y = 0;
        a.b.position.y = a.by + (walking ? 0.1 : 0) + (a.working ? Math.abs(Math.sin(t * 7 + a.phase)) * 0.02 : 0);
        // an astronaut at work: its visor and its chest light go cyan
        a.visorM.emissiveIntensity = a.working ? 1.3 : 0.06; a.chest.material = a.working ? OM.cyan.glow : OM.pack;
        a.ringM.emissiveIntensity = a.working ? 1.8 * (1 - ((t * 0.9 + a.phase) % 1)) : 0;
        a.ring.scale.setScalar(a.working ? 0.3 + ((t * 0.9 + a.phase) % 1) * 0.35 : 0.3);
      });
    });
    // packets
    this.packets = this.packets.filter((k) => {
      const f = (now - k.t0) / k.dur;
      if (f < 0) return true;
      if (f >= 1) { this.pk.remove(k.g); k.trail.forEach((m) => this.pk.remove(m)); return false; }
      const e = f < 0.5 ? 2 * f * f : 1 - Math.pow(-2 * f + 2, 2) / 2, q = this.along(k.p, e, k.len);
      k.g.visible = true; k.g.position.copy(this.V(q[0], q[1], 0.22));
      k.trail.forEach((m, i) => { const tq = this.along(k.p, Math.max(0, e - (i + 1) * 0.02), k.len); m.position.copy(this.V(tq[0], tq[1], 0.22)); });
      return true;
    });
    if (this.mouseMoved) { this.mouseMoved = false; this.pick(); }
    try { if (this.post) this.post.render(); else this.renderer.render(this.scene, this.camera); this.frames = (this.frames || 0) + 1; }
    catch (e) { console.error('3D office stopped:', e); this.renderer.setAnimationLoop(null); if (this.onFail && !(this.frames > 30)) this.onFail(e); return; }
    this.labels(w, h);
  }
  // plates over their rooms; agents' names only in the room that is open or under the mouse
  labels(w, h) {
    const v = new THREE.Vector3(), show = (el, p, dy) => {
      v.copy(p).project(this.camera);
      const y = (1 - v.y) / 2 * h + (dy || 0);
      // off screen, behind the camera, or up under the stage's own bar (where the crumb and the zoom live)
      const off = v.z > 1 || v.x < -1.3 || v.x > 1.3 || y < 58 || y > h + 40;
      el.style.display = off ? 'none' : '';
      if (!off) el.style.transform = 'translate(' + ((v.x + 1) / 2 * w).toFixed(1) + 'px,' + y.toFixed(1) + 'px) translate(-50%,-50%)';
    };
    Object.values(this.rooms).forEach((r) => {
      if (r.plate && r.plateAt) { show(r.plate, r.plateAt); r.plate.classList.toggle('sel', this.sel === r.key); r.plate.classList.toggle('hov', this.hover === r.key); }
      if (r.need && !r.need.hidden) show(r.need, r.coreAt, -10);
      const named = this.sel === r.key || this.hover === r.key;
      r.agents.forEach((a) => { a.el.classList.toggle('on', named); if (named) show(a.el, a.g.position.clone().add(new THREE.Vector3(0, 1.85, 0))); });
    });
  }

  /* ---------------- input ---------------- */
  bind() {
    const cv = this.renderer.domElement; let down = null;
    cv.addEventListener('pointerdown', (e) => { down = { x: e.clientX, y: e.clientY }; });
    cv.addEventListener('pointermove', (e) => { this.setMouse(e); this.mouseMoved = true; this.lastEv = e; });
    cv.addEventListener('pointerleave', () => { this.setHover(null); this.hideTip(); });
    cv.addEventListener('pointerup', (e) => {
      if (!down) return; const moved = Math.abs(e.clientX - down.x) + Math.abs(e.clientY - down.y) > 5; down = null; if (moved) return;
      this.setMouse(e); const hit = this.pickHit(); if (!hit) return;
      if (hit.userData.pc) { window.open(hit.userData.pc.url, '_blank', 'noopener'); return; }
      if (hit.userData.key) CO.emit('office:click', hit.userData.key);
    });
    cv.addEventListener('wheel', () => { this.tw = null; }, { passive: true });
  }
  setMouse(e) { const r = this.renderer.domElement.getBoundingClientRect(); this.mouse.set((e.clientX - r.left) / r.width * 2 - 1, -(e.clientY - r.top) / r.height * 2 + 1); }
  pickHit() {
    this.ray.setFromCamera(this.mouse, this.camera);
    // a computer stands inside its room's hit box, which the ray always enters first: ask the computers first
    const pc = this.ray.intersectObjects(this.pcs || [], false);
    if (pc.length) return pc[0].object;
    const hits = this.ray.intersectObjects(this.hits || [], false);
    return hits.length ? hits[0].object : null;
  }
  pick() {
    const hit = this.pickHit();
    const key = hit ? (hit.userData.key || null) : null;
    this.setHover(hit && hit.userData.pc ? this.roomOf(hit) : key);
    this.renderer.domElement.style.cursor = hit ? 'pointer' : '';
    if (!hit || !this.lastEv) return this.hideTip();
    let html = '';
    if (hit.userData.pc) html = '<b>' + esc(hit.userData.pc.label) + ' ↗</b><br><span style="color:#7f93ad">' + esc(String(hit.userData.pc.url).replace(/^https:\/\//, '')) + '</span>';
    else if (key) html = this.tipFor('room', key);
    if (!html) return this.hideTip();
    const r = this.stage.getBoundingClientRect(), e = this.lastEv;
    this.tip.innerHTML = html; this.tip.hidden = false;
    let x = e.clientX - r.left + 14, y = e.clientY - r.top + 14;
    if (x + this.tip.offsetWidth > r.width - 8) x = e.clientX - r.left - this.tip.offsetWidth - 14;
    if (y + this.tip.offsetHeight > r.height - 8) y = e.clientY - r.top - this.tip.offsetHeight - 14;
    this.tip.style.left = x + 'px'; this.tip.style.top = y + 'px';
  }
  roomOf(obj) { for (const k in this.rooms) { let o = obj; while (o) { if (o === this.rooms[k].g) return k; o = o.parent; } } return null; }
  setHover(key) { this.hover = key; }
  hideTip() { if (this.tip) this.tip.hidden = true; }
  dispose() { try { this.renderer.setAnimationLoop(null); this.renderer.dispose(); } catch (e) { /* gone */ } this.layer.innerHTML = ''; this.el.innerHTML = ''; }
}

// can this browser draw it at all? WebGPU, or WebGL2 underneath it
(function () {
  let gl2 = false;
  try { gl2 = !!document.createElement('canvas').getContext('webgl2'); } catch (e) { gl2 = false; }
  CO.U3 = (gl2 || navigator.gpu) ? { ok: true, gpu: !!navigator.gpu, universe: (el, stage, h) => new Universe3D(el, stage, h), office: (el, stage, tipFor) => new Office3D(el, stage, tipFor), preview, thumbs, THREE, geo, makeStation, SKIN, amat, nebTex, TX }
    : { failed: true, why: 'no WebGPU and no WebGL2' };
  window.dispatchEvent(new Event('co3d'));
})();
