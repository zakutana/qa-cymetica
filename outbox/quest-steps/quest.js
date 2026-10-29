/* The Cymetica Quest, step by step: the figures, the rail, the opening's flight, and what moves as you scroll (the words
   rise in, the pictures drift a little slower than the page, the prizes count up). No library.

   The flight is outbox/quest's engine made small: an image sequence on a canvas, scrubbed by how far through the
   opening the page is -- scroll down and the camera flies in, scroll up and it flies back. Frames load coarse to fine,
   so a fast scroll always has a near frame to show, and the first frame stands under them until they come.

   QUEST holds every figure and every address on the page. Nothing else may type a number (tests/test_quest_steps.py). */
(function () {
  'use strict';

  var Q = window.QUEST = {
    // The monthly prize (the operator, 2026-10-29: "kept at 500k / 250k / 100k"), as in our Universe mock's leaderboard
    // (outbox/company-live/uv-data.js CO.SEASON.prizes), so the page and its picture are the same figures. Cymetica's own
    // sample was 50,000 / 30,000 / 10,000; their operator sets the real prize. If it changes, it changes here and there.
    prizes: [500000, 250000, 100000],
    places: ['1st', '2nd', '3rd'],
    unit: 'ET10',
    slots: 3,
    // the builder's pre-built company, read on cymetica.com/company/app/builder 2026-10-29: "7 rooms · 4 departments · 9 agents"
    hq: { rooms: 7, departments: 4, agents: 9 },
    steps: [
      { n: '01', label: 'Start a company', short: 'Start' },
      { n: '02', label: 'Build', short: 'Build' },
      { n: '03', label: 'Get seen', short: 'Get seen' },
      { n: '04', label: 'Climb', short: 'Climb' }
    ],
    links: {
      builder: 'https://cymetica.com/company/app/builder',
      universe: 'https://cymetica.com/company/app#universe',
      bib: 'https://cymetica.com/build-it-better',
      lab: 'https://cymetica.com/company/app/experiments',
      promo: 'https://cymetica.com/promo-market'
    },
    // the opening's flight: capture.py's frames (pics/fly/, not in git) over its first frame (pics/fly-0.webp, kept)
    fly: { count: 71, dir: 'pics/fly/', poster: 'pics/fly-0.webp' }
  };
  var S = window.QUEST_STATE = { ready: false, active: 0, frame: 0, drawn: -1, loaded: 0 };

  function get(path) { return path.split('.').reduce(function (o, k) { return o == null ? o : o[k]; }, Q); }
  function fmt(v) { return typeof v === 'number' ? v.toLocaleString('en-US') : String(v); }
  function clamp(x, a, b) { return x < a ? a : x > b ? b : x; }
  function smooth(a, b, x) { var t = clamp((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t); }
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---- the prizes, the figures, the links, from QUEST
  document.querySelectorAll('[data-prizes]').forEach(function (host) {
    host.innerHTML = Q.prizes.map(function (_, i) {
      return '<div class="pz p' + (i + 1) + '"><span class="pl" data-figure="places.' + i + '"></span>' +
        '<b data-figure="prizes.' + i + '" data-count></b><span class="un" data-figure="unit"></span></div>';
    }).join('');
  });
  document.querySelectorAll('[data-figure]').forEach(function (el) { el.textContent = fmt(get(el.dataset.figure)); });
  document.querySelectorAll('[data-link]').forEach(function (a) { a.href = Q.links[a.dataset.link]; a.target = '_blank'; a.rel = 'noopener'; });

  // ---- the rail
  var rail = document.getElementById('rail');
  rail.innerHTML = Q.steps.map(function (s, i) {
    var first = document.querySelector('section[data-step="' + (i + 1) + '"]');
    return '<a data-step="' + (i + 1) + '" href="#' + first.id + '"><i>' + s.n + '</i><span class="lab">' + s.label + '</span><span class="sh">' + s.short + '</span></a>';
  }).join('') + '<span class="bar"><i></i></span>';
  var steps = [].slice.call(rail.querySelectorAll('a'));
  function jump(id) {
    var s = document.getElementById(id);
    window.scrollTo({ top: s.offsetTop + (id === 's1' ? 0 : 1), behavior: reduce ? 'auto' : 'smooth' });
  }
  document.querySelectorAll('a[href^="#"]').forEach(function (a) {
    a.addEventListener('click', function (e) { e.preventDefault(); jump(a.getAttribute('href').slice(1)); });
  });

  // ---- the words rise in, the prizes count up, the first time each comes on screen
  function countUp(el) {
    var to = +String(get(el.dataset.figure)), t0 = performance.now(), dur = 1400;
    if (reduce || !isFinite(to)) return;
    (function tick(now) {
      var t = clamp((now - t0) / dur, 0, 1), e = 1 - Math.pow(1 - t, 4);
      el.textContent = fmt(t < 1 ? Math.round(to * e / 1000) * 1000 : to);
      if (t < 1) requestAnimationFrame(tick);
    })(t0);
  }
  var rv = [].slice.call(document.querySelectorAll('.rv'));
  if (reduce || !('IntersectionObserver' in window)) rv.forEach(function (e) { e.classList.add('in'); });
  else {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) {
        if (!e.isIntersecting) return;
        e.target.classList.add('in');
        e.target.querySelectorAll('[data-count]').forEach(countUp);
        io.unobserve(e.target);
      });
    }, { rootMargin: '0px 0px -10% 0px' });
    rv.forEach(function (e) { io.observe(e); });
  }

  // ---- the opening's flight
  var cv = document.getElementById('fly'), ctx = cv.getContext('2d'), frames = new Array(Q.fly.count);
  var poster = new Image();
  poster.onload = function () { S.drawn = -1; draw(); };
  poster.src = Q.fly.poster;
  document.querySelector('.flight .poster').style.backgroundImage = 'url(' + Q.fly.poster + ')';
  function size() {
    var r = Math.min(window.devicePixelRatio || 1, 1.5);
    cv.width = Math.round(cv.clientWidth * r); cv.height = Math.round(cv.clientHeight * r);
    S.drawn = -1;
  }
  function cover(img) {
    var cw = cv.width, ch = cv.height, s = Math.max(cw / img.naturalWidth, ch / img.naturalHeight);
    var w = img.naturalWidth * s, h = img.naturalHeight * s;
    ctx.drawImage(img, (cw - w) / 2, (ch - h) / 2, w, h);
  }
  function nearest(i) {
    for (var d = 0; d < frames.length; d++) {
      if (frames[i - d] && frames[i - d].ok) return i - d;
      if (frames[i + d] && frames[i + d].ok) return i + d;
    }
    return -1;
  }
  function draw() {
    var k = nearest(S.frame);
    if (k === S.drawn && k >= 0) return;
    if (k >= 0) { cover(frames[k]); S.drawn = k; }
    else if (poster.complete && poster.naturalWidth) { cover(poster); S.drawn = -2; }
  }
  // coarse to fine: every 16th frame, then every 8th, ... so the whole flight is there early, roughly
  var order = [], seen = {};
  [16, 8, 4, 2, 1].forEach(function (st) { for (var i = 0; i < Q.fly.count; i += st) if (!seen[i]) { seen[i] = 1; order.push(i); } });
  var next = 0, live = 0;
  function pump() {
    while (live < 6 && next < order.length) {
      (function (i) {
        var im = new Image(); live++;
        im.onload = function () { im.ok = true; frames[i] = im; S.loaded++; live--; draw(); pump(); };
        im.onerror = function () { live--; next = order.length; };   // no frames here (a fresh clone): the first frame stays
        im.src = Q.fly.dir + String(i).padStart(3, '0') + '.webp';
      })(order[next++]);
    }
  }

  // ---- on every scroll: the step the middle of the screen is in, the rail's fill, the flight, the drift
  var hero = document.getElementById('hero'), heroCopy = hero.querySelector('.hero-copy'), cue = hero.querySelector('.cue');
  var sections = [].slice.call(document.querySelectorAll('section[data-step]'));
  var drifts = [].slice.call(document.querySelectorAll('.scene .bg img, .way .bg img'));
  function frame() {
    var mid = innerHeight / 2, active = 0;
    sections.forEach(function (s) { var r = s.getBoundingClientRect(); if (r.top <= mid && r.bottom > mid) active = +s.dataset.step; });
    if (active !== S.active || !S.ready) {
      S.active = active;
      rail.dataset.active = active;
      steps.forEach(function (a) {
        var n = +a.dataset.step;
        a.classList.toggle('on', n === active);
        a.classList.toggle('done', n < active);
      });
    }
    var first = document.getElementById('s1').offsetTop, last = document.getElementById('go').offsetTop;
    rail.style.setProperty('--fill', clamp((scrollY + mid - first) / (last - first), 0, 1).toFixed(4));
    // the flight: through the opening's scroll, frame 0 to the last
    var span = Math.max(1, hero.offsetHeight - innerHeight), p = clamp(scrollY / span, 0, 1);
    S.frame = Math.round(p * (Q.fly.count - 1));
    draw();
    if (!reduce) {
      heroCopy.style.opacity = (1 - smooth(0.12, 0.5, p)).toFixed(3);
      heroCopy.style.transform = 'translateY(' + (-60 * smooth(0, 0.6, p)).toFixed(1) + 'px)';
      cue.style.opacity = (1 - smooth(0.02, 0.12, p)).toFixed(3);
      drifts.forEach(function (im) {
        var r = im.parentNode.getBoundingClientRect(), t = clamp((mid - (r.top + r.height / 2)) / (innerHeight + r.height), -0.5, 0.5);
        im.style.transform = 'translate3d(0,' + (t * 9).toFixed(2) + '%,0) scale(1.08)';
      });
    }
  }
  var queued = false;
  window.addEventListener('scroll', function () { if (!queued) { queued = true; requestAnimationFrame(function () { queued = false; frame(); }); } }, { passive: true });
  window.addEventListener('resize', function () { size(); frame(); });

  // the pointer's light on the pictures, and the call leaning towards it
  if (!reduce && matchMedia('(hover: hover)').matches) {
    document.querySelectorAll('.scene, .way, .climb').forEach(function (s) {
      s.addEventListener('pointermove', function (e) {
        var r = s.getBoundingClientRect();
        s.style.setProperty('--mx', ((e.clientX - r.left) / r.width * 100).toFixed(1) + '%');
        s.style.setProperty('--my', ((e.clientY - r.top) / r.height * 100).toFixed(1) + '%');
      });
    });
    document.querySelectorAll('.cta').forEach(function (b) {
      b.addEventListener('pointermove', function (e) {
        var r = b.getBoundingClientRect();
        b.style.transform = 'translate(' + ((e.clientX - r.left - r.width / 2) * 0.12).toFixed(1) + 'px,' + ((e.clientY - r.top - r.height / 2) * 0.18).toFixed(1) + 'px)';
      });
      b.addEventListener('pointerleave', function () { b.style.transform = ''; });
    });
  }

  size();
  frame();
  pump();
  S.ready = true;
})();
