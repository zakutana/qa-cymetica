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
  var TSTAT = { queued: 'next', running: 'working', waiting_approval: 'approval', done: 'done', failed: 'failed', cancelled: 'cancelled' };

  var ui = { tab: 'office', view: '2d', panel: null, open: {}, seen: {}, feedTop: 0, dirty: false, prev: {}, tfDept: '', tfStatus: '', memQ: '', memDept: null };
  var office, office2d = null, office3d = null;
  // RO: someone else's public company, looked at from the Universe; everything shows, nothing changes
  var RO = false;

  /* ---------------- the office: in 3D, or flat where 3D cannot start -- the same API either way ---------------- */
  // 3D first: the operator's pictures were the look to build to, and the live WebGPU scene is what he wants to see
  // ("ty textury a picture mody sou uplne nahovno", 2026-10-18); the flat office is the fallback and a choice
  function viewPref() { try { return (CO.Q && CO.Q.get('view')) || localStorage.getItem('co.view') || '3d'; } catch (e) { return '3d'; } }
  function setView(v, save) {
    if (v !== '2d' && v !== '3d') v = '3d';
    if (v === '3d' && !(CO.U3 && CO.U3.ok && CO.U3.office)) v = '2d';
    if (save) { try { localStorage.setItem('co.view', v); } catch (e) { /* fine */ } }
    ui.view = v;
    var st = $('stage');
    st.classList.toggle('is3d', v === '3d');
    Array.prototype.forEach.call(document.querySelectorAll('#vt button'), function (b) { b.classList.toggle('on', b.getAttribute('data-v') === v); });
    // the office's screens are canvases drawn once, in JetBrains Mono: built before the web font had come they kept the
    // browser's fallback (wider, thinner) until their text changed, as a first visit showed them. Built once it is
    // here, the stage blank meanwhile as it is while the 3D starts (1.5 s at most; no font at all: built at once).
    if (v === '3d' && !office3d && !monoWaited && !monoHere()) { monoWait(function () { monoWaited = true; if (ui.view === '3d' && !office3d) setView('3d'); }); return; }
    if (v === '3d') {
      // a 3D office that stopped (its graphics device lost, a frame that threw) starts again with the page: a second
      // office in the same page cannot use the textures the first one made ("Texture already initialized", tried
      // 2026-10-21), so the click reloads into 3D ("jak na 3D klikam nic se nedeje" -- it used to stay dead, silent)
      if (office3d && office3d.stopped) { try { localStorage.setItem('co.view', '3d'); } catch (e) { /* fine */ } location.reload(); return; }
      if (!office3d) {
        office3d = CO.U3.office($('office3d'), st, tipFor);
        office3d.onFail = function () { office3d = null; setView('2d'); toast('3D could not start in this browser: the flat office instead. Reload to try again.'); };
        office3d.onStop = function () { if (ui.view === '3d') { setView('2d'); toast('3D stopped in this browser. Click 3D to start it again.'); } };
        // the loading screen follows its first frame's shaders, and goes with that frame
        office3d.onProgress = function (f) { if (ui.tab === 'office') bootSet(30 + f * 66, 'RENDERING'); };
        office3d.onFirst = function () { if (ui.tab === 'office') bootDone(); warmDialog(); };
      }
      office = office3d;
    } else { office = office2d; if (ui.tab === 'office') bootDone(); }
    office.sel = ui.mgr ? 'hub' : ui.panel != null ? 'd' + ui.panel : null;
    // Back to a 3D office that is already built: brought up to date, not built again. A rebuild throws every room
    // away and compiles their shaders anew, a 2.2 s freeze on every 2D -> 3D switch (11 s at a quarter of the CPU,
    // measured 2026-10-19); update() still rebuilds it when a department was added, edited or removed meanwhile.
    if (office === office3d && office3d.cells && office3d.shapeKey === office3d.shape()) office.update();
    else office.layout();
    if (office === office3d) bootSet(30, 'RENDERING');
    requestAnimationFrame(function () {
      office.resize();
      if (ui.mgr) office.focus('hub', 0, true); else if (ui.panel != null) office.focus('d' + ui.panel, 0, true); else office.fit(false);
    });
  }
  var MONO = ['400', '500', '600', '700'].map(function (w) { return w + ' 16px "JetBrains Mono"'; }), monoWaited = false;
  function monoHere() { try { return !document.fonts || MONO.every(function (f) { return document.fonts.check(f); }); } catch (e) { return true; } }
  function monoWait(cb) {
    var done = false, fin = function () { if (!done) { done = true; cb(); } };
    try { Promise.all(MONO.map(function (f) { return document.fonts.load(f); })).then(fin, fin); } catch (e) { fin(); }
    setTimeout(fin, 1500);
  }
  // the 3D engine loads on its own: switch when it is there, if 3D is the choice. It says so itself (the co3d event
  // at the end of u3d.js), so nothing waits on a timer's next round; 8 s without it is a page without 3D.
  function whenEngine(cb) {
    var done = false, fin = function (ok) { if (done) return; done = true; window.removeEventListener('co3d', on); clearTimeout(late); cb(ok); };
    var on = function () { if (CO.U3 && (CO.U3.ok || CO.U3.failed)) fin(!!CO.U3.ok); };
    var late = setTimeout(function () { fin(!!(CO.U3 && CO.U3.ok)); }, 8000);
    window.addEventListener('co3d', on);
    on();
  }

  /* ---------------- the loading screen ---------------- */
  // Over the whole page until the office has drawn its first frame -- or, opened on it, the Universe -- and over the
  // Universe's stage while its map is made (boot.css), so the page never shows half built ("nevadi kdyz se neco
  // nacita ale musis tam nejakou brutalne top animaci zobrazit misto toho", 2026-10-20). Its number is the work done.
  var boot0 = $('boot'), bootP = 0;
  function ldSet(root, p, what) {
    if (!root) return;
    root.querySelector('.ld-pct').textContent = Math.round(p);
    root.querySelector('.ld-bar i').style.transform = 'scaleX(' + Math.min(1, p / 100).toFixed(3) + ')';
    if (what) root.querySelector('.ld-what').textContent = what;
  }
  function bootSet(p, what) { if (!boot0 || p <= bootP) return; bootP = p; ldSet(boot0, p, what); }
  function bootDone() {
    var el = boot0; if (!el) return; boot0 = null;
    ldSet(el, 100, 'READY');
    setTimeout(function () { el.classList.add('gone'); setTimeout(function () { el.remove(); }, 900); }, 150);
  }
  bootSet(6, 'LOADING');
  setTimeout(bootDone, 30000);   // (never in the way for good)
  // the map's stage: its own loading screen while it is made, gone once it has drawn
  function uvLoad(on, p) { var el = $('uvload'); if (!el) return; if (p != null) ldSet(el, p, 'UNIVERSE'); el.hidden = !on; }
  function afterFrame(o, cb) {
    var f0 = o.frames || 0, t0 = performance.now();
    (function w() { if (!o.renderer || (o.frames || 0) > f0 || performance.now() - t0 > 3000) return cb(); requestAnimationFrame(w); })();
  }

  /* ---------------- boot ---------------- */
  function boot() {
    CO.S = CO.fresh(Date.now());
    RO = !!CO.RO;
    CO.applySetup();
    if (RO) roSetup();
    office = office2d = new CO.Office($('office'), $('stage'), tipFor);
    office.layout();
    bootSet(14, 'ENGINE');
    Array.prototype.forEach.call(document.querySelectorAll('#vt button'), function (b) { b.classList.toggle('on', b.getAttribute('data-v') === '2d'); });
    whenEngine(function (ok) {
      if (ok && viewPref() !== '2d') { bootSet(22, 'OFFICE'); setView('3d'); }
      else if (location.hash !== '#universe') bootDone();   // the flat office is drawn already
      if (ok) afterOffice(prebuildUniverse);
    });
    markSeen();
    bind();
    wire();
    CO.on('change', render);
    CO.on('tick', clock);
    render();
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { if (!office.moved && !office.sel) office.fit(false); $('msgs').scrollTop = 1e6; });
    window.addEventListener('resize', function () { $('msgs').scrollTop = 1e6; });
    if (CO.denied) setTimeout(function () { toast(CO.denied); }, 500);
    // a company is made on the entry (start.html, builder.html); a pre-built one comes with its departments
    if (CO.MODE === 'new') { location.href = 'start.html'; return; }
    if (CO.Q.has('created')) setTimeout(function () {
      if (CO.S.departments.length) return toast('Created: ' + CO.S.company.name + ', ' + CO.S.departments.length + ' departments.');
      toast('Created: ' + CO.S.company.name + '. Add its first department.'); addDeptModal();
    }, 600);
    if (location.hash === '#universe') setTab('universe');
    // back from a visit through the browser's cache: the page comes back as it was left, fade and all
    window.addEventListener('pageshow', function (e) { if (e.persisted) $('uvfade').hidden = true; });
  }
  // the visitor's frame: a bar saying whose company this is and that it is read only
  function roSetup() {
    var c = CO.S.company;
    document.body.classList.add('ro');
    $('robar').hidden = false;
    $('ro-t').innerHTML = 'Inside <b>' + esc(c.name) + '</b> by <b>@' + esc(c.owner) + '</b><em>· you can look at its office, departments and processes; only its owner can change them</em>';
    document.title = c.name + ' · Universe';
    // What a public company keeps to itself (the operator, 2026-10-21: "Tasks, memory, waits for owner a audit by mely
    // byt privatni, to muzou skryt uplne ty taby v tom nahledu"): those four tabs are not in a visit at all, nor the panel of
    // what waits for the owner, nor the chat with NEXUS. The office, the departments (charters, experts, what they
    // are doing now), the processes and the Universe stay.
    ['tasks', 'approvals', 'memory', 'audit'].forEach(function (k) { var b = document.querySelector('#tabs [data-tab="' + k + '"]'); if (b) b.hidden = true; });
    ['p-appr', 'co-waiting'].forEach(function (id) { var e = $(id); if (e) e.hidden = true; });
    var rs = document.querySelector('[data-pane="rules"] .sub'); if (rs) rs.textContent = 'the processes its owner wrote';
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
    // the logo: the company's station as a line icon in the company's colour (CO.stationIcon, uv-data.js)
    var lp = RO ? c : CO.profile(), lsrc = (lp.skin || 'dome') + '-' + (lp.accent || 'green'), lg = $('co-logo');
    if (lg._src !== lsrc) { lg._src = lsrc; lg.innerHTML = CO.stationIcon(lp.skin || 'dome', lp.accent || 'green'); lg.title = c.name; }
    var st = $('co-status'); st.textContent = paused ? 'PAUSED' : 'RUNNING'; st.className = 'pill ' + (paused ? 'off' : 'on');
    $('co-pause').textContent = paused ? 'Resume' : 'Pause';
    // what the company earned lives in its vault (the office and the right column), not in this bar
    var n = S.approvals.length, w = $('co-waiting');
    w.innerHTML = n ? '<b>' + n + '</b> ' + (RO ? 'wait' + (n === 1 ? 's' : '') + ' for its owner' : 'approval' + (n === 1 ? '' : 's')) : '';
    w.hidden = !n;
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

  // each department's icon (CO.deptIconOf, data.js), as the rail and the drawers show it
  function deptIcon(d) {
    var ic = CO.deptIconOf(d);
    return '<span class="dic" style="--ic:' + ic[0] + '"><svg viewBox="0 0 20 20" aria-hidden="true">' + ic[1] + '</svg><i class="dot"></i></span>';
  }
  CO.deptIcon = deptIcon;
  function renderRail() {
    var S = CO.S;
    $('rail-n').textContent = S.departments.length;
    var cc = CO.counts();
    // Each card says three things: who, what it is doing now, and one number. The rest is one click away.
    var na = S.approvals.length;
    var mrow = '<button class="dept mgrrow working" title="' + (RO ? 'Read its chat with NEXUS' : 'Open your chat with NEXUS') + '">' + deptIcon('hub') + '<div class="d1"><b>Command</b>' +
      (na ? '<span class="et red">' + na + (RO ? ' wait for owner' : ' approval' + (na === 1 ? '' : 's')) + '</span>' : '') + '</div>' +
      '<div class="dl"><span class="tx cyan">Chat · runs every department</span></div></button>';
    setHTML($('depts'), mrow + S.departments.map(function (d) {
      var v = CO.deptView(d), ln = CO.deptLine(d, v);
      return '<button class="dept ' + v.status + (ln.tone === 'red' ? ' needs' : '') + (ui.panel === d.id ? ' on' : '') + (d.born && S.clock - d.born < 4000 ? ' born' : '') + '" data-id="' + d.id + '">' +
        deptIcon(d) + '<div class="d1"><b>' + esc(d.name) + '</b>' +
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
    var head = RO ? 'WAITING FOR ITS OWNER' : 'APPROVALS';
    $('ap-t').textContent = fd ? head + ' · ' + fd.name.toUpperCase() : head;
    $('ap-n').textContent = n || '';
    $('p-appr').classList.toggle('none', !n);
    setHTML($('appr'), n ? apprs.map(function (a) { return apprCard(a, false); }).join('') : '<p class="empty ok">' + (RO ? 'Nothing waits for its owner' : 'No approvals') + (fd ? ' from ' + esc(fd.name) : '') + '.</p>');
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
    // it shows only while the vault is open: clicked in the office (the operator, 2026-10-19: "ten vault napravo
    // zobrazis jen kdyz nekdo klikne na trezor")
    $('p-earn').hidden = ui.vault !== 'vault';
    renderOps();
    var V = CO.vaultTotals();
    if (RO) { $('earn-n').textContent = ''; setHTML($('earn'), '<p class="empty"><i class="lk"></i> Private: only its owner sees inside the vault.</p>'); return; }
    $('earn-n').textContent = '';
    var rows = vaultRows(), top = Math.max(1, V.earnedEt10);
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
      '<div class="vbig"><div><b class="g">' + CO.fmtEt(V.et10) + '</b><span>ET10 · your account balance</span></div><div><b class="u">' + CO.fmtUsd(V.usdc) + '</b><span>USDC · your account balance</span></div></div>' +
      '<div class="sec">EARNED BY THE COMPANY <span>' + CO.fmtEt(V.earnedEt10) + ' ET10 · ' + CO.fmtUsd(V.earnedUsdc) + ' USDC, already in the balance</span></div><div class="sec">BY DEPARTMENT</div>' + list('dept') + '<div class="sec">BY APP <span>proposed: ' + R.et10PerVisitor + ' ET10 a visitor, ' + R.usdcPerUse + ' USDC a use (placeholder rates)</span></div>' + list('app'), true);
  }

  // the conversation with the Manager: all of it in the Manager's focus, one department's in its detail
  function chatHTML(msgs, tagged) {
    var S = CO.S, cut = S.cleared_to || 0;
    msgs = msgs.filter(function (m) { return m.id > cut; });
    var last = msgs[msgs.length - 1];
    var mh = (cut ? '<div class="msgclr" title="/clear empties this window only. The messages stay on your account: the Supervisor\'s audit and NEXUS\'s memory still read all of them.">Cleared ' + hhmm(S.cleared_at) + ' · history kept for the audit</div>' : '') + msgs.map(function (m) {
      var md = tagged && m.dept_id ? CO.dept(m.dept_id) : null;
      return '<div class="msg' + (m.role === 'owner' ? ' me' : '') + '"><em>' + (m.role === 'owner' ? 'You' : 'NEXUS') + ' · ' + hhmm(m.at) +
        (md ? '<span class="tagd">' + esc(md.name) + '</span>' : '') + '</em>' + esc(m.text) +
        (m.images && m.images.length ? '<div class="mimgs">' + m.images.map(function (p) { return '<img alt="' + esc(p.name) + '" src="' + p.src + '">'; }).join('') + '</div>' : '') + '</div>';
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
      fillChat($('msgs'), chatHTML(S.messages, true) || '<p class="hint">' + (RO ? 'No messages yet.' : 'No messages yet. Say hello to NEXUS: ask how it goes, give it work, or tell it to add a department.') + '</p>');
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
    ui.panel = id; ui.mgr = false; ui.vault = false; document.body.classList.remove('vopen'); $('mgr').hidden = true;
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
    ui.panel = null; ui.mgr = true; ui.vault = false; document.body.classList.remove('vopen'); $('drawer').hidden = true; $('mgr').hidden = false; $('msgs')._h = null;
    document.body.classList.add('focus');
    $('back').hidden = false; $('where').hidden = false; $('where').textContent = 'Command';
    office.select('hub');
    render();
    setTimeout(function () { $('msg').focus(); }, 60);
    clearTimeout(ui.flyT);
    ui.flyT = setTimeout(function () { office.focus('hub', 0, true); }, was ? 0 : 520);
  }
  // Operations opened from the office: its room and, on the right, what it does and when it audits next; the
  // Audit tab is one link away ("jak kliknu na operations tak taky se ma zoomnout mistnost a az pres link se ma jit na Audit")
  function renderOps() {
    var el = $('p-ops'); el.hidden = ui.vault !== 'audit'; if (el.hidden) return;
    var S = CO.S, A = S.audit, days = Math.max(0, Math.ceil((A.next_at - S.clock) / 86400000));
    setHTML($('ops'), '<div class="kpis two"><div><b class="cy">' + days + 'd</b><span>next audit</span></div><div><b>' + (A.last ? A.last.findings.length : 0) + '</b><span>tips last week</span></div></div>' +
      '<p class="hint">Audits every process once a week: wasted work, duplicates, stuck flows. Keeps the company optimised.</p>' +
      '<button class="btn cy" type="button" id="ops-open">Open Audit →</button>');
  }
  function openOpsRoom() { openVaultRoom('audit'); }
  // the vault opened from the office: the camera goes to its room and the right column shows what it holds
  function openVaultRoom(key) {
    key = key === 'audit' ? 'audit' : 'vault';
    if (ui.tab !== 'office') setTab('office');
    var was = ui.panel != null || ui.mgr;
    ui.panel = null; ui.mgr = false; ui.vault = key; $('drawer').hidden = true; $('mgr').hidden = true;
    document.body.classList.remove('focus'); document.body.classList.add('vopen');
    $('back').hidden = false; $('where').hidden = false; $('where').textContent = key === 'audit' ? 'Operations' : 'Vault';
    office.select(key);
    render();
    clearTimeout(ui.flyT);
    ui.flyT = setTimeout(function () { office.focus(key, 0, true); }, was ? 520 : 0);
  }
  function closeDrawer() {
    if (ui.panel == null && !ui.mgr && !ui.vault) return;
    ui.panel = null; ui.mgr = false; ui.vault = false; $('drawer').hidden = true; $('mgr').hidden = true;
    document.body.classList.remove('focus', 'vopen');
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
    // its page on cymetica.com, one click from its head
    var lk = CO.DEPT_LINK[d.key];
    // one icon a page (the Trading desk has two: My bots, a globe; Agent Tournaments, a cup)
    var GLOBE = '<svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="9" cy="11" r="6.2"/><ellipse cx="9" cy="11" rx="2.6" ry="6.2"/><path d="M2.8 11h12.4 M3.9 7.8h10.2 M3.9 14.2h10.2 M12.6 2.6h4.8v4.8 M17.4 2.6l-5.2 5.2"/></svg>',
      CUP = '<svg viewBox="0 0 20 20" aria-hidden="true"><path d="M6 3.5h8v4.2a4 4 0 0 1-8 0Z M6 5H3.4v1.4A2.6 2.6 0 0 0 6 9 M14 5h2.6v1.4A2.6 2.6 0 0 1 14 9 M10 11.7v2.8 M6.8 17h6.4 M7.6 14.5h4.8V17H7.6Z"/></svg>';
    var lks = lk ? [lk].concat((CO.DEPT_LINK_MORE || {})[d.key] || []) : [];
    var pgi = lks.map(function (x, i) {
      var nm = x.label.split(':')[0];
      return '<a class="pgi" href="' + esc(x.url) + '" target="_blank" rel="noopener" title="' + esc(nm) + ' on cymetica.com" aria-label="Open ' + esc(nm) + '">' + (/tournament/i.test(nm) ? CUP : GLOBE) + '</a>';
    }).join('');
    setHTML($('dr-head'), '<i class="dot ' + v.status + (ln.tone === 'red' ? ' needs' : '') + '"></i><h2>' + esc(d.name) + '</h2>' +
      (d.files_as ? '<span class="et ' + (d.et10 ? 'lit' : 'zero') + '" title="ET10 Cymetica paid for accepted bugs, to ' + esc(d.files_as) + '">' + (d.et10 ? '+' : '') + (d.et10 || 0).toLocaleString('en-US') + ' ET10</span>' : '') +
      '<span class="x">' + pgi + (RO ? '' : '<button class="btn" data-a="edit">Edit</button><button class="btn rd" data-a="delete" title="Delete this department">Delete</button>') + '</span>');
    // what it is doing right now, in one line: the first thing anyone wants to know
    setHTML($('dr-now'), '<div class="now t-' + ln.tone + '"><p>' + esc(ln.text) + '</p>' +
      (appr.length ? '<button class="btn rd" type="button" data-a="appr">Open</button>' : '') + (v.running ? '<span class="run"><i></i></span>' : '') + '</div>');
    // the charter is read and changed in Edit ("charter defaultne skryj, jen v nejakem editu se zobrazi"); a visitor,
    // who has no Edit, reads it here
    $('dr-charter').hidden = !RO;
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
      (d.schedule ? '<div class="rpd"><span class="l">' + (d.key === 'testing' ? 'Bug hunts a day' : 'Runs a day') + '</span>' + [1, 2, 3, 4, 6, 12].map(function (n) {
        return '<button type="button" data-rpd="' + n + '"' + (n === runsNow ? ' class="on"' : '') + '>' + n + '×</button>';
      }).join('') + '</div>' : '')) + '</div>';
    var tk = $('dr-tok');
    if (tk._h !== tokHtml && document.activeElement !== $('dr-cap')) { tk._h = tokHtml; tk.innerHTML = tokHtml; }
    // a department on a clock: its runs, products, who the bugs are filed as, what they earned
    var runsHtml = '';
    if (d.schedule) {
      var hunt = d.key === 'testing';
      runsHtml = '<div class="runs"><div class="sec">' + (hunt ? 'BUG HUNTS' : 'RUNS') + ' <span>' + esc(d.schedule.label) + '</span></div>' +
        '<div class="rk" style="grid-template-columns:repeat(2,1fr)"><div><b>' + hhmm(d.next_run) + '</b><span>' + (hunt ? 'next bug hunt' : 'next run') + '</span></div>' +
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
    return '<button data-sw="hub"' + (on === 'hub' ? ' class="on"' : '') + '><i class="dot working"></i>Command</button>' + CO.S.departments.map(function (x) {
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
    ({ portfolio: renderPortfolio, tasks: renderTasks, approvals: renderApprovals, memory: renderMemory, audit: renderAudit, rules: renderRules, investable: renderInvest, legal: renderLegal, token: renderToken, connect: renderConnect, settings: renderSettings, universe: renderUniverse }[ui.tab] || function () {})();
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
  // the 3D renderer could not start here: the flat map takes its place (shown when its tab is, if it failed while it
  // was being built ahead)
  function uvTo2D() {
    var st = $('uvstage'); st.classList.remove('is3d'); st.classList.add('is2d'); $('uvbans').innerHTML = '';
    uv = new CO.Universe($('uvmap'), st, uvHooks()); CO.uv = uv; uv.layout(); uvLaid = true;
    if (ui.tab === 'universe') finishShow(true); else uvShown = false;
  }
  // The Universe is the live 3D map, the flat one where 3D cannot start. The painted picture and the map composed
  // from his generated pieces are gone ("ty textury a picture mody sou uplne nahovno", 2026-10-18).
  function showUniverse() { show3D(); }
  // the 3D map when the browser can draw it (WebGPU, or WebGL2), the flat one otherwise
  var uvLaid = false, uvShown = false;
  function show3D() {
    if (!uv) {
      var t0 = Date.now();
      $('uvstage').classList.add('loading'); uvLoad(true, 8);
      (function wait() {
        if (uv) return;
        if (CO.U3 && CO.U3.ok) { uv = CO.U3.universe($('uv3d'), $('uvstage'), uvHooks()); $('uvstage').classList.add('is3d'); }
        else if ((CO.U3 && CO.U3.failed) || Date.now() - t0 > 6000) { uv = new CO.Universe($('uvmap'), $('uvstage'), uvHooks()); $('uvstage').classList.add('is2d'); }
        else return setTimeout(wait, 60);
        $('uvstage').classList.remove('loading');
        CO.uv = uv;   // a handle for looking at the map from the console
        uv.layout(); uvLaid = true;
        whenWarm(true);
      })();
      return;
    }
    // built ahead (prebuildUniverse): whatever step it had not reached yet is done now
    if (!uvLaid) { if (uvLay) { uvLay.forEach(function (f) { f(); }); uvLay = null; } else uv.layout(); uvLaid = true; }
    whenWarm(!uvShown);
  }
  // Shown once its shaders are made (warm(), a piece at a time), the flight in starting then: not built ahead (the page
  // opened on the map) its first frame built all of them at once, a 1.0 s frame with the flight's start lost in it
  // (measured 2026-10-20); built ahead but not yet warm, the frames waited for it while the flight ran on unseen.
  function whenWarm(first) {
    uvShown = true;   // (what is built ahead stops here, and its pieces wait for no hand)
    if (!(uv.warm && !uv.warmed)) return finishShow(first);
    // meanwhile its loading screen, on the stage (and over the page, opened on the map), its number the work done
    uvLoad(true, 20);
    uv.warm(null, function (f) { var p = 20 + f * 76; uvLoad(true, p); bootSet(p, 'UNIVERSE'); }).then(function () { finishShow(first); });
  }
  // The Universe built ahead (2026-10-19, "load things in the background"): once the office has drawn and the page
  // has been left alone for a moment, the map is built a step at a time in the browser's idle time -- its renderer,
  // its stations, then everything its first frame would compile (warm()) -- so its tab opens at once. Measured before:
  // the first open held the page 616 ms (309 ms building, then a first frame of 65 shaders and 67 pipelines), 2.9 s
  // on a computer a quarter as fast. A hand on the page comes first: a step waits until it has been still 1.2 s.
  var lastHand = 0, uvLay = null;
  ['pointerdown', 'wheel', 'keydown', 'touchstart'].forEach(function (k) { document.addEventListener(k, function () { lastHand = performance.now(); }, { capture: true, passive: true }); });
  document.addEventListener('pointermove', function (e) { if (e.buttons) lastHand = performance.now(); }, { capture: true, passive: true });   // a drag held on
  function prebuildUniverse() {
    if (RO || uv || !(CO.U3 && CO.U3.ok)) return;
    // the renderer and its world; the plan; a station a step (uvLay, which show3D finishes if the tab opens first);
    // then its shaders and pipelines (warm(), a piece at a time of its own)
    var steps = [
      function () { if (uv) return false; uv = CO.U3.universe($('uv3d'), $('uvstage'), uvHooks()); $('uvstage').classList.add('is3d'); CO.uv = uv; },
      function () { if (!uv || uvLaid || !uv.layoutSteps) return false; uvLay = uv.layoutSteps(); },
      function () { if (!uvLay) return false; uvLay.shift()(); if (uvLay.length) return true; uvLay = null; uvLaid = true; },
      // its pieces wait while a hand is on the page (a drag of the office ran 80 fps instead of 95 beside them), and
      // not at all once its tab is open: then it is what the tab waits for
      function () { if (uv && uv.warm && uvLaid) uv.warm(handsOff); }
    ], i = 0;
    function handsOff() {
      return new Promise(function (res) { (function w() { if (uvShown || performance.now() - lastHand >= 1200) res(); else setTimeout(w, 150); })(); });
    }
    // (a computer the office keeps busy has no idle moment at all: there a step runs after 300 ms anyway, and the
    // stations go on for 12 ms at a time -- at a quarter of the CPU they had waited 5 s each, the tab opened first)
    var idle = window.requestIdleCallback ? function (f) { window.requestIdleCallback(f, { timeout: 300 }); } : function (f) { setTimeout(f, 300); };
    (function next() {
      if (i >= steps.length || uvShown) return;   // its tab opened first: show3D did the rest
      idle(function (dl) {
        if (uvShown) return;
        if (performance.now() - lastHand < 1200) return setTimeout(next, 700);
        // a step returning true has more to do: it runs again while this idle moment lasts, then at the next
        var again, t0 = performance.now();
        do { again = steps[i]() === true; } while (again && (dl && dl.didTimeout ? performance.now() - t0 < 12 : dl && dl.timeRemaining && dl.timeRemaining() > 8));
        if (!again) i++;
        setTimeout(next, again ? 0 : 120);
      });
    })();
  }
  // after the office's first frames (the 3D office's, or the flat one's when 3D is off), not before: the office first
  function afterOffice(cb) {
    var t0 = performance.now();
    (function wait() { if ((!office3d && ui.view !== '3d') || (office3d && office3d.frames > 40) || performance.now() - t0 > 20000) return cb(); setTimeout(wait, 250); })();
  }
  function finishShow(first) {
    uvShown = true;
    requestAnimationFrame(function () {
      uv.resize();
      if (!uv.fitted) uv.fit(false);
      uv.setMine(mineForMap());
      if (first) {
        // back from a visit: start at the company just left, then pull back to the whole map
        var from = null; try { from = sessionStorage.getItem('uv.from'); sessionStorage.removeItem('uv.from'); } catch (e) { /* fine */ }
        if (from) { uv.flyTo(+from, null, 0); setTimeout(function () { uv.fit(true); }, 350); }
      }
      // the loading screens go once the map has drawn
      afterFrame(uv, function () { uvLoad(false); if (ui.tab === 'universe') bootDone(); });
    });
  }
  function renderUniverse() { if (uv) uv.setMine(mineForMap()); }
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
          '<div class="pfown" style="--acc:' + CO.accentHex(CO.profile().accent) + '"><span class="mkb sm"><span class="mkt">MADE BY</span><span class="mkr">' + esc(CO.S.company.name) + '</span></span></div>' +
          '<div class="pfn"><div><b>' + v.toLocaleString('en-US') + '</b><span>visitors</span></div><div><b>' + (a.uses + a.todayUses).toLocaleString('en-US') + '</b><span>uses</span></div>' +
          '<div><b>' + a.views.toLocaleString('en-US') + '</b><span>views</span></div><div><b>' + a.likes + '</b><span>likes</span></div></div>' +
          '<span class="pfbar"><i style="width:' + pct + '%"></i></span>' +
          '<div class="pfe"><span class="g">+' + CO.fmtEt(e.et10) + ' ET10</span><span class="u">+' + CO.fmtUsd(e.usdc) + ' USDC</span><em>proposed</em>' +
          (a.todayVisitors ? '<i>+' + a.todayVisitors + ' now</i>' : '') + '</div></div>';
      }).join('') + '</div>' +
      '<p class="pfsrc">Visitors, uses, views, likes: Cymetica (' + esc(Rd.src) + '), last ' + Rd.days + ' days, read ' + Rd.at + '. Earnings: proposed, placeholder rates.</p>');
  }
  function uvStats(s) {
    setHTML($('uv-sum'), '<b>' + s.companies + '</b> companies · <b>' + s.free + '</b> free slots · <b class="gr">' + s.owned + '</b> yours' + (s.ads ? ' · <b class="cy">' + s.ads + '</b> products' : ''));
  }
  // Buy land: a mode the stage is in. On, the free slots show on the map and a click on one buys it; Esc or the button
  // again turns it off.
  var buying = false;
  function setBuying(on) {
    buying = !!on;
    $('uvstage').classList.toggle('buying', buying);
    $('uv-buy').classList.toggle('on', buying);
    $('uv-buy').textContent = buying ? '× Done' : '+ Buy land';
    $('uv-price').textContent = CO.LAND_PRICE.toLocaleString('en-US');    if (uv && uv.setBuying) uv.setBuying(buying);
  }
  // a slot: for sale, its price and a Buy; yours, the way to build on it (Build it Better)
  function slotCard(it) {
    var where = CO.uvSlotName(it), price = CO.LAND_PRICE.toLocaleString('en-US');
    if (it.owned) {
      return openModal('<div class="mh"><h3>Your land</h3><span class="sp"></span><button class="btn" data-a="close">×</button></div>' +
        '<div class="kpis two"><div><b class="gr">' + esc(where) + '</b><span>bought with ET10</span></div><div><b>Empty</b><span>no building yet</span></div></div>' +
        '<p class="hint">A building goes up here through Build it Better: describe it, and it stands on this slot once it ships.</p>' +
        '<div class="mf"><span class="sp"></span><button class="btn" data-a="close">Close</button><button class="btn gr" data-a="build">Add a building with Build it Better ↗</button></div>', false, function (a) {
        if (a === 'build') { window.open(CO.BUILD_URL, '_blank', 'noopener'); closeModal(); }
      });
    }
    // three slots to an account for now: with all three held, the card says so and offers nothing to buy
    if (!CO.landLeft()) {
      return openModal('<div class="mh"><h3>Land limit reached</h3><span class="sp"></span><button class="btn" data-a="close">×</button></div>' +
        '<div class="kpis two"><div><b class="gr">' + CO.land().length + ' / ' + CO.LAND_MAX + '</b><span>slots you hold</span></div><div><b>' + esc(where) + '</b><span>this one stays free</span></div></div>' +
        '<p class="hint">An account can hold ' + CO.LAND_MAX + ' slots for now, so nobody buys the whole map up.</p>' +
        '<div class="mf"><span class="sp"></span><button class="btn" data-a="close">Close</button></div>', false);
    }
    openModal('<div class="mh"><h3>Buy this slot</h3><span class="sp"></span><button class="btn" data-a="close">×</button></div>' +
      '<div class="kpis two"><div><b class="gr">' + price + '</b><span>ET10 · placeholder price</span></div><div><b>' + esc(where) + '</b><span>orbit 1 is nearest Cymetica</span></div></div>' +
      '<p class="hint">Yours once bought: then add a building here with Build it Better. You can hold ' + CO.LAND_MAX + ' slots for now; ' + CO.landLeft() + ' left.</p>' +
      '<div class="mf"><span class="sp"></span><button class="btn" data-a="close">Cancel</button><button class="btn gr" data-a="buy">Buy for ' + price + ' ET10</button></div>', false, function (a) {
      if (a !== 'buy') return;
      CO.buyLand(it.c.id); closeModal();
      if (uv && uv.refreshLand) uv.refreshLand();
      toast('Bought ' + where + '. Add a building with Build it Better. ' + CO.landLeft() + ' of ' + CO.LAND_MAX + ' slots left.');
    });
  }
  // The panel stands over the stage's right side, so the product is flown to the middle of what is left (a stage too
  // narrow for both lets the panel take the lower part of it instead, and the product stays in the middle)
  function openAd(it) {
    var st = $('uvstage'), W = st.clientWidth, pw = Math.min(420, W - 24), side = W > 760;
    if (!CO.uvPanel || !CO.uvPanel.el) { window.open(it.ad.url, '_blank', 'noopener'); return; }
    if (buying) setBuying(false);
    CO.uvPanel.show(it);
    uv.flyTo(it.c.id, null, 1100, side ? (pw + 12) / 2 : 0);
  }
  function closeAd() {
    if (!CO.uvPanel || !CO.uvPanel.isOpen()) return false;
    CO.uvPanel.hide();
    if (uv) uv.fit(true);
    return true;
  }
  function openFromMap(it) {
    var c = it.c;
    // an ad: the map flies to it and its panel slides in (Visit / Go play opens the live page); a slot its card (one for sale only while Buy land is on)
    if (it.kind === 'ad') return openAd(it);
    if (it.kind === 'slot') { if (it.owned || buying) slotCard(it); return; }
    if (it.mine) return setTab('office');
    // another company: as it always was (the operator, 2026-10-22: no change, no side panel for companies): a private one
    // shows its card, a public one the flight into its visit
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
  // each station's 3D picture in its colour ships as a file (shots/station-<skin>-<accent>.webp, drawn by
  // CO.U3.thumbs): shown at once, where the flat drawing showed first ("tam prvne najedou ty hnusne ikony")
  function skinButtons(sel, acc) {
    return CO.SKINS.map(function (s) {
      var file = 'shots/station-' + s.key + '-' + (acc || 'green') + '.webp';
      return '<button type="button" class="skin has3d' + (s.key === sel ? ' on' : '') + '" data-a="uv-skin" data-k="' + s.key + '"><img class="th3" alt="" src="' + file + '">' +
        CO.skinSVG({ skin: s.key, accent: acc, floors: 3, seed: 11 }) + '<b>' + s.name + '</b></button>';
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
    setHTML($('appr-full'), S.approvals.length ? S.approvals.map(function (a) { return apprCard(a, false); }).join('') : '<p class="empty ok">No approvals.</p>');
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

  // Connect AI: the whole company from the owner's own AI, through Cymetica's MCP server and API -- one ready prompt for
  // any AI, the connector, the key (the operator, 2026-10-20: "talk to NEXUS and run the whole company from your
  // favourite AI"; "staci tam jeden prompt"). A sketch: the tab is Cymetica's to design (SPEC section 13).
  var MCP_URL = 'https://cymetica.com/mcp/v1';
  function connectPrompt() {
    var S = CO.S;
    return 'You run my company "' + S.company.name + '" on Cymetica for me. Connect to Cymetica\'s MCP server (' + MCP_URL + ') with my API key. ' +
      'Read my company first. From then on, pass what I ask about the company to NEXUS, its AI, and show me its answers; ' +
      'tell me what waits for my approval and approve or reject only when I say so. Keep answers short, numbers first.';
  }
  function renderConnect() {
    var el = $('connect'); if (!el) return;
    if (el._done) return;
    el._done = true;
    var steps = [['1', 'Your API key', '<span class="ckey">evt_••••••••••••3f9a</span><button type="button" class="btn cy" data-cc="key">Copy</button>'],
      ['2', 'Add the connector', '<span class="ckey">' + MCP_URL + '</span><button type="button" class="btn cy" data-cc="mcp">Copy</button>'],
      ['3', 'Paste the prompt', '<span class="chint">into ChatGPT, Claude, Gemini or any AI that speaks MCP</span>']];
    el.innerHTML = '<div class="cnhero"><h2>Talk to NEXUS.<br><em>Run your whole company from your favourite AI.</em></h2>' +
      '<p>Departments, processes, approvals, experiments, the Vault: everything you do here works from your AI.</p></div>' +
      '<div class="cnsteps">' + steps.map(function (s) { return '<div class="cnstep"><b>' + s[0] + '</b><span>' + s[1] + '</span><div>' + s[2] + '</div></div>'; }).join('') + '</div>' +
      '<div class="cnone"><div class="cnh"><b>The prompt</b><span class="cnais1">ChatGPT · Claude · Gemini · any AI</span></div>' +
      '<pre>' + esc(connectPrompt()) + '</pre><button type="button" class="cngo" data-cc="prompt">Copy prompt</button></div>';
    el.onclick = function (e) {
      var b = e.target.closest('[data-cc]'); if (!b) return;
      var w = b.getAttribute('data-cc'), txt = w === 'mcp' ? MCP_URL : w === 'key' ? 'evt_your_api_key' : connectPrompt();
      try { navigator.clipboard.writeText(txt); } catch (err) { /* the mock goes on */ }
      var was = b.textContent; b.textContent = 'Copied'; b.classList.add('done'); setTimeout(function () { b.textContent = was; b.classList.remove('done'); }, 1400);
    };
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
    else heart = '';   // nothing while it runs ("odstran ten maly napis waiting"): the rail and the rooms say who works
    $('co-heart').innerHTML = heart;
    var ur = $('us-r');
    // The plan windows run out and work goes on, paid from the owner's own USDC (the live /mine says so: at_zero,
    // extra.month_spend_usdc of monthly_cap_usdc, turns_left). The bar says it in numbers: a red bar with no word about
    // it read as work running for free past the limit ("nechapu jak to funguje", 2026-10-21; their build shows "Resets in" only).
    ur.textContent = g.code === 'extra' ? 'on extra usage · ' + CO.fmtUsd(b.extra.month_cap - b.extra.left) + ' of ' + CO.fmtUsd(b.extra.month_cap) + ' USDC this month · resets in ' + hm(b.session.resets_at - S.clock) : 'Resets in ' + hm(b.session.resets_at - S.clock);
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
      if (rk === 'hub') return '<b>Command</b> · routes ' + c.open + ' open<br>' + (S.company.status === 'paused' ? 'paused' : RO ? 'plans the next pass · click to read its chat' : 'plans the next pass · click to message it');
      if (rk === 'you') return '<b>You</b> · ' + (S.approvals.length ? '<span class="r">' + S.approvals.length + ' to approve</span>' : 'nothing waits for you');
      if (rk === 'audit') return '<b>Supervisor</b> · runs the weekly audit';
      var d = CO.dept(+rk.slice(1)); if (!d) return '';
      var v = CO.deptView(d), e = v.experts[i]; if (!e) return '';
      return '<b>' + esc(e.name) + '</b> · ' + esc(d.name) + '<br>' + (e.state === 'working' && v.running ? '<span class="c">working on</span> “' + esc(v.running.title) + '”' : 'idle');
    }
    if (key === 'hub') return '<b>Command</b> · ' + (RO ? 'its chat' : 'your chat') + (S.approvals.length ? ' · <span class="r">' + S.approvals.length + (RO ? ' wait for its owner' : ' approval' + (S.approvals.length === 1 ? '' : 's')) + '</span>' : '') + '<br>click to open';
    if (key === 'you') return '<b>Your desk</b> · ' + (S.approvals.length ? '<span class="r">' + S.approvals.length + ' approvals waiting</span>' : 'all clear') + '<br>click to open Approvals';
    if (key === 'audit') {
      var A = S.audit;
      return '<b>Operations</b> · next in ' + Math.max(0, Math.ceil((A.next_at - S.clock) / 86400000)) + 'd · ' + (A.last ? A.last.findings.length : 0) + ' findings last week<br>click to look inside';
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
  // wide: true for the wide card, or a class of its own ('x3', the 3D Add a department)
  function openModal(html, wide, act) {
    var card = $('modal-card');
    drop3d();
    card.className = 'modal-card' + (wide === true ? ' wide' : wide ? ' ' + wide : '');
    card.innerHTML = html; modalAct = act || null;
    $('modal').hidden = false;
    var f = card.querySelector('input,textarea'); if (f) setTimeout(function () { f.focus(); }, 30);
  }
  function closeModal() { $('modal').hidden = true; modalAct = null; drop3d(); dlgMode = ''; }
  // the 3D dialog's live room: one renderer for the page, out of the dialog whenever it goes, however it goes
  var dlg3 = null;
  function drop3d() { if (dlg3) { if (dlg3.detach) dlg3.detach(); else dlg3.dispose(); dlg3 = null; warmRooms(); } holdOffice(false); }
  // That renderer made ready while the office is shown, a few seconds after its first frame and only while the page
  // is left alone (RoomPreview.warmUp): the room Add department opens on, every room a click brings, and every
  // department's own as Edit shows it. Opened before, the dialog makes them as it opens, as it always did.
  // The stage's size is a guess from the dialog's layout (style.css .modal-card.x3, .d3main, .d3bot); the dialog
  // corrects it as it opens, and only the time that takes depends on it.
  function warmDialog() {
    if (RO || ui.view !== '3d' || !office3d || !(CO.U3 && CO.U3.dialogPreview)) return;
    setTimeout(function () {
      var ric = window.requestIdleCallback || function (f) { return setTimeout(f, 50); };
      ric(warmRooms, { timeout: 4000 });
    }, 2500);
  }
  // (and again as the dialog goes: a department added or changed meanwhile has a room of its own to make)
  function warmRooms() {
    if (RO || ui.view !== '3d' || !office3d || !(CO.U3 && CO.U3.dialogPreview)) return;
    var L = looks(), own = CO.TEMPLATES.filter(function (t) { return t.key === 'custom'; })[0] || { key: 'custom', name: '', experts: ['researcher'] };
    var free = CO.TEMPLATES.filter(function (t) { return t.key !== 'custom' && !CO.S.departments.some(function (d) { return d.key === t.key; }); })[0];
    var first = free ? { key: free.key, experts: free.experts, look: null, name: free.name } : { key: 'custom', experts: own.experts, look: L[0].key, name: '' };
    var list = CO.TEMPLATES.map(function (t) { return { key: t.key, experts: t.experts, look: t.key === 'custom' ? L[0].key : null }; })
      .concat(CO.S.departments.map(function (d) { return { key: d.key, experts: d.experts, look: d.key === 'custom' ? d.look || L[0].key : null }; }))
      .concat(L.map(function (l) { return { key: 'custom', experts: own.experts, look: l.key }; }));
    var W = Math.min(1760, innerWidth * 0.96), H = Math.min(980, innerHeight * 0.94);
    CO.U3.dialogPreview().warmUp({ w: Math.round(W) - 382, h: Math.round(H) - 308 }, first, list);
  }
  // The 3D office stops drawing while the 3D dialog covers it (its last frame stays on its canvas): its own frames of
  // 130-140 ms every few seconds (measured 2026-10-19) were the dialog's last stalls once its rooms were kept.
  function holdOffice(on) {
    var o = office3d; if (!o || !o.renderer) return;
    if (on && o.frames && !o.held) { o.held = true; o.renderer.setAnimationLoop(null); }
    else if (!on && o.held) { o.held = false; o.renderer.setAnimationLoop(function () { o.frame(); }); }
  }
  var toastT = 0;
  function toast(text) {
    var t = $('toast'); t.textContent = text; t.hidden = false;
    clearTimeout(toastT); toastT = setTimeout(function () { t.hidden = true; }, 2600);
  }
  function readModal(id) {
    // ids come off the page as text and may be numbers in the data: compared as text, as decide() does (their live build
    // compared with === and Read did nothing, 2026-10-22)
    var a = CO.S.approvals.filter(function (x) { return String(x.id) === String(id); })[0]; if (!a) return;
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
    return keys.length ? keys.map(function (k) { return '<span class="hx" data-ex="' + k + '"><i>' + miniArt(k) + '</i>' + esc(CO.expertName(k)) + '</span>'; }).join('') : '<span class="hint">nobody yet: hire at least one</span>';
  }
  // An expert's chip: in the Add-a-department dialog its astronaut -- the 3D one once its picture is drawn, in the 3D
  // dialog, the flat office's in the 2D one; in the edit form the flat figure. dlgMode says which dialog is open.
  var dlgMode = '';
  // the cards' 3D pictures, drawn once by the dialog's own renderer and kept as files (shots/): shown at once, where
  // the renderer drew 18 of them as the dialog opened and the flat figures stood in meanwhile
  var SHOT_FILES = { astro: ['qa_tester', 'researcher', 'trader', 'developer', 'lab_scientist', 'auditor', 'designer'],
    room: ['development', 'design', 'testing', 'testing_lab', 'trading_desk', 'custom-office', 'custom-ops', 'custom-library', 'custom-workshop', 'custom-command', 'custom-greenhouse'] };
  function shotFile(kind, k, look) {
    var n = kind === 'astro' ? k : k + (look ? '-' + look : '');
    return SHOT_FILES[kind].indexOf(n) >= 0 ? 'shots/' + kind + '-' + n + '.webp' : null;
  }
  CO.shotFile = shotFile;
  function miniArt(k) {
    var u = dlgMode === '3d' && (shotFile('astro', k) || (CO.U3 && CO.U3.shotOf && CO.U3.shotOf('astro:' + k)));
    if (u) return '<img alt="" src="' + u + '">';
    if (dlgMode && CO.iso && CO.iso.astroArt) return CO.iso.astroArt(k, true);
    return CO.expertArt(k, true);
  }
  // the looks a department of your own can have, picked with the arrows round its room
  function looks() { return CO.ROOM_LOOKS && CO.ROOM_LOOKS.length ? CO.ROOM_LOOKS : [{ key: 'office', name: 'Office' }]; }
  function lookIdx(k) { var L = looks(); for (var i = 0; i < L.length; i++) if (L[i].key === k) return i; return 0; }
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
  // Add a department, one layout in either view (the operator, translated: "depending on which view you are in, 3D or
  // 2D, that's the Add-department layout that shows"): the department's own room in the middle -- in the 3D office
  // built by the office's builders, turning slowly; in the flat office drawn by the flat office's own drawing,
  // floating -- with its experts in it; on the left what it is, or the expert last clicked ("kdyz v add department
  // kliknu na experta nejakeho tak taky se ma zobrazit nekde popis jeho o cem je"); the departments and the experts in
  // two sliders under it, their pictures those rooms and astronauts. Where 3D cannot start, the flat one.
  function addDeptModal(editId) {
    var L = looks(), own = CO.TEMPLATES.filter(function (t) { return t.key === 'custom'; })[0] || { key: 'custom', name: '', experts: ['researcher'], charter: '' };
    var o = { key: 'custom', name: '', experts: own.experts.slice(), charter: '' };
    var free = CO.TEMPLATES.filter(function (t) { return t.key !== 'custom' && !CO.S.departments.some(function (d) { return d.key === t.key; }); })[0];
    if (free) o = { key: free.key, name: free.name, experts: free.experts.slice(), charter: free.charter };
    o.look = L[0].key;
    // Edit is this dialog on a department that exists: its own room, kind and look, no picker of kinds
    var ed = editId != null ? CO.dept(editId) : null;
    if (ed) o = { key: ed.key, name: ed.name, experts: ed.experts.slice(), charter: ed.charter, look: ed.look || L[0].key };
    var mode = !RO && ui.view === '3d' && !!office3d && !!(CO.U3 && CO.U3.roomPreview) ? '3d' : '2d', viewing = null, nameRaf = 0;
    function tplOf(k) { return CO.TEMPLATES.filter(function (t) { return t.key === k; })[0] || null; }
    function draw(m) {
      mode = dlgMode = m; viewing = null;
      openModal(form(), 'x3', act);
      if (m === '3d') {
        holdOffice(true);
        var mine = dlg3 = CO.U3.dialogPreview ? CO.U3.dialogPreview().attach($('d3-stage')) : CO.U3.roomPreview($('d3-stage'));
        // its renderer would not start: the same dialog, flat, with what was already chosen
        mine.onFail = function () {
          if (dlg3 !== mine) return;
          dlg3 = null; o.name = $('df-name').value; o.charter = $('df-ch').value; o.experts = hiredKeys(); draw('2d');
        };
        sync(); shots();
        // what a click can bring next, built while nothing happens: every department as its card staffs it, then
        // every look of your own (editing, only the looks of its own room, if it is one of your own)
        if (ed) mine.ahead(o.key === 'custom' ? L.map(function (l) { return { key: 'custom', experts: o.experts, look: l.key }; }) : []);
        else mine.ahead(CO.TEMPLATES.map(function (t) { return { key: t.key, experts: t.experts, look: t.key === 'custom' ? L[0].key : null }; })
          .concat(L.map(function (l) { return { key: 'custom', experts: own.experts, look: l.key }; })));
      } else {
        $('d3-stage').style.setProperty('--stars', CO.iso.stars());
        sync();
      }
    }
    function form() {
      var two = mode === '2d';
      return '<div class="ad3' + (two ? ' two' : '') + (ed ? ' edit' : '') + '"><div class="d3h"><h3>' + (ed ? 'Edit department' : 'Add a department') + '</h3><button class="btn" data-a="close">×</button></div>' +
        '<div class="d3main"><aside class="d3side"><div class="d3pane d3dept">' +
          '<div class="d3kick"><span id="d3-ic"></span><div class="d3k">DEPARTMENT <span id="d3-ti"></span></div></div>' +
          '<input id="df-name" class="d3name" maxlength="60" autocomplete="off" value="' + esc(o.name) + '" placeholder="Name it, e.g. Growth">' +
          '<ul class="d3about" id="d3-about"></ul>' +
          '<div class="d3k">WHO WORKS THERE <span>click one to read it</span></div><div class="hiredline" id="df-hired">' + hiredLine(o.experts) + '</div>' +
          '<div class="d3ch"><button type="button" class="d3cht" data-a="charter"><span class="d3k">CHARTER</span><span class="d3n" id="df-n">' + o.charter.length + ' / 2,000</span></button>' +
          '<textarea id="df-ch" maxlength="2000" placeholder="Your rules, notes and lessons">' + esc(o.charter) + '</textarea></div>' +
          '<div class="d3act"><span class="hint">' + (ed ? 'Its next task starts from this charter.' : 'Its first task starts from this charter.') + '</span><span class="d3btns">' +
            (ed ? '<button class="btn rd" data-a="remove">Delete</button>' : '') + '<button class="btn" data-a="close">Cancel</button><button class="btn gr" data-a="create">' + (ed ? 'Save' : 'Create department') + '</button></span></div>' +
        '</div><div class="d3pane d3ex" id="d3-ex"></div></aside>' +
        '<div class="d3stage' + (two ? ' d2stage' : '') + '" id="d3-stage">' + (two ? '<div class="d2room" id="d2-room"></div>' : '') +
          '<button type="button" class="d3arw l" data-a="look-prev" title="Previous look">‹</button><button type="button" class="d3arw r" data-a="look-next" title="Next look">›</button>' +
          '<div class="d3look" id="d3-look"></div>' + (two ? '' : '<div class="d3tip">drag to turn</div>') +
        '</div></div><div class="d3bot">' +
          (ed ? '' : '<div class="d3col"><div class="sec step">PICK A DEPARTMENT</div>' + slider('tpl-track', CO.TEMPLATES.map(tcard).join('')) + '</div>') +
          '<div class="d3col"><div class="sec step">HIRE ITS EXPERTS <span id="ex-n">' + o.experts.length + ' hired</span></div>' +
            slider('ex-track', CO.EXPERTS.map(function (e) { return xcard(e, o.experts.indexOf(e.key) >= 0); }).join('')) + '</div>' +
        '</div></div>';
    }
    // a department's room as its card shows it: the flat office's drawing in 2D; in 3D the picture kept from an earlier
    // opening, or the flat art until the 3D one is drawn
    function cardArt(t, look) {
      if (mode === '2d') return CO.iso.roomArt({ key: t.key, experts: t.experts, look: look, name: t.name }, { still: true });
      var u = shotFile('room', t.key, look) || CO.U3.shotOf('room:' + t.key + ':' + (look || ''));
      return u ? '<img alt="" src="' + u + '">' : CO.deptArt(t.key);
    }
    function tcard(t) {
      var used = t.key !== 'custom' && CO.S.departments.some(function (d) { return d.key === t.key; });
      var n = t.experts.length, sub = t.key === 'custom' ? L.length + ' looks' : n + (n === 1 ? ' expert' : ' experts'), look = t.key === 'custom' ? o.look : null;
      return '<button type="button" class="tcard' + (t.key === o.key ? ' on' : '') + '" data-tpl="' + t.key + '"><div class="art">' + cardArt(t, look) + '</div>' +
        '<b>' + CO.deptIcon({ key: t.key, look: look }) + esc(t.name || 'Custom') + '</b><span>' + esc(CO.DEPT_INFO[t.key] || '') + '</span>' +
        '<em class="tst">' + sub + (used ? '<i>you have one</i>' : '') + '</em></button>';
    }
    // an expert's card: its astronaut, its name, what it does in Cymetica's own words; the chip hires and fires, the
    // rest of the card opens it on the left
    function figOf(k, still) {
      if (mode === '2d') return CO.iso.astroArt(k, still);
      var u = shotFile('astro', k) || CO.U3.shotOf('astro:' + k);
      return u ? '<img alt="" src="' + u + '">' : CO.expertArt(k);
    }
    function xcard(e, on) {
      return '<button type="button" class="xcard' + (on ? ' on' : '') + '" data-ex="' + e.key + '"><div class="fig">' + figOf(e.key, true) + '</div>' +
        '<b>' + esc(e.name) + '</b><span>' + esc(e.description || '') + '</span><i class="ck">' + (on ? '✓ hired' : '+ hire') + '</i></button>';
    }
    // the room follows what is picked, hired and (for your own) which look; the panel says what it is
    function sync() {
      var custom = o.key === 'custom', i = lookIdx(o.look), ti = 0;
      CO.TEMPLATES.forEach(function (t, k) { if (t.key === o.key) ti = k; });
      if (dlg3) dlg3.set({ key: o.key, experts: hiredKeys(), look: custom ? o.look : null, name: $('df-name').value });
      else room2();
      var lk = $('d3-look'); lk.hidden = !custom; lk.innerHTML = '<b>' + (i + 1) + ' / ' + L.length + '</b>' + esc(L[i].name);
      Array.prototype.forEach.call(document.querySelectorAll('#d3-stage .d3arw'), function (b) { b.hidden = !custom; });
      $('d3-about').innerHTML = (CO.DEPT_ABOUT[o.key] || CO.DEPT_ABOUT.custom).map(function (s) { return '<li>' + esc(s) + '</li>'; }).join('');
      $('d3-ti').textContent = (ti + 1) + ' / ' + CO.TEMPLATES.length;
      $('d3-ic').innerHTML = CO.deptIcon({ key: o.key, look: custom ? o.look : null });
    }
    // the flat room, redrawn whole (a few milliseconds); it rises out of its deck when it is another room
    function room2() {
      var box = $('d2-room'); if (!box) return;
      var look = o.key === 'custom' ? o.look : null, ex = hiredKeys(), key = [o.key, ex.join(','), look || ''].join('|');
      box.innerHTML = CO.iso.roomArt({ key: o.key, experts: ex, look: look, name: $('df-name').value });
      if (box._k !== key) { box._k = key; box.classList.remove('rise'); void box.offsetWidth; box.classList.add('rise'); }
    }
    // the cards' 3D pictures, each drawn once and kept: they replace the flat ones as they come, the astronauts first
    // (quick to draw, and the chips of who works there wait for them)
    function shots() {
      if (!dlg3) return;
      Array.prototype.forEach.call(document.querySelectorAll('#ex-track .xcard'), function (c) {
        var k = c.getAttribute('data-ex');
        if (shotFile('astro', k)) return;
        dlg3.shot('astro', k, function (u) {
          put(c.querySelector('.fig'), u);
          var h = $('df-hired'); if (u && dlg3 && h) h.innerHTML = hiredLine(hiredKeys());
          if (u && viewing === k) showExpert(k);
        });
      });
      CO.TEMPLATES.forEach(function (t) {
        if (t.key === 'custom') return customShot();
        if (shotFile('room', t.key)) return;
        var c = document.querySelector('#tpl-track .tcard[data-tpl="' + t.key + '"]');
        dlg3.shot('room', { key: t.key, experts: t.experts }, function (u) { if (c) put(c.querySelector('.art'), u); });
      });
    }
    // the card of your own shows the look picked
    function customShot() {
      var c = document.querySelector('#tpl-track .tcard[data-tpl="custom"]'), lk = o.look; if (!c) return;
      var ic = c.querySelector('b .dic'); if (ic) ic.outerHTML = CO.deptIcon({ key: 'custom', look: lk });
      if (mode === '2d' || shotFile('room', 'custom', lk)) { c.querySelector('.art').innerHTML = cardArt(own, lk); return; }
      if (dlg3) dlg3.shot('room', { key: 'custom', experts: own.experts, look: lk }, function (u) { if (o.look === lk) put(c.querySelector('.art'), u); });
    }
    function put(box, u) { if (u && box && document.body.contains(box)) box.innerHTML = '<img alt="" src="' + u + '">'; }
    // An expert in the panel's place: what it does and the departments it fits, word for word as Cymetica has them
    // (CO.EXPERTS), whether it reads the web, the rule every expert keeps, and hire or fire it. Back returns to the
    // department.
    function showExpert(k) {
      var e = CO.expert(k), pane = $('d3-ex'); if (!e || !pane) return;
      viewing = k;
      var on = hiredKeys().indexOf(k) >= 0, i = CO.EXPERTS.indexOf(e), web = (e.tools || []).length > 0, dn = $('df-name').value.trim() || (tplOf(o.key) || {}).name || 'your department';
      var big = mode === '3d' && !shotFile('astro', k) && !CO.U3.shotOf('astro:' + k) ? CO.expertArt(k) : figOf(k, false);
      var fits = (e.fits || []).map(function (f) { var t = tplOf(f); return '<span class="d3fit' + (f === o.key ? ' here' : '') + '">' + CO.deptIcon({ key: f }) + esc(t ? t.name : f) + '</span>'; }).join('');
      pane.innerHTML = '<button type="button" class="d3back" data-a="xback">‹ <b>' + esc(dn) + '</b></button>' +
        '<div class="d3xhead"><div class="d3xfig">' + big + '</div><div><div class="d3k">EXPERT <span>' + (i + 1) + ' / ' + CO.EXPERTS.length + '</span></div>' +
        '<h4 class="d3xn">' + esc(e.name) + '</h4><div class="d3xt ' + (on ? 'on' : '') + '">' + (on ? '✓ hired here' : 'not hired') + '</div></div></div>' +
        '<div class="d3xbody"><p class="d3xd">' + esc(e.description) + '</p>' +
        '<div class="d3k">FITS <span>' + e.fits.length + (e.fits.length === 1 ? ' department' : ' departments') + '</span></div><div class="d3fits">' + fits + '</div>' +
        '<div class="d3xw ' + (web ? 'ok' : 'no') + '"><i>' + (web ? '✓' : '×') + '</i><span>' + esc(e.capabilities[0]) + '</span></div>' +
        '<div class="d3xa">' + CO.ruleIcon('real') + '<span>' + esc(e.capabilities[1]) + '</span></div></div>' +
        '<div class="d3act"><button type="button" class="btn ' + (on ? 'd3fire' : 'gr') + '" data-a="xhire">' + (on ? 'Fire from ' + esc(dn) : '+ Hire into ' + esc(dn)) + '</button></div>';
      document.querySelector('#modal-card .d3side').classList.add('ex');
      Array.prototype.forEach.call(document.querySelectorAll('#ex-track .xcard'), function (c) { c.classList.toggle('view', c.getAttribute('data-ex') === k); });
    }
    function hideExpert() {
      viewing = null;
      var side = document.querySelector('#modal-card .d3side'); if (side) side.classList.remove('ex');
      Array.prototype.forEach.call(document.querySelectorAll('#ex-track .xcard.view'), function (c) { c.classList.remove('view'); });
    }
    function pick(el) {
      var t = tplOf(el.getAttribute('data-tpl')); if (!t) return;
      o = { key: t.key, name: t.name, experts: t.experts.slice(), charter: t.charter, look: o.look };
      Array.prototype.forEach.call(document.querySelectorAll('#tpl-track .tcard'), function (c) { c.classList.toggle('on', c === el); });
      Array.prototype.forEach.call(document.querySelectorAll('#ex-track .xcard'), function (c) { toggleExpert(c, o.experts.indexOf(c.getAttribute('data-ex')) >= 0); });
      $('df-name').value = t.name; $('df-ch').value = t.charter; $('df-n').textContent = t.charter.length + ' / 2,000';
      var ch = document.querySelector('#modal-card .d3ch'); if (ch && !t.charter) ch.classList.remove('shut');
      el.scrollIntoView({ behavior: 'smooth', inline: 'center', block: 'nearest' });
      if (!t.name) $('df-name').focus();
    }
    function act(a, el) {
      if (a === 'tpl') { pick(el); hideExpert(); sync(); }
      else if (a === 'hired') { sync(); if (el && el.getAttribute('data-ex')) showExpert(el.getAttribute('data-ex')); }
      else if (a === 'expert') showExpert(el.getAttribute('data-ex'));
      else if (a === 'xback') hideExpert();
      else if (a === 'xhire') {
        var c = document.querySelector('#ex-track .xcard[data-ex="' + viewing + '"]'); if (!c) return;
        toggleExpert(c, !c.classList.contains('on')); sync(); showExpert(viewing);
      } else if (a === 'name') {
        if (dlg3) dlg3.name(el.value);
        else if (mode === '2d') { cancelAnimationFrame(nameRaf); nameRaf = requestAnimationFrame(room2); }
      } else if (a === 'charter') el.parentNode.classList.toggle('shut');
      else if (a === 'look-prev' || a === 'look-next') {
        var i = lookIdx(o.look) + (a === 'look-next' ? 1 : -1);
        o.look = L[(i + L.length) % L.length].key; sync(); customShot();
      } else if (a === 'remove' && ed) deleteDeptModal(ed.id);
      else if (a === 'create') {
        var f = readDeptForm();
        if (!f.name) { hideExpert(); $('df-name').focus(); $('df-name').style.borderColor = 'var(--red)'; return; }
        if (!f.experts.length) { toast('Hire at least one expert.'); return; }
        var look = o.key === 'custom' ? o.look : null;
        closeModal();
        if (ed) {
          CO.act.editDept(ed.id, { name: f.name, experts: f.experts, charter: f.charter, look: look });
          ui.dirty = false; $('dr-ch-text').value = CO.dept(ed.id).charter; renderDrawer(); toast(f.name + ' saved.'); return;
        }
        var d = CO.act.addDept({ key: o.key, name: f.name, experts: f.experts, charter: f.charter, look: look });
        toast('New department: ' + d.name + '. Its room is being built.');
      }
    }
    draw(mode);
  }
  // Edit is the Add dialog on the department ("edit departmentu vypada stare")
  function editDeptModal(id) { if (CO.dept(id)) addDeptModal(id); }
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
  function sendMessage(text, deptId, images) {
    if (!text && !(images && images.length)) return;
    // /clear on its own is a command, not a message: it is not sent to NEXUS and costs no turn
    if (/^\/clear$/i.test(text) && !(images && images.length)) { CO.act.clear(); toast('Window cleared. The history is kept for the audit.'); return; }
    CO.act.message(text || 'Screenshot', deptId, images);
    office.packet('you', 'hub', 'blue');
  }
  // the pictures waiting to go with the next message: at most four, each a PNG or JPEG under 5 MB
  var pics = [];
  function addPic(f) {
    if (!f || !/^image\//.test(f.type)) return;
    if (pics.length >= 4) return toast('Four images at most in one message.');
    if (f.size > 5 * 1024 * 1024) return toast('That image is over 5 MB.');
    var r = new FileReader();
    r.onload = function () { pics.push({ name: f.name || 'screenshot.png', src: String(r.result) }); renderAttach(); };
    r.readAsDataURL(f);
  }
  function renderAttach() {
    var el = $('attach'); el.hidden = !pics.length;
    el.innerHTML = pics.map(function (p, i) { return '<span class="apic"><img alt="" src="' + p.src + '"><button type="button" data-x="' + i + '" title="Take it out">×</button></span>'; }).join('');
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
      if (t.closest('#sim-new')) { location.href = 'start.html'; return; }
      // the Universe's way in for someone without a company ("musis dat nekde zelene tlacitko pro create company")
      if (t.closest('#uv-new')) { location.href = 'builder.html'; return; }
      if (t.closest('#uv-panel [data-a="close"]')) return closeAd();
      if (t.closest('#uv-panel [data-a="owner"]')) { e.preventDefault(); closeAd(); return setTab('office'); }
      if (uv) {
        if (t.closest('#uv-in')) return uv.zoom(0.78);
        if (t.closest('#uv-out')) return uv.zoom(1.28);
        if (t.closest('#uv-fit')) return closeAd() || uv.fit(true);
        if (t.closest('#uv-buy')) return setBuying(!buying);
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
      if (t.closest('#ops-open')) { closeDrawer(); setTab('audit'); return; }
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
      // in the Add-a-department dialog an expert's card opens it on the left and its chip hires or fires it; in the
      // edit form the whole card hires or fires
      var xc = t.closest('#modal-card .xcard');
      if (xc) {
        if (xc.closest('.ad3') && !t.closest('.ck')) { if (modalAct) modalAct('expert', xc); return; }
        toggleExpert(xc, !xc.classList.contains('on')); if (modalAct) modalAct('hired', xc); return;
      }
      var hx = t.closest('#modal-card .ad3 .hx[data-ex]'); if (hx && modalAct) return modalAct('expert', hx);
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
    $('compose').addEventListener('submit', function (e) {
      e.preventDefault(); var i = $('msg'), text = i.value.trim();
      if (!text && !pics.length) return;
      sendMessage(text, null, pics.slice()); i.value = ''; pics.length = 0; renderAttach();
    });
    // Pictures in the chat with NEXUS ("chci at jde vkladat obrazky do chatu nexuse, ze jak nekde udelam print screen tak to
    // tam pujde vlozit", 2026-10-21): a screenshot pasted into the box (Ctrl+V) or an image picked with the clip is shown as a
    // small card above the box, with a cross to take it back, and goes with the message.
    $('msg').addEventListener('paste', function (e) {
      var items = (e.clipboardData && e.clipboardData.items) || [], got = false;
      Array.prototype.forEach.call(items, function (it) { if (it.kind === 'file' && /^image\//.test(it.type)) { got = true; addPic(it.getAsFile()); } });
      if (got) e.preventDefault();
    });
    $('msg-file').addEventListener('change', function (e) { Array.prototype.forEach.call(e.target.files || [], addPic); e.target.value = ''; });
    $('attach').addEventListener('click', function (e) { var x = e.target.closest('[data-x]'); if (x) { pics.splice(+x.getAttribute('data-x'), 1); renderAttach(); } });
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
      // the room's wall screen carries the name as it is typed (in 3D nothing is rebuilt for it)
      if (e.target.id === 'df-name' && modalAct) modalAct('name', e.target);
    });
    document.addEventListener('change', function (e) {
      if (e.target.classList.contains('rvw')) { var rid2 = e.target.closest('.rule').getAttribute('data-rule'); var rl2 = CO.S.rules.filter(function (x) { return x.id === rid2; })[0]; if (rl2) { CO.act.review(rid2, rl2.review, e.target.value.trim() || 'you'); toast(rid2 + ': reviewed by ' + (e.target.value.trim() || 'you') + '.'); } }
      if (e.target.id === 'tk-chain') CO.S.token.chain = e.target.value;
      if (e.target.id === 'lg-dom') { CO.S.legal.domicile = e.target.value; toast('Domicile: ' + e.target.value); }
    });
    document.addEventListener('keydown', function (e) {
      if (e.key !== 'Escape') return;
      if (!$('modal').hidden) return closeModal();
      if (buying) return setBuying(false);
      if (closeAd()) return;
      if (ui.panel != null || ui.mgr || ui.vault) closeDrawer();
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
    function reframe() { if (ui.mgr) office.focus('hub', 0, true); else if (ui.panel != null) office.focus('d' + ui.panel, 0, true); else if (ui.vault) office.focus(ui.vault, 0, true); else office.fit(true); }
    CO.on('dept:new', function (d) { office.layout({ born: d.id }); if (ui.panel != null || ui.mgr) office.select(ui.mgr ? 'hub' : 'd' + ui.panel); setTimeout(reframe, 60); });
    CO.on('dept:edit', function () { office.layout(); });
    CO.on('dept:removed', function () { office.layout(); setTimeout(reframe, 60); });
    CO.on('reset', function () {
      closeModal(); ui.panel = null; ui.vault = false; document.body.classList.remove('vopen'); $('drawer').hidden = true; office.sel = null; ui.open = {}; ui.prev = {};
      office.layout(); office.fit(true); markSeen();
      ['depts', 'appr', 'earn', 'msgs', 'legal', 'settings'].forEach(function (id) { $(id)._h = null; });
      if (uv) uv.setMine(mineForMap());
    });
    CO.on('office:click', function (key) {
      if (key.charAt(0) === 'd') return openDrawer(+key.slice(1));
      if (key === 'hub') return openManager();
      if (key === 'you') return setTab('approvals');
      if (key === 'audit') return openOpsRoom();
      if (key === 'vault') return openVaultRoom();
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
