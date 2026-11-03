/* The Cymetica Quest, step by step: what moves (the operator, 2026-10-30: "v kazdem kroku musi byt top animace").

   - the clips (record.py): each plays only while it is on screen and cross-fades into itself at its loop point; the
     office plays only its still part (data-loop-from: "kasli na tu animaci zoomu"). A clip is loaded only when its
     step comes near and let go when it is far: Firefox, his browser, stalls a playing clip (time stuck, never paused)
     while the page's other clips are loading ("animace se nespusti", measured 2026-10-30); its poster stands behind it;
   - step 2's Cymetica pipeline, in step with the workshop clip: an idea typed in, through the pipeline's six
     chambers, a product out; and the ring of the products already built, as holograms, turned by dragging;
   - step 3's users, walking from the Promo Market to the product, and the Promo Market cube's faces changing;
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
  // filmed over black, so it is already the colour times its alpha), less the codec's faint noise in the black ("zrnity")
  // While the pointer is on something in the clip (step 3, below) everything outside hr (x0, y0, x1, y1 of the clip)
  // steps back, softly, so the lanes running out of hr carry no edge
  var KEY_FS = 'precision mediump float; uniform sampler2D A, B; uniform float w, lo, hi, kg, hs; uniform vec2 sc, of; uniform vec4 hr; varying vec2 uv;' +
    'vec4 key(vec3 c) { float m = max(c.r, max(c.g, c.b)); float a = smoothstep(lo, hi, m); c *= mix(1.0, smoothstep(0.006, 0.024, m), kg); return vec4(mix(min(c, vec3(a)), c, kg), a); }' +
    // the loop's cross-fade as a dissolve, one copy into the other: never the two half see-through (measured: one over
    // the other dimmed the HQ by a sixth mid-fade)
    'void main() { vec2 t = uv * sc + of; vec4 o = mix(key(texture2D(A, t).rgb), key(texture2D(B, t).rgb), w);' +
    ' if (hs > 0.001) { vec2 q = max(hr.xy - t, t - hr.zw); o *= 1.0 - 0.55 * hs * smoothstep(0.0, 0.06, length(max(q, vec2(0.0)))); }' +
    ' gl_FragColor = o; }';
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
    var U = {}; ['A', 'B', 'w', 'sc', 'of', 'lo', 'hi', 'kg', 'hs', 'hr'].forEach(function (n) { U[n] = gl.getUniformLocation(pr, n); });
    gl.uniform1i(U.A, 0); gl.uniform1i(U.B, 1);
    var glow = box.dataset.key === 'glow', hot = null, hv = 0;
    gl.uniform1f(U.lo, glow ? 0.0 : 0.025); gl.uniform1f(U.hi, glow ? 0.45 : 0.12); gl.uniform1f(U.kg, glow ? 1 : 0);
    gl.uniform1f(U.hs, 0);
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
      var ca = w / h, va = sw / shh, sx = ca > va ? 1 : ca / va, sy = ca > va ? va / ca : 1;
      gl.uniform2f(U.sc, sx, sy); gl.uniform2f(U.of, (1 - sx) / 2, (1 - sy) / 2);
      hv = reduce ? (hot ? 1 : 0) : hv + ((hot ? 1 : 0) - hv) * 0.2;
      gl.uniform1f(U.hs, hv < 0.004 ? 0 : hv);
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
    // hot([x0, y0, x1, y1]) in the clip from its top left: the rest back; [] all of it back; null: as it was
    function hotSet(r) {
      hot = r;
      if (r) { var e = r.length ? r : [-9, -9, -9, -9]; gl.uniform4f(U.hr, e[0], 1 - e[3], e[2], 1 - e[1]); }
      if (reduce) draw();
    }
    return { draw: draw, hot: hotSet };
  }

  /* ---------------- the clips ---------------- */
  // .clip.xf: a second copy of the video under the first; near the end the other one starts (from data-loop-from)
  // and fades in, so the loop has no seam
  var XF = 0.9;
  // ("snad at se to vse stahne naraz ... jak nekde doscroluju a nebude tam video spsuiteno"): once the page has loaded,
  // every clip is fetched in the background, two at a time in the page's order, and kept in memory; a clip that comes on
  // screen then starts from memory, whatever the line. One that is reached first streams from the network as before.
  // Not on a saved-data or 2G line.
  var clipUrls = [], CLIPBLOB = {}, STREAM = {}, streamers = [], PQ = [], INFLIGHT = null, PF = false;
  // one background fetch at a time (two would each be half as fast and neither ready), each time the clip nearest below
  // where the visitor is; what they have scrolled past comes last. A clip that has to stream now (reached before its turn)
  // gets the whole line: the fetch in flight is dropped and queued again, and none starts while one is still buffering.
  function streamStalled() { return streamers.some(function (v) { return v.getAttribute('src') && v.readyState < 3 && v.networkState === 2; }); }
  function prefetchNext() {
    if (!PF || INFLIGHT || !PQ.length) return;
    if (streamStalled()) { setTimeout(prefetchNext, 500); return; }
    var vh = innerHeight, bi = -1, bd = 1e9;
    PQ.forEach(function (it, i) {
      if (STREAM[it.url]) return;                         // already coming down on its own: not twice
      var d = 1e8;
      it.boxes.forEach(function (bx) {
        var r = bx.getBoundingClientRect();
        d = Math.min(d, r.top > vh ? r.top - vh : r.bottom < 0 ? 3 * vh - r.bottom : 0);
      });
      if (d < bd) { bd = d; bi = i; }
    });
    if (bi < 0) return;
    var it = PQ.splice(bi, 1)[0], ctrl = window.AbortController ? new AbortController() : null;
    INFLIGHT = { it: it, ctrl: ctrl };
    fetch(it.url, ctrl ? { signal: ctrl.signal } : undefined).then(function (r) { return r.ok ? r.blob() : null; })
      .then(function (b) { if (b) CLIPBLOB[it.url] = URL.createObjectURL(b); })
      .catch(function (e) { if (e && e.name === 'AbortError') PQ.push(it); })
      .then(function () { INFLIGHT = null; prefetchNext(); });
  }
  function prefetchClips() {
    var cn = navigator.connection;
    if (reduce || !window.fetch || !window.URL || (cn && (cn.saveData || /2g/.test(cn.effectiveType || '')))) return;
    PF = true; PQ = clipUrls.slice(); prefetchNext();
  }
  document.querySelectorAll('.clip').forEach(function (box) {
    var a = box.querySelector('video'), from = +box.dataset.loopFrom || 0, srcEls = [].slice.call(a.querySelectorAll('source')), url = a.getAttribute('src');
    // the first <source> this browser can play, in the page's order (H.264 first: every phone and laptop decodes it in hardware; WebM VP9 after it)
    for (var si = 0; si < srcEls.length; si++) { var st = srcEls[si].getAttribute('type'); if (!st || a.canPlayType(st)) { url = srcEls[si].getAttribute('src'); break; } }
    srcEls.forEach(function (s) { s.remove(); });    // nothing loads until the step is near
    if (url) {
      var cu = clipUrls.filter(function (x) { return x.url === url; })[0];
      if (!cu) clipUrls.push(cu = { url: url, boxes: [] });
      cu.boxes.push(box);
    }
    a.removeAttribute('src'); a.preload = 'none';
    var vids = [a];
    if (box.classList.contains('xf')) { var b = a.cloneNode(true); b.classList.add('b'); box.appendChild(b); vids.push(b); }
    vids.forEach(function (v) { v.muted = true; v.playsInline = true; v.addEventListener('error', function () { if (v.getAttribute('src')) box.classList.add('dead'); }); });
    var key = box.keyed = 'key' in box.dataset ? keyed(box, vids, a.getAttribute('poster')) : null;
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
    box.clipNow = function () { return vids[cur]; };
    function play(v) { if (!v.getAttribute('src')) attach(v); var p = v.play(); if (p && p.catch) p.catch(function () {}); }
    function attach(v) { if (v.getAttribute('src')) return; v.preload = 'auto';
      if (!CLIPBLOB[url]) {
        STREAM[url] = 1; if (streamers.indexOf(v) < 0) streamers.push(v);
        if (INFLIGHT && INFLIGHT.it.url !== url && INFLIGHT.ctrl) INFLIGHT.ctrl.abort();
      }
      v.src = CLIPBLOB[url] || url; }
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
  if (document.readyState === 'complete') setTimeout(prefetchClips, 600);
  else window.addEventListener('load', function () { setTimeout(prefetchClips, 600); });

  /* ---------------- step 2: the Cymetica pipeline, an idea in and a product out ---------------- */
  // ("musi to byt viditelne ze je to cymetica pipeline a ze dovnitr vchazi idea a vystupuje moje apka"): in step with
  // the workshop clip's 10 s, whose arms build the same thing: the idea typed in (0.2 - 1.5 s), sent (1.6 - 2 s),
  // through six chambers (2 - 6.2 s), the product out and live (6.3 - 8.8 s), let go (8.8 - 9.6 s); a new idea each time
  (function () {
    var m = document.querySelector('[data-anim=pipeline]'); if (!m) return;
    var vid = document.querySelector('#s2 video');
    var CH = [['doc', 'Spec', 'spec', '0, 207, 255'], ['design', 'Design', 'design', '0, 207, 255'], ['development', 'Build', 'build', '0, 207, 255'], ['shield', 'Security', 'sec', '0, 207, 255'], ['rocket', 'Deploy', 'dep', '0, 207, 255'], ['cloud', 'Hosting', 'host', '0, 255, 136']];
    // each chamber's icon in colours of its own, as the Quant Lab's tiles have them ("jak v quant labu tady mame ruzne
    // ikonky barevne", 2026-11-01), drawn, as an emoji differs from browser to browser
    var GLYPH = {
      spec: '<path d="M8 3h11l6 6v20H8z" fill="#e8f1ff"/><path d="M19 3l6 6h-6z" fill="#9dc2ff"/><path d="M11.5 14h9M11.5 18h9M11.5 22h6" stroke="#3b82f6" stroke-width="2.2" stroke-linecap="round"/>',
      design: '<path d="M16 3.5C8.5 3.5 3 8.9 3 15.5S8.6 28.5 15 28.5c2 0 3.2-1.2 3.2-2.8 0-1.6-1.3-2.2-1.3-3.7 0-1.5 1.2-2.5 2.8-2.5h3.6c3.7 0 5.7-2.3 5.7-5.6 0-5.6-5.4-10.4-13-10.4z" fill="#a855f7"/><circle cx="10" cy="11.5" r="2.4" fill="#ff4fd8"/><circle cx="17" cy="8.5" r="2.4" fill="#ffc83d"/><circle cx="23" cy="12.5" r="2.4" fill="#00cfff"/><circle cx="8.5" cy="18.5" r="2.4" fill="#00ff88"/>',
      build: '<rect x="3" y="5" width="26" height="22" rx="4" fill="#0b3a55"/><path d="M7 5h18a4 4 0 0 1 4 4v2H3V9a4 4 0 0 1 4-4z" fill="#00cfff"/><circle cx="7" cy="8" r="1.2" fill="#fff"/><circle cx="11" cy="8" r="1.2" fill="#fff"/><path d="M13 15.5l-4 4 4 4M19 15.5l4 4-4 4" fill="none" stroke="#e6fbff" stroke-width="2.3" stroke-linecap="round" stroke-linejoin="round"/>',
      sec: '<path d="M16 3l11 4v8c0 7.2-4.6 12-11 14C9.6 27 5 22.2 5 15V7z" fill="#ffc83d"/><path d="M16 3l11 4v8c0 7.2-4.6 12-11 14z" fill="#dfa41f"/><path d="M11 15.5l3.6 3.6 6.9-7.1" fill="none" stroke="#ffffff" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>',
      dep: '<g transform="rotate(45 16 16)"><path d="M12.5 21h7L16 30z" fill="#ffc83d"/><path d="M10 15l-4.5 5v4l4.5-3zM22 15l4.5 5v4l-4.5-3z" fill="#ff5a68"/><path d="M16 2c4 3 6 8 6 13v6H10v-6c0-5 2-10 6-13z" fill="#eef4fa"/><path d="M16 2c2.3 1.7 4 4 5 6.6H11C12 6 13.7 3.7 16 2z" fill="#ff5a68"/><circle cx="16" cy="13.5" r="2.8" fill="#00cfff" stroke="#5b6b80" stroke-width="1.2"/></g>',
      host: '<path d="M9.5 25a6.5 6.5 0 0 1-1.1-12.9A8.2 8.2 0 0 1 24 11.2 6.9 6.9 0 0 1 23.5 25z" fill="#e6f7ff"/><path d="M3.9 21.8a6.5 6.5 0 0 0 5.6 3.2h14a6.9 6.9 0 0 0 6-4.2c-9.600 3.400-17.600 3.400-25.600 1z" fill="#9ad9f5"/><circle cx="23.500" cy="24" r="5" fill="#00ff88"/><path d="M21.200 24l1.700 1.700 2.900-3" fill="none" stroke="#04331f" stroke-width="1.800" stroke-linecap="round" stroke-linejoin="round"/>'
    };
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
      '<div class="tube"><div class="hd"><span class="pn"><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="12" cy="12" r="9"/><circle cx="12" cy="12" r="3.4"/></svg>Build it Better pipeline</span>' +
          '<span class="st"><i></i><b class="sv"></b><span class="pc">0%</span></span></div>' +
        '<div class="track"><span class="lit"></span><span class="orb"></span></div>' +
        '<div class="chs">' + CH.map(function (c, j) {
          return '<div class="ch ' + c[2] + '"><span class="no">0' + (j + 1) + '</span><span class="ci"><svg class="pr" viewBox="0 0 48 48" aria-hidden="true"><circle cx="24" cy="24" r="21"/></svg>' +
            '<svg viewBox="0 0 32 32" aria-hidden="true">' + GLYPH[c[2]] + '</svg></span><b>' + c[1] + '</b><span class="fx">' + FX[c[2]] + '</span><span class="ok">&check;</span></div>';
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
      orb.style.setProperty('--oc', CH[i][3]);
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
        plate.textContent = items[bi].name;
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

  /* ---------------- step 1: live HQ telemetry count-up & active department scan ---------------- */
  (function () {
    var box = document.querySelector('#s1 .crew-box'); if (!box || reduce) return;
    var nums = [].slice.call(box.querySelectorAll('.crew [data-figure]')).map(function (el) {
      return { el: el, to: parseInt(el.textContent.replace(/,/g, ''), 10) || 0 };
    });
    var dps = [].slice.call(box.querySelectorAll('.dp'));
    var counted = false;
    seen(box, function (v) {
      if (!v || counted) return;
      counted = true;
      var t0 = performance.now();
      (function step(now) {
        var k = ease(clamp((now - t0) / 900, 0, 1));
        nums.forEach(function (n) { n.el.textContent = Math.max(1, Math.round(n.to * k)); });
        if (k < 1) requestAnimationFrame(step);
      })(t0);
    }, 0.25);
    run('hqHud', box, function (t) {
      var idx = Math.floor(t / 1.8) % dps.length;
      dps.forEach(function (d, i) { d.style.borderColor = ''; d.classList.toggle('cmd', i === 0 || i === idx); });
    });
  })();

  /* ---------------- step 3: every product on the map lit under the pointer, and a link ---------------- */
  // ("na kazde kdyz najede nekdo mysi tak se highlightuje a pujde na nej kliknout a otevre se ta stranka v novem okne a
  // ty highlighy zkus udelat tim zelenym ze budou obramovane", 2026-11-01): a .hot over each, its name's plate and the
  // Promo Market's name in the words all do the same; the outlines are record.py's, the cube's drawn here
  (function () {
    var stage = document.querySelector('.stage.market'); if (!stage) return;
    var orbit = stage.querySelector('[data-anim=market-orbit]'), bld = stage.querySelector('[data-anim=market-building]'), O = window.QUEST_OUTLINES;
    if (O) {
      var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
      svg.setAttribute('class', 'hlo'); svg.setAttribute('viewBox', '0 0 ' + O.w + ' ' + O.h); svg.setAttribute('preserveAspectRatio', 'none'); svg.setAttribute('aria-hidden', 'true');
      svg.innerHTML = ['gem', 'farmer', 'casino', 'promo'].map(function (n) {
        var d = O[n] || 'M0 0Z';
        return '<g data-name="' + n + '"><path class="gl" d="' + d + '"/><path class="ln" d="' + d + '"/><path class="rn" pathLength="100" d="' + d + '"/></g>';
      }).join('');
      stage.querySelector('.pic').appendChild(svg);
    }
    // the cube's line goes round its outside only, as the others' do (each face's edge ran a seam across it): its eight
    // corners, read as the browser projects them while it turns, and the hull of those; drawn only while it is lit
    var cube = stage.querySelector('.holo .hstage'), at = stage.querySelector('.holo-at'), hullOn = false, hullSvg, hullPaths, corners;
    if (cube && at) {
      var vx = '';
      [0, 100].forEach(function (x) { [0, 100].forEach(function (y) { [-0.5, 0.5].forEach(function (z) {
        vx += '<i class="vx" style="left:' + x + '%;top:' + y + '%;transform:translateZ(calc(var(--s) * ' + z + '))"></i>';
      }); }); });
      cube.insertAdjacentHTML('beforeend', vx);
      corners = [].slice.call(cube.querySelectorAll('.vx'));
      at.insertAdjacentHTML('beforeend', '<svg class="hlo hlc" aria-hidden="true"><g data-name="promo"><path class="gl"/><path class="ln"/><path class="rn" pathLength="100"/></g></svg>');
      hullSvg = at.querySelector('.hlc'); hullPaths = [].slice.call(hullSvg.querySelectorAll('path'));
    }
    function drawHull() {
      var o = hullSvg.getBoundingClientRect(), pts = corners.map(function (c) { var r = c.getBoundingClientRect(); return [r.left - o.left, r.top - o.top]; });
      pts.sort(function (a, b) { return a[0] - b[0] || a[1] - b[1]; });
      var cross = function (a, b, c) { return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]); }, half = function (list) {
        var h = []; list.forEach(function (q) { while (h.length > 1 && cross(h[h.length - 2], h[h.length - 1], q) <= 0) h.pop(); h.push(q); }); h.pop(); return h;
      }, hull = half(pts).concat(half(pts.slice().reverse()));
      var cx = 0, cy = 0; hull.forEach(function (q) { cx += q[0] / hull.length; cy += q[1] / hull.length; });
      var d = 'M' + hull.map(function (q) { var l = Math.hypot(q[0] - cx, q[1] - cy) || 1, k = 1 + 3 / l; return (cx + (q[0] - cx) * k).toFixed(1) + ' ' + (cy + (q[1] - cy) * k).toFixed(1); }).join('L') + 'Z';
      hullPaths.forEach(function (h) { h.setAttribute('d', d); });
      if (hullOn) requestAnimationFrame(drawHull);
    }
    // the line goes with the thing ("porad mas to obramovani proste blbe", three times): record.py films each clip by a clock of
    // its own and, for every tenth of a second of it, the outline of the gem, the farmer and the Promo Market, so the line is
    // tight on it as the casino's (which stands still and keeps one path) and the two never part; through the loop's
    // cross-fade one outline turns into the other
    var TR = {}, trackOn = null;
    if (O && O.track) Object.keys(O.track).forEach(function (n) {
      var t = O.track[n], bin = atob(t.b64), a = new Int16Array(bin.length / 2);
      for (var i = 0; i < a.length; i++) a[i] = bin.charCodeAt(i * 2) | (bin.charCodeAt(i * 2 + 1) << 8);
      TR[n] = { n: t.n, fps: t.fps, m: a.length / (2 * t.n), loop: !!t.loop, a: a, clip: n === 'promo' ? bld : orbit, paths: svg.querySelectorAll('g[data-name=' + n + '] path') };
    });
    function poseAt(tr, T, out) {
      var f = T * tr.fps, k = f - Math.floor(f), i = Math.floor(f) % tr.m, j = (i + 1) % tr.m, c = tr.n * 2;
      if (!tr.loop) { if (Math.floor(f) >= tr.m - 1) { i = tr.m - 1; j = i; k = 0; } }
      for (var q = 0; q < c; q++) out[q] = (tr.a[i * c + q] * (1 - k) + tr.a[j * c + q] * k) / 10;
    }
    var P1 = new Float32Array(1024), P2 = new Float32Array(1024);
    function drawTrack() {
      if (!trackOn) return;
      var tr = TR[trackOn], v = tr.clip.clipNow && tr.clip.clipNow(), T = v ? v.currentTime : 0, c = tr.n * 2;
      poseAt(tr, T, P1);
      if (!tr.loop && v && T < XF && isFinite(v.duration)) { poseAt(tr, v.duration - XF + T, P2); var w = T / XF; for (var q = 0; q < c; q++) P1[q] = P2[q] * (1 - w) + P1[q] * w; }
      var d = 'M';
      for (var e = 0; e < c; e += 2) d += (e ? 'L' : '') + P1[e].toFixed(1) + ' ' + P1[e + 1].toFixed(1);
      d += 'Z';
      for (var h = 0; h < tr.paths.length; h++) tr.paths[h].setAttribute('d', d);
      requestAnimationFrame(drawTrack);
    }
    function lit(name) {
      if (name) stage.dataset.hl = name; else delete stage.dataset.hl;
      var wasOn = trackOn; trackOn = name && TR[name] ? name : null; if (trackOn && !wasOn) drawTrack();
      [].forEach.call(stage.querySelectorAll('.b3[data-hot]'), function (p) { p.classList.toggle('hov', p.dataset.hot === name); });
      [].forEach.call(stage.querySelectorAll('.hlo g'), function (g) { g.classList.toggle('hov', g.getAttribute('data-name') === name); });
      var hit = name && name !== 'promo' && stage.querySelector('.hot[data-hot=' + name + ']'), s = hit && hit.style;
      if (orbit.keyed) orbit.keyed.hot(!name ? null : hit ? [parseFloat(s.left) / 100, parseFloat(s.top) / 100, (parseFloat(s.left) + parseFloat(s.width)) / 100, (parseFloat(s.top) + parseFloat(s.height)) / 100] : []);
      if (bld.keyed) bld.keyed.hot(!name ? null : name === 'promo' ? [0, 0, 1, 1] : []);
      if (hullSvg && (name === 'promo') !== hullOn) { hullOn = name === 'promo'; if (hullOn) drawHull(); }
    }
    [].forEach.call(document.querySelectorAll('a[data-hot]'), function (a) {
      var on = function () { lit(a.dataset.hot); }, off = function () { lit(null); };
      a.addEventListener('pointerenter', on); a.addEventListener('pointerleave', off);
      a.addEventListener('focus', on); a.addEventListener('blur', off);
    });
  })();

  /* ---------------- step 3: users walk from the Promo Market to the product ---------------- */
  (function () {
    var svg = document.querySelector('[data-anim=flow]'); if (!svg) return;
    var stage = svg.parentElement, near = stage.querySelector('.near'), promo = near;
    var count = stage.querySelector('.users b'), pop = stage.querySelector('.plus');
    var NS = svg.namespaceURI, glows = [], paths = [], dots = [], users = 0, lastW = 0;
    // fifteenth take: from the Promo Market's platform, its left and front (x, y in % of the clip, record.py market),
    // to the farmer's ring, its right side
    var FROM = [[61.5, 77], [63.5, 85], [68.5, 90]], TO = [49.3, 62.5];
    // the cube's faces change their page every 2.4 s, two of three lit, as the Promo Market's own (promo_market_v2.js)
    setInterval(function () {
      document.querySelectorAll('.holo:not(.fast) .hstage').forEach(function (st) {
        var imgs = st.querySelectorAll('.f img'); if (!imgs.length) return;
        var k = (+st.dataset.k || 0); st.dataset.k = k + 1;
        imgs.forEach(function (im, j) { im.classList.toggle('on', (j + k) % 3 !== 0); });
      });
    }, 2400);
    FROM.forEach(function () {
      var g = document.createElementNS(NS, 'path'); g.setAttribute('class', 'fl-glow'); svg.appendChild(g); glows.push(g);
      var p = document.createElementNS(NS, 'path'); p.setAttribute('class', 'fl'); svg.appendChild(p); paths.push(p);
    });
    var ring = document.createElementNS(NS, 'circle'); ring.setAttribute('r', 8); ring.setAttribute('class', 'ping-ring'); svg.appendChild(ring);
    var PER = 5.0;
    for (var i = 0; i < 6; i++) {
      var h = document.createElementNS(NS, 'circle'); h.setAttribute('r', 12); h.setAttribute('class', 'u-halo'); svg.appendChild(h);
      var c = document.createElementNS(NS, 'circle'); c.setAttribute('r', 5); c.setAttribute('class', 'u'); svg.appendChild(c);
      dots.push({ el: c, halo: h, path: i % 3, off: i * PER / 6, arrived: -1 });
    }
    function layout() {
      var s = stage.getBoundingClientRect(), a = promo.getBoundingClientRect(), b = near.getBoundingClientRect();
      if (!s.width || !a.width || !b.width) return;
      lastW = Math.round(s.width * 10 + a.left - s.left);
      svg.setAttribute('viewBox', '0 0 ' + s.width + ' ' + s.height);
      var tx = b.left - s.left + b.width * TO[0] / 100, ty = b.top - s.top + b.height * TO[1] / 100;
      ring.setAttribute('cx', tx.toFixed(1)); ring.setAttribute('cy', ty.toFixed(1));
      FROM.forEach(function (f, i) {
        var fx = a.left - s.left + a.width * f[0] / 100, fy = a.top - s.top + a.height * f[1] / 100;
        var d = 'M' + fx.toFixed(1) + ' ' + fy.toFixed(1) + ' C' + (fx - 34).toFixed(1) + ' ' + (fy + 64).toFixed(1) + ' ' + (tx + 170).toFixed(1) + ' ' + (ty + 28).toFixed(1) + ' ' + tx.toFixed(1) + ' ' + ty.toFixed(1);
        glows[i].setAttribute('d', d);
        paths[i].setAttribute('d', d);
        paths[i].len = paths[i].getTotalLength();
      });
    }
    layout(); window.addEventListener('resize', layout);
    run('flow', svg, function (t) {
      var s = stage.getBoundingClientRect(), a = promo.getBoundingClientRect();
      if (s.width && a.width && Math.round(s.width * 10 + a.left - s.left) !== lastW) layout();
      dots.forEach(function (d) {
        var p = paths[d.path]; if (!p.len) return;
        var cyc = (t + d.off) / PER, k = cyc % 1, n = Math.floor(cyc);
        var q = p.getPointAtLength(p.len * ease(k));
        var op = (Math.sin(Math.PI * k) * 0.92 + 0.08).toFixed(2);
        d.el.setAttribute('cx', q.x.toFixed(1)); d.el.setAttribute('cy', q.y.toFixed(1)); d.el.style.opacity = op;
        d.halo.setAttribute('cx', q.x.toFixed(1)); d.halo.setAttribute('cy', q.y.toFixed(1)); d.halo.style.opacity = op;
        if (k > 0.96 && d.arrived !== n) {
          d.arrived = n; users++; count.textContent = users.toLocaleString('en-US');
          pop.classList.remove('go'); void pop.offsetWidth; pop.classList.add('go');
          ring.classList.remove('pop'); void ring.offsetWidth; ring.classList.add('pop');
        }
      });
    });
  })();

  /* ---------------- step 4: Quant Lab stage telemetry synced to the clip ---------------- */
  (function () {
    var hud = document.querySelector('[data-lab-hud]'); if (!hud) return;
    var vids = [].slice.call(document.querySelectorAll('#s4 video'));
    var lbl = hud.querySelector('.st-lbl'), tag = hud.querySelector('.st-tag'), last = '';
    run('labHud', hud, function () {
      var v = vids.find(function (x) { return !x.paused && x.readyState >= 2 && +getComputedStyle(x).opacity > 0.4; }) || vids[0];
      var T = v && v.readyState >= 1 ? v.currentTime : 17.8;
      var born = T >= 16.6;
      var s = T < 3.2 ? ['Stage 01 · Building strategy genome', 'Build']
        : T < 7.6 ? ['Stage 02 · Blasting 7,776 variations', 'Blast']
        : T < 11.0 ? ['Stage 03 · Out-of-sample blind test', 'Blind']
        : T < 16.6 ? ['Stage 04 · Verifying against the bar', 'The Bar']
        : ['Hero agent born · Ready for Agent Casino', 'Found ★'];
      if (s[0] !== last) { last = s[0]; lbl.textContent = s[0]; tag.textContent = s[1]; hud.classList.toggle('born', born); }
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
