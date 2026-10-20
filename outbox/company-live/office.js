/* The /company mockup: the flat office. The 3D office (u3d.js) drawn as an isometric SVG, in its colours: a navy
 * sky, a slate deck on a plated hull, slate-blue tiled floors in pale frosted glass, ONE mint neon line round every
 * room (the back walls' tops, the front walls' feet), orange only while a room waits on you. World coordinates are floor tiles
 * (1 unit = one tile of the plan, the plan the 3D office reads from CO.iso), so every room, desk, monitor, wall
 * screen and task note sits where the data puts it. It is also the fallback where 3D cannot start, so it stays
 * plain SVG and CSS: flat fills, a few gradients, a handful of blurs.
 * Rooms are rebuilt only when the company's shape changes (a department added, edited or removed); everything else
 * updates in place: status classes, wall screens, task boards, plates. Packets ride the deck's lanes between the
 * rooms and the Manager; idle people get up and walk now and then. Zoom, pan, fit and focus move the viewBox, so it
 * stays sharp at any size. */
(function () {
  'use strict';
  var CO = window.CO;
  var SC = 22, C30 = Math.cos(Math.PI / 6), S30 = 0.5, RS = 7;
  // the site's palette: the Universe's flat picture draws with it (CO.iso.C), so it stays as it is
  var C = { bg: '#0a0e17', deep: '#05070a', navy: '#0b0f15', navy2: '#10151c', line: '#161d26', line2: '#1d2631',
    line3: '#27313e', plate: '#0a0d12', tile: '#11161d', text: '#e6edf7', dim: '#a9b8cc', dim2: '#7f93ad',
    cyan: '#00cfff', green: '#00ff88', red: '#ff4444', blue: '#3b82f6' };
  // The office's own colours: the 3D office's, read off u3d.js and screenshots of it (sRGB). A flat picture has no
  // light of its own, so a thing's lit side is drawn lighter: its top lightest, the face to the camera's left mid,
  // the face to its right darkest.
  var L = {
    deck: '#1b2632', deckSeam: '#111a23', rimL: '#2b3949', rimR: '#212d3b', rimHi: '#4c5e72',
    hullTop: '#3a4757', keelL: '#152029', keelR: '#0f171f', keelB: '#0a1017',
    floor: '#2f4353', seam: '#1a2732', slabL: '#1d2a36', slabR: '#16212c',
    band: '#0f161e', bandTop: '#1b2531',
    desk: '#1e262f', desk2: '#1a2129', deskR: '#151c24', deskTop: '#2e3a46', dark: '#0b1118', frame: '#2a3644',
    white: '#c6cfd7', white2: '#8d99a3', white3: '#6c7782',
    suit2: '#b3c1cf', pack: '#4a5c70', visor: '#0e2c56',
    neon: '#7cf2c4', amber: '#ff8824', hub: '#00e5ff', mint: '#38f2b8', lime: '#c8ea6a',
    text: '#eef4f8', dim: '#a9b8cc', dim2: '#7f93ad'
  };
  // What a room is doing, said as the 3D office says it: on its plate's dot and on its wall screen. The room's own
  // light stays mint, brighter while it works, orange while it waits on you.
  var STC = { working: '#24e8ff', queued: '#3b82f6', waiting: '#ff8824', idle: '#38f2b8' };
  var TONEC = { cyan: '#24e8ff', red: '#ff9438', blue: '#dfe6ee', dim: '#a9b8cc' };
  // The plan: the Manager in the middle, the weekly audit and the vault in two fixed corners, departments in the
  // slots in this order. The vault takes the front corner, where what the company earns is seen first.
  var HUB = [8, 8], AUDIT = [0, 16], VAULT = [16, 16];
  var SLOTS = [[0, 0], [8, 0], [16, 0], [0, 8], [16, 8], [8, 16], [24, 0], [24, 8], [24, 16], [24, 24], [16, 24], [8, 24], [0, 24]];
  var NS = 'http://www.w3.org/2000/svg';
  var WZ = 1.3;               // the glass walls' top: the 3D's 1.4, a little lower for this flatter angle
  var WS0 = 0.56, WS1 = 1.2;  // a wall screen's foot and top, over the dark band along the back walls
  var T = 0.35, HD = 0.45;    // the deck's thickness and the hull's under it (the 3D's 0.35 and 0.47, 2026-10-20)
  var EDGE = 'rgba(4, 8, 12, .45)';
  var SANS = "'Segoe UI','Inter',system-ui,sans-serif";

  function P(x, y, z) { return [(x - y) * SC * C30, (x + y) * SC * S30 - (z || 0) * SC]; }
  function f1(v) { return Math.round(v * 10) / 10; }
  function pts(l) { return l.map(function (p) { return f1(p[0]) + ',' + f1(p[1]); }).join(' '); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function poly(l, fill, stroke, sw, op, extra) {
    return '<polygon points="' + pts(l) + '" fill="' + fill + '"' + (stroke ? ' stroke="' + stroke + '" stroke-width="' + (sw || 0.8) + '"' : '') +
      (op != null && op !== 1 ? ' opacity="' + op + '"' : '') + (extra || '') + '/>';
  }
  function box(x, y, z, w, d, h, top, left, right, stroke, op, extra) {
    return '<g' + (extra || '') + '>' +
      poly([P(x, y + d, z), P(x + w, y + d, z), P(x + w, y + d, z + h), P(x, y + d, z + h)], left, stroke, 0.6, op) +
      poly([P(x + w, y, z), P(x + w, y + d, z), P(x + w, y + d, z + h), P(x + w, y, z + h)], right, stroke, 0.6, op) +
      poly([P(x, y, z + h), P(x + w, y, z + h), P(x + w, y + d, z + h), P(x, y + d, z + h)], top, stroke, 0.6, op) + '</g>';
  }
  // a piece of furniture: a box with a hairline of shadow round its faces, so the shapes stay clean
  function fb(x, y, z, w, d, h, top, left, right) { return box(x, y, z, w, d, h, top, left, right, EDGE); }
  function text(x, y, s, size, fill, weight, anchor, fam, extra) {
    var f = fam === 'display' ? "'Archivo Black',sans-serif" : fam === 'sans' ? SANS : "'JetBrains Mono',monospace";
    return '<text x="' + f1(x) + '" y="' + f1(y) + '" font-family="' + f + '" font-size="' + size + '" fill="' + fill +
      '" font-weight="' + (weight || 400) + '" text-anchor="' + (anchor || 'start') + '"' + (extra || '') + '>' + esc(s) + '</text>';
  }
  function line(a, b, stroke, w, extra) {
    return '<line x1="' + f1(a[0]) + '" y1="' + f1(a[1]) + '" x2="' + f1(b[0]) + '" y2="' + f1(b[1]) + '"' +
      (stroke ? ' stroke="' + stroke + '" stroke-width="' + w + '"' : '') + (extra || '') + '/>';
  }
  function pline(l, cls, extra) { return '<polyline' + (cls ? ' class="' + cls + '"' : '') + ' points="' + pts(l) + '" fill="none"' + (extra || '') + '/>'; }
  // a flat drawing on a back wall: x along the wall in pixels from x0 + u, y down from zTop
  function onBack(x0, u, yPlane, zTop) {
    var o = P(x0 + u, yPlane, zTop);
    return 'matrix(' + C30.toFixed(4) + ' ' + S30 + ' 0 1 ' + f1(o[0]) + ' ' + f1(o[1]) + ')';
  }
  function onSide(xPlane, y0, v, zTop) {
    var o = P(xPlane, y0 + v, zTop);
    return 'matrix(' + (-C30).toFixed(4) + ' ' + S30 + ' 0 1 ' + f1(o[0]) + ' ' + f1(o[1]) + ')';
  }
  // the same on the left back wall, read from the camera: x runs from its near end (y0 + v) towards its far one
  function onLeft(xPlane, y0, v, zTop) {
    var o = P(xPlane, y0 + v, zTop);
    return 'matrix(' + C30.toFixed(4) + ' ' + (-S30) + ' 0 1 ' + f1(o[0]) + ' ' + f1(o[1]) + ')';
  }
  function cut(s, n) { s = String(s || ''); return s.length > n ? s.slice(0, n - 1) + '…' : s; }
  function rng(s) { s = Math.floor(s) % 2147483647 || 1; return function () { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646; }; }
  // a colour a shade lighter (k > 0) or darker (k < 0)
  function shade(hex, k) {
    var n = parseInt(hex.slice(1), 16), f = function (c) { return Math.max(0, Math.min(255, Math.round(k < 0 ? c * (1 + k) : c + (255 - c) * k))); };
    return '#' + ((1 << 24) | (f(n >> 16) << 16) | (f(n >> 8 & 255) << 8) | f(n & 255)).toString(16).slice(1);
  }
  // A circle lying flat at height z, seen from the office's angle, is an ellipse this much wider than tall
  var RXc = SC * C30 * Math.SQRT2, RYc = SC * S30 * Math.SQRT2;
  function disc(cx, cy, z, r, fill, stroke, sw, extra) {
    var c = P(cx, cy, z);
    return '<ellipse cx="' + f1(c[0]) + '" cy="' + f1(c[1]) + '" rx="' + f1(r * RXc) + '" ry="' + f1(r * RYc) + '" fill="' + fill + '"' +
      (stroke ? ' stroke="' + stroke + '" stroke-width="' + sw + '"' : '') + (extra || '') + '/>';
  }
  // an arc of that circle, from a0 to a1 radians round its centre on the plan
  function arc(cx, cy, z, r, a0, a1) {
    var l = [], n = Math.max(6, Math.ceil(Math.abs(a1 - a0) * 9));
    for (var i = 0; i <= n; i++) { var a = a0 + (a1 - a0) * i / n; l.push(P(cx + Math.cos(a) * r, cy + Math.sin(a) * r, z)); }
    return l;
  }
  // a cylinder standing on the floor plan: its front band and its top
  function cyl(cx, cy, z0, z1, r, top, side, stroke) {
    var a = P(cx, cy, z0), b = P(cx, cy, z1), rx = r * RXc, ry = r * RYc;
    return '<path d="M' + f1(a[0] - rx) + ',' + f1(b[1]) + ' A' + f1(rx) + ',' + f1(ry) + ' 0 0 0 ' + f1(a[0] + rx) + ',' + f1(b[1]) +
      ' L' + f1(a[0] + rx) + ',' + f1(a[1]) + ' A' + f1(rx) + ',' + f1(ry) + ' 0 0 1 ' + f1(a[0] - rx) + ',' + f1(a[1]) + ' Z" fill="' + side + '" stroke="' + stroke + '" stroke-width=".5"/>' +
      '<ellipse cx="' + f1(b[0]) + '" cy="' + f1(b[1]) + '" rx="' + f1(rx) + '" ry="' + f1(ry) + '" fill="' + top + '" stroke="' + stroke + '" stroke-width=".5"/>';
  }
  // a band of a cylinder's wall between two heights: the half towards the camera (front) or away from it
  function band(cx, cy, z0, z1, r, front, fill, extra) {
    var a = P(cx, cy, z0), b = P(cx, cy, z1), rx = f1(r * RXc), ry = f1(r * RYc), s0 = front ? 0 : 1, s1 = front ? 1 : 0;
    return '<path d="M' + f1(a[0] - rx) + ',' + f1(a[1]) + ' A' + rx + ',' + ry + ' 0 0 ' + s0 + ' ' + f1(a[0] + rx) + ',' + f1(a[1]) +
      ' L' + f1(b[0] + rx) + ',' + f1(b[1]) + ' A' + rx + ',' + ry + ' 0 0 ' + s1 + ' ' + f1(b[0] - rx) + ',' + f1(b[1]) + ' Z" fill="' + fill + '"' + (extra || '') + '/>';
  }
  // what stands in a room, drawn back to front by where it stands on the plan
  function sortJoin(items) {
    return items.map(function (it, i) { return [it[0], i, it[1]]; }).sort(function (a, b) { return a[0] - b[0] || a[1] - b[1]; })
      .map(function (it) { return it[2]; }).join('');
  }
  // text widths for the plates, from a canvas with the plates' own fonts (a width read before the web fonts are in is
  // the fallback's, so it is kept only once they are)
  var MCX = null, MW = {};
  function measure(s, font, ls) {
    var k = font + '|' + s;
    if (MW[k] != null) return MW[k];
    if (MCX === null) { try { MCX = document.createElement('canvas').getContext('2d'); } catch (e) { MCX = false; } }
    var w;
    if (MCX) { MCX.font = font; w = MCX.measureText(s).width; } else w = s.length * parseFloat(font.split(' ')[1]) * 0.62;
    w += (ls || 0) * s.length;
    if (!document.fonts || document.fonts.status === 'loaded') MW[k] = w;
    return w;
  }

  /* ---------------- pieces ---------------- */
  // Every role's helmet in the 3D office's colour for it (u3d.js, agent()'s role skins), so an astronaut tells its
  // role in the flat office too; the researcher keeps the suit's own blue, and so does an unknown role. The QA tester's
  // and the trader's visors are tinted as theirs are.
  var ROLE2D = { qa_tester: ['#c4532f', '#160a08'], trader: ['#c49035', '#6a4a14'], developer: ['#1c9cb4'], lab_scientist: ['#5aa888'], auditor: ['#8a9bb0'],
    designer: ['#9c4cc4'], manager: ['#bccad6'], supervisor: ['#1d3656'] };
  var ROLEDEFS = Object.keys(ROLE2D).map(function (k) {
    var c = ROLE2D[k][0];
    return '<radialGradient id="g-helmet-' + k + '" cx=".36" cy=".3" r=".78"><stop offset="0" stop-color="' + shade(c, 0.45) + '"/><stop offset=".55" stop-color="' + c +
      '"/><stop offset="1" stop-color="' + shade(c, -0.45) + '"/></radialGradient>';
  }).join('');
  var DEFS = '<defs>' + ROLEDEFS +
    '<filter id="glow" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="2.2" result="b"/>' +
    '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>' +
    '<filter id="glowS" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="1.1" result="b"/>' +
    '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>' +
    '<filter id="glow2" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="2.6"/></filter>' +
    // a room's floor while it works: a faint mint wash; while it waits on you and in the trading desk, the 3D's pool
    // of orange light, brightest in the middle, gone at its walls
    grad('g-fglow', L.neon, 0.16) + grad('g-fglow-b', C.blue, 0.12) +
    '<radialGradient id="g-fglow-o"><stop offset="0" stop-color="#ff7a3c" stop-opacity=".6"/><stop offset=".45" stop-color="#ff6a30" stop-opacity=".28"/>' +
    '<stop offset="1" stop-color="#ff6a30" stop-opacity="0"/></radialGradient>' +
    grad('g-spill', L.neon, 0.3) + grad('g-ping', L.hub, 0.5) +
    halo('g-halo-c', L.hub) + halo('g-halo-g', L.mint) + halo('g-halo-r', L.amber) + halo('g-halo-b', C.blue) + halo('g-halo-q', '#9ff5ec') +
    // the column of light over the Manager's dais: soft at its sides, brightest at its foot
    '<radialGradient id="g-beam" cx=".5" cy=".78" r=".6"><stop offset="0" stop-color="#9ff4ff" stop-opacity=".42"/>' +
    '<stop offset=".55" stop-color="#7fe8f8" stop-opacity=".16"/><stop offset="1" stop-color="#7fe8f8" stop-opacity="0"/></radialGradient>' +
    // the glass: a pale frosted pane, catching more light at its top; the trading desk's warmed by its light
    pane('g-paneB', '#c9dbe4', 0.15, '#a9bfca', 0.05) + pane('g-paneF', '#c9dbe4', 0.08, '#a9bfca', 0.025) + pane('g-paneO', '#ffc49c', 0.14, '#ffb084', 0.05) +
    '<linearGradient id="g-scr" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0a1622"/><stop offset="1" stop-color="#050c14"/></linearGradient>' +
    // a room's ceiling lamp on its floor: plain white light
    '<radialGradient id="g-lamp"><stop offset="0" stop-color="#eef6ff" stop-opacity=".13"/><stop offset=".6" stop-color="#eef6ff" stop-opacity=".04"/><stop offset="1" stop-color="#eef6ff" stop-opacity="0"/></radialGradient>' +
    // the hull's two sides you see: the left one lit, the right one in shade
    '<linearGradient id="g-hullL" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#303d4c"/><stop offset="1" stop-color="#222c38"/></linearGradient>' +
    '<linearGradient id="g-hullR" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#252f3c"/><stop offset="1" stop-color="#19222c"/></linearGradient>' +
    // an astronaut's white suit, lit from the left, and the blue helmet
    '<linearGradient id="g-suit" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#f4f8fb"/><stop offset="1" stop-color="#b9c7d4"/></linearGradient>' +
    '<radialGradient id="g-helmet" cx=".36" cy=".3" r=".78"><stop offset="0" stop-color="#9cc0e6"/><stop offset=".55" stop-color="#4e74a0"/><stop offset="1" stop-color="#2a4466"/></radialGradient>' +
    '<radialGradient id="g-shadow"><stop offset="0" stop-color="#03060a" stop-opacity=".75"/><stop offset="1" stop-color="#03060a" stop-opacity="0"/></radialGradient>' +
    // the Manager's core: white-hot, a cyan halo round it, and the cyan light on the floor round its dais
    '<radialGradient id="g-core"><stop offset="0" stop-color="#ffffff"/><stop offset=".22" stop-color="#e6fdff" stop-opacity=".95"/>' +
    '<stop offset=".5" stop-color="#7fe8f8" stop-opacity=".32"/><stop offset="1" stop-color="#24e8ff" stop-opacity="0"/></radialGradient>' +
    '<radialGradient id="g-hubf"><stop offset="0" stop-color="#00e1ff" stop-opacity=".22"/><stop offset=".55" stop-color="#00c3eb" stop-opacity=".08"/><stop offset="1" stop-color="#00c3eb" stop-opacity="0"/></radialGradient>' +
    // the Add-department pad: a faint teal disc and its wall of teal light, brightest along its top
    '<radialGradient id="g-pad"><stop offset="0" stop-color="#14917d" stop-opacity="0"/><stop offset=".7" stop-color="#0e8c82" stop-opacity=".04"/><stop offset="1" stop-color="#20cdac" stop-opacity=".16"/></radialGradient>' +
    '<linearGradient id="g-padw" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#3ad8c4" stop-opacity=".55"/><stop offset=".3" stop-color="#2cc8b4" stop-opacity=".2"/><stop offset="1" stop-color="#1ea896" stop-opacity=".07"/></linearGradient>' +
    // Cymetica QA's window of light, and the vault door's brushed steel lit from the top left
    '<linearGradient id="g-qa" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#dcfff8"/><stop offset="1" stop-color="#58f2dc"/></linearGradient>' +
    '<radialGradient id="g-door" cx=".38" cy=".32" r=".82"><stop offset="0" stop-color="#7d8999"/><stop offset=".6" stop-color="#4a5664"/><stop offset="1" stop-color="#29323d"/></radialGradient>' +
    '<linearGradient id="g-steel" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#a7b2bf"/><stop offset=".5" stop-color="#5d6977"/><stop offset="1" stop-color="#343e4a"/></linearGradient>' +
    '</defs>';
  function grad(id, c, op) {
    return '<radialGradient id="' + id + '"><stop offset="0" stop-color="' + c + '" stop-opacity="' + op + '"/><stop offset="1" stop-color="' + c + '" stop-opacity="0"/></radialGradient>';
  }
  function halo(id, c) {
    return '<radialGradient id="' + id + '"><stop offset="0" stop-color="' + c + '" stop-opacity=".95"/><stop offset=".35" stop-color="' + c +
      '" stop-opacity=".45"/><stop offset="1" stop-color="' + c + '" stop-opacity="0"/></radialGradient>';
  }
  function pane(id, c0, o0, c1, o1) {
    return '<linearGradient id="' + id + '" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="' + c0 + '" stop-opacity="' + o0 + '"/>' +
      '<stop offset="1" stop-color="' + c1 + '" stop-opacity="' + o1 + '"/></linearGradient>';
  }
  // the sky's stars, one tile of them repeated behind the office: small, sharp, mostly white, a few in cyan, a few
  // brighter with a soft halo -- about one to every 2,500 px, as the 3D's sky
  function starTile() {
    var R = rng(20261019), W = 620, out = '<svg xmlns="http://www.w3.org/2000/svg" width="' + W + '" height="' + W + '">';
    for (var i = 0; i < 150; i++) {
      var x = f1(R() * W), y = f1(R() * W), b = R(), r = b > 0.96 ? 1.2 : b > 0.82 ? 0.8 : 0.5, col = R() < 0.12 ? '#9fe8ff' : '#ffffff';
      if (r > 1) out += '<circle cx="' + x + '" cy="' + y + '" r="3.4" fill="' + col + '" opacity=".1"/>';
      out += '<circle cx="' + x + '" cy="' + y + '" r="' + r + '" fill="' + col + '" opacity="' + (0.3 + R() * 0.6).toFixed(2) + '"/>';
    }
    return 'url("data:image/svg+xml,' + encodeURIComponent(out + '</svg>') + '")';
  }

  // An astronaut as in the 3D office: a white suit, a grey pack on the back, a helmet in its role's colour (blue for
  // the rest) with a dark visor and its shine. Feet at 0,0; the name tag over the helmet shows only in the room under
  // the mouse or the one open.
  function avatar(label, role) {
    var w = 5.8 * label.length + 10, rs = ROLE2D[role];
    return '<ellipse cx="0" cy="0" rx="8" ry="3.4" fill="url(#g-shadow)"/>' +
      '<ellipse class="ring" cx="0" cy="0" rx="11" ry="5"/><ellipse class="ring2" cx="0" cy="0" rx="11" ry="5"/>' +
      '<g class="bob">' +
      '<rect x="-4.3" y="-8.6" width="3.6" height="8" rx="1.6" fill="' + L.suit2 + '"/><rect x=".7" y="-8.6" width="3.6" height="8" rx="1.6" fill="' + L.suit2 + '"/>' +
      '<rect x="-4.7" y="-2.3" width="4.1" height="2.5" rx="1" fill="' + L.pack + '"/><rect x=".6" y="-2.3" width="4.1" height="2.5" rx="1" fill="' + L.pack + '"/>' +
      '<rect x="-3.8" y="-18.8" width="10.2" height="9.8" rx="2.6" fill="' + L.pack + '"/>' +
      '<rect x="-7.7" y="-16.4" width="3.4" height="9.2" rx="1.7" fill="url(#g-suit)"/><rect x="4.3" y="-16.4" width="3.4" height="9.2" rx="1.7" fill="' + L.suit2 + '"/>' +
      '<rect class="body" x="-5.4" y="-17.6" width="10.8" height="10.8" rx="4.2"/>' +
      '<rect x="-2.9" y="-14.7" width="5.8" height="3.1" rx=".9" fill="' + L.pack + '"/><circle class="chest" cx="1.3" cy="-13.15" r=".8"/>' +
      '<ellipse cx="0" cy="-17.4" rx="4.5" ry="1.45" fill="' + L.pack + '"/>' +
      '<circle cx="0" cy="-22.2" r="5.7" fill="url(#g-helmet' + (rs ? '-' + role : '') + ')"/>' +
      '<ellipse cx="-1.2" cy="-21.8" rx="3.9" ry="2.8" fill="' + (rs && rs[1] || L.visor) + '"/>' +
      '<ellipse cx="-2.5" cy="-22.8" rx="1.3" ry=".75" fill="#cfe6ff" opacity=".75"/></g>' +
      (label ? '<g class="lbl"><rect x="' + f1(-w / 2) + '" y="-41" width="' + f1(w) + '" height="11.5" rx="5.75"/>' +
        text(0, -32.4, label, 7.4, L.text, 600, 'middle') + '</g>' : '');
  }
  function agentAt(x, y, key, i, label, role) {
    var p = P(x, y, 0.1);
    return '<g class="agent idle" data-agent="' + key + ':' + i + '" data-hx="' + f1(p[0]) + '" data-hy="' + f1(p[1]) +
      '" transform="translate(' + f1(p[0]) + ' ' + f1(p[1]) + ')">' + avatar(label, role) + '</g>';
  }
  // a screen on a stand, facing the room: dark glass that lights mint while its expert works, its code typing over it
  function monitor(mx, my, mz, mw, mh, i) {
    var md = 0.05, out = '';
    out += poly([P(mx + mw, my, mz), P(mx + mw, my + md, mz), P(mx + mw, my + md, mz + mh), P(mx + mw, my, mz + mh)], L.dark);
    out += poly([P(mx, my, mz + mh), P(mx + mw, my, mz + mh), P(mx + mw, my + md, mz + mh), P(mx, my + md, mz + mh)], L.frame);
    out += poly([P(mx, my + md, mz), P(mx + mw, my + md, mz), P(mx + mw, my + md, mz + mh), P(mx, my + md, mz + mh)], '#0a1016', L.frame, 0.5, 1,
      ' class="mon" data-i="' + i + '"');
    out += '<g class="code" transform="' + onBack(mx, 0.08, my + md, mz + mh - 0.05) + '">';
    [11, 7, 9, 5].forEach(function (w, k) {
      out += '<rect class="ln" x="1" y="' + f1(0.9 + k * 1.8) + '" width="' + w + '" height=".8" fill="' + C.deep + '" style="animation-delay:' + (-k * 0.55 - i * 0.3).toFixed(2) + 's"/>';
    });
    return out + '</g>';
  }
  // a desk facing the back wall, as the 3D's: a top on two side panels and a drawer unit, two screens, a keyboard, a mug
  function desk(x, y, i) {
    var out = fb(x + 0.04, y + 0.06, 0.1, 0.12, 0.72, 0.34, L.desk, L.desk, L.deskR) +
      fb(x + 1.1, y + 0.08, 0.1, 0.6, 0.66, 0.32, L.desk, L.desk2, L.deskR) +
      fb(x + 1.74, y + 0.06, 0.1, 0.12, 0.72, 0.34, L.desk, L.desk, L.deskR);
    out += fb(x, y, 0.44, 1.9, 0.86, 0.05, L.deskTop, '#25303b', '#1b232c');
    var sp = P(x + 0.95, y + 0.5, 0.49);
    out += '<ellipse class="spill" data-i="' + i + '" cx="' + f1(sp[0]) + '" cy="' + f1(sp[1]) + '" rx="22" ry="9" fill="url(#g-spill)"/>';
    [x + 0.1, x + 1.0].forEach(function (mx) {
      out += fb(mx + 0.36, y + 0.2, 0.49, 0.08, 0.06, 0.08, L.frame, L.frame, L.dark);
      out += monitor(mx, y + 0.12, 0.56, 0.8, 0.36, i);
    });
    out += fb(x + 0.64, y + 0.5, 0.49, 0.62, 0.2, 0.02, '#3a4756', L.frame, L.dark);
    out += cyl(x + 1.62, y + 0.62, 0.49, 0.6, 0.055, L.white, L.white2, L.white3);
    return out;
  }
  // the department's computer: a console in the back corner whose screen opens the department's page on cymetica.com
  function terminal(x, y, link) {
    var out = '<g class="pc" data-link="' + esc(link.url) + '" data-label="' + esc(link.label) + '">';
    var fl = P(x + 0.62, y + 0.95, 0.1);
    out += '<ellipse class="pcglow" cx="' + f1(fl[0]) + '" cy="' + f1(fl[1]) + '" rx="30" ry="12" fill="url(#g-spill)"/>';
    out += fb(x, y, 0.1, 1.25, 0.8, 0.36, L.deskTop, L.desk, L.deskR);
    var mx = x + 0.08, my = y + 0.1, mz = 0.46, mw = 1.09, md = 0.08, mh = 0.64;
    out += poly([P(mx + mw, my, mz), P(mx + mw, my + md, mz), P(mx + mw, my + md, mz + mh), P(mx + mw, my, mz + mh)], L.dark);
    out += poly([P(mx, my, mz + mh), P(mx + mw, my, mz + mh), P(mx + mw, my + md, mz + mh), P(mx, my + md, mz + mh)], L.frame);
    out += poly([P(mx, my + md, mz), P(mx + mw, my + md, mz), P(mx + mw, my + md, mz + mh), P(mx, my + md, mz + mh)], '#06261f', L.mint, 1, 1, ' class="pcscr"');
    var sc = P(mx + mw / 2, my + md, mz + mh / 2);
    out += text(sc[0], sc[1] + 5, '↗', 14, L.mint, 700, 'middle', null, ' class="pcarrow" filter="url(#glowS)"');
    return out + '</g>';
  }
  function plant(x, y, k) {
    k = k || 1;
    var out = cyl(x, y, 0.1, 0.1 + 0.34 * k, 0.22 * k, '#2c3742', '#232c36', '#161d25'), c = P(x, y, 0.1 + 0.34 * k);
    [[-3.6, -5.5, 5.6, '#1d5a3f'], [3.8, -6.5, 5.2, '#22684a'], [0, -9.5, 6, '#277553'], [-2, -13, 4.4, '#2e875f'], [2.4, -12.4, 3.6, '#349466']].forEach(function (l) {
      out += '<circle cx="' + f1(c[0] + l[0] * k) + '" cy="' + f1(c[1] + l[1] * k) + '" r="' + f1(l[2] * k) + '" fill="' + l[3] + '"/>';
    });
    return out + '<circle cx="' + f1(c[0] - 1.5 * k) + '" cy="' + f1(c[1] - 14.5 * k) + '" r="' + f1(1.8 * k) + '" fill="#6fe0a6" opacity=".35"/>';
  }
  // server racks in a row, fronts to the room: charcoal towers with blinking lights and a mint strip along the top
  function racks(x, y, n, step) {
    var out = '';
    for (var i = 0; i < n; i++) {
      var rx = x + i * (step || 0.72);
      out += fb(rx, y, 0.1, 0.62, 0.68, 1.1, '#24303c', '#151d26', '#10171f');
      out += '<g transform="' + onBack(rx, 0.06, y + 0.68, 1.16) + '"><rect x="0" y=".5" width="11.6" height=".9" fill="' + L.mint + '" opacity=".75"/>';
      for (var k = 0; k < 5; k++) {
        out += '<rect x="1" y="' + f1(3 + k * 4.2) + '" width="9.6" height="2.8" fill="#0b1118"/>';
        for (var j = 0; j < 2; j++) {
          out += '<rect class="led" x="' + (2 + j * 4.6) + '" y="' + f1(3.8 + k * 4.2) + '" width="2.2" height="1.1" fill="' + [L.mint, L.hub, C.blue][(i + k + j) % 3] +
            '" style="animation-delay:' + (-((i * 7 + k * 3 + j * 5) % 11) * 0.17).toFixed(2) + 's"/>';
        }
      }
      out += '</g>';
    }
    return out;
  }
  // a low cabinet against a wall
  function cabinet(x, y, w, d, h) { return fb(x, y, 0.1, w, d, h, L.deskTop, L.desk, L.deskR); }
  // a see-through screen in a yellow-green frame on a slim stand, a small ring of light in it, as every 3D room has
  function holoFrame(x, y) {
    var out = line(P(x, y, 0.1), P(x, y, 0.64), L.frame, 1.4);
    return out + '<g transform="' + onBack(x - 0.47, 0, y, 1.18) + '"><rect x="0" y="0" width="20.9" height="12.3" fill="rgba(106, 138, 58, .22)" stroke="' + L.lime + '" stroke-width=".8"/>' +
      '<circle cx="10.45" cy="6.15" r="1.6" fill="none" stroke="' + L.lime + '" stroke-width=".6"/></g>';
  }
  // the laboratory's instruments: a white cabinet with a terminal on it, its screen a cyan-green hologram of data
  function labMachine(x, y) {
    var out = fb(x, y, 0.1, 1.15, 0.8, 0.5, L.white, L.white2, L.white3);
    out += fb(x + 0.08, y + 0.14, 0.6, 1.0, 0.46, 0.4, L.white, L.white2, L.white3);
    var mx = x + 0.16, my = y + 0.6, z0 = 0.66, z1 = 0.94, w = 0.84;
    out += poly([P(mx, my, z0), P(mx + w, my, z0), P(mx + w, my, z1), P(mx, my, z1)], 'rgba(32, 235, 255, .3)', '#38f5d2', 0.6);
    out += '<g transform="' + onBack(mx, 0, my, z1) + '"><polyline points="1.5,3.4 3.5,2.4 5.5,3.8 7.5,1.9 9.5,3 11.5,1.6 13.5,2.9 15.5,2.2 17,3.5" fill="none" stroke="#38ffb4" stroke-width=".6"/>';
    for (var k = 0; k < 6; k++) out += '<rect x="' + (2 + k * 2.6) + '" y="' + (5.4 - (k * 1.3 % 1.8)) + '" width="1.6" height="' + (0.6 + (k * 1.3 % 1.8)) + '" fill="#24e8ff" opacity=".85"/>';
    out += '</g>';
    for (var j = 0; j < 3; j++) {
      var l = P(x + 0.3 + j * 0.2, y + 0.8, 0.3);
      out += '<rect class="led" x="' + f1(l[0] - 1.2) + '" y="' + f1(l[1] - 0.6) + '" width="2.4" height="1.2" fill="' + (j % 2 ? L.mint : L.hub) + '" style="animation-delay:' + (-j * 0.5) + 's"/>';
    }
    return out;
  }
  // a white base with a holographic crystal of data turning over it
  function labHolo(x, y) {
    var out = fb(x, y, 0.1, 1.2, 0.85, 0.42, L.white, L.white2, L.white3) + fb(x + 0.12, y + 0.1, 0.52, 0.96, 0.65, 0.04, '#d6dde3', L.white2, L.white3);
    var cx = x + 0.6, cy = y + 0.42, m = 1.04, r = 0.3, t = P(cx, cy, 1.34), b = P(cx, cy, 0.74);
    var e = P(cx + r, cy, m), w = P(cx - r, cy, m), s = P(cx, cy + r, m), h = P(cx, cy, m);
    out += '<ellipse cx="' + f1(h[0]) + '" cy="' + f1(h[1]) + '" rx="20" ry="18" fill="url(#g-halo-q)" opacity=".32"/>';
    out += '<g class="crys">' + [[t, w, s], [t, s, e], [b, w, s], [b, s, e]].map(function (f) { return poly(f, 'rgba(111, 245, 208, .36)', '#bffff0', 0.6); }).join('') + '</g>';
    return out;
  }
  function canisters(x, y) {
    var out = '';
    [[-0.45, 0.3, 0.34], [0, 0, 0.46], [0, 0.55, 0.4], [0, 1.1, 0.46]].sort(function (a, b) { return a[0] + a[1] - b[0] - b[1]; }).forEach(function (c) {
      out += cyl(x + c[0], y + c[1], 0.1, 0.1 + c[2], 0.18, L.white, L.white2, L.white3);
      out += cyl(x + c[0], y + c[1], 0.1 + c[2], 0.15 + c[2], 0.13, '#8ff4ff', '#24c8e0', '#1aa0b8');
    });
    return out;
  }
  // the weekly audit's consoles: white cabinets with a green screen and a lit keyboard
  function console3(x, y) {
    var out = fb(x, y, 0.1, 1.2, 0.72, 0.44, L.white, L.white2, L.white3) + fb(x + 0.08, y + 0.04, 0.54, 1.04, 0.24, 0.5, L.white, L.white2, L.white3);
    var mx = x + 0.17, my = y + 0.28, z0 = 0.62, z1 = 0.96, w = 0.86;
    out += poly([P(mx, my, z0), P(mx + w, my, z0), P(mx + w, my, z1), P(mx, my, z1)], '#06261f', L.mint, 0.5);
    out += '<g transform="' + onBack(mx, 0, my, z1) + '">';
    [12, 8, 14, 6].forEach(function (lw, k) { out += '<rect x="1.4" y="' + f1(1.3 + k * 1.6) + '" width="' + lw + '" height=".7" fill="' + L.mint + '" opacity=".75"/>'; });
    out += '</g>';
    return out + poly([P(x + 0.15, y + 0.36, 0.545), P(x + 1.05, y + 0.36, 0.545), P(x + 1.05, y + 0.6, 0.545), P(x + 0.15, y + 0.6, 0.545)], 'rgba(56, 242, 184, .32)');
  }
  // a printer for the audit's report
  function printer(x, y) {
    return fb(x, y, 0.1, 1.0, 0.8, 0.5, L.white, L.white2, L.white3) + fb(x + 0.1, y + 0.1, 0.6, 0.8, 0.6, 0.06, '#d6dde3', L.white2, L.white3) +
      line(P(x + 0.2, y + 0.8, 0.42), P(x + 0.8, y + 0.8, 0.42), L.dark, 1.2);
  }
  // Cymetica QA's window of light: a grid of glowing panes at the right end of the back wall, rising over it
  function qaWindow(x0, y0) {
    var w = 1.1 * SC, h = 0.8 * SC, c = P(x0 + 6.05, y0 + 0.2, 1.02), pd = 1.4, cw = (w - pd * 5) / 4, ch = (h - pd * 4) / 3;
    var out = '<ellipse cx="' + f1(c[0]) + '" cy="' + f1(c[1]) + '" rx="36" ry="26" fill="url(#g-halo-q)" opacity=".2"/>';
    out += '<g transform="' + onBack(x0, 5.5, y0 + 0.12, 1.42) + '"><rect x="-1" y="-1" width="' + f1(w + 2) + '" height="' + f1(h + 2) + '" fill="' + L.dark + '"/>' +
      '<rect width="' + f1(w) + '" height="' + f1(h) + '" fill="#051418"/>';
    for (var r = 0; r < 3; r++) for (var k = 0; k < 4; k++) {
      out += '<rect x="' + f1(pd + k * (cw + pd)) + '" y="' + f1(pd + r * (ch + pd)) + '" width="' + f1(cw) + '" height="' + f1(ch) + '" fill="url(#g-qa)"/>';
    }
    return out + '</g>';
  }
  // the trading desk's chart walls across both back walls, in the site's green: orange is for a room waiting on you
  function chartWall(tf, w, h) {
    var out = '<g transform="' + tf + '"><rect x="0" y="0" width="' + f1(w) + '" height="' + f1(h) + '" fill="#04140e" stroke="#38f5b8" stroke-width=".7"/>';
    out += text(2.6, 4.2, 'ALPHA FLOW · +6.2% ROI', 3, '#7cf2c4', 700);
    for (var gy = 6; gy < h - 1.5; gy += 2.6) out += '<rect x="1.5" y="' + f1(gy) + '" width="' + f1(w - 3) + '" height=".25" fill="#38f5b8" opacity=".2"/>';
    for (var i = 0; i < Math.floor((w - 4) / 4.6); i++) { var bh = 1.4 + ((i * 19) % 28) / 9; out += '<rect x="' + f1(2.2 + i * 4.6) + '" y="' + f1(h - 1.4 - bh) + '" width="2.6" height="' + f1(bh) + '" fill="' + (i % 4 === 2 ? '#ff4f5e' : '#38f5b8') + '" opacity=".42"/>'; }
    var l = [];
    for (var x = 2; x < w - 2; x += 1.6) l.push([x, h * 0.6 + Math.sin(x * 0.3) * h * 0.14 + Math.cos(x * 0.71) * h * 0.06]);
    out += '<polyline points="' + pts(l) + '" fill="none" stroke="#38f5b8" stroke-width=".7" stroke-linejoin="round"/>';
    return out + '</g>';
  }
  function mood(x0, y0, u0, u1) {
    var yp = y0 + 0.13, w = (u1 - u0) * SC;
    var out = poly([P(x0 + u0, yp, WS0), P(x0 + u1, yp, WS0), P(x0 + u1, yp, WS1), P(x0 + u0, yp, WS1)], '#08121c', '#1c3248', 0.8);
    out += '<g transform="' + onBack(x0, u0, yp, WS1) + '">';
    ['#24e8ff', '#38f5b8', '#3b82f6', '#ff8824'].forEach(function (c, i) { out += '<rect x="' + (2.2 + i * 4.6) + '" y="1.8" width="3.6" height="3.6" rx=".5" fill="' + c + '"/>'; });
    out += '<rect x="2.2" y="7.2" width="16" height="5.4" rx=".5" fill="none" stroke="' + L.dim2 + '" stroke-width=".45"/>';
    out += '<rect x="21" y="1.8" width="' + f1(w - 23.4) + '" height="10.8" rx=".5" fill="none" stroke="#24e8ff" stroke-width=".45" stroke-dasharray="1.4 1.2"/></g>';
    return out;
  }

  // The glass room of the 3D office, in two halves. What stands behind its contents: the floor of large slate-blue
  // tiles, its lamp's pool and the light of what the room does, the two pale back panes with a dark band along
  // their foot, and the neon along their top. What stands in front: the two front panes, their pale top edges and
  // corners, and the neon along their foot -- so the one neon line traces the room as the camera sees it.
  function shellBack(x0, y0, kind) {
    var out = '', z0 = 0.1;
    out += poly([P(x0, y0 + RS, 0), P(x0, y0 + RS, WZ), P(x0, y0, WZ), P(x0 + RS, y0, WZ), P(x0 + RS, y0, 0), P(x0 + RS, y0 + RS, 0)], 'transparent', null, 0, 1, ' class="hit"');
    var R = rng(29 + x0 * 7 + y0 * 13), n = 4, s = RS / n, g = 0.035;
    var base = kind === 'hub' ? '#33495a' : L.floor;
    out += box(x0, y0, 0, RS, RS, z0, L.seam, L.slabL, L.slabR);
    for (var i = 0; i < n; i++) for (var j = 0; j < n; j++) {
      out += poly([P(x0 + i * s + g, y0 + j * s + g, z0), P(x0 + (i + 1) * s - g, y0 + j * s + g, z0), P(x0 + (i + 1) * s - g, y0 + (j + 1) * s - g, z0),
        P(x0 + i * s + g, y0 + (j + 1) * s - g, z0)], shade(base, R() * 0.07 - 0.035));
    }
    var cc = P(x0 + RS / 2, y0 + RS / 2, z0), el = function (cls, k, fill) {
      return '<ellipse class="' + cls + '" cx="' + f1(cc[0]) + '" cy="' + f1(cc[1]) + '" rx="' + f1(RS * SC * k) + '" ry="' + f1(RS * SC * k * 0.575) + '"' + (fill ? ' fill="' + fill + '"' : '') + '/>';
    };
    out += el('lamp', 0.8, 'url(#g-lamp)') + el('fglow', 0.86) + el('fping', 0.8, 'url(#g-ping)');
    out += poly([P(x0, y0, z0), P(x0 + RS, y0, z0), P(x0 + RS, y0 + RS, z0), P(x0, y0 + RS, z0)], '#ffffff', null, 0, 1, ' class="hl" fill-opacity=".05"');
    out += poly([P(x0, y0 + RS, z0), P(x0, y0, z0), P(x0, y0, WZ), P(x0, y0 + RS, WZ)], 'url(#g-paneB)', null, 0, 1, ' class="pane"');
    out += poly([P(x0, y0, z0), P(x0 + RS, y0, z0), P(x0 + RS, y0, WZ), P(x0, y0, WZ)], 'url(#g-paneB)', null, 0, 1, ' class="pane"');
    if (kind !== 'hub') {
      out += box(x0 + 0.04, y0 + 0.04, z0, 0.1, RS - 0.08, 0.46, L.bandTop, L.band, L.band);
      out += box(x0 + 0.04, y0 + 0.04, z0, RS - 0.08, 0.1, 0.46, L.bandTop, L.band, L.band);
    }
    out += line(P(x0, y0, z0), P(x0, y0, WZ), null, 0, ' class="gedge"');
    var nb = [P(x0, y0 + RS, WZ), P(x0, y0, WZ), P(x0 + RS, y0, WZ)];
    return out + pline(nb, 'neonG') + pline(nb, 'neon');
  }
  function shellFront(x0, y0) {
    var z0 = 0.1, out = '';
    out += poly([P(x0, y0 + RS, z0), P(x0 + RS, y0 + RS, z0), P(x0 + RS, y0 + RS, WZ), P(x0, y0 + RS, WZ)], 'url(#g-paneF)', null, 0, 1, ' class="pane"');
    out += poly([P(x0 + RS, y0, z0), P(x0 + RS, y0 + RS, z0), P(x0 + RS, y0 + RS, WZ), P(x0 + RS, y0, WZ)], 'url(#g-paneF)', null, 0, 1, ' class="pane"');
    out += pline([P(x0, y0 + RS, WZ), P(x0 + RS, y0 + RS, WZ), P(x0 + RS, y0, WZ)], 'gedge');
    [[x0, y0 + RS], [x0 + RS, y0 + RS], [x0 + RS, y0]].forEach(function (c) { out += line(P(c[0], c[1], z0), P(c[0], c[1], WZ), null, 0, ' class="gedge"'); });
    var nf = [P(x0, y0 + RS, z0), P(x0 + RS, y0 + RS, z0), P(x0 + RS, y0, z0)];
    return out + pline(nf, 'neonG') + pline(nf, 'neon');
  }

  // the room's wall screen: what runs now, or why it waits
  function wallScreen(x0, y0, u0, u1, title, sub, colour, mode) {
    var yp = y0 + 0.13, w = (u1 - u0) * SC;
    var out = poly([P(x0 + u0, yp, WS0), P(x0 + u1, yp, WS0), P(x0 + u1, yp, WS1), P(x0 + u0, yp, WS1)], 'url(#g-scr)', colour, 0.8);
    out += '<g transform="' + onBack(x0, u0, yp, WS1) + '">';
    out += text(3.6, 5.8, cut(title, Math.floor((w - 6) / 3.12)), 5.2, colour, 700);
    out += text(3.6, 9.9, cut(sub, Math.floor((w - 6) / 2.16)), 3.6, '#8fa8c2', 500);
    out += '<rect x="3.6" y="11.3" width="' + f1(w - 7.2) + '" height="1.2" rx=".6" fill="#142436"/>';
    if (mode === 'run') {
      var id = 'cp-' + f1(x0) + '-' + f1(y0);
      out += '<clipPath id="' + id + '"><rect x="3.6" y="11.3" width="' + f1(w - 7.2) + '" height="1.2"/></clipPath>' +
        '<g clip-path="url(#' + id + ')"><rect class="shim" x="3.6" y="11.3" width="' + f1((w - 7.2) * 0.35) + '" height="1.2" fill="' + colour + '"/></g>';
    } else if (mode === 'full') {
      out += '<rect x="3.6" y="11.3" width="' + f1(w - 7.2) + '" height="1.2" rx=".6" fill="' + colour + '" opacity=".8"/>';
    }
    return out + '</g>';
  }
  function barsScreen(x0, y0, u0, u1, title, bars) {
    var yp = y0 + 0.13, w = (u1 - u0) * SC, top = 1;
    var out = poly([P(x0 + u0, yp, WS0), P(x0 + u1, yp, WS0), P(x0 + u1, yp, WS1), P(x0 + u0, yp, WS1)], 'url(#g-scr)', STC.working, 0.8);
    bars.forEach(function (b) { top = Math.max(top, b[1]); });
    var bw = (w - 8) / Math.max(1, bars.length);
    out += '<g transform="' + onBack(x0, u0, yp, WS1) + '">' + text(4, 4.2, title, 3.2, STC.working, 700);
    bars.forEach(function (b, i) {
      var h = 7.4 * b[1] / top;
      out += '<rect x="' + f1(4 + i * bw) + '" y="' + f1(12.6 - h) + '" width="' + f1(bw - 2) + '" height="' + f1(Math.max(0.6, h)) + '" fill="' + b[0] + '" opacity=".9"/>';
    });
    return out + '</g>';
  }
  // the task board on the left back wall: queued, running, done and failed, read from the camera left to right
  function kanban(x0, y0, counts, v0, v1) {
    var xp = x0 + 0.13, cw = (v1 - v0 - 0.2) / 4;
    var out = poly([P(xp, y0 + v0, WS0), P(xp, y0 + v1, WS0), P(xp, y0 + v1, WS1), P(xp, y0 + v0, WS1)], 'url(#g-scr)', '#1c3248', 0.8);
    ['queued', 'running', 'done', 'failed'].forEach(function (st, col) {
      var a = y0 + v1 - 0.1 - col * cw - 0.08, b = a - cw + 0.16, c = { queued: STC.queued, running: STC.working, done: '#38f5b8', failed: STC.waiting }[st];
      out += poly([P(xp + 0.01, a, WS1 - 0.07), P(xp + 0.01, b, WS1 - 0.07), P(xp + 0.01, b, WS1 - 0.11), P(xp + 0.01, a, WS1 - 0.11)], c, null, 0, 0.95);
      for (var k = 0; k < Math.min(counts[st] || 0, 4); k++) {
        var z = WS1 - 0.24 - k * 0.12;
        out += poly([P(xp + 0.01, a - 0.04, z), P(xp + 0.01, b + 0.04, z), P(xp + 0.01, b + 0.04, z + 0.08), P(xp + 0.01, a - 0.04, z + 0.08)],
          c, null, 0, 0.85, st === 'running' ? ' class="note-run"' : '');
      }
    });
    return out;
  }
  // the pills' fonts, for their widths
  var FS = "500 7.6px 'JetBrains Mono', monospace", FN = "600 8.4px 'Segoe UI', Inter, system-ui, sans-serif";
  // A room's name lettered on its front glass, as the 3D office's (u3d.js glassSign), and no plate over it ("tam
  // vlastne staci jen ty nazvy mistnosti dat na to sklo ... nic vic se tam zobrazovat uz nemusi"): as written and
  // bold, the site's cyan-blue with a soft glow and a thin dark outline, nothing behind it ("ne na nejakym cernym
  // pozadi, a mozna nedelat vse capslockem"), the department's icon from the rail before it ("pridat ty loga stejne jak
  // vlevo v panelu"), from the pane's left end ("dat vic doleva"), in the glass's upper part; on the front-left pane,
  // or the front-right one when a room stands in front of the left; orange while the room waits on the owner. Drawn
  // over the rooms, so a neighbour in front never hides it; a click on it opens the room, as a plate's did.
  function glassSign(c, key, name, icon, have, st) {
    var x0 = c[0], y0 = c[1], leftFree = !have[x0 + ',' + (y0 + 8)], rightFree = !have[(x0 + 8) + ',' + y0];
    var right = !leftFree && rightFree, u0 = 0.4, zt = WZ - 0.03, fs = 13.6, is = 16, ty = 1.2 + is / 2 + fs * 0.35;
    var tf = right ? onLeft(x0 + RS, y0 + RS, -u0, zt) : onBack(x0, u0, y0 + RS, zt);
    var col = st === 'waiting' ? '#ff8a3a' : '#00cfff', label = cut(name, 22), lit = st === 'working' ? 1 : 0.9;
    var def = CO.deptIconSvg ? CO.deptIconSvg(icon, is - 4) : null, ic = def ? def.color : col;
    var out = '<g class="sign" data-key="' + key + '" transform="' + tf + '">';
    out += '<rect x="0" y="1.2" width="' + is + '" height="' + is + '" rx="4" fill="' + ic + '" fill-opacity=".2" stroke="' + ic + '" stroke-opacity=".7" stroke-width=".8"/>';
    if (def) out += def.svg.replace('<svg ', '<svg x="2.5" y="3.7" filter="url(#glowS)" ');
    // the glow under the letters, then the letters on a thin dark outline
    out += '<text x="' + (is + 5) + '" y="' + f1(ty) + '" font-family="' + SANS + '" font-size="' + fs + '" font-weight="700" fill="' + col + '" opacity="' + (0.55 * lit).toFixed(2) + '" filter="url(#glow2)">' + esc(label) + '</text>';
    out += '<text x="' + (is + 5) + '" y="' + f1(ty) + '" font-family="' + SANS + '" font-size="' + fs + '" font-weight="700" fill="' + col + '" fill-opacity="' + lit + '" stroke="rgba(2, 8, 14, .8)" stroke-width="2.6" stroke-linejoin="round" paint-order="stroke">' + esc(label) + '</text>';
    return out + '</g>';
  }
  // the Treasury's amounts over its plinth, the figures lit in their colours
  function amountPill(cx, cy, key, parts) {
    var s = parts.map(function (p) { return p[0]; }).join(''), w = Math.round(measure(s, FS, 0) + 26), h = 17, x = cx - w / 2, y = cy - h / 2;
    var r = ' x="' + f1(x) + '" y="' + f1(y) + '" width="' + w + '" height="' + h + '" rx="4"';
    return '<g class="plate rp" data-key="' + key + '" style="--c:#38f2b8"><rect class="pglow"' + r + '/><rect class="pbg"' + r + '/>' +
      '<text x="' + f1(cx) + '" y="' + f1(y + 11.6) + '" text-anchor="middle" font-family="\'JetBrains Mono\',monospace" font-size="7.6" font-weight="500">' + parts.map(function (p) {
        return '<tspan fill="' + p[1] + '"' + (p[2] ? ' font-weight="700" filter="url(#glowS)"' : '') + '>' + esc(p[0]) + '</tspan>';
      }).join('') + '</text></g>';
  }
  // over the Manager's rings: what needs the owner, in orange, or that nothing does
  function needPill(cx, cy, label, alert) {
    var w = Math.round(measure(label, FN, 0.5) + 24), h = 17, x = cx - w / 2, y = cy - h / 2;
    var r = ' x="' + f1(x) + '" y="' + f1(y) + '" width="' + w + '" height="' + h + '" rx="4"';
    return '<g class="plate need' + (alert ? ' alert' : '') + '" data-key="hub"><rect class="pglow"' + r + '/><rect class="pbg"' + r + '/>' +
      text(cx, y + 11.6, label, 8.4, alert ? '#ffba68' : L.dim, 600, 'middle', 'sans', ' letter-spacing=".5"') + '</g>';
  }

  /* ---------------- corridors: room doors to the Manager's, shortest way ---------------- */
  function route(cells, from, hub) {
    var xs = {}, ys = {};
    cells.forEach(function (c) { xs[c[0] - 0.5] = 1; xs[c[0] + RS + 0.5] = 1; ys[c[1] - 0.5] = 1; ys[c[1] + RS + 0.5] = 1; });
    var XL = Object.keys(xs).map(Number), YL = Object.keys(ys).map(Number);
    var nodes = {}, onX = {}, onY = {};
    function node(x, y) { var k = x + ',' + y; if (!nodes[k]) nodes[k] = { x: x, y: y, adj: [] }; return nodes[k]; }
    XL.forEach(function (x) { YL.forEach(function (y) { var n = node(x, y); (onX[x] = onX[x] || []).push(n); (onY[y] = onY[y] || []).push(n); }); });
    function doors(c, isHub) {
      var x0 = c[0], y0 = c[1], m = RS / 2;
      return [
        { wall: [x0 + m, y0 + RS], cor: [x0 + m, y0 + RS + 0.5], pen: 0 }, { wall: [x0 + RS, y0 + m], cor: [x0 + RS + 0.5, y0 + m], pen: 0 },
        { wall: [x0 + m, y0], cor: [x0 + m, y0 - 0.5], pen: isHub ? 0 : 2.5 }, { wall: [x0, y0 + m], cor: [x0 - 0.5, y0 + m], pen: isHub ? 0 : 2.5 }
      ].map(function (d) {
        var n = node(d.cor[0], d.cor[1]);
        if (onY[d.cor[1]] && XL.indexOf(d.cor[0]) < 0) onY[d.cor[1]].push(n);
        if (onX[d.cor[0]] && YL.indexOf(d.cor[1]) < 0) onX[d.cor[0]].push(n);
        d.node = n; return d;
      });
    }
    var fromD = doors(from, false), hubD = doors(hub, true);
    Object.keys(onX).forEach(function (x) { link(onX[x].sort(function (a, b) { return a.y - b.y; })); });
    Object.keys(onY).forEach(function (y) { link(onY[y].sort(function (a, b) { return a.x - b.x; })); });
    function link(l) { for (var i = 1; i < l.length; i++) { var a = l[i - 1], b = l[i], d = Math.abs(a.x - b.x) + Math.abs(a.y - b.y); a.adj.push([b, d]); b.adj.push([a, d]); } }
    var dist = new Map(), prev = new Map(), open = [];
    fromD.forEach(function (d) { dist.set(d.node, d.pen + 0.5); open.push(d.node); d.node.door = d; });
    var goal = new Map(); hubD.forEach(function (d) { goal.set(d.node, d); });
    var best = null, bestD = Infinity;
    while (open.length) {
      open.sort(function (a, b) { return dist.get(a) - dist.get(b); });
      var n = open.shift(), dn = dist.get(n);
      if (dn >= bestD) break;
      if (goal.has(n)) { if (dn + 0.5 < bestD) { bestD = dn + 0.5; best = n; } continue; }
      n.adj.forEach(function (e) {
        var nd = dn + e[1];
        if (!dist.has(e[0]) || nd < dist.get(e[0])) { dist.set(e[0], nd); prev.set(e[0], n); if (open.indexOf(e[0]) < 0) open.push(e[0]); }
      });
    }
    if (!best) return null;
    var path = [goal.get(best).wall], cur = best;
    while (cur) { path.push([cur.x, cur.y]); if (cur.door && !prev.has(cur)) { path.push(cur.door.wall); break; } cur = prev.get(cur); }
    fromD.forEach(function (d) { delete d.node.door; });
    path.reverse();
    // drop collinear points
    var out = [path[0]];
    for (var i = 1; i < path.length - 1; i++) {
      var a = out[out.length - 1], b = path[i], c = path[i + 1];
      if (!((a[0] === b[0] && b[0] === c[0]) || (a[1] === b[1] && b[1] === c[1]))) out.push(b);
    }
    out.push(path[path.length - 1]);
    return out;
  }
  function plen(p) { var s = 0; for (var i = 1; i < p.length; i++) s += Math.abs(p[i][0] - p[i - 1][0]) + Math.abs(p[i][1] - p[i - 1][1]); return s; }
  function along(p, f) {
    var total = plen(p), d = f * total;
    for (var i = 1; i < p.length; i++) {
      var l = Math.abs(p[i][0] - p[i - 1][0]) + Math.abs(p[i][1] - p[i - 1][1]);
      if (d <= l) { var t = l ? d / l : 0; return [p[i - 1][0] + (p[i][0] - p[i - 1][0]) * t, p[i - 1][1] + (p[i][1] - p[i - 1][1]) * t]; }
      d -= l;
    }
    return p[p.length - 1];
  }

  /* ---------------- the office ---------------- */
  function Office(svg, stage, tipFor) {
    this.svg = svg; this.stage = stage; this.tipFor = tipFor;
    this.sel = null; this.cells = {}; this.paths = {}; this.packets = []; this.walkers = {};
    svg.innerHTML = DEFS + '<g class="world"><g class="floor"></g><g class="rooms"></g><g class="packets"></g><g class="overlay"></g></g>';
    // the sky behind it: the stars are one tile repeated, the haze and the navy are the stylesheet's (#office)
    try { svg.style.setProperty('--stars', starTile()); } catch (e) { /* the navy alone is a sky too */ }
    this.gWorld = svg.querySelector('.world');
    this.gFloor = svg.querySelector('.floor'); this.gRooms = svg.querySelector('.rooms');
    this.gPk = svg.querySelector('.packets'); this.gOver = svg.querySelector('.overlay');
    this.tip = stage.querySelector('.tip');
    this.vb = { x: 0, y: 0, w: 1000, h: 600 };
    this.bind();
    var self = this;
    var pace = pacer(function () { return !!self.tw || performance.now() - (self.lastInput || 0) < 1500; });
    requestAnimationFrame(function loop(t) { if (pace(t)) { self.frame(t); self.stepAnims(t); } requestAnimationFrame(loop); });
    setInterval(function () { self.wander(); }, 2600);
    if (window.ResizeObserver) new ResizeObserver(function () { self.resize(); }).observe(svg);
  }
  CO.Office = Office;

  Office.prototype.shape = function () {
    var S = CO.S;
    return S.departments.map(function (d) { return d.id + ':' + d.slot + ':' + d.key + ':' + (d.look || '') + ':' + d.experts.join(','); }).join('|');
  };

  // Under the deck, the 3D office's hull: a plated tier under every slab, inset where it is the outside, as low as
  // the 3D's, its sides a grey rail with a few windows over slate (hullFace), and one keel step under it. No rock, engines or solar wings: flat, they looked ugly (the operator, 2026-10-19:
  // remove the rock and the thrusters from the 2D view). Drawn in layers, lowest first, each back to front.
  Office.prototype.hull = function (order, have, pad) {
    var out = ['', '', ''], zt = -T - 0.12;
    order.forEach(function (c) {
      var Lf = !have[(c[0] - 8) + ',' + c[1]], Rt = !have[(c[0] + 8) + ',' + c[1]], Bk = !have[c[0] + ',' + (c[1] - 8)], Fr = !have[c[0] + ',' + (c[1] + 8)];
      var x0 = c[0] - pad, y0 = c[1] - pad, x1 = c[0] + RS + pad, y1 = c[1] + RS + pad, R = rng(41 + c[0] * 3 + c[1] * 5);
      var tier = function (ins, z0, h, top, left, right) {
        var ax = x0 + (Lf ? ins : 0), ay = y0 + (Bk ? ins : 0), bx = x1 - (Rt ? ins : 0), by = y1 - (Fr ? ins : 0);
        return { s: box(ax, ay, z0, bx - ax, by - ay, h, top, left, right), ax: ax, ay: ay, bx: bx, by: by };
      };
      out[1] += tier(0.6, zt - HD - 0.24, 0.24, L.keelL, L.keelL, L.keelR).s;
      var t = tier(0.12, zt - HD, HD, L.hullTop, 'url(#g-hullL)', 'url(#g-hullR)');
      out[2] += t.s;
      if (Fr) out[2] += hullFace(onBack(t.ax, 0, t.by, zt), (t.bx - t.ax) * SC, HD * SC, R, false);
      if (Rt) out[2] += hullFace(onSide(t.bx, t.ay, 0, zt), (t.by - t.ay) * SC, HD * SC, R, true);
    });
    return out.join('');
  };
  // a side of the hull as the 3D's (hullTex): a light-grey rail flush along its upper half with a few dark windows
  // in it, one small light in each, seams between its lengths; the slate under it, its foot dark
  function hullFace(tf, W, H, R, dark) {
    var r0 = H * 0.12, r1 = H * 0.58, out = '<g transform="' + tf + '">' +
      '<rect y="' + f1(r0) + '" width="' + f1(W) + '" height="' + f1(r1 - r0) + '" fill="' + (dark ? '#5f6a77' : '#7c8897') + '"/>' +
      '<rect y="' + f1(r0) + '" width="' + f1(W) + '" height=".6" fill="#c4ced8" opacity="' + (dark ? '.3' : '.55') + '"/>' +
      '<rect y="' + f1(H - 1.6) + '" width="' + f1(W) + '" height="1.6" fill="#121922" opacity=".85"/>';
    var n = Math.max(1, Math.round(W / 60)), step = W / n;
    for (var i = 0; i < n; i++) {
      var x = i * step, ww = step * (0.3 + R() * 0.15), wx = x + step * 0.3, wy = r0 + (r1 - r0) * 0.28, wh = (r1 - r0) * 0.44;
      if (i) out += '<rect x="' + f1(x) + '" y="' + f1(r0) + '" width=".7" height="' + f1(r1 - r0) + '" fill="#3e4855"/>';
      out += '<rect x="' + f1(wx) + '" y="' + f1(wy) + '" width="' + f1(ww) + '" height="' + f1(wh) + '" fill="#121a28"/>' +
        '<rect x="' + f1(wx + ww - 3.2) + '" y="' + f1(wy + wh / 2 - 0.6) + '" width="2.2" height="1.2" fill="' + (i % 2 ? '#9fe8ff' : L.neon) + '"/>';
    }
    return out + '</g>';
  }
  // the deck's plates: two by two over every slab, a shade apart, dark seams between them
  function deckPanels(x0, y0, s, R) {
    var out = '', h = s / 2, g = 0.04;
    for (var i = 0; i < 2; i++) for (var j = 0; j < 2; j++) {
      out += poly([P(x0 + i * h + g, y0 + j * h + g, 0), P(x0 + (i + 1) * h - g, y0 + j * h + g, 0), P(x0 + (i + 1) * h - g, y0 + (j + 1) * h - g, 0),
        P(x0 + i * h + g, y0 + (j + 1) * h - g, 0)], shade(L.deck, R() * 0.06 - 0.03));
    }
    return out;
  }
  Office.prototype.layout = function (opts) {
    var S = CO.S, self = this, born = opts && opts.born;
    this.shapeKey = this.shape();
    var cells = { hub: HUB, audit: AUDIT, vault: VAULT };   // no room for the owner: approvals live in the right column
    var used = {};
    S.departments.forEach(function (d) { cells['d' + d.id] = SLOTS[d.slot]; used[d.slot] = 1; });
    var lot = 0; while (used[lot]) lot++;
    // a visitor sees the company as it is: no empty lot inviting a department they cannot add
    if (lot < SLOTS.length && !CO.RO) cells.lot = SLOTS[lot];
    this.cells = cells;
    var all = Object.keys(cells).map(function (k) { return cells[k]; });
    var maxX = 0, maxY = 0;
    all.forEach(function (c) { maxX = Math.max(maxX, c[0] + RS); maxY = Math.max(maxY, c[1] + RS); });
    this.world = [maxX, maxY];

    // The deck, as the 3D office's: a slab under every room (the free lot included), so a corner of the plan with no
    // room is open space and the office floats; its outside a slate rim with a lit top edge, a small cyan beacon on
    // the rim of every other near side, the hull and its keel under it.
    var pad = 0.5, have = {}, f = '', rims = '', corners = [], nb = 0;
    all.forEach(function (c) { have[c[0] + ',' + c[1]] = 1; });
    var order = all.slice().sort(function (p, q) { return (p[0] + p[1]) - (q[0] + q[1]) || p[0] - q[0]; });
    f += this.hull(order, have, pad);
    order.forEach(function (c) {
      var x0 = c[0] - pad, y0 = c[1] - pad, x1 = c[0] + RS + pad, y1 = c[1] + RS + pad;
      f += box(x0, y0, -T, x1 - x0, y1 - y0, T, L.deckSeam, L.rimL, L.rimR);
      f += deckPanels(x0, y0, x1 - x0, rng(23 + c[0] * 11 + c[1] * 17));
      [[x0, y0, x1, y0, !have[c[0] + ',' + (c[1] - 8)], false], [x0, y1, x1, y1, !have[c[0] + ',' + (c[1] + 8)], true],
        [x0, y0, x0, y1, !have[(c[0] - 8) + ',' + c[1]], false], [x1, y0, x1, y1, !have[(c[0] + 8) + ',' + c[1]], true]].forEach(function (s) {
        if (!s[4]) return;
        rims += line(P(s[0], s[1], 0), P(s[2], s[3], 0), L.rimHi, 1.1, ' stroke-linecap="round"');
        if (!s[5]) return;
        rims += line(P(s[0], s[1], -T), P(s[2], s[3], -T), '#0c1219', 1);
        if (nb++ % 2) return;
        var mx = (s[0] + s[2]) / 2, my = (s[1] + s[3]) / 2, ax = s[0] === s[2] ? 0 : 0.42, ay = s[0] === s[2] ? 0.42 : 0;
        var a = P(mx - ax, my - ay, -T * 0.55), b = P(mx + ax, my + ay, -T * 0.55);
        rims += line(a, b, '#24e8ff', 3.2, ' opacity=".35" filter="url(#glow2)"') + line(a, b, '#7ff0ff', 1.3, ' stroke-linecap="round"');
      });
      corners.push(P(x0, y0, WZ), P(x1, y0, 0), P(x0, y1, 0), P(x1 - 0.12, y1 - 0.12, -T - 0.12 - HD), P(x1 - 0.6, y1 - 0.6, -T - 0.12 - HD - 0.24));
    });
    f += rims;
    this.plateRect = {
      x: Math.min.apply(null, corners.map(function (q) { return q[0]; })), y: Math.min.apply(null, corners.map(function (q) { return q[1]; })),
      x2: Math.max.apply(null, corners.map(function (q) { return q[0]; })), y2: Math.max.apply(null, corners.map(function (q) { return q[1]; }))
    };
    // the lanes: from every room's door to the Manager's, dim white dashes on the bare deck that light cyan while
    // work runs along them
    this.paths = {};
    Object.keys(cells).forEach(function (k) {
      if (k === 'hub' || k === 'lot') return;
      var p = route(all, cells[k], HUB);
      if (!p) return;
      self.paths[k] = p;
      f += '<polyline class="flow" data-path="' + k + '" points="' + pts(p.map(function (q) { return P(q[0], q[1], 0.02); })) + '" fill="none"/>';
    });
    this.gFloor.innerHTML = f;

    // rooms, back to front
    var rorder = Object.keys(cells).sort(function (p, q) {
      var A = cells[p], B = cells[q];
      return (A[0] + A[1]) - (B[0] + B[1]) || A[0] - B[0];
    });
    this.gRooms.innerHTML = rorder.map(function (k) {
      var c = cells[k], x0 = c[0], y0 = c[1], inner;
      if (k === 'hub') inner = self.hubRoom(x0, y0);
      else if (k === 'audit') inner = self.auditRoom(x0, y0);
      else if (k === 'vault') inner = self.vaultRoom(x0, y0);
      else if (k === 'lot') inner = self.lotRoom(x0, y0);
      else inner = self.deptRoom(CO.dept(+k.slice(1)), x0, y0);
      var cls = 'room' + (k === 'lot' ? ' lot' : '') + (born && k === 'd' + born ? ' born' : '');
      return '<g class="' + cls + '" data-key="' + k + '">' + inner + '</g>';
    }).join('');
    this.walkers = {};
    this.update();
    if (!this.fitted) { this.fit(false); this.fitted = true; }
  };

  // A department's room, furnished as the 3D office furnishes it: its computer in the back corner, a wall screen and
  // a task board on the back walls, desks for its experts with them at work in front, a lime holo screen, a cabinet,
  // plants; and what each kind of department has of its own.
  // Mint like every room: orange is only for a room that waits on you ("oranzove sviti jen roomka ktera chce pozornost
  // moji, needs you"), so the trading desk's chart walls are the site's green. A department of the owner's own in a
  // look (d.look, CO.ROOM_LOOKS) has that look's pieces where the others have their racks, as the 3D's builds them.
  var LOOK2D = { ops: 1, library: 1, workshop: 1, command: 1, greenhouse: 1 };
  Office.prototype.deptRoom = function (d, x0, y0) {
    var k = d.key, key = 'd' + d.id, items = [], walls = '';
    var out = shellBack(x0, y0, 'room');
    var ex = d.experts.slice(0, 3), link = d.link || CO.DEPT_LINK[k] || CO.DEPT_LINK.custom;
    var look = k === 'custom' && LOOK2D[d.look] ? d.look : null;
    var add = function (x, y, s) { items.push([x + y, s]); };
    if (link) add(x0 + 0.92, y0 + 0.72, terminal(x0 + 0.3, y0 + 0.32, link));
    var u1 = 4.6, xs = ex.length === 1 ? [2.4] : ex.length === 2 ? [1.0, 3.7] : [0.35, 2.55, 4.75], charts = k === 'trading_desk';
    if (look) u1 = lookPieces(look, x0, y0, add, function (s) { walls += s; });
    else if (k === 'development') { u1 = 3.3; add(x0 + 1.6, y0 + 1.69, racks(x0 + 0.55, y0 + 1.35, 3, 0.78)); }
    else if (k === 'testing') walls += qaWindow(x0, y0);
    else if (k === 'testing_lab') {
      u1 = 3.4;
      add(x0 + 4.33, y0 + 0.7, labMachine(x0 + 3.75, y0 + 0.3)); add(x0 + 5.73, y0 + 0.7, labMachine(x0 + 5.15, y0 + 0.3));
      add(x0 + 1.2, y0 + 5.42, labHolo(x0 + 0.6, y0 + 5.0)); add(x0 + 6.45, y0 + 2.4, canisters(x0 + 6.45, y0 + 1.85));
    } else if (k === 'design') { u1 = 4.5; walls += mood(x0, y0, 4.7, 6.75); }
    else if (!charts) add(x0 + 5.8, y0 + 0.64, racks(x0 + 5.2, y0 + 0.3, 2, 0.72));
    if (charts) {
      walls += chartWall(onBack(x0, 1.75, y0 + 0.13, WS1 + 0.06), 5.1 * SC, (WS1 + 0.06 - WS0 + 0.1) * SC) +
        chartWall(onLeft(x0 + 0.13, y0, 6.05, WS1 + 0.06), 4.7 * SC, (WS1 + 0.06 - WS0 + 0.1) * SC);
    } else {
      walls += '<g class="scr" data-u0="1.75" data-u1="' + u1 + '"></g><g class="kb" data-v0="1.5" data-v1="5.8"></g>';
    }
    ex.forEach(function (e, i) { add(x0 + xs[i] + 0.95, y0 + 3.18, desk(x0 + xs[i], y0 + 2.75, i)); });
    add(x0 + 0.75, y0 + 2.2, holoFrame(x0 + 0.75, y0 + 2.2));
    ex.forEach(function (e, i) { add(x0 + xs[i] + 0.95, y0 + 4.05, agentAt(x0 + xs[i] + 0.95, y0 + 4.05, key, i, CO.expertName(e), e)); });
    if (!look) add(x0 + 6.67, y0 + 4.15, cabinet(x0 + 6.45, y0 + 3.0, 0.45, 2.3, 0.62));
    add(x0 + 0.42, y0 + 6.5, plant(x0 + 0.42, y0 + 6.5));
    if (!look) add(x0 + 6.55, y0 + 6.55, plant(x0 + 6.55, y0 + 6.55, 0.8));
    return out + walls + sortJoin(items) + shellFront(x0, y0);
  };
  // A look's own pieces, drawn as the 3D's have them, in the room's free places: the back wall's right end (from 4.2
  // along it) and the floor's front right; the wall screen ends at the length returned. wall(s) puts s on the walls.
  function lookPieces(look, x0, y0, add, wall) {
    var X = function (v) { return x0 + v; }, Y = function (v) { return y0 + v; };
    if (look === 'ops') {
      // the operations room: a wall of screens over a console along the back wall, comms cabinets by the right wall,
      // a light tower in the front corner
      wall(poly([P(X(4.2), Y(0.13), WS0), P(X(6.85), Y(0.13), WS0), P(X(6.85), Y(0.13), WS1 + 0.06), P(X(4.2), Y(0.13), WS1 + 0.06)], '#061420', '#24e8ff', 0.8));
      var sw = '<g transform="' + onBack(x0, 4.2, y0 + 0.13, WS1 + 0.06) + '">';
      for (var i = 0; i < 3; i++) {
        var sx = 1.6 + i * 19;
        sw += '<rect x="' + sx + '" y="1.6" width="17" height="11" rx=".6" fill="#0a2030" stroke="#24e8ff" stroke-width=".5"/>' +
          '<polyline points="' + [0, 1, 2, 3, 4, 5, 6].map(function (j) { return f1(sx + 1.4 + j * 2.4) + ',' + f1(9.6 - ((i * 7 + j * 5) % 6) * 1.1); }).join(' ') + '" fill="none" stroke="' + ['#38f5b8', '#24e8ff', '#5b9bff'][i] + '" stroke-width=".6"/>';
      }
      wall(sw + '</g>');
      add(X(5.5), Y(0.75), fb(X(4.3), Y(0.3), 0.1, 2.5, 0.55, 0.45, L.deskTop, L.desk, L.deskR) +
        poly([P(X(4.35), Y(0.85), 0.5), P(X(6.75), Y(0.85), 0.5), P(X(6.75), Y(0.85), 0.47), P(X(4.35), Y(0.85), 0.47)], '#24e8ff', null, 0, 0.7));
      [2.7, 3.7].forEach(function (y) {
        add(X(6.65), Y(y + 0.4), fb(X(6.3), Y(y), 0.1, 0.5, 0.85, 1.1, '#24303c', '#151d26', '#10171f') +
          '<g transform="' + onSide(X(6.3), Y(y), 0.1, 1.1) + '"><rect x="2" y="3" width="1.2" height="16" fill="#24e8ff" opacity=".7"/>' +
          '<rect class="led" x="5" y="5" width="2.2" height="1.1" fill="#38f5b8"/><rect class="led" x="5" y="9" width="2.2" height="1.1" fill="#5b9bff" style="animation-delay:-.6s"/></g>');
      });
      var tw = cyl(X(6.4), Y(6.3), 0.1, 0.16, 0.26, '#2c3742', '#232c36', '#161d25') + line(P(X(6.4), Y(6.3), 0.16), P(X(6.4), Y(6.3), 1.1), L.frame, 2.4);
      [['#38f5b8', 1.1], ['#24e8ff', 0.92], ['#5b9bff', 0.74]].forEach(function (c) { tw += cyl(X(6.4), Y(6.3), c[1], c[1] + 0.14, 0.09, c[0], shade(c[0], -0.3), shade(c[0], -0.5)); });
      add(X(6.4), Y(6.3), tw + disc(X(6.4), Y(6.3), 1.18, 0.5, 'url(#g-halo-c)', null, 0, ' opacity=".35"'));
      return 4.0;
    }
    if (look === 'library') {
      // the research library: a tall shelf of glowing data books along the back wall with its ladder, an orb of
      // knowledge on its pedestal, an armchair by it
      var sh = fb(X(4.25), Y(0.25), 0.1, 2.6, 0.5, 1.22, '#2a3644', '#1d2631', '#151c24'), cols = ['#24e8ff', '#5b9bff', '#38f5b8', '#9fe8ff'];
      sh += '<g transform="' + onBack(x0, 4.3, y0 + 0.75, 1.28) + '">';
      for (var r = 0; r < 4; r++) {
        sh += '<rect x="0" y="' + f1(3.6 + r * 6) + '" width="56" height=".7" fill="#0d141c"/>';
        for (var b = 0; b < 14; b++) {
          var bh = 3 + ((r * 5 + b * 3) % 3) * 0.7;
          sh += '<rect x="' + f1(1 + b * 3.9) + '" y="' + f1(3.6 + r * 6 - bh) + '" width="2.6" height="' + f1(bh) + '" fill="' + cols[(r + b) % 4] + '" opacity="' + (0.55 + ((b * 7) % 4) * 0.1).toFixed(2) + '"/>';
        }
      }
      sh += '</g>' + line(P(X(6.2), Y(0.85), 0.1), P(X(6.45), Y(0.78), 1.3), '#b48a4a', 1.2) + line(P(X(6.5), Y(0.95), 0.1), P(X(6.75), Y(0.88), 1.3), '#b48a4a', 1.2);
      add(X(5.6), Y(0.8), sh);
      var orb = cyl(X(5.6), Y(5.4), 0.1, 0.6, 0.3, L.white, L.white2, L.white3), oc = P(X(5.6), Y(5.4), 0.95);
      orb += '<circle cx="' + f1(oc[0]) + '" cy="' + f1(oc[1]) + '" r="16" fill="url(#g-halo-c)" opacity=".35"/>' +
        '<circle class="holo-core" cx="' + f1(oc[0]) + '" cy="' + f1(oc[1]) + '" r="6.4" fill="#9ff4ff" opacity=".85" filter="url(#glowS)"/>' +
        '<ellipse cx="' + f1(oc[0]) + '" cy="' + f1(oc[1]) + '" rx="10" ry="3.2" fill="none" stroke="#24e8ff" stroke-width=".7" opacity=".8"/>';
      add(X(5.6), Y(5.4), orb);
      add(X(6.4), Y(6.35), fb(X(6.0), Y(6.0), 0.1, 0.8, 0.7, 0.3, '#3a4756', '#2a3644', '#1d2631') + fb(X(6.62), Y(6.0), 0.4, 0.18, 0.7, 0.42, '#3a4756', '#2a3644', '#1d2631'));
      return 4.0;
    }
    if (look === 'workshop') {
      // the workshop: a bench under a pegboard of tools along the back wall, a wall of parts bins by the right wall,
      // a robot arm at work in its taped cell
      var pb = poly([P(X(4.25), Y(0.13), WS0), P(X(6.85), Y(0.13), WS0), P(X(6.85), Y(0.13), WS1 + 0.06), P(X(4.25), Y(0.13), WS1 + 0.06)], '#1a2430', '#2a3644', 0.8);
      pb += '<g transform="' + onBack(x0, 4.25, y0 + 0.13, WS1 + 0.06) + '">';
      for (var py = 2; py < 14; py += 2.4) for (var px = 2; px < 56; px += 2.4) pb += '<circle cx="' + f1(px) + '" cy="' + f1(py) + '" r=".3" fill="#0b1118"/>';
      pb += '<path d="M8 3v8 M14 3l4 7 M24 3v6 M23 9h2 M34 4l-3 6 M44 3v9 M43 3h2" stroke="#c6cfd7" stroke-width="1" fill="none"/><rect x="48" y="4" width="5" height="4" fill="#24e8ff" opacity=".7"/></g>';
      wall(pb);
      add(X(5.5), Y(0.75), fb(X(4.3), Y(0.3), 0.1, 2.5, 0.75, 0.46, L.deskTop, L.desk, L.deskR) + fb(X(4.6), Y(0.45), 0.56, 0.5, 0.3, 0.12, '#56626e', '#3a4756', '#2a3644') +
        fb(X(5.6), Y(0.4), 0.56, 0.7, 0.45, 0.08, '#24e8ff', '#1aa0b8', '#147a8c'));
      var bins = fb(X(6.3), Y(2.6), 0.1, 0.5, 1.9, 1.05, '#24303c', '#151d26', '#10171f') + '<g transform="' + onSide(X(6.3), Y(2.6), 0.1, 1.1) + '">';
      for (var br = 0; br < 4; br++) for (var bc = 0; bc < 5; bc++) bins += '<rect x="' + f1(2 + bc * 8) + '" y="' + f1(2.5 + br * 5.2) + '" width="6.4" height="3.6" rx=".5" fill="' + ['#2a6aa8', '#1c9cb4', '#38a878', '#56626e'][(br + bc) % 4] + '"/>';
      add(X(6.6), Y(3.5), bins + '</g>');
      var cell = '';
      [[4.9, 4.9, 6.7, 4.9], [6.7, 4.9, 6.7, 6.7], [6.7, 6.7, 4.9, 6.7], [4.9, 6.7, 4.9, 4.9]].forEach(function (s) { cell += line(P(X(s[0]), Y(s[1]), 0.11), P(X(s[2]), Y(s[3]), 0.11), '#24e8ff', 1.4, ' stroke-dasharray="4 3" opacity=".7"'); });
      add(X(5.0), Y(5.0), cell);
      var a0 = P(X(5.8), Y(5.8), 0.3), a1 = P(X(5.5), Y(5.6), 1.0), a2 = P(X(5.1), Y(5.9), 0.75);
      add(X(5.8), Y(5.8), cyl(X(5.8), Y(5.8), 0.1, 0.3, 0.32, L.white, L.white2, L.white3) +
        line(a0, a1, L.white, 4.6, ' stroke-linecap="round"') + line(a1, a2, L.white2, 3.6, ' stroke-linecap="round"') +
        '<circle cx="' + f1(a1[0]) + '" cy="' + f1(a1[1]) + '" r="2.6" fill="#24e8ff"/><circle cx="' + f1(a2[0]) + '" cy="' + f1(a2[1]) + '" r="1.8" fill="#38f5b8" filter="url(#glowS)"/>');
      return 4.0;
    }
    if (look === 'command') {
      // the command center: a holographic table with a tactical map, its targets' beams and a globe over it, two
      // consoles round it
      var cx = X(5.3), cy = Y(5.3), tb = cyl(cx, cy, 0.1, 0.48, 1.05, '#16222e', '#111a24', '#2b3846');
      tb += disc(cx, cy, 0.49, 1.0, 'rgba(36, 232, 255, .18)', '#24e8ff', 1.1);
      for (var g = -0.6; g <= 0.61; g += 0.3) tb += line(P(cx + g, cy - 0.8, 0.5), P(cx + g, cy + 0.8, 0.5), '#24e8ff', 0.4, ' opacity=".35"') + line(P(cx - 0.8, cy + g, 0.5), P(cx + 0.8, cy + g, 0.5), '#24e8ff', 0.4, ' opacity=".35"');
      [[-0.4, -0.2], [0.35, 0.3], [0.1, -0.5]].forEach(function (t) { tb += line(P(cx + t[0], cy + t[1], 0.5), P(cx + t[0], cy + t[1], 1.3), '#38f5b8', 1.2, ' opacity=".7" filter="url(#glowS)"'); });
      var gc = P(cx, cy, 1.55);
      tb += '<g class="holo"><circle cx="' + f1(gc[0]) + '" cy="' + f1(gc[1]) + '" r="9" fill="rgba(36, 232, 255, .12)" stroke="#9ff4ff" stroke-width=".8"/>' +
        '<ellipse cx="' + f1(gc[0]) + '" cy="' + f1(gc[1]) + '" rx="9" ry="3" fill="none" stroke="#24e8ff" stroke-width=".6"/>' +
        '<ellipse cx="' + f1(gc[0]) + '" cy="' + f1(gc[1]) + '" rx="3.4" ry="9" fill="none" stroke="#24e8ff" stroke-width=".6"/></g>' + disc(cx, cy, 1.0, 1.4, 'none', '#24e8ff', 3, ' opacity=".25" filter="url(#glow2)"');
      add(cx, cy, tb);
      add(X(4.95), Y(0.75), console3(X(4.3), Y(0.3))); add(X(6.35), Y(0.75), console3(X(5.7), Y(0.3)));
      return 4.0;
    }
    // the greenhouse: a hydroponic rack of plants under violet-pink grow lights along the back wall, an island of
    // gutters by the right wall, planters in the front corner
    var gr = fb(X(4.25), Y(0.25), 0.1, 2.6, 0.55, 1.2, '#2a3644', '#1d2631', '#151c24');
    [0.42, 0.78, 1.14].forEach(function (z) {
      gr += poly([P(X(4.3), Y(0.8), z + 0.05), P(X(6.8), Y(0.8), z + 0.05), P(X(6.8), Y(0.8), z + 0.02), P(X(4.3), Y(0.8), z + 0.02)], '#e07ae8', null, 0, 0.9, ' filter="url(#glowS)"');
      for (var p = 0; p < 6; p++) { var pc = P(X(4.5 + p * 0.42), Y(0.62), z - 0.22); gr += '<circle cx="' + f1(pc[0]) + '" cy="' + f1(pc[1]) + '" r="3.2" fill="' + (p % 2 ? '#2e875f' : '#349466') + '"/>'; }
    });
    gr += disc(X(5.55), Y(1.2), 0.1, 1.4, 'rgba(224, 122, 232, .1)');
    add(X(5.6), Y(0.8), gr);
    var isl = fb(X(5.9), Y(3.0), 0.1, 0.8, 2.6, 0.42, '#3a4756', '#2a3644', '#1d2631');
    for (var q = 0; q < 6; q++) { var qc = P(X(6.3), Y(3.25 + q * 0.42), 0.6); isl += '<circle cx="' + f1(qc[0]) + '" cy="' + f1(qc[1]) + '" r="3.6" fill="' + ['#22684a', '#2e875f', '#349466'][q % 3] + '"/>'; }
    add(X(6.3), Y(4.3), isl);
    add(X(5.6), Y(6.3), plant(X(5.6), Y(6.3), 1.1)); add(X(6.5), Y(5.7), plant(X(6.5), Y(5.7), 0.85));
    return 4.0;
  }
  // The Manager's room: consoles along both back walls under its screens, cyan light on the floor round a dark
  // dais -- a wide disc with a pale rim, a drum with a cyan lip -- a white-hot core over it in a column of light,
  // three rings of light over that, smaller as they rise; the Manager standing in front.
  Office.prototype.hubRoom = function (x0, y0) {
    var out = shellBack(x0, y0, 'hub'), cx = x0 + 3.8, cy = y0 + 3.55, items = [], d = '';
    var add = function (x, y, s) { items.push([x + y, s]); };
    out += disc(cx, cy, 0.11, 3.2, 'url(#g-hubf)');
    out += disc(cx, cy, 0.11, 2.95, 'none', STC.working, 1.1, ' opacity=".5"') + disc(cx, cy, 0.11, 2.62, 'none', '#38f5d7', 1.3, ' stroke-dasharray=".8 3.2" opacity=".6"');
    out += disc(cx, cy, 0.11, 2.15, 'none', STC.working, 2.2, ' opacity=".2"');
    [[0.26, 2.6], [3.4, 5.76]].forEach(function (a) { out += pline(arc(cx, cy, 0.11, 1.95, a[0], a[1]), '', ' stroke="' + STC.working + '" stroke-width="1.2" opacity=".75"'); });
    [[0.35, 2.25], [3.55, 5.05]].forEach(function (a) { out += pline(arc(cx, cy, 0.11, 2.36, a[0], a[1]), '', ' stroke="#c8d4de" stroke-width="2.2" stroke-linecap="round" opacity=".45"'); });
    out += '<g class="scr hubscr" data-u0="0.6" data-u1="4.0"></g><g class="kb" data-v0="1.4" data-v1="5.4"></g>';
    add(x0 + 2.3, y0 + 0.6, fb(x0 + 0.5, y0 + 0.25, 0.1, 3.6, 0.7, 0.42, L.deskTop, L.desk, L.deskR));
    add(x0 + 0.6, y0 + 3.3, fb(x0 + 0.25, y0 + 1.5, 0.1, 0.7, 3.6, 0.42, L.deskTop, L.desk, L.deskR));
    d += cyl(cx, cy, 0.1, 0.26, 1.72, '#223040', '#18232e', '#4a5866');
    d += cyl(cx, cy, 0.26, 0.46, 1.05, '#111a24', '#0b1118', '#2b3846');
    d += disc(cx, cy, 0.46, 1.05, 'none', STC.working, 3.6, ' opacity=".4" filter="url(#glow2)"') + disc(cx, cy, 0.46, 1.05, 'none', '#7ff4ff', 1.2);
    var top = P(cx, cy, 0.46), core = P(cx, cy, 1.0);
    d += '<ellipse class="beam" cx="' + f1(top[0]) + '" cy="' + f1(top[1] - 30) + '" rx="14" ry="40" fill="url(#g-beam)"/>';
    d += '<ellipse class="holo-core" cx="' + f1(core[0]) + '" cy="' + f1(core[1]) + '" rx="30" ry="28" fill="url(#g-core)" opacity=".7"/>';
    d += '<circle cx="' + f1(core[0]) + '" cy="' + f1(core[1]) + '" r="5.6" fill="#ffffff" filter="url(#glow)"/>';
    [[1.45, 0.98], [1.85, 0.86], [2.25, 0.74]].forEach(function (h, k) {
      d += '<g class="holo h' + k + '">' + disc(cx, cy, h[0], h[1], 'none', STC.working, 4, ' opacity=".35" filter="url(#glow2)"') + disc(cx, cy, h[0], h[1], 'none', '#9ff8ff', 1.3) + '</g>';
    });
    for (var i = 0; i < 7; i++) {
      d += '<circle class="mote" cx="' + f1(top[0] - 8 + (i * 37 % 17)) + '" cy="' + f1(top[1] - 4) + '" r="' + (0.8 + (i % 3) * 0.3) + '" fill="' + STC.working + '" style="animation-delay:' + (-i * 0.55).toFixed(2) + 's"/>';
    }
    add(cx, cy, d);
    this.hubTop = P(x0 + 3.0, y0 + 2.8, 2.75);
    // nobody stands here: the core is NEXUS
    add(x0 + 6.4, y0 + 0.5, plant(x0 + 6.4, y0 + 0.5));
    return out + sortJoin(items) + shellFront(x0, y0);
  };
  // the weekly audit: two white consoles with green screens, its wall screen, a desk, a printer for the report
  Office.prototype.auditRoom = function (x0, y0) {
    var out = shellBack(x0, y0, 'room'), items = [];
    var add = function (x, y, s) { items.push([x + y, s]); };
    out += '<g class="scr" data-u0="3.4" data-u1="6.6"></g>';
    add(x0 + 0.9, y0 + 0.66, console3(x0 + 0.3, y0 + 0.3)); add(x0 + 2.3, y0 + 0.66, console3(x0 + 1.7, y0 + 0.3));
    add(x0 + 3.95, y0 + 3.18, desk(x0 + 3.0, y0 + 2.75, 0));
    add(x0 + 3.95, y0 + 4.05, agentAt(x0 + 3.95, y0 + 4.05, 'audit', 0, 'Supervisor', 'supervisor'));
    add(x0 + 0.85, y0 + 4.8, printer(x0 + 0.35, y0 + 4.4));
    add(x0 + 6.67, y0 + 3.7, cabinet(x0 + 6.45, y0 + 2.6, 0.45, 2.2, 0.62));
    add(x0 + 6.5, y0 + 6.5, plant(x0 + 6.5, y0 + 6.5));
    return out + sortJoin(items) + shellFront(x0, y0);
  };
  // The vault: a massive round door in its back wall -- a heavy steel frame lit mint, a ring of bolts, a wheel -- and
  // a lit plinth where the earnings pile up under glass, ET10 green and USDC blue. A visitor finds the plinth bare.
  Office.prototype.vaultRoom = function (x0, y0) {
    var out = shellBack(x0, y0, 'room'), items = [];
    var add = function (x, y, s) { items.push([x + y, s]); };
    // the door fills the wall from its foot to its top, set in a dark armoured plate with its hinges and its bolt
    var dr = '<g class="vdoor" transform="' + onBack(x0, 3.5, y0 + 0.15, 0.7) + '">' +
      '<rect x="-21" y="-13.2" width="42" height="26.4" rx="1.8" fill="' + L.dark + '" stroke="' + L.frame + '" stroke-width=".8"/>' +
      '<rect x="-19" y="-8.4" width="3.2" height="5" rx=".8" fill="url(#g-steel)"/><rect x="-19" y="3.4" width="3.2" height="5" rx=".8" fill="url(#g-steel)"/>' +
      '<rect x="14.2" y="-2.2" width="5" height="4.4" rx=".8" fill="url(#g-steel)"/>' +
      '<circle r="14.4" fill="' + L.mint + '" opacity=".25" filter="url(#glow2)"/>' +
      '<circle r="13.8" fill="url(#g-steel)" stroke="' + L.mint + '" stroke-width=".9"/><circle r="12.5" fill="none" stroke="#2a333e" stroke-width=".5"/>' +
      '<circle r="11.7" fill="#151c25"/><circle r="11" fill="url(#g-door)" stroke="#9aa6b4" stroke-width=".45"/>';
    for (var b = 0; b < 16; b++) { var a = b / 16 * Math.PI * 2; dr += '<circle cx="' + f1(Math.cos(a) * 9.5) + '" cy="' + f1(Math.sin(a) * 9.5) + '" r=".85" fill="#c3ccd4" stroke="#2a333e" stroke-width=".3"/>'; }
    dr += '<circle r="7.2" fill="none" stroke="#2a333e" stroke-width="1.3"/><circle r="7.2" fill="none" stroke="#9aa6b4" stroke-width=".4" stroke-dasharray="2 2.2"/>';
    for (var s = 0; s < 3; s++) {
      var q = s * Math.PI / 3 + 0.3, cx = Math.cos(q) * 5.5, cy = Math.sin(q) * 5.5;
      dr += '<line x1="' + f1(-cx) + '" y1="' + f1(-cy) + '" x2="' + f1(cx) + '" y2="' + f1(cy) + '" stroke="#c6cfd7" stroke-width="1.5" stroke-linecap="round"/>' +
        '<circle cx="' + f1(cx) + '" cy="' + f1(cy) + '" r="1.2" fill="#dfe6ec"/><circle cx="' + f1(-cx) + '" cy="' + f1(-cy) + '" r="1.2" fill="#dfe6ec"/>';
    }
    dr += '<circle r="2.6" fill="' + L.mint + '" filter="url(#glowS)"/><circle r="1" fill="#ffffff"/></g>';
    out += dr;
    var pl = fb(x0 + 1.4, y0 + 2.2, 0.1, 4.2, 2.6, 0.22, '#26323e', '#1c2833', '#151f29');
    [[y0 + 2.22], [y0 + 4.78]].forEach(function (yy) {
      var a = P(x0 + 1.42, yy[0], 0.33), b2 = P(x0 + 5.58, yy[0], 0.33);
      pl += line(a, b2, L.mint, 3, ' opacity=".35" filter="url(#glow2)"') + line(a, b2, '#8ff8d4', 0.9);
    });
    add(x0 + 3.5, y0 + 3.5, pl + '<g class="piles"></g>');
    add(x0 + 0.42, y0 + 6.5, plant(x0 + 0.42, y0 + 6.5));
    return out + sortJoin(items) + shellFront(x0, y0);
  };
  // two piles on the plinth, ET10 green and USDC blue: five stacks of coins each, taller with every order of
  // magnitude, each pile under a glass case with its glow over it
  function vaultPiles(x0, y0, V) {
    var out = '';
    [[V.et10, '#46f5bf', '#169a68', '#0f6e4b', x0 + 2.3, 'g-halo-g'], [V.usdc * 100, '#6aa4ff', '#2a62c4', '#1d4790', x0 + 4.3, 'g-halo-b']].forEach(function (p) {
      var lvl = Math.max(0, Math.log10(1 + p[0] / 50));
      var stacks = [[0, 0, 1], [0.48, 0.12, 0.8], [-0.08, 0.52, 0.7], [0.46, 0.6, 0.55], [0.2, 0.3, 0.9]].map(function (s, i) { return s.concat([i]); })
        .sort(function (a, b) { return a[0] + a[1] - b[0] - b[1]; });
      stacks.forEach(function (s) {
        if (lvl <= 0 && s[3]) return;
        var h = Math.max(0.06, lvl * 0.2 * s[2]), sx = p[4] + s[0], sy = y0 + 3.0 + s[1];
        out += cyl(sx, sy, 0.32, 0.32 + h, 0.19, p[1], p[2], p[3]);
        for (var k = 0.08; k < h - 0.02; k += 0.08) {
          var a = P(sx, sy, 0.32 + k);
          out += '<path d="M' + f1(a[0] - 0.19 * RXc) + ',' + f1(a[1]) + ' a' + f1(0.19 * RXc) + ',' + f1(0.19 * RYc) + ' 0 0 0 ' + f1(0.38 * RXc) + ',0" fill="none" stroke="' + p[3] + '" stroke-width=".5" opacity=".7"/>';
        }
      });
      var ch = Math.max(0.5, lvl * 0.2 + 0.25), c = P(p[4] + 0.25, y0 + 3.35, 0.4 + lvl * 0.2);
      out += '<ellipse cx="' + f1(c[0]) + '" cy="' + f1(c[1]) + '" rx="30" ry="20" fill="url(#' + p[5] + ')" opacity=".3"/>';
      out += box(p[4] - 0.375, y0 + 2.725, 0.32, 1.25, 1.25, ch, 'rgba(201, 219, 228, .07)', 'rgba(201, 219, 228, .05)', 'rgba(201, 219, 228, .035)', 'rgba(200, 222, 232, .32)');
    });
    return out;
  }
  // The free lot, as the 3D's: the bare deck marked out by a square of lane dashes; inside it a pad -- a faint grid
  // in a disc, a wall of teal light round it with a bright line along its top, a thin teal circle at its foot -- and
  // one cyan dashed circle round the pad; the label lies on the floor in the middle
  Office.prototype.lotRoom = function (x0, y0) {
    var out = poly([P(x0, y0 + RS, 0), P(x0, y0 + RS, 1.0), P(x0, y0, 1.0), P(x0 + RS, y0, 1.0), P(x0 + RS, y0, 0), P(x0 + RS, y0 + RS, 0)], 'transparent', null, 0, 1, ' class="hit"');
    var z = 0.02, ins = 0.35, a = ins, b = RS - ins, cx = x0 + RS / 2, cy = y0 + RS / 2;
    [[a, a, b, a], [b, a, b, b], [b, b, a, b], [a, b, a, a]].forEach(function (s) { out += line(P(x0 + s[0], y0 + s[1], z), P(x0 + s[2], y0 + s[3], z), null, 0, ' class="lotf"'); });
    out += disc(cx, cy, z, 2.5, 'url(#g-pad)');
    var c = P(cx, cy, z), g = '<clipPath id="cp-lot"><ellipse cx="' + f1(c[0]) + '" cy="' + f1(c[1]) + '" rx="' + f1(2.38 * RXc) + '" ry="' + f1(2.38 * RYc) + '"/></clipPath>' +
      '<g clip-path="url(#cp-lot)" stroke="#46d7c8" stroke-width=".5" opacity=".2">';
    for (var t = -2.4; t <= 2.41; t += 0.4) g += line(P(cx + t, cy - 2.5, z), P(cx + t, cy + 2.5, z)) + line(P(cx - 2.5, cy + t, z), P(cx + 2.5, cy + t, z));
    out += g + '</g>';
    out += disc(cx, cy, z, 2.95, 'none', '#36c8e8', 1, ' stroke-dasharray="2.8 2.6" opacity=".85"');
    out += disc(cx, cy, z, 1.92, 'none', '#1ed8cc', 0.8, ' opacity=".75"');
    out += '<g class="padw">' + band(cx, cy, z, 0.48, 2.38, false, 'url(#g-padw)', ' opacity=".55"') + '</g>';
    var lc = P(cx, cy, z);
    out += text(lc[0], lc[1] - 1.5, '+', 15, '#46f8c8', 400, 'middle', 'display', ' filter="url(#glowS)"');
    out += text(lc[0], lc[1] + 9.5, 'ADD DEPARTMENT', 7.2, '#e6faf6', 600, 'middle', 'sans', ' letter-spacing=".6" filter="url(#glowS)"');
    out += '<g class="padw">' + band(cx, cy, z, 0.48, 2.38, true, 'url(#g-padw)') +
      disc(cx, cy, 0.48, 2.38, 'none', '#3ae8d0', 3.4, ' opacity=".35" filter="url(#glow2)"') + disc(cx, cy, 0.48, 2.38, 'none', '#6ff8e0', 1.2) +
      disc(cx, cy, z, 2.38, 'none', '#1ed8cc', 0.8, ' opacity=".6"') + '</g>';
    return out;
  };

  /* ---------------- update in place ---------------- */
  Office.prototype.update = function () {
    var S = CO.S, self = this;
    if (this.shape() !== this.shapeKey) return this.layout();
    var over = '', cells = this.cells, ex = function (k) { return self.gRooms.querySelector('[data-key="' + k + '"]'); };
    var setCls = function (g, k, st, extra) {
      g.setAttribute('class', 'room st-' + st + (extra || '') + (self.sel === k ? ' sel' : '') + (g.classList.contains('born') ? ' born' : '') + (g.classList.contains('hover') ? ' hover' : ''));
    };
    var paint = function (el, html) { if (el && el._h !== html) { el._h = html; el.innerHTML = html; } };
    var turnsBy = {}, have = {};
    S.strip.forEach(function (c) { turnsBy[c.dept_id] = (turnsBy[c.dept_id] || 0) + 1; });
    Object.keys(cells).forEach(function (k) { have[cells[k][0] + ',' + cells[k][1]] = 1; });
    var anyWork = false;
    S.departments.forEach(function (d) {
      var key = 'd' + d.id, g = ex(key); if (!g) return;
      // orange only while it waits on the owner ("oranzove sviti jen roomka ktera chce pozornost moji, needs you")
      var v = CO.deptView(d), ln = CO.deptLine(d, v), st = ln.tone === 'red' ? 'waiting' : v.status;
      var x0 = cells[key][0], y0 = cells[key][1];
      if (v.status === 'working') anyWork = true;
      setCls(g, key, st, '');
      var dot = STC[st] || STC.idle;
      var col = st === 'queued' ? TONEC.dim : dot, title, sub, mode;
      // the wall screen says what the plate says, a little longer: never passes or attempts
      if (v.running) { title = v.running.title; sub = CO.expertName(v.running.expert) + ' is on it'; mode = 'run'; }
      else if (v.waiting) { title = 'Needs you'; sub = 'approve or reject on the right'; mode = 'full'; col = STC.waiting; }
      else if (v.queued.length) { title = 'Up next: ' + v.queued[0].title; sub = ''; mode = ''; }
      else { title = d.schedule && d.next_run ? 'Next run at ' + CO.hhmm(d.next_run) : 'Idle'; sub = ''; mode = ''; }
      var scr = g.querySelector('.scr');
      if (scr) paint(scr, wallScreen(x0, y0, +scr.getAttribute('data-u0'), +scr.getAttribute('data-u1'), title, sub, col, mode));
      var kb = g.querySelector('.kb');
      if (kb) paint(kb, kanban(x0, y0, { queued: v.queued.length, running: v.running ? 1 : 0, done: v.done, failed: v.failed }, +kb.getAttribute('data-v0'), +kb.getAttribute('data-v1')));
      v.experts.slice(0, 3).forEach(function (e, i) {
        Array.prototype.forEach.call(g.querySelectorAll('[data-i="' + i + '"]'), function (m) { m.classList.toggle('on', e.state === 'working'); });
        var ag = g.querySelector('.agent[data-agent="' + key + ':' + i + '"]');
        if (ag) { ag.classList.toggle('working', e.state === 'working'); ag.classList.toggle('idle', e.state !== 'working'); }
      });
      // its name on its front glass; what it does is on its wall screen and one click away
      over += glassSign(cells[key], key, d.name, d, have, st);
    });
    // the Manager's room
    var hub = ex('hub');
    if (hub) {
      var paused = S.company.status === 'paused', hx = cells.hub[0], hy = cells.hub[1];
      setCls(hub, 'hub', paused ? 'idle' : 'working');
      var bars = S.departments.map(function (d) { var v = CO.deptView(d); return [v.status === 'idle' ? STC.queued : STC[v.status], turnsBy[d.id] || 0]; });
      var hs = hub.querySelector('.scr');
      paint(hs, barsScreen(hx, hy, +hs.getAttribute('data-u0'), +hs.getAttribute('data-u1'), 'TURNS BY DEPT TODAY', bars));
      var pc = { queued: S.plan.length, running: S.tasks.filter(function (t) { return t.status === 'running'; }).length,
        done: S.strip.filter(function (c) { return c.state === 'done'; }).length, failed: S.strip.filter(function (c) { return c.state === 'failed'; }).length };
      var hk = hub.querySelector('.kb');
      paint(hk, kanban(hx, hy, pc, +hk.getAttribute('data-v0'), +hk.getAttribute('data-v1')));
      var mg = hub.querySelector('.agent');
      if (mg) { mg.classList.toggle('working', S.company.status === 'active'); mg.classList.toggle('idle', S.company.status !== 'active'); }
      // over the rings: what needs the owner, or that nothing does
      var ht = this.hubTop, na = S.approvals.length;
      if (ht) over += needPill(ht[0], ht[1] - 10, na ? na + (CO.RO ? ' WAIT FOR ITS OWNER' : na === 1 ? ' NEEDS YOU' : ' NEED ATTENTION') : 'ALL CLEAR', na > 0);
      over += glassSign(cells.hub, 'hub', 'Command', 'hub', have, paused ? 'idle' : anyWork ? 'working' : 'idle');
    }
    var au = ex('audit');
    if (au) {
      var A = S.audit, days = Math.max(0, Math.ceil((A.next_at - S.clock) / 86400000)), nf = A.last ? A.last.findings.length : 0, ax = cells.audit[0], ay = cells.audit[1];
      setCls(au, 'audit', 'idle');
      var as = au.querySelector('.scr');
      paint(as, wallScreen(ax, ay, +as.getAttribute('data-u0'), +as.getAttribute('data-u1'), 'Weekly audit: next in ' + days + 'd', nf + ' findings last week', STC.idle, ''));
      over += glassSign(cells.audit, 'audit', 'Operations', 'audit', have, 'idle');
    }
    // the Treasury: its name on its glass, and over its plinth what it holds, ET10 and USDC lit ("v cedulce Vaultu by
    // melo svitit kolik tam je"); a visitor finds it private and the plinth bare
    var vr = ex('vault');
    if (vr) {
      var VT = CO.vaultTotals(), priv = !!CO.RO, vkey = priv ? 'priv' : Math.round(VT.et10) + '|' + VT.usdc.toFixed(2);
      setCls(vr, 'vault', 'idle', priv ? ' closed' : '');
      var pg = vr.querySelector('.piles');
      if (pg._k !== vkey) { pg._k = vkey; pg.innerHTML = priv ? '' : vaultPiles(cells.vault[0], cells.vault[1], VT); }
      over += glassSign(cells.vault, 'vault', 'Vault', 'vault', have, 'idle');
      if (!priv) {
        var vp = P(cells.vault[0] + 5.2, cells.vault[1] + 2.6, 1.05);   // over the plinth's back, clear of the name on the glass
        over += amountPill(vp[0], vp[1], 'vault', [[CO.fmtEt(VT.et10), '#38f5b8', 1], [' ET10 · ', L.dim], [CO.fmtUsd(VT.usdc), '#8fbaff', 1], [' USDC', L.dim]]);
      }
    }
    // the selection ring lies on the floor, just under the selected room: walls, people and plates stay above it
    var oldRing = this.gRooms.querySelector('.selring');
    if (oldRing) oldRing.parentNode.removeChild(oldRing);
    var selRoom = this.sel && cells[this.sel] ? ex(this.sel) : null;
    if (selRoom) {
      var s = cells[this.sel], tmp = document.createElementNS(NS, 'g');
      tmp.innerHTML = poly([P(s[0] - 0.15, s[1] - 0.15, 0.12), P(s[0] + 7.15, s[1] - 0.15, 0.12), P(s[0] + 7.15, s[1] + 7.15, 0.12), P(s[0] - 0.15, s[1] + 7.15, 0.12)],
        'none', L.hub, 2.4, 1, ' class="selring" filter="url(#glow)"');
      if (tmp.firstChild) selRoom.parentNode.insertBefore(tmp.firstChild, selRoom);
    }
    this.gOver.innerHTML = over;
    this.markPlates();
    // a lane lights while work runs along it
    Array.prototype.forEach.call(this.gFloor.querySelectorAll('.flow'), function (pl) {
      var k = pl.getAttribute('data-path'), d = k.charAt(0) === 'd' ? CO.dept(+k.slice(1)) : null;
      pl.classList.toggle('hot', !!(d && CO.deptView(d).status === 'working'));
    });
    this.svg.classList.toggle('paused', S.company.status === 'paused');
  };
  // a room's plate framed in its colour while the room is under the mouse or open, as the 3D's
  Office.prototype.markPlates = function () {
    var self = this;
    Array.prototype.forEach.call(this.gOver.querySelectorAll('.rp'), function (p) {
      var k = p.getAttribute('data-key');
      p.classList.toggle('sel', self.sel === k); p.classList.toggle('hov', self.hover === k);
    });
  };

  /* ---------------- packets ---------------- */
  Office.prototype.packet = function (from, to, colour, delay) {
    var p;
    if (from === 'hub' && this.paths[to]) p = this.paths[to].slice().reverse();
    else if (to === 'hub' && this.paths[from]) p = this.paths[from].slice();
    else if (this.paths[from] && this.paths[to]) p = this.paths[from].concat(this.paths[to].slice().reverse().slice(1));
    if (!p) return;
    var id = { cyan: 'g-halo-c', green: 'g-halo-g', red: 'g-halo-r', blue: 'g-halo-b' }[colour] || 'g-halo-c';
    var hex = { cyan: L.hub, green: L.mint, red: L.amber, blue: C.blue }[colour] || L.hub;
    var g = document.createElementNS(NS, 'g');
    g.setAttribute('class', 'pk');
    var html = '';
    for (var i = 4; i >= 1; i--) html += '<circle class="tr" r="' + (2.6 - i * 0.4).toFixed(1) + '" fill="' + hex + '" opacity="' + (0.5 - i * 0.1).toFixed(2) + '"/>';
    html += '<circle r="10" fill="url(#' + id + ')"/><circle r="2.8" fill="' + hex + '"/><circle r="1.2" fill="#ffffff" opacity=".8"/>';
    g.innerHTML = html;
    g.style.opacity = '0';
    this.gPk.appendChild(g);
    var len = plen(p);
    this.packets.push({ g: g, p: p, t0: performance.now() + (delay || 0), dur: Math.max(900, len * 150), to: to });
  };
  Office.prototype.ping = function (key, colour) {
    var g = this.gRooms.querySelector('[data-key="' + key + '"]');
    if (!g) return;
    g.classList.remove('ping', 'ping-g', 'ping-r');
    void g.getBoundingClientRect();
    g.classList.add('ping'); if (colour === 'green') g.classList.add('ping-g'); if (colour === 'red') g.classList.add('ping-r');
    setTimeout(function () { g.classList.remove('ping', 'ping-g', 'ping-r'); }, 900);
  };
  // The flat office's own pace (2026-10-19, for weak computers; nothing is drawn differently, only less often while
  // nobody does anything). Any change anywhere in the drawing repaints the whole SVG, and its CSS animations change
  // it every display frame, so they run on this clock instead of the browser's: every frame while the view is being
  // moved or zoomed and for the first seconds; otherwise every other frame on a 120/144 Hz screen (60 or 72 a
  // second) and 30 a second on a computer that could not hold about 45 while everything moved. Measured: a 2D
  // office left alone cost 430 ms of the main thread a second at 144 Hz, almost all of it repainting.
  function pacer(busy) {
    var last = 0, drawn = 0, avg = 0, slow = false, t0 = performance.now();
    return function (now) {
      var dt = now - last; last = now;
      if (busy() || now - t0 < 3000) {
        if (dt > 0 && dt < 250) { avg = avg ? avg * 0.94 + dt * 0.06 : dt; slow = avg > 22 ? true : avg < 18 ? false : slow; }
        drawn = now; return true;
      }
      if (now - drawn < (slow ? 30 : 12.5)) return false;
      drawn = now; return true;
    };
  }
  // the stylesheet's animations, stepped by hand on the pace above: each is paused the first time it is seen and its
  // time set on every paced frame; what the stylesheet pauses while the company is paused stays where it is
  var STILL_WHEN_PAUSED = '.flow.hot, .holo, .mote, .beam, .holo-core';
  Office.prototype.stepAnims = function (now) {
    var list = this.svg.getAnimations ? this.svg.getAnimations({ subtree: true }) : [], still = this.svg.classList.contains('paused');
    for (var i = 0; i < list.length; i++) {
      var a = list[i];
      if (a.__t0 == null) { a.__base = a.currentTime || 0; a.__t0 = now; a.pause(); }
      var tg = a.effect && a.effect.target;
      if (still && tg && tg.matches && tg.matches(STILL_WHEN_PAUSED)) { a.__base = a.currentTime || 0; a.__t0 = now; continue; }
      a.currentTime = a.__base + (now - a.__t0);
    }
  };
  Office.prototype.frame = function (now) {
    var self = this;
    this.packets = this.packets.filter(function (k) {
      var f = (now - k.t0) / k.dur;
      if (f < 0) return true;
      if (f >= 1) { k.g.remove(); self.ping(k.to, null); return false; }
      var e = f < 0.5 ? 2 * f * f : 1 - Math.pow(-2 * f + 2, 2) / 2;
      var q = along(k.p, e), s = P(q[0], q[1], 0.18);
      k.g.style.opacity = f < 0.08 ? f / 0.08 : f > 0.92 ? (1 - f) / 0.08 : 1;
      var kids = k.g.childNodes;
      for (var i = 0; i < 4; i++) {
        var tq = along(k.p, Math.max(0, e - (4 - i) * 0.018)), ts = P(tq[0], tq[1], 0.18);
        kids[i].setAttribute('cx', f1(ts[0] - s[0])); kids[i].setAttribute('cy', f1(ts[1] - s[1]));
      }
      k.g.setAttribute('transform', 'translate(' + f1(s[0]) + ' ' + f1(s[1]) + ')');
      return true;
    });
    Object.keys(this.walkers).forEach(function (id) {
      var w = self.walkers[id], el = w.el;
      if (!el.isConnected) { delete self.walkers[id]; return; }
      var f = (now - w.t0) / w.dur;
      if (el.classList.contains('working') && w.phase !== 'home') { w.phase = 'home'; w.from = w.pos; w.to = w.home; w.t0 = now; w.dur = 500; f = 0; }
      if (f >= 1) {
        w.pos = w.to;
        if (w.phase === 'out') { w.phase = 'stay'; w.t0 = now; w.dur = 1600 + Math.random() * 1600; return; }
        if (w.phase === 'stay') { w.phase = 'home'; w.from = w.pos; w.to = w.home; w.t0 = now; w.dur = 2000; return; }
        el.setAttribute('transform', 'translate(' + w.home[0] + ' ' + w.home[1] + ')');
        el.classList.remove('walking');
        delete self.walkers[id]; return;
      }
      if (w.phase === 'stay') return;
      var e = f < 0.5 ? 2 * f * f : 1 - Math.pow(-2 * f + 2, 2) / 2;
      w.pos = [w.from[0] + (w.to[0] - w.from[0]) * e, w.from[1] + (w.to[1] - w.from[1]) * e];
      el.setAttribute('transform', 'translate(' + f1(w.pos[0]) + ' ' + f1(w.pos[1]) + ')');
    });
  };
  // now and then an idle agent gets up: to the task board, the window, a colleague
  Office.prototype.wander = function () {
    if (document.hidden || CO.S.company.status === 'paused' && Math.random() < 0.5) return;
    var idle = Array.prototype.filter.call(this.gRooms.querySelectorAll('.agent.idle'), function (a) { return !a.classList.contains('walking'); });
    if (!idle.length || Object.keys(this.walkers).length >= 3 || Math.random() < 0.35) return;
    var el = idle[Math.floor(Math.random() * idle.length)], id = el.getAttribute('data-agent');
    var key = id.split(':')[0], c = this.cells[key]; if (!c) return;
    // open floor only: in front of the desks, off the dais, not on a colleague's spot
    var spots = key === 'hub' ? [[10.2, 13.6], [13.4, 13.0], [9.6, 11.0]] : [[c[0] + 2.6, c[1] + 4.9], [c[0] + 3.3, c[1] + 5.2], [c[0] + 2.9, c[1] + 4.6]];
    var tgt = spots[Math.floor(Math.random() * spots.length)], sp = P(tgt[0], tgt[1], 0.1);
    var home = [+el.getAttribute('data-hx'), +el.getAttribute('data-hy')];
    el.classList.add('walking');
    this.walkers[id] = { el: el, home: home, from: home, to: sp, pos: home, t0: performance.now(), dur: 2200, phase: 'out' };
  };

  /* ---------------- camera: viewBox zoom, pan, fit, focus ---------------- */
  Office.prototype.apply = function () {
    var v = this.vb;
    this.svg.setAttribute('viewBox', f1(v.x) + ' ' + f1(v.y) + ' ' + f1(v.w) + ' ' + f1(v.h));
  };
  Office.prototype.client = function () { var r = this.svg.getBoundingClientRect(); return { w: Math.max(50, r.width), h: Math.max(50, r.height), l: r.left, t: r.top }; };
  Office.prototype.tween = function (to, ms) {
    var self = this, from = { x: this.vb.x, y: this.vb.y, w: this.vb.w, h: this.vb.h }, t0 = performance.now();
    if (!ms) { this.vb = to; this.apply(); return; }
    this.tw = t0;
    (function step(now) {
      if (self.tw !== t0) return;
      var f = Math.min(1, (now - t0) / ms), e = 1 - Math.pow(1 - f, 3);
      self.vb = { x: from.x + (to.x - from.x) * e, y: from.y + (to.y - from.y) * e, w: from.w + (to.w - from.w) * e, h: from.h + (to.h - from.h) * e };
      self.apply();
      if (f < 1) requestAnimationFrame(step); else self.tw = 0;   // done: the pacer may slow down again
    })(t0);
  };
  // what is drawn: the platform, its hull and keel, the rooms and the plates over them
  Office.prototype.bounds = function () {
    var r = this.plateRect || { x: 0, y: 0, x2: 100, y2: 100 }, x = r.x, y = r.y, x2 = r.x2, y2 = r.y2;
    [this.gRooms, this.gOver].forEach(function (g) {
      var b = g.getBBox(); if (!b.width) return;
      x = Math.min(x, b.x); y = Math.min(y, b.y); x2 = Math.max(x2, b.x + b.width); y2 = Math.max(y2, b.y + b.height);
    });
    return { x: x - 14, y: y - 8, w: x2 - x + 28, h: y2 - y + 16 };
  };
  // fill the stage below its top bar (live, 2D/3D, zoom), centred
  Office.prototype.fit = function (anim) {
    var b = this.bounds(), c = this.client(), top = 44, availH = Math.max(80, c.h - top);
    var k = Math.min(c.w / b.w, availH / b.h), w = c.w / k, h = c.h / k;
    var x = b.x + b.w / 2 - w / 2, y = b.y - top / k - (availH / k - b.h) / 2;
    this.tween({ x: x, y: y, w: w, h: h }, anim === false ? 0 : 420);
  };
  Office.prototype.zoom = function (f, cx, cy) {
    var c = this.client(), v = this.vb;
    var px = cx == null ? 0.5 : (cx - c.l) / c.w, py = cy == null ? 0.5 : (cy - c.t) / c.h;
    var b = this.bounds(), maxW = b.w * 2.2, minW = 160;
    var nw = Math.max(minW, Math.min(maxW, v.w * f)), k = nw / v.w, nh = v.h * k;
    var to = { x: v.x + (v.w - nw) * px, y: v.y + (v.h - nh) * py, w: nw, h: nh };
    if (cx == null) this.tween(to, 260); else { this.tw = 0; this.vb = to; this.apply(); }
  };
  // bring a room to the middle of what the drawer leaves visible
  Office.prototype.focus = function (key, leftPx, tight) {
    var c = this.cells[key]; if (!c) return;
    if (tight) {
      // the room, its walls and its plate fill the stage below the top bar
      var cz = this.client(), m = P(c[0] + 3.5, c[1] + 3.6, 0.45), top = 50, bottom = 8;
      var k = Math.min(cz.w / 400, (cz.h - top - bottom) / 300), ww = cz.w / k, hh = cz.h / k;
      this.tween({ x: m[0] - ww / 2, y: m[1] - (top + (cz.h - top - bottom) / 2) / k, w: ww, h: hh }, 700);
      return;
    }
    var cl = this.client(), mid = P(c[0] + 3.5, c[1] + 3.5, 0.6);
    var visW = cl.w - (leftPx || 0), w = Math.min(this.vb.w, Math.max(420, RS * SC * 2.6 * cl.w / Math.max(200, visW)));
    var h = w * cl.h / cl.w, fx = ((leftPx || 0) + visW / 2) / cl.w;
    this.tween({ x: mid[0] - w * fx, y: mid[1] - h * 0.5, w: w, h: h }, 520);
  };
  Office.prototype.resize = function () {
    var c = this.client(), v = this.vb;
    if (!this.fitted) return;
    var cy = v.y + v.h / 2, nh = v.w * c.h / c.w;
    this.vb = { x: v.x, y: cy - nh / 2, w: v.w, h: nh };
    this.apply();
  };
  Office.prototype.select = function (key) { this.sel = key; this.update(); };

  /* ---------------- input ---------------- */
  Office.prototype.bind = function () {
    var self = this, svg = this.svg, drag = null;
    // a hand on the drawing, for the pacer
    ['pointerdown', 'pointermove', 'wheel'].forEach(function (ev) { svg.addEventListener(ev, function () { self.lastInput = performance.now(); }, { passive: true }); });
    svg.addEventListener('pointerdown', function (e) {
      if (e.button !== 0) return;
      drag = { x: e.clientX, y: e.clientY, vx: self.vb.x, vy: self.vb.y, moved: false, id: e.pointerId };
    });
    window.addEventListener('pointermove', function (e) {
      if (drag) {
        var dx = e.clientX - drag.x, dy = e.clientY - drag.y;
        if (!drag.moved && Math.abs(dx) + Math.abs(dy) > 4) { drag.moved = true; svg.classList.add('grabbing'); self.hideTip(); try { svg.setPointerCapture(drag.id); } catch (er) { /* fine */ } }
        if (drag.moved) {
          var c = self.client(); self.tw = 0;
          self.vb.x = drag.vx - dx * self.vb.w / c.w; self.vb.y = drag.vy - dy * self.vb.h / c.h; self.apply();
        }
        return;
      }
      if (e.target.closest && svg.contains(e.target)) self.hoverAt(e);
    });
    window.addEventListener('pointerup', function (e) {
      if (!drag) return;
      var was = drag; drag = null; svg.classList.remove('grabbing');
      if (was.moved) return;
      var pc = e.target.closest ? e.target.closest('.pc') : null;
      if (pc && svg.contains(pc)) { window.open(pc.getAttribute('data-link'), '_blank', 'noopener'); return; }
      var t = e.target.closest ? e.target.closest('[data-key]') : null;
      if (t && svg.contains(t)) CO.emit('office:click', t.getAttribute('data-key'));
    });
    svg.addEventListener('wheel', function (e) { e.preventDefault(); self.zoom(Math.pow(1.0018, e.deltaY), e.clientX, e.clientY); }, { passive: false });
    svg.addEventListener('pointerleave', function () { self.hideTip(); self.setHover(null); });
  };
  Office.prototype.setHover = function (key) {
    if (this.hover === key) return;
    var old = this.hover && this.gRooms.querySelector('[data-key="' + this.hover + '"]');
    if (old) old.classList.remove('hover');
    this.hover = key;
    var g = key && this.gRooms.querySelector('[data-key="' + key + '"]');
    if (g) g.classList.add('hover');
    this.markPlates();
  };
  Office.prototype.hoverAt = function (e) {
    var ag = e.target.closest('.agent'), rm = e.target.closest('[data-key]'), pc = e.target.closest('.pc');
    this.setHover(rm ? rm.getAttribute('data-key') : null);
    var html = pc ? '<b>' + esc(pc.getAttribute('data-label')) + ' ↗</b><br><span style="color:#7f93ad">' +
        esc(pc.getAttribute('data-link').replace(/^https:\/\//, '')) + '</span>'
      : ag ? this.tipFor('agent', ag.getAttribute('data-agent')) : rm ? this.tipFor('room', rm.getAttribute('data-key')) : '';
    if (!html) return this.hideTip();
    var r = this.stage.getBoundingClientRect();
    this.tip.innerHTML = html; this.tip.hidden = false;
    var x = e.clientX - r.left + 14, y = e.clientY - r.top + 14;
    if (x + this.tip.offsetWidth > r.width - 8) x = e.clientX - r.left - this.tip.offsetWidth - 14;
    if (y + this.tip.offsetHeight > r.height - 8) y = e.clientY - r.top - this.tip.offsetHeight - 14;
    this.tip.style.left = x + 'px'; this.tip.style.top = y + 'px';
  };
  Office.prototype.hideTip = function () { if (this.tip) this.tip.hidden = true; };

  /* ---------------- one room on its own: the Add-a-department dialog in the flat office ---------------- */
  // A department's room as this office draws it (deptRoom: its furniture, its look, its astronauts by role), on a slab
  // of deck and a slice of hull of its own, at work: its wall screen naming it, the first task on its board, its desks'
  // screens lit, its people working. An SVG of its own with the office's defs; still: no animation (a card's picture).
  function roomArt(d, opts) {
    opts = opts || {};
    var dd = { id: 'pv', key: d.key || 'custom', name: d.name || '', experts: (d.experts || []).slice(), look: d.look || null, run_kind: null, link: null };
    var n = dd.experts.length, title = String(dd.name || '').trim() || 'New department';
    var inner = Office.prototype.deptRoom.call(null, dd, 0, 0)
      .replace(/class="mon"/g, 'class="mon on"').replace(/class="spill"/g, 'class="spill on"').replace(/class="agent idle"/g, 'class="agent working"')
      .replace(/<g class="scr" data-u0="([\d.]+)" data-u1="([\d.]+)"><\/g>/, function (m, u0, u1) {
        return '<g class="scr">' + wallScreen(0, 0, +u0, +u1, title, n + (n === 1 ? ' expert' : ' experts') + ' · first task queued', L.neon, 'full') + '</g>';
      })
      .replace(/<g class="kb" data-v0="([\d.]+)" data-v1="([\d.]+)"><\/g>/, function (m, v0, v1) { return '<g class="kb">' + kanban(0, 0, { queued: 1, running: 0, done: 0, failed: 0 }, +v0, +v1) + '</g>'; });
    // under it: the deck's slab with its lit rim, a hull a little lower than the office's and its keel, a glow below
    var pad = 0.5, x0 = -pad, y0 = -pad, x1 = RS + pad, y1 = RS + pad, zt = -T - 0.12, HDp = HD, K = 0.24, R = rng(41);
    var ax = x0 + 0.12, ay = y0 + 0.12, bx = x1 - 0.12, by = y1 - 0.12, gc = P(RS / 2, RS / 2, zt - HDp - K - 0.6);
    var base = '<ellipse cx="' + f1(gc[0]) + '" cy="' + f1(gc[1]) + '" rx="' + f1(RS * SC * 1.05) + '" ry="' + f1(RS * SC * 0.5) + '" fill="url(#g-halo-g)" opacity=".16"/>' +
      box(x0 + 0.7, y0 + 0.7, zt - HDp - K, x1 - x0 - 1.4, y1 - y0 - 1.4, K, L.keelL, L.keelL, L.keelR) +
      box(ax, ay, zt - HDp, bx - ax, by - ay, HDp, L.hullTop, 'url(#g-hullL)', 'url(#g-hullR)') +
      hullFace(onBack(ax, 0, by, zt), (bx - ax) * SC, HDp * SC, R, false) + hullFace(onSide(bx, ay, 0, zt), (by - ay) * SC, HDp * SC, R, true) +
      box(x0, y0, -T, x1 - x0, y1 - y0, T, L.deckSeam, L.rimL, L.rimR) + deckPanels(x0, y0, x1 - x0, rng(23));
    [[x0, y1, x1, y1], [x1, y0, x1, y1], [x0, y0, x1, y0], [x0, y0, x0, y1]].forEach(function (s) { base += line(P(s[0], s[1], 0), P(s[2], s[3], 0), L.rimHi, 1.1, ' stroke-linecap="round"'); });
    var a = P(RS / 2 - 0.42, y1, -T * 0.55), b = P(RS / 2 + 0.42, y1, -T * 0.55);
    base += line(a, b, '#24e8ff', 3.2, ' opacity=".35" filter="url(#glow2)"') + line(a, b, '#7ff0ff', 1.3, ' stroke-linecap="round"');
    // its frame: the back corner's top, the left and right corners, the keel's foot, the glow under it
    var top = P(0, 0, WZ + 0.35)[1] - 6, left = P(x0, y1, 0)[0] - 8, right = P(x1, y0, 0)[0] + 8;
    var bot = Math.max(P(x1 - 0.7, y1 - 0.7, zt - HDp - K)[1], P(bx, by, zt - HDp)[1]) + 12;
    var vb = f1(left) + ' ' + f1(top) + ' ' + f1(right - left) + ' ' + f1(bot - top);
    return '<svg class="office roomart' + (opts.still ? ' still' : '') + '" viewBox="' + vb + '" preserveAspectRatio="xMidYMid meet" xmlns="' + NS + '">' + DEFS +
      base + '<g class="room st-working" data-key="pv">' + inner + '</g></svg>';
  }
  // an expert as this office's astronaut of its role, on a disc of deck ringed in the role's colour
  function astroArt(role, still) {
    var col = (CO.EXPERT_INFO && CO.EXPERT_INFO[role] && CO.EXPERT_INFO[role].col) || '#00cfff';
    return '<svg class="office astroart' + (still ? ' still' : '') + '" viewBox="-30 -36 60 45" preserveAspectRatio="xMidYMid meet" xmlns="' + NS + '">' + DEFS +
      '<ellipse cx="0" cy="2" rx="27" ry="9" fill="' + col + '" opacity=".12"/>' +
      '<ellipse cx="0" cy="1.6" rx="17" ry="6.4" fill="#121b25"/><ellipse cx="0" cy="0" rx="17" ry="6.2" fill="#1b2632" stroke="' + col + '" stroke-width="1.2"/>' +
      '<ellipse cx="0" cy="0" rx="17" ry="6.2" fill="none" stroke="' + col + '" stroke-width="3" opacity=".3" filter="url(#glow2)"/>' +
      '<g class="agent working" transform="translate(0 0)">' + avatar('', role) + '</g></svg>';
  }
  var STARS = null;
  function stars() { if (STARS === null) { try { STARS = starTile(); } catch (e) { STARS = 'none'; } } return STARS; }

  // the same projection and palette for the Universe map and the building pictures
  CO.iso = { SC: SC, C30: C30, S30: S30, C: C, P: P, f1: f1, pts: pts, esc: esc, poly: poly, box: box, text: text,
    onBack: onBack, onSide: onSide, cut: cut, plant: plant, roomArt: roomArt, astroArt: astroArt, stars: stars,
    // the office's floor plan for the 3D office: the same rooms in the same places, the same corridors
    route: route, SLOTS: SLOTS, HUB: HUB, AUDIT: AUDIT, VAULT: VAULT, RS: RS };
})();
