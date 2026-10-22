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
  var R = PM.market.results;
  var S = {
    briefs: PM.market.briefs.slice(),
    taken: { gem: { slug: slugOf('gem'), at: '2026-10-21' } },  // a brief this creator took yesterday: the Briefs tab's sample
    sent: {},                                                   // post offers this creator sent, by brief
    filter: 'all', sort: 'pay', qtab: 'reddit', qsel: {}, radar: 0, open: {}, pgSort: 'uniq', pgQ: '', oplat: 'x'
  };
  function stats() {
    var b = S.briefs, of = function (c) { return sum(b.filter(function (x) { return x.cur === c; }), function (x) { return x.left; }); };
    return { usdc: of('USDC'), et10: of('ET10'), paid: sum(b, function (x) { return x.paid; }), held: sum(b, function (x) { return x.held; }),
      rejected: sum(b, function (x) { return x.rejected; }), offers: sum(b, function (x) { return x.offers.length; }), n: b.length };
  }
  function cap(s) { return s.charAt(0).toUpperCase() + s.slice(1); }

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
    company: I.company, launch: I.shield
  };
  var HUE = { gem: ['#00ff88', '#00cfff'], casino: ['#00cfff', '#00ff88'], chart: ['#00ff88', '#ff4444'], supply: ['#3b82f6', '#00cfff'], company: ['#00cfff', '#3b82f6'], launch: ['#00ff88', '#00cfff'] };
  function art(b) {
    var k = HUE[b.art || b.key] ? (b.art || b.key) : 'gem', c = HUE[k], id = 'g' + k + Math.random().toString(36).slice(2, 7), m = '', i, x, y;
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
      '<g transform="translate(11 11)" fill="none" stroke="' + c[0] + '" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><svg width="24" height="24" viewBox="0 0 20 20">' + (GLYPH[k] || '') + '</svg></g></g>' +
      '<text x="24" y="92" fill="#7f93ad" font-family="JetBrains Mono, monospace" font-size="10">cymetica.com' + esc(b.path || '') + '</text></svg>';
  }

  /* ---------------- pieces ---------------- */
  var KINDS = [['all', 'All'], ['active', 'Active user'], ['funded', 'Funded user'], ['paying', 'Paying user']];
  var PLAT = { x: ['X', 'followers'], youtube: ['YouTube', 'subscribers'], telegram: ['Telegram', 'channel members'] };
  function daysChip(b) { return b.days <= 2 ? '<span class="chip r">' + ic('clock') + b.days + 'd left</span>' : '<span class="chip">' + ic('clock') + b.days + 'd left</span>'; }
  function perTxt(b) { return 'per ' + R[b.kind].name; }
  function briefCard(b) {
    var pct = Math.round(b.left / b.budget * 100), taken = S.taken[b.key], k = R[b.kind];
    return '<article class="bc" data-brief="' + b.key + '">' +
      '<div class="img">' + art(b) + '<div class="dl">' + daysChip(b) + '</div></div>' +
      '<div class="bd"><div class="nm"><b>' + esc(b.name) + '</b><span class="by2">by ' + esc(b.buyer) + '</span></div>' +
      '<div class="ask">' + esc(b.ask) + '</div>' +
      '<div class="pay"><span class="v">' + fmt(b.price) + ' <small>' + b.cur + '</small></span><span class="per" data-tip="' + esc(cap(k.rule)) + '">' + perTxt(b) + '</span></div>' +
      '<div class="facts"><span class="chip g" data-tip="Results that passed every check and the hold">' + ic('check') + b.paid + ' paid</span>' +
        '<span class="chip r" data-tip="Sign-ups that failed a check: never paid">' + ic('shield') + b.rejected + ' rejected</span>' +
        '<span class="chip" data-tip="Each result waits this long before it is paid">' + ic('lock') + b.hold + 'd hold</span></div>' +
      '<div><div class="bar"><i style="width:' + pct + '%"></i></div><div class="meta" style="margin-top:7px"><span><b>' + short(b.left) + '</b> of ' + short(b.budget) + ' ' + b.cur + ' left</span><span>' +
        (b.offers.length ? '<b>' + b.offers.length + '</b> post offer' + (b.offers.length > 1 ? 's' : '') : 'no post offers yet') + '</span></div></div>' +
      '<div class="ft"><button class="btn sm gh" data-offer="' + b.key + '" data-tip="Quote a price for one post to your audience">' + ic('reply') + 'Offer a post</button>' +
        (taken ? '<button class="btn sm gh" data-brief="' + b.key + '">' + ic('check') + 'Taken · open</button>' : '<button class="btn sm g" data-take="' + b.key + '">Take it ' + ic('arrow') + '</button>') + '</div></div></article>';
  }
  function sortBriefs(list) {
    var l = list.filter(function (b) { return S.filter === 'all' || b.kind === S.filter; });
    // ET10 and USDC are not compared with each other: USDC prices first, by size, then ET10
    var f = { pay: function (a, b) { return (b.cur === 'USDC') - (a.cur === 'USDC') || b.price - a.price; }, ending: function (a, b) { return a.days - b.days; }, newest: function (a, b) { return a.age - b.age; } }[S.sort];
    return l.sort(f);
  }
  function boardHead(title) {
    return '<div class="bhead"><h2>' + title + '</h2><span class="cnt" id="bcnt"></span><span class="sp"></span>' +
      '<div class="seg" id="bfilter">' + KINDS.map(function (k) { return '<button data-f="' + k[0] + '" class="' + (S.filter === k[0] ? 'on' : '') + '">' + k[1] + '</button>'; }).join('') + '</div>' +
      '<div class="seg" id="bsort">' + [['pay', 'Best paid'], ['ending', 'Ending soon'], ['newest', 'Newest']].map(function (s) { return '<button data-s="' + s[0] + '" class="' + (S.sort === s[0] ? 'on' : '') + '">' + s[1] + '</button>'; }).join('') + '</div></div>';
  }
  function board() { var l = sortBriefs(S.briefs.slice()); return '<div class="grid" id="bgrid">' + l.map(briefCard).join('') + '</div>'; }
  function refreshBoard() { var g = $('bgrid'); if (!g) return; var l = sortBriefs(S.briefs.slice()); g.innerHTML = l.map(briefCard).join(''); var c = $('bcnt'); if (c) c.textContent = l.length; }
  // the way from a click to a paid result, as five numbers
  function funnel(f) {
    var steps = [['Clicks', f.clicks, ''], ['New accounts', f.accounts, ''], ['Qualified', f.qualified, 'c'], ['In hold', f.held, ''], ['Paid', f.paid, 'g']];
    return '<div class="fun">' + steps.map(function (s, i) { return (i ? '<span class="fa">' + ic('chev') + '</span>' : '') + '<div class="fs ' + s[2] + '"><b>' + fmt(s[1]) + '</b><span>' + s[0] + '</span></div>'; }).join('') + '</div>';
  }

  var PROMO_PROMPT = 'Read https://cymetica.com/llms.txt and https://cymetica.com/.well-known/mcp.json.\n' +
    'Then register me as an agent: POST https://cymetica.com/mcp/v1/register\n' +
    'with {"name": "my-agent", "contact_email": "", "intended_use": "promotion"}.\n' +
    'Save the returned api_key privately and send it as the X-API-Key header on every later call.\n' +
    'Then list the open promo briefs: GET https://cymetica.com/api/v1/promo/briefs?sort=pay\n' +
    'Each one pays per verified new user, never per click: read what counts as a result in each.\n' +
    'Show me the three best paid briefs I can take.\n' +
    'Wait for my go before taking a brief or posting anything.';
  function codeHTML(t) { return esc(t).replace(/(https:\/\/[^\s]+)/g, '<span class="u">$1</span>'); }

  /* ---------------- the market (/creator-dashboard) ---------------- */
  function market() {
    var st = stats(), h = PM.market.house, m = PM.live.measure.match(/([\d.]+) clicks per posted link per day.*?over ([\d,]+) links, ([\d,]+) unique visitors/);
    var all = st.paid + st.held + st.rejected;
    return '<div class="wrap">' +
      '<section class="hero"><div>' +
        '<span class="chip g"><i class="live"></i>PROMO MARKET</span>' +
        '<h1>Get real users.<br><em>Pay only for results.</em></h1>' +
        '<p class="lead">Show your product and lock a budget. Creators, agents and firms compete to bring you new users; you pay for each one that passes the checks.</p>' +
        '<div class="ctas"><button class="btn g lg" data-act="brief">' + ic('plus') + 'Post a brief</button>' +
        '<a class="btn c lg" href="#board">Find a brief to take ' + ic('arrow') + '</a>' +
        '<button class="btn gh lg" data-act="agent">' + ic('agent') + 'From your AI agent</button></div></div>' +
      '<div class="stats">' +
        '<div class="stat" style="--c:#00ff88"><div class="k">' + ic('coin') + 'On offer</div><div class="v pos">' + short(st.usdc) + '<small>USDC</small></div><div class="s">+ ' + short(st.et10) + ' ET10 · ' + st.n + ' briefs</div></div>' +
        '<div class="stat"><div class="k">' + ic('check') + 'Results paid</div><div class="v">' + fmt(st.paid) + '</div><div class="s">' + st.held + ' in hold now</div></div>' +
        '<div class="stat" style="--c:#ff4444"><div class="k">' + ic('shield') + 'Rejected by the checks <span class="i" data-tip="Sign-ups that failed a check (same device, a wallet the promoter funded, no proof of person, gone before the hold ended) and were never paid">i</span></div><div class="v neg">' + fmt(st.rejected) + '</div><div class="s">' + Math.round(st.rejected / all * 100) + '% of sign-ups, never paid</div></div>' +
        '<div class="stat" style="--c:#3b82f6"><div class="k">' + ic('uniq') + 'Visitors from creators <span class="i tipr" data-tip="Live measure across all creators: ' + m[1] + ' clicks per posted link per day">i</span></div><div class="v">' + fmt(+m[3]) + '</div><div class="s">last 30 days · ' + fmt(+m[2]) + ' links</div></div>' +
      '</div></section>' +
      '<section class="steps">' +
        step('briefs', 'Show your product', 'lock a budget, name the result', 'The budget is locked when the brief opens. What is not spent comes back when it ends.') +
        step('link', 'Anyone promotes', 'a tracked link each', 'Creators, AI agents and marketing firms take the brief; each gets its own cymetica.com/c/ link, and one per thread it replies in.') +
        step('shield', 'Every result checked', 'new person · real action · hold', 'A new person, through the link, doing the brief’s action, with proof of person, held 14 or 30 days.') +
        step('coin', 'Paid per result', 'or per post, if you accept an offer', 'A result is paid from the budget when its hold ends. An influencer’s post offer is paid once the post has stayed up 7 days.') +
      '</section>' +
      '<section class="checks"><div class="ch2"><span class="kick">What counts as a result</span><h2>Cheaper to earn than to fake.</h2><p>Every rule is checked by the platform, for every result, before a cent moves.</p></div><div class="cgrid">' +
        chk('uniq', 'A new person', 'A first account, first visit through the promoter’s link, within 7 days.') +
        chk('shield', 'One person, one result', 'Device, network, wallet and phone are matched across every result.') +
        chk('today', 'A real action', 'The brief’s own: 3 days of use, a $20 deposit of own funds, or a paid plan.') +
        chk('telegram', 'Proof of person', 'A Telegram account or a wallet with on-chain history, one per result.') +
        chk('lock', 'Held, then paid', '14 or 30 days in escrow, clawed back if it turns out fake.') +
        chk('coin', 'Promoters stake', 'Agents and new promoters stake ET10 to take a brief; a farmed result burns it.') +
      '</div></section>' +
      '<section id="board">' + boardHead('Open briefs') + board() + '</section>' +
      '<section class="house"><div class="badge">' + ic('coin') + '</div><div><span class="kick">Per post · Cymetica’s own programme</span>' +
        '<h3>Any Cymetica tool, in the thread that asks for it</h3><div class="row">' +
        h.outlets.map(function (o) { return '<span class="chip">' + ic(o) + OUT[o] + '</span>'; }).join('') +
        '<span class="chip g">' + fmt(h.replied) + ' replies posted</span><span class="chip c">' + fmt(h.open_threads) + ' threads waiting</span></div></div>' +
        '<div class="pay"><div class="v">' + fmt(h.pay) + ' ET10 <small>+ ' + fmt(h.pay2) + ' ETLP / post</small></div><a class="btn g" href="#me/queues" style="margin-top:12px">Open the queue ' + ic('arrow') + '</a></div></section>' +
      '<section class="duo">' +
        '<div class="panel"><span class="kick">For companies</span><h3>Show your product. Name a budget.</h3><p>Anyone may bring you users; you choose what a result is.</p>' +
          '<div class="pledge"><div>' + ic('lock') + 'Budget locked when the brief opens; unspent comes back</div><div>' + ic('shield') + 'Paid per verified new user, never per click</div><div>' + ic('reply') + 'Influencers may quote a price per post; you accept or decline</div></div>' +
          '<div class="ctas" style="display:flex;gap:10px"><button class="btn g" data-act="brief">' + ic('plus') + 'Post a brief</button><a class="btn gh" href="https://cymetica.com/company" target="_blank" rel="noopener" data-tip="A Marketing department writes the briefs for your products; each one waits for your approval">' + ic('company') + 'Let your company’s Marketing do it</a></div></div>' +
        '<div class="panel"><span class="kick">For agents and firms</span><h3>Promote from your own AI agent</h3><p>Paste into Claude, ChatGPT, Gemini or any MCP agent.</p>' +
          '<pre class="code">' + codeHTML(PROMO_PROMPT) + '</pre><button class="btn c" data-copy="promo">' + ic('copy') + 'Copy prompt</button></div>' +
      '</section>' +
      '<footer class="foot"><a href="#profile">Creator pages</a><a href="#me">Your dashboard</a><a href="https://cymetica.com/company" target="_blank" rel="noopener">Start a company ↗</a><span style="margin-left:auto">Data read ' + DAY + ' · briefs are samples</span></footer>' +
    '</div>';
  }
  function step(i, b, s, tip) { return '<div class="step" data-tip="' + esc(tip) + '"><span class="n">' + ic(i) + '</span><div><b>' + b + '</b><span>' + s + '</span></div></div>'; }
  function chk(i, b, s) { return '<div class="chk"><span class="n">' + ic(i) + '</span><div><b>' + b + '</b><span>' + s + '</span></div></div>'; }

  /* ---------------- the creator's dashboard ---------------- */
  var TABS = [['today', 'Today', 'today'], ['briefs', 'Briefs', 'briefs'], ['queues', 'Queues', 'queues'], ['pages', 'Pages & links', 'pages'], ['rewards', 'Rewards', 'coin']];
  function dash(tab) {
    var me = PM.me, rw = PM.rewards.summary, q = PM.queues;
    var counts = { briefs: Object.keys(S.taken).length, queues: q.reddit.stats.new + q.x.stats.new + q.press.stats.open, pages: me.summary.links, rewards: rw.paid };
    var title = { today: 'Today', briefs: 'Briefs', queues: 'Queues', pages: 'Pages & links', rewards: 'Rewards' }[tab];
    return '<div class="app"><aside class="rail">' +
      '<div class="me"><span class="av lg">E</span><div><b>' + esc(me.username) + '</b><span>Creator · ' + me.summary.links + ' pages</span></div></div>' +
      '<nav class="rnav">' + TABS.map(function (t) {
        var n = counts[t[0]], hot = t[0] === 'queues';
        return '<a href="#me/' + t[0] + '" class="' + (t[0] === tab ? 'on' : '') + '">' + ic(t[2]) + t[1] + (n != null ? '<span class="n' + (hot ? ' hot' : '') + '">' + short(n) + '</span>' : '') + '</a>';
      }).join('') + '</nav>' +
      '<div class="rlinks"><a href="#market">' + ic('briefs') + 'Promo Market</a><a href="#profile/me">' + ic('ext') + 'Your public page</a><a href="#" data-act="agent">' + ic('agent') + 'Agent prompts</a></div>' +
      '<div class="earn"><div class="k">Earned · ' + rw.paid + ' posts</div><div class="v">' + fmt(rw.et10) + ' <small>ET10</small></div><div class="s">+ ' + fmt(rw.etlp) + ' ETLP</div></div>' +
      '</aside><section class="main">' +
      '<div class="ph"><h1>' + title + '</h1><span class="sub">' + esc(me.username) + ' · ' + dShort(new Date(DAY + 'T12:00:00Z')) + ' 2026</span><span class="sp"></span>' +
        (tab === 'pages' ? '<button class="btn sm" data-act="track">' + ic('link') + 'Track a link</button><button class="btn sm c" data-act="page">' + ic('plus') + 'Create a page</button>' :
          '<button class="btn sm" data-act="agent">' + ic('agent') + 'From your agent</button>') + '</div>' +
      ({ today: today, briefs: myBriefs, queues: queues, pages: pages, rewards: rewards }[tab])() +
      '</section></div>';
  }
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
    var best = S.briefs.filter(function (b) { return b.cur === 'USDC'; }).sort(function (a, b) { return b.price - a.price; }).slice(0, 3);
    var tx = esc(L.tweet).replace(/(https:\/\/\S+)/g, '<span class="u">$1</span>').replace(/(#\w+)/g, '<span class="h">$1</span>');
    var nextPress = q.press.items.slice().sort(function (a, b) { return a.hours - b.hours; })[0];
    return kpis(PM.me) + '<div class="cols"><div>' +
      '<div class="card"><div class="ch"><span class="chip g"><i class="live"></i>Top priority</span><h3>Post this on X today</h3><span class="sp"></span><span class="chip" data-tip="Two posts share this slot and alternate daily; it changes at 00:00 UTC">post ' + esc(L.tweet_nth) + '</span></div>' +
        '<div class="tw"><div><div class="post"><div class="ah"><span class="av">E</span><b>' + esc(PM.me.username) + '</b><span>· now</span></div><div class="tx">' + tx + '</div></div>' +
        '<div class="acts"><button class="btn sm c" data-copy="tweet">' + ic('copy') + 'Copy</button><a class="btn sm" href="https://x.com/intent/post" target="_blank" rel="noopener">' + ic('x') + 'Open in X</a><button class="btn sm g" data-act="posted">' + ic('check') + 'Mark posted</button>' +
        '<span class="reward" data-tip="Paid once the checker sees the post displayed">+1,000 ET10 · +1,000 ETLP</span></div></div>' +
        '<div class="og" data-tip="X may not show the link card right away: attach this graphic to the post">' + art(S.briefs.filter(function (x) { return x.key === 'gem'; })[0]) + '<div>Save graphic · cymetica.com/gem-screener</div></div></div></div>' +
      '<div class="card"><div class="ch"><h3>Briefs paying per result</h3><span class="chip c">new users, not clicks</span><span class="sp"></span><a class="btn sm gh" href="#me/briefs">All briefs ' + ic('arrow') + '</a></div>' +
        '<div class="strip">' + best.map(function (b) {
          return '<div class="sb" data-brief="' + b.key + '"><div class="art">' + art(b) + '</div><div><b>' + esc(b.name) + '</b><div class="pv">' + fmt(b.price) + ' <small>' + b.cur + ' per ' + R[b.kind].short + '</small></div><div class="m">' + b.days + 'd left · ' + short(b.left) + ' ' + b.cur + ' left</div></div></div>';
        }).join('') + '</div></div>' +
      '</div><div>' +
      '<div class="card"><div class="ch"><h3>Queues</h3><span class="sp"></span><a class="btn sm gh" href="#me/queues">Open ' + ic('arrow') + '</a></div><div class="q4">' +
        qt('reddit', 'Reddit', 'asking what a page answers', q.reddit.stats.new, 'new', 'reddit') +
        qt('x', 'X', q.x.stats.claimed + ' claimed · ' + fmt(q.x.stats.replied) + ' replied', q.x.stats.new, 'new', 'x') +
        qt('press', 'Press', 'next deadline in ' + Math.round(nextPress.hours) + ' h', q.press.stats.open, 'open', 'press') +
        qt('radar', 'Radar apps', 'where their users already are', PM.radar.length, 'apps', 'radar') +
      '</div></div>' +
      '<div class="card"><div class="ch"><h3>Your best pages</h3><span class="sp"></span><a class="btn sm gh" href="#me/pages">All ' + ic('arrow') + '</a></div><div class="tops">' +
        top.map(function (l) { return '<div class="tp"><div><b>' + esc(l.title) + '</b><span>' + fmt(l.reads) + ' reads · ' + fmt(l.likes) + ' likes</span></div>' + spark(l.series) + '<div class="u">' + l.uniq + '</div></div>'; }).join('') +
      '</div></div></div></div>';
  }
  function qt(icon, name, sub, v, unit, tab) {
    return '<a class="qt" href="#me/queues" data-qtab="' + tab + '"><span class="ic">' + ic(icon) + '</span><div><b>' + name + '</b><span>' + sub + '</span></div><div class="v">' + short(v) + '<small>' + unit + '</small></div></a>';
  }
  // this creator's share of a brief's funnel: one fixed share of the brief's own numbers (a sample, from the one model)
  function mine(b) {
    var f = b.funnel, s = function (n, k) { return Math.round(n * k); };
    return { clicks: s(f.clicks, 0.08), accounts: s(f.accounts, 0.06), qualified: s(f.qualified, 0.05), held: s(f.held, 0.05), paid: s(f.paid, 0.05) };
  }
  function myBriefs() {
    var keys = Object.keys(S.taken);
    var rows = keys.map(function (k) {
      var b = S.briefs.filter(function (x) { return x.key === k; })[0], t = S.taken[k]; if (!b) return '';
      var m = mine(b), rej = m.accounts - m.qualified;
      return '<div class="card cmb"><div class="ch"><h3>' + esc(b.name) + '</h3><span class="chip g">' + fmt(b.price) + ' ' + b.cur + ' ' + perTxt(b) + '</span><span class="chip">' + ic('lock') + b.hold + 'd hold</span><span class="sp"></span>' +
          '<span class="mono acc" style="font-size:12.5px">cymetica.com/c/' + t.slug + '</span><button class="btn sm c" data-copy="link:' + t.slug + '">' + ic('copy') + 'Copy link</button><a class="btn sm" href="#me/queues">' + ic('queues') + 'Threads for it</a></div>' +
        '<div class="mrow">' + funnel(m) + '<div class="earned"><span>Earned</span><b>' + fmt(m.paid * b.price) + ' <small>' + b.cur + '</small></b><em>' + fmt(m.held * b.price) + ' ' + b.cur + ' in hold · ' + rej + ' not counted</em></div></div></div>';
    }).join('');
    var sent = Object.keys(S.sent).map(function (k) {
      var o = S.sent[k], b = S.briefs.filter(function (x) { return x.key === k; })[0];
      return '<div class="ofr">' + ic(o.platform) + '<b>' + esc(b.name) + '</b><span>' + esc(PLAT[o.platform][0]) + ' · ' + esc(o.handle || 'your account') + '</span><b class="pos">' + fmt(o.price) + ' ' + b.cur + '</b><span class="chip c">waiting for the owner</span></div>';
    }).join('');
    return '<div class="sech"><h2>Taken by you</h2><span class="dim mono">paid per verified new user · the house programme needs no taking</span></div>' + rows +
      '<div class="card cmb"><div class="ch"><h3>Your post offers</h3><span class="chip">' + Object.keys(S.sent).length + '</span><span class="sp"></span><span class="dim mono" style="font-size:12px">Paid once the post has stayed up 7 days</span></div>' +
        (sent || '<div class="draft">None yet. Have an audience? Quote a price for one post on any brief: the owner accepts or declines.</div>') + '</div>' +
      boardHead('Open briefs') + board();
  }
  function queues() {
    var q = PM.queues, t = S.qtab;
    var seg = '<div class="seg" id="qseg" style="margin-bottom:16px">' + [['reddit', 'Reddit', q.reddit.stats.new], ['x', 'X', q.x.stats.new], ['press', 'Press', q.press.stats.open], ['radar', 'Radar apps', PM.radar.length]].map(function (s) {
      return '<button data-q="' + s[0] + '" class="' + (t === s[0] ? 'on' : '') + '">' + ic(s[0]) + s[1] + ' <span class="n">' + short(s[2]) + '</span></button>';
    }).join('') + '</div>';
    if (t === 'radar') return seg + radarView();
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
      return '<div class="card qd"><div class="ch"><span class="chip">' + ic('press') + esc(it.outlet) + '</span><span class="chip">Tier ' + it.tier + '</span><span class="sp"></span><span class="chip ' + (it.hours < 24 ? 'r' : '') + '">' + ic('clock') + Math.round(it.hours) + ' h left</span></div>' +
        '<h3 style="margin:0 0 12px;font:20px var(--display)">' + esc(it.subject) + '</h3><div class="m" style="display:flex;gap:6px;flex-wrap:wrap;margin-bottom:16px">' + it.topics.map(function (x) { return '<span class="chip">' + esc(x.replace(/_/g, ' ')) + '</span>'; }).join('') + '</div>' +
        '<div class="sec">Answer with a page<span class="ln"></span></div><div class="sel">' + ic('pages') + 'Build a Company<span class="chev">' + ic('down') + '</span></div>' +
        '<div class="acts"><button class="btn c" data-act="pitched">' + ic('mail') + 'Pitch by email</button><button class="btn gh" data-act="skip">' + ic('skip') + 'Skip</button></div></div>';
    }
    var rule = t === 'reddit' ? kit.reddit_rule : kit.x_rule;
    return '<div class="card qd"><div class="ch">' + (t === 'reddit' ? '<span class="chip">' + ic('reddit') + 'r/' + esc(it.sub) + '</span>' : '<span class="chip">' + ic('x') + esc(it.group) + '</span>') +
      '<span class="sp"></span><span class="dim mono" style="font-size:11.5px">' + esc(it.at) + ' UTC</span></div>' +
      (t === 'reddit' ? '<h3 style="margin:0 0 12px;font:19px/1.3 var(--display)">' + esc(it.title) + '</h3>' : '') +
      '<div class="body">' + esc(it.body) + '</div>' +
      '<div class="sec">Reply with this page<span class="ln"></span></div><div class="sel">' + ic('pages') + esc(it.tool) + '<span class="dim mono" style="font-size:11.5px;margin-left:8px">' + esc(it.path) + '</span><span class="chev">' + ic('down') + '</span></div>' +
      '<div class="acts"><button class="btn g" data-act="draft">' + ic('reply') + 'Reply with this page</button><button class="btn gh" data-act="skip">' + ic('skip') + 'Skip</button></div>' +
      '<div class="draft" id="draft" style="margin-top:12px">The reply opens on this thread’s own question, adds one line about the page and ends with a tracked link made for this thread.</div>' +
      '<div class="rules" style="margin-top:14px"><div>' + ic('check') + esc(rule) + '</div></div></div>';
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

  /* ---------------- drawer: one brief ---------------- */
  function openBrief(key, mode) {
    var b = S.briefs.filter(function (x) { return x.key === key; })[0]; if (!b) return;
    var t = S.taken[key], k = R[b.kind], all = b.paid + b.held + b.rejected;
    var threads = PM.queues.reddit.items.concat(PM.queues.x.items).filter(function (l) { return l.path === b.path; });
    var maxRej = Math.max.apply(null, b.rejects.map(function (r) { return r[1]; })) || 1;
    var offers = b.offers.map(function (o) {
      var st = { live: ['c', 'up · paid after 7 days'], pending: ['', 'waiting for the owner'], paid: ['g', 'paid'] }[o.state] || ['', o.state];
      return '<div class="ofr">' + ic(o.platform) + '<b>' + short(o.audience) + '</b><span>' + PLAT[o.platform][1] + ' on ' + PLAT[o.platform][0] + '</span><b class="pos">' + fmt(o.price) + ' ' + b.cur + '</b><span class="chip ' + st[0] + '">' + st[1] + '</span></div>';
    }).join('');
    $('drawer').innerHTML = '<div class="dh">' + art(b) + '<button class="x" data-act="close">' + ic('close') + '</button></div>' +
      '<div class="db"><div style="display:flex;gap:8px;align-items:center"><span class="chip">by ' + esc(b.buyer) + '</span>' + daysChip(b) + '<span class="chip">' + ic('clock') + 'ends ' + dShort(addDays(DAY, b.days)) + '</span></div>' +
      '<h2>' + esc(b.name) + '</h2><p class="ask">' + esc(b.ask) + '</p>' +
      '<div class="pbx"><div><span class="v">' + fmt(b.price) + ' <small>' + b.cur + '</small></span><span class="per">' + perTxt(b) + '</span></div><span class="chip">' + ic('lock') + b.hold + '-day hold</span></div>' +
      '<p class="rule">' + esc(cap(k.rule)) + '.</p>' +
      (t ? '<div class="taken">' + ic('check') + '<div style="flex:1"><b>' + (mode === 'took' ? 'Taken. Your link for this brief:' : 'You took this brief') + '</b><span class="mono">cymetica.com/c/' + t.slug + '</span></div><button class="btn sm c" data-copy="link:' + t.slug + '">' + ic('copy') + 'Copy</button></div>' : '') +
      '<div class="sec">This brief so far<span class="ln"></span></div>' + funnel(b.funnel) +
      '<div class="bar" style="margin-top:14px"><i style="width:' + Math.round(b.left / b.budget * 100) + '%"></i></div><div class="meta2"><span><b>' + fmt(b.left) + '</b> of ' + fmt(b.budget) + ' ' + b.cur + ' left · locked</span><span><b>' + fmt(b.spent) + '</b> paid · ' + fmt(b.committed) + ' due</span></div>' +
      '<div class="sec">Not paid · ' + b.rejected + ' of ' + all + ' sign-ups<span class="ln"></span></div><div class="rej">' + b.rejects.map(function (r) {
        return '<div><span>' + esc(cap(r[0])) + '</span><i style="width:' + Math.round(r[1] / maxRej * 100) + '%"></i><b>' + r[1] + '</b></div>'; }).join('') + '</div>' +
      '<div class="sec">What counts as a result<span class="ln"></span></div><div class="rules">' +
        '<div>' + ic('uniq') + '<span><b style="color:var(--text)">A new person,</b> first account and first visit through your link, within 7 days.</span></div>' +
        '<div>' + ic('today') + '<span><b style="color:var(--text)">The action:</b> ' + esc(k.rule.replace(/^a new account that /, '')) + '.</span></div>' +
        '<div>' + ic('shield') + '<span><b style="color:var(--text)">One person, one result:</b> device, network, wallet and phone matched; proof of person by Telegram or a wallet with history.</span></div>' +
        '<div>' + ic('lock') + '<span><b style="color:var(--text)">Held ' + b.hold + ' days,</b> then paid; clawed back if it turns out fake. Self-referrals and wallets you funded never count.</span></div></div>' +
      '<div class="sec" id="offers">Post offers<span class="ln"></span><span class="chip">' + b.offers.length + '</span></div>' +
        (offers ? '<div class="ofl">' + offers + '</div>' : '') +
        '<div class="ofrm' + (mode === 'offer' ? ' hl' : '') + '"><div class="seg" id="oplat">' + Object.keys(PLAT).map(function (p) { return '<button data-oplat="' + p + '" class="' + (S.oplat === p ? 'on' : '') + '">' + ic(p) + PLAT[p][0] + '</button>'; }).join('') + '</div>' +
          '<div class="two"><input class="in" id="o-handle" placeholder="Your account, e.g. @handle"><div class="unit"><input class="in num" id="o-price" placeholder="Price for one post"><em>' + b.cur + '</em></div></div>' +
          '<div class="onote">' + ic('shield') + 'Your audience is read from the account you link. Paid once the post has stayed up 7 days.</div>' +
          '<button class="btn c" data-sendoffer="' + b.key + '">' + ic('reply') + 'Send offer</button></div>' +
      (threads.length ? '<div class="sec">Threads asking for it now<span class="ln"></span><span class="chip c">' + threads.length + '</span></div><div class="thr">' + threads.slice(0, 3).map(function (l) { return '<a href="#me/queues">' + ic(l.sub ? 'reddit' : 'x') + '<span>' + esc(l.title || l.body) + '</span><b class="acc mono">' + l.rel + '</b></a>'; }).join('') + '</div>' : '') +
      '</div>' +
      '<div class="dfoot">' + (t ? '<a class="btn g full" href="#me/briefs">' + ic('briefs') + 'Your results for it</a>' :
        '<button class="btn gh" data-act="close">Not now</button><button class="btn g full" data-take="' + b.key + '">Take this brief ' + ic('arrow') + '</button>') + '</div>';
    show('drawer');
    if (mode === 'offer') { var o = $('offers'); if (o) setTimeout(function () { o.scrollIntoView({ block: 'start' }); }, 60); }
  }
  function take(key) {
    if (!S.taken[key]) S.taken[key] = { slug: slugOf(key + '·' + PM.me.username), at: DAY };
    openBrief(key, 'took'); refreshBoard(); toast('Brief taken · your tracked link is ready');
  }
  function sendOffer(key) {
    var b = S.briefs.filter(function (x) { return x.key === key; })[0], price = num('o-price', 0);
    if (!price) { toast('Name a price for the post'); return; }
    S.sent[key] = { platform: S.oplat, handle: ($('o-handle') || {}).value, price: price };
    b.offers = b.offers.concat([{ platform: S.oplat, audience: 0, price: price, state: 'pending', mine: true }]);
    openBrief(key); toast('Offer sent · the owner accepts or declines');
  }

  /* ---------------- modal: post a brief ---------------- */
  var F;
  function briefForm() {
    var prods = PM.market.briefs.filter(function (b) { return b.buyer === 'Cymetica QA'; });
    F = F || { prod: prods[0].key, ask: prods[0].ask, kind: prods[0].kind, price: prods[0].price, cur: prods[0].cur, hold: 14, offers: true, maxOffer: 500, budget: 2000, days: 14, as: 'Cymetica QA' };
    $('modal').className = 'modal';
    $('modal').innerHTML = '<div class="mh"><span class="kick">Promo Market</span><h2>Post a brief</h2><button class="x" data-act="close">' + ic('close') + '</button></div>' +
      '<div class="mb"><div class="f">' +
        '<div class="fl"><label>What to promote <span>your products, or any cymetica.com page</span></label><div class="prods">' +
          prods.map(function (x) { return '<button class="prod' + (x.key === F.prod ? ' on' : '') + '" data-prod="' + x.key + '"><span class="pa">' + art(x) + '</span><b>' + esc(x.name) + '</b></button>'; }).join('') +
          '<button class="prod" data-act="anyurl"><span class="chip" style="height:30px">' + ic('link') + '</span><b>Any page</b></button></div></div>' +
        '<div class="fl"><label>The ask <span id="askn">' + F.ask.length + ' / 120</span></label><input class="in" id="f-ask" maxlength="120" value="' + esc(F.ask) + '"></div>' +
        '<div class="fl"><label>Pay for <span>what one result is</span></label><div class="kinds">' + Object.keys(R).map(function (k) {
          return '<button class="kc' + (F.kind === k ? ' on' : '') + '" data-kind="' + k + '"><b>' + cap(R[k].name) + '</b><span>' + esc(cap(R[k].rule.replace(/^a new account that /, ''))) + '</span></button>'; }).join('') + '</div></div>' +
        '<div class="three"><div class="fl"><label>Price per result</label><div class="unit"><input class="in num" id="f-price" value="' + F.price + '"><em>' + F.cur + '</em></div></div>' +
          '<div class="fl"><label>Pay in</label><div class="seg" style="height:44px;align-items:center">' + ['USDC', 'ET10'].map(function (c) { return '<button data-cur="' + c + '" class="' + (F.cur === c ? 'on' : '') + '" style="height:36px;padding:0 16px">' + c + '</button>'; }).join('') + '</div></div>' +
          '<div class="fl"><label>Hold <span class="i" data-tip="How long a result waits before it is paid; a fake found in that time is not paid">i</span></label><div class="seg" style="height:44px;align-items:center">' + [14, 30].map(function (d) { return '<button data-hold="' + d + '" class="' + (F.hold === d ? 'on' : '') + '" style="height:36px;padding:0 14px">' + d + ' days</button>'; }).join('') + '</div></div></div>' +
        '<div class="two"><div class="fl"><label>Budget</label><div class="unit"><input class="in num" id="f-budget" value="' + F.budget + '"><em>' + F.cur + '</em></div></div>' +
          '<div class="fl"><label>Runs for</label><div class="seg" style="height:44px;align-items:center">' + [7, 14, 30].map(function (d) { return '<button data-days="' + d + '" class="' + (F.days === d ? 'on' : '') + '" style="height:36px;flex:1;justify-content:center">' + d + ' days</button>'; }).join('') + '</div></div></div>' +
        '<div class="two"><div class="fl"><label>Post offers <span>influencers quote a price</span></label><div class="seg" style="height:44px;align-items:center">' + [[true, 'Take offers'], [false, 'Results only']].map(function (o) { return '<button data-acc="' + o[0] + '" class="' + (F.offers === o[0] ? 'on' : '') + '" style="height:36px;flex:1;justify-content:center">' + o[1] + '</button>'; }).join('') + '</div></div>' +
          (F.offers ? '<div class="fl"><label>Up to, per post</label><div class="unit"><input class="in num" id="f-max" value="' + F.maxOffer + '"><em>' + F.cur + '</em></div></div>' : '<div></div>') + '</div>' +
        '<div class="fl"><label>Posted by <span>a department’s brief waits for your approval</span></label><div class="seg" style="align-self:start">' + ['Cymetica QA', PM.me.username].map(function (a) { return '<button data-as="' + esc(a) + '" class="' + (F.as === a ? 'on' : '') + '">' + ic(a === PM.me.username ? 'uniq' : 'company') + esc(a) + '</button>'; }).join('') + '</div></div>' +
      '</div><div class="prev"><span class="cap">How it shows on the board</span><div id="pv"></div><div class="calc" id="calc"></div></div></div>' +
      '<div class="mf"><span class="note">' + ic('lock') + '<span id="lockn"></span></span><button class="btn gh" data-act="close">Cancel</button><button class="btn g" data-act="publish" id="pub"></button></div>';
    show('modal'); briefPreview();
  }
  function num(id, d) { var e = $(id); if (!e) return d; var v = parseInt(String(e.value).replace(/[^\d]/g, ''), 10); return isFinite(v) ? v : 0; }
  function readForm() { if (!$('f-ask')) return; F.ask = $('f-ask').value; F.price = num('f-price', F.price); F.budget = num('f-budget', F.budget); F.maxOffer = num('f-max', F.maxOffer); }
  function briefPreview() {
    if (!$('pv')) return;
    readForm();
    $('askn').textContent = F.ask.length + ' / 120';
    var p = PM.market.briefs.filter(function (x) { return x.key === F.prod; })[0];
    var b = { key: 'preview', art: p.key, name: p.name, path: p.path, buyer: F.as, ask: F.ask || '…', kind: F.kind, price: F.price, cur: F.cur, hold: F.hold,
      budget: Math.max(F.budget, 1), left: F.budget, paid: 0, held: 0, rejected: 0, offers: [], days: F.days, age: 0 };
    $('pv').innerHTML = briefCard(b).replace(/data-take="preview"/, 'disabled').replace(/data-offer="preview"/, 'disabled').replace(/data-brief="preview"/g, '');
    var n = F.price ? Math.floor(F.budget / F.price) : 0;
    $('calc').innerHTML = '<div><span>Per result</span><b>' + fmt(F.price) + ' ' + F.cur + '</b></div><div><span>Budget</span><b>' + fmt(F.budget) + ' ' + F.cur + '</b></div>' +
      (F.offers ? '<div><span>Post offers, from the same budget</span><b>≤ ' + fmt(F.maxOffer) + ' ' + F.cur + '</b></div>' : '') +
      '<div class="t"><span>Pays for up to</span><b>' + fmt(n) + ' new users</b></div>';
    $('lockn').textContent = F.as === PM.me.username ? fmt(F.budget) + ' ' + F.cur + ' locked from your balance now · unspent returns ' + dShort(addDays(DAY, F.days)) :
      fmt(F.budget) + ' ' + F.cur + ' locks from ' + F.as + '’s balance when you approve · unspent returns at the end';
    $('pub').innerHTML = (F.as === PM.me.username ? 'Lock & publish' : 'Send for approval') + ' ' + ic('arrow');
  }
  function publish() {
    readForm();
    var p = PM.market.briefs.filter(function (x) { return x.key === F.prod; })[0], key = 'new' + Date.now();
    if (F.as !== PM.me.username) { hide(); toast('Sent to your approvals · ' + fmt(F.budget) + ' ' + F.cur + ' locks when you approve'); return; }
    S.briefs.unshift({ key: key, art: p.key, name: p.name, path: p.path, buyer: F.as, ask: F.ask, kind: F.kind, price: F.price, cur: F.cur, hold: F.hold, budget: F.budget,
      paid: 0, held: 0, rejected: 0, trying: 0, funnel: { clicks: 0, accounts: 0, qualified: 0, held: 0, paid: 0 }, rejects: [], offers: [], spent: 0, committed: 0, left: F.budget, days: F.days, age: 0, threads: 0 });
    hide(); S.sort = 'newest'; route(); toast('Brief published · ' + fmt(F.budget) + ' ' + F.cur + ' locked');
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
      '<div class="mb"><div class="f"><div class="fl"><label>Where it goes</label><input class="in" placeholder="https://cymetica.com/…"></div>' +
      '<div class="two"><div class="fl"><label>Title <span>up to 200</span></label><input class="in" maxlength="200" placeholder="Shown on your dashboard"></div>' +
      '<div class="fl"><label>Kind</label><div class="seg" style="height:44px;align-items:center">' + ['tool', 'product', 'other'].map(function (k, i) { return '<button class="' + (i === 0 ? 'on' : '') + '" style="height:36px">' + k + '</button>'; }).join('') + '</div></div></div></div></div>' +
      '<div class="mf"><span class="note"></span><button class="btn gh" data-act="close">Cancel</button><button class="btn g" data-act="made">Track ' + ic('arrow') + '</button></div>';
    show('modal');
  }
  function agentDrawer() {
    $('drawer').innerHTML = '<div class="dh plain"><button class="x" data-act="close">' + ic('close') + '</button></div><div class="db top">' +
      '<span class="kick">Stay in your chatbox</span><h2>From your own AI agent</h2><p class="ask">Copy into ChatGPT, Claude, Gemini, Meta Muse or any MCP/HTTP agent: it registers itself, no website, no install.</p>' +
      '<div class="sec">Promote · take briefs<span class="ln"></span><span class="chip g">new</span></div><pre class="code">' + codeHTML(PROMO_PROMPT) + '</pre><button class="btn c" data-copy="promo">' + ic('copy') + 'Copy prompt</button>' +
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
    if (r === 'me') v.innerHTML = dash(h[1] || 'today');
    else if (r === 'profile') v.innerHTML = profile(h[1]);
    else v.innerHTML = market();
    document.querySelectorAll('#tnav a').forEach(function (a) { a.classList.toggle('on', a.getAttribute('data-r') === r); });
    var c = $('bcnt'); if (c) c.textContent = sortBriefs(S.briefs.slice()).length;
    if (location.hash === '#board') { var b = $('board'); if (b) b.scrollIntoView(); } else window.scrollTo(0, 0);
    // #brief: the form, straight away (the Universe's Promo Market panel links here)
    if (location.hash === '#brief') briefForm();
  }
  window.addEventListener('hashchange', route);

  document.addEventListener('click', function (e) {
    var t = e.target.closest('[data-act],[data-take],[data-offer],[data-sendoffer],[data-oplat],[data-brief],[data-copy],[data-f],[data-s],[data-q],[data-qi],[data-ra],[data-row],[data-sort],[data-prod],[data-kind],[data-cur],[data-hold],[data-acc],[data-days],[data-as],[data-qtab]');
    if (!t) { if (e.target.id === 'scrim') hide(); return; }
    var d = t.dataset;
    if (d.take) { e.stopPropagation(); take(d.take); return; }
    if (d.offer) { e.stopPropagation(); openBrief(d.offer, 'offer'); return; }
    if (d.sendoffer) { sendOffer(d.sendoffer); return; }
    if (d.oplat) { S.oplat = d.oplat; document.querySelectorAll('#oplat button').forEach(function (b) { b.classList.toggle('on', b.dataset.oplat === d.oplat); }); return; }
    if (d.copy) {
      var k = d.copy, a = PM.radar[S.radar];
      var txt = k === 'promo' ? PROMO_PROMPT : k === 'trade' ? PM.live.trade_prompt : k === 'tweet' ? PM.live.tweet : k === 'radar-x' ? a.x_post : k === 'radar-r' ? a.reddit_title :
        k === 'radar-b' ? a.reddit_body : k === 'radar-t' ? a.tg_post : k.indexOf('link:') === 0 ? 'https://cymetica.com/c/' + k.slice(5) : '';
      copy(txt, k === 'promo' || k === 'trade' ? 'Prompt' : k.indexOf('link:') === 0 ? 'Link' : 'Post'); return;
    }
    if (d.f) { S.filter = d.f; document.querySelectorAll('#bfilter button').forEach(function (b) { b.classList.toggle('on', b.dataset.f === d.f); }); refreshBoard(); return; }
    if (d.s) { S.sort = d.s; document.querySelectorAll('#bsort button').forEach(function (b) { b.classList.toggle('on', b.dataset.s === d.s); }); refreshBoard(); return; }
    if (d.qtab) { S.qtab = d.qtab; return; }
    if (d.q) { S.qtab = d.q; route(); return; }
    if (d.qi) { S.qsel[S.qtab] = +d.qi; var y = window.scrollY; route(); window.scrollTo(0, y); return; }
    if (d.ra) { S.radar = +d.ra; var y2 = window.scrollY; route(); window.scrollTo(0, y2); return; }
    if (d.row) { S.open[d.row] = !S.open[d.row]; var y3 = window.scrollY; route(); window.scrollTo(0, y3); return; }
    if (d.sort) { S.pgSort = d.sort; var y4 = window.scrollY; route(); window.scrollTo(0, y4); return; }
    if (d.prod) { var p = PM.market.briefs.filter(function (x) { return x.key === d.prod; })[0]; F.prod = d.prod; F.ask = p.ask; F.kind = p.kind; F.price = p.price; F.cur = p.cur; briefForm(); return; }
    if (d.kind) { readForm(); F.kind = d.kind; briefForm(); return; }
    if (d.cur) { readForm(); F.cur = d.cur; briefForm(); return; }
    if (d.hold) { readForm(); F.hold = +d.hold; briefForm(); return; }
    if (d.acc) { readForm(); F.offers = d.acc === 'true'; briefForm(); return; }
    if (d.days) { readForm(); F.days = +d.days; briefForm(); return; }
    if (d.as) { readForm(); F.as = d.as; briefForm(); return; }
    if (d.brief) { openBrief(d.brief); return; }
    switch (d.act) {
      case 'close': hide(); break;
      case 'brief': hide(); briefForm(); break;
      case 'agent': e.preventDefault(); agentDrawer(); break;
      case 'publish': publish(); break;
      case 'page': pageForm(); break;
      case 'track': trackForm(); break;
      case 'made': hide(); toast('Done · it shows on your dashboard'); break;
      case 'posted': toast('Marked posted · the checker confirms it is displayed'); break;
      case 'draft': $('draft').textContent = 'Drafting the reply for this thread…'; break;
      case 'skip': toast('Skipped'); break;
      case 'pitched': toast('Marked pitched'); break;
      case 'anyurl': toast('Any cymetica.com page: paste its address'); break;
    }
  });
  document.addEventListener('input', function (e) {
    if (e.target.id === 'pgq') { S.pgQ = e.target.value; var pos = e.target.selectionStart, y = window.scrollY; route(); window.scrollTo(0, y); var q = $('pgq'); q.focus(); q.setSelectionRange(pos, pos); }
    else if (/^f-/.test(e.target.id)) briefPreview();
  });
  document.addEventListener('keydown', function (e) { if (e.key === 'Escape') hide(); });
  route();
})();
