/* The Trading desk's experiments page: what we are trying, how each experiment is doing, and the bots in it.
 * Seeded from our real paper clones (xp-data.js); an experiment's % is its bots' P&L since they joined it,
 * over what they staked. The simulation moves only bots that are trading. Added experiments and edits are
 * kept in this browser only (localStorage), and ↺ goes back to the real snapshot. */
(function () {
  'use strict';
  var SEED = window.XP_SEED, STAKE = SEED.stake, KEY = 'co.xp.v1';
  // no stop or take-profit of our own: a bot stops when its owner or its platform settings stop it
  var S, speed = 1, ui = { open: null, pick: null, q: '', dirty: false };

  function $(id) { return document.getElementById(id); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function pct(v) { return (v > 0.005 ? '+' : v < -0.005 ? '−' : '') + Math.abs(v).toFixed(1) + '%'; }
  function usd(v) { var a = Math.abs(v); return (v > 0.005 ? '+' : v < -0.005 ? '−' : '') + '$' + (a >= 100 ? Math.round(a).toLocaleString('en-US') : a.toFixed(2)); }
  function sign(v) { return v > 0.005 ? 'up' : v < -0.005 ? 'down' : 'flat'; }
  function short(name) { return String(name).replace(/^(lab (Wave 2|Grid|h2h|cap probe)|tournament)\s+/i, ''); }
  function now() { return Date.now(); }

  /* ---------------- state ---------------- */
  function fresh() {
    var bots = {};
    SEED.bots.forEach(function (b) { bots[b.id] = JSON.parse(JSON.stringify(b)); });
    var exps = SEED.experiments.map(function (e) {
      var x = JSON.parse(JSON.stringify(e)); x.hist = [];
      return x;
    });
    var s = { bots: bots, exps: exps, next: exps.length + 1 };
    // start to now, drawn straight: the snapshot has no history in between; the live line grows from here
    s.exps.forEach(function (e) { var p = metrics(e, s).pct; e.hist = []; for (var i = 0; i <= 24; i++) e.hist.push(Math.round(p * i / 24 * 100) / 100); });
    return s;
  }
  function load() {
    try { var raw = localStorage.getItem(KEY); if (raw) return JSON.parse(raw); } catch (er) { /* private window: start fresh */ }
    return fresh();
  }
  function save() { try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (er) { /* fine: this browser only */ } }

  function metrics(e, s) {
    s = s || S;
    var rows = e.members.map(function (m) {
      var b = s.bots[m.bot]; if (!b) return null;
      var p = b.pnl - m.base;
      return { m: m, b: b, usd: p, pct: p / STAKE * 100 };
    }).filter(Boolean);
    var tot = rows.reduce(function (a, r) { return a + r.usd; }, 0);
    var trading = rows.filter(function (r) { return r.b.status === 'trading'; }).length;
    var stopped = rows.filter(function (r) { return r.b.status === 'stopped'; }).length;
    rows.sort(function (a, b) { return b.pct - a.pct; });
    return { rows: rows, usd: tot, pct: rows.length ? tot / (rows.length * STAKE) * 100 : 0, trading: trading,
      state: trading ? 'running' : rows.length && stopped === rows.length ? 'done' : 'paused',
      days: Math.max(0, Math.floor((now() - Date.parse(e.created)) / 86400000)) };
  }
  var WORD = { running: 'RUNNING', paused: 'PAUSED', done: 'FINISHED' };

  /* ---------------- the simulation: trading bots move, everything else holds ---------------- */
  function gauss() { return (Math.random() + Math.random() + Math.random() - 1.5) / 0.5; }
  function tick() {
    if (!speed) return;
    for (var k = 0; k < speed; k++) {
      Object.keys(S.bots).forEach(function (id) {
        var b = S.bots[id]; if (b.status !== 'trading') return;
        b.pnl = Math.round((b.pnl + 0.12 + gauss() * 2.6) * 100) / 100;
        if (Math.random() < 0.18) b.trades++;
      });
    }
    S.exps.forEach(function (e) {
      var x = metrics(e);
      if (x.trading) { e.hist.push(Math.round(x.pct * 100) / 100); if (e.hist.length > 160) e.hist.shift(); }
    });
    save(); render();
  }

  /* ---------------- drawing ---------------- */
  function spark(h, w, ht, cls) {
    if (!h || h.length < 2) h = [0, 0];
    var lo = Math.min.apply(null, h.concat([0])), hi = Math.max.apply(null, h.concat([0])), span = hi - lo || 1;
    var pts = h.map(function (v, i) { return [(i / (h.length - 1)) * w, ht - 3 - ((v - lo) / span) * (ht - 6)]; });
    var d = pts.map(function (p, i) { return (i ? 'L' : 'M') + p[0].toFixed(1) + ',' + p[1].toFixed(1); }).join('');
    var zero = ht - 3 - ((0 - lo) / span) * (ht - 6), last = h[h.length - 1], col = last >= 0 ? 'var(--green)' : 'var(--red)';
    return '<svg class="' + cls + '" viewBox="0 0 ' + w + ' ' + ht + '" preserveAspectRatio="none">' +
      '<line x1="0" x2="' + w + '" y1="' + zero.toFixed(1) + '" y2="' + zero.toFixed(1) + '" class="z"/>' +
      '<path d="' + d + 'L' + w + ',' + zero.toFixed(1) + 'L0,' + zero.toFixed(1) + 'Z" fill="' + col + '" opacity=".12"/>' +
      '<path d="' + d + '" fill="none" stroke="' + col + '" stroke-width="2" vector-effect="non-scaling-stroke"/>' +
      '<circle cx="' + pts[pts.length - 1][0].toFixed(1) + '" cy="' + pts[pts.length - 1][1].toFixed(1) + '" r="3" fill="' + col + '"/></svg>';
  }
  function chips(rows) {
    var max = 14;
    return rows.slice(0, max).map(function (r) {
      return '<i class="bc ' + sign(r.pct) + (r.b.status === 'trading' ? ' live' : '') + '" title="' + esc(short(r.b.name) + ' · ' + pct(r.pct)) + '"></i>';
    }).join('') + (rows.length > max ? '<em>+' + (rows.length - max) + '</em>' : '');
  }

  function render() {
    var all = S.exps.map(function (e) { return { e: e, x: metrics(e) }; });
    all.sort(function (a, b) { var r = { running: 0, paused: 1, done: 2 }; return (r[a.x.state] - r[b.x.state]) || (b.x.pct - a.x.pct); });
    var running = all.filter(function (a) { return a.x.state === 'running'; }).length;
    var n = all.reduce(function (s, a) { return s + a.x.rows.length; }, 0), tot = all.reduce(function (s, a) { return s + a.x.usd; }, 0);
    var tp = n ? tot / (n * STAKE) * 100 : 0, best = all.slice().sort(function (a, b) { return b.x.pct - a.x.pct; })[0];
    $('xsum').innerHTML =
      '<span class="k"><b>' + running + '</b> running of ' + all.length + '</span>' +
      '<span class="k ' + sign(tp) + '" title="Every experiment together: its bots\' P&L over what they staked"><b>' + pct(tp) + '</b> all together · ' + usd(tot) + '</span>' +
      (best ? '<span class="k up" title="The best experiment so far"><b>' + esc(best.e.name) + '</b> leads ' + pct(best.x.pct) + '</span>' : '');
    $('xgrid').innerHTML = all.map(function (a) {
      var e = a.e, x = a.x;
      return '<button class="xc ' + sign(x.pct) + ' ' + x.state + (ui.open === e.id ? ' on' : '') + '" data-id="' + e.id + '">' +
        '<div class="xc1"><span class="st ' + x.state + '"><i></i>' + WORD[x.state] + '</span><span class="meta">' + x.rows.length + ' bot' + (x.rows.length === 1 ? '' : 's') + ' · ' + x.days + ' day' + (x.days === 1 ? '' : 's') + '</span></div>' +
        '<h3>' + esc(e.name) + '</h3>' +
        '<div class="xc2"><b class="pct">' + pct(x.pct) + '</b><span class="usd">' + usd(x.usd) + '</span></div>' +
        spark(e.hist, 300, 54, 'spark') +
        '<div class="chips">' + chips(x.rows) + '</div>' +
        '<p class="brief">' + esc(e.brief) + '</p></button>';
    }).join('') + '<button class="xc add" id="x-new2"><span>+</span><b>New experiment</b><em>Name it, say what to try, pick the bots.</em></button>';
    if (ui.open) renderDrawer();
  }

  /* ---------------- one experiment, opened ---------------- */
  // The drawer is built whole when it opens or its shape changes; the live parts (status, numbers, the line,
  // the bots) refresh on every tick without touching what the owner may be typing in.
  function renderDrawer(full) {
    var e = S.exps.filter(function (x) { return x.id === ui.open; })[0];
    if (!e) return closeDrawer();
    var x = metrics(e), d = $('xd');
    if (!full && $('xd-live')) {
      $('xd-st').innerHTML = stHTML(x); $('xd-live').innerHTML = liveHTML(e, x); $('xd-bn').textContent = x.rows.length; $('xd-rows').innerHTML = rowsHTML(x);
      return;
    }
    var focus = document.activeElement && document.activeElement.id;
    d.innerHTML = '<div class="xd-h"><span id="xd-st" class="xd-st">' + stHTML(x) + '</span>' +
      '<input id="xd-name" value="' + esc(e.name) + '" spellcheck="false" title="Rename">' +
      '<button class="xx" data-a="close" title="Close">×</button></div>' +
      '<div id="xd-live">' + liveHTML(e, x) + '</div>' +
      '<div class="xs">INSTRUCTIONS FOR THE AGENT RUNNING IT</div>' +
      '<textarea id="xd-brief" spellcheck="false" placeholder="What to try, how long, and what counts as a win.">' + esc(e.brief) + '</textarea>' +
      '<div class="xd-save' + (ui.dirty ? ' on' : '') + '"><span>not saved</span><button class="btn gr xs" data-a="brief">Save</button></div>' +
      '<div class="xs">BOTS <b id="xd-bn">' + x.rows.length + '</b><button class="btn cy xs" data-a="pick">' + (ui.pick === 'drawer' ? 'Close' : '+ Add bots') + '</button></div>' +
      (ui.pick === 'drawer' ? picker(e) : '') +
      '<div class="br bh"><span></span><span>Bot</span><span></span><span>Return</span><span>P&amp;L</span><span>Trades</span><span></span></div>' +
      '<div class="brows" id="xd-rows">' + rowsHTML(x) + '</div>' +
      '<button class="del" data-a="delete">Delete experiment</button>';
    if (focus && $(focus)) { $(focus).focus(); if ($(focus).setSelectionRange) $(focus).setSelectionRange(1e4, 1e4); }
    fit($('xd-brief'));
  }
  function stHTML(x) {
    return '<span class="st ' + x.state + '"><i></i>' + WORD[x.state] + '</span>' +
      '<button class="btn ' + (x.state === 'running' ? '' : 'gr') + ' xs" data-a="' + (x.state === 'running' ? 'pause' : 'run') + '">' + (x.state === 'running' ? '❚❚ Pause' : x.state === 'done' ? '▶ Run again' : '▶ Run') + '</button>';
  }
  function liveHTML(e, x) {
    return '<div class="xd-big ' + sign(x.pct) + '"><b>' + pct(x.pct) + '</b><div><span>' + usd(x.usd) + '</span><em>' + x.rows.length + ' bots · ' + x.days + ' days · ' + x.trading + ' trading</em></div></div>' +
      spark(e.hist, 520, 90, 'spark big');
  }
  function rowsHTML(x) {
    var maxAbs = Math.max(5, Math.max.apply(null, x.rows.map(function (r) { return Math.abs(r.pct); }).concat([0])));
    return x.rows.length ? x.rows.map(function (r, i) {
      var w = Math.min(50, Math.abs(r.pct) / maxAbs * 50);
      return '<div class="br ' + sign(r.pct) + '"><span class="rk">' + (i + 1) + '</span>' +
        '<span class="nm"><i class="sd ' + r.b.status + '" title="' + esc(r.b.status + (r.b.why ? ': ' + r.b.why.replace('_', ' ') : '')) + '"></i>' + esc(short(r.b.name)) + '</span>' +
        '<span class="bar"><i style="' + (r.pct >= 0 ? 'left:50%' : 'right:50%') + ';width:' + w.toFixed(1) + '%"></i></span>' +
        '<b class="p">' + pct(r.pct) + '</b><span class="u">' + usd(r.usd) + '</span><span class="t">' + r.b.trades + '</span>' +
        '<button class="rm" data-rm="' + r.b.id + '" title="Take it out of this experiment">×</button></div>';
    }).join('') : '<p class="empty">No bots yet. Add some above.</p>';
  }
  function picker(e) {
    var inIt = {}; (e ? e.members : []).forEach(function (m) { inIt[m.bot] = 1; });
    var q = ui.q.toLowerCase(), list = Object.keys(S.bots).map(function (k) { return S.bots[k]; })
      .filter(function (b) { return !inIt[b.id] && (!q || b.name.toLowerCase().indexOf(q) >= 0); })
      .sort(function (a, b) { return b.pnl - a.pnl; });
    var sel = ui.sel || {};
    return '<div class="pick"><input id="xd-q" placeholder="Search your bots…" value="' + esc(ui.q) + '">' +
      '<div class="plist">' + (list.length ? list.map(function (b) {
        var p = b.pnl / STAKE * 100;
        return '<label class="pi' + (sel[b.id] ? ' on' : '') + '"><input type="checkbox" data-pk="' + b.id + '"' + (sel[b.id] ? ' checked' : '') + '>' +
          '<span class="nm">' + esc(b.name) + '</span><i class="sd ' + b.status + '"></i><b class="' + sign(p) + '">' + pct(p) + '</b></label>';
      }).join('') : '<p class="empty">No other bots match.</p>') + '</div>' +
      (e ? '<div class="pf"><button class="btn xs" data-a="pick-x">Cancel</button><button class="btn gr xs" data-a="pick-add">Add <span class="pkn">' + Object.keys(sel).length + '</span></button></div>' : '') + '</div>';
  }
  function fit(ta) { if (!ta) return; ta.style.height = 'auto'; ta.style.height = Math.min(ta.scrollHeight + 2, 260) + 'px'; }
  function openDrawer(id) {
    ui.open = id; ui.pick = null; ui.sel = {}; ui.q = ''; ui.dirty = false;
    $('xd').hidden = false; $('xshade').hidden = false;
    requestAnimationFrame(function () { $('xd').classList.add('in'); });
    render(); renderDrawer(true);
  }
  function closeDrawer() {
    ui.open = null; ui.pick = null; ui.dirty = false;
    $('xd').classList.remove('in'); $('xshade').hidden = true;
    setTimeout(function () { if (!ui.open) $('xd').hidden = true; }, 260);
    render();
  }

  /* ---------------- a new experiment ---------------- */
  function newModal() {
    ui.sel = {}; ui.q = ''; ui.pick = 'modal';
    $('xm').hidden = false;
    drawModal();
    setTimeout(function () { $('xm-name').focus(); }, 30);
  }
  function drawModal(keep) {
    var name = keep ? $('xm-name').value : '', brief = keep ? $('xm-brief').value : '', focus = document.activeElement && document.activeElement.id;
    $('xm-card').innerHTML = '<div class="mh"><h3>New experiment</h3><button class="xx" data-m="close">×</button></div>' +
      '<label class="fl">Name<input id="xm-name" placeholder="e.g. Momentum vs the dip" value="' + esc(name) + '"></label>' +
      '<label class="fl">Instructions for the agent running it<textarea id="xm-brief" placeholder="What to try, how long, and what counts as a win.">' + esc(brief) + '</textarea></label>' +
      '<div class="xs">BOTS <b><span class="pkn">' + Object.keys(ui.sel).length + '</span> picked</b></div>' + picker(null) +
      '<div class="mf"><span class="hint">They start trading on paper when it starts.</span><button class="btn" data-m="close">Cancel</button><button class="btn gr" data-m="start">Start experiment</button></div>';
    if (focus && $(focus)) { $(focus).focus(); if ($(focus).setSelectionRange) $(focus).setSelectionRange(1e4, 1e4); }
  }
  function startNew() {
    var name = $('xm-name').value.trim(), brief = $('xm-brief').value.trim(), ids = Object.keys(ui.sel);
    if (!name) { $('xm-name').focus(); return toast('Give it a name.'); }
    if (!ids.length) return toast('Pick at least one bot.');
    var e = { id: 'x' + (S.next++), name: name, brief: brief || 'No instructions yet.', created: new Date().toISOString(), hist: [0],
      members: ids.map(function (id) { var b = S.bots[id]; b.status = 'trading'; b.why = null; return { bot: id, base: b.pnl }; }) };
    S.exps.unshift(e); save();
    $('xm').hidden = true; ui.pick = null;
    toast(name + ' started: ' + ids.length + ' bot' + (ids.length === 1 ? '' : 's') + ' trading on paper.');
    openDrawer(e.id);
  }

  /* ---------------- input ---------------- */
  var toastT;
  function toast(t) { var el = $('toast'); el.textContent = t; el.hidden = false; clearTimeout(toastT); toastT = setTimeout(function () { el.hidden = true; }, 2600); }
  function current() { return S.exps.filter(function (x) { return x.id === ui.open; })[0]; }
  document.addEventListener('click', function (ev) {
    var t = ev.target;
    var sp = t.closest('[data-speed]');
    if (sp) { speed = +sp.getAttribute('data-speed'); Array.prototype.forEach.call(document.querySelectorAll('[data-speed]'), function (b) { b.classList.toggle('on', b === sp); }); return; }
    if (t.closest('#x-reset')) { try { localStorage.removeItem(KEY); } catch (er) { /* fine */ } S = fresh(); closeDrawer(); return toast('Back to the real snapshot of 17 Oct.'); }
    if (t.closest('#x-new') || t.closest('#x-new2')) return newModal();
    var card = t.closest('.xc[data-id]'); if (card) return openDrawer(card.getAttribute('data-id'));
    if (t.id === 'xshade') return closeDrawer();
    var m = t.closest('#xm [data-m]');
    if (m) { var a = m.getAttribute('data-m'); if (a === 'close') { $('xm').hidden = true; ui.pick = null; } if (a === 'start') startNew(); return; }
    if (t.id === 'xm') { $('xm').hidden = true; ui.pick = null; return; }
    var e = current();
    var act = t.closest('#xd [data-a]');
    if (act && e) {
      var w = act.getAttribute('data-a');
      if (w === 'close') return closeDrawer();
      if (w === 'run' || w === 'pause') {
        e.members.forEach(function (mm) { var b = S.bots[mm.bot]; if (!b) return; if (w === 'run') { b.status = 'trading'; b.why = null; } else if (b.status === 'trading') b.status = 'paused'; });
        save(); render(); return toast(e.name + (w === 'run' ? ' runs: its bots trade on paper.' : ' paused: its bots stop opening trades.'));
      }
      if (w === 'brief') { e.brief = $('xd-brief').value.trim(); ui.dirty = false; save(); render(); renderDrawer(true); return toast('Instructions saved: the agent works from them now.'); }
      if (w === 'pick') { ui.pick = ui.pick === 'drawer' ? null : 'drawer'; ui.sel = {}; ui.q = ''; return renderDrawer(true); }
      if (w === 'pick-x') { ui.pick = null; return renderDrawer(true); }
      if (w === 'pick-add') {
        var ids = Object.keys(ui.sel || {}); if (!ids.length) return toast('Tick the bots to add.');
        var live = metrics(e).state === 'running';
        ids.forEach(function (id) { var b = S.bots[id]; if (live) { b.status = 'trading'; b.why = null; } e.members.push({ bot: id, base: b.pnl }); });
        ui.pick = null; ui.sel = {}; save(); render(); renderDrawer(true); return toast(ids.length + ' bot' + (ids.length === 1 ? '' : 's') + ' added to ' + e.name + '.');
      }
      if (w === 'delete') {
        if (!confirm('Delete "' + e.name + '"? Its bots stay in your account.')) return;
        S.exps = S.exps.filter(function (x) { return x !== e; }); save(); closeDrawer(); return toast('Experiment deleted. Its bots stay in your account.');
      }
    }
    var rm = t.closest('#xd [data-rm]');
    if (rm && e) { var id = rm.getAttribute('data-rm'); e.members = e.members.filter(function (mm) { return mm.bot !== id; }); save(); return render(); }
  });
  document.addEventListener('change', function (ev) {
    var pk = ev.target.getAttribute && ev.target.getAttribute('data-pk');
    // a tick only marks the row and moves the count: the list stays where it was scrolled
    if (pk) {
      ui.sel = ui.sel || {}; if (ev.target.checked) ui.sel[pk] = 1; else delete ui.sel[pk];
      var row = ev.target.closest('.pi'); if (row) row.classList.toggle('on', ev.target.checked);
      Array.prototype.forEach.call(document.querySelectorAll('.pkn'), function (el) { el.textContent = Object.keys(ui.sel).length; });
    }
    if (ev.target.id === 'xd-name') { var e = current(); if (e && ev.target.value.trim()) { e.name = ev.target.value.trim(); save(); render(); } }
  });
  document.addEventListener('input', function (ev) {
    if (ev.target.id === 'xd-brief') { ui.dirty = true; fit(ev.target); var s = document.querySelector('.xd-save'); if (s) s.classList.add('on'); }
    if (ev.target.id === 'xd-q' || ev.target.id === 'xm-q') { ui.q = ev.target.value; if (ui.pick === 'modal') drawModal(true); else renderDrawer(true); }
  });
  document.addEventListener('keydown', function (ev) {
    if (ev.key !== 'Escape') return;
    if (!$('xm').hidden) { $('xm').hidden = true; ui.pick = null; } else if (ui.open) closeDrawer();
  });

  S = load();
  render();
  setInterval(tick, 1100);
})();
