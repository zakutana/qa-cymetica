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
  // The orrery, to the operator's picture: Cymetica in the middle, every company a station on one of seven
  // orbits round it, the biggest on the inner ones, ours on the second, in front of it where the camera first
  // looks. An orbit turns at its own pace, the inner ones faster as orbits do (omega ~ r^-1.5): slowly, so the
  // picture is alive and a name can still be read. One copy of the model, so the two pictures cannot drift apart;
  // the flat map draws it at its first moment. Units are the stations' own (a deck is 0.8 high).
  var ORBITS = [68, 90, 112, 134, 156, 180, 204], AZ = 1.08, SPIN = 2.2, R1 = ORBITS[ORBITS.length - 1];
  CO.uvRng = rng; CO.fpOf = fpOf;
  CO.uvGalaxy = { ORBITS: ORBITS, AZ: AZ, R1: R1, outer: R1, omega: function (r) { return SPIN / Math.pow(r, 1.5); } };
  CO.uvPlan = function (mine) {
    var list = CO.UNIVERSE.slice().sort(function (a, b) { return floorsOf(b) - floorsOf(a) || a.id - b.id; });
    var R = rng(2026), items = [], n = list.length + 1, tot = 0, k = 0;
    ORBITS.forEach(function (r) { tot += r; });
    // stations per orbit in proportion to its length, so they stand about as far apart on every one
    var counts = ORBITS.map(function (r) { return Math.max(1, Math.round(r / tot * n)); }), d = n - counts.reduce(function (a, b) { return a + b; }, 0);
    for (var i = counts.length - 1; d !== 0; i = (i + counts.length - 1) % counts.length) { if (d > 0) { counts[i]++; d--; } else if (counts[i] > 1) { counts[i]--; d++; } }
    ORBITS.forEach(function (r, o) {
      var m = counts[o], a0 = o === 1 ? AZ + 0.55 : R() * Math.PI * 2;
      for (var j = 0; j < m; j++) {
        var me = o === 1 && j === 0, c = me ? mine : list[k++]; if (!c) return;
        var a = a0 + (j + (me ? 0 : (R() - 0.5) * 0.4)) / m * Math.PI * 2;
        items.push({ c: c, mine: me, orbit: { r: r, a: a, w: CO.uvGalaxy.omega(r) }, pos: [Math.sin(a) * r, 0, Math.cos(a) * r] });
      }
    });
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
  // Fortress (the key stays 'pyramid'), as u3d.js builds it after the Bull Club in the operator's orrery: crenellated
  // walls in the company's colour round a tiled courtyard, a tower at each corner, grey blocks inside, all on a dark
  // plinth; an engine burning blue out of two sides, a solar wing out of the other two. Its decks: the keep, the
  // walls, a second block, then the towers rise one by one (the back one highest), the keep gains a storey, the front
  // tower last. One deck is his small Bull Club: a block with a lamp on a mast.
  SKIN.pyramid = function (n, acc, R) {
    var V = vfCols(acc); VB = [0, 66, 0, 66, 66];
    if (n === 1) return vfBlock(V, acc, R);
    var s = fpOf(n) + 1.3, hs = s / 2, t = 0.36, Hw = 1.05, tw = 1.0, fy = 0.26, len = s - 2 * tw + 0.1, tc = hs - tw / 2 + 0.05, out = '';
    // a wall between two towers on side (ax, ay): on a near one its outer face's arrow slits (deck 1) and pilasters,
    // then its merlons along the outer edge, back to front
    function wall(ax, ay) {
      var c = hs - t / 2, o = cc(ax ? 3 + ax * c : 3, ay ? 3 + ay * c : 3, fy, ax ? t : len, ax ? len : t, Hw - fy, V.body);
      var at = function (u, v) { return ax ? [3 + ax * v, 3 + u] : [3 + u, 3 + ay * v]; }, q = Math.max(2, Math.round(len / 0.75)), sq = len / q, i, p;
      if (ax + ay > 0) {
        var g = '', zc = fy + (Hw - fy) * 0.55;
        for (i = 0; i < q; i++) { p = at(-len / 2 + sq * (i + 0.5), hs + 0.012); g += vfWin(ax ? onX(p[0], p[1] - 0.035, p[1] + 0.035, zc - 0.15, zc + 0.15) : onY(p[1], p[0] - 0.035, p[0] + 0.035, zc - 0.15, zc + 0.15), V, R() < 0.25); }
        o += '<g class="fl" data-f="1">' + g + '</g>';
        for (i = 1; i < q; i++) { p = at(-len / 2 + sq * i, hs + 0.03); o += cc(p[0], p[1], fy, ax ? 0.06 : 0.15, ax ? 0.15 : 0.06, Hw - fy - 0.1, V.body); }
      }
      var mm = Math.max(2, Math.round(len / 0.24)), st = len / mm;
      for (i = 0; i < mm; i++) { p = at(-len / 2 + st * (i + 0.5), hs - 0.06); o += cc(p[0], p[1], Hw, ax ? 0.11 : st * 0.48, ax ? st * 0.48 : 0.11, 0.1, V.body); }
      return o;
    }
    // a tower at corner (sx, sy), risen when its own deck comes: slits in the outer faces we see (the back one's are
    // turned away, so its deck's slits go in the two faces it shows, high enough to clear the blocks in front), a
    // parapet with two merlons a side round a sunken roof
    function tower(sx, sy, f, up) {
      var own = f < n, back = sx < 0 && sy < 0, H = Hw + 0.16 + (own ? up : 0), x = 3 + sx * tc, y = 3 + sy * tc, g = '', e = tw / 2 - 0.05;
      var wy = own ? (back ? H - 0.3 : Hw + 0.14) : H - 0.5;
      var o = cc(x, y, 0, tw, tw, H, V.body);
      [-0.2, 0.2].forEach(function (u) {
        if (sx > 0 || back) g += vfWin(onX(x + tw / 2 + 0.012, y + u * tw - 0.035, y + u * tw + 0.035, wy - 0.14, wy + 0.14), V, R() < 0.3);
        if (sy > 0 || back) g += vfWin(onY(y + tw / 2 + 0.012, x + u * tw - 0.035, x + u * tw + 0.035, wy - 0.14, wy + 0.14), V, R() < 0.3);
      });
      if (g) o += '<g class="fl" data-f="' + (own ? f : 1) + '">' + g + '</g>';
      o += pg(flat(x, y, H + 0.055, tw - 0.2, tw - 0.2), V.floor);
      [[-1, 0], [0, -1], [1, 0], [0, 1]].forEach(function (a) {
        o += cc(x + a[0] * e, y + a[1] * e, H, a[0] ? 0.1 : tw, a[0] ? tw : 0.1, 0.2, V.body);
        [-0.24, 0.24].forEach(function (u) { o += cc(a[0] ? x + a[0] * e : x + u * tw, a[1] ? y + a[1] * e : y + u * tw, H + 0.2, a[0] ? 0.1 : 0.14, a[0] ? 0.14 : 0.1, 0.13, V.body); });
      });
      return o;
    }
    // behind it: the far wing and the far engine
    out += vfWing(3 - hs - 0.15, 3 + s * 0.1, -0.3, -1, 0, 0.35, s * 0.3, s * 0.55, 0.32);
    out += vfJet(3 + s * 0.2, 3 - hs - 0.1, -0.25, 0, -1, s * 0.085, 2.8, 0.06);
    // the plinth, the walls' foot, the courtyard's tiles
    out += cc(3, 3, -0.87, s * 0.7, s * 0.7, 0.3, VFX.base) + rbox(3, 3, -0.6, 0, s + 0.3, s + 0.3, 0.1, VFX.base);
    out += cc(3, 3, 0, s + 0.1, s + 0.1, fy, V.body2) + vfTiles(fy + 0.045, 2 * (hs - t) + 0.02, V);
    // the back tower, the back walls, the side towers; inside, the keep (deck 0, a storey more at deck 6) and a
    // smaller block (deck 2), grey; then the near walls and the front tower
    out += tower(-1, -1, 3, 0.6) + wall(-1, 0) + wall(0, -1) + tower(-1, 1, 4, 0.32) + tower(1, -1, 5, 0.32);
    var kw = Math.min(1.45, s * 0.28), kh = Hw * 1.3;
    out += vfHouse(3 - s * 0.19, 3 + s * 0.05, fy + 0.05, kw, kh, 0, V, R);
    if (n > 6) out += vfHouse(3 - s * 0.19, 3 + s * 0.05, fy + 0.05 + kh, kw * 0.78, kh * 0.62, 6, V, R);
    if (n > 2) out += vfHouse(3 + s * 0.14, 3 - s * 0.17, fy + 0.05, kw * 0.8, Hw * 0.85, 2, V, R);
    out += wall(1, 0) + wall(0, 1) + tower(1, 1, 7, 0.32);
    // in front: the near wing and the near engine
    out += vfWing(3 + hs + 0.15, 3 - s * 0.1, -0.3, 1, 0, 0.35, s * 0.3, s * 0.55, 0.32);
    out += vfJet(3 + s * 0.2, 3 + hs + 0.1, -0.25, 0, 1, s * 0.085, 2.8, 0.06);
    return vfDone(out, Math.max(Hw + 0.16 + (n > 3 ? 0.6 : 0), n > 6 ? fy + 0.05 + kh * 1.62 + 0.18 : 0) + 0.6, -1.0);
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
  // Vault, as u3d.js builds it after the Giga Fund in the operator's orrery: a block in the company's colour narrowing
  // upward, a band of plates per deck whose seams are its windows, in a thick rounded collar; a round door in the
  // first deck, a pale lid with a lamp on a mast, a long solar wing out of two sides, an engine pod under the collar
  SKIN.vault = function (n, acc, R) {
    var V = vfCols(acc), W = fpOf(n) * 0.8 + 0.3, h0 = 0.95, hk = n <= 3 ? 0.62 : 0.52, cw = W * 1.45, k = 0.1, m = W < 2.4 ? 3 : 4;
    var H = h0 + (n - 1) * hk, y0 = 0.12, zt = y0 + H, at = function (z) { return W * (1 - k * (z - y0) / H); }, out = '', f, i, F;
    VB = [0, 66, 0, 66, 66];
    // a point on the block's left face (F 0, its +y) or right face (F 1, its +x), t across it from our left
    var fp = function (F, t, z) { var a = at(z) / 2; return F ? [3 + a, 3 + a - 2 * a * t, z] : [3 - a + 2 * a * t, 3 + a, z]; };
    var fq = function (F, t0, t1, z0, z1) { return [fp(F, t0, z0), fp(F, t1, z0), fp(F, t1, z1), fp(F, t0, z1)]; };
    // behind it the far wing; under it the keel and the drum; round it the collar
    out += vfWing(3, 3 - cw / 2, -0.06, 0, -1, 0.4, W * 1.25, W * 0.66, 0.1);
    out += cc(3, 3, -1.2, W * 0.5, W * 0.5, 0.32, VFX.base) + cc(3, 3, -0.9, W * 0.96, W * 0.96, 0.6, V.body2);
    out += rbox(3, 3, -0.47, 0.19, cw, cw, 0.31, V.body);
    // the block, its plates lit down their left edge and shaded down their right, the seams between them dark, a
    // dark line round it between two decks
    out += loft(3, 3, [[y0, W, W, 0.12], [zt, at(zt), at(zt), 0.12 * (1 - k)]], V.body);
    for (F = 0; F < 2; F++) for (i = 0; i <= m; i++) {
      var t0 = i / (m + 1), t1 = (i + 1) / (m + 1), e = 0.15 / (m + 1);
      out += pg(fq(F, Math.max(0.03, t1 - e), Math.min(0.97, t1), y0, zt), '#000', ' opacity=".16"') + pg(fq(F, Math.max(0.03, t0), t0 + e, y0, zt), '#fff', ' opacity=".07"');
      if (i) out += pg(fq(F, t0 - 0.02, t0 + 0.02, y0, zt), VFX.seam);
    }
    var z = y0, fl = '';
    for (f = 0; f < n; f++) {
      var h = f ? hk : h0, zc = z + h / 2, wc = at(zc), g = '';
      if (f) out += '<polyline points="' + pts([Q.apply(null, fp(0, 0.03, z)), Q.apply(null, fp(0, 1, z)), Q.apply(null, fp(1, 0.97, z))]) + '" fill="none" stroke="' + VFX.seam + '" stroke-width="1.1"/>';
      for (F = 0; F < 2; F++) for (i = 1; i <= m; i++) {
        if (!f && !F && Math.abs(-wc / 2 + wc * i / (m + 1) + W * 0.18) < 0.45) continue;   // where the door is
        var tt = i / (m + 1), dt = 0.05 / wc;
        g += vfWin(fq(F, tt - dt, tt + dt, zc - h * 0.35, zc + h * 0.35), V, R() < 0.15);
      }
      fl += '<g class="fl" data-f="' + f + '">' + g + '</g>';
      z += h;
    }
    out += fl;
    // the round door in the first deck, a wheel on it, a lamp beside
    var dz = y0 + h0 * 0.48;
    out += '<g transform="' + I.onBack(3 - W * 0.18, 0, 3 + at(dz) / 2 + 0.02, dz) + '"><circle r="' + f1(0.31 * SC) + '" fill="' + VFX.dark.l + '" stroke="' + V.cap.top + '" stroke-width="1.6"/>' +
      '<path d="M-4.4,-4.4 L4.4,4.4 M-4.4,4.4 L4.4,-4.4" stroke="' + VFX.silver.l + '" stroke-width="1"/><circle cx="' + f1(0.42 * SC) + '" cy="' + f1(-0.18 * SC) + '" r="1.2" fill="' + acc + '"/></g>';
    // the lid: its rim, the far bars, the pale plate, the near bars; a mast and its lamp
    var Wt = at(zt), bw = Wt * 0.36;
    out += cc(3, 3, zt - 0.03, Wt * 0.96, Wt * 0.96, 0.14, V.body);
    out += cc(3 - bw, 3, zt + 0.1, 0.09, Wt * 0.8, 0.08, V.body) + cc(3, 3 - bw, zt + 0.1, Wt * 0.8, 0.09, 0.08, V.body);
    out += cc(3, 3, zt + 0.1, Wt * 0.68, Wt * 0.68, 0.04, V.cap);
    out += cc(3 + bw, 3, zt + 0.1, 0.09, Wt * 0.8, 0.08, V.body) + cc(3, 3 + bw, zt + 0.1, Wt * 0.8, 0.09, 0.08, V.body);
    out += cc(3, 3, zt + 0.12, 0.3, 0.3, 0.12, VFX.base) + line(Q(3, 3, zt + 0.24), Q(3, 3, zt + 0.52), VFX.silver.l, 1.5) + vfLamp(3, 3, zt + 0.58, 0.17, acc);
    // in front: the near wing, and the engine pod out from under the collar's near side
    out += vfWing(3, 3 + cw / 2, -0.06, 0, 1, 0.4, W * 1.25, W * 0.66, 0.1);
    out += vfJet(3 + W * 0.62, 3 + W * 0.3, -0.52, 1, 0, 0.25, 2.2, cw / 2 - W * 0.62 + 0.02);
    return vfDone(out, zt + 1.05, -1.3);
  };

  /* The Vault's and the Fortress's parts, from u3d.js's vf* ones: a body in the company's own colour, as saturated as
   * the operator's pictures have it, lit from the top left; a dark plinth; blue-grey solar wings in a pale frame;
   * engines burning white-blue whatever the colour. Every point goes through Q, so the picture knows how far it
   * reaches and CO.skinSVG frames all of it. */
  var VFC = {}, VB = null;
  var VFX = { base: { top: '#3b3e48', l: '#2c2e36', r: '#202228' }, dark: { top: '#1a1d24', l: '#0d1015', r: '#08090d' },
    grey: { top: '#55545b', l: '#37363c', r: '#26252a' }, grey2: { top: '#b5b2bc', l: '#8a8791', r: '#66636d' },
    silver: { top: '#d0d6de', l: '#a9b1bc', r: '#7f8792' }, frame: '#7d8594', cell: '#5f6683', grid: '#b3b9c8',
    seam: '#16181e', jet: '#2f9cff', plume: '#5ac8ff', core: '#e6fcff', edge: 'rgba(5,7,10,.5)' };
  function rgbOf(hex) { var v = parseInt(hex.slice(1), 16); return [v >> 16 & 255, v >> 8 & 255, v & 255]; }
  function hexOf(c) { return '#' + c.map(function (v) { return ('0' + Math.round(Math.max(0, Math.min(255, v))).toString(16)).slice(-2); }).join(''); }
  function mix(a, b, t) { var p = rgbOf(a), q = rgbOf(b); return hexOf(p.map(function (v, i) { return v + (q[i] - v) * t; })); }
  // a colour of the accent's hue at saturation s and lightness l
  function tone(acc, s, l) {
    var c = rgbOf(acc).map(function (v) { return v / 255; }), mx = Math.max.apply(null, c), d = mx - Math.min.apply(null, c), h = 0;
    if (d) h = (mx === c[0] ? ((c[1] - c[2]) / d + 6) % 6 : mx === c[1] ? (c[2] - c[0]) / d + 2 : (c[0] - c[1]) / d + 4) / 6;
    var a = s * Math.min(l, 1 - l), f = function (n) { var k = (n + h * 12) % 12; return 255 * (l - a * Math.max(-1, Math.min(k - 3, 9 - k, 1))); };
    return hexOf([f(0), f(8), f(4)]);
  }
  function vfCols(acc) {
    return VFC[acc] || (VFC[acc] = {
      body: { top: tone(acc, 0.45, 0.43), l: tone(acc, 0.5, 0.32), r: tone(acc, 0.55, 0.22) },
      body2: { top: tone(acc, 0.42, 0.37), l: tone(acc, 0.48, 0.27), r: tone(acc, 0.5, 0.19) },
      cap: { top: tone(acc, 0.2, 0.62), l: tone(acc, 0.2, 0.5), r: tone(acc, 0.2, 0.38) },
      floor: tone(acc, 0.3, 0.2), tile: tone(acc, 0.3, 0.14), win: mix(acc, '#ffffff', 0.3)
    });
  }
  function Q(x, y, z) {
    var p = P(x, y, z), b = VB;
    if (b) { b[0] = Math.min(b[0], p[0]); b[1] = Math.min(b[1], p[1]); b[2] = Math.max(b[2], p[0]); b[3] = Math.max(b[3], p[1]); if (Math.abs(p[0]) < 30) b[4] = Math.min(b[4], p[1]); }
    return p;
  }
  // The picture's top (where its banner hangs: over everything near its middle) and its reach (CO.skinSVG frames
  // +-2 ext * SC * C30 across, down to P(3 + .7 ext, 3 + .7 ext, bot - .4)) from what it drew
  function vfDone(svg, top, bot) {
    var b = VB, hx = SC * I.C30, hy = SC * I.S30; VB = null;
    top = Math.max(top, (68 - b[4]) / SC);
    var ext = Math.max(3, Math.max(-b[0], b[2]) / (2 * hx) + 0.1,((b[3] - 4 + (bot - 0.4) * SC) / hy - 6) / 1.4);
    if (P(3, 3, top)[1] > b[1] + 8) ext = Math.max(ext, (6 - (b[1] + 8) / hy) / 2);
    return { svg: svg, top: top, bot: bot, ext: ext };
  }
  function pg(l, fill, extra) { return '<polygon points="' + pts(l.map(function (q) { return Q(q[0], q[1], q[2]); })) + '" fill="' + fill + '"' + (extra || '') + '/>'; }
  function flat(x, y, z, w, d) { return [[x - w / 2, y - d / 2, z], [x + w / 2, y - d / 2, z], [x + w / 2, y + d / 2, z], [x - w / 2, y + d / 2, z]]; }
  // a rectangle on a wall facing +x (at x) or +y (at y), from a to b along it and z0 to z1 up it
  function onX(x, a, b, z0, z1) { return [[x, a, z0], [x, b, z0], [x, b, z1], [x, a, z1]]; }
  function onY(y, a, b, z0, z1) { return [[a, y, z0], [b, y, z0], [b, y, z1], [a, y, z1]]; }
  // a window: a dark slit, and the light in it that its deck turns on
  function vfWin(q, V, on) { return pg(q, VFX.dark.l) + pg(q, V.win, ' class="w' + (on ? ' on' : '') + '"'); }
  // a box by the middle of its foot
  function cc(x, y, z, w, d, h, c) {
    var x0 = x - w / 2, y0 = y - d / 2;
    Q(x0, y0 + d, z); Q(x0 + w, y0 + d, z); Q(x0 + w, y0, z); Q(x0, y0, z + h); Q(x0 + w, y0 + d, z + h);
    return box(x0, y0, z, w, d, h, c.top, c.l, c.r, VFX.edge);
  }
  // a rounded rectangle's outline round (cx, cy), counter-clockwise on the map, k points to a corner
  function rrect(cx, cy, w, d, r, k) {
    var out = [], hw = w / 2, hd = d / 2;
    r = Math.max(0, Math.min(r, hw - 0.001, hd - 0.001));
    [[1, 1], [-1, 1], [-1, -1], [1, -1]].forEach(function (c, q) {
      for (var i = 0; i <= k; i++) { var a = (q + i / k) * Math.PI / 2; out.push([cx + c[0] * (hw - r) + r * Math.cos(a), cy + c[1] * (hd - r) + r * Math.sin(a)]); }
    });
    return out;
  }
  // a body lofted through rounded outlines [z, w, d, r] from its foot up: each face turned to us shaded by where it
  // faces (the left lit, the right in shade, one leaning back toward the top's colour, one leaning out darker), then
  // its top
  function loft(cx, cy, rings, c) {
    var ol = rings.map(function (g) { return rrect(cx, cy, g[1], g[2], g[3], 4); }), out = '';
    for (var i = 0; i < rings.length - 1; i++) {
      var a = ol[i], b = ol[i + 1], z0 = rings[i][0], z1 = rings[i + 1][0];
      for (var j = 0; j < a.length; j++) {
        var j2 = (j + 1) % a.length, ex = a[j2][0] - a[j][0], ey = a[j2][1] - a[j][1], L = Math.hypot(ex, ey);
        if (L < 1e-4) continue;
        var nx = ey / L, ny = -ex / L, back = ((a[j][0] + a[j2][0] - b[j][0] - b[j2][0]) * nx + (a[j][1] + a[j2][1] - b[j][1] - b[j2][1]) * ny) / 2;
        if ((z1 - z0) * (nx + ny) + back <= 0.002) continue;
        var s = back / Math.hypot(back, z1 - z0), col = mix(c.l, c.r, Math.max(0, Math.min(1, nx / (Math.max(0, nx) + Math.max(0, ny)))));
        col = s > 0 ? mix(col, c.top, Math.min(1, s * 1.1)) : mix(col, '#000000', Math.min(0.5, -s * 0.45));
        out += pg([[a[j][0], a[j][1], z0], [a[j2][0], a[j2][1], z0], [b[j2][0], b[j2][1], z1], [b[j][0], b[j][1], z1]], col, ' stroke="' + col + '" stroke-width=".5"');
      }
    }
    var t = rings[rings.length - 1][0];
    return out + pg(ol[ol.length - 1].map(function (p) { return [p[0], p[1], t]; }), c.top, ' stroke="' + c.top + '" stroke-width=".5"');
  }
  // a box rounded on every edge (u3d.js's RoundedBoxGeometry), r the rounding; a slight one stays square
  function rbox(cx, cy, z0, z1, w, d, r, c) {
    if (r < 0.07) return cc(cx, cy, z0, w, d, z1 - z0, c);
    var rg = [];
    [-60, -30, 0].forEach(function (a) { a *= Math.PI / 180; var i = r * (1 - Math.cos(a)); rg.push([z0 + r + r * Math.sin(a), w - 2 * i, d - 2 * i, r - i]); });
    [0, 35, 65, 90].forEach(function (a) { a *= Math.PI / 180; var i = r * (1 - Math.cos(a)); rg.push([z1 - r + r * Math.sin(a), w - 2 * i, d - 2 * i, r - i]); });
    return loft(cx, cy, rg, c);
  }
  // the screen outline round a set of points (monotone chain)
  function hull(p) {
    p = p.slice().sort(function (a, b) { return a[0] - b[0] || a[1] - b[1]; });
    var cr = function (o, a, b) { return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0]); }, lo = [], up = [], i;
    for (i = 0; i < p.length; i++) { while (lo.length > 1 && cr(lo[lo.length - 2], lo[lo.length - 1], p[i]) <= 0) lo.pop(); lo.push(p[i]); }
    for (i = p.length - 1; i >= 0; i--) { while (up.length > 1 && cr(up[up.length - 2], up[up.length - 1], p[i]) <= 0) up.pop(); up.push(p[i]); }
    return lo.slice(0, -1).concat(up.slice(0, -1));
  }
  // a cylinder lying on the map from a to b along (dx, dy), radius r: its outline, a light along its top, and the end
  // that faces us
  function tube(a, b, dx, dy, r, c, cap) {
    var ring = function (p, rr, up) { var o = []; for (var i = 0; i < 16; i++) { var t = i / 16 * Math.PI * 2, u = Math.cos(t) * rr; o.push(Q(p[0] - dy * u, p[1] + dx * u, p[2] + up + Math.sin(t) * rr)); } return o; };
    var A = ring(a, r, 0), B = ring(b, r, 0), end = dx + dy > 0 ? B : A;
    return '<polygon points="' + pts(hull(A.concat(B))) + '" fill="' + c.l + '" stroke="' + VFX.edge + '" stroke-width=".5"/>' +
      '<polygon points="' + pts(hull(ring(a, r * 0.45, r * 0.4).concat(ring(b, r * 0.45, r * 0.4)))) + '" fill="' + c.top + '" opacity=".55"/>' +
      '<polygon points="' + pts(end) + '" fill="' + cap + '" stroke="' + VFX.edge + '" stroke-width=".5"/>';
  }
  // An engine on its side (u3d.js vfJet): a silver pod with three dark ribs, a bell, a white-hot nozzle and a blue
  // plume. (x, y, z) is where it leaves the hull, (dx, dy) the way it points, r its radius, lk the plume in radii;
  // only what is out from k0 along it shows (the rest is inside the hull). Drawn from its far end to its near one.
  function vfJet(x, y, z, dx, dy, r, lk, k0) {
    var L = r * 2.4, nz = L + r * 0.62, len = r * lk * 0.92, at = function (k) { return [x + dx * k, y + dy * k, z]; };
    var parts = [[0, 0.3 * L - 0.08 * r, r, VFX.silver], [0.3 * L - 0.08 * r, 0.3 * L + 0.08 * r, r * 1.07, VFX.base], [0.3 * L + 0.08 * r, 0.52 * L - 0.08 * r, r, VFX.silver],
      [0.52 * L - 0.08 * r, 0.52 * L + 0.08 * r, r * 1.07, VFX.base], [0.52 * L + 0.08 * r, 0.74 * L - 0.08 * r, r, VFX.silver], [0.74 * L - 0.08 * r, 0.74 * L + 0.08 * r, r * 1.07, VFX.base],
      [0.74 * L + 0.08 * r, L, r, VFX.silver], [L, nz, r * 0.98, VFX.silver]].filter(function (p) { return p[1] > k0; });
    var near = dx + dy > 0, out = '';
    if (!near) parts.reverse();
    parts.forEach(function (p) { out += tube(at(Math.max(k0, p[0])), at(p[1]), dx, dy, p[2], p[3], near && p[0] === L ? VFX.core : p[3].top); });
    // the plume: a soft glow, the flame, its white core, a halo at the nozzle
    var p0 = Q.apply(null, at(nz)), p1 = Q.apply(null, at(nz + len)), ex = p1[0] - p0[0], ey = p1[1] - p0[1], el = Math.hypot(ex, ey) || 1, ux = ex / el, uy = ey / el, vx = -uy, vy = ux;
    var cone = function (w0, w1, k, tip) {
      var q = [[p0[0] + vx * w0, p0[1] + vy * w0], [p0[0] + ex * k + vx * w1, p0[1] + ey * k + vy * w1], [p0[0] + ex * k + ux * tip, p0[1] + ey * k + uy * tip], [p0[0] + ex * k - vx * w1, p0[1] + ey * k - vy * w1], [p0[0] - vx * w0, p0[1] - vy * w0]];
      q.forEach(function (c) { if (VB) { VB[0] = Math.min(VB[0], c[0]); VB[2] = Math.max(VB[2], c[0]); VB[1] = Math.min(VB[1], c[1]); VB[3] = Math.max(VB[3], c[1]); } });
      return pts(q);
    };
    var plume = '<circle cx="' + f1(p0[0] + ux * r * SC * 0.5) + '" cy="' + f1(p0[1] + uy * r * SC * 0.5) + '" r="' + f1(r * SC * 2.2) + '" fill="' + VFX.jet + '" opacity=".22"/>' +
      '<polygon class="flame" points="' + cone(r * SC * 1.2, r * SC * 0.8, 1, r * SC * 1.2) + '" fill="' + VFX.jet + '"/>' +
      '<polygon points="' + cone(r * SC * 0.85, r * SC * 0.45, 1, r * SC * 0.6) + '" fill="' + VFX.plume + '" opacity=".75"/>' +
      '<polygon points="' + cone(r * SC * 0.55, r * SC * 0.2, 0.45, r * SC * 0.5) + '" fill="' + VFX.core + '" opacity=".9"/>';
    return near ? out + plume : plume + out;
  }
  // A solar wing (u3d.js vfWing): a boom out of the hull at (x0, y0) along (ax, ay), one panel in a pale frame, `out`
  // long away from the hull and `side` along it, ten cells by five; its +x edge dips by tilt (his panels lean)
  function vfWing(x0, y0, z, ax, ay, boom, out, side, tilt) {
    var c = boom + out / 2, mx = x0 + ax * c, my = y0 + ay * c, hx = ax ? out / 2 : side / 2, hy = ax ? side / 2 : out / 2, sn = Math.sin(tilt * (ax || ay));
    var pan = function (ex, ez) {
      return [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(function (s) { var px = s[0] * (hx + ex); return [mx + px, my + s[1] * (hy + ex), z + ez - px * sn]; });
    };
    var o = line(Q(x0, y0, z), Q(x0 + ax * boom, y0 + ay * boom, z), VFX.silver.r, 1.8);
    o += pg(pan(0.05, -0.012), VFX.frame, ' stroke="' + VFX.edge + '" stroke-width=".5"') + pg(pan(0, 0), VFX.cell);
    var p = pan(0, 0.001), lx = hx >= hy, gl = function (a, b) { return line(Q(a[0], a[1], a[2]), Q(b[0], b[1], b[2]), VFX.grid, 0.7, 0.75); };
    var lerp = function (a, b, t) { return [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t]; };
    for (var i = 1; i < 10; i++) o += lx ? gl(lerp(p[0], p[1], i / 10), lerp(p[3], p[2], i / 10)) : gl(lerp(p[0], p[3], i / 10), lerp(p[1], p[2], i / 10));
    for (i = 1; i < 5; i++) o += lx ? gl(lerp(p[0], p[3], i / 5), lerp(p[1], p[2], i / 5)) : gl(lerp(p[0], p[1], i / 5), lerp(p[3], p[2], i / 5));
    return o;
  }
  // a lamp: the station's colour, pulsing in its halo
  function vfLamp(x, y, z, r, acc) {
    var p = Q(x, y, z); Q(x, y, z + r * 3);
    return '<circle cx="' + f1(p[0]) + '" cy="' + f1(p[1]) + '" r="' + f1(r * SC * 3) + '" fill="' + acc + '" opacity=".22"/>' + beacon(p, acc, f1(r * SC));
  }
  // the courtyard: its tiles, eight by eight
  function vfTiles(z, w, V) {
    var a = w / 2, o = pg(flat(3, 3, z, w, w), V.floor);
    for (var i = 1; i < 8; i++) { var u = -a + w * i / 8; o += line(Q(3 + u, 3 - a, z), Q(3 + u, 3 + a, z), V.tile, 0.8) + line(Q(3 - a, 3 + u, z), Q(3 + a, 3 + u, z), V.tile, 0.8); }
    return o;
  }
  // a grey block in the courtyard: two windows in each face we see (deck f), a pale lid with a lip
  function vfHouse(x, y, z0, w, h, f, V, R) {
    var o = cc(x, y, z0, w, w, h, VFX.grey), g = '', zc = z0 + h * 0.55, hh = h * 0.21;
    [-0.22, 0.22].forEach(function (u) {
      g += vfWin(onX(x + w / 2 + 0.012, y + u * w - 0.04, y + u * w + 0.04, zc - hh, zc + hh), V, R() < 0.3);
      g += vfWin(onY(y + w / 2 + 0.012, x + u * w - 0.04, x + u * w + 0.04, zc - hh, zc + hh), V, R() < 0.3);
    });
    return o + '<g class="fl" data-f="' + f + '">' + g + '</g>' + cc(x, y, z0 + h - 0.02, w + 0.06, w + 0.06, 0.1, VFX.grey2) + cc(x, y, z0 + h + 0.06, w * 0.8, w * 0.8, 0.08, VFX.grey2);
  }
  // one deck of the Fortress, his small Bull Club: a block in the company's colour on a dark plinth, four windows a
  // face, a dark hatch in its roof with a lamp on a mast, a solar wing out of two sides
  function vfBlock(V, acc, R) {
    var s = 2.1, h = 1.35, out = '', g = '';
    out += vfWing(3, 3 - s / 2 - 0.17, -0.1, 0, -1, 0.4, 2.1, 0.8, 0.12);
    out += cc(3, 3, -0.71, s * 0.6, s * 0.6, 0.3, VFX.base) + rbox(3, 3, -0.42, 0, s + 0.34, s + 0.34, 0.1, VFX.base) + rbox(3, 3, 0, h, s, s, 0.16, V.body);
    [[-0.12, 0.62], [0.12, 0.62], [-0.12, 0.38], [0.12, 0.38]].forEach(function (q) {
      var u = q[0] * s + 0.25, z = h * q[1];
      g += vfWin(onY(3 + s / 2 + 0.012, 3 + u - 0.1, 3 + u + 0.1, z - 0.1, z + 0.1), V, R() < 0.5) + vfWin(onX(3 + s / 2 + 0.012, 3 + u - 0.1, 3 + u + 0.1, z - 0.1, z + 0.1), V, R() < 0.5);
    });
    out += '<g class="fl" data-f="0">' + g + '</g>';
    out += pg(flat(3, 3, h + 0.005, s * 0.38, s * 0.38), VFX.base.top) + cc(3, 3, h, 0.34, 0.34, 0.16, VFX.dark);
    out += line(Q(3, 3, h + 0.16), Q(3, 3, h + 0.5), VFX.silver.l, 1.4) + vfLamp(3, 3, h + 0.56, 0.13, acc);
    out += vfWing(3, 3 + s / 2 + 0.17, -0.1, 0, 1, 0.4, 2.1, 0.8, 0.12);
    return vfDone(out, h + 1.2, -0.9);
  }

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
  // the orbits and the lights that run along them, a glow round the middle, and Cymetica in it
  Universe.prototype.drawSpace = function () {
    var Gx = CO.uvGalaxy, out = '', c = gp(0, 0, 0), cols = [C.green, C.cyan, C.green, C.cyan, C.blue, C.cyan, C.blue];
    out += '<ellipse cx="' + f1(c[0]) + '" cy="' + f1(c[1]) + '" rx="' + f1(120 * RX) + '" ry="' + f1(120 * RY) + '" fill="url(#uv-cc)" opacity=".5"/>';
    Gx.ORBITS.forEach(function (r, k) {
      var rx = r * RX, ry = r * RY, path = 'M' + f1(c[0] - rx) + ',' + f1(c[1]) + ' a' + f1(rx) + ',' + f1(ry) + ' 0 1 0 ' + f1(rx * 2) + ',0 a' + f1(rx) + ',' + f1(ry) + ' 0 1 0 ' + f1(-rx * 2) + ',0';
      out += '<path class="lane" d="' + path + '" stroke="' + cols[k] + '"/>';
      if (k % 3 === 1) out += '<ellipse class="lane2" cx="' + f1(c[0]) + '" cy="' + f1(c[1]) + '" rx="' + f1((r + 2.4) * RX) + '" ry="' + f1((r + 2.4) * RY) + '" stroke="' + cols[k] + '"/>';
      for (var j = 0; j < 2; j++) out += '<circle class="ship" r="14" fill="' + cols[k] + '"><animateMotion dur="' + (40 + r * 0.9).toFixed(0) + 's" begin="-' + (j * (40 + r * 0.9) / 2).toFixed(1) + 's" repeatCount="indefinite" path="' + path + '"/></circle>';
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
