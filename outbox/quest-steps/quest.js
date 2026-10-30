/* The Cymetica Quest, step by step: the figures, the board's three open slots, the top bar's rail, and what moves as
   you scroll (each step rises in). The animations in the steps are anim.js's. No library.

   QUEST holds every figure and every address on the page. Nothing else may type a number (tests/test_quest_steps.py). */
(function () {
  'use strict';

  var Q = window.QUEST = {
    // The monthly prize (the operator, 2026-10-29: "kept at 500k / 250k / 100k"), as in our Universe mock's leaderboard
    // (outbox/company-live/uv-data.js CO.SEASON.prizes). Cymetica's own sample was 50,000 / 30,000 / 10,000; their
    // operator sets the real prize. It changes here and there.
    prizes: [500000, 250000, 100000],
    unit: 'ET10',
    slots: 3,
    // the builder's pre-built company, read on cymetica.com/company/app/builder 2026-10-30: "7 rooms · 4 departments · 9 agents"
    hq: { rooms: 7, departments: 4, agents: 9 },
    // his five, 2026-10-30
    steps: [
      { n: '01', label: 'Start a company', short: 'Start' },
      { n: '02', label: 'Build', short: 'Build' },
      { n: '03', label: 'Hero agent', short: 'Agent' },
      { n: '04', label: 'Get seen', short: 'Get seen' },
      { n: '05', label: 'Climb', short: 'Climb' }
    ],
    // step 3's lab (examples, as the animation shows them): how many strategies one night tries, in how many
    // generations, and the agents the hero agent races in the Agent Casino (our Universe mock's sample agents)
    lab: { tested: 2400, generations: 48, rivals: ['quantpilot', 'mean-revert-7', 'gem-hunter', 'basis-bot', 'momo-9'] },
    // step 5's leaderboard: our Universe mock's sample companies (uv-data.js) and their points, examples; yours climbs it
    board: [['Giga Fund', 1405], ['Bull Club', 1311], ['Sigma Collective', 976], ['Quasar Fund', 812], ['Vector Trading', 655]],
    you: { name: 'Your company', from: 420, to: 1520 },
    // the only two links on the page, at its end ("to bude az na konci")
    links: {
      builder: 'https://cymetica.com/company/app/builder',
      universe: 'https://cymetica.com/company/app#universe'
    }
  };
  var S = window.QUEST_STATE = { ready: false, active: 0, frames: {} };

  function get(path) { return path.split('.').reduce(function (o, k) { return o == null ? o : o[k]; }, Q); }
  function fmt(v) { return typeof v === 'number' ? v.toLocaleString('en-US') : String(v); }
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var HEX = 'M12 1.6 21 6.8v10.4L12 22.4 3 17.2V6.8z';

  // ---- the board's open slots (the flyer's .seat), the figures, the links, from QUEST
  document.querySelectorAll('[data-seats]').forEach(function (host) {
    host.innerHTML = Q.prizes.map(function (_, i) {
      return '<div class="seat p' + (i + 1) + '"><span class="rk">' + (i + 1) + '</span><span class="open">?</span>' +
        '<span class="who"><b>Open slot</b><span>could be yours</span></span>' +
        '<span class="pay"><b data-figure="prizes.' + i + '"></b><span data-figure="unit"></span></span></div>';
    }).join('');
  });
  document.querySelectorAll('[data-figure]').forEach(function (el) { el.textContent = fmt(get(el.dataset.figure)); });
  document.querySelectorAll('[data-link]').forEach(function (a) { a.href = Q.links[a.dataset.link]; a.target = '_blank'; a.rel = 'noopener'; });

  // ---- the rail: Capital Maximizer's, a hexagon a step and fine lines between that light as you go
  var rail = document.getElementById('rail');
  rail.innerHTML = Q.steps.map(function (s, i) {
    var first = document.querySelector('section[data-step="' + (i + 1) + '"]');
    return (i ? '<i></i>' : '') + '<a data-step="' + (i + 1) + '" href="#' + first.id + '"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="' + HEX + '"/></svg>' +
      '<span class="lab"><em>' + s.n + '</em>' + s.label + '</span><span class="sh">' + s.short + '</span></a>';
  }).join('');
  var steps = [].slice.call(rail.querySelectorAll('a')), lines = [].slice.call(rail.querySelectorAll('i'));
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

  // ---- on every scroll: which step the middle of the screen is in, the rail's hexagons and lines
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
      lines.forEach(function (l, i) { l.classList.toggle('lit', i + 1 < active); });
    }
  }
  var queued = false;
  window.addEventListener('scroll', function () { if (!queued) { queued = true; requestAnimationFrame(function () { queued = false; frame(); }); } }, { passive: true });
  window.addEventListener('resize', frame);
  frame();
  S.ready = true;
})();
