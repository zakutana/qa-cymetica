/* The /company mockup's 3D engine. The Universe is a galaxy: Cymetica the star at its heart, every company a
 * station on one of its spiral arms, ONE DECK PER DEPARTMENT, a deck lit while its department works. three.js with
 * its WebGPU renderer (WebGL2 where a browser has no WebGPU), bloom on everything that glows, an orbit camera that
 * zooms to the cursor. Banners and the tooltip are HTML over the canvas, so they stay sharp and clickable. If the
 * renderer cannot start, the page keeps the flat map. The office in 3D is the second half of this file. */
import * as THREE from 'three/webgpu';
import { pass, renderOutput } from 'three/tsl';
import { bloom } from 'three/addons/tsl/display/BloomNode.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { mergeGeometries } from 'three/addons/utils/BufferGeometryUtils.js';

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
    wire: new THREE.MeshBasicMaterial({ color: c.clone().multiplyScalar(0.85), wireframe: true, transparent: true, opacity: 0.45 }),
    beam: new THREE.MeshBasicMaterial({ color: c.clone().multiplyScalar(1.3), transparent: true, opacity: 0.14, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }),
    atmo: new THREE.MeshBasicMaterial({ color: c.clone().multiplyScalar(0.9), transparent: true, opacity: 0.12, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.BackSide }),
    fin: new THREE.MeshStandardMaterial({ color: 0x0a111d, emissive: c, emissiveIntensity: 0.55, roughness: 0.6 }),
    panel: new THREE.MeshStandardMaterial({ color: 0x9fb2c8, map: cells, emissive: c, emissiveMap: cells, emissiveIntensity: 0.5, roughness: 0.25, metalness: 0.55 }),
    lit: c.clone().multiplyScalar(1.2), hot: c.clone().multiplyScalar(3.2), dim: new THREE.Color(0.012, 0.02, 0.035)
  };
  return AM[hex];
}
// The scene, its bloom, then tone mapping, drawn through a quad of its own. three.js's PostProcessing (r172)
// keeps ONE material for every instance on the page, so with the map and a preview both running, whichever
// updated last would draw into both canvases. This one owns its material.
class Post {
  constructor(renderer, scene, camera, strength, radius, threshold) {
    this.renderer = renderer;
    const sp = pass(scene, camera, { samples: 4 }), col = sp.getTextureNode('output');
    this.material = new THREE.NodeMaterial();
    this.material.fragmentNode = renderOutput(col.add(bloom(col, strength, radius, threshold)), renderer.toneMapping, renderer.outputColorSpace);
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
// The sky, painted once: near-black, the Milky Way as a band of light with dust down its middle, nebulae in the
// site's colours (cyan, green, blue, a breath of red), and stars -- thick in the band, thin elsewhere.
function skyTex() {
  if (TX.sky) return TX.sky;
  const W = 4096, H = 2048, c = document.createElement('canvas'); c.width = W; c.height = H;
  const g = c.getContext('2d'), R = rng(5), gauss = () => R() + R() + R() + R() - 2;
  const band = (x) => H * 0.5 + Math.sin(x / W * Math.PI * 2 + 0.6) * H * 0.2;
  const blob = (x, y, r, rgb, a) => {
    [x, x - W, x + W].forEach((xx) => {
      if (xx + r < 0 || xx - r > W) return;
      const gr = g.createRadialGradient(xx, y, 0, xx, y, r);
      gr.addColorStop(0, 'rgba(' + rgb + ',' + a + ')'); gr.addColorStop(0.45, 'rgba(' + rgb + ',' + (a * 0.35) + ')'); gr.addColorStop(1, 'rgba(' + rgb + ',0)');
      g.fillStyle = gr; g.fillRect(xx - r, y - r, r * 2, r * 2);
    });
  };
  g.fillStyle = '#010204'; g.fillRect(0, 0, W, H);
  g.globalCompositeOperation = 'lighter';
  for (let i = 0; i < 420; i++) { const x = R() * W, m = R(); blob(x, band(x) + gauss() * H * 0.05, 50 + R() * 170, m < 0.45 ? '120,200,230' : m < 0.8 ? '0,207,255' : '0,255,136', 0.012 + R() * 0.022); }
  [['0,207,255', 0.3, 0.18, 0.36, 520], ['0,255,136', 0.16, 0.62, 0.6, 460], ['59,130,246', 0.22, 0.4, 0.74, 500], ['0,207,255', 0.18, 0.86, 0.32, 380],
    ['0,255,136', 0.1, 0.05, 0.7, 340], ['255,68,68', 0.05, 0.3, 0.2, 300]].forEach(([rgb, a, fx, fy, r]) => {
    for (let k = 0; k < 18; k++) blob(fx * W + gauss() * r * 0.5, fy * H + gauss() * r * 0.3, r * (0.25 + R() * 0.6), rgb, a * (0.25 + R() * 0.45));
  });
  g.globalCompositeOperation = 'source-over';
  for (let i = 0; i < 160; i++) { const x = R() * W; blob(x, band(x) + gauss() * H * 0.012, 30 + R() * 90, '0,0,0', 0.25 + R() * 0.25); }
  for (let i = 0; i < 30000; i++) {
    const inBand = R() < 0.55, x = R() * W, y = inBand ? band(x) + gauss() * H * 0.06 : H * (0.04 + R() * 0.92);
    const m = R(), a = (0.2 + m * m * 0.8).toFixed(2), s = m > 0.993 ? 2.4 : m > 0.95 ? 1.6 : 1, hue = R();
    g.fillStyle = hue < 0.1 ? 'rgba(0,207,255,' + a + ')' : hue < 0.14 ? 'rgba(0,255,136,' + a + ')' : 'rgba(235,242,250,' + a + ')';
    g.fillRect(x, y, s, s);
  }
  for (let i = 0; i < 30; i++) {
    const x = R() * W, y = H * (0.08 + R() * 0.84), s = 3 + R() * 7;
    g.globalCompositeOperation = 'lighter'; blob(x, y, s * 1.5, '200,240,255', 0.45);
    g.fillStyle = 'rgba(220,245,255,.32)'; g.fillRect(x - s * 1.6, y - 0.5, s * 3.2, 1); g.fillRect(x - 0.5, y - s * 1.6, 1, s * 3.2);
    g.globalCompositeOperation = 'source-over';
  }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 4; TX.sky = t; return t;
}
// the galaxy's own stars and dust along its arms, and the bulge round the core: what the stations live in
function galaxyDust() {
  const Gx = CO.uvGalaxy, R = rng(9), g = new THREE.Group(), N = 32000, outer = Gx.R1 * 1.12, gauss = () => R() + R() + R() + R() - 2;
  const pos = new Float32Array(N * 3), col = new Float32Array(N * 3), c = new THREE.Color();
  const core = new THREE.Color(0xe8fbff), cy = new THREE.Color(0x00cfff), gr = new THREE.Color(0x00ff88), bl = new THREE.Color(0x3b82f6);
  for (let i = 0; i < N; i++) {
    let x, y, z;
    if (i < N * 0.16) {
      const r = Math.pow(R(), 2.2) * 28, th = R() * Math.PI * 2, ph = Math.acos(R() * 2 - 1), k = 1 - r / 28;
      x = Math.sin(ph) * Math.cos(th) * r; y = Math.cos(ph) * r * 0.42; z = Math.sin(ph) * Math.sin(th) * r;
      c.copy(core).lerp(cy, 1 - k).multiplyScalar(0.45 + k * 1.3);
    } else {
      const r = 14 + Math.pow(R(), 0.9) * outer, th = Gx.angle(i % Gx.ARMS, r) + gauss() * (0.14 + r / outer * 0.16), k = r / outer, m = R();
      x = Math.cos(th) * r; z = Math.sin(th) * r; y = gauss() * (1 + r * 0.03);
      c.copy(k < 0.3 || m < 0.45 ? cy : m < 0.75 ? gr : bl).lerp(core, Math.max(0, 0.45 - k)).multiplyScalar(0.25 + R() * R() * 0.95);
    }
    pos.set([x, y, z], i * 3); col.set([c.r, c.g, c.b], i * 3);
  }
  const geom = new THREE.BufferGeometry(); geom.setAttribute('position', new THREE.BufferAttribute(pos, 3)); geom.setAttribute('color', new THREE.BufferAttribute(col, 3));
  g.add(new THREE.Points(geom, new THREE.PointsMaterial({ vertexColors: true, size: 1, sizeAttenuation: false, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false })));
  // soft clouds along the arms, so the arms glow and do not only sparkle; they fade as the camera comes into
  // them, or a close look would be a look through fog (fadeNear, every frame)
  g.userData.fade = [];
  for (let i = 0; i < 96; i++) {
    const r = 18 + Math.pow(R(), 0.8) * outer * 0.95, th = Gx.angle(i % Gx.ARMS, r) + gauss() * 0.1, m = R();
    const s = glowSprite(m < 0.5 ? 0x00cfff : m < 0.8 ? 0x00ff88 : 0x3b82f6, 0.045 + R() * 0.055, 24 + R() * 44 * (1 - r / outer * 0.4));
    s.position.set(Math.cos(th) * r, gauss() * 2, Math.sin(th) * r); g.add(s);
    g.userData.fade.push({ s, base: s.material.opacity, near: 50, far: 150 });
  }
  return g;
}
// the disc of light Cymetica spins round itself
function discPoints() {
  const N = 4500, pos = new Float32Array(N * 3), col = new Float32Array(N * 3), R = rng(4), c = new THREE.Color();
  for (let i = 0; i < N; i++) {
    const r = 3.4 + Math.pow(R(), 1.5) * 15, th = R() * Math.PI * 2, m = R();
    pos.set([Math.cos(th) * r, (R() - 0.5) * 0.35, Math.sin(th) * r], i * 3);
    c.set(m < 0.65 ? 0x00cfff : m < 0.85 ? 0x00ff88 : 0xe8fbff).multiplyScalar(0.45 + (1 - (r - 3.4) / 15) * 1.7);
    col.set([c.r, c.g, c.b], i * 3);
  }
  const geom = new THREE.BufferGeometry(); geom.setAttribute('position', new THREE.BufferAttribute(pos, 3)); geom.setAttribute('color', new THREE.BufferAttribute(col, 3));
  return new THREE.Points(geom, new THREE.PointsMaterial({ vertexColors: true, size: 1, sizeAttenuation: false, transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
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
  const keel = b.part(G.cone, M.hull2, half * 0.95, 1.6, half * 0.95, 0, -0.8, 0); keel.rotation.x = Math.PI;
  b.part(G.cyl, M.trim, half * 1.02, 0.16, half * 1.02, 0, -0.08, 0);
  flame(b, -1.62, 0.7, 1.4);
  const dock = b.part(G.ringT, A.rim, half * 1.6, half * 1.6, half * 1.6, 0, 0.32, 0); dock.rotation.x = Math.PI / 2;
  for (let k = 0; k < 4; k++) { const a = k * Math.PI / 2 + Math.PI / 4; b.box(half * 0.62, 0.05, 0.05, Math.cos(a) * half * 1.28, 0.32, Math.sin(a) * half * 1.28, M.metal).rotation.y = -a; }
  let y = 0;
  for (let f = 0; f < n; f++) {
    const h = FH - 0.08, rot = f * tw;
    b.box(fp, h, fp, 0, y + h / 2, 0, f % 2 ? M.hull2 : M.hull).rotation.y = rot;
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
  b.top = y + 2.1; b.bot = -3.0; b.foot = Math.max(half * 1.7, 2.2);
};
// Biodome: a drum of decks on a small planetoid, a glass dome with a garden and a light in it, a moonlet
SKIN.dome = (b, n) => {
  const A = b.A, r = fpOf(n) / 2 + 0.5, rr = r * 1.45, cy = -rr * 0.62;
  const rock = b.part(G.rock, M.rock, rr, rr * 0.8, rr, 0, cy, 0); rock.rotation.y = b.R() * 6;
  for (let k = 0; k < 6; k++) {
    const a = k / 6 * Math.PI * 2 + b.R() * 0.6, e = -0.15 - b.R() * 0.55;
    b.part(G.sphere, A.glow, 0.055, 0.055, 0.055, Math.cos(a) * Math.cos(e) * rr * 1.1, cy + Math.sin(e) * rr * 0.9, Math.sin(a) * Math.cos(e) * rr * 1.1);
  }
  b.cyl(r + 0.3, 0.16, 0, 0, 0, M.trim);
  let y = 0.08;
  for (let f = 0; f < n; f++) {
    const h = FH - 0.06;
    b.cyl(r, h, 0, y + h / 2, 0, f % 2 ? M.hull2 : M.hull);
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
  const moon = b.part(G.rock, M.rock, 0.42, 0.36, 0.42, 0, 0, 0, true);
  b.anim.push((t) => {
    core.position.y = y + r * 0.42 + Math.sin(t * 1.3 + b.phase) * 0.05; wire.rotation.y = t * 0.08;
    const a = t * 0.3 + b.phase; moon.position.set(Math.cos(a) * rr * 1.55, cy * 0.4 + Math.sin(a * 0.7) * 0.5, Math.sin(a) * rr * 1.55); moon.rotation.y = t * 0.4;
  });
  b.beacon(0, y + r * 0.95 + 0.06, 0, 0.08);
  b.top = y + r * 0.95 + 0.6; b.bot = cy - rr * 0.82; b.foot = rr * 1.3;
};
// Ziggurat: a tier per deck on a floating island of rock, stones drifting under it, a beam from its temple
SKIN.pyramid = (b, n) => {
  const A = b.A, b0 = fpOf(n) + 1.0, inset = Math.min(0.3, (b0 - 1.1) / (2 * n)), kh = b0 * 1.05;
  b.part(G.cone4, M.rock, b0 * 0.72, kh, b0 * 0.72, 0, -kh / 2, 0).rotation.set(Math.PI, Math.PI / 4, 0);
  for (let k = 0; k < 3; k++) {
    const a = k / 3 * Math.PI * 2 + b.R(), s = 0.22 + b.R() * 0.22, x = Math.cos(a) * b0 * 0.42, z = Math.sin(a) * b0 * 0.42, y0 = -kh * (0.55 + b.R() * 0.3);
    const st = b.part(G.rock, M.rock, s, s * 0.85, s, x, y0, z, true);
    b.anim.push((t) => { st.position.y = y0 + Math.sin(t * 0.8 + k * 2 + b.phase) * 0.18; st.rotation.y = t * 0.3 + k; });
  }
  b.rimSquare(b0 + 0.04, 0.0, A.soft);
  let y = 0;
  for (let f = 0; f < n; f++) {
    const s = b0 - 2 * inset * f, h = FH - 0.05;
    b.box(s, h, s, 0, y + h / 2, 0, f % 2 ? M.hull2 : M.hull);
    b.rimSquare(s, y + h, A.rim);
    b.faceWins(f, s, s, y + h / 2, h, 0.62, 0.3);
    y += FH;
  }
  b.box(0.8, 0.5, 0.8, 0, y + 0.25, 0, M.trim);
  const beam = b.part(G.beam, A.beam.clone(), 1, 6, 1, 0, y + 3.5, 0, true);
  b.anim.push((t) => { beam.material.opacity = (b.busy ? 0.3 : 0.16) + 0.05 * Math.sin(t * 2 + b.phase); });
  b.beacon(0, y + 0.62, 0, 0.13);
  b.top = y + 1.5; b.bot = -kh - 0.2; b.foot = b0 * 0.85 + 0.4;
};
// Ring station: a spindle of disc decks, a great wheel round it on four spokes, turning slowly, an engine below
SKIN.orbital = (b, n) => {
  const A = b.A, rd = 0.75 + fpOf(n) * 0.15, spineH = 0.4 + n * FH, RR = rd + 1.9;
  b.cyl(0.22, spineH + 1.6, 0, (spineH - 0.4) / 2, 0, M.metal);
  b.part(G.bell, M.trim, 0.42, 0.55, 0.42, 0, -1.25, 0);
  flame(b, -1.55, 0.75, 1.3);
  let y = 0.2;
  for (let f = 0; f < n; f++) {
    b.cyl(rd, 0.3, 0, y + 0.15, 0, f % 2 ? M.hull2 : M.hull);
    b.part(G.ringT, A.rim, rd + 0.01, rd + 0.01, rd + 0.01, 0, y + 0.3, 0).rotation.x = Math.PI / 2;
    b.ringWins(f, rd, y + 0.15, 0.14, 0.38, 0.5, 0.15);
    y += FH;
  }
  const wheel = new THREE.Group(); wheel.position.y = 0.2 + n * FH / 2 - 0.25; wheel.userData.dyn = true; b.g.add(wheel);
  const tor = new THREE.Mesh(G.wheel, M.hull2); tor.scale.setScalar(RR); tor.rotation.x = Math.PI / 2; wheel.add(tor);
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
    b.part(G.cyl, f % 2 ? M.hull2 : M.hull, rr, L - 0.05, rr, x, cy, 0).rotation.z = Math.PI / 2;
    b.part(G.cyl, A.rim, rr * 1.035, 0.05, rr * 1.035, x + L / 2 - 0.025, cy, 0).rotation.z = Math.PI / 2;
    for (const s of [1, -1]) for (const dx of [-0.22, 0.2]) b.win(x + dx, cy + 0.06, s * (rr + 0.014), s > 0 ? 0 : Math.PI, 0.17, 0.19, f, b.R() < 0.55);
  }
  b.part(G.cone, M.hull, rr, rr * 2.3, rr, len / 2 + rr * 1.15, cy, 0).rotation.z = -Math.PI / 2;
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
    b.box(w, h, d, 0, y + h / 2, 0, f % 2 ? M.hull2 : M.hull);
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
const RING = { pub: 0.7, priv: 0.45, hover: 2.6 };
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
  return { root, body, b, rimMat, ring, ringR, hit, halo, haloBase: halo.material.opacity, top: b.top, bot: ringY, n, pub, spin: (seed % 13) / 13 * Math.PI * 2 };
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
    this.camera = new THREE.PerspectiveCamera(36, 2, 0.5, 6000);
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
      autoRotate: true, autoRotateSpeed: 0.16, screenSpacePanning: false, zoomToCursor: true, zoomSpeed: 1.1, rotateSpeed: 0.55, panSpeed: 1.1,
      mouseButtons: { LEFT: THREE.MOUSE.PAN, MIDDLE: THREE.MOUSE.DOLLY, RIGHT: THREE.MOUSE.ROTATE },
      touches: { ONE: THREE.TOUCH.PAN, TWO: THREE.TOUCH.DOLLY_ROTATE } });
    this.controls.addEventListener('start', () => { this.tw = null; this.used = true; this.lastUse = performance.now(); this.controls.autoRotate = false; });
    this.world();
    this.bind();
    this.resize();
    this.clock = new THREE.Clock();
    this.renderer.init().then(() => {
      try { this.post = new Post(this.renderer, this.scene, this.camera, 0.9, 0.55, 0.68); } catch (e) { console.warn('bloom off:', e); this.post = null; }
      this.renderer.setAnimationLoop(() => this.frame());
      this.ready = true;
    }).catch((e) => { console.error('3D map could not start:', e); if (this.h.onFail) this.h.onFail(e); });
    setInterval(() => { if (this.visible()) this.pulse(); }, 1700);
    if (window.ResizeObserver) new ResizeObserver(() => this.resize()).observe(el);
  }
  visible() { return this.el.clientWidth > 0 && this.el.clientHeight > 0; }

  // light, the sky, the galaxy's dust, the lanes its traffic flies, and Cymetica in the middle
  world() {
    const S = this.scene;
    S.add(new THREE.AmbientLight(0x1a2230, 0.7));
    S.add(new THREE.HemisphereLight(0xdfe8f2, 0x05070a, 0.6));
    const sun = new THREE.DirectionalLight(0xf4f8fc, 1.9); sun.position.set(-300, 240, 160); S.add(sun);
    const rim = new THREE.DirectionalLight(0x00cfff, 0.5); rim.position.set(240, -60, -260); S.add(rim);
    this.sky = new THREE.Mesh(new THREE.SphereGeometry(2600, 64, 32), new THREE.MeshBasicMaterial({ map: skyTex(), side: THREE.BackSide, depthWrite: false }));
    this.sky.rotation.set(0.42, 0.3, 0.18); this.sky.renderOrder = -1; S.add(this.sky);
    this.starLayers = [starField(5000, 1400, 700, 1.0, 11), starField(1800, 700, 300, 0.9, 12)];
    this.starLayers.forEach((s) => S.add(s));
    const dust = galaxyDust(); S.add(dust); this.fades = dust.userData.fade.slice();
    this.lanes();
    this.core();
  }
  // five orbits round the core, faint, and the shuttles flying them
  lanes() {
    const R = rng(3);
    this.laneDefs = [[22, 0x00cfff], [56, 0x00ff88], [96, 0x00cfff], [140, 0x3b82f6], [184, 0x00ff88]].map(([r, col], i) => {
      const m = new THREE.Matrix4().makeRotationFromEuler(new THREE.Euler((R() - 0.5) * 0.22, R() * Math.PI * 2, (R() - 0.5) * 0.22)), pts = [];
      for (let k = 0; k <= 256; k++) { const a = k / 256 * Math.PI * 2; pts.push(new THREE.Vector3(Math.cos(a) * r, 0, Math.sin(a) * r).applyMatrix4(m)); }
      // a Line through 257 points that end where they begin (the WebGPU renderer draws no LineLoop)
      this.scene.add(new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts), new THREE.LineBasicMaterial({ color: col, transparent: true, opacity: 0.11, blending: THREE.AdditiveBlending, depthWrite: false })));
      return { r, m, col, speed: (i % 2 ? -1 : 1) * 14 / Math.pow(r, 1.5) };
    });
    this.ships = [];
    this.laneDefs.forEach((L, i) => { const n = 4 + i * 2; for (let k = 0; k < n; k++) this.ships.push({ L, a: k / n * Math.PI * 2 + R() * 0.5 }); });
    const n = this.ships.length;
    this.shipMesh = new THREE.InstancedMesh(G.box, new THREE.MeshBasicMaterial({ color: 0xffffff }), n);
    this.trailMesh = new THREE.InstancedMesh(G.box, new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.4, blending: THREE.AdditiveBlending, depthWrite: false }), n);
    this.ships.forEach((s, i) => { const c = new THREE.Color(s.L.col); this.shipMesh.setColorAt(i, c.clone().multiplyScalar(2.6)); this.trailMesh.setColorAt(i, c.clone().multiplyScalar(0.8)); });
    this.shipMesh.instanceColor.needsUpdate = true; this.trailMesh.instanceColor.needsUpdate = true;
    this.shipMesh.frustumCulled = false; this.trailMesh.frustumCulled = false;
    this.scene.add(this.shipMesh, this.trailMesh);
  }
  // Cymetica: a star, its corona, a gyroscope of rings, a beam through its poles and a spinning disc of light
  core() {
    const g = new THREE.Group(), cy = amat('#00cfff'), gr = amat('#00ff88');
    const star = new THREE.Mesh(G.sphere, new THREE.MeshBasicMaterial({ color: new THREE.Color(0xd8f7ff).multiplyScalar(3.2) })); star.scale.setScalar(2.4); g.add(star);
    this.corona = [[12, 0.95, 0xd8f7ff], [26, 0.42, 0x00cfff], [52, 0.13, 0x00cfff], [96, 0.035, 0x00ff88]].map(([s, o, c]) => { const sp = glowSprite(c, o, s); g.add(sp); return sp; });
    this.coreRings = [[6, cy.rim], [8.2, gr.rim], [10.6, cy.soft]].map(([r, m]) => { const ring = new THREE.Mesh(G.ringT, m); ring.scale.setScalar(r); g.add(ring); return ring; });
    // its jet: thin and faint, narrowing up from the north pole
    const jet = new THREE.Mesh(G.beam, new THREE.MeshBasicMaterial({ color: new THREE.Color(0x00cfff).multiplyScalar(1.2), transparent: true, opacity: 0.06, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }));
    jet.scale.set(0.8, 70, 0.8); jet.position.y = 37; g.add(jet);
    this.disc = discPoints(); g.add(this.disc);
    g.add(new THREE.PointLight(0xa8ecff, 2200, 0, 2));
    const hit = new THREE.Mesh(G.sphere, M.hit); hit.scale.setScalar(8); hit.userData.id = 'core'; g.add(hit); this.coreHit = hit;
    this.coreAt = new THREE.Vector3(0, 12.5, 0);
    this.scene.add(g);
  }

  // every company in its place on the arms; ours where the camera first looks
  layout() {
    this.items = CO.uvPlan(this.h.mine());
    CO.uvSeed(this.items, this.live);
    this.items.forEach((it) => this.place(it));
    this.coreBanner();
    this.stats();
    // zoomed all the way out, the galaxy still fills most of the view: not a speck in the dark
    this.controls.maxDistance = this.home().pos.distanceTo(this.home().tgt) * 1.6;
  }
  place(it) {
    this.built = (this.built || 0) + 1;
    if (it.plot) { this.scene.remove(it.plot.root); release(it.plot.root); }
    const c = it.c, p = makeStation(c, it.mine ? 7 : c.id, { mine: it.mine });
    p.root.position.set(it.pos[0], it.pos[1], it.pos[2]);
    p.hit.userData.id = c.id;
    if (it.mine) p.meRing = p.ring;
    this.scene.add(p.root);
    it.plot = p;
    it.anchor = new THREE.Vector3(it.pos[0], it.pos[1] + p.top + 0.5, it.pos[2]);
    it.size = p.top - p.bot;
    this.paint(it);
    this.banner(it);
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
    const core = new THREE.Vector3(0, 0, 0), top = it.plot.root.position.clone().add(new THREE.Vector3(0, it.plot.top * 0.6, 0));
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
  // the whole galaxy, seen from above its disc on our side of the core
  home() {
    const Gx = CO.uvGalaxy, R = (Gx.outer || Gx.R1) + 12, a = this.camera.aspect || 2;
    const d = R * (a < 1.2 ? 3.4 : a < 1.6 ? 2.7 : 2.3);
    // aimed a little to our side of the core: the near half of a disc seen from above looks the bigger one
    const tgt = new THREE.Vector3(Math.sin(Gx.AZ) * R * 0.1, -6, Math.cos(Gx.AZ) * R * 0.1);
    return { pos: new THREE.Vector3().setFromSpherical(new THREE.Spherical(d, 0.9, Gx.AZ)).add(tgt), tgt };
  }
  fit(anim) {
    const h = this.home();
    if (!this.fitted && anim === false) {
      // the first look: from far outside the galaxy, flying in
      this.fitted = true;
      this.camera.position.copy(h.pos.clone().multiplyScalar(2.3).add(new THREE.Vector3(0, 380, 0))); this.controls.target.copy(h.tgt);
      this.tween(h.pos, h.tgt, 3400);
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
    const p = it.plot.root.position, tgt = new THREE.Vector3(p.x, p.y + (it.plot.top + it.plot.bot) * 0.5, p.z);
    const dir = this.camera.position.clone().sub(this.controls.target); if (dir.lengthSq() < 1e-6) dir.set(1, 0.6, 1);
    dir.y = Math.max(dir.y, dir.length() * 0.35); dir.normalize();
    const dist = 9 + (it.plot.top - it.plot.bot) * 1.3 + it.plot.b.foot * 0.7;
    this.tween(tgt.clone().add(dir.multiplyScalar(dist)), tgt, ms == null ? 1300 : ms, done);
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
      if (this.fitted && !this.tw && !this.used) this.fit(false);
    }
    const t = this.clock.getElapsedTime(), now = performance.now();
    if (this.tw) {
      const k = Math.min(1, (now - this.tw.s) / this.tw.ms), e = k < 0.5 ? 4 * k * k * k : 1 - Math.pow(-2 * k + 2, 3) / 2;
      this.camera.position.lerpVectors(this.tw.p0, this.tw.p1, e); this.controls.target.lerpVectors(this.tw.t0, this.tw.t1, e);
      if (k >= 1) { const d = this.tw.done; this.tw = null; if (d) d(); }
    }
    // turn slowly while nobody is using the map
    if (!this.tw && !this.mouseIn && now - this.lastUse > 7000) this.controls.autoRotate = true;
    if (this.mouseIn) this.controls.autoRotate = false;
    this.controls.update();
    // every station floats: it bobs, turns slowly, and our own ring breathes. What glows from afar -- a station's
    // halo, the arms' clouds -- gives way as the camera comes close
    const cam = this.camera.position, ss = THREE.MathUtils.smoothstep;
    this.items.forEach((it) => {
      const p = it.plot; if (!p) return;
      p.b.tick(t); p.body.position.y = Math.sin(t * 0.45 + p.b.phase) * 0.22; p.body.rotation.y = p.spin + t * 0.035;
      if (p.meRing) p.meRing.scale.setScalar(p.ringR * (1 + Math.sin(t * 2.4) * 0.05));
      p.halo.material.opacity = p.haloBase * ss(cam.distanceTo(p.root.position), 18, 80);
    });
    this.fades.forEach((f) => { f.s.material.opacity = f.base * ss(cam.distanceTo(f.s.position), f.near, f.far); });
    this.coreRings.forEach((r, i) => r.rotation.set(t * (0.31 + i * 0.17) * (i % 2 ? -1 : 1), t * (0.22 + i * 0.11), 0.4 * i));
    this.disc.rotation.y = t * 0.35;
    this.corona[0].material.opacity = 0.85 + 0.1 * Math.sin(t * 2.1);
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
    // the sky and the far stars go where the camera goes: they are as far as a sky is
    this.sky.position.copy(this.camera.position);
    this.starLayers.forEach((s) => s.position.copy(this.camera.position));
    if (this.mouseMoved) { this.mouseMoved = false; this.pick(); }
    // a GPU that cannot run a shader says so on the first frames: stop, and let the flat map take over
    try { if (this.post) this.post.render(); else this.renderer.render(this.scene, this.camera); this.frames = (this.frames || 0) + 1; }
    catch (e) { console.error('3D map stopped:', e); this.renderer.setAnimationLoop(null); if (this.h.onFail && !(this.frames > 30)) this.h.onFail(e); return; }
    this.overlay();
  }
  moveShips(t) {
    const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), p = new THREE.Vector3(), dir = new THREE.Vector3(), fwd = new THREE.Vector3(0, 0, 1);
    const s1 = new THREE.Vector3(0.24, 0.13, 0.75), s2 = new THREE.Vector3(0.07, 0.05, 3.4);
    this.ships.forEach((s, i) => {
      const L = s.L, a = s.a + t * L.speed;
      p.set(Math.cos(a) * L.r, 0, Math.sin(a) * L.r).applyMatrix4(L.m);
      dir.set(-Math.sin(a), 0, Math.cos(a)).transformDirection(L.m).multiplyScalar(Math.sign(L.speed));
      q.setFromUnitVectors(fwd, dir);
      m4.compose(p, q, s1); this.shipMesh.setMatrixAt(i, m4);
      p.addScaledVector(dir, -2.1); m4.compose(p, q, s2); this.trailMesh.setMatrixAt(i, m4);
    });
    this.shipMesh.instanceMatrix.needsUpdate = true; this.trailMesh.instanceMatrix.needsUpdate = true;
  }
  // The banners follow their stations. Ours, the hovered one and Cymetica's always show; the rest nearest first,
  // each only where no nearer one stands and only while its station is big enough on screen to be worth a name.
  overlay() {
    const w = this.el.clientWidth, h = this.el.clientHeight, v = new THREE.Vector3(), placed = [];
    // a still camera moves no banner: restyle them only when the view, the size, the hover or a station changed
    const key = this.camera.matrixWorld.elements.join(',') + '|' + w + 'x' + h + '|' + this.hover + '|' + this.items.length + '|' + this.built;
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
      const s = o.core ? 1 : Math.max(0.66, Math.min(1, 0.5 + o.px / 120));
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
const OFFICE = { bg: 0x05070a, lamp: 0xeef3f8, agent: 0x4d5d72, agentE: 0x0b0f14, mon: 0x10202a };
const OM = {};
function omats() {
  if (OM.tile) return;
  const c = document.createElement('canvas'); c.width = c.height = 512; const g = c.getContext('2d');
  // near-black tiles on a faint Cymetica-green grid
  g.fillStyle = '#0c1015'; g.fillRect(0, 0, 512, 512);
  g.strokeStyle = 'rgba(0,255,136,.14)'; g.lineWidth = 2;
  for (let i = 0; i <= 7; i++) { const p = i * 512 / 7; g.beginPath(); g.moveTo(p, 0); g.lineTo(p, 512); g.stroke(); g.beginPath(); g.moveTo(0, p); g.lineTo(512, p); g.stroke(); }
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
  OM.tile = new THREE.MeshStandardMaterial({ map: t, roughness: 0.38, metalness: 0.45 });
  OM.glass = new THREE.MeshStandardMaterial({ color: 0x33424f, transparent: true, opacity: 0.34, roughness: 0.06, metalness: 0.4, depthWrite: false });
  OM.frame = new THREE.MeshStandardMaterial({ color: 0x222c37, roughness: 0.45, metalness: 0.55 });
  OM.desk = new THREE.MeshStandardMaterial({ color: 0x1b232d, roughness: 0.5, metalness: 0.35 });
  OM.deskTop = new THREE.MeshStandardMaterial({ color: 0x2b3643, roughness: 0.35, metalness: 0.35 });
  OM.dark = new THREE.MeshStandardMaterial({ color: 0x07090d, roughness: 0.45, metalness: 0.45 });
  OM.head = new THREE.MeshStandardMaterial({ color: 0xa9b8cc, roughness: 0.6 });
  OM.plinth = new THREE.MeshStandardMaterial({ color: 0x0c1016, roughness: 0.45, metalness: 0.55 });
  OM.capsule = new THREE.CapsuleGeometry(0.17, 0.34, 4, 14);
  OM.green = amat('#00ff88'); OM.cyan = amat('#00cfff'); OM.blue = amat('#3b82f6'); OM.red = amat('#ff4444');
}
// what a layout, a selection or a station built for itself goes back to the GPU when it is cleared; the shared
// geometries (G, OM.capsule), materials (M, AM, OM) and textures (TX) stay, since the next one draws with them
// again. A station's merged parts (userData.own) are its own geometry.
function release(root) {
  const shared = new Set(Object.values(TX));
  [M, OM].concat(Object.values(AM)).forEach((bag) => Object.values(bag).forEach((v) => {
    if (v && v.isMaterial) { shared.add(v); if (v.map) shared.add(v.map); } else if (v && typeof v === 'object') Object.values(v).forEach((m) => { if (m && m.isMaterial) shared.add(m); });
  }));
  root.traverse((o) => {
    if (o.isLight && o.dispose) o.dispose();
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
  const fit = (t, size) => { let s2 = String(t || ''); while (s2.length > 3 && g.measureText(s2).width > W - 40) s2 = s2.slice(0, -2); return s2 !== t ? s2.replace(/.$/, '…') : s2; };
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
  const c = document.createElement('canvas'); c.width = 512; c.height = 256; const g = c.getContext('2d');
  g.fillStyle = '#06100c'; g.fillRect(0, 0, 512, 256); g.strokeStyle = '#00ff88'; g.lineWidth = 5; g.strokeRect(3, 3, 506, 250);
  let v = 140; for (let i = 0; i < 16; i++) { const up = [1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 1, 0, 1, 1, 0, 1][i], o = v; v = Math.max(60, Math.min(210, v + (up ? -16 : 13))); g.fillStyle = up ? '#00ff88' : '#ff4444'; g.fillRect(24 + i * 29, Math.min(o, v), 17, Math.max(6, Math.abs(o - v))); g.fillRect(31 + i * 29, Math.min(o, v) - 10, 3, Math.abs(o - v) + 20); }
  g.fillStyle = '#00ff88'; g.font = '700 22px JetBrains Mono, monospace'; g.fillText('BASKET H2 · +1.1%', 22, 34);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}
function moodTex() {
  const c = document.createElement('canvas'); c.width = 512; c.height = 256; const g = c.getContext('2d');
  g.fillStyle = '#0b1016'; g.fillRect(0, 0, 512, 256); g.strokeStyle = '#18212b'; g.lineWidth = 5; g.strokeRect(3, 3, 506, 250);
  ['#00cfff', '#00ff88', '#3b82f6', '#ff4444'].forEach((col, i) => { g.fillStyle = col; g.fillRect(24 + i * 58, 28, 46, 46); });
  g.strokeStyle = '#7f93ad'; g.lineWidth = 3; g.strokeRect(24, 96, 220, 70); g.fillStyle = '#7f93ad'; g.fillRect(36, 110, 90, 10); g.fillStyle = '#18212b'; g.fillRect(36, 132, 160, 8);
  g.strokeStyle = '#00cfff'; g.setLineDash([10, 8]); g.strokeRect(270, 28, 214, 200);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

class Office3D {
  constructor(el, stage, tipFor) {
    geo(); omats();
    this.el = el; this.stage = stage; this.tipFor = tipFor;
    this.tip = stage.querySelector('.tip'); this.layer = stage.querySelector('.o3layer');
    this.sel = null; this.cells = {}; this.paths = {}; this.packets = []; this.rooms = {}; this.fitted = false; this.hover = null;
    this.mouse = new THREE.Vector2(); this.ray = new THREE.Raycaster();
    this.scene = new THREE.Scene(); this.scene.background = new THREE.Color(OFFICE.bg); this.scene.fog = new THREE.Fog(OFFICE.bg, 80, 170);
    this.camera = new THREE.PerspectiveCamera(30, 2, 0.3, 500);
    this.renderer = new THREE.WebGPURenderer({ antialias: false });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping; this.renderer.toneMappingExposure = 1.2;
    this.renderer.shadowMap.enabled = true; this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    el.appendChild(this.renderer.domElement);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    Object.assign(this.controls, { enableDamping: true, dampingFactor: 0.08, minDistance: 6, maxDistance: 110, maxPolarAngle: Math.PI * 0.43, minPolarAngle: 0.2,
      screenSpacePanning: false, zoomSpeed: 0.9, rotateSpeed: 0.55 });
    this.controls.addEventListener('start', () => { this.tw = null; });
    const S = this.scene;
    // white light, not blue: the colour in the room is what the room is doing
    S.add(new THREE.HemisphereLight(0xe2eaf2, 0x07090d, 1.4), new THREE.AmbientLight(0x1b222b, 0.8));
    this.sun = new THREE.DirectionalLight(0xf4f8fc, 2.3); this.sun.castShadow = true; this.sun.shadow.mapSize.set(2048, 2048);
    this.sun.shadow.normalBias = 0.02; this.sun.shadow.bias = -0.0005; S.add(this.sun); S.add(this.sun.target);
    const rim = new THREE.DirectionalLight(0x00cfff, 0.3); rim.position.set(30, 14, -30); S.add(rim);
    S.add(starField(1400, 230, 60, 0.75));
    // far behind the floor, the faint green of the Universe it floats in
    [[0x00ff88, 0.045, [-115, -75, -95], 150], [0x00cfff, 0.03, [-55, -95, -150], 120], [0x00ff88, 0.025, [55, -105, -125], 100]].forEach(([c, o, p, s]) => {
      const sp = glowSprite(c, o, s); sp.material.fog = false; sp.position.set(p[0], p[1], p[2]); S.add(sp);
    });
    this.world = new THREE.Group(); S.add(this.world);
    this.pk = new THREE.Group(); S.add(this.pk);
    this.clock = new THREE.Clock();
    this.bind();
    this.renderer.init().then(() => {
      try { this.post = new Post(this.renderer, this.scene, this.camera, 0.55, 0.4, 0.82); } catch (e) { this.post = null; }
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

  layout(opts) {
    const S = CO.S, L = CO.iso, born = opts && opts.born;
    this.shapeKey = this.shape();
    const cells = { hub: L.HUB, audit: L.AUDIT }, used = {};
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
    // The floor: a slab under every room (the Manager's, the audit and the free lot included), so a corner of the plan
    // with no room is open space, and the office floats. Cymetica green runs round its outside only, a green glow
    // under it. The fit frames these slabs, not the plan's whole square.
    const pad = 0.5, T = 0.75, have = {}, kc = (x, y) => x + ',' + y;
    all.forEach((c) => { have[kc(c[0], c[1])] = 1; });
    const top = new THREE.MeshStandardMaterial({ color: 0x090c11, roughness: 0.5, metalness: 0.45 }), edgeM = emis('#00ff88', 1.25), edgeLow = emis('#00ff88', 0.35);
    this.corners = [];
    all.forEach((c) => {
      const s = new THREE.Mesh(G.box, [OM.plinth, OM.plinth, top, OM.plinth, OM.plinth, OM.plinth]);
      s.scale.set(RS + 2 * pad + 0.02, T, RS + 2 * pad + 0.02); s.position.copy(this.V(c[0] + RS / 2, c[1] + RS / 2, -T / 2)); s.receiveShadow = true; W.add(s);
      const glow = new THREE.Mesh(G.plane, new THREE.MeshBasicMaterial({ map: glowTex(), color: 0x00ff88, transparent: true, opacity: 0.06, blending: THREE.AdditiveBlending, depthWrite: false, fog: false }));
      glow.scale.set(RS * 1.9, RS * 1.9, 1); glow.rotation.x = -Math.PI / 2; glow.position.copy(this.V(c[0] + RS / 2, c[1] + RS / 2, -T - 0.6)); W.add(glow);
      const x0 = c[0] - pad, y0 = c[1] - pad, x1 = c[0] + RS + pad, y1 = c[1] + RS + pad;
      // a side is the outside when no room's slab meets it there
      [[x0, y0, x1, y0, !have[kc(c[0], c[1] - 8)]], [x0, y1, x1, y1, !have[kc(c[0], c[1] + 8)]], [x0, y0, x0, y1, !have[kc(c[0] - 8, c[1])]], [x1, y0, x1, y1, !have[kc(c[0] + 8, c[1])]]].forEach(([ax, ay, bx, by, out]) => {
        if (!out) return;
        const len = Math.hypot(bx - ax, by - ay) + 0.06, along = ax === bx;
        [[0, 0.07, edgeM], [-T, 0.05, edgeLow]].forEach(([z, t, m]) => { const e = new THREE.Mesh(G.box, m); e.scale.set(along ? t : len, t, along ? len : t); e.position.copy(this.V((ax + bx) / 2, (ay + by) / 2, z)); W.add(e); });
      });
      [[x0, y0], [x1, y0], [x0, y1], [x1, y1]].forEach(([x, y]) => { this.corners.push(this.V(x, y, -T), this.V(x, y, 1.35)); });
    });
    // corridors: from every room's door to the Manager's, the 2D office's own routes
    this.paths = {}; this.conduits = {};
    Object.keys(cells).forEach((k) => {
      if (k === 'hub' || k === 'lot') return;
      const p = L.route(all, cells[k], L.HUB); if (!p) return;
      this.paths[k] = p;
      const mat = emis('#00ff88', 0.22), segs = [];
      for (let i = 1; i < p.length; i++) {
        const a = p[i - 1], b = p[i], len = Math.hypot(b[0] - a[0], b[1] - a[1]); if (len < 0.01) continue;
        const base = new THREE.Mesh(G.box, OM.dark); base.scale.set(len + 0.24, 0.03, 0.24);
        const line = new THREE.Mesh(G.box, mat); line.scale.set(len + 0.06, 0.035, 0.06);
        [base, line].forEach((m) => { m.position.copy(this.V((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, m === base ? 0.015 : 0.03)); m.rotation.y = -Math.atan2(b[1] - a[1], b[0] - a[0]); W.add(m); });
        segs.push(line);
      }
      this.conduits[k] = { mat, segs };
    });
    const sz = this.size;
    this.sun.position.copy(new THREE.Vector3(-sz * 0.9, sz * 1.5, sz * 0.7)); this.sun.target.position.set(0, 0, 0);
    Object.assign(this.sun.shadow.camera, { left: -sz * 0.8, right: sz * 0.8, top: sz * 0.8, bottom: -sz * 0.8, near: 1, far: sz * 4 }); this.sun.shadow.camera.updateProjectionMatrix();
    // rooms
    Object.keys(cells).forEach((k) => {
      const c = cells[k], g = new THREE.Group(); W.add(g);
      const room = { key: k, g, x0: c[0], y0: c[1], agents: [], screens: [], mons: [], born: born && k === 'd' + born };
      this.rooms[k] = room;
      if (k === 'lot') return this.lotRoom(room);
      this.shell(room);
      if (k === 'hub') this.hubRoom(room); else if (k === 'audit') this.auditRoom(room); else this.deptRoom(room, CO.dept(+k.slice(1)));
      const hit = new THREE.Mesh(G.box, M.hit); hit.scale.set(RS, 1.6, RS); hit.position.copy(this.V(c[0] + RS / 2, c[1] + RS / 2, 0.8)); hit.userData.key = k; g.add(hit); this.hits.push(hit);
      if (room.born) { g.scale.set(1, 0.01, 1); room.grow = performance.now(); }
    });
    this.selRing = new THREE.Group(); W.add(this.selRing);
    this.update();
    if (!this.fitted) { this.fit(false); }
  }
  shell(r) {
    const { g, x0, y0 } = r, RS = CO.iso.RS;
    this.box(g, x0, y0, 0, RS, RS, 0.1, OM.tile);
    r.glow = new THREE.Mesh(G.plane, new THREE.MeshBasicMaterial({ map: radialTex('255,255,255', 0.9), transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false, color: 0x00cfff }));
    r.glow.scale.set(RS * 1.15, RS * 1.15, 1); r.glow.rotation.x = -Math.PI / 2; r.glow.position.copy(this.V(x0 + RS / 2, y0 + RS / 2, 0.11)); g.add(r.glow);
    // glass back walls, mullions and a lit top edge in the room's colour
    this.box(g, x0, y0, 0.1, RS, 0.08, 1.15, OM.glass, false);
    this.box(g, x0, y0, 0.1, 0.08, RS, 1.15, OM.glass, false);
    for (let m = 1; m < 4; m++) { this.box(g, x0 + m * RS / 4 - 0.03, y0, 0.1, 0.06, 0.1, 1.15, OM.frame); this.box(g, x0, y0 + m * RS / 4 - 0.03, 0.1, 0.1, 0.06, 1.15, OM.frame); }
    // a lamp over the room in the colour of what it is doing: it lights the desks, the people and the floor
    r.lamp = new THREE.PointLight(OFFICE.lamp, 3, 9, 1.4); r.lamp.position.copy(this.V(x0 + RS / 2, y0 + RS / 2, 2.6)); g.add(r.lamp);
    r.edgeM = emis('#7f93ad', 0.4); r.sillM = emis('#7f93ad', 0.15);
    this.box(g, x0, y0, 1.25, RS, 0.07, 0.05, r.edgeM, false); this.box(g, x0, y0, 1.25, 0.07, RS, 0.05, r.edgeM, false);
    this.box(g, x0 + RS - 0.04, y0, 0.1, 0.04, RS, 0.04, r.sillM, false); this.box(g, x0, y0 + RS - 0.04, 0.1, RS, 0.04, 0.04, r.sillM, false);
  }
  // a wall screen on the back wall: what runs now, or why it waits
  wallScreen(r, u0, u1) {
    const s = screen(u1 - u0, 0.74), mat = new THREE.MeshBasicMaterial({ map: s.tex, toneMapped: false });
    const m = new THREE.Mesh(G.plane, mat); m.scale.set(u1 - u0, 0.74, 1); m.position.copy(this.V(r.x0 + (u0 + u1) / 2, r.y0 + 0.13, 0.73)); r.g.add(m);
    r.wall = s; return s;
  }
  kanban(r) {
    const s = screen(4.9, 0.72), mat = new THREE.MeshBasicMaterial({ map: s.tex, toneMapped: false });
    const m = new THREE.Mesh(G.plane, mat); m.scale.set(4.9, 0.72, 1); m.rotation.y = Math.PI / 2; m.position.copy(this.V(r.x0 + 0.13, r.y0 + 3.45, 0.72)); r.g.add(m);
    r.kb = s;
  }
  desk(r, x, y, i) {
    const g = r.g;
    this.box(g, x, y, 0, 1.9, 0.9, 0.42, OM.desk); this.box(g, x - 0.02, y - 0.02, 0.42, 1.94, 0.94, 0.03, OM.deskTop, false);
    this.box(g, x + 0.6, y + 0.48, 0.45, 0.7, 0.22, 0.02, OM.dark, false);
    this.box(g, x + 0.88, y + 0.17, 0.45, 0.14, 0.06, 0.12, OM.frame, false);
    this.box(g, x + 0.5, y + 0.12, 0.55, 0.9, 0.06, 0.52, OM.dark);
    const scr = new THREE.MeshBasicMaterial({ color: new THREE.Color(OFFICE.mon) });
    const face = new THREE.Mesh(G.plane, scr); face.scale.set(0.84, 0.46, 1); face.position.copy(this.V(x + 0.95, y + 0.185, 0.81)); g.add(face);
    r.mons[i] = scr;
    this.box(g, x + 0.7, y + 1.08, 0, 0.5, 0.45, 0.22, OM.plinth);
  }
  agent(r, x, y, i, label, head) {
    const g = new THREE.Group(); g.position.copy(this.V(x, y, 0.1)); r.g.add(g);
    const body = new THREE.MeshStandardMaterial({ color: OFFICE.agent, emissive: OFFICE.agentE, emissiveIntensity: 0.6, roughness: 0.5, metalness: 0.2 });
    const b = new THREE.Mesh(OM.capsule, body); b.position.y = 0.42; b.castShadow = true; g.add(b);
    const h = new THREE.Mesh(G.sphere, head ? new THREE.MeshStandardMaterial({ color: head, roughness: 0.6 }) : OM.head); h.scale.setScalar(0.15); h.position.y = 0.86; h.castShadow = true; g.add(h);
    const ringM = emis('#00cfff', 0); const ring = new THREE.Mesh(G.ring, ringM); ring.rotation.x = Math.PI / 2; ring.scale.setScalar(0.34); ring.position.y = 0.02; g.add(ring);
    const el = document.createElement('div'); el.className = 'a3'; el.textContent = label; this.layer.appendChild(el);
    const a = { g, body, b, h, ring, ringM, el, home: g.position.clone(), phase: (i + r.x0 * 0.37) % 6.28, key: r.key + ':' + i, room: r, label };
    r.agents.push(a); return a;
  }
  plate(r, cls) {
    const el = document.createElement('div'); el.className = 'p3' + (cls ? ' ' + cls : ''); el.setAttribute('data-key', r.key); this.layer.appendChild(el);
    el.addEventListener('click', () => CO.emit('office:click', r.key));
    el.addEventListener('pointerenter', () => this.setHover(r.key)); el.addEventListener('pointerleave', () => this.setHover(null));
    r.plate = el; r.plateAt = this.V(r.x0 + 4.4, r.y0 + 5.75, 1.35); return el;
  }
  deptRoom(r, d) {
    const k = d.key; let u1 = 6.2;
    if (k === 'trading_desk') { u1 = 4.2; this.boardTex(r, 4.4, 6.75, candleTex()); }
    else if (k === 'design') { u1 = 4.6; this.boardTex(r, 4.8, 6.75, moodTex()); }
    else if (k === 'development' || k === 'testing' || k === 'testing_lab') u1 = 5.4;
    this.wallScreen(r, 1.1, u1); this.kanban(r);
    const g = r.g, x0 = r.x0, y0 = r.y0;
    if (k === 'development') this.racks(r, x0 + 5.7, y0 + 0.25, 2);
    else if (k === 'testing') this.devices(r, x0 + 5.65, y0 + 0.28);
    else if (k === 'testing_lab') this.flasks(r, x0 + 5.5, y0 + 0.3);
    else if (k === 'custom') this.box(g, x0 + 5.6, y0 + 0.2, 0.1, 1.05, 0.12, 1.15, OM.frame);
    const ex = d.experts.slice(0, 3), xs = ex.length === 1 ? [2.55] : ex.length === 2 ? [1.0, 3.75] : [0.55, 2.6, 4.65];
    ex.forEach((e, i) => this.desk(r, x0 + xs[i], y0 + 1.75, i));
    ex.forEach((e, i) => this.agent(r, x0 + xs[i] + 0.95, y0 + 3.05, i, CO.expertName(e)));
    this.terminal(r, x0 + 0.35, y0 + 4.0, d.link || CO.DEPT_LINK[k] || CO.DEPT_LINK.custom);
    this.plant(r, x0 + 0.3, y0 + 6.2);
    this.plate(r);
  }
  boardTex(r, u0, u1, tex) {
    const m = new THREE.Mesh(G.plane, new THREE.MeshBasicMaterial({ map: tex, toneMapped: false })); m.scale.set(u1 - u0, 0.74, 1); m.position.copy(this.V(r.x0 + (u0 + u1) / 2, r.y0 + 0.13, 0.73)); r.g.add(m);
  }
  terminal(r, x, y, link) {
    const g = r.g;
    this.box(g, x, y, 0, 1.2, 0.8, 0.42, OM.desk);
    this.box(g, x + 0.5, y + 0.2, 0.42, 0.2, 0.1, 0.12, OM.frame, false);
    this.box(g, x + 0.08, y + 0.12, 0.54, 1.04, 0.08, 0.74, OM.dark);
    const scr = new THREE.MeshBasicMaterial({ map: this.pcTex(), toneMapped: false });
    const face = new THREE.Mesh(G.plane, scr); face.scale.set(0.98, 0.68, 1); face.position.copy(this.V(x + 0.6, y + 0.205, 0.91)); g.add(face);
    const hit = new THREE.Mesh(G.box, M.hit); hit.scale.set(1.3, 1.3, 1.0); hit.position.copy(this.V(x + 0.6, y + 0.4, 0.65)); hit.userData.pc = link; g.add(hit);
    this.pcs.push(hit); r.pcFace = scr;
  }
  pcTex() {
    if (this._pc) return this._pc;
    const c = document.createElement('canvas'); c.width = 256; c.height = 176; const g = c.getContext('2d');
    g.fillStyle = '#06261f'; g.fillRect(0, 0, 256, 176); g.strokeStyle = '#00ff88'; g.lineWidth = 8; g.strokeRect(4, 4, 248, 168);
    g.fillStyle = '#00ff88'; g.font = '700 96px JetBrains Mono, monospace'; g.textAlign = 'center'; g.textBaseline = 'middle'; g.fillText('↗', 128, 92);
    const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; this._pc = t; return t;
  }
  plant(r, x, y) {
    this.box(r.g, x, y, 0, 0.42, 0.42, 0.34, OM.frame);
    const p = this.V(x + 0.21, y + 0.21, 0.34);
    [[-0.08, 0.25, 0.2], [0.08, 0.32, 0.18], [0, 0.42, 0.15]].forEach(([dx, dy, s]) => { const m = new THREE.Mesh(G.sphere, M.leaf); m.scale.set(s, s * 1.2, s); m.position.set(p.x + dx, p.y + dy, p.z); m.castShadow = true; r.g.add(m); });
  }
  racks(r, x, y, n) {
    for (let i = 0; i < n; i++) {
      const rx = x + i * 0.55; this.box(r.g, rx, y, 0.1, 0.5, 0.55, 1.45, OM.dark);
      for (let k = 0; k < 8; k++) { const col = ['#00ff88', '#00cfff', '#3b82f6', '#00ff88'][(i + k) % 4]; const m = new THREE.Mesh(G.box, amat(col).glow); m.scale.set(0.07, 0.035, 0.01); m.position.copy(this.V(rx + 0.12 + (k % 2) * 0.22, y + 0.56, 0.35 + Math.floor(k / 2) * 0.3)); m.userData.blink = (i * 7 + k * 3) % 11; r.g.add(m); (r.leds = r.leds || []).push(m); }
    }
  }
  devices(r, x, y) {
    this.box(r.g, x, y, 0.1, 1.1, 0.45, 1.25, OM.dark);
    for (let s = 0; s < 3; s++) for (let k = 0; k < 3; k++) { const col = ['#00cfff', '#00ff88', '#3b82f6'][(s + k) % 3]; const m = new THREE.Mesh(G.plane, amat(col).glow); m.scale.set(0.2, 0.26, 1); m.position.copy(this.V(x + 0.18 + k * 0.36, y + 0.46, 0.4 + s * 0.38)); r.g.add(m); }
  }
  flasks(r, x, y) {
    this.box(r.g, x, y, 0, 1.3, 0.6, 0.45, OM.desk);
    [[0.25, '#00cfff', 0.5], [0.65, '#00ff88', 0.36], [1.02, '#00cfff', 0.42]].forEach(([u, col, h]) => {
      const glass = new THREE.Mesh(G.cyl, OM.glass); glass.scale.set(0.12, h, 0.12); glass.position.copy(this.V(x + u, y + 0.3, 0.45 + h / 2)); r.g.add(glass);
      const liq = new THREE.Mesh(G.cyl, amat(col).soft); liq.scale.set(0.1, h * 0.6, 0.1); liq.position.copy(this.V(x + u, y + 0.3, 0.45 + h * 0.3)); r.g.add(liq);
    });
  }
  hubRoom(r) {
    const g = r.g;
    this.racks(r, r.x0 + 0.45, r.y0 + 0.3, 3);
    const s = screen(3.4, 0.74), m = new THREE.Mesh(G.plane, new THREE.MeshBasicMaterial({ map: s.tex, toneMapped: false })); m.scale.set(3.4, 0.74, 1); m.position.copy(this.V(r.x0 + 4.7, r.y0 + 0.13, 0.73)); g.add(m); r.bars = s;
    this.kanban(r);
    const c = this.V(11.6, 11.4, 0), cy = OM.cyan;
    const ped = new THREE.Mesh(G.cyl, OM.plinth); ped.scale.set(1.55, 0.45, 1.55); ped.position.set(c.x, 0.32, c.z); ped.castShadow = true; ped.receiveShadow = true; g.add(ped);
    const lip = new THREE.Mesh(G.ringT, cy.rim); lip.scale.setScalar(1.55); lip.rotation.x = Math.PI / 2; lip.position.set(c.x, 0.55, c.z); g.add(lip);
    const core = new THREE.Mesh(G.sphere, cy.glow); core.scale.setScalar(0.32); core.position.set(c.x, 1.2, c.z); g.add(core);
    const beam = new THREE.Mesh(G.beam, cy.beam); beam.scale.set(2.2, 3.4, 2.2); beam.position.set(c.x, 2.25, c.z); g.add(beam);
    r.holo = [1.35, 1.95, 2.55].map((y, i) => { const h = new THREE.Mesh(G.ringT, cy.rim); h.scale.setScalar(1.1 - i * 0.22); h.rotation.x = Math.PI / 2; h.position.set(c.x, y, c.z); g.add(h); return h; });
    r.core = core; r.coreAt = new THREE.Vector3(c.x, 3.2, c.z);
    const light = new THREE.PointLight(0x00cfff, 14, 12, 1.6); light.position.set(c.x, 1.8, c.z); g.add(light);
    this.agent(r, 11.7, 13.9, 0, 'Manager', 0xe6edf7);
    this.plant(r, r.x0 + 6.3, r.y0 + 0.4);
    this.plate(r, 'hubp'); r.plateAt = this.V(12.9 + 1.2, 14.25 + 0.5, 1.35);
    r.need = document.createElement('div'); r.need.className = 'p3need'; r.need.addEventListener('click', () => CO.emit('office:click', 'hub')); this.layer.appendChild(r.need);
  }
  auditRoom(r) {
    this.wallScreen(r, 1.1, 5.0);
    this.desk(r, r.x0 + 2.2, r.y0 + 1.8, 0);
    this.agent(r, r.x0 + 3.15, r.y0 + 3.1, 0, 'Supervisor');
    this.plant(r, r.x0 + 0.3, r.y0 + 6.2);
    this.plate(r, 'auditp');
  }
  lotRoom(r) {
    const RS = CO.iso.RS, g = r.g, c = this.V(r.x0 + RS / 2, r.y0 + RS / 2, 0.05);
    const dash = emis('#00cfff', 0.55);
    for (let a = 0; a < RS; a += 0.7) {
      [[r.x0 + a, r.y0], [r.x0 + a, r.y0 + RS]].forEach(([x, y]) => this.box(g, x, y - 0.03, 0.04, 0.4, 0.06, 0.03, dash, false));
      [[r.x0, r.y0 + a], [r.x0 + RS, r.y0 + a]].forEach(([x, y]) => this.box(g, x - 0.03, y, 0.04, 0.06, 0.4, 0.03, dash, false));
    }
    // a ring of light lying on the free floor, breathing; the label above it says what it is for
    r.plus = new THREE.Mesh(G.ringT, OM.cyan.rim); r.plus.scale.setScalar(2.1); r.plus.rotation.x = Math.PI / 2; r.plus.position.set(c.x, 0.12, c.z); g.add(r.plus);
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
      if (this.conduits['d' + d.id]) { const cm = this.conduits['d' + d.id].mat; cm.emissive.set(v.status === 'working' ? 0x00cfff : 0x00ff88); cm.emissiveIntensity = v.status === 'working' ? 1.6 : 0.22; }
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
    this.paused = S.company.status === 'paused';
    this.drawSel();
  }
  // a room in the colour of what it does: working cyan and waiting red light the room; up next and idle keep a
  // slate edge under plain white light (up next says itself on the plate and the wall screen)
  tint(r, st) {
    if (r.st === st) return; r.st = st;
    // a room at rest keeps a dim green edge: green is the office's structure, cyan and red what its rooms do
    const lit = st === 'working' || st === 'waiting', c = new THREE.Color(lit ? STC[st] : 0x00ff88);
    if (r.edgeM) { r.edgeM.emissive.copy(c); r.edgeM.emissiveIntensity = lit ? 1.5 : st === 'queued' ? 0.4 : 0.26; }
    if (r.sillM) { r.sillM.emissive.copy(c); r.sillM.emissiveIntensity = lit ? 0.6 : 0.1; }
    if (r.glow) { r.glow.material.color.copy(c); r.glowBase = st === 'working' ? 0.3 : st === 'waiting' ? 0.26 : 0; }
    if (r.lamp) { r.lamp.color.copy(lit ? c : new THREE.Color(OFFICE.lamp)); r.lamp.intensity = st === 'working' ? 9 : st === 'waiting' ? 7 : 3.2; }
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
    const dir = new THREE.Vector3().setFromSpherical(new THREE.Spherical(1, 0.86, Math.PI / 4)), cam = this.camera.clone(), pts = this.corners || [];
    const tgt = new THREE.Vector3(); pts.forEach((p) => tgt.add(p)); if (pts.length) tgt.divideScalar(pts.length); tgt.y = 0;
    const fits = (d, t) => { cam.position.copy(t).addScaledVector(dir, d); cam.lookAt(t); cam.updateMatrixWorld(); return pts.every((p) => { const v = p.clone().project(cam); return Math.abs(v.x) < 0.93 && v.y < 0.82 && v.y > -0.95; }); };
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
    this.tween(tgt.clone().add(dir.multiplyScalar(tight ? 20 : 24)), tgt, 750);
  }
  tween(pos, tgt, ms, done) {
    if (!ms) { this.camera.position.copy(pos); this.controls.target.copy(tgt); this.controls.update(); this.tw = null; if (done) done(); return; }
    this.tw = { p0: this.camera.position.clone(), t0: this.controls.target.clone(), p1: pos.clone(), t1: tgt.clone(), s: performance.now(), ms, done };
  }
  resize() {
    const w = this.el.clientWidth, h = this.el.clientHeight; if (!w || !h) return;
    this.camera.aspect = w / h; this.camera.updateProjectionMatrix(); this.renderer.setSize(w, h, false);
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
    Object.values(this.rooms).forEach((r) => {
      if (r.grow) { const k = Math.min(1, (now - r.grow) / 1200), e = 1 - Math.pow(1 - k, 3); r.g.scale.set(1, Math.max(0.01, e), 1); if (k >= 1) r.grow = 0; }
      if (r.glow) r.glow.material.opacity = (r.glowBase || 0) * (r.st === 'working' ? 0.75 + 0.25 * Math.sin(t * 2.4 + r.x0) : 1);
      if (r.leds) r.leds.forEach((m, i) => { m.visible = ((Math.floor(t * 3 + m.userData.blink)) % 3) !== 0; });
      if (r.holo) { r.holo.forEach((hh, i) => { hh.rotation.z = t * (0.6 + i * 0.35) * (i % 2 ? -1 : 1); hh.position.y = 1.35 + i * 0.6 + Math.sin(t * 1.3 + i) * 0.05; }); r.core.position.y = 1.2 + Math.sin(t * 1.7) * 0.06; }
      if (r.plus) r.plus.scale.setScalar(2.1 + Math.sin(t * 1.6) * 0.1);
      r.agents.forEach((a) => {
        if (a.walk) {
          const W2 = a.walk, f = (now - W2.t0) / W2.dur;
          if (a.working) { a.walk = null; a.g.position.copy(a.home); }
          else if (f < 1) a.g.position.lerpVectors(W2.from, W2.to, f < 0.5 ? 2 * f * f : 1 - Math.pow(-2 * f + 2, 2) / 2);
          else if (now < W2.t0 + W2.dur + W2.stay) a.g.position.copy(W2.to);
          else if (!W2.back) { W2.back = true; W2.from = W2.to.clone(); W2.to = a.home.clone(); W2.t0 = now; W2.stay = 0; }
          else { a.walk = null; a.g.position.copy(a.home); }
        }
        a.b.position.y = 0.42 + (a.working ? Math.abs(Math.sin(t * 7 + a.phase)) * 0.035 : 0);
        a.body.color.set(a.working ? 0x00cfff : OFFICE.agent); a.body.emissiveIntensity = a.working ? 1.1 : 0.5; a.body.emissive.set(a.working ? 0x00506a : OFFICE.agentE);
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
      r.agents.forEach((a) => { a.el.classList.toggle('on', named); if (named) show(a.el, a.g.position.clone().add(new THREE.Vector3(0, 1.22, 0))); });
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
  CO.U3 = (gl2 || navigator.gpu) ? { ok: true, gpu: !!navigator.gpu, universe: (el, stage, h) => new Universe3D(el, stage, h), office: (el, stage, tipFor) => new Office3D(el, stage, tipFor), preview, thumbs, THREE, geo, makeStation, SKIN, amat }
    : { failed: true, why: 'no WebGPU and no WebGL2' };
  window.dispatchEvent(new Event('co3d'));
})();
