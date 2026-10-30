/* The Cymetica Quest, step by step: the figures, the board's three open slots, the top bar's rail, and what moves as
   you scroll (each step rises in). The animations in the steps are anim.js's. No library.

   QUEST holds every figure and every address on the page. */
(function () {
  'use strict';

  var Q = window.QUEST = {
    // The monthly prize (the operator, 2026-10-29: "kept at 500k / 250k / 100k"), as in our Universe mock's leaderboard
    // (outbox/company-live/uv-data.js CO.SEASON.prizes). Cymetica has not confirmed it.
    prizes: [500000, 250000, 100000],
    unit: 'ET10',
    slots: 3,
    // the live builder's pre-build (builder.js PRE, data.js TEMPLATES, read 2026-10-30): four departments, two AI agents
    // each, and a supervisor in Operations: nine agents, three of them researchers; NEXUS in Command runs them
    hq: { agents: 9, researchers: 3 },
    // Build it Better's own count, GET /api/v1/build-it-better/apps/leaderboard, 2026-10-30
    apps: 134,
    // the products in step 2's ring, the most visited first, each its live page (capture.py apps: pics/apps/)
    built: [['Gem Screener', 'gem-screener'], ['Chart Analyzer', 'chart-analyzer'], ['Agent Casino', 'agent-casino'], ['Supply Analyzer', 'supply-analyzer'],
            ['Crypto Dashboards', 'crypto'], ['AI Marketplace', 'ai-marketplace'], ['TradingView', 'tradingview'], ['Weekly Signal', 'weekly-signal'],
            ['Team Dump Radar', 'team-dump-radar'], ['Airdrop Farmer', 'airdrop-farmer'], ['Events', 'events'], ['Infiltrator', 'infiltrator'],
            ['Nasdaq Data Link', 'nasdaq-data-link']],
    // step 2's pipeline: an idea in, a product out (each a real product Build it Better has built)
    ideas: [['a screener that finds hidden gems first', 'Gem Screener', 'gem-screener'], ['an AI that reads any chart', 'Chart Analyzer', 'chart-analyzer'],
            ['a casino where AI agents play', 'Agent Casino', 'agent-casino'], ['a bot that farms every airdrop', 'Airdrop Farmer', 'airdrop-farmer'],
            ['a radar for team token dumps', 'Team Dump Radar', 'team-dump-radar']],
    // his five, 2026-10-30
    steps: [
      { n: '01', label: 'Start', short: 'Start' },
      { n: '02', label: 'Build', short: 'Build' },
      { n: '03', label: 'Hero agent', short: 'Agent' },
      { n: '04', label: 'Get seen', short: 'Seen' },
      { n: '05', label: 'Climb', short: 'Climb' }
    ],
    // the last step's leaderboard: our Universe mock's sample companies (uv-data.js, their station as their mark) and
    // their points, examples; yours climbs it
    board: [['Giga Fund', 1405, 'station-vault-red'], ['Bull Club', 1311, 'station-pyramid-red'], ['Sigma Collective', 976, 'station-tower-blue'],
            ['Quasar Fund', 812, 'station-dome-green'], ['Vector Trading', 655, 'station-tower-cyan']],
    you: { name: 'Your company', from: 420, to: 1520, mark: 'you' },
    // the only two links on the page, at its end ("to bude az na konci")
    links: {
      builder: 'https://cymetica.com/company/app/builder',
      universe: 'https://cymetica.com/company/app#universe'
    }
  };
  var S = window.QUEST_STATE = { ready: false, active: 0, frames: {} };

  // line icons on a 20 x 20 grid, for the pipeline's chambers (the company's own department icons among them,
  // outbox/company-live/data.js DEPT_ICON)
  var ICON = window.QUEST_ICON = {
    doc: '<path d="M5 2.6h6.6L15 6v11.4H5Z M11.4 2.6V6H15 M7.4 9.4h5.2 M7.4 12h5.2 M7.4 14.6h3.2"/>',
    design: '<path d="M10 2.6l5.4 9.9L10 17.4l-5.4-4.9Z M10 2.6v7.4"/><circle cx="10" cy="11.3" r="1.5"/>',
    development: '<rect x="2.5" y="3.5" width="15" height="13" rx="2"/><path d="M2.5 7h15 M8.2 9.6l-2.3 2.4 2.3 2.4 M11.8 9.6l2.3 2.4-2.3 2.4"/>',
    shield: '<path d="M10 2.4l6.4 2.4v4.8c0 4-2.7 6.9-6.4 8-3.7-1.1-6.4-4-6.4-8V4.8Z M7.2 10l2 2 3.8-3.8"/>',
    rocket: '<path d="M11.8 3.2c2.4-.6 4.4-.6 5 0 .6.6.6 2.6 0 5l-5.6 5.6-4.9-4.9Z M6.3 8.9 3.4 8.6l2.2-2.2 3.4-.4 M11.1 13.7l.3 2.9 2.2-2.2.4-3.4 M5.8 14.2c-1 .4-1.8 1.6-2 2.8 1.2-.2 2.4-1 2.8-2"/><circle cx="13.2" cy="6.8" r="1.2"/>',
    cloud: '<path d="M6 15.6h8.4a3.4 3.4 0 0 0 .4-6.8A4.8 4.8 0 0 0 5.6 8 3.8 3.8 0 0 0 6 15.6Z"/>',
    bulb: '<path d="M7.2 14.2h5.6 M7.8 16.6h4.4 M10 2.6a5 5 0 0 0-3 9c.6.5 1 1.2 1 2v.6h4v-.6c0-.8.4-1.5 1-2a5 5 0 0 0-3-9Z"/>'
  };
  window.QUEST_ICON_SVG = function (k) { return '<svg viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (ICON[k] || '') + '</svg>'; };

  function get(path) { return path.split('.').reduce(function (o, k) { return o == null ? o : o[k]; }, Q); }
  function fmt(v) { return typeof v === 'number' ? v.toLocaleString('en-US') : String(v); }
  var reduce = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  var HEX = 'M12 1.6 21 6.8v10.4L12 22.4 3 17.2V6.8z';

  // ---- the board's open slots (the flyer's .seat): who wins each ("nepis could be yours, ale ze nejvice points vyhrava")
  var BY = ['most points', '2nd most points', '3rd most points'];
  document.querySelectorAll('[data-seats]').forEach(function (host) {
    host.innerHTML = Q.prizes.map(function (_, i) {
      return '<div class="seat p' + (i + 1) + '"><span class="rk">' + (i + 1) + '</span>' +
        '<span class="who"><b>Open slot</b><span>' + BY[i] + '</span></span>' +
        '<span class="pay"><b data-figure="prizes.' + i + '"></b><span data-figure="unit"></span></span></div>';
    }).join('');
  });
  document.querySelectorAll('[data-figure]').forEach(function (el) { el.textContent = fmt(get(el.dataset.figure)); });
  document.querySelectorAll('[data-link]').forEach(function (a) { a.href = Q.links[a.dataset.link]; a.target = '_blank'; a.rel = 'noopener'; });

  // ---- the rail: Capital Maximizer's tabs in a capsule of crystal, a hexagon a step, the step you are on lit
  var rail = document.getElementById('rail');
  rail.innerHTML = Q.steps.map(function (s, i) {
    return '<a data-step="' + (i + 1) + '" href="#s' + (i + 1) + '"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="' + HEX + '"/></svg>' +
      '<span class="lab"><em>' + s.n + '</em>' + s.label + '</span><span class="sh">' + s.short + '</span></a>';
  }).join('') + '<span class="fill"></span>';
  var steps = [].slice.call(rail.querySelectorAll('a')), fill = rail.querySelector('.fill');
  document.querySelectorAll('#rail a').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      var sec = document.getElementById(a.getAttribute('href').slice(1));
      window.scrollTo({ top: sec.getBoundingClientRect().top + scrollY - innerHeight * 0.06, behavior: reduce ? 'auto' : 'smooth' });
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

  // ---- on every scroll: which step is on screen, the rail's lit tab and the light under it
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
      var on = steps[active - 1];
      if (on) { fill.style.opacity = 1; fill.style.left = on.offsetLeft + 'px'; fill.style.width = on.offsetWidth + 'px'; }
      else fill.style.opacity = 0;
    }
  }
  var queued = false;
  window.addEventListener('scroll', function () { if (!queued) { queued = true; requestAnimationFrame(function () { queued = false; frame(); }); } }, { passive: true });
  window.addEventListener('resize', function () { frame(true); });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { frame(true); });
  frame();
  S.ready = true;
})();
