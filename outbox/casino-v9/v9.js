/* Agent Casino v9, on their page. Running tables on the rendered table, Open as a picker with its switches beside it,
   Finished folded, one card per table. Buttons do nothing. Every figure comes from lobby.js (their markup and the owner's)
   or data.js (our results). */
(function () {
  var L = window.CASINO_LOBBY, D = window.CASINO, G = window.CASINO_TABLE;
  var HOST = 'https://cymetica.com';
  var root = document.getElementById('v9');
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var esc = function (s) { var d = document.createElement('div'); d.textContent = s == null ? '' : s; return d.innerHTML; };
  var num = function (n) { return Math.abs(n).toLocaleString('en-US', { maximumFractionDigits: 2 }); };
  var usd = function (n) { return (n < 0 ? '−$' : '$') + num(n); };
  var signed = function (n) { return (n > 0 ? '+$' : n < 0 ? '−$' : '$') + num(n); };
  var pct = function (n) { return n == null ? '—' : (n > 0 ? '+' : n < 0 ? '−' : '') + Math.abs(n).toFixed(2) + '%'; };
  var tone = function (n) { return n > 0 ? 'pos' : n < 0 ? 'neg' : 'flat'; };
  var len = function (h) { return h === 1 ? '1H' : h === 5 ? '5H' : h === 168 ? '7D' : '1D'; };
  var ARROW = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M5 12h14M13 6l6 6-6 6"/></svg>';
  var BACK = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M19 12H5M11 6l-6 6 6 6"/></svg>';
  var CROWN = '<span class="at-crown"><svg viewBox="0 0 18 12" aria-hidden="true"><path d="M1 11h16L15.5 3 11.8 6.8 9 1 6.2 6.8 2.5 3z" fill="currentColor"/></svg></span>';
  var CHEV = '<svg class="chev" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>';
  var ava = function (colour, shape) {
    return '<span class="at-ava" style="--c:' + esc(colour || '#00cfff') + '"><svg viewBox="0 0 40 40" aria-hidden="true"><use href="#at-bot-' + esc(shape || 'a') + '"/></svg></span>';
  };
  /* their stopwatch from the hero's How long box, small: the table's length wherever its type is named */
  var stopwatch = function (label) {
    var l = String(label || '').toUpperCase(), share = l === '1H' ? 18 : l === '5H' ? 55 : 92;
    return '<span class="at-bclk v9-clk' + (l === '5H' ? ' h5' : '') + '" title="' + esc(l) + ' table"><svg viewBox="0 0 48 52" aria-hidden="true"><rect x="20" y="1" width="8" height="5" rx="1.5"/><path d="M24 6v4"/><circle class="tr" cx="24" cy="29" r="20"/><circle class="rg" cx="24" cy="29" r="20" pathLength="100" stroke-dasharray="' + share + ' 100" transform="rotate(-90 24 29)"/></svg><b>' + esc(l) + '</b></span>';
  };
  var cdn = function (end) {
    return '<span class="at-cdn" data-end="' + esc(end) + '" aria-label="Time left"><span data-u="d" hidden></span><span data-u="h"></span><span data-u="m"></span><span data-u="s"></span></span>';
  };

  /* a species wears the same face at every table: read it off the seats their page draws */
  var species = function (name) { return String(name || '').replace(/^(House|casino|tournament|lab Wave \d+)\s+/i, '').replace(/\s+Clone$/i, ''); };
  var faces = {};
  L.live.concat(L.open, L.liveKinds).forEach(function (t) {
    (t.seats || []).forEach(function (s) { if (s && s.bot && s.colour) faces[species(s.bot)] = { colour: s.colour, shape: s.shape }; });
  });
  D.bots.forEach(function (b) { if (b.avatar && b.avatar.color) faces[species(b.bot)] = faces[species(b.bot)] || { colour: b.avatar.color, shape: b.avatar.shape }; });

  /* ---------------------------------------------------------------- the table: everything inside the card */
  var PW = 890, PH = PW * G.h / G.w, FW = 420, FH = 180;
  function feltMatrix(w, h) {
    var f = G.felt, P = function (p) { return [p[0] * PW, p[1] * PH]; };
    var a = P(f.tl), b = P(f.tr), c = P(f.br), d = P(f.bl);
    var dx1 = b[0] - c[0], dx2 = d[0] - c[0], sx = a[0] - b[0] + c[0] - d[0];
    var dy1 = b[1] - c[1], dy2 = d[1] - c[1], sy = a[1] - b[1] + c[1] - d[1];
    var det = dx1 * dy2 - dx2 * dy1;
    var g = (sx * dy2 - dx2 * sy) / det, hh = (dx1 * sy - sx * dy1) / det;
    var m = [b[0] - a[0] + g * b[0], d[0] - a[0] + hh * d[0], a[0], b[1] - a[1] + g * b[1], d[1] - a[1] + hh * d[1], a[1], g, hh, 1];
    var A = m[0] / w, B = m[1] / h, C = m[2], E = m[3] / w, F = m[4] / h, H = m[5], I = m[6] / w, J = m[7] / h;
    return 'matrix3d(' + [A, E, 0, I, B, F, 0, J, 0, 0, 1, 0, C, H, 0, 1].map(function (n) { return n.toFixed(7); }).join(',') + ')';
  }
  var FM = feltMatrix(FW, FH);
  var at = function (i) { var p = G.seats[i]; return 'left:' + (p[0] * PW).toFixed(1) + 'px;top:' + (p[1] * PH).toFixed(1) + 'px'; };

  function seatHtml(s, i, us) {
    if (!s || s.empty) return '<span class="v9-seat empty" style="' + at(i) + '"><span class="at-ava"></span></span>';
    var mine = us && us.bot === s.bot;
    return '<span class="v9-seat' + (s.lead ? ' lead' : '') + (mine ? ' you' : '') + (s.pending ? ' pend' : '') + '" style="' + at(i) + '" title="' + esc(s.bot) + '">' +
      ava(s.colour, s.shape) + (s.lead ? CROWN : '') + (mine ? '<em>YOU</em>' : '') + '</span>';
  }
  function plate(inner, moving) {
    return '<div class="v9-stage"><div class="v9-obj"><div class="v9-plate">' +
      '<img class="glow" src="art/glow.webp" alt="" draggable="false"><img class="tbl" src="art/table.webp" alt="" draggable="false">' +
      (moving ? '<span class="sheen" aria-hidden="true"><i></i></span>' : '') + inner + '</div></div></div>';
  }
  function pot(key, value, sub) {
    return '<div class="pot" style="width:' + FW + 'px;height:' + FH + 'px;transform:' + FM + '"><span class="k">' + esc(key) + '</span><b class="v' + (/^\d/.test(value) ? ' cy' : '') + '">' + esc(value) + '</b><span class="s">' + esc(sub) + '</span></div>';
  }
  function fit() {
    $$('.v9-stage').forEach(function (s) { s.style.setProperty('--k', Math.min(1, s.clientWidth / 580).toFixed(4)); });
  }

  /* one card, a running table or an open one */
  function cardInner(t, moving, quiet) {
    var us = L.agents[t.id];
    var clock = t.end ? '<div class="clock">' + cdn(t.end) + '<span class="cdl">' + esc(t.cdl) + '</span><span class="at-pb" data-start="' + esc(t.start) + '" data-end="' + esc(t.end) + '"><i></i></span></div>'
      : '<div class="clock quiet">' + esc(t.cdl) + '</div>';
    var prizes = t.prizes.map(function (p) {
      return '<div class="pz' + (p.place === '1ST' ? ' w' : '') + '"><span class="k">' + esc(p.place) + '</span><b>' + esc(p.cash) + (p.unit ? '<small>' + esc(p.unit) + '</small>' : '') + '</b>' + (p.extra ? '<span class="e">' + esc(p.extra) + '</span>' : '') + '</div>';
    }).join('');
    var who = us ? '<span class="you">YOU</span><b>' + esc(us.bot) + '</b><span class="r">' + esc(us.rank) + '</span><span class="o ' + (/^-/.test(us.roi) ? 'neg' : /^\+0\.00/.test(us.roi) ? 'flat' : 'pos') + '">' + esc(us.roi) + '</span>' + (us.need ? '<small class="need">' + esc(us.need) + '</small>' : '')
      : '<span class="plain">' + esc(t.who) + '</span>';
    return '<header class="ctop"><div class="l"><span class="st"><i></i>' + esc(t.stateText) + '</span>' + (t.example ? '<span class="ex">EXAMPLE</span>' : '') + '<div class="buy">' + esc(t.buy) + '<small>' + esc(t.unit || 'buy-in') + '</small><span class="ln">' + stopwatch(t.len) + (t.id ? '#' + t.id : '') + '</span></div></div>' + clock + '</header>' +
      plate(pot(t.potKey, t.pot, t.potSub) + t.seats.map(function (s, i) { return seatHtml(s, i, us); }).join(''), moving) +
      '<footer class="cfoot"><div class="pzs">' + prizes + '</div>' + (quiet ? '' : '<div class="who">' + who + '</div>') + '</footer>';
  }

  /* ---------------------------------------------------------------- the switches: they choose the open table */
  var state = { len: 24, cur: 'USDC', mode: 'paper', i: 0 };
  try { var kept = JSON.parse(localStorage.getItem('v9-casino') || 'null'); if (kept && kept.len) { state.len = kept.len; state.cur = kept.cur; state.mode = kept.mode; } } catch (e) { /* first visit */ }
  function openList() {
    var base = (state.mode === 'live' ? L.liveKinds : L.open).filter(function (c) { return c.hours === state.len && c.cur === state.cur; });
    if (!state.example || state.mode === 'live') return base;
    /* a busy lobby: three tables of each kind on offer, the copies without a number of their own */
    var many = [];
    [0, 1, 2].forEach(function (copy) { base.forEach(function (t) { many.push(Object.assign({}, t, { id: copy ? null : t.id, seed: (t.id || 0) + copy * 5 })); }); });
    return many.map(exampleOf).sort(function (a, b) { return b.taken - a.taken; });
  }

  /* An example, asked for by the operator: the same open tables with players seated, so the page shows a busy lobby.
     One model: k paid seats of the table's own buy-in; the pot is k buy-ins, split 2/3 and 1/3 (/rules prize_split),
     and a table with one member pays its buy-in back (/rules one_member_table). The seated bots are species of theirs. */
  var CROWD = Object.keys(faces).sort();
  var FILL = [4, 2, 5, 1, 3, 0];
  function exampleOf(t, i) {
    var k = FILL[(t.seed || i) % FILL.length], et = t.cur === 'ET10', unit = et ? 'ET10' : '';
    var buy = parseFloat(String(t.buy).replace(/[^\d.]/g, '')) || 0;
    var money = function (n) { return et ? num(n) : usd(n); };
    var pot = buy * k, second = Math.floor(pot / 3 * 100) / 100, first = Math.round((pot - second) * 100) / 100;
    var seats = t.seats.map(function (s, j) {
      if (j >= k || !CROWD.length) return { empty: true };
      var name = CROWD[((t.seed || 0) * 7 + j * 3) % CROWD.length], f = faces[name];
      return { bot: name, colour: f.colour, shape: f.shape };
    });
    var prizes = k > 1 ? [{ place: '1ST', cash: money(first), unit: unit, extra: 'now' }, { place: '2ND', cash: money(second), unit: unit, extra: 'now' }]
      : k === 1 ? [{ place: '1ST', cash: money(buy), unit: unit, extra: 'buy-in back' }] : t.prizes;
    return Object.assign({}, t, { example: true, taken: k, seats: seats, who: (6 - k) + (6 - k === 1 ? ' seat left' : ' seats left'),
      potKey: k ? 'PRIZE POOL · SO FAR' : t.potKey, pot: k ? money(pot) : t.pot,
      potSub: k ? k + ' paid · ' + t.pot + (et ? ' ET10' : '') + ' when full' : t.potSub, prizes: prizes });
  }
  function railHtml(items) {
    if (items.length < 2) return '';
    return items.map(function (x, i) {
      return '<button type="button" class="rt' + (i === state.i ? ' on' : '') + '" data-pick="' + i + '">' +
        plate(x.seats.map(function (s, j) { return seatHtml(s, j, null); }).join(''), false) +
        '<span class="rc"><b>' + esc(x.buy) + (x.unit ? '<small>' + esc(x.unit) + '</small>' : '') + '</b><span>' + stopwatch(x.len) + (x.id ? '#' + x.id : '') + '</span></span><span class="rs">' + esc(x.who) + '</span></button>';
    }).join('');
  }

  /* ---------------------------------------------------------------- running tables: all of them */
  function paintLive() {
    var grid = $('#liveGrid');
    $('#tables h2 .n').textContent = L.live.length;
    grid.innerHTML = L.live.map(function (t) {
      return '<a class="v9-card live' + (t.cur === 'ET10' ? ' et' : '') + (L.agents[t.id] ? ' mine' : '') + '" href="' + (t.id === L.tableMock ? 'table.html' : esc(t.href)) + '">' + cardInner(t, false, true) + '</a>';
    }).join('');
    $('#liveNote').hidden = L.live.length > 0;
  }

  /* ---------------------------------------------------------------- the open table, one at a time, its controls beside it */
  function paintOpen() {
    var items = openList();
    if (state.i >= items.length) state.i = 0;
    var t = items[state.i], card = $('#openCard');
    card.className = 'v9-card ' + (t ? (t.state === 'coming' ? 'coming' : 'open') + (t.cur === 'ET10' ? ' et' : '') : 'none');
    card.innerHTML = t ? cardInner(t, true)
      : '<div class="nothing"><b>No open table here.</b><span>' + esc(state.mode === 'live' ? L.liveNote.split('. ')[0] + '.' : 'Try another length or buy-in.') + '</span></div>';
    card.classList.remove('shown'); void card.offsetWidth; card.classList.add('shown');
    $('#open h2 .n').textContent = items.length;
    $('#openRail').innerHTML = railHtml(items);
    var pager = $('#openPager');
    pager.hidden = items.length < 2;
    $('.count', pager).innerHTML = 'Table <b>' + (state.i + 1) + '</b> of ' + items.length;
    $('#openAct').innerHTML = !t ? '' : t.state === 'coming' ? '<button type="button" class="at-btn no wide" disabled>' + esc(t.cta) + '</button>'
      : '<button type="button" class="at-btn go xl wide" data-noop>' + esc(t.cta) + ' ' + ARROW + '</button>';
    $('#openNote').textContent = state.mode === 'live' ? L.liveNote : '';
    $$('[data-sw]').forEach(function (b) {
      var on = String(state[b.getAttribute('data-sw')]) === b.getAttribute('data-v');
      b.classList.toggle('on', on); b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    try { localStorage.setItem('v9-casino', JSON.stringify({ len: state.len, cur: state.cur, mode: state.mode })); } catch (e) { /* the switch still works */ }
    fit(); tick();
  }
  function go(dir) {
    var n = openList().length;
    if (n < 2) return;
    state.i = (state.i + dir + n) % n;
    paintOpen();
  }

  /* ---------------------------------------------------------------- finished: one card per table */
  /* An ET10 table's buy-in is in its tier and its prize in ET10: it never enters a dollar sum. */
  function et10Buyin(t) { return t.tier === 'et100' ? 100 : t.tier === 'et1k' ? 1000 : t.buyin || 0; }
  function isEt(t) { return t.currency === 'ET10'; }
  function took(t, r) {
    if (!(r.prize > 0)) return '';
    if (isEt(t)) return num(r.prize) + ' ET10' + (r.prize === et10Buyin(t) ? ' back' : '');
    return usd(r.prize) + (r.prize === t.buyin ? ' back' : '');
  }
  /* /tables/5 and /tables/11 read status "capped" (seats 29 and 46), read 5 Nov: their terms say capped is not paid out. */
  var CAPPED = { 29: true, 46: true };
  function etPaid(r) { return CAPPED[r.seat_id] ? 0 : r.et10 || 0; }
  function etLabel(r) { return r.et10 ? '+' + num(r.et10) + ' ET10' + (CAPPED[r.seat_id] ? ' capped' : '') : ''; }
  var totals = { n: D.tables.length, won: 0, net: 0, et10: 0 };
  D.tables.forEach(function (t) {
    var ids = t.mine.map(function (m) { return m.seat_id; });
    if (t.winner && ids.indexOf(t.winner.seat_id) >= 0) totals.won++;
    t.mine.forEach(function (m) {
      if (!isEt(t)) totals.net += (m.prize || 0) - (t.buyin || 0);
      totals.et10 += etPaid(m);
    });
  });
  function finishedTable(t, ids) {
    var order = t.ranked.slice().sort(function (a, b) { return a.rank - b.rank; });
    var seats = order.map(function (r, i) {
      if (i >= G.seats.length) return '';
      var face = faces[species(r.bot)] || {}, mine = ids.indexOf(r.seat_id) >= 0;
      return '<span class="v9-seat' + (r.rank === 1 ? ' lead' : '') + (mine ? ' you' : '') + '" style="' + at(i) + '" title="' + esc(r.bot) + '">' + ava(face.colour, face.shape) + (r.rank === 1 ? CROWN : '') + '</span>';
    }).join('');
    var value = isEt(t) ? num(t.pot || 0) : usd(t.pot || 0);
    return '<div class="v9-mini">' + plate(pot('POT', value, isEt(t) ? 'ET10' : '') + seats, false) + '</div>';
  }
  function doneCard(t, hidden) {
    var ids = t.mine.map(function (m) { return m.seat_id; });
    var rows = t.ranked.slice().sort(function (a, b) { return a.rank - b.rank; }).filter(function (r) { return r.rank <= 3 || ids.indexOf(r.seat_id) >= 0; });
    var ended = String(t.ends_at || '').slice(5, 10).replace('-', '/');
    var buy = isEt(t) ? num(et10Buyin(t)) + ' ET10' : usd(t.buyin || 0);
    var me = t.ranked.filter(function (r) { return ids.indexOf(r.seat_id) >= 0; })[0];
    return '<a class="v9-fin' + (ids.length ? ' ours' : '') + (isEt(t) ? ' et' : '') + '"' + (hidden ? ' hidden' : '') + ' href="' + HOST + '/agent-casino/table/' + t.id + '/results">' +
      '<div class="fh"><b>' + esc(buy) + '</b><span class="ln">' + stopwatch(len(t.hours)) + '#' + t.id + '</span><span class="sp"></span>' + (me ? '<span class="place">#' + me.rank + ' of ' + t.ranked.length + '</span>' : '') + '<span>' + esc(ended) + '</span></div>' +
      '<div class="fbody">' + finishedTable(t, ids) + '<div class="fb">' +
      rows.map(function (r) {
        var mine = ids.indexOf(r.seat_id) >= 0, w = [took(t, r), etLabel(r)].filter(Boolean).join(' ');
        return '<div class="fr' + (mine ? ' mine' : '') + '"><span class="p">' + r.rank + '</span><span class="n">' + esc(r.bot) + '</span><span class="o ' + tone(r.roi) + '">' + pct(r.roi) + '</span><span class="w' + (w ? '' : ' none') + '">' + (esc(w) || '—') + '</span></div>';
      }).join('') + '</div></div></a>';
  }

  /* ---------------------------------------------------------------- the page */
  var SHOW_DONE = 8;
  function build() {
    var newest = D.tables.slice().sort(function (a, b) { return String(b.ends_at).localeCompare(String(a.ends_at)); });
    root.innerHTML =
      '<div class="at-sec" id="tables"><h2>Live now <span class="n"></span></h2></div><div class="v9-live" id="liveGrid"></div><p class="v9-note" id="liveNote" hidden>No table is running.</p>' +
      '<div class="at-sec" id="open"><h2>Open, starts when full <span class="n"></span></h2></div>' +
      '<div class="v9-open"><div class="v9-openl"><article class="v9-card open" id="openCard"></article><div class="v9-rail" id="openRail"></div></div>' +
        '<aside class="v9-side">' +
          '<div class="sw"><span class="at-lbl">How long</span><div class="at-seg" role="group" aria-label="Length"><button type="button" data-sw="len" data-v="1">1H</button><button type="button" data-sw="len" data-v="5">5H</button><button type="button" data-sw="len" data-v="24">1D</button></div></div>' +
          '<div class="sw"><span class="at-lbl">Buy-in</span><div class="at-seg" role="group" aria-label="Buy-in"><button type="button" data-sw="cur" data-v="USDC">USDC</button><button type="button" data-sw="cur" data-v="ET10">ET10</button></div></div>' +
          '<div class="sw"><span class="at-lbl">Tables</span><div class="at-seg" role="group" aria-label="Paper or Live tables"><button type="button" data-sw="mode" data-v="paper">PAPER</button><button type="button" data-sw="mode" data-v="live"><i class="at-dot"></i>LIVE</button></div></div>' +
          '<label class="v9-ex"><input type="checkbox" data-example> Show an example: open tables with players</label>' +
          '<div class="pager" id="openPager"><button type="button" class="nav" data-go="-1" aria-label="Previous table">' + BACK + '</button><span class="count"></span><button type="button" class="nav" data-go="1" aria-label="Next table">' + ARROW + '</button></div>' +
          '<div id="openAct"></div><p class="v9-note" id="openNote"></p>' +
          '<a class="v9-create" href="' + esc(L.create) + '">+ Create a table</a>' +
        '</aside></div>' +
      '<details class="v9-done" id="finished"><summary><h2>Finished tables <span class="n">' + totals.n + '</span></h2><span class="st"><b>' + totals.won + '</b> won by your agents</span><span class="st">net <b class="' + tone(totals.net) + '">' + signed(totals.net) + '</b></span><span class="st"><b>+' + num(totals.et10) + '</b> ET10</span>' + CHEV + '</summary>' +
        '<div class="v9-finlist">' + newest.map(function (t, i) { return doneCard(t, i >= SHOW_DONE); }).join('') + '</div>' +
        (newest.length > SHOW_DONE ? '<button type="button" class="v9-all" data-moredone>All ' + totals.n + ' finished ' + CHEV + '</button>' : '') + '</details>';

    root.addEventListener('click', function (e) {
      if (e.target.closest('[data-noop]')) { e.preventDefault(); return; }
      var sw = e.target.closest('[data-sw]');
      if (sw) {
        var k = sw.getAttribute('data-sw'), v = sw.getAttribute('data-v');
        state[k] = k === 'len' ? Number(v) : v;
        state.i = 0;
        paintOpen();
        return;
      }
      var nav = e.target.closest('[data-go]');
      if (nav) { go(Number(nav.getAttribute('data-go'))); return; }
      var pick = e.target.closest('[data-pick]');
      if (pick) { state.i = Number(pick.getAttribute('data-pick')); paintOpen(); return; }
      if (e.target.closest('[data-moredone]')) { $$('.v9-fin[hidden]').forEach(function (b) { b.hidden = false; }); fit(); e.target.closest('[data-moredone]').remove(); }
    });
    $('#finished').addEventListener('toggle', fit);
    $('[data-example]').addEventListener('change', function (e) { state.example = e.target.checked; state.i = 0; paintOpen(); });
    addEventListener('resize', fit);
  }

  /* ---------------------------------------------------------------- Your agents: a tab of its own */
  function tab(name) {
    document.body.classList.toggle('v9-agents', name === 'agents');
    $$('[data-tab]').forEach(function (a) { a.classList.toggle('on', a.getAttribute('data-tab') === name); });
    fit();
  }

  /* ---------------------------------------------------------------- what their scripts did */
  document.addEventListener('click', function (e) {
    var tb = e.target.closest('[data-tab], a[href$="#agents"]');
    if (tb) { e.preventDefault(); tab(tb.getAttribute('data-tab') || 'agents'); scrollTo(0, 0); return; }
    var more = e.target.closest('[data-more]');
    if (more) {
      var small = $('small', more.parentNode), was = !small.hidden;
      small.hidden = was; more.textContent = was ? 'More' : 'Less'; more.setAttribute('aria-expanded', was ? 'false' : 'true');
      return;
    }
    var f = e.target.closest('[data-filter="agents"] [data-f]');
    if (f) {
      var want = f.getAttribute('data-f');
      $$('[data-filter="agents"] [data-f]').forEach(function (b) { b.classList.toggle('on', b === f); });
      $$('.at-agents .at-ar').forEach(function (r) { r.hidden = (r.getAttribute('data-tags') || '').split(' ').indexOf(want) < 0; });
      return;
    }
    /* Approve and Decline on a copy do nothing, and must not follow the row's link */
    var b = e.target.closest('.at-asks button, .at-ar button');
    if (b) e.preventDefault();
  });
  var pad = function (n) { return (n < 10 ? '0' : '') + n; };
  function tick() {
    $$('.at-cdn[data-end]').forEach(function (el) {
      var left = Math.max(0, Date.parse(el.getAttribute('data-end')) - Date.now());
      var parts = { d: Math.floor(left / 864e5), h: Math.floor(left / 36e5) % 24, m: Math.floor(left / 6e4) % 60, s: Math.floor(left / 1e3) % 60 };
      ['d', 'h', 'm', 's'].forEach(function (u) {
        var b = $('[data-u="' + u + '"]', el);
        if (b) { b.innerHTML = pad(parts[u]) + '<i>' + u.toUpperCase() + '</i>'; if (u === 'd') b.hidden = !parts.d; }
      });
    });
    $$('.at-pb[data-start]').forEach(function (el) {
      var a = Date.parse(el.getAttribute('data-start')), b = Date.parse(el.getAttribute('data-end'));
      var i = $('i', el);
      if (i && b > a) i.style.width = Math.min(100, Math.max(0, (Date.now() - a) / (b - a) * 100)).toFixed(1) + '%';
    });
  }

  build();
  paintLive();
  paintOpen();
  tab(location.hash === '#agents' ? 'agents' : 'lobby');
  setInterval(tick, 1000);
})();
