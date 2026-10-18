/* The /company mockup: the office composed live from the operator's Gemini pieces (gemini-prompts.md; keyed and
 * measured by tools/sprites.py into assets/gen/), the way the Universe is (uvlive.js): his platform, and on its
 * plates one room per department (a QA room for QA, a lab for the lab, a trading room for the desk), the Manager
 * in the middle, the weekly Audit and the Vault. Unlike his painted picture (opic.js) it holds any company of up
 * to five departments, a visit included; more need the 4 x 4 platform still to come, and go to 3D or flat.
 * It keeps the picture's plates, glows, badge, tooltip and API (OfficePic): only where things stand differs.
 * assets/gen/ is kept out of git: where the pieces are not, load() answers false and the picture stays. */
(function () {
  'use strict';
  var CO = window.CO, OfficePic = CO.OfficePic, BASE = 'assets/gen/', PLAT = 'O-platform-3x3';
  var K = 1528 / 2576;   // the stage works in the painted picture's units, so plates keep the size they have there
  // which plate holds what: the Manager in the middle, the Audit on the left, the Vault in front of it, the
  // departments by their slot round the back and the right (rows run towards the left corner, columns the right)
  var HUB = '11', AUDIT = '20', VAULT = '21', SLOT = ['00', '10', '01', '02', '12'];
  // a department's room: its own picture, or the nearest one there is until he sends it
  var ROOM = { testing: ['qa'], testing_lab: ['lab'], trading_desk: ['trading'], development: ['development'], design: ['design', 'generic', 'development'],
    stranger: ['outsider', 'generic'], league: ['league'], custom: ['generic', 'development'] };
  var M = null, state = 'idle', waits = [];

  function pick(list) { for (var i = 0; i < list.length; i++) if (M['O-room-' + list[i]]) return 'O-room-' + list[i]; return null; }
  function roomFor(d) {
    var k = d.key === 'custom' ? (d.run_kind === 'stranger' || d.run_kind === 'league' ? d.run_kind : 'custom') : d.key;
    return pick((ROOM[k] || ['generic']).concat(['development', 'qa']));
  }
  // sprites.json, once; ok when the platform with its plates and the three fixed rooms are there
  function load(cb) {
    if (state === 'ok' || state === 'no') return cb(state === 'ok');
    waits.push(cb);
    if (state === 'loading') return;
    state = 'loading';
    var done = function (ok) { state = ok ? 'ok' : 'no'; var w = waits; waits = []; w.forEach(function (f) { f(ok); }); };
    if (!window.fetch) return done(false);
    fetch(BASE + 'sprites.json', { cache: 'no-cache' }).then(function (r) { return r.ok ? r.json() : null; }).then(function (m) {
      var ok = !!(m && m[PLAT] && m[PLAT].calib && m[PLAT].calib.tiles && m['O-room-manager'] && m['O-room-audit'] && m['O-room-vault']);
      if (!ok) return done(false);
      M = m;
      // the pictures in before the first look, so rooms do not pop in one by one
      var names = [PLAT].concat(Object.keys(m).filter(function (k) { return k.indexOf('O-room-') === 0; })), left = names.length;
      names.forEach(function (n) { var im = new Image(); im.onload = im.onerror = function () { if (!--left) done(true); }; im.src = BASE + n + '.webp'; });
    }).catch(function () { done(false); });
  }
  // up to five departments, each in a slot the platform has, each with a room to show
  function fits(S) {
    return !!M && S.departments.length <= SLOT.length && S.departments.every(function (d) { return d.slot < SLOT.length && !!roomFor(d); });
  }
  function sig(S) { return S.departments.map(function (d) { return d.id + ':' + d.slot + ':' + d.key + ':' + (d.run_kind || ''); }).join('|') + (CO.RO ? '|ro' : ''); }

  // the affine that takes three points onto three others, as CSS matrix(a, b, c, d, e, f)
  function affine(s, d) {
    var x1 = s[0][0], y1 = s[0][1], x2 = s[1][0], y2 = s[1][1], x3 = s[2][0], y3 = s[2][1];
    var det = x1 * (y2 - y3) + x2 * (y3 - y1) + x3 * (y1 - y2);
    var row = function (u1, u2, u3) {
      return [(u1 * (y2 - y3) + u2 * (y3 - y1) + u3 * (y1 - y2)) / det, (x1 * (u2 - u3) + x2 * (u3 - u1) + x3 * (u1 - u2)) / det,
        (x1 * (y2 * u3 - y3 * u2) + x2 * (y3 * u1 - y1 * u3) + x3 * (y1 * u2 - y2 * u1)) / det];
    };
    var U = row(d[0][0], d[1][0], d[2][0]), V = row(d[0][1], d[1][1], d[2][1]);
    return [U[0], V[0], U[1], V[1], U[2], V[2]];
  }
  // A room onto its cell: the projective map that takes the room's four floor corners onto the cell's four, as the
  // CSS matrix3d of a 2D homography. The platform is shot with a wide lens and the rooms near orthographic, so
  // nothing simpler fits (2026-10-18): an affine through three corners sheared the rooms ("uplne krive"); one that
  // kept the walls upright could not follow the plate and left them turned, with gaps between ("mezery ... nakrivo
  // otocene"). This one takes the platform's own perspective, wall to wall; walls lean outwards at the sides as
  // that lens makes them, and look lower, nearer his picture.
  function homog(s, d) {
    var A = [], b = [], i, j, k;
    for (i = 0; i < 4; i++) {
      var x = s[i][0], y = s[i][1], u = d[i][0], v = d[i][1];
      A.push([x, y, 1, 0, 0, 0, -u * x, -u * y]); b.push(u);
      A.push([0, 0, 0, x, y, 1, -v * x, -v * y]); b.push(v);
    }
    for (i = 0; i < 8; i++) {   // Gaussian elimination with partial pivoting
      var p = i;
      for (j = i + 1; j < 8; j++) if (Math.abs(A[j][i]) > Math.abs(A[p][i])) p = j;
      var t = A[i]; A[i] = A[p]; A[p] = t; t = b[i]; b[i] = b[p]; b[p] = t;
      for (j = i + 1; j < 8; j++) { var f = A[j][i] / A[i][i]; for (k = i; k < 8; k++) A[j][k] -= f * A[i][k]; b[j] -= f * b[i]; }
    }
    var h = [];
    for (i = 7; i >= 0; i--) { var sum = b[i]; for (k = i + 1; k < 8; k++) sum -= A[i][k] * h[k]; h[i] = sum / A[i][i]; }
    return 'matrix3d(' + [h[0], h[3], 0, h[6], h[1], h[4], 0, h[7], 0, 0, 1, 0, h[2], h[5], 0, 1].map(function (v) { return +v.toPrecision(9); }).join(',') + ')';
  }
  function mat(m) { return 'matrix(' + m.map(function (v) { return v.toFixed(5); }).join(',') + ')'; }
  function f1(v) { return v.toFixed(1); }

  function OfficeLive(el, stage, tipFor) { OfficePic.call(this, el, stage, tipFor); }
  OfficeLive.prototype = Object.create(OfficePic.prototype);
  OfficeLive.prototype.constructor = OfficeLive;
  OfficeLive.load = load;
  OfficeLive.fits = function (S) { return fits(S); };
  OfficeLive.prototype.fits = fits;

  OfficeLive.prototype.layout = function () {
    var S = CO.S, self = this, P = M[PLAT], pw = P.w * K, ph = P.h * K, src = BASE + PLAT + '.webp';
    var T = {}, C = {}, cells = P.calib.cells || P.calib.tiles;
    Object.keys(P.calib.tiles).forEach(function (t) {
      T[t] = P.calib.tiles[t].map(function (p) { return [p[0] * K, p[1] * K]; });   // back, right, front, left
      C[t] = cells[t].map(function (p) { return [p[0] * K, p[1] * K]; });
    });
    var at = {}, used = {};
    at[HUB] = { key: 'hub', img: 'O-room-manager' }; at[AUDIT] = { key: 'audit', img: 'O-room-audit' }; at[VAULT] = { key: 'vault', img: 'O-room-vault' };
    S.departments.forEach(function (d) { at[SLOT[d.slot]] = { key: 'd' + d.id, img: roomFor(d) }; used[d.slot] = 1; });
    var lot = 0; while (used[lot]) lot++;
    // a visitor sees the company as it is: no empty lot inviting a department they cannot add
    if (lot < SLOT.length && !CO.RO) at[SLOT[lot]] = { key: 'lot' };
    this.sig = sig(S);
    this.keys = {};
    var order = Object.keys(at).sort(function (a, b) { return T[a][2][1] - T[b][2][1]; });   // back to front
    var h = '<img class="opic-bg" src="' + src + '" alt="" draggable="false"><div class="opic-in olive" id="opic-in" style="width:' + f1(pw) + 'px;height:' + f1(ph) + 'px">' +
      '<img class="oplat" src="' + src + '" alt="" draggable="false" style="width:' + f1(pw) + 'px;height:' + f1(ph) + 'px">';
    var over = '', hits = '';
    this.geo = {};
    order.forEach(function (t) {
      var a = at[t], q = T[t], c = [(q[0][0] + q[1][0] + q[2][0] + q[3][0]) / 4, (q[0][1] + q[1][1] + q[2][1] + q[3][1]) / 4];
      // a room's plate a little behind its middle: the back half is what a room in front leaves to be seen
      var plate = [c[0] + (q[0][0] - c[0]) * 0.12, c[1] + (q[0][1] - c[1]) * 0.12];
      self.keys[a.key] = a.key;
      self.geo[a.key] = { q: q, c: c, plate: plate };
      if (a.key === 'lot') {
        // the free plate: a holographic pad with a grid, drawn flat on the plate (a 100 px square mapped onto it)
        h += '<div class="olot" style="transform:' + mat(affine([[0, 0], [100, 0], [0, 100]], [q[0], q[1], q[3]])) + '"><i></i><i></i><i></i></div>';
        over += '<div class="p3lot" data-key="lot" style="left:' + f1(c[0]) + 'px;top:' + f1(c[1]) + 'px;transform:translate(-50%,-50%)"><b>+</b>ADD DEPARTMENT</div>';
      } else {
        var m = M[a.img], back = [m.left[0] + m.right[0] - m.bottom[0], m.left[1] + m.right[1] - m.bottom[1]], cq = C[t];
        var fl = [m.left, m.right, m.bottom, back], to = [cq[3], cq[1], cq[2], cq[0]];
        h += '<img class="oroom' + (a.key === 'vault' && CO.RO ? ' shut' : '') + '" src="' + BASE + a.img + '.webp" alt="" draggable="false" style="width:' + m.w + 'px;height:' + m.h + 'px;transform:' + homog(fl, to) + '">';
        var rx = (q[1][0] - q[3][0]) / 2, ry = (q[2][1] - q[0][1]) / 2;
        over += '<div class="opglow" data-r="' + a.key + '" style="left:' + f1(c[0] - rx) + 'px;top:' + f1(c[1] - ry) + 'px;width:' + f1(2 * rx) + 'px;height:' + f1(2 * ry) + 'px"></div>';
        if (a.key === 'vault') over += '<div class="opvault mini" id="opvault" data-key="vault" style="left:' + f1(plate[0]) + 'px;top:' + f1(plate[1]) + 'px"></div>';
        else over += '<div class="p3 pp" data-key="' + a.key + '" style="left:' + f1(plate[0]) + 'px;top:' + f1(plate[1]) + 'px"></div>';
      }
      hits += '<div class="ophit" data-key="' + a.key + '" style="clip-path:polygon(' + q.map(function (p) { return f1(p[0]) + 'px ' + f1(p[1]) + 'px'; }).join(',') + ')"></div>';
    });
    // "N need you" stands on the Manager's plate, as it does in the picture
    var hp = this.geo.hub.plate;
    h += hits + over + '<div class="opneed" id="opneed" style="left:' + f1(hp[0]) + 'px;top:' + f1(hp[1] - 44) + 'px"></div></div>';
    this.el.innerHTML = h;
    Array.prototype.forEach.call(this.el.querySelectorAll('[data-key]'), function (n) {
      n.addEventListener('click', function () { CO.emit('office:click', n.getAttribute('data-key')); });
      n.addEventListener('mouseenter', function () { self.hover = n.getAttribute('data-key'); self.paintSel(); });
      n.addEventListener('mouseleave', function () { self.hover = null; self.paintSel(); if (self.tip) self.tip.hidden = true; });
      if (n.classList.contains('ophit')) n.addEventListener('mousemove', function (e) { self.showTip(n.getAttribute('data-key'), e); });
    });
    document.getElementById('opneed').addEventListener('click', function () { CO.emit('office:click', 'hub'); });
    // what stands where: the box round the whole platform and the rooms' tops, in the stage's units (every plate,
    // used or not, so a company of two is framed as one of five is)
    var xs = [], ys = [];
    Object.keys(T).forEach(function (t) { T[t].forEach(function (p) { xs.push(p[0]); ys.push(p[1]); }); });
    this.box = [Math.min.apply(null, xs) - 70 * K, Math.min(0, Math.min.apply(null, ys) - 190 * K), Math.max.apply(null, xs) + 70 * K, Math.max.apply(null, ys) + 150 * K];
    this.update();
  };
  OfficeLive.prototype.update = function () {
    if (!fits(CO.S)) { if (this.onUnfit) this.onUnfit(); return; }
    if (this.sig !== sig(CO.S)) return this.layout();
    OfficePic.prototype.update.call(this);
    // the vault's plate, as small as the others: what it holds, or shut on a visit
    var V = CO.RO ? null : CO.vaultTotals(), vc = document.getElementById('opvault');
    var vh = '<span class="k">VAULT</span>' + (V ? '<span class="vl"><b class="g">' + CO.fmtEt(V.et10) + '</b> ET10 · <b class="u">' + CO.fmtUsd(V.usdc) + '</b> USDC</span>' : '<span class="pv">Private</span>');
    if (vc && vc._h !== vh) { vc._h = vh; vc.innerHTML = vh; }
  };
  // the platform and its rooms as large as the stage allows, whole, centred
  OfficeLive.prototype.resize = function () {
    var inn = document.getElementById('opic-in'), b = this.box; if (!inn || !b) return;
    var w = this.el.clientWidth, h = this.el.clientHeight; if (!w || !h) return;
    var bw = b[2] - b[0], bh = b[3] - b[1], s = Math.min(w / bw, h / bh);
    inn.style.transform = 'translate(' + f1((w - bw * s) / 2 - b[0] * s) + 'px,' + f1((h - bh * s) / 2 - b[1] * s) + 'px) scale(' + s.toFixed(4) + ')';
    // plates shrink with the picture only down to three quarters of their size, so a small screen can still read them
    inn.style.setProperty('--ps', Math.max(1, 0.75 / s).toFixed(3));
  };
  CO.OfficeLive = OfficeLive;
})();
