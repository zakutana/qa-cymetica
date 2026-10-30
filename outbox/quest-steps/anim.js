/* The Cymetica Quest, step by step: what moves ("v kazdem kroku musi byt top animace", the operator, 2026-10-30).

   - the clips (record.py): each plays only while it is on screen; step 1 dives from the company's station into its
     HQ, which comes in once and then holds; farmer and Universe cross-fade into themselves, the workshop is a true loop;
   - the first screen's sun with five companies standing round it, in front of it and behind it;
   - step 2's slider between its two ways, building products and breeding the hero agent;
   - way A's pipeline, a skill tree as Capital Maximizer's, in step with the workshop clip: the idea in, the product out;
   - way B's Quant Lab: strategies backtested, the losers fall away, the best one becomes the hero agent, who wins the
     Agent Casino's race, in under 7 s, then it holds;
   - step 3's users, walking from the Promo Market's briefs to the product;
   - step 4's leaderboard, your company climbing it.

   Each live one draws only while it is on screen and counts its frames in QUEST_STATE.frames (the tests read them).
   Figures come from QUEST (quest.js). No library. */
(function () {
  'use strict';
  var Q = window.QUEST, S = window.QUEST_STATE;
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
  // draw(t) every frame while `el` is on screen (and opts.gate(), if given, says yes), t in seconds since it first ran;
  // opts.restart: t starts again from 0 each time it comes back on
  function run(name, el, draw, opts) {
    opts = opts || {};
    var vis = false, on = false, raf = 0, t0 = 0, last = 0;
    S.frames[name] = 0;
    function tick(now) {
      if (!vis) { on = false; return; }
      var ok = !opts.gate || opts.gate();
      if (!ok) { if (opts.restart) last = 0; t0 = 0; raf = requestAnimationFrame(tick); return; }
      if (!t0) t0 = now - last * 1000;
      last = (now - t0) / 1000;
      draw(last); S.frames[name]++;
      raf = requestAnimationFrame(tick);
    }
    if (reduce) { draw(1e3); return; }
    seen(el, function (v) {
      vis = v;
      if (v && !on) { on = true; t0 = 0; if (opts.restart) last = 0; raf = requestAnimationFrame(tick); }
    });
  }

  /* ---------------- step 2's slider: building products, or breeding the hero agent, on one screen ---------------- */
  // ("a kdyz ho presunu zprava doleva tak se zobrazi krok s agentem a kdyz pojedu zpet zacne se zobrazovat to build a
  // produkt"): the agent's pane lies over the builder's, cut at the handle; drag it, or click, or the arrow keys
  // X: where the handle stands, % of the screen's width; its ends are 0 (all agent) and 100 (all builder), the knob
  // kept on screen by quest.css
  var duel = document.getElementById('build'), X = 100;
  var shown = { build: function () { return X > 12; }, agent: function () { return X < 65; } };
  (function () {
    if (!duel) return;
    var div = duel.querySelector('.divider'), tw = 0, nudged = false;
    function set(v) {
      X = clamp(v, 0, 100);
      duel.style.setProperty('--x', X.toFixed(2) + '%');
      div.setAttribute('aria-valuenow', Math.round(X));
      var side = X < 50 ? 'agent' : 'build';
      if (side !== S.side) { S.side = side; duel.classList.toggle('on-agent', side === 'agent'); }
    }
    function to(v, ms) {
      cancelAnimationFrame(tw);
      var a = X, t0 = performance.now(); ms = ms || 650;
      (function f(now) { var k = ease(Math.min(1, (now - t0) / ms)); set(a + (v - a) * k); if (k < 1) tw = requestAnimationFrame(f); })(t0);
    }
    window.QUEST_SIDE = function (side) { to(side === 'agent' ? 0 : 100); };
    var drag = false, moved = 0, x0 = 0;
    div.addEventListener('pointerdown', function (e) { drag = true; moved = 0; x0 = e.clientX; div.setPointerCapture(e.pointerId); cancelAnimationFrame(tw); duel.classList.add('dragging'); });
    div.addEventListener('pointermove', function (e) {
      if (!drag) return;
      moved = Math.max(moved, Math.abs(e.clientX - x0));
      var r = duel.getBoundingClientRect(); set((e.clientX - r.left) / r.width * 100);
    });
    function up() {
      if (!drag) return; drag = false; duel.classList.remove('dragging');
      // a click turns it to the other side; a drag lets go to the nearer one
      if (moved < 6) to(X < 50 ? 100 : 0); else to(X < 50 ? 0 : 100);
    }
    div.addEventListener('pointerup', up); div.addEventListener('pointercancel', up);
    div.addEventListener('keydown', function (e) { if (e.key === 'ArrowLeft') { to(0); e.preventDefault(); } if (e.key === 'ArrowRight') { to(100); e.preventDefault(); } });
    // the first time it comes on screen, the handle shows it can be moved: a little way in, and back
    seen(duel, function (v) {
      if (!v || nudged || reduce) return; nudged = true;
      setTimeout(function () { to(86, 700); setTimeout(function () { if (!drag && X > 80) to(100, 700); }, 900); }, 900);
    });
    set(X);
  })();

  /* ---------------- the clips ---------------- */
  // .clip.xf: a second copy of the video under the first; near the end the other one starts (from data-loop-from)
  // and fades in. .clip.seq: first its intro (step 1's station), the page diving into it, then the main clip fades in.
  // data-gate: plays only while that side of step 2's slider shows.
  var XF = 0.9;
  document.querySelectorAll('.clip').forEach(function (box) {
    var intro = box.querySelector('video.intro'), a = box.querySelector('video:not(.intro)'), vids = [a];
    var loopFrom = +box.dataset.loopFrom || 0, gate = shown[box.dataset.gate] || null;
    if (box.classList.contains('xf') || box.classList.contains('seq')) { var b = a.cloneNode(true); b.classList.add('b'); b.classList.remove('main'); box.appendChild(b); vids.push(b); }
    vids.concat(intro ? [intro] : []).forEach(function (v) { v.muted = true; v.playsInline = true; });
    var cur = 0, on = false, raf = 0, phase = intro ? 'intro' : 'main', fig = box.closest('.pic');
    function play(v) { var p = v.play(); if (p && p.catch) p.catch(function () {}); }
    function tick() {
      if (!on) return;
      if (gate && !gate()) { vids.forEach(function (v) { if (!v.paused) v.pause(); }); raf = requestAnimationFrame(tick); return; }
      if (phase === 'intro') {
        if (intro.paused) { play(intro); box.classList.add('zoom'); }
        if (isFinite(intro.duration) && intro.currentTime > Math.min(intro.duration - 0.25, 3.3)) {
          phase = 'main'; a.currentTime = 0; play(a); box.classList.add('in'); if (fig) fig.classList.add('on');
          setTimeout(function () { intro.pause(); }, 1000);
        }
      } else {
        var v = vids[cur];
        if (v.paused && !(vids[1 - cur] && !vids[1 - cur].paused)) play(v);
        if (vids.length > 1) {
          var o = vids[1 - cur];
          if (isFinite(v.duration) && v.currentTime > v.duration - XF && o.paused) {
            o.currentTime = loopFrom; play(o); o.style.opacity = 1; v.style.opacity = 0;
            setTimeout(function () { v.pause(); }, XF * 1000 + 60);
            cur = 1 - cur;
          }
        }
      }
      raf = requestAnimationFrame(tick);
    }
    if (reduce) { box.classList.add('in'); if (fig) fig.classList.add('on'); return; }
    seen(box, function (vis) {
      if (vis && !on) { on = true; raf = requestAnimationFrame(tick); }
      else if (!vis && on) { on = false; cancelAnimationFrame(raf); vids.concat(intro ? [intro] : []).forEach(function (v) { v.pause(); }); }
    });
  });

  /* ---------------- the first screen: companies by the sun ---------------- */
  // ("ty company nemaji rotovat a jsou strasne malinke"): five, each where it stands round the sun, floating a little;
  // two in front of it (over its disc's edge), three behind it; none more than an eighth of its disc (quest.css .core)
  (function () {
    var sun = document.getElementById('sun'); if (!sun) return;
    var ball = sun.querySelector('.ball'), cos = [].slice.call(sun.querySelectorAll('.co'));
    // where each stands from the sun's middle (px at a 640 px sun), in front (1) or behind (0), its float's phase
    var P = [[-76, 74, 1, 0], [196, -46, 0, 1.7], [-262, -58, 0, 3.1], [96, 92, 1, 4.4], [-36, -178, 0, 5.6]];
    run('sun', sun, function (t) {
      var cx = sun.clientWidth / 2, cy = sun.clientHeight / 2, s = ball.offsetWidth / 640;
      cos.forEach(function (c, i) {
        var p = P[i], y = p[1] * s + 3.5 * Math.sin(Math.PI * 2 * t / 6.5 + p[3]);
        c.style.transform = 'translate(' + (cx + p[0] * s).toFixed(1) + 'px,' + (cy + y).toFixed(1) + 'px) translate(-50%,-50%)';
        c.style.zIndex = p[2] ? 3 : 1;
        c.classList.toggle('back', !p[2]);
      });
    });
  })();

  /* ---------------- step 2: the pipeline as a skill tree, in step with the workshop ---------------- */
  (function () {
    var tree = document.querySelector('[data-anim=pipeline]'); if (!tree) return;
    var vid = document.querySelector('#s2 video');
    // where each node stands in the tree's box (x, y in %), its words, when it lights (s into the workshop's 10 s),
    // and its label's side; the links say which lights which
    var N = [['idea', 50, 3, 'Idea', 'you say what', 0.35, 'r', 'bulb'], ['spec', 50, 15, 'Spec', '', 1.8, 'r', 'doc'], ['design', 50, 27, 'Design', '', 2.4, 'r', 'design'],
             ['fe', 14, 43, 'Frontend', '', 3.1, 'b', 'monitor'], ['be', 50, 43, 'Backend', '', 3.25, 'b', 'server'], ['da', 86, 43, 'Data', '', 3.4, 'b', 'data'],
             ['sec', 50, 62, 'Top security', '', 4.7, 'r', 'shield'], ['dep', 50, 73, 'Deploy', '', 5.4, 'r', 'rocket'], ['host', 50, 84, 'Hosting', '', 6.0, 'r', 'cloud'],
             ['prod', 50, 97, 'Production-grade app', 'Yours', 6.45, 'r', 'crown']];
    var E = [['idea', 'spec', 1.4, 1.8], ['spec', 'design', 2.0, 2.4], ['design', 'fe', 2.6, 3.1], ['design', 'be', 2.6, 3.25], ['design', 'da', 2.6, 3.4],
             ['fe', 'sec', 4.2, 4.7], ['be', 'sec', 4.2, 4.7], ['da', 'sec', 4.2, 4.7], ['sec', 'dep', 5.0, 5.4], ['dep', 'host', 5.6, 6.0], ['host', 'prod', 6.05, 6.45]];
    var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg'); svg.setAttribute('class', 'wires'); svg.setAttribute('aria-hidden', 'true');
    tree.appendChild(svg);
    var nodes = {};
    N.forEach(function (n) {
      var d = document.createElement('div');
      d.className = 'nd ' + n[6] + (n[0] === 'prod' ? ' apex' : '') + (n[0] === 'idea' ? ' root' : '');
      d.style.left = n[1] + '%'; d.style.top = n[2] + '%';
      // a hexagon with the step's icon in it and a ring that bursts out of it when it lights; the words on a chip of glass
      d.innerHTML = '<span class="hx"><svg class="h" viewBox="0 0 24 24" aria-hidden="true"><path d="' + HEX + '"/></svg>' + window.QUEST_ICON_SVG(n[7]) +
        '<svg class="ring" viewBox="0 0 24 24" aria-hidden="true"><path d="' + HEX + '"/></svg></span><span class="w"><b>' + n[3] + '</b>' + (n[4] ? '<i>' + n[4] + '</i>' : '') + '</span>';
      tree.appendChild(d); nodes[n[0]] = { el: d, at: n[5] };
    });
    var links = E.map(function (e) {
      var mk = function (cls) { var p = document.createElementNS(svg.namespaceURI, 'path'); p.setAttribute('class', cls); svg.appendChild(p); return p; };
      var base = mk('lk'), lit = mk('lk lit'), flow = mk('lk flow'), dot = document.createElementNS(svg.namespaceURI, 'circle');
      dot.setAttribute('class', 'pk'); dot.setAttribute('r', 5); svg.appendChild(dot);
      return { a: e[0], b: e[1], t0: e[2], t1: e[3], base: base, lit: lit, flow: flow, dot: dot, len: 1 };
    });
    function layout() {
      var W = tree.clientWidth, H = tree.clientHeight;
      svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H); svg.setAttribute('width', W); svg.setAttribute('height', H);
      links.forEach(function (l) {
        var A = nodes[l.a].el, B = nodes[l.b].el;
        var ax = A.offsetLeft, ay = A.offsetTop, bx = B.offsetLeft, by = B.offsetTop, my = (ay + by) / 2;
        var d = ax === bx ? 'M' + ax + ' ' + ay + ' L' + bx + ' ' + by : 'M' + ax + ' ' + ay + ' C' + ax + ' ' + my + ' ' + bx + ' ' + my + ' ' + bx + ' ' + by;
        l.base.setAttribute('d', d); l.lit.setAttribute('d', d); l.flow.setAttribute('d', d);
        l.len = l.lit.getTotalLength(); l.lit.style.strokeDasharray = l.len;
      });
    }
    layout(); window.addEventListener('resize', layout);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(layout);
    var clock = 0;
    run('pipeline', tree, function (t) {
      // the workshop's own time when it plays, so the tree and the arms tell one story; else the page's clock
      var T = vid && !vid.paused && vid.readyState >= 2 ? vid.currentTime % 10 : t % 10;
      var reset = 1 - win(T, 8.6, 9.4);
      links.forEach(function (l) {
        var k = win(T, l.t0, l.t1) * reset;
        l.lit.style.strokeDashoffset = (l.len * (1 - k)).toFixed(1);
        // once a link is lit, light keeps running along it (its dashes drift), until the tree gives itself back
        l.flow.style.opacity = k >= 1 ? 1 : 0;
        l.flow.style.strokeDashoffset = (-t * 38).toFixed(1);
        var moving = T >= l.t0 && T < l.t1;
        l.dot.style.opacity = moving ? 1 : 0;
        if (moving) { var p = l.lit.getPointAtLength(l.len * k); l.dot.setAttribute('cx', p.x.toFixed(1)); l.dot.setAttribute('cy', p.y.toFixed(1)); }
      });
      Object.keys(nodes).forEach(function (k) {
        var n = nodes[k], lit = T >= n.at && T < 9.1;
        n.el.classList.toggle('lit', lit);
        n.el.classList.toggle('pop', T >= n.at && T < n.at + 0.45);
      });
      tree.classList.toggle('done', T >= 6.45 && T < 9.1);
      clock = T;
    }, { gate: shown.build });
  })();

  /* ---------------- step 3: the Quant Lab breeds the hero agent ---------------- */
  (function () {
    var cv = document.querySelector('[data-anim=lab]'); if (!cv) return;
    var g = cv.getContext('2d'), W = 1440, H = 810;
    var agent = new Image(); agent.src = 'pics/agent.webp';
    // the strategies: random walks of one seed, a few with a drift that keeps them alive
    var R = (function (s) { return function () { s = (s * 16807) % 2147483647; return s / 2147483647; }; })(42);
    var CURVES = 120, STEPS = 110, curves = [];
    for (var i = 0; i < CURVES; i++) {
      var drift = (R() - 0.55) * 0.9, v = 0, pts = [];
      for (var j = 0; j <= STEPS; j++) { v += drift * 0.9 + (R() - 0.5) * 3.2; pts.push(v); }
      curves.push(pts);
    }
    var order = curves.map(function (c, i) { return [c[STEPS], i]; }).sort(function (a, b) { return b[0] - a[0]; }).map(function (x) { return x[1]; });
    var best = order[0], rank = {}; order.forEach(function (ci, r) { rank[ci] = r; });
    // when each falls away: the worst first, through the backtest; the best eight survive to the end
    var dies = curves.map(function (_, i) { var r = rank[i]; return r < 8 ? 99 : 1.2 + (CURVES - r) / CURVES * 3.4; });
    // the chart clear of the canvas's faded edges (quest.css fades the outer 16 %)
    var CH = { x: 250, y: 215, w: 940, h: 440 }, CHEST = [1090, 440];
    var lo = Math.min.apply(null, curves.map(function (c) { return Math.min.apply(null, c); })), hi = Math.max.apply(null, curves.map(function (c) { return Math.max.apply(null, c); }));
    function px(j) { return CH.x + CH.w * j / STEPS; }
    function py(v) { return CH.y + CH.h * (1 - (v - lo) / (hi - lo)); }
    // the race: our agent and five rivals, ROI bars that wander; ours takes the lead at the end
    var rivals = Q.lab.rivals, race = rivals.map(function (_, i) { return 0.55 + 0.35 * ((i * 37) % 11) / 11; });
    function size() {
      var r = cv.getBoundingClientRect(), k = Math.min(window.devicePixelRatio || 1, 1.5);
      var w = Math.round(r.width * k), h = Math.round(r.width * k * H / W);
      if (cv.width !== w) { cv.width = w; cv.height = h; }
    }
    size(); window.addEventListener('resize', size);
    function text(s, x, y, px, col, weight, align, spacing) {
      g.font = (weight || 800) + ' ' + px + 'px "JetBrains Mono", monospace'; g.fillStyle = col; g.textAlign = align || 'left';
      if (spacing) { g.letterSpacing = spacing + 'px'; }
      g.fillText(s, x, y); g.letterSpacing = '0px';
    }
    function hex(x, y, r, fill, stroke) {
      g.beginPath();
      for (var k = 0; k < 6; k++) { var a = Math.PI / 6 + k * Math.PI / 3; g[k ? 'lineTo' : 'moveTo'](x + r * Math.cos(a), y + r * Math.sin(a)); }
      g.closePath(); if (fill) { g.fillStyle = fill; g.fill(); } if (stroke) { g.strokeStyle = stroke; g.lineWidth = 2; g.stroke(); }
    }
    // "trva moc dlouho a musim cekat nez se dokonci": the whole story told 1.9 times as fast as it was drawn (in under
    // 7 s), then it holds on its end (the hero agent, the race won); it starts again each time the slider shows it
    var SPEED = 1.9, END = 12.85;
    S.labSeconds = END / SPEED;
    run('lab', cv, function (t) {
      var T = Math.min(t * SPEED, END), sc = cv.width / W;
      g.setTransform(sc, 0, 0, sc, 0, 0);
      g.clearRect(0, 0, W, H);
      g.fillStyle = '#05070c'; g.fillRect(0, 0, W, H);
      var fadeIn = win(T, 0, 0.6), fadeOut = 1;
      g.globalAlpha = fadeIn * fadeOut;
      // the hero agent, out of a hologram scan (8.0 - 10.4 s), on the right
      var scan = win(T, 8.0, 10.2);
      if (agent.complete && agent.naturalWidth && scan > 0) {
        var sx = 1180, sw = 1380, sh = 1440, dx = 700, dw = 740, dh = 810;
        g.save(); g.beginPath(); g.rect(dx, 0, dw, dh * scan); g.clip();
        g.globalAlpha = fadeOut * (0.35 + 0.65 * win(T, 9.6, 10.6));
        g.drawImage(agent, sx, 0, sw, sh, dx, 0, dw, dh);
        g.restore();
        g.globalAlpha = fadeOut;
        // the light of the scan: a line, and lines of light over what it has drawn while it draws
        if (scan < 1) {
          var ly = dh * scan, gr = g.createLinearGradient(0, ly - 60, 0, ly + 4);
          gr.addColorStop(0, 'rgba(0,207,255,0)'); gr.addColorStop(1, 'rgba(0,207,255,.55)');
          g.fillStyle = gr; g.fillRect(dx, ly - 60, dw, 64);
          g.fillStyle = 'rgba(190,250,255,.95)'; g.fillRect(dx, ly - 1, dw, 2.5);
        }
        g.fillStyle = 'rgba(0,207,255,' + (0.1 * (1 - win(T, 10.2, 11))).toFixed(3) + ')';
        for (var yy = 0; yy < dh * scan; yy += 6) g.fillRect(dx, yy, dw, 2);
        // the edge of the picture into the dark
        var fade = g.createLinearGradient(dx, 0, dx + 260, 0); fade.addColorStop(0, 'rgba(5,7,12,1)'); fade.addColorStop(1, 'rgba(5,7,12,0)');
        g.fillStyle = fade; g.fillRect(dx, 0, 262, dh);
      }
      // the lab's chart: grid, then the curves
      var chart = 1 - 0.75 * win(T, 7.2, 8.6);
      g.globalAlpha = fadeIn * fadeOut * chart;
      g.strokeStyle = 'rgba(30,48,80,.7)'; g.lineWidth = 1;
      for (var gx = 0; gx <= 6; gx++) { g.beginPath(); g.moveTo(CH.x + CH.w * gx / 6, CH.y); g.lineTo(CH.x + CH.w * gx / 6, CH.y + CH.h); g.stroke(); }
      for (var gy = 0; gy <= 4; gy++) { g.beginPath(); g.moveTo(CH.x, CH.y + CH.h * gy / 4); g.lineTo(CH.x + CH.w, CH.y + CH.h * gy / 4); g.stroke(); }
      text('QUANT LAB', CH.x, 146, 34, '#00cfff', 800, 'left', 6);
      var prog = win(T, 0.3, 4.8), gen = Math.max(1, Math.round(Q.lab.generations * prog)), tested = Q.lab.tested * ease(win(T, 0.3, 5.0));
      text('STRATEGIES TESTED  ' + fmt(tested), CH.x, 188, 26, '#a9bfcd', 700);
      text('GENERATION ' + String(gen).padStart(2, '0'), CH.x + CH.w, CH.y + CH.h + 44, 26, '#a9bfcd', 700, 'right');
      g.globalCompositeOperation = 'lighter';
      var upto = Math.round(STEPS * prog), xs = px(upto);
      curves.forEach(function (c, ci) {
        if (ci === best && T > 4.9) return;
        var dead = T > dies[ci], gone = win(T, dies[ci], dies[ci] + 0.7), fall = 60 * gone * gone;
        var a = (ci === best ? 0.9 : rank[ci] < 8 ? 0.62 : 0.3) * (1 - gone) * (1 - win(T, 5.0, 6.0) * (ci === best ? 0 : 1));
        if (a <= 0.01) return;
        // a strategy that fails flashes red as it goes
        var red = dead ? 0.6 + 0.4 * Math.sin(Math.PI * clamp(gone * 2, 0, 1)) : 0;
        g.strokeStyle = dead ? 'rgba(255,68,68,' + (a * (0.6 + red)).toFixed(3) + ')' : (ci === best ? 'rgba(0,255,136,' + a + ')' : 'rgba(0,207,255,' + a.toFixed(3) + ')');
        g.lineWidth = ci === best ? 2.6 : dead ? 1.8 : 1.3;
        g.beginPath();
        for (var j = 0; j <= upto; j++) g[j ? 'lineTo' : 'moveTo'](px(j), py(c[j]) + fall);
        g.stroke();
        // the head of each live one: a point of light where the backtest has reached
        if (!dead && T < 5.0 && upto > 0) { g.fillStyle = 'rgba(150,240,255,' + (a * 0.9).toFixed(3) + ')'; g.fillRect(xs - 1.5, py(c[upto]) - 1.5, 3, 3); }
      });
      // the backtest's front: a line of light sweeping across as it runs
      if (T < 5.0) {
        var sw = g.createLinearGradient(xs - 90, 0, xs + 2, 0);
        sw.addColorStop(0, 'rgba(0,207,255,0)'); sw.addColorStop(1, 'rgba(0,207,255,.16)');
        g.fillStyle = sw; g.fillRect(xs - 90, CH.y, 92, CH.h);
        g.fillStyle = 'rgba(160,240,255,.7)'; g.fillRect(xs - 1, CH.y, 2, CH.h);
      }
      g.globalCompositeOperation = 'source-over';
      // the best one: green, thick, and it climbs (4.9 - 7.2 s)
      if (T > 4.9) {
        var c = curves[best], climb = ease(win(T, 5.0, 6.6)), k2 = 1 - win(T, 7.2, 8.3);
        g.save(); g.shadowColor = 'rgba(0,255,136,.9)'; g.shadowBlur = 22 * k2; g.strokeStyle = 'rgba(0,255,136,' + (0.95 * k2).toFixed(3) + ')'; g.lineWidth = 4.5;
        g.beginPath();
        for (var j2 = 0; j2 <= STEPS; j2++) { var lift = Math.pow(j2 / STEPS, 2.2) * climb * (hi - c[STEPS]) * 1.05; g[j2 ? 'lineTo' : 'moveTo'](px(j2), py(c[j2] + lift)); }
        g.stroke(); g.restore();
        var ex = px(STEPS), ey = py(c[STEPS] + climb * (hi - c[STEPS]) * 1.05);
        if (T < 7.4) {
          g.globalAlpha = fadeOut * win(T, 5.6, 6.2);
          text('BEST STRATEGY', ex - 18, ey + 48, 28, '#00ff88', 800, 'right', 3);
          g.globalAlpha = fadeOut;
        }
        // into light, and the light into the agent (7.2 - 9.2 s)
        var fly = ease(win(T, 7.3, 9.0));
        if (T > 7.2 && T < 9.4) {
          var ox = ex + (CHEST[0] - ex) * fly, oy = ey + (CHEST[1] - ey) * fly - Math.sin(Math.PI * fly) * 120, r = 14 + 20 * Math.sin(Math.PI * win(T, 7.2, 7.8));
          var orb = g.createRadialGradient(ox, oy, 0, ox, oy, r * 3.2);
          orb.addColorStop(0, 'rgba(230,255,245,1)'); orb.addColorStop(0.3, 'rgba(0,255,136,.85)'); orb.addColorStop(1, 'rgba(0,255,136,0)');
          g.globalAlpha = fadeOut * (1 - win(T, 9.0, 9.4)); g.fillStyle = orb; g.beginPath(); g.arc(ox, oy, r * 3.2, 0, Math.PI * 2); g.fill();
          g.globalAlpha = fadeOut;
        }
      }
      // the strategy taken in: a ring of light from the agent's chest
      if (T > 9.0 && T < 10.6) {
        var rk = win(T, 9.0, 10.6);
        g.strokeStyle = 'rgba(0,255,136,' + (0.9 * (1 - rk)).toFixed(3) + ')'; g.lineWidth = 3;
        g.beginPath(); g.arc(CHEST[0], CHEST[1], 20 + 260 * rk, 0, Math.PI * 2); g.stroke();
      }
      g.globalAlpha = fadeOut * win(T, 9.8, 10.4) * (1 - win(T, 12.9, 13.4));
      text('HERO AGENT', 1000, 150, 34, '#ffffff', 800, 'left', 4);
      text('EQUIPPED · BEST STRATEGY', 1000, 190, 24, '#00ff88', 800, 'left', 2);
      // the Agent Casino's race (10.4 - 13.3 s): best ROI wins
      var rc = win(T, 10.4, 10.9) * (1 - win(T, 13.0, 13.4));
      if (rc > 0) {
        g.globalAlpha = fadeOut * rc;
        var bx = 250, by = 330, bw = 560, rowH = 62;
        g.fillStyle = 'rgba(5,7,12,.78)'; g.fillRect(bx - 30, by - 90, bw + 120, rowH * 6 + 120);
        text('AGENT CASINO', bx, by - 40, 30, '#00cfff', 800, 'left', 5);
        text('BEST ROI WINS', bx + bw + 60, by - 40, 24, '#a9bfcd', 700, 'right', 2);
        var k3 = ease(win(T, 10.6, 12.8));
        var rows = [{ n: 'hero agent', v: 0.2 + 0.82 * k3, me: true }].concat(rivals.map(function (n, i) { return { n: n, v: race[i] * (0.25 + 0.75 * k3) + 0.04 * Math.sin(T * 3 + i) }; }));
        rows.forEach(function (row, i) {
          var y = by + i * rowH, w = bw * 0.5 * clamp(row.v, 0, 1.05);
          hex(bx + 14, y + 20, 15, row.me ? 'rgba(0,255,136,.22)' : 'rgba(0,207,255,.12)', row.me ? '#00ff88' : 'rgba(0,207,255,.6)');
          text(row.n, bx + 44, y + 29, 26, row.me ? '#00ff88' : '#e6edf7', row.me ? 800 : 600);
          g.fillStyle = 'rgba(30,48,80,.6)'; g.fillRect(bx + 290, y + 12, bw * 0.5, 16);
          var bg = g.createLinearGradient(bx + 290, 0, bx + 290 + w, 0);
          bg.addColorStop(0, row.me ? 'rgba(0,255,136,.5)' : 'rgba(0,207,255,.35)'); bg.addColorStop(1, row.me ? '#00ff88' : 'rgba(0,207,255,.8)');
          g.fillStyle = bg; g.fillRect(bx + 290, y + 12, w, 16);
        });
        if (T > 12.5) { g.globalAlpha = fadeOut * rc * win(T, 12.5, 12.8); text('WINS', bx + 290 + bw * 0.5 * 1.02 + 16, by + 32, 28, '#00ff88', 800, 'left', 3); }
      }
      g.globalAlpha = 1;
    }, { gate: shown.agent, restart: true });
  })();

  /* ---------------- step 4: users run from the briefs to the product ---------------- */
  (function () {
    var svg = document.querySelector('[data-anim=flow]'); if (!svg) return;
    var stage = svg.parentElement, promo = stage.querySelector('.pic img'), near = stage.querySelector('.near');
    var count = stage.querySelector('.users b'), pop = stage.querySelector('.plus');
    var NS = svg.namespaceURI, paths = [], dots = [], users = 0;
    // the briefs' "See my offer" buttons in promo.webp (x, y in %), and where the farmer stands in its clip
    var FROM = [[17, 93], [50, 93], [83, 93]], TO = [30, 48];
    FROM.forEach(function () { var p = document.createElementNS(NS, 'path'); p.setAttribute('class', 'fl'); svg.appendChild(p); paths.push(p); });
    // ("step 4 animace je moc rychla"): six users at a time, each 5.2 s from a brief to the product
    var PER = 5.2;
    S.flowSeconds = PER;
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
    var rows = Q.board.map(function (r) { return { name: r[0], pts: r[1], me: false }; });
    var me = { name: Q.you.name, pts: Q.you.from, me: true }; rows.push(me);
    rows.forEach(function (r) {
      r.el = document.createElement('div'); r.el.className = 'row' + (r.me ? ' me' : '');
      r.el.innerHTML = '<span class="rk"></span><svg viewBox="0 0 24 24" aria-hidden="true"><path d="' + HEX + '"/></svg><span class="nm">' + r.name + '</span>' +
        '<span class="pp"><b></b> pts</span><span class="pz"></span>';
      box.appendChild(r.el);
    });
    var STEP = 2.2, P = Q.board.length * STEP + 4.5, last = -1;
    function place(order) {
      order.forEach(function (r, i) {
        r.el.style.transform = 'translateY(' + (i * 100) + '%)';
        r.el.querySelector('.rk').textContent = i + 1;
        r.el.querySelector('.pz').textContent = i < Q.prizes.length ? Q.prizes[i].toLocaleString('en-US') + ' ' + Q.unit : '';
        r.el.classList.toggle('paid', i < Q.prizes.length);
      });
    }
    var n = Q.board.length, others = rows.filter(function (r) { return !r.me; });
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
      rows.forEach(function (r) { r.el.querySelector('.pp b').textContent = fmt(r.pts); });
      box.classList.toggle('won', at === 0);
    });
  })();
})();
