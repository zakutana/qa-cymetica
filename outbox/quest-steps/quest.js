/* The Cymetica Quest, step by step: the figures, the rail, the pictures' frames and hotspots, and what moves as you
   scroll (the hero's picture lies back and stands up, each step rises in, the quest path fills). No library.

   QUEST holds every figure and every address on the page. Nothing else may type a number (tests/test_quest.py). */
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
    apps: 133,                          // /build-it-better, "See the 133 apps already rebuilt", read 2026-10-29
    casino: { seats: 6, tables: 1 },    // /agent-casino, "6 agents. 1 table. Best ROI wins."
    steps: [
      { n: '01', label: 'Start a company', short: 'Start' },
      { n: '02', label: 'Build', short: 'Build' },
      { n: '03', label: 'Get seen', short: 'Get seen' },
      { n: '04', label: 'Climb', short: 'Climb' }
    ],
    links: {
      company: 'https://cymetica.com/company',
      universe: 'https://cymetica.com/company/app#universe',
      bib: 'https://cymetica.com/build-it-better',
      casino: 'https://cymetica.com/agent-casino',
      promo: 'https://cymetica.com/promo-market'
    },
    // the control each step names, as a box in its picture (x, y, w, h as fractions of the picture; capture.py prints them)
    spots: { universe: [0.6269, 0.0355, 0.1445, 0.0406], bib: [0.2778, 0.8214, 0.1644, 0.1313], promo: [0.1632, 0.8011, 0.1639, 0.1276] }
  };
  var S = window.QUEST_STATE = { ready: false, active: 0 };

  function get(path) { return path.split('.').reduce(function (o, k) { return o == null ? o : o[k]; }, Q); }
  function fmt(v) { return typeof v === 'number' ? v.toLocaleString('en-US') : String(v); }
  function clamp(x, a, b) { return x < a ? a : x > b ? b : x; }
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  // ---- the prize rows, the figures, the links, from QUEST
  document.querySelectorAll('[data-prizes]').forEach(function (host) {
    host.innerHTML = Q.prizes.map(function (_, i) {
      return '<div class="pz p' + (i + 1) + '"><span class="pl" data-figure="places.' + i + '"></span><b data-figure="prizes.' + i + '"></b>' +
        '<span class="un" data-figure="unit"></span></div>';
    }).join('');
  });
  document.querySelectorAll('[data-figure]').forEach(function (el) { el.textContent = fmt(get(el.dataset.figure)); });
  document.querySelectorAll('[data-link]').forEach(function (a) { a.href = Q.links[a.dataset.link]; a.target = '_blank'; a.rel = 'noopener'; });

  // ---- each picture in a browser frame: the address it came from on top, a pulse on the control the step names
  document.querySelectorAll('figure.frame').forEach(function (f) {
    var addr = Q.links[f.dataset.addr].replace(/^https:\/\//, '').replace(/#.*$/, '');
    var bar = document.createElement('div');
    bar.className = 'bar';
    bar.innerHTML = '<i></i><i></i><i></i><span class="addr"><b></b>' + addr + '</span>';
    f.insertBefore(bar, f.firstChild);
    var shot = document.createElement('div');
    shot.className = 'shot';
    var img = f.querySelector('img:not(.strip)');
    f.insertBefore(shot, img);
    shot.appendChild(img);
    if (f.dataset.spot) {
      var p = Q.spots[f.dataset.spot], s = document.createElement('span');
      s.className = 'spot';
      s.style.left = (p[0] * 100) + '%';
      s.style.top = (p[1] * 100) + '%';
      s.style.width = (p[2] * 100) + '%';
      s.style.height = (p[3] * 100) + '%';
      shot.appendChild(s);
    }
    f.insertAdjacentHTML('beforeend', '<span class="sheen" aria-hidden="true"></span>');
  });

  // ---- the rail
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
      window.scrollTo({ top: s.offsetTop - innerHeight * 0.1, behavior: 'smooth' });
    });
  });
  document.querySelectorAll('a[href^="#"]:not([data-step])').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      var s = document.getElementById(a.getAttribute('href').slice(1));
      window.scrollTo({ top: s.offsetTop - innerHeight * 0.1, behavior: 'smooth' });
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

  // ---- the pictures lean towards the pointer, a little
  if (!reduce && matchMedia('(hover: hover)').matches) {
    document.querySelectorAll('.stage').forEach(function (st) {
      var f = st.querySelector('.frame');
      st.addEventListener('pointermove', function (e) {
        var r = st.getBoundingClientRect(), x = (e.clientX - r.left) / r.width - 0.5, y = (e.clientY - r.top) / r.height - 0.5;
        f.style.setProperty('--px', (x * 7).toFixed(2) + 'deg');
        f.style.setProperty('--py', (-y * 6).toFixed(2) + 'deg');
        f.style.setProperty('--gx', ((x + 0.5) * 100).toFixed(1) + '%');
      });
      st.addEventListener('pointerleave', function () { f.style.setProperty('--px', '0deg'); f.style.setProperty('--py', '0deg'); });
    });
  }

  // ---- on every scroll: which step the middle of the screen is in, the rail's fill, the hero picture standing up
  var sections = [].slice.call(document.querySelectorAll('section[data-step]'));
  var hero = document.querySelector('.hero-stage .frame');
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
    if (hero && !reduce) {
      var t = clamp(scrollY / (innerHeight * 0.7), 0, 1);
      hero.style.setProperty('--lie', (24 * (1 - t)).toFixed(2) + 'deg');
      hero.style.setProperty('--lift', (1 - t).toFixed(3));
    }
  }
  var queued = false;
  window.addEventListener('scroll', function () { if (!queued) { queued = true; requestAnimationFrame(function () { queued = false; frame(); }); } }, { passive: true });
  window.addEventListener('resize', frame);
  frame();
  S.ready = true;
})();
