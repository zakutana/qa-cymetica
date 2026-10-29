/* Airdrop Farmer (ET-32463): the amount, the farm from above, every farm hottest first, and Live farms.
 * Data: GET /api/v1/airdrop-farm/farms (the gated list with heat), /plan (the signed-in user's plan, their farm wallet
 * and every supported coin their own wallets hold on every funding network, valued), /status (the farm wallet).
 * START FARMING starts the farm wallet itself through POST /deploy (the user's own on-chain coins, any supported
 * coin, Solana included) or POST /open-direct (coins sent to it); the plan then sits beside it: a farm with a reviewed
 * deposit route is funded from the farm wallet's own USDC (status deposited), every other farm says why it is not.
 * Farm names and logos come from outside: always escaped. Addresses are shown in full. */
(function () {
  'use strict';
  var API = '/api/v1/airdrop-farm';
  var H_DAYS = 180, E = 0.7, FIX = 5;
  var $ = function (s) { return document.querySelector(s); };
  var esc = function (s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); };
  var fmt = function (n) { return Math.round(n || 0).toLocaleString('en-US'); };
  var usd = function (n) { return '$' + fmt(n); };
  var r10 = function (n) { return Math.round(n / 10) * 10; };
  var money = function (n) { return n < 100 ? '$' + Math.round(n) : usd(r10(n)); };
  var rng = function (lo, hi) { return Math.round(lo) === Math.round(hi) ? money(lo) : money(lo) + ' – ' + money(hi); };
  var BOLT = '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M13.5 2 4 14h6.5L9.5 22 20 9.5h-6.6z"/></svg>';
  var LOGO = '<svg><use href="#aflogo"/></svg>';

  function headers(json) {
    var h = json ? { 'Content-Type': 'application/json' } : {};
    try {
      var k = localStorage.getItem('api_key'); if (k) h['X-API-Key'] = k;
      var t = localStorage.getItem('accessToken') || localStorage.getItem('access_token'); if (t) h['Authorization'] = 'Bearer ' + t;
    } catch (e) { /* cookies still apply */ }
    return h;
  }
  function api(method, path, body) {
    return fetch(API + path, { method: method, credentials: 'same-origin', headers: headers(body !== undefined), body: body !== undefined ? JSON.stringify(body) : undefined })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (d) { return { ok: r.ok, status: r.status, d: d }; }); })
      .catch(function () { return { ok: false, status: 0, d: {} }; });
  }
  function plain(res) {
    if (!res || res.status === 0) return 'Network problem. Please try again.';
    if (res.status === 401) return 'Sign in to continue.';
    var m = res.d && res.d.detail;
    if (Array.isArray(m) && m[0] && m[0].msg) m = m[0].msg;
    if (typeof m !== 'string' || m.length > 260 || /traceback|exception|error:|sqlalchemy|psycopg|https?:\/\/|\brpc\b|api.?key/i.test(m)) return 'Something went wrong. Please try again.';
    return m;
  }
  function toast(t) {
    var dm = document.getElementById('afm-dlgmsg');
    if (dm) { dm.textContent = t; dm.style.display = 'block'; return; }   /* dialog open: the message shows INSIDE it */
    var el = $('#afm-toast'); el.innerHTML = '<div class="toast">' + esc(t) + '</div>';
    clearTimeout(toast.t); toast.t = setTimeout(function () { el.innerHTML = ''; }, 2800);
  }

  /* ---------- state ---------- */
  var Q = new URLSearchParams(location.search);
  var TAB = Q.get('tab') === 'live' ? 'live' : 'farms';
  var SIGNED = $('#adf').getAttribute('data-signed-in') === '1' || !!(window.hasSession && window.hasSession());
  // expire76 2026-10-24: FARMS = only the farms the agent runs end to end (START FARMING); SOON = every other farm
  var FARMS = [], SOON = [], BY = {}, META = { count: 0, available: true, note: '' };
  var S = { budget: 1000, balance: null, cap: 2000, amt: {}, on: {}, last: {}, custom: false, q: '', shown: 12,
    byChain: [], unread: [], coinsHeld: [], coinsSupported: 0, netsRead: 0, minDeploy: 20, minDirect: 20, open: true,
    farmChains: [], mode: 'wallet' };
  var PLAN = null, LEGACY = null, REC = {};

  /* ---------- the maths (the API's formulas: farms.estimate / farms.best_split) ---------- */
  function est(f, x) {
    if (f.lo == null || f.hi == null || !f.ref || x <= 0) return null;
    var k = Math.pow(x / f.ref, E);
    return { lo: f.lo * k, hi: f.hi * k };
  }
  function midAt(f, x) { var e = est(f, x); return e ? (e.lo + e.hi) / 2 : 0; }
  function eff(f) { return f.lo == null ? -1 : midAt(f, f.ref) / f.ref - (f.cost_per_1000 || 0) / 1000; }
  // value rank: estimated farms by what a dollar earns, then free ones, then the rest (where money moves between farms)
  function rank(f) { return f.lo != null ? 1 - eff(f) : f.free ? 2 : 3; }
  // No farm has a points rate we could read: the amount goes evenly to up to five of the hottest farms (a fifth
  // each when five exist; with fewer farms the whole amount is still deployed, split evenly, never left idle),
  // never under $50 a farm (fewer farms below $250). It is a split by heat, not by an estimate, and the panel says so.
  function evenSplit(B) {
    var hot = FARMS.filter(function (f) { return !f.free; }), n = Math.min(5, hot.length, Math.floor(B / 50));
    var a = {}, each = n ? Math.floor(B / n / 10) * 10 : 0;
    if (each <= 0) return a;
    hot.slice(0, n).forEach(function (f) { a[f.id] = each; });
    return a;
  }
  var byHeat = function () { return !FARMS.some(function (f) { return f.lo != null && !f.free; }); };
  function recommend(B) {
    var a = {}, ok = FARMS.filter(function (f) { return f.lo != null && !f.free; });
    ok.forEach(function (f) { a[f.id] = 0; });
    if (B <= 0) return {};
    if (!ok.length) return evenSplit(B);
    // the same rule as farms.best_split: a farm's cap is 20% of B with five or more farms, else B/n; a farm is entered
    // when the whole stake it may hold beats its entry gas; the split stops when no next dollar earns anything net
    var step = Math.max(10, Math.ceil(B / 500 / 10) * 10), t0 = Math.max(step, Math.round(B * 0.05 / 10) * 10), left = B;
    var cap = B * Math.max(0.2, 1 / ok.length);
    while (left >= step) {
      var best = null, bm = 0, add = 0;
      ok.forEach(function (f) {
        var have = a[f.id], d = have ? step : t0;
        if (d > left || have + d > cap + 1e-9) return;
        var cpk = (f.cost_per_1000 || 0) / 1000, m;
        if (have) m = (midAt(f, have + d) - midAt(f, have)) / d - cpk;
        else { var room = Math.min(cap, left); m = (midAt(f, room) - (f.gas || FIX)) / room - cpk; }
        if (m > bm) { bm = m; best = f; add = d; }
      });
      if (!best) break;
      a[best.id] += add; left -= add;
    }
    Object.keys(a).forEach(function (k) { a[k] = r10(a[k]); if (!a[k]) delete a[k]; });
    return a;
  }
  var rec = function (f) { return f.free ? 0 : (REC[f.id] || 0); };
  var amtOf = function (id) { return S.amt[id] || 0; };
  var planSum = function () { return FARMS.reduce(function (s, f) { return s + (S.on[f.id] && !f.free ? amtOf(f.id) : 0); }, 0); };
  // The amount stops at min(plan cap, what the wallets hold) once the balance is read (ET-32549 item 2): MAX and
  // every farm field never promise more than the user can start with. Before the balance is read, the plan cap.
  var maxAmt = function () { return Math.floor(S.balance != null ? Math.min(S.cap, Math.max(0, S.balance)) : S.cap); };
  var maxWhy = function (most) { return S.balance != null && S.balance < S.cap ? 'Your wallets hold ' + usd(most) + ' (plan cap ' + usd(S.cap) + ')' : 'The plan cap is ' + usd(most); };
  function applyBest() {
    FARMS.forEach(function (f) { var r = rec(f); S.amt[f.id] = f.free ? 0 : r; S.on[f.id] = f.free ? true : r > 0; });
    S.custom = false;
  }
  function planTotals() {
    var lo = 0, hi = 0, n = 0, a = 0, c = 0, any = false;
    FARMS.forEach(function (f) {
      if (!S.on[f.id]) return;
      var x = f.free ? 0 : amtOf(f.id), e = est(f, x);
      n++; a += x;
      if (!f.free && x > 0) c += (f.gas || FIX) + (f.cost_per_1000 || 0) * x / 1000;
      if (e) { lo += r10(e.lo); hi += r10(e.hi); any = true; }
    });
    return { lo: lo, hi: hi, n: n, a: a, c: Math.round(c), any: any };
  }

  /* ---------- heat, EARLY ---------- */
  var FLAME = 'M12 2.2c1.1 3.4-1.2 5.2-2.5 7C8.1 11.1 7 12.9 7 15.1a5 5 0 0 0 10 0c0-2.6-1.4-4.3-2.4-5.5.1 1.6-.5 2.7-1.6 3.3.3-3.7-.9-7.5-1-10.7z';
  var FLAME_IN = 'M12 13.2c.8 1.2 2 2 2 3.4a2 2 0 0 1-4 0c0-1.1.9-1.9 2-3.4z';
  var SPROUT = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 21v-8"/><path d="M12 13c-4 0-6-2.5-6-6 4 0 6 2.5 6 6z"/><path d="M12 11c0-3.5 2.2-6 6-6 0 3.5-2.2 6-6 6z"/></svg>';
  var tier = function (h) { return h >= 85 ? 'h3' : h >= 60 ? 'h2' : h >= 35 ? 'h1' : 'h0'; };
  function flameSvg(h) {
    var t = tier(h);
    if (t === 'h0') return '<svg viewBox="5.5 1.5 13 19.5"><path d="' + FLAME + '" fill="none" stroke="#7e90a1" stroke-width="1.4"/></svg>';
    var fill = t === 'h3' ? 'url(#afflame)' : t === 'h2' ? '#3ddc8a' : '#00cfff';
    return '<svg viewBox="5.5 1.5 13 19.5"><path d="' + FLAME + '" fill="' + fill + '" fill-opacity="' + (t === 'h1' ? 0.75 : 1) + '"/>' + (t === 'h3' ? '<path d="' + FLAME_IN + '" fill="#e9eff5" fill-opacity=".85"/>' : '') + '</svg>';
  }
  // Heat is shown only when the engine has ranked enough farms (ET-32549 item 6): one hot farm and twenty zeros is no order.
  // Heat is an ABSOLUTE 0-100 (talk + money + momentum, tooltip shows each part); a farm none of it can be read for says "no data".
  var heatOK = function () { return FARMS.some(function (f) { return f.heat != null; }); };
  function heatHTML(f, mini) {
    if (!heatOK()) return '';
    if (f.heat == null) return '<span class="heat h0 nodata' + (mini ? ' mini' : '') + '" title="' + esc(f.heat_tip || 'No data: nothing about this farm could be read from the channels we follow.') + '"><b class="num">no data</b></span>';
    var h = Math.max(0, Math.min(100, Math.round(+f.heat)));
    return '<span class="heat ' + tier(h) + (mini ? ' mini' : '') + '" title="' + esc(f.heat_tip || ('Heat ' + h + '/100')) + '">' + flameSvg(h) + '<b class="num">' + h + '</b></span>';
  }
  function routeHTML(f) {
    var r = f.route || {};
    // ET-32679: say plainly whether the agent runs this farm for you today
    if (r.state === 'ready') return '<span class="chip g" title="' + esc(r.reason || '') + '">AGENT RUNS IT</span>';
    // CentCom 32706: free task / testnet farms are not automated; the user does the tasks
    if (r.state === 'tasks') return '<span class="rt" title="' + esc(r.reason || '') + '">manual: you do the tasks</span>';
    return '<span class="rt" title="' + esc(r.reason || 'The agent does not run this farm yet') + '">not run by the agent yet</span>';
  }
  function earlyHTML(f) { return f.early ? '<span class="early" title="Few people talk about ' + esc(f.name) + ' yet; Cymetica\'s sentiment engine sees potential">' + SPROUT + 'EARLY</span>' : ''; }
  // ET-32686: the chip says where it came from and when the farm was last checked
  function chipTip(f) {
    var c = f.checks || {}, out = [];
    if (c.checked_at) out.push('Checked ' + String(c.checked_at).slice(0, 10) + '.');
    if (c.programme_url) out.push('Programme read on ' + c.programme_url + '.');
    if (c.market) out.push('Market: ' + c.market + '.');
    (f.evidence || []).forEach(function (e) { if (e.kind === 'news' && e.t) out.push('News: ' + e.t); });
    return out.join(' ') || 'Read from the farm\'s own page';
  }
  var webUrl = function (u) { u = String(u || ''); return /^https?:\/\/[^\s"'<>]+$/i.test(u) ? u : ''; };
  function logo(f) { return '<span class="logo">' + esc(f.ini || '') + (webUrl(f.icon) ? '<img src="' + esc(webUrl(f.icon)) + '" alt="" loading="lazy" onerror="this.remove()">' : '') + '</span>'; }

  /* ---------- the farm from above ---------- */
  function plantTop(f, x, y, ready) {
    var r = 17, s = '';
    if (ready) s += '<circle class="halo" cx="' + x + '" cy="' + y + '" r="' + (r + 10) + '" fill="#3ddc8a" fill-opacity=".4" filter="url(#afsoft)"/>';
    s += '<circle cx="' + x + '" cy="' + y + '" r="' + (r + 2.5) + '" fill="#070b10" stroke="' + (ready ? '#3ddc8a' : '#00cfff') + '" stroke-opacity="' + (ready ? 1 : 0.55) + '" stroke-width="2"/>';
    s += '<text x="' + x + '" y="' + (y + 4) + '" text-anchor="middle" fill="#3ddc8a" font-size="11" font-weight="800" font-family="JetBrains Mono,monospace">' + esc(f.ini) + '</text>';
    if (webUrl(f.icon)) s += '<image href="' + esc(webUrl(f.icon)) + '" x="' + (x - r) + '" y="' + (y - r) + '" width="' + 2 * r + '" height="' + 2 * r + '" clip-path="url(#afdisc)"/>';
    if (ready) s += '<g transform="translate(' + x + ' ' + (y - r - 16) + ')"><rect x="-32" y="-10" width="64" height="19" rx="9.5" fill="#3ddc8a"/><text y="3.5" text-anchor="middle" fill="#070b10" font-size="9.5" font-weight="800" font-family="Inter,sans-serif" letter-spacing="1">HARVEST</text></g>';
    if (f.heat >= 85) s += '<g transform="translate(' + (x + 13) + ' ' + (y - 15) + ')"><circle r="9" fill="#070b10" stroke="#3ddc8a" stroke-width="1.5"/><path d="' + FLAME + '" fill="url(#afflame)" transform="translate(-6.5 -7) scale(.55)"/></g>';
    else if (f.early) s += '<g transform="translate(' + (x + 13) + ' ' + (y - 15) + ')"><circle r="9" fill="#070b10" stroke="#00cfff" stroke-width="1.5" stroke-dasharray="2.5 2"/><g transform="translate(-6 -6.5) scale(.5)" stroke="#00cfff" stroke-width="2.6" fill="none" stroke-linecap="round"><path d="M12 21v-8"/><path d="M12 13c-4 0-6-2.5-6-6 4 0 6 2.5 6 6z"/><path d="M12 11c0-3.5 2.2-6 6-6 0 3.5-2.2 6-6 6z"/></g></g>';
    return s;
  }
  // items: [{f, v, ready}] ; live: pillars as tall as what each farm earned (6 + sqrt * 144), else as the USDC (16 + sqrt * 134)
  function fieldSvg(items, live) {
    var tw = 116, th = 58, pw = 26, ph = 13, hmax = 150;
    items = items.slice().sort(function (a, b) { return b.v - a.v || rank(a.f) - rank(b.f); });
    var cols = 4, n = Math.min(items.length, 16), rows = Math.max(3, Math.ceil(n / cols)), plots = [], r, c;
    for (r = 0; r < rows; r++) for (c = 0; c < cols; c++) plots.push([c, r]);
    plots.sort(function (p, q) { return (p[0] + p[1]) - (q[0] + q[1]) || p[0] - q[0]; });
    var ox = rows * tw / 2 + 24, oy = hmax + 70, W = (cols + rows) * tw / 2 + 48, Hh = oy + (cols + rows) * th / 2 + 18;
    var at = function (cc, rr) { return [ox + (cc - rr) * tw / 2, oy + (cc + rr) * th / 2]; };
    var vmax = Math.max.apply(null, [1e-9].concat(items.slice(0, n).map(function (i) { return i.v; })));
    var s = '<ellipse cx="' + W / 2 + '" cy="' + (oy + (cols + rows) * th / 4) + '" rx="' + W * 0.5 + '" ry="' + (cols + rows) * th / 2.6 + '" fill="url(#afground)"/>';
    plots.forEach(function (p) {
      var xy = at(p[0], p[1]), x = xy[0], y = xy[1];
      s += '<polygon points="' + x + ',' + (y - th / 2) + ' ' + (x + tw / 2) + ',' + y + ' ' + x + ',' + (y + th / 2) + ' ' + (x - tw / 2) + ',' + y + '" fill="#0d141c" fill-opacity=".92" stroke="#3ddc8a" stroke-opacity=".18"/>' +
        '<polygon points="' + x + ',' + (y - th / 4) + ' ' + (x + tw / 4) + ',' + y + ' ' + x + ',' + (y + th / 4) + ' ' + (x - tw / 4) + ',' + y + '" fill="none" stroke="#3ddc8a" stroke-opacity=".07"/>';
    });
    plots.slice(0, n).forEach(function (p, k) {
      var it = items[k], f = it.f, xy = at(p[0], p[1]), x = xy[0], y = xy[1];
      var base = live ? 6 : 16, h = !live && f.free ? 16 : base + Math.sqrt(it.v / vmax) * (hmax - base);
      if (!(it.v > 0) && !f.free) h = base;
      var side = f.free ? 'affl' : 'afpl', top = f.free ? '#00cfff' : '#3ddc8a';
      s += '<g class="pillar' + (it.ready ? ' ready' : '') + '"><title>' + esc(f.name) + ': ' + (live ? money(it.v) + ' earned' : f.free ? 'free' : usd(it.v)) + '</title>' +
        '<ellipse cx="' + x + '" cy="' + (y + 2) + '" rx="' + pw * 1.6 + '" ry="' + ph * 1.6 + '" fill="' + top + '" fill-opacity=".12" filter="url(#afsoft)"/>' +
        '<polygon points="' + (x - pw) + ',' + y + ' ' + x + ',' + (y + ph) + ' ' + x + ',' + (y + ph - h) + ' ' + (x - pw) + ',' + (y - h) + '" fill="url(#' + side + ')"/>' +
        '<polygon points="' + x + ',' + (y + ph) + ' ' + (x + pw) + ',' + y + ' ' + (x + pw) + ',' + (y - h) + ' ' + x + ',' + (y + ph - h) + '" fill="url(#afpr)"/>' +
        '<polygon points="' + x + ',' + (y - ph - h) + ' ' + (x + pw) + ',' + (y - h) + ' ' + x + ',' + (y + ph - h) + ' ' + (x - pw) + ',' + (y - h) + '" fill="' + top + '" filter="url(#afsoft)"/>' +
        '<line x1="' + x + '" y1="' + (y - h - ph) + '" x2="' + x + '" y2="' + (y - h - 12) + '" stroke="' + top + '" stroke-opacity=".5" stroke-dasharray="2 3"/>' +
        plantTop(f, x, y - h - 32, it.ready) + '</g>';
    });
    if (items.length > n) s += '<text x="' + (W - 16) + '" y="' + (Hh - 6) + '" text-anchor="end" fill="#7e90a1" font-size="12" font-family="JetBrains Mono,monospace">+' + (items.length - n) + ' more farms</text>';
    return '<svg class="field" viewBox="0 0 ' + W + ' ' + Hh + '" role="img" aria-label="Your farm from above">' + s + '</svg>';
  }

  /* ---------- header ---------- */
  function liveCount() { return PLAN ? PLAN.farms.length : 0; }
  var RUNNING = ['pending_funding', 'funding', 'active', 'paused', 'unwinding'];
  var running = function () { return !!(LEGACY && RUNNING.indexOf(LEGACY.status) >= 0); };
  function header() {
    var n = liveCount();
    // FARMING only when the farm wallet really runs; a saved plan alone moves nothing
    var status = running() ? '<span class="dot"></span><b>' + (LEGACY.status === 'unwinding' ? 'BRINGING FUNDS HOME' : LEGACY.status === 'pending_funding' && LEGACY.funding_mode === 'direct' ? 'WAITING FOR YOUR DEPOSIT' : 'FARMING') + '</b>' + /* MOCK PATCH: no "farm wallet"; what is in and what it is worth, in green */ (+LEGACY.deployed_usdc > 0 ? ' · <b>' + usd(+LEGACY.deployed_usdc) + '</b> in' + (LEGACY.farm_value_usd ? ' · <b>' + usd(+LEGACY.farm_value_usd) + '</b> now' : '') : '')
      : n ? '<span class="dot idle"></span><b>PLAN SAVED</b> · ' + n + ' farm' + (n > 1 ? 's' : '') + ' on the plan' : '<span class="dot idle"></span><b>NOT FARMING</b>';
    return '<header class="app"><a class="brand" href="/airdrop-farmer">' + LOGO + '<div class="w"><span>AIRDROP</span><b>FARMER</b></div></a>' +
      '<nav class="tabs" aria-label="Airdrop Farmer"><a data-tab="farms" class="' + (TAB === 'farms' ? 'on' : '') + '">Farms</a><a data-tab="live" class="' + (TAB === 'live' ? 'on' : '') + '">Live farms' + (n ? ' <i>' + n + '</i>' : '') + '</a></nav>' +
      '<div class="status" id="hstatus">' + status + '</div></header>';
  }

  /* ---------- Farms tab ---------- */
  var toPos = function (v) { return Math.round(1000 * Math.sqrt(Math.min(1, Math.max(0, v) / Math.max(1, maxAmt())))); };
  var fromPos = function (p) { var v = maxAmt() * Math.pow(p / 1000, 2); return v < 1000 ? Math.round(v / 10) * 10 : v < 5000 ? Math.round(v / 50) * 50 : Math.round(v / 100) * 100; };
  var along = function (v) { return 'calc(11px + (100% - 22px) * ' + toPos(v) / 1000 + ')'; };

  // where the balance sits: one line per network from the user's own wallets only, every coin on request
  function byChainHTML() {
    var rows = S.byChain || [];
    if (!rows.length && !S.unread.length) return '';
    var line = rows.length ? '<div class="bal bychain">' + rows.map(function (r) {
      var short = r.fundable_usdc < (r.usd != null ? r.usd : r.usdc);
      return '<span title="' + esc(r.wallets.map(function (w) { return w.label + ' ' + w.address + (w.note ? ' (' + w.note + ')' : ''); }).join('\n')) + '">' +
        esc(r.chain) + ' <b>$' + (+(r.usd != null ? r.usd : r.usdc)).toFixed(2) + '</b>' + (short ? ' <small>(' + '$' + (+r.fundable_usdc).toFixed(2) + ' can move)</small>' : '') + '</span>';
    }).join(' · ') + '</div>' : '';
    var coins = [];
    rows.forEach(function (r) {
      (r.wallets || []).forEach(function (w) {
        (w.coins || []).forEach(function (c) {
          coins.push('<div class="ln"><span>' + esc(r.chain) + '</span><span>' + esc(c.symbol) + ' <small>' + esc(String(+(+c.amount).toFixed(6))) + '</small></span><span class="num">' + (c.usd != null ? '$' + (+c.usd).toFixed(2) + (c.gas_kept_usd ? ' <small>+ $' + (+c.gas_kept_usd).toFixed(2) + ' kept for fees</small>' : '') : '<small>not priced</small>') + '</span></div>');
        });
      });
    });
    var unread = S.unread.length ? '<div class="ln"><span>' + esc(S.unread.join(', ')) + '</span><span><small>could not be read just now</small></span><span></span></div>' : '';
    return line + '<details class="hold"><summary>See every coin, every network ▾</summary>' + coins.join('') + unread +
      '<div class="ln fineln"><span>Any of ' + fmt(S.coinsSupported || 0) + ' supported coins on ' + fmt(S.netsRead || rows.length) + ' networks can fund a farm · the gas coin above a small reserve counts too · other coins become USDC inside your farm wallet</span></div></details>';
  }
  function balanceLine() {
    if (S.balance == null) return SIGNED ? 'Your wallets could not be read just now' : '<a href="/login?next=/airdrop-farmer">Sign in</a> to farm with your own coins';
    // MOCK PATCH: one number, the USDC the user can farm with, summed over every wallet and network
    return '<b id="bal">' + usd(S.balance) + ' USDC</b>';
  }
  function farmsView() {
    return '<div class="wrap">' + header() +
      '<section class="hero"><div>' +
      '<div class="pill"><span class="dot"></span>' + fmt(FARMS.length) + ' RUN BY THE AGENT · ' + fmt(SOON.length) + ' COMING SOON</div>' +
      '<h1>Bring USDC, or nothing.<br>One click. Every airdrop.<br><em>Cymetica does the rest.</em></h1>' + /* MOCK PATCH: the operator's headline */
      '<div class="sub">Chatbots explain airdrops. <b>Cymetica farms them.</b></div>' +
      '<div class="glass glow plan">' +
      '<div class="top"><span class="cap">HOW MUCH?</span><span id="bestslot"></span></div>' +
      '<div class="bigin"><input id="budget" inputmode="decimal" autocomplete="off" value="' + fmt(S.budget) + '" aria-label="Amount to farm, in dollars"><span class="token"><i>$</i>USD</span><button class="max" data-act="max" type="button">MAX</button></div>' +
      '<div class="bal">Balance ' + balanceLine() + '</div>' + /* MOCK PATCH: no per-network lines, no coin list */
      '<div class="you"><small>YOU FARM ≈</small><b id="kest" class="num"></b><span id="kline"></span></div>' +
      '<button class="go" data-act="start" id="gobtn" type="button"></button>' + /* MOCK PATCH: the fine line goes, the Start dialog shows the costs */
      '</div></div>' +
      '<div class="fieldwrap"><div id="field"></div><div class="fcap">Your farm from above: one pillar per farm, as tall as the dollars you plant.</div></div>' +
      '</section>' +
      '<div class="sechead"><div><h2>AGENT RUNS IT <small style="font-weight:500;color:var(--text-3);font-size:13px">' + fmt(FARMS.length) + ' farm' + (FARMS.length === 1 ? '' : 's') + ' the agent runs end to end from your farm wallet</small></h2><p>' + (heatOK() ? 'Heat is 0-100 from talk (Telegram, Discord, X, Reddit, headlines, news), money in the farm and momentum; hover a number for its parts. ' : 'Heat shows once the engine has read the channels. ') + 'Estimates are ranges from comparable airdrops, labelled as estimates. Drag to plant more or less.</p></div>' +
      '<input id="q" class="search" placeholder="Search farms" value="' + esc(S.q) + '" aria-label="Search farms"></div>' +
      // ET-32463 (expire76): while heat is hidden the whole column goes, header included — FARM starts at the left edge.
      '<div class="glass list' + (heatOK() ? '' : ' noheat') + '"><div class="rowh cols"><div>HEAT</div><div>FARM</div><div>PLANT</div><div>USD</div><div>EST. AIRDROP · 6 MO</div><div style="text-align:right">ON</div></div><div id="list"></div></div>' +
      '<div class="more" id="more"></div>' +
      '<div class="sechead"><div><h2>Coming soon <small style="font-weight:500;color:var(--text-3);font-size:13px">' + fmt(SOON.length) + ' farms the agent does not run yet</small></h2><p>These farms passed the checks, but no runner does their deposits, tasks or claims from your farm wallet yet, so they cannot be started. Each says why.</p></div></div>' +
      '<div class="glass list' + (heatOK() ? '' : ' noheat') + '"><div id="soon"></div></div>' +
      '<p class="gatenote">' + esc(META.note || '') + '</p></div>';
  }
  function visible() {
    var q = S.q.toLowerCase();
    return FARMS.filter(function (f) { return !q || f.name.toLowerCase().indexOf(q) >= 0; });
  }
  function estHTML(f) {
    if (f.free) return '<b class="num">FREE</b><small>no money · no estimate</small>';
    if (f.lo == null) return '<b class="num no">no estimate</b><small>' + esc(f.why || 'no comparable valuation for this farm') + '</small>';
    var a = S.on[f.id] ? amtOf(f.id) : 0, e = est(f, a), tip = esc(f.est_basis || 'An estimate from comparable airdrops, not a promise.');
    // CentCom 32706: a range from comparables is the same for every farm of its kind; it says so
    var avg = f.est_kind === 'category_average';
    if (!e) { var p = rec(f) || f.ref, ep = est(f, p); return '<b class="num dim" title="' + tip + '">' + rng(ep.lo, ep.hi) + '</b><small title="' + tip + '">' + (avg ? 'category average if you plant ' : 'estimate if you plant ') + usd(p) + '</small>'; }
    return '<b class="num" title="' + tip + '">' + rng(e.lo, e.hi) + '</b><small title="' + tip + '">' + (avg ? 'CATEGORY AVERAGE · not this farm\'s own rate' : 'ESTIMATE · airdrop in 6 months') + '</small>';
  }
  function useBestHTML(f) { var r = rec(f); return !f.free && r && !(S.on[f.id] && amtOf(f.id) === r) ? '<button class="usebest" type="button" data-use="' + esc(f.id) + '">best ' + usd(r) + '</button>' : ''; }
  function rowHTML(f) {
    var on = !!S.on[f.id], a = amtOf(f.id), r = rec(f), id = esc(f.id);
    var plant = f.free ? '<span class="freepill">FREE · NO MONEY NEEDED</span>'
      : '<div class="trk"><i class="bar"></i><i class="fil" style="width:' + along(a) + '"></i>' + (r ? '<i class="notch" style="left:' + along(r) + '"><em>' + (byHeat() ? 'SPLIT' : 'BEST') + '</em></i>' : '') +
        '<input type="range" min="0" max="1000" step="1" value="' + toPos(a) + '" data-rng="' + id + '" aria-label="Dollars into ' + esc(f.name) + '"></div>';
    var name = webUrl(f.url) ? '<a href="' + esc(webUrl(f.url)) + '" target="_blank" rel="noopener nofollow" title="' + esc(f.category || '') + ' · ' + esc((f.chains || []).join(', ')) + ' · $' + fmt(f.tvl_usd) + ' deposited">' + esc(f.name) + '</a>' : esc(f.name);
    return '<div class="row cols ' + (on ? 'on' : 'off') + '" data-row="' + id + '">' +
      '<div>' + heatHTML(f) + '</div>' +
      '<div class="who">' + logo(f) + '<div><b>' + name + '</b><div class="tags"><span class="chip ' + esc(f.chip[1]) + '"' + ' title="' + esc(chipTip(f)) + '"' + '>' + esc(f.chip[0]) + '</span>' + earlyHTML(f) + routeHTML(f) + '</div></div></div>' +
      '<div class="plant">' + plant + '</div>' +
      '<div>' + (f.free ? '' : '<div class="amt"><input data-amt="' + id + '" inputmode="decimal" value="' + fmt(a) + '" aria-label="' + esc(f.name) + ' dollars"><span>USD</span></div>') + '<span id="ub-' + id + '">' + useBestHTML(f) + '</span></div>' +
      '<div class="est" id="est-' + id + '">' + estHTML(f) + '</div>' +
      '<div><button class="tg ' + (on ? 'on' : '') + '" type="button" data-tog="' + id + '" aria-label="Farm ' + esc(f.name) + '"></button></div></div>';
  }
  // a Coming soon farm: no slider, no amount, no switch; the reason it is not run yet
  function soonRowHTML(f) {
    var name = webUrl(f.url) ? '<a href="' + esc(webUrl(f.url)) + '" target="_blank" rel="noopener nofollow">' + esc(f.name) + '</a>' : esc(f.name);
    var why = (f.route || {}).reason || 'No runner for this farm yet.';
    return '<div class="row cols off soon" data-soon="' + esc(f.id) + '">' +
      '<div>' + heatHTML(f) + '</div>' +
      '<div class="who">' + logo(f) + '<div><b>' + name + '</b><div class="tags"><span class="chip ' + esc(f.chip[1]) + '" title="' + esc(chipTip(f)) + '">' + esc(f.chip[0]) + '</span>' + earlyHTML(f) + '</div></div></div>' +
      '<div class="plant"><span class="freepill" title="' + esc(why) + '">COMING SOON</span></div>' +
      '<div class="why"><small title="' + esc(why) + '">' + esc(why) + '</small></div>' + /* MOCK PATCH: the reason gets the width, three lines, the rest on hover */
      '<div class="est">' + estHTML(f) + '</div><div></div></div>';
  }
  function renderList() {
    var L = visible(), shown = L.slice(0, S.shown);
    var q = S.q.toLowerCase(), SL = SOON.filter(function (f) { return !q || f.name.toLowerCase().indexOf(q) >= 0; });
    var so = $('#soon'); if (so) so.innerHTML = SL.length ? SL.map(soonRowHTML).join('') : '<div class="more" style="margin:20px 0">' + (SOON.length ? 'No farm matches.' : 'Nothing here.') + '</div>';
    $('#list').innerHTML = shown.length ? shown.map(rowHTML).join('') : '<div class="more" style="margin:20px 0">' + (FARMS.length ? 'No farm matches.' : (META.available ? 'No farm is run by the agent yet: START FARMING opens as soon as the first runner ships. Every farm is under Coming soon below, with the reason.' : 'The farm list could not be read just now. Try again in a minute.')) + '</div>';
    $('#more').innerHTML = L.length ? '<span>Showing ' + shown.length + ' of ' + L.length + ' farms</span>' + (L.length > shown.length ? '<button type="button" data-act="more">Show 50 more</button>' : '') : '';
  }
  function rowOf(id) { var rows = document.querySelectorAll('[data-row]'); for (var i = 0; i < rows.length; i++) if (rows[i].getAttribute('data-row') === id) return rows[i]; return null; }
  function updateCard(id) {
    var f = BY[id], row = rowOf(id); if (!row || !f) return;
    var on = !!S.on[id], a = amtOf(id);
    row.classList.toggle('on', on); row.classList.toggle('off', !on);
    row.querySelector('.tg').classList.toggle('on', on);
    var fil = row.querySelector('.fil'); if (fil) fil.style.width = along(a);
    var rg = row.querySelector('[data-rng]'); if (rg && document.activeElement !== rg) rg.value = toPos(a);
    var fi = row.querySelector('[data-amt]'); if (fi && document.activeElement !== fi) fi.value = fmt(a);
    row.querySelector('.est').innerHTML = estHTML(f);
    var ub = row.querySelector('[id^="ub-"]'); if (ub) ub.innerHTML = useBestHTML(f);
  }
  function tween(el, lo, hi) {
    var from = el._v || [lo, hi]; el._v = [lo, hi];
    cancelAnimationFrame(el._raf);
    if (from[0] === lo && from[1] === hi) { el.textContent = rng(lo, hi); return; }
    var t0 = performance.now();
    var step = function (now) {
      var k = Math.min(1, (now - t0) / 420), e = 1 - Math.pow(1 - k, 3);
      el.textContent = rng(from[0] + (lo - from[0]) * e, from[1] + (hi - from[1]) * e);
      if (k < 1) el._raf = requestAnimationFrame(step);
    };
    el._raf = requestAnimationFrame(step);
  }
  function updatePlan() {
    var t = planTotals(), k = $('#kest');
    if (t.any) { k.className = 'num'; tween(k, t.lo, t.hi); }
    else { k._v = null; k.className = 'num no'; k.textContent = 'no estimate for these'; }
    $('#kline').textContent = 'estimated airdrops over 6 months · ' + t.n + ' farm' + (t.n === 1 ? '' : 's') + ' · ' + usd(t.a) + ' planted';
    $('#bestslot').innerHTML = S.custom ? '<button class="bestbtn" type="button" data-act="best">↺ ' + (byHeat() ? 'HOTTEST' : 'BEST') + ' SPLIT</button>' : (byHeat() ? '<span class="bestok">HOTTEST SPLIT ✓</span>' : '<span class="bestok">BEST SPLIT ✓</span>');
    var bi = $('#budget'); if (bi && document.activeElement !== bi) bi.value = fmt(S.budget);
    var gb = $('#gobtn'); gb.disabled = !FARMS.length && !PLAN;
    gb.innerHTML = !FARMS.length && !PLAN ? 'NO FARM THE AGENT RUNS YET' : BOLT + (PLAN ? 'UPDATE FARMS' : 'START FARMING');
    var items = FARMS.filter(function (f) { return S.on[f.id] && (f.free || amtOf(f.id) > 0); }).map(function (f) { return { f: f, v: f.free ? 0 : amtOf(f.id) }; });
    $('#field').innerHTML = fieldSvg(items, false);
  }
  var moved = { usd: 0, n: {} };
  function setAmt(id, v, quiet) {
    var f = BY[id]; if (!f || f.free) return;
    v = Math.max(0, Math.round(v || 0));
    var over = planSum() - (S.on[id] ? amtOf(id) : 0) + v - maxAmt();
    if (over > 0) {
      // all the USDC is in farms: what goes to this farm comes out of the farms that farm least (lowest rank first)
      var others = FARMS.filter(function (g) { return g.id !== id && S.on[g.id] && !g.free && amtOf(g.id) > 0; }).sort(function (a, b) { return rank(b) - rank(a) || amtOf(a.id) - amtOf(b.id); });
      for (var i = 0; i < others.length && over > 0; i++) {
        var g = others[i], take = Math.min(amtOf(g.id), over);
        S.amt[g.id] -= take; if (!S.amt[g.id]) S.on[g.id] = false;
        over -= take; moved.usd += take; moved.n[g.id] = 1; updateCard(g.id);
      }
      if (over > 0) { v -= over; if (!quiet) toast('That is the plan cap: ' + usd(maxAmt())); }
    }
    S.amt[id] = v; S.on[id] = v > 0; S.custom = true;
    if (v > 0) S.last[id] = v;
    S.budget = planSum();
    updateCard(id); updatePlan();
    if (!quiet) tellMoved(f);
  }
  function tellMoved(f) {
    var n = Object.keys(moved.n).length;
    if (moved.usd > 0) toast(usd(moved.usd) + ' moved to ' + f.name + ' from ' + n + ' farm' + (n > 1 ? 's' : '') + ' that farm less');
    moved = { usd: 0, n: {} };
  }
  function setBudget(B, commit) {
    B = Math.max(0, Math.round(B || 0));
    var most = maxAmt();
    if (commit && B > most) { B = most; toast(maxWhy(most)); }
    S.budget = B; REC = recommend(B); applyBest();
    renderList(); updatePlan();
  }

  /* ---------- the confirmation ---------- */
  function planLines() {
    return FARMS.filter(function (f) { return S.on[f.id] && (f.free || amtOf(f.id) > 0); }).map(function (f) { var a = f.free ? 0 : amtOf(f.id); return { f: f, a: a, e: est(f, a) }; });
  }
  /* START FARMING starts the real farm wallet (POST /deploy from the user's own wallets, Solana included, or
   * POST /open-direct and the user sends coins to their own farm address). The picked farms are saved beside it: a farm
   * with a reviewed deposit route gets USDC from the farm wallet as soon as it holds it; a farm without one says why
   * and nothing is sent to it. The modal lists both, per farm. */
  function routeLines(L) {
    var ready = L.filter(function (l) { return l.f.route && l.f.route.state === 'ready'; }), rest = L.filter(function (l) { return !(l.f.route && l.f.route.state === 'ready'); });
    var out = '';
    if (ready.length) out += '<b>Funded from your farm wallet\'s USDC:</b> ' + ready.map(function (l) { return esc(l.f.name) + ' (' + usd(l.a) + ', ' + esc(l.f.route.chain || '') + ')'; }).join(', ') + '. ';
    if (rest.length) out += '<b>' + rest.length + ' farm' + (rest.length === 1 ? ' has' : 's have') + ' not run by the agent yet:</b> ' + rest.slice(0, 4).map(function (l) { return esc(l.f.name) + ' (' + esc(((l.f.route || {}).reason || 'no route yet').split(':')[0]) + ')'; }).join('; ') + (rest.length > 4 ? ' and ' + (rest.length - 4) + ' more' : '') + '. The agent sends nothing to them and does no tasks there yet; Live farms says why for each.';
    return out;
  }
  var canDeploy = function (amt) { return S.balance != null && S.balance >= S.minDeploy && amt >= S.minDeploy && amt <= S.balance + 1e-9; };
  function startAmount() {
    var t = planTotals(), a = t.a > 0 ? t.a : S.budget;
    if (S.balance != null) a = Math.min(a, Math.floor(S.balance * 100) / 100);
    return Math.max(0, Math.floor(a * 100) / 100);
  }
  function walletLine() {
    var rows = (S.byChain || []).filter(function (r) { return r.fundable_usdc > 0; });
    return rows.length ? rows.map(function (r) { var syms = []; (r.wallets || []).forEach(function (w) { (w.coins || []).forEach(function (c) { if (c.usd && syms.indexOf(c.symbol) < 0) syms.push(c.symbol); }); }); return esc(r.chain) + ' $' + (+r.fundable_usdc).toFixed(2) + (syms.length ? ' (' + esc(syms.slice(0, 5).join(', ')) + (syms.length > 5 ? ', …' : '') + ')' : ''); }).join(', ') : '';
  }
  /* Farms whose own terms exclude some places (Upshift: US residents): the user confirms the farm's fixed statement
   * before the agent deposits; the server stores it (user, time, farm, exact wording) and refuses without it. */
  function attestLines(L) { return L.filter(function (l) { return l.f.route && l.f.route.attest && l.f.route.attest.wording; }); }
  function attestHTML(L) {
    return attestLines(L).map(function (l) {
      return '<label class="fine" style="display:block;text-align:left;margin:8px 0"><input type="checkbox" data-attest="' + esc(l.f.id) + '"> ' + esc(l.f.route.attest.wording) + '</label>';
    }).join('');
  }
  function attestations(L) {
    var out = {}, ok = true;
    attestLines(L).forEach(function (l) { var el = document.querySelector('[data-attest="' + l.f.id + '"]'); if (el && el.checked) out[l.f.id] = true; else ok = false; });
    return { map: out, ok: ok };
  }
  function openStart() {
    if (!SIGNED) { location.href = '/login?next=' + encodeURIComponent('/airdrop-farmer'); return; }
    var L = planLines(), t = planTotals(), amt = startAmount(), busy = running();
    var tnOnly = L.length && L.every(function (l) { return l.f.route && l.f.route.state === 'testnet'; });
    if (tnOnly) busy = true;   /* ET-32981: free testnet farms need no deposit: confirming saves the plan */
    if (!busy && !S.open) return toast('The Airdrop Farmer is not taking new farms right now.');
    if (!busy && !FARMS.length) return toast('No farm is run by the agent yet. Every farm is under Coming soon, with the reason.');
    S.mode = canDeploy(amt) ? 'wallet' : 'direct';
    var chainsTxt = (S.farmChains || []).join(', ') || 'the farmer\'s networks';
    $('#afm-modal').innerHTML = '<div class="ov" data-act="close"><div class="glass glow afm-dlg" role="dialog" aria-modal="true">' +
      '<div class="cap">' + (tnOnly ? 'FREE TESTNET FARMS' : busy ? 'YOUR FARM WALLET IS RUNNING' : 'START FARMING') + '</div>' +
      (tnOnly ? '<h3>Start your free testnet farms</h3><div class="lead">Your own farm wallet sends each farm\'s testnet transactions on a schedule. Testnet gas comes from our faucet; nothing is sent from your coins and no money is used. ' + L.map(function (l) { return esc(l.f.name) + ' (' + esc(l.f.route.automation_note || '') + ')'; }).join(', ') + '. Every step and its transaction shows on Live farms.</div>'
        : busy ? '<h3>' + (L.length ? 'Save your farm picks' : 'Your farm wallet already runs') + '</h3><div class="lead">One farm wallet per person: yours is already running. ' + (L.length ? 'Your picks are saved to your plan. ' + routeLines(L) : 'Stop it on Live farms to start again.') + '</div>' + attestHTML(L)
        : '<h3>Start your farm wallet</h3>' +
        '<div class="lead"><b>What starts now:</b> your own farm wallet (one wallet, never pooled) is funded from your coins, then the agent deposits USDC into the farms it runs (today ' + esc(agentFarmNames()) + '), one deposit per farm. Each deposit is simulated before anything is sent, and nothing is sent until you confirm your eligibility below. No swap or bridge loops run, and no fees are spent on anything else. ' + (L.length ? routeLines(L) : 'Pick farms to see which ones can be funded.') + ' Stop any time and everything, deposits included, comes back to your own wallet.</div>' +
        '<div class="kv"><span>Network fee for the deposit</span><b id="afm-depfee">reading the current fee…</b></div>' +
        '<div class="kv"><label><input type="radio" name="afmode" value="wallet" data-mode="wallet"' + (S.mode === 'wallet' ? ' checked' : '') + (S.balance != null && S.balance >= S.minDeploy ? '' : ' disabled') + '> From my own wallets, any supported coin, Solana included (no deposit step)</label><b>' + (S.balance != null ? '$' + S.balance.toFixed(2) + ' available' : 'balance not read') + '</b></div>' +
        (walletLine() ? '<div class="mnuml" style="margin:-4px 0 8px">' + walletLine() + ' · each wallet pays its own network fee from its own coins · other coins become USDC inside your farm wallet</div>' : '') +
        '<div class="kv" id="amtrow"' + (S.mode === 'wallet' ? '' : ' style="display:none"') + '><span>Amount (min $' + S.minDeploy + ')</span><b><input id="dep-amt" class="dep-amt" inputmode="decimal" value="' + amt.toFixed(2) + '" aria-label="Amount to deploy, in dollars"> USD</b></div>' +
        '<div class="kv"><label><input type="radio" name="afmode" value="direct" data-mode="direct"' + (S.mode === 'direct' ? ' checked' : '') + '> Send any supported coin to my farm address</label><b>min $' + S.minDirect + '</b></div>' +
        attestHTML(L) +
        '<div class="kv"><span>Cymetica fee</span><b>' + esc(S.fee || '10') + '% of realized profit, nothing on a loss</b></div>' +
        '<div class="fine" style="text-align:left">By starting you accept that your capital is at risk, that network fees are paid from your farm, and that no airdrop is promised. Stop any time and your coins come home to your own wallet.</div>') +
      '<div id="afm-dlgmsg" role="alert" aria-live="assertive" style="display:none"></div><div class="btns"><button class="ghost" type="button" data-act="close">Cancel</button><button class="go" type="button" data-act="confirm">' + BOLT + (busy ? 'SAVE PLAN' : 'START FARMING') + '</button></div>' +
      '</div></div>';
    if (!busy) loadDepositFee(L, amt);
  }
  function agentFarmNames() { var n = FARMS.map(function (f) { return f.name; }); return n.length ? n.slice(0, 3).join(', ') : 'none yet'; }
  /* the Ethereum network fee of one agent-run deposit, shown before the user confirms (a $20 deposit pays a large share) */
  function loadDepositFee(L, amt) {
    var eth = L.some(function (l) { return l.f.route && l.f.route.state === 'ready' && /ethereum/i.test(l.f.route.chain || ''); });
    var el = document.getElementById('afm-depfee'); if (!el) return;
    if (!eth) { el.textContent = 'shown once a farm with a deposit route is picked'; return; }
    api('GET', '/deposit-fee?chain_id=1').then(function (r) {
      var el2 = document.getElementById('afm-depfee'); if (!el2) return;
      var f = r.ok && r.d && r.d.fee_usd_max != null ? +r.d.fee_usd_max : null;
      if (f == null || !(f >= 0)) { el2.textContent = 'not readable right now; a deposit whose fee is too large is skipped, never sent'; return; }
      var dep = Math.max(amt, 0);
      el2.textContent = 'up to ' + usd(f) + ' on Ethereum' + (dep > 0 ? ' (' + (f / dep * 100).toFixed(1) + '% of ' + usd(dep) + ')' : '');
    });
  }
  function savePlan() {
    var alloc = {}, L = planLines();
    L.forEach(function (l) { alloc[l.f.id] = l.a; });
    if (!L.length) return Promise.resolve({ ok: true, skip: true });
    return api('POST', '/plan', { allocations: alloc, attestations: attestations(L).map }).then(function (r) { if (r.ok) PLAN = r.d.plan; return r; });
  }
  function confirmStart() {
    var b = document.querySelector('[data-act=confirm]');
    if (!attestations(planLines()).ok) return toast('Confirm the eligibility statement for each farm that shows one.');
    var LL = planLines(), tnOnly = LL.length && LL.every(function (l) { return l.f.route && l.f.route.state === 'testnet'; });
    if (running() || tnOnly) {
      if (b) b.disabled = true;
      return savePlan().then(function (r) { $('#afm-modal').innerHTML = ''; if (!r.ok) return toast(plain(r)); go('live'); if (!r.skip) toast('Plan saved. Farms with a deposit route are funded from your farm wallet.'); });
    }
    var risk = 'balanced', path, body;   /* pace is gone: the agent runs no scheduled steps */
    if (S.mode === 'wallet') {
      var amt = +String(($('#dep-amt') || {}).value || '').replace(/[^\d.]/g, '');
      if (!(amt >= S.minDeploy)) return toast('The minimum is $' + S.minDeploy + '.');
      if (S.balance != null && amt > S.balance + 1e-9) return toast('Your own wallets hold $' + S.balance.toFixed(2) + ' the farm can move.');
      path = '/deploy'; body = { amount_usdc: amt.toFixed(2), risk_mode: risk, terms_accepted: true };
    } else {
      path = '/open-direct'; body = { risk_mode: risk, terms_accepted: true };
    }
    if (b) b.disabled = true;
    api('POST', path, body).then(function (r) {
      if (!r.ok) { if (b) b.disabled = false; toast(plain(r)); return; }
      LEGACY = r.d;
      savePlan().then(function () {
        $('#afm-modal').innerHTML = ''; go('live');
        toast(S.mode === 'wallet' ? (r.d.funding === 'wallets' ? 'Farm started: your own coins move from your wallets into your farm wallet in the next few minutes.' : 'Farm started: deployed from your balance; your own coins move into your farm wallet in the next few minutes.') : 'Farm opened: send any supported coin to the farm address shown.');
      });
    });
  }

  /* ---------- Live farms ---------- */
  var ERRS = { fee_too_high: 'the network fee is over 4% of the deposit; it goes through at a larger amount', usdc_short: 'waiting for USDC in the farm wallet', below_route_min: 'under the smallest route minimum, so nothing can be deposited; the coins are coming back to you',
    gas_short: 'waiting for network-fee coin in the farm wallet', redeem_unavailable: 'the farm\'s liquid reserve is short right now; retrying', below_min: 'under the minimum for this route',
    deposit_refused: 'the farm\'s contract refused the deposit; nothing was sent', route_unverified: 'the farm\'s contracts did not match the reviewed ones; nothing was sent', deposit_unverified: 'the receipt did not match; checking', attestation_missing: 'waiting for your eligibility confirmation; nothing is deposited without it', redeem_pending: 'the withdrawal is booked; it is claimed to your farm wallet once the vault releases it' };
  function statusChip(p) {
    var r = p.route || {};
    if (p.status === 'deposited') return '<span class="chip g" title="USDC is deposited in this farm from your farm wallet">IN THE FARM</span>';
    if (p.status === 'exiting') return '<span class="chip c" title="Being redeemed to USDC in your farm wallet">EXITING</span>';
    if (p.status === 'testnet') return '<span class="chip g" title="' + esc(r.reason || '') + '">TESTNET RUNS</span>';
    if (p.status === 'queued') return '<span class="chip c" title="' + esc(r.reason || '') + '">QUEUED</span>';
    return '<span class="chip m" title="' + esc(r.reason || 'No reviewed deposit route yet') + '">NO ROUTE</span>';
  }
  function liveRowHTML(p) {
    var f = BY[p.id] || { id: p.id, name: p.name, icon: p.icon, ini: p.ini, heat: p.heat, early: p.early };
    var days = p.since ? Math.max(0, (Date.now() - Date.parse(p.since)) / 864e5) : 0;
    var grown = Math.min(100, days / H_DAYS * 100), r = p.route || {};
    var inFarm = p.status === 'deposited' || p.status === 'exiting';
    var why = inFarm ? usd(p.deposited_usdc) + ' deposited' + (p.deposit_tx ? ' · <a href="https://etherscan.io/tx/' + esc(p.deposit_tx) + '" target="_blank" rel="noopener nofollow">transaction</a>' : '')
      : p.status === 'testnet' ? testnetLine(p.id, r)
      : p.status === 'queued' ? 'deposits as soon as the farm wallet holds the USDC' + (p.last_error && ERRS[p.last_error] ? ' · ' + esc(ERRS[p.last_error]) + (p.needs_usd && p.last_error === 'usdc_short' ? ' (' + usd(p.needs_usd) + ' more needed)' : '') : '')
      : esc(r.reason || 'No reviewed deposit route yet') + ' Nothing is sent to it.';
    return '<div class="lrow lcols">' +
      '<div class="who">' + logo(f) + '<div><b>' + esc(f.name) + '</b><div class="tags">' + statusChip(p) + heatHTML(f, true) + earlyHTML(f) + '</div></div></div>' +
      '<div class="cell"><small>' + (inFarm ? 'IN' : 'PLANNED') + '</small><b>' + (inFarm ? usd(p.deposited_usdc) : p.usdc ? usd(p.usdc) : 'free') + '</b></div>' +
      '<div class="growth"><div class="gbar"><i style="width:' + grown.toFixed(1) + '%"></i></div><small>day ' + Math.floor(days) + ' of 180 · ' + why + '</small></div>' +
      '<div class="est"><b class="num">$0</b><small>earned so far (no token has paid yet)</small></div>' +
      '<div class="acts"><button class="stop" type="button" data-stop="' + esc(p.id) + '">' + (inFarm ? 'Take it out' : 'Stop') + '</button></div></div>';
  }
  /* ET-32981: free testnet farms — every faucet drip and testnet step the runner sent from the farm wallet */
  var TN = null;
  function testnetLine(id, r) {
    var f = TN && (TN.farms || []).filter(function (x) { return x.id === id; })[0], s = f && f.steps && f.steps[0];
    var terms = r.automation_note ? ' · ' + esc(r.automation_note) : '';
    if (!s) return 'free testnet farm: the first step is sent on the next run' + terms;
    return esc(s.label || s.step) + ' ' + (s.status === 'confirmed' ? 'done' : esc(s.status)) + (s.url ? ' · <a href="' + esc(s.url) + '" target="_blank" rel="noopener nofollow">transaction</a>' : '') + (s.at ? ' · ' + ago(s.at) : '') + terms;
  }
  function testnetHTML() {
    if (!TN || !(TN.farms || []).length) return '';
    return '<div class="sechead" style="margin-top:30px"><div><h2>Testnet steps</h2></div></div><div class="glass list">' + TN.farms.map(function (f) {
      return '<div class="lrow"><div class="who"><div><b>' + esc(f.name) + '</b><div class="tags"><span class="chip c">' + esc(f.chain) + '</span>' +
        (f.automation ? '<span class="chip m" title="' + esc(f.terms || '') + '">' + (f.automation === 'allowed' ? 'TERMS ALLOW AUTOMATION' : 'TERMS SILENT ON AUTOMATION') + '</span>' : '') + '</div></div></div>' +
        '<div class="growth"><small>' + f.steps.slice(0, 6).map(function (s) {
          return esc(s.label || s.step) + ': ' + esc(s.status) + (s.url ? ' <a href="' + esc(s.url) + '" target="_blank" rel="noopener nofollow">tx</a>' : '') + (s.at ? ' (' + ago(s.at) + ')' : '');
        }).join('<br>') + '</small></div></div>';
    }).join('') + '<div class="note" style="padding:10px 14px;color:var(--muted);font-size:12px">' + esc(TN.note || '') + '</div></div>';
  }
  function loadTestnet() {
    if (!SIGNED) return;
    api('GET', '/testnet').then(function (r) { if (r.ok) { TN = r.d; if (TAB === 'live') render(); } });
  }
  function liveChart(P) {
    var W = 760, Hh = 168, L = 2, R = 2, T = 26, B = 22, day = P.day;
    var top = Math.max(50, P.hi || 0) * 1.08;
    var x = function (d) { return L + Math.min(H_DAYS, d) / H_DAYS * (W - L - R); }, y = function (v) { return Hh - B - v / top * (Hh - T - B); };
    var nx = x(day), pm = ((P.lo || 0) + (P.hi || 0)) / 2, right = nx > W - 200;
    return '<svg viewBox="0 0 ' + W + ' ' + Hh + '">' +
      '<line x1="' + L + '" x2="' + (W - R) + '" y1="' + y(0) + '" y2="' + y(0) + '" stroke="#1e2a36"/>' +
      (P.any ? '<path d="M' + nx + ' ' + y(0) + ' L' + x(H_DAYS) + ' ' + y(P.hi) + ' L' + x(H_DAYS) + ' ' + y(P.lo) + ' Z" fill="url(#afproj)"/>' : '') +
      '<path d="M' + nx + ' ' + y(0) + ' L' + x(H_DAYS) + ' ' + y(pm) + '" stroke="#00cfff" stroke-width="2" stroke-dasharray="5 6" fill="none" stroke-opacity=".8"/>' +
      '<path d="M' + x(0) + ' ' + y(0) + ' L' + nx + ' ' + y(0) + '" stroke="#3ddc8a" stroke-width="3" fill="none" filter="url(#afsoft)"/>' +
      '<circle cx="' + nx + '" cy="' + y(0) + '" r="12" fill="#3ddc8a" fill-opacity=".18"/><circle cx="' + nx + '" cy="' + y(0) + '" r="5.5" fill="#3ddc8a" filter="url(#afsoft)"/>' +
      '<circle cx="' + x(H_DAYS) + '" cy="' + y(pm) + '" r="5" fill="#070b10" stroke="#00cfff" stroke-width="2"/>' +
      '<text x="' + (x(H_DAYS) - 4) + '" y="' + Math.max(12, y(P.hi || 0) - 8) + '" text-anchor="end" fill="#00cfff" font-size="12" font-weight="700" font-family="JetBrains Mono,monospace">6 months ≈ ' + (P.any ? rng(P.lo, P.hi) : 'no estimate yet') + '</text>' +
      '<text x="' + L + '" y="' + (Hh - 5) + '" fill="#7e90a1" font-size="11" font-family="JetBrains Mono,monospace">' + esc(P.start) + '</text>' +
      (nx > 90 ? '<text x="' + (nx + (right ? -8 : 8)) + '" y="' + (Hh - 5) + '" text-anchor="' + (right ? 'end' : 'start') + '" fill="#3ddc8a" font-size="11" font-weight="700" font-family="JetBrains Mono,monospace">now</text>' : '') +
      '<text x="' + (W - R) + '" y="' + (Hh - 5) + '" text-anchor="end" fill="#7e90a1" font-size="11" font-family="JetBrains Mono,monospace">' + esc(P.end) + '</text></svg>';
  }
  function ago(t) {
    var m = Math.round((Date.now() - Date.parse(t)) / 60000);
    return !isFinite(m) ? '' : m < 2 ? 'just now' : m < 60 ? m + 'm ago' : m < 1440 ? Math.round(m / 60) + 'h ago' : Math.round(m / 1440) + 'd ago';
  }
  // a direct farm waiting for its coins: where to send them (address in full), every accepted coin by network, the minimum and the gas note
  function depositHTML(d) {
    if (!d) return '';
    var nets = (d.accepted || []).map(function (n) { return '<div class="ln"><span>' + esc(n.chain) + '</span><span><small>' + esc((n.coins || []).slice(0, 8).join(', ')) + (n.count > 8 ? ' +' + (n.count - 8) + ' more' : '') + '</small></span><span></span></div>'; }).join('');
    return '<div class="dep"><span class="cap">SEND ANY SUPPORTED COIN TO YOUR FARM WALLET</span>' +
      '<p class="addr"><code id="depaddr">' + esc(d.address) + '</code><button class="copy" type="button" data-copy="' + esc(d.address) + '">Copy address</button></p>' +
      '<p>Any of ' + fmt(d.coins_supported || 0) + ' supported coins on ' + esc((d.accepted_chains || []).join(', ')) + ' · min $' + esc(d.min_usd) + ', up to $' + fmt(+d.max_usd) + ' · ' + esc(d.recommended_chain || 'Ethereum') + ' and ' + esc(d.recommended_coin || 'USDT') + ' are the default. Your farm wallet converts what arrives into USDC on its own network and starts farming once it is confirmed.</p>' +
      '<details class="hold"><summary>Coins by network ▾</summary>' + nets + '</details>' +
      (d.gas_note ? '<p class="gasnote">' + esc(d.gas_note) + '</p>' : '') + '</div>';
  }
  function legacyHTML() {
    var a = LEGACY; if (!a) return '';
    var live = ['pending_funding', 'funding', 'active', 'paused'].indexOf(a.status) >= 0;
    var title = a.status === 'pending_funding' ? (a.funding_mode === 'direct' && a.funding !== 'wallets' ? 'Waiting for your coins' : 'Funding from your own wallets')
      : ({ funding: 'Funding', active: 'Farming', paused: 'Paused', unwinding: 'Bringing your funds home', closed: 'Closed', refunded: 'Refunded' })[a.status] || a.status;
    return '<div class="glass wallet"><span class="cap">YOUR FARM WALLET</span><h3>' + esc(title) + '</h3>' +
      '<div class="kv"><span>In <b>' + usd(a.deployed_usdc) + '</b></span><span>On-chain transactions <b>' + (a.transactions || 0) + '</b></span>' + (a.farm_value_usd ? '<span>Value now <b>' + usd(a.farm_value_usd) + '</b></span>' : '') + ((a.chains_touched || []).length ? '<span>Networks <b>' + esc(a.chains_touched.join(', ')) + '</b></span>' : '') + '</div>' +
      depositHTML(a.deposit) +
      (a.deposit ? '' : '<p style="margin-top:10px;color:var(--muted);font-size:12px">Address <code style="word-break:break-all">' + esc(a.wallet_address) + '</code> <button class="usebest" type="button" data-copy="' + esc(a.wallet_address) + '">Copy</button></p>') +
      (a.note ? '<p style="margin-top:6px;color:var(--dim);font-size:12px">' + esc(a.note) + '</p>' : '') +
      (live ? '<div class="acts"><button class="stop" type="button" data-legacy-stop="' + esc(a.id) + '">Stop and bring my funds home</button></div>' : '') + '</div>';
  }
  function liveView() {
    if (!PLAN && running()) return '<div class="wrap">' + header() + legacyHTML() + '</div>';
    if (!PLAN) {
      return '<div class="wrap">' + header() + '<div class="glass emptylive"><b>Nothing planted yet</b>Type an amount on the Farms tab and press Start farming.<br>' +
        (SIGNED ? '' : '<a href="/login?next=/airdrop-farmer?tab=live" style="color:var(--cyan)">Sign in</a> to see your farms.<br>') +
        '<button class="go" type="button" data-tab="farms">' + BOLT + 'GO TO FARMS</button></div>' + legacyHTML() + '</div>';
    }
    var start = PLAN.started_at ? new Date(PLAN.started_at) : new Date();
    var day = Math.max(0, (Date.now() - start.getTime()) / 864e5), lo = 0, hi = 0, any = false;
    PLAN.farms.forEach(function (p) { var f = BY[p.id], e = f ? est(f, p.usdc) : null, left = Math.max(0, H_DAYS - day) / H_DAYS; if (e) { lo += e.lo * left; hi += e.hi * left; any = true; } });
    var end = new Date(start.getTime() + H_DAYS * 864e5), dfmt = function (d) { return d.toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }); };
    var items = PLAN.farms.map(function (p) { return { f: BY[p.id] || { id: p.id, name: p.name, icon: p.icon, ini: p.ini, heat: p.heat }, v: p.deposited_usdc || 0, ready: false }; });
    var events = [];
    if (PLAN.started_at) events.push({ t: PLAN.started_at, c: 'cyan', txt: 'Plan saved: <b>' + PLAN.farms.length + ' farm' + (PLAN.farms.length === 1 ? '' : 's') + '</b>' });
    PLAN.farms.forEach(function (p) { if (p.deposited_at) events.push({ t: p.deposited_at, c: 'green', txt: 'Deposited <b>' + usd(p.deposited_usdc) + '</b> into ' + esc(p.name) }); });
    if (META.generated_at) events.push({ t: META.generated_at, c: 'green', txt: 'Farm list checked: <b>' + fmt(META.count) + ' farms</b> pass the gate' });
    if (LEGACY && LEGACY.last_action_at) events.push({ t: LEGACY.last_action_at, c: 'blue', txt: 'Farm wallet step recorded' });
    events.sort(function (a, b) { return Date.parse(b.t) - Date.parse(a.t); });
    return '<div class="wrap">' + header() + (running() ? legacyHTML() : '') +
      '<section class="lhero"><div class="glass glow earnp"><span class="cap">EARNED SO FAR</span><div class="big num">$0</div>' +
      '<div class="today"><em class="num">+$0 today</em><span>day ' + Math.floor(day) + ' of your 6 months · ' + PLAN.farms.length + ' farm' + (PLAN.farms.length === 1 ? '' : 's') + ' · ' + usd(PLAN.amount_usdc) + ' planted</span></div>' +
      '<button class="go" type="button" disabled>' + BOLT + 'NOTHING TO HARVEST YET</button>' +
      '<div class="note">' + esc(PLAN.note || '') + '</div>' +
      '<div class="fine"><button type="button" data-act="stopall">Stop all farms</button></div></div>' +
      '<div class="fieldwrap">' + fieldSvg(items, true) + '<div class="fcap">Each pillar grows with what its farm has earned. A lit one is ready to harvest.</div></div></section>' +
      '<div class="glass chartp"><span class="cap">YOUR 6 MONTHS</span>' + liveChart({ day: day, lo: lo, hi: hi, any: any, start: dfmt(start), end: dfmt(end) }) +
      '<div class="ticker"><span class="cap">CYMETICA 24/7</span>' + events.slice(0, 3).map(function (e) { return '<span class="ev"><i style="background:var(--' + e.c + ')"></i><time>' + ago(e.t) + '</time><span>' + e.txt + '</span></span>'; }).join('') + '</div></div>' +
      '<div class="sechead" style="margin-top:30px"><div><h2>Your farms</h2></div></div>' +
      '<div class="glass list">' + PLAN.farms.map(liveRowHTML).join('') + '</div>' + testnetHTML() + (running() ? '' : legacyHTML()) + '</div>';
  }

  /* ---------- wiring ---------- */
  function render() {
    if (TAB === 'live') { $('#afm-root').innerHTML = liveView(); return; }
    $('#afm-root').innerHTML = farmsView(); renderList(); updatePlan();
  }
  function go(tab) {
    TAB = tab;
    try { var u = new URL(location.href); u.searchParams.set('tab', tab); history.replaceState(null, '', u); } catch (e) { /* fine */ }
    render(); window.scrollTo(0, 0);
  }
  function openStopAll() {
    $('#afm-modal').innerHTML = '<div class="ov" data-act="close"><div class="glass afm-dlg" style="width:440px"><div class="cap">STOP ALL</div><h3>Stop every farm?</h3>' +
      '<div class="lead">Every farm comes off your plan and your farm wallet brings every coin it holds home to your own wallet. A farm that was still waiting has nothing to send back.</div>' +
      '<div class="btns"><button class="ghost" type="button" data-act="close">Cancel</button><button class="go" type="button" style="background:var(--red);box-shadow:none;color:var(--text)" data-act="stopall-ok">STOP ALL</button></div></div></div>';
  }
  document.addEventListener('click', function (e) {
    var t = e.target.closest && e.target.closest(':is(#adf,.afm-portal) [data-tab],:is(#adf,.afm-portal) [data-tog],:is(#adf,.afm-portal) [data-use],:is(#adf,.afm-portal) [data-act],:is(#adf,.afm-portal) [data-stop],:is(#adf,.afm-portal) [data-legacy-stop],:is(#adf,.afm-portal) [data-mode],:is(#adf,.afm-portal) [data-copy]');
    if (!t) return;
    var d = t.dataset;
    if (d.mode) { S.mode = d.mode; var ar = $('#amtrow'); if (ar) ar.style.display = d.mode === 'wallet' ? '' : 'none'; return; }
    if (d.copy) {
      try { navigator.clipboard.writeText(d.copy).then(function () { toast('Farm address copied in full'); }, function () { toast(d.copy); }); } catch (x) { toast(d.copy); }
      return;
    }
    if (d.tab) { e.preventDefault(); return go(d.tab); }
    if (d.tog) {
      var f = BY[d.tog]; if (!f) return;
      if (S.on[f.id]) { S.on[f.id] = false; S.custom = true; if (!f.free) { S.last[f.id] = amtOf(f.id) || S.last[f.id]; S.amt[f.id] = 0; } S.budget = planSum(); updateCard(f.id); updatePlan(); }
      else if (f.free) { S.on[f.id] = true; S.custom = true; updateCard(f.id); updatePlan(); }
      else setAmt(f.id, Math.min(rec(f) || S.last[f.id] || 300, maxAmt()));
      return;
    }
    if (d.use) return setAmt(d.use, rec(BY[d.use]));
    if (d.stop) {
      api('DELETE', '/plan/' + encodeURIComponent(d.stop)).then(function (r) { if (!r.ok) return toast(plain(r)); PLAN = r.d.plan; if (r.d.farm) LEGACY = r.d.farm; toast(PLAN ? 'Taken off your plan.' : 'Stopped. Your farm wallet brings your coins home.'); render(); });
      return;
    }
    if (d.legacyStop) {
      if (!window.confirm('Stop farming and bring everything back to your balance?')) return;
      api('POST', '/' + encodeURIComponent(d.legacyStop) + '/stop').then(function (r) { if (!r.ok) return toast(plain(r)); LEGACY = r.d; toast('Stopping. Your funds come home after a few confirmations.'); render(); });
      return;
    }
    switch (d.act) {
      case 'max': setBudget(maxAmt(), true); break;
      case 'best': REC = recommend(S.budget); applyBest(); renderList(); updatePlan(); toast('Best split for ' + usd(S.budget)); break;
      case 'start': openStart(); break;
      case 'more': S.shown += 50; renderList(); break;
      case 'close': if (e.target === t) $('#afm-modal').innerHTML = ''; break;
      case 'confirm': confirmStart(); break;
      case 'stopall': openStopAll(); break;
      case 'stopall-ok':
        api('DELETE', '/plan').then(function (r) { if (!r.ok) return toast(plain(r)); PLAN = null; if (r.d.farm) LEGACY = r.d.farm; $('#afm-modal').innerHTML = ''; toast(r.d.farm ? 'All farms stopped. Your coins are coming home to your own wallet.' : 'All farms stopped'); render(); });
        break;
    }
  });
  document.addEventListener('input', function (e) {
    var t = e.target; if (!t.closest || !t.closest('#adf,.afm-portal')) return;
    if (t.dataset.rng) { setAmt(t.dataset.rng, fromPos(+t.value), true); return; }
    if (t.dataset.amt) { setAmt(t.dataset.amt, +t.value.replace(/[^\d.]/g, '')); return; }
    if (t.id === 'budget') { setBudget(+t.value.replace(/[^\d.]/g, ''), false); return; }
    if (t.id === 'q') { S.q = t.value; renderList(); }
  });
  document.addEventListener('change', function (e) { if (e.target.dataset && e.target.dataset.rng && BY[e.target.dataset.rng]) tellMoved(BY[e.target.dataset.rng]); });
  document.addEventListener('focusout', function (e) {
    var t = e.target; if (!t.closest || !t.closest('#adf,.afm-portal')) return;
    if (t.dataset && t.dataset.amt) t.value = fmt(amtOf(t.dataset.amt));
    if (t.id === 'budget') { if (S.budget > maxAmt()) setBudget(S.budget, true); t.value = fmt(S.budget); }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') $('#afm-modal').innerHTML = '';
    if (e.key === 'Enter' && (e.target.id === 'budget' || (e.target.dataset && e.target.dataset.amt))) e.target.blur();
  });

  /* ---------- load ---------- */
  function load() {
    // ET-32800: the loading screen's number follows these requests (AFBoot.done as each one returns)
    var boot = window.AFBoot || { done: function () {}, signed: function () {} };
    boot.signed(SIGNED);
    function track(k, p) {
      return p.then(function (r) { boot.done(k, k === 'farms' && r && r.ok && r.d ? { count: r.d.count || (r.d.farms || []).length } : null); return r; });
    }
    var reqs = [track('farms', api('GET', '/farms')), track('config', api('GET', '/config'))];
    if (SIGNED) { reqs.push(track('plan', api('GET', '/plan'))); reqs.push(track('status', api('GET', '/status'))); }
    Promise.all(reqs).then(function (rs) {
      var fr = rs[0], cf = rs[1], pl = rs[2], st = rs[3];
      if (fr.ok) {
        FARMS = (fr.d.farms || []).map(function (f) { f.chip = f.chip && f.chip.length === 2 ? f.chip : ['SPECULATIVE', 'm']; return f; });
        BY = {}; FARMS.forEach(function (f) { BY[f.id] = f; });
        SOON = FARMS.filter(function (f) { return !f.agent_runs; }); FARMS = FARMS.filter(function (f) { return !!f.agent_runs; });
        META = { count: fr.d.count || FARMS.length, available: fr.d.available !== false, note: fr.d.note || '', generated_at: fr.d.generated_at };
        S.fee = fr.d.perf_fee_pct ? String(+fr.d.perf_fee_pct) : S.fee;
      } else META.available = false;
      if (cf && cf.ok && cf.d.user_cap_usdc) S.cap = +cf.d.user_cap_usdc || S.cap;
      if (cf && cf.ok) {
        S.open = cf.d.open !== false; S.farmChains = cf.d.chains || [];
        if (cf.d.min_deploy_usdc) S.minDeploy = +cf.d.min_deploy_usdc || S.minDeploy;
        if (cf.d.min_direct_usd) S.minDirect = +cf.d.min_direct_usd || S.minDirect;
      }
      if (pl && pl.status === 401) SIGNED = false;
      if (pl && pl.ok) {
        PLAN = pl.d.plan; S.balance = pl.d.balance_usdc; if (pl.d.plan_cap_usdc) S.cap = +pl.d.plan_cap_usdc;
        S.byChain = pl.d.balance_by_chain || []; S.unread = pl.d.networks_unread || []; S.coinsHeld = pl.d.coins_held || [];
        S.coinsSupported = +pl.d.coins_supported || 0; S.netsRead = +pl.d.networks_read || 0;
        if (pl.d.min_deploy_usdc) S.minDeploy = +pl.d.min_deploy_usdc; if (pl.d.min_direct_usd) S.minDirect = +pl.d.min_direct_usd;
        if (pl.d.farm) LEGACY = pl.d.farm;
        if (S.balance != null) S.balance = Math.min(S.balance, S.cap);
      }
      if (st && st.ok && st.d.current) LEGACY = st.d.current;
      if (PLAN) {
        PLAN.farms.forEach(function (p) { S.amt[p.id] = p.usdc; S.on[p.id] = true; });
        S.custom = true; S.budget = PLAN.amount_usdc; REC = recommend(S.budget);
      } else {
        S.budget = Math.min(S.budget, maxAmt()); REC = recommend(S.budget); applyBest();
      }
      render();
      approveLink();
      loadTestnet();
    });
  }
  /* ---------- a plan your agent proposed: one link (ET-32463 item 15) ----------
   * ?approve=<token> carries the farms and amounts an agent proposed with your API key. Signed in to the same account,
   * the page fills them in and opens the one START FARMING confirmation: approving there is pressing its button.
   * Nothing is saved or moved before that. */
  function approveLink() {
    var tok = null;
    try { tok = new URLSearchParams(location.search).get('approve'); } catch (e) { tok = null; }
    if (!tok) return;
    if (!SIGNED) { location.href = '/login?next=' + encodeURIComponent('/airdrop-farmer?approve=' + tok); return; }
    api('GET', '/plan/proposal?token=' + encodeURIComponent(tok)).then(function (r) {
      try { history.replaceState(null, '', location.pathname + location.hash); } catch (e) { /* the link stays */ }
      if (!r.ok) return toast(plain(r));
      var P = r.d.proposal || {}, n = 0, sum = 0;
      FARMS.forEach(function (f) { S.amt[f.id] = 0; S.on[f.id] = false; });
      (P.farms || []).forEach(function (p) { if (BY[p.id] && BY[p.id].agent_runs) { S.amt[p.id] = p.usdc; S.on[p.id] = true; n++; sum += p.usdc; } });
      if (!n) return toast('None of the proposed farms can be started now.');
      S.custom = true; S.budget = Math.round(sum); render();
      toast('Your agent proposed ' + n + (n === 1 ? ' farm' : ' farms') + ', ' + usd(sum) + '. Check it and press Start to approve.');
      openStart();
    });
  }
  /* ET-32800: the dialog's dark overlay must cover the whole screen, site header and NEXUS bar included. The app is its own
   * stacking context (so its backdrop layers can sit behind it), which keeps the overlay under the site chrome. The
   * dialog's mount node therefore lives on <body>, in a host that carries the same .afm styles, for this page only. */
  (function portalDialog() {
    var m = $('#afm-modal'); if (!m || !document.body) return;
    var host = document.createElement('div'); host.className = 'afm afm-portal';
    host.appendChild(m); document.body.appendChild(host);
  })();
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', load); else load();
})();
