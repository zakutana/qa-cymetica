/* Agent Casino v9, on their page. Running tables on the rendered table, Open as a picker, Finished folded. Buttons do nothing.
   Every figure comes from lobby.js (their markup and the owner's) or data.js (our results). */
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
  var cdn = function (end) {
    return '<span class="at-cdn" data-end="' + esc(end) + '" aria-label="Time left"><span data-u="d" hidden></span><span data-u="h"></span><span data-u="m"></span><span data-u="s"></span></span>';
  };

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

  function seatHtml(s, i, us) {
    var at = G.seats[i], pos = 'left:' + (at[0] * PW).toFixed(1) + 'px;top:' + (at[1] * PH).toFixed(1) + 'px';
    if (!s || s.empty) return '<span class="v9-seat empty" style="' + pos + '"><span class="at-ava"></span></span>';
    var mine = us && us.bot === s.bot;
    return '<span class="v9-seat' + (s.lead ? ' lead' : '') + (mine ? ' you' : '') + (s.pending ? ' pend' : '') + '" style="' + pos + '" title="' + esc(s.bot) + '">' +
      ava(s.colour, s.shape) + (s.lead ? CROWN : '') + (mine ? '<em>YOU</em>' : '') + '</span>';
  }
  function stage(t, us, moving) {
    var cy = /^\d/.test(t.pot) ? ' cy' : '';
    return '<div class="v9-stage"><div class="v9-obj"><div class="v9-plate">' +
      '<img class="glow" src="art/glow.webp" alt="" draggable="false"><img class="tbl" src="art/table.webp" alt="" draggable="false">' +
      (moving ? '<span class="sheen" aria-hidden="true"><i></i></span>' : '') +
      '<div class="pot" style="width:' + FW + 'px;height:' + FH + 'px;transform:' + FM + '"><span class="k">' + esc(t.potKey) + '</span><b class="v' + cy + '">' + esc(t.pot) + '</b><span class="s">' + esc(t.potSub) + '</span></div>' +
      t.seats.map(function (s, i) { return seatHtml(s, i, us); }).join('') + '</div></div></div>';
  }
  function fit() {
    $$('.v9-stage').forEach(function (s) { s.style.setProperty('--k', Math.min(1, s.clientWidth / 580).toFixed(4)); });
  }

  /* one card, a running table or an open one */
  function cardInner(t, moving) {
    var us = L.agents[t.id];
    var clock = t.end ? '<div class="clock">' + cdn(t.end) + '<span class="cdl">' + esc(t.cdl) + '</span><span class="at-pb" data-start="' + esc(t.start) + '" data-end="' + esc(t.end) + '"><i></i></span></div>'
      : '<div class="clock quiet">' + esc(t.cdl) + '</div>';
    var prizes = t.prizes.map(function (p) {
      return '<div class="pz' + (p.place === '1ST' ? ' w' : '') + '"><span class="k">' + esc(p.place) + '</span><b>' + esc(p.cash) + (p.unit ? '<small>' + esc(p.unit) + '</small>' : '') + '</b>' + (p.extra ? '<span class="e">' + esc(p.extra) + '</span>' : '') + '</div>';
    }).join('');
    var who = us ? '<span class="you">YOU</span><b>' + esc(us.bot) + '</b><span class="r">' + esc(us.rank) + '</span><span class="o ' + (/^-/.test(us.roi) ? 'neg' : 'flat') + '">' + esc(us.roi) + '</span>' + (us.need ? '<small class="need">' + esc(us.need) + '</small>' : '')
      : '<span class="plain">' + esc(t.who) + '</span>';
    return '<header class="ctop"><div class="l"><span class="st"><i></i>' + esc(t.stateText) + '</span><div class="buy">' + esc(t.buy) + '<small>' + esc(t.unit || 'buy-in') + '</small><span class="ln">' + esc(t.len) + (t.id ? ' &middot; #' + t.id : '') + '</span></div></div>' + clock + '</header>' +
      stage(t, us, moving) +
      '<footer class="cfoot"><div class="pzs">' + prizes + '</div><div class="who">' + who + '</div></footer>';
  }

  /* ---------------------------------------------------------------- the switches */
  var state = { len: 24, cur: 'USDC', mode: 'paper', i: 0 };
  try { var kept = JSON.parse(localStorage.getItem('v9-casino') || 'null'); if (kept && kept.len) { state.len = kept.len; state.cur = kept.cur; state.mode = kept.mode; } } catch (e) { /* first visit */ }
  function match(c) { return c.hours === state.len && c.cur === state.cur; }
  function openList() { return (state.mode === 'live' ? L.liveKinds : L.open).filter(match); }
  function liveList() { return state.mode === 'live' ? [] : L.live.filter(match); }

  /* ---------------------------------------------------------------- running tables */
  function paintLive() {
    var items = liveList(), grid = $('#liveGrid');
    $('#tables h2 .n').textContent = items.length;
    grid.innerHTML = items.map(function (t) {
      var mine = L.agents[t.id] ? ' mine' : '';
      return '<a class="v9-card live' + mine + '" href="' + esc(t.href) + '">' + cardInner(t, false) + '</a>';
    }).join('');
    var note = $('#liveNote');
    note.hidden = items.length > 0;
    note.textContent = state.mode === 'live' ? L.liveNote : 'No table running at this length.';
  }

  /* ---------------------------------------------------------------- the picker: Open, one table at a time */
  var deck, stack, pager, acts, busy = false;
  function cardHtml(t) { return '<article class="v9-card ' + (t.state === 'coming' ? 'coming' : 'open') + '" data-id="' + (t.id || '') + '">' + cardInner(t, true) + '</article>'; }
  function actionHtml(t) {
    if (!t) return '';
    if (t.state === 'coming') return '<button type="button" class="at-btn no act" disabled>' + esc(t.cta) + '</button>';
    return '<button type="button" class="at-btn go act" data-noop>' + esc(t.cta) + ' ' + ARROW + '</button>';
  }
  function chrome(items, t) {
    pager.hidden = items.length < 2;
    $('.count', pager).innerHTML = '<b>' + (state.i + 1) + '</b> / ' + items.length;
    acts.innerHTML = actionHtml(t);
    $('#open h2 .n').textContent = items.length;
  }
  function setBack(i) {
    var old = $('.v9-card.back', stack), items = openList();
    if (old) old.remove();
    var holder = document.createElement('div');
    holder.innerHTML = cardHtml(items[i]);
    var b = holder.firstChild;
    b.classList.add('back'); b.setAttribute('data-i', i);
    stack.insertBefore(b, stack.firstChild);
    fit(); tick();
    return b;
  }
  function holdHeight(el) { stack.style.height = el.offsetHeight + 'px'; }
  function paintDeck(direction) {
    var items = openList();
    if (state.i >= items.length) state.i = 0;
    var t = items[state.i], fresh = document.createElement('div');
    fresh.innerHTML = t ? cardHtml(t) : '<article class="v9-card none"><div class="nothing"><b>No open table here.</b><span>Try another length.</span></div></article>';
    var el = fresh.firstChild;
    $$('.v9-card', stack).forEach(function (old) { old.remove(); });
    stack.appendChild(el);
    if (direction) { el.classList.add('in'); void el.offsetWidth; el.classList.remove('in'); }
    fit();
    holdHeight(el);
    chrome(items, t);
    if (t && items.length > 1) { setBack((state.i + 1) % items.length); drag(el); }
    tick();
  }
  function go(dir) {
    var items = openList();
    if (busy || items.length < 2) return;
    busy = true;
    var n = items.length, target = (state.i + dir + n) % n;
    var top = $('.v9-card:not(.back)', stack), back = $('.v9-card.back', stack);
    if (!back || Number(back.getAttribute('data-i')) !== target) { back = setBack(target); void back.offsetWidth; }
    state.i = target;
    chrome(items, items[target]);
    stack.classList.add('leaving');
    top.classList.add(dir > 0 ? 'gone-l' : 'gone-r');
    setTimeout(function () {
      top.remove();
      back.classList.remove('back'); back.removeAttribute('data-i');
      stack.classList.remove('leaving');
      holdHeight(back);
      drag(back);
      setBack((state.i + 1) % n);
      busy = false;
    }, 420);
  }
  /* Pitch Cards' drag: it only turns the page */
  function drag(el) {
    var x0 = 0, y0 = 0, dx = 0, on = false;
    el.addEventListener('pointerdown', function (e) {
      if (e.button || e.target.closest('a,button')) return;
      on = true; x0 = e.clientX; y0 = e.clientY; dx = 0; el.classList.add('drag'); stack.classList.add('dragging'); el.setPointerCapture(e.pointerId);
    });
    el.addEventListener('pointermove', function (e) {
      if (!on) return;
      dx = e.clientX - x0;
      var items = openList(), n = items.length, want = (state.i + (dx < 0 ? 1 : -1) + n) % n, back = $('.v9-card.back', stack);
      if (back && dx !== 0 && Number(back.getAttribute('data-i')) !== want) setBack(want);
      el.style.setProperty('--tx', dx + 'px'); el.style.setProperty('--ty', (e.clientY - y0) * .2 + 'px'); el.style.setProperty('--r', dx / 22 + 'deg');
    });
    function end() {
      if (!on) return;
      on = false; el.classList.remove('drag'); stack.classList.remove('dragging');
      ['--tx', '--ty', '--r'].forEach(function (k) { el.style.removeProperty(k); });
      if (dx < -110) go(1); else if (dx > 110) go(-1);
    }
    el.addEventListener('pointerup', end); el.addEventListener('pointercancel', end);
  }

  /* ---------------------------------------------------------------- finished: a small table, and the placings beside it */
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
  function miniTable(t, ids) {
    var order = t.ranked.slice().sort(function (a, b) { return a.rank - b.rank; });
    var dots = G.seats.map(function (at, i) {
      var r = order[i];
      if (!r) return '';
      var cls = ids.indexOf(r.seat_id) >= 0 ? ' me' : r.rank === 1 ? ' first' : '';
      return '<i class="d' + cls + '" style="left:' + (at[0] * PW).toFixed(1) + 'px;top:' + (at[1] * PH).toFixed(1) + 'px"></i>';
    }).join('');
    return '<div class="v9-mini"><div class="v9-stage"><div class="v9-obj"><div class="v9-plate"><img class="tbl" src="art/table.webp" alt="" loading="lazy" draggable="false">' + dots + '</div></div></div></div>';
  }
  function doneCard(t, hidden) {
    var ids = t.mine.map(function (m) { return m.seat_id; });
    var rows = t.ranked.slice().sort(function (a, b) { return a.rank - b.rank; }).filter(function (r) { return r.rank <= 3 || ids.indexOf(r.seat_id) >= 0; });
    var ended = String(t.ends_at || '').slice(5, 10).replace('-', '/');
    var buy = isEt(t) ? num(et10Buyin(t)) + ' ET10' : usd(t.buyin || 0);
    return '<a class="v9-fin' + (ids.length ? ' ours' : '') + '"' + (hidden ? ' hidden' : '') + ' href="' + HOST + '/agent-casino/table/' + t.id + '/results">' + miniTable(t, ids) +
      '<div class="fb"><div class="fh"><b>' + esc(buy) + '</b><span>' + len(t.hours) + ' &middot; #' + t.id + '</span><span class="sp"></span><span>' + esc(ended) + '</span></div>' +
      rows.map(function (r) {
        var mine = ids.indexOf(r.seat_id) >= 0, w = [took(t, r), etLabel(r)].filter(Boolean).join(' ');
        return '<div class="fr' + (mine ? ' mine' : '') + '"><span class="p">' + r.rank + '</span><span class="n">' + esc(r.bot) + '</span><span class="o ' + tone(r.roi) + '">' + pct(r.roi) + '</span><span class="w' + (w ? '' : ' none') + '">' + (esc(w) || '—') + '</span></div>';
      }).join('') + '</div></a>';
  }

  /* ---------------------------------------------------------------- the page */
  var SHOW_DONE = 8;
  function build() {
    var newest = D.tables.slice().sort(function (a, b) { return String(b.ends_at).localeCompare(String(a.ends_at)); });
    root.innerHTML =
      '<div class="v9-bar" id="tablesbar"><div class="at-seg" role="group" aria-label="Length"><button type="button" data-sw="len" data-v="1">1H</button><button type="button" data-sw="len" data-v="5">5H</button><button type="button" data-sw="len" data-v="24">1D</button></div>' +
        '<div class="at-seg" role="group" aria-label="Buy-in"><button type="button" data-sw="cur" data-v="USDC">USDC</button><button type="button" data-sw="cur" data-v="ET10">ET10</button></div>' +
        '<div class="at-seg mode" role="group" aria-label="Paper or Live tables"><button type="button" data-sw="mode" data-v="paper">PAPER</button><button type="button" data-sw="mode" data-v="live"><i class="at-dot"></i>LIVE</button></div></div>' +
      '<div class="at-sec" id="tables"><h2>Live now <span class="n"></span></h2></div><div class="v9-live" id="liveGrid"></div><p class="v9-note" id="liveNote" hidden></p>' +
      '<div class="at-sec" id="open"><h2>Open, starts when full <span class="n"></span></h2><a class="v9-create" href="' + esc(L.create) + '">+ Create a table</a></div>' +
      '<div class="v9-deck" id="deck"><div class="v9-stack"></div><div class="v9-under"><div class="pager"><button type="button" class="nav" data-go="-1" aria-label="Previous table">' + BACK + '</button><span class="count"></span><button type="button" class="nav" data-go="1" aria-label="Next table">' + ARROW + '</button></div><div class="acts"></div></div></div>' +
      '<details class="v9-done" id="finished"><summary><h2>Finished tables <span class="n">' + totals.n + '</span></h2><span class="st"><b>' + totals.won + '</b> won by your agents</span><span class="st">net <b class="' + tone(totals.net) + '">' + signed(totals.net) + '</b></span><span class="st"><b>+' + num(totals.et10) + '</b> ET10</span>' + CHEV + '</summary>' +
        '<div class="v9-finlist">' + newest.map(function (t, i) { return doneCard(t, i >= SHOW_DONE); }).join('') + '</div>' +
        (newest.length > SHOW_DONE ? '<button type="button" class="v9-all" data-moredone>All ' + totals.n + ' finished ' + CHEV + '</button>' : '') + '</details>';
    deck = $('#deck'); stack = $('.v9-stack', deck); pager = $('.pager', deck); acts = $('.acts', deck);

    root.addEventListener('click', function (e) {
      if (e.target.closest('[data-noop]')) { e.preventDefault(); return; }
      var sw = e.target.closest('[data-sw]');
      if (sw) {
        var k = sw.getAttribute('data-sw'), v = sw.getAttribute('data-v');
        state[k] = k === 'len' ? Number(v) : v;
        state.i = 0;
        paintAll(1);
        return;
      }
      var nav = e.target.closest('[data-go]');
      if (nav) { go(Number(nav.getAttribute('data-go'))); return; }
      if (e.target.closest('[data-moredone]')) { $$('.v9-fin[hidden]').forEach(function (b) { b.hidden = false; }); fit(); e.target.closest('[data-moredone]').remove(); }
    });
    $('#finished').addEventListener('toggle', fit);
    document.addEventListener('keydown', function (e) {
      if (e.target.closest && e.target.closest('input,textarea,[contenteditable]')) return;
      if (e.key === 'ArrowLeft') go(-1); else if (e.key === 'ArrowRight') go(1);
    });
    addEventListener('resize', function () { fit(); var top = $('.v9-card:not(.back)', stack); if (top) holdHeight(top); });
  }
  function paintAll(direction) {
    paintLive();
    paintDeck(direction);
    fit();
    $$('[data-sw]').forEach(function (b) {
      var on = String(state[b.getAttribute('data-sw')]) === b.getAttribute('data-v');
      b.classList.toggle('on', on); b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    try { localStorage.setItem('v9-casino', JSON.stringify({ len: state.len, cur: state.cur, mode: state.mode })); } catch (e) { /* the switch still works */ }
  }

  /* ---------------------------------------------------------------- what their scripts did */
  document.addEventListener('click', function (e) {
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

  /* the column names over their list */
  var list = $('.at-agents');
  if (list) list.insertAdjacentHTML('afterbegin', '<div class="v9-arhead"><span></span><span>Agent</span><span>Table</span><span>Rank</span><span>ROI</span><span>Wins now</span></div>');

  build();
  paintAll();
  setInterval(tick, 1000);
})();
