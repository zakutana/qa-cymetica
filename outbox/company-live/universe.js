/* The /company mockup: the Universe map. Every company stands on one isometric map in the building its owner
 * picked, ONE FLOOR PER DEPARTMENT (a giant company is a panel block), its name on a banner. A floor lights up
 * while its department works. Public companies open read only; a private one shows its name, building and
 * mission. Drawn with the office's projection and palette (CO.iso); the camera pans and zooms the viewBox.
 * The building pictures in Settings and in "Create your company" come from the same CO.skinArt. */
(function () {
  'use strict';
  var CO = window.CO;
  var I = CO.iso, SC = I.SC, P = I.P, f1 = I.f1, pts = I.pts, box = I.box, esc = I.esc, C = I.C;
  var PS = 6, ST = 2, CELL = PS + ST, GRID = 5, CORE = [2, 2], MINE = [3, 2], FH = 0.8;
  var RX = SC * I.C30 * Math.SQRT2, RY = SC * I.S30 * Math.SQRT2;   // a circle of radius 1 tile, seen from the map
  var WALL_L = '#14223a', WALL_R = '#0e1828', ROOF = '#1b2b46';

  function rng(seed) {
    var s = Math.abs(Math.floor(seed * 9301 + 49297)) % 233280 || 1;
    return function () { s = (s * 9301 + 49297) % 233280; return s / 233280; };
  }
  function floorsOf(c) { return Math.max(1, Math.min(8, (c.departments || []).length || 1)); }
  function fpOf(n) { return n <= 2 ? 2.3 : n <= 5 ? 2.9 : 3.5; }
  CO.floorsOf = floorsOf;

  /* ---------------- the map's model, drawn twice: here in SVG and in u3d.js in 3D ---------------- */
  // one copy, so the two pictures cannot drift apart
  CO.uvRng = rng; CO.fpOf = fpOf; CO.uvGrid = { GRID: GRID, CORE: CORE, MINE: MINE };
  // where each company stands: the biggest at the back, so a small one in front is never hidden
  CO.uvPlan = function (mine) {
    var slots = [], i, j;
    for (i = 0; i < GRID; i++) for (j = 0; j < GRID; j++) {
      if ((i === CORE[0] && j === CORE[1]) || (i === MINE[0] && j === MINE[1])) continue;
      slots.push([i, j]);
    }
    slots.sort(function (a, b) { return (a[0] + a[1]) - (b[0] + b[1]) || Math.abs(a[0] - a[1]) - Math.abs(b[0] - b[1]) || a[0] - b[0]; });
    var list = CO.UNIVERSE.slice().sort(function (a, b) { return floorsOf(b) - floorsOf(a) || a.id - b.id; });
    var items = list.map(function (c, k) { return { c: c, at: slots[k] }; }).filter(function (it) { return it.at; });
    items.push({ c: mine, at: MINE, mine: true });
    return items;
  };
  // a lively first look: some floors already at work
  CO.uvSeed = function (items, live) {
    items.forEach(function (it) {
      if (it.mine || it.c.status === 'paused') return;
      var n = floorsOf(it.c), R = rng(it.c.id * 3);
      live[it.c.id] = R() < 0.55 ? [Math.floor(R() * n)] : [];
    });
  };
  // one beat of the sample companies: up to three change which floors work; the picture answers what changed
  CO.uvStep = function (items, live) {
    var pool = items.filter(function (it) { return !it.mine && it.c.status !== 'paused'; }), out = [];
    for (var k = 0; k < 3 && pool.length; k++) {
      var it = pool[Math.floor(Math.random() * pool.length)], n = floorsOf(it.c), on = [];
      var w = Math.random() < 0.3 ? 0 : (n > 1 && Math.random() < 0.3 ? 2 : 1);
      while (on.length < w) { var f = Math.floor(Math.random() * n); if (on.indexOf(f) < 0) on.push(f); }
      var was = (live[it.c.id] || []).length;
      live[it.c.id] = on;
      var qa = (it.c.departments || []).some(function (d) { return d.key === 'testing'; });
      var bug = !!(qa && on.length && Math.random() < 0.1);
      if (bug) it.c.bugs = (it.c.bugs || 0) + 1;
      out.push({ it: it, on: on, was: was, bug: bug });
    }
    return out;
  };
  CO.uvStats = function (items, live) {
    var pub = 0, work = 0;
    items.forEach(function (it) {
      if (it.c.public) pub++;
      work += (it.mine ? (it.c.working || []) : (live[it.c.id] || [])).length;
    });
    return { companies: items.length, public: pub, working: work };
  };
  CO.uvTip = function (id, it, live) {
    if (id === 'core') return '<b class="c">Cymetica</b><br>Every company here works on it.';
    if (!it) return '';
    var c = it.c, n = floorsOf(c), work = (it.mine ? (c.working || []) : (live[c.id] || [])).length;
    var et = it.mine ? (c.et10 || 0) : CO.uvEt10(c), acc = CO.accentHex(c.accent);
    var nums = '<b>' + n + '</b> department' + (n === 1 ? '' : 's') + (c.public || it.mine ? ' · <b>' + work + '</b> working now' + (et ? ' · <b class="g">+' + et.toLocaleString('en-US') + '</b> ET10' : '') : '');
    var act = it.mine ? '<span class="g">Your company · click to open your office</span>' + (c.public ? '' : '<br><span>Private: others see its name, building and mission</span>')
      : c.public ? (c.status === 'paused' ? '<span>Paused · click to look inside</span>' : '<span class="c">Click to look inside →</span>') : '<span>Private · click for its description</span>';
    return '<div class="uvt"><b style="color:' + acc + '">' + esc(c.name) + '</b><span>@' + esc(c.owner) + '</span></div><div>' + nums + '</div><div>' + act + '</div>';
  };

  /* ---------------- the pieces of a building ---------------- */
  // one row of windows on a wall, in the wall's own pixels (tf maps them onto it)
  function wins(tf, wPx, hPx, acc, R, lit, step) {
    step = step || 7.4;
    var n = Math.max(1, Math.floor((wPx - 3) / step)), x0 = (wPx - n * step) / 2 + 1.7, out = '<g transform="' + tf + '">';
    for (var i = 0; i < n; i++) {
      var on = R() < lit, fl = on && R() < 0.2;
      out += '<rect class="w' + (on ? ' on' : '') + (fl ? ' fl' : '') + '" x="' + f1(x0 + i * step) + '" y="' + f1(hPx * 0.3) + '" width="4" height="' + f1(hPx * 0.4) +
        '" fill="' + acc + '"' + (fl ? ' style="animation-delay:-' + (R() * 5).toFixed(2) + 's"' : '') + '/>';
    }
    return out + '</g>';
  }
  // a flat cylinder from z0 to z1: its front band and its top
  function cyl(cx, cy, z0, z1, r, top, side, stroke) {
    var a = P(cx, cy, z0), b = P(cx, cy, z1), rx = r * RX, ry = r * RY, s = stroke || C.line2;
    return '<path d="M' + f1(a[0] - rx) + ',' + f1(b[1]) + ' A' + f1(rx) + ',' + f1(ry) + ' 0 0 0 ' + f1(a[0] + rx) + ',' + f1(b[1]) +
      ' L' + f1(a[0] + rx) + ',' + f1(a[1]) + ' A' + f1(rx) + ',' + f1(ry) + ' 0 0 1 ' + f1(a[0] - rx) + ',' + f1(a[1]) + ' Z" fill="' + side + '" stroke="' + s + '" stroke-width=".6"/>' +
      '<ellipse cx="' + f1(b[0]) + '" cy="' + f1(b[1]) + '" rx="' + f1(rx) + '" ry="' + f1(ry) + '" fill="' + top + '" stroke="' + s + '" stroke-width=".6"/>';
  }
  // windows round the front of a cylinder band
  function ring(cx, cy, zMid, r, acc, R, lit, m) {
    var c = P(cx, cy, zMid), rx = r * RX, ry = r * RY, out = '';
    for (var i = 0; i < m; i++) {
      var ph = -1.25 + 2.5 * (i + 0.5) / m, x = c[0] + rx * Math.sin(ph), y = c[1] + ry * Math.cos(ph), on = R() < lit;
      out += '<rect class="w' + (on ? ' on' : '') + '" x="' + f1(x - 1.6) + '" y="' + f1(y - 3.6) + '" width="3.2" height="6" rx=".6" fill="' + acc + '"/>';
    }
    return out;
  }
  function line(a, b, col, w, op, cls) {
    return '<line' + (cls ? ' class="' + cls + '"' : '') + ' x1="' + f1(a[0]) + '" y1="' + f1(a[1]) + '" x2="' + f1(b[0]) + '" y2="' + f1(b[1]) +
      '" stroke="' + col + '" stroke-width="' + (w || 1) + '"' + (op != null ? ' opacity="' + op + '"' : '') + '/>';
  }
  function beacon(p, acc, r) { return '<circle class="beacon" cx="' + f1(p[0]) + '" cy="' + f1(p[1]) + '" r="' + (r || 2.6) + '" fill="' + acc + '"/>'; }

  /* ---------------- the six buildings, n floors each ---------------- */
  var SKIN = {};
  // a glass tower: floor on floor, a crown and a mast with its light
  SKIN.tower = function (n, acc, R) {
    var fp = fpOf(n), x0 = 3 - fp / 2, y0 = 3 - fp / 2, z = 0.22, out = box(x0 - 0.3, y0 - 0.3, 0, fp + 0.6, fp + 0.6, 0.22, C.line3, C.navy2, C.navy, C.line2);
    for (var f = 0; f < n; f++) {
      var h = FH - 0.06;
      out += '<g class="fl" data-f="' + f + '">' + box(x0, y0, z, fp, fp, h, ROOF, WALL_L, WALL_R, C.line2) +
        wins(I.onBack(x0, 0, y0 + fp, z + h), fp * SC, h * SC, acc, R, 0.42) + wins(I.onSide(x0 + fp, y0, 0, z + h), fp * SC, h * SC, acc, R, 0.42) + '</g>';
      z += FH;
    }
    out += line(P(x0 + fp, y0 + fp, 0.22), P(x0 + fp, y0 + fp, z), acc, 1.4, 0.75, 'edge');
    out += box(x0 + fp * 0.22, y0 + fp * 0.22, z, fp * 0.56, fp * 0.56, 0.32, C.line3, C.navy2, C.navy, C.line2);
    var m0 = P(3, 3, z + 0.32), m1 = P(3, 3, z + 1.45);
    out += line(m0, m1, C.dim2, 1.2) + beacon(m1, acc);
    return { svg: out, top: z + 1.5 };
  };
  // a biodome: a round drum of floors under a glass dome
  SKIN.dome = function (n, acc, R) {
    var r = fpOf(n) / 2 + 0.5, z = 0.2, out = cyl(3, 3, 0, 0.2, r + 0.35, C.line3, C.navy2);
    for (var f = 0; f < n; f++) {
      var h = FH - 0.05;
      out += '<g class="fl" data-f="' + f + '">' + cyl(3, 3, z, z + h, r, ROOF, WALL_L) + ring(3, 3, z + h / 2, r, acc, R, 0.45, Math.round(r * 5)) + '</g>';
      z += FH;
    }
    var t = P(3, 3, z), rx = r * RX, ry = r * RY, up = r * SC * 0.92;
    out += '<ellipse class="core" cx="' + f1(t[0]) + '" cy="' + f1(t[1] - up * 0.3) + '" rx="' + f1(rx * 0.45) + '" ry="' + f1(up * 0.32) + '" fill="' + acc + '" opacity=".22"/>';
    out += '<path class="glass" d="M' + f1(t[0] - rx) + ',' + f1(t[1]) + ' A' + f1(rx) + ',' + f1(up) + ' 0 0 1 ' + f1(t[0] + rx) + ',' + f1(t[1]) +
      ' A' + f1(rx) + ',' + f1(ry) + ' 0 0 1 ' + f1(t[0] - rx) + ',' + f1(t[1]) + ' Z" fill="' + acc + '" fill-opacity=".09" stroke="' + acc + '" stroke-opacity=".9" stroke-width="1.2"/>';
    [0.4, 0.72].forEach(function (k) {
      var y = t[1] - up * k, q = Math.sqrt(1 - k * k);
      out += '<path d="M' + f1(t[0] - rx * q) + ',' + f1(y) + ' A' + f1(rx * q) + ',' + f1(ry * q) + ' 0 0 0 ' + f1(t[0] + rx * q) + ',' + f1(y) + '" fill="none" stroke="' + acc + '" stroke-opacity=".45" stroke-width=".8"/>';
    });
    [-0.62, 0, 0.62].forEach(function (s) {
      var x = t[0] + rx * Math.sin(s), y = t[1] + ry * Math.cos(s);
      out += '<path d="M' + f1(x) + ',' + f1(y) + ' Q' + f1(t[0] + rx * Math.sin(s) * 1.05) + ',' + f1(t[1] - up * 0.95) + ' ' + f1(t[0]) + ',' + f1(t[1] - up) + '" fill="none" stroke="' + acc + '" stroke-opacity=".4" stroke-width=".8"/>';
    });
    out += beacon([t[0], t[1] - up], acc, 2.2);
    return { svg: out, top: z + r * 0.92 + 0.5 };
  };
  // a ziggurat: one tier per floor, each rim lit, a temple and its beam on top
  SKIN.pyramid = function (n, acc, R) {
    var b0 = fpOf(n) + 1.0, inset = Math.min(0.3, (b0 - 1.1) / (2 * n)), z = 0, out = '';
    for (var f = 0; f < n; f++) {
      var b = b0 - 2 * inset * f, x0 = 3 - b / 2, y0 = 3 - b / 2, h = FH - 0.04;
      out += '<g class="fl" data-f="' + f + '">' + box(x0, y0, z, b, b, h, ROOF, WALL_L, WALL_R, C.line2) +
        '<polyline class="rim" points="' + pts([P(x0, y0 + b, z + h), P(x0 + b, y0 + b, z + h), P(x0 + b, y0, z + h)]) + '" fill="none" stroke="' + acc + '" stroke-width="1.1"/>' +
        wins(I.onBack(x0, 0, y0 + b, z + h), b * SC, h * SC, acc, R, 0.3, 9) + wins(I.onSide(x0 + b, y0, 0, z + h), b * SC, h * SC, acc, R, 0.3, 9) + '</g>';
      z += FH;
    }
    out += box(2.62, 2.62, z, 0.76, 0.76, 0.45, C.line3, C.navy2, C.navy, C.line2);
    var c = P(3, 3, z + 0.45);
    out += '<polygon class="beam" points="' + pts([[c[0] - 6, c[1]], [c[0] + 6, c[1]], [c[0] + 1.5, c[1] - 46], [c[0] - 1.5, c[1] - 46]]) + '" fill="' + acc + '"/>';
    out += beacon(c, acc, 3);
    return { svg: out, top: z + 1.4 };
  };
  // an orbital station: a spine with one disc per floor, a planet and its ring floating on top
  SKIN.orbital = function (n, acc, R) {
    var pad = fpOf(n) + 0.5, x0 = 3 - pad / 2, y0 = 3 - pad / 2, out = box(x0, y0, 0, pad, pad, 0.25, C.line3, C.navy2, C.navy, C.line2);
    var pc = P(3, 3, 0.25);
    out += '<ellipse cx="' + f1(pc[0]) + '" cy="' + f1(pc[1]) + '" rx="' + f1(pad * 0.42 * RX) + '" ry="' + f1(pad * 0.42 * RY) + '" fill="none" stroke="' + acc + '" stroke-opacity=".55" stroke-width="1"/>';
    var rd = 0.72 + fpOf(n) * 0.14, z = 0.55, top = 0.55 + n * FH;
    out += box(2.8, 2.8, 0.25, 0.4, 0.4, top - 0.1, C.line3, C.line2, C.navy, C.line2);
    for (var f = 0; f < n; f++) {
      out += '<g class="fl" data-f="' + f + '">' + cyl(3, 3, z, z + 0.26, rd, ROOF, WALL_L) + ring(3, 3, z + 0.13, rd, acc, R, 0.5, Math.round(rd * 6)) + '</g>';
      z += FH;
    }
    var Rr = 12 + Math.min(n, 8) * 1.6, sc = P(3, 3, top + 0.3), cy = sc[1] - Rr;
    var rot = 'rotate(-13 ' + f1(sc[0]) + ' ' + f1(cy) + ')', rrx = Rr * 1.95, rry = Rr * 0.5;
    var back = 'M' + f1(sc[0] - rrx) + ',' + f1(cy) + ' A' + f1(rrx) + ',' + f1(rry) + ' 0 0 1 ' + f1(sc[0] + rrx) + ',' + f1(cy);
    var front = 'M' + f1(sc[0] + rrx) + ',' + f1(cy) + ' A' + f1(rrx) + ',' + f1(rry) + ' 0 0 1 ' + f1(sc[0] - rrx) + ',' + f1(cy);
    out += '<g class="orb">';
    out += '<path d="' + back + '" transform="' + rot + '" fill="none" stroke="' + acc + '" stroke-opacity=".55" stroke-width="2"/>';
    out += '<circle cx="' + f1(sc[0]) + '" cy="' + f1(cy) + '" r="' + f1(Rr) + '" fill="' + C.navy2 + '" stroke="' + C.line3 + '"/>';
    out += '<path d="M' + f1(sc[0] - Rr * 0.92) + ',' + f1(cy - Rr * 0.18) + ' A' + f1(Rr) + ',' + f1(Rr) + ' 0 0 1 ' + f1(sc[0] + Rr * 0.3) + ',' + f1(cy - Rr * 0.95) + '" fill="none" stroke="' + acc + '" stroke-width="2.2" stroke-linecap="round" opacity=".9"/>';
    out += '<ellipse cx="' + f1(sc[0] + Rr * 0.25) + '" cy="' + f1(cy + Rr * 0.3) + '" rx="' + f1(Rr * 0.55) + '" ry="' + f1(Rr * 0.38) + '" fill="' + C.deep + '" opacity=".45"/>';
    out += '<path d="' + front + '" transform="' + rot + '" fill="none" stroke="' + acc + '" stroke-width="2.2"/>';
    out += '<circle class="sat" r="2.4" fill="' + acc + '"><animateMotion dur="7s" repeatCount="indefinite" path="' + back + ' ' + front.replace(/^M[^A]*/, '') + '" rotate="0"/></circle>';
    out += '</g>';
    return { svg: out, top: top + 0.3 + (Rr * 2 + 8) / SC };
  };
  // a launchpad: one stage of the rocket per floor, its gantry beside it, the engines glowing
  SKIN.rocket = function (n, acc, R) {
    var pad = fpOf(n) + 0.8, x0 = 3 - pad / 2, y0 = 3 - pad / 2, out = box(x0, y0, 0, pad, pad, 0.3, C.line3, C.navy2, C.navy, C.line2);
    var c = P(3.1, 3.1, 0.3), sh = FH * SC, bw = 15 + Math.min(n, 8) * 1.7, H = n * sh;
    out += '<ellipse cx="' + f1(c[0]) + '" cy="' + f1(c[1]) + '" rx="' + f1(1.25 * RX) + '" ry="' + f1(1.25 * RY) + '" fill="none" stroke="' + acc + '" stroke-opacity=".45" stroke-dasharray="4 4"/>';
    var gx = 1.25, gy = 1.95, gh = (H + 20) / SC;
    out += box(gx, gy, 0.3, 0.42, 0.42, gh, C.line3, C.line2, C.navy, C.line2);
    for (var k = 1; k <= n; k++) {
      var a = P(gx + 0.42, gy + 0.42, 0.3 + (k * sh - 4) / SC);
      out += line(a, [c[0] - bw / 2, c[1] - k * sh + 4], C.line3, 1.6);
    }
    out += '<ellipse class="flame" cx="' + f1(c[0]) + '" cy="' + f1(c[1] + 1) + '" rx="' + f1(bw * 0.95) + '" ry="' + f1(bw * 0.36) + '" fill="' + acc + '"/>';
    out += '<polygon points="' + pts([[c[0] - bw / 2, c[1] - sh * 0.95], [c[0] - bw / 2 - bw * 0.5, c[1] + 2], [c[0] - bw / 2, c[1]]]) + '" fill="' + acc + '" opacity=".55"/>';
    for (var f = 0; f < n; f++) {
      var yb = c[1] - f * sh, yt = yb - sh + 0.8, on = R() < 0.55;
      out += '<g class="fl" data-f="' + f + '">' +
        '<rect x="' + f1(c[0] - bw / 2) + '" y="' + f1(yt) + '" width="' + f1(bw) + '" height="' + f1(yb - yt) + '" fill="' + ROOF + '" stroke="' + C.line3 + '" stroke-width=".6"/>' +
        '<rect x="' + f1(c[0] + bw * 0.12) + '" y="' + f1(yt) + '" width="' + f1(bw * 0.38) + '" height="' + f1(yb - yt) + '" fill="' + C.deep + '" opacity=".45"/>' +
        line([c[0] - bw / 2, yt], [c[0] + bw / 2, yt], acc, 1, 0.7) +
        '<circle class="w' + (on ? ' on' : '') + '" cx="' + f1(c[0] - bw * 0.14) + '" cy="' + f1((yt + yb) / 2) + '" r="2.8" fill="' + acc + '"/></g>';
    }
    var tp = c[1] - H;
    out += '<path d="M' + f1(c[0] - bw / 2) + ',' + f1(tp) + ' C' + f1(c[0] - bw / 2) + ',' + f1(tp - bw * 0.7) + ' ' + f1(c[0] - bw * 0.12) + ',' + f1(tp - bw * 1.25) + ' ' + f1(c[0]) + ',' + f1(tp - bw * 1.35) +
      ' C' + f1(c[0] + bw * 0.12) + ',' + f1(tp - bw * 1.25) + ' ' + f1(c[0] + bw / 2) + ',' + f1(tp - bw * 0.7) + ' ' + f1(c[0] + bw / 2) + ',' + f1(tp) + ' Z" fill="' + C.line3 + '" stroke="' + acc + '" stroke-opacity=".8" stroke-width="1"/>';
    out += '<polygon points="' + pts([[c[0] + bw / 2, c[1] - sh * 0.95], [c[0] + bw / 2 + bw * 0.5, c[1] + 2], [c[0] + bw / 2, c[1]]]) + '" fill="' + acc + '" opacity=".75"/>';
    out += beacon([c[0], tp - bw * 1.35], acc, 2.2);
    return { svg: out, top: 0.3 + (H + bw * 1.35 + 6) / SC };
  };
  // a vault: a wide block of floors (the giant one is a panel block), a round door, server lights, a dish
  SKIN.vault = function (n, acc, R) {
    var fp = fpOf(n), w = fp + 1.1, dd = Math.max(1.9, fp * 0.82), x0 = 3 - w / 2, y0 = 3 - dd / 2, z = 0.18;
    var out = box(x0 - 0.25, y0 - 0.25, 0, w + 0.5, dd + 0.5, 0.18, C.line3, C.navy2, C.navy, C.line2);
    for (var f = 0; f < n; f++) {
      var h = (f === 0 ? FH * 1.35 : FH) - 0.05, g = '<g class="fl" data-f="' + f + '">' + box(x0, y0, z, w, dd, h, ROOF, WALL_L, WALL_R, C.line2);
      if (f === 0) {
        var dr = h * SC * 0.4;
        g += '<g transform="' + I.onBack(x0, 0, y0 + dd, z + h) + '"><circle cx="' + f1(w * SC * 0.32) + '" cy="' + f1(h * SC * 0.52) + '" r="' + f1(dr) + '" fill="' + C.deep + '" stroke="' + acc + '" stroke-width="1.3"/>' +
          '<circle cx="' + f1(w * SC * 0.32) + '" cy="' + f1(h * SC * 0.52) + '" r="' + f1(dr * 0.55) + '" fill="none" stroke="' + acc + '" stroke-opacity=".6"/>' +
          '<path d="M' + f1(w * SC * 0.32 - dr * 0.55) + ',' + f1(h * SC * 0.52) + ' h' + f1(dr * 1.1) + ' M' + f1(w * SC * 0.32) + ',' + f1(h * SC * 0.52 - dr * 0.55) + ' v' + f1(dr * 1.1) + '" stroke="' + acc + '" stroke-opacity=".6"/>' +
          '<rect x="' + f1(w * SC * 0.55) + '" y="' + f1(h * SC * 0.35) + '" width="' + f1(w * SC * 0.36) + '" height="' + f1(h * SC * 0.3) + '" rx="1" fill="' + acc + '" opacity=".18"/></g>';
      } else g += wins(I.onBack(x0, 0, y0 + dd, z + h), w * SC, h * SC, acc, R, 0.5, 8.4);
      g += '<g transform="' + I.onSide(x0 + w, y0, 0, z + h) + '">';
      for (var k = 0; k < Math.floor(dd * SC / 6); k++) g += '<rect class="led" x="' + (3 + k * 6) + '" y="' + f1(h * SC * 0.45) + '" width="3" height="1.6" fill="' + acc + '" style="animation-delay:-' + (R() * 2).toFixed(2) + 's"/>';
      out += g + '</g></g>';
      z += h + 0.05;
    }
    out += box(x0 + 0.4, y0 + 0.35, z, 0.5, 0.5, 0.3, C.line3, C.navy2, C.navy, C.line2) + box(x0 + 1.1, y0 + 0.35, z, 0.5, 0.5, 0.3, C.line3, C.navy2, C.navy, C.line2);
    var dc = P(x0 + w - 0.8, y0 + dd - 0.7, z + 0.35);
    out += line(P(x0 + w - 0.8, y0 + dd - 0.7, z), dc, C.dim2, 1.2);
    out += '<ellipse cx="' + f1(dc[0]) + '" cy="' + f1(dc[1] - 3) + '" rx="9" ry="4.2" fill="' + C.line3 + '" stroke="' + acc + '" stroke-opacity=".7" transform="rotate(-20 ' + f1(dc[0]) + ' ' + f1(dc[1] - 3) + ')"/>';
    out += beacon([dc[0] + 6, dc[1] - 9], acc, 1.8);
    return { svg: out, top: z + 1.1 };
  };

  /* ---------------- a plot, a banner, a whole picture ---------------- */
  function slab(acc, priv) {
    var out = box(0, 0, -0.3, PS, PS, 0.3, '#0f1a2c', C.navy2, C.navy, C.line2);
    out += '<polyline class="rim' + (priv ? ' fence' : '') + '" points="' + pts([P(0, PS, 0), P(PS, PS, 0), P(PS, 0, 0)]) + '" fill="none" stroke="' + acc + '" stroke-width="1.4"/>';
    out += '<polyline points="' + pts([P(0, PS, 0), P(0, 0, 0), P(PS, 0, 0)]) + '" fill="none" stroke="' + C.line3 + '" stroke-width="1"/>';
    out += I.plant(0.15, 5.42) + I.plant(5.42, 0.15);
    var l1 = P(5.6, 5.6, 0), l2 = P(5.6, 5.6, 0.9);
    out += line(l1, l2, C.line3, 1.2) + '<circle cx="' + f1(l2[0]) + '" cy="' + f1(l2[1]) + '" r="1.6" fill="' + acc + '" opacity=".8"/>';
    return out;
  }
  // the building alone, with or without its plot, in the plot's own coordinates
  CO.skinArt = function (o) {
    var acc = CO.accentHex(o.accent), n = Math.max(1, Math.min(8, o.floors || 1));
    var b = (SKIN[o.skin] || SKIN.tower)(n, acc, rng(o.seed || 7));
    return { svg: (o.plot === false ? '' : slab(acc, o.priv)) + b.svg, top: b.top, acc: acc };
  };
  var LOCK = function (x, y, col) {
    return '<g class="lock" transform="translate(' + f1(x) + ' ' + f1(y) + ')"><path d="M-3,-1 v-2.6 a3,3 0 0 1 6,0 v2.6" fill="none" stroke="' + col + '" stroke-width="1.3"/>' +
      '<rect x="-4.2" y="-1.2" width="8.4" height="6.4" rx="1.2" fill="' + col + '"/></g>';
  };
  // the name on a banner over the building: a ribbon on a tether, a lock when private, YOU over your own
  function banner(x, y, name, acc, o) {
    o = o || {};
    var fs = o.fs || 12.5, lab = String(name || '').toUpperCase();
    if (lab.length > 22) lab = lab.slice(0, 21) + '…';
    var lw = o.lock ? 14 : 0, tw = lab.length * fs * 0.78, W = tw + lw + 24, H = fs + 10, by = y - (o.lift || 30);
    var l = x - W / 2, r = x + W / 2, t = by - H / 2, b = by + H / 2, nt = 7;
    var out = '<g class="ban' + (o.cls ? ' ' + o.cls : '') + '"' + (o.id != null ? ' data-id="' + o.id + '"' : '') + '>' +
      line([x, y], [x, b], acc, 1, 0.55) + '<circle cx="' + f1(x) + '" cy="' + f1(y) + '" r="2" fill="' + acc + '"/>' +
      '<polygon class="rib" points="' + pts([[l - nt, t], [r + nt, t], [r + 1.5, by], [r + nt, b], [l - nt, b], [l - 1.5, by]]) + '" fill="#0a0e17" fill-opacity=".92" stroke="' + acc + '" stroke-width="1.3"/>' +
      (o.lock ? LOCK(l + 10, by - 1.4, C.dim) : '') +
      '<text x="' + f1(x + lw / 2) + '" y="' + f1(by + fs * 0.36) + '" text-anchor="middle" font-family="\'Archivo Black\',sans-serif" font-size="' + fs + '" fill="#e6edf7" letter-spacing=".4">' + esc(lab) + '</text>';
    if (o.you) {
      out += '<rect x="' + f1(x - 17) + '" y="' + f1(t - 15) + '" width="34" height="12" rx="6" fill="' + C.green + '"/>' +
        '<text x="' + f1(x) + '" y="' + f1(t - 6) + '" text-anchor="middle" font-family="\'JetBrains Mono\',monospace" font-weight="800" font-size="8" fill="' + C.bg + '">YOU</text>';
    }
    return out + '</g>';
  }
  // a whole picture: plot, building and (optionally) the banner, in an <svg> sized to fit them
  CO.skinSVG = function (o) {
    var a = CO.skinArt(o), top = P(3, 3, a.top)[1], bn = o.banner != null;
    var x0 = P(0, PS, 0)[0] - 6, x1 = P(PS, 0, 0)[0] + 6, y0 = Math.min(P(0, 0, 0)[1], top) - (bn ? 58 + (o.you ? 14 : 0) : 10), y1 = P(PS, PS, -0.3)[1] + 6;
    var w = x1 - x0, h = y1 - y0;
    return '<svg class="skinsvg" viewBox="' + f1(x0) + ' ' + f1(y0) + ' ' + f1(w) + ' ' + f1(h) + '" preserveAspectRatio="xMidYMax meet" xmlns="http://www.w3.org/2000/svg">' +
      '<g class="plot' + (o.priv ? ' priv' : '') + '">' + a.svg + '</g>' +
      (bn ? banner(P(3, 3, a.top)[0], top, o.banner, a.acc, { lock: o.priv, you: o.you, fs: o.fs }) : '') + '</svg>';
  };

  /* ---------------- the map ---------------- */
  function Universe(svg, stage, h) {
    this.svg = svg; this.stage = stage; this.h = h || {};
    svg.innerHTML = '<g class="uw"><g class="ground"></g><g class="plots"></g><g class="fx"></g><g class="bans"></g></g>';
    this.gGround = svg.querySelector('.ground'); this.gPlots = svg.querySelector('.plots');
    this.gFx = svg.querySelector('.fx'); this.gBans = svg.querySelector('.bans');
    this.tip = stage.querySelector('.tip'); this.stars = stage.querySelector('.stars');
    this.vb = { x: 0, y: 0, w: 1000, h: 600 };
    this.live = {}; this.mineKey = '';
    this.makeStars();
    this.bind();
    var self = this;
    setInterval(function () { if (self.visible()) self.pulse(); }, 1700);
    if (window.ResizeObserver) new ResizeObserver(function () { self.resize(); }).observe(svg);
  }
  CO.Universe = Universe;
  Universe.prototype.visible = function () { return this.svg.getBoundingClientRect().width > 0; };

  Universe.prototype.layout = function () {
    this.items = CO.uvPlan(this.h.mine());
    CO.uvSeed(this.items, this.live);
    this.drawGround();
    this.draw();
  };
  Universe.prototype.drawGround = function () {
    var W = GRID * CELL - ST, g = '', a, b, k;
    g += box(-1.6, -1.6, -0.75, W + 3.2, W + 3.2, 0.45, '#0b1424', C.navy2, '#070b13', C.line2);
    for (k = 0; k <= W; k += 2) {
      a = P(k, -1.6, -0.3); b = P(k, W + 1.6, -0.3); g += line(a, b, '#0f1b2e', 0.6);
      a = P(-1.6, k, -0.3); b = P(W + 1.6, k, -0.3); g += line(a, b, '#0f1b2e', 0.6);
    }
    var cars = '', cols = [C.cyan, C.green, C.blue, C.cyan], n = 0;
    for (k = 0; k < GRID - 1; k++) {
      var s = k * CELL + PS + ST / 2;
      a = P(s, -1.6, -0.3); b = P(s, W + 1.6, -0.3);
      g += '<line class="street" x1="' + f1(a[0]) + '" y1="' + f1(a[1]) + '" x2="' + f1(b[0]) + '" y2="' + f1(b[1]) + '"/>';
      cars += car(a, b, cols[n++ % 4], 15 + (k * 5) % 9, k * 3.1) + car(b, a, cols[n++ % 4], 19 + (k * 7) % 8, k * 1.7 + 4);
      a = P(-1.6, s, -0.3); b = P(W + 1.6, s, -0.3);
      g += '<line class="street" x1="' + f1(a[0]) + '" y1="' + f1(a[1]) + '" x2="' + f1(b[0]) + '" y2="' + f1(b[1]) + '"/>';
      cars += car(a, b, cols[n++ % 4], 17 + (k * 3) % 9, k * 2.3 + 1) + car(b, a, cols[n++ % 4], 21 + (k * 5) % 7, k * 2.9 + 6);
    }
    var e1 = P(-1.6, W + 1.6, -0.3), e2 = P(W + 1.6, W + 1.6, -0.3), e3 = P(W + 1.6, -1.6, -0.3);
    g += '<polyline class="edgeglow" points="' + pts([e1, e2, e3]) + '" fill="none"/>';
    this.gGround.innerHTML = g + cars + this.core();
    var c0 = [P(-1.6, -1.6, 0), P(W + 1.6, -1.6, 0), P(W + 1.6, W + 1.6, -0.75), P(-1.6, W + 1.6, -0.75)];
    this.groundRect = { x: Math.min.apply(null, c0.map(function (q) { return q[0]; })), x2: Math.max.apply(null, c0.map(function (q) { return q[0]; })),
      y: Math.min.apply(null, c0.map(function (q) { return q[1]; })), y2: Math.max.apply(null, c0.map(function (q) { return q[1]; })) };
  };
  function car(a, b, col, dur, delay) {
    return '<circle class="car" r="2.3" fill="' + col + '"><animateMotion dur="' + dur + 's" begin="-' + delay.toFixed(1) + 's" repeatCount="indefinite" path="M' + f1(a[0]) + ',' + f1(a[1]) + ' L' + f1(b[0]) + ',' + f1(b[1]) + '"/></circle>';
  }
  // the middle of the map: Cymetica, the platform every company works on
  Universe.prototype.core = function () {
    var x = CORE[0] * CELL, y = CORE[1] * CELL, cx = x + PS / 2, cy = y + PS / 2, out = '<g class="core-plot" data-id="core">';
    out += box(x, y, -0.3, PS, PS, 0.3, '#0e1a2e', C.navy2, C.navy, C.line2);
    var c = P(cx, cy, 0);
    [2.7, 2.05, 1.4].forEach(function (r, i) {
      out += '<ellipse class="cring' + (i === 1 ? ' spin' : '') + '" cx="' + f1(c[0]) + '" cy="' + f1(c[1]) + '" rx="' + f1(r * RX) + '" ry="' + f1(r * RY) + '" fill="none" stroke="' + (i === 1 ? C.cyan : C.blue) + '"/>';
    });
    out += box(cx - 0.45, cy - 0.45, 0, 0.9, 0.9, 0.85, C.line3, C.line2, C.navy, C.line2);
    var t = P(cx, cy, 0.85);
    out += '<polygon class="cbeam" points="' + pts([[t[0] - 9, t[1]], [t[0] + 9, t[1]], [t[0] + 3, t[1] - 175], [t[0] - 3, t[1] - 175]]) + '" fill="' + C.cyan + '"/>';
    [1.5, 2.2, 2.9].forEach(function (z, i) {
      var p = P(cx, cy, z), r = 0.95 - i * 0.22;
      out += '<ellipse class="holo" style="animation-delay:-' + (i * 0.7) + 's" cx="' + f1(p[0]) + '" cy="' + f1(p[1]) + '" rx="' + f1(r * RX) + '" ry="' + f1(r * RY) + '" fill="none" stroke="' + C.cyan + '"/>';
    });
    var o = P(cx, cy, 3.6);
    out += '<circle class="corb" cx="' + f1(o[0]) + '" cy="' + f1(o[1]) + '" r="7" fill="' + C.cyan + '"/>';
    out += '<polygon fill="transparent" points="' + pts([P(x, y + PS, 0), P(x, y + PS, 4), P(x, y, 4), P(x + PS, y, 4), P(x + PS, y, 0), P(x + PS, y + PS, 0)]) + '"/>';
    return out + '</g>';
  };
  // every plot, back to front, and every banner on top of them all
  Universe.prototype.draw = function () {
    var self = this, plots = '', bans = '';
    var order = this.items.slice().sort(function (p, q) { return (p.at[0] + p.at[1]) - (q.at[0] + q.at[1]) || p.at[0] - q.at[0]; });
    order.forEach(function (it) {
      var r = self.plotSVG(it);
      plots += r.plot; bans += r.ban;
    });
    this.gPlots.innerHTML = plots;
    this.gBans.innerHTML = bans;
    this.items.forEach(function (it) { self.paintFloors(it); });
    this.stats();
  };
  Universe.prototype.plotSVG = function (it) {
    var c = it.c, n = floorsOf(c), priv = !c.public, paused = c.status === 'paused';
    var a = CO.skinArt({ skin: c.skin, accent: c.accent, floors: n, seed: it.mine ? 7 : c.id, priv: priv });
    var o = P(it.at[0] * CELL, it.at[1] * CELL, 0), tf = 'translate(' + f1(o[0]) + ' ' + f1(o[1]) + ')';
    var hit = '<polygon class="hit" fill="transparent" points="' + pts([P(0, PS, 0), P(0, PS, a.top), P(0, 0, a.top), P(PS, 0, a.top), P(PS, 0, 0), P(PS, PS, 0)]) + '"/>';
    var mine = it.mine ? '<ellipse class="mering" cx="' + f1(P(3, 3, 0)[0]) + '" cy="' + f1(P(3, 3, 0)[1]) + '" rx="' + f1(3.9 * RX) + '" ry="' + f1(3.9 * RY) + '" fill="none" stroke="' + C.green + '"/>' : '';
    var cls = 'plot' + (priv ? ' priv' : '') + (paused ? ' paused' : '') + (it.mine ? ' mine' : '');
    var top = P(3, 3, a.top);
    it.anchor = [o[0] + top[0], o[1] + top[1]];
    return {
      plot: '<g class="' + cls + '" data-id="' + c.id + '" transform="' + tf + '">' + mine + a.svg + hit + '</g>',
      ban: banner(it.anchor[0], it.anchor[1], c.name, a.acc, { id: c.id, lock: priv, you: it.mine, cls: (priv ? 'priv' : '') + (paused ? ' paused' : '') })
    };
  };
  // the floors at work light up: a department working is its floor lit
  Universe.prototype.paintFloors = function (it) {
    var g = this.gPlots.querySelector('.plot[data-id="' + it.c.id + '"]'); if (!g) return;
    var on = it.mine ? (it.c.working || []) : (this.live[it.c.id] || []);
    Array.prototype.forEach.call(g.querySelectorAll('.fl'), function (f) { f.classList.toggle('on', on.indexOf(+f.getAttribute('data-f')) >= 0); });
    g.classList.toggle('busy', on.length > 0);
  };
  // the others' days go on: a floor starts, a floor stops, now and then Cymetica pays a bug
  Universe.prototype.pulse = function () {
    if (!this.items) return;
    var self = this;
    CO.uvStep(this.items, this.live).forEach(function (s) {
      self.paintFloors(s.it);
      if (s.bug) self.pop(s.it, '+1,000 ET10');
    });
    this.stats();
  };
  Universe.prototype.pop = function (it, label) {
    if (!it.anchor) return;
    var x = it.anchor[0], y = it.anchor[1] - 64, g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.setAttribute('class', 'etpop');
    g.innerHTML = '<text x="' + f1(x) + '" y="' + f1(y) + '" text-anchor="middle" font-family="\'JetBrains Mono\',monospace" font-weight="800" font-size="13" fill="' + C.green + '">' + esc(label) + '</text>';
    this.gFx.appendChild(g);
    setTimeout(function () { g.remove(); }, 2600);
  };
  // your own company: its building follows Settings, its floors follow your departments, its ET10 pops
  Universe.prototype.setMine = function (m) {
    if (!this.items) return;
    var it = this.items.filter(function (x) { return x.mine; })[0]; if (!it) return;
    var key = [m.name, m.skin, m.accent, m.public, m.status, floorsOf(m)].join('|');
    var gain = it.c.et10 != null && m.et10 > it.c.et10 ? m.et10 - it.c.et10 : 0;
    it.c = m;
    if (key !== this.mineKey) {
      this.mineKey = key;
      var r = this.plotSVG(it), old = this.gPlots.querySelector('.plot.mine'), ob = this.gBans.querySelector('.ban[data-id="0"]');
      if (old) { var t = document.createElementNS('http://www.w3.org/2000/svg', 'g'); t.innerHTML = r.plot; old.replaceWith(t.firstChild); }
      if (ob) { var tb = document.createElementNS('http://www.w3.org/2000/svg', 'g'); tb.innerHTML = r.ban; ob.replaceWith(tb.firstChild); }
    }
    this.paintFloors(it);
    if (gain) this.pop(it, '+' + gain.toLocaleString('en-US') + ' ET10');
    this.stats();
  };
  Universe.prototype.stats = function () {
    if (this.h.onStats) this.h.onStats(CO.uvStats(this.items || [], this.live));
  };

  /* ---------------- the tooltip ---------------- */
  Universe.prototype.tipHTML = function (id) { return CO.uvTip(id, id === 'core' ? null : this.find(id), this.live); };
  Universe.prototype.find = function (id) {
    for (var i = 0; i < (this.items || []).length; i++) if (String(this.items[i].c.id) === String(id)) return this.items[i];
    return null;
  };

  /* ---------------- camera ---------------- */
  Universe.prototype.makeStars = function () {
    if (!this.stars) return;
    var R = rng(42), far = [], near = [];
    for (var i = 0; i < 220; i++) far.push(Math.round(R() * 3200 - 400) + 'px ' + Math.round(R() * 1800 - 300) + 'px 0 ' + (R() < 0.15 ? '1px' : '0') + ' rgba(169,184,204,' + (0.25 + R() * 0.45).toFixed(2) + ')');
    for (i = 0; i < 40; i++) near.push(Math.round(R() * 3200 - 400) + 'px ' + Math.round(R() * 1800 - 300) + 'px 0 1px ' + (R() < 0.5 ? 'rgba(0,207,255,.7)' : 'rgba(230,237,247,.8)'));
    this.stars.innerHTML = '<i class="far" style="box-shadow:' + far.join(',') + '"></i><i class="near" style="box-shadow:' + near.join(',') + '"></i>';
  };
  Universe.prototype.apply = function () {
    var v = this.vb;
    this.svg.setAttribute('viewBox', f1(v.x) + ' ' + f1(v.y) + ' ' + f1(v.w) + ' ' + f1(v.h));
    if (this.stars) this.stars.style.transform = 'translate(' + f1(-v.x * 0.06) + 'px,' + f1(-v.y * 0.06) + 'px)';
  };
  Universe.prototype.client = function () { var r = this.svg.getBoundingClientRect(); return { w: Math.max(50, r.width), h: Math.max(50, r.height), l: r.left, t: r.top }; };
  Universe.prototype.tween = function (to, ms, done) {
    var self = this, from = { x: this.vb.x, y: this.vb.y, w: this.vb.w, h: this.vb.h }, t0 = performance.now();
    if (!ms) { this.vb = to; this.apply(); if (done) done(); return; }
    this.tw = t0;
    (function step(now) {
      if (self.tw !== t0) return;
      var f = Math.min(1, (now - t0) / ms), e = 1 - Math.pow(1 - f, 3);
      self.vb = { x: from.x + (to.x - from.x) * e, y: from.y + (to.y - from.y) * e, w: from.w + (to.w - from.w) * e, h: from.h + (to.h - from.h) * e };
      self.apply();
      if (f < 1) requestAnimationFrame(step); else if (done) done();
    })(t0);
  };
  Universe.prototype.bounds = function () {
    var r = this.groundRect || { x: 0, y: 0, x2: 100, y2: 100 }, x = r.x, y = r.y, x2 = r.x2, y2 = r.y2;
    [this.gPlots, this.gBans].forEach(function (g) {
      var b = g.getBBox(); if (!b.width) return;
      x = Math.min(x, b.x); y = Math.min(y, b.y); x2 = Math.max(x2, b.x + b.width); y2 = Math.max(y2, b.y + b.height);
    });
    return { x: x - 10, y: y - 10, w: x2 - x + 20, h: y2 - y + 20 };
  };
  Universe.prototype.fit = function (anim) {
    var b = this.bounds(), c = this.client(), top = 40, availH = Math.max(80, c.h - top);
    var k = Math.min(c.w / b.w, availH / b.h), w = c.w / k, h = c.h / k;
    var x = b.x + b.w / 2 - w / 2, y = b.y - top / k - (availH / k - b.h) / 2;
    this.fitted = true;
    this.tween({ x: x, y: y, w: w, h: h }, anim === false ? 0 : 450);
  };
  Universe.prototype.zoom = function (f, cx, cy) {
    var c = this.client(), v = this.vb;
    var px = cx == null ? 0.5 : (cx - c.l) / c.w, py = cy == null ? 0.5 : (cy - c.t) / c.h;
    var b = this.bounds(), nw = Math.max(240, Math.min(b.w * 2.4, v.w * f)), k = nw / v.w, nh = v.h * k;
    var to = { x: v.x + (v.w - nw) * px, y: v.y + (v.h - nh) * py, w: nw, h: nh };
    if (cx == null) this.tween(to, 260); else { this.tw = 0; this.vb = to; this.apply(); }
  };
  // bring one company to the middle, close up
  Universe.prototype.flyTo = function (id, done, ms) {
    var it = this.find(id); if (!it || !it.anchor) { if (done) done(); return; }
    var c = this.client(), w = 520, h = w * c.h / c.w, m = [it.anchor[0], it.anchor[1] + 70];
    this.tween({ x: m[0] - w / 2, y: m[1] - h / 2, w: w, h: h }, ms || 650, done);
  };
  Universe.prototype.resize = function () {
    var c = this.client(), v = this.vb;
    if (!this.fitted) return;
    var cy = v.y + v.h / 2, nh = v.w * c.h / c.w;
    this.vb = { x: v.x, y: cy - nh / 2, w: v.w, h: nh };
    this.apply();
  };

  /* ---------------- input ---------------- */
  Universe.prototype.bind = function () {
    var self = this, svg = this.svg, drag = null;
    svg.addEventListener('pointerdown', function (e) {
      if (e.button !== 0) return;
      drag = { x: e.clientX, y: e.clientY, vx: self.vb.x, vy: self.vb.y, moved: false, id: e.pointerId };
    });
    window.addEventListener('pointermove', function (e) {
      if (drag) {
        var dx = e.clientX - drag.x, dy = e.clientY - drag.y;
        if (!drag.moved && Math.abs(dx) + Math.abs(dy) > 4) { drag.moved = true; svg.classList.add('grabbing'); self.hideTip(); try { svg.setPointerCapture(drag.id); } catch (er) { /* fine */ } }
        if (drag.moved) { var c = self.client(); self.tw = 0; self.vb.x = drag.vx - dx * self.vb.w / c.w; self.vb.y = drag.vy - dy * self.vb.h / c.h; self.apply(); }
        return;
      }
      if (e.target.closest && svg.contains(e.target)) self.hoverAt(e);
    });
    window.addEventListener('pointerup', function (e) {
      if (!drag) return;
      var was = drag; drag = null; svg.classList.remove('grabbing');
      if (was.moved) return;
      var t = e.target.closest ? e.target.closest('[data-id]') : null;
      if (!t || !svg.contains(t)) return;
      var id = t.getAttribute('data-id'); if (id === 'core') return;
      var it = self.find(id); if (it && self.h.onOpen) { self.hideTip(); self.h.onOpen(it); }
    });
    svg.addEventListener('wheel', function (e) { e.preventDefault(); self.zoom(Math.pow(1.0018, e.deltaY), e.clientX, e.clientY); }, { passive: false });
    svg.addEventListener('pointerleave', function () { self.hideTip(); self.setHover(null); });
  };
  Universe.prototype.setHover = function (id) {
    if (this.hover === id) return;
    var self = this;
    [this.gPlots, this.gBans, this.gGround].forEach(function (g) {
      Array.prototype.forEach.call(g.querySelectorAll('.hov'), function (x) { x.classList.remove('hov'); });
      if (id != null) Array.prototype.forEach.call(g.querySelectorAll('[data-id="' + id + '"]'), function (x) { x.classList.add('hov'); });
    });
    self.hover = id;
  };
  Universe.prototype.hoverAt = function (e) {
    var t = e.target.closest('[data-id]'), id = t ? t.getAttribute('data-id') : null;
    this.setHover(id);
    var html = id != null ? this.tipHTML(id) : '';
    if (!html) return this.hideTip();
    var r = this.stage.getBoundingClientRect();
    this.tip.innerHTML = html; this.tip.hidden = false;
    var x = e.clientX - r.left + 16, y = e.clientY - r.top + 16;
    if (x + this.tip.offsetWidth > r.width - 8) x = e.clientX - r.left - this.tip.offsetWidth - 16;
    if (y + this.tip.offsetHeight > r.height - 8) y = e.clientY - r.top - this.tip.offsetHeight - 16;
    this.tip.style.left = x + 'px'; this.tip.style.top = y + 'px';
  };
  Universe.prototype.hideTip = function () { if (this.tip) this.tip.hidden = true; };
})();
