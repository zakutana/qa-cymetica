/* The Cymetica Quest guide: the scroll engine, without a library (the same three mechanisms robinwifhoodcoin.com's
   scroll-fx.js uses):
     1. the film: one layer per chapter, fixed behind the page, faded by how much of the screen its chapter covers, so
        the text scrolls over the picture and one chapter's picture hands over to the next as the page moves;
     2. a flight inside a layer: an image sequence on a canvas, scrubbed by how far through its chapter the page is --
        scroll down and the camera flies on, scroll up and it flies back. Frames load coarse to fine, so a fast scroll
        always has a near frame to show, and the chapter's poster stands under them until they come;
     3. the text pinned in each chapter, faded in and out through --o and --y.
   And the rail: which of the four steps the middle of the screen is in, and a click jumps there.

   QUEST holds every figure and every address on the page. Nothing else may type a number (tests/test_quest.py). */
(function () {
  'use strict';

  var Q = window.QUEST = {
    // The revenue share as it is live on 2026-10-27 (/company's board, the flyer): up to 5 % / 3 % / 1 % of Cymetica
    // revenue to the top three companies. We asked Cymetica that day (Telegram, "Revenue Share / Cymetica Quest") whether
    // to run a Season 0 in ET10 or a cash prize until revenue starts; unanswered. If the prize changes, it changes here.
    prize: { shares: [5, 3, 1], top: 5, slots: 3 },
    board: { ranks: [1, 2, 3] },
    apps: 133,                          // /build-it-better, "See the 133 apps already rebuilt", read 2026-10-27
    casino: { seats: 6, tables: 1 },    // /agent-casino, "6 agents. 1 table. Best ROI wins."
    steps: [
      { n: '01', label: 'Start a company', short: 'Start' },
      { n: '02', label: 'Ship products', short: 'Ship' },
      { n: '03', label: 'Get seen', short: 'Get seen' },
      { n: '04', label: 'Bring the most revenue', short: 'Revenue' }
    ],
    links: {
      company: 'https://cymetica.com/company',
      bib: 'https://cymetica.com/build-it-better',
      casino: 'https://cymetica.com/agent-casino',
      promo: 'https://cymetica.com/promo-market',
      board: 'https://cymetica.com/company#universe'
    },
    // What plays under each chapter. seq: a flight rendered by render.py (frames/<set>/<seq>/NNNN.webp), from..to of its
    // frames across the chapter; still: one picture with a slow push in. poster: what stands there before any frame
    // has come (stills/<poster>.webp). out / in: how the chapter's picture leaves and arrives at a cut between two
    // worlds -- a dive into the company (it grows and blurs away) or a pull back out of it (it shrinks away).
    film: {
      hero: { seq: 'approach', from: 0, to: 36, poster: 'hero' },
      s1: { seq: 'approach', from: 36, to: 179, poster: 's1', out: 'dive' },
      s2a: { still: 'dev', poster: 'dev', in: 'land' },
      s2b: { still: 'lab', poster: 'lab', out: 'rise' },
      s2c: { seq: 'casino', from: 0, to: 89, poster: 's2c', in: 'back' },
      s3: { seq: 'promo', from: 0, to: 89, poster: 's3' },
      s4: { seq: 'pullback', from: 0, to: 119, poster: 's4' }
    }
  };
  var S = window.QUEST_STATE = { ready: false, active: 0, shot: null, frame: null, lit: 0 };

  function get(path) { return path.split('.').reduce(function (o, k) { return o == null ? o : o[k]; }, Q); }
  function clamp(x, a, b) { return x < a ? a : x > b ? b : x; }
  function ease(t) { return t < .5 ? 2 * t * t : 1 - Math.pow(-2 * t + 2, 2) / 2; }
  function smooth(a, b, x) { var t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); }
  function el(tag, cls, html) { var e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; }

  // ---- the boards and the rail, from QUEST
  document.querySelectorAll('[data-board]').forEach(function (host) {
    var rows = Q.prize.shares.map(function (_, i) {
      return '<div class="bd-r p' + (i + 1) + '"><span class="rk" data-figure="board.ranks.' + i + '"></span><span class="seat">+</span>' +
        '<span class="who"><b>Open slot</b><span>could be yours</span></span>' +
        '<span class="pay"><b><span data-figure="prize.shares.' + i + '"></span>%</b><span>of revenue</span></span></div>';
    }).join('');
    host.innerHTML = '<div class="bd glass"><div class="bd-h"><span class="dot"></span><b>REVENUE SHARE</b>' +
      '<span class="tg">TOP <span data-figure="prize.slots"></span></span></div><div class="bd-sub">All open. Be the first.</div>' + rows + '</div>';
  });
  var rail = document.getElementById('rail');
  rail.innerHTML = Q.steps.map(function (s, i) {
    var first = document.querySelector('section[data-step="' + (i + 1) + '"]');
    return '<a data-step="' + (i + 1) + '" href="#' + first.id + '"><i>' + s.n + '</i><span class="lab">' + s.label + '</span><span class="sh">' + s.short + '</span></a>';
  }).join('') + '<span class="bar"><i></i></span>';
  var steps = [].slice.call(rail.querySelectorAll('a'));
  steps.forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      var s = document.getElementById(a.getAttribute('href').slice(1));
      window.scrollTo({ top: s.offsetTop + 1, behavior: 'smooth' });
    });
  });
  document.querySelectorAll('[data-figure]').forEach(function (e) { e.textContent = String(get(e.dataset.figure)); });
  document.querySelectorAll('[data-link]').forEach(function (a) { a.href = get('links.' + a.dataset.link); });

  // ---- the film
  var film = document.getElementById('film');
  var secs = [].slice.call(document.querySelectorAll('section[data-step]'));
  var phone = function () { return innerWidth < 760 || innerHeight > innerWidth * 1.1; };
  var set = phone() ? 'mob' : 'desk';
  var seqs = {};            // name -> { count, imgs: [], started }
  var shots = secs.map(function (sec) {
    var f = Q.film[sec.id] || {}, layer = el('div', 'shot'), poster = el('div', 'poster');
    layer.appendChild(poster);
    var shot = { sec: sec, f: f, layer: layer, poster: poster, panel: sec.querySelector('.panel'), canvas: null, ctx: null, drawn: -1 };
    if (f.seq) { shot.canvas = el('canvas'); layer.appendChild(shot.canvas); shot.ctx = shot.canvas.getContext('2d', { alpha: true }); }
    // the poster: the chapter's still if render.py (or Antigravity, gen/) has made it, deep space until then
    var src = 'stills/' + set + '/' + (f.still || f.poster || sec.id) + '.webp', probe = new Image();
    probe.onload = function () { poster.style.backgroundImage = 'url("' + src + '")'; poster.classList.add('img'); };
    probe.src = src;
    film.appendChild(layer);
    return shot;
  });

  var dpr = Math.min(window.devicePixelRatio || 1, 1.5);
  function size() {
    shots.forEach(function (s) {
      if (!s.canvas) return;
      s.canvas.width = Math.round(innerWidth * dpr); s.canvas.height = Math.round(innerHeight * dpr); s.drawn = -1;
    });
  }

  // frames: frames/manifest.json says what render.py made, per set and sequence ({ "desk": { "approach": { "count": 180 } } })
  var manifest = null;
  fetch('frames/manifest.json').then(function (r) { return r.ok ? r.json() : null; }).then(function (m) {
    manifest = m && m[set]; Object.keys(manifest || {}).forEach(function (k) { seqs[k] = { count: manifest[k].count, imgs: [], started: false }; });
    schedule();
  }).catch(function () {});

  function load(name) {
    var q = seqs[name]; if (!q || q.started) return; q.started = true;
    var order = [], seen = {};
    [16, 8, 4, 2, 1].forEach(function (step) { for (var i = 0; i < q.count; i += step) if (!seen[i]) { seen[i] = 1; order.push(i); } });
    if (!seen[q.count - 1]) order.push(q.count - 1);
    var next = 0, live = 0;
    function pump() {
      while (live < 6 && next < order.length) {
        (function (i) {
          var img = new Image(); live++;
          img.onload = function () { q.imgs[i] = img; live--; schedule(); pump(); };
          img.onerror = function () { live--; pump(); };
          img.src = 'frames/' + set + '/' + name + '/' + String(i).padStart(4, '0') + '.webp';
        })(order[next++]);
      }
    }
    pump();
  }

  function nearest(q, i) {
    for (var d = 0; d < q.count; d++) {
      if (q.imgs[i - d]) return q.imgs[i - d];
      if (q.imgs[i + d]) return q.imgs[i + d];
    }
    return null;
  }

  function draw(s, idx) {
    var q = seqs[s.f.seq]; if (!q) return;
    var img = nearest(q, idx); if (!img) return;
    var key = img.src; if (s.drawn === key) return; s.drawn = key;
    var cw = s.canvas.width, ch = s.canvas.height, k = Math.max(cw / img.naturalWidth, ch / img.naturalHeight);
    var w = img.naturalWidth * k, h = img.naturalHeight * k;
    s.ctx.clearRect(0, 0, cw, ch);
    s.ctx.drawImage(img, (cw - w) / 2, (ch - h) / 2, w, h);
  }

  // ---- one pass: called on the next frame after anything moves
  var queued = false;
  function schedule() { if (!queued) { queued = true; requestAnimationFrame(update); } }

  function update() {
    queued = false;
    var vh = innerHeight, mid = vh / 2, active = 0, lit = 0, best = null, bestCov = -1;
    shots.forEach(function (s) {
      var r = s.sec.getBoundingClientRect();
      var cov = Math.max(0, Math.min(r.bottom, vh) - Math.max(r.top, 0)) / vh;
      var p = clamp(-r.top / Math.max(1, r.height - vh), 0, 1);
      if (r.top <= mid && r.bottom > mid) active = +s.sec.dataset.step;
      // the cut between two worlds: on its way out a chapter's picture dives (grows, blurs) or rises (shrinks); on its
      // way in it settles from a little larger or smaller
      var scale = 1, blur = 0, leaving = r.top < 0, f = s.f;
      if (leaving && f.out === 'dive') { scale = 1 + 1.1 * (1 - cov) * (1 - cov); blur = 10 * (1 - cov); }
      else if (leaving && f.out === 'rise') { scale = 1 - .22 * (1 - cov); blur = 4 * (1 - cov); }
      else if (!leaving && f.in === 'land') { scale = 1 + .35 * (1 - cov); }
      else if (!leaving && f.in === 'back') { scale = 1 + .25 * (1 - cov); }
      if (f.still) scale *= 1.03 + .09 * p;          // a slow push in on a still
      s.layer.style.opacity = cov.toFixed(4);
      s.layer.style.transform = scale === 1 ? '' : 'scale(' + scale.toFixed(4) + ')';
      s.layer.style.filter = blur > .05 ? 'blur(' + blur.toFixed(2) + 'px)' : '';
      lit += cov;
      var idx = null;
      if (f.seq) {
        idx = Math.round(f.from + (f.to - f.from) * ease(p));
        if (cov > 0 || Math.abs(r.top) < vh * 2) load(f.seq);
        if (cov > 0) draw(s, idx);
      }
      if (cov > bestCov) { bestCov = cov; best = { id: s.sec.id, idx: idx }; }
      // the text: in as the chapter arrives, out before it leaves (the hero is there from the start, the last stays)
      if (s.panel) {
        var first = s.sec.id === 'hero', last = s.sec === secs[secs.length - 1];
        var o = first ? 1 - smooth(.45, .8, p) : smooth(.04, .18, p) * (last ? 1 : 1 - smooth(.82, .96, p));
        var y = first ? -60 * smooth(.45, .8, p) : 40 * (1 - smooth(.04, .18, p)) - (last ? 0 : 40 * smooth(.82, .96, p));
        s.panel.style.setProperty('--o', o.toFixed(3));
        s.panel.style.setProperty('--y', y.toFixed(1));
      }
    });
    // the rail: the step in the middle of the screen, the ones before it done, and a line across all four
    rail.dataset.active = String(active);
    steps.forEach(function (a) { var n = +a.dataset.step; a.classList.toggle('on', n === active); a.classList.toggle('done', n < active); });
    var s1 = document.getElementById('s1'), last = secs[secs.length - 1];
    var span = last.offsetTop + last.offsetHeight - vh - s1.offsetTop;
    rail.style.setProperty('--fill', clamp((scrollY - s1.offsetTop + mid) / Math.max(1, span), 0, 1).toFixed(4));
    S.active = active; S.lit = lit; S.shot = best && best.id; S.frame = best ? best.idx : null; S.ready = true;
  }

  size();
  addEventListener('scroll', schedule, { passive: true });
  addEventListener('resize', function () {
    var was = set; set = phone() ? 'mob' : 'desk';
    if (was !== set) location.reload();
    size(); schedule();
  });
  update();
})();
