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
  var TSTAT = { queued: 'next', running: 'working', waiting_approval: 'needs you', done: 'done', failed: 'failed', cancelled: 'cancelled' };

  var ui = { tab: 'office', view: '2d', panel: null, open: {}, seen: {}, feedTop: 0, dirty: false, prev: {}, tfDept: '', tfStatus: '', memQ: '', memDept: null };
  var office, office2d = null, office3d = null, officePic = null;
  // RO: someone else's public company, looked at from the Universe; everything shows, nothing changes
  var RO = false;

  /* ---------------- the office: flat or in 3D, the same API either way ---------------- */
  function viewPref() { try { return localStorage.getItem('co.view') || 'pic'; } catch (e) { return 'pic'; } }
  // the operator's picture of the office stands only while the company is the one it shows (opic.js)
  function picFits() { return !!(CO.OfficePic && CO.OfficePic.fits(CO.S)); }
  function liveView() { return CO.U3 && CO.U3.ok && CO.U3.office ? '3d' : '2d'; }
  function setView(v, save) {
    if (v === 'pic' && !picFits()) v = liveView();
    if (v === '3d' && !(CO.U3 && CO.U3.ok && CO.U3.office)) v = '2d';
    if (save) { try { localStorage.setItem('co.view', v); } catch (e) { /* fine */ } }
    ui.view = v;
    var st = $('stage');
    st.classList.toggle('is3d', v === '3d'); st.classList.toggle('ispic', v === 'pic');
    Array.prototype.forEach.call(document.querySelectorAll('#vt button'), function (b) { b.classList.toggle('on', b.getAttribute('data-v') === v); });
    if (v === '3d') {
      if (!office3d) { office3d = CO.U3.office($('office3d'), st, tipFor); office3d.onFail = function () { office3d = null; setView('2d'); }; }
      office = office3d;
    } else if (v === 'pic') {
      if (!officePic) { officePic = new CO.OfficePic($('opic'), st, tipFor); officePic.onUnfit = function () { setView(liveView()); }; }
      office = officePic;
    } else office = office2d;
    var pb = document.querySelector('#vt [data-v="pic"]'); if (pb) { pb.disabled = !picFits(); pb.title = picFits() ? 'The office as its picture' : 'The picture shows the five departments it was drawn with'; }
    office.sel = ui.mgr ? 'hub' : ui.panel != null ? 'd' + ui.panel : null;
    office.layout();
    requestAnimationFrame(function () {
      office.resize();
      if (ui.mgr) office.focus('hub', 0, true); else if (ui.panel != null) office.focus('d' + ui.panel, 0, true); else office.fit(false);
    });
  }
  // the 3D engine loads on its own: switch when it is there, if 3D is the choice
  function whenEngine(cb) {
    var t0 = Date.now();
    (function wait() { if (CO.U3 && (CO.U3.ok || CO.U3.failed)) return cb(!!CO.U3.ok); if (Date.now() - t0 > 8000) return cb(false); setTimeout(wait, 80); })();
  }

  /* ---------------- boot ---------------- */
  function boot() {
    CO.S = CO.fresh(Date.now());
    RO = !!CO.RO;
    CO.applySetup();
    if (RO) roSetup();
    office = office2d = new CO.Office($('office'), $('stage'), tipFor);
    office.layout();
    Array.prototype.forEach.call(document.querySelectorAll('#vt button'), function (b) { b.classList.toggle('on', b.getAttribute('data-v') === '2d'); });
    if (viewPref() === 'pic' && picFits()) setView('pic');
    whenEngine(function (ok) { if (ok && (viewPref() === '3d' || (viewPref() === 'pic' && !picFits()))) setView('3d'); });
    markSeen();
    bind();
    wire();
    CO.on('change', render);
    CO.on('tick', clock);
    render();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { office.fit(false); $('msgs').scrollTop = 1e6; });
    window.addEventListener('resize', function () { $('msgs').scrollTop = 1e6; });
    if (CO.denied) setTimeout(function () { toast(CO.denied); }, 500);
    if (CO.MODE === 'new') setTimeout(createCompanyModal, 300);
    if (CO.Q.has('created')) setTimeout(function () { toast('Created: ' + CO.S.company.name + '. Add its first department.'); addDeptModal(); }, 600);
    if (location.hash === '#universe') setTab('universe');
    // back from a visit through the browser's cache: the page comes back as it was left, fade and all
    window.addEventListener('pageshow', function (e) { if (e.persisted) $('uvfade').hidden = true; });
  }
  // the visitor's frame: a bar saying whose company this is and that it is read only
  function roSetup() {
    var c = CO.S.company;
    document.body.classList.add('ro');
    $('robar').hidden = false;
    $('ro-t').innerHTML = 'Inside <b>' + esc(c.name) + '</b> by <b>@' + esc(c.owner) + '</b><em>· you can look at everything; only its owner can change it</em>';
    document.title = c.name + ' · Universe';
    var ap = document.querySelector('#tabs [data-tab="approvals"] .tl'); if (ap) ap.textContent = 'Waits for owner';
    var rs = document.querySelector('[data-pane="rules"] .sub'); if (rs) rs.textContent = 'the processes its owner wrote';
    var as = document.querySelector('[data-pane="approvals"] .sub'); if (as) as.textContent = 'What its departments asked the owner, and what the owner decided.';
    $('dr-ch-text').readOnly = true;
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
    var st = $('co-status'); st.textContent = paused ? 'PAUSED' : 'RUNNING'; st.className = 'pill ' + (paused ? 'off' : 'on');
    $('co-pause').textContent = paused ? 'Resume' : 'Pause';
    // what the company earned lives in its vault (the office and the right column), not in this bar
    var n = S.approvals.length, w = $('co-waiting');
    w.innerHTML = n ? '<b>' + n + '</b> ' + (RO ? 'wait' + (n === 1 ? 's' : '') + ' for its owner' : 'need' + (n === 1 ? 's' : '') + ' you') : '✓ all clear';
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
    $('tn-rules').textContent = S.rules ? S.rules.filter(function (r) { return r.on; }).length : '';
  }

  function renderRail() {
    var S = CO.S;
    $('rail-n').textContent = S.departments.length;
    var cc = CO.counts();
    // Each card says three things: who, what it is doing now, and one number. The rest is one click away.
    var na = S.approvals.length;
    var mrow = '<button class="dept mgrrow working" title="' + (RO ? 'Read its chat with the Manager' : 'Open your chat with the Manager') + '"><div class="d1"><i class="dot"></i><b>Manager</b>' +
      (na ? '<span class="et red">' + na + (RO ? ' wait for owner' : ' need' + (na === 1 ? 's' : '') + ' you') + '</span>' : '') + '</div>' +
      '<div class="dl"><span class="tx cyan">Chat · runs every department</span></div></button>';
    setHTML($('depts'), mrow + S.departments.map(function (d) {
      var v = CO.deptView(d), ln = CO.deptLine(d, v);
      return '<button class="dept ' + v.status + (ln.tone === 'red' ? ' needs' : '') + (ui.panel === d.id ? ' on' : '') + (d.born && S.clock - d.born < 4000 ? ' born' : '') + '" data-id="' + d.id + '">' +
        '<div class="d1"><i class="dot"></i><b>' + esc(d.name) + '</b>' +
        (d.files_as ? '<span class="et ' + (d.et10 ? 'lit' : 'zero') + '" title="ET10 Cymetica paid for accepted bugs, to ' + esc(d.files_as) + '">' + (d.et10 ? '+' : '') + (d.et10 || 0).toLocaleString('en-US') + ' ET10</span>' : '') + '</div>' +
        '<div class="dl"><span class="tx ' + ln.tone + '" title="' + esc(ln.text) + '">' + esc(ln.text) + '</span>' +
        '<span class="sp' + (v.capped ? ' hot' : '') + '" title="Spent of your plan today' + (v.cap ? ', of its ' + CO.fmtTok(v.cap) + ' daily cap' : '') + '">' + CO.fmtTok(v.tokToday) + '<small>today</small></span></div>' +
        (v.cap ? '<span class="ubar capb"><i class="' + (v.capped ? 'hot' : '') + '" style="width:' + Math.min(100, v.tokToday / v.cap * 100).toFixed(0) + '%"></i></span>' : '') +
        (v.status === 'working' ? '<span class="run"><i></i></span>' : '') + '</button>';
    }).join(''));
  }

  // The bottom panel, the way Claude shows usage: one bar each for the 5-hour session, the week and
  // today's turns. A bar fills in one colour and turns red only near its limit.
  function renderStrip() {
    var S = CO.S, b = S.budget, cap = b.session.cap;
    var start = b.session.resets_at - b.session.every;
    var onExtra = S.strip.filter(function (c) { return c.at >= start && c.extra; }).length;
    var used = Math.min(b.session.used, cap), sp = Math.round(used / cap * 100), usp = $('us-p');
    usp.textContent = sp + '% used';
    usp.classList.toggle('hot', sp >= 85);
    var sb = $('us-bar'); sb.style.width = sp + '%'; sb.classList.toggle('hot', sp >= 85);
    var wp = Math.min(100, b.week.used / b.week.cap * 100);
    $('uw-p').textContent = Math.round(wp) + '% used';
    var wb = $('uw-bar'); wb.style.width = wp.toFixed(1) + '%'; wb.classList.toggle('hot', wp >= 85);
  }

  // what an approval is, in words a person uses
  var KIND_WORD = { 'BB request': 'Build it Better request', 'bug report': 'Bug report', 'real-money action': 'Real money',
    'seat request': 'Tournament seat', 'start?': 'Start it?', 'review': 'Check the result' };
  function kindWord(k) { return KIND_WORD[k] || k; }
  function plainTitle(s) { return String(s || '').replace(/^(BB request|Seat|Real trade|Handle): /, ''); }
  function apprCard(a, full) {
    var d = CO.dept(a.dept_id), isNew = !ui.seen[a.id];
    var kind = a.kind === 'real-money action' ? 'tag money' : a.kind === 'review' || a.kind === 'start?' ? 'tag rvk' : 'tag k';
    return '<div class="ai' + (isNew ? ' new' : '') + '" data-id="' + a.id + '"><div class="t"><span class="' + kind + '">' + esc(kindWord(a.kind)) + '</span>' +
      '<span class="from">' + esc(d ? d.name : '') + ' · ' + esc(CO.ago(a.created_at)) + '</span></div><p>' + esc(plainTitle(a.summary)) + '</p>' + (full ? '<div class="draft">' + fmtDraft(a.body) + '</div>' : '') +
      '<div class="bt">' + (RO ? '<span class="wo">waits for its owner</span>' : '<button class="btn gr" data-d="approve">Approve</button><button class="btn rd" data-d="reject">Reject</button>') +
      (full ? '' : '<button class="btn" data-r="1">Read</button>') + '</div></div>';
  }
  function fmtDraft(body) {
    return String(body || '').split('\n\n').map(function (blk, i) {
      var lines = blk.split('\n'), head = i === 0 || (lines.length > 1 && lines[0].length < 30);
      return '<div>' + (head ? '<h4>' + esc(i ? lines[0].toUpperCase() : lines[0]) + '</h4>' + esc(lines.slice(1).join('\n')) : esc(blk)) + '</div>';
    }).join('');
  }
  function renderRight() {
    var S = CO.S, fd = ui.panel != null ? CO.dept(ui.panel) : null;
    var apprs = fd ? S.approvals.filter(function (a) { return a.dept_id === fd.id; }) : S.approvals, n = apprs.length;
    var head = RO ? 'WAITING FOR ITS OWNER' : 'NEEDS YOU';
    $('ap-t').textContent = fd ? head + ' · ' + fd.name.toUpperCase() : head;
    $('ap-n').textContent = n || '';
    $('p-appr').classList.toggle('none', !n);
    setHTML($('appr'), n ? apprs.map(function (a) { return apprCard(a, false); }).join('') : '<p class="empty ok">' + (RO ? 'Nothing waits for its owner' : 'All clear: nothing needs you') + (fd ? ' from ' + esc(fd.name) : '') + '.</p>');
    S.approvals.forEach(function (a) { ui.seen[a.id] = 1; });
    renderEarned(fd);
    renderChats();
  }
  // What the company earned, by where it came from: each department that earns (ET10: bugs, prizes, the League) and
  // each app it built (the proposed ET10 for the visitors it brings, and USDC from its revenue share).
  function vaultRows() {
    var S = CO.S, out = [];
    S.departments.filter(function (d) { return d.et10 || d.files_as; }).forEach(function (d) {
      var why = d.files_as ? (d.accepted || 0) + ' bug' + (d.accepted === 1 ? '' : 's') + ' accepted' :
        d.prizes ? d.prizes + ' tournament prize' + (d.prizes === 1 ? '' : 's') : d.answers ? d.answers + ' League answers' : 'prizes';
      out.push({ kind: 'dept', id: d.id, name: d.name, why: why, et10: d.et10 || 0, usdc: 0 });
    });
    CO.apps().forEach(function (a) {
      var e = CO.appEarn(a);
      out.push({ kind: 'app', name: a.name, why: (a.visitors + a.todayVisitors).toLocaleString('en-US') + ' visitors · ' + (a.uses + a.todayUses).toLocaleString('en-US') + ' uses', et10: e.et10, usdc: e.usdc });
    });
    return out.sort(function (a, b) { return (b.et10 + b.usdc * 100) - (a.et10 + a.usdc * 100); });
  }
  // the right column's vault: its two totals, then where they came from; a visitor sees only that it is private
  function renderEarned(fd) {
    var V = CO.vaultTotals();
    if (RO) { $('earn-n').textContent = ''; setHTML($('earn'), '<p class="empty"><i class="lk"></i> Private: only its owner sees inside the vault.</p>'); return; }
    $('earn-n').textContent = '';
    var rows = vaultRows(), top = Math.max(1, V.et10);
    setHTML($('earn'), '<button class="vtot" data-a="vault"><div><b class="g">' + CO.fmtEt(V.et10) + '</b><span>ET10</span></div><div><b class="u">' + CO.fmtUsd(V.usdc) + '</b><span>USDC</span></div></button>' +
      rows.slice(0, 5).map(function (r) {
        var pct = Math.round(r.et10 / top * 100);
        return '<button class="er' + (fd && r.kind === 'dept' && fd.id === r.id ? ' on' : '') + ((r.et10 || r.usdc) ? '' : ' zero') + '"' + (r.kind === 'dept' ? ' data-id="' + r.id + '"' : ' data-a="vault"') + '>' +
          '<div class="e1"><b>' + esc(r.name) + '</b><span class="v">' + (r.et10 ? '+' + CO.fmtEt(r.et10) + ' ET10' : '') + (r.usdc ? ' <em>+' + CO.fmtUsd(r.usdc) + ' USDC</em>' : '') + (!r.et10 && !r.usdc ? '0 ET10' : '') + '</span></div>' +
          '<div class="e2"><span>' + (r.kind === 'app' ? 'app · ' : '') + esc(r.why) + '</span><span>' + pct + '%</span></div>' +
          '<span class="ebar"><i style="width:' + pct + '%"></i></span></button>';
      }).join('') + (CO.apps().length ? '<p class="hint vnote" title="Build it Better apps earn nothing today; Cymetica was asked on 2026-10-18 to pay ET10 for the users they bring. The rates here are placeholders.">App earnings: proposed, placeholder rates</p>' : ''));
  }
  // the vault opened: both totals, every department and every app that put something in it
  function openVault() {
    if (RO) return toast('The vault is private: only its owner sees inside.');
    var V = CO.vaultTotals(), rows = vaultRows(), R = CO.RATE;
    var list = function (kind) {
      var rs = rows.filter(function (r) { return r.kind === kind; });
      if (!rs.length) return '<p class="empty">' + (kind === 'app' ? 'No apps yet: build one with Build it Better and it earns here.' : 'No department has earned yet.') + '</p>';
      return rs.map(function (r) {
        return '<div class="vrow"><b>' + esc(r.name) + '</b><span class="w">' + esc(r.why) + '</span><span class="g">' + (r.et10 ? '+' + CO.fmtEt(r.et10) : '0') + ' ET10</span><span class="u">' + (r.usdc ? '+' + CO.fmtUsd(r.usdc) + ' USDC' : '') + '</span></div>';
      }).join('');
    };
    openModal('<div class="mh"><h3>Vault</h3><span class="lockp"><i class="lk"></i>PRIVATE</span><span class="sp"></span><button class="btn" data-a="close">×</button></div>' +
      '<div class="vbig"><div><b class="g">' + CO.fmtEt(V.et10) + '</b><span>ET10</span></div><div><b class="u">' + CO.fmtUsd(V.usdc) + '</b><span>USDC</span></div></div>' +
      '<div class="sec">BY DEPARTMENT</div>' + list('dept') + '<div class="sec">BY APP <span>proposed: ' + R.et10PerVisitor + ' ET10 a visitor, ' + R.usdcPerUse + ' USDC a use (placeholder rates)</span></div>' + list('app'), true);
  }

  // the conversation with the Manager: all of it in the Manager's focus, one department's in its detail
  function chatHTML(msgs, tagged) {
    var S = CO.S, last = msgs[msgs.length - 1];
    var mh = msgs.map(function (m) {
      var md = tagged && m.dept_id ? CO.dept(m.dept_id) : null;
      return '<div class="msg' + (m.role === 'owner' ? ' me' : '') + '"><em>' + (m.role === 'owner' ? 'You' : 'Manager') + ' · ' + hhmm(m.at) +
        (md ? '<span class="tagd">' + esc(md.name) + '</span>' : '') + '</em>' + esc(m.text) + '</div>';
    }).join('');
    if (S.notice && last && last.role === 'owner' && !last.answered) mh += '<div class="msgwait">' + esc(S.notice.text) + '</div>';
    return mh;
  }
  function fillChat(el, html) {
    if (setHTML(el, html)) { el.scrollTop = 1e6; requestAnimationFrame(function () { el.scrollTop = 1e6; }); }
  }
  function renderChats() {
    var S = CO.S;
    if (ui.mgr) {
      setHTML($('mg-switch'), switcher('hub'));
      fillChat($('msgs'), chatHTML(S.messages, true) || '<p class="hint">' + (RO ? 'No messages yet.' : 'No messages yet. Say hello to your Manager: ask how it goes, give it work, or tell it to add a department.') + '</p>');
      $('typing').hidden = !S.typing;
      var c = CO.counts();
      $('mg-pill').textContent = S.company.status === 'paused' ? 'PAUSED' : c.working ? c.working + ' WORKING' : 'RUNNING';
    }
  }

  /* ---------------- the department drawer ---------------- */
  function openDrawer(id) {
    var d = CO.dept(id); if (!d) return;
    if (ui.tab !== 'office') setTab('office');
    if (ui.panel !== id) { ui.dirty = false; $('dr-ch-text').value = d.charter; ui.open = {}; }
    var was = ui.panel != null || ui.mgr;
    ui.panel = id; ui.mgr = false; $('mgr').hidden = true;
    var dr = $('drawer'); dr.hidden = false; dr.scrollTop = 0;
    document.body.classList.add('focus');
    $('back').hidden = false; $('where').hidden = false; $('where').textContent = d.name;
    office.select('d' + id);
    render();
    // let the columns open first, then fly the camera in
    clearTimeout(ui.flyT);
    ui.flyT = setTimeout(function () { office.focus('d' + id, 0, true); fitCharter(); }, was ? 0 : 520);
  }
  function openManager() {
    if (ui.tab !== 'office') setTab('office');
    var was = ui.panel != null || ui.mgr;
    ui.panel = null; ui.mgr = true; $('drawer').hidden = true; $('mgr').hidden = false; $('msgs')._h = null;
    document.body.classList.add('focus');
    $('back').hidden = false; $('where').hidden = false; $('where').textContent = 'Manager';
    office.select('hub');
    render();
    setTimeout(function () { $('msg').focus(); }, 60);
    clearTimeout(ui.flyT);
    ui.flyT = setTimeout(function () { office.focus('hub', 0, true); }, was ? 0 : 520);
  }
  function closeDrawer() {
    if (ui.panel == null && !ui.mgr) return;
    ui.panel = null; ui.mgr = false; $('drawer').hidden = true; $('mgr').hidden = true;
    document.body.classList.remove('focus');
    $('back').hidden = true; $('where').hidden = true;
    office.select(null);
    render();
    clearTimeout(ui.flyT);
    ui.flyT = setTimeout(function () { office.fit(true); }, 520);
  }
  function taskRow(t, opened) {
    // one plain line: the result when there is one; nothing about attempts or passes
    var one = t.status === 'done' || t.status === 'failed' || t.status === 'waiting_approval' ? (t.outcome || '') : '';
    var when = t.finished_at || t.started_at || t.created_at;
    var more = opened ? '<div class="more"><b>Brief:</b> ' + esc(t.brief) + '<br><b>Result:</b> ' + esc(t.outcome || 'No output yet.') +
      (t.last_error ? '<br><b class="red">Last error:</b> ' + esc(t.last_error) : '') + '<br>' + esc(TSTAT[t.status]) + ' · ' + t.turns + ' turn' + (t.turns === 1 ? '' : 's') +
      (t.units ? ' · ' + u2(t.units) + ' u' : '') + ' · ' + CO.expertName(t.expert || '') + '</div>' : '';
    return '<div class="trow" data-task="' + t.id + '"><span><span class="st ' + t.status + '">' + esc(TSTAT[t.status]) + '</span></span><div><b>' + esc(plainTitle(t.title)) + '</b><em>' + esc(one) + '</em></div><i>' + hhmm(when) + '</i>' + more + '</div>';
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
    setHTML($('dr-switch'), switcher(d.id));
    var ln = CO.deptLine(d, v);
    setHTML($('dr-head'), '<i class="dot ' + v.status + (ln.tone === 'red' ? ' needs' : '') + '"></i><h2>' + esc(d.name) + '</h2>' +
      (d.files_as ? '<span class="et ' + (d.et10 ? 'lit' : 'zero') + '" title="ET10 Cymetica paid for accepted bugs, to ' + esc(d.files_as) + '">' + (d.et10 ? '+' : '') + (d.et10 || 0).toLocaleString('en-US') + ' ET10</span>' : '') +
      (RO ? '' : '<span class="x"><button class="btn" data-a="edit">Edit</button><button class="btn rd" data-a="delete" title="Delete this department">Delete</button></span>'));
    // what it is doing right now, in one line: the first thing anyone wants to know
    setHTML($('dr-now'), '<div class="now t-' + ln.tone + '"><p>' + esc(ln.text) + '</p>' +
      (appr.length ? '<button class="btn rd" type="button" data-a="appr">Open</button>' : '') + (v.running ? '<span class="run"><i></i></span>' : '') + '</div>');
    var ta = $('dr-ch-text');
    if (!ui.dirty && ta.value !== d.charter) ta.value = d.charter;
    charterMeta();
    // what it spends, and the owner's two brakes (a daily cap; runs a day for a department on a clock)
    var ci = CO.CAP_STEPS.indexOf(v.cap); if (ci < 0) ci = CO.CAP_STEPS.length - 1;
    var runsNow = d.schedule ? d.schedule.times.length : 0;
    var tokHtml = '<div class="tok"><div class="sec">SPEND</div>' +
      '<div class="tk2"><div><b class="' + (v.capped ? 'red' : 'cy') + '">' + CO.fmtTok(v.tokToday) + '</b><span>today</span></div>' +
      '<div><b>' + CO.fmtTok(v.tok7d) + '</b><span>last 7 days</span></div></div>' +
      // the bar is always there: against the cap when there is one, empty and saying so when not
      '<div class="track tkbar' + (v.cap ? '' : ' nocap') + '"><i class="' + (v.capped ? 'hot' : '') + '" style="width:' + (v.cap ? Math.min(100, v.tokToday / v.cap * 100).toFixed(1) : 0) + '%"></i></div>' +
      '<div class="tkcap' + (v.capped ? ' hot' : '') + '">' + (!v.cap ? (RO ? 'No daily cap' : 'No daily cap: set one below to hold it back') : v.capped ? 'Cap reached: it waits until 00:00' : CO.fmtTok(Math.max(0, v.cap - v.tokToday)) + ' left today of ' + CO.fmtTok(v.cap)) + '</div>' +
      (RO ? (d.schedule ? '<div class="capr ro"><span class="l">Runs a day</span><b>' + runsNow + '×</b></div>' : '') :
      '<label class="capr"><span class="l">Daily cap</span><input type="range" id="dr-cap" min="0" max="' + (CO.CAP_STEPS.length - 1) + '" step="1" value="' + ci + '">' +
      '<b id="dr-cap-v">' + capLabel(CO.CAP_STEPS[ci], v.perTurn) + '</b></label>' +
      (d.schedule ? '<div class="rpd"><span class="l">Runs a day</span>' + [1, 2, 3, 4, 6, 12].map(function (n) {
        return '<button type="button" data-rpd="' + n + '"' + (n === runsNow ? ' class="on"' : '') + '>' + n + '×</button>';
      }).join('') + '</div>' : '')) + '</div>';
    var tk = $('dr-tok');
    if (tk._h !== tokHtml && document.activeElement !== $('dr-cap')) { tk._h = tokHtml; tk.innerHTML = tokHtml; }
    // a department on a clock: its runs, products, who the bugs are filed as, what they earned
    var runsHtml = '';
    if (d.schedule && d.run_kind) {
      // the league answers puzzles and the outsider hands problems on: no products, no bug count of their own
      var third = d.run_kind === 'league' ? [(d.answers || 0), 'answers sent'] : [(d.handed || 0), 'handed to QA'];
      runsHtml = '<div class="runs"><div class="sec">RUNS <span>' + esc(d.schedule.label) + '</span></div>' +
        '<div class="rk" style="grid-template-columns:repeat(2,1fr)"><div><b>' + hhmm(d.next_run) + '</b><span>next run</span></div>' +
        '<div><b class="gr">' + third[0] + '</b><span>' + third[1] + '</span></div></div>' +
        (RO ? '' : '<div class="cb"><span class="sp" style="flex:1"></span><button class="btn cy" data-a="runnow">Run now</button></div>') + '</div>';
    } else if (d.schedule) {
      runsHtml = '<div class="runs"><div class="sec">RUNS <span>' + esc(d.schedule.label) + '</span></div>' +
        '<div class="rk" style="grid-template-columns:repeat(2,1fr)"><div><b>' + hhmm(d.next_run) + '</b><span>next run</span></div>' +
        '<div><b class="gr">' + (d.accepted || 0) + '</b><span>bugs accepted</span></div></div>' +
        '<div class="prods">' + (d.products.length ? d.products.map(function (p) { return '<span class="chip">' + esc(p) + '</span>'; }).join('') : '<span class="hint">no products yet: the public site</span>') + '</div>' +
        (RO ? '' : '<div class="cb"><input id="dr-prods" placeholder="Products, comma separated" value="' + esc(d.products.join(', ')) + '"><button class="btn" data-a="prods">Save</button><button class="btn cy" data-a="runnow">Run now</button></div>') + '</div>';
    }
    if ($('dr-runs')._h !== runsHtml && !(document.activeElement && document.activeElement.id === 'dr-prods')) { $('dr-runs')._h = runsHtml; $('dr-runs').innerHTML = runsHtml; }
    // the latest results: what it finished, plainly; the full list is one click away
    var ts = sortTasks(CO.deptTasks(d.id)).filter(function (t) { return t.status !== 'cancelled'; });
    $('dr-tasks-all').textContent = 'All ' + ts.length + ' →';
    setHTML($('dr-tasks'), ts.length ? ts.slice(0, 5).map(function (t) { return taskRow(t, ui.open[t.id]); }).join('') : '<p class="empty">Nothing yet.</p>');
    // memory: what it learned, folded away until asked for
    var mem = S.memory.filter(function (m) { return m.dept_id === d.id; }).sort(function (a, b) { return b.id - a.id; });
    $('dr-mem-t').innerHTML = 'MEMORY · ' + mem.length + ' <span>' + (ui.memOpen ? '▾' : '▸') + '</span>';
    $('dr-mem').hidden = !ui.memOpen;
    setHTML($('dr-mem'), mem.length ? mem.map(function (m) { return '<div class="mem"><span class="k-' + m.kind + '">' + esc(m.kind) + '</span><div>' + esc(m.text) + '</div></div>'; }).join('') : '<p class="empty">Nothing learned yet.</p>');
  }
  function capLabel(cap, perTurn) {
    return cap ? CO.fmtTok(cap) + ' a day · ~' + Math.max(1, Math.floor(cap / (perTurn || 0.19))) + ' turns' : 'no cap';
  }
  function switcher(on) {
    return '<button data-sw="hub"' + (on === 'hub' ? ' class="on"' : '') + '><i class="dot working"></i>Manager</button>' + CO.S.departments.map(function (x) {
      return '<button data-sw="' + x.id + '"' + (x.id === on ? ' class="on"' : '') + '><i class="dot ' + CO.deptView(x).status + '"></i>' + esc(x.name) + '</button>';
    }).join('');
  }
  // the charter opens as tall as its text (up to 70% of the window) and grows as it is written
  function fitCharter() {
    var ta = $('dr-ch-text'); if (!ta || ta.offsetParent === null) return;
    // only when the text or the width changed: a refit on every render would jump the drawer's scroll
    var key = ta.value + '|' + ta.clientWidth + '|' + window.innerHeight;
    if (ta._fit === key) return;
    ta._fit = key;
    ta.style.height = 'auto';
    ta.style.height = Math.min(ta.scrollHeight + 2, Math.round(window.innerHeight * 0.7)) + 'px';
  }
  function charterMeta() {
    fitCharter();
    var d = CO.dept(ui.panel), ta = $('dr-ch-text'), n = ta.value.length.toLocaleString('en-US');
    var m = $('dr-ch-meta');
    m.className = ui.dirty ? 'unsaved' : '';
    m.textContent = ui.dirty ? n + ' / 2,000 · not saved' : n + ' / 2,000 · saved ' + (d ? dayTime(d.charter_updated_at) : '');
  }

  /* ---------------- the other tabs ---------------- */
  function setTab(name) {
    // a visitor's Universe is the visitor's own page: the map, with their own company on it
    if (name === 'universe' && RO) { location.href = 'index.html#universe'; return; }
    ui.tab = name;
    Array.prototype.forEach.call(document.querySelectorAll('#tabs button'), function (b) { b.classList.toggle('on', b.getAttribute('data-tab') === name); });
    Array.prototype.forEach.call(document.querySelectorAll('.pane'), function (p) { p.hidden = p.getAttribute('data-pane') !== name; });
    if (name !== 'office') { $('drawer').hidden = true; } else if (ui.panel != null) { $('drawer').hidden = false; }
    render();
    if (name === 'office') requestAnimationFrame(function () { office.resize(); });
    if (name === 'universe') showUniverse();
    // the address remembers the Universe tab, but never at the cost of a mode carried in the hash (#demo, #empty)
    if (!/^#(demo|empty)$/.test(location.hash)) {
      try { history.replaceState(null, '', location.pathname + location.search + (name === 'universe' ? '#universe' : '')); } catch (e) { /* fine */ }
    }
  }
  function renderPane() {
    ({ portfolio: renderPortfolio, tasks: renderTasks, approvals: renderApprovals, memory: renderMemory, audit: renderAudit, rules: renderRules, investable: renderInvest, legal: renderLegal, token: renderToken, settings: renderSettings, universe: renderUniverse }[ui.tab] || function () {})();
  }

  /* ---------------- the Universe: every company on one map ---------------- */
  var uv = null;
  // our own company as the map draws it: its name, station and colour from Settings, a deck per department
  function mineForMap() {
    var S = CO.S, p = CO.profile(), work = [];
    S.departments.forEach(function (d, i) { if (CO.deptView(d).running) work.push(i); });
    return { id: 0, name: S.company.name, owner: CO.ME, public: !!p.public, status: S.company.status, skin: p.skin, accent: p.accent,
      departments: S.departments.slice(), mission: S.company.mission, et10: S.et10 || 0, working: work, plan: S.company.plan, days: 0 };
  }
  function uvHooks() { return { mine: mineForMap, onOpen: openFromMap, onStats: uvStats, onFail: uvTo2D }; }
  // the 3D renderer could not start here: the flat map takes its place
  function uvTo2D() {
    var st = $('uvstage'); st.classList.remove('is3d'); st.classList.add('is2d'); $('uvbans').innerHTML = '';
    uv = new CO.Universe($('uvmap'), st, uvHooks()); uv.layout(); finishShow(true);
  }
  /* ---------------- the Universe as the operator's picture ---------------- */
  // His orrery (look-universe.webp, 1533 x 820) is the Universe's first look: "they can be pictures, only the
  // office has to be interactive" (2026-10-18). Each station in it opens the sample company of that name; the
  // live 3D orrery stays one click away, and is where our own station is found. Positions are the picture's
  // pixels: the name's centre, its top, and the bottom of the station under it.
  var UVPIC = { w: 1533, h: 820, core: [790, 282],
    st: [['Sigma Collective', 553, 98, 238], ['Night Owl Trading', 1058, 126, 272], ['Ion Analytics', 1362, 127, 250], ['Giga Fund', 245, 225, 345],
      ['League Lab', 583, 375, 500], ['Vector Trading', 963, 333, 500], ['Ion Analytics', 1361, 348, 455], ['Bull Club', 293, 516, 630],
      ['Bull Club', 499, 599, 750], ['Quasar Fund', 958, 552, 690], ['Laser Station', 1258, 510, 650]] };
  // Cymetica's core in the picture, made the collider of the operator's other picture: a white-hot heart, a ball of
  // light filaments turning round it, beams shot out of it, sparks flying off -- in white, cyan and blue (the site's
  // palette; the collider picture's gold is not allowed). Drawn on a canvas over the painted core, added onto it
  // (screen), at about 30 frames a second and only while the picture is on screen.
  var CORE = { size: 600, fil: null, sparks: null, beams: null, raf: 0, last: 0 };
  function coreSeed() {
    var s = 7, R = function () { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646; };
    var unit = function () { var u = R() * 2 - 1, th = R() * Math.PI * 2, q = Math.sqrt(1 - u * u); return [Math.cos(th) * q, u, Math.sin(th) * q]; };
    var cols = [[235, 252, 255], [160, 236, 255], [0, 207, 255], [127, 184, 255], [59, 130, 246], [140, 255, 205]];
    CORE.fil = [];
    for (var i = 0; i < 78; i++) {
      var ax = unit(), t = [0.31, 0.93, 0.19], u = [ax[1] * t[2] - ax[2] * t[1], ax[2] * t[0] - ax[0] * t[2], ax[0] * t[1] - ax[1] * t[0]], ul = Math.hypot(u[0], u[1], u[2]);
      u = [u[0] / ul, u[1] / ul, u[2] / ul];
      var v = [ax[1] * u[2] - ax[2] * u[1], ax[2] * u[0] - ax[0] * u[2], ax[0] * u[1] - ax[1] * u[0]], m = R();
      CORE.fil.push({ ax: ax, u: u, v: v, r: 0.08 + R() * 0.2, a0: R() * 6.28, len: 0.9 + R() * 2.6, wob: R() * 0.35, f: 2 + Math.floor(R() * 4), sp: (R() - 0.5) * 0.9,
        c: cols[m < 0.3 ? 0 : m < 0.55 ? 1 : m < 0.75 ? 2 : m < 0.88 ? 3 : m < 0.96 ? 4 : 5], a: 0.45 + R() * 0.5 });
    }
    CORE.beams = [];
    for (var b = 0; b < 8; b++) CORE.beams.push({ th: R() * 6.28, len: 0.55 + R() * 0.43, w: 0.018 + R() * 0.03, ph: R() * 6.28, sp: (R() - 0.5) * 0.12, white: R() < 0.6 });
    CORE.sparks = [];
    for (var k = 0; k < 160; k++) CORE.sparks.push({ d: unit(), sp: 0.12 + R() * 0.35, ph: R(), s: 0.6 + R() * 1.4 });
  }
  function coreFrame(now) {
    CORE.raf = requestAnimationFrame(coreFrame);
    var cv = $('uvcore'); if (!cv || document.hidden || !$('uvstage').classList.contains('pic') || !cv.offsetParent) return;
    if (now - CORE.last < 33) return; CORE.last = now;
    var g = cv.getContext('2d'), W = cv.width, R = W / 2, t = now / 1000, cx = R, cy = R;
    g.clearRect(0, 0, W, W); g.globalCompositeOperation = 'lighter';
    var flick = 0.85 + 0.15 * Math.sin(t * 7.3) * Math.sin(t * 2.1);
    // haze round it
    var h = g.createRadialGradient(cx, cy, 0, cx, cy, R * 0.6);
    h.addColorStop(0, 'rgba(0,207,255,' + (0.22 * flick).toFixed(3) + ')'); h.addColorStop(1, 'rgba(0,207,255,0)');
    g.fillStyle = h; g.fillRect(0, 0, W, W);
    // beams: tapering streaks out of the heart, turning slowly, breathing
    CORE.beams.forEach(function (b) {
      var a = b.th + t * b.sp, L = R * b.len * (0.85 + 0.15 * Math.sin(t * 1.7 + b.ph)), w = R * b.w, al = 0.5 + 0.4 * Math.max(0, Math.sin(t * 2.3 + b.ph));
      var ex = cx + Math.cos(a) * L, ey = cy + Math.sin(a) * L * 0.62, nx = -Math.sin(a) * w, ny = Math.cos(a) * w * 0.62;
      var lg = g.createLinearGradient(cx, cy, ex, ey), c = b.white ? '235,252,255' : '127,214,255';
      lg.addColorStop(0, 'rgba(' + c + ',' + al.toFixed(3) + ')'); lg.addColorStop(0.5, 'rgba(0,207,255,' + (al * 0.35).toFixed(3) + ')'); lg.addColorStop(1, 'rgba(0,207,255,0)');
      g.fillStyle = lg; g.beginPath(); g.moveTo(cx + nx, cy + ny); g.lineTo(ex, ey); g.lineTo(cx - nx, cy - ny); g.closePath(); g.fill();
    });
    // the filaments: arcs on a ball round the heart, the ball turning, each arc drawn as a glow and a thread
    var ry = t * 0.35, rx = 0.42, cyr = Math.cos(ry), syr = Math.sin(ry), cxr = Math.cos(rx), sxr = Math.sin(rx);
    CORE.fil.forEach(function (f, i) {
      var pts = [], n = 22, off = t * f.sp;
      for (var s2 = 0; s2 <= n; s2++) {
        var an = f.a0 + off + f.len * s2 / n, rad = f.r * (1 + f.wob * Math.sin(an * f.f + t * 1.3));
        var x = (f.u[0] * Math.cos(an) + f.v[0] * Math.sin(an)) * rad, y = (f.u[1] * Math.cos(an) + f.v[1] * Math.sin(an)) * rad, z = (f.u[2] * Math.cos(an) + f.v[2] * Math.sin(an)) * rad;
        var x2 = x * cyr + z * syr, z2 = -x * syr + z * cyr, y2 = y * cxr - z2 * sxr;
        pts.push([cx + x2 * R, cy + y2 * R * 0.92]);
      }
      var a = f.a * flick * (0.75 + 0.25 * Math.sin(t * (3 + i % 5) + i));
      [[3.2, 0.12], [1.1, 1]].forEach(function (pass) {
        g.lineWidth = pass[0] * W / 600; g.strokeStyle = 'rgba(' + f.c.join(',') + ',' + (a * pass[1]).toFixed(3) + ')';
        g.beginPath(); pts.forEach(function (p, k) { if (k) g.lineTo(p[0], p[1]); else g.moveTo(p[0], p[1]); }); g.stroke();
      });
    });
    // sparks flying off
    CORE.sparks.forEach(function (sp) {
      var k = (t * sp.sp + sp.ph) % 1, r = R * (0.05 + k * 0.85), al = (1 - k) * 0.8;
      g.fillStyle = 'rgba(220,248,255,' + al.toFixed(3) + ')'; g.fillRect(cx + sp.d[0] * r, cy + sp.d[1] * r * 0.62 + sp.d[2] * r * 0.2, sp.s * W / 600, sp.s * W / 600);
    });
    // the white-hot heart
    var c0 = g.createRadialGradient(cx, cy, 0, cx, cy, R * 0.22);
    c0.addColorStop(0, 'rgba(255,255,255,' + (0.95 * flick).toFixed(3) + ')'); c0.addColorStop(0.25, 'rgba(235,252,255,0.8)'); c0.addColorStop(0.6, 'rgba(0,207,255,0.25)'); c0.addColorStop(1, 'rgba(0,207,255,0)');
    g.fillStyle = c0; g.fillRect(cx - R * 0.22, cy - R * 0.22, R * 0.44, R * 0.44);
    g.globalCompositeOperation = 'source-over';
  }
  function startCore() { if (!CORE.fil) coreSeed(); if (!CORE.raf) CORE.raf = requestAnimationFrame(coreFrame); }
  function uvView() { try { return localStorage.getItem('co.uvview') || 'pic'; } catch (e) { return 'pic'; } }
  function setUvView(v) { try { localStorage.setItem('co.uvview', v); } catch (e) { /* fine */ } showUniverse(); }
  function byName(n) { for (var i = 0; i < CO.UNIVERSE.length; i++) if (CO.UNIVERSE[i].name === n) return CO.UNIVERSE[i]; return null; }
  // The Universe composed live (uvlive.js) out of the pieces he generates: his background with every company's
  // station on its orbits, as many as there are. It takes the picture's place wherever the pieces are (they are kept
  // out of git); the painted picture stays where they are not. PIC is whichever of the two is up.
  var PIC = UVPIC, uvl = null;
  function buildPic() {
    var host = $('uvpic'); if (host.getAttribute('data-built')) return;
    host.setAttribute('data-built', '1');
    CO.uvLive.load(function (ok) { if (ok) buildLive(host); else buildStatic(host); fitPic(); picCard(); });
  }
  function buildLive(host) {
    var bg = CO.uvLive.man['U-background'], pc = function (v, of) { return (v / of * 100).toFixed(3) + '%'; };
    PIC = { w: bg.w, h: bg.h, core: bg.calib.core, coreSize: CORE.size * bg.w / UVPIC.w, live: true };
    host.innerHTML = '<div class="uvpic-in live" id="uvpic-in"><img src="assets/gen/U-background.webp" alt="" draggable="false">' +
      '<canvas class="uvl" id="uvl-back"></canvas>' +
      '<canvas class="uvcore" id="uvcore" style="left:' + pc(PIC.core[0] - PIC.coreSize / 2, PIC.w) + ';top:' + pc(PIC.core[1] - PIC.coreSize / 2, PIC.h) + ';width:' + pc(PIC.coreSize, PIC.w) + ';height:' + pc(PIC.coreSize, PIC.h) + '"></canvas>' +
      '<canvas class="uvl" id="uvl-front"></canvas><div class="uvl-top" id="uvl-top"></div></div><button class="uvpic-card" id="uvpic-card"></button>';
    uvl = new CO.UvLive({ back: $('uvl-back'), front: $('uvl-front'), top: $('uvl-top') }, {});
    uvl.set(mineForMap());
    var top = $('uvl-top');
    top.addEventListener('mousemove', function (e) { var b = e.target.closest('[data-id]'); if (b) liveTip(+b.getAttribute('data-id'), e); else $('uvstage').querySelector('.tip').hidden = true; });
    top.addEventListener('mouseleave', function () { $('uvstage').querySelector('.tip').hidden = true; });
    if (window.ResizeObserver) new ResizeObserver(fitPic).observe($('uvstage'));
    uvl.start();
    startCore();
  }
  function liveTip(id, e) {
    var tip = $('uvstage').querySelector('.tip'), html = uvl.tip(id); if (!html) return;
    tip.innerHTML = html; tip.hidden = false;
    var r = $('uvstage').getBoundingClientRect(), x = e.clientX - r.left + 16, y = e.clientY - r.top + 16;
    if (x + tip.offsetWidth > r.width - 8) x = e.clientX - r.left - tip.offsetWidth - 16;
    if (y + tip.offsetHeight > r.height - 8) y = e.clientY - r.top - tip.offsetHeight - 16;
    tip.style.left = x + 'px'; tip.style.top = y + 'px';
  }
  // a station on the live map: ours opens the office, a public one its visit, a private one its card
  function openFromLive(id) {
    if (id === 0) return setTab('office');
    var c = null; CO.UNIVERSE.forEach(function (x) { if (x.id === id) c = x; });
    if (c) openFromPic(c.name, c);
  }
  function buildStatic(host) {
    var pc = function (v, of) { return (v / of * 100).toFixed(3) + '%'; }, html = '<div class="uvpic-in" id="uvpic-in"><img src="look-universe.webp" alt="" draggable="false">';
    UVPIC.st.forEach(function (s) {
      var w = 210, x = s[1] - w / 2, y = s[2] - 12, h = s[3] - y;
      html += '<button class="uvhs" data-name="' + esc(s[0]) + '" style="left:' + pc(x, UVPIC.w) + ';top:' + pc(y, UVPIC.h) + ';width:' + pc(w, UVPIC.w) + ';height:' + pc(h, UVPIC.h) + '"></button>';
    });
    html += '<canvas class="uvcore" id="uvcore" style="left:' + pc(UVPIC.core[0] - CORE.size / 2, UVPIC.w) + ';top:' + pc(UVPIC.core[1] - CORE.size / 2, UVPIC.h) + ';width:' + pc(CORE.size, UVPIC.w) + ';height:' + pc(CORE.size, UVPIC.h) + '"></canvas>';
    // the picture's own corner panel is painted; ours, with our company, covers it
    html += '</div><button class="uvpic-card" id="uvpic-card"></button>';
    host.innerHTML = html;
    Array.prototype.forEach.call(host.querySelectorAll('.uvhs'), function (b) {
      b.addEventListener('mouseenter', function (e) { picTip(b, e); });
      b.addEventListener('mousemove', function (e) { picTip(b, e); });
      b.addEventListener('mouseleave', function () { $('uvstage').querySelector('.tip').hidden = true; });
    });
    if (window.ResizeObserver) new ResizeObserver(fitPic).observe($('uvstage'));
    startCore();
  }
  function picTip(b, e) {
    var c = byName(b.getAttribute('data-name')), tip = $('uvstage').querySelector('.tip'); if (!c) return;
    tip.innerHTML = CO.uvTip(c.id, { c: c }, {}); tip.hidden = false;
    var r = $('uvstage').getBoundingClientRect(), x = e.clientX - r.left + 16, y = e.clientY - r.top + 16;
    if (x + tip.offsetWidth > r.width - 8) x = e.clientX - r.left - tip.offsetWidth - 16;
    if (y + tip.offsetHeight > r.height - 8) y = e.clientY - r.top - tip.offsetHeight - 16;
    tip.style.left = x + 'px'; tip.style.top = y + 'px';
  }
  // the picture covers the stage, centred, as a photo would
  function fitPic() {
    var st = $('uvstage'), inn = $('uvpic-in'); if (!inn) return;
    var W = st.clientWidth, H = st.clientHeight, s = Math.max(W / PIC.w, H / PIC.h);
    inn.style.width = (PIC.w * s) + 'px'; inn.style.height = (PIC.h * s) + 'px';
    var ox = (W - PIC.w * s) / 2, oy = (H - PIC.h * s) / 2;
    inn.style.left = ox + 'px'; inn.style.top = oy + 'px';
    var cv = $('uvcore'), px = Math.round((PIC.coreSize || CORE.size) * s * Math.min(window.devicePixelRatio || 1, 2)); if (cv && cv.width !== px) { cv.width = px; cv.height = px; }
    var card = $('uvpic-card');
    // live: the background has no painted panel, so the card stands in the stage's corner
    if (PIC.live) {
      uvl.fit(s, ox, oy, W, H);
      card.style.width = '236px'; card.style.height = '96px'; card.style.left = (W - 236 - 16) + 'px'; card.style.top = (H - 96 - 16) + 'px';
      return;
    }
    // our card sits over the picture's painted corner panel, a little larger (the picture drifts), kept on the stage
    var cw = 236 * s, bottom = Math.min(oy + 818 * s, H), top = Math.min(oy + 690 * s, bottom - 104);
    card.style.width = cw + 'px'; card.style.left = Math.min(ox + 1292 * s, W - cw) + 'px';
    card.style.top = top + 'px'; card.style.height = (bottom - top) + 'px';
  }
  function picCard() {
    if (!$('uvpic-card')) return;
    if (uvl) uvl.setMine(mineForMap());
    var S = CO.S, n = S.departments.length, w = S.departments.filter(function (d) { return CO.deptView(d).status === 'working'; }).length;
    setHTML($('uvpic-card'), '<span class="k">YOUR COMPANY</span><b>' + esc(S.company.name) + '</b><span>' + n + ' departments · <em>' + w + ' working</em></span><span class="go">Open the office →</span>');
    var pub = CO.UNIVERSE.filter(function (c) { return c.public; }).length + (CO.profile().public ? 1 : 0);
    uvStats({ companies: CO.UNIVERSE.length + 1, public: pub, working: w });
  }
  function openFromPic(name, c) {
    c = c || byName(name); if (!c) return;
    if (!c.public) return privateCard(c);
    try { sessionStorage.setItem('uv.from', String(c.id)); } catch (e) { /* fine */ }
    $('uvfade').hidden = false; setTimeout(function () { location.href = 'index.html?visit=' + c.id; }, 350);
  }
  // the picture first; the live map when asked for
  function showUniverse() {
    var pic = uvView() === 'pic';
    $('uvstage').classList.toggle('pic', pic);
    Array.prototype.forEach.call(document.querySelectorAll('#uvvt [data-uvv]'), function (b) { b.classList.toggle('on', b.getAttribute('data-uvv') === (pic ? 'pic' : '3d')); });
    if (pic) { buildPic(); fitPic(); picCard(); return; }
    show3D();
  }
  // the 3D map when the browser can draw it (WebGPU, or WebGL2), the flat one otherwise
  function show3D() {
    if (!uv) {
      var t0 = Date.now();
      $('uvstage').classList.add('loading');
      (function wait() {
        if (uv) return;
        if (CO.U3 && CO.U3.ok) { uv = CO.U3.universe($('uv3d'), $('uvstage'), uvHooks()); $('uvstage').classList.add('is3d'); }
        else if ((CO.U3 && CO.U3.failed) || Date.now() - t0 > 6000) { uv = new CO.Universe($('uvmap'), $('uvstage'), uvHooks()); $('uvstage').classList.add('is2d'); }
        else return setTimeout(wait, 60);
        $('uvstage').classList.remove('loading');
        CO.uv = uv;   // a handle for looking at the map from the console
        uv.layout();
        finishShow(true);
      })();
      return;
    }
    finishShow(false);
  }
  function finishShow(first) {
    requestAnimationFrame(function () {
      uv.resize();
      if (!uv.fitted) uv.fit(false);
      uv.setMine(mineForMap());
      if (first) {
        // back from a visit: start at the company just left, then pull back to the whole map
        var from = null; try { from = sessionStorage.getItem('uv.from'); sessionStorage.removeItem('uv.from'); } catch (e) { /* fine */ }
        if (from) { uv.flyTo(+from, null, 0); setTimeout(function () { uv.fit(true); }, 350); }
      }
    });
  }
  function renderUniverse() { if (uvView() === 'pic' && $('uvpic-card')) picCard(); if (uv) uv.setMine(mineForMap()); }
  // Portfolio: build products, bring in users, earn. The flow first, as numbers; then one card per app.
  function renderPortfolio() {
    var apps = CO.apps(), Rd = CO.PORTFOLIO_READ, R = CO.RATE;
    if (!apps.length) return setHTML($('portfolio'), '<div class="pfempty"><b>No apps yet</b><span>Build one with Build it Better: its visitors, its uses and what it earns show here.</span></div>');
    var sum = { visitors: 0, uses: 0, likes: 0, et10: 0, usdc: 0, today: 0 };
    apps.forEach(function (a) { var e = CO.appEarn(a); sum.visitors += a.visitors + a.todayVisitors; sum.uses += a.uses + a.todayUses; sum.likes += a.likes; sum.et10 += e.et10; sum.usdc += e.usdc; sum.today += a.todayVisitors; });
    var step = function (n, l, cls, tip) { return '<div class="pk' + (cls ? ' ' + cls : '') + '"' + (tip ? ' title="' + esc(tip) + '"' : '') + '><b>' + n + '</b><span>' + l + '</span></div>'; };
    var top = Math.max.apply(null, apps.map(function (a) { return a.visitors + a.todayVisitors; }));
    setHTML($('portfolio'),
      '<div class="pkpis">' + step(apps.length, 'apps built') + '<i class="arr">→</i>' +
      step(sum.visitors.toLocaleString('en-US'), 'visitors · 30 d' + (sum.today ? ' <em>+' + sum.today + ' now</em>' : ''), '', 'Distinct daily visitors, summed over the days: Cymetica\'s own count') + '<i class="arr">→</i>' +
      step(sum.uses.toLocaleString('en-US'), 'uses · 30 d', '', 'Page loads where the visitor clicked, typed or filled a form') + '<i class="arr">→</i>' +
      step('+' + CO.fmtEt(sum.et10), 'ET10 · proposed', 'g', R.et10PerVisitor + ' ET10 for each visitor an app brings: a placeholder rate. Asked of Cymetica on 2026-10-18') +
      step('+' + CO.fmtUsd(sum.usdc), 'USDC · proposed', 'u', R.usdcPerUse + ' USDC for each use, a revenue share: a placeholder rate') + '</div>' +
      '<div class="pfgrid">' + apps.slice().sort(function (a, b) { return (b.visitors + b.todayVisitors) - (a.visitors + a.todayVisitors); }).map(function (a) {
        var e = CO.appEarn(a), v = a.visitors + a.todayVisitors, pct = Math.round(v / top * 100);
        return '<div class="pf"><div class="pf1"><b>' + esc(a.name) + '</b><a href="' + esc(a.url) + '" target="_blank" rel="noopener">' + esc(a.path) + ' ↗</a></div>' +
          '<div class="pfn"><div><b>' + v.toLocaleString('en-US') + '</b><span>visitors</span></div><div><b>' + (a.uses + a.todayUses).toLocaleString('en-US') + '</b><span>uses</span></div>' +
          '<div><b>' + a.views.toLocaleString('en-US') + '</b><span>views</span></div><div><b>' + a.likes + '</b><span>likes</span></div></div>' +
          '<span class="pfbar"><i style="width:' + pct + '%"></i></span>' +
          '<div class="pfe"><span class="g">+' + CO.fmtEt(e.et10) + ' ET10</span><span class="u">+' + CO.fmtUsd(e.usdc) + ' USDC</span><em>proposed</em>' +
          (a.todayVisitors ? '<i>+' + a.todayVisitors + ' now</i>' : '') + '</div></div>';
      }).join('') + '</div>' +
      '<p class="pfsrc">Visitors, uses, views, likes: Cymetica (' + esc(Rd.src) + '), last ' + Rd.days + ' days, read ' + Rd.at + '. Earnings: proposed, placeholder rates.</p>');
  }
  function uvStats(s) {
    setHTML($('uv-sum'), '<b>' + s.companies + '</b> companies · <b>' + s.public + '</b> public · <b class="cy">' + s.working + '</b> working now');
  }
  function openFromMap(it) {
    var c = it.c;
    if (it.mine) return setTab('office');
    if (!c.public) return privateCard(c);
    try { sessionStorage.setItem('uv.from', String(c.id)); } catch (e) { /* fine */ }
    $('uvfade').hidden = false;
    // the flight is only the way in: a drag or a wheel that cuts it short must not cut the visit too
    var gone = false, go = function () { if (!gone) { gone = true; location.href = 'index.html?visit=' + c.id; } };
    uv.flyTo(c.id, go);
    setTimeout(go, 1300);
  }
  // a private company: what it shows the world, and nothing from inside
  function privateCard(c) {
    var n = CO.floorsOf(c);
    openModal('<div class="pcard"><div class="pc-art uvprev">' + CO.skinSVG({ skin: c.skin, accent: c.accent, floors: n, seed: c.id, banner: c.name, priv: true }) + '</div>' +
      '<div class="pc-b"><div class="pc-h"><h3>' + esc(c.name) + '</h3><span class="lockp"><i class="lk"></i>PRIVATE</span><span class="sp"></span><button class="btn" data-a="close">×</button></div>' +
      '<div class="pc-o">by <b>@' + esc(c.owner) + '</b> · ' + (c.days ? 'on Cymetica for ' + c.days + ' day' + (c.days === 1 ? '' : 's') : 'new today') + '</div>' +
      '<div class="sec">ABOUT</div><p class="pc-d">' + esc(c.mission || 'Its owner has not written a description yet.') + '</p>' +
      '<div class="kpis two"><div><b>' + n + '</b><span>department' + (n === 1 ? '' : 's') + ' · one deck each</span></div><div><b>' + (c.status === 'paused' ? 'Paused' : 'Active') + '</b><span>status</span></div></div>' +
      '<p class="hint"><i class="lk"></i>Private: only its owner can look inside.</p></div></div>', true);
    pv3(document.querySelector('#modal-card .pc-art'), { skin: c.skin, accent: c.accent, floors: n, seed: c.id, name: c.name, public: false });
  }
  // the station pictures: six shapes in the company's colour
  function skinButtons(sel, acc) {
    return CO.SKINS.map(function (s) {
      return '<button type="button" class="skin' + (s.key === sel ? ' on' : '') + '" data-a="uv-skin" data-k="' + s.key + '">' + CO.skinSVG({ skin: s.key, accent: acc, floors: 3, seed: 11 }) + '<b>' + s.name + '</b></button>';
    }).join('');
  }
  function accentButtons(sel) {
    return CO.ACCENTS.map(function (a) { return '<button type="button" class="acc' + (a.key === sel ? ' on' : '') + '" data-a="uv-accent" data-k="' + a.key + '" style="--c:' + a.hex + '" title="' + a.key + '"></button>'; }).join('');
  }
  function mark(sel, el) { Array.prototype.forEach.call(document.querySelectorAll(sel), function (x) { x.classList.toggle('on', x === el); }); }
  // the station turning in 3D where the browser can draw it; the flat picture stays underneath until then
  function pv3(el, o) { if (el && CO.U3 && CO.U3.ok && CO.U3.preview) CO.U3.preview(el, o); }
  // the six station tiles as 3D pictures once they are drawn; the flat ones until then
  function thumbs3(root, accent) {
    if (!root || !(CO.U3 && CO.U3.ok && CO.U3.thumbs)) return;
    CO.U3.thumbs(CO.accentHex(accent), function (urls) {
      Array.prototype.forEach.call(root.querySelectorAll('.skin[data-k]'), function (b) {
        var u = urls[b.getAttribute('data-k')]; if (!u || b.querySelector('img.th3')) return;
        var img = document.createElement('img'); img.className = 'th3'; img.alt = ''; img.src = u; b.insertBefore(img, b.firstChild); b.classList.add('has3d');
      });
    });
  }
  function myPv() {
    var S = CO.S, p = CO.profile();
    return { skin: p.skin, accent: p.accent, floors: Math.max(1, S.departments.length), seed: 7, name: S.company.name, you: true, public: !!p.public };
  }
  function uvCard() {
    var S = CO.S, p = CO.profile(), n = Math.max(1, S.departments.length);
    return '<div class="card uvcard"><h3>In the Universe <span class="hint">where every company on Cymetica floats</span></h3><div class="uvset">' +
      '<div class="uvprev" id="st-prev">' + CO.skinSVG({ skin: p.skin, accent: p.accent, floors: n, seed: 7, banner: S.company.name, you: true, priv: !p.public }) + '</div>' +
      '<div class="uvopts"><div class="switch' + (p.public ? ' on' : '') + '" data-a="uv-public"><span class="sw"></span><div><b>' + (p.public ? 'Public' : 'Private') + '</b><span>' +
      (p.public ? 'Anyone can open it from the map and look at everything inside: office, departments, charters, processes, tasks, settings. Only you change anything.' :
        'It floats in the Universe with a lock. Others see its name, its station and its mission; nothing inside.') + '</span></div></div>' +
      '<div class="sec">STATION <span>one deck per department · ' + n + ' now</span></div><div class="skins">' + skinButtons(p.skin, p.accent) + '</div>' +
      '<div class="sec">COLOUR</div><div class="accents">' + accentButtons(p.accent) + '</div></div></div></div>';
  }
  // "Create your company": a name, a mission, the station in the Universe and who may look inside
  function createCompanyModal() {
    var o = { name: '', mission: '', skin: 'tower', accent: 'green', public: false };
    function prev() { return CO.skinSVG({ skin: o.skin, accent: o.accent, floors: 3, seed: 7, banner: o.name || 'Your company', you: true, priv: !o.public }); }
    function show() {
      var el = $('cc-prev'); if (!el) return;
      if (!el.__pv) el.innerHTML = prev();
      pv3(el, { skin: o.skin, accent: o.accent, floors: 3, seed: 7, name: o.name || 'Your company', you: true, public: o.public });
    }
    function pub() {
      return '<span class="sw"></span><div><b>' + (o.public ? 'Public' : 'Private') + '</b><span>' + (o.public ? 'Anyone can look inside, read only.' : 'Others see its name, its station and its mission.') + '</span></div>';
    }
    openModal('<div class="mh"><h3>Create your company</h3><button class="btn" data-a="close">×</button></div>' +
      '<div class="cc"><div class="ccl"><div class="form"><label class="field full">Name<input id="cc-name" maxlength="40" placeholder="e.g. Moonshot Labs" autocomplete="off"></label>' +
      '<label class="field full">Mission · what everyone reads in the Universe<input id="cc-mission" maxlength="200" placeholder="What it is for, in one line" autocomplete="off"></label></div>' +
      '<div class="sec step">YOUR STATION IN THE UNIVERSE <span>it grows a deck with every department</span></div>' +
      '<div class="skins" id="cc-skins">' + skinButtons(o.skin, o.accent) + '</div><div class="accents" id="cc-acc">' + accentButtons(o.accent) + '</div>' +
      '<div class="switch" id="cc-pub" data-a="cc-public">' + pub() + '</div></div>' +
      '<div class="ccr"><div class="uvprev big" id="cc-prev">' + prev() + '</div><p class="hint">Shown with 3 departments, as it will float in the Universe.</p></div></div>' +
      '<div class="mf"><span class="hint">One company per account.</span><span class="sp"></span><button class="btn" data-a="close">Cancel</button><button class="btn gr" data-a="create">Create company</button></div>', true, function (a, el) {
        if (a === 'uv-skin') { o.skin = el.getAttribute('data-k'); mark('#cc-skins .skin', el); }
        if (a === 'uv-accent') { o.accent = el.getAttribute('data-k'); mark('#cc-acc .acc', el); $('cc-skins').innerHTML = skinButtons(o.skin, o.accent); thumbs3($('cc-skins'), o.accent); }
        if (a === 'cc-public') { o.public = !o.public; var sw = $('cc-pub'); sw.classList.toggle('on', o.public); sw.innerHTML = pub(); }
        if (a === 'create') {
          var nm = $('cc-name').value.trim();
          if (!nm) { $('cc-name').focus(); $('cc-name').style.borderColor = 'var(--red)'; return; }
          CO.saveProfile({ name: nm, mission: $('cc-mission').value.trim(), skin: o.skin, accent: o.accent, public: o.public });
          location.href = 'index.html?empty&created=1';
          return;
        }
        show();
      });
    ui.ccPrev = function () { o.name = $('cc-name').value.trim(); show(); };
    show();
    thumbs3($('cc-skins'), o.accent);
  }
  // what a process's department raises next, and the process that picks it up
  function nextOf(r) {
    var d = CO.ruleTarget(r); if (!d) return null;
    var k = CO.kindOf(r.when), ev = k === 'released' && d.key === 'testing' ? 'bug' : k === 'bug' ? null : CO.EMITS[d.key];
    if (!ev) return null;
    return CO.S.rules.filter(function (x) { return x.on && x.id !== r.id && CO.kindOf(x.when) === ev; })[0] || null;
  }
  function renderRules() {
    var S = CO.S;
    setHTML($('rules'), S.rules.length ? S.rules.map(function (r) {
      var d = CO.ruleTarget(r), n = r.on ? nextOf(r) : null, nd = n && CO.ruleTarget(n);
      return '<div class="rule' + (r.on ? ' on' : '') + '" data-rule="' + r.id + '"><span class="ric">' + CO.ruleIcon(CO.kindOf(r.when)) + '</span>' +
        '<div class="rbody"><div class="rhead"><span class="rid">' + r.id + '</span><b>When ' + esc(r.when) + '</b><span class="arrow">→</span><b class="rt">' + esc(d ? d.name : 'department removed') + '</b>' +
        (r.fired ? '<span class="fired">' + r.fired + '× so far</span>' : '') + (!d ? '<span class="miss">pick another department</span>' : '') + '</div>' +
        '<p>' + esc(d ? d.name : 'It') + ' ' + esc(r.does) + '.' +
        (r.review ? ' <span class="rvt">' + esc(r.reviewer && r.reviewer !== 'you' ? r.reviewer : 'You') + (r.review === 'start' ? ' approve it before it starts' : ' review the result') + '</span>' : '') + '</p>' +
        (n ? '<div class="then">then: when ' + esc(n.when) + ' → ' + esc(nd ? nd.name : '') + ' <span class="rid">' + n.id + '</span></div>' : '') + '</div>' +
        '<span class="switch mini' + (r.on ? ' on' : '') + '" data-a="rule-toggle"><span class="sw"></span></span><button class="rx" data-a="rule-del" title="Remove">×</button></div>';
    }).join('') : '');
    // only the examples the company does not already follow
    var ex = CO.RULE_EXAMPLES.map(function (e, i) { return [e, i]; }).filter(function (p) {
      return !S.rules.some(function (r) { var d = CO.ruleTarget(r); return d && d.key === p[0][1] && CO.kindOf(r.when) === CO.kindOf(p[0][0]); });
    });
    setHTML($('nr-ex'), ex.length ? '<span class="hint">e.g.</span>' + ex.map(function (p) { return '<button class="exr" type="button" data-ex="' + p[1] + '">' + esc(exampleSentence(p[0])) + '</button>'; }).join('') : '');
  }
  // an example as the sentence the owner would write, naming their own department when they have one
  function exampleSentence(e) {
    var d = CO.S.departments.filter(function (x) { return x.key === e[1]; })[0];
    var tpl = CO.TEMPLATES.filter(function (x) { return x.key === e[1]; })[0];
    return 'When ' + e[0] + ', ' + (d ? d.name : tpl ? tpl.name : 'a department') + ' ' + e[2];
  }
  function addRuleFromPage() {
    var box = $('nr-text'), msg = $('nr-msg'), text = box.value.trim();
    if (!text) { box.focus(); return; }
    var pr = CO.parseRule(text), out, ok = false;
    if (pr.missing === 'when') out = 'Start with when it happens: "When …, <department> …".';
    else if (pr.missing === 'dept') out = CO.S.departments.length ? 'Which department does it? Yours: ' + CO.S.departments.map(function (x) { return x.name; }).join(', ') + '.' : 'Add a department first, then write the process.';
    else { out = CO.addRuleFromWords(pr); ok = true; box.value = ''; }
    msg.hidden = false; msg.textContent = out; msg.className = 'nrmsg' + (ok ? ' ok' : ' bad');
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
      // the result, or why it waits when that is something the owner can act on; never the machinery
      var blocked = t.status === 'queued' && (t.blocked_by || CO.capped(CO.dept(t.dept_id)));
      var res = t.status === 'running' ? 'working on it now' : t.status === 'queued' ? (blocked ? esc(CO.waitText(t)) : '') :
        t.status === 'failed' ? '<span class="err">Could not finish: ' + esc(t.last_error || 'unknown') + '</span>' : esc(t.outcome || '');
      var tr = '<tr class="row" data-task="' + t.id + '"><td><span class="st ' + t.status + '">' + esc(TSTAT[t.status]) + '</span></td><td>' + esc(d ? d.name : 'removed') + '</td>' +
        '<td><span class="id">#' + t.id + '</span><b>' + esc(t.title) + '</b></td><td class="num">' + (t.started_at ? dayTime(t.started_at) : '—') + '</td><td class="res">' + res + '</td></tr>';
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
    setHTML($('appr-full'), S.approvals.length ? S.approvals.map(function (a) { return apprCard(a, false); }).join('') : '<p class="empty ok">All clear: nothing needs you.</p>');
    S.approvals.forEach(function (a) { ui.seen[a.id] = 1; });
    setHTML($('appr-done'), S.decided.length ? S.decided.map(function (a) {
      var d = CO.dept(a.dept_id), filed = a.decision === 'filed', ok = filed || a.decision === 'approve';
      var word = filed ? 'filed #' + a.report_no + (a.verdict ? ' · ' + a.verdict : '') : ok ? 'approved' : 'rejected';
      return '<div class="card"><div class="t" style="display:flex;gap:6px;align-items:center;font-size:10.5px;color:var(--dim2)"><span class="st ' + (ok ? 'done' : 'failed') + '">' + word + '</span>' +
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
        (items.length ? items.map(function (m) { return '<div class="mem"><span class="k-' + m.kind + '">' + esc(m.kind) + '</span><div>' + esc(m.text) + '<i>' + CO.ago(m.at) + '</i></div></div>'; }).join('') : '<p class="empty">Nothing remembered yet.</p>') + '</div>';
    }).join('') || '<p class="empty">Nothing matches.</p>');
  }
  function renderAudit() {
    var S = CO.S, A = S.audit, days = Math.max(0, Math.ceil((A.next_at - S.clock) / 86400000));
    var stuck = S.tasks.filter(function (t) { return t.status === 'queued' && S.clock - t.created_at > 45 * 60000; }).length;
    var html = '<div class="kpis two"><div><b class="cy">' + days + 'd</b><span>next audit · ' + dayTime(A.next_at) + '</span></div><div><b>' + (A.last ? A.last.findings.length : 0) + '</b><span>tips last week</span></div>' +
      '</div>';
    html += A.last ? '<div class="card"><h3>Last audit · ' + dayTime(A.last.at) + '</h3>' + A.last.findings.map(function (f) {
      return '<div class="finding"><span><span class="tag k">' + esc(f.kind) + '</span></span><div>' + esc(f.detail) + (f.fix ? '<div class="fix">→ ' + esc(f.fix) + '</div>' : '') + '</div></div>';
    }).join('') + '</div>' : '<p class="empty">No audit yet: the first one runs a week after setup.</p>';
    setHTML($('audit'), html);
  }
  function renderInvest() {
    var S = CO.S, on = S.company.investable, done = 0, failed = 0, units = 0;
    S.departments.forEach(function (d) { var v = CO.deptView(d); done += v.done; failed += v.failed; units += v.units; });
    // investable is about backers; who may look inside is the Universe switch in Settings
    var html = RO ? '<p class="hint" style="margin:0 0 12px">' + (on ? 'Investable: backers can pledge USDC.' : 'Not investable: its owner has not opened it to backers.') + '</p>' :
      '<div class="switch' + (on ? ' on' : '') + '" data-a="invest"><span class="sw"></span><div><b>' + (on ? 'Investable' : 'Not investable') + '</b><span>' +
      (on ? 'Backers can pledge USDC; the scoreboard below is public.' : 'Nobody can back it yet. Flip to let backers pledge USDC.') + '</span></div></div>';
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
      '<label class="field">Share classes<input value="Ordinary, Preferred"></label><label class="field">Founders<input value="' + esc(S.company.owner || CO.ME) + ' · 100%"></label>' +
      '<label class="field">Option pool<input value="10%"></label><label class="field">Directors<input value="' + esc(S.company.owner || CO.ME) + '"></label>' +
      '<label class="field full">Governance<select><option>The owner decides</option><option>Board of directors</option><option>Token holders vote</option></select></label></div>' +
      '<div class="mf"><span class="hint" title="Cymetica publishes the stake it takes in companies formed here.">Cymetica\'s published stake: 1–10%</span><span class="sp"></span><button class="btn gr" data-a="form">Start formation</button></div></div>' +
      '<div class="card"><h3>Step by step</h3>' + [['Name and domicile', 'done'], ['Founders, shares and option pool', 'done'], ['Directors and governance', 'running'], ['Documents to sign', 'queued'], ['Registry filing', 'queued']].map(function (s, i) {
        return '<div class="trow" style="cursor:default"><span><span class="st ' + s[1] + '">' + (s[1] === 'running' ? 'now' : s[1] === 'queued' ? 'next' : 'done') + '</span></span><div><b>' + (i + 1) + '. ' + s[0] + '</b></div><i></i></div>';
      }).join('<div style="height:6px"></div>') + '<p class="hint">Formation is paper until you approve the filing.</p></div></div>');
    if (RO) lockFields('legal');
  }
  function lockFields(id) { Array.prototype.forEach.call($(id).querySelectorAll('input, select, textarea'), function (el) { el.disabled = true; }); }
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
    if (RO) lockFields('token');
  }
  function renderSettings() {
    var S = CO.S, c = S.company, paused = c.status === 'paused';
    var keep = document.activeElement && $('settings').contains(document.activeElement);
    if (keep) return;
    if (RO) {
      var n = Math.max(1, S.departments.length);
      setHTML($('settings'), '<div class="cols2"><div class="card"><h3>Company</h3><dl class="rodl"><dt>Name</dt><dd>' + esc(c.name) + '</dd><dt>Owner</dt><dd>@' + esc(c.owner) + '</dd>' +
        '<dt>Mission</dt><dd>' + esc(c.mission) + '</dd><dt>Report style</dt><dd>' + esc(c.report_style) + '</dd><dt>Plan</dt><dd>' + esc(c.plan) + '</dd>' +
        '<dt>Status</dt><dd class="' + (paused ? '' : 'gr') + '">' + (paused ? 'Paused' : 'Active') + '</dd></dl></div>' +
        '<div class="card uvcard"><h3>In the Universe</h3><div class="uvset ro"><div class="uvprev">' + CO.skinSVG({ skin: c.skin, accent: c.accent, floors: n, seed: c.id, banner: c.name }) + '</div>' +
        '<dl class="rodl"><dt>Visibility</dt><dd class="cy">Public: anyone can look inside</dd><dt>Station</dt><dd>' + esc(CO.skinName(c.skin)) + ' · ' + n + ' deck' + (n === 1 ? '' : 's') + '</dd></dl></div></div></div>');
      pv3(document.querySelector('#settings .uvprev'), { skin: c.skin, accent: c.accent, floors: n, seed: c.id, name: c.name, public: true });
      return;
    }
    // the turning station survives a re-render: it moves into the new card instead of starting again
    var oldPv = $('st-prev'), keepPv = oldPv && oldPv.__pv;
    settingsHTML(S, c, paused);
    var nuPv = $('st-prev');
    if (keepPv && nuPv && nuPv !== oldPv && !keepPv.dead) { nuPv.appendChild(keepPv.wrap); nuPv.__pv = keepPv; keepPv.el = nuPv; nuPv.classList.add('has3d'); }
    pv3(nuPv, myPv());
    thumbs3($('settings'), CO.profile().accent);
  }
  function settingsHTML(S, c, paused) {
    setHTML($('settings'), uvCard() + '<div class="cols2"><div class="card"><h3>Company</h3><div class="form">' +
      '<label class="field">Name<input id="st-name" maxlength="60" value="' + esc(c.name) + '"></label>' +
      '<label class="field">Report style<select id="st-report">' + ['Short, numbers first', 'Daily digest', 'Every result'].map(function (x) { return '<option' + (x === c.report_style ? ' selected' : '') + '>' + x + '</option>'; }).join('') + '</select></label>' +
      '<label class="field full">Mission<textarea id="st-mission" maxlength="500">' + esc(c.mission) + '</textarea></label></div>' +
      '<div class="mf"><span class="sp"></span><button class="btn gr" data-a="st-save">Save</button></div></div>' +
      '<div><div class="card"><h3>Plan and running</h3>' +
      '<div class="switch' + (S.budget.extra.on ? ' on' : '') + '" data-a="extra"><span class="sw"></span><div><b>Extra usage ' + (S.budget.extra.on ? 'on' : 'off') + '</b><span>At 0 the company ' + (S.budget.extra.on ? 'keeps running on extra usage' : 'pauses until the reset') + '.</span></div></div>' +
      '<div style="height:10px"></div><div class="switch' + (paused ? '' : ' on') + '" data-a="pause"><span class="sw"></span><div><b>' + (paused ? 'Paused' : 'Active') + '</b><span>' + (paused ? 'Nothing new starts.' : 'Your departments work on their own.') + '</span></div></div>' +
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
    // one line in plain words: is anyone working, and if not, why not
    var heart;
    if (S.company.status === 'paused') heart = '<span class="stop">Paused: nothing runs until you resume</span>';
    else if (!g.ok) heart = '<span class="stop">' + (g.code === 'cap' ? 'Daily limit reached' : 'Plan used up') + (g.until ? ': back at ' + hhmm(g.until) : '') + '</span>';
    else heart = (working ? '<span class="hot">' + working + ' working now</span>' : 'Waiting for the next job') + (g.code === 'extra' ? ' · <span class="hot">on extra usage</span>' : '');
    $('co-heart').innerHTML = heart;
    var ur = $('us-r');
    ur.textContent = g.code === 'extra' ? 'on extra usage · resets in ' + hm(b.session.resets_at - S.clock) : 'Resets in ' + hm(b.session.resets_at - S.clock);
    ur.classList.toggle('ex', g.code === 'extra');
    $('uw-r').textContent = 'Resets ' + dayTime(b.week.resets_at);
    var lv = $('live');
    if (S.company.status === 'paused') { lv.className = 'live paused'; lv.innerHTML = '<i></i>PAUSED'; }
    else if (!g.ok) { lv.className = 'live stop'; lv.innerHTML = '<i></i>' + (g.code === 'cap' ? 'DAILY LIMIT REACHED' : 'PLAN USED UP'); }
    else { lv.className = 'live'; lv.innerHTML = '<i></i>LIVE' + (working ? ' · ' + working + ' WORKING' : ''); }
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
      if (rk === 'hub') return '<b>Manager</b> · routes ' + c.open + ' open<br>' + (S.company.status === 'paused' ? 'paused' : RO ? 'plans the next pass · click to read its chat' : 'plans the next pass · click to message it');
      if (rk === 'you') return '<b>You</b> · ' + (S.approvals.length ? '<span class="r">' + S.approvals.length + ' to approve</span>' : 'nothing waits for you');
      if (rk === 'audit') return '<b>Supervisor</b> · runs the weekly audit';
      var d = CO.dept(+rk.slice(1)); if (!d) return '';
      var v = CO.deptView(d), e = v.experts[i]; if (!e) return '';
      return '<b>' + esc(e.name) + '</b> · ' + esc(d.name) + '<br>' + (e.state === 'working' && v.running ? '<span class="c">working on</span> “' + esc(v.running.title) + '”' : 'idle');
    }
    if (key === 'hub') return '<b>Manager</b> · ' + (RO ? 'its chat' : 'your chat') + (S.approvals.length ? ' · <span class="r">' + S.approvals.length + (RO ? ' wait for its owner' : ' need' + (S.approvals.length === 1 ? 's' : '') + ' you') + '</span>' : '') + '<br>click to open';
    if (key === 'you') return '<b>Your desk</b> · ' + (S.approvals.length ? '<span class="r">' + S.approvals.length + ' approvals waiting</span>' : 'all clear') + '<br>click to open Approvals';
    if (key === 'audit') {
      var A = S.audit;
      return '<b>Weekly audit</b> · next in ' + Math.max(0, Math.ceil((A.next_at - S.clock) / 86400000)) + 'd · ' + (A.last ? A.last.findings.length : 0) + ' findings last week<br>click to open Audit';
    }
    if (key === 'lot') return '<b>Add a department</b><br>click to staff a new room';
    if (key === 'vault') {
      if (RO) return '<b>Vault</b> · private<br>only its owner sees inside';
      var VT = CO.vaultTotals();
      return '<b>Vault</b> · <span class="g">' + CO.fmtEt(VT.et10) + ' ET10</span> · <span class="bl">' + CO.fmtUsd(VT.usdc) + ' USDC</span><br>click for where it came from';
    }
    var dd = CO.dept(+String(key).slice(1)); if (!dd) return '';
    var ln = CO.deptLine(dd), col = { cyan: 'c', blue: 'bl', red: 'r', dim: '' }[ln.tone];
    return '<b>' + esc(dd.name) + '</b><br><span class="' + col + '">' + esc(ln.text) + '</span><br><span style="color:var(--dim2)">click to open</span>';
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
      '<div class="mf"><span class="hint">asked ' + CO.ago(a.created_at) + ' ago' + (RO ? ' · waits for its owner' : '') + '</span><span class="sp"></span><button class="btn" data-a="close">Close</button>' +
      (RO ? '' : '<button class="btn rd" data-a="reject">Reject</button><button class="btn gr" data-a="approve">Approve</button>') + '</div>', true, function (act) {
      if (RO) return;
      if (act === 'approve' || act === 'reject') { closeModal(); decide(a.id, act); }
    });
  }
  function deptCard(t, on) {
    var used = CO.S.departments.some(function (d) { return d.key === t.key && t.key !== 'custom'; });
    return '<button class="tcard' + (on ? ' on' : '') + '" data-tpl="' + t.key + '"><div class="art">' + CO.deptArt(t.key) + '</div>' +
      '<b>' + esc(t.name || 'Custom') + '</b><span>' + esc(CO.DEPT_INFO[t.key] || '') + '</span>' +
      '<div class="minis">' + t.experts.map(function (k) { return '<i title="' + esc(CO.expertName(k)) + '">' + CO.expertArt(k, true) + '</i>'; }).join('') +
      (used ? '<em>you have one</em>' : '') + '</div></button>';
  }
  function expertCard(e, on) {
    var info = CO.EXPERT_INFO[e.key] || { line: '' };
    return '<button class="xcard' + (on ? ' on' : '') + '" data-ex="' + e.key + '"><div class="fig">' + CO.expertArt(e.key) + '</div>' +
      '<b>' + esc(e.name) + '</b><span>' + esc(info.line) + '</span><i class="ck">' + (on ? '✓ hired' : '+ hire') + '</i></button>';
  }
  function slider(id, html) {
    return '<div class="slider"><button type="button" class="sl-arrow l" data-sl="' + id + '" data-d="-1" tabindex="-1">‹</button>' +
      '<div class="sl-track" id="' + id + '">' + html + '</div><button type="button" class="sl-arrow r" data-sl="' + id + '" data-d="1" tabindex="-1">›</button></div>';
  }
  function deptForm(o, edit) {
    var tpls = edit ? '' : '<div class="sec step">1 · PICK A DEPARTMENT</div>' + slider('tpl-track', CO.TEMPLATES.map(function (t) { return deptCard(t, t.key === o.key); }).join(''));
    return tpls + '<div class="sec step">' + (edit ? '' : '2 · ') + 'HIRE ITS EXPERTS <span id="ex-n">' + o.experts.length + ' hired</span></div>' +
      slider('ex-track', CO.EXPERTS.map(function (e) { return expertCard(e, o.experts.indexOf(e.key) >= 0); }).join('')) +
      '<div class="sec step">' + (edit ? '' : '3 · ') + 'NAME AND CHARTER</div>' +
      '<div class="form"><label class="field">Department name<input id="df-name" maxlength="60" value="' + esc(o.name) + '" placeholder="e.g. Growth"></label>' +
      '<div class="field">Who works there<div class="hiredline" id="df-hired">' + hiredLine(o.experts) + '</div></div>' +
      '<label class="field full"><span>Charter · your rules, notes and lessons <span id="df-n" style="float:right">' + o.charter.length + ' / 2,000</span></span><textarea id="df-ch" maxlength="2000" rows="5">' + esc(o.charter) + '</textarea></label></div>';
  }
  function hiredLine(keys) {
    return keys.length ? keys.map(function (k) { return '<span class="hx"><i>' + CO.expertArt(k, true) + '</i>' + esc(CO.expertName(k)) + '</span>'; }).join('') : '<span class="hint">nobody yet: hire at least one</span>';
  }
  function hiredKeys() {
    return Array.prototype.map.call(document.querySelectorAll('#ex-track .xcard.on'), function (x) { return x.getAttribute('data-ex'); });
  }
  function readDeptForm() {
    return { name: $('df-name').value.trim(), charter: $('df-ch').value.trim(), experts: hiredKeys() };
  }
  function toggleExpert(card, on) {
    card.classList.toggle('on', on);
    card.querySelector('.ck').textContent = on ? '✓ hired' : '+ hire';
    var k = hiredKeys();
    $('ex-n').textContent = k.length + ' hired';
    $('df-hired').innerHTML = hiredLine(k);
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
        o = { key: t.key, name: t.name, experts: t.experts.slice(), charter: t.charter };
        Array.prototype.forEach.call(document.querySelectorAll('#tpl-track .tcard'), function (c) { c.classList.toggle('on', c === el); });
        Array.prototype.forEach.call(document.querySelectorAll('#ex-track .xcard'), function (c) { toggleExpert(c, o.experts.indexOf(c.getAttribute('data-ex')) >= 0); });
        $('df-name').value = t.name; $('df-ch').value = t.charter; $('df-n').textContent = t.charter.length + ' / 2,000';
        el.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
        if (!t.name) $('df-name').focus();
      } else if (a === 'create') {
        var f = readDeptForm();
        if (!f.name) { $('df-name').focus(); $('df-name').style.borderColor = 'var(--red)'; return; }
        if (!f.experts.length) { toast('Hire at least one expert.'); return; }
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
      '<div class="mf"><button class="btn rd" data-a="remove">Delete department</button><span class="sp"></span><button class="btn" data-a="close">Cancel</button><button class="btn gr" data-a="save">Save</button></div>', true, function (a) {
      if (a === 'save') { var f = readDeptForm(); if (!f.name) return; closeModal(); CO.act.editDept(id, f); ui.dirty = false; $('dr-ch-text').value = CO.dept(id).charter; renderDrawer(); }
      if (a === 'remove') deleteDeptModal(id);
    });
  }
  // deleting a department asks once: its work stops, its room goes, what it learned stays readable
  function deleteDeptModal(id) {
    var d = CO.dept(id); if (!d) return;
    openModal('<div class="mh"><h3>Delete ' + esc(d.name) + '?</h3></div><p>Its open tasks are cancelled and its room is cleared. What it learned stays readable in the Memory tab.</p>' +
      '<div class="mf"><span class="sp"></span><button class="btn" data-a="close">Cancel</button><button class="btn rd" data-a="really">Delete</button></div>', false, function (b) {
      if (b === 'really') { closeModal(); closeDrawer(); CO.act.removeDept(id); toast(d.name + ' deleted.'); }
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
  function sendMessage(text, deptId) {
    if (!text) return;
    CO.act.message(text, deptId);
    office.packet('you', 'hub', 'blue');
  }

  // what a visitor may still press: moving around and reading. Everything else that writes says so instead.
  var RO_OK = '#tabs button, #back, .dswitch [data-sw], .dept, #earn .er, [data-a="vault"], #co-waiting, #z-in, #z-out, #z-fit, .trow, tr.row, #dr-tasks-all, #dr-mem-t, ' +
    '[data-r], [data-a="close"], [data-a="appr"], #simbar [data-speed], #sim-reset, #ro-back, [data-mock], #modal, #vt button, .p3, .p3need';
  function roBlocked(t) { return !t.closest(RO_OK) && !!t.closest('button, [data-a], [data-d], .switch, [data-rpd]'); }
  function bind() {
    document.addEventListener('click', function (e) {
      var t = e.target;
      if (RO && roBlocked(t)) { e.preventDefault(); toast('Read only: only @' + CO.S.company.owner + ' can change this.'); return; }
      if (t.closest('#ro-back')) { location.href = 'index.html#universe'; return; }
      if (t.closest('#sim-new')) return createCompanyModal();
      var uvb = t.closest('#uvvt [data-uvv]'); if (uvb) return setUvView(uvb.getAttribute('data-uvv'));
      var lv = t.closest('#uvl-top [data-id]'); if (lv) return openFromLive(+lv.getAttribute('data-id'));
      var hs = t.closest('.uvhs'); if (hs) return openFromPic(hs.getAttribute('data-name'));
      if (t.closest('#uvpic-card')) return setTab('office');
      // our own station is on the live map only: Mine opens it there
      if (t.closest('#uv-me') && uvView() === 'pic' && uvl) return uvl.ping();
      if (t.closest('#uv-me') && uvView() === 'pic') { setUvView('3d'); setTimeout(function () { if (uv) uv.flyTo(0); }, 3600); return; }
      if (uv) {
        if (t.closest('#uv-in')) return uv.zoom(0.78);
        if (t.closest('#uv-out')) return uv.zoom(1.28);
        if (t.closest('#uv-fit')) return uv.fit(true);
        if (t.closest('#uv-me')) return uv.flyTo(0);
      }
      var mock = t.closest('[data-mock]');
      if (mock) { e.preventDefault(); toast('Mockup: ' + mock.getAttribute('data-mock') + ' is another page.'); return; }
      var tab = t.closest('#tabs button'); if (tab) return setTab(tab.getAttribute('data-tab'));
      if (t.closest('#co-pause')) { CO.act.pause(); toast(CO.S.company.status === 'paused' ? 'Paused: a running turn finishes, nothing new starts.' : 'Resumed: the next pass starts in a few seconds.'); return; }
      if (t.closest('#co-waiting')) return setTab('approvals');
      if (t.closest('[data-a="vault"]')) return openVault();
      var er = t.closest('#earn .er[data-id]'); if (er) return openDrawer(+er.getAttribute('data-id'));
      if (t.closest('#co-upgrade')) return upgradeModal();
      if (t.closest('#back')) return closeDrawer();
      var sw = t.closest('.dswitch [data-sw]'); if (sw) return sw.getAttribute('data-sw') === 'hub' ? openManager() : openDrawer(+sw.getAttribute('data-sw'));
      if (t.closest('.dept.mgrrow')) return openManager();
      if (t.closest('#add-dept') || t.closest('#rail-add')) return addDeptModal();
      var row = t.closest('.dept'); if (row) return openDrawer(+row.getAttribute('data-id'));
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
      var vb = t.closest('#vt [data-v]'); if (vb) return setView(vb.getAttribute('data-v'), true);
      if (t.closest('#z-in')) return office.zoom(0.78);
      if (t.closest('#z-out')) return office.zoom(1.28);
      if (t.closest('#z-fit')) return office.fit(true);
      // the drawer
      var dra = t.closest('#drawer [data-a]');
      if (dra) {
        var x = dra.getAttribute('data-a');
        if (x === 'close') return closeDrawer();
        if (x === 'edit') return editDeptModal(ui.panel);
        if (x === 'delete') return deleteDeptModal(ui.panel);
        if (x === 'prods') {
          var list = $('dr-prods').value.split(',').map(function (s) { return s.trim(); }).filter(Boolean);
          CO.act.products(ui.panel, list); $('dr-prods').blur(); renderDrawer(); return toast('Products saved: every run tests ' + (list.join(', ') || 'the public site') + '.');
        }
        if (x === 'runnow') { var rr = CO.act.runNow(ui.panel); return toast(rr ? 'Run queued at the top: it starts on the next pass.' : 'A run is already queued or running.'); }
        if (x === 'appr') { var first = $('appr').querySelector('.ai'); if (first) first.scrollIntoView({ behavior: 'smooth', block: 'center' }); return; }
      }
      var tr = t.closest('.trow[data-task], tr.row[data-task]');
      if (tr) { var tid = +tr.getAttribute('data-task'); ui.open[tid] = !ui.open[tid]; return render(); }
      if (t.closest('#dr-tasks-all')) { ui.tfDept = String(ui.panel); ui.tfStatus = ''; return setTab('tasks'); }
      if (t.closest('#dr-mem-t')) { ui.memOpen = !ui.memOpen; return renderDrawer(); }
      if (t.closest('#dr-ch-discard')) { ui.dirty = false; $('dr-ch-text').value = CO.dept(ui.panel).charter; charterMeta(); return; }
      // the other tabs
      var exb = t.closest('#nr-ex [data-ex]');
      if (exb) {
        $('nr-text').value = exampleSentence(CO.RULE_EXAMPLES[+exb.getAttribute('data-ex')]); $('nr-text').focus();
        return;
      }
      var rr = t.closest('.rule [data-a]');
      if (rr) {
        var rid = rr.closest('.rule').getAttribute('data-rule'), ra = rr.getAttribute('data-a'), rl = CO.S.rules.filter(function (x) { return x.id === rid; })[0];
        if (ra === 'rule-toggle' && rl) { CO.act.rule(rid, !rl.on); return toast('Rule ' + rid + (rl.on ? ' on.' : ' off.')); }
        if (ra === 'rule-del') { CO.act.removeRule(rid); return toast('Rule ' + rid + ' removed.'); }
        if (ra === 'rule-review') {
          var mode = rr.getAttribute('data-m');
          CO.act.review(rid, mode);
          return toast(mode === 'start' ? rid + ': waits for a person before it starts.' : mode === 'result' ? rid + ': its result waits for a person before it goes on.' : rid + ': no human review.');
        }
      }
      var pa2 = t.closest('.page [data-a]');
      if (pa2) return pageAct(pa2.getAttribute('data-a'), pa2);
      // modal
      if (t.id === 'modal') return closeModal();
      var ma = t.closest('#modal-card [data-a]');
      if (ma) { var m = ma.getAttribute('data-a'); if (m === 'close') return closeModal(); if (modalAct) modalAct(m, ma); return; }
      var tp = t.closest('#modal-card [data-tpl]'); if (tp && modalAct) return modalAct('tpl', tp);
      var xc = t.closest('#modal-card .xcard'); if (xc) { toggleExpert(xc, !xc.classList.contains('on')); return; }
      var sa = t.closest('#modal-card .sl-arrow');
      if (sa) { var tr = $(sa.getAttribute('data-sl')); tr.scrollBy({ left: +sa.getAttribute('data-d') * tr.clientWidth * 0.8, behavior: 'smooth' }); return; }
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
    $('compose').addEventListener('submit', function (e) { e.preventDefault(); var i = $('msg'); sendMessage(i.value.trim(), null); i.value = ''; });
    $('nr-form').addEventListener('submit', function (e) { e.preventDefault(); addRuleFromPage(); });
    // a department's daily token cap: the label follows the slider, the cap is set where it is let go
    $('dr-tok').addEventListener('input', function (e) {
      if (e.target.id !== 'dr-cap') return;
      $('dr-cap-v').textContent = capLabel(CO.CAP_STEPS[+e.target.value], CO.deptView(CO.dept(ui.panel)).perTurn);
    });
    $('dr-tok').addEventListener('change', function (e) {
      if (e.target.id !== 'dr-cap') return;
      var cap = CO.CAP_STEPS[+e.target.value], d = CO.dept(ui.panel);
      CO.act.cap(ui.panel, cap); e.target.blur();
      toast(cap ? d.name + ' spends at most ' + CO.fmtTok(cap) + ' a day; work over it waits for midnight.' : d.name + ' has no daily cap.');
    });
    $('dr-tok').addEventListener('click', function (e) {
      var b = e.target.closest('[data-rpd]'); if (!b) return;
      var n = +b.getAttribute('data-rpd'); CO.act.runsPerDay(ui.panel, n);
      toast(CO.dept(ui.panel).name + ' runs ' + n + '× a day.');
    });
    $('dr-charter').addEventListener('submit', function (e) {
      e.preventDefault(); var d = CO.dept(ui.panel); if (!d) return;
      CO.act.charter(d.id, $('dr-ch-text').value.trim()); ui.dirty = false; charterMeta(); toast('Charter saved: the next task of ' + d.name + ' starts from it.');
    });
    $('dr-ch-text').addEventListener('input', function () { ui.dirty = true; charterMeta(); });
    $('tf-dept').addEventListener('change', function (e) { ui.tfDept = e.target.value; renderTasks(); });
    $('tf-status').addEventListener('change', function (e) { ui.tfStatus = e.target.value; renderTasks(); });
    $('mem-q').addEventListener('input', function (e) { ui.memQ = e.target.value; renderMemory(); });
    document.addEventListener('input', function (e) {
      if (e.target.id === 'df-ch') { var n = $('df-n'); if (n) n.textContent = e.target.value.length + ' / 2,000'; }
      if (e.target.id === 'cc-name' && ui.ccPrev) ui.ccPrev();
    });
    document.addEventListener('change', function (e) {
      if (e.target.classList.contains('rvw')) { var rid2 = e.target.closest('.rule').getAttribute('data-rule'); var rl2 = CO.S.rules.filter(function (x) { return x.id === rid2; })[0]; if (rl2) { CO.act.review(rid2, rl2.review, e.target.value.trim() || 'you'); toast(rid2 + ': reviewed by ' + (e.target.value.trim() || 'you') + '.'); } }
      if (e.target.id === 'tk-chain') CO.S.token.chain = e.target.value;
      if (e.target.id === 'lg-dom') { CO.S.legal.domicile = e.target.value; toast('Domicile: ' + e.target.value); }
    });
    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape') return;
      if (!$('modal').hidden) return closeModal();
      if (ui.panel != null || ui.mgr) closeDrawer();
    });
  }
  function pageAct(a, el) {
    var S = CO.S;
    // the Universe card: who may look inside, the station and its colour; saved at once, the map follows
    if (a === 'uv-public' || a === 'uv-skin' || a === 'uv-accent') {
      var p = CO.profile();
      if (a === 'uv-public') p = CO.saveProfile({ public: !p.public });
      if (a === 'uv-skin') p = CO.saveProfile({ skin: el.getAttribute('data-k') });
      if (a === 'uv-accent') p = CO.saveProfile({ accent: el.getAttribute('data-k') });
      if (document.activeElement) document.activeElement.blur();
      renderSettings();
      if (uv) uv.setMine(mineForMap());
      return toast(a === 'uv-public' ? (p.public ? 'Public: anyone can look inside, read only.' : 'Private: others see its name, station and mission only.') :
        'Your station in the Universe: ' + CO.skinName(p.skin) + ', ' + p.accent + '.');
    }
    if (a === 'invest') { S.company.investable = !S.company.investable; CO.changed(); toast(S.company.investable ? 'Investable: backers can pledge.' : 'Not investable any more.'); }
    if (a === 'form') openModal('<div class="mh"><h3>Start formation?</h3></div><p>' + esc(S.legal.domicile) + ' · ' + esc(($('lg-name') || {}).value || S.legal.name) + '. Filing waits for your approval like everything real.</p>' +
      '<div class="mf"><span class="sp"></span><button class="btn" data-a="close">Cancel</button><button class="btn gr" data-a="go">Start</button></div>', false, function (b) { if (b === 'go') { closeModal(); toast('Mockup: nothing is filed.'); } });
    if (a === 'tk-reserve') { S.token.symbol = ($('tk-sym').value || 'CQA').toUpperCase().replace(/[^A-Z0-9]/g, '').slice(0, 6); S.token.chain = $('tk-chain').value; S.token.reserved = true; CO.changed(); toast(S.token.symbol + ' reserved.'); }
    if (a === 'tk-undo') { S.token.reserved = false; CO.changed(); }
    if (a === 'tk-launch') toast('Mockup: the launch page is another page.');
    if (a === 'perp') { S.token.perp_listed = true; CO.changed(); toast('Listed: CQA-PERP.'); }
    if (a === 'st-save') {
      CO.act.settings({ name: $('st-name').value.trim() || S.company.name, mission: $('st-mission').value.trim(), report_style: $('st-report').value });
      CO.saveProfile({ name: S.company.name, mission: S.company.mission });
      document.activeElement.blur(); renderSettings(); toast('Settings saved.');
    }
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
    CO.on('handoff', function (e) { office.packet('d' + e.from.id, 'd' + e.to.id, 'red'); });
    CO.on('submitted', function (e) { if (e.dept) { office.packet('d' + e.dept.id, 'hub', 'green'); } });
    CO.on('message', function () { office.packet('hub', 'you', 'cyan'); });
    // after the office changes shape, the camera goes back to what is in focus
    function reframe() { if (ui.mgr) office.focus('hub', 0, true); else if (ui.panel != null) office.focus('d' + ui.panel, 0, true); else office.fit(true); }
    CO.on('dept:new', function (d) { office.layout({ born: d.id }); if (ui.panel != null || ui.mgr) office.select(ui.mgr ? 'hub' : 'd' + ui.panel); setTimeout(reframe, 60); });
    CO.on('dept:edit', function () { office.layout(); });
    CO.on('dept:removed', function () { office.layout(); setTimeout(reframe, 60); });
    CO.on('reset', function () {
      closeModal(); ui.panel = null; $('drawer').hidden = true; office.sel = null; ui.open = {}; ui.prev = {};
      office.layout(); office.fit(true); markSeen();
      ['depts', 'appr', 'earn', 'msgs', 'legal', 'settings'].forEach(function (id) { $(id)._h = null; });
      if (uv) uv.setMine(mineForMap());
    });
    CO.on('office:click', function (key) {
      if (key.charAt(0) === 'd') return openDrawer(+key.slice(1));
      if (key === 'hub') return openManager();
      if (key === 'you') return setTab('approvals');
      if (key === 'audit') return setTab('audit');
      if (key === 'vault') return openVault();
      if (key === 'lot') return addDeptModal();
    });
    // people keep arriving at the apps: the vault, its plate and the Portfolio follow
    CO.on('vault', function () {
      if (office && office.update) office.update();
      if (ui.tab === 'office') renderEarned(ui.panel != null ? CO.dept(ui.panel) : null);
      if (ui.tab === 'portfolio') renderPortfolio();
    });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot); else boot();
})();
