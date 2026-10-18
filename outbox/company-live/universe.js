/* The /company mockup: the Universe. Every company is a station in one galaxy round Cymetica, in the station its
 * owner picked, ONE DECK PER DEPARTMENT, its name on a banner; a deck lights up while its department works. Public
 * companies open read only; a private one shows its name, station and mission. This file holds the galaxy's model
 * (u3d.js draws it in 3D) and the flat picture of it, drawn with the office's projection and palette (CO.iso) where
 * a browser cannot draw 3D; its camera pans and zooms the viewBox. The station pictures in Settings and in "Create
 * your company" come from the same CO.skinArt. */
(function () {
  'use strict';
  var CO = window.CO;
  var I = CO.iso, SC = I.SC, P = I.P, f1 = I.f1, pts = I.pts, box = I.box, esc = I.esc, C = I.C;
  var FH = 0.8;
  var RX = SC * I.C30 * Math.SQRT2, RY = SC * I.S30 * Math.SQRT2;   // a circle of radius 1, seen from the map
  // hulls and rock in the site's slate-navy: lit from the top left, darker on the right
  var HULL = { top: '#2b3646', l: '#222b38', r: '#19202b' }, ROCK = { top: '#36404d', l: '#262d38', r: '#1b2129' };

  function rng(seed) {
    var s = Math.abs(Math.floor(seed * 9301 + 49297)) % 233280 || 1;
    return function () { s = (s * 9301 + 49297) % 233280; return s / 233280; };
  }
  function floorsOf(c) { return Math.max(1, Math.min(8, (c.departments || []).length || 1)); }
  function fpOf(n) { return n <= 2 ? 2.3 : n <= 5 ? 2.9 : 3.5; }
  CO.floorsOf = floorsOf;

  /* ---------------- the galaxy: the map's model, drawn twice -- here flat, in u3d.js in 3D ---------------- */
  // Cymetica is the star at the centre. Every company is a station on one of three spiral arms, the biggest
  // nearest the core, ours in front of it where the camera first looks, no two closer than GAP. One copy of
  // the model, so the two pictures cannot drift apart. Units are the stations' own (a deck is 0.8 high).
  var ARMS = 3, R0 = 30, R1 = 190, TWIST = 0.028, GAP = 15, AZ = 1.08;
  function armAngle(arm, r) { return arm * Math.PI * 2 / ARMS + r * TWIST; }
  CO.uvRng = rng; CO.fpOf = fpOf;
  CO.uvGalaxy = { ARMS: ARMS, R0: R0, R1: R1, AZ: AZ, angle: armAngle, outer: R1 };
  CO.uvPlan = function (mine) {
    var list = CO.UNIVERSE.slice().sort(function (a, b) { return floorsOf(b) - floorsOf(a) || a.id - b.id; });
    var R = rng(2026), gauss = function () { return R() + R() + R() + R() - 2; }, placed = [], items = [];
    var free = function (p) {
      for (var i = 0; i < placed.length; i++) {
        var q = placed[i], dx = p[0] - q[0], dy = p[1] - q[1], dz = p[2] - q[2];
        if (dx * dx + dy * dy * 0.5 + dz * dz < GAP * GAP) return false;
      }
      return true;
    };
    // ours: on the camera's side of the core, out of its glare, a little above the disc
    var me = [Math.sin(AZ) * 50, 4, Math.cos(AZ) * 50], outer = R0;
    placed.push(me); items.push({ c: mine, mine: true, pos: me });
    list.forEach(function (c, k) {
      var want = R0 + Math.pow((k + 0.5) / list.length, 0.85) * (R1 - R0), p = null;
      for (var tries = 0; tries < 400 && !p; tries++) {
        var r = want + gauss() * 9 + Math.floor(tries / 80) * 8, th = armAngle(Math.floor(R() * ARMS), r) + gauss() * 0.24;
        var q = [Math.cos(th) * r, gauss() * (2 + r * 0.05), Math.sin(th) * r];
        if (free(q)) p = q;
      }
      if (!p) p = [Math.cos(k) * (R1 + 24), 0, Math.sin(k) * (R1 + 24)];   // not with today's numbers: a last ring outside
      placed.push(p); items.push({ c: c, pos: p });
      outer = Math.max(outer, Math.hypot(p[0], p[2]));
    });
    CO.uvGalaxy.outer = outer;
    return items;
  };
  // a lively first look: some decks already at work
  CO.uvSeed = function (items, live) {
    items.forEach(function (it) {
      if (it.mine || it.c.status === 'paused') return;
      var n = floorsOf(it.c), R = rng(it.c.id * 3);
      live[it.c.id] = R() < 0.55 ? [Math.floor(R() * n)] : [];
    });
  };
  // one beat of the sample companies: up to three change which decks work; the picture answers what changed
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
    var act = it.mine ? '<span class="g">Your company · click to open your office</span>' + (c.public ? '' : '<br><span>Private: others see its name, station and mission</span>')
      : c.public ? (c.status === 'paused' ? '<span>Paused · click to look inside</span>' : '<span class="c">Click to look inside →</span>') : '<span>Private · click for its description</span>';
    return '<div class="uvt"><b style="color:' + acc + '">' + esc(c.name) + '</b><span>@' + esc(c.owner) + '</span></div><div>' + nums + '</div><div>' + act + '</div>';
  };
  // world (x, up, z) on the flat map: the galaxy's disc is the map's floor
  function gp(x, y, z) { return P(x, z, y); }

  /* ---------------- the pieces of a station ---------------- */
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
  // half an ellipse round c: the far half (behind what stands in it) or the near half (in front)
  function arc(c, rx, ry, near, col, w, op, cls) {
    return '<path' + (cls ? ' class="' + cls + '"' : '') + ' d="M' + f1(c[0] - rx) + ',' + f1(c[1]) + ' A' + f1(rx) + ',' + f1(ry) + ' 0 0 ' + (near ? 0 : 1) + ' ' + f1(c[0] + rx) + ',' + f1(c[1]) +
      '" fill="none" stroke="' + col + '" stroke-width="' + w + '"' + (op != null ? ' opacity="' + op + '"' : '') + '/>';
  }
  // an engine's flame: a soft cone in the station's colour from p, len pixels along (dx, dy)
  function flame(p, acc, w, len, dx, dy) {
    dx = dx || 0; dy = dy == null ? 1 : dy;
    var nx = -dy, ny = dx;
    return '<polygon class="flame" points="' + pts([[p[0] + nx * w / 2, p[1] + ny * w / 2], [p[0] - nx * w / 2, p[1] - ny * w / 2], [p[0] + dx * len, p[1] + dy * len]]) + '" fill="' + acc + '"/>';
  }
  // a lump of rock round c, r pixels across, lit from the top left
  function rock(c, r, R, squash) {
    var pl = [], k0 = R() * 6, sq = squash || 0.86;
    for (var k = 0; k < 16; k++) { var a = k / 16 * Math.PI * 2, j = 1 + 0.09 * Math.sin(a * 3 + k0) + 0.05 * Math.cos(a * 5 + k0); pl.push([c[0] + Math.cos(a) * r * j, c[1] + Math.sin(a) * r * sq * j]); }
    var out = '<polygon points="' + pts(pl) + '" fill="' + ROCK.l + '" stroke="' + C.line2 + '" stroke-width=".6"/>';
    out += '<ellipse cx="' + f1(c[0] - r * 0.22) + '" cy="' + f1(c[1] - r * 0.3) + '" rx="' + f1(r * 0.58) + '" ry="' + f1(r * 0.42 * sq) + '" fill="' + ROCK.top + '" opacity=".6"/>';
    for (k = 0; k < 3; k++) out += '<ellipse cx="' + f1(c[0] + (R() - 0.5) * r * 1.1) + '" cy="' + f1(c[1] + (R() - 0.2) * r * 0.6) + '" rx="' + f1(r * (0.08 + R() * 0.08)) + '" ry="' + f1(r * 0.05) + '" fill="' + ROCK.r + '"/>';
    return out;
  }

  /* ---------------- the six stations, n decks each ---------------- */
  // Each returns its picture, the top and bottom it reaches (in decks' units) and how far it reaches out (ext).
  var SKIN = {};
  // Spire: decks one on another, a docking ring round the first, a keel and its flame, a mast with its light
  SKIN.tower = function (n, acc, R) {
    var fp = fpOf(n) * 0.9, x0 = 3 - fp / 2, y0 = 3 - fp / 2, z = 0, out = '', c0 = P(3, 3, 0.32), dr = fp * 0.8;
    var c = P(3, 3, 0), kb = P(3, 3, -1.6), krx = fp * 0.47 * RX;
    out += '<polygon points="' + pts([[c[0] - krx, c[1]], [c[0] + krx, c[1]], kb]) + '" fill="' + HULL.r + '" stroke="' + C.line2 + '" stroke-width=".6"/>';
    out += flame(kb, acc, 6, 22);
    out += arc(c0, dr * RX, dr * RY, false, acc, 1.4, 0.8);
    for (var f = 0; f < n; f++) {
      var h = FH - 0.08;
      out += '<g class="fl" data-f="' + f + '">' + box(x0, y0, z, fp, fp, h, HULL.top, HULL.l, HULL.r, C.line2) +
        wins(I.onBack(x0, 0, y0 + fp, z + h), fp * SC, h * SC, acc, R, 0.45) + wins(I.onSide(x0 + fp, y0, 0, z + h), fp * SC, h * SC, acc, R, 0.45) + '</g>';
      out += line(P(x0 + fp, y0 + fp, z), P(x0 + fp, y0 + fp, z + h), acc, 1.3, 0.85, 'edge');
      z += FH;
    }
    out += arc(c0, dr * RX, dr * RY, true, acc, 1.6, 0.95);
    out += box(x0 + fp * 0.19, y0 + fp * 0.19, z, fp * 0.62, fp * 0.62, 0.36, C.line3, C.navy2, C.navy, C.line2);
    var m0 = P(3, 3, z + 0.36), m1 = P(3, 3, z + 1.5);
    out += line(m0, m1, C.dim2, 1.2) + beacon(m1, acc);
    return { svg: out, top: z + 1.6, bot: -2.6, ext: Math.max(3, dr + 0.4) };
  };
  // Biodome: a drum of decks on a small planetoid, a glass dome over it, a moonlet going round
  SKIN.dome = function (n, acc, R) {
    var r = fpOf(n) / 2 + 0.5, rr = r * 1.45, z = 0.08, out = '', rc = P(3, 3, -rr * 0.62);
    out += rock(rc, rr * SC * 0.98, R);
    for (var k = 0; k < 5; k++) { var a = 0.4 + k * 0.5; out += '<circle class="beacon" cx="' + f1(rc[0] + Math.cos(a) * rr * SC * 0.7) + '" cy="' + f1(rc[1] + Math.sin(a) * rr * SC * 0.5) + '" r="1.3" fill="' + acc + '" style="animation-delay:-' + k * 0.4 + 's"/>'; }
    out += cyl(3, 3, -0.08, 0.08, r + 0.3, C.line3, C.navy2);
    for (var f = 0; f < n; f++) {
      var h = FH - 0.05;
      out += '<g class="fl" data-f="' + f + '">' + cyl(3, 3, z, z + h, r, HULL.top, HULL.l) + ring(3, 3, z + h / 2, r, acc, R, 0.45, Math.round(r * 5)) + '</g>';
      z += FH;
    }
    var t = P(3, 3, z), rx = r * RX, ry = r * RY, up = r * SC * 0.92;
    out += '<ellipse class="core" cx="' + f1(t[0]) + '" cy="' + f1(t[1] - up * 0.3) + '" rx="' + f1(rx * 0.45) + '" ry="' + f1(up * 0.32) + '" fill="' + acc + '" opacity=".22"/>';
    out += '<path class="glass" d="M' + f1(t[0] - rx) + ',' + f1(t[1]) + ' A' + f1(rx) + ',' + f1(up) + ' 0 0 1 ' + f1(t[0] + rx) + ',' + f1(t[1]) +
      ' A' + f1(rx) + ',' + f1(ry) + ' 0 0 1 ' + f1(t[0] - rx) + ',' + f1(t[1]) + ' Z" fill="' + acc + '" fill-opacity=".09" stroke="' + acc + '" stroke-opacity=".9" stroke-width="1.2"/>';
    [0.4, 0.72].forEach(function (k2) {
      var y = t[1] - up * k2, q = Math.sqrt(1 - k2 * k2);
      out += '<path d="M' + f1(t[0] - rx * q) + ',' + f1(y) + ' A' + f1(rx * q) + ',' + f1(ry * q) + ' 0 0 0 ' + f1(t[0] + rx * q) + ',' + f1(y) + '" fill="none" stroke="' + acc + '" stroke-opacity=".45" stroke-width=".8"/>';
    });
    [-0.62, 0, 0.62].forEach(function (s) {
      var x = t[0] + rx * Math.sin(s), y = t[1] + ry * Math.cos(s);
      out += '<path d="M' + f1(x) + ',' + f1(y) + ' Q' + f1(t[0] + rx * Math.sin(s) * 1.05) + ',' + f1(t[1] - up * 0.95) + ' ' + f1(t[0]) + ',' + f1(t[1] - up) + '" fill="none" stroke="' + acc + '" stroke-opacity=".4" stroke-width=".8"/>';
    });
    out += beacon([t[0], t[1] - up], acc, 2.2);
    var mc = [rc[0] + rr * SC * 1.35, rc[1] - rr * SC * 0.2];
    out += '<g class="orb">' + rock(mc, 7, R) + '</g>';
    return { svg: out, top: z + r * 0.92 + 0.5, bot: -rr * 1.5, ext: Math.max(3, rr * 1.2) };
  };
  // Ziggurat: a tier per deck on a floating island of rock, stones drifting under it, a beam from its temple
  SKIN.pyramid = function (n, acc, R) {
    var b0 = fpOf(n) + 1.0, inset = Math.min(0.3, (b0 - 1.1) / (2 * n)), z = 0, out = '', kh = b0 * 1.05, x0 = 3 - b0 / 2, y0 = 3 - b0 / 2, ap = P(3, 3, -kh);
    out += '<polygon points="' + pts([P(x0, y0 + b0, 0), P(x0 + b0, y0 + b0, 0), ap]) + '" fill="' + ROCK.l + '" stroke="' + C.line2 + '" stroke-width=".6"/>';
    out += '<polygon points="' + pts([P(x0 + b0, y0 + b0, 0), P(x0 + b0, y0, 0), ap]) + '" fill="' + ROCK.r + '" stroke="' + C.line2 + '" stroke-width=".6"/>';
    out += '<polyline points="' + pts([P(x0, y0 + b0, 0), P(x0 + b0, y0 + b0, 0), P(x0 + b0, y0, 0)]) + '" fill="none" stroke="' + acc + '" stroke-width="1.2" opacity=".7"/>';
    out += '<g class="orb">' + rock([ap[0] - 18, ap[1] - 6], 5, R) + rock([ap[0] + 16, ap[1] - 14], 4, R) + '</g>';
    for (var f = 0; f < n; f++) {
      var b = b0 - 2 * inset * f, xx = 3 - b / 2, yy = 3 - b / 2, h = FH - 0.04;
      out += '<g class="fl" data-f="' + f + '">' + box(xx, yy, z, b, b, h, HULL.top, HULL.l, HULL.r, C.line2) +
        '<polyline class="rim" points="' + pts([P(xx, yy + b, z + h), P(xx + b, yy + b, z + h), P(xx + b, yy, z + h)]) + '" fill="none" stroke="' + acc + '" stroke-width="1.1"/>' +
        wins(I.onBack(xx, 0, yy + b, z + h), b * SC, h * SC, acc, R, 0.3, 9) + wins(I.onSide(xx + b, yy, 0, z + h), b * SC, h * SC, acc, R, 0.3, 9) + '</g>';
      z += FH;
    }
    out += box(2.62, 2.62, z, 0.76, 0.76, 0.45, C.line3, C.navy2, C.navy, C.line2);
    var c = P(3, 3, z + 0.45);
    out += '<polygon class="beam" points="' + pts([[c[0] - 6, c[1]], [c[0] + 6, c[1]], [c[0] + 1.5, c[1] - 46], [c[0] - 1.5, c[1] - 46]]) + '" fill="' + acc + '"/>';
    out += beacon(c, acc, 3);
    return { svg: out, top: z + 1.4, bot: -kh - 0.3, ext: Math.max(3, b0 * 0.75) };
  };
  // Ring station: a spindle of disc decks, a great wheel round it on four spokes, an engine below
  SKIN.orbital = function (n, acc, R) {
    var rd = 0.72 + fpOf(n) * 0.14, spineH = 0.4 + n * FH, RR = rd + 1.9, wz = 0.2 + n * FH / 2 - 0.25, wc = P(3, 3, wz), out = '';
    var spoke = function (a) { return line(P(3 + Math.cos(a) * 0.3, 3 + Math.sin(a) * 0.3, wz), P(3 + Math.cos(a) * RR, 3 + Math.sin(a) * RR, wz), C.dim2, 1.3, 0.8); };
    out += arc(wc, RR * RX, RR * RY, false, HULL.top, 6) + arc(wc, (RR + 0.12) * RX, (RR + 0.12) * RY, false, acc, 1.2, 0.9);
    out += spoke(Math.PI * 1.25) + spoke(Math.PI * 1.75);
    out += box(2.8, 2.8, -1.0, 0.4, 0.4, spineH + 1.6, C.line3, C.line2, C.navy, C.line2);
    var bt = P(3, 3, -1.0), bb = P(3, 3, -1.55);
    out += '<polygon points="' + pts([[bt[0] - 5, bt[1]], [bt[0] + 5, bt[1]], [bb[0] + 9, bb[1]], [bb[0] - 9, bb[1]]]) + '" fill="' + HULL.r + '" stroke="' + C.line2 + '" stroke-width=".6"/>';
    out += flame(bb, acc, 14, 24);
    var z = 0.2;
    for (var f = 0; f < n; f++) {
      out += '<g class="fl" data-f="' + f + '">' + cyl(3, 3, z, z + 0.3, rd, HULL.top, HULL.l) + ring(3, 3, z + 0.15, rd, acc, R, 0.5, Math.round(rd * 6)) + '</g>';
      out += arc(P(3, 3, z + 0.3), rd * RX, rd * RY, true, acc, 1, 0.8);
      z += FH;
    }
    out += spoke(Math.PI * 0.25) + spoke(Math.PI * 0.75);
    out += arc(wc, RR * RX, RR * RY, true, HULL.top, 6) + arc(wc, (RR + 0.12) * RX, (RR + 0.12) * RY, true, acc, 1.4, 1, 'wheel');
    out += beacon(P(3, 3, spineH + 0.68), acc);
    return { svg: out, top: spineH + 1.1, bot: -2.7, ext: RR + 0.3 };
  };
  // Starship: a hull section per deck along the map's x, its nose away from us, three engines facing us
  SKIN.rocket = function (n, acc, R) {
    var rr = 0.5 + Math.min(n, 8) * 0.05, L = 1.0, len = n * L, w = rr * 1.7, h = rr * 1.7, cz = 0.4, xs = 3 - len / 2, y0 = 3 - w / 2, out = '';
    var tip = P(xs - rr * 2.2, 3, cz + h / 2);
    out += '<polygon points="' + pts([P(xs, y0, cz + h), P(xs, y0 + w, cz + h), tip]) + '" fill="' + HULL.top + '" stroke="' + C.line2 + '" stroke-width=".6"/>';
    out += '<polygon points="' + pts([P(xs, y0 + w, cz), P(xs, y0 + w, cz + h), tip]) + '" fill="' + HULL.l + '" stroke="' + C.line2 + '" stroke-width=".6"/>';
    for (var f = 0; f < n; f++) {
      var x = xs + f * L;
      out += '<g class="fl" data-f="' + f + '">' + box(x, y0, cz, L - 0.05, w, h, HULL.top, HULL.l, HULL.r, C.line2) +
        wins(I.onBack(x, 0, y0 + w, cz + h), (L - 0.05) * SC, h * SC, acc, R, 0.55, 9) + '</g>';
      out += '<polyline points="' + pts([P(x + L - 0.05, y0 + w, cz), P(x + L - 0.05, y0 + w, cz + h), P(x + L - 0.05, y0, cz + h)]) + '" fill="none" stroke="' + acc + '" stroke-width="1.1" opacity=".85"/>';
    }
    out += line(P(xs + 0.1, 3, cz + h), P(xs + len - 0.1, 3, cz + h), acc, 1.2, 0.8);
    var cp = P(xs + 0.35, 3, cz + h);
    out += '<ellipse cx="' + f1(cp[0]) + '" cy="' + f1(cp[1] - 2) + '" rx="7" ry="3.5" fill="' + acc + '" fill-opacity=".25" stroke="' + acc + '" stroke-width=".8"/>';
    var ex = xs + len, eb = 0.45;
    out += box(ex, y0 - 0.06, cz - 0.06, eb, w + 0.12, h + 0.12, C.line3, C.navy2, C.navy, C.line2);
    var fin = [P(ex - 0.2, 3, cz + h), P(ex + 0.3, 3, cz + h), P(ex + 0.3, 3, cz + h + 0.75), P(ex - 0.05, 3, cz + h + 0.75)];
    out += '<polygon points="' + pts(fin) + '" fill="' + acc + '" fill-opacity=".35" stroke="' + acc + '" stroke-width=".8"/>';
    var dx = I.C30, dy = I.S30;
    [[0.5, 0.72], [0.25, 0.3], [0.75, 0.3]].forEach(function (q) {
      var p = P(ex + eb, y0 + w * q[0], cz + h * q[1]);
      out += '<ellipse cx="' + f1(p[0]) + '" cy="' + f1(p[1]) + '" rx="3" ry="4.2" fill="' + acc + '" class="beacon"/>' + flame(p, acc, 8, 26, dx, dy);
    });
    return { svg: out, top: cz + h + 1.0, bot: cz - 0.7, ext: Math.max(3, len / 2 + rr * 2.4 + 1.2) };
  };
  // Vault: an armoured block of decks with its round door, two solar wings, a dish, an engine pod underneath
  SKIN.vault = function (n, acc, R) {
    var fp = fpOf(n), w = fp + 0.7, dd = Math.max(1.9, fp * 0.82), x0 = 3 - w / 2, y0 = 3 - dd / 2, z = 0, out = '', H = 0;
    for (var q = 0; q < n; q++) H += (q === 0 ? FH * 1.35 : FH);
    var wz = Math.min(H * 0.5, 1.6);
    var wing = function (s) {
      var px0 = s > 0 ? x0 + w + 1.1 : x0 - 1.1 - 3.2, px1 = px0 + 3.2, py0 = 3 - 0.85, py1 = 3 + 0.85, g = '';
      g += line(P(s > 0 ? x0 + w : x0, 3, wz), P(s > 0 ? px0 : px1, 3, wz), C.dim2, 1.6);
      g += '<polygon points="' + pts([P(px0, py0, wz), P(px1, py0, wz), P(px1, py1, wz), P(px0, py1, wz)]) + '" fill="#0e1824" stroke="' + acc + '" stroke-width="1" stroke-opacity=".85"/>';
      for (var k = 1; k < 4; k++) g += line(P(px0, py0 + k * 0.425, wz), P(px1, py0 + k * 0.425, wz), acc, 0.6, 0.35);
      for (k = 1; k < 8; k++) g += line(P(px0 + k * 0.4, py0, wz), P(px0 + k * 0.4, py1, wz), acc, 0.6, 0.35);
      return g;
    };
    out += box(3 - w * 0.23, 3 - dd * 0.23, -0.42, w * 0.46, dd * 0.46, 0.42, C.line3, C.navy2, C.navy, C.line2);
    out += flame(P(3, 3, -0.42), acc, 12, 24);
    out += wing(-1);
    for (var f = 0; f < n; f++) {
      var h = (f === 0 ? FH * 1.35 : FH) - 0.05, g = '<g class="fl" data-f="' + f + '">' + box(x0, y0, z, w, dd, h, HULL.top, HULL.l, HULL.r, C.line2);
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
      out += line(P(x0 + w, y0 + dd, z), P(x0 + w, y0 + dd, z + h), C.line3, 2.4);
      z += h + 0.05;
    }
    out += box(x0 + 0.4, y0 + 0.35, z, 0.5, 0.5, 0.3, C.line3, C.navy2, C.navy, C.line2) + box(x0 + 1.1, y0 + 0.35, z, 0.5, 0.5, 0.3, C.line3, C.navy2, C.navy, C.line2);
    var dc = P(x0 + w - 0.8, y0 + dd - 0.7, z + 0.35);
    out += line(P(x0 + w - 0.8, y0 + dd - 0.7, z), dc, C.dim2, 1.2);
    out += '<ellipse cx="' + f1(dc[0]) + '" cy="' + f1(dc[1] - 3) + '" rx="9" ry="4.2" fill="' + C.line3 + '" stroke="' + acc + '" stroke-opacity=".7" transform="rotate(-20 ' + f1(dc[0]) + ' ' + f1(dc[1] - 3) + ')"/>';
    out += beacon([dc[0] + 6, dc[1] - 9], acc, 1.8);
    out += wing(1);
    return { svg: out, top: z + 1.1, bot: -1.6, ext: w / 2 + 4.4 };
  };

  /* ---------------- a station, a banner, a whole picture ---------------- */
  // the holo-ring a station floats over: solid when public, dashed when private
  function holo(acc, priv, rr, zb) {
    var c = P(3, 3, zb), rx = rr * RX, ry = rr * RY;
    return '<ellipse cx="' + f1(c[0]) + '" cy="' + f1(c[1]) + '" rx="' + f1(rx * 1.18) + '" ry="' + f1(ry * 1.18) + '" fill="' + acc + '" opacity=".07"/>' +
      '<ellipse class="rim' + (priv ? ' fence' : '') + '" cx="' + f1(c[0]) + '" cy="' + f1(c[1]) + '" rx="' + f1(rx) + '" ry="' + f1(ry) + '" fill="none" stroke="' + acc + '" stroke-width="1.4"/>';
  }
  // the station alone, with or without its ring, in the station's own coordinates (its middle at 3,3)
  CO.skinArt = function (o) {
    var acc = CO.accentHex(o.accent), n = Math.max(1, Math.min(8, o.floors || 1));
    var b = (SKIN[o.skin] || SKIN.tower)(n, acc, rng(o.seed || 7)), rr = Math.max(2.0, Math.min(b.ext, 4.5) * 0.72), zb = b.bot - 0.4;
    return { svg: (o.plot === false ? '' : holo(o.you ? C.green : acc, o.priv, rr, zb)) + b.svg, top: b.top, bot: zb, ext: b.ext, acc: acc };
  };
  var LOCK = function (x, y, col) {
    return '<g class="lock" transform="translate(' + f1(x) + ' ' + f1(y) + ')"><path d="M-3,-1 v-2.6 a3,3 0 0 1 6,0 v2.6" fill="none" stroke="' + col + '" stroke-width="1.3"/>' +
      '<rect x="-4.2" y="-1.2" width="8.4" height="6.4" rx="1.2" fill="' + col + '"/></g>';
  };
  // the name on a banner over the station: a ribbon on a tether, a lock when private, YOU over your own
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
  // a whole picture: ring, station and (optionally) the banner, in an <svg> sized to fit them
  CO.skinSVG = function (o) {
    var a = CO.skinArt(o), e = Math.max(3, a.ext), top = P(3, 3, a.top)[1], bn = o.banner != null;
    var x0 = P(3 - e, 3 + e, 0)[0] - 8, x1 = P(3 + e, 3 - e, 0)[0] + 8;
    var y0 = Math.min(P(3 - e, 3 - e, 0)[1], top) - (bn ? 58 + (o.you ? 14 : 0) : 10), y1 = P(3 + e * 0.7, 3 + e * 0.7, a.bot)[1] + 8;
    var w = x1 - x0, h = y1 - y0;
    return '<svg class="skinsvg" viewBox="' + f1(x0) + ' ' + f1(y0) + ' ' + f1(w) + ' ' + f1(h) + '" preserveAspectRatio="xMidYMax meet" xmlns="http://www.w3.org/2000/svg">' +
      '<g class="plot' + (o.priv ? ' priv' : '') + '">' + a.svg + '</g>' +
      (bn ? banner(P(3, 3, a.top)[0], top, o.banner, a.acc, { lock: o.priv, you: o.you, fs: o.fs }) : '') + '</svg>';
  };

  /* ---------------- the flat map: the galaxy seen from above its disc ---------------- */
  var DEFS = '<defs>' + ['cc:0,207,255', 'cg:0,255,136', 'cb:59,130,246'].map(function (s) {
    var k = s.split(':');
    return '<radialGradient id="uv-' + k[0] + '"><stop offset="0" stop-color="rgb(' + k[1] + ')" stop-opacity=".3"/><stop offset=".5" stop-color="rgb(' + k[1] + ')" stop-opacity=".1"/><stop offset="1" stop-color="rgb(' + k[1] + ')" stop-opacity="0"/></radialGradient>';
  }).join('') +
    '<radialGradient id="uv-core"><stop offset="0" stop-color="#ffffff"/><stop offset=".08" stop-color="#d8f7ff" stop-opacity=".95"/><stop offset=".3" stop-color="#00cfff" stop-opacity=".35"/>' +
    '<stop offset=".65" stop-color="#00cfff" stop-opacity=".08"/><stop offset="1" stop-color="#00ff88" stop-opacity="0"/></radialGradient></defs>';
  function Universe(svg, stage, h) {
    this.svg = svg; this.stage = stage; this.h = h || {};
    svg.innerHTML = DEFS + '<g class="uw"><g class="space"></g><g class="plots"></g><g class="fx"></g></g>';
    this.gSpace = svg.querySelector('.space'); this.gPlots = svg.querySelector('.plots'); this.gFx = svg.querySelector('.fx');
    this.tip = stage.querySelector('.tip'); this.stars = stage.querySelector('.stars'); this.bans = stage.querySelector('.uvbans');
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
    this.drawSpace();
    this.draw();
  };
  // the arms' clouds and stars, the lanes and their shuttles, and Cymetica in the middle
  Universe.prototype.drawSpace = function () {
    var Gx = CO.uvGalaxy, R = rng(9), gauss = function () { return R() + R() + R() + R() - 2; }, out = '', i, r, th, p, m;
    for (i = 0; i < 46; i++) {
      r = 18 + Math.pow(R(), 0.8) * Gx.R1; th = Gx.angle(i % ARMS, r) + gauss() * 0.12; p = gp(Math.cos(th) * r, 0, Math.sin(th) * r); m = R();
      var s = (22 + R() * 34) * SC;
      out += '<ellipse cx="' + f1(p[0]) + '" cy="' + f1(p[1]) + '" rx="' + f1(s * 1.2) + '" ry="' + f1(s * 0.6) + '" fill="url(#uv-' + (m < 0.5 ? 'cc' : m < 0.8 ? 'cg' : 'cb') + ')"/>';
    }
    var cols = ['#00cfff', '#00ff88', '#3b82f6', '#d8f7ff'];
    for (i = 0; i < 2200; i++) {
      r = 12 + Math.pow(R(), 0.9) * Gx.R1 * 1.1; th = Gx.angle(i % ARMS, r) + gauss() * (0.12 + r / Gx.R1 * 0.12); p = gp(Math.cos(th) * r, 0, Math.sin(th) * r); m = R();
      out += '<circle cx="' + f1(p[0]) + '" cy="' + f1(p[1]) + '" r="' + (m > 0.93 ? 9 : 4.5) + '" fill="' + cols[m < 0.45 ? 0 : m < 0.72 ? 1 : m < 0.86 ? 2 : 3] + '" opacity="' + (0.25 + R() * 0.55).toFixed(2) + '"/>';
    }
    var c = gp(0, 0, 0);
    [[22, C.cyan], [56, C.green], [96, C.cyan], [140, C.blue], [184, C.green]].forEach(function (L, k) {
      var rx = L[0] * RX, ry = L[0] * RY, path = 'M' + f1(c[0] - rx) + ',' + f1(c[1]) + ' a' + f1(rx) + ',' + f1(ry) + ' 0 1 0 ' + f1(rx * 2) + ',0 a' + f1(rx) + ',' + f1(ry) + ' 0 1 0 ' + f1(-rx * 2) + ',0';
      out += '<path class="lane" d="' + path + '" stroke="' + L[1] + '"/>';
      for (var j = 0; j < 3; j++) out += '<circle class="ship" r="16" fill="' + L[1] + '"><animateMotion dur="' + (40 + L[0] * 0.9).toFixed(0) + 's" begin="-' + (j * (40 + L[0] * 0.9) / 3).toFixed(1) + 's" repeatCount="indefinite"' + (k % 2 ? ' keyPoints="1;0" keyTimes="0;1"' : '') + ' path="' + path + '"/></circle>';
    });
    out += this.core();
    this.gSpace.innerHTML = out;
  };
  // the middle of the map: Cymetica, the star every company works on
  Universe.prototype.core = function () {
    var c = gp(0, 0, 0), out = '<g class="core-plot" data-id="core">';
    out += '<circle cx="' + f1(c[0]) + '" cy="' + f1(c[1]) + '" r="' + f1(70 * SC) + '" fill="url(#uv-core)"/>';
    [[6, C.cyan], [8.2, C.green], [10.6, C.cyan]].forEach(function (q, i) {
      out += '<ellipse class="cring' + (i === 1 ? ' spin' : '') + '" cx="' + f1(c[0]) + '" cy="' + f1(c[1]) + '" rx="' + f1(q[0] * RX) + '" ry="' + f1(q[0] * RY) + '" fill="none" stroke="' + q[1] + '"/>';
    });
    out += '<circle class="corb" cx="' + f1(c[0]) + '" cy="' + f1(c[1]) + '" r="' + f1(2.4 * SC) + '" fill="#e8fbff"/>';
    out += '<circle cx="' + f1(c[0]) + '" cy="' + f1(c[1]) + '" r="' + f1(9 * SC) + '" fill="transparent"/>';
    return out + '</g>';
  };
  // every station, back to front; the names are the same HTML banners as the 3D map's
  Universe.prototype.draw = function () {
    var self = this, plots = '';
    var order = this.items.slice().sort(function (p, q) { return gp(p.pos[0], p.pos[1], p.pos[2])[1] - gp(q.pos[0], q.pos[1], q.pos[2])[1]; });
    order.forEach(function (it) { plots += self.plotSVG(it); });
    this.gPlots.innerHTML = plots;
    this.items.forEach(function (it) { self.paintFloors(it); self.banner(it); });
    this.coreBanner();
    this.stats();
  };
  Universe.prototype.plotSVG = function (it) {
    var c = it.c, n = floorsOf(c), priv = !c.public && !it.mine, paused = c.status === 'paused';
    var a = CO.skinArt({ skin: c.skin, accent: c.accent, floors: n, seed: it.mine ? 7 : c.id, priv: priv, you: it.mine });
    var o = gp(it.pos[0], it.pos[1], it.pos[2]), base = P(3, 3, 0), tx = o[0] - base[0], ty = o[1] - base[1], e = Math.min(a.ext, 4.5);
    var hit = '<polygon class="hit" fill="transparent" points="' + pts([P(3 - e, 3 + e, a.bot), P(3 - e, 3 + e, a.top), P(3 - e, 3 - e, a.top), P(3 + e, 3 - e, a.top), P(3 + e, 3 - e, a.bot), P(3 + e, 3 + e, a.bot)]) + '"/>';
    var mine = it.mine ? '<ellipse class="mering" cx="' + f1(P(3, 3, a.bot)[0]) + '" cy="' + f1(P(3, 3, a.bot)[1]) + '" rx="' + f1(3.4 * RX) + '" ry="' + f1(3.4 * RY) + '" fill="none" stroke="' + C.green + '"/>' : '';
    var top = P(3, 3, a.top);
    it.anchor = [tx + top[0], ty + top[1]]; it.size = (a.top - a.bot) * SC;
    return '<g class="plot' + (priv ? ' priv' : '') + (paused ? ' paused' : '') + (it.mine ? ' mine' : '') + '" data-id="' + c.id + '" transform="translate(' + f1(tx) + ' ' + f1(ty) + ')">' + mine + a.svg + hit + '</g>';
  };
  Universe.prototype.banner = function (it) {
    var c = it.c, self = this;
    if (!it.el) {
      it.el = document.createElement('div'); this.bans.appendChild(it.el);
      it.el.addEventListener('pointerenter', function () { self.setHover(c.id); });
      it.el.addEventListener('pointerleave', function () { self.setHover(null); });
      it.el.addEventListener('click', function () { self.open(it.c.id); });
    }
    var name = String(c.name || '').toUpperCase(); if (name.length > 22) name = name.slice(0, 21) + '…';
    it.el.className = 'b3' + (!c.public && !it.mine ? ' priv' : '') + (c.status === 'paused' ? ' paused' : '') + (it.mine ? ' mine' : '');
    it.el.style.setProperty('--acc', CO.accentHex(c.accent));
    it.el.innerHTML = (it.mine ? '<span class="you">YOU</span>' : '') + '<span class="rib">' + (!c.public && !it.mine ? '<i class="lk"></i>' : '') + esc(name) + '</span><span class="teth"></span>';
    it.el._bw = 0;
  };
  Universe.prototype.coreBanner = function () {
    if (this.coreEl) return;
    var el = document.createElement('div'), self = this; el.className = 'b3 core'; el.style.setProperty('--acc', '#00cfff');
    el.innerHTML = '<span class="rib">CYMETICA</span><span class="teth"></span>';
    el.addEventListener('pointerenter', function () { self.setHover('core'); }); el.addEventListener('pointerleave', function () { self.setHover(null); });
    this.bans.appendChild(el); this.coreEl = el;
  };
  // the banners over their stations, the way the 3D map places them: ours, Cymetica and the hovered always, the
  // rest only where nothing stands, only while the station is big enough to be worth a name, at most 14
  Universe.prototype.labels = function () {
    if (!this.items) return;
    var c = this.client(), v = this.vb, k = c.w / v.w, self = this, placed = [], named = 0, cp = gp(0, 0, 0);
    var list = this.items.map(function (it) { return { el: it.el, x: (it.anchor[0] - v.x) * k, y: (it.anchor[1] - v.y) * k, px: it.size * k, mine: it.mine, keep: it.mine || String(self.hover) === String(it.c.id), d: -it.anchor[1] }; });
    if (this.coreEl) list.push({ el: this.coreEl, x: (cp[0] - v.x) * k, y: (cp[1] - 12.5 * SC - v.y) * k, px: 200, keep: true, core: true, d: 0 });
    list.sort(function (a, b) { return (b.keep - a.keep) || a.d - b.d; });
    list.forEach(function (o) {
      var el = o.el; if (!el) return;
      if (!el._bw) el._bw = el.offsetWidth || 160;
      var s = o.core ? 1 : Math.max(0.66, Math.min(1, 0.5 + o.px / 120));
      var off = o.x < -80 || o.x > c.w + 80 || o.y < -40 || o.y > c.h + 60;
      var bw = el._bw * s, bh = (o.mine ? 48 : o.core ? 42 : 30) * s, r = { l: o.x - bw / 2, r: o.x + bw / 2, t: o.y - bh, b: o.y };
      var clash = placed.some(function (p) { return r.l < p.r + 6 && r.r > p.l - 6 && r.t < p.b + 4 && r.b > p.t - 4; });
      var show = !off && (o.keep || (!clash && o.px >= 24 && named < 14));
      if (show && !o.keep) named++;
      el.classList.toggle('hidden', !show);
      if (show) placed.push(r);
      el.style.transform = 'translate(' + o.x.toFixed(1) + 'px,' + o.y.toFixed(1) + 'px) translate(-50%,-100%) scale(' + s.toFixed(3) + ')';
      el.style.zIndex = String(o.keep ? 3000 : 2000 + Math.round(o.y));
    });
  };
  // the decks at work light up: a department working is its deck lit
  Universe.prototype.paintFloors = function (it) {
    var g = this.gPlots.querySelector('.plot[data-id="' + it.c.id + '"]'); if (!g) return;
    var on = it.mine ? (it.c.working || []) : (this.live[it.c.id] || []);
    Array.prototype.forEach.call(g.querySelectorAll('.fl'), function (f) { f.classList.toggle('on', on.indexOf(+f.getAttribute('data-f')) >= 0); });
    g.classList.toggle('busy', on.length > 0);
  };
  // the others' days go on: a deck starts, a deck stops, now and then Cymetica pays a bug
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
  // your own company: its station follows Settings, its decks follow your departments, its ET10 pops
  Universe.prototype.setMine = function (m) {
    if (!this.items) return;
    var it = this.items.filter(function (x) { return x.mine; })[0]; if (!it) return;
    var key = [m.name, m.skin, m.accent, m.public, m.status, floorsOf(m)].join('|');
    var gain = it.c.et10 != null && m.et10 > it.c.et10 ? m.et10 - it.c.et10 : 0;
    it.c = m;
    if (key !== this.mineKey) {
      this.mineKey = key;
      var old = this.gPlots.querySelector('.plot.mine'), t = document.createElementNS('http://www.w3.org/2000/svg', 'g');
      t.innerHTML = this.plotSVG(it);
      if (old) old.replaceWith(t.firstChild);
      this.banner(it); this.labels();
    }
    this.paintFloors(it);
    if (gain) this.pop(it, '+' + gain.toLocaleString('en-US') + ' ET10');
    this.stats();
  };
  Universe.prototype.stats = function () {
    if (this.h.onStats) this.h.onStats(CO.uvStats(this.items || [], this.live));
  };
  Universe.prototype.open = function (id) { var it = this.find(id); if (it && this.h.onOpen) { this.hideTip(); this.h.onOpen(it); } };

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
    for (var i = 0; i < 320; i++) far.push(Math.round(R() * 3200 - 400) + 'px ' + Math.round(R() * 1800 - 300) + 'px 0 ' + (R() < 0.15 ? '1px' : '0') + ' rgba(225,235,245,' + (0.2 + R() * 0.5).toFixed(2) + ')');
    for (i = 0; i < 60; i++) near.push(Math.round(R() * 3200 - 400) + 'px ' + Math.round(R() * 1800 - 300) + 'px 0 1px ' + (R() < 0.4 ? 'rgba(0,207,255,.7)' : R() < 0.3 ? 'rgba(0,255,136,.6)' : 'rgba(230,237,247,.8)'));
    this.stars.innerHTML = '<i class="far" style="box-shadow:' + far.join(',') + '"></i><i class="near" style="box-shadow:' + near.join(',') + '"></i>';
  };
  Universe.prototype.apply = function () {
    var v = this.vb;
    this.svg.setAttribute('viewBox', f1(v.x) + ' ' + f1(v.y) + ' ' + f1(v.w) + ' ' + f1(v.h));
    if (this.stars) this.stars.style.transform = 'translate(' + f1(-v.x * 0.01) + 'px,' + f1(-v.y * 0.01) + 'px)';
    this.labels();
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
  // the whole galaxy: every station and the outermost lane
  Universe.prototype.bounds = function () {
    var e = (CO.uvGalaxy.outer || R1) + 14, l = gp(-e, 0, e), r = gp(e, 0, -e), t = gp(-e, 0, -e), b = gp(e, 0, e);
    var x = l[0], x2 = r[0], y = t[1] - 60, y2 = b[1];
    var bb = this.gPlots.getBBox && this.gPlots.getBBox();
    if (bb && bb.width) { x = Math.min(x, bb.x); y = Math.min(y, bb.y); x2 = Math.max(x2, bb.x + bb.width); y2 = Math.max(y2, bb.y + bb.height); }
    return { x: x, y: y, w: x2 - x, h: y2 - y };
  };
  Universe.prototype.fit = function (anim) {
    var b = this.bounds(), c = this.client(), top = 40, availH = Math.max(80, c.h - top);
    var k = Math.min(c.w / b.w, availH / b.h), w = c.w / k, h = c.h / k;
    var x = b.x + b.w / 2 - w / 2, y = b.y - top / k - (availH / k - b.h) / 2;
    this.fitted = true;
    this.tween({ x: x, y: y, w: w, h: h }, anim === false ? 0 : 600);
  };
  Universe.prototype.zoom = function (f, cx, cy) {
    var c = this.client(), v = this.vb;
    var px = cx == null ? 0.5 : (cx - c.l) / c.w, py = cy == null ? 0.5 : (cy - c.t) / c.h;
    var b = this.bounds(), nw = Math.max(320, Math.min(b.w * 1.8, v.w * f)), k = nw / v.w, nh = v.h * k;
    var to = { x: v.x + (v.w - nw) * px, y: v.y + (v.h - nh) * py, w: nw, h: nh };
    if (cx == null) this.tween(to, 260); else { this.tw = 0; this.vb = to; this.apply(); }
  };
  // bring one company to the middle, close up
  Universe.prototype.flyTo = function (id, done, ms) {
    var it = this.find(id); if (!it || !it.anchor) { if (done) done(); return; }
    var c = this.client(), w = 900, h = w * c.h / c.w, m = [it.anchor[0], it.anchor[1] + it.size * 0.55];
    this.tween({ x: m[0] - w / 2, y: m[1] - h / 2, w: w, h: h }, ms || 750, done);
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
      self.open(id);
    });
    svg.addEventListener('wheel', function (e) { e.preventDefault(); self.zoom(Math.pow(1.0018, e.deltaY), e.clientX, e.clientY); }, { passive: false });
    svg.addEventListener('pointerleave', function () { self.hideTip(); self.setHover(null); });
  };
  Universe.prototype.setHover = function (id) {
    if (this.hover === id) return;
    var self = this;
    [this.gPlots, this.gSpace].forEach(function (g) {
      Array.prototype.forEach.call(g.querySelectorAll('.hov'), function (x) { x.classList.remove('hov'); });
      if (id != null) Array.prototype.forEach.call(g.querySelectorAll('[data-id="' + id + '"]'), function (x) { x.classList.add('hov'); });
    });
    (this.items || []).forEach(function (it) { if (it.el) it.el.classList.toggle('hov', String(it.c.id) === String(id)); });
    if (this.coreEl) this.coreEl.classList.toggle('hov', id === 'core');
    self.hover = id;
    this.labels();
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
