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
// the map's model lives in universe.js, which the SVG map draws too: one copy, so the two pictures cannot drift
const rng = CO.uvRng, floorsOf = CO.floorsOf, fpOf = CO.fpOf;

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
    this.controls.addEventListener('start', () => { this.tw = null; this.used = true; this.lastUse = performance.now(); this.controls.autoRotate = false; });
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
    this.items = CO.uvPlan(this.h.mine());
    CO.uvSeed(this.items, this.live);
    this.items.forEach((it) => this.place(it));
    this.stats();
  }
  place(it) {
    this.built = (this.built || 0) + 1;
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
    CO.uvStep(this.items, this.live).forEach(({ it, on, was, bug }) => {
      this.paint(it);
      // a floor that starts work sends it to Cymetica: an arc of light to the beam in the middle
      if (on.length && !was) this.arc(it, false);
      if (bug) { this.arc(it, true); setTimeout(() => this.pop(it, '+1,000 ET10'), 1300); }
    });
    this.stats();
  }
  // work goes in to Cymetica in the company's colour; ET10 comes back out in green
  arc(it, back) {
    if (!it.plot || (this.arcs && this.arcs.length > 10)) return;
    const core = new THREE.Vector3(CORE[0] * CELL + PS / 2 - OFF, 4.1, CORE[1] * CELL + PS / 2 - OFF);
    const top = new THREE.Vector3(it.plot.root.position.x, it.plot.top - 0.3, it.plot.root.position.z);
    const a = back ? core : top, b = back ? top : core, mid = a.clone().lerp(b, 0.5);
    mid.y = Math.max(a.y, b.y) + 3 + a.distanceTo(b) * 0.22;
    const A = back ? amat('#00ff88') : amat(CO.accentHex(it.c.accent)), curve = new THREE.QuadraticBezierCurve3(a, mid, b);
    const head = new THREE.Mesh(G.sphere, A.glow); head.scale.setScalar(0.26);
    const halo = new THREE.Mesh(G.sphere, A.atmo); halo.scale.setScalar(2.4); head.add(halo);
    // the streak: a thin tube along the arc, drawn as the light travels and let go behind it
    const tube = new THREE.TubeGeometry(curve, 64, 0.07, 6, false);
    const mat = new THREE.MeshBasicMaterial({ color: A.c.clone().multiplyScalar(2.6), transparent: true, opacity: 0.85, blending: THREE.AdditiveBlending, depthWrite: false });
    const streak = new THREE.Mesh(tube, mat); tube.setDrawRange(0, 0);
    this.scene.add(head, streak);
    (this.arcs = this.arcs || []).push({ curve, head, streak, tube, mat, trail: [], t0: performance.now(), dur: 1500 + a.distanceTo(b) * 30 });
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
    this.items.forEach((it) => { if (it.plot) { it.plot.b.tick(t); if (it.plot.meRing) it.plot.meRing.scale.setScalar(4.15 + Math.sin(t * 2.4) * 0.12); } });
    this.coreRings.forEach((r, i) => { r.rotation.z = t * (0.5 + i * 0.3) * (i % 2 ? -1 : 1); r.rotation.x = Math.PI / 2 + Math.sin(t * 0.7 + i) * 0.25; });
    this.coreOrb.position.y = 4.1 + Math.sin(t * 1.4) * 0.18;
    this.moveCars(t);
    if (this.arcs && this.arcs.length) {
      this.arcs = this.arcs.filter((a) => {
        const f = (now - a.t0) / a.dur;
        if (f >= 1.25) { this.scene.remove(a.head, a.streak); a.tube.dispose(); a.mat.dispose(); return false; }
        const e = Math.min(1, f < 0.5 ? 2 * f * f : 1 - Math.pow(-2 * Math.min(f, 1) + 2, 2) / 2);
        a.head.position.copy(a.curve.getPoint(e)); a.head.visible = f < 1;
        const n = a.tube.index.count, seg = n / 64, from = Math.max(0, Math.min(f, 1.25) - 0.4) / 0.85, to = e;
        a.tube.setDrawRange(Math.floor(from * 64) * seg, Math.max(0, Math.floor((to - from) * 64)) * seg);
        a.mat.opacity = 0.85 * (f > 1 ? 1 - (f - 1) / 0.25 : 1);
        return true;
      });
    }
    this.nebulae.forEach((n) => n.lookAt(this.camera.position));
    this.starField.rotation.y = t * 0.004;
    if (this.mouseMoved) { this.mouseMoved = false; this.pick(); }
    // a GPU that cannot run a shader says so on the first frames: stop, and let the flat map take over
    try { if (this.post) this.post.render(); else this.renderer.render(this.scene, this.camera); this.frames = (this.frames || 0) + 1; }
    catch (e) { console.error('3D map stopped:', e); this.renderer.setAnimationLoop(null); if (this.h.onFail && !(this.frames > 30)) this.h.onFail(e); return; }
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
    // a still camera moves no banner: restyle them only when the view, the size, the hover or a building changed
    const key = this.camera.matrixWorld.elements.join(',') + '|' + w + 'x' + h + '|' + this.hover + '|' + this.items.length + '|' + this.built;
    if (key === this.ovKey && !this.pops.length) return;
    this.ovKey = key;
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

/* ---------------- the office in 3D: the same floor plan, rooms you can walk the camera into ---------------- */
// What a room is doing, in light. Blue is only "up next", and only on the room's edge line: the floor, the walls,
// the furniture and the light itself are the site's navy-black under white light, the structure Cymetica green.
const STC = { working: 0x00cfff, queued: 0x3b82f6, waiting: 0xff4444, idle: 0x7f93ad };
const TONEC = { cyan: '#00cfff', red: '#ff4444', blue: '#7fb0ff', dim: '#a9b8cc' };
const OFFICE = { bg: 0x05070a, lamp: 0xeef3f8, agent: 0x4d5d72, agentE: 0x0b0f14, mon: 0x10202a };
const OM = {};
function omats() {
  if (OM.tile) return;
  const c = document.createElement('canvas'); c.width = c.height = 512; const g = c.getContext('2d');
  g.fillStyle = '#141a22'; g.fillRect(0, 0, 512, 512);
  g.strokeStyle = 'rgba(38,50,64,.95)'; g.lineWidth = 2;
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
// what a layout or a selection built for itself goes back to the GPU when it is cleared; the shared geometries
// (G, OM.capsule) and the shared materials (M, AM, OM) stay, since the next layout draws with them again
function release(root) {
  const shared = new Set();
  [M, OM].concat(Object.values(AM)).forEach((bag) => Object.values(bag).forEach((v) => {
    if (v && v.isMaterial) { shared.add(v); if (v.map) shared.add(v.map); } else if (v && typeof v === 'object') Object.values(v).forEach((m) => { if (m && m.isMaterial) shared.add(m); });
  }));
  root.traverse((o) => {
    if (o.isLight && o.dispose) o.dispose();
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
    // the floor plate, its grid and a lit edge
    const plate = new THREE.Mesh(G.box, [OM.plinth, OM.plinth, new THREE.MeshStandardMaterial({ color: 0x0a0e13, roughness: 0.5, metalness: 0.45 }), OM.plinth, OM.plinth, OM.plinth]);
    plate.scale.set(maxX + 1.2, 0.45, maxY + 1.2); plate.position.set(0, -0.225, 0); plate.receiveShadow = true; W.add(plate);
    // the frame of the whole office is Cymetica green
    const edgeM = emis('#00ff88', 1.15);
    [[0, maxY / 2 + 0.6, maxX + 1.25, 0.05], [0, -maxY / 2 - 0.6, maxX + 1.25, 0.05]].forEach(([x, z, w, t]) => { const m = new THREE.Mesh(G.box, edgeM); m.scale.set(w, t, t); m.position.set(x, 0, z); W.add(m); });
    [[maxX / 2 + 0.6, 0, maxY + 1.25], [-maxX / 2 - 0.6, 0, maxY + 1.25]].forEach(([x, z, d]) => { const m = new THREE.Mesh(G.box, edgeM); m.scale.set(0.05, 0.05, d); m.position.set(x, 0, z); W.add(m); });
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
    const c = this.V(r.x0 + 5.8, r.y0 + 1.4, 0.12);
    const ring = new THREE.Mesh(G.ring, OM.blue.soft); ring.scale.setScalar(0.62); ring.rotation.x = Math.PI / 2; ring.position.copy(c); r.g.add(ring);
    r.scan = new THREE.Mesh(G.ringT, OM.cyan.rim); r.scan.scale.setScalar(0.62); r.scan.rotation.x = Math.PI / 2; r.scan.position.copy(c); r.g.add(r.scan);
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
    r.plus = new THREE.Mesh(G.ringT, OM.cyan.rim); r.plus.scale.setScalar(0.9); r.plus.position.set(c.x, 1.2, c.z); g.add(r.plus);
    const hit = new THREE.Mesh(G.box, M.hit); hit.scale.set(RS, 1.6, RS); hit.position.set(c.x, 0.8, c.z); hit.userData.key = 'lot'; g.add(hit); this.hits.push(hit);
    const el = document.createElement('div'); el.className = 'p3lot'; el.innerHTML = '<b>+</b>ADD DEPARTMENT'; el.addEventListener('click', () => CO.emit('office:click', 'lot')); this.layer.appendChild(el);
    r.plate = el; r.plateAt = new THREE.Vector3(c.x, 1.25, c.z);
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
    const lit = st === 'working' || st === 'waiting', c = new THREE.Color(lit ? STC[st] : STC.idle);
    if (r.edgeM) { r.edgeM.emissive.copy(c); r.edgeM.emissiveIntensity = lit ? 1.5 : st === 'queued' ? 0.5 : 0.3; }
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
  home() {
    const s = this.size || 30, a = this.camera.aspect || 1.6, d = s * (a < 1.2 ? 2.15 : a < 1.6 ? 1.85 : 1.68);
    const tgt = new THREE.Vector3(s * 0.04, 0, s * 0.04 + 0.5);
    return { pos: new THREE.Vector3().setFromSpherical(new THREE.Spherical(d, 0.84, Math.PI / 4)).add(tgt), tgt };
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
      if (r.scan) { const s = 0.3 + ((t * 0.5) % 1) * 0.5; r.scan.scale.setScalar(s); }
      if (r.plus) { r.plus.rotation.y = t * 0.8; r.plus.position.y = 1.2 + Math.sin(t * 1.6) * 0.08; }
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
  CO.U3 = (gl2 || navigator.gpu) ? { ok: true, gpu: !!navigator.gpu, universe: (el, stage, h) => new Universe3D(el, stage, h), office: (el, stage, tipFor) => new Office3D(el, stage, tipFor), preview, THREE, geo, makePlot, SKIN, amat }
    : { failed: true, why: 'no WebGPU and no WebGL2' };
  window.dispatchEvent(new Event('co3d'));
})();
