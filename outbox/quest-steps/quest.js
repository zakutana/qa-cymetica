/* The Cymetica Quest, step by step: the figures, the rail, and what moves as you scroll (each step rises in) or point
   (each step's hologram of the web leans a little towards the pointer). No library.

   QUEST holds every figure and every address on the page. Nothing else may type a number (tests/test_quest_steps.py). */
(function () {
  'use strict';

  var Q = window.QUEST = {
    // The monthly prize (the operator, 2026-10-29: "kept at 500k / 250k / 100k"), as in our Universe mock's leaderboard
    // (outbox/company-live/uv-data.js CO.SEASON.prizes), so the page and its podium picture are the same figures.
    // Cymetica's own sample was 50,000 / 30,000 / 10,000; their operator sets the real prize. It changes here and there.
    prizes: [500000, 250000, 100000],
    places: ['1st', '2nd', '3rd'],
    unit: 'ET10',
    slots: 3,
    // the builder's pre-built company, read on cymetica.com/company/app/builder 2026-10-29: "7 rooms · 4 departments · 9 agents"
    hq: { rooms: 7, departments: 4, agents: 9 },
    apps: 133,                          // /build-it-better, "See the 133 apps already rebuilt", read 2026-10-29
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
      casino: 'https://cymetica.com/agent-casino',
      promo: 'https://cymetica.com/promo-market'
    }
  };
  var S = window.QUEST_STATE = { ready: false, active: 0 };

  function get(path) { return path.split('.').reduce(function (o, k) { return o == null ? o : o[k]; }, Q); }
  function fmt(v) { return typeof v === 'number' ? v.toLocaleString('en-US') : String(v); }
  function clamp(x, a, b) { return x < a ? a : x > b ? b : x; }
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---- the prize chips, the figures, the links, from QUEST
  document.querySelectorAll('[data-prizes]').forEach(function (host) {
    host.innerHTML = Q.prizes.map(function (_, i) {
      return '<div class="pz p' + (i + 1) + '"><span class="pl" data-figure="places.' + i + '"></span><b data-figure="prizes.' + i + '"></b>' +
        '<span class="un" data-figure="unit"></span></div>';
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
  document.querySelectorAll('a[href^="#"]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      var s = document.getElementById(a.getAttribute('href').slice(1));
      window.scrollTo({ top: s.offsetTop - innerHeight * 0.06, behavior: reduce ? 'auto' : 'smooth' });
    });
  });

  // ---- a step rises in the first time it comes on screen
  var rv = [].slice.call(document.querySelectorAll('.rv'));
  if (reduce || !('IntersectionObserver' in window)) rv.forEach(function (e) { e.classList.add('in'); });
  else {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
    }, { rootMargin: '0px 0px -12% 0px' });
    rv.forEach(function (e) { io.observe(e); });
  }

  // ---- each hologram leans a little towards the pointer
  if (!reduce && matchMedia('(hover: hover)').matches) {
    document.querySelectorAll('.stage').forEach(function (st) {
      st.addEventListener('pointermove', function (e) {
        var r = st.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
        st.style.setProperty('--px', (x * 8).toFixed(2) + 'deg');
        st.style.setProperty('--py', (-y * 6).toFixed(2) + 'deg');
      });
      st.addEventListener('pointerleave', function () { st.style.setProperty('--px', '0deg'); st.style.setProperty('--py', '0deg'); });
    });
  }

  // ---- on every scroll: which step the middle of the screen is in, and the rail's fill
  var sections = [].slice.call(document.querySelectorAll('section[data-step]'));
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
  }
  var queued = false;
  window.addEventListener('scroll', function () { if (!queued) { queued = true; requestAnimationFrame(function () { queued = false; frame(); }); } }, { passive: true });
  window.addEventListener('resize', frame);
  frame();
  S.ready = true;
})();
