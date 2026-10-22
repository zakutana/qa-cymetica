/* Promo Market mockup. Three pages: the market (/creator-dashboard, anyone), the creator's own dashboard (/<username>,
 * logged in: Today, Briefs, Queues, Pages & links, Rewards) and a creator's public page. Plus the brief drawer, the
 * "Post a brief" form, Create a page, Track a link and the agent prompts. Every figure comes from window.PM (data.js);
 * the briefs are the one new thing and come from make_data.py's model. Numbers first; an explanation is a tooltip. */
(function () {
  'use strict';
  var PM = window.PM, DAY = PM.day;
  var $ = function (id) { return document.getElementById(id); };

  /* ---------------- helpers ---------------- */
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function fmt(n) { return n == null ? '—' : Math.round(n).toLocaleString('en-US'); }
  function short(n) { return n >= 1e6 ? (n / 1e6).toFixed(n >= 1e7 ? 0 : 1) + 'M' : n >= 1e4 ? Math.round(n / 1e3) + 'K' : fmt(n); }
  function sum(a, f) { return a.reduce(function (s, x) { return s + f(x); }, 0); }
  function addDays(d, n) { var t = new Date(d + 'T12:00:00Z'); t.setUTCDate(t.getUTCDate() + n); return t; }
  function dShort(t) { return t.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' }); }
  function slugOf(s) { var h = 2166136261, o = '', a = 'abcdefghijkmnpqrstuvwxyz23456789'; for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); }
    for (var j = 0; j < 8; j++) { o += a[(h >>> 0) % a.length]; h = Math.imul(h ^ (h >>> 13), 2246822507); } return o; }

  var I = {
    x: '<path d="M4 3.5h3.2l8.8 13H12.8z M15.6 3.5 4.6 16.5"/>',
    reddit: '<circle cx="10" cy="11.6" r="5.4"/><circle cx="14.9" cy="4.3" r="1.3"/><path d="M10 6.2V3.5l3.6.8"/><circle cx="8" cy="11.2" r=".7" fill="currentColor"/><circle cx="12" cy="11.2" r=".7" fill="currentColor"/><path d="M8 13.7c1.2.8 2.8.8 4 0"/>',
    telegram: '<path d="M2.8 9.4 17 3.6l-2.4 12.6-4.6-3.6-2.4 2.3.3-3.7 6.6-6-8.2 4.9z"/>',
    discord: '<path d="M6.2 5.2c2.6-.9 5-.9 7.6 0 1.5 2.2 2.3 4.6 2.4 7.4-1.2 1-2.6 1.7-4 2l-.9-1.5m-3.6 0-.9 1.5c-1.4-.3-2.8-1-4-2 .1-2.8.9-5.2 2.4-7.4"/><circle cx="7.8" cy="10.6" r="1.1"/><circle cx="12.2" cy="10.6" r="1.1"/>',
    press: '<rect x="3" y="4" width="11" height="12.5" rx="1.5"/><path d="M14 7.5h2.5v7.5a1.5 1.5 0 0 1-3 0 M5.5 7h6 M5.5 10h6 M5.5 13h4"/>',
    clicks: '<path d="M5 3.5l10 5-4.2 1.2L9 14z M11 10.5l3.5 3.5"/>',
    reads: '<path d="M2.5 10s2.8-5 7.5-5 7.5 5 7.5 5-2.8 5-7.5 5-7.5-5-7.5-5z"/><circle cx="10" cy="10" r="2.2"/>',
    likes: '<path d="M10 16s-6-3.6-6-8a3.3 3.3 0 0 1 6-1.9A3.3 3.3 0 0 1 16 8c0 4.4-6 8-6 8z"/>',
    uniq: '<circle cx="10" cy="7" r="3"/><path d="M4 16.5c.8-3 3.2-4.5 6-4.5s5.2 1.5 6 4.5"/>',
    link: '<path d="M8.5 11.5a3 3 0 0 0 4.2 0l2.6-2.6a3 3 0 0 0-4.2-4.2l-1 1 M11.5 8.5a3 3 0 0 0-4.2 0l-2.6 2.6a3 3 0 0 0 4.2 4.2l1-1"/>',
    today: '<path d="M11 2.5 4.5 11H10l-1 6.5L15.5 9H10z"/>',
    briefs: '<circle cx="10" cy="10" r="6.5"/><circle cx="10" cy="10" r="3.5"/><circle cx="10" cy="10" r=".8" fill="currentColor"/>',
    queues: '<path d="M3 11.5 5 4.5h10l2 7v4H3z M3 11.5h4l1 2h4l1-2h4"/>',
    pages: '<path d="M5 2.5h6.5L15 6v11.5H5z M11.5 2.5V6H15 M7.5 10h5 M7.5 13h5"/>',
    coin: '<circle cx="10" cy="10" r="6.5"/><path d="M10 5.8v8.4 M12.3 7.6c-.5-.7-1.3-1-2.3-1-1.4 0-2.4.7-2.4 1.7 0 2.4 4.8 1.2 4.8 3.6 0 1-1 1.8-2.4 1.8-1.1 0-2-.4-2.5-1.2"/>',
    check: '<path d="M4.5 10.5 8.3 14l7.2-8"/>',
    plus: '<path d="M10 4v12 M4 10h12"/>',
    copy: '<rect x="7" y="7" width="9.5" height="9.5" rx="2"/><path d="M13 7V5a1.5 1.5 0 0 0-1.5-1.5h-6A1.5 1.5 0 0 0 4 5v6.5A1.5 1.5 0 0 0 5.5 13H7"/>',
    ext: '<path d="M8.5 4.5H4.5v11h11v-4 M11.5 3.5h5v5 M16.5 3.5 9 11"/>',
    close: '<path d="M5 5l10 10 M15 5 5 15"/>',
    arrow: '<path d="M4 10h12 M11 5l5 5-5 5"/>',
    chev: '<path d="M7.5 5l5 5-5 5"/>',
    down: '<path d="M5 7.5l5 5 5-5"/>',
    clock: '<circle cx="10" cy="10" r="6.5"/><path d="M10 6.5V10l2.5 1.8"/>',
    agent: '<rect x="5" y="5" width="10" height="10" rx="2"/><rect x="8" y="8" width="4" height="4" rx=".8"/><path d="M8 2.5V5 M12 2.5V5 M8 15v2.5 M12 15v2.5 M2.5 8H5 M2.5 12H5 M15 8h2.5 M15 12h2.5"/>',
    company: '<path d="M3.5 17V7.5l6.5-4 6.5 4V17 M3 17h14 M8 17v-4h4v4"/>',
    search: '<circle cx="8.8" cy="8.8" r="5.3"/><path d="M12.8 12.8 16.5 16.5"/>',
    lock: '<rect x="4.5" y="9" width="11" height="8" rx="1.8"/><path d="M7 9V6.8a3 3 0 0 1 6 0V9"/>',
    shield: '<path d="M10 2.8 4.5 5v4.6c0 3.6 2.4 6 5.5 7.6 3.1-1.6 5.5-4 5.5-7.6V5z M7.5 10l1.8 1.8 3.4-3.6"/>',
    radar: '<circle cx="10" cy="10" r="6.5"/><circle cx="10" cy="10" r="3.2"/><path d="M10 10l4.6-4.6"/>',
    reply: '<path d="M8 5 3.5 9.5 8 14 M3.5 9.5H11a5.5 5.5 0 0 1 5.5 5.5v1"/>',
    skip: '<path d="M5 5l6 5-6 5z M14 5v10"/>',
    youtube: '<rect x="2.5" y="5" width="15" height="10.5" rx="3"/><path d="M8.5 7.9v4.7l4-2.35z" fill="currentColor"/>',
    mail: '<rect x="3" y="5" width="14" height="10.5" rx="1.8"/><path d="M3.5 6l6.5 5 6.5-5"/>'
  };
  function ic(k, cls) { return '<svg' + (cls ? ' class="' + cls + '"' : '') + ' viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (I[k] || '') + '</svg>'; }
  var OUT = { x: 'X', reddit: 'Reddit', telegram: 'Telegram', discord: 'Discord', press: 'Press', youtube: 'YouTube' };

  function toast(msg) {
    var t = $('toast'); t.innerHTML = ic('check') + esc(msg); t.classList.add('on');
    clearTimeout(toast.h); toast.h = setTimeout(function () { t.classList.remove('on'); }, 2200);
  }
  function copy(text, what) { try { navigator.clipboard.writeText(text); } catch (e) { /* the mock still says so */ } toast((what || 'Copied') + ' · copied'); }

  /* ---------------- state ---------------- */
  var S = {
    briefs: PM.market.briefs.slice(),
    mine: PM.market.mine.slice(),
    taken: { chart: { slug: slugOf('chart'), at: '2026-10-21' } },  // a brief this creator took yesterday: "Briefs I took"'s sample
    sort: 'left', qtab: 'reddit', qsel: {}, radar: 0, open: {}, pgSort: 'uniq', pgQ: ''
  };
  function stats() {
    var b = S.briefs;
    return { left: sum(b, function (x) { return x.left; }), n: b.length,
      top: b.slice().sort(function (p, q) { return q.per_user - p.per_user; })[0] };
  }
  function briefOf(key) { return S.briefs.filter(function (x) { return x.key === key; })[0]; }
  function productOf(key) { return S.mine.filter(function (x) { return x.key === key; })[0]; }
  function usd(n) { return fmt(n) + ' USDC'; }

  /* ---------------- charts ---------------- */
  function bars(days, tot, h) {
    var W = 520, H = h || 92, n = tot.length, bw = W / n, max = Math.max.apply(null, tot.map(function (d) { return d[0] + d[1] + d[2]; })) || 1, o = '';
    tot.forEach(function (d, i) {
      var x = i * bw + bw * 0.18, w = bw * 0.64, y = H - 14, parts = [[d[1], '#00cfff'], [d[0], '#00ff88'], [d[2], '#3b82f6']];
      parts.forEach(function (p) { var hh = p[0] / max * (H - 22); if (hh > 0) { y -= hh; o += '<rect x="' + x.toFixed(1) + '" y="' + y.toFixed(1) + '" width="' + w.toFixed(1) + '" height="' + hh.toFixed(1) + '" rx="2" fill="' + p[1] + '" opacity=".9"/>'; } });
    });
    var lab = function (i) { return '<span>' + dShort(new Date(days[i] + 'T12:00:00Z')) + '</span>'; };
    return '<svg viewBox="0 0 ' + W + ' ' + (H - 14) + '" preserveAspectRatio="none">' + o + '</svg><div class="dl">' + lab(0) + lab(n - 1) + '</div>';
  }
  function spark(series) {
    var v = series.map(function (d) { return d[0] + d[1]; }), W = 120, H = 28, max = Math.max.apply(null, v) || 1, n = v.length;
    var pts = v.map(function (y, i) { return (i * (W - 2) / (n - 1) + 1).toFixed(1) + ',' + (H - 3 - y / max * (H - 7)).toFixed(1); });
    var col = v.some(function (x) { return x > 0; }) ? '#00cfff' : '#1e3050';
    return '<svg class="spark" viewBox="0 0 ' + W + ' ' + H + '"><polygon points="1,' + (H - 2) + ' ' + pts.join(' ') + ' ' + (W - 1) + ',' + (H - 2) + '" fill="rgba(0,207,255,.10)"/>' +
      '<polyline points="' + pts.join(' ') + '" fill="none" stroke="' + col + '" stroke-width="1.6" stroke-linejoin="round"/></svg>';
  }

  /* ---------------- each product's picture: drawn here, in the palette (the products' own og images were slow, one
     answered 502 and one carries another title, 2026-10-22) ---------------- */
  var GLYPH = {
    gem: '<path d="M6 3.5h8l3 4-7 9-7-9z M3 7.5h14 M8 3.5 7 7.5l3 9 3-9-1-4"/>',
    casino: '<circle cx="10" cy="10" r="6.5"/><circle cx="10" cy="10" r="3"/><path d="M10 3.5v2 M10 14.5v2 M3.5 10h2 M14.5 10h2 M5.4 5.4l1.4 1.4 M13.2 13.2l1.4 1.4 M5.4 14.6l1.4-1.4 M13.2 6.8l1.4-1.4"/>',
    chart: '<path d="M5 4v12 M10 3v14 M15 5v9"/><rect x="3.5" y="7" width="3" height="5" rx=".6"/><rect x="8.5" y="5" width="3" height="7" rx=".6"/><rect x="13.5" y="8" width="3" height="4" rx=".6"/>',
    supply: '<circle cx="10" cy="10" r="6.5"/><path d="M10 3.5V10l5.6 3.2"/>',
    company: I.company, launch: I.shield,
    nexus: '<path d="M4 5.5h12v7H9.5L6 15.5v-3H4z"/><circle cx="8" cy="9" r=".7" fill="currentColor"/><circle cx="12" cy="9" r=".7" fill="currentColor"/>',
    team: I.radar, infil: I.reads, agents: I.agent
  };
  // which of the six motifs each picture uses
  var MOTIF = { nexus: 'supply', team: 'chart', infil: 'company', agents: 'casino' };
  var HUE = { gem: ['#00ff88', '#00cfff'], casino: ['#00cfff', '#00ff88'], chart: ['#00ff88', '#ff4444'], supply: ['#3b82f6', '#00cfff'], company: ['#00cfff', '#3b82f6'], launch: ['#00ff88', '#00cfff'],
    nexus: ['#00cfff', '#00ff88'], team: ['#3b82f6', '#ff4444'], infil: ['#3b82f6', '#00cfff'], agents: ['#00ff88', '#3b82f6'] };
  function art(b) {
    var g = HUE[b.art || b.key] ? (b.art || b.key) : 'gem', k = MOTIF[g] || g, c = HUE[g], id = 'g' + g + Math.random().toString(36).slice(2, 7), m = '', i, x, y;
    var grid = ''; for (x = 12; x < 360; x += 24) grid += 'M' + x + ' 0V150 '; for (y = 6; y < 150; y += 24) grid += 'M0 ' + y + 'H360 ';
    if (k === 'gem') [26, 40, 34, 58, 47, 72, 64, 88, 79, 104, 96, 118].forEach(function (h, j) { m += '<rect x="' + (186 + j * 13.5) + '" y="' + (138 - h) + '" width="9" height="' + h + '" rx="2" fill="url(#' + id + 'v)" opacity="' + (0.35 + j * 0.055).toFixed(2) + '"/>'; });
    if (k === 'casino') for (i = 0; i < 4; i++) for (var j2 = 0; j2 < 5; j2++) { x = 200 + j2 * 30 + (i % 2) * 15; y = 22 + i * 30; var f = (i * 5 + j2) % 4 === 1;
      m += '<path d="M' + x + ' ' + (y - 14) + 'l12 7v14l-12 7-12-7v-14z" fill="' + (f ? c[1] : 'none') + '" fill-opacity="' + (f ? 0.45 : 0) + '" stroke="' + c[0] + '" stroke-opacity=".55" stroke-width="1.2"/>'; }
    if (k === 'chart') [[40, 70, 1], [60, 30, 1], [84, 26, 0], [70, 40, 1], [96, 34, 1], [80, 26, 0], [108, 28, 1], [120, 22, 1], [104, 30, 0], [126, 24, 1]].forEach(function (d, j) {
      x = 212 + j * 14; var col = d[2] ? c[0] : c[1], top = 140 - Math.round(d[0] * 0.7) - d[1]; m += '<path d="M' + (x + 4) + ' ' + (top - 8) + 'V' + (top + d[1] + 8) + '" stroke="' + col + '" stroke-opacity=".7"/><rect x="' + x + '" y="' + top + '" width="8" height="' + d[1] + '" rx="1.5" fill="' + col + '" opacity=".8"/>'; });
    if (k === 'supply') { [70, 52, 34].forEach(function (r, j) { m += '<ellipse cx="272" cy="78" rx="' + r + '" ry="' + (r * 0.42) + '" fill="none" stroke="' + c[j % 2] + '" stroke-opacity=".5" transform="rotate(-14 272 78)"/>'; });
      [[205, 92], [236, 50], [318, 98], [300, 58], [262, 108], [338, 70]].forEach(function (p) { m += '<circle cx="' + p[0] + '" cy="' + p[1] + '" r="4" fill="' + c[1] + '"/><circle cx="' + p[0] + '" cy="' + p[1] + '" r="9" fill="' + c[1] + '" opacity=".15"/>'; });
      m += '<circle cx="272" cy="78" r="14" fill="url(#' + id + 'v)" opacity=".8"/>'; }
    if (k === 'company') { [[214, 70, 40, 68], [260, 40, 46, 98], [312, 86, 36, 52]].forEach(function (r) { m += '<rect x="' + r[0] + '" y="' + r[1] + '" width="' + r[2] + '" height="' + r[3] + '" rx="4" fill="' + c[1] + '" fill-opacity=".12" stroke="' + c[0] + '" stroke-opacity=".6"/>';
        for (var wy = r[1] + 10; wy < r[1] + r[3] - 8; wy += 12) for (var wx = r[0] + 8; wx < r[0] + r[2] - 6; wx += 10) m += '<rect x="' + wx + '" y="' + wy + '" width="5" height="4" rx="1" fill="' + c[0] + '" opacity="' + (((wx + wy) % 3) ? 0.25 : 0.8) + '"/>'; });
      m += '<path d="M283 40V18" stroke="' + c[0] + '"/><circle cx="283" cy="16" r="3" fill="' + c[0] + '"/>'; }
    if (k === 'launch') { m += '<path d="M272 18l44 16v34c0 30-20 48-44 60-24-12-44-30-44-60V34z" fill="' + c[0] + '" fill-opacity=".1" stroke="' + c[0] + '" stroke-opacity=".7" stroke-width="1.5"/><path d="M254 74l13 13 26-28" fill="none" stroke="' + c[0] + '" stroke-width="5" stroke-linecap="round" stroke-linejoin="round"/>';
      [40, 62, 84, 106].forEach(function (yy) { m += '<path d="M196 ' + yy + 'H350" stroke="' + c[1] + '" stroke-opacity=".18" stroke-dasharray="3 5"/>'; }); }
    return '<svg viewBox="0 0 360 150" preserveAspectRatio="xMidYMid slice" aria-hidden="true"><defs>' +
      '<linearGradient id="' + id + 'b" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="' + c[0] + '" stop-opacity=".16"/><stop offset=".6" stop-color="#0d1520" stop-opacity="0"/></linearGradient>' +
      '<linearGradient id="' + id + 'v" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="' + c[0] + '"/><stop offset="1" stop-color="' + c[1] + '"/></linearGradient>' +
      '<radialGradient id="' + id + 'r" cx=".78" cy=".45" r=".6"><stop offset="0" stop-color="' + c[1] + '" stop-opacity=".22"/><stop offset="1" stop-color="' + c[1] + '" stop-opacity="0"/></radialGradient></defs>' +
      '<rect width="360" height="150" fill="#0a0e17"/><rect width="360" height="150" fill="url(#' + id + 'b)"/><rect width="360" height="150" fill="url(#' + id + 'r)"/>' +
      '<path d="' + grid + '" stroke="#e6edf7" stroke-opacity=".035"/><g transform="translate(' + (k === 'gem' || k === 'casino' ? 14 : 0) + ' 0)">' + m + '</g>' +
      '<g transform="translate(22 22)"><rect width="46" height="46" rx="12" fill="#06090f" fill-opacity=".7" stroke="' + c[0] + '" stroke-opacity=".5"/>' +
      '<g transform="translate(11 11)" fill="none" stroke="' + c[0] + '" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><svg width="24" height="24" viewBox="0 0 20 20">' + (GLYPH[g] || '') + '</svg></g></g>' +
      '<text x="24" y="92" fill="#7f93ad" font-family="JetBrains Mono, monospace" font-size="10">cymetica.com' + esc(b.path || '') + '</text></svg>';
  }

  /* ---------------- pieces ---------------- */
  function daysChip(b) { return b.days <= 2 ? '<span class="chip r">' + ic('clock') + b.days + 'd left</span>' : '<span class="chip">' + ic('clock') + b.days + 'd left</span>'; }
  function lnk(path) { return '<a class="lnk" href="https://cymetica.com' + esc(path) + '" target="_blank" rel="noopener">cymetica.com' + esc(path) + ' ↗</a>'; }
  function pay2(b) {
    return '<div class="pay2"><div><b>' + fmt(b.per_post) + ' <small>USDC</small></b><span>per post</span></div>' +
      '<div><b>' + fmt(b.per_user) + ' <small>USDC</small></b><span>per new user</span></div></div>';
  }
  // a promoter's card: the product and its link, what is up for grabs, what one post and one new user pay. Nothing else.
  function briefCard(b) {
    var taken = S.taken[b.key];
    return '<article class="bc" data-brief="' + b.key + '">' +
      '<div class="img">' + art(b) + '<div class="dl">' + daysChip(b) + '</div></div>' +
      '<div class="bd"><div class="nm"><b>' + esc(b.name) + '</b>' + lnk(b.path) + '</div>' +
      '<div class="ufg"><span>Up for grabs</span><b>' + fmt(b.left) + ' <small>USDC</small></b></div>' + pay2(b) +
      (taken ? '<button class="btn gh full" data-brief="' + b.key + '">' + ic('check') + 'Taken · my link</button>' :
        '<button class="btn g full" data-take="' + b.key + '">Take it ' + ic('arrow') + '</button>') + '</div></article>';
  }
  function sortBriefs(list) {
    var f = { left: function (a, b) { return b.left - a.left; }, user: function (a, b) { return b.per_user - a.per_user; }, ending: function (a, b) { return a.days - b.days; } }[S.sort];
    return list.sort(f);
  }
  function boardHead(title) {
    return '<div class="bhead"><h2>' + title + '</h2><span class="cnt" id="bcnt"></span><span class="sp"></span>' +
      '<div class="seg" id="bsort">' + [['left', 'Most up for grabs'], ['user', 'Best per new user'], ['ending', 'Ending soon']].map(function (s) { return '<button data-s="' + s[0] + '" class="' + (S.sort === s[0] ? 'on' : '') + '">' + s[1] + '</button>'; }).join('') + '</div></div>';
  }
  function board() { var l = sortBriefs(S.briefs.slice()); return '<div class="grid" id="bgrid">' + l.map(briefCard).join('') + '</div>'; }
  function refreshBoard() { var g = $('bgrid'); if (!g) return; var l = sortBriefs(S.briefs.slice()); g.innerHTML = l.map(briefCard).join(''); var c = $('bcnt'); if (c) c.textContent = l.length; }
  // the six checks a new user passes before it is paid: kept out of the way, behind a fold
  function rules() {
    var r = [['uniq', 'A new person', 'A first account, first visit through your link, within 7 days.'],
      ['shield', 'One person, one user', 'Device, network, wallet and phone are matched across every user.'],
      ['today', 'Really uses it', 'Uses the product on 3 different days within 14.'],
      ['telegram', 'Proof of person', 'A Telegram account or a wallet with on-chain history.'],
      ['lock', 'Checked for 14 days', 'Paid after 14 days; clawed back if it turns out fake.'],
      ['coin', 'Promoters stake', 'AI agents and new promoters stake ET10; a farmed user burns it.']];
    return '<div class="cgrid">' + r.map(function (x) { return '<div class="chk"><span class="n">' + ic(x[0]) + '</span><div><b>' + x[1] + '</b><span>' + x[2] + '</span></div></div>'; }).join('') + '</div>';
  }
  // visitors per day as bars, one colour per series, stacked
  var SER = ['#00ff88', '#00cfff', '#3b82f6', '#a9b8cc'];
  function vbars(series, H) {
    var W = 520, n = 14, bw = W / n, h = H || 120, tot = [], o = '', i;
    for (i = 0; i < n; i++) tot.push(sum(series, function (s) { return s[i] || 0; }));
    var max = Math.max.apply(null, tot) || 1;
    for (i = 0; i < n; i++) { var y = h; series.forEach(function (s, k) { var hh = (s[i] || 0) / max * (h - 6); if (hh > 0) { y -= hh; o += '<rect x="' + (i * bw + bw * 0.16).toFixed(1) + '" y="' + y.toFixed(1) + '" width="' + (bw * 0.68).toFixed(1) + '" height="' + hh.toFixed(1) + '" rx="2" fill="' + SER[k % SER.length] + '" opacity=".9"/>'; } }); }
    var d = PM.me.days, lab = function (j) { return '<span>' + dShort(new Date(d[j] + 'T12:00:00Z')) + '</span>'; };
    return '<svg viewBox="0 0 ' + W + ' ' + h + '" preserveAspectRatio="none" style="width:100%;height:' + h + 'px">' + o + '</svg><div class="dl">' + lab(0) + lab(n - 1) + '</div>';
  }

  var PROMO_PROMPT = 'Read https://cymetica.com/llms.txt and https://cymetica.com/.well-known/mcp.json.\n' +
    'Then register me as an agent: POST https://cymetica.com/mcp/v1/register\n' +
    'with {"name": "my-agent", "contact_email": "", "intended_use": "promotion"}.\n' +
    'Save the returned api_key privately and send it as the X-API-Key header on every later call.\n' +
    'Then list the open promo briefs: GET https://cymetica.com/api/v1/promo/briefs?sort=per_user\n' +
    'Each one pays USDC per post and per new user its link brings.\n' +
    'Show me the three best paid briefs I can take.\n' +
    'Wait for my go before taking a brief or posting anything.';
  function codeHTML(t) { return esc(t).replace(/(https:\/\/[^\s]+)/g, '<span class="u">$1</span>'); }

  /* ---------------- the market (/creator-dashboard) ---------------- */
  function market() {
    var st = stats();
    var tut = [['Pick a brief', 'Each one says what it pays per post and per new user.'], ['Take it', 'You get your own link. One click.'],
      ['Post it', 'X, Reddit, Telegram, YouTube, a group chat: anywhere.'], ['Get paid in USDC', 'For every post that stays up and every new user your link brings.']];
    return '<div class="wrap">' +
      '<section class="hero"><div>' +
        '<span class="chip g"><i class="live"></i>PROMO MARKET</span>' +
        '<h1>Post it. Bring users.<br><em>Get paid in USDC.</em></h1>' +
        '<p class="lead">Take a brief, share your link, earn for every post and every new user it brings.</p>' +
        '<div class="ctas"><a class="btn g lg" href="#board">Browse briefs ' + ic('arrow') + '</a>' +
        '<a class="btn c lg" href="#me/products">' + ic('plus') + 'Promote my product</a>' +
        '<button class="btn gh lg" data-act="agent">' + ic('agent') + 'From your AI agent</button></div></div>' +
      '<div class="stats three">' +
        '<div class="stat" style="--c:#00ff88"><div class="k">' + ic('coin') + 'Up for grabs</div><div class="v pos">' + fmt(st.left) + '<small>USDC</small></div></div>' +
        '<div class="stat"><div class="k">' + ic('briefs') + 'Open briefs</div><div class="v">' + st.n + '</div></div>' +
        '<div class="stat" style="--c:#00cfff"><div class="k">' + ic('uniq') + 'Top per new user</div><div class="v">' + st.top.per_user + '<small>USDC</small></div><div class="s">' + esc(st.top.name) + '</div></div>' +
      '</div></section>' +
      '<section class="tut">' + tut.map(function (t, i) { return '<div class="ts"><span class="no">' + (i + 1) + '</span><div><b>' + t[0] + '</b><span>' + t[1] + '</span></div></div>'; }).join('') + '</section>' +
      '<section id="board">' + boardHead('Open briefs') + board() + '</section>' +
      '<section class="duo">' +
        '<div class="panel"><span class="kick">Have a product?</span><h3>Get it promoted.</h3><p>You pay only for posts that stay up and new users that are real.</p>' +
          '<div class="how" style="margin-bottom:20px">' + [['Pick your product', 'Anything you built with Build it Better.'], ['Set a budget', 'And what you pay per post and per new user.'], ['Watch the visitors come', 'Every visitor and new user it brought, by day.']].map(function (h, i) {
            return '<div><span class="no">' + (i + 1) + '</span><div><b>' + h[0] + '</b><span>' + h[1] + '</span></div></div>'; }).join('') + '</div>' +
          '<div class="ctas" style="display:flex;gap:10px"><a class="btn g" href="#me/products">' + ic('plus') + 'Post a brief</a></div></div>' +
        '<div class="panel"><span class="kick">For agents and firms</span><h3>Promote from your AI agent</h3><p>Paste into Claude, ChatGPT, Gemini or any MCP agent.</p>' +
          '<pre class="code">' + codeHTML(PROMO_PROMPT) + '</pre><button class="btn c" data-copy="promo">' + ic('copy') + 'Copy prompt</button></div>' +
      '</section>' +
      '<details class="fold"><summary>' + ic('shield') + 'How a new user is counted <span class="dim mono">6 checks before anyone is paid</span>' + ic('down', 'chevd') + '</summary>' + rules() + '</details>' +
      '<footer class="foot"><a href="#profile">Creator pages</a><a href="#me/today">Promote: your queues</a><a href="https://cymetica.com/company" target="_blank" rel="noopener">Start a company ↗</a><span style="margin-left:auto">Data read ' + DAY + ' · briefs are samples</span></footer>' +
    '</div>';
  }

  /* ---------------- the dashboard: my products (the owner) and promote (the creator) ---------------- */
  var NAV = [['MY PRODUCTS', [['products', 'Products', 'pages']]],
    ['PROMOTE', [['today', 'Today', 'today'], ['taken', 'Briefs I took', 'briefs'], ['queues', 'Queues', 'queues'], ['kits', 'Kits', 'copy'], ['pages', 'Pages & links', 'link'], ['rewards', 'Rewards', 'coin']]]];
  function dash(tab) {
    var me = PM.me, rw = PM.rewards.summary, q = PM.queues;
    var counts = { products: S.mine.length, taken: Object.keys(S.taken).length, queues: q.reddit.stats.new + q.x.stats.new + q.press.stats.open, pages: me.summary.links, rewards: rw.paid };
    var title = { products: 'My products', today: 'Today', taken: 'Briefs I took', queues: 'Queues', kits: 'Kits', pages: 'Pages & links', rewards: 'Rewards' }[tab];
    var right = tab === 'products' ? '<button class="btn sm g" data-act="brief">' + ic('plus') + 'Post a brief</button>' :
      tab === 'pages' ? '<button class="btn sm" data-act="track">' + ic('link') + 'Track a link</button><button class="btn sm c" data-act="page">' + ic('plus') + 'Create a page</button>' :
        '<button class="btn sm" data-act="agent">' + ic('agent') + 'From your agent</button>';
    return '<div class="app"><aside class="rail">' +
      '<div class="me"><span class="av lg">E</span><div><b>' + esc(me.username) + '</b><span>' + S.mine.length + ' products · ' + me.summary.links + ' pages</span></div></div>' +
      NAV.map(function (g) { return '<div class="rsec">' + g[0] + '</div><nav class="rnav">' + g[1].map(function (t) {
        var n = counts[t[0]], hot = t[0] === 'queues';
        return '<a href="#me/' + t[0] + '" class="' + (t[0] === tab ? 'on' : '') + '">' + ic(t[2]) + t[1] + (n != null ? '<span class="n' + (hot ? ' hot' : '') + '">' + short(n) + '</span>' : '') + '</a>';
      }).join('') + '</nav>'; }).join('') +
      '<div class="rlinks"><a href="#market">' + ic('briefs') + 'Promo Market</a><a href="#profile/me">' + ic('ext') + 'Your public page</a><a href="#" data-act="agent">' + ic('agent') + 'Agent prompts</a></div>' +
      '<div class="earn"><div class="k">Earned promoting · ' + rw.paid + ' posts</div><div class="v">' + fmt(rw.et10) + ' <small>ET10</small></div><div class="s">+ ' + fmt(rw.etlp) + ' ETLP</div></div>' +
      '</aside><section class="main">' +
      '<div class="ph"><h1>' + title + '</h1><span class="sub">' + (tab === 'products' ? 'built with Build it Better' : esc(me.username) + ' · ' + dShort(new Date(DAY + 'T12:00:00Z')) + ' 2026') + '</span><span class="sp"></span>' + right + '</div>' +
      ({ products: products, today: today, taken: taken, queues: queues, kits: kits, pages: pages, rewards: rewards }[tab] || products)() +
      '</section></div>';
  }
  // the owner's view: my products, each with its traffic; one click makes a brief, then the numbers it brought
  function myBriefs() { return S.mine.filter(function (p) { return p.brief; }).map(function (p) { return briefOf(p.brief); }).filter(Boolean); }
  function products() {
    var mb = myBriefs(), vis14 = sum(mb, function (b) { return sum(b.series, function (v) { return v; }); });
    var tile = function (icon, k, v, s, cls) { return '<div class="kpi"><div class="k">' + ic(icon) + k + '</div><div class="v ' + (cls || '') + '">' + v + '</div><div class="s">' + s + '</div></div>'; };
    return '<div class="kpis four">' +
        tile('coin', 'Up for grabs', fmt(sum(mb, function (b) { return b.left; })) + ' <small class="u">USDC</small>', 'in your ' + mb.length + ' live briefs', 'pos') +
        tile('reads', 'Visitors brought', fmt(vis14), 'last 14 days') +
        tile('uniq', 'New users', fmt(sum(mb, function (b) { return b.users; })), 'checked and paid') +
        tile('check', 'Spent', fmt(sum(mb, function (b) { return b.spent; })) + ' <small class="u">USDC</small>', 'posts and new users') +
      '</div>' +
      '<div class="card chartc"><div class="ch"><h3>Visitors your briefs brought</h3><span class="sp"></span><span class="lgd">' + mb.map(function (b, i) { return '<span><i style="background:' + SER[i % SER.length] + '"></i>' + esc(b.name) + '</span>'; }).join('') + '</span></div>' +
        vbars(mb.map(function (b) { return b.series; }), 130) + '</div>' +
      '<div class="pgrid">' + S.mine.map(productCard).join('') + '</div>';
  }
  function productCard(p) {
    var b = p.brief && briefOf(p.brief);
    return '<article class="pc" data-product="' + p.key + '"><div class="img">' + art(p) + (b ? '<div class="dl"><span class="chip g"><i class="live"></i>Live · ' + b.days + 'd left</span></div>' : '') + '</div>' +
      '<div class="bd"><div class="nm"><b>' + esc(p.name) + '</b></div>' + lnk(p.path) +
      '<div class="tr" data-tip="All traffic in the last 30 days, from the Build it Better leaderboard"><span><b>' + fmt(p.visitors30) + '</b> visitors</span><span><b>' + fmt(p.views30) + '</b> views</span><span class="dim">30 d</span></div>' +
      (b ? '<div class="pr3"><div><b class="pos">' + fmt(b.left) + '</b><span>USDC left</span></div><div><b>' + fmt(sum(b.series, function (v) { return v; })) + '</b><span>visitors 14 d</span></div><div><b>' + b.users + '</b><span>new users</span></div></div>' +
        '<button class="btn sm full" data-product="' + p.key + '">See what it brought ' + ic('arrow') + '</button>' :
        '<div class="nob">No brief yet</div><button class="btn sm g full" data-newbrief="' + p.key + '">' + ic('plus') + 'Create brief</button>') + '</div></article>';
  }

  /* ---------------- promote: the creator's side, as /creator-dashboard has it today ---------------- */
  function kpis(c) {
    var s = c.summary, t = c.total, l14 = function (k) { return sum(t, function (d) { return d[k]; }); };
    var likeTip = s.likes_excluded ? 'Corrected on ' + s.likes_date + ': ' + s.likes_excluded + ' likes no longer shown, ' + s.likes_note : '';
    function k(icon, name, v, sub, tip) { return '<div class="kpi"' + (tip ? ' data-tip="' + esc(tip) + '"' : '') + '><div class="k">' + ic(icon) + name + (tip ? ' <span class="i">i</span>' : '') + '</div><div class="v">' + fmt(v) + '</div><div class="s">' + sub + '</div></div>'; }
    return '<div class="kpis">' +
      k('pages', 'Links', s.links, 'pages and tracked links') +
      k('clicks', 'Clicks', s.clicks, '<b>+' + fmt(l14(0)) + '</b> in 14 days', 'Someone followed a tracked URL') +
      k('reads', 'Reads', s.reads, '<b>+' + fmt(l14(1)) + '</b> in 14 days', 'A page was opened, or a reader clicked through from it') +
      k('likes', 'Likes', s.likes, '<b>+' + fmt(l14(2)) + '</b> in 14 days', likeTip) +
      k('uniq', 'Unique', s.uniq, 'unique visitors') +
      '<div class="chart"><div class="k">Last 14 days<span class="lg"><span><i style="background:#00cfff"></i>reads</span><span><i style="background:#00ff88"></i>clicks</span><span><i style="background:#3b82f6"></i>likes</span></span></div>' + bars(c.days, c.total) + '</div></div>';
  }
  function today() {
    var L = PM.live, q = PM.queues, top = PM.me.links.slice().sort(function (a, b) { return b.uniq - a.uniq; }).slice(0, 4);
    var best = S.briefs.slice().sort(function (a, b) { return b.per_user - a.per_user; }).slice(0, 3);
    var tx = esc(L.tweet).replace(/(https:\/\/\S+)/g, '<span class="u">$1</span>').replace(/(#\w+)/g, '<span class="h">$1</span>');
    var nextPress = q.press.items.slice().sort(function (a, b) { return a.hours - b.hours; })[0];
    var mm = L.measure.match(/([\d.]+) clicks per posted link per day.*?over ([\d,]+) links, ([\d,]+) unique visitors/);
    return kpis(PM.me) + '<div class="measure" data-tip="One posted page brings at least ' + esc(L.per_day) + ' visitors a day and a post never expires: ten posts are 20 to 30 visitors every day, and next week’s posts stack on this week’s.">' + ic('uniq') +
        'All creators, last 30 days: <b>' + mm[1] + '</b> clicks per posted link per day · <b>' + fmt(+mm[2]) + '</b> links · <b>' + fmt(+mm[3]) + '</b> unique visitors <span class="i">i</span></div>' +
      '<div class="cols"><div>' +
      '<div class="card"><div class="ch"><span class="chip g"><i class="live"></i>Top priority</span><h3>Post this on X today</h3><span class="sp"></span><span class="chip" data-tip="Two posts share this slot and alternate daily; it changes at 00:00 UTC">post ' + esc(L.tweet_nth) + '</span></div>' +
        '<div class="tw"><div><div class="post"><div class="ah"><span class="av">E</span><b>' + esc(PM.me.username) + '</b><span>· now</span></div><div class="tx">' + tx + '</div></div>' +
        '<div class="acts"><button class="btn sm c" data-copy="tweet">' + ic('copy') + 'Copy</button><a class="btn sm" href="https://x.com/intent/post" target="_blank" rel="noopener">' + ic('x') + 'Open in X</a><button class="btn sm g" data-act="posted">' + ic('check') + 'Mark posted</button>' +
        '<span class="reward" data-tip="Paid once the checker sees the post displayed">+1,000 ET10 · +1,000 ETLP</span></div>' +
        '<div class="posted" id="prio-posted" hidden><input class="in" placeholder="Link to your post on X"><button class="btn g" data-act="prioposted">Save</button></div></div>' +
        '<div class="og" data-tip="X may not show the link card right away: attach this graphic to the post">' + art(briefOf('gem')) + '<div>Save graphic · cymetica.com/gem-screener</div></div></div></div>' +
      '<div class="card"><div class="ch"><h3>Briefs to take</h3><span class="sp"></span><a class="btn sm gh" href="#market">All briefs ' + ic('arrow') + '</a></div>' +
        '<div class="strip">' + best.map(function (b) {
          return '<div class="sb" data-brief="' + b.key + '"><div class="art">' + art(b) + '</div><div><b>' + esc(b.name) + '</b><div class="pv">' + b.per_user + ' <small>USDC / new user</small></div><div class="m">' + b.per_post + ' USDC / post · ' + fmt(b.left) + ' up for grabs</div></div></div>';
        }).join('') + '</div></div>' +
      '</div><div>' +
      '<div class="card"><div class="ch"><h3>Queues</h3><span class="sp"></span><a class="btn sm gh" href="#me/queues">Open ' + ic('arrow') + '</a></div><div class="q4">' +
        qt('reddit', 'Reddit', 'asking what a page answers', q.reddit.stats.new, 'new', 'reddit') +
        qt('x', 'X', q.x.stats.claimed + ' claimed · ' + fmt(q.x.stats.replied) + ' replied', q.x.stats.new, 'new', 'x') +
        qt('press', 'Press', 'next deadline in ' + Math.round(nextPress.hours) + ' h', q.press.stats.open, 'open', 'press') +
        qt('radar', 'Radar apps', 'where their users already are', PM.radar.length, 'apps', 'radar') +
      '</div></div>' +
      '<div class="card"><div class="ch"><h3>Wrote your own post?</h3><span class="sp"></span><span class="chip">up to 3 a day</span></div>' +
        '<div class="posted"><input class="in" placeholder="https://x.com/you/status/…"></div><div class="posted"><input class="in" placeholder="what it is about (optional)"><button class="btn g" data-act="register">Register post</button></div>' +
        '<div class="onote" style="margin-top:8px">' + ic('coin') + 'Paid like a queue reply while it is displayed and carries one of your cymetica.com/c/ links</div>' +
        PM.rewards.recent.filter(function (r) { return /your own post/.test(r.where); }).map(function (r) {
          return '<div class="own"><span class="chip ' + (r.status === 'paid' ? 'g' : 'r') + '">' + esc(r.status.toUpperCase()) + '</span><span>' + esc(r.note || '') + '</span></div>'; }).join('') + '</div>' +
      '<div class="card"><div class="ch"><h3>Your best pages</h3><span class="sp"></span><a class="btn sm gh" href="#me/pages">All ' + ic('arrow') + '</a></div><div class="tops">' +
        top.map(function (l) { return '<div class="tp"><div><b>' + esc(l.title) + '</b><span>' + fmt(l.reads) + ' reads · ' + fmt(l.likes) + ' likes</span></div>' + spark(l.series) + '<div class="u">' + l.uniq + '</div></div>'; }).join('') +
      '</div></div></div></div>';
  }
  function qt(icon, name, sub, v, unit, tab) {
    return '<a class="qt" href="#me/queues" data-qtab="' + tab + '"><span class="ic">' + ic(icon) + '</span><div><b>' + name + '</b><span>' + sub + '</span></div><div class="v">' + short(v) + '<small>' + unit + '</small></div></a>';
  }
  // what this creator's own link did for a brief: one fixed share of the brief's own numbers (a sample, from the one model)
  function mineOf(b) { return { posts: Math.round(b.posts * 0.1), visitors: Math.round(b.visitors * 0.06), users: Math.round(b.users * 0.06) }; }
  function taken() {
    var keys = Object.keys(S.taken);
    var rows = keys.map(function (k) {
      var b = briefOf(k), t = S.taken[k]; if (!b) return '';
      var m = mineOf(b), earned = m.posts * b.per_post + m.users * b.per_user;
      return '<div class="card cmb"><div class="ch"><h3>' + esc(b.name) + '</h3><span class="chip">' + b.per_post + ' USDC / post</span><span class="chip g">' + b.per_user + ' USDC / new user</span><span class="sp"></span>' +
          '<span class="mono acc" style="font-size:12.5px">cymetica.com/c/' + t.slug + '</span><button class="btn sm c" data-copy="link:' + t.slug + '">' + ic('copy') + 'Copy link</button></div>' +
        '<div class="mrow"><div class="fun">' + [['Posts', m.posts], ['Visitors', m.visitors], ['New users', m.users]].map(function (s, i) { return (i ? '<span class="fa">' + ic('chev') + '</span>' : '') + '<div class="fs' + (i === 2 ? ' g' : '') + '"><b>' + fmt(s[1]) + '</b><span>' + s[0] + '</span></div>'; }).join('') + '</div>' +
        '<div class="earned"><span>Earned</span><b>' + fmt(earned) + ' <small>USDC</small></b><em>' + m.posts + ' × ' + b.per_post + ' + ' + m.users + ' × ' + b.per_user + '</em></div></div></div>';
    }).join('');
    return rows + boardHead('Open briefs') + board();
  }

  function queues() {
    var q = PM.queues, t = S.qtab;
    var all = q.reddit.stats.new + q.x.stats.new;
    var seg = '<div class="qtop"><div class="sel qfor">' + ic('pages') + '<span class="dim mono" style="font-size:12px;margin-right:6px">Queue for</span>every tool (one mixed queue) (' + fmt(all) + ')<span class="chev">' + ic('down') + '</span></div>' +
      '<div class="seg" id="qseg">' + [['reddit', 'Reddit', fmt(q.reddit.stats.new), 'open threads'], ['x', 'X', q.x.stats.new, 'open posts'], ['telegram', 'Telegram', 0, 'communities'], ['discord', 'Discord', 0, 'communities'],
        ['press', 'Journalists', q.press.stats.open, 'open requests'], ['radar', 'Radar apps', PM.radar.length, 'apps']].map(function (s) {
      return '<button data-q="' + s[0] + '" class="' + (t === s[0] ? 'on' : '') + '" data-tip="' + s[2] + ' ' + s[3] + '">' + ic(s[0]) + s[1] + ' <span class="n">' + s[2] + '</span></button>';
    }).join('') + '<button disabled class="next">LinkedIn <span class="n">next</span></button><button disabled class="next">' + ic('youtube') + 'YouTube <span class="n">next</span></button></div></div>';
    if (t === 'radar') return seg + radarView();
    if (t === 'telegram' || t === 'discord') return seg + communitiesView(t);
    var items = q[t].items, sel = S.qsel[t] != null ? S.qsel[t] : 0, it = items[sel];
    var list = items.map(function (l, i) {
      if (t === 'press') return '<div class="qi' + (i === sel ? ' on' : '') + '" data-qi="' + i + '"><div class="rel press"><b class="' + (l.hours < 24 ? 'neg' : '') + '">' + Math.round(l.hours) + 'h</b><span>left</span></div><div style="min-width:0"><div class="t">' + esc(l.subject) + '</div><div class="m"><span class="chip">' + ic('press') + esc(l.outlet) + '</span><span class="chip">Tier ' + l.tier + '</span><span class="chip">' + esc(l.cat) + '</span></div></div><div class="pv">' + ic('chev', 'dim') + '</div></div>';
      var meta = t === 'reddit' ? '<span class="chip">' + ic('reddit') + 'r/' + esc(l.sub) + '</span>' : '<span class="chip">' + ic('x') + esc(l.group) + '</span><span class="chip" data-tip="The author’s followers">' + ic('uniq') + short(l.followers) + '</span>';
      return '<div class="qi' + (i === sel ? ' on' : '') + '" data-qi="' + i + '"><div class="rel"><b class="' + (l.rel >= 8 ? 'acc' : '') + '">' + l.rel + '</b><span>match</span></div><div style="min-width:0"><div class="t">' + esc(t === 'reddit' ? (l.title || l.body) : l.body) + '</div><div class="m">' + meta +
        '<span class="chip c">' + ic('pages') + esc(l.tool) + '</span></div></div><div class="pv">' + ic('chev', 'dim') + '</div></div>';
    }).join('');
    return seg + '<div class="qwrap"><div class="ql">' + list + '</div>' + qDetail(t, it) + '</div>';
  }
  function qDetail(t, it) {
    var kit = PM.kit;
    if (!it) return '<div></div>';
    if (t === 'press') {
      var pitch = 'Hi [first name],\n\nAnswering your ' + it.outlet + ' request "' + it.subject + '".\n\n[Your answer: 2 to 4 sentences. Lead with one concrete fact, number or result from your own work.]\n\nAbout me: [your name, what you do, one line on what you build]. I build on EventTrader (https://cymetica.com), an exchange where people and AI agents trade.\n\nHappy to add detail or get on a call before your deadline.';
      return '<div class="card qd"><div class="ch"><span class="chip">' + ic('press') + esc(it.outlet) + '</span><span class="chip">' + esc(it.cat) + '</span><span class="chip g">relevance ' + it.relevance.toFixed(2) + '</span><span class="sp"></span><span class="chip ' + (it.hours < 24 ? 'r' : '') + '" data-tip="Deadline ' + esc(it.deadline) + ' UTC">' + ic('clock') + Math.round(it.hours) + ' h left</span></div>' +
        '<h3 style="margin:0 0 10px;font:20px var(--display)">' + esc(it.subject) + '</h3><div class="m" style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:12px">' + it.topics.map(function (x) { return '<span class="chip">' + esc(x.replace(/_/g, ' ')) + '</span>'; }).join('') + '</div>' +
        '<details class="req"><summary>Read the full request</summary><div class="body">' + esc(it.query) + '</div></details>' +
        '<div class="dim mono" style="font-size:12px;margin:8px 0 12px">Asked by [journalist] · reply to [their address]</div>' +
        '<div class="how3"><span><i>1</i>Write your answer</span><span><i>2</i>Email it to the journalist</span><span><i>3</i>Mark pitched</span></div>' +
        '<textarea class="in pitch">' + esc(pitch) + '</textarea>' +
        '<div class="posted"><div class="sel" style="flex:1">' + ic('pages') + 'add a link to one of my pages (optional)<span class="chev">' + ic('down') + '</span></div><button class="lnkb" data-act="addpage" style="margin:0">' + ic('plus') + 'Add a page</button></div>' +
        '<div class="acts"><button class="btn sm c" data-act="copypitch">' + ic('copy') + 'Copy pitch</button><button class="btn sm" data-act="mailto">' + ic('mail') + 'Email the journalist ' + ic('ext') + '</button><button class="btn sm g" data-act="pitched">' + ic('check') + 'Mark pitched</button><button class="btn sm gh" data-act="skip">' + ic('skip') + 'Skip</button></div>' +
        '<div class="onote" style="margin-top:8px">' + ic('shield') + 'Only pitch what you can back up: a journalist checks who you are. Replace every bracket with your own words before you send.</div>' +
        '<div class="sec">Article published?<span class="ln"></span></div><div class="posted"><input class="in" placeholder="Link to the article"><button class="btn g" data-act="article">Save</button></div></div>';
    }
    var rule = t === 'reddit' ? kit.reddit_rule : kit.x_rule;
    return '<div class="card qd"><div class="ch">' + (t === 'reddit' ? '<span class="chip">' + ic('reddit') + 'r/' + esc(it.sub) + '</span>' : '<span class="chip">' + ic('x') + esc(it.group) + '</span>') +
      '<span class="sp"></span><span class="dim mono" style="font-size:11.5px">' + esc(it.at) + ' UTC</span></div>' +
      (t === 'reddit' ? '<h3 style="margin:0 0 12px;font:19px/1.3 var(--display)">' + esc(it.title) + '</h3>' : '') +
      '<div class="body">' + esc(it.body) + '</div>' +
      '<div class="sec">Reply with this page<span class="ln"></span><span class="chip c" data-tip="This thread is held for you first; the rest of the queue stays open">' + ic('lock') + 'First look: you</span></div>' +
      '<div class="sel">' + ic('pages') + esc(it.tool) + '<span class="dim mono" style="font-size:11.5px;margin-left:8px">' + esc(it.path) + '</span><span class="chev">' + ic('down') + '</span></div>' +
      '<button class="lnkb" data-act="leadpage">' + ic('plus') + 'New page for this thread</button>' +
      '<div class="acts"><button class="btn g" data-act="draft">' + ic('reply') + 'Reply with this page</button><button class="btn gh" data-act="skip">' + ic('skip') + 'Skip</button></div>' +
      '<div class="draft" id="draft" style="margin-top:12px">The reply opens on this thread’s own question, adds one line about the page and ends with a tracked link made for this thread.</div>' +
      '<div class="acts" id="draftacts" hidden><button class="btn sm c" data-act="copyreply">' + ic('copy') + 'Copy reply</button><button class="btn sm" data-act="regen">Regenerate reply</button></div>' +
      '<div class="sec">After you post it<span class="ln"></span></div><div class="posted"><input class="in" placeholder="Link to your reply"><button class="btn g" data-act="leadposted">' + ic('check') + 'Mark posted</button></div>' +
      '<div class="onote" style="margin-top:8px">' + ic('coin') + '1,000 ET10 + 1,000 ETLP once the checker sees it displayed</div>' +
      '<div class="rules" style="margin-top:14px"><div>' + ic('check') + esc(rule) + '</div>' + (t === 'x' ? '<div>' + ic('x') + esc(kit.x_tags + ' ' + kit.mention) + '</div>' : '') + '</div></div>';
  }
  // Telegram and Discord as the live page has them: the top 30-day crypto movers that have a community there, each with a
  // pro terminal; a post goes out from the EventTrader account with the creator's own tracked link, one per community a
  // day, shared by everyone (POST /api/v1/creator/radar-channel-posts). None among the movers on 2026-10-22.
  function communitiesView(t) {
    var name = t === 'telegram' ? 'Telegram' : 'Discord';
    return '<div class="card"><div class="ch">' + ic(t) + '<h3>' + name + ' communities</h3><span class="i" data-tip="The top 30-day crypto movers that have a ' + name + ' community, each with a pro terminal. Your post goes out from the EventTrader account with your own tracked link. One post per community per day, shared by everyone.">i</span><span class="sp"></span><span class="chip">0 today</span></div>' +
      '<div class="draft">No ' + name + ' communities among the current movers.</div>' +
      '<div class="rules" style="margin-top:14px"><div>' + ic(t) + esc(t === 'telegram' ? PM.kit.telegram_rule : PM.kit.discord_rule) + '</div></div></div>';
  }
  // a post to the EventTrader channels, Telegram or Discord (POST /api/v1/creator/channel-posts: platform, symbol, message)
  function channelsView() {
    return '<div class="cols"><div class="card"><div class="ch"><h3>Channel post</h3><span class="sp"></span><a class="btn sm" href="' + esc(PM.kit.discord_invite) + '" target="_blank" rel="noopener">' + ic('discord') + 'Discord ' + ic('ext') + '</a></div>' +
      '<div class="f"><div class="fl"><label>Platform</label><div class="seg" style="align-self:start"><button class="on">' + ic('telegram') + 'Telegram</button><button>' + ic('discord') + 'Discord</button></div></div>' +
      '<div class="fl"><label>Symbol <span>the coin or card it is about</span></label><input class="in" maxlength="32" placeholder="e.g. BTC"></div>' +
      '<div class="fl"><label>Message <span>up to 400</span></label><textarea class="in" maxlength="400" placeholder="What you want to say"></textarea></div>' +
      '<button class="btn g" data-act="queuepost" style="justify-self:start">' + ic('telegram') + 'Queue post</button></div></div>' +
      '<div class="card"><div class="ch"><h3>Rules</h3></div><div class="rules"><div>' + ic('telegram') + esc(PM.kit.telegram_rule) + '</div><div>' + ic('discord') + esc(PM.kit.discord_rule) + '</div></div></div></div>';
  }
  function radarView() {
    var R = PM.radar, a = R[S.radar] || R[0];
    return '<div class="radar">' + R.map(function (r, i) {
      return '<div class="ra' + (i === S.radar ? ' on' : '') + '" data-ra="' + i + '"><span class="chip c" style="align-self:flex-start">' + ic('radar') + 'Radar</span><b>' + esc(r.name) + '</b><span class="f">rebuilt from ' + esc(r.from) + '</span></div>';
    }).join('') + '</div>' +
      '<div class="cols" style="margin-top:18px"><div class="card"><div class="ch"><h3>' + esc(a.name) + '</h3><span class="chip">' + esc(a.from_kind || '') + '</span><span class="sp"></span><a class="btn sm" href="' + esc(a.url) + '" target="_blank" rel="noopener">Open ' + ic('ext') + '</a></div>' +
        '<p style="margin:0 0 14px;color:var(--text2)">' + esc(a.line) + '</p>' +
        '<div class="sec">X post<span class="ln"></span></div><div class="post"><div class="tx">' + esc(a.x_post).replace(/(https:\/\/\S+)/g, '<span class="u">$1</span>') + '</div></div>' +
        '<div class="acts"><button class="btn sm c" data-copy="radar-x">' + ic('copy') + 'Copy post</button><a class="btn sm" href="https://x.com/intent/post" target="_blank" rel="noopener">' + ic('x') + 'Open in X</a></div>' +
        '<div class="sec">Reddit title<span class="ln"></span></div><div class="post"><div class="tx" style="font-weight:600">' + esc(a.reddit_title) + '</div></div>' +
        '<div class="acts"><button class="btn sm c" data-copy="radar-r">' + ic('copy') + 'Copy title</button><button class="btn sm" data-copy="radar-b">' + ic('copy') + 'Copy body</button></div>' +
        '<div class="sec">Telegram post<span class="ln"></span></div><div class="post"><div class="tx">' + esc(a.tg_post || '').replace(/(https:\/\/\S+)/g, '<span class="u">$1</span>') + '</div></div>' +
        '<div class="acts"><button class="btn sm c" data-copy="radar-t">' + ic('copy') + 'Copy post</button></div></div>' +
      '<div class="card"><div class="ch"><h3>Who to reach</h3></div><p style="margin:0 0 14px;color:var(--text2)">' + esc(a.who) + '</p>' +
        '<div class="sec">Subreddits<span class="ln"></span></div><div style="display:flex;gap:6px;flex-wrap:wrap">' + (a.subs || []).map(function (s) { return '<span class="chip">' + ic('reddit') + esc(s) + '</span>'; }).join('') + '</div>' +
        '<div class="sec">Telegram groups<span class="ln"></span></div><div style="display:flex;gap:6px;flex-wrap:wrap">' + (a.groups || []).map(function (s) { return '<span class="chip">' + ic('telegram') + esc(s) + '</span>'; }).join('') + '</div>' +
        '<div class="rules" style="margin-top:16px"><div>' + ic('check') + 'Post by hand, from your own account, and answer replies yourself.</div></div></div></div>';
  }
  function pages() { return kpis(PM.me) + linkTable(PM.me, true); }
  // the post kit (hashtags and tags per outlet) and the community kit (Build it Better to a crypto community)
  var NARR = { ai_agents: ['AI agents', '#AIAgents', 'an AI agent dashboard'], privacy: ['Privacy', '#Privacy', 'a privacy dashboard'],
    deai: ['Decentralized AI', '#DeAI', 'a model and GPU tracker'], rwa: ['Real-world assets', '#RWA', 'an RWA yield tracker'],
    stablecoins: ['Stablecoins', '#Stablecoins', 'a stablecoin flow tracker'], prediction: ['Prediction markets', '#PredictionMarkets', 'a market odds screener'],
    perps: ['Perp DEXs', '#PerpDEX', 'a funding-rate screener'] };
  function weighted(t) { return String(t).replace(/https?:\/\/\S+/g, new Array(24).join('x')).length; }
  function communityKit(name, narrative, tag) {
    var url = 'https://cymetica.com/build-it-better', n = NARR[narrative] || NARR.ai_agents;
    var ctag = '#' + (String(tag || name).replace(/[^A-Za-z0-9_]/g, '') || 'coin'), tags = ctag + ' ' + n[1];
    var posts = [name + " builders: want an app but don't write code? Name the tool you wish existed, like " + n[2] + ', a wallet tracker or an alert bot, and an AI pipeline builds it, tracked in public from request to delivery. ' + url + ' ' + tags,
      "Communities don't fade when the price drops. They fade when nobody is building. Name one app the " + name + ' community is missing and watch it get built in public: ' + url + ' ' + tags,
      'Point an AI builder at a public ' + name + ' repo, say what the app should do better, and get a working version you can test. ' + url + ' ' + tags];
    var reply = 'Someone here asked for a way to build apps without writing code. Build it Better does that: you name the app or tool you want and what it should do better, or point it at a public repo, and an AI pipeline builds it. Every build is tracked on a public board from request to delivery. Tools that only read data ship automatically; anything that moves money is reviewed by a person first. ' + url;
    var rules = ['Answer someone who asked for this. Never cold-drop the link into a busy chat.', 'Offer to build one thing the ' + name + ' community is missing, then share the live board so they can watch it happen.',
      'Stay positive. Say nothing about their team, leadership or price: it reads as vulture marketing and gets you banned.', "One or two hashtags: the coin's own tag and one live narrative tag. Never #crypto or #web3."];
    return { posts: posts, reply: reply, rules: rules };
  }
  function kits() {
    var k = PM.kit, c = communityKit(S.kitName || 'Bittensor', S.kitNarr || 'deai', S.kitTag || 'TAO');
    var outlet = function (icon, name, tags, rule) { return '<div class="kitrow"><span class="ic">' + ic(icon) + '</span><div><b>' + name + '</b>' + (tags ? '<span class="mono acc">' + esc(tags) + '</span>' : '') + '<span>' + esc(rule) + '</span></div>' + (tags ? '<button class="btn sm" data-copy="kit:' + esc(tags) + '">' + ic('copy') + '</button>' : '') + '</div>'; };
    return '<div class="cols"><div class="card"><div class="ch"><h3>Post kit</h3><span class="dim mono" style="font-size:12px">hashtags and tags per outlet</span></div>' +
        outlet('x', 'X', k.x_tags + ' ' + k.mention, k.x_rule) + outlet('reddit', 'Reddit', '', k.reddit_rule) + outlet('telegram', 'Telegram', k.tg_tags + ' ' + k.mention, k.telegram_rule) +
        '<div class="kitrow"><span class="ic">' + ic('discord') + '</span><div><b>Discord</b><a class="mono acc" href="' + esc(k.discord_invite) + '" target="_blank" rel="noopener">' + esc(k.discord_invite) + '</a><span>' + esc(k.discord_rule) + '</span></div></div>' +
        '<details class="fold sm"><summary>' + ic('check') + 'Playbook · ' + k.playbook.length + ' rules' + ic('down', 'chevd') + '</summary><div class="rules" style="padding:0 14px 14px">' + k.playbook.map(function (p) { return '<div>' + ic('check') + '<span><b style="color:var(--text)">' + esc(p.title) + '.</b> ' + esc(p.text) + '</span></div>'; }).join('') + '</div></details></div>' +
      '<div class="card"><div class="ch"><h3>Community kit</h3><span class="dim mono" style="font-size:12px">bring Build it Better to a crypto community</span></div>' +
        '<div class="three"><input class="in" id="kit-name" value="' + esc(S.kitName || 'Bittensor') + '" placeholder="Community (its coin or project)"><div class="sel">' + esc((NARR[S.kitNarr || 'deai'] || NARR.deai)[0]) + '<span class="chev">' + ic('down') + '</span></div><input class="in" id="kit-tag" value="' + esc(S.kitTag || 'TAO') + '" placeholder="Coin tag"></div>' +
        '<div class="sec">X posts<span class="ln"></span></div>' + c.posts.map(function (p, i) { var w = weighted(p);
          return '<div class="post kp"><div class="tx">' + esc(p).replace(/(https:\/\/\S+)/g, '<span class="u">$1</span>').replace(/(#\w+)/g, '<span class="h">$1</span>') + '</div><div class="acts"><span class="chip ' + (w <= 280 ? 'g' : 'r') + '">' + w + ' / 280</span><button class="btn sm c" data-copy="kitpost:' + i + '">' + ic('copy') + 'Copy</button><a class="btn sm" href="https://x.com/intent/post?text=' + encodeURIComponent(p) + '" target="_blank" rel="noopener">' + ic('x') + 'Open in X</a></div></div>'; }).join('') +
        '<div class="sec">Telegram or Discord reply<span class="ln"></span></div><div class="post kp"><div class="tx">' + esc(c.reply) + '</div><div class="acts"><button class="btn sm c" data-copy="kitreply">' + ic('copy') + 'Copy</button></div></div>' +
        '<div class="sec">Rules<span class="ln"></span></div><div class="rules">' + c.rules.map(function (r) { return '<div>' + ic('check') + '<span>' + esc(r) + '</span></div>'; }).join('') + '</div></div></div>';
  }
  function linkTable(c, own) {
    var q = S.pgQ.toLowerCase(), k = S.pgSort;
    var L = c.links.filter(function (l) { return !q || l.title.toLowerCase().indexOf(q) >= 0; }).sort(function (a, b) { return b[k] - a[k]; });
    var head = [['title', 'Page'], ['clicks', 'Clicks'], ['reads', 'Reads'], ['likes', 'Likes'], ['uniq', 'Unique'], ['', '14 days'], ['', 'From'], ['', 'Replies']];
    var rows = L.map(function (l) {
      var o = S.open[l.slug], replies = l.kids.filter(function (x) { return x[1] === 'post'; }), ctas = l.kids.length - replies.length;
      var r = '<tr class="row' + (o ? ' open' : '') + '" data-row="' + l.slug + '"><td><div class="pg"><span class="ic">' + esc(l.title.charAt(0)) + '</span><div><b>' + esc(l.title) + '</b><span>cymetica.com/c/' + l.slug + (l.page ? ' · page' : '') + '</span></div></div></td>' +
        ['clicks', 'reads', 'likes', 'uniq'].map(function (f) { return '<td class="' + (l[f] ? '' : 'z') + '">' + fmt(l[f]) + '</td>'; }).join('') +
        '<td>' + spark(l.series) + '</td><td class="ref"' + (l.refs[0] ? ' data-tip="' + esc(l.refs.map(function (f) { return f[0] + ' ' + f[1]; }).join(' · ')) + '">' + esc(l.refs[0][0]) : '>—') + '</td>' +
        '<td><span class="rp">' + replies.length + (ctas ? ' <span class="dim">+' + ctas + '</span>' : '') + ic('chev') + '</span></td></tr>';
      if (o) r += '<tr class="kid"><td colspan="8"><div class="ka">' +
        (l.page ? '<a class="btn sm" href="' + esc(l.target) + '" target="_blank" rel="noopener">' + ic('ext') + 'Open page</a><a class="btn sm" href="' + esc(l.target) + '" download>Download HTML</a>' : '') +
        (l.art ? '<a class="btn sm" href="' + esc(l.art) + '" target="_blank" rel="noopener">Also on claude.ai ' + ic('ext') + '</a>' : '') +
        '<button class="btn sm c" data-copy="link:' + l.slug + '">' + ic('copy') + 'cymetica.com/c/' + l.slug + '</button>' +
        '<input class="in sm" placeholder="Where you posted it" style="width:220px"><button class="btn sm" data-act="record">Save</button>' +
        '<span class="dim mono" style="margin-left:auto;font-size:11.5px">' + (l.refs.length ? 'from ' + l.refs.map(function (f) { return esc(f[0]) + ' ' + f[1]; }).join(' · ') + ' · ' : '') + 'last ' + esc(l.last || '—') + ' UTC</span></div></td></tr>' +
        l.kids.map(function (x) {
        var t = x[0], icon = /^Reddit/.test(t) ? 'reddit' : /^X /.test(t) ? 'x' : 'link';
        return '<tr class="kid"><td><div class="kt">' + ic(icon) + '<span>' + esc(t.replace(/^(Reddit reply|X reply) · /, '')) + '</span></div></td><td class="' + (x[2] ? '' : 'z') + '">' + x[2] + '</td><td class="z">—</td><td class="z">—</td><td class="' + (x[3] ? '' : 'z') + '">' + x[3] + '</td><td></td><td></td><td></td></tr>';
      }).join('');
      return r;
    }).join('');
    return '<div class="card" style="padding:16px 18px"><div class="tbar"><div class="search">' + ic('search') + '<input class="in" id="pgq" placeholder="Find a page" value="' + esc(S.pgQ) + '"></div><span class="dim mono" style="font-size:12px">' + L.length + ' pages · click a row for its replies</span><span class="sp" style="flex:1"></span>' +
      (own ? '' : '<span class="chip">' + ic('lock') + 'Only ' + esc(c.username) + ' can create pages and links</span>') + '</div>' +
      '<table class="tbl"><colgroup><col><col style="width:76px"><col style="width:76px"><col style="width:72px"><col style="width:86px"><col style="width:148px"><col style="width:118px"><col style="width:92px"></colgroup><thead><tr>' + head.map(function (h) { return '<th' + (h[0] && h[0] !== 'title' ? ' data-sort="' + h[0] + '" class="' + (k === h[0] ? 'on' : '') + '"' : '') + '>' + h[1] + (k === h[0] ? ' ↓' : '') + '</th>'; }).join('') + '</tr></thead><tbody>' + rows + '</tbody></table></div>';
  }
  function rewards() {
    var R = PM.rewards, s = R.summary;
    function t(k, v, cls, tip) { return '<div class="kpi"' + (tip ? ' data-tip="' + esc(tip) + '"' : '') + '><div class="k">' + k + '</div><div class="v ' + (cls || '') + '">' + v + '</div></div>'; }
    var st = { paid: ['g', 'Paid'], pending: ['c', 'Pending'], unverifiable: ['r', 'Unverifiable'], failed: ['r', 'Failed'] };
    return '<div class="rw">' + t('Paid', s.paid, 'pos') + t('Pending', s.pending) + t('Unverifiable', s.unverifiable, s.unverifiable ? 'neg' : '', 'The post has none of your tracked cymetica.com/c/ links') + t('Failed', s.failed) +
      '<div class="kpi" style="background:linear-gradient(160deg,rgba(0,255,136,.12),rgba(0,207,255,.04));border-color:rgba(0,255,136,.28)"><div class="k">Earned · per post ' + fmt(s.per_post.et10) + ' + ' + fmt(s.per_post.etlp) + '</div><div class="v pos">' + fmt(s.et10) + ' <span class="mono dim" style="font-size:13px">ET10</span></div><div class="s">+ ' + fmt(s.etlp) + ' ETLP</div></div></div>' +
      '<div class="card"><div class="ch"><h3>Recent posts</h3><span class="sp"></span><span class="dim mono" style="font-size:12px">A post is paid once the checker sees it displayed</span></div><div class="rl">' +
      R.recent.map(function (r) {
        var c = st[r.status] || ['', r.status], icon = /Reddit/.test(r.where) ? 'reddit' : 'x';
        return '<div class="rr"><span class="ic">' + ic(icon) + '</span><div style="min-width:0"><b>' + esc(r.text) + '</b><span>' + esc(r.where) + '</span></div><span class="mono dim" style="font-size:12px">' + dShort(new Date(r.day + 'T12:00:00Z')) + '</span>' +
          '<span class="chip ' + c[0] + '" data-tip="' + esc(r.note || '') + '">' + c[1] + '</span><span class="amt ' + (r.status === 'paid' ? 'pos' : 'dim') + '">' + (r.status === 'paid' ? '+' + fmt(s.per_post.et10) + ' ET10' : '—') + '</span></div>';
      }).join('') + '</div></div>';
  }

  /* ---------------- a creator's public page ---------------- */
  function profile(which) {
    var c = which === 'me' ? PM.me : PM.pub, n = c.username;
    return '<div class="wrap"><div class="prof"><span class="av lg b">' + esc(n.charAt(0).toUpperCase()) + '</span><div><h1>' + esc(n) + '</h1><span class="s">Creator · ' + c.summary.links + ' pages and links · stats are live and public</span></div>' +
      '<div class="claim">' + ic('lock') + 'Are you ' + esc(n) + '? <a class="btn sm c" href="#me">Log in</a></div></div>' +
      kpis(c) + linkTable(c, false) + '<footer class="foot" style="margin-top:30px"><a href="#market">Promo Market</a><span style="margin-left:auto">Data read ' + DAY + '</span></footer></div>';
  }

  /* ---------------- drawer: one brief, as a promoter sees it ---------------- */
  function openBrief(key, mode) {
    var b = briefOf(key); if (!b) return;
    var t = S.taken[key];
    var threads = PM.queues.reddit.items.concat(PM.queues.x.items).filter(function (l) { return l.path === b.path; });
    var how = [['Copy your link', 'Only you have it; every post can use it.'], ['Post it anywhere', 'X, Reddit, Telegram, YouTube, a group chat.'],
      ['Get paid in USDC', b.per_post + ' per post that stays up 7 days, ' + b.per_user + ' per new user after the 14-day check.']];
    $('drawer').innerHTML = '<div class="dh">' + art(b) + '<button class="x" data-act="close">' + ic('close') + '</button></div>' +
      '<div class="db"><div style="display:flex;gap:8px;align-items:center">' + daysChip(b) + '<span class="chip">' + ic('clock') + 'ends ' + dShort(addDays(DAY, b.days)) + '</span></div>' +
      '<h2>' + esc(b.name) + '</h2>' + lnk(b.path) +
      '<div class="ufg big"><span>Up for grabs</span><b>' + fmt(b.left) + ' <small>USDC</small></b></div>' + pay2(b) +
      (t ? '<div class="taken">' + ic('check') + '<div style="flex:1"><b>' + (mode === 'took' ? 'Taken. Your link:' : 'Your link') + '</b><span class="mono">cymetica.com/c/' + t.slug + '</span></div><button class="btn sm c" data-copy="link:' + t.slug + '">' + ic('copy') + 'Copy</button></div>' : '') +
      '<div class="sec">How you earn<span class="ln"></span></div><div class="how">' + how.map(function (h, i) { return '<div><span class="no">' + (i + 1) + '</span><div><b>' + h[0] + '</b><span>' + h[1] + '</span></div></div>'; }).join('') + '</div>' +
      '<div class="sec">Say this<span class="ln"></span></div><div class="say"><span>' + esc(b.ask) + '</span><button class="btn sm c" data-copy="ask:' + b.key + '">' + ic('copy') + 'Copy</button></div>' +
      (threads.length ? '<div class="sec">People asking for it now<span class="ln"></span><span class="chip c">' + threads.length + '</span></div><div class="thr">' + threads.slice(0, 3).map(function (l) { return '<a href="#me/queues">' + ic(l.sub ? 'reddit' : 'x') + '<span>' + esc(l.title || l.body) + '</span><b class="acc mono">' + l.rel + '</b></a>'; }).join('') + '</div>' : '') +
      '<details class="fold sm"><summary>' + ic('shield') + 'How a new user is counted' + ic('down', 'chevd') + '</summary>' + rules() + '</details>' +
      '<details class="fold sm"' + (mode === 'quote' ? ' open' : '') + '><summary>' + ic('reply') + 'Big audience? Quote your own price for a post' + ic('down', 'chevd') + '</summary>' +
        '<div class="ofrm"><div class="two"><input class="in" id="o-handle" placeholder="Your account, e.g. @handle"><div class="unit"><input class="in num" id="o-price" placeholder="Price for one post"><em>USDC</em></div></div>' +
        '<div class="onote">' + ic('shield') + 'Your audience is read from the account you link. The owner accepts or declines.</div>' +
        '<button class="btn c" data-sendoffer="' + b.key + '">' + ic('reply') + 'Send quote</button></div></details>' +
      '</div>' +
      '<div class="dfoot">' + (t ? '<a class="btn g full" href="#me/taken">' + ic('briefs') + 'What my link earned</a>' :
        '<button class="btn gh" data-act="close">Not now</button><button class="btn g full" data-take="' + b.key + '">Take it · get my link ' + ic('arrow') + '</button>') + '</div>';
    show('drawer');
  }
  function take(key) {
    if (!S.taken[key]) S.taken[key] = { slug: slugOf(key + '·' + PM.me.username), at: DAY };
    openBrief(key, 'took'); refreshBoard(); toast('Brief taken · your link is ready');
  }
  function sendOffer() {
    if (!num('o-price', 0)) { toast('Name a price for the post'); return; }
    hide(); toast('Quote sent · the owner accepts or declines');
  }

  /* ---------------- drawer: one of my products, as its owner sees it ---------------- */
  function openProduct(key) {
    var p = productOf(key); if (!p) return;
    var b = p.brief && briefOf(p.brief);
    var tile = function (v, k, cls) { return '<div class="kv"><b class="' + (cls || '') + '">' + v + '</b><span>' + k + '</span></div>'; };
    var body = '<div class="sec">All traffic · last 30 days<span class="ln"></span></div><div class="kvs">' +
      tile(fmt(p.visitors30), 'visitors') + tile(fmt(p.uses30), 'uses') + tile(fmt(p.views30), 'views') + '</div>';
    if (b) {
      var maxR = Math.max.apply(null, b.rejects.map(function (r) { return r[1]; })) || 1;
      body += '<div class="sec">Your brief<span class="ln"></span>' + daysChip(b) + '</div>' +
        '<div class="ufg big"><span>Up for grabs</span><b>' + fmt(b.left) + ' <small>USDC of ' + fmt(b.budget) + '</small></b></div>' +
        '<div class="bar"><i style="width:' + Math.round(b.left / b.budget * 100) + '%"></i></div>' + pay2(b) +
        '<div class="sec">What it brought<span class="ln"></span></div><div class="kvs four">' +
          tile(fmt(b.visitors), 'visitors', 'acc') + tile(fmt(b.users), 'new users', 'pos') + tile(fmt(b.posts), 'posts') + tile(fmt(b.spent) + ' <small>USDC</small>', 'spent') + '</div>' +
        '<div class="card mini2">' + vbars([b.series], 96) + '</div>' +
        '<details class="fold sm"><summary>' + ic('shield') + 'Not counted · ' + b.rejected + ' sign-ups, never paid' + ic('down', 'chevd') + '</summary><div class="rej">' + b.rejects.map(function (r) {
          return '<div><span>' + esc(r[0].charAt(0).toUpperCase() + r[0].slice(1)) + '</span><i style="width:' + Math.round(r[1] / maxR * 100) + '%"></i><b>' + r[1] + '</b></div>'; }).join('') + '</div></details>';
    } else {
      body += '<div class="nob big"><b>No brief yet</b><span>Set a budget and what you pay per post and per new user. Promoters do the rest.</span></div>';
    }
    $('drawer').innerHTML = '<div class="dh">' + art(p) + '<button class="x" data-act="close">' + ic('close') + '</button></div>' +
      '<div class="db"><h2>' + esc(p.name) + '</h2>' + lnk(p.path) + body + '</div>' +
      '<div class="dfoot">' + (b ? '<button class="btn" data-act="pause">Pause</button><button class="btn" data-newbrief="' + p.key + '">Edit prices</button><button class="btn g full" data-act="topup">' + ic('plus') + 'Add budget</button>' :
        '<button class="btn g full" data-newbrief="' + p.key + '">' + ic('plus') + 'Create brief</button>') + '</div>';
    show('drawer');
  }

  /* ---------------- modal: post a brief (the owner) ---------------- */
  var F;
  function briefForm(key) {
    var p = productOf(key || (F && F.prod) || S.mine[0].key), b = p.brief && briefOf(p.brief);
    if (!F || key) F = { prod: p.key, per_post: b ? b.per_post : 5, per_user: b ? b.per_user : 4, budget: b ? b.budget : 1000, days: 14 };
    $('modal').className = 'modal';
    $('modal').innerHTML = '<div class="mh"><span class="kick">Promo Market</span><h2>' + (b ? 'Edit brief' : 'Post a brief') + '</h2><button class="x" data-act="close">' + ic('close') + '</button></div>' +
      '<div class="mb"><div class="f">' +
        '<div class="fl"><label>Your product <span>built with Build it Better</span></label><div class="prods">' +
          S.mine.map(function (x) { return '<button class="prod' + (x.key === F.prod ? ' on' : '') + '" data-prod="' + x.key + '"><span class="pa">' + art(x) + '</span><b>' + esc(x.name) + '</b></button>'; }).join('') + '</div></div>' +
        '<div class="two"><div class="fl"><label>Per post <span>a post that stays up 7 days</span></label><div class="unit"><input class="in num" id="f-post" value="' + F.per_post + '"><em>USDC</em></div></div>' +
          '<div class="fl"><label>Per new user <span>after the 14-day check</span></label><div class="unit"><input class="in num" id="f-user" value="' + F.per_user + '"><em>USDC</em></div></div></div>' +
        '<div class="two"><div class="fl"><label>Budget</label><div class="unit"><input class="in num" id="f-budget" value="' + F.budget + '"><em>USDC</em></div></div>' +
          '<div class="fl"><label>Runs for</label><div class="seg" style="height:44px;align-items:center">' + [7, 14, 30].map(function (d) { return '<button data-days="' + d + '" class="' + (F.days === d ? 'on' : '') + '" style="height:36px;flex:1;justify-content:center">' + d + ' days</button>'; }).join('') + '</div></div></div>' +
        '<div class="calc" id="calc"></div>' +
      '</div><div class="prev"><span class="cap">How promoters see it</span><div id="pv"></div></div></div>' +
      '<div class="mf"><span class="note">' + ic('lock') + '<span id="lockn"></span></span><button class="btn gh" data-act="close">Cancel</button><button class="btn g" data-act="publish">Lock &amp; publish ' + ic('arrow') + '</button></div>';
    show('modal'); briefPreview();
  }
  function num(id, d) { var e = $(id); if (!e) return d; var v = parseInt(String(e.value).replace(/[^\d]/g, ''), 10); return isFinite(v) ? v : 0; }
  function readForm() { if (!$('f-post')) return; F.per_post = num('f-post', F.per_post); F.per_user = num('f-user', F.per_user); F.budget = num('f-budget', F.budget); }
  function briefPreview() {
    if (!$('pv')) return;
    readForm();
    var p = productOf(F.prod);
    var b = { key: 'preview', art: p.key, name: p.name, path: p.path, per_post: F.per_post, per_user: F.per_user, left: F.budget, days: F.days };
    $('pv').innerHTML = briefCard(b).replace(/data-take="preview"/, 'disabled').replace(/data-brief="preview"/g, '');
    $('calc').innerHTML = '<div><span>Pays for up to</span><b>' + fmt(F.per_post ? Math.floor(F.budget / F.per_post) : 0) + ' posts</b></div>' +
      '<div><span>or up to</span><b>' + fmt(F.per_user ? Math.floor(F.budget / F.per_user) : 0) + ' new users</b></div>';
    $('lockn').textContent = fmt(F.budget) + ' USDC locked from your balance · unspent returns ' + dShort(addDays(DAY, F.days));
  }
  function publish() {
    readForm();
    var p = productOf(F.prod), old = p.brief && briefOf(p.brief);
    if (old) { old.per_post = F.per_post; old.per_user = F.per_user; old.budget = Math.max(old.budget, F.budget); old.left = old.budget - old.spent; }
    else {
      S.briefs.unshift({ key: p.key, name: p.name, path: p.path, ask: '', per_post: F.per_post, per_user: F.per_user, budget: F.budget, posts: 0, users: 0, rejected: 0,
        visitors: 0, spent: 0, left: F.budget, days: F.days, age: 0, series: [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0], rejects: [], threads: 0 });
      p.brief = p.key;
    }
    hide(); route(); toast((old ? 'Brief updated · ' : 'Brief live · ') + fmt(F.budget) + ' USDC up for grabs');
  }

  /* ---------------- small modals: create a page, track a link; drawer: agent prompts ---------------- */
  function pageForm() {
    var tools = PM.queues.pages;
    $('modal').className = 'modal sm';
    $('modal').innerHTML = '<div class="mh"><span class="kick">Pages & links</span><h2>Create a page</h2><button class="x" data-act="close">' + ic('close') + '</button></div>' +
      '<div class="mb"><div class="f"><div class="fl"><label>Tool</label><div class="sel">' + ic('pages') + 'Gem Screener<span class="dim mono" style="font-size:11.5px;margin-left:8px">/gem-screener</span><span class="chev">' + ic('down') + '</span></div></div>' +
      '<div class="fl"><label>Headline <span>up to 120</span></label><input class="in" maxlength="120" placeholder="One line a reader stops for"></div>' +
      '<div class="fl"><label>Why it matters <span>up to 600</span></label><textarea class="in" maxlength="600" placeholder="One line on why it matters"></textarea></div>' +
      '<div class="rules"><div>' + ic('check') + '<span>You get a page with a tracked URL. Reuse it on every matching thread; make a new one only for a new tool. ' + tools.length + ' pages so far.</span></div></div></div></div>' +
      '<div class="mf"><span class="note"></span><button class="btn gh" data-act="close">Cancel</button><button class="btn g" data-act="made">Create page ' + ic('arrow') + '</button></div>';
    show('modal');
  }
  function trackForm() {
    $('modal').className = 'modal sm';
    $('modal').innerHTML = '<div class="mh"><span class="kick">Pages & links</span><h2>Track a link</h2><button class="x" data-act="close">' + ic('close') + '</button></div>' +
      '<div class="mb"><div class="f"><div class="fl"><label>Target <span>choose a surface or paste a URL</span></label><input class="in" placeholder="https://claude.ai/artifact/… or /exchange"></div>' +
      '<div class="two"><div class="fl"><label>Title <span>up to 200</span></label><input class="in" maxlength="200" placeholder="Shown on your dashboard"></div>' +
      '<div class="fl"><label>Kind</label><div class="seg" style="height:44px;align-items:center">' + ['artifact', 'tool', 'product', 'post', 'other'].map(function (k, i) { return '<button class="' + (i === 0 ? 'on' : '') + '" style="height:36px">' + k + '</button>'; }).join('') + '</div></div></div></div></div>' +
      '<div class="mf"><span class="note"></span><button class="btn gh" data-act="close">Cancel</button><button class="btn g" data-act="made">Create link ' + ic('arrow') + '</button></div>';
    show('modal');
  }
  function agentDrawer() {
    $('drawer').innerHTML = '<div class="dh plain"><button class="x" data-act="close">' + ic('close') + '</button></div><div class="db top">' +
      '<span class="kick">Stay in your chatbox</span><h2>From your own AI agent</h2><p class="ask">Copy into ChatGPT, Claude, Gemini, Meta Muse or any MCP/HTTP agent: it registers itself, no website, no install.</p>' +
      '<div class="sec">Promote · take briefs<span class="ln"></span><span class="chip g">new</span></div><pre class="code">' + codeHTML(PROMO_PROMPT) + '</pre><button class="btn c" data-copy="promo">' + ic('copy') + 'Copy prompt</button>' +
      '<div class="sec">Your agent’s key<span class="ln"></span></div><div class="posted"><input class="in" value="creator-agent"><button class="btn g" data-act="newkey">Create key</button></div><div class="onote" style="margin-top:6px">' + ic('lock') + PM.live.active_keys + ' active keys on this account</div>' +
      '<div class="sec">Trade · fund with your own USDC<span class="ln"></span></div><pre class="code">' + codeHTML(PM.live.trade_prompt) + '</pre><button class="btn" data-copy="trade">' + ic('copy') + 'Copy prompt</button></div>';
    show('drawer');
  }

  /* ---------------- overlay plumbing ---------------- */
  function show(which) { $('scrim').classList.add('on'); $(which).classList.add('on'); if (which === 'modal') $('drawer').classList.remove('on'); }
  function hide() { ['scrim', 'drawer', 'modal'].forEach(function (i) { $(i).classList.remove('on'); }); }

  /* ---------------- routing ---------------- */
  function route() {
    var h = (location.hash || '#market').slice(1).split('/'), r = h[0] || 'market';
    if (r === 'board' || r === 'brief') { r = 'market'; }
    var v = $('view');
    if (r === 'me') v.innerHTML = dash(h[1] || 'products');
    else if (r === 'profile') v.innerHTML = profile(h[1]);
    else v.innerHTML = market();
    document.querySelectorAll('#tnav a').forEach(function (a) { a.classList.toggle('on', a.getAttribute('data-r') === r); });
    var c = $('bcnt'); if (c) c.textContent = S.briefs.length;
    if (location.hash === '#board') { var b = $('board'); if (b) b.scrollIntoView(); } else window.scrollTo(0, 0);
    // #brief: the form, straight away (the Universe's Promo Market panel links here)
    if (location.hash === '#brief') briefForm();
  }
  window.addEventListener('hashchange', route);

  document.addEventListener('click', function (e) {
    if (e.target.closest('a.lnk')) return;                    // a product's own link opens the product, nothing else
    var t = e.target.closest('[data-act],[data-take],[data-sendoffer],[data-brief],[data-product],[data-newbrief],[data-copy],[data-s],[data-q],[data-qi],[data-ra],[data-row],[data-sort],[data-prod],[data-days],[data-qtab]');
    if (!t) { if (e.target.id === 'scrim') hide(); return; }
    var d = t.dataset;
    if (d.take) { e.stopPropagation(); take(d.take); return; }
    if (d.newbrief) { e.stopPropagation(); hide(); briefForm(d.newbrief); return; }
    if (d.sendoffer) { sendOffer(); return; }
    if (d.copy) {
      var k = d.copy, a = PM.radar[S.radar];
      var txt = k === 'promo' ? PROMO_PROMPT : k === 'trade' ? PM.live.trade_prompt : k === 'tweet' ? PM.live.tweet : k === 'radar-x' ? a.x_post : k === 'radar-r' ? a.reddit_title :
        k === 'radar-b' ? a.reddit_body : k === 'radar-t' ? a.tg_post : k.indexOf('link:') === 0 ? 'https://cymetica.com/c/' + k.slice(5) :
          k.indexOf('ask:') === 0 ? (briefOf(k.slice(4)) || {}).ask : k.indexOf('kit:') === 0 ? k.slice(4) :
            k.indexOf('kitpost:') === 0 ? communityKit(S.kitName || 'Bittensor', S.kitNarr || 'deai', S.kitTag || 'TAO').posts[+k.slice(8)] :
              k === 'kitreply' ? communityKit(S.kitName || 'Bittensor', S.kitNarr || 'deai', S.kitTag || 'TAO').reply : '';
      copy(txt, k === 'promo' || k === 'trade' ? 'Prompt' : k.indexOf('link:') === 0 ? 'Link' : 'Post'); return;
    }
    if (d.s) { S.sort = d.s; document.querySelectorAll('#bsort button').forEach(function (b) { b.classList.toggle('on', b.dataset.s === d.s); }); refreshBoard(); return; }
    if (d.qtab) { S.qtab = d.qtab; return; }
    if (d.q) { S.qtab = d.q; route(); return; }
    if (d.qi) { S.qsel[S.qtab] = +d.qi; var y = window.scrollY; route(); window.scrollTo(0, y); return; }
    if (d.ra) { S.radar = +d.ra; var y2 = window.scrollY; route(); window.scrollTo(0, y2); return; }
    if (d.row) { S.open[d.row] = !S.open[d.row]; var y3 = window.scrollY; route(); window.scrollTo(0, y3); return; }
    if (d.sort) { S.pgSort = d.sort; var y4 = window.scrollY; route(); window.scrollTo(0, y4); return; }
    if (d.prod) { readForm(); briefForm(d.prod); return; }
    if (d.days) { readForm(); F.days = +d.days; briefForm(); return; }
    if (d.product) { openProduct(d.product); return; }
    if (d.brief) { openBrief(d.brief); return; }
    switch (d.act) {
      case 'close': hide(); break;
      case 'brief': hide(); briefForm(); break;
      case 'agent': e.preventDefault(); agentDrawer(); break;
      case 'publish': publish(); break;
      case 'page': pageForm(); break;
      case 'track': trackForm(); break;
      case 'made': hide(); toast('Done · it shows on your dashboard'); break;
      case 'posted': $('prio-posted').hidden = false; break;
      case 'draft': $('draft').textContent = 'Drafting the reply for this thread…'; $('draftacts').hidden = false; break;
      case 'regen': $('draft').textContent = 'Drafting another reply…'; break;
      case 'copyreply': toast('Reply · copied'); break;
      case 'copypitch': toast('Pitch · copied'); break;
      case 'leadposted': toast('Marked posted · reward once the checker sees it'); break;
      case 'leadpage': pageForm(); break;
      case 'addpage': pageForm(); break;
      case 'mailto': toast('Your mail opens with the pitch'); break;
      case 'article': toast('Article saved'); break;
      case 'prioposted': toast('Marked posted · reward once the checker sees it'); break;
      case 'register': toast('Registered · reward once it carries your link'); break;
      case 'queuepost': toast('Post queued'); break;
      case 'record': toast('Saved where you posted it'); break;
      case 'newkey': toast('Key created · shown once, keep it private'); break;
      case 'skip': toast('Skipped'); break;
      case 'pitched': toast('Marked pitched'); break;
      case 'topup': toast('Add budget · the form opens with your card on file'); break;
      case 'pause': toast('Paused · promoters see it as closed'); break;
    }
  });
  document.addEventListener('input', function (e) {
    if (e.target.id === 'pgq') { S.pgQ = e.target.value; var pos = e.target.selectionStart, y = window.scrollY; route(); window.scrollTo(0, y); var q = $('pgq'); q.focus(); q.setSelectionRange(pos, pos); }
    else if (/^f-/.test(e.target.id)) briefPreview();
    else if (e.target.id === 'kit-name' || e.target.id === 'kit-tag') { S[e.target.id === 'kit-name' ? 'kitName' : 'kitTag'] = e.target.value; var id = e.target.id, pos = e.target.selectionStart, y = window.scrollY; route(); window.scrollTo(0, y); var el = $(id); el.focus(); el.setSelectionRange(pos, pos); }
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') hide(); });
  route();
})();
