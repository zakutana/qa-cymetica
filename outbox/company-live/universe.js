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
  // Since 2026-10-21 the orrery holds no companies: it is land for sale. Every orbit carries SLOTS, places a slot at a
  // time is bought on (with ET10, then built on through Build it Better), as many to an orbit as its length gives
  // (36 in all, where the 35 sample companies and ours stood); and the two ADS (CO.ADS), each on its orbit at its
  // angle from the first look's front, so both stand in it. A slot where an ad stands at the first moment is left
  // out (adClear: about an ad's reach, in the plane's units). Items: { kind: 'slot' | 'ad', c: { id, name, accent },
  // orbit, pos }; a slot also has n (its orbit, 1 nearest Cymetica) and owned. Ids are fixed by the seed, so a slot
  // bought keeps its id. (The station code below still takes a company item, kind unset, should companies return.)
  CO.uvGalaxy.adClear = 26;
  // An ad stands ON a slot, one of the 36 ("Orbit 2 · slot 4": the operator bought two, 2026-10-22): CO.ADS names the
  // slot's id, and the ad takes that slot's place on its orbit, so the map holds 34 free slots and two ads.
  // The companies stand again (2026-10-22): each orbit's slots leave gaps, and a company stands in each, the biggest on the
  // inner orbits, ours on the second in front of Cymetica where the camera first looks. So the slots keep their ids and
  // places whatever the companies are, and no company stands on a slot.
  CO.uvPlan = function (mine) {
    var R = rng(2026), items = [], n = 36, tot = 0, own = CO.land ? CO.land() : [], clear = CO.uvGalaxy.adClear;
    var at = function (r, a) { return [Math.sin(a) * r, 0, Math.cos(a) * r]; };
    ORBITS.forEach(function (r) { tot += r; });
    // slots per orbit in proportion to its length, so they stand about as far apart on every one
    var counts = ORBITS.map(function (r) { return Math.max(1, Math.round(r / tot * n)); }), d = n - counts.reduce(function (a, b) { return a + b; }, 0);
    for (var i = counts.length - 1; d !== 0; i = (i + counts.length - 1) % counts.length) { if (d > 0) { counts[i]++; d--; } else if (counts[i] > 1) { counts[i]--; d++; } }
    var cand = [];
    ORBITS.forEach(function (r, o) {
      var m = counts[o], a0 = R() * Math.PI * 2;
      for (var j = 0; j < m; j++) {
        var a = a0 + (j + (R() - 0.5) * 0.4) / m * Math.PI * 2;
        cand.push({ n: o + 1, id: 'slot-' + (o + 1) + '-' + (j + 1), r: r, a: a, pos: at(r, a) });
      }
    });
    var ads = [];
    (CO.ADS_ON ? CO.ADS || [] : []).forEach(function (ad) {
      var s = cand.filter(function (x) { return x.id === ad.slot; })[0]; if (!s) return;
      var it = { kind: 'ad', ad: ad, slotId: s.id, n: s.n, c: { id: 'ad-' + ad.key, name: ad.name, accent: ad.accent }, orbit: { r: s.r, a: s.a, w: CO.uvGalaxy.omega(s.r) }, pos: s.pos };
      ads.push(it); items.push(it);
    });
    var list = CO.UNIVERSE.slice().sort(function (a, b) { return floorsOf(b) - floorsOf(a) || a.id - b.id; }), k = 0, TAU = Math.PI * 2;
    ORBITS.forEach(function (r, o) {
      var on = cand.filter(function (s) { return s.n === o + 1; }), gaps = on.map(function (s, j) { var nx = on[(j + 1) % on.length]; return (s.a + (nx.a + (j + 1 === on.length ? TAU : 0))) / 2; });
      var mi = -1;
      if (o === 1 && mine) {
        var want = AZ + 0.55, dist = function (g) { var d = Math.abs(((g - want) % TAU + TAU) % TAU); return Math.min(d, TAU - d); };
        gaps.forEach(function (g, j) { if (mi < 0 || dist(g) < dist(gaps[mi])) mi = j; });
      }
      gaps.forEach(function (a, j) {
        var me = j === mi, c = me ? mine : list[k++]; if (!c) return;
        items.push({ c: c, mine: me, orbit: { r: r, a: a, w: CO.uvGalaxy.omega(r) }, pos: at(r, a) });
      });
    });
    cand.forEach(function (s) {
      if (ads.some(function (x) { return x.slotId === s.id || Math.hypot(x.pos[0] - s.pos[0], x.pos[2] - s.pos[2]) < clear; })) return;
      items.push({ kind: 'slot', n: s.n, owned: own.indexOf(s.id) >= 0, c: { id: s.id, name: own.indexOf(s.id) >= 0 ? 'Your land' : 'Free slot', accent: 'green' },
        orbit: { r: s.r, a: s.a, w: CO.uvGalaxy.omega(s.r) }, pos: s.pos });
    });
    return items;
  };
  // a lively first look: some decks already at work (companies only: land and ads have no decks)
  CO.uvSeed = function (items, live) {
    items.forEach(function (it) {
      if (it.kind || it.mine || it.c.status === 'paused') return;
      var n = floorsOf(it.c), R = rng(it.c.id * 3);
      live[it.c.id] = R() < 0.55 ? [Math.floor(R() * n)] : [];
    });
  };
  // one beat of the sample companies: up to three change which decks work; the picture answers what changed
  CO.uvStep = function (items, live) {
    var pool = items.filter(function (it) { return !it.kind && !it.mine && it.c.status !== 'paused'; }), out = [];
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
    var pub = 0, work = 0, free = 0, owned = 0, ads = 0, cos = 0;
    items.forEach(function (it) {
      if (it.kind === 'slot') { if (it.owned) owned++; else free++; return; }
      if (it.kind === 'ad') { if (!it.ad.house) ads++; return; }   // Cymetica's own Promo Market is not a product
      cos++;
      if (it.c.public) pub++;
      work += (it.mine ? (it.c.working || []) : (live[it.c.id] || [])).length;
    });
    return { companies: cos, public: pub, working: work, free: free, owned: owned, ads: ads };
  };
  // a slot's address and an ad's page, for the tooltip and the cards
  CO.uvSlotName = function (it) { return 'Orbit ' + it.n + ' · slot ' + String(it.slotId || it.c.id).split('-').pop(); };
  // the plate over an ad, and over a slot of your own; a free slot has none (its tooltip says what it is). undefined:
  // a company, whose plate each map draws itself. Both maps use this, so the two say the same.
  CO.uvPlate = function (it) {
    if (it.kind === 'ad') return { cls: 'b3 ad', html: '<span class="rib">' + esc(String(it.c.name).toUpperCase()) + '</span><span class="teth"></span>' };
    if (it.kind === 'slot') return it.owned ? { cls: 'b3 land', html: '<span class="rib">YOUR LAND</span><span class="teth"></span>' } : null;
    return undefined;
  };
  CO.uvAdPath = function (ad) { return ad.url.replace(/^https?:\/\//, '').replace(/\?.*$/, ''); };
  CO.uvTip = function (id, it, live) {
    if (id === 'core') return '<b class="c">Cymetica</b><br>The land round it is for sale.';
    if (!it) return '';
    if (it.kind === 'ad') {
      return '<div class="uvt"><b style="color:' + CO.accentHex(it.c.accent) + '">' + esc(it.c.name) + '</b><span>' + esc(CO.uvSlotName(it)) + '</span></div><div><span class="c">Click to look closer →</span></div>';
    }
    if (it.kind === 'slot') {
      return it.owned
        ? '<div class="uvt"><b class="g">Your land</b><span>' + esc(CO.uvSlotName(it)) + '</span></div><div><span class="c">Click to add a building with Build it Better →</span></div>'
        : '<div class="uvt"><b>Free slot</b><span>' + esc(CO.uvSlotName(it)) + '</span></div><div><b class="g">' + CO.LAND_PRICE.toLocaleString('en-US') + '</b> ET10 <span class="dim">placeholder price</span></div><div><span class="c">Click to buy →</span></div>';
    }
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
  // Each returns its picture, the top and bottom it reaches (in decks' units) and how far it reaches out (ext). They
  // are drawn further down, after the parts they are made of, as stations.js builds them in 3D.
  var SKIN = {};

  /* The parts every station's picture is drawn with. Every point goes through Q, so the picture knows how far it
   * reaches and CO.skinSVG frames all of it. */
  var VFC = {}, VB = null;
  // a window's dark slit, a mast's silver, the hairline round a solid's faces
  var VFX = { dark: { top: '#1a1d24', l: '#0d1015', r: '#08090d' }, silver: { top: '#d0d6de', l: '#a9b1bc', r: '#7f8792' }, edge: 'rgba(5,7,10,.5)' };
  function rgbOf(hex) { var v = parseInt(hex.slice(1), 16); return [v >> 16 & 255, v >> 8 & 255, v & 255]; }
  function hexOf(c) { return '#' + c.map(function (v) { return ('0' + Math.round(Math.max(0, Math.min(255, v))).toString(16)).slice(-2); }).join(''); }
  function mix(a, b, t) { var p = rgbOf(a), q = rgbOf(b); return hexOf(p.map(function (v, i) { return v + (q[i] - v) * t; })); }
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
  // a window: a dark slit, and the light in it that its deck turns on
  function vfWin(q, V, on) { return pg(q, VFX.dark.l) + pg(q, V.win, ' class="w' + (on ? ' on' : '') + '"'); }
  // a lamp: the station's colour, pulsing in its halo
  function vfLamp(x, y, z, r, acc) {
    var p = Q(x, y, z); Q(x, y, z + r * 3);
    return '<circle cx="' + f1(p[0]) + '" cy="' + f1(p[1]) + '" r="' + f1(r * SC * 3) + '" fill="' + acc + '" opacity=".22"/>' + beacon(p, acc, f1(r * SC));
  }

  // a line of light through points: a soft wide glow under a sharp core
  function sdLine(l, col, w, closed, op) {
    var p = pts(l.map(function (q) { return Q(q[0], q[1], q[2]); })), tag = closed ? 'polygon' : 'polyline', k = op == null ? 1 : op;
    return '<' + tag + ' points="' + p + '" fill="none" stroke="' + col + '" stroke-width="' + f1(w * 2.8) + '" opacity="' + f1(0.22 * k * 100) / 100 + '" stroke-linejoin="round"/>' +
      '<' + tag + ' points="' + p + '" fill="none" stroke="' + col + '" stroke-width="' + w + '"' + (op != null ? ' opacity="' + op + '"' : '') + ' stroke-linejoin="round" stroke-linecap="round"/>';
  }

  /* ---------------- the seven stations, as stations.js builds them ---------------- */
  // stations.js drew the seven again on 2026-10-20 (Dreadnought, Gateway, Pyramid Carrier, Ring Habitat, Lancer,
  // Citadel, Monolith, under the old keys so a saved company keeps its pick); these are the same stations flat, from its
  // builders' own measures and in its units, n decks each. Its x is the map's x, its z the map's y, its y up, its
  // middle at (3, 3); the map looks along its (1, 1, 1), so a face shows when its normal leans that way. A part that
  // moves there (a wheel, the blocks round the Monolith, the escorts) stands where it starts. Every point goes
  // through Q, so each picture frames what it drew; its ring is as wide as stations.js's b.foot makes the 3D one.
  function nm(p) { return [3 + p[0], 3 + p[2], p[1]]; }
  function nq(p) { return Q(3 + p[0], 3 + p[2], p[1]); }
  function vadd(a, b, k) { return [a[0] + b[0] * k, a[1] + b[1] * k, a[2] + b[2] * k]; }
  function vcross(a, b) { return [a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0]]; }
  function vunit(a) { var l = Math.hypot(a[0], a[1], a[2]) || 1; return [a[0] / l, a[1] / l, a[2] / l]; }
  // two directions across the axis a
  function across(a) { var u = vunit(vcross(a, Math.abs(a[1]) > 0.9 ? [1, 0, 0] : [0, 1, 0])); return [u, vcross(a, u)]; }
  // turned as three.js turns a mesh (its rotation, order XYZ: about z first, then y, then x)
  function eul(p, o) {
    var x = p[0], y = p[1], z = p[2], c, s, t;
    if (o.rz) { c = Math.cos(o.rz); s = Math.sin(o.rz); t = x * c - y * s; y = x * s + y * c; x = t; }
    if (o.ry) { c = Math.cos(o.ry); s = Math.sin(o.ry); t = x * c + z * s; z = -x * s + z * c; x = t; }
    if (o.rx) { c = Math.cos(o.rx); s = Math.sin(o.rx); t = y * c - z * s; z = y * s + z * c; y = t; }
    return [x, y, z];
  }

  // The armour, as the previews show stations.js's materials (mats()): the sun-lit top, the lit left face and the right
  // face in shade (lit only by the cyan rim), read off them at the map's angle, and how much of the company's colour
  // its mats() mixes in. A face between those is lit as the previews' sun and rim light it, its sun capped at the top's
  // (the preview's tone curve flattens what is brighter).
  var NSA = { light: ['#abb2b9', '#777e88', '#30495d', 0.04], mid: ['#717986', '#464c58', '#18293b', 0.07], dark: ['#4f5a62', '#2b3038', '#141c26', 0.12],
    black: ['#1b2028', '#0d1117', '#080b10', 0.12], bronze: ['#968f85', '#6b665d', '#2b2a2c', 0.08], metal: ['#7c8590', '#575d68', '#283545', 0.06] };
  // the plates of light over a tier (stations.js's neonSoft on the Gateway's and the Pyramid's tiers), as they show
  var NSP = { '#00ff88': '#c3e6cc', '#00cfff': '#a5d3df', '#3b82f6': '#7297d6', '#ff4444': '#e67975' };
  var NSUN = vunit([-8, 12, 6]), NRIM = vunit([9, 2, -9]);   // u3d.js Preview's sun and rim, toward the light
  function nsCols(acc) {
    var k = 'ns' + acc;
    if (VFC[k]) return VFC[k];
    var o = {};
    Object.keys(NSA).forEach(function (m) { var a = NSA[m]; o[m] = { t: [mix(a[0], acc, a[3]), mix(a[1], acc, a[3]), mix(a[2], acc, a[3])] }; });
    o.plate = NSP[acc] || mix(acc, '#ffffff', 0.45); o.neon = mix(acc, '#ffffff', 0.45); o.soft = mix(acc, '#ffffff', 0.15);
    o.hot = mix(acc, '#ffffff', 0.72); o.glass = mix('#0e1a26', acc, 0.3); o.win = mix(acc, '#ffffff', 0.35);
    return (VFC[k] = o);
  }
  // material c (or a colour) on a face whose outward normal is n
  function nsShade(c, n) {
    if (typeof c === 'string') return c;
    if (!c.b) {
      var T = rgbOf(c.t[0]).map(lin), L = rgbOf(c.t[1]).map(lin), Rt = rgbOf(c.t[2]).map(lin), q = NRIM[1] / NRIM[0];
      c.b = T.map(function (t, i) {
        var cs = (t - L[i] - q * (Rt[i] - L[i])) / (NSUN[1] - NSUN[2] + q * NSUN[2]), c0 = L[i] - NSUN[2] * cs;
        return [c0, cs, (Rt[i] - c0) / NRIM[0], Math.min(Rt[i], L[i]) * 0.8];
      });
    }
    var s = Math.min(NSUN[1], Math.max(0, n[0] * NSUN[0] + n[1] * NSUN[1] + n[2] * NSUN[2])), r = Math.max(0, n[0] * NRIM[0] + n[1] * NRIM[1] + n[2] * NRIM[2]);
    return hexOf(c.b.map(function (q) { return srgb(Math.max(q[3], q[0] + q[1] * s + q[2] * r)); }));
  }
  // a face (its corners), drawn when it is turned to the map; its outside is away from `inside` (a point in its solid),
  // so its corners may run either way; edge: its outline (its own colour by default, so a curved body shows no seams)
  function nface(V, c, inside, edge) {
    var n = [0, 0, 0], m = [0, 0, 0], k = V.length;
    for (var i = 0; i < k; i++) {
      var a = V[i], b = V[(i + 1) % k];
      n[0] += (a[1] - b[1]) * (a[2] + b[2]); n[1] += (a[2] - b[2]) * (a[0] + b[0]); n[2] += (a[0] - b[0]) * (a[1] + b[1]); m = vadd(m, a, 1 / k);
    }
    if ((n[0] * (m[0] - inside[0]) + n[1] * (m[1] - inside[1]) + n[2] * (m[2] - inside[2])) < 0) n = [-n[0], -n[1], -n[2]];
    if (n[0] + n[1] + n[2] <= 1e-9) return '';
    var col = nsShade(c, vunit(n));
    return '<polygon points="' + pts(V.map(nq)) + '" fill="' + col + '" stroke="' + (edge || col) + '" stroke-width=".5" stroke-linejoin="round"/>';
  }
  // a convex solid: its corners and its faces (indices into them)
  function nsolid(P, F, c, edge) {
    var m = [0, 0, 0];
    P.forEach(function (p) { m = vadd(m, p, 1 / P.length); });
    return F.map(function (f) { return nface(f.map(function (i) { return P[i]; }), c, m, edge); }).join('');
  }
  // a box w x h x d round (x, y, z), turned by o (three.js's rotation)
  function nbox(w, h, d, x, y, z, c, o, edge) {
    var P = [];
    for (var i = 0; i < 8; i++) {
      var p = [(i & 1 ? 0.5 : -0.5) * w, (i & 2 ? 0.5 : -0.5) * h, (i & 4 ? 0.5 : -0.5) * d];
      if (o) p = eul(p, o);
      P.push([p[0] + x, p[1] + y, p[2] + z]);
    }
    return nsolid(P, [[0, 1, 3, 2], [4, 5, 7, 6], [0, 1, 5, 4], [2, 3, 7, 6], [0, 2, 6, 4], [1, 3, 7, 5]], c, edge || VFX.edge);
  }
  // an upright prism on a footprint of (x, z) points, from y0 to y1, of any shape: its sides back to front, its top
  function nprism(F, y0, y1, c, top) {
    var area = 0, sides = [], i;
    for (i = 0; i < F.length; i++) area += F[i][0] * F[(i + 1) % F.length][1] - F[(i + 1) % F.length][0] * F[i][1];
    for (i = 0; i < F.length; i++) {
      var a = F[i], b = F[(i + 1) % F.length], ex = b[0] - a[0], ez = b[1] - a[1], L = Math.hypot(ex, ez);
      if (L < 1e-6) continue;
      var nx = (area > 0 ? ez : -ez) / L, nz = (area > 0 ? -ex : ex) / L, col = nsShade(c, [nx, 0, nz]);
      if (nx + nz <= 1e-6) continue;
      sides.push({ d: a[0] + b[0] + a[1] + b[1], s: '<polygon points="' + pts([[a[0], y0, a[1]], [b[0], y0, b[1]], [b[0], y1, b[1]], [a[0], y1, a[1]]].map(nq)) + '" fill="' + col + '" stroke="' + VFX.edge + '" stroke-width=".5"/>' });
    }
    sides.sort(function (p, q) { return p.d - q.d; });
    var tc = nsShade(top || c, [0, 1, 0]);
    return sides.map(function (s) { return s.s; }).join('') + '<polygon points="' + pts(F.map(function (p) { return nq([p[0], y1, p[1]]); })) + '" fill="' + tc + '" stroke="' + VFX.edge + '" stroke-width=".5"/>';
  }
  // a solid turned round the axis a from o, its sides laid as three.js lays a cylinder's (sin along u, cos along v):
  // rings [t, r] along the axis, k sides from angle ph; its ends closed unless open
  function nrev(o, a, u, v, rings, k, ph, c, open) {
    var P = rings.map(function (g) {
      var l = [];
      for (var i = 0; i < k; i++) { var t = ph + i / k * Math.PI * 2; l.push(vadd(vadd(vadd(o, a, g[0]), u, Math.sin(t) * g[1]), v, Math.cos(t) * g[1])); }
      return l;
    });
    var mid = vadd(o, a, (rings[0][0] + rings[rings.length - 1][0]) / 2), out = '', e = rings.length - 1;
    for (var j = 0; j < e; j++) for (var i = 0; i < k; i++) out += nface([P[j][i], P[j][(i + 1) % k], P[j + 1][(i + 1) % k], P[j + 1][i]], c, mid);
    if (!open && rings[0][1] > 1e-3) out += nface(P[0], c, mid);
    if (!open && rings[e][1] > 1e-3) out += nface(P[e], c, mid);
    return out;
  }
  // an upright cylinder or cone (three.js's: radius r0 at its foot y0, r1 at its top y1), k sides
  function ncyl(x, z, y0, y1, r0, r1, k, c, ph, open) { return nrev([x, y0, z], [0, 1, 0], [1, 0, 0], [0, 0, 1], [[0, r0], [y1 - y0, r1]], k, ph || 0, c, open); }
  // a sphere (or its upper half, top), its bands of faces shaded as they turn
  function nsphere(o, r, kw, kh, c, top) {
    var out = '', p = function (a, b) { return [o[0] + r * Math.cos(a) * Math.sin(b), o[1] + r * Math.sin(a), o[2] + r * Math.cos(a) * Math.cos(b)]; };
    for (var i = top ? kh / 2 : 0; i < kh; i++) for (var j = 0; j < kw; j++) {
      var a0 = i / kh * Math.PI - Math.PI / 2, a1 = (i + 1) / kh * Math.PI - Math.PI / 2, b0 = j / kw * Math.PI * 2, b1 = (j + 1) / kw * Math.PI * 2;
      out += nface(i === kh - 1 ? [p(a0, b0), p(a0, b1), p(a1, b0)] : [p(a0, b0), p(a0, b1), p(a1, b1), p(a1, b0)], c, o);
    }
    return out;
  }
  // a circle (centre o, in the plane of u and v), or the half of it far from the viewer or near
  function narc(o, u, v, R, part, k) {
    k = k || 48;
    var at = function (t) { return vadd(vadd(o, u, Math.cos(t) * R), v, Math.sin(t) * R); }, l = [], i;
    if (!part) { for (i = 0; i < k; i++) l.push(at(i / k * Math.PI * 2)); return l; }
    var ph = Math.atan2(v[0] + v[1] + v[2], u[0] + u[1] + u[2]), t0 = (part === 'near' ? ph - Math.PI / 2 : ph + Math.PI / 2) - 0.05;
    for (i = 0; i <= k / 2; i++) l.push(at(t0 + i / (k / 2) * (Math.PI + 0.1)));
    return l;
  }
  // A torus seen from the map: the band its tube covers (its tube's round section makes it as wide as the tube all
  // round), a lighter band along the side its light falls on. Half of it (part) when something stands inside it.
  function nband(o, u, v, R, t, c, part) {
    var l = pts(narc(o, u, v, R, part).map(nq)), W = 2 * t * SC * 1.2247, a = P(3, 3, 0), k = t * 0.42;
    var b = P(3 + NSUN[0] * k, 3 + NSUN[2] * k, NSUN[1] * k), tag = part ? 'polyline' : 'polygon', o2 = ' fill="none" stroke-linejoin="round"';
    return '<' + tag + ' points="' + l + '"' + o2 + ' stroke="' + nsShade(c, vunit([1, 0.4, 1])) + '" stroke-width="' + f1(W) + '"/>' +
      '<' + tag + ' points="' + l + '"' + o2 + ' stroke="' + nsShade(c, [0, 1, 0]) + '" stroke-width="' + f1(W * 0.5) + '" transform="translate(' + f1(b[0] - a[0]) + ' ' + f1(b[1] - a[1]) + ')"/>';
  }
  // a line of light round a circle (or its far or near half)
  function nring(o, u, v, R, col, w, part, op) { return sdLine(narc(o, u, v, R, part).map(nm), col, w, !part, op); }
  // a window (stations.js's b.win): a pane w x h at p facing ry, drawn when it faces the map
  function nwin(p, ry, w, h, C, on) {
    var s = Math.sin(ry), c = Math.cos(ry), tx = c * w / 2, tz = -s * w / 2, hh = h / 2;
    if (s + c <= 0.05) return '';
    return vfWin([[p[0] - tx, p[1] - hh, p[2] - tz], [p[0] + tx, p[1] - hh, p[2] + tz], [p[0] + tx, p[1] + hh, p[2] + tz], [p[0] - tx, p[1] + hh, p[2] - tz]].map(nm), C, on);
  }
  // rows of windows along a box's faces (stations.js's wins()), on those of `faces` the map sees (+x, +z)
  // (ww0: a pane's width when they are set further apart than there, to keep a long face's count down)
  function nwins(cx, y, cz, w, d, rows, rowH, step, lit, faces, C, R, ww0) {
    var ww = ww0 || Math.min(0.16, step * 0.55), wh = Math.min(0.07, rowH * 0.42), o = '';
    var run = function (len, place) { var m = Math.max(1, Math.floor((len - 0.12) / step)), s = len / m; for (var i = 0; i < m; i++) place(-len / 2 + s * (i + 0.5)); };
    for (var r = 0; r < rows; r++) {
      var yy = y + (r - (rows - 1) / 2) * rowH;
      if (faces.indexOf('+z') >= 0) run(w, function (u) { o += nwin([cx + u, yy, cz + d / 2 + 0.012], 0, ww, wh, C, R() < lit); });
      if (faces.indexOf('+x') >= 0) run(d, function (u) { o += nwin([cx + w / 2 + 0.012, yy, cz + u], Math.PI / 2, ww, wh, C, R() < lit); });
    }
    return o;
  }
  // windows round an upright drum (u3d.js's ringWins)
  function nrwins(r, y, h, step, lit, ww, C, R) {
    var m = Math.max(6, Math.round(2 * Math.PI * r / step)), o = '';
    for (var i = 0; i < m; i++) { var t = i / m * Math.PI * 2, on = R() < lit; o += nwin([Math.cos(t) * (r + 0.014), y, Math.sin(t) * (r + 0.014)], Math.PI / 2 - t, ww, h, C, on); }
    return o;
  }
  function nfl(f, g) { return g ? '<g class="fl" data-f="' + f + '">' + g + '</g>' : ''; }
  // a soft light (one of stations.js's sprites, s across)
  // a soft light (one of stations.js's sprites, s across): rings of it, fainter outward, as its texture falls off
  function nhalo(p, s, col, op) {
    var c = nq(p), r = s / 2 * SC * 1.2247;
    return [[0.85, 0.07], [0.6, 0.1], [0.4, 0.16], [0.22, 0.3]].map(function (q) {
      return '<circle cx="' + f1(c[0]) + '" cy="' + f1(c[1]) + '" r="' + f1(r * q[0]) + '" fill="' + col + '" opacity="' + f1(op * q[1] * 100) / 100 + '"/>';
    }).join('');
  }
  function nlamp(p, r, acc) { return vfLamp(3 + p[0], 3 + p[2], p[1], r * 1.4, acc); }
  // a line of light between two points (stations.js's thin neon boxes)
  function nlit(a, b, col, w, op) { return sdLine([nm(a), nm(b)], col, w, false, op); }
  // an engine as stations.js's engine(): its housing, its open nozzle, the disc of light in its mouth (its rim a ring of
  // light round the nozzle's end, whichever way it points) and a soft light there; no plume, as there ("pulsujici
  // trysky u vseho zrus", 2026-10-20). e the way it burns; turned away, the light and the ring go behind it.
  function neng(p, e, r, C) {
    var a = vunit(e), uv = across(a), u = uv[0], v = uv[1], at = function (s) { return vadd(p, a, s); }, toward = a[0] + a[1] + a[2] > 0.05;
    var house = nrev(p, a, u, v, [[-0.75 * r, 1.08 * r], [0.35 * r, 1.12 * r]], 14, 0, C.light), noz = nrev(p, a, u, v, [[0.3 * r, r], [r, 0.78 * r]], 14, 0, C.mid, true);
    var rim = narc(at(0.98 * r), u, v, 0.82 * r, null, 16).map(nq), h = nq(at(1.05 * r));
    var halo = '<circle cx="' + f1(h[0]) + '" cy="' + f1(h[1]) + '" r="' + f1(r * SC * 1.3) + '" fill="#8fdcff" opacity=".22"/>';
    var core = '<polygon points="' + pts(rim) + '" fill="' + (toward ? '#e6fcff' : 'none') + '" stroke="#e6fcff" stroke-width="1.6"/>';
    return toward ? house + noz + core + halo : halo + core + noz + house;
  }
  // an escort (stations.js's escorts()): a small delta on its circuit at angle a, its nose the way it flies, a light at
  // its tail; the circuit turned as a preview's starts it (its rotation -b.phase, 1 for seed 7)
  function nescort(a, rad, yy, s, C) {
    a += 1;
    var x = Math.cos(a) * rad, z = Math.sin(a) * rad, dir = Math.PI - a, c = Math.cos(dir), sn = Math.sin(dir);
    var sh = [[0, 0.9], [0.55, -0.5], [0.18, -0.36], [0, -0.5], [-0.18, -0.36], [-0.55, -0.5]].map(function (q) { var px = q[0] * s, pz = -q[1] * s; return nq([x + px * c + pz * sn, yy + 0.08 * s, z - px * sn + pz * c]); });
    var g = nq([x + sn * 0.52 * s, yy + 0.04 * s, z + c * 0.52 * s]);
    return { d: x + z + yy, s: '<polygon points="' + pts(sh) + '" fill="' + nsShade(C.mid, [0, 1, 0]) + '" stroke="' + nsShade(C.mid, [1, 0, 0]) + '" stroke-width=".8"/>' +
      '<circle cx="' + f1(g[0]) + '" cy="' + f1(g[1]) + '" r="' + f1(0.11 * s * SC * 1.5) + '" fill="#e6fcff"/>' };
  }
  // small blocks over a deck at height y wherever inside(x, z) holds (stations.js's greebles(), a few of them)
  function ngreebles(mats, y, x0, x1, z0, z1, count, inside, R) {
    var q = function (v) { return Math.max(0.04, Math.round(v / 0.02) * 0.02); }, l = [];
    for (var i = 0, tries = 0; i < count && tries < count * 8; tries++) {
      var x = x0 + (x1 - x0) * R(), z = z0 + (z1 - z0) * R(); if (inside && !inside(x, z)) continue;
      var w = q(0.06 + R() * 0.24), d = q(0.06 + R() * 0.24), h = q(0.03 + R() * R() * 0.16), turn = R() < 0.5;
      l.push({ x: x, z: z, d: x + z, s: nbox(turn ? d : w, h, turn ? w : d, x, y + h / 2, z, mats[i % mats.length]) }); i++;
    }
    return l.sort(function (a, b) { return a.d - b.d; });
  }
  function nj(l) { return l.map(function (p) { return p.s; }).join(''); }
  // what the picture is told of the 3D one: its top and bottom (its ring hangs half a unit under b.bot) and its
  // foot, which sizes the ring
  function nsDone(out, top, bot, foot) { VB[5] = foot; return vfDone(out, top, bot - 0.1); }
  var X3 = [1, 0, 0], Y3 = [0, 1, 0], Z3 = [0, 0, 1];

  // 1. Dreadnought (key 'tower'): a wedge of pale armour, a narrower wedge on it, its decks stepping up and back to the
  // bridge, three great engines and four small across its stern, three escorts on a circuit round it
  SKIN.tower = function (n, acc, R) {
    var C = nsCols(acc), L = 4.5 + 0.22 * n, W = L * 0.6, H = 0.38, z0 = -0.05 * L, f;
    VB = [0, 66, 0, 66, 66];
    var back = z0 - L * 0.38, nose = z0 + L * 0.62, nS = z0 - L * 0.06 + 0.62 * 0.82 * L;
    // a wedge len long and wid across its stern, its nose forward (+z), from y0 to y1, z its shape's middle
    var wedge = function (len, wid, y0, y1, z, c) { return nprism([[0, z + len * 0.62], [wid / 2, z - len * 0.38], [-wid / 2, z - len * 0.38]], y0, y1, c); };
    var half = function (z, nz, len, hw) { return hw * (nz - z) / len; };
    var esc = [0, 1, 2].map(function (i) { return nescort(i / 3 * Math.PI * 2, L * 0.62, -0.2 + (i % 2 ? 0.25 : -0.2), 0.36, C); });
    var out = nj(esc.filter(function (e) { return e.d < 0; }));
    // the engines across the stern, burning aft: the small ones under, the great ones
    var sz = back - 0.02, eng = [];
    [[-W * 0.36, 0.16], [-W * 0.11, 0.15], [W * 0.11, 0.15], [W * 0.36, 0.16]].forEach(function (q) { eng.push({ d: q[0] - 1, s: neng([q[0], -H * 1.35, sz - 0.12], [0, 0, -1], q[1], C) }); });
    [[-W * 0.22, 0.34], [0, 0.4], [W * 0.22, 0.34]].forEach(function (q) { eng.push({ d: q[0], s: neng([q[0], -H * 0.4, sz - q[1] * 0.6], [0, 0, -1], q[1], C) }); });
    out += nj(eng.sort(function (a, b) { return a.d - b.d; }));
    // the keel under it, the hull with its trench of light down the flank, the blocks over its broad deck
    out += wedge(L * 0.9, W * 0.5, -H * 1.75, -H * 0.95, z0 + L * 0.02, C.mid);
    out += wedge(L, W, -H, 0, z0, C.light) + nlit([W / 2 * 0.985, -H * 0.5, back], [0, -H * 0.5, nose], C.neon, 1.3);
    out += nj(ngreebles([C.mid, C.light, C.mid, C.dark], 0, -W / 2, W / 2, back + 0.15, nose - 0.4, 12,
      function (x, z) { return Math.abs(x) < half(z, nose, L, W / 2) * 0.86 && Math.abs(x) > half(z, nS, 0.82 * L, 0.31 * W) + 0.1; }, R));
    out += wedge(L * 0.82, W * 0.62, 0, H * 0.7, z0 - L * 0.06, C.light) + nlit([W * 0.31, H * 0.36, back + L * 0.06], [0, H * 0.36, nose - L * 0.12], C.soft, 1.1);
    out += nj(ngreebles([C.mid, C.light], H * 0.7, -W * 0.3, W * 0.3, z0 + L * 0.12, nS - 0.4, 5,
      function (x, z) { return Math.abs(x) < half(z, nS, 0.82 * L, 0.31 * W) * 0.7; }, R));
    // the decks, stepping up and back: a row of windows round each, a metal lip on top
    var dz = Math.min(0.62, 2.6 / Math.max(1, n)), y = H * 0.7, zc = z0 - L * 0.02, w = W * 0.42, d = L * 0.36, hh = 0.24;
    for (f = 0; f < n; f++) {
      out += nbox(w, hh, d, 0, y + hh / 2, zc, f % 2 ? C.mid : C.light);
      out += nfl(f, nwins(0, y + hh * 0.52, zc, w, d, 1, hh, 0.17, 0.7, '+x+z', C, R));
      out += nbox(w + 0.04, 0.03, d + 0.04, 0, y + hh, zc, C.metal);
      y += hh; zc -= dz * 0.32; w *= 0.88; d *= 0.84;
    }
    // the bridge: a neck, a broad head with a band of glass across its front, two sensor globes and two masts on it
    var bz = zc - d * 0.15, nh = 0.5, hy = y + nh + 0.13, hw = Math.max(1.1, W * 0.34), g = '', k;
    out += nbox(w * 0.32, nh, d * 0.32, 0, y + nh / 2, bz, C.mid) + nbox(hw, 0.26, 0.5, 0, hy, bz, C.light) + nbox(hw * 0.92, 0.07, 0.02, 0, hy + 0.02, bz + 0.26, C.glass);
    for (k = -3; k <= 3; k++) g += nwin([k * hw * 0.12, hy + 0.02, bz + 0.27], 0, hw * 0.08, 0.04, C, true);
    out += nfl(Math.max(0, n - 1), g);
    [-1, 1].forEach(function (s) {
      out += line(nq([s * hw * 0.42, hy + 0.11, bz - 0.12]), nq([s * hw * 0.42, hy + 0.53, bz - 0.12]), VFX.silver.r, 1.3);
      out += nsphere([s * hw * 0.3, hy + 0.27, bz - 0.05], 0.15, 12, 8, C.light);
    });
    out += nlamp([0, hy + 0.42, bz - 0.1], 0.05, acc);
    out += nj(esc.filter(function (e) { return e.d >= 0; }));
    return nsDone(out, hy + 0.6, -H * 2.1, L * 0.5);
  };

  // 2. Shipyard (key 'dome', in place of the Gateway: "tu hvezdnou branu nechci", 2026-10-20): a dry dock, its two
  // walls a storey a deck with windows down both faces, a ship half built between them on cradles (its bow plated,
  // its stern a skeleton of ribs), a gantry crane over it with a welding light, a control tower at each corner
  SKIN.dome = function (n, acc, R) {
    var C = nsCols(acc), Ld = 4.1 + 0.2 * n, Wg = 1.9, tw = 0.52, dh = 0.32, Hw = 0.5 + n * dh, wx = Wg / 2 + tw / 2, th = Hw + 0.7, out = '', f, k;
    VB = [0, 66, 0, 66, 66];
    var esc = [0, 1].map(function (i) { return nescort(i / 2 * Math.PI * 2, Ld * 0.62, Hw * 0.75 + (i % 2 ? 0.25 : -0.2), 0.26, C); });
    out += nj(esc.filter(function (e) { return e.d < 0; }));
    // under the dock: the six-sided keel, long as the dock, a thruster pod at each corner; the dock's floor, lit
    // along its edge
    var kz = Ld / Wg * 0.7, hexAt = function (r, y) { return [0, 1, 2, 3, 4, 5].map(function (j) { var t = j / 6 * Math.PI * 2; return [Math.sin(t) * r, y, Math.cos(t) * r * kz]; }); };
    out += nsolid(hexAt(Wg * 0.3, -1.14).concat(hexAt(Wg * 0.55, -0.34)), [[0, 1, 2, 3, 4, 5], [6, 7, 8, 9, 10, 11], [0, 1, 7, 6], [1, 2, 8, 7], [2, 3, 9, 8], [3, 4, 10, 9], [4, 5, 11, 10], [5, 0, 6, 11]], C.mid);
    [[-1, -1], [1, -1], [-1, 1], [1, 1]].forEach(function (q) { out += ncyl(q[0] * (wx + 0.1), q[1] * (Ld / 2 - 0.25), -0.63, -0.33, 0.2, 0.16, 12, C.metal); });
    out += nbox(Wg + 2 * tw + 0.3, 0.34, Ld + 0.4, 0, -0.17, 0, C.dark) + nlit([Wg / 2 + tw + 0.15, -0.05, -(Ld + 0.4) / 2], [Wg / 2 + tw + 0.15, -0.05, (Ld + 0.4) / 2], C.neon, 1.3);
    // a control tower: a band of glass round its head with its windows, a lid, a mast and its light; lo/hi the part
    // of it drawn (the near wall stands between its two halves)
    var tower = function (sx, sz, lo, hi) {
      var x = sx * (wx + 0.08), z = sz * (Ld / 2 + 0.12), o = '';
      if (lo < Hw) o += nbox(0.62, Math.min(hi, th) - lo, 0.62, x, (lo + Math.min(hi, th)) / 2, z, C.light);
      if (hi > Hw) {
        if (lo >= Hw) o += nbox(0.62, th - lo, 0.62, x, (lo + th) / 2, z, C.light);
        o += nbox(0.7, 0.18, 0.7, x, th - 0.22, z, C.glass) + nfl(Math.max(0, n - 1), nwins(x, th - 0.22, z, 0.7, 0.7, 1, 0.18, 0.16, 0.8, '+x+z', C, R));
        o += nbox(0.7, 0.06, 0.7, x, th + 0.03, z, C.metal) + line(nq([x, th + 0.06, z]), nq([x, th + 0.55, z]), VFX.silver.r, 1.2) + nlamp([x, th + 0.58, z], 0.045, acc);
      }
      return o;
    };
    // a wall: its plinth, a storey a deck with a metal lip and its windows on the face the map sees (the far wall's
    // inner one, the near wall's outer one), the near wall's ribs up its outer face, the rails on top; along the far
    // wall's inner face the bay's lit edge and its work lights
    var wall = function (sx) {
      var x = sx * wx, o = nbox(tw, 0.5, Ld, x, 0.25, 0, C.mid);
      for (f = 0; f < n; f++) {
        var y = 0.5 + f * dh;
        o += nbox(tw, dh - 0.03, Ld * 0.97, x, y + (dh - 0.03) / 2, 0, f % 2 ? C.mid : C.light) + nbox(tw + 0.04, 0.03, Ld * 0.97 + 0.04, x, y + dh - 0.015, 0, C.metal);
        o += nfl(f, nwins(x, y + dh * 0.48, 0, tw, Ld * 0.97, 1, dh, 0.26, 0.7, '+x', C, R, 0.105));
      }
      if (sx > 0) for (k = 0; k < Math.floor(Ld / 0.7); k++) o += nbox(0.08, Hw - 0.1, 0.1, x + tw / 2 + 0.03, (Hw - 0.1) / 2 + 0.05, -Ld / 2 + 0.35 + k * 0.7, C.dark);
      [-0.13, 0.13].forEach(function (d) { o += nbox(0.05, 0.06, Ld, x + d, Hw + 0.03, 0, C.metal); });
      if (sx < 0) {
        o += nlit([x + tw / 2 + 0.01, Hw - 0.04, -Ld * 0.485], [x + tw / 2 + 0.01, Hw - 0.04, Ld * 0.485], C.neon, 1.2);
        for (k = 0; k < 4; k++) { var wy = 0.42 + (k % 2) * Math.max(0.3, Hw * 0.45), wz = -Ld * 0.36 + k * Ld * 0.24; o += '<polygon points="' + pts([[x + tw / 2 + 0.013, wy - 0.03, wz - 0.08], [x + tw / 2 + 0.013, wy - 0.03, wz + 0.08], [x + tw / 2 + 0.013, wy + 0.03, wz + 0.08], [x + tw / 2 + 0.013, wy + 0.03, wz - 0.08]].map(nq)) + '" fill="' + C.hot + '"/>'; }
      }
      return o;
    };
    out += tower(-1, -1, 0, 99) + wall(-1) + tower(-1, 1, 0, 99) + tower(1, -1, 0, Hw);
    // the ship in the bay, its nose to +z: three cradles, the spine, the stern's ribs back to front, the plated bow
    // and the ridge along it
    var Ls = Ld * 0.8, Ws = Wg * 0.74, hs = 0.34, y0 = 0.22, nose = Ls * 0.55, tail = -Ls * 0.45, zc = -Ls * 0.02, rib = nsShade(C.metal, vunit([1, 1, 1]));
    var half = function (z) { return Ws / 2 * (nose - z) / (nose - tail); };
    [-Ls * 0.3, 0, Ls * 0.28].forEach(function (z) { out += nbox(Ws * 0.5, y0, 0.22, 0, y0 / 2, z, C.dark); });
    out += nbox(0.1, 0.1, Ls, 0, y0 + hs * 0.55, (nose + tail) / 2, C.metal);
    for (k = 6; k >= 1; k--) {
      var z = zc - k * (zc - tail) / 6.2, w = half(z), w2 = line(nq([0, y0 + hs, z]), nq([w, y0, z]), rib, 1.6) + line(nq([0, y0 + hs, z]), nq([-w, y0, z]), rib, 1.6);
      out += line(nq([-w, y0 + 0.03, z]), nq([w, y0 + 0.03, z]), rib, 1.6) + w2;
    }
    out += nprism([[0, nose], [half(zc), zc], [-half(zc), zc]], y0, y0 + hs, C.light) + nbox(Ws * 0.18, hs * 0.5, nose - zc, 0, y0 + hs * 1.25, (nose + zc) / 2 - 0.1, C.mid);
    // the welding light under the gantry (it rides the rails; here where a preview first has it), its cable
    var gz = Ld * 0.25, gy = Hw + 0.12;
    out += line(nq([0, gy - 0.12, gz]), nq([0, y0 + hs + 0.35, gz]), VFX.silver.r, 1) + nhalo([0, y0 + hs + 0.3, gz], 0.7, acc, 0.9);
    var wl = nq([0, y0 + hs + 0.33, gz]);
    out += '<circle cx="' + f1(wl[0]) + '" cy="' + f1(wl[1]) + '" r="' + f1(0.06 * SC * 1.22) + '" fill="' + C.hot + '"/>';
    // the near wall, the rest of the tower behind it; the gantry: its far truck, the trolley, the near truck, the bridge
    out += wall(1) + tower(1, -1, Hw, 99);
    out += nbox(0.36, 0.2, 0.52, -wx, gy, gz, C.mid) + nbox(0.34, 0.16, 0.44, 0, gy - 0.04, gz, C.mid) + nbox(0.36, 0.2, 0.52, wx, gy, gz, C.mid) + nbox(Wg + 2 * tw + 0.24, 0.17, 0.34, 0, gy + 0.12, gz, C.light);
    out += tower(1, 1, 0, 99) + nj(esc.filter(function (e) { return e.d >= 0; }));
    return nsDone(out, th + 0.7, -1.2, Math.max(Ld / 2 + 0.5, wx + 0.6));
  };

  // 3. Pyramid Carrier (key 'pyramid'): a stepped pyramid, a tier a deck under a plate of light and a capstone burning
  // in the company's colour, inside a ring of eight armoured petals, engines on four of them, a pyramid keel under it
  SKIN.pyramid = function (n, acc, R) {
    var C = nsCols(acc), Ro = 2.6 + 0.16 * n, Ri = Ro * 0.6, hh = 0.36, out = '', petals = [], k, i, f;
    VB = [0, 66, 0, 66, 66];
    out += ncyl(0, 0, -hh * 0.6 - 1.3, -hh * 0.6, 0, Ri * 0.9, 4, C.dark, Math.PI / 4);
    for (k = 0; k < 8; k++) {
      var a0 = k / 8 * Math.PI * 2 + 0.06, a1 = (k + 1) / 8 * Math.PI * 2 - 0.06, am = (a0 + a1) / 2, F = [], s = '', ca = Math.cos(am), sa = Math.sin(am);
      for (i = 0; i <= 6; i++) { var a = a0 + (a1 - a0) * i / 6; F.push([Math.cos(a) * Ro, -Math.sin(a) * Ro]); }
      for (i = 6; i >= 0; i--) { a = a0 + (a1 - a0) * i / 6; F.push([Math.cos(a) * Ri, -Math.sin(a) * Ri]); }
      s += nprism(F, -hh * 0.6, hh * 0.4, C.bronze);
      // the light along its outer edge, and the machinery on its back, clear of the gaps
      var e = [ca * (Ro - 0.03), hh * 0.4 + 0.005, -sa * (Ro - 0.03)], tg = [sa * Ro * 0.31, 0, ca * Ro * 0.31];
      s += nlit(vadd(e, tg, -1), vadd(e, tg, 1), C.neon, 1.3);
      s += nj(ngreebles([C.bronze, C.dark, C.mid], hh * 0.4, -Ro, Ro, -Ro, Ro, 3, function (x, z) {
        var r = Math.hypot(x, z), b = Math.atan2(-z, x); b = ((b - a0) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2);
        return r > Ri + 0.15 && r < Ro - 0.2 && b > 0.08 && b < a1 - a0 - 0.08;
      }, R));
      petals.push({ d: ca - sa, s: s, eng: k >= 4 ? neng([ca * (Ro + 0.05), -hh * 0.3, -sa * (Ro + 0.05)], [ca, 0, -sa], 0.17, C) : '' });
    }
    petals.sort(function (p, q) { return p.d - q.d; });
    var far = petals.filter(function (p) { return p.d < 0; }), near = petals.filter(function (p) { return p.d >= 0; });
    out += far.map(function (p) { return p.eng + p.s; }).join('') + nring([0, hh * 0.4, 0], X3, Z3, Ri * 0.98, C.soft, 1.3, 'far');
    // the pyramid: a tier a deck turned to the corners, its windows on the riser the map sees, a plate of light on top
    var base = Ri * 1.42, tierH = Math.min(0.42, 2.4 / Math.max(2, n)), y = -0.05, w = base;
    for (f = 0; f < n; f++) {
      out += nbox(w, tierH, w, 0, y + tierH / 2, 0, C.bronze, { ry: Math.PI / 4 }) + nbox(w + 0.03, 0.025, w + 0.03, 0, y + tierH, 0, C.plate, { ry: Math.PI / 4 }, C.plate);
      var g = '', m = Math.max(2, Math.floor(w / 0.24)), q = 3, aq = Math.PI / 4 + q * Math.PI / 2, cq = Math.cos(aq), sq = Math.sin(aq);
      for (i = 0; i < m; i++) { var u = -w / 2 + w / m * (i + 0.5); g += nwin([cq * (w / 2 + 0.012) + sq * u, y + tierH * 0.5, -sq * (w / 2 + 0.012) + cq * u], aq + Math.PI / 2, 0.11, Math.min(0.08, tierH * 0.35), C, R() < 0.65); }
      out += nfl(f, g);
      y += tierH; w -= (base - 0.55) / (n + 1.2);
    }
    var cap = Math.max(0.5, w), ch = cap * 0.75;
    out += ncyl(0, 0, y, y + ch, cap * 0.72, 0, 4, C.bronze) + ncyl(0, 0, y + ch * 0.68, y + ch, cap * 0.24, 0, 4, C.hot);
    out += nhalo([0, y + ch * 0.9, 0], 1.6, acc, 0.55) + nlamp([0, y + ch + 0.08, 0], 0.06, acc);
    out += nring([0, hh * 0.4, 0], X3, Z3, Ri * 0.98, C.soft, 1.3, 'near');
    out += near.map(function (p) { return p.s; }).join('') + near.map(function (p) { return p.eng; }).join('');
    return nsDone(out, y + ch + 0.25, -hh * 0.6 - 1.4, Ro + 0.1);
  };

  // 4. Ring Habitat (key 'orbital'): a wheel on six spokes, modules docked on its rim, turning round a spindle of
  // decks, a dome and a mast on top, the engine under it
  SKIN.orbital = function (n, acc, R) {
    var C = nsCols(acc), Rw = 2.5 + 0.14 * n, rs = 0.5, dh = 0.34, y0 = -(n * dh) / 2, wy = 0.05, out = '', f, k;
    VB = [0, 66, 0, 66, 66];
    var spokes = [], mods = [];
    for (k = 0; k < 6; k++) {
      var a = k / 6 * Math.PI * 2, ca = Math.cos(a), sa = -Math.sin(a), b = (k + 0.5) / 6 * Math.PI * 2, mx = Math.cos(b) * Rw, mz = Math.sin(b) * Rw;
      spokes.push({ d: ca + sa, s: line(nq([ca * (rs + 0.2), wy, sa * (rs + 0.2)]), nq([ca * (Rw - 0.2), wy, sa * (Rw - 0.2)]), nsShade(C.metal, vunit([1, 1, 1])), f1(0.12 * SC * 1.22)) });
      mods.push({ d: mx + mz, s: nbox(0.42, 0.42, 0.42, mx, wy + 0.32, mz, C.mid, { ry: -b }) });
    }
    var farOf = function (l, far) { return nj(l.filter(function (p) { return far ? p.d < 0 : p.d >= 0; }).sort(function (p, q) { return p.d - q.d; })); };
    // under it: the engine burning down, the cone it hangs from
    out += neng([0, y0 - 0.85, 0], [0, -1, 0], 0.26, C) + ncyl(0, 0, y0 - 0.8, y0, rs * 0.4, rs * 0.9, 16, C.dark);
    // the wheel's far half with its lines of light, the far spokes and modules
    out += nband([0, wy, 0], X3, Z3, Rw, 0.3, C.light, 'far') + nring([0, wy, 0], X3, Z3, Rw - 0.31, C.soft, 1.1, 'far') + farOf(spokes, true) + farOf(mods, true);
    // the spindle, a drum a deck with its windows and a collar over it, the hub collar the spokes hang from at the
    // wheel's height
    var y = y0, hub = false, sp = '';
    for (f = 0; f < n; f++) {
      if (!hub && y >= wy) { sp += ncyl(0, 0, wy - 0.15, wy + 0.15, rs + 0.2, rs + 0.2, 20, C.mid); hub = true; }
      sp += ncyl(0, 0, y + 0.025, y + dh - 0.025, rs, rs, 20, f % 2 ? C.mid : C.light) + nfl(f, nrwins(rs, y + dh / 2, 0.08, 0.2, 0.65, 0.09, C, R)) + ncyl(0, 0, y + dh - 0.025, y + dh + 0.025, rs + 0.06, rs + 0.06, 20, C.metal);
      y += dh;
    }
    if (!hub) sp += ncyl(0, 0, wy - 0.15, wy + 0.15, rs + 0.2, rs + 0.2, 20, C.mid);
    out += sp + nsphere([0, y, 0], rs * 0.9, 16, 8, C.light, true);
    out += line(nq([0, y + 0.3, 0]), nq([0, y + 1.4, 0]), VFX.silver.r, 1.4) + nlamp([0, y + 1.42, 0], 0.06, acc);
    // the near spokes and modules, the wheel's near half and the line of light round its rim
    out += farOf(spokes, false) + nband([0, wy, 0], X3, Z3, Rw, 0.3, C.light, 'near') + farOf(mods, false) + nring([0, wy, 0], X3, Z3, Rw + 0.31, C.neon, 1.4, 'near');
    return nsDone(out, y + 1.6, y0 - 1.4, Rw + 0.4);
  };

  // 5. Lancer (key 'rocket'): a spine of eight faces, rings round its front half, a sensor light at its prow (its lance
  // of light is gone, as in stations.js: "u te rakety ji zrus ten laser vepredu", 2026-10-20); two armoured flanks round
  // its back half, the decks along its top, the bridge tower at the stern, four engines round it
  SKIN.rocket = function (n, acc, R) {
    var C = nsCols(acc), L = 4.8 + 0.24 * n, r = 0.38, zt = L / 2, out = '', f, k, eng = [];
    VB = [0, 66, 0, 66, 66];
    [[0.45, 0.3], [-0.45, 0.3], [0.45, -0.3], [-0.45, -0.3]].forEach(function (q) { eng.push({ d: q[0] + q[1], s: neng([q[0], q[1], -zt - 0.15], [0, 0, -1], 0.26, C) }); });
    out += nj(eng.sort(function (a, b) { return a.d - b.d; }));
    var flank = function (s) {
      var o = nprism([[0, -0.42 * L], [1.15 * s, -0.36 * L], [0.9 * s, 0.08 * L], [0, 0.18 * L]], -0.14, 0.14, C.light);
      return o + nj(ngreebles([C.mid, C.dark], 0.14, s > 0 ? 0.55 : -0.95, s > 0 ? 0.95 : -0.55, -L * 0.38, L * 0.02, 4, null, R));
    };
    var rings = function (part) {
      var o = '';
      for (k = 0; k < 6; k++) { var z = zt - 0.35 - k * 0.42; o += nband([0, 0, z], X3, Y3, r + 0.12, 0.08, C.dark, part) + nring([0, 0, z + 0.06], X3, Y3, r + 0.13, C.soft, 1.3, part); }
      return o;
    };
    // the far flank, the rings' far halves, the spine and its prow, the bridge tower, the decks
    out += flank(-1) + rings('far');
    out += nrev([0, 0, -L / 2], Z3, X3, [0, -1, 0], [[0, r * 1.05], [L, r]], 8, Math.PI / 8, C.mid) + nrev([0, 0, zt], Z3, X3, [0, -1, 0], [[0, r], [1.2, 0]], 8, 0, C.light);
    var tz = -L * 0.4, ty = r + 0.24;
    out += nbox(0.5, 0.7, 0.55, 0, ty + 0.35, tz, C.light) + nbox(0.9, 0.22, 0.42, 0, ty + 0.8, tz + 0.04, C.mid) + nbox(0.8, 0.06, 0.02, 0, ty + 0.8, tz + 0.26, C.glass) + nlamp([0, ty + 1.05, tz], 0.05, acc);
    var dz = Math.min(0.55, (L * 0.5) / Math.max(1, n));
    for (f = 0; f < n; f++) {
      var z = -L * 0.36 + f * dz, hh = 0.26, w = 0.8 - f * 0.03, d = dz * 0.86;
      out += nbox(w, hh, d, 0, r + hh / 2 - 0.05, z + d / 2, f % 2 ? C.mid : C.light) + nfl(f, nwins(0, r + hh * 0.5 - 0.05, z + d / 2, w, d, 1, hh, 0.16, 0.65, '+x', C, R));
    }
    // the rings' near halves, the near flank with its line of light
    var lc = [1.1, 0.05, -L * 0.16], ld = [Math.sin(-0.05), 0, Math.cos(-0.05)];
    out += rings('near') + flank(1) + nlit(vadd(lc, ld, -L * 0.22), vadd(lc, ld, L * 0.22), C.neon, 1.3);
    // the prow's sensor tip, a small still light
    var tp = nq([0, 0, zt + 1.22]);
    out += '<circle cx="' + f1(tp[0]) + '" cy="' + f1(tp[1]) + '" r="' + f1(0.05 * SC * 1.22 * 2.6) + '" fill="' + acc + '" opacity=".3"/><circle cx="' + f1(tp[0]) + '" cy="' + f1(tp[1]) + '" r="' + f1(0.05 * SC * 1.22) + '" fill="' + C.hot + '"/>';
    return nsDone(out, ty + 1.2, -1.0, L * 0.5 + 0.4);
  };

  // 6. Citadel (key 'vault'): an armoured orb, a band of hangars round its middle, meridian ribs, its decks in bands of
  // windows above and below the middle in turn, a spire on top and an antenna under it, a docking ring on four arms
  SKIN.vault = function (n, acc, R) {
    var C = nsCols(acc), Rs = 1.45 + 0.09 * n, D = Rs * 1.75, out = '', f, k;
    VB = [0, 66, 0, 66, 66];
    var esc = [0, 1].map(function (i) { return nescort(i / 2 * Math.PI * 2, D * 1.35, 0.5 + (i % 2 ? 0.25 : -0.2), 0.32, C); });
    var arms = [];
    for (k = 0; k < 4; k++) {
      var a = k * Math.PI / 2 + Math.PI / 4, ca = Math.cos(a), sa = Math.sin(a);
      arms.push({ d: ca + sa, s: nbox(D - Rs, 0.1, 0.12, ca * (Rs + D) / 2, -0.05, sa * (Rs + D) / 2, C.metal, { ry: -a }) + nbox(0.3, 0.22, 0.6, ca * D, 0.12, sa * D, C.mid, { ry: -a }) + nlamp([ca * D, 0.3, sa * D], 0.04, acc) });
    }
    var side = function (far) { return nj(arms.filter(function (p) { return far ? p.d < 0.5 : p.d >= 0.5; })); };
    out += nj(esc.filter(function (e) { return e.d < 0; }));
    out += ncyl(0, 0, -Rs - 1.4, -Rs + 0.1, 0.05, 0.26, 12, C.dark) + neng([0, -Rs - 0.15, 0], [0, -1, 0], 0.3, C);
    out += nband([0, -0.05, 0], X3, Z3, D, 0.08, C.mid, 'far') + nring([0, 0.04, 0], X3, Z3, D, C.soft, 0.8, 'far', 0.55) + side(true);
    // the orb, its band, the ribs over it where the map sees them
    out += nsphere([0, 0, 0], Rs, 24, 14, C.light) + ncyl(0, 0, -0.17, 0.17, Rs * 1.035, Rs * 1.035, 32, C.mid, 0, true);
    var rib = nsShade(C.mid, vunit([0.3, 1, 0.3])), run = [];
    var flush = function () { if (run.length > 1) out += '<polyline points="' + pts(run.map(nq)) + '" fill="none" stroke="' + rib + '" stroke-width="1.4"/>'; run = []; };
    for (k = 0; k < 6; k++) {
      var be = k / 6 * Math.PI * 2;
      for (var i = 0; i <= 24; i++) {
        var u = i / 24 * Math.PI, p = [-Rs * 1.008 * Math.sin(u) * Math.cos(be), Rs * 1.008 * Math.cos(u), Rs * 1.008 * Math.sin(u) * Math.sin(be)];
        if (p[0] + p[1] + p[2] > 0.02 * Rs) run.push(p); else flush();
      }
      flush();
    }
    // the decks: a dark seam and a band of windows each, above and below the middle in turn
    for (f = 0; f < n; f++) {
      var lat = (f % 2 ? -1 : 1) * (0.28 + Math.floor(f / 2) * 0.22), yy = Math.sin(lat) * Rs, rr = Math.cos(lat) * Rs, seam = narc([0, yy + 0.06, 0], X3, Z3, rr + 0.01, 'near');
      out += '<polyline points="' + pts(seam.map(nq)) + '" fill="none" stroke="' + nsShade(C.dark, [0.6, 0.4, 0.6]) + '" stroke-width="1.3"/>';
      out += nfl(f, nrwins(rr + 0.05, yy, 0.07, 0.2, 0.6, 0.1, C, R));
    }
    // the band's line of light and its eight hangar mouths, glowing
    out += nring([0, 0, 0], X3, Z3, Rs * 1.04, C.neon, 1.4, 'near');
    for (k = 0; k < 8; k++) {
      var b = (k + 0.5) / 8 * Math.PI * 2, cb = Math.cos(b), sb = Math.sin(b);
      if (cb + sb < 0.1) continue;
      var c = [cb * Rs * 1.045, -0.08, sb * Rs * 1.045], t = [sb * 0.17, 0, -cb * 0.17];
      out += '<polygon points="' + pts([vadd(vadd(c, t, -1), Y3, -0.06), vadd(vadd(c, t, 1), Y3, -0.06), vadd(vadd(c, t, 1), Y3, 0.06), vadd(vadd(c, t, -1), Y3, 0.06)].map(nq)) + '" fill="' + C.hot + '"/>';
    }
    // the spire, its mast and beacon; the near half of the docking ring, its near arms and what is docked there
    out += ncyl(0, 0, Rs - 0.1, Rs + 1.1, 0.32, 0.1, 12, C.mid) + line(nq([0, Rs + 1.1, 0]), nq([0, Rs + 1.9, 0]), VFX.silver.r, 1.3) + nlamp([0, Rs + 1.92, 0], 0.06, acc);
    out += nband([0, -0.05, 0], X3, Z3, D, 0.08, C.mid, 'near') + nring([0, 0.04, 0], X3, Z3, D, C.soft, 0.8, 'near', 0.55) + side(false);
    out += nj(esc.filter(function (e) { return e.d >= 0; }));
    return nsDone(out, Rs + 2.0, -Rs - 1.5, D + 0.3);
  };

  // 7. Monolith (key 'stack'): a slab of black glass, a seam of light up each edge, a deck a band of windows across its
  // broad face; a prism of light over it, rings of data blocks round it, on a six-sided plinth with shards under it
  SKIN.stack = function (n, acc, R) {
    var C = nsCols(acc), w = 1.3, d = 0.62, dh = 0.46, H = n * dh + 0.5, out = '', f, k, i;
    VB = [0, 66, 0, 66, 66];
    var octa = function (x, y, z, r, s, c) {
      var P = [[r * s[0], 0, 0], [-r * s[0], 0, 0], [0, r * s[1], 0], [0, -r * s[1], 0], [0, 0, r * s[2]], [0, 0, -r * s[2]]].map(function (p) { return [p[0] + x, p[1] + y, p[2] + z]; });
      return nsolid(P, [[0, 2, 4], [0, 4, 3], [0, 3, 5], [0, 5, 2], [1, 2, 5], [1, 5, 3], [1, 3, 4], [1, 4, 2]], c, typeof c === 'string' ? c : null);
    };
    // under the plinth, the shards; the plinth with its line of light round the top
    var sh = [{ d: -1, s: octa(0, -0.95, 0, 0.42, [0.8, 1.9, 0.8], C.mid) }];
    for (k = 0; k < 5; k++) { var a = k / 5 * Math.PI * 2; sh.push({ d: Math.cos(a) + Math.sin(a), s: octa(Math.cos(a) * 1.1, -0.75 - (k % 3) * 0.2, Math.sin(a) * 1.1, 0.22 + (k % 2) * 0.1, [0.7, 1.6, 0.7], C.dark) }); }
    out += nj(sh.sort(function (p, q) { return p.d - q.d; }));
    var hex = [0, 1, 2, 3, 4, 5].map(function (j) { var b = j / 6 * Math.PI * 2; return [Math.cos(b) * 1.9, -Math.sin(b) * 1.9]; });
    out += nprism(hex, -0.3, 0, C.dark) + sdLine(hex.map(function (p) { return nm([p[0] * 0.98, 0.005, p[1] * 0.98]); }), C.neon, 1.4, true);
    // the data blocks, three rings of them: those behind the slab first
    var blocks = [];
    for (var rg = 0; rg < 3; rg++) {
      var m = 9 + rg * 2, rad = 1.55 + rg * 0.32, yy = H * (0.25 + rg * 0.3);
      for (k = 0; k < m; k++) {
        var b = k / m * Math.PI * 2, s = 0.13 + ((k * 7 + rg) % 3) * 0.05, x = Math.cos(b) * rad, z = Math.sin(b) * rad;
        blocks.push({ d: x + z, s: nbox(s, s, s, x, yy + Math.sin(k * 1.7) * 0.12, z, (k + rg) % 3 ? C.metal : C.hot, { ry: b + k, rx: k * 0.7 }) });
      }
    }
    blocks.sort(function (p, q) { return p.d - q.d; });
    out += nj(blocks.filter(function (p) { return p.d < 0; }));
    // the slab, its seams of light, a deck's band of light and its windows
    out += nbox(w, H, d, 0, H / 2, 0, C.black);
    [[1, 1], [1, -1], [-1, 1]].forEach(function (q) { out += nlit([q[0] * w / 2, 0, q[1] * d / 2], [q[0] * w / 2, H, q[1] * d / 2], C.neon, 1.3); });
    for (f = 0; f < n; f++) {
      var yc = 0.25 + f * dh + dh / 2, yb = yc + dh / 2;
      out += '<polyline points="' + pts([[-w / 2 - 0.01, yb, d / 2 + 0.01], [w / 2 + 0.01, yb, d / 2 + 0.01], [w / 2 + 0.01, yb, -d / 2 - 0.01]].map(nq)) + '" fill="none" stroke="' + C.soft + '" stroke-width="1"/>';
      out += nfl(f, nwins(0, yc, 0, w, d, 2, 0.13, 0.13, 0.7, '+z', C, R));
    }
    // its crown, a prism of light; the blocks in front
    out += octa(0, H + 0.45, 0, 0.3, [0.8, 1.6, 0.8], C.hot) + nhalo([0, H + 0.45, 0], 1.4, acc, 0.6) + nlamp([0, H + 0.95, 0], 0.05, acc);
    out += nj(blocks.filter(function (p) { return p.d >= 0; }));
    return nsDone(out, H + 1.1, -1.4, 2.6);
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
    // the revenue share's top 3 (uvboard.js): a gold pop over each now and then (the 3D map sends an arc with it)
    setInterval(function () { if (self.visible()) self.sharePulse(); }, 10000);
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
    if (it.kind === 'ad') return this.adSVG(it);
    if (it.kind === 'slot') return this.slotSVG(it);
    var c = it.c, n = floorsOf(c), priv = !c.public && !it.mine, paused = c.status === 'paused';
    var a = CO.skinArt({ skin: c.skin, accent: c.accent, floors: n, seed: it.mine ? 7 : c.id, priv: priv, you: it.mine, plot: it.mine ? true : false });
    var o = gp(it.pos[0], it.pos[1], it.pos[2]), base = P(3, 3, 0), tx = o[0] - base[0] * UVSS, ty = o[1] - base[1] * UVSS, e = Math.min(a.ext, 4.5);
    var hit = '<polygon class="hit" fill="transparent" points="' + pts([P(3 - e, 3 + e, a.bot), P(3 - e, 3 + e, a.top), P(3 - e, 3 - e, a.top), P(3 + e, 3 - e, a.top), P(3 + e, 3 - e, a.bot), P(3 + e, 3 + e, a.bot)]) + '"/>';
    var top = P(3, 3, a.top + 0.5);
    it.anchor = [tx + top[0] * UVSS, ty + top[1] * UVSS]; it.size = (a.top - a.bot) * SC * UVSS;
    return '<g class="plot' + (priv ? ' priv' : '') + (paused ? ' paused' : '') + (it.mine ? ' mine' : '') + '" data-id="' + c.id + '" transform="matrix(' + UVSS + ' 0 0 ' + UVSS + ' ' + f1(tx) + ' ' + f1(ty) + ')">' + a.svg + hit + '</g>';
  };
  // The ads, flat: the gem its logo, a cut diamond in the logo's greens floating over its shadow; the casino an orbital
  // chip, its spine through two magenta rings with a chip's white inserts round them and Agent Tournaments' logo over it
  // -- the shapes the 3D map builds, as simple as the flat map is.
  Universe.prototype.adSVG = function (it) {
    var o = gp(it.pos[0], it.pos[1], it.pos[2]), x = o[0], y = o[1], s = CO.uvGalaxy.adClear * RX * 1.1, acc = CO.accentHex(it.c.accent), out, top;
    var shadow = '<ellipse cx="' + f1(x) + '" cy="' + f1(y) + '" rx="' + f1(s * 0.5) + '" ry="' + f1(s * 0.5 * RY / RX) + '" fill="' + acc + '" opacity=".12"/>';
    var poly = function (p, fill) { return '<polygon points="' + pts(p) + '" fill="' + fill + '" stroke="#0b1a22" stroke-width="2" stroke-linejoin="round"/>'; };
    if (it.ad.key === 'gem') {
      var cy = y - s * 0.3, gy = cy - s * 0.62, ty = gy - s * 0.26, gw = s * 0.5, tw = s * 0.3, m = gw * 0.34;
      out = shadow + poly([[x - gw, gy], [x - m, gy], [x, cy]], '#2fc3a0') + poly([[x - m, gy], [x + m, gy], [x, cy]], '#16967f') + poly([[x + m, gy], [x + gw, gy], [x, cy]], '#2fc3a0') +
        poly([[x - gw, gy], [x - tw, ty], [x - m, gy]], '#7fdccd') + poly([[x - tw, ty], [x + tw, ty], [x + m, gy], [x - m, gy]], '#dafcf6') + poly([[x + tw, ty], [x + gw, gy], [x + m, gy]], '#aef2e8');
      top = ty;
    } else if (it.ad.key === 'promo') {
      // the Promo Market as u3d.js adPromo draws it: a hex platform, the cyan spire with its ticker band and two rings,
      // the hologram on top (a cube of light: a magenta screen and an amber one, its edges lit), two searchlights over it;
      // 15 % smaller than the other two, as in 3D
      s = s * 0.85;
      var el = function (cyy, k, w) { return '<ellipse cx="' + f1(x) + '" cy="' + f1(cyy) + '" rx="' + f1(s * 0.5 * k) + '" ry="' + f1(s * 0.5 * k * RY / RX) + '" fill="none" stroke="#00cfff" stroke-width="' + f1(w) + '"/>'; };
      var hex = [0, 1, 2, 3, 4, 5].map(function (i) { var a = i * Math.PI / 3; return [x + Math.cos(a) * s * 0.42, y - s * 0.06 + Math.sin(a) * s * 0.42 * RY / RX]; });
      var cs = s * 0.18, cy0 = y - s * 0.83, cb = cy0 + cs * 0.55;   // the cube's half width, its top edge's middle, its bottom corner
      var top3 = [[x, cy0 - cs * 0.5], [x + cs, cy0], [x, cy0 + cs * 0.5], [x - cs, cy0]];
      var left = [[x - cs, cy0], [x, cy0 + cs * 0.5], [x, cb + cs * 0.5 + cs], [x - cs, cb + cs]];
      var right = [[x + cs, cy0], [x, cy0 + cs * 0.5], [x, cb + cs * 0.5 + cs], [x + cs, cb + cs]];
      var beam = function (dx) { return '<polygon points="' + pts([[x - dx * cs * 0.3, cy0 - cs * 0.3], [x + dx * s * 0.62, cy0 - s * 0.62], [x + dx * s * 0.38, cy0 - s * 0.7]]) + '" fill="#e8fbff" opacity=".16"/>'; };
      out = shadow + beam(1) + beam(-1) + poly(hex, '#0d1520') + '<polygon points="' + pts(hex) + '" fill="none" stroke="#00cfff" stroke-width="2"/>' +
        '<polygon points="' + pts([[x - s * 0.07, y - s * 0.1], [x + s * 0.07, y - s * 0.1], [x + s * 0.03, cb + cs], [x - s * 0.03, cb + cs]]) + '" fill="#8fa3b8" stroke="#0b1a22" stroke-width="2"/>' +
        '<rect x="' + f1(x - s * 0.26) + '" y="' + f1(y - s * 0.32) + '" width="' + f1(s * 0.52) + '" height="' + f1(s * 0.08) + '" rx="' + f1(s * 0.02) + '" fill="#00cfff" opacity=".8"/>' +
        el(y - s * 0.46, 0.5, 3) + el(y - s * 0.6, 0.36, 2.5) +
        '<polygon points="' + pts(left) + '" fill="#ff2d95" fill-opacity=".38" stroke="#bff3ff" stroke-width="2"/><polygon points="' + pts(right) + '" fill="#ffb020" fill-opacity=".3" stroke="#bff3ff" stroke-width="2"/>' +
        '<polygon points="' + pts(top3) + '" fill="#00cfff" fill-opacity=".12" stroke="#bff3ff" stroke-width="2"/>';
      top = cy0 - s * 0.7;
    } else {
      var c0 = y - s * 0.55, rx = s * 0.5, ry = rx * RY / RX, ring = function (cyy, k) {
        return '<ellipse cx="' + f1(x) + '" cy="' + f1(cyy) + '" rx="' + f1(rx * k) + '" ry="' + f1(ry * k) + '" fill="none" stroke="#ff3dc8" stroke-width="' + f1(6 * k) + '"/>' +
          '<ellipse cx="' + f1(x) + '" cy="' + f1(cyy) + '" rx="' + f1(rx * k) + '" ry="' + f1(ry * k) + '" fill="none" stroke="#f2f7fb" stroke-width="' + f1(6 * k) + '" stroke-dasharray="' + f1(rx * k * 0.18) + ' ' + f1(rx * k * 0.34) + '"/>';
      };
      out = shadow + '<line x1="' + f1(x) + '" y1="' + f1(c0 + s * 0.5) + '" x2="' + f1(x) + '" y2="' + f1(c0 - s * 0.55) + '" stroke="#8a84a8" stroke-width="5"/>' +
        ring(c0 + s * 0.12, 0.65) + ring(c0, 1) + ring(c0 - s * 0.08, 1) +
        '<circle cx="' + f1(x) + '" cy="' + f1(c0 - s * 0.72) + '" r="' + f1(s * 0.16) + '" fill="#0d1520" stroke="#00e6c0" stroke-width="3"/>' +
        '<rect x="' + f1(x - s * 0.07) + '" y="' + f1(c0 - s * 0.77) + '" width="' + f1(s * 0.045) + '" height="' + f1(s * 0.09) + '" rx="' + f1(s * 0.022) + '" fill="#00cfff"/>' +
        '<rect x="' + f1(x + s * 0.025) + '" y="' + f1(c0 - s * 0.77) + '" width="' + f1(s * 0.045) + '" height="' + f1(s * 0.09) + '" rx="' + f1(s * 0.022) + '" fill="#00ff88"/>';
      top = c0 - s * 0.9;
    }
    it.anchor = [x, top - 4]; it.size = s * 1.2;
    return '<g class="plot ad" data-id="' + esc(it.c.id) + '">' + out + '<circle cx="' + f1(x) + '" cy="' + f1(y - s * 0.6) + '" r="' + f1(s * 0.7) + '" fill="transparent"/></g>';
  };
  // a slot: a ring of land on its orbit, dashed while it is for sale (shown only while buying), solid green once yours
  Universe.prototype.slotSVG = function (it) {
    var o = gp(it.pos[0], it.pos[1], it.pos[2]), r = 9, col = it.owned ? C.green : '#00cfff';
    it.anchor = [o[0], o[1] - 14]; it.size = r * RX * 2;
    return '<g class="plot slot' + (it.owned ? ' own' : '') + '" data-id="' + esc(it.c.id) + '"><ellipse cx="' + f1(o[0]) + '" cy="' + f1(o[1]) + '" rx="' + f1(r * RX) + '" ry="' + f1(r * RY) + '" fill="' + col + '" fill-opacity=".12" stroke="' + col + '" stroke-width="2.5"' + (it.owned ? '' : ' stroke-dasharray="7 6"') + '/>' +
      '<text x="' + f1(o[0]) + '" y="' + f1(o[1] + 6) + '" text-anchor="middle" font-family="\'JetBrains Mono\',monospace" font-weight="800" font-size="18" fill="' + col + '">' + (it.owned ? '✓' : '+') + '</text></g>';
  };
  // Buy land: the free slots show and can be clicked while it is on
  Universe.prototype.setBuying = function (on) { this.buying = !!on; this.svg.classList.toggle('buying', this.buying); this.labels(); };
  // a slot bought: the plan again (it reads what is owned) and the picture with it
  Universe.prototype.refreshLand = function () {
    (this.items || []).forEach(function (it) { if (it.el) it.el.remove(); });
    this.items = CO.uvPlan(); this.draw(); this.labels();
  };
  Universe.prototype.banner = function (it) {
    var c = it.c, self = this, pl = CO.uvPlate(it);
    if (pl === null) { if (it.el) { it.el.remove(); it.el = null; } return; }
    if (!it.el) {
      it.el = document.createElement('div'); this.bans.appendChild(it.el);
      it.el.addEventListener('pointerenter', function () { self.setHover(c.id); });
      it.el.addEventListener('pointerleave', function () { self.setHover(null); });
      it.el.addEventListener('click', function () { self.open(it.c.id); });
    }
    if (pl) { it.el.className = pl.cls; it.el.style.setProperty('--acc', CO.accentHex(c.accent)); it.el.innerHTML = pl.html; it.el._bw = 0; return; }
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
    var list = this.items.map(function (it) { return { el: it.el, x: (it.anchor[0] - v.x) * k, y: (it.anchor[1] - v.y) * k, px: it.size * k, mine: it.mine, keep: it.mine || it.kind === 'ad' || !!it.owned || String(self.hover) === String(it.c.id), d: -it.anchor[1] }; });
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
  Universe.prototype.sharePulse = function () {
    if (!CO.uvBoard || !this.items) return;
    var self = this, mine = this.h.mine ? this.h.mine() : null;
    CO.uvBoard(mine).top.forEach(function (r, i) {
      var it = self.items.filter(function (x) { return r.mine ? x.mine : !x.kind && !x.mine && String(x.c.id) === String(r.c.id); })[0];
      if (it) setTimeout(function () { self.pop(it, '+' + r.share + '% of fees', '#ffc83d'); }, i * 450);
    });
  };
  Universe.prototype.pop = function (it, label, colour) {
    if (!it.anchor) return;
    var x = it.anchor[0], y = it.anchor[1] - 64, g = document.createElementNS('http://www.w3.org/2000/svg', 'g');
    g.setAttribute('class', 'etpop');
    g.innerHTML = '<text x="' + f1(x) + '" y="' + f1(y) + '" text-anchor="middle" font-family="\'JetBrains Mono\',monospace" font-weight="800" font-size="' + (colour ? 15 : 13) + '" fill="' + (colour || C.green) + '">' + esc(label) + '</text>';
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
  Universe.prototype.flyTo = function (id, done, ms, shiftPx) {
    var it = this.find(id); if (!it || !it.anchor) { if (done) done(); return; }
    var c = this.client(), w = Math.max(1100, it.size * 2.6), h = w * c.h / c.w, m = [it.anchor[0] + (shiftPx || 0) * w / c.w, it.anchor[1] + it.size * 0.55];
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
