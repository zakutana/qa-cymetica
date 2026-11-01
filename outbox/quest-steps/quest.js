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
    // the live builder's pre-build (builder.js PRE, data.js TEMPLATES, read again 2026-10-31): four departments (Cymetica
    // QA, Development, Quant Lab, Trading desk), two AI agents each, and a supervisor in Operations: nine agents; NEXUS
    // in Command runs them. Marketing is a fifth the owner can add (ET-32484), not in the pre-build
    hq: { departments: 4, agents: 9 },
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
    // his five, in his order of 2026-10-31 ("po build produkt bude market it ... a az pak bude breed your agent")
    steps: [
      { n: '01', label: 'Start', short: 'Start' },
      { n: '02', label: 'Build', short: 'Build' },
      { n: '03', label: 'Market', short: 'Market' },
      { n: '04', label: 'Hero agent', short: 'Agent' },
      { n: '05', label: 'Climb', short: 'Climb' }
    ],
    // the last step's leaderboard: our Universe mock's sample companies (uv-data.js, their station as their mark) and
    // their points, examples; yours climbs it
    board: [['Giga Fund', 1405, 'station-vault-red'], ['Bull Club', 1311, 'station-pyramid-red'], ['Sigma Collective', 976, 'station-tower-blue'],
            ['Quasar Fund', 812, 'station-dome-green'], ['Vector Trading', 655, 'station-tower-cyan']],
    you: { name: 'Your company', from: 420, to: 1520, mark: 'you' },
    // every product a step names links to it, lit in the words ("vsude v textech musis zvyraznovat veci kterym das
    // link odkaz primo", 2026-10-31: until then the only links were the two doors at the end); each answered 200
    links: {
      builder: 'https://cymetica.com/company/app/builder',
      universe: 'https://cymetica.com/company/app#universe',
      bib: 'https://cymetica.com/build-it-better',
      promo: 'https://cymetica.com/promo-market',
      casino: 'https://cymetica.com/agent-casino',
      gem: 'https://cymetica.com/gem-screener',
      farmer: 'https://cymetica.com/airdrop-farmer'
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
  // each department's little agent ("dej jim ikonky tech agentu malinke misto tech svetilek. staci 1 ikonka na
  // department", 2026-11-01): the live office's own astronaut (cymetica.com/static/company/office.js avatar(), read
  // 2026-11-01), its helmet and visor the department's role's (its ROLE2D)
  var ROLE2D = { manager: ['#bccad6'], developer: ['#1c9cb4'], lab_scientist: ['#5aa888'], trader: ['#c49035', '#6a4a14'], qa_tester: ['#c4532f', '#160a08'] };
  function shade(hex, k) {
    var n = parseInt(hex.slice(1), 16), to = k > 0 ? 255 : 0, a = Math.abs(k);
    return 'rgb(' + [n >> 16, (n >> 8) & 255, n & 255].map(function (c) { return Math.round(c + (to - c) * a); }).join(',') + ')';
  }
  document.querySelectorAll('.dp[data-role]').forEach(function (d) {
    var role = d.dataset.role, c = ROLE2D[role][0], visor = ROLE2D[role][1] || '#0e2c56', suit2 = '#b3c1cf', pack = '#4a5c70';
    d.insertAdjacentHTML('afterbegin', '<svg viewBox="-9 -29 18 30" aria-hidden="true"><defs>' +
      '<linearGradient id="dp-suit-' + role + '" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#f4f8fb"/><stop offset="1" stop-color="#b9c7d4"/></linearGradient>' +
      '<radialGradient id="dp-helmet-' + role + '" cx=".36" cy=".3" r=".78"><stop offset="0" stop-color="' + shade(c, 0.45) + '"/><stop offset=".55" stop-color="' + c + '"/><stop offset="1" stop-color="' + shade(c, -0.45) + '"/></radialGradient></defs>' +
      '<rect x="-4.3" y="-8.6" width="3.6" height="8" rx="1.6" fill="' + suit2 + '"/><rect x=".7" y="-8.6" width="3.6" height="8" rx="1.6" fill="' + suit2 + '"/>' +
      '<rect x="-4.7" y="-2.3" width="4.1" height="2.5" rx="1" fill="' + pack + '"/><rect x=".6" y="-2.3" width="4.1" height="2.5" rx="1" fill="' + pack + '"/>' +
      '<rect x="-3.8" y="-18.8" width="10.2" height="9.8" rx="2.6" fill="' + pack + '"/>' +
      '<rect x="-7.7" y="-16.4" width="3.4" height="9.2" rx="1.7" fill="url(#dp-suit-' + role + ')"/><rect x="4.3" y="-16.4" width="3.4" height="9.2" rx="1.7" fill="' + suit2 + '"/>' +
      '<rect x="-5.4" y="-17.6" width="10.8" height="10.8" rx="4.2" fill="url(#dp-suit-' + role + ')"/>' +
      '<rect x="-2.9" y="-14.7" width="5.8" height="3.1" rx=".9" fill="' + pack + '"/><circle cx="1.3" cy="-13.15" r=".8" fill="#38f2b8" opacity=".6"/>' +
      '<ellipse cx="0" cy="-17.4" rx="4.5" ry="1.45" fill="' + pack + '"/>' +
      '<circle cx="0" cy="-22.2" r="5.7" fill="url(#dp-helmet-' + role + ')"/>' +
      '<ellipse cx="-1.2" cy="-21.8" rx="3.9" ry="2.8" fill="' + visor + '"/><ellipse cx="-2.5" cy="-22.8" rx="1.3" ry=".75" fill="#cfe6ff" opacity=".75"/></svg>');
  });

  // ---- the rail: the quest's track: a round light a step with its number in it (no hexagon: "nelibi se mi ten
  // hexagon co pouzivas v logu a stepech"), the lines between them filling as you read down the page (a spark at the
  // fill's front), the step you are on lit
  var rail = document.getElementById('rail');
  rail.innerHTML = Q.steps.map(function (s, i) {
    return '<a data-step="' + (i + 1) + '" href="#s' + (i + 1) + '"><span class="nd"><em>' + (i + 1) + '</em></span>' +
      '<span class="lab">' + s.label + '</span><span class="sh">' + s.short + '</span></a>';
  }).join('<i><b></b></i>');
  var steps = [].slice.call(rail.querySelectorAll('a')), lines = [].slice.call(rail.querySelectorAll('i'));
  document.querySelectorAll('#rail a, .btn-how').forEach(function (a) {
    a.addEventListener('click', function (e) {
      e.preventDefault();
      var sec = document.getElementById(a.getAttribute('href').slice(1));
      if (!sec) return;
      var off = sec.id === 's2' ? 0 : innerHeight * 0.04;
      window.scrollTo({ top: sec.getBoundingClientRect().top + scrollY - off, behavior: reduce ? 'auto' : 'smooth' });
    });
  });

  // ---- subtle 3D specular parallax on the hero prize board
  var heroBoard = document.querySelector('#hero .board'), heroSec = document.getElementById('hero');
  if (heroBoard && heroSec && !reduce) {
    heroSec.addEventListener('pointermove', function (e) {
      if (innerWidth <= 900) return;
      var nx = (e.clientX / innerWidth - 0.5) * 2, ny = (e.clientY / innerHeight - 0.5) * 2;
      heroBoard.style.setProperty('--ry', (-12 + nx * 2.8).toFixed(2) + 'deg');
      heroBoard.style.setProperty('--rx', (2.6 - ny * 2.2).toFixed(2) + 'deg');
    }, { passive: true });
    heroSec.addEventListener('pointerleave', function () {
      heroBoard.style.removeProperty('--ry');
      heroBoard.style.removeProperty('--rx');
    });
  }

  // ---- a step rises in the first time it comes on screen
  var rv = [].slice.call(document.querySelectorAll('.rv'));
  if (reduce || !('IntersectionObserver' in window)) rv.forEach(function (e) { e.classList.add('in'); });
  else {
    var io = new IntersectionObserver(function (es) {
      es.forEach(function (e) { if (e.isIntersecting) { e.target.classList.add('in'); io.unobserve(e.target); } });
    }, { rootMargin: '0px 0px -5% 0px' });
    rv.forEach(function (e) { io.observe(e); });
  }

  // ---- on every scroll: which step is on screen, the rail's lit tab and the light under it
  var sections = [].slice.call(document.querySelectorAll('section[data-step]'));
  var stepSecs = Q.steps.map(function (_, i) { return document.getElementById('s' + (i + 1)); });
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
    }
    // the line from step k to step k + 1 fills as the middle of the window goes from one's top to the next one's
    var tops = stepSecs.map(function (s) { return s.getBoundingClientRect().top; });
    lines.forEach(function (l, i) {
      var p = (mid - tops[i]) / (tops[i + 1] - tops[i]); p = p < 0 ? 0 : p > 1 ? 1 : p;
      l.firstChild.style.width = (p * 100).toFixed(1) + '%';
      l.classList.toggle('run', p > 0 && p < 1);
    });
  }
  var queued = false;
  window.addEventListener('scroll', function () { if (!queued) { queued = true; requestAnimationFrame(function () { queued = false; frame(); }); } }, { passive: true });
  window.addEventListener('resize', function () { frame(true); });
  frame();
  S.ready = true;
})();
