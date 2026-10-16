/* The /company mockup: the live office. An isometric SVG drawn from world coordinates
 * (1 unit = one floor tile), so every room, desk, monitor, wall screen and task note sits
 * where the data puts it. Rooms are rebuilt only when the company's shape changes (a
 * department added, edited or removed); everything else updates in place: status classes,
 * wall screens, task boards, plates. Packets ride the floor conduits between the rooms
 * and the Manager; idle agents get up and walk now and then. Zoom, pan, fit and focus
 * move the viewBox, so it stays sharp at any size. */
(function () {
  'use strict';
  var CO = window.CO;
  var SC = 22, C30 = Math.cos(Math.PI / 6), S30 = 0.5, RS = 7;
  var C = { bg: '#0a0e17', deep: '#06090f', navy: '#0d1520', navy2: '#111a28', line: '#16233a', line2: '#1a2a44',
    line3: '#1e3050', plate: '#0c1422', tile: '#101b2d', text: '#e6edf7', dim: '#a9b8cc', dim2: '#7f93ad',
    cyan: '#00cfff', green: '#00ff88', red: '#ff4444', blue: '#3b82f6' };
  var ST = { working: C.cyan, queued: C.blue, waiting: C.red, idle: C.dim2 };
  var HUB = [8, 8], YOU = [8, 16], AUDIT = [0, 16];
  var SLOTS = [[0, 0], [8, 0], [16, 0], [0, 8], [16, 8], [16, 16], [24, 0], [24, 8], [24, 16], [24, 24], [16, 24], [8, 24], [0, 24]];
  var NS = 'http://www.w3.org/2000/svg';

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
  function text(x, y, s, size, fill, weight, anchor, fam, extra) {
    var f = fam === 'display' ? "'Archivo Black',sans-serif" : "'JetBrains Mono',monospace";
    return '<text x="' + f1(x) + '" y="' + f1(y) + '" font-family="' + f + '" font-size="' + size + '" fill="' + fill +
      '" font-weight="' + (weight || 400) + '" text-anchor="' + (anchor || 'start') + '"' + (extra || '') + '>' + esc(s) + '</text>';
  }
  function onBack(x0, u, yPlane, zTop) {
    var o = P(x0 + u, yPlane, zTop);
    return 'matrix(' + C30.toFixed(4) + ' ' + S30 + ' 0 1 ' + f1(o[0]) + ' ' + f1(o[1]) + ')';
  }
  function onSide(xPlane, y0, v, zTop) {
    var o = P(xPlane, y0 + v, zTop);
    return 'matrix(' + (-C30).toFixed(4) + ' ' + S30 + ' 0 1 ' + f1(o[0]) + ' ' + f1(o[1]) + ')';
  }
  function cut(s, n) { s = String(s || ''); return s.length > n ? s.slice(0, n - 1) + '…' : s; }

  /* ---------------- pieces ---------------- */
  var DEFS = '<defs>' +
    '<filter id="glow" x="-80%" y="-80%" width="260%" height="260%"><feGaussianBlur stdDeviation="2.2" result="b"/>' +
    '<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>' +
    '<filter id="glow2" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4"/></filter>' +
    grad('g-fglow', C.cyan, 0.2) + grad('g-fglow-r', C.red, 0.16) + grad('g-fglow-b', C.blue, 0.12) +
    grad('g-spill', C.cyan, 0.35) + grad('g-ping', C.cyan, 0.5) +
    halo('g-halo-c', C.cyan) + halo('g-halo-g', C.green) + halo('g-halo-r', C.red) + halo('g-halo-b', C.blue) +
    '<linearGradient id="g-beam" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="' + C.cyan + '" stop-opacity=".55"/>' +
    '<stop offset="1" stop-color="' + C.cyan + '" stop-opacity="0"/></linearGradient>' +
    '<linearGradient id="g-glass" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="' + C.line3 + '" stop-opacity=".95"/>' +
    '<stop offset="1" stop-color="' + C.navy2 + '" stop-opacity=".55"/></linearGradient>' +
    '<linearGradient id="g-tile" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#13213a"/><stop offset="1" stop-color="' + C.tile + '"/></linearGradient>' +
    '<linearGradient id="g-scr" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0c1a2c"/><stop offset="1" stop-color="' + C.deep + '"/></linearGradient>' +
    '<linearGradient id="g-plate" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="' + C.plate + '"/><stop offset="1" stop-color="#0a1120"/></linearGradient>' +
    body('gb-cyan', C.cyan) + body('gb-blue', C.blue) + body('gb-green', C.green) + body('gb-red', C.red) + body('gb-slate', C.dim2) +
    '<radialGradient id="g-shadow"><stop offset="0" stop-color="' + C.deep + '" stop-opacity=".9"/><stop offset="1" stop-color="' + C.deep + '" stop-opacity="0"/></radialGradient>' +
    '</defs>';
  function grad(id, c, op) {
    return '<radialGradient id="' + id + '"><stop offset="0" stop-color="' + c + '" stop-opacity="' + op + '"/><stop offset="1" stop-color="' + c + '" stop-opacity="0"/></radialGradient>';
  }
  function halo(id, c) {
    return '<radialGradient id="' + id + '"><stop offset="0" stop-color="' + c + '" stop-opacity=".95"/><stop offset=".35" stop-color="' + c +
      '" stop-opacity=".45"/><stop offset="1" stop-color="' + c + '" stop-opacity="0"/></radialGradient>';
  }
  function body(id, c) {
    return '<linearGradient id="' + id + '" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="' + c + '"/><stop offset="1" stop-color="' + c + '" stop-opacity=".55"/></linearGradient>';
  }

  function avatar(label, cls, head) {
    var w = 5.6 * label.length + 9;
    return '<ellipse cx="0" cy="0" rx="9" ry="4" fill="url(#g-shadow)"/>' +
      '<ellipse class="ring" cx="0" cy="0" rx="11" ry="5"/>' +
      '<ellipse class="ring2" cx="0" cy="0" rx="11" ry="5"/>' +
      '<g class="bob"><rect class="body" x="-6" y="-17" width="12" height="14" rx="5"/>' +
      '<rect x="-6" y="-9" width="12" height="6" rx="2" fill="' + C.deep + '" opacity=".28"/>' +
      '<circle cx="0" cy="-21.5" r="4.8" fill="' + (head || C.dim) + '"/>' +
      '<circle cx="-1.7" cy="-23.2" r="1.7" fill="' + C.text + '" opacity=".35"/></g>' +
      (label ? '<g class="lbl"><rect x="' + f1(-w / 2) + '" y="-39.5" width="' + f1(w) + '" height="11.5" rx="5.75"/>' +
        text(0, -30.9, label, 7.6, C.text, 600, 'middle') + '</g>' : '');
  }
  function agentAt(x, y, key, i, label, head) {
    var p = P(x, y, 0.1);
    return '<g class="agent idle" data-agent="' + key + ':' + i + '" data-hx="' + f1(p[0]) + '" data-hy="' + f1(p[1]) +
      '" transform="translate(' + f1(p[0]) + ' ' + f1(p[1]) + ')">' + avatar(label, '', head) + '</g>';
  }
  function desk(x, y, i, screenFill) {
    var out = box(x, y, 0, 1.9, 0.9, 0.42, C.line3, C.line, C.navy2, C.line2);
    out += box(x + 0.6, y + 0.48, 0.42, 0.7, 0.22, 0.02, '#1a2a44', C.line, C.navy);              // keyboard
    out += box(x + 0.88, y + 0.17, 0.42, 0.14, 0.06, 0.1, C.navy2, C.line, C.navy);              // stand
    var mx = x + 0.5, my = y + 0.14, mz = 0.5, mw = 0.9, md = 0.08, mh = 0.52;
    out += poly([P(mx + mw, my, mz), P(mx + mw, my + md, mz), P(mx + mw, my + md, mz + mh), P(mx + mw, my, mz + mh)], C.navy);
    out += poly([P(mx, my, mz + mh), P(mx + mw, my, mz + mh), P(mx + mw, my + md, mz + mh), P(mx, my + md, mz + mh)], C.navy2);
    var sp = P(x + 0.95, y + 0.75, 0.43);
    out += '<ellipse class="spill" data-i="' + i + '" cx="' + f1(sp[0]) + '" cy="' + f1(sp[1]) + '" rx="20" ry="8" fill="url(#g-spill)"/>';
    out += poly([P(mx, my + md, mz), P(mx + mw, my + md, mz), P(mx + mw, my + md, mz + mh), P(mx, my + md, mz + mh)],
      screenFill || C.line2, null, 0, 1, ' class="mon" data-i="' + i + '"');
    out += '<g class="code" transform="' + onBack(mx, 0.1, my + md, mz + mh - 0.05) + '">';
    [13, 8, 11, 6].forEach(function (w, k) {
      out += '<rect class="ln" x="1.5" y="' + f1(1.6 + k * 2.55) + '" width="' + w + '" height="1.1" fill="' + C.deep + '" style="animation-delay:' + (-k * 0.55 - i * 0.3).toFixed(2) + 's"/>';
    });
    out += '</g>';
    out += box(x + 0.7, y + 1.08, 0, 0.5, 0.45, 0.22, C.navy2, C.line, C.navy);                   // stool
    return out;
  }
  function plant(x, y) {
    var out = box(x, y, 0, 0.42, 0.42, 0.34, C.line3, C.line2, C.navy2, C.line);
    var c = P(x + 0.21, y + 0.21, 0.34);
    out += '<g class="leaf">' +
      '<ellipse cx="' + f1(c[0] - 4) + '" cy="' + f1(c[1] - 6) + '" rx="6" ry="7.5" fill="#0d5a3a"/>' +
      '<ellipse cx="' + f1(c[0] + 4) + '" cy="' + f1(c[1] - 8) + '" rx="5.5" ry="8" fill="#0f7a4c"/>' +
      '<ellipse cx="' + f1(c[0]) + '" cy="' + f1(c[1] - 12) + '" rx="5" ry="6.5" fill="#12a05f"/>' +
      '<ellipse cx="' + f1(c[0] + 1.5) + '" cy="' + f1(c[1] - 14) + '" rx="2" ry="2.5" fill="' + C.green + '" opacity=".45"/></g>';
    return out;
  }
  function racks(x, y, n) {
    var out = '';
    for (var i = 0; i < n; i++) {
      var rx = x + i * 0.55;
      out += box(rx, y, 0.1, 0.5, 0.55, 1.45, C.line3, C.line, C.navy2, C.line2);
      for (var k = 0; k < 8; k++) {
        var p = P(rx + 0.1 + (k % 2) * 0.22, y + 0.55, 0.35 + Math.floor(k / 2) * 0.3);
        var col = [C.green, C.cyan, C.blue, C.green][(i + k) % 4];
        out += '<rect class="led" x="' + f1(p[0]) + '" y="' + f1(p[1]) + '" width="3" height="1.5" fill="' + col + '" style="animation-delay:' + (-((i * 7 + k * 3) % 11) * 0.17).toFixed(2) + 's"/>';
      }
    }
    return out;
  }
  function devices(x, y) {
    var out = box(x, y, 0.1, 1.1, 0.45, 1.25, C.line3, C.line, C.navy2, C.line2);
    var tf, k;
    for (var s = 0; s < 3; s++) {
      tf = onBack(x, 0.08, y + 0.45, 1.27 - s * 0.38);
      out += '<g transform="' + tf + '">';
      for (k = 0; k < 3; k++) {
        out += '<rect class="dev" x="' + (1.2 + k * 6.6) + '" y="1.6" width="4.6" height="6" rx="0.8" fill="' + [C.cyan, C.green, C.blue][(s + k) % 3] +
          '" style="animation-delay:' + (-(s * 3 + k) * 0.4).toFixed(1) + 's"/>';
      }
      out += '<rect x="0" y="8.2" width="22" height="0.7" fill="' + C.line3 + '"/></g>';
    }
    return out;
  }
  function flasks(x, y) {
    var out = box(x, y, 0, 1.3, 0.6, 0.45, C.line3, C.line, C.navy2, C.line2);
    [[0.25, C.cyan, 0.5], [0.65, C.green, 0.36], [1.02, C.cyan, 0.42]].forEach(function (f, i) {
      var b = P(x + f[0], y + 0.3, 0.45), h = f[2] * SC;
      out += '<rect x="' + f1(b[0] - 3) + '" y="' + f1(b[1] - h) + '" width="6" height="' + f1(h) + '" rx="2" fill="' + C.navy + '" stroke="' + C.line3 + '" stroke-width=".6"/>';
      out += '<rect class="liq" x="' + f1(b[0] - 2.4) + '" y="' + f1(b[1] - h * 0.62) + '" width="4.8" height="' + f1(h * 0.62 - 0.6) + '" rx="1.6" fill="' + f[1] + '" opacity=".85"/>';
      out += '<ellipse cx="' + f1(b[0]) + '" cy="' + f1(b[1] - h * 0.5) + '" rx="7" ry="5" fill="url(#' + (f[1] === C.green ? 'g-halo-g' : 'g-halo-c') + ')" opacity=".35"/>';
      for (var k = 0; k < 2; k++) {
        out += '<circle class="bub" cx="' + f1(b[0] - 1 + k * 2) + '" cy="' + f1(b[1] - 2) + '" r=".7" fill="' + C.text + '" style="animation-delay:' + (-(i + k * 1.3) * 0.5).toFixed(1) + 's"/>';
      }
    });
    return out;
  }
  function candles(x0, y0, u0, u1) {
    var z0 = 0.36, z1 = 1.1, yp = y0 + 0.13;
    var out = poly([P(x0 + u0, yp, z0), P(x0 + u1, yp, z0), P(x0 + u1, yp, z1), P(x0 + u0, yp, z1)], 'url(#g-scr)', C.green, 0.8);
    out += '<g transform="' + onBack(x0, u0, yp, z1) + '">';
    var w = (u1 - u0) * SC, n = 11, bw = (w - 8) / n, v = 9;
    for (var i = 0; i < n; i++) {
      var up = [1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 1][i], o = v;
      v = Math.max(3.5, Math.min(13.5, v + (up ? -1.4 : 1.1) * (0.6 + (i % 3) * 0.4)));
      var top = Math.min(o, v), hgt = Math.max(1.1, Math.abs(o - v));
      out += '<rect' + (i === n - 1 ? ' class="lastc"' : '') + ' x="' + f1(4 + i * bw) + '" y="' + f1(top) + '" width="' + f1(bw * 0.62) + '" height="' + f1(hgt) + '" fill="' + (up ? C.green : C.red) + '"/>';
      out += '<rect x="' + f1(4 + i * bw + bw * 0.28) + '" y="' + f1(top - 1.2) + '" width=".5" height="' + f1(hgt + 2.4) + '" fill="' + (up ? C.green : C.red) + '" opacity=".7"/>';
    }
    out += text(4, 3.4, 'BASKET H2 · +1.1%', 3.2, C.green, 700) + '</g>';
    return out;
  }
  function mood(x0, y0, u0, u1) {
    var z0 = 0.36, z1 = 1.1, yp = y0 + 0.13;
    var out = poly([P(x0 + u0, yp, z0), P(x0 + u1, yp, z0), P(x0 + u1, yp, z1), P(x0 + u0, yp, z1)], C.navy2, C.line3, 0.8);
    out += '<g transform="' + onBack(x0, u0, yp, z1) + '">';
    [C.cyan, C.green, C.blue, C.red].forEach(function (c, i) { out += '<rect x="' + (3 + i * 5.2) + '" y="2.5" width="4.2" height="4.2" rx=".6" fill="' + c + '"/>'; });
    out += '<rect x="3" y="8.6" width="20" height="6.6" rx=".6" fill="none" stroke="' + C.dim2 + '" stroke-width=".5"/>';
    out += '<rect x="4.2" y="9.8" width="7" height="1.2" fill="' + C.dim2 + '"/><rect x="4.2" y="12.2" width="12" height="1" fill="' + C.line3 + '"/>';
    out += '<rect x="25" y="2.5" width="' + f1((u1 - u0) * SC - 28) + '" height="12.7" rx=".6" fill="none" stroke="' + C.cyan + '" stroke-width=".5" stroke-dasharray="1.4 1.2"/></g>';
    return out;
  }
  function whiteboard(x, y) {
    return box(x, y, 0.1, 1.05, 0.12, 1.15, C.line3, C.dim2, C.navy2, C.line2);
  }

  function shell(x0, y0, kind) {
    var out = '';
    var hit = [P(x0, y0 + RS, 0), P(x0, y0 + RS, 1.3), P(x0, y0, 1.3), P(x0 + RS, y0, 1.3), P(x0 + RS, y0, 0), P(x0 + RS, y0 + RS, 0)];
    out += poly(hit, 'transparent', null, 0, 1, ' class="hit"');
    if (kind === 'lot') {
      out += poly([P(x0, y0, 0.1), P(x0 + RS, y0, 0.1), P(x0 + RS, y0 + RS, 0.1), P(x0, y0 + RS, 0.1)], C.navy, C.blue, 1.1, 0.6, ' class="lotf" stroke-dasharray="5 5"');
      return out;
    }
    out += box(x0, y0, 0, RS, RS, 0.1, 'url(#g-tile)', C.navy2, C.navy, C.line, null, ' class="slab"');
    for (var i = 1; i < RS; i++) {
      var a = P(x0 + i, y0, 0.1), b = P(x0 + i, y0 + RS, 0.1), c = P(x0, y0 + i, 0.1), d = P(x0 + RS, y0 + i, 0.1);
      out += '<line x1="' + f1(a[0]) + '" y1="' + f1(a[1]) + '" x2="' + f1(b[0]) + '" y2="' + f1(b[1]) + '" stroke="' + C.line + '" stroke-width=".6"/>';
      out += '<line x1="' + f1(c[0]) + '" y1="' + f1(c[1]) + '" x2="' + f1(d[0]) + '" y2="' + f1(d[1]) + '" stroke="' + C.line + '" stroke-width=".6"/>';
    }
    var cc = P(x0 + RS / 2, y0 + RS / 2, 0.1);
    out += '<ellipse class="fglow" cx="' + f1(cc[0]) + '" cy="' + f1(cc[1]) + '" rx="' + f1(RS * SC * 0.95) + '" ry="' + f1(RS * SC * 0.55) + '"/>';
    out += '<ellipse class="fping" cx="' + f1(cc[0]) + '" cy="' + f1(cc[1]) + '" rx="' + f1(RS * SC * 0.8) + '" ry="' + f1(RS * SC * 0.46) + '" fill="url(#g-ping)"/>';
    // glass back walls with mullions and a lit top edge
    out += box(x0, y0, 0.1, RS, 0.12, 1.15, C.line3, 'url(#g-glass)', C.navy, null, 0.8);
    out += box(x0, y0, 0.1, 0.12, RS, 1.15, C.line3, C.navy, 'url(#g-glass)', null, 0.8);
    for (var m = 1; m < 4; m++) {
      var u = m * RS / 4, p1 = P(x0 + u, y0 + 0.12, 0.1), p2 = P(x0 + u, y0 + 0.12, 1.25);
      var q1 = P(x0 + 0.12, y0 + u, 0.1), q2 = P(x0 + 0.12, y0 + u, 1.25);
      out += '<line x1="' + f1(p1[0]) + '" y1="' + f1(p1[1]) + '" x2="' + f1(p2[0]) + '" y2="' + f1(p2[1]) + '" stroke="' + C.line2 + '" stroke-width=".7"/>';
      out += '<line x1="' + f1(q1[0]) + '" y1="' + f1(q1[1]) + '" x2="' + f1(q2[0]) + '" y2="' + f1(q2[1]) + '" stroke="' + C.line2 + '" stroke-width=".7"/>';
    }
    var e1 = P(x0, y0 + RS, 1.25), e2 = P(x0, y0, 1.25), e3 = P(x0 + RS, y0, 1.25);
    out += '<polyline class="edge" points="' + pts([e1, e2, e3]) + '" fill="none" stroke-width="1.3"/>';
    out += '<polyline class="edge2" points="' + pts([e1, e2, e3]) + '" fill="none" stroke-width="4"/>';
    [[[x0 + RS, y0], [x0 + RS, y0 + RS]], [[x0, y0 + RS], [x0 + RS, y0 + RS]]].forEach(function (s) {
      var a = P(s[0][0], s[0][1], 0.12), b = P(s[1][0], s[1][1], 0.12);
      out += '<line class="sill" x1="' + f1(a[0]) + '" y1="' + f1(a[1]) + '" x2="' + f1(b[0]) + '" y2="' + f1(b[1]) + '" stroke-width="1.2"/>';
    });
    return out;
  }

  // the room's wall screen: what runs now, or why it waits
  function wallScreen(x0, y0, u0, u1, title, sub, colour, mode) {
    var z0 = 0.36, z1 = 1.1, yp = y0 + 0.13;
    var out = poly([P(x0 + u0, yp, z0), P(x0 + u1, yp, z0), P(x0 + u1, yp, z1), P(x0 + u0, yp, z1)], 'url(#g-scr)', colour, 0.9);
    var w = (u1 - u0) * SC;
    out += '<g transform="' + onBack(x0, u0, yp, z1) + '">';
    out += text(4, 6.6, cut(title, Math.floor((w - 7) / 3.5)), 5.8, colour, 700);
    out += text(4, 11.6, cut(sub, Math.floor((w - 7) / 2.45)), 4, C.dim2, 500);
    out += '<rect x="4" y="13.4" width="' + f1(w - 8) + '" height="1.3" rx=".6" fill="' + C.line3 + '"/>';
    if (mode === 'run') {
      out += '<clipPath id="cp-' + f1(x0) + '-' + f1(y0) + '"><rect x="4" y="13.4" width="' + f1(w - 8) + '" height="1.3"/></clipPath>' +
        '<g clip-path="url(#cp-' + f1(x0) + '-' + f1(y0) + ')"><rect class="shim" x="4" y="13.4" width="' + f1((w - 8) * 0.35) + '" height="1.3" fill="' + colour + '"/></g>';
    } else if (mode === 'full') {
      out += '<rect x="4" y="13.4" width="' + f1(w - 8) + '" height="1.3" rx=".6" fill="' + colour + '" opacity=".7"/>';
    }
    out += '</g>';
    return out;
  }
  function barsScreen(x0, y0, u0, u1, title, bars) {
    var z0 = 0.36, z1 = 1.1, yp = y0 + 0.13;
    var out = poly([P(x0 + u0, yp, z0), P(x0 + u1, yp, z0), P(x0 + u1, yp, z1), P(x0 + u0, yp, z1)], 'url(#g-scr)', C.cyan, 0.9);
    var w = (u1 - u0) * SC, top = 1;
    bars.forEach(function (b) { top = Math.max(top, b[1]); });
    var bw = (w - 10) / Math.max(1, bars.length);
    out += '<g transform="' + onBack(x0, u0, yp, z1) + '">' + text(5, 4.6, title, 3.6, C.cyan, 700);
    bars.forEach(function (b, i) {
      var h = 9.5 * b[1] / top;
      out += '<rect x="' + f1(5 + i * bw) + '" y="' + f1(15.2 - h) + '" width="' + f1(bw - 2) + '" height="' + f1(Math.max(0.6, h)) + '" fill="' + b[0] + '" opacity=".9"/>';
    });
    return out + '</g>';
  }
  function kanban(x0, y0, counts) {
    var out = poly([P(x0 + 0.13, y0 + 1.0, 0.36), P(x0 + 0.13, y0 + 5.9, 0.36), P(x0 + 0.13, y0 + 5.9, 1.08), P(x0 + 0.13, y0 + 1.0, 1.08)], C.deep, C.line3, 0.8);
    ['queued', 'running', 'done', 'failed'].forEach(function (st, col) {
      var v = 1.15 + col * 1.2, c = { queued: C.blue, running: C.cyan, done: C.green, failed: C.red }[st];
      out += poly([P(x0 + 0.14, y0 + v, 1.0), P(x0 + 0.14, y0 + v + 0.95, 1.0), P(x0 + 0.14, y0 + v + 0.95, 1.04), P(x0 + 0.14, y0 + v, 1.04)], c, null, 0, 0.9);
      for (var k = 0; k < Math.min(counts[st] || 0, 4); k++) {
        var z = 0.86 - k * 0.15;
        out += poly([P(x0 + 0.14, y0 + v + 0.05, z), P(x0 + 0.14, y0 + v + 0.9, z), P(x0 + 0.14, y0 + v + 0.9, z + 0.12), P(x0 + 0.14, y0 + v + 0.05, z + 0.12)],
          c, null, 0, 0.85, st === 'running' ? ' class="note-run"' : '');
      }
    });
    return out;
  }
  function plate(cx, cy, title, colour, line2, w, key, pulse) {
    var out = '<g class="plate" data-key="' + key + '">';
    out += '<rect x="' + f1(cx - w / 2) + '" y="' + f1(cy - 17) + '" width="' + w + '" height="34" rx="6" fill="' + C.bg + '" stroke="' + colour + '" stroke-width=".9" opacity=".95"/>';
    out += '<rect x="' + f1(cx - w / 2 + 1) + '" y="' + f1(cy - 16) + '" width="' + (w - 2) + '" height="10" rx="5" fill="' + colour + '" opacity=".07"/>';
    out += '<circle' + (pulse ? ' class="pdot"' : '') + ' cx="' + f1(cx - w / 2 + 11) + '" cy="' + f1(cy - 6) + '" r="3.4" fill="' + colour + '" filter="url(#glow)"/>';
    out += text(cx - w / 2 + 20, cy - 2.4, title, 10.2, C.text, 400, 'start', 'display');
    var x = cx - w / 2 + 9;
    line2.forEach(function (s) { out += text(x, cy + 11.5, s[0], 8.6, s[1], 600); x += 6.0 * s[0].length + 7; });
    return out + '</g>';
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
    this.gWorld = svg.querySelector('.world');
    this.gFloor = svg.querySelector('.floor'); this.gRooms = svg.querySelector('.rooms');
    this.gPk = svg.querySelector('.packets'); this.gOver = svg.querySelector('.overlay');
    this.tip = stage.querySelector('.tip');
    this.vb = { x: 0, y: 0, w: 1000, h: 600 };
    this.bind();
    var self = this;
    requestAnimationFrame(function loop(t) { self.frame(t); requestAnimationFrame(loop); });
    setInterval(function () { self.wander(); }, 2600);
    if (window.ResizeObserver) new ResizeObserver(function () { self.resize(); }).observe(svg);
  }
  CO.Office = Office;

  Office.prototype.shape = function () {
    var S = CO.S;
    return S.departments.map(function (d) { return d.id + ':' + d.slot + ':' + d.key + ':' + d.experts.join(','); }).join('|');
  };

  Office.prototype.layout = function (opts) {
    var S = CO.S, self = this, born = opts && opts.born;
    this.shapeKey = this.shape();
    var cells = { hub: HUB, you: YOU, audit: AUDIT };
    var used = {};
    S.departments.forEach(function (d) { cells['d' + d.id] = SLOTS[d.slot]; used[d.slot] = 1; });
    var lot = 0; while (used[lot]) lot++;
    if (lot < SLOTS.length) cells.lot = SLOTS[lot];
    this.cells = cells;
    var all = Object.keys(cells).map(function (k) { return cells[k]; });
    var maxX = 0, maxY = 0;
    all.forEach(function (c) { maxX = Math.max(maxX, c[0] + RS); maxY = Math.max(maxY, c[1] + RS); });
    this.world = [maxX, maxY];

    // floor plate, its grid and the conduits
    var f = '<ellipse cx="' + f1(P(maxX / 2, maxY / 2)[0]) + '" cy="' + f1(P(maxX / 2, maxY / 2, -0.8)[1]) + '" rx="' + f1((maxX + maxY) * SC * 0.62) +
      '" ry="' + f1((maxX + maxY) * SC * 0.3) + '" fill="url(#g-shadow)" opacity=".8"/>';
    f += box(-0.6, -0.6, -0.45, maxX + 1.2, maxY + 1.2, 0.45, 'url(#g-plate)', C.navy2, C.deep, C.line);
    var a, b;
    for (var i = 0; i <= maxX; i++) { a = P(i, -0.6); b = P(i, maxY + 0.6); f += '<line x1="' + f1(a[0]) + '" y1="' + f1(a[1]) + '" x2="' + f1(b[0]) + '" y2="' + f1(b[1]) + '" stroke="' + C.navy2 + '" stroke-width=".6"/>'; }
    for (var j = 0; j <= maxY; j++) { a = P(-0.6, j); b = P(maxX + 0.6, j); f += '<line x1="' + f1(a[0]) + '" y1="' + f1(a[1]) + '" x2="' + f1(b[0]) + '" y2="' + f1(b[1]) + '" stroke="' + C.navy2 + '" stroke-width=".6"/>'; }
    var corners = [P(-0.6, -0.6, 0), P(maxX + 0.6, -0.6, 0), P(maxX + 0.6, maxY + 0.6, -0.45), P(-0.6, maxY + 0.6, -0.45)];
    this.plateRect = {
      x: Math.min.apply(null, corners.map(function (q) { return q[0]; })), y: Math.min.apply(null, corners.map(function (q) { return q[1]; })),
      x2: Math.max.apply(null, corners.map(function (q) { return q[0]; })), y2: Math.max.apply(null, corners.map(function (q) { return q[1]; }))
    };
    var e1 = P(-0.6, maxY + 0.6), e2 = P(maxX + 0.6, maxY + 0.6), e3 = P(maxX + 0.6, -0.6);
    f += '<polyline points="' + pts([e1, e2, e3]) + '" fill="none" stroke="' + C.cyan + '" stroke-width="1" opacity=".35"/>';
    this.paths = {};
    Object.keys(cells).forEach(function (k) {
      if (k === 'hub' || k === 'lot') return;
      var p = route(all, cells[k], HUB);
      if (!p) return;
      self.paths[k] = p;
      var sp = p.map(function (q) { return P(q[0], q[1], 0.03); });
      f += '<polyline points="' + pts(sp) + '" fill="none" stroke="' + C.line3 + '" stroke-width="5" stroke-linejoin="round" stroke-linecap="round"/>';
      f += '<polyline class="flow" data-path="' + k + '" points="' + pts(sp) + '" fill="none" stroke="' + C.cyan + '" stroke-width="1.2" stroke-linejoin="round"/>';
    });
    this.gFloor.innerHTML = f;

    // rooms, back to front
    var order = Object.keys(cells).sort(function (p, q) {
      var A = cells[p], B = cells[q];
      return (A[0] + A[1]) - (B[0] + B[1]) || A[0] - B[0];
    });
    this.gRooms.innerHTML = order.map(function (k) {
      var c = cells[k], x0 = c[0], y0 = c[1], inner;
      if (k === 'hub') inner = self.hubRoom(x0, y0);
      else if (k === 'you') inner = self.ownerRoom(x0, y0);
      else if (k === 'audit') inner = self.auditRoom(x0, y0);
      else if (k === 'lot') inner = self.lotRoom(x0, y0);
      else inner = self.deptRoom(CO.dept(+k.slice(1)), x0, y0);
      var cls = 'room' + (k === 'lot' ? ' lot' : '') + (born && k === 'd' + born ? ' born' : '');
      return '<g class="' + cls + '" data-key="' + k + '">' + inner + '</g>';
    }).join('');
    this.walkers = {};
    this.update();
    if (!this.fitted) { this.fit(false); this.fitted = true; }
  };

  Office.prototype.deptRoom = function (d, x0, y0) {
    var out = shell(x0, y0, 'room');
    var k = d.key, u1 = 6.2;
    if (k === 'trading_desk') { u1 = 4.2; out += candles(x0, y0, 4.4, 6.75); }
    else if (k === 'design') { u1 = 4.6; out += mood(x0, y0, 4.8, 6.75); }
    else if (k === 'development' || k === 'testing' || k === 'testing_lab') u1 = 5.4;
    out += '<g class="scr" data-u1="' + u1 + '"></g><g class="kb"></g>';
    if (k === 'development') out += racks(x0 + 5.7, y0 + 0.25, 2);
    else if (k === 'testing') out += devices(x0 + 5.65, y0 + 0.28);
    else if (k === 'testing_lab') out += flasks(x0 + 5.5, y0 + 0.3);
    else if (k === 'custom') out += whiteboard(x0 + 5.6, y0 + 0.2);
    var ex = d.experts.slice(0, 3), xs = ex.length === 1 ? [2.55] : ex.length === 2 ? [1.0, 3.75] : [0.55, 2.6, 4.65];
    var key = 'd' + d.id;
    ex.forEach(function (e, i) { out += desk(x0 + xs[i], y0 + 1.75, i); });
    ex.forEach(function (e, i) { out += agentAt(x0 + xs[i] + 0.95, y0 + 3.05, key, i, CO.expertName(e)); });
    out += plant(x0 + 0.3, y0 + 6.2);
    return out;
  };
  Office.prototype.hubRoom = function (x0, y0) {
    var out = shell(x0, y0, 'hub');
    out += '<g class="scr hubscr"></g><g class="kb"></g>';
    out += racks(x0 + 0.45, y0 + 0.3, 3);
    var cx = P(11.6, 11.4, 0.1), rx = 1.2247 * 1.55 * SC, ry = 0.7071 * 1.55 * SC, tz = 0.45 * SC;
    out += '<ellipse cx="' + f1(cx[0]) + '" cy="' + f1(cx[1]) + '" rx="' + f1(rx * 1.5) + '" ry="' + f1(ry * 1.5) + '" fill="url(#g-fglow)"/>';
    out += '<ellipse cx="' + f1(cx[0]) + '" cy="' + f1(cx[1]) + '" rx="' + f1(rx) + '" ry="' + f1(ry) + '" fill="' + C.deep + '" opacity=".6"/>';
    out += '<path d="M' + f1(cx[0] - rx) + ',' + f1(cx[1] - tz) + ' L' + f1(cx[0] - rx) + ',' + f1(cx[1]) + ' A' + f1(rx) + ',' + f1(ry) + ' 0 0 0 ' +
      f1(cx[0] + rx) + ',' + f1(cx[1]) + ' L' + f1(cx[0] + rx) + ',' + f1(cx[1] - tz) + ' Z" fill="' + C.navy2 + '" stroke="' + C.line2 + '"/>';
    out += '<ellipse cx="' + f1(cx[0]) + '" cy="' + f1(cx[1] - tz) + '" rx="' + f1(rx) + '" ry="' + f1(ry) + '" fill="' + C.line3 + '" stroke="' + C.cyan + '" stroke-width=".9"/>';
    out += '<ellipse class="holo-core" cx="' + f1(cx[0]) + '" cy="' + f1(cx[1] - tz) + '" rx="' + f1(rx * 0.55) + '" ry="' + f1(ry * 0.55) + '" fill="url(#g-halo-c)" opacity=".5"/>';
    out += '<rect class="beam" x="' + f1(cx[0] - 10) + '" y="' + f1(cx[1] - tz - 70) + '" width="20" height="70" fill="url(#g-beam)"/>';
    [26, 42, 58].forEach(function (z, k) {
      out += '<ellipse class="holo h' + k + '" cx="' + f1(cx[0]) + '" cy="' + f1(cx[1] - tz - z) + '" rx="' + f1(rx * (0.75 - k * 0.15)) + '" ry="' + f1(ry * (0.75 - k * 0.15)) +
        '" fill="none" stroke="' + C.cyan + '" stroke-width="1.1" opacity="' + (0.8 - k * 0.2).toFixed(2) + '"/>';
    });
    for (var i = 0; i < 7; i++) {
      out += '<circle class="mote" cx="' + f1(cx[0] - 8 + (i * 37 % 17)) + '" cy="' + f1(cx[1] - tz - 4) + '" r="' + (0.8 + (i % 3) * 0.3) + '" fill="' + C.cyan + '" style="animation-delay:' + (-i * 0.55).toFixed(2) + 's"/>';
    }
    this.hubTop = [cx[0], cx[1] - tz];
    out += agentAt(11.7, 13.9, 'hub', 0, 'Manager', C.text);
    out += plant(x0 + 6.3, y0 + 0.4);
    return out;
  };
  Office.prototype.ownerRoom = function (x0, y0) {
    var out = shell(x0, y0, 'you');
    out += '<g class="scr"></g>';
    out += desk(x0 + 2.4, y0 + 1.8, 0, C.blue);
    out += '<g class="badge"></g>';
    out += agentAt(x0 + 3.35, y0 + 3.1, 'you', 0, 'You', C.text);
    out += box(x0 + 5.6, y0 + 0.35, 0.1, 1.0, 0.5, 0.35, C.line3, C.line2, C.navy2, C.line);   // sofa
    out += box(x0 + 5.6, y0 + 0.25, 0.1, 1.0, 0.12, 0.7, C.line3, C.line2, C.navy2, C.line);
    out += plant(x0 + 0.3, y0 + 6.2);
    return out;
  };
  Office.prototype.auditRoom = function (x0, y0) {
    var out = shell(x0, y0, 'audit');
    out += '<g class="scr"></g>';
    out += desk(x0 + 2.2, y0 + 1.8, 0, C.line2);
    out += agentAt(x0 + 3.15, y0 + 3.1, 'audit', 0, 'Supervisor');
    var c = P(x0 + 5.8, y0 + 1.4, 0.1);
    out += '<ellipse cx="' + f1(c[0]) + '" cy="' + f1(c[1]) + '" rx="16" ry="7" fill="none" stroke="' + C.blue + '" stroke-width="1" opacity=".6"/>';
    out += '<ellipse class="scan" cx="' + f1(c[0]) + '" cy="' + f1(c[1]) + '" rx="16" ry="7" fill="none" stroke="' + C.cyan + '" stroke-width="1.2"/>';
    out += plant(x0 + 0.3, y0 + 6.2);
    return out;
  };
  Office.prototype.lotRoom = function (x0, y0) {
    var out = shell(x0, y0, 'lot');
    var c = P(x0 + 3.5, y0 + 3.5, 0.1);
    out += '<circle class="lotc" cx="' + f1(c[0]) + '" cy="' + f1(c[1] - 6) + '" r="15" fill="' + C.deep + '" stroke="' + C.cyan + '" stroke-width="1.3"/>';
    out += text(c[0], c[1] + 0.2, '+', 20, C.cyan, 400, 'middle', 'display');
    out += text(c[0], c[1] + 23, 'ADD DEPARTMENT', 8.8, C.cyan, 700, 'middle');
    return out;
  };

  /* ---------------- update in place ---------------- */
  Office.prototype.update = function () {
    var S = CO.S, self = this;
    if (this.shape() !== this.shapeKey) return this.layout();
    var over = '', cells = this.cells, ex = function (k) { return self.gRooms.querySelector('[data-key="' + k + '"]'); };
    var turnsBy = {};
    S.strip.forEach(function (c) { turnsBy[c.dept_id] = (turnsBy[c.dept_id] || 0) + 1; });
    var anyWork = false;
    S.departments.forEach(function (d) {
      var g = ex('d' + d.id); if (!g) return;
      var v = CO.deptView(d), x0 = cells['d' + d.id][0], y0 = cells['d' + d.id][1];
      if (v.status === 'working') anyWork = true;
      g.setAttribute('class', 'room st-' + v.status + (self.sel === 'd' + d.id ? ' sel' : '') + (g.classList.contains('born') ? ' born' : '') + (g.classList.contains('hover') ? ' hover' : ''));
      var col = ST[v.status], title, sub, mode;
      if (v.running) { title = v.running.title; sub = 'attempt ' + v.running.attempt + ' of 3 · ' + CO.expertName(v.running.expert); mode = 'run'; }
      else if (v.queued.length) { title = 'Next: ' + v.queued[0].title; sub = 'Queued: ' + v.waits; mode = ''; }
      else if (v.waiting) { title = v.waiting + ' wait' + (v.waiting > 1 ? '' : 's') + ' for you'; sub = 'approve or reject on the right'; mode = 'full'; col = C.red; }
      else { title = 'Idle'; sub = v.done + ' done · nothing queued'; mode = ''; }
      var scr = g.querySelector('.scr');
      scr.innerHTML = wallScreen(x0, y0, 1.1, +scr.getAttribute('data-u1'), title, sub, col, mode);
      var kc = { queued: v.queued.length, running: v.running ? 1 : 0, done: v.done, failed: v.failed };
      g.querySelector('.kb').innerHTML = kanban(x0, y0, kc);
      v.experts.slice(0, 3).forEach(function (e, i) {
        Array.prototype.forEach.call(g.querySelectorAll('[data-i="' + i + '"]'), function (m) { m.classList.toggle('on', e.state === 'working'); });
        var ag = g.querySelector('.agent[data-agent="d' + d.id + ':' + i + '"]');
        if (ag) { ag.classList.toggle('working', e.state === 'working'); ag.classList.toggle('idle', e.state !== 'working'); }
      });
      var c = P(x0 + 4.6, y0 + 5.55, 0.1);
      var l2 = [[v.open + ' open', C.cyan], [v.done + ' done', C.green]];
      if (v.failed) l2.push([v.failed + ' failed', C.red]);
      over += plate(c[0], c[1], d.name.toUpperCase(), col, l2, Math.max(150, d.name.length * 10.5 + 34), 'd' + d.id, v.status === 'working');
    });
    // the Manager's room
    var hub = ex('hub');
    if (hub) {
      var cnt = CO.counts();
      hub.setAttribute('class', 'room st-working' + (self.sel === 'hub' ? ' sel' : ''));
      var bars = S.departments.map(function (d) { var v = CO.deptView(d); return [ST[v.status] === C.dim2 ? C.blue : ST[v.status], turnsBy[d.id] || 0]; });
      hub.querySelector('.scr').innerHTML = barsScreen(8, 8, 3.0, 6.4, 'TURNS BY DEPT TODAY', bars);
      var pc = { queued: S.plan.length, running: S.tasks.filter(function (t) { return t.status === 'running'; }).length,
        done: S.strip.filter(function (c) { return c.state === 'done'; }).length, failed: S.strip.filter(function (c) { return c.state === 'failed'; }).length };
      hub.querySelector('.kb').innerHTML = kanban(8, 8, pc);
      var mg = hub.querySelector('.agent');
      if (mg) { mg.classList.toggle('working', S.company.status === 'active'); mg.classList.toggle('idle', S.company.status !== 'active'); }
      var ht = this.hubTop;
      if (ht) {
        over += '<g class="plate" data-key="hub"><rect x="' + f1(ht[0] - 56) + '" y="' + f1(ht[1] - 108) + '" width="112" height="32" rx="7" fill="' + C.bg + '" stroke="' + C.cyan + '" stroke-width=".9" opacity=".95"/>' +
          text(ht[0], ht[1] - 88.5, cnt.open + ' OPEN', 13, C.cyan, 400, 'middle', 'display') +
          text(ht[0], ht[1] - 80, S.approvals.length ? S.approvals.length + ' wait for you' : 'nothing waits for you', 7.6, S.approvals.length ? C.red : C.dim2, 600, 'middle') + '</g>';
      }
      var mp = P(12.9, 14.25, 0.1);
      over += plate(mp[0] + 30, mp[1] + 8, 'MANAGER', S.company.status === 'active' ? C.cyan : C.dim2,
        [['routes ' + cnt.open, C.cyan], [S.approvals.length + ' for you', S.approvals.length ? C.red : C.dim2]], 150, 'hub', S.company.status === 'active' && anyWork);
    }
    // the owner's desk
    var you = ex('you');
    if (you) {
      var n = S.approvals.length;
      you.setAttribute('class', 'room ' + (n ? 'st-waiting' : 'st-idle') + (self.sel === 'you' ? ' sel' : ''));
      you.querySelector('.scr').innerHTML = wallScreen(8, 16, 1.1, 6.2, n ? n + ' approval' + (n > 1 ? 's' : '') + ' waiting' : 'Nothing waits for you',
        n ? 'oldest ' + CO.ago(S.approvals[S.approvals.length - 1].created_at) : 'the Manager asks before anything real', n ? C.red : C.dim2, n ? 'full' : '');
      var bp = P(8 + 4.15, 16 + 2.15, 0.6);
      you.querySelector('.badge').innerHTML = n ? box(8 + 3.95, 16 + 1.95, 0.42, 0.42, 0.42, 0.14, C.red, C.navy2, C.navy) +
        '<circle class="bdg" cx="' + f1(bp[0]) + '" cy="' + f1(bp[1] - 12) + '" r="8.5" fill="' + C.red + '" filter="url(#glow)"/>' +
        text(bp[0], bp[1] - 8.4, String(n), 10.5, C.bg, 700, 'middle', 'display') : '';
      var yp = P(8 + 4.6, 16 + 5.55, 0.1);
      over += plate(yp[0], yp[1], 'YOU', n ? C.red : C.blue, [[n ? n + ' to approve' : 'all clear', n ? C.red : C.green]], 140, 'you', false);
    }
    var au = ex('audit');
    if (au) {
      var A = S.audit, days = Math.max(0, Math.ceil((A.next_at - S.clock) / 86400000)), nf = A.last ? A.last.findings.length : 0;
      au.setAttribute('class', 'room st-idle' + (self.sel === 'audit' ? ' sel' : ''));
      au.querySelector('.scr').innerHTML = wallScreen(0, 16, 1.1, 5.0, 'Weekly audit: next in ' + days + 'd', nf + ' findings last week', C.dim2, '');
      var ap = P(0 + 4.6, 16 + 5.55, 0.1);
      over += plate(ap[0], ap[1], 'WEEKLY AUDIT', C.dim2, [['next ' + days + 'd', C.dim], [nf + ' findings', nf ? C.cyan : C.green]], 150, 'audit', false);
    }
    // the selection ring
    if (this.sel && cells[this.sel]) {
      var s = cells[this.sel];
      over += poly([P(s[0] - 0.15, s[1] - 0.15, 0.12), P(s[0] + 7.15, s[1] - 0.15, 0.12), P(s[0] + 7.15, s[1] + 7.15, 0.12), P(s[0] - 0.15, s[1] + 7.15, 0.12)],
        'none', C.cyan, 2.4, 1, ' class="selring" filter="url(#glow)"');
    }
    this.gOver.innerHTML = over;
    // conduits run fast to working rooms
    Array.prototype.forEach.call(this.gFloor.querySelectorAll('.flow'), function (pl) {
      var k = pl.getAttribute('data-path'), d = k.charAt(0) === 'd' ? CO.dept(+k.slice(1)) : null;
      pl.classList.toggle('hot', !!(d && CO.deptView(d).status === 'working'));
    });
    this.svg.classList.toggle('paused', S.company.status === 'paused');
  };

  /* ---------------- packets ---------------- */
  Office.prototype.packet = function (from, to, colour, delay) {
    var p;
    if (from === 'hub' && this.paths[to]) p = this.paths[to].slice().reverse();
    else if (to === 'hub' && this.paths[from]) p = this.paths[from].slice();
    else if (this.paths[from] && this.paths[to]) p = this.paths[from].concat(this.paths[to].slice().reverse().slice(1));
    if (!p) return;
    var id = { cyan: 'g-halo-c', green: 'g-halo-g', red: 'g-halo-r', blue: 'g-halo-b' }[colour] || 'g-halo-c';
    var hex = { cyan: C.cyan, green: C.green, red: C.red, blue: C.blue }[colour] || C.cyan;
    var g = document.createElementNS(NS, 'g');
    g.setAttribute('class', 'pk');
    var html = '';
    for (var i = 4; i >= 1; i--) html += '<circle class="tr" r="' + (2.6 - i * 0.4).toFixed(1) + '" fill="' + hex + '" opacity="' + (0.5 - i * 0.1).toFixed(2) + '"/>';
    html += '<circle r="10" fill="url(#' + id + ')"/><circle r="2.8" fill="' + hex + '"/><circle r="1.2" fill="' + C.text + '" opacity=".8"/>';
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
    var idle = Array.prototype.filter.call(this.gRooms.querySelectorAll('.agent.idle'), function (a) {
      return !a.classList.contains('walking') && a.getAttribute('data-agent').indexOf('you') !== 0;
    });
    if (!idle.length || Object.keys(this.walkers).length >= 3 || Math.random() < 0.35) return;
    var el = idle[Math.floor(Math.random() * idle.length)], id = el.getAttribute('data-agent');
    var key = id.split(':')[0], c = this.cells[key]; if (!c) return;
    var spots = key === 'hub' ? [[10.2, 13.6], [13.4, 13.0], [9.6, 11.0]] : [[c[0] + 0.9, c[1] + 4.0], [c[0] + 2.9, c[1] + 4.7], [c[0] + 1.6, c[1] + 3.6], [c[0] + 5.2, c[1] + 3.5]];
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
      if (f < 1) requestAnimationFrame(step);
    })(t0);
  };
  // what is drawn, without the soft shadow under the plate
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
  Office.prototype.focus = function (key, leftPx) {
    var c = this.cells[key]; if (!c) return;
    var cl = this.client(), mid = P(c[0] + 3.5, c[1] + 3.5, 0.6);
    var visW = cl.w - (leftPx || 0), w = Math.min(this.vb.w, Math.max(420, RS * SC * 2.6 * cl.w / Math.max(200, visW)));
    var h = w * cl.h / cl.w, fx = ((leftPx || 0) + visW / 2) / cl.w;
    this.tween({ x: mid[0] - w * fx, y: mid[1] - h * 0.5, w: w, h: h }, 520);
  };
  Office.prototype.resize = function () {
    var c = this.client(), v = this.vb;
    if (!this.fitted) return;
    var cx = v.x + v.w / 2, cy = v.y + v.h / 2, nh = v.w * c.h / c.w;
    this.vb = { x: v.x, y: cy - nh / 2, w: v.w, h: nh };
    this.apply();
  };
  Office.prototype.select = function (key) { this.sel = key; this.update(); };

  /* ---------------- input ---------------- */
  Office.prototype.bind = function () {
    var self = this, svg = this.svg, drag = null;
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
  };
  Office.prototype.hoverAt = function (e) {
    var ag = e.target.closest('.agent'), rm = e.target.closest('[data-key]');
    this.setHover(rm ? rm.getAttribute('data-key') : null);
    var html = ag ? this.tipFor('agent', ag.getAttribute('data-agent')) : rm ? this.tipFor('room', rm.getAttribute('data-key')) : '';
    if (!html) return this.hideTip();
    var r = this.stage.getBoundingClientRect();
    this.tip.innerHTML = html; this.tip.hidden = false;
    var x = e.clientX - r.left + 14, y = e.clientY - r.top + 14;
    if (x + this.tip.offsetWidth > r.width - 8) x = e.clientX - r.left - this.tip.offsetWidth - 14;
    if (y + this.tip.offsetHeight > r.height - 8) y = e.clientY - r.top - this.tip.offsetHeight - 14;
    this.tip.style.left = x + 'px'; this.tip.style.top = y + 'px';
  };
  Office.prototype.hideTip = function () { if (this.tip) this.tip.hidden = true; };
})();
