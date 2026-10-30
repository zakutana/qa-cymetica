/* The Cymetica Quest, step by step: what moves (the operator, 2026-10-30: "v kazdem kroku musi byt top animace").

   - the clips (record.py): each plays only while it is on screen and cross-fades into itself at its loop point; the
     office plays only its still part (data-loop-from: "kasli na tu animaci zoomu");
   - the first screen's five companies, standing round the sun ("nemusi to byt animace, staci at stoji na miste");
   - step 2's Cymetica pipeline, in step with the workshop clip: an idea typed in, through the pipeline's six
     chambers, a product out; and the ring of the products already built, as holograms, turned by dragging;
   - step 4's users, walking from the Promo Market's briefs to the product;
   - step 5's leaderboard, your company climbing it.

   Each live one draws only while it is on screen and counts its frames in QUEST_STATE.frames. Figures from QUEST. */
(function () {
  'use strict';
  var Q = window.QUEST, S = window.QUEST_STATE;
  function shot(key) { return '<img src="pics/apps/' + key + '.webp" alt="" width="560" height="315" loading="lazy" draggable="false">'; }
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var HEX = 'M12 1.6 21 6.8v10.4L12 22.4 3 17.2V6.8z';
  var clamp = function (x, a, b) { return x < a ? a : x > b ? b : x; };
  var win = function (t, a, b) { return clamp((t - a) / (b - a), 0, 1); };
  var ease = function (x) { x = clamp(x, 0, 1); return x < 0.5 ? 4 * x * x * x : 1 - Math.pow(-2 * x + 2, 3) / 2; };
  var fmt = function (v) { return Math.round(v).toLocaleString('en-US'); };

  function seen(el, cb) {
    if (!('IntersectionObserver' in window)) { cb(true); return; }
    new IntersectionObserver(function (es) { es.forEach(function (e) { cb(e.isIntersecting); }); }, { threshold: 0.04 }).observe(el);
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

  /* ---------------- the clips ---------------- */
  // .clip.xf: a second copy of the video under the first; near the end the other one starts (from data-loop-from)
  // and fades in, so the loop has no seam
  var XF = 0.9;
  document.querySelectorAll('.clip').forEach(function (box) {
    var a = box.querySelector('video'), vids = [a], from = +box.dataset.loopFrom || 0;
    if (box.classList.contains('xf')) { var b = a.cloneNode(true); b.classList.add('b'); box.appendChild(b); vids.push(b); }
    vids.forEach(function (v) { v.muted = true; v.playsInline = true; });
    var cur = 0, on = false, raf = 0, started = false;
    function play(v) { var p = v.play(); if (p && p.catch) p.catch(function () {}); }
    function begin() { if (started) return; started = true; if (from) a.currentTime = from; play(a); }
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
      raf = requestAnimationFrame(tick);
    }
    if (reduce) return;
    seen(box, function (vis) {
      if (vis && !on) { on = true; if (!started) { if (a.readyState >= 1) begin(); else a.addEventListener('loadedmetadata', begin, { once: true }); } else play(vids[cur]); raf = requestAnimationFrame(tick); }
      else if (!vis && on) { on = false; cancelAnimationFrame(raf); vids.forEach(function (v) { v.pause(); }); }
    });
  });

  /* ---------------- the first screen: five companies standing round the sun ---------------- */
  // where each stands from the sun's middle (a share of the sun's size), and whether in front of it or behind it
  (function () {
    var sun = document.getElementById('sun'); if (!sun) return;
    var ball = sun.querySelector('.ball'), cos = [].slice.call(sun.querySelectorAll('.co'));
    var P = [[-0.14, 0.12, 1], [0.32, -0.08, 0], [-0.42, -0.1, 0], [0.17, 0.15, 1], [-0.06, -0.3, 0]];
    function place() {
      var cx = sun.clientWidth / 2, cy = sun.clientHeight / 2, s = ball.offsetWidth;
      cos.forEach(function (c, i) {
        var p = P[i];
        c.style.left = (cx + p[0] * s).toFixed(1) + 'px'; c.style.top = (cy + p[1] * s).toFixed(1) + 'px';
        c.classList.toggle('back', !p[2]);
      });
    }
    place(); window.addEventListener('resize', place);
  })();

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
    m.innerHTML =
      '<div class="inlet"><span class="cap">Your idea</span><p class="say">&ldquo;<span class="tx"></span><span class="caret"></span>&rdquo;</p></div>' +
      '<div class="tube"><div class="brand"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="' + HEX + '"/></svg>Cymetica pipeline</div>' +
        '<div class="track"><span class="lit"></span><span class="orb"></span></div>' +
        '<div class="chs">' + CH.map(function (c) {
          return '<div class="ch ' + c[2] + '"><span class="ci">' + window.QUEST_ICON_SVG(c[0]) + '</span><b>' + c[1] + '</b><span class="fx">' + FX[c[2]] + '</span><span class="ok">&check;</span></div>';
        }).join('') + '</div></div>' +
      '<div class="outlet"><span class="cap">Your app</span><div class="app"><span class="lg"></span><span class="an"><b></b><i>Live &middot; yours</i></span></div><span class="burst"></span></div>';
    var tx = m.querySelector('.tx'), orb = m.querySelector('.orb'), lit = m.querySelector('.lit'), chs = [].slice.call(m.querySelectorAll('.ch'));
    var app = m.querySelector('.app'), lg = m.querySelector('.lg'), an = m.querySelector('.an b');
    var idea = -1, lastT = 99;
    function setIdea(i) {
      idea = i; var d = Q.ideas[i];
      lg.innerHTML = shot(d[2]); an.textContent = d[1];
    }
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
      });
      m.classList.toggle('out', T >= 6.3 && T < 9.2);
      m.classList.toggle('pop', T >= 6.3 && T < 7.1);
    });
  })();

  /* ---------------- step 2: the ring of products already built, their live pages as holograms ---------------- */
  // ("nechci at to jsou ikonky ale screeny z live aplikaci holograficky"): turning slowly, turned faster by a drag; the
  // one in front says its name
  (function () {
    var ring = document.querySelector('[data-anim=apps]'); if (!ring) return;
    var wrap = ring.querySelector('.items'), plate = ring.querySelector('.plate b');
    var items = Q.built.map(function (a) {
      var e = document.createElement('div'); e.className = 'it';
      e.innerHTML = '<span class="mk">' + shot(a[1]) + '</span>';
      wrap.appendChild(e); return { el: e, name: a[0] };
    });
    var n = items.length, drag = 0, vel = 0, down = false, x0 = 0, front = -1;
    ring.addEventListener('pointerdown', function (e) { down = true; x0 = e.clientX; ring.setPointerCapture(e.pointerId); ring.classList.add('grab'); });
    ring.addEventListener('pointermove', function (e) { if (!down) return; var dx = e.clientX - x0; x0 = e.clientX; drag += dx * 0.45; vel = dx * 0.45; });
    function up() { down = false; ring.classList.remove('grab'); }
    ring.addEventListener('pointerup', up); ring.addEventListener('pointercancel', up);
    ring.addEventListener('wheel', function (e) { if (Math.abs(e.deltaX) > Math.abs(e.deltaY)) { drag -= e.deltaX * 0.3; e.preventDefault(); } }, { passive: false });
    run('apps', ring, function (t) {
      if (!down) { drag += vel; vel *= 0.94; }
      // a ring seen a little from above: the front ones lower and bigger, the back ones higher, small and faint
      var W = wrap.clientWidth, R = W * 0.4, base = t * 9 + drag, best = -2, bi = 0;
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
    });
  })();

  /* ---------------- step 4: users walk from the briefs to the product ---------------- */
  (function () {
    var svg = document.querySelector('[data-anim=flow]'); if (!svg) return;
    var stage = svg.parentElement, promo = stage.querySelector('.promo3d img'), near = stage.querySelector('.near');
    var count = stage.querySelector('.users b'), pop = stage.querySelector('.plus');
    var NS = svg.namespaceURI, paths = [], dots = [], users = 0;
    // the briefs' "See my offer" buttons in promo.webp (x, y in %), and where the farmer stands in its clip
    var FROM = [[17, 93], [50, 93], [83, 93]], TO = [30, 48];
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
        paths[i].setAttribute('d', 'M' + fx + ' ' + fy + ' C' + fx + ' ' + (fy + 120) + ' ' + (tx - 60) + ' ' + (ty - 160) + ' ' + tx + ' ' + ty);
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
    var STEP = 2.2, P = Q.board.length * STEP + 4.5, last = -1, n = Q.board.length, others = rows.filter(function (r) { return !r.me; });
    function place(order) {
      order.forEach(function (r, i) {
        r.el.style.transform = 'translateY(' + (i * 100) + '%)';
        r.el.querySelector('.rk').textContent = i + 1;
        r.el.querySelector('.pz').textContent = i < Q.prizes.length ? Q.prizes[i].toLocaleString('en-US') + ' ' + Q.unit : '';
        r.el.className = 'row' + (r.me ? ' me' : '') + (i < Q.prizes.length ? ' paid p' + (i + 1) : '');
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
      if (at !== last) { var order = others.slice(); order.splice(at, 0, me); place(order); last = at; }
      rows.forEach(function (r) { r.el.querySelector('.pp b').textContent = fmt(r.pts); r.el.querySelector('.bar i').style.width = (r.pts / top * 100).toFixed(1) + '%'; });
      box.classList.toggle('won', at === 0);
    });
  })();
})();
