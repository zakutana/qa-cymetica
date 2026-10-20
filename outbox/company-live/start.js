/* The /company entry's pictures, all drawn live by the mockup's own 3D engine (u3d.js, its stations from
 * stations.js), nothing painted for the page:
 *  - on the right, Cymetica's sun as the Universe has it -- the collider painting (colliderTex) laid over the scene
 *    at the ball's place, a corona round it -- and a few companies on two orbits round it, slowly, nose first
 *    (the operator, 2026-10-20: "cymetica slunce na te uvodni strane vpravo ... a kolem ni by rotovalo par firem
 *    ruznych"), at about the size the single station had there before;
 *  - "Start a company": a room of the office turning, the Add-department dialog's own renderer (RoomPreview);
 *  - "Explore the Universe": that same sun and its companies seen from above, drawn once into a picture.
 * Nothing on them pulses. */
(function () {
  'use strict';
  var CO = window.CO;

  // the companies round the sun: their station, colour, decks, orbit and where on it they start
  var FLEET = [
    { skin: 'tower', accent: 'cyan', n: 4, orbit: 0, at: 0.4 },
    { skin: 'dome', accent: 'green', n: 5, orbit: 0, at: 2.5 },
    { skin: 'pyramid', accent: 'red', n: 3, orbit: 0, at: 4.5 },
    { skin: 'orbital', accent: 'blue', n: 4, orbit: 1, at: 1.3 },
    { skin: 'rocket', accent: 'green', n: 3, orbit: 1, at: 3.0 },
    { skin: 'vault', accent: 'cyan', n: 5, orbit: 1, at: 4.4 },
    { skin: 'stack', accent: 'red', n: 4, orbit: 1, at: 5.9 }
  ];
  // world units: the sun's ball, the two orbits (wide enough that a company never crosses the ball on the screen
  // from this height), how high the camera looks down (radians above the plane) and how slowly they go round
  var BALL = 8, ORBITS = [20, 28.5], LIFT = 0.72, SPEED = [0.05, 0.034], SHARE = 0.245, SIZE = 1.25;

  function sky(T, U, scene) {
    scene.background = new T.Color(0x01080d);
    scene.add(U.starField(2600, 260, 240, 1.0, 9));
    [[0x00cfff, 0.11, [-160, 60, -220], 320], [0x00ff88, 0.05, [180, -80, -240], 260], [0x3b82f6, 0.06, [-240, -90, 60], 260]].forEach(function (g) {
      var s = U.glowSprite(g[0], g[1], g[3]); s.position.set(g[2][0], g[2][1], g[2][2]); scene.add(s);
    });
  }

  function Showcase(el) {
    var U = CO.U3, T = U.THREE, self = this;
    U.geo();
    this.el = el;
    this.renderer = new T.WebGPURenderer({ antialias: false });   // the bloom pass multisamples (u3d.js, Post)
    this.renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    this.renderer.toneMapping = T.ACESFilmicToneMapping; this.renderer.toneMappingExposure = 1.15;
    el.appendChild(this.renderer.domElement);
    var S = this.scene = new T.Scene(); sky(T, U, S);
    this.camera = new T.PerspectiveCamera(30, 2, 1, 5000);
    // light: the sun's own from the middle, a soft fill from the camera's side, a cool rim, the dark side not black
    S.add(new T.AmbientLight(0x1a2230, 0.8), new T.HemisphereLight(0xdfe8f2, 0x05070a, 0.5));
    var sunLight = new T.PointLight(0xffe0b0, 3.2, 0, 0); S.add(sunLight);
    this.fill = new T.DirectionalLight(0xdfe8f2, 1.2); S.add(this.fill, this.fill.target);
    var rim = new T.DirectionalLight(0x00cfff, 0.5); rim.position.set(60, -20, -80); S.add(rim);
    // the corona: the Universe's three glows round the ball, in the same proportion to it
    [[2.64, 0.07, 0xffb04a], [4.3, 0.035, 0xff9a3c], [6.1, 0.025, 0x3b9dff]].forEach(function (c) { S.add(U.glowSprite(c[2], c[1], BALL * c[0])); });
    // the orbits: thin lines of the Universe's cyan, lying on the plane
    ORBITS.forEach(function (r, i) {
      var m = new T.Mesh(new T.TorusGeometry(r, 0.05, 6, 360), new T.MeshBasicMaterial({ color: new T.Color(i ? 0x3f7d8a : 0x80c8d0).multiplyScalar(0.9), transparent: true, opacity: 0.55, blending: T.AdditiveBlending, depthWrite: false }));
      m.rotation.x = Math.PI / 2; S.add(m);
    });
    // the companies, nose first along their orbits; the Universe's ring and pool under each are its pickers, not here
    this.fleet = FLEET.map(function (f, i) {
      var p = U.makeStation({ skin: f.skin, accent: f.accent, public: true, departments: new Array(f.n).fill(0), status: 'active' }, 31 + i * 7, {});
      p.ring.visible = false; p.pool.visible = false; p.halo.material.opacity = 0.1;
      p.root.scale.setScalar(SIZE); S.add(p.root);
      return { p: p, f: f, r: ORBITS[f.orbit], a: f.at, w: SPEED[f.orbit] };
    });
    // the ball itself: the painting, over the scene where the ball is (as the Universe lays it), two of them turning
    // against each other over a blurred copy, its glow
    var ce = this.col = document.createElement('div'); ce.className = 'lp-col';
    var p1 = U.colliderTex(1).image, glow = document.createElement('canvas'); glow.width = p1.width; glow.height = p1.height; glow.getContext('2d').drawImage(p1, 0, 0); glow.className = 'g1';
    ce.appendChild(glow);
    [1, 2].forEach(function (seed) { var cv = U.colliderTex(seed).image; cv.className = 'l' + seed; ce.appendChild(cv); });
    el.appendChild(ce);
    this.clock = new T.Clock(); this.last = 0; this.work = 0;
    this.v = new T.Vector3(); this.c = new T.Vector3(); this.rt = new T.Vector3();
    this.renderer.init().then(function () {
      try { self.post = new U.Post(self.renderer, S, self.camera, 0.5, 0.3, 0.8, { sat: 0.9 }); } catch (e) { self.post = null; }
      self.resize();
      self.renderer.setAnimationLoop(function () { self.frame(); });
      self.ready = true;
      if (self.onReady) self.onReady();
    }).catch(function (e) { console.error('the entry scene could not start:', e); });
    if (window.ResizeObserver) new ResizeObserver(function () { self.resize(); }).observe(el);
  }
  // the camera: looking down on the sun from LIFT, at the distance where the ball is about a third of the height
  Showcase.prototype.aim = function (cam, h, ballShare) {
    var T = CO.U3.THREE, d = BALL * 2 / ballShare / (2 * Math.tan(T.MathUtils.degToRad(cam.fov) / 2));
    cam.position.set(0, Math.sin(LIFT) * d, Math.cos(LIFT) * d); cam.lookAt(0, 0, 0); cam.updateMatrixWorld();
  };
  Showcase.prototype.resize = function () {
    var w = this.el.clientWidth, h = this.el.clientHeight; if (!w || !h) return;
    this.w = w; this.h = h;
    this.camera.aspect = w / h; this.camera.updateProjectionMatrix(); this.renderer.setSize(w, h, false);
    this.aim(this.camera, h, SHARE);
    this.fill.position.copy(this.camera.position).add(new CO.U3.THREE.Vector3(-30, 60, 0)); this.fill.target.position.set(0, 0, 0);
  };
  Showcase.prototype.frame = function () {
    if (!this.w) return;
    var t = this.clock.getElapsedTime(), dt = Math.min(0.1, t - this.last); this.last = t;
    this.fleet.forEach(function (s, i) {
      s.a += s.w * dt;
      var x = Math.cos(s.a) * s.r, z = Math.sin(s.a) * s.r;
      // nose first: +z of a station is its bow, turned onto the orbit's way (angle rising)
      s.p.root.position.set(x, Math.sin(t * 0.5 + i) * 0.35, z); s.p.root.rotation.y = -s.a;
      s.p.b.tick(t);
    });
    // now and then a company's decks light up and go out again: its departments at work
    if (t > this.work) {
      this.work = t + 2.5;
      this.fleet.forEach(function (s) { var on = []; for (var k = 0; k < s.f.n; k++) if (Math.random() < 0.35) on.push(k); s.p.b.paint(on, ''); });
    }
    if (this.post) this.post.render(); else this.renderer.render(this.scene, this.camera);
    this.place(this.camera, this.w, this.h, this.col);
  };
  // the painting over the ball: its middle at the ball's on the screen, scaled so its ball (360 of its 600 px) is the
  // ball's width there -- the Universe's own sum (overlay() in u3d.js): the ball's radius on the screen over 180
  Showcase.prototype.place = function (cam, w, h, el) {
    var v = this.v.set(0, 0, 0).project(cam), right = this.rt.setFromMatrixColumn(cam.matrixWorld, 0).normalize();
    var c = this.c.set(0, 0, 0).addScaledVector(right, BALL).project(cam), s = Math.abs(c.x - v.x) * w / 360;
    var x = (v.x + 1) / 2 * w, y = (1 - v.y) / 2 * h;
    el.style.transform = 'translate(' + (x - 300).toFixed(1) + 'px,' + (y - 300).toFixed(1) + 'px) scale(' + s.toFixed(4) + ')';
    return { x: x, y: y, s: s };
  };
  // The Universe tile's picture: the same scene from higher and further, drawn once into a render target, read back
  // and the painting laid on it at the ball's place (as the page lays it)
  Showcase.prototype.picture = function (W, H, done) {
    var self = this, U = CO.U3, T = U.THREE, r = this.renderer, cam = this.camera, rt = new T.RenderTarget(W, H);
    var keep = { p: cam.position.clone(), q: cam.quaternion.clone(), a: cam.aspect }, lift = LIFT;
    LIFT = 1.0; cam.aspect = W / H; cam.updateProjectionMatrix(); this.aim(cam, H, 0.27); LIFT = lift;
    var at = this.place(cam, W, H, document.createElement('div'));
    r.setRenderTarget(rt); if (this.post) this.post.render(); else r.render(this.scene, cam); r.setRenderTarget(null);
    cam.position.copy(keep.p); cam.quaternion.copy(keep.q); cam.aspect = keep.a; cam.updateProjectionMatrix(); cam.updateMatrixWorld();
    r.readRenderTargetPixelsAsync(rt, 0, 0, W, H).then(function (px) {
      var flip = !(r.backend && r.backend.isWebGPUBackend), c = document.createElement('canvas'); c.width = W; c.height = H;
      var g = c.getContext('2d'), img = g.createImageData(W, H);
      for (var y = 0; y < H; y++) { var sy = flip ? H - 1 - y : y; img.data.set(px.subarray(sy * W * 4, (sy + 1) * W * 4), y * W * 4); }
      for (var i = 3; i < img.data.length; i += 4) img.data[i] = 255;
      g.putImageData(img, 0, 0);
      g.globalCompositeOperation = 'screen';
      var p = U.colliderTex(1).image, size = 600 * at.s; g.drawImage(p, at.x - size / 2, at.y - size / 2, size, size);
      rt.dispose(); done(c);
    }, function () { rt.dispose(); done(null); });
  };

  // "Start a company": a room of the office, turning
  function room(el) {
    if (!CO.U3.roomPreview) return;
    var rp = CO.U3.roomPreview(el);
    rp.set({ key: 'development', name: 'Development', experts: ['developer', 'researcher'] });
  }

  function go() {
    var U = CO.U3; if (!U || !U.ok || !U.Post) return;
    var space = document.getElementById('lp-space'), sc = new Showcase(space);
    sc.onReady = function () {
      // the Universe tile's picture once the companies are drawn: a few frames in, so every station's shaders are made
      setTimeout(function () {
        // (a width in 64s: WebGPU reads a picture back in rows of 256 bytes, as thumbs() in u3d.js says)
        var box = document.getElementById('lp-uvpic'), W = Math.ceil(box.clientWidth * 2 / 64) * 64, H = Math.round(box.clientHeight * 2);
        if (W && H) sc.picture(W, H, function (c) { if (c) { c.className = 'pic'; box.appendChild(c); } });
      }, 900);
      // the room after the sun, so the two engines do not build at once
      setTimeout(function () { room(document.getElementById('lp-room')); }, 400);
    };
  }
  var done = false, start = function () { if (done) return; done = true; go(); };
  if (CO.U3 && CO.U3.skins) start();
  else { window.addEventListener('co3d-skins', start, { once: true }); setTimeout(function () { if (CO.U3 && CO.U3.ok) start(); }, 8000); }
})();
