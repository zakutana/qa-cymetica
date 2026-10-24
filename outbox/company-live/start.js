/* The /company entry's pictures, all drawn live by the mockup's own 3D engine (u3d.js, its stations from
 * stations.js), nothing painted for the page, in the office's own space (entry3d.js: its navy, nebulae and glow):
 *  - on the right, Cymetica's sun as the Universe has it -- the collider painting (colliderTex) laid over the scene
 *    at the ball's place, a corona round it -- and a few companies on two orbits round it, slowly, nose first
 *    (the operator, 2026-10-20: "cymetica slunce na te uvodni strane vpravo ... a kolem ni by rotovalo par firem
 *    ruznych"), at about the size the single station had there before;
 *  - "Start a company": a room of the office turning, the Add-department dialog's own renderer (RoomPreview);
 *  - "Explore the Universe": the same sun and companies seen from above, live, by a small renderer of its own drawing
 *    the same scene at the tile's own size. (A picture read back from the big renderer came out squashed: its bloom
 *    pass is sized to the big canvas, "nejak sisate", 2026-10-20.)
 * Nothing on them pulses. */
(function () {
  'use strict';
  var CO = window.CO;

  // The loading screen (boot.css, as index.html's): over the page until the sun and both doors have drawn, so it never
  // shows half built -- the painting over a sun not yet there, a door's black box ("nevadi kdyz se neco nacita ale
  // musis tam nejakou brutalne top animaci zobrazit misto toho", 2026-10-20). Its number is the work done.
  var boot0 = document.getElementById('boot'), bootP = 0;
  function bootSet(p, what) {
    if (!boot0 || p <= bootP) return; bootP = p;
    boot0.querySelector('.ld-pct').textContent = Math.round(p);
    boot0.querySelector('.ld-bar i').style.transform = 'scaleX(' + Math.min(1, p / 100).toFixed(3) + ')';
    if (what) boot0.querySelector('.ld-what').textContent = what;
  }
  function bootDone() {
    var el = boot0; if (!el) return; bootSet(100, 'READY'); boot0 = null;
    setTimeout(function () { el.classList.add('gone'); setTimeout(function () { el.remove(); }, 900); }, 150);
  }
  bootSet(18, 'ENGINE');
  setTimeout(bootDone, 20000);   // (never in the way for good)
  // drawn: the sun's scene and the room's door each a frame on the screen (the Universe's door draws with the sun)
  function whenDrawn(sc) {
    (function w() {
      if (sc.frames > 0) bootSet(72, 'OFFICE');
      if (sc.frames > 0 && sc.room && sc.room.frames > 0) return bootDone();
      requestAnimationFrame(w);
    })();
  }

  // The companies round the sun: their station, colour, decks, orbit and where on it they stand. Three a orbit, a
  // third of a turn apart, the outer three half way between the inner ones, and the whole turning as one (one speed
  // for both orbits): no two ever come one over the other ("tyto dve firmy jsou moc u sebe", 2026-10-20 -- with
  // two speeds the orbits drifted through each other and lined two companies up).
  var T3 = Math.PI * 2 / 3, FLEET = [
    { skin: 'tower', accent: 'cyan', n: 4, orbit: 0, at: 0.4 },
    { skin: 'dome', accent: 'green', n: 5, orbit: 0, at: 0.4 + T3 },
    { skin: 'pyramid', accent: 'red', n: 3, orbit: 0, at: 0.4 + 2 * T3 },
    { skin: 'orbital', accent: 'blue', n: 4, orbit: 1, at: 0.4 + T3 / 2 },
    { skin: 'rocket', accent: 'green', n: 3, orbit: 1, at: 0.4 + T3 * 1.5 },
    { skin: 'vault', accent: 'cyan', n: 5, orbit: 1, at: 0.4 + T3 * 2.5 }
  ];
  // world units: the sun's ball, the two orbits (wide enough that a company never crosses the ball on the screen
  // from this height), how high the camera looks down (radians above the plane), how slowly they go round, how much
  // of the stage's height the ball takes, how big the stations are drawn
  var BALL = 8, ORBITS = [20, 28.5], LIFT = 0.72, SPEED = [0.04, 0.04], SHARE = 0.245, SIZE = 1.25;

  // a renderer as the mockup makes them: no antialias of its own (the bloom pass multisamples; u3d.js says why)
  function renderer(T, el) {
    var r = new T.WebGPURenderer({ antialias: false });
    r.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
    r.toneMapping = T.ACESFilmicToneMapping; r.toneMappingExposure = 1.15;
    el.appendChild(r.domElement);
    return r;
  }
  // the camera looking down on the sun from lift, at the distance where the ball is share of the view's height
  function aim(T, cam, lift, share) {
    var d = BALL * 2 / share / (2 * Math.tan(T.MathUtils.degToRad(cam.fov) / 2));
    cam.position.set(0, Math.sin(lift) * d, Math.cos(lift) * d); cam.lookAt(0, 0, 0); cam.updateMatrixWorld();
  }
  // the painting over the ball, in its own element: middle at the ball's on the screen, scaled so its ball (360 of
  // its 600 px) is the ball's width there -- the Universe's own sum (overlay() in u3d.js)
  function painting(U, host) {
    var ce = document.createElement('div'); ce.className = 'lp-col';
    var p1 = U.colliderTex(1).image, glow = document.createElement('canvas'); glow.width = p1.width; glow.height = p1.height; glow.getContext('2d').drawImage(p1, 0, 0); glow.className = 'g1';
    ce.appendChild(glow);
    [1, 2].forEach(function (seed) { var cv = document.createElement('canvas'), src = U.colliderTex(seed).image; cv.width = src.width; cv.height = src.height; cv.getContext('2d').drawImage(src, 0, 0); cv.className = 'l' + seed; ce.appendChild(cv); });
    host.appendChild(ce);
    return ce;
  }
  var V = [], place = function (T, cam, w, h, el) {
    var v = (V[0] || (V[0] = new T.Vector3())).set(0, 0, 0).project(cam), right = (V[1] || (V[1] = new T.Vector3())).setFromMatrixColumn(cam.matrixWorld, 0).normalize();
    var c = (V[2] || (V[2] = new T.Vector3())).set(0, 0, 0).addScaledVector(right, BALL).project(cam), s = Math.abs(c.x - v.x) * w / 360;
    el.style.transform = 'translate(' + ((v.x + 1) / 2 * w - 300).toFixed(1) + 'px,' + ((1 - v.y) / 2 * h - 300).toFixed(1) + 'px) scale(' + s.toFixed(4) + ')';
  };

  function Showcase(el, tileEl) {
    var U = CO.U3, T = U.THREE, self = this;
    U.geo();
    this.el = el; this.renderer = renderer(T, el);
    var S = this.scene = new T.Scene();
    this.camera = new T.PerspectiveCamera(30, 2, 1, 2000);
    this.sky = CO.E3.sky(S, -Math.PI / 4);
    // light: the stations' own, the sun's from the middle, a soft fill from the camera's side
    CO.E3.lights(S);
    S.add(new T.PointLight(0xffe0b0, 2.6, 0, 0));
    this.fill = new T.DirectionalLight(0xdfe8f2, 0.9); S.add(this.fill, this.fill.target);
    // the corona: the Universe's three glows round the ball, in the same proportion to it
    [[2.64, 0.07, 0xffb04a], [4.3, 0.035, 0xff9a3c], [6.1, 0.025, 0x3b9dff]].forEach(function (c) { S.add(U.glowSprite(c[2], c[1], BALL * c[0])); });
    // the orbits: lanes of drifting light-dust, as the Universe's are (u3d.js dustLane, 2026-10-23: "uprav ty prstence i
    // na uvodni strane"), not lines -- the Universe's cyan, the inner one paler; they flow the way the companies go,
    // brighter on the far side of the view; k scales the dots to this scene (its ball is a third of the Universe's)
    var R = CO.uvRng(5), P = [];
    ORBITS.forEach(function (r, i) {
      var o = { omega: i ? -0.065 : -0.08, k: 0.5, den: 2.4, col: new T.Color(i ? 0x5cc8f2 : 0x8fe6ea).multiplyScalar(2.2) };
      U.dustLane(P, R, r, 'thread', o); U.dustLane(P, R, r, 'haze', o); U.dustLane(P, R, r, 'star', o);
    });
    S.add(U.dustMesh(P, 3.6));
    // the companies, nose first along their orbits; the Universe's ring and pool under each are its pickers, not here
    this.fleet = FLEET.map(function (f, i) {
      var p = U.makeStation({ skin: f.skin, accent: f.accent, public: true, departments: new Array(f.n).fill(0), status: 'active' }, 31 + i * 7, {});
      p.ring.visible = false; p.pool.visible = false; p.halo.material.opacity = 0.1;
      p.root.scale.setScalar(SIZE); S.add(p.root);
      return { p: p, f: f, r: ORBITS[f.orbit], a: f.at, w: SPEED[f.orbit] };
    });
    this.col = painting(U, el);
    // the Universe tile: the same scene from higher up, its own renderer and bloom at the tile's own size
    if (tileEl) {
      this.tile = { el: tileEl, r: renderer(T, tileEl), cam: new T.PerspectiveCamera(30, 1, 1, 2000) };
      this.tile.col = painting(U, tileEl);
    }
    this.clock = new T.Clock(); this.last = 0; this.work = 0;
    var starts = [this.renderer.init()];
    if (this.tile) starts.push(this.tile.r.init());
    Promise.all(starts).then(function () {
      try { self.post = new U.Post(self.renderer, S, self.camera, 0.5, 0.3, 0.8, { sat: 0.9 }); } catch (e) { self.post = null; }
      if (self.tile) { try { self.tile.post = new U.Post(self.tile.r, S, self.tile.cam, 0.5, 0.3, 0.8, { sat: 0.9 }); } catch (e) { self.tile.post = null; } }
      self.resize();
      self.renderer.setAnimationLoop(function () { self.frame(); });
      self.ready = true;
      if (self.onReady) self.onReady();
    }).catch(function (e) { console.error('the entry scene could not start:', e); });
    if (window.ResizeObserver) new ResizeObserver(function () { self.resize(); }).observe(el);
  }
  Showcase.prototype.resize = function () {
    var T = CO.U3.THREE, w = this.el.clientWidth, h = this.el.clientHeight; if (!w || !h) return;
    this.w = w; this.h = h;
    this.camera.aspect = w / h; this.camera.updateProjectionMatrix(); this.renderer.setSize(w, h, false);
    aim(T, this.camera, LIFT, SHARE);
    this.fill.position.copy(this.camera.position).add(new T.Vector3(-30, 60, 0)); this.fill.target.position.set(0, 0, 0);
    var t = this.tile;
    if (t) {
      t.w = t.el.clientWidth; t.h = t.el.clientHeight;
      if (t.w && t.h) { t.cam.aspect = t.w / t.h; t.cam.updateProjectionMatrix(); t.r.setSize(t.w, t.h, false); aim(T, t.cam, 1.0, 0.27); }
    }
  };
  Showcase.prototype.frame = function () {
    if (!this.w) return;
    var T = CO.U3.THREE, t = this.clock.getElapsedTime(), dt = Math.min(0.1, t - this.last); this.last = t;
    this.fleet.forEach(function (s, i) {
      s.a += s.w * dt;
      // nose first: +z of a station is its bow, turned onto the orbit's way (angle rising)
      s.p.root.position.set(Math.cos(s.a) * s.r, Math.sin(t * 0.5 + i) * 0.35, Math.sin(s.a) * s.r); s.p.root.rotation.y = -s.a;
      s.p.b.tick(t);
    });
    // now and then a company's decks light up and go out again: its departments at work
    if (t > this.work) {
      this.work = t + 2.5;
      this.fleet.forEach(function (s) { var on = []; for (var k = 0; k < s.f.n; k++) if (Math.random() < 0.35) on.push(k); s.p.b.paint(on, ''); });
    }
    this.sky.position.copy(this.camera.position);
    if (this.post) this.post.render(); else this.renderer.render(this.scene, this.camera);
    this.frames = (this.frames || 0) + 1;
    place(T, this.camera, this.w, this.h, this.col);
    var tl = this.tile;
    // the tile without the sky's stars and nebulae: from that high its star field read as rows of dots; its navy stays
    if (tl && tl.w) {
      this.sky.visible = false;
      if (tl.post) tl.post.render(); else tl.r.render(this.scene, tl.cam);
      this.sky.visible = true;
      place(T, tl.cam, tl.w, tl.h, tl.col);
    }
  };

  // "Start a company": a room of the office, turning -- a department of one's own in the Operations look (curved
  // command desk, comms and supply cabinets, the coffee corner with its two stools), as the Add-department dialog
  // shows a new one ("v te dlazdici build a company vymen mistnost za tuto", 2026-10-20)
  function room(el) {
    if (!CO.U3.roomPreview) return null;
    var rp = CO.U3.roomPreview(el); rp.set({ key: 'custom', name: '', experts: ['researcher'], look: 'ops' });
    return rp;
  }
  // A door: the page's scenes stopped and the page faded out first, then the next page -- not a page that stutters
  // while the next one is fetched
  var SC = null;
  Array.prototype.forEach.call(document.querySelectorAll('.lp-tile'), function (a) {
    a.addEventListener('click', function (e) {
      if (e.button || e.metaKey || e.ctrlKey || e.shiftKey) return;
      e.preventDefault();
      if (SC) SC.stop();
      document.body.classList.add('lp-leave');
      setTimeout(function () { location.href = a.getAttribute('href'); }, 220);
    });
  });
  Showcase.prototype.stop = function () {
    [this.renderer, this.tile && this.tile.r, this.room && this.room.renderer].forEach(function (r) { if (r) r.setAnimationLoop(null); });
  };

  function go() {
    var U = CO.U3; if (!U || !U.ok || !U.Post || !CO.E3) return bootDone();
    bootSet(34, 'UNIVERSE');
    var sc = SC = new Showcase(document.getElementById('lp-space'), document.getElementById('lp-uvpic'));
    // the room after the sun, so the two engines do not build at once
    sc.onReady = function () {
      bootSet(55, 'UNIVERSE');
      setTimeout(function () { sc.room = room(document.getElementById('lp-room')); if (!sc.room) bootDone(); else bootSet(80, 'OFFICE'); }, 400);
    };
    whenDrawn(sc);
  }
  var done = false, start = function () { if (done) return; done = true; go(); };
  if (CO.U3 && CO.U3.skins) start();
  else { window.addEventListener('co3d-skins', start, { once: true }); setTimeout(function () { if (CO.U3 && CO.U3.ok) start(); }, 8000); }
})();
