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
  var RX = SC * I.C30 * Math.SQRT2, RY = SC * I.S30 * Math.SQRT2;   // a circle of radius 1, seen from the map

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
  // the flat map draws it at its first moment. Units are the stations' own (a deck is 0.8 high). The radii are his
  // picture's lines, measured on it (u3d.js, UVLINES): nothing inside 90, where Cymetica's own rings end at about 60.
  var ORBITS = [90, 105, 120, 136, 154, 178, 203], AZ = 1.08, SPIN = 2.2, R1 = ORBITS[ORBITS.length - 1];
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
  // world (x, up, z) on the flat map: the galaxy's disc is the map's floor, turned so that the side of it the 3D map's
  // first look faces (its camera's azimuth, AZ) is the side the flat one faces, so both show the same arrangement
  var ROT = AZ - Math.PI / 4, CR = Math.cos(ROT), SR = Math.sin(ROT);
  function gp(x, y, z) { return P(x * CR - z * SR, z * CR + x * SR, y); }
  // a point of the disc r out at the plan's angle a (CO.uvPlan's: x = sin a, z = cos a)
  function disc(r, a, y) { return gp(Math.sin(a) * r, y || 0, Math.cos(a) * r); }

  /* ---------------- the pieces every station uses ---------------- */
  function line(a, b, col, w, op, cls) {
    return '<line' + (cls ? ' class="' + cls + '"' : '') + ' x1="' + f1(a[0]) + '" y1="' + f1(a[1]) + '" x2="' + f1(b[0]) + '" y2="' + f1(b[1]) +
      '" stroke="' + col + '" stroke-width="' + (w || 1) + '"' + (op != null ? ' opacity="' + op + '"' : '') + '/>';
  }
  function beacon(p, acc, r) { return '<circle class="beacon" cx="' + f1(p[0]) + '" cy="' + f1(p[1]) + '" r="' + (r || 2.6) + '" fill="' + acc + '"/>'; }

  /* ---------------- the seven stations, n decks each ---------------- */
  // Each returns its picture, the top and bottom it reaches (in decks' units) and how far it reaches out (ext). All
  // seven are drawn as u3d.js builds them after the operator's orrery, from its builders' own measures: its x is the
  // map's x, its z the map's y, its y up. Every point goes through Q, so each picture frames what it drew (vfDone).
  var SKIN = {};
  // Spire, Vector Trading in his orrery: a glass tower of decks on a plinth, lit slats across its right face and two
  // rows of windows either side of a band of light up its left one (a deck's slats and windows are its lights), lit
  // edges, a square of light in its roof and a mast; four solar wings off the platform, light tubes round a column
  // under it, the engine's jet at the column's foot. The decks share the tower's height, so more decks are thinner.
  SKIN.tower = function (n, acc, R) {
    var V = sdCols(acc), s = fpOf(n) + 1.3, h = 0.2 * s, ts = 0.38 * s, H = s * (0.3 + 0.065 * n), dh = H / n, hs = ts / 2;
    var ps = 0.7 * s, ph = 0.055 * s, pr = ph * 0.45, cs = 0.26 * s, ch = 0.3 * s, out = '', f, i;
    VB = [0, 66, 0, 66, 66];
    var B = sdBase(s, h, V.hull, V.hull2, 0.44, 1, V), kb = B.kb, cz = kb - ch;
    // under it all: the jet, the column's foot and the column, its tubes of light (the far ones behind it), the keel
    var tubes = function (near) {
      var o = '';
      SDQ.forEach(function (q) { if ((q[0] + q[1] > 0) === near) o += line(Q(3 + q[0] * cs * 0.62, 3 + q[1] * cs * 0.62, kb - ch * 0.93), Q(3 + q[0] * cs * 0.62, 3 + q[1] * cs * 0.62, kb - ch * 0.03), V.band, 1.7); });
      [[1, 0], [0, 1], [-1, 0], [0, -1]].forEach(function (q) { if ((q[0] + q[1] > 0) === near) o += line(Q(3 + q[0] * cs * 0.53, 3 + q[1] * cs * 0.53, kb - ch * 0.8), Q(3 + q[0] * cs * 0.53, 3 + q[1] * cs * 0.53, kb - ch * 0.1), V.rim, 1.2); });
      return o;
    };
    out += sdJet(3, 3, cz - 0.05 * s, 0.6 * cs, 0.14 * s) + cc(3, 3, cz - 0.05 * s, cs * 1.15, cs * 1.15, 0.05 * s, V.hull2);
    out += tubes(false) + cc(3, 3, cz, cs, cs, ch, V.hull) + tubes(true) + B.keel;
    // the far wings, the platform, the near wings, the plinth with its line of light
    var wing = function (a) { return sdWing(a, s / 2, -h * 0.5, 0.5 * s, 0.22 * s, { lanes: 2, nx: 3, ny: 1 }); };
    out += wing(Math.PI / 2) + wing(Math.PI) + B.slab + wing(0) + wing(-Math.PI / 2);
    out += rbox(3, 3, 0, ph, ps, ps, pr, V.hull2) + sdLine(rrPts(3, 3, ps - pr * 0.5, ps - pr * 0.5, pr * 0.75, 0, 360, ph - pr * 0.22), V.neon, 1.3, true);
    // the tower, deck by deck: its glass, a dark seam between two decks, the deck's slats and windows
    var y = ph;
    for (f = 0; f < n; f++) {
      out += cc(3, 3, y, ts, ts, dh - 0.03, V.glass);
      if (f) out += '<polyline points="' + pts([Q(3 - hs - 0.025, 3 + hs + 0.025, y), Q(3 + hs + 0.025, 3 + hs + 0.025, y), Q(3 + hs + 0.025, 3 - hs - 0.025, y)]) + '" fill="none" stroke="' + V.seam + '" stroke-width="1.4"/>';
      var k = Math.max(1, Math.round(dh / 0.3)), sh = dh / k, wh = Math.min(0.09, sh * 0.34), g = '';
      for (i = 0; i < k; i++) {
        var yy = y + sh * (i + 0.5);
        g += vfWin(onX(3 + hs + 0.012, 3 - ts * 0.32, 3 + ts * 0.32, yy - wh / 2, yy + wh / 2), V, R() < 0.6);
        [-1, 1].forEach(function (o) { g += vfWin(onY(3 + hs + 0.012, 3 + o * ts * 0.3 - ts * 0.065, 3 + o * ts * 0.3 + ts * 0.065, yy - sh * 0.25, yy + sh * 0.25), V, R() < 0.5); });
      }
      out += '<g class="fl" data-f="' + f + '">' + g + '</g>';
      y += dh;
    }
    // the band of light up its left face, its three lit edges, the roof with its square of light, the mast
    out += pg(onY(3 + hs + 0.014, 3 - ts * 0.06, 3 + ts * 0.06, ph + 0.03, y - 0.03), V.band);
    [[-1, 1], [1, 1], [1, -1]].forEach(function (q) { out += sdLine([[3 + q[0] * hs, 3 + q[1] * hs, ph], [3 + q[0] * hs, 3 + q[1] * hs, y]], V.band, 1.8); });
    out += cc(3, 3, y, ts + 0.12, ts + 0.12, 0.16, V.roof) + pg(flat(3, 3, y + 0.165, ts * 0.62, ts * 0.62), V.sq);
    var mh = 0.2 * s;
    out += line(Q(3, 3, y + 0.16), Q(3, 3, y + 0.16 + mh), VFX.silver.r, 1.4) + vfLamp(3, 3, y + 0.18 + mh, 0.07, acc);
    return vfDone(out, y + 0.3 + mh, cz - 0.1 * s - 0.1);
  };
  // Biodome, Quasar Fund in his orrery: a glass dome glowing in the company's colour on a drum of ring decks, a lit
  // collar at its foot, on a dark platform with a hatch and modules on its deck; four broad solar wings
  SKIN.dome = function (n, acc, R) {
    var V = sdCols(acc), s = fpOf(n) + 1.3, h = 0.16 * s, out = '', f;
    VB = [0, 66, 0, 66, 66];
    var B = sdBase(s, h, V.hull, V.hull2, 0.56, 1, V);
    var wing = function (a) { return sdWing(a, s / 2, -h * 0.5, 0.62 * s, 0.34 * s, { nx: 4, ny: 2 }); };
    out += B.keel + wing(Math.PI / 2) + wing(Math.PI) + B.slab + wing(0) + wing(-Math.PI / 2);
    // on the deck: a hatch at the back, modules along the two front edges
    var hx = 3 - 0.37 * s, hy = 3 + 0.33 * s;
    out += vcyl(hx, hy, 0, 0.035 * s, 0.075 * s, V.hull2) + vcyl(hx, hy, 0, 0.04 * s, 0.05 * s, VFX.dark) + hoop(hx, hy, 0.035 * s, 0.075 * s, SDX.module.top, 1.2);
    [[-0.3, 0.42], [-0.18, 0.42], [0.42, -0.28], [0.42, -0.16]].forEach(function (q) {
      out += cc(3 + q[0] * s, 3 + q[1] * s, 0, (q[1] > 0.4 ? 0.08 : 0.06) * s, (q[1] > 0.4 ? 0.06 : 0.08) * s, 0.045 * s, SDX.module);
    });
    // the collar where the drum meets the deck, a lit ring round its top and lit ribs round its side
    var cr = 0.38 * s, chh = 0.045 * s;
    out += vcyl(3, 3, 0, chh, cr, V.hull2, 10) + hoop(3, 3, chh, cr, V.rim, 1.8);
    for (var k = 0; k < 18; k++) {
      var a = k / 18 * Math.PI * 2, c = Math.cos(a), sn = -Math.sin(a);
      if (c + sn > 0.2) out += line(Q(3 + c * (cr + 0.01), 3 + sn * (cr + 0.01), chh * 0.2), Q(3 + c * (cr + 0.01), 3 + sn * (cr + 0.01), chh * 0.7), V.soft, 1.6);
    }
    // the small dome at the front corner
    out += sdDome(3 + 0.37 * s, 3 + 0.37 * s, 0, 0.05 * s, 0.05 * s, SDX.module);
    // the drum: a ring deck per department -- its hull with a row of windows, a dark band, a line of light between
    var dr = 0.31 * s, dh = 0.085 * s, y = chh;
    for (f = 0; f < n; f++) {
      out += vcyl(3, 3, y, y + dh * 0.8, dr, V.drum, 10);
      out += '<g class="fl" data-f="' + f + '">' + sdRingWins(3, 3, dr, y + dh * 0.4, dh * 0.42, 0.26, 0.09, V, R, 0.5) + '</g>';
      out += hoop(3, 3, y + dh * 0.8, dr, V.soft, 1.3, 'far') + vcyl(3, 3, y + dh * 0.8, y + dh, dr * 0.95, V.band2, 10) + hoop(3, 3, y + dh * 0.8, dr, V.soft, 1.5, 'near');
      y += dh;
    }
    // the glass dome on its rim: behind the glass the far ribs, a garden and a light; the glass; the near ribs, the cap
    var gr = 0.235 * s, gh = 0.24 * s, rib = function (near) {
      var o = '';
      for (var j = 0; j < 10; j++) { var t = j / 10 * Math.PI * 2, x = 3 + Math.cos(t) * gr, yy = 3 + Math.sin(t) * gr; if ((Math.cos(t) + Math.sin(t) > 0) === near) o += line(Q(x, yy, y + 0.04), Q(x, yy, y + gh), SDX.cap.l, near ? 1.3 : 0.9, near ? 0.9 : 0.5); }
      return o;
    };
    out += vcyl(3, 3, y, y + 0.04, gr + 0.04, SDX.trim, 10) + hoop(3, 3, y + 0.04, gr + 0.02, V.rim, 1.6);
    out += rib(false);
    for (k = 0; k < 5; k++) { var t = k / 5 * Math.PI * 2 + 0.3, lp = Q(3 + Math.cos(t) * gr * 0.6, 3 + Math.sin(t) * gr * 0.6, y + 0.06 * s); out += '<ellipse cx="' + f1(lp[0]) + '" cy="' + f1(lp[1]) + '" rx="' + f1(0.07 * s * RX * 0.72) + '" ry="' + f1(0.09 * s * SC * 0.9) + '" fill="' + SDX.leaf + '"/>'; }
    var cp = Q(3, 3, y + gh * 0.55);
    out += '<circle cx="' + f1(cp[0]) + '" cy="' + f1(cp[1]) + '" r="' + f1(0.06 * s * RX * 0.75) + '" fill="' + V.band + '"/>';
    out += sdGlass(3, 3, y, y + gh, gr, 0.1 * s, V) + rib(true) + hoop(3, 3, y + gh, gr, V.soft, 1.4);
    out += line(Q(3, 3, y + gh + 0.1 * s), Q(3, 3, y + gh + 0.17 * s), VFX.silver.r, 1.6) + vfLamp(3, 3, y + gh + 0.18 * s, 0.06, acc);
    return vfDone(out, y + gh + 0.18 * s + 0.15, B.kb - 0.1);
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
  // Ring station, Sigma Collective in his orrery: a stack of ring decks stepping in, a line of light round each rim,
  // a neck, a saucer and a dome over them and a dish on top, on a light grey platform with two lines of light and lit
  // ports along its sides; solar wings off three sides, an engine glowing blue out of the fourth
  SKIN.orbital = function (n, acc, R) {
    var V = sdCols(acc), G = sdGreys(acc), s = fpOf(n) + 1.3, h = 0.16 * s, out = '', f;
    VB = [0, 66, 0, 66, 66];
    var B = sdBase(s, h, G.plate, G.steel2, 0.56, 2, V);
    var wing = function (a) { return sdWing(a, s / 2, -h * 0.45, 0.62 * s, 0.28 * s, { rows: 2, nx: 3, ny: 2 }); };
    out += B.keel + wing(Math.PI / 2) + wing(Math.PI) + B.slab + wing(-Math.PI / 2);
    // the lit ports along the two sides we see (none where the engine is), then the engine out of the right side
    [0, 0.28].forEach(function (o) { out += pg(onX(3 + s / 2 + 0.008, 3 + o * s - 0.085 * s, 3 + o * s + 0.085 * s, -h * 0.68, -h * 0.52), SDX.lamp); });
    [-0.28, 0, 0.28].forEach(function (o) { out += pg(onY(3 + s / 2 + 0.008, 3 - o * s - 0.085 * s, 3 - o * s + 0.085 * s, -h * 0.68, -h * 0.52), SDX.lamp); });
    out += sdEngine(3 + s / 2, 3 - 0.22 * s, -h * 0.5, 0.075 * s);
    // the hub: ring decks stepping in, each with a line of light round its rim and its ports round its side
    var r0 = 0.36 * s, r1 = 0.25 * s, dh = 0.1 * s, y = 0.03 * s;
    out += vcyl(3, 3, 0, 0.03 * s, r0 + 0.04 * s, G.steel2, 10);
    for (f = 0; f < n; f++) {
      var r = n > 1 ? r0 + (r1 - r0) * f / (n - 1) : r0, th = dh * 0.66;
      out += vcyl(3, 3, y, y + th, r, G.steel, 10) + hoop(3, 3, y + 0.012, r + 0.01, acc, 0.6, 'near', true);
      out += '<g class="fl" data-f="' + f + '">' + sdRingWins(3, 3, r, y + th * 0.5, th * 0.34, 0.3, 0.11, V, R, 0.5) + '</g>';
      out += hoop(3, 3, y + th - 0.01, r + 0.01, V.rim, 0.8, 'far', true) + vcyl(3, 3, y + th, y + dh, r * 0.86, G.steel2, 10) + hoop(3, 3, y + th - 0.01, r + 0.01, V.rim, 1, 'near', true);
      y += dh;
    }
    // the neck, the saucer with its line of light, the dome's seat and the dome; the dish on it and a light beside
    var sr = 0.29 * s, dr = 0.15 * s;
    out += vcyl(3, 3, y, y + 0.05 * s, 0.17 * s, G.steel2, 8); y += 0.05 * s;
    out += vcyl(3, 3, y, y + 0.065 * s, sr, G.steel, 10) + hoop(3, 3, y + 0.055 * s, sr + 0.01, V.rim, 1.6, 'near'); y += 0.065 * s;
    out += vcyl(3, 3, y, y + 0.06 * s, dr, G.steel2, 8); y += 0.06 * s;
    out += sdDome(3, 3, y, dr, 0.11 * s, SDX.cap);
    var yt = y + 0.11 * s, bw = Q(3, 3, yt + 0.07 * s);
    out += line(Q(3, 3, yt), Q(3, 3, yt + 0.06 * s), VFX.silver.r, 1.3);
    out += '<ellipse cx="' + f1(bw[0]) + '" cy="' + f1(bw[1]) + '" rx="' + f1(0.075 * s * RX * 0.75) + '" ry="' + f1(0.075 * s * RY * 0.35) + '" fill="' + SDX.cap.l + '" stroke="' + SDX.cap.r + '" stroke-width=".6" transform="rotate(-10 ' + f1(bw[0]) + ' ' + f1(bw[1]) + ')"/>';
    Q(3 - 0.075 * s, 3 + 0.075 * s, yt + 0.1 * s); Q(3 + 0.075 * s, 3 - 0.075 * s, yt + 0.1 * s);
    out += vfLamp(3 + 0.12 * s, 3, yt - 0.04 * s, 0.05, acc);
    // a module at the platform's front corner, turned to it
    out += sdPrism(sqAt(3 + 0.33 * s, 3 + 0.33 * s, 0.055 * s * Math.SQRT2, 0), 0, 0.08 * s, SDX.module);
    return vfDone(out, yt + 0.12 * s, B.kb - 0.1);
  };
  // Laser station (key 'rocket', so a company saved with the old Starship keeps its pick), as the operator's picture
  // draws it: an armoured block in the company's colour under a round lid, a laser cannon out of its left side firing
  // a beam of its colour, pale solar wings on the other three; under the block a dark drum, one ribbed ring per deck,
  // its windows lit while the deck's department works
  SKIN.rocket = function (n, acc, R) {
    var L = lsCols(acc), V = sdCols(acc), w = 1.6 + Math.min(n, 8) * 0.06, hc = w * 0.95, half = w / 2, rd = w * 0.4, dh = 0.4, out = '', f;
    VB = [0, 66, 0, 66, 66];
    // the drum of decks under the block, drawn from its foot up: the cone and light at its foot, each deck's rib and
    // ring with its windows, the broad rib under the block
    var yb = -0.08 - n * dh;
    out += sdCone(3, 3, yb, yb - 0.32, rd * 0.72, LSX.drum) + vfLamp(3, 3, yb - 0.4, 0.06, acc);
    for (f = n - 1; f >= 0; f--) {
      var top = -0.08 - f * dh;
      out += vcyl(3, 3, top - dh, top - dh + 0.07, rd + 0.05, LSX.rib, 8) + vcyl(3, 3, top - dh + 0.07, top, rd, LSX.drum, 8);
      out += '<g class="fl" data-f="' + f + '">' + sdRingWins(3, 3, rd, top - (dh - 0.07) / 2, 0.1, 0.34, 0.09, V, R, 0.35) + '</g>';
    }
    out += vcyl(3, 3, -0.08, 0, rd + 0.1, LSX.rib, 8);
    // the wings: the far two behind the block, the right one in front of it
    var wy = hc * 0.52, pl = w * 2.0, pw = w * 0.8, w0 = half + 0.3;
    out += lsWing(Math.PI, half, w0, wy, pl, pw, -0.35) + lsWing(Math.PI / 2, half, w0, wy, pl, pw, 0.35);
    // the block: rounded, on the two faces we see a dark plate in a frame of the body's colour; the round lid
    out += rbox(3, 3, 0, hc, w, w, 0.12 * w, L.body);
    [0, 1].forEach(function (F) {
      var on = F ? function (a, b, z0, z1, e) { return onX(3 + half + e, 3 + a, 3 + b, z0, z1); } : function (a, b, z0, z1, e) { return onY(3 + half + e, 3 + a, 3 + b, z0, z1); };
      out += pg(on(-w * 0.31, w * 0.31, hc * 0.21, hc * 0.79, 0.008), L.plate);
      var bar = F ? L.body.r : L.body.l;
      [1, -1].forEach(function (sg) {
        out += pg(on(-w * 0.36, w * 0.36, hc / 2 + sg * hc * 0.32 - 0.04, hc / 2 + sg * hc * 0.32 + 0.04, 0.03), bar);
        out += pg(on(sg * w * 0.34 - 0.04, sg * w * 0.34 + 0.04, hc * 0.18, hc * 0.82, 0.03), bar);
      });
    });
    out += vcyl(3, 3, hc, hc + 0.08, w * 0.37, LSX.rib, 8) + vcyl(3, 3, hc + 0.08, hc + 0.08 + w * 0.24, w * 0.42, L.lid, 10);
    out += lsWing(0, half, w0, wy, pl, pw, 0.35);
    // the cannon out of the left side: a dark ribbed housing, a collar and a barrel of the body's colour, a ring of
    // light at its mouth and the beam, a light at its tip
    var ly = hc * 0.36, cy = 3 + half, at = function (k) { return [3, cy + k, ly]; }, parts = [];
    var rib = [0.08, 0.21, 0.34, 0.47].map(function (k) { return k * w; }), k0 = 0;
    rib.forEach(function (c) { parts.push([k0, c - 0.025, w * 0.22, LSX.drum]); parts.push([c - 0.025, c + 0.025, w * 0.235, LSX.rib]); k0 = c + 0.025; });
    parts.push([k0, w * 0.6, w * 0.22, LSX.drum], [w * 0.6, w * 0.74, w * 0.17, L.lid], [w * 0.74, w * 0.96, w * 0.055, L.lid]);
    parts.forEach(function (p) { out += tube(at(p[0]), at(p[1]), 0, 1, p[2], p[3], p[3].top); });
    var zb = w * 0.96, bl = w * 1.6, b0 = Q.apply(null, at(zb)), b1 = Q.apply(null, at(zb + bl));
    out += '<polygon points="' + pts(sdRingAt(at(zb), 0, 1, w * 0.07)) + '" fill="none" stroke="' + V.band + '" stroke-width="1.4"/>';
    out += line(b0, b1, acc, 10, 0.2) + line(b0, b1, acc, 5.5, 0.35) + line(b0, b1, V.neon, 2.8) + line(b0, b1, '#ffffff', 1.1, 0.85);
    out += '<circle cx="' + f1(b1[0]) + '" cy="' + f1(b1[1]) + '" r="' + f1(0.45 * RX) + '" fill="' + acc + '" opacity=".28"/>' + beacon(b1, V.neon, 2.4);
    VB[0] = Math.min(VB[0], b1[0] - 0.45 * RX); VB[3] = Math.max(VB[3], b1[1] + 0.45 * RX);
    return vfDone(out, hc + w * 0.32 + 0.3, yb - 0.5);
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
  // Data stack, the operator's picture's "Night Owl Trading": dark server blocks of different heights, a block per
  // department, each a pile of plates with a strip of light along every plate that the department's work lights; on a
  // rounded base ringed in the company's colour, two engines glowing blue at its stern, a dark solar wing either side.
  // u3d.js draws it in a server block's own units and then 1.3 times as large, so every measure here is times K. Its
  // blocks take their heights from R in u3d.js's own order, so a seed gives the same skyline in both pictures.
  SKIN.stack = function (n, acc, R) {
    var K = 1.3, m = Math.max(1, Math.min(n, 8)), cols = m === 1 ? 1 : m <= 4 ? 2 : m <= 6 ? 3 : 4, rows = m <= 2 ? 1 : 2, cell = 1.08, s = 0.98;
    var bw = cols * cell + 0.72, bd = rows * cell + 0.72, bh = 0.46, S = stCols(acc), V = sdCols(acc), out = '', blocks = [], hmax = 0.4;
    VB = [0, 66, 0, 66, 66];
    // its own units to the map's: x and z about the middle, times K
    var X = function (x) { return 3 + x * K; };
    // the blocks first, as u3d.js reads R: a height, then a window's light per plate and face
    for (var j = 0, f = 0; j < rows; j++) for (var i = 0; i < cols; i++, f++) {
      var x = (i - (cols - 1) / 2) * cell, z = (j - (rows - 1) / 2) * cell;
      if (f >= m) { blocks.push({ x: x, z: z }); continue; }
      var hb = 0.8 + R() * 0.38, np = Math.max(4, Math.round(hb / 0.18)), ph = hb / np, lit = [];
      for (var k = 0; k < np; k++) lit.push([R() < 0.2, R() < 0.2, R() < 0.2, R() < 0.2]);
      hmax = Math.max(hmax, hb);
      blocks.push({ x: x, z: z, f: f, hb: hb, np: np, ph: ph, lit: lit });
    }
    // the far wing, the keel and the skirt, the base with its line of light
    out += stWing(-1, bd, bh, K);
    out += cc(3, 3, (-bh - 0.49) * K, bw * 0.46 * K, bd * 0.46 * K, 0.22 * K, S.dark) + rbox(3, 3, (-bh - 0.28) * K, (-bh + 0.02) * K, (bw - 0.34) * K, (bd - 0.34) * K, 0.13 * K, S.dark);
    out += rbox(3, 3, -bh * K, 0, bw * K, bd * K, 0.15 * K, S.base);
    out += sdLine(rrPts(3, 3, (bw + 0.02) * K, (bd + 0.02) * K, 0.15 * K, 0, 360, -0.12 * K), V.neon, 1.6, true);
    // the blocks back to front: a dark core, its plates, the strips of light on the faces we see, a lid and a light
    blocks.slice().sort(function (a, b) { return (a.x + a.z) - (b.x + b.z); }).forEach(function (b) {
      var bx = X(b.x), by = X(b.z);
      if (b.f == null) {
        out += cc(bx, by, 0, 0.62 * K, 0.62 * K, 0.34 * K, S.side) + vcyl(bx, by, 0.34 * K, 0.39 * K, 0.2 * K, VFX.silver, 8) + vcyl(bx, by, 0.38 * K, 0.41 * K, 0.16 * K, VFX.dark, 8);
        return;
      }
      var hs = s / 2 * K, g = '';
      out += cc(bx, by, 0, (s - 0.1) * K, (s - 0.1) * K, b.hb * K, S.dark);
      for (var q = 0; q < b.np; q++) {
        var z0 = q * b.ph * K, zc = (q * b.ph + b.ph / 2) * K, wh = 0.013 * K;
        // a plate, and the light its rounded top edge catches
        var zt = z0 + (b.ph - 0.0175) * K;
        out += cc(bx, by, z0 + 0.0175 * K, s * K, s * K, (b.ph - 0.035) * K, S.side) +
          '<polyline points="' + pts([Q(bx - hs, by + hs, zt), Q(bx + hs, by + hs, zt), Q(bx + hs, by - hs, zt)]) + '" fill="none" stroke="' + S.edge + '" stroke-width=".9"/>';
        g += vfWin(onY(by + hs + 0.008, bx - 0.28 * s * K, bx + 0.28 * s * K, zc - wh, zc + wh), V, b.lit[q][0]);
        g += vfWin(onX(bx + hs + 0.008, by - 0.28 * s * K, by + 0.28 * s * K, zc - wh, zc + wh), V, b.lit[q][2]);
      }
      // the lid; a block hemmed in at the back has its faces hidden behind its neighbours, so its deck also lights a
      // panel in the lid, which the map always sees
      out += cc(bx - 0.1 * s * K, by + 0.1 * s * K, b.hb * K, 0.56 * s * K, 0.42 * s * K, 0.05 * K, S.top);
      g += pg(flat(bx - 0.1 * s * K, by + 0.1 * s * K, (b.hb + 0.051) * K, 0.4 * s * K, 0.26 * s * K), V.win, ' class="w"');
      out += '<g class="fl" data-f="' + b.f + '">' + g + '</g>';
      var lp = Q(bx + 0.38 * s * K, by - 0.38 * s * K, (b.hb + 0.03) * K);
      out += beacon(lp, V.neon, 1.6);
    });
    // the engines at the stern, the far one first; the near wing
    out += stEngine(X(bw / 2), X(-0.42), -bh * 0.5 * K, K) + stEngine(X(bw / 2), X(0.42), -bh * 0.5 * K, K);
    out += stWing(1, bd, bh, K);
    return vfDone(out, (hmax + 0.3) * K, (-bh - 0.7) * K);
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
  // a point on the map, its screen bounds kept in VB: [left, top, right, bottom, the top near the middle, and the
  // farthest the picture reaches out from its axis on the map -- u3d.js's foot]
  function Q(x, y, z) {
    var p = P(x, y, z), b = VB;
    if (b) {
      b[0] = Math.min(b[0], p[0]); b[1] = Math.min(b[1], p[1]); b[2] = Math.max(b[2], p[0]); b[3] = Math.max(b[3], p[1]); if (Math.abs(p[0]) < 30) b[4] = Math.min(b[4], p[1]);
      b[5] = Math.max(b[5] || 0, Math.hypot(x - 3, y - 3));
    }
    return p;
  }
  // the holo-ring under a station, as wide as u3d.js makes it from the station's reach
  function ringOf(foot) { return Math.max(2.0, Math.min(foot, 6.5) * 0.72); }
  // The picture's top (where its banner hangs: over everything near its middle), its foot, and its reach (CO.skinSVG
  // frames +-2 ext * SC * C30 across, down to P(3 + .7 ext, 3 + .7 ext, bot - .4)) from what it drew and the ring
  // CO.skinArt puts under it
  function vfDone(svg, top, bot) {
    var b = VB, hx = SC * I.C30, hy = SC * I.S30, foot = b[5] || 3, rr = ringOf(foot) * 1.18, rc = P(3, 3, bot - 0.4); VB = null;
    b[0] = Math.min(b[0], rc[0] - rr * RX); b[2] = Math.max(b[2], rc[0] + rr * RX); b[3] = Math.max(b[3], rc[1] + rr * RY);
    top = Math.max(top, (68 - b[4]) / SC);
    var ext = Math.max(3, Math.max(-b[0], b[2]) / (2 * hx) + 0.1,((b[3] - 4 + (bot - 0.4) * SC) / hy - 6) / 1.4);
    if (P(3, 3, top)[1] > b[1] + 8) ext = Math.max(ext, (6 - (b[1] + 8) / hy) / 2);
    return { svg: svg, top: top, bot: bot, ext: ext, foot: foot };
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
  function loft(cx, cy, rings, c, k) {
    var ol = rings.map(function (g) { return rrect(cx, cy, g[1], g[2], g[3], k || 4); }), out = '';
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
  // a cylinder lying on the map from a to b along (dx, dy), radius r (r1 at b, for a bell): its outline, a light
  // along its top, and the end that faces us
  function tube(a, b, dx, dy, r, c, cap, r1) {
    var ring = function (p, rr, up) { var o = []; for (var i = 0; i < 16; i++) { var t = i / 16 * Math.PI * 2, u = Math.cos(t) * rr; o.push(Q(p[0] - dy * u, p[1] + dx * u, p[2] + up + Math.sin(t) * rr)); } return o; };
    var rb = r1 || r, A = ring(a, r, 0), B = ring(b, rb, 0), end = dx + dy > 0 ? B : A;
    return '<polygon points="' + pts(hull(A.concat(B))) + '" fill="' + c.l + '" stroke="' + VFX.edge + '" stroke-width=".5"/>' +
      '<polygon points="' + pts(hull(ring(a, r * 0.45, r * 0.4).concat(ring(b, rb * 0.45, rb * 0.4)))) + '" fill="' + c.top + '" opacity=".55"/>' +
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

  /* The Spire's, the Biodome's, the Ring station's, the Laser station's and the Data stack's parts, from u3d.js's
   * srd*, ls* and st* ones, drawn with the helpers above. Their colours are what the Settings preview shows of
   * u3d.js's materials, read off it in all four colours: a hull tinted by the company's colour comes out lighter the
   * brighter that colour is (its green hulls far lighter than its blue ones), so a tone's lightness here follows the
   * colour's luminance (lt). Lines of light are a sharp core over a soft glow, as the preview's bloom draws them. */
  var SDQ = [[1, 1], [1, -1], [-1, 1], [-1, -1]];
  // what every company's station shares: pale modules and caps, trim, the Biodome's garden, the Ring station's ports,
  // the srd solar cells (slate blue in a pale frame)
  var SDX = { module: { top: '#c3cbd3', l: '#a2abb5', r: '#7a838e' }, cap: { top: '#e2e4ea', l: '#c1c4cc', r: '#8f939c' },
    trim: { top: '#6b7a90', l: '#56647a', r: '#414c5e' }, metal: { top: '#7d8aa0', l: '#5a6b82', r: '#46536a' }, leaf: '#1d5a42', lamp: '#c4eef2',
    solar: { frame: '#a9b7cc', cell: '#5b76a3', line: '#bccbe4' } };
  // the Laser station's dark drum and ribs, its pale wings
  var LSX = { drum: { top: '#2a2d33', l: '#1d1f24', r: '#121418' }, rib: { top: '#4a4e57', l: '#373a42', r: '#25272d' },
    wing: { cell: '#c4c2cf', line: '#a19fb2', frame: '#e6e4ec' } };
  function lumOf(hex) {
    var c = rgbOf(hex).map(function (v) { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); });
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
  }
  // a tone of the accent's hue at saturation s, its lightness a + b times the accent's luminance
  function lt(acc, s, a, b) { return tone(acc, s, Math.max(0.05, Math.min(0.93, a + b * lumOf(acc)))); }
  // the srd stations' hulls (slate tinted by the colour), the Spire's glass, the Biodome's drum, the lines of light
  function sdCols(acc) {
    var k = 'sd' + acc;
    return VFC[k] || (VFC[k] = {
      hull: { top: lt(acc, 0.33, 0.11, 0.53), l: lt(acc, 0.4, 0.05, 0.38), r: lt(acc, 0.42, 0.01, 0.34) },
      hull2: { top: lt(acc, 0.3, 0.16, 0.5), l: lt(acc, 0.3, 0.12, 0.5), r: lt(acc, 0.32, 0.06, 0.45) },
      glass: { top: lt(acc, 0.5, 0.14, 0.72), l: lt(acc, 0.52, 0.1, 0.78), r: lt(acc, 0.56, 0.05, 0.72) },
      roof: { top: lt(acc, 0.3, 0.22, 0.25), l: lt(acc, 0.3, 0.15, 0.22), r: lt(acc, 0.3, 0.1, 0.2) },
      drum: { top: lt(acc, 0.4, 0.08, 0.45), l: lt(acc, 0.5, 0.0, 0.45), r: lt(acc, 0.52, -0.03, 0.38) },
      band2: { top: lt(acc, 0.3, 0.06, 0.1), l: lt(acc, 0.3, 0.04, 0.08), r: lt(acc, 0.3, 0.03, 0.06) },
      neon: mix(acc, '#ffffff', 0.45), rim: mix(acc, '#ffffff', 0.3), soft: mix(acc, '#ffffff', 0.12), band: mix(acc, '#ffffff', 0.62),
      sq: lt(acc, 0.6, 0.5, 0.2), seam: '#15181f', win: mix(acc, '#ffffff', 0.35)
    });
  }
  // the Ring station's light grey platform and its steel, a little of the company's colour in its light
  function sdGreys(acc) {
    var k = 'sg' + acc, t = function (hex) { return mix(hex, acc, 0.06); };
    return VFC[k] || (VFC[k] = {
      plate: { top: t('#a9abb4'), l: t('#878890'), r: t('#5e6a7a') },
      steel: { top: t('#81868e'), l: t('#91979f'), r: t('#61676f') },
      steel2: { top: t('#606369'), l: t('#4f525a'), r: t('#383b41') }
    });
  }
  // the Laser station's body and lid in the company's colour (lit on the right, as the preview's light falls), its plates
  function lsCols(acc) {
    var k = 'ls' + acc;
    return VFC[k] || (VFC[k] = {
      body: { top: lt(acc, 0.4, 0.5, 0.25), l: lt(acc, 0.45, 0.22, 0.33), r: lt(acc, 0.42, 0.34, 0.28) },
      lid: { top: lt(acc, 0.4, 0.55, 0.25), l: lt(acc, 0.45, 0.22, 0.3), r: lt(acc, 0.45, 0.16, 0.25) },
      plate: lt(acc, 0.3, 0.07, 0.05)
    });
  }
  // the Data stack: dark slate everywhere, its base faintly of the company's colour
  function stCols(acc) {
    var k = 'st' + acc;
    return VFC[k] || (VFC[k] = {
      base: { top: mix('#1c2532', acc, 0.1), l: mix('#0e141d', acc, 0.04), r: mix('#0a0f17', acc, 0.03) },
      dark: { top: '#141a23', l: '#0b0f15', r: '#07090d' },
      side: { top: '#232c3a', l: '#0f141c', r: '#171e2a' }, edge: '#3a4659',
      top: { top: '#36435a', l: '#253043', r: '#1c2433' }
    });
  }
  // (u, v) turned by a about the upright axis, as u3d.js's rotXZ turns its (x, z)
  function rot(u, v, a) { var c = Math.cos(a), s = Math.sin(a); return [u * c + v * s, -u * s + v * c]; }
  // one stroke of a path between two points
  function seg(a, b) { var p = Q(a[0], a[1], a[2]), q = Q(b[0], b[1], b[2]); return 'M' + f1(p[0]) + ',' + f1(p[1]) + 'L' + f1(q[0]) + ',' + f1(q[1]); }
  // points along a rounded rectangle's outline round (cx, cy) at height z, from angle a0 to a1 (degrees, 0 = +x,
  // counter-clockwise on the map): -45 to 135 is the half turned to us
  function rrPts(cx, cy, w, d, r, a0, a1, z) {
    var hw = w / 2, hd = d / 2, out = [], C4 = [[1, 1], [-1, 1], [-1, -1], [1, -1]];
    r = Math.max(0, Math.min(r, hw - 0.001, hd - 0.001));
    for (var q = Math.floor(a0 / 90); q * 90 < a1; q++) {
      var c = C4[((q % 4) + 4) % 4], b0 = Math.max(a0, q * 90), b1 = Math.min(a1, q * 90 + 90), m = Math.max(1, Math.ceil((b1 - b0) / 15));
      for (var i = 0; i <= m; i++) { var t = (b0 + (b1 - b0) * i / m) * Math.PI / 180; out.push([cx + c[0] * (hw - r) + r * Math.cos(t), cy + c[1] * (hd - r) + r * Math.sin(t), z]); }
    }
    return out;
  }
  // a line of light through points: a soft wide glow under a sharp core
  function sdLine(l, col, w, closed, op) {
    var p = pts(l.map(function (q) { return Q(q[0], q[1], q[2]); })), tag = closed ? 'polygon' : 'polyline', k = op == null ? 1 : op;
    return '<' + tag + ' points="' + p + '" fill="none" stroke="' + col + '" stroke-width="' + f1(w * 2.8) + '" opacity="' + f1(0.22 * k * 100) / 100 + '" stroke-linejoin="round"/>' +
      '<' + tag + ' points="' + p + '" fill="none" stroke="' + col + '" stroke-width="' + w + '"' + (op != null ? ' opacity="' + op + '"' : '') + ' stroke-linejoin="round" stroke-linecap="round"/>';
  }
  // a ring of light round an upright axis at height z (a torus seen from the map): all of it, its far half or its near
  // half; its glow kept tight, as rings stacked a deck apart would otherwise run into one, and none at all (bare)
  // where they are a deck's fine line on steel
  function hoop(x, y, z, r, col, w, part, bare) {
    var a0 = part === 'near' ? -45 : part === 'far' ? 135 : 0, a1 = part === 'near' ? 135 : part === 'far' ? 315 : 360, l = [];
    for (var a = a0; a <= a1 + 0.01; a += 7.5) l.push(Q(x + r * Math.cos(a * Math.PI / 180), y + r * Math.sin(a * Math.PI / 180), z));
    var p = pts(l);
    return (bare ? '' : '<polyline points="' + p + '" fill="none" stroke="' + col + '" stroke-width="' + f1(w * 2) + '" opacity=".14"/>') +
      '<polyline points="' + p + '" fill="none" stroke="' + col + '" stroke-width="' + w + '" stroke-linecap="round"/>';
  }
  // an upright cylinder (u3d.js's G.cyl), round (x, y) from z0 to z1: its side shaded as it turns, then its top
  function vcyl(x, y, z0, z1, r, c, k) { return loft(x, y, [[z0, 2 * r, 2 * r, r], [z1, 2 * r, 2 * r, r]], c, k || 6); }
  // a cone hanging from an upright drum's foot, its tip at z1 below z0
  function sdCone(x, y, z0, z1, r, c) {
    var a = Q(x, y, z0), t = Q(x, y, z1), rx = r * RX, ry = r * RY;
    Q(x - r, y + r, z0); Q(x + r, y - r, z0); Q(x + r, y + r, z0);
    return '<path d="M' + f1(a[0] - rx) + ',' + f1(a[1]) + ' A' + f1(rx) + ',' + f1(ry) + ' 0 0 0 ' + f1(a[0] + rx) + ',' + f1(a[1]) + ' L' + f1(t[0]) + ',' + f1(t[1]) + ' Z" fill="' + c.l + '" stroke="' + VFX.edge + '" stroke-width=".5"/>';
  }
  // a dome (u3d.js's G.hemi), r across and hgt high, on (x, y, z): its outline, a highlight up its lit side
  function sdDome(x, y, z, r, hgt, c) {
    var p = Q(x, y, z), rx = r * RX, ry = r * RY, vr = Math.sqrt(hgt * SC * hgt * SC + ry * ry);
    Q(x - r, y + r, z); Q(x + r, y - r, z); Q(x + r, y + r, z); Q(x, y, z + hgt);
    return '<path d="M' + f1(p[0] - rx) + ',' + f1(p[1]) + ' A' + f1(rx) + ',' + f1(vr) + ' 0 0 1 ' + f1(p[0] + rx) + ',' + f1(p[1]) + ' A' + f1(rx) + ',' + f1(ry) + ' 0 0 1 ' + f1(p[0] - rx) + ',' + f1(p[1]) + ' Z" fill="' + c.l + '" stroke="' + VFX.edge + '" stroke-width=".5"/>' +
      '<ellipse cx="' + f1(p[0] - rx * 0.22) + '" cy="' + f1(p[1] - vr * 0.5) + '" rx="' + f1(rx * 0.5) + '" ry="' + f1(vr * 0.32) + '" fill="' + c.top + '" opacity=".75"/>' +
      '<ellipse cx="' + f1(p[0] + rx * 0.3) + '" cy="' + f1(p[1] - vr * 0.2) + '" rx="' + f1(rx * 0.4) + '" ry="' + f1(vr * 0.3) + '" fill="' + c.r + '" opacity=".45"/>';
  }
  // the Biodome's glass: a drum of glass r across from z0 to z1 and its cap capH high, in the company's colour, with
  // what is inside it showing through
  function sdGlass(x, y, z0, z1, r, capH, V) {
    var a = Q(x, y, z0), b = Q(x, y, z1), rx = r * RX, ry = r * RY, vr = Math.sqrt(capH * SC * capH * SC + ry * ry);
    Q(x - r, y + r, z0); Q(x + r, y - r, z0); Q(x + r, y + r, z0); Q(x, y, z1 + capH);
    var L0 = f1(a[0] - rx) + ',' + f1(a[1]), R0 = f1(a[0] + rx) + ',' + f1(a[1]), L1 = f1(b[0] - rx) + ',' + f1(b[1]), R1 = f1(b[0] + rx) + ',' + f1(b[1]);
    return '<path d="M' + L0 + ' A' + f1(rx) + ',' + f1(ry) + ' 0 0 0 ' + R0 + ' L' + R1 + ' A' + f1(rx) + ',' + f1(vr) + ' 0 0 0 ' + L1 + ' Z" fill="' + V.glass.l + '" opacity=".68"/>' +
      '<path d="M' + L1 + ' A' + f1(rx) + ',' + f1(vr) + ' 0 0 1 ' + R1 + ' A' + f1(rx) + ',' + f1(ry) + ' 0 0 1 ' + L1 + ' Z" fill="' + V.glass.top + '" opacity=".5"/>' +
      '<path d="M' + L0 + ' A' + f1(rx) + ',' + f1(ry) + ' 0 0 0 ' + R0 + ' L' + R1 + ' A' + f1(rx) + ',' + f1(ry) + ' 0 0 1 ' + L1 + ' Z" fill="none" stroke="' + V.band + '" stroke-width=".9" opacity=".7"/>';
  }
  // windows round an upright drum (u3d.js ringWins): one every step round it; those turned to us are drawn, each
  // flat on the drum where it stands
  function sdRingWins(x, y, r, zc, h, step, ww, V, R, lit) {
    var m = Math.max(6, Math.round(2 * Math.PI * r / step)), o = '';
    for (var i = 0; i < m; i++) {
      var t = i / m * Math.PI * 2, c = Math.cos(t), s = Math.sin(t), on = R() < lit;
      if (c + s < 0.25) continue;
      var px = x + c * (r + 0.014), py = y + s * (r + 0.014), dx = -s * ww / 2, dy = c * ww / 2;
      o += vfWin([[px - dx, py - dy, zc - h / 2], [px + dx, py + dy, zc - h / 2], [px + dx, py + dy, zc + h / 2], [px - dx, py - dy, zc + h / 2]], V, on);
    }
    return o;
  }
  // a ring of points round p, across the way (dx, dy) points
  function sdRingAt(p, dx, dy, rr) {
    var o = [];
    for (var i = 0; i < 16; i++) { var t = i / 16 * Math.PI * 2, u = Math.cos(t) * rr; o.push(Q(p[0] - dy * u, p[1] + dx * u, p[2] + Math.sin(t) * rr)); }
    return o;
  }
  // a square's corners round (cx, cy), the first at angle a0, counter-clockwise
  function sqAt(cx, cy, rad, a0) { return [0, 1, 2, 3].map(function (k) { var a = a0 + k * Math.PI / 2; return [cx + rad * Math.cos(a), cy + rad * Math.sin(a)]; }); }
  // an upright prism on a footprint (counter-clockwise on the map): its sides turned to us shaded as they face, its top
  function sdPrism(fp, z0, z1, c) {
    var o = '', n = fp.length;
    for (var i = 0; i < n; i++) {
      var a = fp[i], b = fp[(i + 1) % n], ex = b[0] - a[0], ey = b[1] - a[1], L = Math.hypot(ex, ey);
      if (L < 1e-6) continue;
      var nx = ey / L, ny = -ex / L;
      if (nx + ny <= 0.01) continue;
      o += pg([[a[0], a[1], z0], [b[0], b[1], z0], [b[0], b[1], z1], [a[0], a[1], z1]], mix(c.l, c.r, Math.max(0, Math.min(1, nx / (Math.max(0, nx) + Math.max(0, ny))))), ' stroke="' + VFX.edge + '" stroke-width=".5"');
    }
    return o + pg(fp.map(function (p) { return [p[0], p[1], z1]; }), c.top, ' stroke="' + VFX.edge + '" stroke-width=".5"');
  }
  // u3d.js srdBase: the platform, a slab with rounded corners; a line of light along its top edge (a second inside
  // it for rims 2) and a softer one round its side; a keel under it, kk of its width. kb is the keel's foot.
  function sdBase(s, h, hull, keel, kk, rims, V) {
    var r = Math.min(0.26, h * 0.4), d = r * 0.25, ks = s * kk, kh = h * 0.5, kr = Math.min(0.12, kh * 0.4);
    var slab = rbox(3, 3, -h, 0, s, s, r, hull) + sdLine(rrPts(3, 3, s, s, r, -45, 135, -h * 0.58), V.soft, 1.1, false, 0.9);
    slab += sdLine(rrPts(3, 3, s - 2 * d, s - 2 * d, r - d, 0, 360, -r * 0.22), V.neon, 1.4, true);
    if (rims > 1) slab += sdLine(rrPts(3, 3, s - 2.8 * r, s - 2.8 * r, r * 0.4, 0, 360, 0.012), V.rim, 1.2, true);
    return { keel: rbox(3, 3, -h - kh + 0.02, -h + 0.02, ks, ks, kr, keel), slab: slab, kb: -h - kh + 0.02 };
  }
  // a solar wing off the platform (u3d.js srdWing): a strut out from its side at angle a, a block where it leaves,
  // panels along it -- rows end to end, lanes side by side -- of nx by ny slate-blue cells in a pale frame, each panel
  // rolled a little about the strut
  function sdWing(a, out, z, len, wid, o) {
    var rows = o.rows || 1, lanes = o.lanes || 1, gap = 0.1, sn = Math.sin(0.08), cs = Math.cos(0.08), nx = o.nx || 3, ny = o.ny || 2;
    var at = function (u, v, dz) { var p = rot(u, v, a); return [3 + p[0], 3 + p[1], z + (dz || 0)]; }, g = '', cells = '', d = '', ax = Math.abs(Math.cos(a)) > 0.5;
    g += line(Q.apply(null, at(out, 0)), Q.apply(null, at(out + gap + len, 0)), VFX.silver.r, 1.6);
    var tb = at(out + 0.04, 0);
    g += cc(tb[0], tb[1], z - 0.08, ax ? 0.14 : 0.2, ax ? 0.2 : 0.14, 0.16, SDX.trim);
    var pl = (len - (rows - 1) * 0.06) / rows, pw = (wid - (lanes - 1) * 0.07) / lanes;
    for (var i = 0; i < rows; i++) for (var j = 0; j < lanes; j++) {
      var u0 = out + gap + i * (pl + 0.06), v0 = -wid / 2 + pw / 2 + j * (pw + 0.07);
      var c = function (u, v) { return at(u0 + u, v0 + v * cs, -v * sn); }, mu = pl / nx, mv = pw / ny, e = Math.min(mu, mv) * 0.05;
      g += pg([c(0, -pw / 2), c(pl, -pw / 2), c(pl, pw / 2), c(0, pw / 2)], SDX.solar.frame, ' stroke="' + VFX.edge + '" stroke-width=".5"');
      for (var p = 0; p < nx; p++) for (var q = 0; q < ny; q++) {
        var a0 = p * mu + e, a1 = (p + 1) * mu - e, b0 = -pw / 2 + q * mv + e, b1 = -pw / 2 + (q + 1) * mv - e;
        cells += pg([c(a0, b0), c(a1, b0), c(a1, b1), c(a0, b1)], SDX.solar.cell);
        for (var t = 1; t < 4; t++) d += seg(c(a0 + (a1 - a0) * t / 4, b0), c(a0 + (a1 - a0) * t / 4, b1)) + seg(c(a0, b0 + (b1 - b0) * t / 4), c(a1, b0 + (b1 - b0) * t / 4));
      }
    }
    return g + cells + '<path d="' + d + '" fill="none" stroke="' + SDX.solar.line + '" stroke-width=".5" opacity=".38"/>';
  }
  // a blue plume from p0 to p1 (on screen), r its radius at the nozzle: a soft glow, the flame, its white core
  function sdPlume(p0, p1, r) {
    var ex = p1[0] - p0[0], ey = p1[1] - p0[1], el = Math.hypot(ex, ey) || 1, ux = ex / el, uy = ey / el, vx = -uy, vy = ux;
    var cone = function (w0, w1, k, tip) {
      var q = [[p0[0] + vx * w0, p0[1] + vy * w0], [p0[0] + ex * k + vx * w1, p0[1] + ey * k + vy * w1], [p0[0] + ex * k + ux * tip, p0[1] + ey * k + uy * tip], [p0[0] + ex * k - vx * w1, p0[1] + ey * k - vy * w1], [p0[0] - vx * w0, p0[1] - vy * w0]];
      q.forEach(function (c) { if (VB) { VB[0] = Math.min(VB[0], c[0]); VB[2] = Math.max(VB[2], c[0]); VB[1] = Math.min(VB[1], c[1]); VB[3] = Math.max(VB[3], c[1]); } });
      return pts(q);
    };
    return '<circle cx="' + f1(p0[0]) + '" cy="' + f1(p0[1]) + '" r="' + f1(r * 1.6) + '" fill="' + VFX.jet + '" opacity=".22"/>' +
      '<polygon class="flame" points="' + cone(r * 1.15, r * 0.35, 1, 0) + '" fill="' + VFX.jet + '"/>' +
      '<polygon points="' + cone(r * 0.8, r * 0.2, 0.75, 0) + '" fill="' + VFX.plume + '" opacity=".28"/>' +
      '<polygon points="' + cone(r * 0.5, r * 0.12, 0.3, 0) + '" fill="' + VFX.core + '" opacity=".55"/>';
  }
  // the engine's jet under a srd station (u3d.js srdJet): a white-blue core and a blue cone of light down from it
  function sdJet(x, y, z, w, len) {
    var p0 = Q(x, y, z), p1 = Q(x, y, z - len), a = w * 0.3 * RX, b = w * 0.05 * RX;
    return '<polygon class="flame" points="' + pts([[p0[0] - a, p0[1]], [p0[0] + a, p0[1]], [p1[0] + b, p1[1]], [p1[0] - b, p1[1]]]) + '" fill="' + VFX.plume + '"/>' +
      '<ellipse cx="' + f1(p0[0]) + '" cy="' + f1(p0[1]) + '" rx="' + f1(w * 0.28 * RX) + '" ry="' + f1(w * 0.28 * RY) + '" fill="' + VFX.core + '"/>';
  }
  // the Ring station's engine (u3d.js srdEngine) out of a side facing +x at (x, y, z), radius r: its housing, its bell,
  // the disc of light in its mouth and the halo round it -- no plume, as in his picture
  function sdEngine(x, y, z, r) {
    var at = function (k) { return [x + k, y, z]; }, o = '', d = Q.apply(null, at(2.3 * r));
    o += tube(at(-0.05 * r), at(1.25 * r), 1, 0, 1.15 * r, SDX.trim, SDX.trim.top);
    o += tube(at(1.3 * r), at(2.3 * r), 1, 0, 0.5 * r, SDX.metal, VFX.core, r);
    o += '<circle class="flame" cx="' + f1(d[0]) + '" cy="' + f1(d[1]) + '" r="' + f1(1.7 * r * RX) + '" fill="' + VFX.plume + '"/>';
    o += '<polygon points="' + pts(sdRingAt(at(2.31 * r), 1, 0, 0.9 * r)) + '" fill="#d6f4ff"/><polygon points="' + pts(sdRingAt(at(2.32 * r), 1, 0, 0.5 * r)) + '" fill="#ffffff"/>';
    VB[2] = Math.max(VB[2], d[0] + 1.7 * r * RX); VB[3] = Math.max(VB[3], d[1] + 1.7 * r * RX);
    return o;
  }
  // a Laser station wing on its arm at angle a (u3d.js lsArm): a strut out of the block, a dark collar, a long pale
  // panel of small cells tilted toward the front, a metal spine down its middle
  function lsWing(a, half, w0, wy, pl, pw, tilt) {
    var sn = Math.sin(tilt), cs = Math.cos(tilt), o = '', d = '', i;
    var at = function (u, v, dz) { var p = rot(u, v, a); return [3 + p[0], 3 + p[1], wy + (dz || 0)]; };
    var c = function (u, v) { return at(w0 + u, v * cs, -v * sn); }, quad = function (u0, u1, v0, v1) { return [c(u0, v0), c(u1, v0), c(u1, v1), c(u0, v1)]; };
    o += line(Q.apply(null, at(half, 0)), Q.apply(null, at(half + 0.33, 0)), VFX.silver.r, 2.2);
    var cb = at(w0 - 0.04, 0);
    o += cc(cb[0], cb[1], wy - 0.07, 0.16, 0.16, 0.14, LSX.rib);
    o += pg(quad(-0.02, pl + 0.02, -pw / 2 - 0.02, pw / 2 + 0.02), LSX.wing.frame, ' stroke="' + VFX.edge + '" stroke-width=".5"') + pg(quad(0.03, pl - 0.03, -pw / 2 + 0.03, pw / 2 - 0.03), LSX.wing.cell);
    for (i = 1; i < 14; i++) { var u = 0.03 + (pl - 0.06) * i / 14; d += seg(c(u, -pw / 2 + 0.03), c(u, pw / 2 - 0.03)); }
    for (i = 1; i < 4; i++) { var v = -pw / 2 + 0.03 + (pw - 0.06) * i / 4; d += seg(c(0.03, v), c(pl - 0.03, v)); }
    o += '<path d="' + d + '" fill="none" stroke="' + LSX.wing.line + '" stroke-width=".6"/>';
    return o + line(Q.apply(null, c(-0.02, 0)), Q.apply(null, c(pl + 0.02, 0)), SDX.metal.l, 1.8);
  }
  // a Data stack wing on side sz (u3d.js's): a strut out of the base, two dark panels drooping a little, slate cells
  // in a lighter frame
  function stWing(sz, bd, bh, K) {
    var wy = -bh * 0.45, sn = Math.sin(sz * 0.2), cs = Math.cos(sz * 0.2), o = '', d = '';
    o += line(Q(3, 3 + sz * bd / 2 * K, wy * K), Q(3, 3 + sz * (bd / 2 + 0.3) * K, wy * K), VFX.silver.r, 2);
    [1, 0].forEach(function (k) {
      var cy = sz * (bd / 2 + 0.62 + k * 0.67), cz = wy - k * 0.065;
      var c = function (u, v) { return [3 + u * K, 3 + (cy + v * cs) * K, (cz - v * sn) * K]; };
      o += pg([c(-0.425, -0.31), c(0.425, -0.31), c(0.425, 0.31), c(-0.425, 0.31)], '#3a4455', ' stroke="' + VFX.edge + '" stroke-width=".5"');
      for (var p = 0; p < 4; p++) for (var q = 0; q < 3; q++) {
        var u0 = -0.41 + p * 0.205, v0 = -0.295 + q * 0.197;
        o += pg([c(u0 + 0.012, v0 + 0.012), c(u0 + 0.193, v0 + 0.012), c(u0 + 0.193, v0 + 0.185), c(u0 + 0.012, v0 + 0.185)], '#1f2836');
        d += seg(c(u0 + 0.07, v0 + 0.012), c(u0 + 0.07, v0 + 0.185)) + seg(c(u0 + 0.13, v0 + 0.012), c(u0 + 0.13, v0 + 0.185));
      }
    });
    return o + '<path d="' + d + '" fill="none" stroke="#3d4859" stroke-width=".5"/>';
  }
  // a Data stack engine at the stern (+x) from (x, y, z): a dark collar, a silver can, a bell, a white-hot nozzle and
  // a blue plume, K times its own size
  function stEngine(x, y, z, K) {
    var at = function (k) { return [x + k * K, y, z]; }, o = '';
    o += tube(at(0), at(0.06), 1, 0, 0.22 * K, VFX.dark, VFX.dark.top) + tube(at(0.05), at(0.35), 1, 0, 0.19 * K, VFX.silver, VFX.silver.top);
    o += tube(at(0.34), at(0.56), 1, 0, 0.105 * K, SDX.trim, VFX.core, 0.21 * K);
    return o + sdPlume(Q.apply(null, at(0.56)), Q.apply(null, at(1.3)), 0.19 * K * RX);
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
    var b = (SKIN[o.skin] || SKIN.tower)(n, acc, rng(o.seed || 7)), rr = b.foot ? ringOf(b.foot) : Math.max(2.0, Math.min(b.ext, 4.5) * 0.72), zb = b.bot - 0.4;
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
  // His orbit lines as u3d.js has them (UVLINES there, read off his picture): radius, the line's colour on screen, its
  // width on his 1533-wide frame, dotted, how much of a halo. A copy, as the two files share no module; change both.
  var LINES = [
    { r: 205.5, hex: '#548f9d', px: 2.4 }, { r: 203, hex: '#80c8d0', px: 3, glow: 0.5 }, { r: 194, hex: '#2a4a52', px: 2.6, dots: 1 },
    { r: 183, hex: '#1f3239', px: 2.2 }, { r: 178, hex: '#23394b', px: 2.4 },
    { r: 154, hex: '#3d526a', px: 3.4, glow: 0.2 },
    { r: 136, hex: '#426862', px: 3, glow: 0.15 },
    { r: 120, hex: '#263a48', px: 2.4, dots: 1 },
    { r: 105, hex: '#8fb8b2', px: 4.4, glow: 0.45 }, { r: 100, hex: '#3f7d71', px: 4, glow: 0.3 },
    { r: 90, hex: '#3e706d', px: 2.4, dots: 1 }
  ];
  // a line px wide on his frame, in the map's units: u3d.js's band is .84 px units across, two thirds of it lit, and a
  // unit of the disc is about 21 of the map's across its lines
  var LW = 0.57 * 21;
  // where the orbits are lit: brightest on the far left of the first look, dim on the right (u3d.js lanes()' peak)
  var PEAK = AZ - Math.PI / 2 - 0.45;
  // the colour space u3d.js mixes in: sRGB to linear and back
  function lin(v) { v /= 255; return v <= 0.04045 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4); }
  function srgb(v) { v = Math.max(0, Math.min(1, v)); return 255 * (v <= 0.0031308 ? v * 12.92 : 1.055 * Math.pow(v, 1 / 2.4) - 0.055); }
  // his dim side is grey as well as dark: a line's colour there loses most of its hue (u3d.js dimOf)
  function dimOf(hex) {
    var c = rgbOf(hex).map(lin), l = 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2];
    return hexOf(c.map(function (v) { return srgb((l + (v - l) * 0.35) * 0.42); }));
  }
  // a stroke lit along the orbit as his are: a gradient across the map from its lit point to the opposite one, the
  // light falling off as u3d.js's shade() does (k scales it, pow sharpens it, as its glow bands do)
  function laneGrad(id, r, hex, k, pow) {
    var a = disc(r, PEAK), b = disc(r, PEAK + Math.PI), hi = hex, lo = dimOf(hex), out = '';
    for (var i = 0; i <= 6; i++) { var t = i / 6, c = mix(lo, hi, Math.pow(1 - t, 1.3 * (pow || 1))); out += '<stop offset="' + f1(t * 100) + '%" stop-color="' + c + '" stop-opacity="' + (k == null ? 1 : k) + '"/>'; }
    return '<linearGradient id="' + id + '" gradientUnits="userSpaceOnUse" x1="' + f1(a[0]) + '" y1="' + f1(a[1]) + '" x2="' + f1(b[0]) + '" y2="' + f1(b[1]) + '">' + out + '</linearGradient>';
  }
  // an orbit on the map: an ellipse round the middle, as a path (so a dash pattern runs along it)
  function orbitPath(r) {
    var c = gp(0, 0, 0), rx = r * RX, ry = r * RY;
    return 'M' + f1(c[0] - rx) + ',' + f1(c[1]) + ' a' + f1(rx) + ',' + f1(ry) + ' 0 1 0 ' + f1(rx * 2) + ',0 a' + f1(rx) + ',' + f1(ry) + ' 0 1 0 ' + f1(-rx * 2) + ',0';
  }
  // round dots along an orbit, one every `gap` of the disc's units (u3d.js's dotted lines)
  function dotsOf(r, gap) {
    var a = r * RX, b = r * RY, per = Math.PI * (3 * (a + b) - Math.sqrt((3 * a + b) * (a + 3 * b))), n = Math.round(r * Math.PI * 2 / gap);
    return ' stroke-dasharray="0.01 ' + f1(per / n) + '" stroke-linecap="round"';
  }
  // the soft lights the map draws: a radial gradient from a colour to nothing, through [offset, opacity] stops
  function glowDef(id, col, stops) {
    return '<radialGradient id="' + id + '">' + stops.map(function (s) { return '<stop offset="' + s[0] + '" stop-color="' + col + '" stop-opacity="' + s[1] + '"/>'; }).join('') + '</radialGradient>';
  }
  // a star's point of light falls off fast; the glow round Cymetica's ball is u3d.js core()'s (gold, orange, a faint
  // blue at the edge of its light), as broad as the 3D map's bloom spreads it
  var DEFS = '<defs>' + glowDef('uv-fl', '#c8f2ff', [[0, 1], [0.22, 0.35], [0.55, 0.12], [1, 0]]) +
    ['#ffb04a', '#ff9a3c', '#3b9dff'].map(function (c, i) { return glowDef('uv-co' + i, c, [[0, 1], [0.5, 0.45], [1, 0]]); }).join('') + '</defs>';
  function Universe(svg, stage, h) {
    this.svg = svg; this.stage = stage; this.h = h || {};
    svg.innerHTML = DEFS + '<defs class="uvd"></defs><g class="uw"><g class="space"></g><g class="plots"></g><g class="fx"></g></g>';
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
  // The orbits as he drew them (LINES): each a sharp line of light in its own colour, the bright ones in a soft halo,
  // some dotted, all lit on the left and the far side and dim on the right, as the 3D map draws them; the teal light
  // the outer pair sits in; the stars of light on the orbits where his are; Cymetica in the middle
  Universe.prototype.drawSpace = function () {
    var defs = '', out = '', c = gp(0, 0, 0);
    var ell = function (r, w, id, op, extra) {
      return '<ellipse cx="' + f1(c[0]) + '" cy="' + f1(c[1]) + '" rx="' + f1(r * RX) + '" ry="' + f1(r * RY) + '" fill="none" stroke="url(#' + id + ')" stroke-width="' + f1(w) + '"' + (op != null ? ' opacity="' + op + '"' : '') + (extra || '') + '/>';
    };
    // a halo: three strokes, widest faintest, for a band of light that fades to its edges
    var halo = function (r, half, id, k) { return [1, 0.62, 0.3].map(function (q) { return ell(r, half * 2 * 21 * q, id, f1(k * 100) / 100); }).join(''); };
    defs += laneGrad('uvl-teal', 204.5, '#00262e', 1, 2.5);
    out += halo(204.5, 9, 'uvl-teal', 0.4);
    LINES.forEach(function (L, k) {
      if (!L.glow) return;
      defs += laneGrad('uvl-g' + k, L.r, L.hex, 1, 2);
      out += halo(L.r, 2.5 + L.glow * 3, 'uvl-g' + k, 0.22 * L.glow * 0.9);
    });
    LINES.forEach(function (L, k) {
      defs += laneGrad('uvl' + k, L.r, L.hex);
      out += L.dots ? '<path d="' + orbitPath(L.r) + '" fill="none" stroke="url(#uvl' + k + ')" stroke-width="' + f1(L.px * LW * 1.1) + '"' + dotsOf(L.r, 2.1) + '/>' : ell(L.r, L.px * LW, 'uvl' + k);
    });
    // his stars of light on the orbits: a white-hot point, a long horizontal glint, a shorter upright one
    [[203, -1.0, 24, 1.5], [136, 0.42, 9, 0.9], [178, -1.47, 8, 0.7], [203, 2.3, 16, 1.2], [105, 3.9, 13, 1.1]].forEach(function (q) {
      var p = disc(q[0], q[1]), s = q[2] * RX * 0.5, o = Math.min(1, q[3] * 0.7);
      out += '<g opacity="' + f1(o * 100) / 100 + '"><circle cx="' + f1(p[0]) + '" cy="' + f1(p[1]) + '" r="' + f1(s) + '" fill="url(#uv-fl)"/>' +
        '<ellipse cx="' + f1(p[0]) + '" cy="' + f1(p[1]) + '" rx="' + f1(s * 1.3) + '" ry="' + f1(s * 0.05) + '" fill="#e1fcff" opacity=".7"/>' +
        '<ellipse cx="' + f1(p[0]) + '" cy="' + f1(p[1]) + '" rx="' + f1(s * 0.05) + '" ry="' + f1(s * 0.6) + '" fill="#e1fcff" opacity=".5"/>' +
        '<circle cx="' + f1(p[0]) + '" cy="' + f1(p[1]) + '" r="' + f1(s * 0.09) + '" fill="#ffffff"/></g>';
    });
    this.svg.querySelector('.uvd').innerHTML = defs + this.coreDefs();
    out += this.core();
    this.gSpace.innerHTML = out;
    this.paintBall();
  };
  // Cymetica's ball: each of its images gets its painting as soon as that is made (at once once it has been)
  Universe.prototype.paintBall = function () {
    Array.prototype.forEach.call(this.gSpace.querySelectorAll('image.uvball'), function (im) {
      var k = im.getAttribute('data-k');
      paintURL(k === 'glow' ? k : +k, function (u) { if (u) im.setAttribute('href', u); else im.remove(); });
    });
  };
  // Cymetica, as the 3D map draws it after the operator's picture of a collision (2026-10-19, images/12: "ma vypadat
  // takto presne"; before it, of the sun: "to nemaji byt letajici krouzky, to ma vse jakoby zevnitr vychazet"): a ball
  // woven of plasma arcs round a white-hot heart, the very painting the 3D map lays over its heart (colliderPaint), its
  // beams of blue-white and gold and its sparks flying out of it, a faint glow round it -- nothing flies round it.
  // Round it on the plane, still, the orrery's cyan rings and pale arcs. Sizes are u3d.js's (UVSUN: the ball drawn k
  // times its own size, y above the plane), units the plane's: his rings reach 60.
  var SUN = { k: 1.7, y: 6, ball: 16.5, disc: 15 };
  var CORE = {
    // the orrery's rings on the plane: radius, half width, colour, dots round it
    lines: [[60, 0.9, '#a5d8e6'], [57.5, 0.7, '#4f8a9c'], [53, 0.7, '#77c2d0'], [42, 0.8, '#4e8d9f', 90], [36.5, 0.8, '#81cbdb']],
    arcs: [[33.5, 0.55, [[0.2, 1.5], [2.2, 3.3], [4.1, 5.6]]], [56.5, 0.5, [[0.9, 2.6], [3.4, 4.4], [5.0, 6.0]]]],
    // the glow round the ball: across in the ball's own units, and how bright
    corona: [[44, 0.07], [70, 0.035], [100, 0.025]],
    // the beams: their angle on the first look's screen, how far toward it, length in the ball's units, colour
    jets: [[36, 0.1, 34, '#9fd0ff'], [216, -0.1, 33, '#8fc4ff'], [166, 0.2, 29, '#ffb347'], [348, -0.25, 27, '#ffa22e'], [300, 0.3, 21, '#6fb0ff'], [118, -0.3, 20, '#ffc266'], [78, 0.4, 16, '#ffd28a'], [258, 0.35, 18, '#ff9a22']]
  };
  // where the ball's middle is on the map, and its banner's height over the plane's middle in the map's units: as the
  // 3D map hangs it, nine tenths of the ball's light up the screen from its heart
  function sunAt() { return gp(0, SUN.y, 0); }
  CORE.banner = SUN.y * SC + SUN.ball * SUN.k * 0.9 * RX;
  // Cymetica's ball, painted as the operator's picture of a collision has it: u3d.js colliderTex, line for line, so
  // that a seed paints the same ball on both maps (it draws from R in u3d.js's order). Arcs of plasma lying round a
  // sphere -- gold most, orange, blue and white between, brighter on the near side -- over a white-hot heart that runs
  // pink and then blue inside, a gold glow along its edge, two blue-white beams and two gold ones through it, a burst
  // of spikes, sparks and streaks out of the middle. A 1024 canvas, the ball the middle 0.6 of it; one per seed.
  var PAINT = {};
  CO.colliderPaint = function (seed) {
    if (PAINT[seed]) return PAINT[seed];
    var cv = document.createElement('canvas'), W = 1024, R = rng(seed * 7 + 3), i;
    cv.width = cv.height = W;
    var g = cv.getContext('2d'), c = W / 2, rad = W * 0.3;
    g.globalCompositeOperation = 'lighter';
    var heart = g.createRadialGradient(c, c, 0, c, c, rad * 1.1);
    [[0, 'rgba(255,255,255,1)'], [0.015, 'rgba(255,230,246,.9)'], [0.06, 'rgba(255,74,176,.75)'], [0.12, 'rgba(176,70,240,.5)'], [0.2, 'rgba(60,96,255,.45)'], [0.38, 'rgba(255,140,40,.12)'], [0.75, 'rgba(255,130,40,.05)'], [1, 'rgba(255,130,40,0)']].forEach(function (s) { heart.addColorStop(s[0], s[1]); });
    g.fillStyle = heart; g.fillRect(0, 0, W, W);
    var V = function () { var u = R() * 2 - 1, th = R() * Math.PI * 2, s = Math.sqrt(1 - u * u); return [Math.cos(th) * s, u, Math.sin(th) * s]; };
    var cross = function (a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; };
    var nrm = function (a) { var l = Math.hypot(a[0], a[1], a[2]); return a.map(function (x) { return x / l; }); };
    // an arc of a circle round o in a random plane, drawn in four pieces each as bright as its depth: a wide soft
    // pass under a crisp one
    var arc = function (o, rr, len, wa, cols, w, dim) {
      var n = V(), u = nrm(cross(n, Math.abs(n[1]) < 0.9 ? [0, 1, 0] : [1, 0, 0])), v = cross(n, u), t0 = R() * Math.PI * 2, wf = 3 + R() * 6, ph = R() * 6, col = cols[Math.floor(R() * cols.length)], p = [], s, q;
      for (s = 0; s <= 48; s++) {
        var t = t0 + len * s / 48, k = rr * (1 + wa * Math.sin(t * wf + ph)), pt = [0, 1, 2].map(function (j) { return o[j] + (Math.cos(t) * u[j] + Math.sin(t) * v[j]) * k; });
        p.push([c + pt[0], c - pt[1], Math.max(-1, Math.min(1, pt[2] / rad))]);
      }
      for (q = 0; q < 4; q++) {
        var a0 = q * 12, a1 = a0 + 12, b = (0.3 + 0.7 * ((p[a0][2] + p[a1][2]) / 2 + 1) / 2) * dim;
        [[w * 3.2, 0.06 * b], [w, 0.92 * b]].forEach(function (L) {
          g.strokeStyle = 'rgba(' + col.join(',') + ',' + L[1].toFixed(3) + ')'; g.lineWidth = L[0]; g.lineCap = 'round';
          g.beginPath(); g.moveTo(p[a0][0], p[a0][1]); for (var m = a0 + 1; m <= a1; m++) g.lineTo(p[m][0], p[m][1]); g.stroke();
        });
      }
    };
    var GOLD = [[255, 150, 36], [255, 150, 36], [255, 178, 70], [255, 112, 18], [255, 196, 96]], BLUE = [[36, 104, 255], [60, 130, 255], [96, 160, 255], [150, 200, 255]];
    var DEEP = [[255, 84, 180], [150, 84, 255], [60, 110, 255], [40, 90, 255], [40, 90, 255], [255, 100, 60]];
    // a gold glow along the ball's edge, where the weave is densest and brightest
    var rim = g.createRadialGradient(c, c, rad * 0.72, c, c, rad * 1.16);
    rim.addColorStop(0, 'rgba(255,170,70,0)'); rim.addColorStop(0.55, 'rgba(255,170,70,.26)'); rim.addColorStop(1, 'rgba(255,150,50,0)'); g.fillStyle = rim; g.fillRect(0, 0, W, W);
    // inside: pink, violet and blue swirls round the heart; through the ball: gold and blue loops; on its shell: the
    // arcs that draw its round edge; a few big loops bulging out past it
    for (i = 0; i < 80; i++) arc(V().map(function (x) { return x * rad * R() * 0.3; }), rad * (0.12 + R() * 0.32), 2 + R() * 3.5, 0.1 * R(), DEEP, 2.2 + R() * 2.8, 0.85);
    for (i = 0; i < 56; i++) arc(V().map(function (x) { return x * rad * R() * 0.5; }), rad * (0.25 + R() * 0.35), 1.6 + R() * 3.2, 0.08 * R(), R() < 0.5 ? GOLD : BLUE, 2.4 + R() * 2.8, 0.9);
    for (i = 0; i < 110; i++) arc([0, 0, 0], rad * (0.86 + R() * 0.16), 0.6 + R() * 1.9, 0.04 * R(), R() < 0.6 ? GOLD : BLUE, 2.4 + R() * 2.8, 1);
    for (i = 0; i < 18; i++) arc(V().map(function (x) { return x * rad * (0.4 + R() * 0.25); }), rad * (0.5 + R() * 0.3), 1.4 + R() * 2.2, 0.05 * R(), R() < 0.6 ? GOLD : BLUE, 2.5 + R() * 2.2, 0.95);
    // the beams: two broad blue-white ones on one diagonal through the heart, two gold ones across it, tapering out
    // past the ball, each a wide soft pass under a hot narrow one
    [[-0.62 + R() * 0.1, '170,206,255', 26], [2.52 + R() * 0.1, '170,206,255', 22], [3.0 + R() * 0.2, '255,186,90', 20], [0.12 + R() * 0.2, '255,176,80', 16]].forEach(function (B) {
      var rgb = B[1], wd = B[2];
      g.save(); g.translate(c, c); g.rotate(B[0]);
      [[wd * 2.6, 0.28], [wd, 0.75], [wd * 0.3, 1]].forEach(function (L) {
        var ww = L[0], al = L[1], gr = g.createLinearGradient(rad * 0.1, 0, W * 0.5, 0);
        gr.addColorStop(0, 'rgba(' + rgb + ',' + al + ')'); gr.addColorStop(0.6, 'rgba(' + rgb + ',' + (al * 0.55).toFixed(2) + ')'); gr.addColorStop(1, 'rgba(' + rgb + ',0)');
        g.fillStyle = gr; g.beginPath(); g.moveTo(rad * 0.1, -ww / 2); g.lineTo(W * 0.5, 0); g.lineTo(rad * 0.1, ww / 2); g.closePath(); g.fill();
      });
      g.restore();
    });
    // the burst: spikes of light out of the ball's edge, gold and blue-white
    for (i = 0; i < 64; i++) {
      var a = R() * Math.PI * 2, r0 = rad * (0.55 + R() * 0.35), r1 = rad * (1.15 + R() * R() * 0.55), wd = 3 + R() * 9, rgb = R() < 0.6 ? '255,178,74' : R() < 0.6 ? '150,196,255' : '255,240,220';
      g.save(); g.translate(c, c); g.rotate(a);
      var gs = g.createLinearGradient(r0, 0, r1, 0); gs.addColorStop(0, 'rgba(' + rgb + ',0)'); gs.addColorStop(0.25, 'rgba(' + rgb + ',' + (0.35 + R() * 0.4).toFixed(2) + ')'); gs.addColorStop(1, 'rgba(' + rgb + ',0)');
      g.fillStyle = gs; g.beginPath(); g.moveTo(r0, -wd); g.lineTo(r1, 0); g.lineTo(r0, wd); g.closePath(); g.fill(); g.restore();
    }
    // knots of light in the weave; sparks everywhere; fine streaks flying out of the middle
    var dot = function (x, y, r, rgb, al) { var gr = g.createRadialGradient(x, y, 0, x, y, r); gr.addColorStop(0, 'rgba(' + rgb + ',' + al + ')'); gr.addColorStop(1, 'rgba(' + rgb + ',0)'); g.fillStyle = gr; g.fillRect(x - r, y - r, r * 2, r * 2); };
    for (i = 0; i < 60; i++) { var ad = R() * Math.PI * 2, rd = rad * (0.35 + R() * 0.65); dot(c + Math.cos(ad) * rd, c + Math.sin(ad) * rd, 6 + R() * 14, R() < 0.7 ? '255,228,170' : '200,224,255', 0.45 + R() * 0.4); }
    for (i = 0; i < 1500; i++) { var ap = R() * Math.PI * 2, rp = rad * (0.45 + R() * 1.15), sp = 0.6 + R() * 1.8; g.fillStyle = (R() < 0.78 ? 'rgba(255,196,100,' : 'rgba(190,220,255,') + (0.3 + R() * 0.65).toFixed(2) + ')'; g.fillRect(c + Math.cos(ap) * rp - sp / 2, c + Math.sin(ap) * rp - sp / 2, sp, sp); }
    for (i = 0; i < 320; i++) {
      var at = R() * Math.PI * 2, rt = rad * (0.2 + R() * 1.2), lt2 = 10 + R() * R() * 120, rgbt = R() < 0.62 ? '255,190,96' : R() < 0.5 ? '255,248,236' : '130,180,255';
      var x0 = c + Math.cos(at) * rt, y0 = c + Math.sin(at) * rt, x1 = c + Math.cos(at) * (rt + lt2), y1 = c + Math.sin(at) * (rt + lt2), gt = g.createLinearGradient(x0, y0, x1, y1);
      gt.addColorStop(0, 'rgba(' + rgbt + ',0)'); gt.addColorStop(0.5, 'rgba(' + rgbt + ',' + (0.3 + R() * 0.5).toFixed(2) + ')'); gt.addColorStop(1, 'rgba(' + rgbt + ',0)');
      g.strokeStyle = gt; g.lineWidth = 0.9 + R() * 1.6; g.beginPath(); g.moveTo(x0, y0); g.lineTo(x1, y1); g.stroke();
    }
    return (PAINT[seed] = cv);
  };
  // The painting as an image the map can show, made once and kept: the ball of a seed, or (glow) seed 1 blurred and
  // brightened, the glow the 3D map puts under it (none where a canvas cannot blur). Encoded off the main thread
  // where the browser can (toBlob), as the flat map is where a weak computer goes: three paintings encoded at once
  // there would stall its first look. cb gets the URL, or null.
  var PAINTURL = {}, PAINTWAIT = {};
  function paintURL(key, cb) {
    if (PAINTURL[key] !== undefined) return cb(PAINTURL[key]);
    if (PAINTWAIT[key]) return PAINTWAIT[key].push(cb);
    PAINTWAIT[key] = [cb];
    var done = function (u) { PAINTURL[key] = u; var q = PAINTWAIT[key]; delete PAINTWAIT[key]; q.forEach(function (f) { f(u); }); };
    var src = CO.colliderPaint(key === 'glow' ? 1 : key), cv = src;
    if (key === 'glow') {
      cv = document.createElement('canvas'); cv.width = cv.height = src.width;
      var g = cv.getContext('2d'); g.filter = 'blur(15px) brightness(1.5)';
      if (g.filter !== 'blur(15px) brightness(1.5)') return done(null);
      g.drawImage(src, 0, 0);
    }
    try {
      if (cv.toBlob) cv.toBlob(function (b) { done(b ? URL.createObjectURL(b) : null); }, 'image/png');
      else done(cv.toDataURL('image/png'));
    } catch (e) { done(null); }
  }
  // a beam's light along it: none at its root, full a quarter of the way out, gone at its tip (u3d.js jetTex)
  Universe.prototype.coreDefs = function () {
    var h = sunAt(), out = '';
    CORE.jets.forEach(function (j, i) {
      var t = j[0] * Math.PI / 180, L = j[2] * SUN.k * RX / Math.sqrt(1 + j[1] * j[1]), e = [h[0] + Math.cos(t) * L, h[1] - Math.sin(t) * L];
      out += '<linearGradient id="uvj' + i + '" gradientUnits="userSpaceOnUse" x1="' + f1(h[0]) + '" y1="' + f1(h[1]) + '" x2="' + f1(e[0]) + '" y2="' + f1(e[1]) + '">' +
        [[0, 0], [12, 0.25], [24, 1], [50, 0.55], [85, 0.1], [100, 0]].map(function (s) { return '<stop offset="' + s[0] + '%" stop-color="' + j[3] + '" stop-opacity="' + s[1] + '"/>'; }).join('') + '</linearGradient>';
    });
    return out;
  };
  Universe.prototype.core = function () {
    var c = gp(0, 0, 0), h = sunAt(), R = rng(77), out = '<g class="core-plot" data-id="core">', i;
    // the orrery's rings and arcs on the plane
    CORE.lines.forEach(function (q) {
      out += '<ellipse cx="' + f1(c[0]) + '" cy="' + f1(c[1]) + '" rx="' + f1(q[0] * RX) + '" ry="' + f1(q[0] * RY) + '" fill="none" stroke="' + q[2] + '" stroke-width="' + f1(q[1] * 2 * 0.68 * 21) + '"' + (q[3] ? dotsOf(q[0], q[0] * Math.PI * 2 / q[3]) : '') + '/>';
    });
    CORE.arcs.forEach(function (q) {
      q[2].forEach(function (ab) {
        var l = [];
        for (var t = ab[0]; t <= ab[1] + 1e-6; t += 0.06) l.push(disc(q[0], t + Math.PI / 2));
        out += '<polyline points="' + pts(l) + '" fill="none" stroke="#93a0a8" stroke-width="' + f1(q[1] * 2 * 21) + '" opacity=".55"/>';
      });
    });
    // under the ball, each added to the light under it as the 3D map adds them: the faint glow round it; the beams, a
    // wide soft cone round a narrow hot one, the two long blue-white ones broad; the sparks flying out of its heart --
    // golden mostly, some white-blue, most along the beams, the rest every way, some twinkling; one coming straight
    // at us would sit on the ball like a speck of dust, so those fade
    var glow = '', beams = '', sparks = '';
    CORE.corona.forEach(function (q, k) {
      glow += '<circle cx="' + f1(h[0]) + '" cy="' + f1(h[1]) + '" r="' + f1(q[0] / 2 * SUN.k * RX) + '" fill="url(#uv-co' + k + ')" opacity="' + f1(Math.min(1, q[1] * 5) * 100) / 100 + '"/>';
    });
    CORE.jets.forEach(function (j, k) {
      var t = j[0] * Math.PI / 180, L = j[2] * SUN.k * RX / Math.sqrt(1 + j[1] * j[1]), ux = Math.cos(t), uy = -Math.sin(t), vx = -uy, vy = ux, wk = j[2] > 30 ? 1.8 : 1;
      [[1.3 * wk, 0.22], [0.3 * wk, 0.7]].forEach(function (q) {
        var w0 = q[0] * SUN.k * RX, w1 = w0 * 0.06;
        beams += '<polygon points="' + pts([[h[0] + vx * w0, h[1] + vy * w0], [h[0] + ux * L + vx * w1, h[1] + uy * L + vy * w1], [h[0] + ux * L - vx * w1, h[1] + uy * L - vy * w1], [h[0] - vx * w0, h[1] - vy * w0]]) + '" fill="url(#uvj' + k + ')" opacity="' + q[1] + '"/>';
      });
    });
    for (i = 0; i < 220; i++) {
      var jet = R() < 0.55 ? CORE.jets[Math.floor(R() * CORE.jets.length)] : null, toward = jet ? jet[1] / Math.sqrt(1 + jet[1] * jet[1]) : R() * 2 - 1;
      var a = jet ? jet[0] * Math.PI / 180 + (R() - 0.5) * 0.3 : R() * Math.PI * 2, life = R();
      var dist = (2 + life * (jet ? jet[2] * (0.55 + R() * 0.45) : 10 + R() * 18)) * SUN.k * RX * Math.sqrt(1 - toward * toward);
      var op = (1 - life) * (1 - Math.min(1, Math.max(0, (toward - 0.8) / 0.17)));
      if (op < 0.08) continue;
      var col = R() < 0.78 ? (R() < 0.5 ? '#ffb94a' : '#ffdf8a') : '#cfe9ff', tw = R() < 0.4;
      sparks += '<circle' + (tw ? ' class="beacon" style="animation-delay:-' + (R() * 1.8).toFixed(2) + 's"' : '') + ' cx="' + f1(h[0] + Math.cos(a) * dist) + '" cy="' + f1(h[1] - Math.sin(a) * dist) + '" r="' + f1(5 + R() * 9) + '" fill="' + col + '" opacity="' + f1(Math.min(1, op * 1.3) * 100) / 100 + '"/>';
    }
    out += [glow, beams, sparks].map(function (l) { return '<g style="mix-blend-mode:screen">' + l + '</g>'; }).join('');
    // the ball: the 3D map's painting at its size and place -- the ball as wide as u3d.js makes it (UVSUN.disc times
    // k across its radius), the painting 600/360 of the ball -- seed 1 over its blurred glow, seed 2 faint over both,
    // laid over the map as the 3D lays it (its overlay blends inside the banners' own layer, so on the map it simply
    // covers: added to the beams' light the weave would wash out to white). Still: the 3D's pair turns and flickers,
    // but on the flat map that would repaint the whole map every frame, on the weak computers it is for.
    // (drawSpace gives each image its painting once it is made: paintBall)
    var half = SUN.disc * SUN.k * RX * 600 / 360, img = function (key, op) {
      return '<image class="uvball" data-k="' + key + '" x="' + f1(h[0] - half) + '" y="' + f1(h[1] - half) + '" width="' + f1(half * 2) + '" height="' + f1(half * 2) + '"' + (op != null ? ' opacity="' + op + '"' : '') + '/>';
    };
    out += '<g>' + img('glow', 0.85) + img(1) + img(2, 0.35) + '</g>';
    // where a pointer finds it: the ball and a little round it
    out += '<circle cx="' + f1(h[0]) + '" cy="' + f1(h[1]) + '" r="' + f1(34 * RX) + '" fill="transparent"/>';
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
  // a station on its orbit, drawn as much larger than its own decks as the 3D map draws it (u3d.js UVSS), so it
  // reads at a glance orbit by orbit; only ours keeps its ring of light, the others ride their orbits, as in his picture
  var UVSS = 3.8;
  Universe.prototype.plotSVG = function (it) {
    var c = it.c, n = floorsOf(c), priv = !c.public && !it.mine, paused = c.status === 'paused';
    var a = CO.skinArt({ skin: c.skin, accent: c.accent, floors: n, seed: it.mine ? 7 : c.id, priv: priv, you: it.mine, plot: it.mine ? true : false });
    var o = gp(it.pos[0], it.pos[1], it.pos[2]), base = P(3, 3, 0), tx = o[0] - base[0] * UVSS, ty = o[1] - base[1] * UVSS, e = Math.min(a.ext, 4.5);
    var hit = '<polygon class="hit" fill="transparent" points="' + pts([P(3 - e, 3 + e, a.bot), P(3 - e, 3 + e, a.top), P(3 - e, 3 - e, a.top), P(3 + e, 3 - e, a.top), P(3 + e, 3 - e, a.bot), P(3 + e, 3 + e, a.bot)]) + '"/>';
    var top = P(3, 3, a.top + 0.5);
    it.anchor = [tx + top[0] * UVSS, ty + top[1] * UVSS]; it.size = (a.top - a.bot) * SC * UVSS;
    return '<g class="plot' + (priv ? ' priv' : '') + (paused ? ' paused' : '') + (it.mine ? ' mine' : '') + '" data-id="' + c.id + '" transform="matrix(' + UVSS + ' 0 0 ' + UVSS + ' ' + f1(tx) + ' ' + f1(ty) + ')">' + a.svg + hit + '</g>';
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
    if (this.coreEl) list.push({ el: this.coreEl, x: (cp[0] - v.x) * k, y: (cp[1] - CORE.banner - v.y) * k, px: 200, keep: true, core: true, d: 0 });
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
    var e = (CO.uvGalaxy.outer || R1) + 14, c = gp(0, 0, 0);
    var x = c[0] - e * RX, x2 = c[0] + e * RX, y = c[1] - e * RY - 60, y2 = c[1] + e * RY;
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
    var b = this.bounds(), nw = Math.max(700, Math.min(b.w * 1.8, v.w * f)), k = nw / v.w, nh = v.h * k;
    var to = { x: v.x + (v.w - nw) * px, y: v.y + (v.h - nh) * py, w: nw, h: nh };
    if (cx == null) this.tween(to, 260); else { this.tw = 0; this.vb = to; this.apply(); }
  };
  // bring one company to the middle, close up
  Universe.prototype.flyTo = function (id, done, ms) {
    var it = this.find(id); if (!it || !it.anchor) { if (done) done(); return; }
    var c = this.client(), w = Math.max(1100, it.size * 2.6), h = w * c.h / c.w, m = [it.anchor[0], it.anchor[1] + it.size * 0.55];
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
