/* The /company mockup's 3D engine. The Universe is a galaxy: Cymetica the star at its heart, every company a
 * station on one of its spiral arms, ONE DECK PER DEPARTMENT, a deck lit while its department works. three.js with
 * its WebGPU renderer (WebGL2 where a browser has no WebGPU), bloom on everything that glows, an orbit camera that
 * zooms to the cursor. Banners and the tooltip are HTML over the canvas, so they stay sharp and clickable. If the
 * renderer cannot start, the page keeps the flat map. The office in 3D is the second half of this file. */
import * as THREE from 'three/webgpu';
import { pass, renderOutput, vec4, vec3, mrt, output, normalView, dot, mix } from 'three/tsl';
import * as TSL from 'three/tsl';
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
function dashedRing(n, fill, tube = 0.02) {
  const parts = [];
  for (let i = 0; i < n; i++) { const t = new THREE.TorusGeometry(1, tube, 6, 8, Math.PI * 2 / n * fill); t.rotateZ(i * Math.PI * 2 / n); parts.push(t); }
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
// How often a scene is drawn (2026-10-19, for weak computers; nothing is drawn differently, only less often while
// nobody is doing anything). Every display frame while something moves under the user's hand -- a drag, the wheel,
// a flight, the camera settling after it, a station the camera rides with -- and for the first seconds. Otherwise
// what moves is the scene's own slow motion (rings, lights, people, stations on their orbits): a 120 or 144 Hz
// screen gets it every other display frame (60 or 72 a second, nothing it shows is lost), and a computer that could
// not hold about 45 a second while everything moved gets it at 30, so it has room to answer the next drag at once.
function pacer(busy) {
  let last = 0, drawn = 0, avg = 0, slow = false; const t0 = performance.now();
  return (now) => {
    const dt = now - last; last = now;
    if (busy() || now - t0 < 3000) {
      if (dt > 0 && dt < 250) { avg = avg ? avg * 0.94 + dt * 0.06 : dt; slow = avg > 22 ? true : avg < 18 ? false : slow; }
      drawn = now; return true;
    }
    if (now - drawn < (slow ? 30 : 12.5)) return false;
    drawn = now; return true;
  };
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
// Spire, Vector Trading in his orrery: a glass tower of decks on a plinth, a band of light up two of its faces and
// lit slats across the other two (a deck's slats are its windows), lit edges, a square of light in its roof and a
// mast; four solar wings off the platform, light tubes round a column under it and an engine at the column's foot
SKIN.tower = (b, n) => {
  const A = b.A, X = srdA(A), s = fpOf(n) + 1.3, h = 0.2 * s, ts = 0.38 * s, H = s * (0.3 + 0.065 * n), dh = H / n, R = b.R;
  srdM();
  const kb = srdBase(b, s, h, { hull: X.hullT, keel: 0.44, keelMat: X.hullT2 });
  const ps = 0.7 * s, ph = 0.055 * s, pr = ph * 0.45;
  b.part(srdRBox(ps, ph, ps, pr), X.hullT2, 1, 1, 1, 0, ph / 2, 0);
  b.part(srdLoop(ps - pr * 0.5, ps - pr * 0.5, pr * 0.75, 0.026), X.neon, 1, 1, 1, 0, ph - pr * 0.22, 0);
  for (let k = 0; k < 4; k++) srdWing(b, k * Math.PI / 2, s / 2, -h * 0.5, 0.5 * s, 0.22 * s, { lanes: 2, nx: 3, ny: 1 });
  const cs = 0.26 * s, ch = 0.3 * s;
  b.box(cs, ch, cs, 0, kb - ch / 2, 0, X.hullT);
  for (const [sx, sz] of SRD.corners) b.cyl(0.014 * s, ch * 0.9, sx * cs * 0.62, kb - ch * 0.48, sz * cs * 0.62, A.rim);
  for (const [sx, sz] of [[1, 0], [0, 1], [-1, 0], [0, -1]]) b.cyl(0.011 * s, ch * 0.7, sx * cs * 0.53, kb - ch * 0.45, sz * cs * 0.53, A.soft);
  b.box(cs * 1.15, 0.05 * s, cs * 1.15, 0, kb - ch - 0.025 * s, 0, X.hullT2);
  srdJet(b, 0, kb - ch - 0.05 * s, 0, 0.6 * cs, 0.14 * s);
  let y = ph;
  for (let f = 0; f < n; f++) {
    b.box(ts, dh - 0.03, ts, 0, y + dh / 2, 0, X.glassT);
    if (f) b.box(ts + 0.05, 0.035, ts + 0.05, 0, y, 0, M.trim);
    const k = Math.max(1, Math.round(dh / 0.3)), sh = dh / k;
    for (let i = 0; i < k; i++) {
      const yy = y + sh * (i + 0.5);
      for (const sx of [1, -1]) b.win(sx * (ts / 2 + 0.012), yy, 0, sx * Math.PI / 2, ts * 0.64, Math.min(0.09, sh * 0.34), f, R() < 0.6);
      for (const sz of [1, -1]) for (const o of [-1, 1]) b.win(o * ts * 0.3, yy, sz * (ts / 2 + 0.012), sz > 0 ? 0 : Math.PI, ts * 0.13, sh * 0.5, f, R() < 0.5);
    }
    y += dh;
  }
  for (const sz of [1, -1]) b.box(ts * 0.12, H - 0.06, 0.025, 0, ph + H / 2, sz * (ts / 2 + 0.008), A.rim);
  for (const [sx, sz] of SRD.corners) b.box(0.08, H, 0.08, sx * ts / 2, ph + H / 2, sz * ts / 2, A.rim);
  b.part(srdRBox(ts + 0.12, 0.16, ts + 0.12, 0.05), X.hullT2, 1, 1, 1, 0, y + 0.08, 0);
  b.box(ts * 0.62, 0.03, ts * 0.62, 0, y + 0.17, 0, A.soft);
  const mh = 0.2 * s; b.cyl(0.025, mh, 0, y + 0.16 + mh / 2, 0, M.metal);
  b.beacon(0, y + 0.18 + mh, 0, 0.07);
  b.top = y + 0.3 + mh; b.bot = kb - ch - 0.1; b.foot = s / 2 + 0.1 + 0.5 * s + 0.15;
};
/* The Spire, the Ring station and the Biodome as in the operator's orrery (look-universe.webp): a square platform with
 * rounded corners, a line of the company's colour along its top edge, solar wings off its sides, engines that glow
 * blue whatever the company's colour. Their parts are their own (srd*), so the shared builders stay as they are, and
 * their materials hang on M and on the colour's own set, where release() leaves them alone. Sizes are in parts of
 * the platform's side, read off the picture. */
const SRD = { jet: 0x63c4ff, corners: [[1, 1], [1, -1], [-1, 1], [-1, -1]] };
function srdA(A) {
  if (A.srd) return A.srd;
  const c = A.c, tint = (hex, k) => new THREE.Color(hex).lerp(c, k);
  // Matte enough to read in space without anything for a metal to reflect, and lit a little from within: the map's
  // sun stands behind a station as often as before it, and his picture has no side in the dark.
  A.srd = {
    hullT: srdHull(tint(0x253545, 0.13), 0.6),
    hullT2: srdHull(tint(0x334558, 0.11), 0.55),
    glassT: std({ color: tint(0x1a3846, 0.32), roughness: 0.25, metalness: 0.2, emissive: c, emissiveIntensity: 0.18 }),
    hullD: srdHull(tint(0x232e2d, 0.18), 0.62),
    hullD2: srdHull(tint(0x323e3c, 0.16), 0.55),
    glassD: std({ color: c.clone().multiplyScalar(0.5), emissive: c, emissiveIntensity: 0.55, transparent: true, opacity: 0.48, roughness: 0.08, metalness: 0.1, depthWrite: false, side: THREE.DoubleSide }),
    neon: std({ color: 0x000000, emissive: c, emissiveIntensity: 1.5, roughness: 1 })
  };
  return A.srd;
}
function srdHull(color, rough) { const c = new THREE.Color(color); return std({ color: c, roughness: rough, metalness: 0.15, emissive: c.clone().multiplyScalar(0.16) }); }
function srdM() {
  if (M.srdJet) return M;
  M.srdJet = new THREE.MeshBasicMaterial({ color: new THREE.Color(SRD.jet).multiplyScalar(1.2), transparent: true, opacity: 0.11, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
  M.srdJetCore = new THREE.MeshBasicMaterial({ color: new THREE.Color(0x3ab4ff).multiplyScalar(1.7) });
  M.srdPlate = srdHull(0xa4a2ad, 0.55);
  M.srdSteel = srdHull(0x74767f, 0.5);
  M.srdSteel2 = srdHull(0x5a5c66, 0.55);
  M.srdCap = srdHull(0xc8cad2, 0.4);
  M.srdModule = srdHull(0xa7b0bb, 0.5);
  M.srdLamp = std({ color: 0x000000, emissive: new THREE.Color(0x52d6e8), emissiveIntensity: 1.1, roughness: 1 });
  return M;
}
// solar cells as in his picture: slate-blue cells with pale lines in a light frame, nx along a panel and ny across it
function srdSolar(nx, ny) {
  const k = 'srdSolar' + nx + 'x' + ny;
  if (M[k]) return M[k];
  const t = TX[k] || (TX[k] = ctex(nx * 80, ny * 80, (g, W, H) => {
    g.fillStyle = '#b6c1d2'; g.fillRect(0, 0, W, H);
    const m = 4, sx = (W - 2 * m) / nx, sy = (H - 2 * m) / ny;
    for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++) {
      const x = m + i * sx, y = m + j * sy, gr = g.createLinearGradient(x, y, x + sx, y + sy);
      gr.addColorStop(0, '#6683b0'); gr.addColorStop(1, '#41598a'); g.fillStyle = gr; g.fillRect(x + 1.5, y + 1.5, sx - 3, sy - 3);
      g.strokeStyle = 'rgba(205,220,250,.4)'; g.lineWidth = 1; g.beginPath();
      for (let q = 1; q < 4; q++) { const ox = x + 1.5 + q * (sx - 3) / 4, oy = y + 1.5 + q * (sy - 3) / 4; g.moveTo(ox, y + 2); g.lineTo(ox, y + sy - 2); g.moveTo(x + 2, oy); g.lineTo(x + sx - 2, oy); }
      g.stroke();
    }
  }));
  return (M[k] = std({ map: t, emissive: 0xffffff, emissiveMap: t, emissiveIntensity: 0.26, roughness: 0.45, metalness: 0.15 }));
}
function srdRR(w, d, r) {
  const s = new THREE.Shape(), x = w / 2, y = d / 2;
  s.moveTo(-x + r, -y);
  s.lineTo(x - r, -y); s.absarc(x - r, -y + r, r, -Math.PI / 2, 0, false);
  s.lineTo(x, y - r); s.absarc(x - r, y - r, r, 0, Math.PI / 2, false);
  s.lineTo(-x + r, y); s.absarc(-x + r, y - r, r, Math.PI / 2, Math.PI, false);
  s.lineTo(-x, -y + r); s.absarc(-x + r, -y + r, r, Math.PI, Math.PI * 1.5, false);
  return s;
}
const srdKey = (p, v) => p + v.map((x) => x.toFixed(3)).join(',');
function srdRBox(w, h, d, r) { const k = srdKey('srdRB', [w, h, d, r]); return G[k] || (G[k] = new RoundedBoxGeometry(w, h, d, 4, r)); }
// a tube of light along a rounded square, lying flat
function srdLoop(w, d, r, tube) {
  const k = srdKey('srdLp', [w, d, r, tube]);
  if (G[k]) return G[k];
  const pts = srdRR(w, d, r).getSpacedPoints(200).map((p) => new THREE.Vector3(p.x, 0, -p.y)); pts.pop();
  return (G[k] = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts, true, 'centripetal'), 400, tube, 6, true));
}
// the platform: a slab with rounded corners, a tube of light along its top edge (a second inside it for o.rims 2),
// a keel under it; returns the keel's foot
function srdBase(b, s, h, o) {
  const A = b.A, X = srdA(A), r = Math.min(0.26, h * 0.4), d = r * 0.25;
  b.part(srdRBox(s, h, s, r), o.hull, 1, 1, 1, 0, -h / 2, 0);
  b.part(srdLoop(s - 2 * d, s - 2 * d, r - d, 0.024), X.neon, 1, 1, 1, 0, -r * 0.22, 0);
  if (o.rims > 1) b.part(srdLoop(s - 2.8 * r, s - 2.8 * r, r * 0.4, 0.022), A.rim, 1, 1, 1, 0, 0.01, 0);
  b.part(srdLoop(s, s, r, 0.016), A.soft, 1, 1, 1, 0, -h * 0.58, 0);
  const ks = s * (o.keel || 0.56), kh = h * 0.5;
  b.part(srdRBox(ks, kh, ks, Math.min(0.12, kh * 0.4)), o.keelMat || o.hull, 1, 1, 1, 0, -h - kh / 2 + 0.02, 0);
  b.srdBase = { s, y: 0 };
  return -h - kh + 0.02;
}
// a solar wing off the platform's side at angle a: a strut out from it, panels along it -- rows of them end to end,
// lanes of them side by side
function srdWing(b, a, out, y, len, wid, o) {
  const rows = o.rows || 1, lanes = o.lanes || 1, gap = 0.1, tilt = o.tilt != null ? o.tilt : 0.08, mat = srdSolar(o.nx || 3, o.ny || 2), at = (x, z) => rotXZ(x, z, a);
  let p = at(out + (gap + len) / 2, 0); b.box(gap + len, 0.055, 0.055, p[0], y, p[1], M.metal).rotation.y = a;
  p = at(out + 0.04, 0); b.box(0.14, 0.16, 0.2, p[0], y, p[1], M.trim).rotation.y = a;
  const pl = (len - (rows - 1) * 0.06) / rows, pw = (wid - (lanes - 1) * 0.07) / lanes;
  for (let i = 0; i < rows; i++) for (let j = 0; j < lanes; j++) {
    p = at(out + gap + pl / 2 + i * (pl + 0.06), -wid / 2 + pw / 2 + j * (pw + 0.07));
    const m = b.box(pl, 0.035, pw, p[0], y, p[1], mat); m.rotation.order = 'YXZ'; m.rotation.set(tilt, a, 0);
  }
}
// an engine's jet in the engines' blue, down from (x, y, z); it grows while a deck works
function srdJet(b, x, y, z, w, len) {
  const m = srdM();
  b.part(G.sphere, m.srdJetCore, w * 0.28, w * 0.28, w * 0.28, x, y, z);
  const p = b.part(G.beam, m.srdJet, w, len, w, x, y, z, true); p.rotation.x = Math.PI;
  b.anim.push((t) => { const k = (b.busy ? 1.3 : 0.85) + 0.12 * Math.sin(t * 17 + b.phase + x * 3 + z); p.scale.set(w * k, len * k, w * k); p.position.y = y - len * k / 2; });
}
// an engine out of the platform's side at angle a, o along that side: its housing, its bell, the glow in its mouth;
// as in his picture a disc of light and no plume, a halo round it that swells while a deck works
function srdEngine(b, a, o, y, r, half) {
  const m = srdM(), at = (x) => rotXZ(x, o, a), turn = (mesh, z) => { mesh.rotation.order = 'YXZ'; mesh.rotation.set(0, a, z); };
  let p = at(half + r * 0.6); turn(b.part(G.cyl, M.trim, r * 1.15, r * 1.3, r * 1.15, p[0], y, p[1]), -Math.PI / 2);
  p = at(half + r * 1.8); turn(b.part(G.bell, M.metal, r, r, r, p[0], y, p[1]), Math.PI / 2);
  p = at(half + r * 2.25); turn(b.part(G.cyl, m.srdJetCore, r * 0.9, 0.02, r * 0.9, p[0], y, p[1]), -Math.PI / 2);
  const halo = b.part(G.sphere, m.srdJet, r, r, r, p[0], y, p[1], true);
  b.anim.push((t) => halo.scale.setScalar(r * ((b.busy ? 1.6 : 1.15) + 0.1 * Math.sin(t * 13 + b.phase))));
}
// Biodome, Quasar Fund in his orrery: a glass dome glowing in the company's colour on a drum of ring decks, a lit
// collar at its foot, on a dark platform with a hatch and modules on its deck; four broad solar wings
SKIN.dome = (b, n) => {
  const A = b.A, X = srdA(A), m = srdM(), s = fpOf(n) + 1.3, h = 0.16 * s;
  const kb = srdBase(b, s, h, { hull: X.hullD, keelMat: X.hullD2 });
  for (let k = 0; k < 4; k++) srdWing(b, k * Math.PI / 2, s / 2, -h * 0.5, 0.62 * s, 0.34 * s, { nx: 4, ny: 2 });
  // on the deck: a hatch at the back, modules along the front edges, a small dome at the front corner
  b.cyl(0.075 * s, 0.035 * s, -0.37 * s, 0.0175 * s, 0.33 * s, X.hullD2);
  b.cyl(0.05 * s, 0.04 * s, -0.37 * s, 0.02 * s, 0.33 * s, M.dark);
  b.part(G.ringT, m.srdModule, 0.075 * s, 0.075 * s, 0.075 * s, -0.37 * s, 0.035 * s, 0.33 * s).rotation.x = Math.PI / 2;
  for (const [x, z] of [[-0.18, 0.42], [-0.3, 0.42], [0.42, -0.16], [0.42, -0.28]]) b.box(0.08 * s, 0.045 * s, 0.06 * s, x * s, 0.0225 * s, z * s, m.srdModule).rotation.y = z > 0.4 ? 0 : Math.PI / 2;
  b.part(G.hemi, m.srdModule, 0.05 * s, 0.05 * s, 0.05 * s, 0.37 * s, 0, 0.37 * s);
  // the collar where the drum meets the deck, lit ribs round it
  const cr = 0.38 * s, chh = 0.045 * s;
  b.cyl(cr, chh, 0, chh / 2, 0, X.hullD2);
  b.part(G.ringT, A.rim, cr, cr, cr, 0, chh, 0).rotation.x = Math.PI / 2;
  for (let k = 0; k < 18; k++) { const a = k / 18 * Math.PI * 2; b.box(0.02, chh * 0.5, 0.05 * s, Math.cos(a) * (cr + 0.01), chh * 0.45, -Math.sin(a) * (cr + 0.01), A.soft).rotation.y = a; }
  // the drum: a ring deck per department
  const dr = 0.31 * s, dh = 0.085 * s;
  let y = chh;
  for (let f = 0; f < n; f++) {
    b.cyl(dr, dh * 0.8, 0, y + dh * 0.4, 0, X.hullD);
    b.cyl(dr * 0.95, dh * 0.2, 0, y + dh * 0.9, 0, M.dark);
    b.part(G.ringT, A.soft, dr, dr, dr, 0, y + dh * 0.8, 0).rotation.x = Math.PI / 2;
    b.ringWins(f, dr, y + dh * 0.4, dh * 0.42, 0.26, 0.5, 0.09);
    y += dh;
  }
  // the glass dome: a drum of glass and its cap, ribs, a light and a garden inside
  const gr = 0.235 * s, gh = 0.24 * s;
  b.cyl(gr + 0.04, 0.04, 0, y + 0.02, 0, M.trim);
  b.part(G.ringT, A.rim, gr + 0.02, gr + 0.02, gr + 0.02, 0, y + 0.04, 0).rotation.x = Math.PI / 2;
  b.part(G.pole, X.glassD, gr, gh, gr, 0, y + gh / 2, 0);
  b.part(G.hemi, X.glassD, gr, 0.1 * s, gr, 0, y + gh, 0);
  b.part(G.ringT, A.soft, gr, gr, gr, 0, y + gh, 0).rotation.x = Math.PI / 2;
  for (let k = 0; k < 10; k++) { const a = k / 10 * Math.PI * 2; b.box(0.025, gh, 0.025, Math.cos(a) * gr, y + gh / 2, Math.sin(a) * gr, m.srdCap); }
  for (let k = 0; k < 5; k++) { const a = k / 5 * Math.PI * 2 + 0.3; b.part(G.sphere, M.leaf, 0.07 * s, 0.09 * s, 0.07 * s, Math.cos(a) * gr * 0.6, y + 0.06 * s, Math.sin(a) * gr * 0.6); }
  const core = b.part(G.sphere, A.soft, 0.06 * s, 0.06 * s, 0.06 * s, 0, y + gh * 0.55, 0, true);
  const yc = y + gh * 0.55;
  b.anim.push((t) => { core.position.y = yc + Math.sin(t * 1.3 + b.phase) * 0.04 * s; });
  b.cyl(0.018 * s, 0.07 * s, 0, y + gh + 0.1 * s + 0.035 * s, 0, M.metal);
  b.beacon(0, y + gh + 0.18 * s, 0, 0.06);
  b.top = y + gh + 0.18 * s + 0.15; b.bot = kb - 0.1; b.foot = s / 2 + 0.1 + 0.62 * s + 0.1;
};
// Fortress (the key stays 'pyramid', so a company saved as a Ziggurat keeps its pick), as the Bull Club in the
// operator's orrery: crenellated walls in the company's colour round a courtyard, a tower at each corner, grey
// blocks inside, all on a dark plinth; an engine burning blue out of two sides, a solar wing out of the other two.
// One deck per department: the keep, the walls, a second block, then the towers rise one by one (the back one
// highest), the keep gains a storey, the front tower last. One deck is his small Bull Club: a block, a lamp on a mast.
SKIN.pyramid = (b, n) => {
  const A = b.A, V = vfMats(A.hex), R = b.R;
  if (n === 1) return vfBlock(b, V);
  const s = fpOf(n) + 1.3, hs = s / 2, t = 0.36, Hw = 1.05, tw = 1.0, fy = 0.26, inner = hs - t;
  // the plinth under it all, dark, and the walls' foot: a band a little wider than the walls
  vfRbox(b, s + 0.3, 0.6, s + 0.3, 0, -0.3, 0, V.base, 0.1);
  vfRbox(b, s * 0.7, 0.3, s * 0.7, 0, -0.72, 0, V.base, 0.08);
  vfRbox(b, s + 0.1, fy, s + 0.1, 0, fy / 2, 0, V.body2, 0.04);
  b.box(2 * inner + 0.02, 0.05, 2 * inner + 0.02, 0, fy + 0.02, 0, V.floor);
  // the walls: a merlon every 0.24 along the outer edge, a pilaster every 0.75 down the outer face, an arrow slit
  // between two pilasters (deck 1)
  for (const [ax, az] of [[0, 1], [0, -1], [1, 0], [-1, 0]]) {
    const len = s - 2 * tw + 0.1, at = (u, v) => (ax ? [ax * v, u] : [u, az * v]), ry = ax ? ax * Math.PI / 2 : az > 0 ? 0 : Math.PI;
    const c = at(0, hs - t / 2), sz = ax ? [t, len] : [len, t];
    vfRbox(b, sz[0], Hw, sz[1], c[0], Hw / 2, c[1], V.body, 0.03);
    const m = Math.max(2, Math.round(len / 0.24)), st = len / m;
    for (let i = 0; i < m; i++) { const p = at(-len / 2 + st * (i + 0.5), hs - 0.06); b.box(ax ? 0.11 : st * 0.48, 0.1, ax ? st * 0.48 : 0.11, p[0], Hw + 0.05, p[1], V.body); }
    const q = Math.max(2, Math.round(len / 0.75)), sq = len / q;
    for (let i = 0; i <= q; i++) {
      const u = -len / 2 + sq * i, p = at(u, hs + 0.03);
      if (i > 0 && i < q) b.box(ax ? 0.06 : 0.15, Hw - fy - 0.1, ax ? 0.15 : 0.06, p[0], fy + (Hw - fy - 0.1) / 2, p[1], V.body);
      if (i < q) { const w = at(u + sq / 2, hs + 0.012); b.win(w[0], fy + (Hw - fy) * 0.55, w[1], ry, 0.07, 0.3, 1, R() < 0.25); }
    }
  }
  // the towers, back, left, right, front: each rises when its own deck comes (back highest), else it stands with the walls
  [[-1, -1, 3, 0.6], [-1, 1, 4, 0.32], [1, -1, 5, 0.32], [1, 1, 7, 0.32]].forEach(([sx, sz, f, up]) => {
    const own = f < n, H = Hw + 0.16 + (own ? up : 0), x = sx * (hs - tw / 2 + 0.05), z = sz * (hs - tw / 2 + 0.05);
    vfTower(b, V, x, z, tw, H, own ? f : 1, own ? Hw + 0.14 : H - 0.5, sx, sz);
  });
  // inside: the keep (deck 0, a storey more at deck 6) and a smaller block (deck 2), grey as his
  const kw = Math.min(1.45, s * 0.28), kh = Hw * 1.3, kx = -s * 0.19, kz = s * 0.05;
  vfHouse(b, V, kx, fy + 0.05, kz, kw, kh, 0);
  if (n > 6) vfHouse(b, V, kx, fy + 0.05 + kh, kz, kw * 0.78, kh * 0.62, 6);
  if (n > 2) vfHouse(b, V, s * 0.14, fy + 0.05, -s * 0.17, kw * 0.8, Hw * 0.85, 2);
  // engines out of the two sides the wings are not on, toward the front corner as his; a wing beside each other side
  const reach = Math.max(vfJet(b, s * 0.2, -0.25, hs + 0.1, -Math.PI / 2, s * 0.085), vfJet(b, s * 0.2, -0.25, -hs - 0.1, Math.PI / 2, s * 0.085));
  const wing = vfWing(b, hs + 0.15, -0.3, -s * 0.1, 1, 0, 0.35, s * 0.3, s * 0.55, 0.32);
  vfWing(b, -hs - 0.15, -0.3, s * 0.1, -1, 0, 0.35, s * 0.3, s * 0.55, 0.32);
  b.top = Math.max(Hw + 0.16 + (n > 3 ? 0.6 : 0), n > 6 ? fy + 0.05 + kh * 1.62 + 0.18 : 0) + 0.6; b.bot = -1.0; b.foot = Math.max(hs + wing, hs + reach);
};
// Ring station, Sigma Collective in his orrery: a stack of ring decks stepping in, a line of light round each rim,
// a neck, a saucer and a dome over them and a dish turning on top, on a light grey platform with two lines of light
// and lit ports along its sides; solar wings off three sides, an engine glowing blue out of the fourth
SKIN.orbital = (b, n) => {
  const A = b.A, m = srdM(), s = fpOf(n) + 1.3, h = 0.16 * s;
  const kb = srdBase(b, s, h, { hull: m.srdPlate, rims: 2, keelMat: m.srdSteel2 });
  for (let k = 0; k < 4; k++) for (const o of [-0.28, 0, 0.28]) {
    if (k === 0 && o < 0) continue;
    const a = k * Math.PI / 2, p = rotXZ(s / 2 + 0.006, o * s, a);
    b.box(0.02, h * 0.16, s * 0.17, p[0], -h * 0.6, p[1], m.srdLamp).rotation.y = a;
  }
  [-Math.PI / 2, Math.PI, Math.PI / 2].forEach((a) => srdWing(b, a, s / 2, -h * 0.45, 0.62 * s, 0.28 * s, { rows: 2, nx: 3, ny: 2 }));
  srdEngine(b, 0, -0.22 * s, -h * 0.5, 0.075 * s, s / 2);
  // the hub: ring decks stepping in, each a light round its rim and lit ports round its side
  const r0 = 0.36 * s, r1 = 0.25 * s, dh = 0.1 * s;
  b.cyl(r0 + 0.04 * s, 0.03 * s, 0, 0.015 * s, 0, m.srdSteel2);
  let y = 0.03 * s;
  for (let f = 0; f < n; f++) {
    const r = n > 1 ? r0 + (r1 - r0) * f / (n - 1) : r0, th = dh * 0.66;
    b.cyl(r, th, 0, y + th / 2, 0, m.srdSteel);
    b.cyl(r * 0.86, dh - th, 0, y + th + (dh - th) / 2, 0, m.srdSteel2);
    b.part(G.ring, A.rim, r + 0.01, r + 0.01, r + 0.01, 0, y + th - 0.01, 0).rotation.x = Math.PI / 2;
    b.part(G.ring, A.soft, r + 0.01, r + 0.01, r + 0.01, 0, y + 0.012, 0).rotation.x = Math.PI / 2;
    b.ringWins(f, r, y + th * 0.5, th * 0.34, 0.3, 0.5, 0.11);
    y += dh;
  }
  // the neck, the saucer and the dome
  const nr = 0.17 * s, sr = 0.29 * s, dr = 0.15 * s;
  b.cyl(nr, 0.05 * s, 0, y + 0.025 * s, 0, m.srdSteel2); y += 0.05 * s;
  b.cyl(sr, 0.065 * s, 0, y + 0.0325 * s, 0, m.srdSteel);
  b.part(G.ring, A.rim, sr + 0.01, sr + 0.01, sr + 0.01, 0, y + 0.055 * s, 0).rotation.x = Math.PI / 2;
  y += 0.065 * s;
  b.cyl(dr, 0.06 * s, 0, y + 0.03 * s, 0, m.srdSteel2); y += 0.06 * s;
  b.part(G.hemi, m.srdCap, dr, 0.11 * s, dr, 0, y, 0);
  const yt = y + 0.11 * s;
  // the dish on the dome, turning
  const dish = new THREE.Group(); dish.position.set(0, yt, 0); dish.userData.dyn = true; b.g.add(dish);
  const stalk = new THREE.Mesh(G.cyl, M.metal); stalk.scale.set(0.012 * s, 0.06 * s, 0.012 * s); stalk.position.y = 0.03 * s; dish.add(stalk);
  const bowl = new THREE.Mesh(G.hemi, m.srdCap); bowl.scale.set(0.075 * s, 0.03 * s, 0.075 * s); bowl.rotation.set(Math.PI - 0.5, 0, 0); bowl.position.set(0, 0.07 * s, 0); dish.add(bowl);
  const horn = new THREE.Mesh(G.cyl, M.metal); horn.scale.set(0.008 * s, 0.05 * s, 0.008 * s); horn.rotation.x = -0.5; horn.position.set(0, 0.09 * s, 0.012 * s); dish.add(horn);
  bakeGroup(dish);
  b.anim.push((t) => { dish.rotation.y = t * 0.4 + b.phase; });
  b.beacon(0.12 * s, yt - 0.04 * s, 0, 0.05);
  b.box(0.11 * s, 0.08 * s, 0.11 * s, 0.33 * s, 0.04 * s, 0.33 * s, m.srdModule).rotation.y = Math.PI / 4;
  b.top = yt + 0.12 * s; b.bot = kb - 0.1; b.foot = s / 2 + 0.1 + 0.6 * s + 0.1;
};
// Laser station (key 'rocket', so a company saved with the old Starship keeps its pick), as the operator's picture
// draws it: an armoured block in the company's colour under a round lid, a laser cannon out of one side firing a
// beam of its colour, pale solar wings on the other three (his has three, the cannon takes the fourth arm); under
// the block a dark drum, one ribbed ring per deck, its windows lit while the deck's department works.
// The materials both of these stations add, one set per colour, kept in AM beside amat's own so that release()
// keeps them for the next station as it keeps those.
function lsMats(A) {
  const k = 'ls' + A.hex; if (AM[k]) return AM[k];
  const c = A.c, grey = new THREE.Color(0xc8ccd4);
  return (AM[k] = {
    body: std({ color: c.clone().lerp(grey, 0.15), roughness: 0.42, metalness: 0.12, emissive: c, emissiveIntensity: 0.07 }),
    plate: std({ color: c.clone().lerp(grey, 0.12).multiplyScalar(0.34), roughness: 0.55, metalness: 0.25 }),
    drum: std({ color: 0x25272d, roughness: 0.5, metalness: 0.55 }),
    rib: std({ color: 0x3b3e46, roughness: 0.42, metalness: 0.6 }),
    wing: std({ color: new THREE.Color(0xe6e4ee).lerp(c, 0.08), map: lsCellTex(), roughness: 0.42, metalness: 0.3 })
  });
}
// his wings' cells: pale lavender-grey squares in a slightly darker grid, a light frame round the panel
function lsCellTex() {
  return TX.lsCells || (TX.lsCells = ctex(512, 192, (g, W, H) => {
    g.fillStyle = '#a3a0b4'; g.fillRect(0, 0, W, H);
    const nx = 14, ny = 4, p = 6, cw = (W - 2 * p) / nx, ch = (H - 2 * p) / ny;
    for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++) {
      const x = p + i * cw, y = p + j * ch, gr = g.createLinearGradient(x, y, x + cw, y + ch);
      gr.addColorStop(0, '#e2dfea'); gr.addColorStop(1, '#c6c3d3'); g.fillStyle = gr; g.fillRect(x + 1, y + 1, cw - 2, ch - 2);
    }
    g.strokeStyle = '#f4f2fa'; g.lineWidth = 4; g.strokeRect(2, 2, W - 4, H - 4);
  }));
}
// a part turned to point along an arm: a yaw about the station's axis after its own tilt (rx) and roll (rz)
function lsArm(m, a, d, rx, rz) {
  const p = rotXZ(d, 0, a); m.position.x = p[0]; m.position.z = p[1];
  m.rotation.order = 'YXZ'; m.rotation.set(rx || 0, a, rz || 0); return m;
}
SKIN.rocket = (b, n) => {
  const A = b.A, L = lsMats(A), w = 1.6 + Math.min(n, 8) * 0.06, hc = w * 0.95, half = w / 2;
  // the armoured block: rounded, a dark plate framed on each side, a round lid on a seat
  b.part(G.lsCube || (G.lsCube = new RoundedBoxGeometry(1, 1, 1, 3, 0.12)), L.body, w, hc, w, 0, hc / 2, 0);
  for (let k = 0; k < 4; k++) {
    const a = k * Math.PI / 2, on = (m, x, y, out) => { const p = rotXZ(x, half + out, a); m.position.set(p[0], y, p[1]); m.rotation.y = a; return m; };
    on(b.box(w * 0.62, hc * 0.58, 0.02, 0, 0, 0, L.plate), 0, hc / 2, 0.006);
    for (const s of [1, -1]) {
      on(b.box(w * 0.72, 0.08, 0.06, 0, 0, 0, L.body), 0, hc / 2 + s * hc * 0.32, 0.025);
      on(b.box(0.08, hc * 0.64, 0.06, 0, 0, 0, L.body), s * w * 0.34, hc / 2, 0.025);
    }
  }
  b.cyl(w * 0.37, 0.08, 0, hc + 0.04, 0, L.rib);
  b.cyl(w * 0.42, w * 0.24, 0, hc + 0.08 + w * 0.12, 0, L.body);
  // the drum of decks under it
  const rd = w * 0.4, dh = 0.4;
  b.cyl(rd + 0.1, 0.08, 0, -0.04, 0, L.rib);
  let y = -0.08;
  for (let f = 0; f < n; f++) {
    b.cyl(rd, dh - 0.07, 0, y - (dh - 0.07) / 2, 0, L.drum);
    b.ringWins(f, rd, y - (dh - 0.07) / 2, 0.1, 0.34, 0.35, 0.09);
    b.cyl(rd + 0.05, 0.07, 0, y - dh + 0.035, 0, L.rib);
    y -= dh;
  }
  b.part(G.cone, L.drum, rd * 0.72, 0.32, rd * 0.72, 0, y - 0.16, 0).rotation.x = Math.PI;
  b.beacon(0, y - 0.4, 0, 0.06);
  // the cannon, out of the +z side: a dark ribbed housing, a collar in the station's colour, a barrel, and the beam
  // with a light at either end; a bolt runs down it, and it burns brighter while a deck works
  const ly = hc * 0.36, z0 = half, fire = (geom, mat, r, len, z, dyn) => { const m = b.part(geom, mat, r, len, r, 0, ly, z, dyn); m.rotation.x = Math.PI / 2; return m; };
  fire(G.cyl, L.drum, w * 0.22, w * 0.6, z0 + w * 0.3);
  for (let k = 0; k < 4; k++) fire(G.cyl, L.rib, w * 0.235, 0.05, z0 + w * (0.08 + k * 0.13));
  fire(G.cyl, L.body, w * 0.17, w * 0.14, z0 + w * 0.67);
  fire(G.cyl, L.body, w * 0.055, w * 0.22, z0 + w * 0.85);
  const zb = z0 + w * 0.96, bl = w * 1.6, sheathMat = A.beam.clone();
  b.part(G.ringT, A.rim, w * 0.07, w * 0.07, w * 0.07, 0, ly, zb);
  const core = fire(G.cyl, A.glow, 0.03, bl, zb + bl / 2, true), sheath = fire(G.cyl, sheathMat, 0.075, bl, zb + bl / 2, true);
  const bolt = b.part(G.sphere, A.glow, 0.07, 0.07, 0.3, 0, ly, zb, true);
  const tip = glowSprite(A.c, 0.9, 0.7);
  tip.position.set(0, ly, zb + bl); b.g.add(tip);
  b.anim.push((t) => {
    const k = (b.busy ? 1.35 : 1) * (1 + 0.14 * Math.sin(t * 7.3 + b.phase));
    core.scale.set(0.03 * k, bl, 0.03 * k); sheath.scale.set(0.075 * k, bl, 0.075 * k);
    sheathMat.opacity = (b.busy ? 0.5 : 0.32) + 0.08 * Math.sin(t * 5.1 + b.phase);
    bolt.position.z = zb + ((t * (b.busy ? 1.6 : 0.9) + b.phase) % 1) * bl;
    tip.material.opacity = 0.7 + 0.3 * Math.sin(t * 11 + b.phase);
  });
  // the wings on the other three arms, on struts from the block's middle, each turned a little towards the front
  const wy = hc * 0.52, pl = w * 2.0, pw = w * 0.8, w0 = half + 0.3;
  for (const [a, tilt] of [[0, 0.35], [Math.PI / 2, 0.35], [Math.PI, -0.35]]) {
    lsArm(b.box(0.36, 0.08, 0.08, 0, wy, 0, M.metal), a, half + 0.15);
    lsArm(b.box(0.14, 0.14, 0.18, 0, wy, 0, L.rib), a, w0 - 0.04);
    lsArm(b.box(pl, 0.05, pw, 0, wy, 0, L.wing), a, w0 + pl / 2, tilt);
    lsArm(b.box(pl + 0.04, 0.07, 0.05, 0, wy, 0, M.metal), a, w0 + pl / 2, tilt);
  }
  b.top = hc + w * 0.32 + 0.3; b.bot = y - 0.5; b.foot = Math.max(w0 + pl, zb + bl);
};
// Data stack: the operator's picture's "Night Owl Trading" -- dark server blocks of different heights, a block per
// department, each a pile of plates with a strip of light along every plate that the department's work lights; on a
// rounded base ringed in the company's colour, two engines glowing blue at its stern, a dark solar wing either side.
function stMats(A) {
  const k = 'st' + A.hex; if (AM[k]) return AM[k];
  const c = A.c;
  return (AM[k] = {
    side: std({ color: 0x364357, roughness: 0.5, metalness: 0.25 }),
    top: std({ color: 0x45536a, roughness: 0.45, metalness: 0.25 }),
    dark: std({ color: 0x0b0f15, roughness: 0.6, metalness: 0.4 }),
    base: std({ color: new THREE.Color(0x262f3c).lerp(c, 0.05), roughness: 0.5, metalness: 0.25 }),
    wing: std({ color: 0xffffff, map: stPanelTex(), roughness: 0.38, metalness: 0.35 }),
    plume: new THREE.MeshBasicMaterial({ color: new THREE.Color(0.06, 0.28, 1).multiplyScalar(1.3), transparent: true, opacity: 0.1, blending: THREE.AdditiveBlending, depthWrite: false }),
    nozzle: new THREE.MeshBasicMaterial({ color: new THREE.Color(0.25, 0.5, 1).multiplyScalar(1.5) })
  });
}
// his dark wings: slate cells in a lighter frame
function stPanelTex() {
  return TX.stPanel || (TX.stPanel = ctex(256, 192, (g, W, H) => {
    g.fillStyle = '#4b5567'; g.fillRect(0, 0, W, H);
    const nx = 4, ny = 3, p = 5, cw = (W - 2 * p) / nx, ch = (H - 2 * p) / ny;
    for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++) {
      const x = p + i * cw, y = p + j * ch, gr = g.createLinearGradient(x, y, x + cw, y + ch);
      gr.addColorStop(0, '#323d50'); gr.addColorStop(1, '#1d2532'); g.fillStyle = gr; g.fillRect(x + 2, y + 2, cw - 4, ch - 4);
      g.strokeStyle = 'rgba(140,160,190,.22)'; g.lineWidth = 1;
      for (let q = 1; q < 3; q++) { g.beginPath(); g.moveTo(x + 2 + q * (cw - 4) / 3, y + 2); g.lineTo(x + 2 + q * (cw - 4) / 3, y + ch - 2); g.stroke(); }
    }
  }));
}
// a rounded slab of a given size (its corners keep their radius at any size), and the line of light round its top
function stSlab(w, h, d) {
  const k = 'stSlab' + [w, h, d].map((v) => v.toFixed(2)).join('x');
  return G[k] || (G[k] = new RoundedBoxGeometry(w, h, d, 3, Math.min(0.15, h * 0.45)));
}
function stRim(w, d) {
  const k = 'stRim' + w.toFixed(2) + 'x' + d.toFixed(2); if (G[k]) return G[k];
  const r = 0.15, hw = w / 2 + 0.01, hd = d / 2 + 0.01, pts = [];
  const corner = (cx, cz, a0) => { for (let i = 0; i <= 8; i++) { const a = a0 + i / 8 * Math.PI / 2; pts.push(new THREE.Vector3(cx + Math.cos(a) * r, 0, cz + Math.sin(a) * r)); } };
  corner(hw - r, hd - r, 0); corner(-hw + r, hd - r, Math.PI / 2); corner(-hw + r, -hd + r, Math.PI); corner(hw - r, -hd + r, Math.PI * 1.5);
  return (G[k] = new THREE.TubeGeometry(new THREE.CatmullRomCurve3(pts, true, 'centripetal'), 200, 0.035, 6, true));
}
SKIN.stack = (b, n) => {
  const A = b.A, S = stMats(A), R = b.R, m = Math.max(1, Math.min(n, 8));
  const cols = m === 1 ? 1 : m <= 4 ? 2 : m <= 6 ? 3 : 4, rows = m <= 2 ? 1 : 2, cell = 1.08, s = 0.98;
  const bw = cols * cell + 0.72, bd = rows * cell + 0.72, bh = 0.46;
  // the base: a rounded slab with its line of light, a skirt and a keel under it
  b.part(stSlab(bw, bh, bd), S.base, 1, 1, 1, 0, -bh / 2, 0);
  b.part(stRim(bw, bd), A.soft, 1, 1, 1, 0, -0.12, 0);
  b.part(stSlab(bw - 0.34, 0.3, bd - 0.34), S.dark, 1, 1, 1, 0, -bh - 0.13, 0);
  b.box(bw * 0.46, 0.22, bd * 0.46, 0, -bh - 0.38, 0, S.dark);
  // the blocks, row by row; a cell no department fills holds a low cooling unit
  let hmax = 0.4;
  for (let j = 0, f = 0; j < rows; j++) for (let i = 0; i < cols; i++, f++) {
    const x = (i - (cols - 1) / 2) * cell, z = (j - (rows - 1) / 2) * cell;
    if (f >= m) { b.box(0.62, 0.34, 0.62, x, 0.17, z, S.side); b.cyl(0.2, 0.05, x, 0.365, z, M.metal); b.cyl(0.16, 0.03, x, 0.395, z, S.dark); continue; }
    const hb = 0.8 + R() * 0.38, np = Math.max(4, Math.round(hb / 0.18)), ph = hb / np;
    hmax = Math.max(hmax, hb);
    b.box(s - 0.1, hb, s - 0.1, x, hb / 2, z, S.dark);
    for (let k = 0; k < np; k++) {
      const y = k * ph + ph / 2;
      b.part(G.stPlate || (G.stPlate = new RoundedBoxGeometry(1, 1, 1, 2, 0.06)), S.side, s, ph - 0.035, s, x, y, z);
      for (const [dx, dz, ry] of [[0, 1, 0], [0, -1, Math.PI], [1, 0, Math.PI / 2], [-1, 0, -Math.PI / 2]]) b.win(x + dx * (s / 2 + 0.006), y, z + dz * (s / 2 + 0.006), ry, s * 0.56, 0.026, f, R() < 0.2);
    }
    b.box(s * 0.56, 0.05, s * 0.42, x - s * 0.1, hb + 0.025, z + s * 0.1, S.top);
    b.part(G.sphere, A.glow, 0.025, 0.025, 0.025, x + s * 0.38, hb + 0.03, z - s * 0.38);
  }
  // two engines at the stern (+x), silver, their plumes blue whatever the station's colour; longer while it works
  const ey = -bh * 0.5, ex = bw / 2, fl = [];
  for (const ez of [-0.42, 0.42]) {
    const aft = (geom, mat, r, len, x, rz, dyn) => { const p = b.part(geom, mat, r, len, r, x, ey, ez, dyn); p.rotation.z = rz; return p; };
    aft(G.cyl, S.dark, 0.22, 0.06, ex + 0.03, Math.PI / 2);
    aft(G.cyl, M.metal, 0.19, 0.3, ex + 0.2, Math.PI / 2);
    aft(G.bell, M.trim, 0.21, 0.22, ex + 0.45, Math.PI / 2);
    b.part(G.sphere, S.nozzle, 0.03, 0.15, 0.15, ex + 0.55, ey, ez, true);
    // the plume: a faint cone for its shape, a haze of blue lights fading out along it for its glow
    const haze = [[0.22, 0.7, 0.5], [0.5, 0.6, 0.3], [0.82, 0.45, 0.16]].map(([d, sz, op]) => { const h = glowSprite(S.plume.color, op, sz); h.position.set(ex + 0.55 + d, ey, ez); h.userData.d = d; h.userData.op = op; b.g.add(h); return h; });
    fl.push([aft(G.beam, S.plume, 0.5, 0.75, ex + 0.9, -Math.PI / 2, true), haze]);
  }
  b.anim.push((t) => fl.forEach(([p, haze], i) => {
    const k = (b.busy ? 1.35 : 0.9) + 0.1 * Math.sin(t * 17 + i * 2 + b.phase);
    p.scale.set(0.5, 0.75 * k, 0.5); p.position.x = ex + 0.56 + 0.375 * k;
    haze.forEach((h) => { h.position.x = ex + 0.55 + h.userData.d * k; h.material.opacity = h.userData.op * (0.85 + 0.15 * k); });
  }));
  // the wings: two dark panels on a strut out of either side, drooping a little
  const wy = -bh * 0.45;
  for (const sz of [1, -1]) {
    b.box(0.09, 0.09, 0.3, 0, wy, sz * (bd / 2 + 0.15), M.metal);
    for (let k = 0; k < 2; k++) b.box(0.85, 0.04, 0.62, 0, wy - k * 0.065, sz * (bd / 2 + 0.62 + k * 0.67), S.wing).rotation.x = sz * 0.2;
  }
  // drawn in a server block's own units, then made as large as the other stations, as his are on the map
  const K = 1.3;
  b.g.scale.setScalar(K);
  b.top = (hmax + 0.3) * K; b.bot = (-bh - 0.7) * K; b.foot = Math.max(ex + 1.2, bd / 2 + 1.6, bw / 2 + 0.3) * K;
};
// Vault: an armoured block of decks with its round door, two solar wings, a dish, an engine pod underneath
// -- as the Giga Fund in the operator's orrery: the block in the company's colour narrowing upward, a band of
// plates per deck whose seams are its windows, sitting in a thick rounded collar; a pale lid with a lamp on a mast.
SKIN.vault = (b, n) => {
  const A = b.A, V = vfMats(A.hex), R = b.R, W = fpOf(n) * 0.8 + 0.3, h0 = 0.95, hk = n <= 3 ? 0.62 : 0.52, cw = W * 1.45, k = 0.1;
  // the collar, thick and rounded; the drum under it; the keel
  vfRbox(b, cw, 0.66, cw, 0, -0.14, 0, V.body, 0.31);
  vfRbox(b, W * 0.96, 0.6, W * 0.96, 0, -0.6, 0, V.body2, 0.08);
  vfRbox(b, W * 0.5, 0.32, W * 0.5, 0, -1.04, 0, V.base, 0.06);
  // the block: one body narrowing upward, a seam round it between two decks, the seams between its plates its windows
  const H = h0 + (n - 1) * hk, y0 = 0.12, at = (yy) => W * (1 - k * (yy - y0) / H);
  const m = W < 2.4 ? 3 : 4;
  vfTaper(b, W, H, W, 0, y0 + H / 2, 0, vfPlated(A.hex, m), 0.12, k);
  let y = y0;
  for (let f = 0; f < n; f++) {
    const h = f ? hk : h0, yc = y + h / 2, wc = at(yc);
    if (f) b.box(at(y) + 0.02, 0.035, at(y) + 0.02, 0, y, 0, V.base);
    for (const [ax, az] of [[0, 1], [0, -1], [1, 0], [-1, 0]]) {
      const ry = ax ? ax * Math.PI / 2 : az > 0 ? 0 : Math.PI;
      for (let i = 1; i <= m; i++) {
        const u = -wc / 2 + wc * i / (m + 1);
        if (f === 0 && az > 0 && Math.abs(u + W * 0.18) < 0.45) continue;   // where the door is
        b.win(ax ? ax * (wc / 2 + 0.016) : u, yc, ax ? u : az * (wc / 2 + 0.016), ry, 0.1, h * 0.7, f, R() < 0.15);
      }
    }
    y += h;
  }
  // the round door in the first deck, a wheel on it and a lamp beside
  const dx = -W * 0.18, dy = y0 + h0 * 0.48, dz = at(dy) / 2 + 0.01;
  b.part(G.cyl, V.dark, 0.3, 0.06, 0.3, dx, dy, dz + 0.01).rotation.x = Math.PI / 2;
  b.part(vfTorusGeo(), V.cap, 0.33, 0.33, 0.33, dx, dy, dz + 0.04);
  for (const r of [0, Math.PI / 2]) b.box(0.4, 0.035, 0.03, dx, dy, dz + 0.05, M.metal).rotation.z = r + Math.PI / 4;
  b.part(G.sphere, A.glow, 0.04, 0.04, 0.04, dx + 0.42, dy + 0.18, dz + 0.02);
  // the lid, its pale plate, the mast and its lamp
  const Wt = at(y);
  vfRbox(b, Wt * 0.96, 0.14, Wt * 0.96, 0, y + 0.04, 0, V.body, 0.06);
  for (const [ax, az] of [[0, 1], [0, -1], [1, 0], [-1, 0]]) b.box(ax ? 0.09 : Wt * 0.8, 0.08, ax ? Wt * 0.8 : 0.09, ax * Wt * 0.36, y + 0.14, az * Wt * 0.36, V.body);
  b.box(Wt * 0.68, 0.04, Wt * 0.68, 0, y + 0.12, 0, V.cap);
  vfRbox(b, 0.3, 0.12, 0.3, 0, y + 0.18, 0, V.base, 0.04);
  b.cyl(0.035, 0.3, 0, y + 0.37, 0, M.metal);
  vfLamp(b, 0, y + 0.58, 0, 0.17);
  // the wings, the engine pod under the collar's front corner, a sensor on the far side
  const wing = vfWing(b, 0, -0.06, cw / 2, 0, 1, 0.4, W * 1.25, W * 0.66, 0.1);
  vfWing(b, 0, -0.06, -cw / 2, 0, -1, 0.4, W * 1.25, W * 0.66, 0.1);
  const reach = vfJet(b, W * 0.62, -0.52, W * 0.3, 0, 0.25, 2.2);
  b.box(0.22, 0.06, 0.06, -cw / 2 - 0.08, -0.1, W * 0.3, M.metal);
  b.part(G.hemi, M.vfSilver, 0.2, 0.09, 0.2, -cw / 2 - 0.2, -0.1, W * 0.3).rotation.z = Math.PI / 2;
  b.top = y + 1.05; b.bot = -1.3; b.foot = Math.max(cw / 2 + wing, W * 0.62 + reach);
};
/* Vault and Fortress share their parts: a body in the company's own colour, as saturated as the operator's
 * pictures have it (A.hull is slate with a touch of it), on a dark plinth; blue-grey solar wings; engines that burn
 * white-blue whatever the colour. The materials live in M so release() never disposes them. */
function vfMats(hex) {
  const key = 'vf' + hex; if (M[key]) return M[key];
  const hsl = {}; new THREE.Color(hex).getHSL(hsl, THREE.SRGBColorSpace);
  const tone = (s, l) => new THREE.Color().setHSL(hsl.h, s, l, THREE.SRGBColorSpace), st = (o) => new THREE.MeshStandardMaterial(o);
  vfShared();
  M[key] = {
    body: st({ color: tone(0.44, 0.5), emissive: tone(0.6, 0.3), emissiveIntensity: 0.14, roughness: 0.5, metalness: 0.15 }),
    body2: st({ color: tone(0.42, 0.44), emissive: tone(0.6, 0.3), emissiveIntensity: 0.14, roughness: 0.52, metalness: 0.15 }),
    cap: st({ color: tone(0.22, 0.56), roughness: 0.5, metalness: 0.1 }),
    floor: st({ color: tone(0.3, 0.42), map: vfFloorTex(), roughness: 0.85, metalness: 0.05 }),
    base: M.vfBase, dark: M.vfDark, grey: M.vfGrey, grey2: M.vfGrey2
  };
  return M[key];
}
function vfShared() {
  if (M.vfBase) return;
  const st = (o) => new THREE.MeshStandardMaterial(o);
  M.vfBase = st({ color: 0x2c2e36, roughness: 0.55, metalness: 0.35 });
  M.vfDark = st({ color: 0x0a0c11, roughness: 0.45, metalness: 0.4 });
  M.vfGrey = st({ color: 0x48474e, roughness: 0.62, metalness: 0.2 });
  M.vfGrey2 = st({ color: 0x918e98, roughness: 0.55, metalness: 0.15 });
  M.vfSilver = st({ color: 0xa9b1bc, roughness: 0.36, metalness: 0.45 });
  M.vfSolar = st({ map: vfSolarTex(), roughness: 0.38, metalness: 0.3 });
  M.vfFrame = st({ color: 0x7d8594, roughness: 0.45, metalness: 0.4 });
  M.vfCore = new THREE.MeshBasicMaterial({ color: new THREE.Color(0.3, 0.78, 1).multiplyScalar(1.35) });
  M.vfPlume = new THREE.MeshBasicMaterial({ map: vfPlumeTex(), color: new THREE.Color(0x5ac8ff).multiplyScalar(1.5), transparent: true, opacity: 0.8, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
}
const VFG = new Map();
function vfRgeo(w, h, d, r) {
  const k = [w, h, d, r].map((v) => v.toFixed(3)).join(',');
  let g = VFG.get(k);
  if (!g) { g = new RoundedBoxGeometry(w, h, d, r > 0.08 ? 3 : 2, Math.max(0.005, Math.min(r, w / 2 - 0.005, h / 2 - 0.005, d / 2 - 0.005))); VFG.set(k, g); }
  return g;
}
function vfRbox(b, w, h, d, x, y, z, mat, r) { return b.part(vfRgeo(w, h, d, r), mat, 1, 1, 1, x, y, z); }
// the same, its top k narrower than its foot: the Vault's block, a frustum as in his picture
function vfTaper(b, w, h, d, x, y, z, mat, r, k) {
  const key = ['taper', w, h, d, r, k].map((v) => (typeof v === 'number' ? v.toFixed(3) : v)).join(',');
  let g = VFG.get(key);
  if (!g) {
    g = vfRgeo(w, h, d, r).clone(); const p = g.attributes.position;
    for (let i = 0; i < p.count; i++) { const s = 1 - k * (p.getY(i) / h + 0.5); p.setX(i, p.getX(i) * s); p.setZ(i, p.getZ(i) * s); }
    VFG.set(key, g);
  }
  return b.part(g, mat, 1, 1, 1, x, y, z);
}
function vfTorusGeo() { let g = VFG.get('torus'); if (!g) { g = new THREE.TorusGeometry(1, 0.11, 10, 48); VFG.set('torus', g); } return g; }
// solar cells: blue-grey in a thin pale grid, ten by five along the wing
function vfSolarTex() {
  return TX.vfSolar || (TX.vfSolar = (() => {
    const c = document.createElement('canvas'); c.width = 512; c.height = 256; const g = c.getContext('2d');
    g.fillStyle = '#b3b9c8'; g.fillRect(0, 0, 512, 256);
    for (let i = 0; i < 10; i++) for (let j = 0; j < 5; j++) {
      const x = 6 + i * 50, y = 6 + j * 49, gr = g.createLinearGradient(x, y, x + 50, y + 49);
      gr.addColorStop(0, '#7c839c'); gr.addColorStop(1, '#5d647c'); g.fillStyle = gr; g.fillRect(x + 1.5, y + 1.5, 47, 46);
    }
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
  })());
}
// The Vault's block in armour: its colour over m + 1 plates a face, the dark seams between them where its windows
// are, each plate lit a little down its left edge and shaded down its right, as his picture's are
function vfPlated(hex, m) {
  const key = 'vfPlated' + m + hex; if (M[key]) return M[key];
  const tex = TX['vfPlates' + m] || (TX['vfPlates' + m] = (() => {
    const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d'), s = 256 / (m + 1);
    for (let i = 0; i <= m; i++) {
      const x0 = i * s, gr = g.createLinearGradient(x0, 0, x0 + s, 0);
      gr.addColorStop(0, '#ffffff'); gr.addColorStop(0.15, '#f0f0f0'); gr.addColorStop(0.85, '#dcdcdc'); gr.addColorStop(1, '#a8a8a8');
      g.fillStyle = gr; g.fillRect(x0, 0, s, 256);
      if (i) { g.fillStyle = '#3c3c3c'; g.fillRect(x0 - 5, 0, 10, 256); }
    }
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
  })());
  const V = vfMats(hex);
  M[key] = new THREE.MeshStandardMaterial({ color: V.body.color, emissive: V.body.emissive, emissiveIntensity: V.body.emissiveIntensity, map: tex, roughness: 0.52, metalness: 0.15 });
  return M[key];
}
// a courtyard's tiles: a grey grid the floor's colour multiplies
function vfFloorTex() {
  return TX.vfFloor || (TX.vfFloor = (() => {
    const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d'), R = rng(5);
    g.fillStyle = '#b8b8b8'; g.fillRect(0, 0, 256, 256);
    for (let i = 0; i < 8; i++) for (let j = 0; j < 8; j++) { const v = 150 + Math.floor(R() * 40); g.fillStyle = 'rgb(' + v + ',' + v + ',' + v + ')'; g.fillRect(i * 32 + 2, j * 32 + 2, 28, 28); }
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
  })());
}
function vfPlumeTex() {
  return TX.vfPlume || (TX.vfPlume = (() => {
    const c = document.createElement('canvas'); c.width = 16; c.height = 128; const g = c.getContext('2d'), gr = g.createLinearGradient(0, 0, 0, 128);
    gr.addColorStop(0, 'rgba(230,252,255,1)'); gr.addColorStop(0.3, 'rgba(70,200,255,.6)'); gr.addColorStop(1, 'rgba(20,120,255,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 16, 128);
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
  })());
}
// a lamp on a mast: the station's colour, pulsing with its halo
function vfLamp(b, x, y, z, r) {
  const i = b.beacons.length; b.beacon(x, y, z, r);
  const halo = glowSprite(b.A.c, 0.8, r * 12); halo.position.set(x, y, z); b.g.add(halo);
  b.anim.push((t) => { halo.material.opacity = 0.5 + 0.5 * Math.max(0, Math.sin(t * 2.6 + b.phase + i)); });
}
// An engine on its side: a ribbed pod, a bell, a white-hot nozzle and a blue plume out of it, longer while a deck
// works. (x, y, z) is where the pod meets the hull, ry the way it points (0: +x), r its radius, lk the plume's
// length in radii. Returns its reach.
function vfJet(b, x, y, z, ry, r, lk = 2.8) {
  const g = new THREE.Group(), L = r * 2.4, len = r * lk, nz = L + r * 0.62; g.position.set(x, y, z); g.rotation.y = ry; b.g.add(g);
  const put = (geom, mat, sx, sy, sz, px, rz, dyn) => { const m = new THREE.Mesh(geom, mat); m.scale.set(sx, sy, sz); m.position.set(px, 0, 0); m.rotation.z = rz; if (dyn) m.userData.dyn = true; g.add(m); return m; };
  put(G.cyl, M.vfSilver, r, L, r, L / 2, Math.PI / 2);
  for (const k of [0.3, 0.52, 0.74]) put(G.cyl, M.vfBase, r * 1.07, r * 0.16, r * 1.07, L * k, Math.PI / 2);
  put(G.bell, M.vfSilver, r * 0.98, r * 0.66, r * 0.98, L + r * 0.3, Math.PI / 2);
  put(G.sphere, M.vfCore, r * 0.06, r * 0.86, r * 0.86, nz - r * 0.04, 0);
  const p = put(vfPlumeGeo(), M.vfPlume, r * 0.9, len, r * 0.9, nz + len / 2, Math.PI / 2, true);
  const s = glowSprite(0x2f9cff, 0.35, r * 4.5); s.position.set(nz + r * 0.5, 0, 0); g.add(s);
  b.anim.push((t) => { const k = (b.busy ? 1.4 : 0.92) + 0.1 * Math.sin(t * 17 + b.phase + x + z); p.scale.y = len * k; p.position.x = nz + len * k / 2; });
  return nz + len * 1.2;
}
function vfPlumeGeo() { let g = VFG.get('plume'); if (!g) { g = new THREE.CylinderGeometry(1, 0.55, 1, 24, 1, true); VFG.set('plume', g); } return g; }
// a solar wing on a boom out of the hull at (x0, y, z0) along (ax, az): one panel in a pale frame, `out` long away
// from the hull and `side` along it, tilted about its long side. Returns how far it reaches.
function vfWing(b, x0, y, z0, ax, az, boom, out, side, tilt) {
  b.box(ax ? boom : 0.08, 0.08, ax ? 0.08 : boom, x0 + ax * boom / 2, y, z0 + az * boom / 2, M.metal);
  const c = boom + out / 2, L = Math.max(out, side), Wd = Math.min(out, side), alongX = (out >= side) === !!ax;
  [[M.vfFrame, L + 0.1, 0.04, Wd + 0.1, -0.012], [M.vfSolar, L, 0.05, Wd, 0]].forEach(([mat, l, h, w, dy]) => {
    const m = b.part(G.box, mat, l, h, w, x0 + ax * c, y + dy, z0 + az * c); m.rotation.order = 'YXZ'; m.rotation.set(tilt * (ax || az), alongX ? 0 : Math.PI / 2, 0);
  });
  return boom + out;
}
// a tower at a corner of the walls: its body, a parapet round a sunken roof with a merlon each side, slits in its
// two outer faces (deck f)
function vfTower(b, V, x, z, tw, H, f, wy, sx, sz) {
  vfRbox(b, tw, H, tw, x, H / 2, z, V.body, 0.04);
  b.box(tw - 0.2, 0.05, tw - 0.2, x, H + 0.03, z, V.floor);
  for (const [ax, az] of [[0, 1], [0, -1], [1, 0], [-1, 0]]) {
    b.box(ax ? 0.1 : tw, 0.2, ax ? tw : 0.1, x + ax * (tw / 2 - 0.05), H + 0.1, z + az * (tw / 2 - 0.05), V.body);
    for (const u of [-0.24, 0.24]) b.box(ax ? 0.1 : 0.14, 0.13, ax ? 0.14 : 0.1, x + (ax ? ax * (tw / 2 - 0.05) : u * tw), H + 0.26, z + (az ? az * (tw / 2 - 0.05) : u * tw), V.body);
  }
  for (const u of [-0.2, 0.2]) {
    b.win(x + sx * (tw / 2 + 0.012), wy, z + u * tw, sx * Math.PI / 2, 0.07, 0.28, f, b.R() < 0.3);
    b.win(x + u * tw, wy, z + sz * (tw / 2 + 0.012), sz > 0 ? 0 : Math.PI, 0.07, 0.28, f, b.R() < 0.3);
  }
}
// a grey block in the courtyard: its body, a pale lid with a lip, two windows a face (deck f)
function vfHouse(b, V, x, y0, z, w, h, f) {
  vfRbox(b, w, h, w, x, y0 + h / 2, z, V.grey, 0.05);
  vfRbox(b, w + 0.06, 0.1, w + 0.06, x, y0 + h + 0.03, z, V.grey2, 0.03);
  vfRbox(b, w * 0.8, 0.08, w * 0.8, x, y0 + h + 0.1, z, V.grey2, 0.03);
  for (const [ax, az] of [[0, 1], [0, -1], [1, 0], [-1, 0]]) for (const u of [-0.22, 0.22]) {
    const ry = ax ? ax * Math.PI / 2 : az > 0 ? 0 : Math.PI;
    b.win(x + (ax ? ax * (w / 2 + 0.012) : u * w), y0 + h * 0.55, z + (az ? az * (w / 2 + 0.012) : u * w), ry, 0.08, h * 0.42, f, b.R() < 0.3);
  }
}
// one deck of the Fortress: the small Bull Club, a block in the company's colour on a dark plinth, a dark hatch in
// its roof with a lamp on a mast, a solar wing out of two sides
function vfBlock(b, V) {
  const s = 2.1, h = 1.35;
  vfRbox(b, s + 0.34, 0.42, s + 0.34, 0, -0.21, 0, V.base, 0.1);
  vfRbox(b, s * 0.6, 0.3, s * 0.6, 0, -0.56, 0, V.base, 0.06);
  vfRbox(b, s, h, s, 0, h / 2, 0, V.body, 0.16);
  b.box(s * 0.38, 0.03, s * 0.38, 0, h + 0.005, 0, V.base);
  vfRbox(b, 0.34, 0.16, 0.34, 0, h + 0.08, 0, V.dark, 0.04);
  b.cyl(0.035, 0.36, 0, h + 0.34, 0, M.metal);
  vfLamp(b, 0, h + 0.56, 0, 0.13);
  for (const [ax, az] of [[0, 1], [0, -1], [1, 0], [-1, 0]]) {
    const ry = ax ? ax * Math.PI / 2 : az > 0 ? 0 : Math.PI;
    for (const [u, v] of [[-0.12, 0.62], [0.12, 0.62], [-0.12, 0.38], [0.12, 0.38]]) b.win(ax ? ax * (s / 2 + 0.012) : u * s + 0.25, h * v, az ? az * (s / 2 + 0.012) : u * s + 0.25, ry, 0.2, 0.2, 0, b.R() < 0.5);
  }
  const wing = vfWing(b, 0, -0.1, s / 2 + 0.17, 0, 1, 0.4, 2.1, 0.8, 0.12);
  vfWing(b, 0, -0.1, -s / 2 - 0.17, 0, -1, 0.4, 2.1, 0.8, 0.12);
  b.top = h + 1.2; b.bot = -0.9; b.foot = s / 2 + 0.17 + wing;
}

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
// The camera of the operator's orrery picture (look-universe.webp, 1533 x 820), recovered by fitting a perspective
// camera to two of its landmarks -- the outer orbit's ellipse (centre 817,390; 738 x 378 px) and Cymetica's own
// outer ring (791,280; 203 x 107) -- rms 6 px: the view 56.5 degrees off vertical, a 25-degree lens, aimed a little
// in front of Cymetica (off: right, toward the camera; in units where the outer pair sits at 206). home() keeps his
// frame inside the stage at any size: as tall as the stage when it is wider than his picture, as wide when narrower.
const UVCAM = { polar: 0.9865, fov: 25.04, aspect: 1533 / 820, dist: 481.7, off: [-10.57, 74.57] };
// how far the view may turn, off vertical: from nearly straight down to 18 degrees above the plane (his first look
// is 56.5 off vertical). A flight to a station stays inside it (flyTo keeps it at least 19 degrees up).
const UVTURN = { min: 0.12, max: 1.25 };
// Cymetica's sun: its parts are written at the size the detector once framed (a ball of 16.5); the sun is drawn
// k times that, so it fills the inner rings as the light fills his (white-hot to ~20 of the plane, glow to ~40,
// his ring at 60), and floats y above the plane. "Make the sun itself bigger" (2026-10-19).
const UVSUN = { k: 1.7, y: 6, ball: 14, disc: 12.75 };   // 15 % smaller than first drawn ("o 15% asi zmensil", 2026-10-19)
// how much larger than its own decks a station is drawn on the map: his stations are 100 to 150 px across on his
// 1533-wide frame, about 30 to 40 units of the plane; ours, 36 of them where he drew 13, a little smaller
const UVSS = 3.8;
// His orbit lines, read off the picture: each crossing sent back through that camera onto the plane gave its
// radius; colour is the line's core as he has it on the left of his picture (sRGB), px its width there on his
// 1533-wide frame, dots where his line is dotted, glow how much of a halo it carries. The stations ride the solid
// ones (CO.uvGalaxy.ORBITS). Brighter on the left and the far side, as his are.
const UVLINES = [
  { r: 205.5, hex: '#548f9d', px: 2.4 }, { r: 203, hex: '#80c8d0', px: 3, glow: 0.5 }, { r: 194, hex: '#2a4a52', px: 2.6, dots: 1 },
  { r: 183, hex: '#1f3239', px: 2.2 }, { r: 178, hex: '#23394b', px: 2.4 },
  { r: 154, hex: '#3d526a', px: 3.4, glow: 0.2 },
  { r: 136, hex: '#426862', px: 3, glow: 0.15 },
  { r: 120, hex: '#263a48', px: 2.4, dots: 1 },
  { r: 105, hex: '#8fb8b2', px: 4.4, glow: 0.45 }, { r: 100, hex: '#3f7d71', px: 4, glow: 0.3 },
  { r: 90, hex: '#3e706d', px: 2.4, dots: 1 }
];
// The colour to give a light so it shows on screen as his hex: the map's frame is desaturated a little (sat) and
// goes through three.js's ACES (exposure 1.15), which lifts the middle and crushes the darkest tones to black, so a
// colour written as measured comes out wrong. Undone here in reverse: ACES's output matrix, its curve, its input
// matrix, then the saturation. Good to a few levels, bloom aside.
const UVLOOK = { exposure: 1.15, sat: 0.9 };
const ACES_IN = new THREE.Matrix3().set(0.59719, 0.35458, 0.04823, 0.07600, 0.90834, 0.01566, 0.02840, 0.13383, 0.83777);
const ACES_OUT = new THREE.Matrix3().set(1.60475, -0.53108, -0.07367, -0.10208, 1.10813, -0.00605, -0.00327, -0.07276, 1.07602);
const ACES_IN_INV = ACES_IN.clone().invert(), ACES_OUT_INV = ACES_OUT.clone().invert();
function acesFit(v) { return (v * (v + 0.0245786) - 0.000090537) / (v * (0.983729 * v + 0.432951) + 0.238081); }
function look(hex, k = 1) {
  const t = new THREE.Color(hex), u = new THREE.Vector3(t.r * k, t.g * k, t.b * k).applyMatrix3(ACES_OUT_INV);
  for (const ch of ['x', 'y', 'z']) {
    const want = Math.min(0.97, u[ch]);
    let lo = 0, hi = 40; for (let i = 0; i < 40; i++) { const m = (lo + hi) / 2; if (acesFit(m) < want) lo = m; else hi = m; }
    u[ch] = lo;
  }
  u.applyMatrix3(ACES_IN_INV).multiplyScalar(0.6 / UVLOOK.exposure);
  const lum = 0.2126 * u.x + 0.7152 * u.y + 0.0722 * u.z;
  return new THREE.Color(Math.max(0, lum + (u.x - lum) / UVLOOK.sat), Math.max(0, lum + (u.y - lum) / UVLOOK.sat), Math.max(0, lum + (u.z - lum) / UVLOOK.sat));
}
// a band round the centre, r wide by w either side; u runs U times round it (dots), and each vertex takes the
// colour paint(angle) gives it: where it is on the orbit
function uvBand(r, w, U, paint, n = 720) {
  const pos = [], uv = [], col = [], idx = [];
  for (let k = 0; k <= n; k++) {
    const a = k / n * Math.PI * 2, s = Math.sin(a), c = Math.cos(a), f = paint(a);
    pos.push(s * (r - w), 0, c * (r - w), s * (r + w), 0, c * (r + w)); uv.push(k / n * U, 0, k / n * U, 1); col.push(f.r, f.g, f.b, f.r, f.g, f.b);
    if (k < n) { const i = k * 2; idx.push(i, i + 1, i + 2, i + 1, i + 3, i + 2); }
  }
  const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.setAttribute('uv', new THREE.Float32BufferAttribute(uv, 2));
  g.setAttribute('color', new THREE.Float32BufferAttribute(col, 3)); g.setIndex(idx);
  return g;
}
// a line of light across its band: a sharp core and a little falloff; dots: one round dot per repeat
function uvLineTex(dots) {
  const key = dots ? 'uvDot' : 'uvLine'; if (TX[key]) return TX[key];
  const t = ctex(dots ? 32 : 4, 32, (g, W, H) => {
    const img = g.createImageData(W, H), d = img.data;
    for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
      const v = (j + 0.5) / H - 0.5, u = dots ? (i + 0.5) / W - 0.5 : 0, rr = Math.sqrt(v * v + u * u);
      // flat across the middle so a line two or three pixels wide still reaches its full colour
      const k = (j * W + i) * 4, a = dots ? 1 - sstep(0.2, 0.42, rr) : 1 - sstep(0.18, 0.5, Math.abs(v));
      d[k] = d[k + 1] = d[k + 2] = 255; d[k + 3] = Math.round(a * 255);
    }
    g.putImageData(img, 0, 0);
  });
  t.wrapS = THREE.RepeatWrapping; TX[key] = t; return t;
}
// a star on an orbit as he has it: a white-hot point, a long horizontal glint, a shorter vertical one, faint rays
function flareTex() {
  return TX.flare || (TX.flare = ctex(256, 256, (g, W) => {
    const c = W / 2, gr = g.createRadialGradient(c, c, 0, c, c, c);
    gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.05, 'rgba(240,255,255,.95)'); gr.addColorStop(0.16, 'rgba(160,240,255,.32)'); gr.addColorStop(0.45, 'rgba(90,200,230,.06)'); gr.addColorStop(1, 'rgba(90,200,230,0)');
    g.fillStyle = gr; g.fillRect(0, 0, W, W);
    const streak = (w, h, a) => { g.save(); g.translate(c, c); g.scale(w, h); const s = g.createRadialGradient(0, 0, 0, 0, 0, c); s.addColorStop(0, 'rgba(225,252,255,' + a + ')'); s.addColorStop(1, 'rgba(160,235,255,0)'); g.fillStyle = s; g.beginPath(); g.arc(0, 0, c, 0, Math.PI * 2); g.fill(); g.restore(); };
    streak(1, 0.035, 0.9); streak(0.035, 0.55, 0.6); g.rotate(0); streak(0.6, 0.02, 0.35);
  }));
}
// Cymetica's ball, painted once as the operator's picture of a collision has it (images/12, 2026-10-19: "ma vypadat
// takto presne"): arcs of plasma lying round a sphere -- gold most, orange, blue and white between, brighter on the
// near side -- over a white-hot heart that runs pink and then blue inside, knots of light where the weave is dense,
// sparks and short streaks flying out of the middle. On a face turned to the camera it reads as the same ball from
// every side. Arcs are drawn in four pieces, each as bright as its depth, then a soft wide pass under a crisp one.
function colliderTex(seed) {
  const key = 'col' + seed; if (TX[key]) return TX[key];
  const R = rng(seed * 7 + 3);
  return (TX[key] = ctex(1024, 1024, (g, W) => {
    // the ball takes the middle 0.6 of the picture; the burst round it reaches the edges
    const c = W / 2, rad = W * 0.3; g.globalCompositeOperation = 'lighter';
    const heart = g.createRadialGradient(c, c, 0, c, c, rad * 1.1);
    [[0, 'rgba(255,255,255,1)'], [0.015, 'rgba(255,230,246,.9)'], [0.06, 'rgba(255,74,176,.75)'], [0.12, 'rgba(176,70,240,.5)'], [0.2, 'rgba(60,96,255,.45)'], [0.38, 'rgba(255,140,40,.12)'], [0.75, 'rgba(255,130,40,.05)'], [1, 'rgba(255,130,40,0)']].forEach(([o, s]) => heart.addColorStop(o, s));
    g.fillStyle = heart; g.fillRect(0, 0, W, W);
    const V = () => { const u = R() * 2 - 1, th = R() * Math.PI * 2, s = Math.sqrt(1 - u * u); return [Math.cos(th) * s, u, Math.sin(th) * s]; };
    const cross = (a, b) => [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]], nrm = (a) => { const l = Math.hypot(a[0], a[1], a[2]); return a.map((x) => x / l); };
    // an arc of a circle round o in a random plane, drawn in four pieces each as bright as its depth: a wide soft
    // pass under a crisp one, thick and saturated as his are
    const arc = (o, rr, len, wa, cols, w, dim) => {
      const n = V(), u = nrm(cross(n, Math.abs(n[1]) < 0.9 ? [0, 1, 0] : [1, 0, 0])), v = cross(n, u), t0 = R() * Math.PI * 2, wf = 3 + R() * 6, ph = R() * 6, col = cols[Math.floor(R() * cols.length)], pts = [];
      for (let s = 0; s <= 48; s++) {
        const t = t0 + len * s / 48, k = rr * (1 + wa * Math.sin(t * wf + ph)), p = [0, 1, 2].map((i) => o[i] + (Math.cos(t) * u[i] + Math.sin(t) * v[i]) * k);
        pts.push([c + p[0], c - p[1], Math.max(-1, Math.min(1, p[2] / rad))]);
      }
      for (let q = 0; q < 4; q++) {
        const a0 = q * 12, a1 = a0 + 12, b = (0.3 + 0.7 * ((pts[a0][2] + pts[a1][2]) / 2 + 1) / 2) * dim;
        [[w * 3.2, 0.06 * b], [w, 0.92 * b]].forEach(([lw, al]) => {
          g.strokeStyle = 'rgba(' + col.join(',') + ',' + al.toFixed(3) + ')'; g.lineWidth = lw; g.lineCap = 'round';
          g.beginPath(); g.moveTo(pts[a0][0], pts[a0][1]); for (let s = a0 + 1; s <= a1; s++) g.lineTo(pts[s][0], pts[s][1]); g.stroke();
        });
      }
    };
    const GOLD = [[255, 150, 36], [255, 150, 36], [255, 178, 70], [255, 112, 18], [255, 196, 96]], BLUE = [[36, 104, 255], [60, 130, 255], [96, 160, 255], [150, 200, 255]];
    const DEEP = [[255, 84, 180], [150, 84, 255], [60, 110, 255], [40, 90, 255], [40, 90, 255], [255, 100, 60]];
    // a gold glow along the ball's edge, where his weave is densest and brightest
    const rim = g.createRadialGradient(c, c, rad * 0.72, c, c, rad * 1.16);
    rim.addColorStop(0, 'rgba(255,170,70,0)'); rim.addColorStop(0.55, 'rgba(255,170,70,.26)'); rim.addColorStop(1, 'rgba(255,150,50,0)'); g.fillStyle = rim; g.fillRect(0, 0, W, W);
    // inside: pink, violet and blue swirls round the heart; through the ball: gold and blue loops; on its shell: the
    // arcs that draw its round edge
    for (let i = 0; i < 80; i++) arc(V().map((x) => x * rad * R() * 0.3), rad * (0.12 + R() * 0.32), 2 + R() * 3.5, 0.1 * R(), DEEP, 2.2 + R() * 2.8, 0.85);
    for (let i = 0; i < 56; i++) arc(V().map((x) => x * rad * R() * 0.5), rad * (0.25 + R() * 0.35), 1.6 + R() * 3.2, 0.08 * R(), R() < 0.5 ? GOLD : BLUE, 2.4 + R() * 2.8, 0.9);
    for (let i = 0; i < 110; i++) arc([0, 0, 0], rad * (0.86 + R() * 0.16), 0.6 + R() * 1.9, 0.04 * R(), R() < 0.6 ? GOLD : BLUE, 2.4 + R() * 2.8, 1);
    // and a few big loops bulging out past the edge, as his do
    for (let i = 0; i < 18; i++) arc(V().map((x) => x * rad * (0.4 + R() * 0.25)), rad * (0.5 + R() * 0.3), 1.4 + R() * 2.2, 0.05 * R(), R() < 0.6 ? GOLD : BLUE, 2.5 + R() * 2.2, 0.95);
    // his beams: two broad blue-white ones on one diagonal through the heart, two gold ones across it, tapering out
    // past the ball, each a wide soft pass under a hot narrow one
    [[-0.62 + R() * 0.1, '170,206,255', 26], [2.52 + R() * 0.1, '170,206,255', 22], [3.0 + R() * 0.2, '255,186,90', 20], [0.12 + R() * 0.2, '255,176,80', 16]].forEach(([a, rgb, wd]) => {
      g.save(); g.translate(c, c); g.rotate(a);
      [[wd * 2.6, 0.28], [wd, 0.75], [wd * 0.3, 1]].forEach(([ww, al]) => {
        const gr = g.createLinearGradient(rad * 0.1, 0, W * 0.5, 0); gr.addColorStop(0, 'rgba(' + rgb + ',' + al + ')'); gr.addColorStop(0.6, 'rgba(' + rgb + ',' + (al * 0.55).toFixed(2) + ')'); gr.addColorStop(1, 'rgba(' + rgb + ',0)');
        g.fillStyle = gr; g.beginPath(); g.moveTo(rad * 0.1, -ww / 2); g.lineTo(W * 0.5, 0); g.lineTo(rad * 0.1, ww / 2); g.closePath(); g.fill();
      });
      g.restore();
    });
    // the burst: spikes of light out of the ball's edge, gold and blue-white, sparks along them; fine streaks
    // flying out of the middle; sparks everywhere; knots of light in the weave
    for (let i = 0; i < 64; i++) {
      const a = R() * Math.PI * 2, r0 = rad * (0.55 + R() * 0.35), r1 = rad * (1.15 + R() * R() * 0.55), wd = 3 + R() * 9, rgb = R() < 0.6 ? '255,178,74' : R() < 0.6 ? '150,196,255' : '255,240,220';
      g.save(); g.translate(c, c); g.rotate(a);
      const gr = g.createLinearGradient(r0, 0, r1, 0); gr.addColorStop(0, 'rgba(' + rgb + ',0)'); gr.addColorStop(0.25, 'rgba(' + rgb + ',' + (0.35 + R() * 0.4).toFixed(2) + ')'); gr.addColorStop(1, 'rgba(' + rgb + ',0)');
      g.fillStyle = gr; g.beginPath(); g.moveTo(r0, -wd); g.lineTo(r1, 0); g.lineTo(r0, wd); g.closePath(); g.fill(); g.restore();
    }
    const dot = (x, y, r, rgb, a) => { const gr = g.createRadialGradient(x, y, 0, x, y, r); gr.addColorStop(0, 'rgba(' + rgb + ',' + a + ')'); gr.addColorStop(1, 'rgba(' + rgb + ',0)'); g.fillStyle = gr; g.fillRect(x - r, y - r, r * 2, r * 2); };
    for (let i = 0; i < 60; i++) { const a = R() * Math.PI * 2, r = rad * (0.35 + R() * 0.65); dot(c + Math.cos(a) * r, c + Math.sin(a) * r, 6 + R() * 14, R() < 0.7 ? '255,228,170' : '200,224,255', 0.45 + R() * 0.4); }
    for (let i = 0; i < 1500; i++) { const a = R() * Math.PI * 2, r = rad * (0.45 + R() * 1.15), s = 0.6 + R() * 1.8; g.fillStyle = (R() < 0.78 ? 'rgba(255,196,100,' : 'rgba(190,220,255,') + (0.3 + R() * 0.65).toFixed(2) + ')'; g.fillRect(c + Math.cos(a) * r - s / 2, c + Math.sin(a) * r - s / 2, s, s); }
    for (let i = 0; i < 320; i++) {
      const a = R() * Math.PI * 2, r0 = rad * (0.2 + R() * 1.2), l = 10 + R() * R() * 120, rgb = R() < 0.62 ? '255,190,96' : R() < 0.5 ? '255,248,236' : '130,180,255';
      const x0 = c + Math.cos(a) * r0, y0 = c + Math.sin(a) * r0, x1 = c + Math.cos(a) * (r0 + l), y1 = c + Math.sin(a) * (r0 + l), gr = g.createLinearGradient(x0, y0, x1, y1);
      gr.addColorStop(0, 'rgba(' + rgb + ',0)'); gr.addColorStop(0.5, 'rgba(' + rgb + ',' + (0.3 + R() * 0.5).toFixed(2) + ')'); gr.addColorStop(1, 'rgba(' + rgb + ',0)');
      g.strokeStyle = gr; g.lineWidth = 0.9 + R() * 1.6; g.beginPath(); g.moveTo(x0, y0); g.lineTo(x1, y1); g.stroke();
    }
  }));
}
// a jet's light: white at its root, gone at its tip (the colour comes from its material). The canvas's top row is
// the cylinder's top, the jet's tip.
function jetTex() {
  // (rising over its first few percent: eight jets share one root, and at full strength there they add up to a blot)
  return TX.jet || (TX.jet = ctex(32, 256, (g, W, H) => { const gr = g.createLinearGradient(0, H, 0, 0); gr.addColorStop(0, 'rgba(255,255,255,0)'); gr.addColorStop(0.12, 'rgba(255,255,255,.25)'); gr.addColorStop(0.24, 'rgba(255,255,255,1)'); gr.addColorStop(0.5, 'rgba(255,255,255,.55)'); gr.addColorStop(0.85, 'rgba(255,255,255,.1)'); gr.addColorStop(1, 'rgba(255,255,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, W, H); }));
}
// The sky of his picture: near-black navy, a teal haze over the top left of the first look fading to the bottom
// right, and many small sharp white stars, a few brighter. Drawn round the camera as far as a sky is.
function uvSky(AZ) {
  const g = new THREE.Group(), R = rng(58), D = 4200;
  // the haze, painted on the inside of a sphere: lon/lat of every texel, lit by how close it is to the direction the
  // top left of the first look shows
  const cam = new THREE.Vector3().setFromSpherical(new THREE.Spherical(1, UVCAM.polar, AZ)).negate();   // where the camera looks
  const right = new THREE.Vector3().crossVectors(cam, new THREE.Vector3(0, 1, 0)).normalize(), up = new THREE.Vector3().crossVectors(right, cam).normalize();
  const tv = Math.tan(THREE.MathUtils.degToRad(UVCAM.fov) / 2), th = tv * UVCAM.aspect;
  const toward = (x, y) => cam.clone().addScaledVector(right, x * th).addScaledVector(up, y * tv).normalize();
  const hot = toward(-0.55, 0.75), warm = toward(-0.1, 0.95), cold = toward(0.9, -0.9), f = vnoise(19);
  // his sky, measured: #01080d over most of it, #051d28 at the top left, #01060a at the bottom right
  const rgb = (hex) => { const h = look(hex).getHex(THREE.SRGBColorSpace); return [h >> 16 & 255, h >> 8 & 255, h & 255]; };
  const B0 = rgb('#01090e'), B1 = rgb('#062030'), B2 = rgb('#01050a');
  const tex = ctex(1024, 512, (c, W, H) => {
    const img = c.createImageData(W, H), d = img.data, v = new THREE.Vector3();
    for (let j = 0; j < H; j++) for (let i = 0; i < W; i++) {
      const lon = (i + 0.5) / W * Math.PI * 2, lat = Math.PI / 2 - (j + 0.5) / H * Math.PI;
      // three.js's sphere: u = 0 at -x, going round through +z
      v.set(-Math.cos(lon) * Math.cos(lat), Math.sin(lat), Math.sin(lon) * Math.cos(lat));
      const n = f(i / W * 9, j / H * 5, 4);
      const h = Math.max(0, v.dot(hot)) ** 22 * 0.9 + Math.max(0, v.dot(warm)) ** 30 * 0.5, k = (j * W + i) * 4;
      const haze = Math.min(1, h * (0.75 + 0.5 * n)), dark = Math.min(1, Math.max(0, v.dot(cold)) ** 10 * 1.2);
      for (let ch = 0; ch < 3; ch++) d[k + ch] = B0[ch] + (B1[ch] - B0[ch]) * haze + (B2[ch] - B0[ch]) * dark * (1 - haze);
      d[k + 3] = 255;
    }
    c.putImageData(img, 0, 0);
  });
  const sph = new THREE.Mesh(new THREE.SphereGeometry(D, 64, 32), new THREE.MeshBasicMaterial({ map: tex, side: THREE.BackSide, depthWrite: false, fog: false }));
  sph.renderOrder = -20; sph.frustumCulled = false; g.add(sph);
  // a faint teal wisp or two inside the haze, his nebula's filaments
  [[-0.62, 0.62, 0.55, 7, 0.07], [-0.25, 0.85, 0.4, 13, 0.05], [-0.85, 0.2, 0.35, 29, 0.04]].forEach(([x, y, s, seed, op]) => {
    const m = new THREE.Mesh(G.plane, new THREE.MeshBasicMaterial({ map: filamentTex(seed), transparent: true, opacity: op, blending: THREE.AdditiveBlending, depthWrite: false, fog: false }));
    const at = toward(x, y), sz = D * s * th * 2; m.scale.set(sz, sz, 1); m.position.copy(at).multiplyScalar(D * 0.98); m.lookAt(0, 0, 0); m.rotateZ(R() * 6.28); m.renderOrder = -19; m.frustumCulled = false; g.add(m);
  });
  // stars: about one to every 2,500 px of his sky, mostly faint, sharp; points are a pixel each
  const rnd = () => { const u = R() * 2 - 1, t = R() * Math.PI * 2, s = Math.sqrt(1 - u * u); return new THREE.Vector3(Math.cos(t) * s, u, Math.sin(t) * s); };
  const N = 26000, pos = new Float32Array(N * 3), col = new Float32Array(N * 3), cc = new THREE.Color();
  for (let i = 0; i < N; i++) { pos.set(rnd().multiplyScalar(D * 0.95).toArray(), i * 3); cc.set(R() < 0.15 ? 0xbfe9ff : 0xeef6ff).multiplyScalar(0.18 + R() * R() * 1.1); col.set([cc.r, cc.g, cc.b], i * 3); }
  const pg = new THREE.BufferGeometry(); pg.setAttribute('position', new THREE.BufferAttribute(pos, 3)); pg.setAttribute('color', new THREE.BufferAttribute(col, 3));
  const pts = new THREE.Points(pg, new THREE.PointsMaterial({ vertexColors: true, size: 1, sizeAttenuation: false, fog: false, depthWrite: false })); pts.frustumCulled = false; pts.renderOrder = -18; g.add(pts);
  // the brighter ones, two to three pixels with a soft edge
  const B = 1400, px = D * 0.93 * 2 * tv / 1116, im = new THREE.InstancedMesh(G.plane, new THREE.MeshBasicMaterial({ map: starTex(), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, fog: false }), B), o = new THREE.Object3D();
  for (let i = 0; i < B; i++) {
    o.position.copy(rnd().multiplyScalar(D * 0.93)); o.lookAt(0, 0, 0); o.scale.setScalar(px * (3 + R() * R() * 5)); o.updateMatrix(); im.setMatrixAt(i, o.matrix);
    im.setColorAt(i, cc.set(R() < 0.2 ? 0xc8eeff : 0xffffff).multiplyScalar(0.5 + R() * 0.9));
  }
  im.frustumCulled = false; im.renderOrder = -18; g.add(im);
  return g;
}
class Universe3D {
  constructor(el, stage, h) {
    this.el = el; this.stage = stage; this.h = h || {};
    this.tip = stage.querySelector('.tip'); this.bans = stage.querySelector('.uvbans');
    this.items = []; this.live = {}; this.mineKey = ''; this.fitted = false; this.pops = []; this.arcs = [];
    this.mouse = new THREE.Vector2(); this.ray = new THREE.Raycaster(); this.hover = null; this.mouseIn = false; this.lastUse = 0;
    geo();
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x01080d);
    this.camera = new THREE.PerspectiveCamera(UVCAM.fov, 2, 0.5, 9000);
    // no antialias on the renderer itself: three.js resolves it through ONE quad shared by every renderer on the
    // page, so a second renderer (a preview) would take this canvas over. The pass multisamples instead.
    this.renderer = new THREE.WebGPURenderer({ antialias: false });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.15;
    el.appendChild(this.renderer.domElement);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    // Turned as the office is: the left button turns the view round what it looks at, the right one (or shift with
    // the left) slides it over the galaxy's disc, the wheel zooms where it points. "Only to the sides, it cannot be
    // turned like the office" (2026-10-19) was the left button panning. The view stays above the plane: from
    // straight down to about 18 degrees over it, never under the disc and never edge-on, where the orbits are lines.
    Object.assign(this.controls, { enableDamping: true, dampingFactor: 0.08, minDistance: 7, maxDistance: 900, minPolarAngle: UVTURN.min, maxPolarAngle: UVTURN.max,
      autoRotate: false, screenSpacePanning: false, zoomToCursor: true, zoomSpeed: 1.1, rotateSpeed: 0.55, panSpeed: 1.1,
      mouseButtons: { LEFT: THREE.MOUSE.ROTATE, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.PAN },
      touches: { ONE: THREE.TOUCH.ROTATE, TWO: THREE.TOUCH.DOLLY_PAN } });
    // a hand on the controls ends a flight; turning round a station the camera follows keeps following it, sliding
    // the view away lets it go (OrbitControls has set its state by the time it says 'start': 2, 4 and 5 move the target)
    this.controls.addEventListener('start', () => {
      this.tw = null; this.used = true; this.lastUse = performance.now();
      if ([2, 4, 5].includes(this.controls.state)) { this.follow = null; this.followAt = null; }
    });
    // a hand on the map, for the pacer: the controls moving the camera (also while it settles) and the mouse
    this.controls.addEventListener('change', () => { this.lastInput = performance.now(); });
    this.pace = pacer(() => !!this.tw || !!this.follow || this.controls.autoRotate || performance.now() - (this.lastInput || 0) < 1500);
    this.world();
    this.bind();
    this.resize();
    this.clock = new THREE.Clock();
    this.renderer.init().then(() => {
      // his picture keeps its teal and green: less of the pastel pull than the office's
      try { this.post = new Post(this.renderer, this.scene, this.camera, 0.5, 0.3, 0.8, { sat: 0.9 }); } catch (e) { console.warn('bloom off:', e); this.post = null; }
      this.renderer.setAnimationLoop(() => this.frame());
      this.ready = true;
    }).catch((e) => { console.error('3D map could not start:', e); if (this.h.onFail) this.h.onFail(e); });
    setInterval(() => { if (this.visible()) this.pulse(); }, 1700);
    if (window.ResizeObserver) new ResizeObserver(() => this.resize()).observe(el);
    // the plates' font arrives after their first measure: measure them again when it has, for the overlap test
    const remeasure = () => { this.items.forEach((it) => { if (it.el) it.el._bw = 0; }); if (this.coreEl) this.coreEl._bw = 0; this.ovKey = ''; };
    if (document.fonts && document.fonts.addEventListener) document.fonts.addEventListener('loadingdone', remeasure);
  }
  visible() { return this.el.clientWidth > 0 && this.el.clientHeight > 0; }

  // light, the sky, the orbits and what runs along them, and Cymetica in the middle
  world() {
    const S = this.scene;
    S.add(new THREE.AmbientLight(0x1a2230, 0.7));
    S.add(new THREE.HemisphereLight(0xdfe8f2, 0x05070a, 0.75));
    const sun = new THREE.DirectionalLight(0xf4f8fc, 2.1); sun.position.set(-300, 280, 220); S.add(sun);
    const rim = new THREE.DirectionalLight(0x00cfff, 0.5); rim.position.set(240, -60, -260); S.add(rim);
    this.sky = uvSky(CO.uvGalaxy.AZ); S.add(this.sky);
    this.fades = [];
    this.lanes();
    this.core();
  }
  // The orbits as he drew them (UVLINES): each a sharp line of light in its own colour, the bright ones in a soft
  // halo, some dotted; all brighter on the left and the far side of the first look and dim on the right, as in his
  // picture. A few stars of light ride the orbits, faster than the stations.
  lanes() {
    const Gx = CO.uvGalaxy, R = rng(3), peak = Gx.AZ - Math.PI / 2 - 0.45;
    // at the first look one unit of the plane is about 3.6 px wide on his 1533-wide frame
    // how lit a point of an orbit is: 1 on the far left, about .75 at the back, .45 in front, .3 on the right
    const PX = 0.42, shade = (a) => 0.3 + 0.7 * Math.pow(0.5 + 0.5 * Math.cos(a - peak), 1.3);
    // his dim side is grey as well as dark: a line's colour there loses most of its hue
    const dimOf = (hex) => { const c = new THREE.Color(hex), l = 0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b; return new THREE.Color(l, l, l).lerp(c, 0.35).multiplyScalar(0.42); };
    const paint = (hex, k = 1, pow = 1) => { const hi = look(hex, k), lo = look('#' + dimOf(hex).getHexString(), k); return (a) => lo.clone().lerp(hi, Math.pow((shade(a) - 0.3) / 0.7, pow)); };
    const add = (r, w, U, tex, f) => {
      const m = new THREE.Mesh(uvBand(r, w, U, f), new THREE.MeshBasicMaterial({ map: tex, vertexColors: true, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
      m.renderOrder = -5; this.scene.add(m); return m;
    };
    UVLINES.forEach((L) => {
      const w = L.px * PX;
      add(L.r, w, L.dots ? Math.round(L.r * Math.PI * 2 / 2.1) : 1, uvLineTex(L.dots), paint(L.hex));
      if (L.glow) add(L.r, 2.5 + L.glow * 3, 1, bandTex(), paint(L.hex, 0.22 * L.glow, 2));
    });
    // the teal light the outer pair sits in: wide and faint (#003a47 round it where his sky is #031820), on its lit side
    add(204.5, 9, 1, bandTex(), paint('#00262e', 1, 2.5));
    this.laneDefs = UVLINES.filter((L) => !L.dots).map((L) => ({ r: L.r, col: L.hex, speed: Gx.omega(L.r) * 6 }));
    // the stars of light on the orbits, where his are at the first look (sent back through his camera): a big one
    // top left on the outer pair, a small green one on the green-grey line, a faint one high on the blue; two more
    // round the far side
    this.ships = [[203, -1.0, 24, 1.5], [136, 0.42, 9, 0.9], [178, -1.47, 8, 0.7], [203, 2.3, 16, 1.2], [105, 3.9, 13, 1.1]].map(([r, a, size, k]) => {
      const L = this.laneDefs.find((x) => x.r === r) || this.laneDefs[0];
      const head = new THREE.Sprite(new THREE.SpriteMaterial({ map: flareTex(), color: new THREE.Color(L.col).lerp(new THREE.Color(0xffffff), 0.6).multiplyScalar(k), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
      head.scale.setScalar(size); this.scene.add(head);
      return { L, a, head, size, ph: R() * 6 };
    });
  }
  // Cymetica, as the operator's collider photograph and the sun of his orrery: a ball of hundreds of tangled
  // filaments of light, mostly golden-orange and warm yellow threads through electric-blue and white-blue ones, a
  // white-hot heart with a little red-magenta deep inside, thick jets shot out of it in several directions (gold
  // and blue-white, narrowing, sparkling) and a spray of golden sparks -- drawn big (UVSUN), the one thing at the
  // centre. Round it on the orbits' plane, still, his orrery's cyan rings of light and pale silver arcs. The
  // detector that framed it, four turning rings of silver panels, is gone: "remove those weird rings that turn
  // round it and make the sun itself bigger" (2026-10-19). Units are the plane's: his rings reach 60.
  core() {
    const g = new THREE.Group(), R = rng(77), up = new THREE.Vector3(0, 1, 0);
    // everything of the sun in one group, written at the ball's own size and drawn k times it: the sparks' sizes
    // and the glows' with it, since a sprite takes its parent's scale
    const sun = new THREE.Group(); sun.position.y = UVSUN.y; sun.scale.setScalar(UVSUN.k); g.add(sun); this.sun = sun;
    this.heartAt = new THREE.Vector3(0, UVSUN.y, 0); this.sunR = UVSUN.ball * UVSUN.k;
    // the heart: white-hot, a warm and a magenta glow round it, a white-gold one that fills the ball so it reads as
    // a sun and not a tangle, a wide soft gold one, a cool one wider still
    const heart = new THREE.Group(); sun.add(heart); this.heart = heart;
    heart.add(new THREE.Mesh(G.sphere, new THREE.MeshBasicMaterial({ color: new THREE.Color(1, 0.97, 0.9).multiplyScalar(2.6) })));
    heart.children[0].scale.setScalar(this.heartR = 0.9);
    // Cymetica as the operator's picture of a collision (2026-10-19, images/12: "ma vypadat takto presne"; before it,
    // of the sun: "to nemaji byt letajici krouzky, to ma vse jakoby zevnitr vychazet"): a ball woven of plasma arcs
    // round a white-hot heart that runs pink and blue inside, beams of blue-white and gold shooting out through it,
    // sparks and streaks flying out of it -- nothing flies round it. The ball is painted (colliderTex) on faces that
    // always turn to the camera, so it is the same ball from every side; two of them from different seeds turn slowly
    // against each other and flicker, so the weave shimmers. Round it a glow: white, pink, blue, gold, a faint blue.
    this.corona = [[37, 0.07, 0xffb04a], [60, 0.035, 0xff9a3c], [85, 0.025, 0x3b9dff]].map(([s, o, c]) => { const sp = glowSprite(c, o, s); sun.add(sp); return sp; });
    heart.children[0].visible = false;   // the painting has its own heart
    this.fil = []; this.rays = []; this.weave = [];
    // The ball itself is the painting (colliderTex), laid over the map as it is -- two of them from different seeds,
    // turning slowly against each other -- not drawn through the map's pastel pipeline: through its bloom, its
    // saturation and its tone mapping his gold and blue came out a white blot (2026-10-19: the texture alone was his
    // picture, the scene was not). overlay() puts it where the heart is on the screen, as wide as the ball there; the
    // beams and the sparks stay in the scene, so they still pass in front of and behind it.
    const ce = document.createElement('div'); ce.className = 'uvcol'; ce.style.display = 'none'; ce._off = true;   // until overlay() places it
    // under the painting a blurred copy of it, turning with it: the glow his arcs have (a bloom of its own)
    const p1 = colliderTex(1).image, glow = document.createElement('canvas'); glow.width = p1.width; glow.height = p1.height; glow.getContext('2d').drawImage(p1, 0, 0); glow.className = 'g1';
    ce.appendChild(glow);
    [1, 2].forEach((seed) => { const cv = colliderTex(seed).image; cv.className = 'l' + seed; ce.appendChild(cv); });
    this.bans.insertBefore(ce, this.bans.firstChild); this.colEl = ce;
    // the jets: a wide soft cone and a hot narrow one inside it, white at the root, gone at the tip
    G.jet = G.jet || new THREE.CylinderGeometry(0.06, 1, 1, 24, 1, true).translate(0, 0.5, 0);
    // they fan out across the first look's view (an angle on its screen, a little toward or away from it), so each
    // reads at its length instead of as a blot pointing at the camera; a little shorter than the ball is wide
    // times k, so the longest ends inside his ring at 60
    const cam = new THREE.Vector3().setFromSpherical(new THREE.Spherical(1, UVCAM.polar, CO.uvGalaxy.AZ)), right = new THREE.Vector3().crossVectors(cam, up).normalize(), vup = new THREE.Vector3().crossVectors(right, cam).normalize();
    this.beams = [];
    // his beams: two long blue-white ones through the middle on one diagonal, gold ones across, shorter ones between
    [[36, 0.1, 34, 0x9fd0ff], [216, -0.1, 33, 0x8fc4ff], [166, 0.2, 29, 0xffb347], [348, -0.25, 27, 0xffa22e], [300, 0.3, 21, 0x6fb0ff], [118, -0.3, 20, 0xffc266], [78, 0.4, 16, 0xffd28a], [258, 0.35, 18, 0xff9a22]].forEach(([deg, depth, len0, hex]) => {
      const len = len0 * 0.85;
      const t = deg * Math.PI / 180, dir = right.clone().multiplyScalar(Math.cos(t)).addScaledVector(vup, Math.sin(t)).addScaledVector(cam, depth).normalize();
      const q = new THREE.Quaternion().setFromUnitVectors(up, dir), j = new THREE.Group();
      j.quaternion.copy(q); sun.add(j);
      const outer = new THREE.Mesh(G.jet, new THREE.MeshBasicMaterial({ map: jetTex(), color: new THREE.Color(hex).multiplyScalar(0.45), transparent: true, opacity: 0.5, blending: THREE.AdditiveBlending, depthWrite: false }));
      const wk = len > 30 ? 1.8 : 1;   // his two long blue-white beams are the broad ones
      outer.scale.set(1.3 * wk, len, 1.3 * wk); j.add(outer);
      const inner = new THREE.Mesh(G.jet, new THREE.MeshBasicMaterial({ map: jetTex(), color: new THREE.Color(hex).multiplyScalar(1.0), transparent: true, opacity: 0.85, blending: THREE.AdditiveBlending, depthWrite: false }));
      inner.scale.set(0.3 * wk, len * 0.96, 0.3 * wk); j.add(inner);
      this.beams.push({ j, outer, inner, dir, len, ph: R() * 6, hex });
    });
    // the sparks: golden mostly, some white-blue; most stream out along the jets, the rest everywhere; each lives
    // a moment on the GPU (TSL: where it is is time, its own speed and its own phase), twinkling as it goes
    const NS = 1400, A = new Float32Array(NS * 4), B = new Float32Array(NS * 4), C = new Float32Array(NS * 3), cc = new THREE.Color();
    for (let i = 0; i < NS; i++) {
      const jet = R() < 0.55 ? this.beams[Math.floor(R() * this.beams.length)] : null;
      const d = jet ? jet.dir.clone().add(new THREE.Vector3(R() - 0.5, R() - 0.5, R() - 0.5).multiplyScalar(0.3)).normalize() : new THREE.Vector3(R() * 2 - 1, R() * 2 - 1, R() * 2 - 1).normalize();
      A.set([d.x, d.y, d.z, 0.1 + R() * 0.3], i * 4);
      // (the free ones fly as far as the jets do: the spray stays round the sun, not out among the stations)
      B.set([R(), 0.45 + R() * R() * 1.1, jet ? jet.len * (0.55 + R() * 0.45) : 10 + R() * 18, 0], i * 4);
      cc.set(R() < 0.78 ? (R() < 0.5 ? 0xffb94a : 0xffdf8a) : 0xcfe9ff).multiplyScalar(1.8); C.set([cc.r, cc.g, cc.b], i * 3);
    }
    const a = TSL.instancedBufferAttribute(new THREE.InstancedBufferAttribute(A, 4)), b = TSL.instancedBufferAttribute(new THREE.InstancedBufferAttribute(B, 4)), c = TSL.instancedBufferAttribute(new THREE.InstancedBufferAttribute(C, 3));
    const life = TSL.fract(TSL.time.mul(a.w).add(b.x)), fade = life.oneMinus().pow(0.8);
    const sm = new THREE.SpriteNodeMaterial({ transparent: true, depthWrite: false, blending: THREE.AdditiveBlending });
    sm.positionNode = a.xyz.mul(life.mul(b.z).add(2));
    sm.scaleNode = b.y.mul(fade.mul(0.7).add(0.3)).mul(TSL.sin(TSL.time.mul(19).add(b.x.mul(61))).mul(0.3).add(0.7));
    const tx = TSL.texture(glowTex(), TSL.uv());
    // a spark flying straight at the camera would sit on the disc all its life, a speck of dust on the sun: those fade
    const toward = TSL.cameraViewMatrix.mul(TSL.modelWorldMatrix.mul(vec4(a.xyz, 0))).xyz.normalize().z, side = TSL.smoothstep(0.8, 0.97, toward).oneMinus();
    sm.colorNode = vec4(c.mul(fade), tx.a.mul(fade).mul(side));
    this.sparkPts = new THREE.Mesh(G.plane, sm); this.sparkPts.count = NS; this.sparkPts.frustumCulled = false; sun.add(this.sparkPts);
    // the orrery's own rings on the plane, as his: thin cyan circles at 36, 42 (dashed), 53 and a bright one at 60,
    // a pale silver arc in pieces at 33 and 57; none of them turns
    const ringAt = (r, w, hex, U = 1, k = 1) => { const m = new THREE.Mesh(uvBand(r, w, U, () => look(hex, k)), new THREE.MeshBasicMaterial({ map: uvLineTex(U > 1), vertexColors: true, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide })); m.renderOrder = -4; g.add(m); return m; };
    this.coreRings = [ringAt(60, 0.9, '#a5d8e6'), ringAt(57.5, 0.7, '#4f8a9c'), ringAt(53, 0.7, '#77c2d0'), ringAt(42, 0.8, '#4e8d9f', 90), ringAt(36.5, 0.8, '#81cbdb')];
    const arcGeo = (r, w, a0, a1) => { const sh = new THREE.Shape(); sh.absarc(0, 0, r + w, a0, a1, false); sh.absarc(0, 0, r - w, a1, a0, true); return new THREE.ShapeGeometry(sh, 48).rotateX(-Math.PI / 2); };
    const arcMat = new THREE.MeshBasicMaterial({ color: look('#b8c8d2', 0.8), transparent: true, opacity: 0.55, depthWrite: false, side: THREE.DoubleSide });
    this.coneRings = [[33.5, 0.55, [[0.2, 1.5], [2.2, 3.3], [4.1, 5.6]]], [56.5, 0.5, [[0.9, 2.6], [3.4, 4.4], [5.0, 6.0]]]].map(([r, w, arcs]) => {
      const grp = new THREE.Group(); arcs.forEach(([a0, a1]) => grp.add(new THREE.Mesh(arcGeo(r, w, a0, a1), arcMat))); grp.position.y = 0.05; g.add(grp); return grp;
    });
    // a star of light on the outer ring, where his is
    const fl = new THREE.Sprite(new THREE.SpriteMaterial({ map: flareTex(), color: new THREE.Color(0xd8f6ff).multiplyScalar(1.4), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
    fl.scale.setScalar(16); g.add(fl); this.coreFlare = fl;
    // (its warm point light went with the detector: it reached only the panels, and no station is that close)
    // what the pointer finds: the sun and a little round it
    const hit = new THREE.Mesh(G.sphere, M.hit); hit.scale.setScalar(Math.max(34, this.sunR * 1.15)); hit.position.copy(this.heartAt); hit.userData.id = 'core'; g.add(hit); this.coreHit = hit;
    this.scene.add(g); this.coreG = g;
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
    p.root.scale.setScalar(UVSS);
    // only ours keeps its ring of light; the others ride their orbits, as in the picture
    if (!it.mine) { p.ring.visible = false; p.pool.visible = false; }
    p.hit.userData.id = c.id;
    if (it.mine) p.meRing = p.ring;
    this.scene.add(p.root);
    it.plot = p;
    it.anchor = new THREE.Vector3(); this.orbit(it, this.clock ? this.clock.getElapsedTime() : 0);
    it.size = (p.top - p.bot) * UVSS;
    this.paint(it);
    this.banner(it);
  }
  // where a station is on its orbit at a moment, and where its banner hangs
  orbit(it, t) {
    const o = it.orbit, p = it.plot; if (!o || !p) return;
    const a = o.a + o.w * t; p.root.position.set(Math.sin(a) * o.r, 0, Math.cos(a) * o.r);
    it.anchor.set(p.root.position.x, (p.top + 0.5) * UVSS, p.root.position.z);
  }
  paint(it) {
    const on = it.mine ? (it.c.working || []) : (this.live[it.c.id] || []);
    it.plot.b.paint(on, it.c.status === 'paused' ? 'paused' : !it.c.public && !it.mine ? 'priv' : '');
  }
  banner(it) {
    const c = it.c, acc = CO.accentHex(c.accent);
    if (!it.el) { it.el = document.createElement('div'); this.bans.appendChild(it.el); it.el.addEventListener('pointerenter', () => this.setHover(c.id, true)); it.el.addEventListener('pointerleave', () => this.setHover(null, true)); it.el.addEventListener('click', () => this.open(c.id)); }
    let name = String(c.name || '').toUpperCase(); if (name.length > 22) name = name.slice(0, 21) + '…';
    // hidden until overlay() has placed it once: a new banner otherwise sits in a heap at the stage's top left while
    // the map is starting ("jak nacita mapa tak vlevo nahore sou nejake nesmysly"), and one overlay() hid stays hidden
    const hid = !it.el._placed || it.el.classList.contains('hidden');
    it.el.className = 'b3' + (!c.public && !it.mine ? ' priv' : '') + (c.status === 'paused' ? ' paused' : '') + (it.mine ? ' mine' : '') + (hid ? ' hidden' : '');
    it.el.style.setProperty('--acc', acc);
    it.el.setAttribute('data-id', c.id);
    it.el.innerHTML = (it.mine ? '<span class="you">YOU</span>' : '') + '<span class="rib">' + (!c.public && !it.mine ? '<i class="lk"></i>' : '') + esc(name) + '</span><span class="teth"></span>';
    it.el._bw = 0;
  }
  coreBanner() {
    if (this.coreEl) return;
    const el = document.createElement('div'); el.className = 'b3 core hidden'; el.style.setProperty('--acc', '#00cfff');
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
    const core = this.heartAt.clone(), top = it.plot.root.position.clone().add(new THREE.Vector3(0, it.plot.top * 0.6 * UVSS, 0));
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
    const el = document.createElement('div'); el.className = 'b3pop'; el.textContent = label; el.style.visibility = 'hidden'; this.bans.appendChild(el);
    const p = { el, it, t0: performance.now() }; this.pops.push(p);
    setTimeout(() => { el.remove(); this.pops = this.pops.filter((x) => x !== p); }, 2600);
  }
  stats() { if (this.h.onStats) this.h.onStats(CO.uvStats(this.items, this.live)); }
  find(id) { return this.items.find((it) => String(it.c.id) === String(id)) || null; }
  open(id) { const it = this.find(id); if (it && this.h.onOpen) { this.hideTip(); this.h.onOpen(it); } }

  /* ---------------- camera ---------------- */
  // His camera (UVCAM): the same place at every stage size, aimed where his is; the lens (resize) widens only on a
  // stage narrower than his picture, so his whole frame stays in view
  home() {
    const Gx = CO.uvGalaxy, [ox, oz] = rotXZ(UVCAM.off[0], UVCAM.off[1], Gx.AZ);
    const tgt = new THREE.Vector3(ox, 0, oz), dir = new THREE.Vector3().setFromSpherical(new THREE.Spherical(1, UVCAM.polar, Gx.AZ));
    return { pos: tgt.clone().addScaledVector(dir, UVCAM.dist), tgt };
  }
  lens(aspect) { return aspect >= UVCAM.aspect ? UVCAM.fov : 2 * THREE.MathUtils.radToDeg(Math.atan(Math.tan(THREE.MathUtils.degToRad(UVCAM.fov) / 2) * UVCAM.aspect / aspect)); }
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
    const p = it.plot.root.position, tgt = new THREE.Vector3(p.x, p.y + (it.plot.top + it.plot.bot) * 0.5 * UVSS, p.z);
    const dir = this.camera.position.clone().sub(this.controls.target); if (dir.lengthSq() < 1e-6) dir.set(1, 0.6, 1);
    dir.y = Math.max(dir.y, dir.length() * 0.35); dir.normalize();
    // as near as the old 36-degree lens stood: a station fills the view as much as it did
    const dist = (16 + (it.plot.top - it.plot.bot) * 1.4 + it.plot.b.foot * 0.9) * UVSS * Math.tan(THREE.MathUtils.degToRad(18)) / Math.tan(THREE.MathUtils.degToRad(this.camera.fov) / 2);
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
    this.camera.aspect = w / h; this.camera.fov = this.lens(w / h); this.camera.updateProjectionMatrix();
    this.renderer.setSize(w, h, false);
  }

  /* ---------------- the frame ---------------- */
  frame() {
    if (!this.visible()) return;
    // a page opened in a hidden tab learns its size late, and not always through ResizeObserver
    if (this.el.clientWidth !== this._cw || this.el.clientHeight !== this._ch) {
      this._cw = this.el.clientWidth; this._ch = this.el.clientHeight; this.resize();
      if (this.fitted && !this.used) { if (!this.tw) this.fit(false); else if (this.tw.home) { const h2 = this.home(); this.tw.p1 = h2.pos; this.tw.t1 = h2.tgt; } }
      this.lastInput = performance.now();
    }
    if (!this.pace(performance.now())) return;
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
    // Cymetica: the filaments turn each their own way and flicker, the jets breathe, the heart pulses, a star of
    // light runs round the outer ring (the sparks fly on the GPU); the rings round it stay still
    this.fil.forEach((f, i) => { f.rotation.set(t * (0.11 + i * 0.05) * (i % 2 ? -1 : 1), t * (0.17 + i * 0.04), t * 0.04 * (i - 1.5)); f.material.opacity = 0.7 + 0.3 * Math.sin(t * (6 + i * 2.3) + i) * Math.sin(t * 2.3 + i * 1.7); });
    this.beams.forEach((b) => {
      const k = 0.5 + 0.5 * Math.sin(t * 1.9 + b.ph), fl = 0.85 + 0.15 * Math.sin(t * 23 + b.ph * 7);
      b.j.scale.set(0.85 + 0.3 * k, 0.8 + 0.3 * k, 0.85 + 0.3 * k); b.outer.material.opacity = (0.3 + 0.3 * k) * fl; b.inner.material.opacity = (0.55 + 0.4 * k) * fl;
    });
    this.corona[0].material.opacity = 0.07 + 0.015 * Math.sin(t * 3.3 + 1); this.corona[1].material.opacity = 0.035 + 0.01 * Math.sin(t * 2.1);
    this.heart.children[0].scale.setScalar(this.heartR * (1 + 0.08 * Math.sin(t * 4.2)));
    const fa = 0.53 + t * 0.05; this.coreFlare.position.set(Math.sin(fa) * 60, 0.3, Math.cos(fa) * 60);
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
  // the stars of light along the orbits: each rides its line and glints
  moveShips(t) {
    this.ships.forEach((s) => {
      const L = s.L, a = s.a + t * L.speed;
      s.head.position.set(Math.sin(a) * L.r, 0.2, Math.cos(a) * L.r);
      s.head.scale.setScalar(s.size * (0.85 + 0.15 * Math.sin(t * 3.1 + s.ph) * Math.sin(t * 1.7 + s.ph * 2)));
    });
  }
  // The banners follow their stations. Ours, the hovered one and Cymetica's always show; the rest nearest first,
  // each only where no nearer one stands, wholly inside the stage and clear of its bars, and only while its station
  // is big enough on screen to be worth a name. A plate stands on its station's top as the camera sees it: over the
  // mast from the side, past the edge of the deck from straight above, so it names the station from any angle
  // without covering it. Cymetica's stands on its sun the same way.
  overlay() {
    const w = this.el.clientWidth, h = this.el.clientHeight, v = new THREE.Vector3(), placed = [], now = performance.now();
    // a still camera moves no banner: restyle them only when the view, the size, the hover or a station changed
    const key = this.camera.matrixWorld.elements.join(',') + '|' + w + 'x' + h + '|' + this.hover + '|' + this.items.length + '|' + this.built + '|' + Math.floor(now / 66);
    if (key === this.ovKey && !this.pops.length) return;
    this.ovKey = key;
    // the stage's own bars (the count, the zoom buttons, the legend) are drawn over the plates: a plate under one is
    // a plate cut in half. Where they are, read again once a second (they move only with the stage and the font).
    if (!this.bars || now - this.barsAt > 1000) {
      const S = this.stage.getBoundingClientRect();
      this.bars = Array.prototype.map.call(this.stage.querySelectorAll('.top > *, .uvlegend'), (e) => e.getBoundingClientRect())
        .filter((b) => b.width && b.height).map((b) => ({ l: b.left - S.left, r: b.right - S.left, t: b.top - S.top, b: b.bottom - S.top }));
      this.barsAt = now;
    }
    // the plates are his size on his 820-high frame, and grow and shrink with the stage as his picture would
    const f = h / (2 * Math.tan(THREE.MathUtils.degToRad(this.camera.fov) / 2)), cam = this.camera.position, bs = Math.max(0.8, Math.min(1.35, h / 820));
    // the camera's up in the world: a plate is lifted along it, so it is "above" on the screen whatever the angle.
    // Seen from his first look's height or lower, a station's top is its mast (the lift is the mast's height as
    // the camera sees it); looking further down, its deck shows round the mast, so the plate moves out to the
    // deck's edge (a little over half the station's reach: the solar wings beyond it are thin, a plate may cross them).
    const up = (this._up || (this._up = new THREE.Vector3())).setFromMatrixColumn(this.camera.matrixWorld, 1).normalize();
    const c = new THREE.Vector3(), dir = new THREE.Vector3(), cH = Math.cos(UVCAM.polar);
    // Cymetica's painted ball over its heart, as wide as the ball there: the heart and a point a ball's radius to
    // its side on the screen; the painting is 600 px with the ball 360 across in its middle (colliderTex)
    if (this.colEl) {
      const right = (this._rt || (this._rt = new THREE.Vector3())).setFromMatrixColumn(this.camera.matrixWorld, 0).normalize();
      v.copy(this.heartAt).project(this.camera);
      const off = v.z > 1, x = (v.x + 1) / 2 * w, y = (1 - v.y) / 2 * h;
      c.copy(this.heartAt).addScaledVector(right, UVSUN.disc * UVSUN.k).project(this.camera);
      const s = Math.abs(c.x - v.x) * w / 360;
      if (this.colEl._off !== off) { this.colEl._off = off; this.colEl.style.display = off ? 'none' : ''; }
      if (!off) this.colEl.style.transform = 'translate(' + (x - 300).toFixed(1) + 'px,' + (y - 300).toFixed(1) + 'px) scale(' + s.toFixed(4) + ')';
    }
    const list = this.items.filter((it) => it.plot).map((it) => {
      const p = it.plot, hh = (p.top - p.bot) / 2 * UVSS;
      c.copy(p.root.position); c.y += (p.top + p.bot) / 2 * UVSS;
      const cos = Math.max(0, Math.min(1, dir.copy(cam).sub(c).normalize().y)), sin = Math.sqrt(1 - cos * cos);
      const lift = (hh + 0.5 * UVSS) * sin + p.b.foot * 0.55 * UVSS * Math.max(0, (cos - cH) / (1 - cH));
      it.plateAt = (it.plateAt || new THREE.Vector3()).copy(c).addScaledVector(up, lift);
      v.copy(it.plateAt).project(this.camera); const d = cam.distanceTo(it.anchor);
      return { el: it.el, x: (v.x + 1) / 2 * w, y: (1 - v.y) / 2 * h, z: v.z, d, px: it.size * f / d, mine: it.mine, keep: it.mine || String(this.hover) === String(it.c.id) };
    });
    if (this.coreEl) {
      c.copy(this.heartAt).addScaledVector(up, this.sunR * 0.9); v.copy(c).project(this.camera);
      list.push({ el: this.coreEl, x: (v.x + 1) / 2 * w, y: (1 - v.y) / 2 * h, z: v.z, d: cam.distanceTo(this.heartAt), px: 200, keep: true, core: true });
    }
    list.sort((a, b) => (b.keep - a.keep) || a.d - b.d);
    // a galaxy with a name on every star reads as a list: at most this many names besides ours, Cymetica and the hovered
    let named = 0;
    list.forEach((o) => {
      const el = o.el; if (!el) return;
      if (!el._bw) el._bw = el.offsetWidth || 160;
      const s = bs * (o.core ? 1 : Math.max(0.86, Math.min(1, 0.6 + o.px / 120)));
      const off = o.z > 1 || o.x < -80 || o.x > w + 80 || o.y < -40 || o.y > h + 60;
      const bw = el._bw * s, bh = (o.mine ? 50 : o.core ? 42 : 32) * s;
      // one that must show is slid along the edge to stay whole; any other shows whole or not at all
      if (o.keep) o.x = Math.max(bw / 2 + 4, Math.min(w - bw / 2 - 4, o.x));
      const r = { l: o.x - bw / 2, r: o.x + bw / 2, t: o.y - bh, b: o.y };
      const hit = (p) => r.l < p.r + 6 && r.r > p.l - 6 && r.t < p.b + 4 && r.b > p.t - 4;
      const whole = r.l >= 2 && r.r <= w - 2 && r.t >= 2 && r.b <= h - 2;
      const show = !off && (o.keep || (whole && !placed.some(hit) && !this.bars.some(hit) && o.px >= 24 && named < 14));
      if (show && !o.keep) named++;
      el.classList.toggle('hidden', !show); el._placed = true;
      if (show) placed.push(r);
      el.style.transform = 'translate(' + o.x.toFixed(1) + 'px,' + o.y.toFixed(1) + 'px) translate(-50%,-100%) scale(' + s.toFixed(3) + ')';
      el.style.zIndex = String(o.keep ? 3000 : 2000 - Math.round(o.d));
    });
    // an ET10 pop rises over its station's plate, wherever the plate now stands
    this.pops.forEach((p) => {
      v.copy(p.it.plateAt || p.it.anchor).project(this.camera);
      p.el.style.transform = 'translate(' + ((v.x + 1) / 2 * w).toFixed(1) + 'px,' + ((1 - v.y) / 2 * h - 46).toFixed(1) + 'px) translate(-50%,-100%)';
      p.el.style.visibility = '';
    });
  }

  /* ---------------- input ---------------- */
  bind() {
    const cv = this.renderer.domElement;
    let down = null;
    cv.addEventListener('pointerdown', (e) => { down = { x: e.clientX, y: e.clientY }; this.lastUse = this.lastInput = performance.now(); });
    cv.addEventListener('pointermove', (e) => { this.setMouse(e); this.mouseMoved = true; this.lastEv = e; this.lastInput = performance.now(); });
    cv.addEventListener('pointerenter', () => { this.mouseIn = true; });
    cv.addEventListener('pointerleave', () => { this.mouseIn = false; this.setHover(null); this.hideTip(); });
    cv.addEventListener('pointerup', (e) => {
      if (!down) return;
      const moved = Math.abs(e.clientX - down.x) + Math.abs(e.clientY - down.y) > 5; down = null;
      if (moved) return;
      this.setMouse(e); const id = this.pickId();
      if (id != null && id !== 'core') this.open(id);
    });
    cv.addEventListener('wheel', () => { this.tw = null; this.lastUse = this.lastInput = performance.now(); }, { passive: true });
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
const STC = { working: 0x24e8ff, queued: 0x3b82f6, waiting: 0xff8824, idle: 0x38f2b8 };
const TONEC = { cyan: '#24e8ff', red: '#ff9438', blue: '#dfe6ee', dim: '#a9b8cc' };
const OFFICE = { bg: 0x040b14, lamp: 0xa8e8f8, mon: 0x58ffc0 };
const WH = 1.4;   // the glass walls' height: his picture's corners put their top rail at 1.4 over the floor
const OM = {};
// The home view the operator set by hand and sent (2026-10-19, "zakladni view dej vice seshora a oddal ho tak jak
// posilam"): more from above and further out than his render. Recovered from seven landmarks of his screenshot --
// three room corners at the top rail, two at the floor, the League's front foot, the Manager's core -- by fitting a
// perspective camera at the render's lens (rms 1.4 px over 2020 x 1168): straight down the diagonal (45 degrees),
// 47 degrees off the vertical (the render's was 53). BOX and MID are where the platform's bounds sit in the frame
// (NDC); with the vault filling the corner his screenshot left empty, a little further out than his so the whole
// platform stays in the frame. home() keeps those at any stage size.
const CAM = { polar: 0.8198, az: 0.7854, fov: 30.94, box: [1.3, 1.74], mid: [0.02, -0.02] };
// His picture's colours, read off it (sRGB): the mint of a neon line's core and its halo, the sky between the stars.
const LOOK = { neon: '#7cf2c4', orange: '#ff8a3a', sky: 0x16232f };

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
    let den = edge * sstep(0.28, 0.65, n);
    den *= 1 - 0.55 * sstep(0.5, 0.72, f2(x * 4.5 + 2, y * 4.5 + 7, 4));
    const hh = sstep(0.54, 0.78, n) * edge, k = (j * N + i) * 4;
    for (let ch = 0; ch < 3; ch++) d[k + ch] = Math.min(255, deep[ch] + (mid[ch] - deep[ch]) * den + hi[ch] * hh);
    d[k + 3] = Math.min(255, (den * 1.15 + hh * 0.75) * 255);
  }
  g.putImageData(img, 0, 0);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; TX[key] = t; return t;
}
function starTex() {
  return TX.star || (TX.star = ctex(64, 64, (g) => {
    const gr = g.createRadialGradient(32, 32, 0, 32, 32, 32);
    gr.addColorStop(0, 'rgba(255,255,255,1)'); gr.addColorStop(0.12, 'rgba(235,252,255,.95)'); gr.addColorStop(0.32, 'rgba(130,225,255,.28)'); gr.addColorStop(1, 'rgba(130,225,255,0)');
    g.fillStyle = gr; g.fillRect(0, 0, 64, 64);
  }));
}
// a nebula as the office's picture has it: thin teal filaments and a few denser knots, most of it dark between --
// nebTex's soft clouds, kept for the Universe, read as a haze over the whole office sky
function filamentTex(seed) {
  const key = 'fil' + seed; if (TX[key]) return TX[key];
  const N = 384, f = vnoise(seed), f2 = vnoise(seed + 5), c = document.createElement('canvas'); c.width = c.height = N;
  const g = c.getContext('2d'), img = g.createImageData(N, N), d = img.data;
  for (let j = 0; j < N; j++) for (let i = 0; i < N; i++) {
    const x = i / N * 2 - 1, y = j / N * 2 - 1, rr = Math.sqrt(x * x + y * y); if (rr > 1.02) continue;
    const edge = sstep(1.0, 0.25, rr + 0.45 * (f(x * 1.4 + 2, y * 1.4 + 5, 3) - 0.5)); if (edge <= 0) continue;
    const q = f(x * 2.4 + 1.3, y * 2.4 + 7.7, 4), n = f(x * 4.6 + q * 3.0, y * 4.6 + q * 3.0 + 1.9, 5);
    const ridge = 1 - Math.abs(n - 0.5) * 2;                      // the filaments: where the field crosses its middle
    const patch = sstep(0.42, 0.68, f2(x * 1.6 + 4, y * 1.6 + 1, 3));   // and only in some patches of it
    let den = edge * Math.pow(Math.max(0, ridge), 7) * patch * 0.9;
    const knot = edge * patch * (0.1 + 0.3 * sstep(0.6, 0.85, f2(x * 4 + 9, y * 4 + 3, 4)));   // the haze they sit in
    den = Math.min(1, den + knot);
    const k = (j * N + i) * 4; d[k] = 40 + 60 * den; d[k + 1] = 150 + 60 * den; d[k + 2] = 160 + 50 * den; d[k + 3] = den * 255;
  }
  // soft, as gas is: the filaments over a blurred copy of themselves
  const sharp = document.createElement('canvas'); sharp.width = sharp.height = N; sharp.getContext('2d').putImageData(img, 0, 0);
  g.clearRect(0, 0, N, N); g.filter = 'blur(5px)'; g.drawImage(sharp, 0, 0); g.drawImage(sharp, 0, 0); g.filter = 'blur(1px)'; g.globalAlpha = 0.7; g.drawImage(sharp, 0, 0);
  g.filter = 'none'; g.globalAlpha = 1;
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; TX[key] = t; return t;
}
// The sky: nebulae and stars round the camera. The Universe keeps its rich clouds; the office (office = true) has
// his picture's: a teal nebula of filaments where the home view's sky shows it, stars thick and white.
function spaceSky(office) {
  const g = new THREE.Group(), R = rng(31), D = 380;
  const PAL = {
    teal: [[2, 44, 68], [12, 134, 166], [110, 242, 252]],
    cyan: [[4, 34, 60], [16, 112, 156], [90, 222, 248]],
    blue: [[6, 26, 72], [24, 88, 178], [120, 195, 255]],
    green: [[2, 48, 58], [14, 138, 136], [95, 240, 215]]
  };
  // The office's home view looks 37 degrees down, so the sky it shows is the band from about -51 to -21 degrees;
  // his picture's teal nebula sits at its top left (about -20 azimuth, -28 elevation), knots and wisps round it, a
  // faint one top right, a fainter one low on the left. The last ones are for a camera turned elsewhere.
  const OFFICE_NEB = [[-21, -27, 13, 8, 0.3], [-13, -31, 8, 19, 0.18], [-28, -22, 9, 3, 0.2], [-24, -35, 7, 23, 0.12],
    [16, -23, 12, 13, 0.1], [-32, -46, 12, 37, 0.08], [-32, 8, 60, 41, 0.5], [150, -15, 70, 17, 0.4], [95, 5, 50, 29, 0.3], [-130, -30, 60, 31, 0.4]];
  const UV_NEB = [[-32, 8, 72, 8, 0.72, 'teal'], [-54, -8, 62, 3, 0.62, 'cyan'], [-12, 14, 56, 19, 0.38, 'teal'],
    [32, -22, 64, 13, 0.45, 'cyan'], [52, -32, 56, 37, 0.35, 'teal'], [150, -15, 80, 17, 0.55, 'teal'], [95, -35, 60, 23, 0.35, 'green'], [-130, -30, 70, 29, 0.45, 'blue']];
  (office ? OFFICE_NEB : UV_NEB).forEach(([az, el, size, seed, op, tone]) => {
    const m = new THREE.Mesh(G.plane, new THREE.MeshBasicMaterial({ map: office ? filamentTex(seed) : nebTex(seed, ...PAL[tone]), transparent: true, opacity: op, blending: THREE.AdditiveBlending, depthWrite: false, fog: false }));
    const s = 2 * D * Math.tan(size * Math.PI / 360);
    m.scale.set(s, s, 1); m.position.copy(skyDir(az, el).multiplyScalar(D)); m.lookAt(0, 0, 0); m.rotateZ(R() * 6.28); m.renderOrder = -10; m.frustumCulled = false; g.add(m);
  });
  const rnd = () => { const u = R() * 2 - 1, th = R() * Math.PI * 2, s = Math.sqrt(1 - u * u); return new THREE.Vector3(Math.cos(th) * s, u, Math.sin(th) * s); };
  // his sky is full of small white stars (about one per 2,400 pixels of sky), a few of them bright
  const N = office ? 22000 : 4600, pos = new Float32Array(N * 3), col = new Float32Array(N * 3), cc = new THREE.Color();
  for (let i = 0; i < N; i++) {
    pos.set(rnd().multiplyScalar(360).toArray(), i * 3);
    if (office) cc.set(R() < 0.18 ? 0xb8e8ff : 0xf2f8ff).multiplyScalar(0.8 + R() * R() * 2.2);
    else cc.set(R() < 0.22 ? 0x88ecff : R() < 0.32 ? 0x78ffd6 : 0xf0f7ff).multiplyScalar(0.35 + R() * R() * 1.35);
    col.set([cc.r, cc.g, cc.b], i * 3);
  }
  const pg = new THREE.BufferGeometry(); pg.setAttribute('position', new THREE.BufferAttribute(pos, 3)); pg.setAttribute('color', new THREE.BufferAttribute(col, 3));
  pg.setAttribute('normal', new THREE.BufferAttribute(new Float32Array(N * 3).map((v, i) => (i % 3 === 1 ? 1 : 0)), 3));
  const pts = new THREE.Points(pg, new THREE.PointsMaterial({ vertexColors: true, size: 1, sizeAttenuation: false, fog: false, depthWrite: false })); pts.frustumCulled = false; g.add(pts);
  const B = office ? 2600 : 360, im = new THREE.InstancedMesh(G.plane, new THREE.MeshBasicMaterial({ map: starTex(), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, fog: false }), B), o = new THREE.Object3D();
  for (let i = 0; i < B; i++) {
    // at the office's home distance a sky unit is about 0.7 px: his stars are 1 to 3 px points with a soft halo
    o.position.copy(rnd().multiplyScalar(350)); o.lookAt(0, 0, 0); o.scale.setScalar(office ? 0.7 + R() * R() * 1.1 : 1.0 + R() * R() * 3.1); o.updateMatrix(); im.setMatrixAt(i, o.matrix);
    im.setColorAt(i, office ? cc.set(R() < 0.2 ? 0xc8eeff : 0xffffff).multiplyScalar(1.0 + R() * 1.3) : cc.set(R() < 0.25 ? 0x8ef0ff : 0xffffff).multiplyScalar(0.65 + R() * 0.85));
  }
  im.frustumCulled = false; g.add(im);
  return g;
}
// what shiny surfaces see: a dark room with soft panels of light overhead and a cyan one low on a side
// What shiny surfaces see: a studio -- grey walls, a lit ceiling with soft white panels, a dark floor -- so metal,
// glass and floors catch neutral highlights, as in his render (the downloaded HDR it replaces is gone)
function envTex() {
  if (TX.env) return TX.env;
  const t = ctex(512, 256, (g, W, H) => {
    const gr = g.createLinearGradient(0, 0, 0, H); gr.addColorStop(0, '#8a96a4'); gr.addColorStop(0.45, '#3a4552'); gr.addColorStop(0.55, '#222a33'); gr.addColorStop(1, '#0b0f14'); g.fillStyle = gr; g.fillRect(0, 0, W, H);
    [[0.1, 0.12, 0.2, 0.09, 'rgba(255,255,255,.95)'], [0.45, 0.08, 0.24, 0.08, 'rgba(250,252,255,.9)'], [0.78, 0.15, 0.14, 0.1, 'rgba(235,245,255,.8)'], [0.3, 0.33, 0.12, 0.08, 'rgba(210,225,240,.5)']].forEach(([x, y, w, h, c]) => {
      g.fillStyle = c; g.filter = 'blur(8px)'; g.fillRect(x * W, y * H, w * W, h * H); g.filter = 'none';
    });
  });
  t.mapping = THREE.EquirectangularReflectionMapping; TX.env = t; return t;
}

/* ---------------- the office's surfaces ---------------- */
// the deck between the rooms, as his: smooth dark slate, large panels with hairline joints
function deckTex() {
  return TX.deck || (TX.deck = ctex(512, 512, (g, W) => {
    const R = rng(23), s = W / 2;
    g.fillStyle = '#121b25'; g.fillRect(0, 0, W, W);
    for (let i = 0; i < 2; i++) for (let j = 0; j < 2; j++) {
      const v = Math.floor(R() * 3);
      g.fillStyle = 'rgb(' + (27 + v) + ',' + (37 + v) + ',' + (48 + v) + ')';
      g.fillRect(i * s + 1, j * s + 1, s - 2, s - 2);
    }
  }));
}
// a room's floor: large slate-blue tiles (his picture's floors read #304a55 lit), hairline seams
function tileTex() {
  return TX.tile || (TX.tile = ctex(512, 512, (g, W) => {
    const R = rng(29), s = W / 4;
    // lit, it reads as his floors do (#334754 to #293a4a, measured on bare floor in both pictures)
    g.fillStyle = '#1c2a36'; g.fillRect(0, 0, W, W);
    for (let i = 0; i < 4; i++) for (let j = 0; j < 4; j++) {
      const v = Math.floor(R() * 4);
      g.fillStyle = 'rgb(' + (36 + v) + ',' + (52 + v) + ',' + (65 + v) + ')';
      g.fillRect(i * s + 1.5, j * s + 1.5, s - 3, s - 3);
    }
  }));
}
// The hull's side as in his picture: navy plating with a lighter band along the top and a dark chamfer at the foot,
// seams between its plates, a plate or two a shade apart, navy bays with grilles, a hatch. His silver modules stand
// out from it, so they are boxes of their own (exterior()), not paint. One side of a room's hull is 8 units, the
// texture's width; it repeats round the station, so each side starts it at its own offset (exHullBox) and nothing
// in it lines up at the wrap.
function hullTex() {
  if (TX.hull) return TX.hull;
  const W = 1024, H = 212;
  const plate = (g, x, y, w, h, glow, c) => { if (glow) return; g.fillStyle = c; g.fillRect(x, y, w, h); g.fillStyle = '#34425a'; g.fillRect(x, y, w, 2); };
  const bay = (g, x, y, w, h, glow) => {
    if (glow) return;
    g.fillStyle = '#1d2b47'; g.fillRect(x, y, w, h);
    g.strokeStyle = '#2c3b56'; g.lineWidth = 2; g.strokeRect(x + 1, y + 1, w - 2, h - 2);
    g.fillStyle = '#0c1322'; for (let k = x + 10; k < x + w - 10; k += 10) g.fillRect(k, y + 14, 5, h - 28);
  };
  const draw = (glow) => (g) => {
    g.fillStyle = glow ? '#000000' : '#273346'; g.fillRect(0, 0, W, H);
    if (!glow) {
      g.fillStyle = '#69747f'; g.fillRect(0, 0, W, 20); g.fillStyle = '#8a95a1'; g.fillRect(0, 0, W, 3); g.fillStyle = '#121925'; g.fillRect(0, 20, W, 3);
      g.fillStyle = '#121a26'; g.fillRect(0, H - 24, W, 24); g.fillStyle = '#26324a'; g.fillRect(0, H - 24, W, 2);
      [0, 96, 352, 470, 640, 812, 930].forEach((x) => { g.fillStyle = '#121a27'; g.fillRect(x, 23, 2, H - 47); g.fillStyle = '#2a3750'; g.fillRect(x + 2, 23, 1, H - 47); });
      // a hatch: a rounded square outline with two bolts
      g.strokeStyle = '#33415a'; g.lineWidth = 3; g.beginPath(); g.roundRect(842, 58, 64, 92, 10); g.stroke();
      g.fillStyle = '#4a5870'; g.fillRect(852, 66, 6, 6); g.fillRect(890, 136, 6, 6);
    }
    plate(g, 98, 30, 252, 150, glow, '#2b384c'); plate(g, 642, 30, 168, 150, glow, '#222d3f');
    bay(g, 488, 52, 138, 104, glow);
    bay(g, 14, 60, 70, 92, glow);
    // small lights along the top band
    [[260, '#9fe8ff'], [742, '#7cf2c4']].forEach(([x, c]) => { g.fillStyle = glow ? c : '#3a4a5a'; g.fillRect(x, 8, 26, 5); });
  };
  TX.hull = ctex(W, H, draw(false)); TX.hullGlow = ctex(W, H, draw(true));
  TX.hull.wrapS = TX.hullGlow.wrapS = THREE.RepeatWrapping;
  return TX.hull;
}
// a box like G.box whose four sides start the hull texture at their own offsets (k picks the set), so the modules
// do not repeat in step round the station
function exHullBox(k) {
  const key = 'exHullBox' + k;
  if (G[key]) return G[key];
  const g = G.box.clone(), uv = g.attributes.uv;
  [0, 1, 4, 5].forEach((f, i) => { const o = ((k * 3 + i * 5) % 8) / 8; for (let v = f * 4; v < f * 4 + 4; v++) uv.setX(v, uv.getX(v) + o); });
  return (G[key] = g);
}
// His racks' doors, zoomed: a dark door in a lighter frame, a label and a small display at its head, fourteen units
// behind it -- 1U servers with a short cyan bar of light at their left and a grille, rows of drive caddies with a
// light under the busy ones, a switch with its ports, perforated blanks -- and a grille along its foot. Every light is
// in the emissive map; racks() blinks a few more where the door has none lit (rackTex.leds: where, as fractions of it).
function rackTex() {
  if (TX.rack) return TX.rack;
  const W = 256, H = 512, R = rng(53), plan = 'sdsbswsdsbsdss', top = 36, uh = (H - top - 44) / plan.length;
  const lit = Array.from(plan, () => Array.from({ length: 8 }, () => R()));
  rackTex.leds = [];
  Array.from(plan).forEach((t, i) => {
    if (t === 'd') for (let k = 0; k < 8; k++) if (lit[i][k] >= 0.42 && lit[i][k] < 0.7) rackTex.leds.push([(26 + k * (W - 40) / 8) / W, (top + i * uh + uh - 8.5) / H]);
    if (t === 's' && lit[i][0] <= 0.4) rackTex.leds.push([(W - 21.5) / W, (top + i * uh + (uh - 3) / 2) / H]);
  });
  const draw = (glow) => (g) => {
    g.fillStyle = glow ? '#000000' : '#161d25'; g.fillRect(0, 0, W, H);
    if (!glow) {
      g.fillStyle = '#353f4a'; g.fillRect(0, 0, W, 10); g.fillRect(0, H - 10, W, 10); g.fillRect(0, 0, 10, H); g.fillRect(W - 10, 0, 10, H);
      g.fillStyle = '#4c5966'; g.fillRect(0, 0, W, 3); g.fillRect(0, 0, 3, H);
      g.fillStyle = '#212a34'; g.fillRect(16, 14, W - 32, 17); g.fillStyle = '#5c6976'; g.fillRect(22, 19, 64, 7);
    }
    g.fillStyle = glow ? 'rgba(36,232,255,.5)' : '#1d5e6a'; g.fillRect(W - 76, 17, 50, 11);
    Array.from(plan).forEach((t, i) => {
      const y = top + i * uh, h = uh - 3, L = lit[i];
      if (!glow) { g.fillStyle = '#222b35'; g.fillRect(16, y, W - 32, h); g.fillStyle = '#0c1116'; g.fillRect(16, y + h, W - 32, 2); }
      if (t === 'd') {
        // eight drive caddies, a light at the foot of the busy ones
        const cw = (W - 40) / 8;
        for (let k = 0; k < 8; k++) {
          const x = 20 + k * cw;
          if (!glow) { g.fillStyle = '#2e3843'; g.fillRect(x, y + 3, cw - 4, h - 5); g.fillStyle = '#151b22'; for (let s = y + 6; s < y + h - 10; s += 3) g.fillRect(x + 3, s, cw - 10, 1); }
          g.fillStyle = L[k] < 0.3 ? (glow ? 'rgba(56,245,184,.8)' : '#2a8a6c') : L[k] < 0.42 ? (glow ? 'rgba(36,232,255,.8)' : '#1f7f90') : (glow ? '#000000' : '#1a242e');
          g.fillRect(x + 3, y + h - 7, 7, 3);
        }
      } else if (t === 's') {
        // a server: a short cyan bar of light at its left, a grille, its status lights at the end
        g.fillStyle = glow ? (L[1] < 0.75 ? 'rgba(90,225,240,.7)' : 'rgba(150,205,255,.5)') : '#3d7480'; g.fillRect(22, y + h / 2 - 2, 30 + Math.round(L[2] * 14), 4);
        if (!glow) { g.fillStyle = '#111820'; for (let x = 72; x < W * 0.8; x += 5) g.fillRect(x, y + 4, 2, h - 7); }
        g.fillStyle = glow ? 'rgba(36,232,255,.75)' : '#1f7f90'; g.fillRect(W - 36, y + h / 2 - 3, 7, 5);
        if (L[0] > 0.4) { g.fillStyle = glow ? 'rgba(56,245,184,.75)' : '#2a8a6c'; g.fillRect(W - 25, y + h / 2 - 3, 7, 5); }
      } else if (t === 'w') {
        // a switch: two rows of ports, a light over each one that is linked
        for (let k = 0; k < 12; k++) for (let row = 0; row < 2; row++) {
          const x = 22 + k * 17.5, yy = y + 3 + row * (h / 2);
          if (!glow) { g.fillStyle = '#05080b'; g.fillRect(x, yy + 3, 12, h / 2 - 6); }
          if (L[(k + row * 3) % 8] > 0.55) { g.fillStyle = glow ? '#38f5b8' : '#2a8a6c'; g.fillRect(x + 1, yy, 5, 2); }
        }
      } else if (!glow) {
        g.fillStyle = '#0c1217'; for (let x = 22; x < W - 22; x += 6) for (let s = y + 4; s < y + h - 3; s += 5) g.fillRect(x, s, 2, 2);
      }
    });
    if (!glow) { g.fillStyle = '#0a0f14'; for (let x = 18; x < W - 18; x += 6) g.fillRect(x, H - 36, 3, 22); }
  };
  TX.rack = ctex(W, H, draw(false)); TX.rackGlow = ctex(W, H, draw(true)); return TX.rack;
}
// the office's solar panels as in his picture: deep navy cells with pale grid lines in a light frame (#233561 lit,
// #6c7ea4 at the lines); the Universe's stations keep their brighter ones (solarTex)
function officeSolarTex() {
  return TX.osolar || (TX.osolar = ctex(256, 320, (g, W, H) => {
    g.fillStyle = '#9aaac0'; g.fillRect(0, 0, W, H);
    const nx = 4, ny = 5, sx = (W - 12) / nx, sy = (H - 12) / ny;
    for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++) {
      const x = 6 + i * sx, y = 6 + j * sy, gr = g.createLinearGradient(x, y, x + sx, y + sy);
      gr.addColorStop(0, '#26427e'); gr.addColorStop(1, '#172a5a'); g.fillStyle = gr; g.fillRect(x + 1.5, y + 1.5, sx - 3, sy - 3);
      g.strokeStyle = 'rgba(170,195,235,.35)'; g.lineWidth = 1;
      g.beginPath(); g.moveTo(x + sx / 2, y + 2); g.lineTo(x + sx / 2, y + sy - 2); g.moveTo(x + 2, y + sy / 2); g.lineTo(x + sx - 2, y + sy / 2); g.stroke();
    }
  }));
}
function solarTex() {
  return TX.solar || (TX.solar = ctex(256, 256, (g, W) => {
    g.fillStyle = '#5c82a8'; g.fillRect(0, 0, W, W);
    const n = 4, s = (W - 12) / n;
    for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
      const x = 6 + i * s, y = 6 + j * s, gr = g.createLinearGradient(x, y, x + s, y + s);
      gr.addColorStop(0, '#1e5cc4'); gr.addColorStop(1, '#103478'); g.fillStyle = gr; g.fillRect(x + 2, y + 2, s - 4, s - 4);
      g.strokeStyle = 'rgba(130,210,255,.52)'; g.lineWidth = 1.2;
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
function asteroidGeo(seed, detail = 64, flatTop = true) {
  let g = new THREE.IcosahedronGeometry(1, detail);
  g.deleteAttribute('normal'); g.deleteAttribute('uv'); g = mergeVertices(g);
  const P = perlin3(seed), pos = g.attributes.position, v = new THREE.Vector3(), n = pos.count, col = new Float32Array(n * 3), R = rng(seed + 7);
  const fbm = (x, y, z, o) => { let s = 0, a = 0.5, f = 1; for (let i = 0; i < o; i++) { s += a * P(x * f, y * f, z * f); a *= 0.5; f *= 2.03; } return s; };
  const ridge = (x, y, z, o) => { let s = 0, a = 0.5, f = 1; for (let i = 0; i < o; i++) { const r = 1 - Math.abs(P(x * f + 31.7, y * f + 7.1, z * f)); s += a * r * r; a *= 0.5; f *= 2.1; } return s; };
  const craters = [];
  for (let i = 0; i < 30; i++) craters.push({ c: new THREE.Vector3(R() * 2 - 1, R() * 2 - 1, R() * 2 - 1).normalize(), r: 0.05 + Math.pow(R(), 2.2) * 0.3, d: 0.35 + R() * 0.45 });
  // his rock is a dark slate grey, lit on its faces (#232b37 to #474d5b), not a black mass and not a pale one
  const dark = [0.012, 0.016, 0.024], mid = [0.032, 0.04, 0.054], light = [0.075, 0.085, 0.105];
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
    const t = Math.max(0, Math.min(1, 0.5 + h * 1.4 + 0.35 * fbm(v.x * 6 + 11, v.y * 6, v.z * 6, 3) - pit * 0.35));
    const s = R() < 0.04 ? 0.35 : 0, a = t < 0.5 ? t * 2 : (t - 0.5) * 2, lo = t < 0.5 ? dark : mid, hi = t < 0.5 ? mid : light;
    for (let ch = 0; ch < 3; ch++) col[i * 3 + ch] = lo[ch] + (hi[ch] - lo[ch]) * a + s * light[ch];
  }
  g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  g.computeVertexNormals();
  return g;
}
// The rock the station is built on, as his picture has it: a craggy mass hanging below the hull like an upturned
// mountain. Real broken rock is planes meeting at sharp edges, so it is cut: a sphere sliced by many random planes
// (each point pulled in to the nearest plane), which leaves large faces that catch the light and an angular outline;
// then roughened by ridged noise, so the faces are rock and not cut stone. Below its top it swells out before it
// narrows to the point, so its outline overhangs as his does. His rock is a dark blue-grey (#10 to #19 in the
// middle) whose ridges catch the light, so the colour is baked per vertex: each face its own tone, the hollows of
// the ridges near black, darker deep underneath. flat: cut flat on top, where it meets the keel; drop: how far the
// bottom hangs, in its own radii; swell: how far it bulges out below the top.
function exRockGeo(seed, detail, drop, flat, swell = 0.2) {
  let g = new THREE.IcosahedronGeometry(1, detail);
  g.deleteAttribute('normal'); g.deleteAttribute('uv'); g = mergeVertices(g);
  const P = perlin3(seed), pos = g.attributes.position, v = new THREE.Vector3(), n = pos.count, R = rng(seed + 3);
  const fbm = (x, y, z, o) => { let s = 0, a = 0.5, f = 1; for (let i = 0; i < o; i++) { s += a * P(x * f, y * f, z * f); a *= 0.5; f *= 2.03; } return s; };
  const ridge = (x, y, z, o) => { let s = 0, a = 0.5, f = 1; for (let i = 0; i < o; i++) { const r = 1 - Math.abs(P(x * f + 31.7, y * f + 7.1, z * f)); s += a * r * r; a *= 0.5; f *= 2.1; } return s; };
  const cuts = [];
  for (let i = 0; i < 64; i++) {
    const c = new THREE.Vector3(R() * 2 - 1, R() * 2 - 1, R() * 2 - 1).normalize();
    cuts.push({ c, d: 0.58 + R() * 0.4, tone: 0.45 + R() * 1.1 });
  }
  const tone = new Float32Array(n), cav = new Float32Array(n);
  for (let i = 0; i < n; i++) {
    v.fromBufferAttribute(pos, i);
    let r = 1 + 0.22 * fbm(v.x * 1.3, v.y * 1.3, v.z * 1.3, 3), tn = 0.85;
    for (const k of cuts) { const dd = v.dot(k.c); if (dd > 0.05 && k.d / dd < r) { r = k.d / dd; tn = k.tone; } }
    const rg = ridge(v.x * 2.4, v.y * 2.4, v.z * 2.4, 3) - 0.42;
    r *= 1 + 0.13 * rg;
    tone[i] = tn; cav[i] = rg;
    let x = v.x * r, y = v.y * r, z = v.z * r;
    if (flat && y > 0.22) y = 0.22 + (y - 0.22) * 0.08;
    else if (y < 0.22) {
      const d = (0.22 - y) * drop, t = Math.min(1, d / (1.25 * drop)), k = 1 + swell * Math.sin(Math.PI * Math.min(1, t * 1.6)) - 0.34 * t * t;
      y = 0.22 - d; x *= k; z *= k;
    }
    pos.setXYZ(i, x, y, z);
  }
  g.computeVertexNormals();
  // faces turned up catch the sun and go light, faces turned down sit in the station's shadow and go dark
  const col = new Float32Array(n * 3), lo = -1.25 * drop, nr = g.attributes.normal;
  for (let i = 0; i < n; i++) {
    let k = Math.pow(tone[i], 1.8) * (0.06 + 1.4 * Math.pow(sstep(-0.26, 0.16, cav[i]), 1.5)) + 0.03 * (R() - 0.5);
    k *= (1 - 0.6 * sstep(0, lo, pos.getY(i))) * (0.28 + 1.0 * Math.pow(0.5 + 0.5 * nr.getY(i), 2));
    k = 0.55 * Math.pow(Math.max(0, k), 1.7);   // contrast: the middle sinks to near black, the ridges keep their light
    col[i * 3] = 0.03 * k; col[i * 3 + 1] = 0.034 * k; col[i * 3 + 2] = 0.045 * k;
  }
  g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  return g;
}
// his moonlet: a lumpy potato, softly cratered, light grey with darker plains -- a small moon, not a jagged rock
function exMoonGeo(seed) {
  let g = new THREE.IcosahedronGeometry(1, 22);
  g.deleteAttribute('normal'); g.deleteAttribute('uv'); g = mergeVertices(g);
  const P = perlin3(seed), pos = g.attributes.position, v = new THREE.Vector3(), n = pos.count, R = rng(seed + 5), col = new Float32Array(n * 3);
  const fbm = (x, y, z, o) => { let s = 0, a = 0.5, f = 1; for (let i = 0; i < o; i++) { s += a * P(x * f, y * f, z * f); a *= 0.5; f *= 2.03; } return s; };
  const craters = [];
  for (let i = 0; i < 46; i++) craters.push({ c: new THREE.Vector3(R() * 2 - 1, R() * 2 - 1, R() * 2 - 1).normalize(), r: 0.05 + Math.pow(R(), 2) * 0.3, d: 0.06 + R() * 0.08 });
  for (let i = 0; i < n; i++) {
    v.fromBufferAttribute(pos, i);
    let h = 0.32 * fbm(v.x * 0.75, v.y * 0.75, v.z * 0.75, 2) + 0.07 * fbm(v.x * 2.2, v.y * 2.2, v.z * 2.2, 2) + 0.01 * fbm(v.x * 9, v.y * 9, v.z * 9, 2);
    let tone = 0.85 + 1.9 * fbm(v.x * 1.6 + 4, v.y * 1.6, v.z * 1.6, 3) + 0.5 * fbm(v.x * 5 + 9, v.y * 5, v.z * 5, 2);
    for (const k of craters) {
      const x = Math.acos(Math.max(-1, Math.min(1, v.dot(k.c)))) / k.r;
      if (x < 1) { h -= k.r * k.d * (1 - x * x); tone -= 0.12 * (1 - x); }
      else if (x < 1.5) { h += k.r * k.d * 0.35 * Math.pow(1 - (x - 1) / 0.5, 2); tone += 0.1 * (1 - (x - 1) / 0.5); }
    }
    v.multiplyScalar(1 + h); v.y *= 0.86; v.x *= 1.14; pos.setXYZ(i, v.x, v.y, v.z);
    const t = Math.max(0.25, Math.min(1.4, tone)) * 0.2;
    col[i * 3] = t; col[i * 3 + 1] = t * 1.0; col[i * 3 + 2] = t * 1.04;
  }
  g.setAttribute('color', new THREE.BufferAttribute(col, 3));
  g.computeVertexNormals();
  return g;
}
/* ---- the station's outside: what its engines, thrusters and solar panels are built from ---- */
// His engines are gunmetal, not paint: a dark one for collars and bodies, a lighter one for the big engine's
// housing, near-black for ribs, mounts and lips, a bright chrome band on the back engines, gold fittings. All of
// them made once, on OM like the rest, so a layout reuses them.
function exMats() {
  if (OM.exGun) return;
  const ds = THREE.DoubleSide;
  OM.exGun = std({ color: 0x3c424b, roughness: 0.34, metalness: 0.78, side: ds });
  OM.exGunL = std({ color: 0x939ba6, roughness: 0.28, metalness: 0.76, side: ds });
  // the big engine's housing: his darker, bluish gunmetal, polished, so the studio's lights streak along it
  OM.exGunM = std({ color: 0x5f6e84, roughness: 0.3, metalness: 0.68, side: ds });
  // the hull's modules: light silver boxes standing out from the navy plating, a lit strip in each
  OM.exModule = std({ color: 0x8d97a4, roughness: 0.42, metalness: 0.55 });
  OM.exModuleD = std({ color: 0x0c121c, roughness: 0.35, metalness: 0.4 });
  OM.exStrip = emis('#8fc0f4', 1.6);
  OM.exGunD = std({ color: 0x14181e, roughness: 0.42, metalness: 0.6, side: ds });
  OM.exChrome = std({ color: 0xc4ccd5, roughness: 0.2, metalness: 0.9, side: ds });
  // the panels catch the studio's ceiling at a glancing angle; his never flare white, so they see less of it
  OM.exFrame = std({ color: 0x9aa4b0, roughness: 0.55, metalness: 0.5, envMapIntensity: 0.3 });
  OM.exSolar = std({ map: exSolarTex(), roughness: 0.62, metalness: 0.15, emissive: 0x122042, emissiveIntensity: 0.12, envMapIntensity: 0.12 });
  // his moonlet is lit from one side with a hard terminator; the office's fill light comes from the camera and
  // would light all of the face it shows, so it is lit by its own sun, fixed in the sky as it turns
  OM.exMoon = new THREE.MeshBasicNodeMaterial();
  const nd = TSL.dot(TSL.normalWorld, TSL.vec3(-0.8, 0.1, 0.3).normalize());   // from the left and a little behind: his terminator near the middle
  // its night side keeps a faint blue-grey fill, a shade lighter than the sky behind it, as his does (#0a0e12 there
  // against #050912), not a black hole
  OM.exMoon.colorNode = TSL.vertexColor().xyz.mul(TSL.smoothstep(-0.02, 0.3, nd).mul(1.1).add(0.06)).add(TSL.vec3(0.004, 0.006, 0.009));
  OM.exNoz = new THREE.MeshBasicMaterial({ map: exNozTex(false), toneMapped: false });
  OM.exNozT = new THREE.MeshBasicMaterial({ map: exNozTex(true), color: new THREE.Color(0xffffff).multiplyScalar(2.3), toneMapped: false });
  OM.exNozRim = new THREE.MeshBasicMaterial({ color: new THREE.Color(0x6ff4ff).multiplyScalar(2.6), toneMapped: false });
  OM.exNozB = new THREE.MeshBasicMaterial({ map: exNozTex(true), color: new THREE.Color(0x9cc0ff).multiplyScalar(1.8), toneMapped: false });
  OM.exLedG = emis('#7cf2c4', 2.2); OM.exLedC = emis('#9fe8ff', 2.2); OM.exCable = emis('#38f5b8', 0.9);
  // his plumes are soft: bright where they leave the nozzle, fading along their length AND toward their edges, so
  // the cone never shows a hard outline (the fade across is how square to the eye each point of it is)
  const plume = (hex, k) => {
    const m = new THREE.MeshBasicNodeMaterial({ transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, side: ds }), t = TSL.texture(plumeTex());
    const face = TSL.abs(TSL.dot(TSL.normalView, TSL.positionViewDirection));
    m.colorNode = TSL.vec3(...new THREE.Color(hex).toArray()).mul(t.rgb).mul(1.6); m.opacityNode = t.a.mul(face.mul(face)).mul(k); return m;
  };
  OM.exPlumeA = plume(0x3d6cff, 0.4); OM.exPlumeB = plume(0x9cc4ff, 0.4);
  const L = (pts) => new THREE.LatheGeometry(pts.map(([r, z]) => new THREE.Vector2(r, z)), 48);
  // profiles turned about the engine's axis, back (at the hull) to front (the nozzle), radius first
  G.exCollar = L([[0.45, 0.18], [0.84, 0.2], [0.9, 0.28], [0.9, 0.66], [0.84, 0.74], [0.6, 0.76]]);
  G.exHousing = L([[0.6, 1.04], [0.92, 1.06], [0.99, 1.12], [1.0, 1.2], [1.0, 2.35], [0.97, 2.43], [0.9, 2.45]]);
  G.exThrBody = L([[0.2, 0.4], [0.36, 0.44], [0.4, 0.52], [0.41, 0.6], [0.41, 0.98], [0.38, 1.04]]);
  G.exBackCap = L([[0.05, -0.12], [0.3, -0.1], [0.46, -0.02], [0.52, 0.1]]);
  G.exBell = L([[0.44, 0.92], [0.5, 1.02], [0.54, 1.12], [0.52, 1.16]]);
  G.exTube = new THREE.CylinderGeometry(1, 1, 1, 40, 1, true); G.exTube.rotateX(Math.PI / 2);
  G.exRod = new THREE.CylinderGeometry(1, 1, 1, 10); G.exRod.rotateX(Math.PI / 2);
  G.exTor = {}; [0.03, 0.06, 0.12].forEach((t) => { G.exTor[t] = new THREE.TorusGeometry(1, t, 10, 64); });
}
// his solar panels: deep blue cells, six across and eight down, with pale lines between them and a brighter
// divide across the middle, in a silver frame (the frame is drawn too, so it reads at any distance)
function exSolarTex() {
  return TX.exSolar || (TX.exSolar = ctex(240, 320, (g, W, H) => {
    g.fillStyle = '#aeb8c4'; g.fillRect(0, 0, W, H);
    g.fillStyle = '#5f6d88'; g.fillRect(4, 4, W - 8, H - 8);
    const nx = 7, ny = 10, x0 = 6, y0 = 6, cw = (W - 12) / nx, ch = (H - 12) / ny;
    for (let i = 0; i < nx; i++) for (let j = 0; j < ny; j++) {
      const x = x0 + i * cw, y = y0 + j * ch + (j >= ny / 2 ? 1.5 : -1.5), gr = g.createLinearGradient(x, y, x + cw, y + ch);
      gr.addColorStop(0, '#1d3157'); gr.addColorStop(1, '#111b35'); g.fillStyle = gr; g.fillRect(x + 1, y + 1, cw - 2, ch - 2);
      g.fillStyle = 'rgba(140,170,230,.16)'; g.fillRect(x + cw / 2 - 0.5, y + 2, 1, ch - 4);
    }
    g.fillStyle = '#9aa6bc'; g.fillRect(4, H / 2 - 1.5, W - 8, 3);
  }));
}
// a nozzle seen face on: the big engine's a deep cyan behind concentric rings, a thruster's bright cyan, white
// at the heart
function exNozTex(hot) {
  const k = hot ? 'exNozH' : 'exNoz';
  return TX[k] || (TX[k] = ctex(256, 256, (g) => {
    const gr = g.createRadialGradient(128, 128, 0, 128, 128, 128);
    if (hot) { gr.addColorStop(0, 'rgba(240,255,255,1)'); gr.addColorStop(0.45, 'rgba(120,240,255,1)'); gr.addColorStop(0.85, 'rgba(20,190,230,1)'); gr.addColorStop(1, 'rgba(8,60,80,1)'); }
    else { gr.addColorStop(0, 'rgba(150,250,255,1)'); gr.addColorStop(0.35, 'rgba(60,215,235,1)'); gr.addColorStop(0.7, 'rgba(18,150,180,1)'); gr.addColorStop(0.92, 'rgba(8,70,92,1)'); gr.addColorStop(1, 'rgba(6,26,36,1)'); }
    g.fillStyle = gr; g.beginPath(); g.arc(128, 128, 128, 0, Math.PI * 2); g.fill();
    if (!hot) { g.strokeStyle = 'rgba(6,40,54,.55)'; g.lineWidth = 3; [44, 78, 104].forEach((r) => { g.beginPath(); g.arc(128, 128, r, 0, Math.PI * 2); g.stroke(); }); }
  }));
}
// a part of an engine in its own frame: +z out of the hull, the axis the engine points along
function exPart(g, geom, mat, x, y, z, sx, sy, sz, rx = 0, ry = 0, rz = 0) {
  const m = new THREE.Mesh(geom, mat); m.position.set(x, y, z); m.scale.set(sx, sy, sz); m.rotation.set(rx, ry, rz); g.add(m); return m;
}
// a bar from a to b, w thick
function exStrut(g, a, b, w, mat) {
  const d = new THREE.Vector3().subVectors(b, a), m = new THREE.Mesh(G.box, mat);
  m.scale.set(w, w, d.length()); m.position.copy(a).addScaledVector(d, 0.5); m.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), d.normalize()); g.add(m); return m;
}
// The big engine under the front of the lot, as his close-up has it, from the hull outward: a dark mount, a
// wide dark collar with a ribbed radiator on top and gold tabs, a narrower neck of radial ribs, then the housing --
// light gunmetal, seamed, gold bolts on top and a gold pipe along its side -- ending in a thick dark lip round a
// nozzle that glows deep cyan behind concentric rings. Gold struts brace it to the hull below; a green cable runs
// down the hull to its collar. In units of its housing's radius.
function exBigEngine(g) {
  const O = OM, T = G.exTor;
  exPart(g, rboxGeo(1.9, 1.7, 0.24, 0.06), O.exGunD, 0, 0, 0.12, 1, 1, 1);
  exPart(g, G.exCollar, O.exGun, 0, 0, 0, 1, 1, 1, Math.PI / 2);
  exPart(g, T[0.06], O.exGunL, 0, 0, 0.7, 0.86, 0.86, 0.86);
  exPart(g, T[0.03], O.exGunD, 0, 0, 0.3, 0.9, 0.9, 0.9);
  [[0.92, 0.05], [0.66, -0.66]].forEach(([x, y]) => exPart(g, G.box, O.brass, x, y, 0.5, 0.1, 0.2, 0.2, 0, 0, Math.atan2(y, x)));
  exPart(g, G.box, O.exGunD, 0, 0.98, 0.46, 0.84, 0.22, 0.5);
  for (let i = 0; i < 9; i++) exPart(g, G.box, O.exGun, -0.36 + i * 0.09, 1.1, 0.46, 0.045, 0.06, 0.48);
  exPart(g, G.exTube, O.exGunD, 0, 0, 0.9, 0.62, 0.62, 0.32);
  for (let i = 0; i < 26; i++) { const a = i / 26 * Math.PI * 2; exPart(g, G.box, O.exGun, Math.cos(a) * 0.66, Math.sin(a) * 0.66, 0.9, 0.11, 0.05, 0.28, 0, 0, a); }
  exPart(g, G.exHousing, O.exGunM, 0, 0, 0, 1, 1, 1, Math.PI / 2);
  exPart(g, T[0.03], O.exGunD, 0, 0, 1.62, 1.0, 1.0, 0.4);
  exPart(g, G.box, O.exGunD, Math.cos(2.6), Math.sin(2.6), 1.9, 0.025, 0.025, 0.56, 0, 0, 2.6);
  [1.25, 1.57, 1.9].forEach((a) => { exPart(g, G.box, O.brass, Math.cos(a) * 1.02, Math.sin(a) * 1.02, 1.3, 0.12, 0.07, 0.12, 0, 0, a); exPart(g, G.exRod, O.brass, Math.cos(a) * 1.07, Math.sin(a) * 1.07, 1.3, 0.03, 0.03, 0.05); });
  const pa = -0.55; exStrut(g, new THREE.Vector3(Math.cos(pa) * 0.95, Math.sin(pa) * 0.95, 0.45), new THREE.Vector3(Math.cos(pa) * 1.06, Math.sin(pa) * 1.06, 2.2), 0.05, O.brass);
  // the lip is the housing's own silver, rolled thick; the dark is inside it
  exPart(g, T[0.12], O.exGunM, 0, 0, 2.47, 0.9, 0.9, 1.1);
  exPart(g, G.exTube, O.exGunD, 0, 0, 2.33, 0.8, 0.8, 0.26);
  exPart(g, T[0.06], O.exGun, 0, 0, 2.39, 0.77, 0.77, 0.6);
  exPart(g, T[0.03], O.exGunD, 0, 0, 2.29, 0.68, 0.68, 0.6);
  exPart(g, G.circle, O.exNoz, 0, 0, 2.23, 0.79, 0.79, 1);
  [-0.42, 0.42].forEach((a) => { const t = -Math.PI / 2 + a; exPart(g, G.box, O.exGunD, Math.cos(t) * 0.95, Math.sin(t) * 0.95, 2.59, 0.16, 0.12, 0.3, 0, 0, t); });
  // the braces: from under the collar back to the hull below the engine, a Y each side
  [-1, 1].forEach((s) => {
    const a = new THREE.Vector3(s * 0.32, -0.86, 0.5), b = new THREE.Vector3(s * 0.75, -1.5, 0.03), c = new THREE.Vector3(s * 0.2, -1.55, 0.03);
    exStrut(g, a, b, 0.07, O.brass); exStrut(g, a, c, 0.06, O.brass);
  });
  exStrut(g, new THREE.Vector3(0.62, 1.7, 0.03), new THREE.Vector3(0.5, 0.9, 0.3), 0.04, O.exCable);
  // no halo: his big nozzle glows inside its lip and no further (a sprite out in front was cut by the rock)
}
// a small thruster as his: a dark mount on the hull, a short neck with a gold ring, a dark body with a broad gold
// band, a dark lip round a bright cyan face. Its radius about 0.4.
function exThruster(g) {
  const O = OM, T = G.exTor;
  exPart(g, rboxGeo(0.66, 0.66, 0.12, 0.04), O.exGunD, 0, 0, 0.06, 1, 1, 1);
  [[0.24, 0.24], [-0.24, -0.24]].forEach(([x, y]) => exPart(g, G.exRod, O.brass, x, y, 0.14, 0.04, 0.04, 0.06));
  exPart(g, G.exTube, O.exGun, 0, 0, 0.27, 0.17, 0.17, 0.32);
  exPart(g, T[0.12], O.brass, 0, 0, 0.3, 0.19, 0.19, 0.3);
  exPart(g, G.exThrBody, O.exGun, 0, 0, 0, 1, 1, 1, Math.PI / 2);
  exPart(g, G.exTube, O.brass, 0, 0, 0.67, 0.425, 0.425, 0.22);
  exPart(g, T[0.12], O.exGunD, 0, 0, 1.03, 0.33, 0.33, 0.5);
  exPart(g, G.circle, O.exNozT, 0, 0, 1.0, 0.32, 0.32, 1);
  // his glow is crisp: a bright face whose own bloom makes a tight rim, and a ring of light just inside the lip --
  // no soft sprite round it
  exPart(g, T[0.03], O.exNozRim, 0, 0, 1.01, 0.3, 0.3, 0.5);
  const halo = glowSprite(0x8ff8ff, 0.12, 0.62); halo.position.z = 1.08; halo.userData.dyn = true; g.add(halo);
  return halo;
}
// one of the two back engines on the nacelle, as his: a dark rounded back, a bright chrome band dotted with
// bolts between dark bands, a gold ring, a flared bell, and a blue plume thinning away behind it
function exBackEngine(g) {
  const O = OM, T = G.exTor;
  exPart(g, G.exBackCap, O.exGun, 0, 0, 0, 1, 1, 1, Math.PI / 2);
  exPart(g, G.exTube, O.exChrome, 0, 0, 0.5, 0.53, 0.53, 0.8);
  exPart(g, G.exTube, O.exChrome, 0, 0, 0.45, 0.545, 0.545, 0.42);
  for (let i = 0; i < 10; i++) { const a = i / 10 * Math.PI * 2; exPart(g, G.box, O.exGunD, Math.cos(a) * 0.55, Math.sin(a) * 0.55, 0.45, 0.06, 0.02, 0.06, 0, 0, a); }
  [0.2, 0.7].forEach((z) => exPart(g, T[0.06], O.exGunD, 0, 0, z, 0.55, 0.55, 0.8));
  exPart(g, T[0.06], O.brass, 0, 0, 0.84, 0.53, 0.53, 0.8);
  exPart(g, G.exBell, O.exGun, 0, 0, 0, 1, 1, 1, Math.PI / 2);
  exPart(g, T[0.06], O.exGunD, 0, 0, 1.14, 0.52, 0.52, 0.8);
  exPart(g, G.circle, O.exNozB, 0, 0, 1.0, 0.47, 0.47, 1);
  // a flame as wide as the nozzle where it leaves it, thinning and fading away from it
  [[0.5, 2.6, O.exPlumeA], [0.28, 1.7, O.exPlumeB]].forEach(([w, len, mat]) => {
    const pm = exPart(g, G.plumeCone, mat, 0, 0, 1.12 + len / 2, w, len, w, -Math.PI / 2); pm.userData.dyn = true;
  });
  const halo = glowSprite(0x6a9cff, 0.3, 1.6); halo.position.z = 1.9; halo.userData.dyn = true; g.add(halo);
  return halo;
}
// a solar panel: the cells on a silver frame with a dark back, w by h, its cells facing +y, hinged at its z=0 edge
function exPanel(g, w, h) {
  exPart(g, G.box, OM.exFrame, 0, -0.03, h / 2, w, 0.05, h);
  exPart(g, G.plane, OM.exSolar, 0, 0.0, h / 2, w * 0.97, h * 0.97, 1, -Math.PI / 2);
  exPart(g, G.box, OM.exGunD, 0, -0.07, h / 2, w * 0.2, 0.04, h * 0.9);
}
// fade: [near, far] in view distance -- the fine grain and the cracks fade out between them, leaving the coarse
// noise, so a rock seen from the home view is not a field of pixel noise (procedural detail has no mipmaps)
function rockNodeMat(freq, bump = 0.32, fade = null) {
  const T = TSL, m = new THREE.MeshStandardNodeMaterial({ roughness: 0.9, metalness: 0.05 });
  const q = T.positionLocal.mul(freq);
  const near = fade ? T.float(1).sub(T.smoothstep(fade[0], fade[1], T.length(T.positionView))) : T.float(1);
  const grain = T.mx_fractal_noise_float(q.mul(0.8), 3, 2.0, 0.5).mul(near);
  const crack = T.smoothstep(0.55, 0.9, T.mx_worley_noise_float(q.mul(0.32))).mul(near);
  const big = T.mx_fractal_noise_float(q.mul(0.22), 3, 2.0, 0.5);
  const h = grain.mul(0.4).add(big.mul(0.6)).sub(crack.mul(0.5));
  m.userData.shade = h.mul(0.8).add(1.0).clamp(0.5, 1.6).mul(T.float(1).sub(crack.mul(0.5)));
  m.colorNode = T.vertexColor().xyz.mul(m.userData.shade).mul(0.6);
  const pv = T.positionView, n = T.normalView, dx = T.dFdx(pv), dy = T.dFdy(pv);
  const r1 = T.cross(dy, n), r2 = T.cross(n, dx), det = T.dot(dx, r1);
  m.normalNode = T.normalize(T.abs(det).mul(n).sub(T.sign(det).mul(r1.mul(T.dFdx(h)).add(r2.mul(T.dFdy(h)))).mul(bump)));
  return m;
}
function nozzleTex() {
  return TX.nozzle || (TX.nozzle = ctex(256, 256, (g) => {
    const gr = g.createRadialGradient(128, 128, 0, 128, 128, 128);
    gr.addColorStop(0, 'rgba(235,254,255,1)'); gr.addColorStop(0.38, 'rgba(90,235,255,1)'); gr.addColorStop(0.72, 'rgba(0,185,235,.95)'); gr.addColorStop(0.9, 'rgba(10,45,68,1)'); gr.addColorStop(1, 'rgba(8,16,24,1)');
    g.fillStyle = gr; g.beginPath(); g.arc(128, 128, 128, 0, Math.PI * 2); g.fill();
    g.strokeStyle = 'rgba(8,22,34,.55)'; g.lineWidth = 6;
    for (let k = 0; k < 6; k++) { const a = k / 6 * Math.PI; g.beginPath(); g.moveTo(128 + Math.cos(a) * 118, 128 + Math.sin(a) * 118); g.lineTo(128 - Math.cos(a) * 118, 128 - Math.sin(a) * 118); g.stroke(); }
    g.fillStyle = 'rgba(8,22,34,.7)'; g.beginPath(); g.arc(128, 128, 22, 0, Math.PI * 2); g.fill();
  }));
}
function monTex() {
  return TX.mon || (TX.mon = ctex(256, 144, (g, W) => {
    g.fillStyle = '#031c16'; g.fillRect(0, 0, W, 144);
    g.strokeStyle = '#38f5b8'; g.lineWidth = 3.5; g.beginPath();
    let y = 96; for (let x = 12; x < W - 10; x += 12) { y = Math.max(36, Math.min(112, y + Math.sin(x * 0.13) * 14 + (x % 36 ? -5 : 9))); if (x === 12) g.moveTo(x, y); else g.lineTo(x, y); } g.stroke();
    g.fillStyle = 'rgba(56,245,184,.45)'; for (let i = 0; i < 8; i++) g.fillRect(14 + i * 29, 118, 18, 16 - (i % 3) * 4);
    g.fillStyle = '#38f5b8'; g.fillRect(14, 12, 68, 8); g.fillStyle = 'rgba(36,232,255,.65)'; g.fillRect(14, 26, 110, 5);
  }));
}
// a trader's screen: a price line over its grid, the volume under it, the ticker and its last price at the head
function orangeMonTex() {
  return TX.omon || (TX.omon = ctex(256, 144, (g, W, H) => {
    g.fillStyle = '#1c0e04'; g.fillRect(0, 0, W, H);
    g.strokeStyle = 'rgba(255,148,56,.16)'; g.lineWidth = 1;
    for (let y = 40; y < 116; y += 15) { g.beginPath(); g.moveTo(10, y); g.lineTo(W - 40, y); g.stroke(); }
    for (let x = 40; x < W - 40; x += 36) { g.beginPath(); g.moveTo(x, 36); g.lineTo(x, 114); g.stroke(); }
    g.strokeStyle = '#ff9438'; g.lineWidth = 3; g.beginPath();
    let y = 92, ly = 0; for (let x = 12; x < W - 42; x += 8) { y = Math.max(40, Math.min(110, y + Math.cos(x * 0.15) * 11 + (x % 24 ? -3 : 7))); if (x === 12) g.moveTo(x, y); else g.lineTo(x, y); ly = y; } g.stroke();
    g.fillStyle = '#ff9438'; g.fillRect(W - 38, ly - 7, 32, 14);
    g.fillStyle = 'rgba(255,148,56,.4)'; for (let x = 12; x < W - 42; x += 8) g.fillRect(x, 136 - ((x * 7) % 15), 5, (x * 7) % 15 + 2);
    g.fillStyle = '#ff9438'; g.fillRect(12, 12, 64, 8); g.fillStyle = 'rgba(255,180,90,.6)'; g.fillRect(84, 12, 40, 8); g.fillRect(W - 60, 12, 48, 8);
  }));
}
// The trading desk's chart board, his picture's right-hand one on the back wall: a red line of dots wandering across a
// dark board in a yellow-green frame, its grid and its scale faint behind it
function orangeWallTex() {
  return TX.owall || (TX.owall = ctex(512, 160, (g, W, H) => {
    g.fillStyle = '#0c1108'; g.fillRect(0, 0, W, H);
    g.strokeStyle = '#c8e06a'; g.lineWidth = 5; g.strokeRect(3, 3, W - 6, H - 6);
    g.fillStyle = '#c8e06a'; g.font = '700 17px JetBrains Mono, monospace'; g.fillText('PNL 30D', 18, 28);
    g.fillStyle = 'rgba(200,224,106,.55)'; g.fillRect(110, 18, 70, 8); g.fillRect(W - 92, 18, 74, 8);
    g.strokeStyle = 'rgba(200,224,106,.14)'; g.lineWidth = 1;
    for (let y = 44; y < H - 14; y += 18) { g.beginPath(); g.moveTo(16, y); g.lineTo(W - 46, y); g.stroke(); }
    for (let x = 16; x < W - 46; x += 40) { g.beginPath(); g.moveTo(x, 40); g.lineTo(x, H - 16); g.stroke(); }
    g.fillStyle = 'rgba(200,224,106,.4)'; for (let y = 44; y < H - 14; y += 18) g.fillRect(W - 40, y - 2, 24, 4);
    const pts = []; for (let x = 20; x < W - 50; x += 7) pts.push([x, H * 0.5 + Math.sin(x * 0.03) * 22 + Math.cos(x * 0.09) * 9 - (x - 20) * 0.04]);
    g.strokeStyle = 'rgba(255,90,70,.45)'; g.lineWidth = 2; g.beginPath(); pts.forEach(([x, y], i) => (i ? g.lineTo(x, y) : g.moveTo(x, y))); g.stroke();
    g.fillStyle = '#ff5a46'; pts.forEach(([x, y]) => { g.beginPath(); g.arc(x, y, 2.6, 0, Math.PI * 2); g.fill(); });
  }));
}
// his Cymetica QA's window of light: three by three panes, white-hot at their middles, mint at their edges, in a
// dark frame
function qaGridTex() {
  return TX.qagrid || (TX.qagrid = ctex(256, 256, (g, W, H) => {
    g.fillStyle = '#051418'; g.fillRect(0, 0, W, H);
    const cols = 3, rows = 3, pad = 16, cw = (W - pad * (cols + 1)) / cols, ch = (H - pad * (rows + 1)) / rows;
    for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) {
      const x = pad + c * (cw + pad), y = pad + r * (ch + pad);
      g.fillStyle = '#4fe8d0'; g.fillRect(x, y, cw, ch);
      const gr = g.createRadialGradient(x + cw / 2, y + ch / 2, 0, x + cw / 2, y + ch / 2, cw * 0.62);
      gr.addColorStop(0, '#f2fffc'); gr.addColorStop(0.55, '#bdfdf0'); gr.addColorStop(1, 'rgba(120,246,224,0)');
      g.fillStyle = gr; g.fillRect(x, y, cw, ch);
    }
  }));
}
// the trading desk's floor in his picture glows along its tile seams: the seams as an emissive map, a soft wash in
// each tile so the floor reads lit, not only lined
function seamTex() {
  return TX.seam || (TX.seam = ctex(512, 512, (g, W) => {
    const n = 10, s = W / n; g.fillStyle = '#000000'; g.fillRect(0, 0, W, W);
    g.fillStyle = 'rgba(255,255,255,.1)'; g.fillRect(0, 0, W, W);
    g.fillStyle = 'rgba(255,255,255,.55)'; for (let i = 0; i <= n; i++) { g.fillRect(i * s - 1, 0, 2, W); g.fillRect(0, i * s - 1, W, 2); }
    // the pool: brightest in the middle of the room, gone at its walls -- multiplied in, as the map is read
    // without its alpha
    const pool = g.createRadialGradient(W / 2, W / 2, 0, W / 2, W / 2, W * 0.62);
    pool.addColorStop(0, '#ffffff'); pool.addColorStop(1, '#000000');
    g.globalCompositeOperation = 'multiply'; g.fillStyle = pool; g.fillRect(0, 0, W, W);
    const p2 = g.createRadialGradient(W / 2, W / 2, 0, W / 2, W / 2, W * 0.5); p2.addColorStop(0, 'rgba(255,255,255,.5)'); p2.addColorStop(1, 'rgba(255,255,255,0)');
    g.globalCompositeOperation = 'lighter'; g.fillStyle = p2; g.fillRect(0, 0, W, W); g.globalCompositeOperation = 'source-over';
  }));
}
// a hologram's face: a vibrant aqua-cyan field, a border, a trace and bars
function holoTex() {
  return TX.holo || (TX.holo = ctex(256, 176, (g, W, H) => {
    g.fillStyle = 'rgba(32,235,255,.22)'; g.fillRect(0, 0, W, H); g.strokeStyle = 'rgba(56,245,210,.98)'; g.lineWidth = 4; g.strokeRect(3, 3, W - 6, H - 6);
    g.strokeStyle = 'rgba(56,255,180,.98)'; g.lineWidth = 3.5; g.beginPath(); for (let x = 14; x < W - 14; x += 6) { const y = H * 0.42 + Math.sin(x * 0.09) * 18 * Math.sin(x * 0.021); if (x === 14) g.moveTo(x, y); else g.lineTo(x, y); } g.stroke();
    g.fillStyle = 'rgba(36,232,255,.88)'; for (let i = 0; i < 9; i++) g.fillRect(16 + i * 25, H - 20 - (i * 13 % 34), 14, 8 + (i * 13 % 34));
  }));
}
// a grid of light that wraps round a cylinder: the Add department pad's wall in turquoise-aquamarine
function gridTex() {
  if (TX.grid) return TX.grid;
  // his ring's wall is a fine speckle of light more than a grid: dots on a faint mesh, densest at its foot
  const t = ctex(256, 64, (g, W, H) => {
    const R = rng(61);
    g.fillStyle = 'rgba(24,185,155,.04)'; g.fillRect(0, 0, W, H);
    g.strokeStyle = 'rgba(48,220,188,.18)'; g.lineWidth = 1;
    for (let x = 0; x <= W; x += 6) { g.beginPath(); g.moveTo(x, 0); g.lineTo(x, H); g.stroke(); }
    for (let y = 0; y <= H; y += 6) { g.beginPath(); g.moveTo(0, y); g.lineTo(W, y); g.stroke(); }
    for (let i = 0; i < 1400; i++) { g.fillStyle = 'rgba(120,245,225,' + (0.3 + R() * 0.6).toFixed(2) + ')'; g.fillRect(R() * W, R() * H, 1.4, 1.4); }
  });
  t.wrapS = THREE.RepeatWrapping; t.repeat.set(8, 1); TX.grid = t; return t;
}
// the Manager's floor: rings and arcs of light round the dais, with ticks
function hubFloorTex() {
  return TX.hubf || (TX.hubf = ctex(512, 512, (g, W) => {
    const c = W / 2; g.fillStyle = '#000000'; g.fillRect(0, 0, W, W); g.lineCap = 'round';
    const rg = g.createRadialGradient(c, c, c * 0.1, c, c, c * 0.95);
    rg.addColorStop(0, 'rgba(0,225,255,.22)'); rg.addColorStop(0.55, 'rgba(0,195,235,.08)'); rg.addColorStop(1, 'rgba(0,195,235,0)');
    g.fillStyle = rg; g.fillRect(0, 0, W, W);
    [[0.95, 3.5, 0.65, 0, 360], [0.84, 3.5, 0.85, 15, 150], [0.84, 3.5, 0.85, 195, 330], [0.72, 8, 0.36, 0, 360], [0.61, 2.5, 0.8, 100, 260], [0.61, 2.5, 0.8, 280, 420], [0.5, 14, 0.3, 0, 360]].forEach(([rr, lw, a, s0, s1]) => {
      g.strokeStyle = 'rgba(36,232,255,' + a + ')'; g.lineWidth = lw; g.beginPath(); g.arc(c, c, rr * c, s0 * Math.PI / 180, s1 * Math.PI / 180); g.stroke();
    });
    g.strokeStyle = 'rgba(56,245,215,.65)'; g.lineWidth = 2;
    for (let i = 0; i < 96; i++) { const a = i / 96 * Math.PI * 2, r0 = c * (i % 4 ? 0.9 : 0.87); g.beginPath(); g.moveTo(c + Math.cos(a) * r0, c + Math.sin(a) * r0); g.lineTo(c + Math.cos(a) * c * 0.93, c + Math.sin(a) * c * 0.93); g.stroke(); }
  }));
}
// an engine's exhaust: bright at the nozzle, gone at the tail
function plumeTex() {
  return TX.plume || (TX.plume = ctex(32, 256, (g, W, H) => { const gr = g.createLinearGradient(0, 0, 0, H); gr.addColorStop(0, 'rgba(220,252,255,1)'); gr.addColorStop(0.35, 'rgba(40,220,255,.55)'); gr.addColorStop(1, 'rgba(0,180,255,0)'); g.fillStyle = gr; g.fillRect(0, 0, W, H); }));
}
function std(o) { return new THREE.MeshStandardMaterial(o); }
const RB = new Map();
function rboxGeo(w, h, d, r) {
  const k = [w, h, d, r].map((v) => v.toFixed(3)).join(',');
  let g = RB.get(k); if (!g) { g = new RoundedBoxGeometry(w, h, d, 2, Math.max(0.001, Math.min(r, w / 2 - 0.001, h / 2 - 0.001, d / 2 - 0.001))); RB.set(k, g); }
  return g;
}
function omats() {
  if (OM.tile) return;
  OM.deck = std({ map: deckTex(), roughness: 0.46, metalness: 0.32 });
  OM.tile = std({ map: tileTex(), roughness: 0.58, metalness: 0.2 });
  OM.hubTile = std({ map: tileTex(), color: 0xb4c8dc, roughness: 0.5, metalness: 0.22 });
  OM.rim = std({ color: 0x2c3a4a, roughness: 0.4, metalness: 0.45 });
  OM.rimDark = std({ color: 0x18222e, roughness: 0.48, metalness: 0.4 });
  OM.hull = std({ map: hullTex(), emissiveMap: TX.hullGlow, emissive: 0xffffff, emissiveIntensity: 0.9, roughness: 0.55, metalness: 0.25 });
  OM.hullLow = std({ color: 0x141e30, roughness: 0.48, metalness: 0.4 });   // his keel's chamfer is navy, not black
  // the glass: a pale frosted pane that catches the light (his picture lifts the deck behind it by about a tenth),
  // its own edges a thin pale line; the colour is the neon's, not the glass's
  OM.glass = std({ color: 0xa9bfca, envMapIntensity: 0.7, transparent: true, opacity: 0.075, roughness: 0.1, metalness: 0.0, depthWrite: false, side: THREE.DoubleSide });
  OM.glassCyan = OM.glass;
  OM.glassOrange = std({ color: 0xffb084, emissive: 0x5a2008, emissiveIntensity: 0.25, envMapIntensity: 0.7, transparent: true, opacity: 0.1, roughness: 0.1, metalness: 0.0, depthWrite: false, side: THREE.DoubleSide });
  OM.glassEdge = emis('#a9c4cc', 0.2);
  OM.wallDark = std({ color: 0x0f161e, roughness: 0.45, metalness: 0.3 });
  OM.frame = std({ color: 0x2a3644, roughness: 0.4, metalness: 0.5 });
  OM.brass = std({ color: 0xa8833e, roughness: 0.42, metalness: 0.75 });   // his engines' fittings: a dull, warm gold
  // furniture in his picture: charcoal desks with a lighter top, white retro consoles and lab machines
  OM.desk = std({ color: 0x1e262f, roughness: 0.5, metalness: 0.3 });
  OM.deskTop = std({ color: 0x2c3742, roughness: 0.32, metalness: 0.3 });
  OM.dark = std({ color: 0x0b1118, roughness: 0.36, metalness: 0.45 });
  OM.plinth = std({ color: 0x1c2833, roughness: 0.4, metalness: 0.45 });
  OM.white = std({ color: 0xb9c3cb, roughness: 0.42, metalness: 0.12 });
  OM.white2 = std({ color: 0x8d99a3, roughness: 0.46, metalness: 0.15 });
  OM.rack = std({ color: 0x18222b, roughness: 0.42, metalness: 0.45 });
  OM.rackFace = std({ map: rackTex(), emissiveMap: TX.rackGlow, emissive: 0xffffff, emissiveIntensity: 1.35, roughness: 0.36, metalness: 0.42 });
  OM.solar = std({ map: officeSolarTex(), roughness: 0.22, metalness: 0.5, emissive: 0x1a3a80, emissiveIntensity: 0.05 });
  OM.engine = std({ color: 0x6a7686, roughness: 0.32, metalness: 0.65 });
  OM.engineDark = std({ color: 0x121b26, roughness: 0.4, metalness: 0.55, side: THREE.DoubleSide });
  // the studio's environment lit the rock grey from every side (a dielectric still mirrors 4 % of it); his rock's
  // middle is near black, its light only on the ridges the sun finds
  OM.rock = rockNodeMat(7, 0.3, [16, 34]); OM.rock.roughness = 0.78; OM.rock.envMapIntensity = 0.3; OM.rockS = rockNodeMat(5.0);   // the station's rock: its ridges take a sheen
  // his asteroid top right is a light grey, cratered and lit from the left
  OM.asteroid = rockNodeMat(3.0); OM.asteroid.colorNode = TSL.vec3(0.34, 0.35, 0.38).mul(OM.asteroid.userData.shade);
  // his engines are brushed silver with dark bands, not navy -- matte enough not to read as glass
  OM.engineL = std({ color: 0x6e7886, roughness: 0.5, metalness: 0.45, side: THREE.DoubleSide });
  OM.engineBand = std({ color: 0x1c242e, roughness: 0.45, metalness: 0.5 });
  G.plumeCone = new THREE.CylinderGeometry(1, 0.05, 1, 24, 1, true);   // wide end (and the texture's bright top) at the nozzle
  G.circle = new THREE.CircleGeometry(1, 48);
  G.engHousing = new THREE.LatheGeometry([[0.32, -0.72], [0.5, -0.66], [0.58, -0.5], [0.6, -0.22], [0.55, -0.17], [0.55, -0.1], [0.64, -0.06], [0.66, 0.66], [0.6, 0.72], [0.6, 0.78],
    [0.68, 0.84], [0.74, 0.92], [0.74, 1.1], [0.66, 1.14], [0.56, 1.06], [0.52, 0.98]].map(([r, z]) => new THREE.Vector2(r, z)), 48);
  OM.pot = std({ color: 0x232c36, roughness: 0.5, metalness: 0.3 });
  OM.bush = std({ color: 0x1f5a40, roughness: 0.85 });
  OM.holo = new THREE.MeshBasicMaterial({ map: holoTex(), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
  OM.plume = new THREE.MeshBasicMaterial({ map: plumeTex(), color: new THREE.Color(0x28e4ff).multiplyScalar(1.2), opacity: 0.88, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
  OM.dash = emis('#dfeaf0', 0.62);
  OM.lotRim = emis('#1ed8cc', 2.2);
  OM.lotCyan = emis('#36c8e8', 1.5);
  OM.frameLime = emis('#c8ea6a', 1.5);
  OM.paneLime = new THREE.MeshBasicMaterial({ color: 0x6a8a3a, transparent: true, opacity: 0.22, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
  OM.daisRim = std({ color: 0x4a5866, roughness: 0.35, metalness: 0.45 });
  OM.daisArc = emis('#c8d4de', 0.55);
  // his trading floor: the blue floor under an orange-red pool of light, the tile seams a faint glow in it
  OM.tileOrange = std({ map: tileTex(), color: 0xf0d4cc, emissiveMap: seamTex(), emissive: 0xff6a30, emissiveIntensity: 2.4, roughness: 0.5, metalness: 0.2 });
  OM.coinG = std({ color: 0x18b87a, emissive: 0x38f5b8, emissiveIntensity: 0.28, metalness: 0.8, roughness: 0.22 });
  OM.coinB = std({ color: 0x2f6fd8, emissive: 0x3b82f6, emissiveIntensity: 0.32, metalness: 0.8, roughness: 0.22 });
  G.coin = new THREE.CylinderGeometry(1, 1, 1, 28);
  // astronauts as in his picture, zoomed: steel-blue suits, darker packs and joints, a glossy blue helmet, a dark visor
  OM.suit = std({ color: 0x7088a4, roughness: 0.5, metalness: 0.1 });
  OM.pack = std({ color: 0x4a5c70, roughness: 0.5, metalness: 0.15 });
  OM.visor = std({ color: 0x0e2c56, roughness: 0.14, metalness: 0.6, emissive: 0x0a2e5e, emissiveIntensity: 0.25 });
  OM.helmet = std({ color: 0x4e6c90, roughness: 0.22, metalness: 0.35 });
  OM.torso = new THREE.CapsuleGeometry(0.16, 0.26, 4, 14); OM.limb = new THREE.CapsuleGeometry(0.055, 0.2, 3, 10); OM.leg = new THREE.CapsuleGeometry(0.07, 0.36, 3, 10);
  OM.chair = std({ color: 0x232d38, roughness: 0.48, metalness: 0.3 });
  OM.green = amat('#38f5b8'); OM.cyan = amat('#24e8ff'); OM.blue = amat('#3b82f6'); OM.red = amat('#ff8824'); OM.amber = amat('#ff8824');
  G.smallRock = asteroidGeo(27, 9, false);   // twelve of them drift unmerged: 2,000 triangles each, the grain is the material's
  G.plume = new THREE.CylinderGeometry(0.42, 0.05, 1, 24, 1, true);
}
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
// A room's still parts merged per material, so a weak computer draws each room in a few dozen calls instead of a
// few hundred (measured 2026-10-19: rooms' small parts were 1,100 of the office's 2,000 draw calls a frame, and the
// shadow pass draws them again). The picture does not change: the merged mesh has the same material, the same
// shadows and the same place. What moves or changes stays as it is -- anything the room's fields hold (its agents,
// screens, crystal, rings, door, piles ...), whatever says userData.dyn or blink, instanced meshes, transparent or
// invisible ones (the glass sorts by itself; the hit boxes are invisible), mirrored ones and multi-material boxes.
function bakeRoom(r) {
  const keep = new Set(), seen = new Set([r]);
  const hold = (v, depth) => {
    if (!v || typeof v !== 'object' || seen.has(v) || depth > 4) return;
    seen.add(v);
    if (v.isObject3D) { if (v !== r.g) v.traverse((o) => keep.add(o)); return; }
    if (v.isMaterial || v.isTexture || v.isBufferGeometry || (typeof Node !== 'undefined' && v instanceof Node)) return;
    (Array.isArray(v) ? v : Object.values(v)).forEach((x) => hold(x, depth + 1));
  };
  Object.keys(r).forEach((k) => { if (k !== 'g' && k !== 'dept') hold(r[k], 0); });
  const root = r.g; root.updateMatrixWorld(true);
  const inv = root.matrixWorld.clone().invert(), bins = new Map(), rel = new THREE.Matrix4();
  (function walk(o) {
    o.children.slice().forEach((ch) => {
      if (keep.has(ch) || ch.userData.dyn || ch.userData.blink != null || ch.userData.pc || ch.userData.key || ch.isInstancedMesh || !ch.visible) return;
      walk(ch);
      if (!ch.isMesh || ch.isSkinnedMesh || !ch.material || Array.isArray(ch.material) || ch.children.length) return;
      const m = ch.material, g = ch.geometry;
      if (m.transparent || m.visible === false || m === M.hit || ch.renderOrder || g.morphAttributes && Object.keys(g.morphAttributes).length) return;
      rel.multiplyMatrices(inv, ch.matrixWorld); if (rel.determinant() <= 0) return;
      const key = [m.uuid, ch.castShadow, ch.receiveShadow, !!g.index, Object.keys(g.attributes).sort().join(',')].join('|');
      let bin = bins.get(key); if (!bin) bins.set(key, bin = { mat: m, cast: ch.castShadow, recv: ch.receiveShadow, geos: [], objs: [] });
      bin.geos.push(g.clone().applyMatrix4(rel)); bin.objs.push(ch);
    });
  })(root);
  let calls = 0;
  bins.forEach((bin) => {
    if (bin.objs.length < 2) { bin.geos.forEach((x) => x.dispose()); return; }
    bin.geos.forEach((x) => { x.clearGroups(); });
    const merged = mergeGeometries(bin.geos, false); bin.geos.forEach((x) => x.dispose());
    if (!merged) return;
    bin.objs.forEach((o) => o.parent.remove(o));
    const mm = new THREE.Mesh(merged, bin.mat); mm.castShadow = bin.cast; mm.receiveShadow = bin.recv; mm.userData.own = true; root.add(mm);
    calls += bin.objs.length - 1;
  });
  return calls;
}
function emis(hex, k) { return new THREE.MeshStandardMaterial({ color: 0x000000, emissive: new THREE.Color(hex), emissiveIntensity: k == null ? 1.4 : k, roughness: 1 }); }
// The wall screens' measure: a face 0.56 high from the wainscot up, centred at 0.96, so with its bezel it ends at
// 1.28 -- under the back walls' top neon (1.42 to 1.48) with a clear gap, as every screen in his picture.
const RBW = { h: 0.56, mid: 0.96, top: 1.3 };
function screen(w, h) {
  const c = document.createElement('canvas'); c.width = Math.round(w * 256); c.height = Math.round(h * 256);
  const tex = new THREE.CanvasTexture(c); tex.colorSpace = THREE.SRGBColorSpace; tex.anisotropy = 8;
  return { c, g: c.getContext('2d'), tex, key: '' };
}
// his wall screen: near-black glass inside a thin pale frame, a line of small text top left, faint rows of data
// under it; ours keeps what runs or why it waits, and the bar of its progress
function drawWall(s, title, sub, col, mode) {
  const key = [title, sub, col, mode].join('|'); if (s.key === key) return; s.key = key;
  const { c, g } = s, W = c.width, H = c.height, p = Math.round(H * 0.1);
  g.fillStyle = '#060b11'; g.fillRect(0, 0, W, H);
  const sh = g.createLinearGradient(0, 0, 0, H); sh.addColorStop(0, 'rgba(120,150,170,.08)'); sh.addColorStop(0.5, 'rgba(120,150,170,0)'); g.fillStyle = sh; g.fillRect(0, 0, W, H);
  g.strokeStyle = 'rgba(176,196,208,.62)'; g.lineWidth = Math.max(2, H * 0.025); g.strokeRect(p * 0.5, p * 0.5, W - p, H - p);
  g.fillStyle = col; g.font = '700 ' + Math.round(H * 0.17) + 'px JetBrains Mono, monospace'; g.textBaseline = 'top';
  const fit = (t) => { let s2 = String(t || ''); while (s2.length > 3 && g.measureText(s2).width > W - 3 * p) s2 = s2.slice(0, -2); return s2 !== t ? s2.replace(/.$/, '…') : s2; };
  g.fillText(fit(title), p * 1.4, H * 0.17);
  g.fillStyle = '#8fa8c2'; g.font = '500 ' + Math.round(H * 0.12) + 'px JetBrains Mono, monospace';
  g.fillText(fit(sub), p * 1.4, H * 0.42);
  // faint rows of data along the right of the face, as his screens carry
  g.fillStyle = 'rgba(143,168,194,.16)';
  for (let k = 0; k < 3; k++) { const y = H * (0.2 + k * 0.13), x = W * 0.62; g.fillRect(x, y, (W * 0.3) * (1 - k * 0.22), H * 0.045); }
  g.fillStyle = '#122030'; g.fillRect(p * 1.4, H * 0.72, W - 2.8 * p, H * 0.07);
  if (mode === 'run') { g.fillStyle = col; g.fillRect(p * 1.4, H * 0.72, (W - 2.8 * p) * (0.25 + 0.5 * Math.random()), H * 0.07); }
  if (mode === 'full') { g.fillStyle = col; g.globalAlpha = 0.8; g.fillRect(p * 1.4, H * 0.72, W - 2.8 * p, H * 0.07); g.globalAlpha = 1; }
  s.tex.needsUpdate = true;
}
function drawBars(s, title, bars) {
  const key = title + JSON.stringify(bars); if (s.key === key) return; s.key = key;
  const { c, g } = s, W = c.width, H = c.height;
  g.fillStyle = '#06101a'; g.fillRect(0, 0, W, H); g.strokeStyle = '#24e8ff'; g.lineWidth = 6; g.strokeRect(3, 3, W - 6, H - 6);
  g.fillStyle = '#24e8ff'; g.font = '700 ' + Math.round(H * 0.15) + 'px JetBrains Mono, monospace'; g.textBaseline = 'top'; g.fillText(title, 20, H * 0.1);
  const top = Math.max(1, ...bars.map((b) => b[1])), bw = (W - 40) / Math.max(1, bars.length);
  bars.forEach((b, i) => { const h = (H * 0.55) * b[1] / top; g.fillStyle = b[0]; g.fillRect(20 + i * bw, H * 0.88 - h, bw - 10, Math.max(3, h)); });
  s.tex.needsUpdate = true;
}
function drawKanban(s, counts) {
  const key = JSON.stringify(counts); if (s.key === key) return; s.key = key;
  const { c, g } = s, W = c.width, H = c.height, cols = [['queued', '#3b82f6'], ['running', '#24e8ff'], ['done', '#38f5b8'], ['failed', '#ff8824']];
  // his long panel on the other back wall: a band of coloured strips along its top, one per column, and under each
  // the cards as thin bars, a pale outline where a column is empty
  const p = Math.round(H * 0.1);
  g.fillStyle = '#060b11'; g.fillRect(0, 0, W, H);
  g.strokeStyle = 'rgba(176,196,208,.4)'; g.lineWidth = Math.max(2, H * 0.02); g.strokeRect(p * 0.5, p * 0.5, W - p, H - p);
  const cw = (W - 2 * p) / 4, ch = (H - p * 2) * 0.13;
  cols.forEach(([k, col], i) => {
    const x = p + i * cw + p * 0.3, w = cw - p * 0.6;
    g.fillStyle = col; g.globalAlpha = 0.92; g.fillRect(x, p * 1.1, w, H * 0.12); g.globalAlpha = 1;
    const n = Math.min(counts[k] || 0, 4);
    for (let j = 0; j < 4; j++) {
      const y = p * 1.1 + H * 0.2 + j * (ch + H * 0.05);
      if (j < n) { g.fillStyle = col; g.globalAlpha = 0.55; g.fillRect(x, y, w * (0.92 - (j % 2) * 0.18), ch); g.globalAlpha = 1; }
      else if (j === n) { g.strokeStyle = 'rgba(143,168,194,.22)'; g.lineWidth = 2; g.strokeRect(x + 1, y + 1, w * 0.7, ch - 2); }
    }
  });
  s.tex.needsUpdate = true;
}
// The rooms' furniture and people as his picture has them, zoomed: near-black desks with a lighter top, one wide
// monitor on a neck and a foot, a keyboard with its keys, a white mouse; black office chairs on five-star bases;
// astronauts in white suits with glossy blue helmets; dark pots with a round bush. Made once, shared by every room.
function rbMats() {
  if (OM.rbDesk) return OM;
  OM.rbBezel = OM.rbBezel || std({ color: 0x141b23, roughness: 0.38, metalness: 0.5 });
  OM.rbDesk = std({ color: 0x141a21, roughness: 0.44, metalness: 0.32 });
  OM.rbDeskTop = std({ color: 0x27303a, roughness: 0.3, metalness: 0.32 });
  OM.rbSeam = std({ color: 0x06080b, roughness: 0.6, metalness: 0.2 });
  OM.rbMetal = std({ color: 0x55606e, roughness: 0.28, metalness: 0.75 });
  OM.rbGloss = std({ color: 0x0a0e13, roughness: 0.2, metalness: 0.55 });
  OM.rbKeys = std({ map: rbKeysTex(), roughness: 0.55, metalness: 0.2 });
  OM.rbMouse = std({ color: 0xd8e0e8, roughness: 0.35, metalness: 0.1 });
  // his astronauts: white suits shaded blue-grey, a white pack, darker joints and soles, a glossy blue helmet over a
  // near-black visor, a patch on the shoulder
  OM.rbSuit = std({ color: 0x84a0be, roughness: 0.6, metalness: 0.06 });
  OM.rbJoint = std({ color: 0x4c6480, roughness: 0.5, metalness: 0.12 });
  OM.rbPack = std({ color: 0x9ab4cc, roughness: 0.5, metalness: 0.08 });
  OM.rbCollar = std({ color: 0x9aa7b4, roughness: 0.28, metalness: 0.62 });
  OM.rbHelmet = std({ color: 0x3a6a9c, roughness: 0.14, metalness: 0.42 });
  OM.rbVisor = std({ color: 0x08142a, roughness: 0.06, metalness: 0.75, emissive: 0x0a2e5e, emissiveIntensity: 0.25 });
  OM.rbSole = std({ color: 0x1a2129, roughness: 0.6, metalness: 0.2 });
  OM.rbPatch = std({ color: 0xff8824, roughness: 0.5, emissive: 0xff8824, emissiveIntensity: 0.25 });
  OM.rbChair = std({ color: 0x161c24, roughness: 0.52, metalness: 0.22 });
  OM.rbChairMetal = std({ color: 0x2c3540, roughness: 0.3, metalness: 0.7 });
  OM.rbPot = std({ color: 0x182029, roughness: 0.42, metalness: 0.32 });
  OM.rbSoil = std({ color: 0x1c140e, roughness: 0.95 });
  OM.rbLeaf = std({ color: 0x1e5c3c, roughness: 0.82, flatShading: true });
  OM.rbLeaf2 = std({ color: 0x2a7448, roughness: 0.8, flatShading: true });
  G.rbTorso = new THREE.CapsuleGeometry(0.165, 0.2, 6, 16);
  G.rbArm = new THREE.CapsuleGeometry(0.056, 0.15, 4, 12);
  G.rbFore = new THREE.CapsuleGeometry(0.05, 0.2, 4, 12);
  G.rbThigh = new THREE.CapsuleGeometry(0.07, 0.2, 4, 12);
  G.rbShin = new THREE.CapsuleGeometry(0.062, 0.3, 4, 12);
  G.rbLeg = new THREE.CapsuleGeometry(0.07, 0.34, 4, 12);
  G.rbPot = new THREE.CylinderGeometry(1, 0.8, 1, 28);
  // a bush: a ball of leaves, its surface jittered so the flat shading reads as leaves catching the light
  const bush = new THREE.IcosahedronGeometry(1, 3), p = bush.attributes.position, R = rng(17), seen = new Map();
  for (let i = 0; i < p.count; i++) {
    const k = p.getX(i).toFixed(3) + ',' + p.getY(i).toFixed(3) + ',' + p.getZ(i).toFixed(3);
    let f = seen.get(k); if (f == null) { f = 0.9 + R() * 0.18; seen.set(k, f); }
    p.setXYZ(i, p.getX(i) * f, p.getY(i) * f, p.getZ(i) * f);
  }
  bush.computeVertexNormals(); G.rbBush = bush;
  return OM;
}
// Static parts of one piece merged by material, its direct children only: a desk, a chair or half an astronaut is a
// handful of draw calls, not twenty. A part marked userData.dyn stays as it is: its material changes at run time,
// or its geometry is dense enough that sharing it beats copying it.
function rbBake(root) {
  root.updateMatrixWorld(true);
  const inv = root.matrixWorld.clone().invert(), bins = new Map();
  root.children.slice().forEach((ch) => {
    if (!ch.isMesh || ch.isInstancedMesh || ch.userData.dyn || Array.isArray(ch.material)) return;
    const key = ch.material.uuid + (ch.geometry.index ? 'i' : 'n');
    let bin = bins.get(key); if (!bin) bins.set(key, bin = { mat: ch.material, objs: [] });
    bin.objs.push(ch);
  });
  bins.forEach((bin) => {
    if (bin.objs.length < 2) return;
    const geos = bin.objs.map((o) => { const g = o.geometry.clone(); g.clearGroups(); return g.applyMatrix4(new THREE.Matrix4().multiplyMatrices(inv, o.matrixWorld)); });
    const merged = mergeGeometries(geos, false); geos.forEach((x) => x.dispose());
    if (!merged) return;
    const m = new THREE.Mesh(merged, bin.mat); m.userData.own = true;
    m.castShadow = bin.objs.some((o) => o.castShadow); m.receiveShadow = bin.objs.some((o) => o.receiveShadow);
    if (bin.objs.some((o) => o.userData.rbWall)) m.userData.rbWall = true;
    bin.objs.forEach((o) => root.remove(o)); root.add(m);
  });
  return root;
}
// a keyboard's face: four rows of dark keys with a lighter top edge, a space bar
function rbKeysTex() {
  return TX.rbKeys || (TX.rbKeys = ctex(256, 72, (g, W, H) => {
    g.fillStyle = '#0b1016'; g.fillRect(0, 0, W, H);
    const rows = 4, kw = (W - 12) / 14, kh = (H - 10) / rows;
    for (let r = 0; r < rows; r++) for (let c = 0; c < 14; c++) {
      if (r === 3 && c > 3 && c < 10) { if (c === 4) { g.fillStyle = '#232c36'; g.fillRect(6 + c * kw + 1, 5 + r * kh + 1, kw * 6 - 2, kh - 3); } continue; }
      g.fillStyle = '#232c36'; g.fillRect(6 + c * kw + 1, 5 + r * kh + 1, kw - 2, kh - 3);
      g.fillStyle = '#3a4653'; g.fillRect(6 + c * kw + 1, 5 + r * kh + 1, kw - 2, 1.5);
    }
  }));
}
// his Agent League monitor: lines of green text on near-black, as a terminal shows them
function rbTermTex() {
  return TX.rbTerm || (TX.rbTerm = ctex(256, 144, (g, W, H) => {
    const R = rng(23); g.fillStyle = '#03120d'; g.fillRect(0, 0, W, H);
    g.fillStyle = '#38f5b8'; g.fillRect(12, 10, 64, 7);
    for (let y = 26; y < H - 10; y += 10) {
      let x = 12; while (x < W - 30) { const w = 8 + Math.floor(R() * 34); g.globalAlpha = 0.45 + R() * 0.5; g.fillRect(x, y, Math.min(w, W - 12 - x), 5); x += w + 6 + Math.floor(R() * 8); if (R() < 0.18) break; }
    }
    g.globalAlpha = 1;
  }));
}
// the league's table on its standing board: ranks, a bar for each score, the leader lit
function rbLeagueTex() {
  return TX.rbLeague || (TX.rbLeague = ctex(256, 288, (g, W, H) => {
    g.fillStyle = '#060b11'; g.fillRect(0, 0, W, H);
    g.strokeStyle = 'rgba(176,196,208,.45)'; g.lineWidth = 3; g.strokeRect(6, 6, W - 12, H - 12);
    g.fillStyle = '#38f5b8'; g.font = '700 22px JetBrains Mono, monospace'; g.textBaseline = 'top'; g.fillText('LEAGUE', 20, 20);
    for (let i = 0; i < 8; i++) {
      const y = 58 + i * 27, lead = i === 0;
      g.fillStyle = lead ? 'rgba(56,245,184,.16)' : 'rgba(143,168,194,.05)'; g.fillRect(16, y - 3, W - 32, 22);
      g.fillStyle = lead ? '#38f5b8' : '#8fa8c2'; g.font = '600 15px JetBrains Mono, monospace'; g.fillText(String(i + 1), 24, y);
      g.fillStyle = lead ? '#38f5b8' : i < 3 ? '#24e8ff' : 'rgba(143,168,194,.55)'; g.fillRect(52, y + 4, (W - 120) * (1 - i * 0.1), 8);
    }
  }));
}
function candleTex() {
  if (TX.candle) return TX.candle;
  const c = document.createElement('canvas'); c.width = 512; c.height = 256; const g = c.getContext('2d');
  g.fillStyle = '#140b04'; g.fillRect(0, 0, 512, 256); g.strokeStyle = '#ff9438'; g.lineWidth = 5; g.strokeRect(3, 3, 506, 250);
  // its grid, the price scale down the right, the volume along the foot, then the candles over them
  g.strokeStyle = 'rgba(255,148,56,.14)'; g.lineWidth = 1;
  for (let y = 56; y < 220; y += 28) { g.beginPath(); g.moveTo(14, y); g.lineTo(440, y); g.stroke(); g.fillStyle = 'rgba(255,170,82,.45)'; g.fillRect(452, y - 3, 44, 6); }
  g.fillStyle = 'rgba(255,148,56,.3)'; for (let i = 0; i < 16; i++) g.fillRect(26 + i * 26, 238 - ((i * 13) % 20), 14, (i * 13) % 20 + 4);
  let v = 140; for (let i = 0; i < 16; i++) { const up = [1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1][i], o = v; v = Math.max(60, Math.min(200, v + (up ? -14 : 12))); g.fillStyle = up ? '#38f5b8' : '#ff8824'; g.fillRect(24 + i * 26, Math.min(o, v), 16, Math.max(6, Math.abs(o - v))); g.fillRect(31 + i * 26, Math.min(o, v) - 10, 3, Math.abs(o - v) + 20); }
  g.fillStyle = '#38f5b8'; g.fillRect(446, v - 9, 54, 18);
  g.fillStyle = '#ffaa52'; g.font = '700 22px JetBrains Mono, monospace'; g.fillText('BASKET H2 · +1.1%', 22, 34);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; TX.candle = t; return t;
}
// a holographic pad: a rich turquoise-aquamarine grid inside a double glowing circle
function padTex() {
  if (TX.pad) return TX.pad;
  const c = document.createElement('canvas'); c.width = c.height = 512; const g = c.getContext('2d');
  g.save(); g.beginPath(); g.arc(256, 256, 250, 0, Math.PI * 2); g.clip();
  const gr = g.createRadialGradient(256, 256, 0, 256, 256, 250); gr.addColorStop(0, 'rgba(20,145,125,.0)'); gr.addColorStop(0.7, 'rgba(14,140,130,.02)'); gr.addColorStop(1, 'rgba(32,205,172,.07)');
  g.fillStyle = gr; g.fillRect(0, 0, 512, 512);
  g.strokeStyle = 'rgba(70,215,200,.13)'; g.lineWidth = 1;
  for (let p = 16; p < 512; p += 20) { g.beginPath(); g.moveTo(p, 0); g.lineTo(p, 512); g.stroke(); g.beginPath(); g.moveTo(0, p); g.lineTo(512, p); g.stroke(); }
  g.restore();
  g.strokeStyle = 'rgba(56,232,196,.72)'; g.lineWidth = 7; g.beginPath(); g.arc(256, 256, 245, 0, Math.PI * 2); g.stroke();
  g.strokeStyle = 'rgba(36,208,225,.48)'; g.lineWidth = 3; g.beginPath(); g.arc(256, 256, 224, 0, Math.PI * 2); g.stroke();
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; TX.pad = t; return t;
}
function moodTex() {
  const c = document.createElement('canvas'); c.width = 512; c.height = 256; const g = c.getContext('2d');
  g.fillStyle = '#08121c'; g.fillRect(0, 0, 512, 256); g.strokeStyle = '#1c3248'; g.lineWidth = 5; g.strokeRect(3, 3, 506, 250);
  ['#24e8ff', '#38f5b8', '#3b82f6', '#ff8824'].forEach((col, i) => { g.fillStyle = col; g.fillRect(24 + i * 58, 28, 46, 46); });
  g.strokeStyle = '#7f93ad'; g.lineWidth = 3; g.strokeRect(24, 96, 220, 70); g.fillStyle = '#7f93ad'; g.fillRect(36, 110, 90, 10); g.fillStyle = '#182838'; g.fillRect(36, 132, 160, 8);
  g.strokeStyle = '#24e8ff'; g.setLineDash([10, 8]); g.strokeRect(270, 28, 214, 200);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

class Office3D {
  constructor(el, stage, tipFor) {
    geo(); omats();
    CO.o3 = this;   // a handle for looking at the office from the console, as CO.uv is for the map
    this.el = el; this.stage = stage; this.tipFor = tipFor;
    this.tip = stage.querySelector('.tip'); this.layer = stage.querySelector('.o3layer');
    this.sel = null; this.cells = {}; this.paths = {}; this.packets = []; this.rooms = {}; this.fitted = false; this.hover = null;
    this.mouse = new THREE.Vector2(); this.ray = new THREE.Raycaster();
    this.scene = new THREE.Scene(); this.scene.background = new THREE.Color(LOOK.sky); this.scene.fog = new THREE.Fog(LOOK.sky, 180, 460);
    this.camera = new THREE.PerspectiveCamera(CAM.fov, 2, 0.5, 900);
    this.renderer = new THREE.WebGPURenderer({ antialias: false });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping; this.renderer.toneMappingExposure = 1.0;
    this.renderer.shadowMap.enabled = true; this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    el.appendChild(this.renderer.domElement);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    Object.assign(this.controls, { enableDamping: true, dampingFactor: 0.08, minDistance: 10, maxDistance: 220, maxPolarAngle: Math.PI * 0.47, minPolarAngle: 0.2,
      screenSpacePanning: false, zoomSpeed: 0.9, rotateSpeed: 0.55 });
    this.controls.addEventListener('start', () => { this.tw = null; this.moved = true; });
    // a hand on the office, for the pacer: the controls moving the camera (also while it settles) and the mouse
    this.controls.addEventListener('change', () => { this.lastInput = performance.now(); });
    this.pace = pacer(() => !!this.tw || performance.now() - (this.lastInput || 0) < 1500);
    const S = this.scene;
    S.environment = envTex(); S.environmentIntensity = 0.9;
    // his picture is lit like a studio: soft white light from above and the camera's side, everything readable, the
    // colour only where something glows. No coloured fill: it tinted every surface teal.
    S.add(new THREE.HemisphereLight(0xe2ecf6, 0x10161e, 0.6), new THREE.AmbientLight(0x2a3644, 0.4));
    this.sun = new THREE.DirectionalLight(0xffffff, 1.5); this.sun.castShadow = true; this.sun.shadow.mapSize.set(2048, 2048);
    this.sun.shadow.normalBias = 0.02; this.sun.shadow.bias = -0.0005; S.add(this.sun); S.add(this.sun.target);
    const rim = new THREE.DirectionalLight(0xb8dcf4, 0.45); rim.position.set(-34, 14, -42); S.add(rim);
    const under = new THREE.DirectionalLight(0x8aa4c0, 0.55); under.position.set(22, -24, 44); S.add(under);
    // a soft light from the camera's own side, as a studio render has: every face turned to the viewer is readable,
    // the hull's two visible sides alike (the sun lights only the one it faces)
    this.fill = new THREE.DirectionalLight(0xdfe8f2, 1.7); S.add(this.fill); S.add(this.fill.target);
    this.sky = spaceSky(true); S.add(this.sky);
    this.world = new THREE.Group(); S.add(this.world);
    this.pk = new THREE.Group(); S.add(this.pk);
    this.clock = new THREE.Clock();
    this.bind();
    this.renderer.init().then(() => {
      // bloom tight round what glows: a wide one flooded every floor mint from the neon (measured 2026-10-18)
      try { this.post = new Post(this.renderer, this.scene, this.camera, 0.32, 0.0, 0.86, { sat: 0.96 }); }
      catch (e) { this.post = null; }
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
    // the flat office's plan: the Manager in the middle, the weekly audit and the vault in their fixed corners (the
    // vault in front, where his screenshot had an empty notch), the departments in their slots
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
    const pad = 0.5, T = 0.35, have = {}, kc = (x, y) => x + ',' + y;
    all.forEach((c) => { have[kc(c[0], c[1])] = 1; });
    this.corners = []; const outer = [];
    all.forEach((c) => {
      const s = new THREE.Mesh(G.box, [OM.rimDark, OM.rimDark, OM.deck, OM.rimDark, OM.rimDark, OM.rimDark]);
      s.scale.set(RS + 2 * pad, T, RS + 2 * pad); s.position.copy(this.V(c[0] + RS / 2, c[1] + RS / 2, -T / 2)); s.receiveShadow = true; W.add(s);
      const x0 = c[0] - pad, y0 = c[1] - pad, x1 = c[0] + RS + pad, y1 = c[1] + RS + pad;
      // a side is the outside when no room's slab meets it there
      [[x0, y0, x1, y0, !have[kc(c[0], c[1] - 8)], 0, -1], [x0, y1, x1, y1, !have[kc(c[0], c[1] + 8)], 0, 1], [x0, y0, x0, y1, !have[kc(c[0] - 8, c[1])], -1, 0], [x1, y0, x1, y1, !have[kc(c[0] + 8, c[1])], 1, 0]].forEach(([ax, ay, bx, by, out, nx, ny]) => {
        if (out) outer.push({ ax, ay, bx, by, nx, ny, c0: c[0], c1: c[1] });
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
      const mat = emis('#8cb8d0', 0.25), segs = [];
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
      const dept = (k !== 'hub' && k !== 'audit' && k !== 'vault' && k !== 'lot') ? CO.dept(+k.slice(1)) : null;
      const room = { key: k, dept, g, x0: c[0], y0: c[1], agents: [], screens: [], mons: [], born: born && k === 'd' + born };
      this.rooms[k] = room;
      if (k === 'lot') return this.lotRoom(room);
      this.shell(room);
      if (k === 'hub') this.hubRoom(room); else if (k === 'audit') this.auditRoom(room); else if (k === 'vault') this.vaultRoom(room); else this.deptRoom(room, dept);
      const hit = new THREE.Mesh(G.box, M.hit); hit.scale.set(RS, WH, RS); hit.position.copy(this.V(c[0] + RS / 2, c[1] + RS / 2, WH / 2)); hit.userData.key = k; g.add(hit); this.hits.push(hit);
      if (room.born) { g.scale.set(1, 0.01, 1); room.grow = performance.now(); }
    });
    this.bakeRooms();
    // the plates wait hidden until a frame has put them over their rooms: while the 3D was starting they sat in a
    // heap at the stage's top left ("jak nacita mapa tak vlevo nahore sou nejake nesmysly"); labels() shows them
    Array.prototype.forEach.call(this.layer.children, (el) => { el.style.display = 'none'; el._off = true; });
    this.selRing = new THREE.Group(); W.add(this.selRing);
    this.update();
    if (!this.fitted) { this.fit(false); }
  }
  // every room's still parts merged per material (bakeRoom): the same picture in a fraction of the draw calls
  bakeRooms() { this.baked = 0; Object.values(this.rooms).forEach((r) => { if (r.g) this.baked += bakeRoom(r); }); }
  // Under and round the deck, what makes it a station in space: a rim, a plated hull with its lights, a stepped
  // keel, the rock it is built on, engines, solar wings, asteroids drifting past. Static parts merged per
  // material.
  exterior(all, outer, have, pad, T) {
    const W = this.world, RS = CO.iso.RS, ext = new THREE.Group(), HD = 1.65, R = rng(17), kc = (x, y) => x + ',' + y; W.add(ext);
    all.forEach((c) => {
      const Lf = !have[kc(c[0] - 8, c[1])], Rt = !have[kc(c[0] + 8, c[1])], Bk = !have[kc(c[0], c[1] - 8)], Fr = !have[kc(c[0], c[1] + 8)];
      const x0 = c[0] - pad, y0 = c[1] - pad, x1 = c[0] + RS + pad, y1 = c[1] + RS + pad;
      const tier = (ins, z0, h, mat) => this.box(ext, x0 + (Lf ? ins : 0), y0 + (Bk ? ins : 0), z0, x1 - x0 - (Lf ? ins : 0) - (Rt ? ins : 0), y1 - y0 - (Bk ? ins : 0) - (Fr ? ins : 0), h, mat, false);
      tier(0.12, -T - 0.12 - HD, HD, OM.hull).geometry = exHullBox((c[0] * 3 + c[1] * 5) / 8 % 6);
      tier(0.7, -T - 0.12 - HD - 0.48, 0.48, OM.hullLow);
      tier(1.4, -T - 0.12 - HD - 0.82, 0.34, OM.hullLow);
    });
    // the rim: a lighter lip round the outside of the deck, with small cyan beacon strips along the bevel
    outer.forEach((e, idx) => {
      const len = Math.hypot(e.bx - e.ax, e.by - e.ay) + 0.44, mx = (e.ax + e.bx) / 2 + e.nx * 0.11, my = (e.ay + e.by) / 2 + e.ny * 0.11, along = e.ax === e.bx;
      this.rb(ext, mx - (along ? 0.12 : len / 2), my - (along ? len / 2 : 0.12), -T - 0.14, along ? 0.24 : len, along ? len : 0.24, T + 0.16, OM.rim, 0.1, false);
      if (idx % 2 === 0) {
        const bx = (e.ax + e.bx) / 2 + e.nx * 0.24, by = (e.ay + e.by) / 2 + e.ny * 0.24;
        this.box(ext, bx - (along ? 0.03 : 0.42), by - (along ? 0.42 : 0.03), -T * 0.55, along ? 0.05 : 0.84, along ? 0.84 : 0.05, 0.05, OM.cyan.rim, false);
      }
    });
    let mnx = 1e9, mxx = -1e9, mny = 1e9, mxy = -1e9;
    all.forEach((c) => { mnx = Math.min(mnx, c[0]); mxx = Math.max(mxx, c[0] + RS); mny = Math.min(mny, c[1]); mxy = Math.max(mxy, c[1] + RS); });
    const cxp = (mnx + mxx) / 2, cyp = (mny + mxy) / 2, span = Math.max(mxx - mnx, mxy - mny), keel = -T - HD - 0.95;
    // The rock: one craggy mass under the whole station, biased to the front-left as his is, with lumps of it
    // breaking out under the audit room and the lot where his shows a shoulder past the hull, and nothing under
    // the right side, where his picture shows only space. Turned about the vertical only, so every flat top stays
    // against the keel. The geometries are made once (a layout runs on every change of shape).
    // under 70,000 triangles for all of it: the planes need few, the grain is the material's
    G.exRockA = G.exRockA || exRockGeo(11, 34, 1.7, true, 0.3); G.exRockB = G.exRockB || exRockGeo(29, 22, 1.3, true, 0.3);
    G.exRockC = G.exRockC || exRockGeo(47, 22, 1.15, false, 0.34);
    // a flat lump's top sits at the keel; a round one (what breaks out past the hull) hangs dz below it, so what
    // shows past the hull is crag, not a shelf
    const lump = (geom, x, y, sx, sy, sz, yaw, dz) => { const m = new THREE.Mesh(geom, OM.rock); m.scale.set(sx, sy, sz); m.rotation.set(dz == null ? 0 : 0.25, yaw, dz == null ? 0 : -0.2); m.position.copy(this.V(x, y, dz == null ? keel + 0.2 - 0.26 * sy : keel - dz)); ext.add(m); };
    // the main mass follows the platform as it grows; the lumps that break out sit under fixed rooms
    lump(G.exRockA, cxp - 1, cyp + 1.8, span * 0.483, 5.8, span * 0.483, 0.4);
    lump(G.exRockB, 19, 19.5, 4.0, 4.6, 3.5, 2.3);
    lump(G.exRockC, 18.6, 21.4, 4.2, 3.6, 3.6, 5.2, 4.7);
    lump(G.exRockC, 4.6, 22, 4.6, 3.6, 4.1, 0.7, 4.0);
    lump(G.exRockC, 12.8, 21.4, 3.6, 3.2, 3.7, 3.3, 4.2);
    // What hangs on the outside, where his picture has it, now that the vault fills the front corner (his notch
    // is gone, so what it carried moved to the vault's two faces). Every engine and thruster points straight out
    // of the face it sits on -- an exact axis, no yaw, no tilt -- and no two things share a stretch of face, so
    // nothing is drawn over a panel from any side:
    //   the long nacelle along the back-left room, two engines on it throwing blue plumes (his top left);
    //   the big engine under the front of the lot (his front left); small thrusters on the audit room's front,
    //   the vault's right face and the agent league's right face; a row of five panels hung under the vault's
    //   front (his bottom centre), four under the trading desk's right side, two pairs standing on the back edge
    //   behind the laboratory. Each looked up by its room's cell and face, and left out when that face is not
    //   on the outside.
    exMats();
    this.flames = []; const tag = [], busy = new Map();
    const edge = (c0, c1, nx, ny) => outer.find((o) => o.c0 === c0 && o.c1 === c1 && o.nx === nx && o.ny === ny);
    // a point on an edge's hull face (the hull sits 0.12 in from the deck's edge): f along it, out from it, at z
    const onFace = (e, f, out = 0) => { const s = e.nx ? Math.min(e.ay, e.by) : Math.min(e.ax, e.bx), l = Math.abs(e.bx - e.ax) + Math.abs(e.by - e.ay), t = s + f * l, k = -0.12 + out;
      return e.nx ? { x: e.ax + e.nx * k, y: t } : { x: t, y: e.ay + e.ny * k }; };
    // what holds a stretch of face: 'e' an engine or thruster on the hull itself, 'p' a panel rail at its foot,
    // 'n' the nacelle or the panel stands, above the hull's top edge
    const claim = (e, f0, f1, kind = 'e') => { const k = e.c0 + ',' + e.c1 + ',' + e.nx + ',' + e.ny; (busy.get(k) || busy.set(k, []).get(k)).push([f0, f1, kind]); };
    // a part's own frame on a face: +z straight out of it, +y up
    const mount = (e, f, z, out = 0) => { const p = onFace(e, f, out), g = new THREE.Group(); g.position.copy(this.V(p.x, p.y, z)); g.rotation.y = Math.atan2(e.nx, e.ny); ext.add(g); return g; };
    const flame = (halo, base) => this.flames.push({ glow: halo, ph: R() * 6, base });
    const ePort = edge(0, 8, -1, 0);
    if (ePort) {
      // the nacelle: a long rounded grey body along the room's outer wall at deck height, a dark spine along its
      // top, seams across it, vents on its side; an engine on its outer side near each end
      const nac = mount(ePort, 0.5, 0.08, 0.6);
      exPart(nac, rboxGeo(7.0, 1.0, 1.2, 0.36), OM.exGunL, 0, 0, 0, 1, 1, 1);
      exPart(nac, rboxGeo(6.4, 0.12, 0.34, 0.05), OM.exGunD, 0, 0.52, -0.05, 1, 1, 1);
      [-2.6, -0.9, 0.9, 2.6].forEach((x) => exPart(nac, G.box, OM.exGunD, x, 0, 0, 0.04, 1.02, 1.22));
      [-1.75, 0, 1.75].forEach((x) => { exPart(nac, G.box, OM.exGunD, x, -0.12, 0.6, 0.6, 0.3, 0.04); for (let k = 0; k < 4; k++) exPart(nac, G.box, OM.exGun, x - 0.22 + k * 0.146, -0.12, 0.615, 0.05, 0.26, 0.03); });
      [0.18, 0.82].forEach((f) => {
        const g = mount(ePort, f, 0.18, 1.2); flame(exBackEngine(g), 0.3);
        tag.push({ kind: 'engine', name: 'back@' + f, obj: g });
      });
      claim(ePort, 0, 1, 'n');
    }
    const eLot = edge(8, 16, 0, 1);
    if (eLot) {
      const g = mount(eLot, 0.44, -1.45); g.scale.setScalar(0.95); exBigEngine(g);
      tag.push({ kind: 'engine', name: 'big', obj: g }); claim(eLot, 0.3, 0.58);
    }
    [[edge(0, 16, 0, 1), 0.36], [edge(16, 16, 1, 0), 0.4], [edge(16, 8, 1, 0), 0.62]].forEach(([e, f]) => {
      if (!e) return;
      const g = mount(e, f, -1.25); flame(exThruster(g), 0.1);
      tag.push({ kind: 'engine', name: 'thr' + e.c0 + ',' + e.c1, obj: g }); claim(e, f - 0.08, f + 0.08);
    });
    // a row of n panels w by h hung from a rail at the hull's foot, from f0 to f1 along the edge, each swung out
    // from hanging straight down by tilt, its cells to the sky and the camera; on short silver arms
    const hangRow = (e, n, f0, f1, w, h, tilt) => {
      const rail = mount(e, (f0 + f1) / 2, -2.04, 0.16), L = (f1 - f0) * 8;
      exPart(rail, G.exRod, OM.exGun, 0, 0, 0, 0.05, 0.05, L + 0.3, 0, Math.PI / 2, 0);
      for (let i = 0; i <= n; i++) exPart(rail, G.box, OM.exFrame, -L / 2 + i * L / n, 0.02, -0.08, 0.08, 0.1, 0.2);
      for (let i = 0; i < n; i++) {
        const p = new THREE.Group(); p.position.set(-L / 2 + (i + 0.5) * L / n, -0.05, 0.06); p.rotation.x = Math.PI / 2 - tilt; rail.add(p);
        exPanel(p, w, h); exPart(p, G.box, OM.exFrame, 0, -0.06, 0.12, 0.08, 0.05, 0.3);
        tag.push({ kind: 'panel', name: 'panel' + e.c0 + ',' + e.c1 + '#' + i, obj: p, group: 'row' + e.c0 + ',' + e.c1 });
      }
      claim(e, f0, f1, 'p');
    };
    const eVault = edge(16, 16, 0, 1);
    if (eVault) hangRow(eVault, 5, 0.16, 0.94, 1.12, 1.6, 0.9);
    const eDesk = edge(16, 0, 1, 0);
    if (eDesk) hangRow(eDesk, 4, 0.06, 0.94, 1.64, 1.75, 0.85);
    // his two pairs behind the laboratory stand on brackets off the deck's back edge, leaning back, their cells
    // turned to the room and the camera, taller than its wall
    const eLab = edge(8, 0, 0, -1);
    if (eLab) {
      [0.24, 0.76].forEach((f, j) => {
        const base = mount(eLab, f, -0.05, 0.62), lean = 0.6;
        exPart(base, G.box, OM.exGun, 0, -0.05, -0.2, 3.3, 0.12, 0.5);
        [-0.83, 0.83].forEach((x) => {
          const p = new THREE.Group(); p.position.set(x, 0.05, 0); p.rotation.x = lean - Math.PI / 2; base.add(p);
          exPanel(p, 1.6, 1.45);
          tag.push({ kind: 'panel', name: 'stand' + j + (x > 0 ? 'b' : 'a'), obj: p, group: 'pair' + j });
        });
        // two legs behind them, from the bracket's outer edge up to the panels' backs
        [-1.2, 1.2].forEach((x) => exStrut(base, new THREE.Vector3(x, -0.02, 0.85), new THREE.Vector3(x, 0.05 + Math.cos(lean) * 0.8 - 0.05, Math.sin(lean) * 0.8 + 0.06), 0.06, OM.exFrame));
      });
      claim(eLab, 0, 1, 'n');
    }
    // The hull's own detail: his modules are light silver boxes standing out from the navy plating -- a dark window
    // with a pale-blue lit strip across its top, a grille and a status light below -- two to a room's side, where no
    // engine sits; between them a slatted vent, a pipe run along the foot on brackets, a small light in the top band
    outer.forEach((e) => {
      const k = e.c0 + ',' + e.c1 + ',' + e.nx + ',' + e.ny, used = busy.get(k) || [];
      const free = (f, kinds = 'ep', m = 0.06) => !used.some(([a, b, kd]) => kinds.includes(kd) && f > a - m && f < b + m);
      [0.27, 0.73].forEach((f, n) => {
        if (!free(f, 'e', 0.14)) return;
        const g = mount(e, f, -1.22, 0);
        exPart(g, rboxGeo(1.56, 0.8, 0.14, 0.03), OM.exModule, 0, 0, 0.07, 1, 1, 1);
        exPart(g, G.box, OM.exModuleD, 0, 0.13, 0.145, 1.3, 0.32, 0.02);
        exPart(g, G.box, OM.exStrip, 0, 0.22, 0.158, 1.12, 0.055, 0.01);
        exPart(g, G.box, OM.exModuleD, 0, -0.04, 0.143, 1.38, 0.02, 0.01);
        for (let s = 0; s < 7; s++) exPart(g, G.box, OM.exModuleD, -0.56 + s * 0.1, -0.21, 0.145, 0.045, 0.22, 0.02);
        exPart(g, G.box, n ? OM.exLedC : OM.exLedG, 0.55, -0.23, 0.148, 0.11, 0.06, 0.02);
      });
      const run = []; for (let f = 0.04; f <= 0.96; f += 0.04) if (free(f)) run.push(f);
      for (let i = 0; i < run.length;) {
        let j = i; while (j + 1 < run.length && run[j + 1] - run[j] < 0.05) j++;
        if (run[j] - run[i] > 0.2) {
          const g = mount(e, (run[i] + run[j]) / 2, -1.97, 0.07), L = (run[j] - run[i]) * 8;
          exPart(g, G.exRod, OM.exGun, 0, 0, 0, 0.04, 0.04, L, 0, Math.PI / 2, 0);
          for (let b = 0; b <= Math.floor(L / 1.6); b++) exPart(g, G.box, OM.exGunD, -L / 2 + b * L / Math.max(1, Math.floor(L / 1.6)), 0, -0.035, 0.09, 0.12, 0.08);
        }
        i = j + 1;
      }
      if (free(0.5, 'e', 0.08)) {
        const g = mount(e, 0.5, -1.45, 0.02);
        exPart(g, G.box, OM.exGunD, 0, 0, 0, 0.62, 0.42, 0.05);
        for (let s = 0; s < 4; s++) exPart(g, G.box, OM.exGun, -0.21 + s * 0.14, 0, 0.03, 0.06, 0.34, 0.03);
        exPart(mount(e, 0.5, -0.62, 0.01), G.box, e.c0 % 16 ? OM.exLedC : OM.exLedG, 0, 0, 0, 0.18, 0.05, 0.03);
      }
    });

    // where each engine and panel is, read before the merge: what a test checks for one drawn over another
    ext.updateMatrixWorld(true);
    this.exBoxes = tag.map((t) => ({ kind: t.kind, name: t.name, group: t.group, box: new THREE.Box3().setFromObject(t.obj) }));
    bakeGroup(ext);
    // the rock takes the station's shadow but casts none: below everything, it has nothing to throw one on, and a
    // shadow caster is drawn twice
    ext.traverse((o) => { if (o.isMesh && o.material === OM.rock) o.receiveShadow = true; });
    // Cratered moonlet in the top-right sky and small asteroids drifting round the station
    this.drift = [];
    // his moonlet hangs top right, behind the trading desk (plan 19, -7 at the height his pixels give)
    G.exMoon = G.exMoon || exMoonGeo(53);
    const big = new THREE.Mesh(G.exMoon, OM.exMoon); big.scale.set(0.74, 0.8, 0.7);
    big.position.copy(this.V(18.6, -7.4, 2.5)); W.add(big); this.drift.push({ m: big, sp: 0.03 });
    for (let i = 0; i < 12; i++) {
      const a = R() * Math.PI * 2; if ((Math.cos(a) + Math.sin(a)) / Math.SQRT2 > 0.2) { i--; continue; }
      const d = span * (0.85 + R() * 0.7), s = 0.3 + R() * R() * 1.35, m = new THREE.Mesh(G.smallRock, OM.rockS);
      m.scale.set(s, s * 0.8, s * 0.9); m.position.copy(this.V(cxp + Math.cos(a) * d, cyp + Math.sin(a) * d, -9 + R() * 12)); m.rotation.set(R() * 3, R() * 3, R() * 3);
      W.add(m); this.drift.push({ m, sp: 0.06 + R() * 0.18 });
    }
  }
  // A room as in his picture: a slate-blue tiled floor, low panes of pale frosted glass, and ONE neon line that
  // traces the room's outline as the camera sees it -- along the top of the two back walls and along the foot of
  // the two front walls ("vpredu sviti spodni listy a v zadnich stenach ty vrchni"). The glass's own edges, the
  // front walls' tops and the corners, are a thin pale line. Mint, the trading desk orange.
  shell(r) {
    const { g, x0, y0 } = r, RS = CO.iso.RS, H = WH, t = 0.04, z0 = 0.08;
    const dk = r.dept && r.dept.key;
    const isOrange = dk === 'trading_desk';
    this.box(g, x0, y0, 0, RS, RS, z0, r.key === 'hub' ? OM.hubTile : isOrange ? OM.tileOrange : OM.tile);
    r.glow = new THREE.Mesh(G.plane, new THREE.MeshBasicMaterial({ map: radialTex('255,255,255', 0.85), transparent: true, opacity: 0.04, blending: THREE.AdditiveBlending, depthWrite: false, color: isOrange ? 0xff8824 : 0x7cf2c4 }));
    r.glow.scale.set(RS * 0.92, RS * 0.92, 1); r.glow.rotation.x = -Math.PI / 2; r.glow.position.copy(this.V(x0 + RS / 2, y0 + RS / 2, z0 + 0.01)); g.add(r.glow);
    const glassMat = isOrange ? OM.glassOrange : OM.glass;
    // one pane per wall: a box's six faces stacked their opacity into a milky slab
    [[x0 + RS / 2, y0, 0], [x0 + RS / 2, y0 + RS, 0], [x0, y0 + RS / 2, Math.PI / 2], [x0 + RS, y0 + RS / 2, Math.PI / 2]].forEach(([x, y, rot]) => {
      const p = new THREE.Mesh(G.plane, glassMat); p.scale.set(RS, H, 1); p.rotation.y = rot; p.position.copy(this.V(x, y, z0 + H / 2)); p.renderOrder = 2; g.add(p);
    });
    if (r.key !== 'hub') { this.box(g, x0 + t, y0 + t, z0, RS - 2 * t, 0.1, 0.52, OM.wallDark); this.box(g, x0 + t, y0 + t, z0, 0.1, RS - 2 * t, 0.52, OM.wallDark); }
    r.edgeM = emis(isOrange ? LOOK.orange : LOOK.neon, 2.2);
    const e = 0.058, zt = z0 + H - e, f = 0.022;   // his neon is a thicker soft line than a hairline
    // the neon: back walls' tops (y = y0 along x, x = x0 along y), front walls' feet
    [[x0, y0, zt, RS, e], [x0, y0, zt, e, RS], [x0, y0 + RS - e, z0, RS, e], [x0 + RS - e, y0, z0, e, RS]].forEach(([x, y, z, w, d]) => this.box(g, x, y, z, w, d, e, r.edgeM, false));
    // the glass's edges: the front walls' tops and the four corners
    [[x0, y0 + RS - f, z0 + H - f, RS, f, f], [x0 + RS - f, y0, z0 + H - f, f, RS, f],
      [x0, y0, z0, f, f, H], [x0 + RS - f, y0, z0, f, f, H], [x0, y0 + RS - f, z0, f, f, H], [x0 + RS - f, y0 + RS - f, z0, f, f, H]].forEach(([x, y, z, w, d, h]) => this.box(g, x, y, z, w, d, h, OM.glassEdge, false));
    // the room's own light: white over the floor, warm in the trading desk
    // the light stays in its room: an orange one reaching the neighbours tinted their floors
    r.lamp = new THREE.PointLight(isOrange ? 0xff6a34 : 0xeef6ff, isOrange ? 22 : 6, isOrange ? 6.5 : 9, 1.0);
    r.lamp.position.copy(this.V(x0 + RS / 2, y0 + RS / 2, isOrange ? 2.4 : 4.4)); g.add(r.lamp);
  }
  // a wall screen on the back wall: what runs now, or why it waits
  wallScreen(r, u0, u1) {
    const s = screen(u1 - u0, RBW.h);
    this.rbPanel(r, 'x', u0, u1, RBW.h, new THREE.MeshBasicMaterial({ map: s.tex, toneMapped: false }));
    r.wall = s; return s;
  }
  kanban(r, v0 = 1.5, v1 = 5.8) {
    const s = screen(v1 - v0, RBW.h);
    this.rbPanel(r, 'y', v0, v1, RBW.h, new THREE.MeshBasicMaterial({ map: s.tex, toneMapped: false }));
    r.kb = s;
  }
  // His wall screens are long low panels hung mid-wall, every one wholly under the top neon with a clear gap
  // ("nikde se obrazovka neprekryva s hornim neonovym panelem"): a dark bezel round the face, on two short brackets
  // that stand on the dark wainscot. Along the back wall at y0 ('x') or the one at x0 ('y'), from a0 to a1; the face
  // h high, centred at RBW.mid, so the bezel's top stays at RBW.top or under it.
  rbPanel(r, along, a0, a1, h, faceMat) {
    if (!OM.rbBezel) OM.rbBezel = std({ color: 0x141b23, roughness: 0.38, metalness: 0.5 });
    const g = r.g, L = a1 - a0, zc = RBW.mid, alongX = along === 'x', tag = (m) => { m.userData.rbWall = true; return m; };
    const at = (a, d, z) => alongX ? this.V(r.x0 + a, r.y0 + d, z) : this.V(r.x0 + d, r.y0 + a, z);
    const bz = new THREE.Mesh(rboxGeo(L + 0.08, h + 0.08, 0.06, 0.02), OM.rbBezel);
    bz.position.copy(at((a0 + a1) / 2, 0.08, zc)); if (!alongX) bz.rotation.y = Math.PI / 2; bz.castShadow = true; bz.receiveShadow = true; g.add(tag(bz));
    const face = new THREE.Mesh(G.plane, faceMat); face.scale.set(L, h, 1); face.position.copy(at((a0 + a1) / 2, 0.115, zc));
    if (!alongX) face.rotation.y = Math.PI / 2; g.add(tag(face));
    // the brackets: from the wainscot's top (0.60) to the bezel
    const b0 = 0.6, b1 = zc - h / 2 - 0.04;
    [a0 + L * 0.14, a1 - L * 0.14].forEach((a) => {
      const p = new THREE.Mesh(G.box, OM.rbBezel); p.scale.set(alongX ? 0.05 : 0.07, b1 - b0, alongX ? 0.07 : 0.05); p.position.copy(at(a, 0.1, (b0 + b1) / 2)); g.add(tag(p));
    });
    return face;
  }
  // His desk, zoomed: a near-black block with a lighter top -- a side panel, a modesty panel at the back and a
  // pedestal of drawers on the right, room for the knees between -- one wide monitor on a neck and a foot, its glass
  // dark until its expert works, a keyboard with its keys, a white mouse, a mug. Baked to a few draw calls. The
  // trading desk keeps its own two screens (its room is drawn to his orange picture).
  desk(r, x, y, i, isOrange) {
    if (isOrange) return this.deskTD(r, x, y, i);
    rbMats();
    const g = new THREE.Group(); r.g.add(g);
    const league = r.dept && r.dept.run_kind === 'league';
    this.rb(g, x - 0.03, y - 0.03, 0.5, 1.96, 0.91, 0.06, OM.rbDeskTop, 0.02);
    this.rb(g, x + 0.01, y + 0.02, 0.1, 0.09, 0.82, 0.41, OM.rbDesk, 0.015);
    this.rb(g, x + 0.08, y + 0.04, 0.16, 1.2, 0.07, 0.35, OM.rbDesk, 0.012);
    this.rb(g, x + 1.26, y + 0.02, 0.1, 0.64, 0.82, 0.41, OM.rbDesk, 0.015);
    this.box(g, x + 0.03, y + 0.06, 0.08, 0.05, 0.74, 0.03, OM.rbSeam);
    this.box(g, x + 1.29, y + 0.06, 0.08, 0.58, 0.74, 0.03, OM.rbSeam);
    // the pedestal's three drawers: seams and pulls on its front, the face the room sees
    [0.235, 0.37].forEach((z) => this.box(g, x + 1.29, y + 0.835, z, 0.58, 0.008, 0.008, OM.rbSeam, false));
    [0.18, 0.305, 0.44].forEach((z) => this.box(g, x + 1.46, y + 0.838, z, 0.24, 0.012, 0.016, OM.rbMetal, false));
    // the monitor: a slim glossy bezel, its back housing, a neck and a foot
    const mx = x + 1.08, my = y + 0.2;
    this.rb(g, mx - 0.16, my - 0.1, 0.56, 0.32, 0.2, 0.018, OM.rbMetal, 0.008);
    const neck = this.part(g, G.box, OM.rbMetal, 0.075, 0.17, 0.03, mx, 0.655, my - 0.02); neck.rotation.x = -0.1;
    this.rb(g, mx - 0.25, my - 0.1, 0.76, 0.5, 0.06, 0.3, OM.rbGloss, 0.025);
    this.rb(g, mx - 0.47, my - 0.04, 0.64, 0.94, 0.035, 0.56, OM.rbGloss, 0.012);
    const scr = new THREE.MeshBasicMaterial({ map: league ? rbTermTex() : monTex(), color: new THREE.Color(0x0a1016), toneMapped: false });
    const face = new THREE.Mesh(G.plane, scr); face.scale.set(0.88, 0.5, 1); face.position.copy(this.V(mx, my - 0.004, 0.92)); g.add(face);
    // the keyboard near the desk's front, under the hands, its keys a texture; the mouse beside it, a mug
    this.rb(g, mx - 0.36, y + 0.62, 0.56, 0.68, 0.2, 0.024, OM.rbGloss, 0.008);
    const keys = new THREE.Mesh(G.plane, OM.rbKeys); keys.scale.set(0.64, 0.17, 1); keys.rotation.x = -Math.PI / 2; keys.position.copy(this.V(mx - 0.02, y + 0.72, 0.5855)); g.add(keys);
    const mouse = this.part(g, G.sphere, OM.rbMouse, 0.04, 0.022, 0.062, mx + 0.47, 0.578, y + 0.72);
    mouse.castShadow = false;
    this.cyl(g, x + 1.78, y + 0.3, 0.56, 0.046, 0.1, OM.rbMouse);
    rbBake(g);
    r.mons[i] = scr;
  }
  // the trading desk's own: a top on two side panels and a drawer unit, two screens on stands (one of candles), a
  // keyboard, a mug -- as it was, while that room is drawn to its picture
  deskTD(r, x, y, i) {
    const g = r.g, isOrange = true;
    this.rb(g, x + 0.02, y + 0.06, 0.08, 0.12, 0.72, 0.42, OM.desk, 0.03);
    this.rb(g, x + 1.76, y + 0.06, 0.08, 0.12, 0.72, 0.42, OM.desk, 0.03);
    this.rb(g, x + 1.12, y + 0.08, 0.08, 0.6, 0.68, 0.4, OM.desk, 0.03);
    for (let k = 0; k < 3; k++) this.box(g, x + 1.18, y + 0.76, 0.15 + k * 0.12, 0.48, 0.012, 0.09, OM.frame, false);
    this.rb(g, x - 0.03, y - 0.03, 0.5, 1.96, 0.91, 0.06, OM.deskTop, 0.025);
    const scr = new THREE.MeshBasicMaterial({ map: isOrange ? orangeMonTex() : monTex(), color: new THREE.Color(isOrange ? 0xffae52 : 0x0a1016), toneMapped: false });
    [x + 0.12, x + 0.98].forEach((mx, mi) => {
      this.cyl(g, mx + 0.39, y + 0.26, 0.56, 0.13, 0.02, OM.frame);
      this.box(g, mx + 0.36, y + 0.2, 0.58, 0.06, 0.05, 0.14, OM.frame, false);
      this.rb(g, mx, y + 0.12, 0.68, 0.8, 0.06, 0.46, OM.dark, 0.025);
      const faceMat = (isOrange && mi === 1) ? new THREE.MeshBasicMaterial({ map: candleTex(), toneMapped: false }) : scr;
      const face = new THREE.Mesh(G.plane, faceMat); face.scale.set(0.72, 0.38, 1); face.position.copy(this.V(mx + 0.4, y + 0.185, 0.91)); g.add(face);
    });
    this.rb(g, x + 0.66, y + 0.48, 0.56, 0.6, 0.2, 0.03, OM.frame, 0.01);
    this.cyl(g, x + 1.62, y + 0.6, 0.56, 0.05, 0.1, OM.white);
    r.mons[i] = scr;
  }
  // His astronaut, zoomed: a white suit shaded blue-grey, a big glossy blue helmet over a near-black visor, a white
  // life-support pack, a collar ring and a belt, a control box on the chest (it lights cyan at work), gloves, white
  // boots on dark soles, a patch on the left shoulder; seated, on his black office chair with its five-star base,
  // arms forward to the keyboard. Each half baked to a few draw calls; the chest light keeps its own.
  agent(r, x, y, i, label, opts) {
    rbMats();
    const at = this.V(x, y, 0.08), S = 1.0, standing = !!(opts && opts.stand);
    const cm = (geom, mat, px, py, pz, rx, sc) => { const m = new THREE.Mesh(geom, mat); m.position.set(px, py, pz); if (rx) m.rotation.x = rx; if (sc) m.scale.set(sc[0], sc[1], sc[2]); m.castShadow = true; m.receiveShadow = true; return m; };
    if (!standing) {
      const chair = new THREE.Group(); chair.position.copy(at); chair.scale.setScalar(S); r.g.add(chair);
      chair.add(cm(G.cyl, OM.rbChairMetal, 0, 0.23, 0.08, 0, [0.03, 0.3, 0.03]), cm(G.cyl, OM.rbChairMetal, 0, 0.375, 0.08, 0, [0.12, 0.03, 0.12]));
      for (let k = 0; k < 5; k++) {
        const a = k / 5 * Math.PI * 2 + 0.3, leg = cm(G.box, OM.rbChairMetal, Math.sin(a) * 0.13, 0.065, 0.08 + Math.cos(a) * 0.13, 0, [0.035, 0.03, 0.26]);
        leg.rotation.y = a; chair.add(leg, cm(G.sphere, OM.rbChair, Math.sin(a) * 0.25, 0.032, 0.08 + Math.cos(a) * 0.25, 0, [0.032, 0.032, 0.032]));
      }
      chair.add(cm(rboxGeo(0.46, 0.08, 0.44, 0.035), OM.rbChair, 0, 0.42, 0.06), cm(rboxGeo(0.44, 0.36, 0.07, 0.035), OM.rbChair, 0, 0.7, 0.38, -0.1),
        cm(G.box, OM.rbChairMetal, 0, 0.5, 0.33, 0, [0.05, 0.16, 0.025]));
      rbBake(chair);
    }
    const g = new THREE.Group(); g.position.copy(at); g.scale.setScalar(S); r.g.add(g);
    const up = new THREE.Group(); g.add(up);
    up.add(cm(G.rbTorso, OM.rbSuit, 0, 0.74, 0.03, 0, [1.06, 1, 0.92]), cm(rboxGeo(0.3, 0.14, 0.25, 0.05), OM.rbSuit, 0, 0.53, 0.01));
    up.add(cm(G.cyl, OM.rbJoint, 0, 0.6, 0.03, 0, [0.176, 0.045, 0.158]), cm(G.cyl, OM.rbCollar, 0, 0.99, 0.02, 0, [0.135, 0.06, 0.135]));
    up.add(cm(G.sphere, OM.rbHelmet, 0, 1.15, 0.01, 0, [0.205, 0.2, 0.205]));
    const visorM = OM.rbVisor.clone();
    up.add(cm(G.sphere, visorM, 0, 1.165, -0.085, 0, [0.168, 0.135, 0.13]));
    // the pack on the back: white, a darker panel and two cylinders of air along its sides
    up.add(cm(rboxGeo(0.36, 0.44, 0.17, 0.045), OM.rbPack, 0, 0.8, 0.21), cm(G.box, OM.rbJoint, 0, 0.86, 0.3, 0, [0.22, 0.15, 0.02]));
    [-1, 1].forEach((s) => up.add(cm(G.cyl, OM.rbPack, s * 0.2, 0.78, 0.2, 0, [0.04, 0.34, 0.04])));
    up.add(cm(rboxGeo(0.2, 0.12, 0.06, 0.02), OM.rbJoint, 0, 0.8, -0.15));
    const chest = cm(G.box, OM.pack, 0, 0.8, -0.183, 0, [0.12, 0.05, 0.01]); chest.userData.dyn = true; up.add(chest);
    [-1, 1].forEach((s) => up.add(cm(G.sphere, OM.rbSuit, s * 0.19, 0.92, 0.0, 0, [0.085, 0.08, 0.085])));
    const patch = cm(G.cyl, OM.rbPatch, -0.272, 0.87, -0.02, 0, [0.045, 0.012, 0.045]); patch.rotation.z = Math.PI / 2; up.add(patch);
    rbBake(up);
    // the arms go with the legs: forward to the keyboard while seated, down at the sides while standing or walking
    // (standing lifts the upper body by 0.1, so the standing arms are built that much higher)
    const sit = new THREE.Group(), stand = new THREE.Group(); g.add(sit, stand);
    const boot = (grp, px, pz) => { grp.add(cm(rboxGeo(0.13, 0.1, 0.21, 0.035), OM.rbPack, px, 0.07, pz), cm(rboxGeo(0.14, 0.03, 0.22, 0.012), OM.rbSole, px, 0.016, pz)); };
    [-1, 1].forEach((s) => {
      sit.add(cm(G.rbArm, OM.rbSuit, s * 0.215, 0.8, -0.08, 0.7), cm(G.rbFore, OM.rbSuit, s * 0.19, 0.69, -0.33, 1.38));
      sit.add(cm(G.cyl, OM.rbJoint, s * 0.2, 0.71, -0.2, 1.38, [0.058, 0.04, 0.058]), cm(G.sphere, OM.rbJoint, s * 0.17, 0.665, -0.5, 0, [0.06, 0.05, 0.075]));
      sit.add(cm(G.rbThigh, OM.rbSuit, s * 0.09, 0.5, -0.13, Math.PI / 2), cm(G.rbShin, OM.rbSuit, s * 0.09, 0.31, -0.29));
      sit.add(cm(G.cyl, OM.rbJoint, s * 0.09, 0.5, -0.27, 0, [0.075, 0.07, 0.075])); boot(sit, s * 0.09, -0.33);
      const ua = cm(G.rbArm, OM.rbSuit, s * 0.228, 0.91, 0.0), fa = cm(G.rbFore, OM.rbSuit, s * 0.248, 0.68, -0.025, 0.14);
      ua.rotation.z = s * 0.12; fa.rotation.z = s * 0.05; stand.add(ua, fa);
      stand.add(cm(G.cyl, OM.rbJoint, s * 0.24, 0.79, -0.005, 0, [0.058, 0.04, 0.058]), cm(G.sphere, OM.rbJoint, s * 0.252, 0.52, -0.05, 0, [0.06, 0.07, 0.06]));
      stand.add(cm(G.rbLeg, OM.rbSuit, s * 0.09, 0.37, 0.02), cm(G.cyl, OM.rbJoint, s * 0.09, 0.36, 0.02, 0, [0.078, 0.05, 0.078])); boot(stand, s * 0.09, -0.01);
    });
    rbBake(sit); rbBake(stand);
    sit.visible = !standing; stand.visible = standing;
    const ringM = emis('#00e5ff', 0); const ring = new THREE.Mesh(G.ring, ringM); ring.rotation.x = Math.PI / 2; ring.scale.setScalar(0.4); ring.position.y = 0.02; g.add(ring);
    const el = document.createElement('div'); el.className = 'a3'; el.textContent = label; this.layer.appendChild(el);
    // one sitting faces its desk; one standing faces the room and the camera (its visor looks down -z: turned 3/8 round)
    const a = { g, b: up, by: standing ? 0.1 : 0, ry: standing ? (opts.face != null ? opts.face : -Math.PI * 0.75) : 0, standing, sit, stand, visorM, chest, ring, ringM, el, home: g.position.clone(), phase: (i + r.x0 * 0.37) % 6.28, key: r.key + ':' + i, room: r, label };
    r.agents.push(a); return a;
  }
  plate(r, cls) {
    const el = document.createElement('div'); el.className = 'p3' + (cls ? ' ' + cls : ''); el.setAttribute('data-key', r.key); this.layer.appendChild(el);
    el.addEventListener('click', () => CO.emit('office:click', r.key));
    el.addEventListener('pointerenter', () => this.setHover(r.key)); el.addEventListener('pointerleave', () => this.setHover(null));
    // where his picture has every room's plate: the same spot in each room, found by sending its plates' centres
    // back through the fitted camera (4.4 across, 5.6 down, at 1.3 high)
    r.plate = el; r.plateAt = this.V(r.x0 + 4.4, r.y0 + 5.6, 1.3); return el;
  }
  // A department's room tailored to match look-office.webp:
  // - testing (Cymetica QA): a 3x3 window of light at the right end of the back-right wall + desks
  // - stranger (Outsider): twin-aisle Server Room with 2 rows of 4 tall dark server racks + workstation desk
  // - testing_lab (Laboratory): 3 glowing aqua-cyan specimen pods + floating crystals + canisters
  // - trading_desk (Trading Desk): panoramic warm amber-orange chart walls + dual-screen orange trading desks
  // - league (Agent League): a standing board with the league's table, green terminal monitors, a standing referee
  deptRoom(r, d) {
    const k = d.key, x0 = r.x0, y0 = r.y0, g = r.g; let u1 = 6.6;
    const isOrange = k === 'trading_desk';
    if (d.run_kind === 'stranger') {
      // his server room, rack for rack (their places read off his picture through the fitted camera): a darker,
      // glossy raised floor; three racks a hand apart along the back-right wall, a pair by the back corner,
      // three in a row towards the front, the workstation among them; the kanban low on the back-left wall, under
      // its neon as every board of his is
      this.rcServerFloor(r);
      this.racks(r, x0 + 2.95, y0 + 0.3, 3, 0.88);
      this.racks(r, x0 + 0.35, y0 + 1.3, 2, 0.88);
      this.racks(r, x0 + 3.1, y0 + 5.3, 3, 0.88);
      r.kb = this.rcBoard(r, 'left', 2.6, 5.6, null, { tiles: true });
      this.rcWorkstation(r, x0 + 3.4, y0 + 2.6, 0);
      this.holoFrame(r, x0 + 0.72, y0 + 3.98);
      const ex = d.experts.slice(0, 2);
      if (ex[0]) this.agent(r, x0 + 4.35, y0 + 3.9, 0, CO.expertName(ex[0]));
      if (ex[1]) this.agent(r, x0 + 1.6, y0 + 4.9, 1, CO.expertName(ex[1]), { stand: true });
      this.terminal(r, x0 + 0.3, y0 + 0.28, d.link || CO.DEPT_LINK[k] || CO.DEPT_LINK.custom);
      this.plant(r, x0 + 0.45, y0 + 6.5);
      this.plate(r);
      return;
    }
    if (k === 'development') {
      u1 = 3.3;
      this.racks(r, x0 + 0.55, y0 + 1.35, 3);
    } else if (k === 'testing') {
      // his Cymetica QA: a 3 x 3 window of light at the right end of the back-right wall, standing on the floor in a
      // dark frame; its top under the neon, as every screen of his ("nikde se obrazovka neprekryva s hornim
      // neonovym panelem")
      u1 = 4.6;
      const qa = (m) => { m.userData.rbWall = true; g.add(m); return m; };
      const qw = qa(new THREE.Mesh(G.plane, new THREE.MeshBasicMaterial({ map: qaGridTex(), color: new THREE.Color(0xffffff).multiplyScalar(1.15), toneMapped: false })));
      qw.scale.set(0.84, 0.84, 1); qw.position.copy(this.V(x0 + 6.0, y0 + 0.185, 0.82));
      if (!OM.rbBezel) OM.rbBezel = std({ color: 0x141b23, roughness: 0.38, metalness: 0.5 });
      const qf = qa(new THREE.Mesh(rboxGeo(1.02, 1.2, 0.1, 0.025), OM.rbBezel)); qf.position.copy(this.V(x0 + 6.0, y0 + 0.13, 0.08 + 0.6)); qf.castShadow = true; qf.receiveShadow = true;
      const qh = glowSprite(0x9ff5ec, 0.2, 1.4); qh.position.copy(this.V(x0 + 6.0, y0 + 0.35, 0.82)); g.add(qh);
    } else if (k === 'testing_lab') {
      // his laboratory: two display instruments with a hologram in each along the back-right wall, a tall analyser on
      // the left facing the room with a stool at it, a projector with a turning crystal of data in front of it and a
      // centrifuge beside that, canisters on a bench by the right wall and a dewar beside them. The desks, the
      // terminal, the frame and the wall screens are every room's (below). The analyser stands a metre off the wall
      // so it hides none of the board on it; the crystal stands left of the room's plate, where the home view sees it.
      u1 = 3.4;
      this.labMachine(r, x0 + 3.6, y0 + 0.2, 0);
      this.labMachine(r, x0 + 4.85, y0 + 0.2, 1);
      this.raAnalyser(r, x0 + 1.95, y0 + 5.25);
      this.raStool(r, x0 + 2.42, y0 + 5.68);
      this.labHolo(r, x0 + 0.78, y0 + 5.98);
      this.raCentrifuge(r, x0 + 2.75, y0 + 6.48);
      this.canisters(r, x0 + 6.42, y0 + 1.95);
    } else if (k === 'trading_desk') {
      // his trading desk is a room of its own make (rcTradingRoom): its boards under the neon, its desks of screens
      this.rcTradingRoom(r, d);
      return;
    } else if (k === 'design') {
      u1 = 4.5; this.boardTex(r, 4.7, 6.75, moodTex());
    } else if (d.run_kind === 'league') {
      // his Agent League: a tall dark board standing at the right end of the back-right wall -- ours carries the
      // league's table, dim, under the neon like every screen
      u1 = 4.1; rbMats();
      const lb = new THREE.Mesh(rboxGeo(1.12, 1.2, 0.1, 0.025), OM.rbBezel); lb.position.copy(this.V(x0 + 5.7, y0 + 0.21, 0.68)); lb.castShadow = true; lb.receiveShadow = true; lb.userData.rbWall = true; g.add(lb);
      const lf = new THREE.Mesh(G.plane, new THREE.MeshBasicMaterial({ map: rbLeagueTex(), color: new THREE.Color(0xffffff).multiplyScalar(0.85), toneMapped: false }));
      lf.scale.set(0.98, 1.04, 1); lf.position.copy(this.V(x0 + 5.7, y0 + 0.262, 0.72)); lf.userData.rbWall = true; g.add(lf);
    } else {
      u1 = 4.6; this.racks(r, x0 + 5.2, y0 + 0.3, 2);
    }
    if (k !== 'trading_desk') {
      this.wallScreen(r, 1.75, u1);
      this.kanban(r);
    }
    const ex = d.experts.slice(0, 3), xs = ex.length === 1 ? [2.4] : ex.length === 2 ? [1.0, 3.7] : [0.35, 2.55, 4.75];
    ex.forEach((e, i) => { this.desk(r, x0 + xs[i], y0 + 2.75, i, isOrange); if (isOrange) this.sideScreens(r, x0 + xs[i], y0 + 2.75); });
    // his rooms each have a see-through screen in a yellow-green frame on a stand, by the left wall
    this.holoFrame(r, x0 + 0.75, y0 + 2.2);
    ex.forEach((e, i) => this.agent(r, x0 + xs[i] + 0.95, y0 + 4.05, i, CO.expertName(e)));
    // his League's referee stands behind the desk, towards the back corner, watching the round
    if (d.run_kind === 'league' && ex.length < 3) {
      this.agent(r, x0 + 2.2, y0 + 1.75, ex.length, 'Referee', { stand: true });
    }
    this.terminal(r, x0 + 0.3, y0 + 0.32, d.link || CO.DEPT_LINK[k] || CO.DEPT_LINK.custom);
    // his League keeps its floor open along the front glass: no cabinet there
    if (d.run_kind !== 'league') this.cabinet(r, x0 + 6.45, y0 + 3.0, 0.45, 2.3, 0.72);
    this.plant(r, x0 + 0.42, y0 + 6.5); this.plant(r, x0 + 6.55, y0 + 6.55, 0.8);
    this.plate(r);
  }
  // a picture on the back wall at y0 (a chart, a mood board): hung as the wall screens are, under the neon
  boardTex(r, u0, u1, tex) {
    return this.rbPanel(r, 'x', u0, u1, RBW.h, new THREE.MeshBasicMaterial({ map: tex, toneMapped: false }));
  }
  // the department's computer: a workstation whose screen opens its page on cymetica.com -- one of his desks, a big
  // monitor on a neck and a foot (its top at 1.24, under the neon), a keyboard
  terminal(r, x, y, link) {
    rbMats();
    const g = new THREE.Group(); r.g.add(g);
    this.rb(g, x, y, 0.1, 1.25, 0.8, 0.4, OM.rbDesk, 0.02);
    this.rb(g, x - 0.02, y - 0.02, 0.48, 1.29, 0.84, 0.05, OM.rbDeskTop, 0.018);
    this.box(g, x + 0.05, y + 0.05, 0.08, 1.15, 0.7, 0.03, OM.rbSeam);
    this.box(g, x + 0.05, y + 0.802, 0.3, 1.15, 0.006, 0.008, OM.rbSeam, false);
    const mx = x + 0.625, my = y + 0.2;
    this.rb(g, mx - 0.17, my - 0.1, 0.53, 0.34, 0.22, 0.018, OM.rbMetal, 0.008);
    this.part(g, G.box, OM.rbMetal, 0.08, 0.12, 0.03, mx, 0.6, my - 0.02);
    this.rb(g, mx - 0.28, my - 0.1, 0.72, 0.56, 0.06, 0.34, OM.rbGloss, 0.025);
    this.rb(g, mx - 0.52, my - 0.04, 0.62, 1.04, 0.035, 0.62, OM.rbGloss, 0.012);
    this.rb(g, mx - 0.34, y + 0.5, 0.53, 0.68, 0.2, 0.024, OM.rbGloss, 0.008);
    const keys = new THREE.Mesh(G.plane, OM.rbKeys); keys.scale.set(0.64, 0.17, 1); keys.rotation.x = -Math.PI / 2; keys.position.copy(this.V(mx, y + 0.6, 0.5555)); g.add(keys);
    rbBake(g);
    const scr = new THREE.MeshBasicMaterial({ map: this.pcTex(), toneMapped: false });
    const face = new THREE.Mesh(G.plane, scr); face.scale.set(0.96, 0.56, 1); face.position.copy(this.V(mx, my - 0.004, 0.93)); r.g.add(face);
    const hit = new THREE.Mesh(G.box, M.hit); hit.scale.set(1.35, 1.2, 1.0); hit.position.copy(this.V(x + 0.62, y + 0.4, 0.68)); hit.userData.pc = link; r.g.add(hit);
    this.pcs.push(hit); r.pcFace = scr;
  }
  pcTex() {
    if (this._pc) return this._pc;
    const c = document.createElement('canvas'); c.width = 256; c.height = 176; const g = c.getContext('2d');
    g.fillStyle = '#06261f'; g.fillRect(0, 0, 256, 176); g.strokeStyle = '#38f2b8'; g.lineWidth = 8; g.strokeRect(4, 4, 248, 168);
    g.fillStyle = '#38f2b8'; g.font = '700 96px JetBrains Mono, monospace'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('↗', 128, 92);
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; this._pc = t; return t;
  }
  // his plant: a tall dark pot, tapering to its foot, a metal band at its lip, and one round bush of leaves over it
  plant(r, x, y, k = 1) {
    rbMats();
    const g = new THREE.Group(), ph = 0.44 * k; r.g.add(g);
    this.cyl(g, x, y, 0.08, 0.23 * k, ph, OM.rbPot, G.rbPot);
    this.cyl(g, x, y, 0.08 + ph - 0.03 * k, 0.24 * k, 0.035 * k, OM.rbMetal);
    this.cyl(g, x, y, 0.08 + ph - 0.005, 0.215 * k, 0.012, OM.rbSoil);
    // the leaves stay shared, not baked: one ball of many small facets is drawn for every plant
    const leaf = (mat, dx, dy, z, s) => { const m = this.part(g, G.rbBush, mat, s * k, s * 0.94 * k, s * k, x + dx * k, 0.08 + ph + z * k, y + dy * k); m.rotation.y = dx * 9 + dy * 5; m.userData.dyn = true; return m; };
    leaf(OM.rbLeaf, 0, 0, 0.2, 0.29);
    leaf(OM.rbLeaf2, -0.12, 0.1, 0.3, 0.17); leaf(OM.rbLeaf2, 0.13, -0.05, 0.33, 0.16); leaf(OM.rbLeaf, 0.04, 0.13, 0.12, 0.16);
    rbBake(g);
  }
  // a low cabinet against a wall: a recessed plinth, doors with their seams and pulls on the room's side, its top
  cabinet(r, x, y, w, d, h) {
    rbMats();
    const g = new THREE.Group(); r.g.add(g);
    this.rb(g, x, y, 0.12, w, d, h - 0.04, OM.rbDesk, 0.03);
    this.box(g, x + 0.04, y + 0.04, 0.08, w - 0.08, d - 0.08, 0.05, OM.rbSeam);
    this.rb(g, x - 0.02, y - 0.02, 0.08 + h, w + 0.04, d + 0.04, 0.04, OM.rbDeskTop, 0.015);
    const along = d > w, n = Math.max(1, Math.round((along ? d : w) / 0.6)), L = along ? d : w;
    for (let q = 1; q < n; q++) this.box(g, along ? x - 0.008 : x + q * w / n, along ? y + q * d / n : y - 0.008, 0.16, 0.01, 0.01, h - 0.14, OM.rbSeam, false);
    for (let q = 0; q < n; q++) {
      const c = (q + 0.5) * L / n + (q % 2 ? -0.08 : 0.08);
      this.box(g, along ? x - 0.02 : x + c - 0.012, along ? y + c - 0.012 : y - 0.02, 0.08 + h * 0.62, along ? 0.016 : 0.024, along ? 0.024 : 0.016, h * 0.22, OM.rbMetal, false);
    }
    rbBake(g);
  }
  // Server racks in a row, fronts to the room, as his: dark cabinets on a plinth, their tops a lit grey that the
  // camera looks down on, a door full of drive caddies and servers (rackTex), a handle, panelled sides with a vent;
  // along the row's tops a cable tray with its bundles. The tops stop at 1.42, under the back walls' neon. Over the
  // caddies' own lights a few more blink, in three sets out of step (r.leds: one instanced draw each).
  racks(r, x, y, n, step = 0.78) {
    if (!OM.rcRackSide) {
      OM.rcRackSide = std({ map: this.rcTex('side'), roughness: 0.42, metalness: 0.5 });
      OM.rcRackTop = std({ map: this.rcTex('top'), roughness: 0.48, metalness: 0.42 });
      OM.rcMetal = std({ color: 0x8794a2, roughness: 0.3, metalness: 0.75 });
      OM.rcTray = std({ color: 0x46525e, roughness: 0.42, metalness: 0.6 });
      OM.rcCable = [0x1c2c44, 0x1a3a3c, 0x262b32].map((c) => std({ color: c, roughness: 0.7, metalness: 0.1 }));
    }
    // his racks, measured on his picture: 0.7 across, 0.9 deep, about rail height
    const g = r.g, st = new THREE.Group(), H = 1.3, z0 = 0.12, Wd = 0.7, D = 0.9; g.add(st);
    const body = rboxGeo(Wd, H, D, 0.03), mats = [OM.rcRackSide, OM.rcRackSide, OM.rcRackTop, OM.rack, OM.rackFace, OM.rcRackSide];
    rackTex(); const leds = rackTex.leds, R = rng(Math.round(x * 31 + y * 17 + n)), sets = [[], [], []];
    for (let i = 0; i < n; i++) {
      const rx = x + i * step, m = new THREE.Mesh(body, mats);
      m.position.copy(this.V(rx + Wd / 2, y + D / 2, z0 + H / 2)); m.castShadow = true; m.receiveShadow = true; g.add(m);
      this.box(st, rx + 0.03, y + 0.03, 0.08, Wd - 0.06, D - 0.06, z0 - 0.08, OM.dark, false);
      this.box(st, rx + Wd - 0.08, y + D + 0.002, z0 + 0.5, 0.022, 0.02, 0.34, OM.rcMetal, false);
      // a bundle down from the tray into the rack's top, at its back
      this.box(st, rx + 0.12 + (i % 2) * 0.3, y + 0.14, z0 + H, 0.12, 0.08, 0.045, OM.rcCable[i % 3], false);
      for (let k = 0; k < 5 && leds.length; k++) { const p = leds[Math.floor(R() * leds.length)]; sets[k % 3].push([rx + Wd / 2 + (p[0] - 0.5) * (Wd - 0.02), z0 + H - p[1] * H]); }
    }
    // the tray: two rails, rungs, three bundles laid along it
    const L = (n - 1) * step + Wd, ty = y + 0.12, tz = z0 + H;
    this.box(st, x, ty, tz, L, 0.025, 0.04, OM.rcTray, false); this.box(st, x, ty + 0.3, tz, L, 0.025, 0.04, OM.rcTray, false);
    for (let k = 0.04; k < L; k += 0.17) this.box(st, x + k, ty, tz, 0.025, 0.325, 0.012, OM.rcTray, false);
    [0.05, 0.13, 0.21].forEach((dy, c) => this.box(st, x + 0.02, ty + dy, tz + 0.012, L - 0.04, 0.065, 0.026, OM.rcCable[c], false));
    bakeGroup(st);
    const o = new THREE.Object3D();
    sets.forEach((pts, s) => {
      if (!pts.length) return;
      const im = new THREE.InstancedMesh(G.box, amat(['#38f2b8', '#00e5ff', '#38f2b8'][s]).glow, pts.length);
      pts.forEach(([px, pz], j) => { o.position.copy(this.V(px, y + D + 0.003, pz)); o.scale.set(0.028, 0.012, 0.006); o.updateMatrix(); im.setMatrixAt(j, o.matrix); });
      im.computeBoundingSphere(); im.userData.blink = s * 4; g.add(im); (r.leds = r.leds || []).push(im);
    });
  }
  // His laboratory's display instruments along the back wall: an off-white base with a keyboard set into its top, a
  // dark slot with a readout and lights along its front, grilles in its sides, and on it a thick rounded frame leaning
  // back on two hinges, a hologram of data glowing inside it over a grid (k picks which). x,y its back-left corner on
  // the plan; it faces the room. Its top is 1.25, under the wall's neon (the old one leaned its head up to 1.38).
  labMachine(r, x, y, k) {
    this.raMats();
    const W = 1.15, D = 0.78, H = 0.42, p = this.raG(r, x + W / 2, y + D, 0);
    this.raB(p, W, H, D, 0, H / 2, -D / 2, OM.raLab, 0.07);
    this.raB(p, W - 0.16, 0.012, 0.012, 0, 0.11, 0.003, OM.raLab2, 0.004);
    this.raB(p, W - 0.2, 0.09, 0.03, 0, 0.3, 0, OM.raPanel, 0.015);
    this.raP(p, G.plane, OM.raRead, 0.26, 0.065, 1, -0.28, 0.3, 0.0155, 0, false);
    this.raLed(r, p, '#38f5b8', 0.3, 0.3, 0.016, k * 3 + 1); this.raLed(r, p, '#24e8ff', 0.36, 0.3, 0.016, k * 3 + 2);
    [-1, 1].forEach((s) => { const v = this.raP(p, G.plane, OM.raVentLab, 0.4, 0.18, 1, s * (W / 2 + 0.002), 0.2, -0.42, 0, false); v.rotation.y = s * Math.PI / 2; });
    this.raKeys(p, 16, 2, 0.048, 0, H, -0.13);
    [-0.42, 0.42].forEach((hx) => this.raB(p, 0.12, 0.06, 0.12, hx, H + 0.02, -D + 0.26, OM.raLab2, 0.02));
    // the frame stands 0.72 tall and leans back 10 degrees: its top at 1.25
    const fr = new THREE.Group(); fr.position.set(0, H + 0.02 + 0.355, -D + 0.26); fr.rotation.x = -0.18; p.add(fr);
    this.raP(fr, this.raFrame(), OM.raLab, 1, 1, 1, 0, 0, 0);
    this.raB(fr, 0.9, 0.6, 0.02, 0, 0, -0.03, OM.raGlass, 0.01);
    this.raP(fr, G.plane, k ? OM.raHoloB : OM.raHoloA, 0.88, 0.58, 1, 0, 0, -0.012, 0, false);
    this.raP(fr, G.plane, OM.raGrid, 0.86, 0.56, 1, 0, 0, 0.03, 0, false);
    const h = glowSprite(0x5ff0e0, 0.16, 0.8); h.position.set(0, -0.02, 0.12); fr.add(h);
    this.raBake(p);
  }
  // His holographic projector at the front of the laboratory: an off-white case on dark feet, a dark glass top lit by
  // a grid with a ring of light and an emitter in it, a readout, a drawer, buttons and lights on its dark front; over
  // it, in a faint beam, a crystal of data turning with specks of light round it (r.crystal). x,y its back-left
  // corner on the plan.
  labHolo(r, x, y) {
    this.raMats();
    const W = 1.3, D = 0.9, H = 0.5, p = this.raG(r, x + W / 2, y + D, 0), zc = -D / 2, top = 0.04 + H;
    [[-1, -1], [1, -1], [-1, 1], [1, 1]].forEach(([sx, sz]) => this.raB(p, 0.12, 0.04, 0.12, sx * (W / 2 - 0.12), 0.02, zc + sz * (D / 2 - 0.12), OM.raRubber, 0.015));
    this.raB(p, W, H, D, 0, 0.04 + H / 2, zc, OM.raLab, 0.08);
    this.raB(p, W - 0.22, 0.03, D - 0.22, 0, top + 0.004, zc, OM.raGlass, 0.012);
    this.raP(p, G.plane, OM.raGrid, W - 0.3, D - 0.3, 1, 0, top + 0.021, zc, -Math.PI / 2, false);
    this.raP(p, G.ringT, OM.cyan.rim, 0.2, 0.2, 0.5, 0, top + 0.03, zc, Math.PI / 2, false);
    this.raP(p, G.cyl, OM.raChrome, 0.1, 0.03, 0.1, 0, top + 0.03, zc);
    this.raB(p, W - 0.2, 0.24, 0.03, 0, 0.3, 0, OM.raPanel, 0.02);
    this.raP(p, G.plane, OM.raRead, 0.34, 0.12, 1, -0.32, 0.33, 0.0155, 0, false);
    this.raB(p, 0.42, 0.024, 0.012, 0.2, 0.23, 0.016, OM.raTrim, 0.004);
    [0.08, 0.16, 0.24].forEach((bx) => this.raP(p, G.cyl, OM.raKey, 0.022, 0.02, 0.022, bx, 0.36, 0.018, Math.PI / 2));
    this.raLed(r, p, '#38f5b8', 0.4, 0.37, 0.016, 2); this.raLed(r, p, '#24e8ff', 0.46, 0.37, 0.016, 4);
    // the beam, widening as it rises, and the crystal in it
    // (it stands free at the front, not against a wall, so his tall crystal may rise to the glass's height)
    const cy = top + 0.47;
    this.raP(p, G.beam, OM.raBeam, 0.95, 0.4, 0.95, 0, top + 0.22, zc, Math.PI, false);
    const c = new THREE.Group(); c.position.set(0, cy, zc); c.userData.dyn = true; p.add(c);
    const sh = new THREE.Mesh(this.raShard(), OM.raShard); sh.scale.set(0.44, 0.42, 0.44); sh.rotation.z = 0.14; c.add(sh);
    const ed = new THREE.LineSegments(G.raShardE, OM.raEdge); ed.scale.copy(sh.scale); ed.rotation.copy(sh.rotation); c.add(ed);
    const core = new THREE.Mesh(G.sphere, OM.cyan.glow); core.scale.setScalar(0.04); c.add(core);
    const R = rng(19), o = new THREE.Object3D(), sp = new THREE.InstancedMesh(G.sphere, amat('#9ff6ff').glow, 26);
    for (let i = 0; i < 26; i++) { const a = R() * Math.PI * 2, rr = 0.4 + R() * 0.22; o.position.set(Math.cos(a) * rr, (R() - 0.5) * 0.75, Math.sin(a) * rr); o.scale.setScalar(0.007 + R() * 0.007); o.updateMatrix(); sp.setMatrixAt(i, o.matrix); }
    c.add(sp);
    const hl = glowSprite(0x5ff0d8, 0.26, 1.9); hl.position.set(0, cy, zc); p.add(hl);
    r.crystal = [c];
    this.raBake(p);
  }
  // his see-through screen: a yellow-green frame like a monitor's bezel round a faintly lit pane with a small ring of
  // light in it, on a dark neck and foot, standing on a low dark cabinet (its top at 1.2, under the neon)
  holoFrame(r, x, y) {
    rbMats();
    const g = r.g, fr = OM.frameLime, s = new THREE.Group(); s.position.copy(this.V(x, y, 0.08)); s.rotation.y = 0.55; g.add(s);
    const cm = (geom, mat, px, py, pz, sx, sy, sz) => { const m = new THREE.Mesh(geom, mat); m.position.set(px, py, pz); m.scale.set(sx, sy, sz); m.castShadow = true; m.receiveShadow = true; s.add(m); return m; };
    cm(rboxGeo(0.92, 0.4, 0.52, 0.02), OM.rbDesk, 0, 0.22, 0, 1, 1, 1);
    cm(rboxGeo(0.96, 0.04, 0.56, 0.015), OM.rbDeskTop, 0, 0.43, 0, 1, 1, 1);
    cm(G.box, OM.rbSeam, 0, 0.3, 0.262, 0.86, 0.008, 0.006);
    cm(rboxGeo(0.3, 0.02, 0.18, 0.008), OM.rbGloss, 0, 0.46, -0.04, 1, 1, 1);
    cm(G.box, OM.rbGloss, 0, 0.55, -0.06, 0.06, 0.18, 0.03);
    rbBake(s);
    const f = new THREE.Group(); f.position.set(0, 0.86, -0.04); f.rotation.x = -0.12; s.add(f);
    const pane = new THREE.Mesh(G.plane, OM.paneLime); pane.scale.set(0.8, 0.5, 1); f.add(pane);
    [[0, 0.25, 0.84, 0.035], [0, -0.25, 0.84, 0.035], [-0.42, 0, 0.035, 0.5], [0.42, 0, 0.035, 0.5]].forEach(([px, py, w, h]) => {
      const b = new THREE.Mesh(G.box, fr); b.scale.set(w, h, 0.025); b.position.set(px, py, 0); f.add(b);
    });
    const ring = new THREE.Mesh(G.ringT, fr); ring.scale.setScalar(0.06); ring.position.set(0, 0, 0.01); f.add(ring);
    const dot = new THREE.Mesh(G.sphere, fr); dot.scale.set(0.018, 0.018, 0.006); dot.position.set(0, 0, 0.012); f.add(dot);
    rbBake(f);
  }
  // His weekly audit's computer: a retro console in a slate blue-grey enamel, drawn from the side and extruded across
  // its width -- a dark kick plate, a front, a deck sloping up to a screen housing that leans back, a rounded top. Two
  // CRTs sit in raised bezels (the left green with the audit's log, the right dark glass), a keyboard of real keys and
  // a dark panel of labelled buttons with blinking lights lie on the deck, grilles cut its front, sides and top, a
  // cable runs from its side to the wall. x,y the middle of its front on the plan, ry the way it faces, alt which log
  // it shows. Its top is 1.27: under the walls' neon, as in his picture.
  console3(r, x, y, ry, alt) {
    this.raMats();
    const p = this.raG(r, x, y, ry), W = 1.8, Wh = W / 2;
    this.raP(p, this.raProfile('raConsole', [[0.02, 0], [0, 0.07], [0, 0.57], [0.46, 0.67], [0.64, 1.16], [0.9, 1.18], [0.9, 0]], W, 0.035, 0.012), OM.raCase, 1, 1, 1, 0, 0, 0);
    this.raB(p, W - 0.1, 0.07, 0.02, 0, 0.04, 0.008, OM.raTrim, 0.008);
    this.raB(p, W - 0.12, 0.012, 0.01, 0, 0.47, 0.012, OM.raTrim, 0.003);
    this.raP(p, G.plane, OM.raVent, 0.42, 0.13, 1, Wh * 0.55, 0.25, 0.0125, 0, false);
    this.raB(p, 0.2, 0.06, 0.01, -Wh * 0.62, 0.27, 0.013, OM.raCaseHi, 0.004);
    [-1, 1].forEach((s) => { const v = this.raP(p, G.plane, OM.raVent, 0.36, 0.3, 1, s * (Wh + 0.002), 0.36, -0.62, 0, false); v.rotation.y = s * Math.PI / 2; });
    this.raP(p, G.plane, OM.raVent, W - 0.4, 0.12, 1, 0, 1.19, -0.78, -Math.PI / 2, false);
    // the screen housing's face, leaning back 20 degrees: two bezels, a dark recess in each, the screens in them
    const face = new THREE.Group(); face.position.set(0, 0.919, -0.539); face.rotation.x = -0.3521; p.add(face);
    [-0.44, 0.44].forEach((sx, i) => {
      this.raB(face, 0.8, 0.43, 0.03, sx, 0, 0, OM.raCaseHi, 0.02);
      this.raB(face, 0.72, 0.37, 0.03, sx, 0, 0.012, OM.raPanel, 0.014);
      this.raP(face, G.plane, i ? OM.raDim : alt ? OM.raCrt2 : OM.raCrt1, 0.66, 0.32, 1, sx, 0, 0.0285, 0, false);
    });
    // the deck, sloping up to the housing: the keyboard on the left, the panel of buttons and lights on the right
    const deck = new THREE.Group(); deck.position.set(0, 0.632, -0.2275); deck.rotation.x = 0.2138; p.add(deck);
    this.raKeys(deck, 14, 4, 0.046, -0.44, 0, 0.01);
    this.raB(deck, 0.7, 0.016, 0.3, 0.44, 0.004, 0, OM.raPanel, 0.006);
    this.raP(deck, G.plane, OM.raCtl, 0.66, 0.27, 1, 0.44, 0.0125, 0, -Math.PI / 2, false);
    [0.213, 0.357, 0.502, 0.646].forEach((bx, i) => this.raP(deck, G.cyl, i === 3 ? amat('#ff4444').soft : OM.raKey, 0.025, 0.02, 0.025, bx, 0.022, -0.038));
    ['#38f5b8', '#24e8ff', '#38f5b8'].forEach((c, i) => this.raLed(r, deck, c, 0.19 + i * 0.065, 0.016, -0.122, i * 2 + alt * 5));
    if (!G.raCable) G.raCable = new THREE.TubeGeometry(new THREE.CatmullRomCurve3([[0, 0.22, -0.5], [0.07, 0.05, -0.56], [0.16, 0.016, -0.7], [0.19, 0.016, -0.93]].map((v) => new THREE.Vector3(...v))), 16, 0.014, 6, false);
    this.raP(p, G.raCable, OM.raRubber, 1, 1, 1, Wh, 0, 0);
    this.raBake(p);
  }
  // His canisters: three ribbed cylinders in a pale grey on a dark bench against the right wall, a chrome cap and a lit
  // ring on each; a tall steel dewar on the floor at the bench's far end, a valve and its wheel on top. x,y the
  // middle of the bench's front on the plan; the bench faces into the room.
  canisters(r, x, y) {
    this.raMats();
    const p = this.raG(r, x, y, -Math.PI / 2);
    this.raB(p, 1.5, 0.38, 0.48, 0, 0.21, -0.25, OM.desk, 0.03);
    this.raB(p, 1.56, 0.04, 0.54, 0, 0.42, -0.26, OM.deskTop, 0.012);
    [-0.37, 0.37].forEach((dx) => { this.raB(p, 0.66, 0.3, 0.012, dx, 0.22, -0.006, OM.desk, 0.012); this.raB(p, 0.14, 0.02, 0.02, dx, 0.3, 0.004, OM.raChrome, 0.006); });
    [-0.45, 0, 0.45].forEach((cx, i) => {
      const h = [0.36, 0.3, 0.36][i], b0 = 0.44;
      this.raP(p, G.cyl, OM.raLab2, 0.13, h, 0.13, cx, b0 + h / 2, -0.25);
      [0.08, 0.5, 0.9].forEach((f) => this.raP(p, G.cyl, OM.raLab, 0.137, 0.022, 0.137, cx, b0 + h * f, -0.25));
      this.raP(p, G.cyl, OM.raChrome, 0.085, 0.045, 0.085, cx, b0 + h + 0.022, -0.25);
      this.raP(p, G.ringT, OM.cyan.rim, 0.1, 0.1, 0.4, cx, b0 + h + 0.004, -0.25, Math.PI / 2, false);
    });
    this.raBake(p);
    if (!G.raDewar) G.raDewar = new THREE.LatheGeometry([[0, 0], [0.15, 0], [0.17, 0.03], [0.17, 0.6], [0.14, 0.68], [0.07, 0.72], [0.06, 0.78], [0, 0.78]].map(([a, b]) => new THREE.Vector2(a, b)), 32);
    const d = this.raG(r, x + 0.12, y - 1.33, 0);
    this.raP(d, G.raDewar, OM.raChrome, 1, 1, 1, 0, 0, 0);
    this.raP(d, G.cyl, OM.raLab2, 0.172, 0.05, 0.172, 0, 0.12, 0);
    this.raP(d, G.cyl, OM.raLab2, 0.172, 0.05, 0.172, 0, 0.5, 0);
    this.raP(d, G.cyl, OM.raTrim, 0.03, 0.08, 0.03, 0, 0.82, 0);
    this.raP(d, G.ringT, amat('#ff4444').soft, 0.06, 0.06, 0.5, 0, 0.86, 0, Math.PI / 2);
    this.raB(d, 0.1, 0.08, 0.03, 0, 0.36, 0.17, OM.raPanel, 0.01);
    this.raBake(d);
  }
  /* ---- the weekly audit's and the laboratory's machines, after his picture: parts, materials, textures ---- */
  // a machine stands in its own frame: a group on the floor at plan x,y, turned to face its room (ry 0 faces +y,
  // PI/2 faces +x); its parts are placed in it with x across it, y up and z out of its front
  raG(r, x, y, ry) { const p = new THREE.Group(); p.position.copy(this.V(x, y, 0.08)); p.rotation.y = ry || 0; r.g.add(p); return p; }
  raP(p, geom, mat, sx, sy, sz, x, y, z, rx, shadow = true) {
    const m = new THREE.Mesh(geom, mat); m.scale.set(sx, sy, sz); m.position.set(x, y, z); if (rx) m.rotation.x = rx;
    if (shadow) { m.castShadow = true; m.receiveShadow = true; } p.add(m); return m;
  }
  // a box with soft edges in the machine's frame, at its real size, centred on x,y,z
  raB(p, w, h, d, x, y, z, mat, rad = 0.02) { return this.raP(p, rboxGeo(w, h, d, rad), mat, 1, 1, 1, x, y, z); }
  // a status light that blinks (the room's frame turns r.leds on and off); it stays out of the merge
  raLed(r, p, hex, x, y, z, k) {
    const m = new THREE.Mesh(G.box, amat(hex).glow); m.scale.set(0.024, 0.014, 0.024); m.position.set(x, y, z);
    m.userData.dyn = true; m.userData.blink = k; p.add(m); (r.leds = r.leds || []).push(m); return m;
  }
  // a finished machine: its still parts merged by material, a dozen draw calls instead of fifty; what blinks or turns
  // is marked dyn and stays as it is, the keys are instanced already
  raBake(p) {
    bakeGroup(p);
    p.children.forEach((m) => { if (m.isMesh && m.userData.own) { const lit = !m.material.isMeshBasicMaterial && !m.material.transparent; m.castShadow = lit; m.receiveShadow = lit; } });
    return p;
  }
  // a keyboard: a dark tray and rows of pale keys, all the keys one draw call; the front row has a space bar
  raKeys(p, cols, rows, pitch, x, y, z) {
    const at = [], skip = [], o = new THREE.Object3D();
    this.raB(p, cols * pitch + 0.03, 0.016, rows * pitch + 0.03, x, y + 0.008, z, OM.raKeyDk, 0.005);
    for (let j = 0; j < rows; j++) for (let i = 0; i < cols; i++) {
      if (j === rows - 1 && rows > 2 && i > cols * 0.3 && i < cols * 0.7) { skip.push(i); continue; }
      at.push([x + (i - (cols - 1) / 2) * pitch, z + (j - (rows - 1) / 2) * pitch, pitch * 0.76]);
    }
    if (skip.length) at.push([x + ((skip[0] + skip[skip.length - 1]) / 2 - (cols - 1) / 2) * pitch, z + (rows - 1) / 2 * pitch, (skip.length - 0.24) * pitch]);
    const im = new THREE.InstancedMesh(G.box, OM.raKey, at.length);
    at.forEach(([kx, kz, kw], i) => { o.position.set(kx, y + 0.023, kz); o.scale.set(kw, 0.014, pitch * 0.72); o.updateMatrix(); im.setMatrixAt(i, o.matrix); });
    im.receiveShadow = true; p.add(im); return im;
  }
  // a polygon with every corner rounded by rad
  raShape(pts, rad) {
    const s = new THREE.Shape(), n = pts.length;
    pts.forEach((q, i) => {
      const a = pts[(i + n - 1) % n], b = pts[(i + 1) % n], da = Math.hypot(a[0] - q[0], a[1] - q[1]), db = Math.hypot(b[0] - q[0], b[1] - q[1]), rr = Math.min(rad, da / 2.2, db / 2.2);
      const p1 = [q[0] + (a[0] - q[0]) / da * rr, q[1] + (a[1] - q[1]) / da * rr], p2 = [q[0] + (b[0] - q[0]) / db * rr, q[1] + (b[1] - q[1]) / db * rr];
      if (i) s.lineTo(p1[0], p1[1]); else s.moveTo(p1[0], p1[1]);
      s.quadraticCurveTo(q[0], q[1], p2[0], p2[1]);
    });
    s.closePath(); return s;
  }
  // a machine's body drawn from the side (u back from its front, v up) and extruded across its width w with soft
  // edges: a console's sloped deck and leaning screen housing in one piece. Made once per shape (G[key]).
  raProfile(key, pts, w, rad, bev) {
    if (G[key]) return G[key];
    const geo = new THREE.ExtrudeGeometry(this.raShape(pts, rad), { depth: w - 2 * bev, bevelEnabled: true, bevelThickness: bev, bevelSize: bev, bevelSegments: 2, curveSegments: 4, steps: 1 });
    geo.rotateY(Math.PI / 2); geo.translate(-(w - 2 * bev) / 2, 0, 0);
    G[key] = geo; return geo;
  }
  // the display instruments' thick rounded frame: a rounded rectangle with a rounded hole, extruded
  raFrame() {
    if (G.raFrame) return G.raFrame;
    const rrect = (s, w, h, q) => {
      const x = -w / 2, y = -h / 2;
      s.moveTo(x + q, y); s.lineTo(x + w - q, y); s.quadraticCurveTo(x + w, y, x + w, y + q); s.lineTo(x + w, y + h - q); s.quadraticCurveTo(x + w, y + h, x + w - q, y + h);
      s.lineTo(x + q, y + h); s.quadraticCurveTo(x, y + h, x, y + h - q); s.lineTo(x, y + q); s.quadraticCurveTo(x, y, x + q, y);
    };
    const s = new THREE.Shape(), hole = new THREE.Path(); rrect(s, 1.04, 0.72, 0.07); rrect(hole, 0.88, 0.58, 0.035); s.holes.push(hole);
    const g = new THREE.ExtrudeGeometry(s, { depth: 0.06, bevelEnabled: true, bevelThickness: 0.012, bevelSize: 0.012, bevelSegments: 2, curveSegments: 5 });
    g.translate(0, 0, -0.03); G.raFrame = g; return g;
  }
  // the projector's crystal: a six-sided shard, longer above than below, its facets a little uneven
  raShard() {
    if (G.raShard) return G.raShard;
    const R = rng(77), top = [0.05, 1, -0.03], bot = [0, -0.85, 0.04], ring = [], pos = [];
    for (let i = 0; i < 6; i++) { const a = i / 6 * Math.PI * 2 + (R() - 0.5) * 0.5, rr = 0.42 + R() * 0.2; ring.push([Math.cos(a) * rr, (R() - 0.5) * 0.3 + 0.08, Math.sin(a) * rr]); }
    for (let i = 0; i < 6; i++) { const a = ring[i], b = ring[(i + 1) % 6]; pos.push(...top, ...b, ...a, ...bot, ...a, ...b); }
    const g = new THREE.BufferGeometry(); g.setAttribute('position', new THREE.Float32BufferAttribute(pos, 3)); g.computeVertexNormals();
    G.raShard = g; G.raShardE = new THREE.EdgesGeometry(g, 1); return g;
  }
  // His printer for the report: a teleprinter in the consoles' enamel. A base whose long sides slope in, a recessed
  // tray on top with its keys and the print head on a chrome rail, a rounded platen along its back with a rubber
  // roller and knobs at its ends, and the report coming out over it on fan-fold paper. x,y the middle of its front on
  // the plan, ry the way it faces (his has its platen to the wall, its keys to the room).
  raPrinter(r, x, y, ry) {
    this.raMats();
    const p = this.raG(r, x, y, ry), W = 1.7, rz = (m) => { m.rotation.z = Math.PI / 2; return m; };
    this.raP(p, this.raProfile('raPrinter', [[0.05, 0], [0, 0.04], [0.06, 0.36], [0.12, 0.41], [0.64, 0.41], [0.7, 0.36], [0.76, 0.04], [0.71, 0]], W, 0.03, 0.012), OM.raCase, 1, 1, 1, 0, 0, 0);
    this.raB(p, W - 0.26, 0.03, 0.34, 0, 0.41, -0.3, OM.raPanel, 0.01);
    this.raKeys(p, 16, 3, 0.05, 0.12, 0.425, -0.28);
    this.raB(p, 0.24, 0.07, 0.13, -0.56, 0.46, -0.3, OM.raTrim, 0.014);
    rz(this.raP(p, G.cyl, OM.raChrome, 0.01, W - 0.3, 0.01, 0, 0.45, -0.44));
    rz(this.raP(p, G.cyl, OM.raRubber, 0.075, W - 0.3, 0.075, 0, 0.5, -0.47));
    rz(this.raP(p, G.cyl, OM.raCaseHi, 0.1, W - 0.12, 0.1, 0, 0.5, -0.56));
    [-1, 1].forEach((s) => {
      rz(this.raP(p, G.cyl, OM.raTrim, 0.07, 0.05, 0.07, s * (W / 2 - 0.02), 0.5, -0.56));
      const v = this.raP(p, G.plane, OM.raVent, 0.34, 0.18, 1, s * (W / 2 + 0.002), 0.2, -0.38, 0, false); v.rotation.y = s * Math.PI / 2;
    });
    if (!G.raSheet) {
      const s = new THREE.PlaneGeometry(1, 1, 1, 10), q = s.attributes.position;
      for (let i = 0; i < q.count; i++) { const f = (q.getY(i) + 0.5) * 1.3; q.setXYZ(i, q.getX(i), 0.35 * Math.sin(f), -0.35 * (1 - Math.cos(f))); }
      s.computeVertexNormals(); G.raSheet = s;
    }
    this.raP(p, G.raSheet, OM.raPaper, 0.95, 1, 1, 0, 0.6, -0.56);
    this.raLed(r, p, '#38f5b8', W / 2 - 0.14, 0.3, -0.03, 3);
    this.raBake(p);
  }
  // His laboratory's big instrument: a tall off-white analyser drawn from the side -- a dark plinth, a front with its
  // door, a dial and a handle, a sloping shelf of buttons with a readout and lights, a screen window leaning back
  // with a spectrum on it and a line of cyan light round it, a rounded top, grilles in its sides, a hose to the wall.
  // x,y the middle of its front on the plan; it faces +x. Its top is 1.28.
  raAnalyser(r, x, y) {
    this.raMats();
    const p = this.raG(r, x, y, Math.PI / 2), W = 1.3, Wh = W / 2, b = 0.025;
    this.raB(p, W - 0.1, 0.06, 0.82, 0, 0.03, -0.47, OM.raTrim, 0.01);
    this.raP(p, this.raProfile('raAnalyser', [[0, 0.08], [0, 0.55], [0.26, 0.63], [0.4, 1.08], [0.52, 1.17], [0.92, 1.17], [0.92, 0.08]], W, 0.06, b), OM.raLab, 1, 1, 1, 0, 0, 0);
    // the door, its dial and its handle
    this.raB(p, 0.98, 0.32, 0.014, -0.05, 0.3, b + 0.004, OM.raLab, 0.012);
    this.raB(p, 0.98, 0.006, 0.006, -0.05, 0.46, b + 0.012, OM.raLab2, 0.002);
    this.raP(p, G.cyl, OM.raChrome, 0.055, 0.03, 0.055, -0.42, 0.3, b + 0.02, Math.PI / 2);
    this.raP(p, G.cyl, OM.raTrim, 0.035, 0.032, 0.035, -0.42, 0.3, b + 0.022, Math.PI / 2);
    this.raB(p, 0.024, 0.15, 0.03, 0.38, 0.3, b + 0.024, OM.raChrome, 0.01);
    // the shelf under the window
    const shelf = new THREE.Group(); shelf.position.set(0, 0.614, -0.1227); shelf.rotation.x = 0.2985; p.add(shelf);
    [-0.5, -0.42, -0.34, -0.26].forEach((bx, i) => this.raP(shelf, G.cyl, i === 3 ? OM.cyan.soft : OM.raKey, 0.022, 0.02, 0.022, bx, 0.01, 0.03));
    this.raP(shelf, G.plane, OM.raRead, 0.28, 0.1, 1, 0.02, 0.003, -0.01, -Math.PI / 2, false);
    this.raP(shelf, G.cyl, OM.raChrome, 0.045, 0.035, 0.045, 0.42, 0.017, 0);
    this.raLed(r, shelf, '#38f5b8', 0.22, 0.008, 0.02, 1); this.raLed(r, shelf, '#24e8ff', 0.28, 0.008, 0.02, 5);
    // the window, leaning back: a pale frame, dark glass, the spectrum, the cyan line round it
    const face = new THREE.Group(); face.position.set(0, 0.862, -0.306); face.rotation.x = -0.3016; p.add(face);
    this.raB(face, 1.1, 0.42, 0.03, 0, 0, 0, OM.raLab2, 0.025);
    this.raB(face, 1.0, 0.35, 0.03, 0, 0, 0.012, OM.raGlass, 0.015);
    this.raP(face, G.plane, OM.raSpec, 0.94, 0.3, 1, 0, 0, 0.0285, 0, false);
    [[0, 0.177, 1.0, 0.01], [0, -0.177, 1.0, 0.01], [-0.502, 0, 0.01, 0.36], [0.502, 0, 0.01, 0.36]].forEach(([fx, fy, fw, fh]) => this.raP(face, G.box, OM.cyan.rim, fw, fh, 0.008, fx, fy, 0.03, 0, false));
    [-1, 1].forEach((s) => [[0.82, -0.68, 0.36, 0.3], [0.3, -0.56, 0.5, 0.22]].forEach(([vy, vz, vw, vh]) => {
      const v = this.raP(p, G.plane, OM.raVentLab, vw, vh, 1, s * (Wh + 0.002), vy, vz, 0, false); v.rotation.y = s * Math.PI / 2;
    }));
    this.raB(p, W - 0.24, 0.01, 0.02, 0, 1.17 + b + 0.003, -0.72, OM.raLab2, 0.004);
    if (!G.raHose) G.raHose = new THREE.TubeGeometry(new THREE.CatmullRomCurve3([[0, 0.25, -0.93], [0.05, 0.05, -1.0], [0.1, 0.016, -1.2], [0.12, 0.016, -1.75]].map((v) => new THREE.Vector3(...v))), 16, 0.018, 6, false);
    this.raP(p, G.raHose, OM.raRubber, 1, 1, 1, 0.4, 0, 0);
    this.raBake(p);
  }
  // a lab stool: a round padded seat on a chrome column, a foot ring, five legs on casters
  raStool(r, x, y) {
    this.raMats();
    const p = this.raG(r, x, y, 0.3);
    this.raP(p, G.cyl, OM.chair, 0.19, 0.06, 0.19, 0, 0.58, 0);
    this.raP(p, G.cyl, OM.raTrim, 0.15, 0.03, 0.15, 0, 0.535, 0);
    this.raP(p, G.cyl, OM.raChrome, 0.022, 0.5, 0.022, 0, 0.29, 0);
    this.raP(p, G.ringT, OM.raChrome, 0.15, 0.15, 0.6, 0, 0.26, 0, Math.PI / 2);
    for (let k = 0; k < 5; k++) {
      const a = k / 5 * Math.PI * 2, l = this.raP(p, G.box, OM.raTrim, 0.22, 0.03, 0.04, Math.cos(a) * 0.11, 0.045, Math.sin(a) * 0.11); l.rotation.y = -a;
      this.raP(p, G.sphere, OM.raRubber, 0.026, 0.026, 0.026, Math.cos(a) * 0.21, 0.026, Math.sin(a) * 0.21);
    }
    this.raBake(p);
  }
  // a centrifuge on the floor: an off-white drum with a tinted glass dome, its rotor turning inside (r.spin), a
  // readout and a light on its front
  raCentrifuge(r, x, y) {
    this.raMats();
    if (!G.raDrum) G.raDrum = new THREE.LatheGeometry([[0, 0], [0.25, 0], [0.28, 0.03], [0.28, 0.34], [0.26, 0.39], [0.2, 0.41], [0, 0.41]].map(([a, b]) => new THREE.Vector2(a, b)), 32);
    const p = this.raG(r, x, y, 0.5);
    this.raP(p, G.raDrum, OM.raLab, 1, 1, 1, 0, 0, 0);
    this.raP(p, G.cyl, OM.raLab2, 0.284, 0.024, 0.284, 0, 0.2, 0);
    this.raB(p, 0.2, 0.1, 0.05, 0, 0.28, 0.265, OM.raPanel, 0.015);
    this.raP(p, G.plane, OM.raRead, 0.16, 0.06, 1, 0, 0.28, 0.2905, 0, false);
    this.raLed(r, p, '#38f5b8', 0.08, 0.2, 0.282, 5);
    this.raP(p, G.hemi, OM.raDome, 0.2, 0.11, 0.2, 0, 0.405, 0, 0, false);
    const rot = new THREE.Group(); rot.position.set(0, 0.43, 0); rot.userData.dyn = true; p.add(rot);
    for (let k = 0; k < 3; k++) this.raP(rot, G.box, OM.raChrome, 0.28, 0.018, 0.035, 0, 0, 0, 0, false).rotation.y = k * Math.PI / 3;
    this.raP(rot, G.cyl, OM.cyan.glow, 0.03, 0.03, 0.03, 0, 0.01, 0, 0, false);
    r.spin = rot;
    this.raBake(p);
  }
  // the materials, made once and kept (OM.ra*): his consoles are a slate blue-grey enamel, his laboratory's
  // instruments a cool off-white; dark control panels, pale key caps, glossy black glass, chrome, rubber; screens that
  // glow past the bloom's threshold, holograms that add their light
  raMats() {
    if (OM.raCase) return;
    OM.raCase = std({ color: 0x7b8b9c, roughness: 0.52, metalness: 0.2 });
    OM.raCaseHi = std({ color: 0x95a3b1, roughness: 0.46, metalness: 0.16 });
    OM.raTrim = std({ color: 0x38434e, roughness: 0.5, metalness: 0.35 });
    OM.raPanel = std({ color: 0x131a21, roughness: 0.36, metalness: 0.42 });
    OM.raKey = std({ color: 0xc9d1d8, roughness: 0.62, metalness: 0.05 });
    OM.raKeyDk = std({ color: 0x46515c, roughness: 0.6, metalness: 0.12 });
    OM.raLab = std({ color: 0xb2bfca, roughness: 0.36, metalness: 0.06 });
    OM.raLab2 = std({ color: 0x8c99a5, roughness: 0.42, metalness: 0.14 });
    OM.raGlass = std({ color: 0x070d12, roughness: 0.12, metalness: 0.65 });
    OM.raChrome = std({ color: 0x9aa6b2, roughness: 0.24, metalness: 0.85 });
    OM.raRubber = std({ color: 0x14191f, roughness: 0.8, metalness: 0.05 });
    OM.raVent = std({ map: this.raTex('vent'), color: 0x7b8b9c, roughness: 0.55, metalness: 0.2 });
    OM.raVentLab = std({ map: this.raTex('vent'), color: 0xb2bfca, roughness: 0.4, metalness: 0.08 });
    OM.raCtl = std({ map: this.raTex('ctl'), emissiveMap: this.raTex('ctl'), emissive: 0xffffff, emissiveIntensity: 0.5, roughness: 0.4, metalness: 0.3 });
    OM.raPaper = std({ map: this.raTex('paper'), roughness: 0.85, metalness: 0, side: THREE.DoubleSide });
    OM.raDim = std({ color: 0x04090d, roughness: 0.14, metalness: 0.5, emissiveMap: this.raTex('dim'), emissive: 0xffffff, emissiveIntensity: 0.55 });
    const scr = (k, c) => new THREE.MeshBasicMaterial({ map: this.raTex(k), color: new THREE.Color(0xffffff).multiplyScalar(c), toneMapped: false });
    OM.raCrt1 = scr('crt1', 1.6); OM.raCrt2 = scr('crt2', 1.6); OM.raSpec = scr('spec', 1.3); OM.raRead = scr('read', 1.25);
    const add = (k, c) => new THREE.MeshBasicMaterial({ map: this.raTex(k), color: new THREE.Color(0xffffff).multiplyScalar(c), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide, toneMapped: false });
    OM.raHoloA = add('holoA', 2.1); OM.raHoloB = add('holoB', 2.1); OM.raGrid = add('grid', 0.55);
    OM.raShard = new THREE.MeshBasicMaterial({ color: new THREE.Color(0x5ff5d8).multiplyScalar(0.8), transparent: true, opacity: 0.38, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
    OM.raEdge = new THREE.LineBasicMaterial({ color: new THREE.Color(0xc8fff4).multiplyScalar(1.8), transparent: true, opacity: 0.95, toneMapped: false });
    OM.raBeam = new THREE.MeshBasicMaterial({ color: new THREE.Color(0x5ff0e0).multiplyScalar(0.8), transparent: true, opacity: 0.12, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide });
    OM.raDome = std({ color: 0x9ff2ea, transparent: true, opacity: 0.3, roughness: 0.05, metalness: 0.1, emissive: 0x24e8ff, emissiveIntensity: 0.3, depthWrite: false });
  }
  // the canvas textures, drawn once (TX.ra*): green CRTs with the audit's log, a dark CRT with a faint trace, a panel
  // of labelled buttons, a grille, a spectrum, small readouts, two holograms, a grid of light, a printed page
  raTex(k) {
    const key = 'ra' + k; if (TX[key]) return TX[key];
    const R = rng(k.length * 131 + k.charCodeAt(0) * 7), mono = (px, w) => (w || 600) + ' ' + px + 'px JetBrains Mono, monospace';
    const scan = (g, W, H, a) => { g.fillStyle = 'rgba(0,0,0,' + a + ')'; for (let yy = 0; yy < H; yy += 3) g.fillRect(0, yy, W, 1); };
    const crt = (lines) => (g, W, H) => {
      g.fillStyle = '#021309'; g.fillRect(0, 0, W, H);
      const gr = g.createRadialGradient(W / 2, H / 2, 10, W / 2, H / 2, W * 0.7); gr.addColorStop(0, 'rgba(40,255,150,.16)'); gr.addColorStop(1, 'rgba(0,0,0,.45)');
      g.fillStyle = gr; g.fillRect(0, 0, W, H); g.font = mono(15); g.textBaseline = 'top';
      lines.forEach((s, i) => { g.fillStyle = i ? 'rgba(80,255,165,' + (0.6 + R() * 0.4).toFixed(2) + ')' : '#b4ffd9'; g.fillText(s, 12, 9 + i * 17.6); });
      scan(g, W, H, 0.22);
    };
    const holo = (fn) => (g, W, H) => {
      g.fillStyle = '#000'; g.fillRect(0, 0, W, H); g.strokeStyle = 'rgba(60,230,210,.16)'; g.lineWidth = 1;
      for (let i = 16; i < W; i += 24) { g.beginPath(); g.moveTo(i, 0); g.lineTo(i, H); g.stroke(); }
      for (let i = 16; i < H; i += 24) { g.beginPath(); g.moveTo(0, i); g.lineTo(W, i); g.stroke(); }
      g.shadowColor = '#5ff6e0'; g.shadowBlur = 8; fn(g, W, H); g.shadowBlur = 0;
      g.strokeStyle = 'rgba(120,255,230,.8)'; g.lineWidth = 2;
      [[8, 8, 1, 1], [W - 8, 8, -1, 1], [8, H - 8, 1, -1], [W - 8, H - 8, -1, -1]].forEach(([cx, cy, sx, sy]) => { g.beginPath(); g.moveTo(cx, cy + sy * 16); g.lineTo(cx, cy); g.lineTo(cx + sx * 16, cy); g.stroke(); });
    };
    const D = {
      crt1: [256, 176, crt(['AUDIT  WEEK 42', '> scan ledger', '  1687 checks  OK', '    20 failed', '   130 fixed', '> diff  W41..W42', '  +3   -11   =0', '> report ready _'])],
      crt2: [256, 176, crt(['ID    STATE  AGE', '#212  FIXED   3d', '#209  OPEN    5d', '#206  FIXED   6d', '#201  CLAIM   8d', '#198  FIXED   9d', '#190  OPEN   12d', '> 7 of 61 shown'])],
      dim: [256, 176, (g, W, H) => {
        g.fillStyle = '#000'; g.fillRect(0, 0, W, H); g.strokeStyle = 'rgba(40,160,110,.5)'; g.lineWidth = 1;
        for (let i = 20; i < W; i += 36) { g.beginPath(); g.moveTo(i, 30); g.lineTo(i, H - 14); g.stroke(); }
        g.strokeStyle = 'rgba(70,240,160,.9)'; g.lineWidth = 2.5; g.beginPath();
        for (let i = 0; i <= 30; i++) { const xx = 14 + i * (W - 28) / 30, yy = H * 0.6 - Math.sin(i * 0.5) * 22 - R() * 14; if (i) g.lineTo(xx, yy); else g.moveTo(xx, yy); }
        g.stroke(); g.fillStyle = 'rgba(70,240,160,.85)'; g.font = mono(13); g.textBaseline = 'top'; g.fillText('FINDINGS / WEEK', 14, 10);
      }],
      ctl: [256, 128, (g, W, H) => {
        g.fillStyle = '#121a21'; g.fillRect(0, 0, W, H); g.strokeStyle = '#2c3844'; g.lineWidth = 3; g.strokeRect(2, 2, W - 4, H - 4);
        g.textAlign = 'center'; g.textBaseline = 'middle'; g.font = mono(12, 700);
        ['CYCLE', 'AUDIT', 'PRINT', 'HOLD'].forEach((s, i) => { const cx = 40 + i * 56; g.strokeStyle = '#4a5866'; g.lineWidth = 3; g.beginPath(); g.arc(cx, 46, 15, 0, Math.PI * 2); g.stroke(); g.fillStyle = '#c3cdd6'; g.fillText(s, cx, 72); });
        g.fillStyle = '#03140c'; g.fillRect(20, 88, 216, 30); g.fillStyle = '#5cffb0'; g.font = mono(17, 700); g.fillText('W42  0042  OK', 128, 104);
      }],
      vent: [64, 64, (g, W, H) => {
        g.fillStyle = '#ffffff'; g.fillRect(0, 0, W, H);
        for (let i = 0; i < 7; i++) { g.fillStyle = '#1a2026'; g.fillRect(5, 5 + i * 8.4, W - 10, 4.4); g.fillStyle = 'rgba(255,255,255,.6)'; g.fillRect(5, 9.6 + i * 8.4, W - 10, 1.2); }
      }],
      spec: [256, 160, (g, W, H) => {
        g.fillStyle = '#021018'; g.fillRect(0, 0, W, H); g.strokeStyle = 'rgba(36,232,255,.18)'; g.lineWidth = 1;
        for (let i = 0; i < 6; i++) { g.beginPath(); g.moveTo(16, 34 + i * 20); g.lineTo(W - 12, 34 + i * 20); g.stroke(); }
        const ys = []; for (let xx = 16; xx < W - 12; xx += 2) ys.push([xx, H - 20 - ([[60, 70, 10], [104, 40, 6], [150, 95, 8], [196, 55, 12]].reduce((s, [c, h, w]) => s + h * Math.exp(-((xx - c) ** 2) / (2 * w * w)), 0) + 4 + R() * 3)]);
        g.beginPath(); g.moveTo(16, H - 20); ys.forEach(([xx, yy]) => g.lineTo(xx, yy)); g.lineTo(W - 12, H - 20); g.closePath(); g.fillStyle = 'rgba(36,232,255,.2)'; g.fill();
        g.beginPath(); ys.forEach(([xx, yy], i) => (i ? g.lineTo(xx, yy) : g.moveTo(xx, yy))); g.strokeStyle = '#7ff4ff'; g.lineWidth = 2.5; g.stroke();
        g.fillStyle = '#9ff6ff'; g.font = mono(13, 700); g.textBaseline = 'top'; g.fillText('SPECTRUM  m/z', 14, 8); g.textAlign = 'right'; g.fillText('214.6', W - 12, 8);
        scan(g, W, H, 0.18);
      }],
      read: [128, 48, (g, W, H) => {
        g.fillStyle = '#021016'; g.fillRect(0, 0, W, H); g.font = mono(17, 700); g.textBaseline = 'middle';
        g.fillStyle = '#7ff4ff'; g.fillText('37.0°C', 8, H / 2); g.fillStyle = '#38f5b8'; g.fillText('OK', W - 32, H / 2);
      }],
      holoA: [256, 160, holo((g, W, H) => {
        const cx = W / 2, cy = H / 2 + 4, ring = [], top = [cx + 4, cy - 58], bot = [cx - 2, cy + 56];
        for (let i = 0; i < 7; i++) { const a = i / 7 * Math.PI * 2; ring.push([cx + Math.cos(a) * 46, cy - 6 + Math.sin(a) * 15]); }
        g.fillStyle = 'rgba(60,240,210,.16)'; g.beginPath(); g.moveTo(...top); ring.forEach((q) => g.lineTo(...q)); g.closePath(); g.fill();
        g.strokeStyle = 'rgba(130,255,228,.95)'; g.lineWidth = 2;
        ring.forEach((q, i) => { const n = ring[(i + 1) % 7]; g.beginPath(); g.moveTo(...top); g.lineTo(...q); g.lineTo(...bot); g.moveTo(...q); g.lineTo(...n); g.stroke(); });
        g.fillStyle = '#9ffbe8'; g.font = mono(12, 700); g.textBaseline = 'top'; g.fillText('SAMPLE 07', 14, 12); g.fillText('98.2%', W - 58, H - 24);
      })],
      holoB: [256, 160, holo((g, W, H) => {
        const n = [], cx = W / 2, cy = H / 2;
        for (let i = 0; i < 34; i++) { const a = R() * Math.PI * 2, rr = Math.sqrt(R()); n.push([cx + Math.cos(a) * rr * 82, cy + Math.sin(a) * rr * 50]); }
        g.strokeStyle = 'rgba(70,215,255,.75)'; g.lineWidth = 1.4;
        n.forEach((a, i) => n.forEach((b, j) => { if (j > i && Math.hypot(a[0] - b[0], a[1] - b[1]) < 34) { g.beginPath(); g.moveTo(...a); g.lineTo(...b); g.stroke(); } }));
        g.fillStyle = '#c4f6ff'; n.forEach((a) => { g.beginPath(); g.arc(a[0], a[1], 2.6, 0, Math.PI * 2); g.fill(); });
        g.font = mono(12, 700); g.textBaseline = 'top'; g.fillText('MODEL  v3', 14, 12); g.fillText('0.87', W - 46, H - 24);
      })],
      grid: [128, 128, (g, W, H) => {
        g.fillStyle = '#000'; g.fillRect(0, 0, W, H); g.strokeStyle = 'rgba(50,230,210,.55)'; g.lineWidth = 1.5;
        for (let i = 8; i < W; i += 15) { g.beginPath(); g.moveTo(i, 0); g.lineTo(i, H); g.stroke(); g.beginPath(); g.moveTo(0, i); g.lineTo(W, i); g.stroke(); }
        g.strokeStyle = 'rgba(90,250,230,.9)'; g.lineWidth = 3; g.strokeRect(3, 3, W - 6, H - 6);
      }],
      paper: [128, 192, (g, W, H) => {
        g.fillStyle = '#e4e9ec'; g.fillRect(0, 0, W, H); g.fillStyle = '#b4bdc4';
        for (let yy = 8; yy < H; yy += 16) [7, W - 7].forEach((xx) => { g.beginPath(); g.arc(xx, yy, 3, 0, Math.PI * 2); g.fill(); });
        g.fillStyle = '#3b4652'; g.fillRect(18, 12, 60, 7);
        for (let i = 0; i < 14; i++) { g.fillStyle = 'rgba(60,72,84,' + (0.45 + R() * 0.4).toFixed(2) + ')'; g.fillRect(18, 28 + i * 11, 30 + R() * 62, 4); }
      }]
    };
    const [w, h, draw] = D[k];
    TX[key] = ctex(w, h, draw); return TX[key];
  }
  // somewhere to sit and look at the site as a stranger would
  lounge(r, x, y) {
    const g = r.g;
    this.box(g, x, y, 0.08, 2.2, 0.75, 0.32, OM.frame); this.box(g, x, y, 0.4, 2.2, 0.2, 0.42, OM.frame);
    this.box(g, x + 0.5, y + 1.15, 0.08, 1.2, 0.6, 0.3, OM.deskTop);
  }
  // Two more screens on a trading desk (desk() at x, y), one at each end on its own stand and turned in to the
  // trader, so the desk is a bank of four: a price line on the left, candles on the right. left/right: which ends.
  sideScreens(r, x, y, left = true, right = true) {
    [[x + 0.06, 0.66, left, 0], [x + 1.84, -0.66, right, 1]].forEach(([sx, rot, on, idx]) => {
      if (!on) return;
      const s = new THREE.Group(); s.position.copy(this.V(sx, y + 0.42, 0)); s.rotation.y = rot; r.g.add(s);
      // in s: x across the screen, +z towards the trader, y up from the floor
      const add = (geo, mat, sx2, sy, sz, px, py, pz) => { const m = new THREE.Mesh(geo, mat); m.scale.set(sx2, sy, sz); m.position.set(px, py, pz); s.add(m); return m; };
      add(rboxGeo(0.5, 0.32, 0.035, 0.012), OM.dark, 1, 1, 1, 0, 0.9, 0).castShadow = true;
      add(G.plane, new THREE.MeshBasicMaterial({ map: idx ? candleTex() : orangeMonTex(), toneMapped: false }), 0.46, 0.28, 1, 0, 0.9, 0.019);
      add(G.box, OM.frame, 0.035, 0.2, 0.03, 0, 0.66, -0.04);
      add(G.box, OM.frame, 0.17, 0.012, 0.13, 0, 0.566, -0.04);
    });
  }
  // A board on a back wall that stays under the neon, as every board in his picture does: its face 0.72 to 1.27, a
  // dark backing to 1.30, the neon from 1.44. wall 'back' is the y0 wall (along x), 'left' the x0 wall (along y),
  // a0..a1 along it. With tex a fixed picture; without, a live screen() the update draws into, which it returns.
  // o.edge lights a thin rim round it in that colour; o.tiles splits a kanban into its four columns with dark
  // mullions, his row of tiles.
  rcBoard(r, wall, a0, a1, tex, o = {}) {
    const w = a1 - a0, h = o.h || 0.55, zc = 1.27 - h / 2, back = wall === 'back', s = tex ? null : screen(w, h);
    const face = (mat, ww, hh, off) => {
      const m = new THREE.Mesh(G.plane, mat); m.scale.set(ww, hh, 1);
      if (back) m.position.copy(this.V(r.x0 + (a0 + a1) / 2, r.y0 + off, zc)); else { m.rotation.y = Math.PI / 2; m.position.copy(this.V(r.x0 + off, r.y0 + (a0 + a1) / 2, zc)); }
      r.g.add(m); return m;
    };
    face(new THREE.MeshBasicMaterial({ map: tex || s.tex, toneMapped: false }), w, h, 0.11);
    if (o.edge) { const k = 'rcEdge' + o.edge; OM[k] = OM[k] || emis(o.edge, o.glow || 1.2); face(OM[k], w + 0.04, h + 0.04, 0.104); }
    if (back) this.box(r.g, r.x0 + a0 - 0.05, r.y0 + 0.05, zc - h / 2 - 0.03, w + 0.1, 0.05, h + 0.06, OM.dark, false);
    else this.box(r.g, r.x0 + 0.05, r.y0 + a0 - 0.05, zc - h / 2 - 0.03, 0.05, w + 0.1, h + 0.06, OM.dark, false);
    if (o.tiles && s) {
      const W = s.c.width, cw = (W - 30) / 4;
      for (let i = 1; i < 4; i++) {
        const a = a0 + (15 + i * cw) / W * w;
        if (back) this.box(r.g, r.x0 + a - 0.025, r.y0 + 0.112, zc - h / 2, 0.05, 0.012, h, OM.dark, false);
        else this.box(r.g, r.x0 + 0.112, r.y0 + a - 0.025, zc - h / 2, 0.012, 0.05, h, OM.dark, false);
      }
    }
    return s;
  }
  // His server room's floor: darker than the other rooms' and glossy, the racks faintly mirrored in it, with
  // perforated tiles in the aisles before the racks' fronts, where the cold air comes up
  rcServerFloor(r) {
    if (!OM.rcFloor) OM.rcFloor = std({ map: this.rcTex('floor'), roughness: 0.4, metalness: 0.35 });
    const RS = CO.iso.RS, m = new THREE.Mesh(G.plane, OM.rcFloor);
    m.scale.set(RS - 0.08, RS - 0.08, 1); m.rotation.x = -Math.PI / 2; m.position.copy(this.V(r.x0 + RS / 2, r.y0 + RS / 2, 0.083)); m.receiveShadow = true; r.g.add(m);
  }
  // The server room's workstation, as his: one solid dark desk down to the floor, a wide monitor of the racks'
  // status on its stand (r.mons[i]: lit while its expert works, dark glass otherwise), a keyboard, a mouse, a mug,
  // and a small tower at its end with its lights. The expert sits where desk()'s would (x + 0.95, y + 1.3).
  rcWorkstation(r, x, y, i) {
    const g = r.g;
    this.rb(g, x, y + 0.06, 0.08, 1.72, 0.76, 0.44, OM.desk, 0.03);
    this.box(g, x + 0.04, y + 0.83, 0.12, 1.64, 0.012, 0.34, OM.frame, false);
    this.rb(g, x - 0.03, y, 0.52, 1.78, 0.9, 0.05, OM.deskTop, 0.02);
    this.box(g, x + 0.79, y + 0.18, 0.57, 0.2, 0.14, 0.012, OM.frame, false);
    this.box(g, x + 0.87, y + 0.22, 0.58, 0.04, 0.04, 0.16, OM.frame, false);
    this.rb(g, x + 0.31, y + 0.13, 0.66, 1.16, 0.05, 0.5, OM.dark, 0.02);
    const scr = new THREE.MeshBasicMaterial({ map: this.rcTex('status'), color: new THREE.Color(0x0a1016), toneMapped: false });
    const face = new THREE.Mesh(G.plane, scr); face.scale.set(1.08, 0.42, 1); face.position.copy(this.V(x + 0.89, y + 0.186, 0.91)); g.add(face);
    r.mons[i] = scr;
    this.rb(g, x + 0.58, y + 0.5, 0.57, 0.64, 0.2, 0.022, OM.frame, 0.008, false);
    this.rb(g, x + 1.33, y + 0.54, 0.57, 0.08, 0.12, 0.022, OM.frame, 0.02, false);
    this.cyl(g, x + 0.2, y + 0.62, 0.57, 0.045, 0.09, OM.white);
    this.rb(g, x + 1.86, y + 0.12, 0.08, 0.26, 0.62, 0.56, OM.rack, 0.02);
    [[0.3, '#38f2b8'], [0.38, '#00e5ff']].forEach(([z, col]) => this.box(g, x + 1.9, y + 0.742, z, 0.04, 0.008, 0.016, amat(col).glow, false));
  }
  // the room's textures: drawn once, kept in TX so a new layout finds them (release() spares what TX holds)
  rcTex(k) {
    const id = 'rc' + k; if (TX[id]) return TX[id];
    const T = {
      // a rack's side: a dark panel in three, a vent near its head and its foot
      side: [128, 256, (g, W, H) => {
        g.fillStyle = '#161d25'; g.fillRect(0, 0, W, H); g.fillStyle = '#0d1217'; g.fillRect(W / 3, 0, 2, H); g.fillRect(2 * W / 3, 0, 2, H);
        g.fillStyle = '#222b35'; g.fillRect(0, 0, W, 4); g.fillRect(0, 0, 3, H);
        g.fillStyle = '#0b1015'; for (let y of [22, H - 46]) for (let x = 14; x < W - 14; x += 7) g.fillRect(x, y, 3, 22);
      }],
      // a rack's top: a lighter plate, a grille over its fans, a cut-out at the back where the cables go in
      top: [128, 128, (g, W, H) => {
        g.fillStyle = '#505b67'; g.fillRect(0, 0, W, H); g.fillStyle = '#626e7b'; g.fillRect(0, 0, W, 3); g.fillRect(0, 0, 3, H);
        g.fillStyle = '#323b45'; for (let x = 22; x < W - 22; x += 7) g.fillRect(x, 52, 3, 50);
        g.fillStyle = '#1c232a'; g.fillRect(18, 10, W - 36, 22);
      }],
      // the server room's floor: dark tiles a unit across, hairline seams, perforated tiles in the aisles
      floor: [512, 512, (g, W) => {
        const n = 7, s = W / n, holes = { '3,1': 1, '4,1': 1, '5,1': 1, '0,2': 1, '1,2': 1, '3,6': 1, '4,6': 1, '5,6': 1, '2,4': 1 };
        g.fillStyle = '#0b1014'; g.fillRect(0, 0, W, W);
        for (let i = 0; i < n; i++) for (let j = 0; j < n; j++) {
          const x = i * s + 1.5, y = j * s + 1.5, w = s - 3;
          g.fillStyle = (i + j) % 2 ? '#1d2731' : '#1a242d'; g.fillRect(x, y, w, w);
          if (holes[i + ',' + j]) { g.fillStyle = '#10161c'; for (let a = x + 7; a < x + w - 5; a += 6) for (let b = y + 7; b < y + w - 5; b += 6) g.fillRect(a, b, 2.5, 2.5); }
        }
      }],
      // the workstation's monitor: the racks as a map of lit squares, a load line under it
      status: [256, 128, (g, W, H) => {
        g.fillStyle = '#04150f'; g.fillRect(0, 0, W, H); g.fillStyle = '#38f5b8'; g.fillRect(10, 8, 60, 7); g.fillStyle = 'rgba(36,232,255,.6)'; g.fillRect(80, 8, 44, 7);
        for (let i = 0; i < 8; i++) for (let j = 0; j < 3; j++) { g.fillStyle = (i * 3 + j) % 7 ? 'rgba(56,245,184,.75)' : 'rgba(36,232,255,.9)'; g.fillRect(10 + i * 18, 24 + j * 18, 14, 14); }
        g.strokeStyle = '#38f5b8'; g.lineWidth = 2.5; g.beginPath(); for (let x = 10; x < W - 10; x += 8) { const y = 104 - Math.abs(Math.sin(x * 0.07)) * 16 - (x % 24 ? 0 : 6); if (x === 10) g.moveTo(x, y); else g.lineTo(x, y); } g.stroke();
        g.fillStyle = 'rgba(56,245,184,.5)'; for (let k = 0; k < 4; k++) g.fillRect(170, 26 + k * 12, 70 - k * 12, 6);
      }],
      // the Manager's consoles: rows of keys and small screens, a metre of console that repeats along it
      console: [256, 84, (g, W, H) => {
        g.fillStyle = '#141b23'; g.fillRect(0, 0, W, H); g.fillStyle = '#0a0f14'; g.fillRect(0, 0, W, 3);
        for (let k = 0; k < 3; k++) { g.fillStyle = '#0c1520'; g.fillRect(10 + k * 82, 8, 70, 30); }
        for (let row = 0; row < 3; row++) for (let k = 0; k < 20; k++) { g.fillStyle = '#26303b'; g.fillRect(10 + k * 12, 46 + row * 12, 9, 8); }
      }],
      consoleGlow: [256, 84, (g, W, H) => {
        g.fillStyle = '#000'; g.fillRect(0, 0, W, H);
        ['rgba(36,232,255,.35)', 'rgba(59,130,246,.4)', 'rgba(56,245,184,.3)'].forEach((c, k) => { g.fillStyle = c; g.fillRect(14 + k * 82, 12, 40 + (k % 2) * 18, 6); g.fillRect(14 + k * 82, 24, 26, 4); });
        const R = rng(7); for (let row = 0; row < 3; row++) for (let k = 0; k < 20; k++) if (R() < 0.07) { g.fillStyle = R() < 0.5 ? 'rgba(36,232,255,.7)' : 'rgba(56,245,184,.7)'; g.fillRect(10 + k * 12, 46 + row * 12, 9, 8); }
      }],
      // the trading desk's computer, its link screen in orange (pcTex's, recoloured)
      pcOrange: [256, 176, (g, W, H) => {
        g.fillStyle = '#26140a'; g.fillRect(0, 0, W, H); g.strokeStyle = '#ff9438'; g.lineWidth = 8; g.strokeRect(4, 4, W - 8, H - 8);
        g.fillStyle = '#ff9438'; g.font = '700 96px JetBrains Mono, monospace'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('↗', W / 2, 92);
      }],
      // the column of light over the Manager's core: bright at its foot, gone at its head, faint bands rising in it
      beam: [32, 256, (g, W, H) => {
        const gr = g.createLinearGradient(0, H, 0, 0); gr.addColorStop(0, 'rgba(255,255,255,.9)'); gr.addColorStop(0.35, 'rgba(255,255,255,.45)'); gr.addColorStop(1, 'rgba(255,255,255,0)');
        g.fillStyle = gr; g.fillRect(0, 0, W, H);
        g.fillStyle = 'rgba(255,255,255,.12)'; for (let y = 20; y < H; y += 26) g.fillRect(0, y, W, 3);
      }],
    }[k];
    const t = ctex(T[0], T[1], T[2]);
    if (k === 'console' || k === 'consoleGlow') { t.wrapS = THREE.RepeatWrapping; t.repeat.set(4, 1); }
    return (TX[id] = t);
  }
  // A console along one of the Manager's back walls, as his: a dark body, a top sloped to the room with rows of keys
  // and small lit screens on it, a cyan lip along its front. wall 'back' or 'left', a0..a1 along it.
  rcConsole(r, wall, a0, a1) {
    if (!OM.rcConsole) OM.rcConsole = std({ map: this.rcTex('console'), emissiveMap: this.rcTex('consoleGlow'), emissive: 0xffffff, emissiveIntensity: 1.0, roughness: 0.42, metalness: 0.35 });
    const len = a1 - a0, back = wall === 'back', s = new THREE.Group();
    s.position.copy(back ? this.V(r.x0 + (a0 + a1) / 2, r.y0 + 0.06, 0) : this.V(r.x0 + 0.06, r.y0 + (a0 + a1) / 2, 0)); s.rotation.y = back ? 0 : Math.PI / 2; r.g.add(s);
    // in s: x along the wall, +z into the room, y up from the floor
    const add = (geo, mat, sx, sy, sz, px, py, pz, rx) => { const m = new THREE.Mesh(geo, mat); m.scale.set(sx, sy, sz); m.position.set(px, py, pz); if (rx) m.rotation.x = rx; s.add(m); return m; };
    const body = add(rboxGeo(len, 0.36, 0.46, 0.03), OM.desk, 1, 1, 1, 0, 0.08 + 0.18, 0.23); body.castShadow = true; body.receiveShadow = true;
    add(G.box, OM.dark, len - 0.04, 0.05, 0.42, 0, 0.47, 0.22, 0.4);
    add(G.plane, OM.rcConsole, len - 0.1, 0.38, 1, 0, 0.497, 0.23, -Math.PI / 2 + 0.4);
    add(G.box, OM.cyan.soft, len - 0.06, 0.014, 0.012, 0, 0.36, 0.462);
    add(G.box, OM.dark, len - 0.02, 0.06, 0.02, 0, 0.11, 0.455);
  }
  // his trading desk: the orange-lit room, its boards under the neon -- on the back-right wall the desk's status in
  // an orange frame (r.wall) and its chart in a yellow-green one, on the back-left wall the kanban in its tiles
  // (r.kb) with the see-through frame before it -- and desks of four screens with their traders, a little apart
  rcTradingRoom(r, d) {
    const x0 = r.x0, y0 = r.y0, k = d.key;
    r.wall = this.rcBoard(r, 'back', 1.8, 4.0, null, { edge: '#ff8a3a', glow: 1.6 });
    this.rcBoard(r, 'back', 4.25, 6.7, orangeWallTex(), { edge: '#c8e06a', glow: 0.9 });
    r.kb = this.rcBoard(r, 'left', 1.45, 5.15, null, { tiles: true });
    // two desks as his: one towards the back, the other to the right of it and a little further forward
    const ex = d.experts.slice(0, 3), xs = ex.length === 1 ? [2.4] : ex.length === 2 ? [1.2, 4.15] : [0.35, 2.55, 4.75], ys = ex.length === 2 ? [2.4, 2.85] : [2.75, 2.75, 2.75];
    ex.forEach((e, i) => {
      this.desk(r, x0 + xs[i], y0 + ys[i], i, true);
      this.sideScreens(r, x0 + xs[i], y0 + ys[i], i === 0 || ex.length < 3, i === ex.length - 1 || ex.length < 3);
    });
    this.holoFrame(r, x0 + 0.75, y0 + 3.75);
    ex.forEach((e, i) => this.agent(r, x0 + xs[i] + 0.95, y0 + ys[i] + 1.3, i, CO.expertName(e)));
    this.terminal(r, x0 + 0.3, y0 + 0.32, d.link || CO.DEPT_LINK[k] || CO.DEPT_LINK.custom);
    // its computer's screen in the room's orange: a green one was the only cold light in his warm room
    if (r.pcFace) r.pcFace.map = this.rcTex('pcOrange');
    this.plant(r, x0 + 0.45, y0 + 5.7);
    this.plate(r);
  }
  // The Manager's room, as his: a stepped circular dais in the middle, a white-hot core in a column of light with
  // three rings over it, concentric cyan rings on the floor, and a console under a board on both back walls.
  hubRoom(r) {
    const g = r.g, x0 = r.x0, y0 = r.y0, cy = OM.cyan, c = this.V(x0 + 3.8, y0 + 3.55, 0);
    // his back walls: a long console along each, sloped to the room; over the back-right one the turns of the day
    // (r.bars), over the back-left one the plan's kanban in four tiles (r.kb), both in pale frames under the neon
    this.rcConsole(r, 'back', 1.3, 6.0);
    this.rcConsole(r, 'left', 1.15, 5.65);
    r.bars = this.rcBoard(r, 'back', 1.45, 5.85, null, { edge: '#a9bccb', glow: 0.55 });
    r.kb = this.rcBoard(r, 'left', 1.3, 5.5, null, { tiles: true, edge: '#a9bccb', glow: 0.55 });
    const floor = new THREE.Mesh(G.plane, new THREE.MeshBasicMaterial({ map: hubFloorTex(), color: new THREE.Color(0x46c8f0).multiplyScalar(0.5), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
    floor.scale.set(6.4, 6.4, 1); floor.rotation.x = -Math.PI / 2; floor.position.set(c.x, 0.1, c.z); g.add(floor); r.floor = floor;
    // his dais: a wide dark disc with a pale metal rim, a raised drum on it with a cyan lip, a white-hot core, a
    // column of light and three rings of light over it, smaller as they rise
    [[1.72, 0.18, 0.08, OM.plinth, OM.daisRim], [1.05, 0.22, 0.26, OM.dark, cy.rim]].forEach(([rad, h, z0, mat, rim]) => {
      const d = new THREE.Mesh(G.cyl, mat); d.scale.set(rad, h, rad); d.position.set(c.x, z0 + h / 2, c.z); d.castShadow = true; d.receiveShadow = true; g.add(d);
      const lip = new THREE.Mesh(G.ringT, rim); lip.scale.set(rad, rad, rad * 1.2); lip.rotation.x = Math.PI / 2; lip.position.set(c.x, z0 + h, c.z); g.add(lip);
    });
    // round it on the floor, two thick pale arcs, as his
    [[0.35, 1.9], [3.55, 1.5]].forEach(([a0, len]) => {
      const arc = new THREE.Mesh(new THREE.TorusGeometry(1, 0.03, 6, 60, len), OM.daisArc); arc.userData.own = true;
      arc.scale.set(2.3, 2.3, 0.4); arc.rotation.x = Math.PI / 2; arc.rotation.z = a0; arc.position.set(c.x, 0.1, c.z); g.add(arc);
    });
    const core = new THREE.Mesh(G.sphere, new THREE.MeshBasicMaterial({ color: new THREE.Color(0xffffff).multiplyScalar(3.2) })); core.scale.setScalar(0.3); core.position.set(c.x, 1.0, c.z); g.add(core);
    const halo = glowSprite(0xbff6ff, 0.55, 3.0); halo.position.set(c.x, 1.0, c.z); g.add(halo);
    // his drum: a pale metal band round its top, a cyan glow where it meets the disc, small lights round the disc's rim
    const band = new THREE.Mesh(G.ringT, OM.daisRim); band.scale.set(1.08, 1.08, 2.6); band.rotation.x = Math.PI / 2; band.position.set(c.x, 0.47, c.z); g.add(band);
    const foot = new THREE.Mesh(G.ringT, cy.rim); foot.scale.set(1.13, 1.13, 0.8); foot.rotation.x = Math.PI / 2; foot.position.set(c.x, 0.27, c.z); g.add(foot);
    const o = new THREE.Object3D(), nodes = new THREE.InstancedMesh(G.cyl8, cy.glow, 12);
    for (let i = 0; i < 12; i++) { const a = i / 12 * Math.PI * 2; o.position.set(c.x + Math.cos(a) * 1.6, 0.265, c.z + Math.sin(a) * 1.6); o.scale.set(0.035, 0.01, 0.035); o.updateMatrix(); nodes.setMatrixAt(i, o.matrix); }
    nodes.computeBoundingSphere(); g.add(nodes);
    // his column of light: a frosted shaft from the drum to over the top ring, brightest at the core, gone at its head
    G.rcBeam = G.rcBeam || new THREE.CylinderGeometry(0.3, 0.46, 1, 40, 1, true);
    const beam = new THREE.Mesh(G.rcBeam, new THREE.MeshBasicMaterial({ map: this.rcTex('beam'), color: new THREE.Color(0x8feeff).multiplyScalar(0.75), transparent: true, opacity: 0.5, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
    beam.scale.set(1, 2.3, 1); beam.position.set(c.x, 0.48 + 1.15, c.z); g.add(beam);
    // and the sparks in it: motes rising in the shaft and drifting round the dais, turning slowly (r.spin)
    const R = rng(83), n = 140, motes = new THREE.InstancedMesh(G.box, amat('#7fe8f8').glow, n);
    for (let i = 0; i < n; i++) {
      const inShaft = i < 85, a = R() * Math.PI * 2, rad = inShaft ? Math.sqrt(R()) * 0.38 : 1.2 + R() * 1.25, y = inShaft ? 0.6 + R() * R() * 2.1 : 0.16 + R() * 0.8, s = 0.012 + R() * 0.014;
      o.position.set(Math.cos(a) * rad, y, Math.sin(a) * rad); o.rotation.set(R() * 3, R() * 3, 0); o.scale.set(s, s, s); o.updateMatrix(); motes.setMatrixAt(i, o.matrix);
    }
    motes.computeBoundingSphere();
    r.spin = new THREE.Group(); r.spin.position.set(c.x, 0, c.z); r.spin.add(motes); g.add(r.spin);
    // the rings: thin lines of light as his, smaller as they rise
    OM.rcRing = OM.rcRing || emis('#8ff0ff', 1.15);
    r.holo = [[1.45, 0.98], [1.85, 0.84], [2.25, 0.7]].map(([y, s]) => {
      const h = new THREE.Mesh(G.ringT, OM.rcRing); h.scale.set(s, s, 1.1); h.rotation.x = Math.PI / 2; h.position.set(c.x, y, c.z); h.userData.y = y; g.add(h); return h;
    });
    r.core = core; r.coreAt = this.V(x0 + 3.0, y0 + 2.8, 2.75);   // his "need you" badge: over the rings, a little behind the core
    const light = new THREE.PointLight(0x00e5ff, 4.2, 11, 1.6); light.position.set(c.x, 1.8, c.z); g.add(light);
    this.agent(r, x0 + 3.8, y0 + 5.85, 0, 'Manager', { stand: true });
    this.plant(r, x0 + 6.4, y0 + 0.5);
    this.plate(r, 'hubp'); r.plateAt = this.V(x0 + 6.1, y0 + 6.75, 1.3);
    r.need = document.createElement('div'); r.need.className = 'p3need'; r.need.addEventListener('click', () => CO.emit('office:click', 'hub')); this.layer.appendChild(r.need);
  }
  // The weekly audit as in his picture: two retro consoles side by side along the back-left wall facing the room,
  // the week's screen on the back-right wall, the supervisor at a desk between them, a teleprinter for the report
  // with its platen to the front-right wall (his stands by the front-left one, but there the room's plate hid it from
  // the home view), a cabinet beside it, a plant in the left corner
  auditRoom(r) {
    const x0 = r.x0, y0 = r.y0;
    this.console3(r, x0 + 1.1, y0 + 1.9, Math.PI / 2, 0);
    this.console3(r, x0 + 1.1, y0 + 3.95, Math.PI / 2, 1);
    this.wallScreen(r, 1.6, 5.4);
    this.desk(r, x0 + 2.9, y0 + 1.9, 0, false);
    this.agent(r, x0 + 3.85, y0 + 3.2, 0, 'Supervisor');
    this.raPrinter(r, x0 + 6.08, y0 + 5.75, -Math.PI / 2);
    this.cabinet(r, x0 + 6.45, y0 + 2.6, 0.45, 2.2, 0.72);
    this.plant(r, x0 + 0.45, y0 + 6.5);
    this.plate(r, 'auditp');
  }
  // The vault: a strongroom. Its two back walls are armoured steel instead of glass -- a dark lower band of plates,
  // as his rooms' dado is dark, lighter plates above, a mint seam lit between them, rivets -- and in the wall the
  // corridor comes in by (y = y0, where the lane from the Manager arrives at the middle) stands a round door as big
  // as that wall allows: 1.18 across, 0.46 thick, twelve heavy bolts, on one massive hinge left of the opening. It
  // stands open into the room until its outer face (bolts, wheel, dial) looks at the home view. Safe-deposit lockers
  // are built into the other armoured wall; two floodlights on the door wall light the door and the money. The money
  // itself is piles(): pallets that fill with what the company has earned, and a cart in the walk wheeling in the
  // latest. In front: a counting table, two safes; by the door a shelf of strongboxes. Every top stays at 1.38 or
  // under, clear of the neon over the walls. A visitor finds the door shut.
  vaultRoom(r) {
    const g = r.g, x0 = r.x0, y0 = r.y0;
    const D = r.vt = {
      // the walls: inner face at WT, outer at WO, from under the floor's top to the top, the lit seam's height
      WT: 0.2, WO: -0.1, wb: -0.04, top: 1.38, seam: 0.62,
      // the door: its centre along the wall and its height, the jamb, the leaf's lip and thickness, the collar's
      // outer radius and front, the hinge's axis (left of the opening, off the wall), the leaf's centre when shut,
      // and how far it opens (the leaf clears the opening as the home view sees it, short of face-on so its
      // thickness shows)
      u: 3.5, ch: 0.69, hole: 0.615, lip: 0.59, T: 0.46, collar: 0.69, cz: 0.3, hu: -0.815, hv: 0.44, seat: 0.07, open: -1.8,
      // the floor: pallets of P a side, ET10 left of the walk from the door and USDC right, three rows each; the
      // cart's centre in the walk (behind the room's plate, which in the home view covers the floor round (3.9, 5))
      P: 0.85, ue: [1.63, 0.68], re: [2.2, 3.15, 4.1], uu: [4.52, 5.47], ru: [1.45, 2.4, 3.35], cart: [3.5, 3.15] };
    this.vtMats(D);
    // the armour takes the place of the shell's glass and dark dado on the two back walls
    const wy = this.V(0, y0, 0).z, wx = this.V(x0, 0, 0).x;
    g.children.forEach((m) => {
      if (m.material === OM.wallDark) m.visible = false;
      if (m.material === OM.glass && m.geometry === G.plane && ((m.rotation.y === 0 && Math.abs(m.position.z - wy) < 1e-6) || (m.rotation.y !== 0 && Math.abs(m.position.x - wx) < 1e-6))) m.visible = false;
    });
    const shadowed = (m) => { m.castShadow = true; m.receiveShadow = true; g.add(m); return m; };
    const wY = shadowed(new THREE.Mesh(this.vtWallGeo('y', D), [OM.vtArmour, OM.vtSteelDk])); wY.position.copy(this.V(x0, y0 + D.WO + 0.012, 0));
    const wX = shadowed(new THREE.Mesh(this.vtWallGeo('x', D), [OM.vtArmour, OM.vtSteelDk])); wX.position.copy(this.V(x0 + D.WT - 0.012, y0, 0)); wX.rotation.y = -Math.PI / 2;
    // the lit seam between the bands, along both walls' faces (broken round the door's collar)
    const RS = CO.iso.RS, sh = D.seam + 0.002, gap = D.collar + 0.05;
    [[D.WT, D.u - gap], [D.u + gap, RS - 0.02]].forEach(([a, b]) => this.box(g, x0 + a, y0 + D.WT, sh - 0.009, b - a, 0.012, 0.018, OM.vtSeam, false));
    this.box(g, x0 + D.WT, y0 + D.WT, sh - 0.009, 0.012, RS - 0.02 - D.WT, 0.018, OM.vtSeam, false);
    this.vtRivets(r);
    const wg = new THREE.Group(); wg.position.copy(this.V(x0 + D.u, y0, D.ch)); g.add(wg);
    const add = (geom, mat, x, y, z, sx, sy, sz, par, shadow = true) => {
      const m = new THREE.Mesh(geom, mat); m.position.set(x, y, z); if (sx != null) m.scale.set(sx, sy, sz); if (shadow) { m.castShadow = true; m.receiveShadow = true; } (par || wg).add(m); return m;
    };
    // the collar: a stepped steel ring round the opening, the room's mint neon on its face, a thinner ring of light
    // deep in the jamb; a threshold plate across the opening's foot
    add(G.vtCollar, OM.vtSteel, 0, 0, 0);
    add(G.ringT, OM.vtNeon, 0, 0, D.cz + 0.003, 0.656, 0.656, 0.656, null, false);
    add(G.ring, OM.vtNeon, 0, 0, 0.05, 0.6, 0.6, 0.6, null, false);
    add(G.box, OM.vtSteelDk, 0, 0.088 - D.ch, 0.12, 1.12, 0.016, 0.44);
    // the hinge: a barrel standing off the wall on two plates, chrome caps and a dome; the door hangs on it by two
    // arms with their knuckles
    add(G.cyl, OM.vtSteel, D.hu, 0, D.hv, 0.105, 1.12, 0.105);
    [-0.56, 0.56].forEach((y) => add(G.cyl, OM.vtChrome, D.hu, y, D.hv, 0.12, 0.05, 0.12));
    add(G.hemi, OM.vtChrome, D.hu, 0.585, D.hv, 0.09, 0.06, 0.09);
    [-0.47, 0.47].forEach((y) => add(G.box, OM.vtSteelDk, D.hu - 0.04, y, 0.32, 0.32, 0.14, 0.24));
    // the door: a pivot on the hinge's axis; in it the leaf where it sits when shut, turned so its outer face (local
    // +z) looks out through the opening and its inner face is flush with the collar; the arms hold the inner face
    const piv = r.doorPivot = new THREE.Group(); piv.position.set(D.hu, 0, D.hv); piv.rotation.y = CO.RO ? 0 : D.open; wg.add(piv);
    const az = D.seat - D.hv + D.T / 2;
    [-0.32, 0.32].forEach((y) => {
      add(rboxGeo(0.56, 0.15, 0.11, 0.025), OM.vtSteel, 0.24, y, az + 0.055, null, null, null, piv);
      add(G.cyl, OM.vtChrome, 0, y, 0, 0.125, 0.16, 0.125, piv);
      [0.32, 0.44].forEach((x) => add(G.cyl8, OM.vtChrome, x, y, az + 0.112, 0.022, 0.012, 0.022, piv).rotation.x = Math.PI / 2);
    });
    const leaf = new THREE.Group(); leaf.position.set(-D.hu, 0, D.seat - D.hv); leaf.rotation.y = Math.PI; piv.add(leaf);
    const F = D.T / 2;
    add(G.vtLeaf, OM.vtSteel, 0, 0, 0, null, null, null, leaf);
    add(G.vtFace, OM.vtFace, 0, 0, F + 0.002, null, null, null, leaf, false);
    add(G.ringT, OM.vtNeon, 0, 0, F + 0.006, 0.505, 0.505, 0.505, leaf, false);
    // the locking bolts, twelve, thick, out of the door's edge all round (none straight up, so a shut door's stay
    // under the wall's top); bolt heads round the face
    const o = new THREE.Object3D(), bolts = new THREE.InstancedMesh(G.cyl, OM.vtChrome, 12), heads = new THREE.InstancedMesh(G.cyl8, OM.vtSteelDk, 16);
    for (let k = 0; k < 12; k++) {
      const a = (k + 0.5) / 12 * Math.PI * 2;
      o.position.set(Math.cos(a) * 0.59, Math.sin(a) * 0.59, 0); o.rotation.set(0, 0, a - Math.PI / 2); o.scale.set(0.045, 0.18, 0.045); o.updateMatrix(); bolts.setMatrixAt(k, o.matrix);
    }
    for (let k = 0; k < 16; k++) {
      const a = k / 16 * Math.PI * 2;
      o.position.set(Math.cos(a) * 0.46, Math.sin(a) * 0.46, F + 0.009); o.rotation.set(Math.PI / 2, 0, 0); o.scale.set(0.019, 0.016, 0.019); o.updateMatrix(); heads.setMatrixAt(k, o.matrix);
    }
    bolts.castShadow = true; leaf.add(bolts, heads);
    // the wheel: a boss and a hub, five spokes with knobs and the rim joining them; the dial above it
    add(G.cyl, OM.vtSteelDk, 0, 0, F + 0.03, 0.09, 0.06, 0.09, leaf).rotation.x = Math.PI / 2;
    add(G.cyl, OM.vtChrome, 0, 0, F + 0.085, 0.06, 0.07, 0.06, leaf).rotation.x = Math.PI / 2;
    add(G.wheel, OM.vtChrome, 0, 0, F + 0.09, 0.21, 0.21, 0.21, leaf);
    for (let k = 0; k < 5; k++) {
      const a = Math.PI / 2 + Math.PI / 5 + k * Math.PI * 2 / 5, sp = add(G.cyl, OM.vtChrome, Math.cos(a) * 0.145, Math.sin(a) * 0.145, F + 0.09, 0.016, 0.29, 0.016, leaf);
      sp.rotation.z = a - Math.PI / 2;
      add(G.sphere, OM.vtChrome, Math.cos(a) * 0.305, Math.sin(a) * 0.305, F + 0.09, 0.036, 0.036, 0.036, leaf);
    }
    add(G.cyl, OM.vtSteelDk, 0, 0.4, F + 0.015, 0.075, 0.03, 0.075, leaf).rotation.x = Math.PI / 2;
    add(G.vtDial, OM.vtDial, 0, 0.4, F + 0.031, null, null, null, leaf, false);
    // the inner face, what a visitor sees of a shut door: the bolt-work -- a boss, the bars that throw the bolts,
    // a small wheel to turn them from inside
    add(G.vtFace, OM.vtFace, 0, 0, -F - 0.002, 1.04, 1.04, 1, leaf, false).rotation.y = Math.PI;
    add(G.cyl8, OM.vtSteelDk, 0, 0, -F - 0.03, 0.12, 0.06, 0.12, leaf).rotation.x = Math.PI / 2;
    for (let k = 0; k < 8; k++) {
      const a = (k + 0.5) / 8 * Math.PI * 2, bar = add(G.box, OM.vtChrome, Math.cos(a) * 0.3, Math.sin(a) * 0.3, -F - 0.018, 0.36, 0.04, 0.028, leaf);
      bar.rotation.z = a;
      add(G.cyl8, OM.vtSteelDk, Math.cos(a) * 0.48, Math.sin(a) * 0.48, -F - 0.024, 0.038, 0.048, 0.038, leaf).rotation.x = Math.PI / 2;
    }
    add(G.wheel, OM.vtChrome, 0, 0, -F - 0.07, 0.15, 0.15, 0.15, leaf);
    add(G.cyl, OM.vtChrome, 0, 0, -F - 0.065, 0.04, 0.08, 0.04, leaf).rotation.x = Math.PI / 2;
    // the keypad right of the opening, its light blinking; the screen says whether the vault is open
    add(rboxGeo(0.24, 0.34, 0.055, 0.015), OM.dark, 0.97, 0.16, D.WT + 0.027);
    r.keyFace = add(G.plane, CO.RO ? OM.vtKeyS : OM.vtKeyO, 0.97, 0.16, D.WT + 0.056, 0.21, 0.3, 1, null, false);
    const led = add(G.box, OM.green.glow, 0.97, 0.37, D.WT + 0.01, 0.034, 0.02, 0.014, null, false); led.userData.blink = 2; (r.leds = r.leds || []).push(led);
    // on the floor, the arc the leaf's free edge sweeps, from beside the collar round to where it stands open
    if (!G.vtArc) {
      const parts = [], n = 12, span = -D.open - Math.atan2(D.hv - D.seat, -D.hu + D.lip);
      for (let k = 0; k < n; k++) { const t = new THREE.TorusGeometry(1, 0.012, 4, 6, 0.07); t.rotateZ((k + 0.5) * span / n - 0.035); parts.push(t); }
      G.vtArc = mergeGeometries(parts, false); parts.forEach((p) => p.dispose());
    }
    const arc = new THREE.Mesh(G.vtArc, OM.dash); arc.rotation.x = Math.PI / 2; arc.scale.set(1.46, 1.46, 0.3); arc.position.copy(this.V(x0 + D.u + D.hu, y0 + D.hv, 0.086)); g.add(arc);
    // where each money is stored, painted on the floor as a dashed outline round its pallets, faintly in its colour
    [[D.ue, D.re, OM.vtBayG], [D.uu, D.ru, OM.vtBayB]].forEach(([us, vs, mat]) => {
      const a = x0 + Math.min(...us) - 0.08, b = x0 + Math.max(...us) + D.P + 0.08, c = y0 + vs[0] - 0.08, d = y0 + vs[vs.length - 1] + D.P + 0.08;
      const dash = [], step = 0.3, L = 0.17, w = 0.024;
      for (let x = a + step / 2; x < b - 0.05; x += step) dash.push([x, c, L, w], [x, d, L, w]);
      for (let y = c + step / 2; y < d - 0.05; y += step) dash.push([a, y, w, L], [b, y, w, L]);
      const im = new THREE.InstancedMesh(G.box, mat, dash.length);
      dash.forEach(([x, y, sx, sz], k) => { o.position.copy(this.V(x, y, 0.082)); o.rotation.set(0, 0, 0); o.scale.set(sx, 0.004, sz); o.updateMatrix(); im.setMatrixAt(k, o.matrix); });
      g.add(im);
    });
    // the walk from the door, lit along both edges by studs in the floor
    const studs = [];
    for (let v = 2.25; v < 6.8; v += 0.5) studs.push([2.72, v], [4.28, v]);
    const st = new THREE.InstancedMesh(G.cyl, OM.vtStud, studs.length);
    studs.forEach(([u, v], k) => { o.position.copy(this.V(x0 + u, y0 + v, 0.083)); o.rotation.set(0, 0, 0); o.scale.set(0.024, 0.006, 0.024); o.updateMatrix(); st.setMatrixAt(k, o.matrix); });
    g.add(st);
    // two floodlights on the door wall, the right one turned on the door's face, the left one on the bars; their
    // light one cool white point in front of the door, on the +u side its open face looks to
    this.vtFlood(r, 5.75, [D.u + D.hu + 0.17, D.hv + 0.9, 0.72]);
    this.vtFlood(r, 1.3, [1.6, 3.2, 0.4]);
    const key = new THREE.PointLight(0xf2f8ff, 5, 5.2, 1.1); key.position.copy(this.V(x0 + 3.7, y0 + 2.2, 1.7)); g.add(key);
    this.vtLockers(r);
    this.vtShelf(r, 4.75, 6.75);
    this.vtDesk(r, x0 + 0.6, y0 + 5.3);
    this.vtCart(r);
    this.vtSafe(r, 5.38, 5.72, 0.72, 0.6, 0.82);
    this.vtSafe(r, 6.2, 5.92, 0.5, 0.46, 0.56);
    this.vtSorter(r, 5.45, 4.75);
    r.pileG = new THREE.Group(); g.add(r.pileG);
    this.plant(r, x0 + 0.38, y0 + 6.62, 0.8);
    this.plate(r, 'vaultp'); r.plateAt = this.V(x0 + 4.4, y0 + 5.65, 1.35);
  }
  // The money, rebuilt only when what it holds changes. ET10 is green bars, eighteen to a layer in crossed layers,
  // ten layers to a pallet, on the pallets left of the walk from the door; USDC is blue coins in sixteen stacks of
  // thirty to a pallet on the right. Both fill pallet by pallet, back to front, on a log scale: nothing at 0, a few
  // layers for a few hundred ET10, every pallet full near two million (a quarter of a million USDC). Once there is
  // a load, the cart in the walk carries the newest: nine bars, three short stacks. Shut for a visitor.
  piles(r, V, priv) {
    release(r.pileG); r.pileG.clear(); this.vaultPiles = [];
    if (r.doorPivot) r.doorPivot.rotation.y = priv ? 0 : r.vt.open;
    if (r.keyFace) r.keyFace.material = priv ? OM.vtKeyS : OM.vtKeyO;
    if (priv) return;
    const D = r.vt, x0 = r.x0, y0 = r.y0, P = D.P, o = new THREE.Object3D(), R = rng(5), pg = r.pileG, top = 0.2;
    const BP = 180, CP = 480, CB = 9, CC = 36, slots = (us, vs) => vs.flatMap((v) => us.map((u) => [u, v]));
    const fE = this.vtFill(V.et10, 200, 2e6), fU = this.vtFill(V.usdc, 0.5, 2.5e5);
    const nB = V.et10 > 0 ? Math.max(1, Math.round(fE * (6 * BP + CB))) : 0, nC = V.usdc > 0 ? Math.max(1, Math.round(fU * (6 * CP + CC))) : 0;
    const cB = nB >= 20 ? CB : 0, cC = nC >= 80 ? CC : 0;
    const zones = [[nB - cB, BP, slots(D.ue, D.re), OM.vtLipG, OM.vtPoolG, fE], [nC - cC, CP, slots(D.uu, D.ru), OM.vtLipB, OM.vtPoolB, fU]];
    // the pallets that hold something: a deck on three runners, a line of colour round the deck's edge
    const used = zones.map(([n, per, sl]) => sl.slice(0, Math.ceil(n / per)));
    const all = used[0].concat(used[1]), lipOf = used[0].map(() => 0).concat(used[1].map(() => 1));
    const put = (im, k, x, y, z, sx, sy, sz, ry = 0) => { o.position.copy(this.V(x, y, z)); o.rotation.set(0, ry, 0); o.scale.set(sx, sy, sz); o.updateMatrix(); im.setMatrixAt(k, o.matrix); };
    if (all.length) {
      const deck = new THREE.InstancedMesh(G.box, OM.vtPallet, all.length * 4), nl = [0, 0];
      const lips = [0, 1].map((z) => { const n = lipOf.filter((q) => q === z).length * 4; return n ? new THREE.InstancedMesh(G.box, zones[z][3], n) : null; });
      all.forEach(([u, v], i) => {
        const cx = x0 + u + P / 2, cy = y0 + v + P / 2;
        put(deck, i * 4, cx, cy, 0.18, P, 0.04, P);
        [-0.34, 0, 0.34].forEach((d, k) => put(deck, i * 4 + 1 + k, cx + d, cy, 0.12, 0.12, 0.08, P - 0.04));
        const L = lips[lipOf[i]], b = nl[lipOf[i]]; nl[lipOf[i]] += 4;
        put(L, b, cx, cy + P / 2, 0.18, P + 0.008, 0.016, 0.008); put(L, b + 1, cx, cy - P / 2, 0.18, P + 0.008, 0.016, 0.008);
        put(L, b + 2, cx + P / 2, cy, 0.18, 0.008, 0.016, P + 0.008); put(L, b + 3, cx - P / 2, cy, 0.18, 0.008, 0.016, P + 0.008);
      });
      deck.castShadow = true; deck.receiveShadow = true; pg.add(deck, ...lips.filter(Boolean));
    }
    const [cu, cv] = D.cart, deckTop = 0.355;
    // the bars: even layers lie along the room, odd ones across, a hair of disorder in every bar; then the cart's
    if (nB) {
      const im = new THREE.InstancedMesh(G.vtBar, OM.vtBar, nB), sl = zones[0][2], pb = nB - cB;
      for (let i = 0; i < pb; i++) {
        const [u, v] = sl[Math.floor(i / BP)], k = i % BP, l = Math.floor(k / 18), j = k % 18, even = l % 2 === 0;
        const a = even ? (j % 3 - 1) * 0.275 : (j % 6 - 2.5) * 0.135, b = even ? (Math.floor(j / 3) - 2.5) * 0.135 : (Math.floor(j / 6) - 1) * 0.275;
        put(im, i, x0 + u + P / 2 + a + (R() - 0.5) * 0.008, y0 + v + P / 2 + b + (R() - 0.5) * 0.008, top + l * 0.074 + 0.036, 0.26, 0.072, 0.12, (even ? 0 : Math.PI / 2) + (R() - 0.5) * 0.04);
      }
      for (let i = 0; i < cB; i++) {
        const l = i < 6 ? 0 : 1, j = i < 6 ? i : i - 6, du = l ? (j - 1) * 0.135 : (j % 3 - 1) * 0.135, dv = l ? 0 : (Math.floor(j / 3) - 0.5) * 0.275;
        put(im, pb + i, x0 + cu + du + (R() - 0.5) * 0.01, y0 + cv - 0.21 + dv, deckTop + l * 0.074 + 0.036, 0.26, 0.072, 0.12, Math.PI / 2 + (R() - 0.5) * 0.06);
      }
      im.castShadow = true; im.receiveShadow = true; pg.add(im);
    }
    // the coins: stack by stack, each stack a little off true; then the cart's three short stacks
    if (nC) {
      const im = new THREE.InstancedMesh(G.vtCoin, OM.vtCoin, nC), sl = zones[1][2], pc = nC - cC;
      let su = 0, sv = 0;
      for (let i = 0; i < pc; i++) {
        const [u, v] = sl[Math.floor(i / CP)], k = i % CP, s = Math.floor(k / 30), c = k % 30;
        if (c === 0) { su = (R() - 0.5) * 0.02; sv = (R() - 0.5) * 0.02; }
        put(im, i, x0 + u + P / 2 + (s % 4 - 1.5) * 0.2 + su + (R() - 0.5) * 0.006, y0 + v + P / 2 + (Math.floor(s / 4) - 1.5) * 0.2 + sv + (R() - 0.5) * 0.006, top + c * 0.0235 + 0.01, 0.088, 0.02, 0.088, R() * 6.28);
      }
      for (let i = 0; i < cC; i++) put(im, pc + i, x0 + cu + (Math.floor(i / 12) - 1) * 0.19 + (R() - 0.5) * 0.006, y0 + cv + 0.27 + (R() - 0.5) * 0.006, deckTop + (i % 12) * 0.0235 + 0.01, 0.084, 0.02, 0.084, R() * 6.28);
      // they take shadows but cast none: at their size the shadow pass would draw thousands for a few pixels
      im.receiveShadow = true; pg.add(im);
    }
    // a soft pool of each colour on the floor under what it holds, as his trading desk's light lies on its floor
    // (a coloured lamp over the piles blew their tops out white once they filled)
    zones.forEach(([n, per, sl, lip, pool, f], z) => {
      if (n <= 0) return;
      const us = used[z], u0 = Math.min(...us.map((q) => q[0])), u1 = Math.max(...us.map((q) => q[0])) + P, v0 = Math.min(...us.map((q) => q[1])), v1 = Math.max(...us.map((q) => q[1])) + P;
      pool.opacity = 0.16 + 0.2 * f;
      const m = new THREE.Mesh(G.plane, pool); m.rotation.x = -Math.PI / 2; m.scale.set(u1 - u0 + 1.4, v1 - v0 + 1.4, 1); m.position.copy(this.V(x0 + (u0 + u1) / 2, y0 + (v0 + v1) / 2, 0.087)); pg.add(m);
    });
  }
  // how far a pile fills: nothing at 0, then by orders of magnitude, eased so a few hundred is a little and the
  // pile is whole only near `full`
  vtFill(amt, a0, full) { return amt > 0 ? Math.min(1, Math.pow(Math.log10(1 + amt / a0) / Math.log10(1 + full / a0), 1.4)) : 0; }
  // the vault's materials, textures and shapes, made once and shared (release() keeps what lives on OM, TX and G)
  vtMats(D) {
    if (OM.vtSteel) return;
    const R = rng(61);
    // brushed steel: fine streaks one way (round the door on its lathe, along a wall on the flat)
    const brush = TX.vtBrush = ctex(256, 256, (g, W, H) => {
      g.fillStyle = '#b4bec9'; g.fillRect(0, 0, W, H);
      for (let y = 0; y < H; y++) { const v = 150 + Math.floor((R() - 0.5) * 50); g.fillStyle = 'rgba(' + v + ',' + (v + 8) + ',' + (v + 18) + ',' + (0.2 + R() * 0.4).toFixed(2) + ')'; g.fillRect(0, y, W, 1); }
    });
    brush.wrapS = brush.wrapT = THREE.RepeatWrapping;
    // the armour, one wall's face from the foot to the top: a dark lower band and lighter plates above, six plates a
    // band (the lower ones half a plate along, as brickwork), each bevelled, brushed, a shade apart; the groove of
    // the lit seam between the bands (the rivets are geometry, vtRivets())
    TX.vtArmour = ctex(2048, 430, (g, W, H) => {
      const hy = (h) => H * (1 - (h - D.wb) / (D.top - D.wb)), ys = hy(D.seam + 0.02), yl = hy(D.seam - 0.02);
      const plate = (x, y, w, h, base) => {
        const v = Math.floor((R() - 0.5) * 14), c = base.map((q) => q + v);
        g.fillStyle = 'rgb(' + c.join(',') + ')'; g.fillRect(x, y, w, h);
        for (let k = 0; k < h; k += 2) { g.fillStyle = 'rgba(255,255,255,' + (R() * 0.05).toFixed(3) + ')'; g.fillRect(x, y + k, w, 1); }
        g.fillStyle = 'rgba(255,255,255,.28)'; g.fillRect(x + 3, y + 3, w - 6, 2); g.fillRect(x + 3, y + 3, 2, h - 6);
        g.fillStyle = 'rgba(8,14,22,.7)'; g.fillRect(x + 3, y + h - 5, w - 6, 2); g.fillRect(x + w - 5, y + 3, 2, h - 6);
      };
      g.fillStyle = '#10161e'; g.fillRect(0, 0, W, H);
      for (let k = 0; k < 6; k++) plate(k * W / 6, 0, W / 6, ys, [112, 124, 138]);
      for (let k = -1; k < 6; k++) plate((k + 0.5) * W / 6, yl, W / 6, H - yl, [48, 58, 71]);
      g.fillStyle = '#0a0f15'; g.fillRect(0, ys, W, yl - ys);
    });
    // the door's face, turned on a lathe: rings of polish, engraved circles
    TX.vtFace = ctex(512, 512, (g, W) => {
      const c = W / 2;
      for (let rr = c; rr > 0; rr -= 1.4) { const v = 140 + Math.floor((R() - 0.5) * 36) + Math.floor(rr / c * 22); g.strokeStyle = 'rgb(' + v + ',' + (v + 8) + ',' + (v + 17) + ')'; g.lineWidth = 2; g.beginPath(); g.arc(c, c, rr, 0, Math.PI * 2); g.stroke(); }
      [[0.97, 4], [0.86, 2.5], [0.36, 3]].forEach(([k, w]) => { g.strokeStyle = 'rgba(22,30,40,.75)'; g.lineWidth = w; g.beginPath(); g.arc(c, c, c * k, 0, Math.PI * 2); g.stroke(); });
    });
    TX.vtDial = ctex(128, 128, (g, W) => {
      const c = W / 2; g.fillStyle = '#141c26'; g.beginPath(); g.arc(c, c, c, 0, 7); g.fill();
      for (let k = 0; k < 60; k++) { const a = k / 60 * Math.PI * 2, l = k % 5 ? 8 : 16; g.strokeStyle = k % 5 ? '#8a98a8' : '#e6edf4'; g.lineWidth = k % 5 ? 2 : 3; g.beginPath(); g.moveTo(c + Math.sin(a) * (c - 4), c - Math.cos(a) * (c - 4)); g.lineTo(c + Math.sin(a) * (c - 4 - l), c - Math.cos(a) * (c - 4 - l)); g.stroke(); }
      g.fillStyle = '#7cf2c4'; g.beginPath(); g.moveTo(c, 6); g.lineTo(c - 7, 22); g.lineTo(c + 7, 22); g.fill();
      g.fillStyle = '#3a4756'; g.beginPath(); g.arc(c, c, c * 0.42, 0, 7); g.fill();
    });
    // the keypad: its screen (OPEN in mint, LOCKED in cyan) over twelve keys
    const pad = (word, col, bg) => ctex(128, 180, (g, W, H) => {
      g.fillStyle = '#0c141c'; g.fillRect(0, 0, W, H); g.strokeStyle = '#2c3b4a'; g.lineWidth = 4; g.strokeRect(2, 2, W - 4, H - 4);
      g.fillStyle = bg; g.fillRect(12, 12, W - 24, 40); g.fillStyle = col; g.font = '700 22px JetBrains Mono, monospace'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText(word, W / 2, 33);
      for (let i = 0; i < 12; i++) { const x = 14 + (i % 3) * 36, y = 64 + Math.floor(i / 3) * 28; g.fillStyle = '#3d4b5a'; g.fillRect(x, y, 28, 21); g.fillStyle = '#5a6a7a'; g.fillRect(x, y, 28, 3); g.fillStyle = '#c4ced8'; g.font = '600 12px JetBrains Mono, monospace'; g.fillText('123456789*0#'[i], x + 14, y + 12); }
    });
    TX.vtKeyO = pad('OPEN', '#7cf2c4', '#06231c'); TX.vtKeyS = pad('LOCKED', '#24e8ff', '#062030');
    // the counting table's screen: what came in, in the two colours, by day
    TX.vtLedger = ctex(320, 180, (g, W, H) => {
      g.fillStyle = '#06101a'; g.fillRect(0, 0, W, H); g.strokeStyle = '#38f5b8'; g.lineWidth = 5; g.strokeRect(3, 3, W - 6, H - 6);
      g.fillStyle = '#38f5b8'; g.font = '700 22px JetBrains Mono, monospace'; g.textBaseline = 'top'; g.fillText('VAULT', 16, 12);
      g.fillStyle = '#142436'; for (let y = 60; y < H - 14; y += 24) g.fillRect(16, y, W - 32, 2);
      for (let i = 0; i < 12; i++) { const h1 = 20 + R() * 70, h2 = 8 + R() * 30, x = 22 + i * 24; g.fillStyle = '#38f5b8'; g.fillRect(x, H - 18 - h1, 9, h1); g.fillStyle = '#3b82f6'; g.fillRect(x + 10, H - 18 - h2, 9, h2); }
    });
    // safe-deposit lockers: rows of steel doors, small at the top, larger below, each with a number plate, a keyhole
    // and a light (the glow map carries only the lights)
    const rowsB = [[52, 30], [52, 30], [52, 30], [74, 20], [100, 14]], W2 = 2400, H2 = 372, lights = [];
    TX.vtBoxes = ctex(W2, H2, (g) => {
      g.fillStyle = '#2a3440'; g.fillRect(0, 0, W2, H2);
      let y = 8;
      rowsB.forEach(([h, n]) => {
        const w = (W2 - 16 - (n - 1) * 6) / n;
        for (let i = 0; i < n; i++) {
          const x = 8 + i * (w + 6), v = Math.floor((R() - 0.5) * 16), gr = g.createLinearGradient(x, y, x, y + h);
          gr.addColorStop(0, 'rgb(' + (156 + v) + ',' + (166 + v) + ',' + (178 + v) + ')'); gr.addColorStop(1, 'rgb(' + (112 + v) + ',' + (122 + v) + ',' + (134 + v) + ')');
          g.fillStyle = gr; g.fillRect(x, y, w, h); g.strokeStyle = 'rgba(30,40,52,.55)'; g.lineWidth = 2; g.strokeRect(x + 4, y + 4, w - 8, h - 8);
          g.fillStyle = '#dfe6ee'; g.fillRect(x + 9, y + 9, Math.min(26, w * 0.4), 11);
          g.fillStyle = '#1a222c'; g.beginPath(); g.arc(x + w - 16, y + h / 2 + 2, 4, 0, 7); g.fill(); g.fillRect(x + w - 17, y + h / 2 + 2, 2, 8);
          lights.push([x + w - 12, y + 12, R() < 0.82 ? '#7cf2c4' : '#3b82f6']);
        }
        y += h + 6;
      });
    });
    TX.vtBoxesGlow = ctex(W2, H2, (g) => { g.fillStyle = '#000'; g.fillRect(0, 0, W2, H2); lights.forEach(([x, y, c]) => { g.fillStyle = c; g.fillRect(x - 4, y - 3, 8, 6); }); });
    // steel as his engines and consoles read under the studio light: pale and only half a mirror (a full metal
    // reflects the dark sky and goes black); the door paler than the armour round it, so it stands out of the wall
    OM.vtSteel = std({ color: 0xd2dbe4, map: brush, metalness: 0.55, roughness: 0.34 });
    OM.vtArmour = std({ map: TX.vtArmour, metalness: 0.5, roughness: 0.42 });
    OM.vtSteelDk = std({ color: 0x4e5b69, metalness: 0.6, roughness: 0.42 });
    OM.vtChrome = std({ color: 0xe8eff6, metalness: 0.85, roughness: 0.2 });
    OM.vtSafe = std({ color: 0x2c3846, metalness: 0.6, roughness: 0.36 });
    OM.vtFace = std({ map: TX.vtFace, color: 0xeef3f8, metalness: 0.55, roughness: 0.3 });
    OM.vtDial = new THREE.MeshBasicMaterial({ map: TX.vtDial });
    OM.vtNeon = emis(LOOK.neon, 2.4);
    OM.vtSeam = emis(LOOK.neon, 2.0);
    OM.vtStud = emis(LOOK.neon, 1.1);
    OM.vtRivet = std({ color: 0x8b97a5, metalness: 0.7, roughness: 0.36 });
    OM.vtFlood = new THREE.MeshBasicMaterial({ color: new THREE.Color(0xf4f9ff).multiplyScalar(3) });
    OM.vtKeyO = new THREE.MeshBasicMaterial({ map: TX.vtKeyO, toneMapped: false });
    OM.vtKeyS = new THREE.MeshBasicMaterial({ map: TX.vtKeyS, toneMapped: false });
    OM.vtLedger = new THREE.MeshBasicMaterial({ map: TX.vtLedger, toneMapped: false });
    OM.vtBoxes = std({ map: TX.vtBoxes, emissiveMap: TX.vtBoxesGlow, emissive: 0xffffff, emissiveIntensity: 1.6, metalness: 0.6, roughness: 0.38 });
    // the money: Cymetica's green and USDC's blue, as satin metal that holds its colour under the white light (a
    // glossier finish mirrored the room's lamp off the coins' flat tops into a white blot once the floor filled)
    OM.vtBar = std({ color: 0x2ee59a, metalness: 0.62, roughness: 0.4, emissive: 0x0d7a4e, emissiveIntensity: 0.5 });
    OM.vtCoin = std({ color: 0x5a96fa, metalness: 0.55, roughness: 0.46, emissive: 0x1d4fb8, emissiveIntensity: 0.5 });
    OM.vtPallet = std({ color: 0x1e2a36, roughness: 0.46, metalness: 0.42 });
    OM.vtLipG = emis('#38f5b8', 1.6); OM.vtLipB = emis('#3b82f6', 2.0);
    OM.vtBayG = emis('#7cf2c4', 0.3); OM.vtBayB = emis('#3b82f6', 0.5);
    TX.vtPool = radialTex('255,255,255', 0.9);
    const pool = (hex) => new THREE.MeshBasicMaterial({ map: TX.vtPool, color: hex, transparent: true, opacity: 0.2, blending: THREE.AdditiveBlending, depthWrite: false });
    OM.vtPoolG = pool(0x38f5b8); OM.vtPoolB = pool(0x3b82f6);
    // the leaf turned on a lathe, back to front (so every face looks out): the back, three steps of the plug that
    // seats in the frame, the front lip, a raised rim round the face; the collar round the opening the same way
    G.vtLeaf = this.vtLathe([[0, -0.23], [0.525, -0.23], [0.525, -0.09], [0.556, -0.09], [0.556, 0.09], [0.59, 0.09], [0.59, 0.2], [0.57, 0.23], [0.54, 0.23], [0.54, 0.252], [0.515, 0.252], [0.503, 0.23]], 96);
    G.vtCollar = this.vtLathe([[0.69, 0.18], [0.69, 0.27], [0.672, 0.3], [0.64, 0.3], [0.615, 0.285], [0.615, 0.18]], 96);
    G.vtFace = new THREE.CircleGeometry(0.505, 72);
    G.vtDial = new THREE.CircleGeometry(0.062, 40);
    G.vtRivet = new THREE.SphereGeometry(1, 8, 4, 0, Math.PI * 2, 0, Math.PI / 2);
    // an ingot: a box whose top is drawn in, as cast bars are
    const bar = new THREE.BoxGeometry(1, 1, 1), bp = bar.attributes.position;
    for (let i = 0; i < bp.count; i++) if (bp.getY(i) > 0) bp.setXYZ(i, bp.getX(i) * 0.8, bp.getY(i), bp.getZ(i) * 0.68);
    bar.computeVertexNormals(); G.vtBar = bar;
    // a coin: twelve sides and its top (its bottom always lies on another coin or a deck, so it has none): round
    // enough at a close-up, cheap by the thousand
    const side = new THREE.CylinderGeometry(1, 1, 1, 12, 1, true), cap = new THREE.CircleGeometry(1, 12);
    cap.rotateX(-Math.PI / 2); cap.translate(0, 0.5, 0);
    G.vtCoin = mergeGeometries([side, cap], false); side.dispose(); cap.dispose();
  }
  // a lathe whose every corner is crisp (each inner point doubled, so no normal is averaged across a step), its axis
  // turned to z
  vtLathe(pts, n) {
    const p = [];
    pts.forEach(([x, y], i) => { p.push(new THREE.Vector2(x, y)); if (i > 0 && i < pts.length - 1) p.push(new THREE.Vector2(x, y)); });
    const g = new THREE.LatheGeometry(p, n); g.rotateX(Math.PI / 2); return g;
  }
  // an armoured wall: a slab 0.3 thick along the wall from its inner corner to the front glass, from under the
  // floor's top to D.top, its outline drawn in by the bevel (which grows the body back out to it); the door wall
  // ('y') with the opening cut through it. The armour's texture laid flat along it.
  vtWallGeo(kind, D) {
    const key = 'vtWall' + kind; if (G[key]) return G[key];
    const b = 0.012, a0 = (kind === 'y' ? D.WT : D.WO) + b, a1 = CO.iso.RS - 0.02 - b, yb = D.wb + b, yt = D.top - b, s = new THREE.Shape();
    s.moveTo(a0, yb); s.lineTo(a1, yb); s.lineTo(a1, yt); s.lineTo(a0, yt); s.lineTo(a0, yb);
    if (kind === 'y') { const h = new THREE.Path(); h.absarc(D.u, D.ch, D.hole + b, 0, Math.PI * 2, true); s.holes.push(h); }
    const geo = new THREE.ExtrudeGeometry(s, { depth: D.WT - D.WO - 2 * b, bevelEnabled: true, bevelThickness: b, bevelSize: b, bevelSegments: 1, curveSegments: 80 });
    const p = geo.attributes.position, uv = geo.attributes.uv;
    for (let i = 0; i < p.count; i++) uv.setXY(i, (p.getX(i) - a0) / (a1 - a0), (p.getY(i) - yb) / (yt - yb));
    return (G[key] = geo);
  }
  // rivets along both armoured walls: rows at the top, either side of the lit seam and at the foot, and up each
  // plate's seam -- none where the collar, the keypad or the lockers stand
  vtRivets(r) {
    const D = r.vt, RS = CO.iso.RS, x0 = r.x0, y0 = r.y0, pts = [];
    const walls = [['y', D.WT, RS - 0.02], ['x', D.WO, RS - 0.02]];
    walls.forEach(([w, a0, a1]) => {
      const L = a1 - a0, free = (a, h) => w === 'y'
        ? Math.hypot(a - D.u, h - D.ch) > D.collar + 0.07 && !(Math.abs(a - D.u - 0.97) < 0.18 && h > 0.6 && h < 1.06)
        : !(a > 0.6 && a < 4.8 && h > 0.6);
      const at = (a, h) => { if (a > D.WT + 0.05 && a < a1 - 0.05 && free(a, h)) pts.push([w, a, h]); };
      [1.33, D.seam + 0.07, D.seam - 0.07, 0.14].forEach((h) => { for (let a = a0 + 0.12; a < a1; a += 0.2) at(a, h); });
      for (let k = 1; k < 6; k++) [-0.05, 0.05].forEach((d) => {
        for (let h = 0.8; h < 1.27; h += 0.14) at(a0 + k * L / 6 + d, h);
        for (let h = 0.24; h < 0.5; h += 0.12) at(a0 + (k + 0.5) * L / 6 + d, h);
      });
    });
    const im = new THREE.InstancedMesh(G.vtRivet, OM.vtRivet, pts.length), o = new THREE.Object3D();
    pts.forEach(([w, a, h], k) => {
      if (w === 'y') { o.position.copy(this.V(x0 + a, y0 + D.WT, h)); o.rotation.set(Math.PI / 2, 0, 0); }
      else { o.position.copy(this.V(x0 + D.WT, y0 + a, h)); o.rotation.set(0, 0, -Math.PI / 2); }
      o.scale.set(0.022, 0.012, 0.022); o.updateMatrix(); im.setMatrixAt(k, o.matrix);
    });
    r.g.add(im);
  }
  // a floodlight on the door wall at u: a bracket, a housing turned down at `aim` (u, v, height), its white face, a
  // halo. Its light is vaultRoom()'s one point light: a spot light would be the scene's first and put a new light
  // type into every lit material in the office (switching one recompiles them all; measured 2026-10-19)
  vtFlood(r, u, aim) {
    const D = r.vt, g = r.g, x0 = r.x0, y0 = r.y0, h = 1.2, at = this.V(x0 + u, y0 + D.WT + 0.17, h), to = this.V(x0 + aim[0], y0 + aim[1], aim[2]);
    this.box(g, x0 + u - 0.04, y0 + D.WT, h - 0.06, 0.08, 0.17, 0.05, OM.vtSteelDk);
    const head = new THREE.Group(); head.position.copy(at); head.lookAt(to); g.add(head);
    const hs = new THREE.Mesh(rboxGeo(0.36, 0.14, 0.15, 0.025), OM.vtSteelDk); hs.castShadow = true; head.add(hs);
    const face = new THREE.Mesh(G.plane, OM.vtFlood); face.scale.set(0.3, 0.1, 1); face.position.z = 0.077; head.add(face);
    const halo = glowSprite(0xeef6ff, 0.3, 0.45); halo.position.copy(at).lerp(to, 0.06); g.add(halo);
  }
  // safe-deposit lockers built into the side wall's upper band (x = x0), framed in steel
  vtLockers(r) {
    const D = r.vt, g = r.g, x0 = r.x0, y0 = r.y0;
    const m = new THREE.Mesh(G.box, [OM.vtBoxes, OM.vtSteelDk, OM.vtSteelDk, OM.vtSteelDk, OM.vtSteelDk, OM.vtSteelDk]);
    m.scale.set(0.08, 0.62, 4.0); m.position.copy(this.V(x0 + D.WT + 0.04, y0 + 2.7, 0.98)); m.receiveShadow = true; g.add(m);
    this.rb(g, x0 + D.WT, y0 + 0.66, 1.29, 0.11, 4.08, 0.04, OM.vtSteel, 0.012);
    this.rb(g, x0 + D.WT, y0 + 0.66, 0.64, 0.11, 4.08, 0.03, OM.vtSteel, 0.01);
  }
  // a steel shelf against the door wall from u0 to u1, strongboxes on its two lower boards with chrome handles and
  // a light each (the top board stays bare, clear of the floodlight over it)
  vtShelf(r, u0, u1) {
    const D = r.vt, g = r.g, x0 = r.x0, y0 = r.y0, d = 0.42, v0 = D.WT + 0.02;
    [u0, u1 - 0.04].forEach((u) => [v0, v0 + d - 0.04].forEach((v) => this.box(g, x0 + u, y0 + v, 0.08, 0.04, 0.04, 0.82, OM.vtSteelDk)));
    [0.12, 0.48, 0.84].forEach((h) => this.rb(g, x0 + u0 - 0.01, y0 + v0, h, u1 - u0 + 0.02, d, 0.03, OM.vtSteel, 0.01));
    const R = rng(23);
    [[0.15, 3], [0.51, 4]].forEach(([h, n]) => {
      const w = (u1 - u0 - 0.1) / n;
      for (let k = 0; k < n; k++) {
        if (R() < 0.18) continue;
        const bx = x0 + u0 + 0.05 + k * w + 0.03, bw = w - 0.06, bh = 0.18 + R() * 0.08;
        this.rb(g, bx, y0 + v0 + 0.05, h, bw, 0.3, bh, OM.vtSafe, 0.02);
        this.box(g, bx + bw * 0.3, y0 + v0 + 0.35, h + bh * 0.55, bw * 0.4, 0.02, 0.025, OM.vtChrome, false);
        const l = new THREE.Mesh(G.box, OM.green.glow); l.scale.set(0.025, 0.015, 0.01); l.position.copy(this.V(bx + bw - 0.05, y0 + v0 + 0.355, h + bh - 0.04)); g.add(l);
      }
    });
  }
  // the counting table at (x, y): a desk, a counting machine with its green readout, a screen of what came in, a
  // lamp on an arm with its light on the desk
  vtDesk(r, x, y) {
    const g = r.g;
    this.rb(g, x + 0.05, y + 0.04, 0.08, 0.1, 0.72, 0.42, OM.desk, 0.03);
    this.rb(g, x + 1.55, y + 0.04, 0.08, 0.1, 0.72, 0.42, OM.desk, 0.03);
    this.box(g, x + 0.15, y + 0.06, 0.12, 1.4, 0.04, 0.34, OM.desk);
    this.rb(g, x, y, 0.5, 1.7, 0.8, 0.05, OM.deskTop, 0.02);
    this.cyl(g, x + 1.0, y + 0.2, 0.55, 0.11, 0.02, OM.frame); this.box(g, x + 0.97, y + 0.12, 0.57, 0.06, 0.05, 0.12, OM.frame, false);
    this.rb(g, x + 0.65, y + 0.1, 0.66, 0.7, 0.05, 0.42, OM.dark, 0.02);
    const sc = new THREE.Mesh(G.plane, OM.vtLedger); sc.scale.set(0.64, 0.36, 1); sc.position.copy(this.V(x + 1.0, y + 0.152, 0.87)); g.add(sc);
    this.rb(g, x + 0.1, y + 0.3, 0.55, 0.42, 0.36, 0.18, OM.white, 0.04);
    this.box(g, x + 0.17, y + 0.38, 0.72, 0.28, 0.1, 0.02, OM.dark, false);
    const rd = new THREE.Mesh(G.plane, OM.green.soft); rd.scale.set(0.22, 0.05, 1); rd.position.copy(this.V(x + 0.31, y + 0.662, 0.64)); g.add(rd);
    this.cyl(g, x + 1.52, y + 0.62, 0.55, 0.07, 0.025, OM.dark);
    this.box(g, x + 1.505, y + 0.605, 0.57, 0.03, 0.03, 0.42, OM.frame, false);
    this.box(g, x + 1.3, y + 0.605, 0.97, 0.24, 0.03, 0.03, OM.frame, false);
    this.cyl(g, x + 1.3, y + 0.62, 0.9, 0.065, 0.07, OM.dark);
    const lf = new THREE.Mesh(G.circle, OM.vtFlood); lf.scale.setScalar(0.05); lf.rotation.x = Math.PI / 2; lf.position.copy(this.V(x + 1.3, y + 0.62, 0.895)); g.add(lf);
    const halo = glowSprite(0xf4f9ff, 0.22, 0.6); halo.position.copy(this.V(x + 1.3, y + 0.62, 0.86)); g.add(halo);
  }
  // the cart in the walk: a deck and a shelf under it on four legs and casters, a handle at its front end; what it
  // carries is piles()'
  vtCart(r) {
    const D = r.vt, g = r.g, x = r.x0 + D.cart[0], y = r.y0 + D.cart[1], w = 0.62, l = 0.98;
    this.rb(g, x - w / 2, y - l / 2, 0.3, w, l, 0.05, OM.vtSteelDk, 0.015);
    this.rb(g, x - w / 2 + 0.03, y - l / 2 + 0.03, 0.15, w - 0.06, l - 0.06, 0.025, OM.vtSteelDk, 0.01);
    this.box(g, x - w / 2, y + l / 2 - 0.004, 0.33, w, 0.008, 0.012, OM.vtLipG, false);
    this.box(g, x + w / 2 - 0.004, y - l / 2, 0.33, 0.008, l, 0.012, OM.vtLipG, false);
    [[-1, -1], [1, -1], [-1, 1], [1, 1]].forEach(([sx, sy]) => {
      const cx = x + sx * (w / 2 - 0.05), cy = y + sy * (l / 2 - 0.06);
      this.cyl(g, cx, cy, 0.17, 0.018, 0.13, OM.vtChrome);
      const wh = this.part(g, G.cyl8, OM.dark, 0.05, 0.035, 0.05, cx, 0.13, cy); wh.rotation.z = Math.PI / 2;
    });
    [-1, 1].forEach((sx) => this.cyl(g, x + sx * (w / 2 - 0.04), y + l / 2 - 0.03, 0.35, 0.016, 0.52, OM.vtChrome));
    const bar = this.part(g, G.cyl, OM.vtChrome, 0.02, w - 0.08, 0.02, x, 0.87, y + l / 2 - 0.03); bar.rotation.z = Math.PI / 2;
  }
  // a coin sorter standing on the floor at (u, v), its front to the room's front: a white cabinet, a dark hopper on
  // top, a green readout, three chrome trays where the sorted coins come out
  vtSorter(r, u, v) {
    const g = r.g, x = r.x0 + u, y = r.y0 + v, w = 0.52, d = 0.4, h = 0.74;
    this.rb(g, x, y, 0.08, w, d, h, OM.white, 0.05);
    this.rb(g, x + 0.08, y + 0.06, 0.08 + h - 0.01, w - 0.16, d - 0.12, 0.12, OM.dark, 0.03);
    this.box(g, x + 0.1, y + d - 0.02, 0.08 + h - 0.2, w - 0.2, 0.03, 0.1, OM.dark, false);
    const rd = new THREE.Mesh(G.plane, OM.green.soft); rd.scale.set(w - 0.26, 0.06, 1); rd.position.copy(this.V(x + w / 2, y + d + 0.012, 0.08 + h - 0.15)); g.add(rd);
    for (let k = 0; k < 3; k++) this.rb(g, x + 0.06 + k * (w - 0.12) / 3, y + d - 0.04, 0.3, (w - 0.12) / 3 - 0.03, 0.14, 0.05, OM.vtChrome, 0.012);
    const l = new THREE.Mesh(G.box, OM.blue.glow); l.scale.set(0.03, 0.018, 0.01); l.position.copy(this.V(x + w - 0.08, y + d + 0.012, 0.08 + h - 0.08)); g.add(l);
  }
  // a free-standing safe at (u, v), its door to the room's front: a dark steel body on four feet, the door inset,
  // a chrome dial and handle, its hinge, a light
  vtSafe(r, u, v, w, d, h) {
    const g = r.g, x = r.x0 + u, y = r.y0 + v;
    [[0.06, 0.06], [w - 0.1, 0.06], [0.06, d - 0.1], [w - 0.1, d - 0.1]].forEach(([dx, dy]) => this.box(g, x + dx, y + dy, 0.08, 0.04, 0.04, 0.04, OM.dark));
    this.rb(g, x, y, 0.12, w, d, h - 0.04, OM.vtSafe, 0.04);
    this.rb(g, x + 0.06, y + d - 0.02, 0.18, w - 0.12, 0.04, h - 0.16, OM.vtSteelDk, 0.02);
    const dz = 0.12 + (h - 0.04) * 0.62, dial = this.part(g, G.cyl, OM.vtChrome, 0.065 * w / 0.72, 0.03, 0.065 * w / 0.72, x + w * 0.42, dz, y + d + 0.03); dial.rotation.x = Math.PI / 2;
    for (let k = 0; k < 3; k++) this.part(g, G.cyl, OM.vtChrome, 0.01, 0.12 * w / 0.72, 0.01, x + w * 0.42, dz - 0.16 * h / 0.82, y + d + 0.04).rotation.z = k * Math.PI / 3;
    this.box(g, x + w - 0.1, y + d + 0.01, 0.24, 0.025, 0.03, h - 0.3, OM.vtChrome, false);
    const l = new THREE.Mesh(G.box, OM.green.glow); l.scale.set(0.03, 0.018, 0.01); l.position.copy(this.V(x + w * 0.42, y + d + 0.024, dz + 0.1)); g.add(l);
  }
  // the free lot: open dark-teal deck marked out with glowing cyan-mint dashes, a crisp turquoise-aquamarine holographic pad
  // with a vertical grid cylinder and perimeter nodes; the label lies inside the ring
  lotRoom(r) {
    const RS = CO.iso.RS, g = r.g, c = this.V(r.x0 + RS / 2, r.y0 + RS / 2, 0.05), ins = 0.35;
    if (!G.lotDash) { G.lotDash = dashedRing(44, 0.55, 0.02); G.lotDashFine = dashedRing(70, 0.5, 0.006); G.ringThin = new THREE.TorusGeometry(1, 0.006, 6, 180); }
    this.box(g, r.x0, r.y0, 0, RS, RS, 0.05, OM.deck);
    for (let a = ins; a < RS - ins - 0.2; a += 0.72) {
      const w = Math.min(0.42, RS - ins - a);
      [[r.x0 + a, r.y0 + ins], [r.x0 + a, r.y0 + RS - ins]].forEach(([x, y]) => this.box(g, x, y - 0.035, 0.05, w, 0.07, 0.025, OM.dash, false));
      [[r.x0 + ins, r.y0 + a], [r.x0 + RS - ins, r.y0 + a]].forEach(([x, y]) => this.box(g, x - 0.035, y, 0.05, 0.07, w, 0.025, OM.dash, false));
    }
    const pad = new THREE.Mesh(G.plane, new THREE.MeshBasicMaterial({ map: padTex(), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
    pad.scale.set(5.0, 5.0, 1); pad.rotation.x = -Math.PI / 2; pad.position.set(c.x, 0.07, c.z); g.add(pad);
    // his pad, zoomed: a speckled wall of teal light with a bright line along its top; inside it, on the floor, a
    // ring of thick white dashes and a thin bright teal circle; outside, one thin dashed circle in cyan. (His further
    // cyan circle reached past the square of lane dashes round the lot, so it went, and the white one took its
    // colour: "to kolecko carkovane modre precniva prez ctverecek ... to co je ted bile udelej modre".)
    const ring = (geo, mat, rad, y, flat) => { const m = new THREE.Mesh(geo, mat); m.scale.set(rad, rad, flat || rad); m.rotation.x = Math.PI / 2; m.position.set(c.x, y, c.z); g.add(m); return m; };
    const wall = new THREE.Mesh(G.pole, new THREE.MeshBasicMaterial({ map: gridTex(), color: new THREE.Color(0x3ad8c4).multiplyScalar(0.8), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
    wall.scale.set(2.38, 0.46, 2.38); wall.position.set(c.x, 0.3, c.z); g.add(wall);
    ring(G.ringThin, OM.lotRim, 2.38, 0.53);
    ring(G.ringThin, OM.lotRim, 1.92, 0.07);
    r.plus = ring(G.lotDash, OM.dash, 2.16, 0.07, 0.25);
    ring(G.lotDashFine, OM.lotCyan, 2.95, 0.06);
    const hit = new THREE.Mesh(G.box, M.hit); hit.scale.set(RS, 1.6, RS); hit.position.set(c.x, 0.8, c.z); hit.userData.key = 'lot'; g.add(hit); this.hits.push(hit);
    const el = document.createElement('div'); el.className = 'p3lot'; el.innerHTML = '<b>+</b>ADD DEPARTMENT'; el.addEventListener('click', () => CO.emit('office:click', 'lot')); this.layer.appendChild(el);
    r.plate = el; r.plateAt = new THREE.Vector3(c.x, 0.18, c.z);   // the label lies inside its ring
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
      const isOrange = d.key === 'trading_desk';
      if (v.status === 'working') anyWork = true;
      this.tint(r, st);
      const dot = isOrange && st !== 'working' ? '#ff8824' : '#' + new THREE.Color(STC[st]).getHexString();
      let title, sub, mode, col = isOrange && st !== 'working' ? '#ff9438' : st === 'queued' ? '#a9b8cc' : dot;
      if (v.running) { title = v.running.title; sub = CO.expertName(v.running.expert) + ' is on it'; mode = 'run'; }
      else if (v.waiting) { title = 'Needs you'; sub = 'approve or reject on the right'; mode = 'full'; col = '#ff8824'; }
      else if (v.queued.length) { title = 'Up next: ' + v.queued[0].title; sub = ''; mode = isOrange ? 'full' : ''; }
      else { title = d.schedule && d.next_run ? 'Next run at ' + CO.hhmm(d.next_run) : 'Idle'; sub = ''; mode = isOrange ? 'full' : ''; }
      if (r.wall) drawWall(r.wall, title, sub, col, mode);
      if (r.kb) drawKanban(r.kb, { queued: v.queued.length, running: v.running ? 1 : 0, done: v.done, failed: v.failed });
      v.experts.slice(0, 3).forEach((e, i) => {
        const a = r.agents[i]; if (a) a.working = e.state === 'working';
        // his desks' monitors are dark glass; a screen lights while its expert works (the trading desk's charts always)
        if (r.mons[i]) r.mons[i].color.set(isOrange ? new THREE.Color(0xffae52).multiplyScalar(1.25) : e.state === 'working' ? new THREE.Color(0x7cf2c4).multiplyScalar(1.3) : new THREE.Color(0x0a1016));
      });
      const n = d.et10 || 0, et = d.files_as ? '<span class="et' + (n ? ' lit' : '') + '">' + (n ? '+' : '') + n.toLocaleString('en-US') + ' ET10</span>' : '';
      const subCol = isOrange && ln.tone !== 'cyan' ? '#ff9438' : (TONEC[ln.tone] || '#a9b8cc');
      const html = '<div class="p3h"><i style="background:' + (ln.tone === 'red' || isOrange ? '#ff8824' : dot) + '"></i><b>' + esc(d.name.toUpperCase()) + '</b>' + et + '</div><div class="p3l" style="color:' + subCol + '">' + esc(ln.short) + '</div>';
      if (r.plate && r.plate._h !== html) { r.plate._h = html; r.plate.innerHTML = html; }
      if (r.plate) { r.plate.classList.toggle('work', v.status === 'working'); r.plate.style.setProperty('--c', ln.tone === 'red' || isOrange ? '#ff8824' : col); }
      // the deck's lanes are his dim white dashes; one lights cyan while work runs along it
      if (this.conduits['d' + d.id]) { const cm = this.conduits['d' + d.id].mat; cm.emissive.set(v.status === 'working' ? 0x46d8f0 : 0xb4c4d0); cm.emissiveIntensity = v.status === 'working' ? 0.75 : 0.3; }
    });
    const hub = this.rooms.hub;
    if (hub) {
      const paused = S.company.status === 'paused';
      this.tint(hub, paused ? 'idle' : 'working');
      if (hub.bars) drawBars(hub.bars, 'TURNS BY DEPT TODAY', S.departments.map((d) => { const v = CO.deptView(d); return ['#' + new THREE.Color(v.status === 'idle' ? STC.queued : STC[v.status]).getHexString(), turnsBy[d.id] || 0]; }));
      if (hub.kb) drawKanban(hub.kb, { queued: S.plan.length, running: S.tasks.filter((t) => t.status === 'running').length, done: S.strip.filter((c) => c.state === 'done').length, failed: S.strip.filter((c) => c.state === 'failed').length });
      if (hub.agents[0]) hub.agents[0].working = !paused;
      const html = '<div class="p3h"><i style="background:' + (paused ? '#7f93ad' : '#00e5ff') + '"></i><b>MANAGER</b></div><div class="p3l" style="color:' + (paused ? '#a9b8cc' : '#00e5ff') + '">' + (paused ? 'Paused' : (CO.RO ? 'Its chat' : 'Your chat') + ' · runs it all') + '</div>';
      if (hub.plate._h !== html) { hub.plate._h = html; hub.plate.innerHTML = html; }
      hub.plate.classList.toggle('work', !paused && anyWork); hub.plate.style.setProperty('--c', paused ? '#7f93ad' : '#00e5ff');
      const na = S.approvals.length;
      hub.need.hidden = false;
      hub.need.className = 'p3need' + (na ? '' : ' clear');
      hub.need.textContent = na ? na + (CO.RO ? ' WAIT FOR ITS OWNER' : na === 1 ? ' NEEDS YOU' : ' NEED ATTENTION') : 'ALL CLEAR';
    }
    const au = this.rooms.audit;
    if (au) {
      const A = S.audit, days = Math.max(0, Math.ceil((A.next_at - S.clock) / 86400000)), nf = A.last ? A.last.findings.length : 0;
      this.tint(au, 'idle');
      drawWall(au.wall, 'Weekly audit: next in ' + days + 'd', nf + ' findings last week', '#38f2b8', '');
      const html = '<div class="p3h"><i style="background:#38f2b8"></i><b>WEEKLY AUDIT</b></div><div class="p3l" style="color:#a9b8cc">next in ' + days + (days === 1 ? ' day' : ' days') + '</div>';
      if (au.plate._h !== html) { au.plate._h = html; au.plate.innerHTML = html; }
      au.plate.style.setProperty('--c', '#38f2b8');
    }
    // the vault: what it holds is seen only by clicking it (the right column then opens it), so its plate names it
    // and nothing more; the piles inside are rebuilt when what they hold changes
    const vr = this.rooms.vault;
    if (vr) {
      const VT = CO.vaultTotals(), priv = !!CO.RO, vk = priv ? 'priv' : Math.round(VT.et10) + '|' + VT.usdc.toFixed(2);
      if (vr._k !== vk) { vr._k = vk; this.piles(vr, VT, priv); }
      this.tint(vr, 'idle');
      const html = '<div class="p3h"><i style="background:#38f2b8"></i><b>VAULT</b></div><div class="p3l" style="color:#a9b8cc">' + (priv ? 'Private' : 'Earnings') + '</div>';
      if (vr.plate && vr.plate._h !== html) { vr.plate._h = html; vr.plate.innerHTML = html; }
      if (vr.plate) vr.plate.style.setProperty('--c', '#38f2b8');
    }
    this.paused = S.company.status === 'paused';
    this.drawSel();
  }
  // A room's neon in the colour of what it needs, as in his picture: mint for every room, orange for the one that
  // waits on you (and the trading desk, orange in his picture). Working shows as a brighter line and a faint mint
  // wash on the floor, not as another colour.
  tint(r, st) {
    const dk = r.dept && r.dept.key;
    const isOrange = dk === 'trading_desk' || st === 'waiting';
    if (r.st === st && r.orange === isOrange) return;
    r.st = st; r.orange = isOrange;
    const c = new THREE.Color(isOrange ? LOOK.orange : LOOK.neon);
    if (r.edgeM) { r.edgeM.emissive.copy(c); r.edgeM.emissiveIntensity = isOrange ? 2.2 : st === 'working' ? 2.0 : 1.5; }
    if (r.glow) { r.glow.material.color.copy(c).multiplyScalar(isOrange ? 1.9 : 1); r.glowBase = isOrange ? 1.0 : st === 'working' ? 0.05 : 0; }
    if (r.lamp) { r.lamp.color.set(isOrange ? 0xff6a34 : 0xeef6ff); r.lamp.intensity = isOrange ? 22 : 6; r.lamp.distance = isOrange ? 6.5 : 9; }
  }
  drawSel() {
    release(this.selRing); this.selRing.clear();
    const c = this.sel && this.cells[this.sel]; if (!c) return;
    const RS = CO.iso.RS, m = emis('#00e5ff', 1.4), x0 = c[0] - 0.15, y0 = c[1] - 0.15, s = RS + 0.3;
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
    const hex = { cyan: '#00e5ff', green: '#38f2b8', red: '#ff8824', blue: '#3b82f6' }[colour] || '#00e5ff', A = amat(hex);
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
  // The reference's framing (CAM): its view direction and lens, the distance at which the platform's bounds are as
  // wide and as tall as there (whichever binds at this stage's size), and the target moved so they sit where they do
  home() {
    const dir = new THREE.Vector3().setFromSpherical(new THREE.Spherical(1, CAM.polar, CAM.az)), cam = this.camera.clone(), pts = this.corners || [];
    const tgt = new THREE.Vector3(); pts.forEach((p) => tgt.add(p)); if (pts.length) tgt.divideScalar(pts.length); tgt.y = 0;
    const bounds = (d) => {
      cam.position.copy(tgt).addScaledVector(dir, d); cam.lookAt(tgt); cam.updateMatrixWorld();
      let x0 = 9, x1 = -9, y0 = 9, y1 = -9;
      pts.forEach((p) => { const v = p.clone().project(cam); x0 = Math.min(x0, v.x); x1 = Math.max(x1, v.x); y0 = Math.min(y0, v.y); y1 = Math.max(y1, v.y); });
      return [x0, x1, y0, y1];
    };
    let d = 45;
    for (let k = 0; k < 3; k++) {
      let lo = 8, hi = 420;
      for (let i = 0; i < 24; i++) { const mid = (lo + hi) / 2, b = bounds(mid); if (b[1] - b[0] <= CAM.box[0] && b[3] - b[2] <= CAM.box[1]) hi = mid; else lo = mid; }
      d = hi;
      const b = bounds(d), right = new THREE.Vector3().setFromMatrixColumn(cam.matrixWorld, 0), up = new THREE.Vector3().setFromMatrixColumn(cam.matrixWorld, 1);
      const h = 2 * d * Math.tan(THREE.MathUtils.degToRad(cam.fov) / 2), w = h * cam.aspect;
      tgt.addScaledVector(right, ((b[0] + b[1]) / 2 - CAM.mid[0]) * w / 2).addScaledVector(up, ((b[2] + b[3]) / 2 - CAM.mid[1]) * h / 2);
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
    const dir = new THREE.Vector3().setFromSpherical(new THREE.Spherical(1, CAM.polar - 0.06, CAM.az));
    this.tween(tgt.clone().add(dir.multiplyScalar(tight ? 16.5 : 19.5)), tgt, 750);
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
    if (w !== this._cw || h !== this._ch) { this._cw = w; this._ch = h; this.resize(); this.lastInput = performance.now(); }
    if (!this.pace(performance.now())) return;
    const t = this.clock.getElapsedTime(), now = performance.now();
    if (this.tw) {
      const k = Math.min(1, (now - this.tw.s) / this.tw.ms), e = k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
      this.camera.position.lerpVectors(this.tw.p0, this.tw.p1, e); this.controls.target.lerpVectors(this.tw.t0, this.tw.t1, e);
      if (k >= 1) { const d = this.tw.done; this.tw = null; if (d) d(); }
    }
    this.controls.update();
    this.sky.position.copy(this.camera.position);
    if (this.fill) { this.fill.position.copy(this.camera.position).add(new THREE.Vector3(-4, 8, 0)); this.fill.target.position.copy(this.controls.target); }
    if (this.drift) this.drift.forEach((d, i) => { d.m.rotation.y = t * d.sp + i; d.m.rotation.x = t * d.sp * 0.6 + i * 2; });
    if (this.flames) this.flames.forEach((f) => { f.glow.material.opacity = (f.base || 0.26) + 0.08 * Math.sin(t * 3 + f.ph) + 0.03 * Math.sin(t * 11 + f.ph); });
    if (this.vaultPiles) this.vaultPiles.forEach((p, i) => { p.position.y = p.userData.y + Math.sin(t * 1.2 + i) * 0.03; });
    Object.values(this.rooms).forEach((r) => {
      if (r.grow) { const k = Math.min(1, (now - r.grow) / 1200), e = 1 - Math.pow(1 - k, 3); r.g.scale.set(1, Math.max(0.01, e), 1); if (k >= 1) r.grow = 0; }
      if (r.glow) r.glow.material.opacity = (r.glowBase || 0) * (r.st === 'working' ? 0.75 + 0.25 * Math.sin(t * 2.4 + r.x0) : 1);
      if (r.leds) r.leds.forEach((m, i) => { m.visible = ((Math.floor(t * 3 + m.userData.blink)) % 3) !== 0; });
      if (r.holo) { r.holo.forEach((hh, i) => { hh.rotation.z = t * (0.6 + i * 0.35) * (i % 2 ? -1 : 1); hh.position.y = hh.userData.y + Math.sin(t * 1.3 + i) * 0.05; }); r.core.position.y = 1.0 + Math.sin(t * 1.7) * 0.05; }
      if (r.crystal) r.crystal.forEach((m) => { m.rotation.y = t * 0.7; });
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
        if (a.walk) { const W3 = a.walk, dx = W3.to.x - W3.from.x, dz = W3.to.z - W3.from.z; a.g.rotation.y = (now - W3.t0) < W3.dur && Math.hypot(dx, dz) > 0.01 ? Math.atan2(-dx, -dz) : a.g.rotation.y; } else a.g.rotation.y = a.ry || 0;
        a.b.position.y = a.by + (walking ? 0.1 : 0) + (a.working ? Math.abs(Math.sin(t * 7 + a.phase)) * 0.02 : 0);
        // an astronaut at work: its visor and its chest light go cyan
        a.visorM.emissiveIntensity = a.working ? 0.9 : 0.25; a.chest.material = a.working ? OM.cyan.glow : OM.pack;
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
      // written only when it changes: a still camera then costs the page no style work at all
      if (el._off !== off) { el._off = off; el.style.display = off ? 'none' : ''; }
      const tf = off ? '' : 'translate(' + ((v.x + 1) / 2 * w).toFixed(1) + 'px,' + y.toFixed(1) + 'px) translate(-50%,-50%)';
      if (!off && el._tf !== tf) { el._tf = tf; el.style.transform = tf; }
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
    cv.addEventListener('pointerdown', (e) => { down = { x: e.clientX, y: e.clientY }; this.lastInput = performance.now(); });
    cv.addEventListener('pointermove', (e) => { this.setMouse(e); this.mouseMoved = true; this.lastEv = e; this.lastInput = performance.now(); });
    cv.addEventListener('pointerleave', () => { this.setHover(null); this.hideTip(); });
    cv.addEventListener('pointerup', (e) => {
      if (!down) return; const moved = Math.abs(e.clientX - down.x) + Math.abs(e.clientY - down.y) > 5; down = null; if (moved) return;
      this.setMouse(e); const hit = this.pickHit(); if (!hit) return;
      if (hit.userData.pc) { window.open(hit.userData.pc.url, '_blank', 'noopener'); return; }
      if (hit.userData.key) CO.emit('office:click', hit.userData.key);
    });
    cv.addEventListener('wheel', () => { this.tw = null; this.lastInput = performance.now(); }, { passive: true });
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
  CO.U3 = (gl2 || navigator.gpu) ? { ok: true, gpu: !!navigator.gpu, universe: (el, stage, h) => new Universe3D(el, stage, h), office: (el, stage, tipFor) => new Office3D(el, stage, tipFor), preview, thumbs, THREE, geo, makeStation, SKIN, amat, nebTex, TX, OM }
    : { failed: true, why: 'no WebGPU and no WebGL2' };
  window.dispatchEvent(new Event('co3d'));
})();
