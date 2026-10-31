/* The Cymetica Quest, step by step: what moves (the operator, 2026-10-30: "v kazdem kroku musi byt top animace").

   - the clips (record.py): each plays only while it is on screen and cross-fades into itself at its loop point; the
     office plays only its still part (data-loop-from: "kasli na tu animaci zoomu"). A clip is loaded only when its
     step comes near and let go when it is far: Firefox, his browser, stalls a playing clip (time stuck, never paused)
     while the page's other clips are loading ("animace se nespusti", measured 2026-10-30); its poster stands behind it;
   - step 2's Cymetica pipeline, in step with the workshop clip: an idea typed in, through the pipeline's six
     chambers, a product out; and the ring of the products already built, as holograms, turned by dragging;
   - step 3's users, walking from the Promo Market's briefs to the product;
   - step 4's Quant Lab, started so its agent is born two seconds after the step comes on screen (data-birth);
   - step 5's leaderboard, your company climbing it, passing over the ones it beats.

   Each live one draws only while it is on screen and counts its frames in QUEST_STATE.frames. Figures from QUEST. */
(function () {
  'use strict';
  var Q = window.QUEST, S = window.QUEST_STATE;
  function shot(key) { return '<img src="pics/apps/' + key + '.webp" alt="" width="560" height="315" loading="lazy" draggable="false">'; }
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var clamp = function (x, a, b) { return x < a ? a : x > b ? b : x; };
  var win = function (t, a, b) { return clamp((t - a) / (b - a), 0, 1); };
  var ease = function (x) { x = clamp(x, 0, 1); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
  var fmt = function (v) { return Math.round(v).toLocaleString('en-US'); };

  function seen(el, cb, at) {
    if (!('IntersectionObserver' in window)) { cb(true); return; }
    new IntersectionObserver(function (es) { es.forEach(function (e) { cb(e.isIntersecting); }); }, { threshold: at || 0.04 }).observe(el);
  }
  // draw(t) every frame while `el` is on screen, t in seconds since it first ran
  function run(name, el, draw) {
    var on = false, raf = 0, t0 = 0, last = 0;
    S.frames[name] = 0;
    function tick(now) {
      if (!on) return;
      if (!t0) t0 = now - last * 1000;
      last = (now - t0) / 1000;
      draw(last); S.frames[name]++;
      raf = requestAnimationFrame(tick);
    }
    if (reduce) { draw(1e3); return; }
    seen(el, function (v) {
      if (v && !on) { on = true; t0 = 0; raf = requestAnimationFrame(tick); }
      else if (!v && on) { on = false; cancelAnimationFrame(raf); }
    });
  }

  /* ---------------- a clip filmed on black, keyed into the page's own space ---------------- */
  // data-key (thirteenth take: "pozadi za headquarters je divne, ma byt stejne jako vsude jinde v questu", and "ne jen
  // firefox, musi to ve vsech prohlizecich byt stejne"): the HQ is filmed on black (record.py office) and drawn here
  // through WebGL with its black made see-through, so the page's space stands behind it, in every browser alike (a
  // video's own alpha plays in Chrome and Firefox, never in Safari). Its videos stay as the source, hidden; their
  // cross-fade is mixed here; until one has a frame, its poster is keyed the same way. Without WebGL: the clip on black
  // Two keys. The HQ's (data-key): black to clear, its darkest metal already whole. The Universe's (data-key="glow",
  // fourteenth take: "si nejak smazal ty obezne drahy ... jsou skoro neviditelne"): its lanes are a haze of 2 to 7 %
  // brightness, which the HQ's key cut away, so here the dim light is laid onto the page's sky as light (alpha below its
  // brightness) and only what is bright is whole; either way alpha from the brightest channel, the colour kept (it was
  // filmed over black, so it is already the colour times its alpha)
  var KEY_FS = 'precision mediump float; uniform sampler2D A, B; uniform float w, lo, hi, kg; uniform vec2 sc, of; varying vec2 uv;' +
    'vec4 key(vec3 c) { float m = max(c.r, max(c.g, c.b)); float a = smoothstep(lo, hi, m); return vec4(mix(min(c, vec3(a)), c, kg), a); }' +
    // the loop's cross-fade as a dissolve, one copy into the other: never the two half see-through (measured: one over
    // the other dimmed the HQ by a sixth mid-fade)
    'void main() { vec2 t = uv * sc + of; gl_FragColor = mix(key(texture2D(A, t).rgb), key(texture2D(B, t).rgb), w); }';
  var KEY_VS = 'attribute vec2 p; varying vec2 uv; void main() { uv = p * 0.5 + 0.5; gl_Position = vec4(p, 0.0, 1.0); }';
  function keyed(box, vids, posterUrl) {
    var cv = document.createElement('canvas'), gl = cv.getContext('webgl', { premultipliedAlpha: true, alpha: true, antialias: false });
    if (!gl) return null;
    function sh(type, src) { var s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s); return s; }
    var pr = gl.createProgram();
    gl.attachShader(pr, sh(gl.VERTEX_SHADER, KEY_VS)); gl.attachShader(pr, sh(gl.FRAGMENT_SHADER, KEY_FS)); gl.linkProgram(pr);
    if (!gl.getProgramParameter(pr, gl.LINK_STATUS)) return null;
    gl.useProgram(pr);
    gl.bindBuffer(gl.ARRAY_BUFFER, gl.createBuffer());
    gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
    var lp = gl.getAttribLocation(pr, 'p'); gl.enableVertexAttribArray(lp); gl.vertexAttribPointer(lp, 2, gl.FLOAT, false, 0, 0);
    gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
    var U = {}; ['A', 'B', 'w', 'sc', 'of', 'lo', 'hi', 'kg'].forEach(function (n) { U[n] = gl.getUniformLocation(pr, n); });
    gl.uniform1i(U.A, 0); gl.uniform1i(U.B, 1);
    var glow = box.dataset.key === 'glow';
    gl.uniform1f(U.lo, glow ? 0.0 : 0.025); gl.uniform1f(U.hi, glow ? 0.45 : 0.12); gl.uniform1f(U.kg, glow ? 1 : 0);
    var tex = [0, 1].map(function (i) {
      var t = gl.createTexture(); gl.activeTexture(gl.TEXTURE0 + i); gl.bindTexture(gl.TEXTURE_2D, t);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MAG_FILTER, gl.LINEAR);
      gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE); gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
      gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, 1, 1, 0, gl.RGBA, gl.UNSIGNED_BYTE, new Uint8Array(4));
      return t;
    });
    var poster = new Image(), posterOk = false;
    poster.onload = function () { posterOk = true; draw(); };
    poster.src = posterUrl;
    cv.className = 'keyed';
    box.appendChild(cv);
    box.classList.add('key');
    function up(i, src) { gl.activeTexture(gl.TEXTURE0 + i); gl.bindTexture(gl.TEXTURE_2D, tex[i]); gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, src); }
    function draw() {
      var r = window.devicePixelRatio || 1, w = Math.round(box.clientWidth * r), h = Math.round(box.clientHeight * r);
      if (!w || !h) return;
      var live = vids.map(function (v) { return v.readyState >= 2 && v.getAttribute('src'); });
      var src = live[0] ? vids[0] : live[1] ? vids[1] : posterOk ? poster : null;
      if (!src) return;
      var sw = src.videoWidth || src.naturalWidth, shh = src.videoHeight || src.naturalHeight;
      if (w > sw) { h = Math.round(h * sw / w); w = sw; }
      if (cv.width !== w || cv.height !== h) { cv.width = w; cv.height = h; }
      gl.viewport(0, 0, w, h);
      // as object-fit: cover
      var ca = w / h, va = sw / shh;
      if (ca > va) { gl.uniform2f(U.sc, 1, va / ca); gl.uniform2f(U.of, 0, (1 - va / ca) / 2); }
      else { gl.uniform2f(U.sc, ca / va, 1); gl.uniform2f(U.of, (1 - ca / va) / 2, 0); }
      var w = 0;
      if (src === poster) up(0, poster);
      else {
        // how far the dissolve is into the second copy: its opacity in the cross-fade (the clip's own, below)
        w = !live[0] ? 1 : live[1] ? +getComputedStyle(vids[1]).opacity : 0;
        if (w < 0.998) up(0, vids[0]);
        if (w > 0.002) up(1, vids[1]);
      }
      gl.uniform1f(U.w, w);
      gl.clearColor(0, 0, 0, 0); gl.clear(gl.COLOR_BUFFER_BIT);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
    }
    return { draw: draw };
  }

  /* ---------------- the clips ---------------- */
  // .clip.xf: a second copy of the video under the first; near the end the other one starts (from data-loop-from)
  // and fades in, so the loop has no seam
  var XF = 0.9;
  document.querySelectorAll('.clip').forEach(function (box) {
    var a = box.querySelector('video'), from = +box.dataset.loopFrom || 0, srcEl = a.querySelector('source'), url = srcEl ? srcEl.getAttribute('src') : a.getAttribute('src');
    if (srcEl) srcEl.remove();                       // nothing loads until the step is near
    a.removeAttribute('src'); a.preload = 'none';
    var vids = [a];
    if (box.classList.contains('xf')) { var b = a.cloneNode(true); b.classList.add('b'); box.appendChild(b); vids.push(b); }
    vids.forEach(function (v) { v.muted = true; v.playsInline = true; v.addEventListener('error', function () { if (v.getAttribute('src')) box.classList.add('dead'); }); });
    var key = 'key' in box.dataset ? keyed(box, vids, a.getAttribute('poster')) : null;
    if (key) vids.forEach(function (v) { v.addEventListener('loadeddata', key.draw); v.addEventListener('seeked', key.draw); });
    // the poster behind the video too: a video that does not paint shows its poster, never a hole (a keyed clip draws
    // its own, keyed)
    if (a.getAttribute('poster') && !key) box.style.background = 'url(' + a.getAttribute('poster') + ') 50% 50% / cover no-repeat';
    // data-birth (the Quant Lab: its agent is born that many seconds in): every time the step comes on screen the clip
    // starts two seconds before the birth (fourteenth take: "jak najedu na ten slide tak uz chci aby se hned za 2
    // sekundy zrodil agent, uzivatel bude prvne asi koukat na to nez cist text"); after that it loops whole, the lab's
    // search included
    var birth = +box.dataset.birth || 0, start = birth ? Math.max(0, birth - 2) : from;
    if (birth) S.birth = { from: +start.toFixed(2), born: +(birth - start).toFixed(2) };
    var cur = 0, on = false, raf = 0, started = false;
    function play(v) { if (!v.getAttribute('src')) attach(v); var p = v.play(); if (p && p.catch) p.catch(function () {}); }
    function attach(v) { if (v.getAttribute('src')) return; v.preload = 'auto'; v.src = url; }
    function detach() {
      vids.forEach(function (v) { v.pause(); if (v.getAttribute('src')) { v.removeAttribute('src'); v.load(); } v.style.opacity = ''; });
      cur = 0; started = false;
    }
    function begin() { if (started) return; started = true; attach(a); if (start) a.currentTime = start; play(a); }
    // near: loaded (the copy that cross-fades in too, once it is on screen); far: let go
    if ('IntersectionObserver' in window) {
      new IntersectionObserver(function (es) { es.forEach(function (e) { if (e.isIntersecting) attach(a); else detach(); }); }, { rootMargin: '60% 0px' }).observe(box);
    }
    function tick() {
      if (!on) return;
      if (vids.length > 1) {
        var v = vids[cur], o = vids[1 - cur];
        if (isFinite(v.duration) && v.currentTime > v.duration - XF && o.paused) {
          o.currentTime = from; play(o); o.style.opacity = 1; v.style.opacity = 0;
          setTimeout(function () { v.pause(); }, XF * 1000 + 60);
          cur = 1 - cur;
        }
      }
      if (key) key.draw();
      raf = requestAnimationFrame(tick);
    }
    if (reduce) return;
    seen(box, function (vis) {
      if (vis && !on) {
        on = true;
        if (!started) begin();
        else if (birth) { var o = vids[1 - cur]; if (o) { o.pause(); o.style.opacity = 0; } vids[cur].style.opacity = 1; vids[cur].currentTime = start; play(vids[cur]); }
        else play(vids[cur]);
        if (vids[1]) attach(vids[1]);
        raf = requestAnimationFrame(tick);
        setTimeout(function () { if (on && vids[cur].paused) play(vids[cur]); }, 1200);
      }
      else if (!vis && on) { on = false; cancelAnimationFrame(raf); vids.forEach(function (v) { v.pause(); }); }
    }, birth ? 0.45 : 0.04);
  });

  /* ---------------- step 2: the Cymetica pipeline, an idea in and a product out ---------------- */
  // ("musi to byt viditelne ze je to cymetica pipeline a ze dovnitr vchazi idea a vystupuje moje apka"): in step with
  // the workshop clip's 10 s, whose arms build the same thing: the idea typed in (0.2 - 1.5 s), sent (1.6 - 2 s),
  // through six chambers (2 - 6.2 s), the product out and live (6.3 - 8.8 s), let go (8.8 - 9.6 s); a new idea each time
  (function () {
    var m = document.querySelector('[data-anim=pipeline]'); if (!m) return;
    var vid = document.querySelector('#s2 video');
    var CH = [['doc', 'Spec', 'spec'], ['design', 'Design', 'design'], ['development', 'Build', 'build'], ['shield', 'Security', 'sec'], ['rocket', 'Deploy', 'dep'], ['cloud', 'Hosting', 'host']];
    var FX = {
      spec: '<i></i><i></i><i></i>', design: '<i></i><i></i><i></i><i></i>', build: '<b>&lt;/&gt;</b><i></i>',
      sec: '<i></i>', dep: '<i></i><i></i>', host: '<i></i><i></i><i></i>'
    };
    // what each chamber says while it works (twelfth take: "ta cymetica pipeline mohla by este vypadat lip, ted je to
    // jen 7/10"): its number, a ring that fills round its icon, the chamber lifted and swept by light while it works,
    // and over them all the pipeline's own line: what it is doing now and how far it is
    var DOING = ['Writing the spec', 'Designing every screen', 'Writing the code', 'Checking its security', 'Deploying it', 'Putting it online'];
    m.innerHTML =
      '<div class="inlet"><span class="cap">Your idea</span><p class="say">&ldquo;<span class="tx"></span><span class="caret"></span>&rdquo;</p></div>' +
      '<div class="tube"><div class="hd"><span class="pn"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3.4"/></svg>Cymetica pipeline</span>' +
          '<span class="st"><i></i><b class="sv"></b><span class="pc">0%</span></span></div>' +
        '<div class="track"><span class="lit"></span><span class="orb"></span></div>' +
        '<div class="chs">' + CH.map(function (c, j) {
          return '<div class="ch ' + c[2] + '"><span class="no">0' + (j + 1) + '</span><span class="ci"><svg class="pr" viewBox="0 0 48 48" aria-hidden="true"><circle cx="24" cy="24" r="21"/></svg>' +
            window.QUEST_ICON_SVG(c[0]) + '</span><b>' + c[1] + '</b><span class="fx">' + FX[c[2]] + '</span><span class="ok">&check;</span></div>';
        }).join('') + '</div></div>' +
      // out of the pipeline, the ring of the products already built ("to tocici dej spis jako vystup z te pipeline"):
      // it turns yours to the front as it goes live (the ring's own code, below, reads S.out); no count under it ("to
      // 134 apps already built tam nepis")
      '<div class="outlet">' +
        '<div class="ring" data-anim="apps" aria-label="Products already built with Cymetica, their live pages"><div class="items"></div><span class="base"></span>' +
        '<div class="plate"><b></b></div></div><span class="burst"></span></div>';
    var tx = m.querySelector('.tx'), orb = m.querySelector('.orb'), lit = m.querySelector('.lit'), chs = [].slice.call(m.querySelectorAll('.ch'));
    var sv = m.querySelector('.sv'), pc = m.querySelector('.pc'), st = m.querySelector('.st'), says = '';
    var idea = -1, lastT = 99;
    function setIdea(i) { idea = i; }
    setIdea(0);
    run('pipeline', m, function (t) {
      var T = vid && !vid.paused && vid.readyState >= 2 ? vid.currentTime % 10 : t % 10;
      if (T < lastT - 5) setIdea((idea + 1) % Q.ideas.length);
      lastT = T;
      var d = Q.ideas[idea], say = d[0];
      tx.textContent = say.slice(0, Math.round(say.length * win(T, 0.2, 1.5)));
      m.classList.toggle('typing', T < 1.6);
      m.classList.toggle('sent', T >= 1.6 && T < 8.8);
      var k = win(T, 2.0, 6.2), i = Math.min(5, Math.floor(k * 6));
      var x = T < 2.0 ? 0 : T >= 6.2 ? 1 : (i + ease((k * 6) - i)) / 6;
      orb.style.left = (x * 100).toFixed(2) + '%';
      orb.style.opacity = T >= 1.8 && T < 6.5 ? 1 : 0;
      lit.style.width = (x * 100).toFixed(2) + '%';
      lit.style.opacity = T < 8.8 ? 1 : 1 - win(T, 8.8, 9.6);
      chs.forEach(function (c, j) {
        var a = 2.0 + j * 0.7;
        c.classList.toggle('act', T >= a && T < a + 0.7);
        c.classList.toggle('done', T >= a + 0.7 && T < 8.8);
        c.style.setProperty('--p', (T < 8.8 ? win(T, a, a + 0.7) : 0).toFixed(3));
      });
      // the pipeline's own line
      var now = T < 1.6 ? 'Waiting for your idea' : T < 2.0 ? 'Idea received' : T < 6.2 ? DOING[i] : T < 8.8 ? 'Live · ' + d[1] : 'Ready for the next idea';
      if (now !== says) { says = now; sv.textContent = now; }
      pc.textContent = Math.round((T >= 6.2 && T < 8.8 ? 1 : T < 8.8 ? x : 0) * 100) + '%';
      st.classList.toggle('live', T >= 6.2 && T < 8.8);
      st.classList.toggle('run', T >= 2.0 && T < 6.2);
      m.classList.toggle('out', T >= 6.3 && T < 9.2);
      m.classList.toggle('pop', T >= 6.3 && T < 7.1);
      S.out = { key: d[2], on: T >= 6.0 && T < 9.4 };
    });
  })();

  /* ---------------- step 2: the ring of products already built, the pipeline's output ---------------- */
  // their live pages as holograms ("screeny z live aplikaci holograficky"), turning slowly, turned faster by a drag;
  // the one in front says its name. While the pipeline lets an app out (S.out), the ring turns that app to the front,
  // lit and tagged as yours
  (function () {
    var ring = document.querySelector('[data-anim=apps]'); if (!ring) return;
    var wrap = ring.querySelector('.items'), plate = ring.querySelector('.plate b');
    var items = Q.built.map(function (a) {
      var e = document.createElement('div'); e.className = 'it';
      e.innerHTML = '<span class="mk">' + shot(a[1]) + '</span>';
      wrap.appendChild(e); return { el: e, name: a[0], key: a[1] };
    });
    var n = items.length, drag = 0, vel = 0, down = false, x0 = 0, front = -1, rot = 0, lastT = 0, mine = -1;
    ring.addEventListener('pointerdown', function (e) { down = true; x0 = e.clientX; ring.setPointerCapture(e.pointerId); ring.classList.add('grab'); });
    ring.addEventListener('pointermove', function (e) { if (!down) return; var dx = e.clientX - x0; x0 = e.clientX; drag += dx * 0.45; vel = dx * 0.45; });
    function up() { down = false; ring.classList.remove('grab'); }
    ring.addEventListener('pointerup', up); ring.addEventListener('pointercancel', up);
    ring.addEventListener('wheel', function (e) { if (Math.abs(e.deltaX) > Math.abs(e.deltaY)) { drag -= e.deltaX * 0.3; e.preventDefault(); } }, { passive: false });
    run('apps', ring, function (t) {
      var dt = Math.min(0.1, Math.max(0, t - lastT)); lastT = t;
      if (!down) { drag += vel; vel *= 0.94; }
      // yours coming out: turn the ring the short way round until it stands in front; otherwise turn slowly
      var out = S.out || {}, want = -1;
      if (out.on && !down) for (var j = 0; j < n; j++) if (items[j].key === out.key) want = j;
      if (want >= 0) {
        var gap = ((-want * 360 / n - drag - rot) % 360 + 540) % 360 - 180;
        rot += gap * Math.min(1, dt * 5);
      } else rot += dt * 9;
      // a ring seen a little from above: the front ones lower and bigger, the back ones higher, small and faint
      var W = wrap.clientWidth, R = W * 0.4, base = rot + drag, best = -2, bi = 0;
      items.forEach(function (it, i) {
        var a = (base + i * 360 / n) * Math.PI / 180, z = Math.cos(a), x = Math.sin(a) * R, k = (z + 1) / 2;
        // each page turned to face the way round the ring, as a card on a carousel
        it.el.style.transform = 'translate(' + x.toFixed(1) + 'px,' + (40 * z).toFixed(1) + 'px) translate(-50%,-50%) scale(' + (0.34 + 0.86 * k * k).toFixed(3) + ') rotateY(' + (Math.sin(a) * 38).toFixed(1) + 'deg)';
        it.el.style.opacity = (0.18 + 0.82 * Math.pow(k, 1.6)).toFixed(3);
        it.el.style.zIndex = Math.round(k * 100);
        if (z > best) { best = z; bi = i; }
      });
      if (bi !== front) {
        if (front >= 0) items[front].el.classList.remove('front');
        front = bi; items[bi].el.classList.add('front'); plate.textContent = items[bi].name;
      }
      var m2 = want >= 0 && bi === want ? want : -1;
      if (m2 !== mine) {
        if (mine >= 0) items[mine].el.classList.remove('mine');
        mine = m2; if (mine >= 0) items[mine].el.classList.add('mine');
        ring.classList.toggle('mine', mine >= 0);
        plate.textContent = (mine >= 0 ? 'Your ' : '') + items[bi].name;
      }
    });
  })();

  /* ---------------- the sky: stars that twinkle over the still deep space (#sky) ---------------- */
  // a few hundred, seeded, most faint and white, some cyan and green, a handful with a cross of light; drawn at the
  // window's own pixel ratio (up to 2) and redrawn 30 times a second, not more
  (function () {
    var cv = document.getElementById('twinkle'); if (!cv) return;
    var ctx = cv.getContext('2d'), stars = [], flares = [], W = 0, H = 0;
    var COL = ['#eef6fa', '#cbe8ff', '#00cfff', '#00ff88', '#9fc4ff'];
    function size() {
      var d = Math.min(2, window.devicePixelRatio || 1); W = innerWidth; H = innerHeight;
      cv.width = Math.round(W * d); cv.height = Math.round(H * d); ctx.setTransform(d, 0, 0, d, 0, 0);
      var s = 7; function r() { s = (s * 16807) % 2147483647; return s / 2147483647; }
      stars = []; flares = [];
      var count = Math.max(120, Math.min(320, Math.round(W * H / 8200)));
      for (var i = 0; i < count; i++) {
        var p = r();
        stars.push({ x: r() * W, y: r() * H, r: 0.5 + Math.pow(r(), 2.6) * 1.6, a: 0.25 + r() * 0.7, ph: r() * 6.283, sp: 0.4 + r() * 1.3,
          c: COL[p < 0.64 ? 0 : p < 0.84 ? 1 : p < 0.93 ? 2 : p < 0.97 ? 3 : 4] });
      }
      for (var k = 0; k < 9; k++) flares.push({ x: (0.05 + r() * 0.9) * W, y: (0.08 + r() * 0.86) * H, l: 7 + r() * 10, ph: r() * 6.283, c: k % 3 ? '#eef6fa' : '#00cfff' });
    }
    function draw(t) {
      ctx.clearRect(0, 0, W, H);
      stars.forEach(function (s) {
        var tw = 0.62 + 0.38 * Math.sin(t * s.sp + s.ph);
        ctx.fillStyle = s.c;
        if (s.r > 1.25) { ctx.globalAlpha = s.a * tw * 0.16; ctx.beginPath(); ctx.arc(s.x, s.y, s.r * 3.2, 0, 6.283); ctx.fill(); }
        ctx.globalAlpha = s.a * tw; ctx.beginPath(); ctx.arc(s.x, s.y, s.r, 0, 6.283); ctx.fill();
      });
      flares.forEach(function (f) {
        var p = 0.6 + 0.4 * Math.sin(t * 0.8 + f.ph), L = f.l * p;
        ctx.globalAlpha = 0.5 * p; ctx.strokeStyle = f.c; ctx.lineWidth = 0.8;
        ctx.beginPath(); ctx.moveTo(f.x - L, f.y); ctx.lineTo(f.x + L, f.y); ctx.moveTo(f.x, f.y - L); ctx.lineTo(f.x, f.y + L); ctx.stroke();
        ctx.globalAlpha = 0.9 * p; ctx.fillStyle = '#ffffff'; ctx.beginPath(); ctx.arc(f.x, f.y, 1.2, 0, 6.283); ctx.fill();
      });
      ctx.globalAlpha = 1;
    }
    size(); window.addEventListener('resize', size);
    if (reduce) { draw(0); return; }
    var last = 0;
    (function tick(now) { if (now - last > 33) { last = now; draw(now / 1000); } requestAnimationFrame(tick); })(0);
  })();

  /* ---------------- step 3: users walk from the briefs to the product ---------------- */
  (function () {
    var svg = document.querySelector('[data-anim=flow]'); if (!svg) return;
    var stage = svg.parentElement, promo = stage.querySelector('.holo-at'), near = stage.querySelector('.near');
    var count = stage.querySelector('.users b'), pop = stage.querySelector('.plus');
    var NS = svg.namespaceURI, paths = [], dots = [], users = 0;
    // from the Promo Market's cube, the pool of light under it (x, y in % of its box), to the farmer's ring in its
    // clip, its right side (fourteenth take: the farmer on its lane, record.py FARMER_LANES; the users come in to its
    // ring, never across it)
    var FROM = [[40, 90], [50, 93], [60, 90]], TO = [61, 69];
    // the cube's faces change their page every 2.4 s, two of three lit, as the Promo Market's own (promo_market_v2.js)
    setInterval(function () {
      document.querySelectorAll('.holo:not(.fast) .hstage').forEach(function (st) {
        var imgs = st.querySelectorAll('.f img'); if (!imgs.length) return;
        var k = (+st.dataset.k || 0); st.dataset.k = k + 1;
        imgs.forEach(function (im, j) { im.classList.toggle('on', (j + k) % 3 !== 0); });
      });
    }, 2400);
    FROM.forEach(function () { var p = document.createElementNS(NS, 'path'); p.setAttribute('class', 'fl'); svg.appendChild(p); paths.push(p); });
    // ("step 4 animace je moc rychla"): six users at a time, each 5.2 s from a brief to the product
    var PER = 5.2;
    for (var i = 0; i < 6; i++) { var c = document.createElementNS(NS, 'circle'); c.setAttribute('r', 6); c.setAttribute('class', 'u'); svg.appendChild(c); dots.push({ el: c, path: i % 3, off: i * PER / 6, arrived: -1 }); }
    function layout() {
      var s = stage.getBoundingClientRect(), a = promo.getBoundingClientRect(), b = near.getBoundingClientRect();
      svg.setAttribute('viewBox', '0 0 ' + s.width + ' ' + s.height);
      var tx = b.left - s.left + b.width * TO[0] / 100, ty = b.top - s.top + b.height * TO[1] / 100;
      FROM.forEach(function (f, i) {
        var fx = a.left - s.left + a.width * f[0] / 100, fy = a.top - s.top + a.height * f[1] / 100;
        paths[i].setAttribute('d', 'M' + fx + ' ' + fy + ' C' + (fx - 30) + ' ' + (fy + 70) + ' ' + (tx + 180) + ' ' + (ty + 30) + ' ' + tx + ' ' + ty);
        paths[i].len = paths[i].getTotalLength();
      });
    }
    layout(); window.addEventListener('resize', layout);
    promo.addEventListener('load', layout);
    run('flow', svg, function (t) {
      dots.forEach(function (d) {
        var cyc = (t + d.off) / PER, k = cyc % 1, n = Math.floor(cyc), p = paths[d.path];
        var q = p.getPointAtLength(p.len * ease(k));
        d.el.setAttribute('cx', q.x.toFixed(1)); d.el.setAttribute('cy', q.y.toFixed(1));
        d.el.style.opacity = (Math.sin(Math.PI * k) * 0.9 + 0.1).toFixed(2);
        if (k > 0.96 && d.arrived !== n) {
          d.arrived = n; users++; count.textContent = users.toLocaleString('en-US');
          pop.classList.remove('go'); void pop.offsetWidth; pop.classList.add('go');
        }
      });
    });
  })();

  /* ---------------- step 5: your company climbs the leaderboard ---------------- */
  (function () {
    var box = document.querySelector('[data-anim=climb]'); if (!box) return;
    var rows = Q.board.map(function (r) { return { name: r[0], pts: r[1], mark: r[2], me: false }; });
    var me = { name: Q.you.name, pts: Q.you.from, mark: Q.you.mark, me: true }; rows.push(me);
    var top = Q.board[0][1] > Q.you.to ? Q.board[0][1] : Q.you.to;
    rows.forEach(function (r) {
      r.el = document.createElement('div'); r.el.className = 'row' + (r.me ? ' me' : '');
      r.el.innerHTML = '<span class="rk"></span><span class="badge"><img src="pics/board/' + r.mark + '.webp" alt="" width="64" height="64"></span>' +
        '<span class="nm">' + r.name + (r.me ? '<em>you</em>' : '') + '</span><span class="pp"><span class="bar"><i></i></span><b></b> pts</span><span class="pz"></span>';
      box.appendChild(r.el);
    });
    var STEP = 2.2, P = Q.board.length * STEP + 4.5, last = -1, n = Q.board.length, others = rows.filter(function (r) { return !r.me; }), cur = null, pt = 0;
    // yours, as it passes one, lifted towards you and a little aside, so the one it passes slides under it
    function place(order, passing) {
      order.forEach(function (r, i) {
        r.el.style.transform = 'translateY(' + (i * 100) + '%)' + (r.me && passing ? ' translateX(-14px) scale(1.045)' : '');
        r.el.querySelector('.rk').textContent = i + 1;
        r.el.querySelector('.pz').textContent = i < Q.prizes.length ? Q.prizes[i].toLocaleString('en-US') + ' ' + Q.unit : '';
        r.el.className = 'row' + (r.me ? ' me' + (passing ? ' pass' : '') : '') + (i < Q.prizes.length ? ' paid p' + (i + 1) : '');
      });
    }
    // the points that pass the k-th company from the bottom, with a little to spare
    function beat(k) { return Q.board[n - 1 - k][1] + 40; }
    run('climb', box, function (t) {
      var T = t % P, k = Math.floor(T / STEP), passed, pts;
      if (k >= n) { passed = n; pts = Q.you.to; }
      else {
        var into = ease(win(T - k * STEP, 0.2, 1.3)), from = k ? beat(k - 1) : Q.you.from;
        pts = from + (beat(k) - from) * into; passed = k + (into > 0.6 ? 1 : 0);
      }
      if (T > P - 0.6) { passed = 0; pts = Q.you.from; }
      me.pts = pts;
      var at = n - passed;
      if (at !== last) {
        var up = last >= 0 && at < last;
        cur = others.slice(); cur.splice(at, 0, me); place(cur, up); last = at;
        clearTimeout(pt); if (up) pt = setTimeout(function () { place(cur, false); }, 760);
      }
      rows.forEach(function (r) { r.el.querySelector('.pp b').textContent = fmt(r.pts); r.el.querySelector('.bar i').style.width = (r.pts / top * 100).toFixed(1) + '%'; });
      box.classList.toggle('won', at === 0);
    });
  })();
})();
