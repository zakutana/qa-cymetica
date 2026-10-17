/* The /company mockup's 3D engine: the Universe as a real city floating in space. three.js with its
 * WebGPU renderer (WebGL2 where a browser has no WebGPU), bloom on everything that glows, an orbit camera,
 * ONE FLOOR PER DEPARTMENT, a floor lit while its department works. Banners and the tooltip are HTML over the
 * canvas, so they stay sharp and clickable. If the renderer cannot start, the page keeps the flat map. */
import * as THREE from 'three/webgpu';
import { pass, renderOutput } from 'three/tsl';
import { bloom } from 'three/addons/tsl/display/BloomNode.js';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';

const CO = window.CO;
const PS = 6, ST = 2, CELL = PS + ST, GRID = 5, CITY = GRID * CELL - ST, OFF = CITY / 2, FH = 0.82, PLAT = CITY + 8;
const CORE = [2, 2], MINE = [3, 2];

/* ---------------- shared geometry and materials ---------------- */
const G = {}, M = {}, AM = {};
function geo() {
  if (G.box) return;
  G.box = new THREE.BoxGeometry(1, 1, 1);
  G.cyl = new THREE.CylinderGeometry(1, 1, 1, 40);
  G.cone = new THREE.ConeGeometry(1, 1, 32);
  G.sphere = new THREE.SphereGeometry(1, 32, 16);
  G.hemi = new THREE.SphereGeometry(1, 48, 24, 0, Math.PI * 2, 0, Math.PI / 2);
  G.hemiWire = new THREE.SphereGeometry(1, 16, 6, 0, Math.PI * 2, 0, Math.PI / 2);
  G.plane = new THREE.PlaneGeometry(1, 1);
  G.beam = new THREE.CylinderGeometry(0.05, 0.3, 1, 20, 1, true);
  G.skirt = new THREE.CylinderGeometry(1, 1.5, 1, 28, 1, true);
  G.ring = new THREE.TorusGeometry(1, 0.016, 8, 140);
  G.ringT = new THREE.TorusGeometry(1, 0.03, 8, 120);
  M.wall = new THREE.MeshStandardMaterial({ color: 0x1b2e4c, roughness: 0.6, metalness: 0.3 });
  M.wall2 = new THREE.MeshStandardMaterial({ color: 0x223858, roughness: 0.55, metalness: 0.32 });
  M.roof = new THREE.MeshStandardMaterial({ color: 0x23385a, roughness: 0.6, metalness: 0.25 });
  M.pad = new THREE.MeshStandardMaterial({ color: 0x101c30, roughness: 0.75, metalness: 0.2 });
  M.metal = new THREE.MeshStandardMaterial({ color: 0x2f4468, roughness: 0.35, metalness: 0.75 });
  M.hull = new THREE.MeshStandardMaterial({ color: 0x2a3f62, roughness: 0.38, metalness: 0.55 });
  M.hull2 = new THREE.MeshStandardMaterial({ color: 0x223555, roughness: 0.4, metalness: 0.55 });
  M.dark = new THREE.MeshStandardMaterial({ color: 0x0a111d, roughness: 0.4, metalness: 0.7 });
  M.planet = new THREE.MeshStandardMaterial({ color: 0x1a2c48, roughness: 0.55, metalness: 0.25 });
  M.leaf = new THREE.MeshStandardMaterial({ color: 0x0f7a4c, roughness: 0.85, emissive: 0x00ff88, emissiveIntensity: 0.06 });
  M.trunk = new THREE.MeshStandardMaterial({ color: 0x1e3050, roughness: 0.9 });
  M.win = new THREE.MeshBasicMaterial({ color: 0xffffff });
  M.hit = new THREE.MeshBasicMaterial({ visible: false });
}
// one set per colour: what glows in it, from a lamp to a beam of light
function amat(hex) {
  if (AM[hex]) return AM[hex];
  const c = new THREE.Color(hex);
  AM[hex] = {
    c, hex,
    rim: new THREE.MeshStandardMaterial({ color: 0x000000, emissive: c, emissiveIntensity: 1.3, roughness: 1 }),
    soft: new THREE.MeshStandardMaterial({ color: 0x000000, emissive: c, emissiveIntensity: 0.7, roughness: 1 }),
    glow: new THREE.MeshBasicMaterial({ color: c.clone().multiplyScalar(4) }),
    glass: new THREE.MeshStandardMaterial({ color: c.clone().multiplyScalar(0.55), transparent: true, opacity: 0.1, roughness: 0.05, metalness: 0.2, emissive: c, emissiveIntensity: 0.035, depthWrite: false }),
    wire: new THREE.MeshBasicMaterial({ color: c.clone().multiplyScalar(0.85), wireframe: true, transparent: true, opacity: 0.45 }),
    beam: new THREE.MeshBasicMaterial({ color: c.clone().multiplyScalar(1.3), transparent: true, opacity: 0.14, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.DoubleSide }),
    atmo: new THREE.MeshBasicMaterial({ color: c.clone().multiplyScalar(0.9), transparent: true, opacity: 0.12, blending: THREE.AdditiveBlending, depthWrite: false, side: THREE.BackSide }),
    fin: new THREE.MeshStandardMaterial({ color: 0x0a111d, emissive: c, emissiveIntensity: 0.55, roughness: 0.6 }),
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
function rng(seed) {
  let s = Math.abs(Math.floor(seed * 9301 + 49297)) % 233280 || 1;
  return () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
}
const floorsOf = (c) => Math.max(1, Math.min(8, (c.departments || []).length || 1));
const fpOf = (n) => n <= 2 ? 2.3 : n <= 5 ? 2.9 : 3.5;

/* ---------------- a building: its parts, its windows, its floors ---------------- */
class Building {
  constructor(acc, seed) {
    this.g = new THREE.Group(); this.A = amat(acc); this.R = rng(seed); this.phase = (seed % 97) / 7;
    this.w = []; this.beacons = []; this.anim = []; this.top = 2; this.busy = false;
  }
  part(geom, mat, sx, sy, sz, x, y, z, shadow = true) {
    const m = new THREE.Mesh(geom, mat); m.scale.set(sx, sy, sz); m.position.set(x, y, z);
    if (shadow) { m.castShadow = true; m.receiveShadow = true; }
    this.g.add(m); return m;
  }
  box(w, h, d, x, y, z, mat, shadow) { return this.part(G.box, mat, w, h, d, x, y, z, shadow); }
  cyl(r, h, x, y, z, mat, shadow) { return this.part(G.cyl, mat, r, h, r, x, y, z, shadow); }
  // a window: where, which way it faces, its size, its floor, and whether its light is on by default
  win(x, y, z, ry, w, h, f, lit) { this.w.push({ x, y, z, ry, w, h, f, lit }); }
  beacon(x, y, z, r) { const m = this.part(G.sphere, this.A.glow, r, r, r, x, y, z, false); this.beacons.push(m); return m; }
  ringFlat(r, y, mat) { const m = new THREE.Mesh(G.ring, mat); m.scale.setScalar(r); m.rotation.x = Math.PI / 2; m.position.y = y; this.g.add(m); return m; }
  rimSquare(s, y, mat, dashed) {
    const t = 0.05, h = s / 2;
    const edge = (len, f) => {
      if (!dashed) return f(len, 0);
      for (let a = -len / 2; a < len / 2 - 0.2; a += 0.75) f(Math.min(0.45, len / 2 - a), a + 0.225);
    };
    edge(s + t, (l, o) => this.box(l, t, t, o, y, h, mat, false)); edge(s + t, (l, o) => this.box(l, t, t, o, y, -h, mat, false));
    edge(s + t, (l, o) => this.box(t, t, l, h, y, o, mat, false)); edge(s + t, (l, o) => this.box(t, t, l, -h, y, o, mat, false));
  }
  faceWins(f, w, d, y, h, step, lit) {
    const ww = 0.2, wh = Math.min(0.46, h * 0.56), R = this.R;
    const put = (len, place) => { const m = Math.max(1, Math.floor((len - 0.25) / step)), s = len / m; for (let i = 0; i < m; i++) place(-len / 2 + s * (i + 0.5)); };
    put(w, (x) => this.win(x, y, d / 2 + 0.014, 0, ww, wh, f, R() < lit));
    put(w, (x) => this.win(x, y, -d / 2 - 0.014, Math.PI, ww, wh, f, R() < lit));
    put(d, (z) => this.win(w / 2 + 0.014, y, z, Math.PI / 2, ww, wh, f, R() < lit));
    put(d, (z) => this.win(-w / 2 - 0.014, y, z, -Math.PI / 2, ww, wh, f, R() < lit));
  }
  ringWins(f, r, y, h, step, lit, ww = 0.17) {
    const m = Math.max(6, Math.round(2 * Math.PI * r / step));
    for (let i = 0; i < m; i++) { const t = i / m * Math.PI * 2; this.win(Math.cos(t) * (r + 0.014), y, Math.sin(t) * (r + 0.014), Math.PI / 2 - t, ww, h, f, this.R() < lit); }
  }
  // all the windows as one instanced mesh, coloured per window: off, on, or the whole floor at work
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

const SKIN = {};
SKIN.tower = (b, n) => {
  const fp = fpOf(n), half = fp / 2;
  b.box(fp + 0.6, 0.22, fp + 0.6, 0, 0.11, 0, M.pad);
  let y = 0.22;
  for (let f = 0; f < n; f++) {
    const h = FH - 0.07;
    b.box(fp, h, fp, 0, y + h / 2, 0, M.wall);
    b.box(fp + 0.12, 0.05, fp + 0.12, 0, y + h + 0.025, 0, M.roof);
    b.faceWins(f, fp, fp, y + h / 2, h, 0.38, 0.42);
    y += FH;
  }
  for (const [sx, sz] of [[1, 1], [1, -1], [-1, 1], [-1, -1]]) b.box(0.07, y - 0.22, 0.07, sx * (half + 0.03), 0.22 + (y - 0.22) / 2, sz * (half + 0.03), b.A.rim, false);
  b.box(fp * 0.6, 0.36, fp * 0.6, 0, y + 0.18, 0, M.roof);
  b.cyl(0.03, 1.3, 0, y + 0.36 + 0.65, 0, M.metal, false);
  b.beacon(0, y + 0.36 + 1.33, 0, 0.1);
  b.top = y + 1.9;
};
SKIN.dome = (b, n) => {
  const r = fpOf(n) / 2 + 0.55;
  b.cyl(r + 0.35, 0.2, 0, 0.1, 0, M.pad);
  let y = 0.2;
  for (let f = 0; f < n; f++) {
    const h = FH - 0.06;
    b.cyl(r, h, 0, y + h / 2, 0, M.wall);
    b.cyl(r + 0.05, 0.05, 0, y + h + 0.025, 0, M.roof, false);
    b.ringWins(f, r, y + h / 2, h * 0.52, 0.42, 0.45);
    y += FH;
  }
  b.cyl(r, 0.04, 0, y + 0.02, 0, M.roof, false);
  const lip = new THREE.Mesh(G.ringT, b.A.rim); lip.scale.setScalar(r + 0.03); lip.rotation.x = Math.PI / 2; lip.position.y = y + 0.03; b.g.add(lip);
  const dome = new THREE.Mesh(G.hemi, b.A.glass); dome.scale.set(r, r * 0.95, r); dome.position.y = y; b.g.add(dome);
  const wire = new THREE.Mesh(G.hemiWire, b.A.wire); wire.scale.set(r * 1.006, r * 0.956, r * 1.006); wire.position.y = y; b.g.add(wire);
  const core = b.part(G.sphere, b.A.soft, r * 0.28, r * 0.28, r * 0.28, 0, y + r * 0.34, 0, false);
  b.anim.push((t) => { core.position.y = y + r * 0.34 + Math.sin(t * 1.3 + b.phase) * 0.05; wire.rotation.y = t * 0.08; });
  b.beacon(0, y + r * 0.95 + 0.06, 0, 0.08);
  b.top = y + r * 0.95 + 0.55;
};
SKIN.pyramid = (b, n) => {
  const b0 = fpOf(n) + 1.0, inset = Math.min(0.3, (b0 - 1.1) / (2 * n));
  let y = 0;
  for (let f = 0; f < n; f++) {
    const s = b0 - 2 * inset * f, h = FH - 0.05;
    b.box(s, h, s, 0, y + h / 2, 0, M.wall);
    b.rimSquare(s, y + h, b.A.rim);
    b.faceWins(f, s, s, y + h / 2, h, 0.62, 0.3);
    y += FH;
  }
  b.box(0.8, 0.5, 0.8, 0, y + 0.25, 0, M.roof);
  const beam = b.part(G.beam, b.A.beam, 1, 5.5, 1, 0, y + 0.5 + 2.75, 0, false);
  b.anim.push((t) => { beam.material.opacity = (b.busy ? 0.3 : 0.16) + 0.05 * Math.sin(t * 2 + b.phase); });
  b.beacon(0, y + 0.62, 0, 0.13);
  b.top = y + 1.5;
};
SKIN.orbital = (b, n) => {
  const pad = fpOf(n) + 0.5, rd = 0.75 + fpOf(n) * 0.15;
  b.box(pad, 0.25, pad, 0, 0.125, 0, M.pad);
  b.ringFlat(pad * 0.42, 0.26, b.A.soft);
  const spineH = 0.45 + n * FH;
  b.cyl(0.17, spineH, 0, 0.25 + spineH / 2, 0, M.metal);
  let y = 0.55;
  for (let f = 0; f < n; f++) {
    b.cyl(rd, 0.26, 0, y + 0.13, 0, M.wall2);
    const edge = new THREE.Mesh(G.ringT, b.A.rim); edge.scale.setScalar(rd + 0.01); edge.rotation.x = Math.PI / 2; edge.position.y = y + 0.26; b.g.add(edge);
    b.ringWins(f, rd, y + 0.13, 0.12, 0.38, 0.5, 0.15);
    y += FH;
  }
  const Rp = 0.55 + Math.min(n, 8) * 0.07, py = 0.25 + spineH + Rp + 0.35, sys = new THREE.Group();
  sys.position.y = py; b.g.add(sys);
  const planet = new THREE.Mesh(G.sphere, M.planet); planet.scale.setScalar(Rp); planet.castShadow = true; sys.add(planet);
  const atmo = new THREE.Mesh(G.sphere, b.A.atmo); atmo.scale.setScalar(Rp * 1.14); sys.add(atmo);
  const ring = new THREE.Mesh(G.ringT, b.A.rim); ring.scale.setScalar(Rp * 1.9); ring.rotation.set(Math.PI / 2 - 0.42, 0, 0.25); sys.add(ring);
  const sat = new THREE.Mesh(G.sphere, b.A.glow); sat.scale.setScalar(0.07); sys.add(sat);
  const v = new THREE.Vector3();
  b.anim.push((t) => {
    sys.position.y = py + Math.sin(t * 0.9 + b.phase) * 0.08; planet.rotation.y = t * 0.25;
    const a = t * 0.9 + b.phase; v.set(Math.cos(a), Math.sin(a), 0).multiplyScalar(Rp * 1.9).applyEuler(ring.rotation); sat.position.copy(v);
  });
  b.top = py + Rp + 0.75;
};
SKIN.rocket = (b, n) => {
  const pad = fpOf(n) + 0.8, rr = 0.4 + Math.min(n, 8) * 0.045;
  b.box(pad, 0.3, pad, 0, 0.15, 0, M.pad);
  b.ringFlat(1.3, 0.31, b.A.soft);
  let y = 0.3;
  for (let f = 0; f < n; f++) {
    const h = FH - 0.04;
    b.cyl(rr, h, 0, y + h / 2, 0, f % 2 ? M.hull2 : M.hull);
    b.cyl(rr * 1.035, 0.05, 0, y + h, 0, b.A.rim, false);
    for (let k = 0; k < 4; k++) { const t = k / 4 * Math.PI * 2 + 0.4; b.win(Math.cos(t) * (rr + 0.012), y + h / 2, Math.sin(t) * (rr + 0.012), Math.PI / 2 - t, 0.15, 0.17, f, b.R() < 0.55); }
    y += FH;
  }
  b.part(G.cone, M.hull, rr, rr * 2.6, rr, 0, y + rr * 1.3, 0);
  b.beacon(0, y + rr * 2.6 + 0.04, 0, 0.07);
  for (let k = 0; k < 4; k++) {
    const t = k / 4 * Math.PI * 2 + Math.PI / 4, fin = b.box(0.06, FH * 1.15, rr * 1.15, Math.cos(t) * rr * 1.4, 0.3 + FH * 0.575, Math.sin(t) * rr * 1.4, b.A.fin);
    fin.rotation.y = -t + Math.PI / 2;
  }
  const gx = -rr - 1.0, gz = -rr - 1.0, gh = y + 0.7;
  b.box(0.32, gh, 0.32, gx, 0.3 + gh / 2, gz, M.metal);
  const dir = new THREE.Vector2(-gx, -gz).normalize(), len = Math.hypot(gx, gz) - rr;
  for (let f = 1; f <= n; f++) {
    const arm = b.box(0.07, 0.07, len, gx + dir.x * len / 2, 0.3 + f * FH - 0.12, gz + dir.y * len / 2, M.metal, false);
    arm.rotation.y = Math.atan2(dir.x, dir.y);
  }
  const skirt = b.part(G.skirt, b.A.beam, rr * 0.9, 0.5, rr * 0.9, 0, 0.55, 0, false);
  b.anim.push((t) => { const k = (b.busy ? 1.5 : 0.9) + 0.18 * Math.sin(t * 19 + b.phase); skirt.scale.set(rr * 0.9 * k, 0.5 * k, rr * 0.9 * k); });
  b.top = y + rr * 2.6 + 0.55;
};
SKIN.vault = (b, n) => {
  const fp = fpOf(n), w = fp + 1.1, d = Math.max(1.9, fp * 0.82);
  b.box(w + 0.5, 0.18, d + 0.5, 0, 0.09, 0, M.pad);
  let y = 0.18;
  for (let f = 0; f < n; f++) {
    const h = (f === 0 ? FH * 1.35 : FH) - 0.05;
    b.box(w, h, d, 0, y + h / 2, 0, M.wall);
    b.box(w + 0.08, 0.05, d + 0.08, 0, y + h + 0.025, 0, M.roof);
    if (f === 0) {
      const door = b.part(G.cyl, M.dark, 0.44, 0.05, 0.44, -w * 0.18, y + h * 0.5, d / 2 + 0.02, false); door.rotation.x = Math.PI / 2;
      const ring = new THREE.Mesh(G.ringT, b.A.rim); ring.scale.setScalar(0.46); ring.position.set(-w * 0.18, y + h * 0.5, d / 2 + 0.05); b.g.add(ring);
      b.box(0.62, 0.04, 0.02, -w * 0.18, y + h * 0.5, d / 2 + 0.06, b.A.soft, false); b.box(0.04, 0.62, 0.02, -w * 0.18, y + h * 0.5, d / 2 + 0.06, b.A.soft, false);
      b.box(w * 0.36, h * 0.28, 0.02, w * 0.22, y + h * 0.55, d / 2 + 0.02, b.A.soft, false);
    } else {
      const R = b.R, step = 0.42, m = Math.max(1, Math.floor((w - 0.3) / step)), s = w / m;
      for (let i = 0; i < m; i++) {
        b.win(-w / 2 + s * (i + 0.5), y + h / 2, d / 2 + 0.014, 0, 0.24, h * 0.5, f, R() < 0.5);
        b.win(-w / 2 + s * (i + 0.5), y + h / 2, -d / 2 - 0.014, Math.PI, 0.24, h * 0.5, f, R() < 0.5);
      }
    }
    b.box(0.02, 0.05, d * 0.8, w / 2 + 0.015, y + h * 0.5, 0, b.A.rim, false);
    b.box(0.02, 0.05, d * 0.8, -w / 2 - 0.015, y + h * 0.5, 0, b.A.rim, false);
    y += h + 0.05;
  }
  b.box(0.5, 0.3, 0.5, -w / 2 + 0.6, y + 0.15, -d / 2 + 0.55, M.roof);
  b.box(0.5, 0.3, 0.5, -w / 2 + 1.3, y + 0.15, -d / 2 + 0.55, M.roof);
  b.cyl(0.04, 0.6, w / 2 - 0.7, y + 0.3, d / 2 - 0.6, M.metal, false);
  const dish = b.part(G.hemi, M.metal, 0.42, 0.18, 0.42, w / 2 - 0.7, y + 0.66, d / 2 - 0.6, false); dish.rotation.x = Math.PI * 0.85; dish.rotation.z = 0.4;
  b.beacon(w / 2 - 0.7, y + 0.95, d / 2 - 0.6, 0.07);
  b.top = y + 1.15;
};

// a whole plot: its slab, its rim (dashed when private), two trees, a lamp, and the building
function makePlot(c, seed, opts) {
  geo();
  const n = floorsOf(c), A = amat(CO.accentHex(c.accent)), root = new THREE.Group();
  const slab = new THREE.Mesh(G.box, M.pad); slab.scale.set(PS, 0.25, PS); slab.position.y = 0.125; slab.receiveShadow = true; root.add(slab);
  const rimMat = A.rim.clone(); rimMat.emissiveIntensity = c.public || opts.mine ? 1.0 : 0.6;
  const rb = new Building(A.hex, seed); rb.g = root; rb.rimSquare(PS, 0.26, rimMat, !c.public && !opts.mine);
  for (const [tx, tz] of [[-2.55, 2.55], [2.55, -2.55]]) {
    const tr = new THREE.Mesh(G.cyl, M.trunk); tr.scale.set(0.06, 0.35, 0.06); tr.position.set(tx, 0.42, tz); root.add(tr);
    const lf = new THREE.Mesh(G.cone, M.leaf); lf.scale.set(0.32, 0.75, 0.32); lf.position.set(tx, 0.92, tz); lf.castShadow = true; root.add(lf);
  }
  const lamp = new THREE.Mesh(G.cyl, M.metal); lamp.scale.set(0.03, 0.9, 0.03); lamp.position.set(2.7, 0.7, 2.7); root.add(lamp);
  const bulb = new THREE.Mesh(G.sphere, A.glow); bulb.scale.setScalar(0.06); bulb.position.set(2.7, 1.17, 2.7); root.add(bulb);
  const b = new Building(A.hex, seed);
  (SKIN[c.skin] || SKIN.tower)(b, n);
  b.finish();
  b.g.position.y = 0.25; root.add(b.g);
  const hit = new THREE.Mesh(G.box, M.hit); hit.scale.set(PS, b.top + 0.6, PS); hit.position.y = (b.top + 0.6) / 2; root.add(hit);
  return { root, b, rimMat, hit, top: b.top + 0.25, n };
}

/* ---------------- the ground: a floating platform with streets and their light ---------------- */
function groundTex() {
  const N = 2048, k = N / PLAT, mk = () => { const c = document.createElement('canvas'); c.width = c.height = N; return c; };
  const base = mk(), glow = mk(), g = base.getContext('2d'), h = glow.getContext('2d');
  g.fillStyle = '#0a1322'; g.fillRect(0, 0, N, N);
  h.fillStyle = '#000'; h.fillRect(0, 0, N, N);
  const X = (u) => (u + PLAT / 2) * k;
  g.strokeStyle = 'rgba(34,56,92,.55)'; g.lineWidth = 1.2;
  for (let u = -PLAT / 2; u <= PLAT / 2; u += 1) {
    g.beginPath(); g.moveTo(X(u), 0); g.lineTo(X(u), N); g.stroke();
    g.beginPath(); g.moveTo(0, X(u)); g.lineTo(N, X(u)); g.stroke();
  }
  // streets between the plots and the ring road round the city
  const streets = [];
  for (let i = 0; i < GRID - 1; i++) streets.push(i * CELL + PS + ST / 2 - OFF);
  const lanes = streets.map((s) => [s, ST]).concat([[-OFF - 1.6, 2.2], [OFF + 1.6, 2.2]]);
  lanes.forEach(([s, wid]) => {
    g.fillStyle = '#070d18'; g.fillRect(X(s - wid / 2), 0, wid * k, N); g.fillRect(0, X(s - wid / 2), N, wid * k);
  });
  h.setLineDash([0.55 * k, 0.65 * k]); h.lineWidth = 0.07 * k; h.strokeStyle = 'rgba(0,207,255,.55)';
  lanes.forEach(([s]) => { h.beginPath(); h.moveTo(X(s), 0); h.lineTo(X(s), N); h.stroke(); h.beginPath(); h.moveTo(0, X(s)); h.lineTo(N, X(s)); h.stroke(); });
  h.setLineDash([]); h.lineWidth = 0.035 * k; h.strokeStyle = 'rgba(59,130,246,.45)';
  lanes.forEach(([s, wid]) => [s - wid / 2, s + wid / 2].forEach((e) => { h.beginPath(); h.moveTo(X(e), 0); h.lineTo(X(e), N); h.stroke(); h.beginPath(); h.moveTo(0, X(e)); h.lineTo(N, X(e)); h.stroke(); }));
  const t1 = new THREE.CanvasTexture(base), t2 = new THREE.CanvasTexture(glow);
  [t1, t2].forEach((t) => { t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; });
  return { map: t1, glow: t2, streets: lanes.map((l) => l[0]) };
}
function radialTex(rgb, a) {
  const c = document.createElement('canvas'); c.width = c.height = 256; const g = c.getContext('2d');
  const gr = g.createRadialGradient(128, 128, 0, 128, 128, 128);
  gr.addColorStop(0, 'rgba(' + rgb + ',' + a + ')'); gr.addColorStop(0.45, 'rgba(' + rgb + ',' + (a * 0.35) + ')'); gr.addColorStop(1, 'rgba(' + rgb + ',0)');
  g.fillStyle = gr; g.fillRect(0, 0, 256, 256);
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; return t;
}

/* ---------------- the map ---------------- */
class Universe3D {
  constructor(el, stage, h) {
    this.el = el; this.stage = stage; this.h = h || {};
    this.tip = stage.querySelector('.tip'); this.bans = stage.querySelector('.uvbans');
    this.items = []; this.live = {}; this.mineKey = ''; this.fitted = false; this.pops = [];
    this.mouse = new THREE.Vector2(); this.ray = new THREE.Raycaster(); this.hover = null; this.mouseIn = false; this.lastUse = 0;
    geo();
    this.scene = new THREE.Scene();
    this.scene.background = new THREE.Color(0x03060c);
    this.scene.fog = new THREE.Fog(0x03060c, 95, 230);
    this.camera = new THREE.PerspectiveCamera(32, 2, 0.5, 900);
    // no antialias on the renderer itself: three.js resolves it through ONE quad shared by every renderer on the
    // page, so a second renderer (a preview) would take this canvas over. The pass multisamples instead.
    this.renderer = new THREE.WebGPURenderer({ antialias: false });
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping;
    this.renderer.toneMappingExposure = 1.08;
    this.renderer.shadowMap.enabled = true;
    this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    el.appendChild(this.renderer.domElement);
    this.controls = new OrbitControls(this.camera, this.renderer.domElement);
    Object.assign(this.controls, { enableDamping: true, dampingFactor: 0.07, minDistance: 9, maxDistance: 150, maxPolarAngle: Math.PI * 0.44, minPolarAngle: 0.18,
      autoRotate: true, autoRotateSpeed: 0.28, screenSpacePanning: false, zoomSpeed: 0.9, rotateSpeed: 0.6 });
    this.controls.addEventListener('start', () => { this.tw = null; this.lastUse = performance.now(); this.controls.autoRotate = false; });
    this.world();
    this.bind();
    this.resize();
    this.clock = new THREE.Clock();
    this.renderer.init().then(() => {
      try { this.post = new Post(this.renderer, this.scene, this.camera, 0.62, 0.42, 0.8); } catch (e) { console.warn('bloom off:', e); this.post = null; }
      this.renderer.setAnimationLoop(() => this.frame());
      this.ready = true;
    }).catch((e) => { console.error('3D map could not start:', e); if (this.h.onFail) this.h.onFail(e); });
    setInterval(() => { if (this.visible()) this.pulse(); }, 1700);
    if (window.ResizeObserver) new ResizeObserver(() => this.resize()).observe(el);
  }
  visible() { return this.el.clientWidth > 0 && this.el.clientHeight > 0; }

  // lights, the floating platform, its edge glow, streets with traffic, stars, nebulae, and Cymetica in the middle
  world() {
    const S = this.scene;
    S.add(new THREE.HemisphereLight(0x3a6ab0, 0x05080f, 1.1));
    S.add(new THREE.AmbientLight(0x1a2a44, 0.6));
    const sun = new THREE.DirectionalLight(0xb8d4ff, 1.7);
    sun.position.set(-34, 58, 26); sun.castShadow = true;
    sun.shadow.mapSize.set(2048, 2048);
    Object.assign(sun.shadow.camera, { left: -34, right: 34, top: 34, bottom: -34, near: 5, far: 150 });
    sun.shadow.bias = -0.0006; sun.shadow.normalBias = 0.02;
    S.add(sun); S.add(sun.target);
    const rim = new THREE.DirectionalLight(0x00cfff, 0.45); rim.position.set(40, 18, -40); S.add(rim);
    const tx = groundTex(); this.streets = tx.streets;
    const side = new THREE.MeshStandardMaterial({ color: 0x0b1424, roughness: 0.5, metalness: 0.6 });
    const top = new THREE.MeshStandardMaterial({ map: tx.map, emissiveMap: tx.glow, emissive: 0xffffff, emissiveIntensity: 0.55, roughness: 0.42, metalness: 0.45 });
    const ground = new THREE.Mesh(G.box, [side, side, top, side, side, side]);
    ground.scale.set(PLAT, 1.4, PLAT); ground.position.y = -0.7; ground.receiveShadow = true; S.add(ground);
    // the platform's lit edge and a band of light round its side: a city floating in space
    const edge = new THREE.MeshStandardMaterial({ color: 0, emissive: 0x00cfff, emissiveIntensity: 1.5 }), band = new THREE.MeshStandardMaterial({ color: 0, emissive: 0x3b82f6, emissiveIntensity: 1.0 });
    const H = PLAT / 2;
    [[0, H], [0, -H]].forEach(([x, z]) => { this.addBox(PLAT + 0.12, 0.06, 0.06, x, 0.0, z, edge); this.addBox(PLAT + 0.1, 0.05, 0.05, x, -0.75, z, band); });
    [[H, 0], [-H, 0]].forEach(([x, z]) => { this.addBox(0.06, 0.06, PLAT + 0.12, x, 0.0, z, edge); this.addBox(0.05, 0.05, PLAT + 0.1, x, -0.75, z, band); });
    const under = new THREE.Mesh(G.plane, new THREE.MeshBasicMaterial({ map: radialTex('0,207,255', 0.3), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false }));
    under.scale.setScalar(PLAT * 1.7); under.rotation.x = Math.PI / 2; under.position.y = -3.2; S.add(under);
    // stars all round, and two clouds of colour far away
    const N = 2600, pos = new Float32Array(N * 3), colr = new Float32Array(N * 3), R = rng(42), cc = new THREE.Color();
    for (let i = 0; i < N; i++) {
      const u = R() * 2 - 1, th = R() * Math.PI * 2, rad = 330 + R() * 120, s = Math.sqrt(1 - u * u);
      pos.set([Math.cos(th) * s * rad, u * rad * 0.8 + 40, Math.sin(th) * s * rad], i * 3);
      cc.set(R() < 0.2 ? 0x00cfff : R() < 0.3 ? 0x3b82f6 : 0xa9b8cc).multiplyScalar(0.5 + R() * 1.3); colr.set([cc.r, cc.g, cc.b], i * 3);
    }
    const sg = new THREE.BufferGeometry(); sg.setAttribute('position', new THREE.BufferAttribute(pos, 3)); sg.setAttribute('color', new THREE.BufferAttribute(colr, 3));
    const stars = new THREE.Points(sg, new THREE.PointsMaterial({ vertexColors: true, size: 1, sizeAttenuation: false, fog: false }));
    S.add(stars); this.starField = stars;
    this.nebulae = [['0,207,255', 0.3, [-250, 70, -110], 300], ['59,130,246', 0.36, [-70, 30, -280], 340], ['0,255,136', 0.1, [-230, -50, -240], 260],
      ['59,130,246', 0.3, [260, 50, 60], 320], ['0,207,255', 0.2, [90, -30, 280], 280], ['255,68,68', 0.05, [240, 90, -230], 220]].map(([rgb, a, p, s]) => {
      const m = new THREE.Mesh(G.plane, new THREE.MeshBasicMaterial({ map: radialTex(rgb, a), transparent: true, blending: THREE.AdditiveBlending, depthWrite: false, fog: false }));
      m.position.set(p[0], p[1], p[2]); m.scale.setScalar(s); S.add(m); return m;
    });
    this.traffic();
    this.core();
  }
  addBox(w, h, d, x, y, z, mat) { const m = new THREE.Mesh(G.box, mat); m.scale.set(w, h, d); m.position.set(x, y, z); this.scene.add(m); return m; }
  traffic() {
    const lanes = [];
    this.streets.forEach((s, i) => {
      lanes.push({ ax: 'z', c: s - 0.35, dir: 1 }, { ax: 'z', c: s + 0.35, dir: -1 }, { ax: 'x', c: s - 0.35, dir: -1 }, { ax: 'x', c: s + 0.35, dir: 1 });
    });
    const R = rng(7), cols = [0x00cfff, 0x00ff88, 0x3b82f6, 0x00cfff, 0xe6edf7];
    this.cars = [];
    lanes.forEach((l) => { for (let k = 0; k < 2; k++) this.cars.push({ l, p: R() * PLAT, v: 2.2 + R() * 2.6, col: new THREE.Color(cols[Math.floor(R() * cols.length)]).multiplyScalar(2.3) }); });
    this.carMesh = new THREE.InstancedMesh(G.box, new THREE.MeshBasicMaterial({ color: 0xffffff }), this.cars.length);
    this.cars.forEach((c, i) => this.carMesh.setColorAt(i, c.col));
    this.carMesh.instanceColor.needsUpdate = true;
    this.scene.add(this.carMesh);
  }
  core() {
    const g = new THREE.Group(), cyan = amat('#00cfff'), blue = amat('#3b82f6');
    const slab = new THREE.Mesh(G.box, M.pad); slab.scale.set(PS, 0.25, PS); slab.position.y = 0.125; slab.receiveShadow = true; g.add(slab);
    [2.7, 2.05, 1.4].forEach((r, i) => { const m = new THREE.Mesh(G.ring, i === 1 ? cyan.rim : blue.soft); m.scale.setScalar(r); m.rotation.x = Math.PI / 2; m.position.y = 0.27; g.add(m); });
    const pil = new THREE.Mesh(G.cyl, M.metal); pil.scale.set(0.5, 1.1, 0.5); pil.position.y = 0.8; pil.castShadow = true; g.add(pil);
    const beam = new THREE.Mesh(G.beam, cyan.beam); beam.scale.set(1.6, 34, 1.6); beam.position.y = 1.35 + 17; g.add(beam);
    this.coreRings = [1.5, 2.3, 3.1].map((y, i) => { const m = new THREE.Mesh(G.ringT, cyan.rim); m.scale.setScalar(1.15 - i * 0.25); m.position.y = y; m.rotation.x = Math.PI / 2; g.add(m); return m; });
    this.coreOrb = new THREE.Mesh(G.sphere, cyan.glow); this.coreOrb.scale.setScalar(0.42); this.coreOrb.position.y = 4.1; g.add(this.coreOrb);
    const pl = new THREE.PointLight(0x00cfff, 25, 22, 1.6); pl.position.y = 3.2; g.add(pl);
    g.position.set(CORE[0] * CELL + PS / 2 - OFF, 0, CORE[1] * CELL + PS / 2 - OFF);
    const hit = new THREE.Mesh(G.box, M.hit); hit.scale.set(PS, 5, PS); hit.position.y = 2.5; hit.userData.id = 'core'; g.add(hit);
    this.coreHit = hit;
    this.scene.add(g);
  }

  // where each company stands: the biggest at the back, so a small one in front is never hidden
  layout() {
    const slots = [];
    for (let i = 0; i < GRID; i++) for (let j = 0; j < GRID; j++) {
      if ((i === CORE[0] && j === CORE[1]) || (i === MINE[0] && j === MINE[1])) continue;
      slots.push([i, j]);
    }
    slots.sort((a, b) => (a[0] + a[1]) - (b[0] + b[1]) || Math.abs(a[0] - a[1]) - Math.abs(b[0] - b[1]) || a[0] - b[0]);
    const list = CO.UNIVERSE.slice().sort((a, b) => floorsOf(b) - floorsOf(a) || a.id - b.id);
    this.items = list.map((c, k) => ({ c, at: slots[k] })).filter((it) => it.at);
    this.items.push({ c: this.h.mine(), at: MINE, mine: true });
    this.items.forEach((it) => {
      if (!it.mine && it.c.status !== 'paused') { const R = rng(it.c.id * 3), n = floorsOf(it.c); this.live[it.c.id] = R() < 0.55 ? [Math.floor(R() * n)] : []; }
      this.place(it);
    });
    this.stats();
  }
  place(it) {
    if (it.plot) { this.scene.remove(it.plot.root); }
    const c = it.c, p = makePlot(c, it.mine ? 7 : c.id, { mine: it.mine });
    p.root.position.set(it.at[0] * CELL + PS / 2 - OFF, 0, it.at[1] * CELL + PS / 2 - OFF);
    p.hit.userData.id = c.id;
    if (it.mine) {
      const ring = new THREE.Mesh(G.ring, amat('#00ff88').rim); ring.scale.setScalar(4.15); ring.rotation.x = Math.PI / 2; ring.position.y = 0.05; p.root.add(ring); p.meRing = ring;
    }
    this.scene.add(p.root);
    it.plot = p;
    it.anchor = new THREE.Vector3(p.root.position.x, p.top + 0.3, p.root.position.z);
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
    it.bw = 0;
  }
  // our own company: its building follows Settings, its floors follow its departments, its ET10 pops
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
    const pool = this.items.filter((it) => !it.mine && it.c.status !== 'paused');
    for (let k = 0; k < 3 && pool.length; k++) {
      const it = pool[Math.floor(Math.random() * pool.length)], n = floorsOf(it.c), on = [];
      const w = Math.random() < 0.3 ? 0 : (n > 1 && Math.random() < 0.3 ? 2 : 1);
      while (on.length < w) { const f = Math.floor(Math.random() * n); if (!on.includes(f)) on.push(f); }
      this.live[it.c.id] = on; this.paint(it);
      const qa = (it.c.departments || []).some((d) => d.key === 'testing');
      if (qa && on.length && Math.random() < 0.1) { it.c.bugs = (it.c.bugs || 0) + 1; this.pop(it, '+1,000 ET10'); }
    }
    this.stats();
  }
  pop(it, label) {
    const el = document.createElement('div'); el.className = 'b3pop'; el.textContent = label; this.bans.appendChild(el);
    const p = { el, it, t0: performance.now() }; this.pops.push(p);
    setTimeout(() => { el.remove(); this.pops = this.pops.filter((x) => x !== p); }, 2600);
  }
  stats() {
    let pub = 0, work = 0;
    this.items.forEach((it) => { if (it.c.public) pub++; work += (it.mine ? (it.c.working || []) : (this.live[it.c.id] || [])).length; });
    if (this.h.onStats) this.h.onStats({ companies: this.items.length, public: pub, working: work });
  }
  find(id) { return this.items.find((it) => String(it.c.id) === String(id)) || null; }
  open(id) { const it = this.find(id); if (it && this.h.onOpen) { this.hideTip(); this.h.onOpen(it); } }

  /* ---------------- camera ---------------- */
  home() {
    const d = this.homeDist();
    const sph = new THREE.Spherical(d, 0.98, Math.PI / 4);
    const tgt = new THREE.Vector3(2.4, 0.5, 2.4);
    return { pos: new THREE.Vector3().setFromSpherical(sph).add(tgt), tgt };
  }
  homeDist() { const a = this.camera.aspect || 2; return a < 1.2 ? 128 : a < 1.6 ? 100 : 84; }
  fit(anim) {
    const h = this.home();
    if (!this.fitted && anim === false) {
      // the first look: from high and far, swooping down onto the city
      this.fitted = true;
      this.camera.position.copy(h.pos.clone().multiplyScalar(1.9).add(new THREE.Vector3(0, 40, 0))); this.controls.target.copy(h.tgt);
      this.tween(h.pos, h.tgt, 2200);
      return;
    }
    this.fitted = true;
    this.tween(h.pos, h.tgt, anim === false ? 0 : 900);
  }
  zoom(f) {
    const t = this.controls.target, off = this.camera.position.clone().sub(t);
    const len = Math.max(this.controls.minDistance, Math.min(this.controls.maxDistance, off.length() * f));
    this.tween(t.clone().add(off.setLength(len)), t.clone(), 320);
  }
  flyTo(id, done, ms) {
    const it = this.find(id); if (!it || !it.plot) { if (done) done(); return; }
    const p = it.plot.root.position, tgt = new THREE.Vector3(p.x, Math.min(it.plot.top * 0.45, 4), p.z);
    const dir = this.camera.position.clone().sub(this.controls.target); dir.y = Math.max(dir.y, dir.length() * 0.45); dir.normalize();
    const dist = 9 + it.plot.top * 1.15;
    this.tween(tgt.clone().add(dir.multiplyScalar(dist)), tgt, ms == null ? 950 : ms, done);
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
    this.items.forEach((it) => { if (it.plot) { it.plot.b.tick(t); if (it.plot.meRing) it.plot.meRing.scale.setScalar(4.15 + Math.sin(t * 2.4) * 0.12); } });
    this.coreRings.forEach((r, i) => { r.rotation.z = t * (0.5 + i * 0.3) * (i % 2 ? -1 : 1); r.rotation.x = Math.PI / 2 + Math.sin(t * 0.7 + i) * 0.25; });
    this.coreOrb.position.y = 4.1 + Math.sin(t * 1.4) * 0.18;
    this.moveCars(t);
    this.nebulae.forEach((n) => n.lookAt(this.camera.position));
    this.starField.rotation.y = t * 0.004;
    if (this.mouseMoved) { this.mouseMoved = false; this.pick(); }
    if (this.post) this.post.render(); else this.renderer.render(this.scene, this.camera);
    this.overlay();
  }
  moveCars(t) {
    const m4 = new THREE.Matrix4(), q = new THREE.Quaternion(), v = new THREE.Vector3(), s = new THREE.Vector3(0.26, 0.12, 0.62), up = new THREE.Vector3(0, 1, 0);
    this.cars.forEach((c, i) => {
      const L = c.l, p = ((c.p + t * c.v * L.dir) % PLAT + PLAT) % PLAT - PLAT / 2;
      if (L.ax === 'z') { v.set(L.c, 0.08, p); q.setFromAxisAngle(up, 0); } else { v.set(p, 0.08, L.c); q.setFromAxisAngle(up, Math.PI / 2); }
      m4.compose(v, q, s); this.carMesh.setMatrixAt(i, m4);
    });
    this.carMesh.instanceMatrix.needsUpdate = true;
  }
  // the banners and the ET10 pops follow their buildings; a banner hidden behind a nearer one steps back
  overlay() {
    const w = this.el.clientWidth, h = this.el.clientHeight, v = new THREE.Vector3(), placed = [];
    const list = this.items.map((it) => {
      v.copy(it.anchor).project(this.camera);
      return { it, x: (v.x + 1) / 2 * w, y: (1 - v.y) / 2 * h, z: v.z, d: this.camera.position.distanceTo(it.anchor) };
    }).sort((a, b) => a.d - b.d);
    list.forEach((o) => {
      const el = o.it.el; if (!el) return;
      if (!o.it.bw) o.it.bw = el.offsetWidth || 160;
      const off = o.z > 1 || o.x < -80 || o.x > w + 80 || o.y < -40 || o.y > h + 60;
      const r = { l: o.x - o.it.bw / 2, r: o.x + o.it.bw / 2, t: o.y - 30, b: o.y };
      const clash = placed.some((p) => r.l < p.r && r.r > p.l && r.t < p.b && r.b > p.t);
      const keep = String(this.hover) === String(o.it.c.id) || o.it.mine;
      el.classList.toggle('hidden', off || (clash && !keep));
      if (!off && (!clash || keep)) placed.push(r);
      el.style.transform = 'translate(' + o.x.toFixed(1) + 'px,' + o.y.toFixed(1) + 'px) translate(-50%,-100%)';
      el.style.zIndex = String(1000 - Math.round(o.d));
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
    if (old && old.plot) { old.plot.rimMat.emissiveIntensity = old.c.public || old.mine ? 1.0 : 0.6; if (old.el) old.el.classList.remove('hov'); }
    this.hover = id;
    const it = id != null && this.find(id);
    if (it && it.plot) { it.plot.rimMat.emissiveIntensity = 3.2; if (it.el) it.el.classList.add('hov'); }
    this.renderer.domElement.style.cursor = id != null && id !== 'core' ? 'pointer' : '';
    if (fromBanner) { if (id != null && this.lastEvBanner !== id) { this.lastEvBanner = id; } if (id == null) this.hideTip(); else { const html = this.tipHTML(id), r = it && it.el && it.el.getBoundingClientRect(); if (html && r) this.showTip(html, { clientX: r.left + r.width / 2, clientY: r.bottom + 6 }); } }
  }
  tipHTML(id) {
    if (id === 'core') return '<b class="c">Cymetica</b><br>Every company here works on it.';
    const it = this.find(id); if (!it) return '';
    const c = it.c, n = floorsOf(c), work = (it.mine ? (c.working || []) : (this.live[c.id] || [])).length;
    const et = it.mine ? (c.et10 || 0) : CO.uvEt10(c), acc = CO.accentHex(c.accent);
    const nums = '<b>' + n + '</b> department' + (n === 1 ? '' : 's') + (c.public || it.mine ? ' · <b>' + work + '</b> working now' + (et ? ' · <b class="g">+' + et.toLocaleString('en-US') + '</b> ET10' : '') : '');
    const act = it.mine ? '<span class="g">Your company · click to open your office</span>' + (c.public ? '' : '<br><span>Private: others see its name, building and mission</span>')
      : c.public ? (c.status === 'paused' ? '<span>Paused · click to look inside</span>' : '<span class="c">Click to look inside →</span>') : '<span>Private · click for its description</span>';
    return '<div class="uvt"><b style="color:' + acc + '">' + esc(c.name) + '</b><span>@' + esc(c.owner) + '</span></div><div>' + nums + '</div><div>' + act + '</div>';
  }
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

/* ---------------- one building, turning slowly: Settings, Create your company, a private company's card ---------------- */
const PREVIEWS = [];
class Preview {
  constructor(el) {
    geo();
    this.el = el; this.wrap = document.createElement('div'); this.wrap.className = 'pv3';
    this.ban = document.createElement('div'); this.ban.className = 'b3 pvb'; this.wrap.appendChild(this.ban);
    el.appendChild(this.wrap);
    this.scene = new THREE.Scene(); this.scene.background = new THREE.Color(0x070c16);
    this.camera = new THREE.PerspectiveCamera(30, 1, 0.1, 200);
    this.renderer = new THREE.WebGPURenderer({ antialias: false });   // see Universe3D: the pass multisamples
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.toneMapping = THREE.ACESFilmicToneMapping; this.renderer.toneMappingExposure = 1.1;
    this.renderer.shadowMap.enabled = true; this.renderer.shadowMap.type = THREE.PCFSoftShadowMap;
    this.wrap.insertBefore(this.renderer.domElement, this.ban);
    this.scene.add(new THREE.HemisphereLight(0x3a6ab0, 0x05080f, 1.2), new THREE.AmbientLight(0x1a2a44, 0.6));
    const sun = new THREE.DirectionalLight(0xb8d4ff, 1.8); sun.position.set(-8, 14, 6); sun.castShadow = true; sun.shadow.mapSize.set(1024, 1024);
    Object.assign(sun.shadow.camera, { left: -6, right: 6, top: 6, bottom: -6, near: 1, far: 40 }); sun.shadow.normalBias = 0.02;
    this.scene.add(sun);
    const rim = new THREE.DirectionalLight(0x00cfff, 0.5); rim.position.set(9, 4, -9); this.scene.add(rim);
    const floor = new THREE.Mesh(G.cyl, new THREE.MeshStandardMaterial({ color: 0x0a1322, roughness: 0.5, metalness: 0.4 })); floor.scale.set(5.4, 0.2, 5.4); floor.position.y = -0.1; floor.receiveShadow = true; this.scene.add(floor);
    const glow = new THREE.Mesh(G.ring, new THREE.MeshStandardMaterial({ color: 0, emissive: 0x00cfff, emissiveIntensity: 0.9 })); glow.scale.setScalar(5.4); glow.rotation.x = Math.PI / 2; glow.position.y = 0.01; this.scene.add(glow);
    this.turn = new THREE.Group(); this.scene.add(this.turn);
    this.clock = new THREE.Clock(); this.key = '';
    this.renderer.init().then(() => {
      try { this.post = new Post(this.renderer, this.scene, this.camera, 0.6, 0.4, 0.78); } catch (e) { this.post = null; }
      this.renderer.setAnimationLoop(() => this.frame());
      el.classList.add('has3d');
    }).catch(() => { this.dead = true; });
  }
  set(o) {
    const key = [o.skin, o.accent, o.floors, o.public, o.name, o.you].join('|');
    if (key === this.key) return; this.key = key;
    if (this.plot) this.turn.remove(this.plot.root);
    const c = { skin: o.skin, accent: o.accent, public: !!o.public || !!o.you, departments: new Array(Math.max(1, o.floors || 1)).fill(0), status: 'active' };
    this.plot = makePlot(c, o.seed || 7, { mine: !!o.you });
    this.plot.b.paint([], o.public || o.you ? '' : 'priv');
    this.turn.add(this.plot.root);
    const top = this.plot.top, dist = Math.max(20, (top + 2.4) * 2.05);
    this.target = new THREE.Vector3(0, top * 0.5, 0);
    this.camera.position.copy(new THREE.Vector3().setFromSpherical(new THREE.Spherical(dist, 1.06, Math.PI / 4)).add(this.target));
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
    if (this.plot) this.plot.b.tick(t);
    if (this.post) this.post.render(); else this.renderer.render(this.scene, this.camera);
    if (this.anchor) {
      const v = this.anchor.clone().project(this.camera);
      this.ban.style.transform = 'translate(' + ((v.x + 1) / 2 * w).toFixed(1) + 'px,' + ((1 - v.y) / 2 * h).toFixed(1) + 'px) translate(-50%,-100%)';
    }
  }
  dispose() { try { this.renderer.setAnimationLoop(null); this.renderer.dispose(); } catch (e) { /* gone */ } this.wrap.remove(); this.dead = true; }
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

// can this browser draw it at all? WebGPU, or WebGL2 underneath it
(function () {
  let gl2 = false;
  try { gl2 = !!document.createElement('canvas').getContext('webgl2'); } catch (e) { gl2 = false; }
  CO.U3 = (gl2 || navigator.gpu) ? { ok: true, gpu: !!navigator.gpu, universe: (el, stage, h) => new Universe3D(el, stage, h), preview, THREE, geo, makePlot, SKIN, amat }
    : { failed: true, why: 'no WebGPU and no WebGL2' };
  window.dispatchEvent(new Event('co3d'));
})();
