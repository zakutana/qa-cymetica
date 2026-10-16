/* The /company mockup: the page around the office. Renders the live page's blocks from the
 * simulated state (company bar and turn counter, departments, the office stage, what waits
 * for the owner, the Manager's plan and chat, the feed, the nine tabs) and turns every
 * click into a state change, so nothing on it is a dead button. Strings follow the live
 * page (build-company.js, EN) wherever it has one. */
(function () {
  'use strict';
  var CO = window.CO;
  function $(id) { return document.getElementById(id); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function u2(v) { return (+v || 0).toFixed(2); }
  function hhmm(t) { return CO.hhmm(t); }
  var DAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
  function dayTime(t) { return DAYS[new Date(t).getDay()] + ' ' + hhmm(t); }
  function hm(ms) {
    if (ms <= 0) return '0m';
    var m = Math.round(ms / 60000), h = Math.floor(m / 60);
    return h >= 24 ? Math.floor(h / 24) + 'd ' + (h % 24) + 'h' : h ? h + 'h ' + (m % 60) + 'm' : m + 'm';
  }
  CO.ago = function (t) {
    var m = Math.max(0, Math.round((CO.S.clock - t) / 60000));
    return m < 1 ? 'now' : m < 60 ? m + ' min' : m < 1440 ? Math.round(m / 60) + ' h' : Math.round(m / 1440) + ' d';
  };
  function setHTML(el, html) { if (el && el._h !== html) { el._h = html; el.innerHTML = html; return true; } return false; }
  function initials(n) { return String(n || '?').split(/\s+/).map(function (w) { return w.charAt(0); }).join('').slice(0, 2).toUpperCase(); }
  var WORD = { working: 'Working', queued: 'Queued', waiting: 'Waiting for you', idle: 'Idle' };
  var TSTAT = { queued: 'queued', running: 'running', waiting_approval: 'waits for you', done: 'done', failed: 'failed', cancelled: 'cancelled' };

  var ui = { tab: 'office', view: '2d', panel: null, open: {}, seen: {}, feedTop: 0, dirty: false, prev: {}, tfDept: '', tfStatus: '', memQ: '', memDept: null };
  var office;

  /* ---------------- boot ---------------- */
  function boot() {
    CO.S = CO.fresh(Date.now());
    office =new CO.Office($('office'), $('stage'), tipFor);
    office.layout();
    markSeen();
    bind();
    wire();
    CO.on('change', render);
    CO.on('tick', clock);
    render();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { office.fit(false); $('msgs').scrollTop = 1e6; });
    window.addEventListener('resize', function () { $('msgs').scrollTop = 1e6; });
  }
  function markSeen() {
    ui.seen = {};
    CO.S.approvals.forEach(function (a) { ui.seen[a.id] = 1; });
    ui.feedTop = CO.S.feed.length ? CO.S.feed[0].at : 0;
  }

  /* ---------------- render ---------------- */
  function render() {
    renderBar();
    renderTabs();
    if (ui.tab === 'office') { renderRail(); renderStrip(); renderRight(); }
    else renderPane();
    if (ui.panel != null) renderDrawer();
    office.update();
    clock(true);
  }

  function renderBar() {
    var S = CO.S, c = S.company, b = S.budget, l = CO.left(), paused = c.status === 'paused';
    $('co-name').textContent = c.name;
    $('co-logo').textContent = initials(c.name);
    var st = $('co-status'); st.textContent = paused ? 'PAUSED' : 'ACTIVE'; st.className = 'pill ' + (paused ? 'off' : 'on');
    $('co-pause').textContent = paused ? 'Resume' : 'Pause';
    var et = $('co-et10'); et.hidden = !S.et10;
    if (S.et10) et.innerHTML = '<b>+' + S.et10.toLocaleString('en-US') + '</b> ET10 earned';
    var n = S.approvals.length, w = $('co-waiting');
    w.innerHTML = n ? '<b>' + n + '</b> waiting for you' : 'nothing waits for you';
    w.classList.toggle('none', !n);
  }
  function setN(box, id, v, low) {
    var el = $(id), bx = $(box), s = String(v);
    if (ui.prev[id] != null && ui.prev[id] !== s) { bx.classList.remove('bump'); void bx.offsetWidth; bx.classList.add('bump'); }
    ui.prev[id] = s; el.textContent = s; bx.classList.toggle('low', !!low);
  }
  function renderTabs() {
    var S = CO.S, open = 0;
    S.departments.forEach(function (d) { open += CO.deptView(d).open; });
    $('tn-tasks').textContent = open || '';
    $('tn-appr').textContent = S.approvals.length || '';
  }

  function renderRail() {
    var S = CO.S;
    $('rail-n').textContent = S.departments.length;
    setHTML($('depts'), S.departments.map(function (d) {
      var v = CO.deptView(d);
      return '<button class="dept ' + v.status + (ui.panel === d.id ? ' on' : '') + (d.born && S.clock - d.born < 4000 ? ' born' : '') + '" data-id="' + d.id + '" title="' + WORD[v.status] + '">' +
        '<div class="d1"><i class="dot"></i><b>' + esc(d.name) + '</b>' + (d.et10 ? '<span class="et">+' + d.et10.toLocaleString('en-US') + ' ET10</span>' : '') + '</div>' +
        '<div class="dus" title="What this department used of your plan: this 5-hour session and the last 7 days"><span>' + v.sessPct + '%<small>session</small></span><span>' + v.weekPct + '%<small>week</small></span>' +
        '<span class="ubar"><i style="width:' + Math.min(100, v.weekPct) + '%"></i></span></div>' +
        (d.schedule ? '<div class="dsch">⟳ ' + esc(d.schedule.label.replace(/ \(.*/, '')) + ' · next ' + hhmm(d.next_run) + (d.products.length ? ' · ' + esc(d.products.join(', ')) : '') + '</div>' : '') +
        '<div class="d2"><span class="c">' + v.open + '<small>open</small></span><span class="g">' + v.done + '<small>done</small></span>' +
        '<span class="' + (v.failed ? 'r' : 'z') + '">' + v.failed + '<small>failed</small></span><span class="m">' + v.memory + '<small>mem</small></span></div>' +
        (v.waits ? '<div class="dwait">Queued: <span data-wait="' + d.id + '">' + esc(v.waits) + '</span></div>' : '') +
        '<div class="d3">' + esc(v.experts.map(function (e) { return e.name; }).join(' · ')) + '</div>' +
        (v.status === 'working' ? '<span class="run"><i></i></span>' : '') + '</button>';
    }).join('') || '<p class="empty">No departments yet. <a id="rail-add">+ Add the first one</a>, or click the empty lot in the office.</p>');
  }

  // The bottom panel, the way Claude shows usage: Session limit (built from this window's turns,
  // each as wide as what it cost, then the Manager's plan in blue), Weekly, and Today's ceiling.
  function renderStrip() {
    var S = CO.S, b = S.budget, cap = b.session.cap, avg = S.meter.length ? CO.avg() : 0.22;
    var start = b.session.resets_at - b.session.every, cells = S.strip.filter(function (c) { return c.at >= start; });
    var onPlan = cells.filter(function (c) { return !c.extra; }), onExtra = cells.length - onPlan.length, known = 0;
    onPlan.forEach(function (c) { if (c.units != null) known += c.units; });
    var used = Math.min(b.session.used, cap), before = Math.max(0, used - known), total = 0;
    function seg(cls, u, tip) { u = Math.max(0, Math.min(u, cap - total)); if (u <= 0) return ''; total += u; return '<i class="' + cls + '" style="width:' + (u / cap * 100).toFixed(2) + '%" title="' + esc(tip) + '"></i>'; }
    var h = before > 0.004 ? seg('before', before, 'Earlier in this window: ' + u2(before) + ' u') : '';
    onPlan.forEach(function (c) {
      var d = CO.dept(c.dept_id), u = c.units != null ? c.units : avg;
      h += seg(c.state, u, (d ? d.name : 'Removed department') + ' · ' + c.state + ' · ' + hhmm(c.at) + ' · ' + (c.units != null ? u2(c.units) + ' u' : 'running'));
    });
    S.plan.forEach(function (id) {
      var t = CO.task(id); if (!t) return;
      var d = CO.dept(t.dept_id), k = Math.max(1, t.turns_needed - t.turns);
      for (var i = 0; i < k; i++) h += seg('plan', avg, 'Planned: ' + (d ? d.name + ': ' : '') + t.title + ' · ~' + u2(avg) + ' u');
    });
    setHTML($('segs'), h);
    var sp = Math.round(used / cap * 100), usp = $('us-p');
    usp.textContent = sp + '% used' + (onExtra ? ' · ' + onExtra + ' on extra usage' : '');
    usp.classList.toggle('hot', sp >= 85);
    var wp = Math.min(100, b.week.used / b.week.cap * 100);
    $('uw-p').textContent = Math.round(wp) + '% used';
    var wb = $('uw-bar'); wb.style.width = wp.toFixed(1) + '%'; wb.classList.toggle('hot', wp >= 85);
    $('strip-n').textContent = S.strip.length; $('strip-cap').textContent = b.cap;
    $('day-bar').style.width = Math.min(100, S.strip.length / b.cap * 100).toFixed(1) + '%';
  }

  function apprCard(a, full) {
    var d = CO.dept(a.dept_id), isNew = !ui.seen[a.id];
    var kind = a.kind === 'real-money action' ? 'tag money' : 'tag k';
    return '<div class="ai' + (isNew ? ' new' : '') + '" data-id="' + a.id + '"><div class="t"><span class="tag">' + esc(d ? d.name : '') + '</span><span class="' + kind + '">' + esc(a.kind) + '</span>' +
      esc(CO.ago(a.created_at)) + '</div><p>' + esc(a.summary) + '</p>' + (full ? '<div class="draft">' + fmtDraft(a.body) + '</div>' : '') +
      '<div class="bt"><button class="btn gr" data-d="approve">Approve</button><button class="btn rd" data-d="reject">Reject</button>' +
      (full ? '' : '<button class="btn" data-r="1">Read</button>') + '</div></div>';
  }
  function fmtDraft(body) {
    return String(body || '').split('\n\n').map(function (blk, i) {
      var lines = blk.split('\n'), head = i === 0 || (lines.length > 1 && lines[0].length < 30);
      return '<div>' + (head ? '<h4>' + esc(i ? lines[0].toUpperCase() : lines[0]) + '</h4>' + esc(lines.slice(1).join('\n')) : esc(blk)) + '</div>';
    }).join('');
  }
  function renderRight() {
    var S = CO.S, n = S.approvals.length;
    $('ap-n').textContent = n || '';
    $('p-appr').classList.toggle('none', !n);
    setHTML($('appr'), n ? S.approvals.map(function (a) { return apprCard(a, false); }).join('') : '<p class="empty ok">Nothing is waiting for you.</p>');
    S.approvals.forEach(function (a) { ui.seen[a.id] = 1; });
    // the plan
    $('plan-n').textContent = S.plan.length || '';
    setHTML($('plan'), S.plan.length ? S.plan.map(function (id, i) {
      var t = CO.task(id); if (!t) return '';
      var d = CO.dept(t.dept_id), w = CO.waitText(t), waits = w.indexOf('next pass') !== 0;
      var left = Math.max(1, t.turns_needed - t.turns);
      return '<li data-id="' + id + '"' + (ui.moved === id ? ' class="moved"' : '') + '><span class="n">' + (i + 1) + '</span><div><b title="' + esc(t.title) + '">' + esc(d ? d.name : '') + ': ' + esc(t.title) + '</b>' +
        '<em class="' + (waits ? 'wait' : '') + '">' + esc(waits ? w : t.why) + ' · ~' + left + ' turn' + (left > 1 ? 's' : '') + '</em></div>' +
        '<span class="pa"><button data-a="top" title="Move to the top"' + (i ? '' : ' disabled') + '>⤒</button><button data-a="up" title="Move up"' + (i ? '' : ' disabled') + '>↑</button>' +
        '<button data-a="down" title="Move down"' + (i < S.plan.length - 1 ? '' : ' disabled') + '>↓</button><button data-a="remove" title="Remove from the plan">×</button></span></li>';
    }).join('') : '<li class="empty">Nothing queued. Give the Manager work below.</li>');
    ui.moved = null;
    // the Manager
    var last = S.messages[S.messages.length - 1];
    var mh = S.messages.map(function (m) {
      return '<div class="msg' + (m.role === 'owner' ? ' me' : '') + '"><em>' + (m.role === 'owner' ? 'You' : 'Manager') + ' · ' + hhmm(m.at) + '</em>' + esc(m.text) + '</div>';
    }).join('');
    if (S.notice && last && last.role === 'owner' && !last.answered) mh += '<div class="msgwait">' + esc(S.notice.text) + '</div>';
    if (setHTML($('msgs'), mh || '<p class="empty">No messages yet. Say hello to your Manager.</p>')) {
      var box = $('msgs'); box.scrollTop = 1e6; requestAnimationFrame(function () { box.scrollTop = 1e6; });
    }
    $('typing').hidden = !S.typing;
    // the feed, newest first
    var top = ui.feedTop, fresh = 0;
    S.feed.forEach(function (f) { if (f.at > top) fresh++; });
    setHTML($('feed'), S.feed.slice(0, 12).map(function (f, i) {
      return '<li class="' + f.kind + (i < fresh ? ' new' : '') + '"><span><b>' + esc(f.dept) + '</b> ' + esc(f.text) + '</span><em>' + hhmm(f.at) + '</em></li>';
    }).join('') || '<p class="empty">Quiet so far. Give the Manager work and watch the office move.</p>');
    if (S.feed.length) ui.feedTop = S.feed[0].at;
  }

  /* ---------------- the department drawer ---------------- */
  function openDrawer(id) {
    var d = CO.dept(id); if (!d) return;
    if (ui.tab !== 'office') setTab('office');
    if (ui.panel !== id) { ui.dirty = false; $('dr-ch-text').value = d.charter; ui.open = {}; }
    ui.panel = id;
    var dr = $('drawer'); dr.hidden = false; dr.scrollTop = 0;
    renderDrawer(); renderRail();
    office.select('d' + id);
    office.focus('d' + id, dr.offsetWidth + 24);
  }
  function closeDrawer() {
    if (ui.panel == null) return;
    ui.panel = null; $('drawer').hidden = true;
    office.select(null); renderRail();
    office.fit(true);
  }
  function taskRow(t, opened) {
    var one = t.status === 'running' ? 'running · attempt ' + t.attempt + ' of 3' : t.last_error && t.status !== 'done' ? 'last try: ' + t.last_error : t.outcome || (t.status === 'queued' ? CO.waitText(t) : '');
    var when = t.finished_at || t.started_at || t.created_at;
    var more = opened ? '<div class="more"><b>Brief:</b> ' + esc(t.brief) + '<br><b>Result:</b> ' + esc(t.outcome || 'No output yet.') +
      (t.last_error ? '<br><b class="red">Last error:</b> ' + esc(t.last_error) : '') + '<br>' + esc(TSTAT[t.status]) + ' · ' + t.turns + ' turn' + (t.turns === 1 ? '' : 's') +
      (t.units ? ' · ' + u2(t.units) + ' u' : '') + ' · ' + CO.expertName(t.expert || '') + '</div>' : '';
    return '<div class="trow" data-task="' + t.id + '"><span><span class="st ' + t.status + '">' + esc(TSTAT[t.status]) + '</span></span><div><b>' + esc(t.title) + '</b><em>' + esc(one) + '</em></div><i>' + hhmm(when) + '</i>' + more + '</div>';
  }
  function sortTasks(list) {
    var S = CO.S, rank = { running: 0, queued: 1, waiting_approval: 2 };
    return list.slice().sort(function (a, b) {
      var ra = rank[a.status] != null ? rank[a.status] : 3, rb = rank[b.status] != null ? rank[b.status] : 3;
      if (ra !== rb) return ra - rb;
      if (ra === 1) return S.plan.indexOf(a.id) - S.plan.indexOf(b.id);
      return (b.finished_at || b.started_at || b.created_at) - (a.finished_at || a.started_at || a.created_at);
    });
  }
  function renderDrawer() {
    var S = CO.S, d = CO.dept(ui.panel);
    if (!d) return closeDrawer();
    var v = CO.deptView(d), appr = S.approvals.filter(function (a) { return a.dept_id === d.id; });
    setHTML($('dr-head'), '<i class="dot ' + v.status + '"></i><h2>' + esc(d.name) + '</h2><span class="pill st-' + v.status + '">' + WORD[v.status].toUpperCase() + '</span>' +
      '<span class="x"><button class="btn" data-a="edit">Edit</button><button class="btn" data-a="close" title="Close">×</button></span>');
    setHTML($('dr-chips'), v.experts.map(function (e) { return '<span class="chip">' + esc(e.name) + '</span>'; }).join('') +
      (appr.length ? '<span class="chip red" data-a="appr">' + appr.length + ' waiting for you</span>' : ''));
    var ta = $('dr-ch-text');
    if (!ui.dirty && ta.value !== d.charter) ta.value = d.charter;
    charterMeta();
    setHTML($('dr-kp'), '<div><b class="cy">' + v.open + '</b><span>open</span></div><div><b class="gr">' + v.done + '</b><span>done</span></div>' +
      '<div><b class="red">' + v.failed + '</b><span>failed</span></div>' +
      '<div title="What it used of this 5-hour session"><b>' + v.sessPct + '%</b><span>of session</span></div>' +
      '<div title="What it used of your weekly plan in the last 7 days"><b>' + v.weekPct + '%</b><span>of week</span></div>');
    // a department on a clock: its runs, products, who the bugs are filed as, what they earned
    var runsHtml = '';
    if (d.schedule) {
      runsHtml = '<div class="runs"><div class="sec">RUNS <span>' + esc(d.schedule.label) + '</span></div>' +
        '<div class="rk"><div><b>' + hhmm(d.next_run) + '</b><span>next run</span></div><div><b>' + (d.runs || 0) + '</b><span>runs done</span></div>' +
        '<div><b class="gr">' + (d.accepted || 0) + '</b><span>bugs accepted</span></div><div><b class="gr">+' + (d.et10 || 0).toLocaleString('en-US') + '</b><span>ET10 to ' + esc(d.files_as || 'you') + '</span></div></div>' +
        '<div class="prods">' + (d.products.length ? d.products.map(function (p) { return '<span class="chip">' + esc(p) + '</span>'; }).join('') : '<span class="hint">no products yet: the public site</span>') + '</div>' +
        '<div class="cb"><input id="dr-prods" placeholder="Products, comma separated" value="' + esc(d.products.join(', ')) + '"><button class="btn" data-a="prods">Save</button><button class="btn cy" data-a="runnow">Run now</button></div></div>';
    }
    if ($('dr-runs')._h !== runsHtml && !(document.activeElement && document.activeElement.id === 'dr-prods')) { $('dr-runs')._h = runsHtml; $('dr-runs').innerHTML = runsHtml; }
    var r = v.running;
    setHTML($('dr-now'), r ? '<div class="now"><div class="t1">NOW · ATTEMPT ' + r.attempt + ' OF ' + r.max_attempts + '</div><p>' + esc(r.title) + '</p>' +
      '<div class="t2">' + esc(CO.expertName(r.expert)) + ' · started ' + hhmm(r.turn_started || r.started_at) + (r.last_error ? ' · last try: <b>' + esc(r.last_error) + '</b>' : '') + '</div><span class="run"><i></i></span></div>'
      : '<div class="now idle"><div class="t1">NOW</div><p>' + (v.waits ? 'Queued: <span data-wait="' + d.id + '">' + esc(v.waits) + '</span>' : v.waiting ? 'Waits for your approval.' : 'Nothing runs now.') + '</p></div>');
    var ts = sortTasks(CO.deptTasks(d.id));
    $('dr-tasks-all').textContent = 'All ' + ts.length + ' →';
    setHTML($('dr-tasks'), ts.length ? ts.slice(0, 7).map(function (t) { return taskRow(t, ui.open[t.id]); }).join('') : '<p class="empty">No tasks yet.</p>');
    var mem = S.memory.filter(function (m) { return m.dept_id === d.id; }).sort(function (a, b) { return b.id - a.id; });
    $('dr-mem-all').textContent = 'All ' + mem.length + ' →';
    setHTML($('dr-mem'), mem.length ? mem.slice(0, 5).map(function (m) { return '<div class="mem"><span class="' + m.kind + '">' + esc(m.kind) + '</span><div>' + esc(m.text) + '</div></div>'; }).join('') : '<p class="empty">Nothing remembered yet.</p>');
    setHTML($('dr-appr'), appr.length ? '<div class="sec" style="margin:4px 0 8px">WAITING FOR YOU</div>' + appr.map(function (a) { return apprCard(a, false); }).join('') : '');
  }
  function charterMeta() {
    var d = CO.dept(ui.panel), ta = $('dr-ch-text'), n = ta.value.length.toLocaleString('en-US');
    var m = $('dr-ch-meta');
    m.className = ui.dirty ? 'unsaved' : '';
    m.textContent = ui.dirty ? n + ' / 2,000 · not saved' : n + ' / 2,000 · saved ' + (d ? dayTime(d.charter_updated_at) : '');
  }

  /* ---------------- the other tabs ---------------- */
  function setTab(name) {
    ui.tab = name;
    Array.prototype.forEach.call(document.querySelectorAll('#tabs button'), function (b) { b.classList.toggle('on', b.getAttribute('data-tab') === name); });
    Array.prototype.forEach.call(document.querySelectorAll('.pane'), function (p) { p.hidden = p.getAttribute('data-pane') !== name; });
    if (name !== 'office') { $('drawer').hidden = true; } else if (ui.panel != null) { $('drawer').hidden = false; }
    render();
    if (name === 'office') requestAnimationFrame(function () { office.resize(); });
  }
  function renderPane() {
    ({ tasks: renderTasks, approvals: renderApprovals, memory: renderMemory, audit: renderAudit, investable: renderInvest, legal: renderLegal, token: renderToken, settings: renderSettings }[ui.tab] || function () {})();
  }
  function renderTasks() {
    var S = CO.S, sel = $('tf-dept');
    setHTML(sel, '<option value="">All</option>' + S.departments.map(function (d) { return '<option value="' + d.id + '">' + esc(d.name) + '</option>'; }).join(''));
    sel.value = ui.tfDept; $('tf-status').value = ui.tfStatus;
    var rows = sortTasks(S.tasks.filter(function (t) {
      return (!ui.tfDept || String(t.dept_id) === String(ui.tfDept)) && (!ui.tfStatus || t.status === ui.tfStatus);
    }));
    var open = 0, done = 0, failed = 0;
    S.tasks.forEach(function (t) { if (t.status === 'done') done++; else if (t.status === 'failed') failed++; else if (t.status !== 'cancelled') open++; });
    $('tk-sub').textContent = S.tasks.length + ' tasks · ' + open + ' open · ' + done + ' done · ' + failed + ' failed';
    setHTML($('tasks'), rows.length ? rows.map(function (t) {
      var d = CO.dept(t.dept_id);
      var res = t.status === 'running' ? 'running · attempt ' + t.attempt + ' of 3' : t.last_error && t.status !== 'done' ? '<span class="err">Last error: ' + esc(t.last_error) + '</span>' + (t.status === 'queued' ? ' · ' + esc(CO.waitText(t)) : '') : esc(t.outcome || (t.status === 'queued' ? CO.waitText(t) : ''));
      var tr = '<tr class="row" data-task="' + t.id + '"><td><span class="st ' + t.status + '">' + esc(TSTAT[t.status]) + '</span></td><td>' + esc(d ? d.name : 'removed') + '</td>' +
        '<td><span class="id">#' + t.id + '</span><b>' + esc(t.title) + '</b></td><td class="num">' + (t.started_at ? dayTime(t.started_at) : '—') + '</td><td class="num">' + t.turns + '</td>' +
        '<td class="num">' + (t.units ? u2(t.units) : '—') + '</td><td class="res">' + res + '</td></tr>';
      if (ui.open[t.id]) {
        tr += '<tr class="det"><td></td><td colspan="6"><b>Brief:</b> ' + esc(t.brief) + '<br><b>Result:</b> ' + esc(t.outcome || 'No output yet.') +
          (t.last_error ? '<br><b class="red">Last error:</b> ' + esc(t.last_error) : '') + '<br><b>Expert:</b> ' + esc(CO.expertName(t.expert || '')) +
          ' · <b>created</b> ' + dayTime(t.created_at) + (t.finished_at ? ' → ' + dayTime(t.finished_at) : '') + ' · <b>why</b> ' + esc(t.why || '—') + '</td></tr>';
      }
      return tr;
    }).join('') : '<tr><td colspan="7" class="empty">No tasks match.</td></tr>');
  }
  function renderApprovals() {
    var S = CO.S;
    setHTML($('appr-full'), S.approvals.length ? S.approvals.map(function (a) { return apprCard(a, true); }).join('') : '<p class="empty ok">Nothing is waiting for you.</p>');
    S.approvals.forEach(function (a) { ui.seen[a.id] = 1; });
    setHTML($('appr-done'), S.decided.length ? S.decided.map(function (a) {
      var d = CO.dept(a.dept_id), ok = a.decision === 'approve';
      return '<div class="card"><div class="t" style="display:flex;gap:6px;align-items:center;font-size:10.5px;color:var(--dim2)"><span class="st ' + (ok ? 'done' : 'failed') + '">' + (ok ? 'approved' : 'rejected') + '</span>' +
        '<span class="tag">' + esc(d ? d.name : '') + '</span><span class="tag k">' + esc(a.kind) + '</span>' + hhmm(a.decided_at) + '</div><p style="margin-top:6px;font-weight:600">' + esc(a.summary) + '</p></div>';
    }).join('') : '<p class="empty">Nothing decided yet in this session.</p>');
  }
  function renderMemory() {
    var S = CO.S, q = ui.memQ.toLowerCase();
    $('mem-sub').textContent = S.memory.length + ' items · ' + S.departments.length + ' departments';
    setHTML($('memory'), S.departments.map(function (d) {
      var items = S.memory.filter(function (m) { return m.dept_id === d.id && (!q || m.text.toLowerCase().indexOf(q) >= 0 || m.kind.indexOf(q) >= 0); }).sort(function (a, b) { return b.id - a.id; });
      if (!items.length && q) return '';
      return '<div class="card" data-mem="' + d.id + '"' + (ui.memDept === d.id ? ' style="border-color:var(--cyan)"' : '') + '><h3><i class="dot ' + CO.deptView(d).status + '"></i>' + esc(d.name) + ' <small>' + items.length + '</small></h3>' +
        (items.length ? items.map(function (m) { return '<div class="mem"><span class="' + m.kind + '">' + esc(m.kind) + '</span><div>' + esc(m.text) + '<i>' + CO.ago(m.at) + '</i></div></div>'; }).join('') : '<p class="empty">Nothing remembered yet.</p>') + '</div>';
    }).join('') || '<p class="empty">Nothing matches.</p>');
  }
  function renderAudit() {
    var S = CO.S, A = S.audit, days = Math.max(0, Math.ceil((A.next_at - S.clock) / 86400000));
    var stuck = S.tasks.filter(function (t) { return t.status === 'queued' && S.clock - t.created_at > 45 * 60000; }).length;
    var html = '<div class="kpis"><div><b class="cy">' + days + 'd</b><span>next audit · ' + dayTime(A.next_at) + '</span></div><div><b>' + (A.last ? A.last.findings.length : 0) + '</b><span>findings last week</span></div>' +
      '<div><b class="' + (stuck ? 'red' : 'gr') + '">' + stuck + '</b><span>queued over 45 min now</span></div><div><b>' + S.departments.length + '</b><span>departments it reads</span></div></div>';
    html += A.last ? '<div class="card"><h3>Last audit · ' + dayTime(A.last.at) + '</h3>' + A.last.findings.map(function (f) {
      return '<div class="finding"><span><span class="tag k">' + esc(f.kind) + '</span></span><div>' + esc(f.detail) + (f.fix ? '<div class="fix">→ ' + esc(f.fix) + '</div>' : '') + '</div></div>';
    }).join('') + '</div>' : '<p class="empty">No audit yet: the first one runs a week after setup.</p>';
    setHTML($('audit'), html);
  }
  function renderInvest() {
    var S = CO.S, on = S.company.investable, done = 0, failed = 0, units = 0;
    S.departments.forEach(function (d) { var v = CO.deptView(d); done += v.done; failed += v.failed; units += v.units; });
    var html = '<div class="switch' + (on ? ' on' : '') + '" data-a="invest"><span class="sw"></span><div><b>' + (on ? 'Investable' : 'Private') + '</b><span>' +
      (on ? 'Backers can pledge USDC; the scoreboard below is public.' : 'Nobody else sees this company. Flip to make it investable.') + '</span></div></div>';
    if (on) {
      html += '<div class="sec" style="margin:16px 0 8px">PUBLIC SCOREBOARD · cymetica.com/company/' + S.company.id + '</div>' +
        '<div class="kpis"><div><b class="gr">' + done + '</b><span>tasks done · 7d</span></div><div><b class="red">' + failed + '</b><span>failed · 7d</span></div>' +
        '<div><b>' + u2(units) + '</b><span>units · 7d</span></div><div><b class="cy">' + S.approved_7d + '</b><span>approved · 7d</span></div></div>' +
        '<div class="kpis"><div><b>0</b><span>USDC pledged</span></div><div><b>0</b><span>backers</span></div><div><b>—</b><span>proceeds so far</span></div><div><b>' + S.departments.length + '</b><span>departments</span></div></div>';
    }
    setHTML($('invest'), html);
  }
  var DOMS = ['Cayman Islands', 'Delaware (US)', 'Wyoming (US)', 'Estonia', 'Singapore', 'Switzerland', 'British Virgin Islands', 'Marshall Islands',
    'Moon (through an Earth registry)', 'Mars (through an Earth registry)', 'Europa (through an Earth registry)', 'Titan (through an Earth registry)'];
  function renderLegal() {
    var S = CO.S, L = S.legal;
    if ($('legal')._h) return;
    setHTML($('legal'), '<div class="cols2"><div class="card"><h3>Entity</h3><div class="form">' +
      '<label class="field">Domicile<select id="lg-dom">' + DOMS.map(function (x) { return '<option' + (x === L.domicile ? ' selected' : '') + '>' + x + '</option>'; }).join('') + '</select></label>' +
      '<label class="field">Name<input id="lg-name" value="' + esc(L.name) + '"></label>' +
      '<label class="field">Share classes<input value="Ordinary, Preferred"></label><label class="field">Founders<input value="expire76 · 100%"></label>' +
      '<label class="field">Option pool<input value="10%"></label><label class="field">Directors<input value="expire76"></label>' +
      '<label class="field full">Governance<select><option>The owner decides</option><option>Board of directors</option><option>Token holders vote</option></select></label></div>' +
      '<div class="mf"><span class="hint" title="Cymetica publishes the stake it takes in companies formed here.">Cymetica\'s published stake: 1–10%</span><span class="sp"></span><button class="btn gr" data-a="form">Start formation</button></div></div>' +
      '<div class="card"><h3>Step by step</h3>' + [['Name and domicile', 'done'], ['Founders, shares and option pool', 'done'], ['Directors and governance', 'running'], ['Documents to sign', 'queued'], ['Registry filing', 'queued']].map(function (s, i) {
        return '<div class="trow" style="cursor:default"><span><span class="st ' + s[1] + '">' + (s[1] === 'running' ? 'now' : s[1] === 'queued' ? 'next' : 'done') + '</span></span><div><b>' + (i + 1) + '. ' + s[0] + '</b></div><i></i></div>';
      }).join('<div style="height:6px"></div>') + '<p class="hint">Formation is paper until you approve the filing.</p></div></div>');
  }
  function renderToken() {
    var S = CO.S, T = S.token, ch = CO.CHAINS.filter(function (c) { return c.key === T.chain; })[0] || CO.CHAINS[0];
    setHTML($('token'), '<div class="cols2"><div class="card"><h3>Company token</h3>' +
      (T.reserved ? '<p style="margin-bottom:10px"><b class="gr">' + esc(T.symbol) + '</b> reserved on ' + esc(ch.name) + ' (gas in ' + esc(ch.currency) + '). Launch it when you are ready.</p>' :
        '<p class="hint" style="margin-bottom:10px">Give ' + esc(S.company.name) + ' a token: reserve the symbol now, launch it before, during or after the build.</p>') +
      '<div class="form"><label class="field">Chain<select id="tk-chain"' + (T.reserved ? ' disabled' : '') + '>' + CO.CHAINS.map(function (c) { return '<option value="' + c.key + '"' + (c.key === T.chain ? ' selected' : '') + '>' + c.name + ' (gas in ' + c.currency + ')</option>'; }).join('') + '</select></label>' +
      '<label class="field">Symbol<input id="tk-sym" maxlength="6" value="' + esc(T.symbol || 'CQA') + '"' + (T.reserved ? ' disabled' : '') + '></label></div>' +
      '<div class="mf"><span class="sp"></span>' + (T.reserved ? '<button class="btn" data-a="tk-undo">Release</button><button class="btn gr" data-a="tk-launch">Launch</button>' : '<button class="btn gr" data-a="tk-reserve">Reserve symbol</button>') + '</div></div>' +
      '<div class="card"><h3>Pre-IPO equity perp</h3><p class="hint" style="margin-bottom:10px">A perpetual on this company\'s equity, priced off its reference valuation.</p>' +
      (T.perp_listed ? '<div class="kpis" style="grid-template-columns:1fr 1fr"><div><b class="gr">CQA-PERP</b><span>listed</span></div><div><b>$250,000</b><span>reference valuation</span></div></div>' : '') +
      '<div class="mf"><span class="sp"></span>' + (T.perp_listed ? '<button class="btn cy" data-mock="Trade CQA-PERP">Open it</button>' : '<button class="btn cy" data-a="perp">List it</button>') + '</div></div></div>');
  }
  function renderSettings() {
    var S = CO.S, c = S.company, paused = c.status === 'paused';
    var keep = document.activeElement && $('settings').contains(document.activeElement);
    if (keep) return;
    setHTML($('settings'), '<div class="cols2"><div class="card"><h3>Company</h3><div class="form">' +
      '<label class="field">Name<input id="st-name" maxlength="60" value="' + esc(c.name) + '"></label>' +
      '<label class="field">Report style<select id="st-report">' + ['Short, numbers first', 'Daily digest', 'Every result'].map(function (x) { return '<option' + (x === c.report_style ? ' selected' : '') + '>' + x + '</option>'; }).join('') + '</select></label>' +
      '<label class="field full">Mission<textarea id="st-mission" maxlength="500">' + esc(c.mission) + '</textarea></label></div>' +
      '<div class="mf"><span class="sp"></span><button class="btn gr" data-a="st-save">Save</button></div></div>' +
      '<div><div class="card"><h3>Plan and running</h3>' +
      '<div class="switch' + (S.budget.extra.on ? ' on' : '') + '" data-a="extra"><span class="sw"></span><div><b>Extra usage ' + (S.budget.extra.on ? 'on' : 'off') + '</b><span>At 0 the company ' + (S.budget.extra.on ? 'keeps running on extra usage' : 'pauses until the reset') + '.</span></div></div>' +
      '<div style="height:10px"></div><div class="switch' + (paused ? '' : ' on') + '" data-a="pause"><span class="sw"></span><div><b>' + (paused ? 'Paused' : 'Active') + '</b><span>' + (paused ? 'Nothing new starts.' : 'The runner passes every two minutes.') + '</span></div></div>' +
      '<div class="mf"><span class="hint">Plan: <b>' + esc(c.plan) + '</b></span><span class="sp"></span><button class="btn cy" data-a="upgrade">Upgrade</button></div></div>' +
      '<div class="card danger"><h3 class="red">Danger zone</h3><p class="hint">Deleting the company cancels every open task and removes its memory. One company per account.</p>' +
      '<div class="mf"><span class="sp"></span><button class="btn rd" data-a="delete">Delete company</button></div></div></div></div>');
  }

  /* ---------------- the clock: the lines that count down ---------------- */
  var lastClock = 0;
  function clock(force) {
    var now = performance.now();
    if (!force && now - lastClock < 450) return;
    lastClock = now;
    var S = CO.S, b = S.budget, g = CO.gate(), last = null, i;
    for (i = S.strip.length - 1; i >= 0; i--) if (S.strip[i].state !== 'running') { last = S.strip[i].at; break; }
    var working = S.tasks.filter(function (t) { return t.status === 'running'; }).length;
    var parts = [last ? 'last turn <b>' + hhmm(last) + '</b>' : 'no turn yet'];
    if (S.company.status === 'paused') parts.push('<span class="stop">paused</span>');
    else if (!g.ok) parts.push('<span class="stop">' + esc(g.text + (g.until ? ' until ' + hhmm(g.until) : '')) + '</span>');
    else {
      if (working) parts.push('<span class="hot">' + working + ' working</span>');
      parts.push('next pass in <b>' + Math.max(0, Math.ceil((S.next_pass_at - S.clock) / 1000)) + 's</b>');
      if (g.code === 'extra') parts.push('<span class="hot">on extra usage</span>');
    }
    $('co-heart').innerHTML = parts.join(' · ');
    var ur = $('us-r');
    ur.textContent = g.code === 'extra' ? 'on extra usage · resets in ' + hm(b.session.resets_at - S.clock) : 'Resets in ' + hm(b.session.resets_at - S.clock);
    ur.classList.toggle('ex', g.code === 'extra');
    $('uw-r').textContent = 'Resets ' + dayTime(b.week.resets_at);
    $('day-r').textContent = 'Resets 00:00';
    var lv = $('live');
    if (S.company.status === 'paused') { lv.className = 'live paused'; lv.innerHTML = '<i></i>PAUSED'; }
    else if (!g.ok) { lv.className = 'live stop'; lv.innerHTML = '<i></i>' + esc(g.text.toUpperCase()); }
    else { lv.className = 'live'; lv.innerHTML = '<i></i>LIVE · ' + (working ? working + ' WORKING' : 'WAITING FOR THE NEXT PASS'); }
    Array.prototype.forEach.call(document.querySelectorAll('[data-wait]'), function (el) {
      var d = CO.dept(+el.getAttribute('data-wait')); if (!d) return;
      var v = CO.deptView(d); if (v.waits) el.textContent = v.waits;
    });
  }

  /* ---------------- tooltips over the office and the network ---------------- */
  function tipFor(kind, key) {
    var S = CO.S, c = CO.counts();
    if (kind === 'agent') {
      var p = key.split(':'), rk = p[0], i = +p[1];
      if (rk === 'hub') return '<b>Manager</b> · routes ' + c.open + ' open<br>' + (S.company.status === 'paused' ? 'paused' : 'plans the next pass · click to message it');
      if (rk === 'you') return '<b>You</b> · ' + (S.approvals.length ? '<span class="r">' + S.approvals.length + ' to approve</span>' : 'nothing waits for you');
      if (rk === 'audit') return '<b>Supervisor</b> · runs the weekly audit';
      var d = CO.dept(+rk.slice(1)); if (!d) return '';
      var v = CO.deptView(d), e = v.experts[i]; if (!e) return '';
      return '<b>' + esc(e.name) + '</b> · ' + esc(d.name) + '<br>' + (e.state === 'working' && v.running ? '<span class="c">working</span> on “' + esc(v.running.title) + '” · attempt ' + v.running.attempt + ' of 3' : 'idle');
    }
    if (key === 'hub') return '<b>Manager</b> · <span class="c">' + c.open + ' open</span> · ' + (S.approvals.length ? '<span class="r">' + S.approvals.length + ' wait for you</span>' : 'nothing waits') + '<br>click to message it';
    if (key === 'you') return '<b>Your desk</b> · ' + (S.approvals.length ? '<span class="r">' + S.approvals.length + ' approvals waiting</span>' : 'all clear') + '<br>click to open Approvals';
    if (key === 'audit') {
      var A = S.audit;
      return '<b>Weekly audit</b> · next in ' + Math.max(0, Math.ceil((A.next_at - S.clock) / 86400000)) + 'd · ' + (A.last ? A.last.findings.length : 0) + ' findings last week<br>click to open Audit';
    }
    if (key === 'lot') return '<b>Add a department</b><br>click to staff a new room';
    var dd = CO.dept(+String(key).slice(1)); if (!dd) return '';
    var vv = CO.deptView(dd), col = { working: 'c', queued: 'bl', waiting: 'r', idle: '' }[vv.status];
    return '<b>' + esc(dd.name) + '</b> · <span class="' + col + '">' + WORD[vv.status] + '</span> · ' + vv.open + ' open · ' + vv.done + ' done' + (vv.failed ? ' · <span class="r">' + vv.failed + ' failed</span>' : '') +
      '<br>' + (vv.running ? 'Now: “' + esc(vv.running.title) + '”' : vv.waits ? 'Queued: ' + esc(vv.waits) : vv.waiting ? '<span class="r">waits for your approval</span>' : 'nothing queued') + '<br><span style="color:var(--dim2)">click to open</span>';
  }

  /* ---------------- modals and toasts ---------------- */
  var modalAct = null;
  function openModal(html, wide, act) {
    var card = $('modal-card');
    card.className = 'modal-card' + (wide ? ' wide' : '');
    card.innerHTML = html; modalAct = act || null;
    $('modal').hidden = false;
    var f = card.querySelector('input,textarea'); if (f) setTimeout(function () { f.focus(); }, 30);
  }
  function closeModal() { $('modal').hidden = true; modalAct = null; }
  var toastT = 0;
  function toast(text) {
    var t = $('toast'); t.textContent = text; t.hidden = false;
    clearTimeout(toastT); toastT = setTimeout(function () { t.hidden = true; }, 2600);
  }
  function readModal(id) {
    var a = CO.S.approvals.filter(function (x) { return x.id === id; })[0]; if (!a) return;
    var d = CO.dept(a.dept_id);
    openModal('<div class="mh"><span class="tag">' + esc(d ? d.name : '') + '</span><span class="' + (a.kind === 'real-money action' ? 'tag money' : 'tag k') + '">' + esc(a.kind) + '</span><h3>' + esc(a.summary) + '</h3></div>' +
      '<div class="draft" style="max-height:52vh">' + fmtDraft(a.body) + '</div>' +
      '<div class="mf"><span class="hint">asked ' + CO.ago(a.created_at) + ' ago</span><span class="sp"></span><button class="btn" data-a="close">Close</button>' +
      '<button class="btn rd" data-a="reject">Reject</button><button class="btn gr" data-a="approve">Approve</button></div>', true, function (act) {
      if (act === 'approve' || act === 'reject') { closeModal(); decide(a.id, act); }
    });
  }
  function deptForm(o, edit) {
    var tpls = edit ? '' : '<div class="tpls">' + CO.TEMPLATES.map(function (t) {
      var used = CO.S.departments.some(function (d) { return d.key === t.key && t.key !== 'custom'; });
      return '<button class="tpl' + (t.key === o.key ? ' on' : '') + (used ? ' used' : '') + '" data-tpl="' + t.key + '"><b>' + (t.name || 'Custom') + '</b><span>' +
        (t.key === 'custom' ? 'your own name, charter and experts' : t.experts.map(CO.expertName).join(' · ')) + (used ? ' · you have one' : '') + '</span></button>';
    }).join('') + '</div>';
    return tpls + '<div class="form"><label class="field">Department name<input id="df-name" maxlength="60" value="' + esc(o.name) + '" placeholder="e.g. Growth"></label>' +
      '<div class="field">Experts<div class="xchips" id="df-ex">' + CO.EXPERTS.map(function (e) { return '<span class="xchip' + (o.experts.indexOf(e.key) >= 0 ? ' on' : '') + '" data-ex="' + e.key + '">' + e.name + '</span>'; }).join('') + '</div></div>' +
      '<label class="field full"><span>Charter · your rules, notes and lessons <span id="df-n" style="float:right">' + o.charter.length + ' / 2,000</span></span><textarea id="df-ch" maxlength="2000" rows="6">' + esc(o.charter) + '</textarea></label></div>';
  }
  function readDeptForm() {
    return {
      name: $('df-name').value.trim(), charter: $('df-ch').value.trim(),
      experts: Array.prototype.map.call(document.querySelectorAll('#df-ex .xchip.on'), function (x) { return x.getAttribute('data-ex'); })
    };
  }
  function addDeptModal() {
    var o = { key: 'custom', name: '', experts: ['researcher'], charter: '' };
    var free = CO.TEMPLATES.filter(function (t) { return t.key !== 'custom' && !CO.S.departments.some(function (d) { return d.key === t.key; }); })[0];
    if (free) o = { key: free.key, name: free.name, experts: free.experts.slice(), charter: free.charter };
    function draw() {
      openModal('<div class="mh"><h3>Add a department</h3><button class="btn" data-a="close">×</button></div>' + deptForm(o, false) +
        '<div class="mf"><span class="hint">Its first task starts from this charter.</span><span class="sp"></span><button class="btn" data-a="close">Cancel</button><button class="btn gr" data-a="create">Create department</button></div>', true, act);
    }
    function act(a, el) {
      if (a === 'tpl') {
        var t = CO.TEMPLATES.filter(function (x) { return x.key === el.getAttribute('data-tpl'); })[0];
        o = { key: t.key, name: t.name, experts: t.experts.slice(), charter: t.charter }; draw();
      } else if (a === 'create') {
        var f = readDeptForm();
        if (!f.name) { $('df-name').focus(); $('df-name').style.borderColor = 'var(--red)'; return; }
        closeModal();
        var d = CO.act.addDept({ key: o.key, name: f.name, experts: f.experts, charter: f.charter });
        toast('New department: ' + d.name + '. Its room is being built.');
      }
    }
    draw();
  }
  function editDeptModal(id) {
    var d = CO.dept(id); if (!d) return;
    openModal('<div class="mh"><h3>Edit department</h3><button class="btn" data-a="close">×</button></div>' + deptForm({ key: d.key, name: d.name, experts: d.experts.slice(), charter: d.charter }, true) +
      '<div class="mf"><button class="btn rd" data-a="remove">Remove department</button><span class="sp"></span><button class="btn" data-a="close">Cancel</button><button class="btn gr" data-a="save">Save</button></div>', true, function (a) {
      if (a === 'save') { var f = readDeptForm(); if (!f.name) return; closeModal(); CO.act.editDept(id, f); ui.dirty = false; $('dr-ch-text').value = CO.dept(id).charter; renderDrawer(); }
      if (a === 'remove') {
        openModal('<div class="mh"><h3>Remove ' + esc(d.name) + '?</h3></div><p>Its open tasks are cancelled and its room is cleared. Its memory stays readable in the Memory tab.</p>' +
          '<div class="mf"><span class="sp"></span><button class="btn" data-a="close">Cancel</button><button class="btn rd" data-a="really">Remove</button></div>', false, function (b) {
          if (b === 'really') { closeModal(); closeDrawer(); CO.act.removeDept(id); toast(d.name + ' removed.'); }
        });
      }
    });
  }
  function upgradeModal() {
    openModal('<div class="mh"><h3>Your NEXUS build plan</h3><button class="btn" data-a="close">×</button></div>' +
      '<div class="plans"><div class="on"><b>Pro</b><span>your plan · 1.00 u a session, 6.00 u a week</span></div><div><b>Max 5x</b><span>5× the units of Pro</span></div><div><b>Max 20x</b><span>20× the units of Pro</span></div></div>' +
      '<p class="hint" style="margin-top:12px">Your agents run on your plan; each turn is metered to your account, never the platform\'s. Plans and prices are on /usage.</p>' +
      '<div class="mf"><span class="sp"></span><button class="btn" data-a="close">Close</button><button class="btn cy" data-a="usage">Open /usage</button></div>', false, function (a) {
      if (a === 'usage') { closeModal(); toast('Mockup: /usage is another page.'); }
    });
  }

  /* ---------------- actions ---------------- */
  function decide(id, how) {
    var els = document.querySelectorAll('.ai[data-id="' + id + '"]');
    Array.prototype.forEach.call(els, function (el) { el.classList.add('leaving'); });
    setTimeout(function () { CO.act.decide(id, how); toast(how === 'approve' ? 'Approved: it goes out now.' : 'Rejected: nothing is sent.'); }, els.length ? 230 : 0);
  }
  function sendMessage(text) {
    if (!text) return;
    CO.act.message(text);
    office.packet('you', 'hub', 'blue');
  }

  function bind() {
    document.addEventListener('click', function (e) {
      var t = e.target;
      var mock = t.closest('[data-mock]');
      if (mock) { e.preventDefault(); toast('Mockup: ' + mock.getAttribute('data-mock') + ' is another page.'); return; }
      var tab = t.closest('#tabs button'); if (tab) return setTab(tab.getAttribute('data-tab'));
      if (t.closest('#co-pause')) { CO.act.pause(); toast(CO.S.company.status === 'paused' ? 'Paused: a running turn finishes, nothing new starts.' : 'Resumed: the next pass starts in a few seconds.'); return; }
      if (t.closest('#co-waiting')) return setTab('approvals');
      if (t.closest('#co-upgrade')) return upgradeModal();
      if (t.closest('#add-dept') || t.closest('#rail-add')) return addDeptModal();
      var row = t.closest('.dept'); if (row) return ui.panel === +row.getAttribute('data-id') ? closeDrawer() : openDrawer(+row.getAttribute('data-id'));
      var dd = t.closest('[data-d]');
      if (dd && dd.closest('.ai')) return decide(dd.closest('.ai').getAttribute('data-id'), dd.getAttribute('data-d'));
      var rd = t.closest('[data-r]'); if (rd) return readModal(rd.closest('.ai').getAttribute('data-id'));
      var pa = t.closest('.plan [data-a]');
      if (pa) {
        var id = +pa.closest('li').getAttribute('data-id'), a = pa.getAttribute('data-a');
        if (a === 'remove') { var tk = CO.task(id); CO.act.remove(id); toast('Removed from the plan: ' + (tk ? tk.title : '')); }
        else { ui.moved = id; CO.act.move(id, a); }
        return;
      }
      if (t.closest('#z-in')) return office.zoom(0.78);
      if (t.closest('#z-out')) return office.zoom(1.28);
      if (t.closest('#z-fit')) return office.fit(true);
      // the drawer
      var dra = t.closest('#drawer [data-a]');
      if (dra) {
        var x = dra.getAttribute('data-a');
        if (x === 'close') return closeDrawer();
        if (x === 'edit') return editDeptModal(ui.panel);
        if (x === 'prods') {
          var list = $('dr-prods').value.split(',').map(function (s) { return s.trim(); }).filter(Boolean);
          CO.act.products(ui.panel, list); $('dr-prods').blur(); renderDrawer(); return toast('Products saved: every run tests ' + (list.join(', ') || 'the public site') + '.');
        }
        if (x === 'runnow') { var rr = CO.act.runNow(ui.panel); return toast(rr ? 'Run queued at the top: it starts on the next pass.' : 'A run is already queued or running.'); }
        if (x === 'appr') { var first = $('dr-appr').querySelector('.ai'); if (first) first.scrollIntoView({ behavior: 'smooth', block: 'center' }); return; }
      }
      var tr = t.closest('.trow[data-task], tr.row[data-task]');
      if (tr) { var tid = +tr.getAttribute('data-task'); ui.open[tid] = !ui.open[tid]; return render(); }
      if (t.closest('#dr-tasks-all')) { ui.tfDept = String(ui.panel); ui.tfStatus = ''; return setTab('tasks'); }
      if (t.closest('#dr-mem-all')) { ui.memDept = ui.panel; setTab('memory'); var c = document.querySelector('[data-mem="' + ui.memDept + '"]'); if (c) c.scrollIntoView({ block: 'start' }); return; }
      if (t.closest('#dr-ch-discard')) { ui.dirty = false; $('dr-ch-text').value = CO.dept(ui.panel).charter; charterMeta(); return; }
      // the other tabs
      var pa2 = t.closest('.page [data-a]');
      if (pa2) return pageAct(pa2.getAttribute('data-a'));
      // modal
      if (t.id === 'modal') return closeModal();
      var ma = t.closest('#modal-card [data-a]');
      if (ma) { var m = ma.getAttribute('data-a'); if (m === 'close') return closeModal(); if (modalAct) modalAct(m, ma); return; }
      var tp = t.closest('#modal-card [data-tpl]'); if (tp && modalAct) return modalAct('tpl', tp);
      var xc = t.closest('#modal-card .xchip'); if (xc) { xc.classList.toggle('on'); return; }
      // sim bar
      var sb = t.closest('#simbar [data-speed]');
      if (sb) {
        var v = +sb.getAttribute('data-speed');
        CO.sim.running = v > 0; if (v) CO.sim.speed = v;
        Array.prototype.forEach.call(document.querySelectorAll('#simbar [data-speed]'), function (b) { b.classList.toggle('on', b === sb); });
        return toast(v ? 'Simulation at ' + v + '×' : 'Simulation frozen');
      }
      if (t.closest('#sim-reset')) { CO.reset(); return toast('Simulation started over.'); }
    });
    $('compose').addEventListener('submit', function (e) { e.preventDefault(); var i = $('msg'); sendMessage(i.value.trim()); i.value = ''; });
    $('dr-charter').addEventListener('submit', function (e) {
      e.preventDefault(); var d = CO.dept(ui.panel); if (!d) return;
      CO.act.charter(d.id, $('dr-ch-text').value.trim()); ui.dirty = false; charterMeta(); toast('Charter saved: the next task of ' + d.name + ' starts from it.');
    });
    $('dr-ch-text').addEventListener('input', function () { ui.dirty = true; charterMeta(); });
    $('tf-dept').addEventListener('change', function (e) { ui.tfDept = e.target.value; renderTasks(); });
    $('tf-status').addEventListener('change', function (e) { ui.tfStatus = e.target.value; renderTasks(); });
    $('mem-q').addEventListener('input', function (e) { ui.memQ = e.target.value; renderMemory(); });
    document.addEventListener('input', function (e) { if (e.target.id === 'df-ch') { var n = $('df-n'); if (n) n.textContent = e.target.value.length + ' / 2,000'; } });
    document.addEventListener('change', function (e) {
      if (e.target.id === 'tk-chain') CO.S.token.chain = e.target.value;
      if (e.target.id === 'lg-dom') { CO.S.legal.domicile = e.target.value; toast('Domicile: ' + e.target.value); }
    });
    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape') return;
      if (!$('modal').hidden) return closeModal();
      if (ui.panel != null) closeDrawer();
    });
  }
  function pageAct(a) {
    var S = CO.S;
    if (a === 'invest') { S.company.investable = !S.company.investable; CO.changed(); toast(S.company.investable ? 'Investable: the scoreboard is public.' : 'Private again.'); }
    if (a === 'form') openModal('<div class="mh"><h3>Start formation?</h3></div><p>' + esc(S.legal.domicile) + ' · ' + esc(($('lg-name') || {}).value || S.legal.name) + '. Filing waits for your approval like everything real.</p>' +
      '<div class="mf"><span class="sp"></span><button class="btn" data-a="close">Cancel</button><button class="btn gr" data-a="go">Start</button></div>', false, function (b) { if (b === 'go') { closeModal(); toast('Mockup: nothing is filed.'); } });
    if (a === 'tk-reserve') { S.token.symbol = ($('tk-sym').value || 'CQA').toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 6); S.token.chain = $('tk-chain').value; S.token.reserved = true; CO.changed(); toast(S.token.symbol + ' reserved.'); }
    if (a === 'tk-undo') { S.token.reserved = false; CO.changed(); }
    if (a === 'tk-launch') toast('Mockup: the launch page is another page.');
    if (a === 'perp') { S.token.perp_listed = true; CO.changed(); toast('Listed: CQA-PERP.'); }
    if (a === 'st-save') { CO.act.settings({ name: $('st-name').value.trim() || S.company.name, mission: $('st-mission').value.trim(), report_style: $('st-report').value }); document.activeElement.blur(); renderSettings(); toast('Settings saved.'); }
    if (a === 'extra') { CO.act.extra(!S.budget.extra.on); toast('Extra usage ' + (S.budget.extra.on ? 'on' : 'off') + '.'); }
    if (a === 'pause') CO.act.pause();
    if (a === 'upgrade') upgradeModal();
    if (a === 'delete') openModal('<div class="mh"><h3 class="red">Delete ' + esc(S.company.name) + '?</h3></div><p>Every open task is cancelled and its memory is removed. In this mockup it starts the simulation over.</p>' +
      '<div class="mf"><span class="sp"></span><button class="btn" data-a="close">Cancel</button><button class="btn rd" data-a="del">Delete</button></div>', false, function (b) { if (b === 'del') { closeModal(); CO.reset(); toast('Mockup: started over.'); } });
  }

  /* ---------------- the live events: packets in the office and the network ---------------- */
  function expertIdx(t, d) { var i = d.experts.indexOf(t.expert); return i < 0 ? 0 : Math.min(i, 2); }
  function wire() {
    CO.on('turn:start', function (e) {
      office.packet('hub', 'd' + e.dept.id, 'cyan');
     
    });
    CO.on('turn:end', function (e) {
      var col = { done: 'green', failed: 'red', ask: 'red', 'continue': 'cyan' }[e.outcome] || 'cyan';
      office.packet('d' + e.dept.id, 'hub', col);
     
      if (e.outcome === 'ask') { office.packet('hub', 'you', 'red', 1400); }
    });
    CO.on('approval:decided', function (e) {
      if (!e.dept) return;
      if (e.decision === 'approve') { office.packet('you', 'hub', 'green'); office.packet('hub', 'd' + e.dept.id, 'green', 1100); }
      else { office.packet('you', 'hub', 'red'); }
    });
    CO.on('submitted', function (e) { if (e.dept) { office.packet('d' + e.dept.id, 'hub', 'green'); } });
    CO.on('message', function () { office.packet('hub', 'you', 'cyan'); });
    CO.on('dept:new', function (d) { office.layout({ born: d.id }); setTimeout(function () { office.fit(true); }, 60); });
    CO.on('dept:edit', function () { office.layout(); });
    CO.on('dept:removed', function () { office.layout(); setTimeout(function () { office.fit(true); }, 60); });
    CO.on('reset', function () {
      closeModal(); ui.panel = null; $('drawer').hidden = true; office.sel = null; ui.open = {}; ui.prev = {};
      office.layout(); office.fit(true); markSeen();
      ['depts', 'appr', 'plan', 'msgs', 'feed', 'legal', 'settings'].forEach(function (id) { $(id)._h = null; });
    });
    CO.on('office:click', function (key) {
      if (key.charAt(0) === 'd') return openDrawer(+key.slice(1));
      if (key === 'hub') { var m = $('msg'); m.focus(); m.parentNode.classList.remove('bump'); return; }
      if (key === 'you') return setTab('approvals');
      if (key === 'audit') return setTab('audit');
      if (key === 'lot') return addDeptModal();
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
