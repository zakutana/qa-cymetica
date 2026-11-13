/* Quant Lab v4 mock: a left menu and four tabs around THEIR quant-lab.js (build.py hooks it here).
   Ingredients (what a setup is made of), Runs (every search; the reactor replays the one you click), Bots (every bot
   the lab found, each opens the run it came from), Live search. Every figure comes from company 14's data. */
(function () {
  'use strict';
  var V4 = window.V4 = {};
  var ING = null, TAB = 'runs', GROUP = 'models', DEMO = false, OPEN = { out: false };
  var KIND = { bull: ['🐂', 'BULL BOT'], bear: ['🐻', 'BEAR BOT'], all_weather: ['🌦️', 'ALL-WEATHER'] };
  var KWEEK = { bull: 'rising', bear: 'falling', all_weather: '' };
  var GROUPS = [['models', 'Models'], ['skills', 'Skills'], ['combos', 'Combos'], ['flash', 'Flash signals'], ['off', 'Not in the lab']];

  function $(id) { return document.getElementById(id); }
  function t() { return window.QL.tools; }
  function esc(s) { return t().esc(s); }
  function pct(v, d) { if (v == null || isNaN(v)) return '—'; var a = Math.abs(v); return (v > 0 ? '+' : v < 0 ? '−' : '') + a.toFixed(d == null ? (a >= 100 ? 0 : 1) : d) + '%'; }
  function num(v) { return v == null ? '—' : Number(v).toLocaleString('en-US'); }
  function cls(v) { return v > 0 ? 'up' : v < 0 ? 'down' : ''; }
  function coin(m, big) { return '<span class="v4-coin' + (big ? ' big' : '') + '">' + t().coinImg(m) + '</span>'; }
  function M() { return window.QL.M(); }
  function S() { return window.QL.S; }
  function runs() { return (M() && M().runs) || []; }
  function runById(id) { return runs().filter(function (r) { return r.id === id; })[0] || null; }
  function curId() { var c = window.QL.cur && window.QL.cur(); return c ? c.id : null; }
  function mins(r) { var a = Date.parse(r.started_at || r.requested_at), b = Date.parse(r.finished_at); return isNaN(a) || isNaN(b) ? null : Math.round((b - a) / 60000); }
  function pf(p, short) {
    if (!p) return '<span class="v4-pf old">OLD METHOD</span>';
    var h = p.horizon === 'long_term' ? (short ? 'LONG' : 'LONG TERM') : p.horizon === 'flash_1h' ? 'FLASH 1H' : p.horizon === 'flash_5h' ? 'FLASH 5H' : p.horizon;
    return '<span class="v4-pf ' + (p.risk === 'high' ? 'hi' : 'lo') + '">' + (p.horizon === 'long_term' ? '🗓️ ' : '⚡ ') + h + ' · ' + (p.risk === 'high' ? '🔥 HIGH' : '🛡️ LOW') + '</span>';
  }
  function nameOf(id, flashLabel) {
    if (String(id).indexOf('flash:') === 0) return '⚡ ' + (flashLabel || id).replace(/^Flash /, '');
    var i = t().modelInfo(id); return i[0] + ' ' + i[1];
  }

  // ------------------------------------------------------------------ tabs
  function go(tab) {
    TAB = tab;
    [].forEach.call(document.querySelectorAll('[data-pane]'), function (s) { s.hidden = s.getAttribute('data-pane') !== tab; });
    [].forEach.call(document.querySelectorAll('#v4-nav a'), function (a) { a.classList.toggle('on', a.getAttribute('data-tab') === tab); });
    // one reactor: under the run list on Runs, under the ring on Live
    var rx = document.querySelector('.q2-reactor'), home = tab === 'live' ? $('live-rx') : $('top');
    if (rx && home) { if (tab === 'live') home.appendChild(rx); else home.parentNode.insertBefore(rx, home); }
    if (tab === 'live') renderLive();
    if ((tab === 'runs' || tab === 'live') && window.QL.size) requestAnimationFrame(function () { window.QL.size(); });
  }
  function route() { var h = (location.hash || '').replace('#', ''); go(/^(ingredients|runs|bots|live)$/.test(h) ? h : 'runs'); }
  window.addEventListener('hashchange', route);
  document.addEventListener('click', function (e) {
    var a = e.target.closest('a[href="#"]'); if (a) e.preventDefault();
    var r = e.target.closest('[data-v4run]');
    if (r) { e.preventDefault(); $('v4-drawer').hidden = true; $('v4-scrim').hidden = true; location.hash = 'runs'; window.QL.pick(+r.getAttribute('data-v4run')); window.scrollTo(0, 0); return; }
    var g = e.target.closest('[data-v4g]'); if (g) { GROUP = g.getAttribute('data-v4g'); renderIng(); return; }
    var i = e.target.closest('[data-ing]'); if (i) { drawer(i.getAttribute('data-ing')); return; }
    if (e.target.closest('[data-v4x]') || e.target.id === 'v4-scrim') { $('v4-drawer').hidden = true; $('v4-scrim').hidden = true; return; }
    if (e.target.closest('[data-v4out]')) { OPEN.out = !OPEN.out; V4.top(); return; }
    if (e.target.closest('[data-v4demo]')) { DEMO = !DEMO; renderLive(); return; }
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') { $('v4-drawer').hidden = true; $('v4-scrim').hidden = true; } });

  V4.init = function () {
    route();
    fetch('/v4/ingredients.json').then(function (r) { return r.json(); }).then(function (j) { ING = j; renderIng(); counts(); });
  };
  function counts() {
    var s = S(), ov = s && s.ov, rs = runs();
    if (ING) $('n-ing').textContent = ING.items.filter(function (x) { return !x.off; }).length;
    if (rs.length) $('n-runs').textContent = rs.length;
    var nb = allBots().length; $('n-bots').textContent = nb || '';
    var lv = liveSearch(); $('n-live').textContent = lv ? Math.floor(lv.percent || 0) + '%' : 'idle'; $('n-live').className = 'n' + (lv ? ' hot' : '');
    var co = s && s.mine; if (co && co.name) $('v4-co').textContent = co.name + ' · ' + rs.length + ' runs';
  }

  // ------------------------------------------------------------------ RUNS: the list (their click handler picks: data-run)
  V4.runs = function () {
    var cur = curId();
    $('runs').innerHTML = runs().map(function (r) {
      var failed = r.status === 'failed', m = mins(r);
      return '<button type="button" class="v4-run' + (r.id === cur ? ' on' : '') + (failed ? ' failed' : '') + '" data-run="' + r.id + '">' +
        '<b class="v4-rid">#' + r.id + '</b><span class="v4-rdate">' + esc(t().stamp(r.finished_at || r.requested_at)) + '</span>' +
        (failed ? '<span class="v4-rwon down">⚠</span>' : '<span class="v4-rwon ' + (r.won ? 'up' : 'zero') + '">' + (r.won ? '🏆 ' + r.won : '0') + '</span>') +
        '<span class="v4-rpf">' + pf(r.profile, true) + '</span>' +
        '<span class="v4-rmeta">' + (failed ? esc(r.error_label || 'stopped') : num(r.tried || 0) + ' tried' + (m ? ' · ' + m + ' min' : '')) + '</span></button>';
    }).join('');
    counts();
    return true;
  };

  // ------------------------------------------------------------------ RUNS: what the picked run found
  function strip(c) {
    var ws = (c.windows || []).filter(function (w) { return !w.seen; }); if (!ws.length) return '';
    var kw = KWEEK[c.kind || ''] || '';
    return '<div class="v4-strip" title="Every week it never saw">' + ws.map(function (w) {
      var mine = !kw || w.kind === kw, k = !mine ? 'other' : w.trades != null && w.trades < 5 ? 'thin' : w.made_money ? 'win' : 'loss';
      return '<i class="' + k + '" title="' + esc(t().day(w.start) + ' · ' + w.kind + ' week · ' + pct(w.return_pct, 2) + ' · ' + (w.trades || 0) + ' trades') + '"></i>';
    }).join('') + '</div><div class="v4-leg"><span><i class="win"></i>' + (kw ? kw + ' week, made money' : 'made money') + '</span><span><i class="loss"></i>lost</span>' + (kw ? '<span><i class="other"></i>other weeks</span>' : '') + '</div>';
  }
  function gauge(c) {
    var lo = Math.min(-5, c.held), hi = Math.max(c.bar * 1.25, c.held * 1.1, 5), x = function (v) { return ((v - lo) / (hi - lo) * 100).toFixed(1) + '%'; };
    return '<div class="v4-gauge"><i class="fill ' + cls(c.held) + '" style="left:' + x(Math.min(0, c.held)) + ';width:calc(' + x(Math.max(0, c.held)) + ' - ' + x(Math.min(0, c.held)) + ')"></i><i class="bar" style="left:' + x(c.bar) + '"></i><i class="zero" style="left:' + x(0) + '"></i></div>';
  }
  function state(c) {
    var p = c.proposal || {}, ex = (p.experiment_ids || []).length || c.experiment_id;
    if (ex) return '<span class="v4-st run">🤖 PAPER BOT</span>';
    if (c.approval_id != null && p.state !== 'executed') return '<button class="v4-approve" data-q3="approve" data-id="' + c.approval_id + '">Approve</button>';
    return '';
  }
  function winCard(c) {
    var k = KIND[c.kind] || ['🏆', 'WINNER'], kk = c.kind && c.kinds ? c.kinds[c.kind] : null, other = null;
    if (c.kind === 'bull' || c.kind === 'bear') other = c.kinds[c.kind === 'bull' ? 'bear' : 'bull'];
    var big = [];
    big.push('<div class="v4-b"><b class="' + cls(c.held) + '">' + pct(c.held) + '</b><i>blind result</i>' + gauge(c) + '<em>bar ' + pct(c.bar) + '</em></div>');
    if (kk) big.push('<div class="v4-b"><b>' + kk.won + '<small>/' + kk.windows + '</small></b><i>' + (KWEEK[c.kind] || 'all') + ' weeks won</i></div>');
    else if (c.windows_total) big.push('<div class="v4-b"><b>' + c.windows_won + '<small>/' + c.windows_total + '</small></b><i>windows won</i></div>');
    if (c.flash && c.direction && c.direction.unseen) big.push('<div class="v4-b"><b>' + c.direction.unseen.hit_pct + '%</b><i>direction right</i></div>');
    if (c.worst_window) big.push('<div class="v4-b"><b class="down">' + pct(c.worst_window.return_pct) + '</b><i>worst week</i></div>');
    big.push('<div class="v4-b"><b>' + num(c.trades) + '</b><i>trades</i></div>');
    var coins = (c.by_coin || []).slice().sort(function (a, b) { return b.return_pct - a.return_pct; });
    var mr = c.market_read;
    return '<div class="v4-win k-' + esc(c.kind || 'old') + '">' +
      '<div class="v4-wh"><span class="v4-kind">' + k[0] + ' ' + k[1] + '</span><b class="v4-wn">' + esc(nameOf(c.model, c.model_label)) + (c.side === 'short' ? ' <em>SHORT</em>' : '') + '</b>' +
      '<span class="v4-wc">' + coin(c.market) + esc(c.market) + '</span><span class="sp"></span>' + state(c) + '</div>' +
      '<div class="v4-big">' + big.join('') + '</div>' + strip(c) +
      (other ? '<div class="v4-other">' + (c.kind === 'bull' ? '🐻 in falling weeks' : '🐂 in rising weeks') + ' <b class="down">' + other.won + '/' + other.windows + '</b> · ' + pct(other.mean_return_pct, 2) + ' a week</div>' : '') +
      (coins.length > 1 ? '<div class="v4-coins">' + coins.map(function (b) { return '<span title="' + esc(b.market + ': ' + b.trades + ' trades') + '">' + coin(b.market) + '<b class="' + cls(b.return_pct) + '">' + pct(b.return_pct, 0) + '</b></span>'; }).join('') + '</div>' : '') +
      '<div class="v4-chips">' + (c.flash ? '' : '<span>SL ' + esc(String(c.settings).replace(/^SL /, '').replace(' / TP ', '% · TP ')) + '%</span>') +
      (c.can_run ? '<span>▶ ' + esc(c.can_run.label) + '</span>' : '') +
      (mr ? '<span title="' + esc(mr.text + ' · ' + mr.note) + '">🔮 ' + esc(c.market) + ' now: ' + esc(mr.read) + ' · held ' + Math.round(mr.held_pct) + '%</span>' : '') + '</div></div>';
  }
  function outList(out) {
    if (!out.length) return '';
    var show = OPEN.out ? out.slice(0, 30) : out.slice(0, 6), max = Math.max.apply(null, out.map(function (c) { return Math.abs(c.held || 0); }).concat([c0(out)]));
    function c0(o) { return Math.max.apply(null, o.map(function (c) { return c.bar || 0; })); }
    return '<div class="v4-out"><div class="v4-oh"><b>' + out.length + '</b> thrown out<span class="sp"></span><span class="v4-dim">blind result vs bar</span></div>' +
      show.map(function (c) {
        var w = Math.min(50, Math.abs(c.held || 0) / max * 50), bw = Math.min(50, (c.bar || 0) / max * 50);
        var kk = c.nearest || null;
        return '<div class="v4-orow" title="' + esc(c.reason || '') + '"><span class="v4-on">' + esc(nameOf(c.model, c.model_label)) + (c.side === 'short' ? ' ↘' : '') + '</span>' + coin(c.market) +
          '<span class="v4-ob"><i class="mid"></i><i class="v ' + cls(c.held) + '" style="' + (c.held >= 0 ? 'left:50%' : 'right:50%') + ';width:' + w.toFixed(1) + '%"></i><i class="bar" style="left:' + (50 + bw).toFixed(1) + '%"></i></span>' +
          '<b class="' + cls(c.held) + '">' + pct(c.held) + '</b><span class="v4-why">' + esc(why(c)) + '</span></div>';
      }).join('') + (out.length > 6 ? '<button class="v4-more" data-v4out>' + (OPEN.out ? '▴ less' : '▾ ' + (Math.min(30, out.length) - 6) + ' more') + '</button>' : '') + '</div>';
  }
  function why(c) {
    var l = String(c.label || '').replace(/_/g, ' ');
    return l === 'under volume floor' ? 'low volume' : l === 'lost windows' ? 'lost weeks' : l === 'too few windows' ? 'too few' : l === 'below bar' ? 'under bar' : l || 'out';
  }
  V4.top = function () {
    var m = M(); if (!m || m.mode !== 'real') return false;
    var id = curId(), r = runById(id);
    if (!r) { $('top').innerHTML = ''; return true; }
    var won = m.candidates.filter(function (c) { return c.won; }).sort(function (a, b) { return b.held - a.held; });
    var out = m.candidates.filter(function (c) { return !c.won; }).sort(function (a, b) { return b.held - a.held; });
    var mk = r.search_markets || r.markets || [], mi = mins(r);
    var head = '<div class="v4-sum">' + pf(r.profile) +
      '<span class="v4-k"><b>' + num(r.tried) + '</b> tried</span><span class="v4-k"><b>' + num(r.shortlisted) + '</b> blind-tested</span>' +
      '<span class="v4-k ' + (r.won ? 'up' : '') + '"><b>' + (r.won || 0) + '</b> won</span>' +
      (mi ? '<span class="v4-k"><b>' + mi + '</b> min</span>' : '') +
      '<span class="v4-mk">' + mk.map(function (x) { return coin(x); }).join('') + '</span></div>';
    var body = won.length ? '<div class="v4-wins">' + won.map(winCard).join('') + '</div>'
      : '<div class="v4-zero"><b>0</b><span>winners in #' + r.id + '</span></div>';
    $('top').innerHTML = head + body + outList(out);
    $('toplabel').textContent = '#' + r.id + ' · ' + t().day(r.finished_at || r.requested_at);
    counts(); renderLive();
    return true;
  };

  // ------------------------------------------------------------------ BOTS: every bot the lab found, and the run it came from
  function runFor(model, market, at) {
    var cand = runs().filter(function (r) { return r.status === 'done' && (r.shortlist || []).some(function (s) { return s.model === model && s.market === market; }); });
    if (!cand.length) cand = runs().filter(function (r) { return r.status === 'done'; });
    var tt = Date.parse(at);
    cand.sort(function (a, b) { return Math.abs(Date.parse(a.finished_at) - tt) - Math.abs(Date.parse(b.finished_at) - tt); });
    return cand[0] || null;
  }
  function allBots() {
    var s = S(); if (!s || !s.ov) return [];
    var out = [];
    ((s.res && s.res.held_back_results) || []).forEach(function (x) {
      var p = x.proposal; if (x.approval_id != null && p && p.state === 'proposed' && !(p.experiment_ids || []).length) out.push({ prop: x, run: runById(x.search_id) });
    });
    (s.ov.experiments || []).forEach(function (e) {
      var hb = e.held_back || {}; out.push({ exp: e, run: hb.model ? runFor(hb.model, hb.market, e.created_at) : null });
    });
    return out;
  }
  var WORD = { running: 'RUNNING', pending: 'QUEUED', paused: 'PAUSED', passed: 'PASSED', failed: 'FAILED', stopped: 'STOPPED' };
  function spark(pts) {
    if (!pts || pts.length < 2) return '<div class="v4-spark none">no trades yet</div>';
    var lo = Math.min.apply(null, pts), hi = Math.max.apply(null, pts), d = (hi - lo) || 1;
    return '<svg class="v4-spark" viewBox="0 0 100 30" preserveAspectRatio="none"><polyline points="' + pts.map(function (v, i) { return (i / (pts.length - 1) * 100).toFixed(1) + ',' + (28 - (v - lo) / d * 26).toFixed(1); }).join(' ') + '"/></svg>';
  }
  function botCard(b) {
    var found = b.run ? '<button class="v4-found" data-v4run="' + b.run.id + '">🔎 found in <b>#' + b.run.id + '</b> · ' + esc(t().day(b.run.finished_at)) + '</button>' : '';
    if (b.prop) {
      var x = b.prop, h = x.held_back || {}, k = KIND[x.kind] || ['🏆', 'WINNER'];
      return '<div class="v4-bot prop"><div class="v4-bh">' + t().headImg('v4-head') + '<div><b>' + esc(nameOf(x.model, x.model_label)) + '</b><span>' + coin(x.market) + esc(x.market) + ' · ' + k[0] + ' ' + k[1] + '</span></div>' +
        '<span class="v4-pill wait">WAITING FOR YOU</span></div>' +
        '<div class="v4-bk"><div><b class="' + cls(h.return_pct) + '">' + pct(h.return_pct) + '</b><i>blind</i></div><div><b>' + num(h.trades) + '</b><i>trades</i></div><div><b>' + esc(String(x.settings_label || '').split(' · ')[0].replace('SL ', '').replace(' / TP ', '·')) + '</b><i>SL·TP</i></div></div>' +
        '<div class="v4-bf">' + found + '<span class="sp"></span><button class="v4-approve" data-q3="approve" data-id="' + x.approval_id + '">Approve</button></div></div>';
    }
    var e = b.exp, st = (e.config || {}).settings || {}, hb = e.held_back || {}, pts = t().curveOf(e);
    var word = e.status === 'running' && e.trading === false ? (e.state_word || 'NOT TRADING') : e.held && e.note ? 'PAUSED' : (WORD[e.status] || String(e.status || '').toUpperCase());
    if (/paused/i.test(e.note || '')) word = 'PAUSED';
    var pillc = word === 'RUNNING' ? 'run' : word === 'PASSED' ? 'pass' : word === 'FAILED' ? 'bad' : 'idle';
    return '<div class="v4-bot"><div class="v4-bh">' + t().headImg('v4-head') + '<div><b>' + esc(nameOf(hb.model || (e.title || '').split(' · ')[0])) + '</b><span>' + coin(hb.market) + esc(hb.market || '') + ' · paper</span></div>' +
      '<span class="v4-pill ' + pillc + '" title="' + esc(e.note || e.not_trading_reason || '') + '">' + esc(word) + '</span></div>' +
      '<div class="v4-bk"><div><b class="' + cls(e.return_pct) + '">' + (e.return_pct == null ? '—' : pct(e.return_pct)) + '</b><i>paper</i></div><div><b>' + (e.trades == null ? '0' : e.trades) + '</b><i>trades</i></div>' +
      '<div><b>' + (st.stop_loss_pct == null ? '—' : st.stop_loss_pct + '·' + st.take_profit_pct) + '</b><i>SL·TP %</i></div><div><b class="' + cls(hb.return_pct) + '">' + pct(hb.return_pct) + '</b><i>when found</i></div></div>' +
      spark(pts) +
      '<div class="v4-bf">' + found + '<span class="sp"></span><span class="v4-acts"><button data-q="' + (e.status === 'running' || e.status === 'pending' ? 'pause' : 'run') + '" data-id="' + e.id + '" title="Pause / run">' + (e.status === 'running' || e.status === 'pending' ? '⏸' : '▶') + '</button>' +
      '<button data-q="vary" data-id="' + e.id + '" title="Vary">⟳</button><button data-q="config" data-id="' + e.id + '" title="Setup">⚙</button><button data-q="remove" data-id="' + e.id + '" title="Remove">✕</button></span></div></div>';
  }
  V4.bots = function () {
    var list = allBots();
    $('bots').innerHTML = list.length ? list.map(botCard).join('') : '<div class="v4-zero"><b>0</b><span>bots found yet</span></div>';
    var np = list.filter(function (b) { return b.prop; }).length;
    $('bots-sub').textContent = list.length + ' found' + (np ? ' · ' + np + ' waiting for Approve' : '');
    counts();
    return true;
  };

  // ------------------------------------------------------------------ LIVE: the search running now
  function liveSearch() {
    var lv = window.QL.live && window.QL.live();
    if (lv) return lv;
    if (!DEMO) return null;
    var last = runs().filter(function (r) { return r.status === 'done'; })[0] || {};
    return { id: (last.id || 0) + 2, status: 'running', percent: 63.2, done_jobs: 1734, total_jobs: 2744, eta_seconds: 1260, phase: 'trying combinations on the selection weeks',
      started_at: new Date(Date.now() - 38 * 60000).toISOString(), profile: { horizon: 'long_term', risk: 'low' }, tried_before: last.n_tried_total, demo: true };
  }
  var STG = [['🧩', 'BUILD'], ['💥', 'BLAST'], ['🙈', 'BLIND'], ['🚧', 'THE BAR'], ['🏆', 'FOUND']];
  function stageOf(s) { var ph = s.phase || ''; return /shortlist|held-back|never saw/.test(ph) ? 2 : s.total_jobs > 0 || /combinations/.test(ph) ? 1 : 0; }
  function renderLive() {
    var el = $('live'); if (!el || !M()) return;
    var s = liveSearch(), fails = runs().filter(function (r) { return r.status === 'failed'; });
    if (s && s.demo && window.QL.goStage && !renderLive.st) { renderLive.st = 1; window.QL.goStage(stageOf(s)); }
    if (!s) renderLive.st = 0;
    if ($('live-rx')) { $('live-rx').hidden = !s; if (s && TAB === 'live' && window.QL.size) requestAnimationFrame(function () { window.QL.size(); }); }
    if (!s) {
      var last = runs().filter(function (r) { return r.status === 'done'; })[0], m = last ? mins(last) : null;
      $('live-sub').textContent = 'nothing running';
      el.innerHTML = '<div class="v4-idle"><div class="v4-ring idle"><svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="52"/></svg><b>IDLE</b></div>' +
        '<div class="v4-idle-r"><button class="v4-go" data-go>⚡ SEARCH NOW</button>' +
        (last ? '<div class="v4-lastline"><span class="v4-dim">last</span> <button class="v4-found" data-v4run="' + last.id + '"><b>#' + last.id + '</b> · ' + esc(t().stamp(last.finished_at)) + '</button>' + pf(last.profile) +
          '<span class="v4-k"><b>' + num(last.tried) + '</b> tried</span><span class="v4-k ' + (last.won ? 'up' : '') + '"><b>' + (last.won || 0) + '</b> won</span>' + (m ? '<span class="v4-k"><b>' + m + '</b> min</span>' : '') + '</div>' : '') +
          (fails.length ? '<div class="v4-lastline"><span class="v4-k down"><b>' + fails.length + '</b> failed</span>' + fails.slice(0, 3).map(function (f) { return '<span class="v4-dim">#' + f.id + ' ' + esc(t().day(f.requested_at)) + '</span>'; }).join('') + '</div>' : '') +
        '<button class="v4-demo" data-v4demo>▶ preview a running search</button></div></div>';
      return;
    }
    var p = Math.max(0, Math.min(100, s.percent || 0)), C = 2 * Math.PI * 52, si = stageOf(s), eta = s.eta_seconds;
    $('live-sub').textContent = '#' + s.id + (s.demo ? ' · preview' : '');
    el.innerHTML = '<div class="v4-livebox"><div class="v4-ring"><svg viewBox="0 0 120 120"><circle cx="60" cy="60" r="52"/><circle class="arc" cx="60" cy="60" r="52" stroke-dasharray="' + C.toFixed(1) + '" stroke-dashoffset="' + (C * (1 - p / 100)).toFixed(1) + '"/></svg><b>' + Math.floor(p) + '<small>%</small></b></div>' +
      '<div class="v4-live-r"><div class="v4-lh">' + pf(s.profile) + (s.demo ? '<span class="v4-pill idle">PREVIEW</span>' : '<span class="v4-pill run">● LIVE</span>') + '</div>' +
      '<div class="v4-stg">' + STG.map(function (x, i) { return '<span class="' + (i < si ? 'done' : i === si ? 'now' : '') + '">' + x[0] + ' ' + x[1] + '</span>'; }).join('') + '</div>' +
      '<div class="v4-big">' +
      '<div class="v4-b"><b>' + num(s.done_jobs) + '<small>/' + num(s.total_jobs) + '</small></b><i>setups replayed</i></div>' +
      '<div class="v4-b"><b>' + (eta == null ? '…' : eta < 90 ? eta + 's' : Math.round(eta / 60) + '<small>min</small>') + '</b><i>left</i></div>' +
      '<div class="v4-b"><b>' + Math.round((Date.now() - Date.parse(s.started_at || s.requested_at)) / 60000) + '<small>min</small></b><i>running</i></div>' +
      '<div class="v4-b"><b>' + num(s.tried_before) + '</b><i>tried before</i></div></div>' +
      '<div class="v4-phase">' + esc(s.phase || 'queued') + '</div>' + (s.demo ? '<button class="v4-demo" data-v4demo>✕ end preview</button>' : '') + '</div></div>';
  }

  // ------------------------------------------------------------------ INGREDIENTS
  function inGroup(x) { return GROUP === 'off' ? !!x.off : !x.off && x.group === GROUP; }
  function renderIng() {
    if (!ING) return;
    var items = ING.items;
    $('ing-seg').innerHTML = GROUPS.map(function (g) {
      var n = items.filter(function (x) { return g[0] === 'off' ? x.off : !x.off && x.group === g[0]; }).length;
      return '<button class="' + (GROUP === g[0] ? 'on' : '') + (g[0] === 'off' ? ' off' : '') + '" data-v4g="' + g[0] + '">' + g[1] + ' <b>' + n + '</b></button>';
    }).join('');
    $('ing-sub').textContent = 'what a setup is built from';
    $('ing').innerHTML = items.filter(inGroup).map(function (x) {
      var st = x.stats || {}, side = (x.sides || []).map(function (s) { return '<span class="v4-side ' + s + '">' + (s === 'short' ? '↘ SHORT' : '↗ LONG') + '</span>'; }).join('');
      var mid = x.off ? '<div class="v4-offwhy">' + esc(x.off) + '</div>'
        : x.parts ? '<div class="v4-parts">' + x.parts.map(function (p) { return '<span>' + esc(p) + '</span>'; }).join('<i>+</i>') + '<em>' + esc(x.vote) + ' agree</em></div>'
        : x.rule ? '<div class="v4-rule">' + x.rule.map(function (r) { return '<span>' + esc(r) + '</span>'; }).join('') + '</div>'
        : x.examples ? '<div class="v4-rule"><span>' + num(x.variants) + ' variants</span>' + (x.hit ? '<span>🎯 ' + x.hit.lo + '–' + x.hit.hi + '% right</span>' : '') + '</div>'
        : x.about ? '<div class="v4-rule"><span>' + esc(x.about.split(/[.;]/)[0].slice(0, 46)) + '…</span></div>' : '<div class="v4-rule none"><span>no rule published</span></div>';
      return '<button class="v4-ic' + (x.off ? ' off' : '') + '" data-ing="' + esc(x.id) + '"><span class="v4-ii">' + esc(x.icon) + '</span><b>' + esc(x.name) + '</b>' +
        '<div class="v4-sides">' + side + '</div>' + mid +
        (x.off ? '' : '<div class="v4-ist"><span title="blind-tested">🙈 ' + (st.tested || 0) + '</span><span class="' + (st.won ? 'up' : '') + '" title="won">🏆 ' + (st.won || 0) + '</span>' +
          (st.best && st.best.pct != null ? '<span class="' + cls(st.best.pct) + '" title="best blind result">' + pct(st.best.pct) + ' ' + esc(st.best.market) + '</span>' : '') + '</div>') + '</button>';
    }).join('');
  }
  function drawer(id) {
    var x = ING.items.filter(function (i) { return i.id === id; })[0]; if (!x) return;
    var st = x.stats || {}, h = '';
    h += '<button class="v4-x" data-v4x>✕</button><div class="v4-dh"><span class="v4-ii big">' + esc(x.icon) + '</span><div><h2>' + esc(x.name) + '</h2><span>' +
      esc(x.group === 'models' ? x.family : x.group === 'skills' ? 'Skill' : x.group === 'combos' ? 'Named combination' : 'Flash signal') + '</span>' +
      (x.sides || []).map(function (s) { return '<span class="v4-side ' + s + '">' + (s === 'short' ? '↘ SHORT' : '↗ LONG') + '</span>'; }).join('') + '</div></div>';
    if (x.off) h += '<div class="v4-ds"><h4>NOT IN THE LAB</h4><p class="down">' + esc(x.off) + '</p></div>';
    if (x.about) h += '<div class="v4-ds"><h4>WHAT IT DOES</h4><p>' + esc(x.about) + '</p></div>';
    if (x.exact) h += '<div class="v4-ds"><h4>ITS BOT TRADES</h4><div class="v4-rule"><span class="up">BUY ' + esc(x.exact.buy) + '</span>' + (x.exact.sell ? '<span class="down">SELL ' + esc(x.exact.sell) + '</span>' : '') + '</div></div>';
    if (x.rule) h += '<div class="v4-ds"><h4>ENTERS WHEN</h4><div class="v4-rule">' + x.rule.map(function (r) { return '<span>' + esc(r) + '</span>'; }).join('') + '</div><p class="v4-dim">range = the lab\'s stricter and looser version of its rule</p></div>';
    if (x.parts) h += '<div class="v4-ds"><h4>MADE OF</h4><div class="v4-parts big">' + x.parts.map(function (p) { var it = ING.items.filter(function (i) { return i.name.toUpperCase() === p.toUpperCase(); })[0]; return it ? '<button data-ing="' + esc(it.id) + '">' + esc(it.icon + ' ' + p) + '</button>' : '<span>' + esc(p) + '</span>'; }).join('<i>+</i>') + '</div><p>Enters when any <b>' + esc(x.vote) + '</b> agree.</p></div>';
    if (x.examples) h += '<div class="v4-ds"><h4>' + num(x.variants) + ' VARIANTS, E.G.</h4>' + x.examples.map(function (e) { return '<p class="v4-ex">' + esc(e) + '</p>'; }).join('') + (x.hit ? '<p>🎯 direction right <b>' + x.hit.lo + '–' + x.hit.hi + '%</b> of calls (unseen hours)</p>' : '') + '</div>';
    if (x.example) h += '<div class="v4-ds"><h4>EXAMPLE</h4><p>' + esc(x.example) + '</p></div>';
    if (x['in'] && x['in'].length) h += '<div class="v4-ds"><h4>IN COMBOS</h4><div class="v4-parts big">' + x['in'].map(function (c) { var it = ING.items.filter(function (i) { return i.id === 'combo:' + c; })[0]; return it ? '<button data-ing="' + esc(it.id) + '">' + esc(it.icon + ' ' + it.name) + '</button>' : ''; }).join('') + '</div></div>';
    if (!x.off) h += '<div class="v4-ds"><h4>IN THE LAB</h4><div class="v4-big sm"><div class="v4-b"><b>' + (st.tested || 0) + '</b><i>blind-tested</i></div><div class="v4-b"><b class="' + (st.won ? 'up' : '') + '">' + (st.won || 0) + '</b><i>won</i></div>' +
      (st.best && st.best.pct != null ? '<div class="v4-b"><b class="' + cls(st.best.pct) + '">' + pct(st.best.pct) + '</b><i>best · ' + esc(st.best.market) + '</i></div>' : '') + '</div>' +
      ((st.runs || []).length ? '<div class="v4-parts">' + st.runs.map(function (r) { return '<button data-v4run="' + r + '" data-v4x>#' + r + '</button>'; }).join('') + '</div>' : '') + '</div>';
    if (!x.about && !x.rule && !x.parts && !x.examples && !x.off) h += '<div class="v4-ds"><p class="v4-dim">Cymetica publishes no description of this model.</p></div>';
    h += '<p class="v4-src">source: ' + esc(x.source || 'the lab\'s own results') + '</p>';
    $('v4-drawer').innerHTML = h; $('v4-drawer').hidden = false; $('v4-scrim').hidden = false;
  }
})();
