/* The Cymetica Quest, step by step: the figures, the icons, the board's three open slots, the top bar's rail, and
   what moves as you scroll (each step rises in). The animations in the steps are anim.js's. No library.

   QUEST holds every figure and every address on the page. */
(function () {
  'use strict';

  var Q = window.QUEST = {
    // The monthly prize (the operator, 2026-10-29: "kept at 500k / 250k / 100k"), as in our Universe mock's leaderboard
    // (outbox/company-live/uv-data.js CO.SEASON.prizes). Cymetica has not confirmed it.
    prizes: [500000, 250000, 100000],
    unit: 'ET10',
    slots: 3,
    // the builder's pre-built company, read on cymetica.com/company/app/builder 2026-10-30: "7 rooms · 4 departments · 9 agents"
    hq: { rooms: 7, departments: 4, agents: 9 },
    // Build it Better's own count, GET /api/v1/build-it-better/apps/leaderboard, 2026-10-30
    apps: 134,
    // the products in step 2's strip, the most visited first (capture.py apps), each its preview in pics/apps/
    built: [['Gem Screener', 'gem-screener'], ['Chart Analyzer', 'chart-analyzer'], ['Agent Casino', 'agent-casino'], ['Supply Analyzer', 'supply-analyzer'],
            ['Crypto Dashboards', 'crypto'], ['AI Marketplace', 'ai-marketplace'], ['TradingView', 'tradingview'], ['Weekly Signal', 'weekly-signal'],
            ['Team Dump Radar', 'team-dump-radar'], ['Airdrop Farmer', 'airdrop-farmer'], ['Events', 'events'], ['Infiltrator', 'infiltrator'],
            ['Nasdaq Data Link', 'nasdaq-data-link']],
    // his four (2026-10-30: "ty stepy 1. 2. 3. 4. ... 2. build products or hero agents"); the second's two ways share
    // one screen and a slider between them ("to bude hit")
    steps: [
      { n: '01', label: 'Start a company', short: 'Start' },
      { n: '02', label: 'Build or breed', short: 'Build' },
      { n: '03', label: 'Get seen', short: 'Get seen' },
      { n: '04', label: 'Climb', short: 'Climb' }
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
  var S = window.QUEST_STATE = { ready: false, active: 0, frames: {}, side: 'build' };

  // the icons: the company's own department icons (outbox/company-live/data.js DEPT_ICON: "pridej hezke ikonky i zde
  // k departmentum"), and the rest drawn the same way, line icons on a 20 x 20 grid
  var ICON = window.QUEST_ICON = {
    hub: '<circle cx="10" cy="10" r="2.4" fill="currentColor"/><ellipse cx="10" cy="10" rx="7.6" ry="2.9"/><ellipse cx="10" cy="10" rx="7.6" ry="2.9" transform="rotate(60 10 10)"/><ellipse cx="10" cy="10" rx="7.6" ry="2.9" transform="rotate(-60 10 10)"/>',
    development: '<rect x="2.5" y="3.5" width="15" height="13" rx="2"/><path d="M2.5 7h15 M8.2 9.6l-2.3 2.4 2.3 2.4 M11.8 9.6l2.3 2.4-2.3 2.4"/>',
    design: '<path d="M10 2.6l5.4 9.9L10 17.4l-5.4-4.9Z M10 2.6v7.4"/><circle cx="10" cy="11.3" r="1.5"/>',
    testing: '<ellipse cx="10" cy="11.6" rx="3.6" ry="4.6"/><circle cx="10" cy="5.6" r="1.8"/><path d="M10 8.4v7.6 M6.4 10.6H3.2 M16.8 10.6h-3.2 M6.6 14l-2.7 1.9 M13.4 14l2.7 1.9 M8.6 4.4 7.2 2.6 M11.4 4.4l1.4-1.8"/>',
    lab: '<path d="M7.4 2.6h5.2 M8.5 2.6v5.2L4.1 15.4a1.4 1.4 0 0 0 1.2 2.1h9.4a1.4 1.4 0 0 0 1.2-2.1L11.5 7.8V2.6 M5.9 12.6h8.2"/><circle cx="9" cy="15" r=".8" fill="currentColor"/><circle cx="11.6" cy="14.4" r=".6" fill="currentColor"/>',
    trading: '<path d="M5 2.8v14.4 M10 2v16 M15 4.6v11"/><rect x="3.5" y="6" width="3" height="6.2" rx=".6"/><rect x="8.5" y="9" width="3" height="5.2" rx=".6"/><rect x="13.5" y="6.6" width="3" height="4.6" rx=".6"/>',
    monitor: '<rect x="3" y="3.4" width="14" height="9.6" rx="1.6"/><path d="M7.4 16.6h5.2 M10 13v3.6 M5.6 6.4h5 M5.6 9h3"/>',
    audit: '<circle cx="10" cy="10" r="3.3"/><path d="M10 2.4v2.3 M10 15.3v2.3 M2.4 10h2.3 M15.3 10h2.3 M4.6 4.6l1.6 1.6 M13.8 13.8l1.6 1.6 M4.6 15.4l1.6-1.6 M13.8 6.2l1.6-1.6 M8.6 10l1 1 1.9-2"/>',
    vault: '<rect x="2.6" y="3.2" width="14.8" height="13.6" rx="2"/><circle cx="10" cy="10" r="3.9"/><circle cx="10" cy="10" r="1" fill="currentColor"/><path d="M10 6.1v1.6 M10 12.3v1.6 M6.1 10h1.6 M12.3 10h1.6 M5 16.8v1 M15 16.8v1"/>',
    bulb: '<path d="M7.2 14.2h5.6 M7.8 16.6h4.4 M10 2.6a5 5 0 0 0-3 9c.6.5 1 1.2 1 2v.6h4v-.6c0-.8.4-1.5 1-2a5 5 0 0 0-3-9Z"/>',
    doc: '<path d="M5 2.6h6.6L15 6v11.4H5Z M11.4 2.6V6H15 M7.4 9.4h5.2 M7.4 12h5.2 M7.4 14.6h3.2"/>',
    server: '<rect x="3" y="3" width="14" height="5.4" rx="1.2"/><rect x="3" y="11.6" width="14" height="5.4" rx="1.2"/><path d="M6 5.7h.01 M6 14.3h.01 M9 5.7h5 M9 14.3h5"/>',
    data: '<ellipse cx="10" cy="4.6" rx="6" ry="2.2"/><path d="M4 4.6v10.8c0 1.2 2.7 2.2 6 2.2s6-1 6-2.2V4.6 M4 10c0 1.2 2.7 2.2 6 2.2s6-1 6-2.2"/>',
    shield: '<path d="M10 2.4l6.4 2.4v4.8c0 4-2.7 6.9-6.4 8-3.7-1.1-6.4-4-6.4-8V4.8Z M7.2 10l2 2 3.8-3.8"/>',
    rocket: '<path d="M11.8 3.2c2.4-.6 4.4-.6 5 0 .6.6.6 2.6 0 5l-5.6 5.6-4.9-4.9Z M6.3 8.9 3.4 8.6l2.2-2.2 3.4-.4 M11.1 13.7l.3 2.9 2.2-2.2.4-3.4 M5.8 14.2c-1 .4-1.8 1.6-2 2.8 1.2-.2 2.4-1 2.8-2"/><circle cx="13.2" cy="6.8" r="1.2"/>',
    cloud: '<path d="M6 15.6h8.4a3.4 3.4 0 0 0 .4-6.8A4.8 4.8 0 0 0 5.6 8 3.8 3.8 0 0 0 6 15.6Z"/>',
    crown: '<path d="M3 6.4l3.6 3 3.4-5 3.4 5 3.6-3-1.4 9H4.4Z M4.4 15.4h11.2"/>',
    robot: '<rect x="4.4" y="6.4" width="11.2" height="9" rx="2.4"/><path d="M10 3.2v3.2 M2.6 10.4v2.6 M17.4 10.4v2.6 M7.6 16.6v1.6 M12.4 16.6v1.6"/><circle cx="10" cy="2.8" r=".9" fill="currentColor"/><circle cx="7.8" cy="10.6" r="1.1" fill="currentColor"/><circle cx="12.2" cy="10.6" r="1.1" fill="currentColor"/>',
    trophy: '<path d="M6.2 3h7.6v4.4a3.8 3.8 0 0 1-7.6 0Z M6.2 4.6H3.4a2.8 2.8 0 0 0 2.9 3.2 M13.8 4.6h2.8a2.8 2.8 0 0 1-2.9 3.2 M10 11.2v3.2 M6.6 17h6.8 M7.6 14.4h4.8v2.6H7.6Z"/>',
    megaphone: '<path d="M3 8.4v3.4h2.6L12.6 16V4.2L5.6 8.4Z M5.6 11.8l1 4.6h2.2l-.8-3.8 M15 7.4a3.4 3.4 0 0 1 0 5.4"/>',
    planet: '<circle cx="10" cy="10" r="4.6"/><path d="M3.4 13.8c-1.6 1.6-2 2.8-1.4 3.4 1.2 1.2 6-1.6 10.4-6S18.6 3 17.4 1.8c-.6-.6-1.8-.2-3.4 1.4"/>',
    users: '<circle cx="7.4" cy="7" r="2.8"/><path d="M2.4 16.6c.4-3 2.4-4.6 5-4.6s4.6 1.6 5 4.6 M13 4.6a2.6 2.6 0 0 1 0 5 M14.6 12.4c1.6.5 2.8 2 3 4.2"/>',
    chart: '<path d="M2.8 16.6h14.4 M4 13.6l4-4.4 3 2.6 5-6.2 M13.4 5.6H16v2.6"/>',
    arrow: '<path d="M4 10h12 M11.4 5.4 16 10l-4.6 4.6"/>'
  };
  function icon(k) { return '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (ICON[k] || '') + '</svg>'; }
  window.QUEST_ICON_SVG = icon;
  document.querySelectorAll('[data-ic]').forEach(function (el) { el.innerHTML = icon(el.dataset.ic); });

  function get(path) { return path.split('.').reduce(function (o, k) { return o == null ? o : o[k]; }, Q); }
  function fmt(v) { return typeof v === 'number' ? v.toLocaleString('en-US') : String(v); }
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var HEX = 'M12 1.6 21 6.8v10.4L12 22.4 3 17.2V6.8z';

  // ---- the board's open slots (the flyer's .seat), step 2's strip of built products, the figures, the links
  document.querySelectorAll('[data-seats]').forEach(function (host) {
    host.innerHTML = Q.prizes.map(function (_, i) {
      return '<div class="seat p' + (i + 1) + '"><span class="rk">' + (i + 1) + '</span><span class="open">?</span>' +
        '<span class="who"><b>Open slot</b><span>could be yours</span></span>' +
        '<span class="pay"><b data-figure="prizes.' + i + '"></b><span data-figure="unit"></span></span></div>';
    }).join('');
  });
  document.querySelectorAll('[data-built]').forEach(function (host) {
    host.innerHTML = Q.built.map(function (a) {
      return '<figure class="app"><img src="pics/apps/' + a[1] + '.webp" alt="" width="480" height="270" loading="lazy"><figcaption>' + a[0] + '</figcaption></figure>';
    }).join('');
  });
  document.querySelectorAll('[data-figure]').forEach(function (el) { el.textContent = fmt(get(el.dataset.figure)); });
  document.querySelectorAll('[data-link]').forEach(function (a) { a.href = Q.links[a.dataset.link]; a.target = '_blank'; a.rel = 'noopener'; });

  // ---- the rail: Capital Maximizer's, a hexagon a step and fine lines between that light as you go
  var rail = document.getElementById('rail');
  rail.innerHTML = Q.steps.map(function (s, i) {
    return (i ? '<i></i>' : '') + '<a data-step="' + (i + 1) + '" href="#s' + (i + 1) + '"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="' + HEX + '"/></svg>' +
      '<span class="lab"><em>' + s.n + '</em>' + s.label + '</span><span class="sh">' + s.short + '</span></a>';
  }).join('');
  var steps = [].slice.call(rail.querySelectorAll('a')), lines = [].slice.call(rail.querySelectorAll('i'));
  // a link to a step goes to its section; to step 2 or 3 it also turns the slider to that side
  document.querySelectorAll('a[href^="#"]').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      var el = document.getElementById(a.getAttribute('href').slice(1)), sec = el.closest('section') || el;
      window.scrollTo({ top: sec.getBoundingClientRect().top + scrollY - innerHeight * 0.06, behavior: reduce ? 'auto' : 'smooth' });
      if (el.classList.contains('pane') && window.QUEST_SIDE) window.QUEST_SIDE(el.id === 's2b' ? 'agent' : 'build');
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

  // ---- on every scroll (and every turn of the slider): which step is on screen, the rail's hexagons and lines
  var sections = [].slice.call(document.querySelectorAll('section[data-step]'));
  function frame(force) {
    var mid = innerHeight / 2, active = 0;
    sections.forEach(function (s) { var r = s.getBoundingClientRect(); if (r.top <= mid && r.bottom > mid) active = +s.dataset.step; });
    if (active !== S.active || !S.ready || force) {
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
  window.QUEST_RAIL = function () { frame(true); };
  var queued = false;
  window.addEventListener('scroll', function () { if (!queued) { queued = true; requestAnimationFrame(function () { queued = false; frame(); }); } }, { passive: true });
  window.addEventListener('resize', function () { frame(); });
  frame();
  S.ready = true;
})();
