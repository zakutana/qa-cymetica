/* The /company mockup: the office as the operator's picture (look-office.webp, 1528 x 810), the way the Universe
 * already is ("to vlevo 10/10", 2026-10-18). The picture is the room layout of our own company, so this view
 * stands only while the company has exactly the five departments the picture shows; anything else (a department
 * added or taken away, a visit to someone else's company) goes back to the live 3D or flat office.
 *
 * What is live on it: a plate over each painted label (state, next run, ET10), a glow on each room in the colour of
 * what it is doing (cyan working, red waiting -- the painted orange of the trading desk is taken out of the picture
 * while it does not wait, and turned red when it does), the "need you" badge, the vault card over the painted
 * corner panel, a click on any room doing what a click does in the office, and the tooltip. It keeps the office's
 * API (layout, update, fit, focus, select, ...), so app.js drives it like the other two. */
(function () {
  'use strict';
  var CO = window.CO, esc = CO.iso.esc;
  var W = 1528, H = 810, CUT = 724;   // the picture's painted bottom bar starts at CUT; it is cut off
  // Each room: its floor's centre and half-sizes (for its glow and its click), and the painted label it covers
  // [x, y, w, h], in the picture's pixels. "stranger" is the unlabelled server room at the back on the left.
  var ROOMS = {
    audit: { c: [330, 365], r: [205, 108], plate: [213, 353, 128, 41] },
    stranger: { c: [565, 215], r: [190, 100], plate: [458, 266, 130, 40] },
    testing: { c: [765, 128], r: [185, 88], plate: [653, 106, 190, 44] },
    testing_lab: { c: [985, 232], r: [190, 100], plate: [906, 206, 119, 42] },
    hub: { c: [790, 338], r: [200, 108], plate: [710, 388, 148, 41] },
    trading_desk: { c: [1245, 302], r: [212, 112], plate: [1171, 328, 124, 40] },
    league: { c: [1065, 455], r: [212, 112], plate: [973, 490, 130, 42] },
    lot: { c: [553, 505], r: [190, 102] }
  };
  var NEED = [727, 216, 145, 30], VAULT = [1246, 531, 274, 190];

  function roomOf(d) {
    if (d.key === 'custom') return d.run_kind === 'stranger' ? 'stranger' : d.run_kind === 'league' ? 'league' : null;
    return { testing: 'testing', testing_lab: 'testing_lab', trading_desk: 'trading_desk' }[d.key] || null;
  }
  // the picture holds this company only when its departments are the five it was drawn with, one room each
  function fits(S) {
    if (CO.RO || S.departments.length !== 5) return false;
    var seen = {};
    return S.departments.every(function (d) { var r = roomOf(d); if (!r || seen[r]) return false; seen[r] = 1; return true; });
  }
  function px(b) { return 'left:' + b[0] + 'px;top:' + b[1] + 'px;min-width:' + b[2] + 'px;min-height:' + b[3] + 'px'; }
  function ell(c, r, k) { return 'left:' + (c[0] - r[0] * k) + 'px;top:' + (c[1] - r[1] * k) + 'px;width:' + (2 * r[0] * k) + 'px;height:' + (2 * r[1] * k) + 'px'; }

  function OfficePic(el, stage, tipFor) {
    this.el = el; this.stage = stage; this.tipFor = tipFor; this.sel = null; this.keys = {};
    this.tip = stage.querySelector('.tip');
  }
  OfficePic.fits = fits;
  OfficePic.prototype.layout = function () {
    // behind the picture, the same picture blurred to cover the stage: space all round, no bars
    var S = CO.S, self = this, h = '<img class="opic-bg" src="look-office.webp" alt="" draggable="false"><div class="opic-in" id="opic-in"><img src="look-office.webp" alt="" draggable="false">';
    this.keys = { audit: 'audit', hub: 'hub', lot: 'lot' };
    S.departments.forEach(function (d) { var r = roomOf(d); if (r) self.keys[r] = 'd' + d.id; });
    Object.keys(ROOMS).forEach(function (r) {
      var R = ROOMS[r], key = self.keys[r]; if (!key) return;
      if (r === 'trading_desk') h += '<div class="opfix" data-r="' + r + '" style="' + ell(R.c, R.r, 1.3) + '"></div>';
      h += '<div class="opglow" data-r="' + r + '" style="' + ell(R.c, R.r, 1.0) + '"></div>';
      h += '<div class="ophit" data-key="' + key + '" style="' + ell(R.c, R.r, 0.82) + '"></div>';
      if (R.plate) h += '<div class="p3 pp" data-key="' + key + '" style="' + px(R.plate) + '"></div>';
    });
    h += '<div class="opneed" id="opneed" style="' + px(NEED) + '"></div>';
    h += '<div class="opvault" id="opvault" data-key="vault" style="' + px(VAULT) + '"></div></div>';
    this.el.innerHTML = h;
    Array.prototype.forEach.call(this.el.querySelectorAll('[data-key]'), function (n) {
      n.addEventListener('click', function () { CO.emit('office:click', n.getAttribute('data-key')); });
      n.addEventListener('mouseenter', function () { self.hover = n.getAttribute('data-key'); self.paintSel(); });
      n.addEventListener('mouseleave', function () { self.hover = null; self.paintSel(); if (self.tip) self.tip.hidden = true; });
      if (n.classList.contains('ophit')) n.addEventListener('mousemove', function (e) { self.showTip(n.getAttribute('data-key'), e); });
    });
    $('opneed').addEventListener('click', function () { CO.emit('office:click', 'hub'); });
    this.update();
  };
  OfficePic.prototype.showTip = function (key, e) {
    var html = this.tipFor('room', key); if (!html || !this.tip) return;
    var r = this.stage.getBoundingClientRect();
    this.tip.innerHTML = html; this.tip.hidden = false;
    var x = e.clientX - r.left + 14, y = e.clientY - r.top + 14;
    if (x + this.tip.offsetWidth > r.width - 8) x = e.clientX - r.left - this.tip.offsetWidth - 14;
    if (y + this.tip.offsetHeight > r.height - 8) y = e.clientY - r.top - this.tip.offsetHeight - 14;
    this.tip.style.left = x + 'px'; this.tip.style.top = y + 'px';
  };
  function $(id) { return document.getElementById(id); }
  OfficePic.prototype.update = function () {
    var S = CO.S, self = this;
    if (!fits(S)) { if (this.onUnfit) this.onUnfit(); return; }
    var set = function (key, html, st) {
      var p = self.el.querySelector('.pp[data-key="' + key + '"]'); if (p && p._h !== html) { p._h = html; p.innerHTML = html; }
      var r = null; Object.keys(self.keys).forEach(function (k) { if (self.keys[k] === key) r = k; });
      var g = r && self.el.querySelector('.opglow[data-r="' + r + '"]');
      if (g) { g.classList.toggle('work', st === 'working'); g.classList.toggle('wait', st === 'waiting'); }
      var fx = r === 'trading_desk' && self.el.querySelector('.opfix'); if (fx) fx.classList.toggle('red', st === 'waiting');
    };
    var TONE = { cyan: '#00cfff', red: '#ff4444', blue: '#dfe6ee', dim: '#a9b8cc' }, DOT = { working: '#00cfff', waiting: '#ff4444', queued: '#3b82f6', idle: '#7f93ad' };
    S.departments.forEach(function (d) {
      var v = CO.deptView(d), ln = CO.deptLine(d, v), st = ln.tone === 'red' ? 'waiting' : v.status, n = d.et10 || 0;
      var et = d.files_as ? '<span class="et' + (n ? ' lit' : '') + '">' + (n ? '+' : '') + n.toLocaleString('en-US') + ' ET10</span>' : '';
      set('d' + d.id, '<div class="p3h"><i style="background:' + (DOT[st] || DOT.idle) + '"></i><b>' + esc(d.name.toUpperCase()) + '</b>' + et + '</div>' +
        '<div class="p3l" style="color:' + (TONE[ln.tone] || TONE.dim) + '">' + esc(ln.short) + '</div>', st);
    });
    var paused = S.company.status === 'paused';
    set('hub', '<div class="p3h"><i style="background:' + (paused ? '#7f93ad' : '#00cfff') + '"></i><b>MANAGER</b></div><div class="p3l" style="color:' + (paused ? '#a9b8cc' : '#00cfff') + '">' + (paused ? 'Paused' : 'Your chat · runs it all') + '</div>', paused ? 'idle' : 'working');
    var A = S.audit, days = Math.max(0, Math.ceil((A.next_at - S.clock) / 86400000));
    set('audit', '<div class="p3h"><i style="background:#7f93ad"></i><b>WEEKLY AUDIT</b></div><div class="p3l" style="color:#a9b8cc">next in ' + days + (days === 1 ? ' day' : ' days') + '</div>', 'idle');
    var na = S.approvals.length, need = $('opneed');
    need.className = 'opneed' + (na ? ' on' : ''); need.textContent = na ? na + (na === 1 ? ' NEEDS YOU' : ' NEED YOU') : 'ALL CLEAR';
    var V = CO.vaultTotals(), vh = '<span class="k">VAULT</span><div class="vv"><b class="g">' + CO.fmtEt(V.et10) + '</b><span>ET10</span></div><div class="vv"><b class="u">' + CO.fmtUsd(V.usdc) + '</b><span>USDC</span></div><span class="go">Open the vault →</span>';
    var vc = $('opvault'); if (vc._h !== vh) { vc._h = vh; vc.innerHTML = vh; }
    this.paintSel();
  };
  OfficePic.prototype.paintSel = function () {
    var self = this;
    Array.prototype.forEach.call(this.el.querySelectorAll('.ophit'), function (n) { var k = n.getAttribute('data-key'); n.classList.toggle('sel', k === self.sel || k === self.hover); });
  };
  // the picture as large as the stage allows, whole, centred (the painted bottom bar cut off)
  OfficePic.prototype.resize = function () {
    var inn = $('opic-in'); if (!inn) return;
    var w = this.el.clientWidth, h = this.el.clientHeight; if (!w || !h) return;
    var s = Math.min(w / W * 1.06, h / CUT);   // a sliver of empty space at the sides may go
    inn.style.transform = 'translate(' + ((w - W * s) / 2).toFixed(1) + 'px,' + ((h - CUT * s) / 2).toFixed(1) + 'px) scale(' + s.toFixed(4) + ')';
  };
  OfficePic.prototype.fit = function () { this.resize(); };
  OfficePic.prototype.focus = function (key) { this.sel = key; this.paintSel(); };
  OfficePic.prototype.select = function (key) { this.sel = key; this.paintSel(); };
  OfficePic.prototype.zoom = function () {};
  OfficePic.prototype.packet = function () {};
  CO.OfficePic = OfficePic;
})();
