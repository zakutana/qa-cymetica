// Capital Maximizer (2026-11-01, on the plot the operator bought in the live Universe, slot-4-4): "vidim to jako
// nastackovanou pyramidu nejak ale uvnitr z ni bude vychazet neco v tomto smeru", with his drawing of a zigzag arrow going
// up to the right. A stepped pyramid of four slabs, one per risk tier (cyan at the foot into green at the top, the logo's
// gradient), each floating a little over the next with light in the gap between them; the top is open, a shaft lit from
// below, and out of it comes the arrow as he drew it: up, a short dip, then up higher, its head two open barbs. Light runs
// along the arrow as it runs along the app's skill trees, and the arrow's face stays toward the first look, as the
// casino's hologram does. Dark vault steel, a hex plate on every step, a ticker of candles round every slab: the
// palette's colours only.
const CAP = { green: '#00ff88', cyan: '#00cfff', rails: ['#00cfff', '#00dcc4', '#00eea6', '#00ff88'] };
function capHull(lit) {
  const k = lit ? 'capHullL' : 'capHull'; if (TX[k]) return TX[k];
  const t = ctex(1024, 256, (g, W, H) => {
    const R = rng(11), P = W / 8;
    if (lit) { g.fillStyle = '#000'; g.fillRect(0, 0, W, H); }
    else {
      const gr = g.createLinearGradient(0, 0, 0, H); gr.addColorStop(0, '#7a93a8'); gr.addColorStop(0.5, '#566f85'); gr.addColorStop(1, '#3a4f62');
      g.fillStyle = gr; g.fillRect(0, 0, W, H);
      // plates of slightly different tone, a dark joint and a bright edge between them
      for (let i = 0; i < 8; i++) { g.fillStyle = 'rgba(' + (R() < 0.5 ? '255,255,255' : '0,0,0') + ',' + (0.03 + R() * 0.07) + ')'; g.fillRect(i * P, 0, P, H); }
      g.fillStyle = 'rgba(3,8,14,.85)'; for (let i = 0; i <= 8; i++) g.fillRect(i * P - 2, 0, 4, H);
      g.fillStyle = 'rgba(190,220,240,.28)'; for (let i = 0; i <= 8; i++) g.fillRect(i * P + 2, 0, 1.5, H);
      [0.2, 0.8].forEach((f) => { g.fillStyle = 'rgba(3,8,14,.8)'; g.fillRect(0, f * H - 2, W, 4); g.fillStyle = 'rgba(190,220,240,.22)'; g.fillRect(0, f * H + 2, W, 1.5); });
      g.fillStyle = 'rgba(210,235,250,.5)';
      for (let i = 0; i < 8; i++) [[10, 0.09], [P - 14, 0.09], [10, 0.91], [P - 14, 0.91]].forEach(([x, f]) => { g.beginPath(); g.arc(i * P + x, f * H, 2.4, 0, 7); g.fill(); });
    }
    // a row of slit lights along the plate over the ticker and one under it, some dark
    [0.095, 0.905].forEach((f) => {
      for (let i = 0; i < 8; i++) for (let j = 0; j < 5; j++) {
        const on = R() < 0.72, x = i * P + 24 + j * (P - 44) / 5, w = (P - 44) / 5 - 7;
        if (lit) { g.fillStyle = on ? (R() < 0.3 ? '#9ff4ff' : '#7dffc4') : '#000'; g.fillRect(x, f * H - 3, w, 6); }
        else { g.fillStyle = 'rgba(4,10,16,.9)'; g.fillRect(x - 1, f * H - 4, w + 2, 8); }
      }
    });
  });
  if (lit) t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping; TX[k] = t; return t;
}
// The ticker round every slab: candles going up and down on a dark screen, with a faint grid, seamless round its width.
function capTicker() {
  if (TX.capTicker) return TX.capTicker;
  const t = ctex(2048, 128, (g, W, H) => {
    g.fillStyle = '#04201a'; g.fillRect(0, 0, W, H);
    g.fillStyle = 'rgba(0,255,136,.13)'; for (let y = 16; y < H; y += 24) g.fillRect(0, y, W, 2);
    for (let x = 0; x < W; x += 64) g.fillRect(x, 0, 2, H);
    const R = rng(37), N = 52, Cw = W / N, jag = []; for (let i = 0; i < N; i++) jag.push((R() - 0.5) * 0.34);
    // a price that comes back to where it began (sines of whole turns round the width, a jag per candle), so the band has
    // no seam; each candle opens where the last one closed
    const price = (i) => { const a = i / N * Math.PI * 2; return 0.5 + 0.16 * Math.sin(a * 2 + 1) + 0.08 * Math.sin(a * 5) + jag[i % N]; };
    for (let i = 0; i < N; i++) {
      const o = price(i), c = price(i + 1), up = c >= o, top = Math.max(o, c) + 0.04 + R() * 0.07, bot = Math.min(o, c) - 0.04 - R() * 0.07, x = i * Cw + Cw / 2, Y = (v) => H * (1 - v);
      g.fillStyle = up ? '#00ff88' : '#16a8e0';
      g.fillRect(x - 1.5, Y(top), 3, Y(bot) - Y(top));
      g.fillRect(x - 12, Y(Math.max(o, c)), 24, Math.max(6, Y(Math.min(o, c)) - Y(Math.max(o, c))));
    }
  });
  t.wrapS = t.wrapT = THREE.RepeatWrapping; TX.capTicker = t; return t;
}
// The plate on every step: the app's hexagons, cut into dark steel, their lines lit a little. lit: what the emissive reads.
function capHex(lit) {
  const k = lit ? 'capHexL' : 'capHexP'; if (TX[k]) return TX[k];
  const s = 42, W = 6 * s, H = Math.round(2 * Math.sqrt(3) * s);
  const t = ctex(W, H, (g) => {
    g.fillStyle = lit ? '#000' : '#4a5f72'; g.fillRect(0, 0, W, H);
    if (!lit) { const gr = g.createLinearGradient(0, 0, W, H); gr.addColorStop(0, 'rgba(255,255,255,.07)'); gr.addColorStop(1, 'rgba(0,0,0,.14)'); g.fillStyle = gr; g.fillRect(0, 0, W, H); }
    const a = H / 4, hexAt = (cx, cy) => { g.beginPath(); for (let i = 0; i < 6; i++) { const th = i * Math.PI / 3; g[i ? 'lineTo' : 'moveTo'](cx + s * 0.94 * Math.cos(th), cy + s * 0.94 * Math.sin(th)); } g.closePath(); g.stroke(); };
    g.lineWidth = lit ? 1.6 : 5; g.strokeStyle = lit ? '#0a8f60' : 'rgba(8,16,24,.92)';
    for (let col = -1; col <= 4; col++) for (let row = -1; row <= 4; row++) hexAt(col * 1.5 * s, row * 2 * a + (col % 2 ? a : 0));
  });
  if (lit) t.colorSpace = THREE.SRGBColorSpace;
  t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(1 / 0.85, 1 / (0.85 * H / W)); TX[k] = t; return t;
}
// up a shaft: dark at its mouth, full light at its foot, with lit ribs down the walls
function capShaftTex() {
  return TX.capShaft || (TX.capShaft = ctex(128, 128, (g, W, H) => {
    const gr = g.createLinearGradient(0, 0, 0, H); gr.addColorStop(0, '#04261a'); gr.addColorStop(0.45, '#0a7d50'); gr.addColorStop(1, '#6dffbe');
    g.fillStyle = gr; g.fillRect(0, 0, W, H);
    g.fillStyle = 'rgba(0,8,6,.55)'; for (let x = 0; x < W; x += 16) g.fillRect(x, 0, 5, H);
  }));
}
// a polyline's outline, mitred at its corners: the arrow's shape in 2D
function capOutline(pts, w) {
  const L = [], Rr = [], n = pts.length, unit = (x, y) => { const d = Math.hypot(x, y) || 1; return [x / d, y / d]; };
  for (let i = 0; i < n; i++) {
    const a = pts[Math.max(0, i - 1)], c = pts[Math.min(n - 1, i + 1)], p = pts[i];
    const d0 = i > 0 ? unit(p[0] - a[0], p[1] - a[1]) : unit(c[0] - p[0], c[1] - p[1]), d1 = i < n - 1 ? unit(c[0] - p[0], c[1] - p[1]) : d0;
    const n0 = [-d0[1], d0[0]], n1 = [-d1[1], d1[0]], m = unit(n0[0] + n1[0], n0[1] + n1[1]), k = w / Math.max(0.3, m[0] * n1[0] + m[1] * n1[1]);
    L.push(new THREE.Vector2(p[0] + m[0] * k, p[1] + m[1] * k)); Rr.push(new THREE.Vector2(p[0] - m[0] * k, p[1] - m[1] * k));
  }
  return new THREE.Shape(L.concat(Rr.reverse()));
}
function adCapital(body, b) {
  const SQ2 = Math.SQRT2, part = (geo, mat, parent, y = 0) => { const m = ownGeo(new THREE.Mesh(geo, mat)); m.position.y = y; parent.add(m); return m; };
  // a square frustum: a = half its side, so its corner stands a x sqrt 2 from the axis; flat, and u in plates round it
  const frust = (a0, a1, y0, y1, uK = 1) => {
    const l = new THREE.LatheGeometry([new THREE.Vector2(a0 * SQ2, y0), new THREE.Vector2(a1 * SQ2, y1)], 4, Math.PI / 4), g = l.toNonIndexed(); l.dispose(); g.computeVertexNormals();
    const u = g.attributes.uv; for (let i = 0; i < u.count; i++) u.setX(i, u.getX(i) * uK); return g;
  };
  const ringShape = (o, i) => {
    const sq = (a) => [[a, a], [-a, a], [-a, -a], [a, -a]].map(([x, y]) => new THREE.Vector2(x, y));
    const s = new THREE.Shape(sq(o)); s.holes.push(new THREE.Path(sq(i))); return s;
  };
  const plate = (o, i, y) => { const g = new THREE.ShapeGeometry(ringShape(o, i)); g.rotateX(-Math.PI / 2); g.translate(0, y, 0); return g; };
  // a thin bar along the four sides of a square at height y, as one geometry
  const frame = (a, y, w, h) => {
    const bars = [[0, a, 2 * a + w, w], [0, -a, 2 * a + w, w], [a, 0, w, 2 * a + w], [-a, 0, w, 2 * a + w]].map(([x, z, sx, sz]) => { const g = new THREE.BoxGeometry(sx, h, sz); g.translate(x, y, z); return g; });
    const m = mergeGeometries(bars, false); bars.forEach((g) => g.dispose()); return m;
  };
  // a bar between two points
  const bar = (p, q, w) => {
    const d = new THREE.Vector3(q[0] - p[0], q[1] - p[1], q[2] - p[2]), g = new THREE.BoxGeometry(w, d.length(), w);
    g.applyQuaternion(new THREE.Quaternion().setFromUnitVectors(new THREE.Vector3(0, 1, 0), d.clone().normalize()));
    g.translate((p[0] + q[0]) / 2, (p[1] + q[1]) / 2, (p[2] + q[2]) / 2); return g;
  };
  const env = envTex();
  const hull = new THREE.MeshStandardMaterial({ map: capHull(false), color: new THREE.Color(1.8, 1.8, 1.8), emissive: 0xffffff, emissiveMap: capHull(true), emissiveIntensity: 0.6, roughness: 0.48, metalness: 0.28, envMap: env, envMapIntensity: 0.8 });
  const lip = new THREE.MeshStandardMaterial({ color: 0xb8cedd, roughness: 0.25, metalness: 0.8, envMap: env, envMapIntensity: 1.0 });
  const step = new THREE.MeshStandardMaterial({ map: capHex(false), emissive: 0xffffff, emissiveMap: capHex(true), emissiveIntensity: 0.5, roughness: 0.55, metalness: 0.4, envMap: env, envMapIntensity: 0.3 });
  const dark = new THREE.MeshStandardMaterial({ color: 0x0a1119, roughness: 0.6, metalness: 0.5 });
  const tick = capTicker(), screen = new THREE.MeshBasicMaterial({ map: tick, color: new THREE.Color(0.3, 1.25, 1.05) });
  // the stack: half a side at the foot and at the top of each slab, its height; the shaft runs down through the top two
  const LAY = [[3.62, 3.5, 1.15], [2.98, 2.88, 1.0], [2.36, 2.27, 0.9], [1.74, 1.67, 0.8]], GAP = 0.2, SHAFT = 1.3;
  // Linear colours, not look(): the engine pulls every colour two thirds of the way to pastel (PASTEL, at the operator's
  // word) and ACES mixes red into a bright green, so #00ff88 came out mint white. A negative red leans against both; the
  // neon still arrives soft, as everything on this map does.
  const RAILS = [[-0.1, 0.35, 0.85], [-0.2, 0.55, 0.55], [-0.28, 0.8, 0.3], [-0.33, 1.0, 0.12]], gasketBase = new THREE.Color(-0.33, 1.0, 0.12);
  // 86 % of first drawn, with the ring round its corners: no larger than the casino on the map
  const S = 0.86, st = new THREE.Group(); st.scale.setScalar(S); body.add(st);
  const gaskets = [], bin = { hull: [], screen: [], lip: [], step: [], rail: [] };
  // the rails all one draw: each slab's colour in the vertices
  const tinted = (g, c) => { const n = g.index ? g.toNonIndexed() : g, col = new Float32Array(n.attributes.position.count * 3); for (let i = 0; i < col.length; i += 3) col.set(c, i); n.setAttribute('color', new THREE.BufferAttribute(col, 3)); return n; };
  let y = 0;
  LAY.forEach(([a0, a1, h], i) => {
    const uK = 8 * ((a0 + a1) / 2) / 4.96;            // plates the same width on every slab
    bin.hull.push(frust(a0, a1, y, y + h, uK));
    // the ticker, proud of the wall by a hair, in the middle of its height
    const f0 = 0.27, f1 = 0.73, at = (f) => a0 + (a1 - a0) * f;
    bin.screen.push(frust(at(f0) + 0.012, at(f1) + 0.012, y + h * f0, y + h * f1, (a0 + a1) / 2));
    // the lip, a chamfer of bright steel, and the rail on it
    const top = y + h, C = 0.05;
    bin.lip.push(frust(a1, a1 - C, top, top + C));
    bin.rail.push(tinted(frame(a1 + 0.02, top - 0.025, 0.05, 0.05), RAILS[i]));
    // corners: a rib of steel up each edge of the slab
    [[1, 1], [-1, 1], [-1, -1], [1, -1]].forEach(([sx, sz]) => bin.lip.push(bar([sx * a0, y, sz * a0], [sx * a1, top - 0.05, sz * a1], 0.09)));
    // the step's plate, out to the lip, in to under the next slab (or to the shaft's mouth on top)
    const next = LAY[i + 1], inner = next ? next[0] - 0.3 : SHAFT;
    bin.step.push(plate(a1 - C, inner, top + C));
    if (next) {
      // the light in the gap: a band round the core under the next slab, its own material so it can pulse
      const gm = new THREE.MeshBasicMaterial({ color: gasketBase.clone() });
      part(frust(next[0] - 0.05, next[0] - 0.05, top + C, top + GAP + 0.02), gm, st); gaskets.push(gm);
    }
    y = top + GAP;
  });
  // every slab of one material is one draw
  const merged = (list) => { const parts = list.map((g) => (g.index ? g.toNonIndexed() : g)), m = mergeGeometries(parts, false); list.concat(parts).forEach((g) => g.dispose()); return m; };
  part(merged(bin.hull), hull, st); part(merged(bin.screen), screen, st); part(merged(bin.lip), lip, st); part(merged(bin.step), step, st);
  part(merged(bin.rail), new THREE.MeshBasicMaterial({ vertexColors: true }), st);
  const topY = LAY.reduce((s, l) => s + l[2], 0) + GAP * 3 + 0.05, shaftY = topY - 1.75;
  // the shaft: its walls lit from below, a white-green floor, and the light out of its mouth
  const walls = new THREE.MeshBasicMaterial({ map: capShaftTex(), color: new THREE.Color(0.2, 1.3, 0.75), side: THREE.DoubleSide });
  part(frust(SHAFT, SHAFT, shaftY, topY, 4), walls, st);
  const floorM = new THREE.MeshBasicMaterial({ color: new THREE.Color(-0.1, 1.5, 0.5) });
  part(plate(SHAFT, 0.001, shaftY), floorM, st);
  // ledges down the shaft, dark against its light: what shows that it goes down
  part(merged([0.3, 0.72, 1.2].map((d) => frame(SHAFT - 0.05, topY - d, 0.1, 0.07))), dark, st);

  // the arrow, as he drew it: up, a short dip, up higher; its foot in the shaft. In its own plane (x along it, y up),
  // turned about the axis to face the first look.
  const ar = new THREE.Group(); st.add(ar);
  const W = 0.3, D = 0.26, PTS = [[-0.48, shaftY + 0.05], [1.95, 5.95], [2.92, 4.95], [5.15, 8.25]];
  const tip = PTS[3], prev = PTS[2], dl = Math.hypot(tip[0] - prev[0], tip[1] - prev[1]), dir = [(tip[0] - prev[0]) / dl, (tip[1] - prev[1]) / dl];
  const barb = (th, len) => { const c = Math.cos(th), s = Math.sin(th); return [tip[0] + (-dir[0] * c + dir[1] * s) * len, tip[1] + (-dir[0] * s - dir[1] * c) * len]; };
  const stem = PTS.slice(0, 3).concat([[tip[0] - dir[0] * W * 0.6, tip[1] - dir[1] * W * 0.6]]), head = [barb(0.72, 1.45), tip, barb(-0.72, 1.45)];
  const solid = (pts, w, depth, bevel) => {
    const g = new THREE.ExtrudeGeometry(capOutline(pts, w), { depth, bevelEnabled: bevel > 0, bevelThickness: bevel, bevelSize: bevel, bevelSegments: 2, curveSegments: 1, steps: 1 });
    g.translate(0, 0, -depth / 2); return g;
  };
  const armour = new THREE.MeshStandardMaterial({ color: 0x0e4a33, roughness: 0.28, metalness: 0.75, envMap: env, envMapIntensity: 0.7, emissive: 0x00a860, emissiveIntensity: 0.22 });
  const hot = new THREE.MeshBasicMaterial({ color: new THREE.Color(-0.35, 1.1, 0.1) }), hotBase = hot.color.clone();
  part(merged([solid(stem, W - 0.04, D, 0.04), solid(head, W - 0.04, D, 0.04)]), armour, ar);
  part(merged([solid(stem, W * 0.62, D + 0.1, 0), solid(head, W * 0.62, D + 0.1, 0)]), hot, ar);
  // lengths along the arrow, to place light on it
  const lens = [0]; for (let i = 1; i < 4; i++) lens.push(lens[i - 1] + Math.hypot(PTS[i][0] - PTS[i - 1][0], PTS[i][1] - PTS[i - 1][1]));
  const LEN = lens[3], along = (s) => {
    let i = 1; while (i < 3 && s > lens[i]) i++;
    const f = (s - lens[i - 1]) / (lens[i] - lens[i - 1]); return [PTS[i - 1][0] + (PTS[i][0] - PTS[i - 1][0]) * f, PTS[i - 1][1] + (PTS[i][1] - PTS[i - 1][1]) * f];
  };
  const flare = (size, tint = 0xdcffee, k = 1.6) => { const s = new THREE.Sprite(new THREE.SpriteMaterial({ map: flareTex(), color: new THREE.Color(tint).multiplyScalar(k), transparent: true, opacity: 0, blending: THREE.AdditiveBlending, depthWrite: false })); s.scale.setScalar(size); ar.add(s); return s; };
  const sparks = [0, 1, 2, 3, 4, 5].map((i) => { const s = flare(0.5); s.position.z = (i % 2 ? -1 : 1) * (D / 2 + 0.14); return { s, ph: i / 6 }; });
  const pulse = flare(1.5); pulse.position.z = D / 2 + 0.16;
  const tipF = flare(2.4); tipF.position.set(tip[0], tip[1], D / 2 + 0.16);

  b.tick = (t) => {
    // its face toward the first look (the map's azimuth, less the slow turn frame() gives the body), swaying a little
    ar.rotation.y = CO.uvGalaxy.AZ - t * 0.035 + Math.sin(t * 0.4) * 0.14;
    // the light in the gaps climbs the stack
    gaskets.forEach((m, i) => { m.color.copy(gasketBase).multiplyScalar(0.85 + 0.8 * Math.pow(Math.max(0, Math.sin(t * 1.4 - i * 0.9)), 4)); });
    tick.offset.x = -t * 0.018;
    sparks.forEach((o) => { const f = (t * 0.2 + o.ph) % 1, p = along(f * LEN); o.s.position.x = p[0]; o.s.position.y = p[1]; o.s.material.opacity = p[1] < topY ? 0 : Math.min(1, Math.min(f, 1 - f) * 8) * 0.9; });
    // every few seconds a bright pulse runs out of the shaft to the tip, and the tip flares
    const P = t % 3.8, f = P / 1.7, q = along(Math.min(1, f) * LEN);
    pulse.position.x = q[0]; pulse.position.y = q[1]; pulse.material.opacity = f < 1 && q[1] > topY ? 0.95 : 0;
    const burst = f >= 1 ? Math.max(0, 1 - (f - 1) * 1.6) : 0;
    tipF.material.opacity = 0.3 + 0.7 * burst; tipF.scale.setScalar(1.5 + 2.4 * burst);
    hot.color.copy(hotBase).multiplyScalar(0.92 + 0.08 * Math.sin(t * 2.3) + 0.25 * burst);
  };
  b.top = (tip[1] + 0.4) * S; b.bot = 0; b.foot = LAY[0][0] * SQ2 * S;   // foot: its corner, so the ring goes round it
}
