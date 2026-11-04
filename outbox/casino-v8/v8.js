/* Agent Casino v8. The hero's table is the deck: one table at a time, swiped or arrowed, chosen by two switches. One list of my bots.
   Finished tables folded to one line. Every figure comes from lobby.js (their markup) or data.js (our results). Buttons do nothing. */
(function () {
  var L = window.CASINO_LOBBY, D = window.CASINO, G = window.CASINO_TABLE, O = L.owner;
  var HOST = 'https://cymetica.com';
  var root = document.getElementById('v8');
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
  var ava = function (colour, shape, cls) {
    return '<span class="at-ava ' + (cls || '') + '" style="--c:' + esc(colour || '#00cfff') + '"><svg viewBox="0 0 40 40" aria-hidden="true"><use href="#at-bot-' + esc(shape || 'a') + '"/></svg></span>';
  };
  var cdn = function (end) {
    return '<span class="at-cdn" data-end="' + esc(end) + '" aria-label="Time left"><span data-u="d" hidden></span><span data-u="h"></span><span data-u="m"></span><span data-u="s"></span></span>';
  };

  /* ---------------------------------------------------------------- our results */
  var byBot = {};
  var meta = {};
  D.bots.forEach(function (b) { meta[b.bot] = b; });
  /* An ET10 table's buy-in is in its tier (et100, et1k) and its prize in ET10: it never enters a dollar sum. */
  function et10Buyin(t) { return t.tier === 'et100' ? 100 : t.tier === 'et1k' ? 1000 : t.buyin || 0; }
  function isEt(t) { return t.currency === 'ET10'; }
  function cashTook(t, r) {
    if (!(r.prize > 0)) return '';
    if (isEt(t)) return num(r.prize) + ' ET10' + (r.prize === et10Buyin(t) ? ' back' : '');
    return usd(r.prize) + (r.prize === t.buyin ? ' back' : '');
  }
  function buyLabel(t) { return isEt(t) ? num(et10Buyin(t)) + ' ET10' : usd(t.buyin || 0); }
  /* /tables/5 et10_paid reads status "capped" for seat 29, which their terms say is not paid out: it never enters a sum. */
  var CAPPED = { 29: true };
  function etPaid(m) { return CAPPED[m.seat_id] ? 0 : m.et10 || 0; }
  function etLabel(m) { return m.et10 ? '+' + num(m.et10) + ' ET10' + (CAPPED[m.seat_id] ? ' capped' : '') : ''; }
  var totals = { n: D.tables.length, won: 0, none: 0, net: 0, et10: 0 };
  D.tables.forEach(function (t) {
    var ids = t.mine.map(function (m) { return m.seat_id; });
    if (t.winner && ids.indexOf(t.winner.seat_id) >= 0) totals.won++;
    if (!t.winner) totals.none++;
    t.mine.forEach(function (m) {
      var r = byBot[m.bot] || (byBot[m.bot] = { bot: m.bot, seats: [], net: 0, et10: 0, roi: 0 });
      var net = isEt(t) ? 0 : (m.prize || 0) - (t.buyin || 0);
      r.seats.push({ t: t, m: m, net: net });
      r.net += net; r.et10 += etPaid(m); r.roi += m.roi || 0;
      totals.net += net; totals.et10 += etPaid(m);
    });
  });

  /* ---------------------------------------------------------------- the deck */
  var state = { len: 24, cur: 'USDC', mode: 'paper', i: 0 };
  try { var kept = JSON.parse(localStorage.getItem('v8-casino') || 'null'); if (kept && kept.len) { state.len = kept.len; state.cur = kept.cur; state.mode = kept.mode; } } catch (e) { /* first visit */ }
  var askOf = {}; O.asks.forEach(function (a) { askOf[a.table] = a; });
  var agentOf = {}; O.agents.forEach(function (a) { agentOf[a.table] = a; });

  function list() {
    var match = function (c) { return c.hours === state.len && c.cur === state.cur; };
    if (window.__v8force) return window.__v8force(L, match);
    if (state.mode === 'live') return L.liveKinds.filter(match);
    return L.live.filter(match).concat(L.open.filter(match));
  }

  /* where a seat of the render lands, in the picture's own pixels */
  var PW = 890, PH = PW * G.h / G.w;
  function seatHtml(s, i, table) {
    var at = G.seats[i], left = (at[0] * PW).toFixed(1) + 'px', top = (at[1] * PH).toFixed(1) + 'px', pos = 'left:' + left + ';top:' + top;
    if (!s || s.empty) return '<span class="v8-seat empty" style="' + pos + '"><span class="at-ava"></span></span>';
    var mine = (agentOf[table.id] && agentOf[table.id].bot === s.bot) || (askOf[table.id] && askOf[table.id].bot === s.bot);
    return '<span class="v8-seat' + (s.lead ? ' lead' : '') + (mine ? ' you' : '') + (s.pending ? ' pend' : '') + '" style="' + pos + '" title="' + esc(s.bot) + '">' +
      ava(s.colour, s.shape) + (s.lead ? CROWN : '') + (mine ? '<em>YOU</em>' : '') + '</span>';
  }

  /* the felt's plane, from the render's corners: the pot lies on the table */
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
  var FW = 420, FH = 180, FM = feltMatrix(FW, FH);

  function object(t) {
    var cy = /^\d/.test(t.pot) ? ' cy' : '';
    return '<div class="v8-object"><div class="v8-plate">' +
      '<img class="glow" src="art/glow.webp" alt="" draggable="false"><img class="tbl" src="art/table.webp" alt="" draggable="false">' +
      '<span class="sheen" aria-hidden="true"><i></i></span>' +
      '<div class="pot" style="width:' + FW + 'px;height:' + FH + 'px;transform:' + FM + '"><span class="k">' + esc(t.potKey) + '</span><b class="v' + cy + '" data-pot>' + esc(t.pot) + '</b><span class="s">' + esc(t.potSub) + '</span></div>' +
      t.seats.map(function (s, i) { return seatHtml(s, i, t); }).join('') + '</div></div>';
  }

  function cardHtml(t) {
    var stateCls = t.state === 'live' ? 'live' : t.state === 'coming' ? 'coming' : 'open';
    var clock = t.end ? '<div class="clock">' + cdn(t.end) + '<span class="cdl">' + esc(t.cdl) + '</span><span class="at-pb" data-start="' + esc(t.start) + '" data-end="' + esc(t.end) + '"><i></i></span></div>'
      : '<div class="clock quiet" title="' + esc(t.state === 'coming' ? L.liveNote : L.openNote) + '">' + esc(t.cdl) + '</div>';
    var prizes = t.prizes.map(function (p) {
      return '<div class="pz' + (p.place === '1ST' ? ' w' : '') + '"><span class="k">' + esc(p.place) + '</span><b>' + esc(p.cash) + (p.unit ? '<small>' + esc(p.unit) + '</small>' : '') + '</b>' + (p.extra ? '<span class="e">' + esc(p.extra) + '</span>' : '') + '</div>';
    }).join('');
    var us = agentOf[t.id], ask = askOf[t.id], who;
    if (us) who = '<span class="you">YOU</span><b>' + esc(us.bot) + '</b><span class="r">' + esc(us.rank) + '</span><span class="flat">' + esc(us.roi) + '</span>';
    else if (ask) who = '<span class="you">YOU?</span><b>' + esc(ask.bot) + '</b><span class="q">your OK?</span>';
    else who = '<span class="plain">' + esc(t.who) + '</span>';
    var tags = (L.featured && L.featured === t.id ? '<span class="feat">' + esc(L.featuredLabel) + '</span>' : '');
    return '<article class="v8-card ' + stateCls + '" data-id="' + (t.id || '') + '">' +
      '<div class="v8-pane"><i class="edge"></i></div>' +
      '<header class="ctop"><div class="l"><span class="st"><i></i>' + esc(t.stateText) + '</span>' + tags + '<div class="buy">' + esc(t.buy) + (t.unit ? '<small>' + esc(t.unit) + '</small>' : '') + '<span class="ln">' + esc(t.len) + (t.id ? ' &middot; #' + t.id : '') + '</span></div></div>' + clock + '</header>' +
      object(t) +
      '<footer class="cfoot"><div class="pzs">' + prizes + '</div><div class="who">' + who + (us ? '<small class="need">' + esc(us.need) + '</small>' : '') + '</div></footer>' +
      '</article>';
  }

  function actionHtml(t) {
    if (!t) return '';
    var ask = askOf[t.id];
    if (ask) return '<button type="button" class="at-btn no" data-noop>Decline</button><button type="button" class="at-btn blue act" data-noop>APPROVE ' + esc(ask.loss) + '</button>';
    if (t.state === 'live') return '<a class="at-btn ghost act" href="' + esc(t.href) + '">OPEN TABLE ' + ARROW + '</a>';
    if (t.state === 'coming') return '<button type="button" class="at-btn no act" disabled>' + esc(t.cta) + '</button>';
    return '<button type="button" class="at-btn go act" data-noop>' + esc(t.cta) + ' ' + ARROW + '</button>';
  }

  function emptyHtml() {
    return '<article class="v8-card none"><div class="v8-pane"><i class="edge"></i></div><div class="v8-object"><div class="v8-plate"><img class="glow" src="art/glow.webp" alt=""><img class="tbl" src="art/table.webp" alt=""></div></div>' +
      '<div class="nothing"><b>No table here.</b><span>' + (state.mode === 'live' ? esc(L.liveNote.split('. ')[0]) + '.' : 'Try another length.') + '</span></div></article>';
  }

  var deck, stack, pager, acts, busy = false;
  /* what sits outside the card: the count, the buttons, the note */
  function chrome(items, t) {
    pager.hidden = items.length < 2;
    $('.count', pager).innerHTML = '<b>' + (state.i + 1) + '</b> / ' + items.length;
    $('.note', deck).textContent = state.mode === 'live' ? L.liveNote : '';
    $('.note', deck).hidden = state.mode !== 'live';
    acts.innerHTML = actionHtml(t);
  }
  /* the table under the top one: the next, or the previous while it is dragged the other way */
  function setBack(i) {
    var old = $('.v8-card.back', stack), items = list();
    if (old) old.remove();
    var holder = document.createElement('div');
    holder.innerHTML = cardHtml(items[i]);
    var b = holder.firstChild;
    b.classList.add('back'); b.setAttribute('data-i', i);
    stack.insertBefore(b, stack.firstChild);
    tick();
    return b;
  }
  function paint(direction) {
    var items = list();
    if (state.i >= items.length) state.i = 0;
    var t = items[state.i];
    var fresh = document.createElement('div');
    fresh.innerHTML = t ? cardHtml(t) : emptyHtml();
    var el = fresh.firstChild;
    $$('.v8-card', stack).forEach(function (old) { old.remove(); });
    stack.appendChild(el);
    if (direction) { el.classList.add(direction > 0 ? 'in-r' : 'in-l'); void el.offsetWidth; el.classList.remove('in-r', 'in-l'); countUp(el); }
    chrome(items, t);
    if (t && items.length > 1) { setBack((state.i + 1) % items.length); drag(el); }
    tick();
    $$('[data-sw]').forEach(function (b) {
      var on = String(state[b.getAttribute('data-sw')]) === b.getAttribute('data-v');
      b.classList.toggle('on', on); b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    try { localStorage.setItem('v8-casino', JSON.stringify({ len: state.len, cur: state.cur, mode: state.mode })); } catch (e) { /* the switch still works */ }
  }

  /* the pot counts up as a table arrives, as Pitch Cards' number does */
  function countUp(el) {
    var b = $('[data-pot]', el);
    if (!b) return;
    var raw = b.textContent, m = raw.match(/^(\$?)([\d,]+(?:\.\d+)?)$/);
    if (!m) return;
    var target = parseFloat(m[2].replace(/,/g, '')), t0 = performance.now(), dur = 520;
    (function step(now) {
      var f = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - f, 3);
      b.textContent = m[1] + (f < 1 ? Math.round(target * e).toLocaleString('en-US') : m[2]);
      if (f < 1) requestAnimationFrame(step);
    })(t0);
  }

  function go(dir) {
    var items = list();
    if (busy || items.length < 2) return;
    busy = true;
    var n = items.length, target = (state.i + dir + n) % n;
    var top = $('.v8-card:not(.back)', stack), back = $('.v8-card.back', stack);
    if (!back || Number(back.getAttribute('data-i')) !== target) { back = setBack(target); void back.offsetWidth; }
    state.i = target;
    chrome(items, items[target]);
    /* the top one leaves the screen, the one under it rises into its place: the same element, so there is no gap between tables */
    stack.classList.add('leaving');
    top.classList.add(dir > 0 ? 'gone-l' : 'gone-r');
    countUp(back);
    setTimeout(function () {
      top.remove();
      back.classList.remove('back'); back.removeAttribute('data-i');
      stack.classList.remove('leaving');
      drag(back);
      setBack((state.i + 1) % n);
      busy = false;
    }, 440);
  }

  /* Pitch Cards' drag: the same physics, no verdict, it only turns the page. */
  function drag(el) {
    var x0 = 0, y0 = 0, dx = 0, on = false;
    el.addEventListener('pointerdown', function (e) {
      if (e.button || e.target.closest('a,button')) return;
      on = true; x0 = e.clientX; y0 = e.clientY; dx = 0; el.classList.add('drag'); stack.classList.add('dragging'); el.setPointerCapture(e.pointerId);
    });
    el.addEventListener('pointermove', function (e) {
      if (on) {
        dx = e.clientX - x0;
        var items = list(), n = items.length, want = (state.i + (dx < 0 ? 1 : -1) + n) % n, back = $('.v8-card.back', stack);
        if (back && dx !== 0 && Number(back.getAttribute('data-i')) !== want) setBack(want);
        el.style.setProperty('--tx', dx + 'px'); el.style.setProperty('--ty', (e.clientY - y0) * .2 + 'px'); el.style.setProperty('--r', dx / 22 + 'deg');
      }
    });
    function end() {
      if (!on) return;
      on = false; el.classList.remove('drag'); stack.classList.remove('dragging');
      ['--tx', '--ty', '--r'].forEach(function (k) { el.style.removeProperty(k); });
      if (dx < -110) go(1); else if (dx > 110) go(-1);
    }
    el.addEventListener('pointerup', end); el.addEventListener('pointercancel', end);
  }

  /* ---------------------------------------------------------------- my bots: one list, waiting first, then running, then the rest */
  function botRows() {
    var rows = Object.keys(byBot).map(function (k) { return byBot[k]; });
    var askBy = {}, runBy = {};
    O.asks.forEach(function (a) { askBy[a.bot] = a; });
    O.agents.forEach(function (a) { runBy[a.bot] = a; });
    var rank = function (r) { return askBy[r.bot] ? 0 : runBy[r.bot] ? 1 : 2; };
    rows.sort(function (a, b) { return rank(a) - rank(b) || b.roi / b.seats.length - a.roi / a.seats.length; });
    var liveById = {}; L.live.forEach(function (c) { liveById[c.id] = c; });
    return rows.map(function (r, i) {
      var b = meta[r.bot] || {}, av = b.avatar || {}, avg = r.roi / r.seats.length;
      var ask = askBy[r.bot], run = runBy[r.bot];
      var extra = '';
      if (ask) {
        extra = '<div class="state ask"><span class="tag"><i></i>Wants a seat</span><a href="' + esc(ask.href) + '">' + esc(ask.label) + '</a><span class="m">max loss <b>' + esc(ask.loss) + '</b></span><span class="m">' + esc(ask.lapses) + '</span>' +
          '<span class="btns"><button type="button" class="at-btn blue sm" data-noop>Approve</button><button type="button" class="at-btn no sm" data-noop>Decline</button></span></div>' +
          '<div class="warn"><span>' + esc(ask.short) + '.</span><button type="button" class="lk" data-why aria-expanded="false">More</button></div>' +
          '<div class="why" hidden>' + ask.why.map(function (w, n) { return '<p' + (n === 1 ? ' class="neg"' : '') + '>' + esc(w) + '</p>'; }).join('') + '<p>' + esc(O.sub) + '</p></div>';
      } else if (run) {
        var c = liveById[run.table];
        extra = '<div class="state run"><span class="tag"><i></i>Running</span><a href="' + esc(run.href) + '">' + esc(run.label) + '</a>' + (c ? '<span class="m tick">' + cdn(c.end) + '<small>left</small></span>' : '') +
          '<span class="m"><b>' + esc(run.rank) + '</b></span><span class="m flat">' + esc(run.roi) + '</span><span class="m need">' + esc(run.need) + '</span></div>';
      }
      var hist = r.seats.map(function (s) {
        var took = cashTook(s.t, s.m), e = etLabel(s.m);
        return '<a class="h" href="' + HOST + '/agent-casino/table/' + s.t.id + '/results"><span class="t">' + esc(buyLabel(s.t)) + ' ' + len(s.t.hours) + ' &middot; #' + s.t.id + '</span><span class="rk">#' + s.m.rank + '</span><span class="' + tone(s.m.roi) + '">' + pct(s.m.roi) + '</span><span class="tk">' + esc([took, e].filter(Boolean).join(' ') || '—') + '</span></a>';
      }).join('');
      return '<div class="v8-bot' + (ask ? ' asks' : '') + (i >= 6 ? ' more' : '') + '"' + (i >= 6 ? ' hidden' : '') + '>' +
        '<button type="button" class="row" data-bot aria-expanded="false">' + ava(av.color, av.shape) +
        '<span class="nm">' + esc(r.bot) + '</span><span class="c tb" data-unit="' + (r.seats.length === 1 ? 'table' : 'tables') + '">' + r.seats.length + '</span><span class="c ' + tone(avg) + '">' + pct(avg) + '</span><span class="c net ' + tone(r.net) + '">' + signed(r.net) + '</span><span class="c et">' + (r.et10 ? num(r.et10) : '—') + '</span>' + CHEV + '</button>' +
        extra + '<div class="hist" hidden>' + hist + '</div></div>';
    }).join('');
  }

  /* ---------------------------------------------------------------- finished: one line, then top 3 */
  function doneBlock(t, hidden) {
    var names = t.mine.map(function (m) { return m.seat_id; });
    var rows = t.ranked.slice().sort(function (a, b) { return a.rank - b.rank; }).filter(function (r) { return r.rank <= 3 || names.indexOf(r.seat_id) >= 0; });
    var ended = String(t.ends_at || '').slice(5, 10).replace('-', '/');
    return '<a class="v8-done' + (names.length ? ' ours' : '') + '"' + (hidden ? ' hidden' : '') + ' href="' + HOST + '/agent-casino/table/' + t.id + '/results">' +
      '<span class="dh"><b>' + esc(buyLabel(t)) + '</b><span>' + len(t.hours) + '</span><span class="sp"></span><span>' + esc(ended) + ' &middot; #' + t.id + '</span></span>' +
      rows.map(function (r) {
        var mine = names.indexOf(r.seat_id) >= 0, took = [cashTook(t, r), etLabel(r)].filter(Boolean).join(' ');
        return '<span class="dr' + (mine ? ' mine' : '') + '"><span class="p">' + r.rank + '</span><span class="n">' + esc(r.bot) + (mine ? '<em>YOU</em>' : '') + '</span><span class="o ' + tone(r.roi) + '">' + pct(r.roi) + '</span><span class="w' + (took ? '' : ' none') + '">' + (esc(took) || '—') + '</span></span>';
      }).join('') + '</a>';
  }

  /* ---------------------------------------------------------------- the page */
  var SHOW_DONE = 8;
  function build() {
    var newest = D.tables.slice().sort(function (a, b) { return String(b.ends_at).localeCompare(String(a.ends_at)); });
    root.innerHTML =
      '<section class="v8-hero" id="tables"><div class="v8-floor" aria-hidden="true"></div>' +
        '<div class="v8-copy"><span class="at-kick"><i class="at-dot"></i>' + esc(L.kick) + '</span>' + L.h1 +
          '<dl class="v8-facts"><div><dt>1H &middot; 5H &middot; 1D</dt><dd>How long</dd></div><div><dt>4&times; &middot; 2&times;</dt><dd>' + esc(L.pot.replace(/\.$/, '')) + '</dd></div><div><dt>+ ET10</dt><dd>' + esc(L.onTop.replace(/\.$/, '')) + '</dd></div></dl>' +
          '<div class="v8-steps">' + L.steps.map(function (s, i) { return '<span><em>' + (i + 1) + '</em>' + esc(s) + '</span>'; }).join('<i>&rsaquo;</i>') + '</div>' +
          L.noBot.replace('at-nobot', 'v8-nobot') +
          '<a class="v8-you" href="#mybots"><i></i><b>' + O.asks.length + '</b> wait for your OK<span>&middot;</span><b>' + O.agents.length + '</b> running<span>&middot;</span><b>' + Object.keys(byBot).length + '</b> bots' + ARROW + '</a>' +
        '</div>' +
        '<div class="v8-deck" id="deck">' +
          '<div class="v8-sw"><div class="seg" role="group" aria-label="Length"><button type="button" data-sw="len" data-v="1">1H</button><button type="button" data-sw="len" data-v="5">5H</button><button type="button" data-sw="len" data-v="24">1D</button></div>' +
          '<div class="seg" role="group" aria-label="Buy-in"><button type="button" data-sw="cur" data-v="USDC">USDC</button><button type="button" data-sw="cur" data-v="ET10">ET10</button></div>' +
          '<div class="seg mode" role="group" aria-label="Paper or Live tables"><button type="button" data-sw="mode" data-v="paper">PAPER</button><button type="button" data-sw="mode" data-v="live"><i class="at-dot"></i>LIVE</button></div></div>' +
          '<div class="v8-stack"></div>' +
          '<div class="v8-under"><div class="pager"><button type="button" class="nav" data-go="-1" aria-label="Previous table">' + BACK + '</button><span class="count"></span><button type="button" class="nav" data-go="1" aria-label="Next table">' + ARROW + '</button></div><div class="acts"></div></div>' +
          '<p class="note" hidden></p><a class="v8-create" href="' + esc(L.create) + '">+ Create a table</a>' +
        '</div></section>' +

      '<section class="v8-bots" id="mybots"><header class="v8-h"><h2>My bots <span>' + Object.keys(byBot).length + '</span></h2>' +
        '<div class="sum"><span>Net <b class="' + tone(totals.net) + '">' + signed(totals.net) + '</b></span><span>ET10 <b>' + num(totals.et10) + '</b></span></div>' +
        '<div class="all"><span class="total">' + esc(O.totalLabel) + ' <b>' + esc(O.total) + '</b></span><button type="button" class="at-btn blue sm" data-noop>' + esc(O.approveAll) + '</button><button type="button" class="at-btn no sm" data-noop>' + esc(O.declineAll) + '</button></div></header>' +
        '<div class="v8-cols"><span></span><span>Bot</span><span>Tables</span><span>Avg ROI</span><span>Net</span><span>ET10</span><span></span></div>' +
        botRows() + '<button type="button" class="v8-morebots" data-morebots>All ' + Object.keys(byBot).length + ' bots ' + CHEV + '</button></section>' +

      '<section class="v8-finished" id="finished"><button type="button" class="v8-line" data-fold aria-expanded="false"><h2>Finished tables</h2>' +
        '<span class="st"><b>' + totals.n + '</b> tables</span><span class="st"><b>' + totals.won + '</b> ours won</span><span class="st"><b>' + totals.none + '</b> no winner</span>' +
        '<span class="st">net <b class="' + tone(totals.net) + '">' + signed(totals.net) + '</b></span><span class="st"><b>+' + num(totals.et10) + '</b> ET10</span>' + CHEV + '</button>' +
        '<div class="v8-fold"><div class="in"><p class="v8-dn">Top 3 and what each took. A table with one member pays its own buy-in back.</p><div class="v8-donelist">' +
          newest.map(function (t, i) { return doneBlock(t, i >= SHOW_DONE); }).join('') +
        '</div><button type="button" class="v8-morebots" data-moredone>All ' + totals.n + ' finished ' + CHEV + '</button></div></div></section>';

    deck = $('#deck'); stack = $('.v8-stack', deck); pager = $('.pager', deck); acts = $('.acts', deck);

    root.addEventListener('click', function (e) {
      var noop = e.target.closest('[data-noop]');
      if (noop) { e.preventDefault(); e.stopPropagation(); return; }
      var sw = e.target.closest('[data-sw]');
      if (sw) {
        var k = sw.getAttribute('data-sw'), v = sw.getAttribute('data-v');
        state[k] = k === 'len' ? Number(v) : v;
        state.i = 0;
        paint(1);
        return;
      }
      var nav = e.target.closest('[data-go]');
      if (nav) { go(Number(nav.getAttribute('data-go'))); return; }
      var why = e.target.closest('[data-why]');
      if (why) {
        var box = $('.why', why.closest('.v8-bot')), was = !box.hidden;
        box.hidden = was; why.setAttribute('aria-expanded', was ? 'false' : 'true'); why.textContent = was ? 'More' : 'Less';
        return;
      }
      var row = e.target.closest('[data-bot]');
      if (row) {
        var open = row.getAttribute('aria-expanded') === 'true', hist = $('.hist', row.parentNode);
        row.setAttribute('aria-expanded', open ? 'false' : 'true'); hist.hidden = open;
        return;
      }
      var mb = e.target.closest('[data-morebots]');
      if (mb) { $$('.v8-bot.more').forEach(function (b) { b.hidden = false; }); mb.remove(); return; }
      var fold = e.target.closest('[data-fold]');
      if (fold) {
        var isOpen = fold.getAttribute('aria-expanded') === 'true';
        fold.setAttribute('aria-expanded', isOpen ? 'false' : 'true');
        fold.parentNode.classList.toggle('open', !isOpen);
        return;
      }
      var md = e.target.closest('[data-moredone]');
      if (md) { $$('.v8-done[hidden]').forEach(function (b) { b.hidden = false; }); md.remove(); }
    });
    document.addEventListener('keydown', function (e) {
      if (e.target.closest && e.target.closest('input,textarea,[contenteditable]')) return;
      if (e.key === 'ArrowLeft') go(-1); else if (e.key === 'ArrowRight') go(1);
    });
    /* the light in the glass follows the pointer, as Pitch Cards' does */
    /* and the pane leans a little towards it, as Quest's board does: no tilt on a phone */
    var fine = window.matchMedia && matchMedia('(hover: hover) and (pointer: fine)').matches;
    if (fine) stack.addEventListener('pointermove', function (e) {
      var r = stack.getBoundingClientRect(), fx = (e.clientX - r.left) / r.width, fy = (e.clientY - r.top) / r.height;
      stack.style.setProperty('--gx', (fx * 100).toFixed(1) + '%');
      stack.style.setProperty('--gy', (fy * 100).toFixed(1) + '%');
      stack.style.setProperty('--tilty', ((fx - .5) * 4).toFixed(2) + 'deg');
      stack.style.setProperty('--tiltx', ((.5 - fy) * 3).toFixed(2) + 'deg');
    });
    if (fine) stack.addEventListener('pointerleave', function () { stack.style.setProperty('--tilty', '0deg'); stack.style.setProperty('--tiltx', '0deg'); });
    /* a phone: the object scales with its column */
    var fit = function () { var w = deck.clientWidth; root.style.setProperty('--k', Math.min(1, w / 540).toFixed(4)); };
    addEventListener('resize', fit); fit();
  }

  /* ---------------------------------------------------------------- the one clock, on their contract: .at-cdn[data-end], [data-u], .at-pb */
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

  /* the band: one line until asked */
  var band = $('#agentPasteBar');
  if (band) band.addEventListener('click', function (e) { if (!e.target.closest('button')) band.classList.toggle('v8-open'); });

  build();
  paint();
  countUp($('.v8-card:not(.back)', stack));
  setInterval(tick, 1000);
  window.__v8 = { go: go, paint: paint, state: state, list: list };
})();
