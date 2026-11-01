/* Pitch Cards mock. Nexus pitches only what clears its bar (refresh.py: a fund live 8+ weeks, +5% since it went live
   and up this month; a $10B+ deal this week with a live ripple card). Swipe left to pass, right to invest an amount.
   Every number on a card and on the pitchboard is Cymetica's live data (data.js); the $100 balance is the example the
   operator gave. Investing moves only this page's own counters: the page sends nothing. */
(function () {
  'use strict';
  var D = window.PC_DATA || { pitches: [], board: [] };
  var $ = function (id) { return document.getElementById(id); };
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
  var pct = function (v, d) { return (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(d == null ? 1 : d) + '%'; };
  var usd = function (v, d) { return '$' + v.toLocaleString('en-US', { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 }); };
  var MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  var day = function (iso) { var p = iso.slice(0, 10).split('-'); return (+p[2]) + ' ' + MON[+p[1] - 1]; };
  var NOW = D.as_of ? new Date(D.as_of.replace(' UTC', 'Z').replace(' ', 'T')) : new Date();
  var ago = function (iso) { var n = Math.max(0, Math.round((NOW - new Date(iso.slice(0, 10) + 'T00:00:00Z')) / 864e5)); return n === 0 ? 'today' : n === 1 ? 'yesterday' : n + ' days ago'; };
  var CALM = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;

  var S = { bal: 100, deals: [], i: 0, pending: null };

  /* ------------------------------------------------------------------ a pitch, in Nexus's words, from the data */
  function dealParts(name) {
    var m = name.replace(/\s*\(\$[\d.]+[BM]\)\s*$/, '').split(' to acquire ');
    var short = function (s) { return s.replace(/,?\s+(Corporation|Corp\.?|Inc\.?|Holdings|plc|Ltd\.?|Group)$/i, ''); };
    return m.length === 2 ? { buyer: short(m[0]), target: short(m[1]) } : null;
  }
  function money(v) { return v >= 1e9 ? '$' + (v / 1e9).toFixed(1) + 'B' : '$' + Math.round(v / 1e6) + 'M'; }
  function pitch(p) {
    if (p.kind === 'fund') return {
      kind: 'fund', label: 'Fund', num: pct(p.ret), what: p.name + ' fund, since it went live ' + day(p.since),
      cap: [p.name + ' index', '<b' + (p.ret30 < 0 ? ' class="neg"' : '') + '>' + pct(p.ret30) + '</b> last 30 days'],
      say: 'Live for ' + p.weeks + ' weeks and still climbing. Want a piece?'
    };
    var dp = dealParts(p.name);
    return {
      kind: 'deal', label: 'Mega deal · ' + ago(p.since), num: money(p.size), what: dp ? dp.buyer + ' buys ' + dp.target : p.name,
      cap: [p.ticker + ' ripple card', '<b' + (p.ret < 0 ? ' class="neg"' : '') + '>' + pct(p.ret) + '</b> since the news'],
      say: 'Deals this big move the companies around them. My pick is the ' + p.ticker + ' card. In?'
    };
  }

  /* a smooth line through the points (monotone, so it never overshoots a real high or low), sized to its box */
  function curve(P) {
    var n = P.length, i, dx = [], m = [], t = [];
    for (i = 0; i < n - 1; i++) { dx[i] = P[i + 1][0] - P[i][0]; m[i] = (P[i + 1][1] - P[i][1]) / dx[i]; }
    t[0] = m[0]; t[n - 1] = m[n - 2];
    for (i = 1; i < n - 1; i++) t[i] = m[i - 1] * m[i] <= 0 ? 0 : (m[i - 1] + m[i]) / 2;
    for (i = 0; i < n - 1; i++) {
      if (!m[i]) { t[i] = t[i + 1] = 0; continue; }
      var a = t[i] / m[i], b = t[i + 1] / m[i], s = a * a + b * b;
      if (s > 9) { var k = 3 / Math.sqrt(s); t[i] = k * a * m[i]; t[i + 1] = k * b * m[i]; }
    }
    var d = 'M' + P[0][0].toFixed(1) + ' ' + P[0][1].toFixed(1);
    for (i = 0; i < n - 1; i++) {
      var h = dx[i] / 3;
      d += 'C' + (P[i][0] + h).toFixed(1) + ' ' + (P[i][1] + t[i] * h).toFixed(1) + ' ' + (P[i + 1][0] - h).toFixed(1) + ' ' + (P[i + 1][1] - t[i + 1] * h).toFixed(1) +
        ' ' + P[i + 1][0].toFixed(1) + ' ' + P[i + 1][1].toFixed(1);
    }
    return d;
  }
  var gid = 0;
  function drawChart(box, spark, kind) {
    var W = box.clientWidth, H = box.clientHeight, n = spark.length;
    if (!W || !H || n < 2) return;
    // a three-point mean for the drawing only (an index that moves in steps reads as stairs); the last point stays exact
    spark = spark.map(function (v, i) { return i === n - 1 ? v : (spark[Math.max(0, i - 1)] + v + spark[Math.min(n - 1, i + 1)]) / 3; });
    var lo = Math.min.apply(null, spark), hi = Math.max.apply(null, spark), r = hi - lo || 1, top = H * .16, bot = H * .14, R = W - 18;
    var P = spark.map(function (v, i) { return [R * i / (n - 1), top + (H - top - bot) * (1 - (v - lo) / r)]; });
    var line = curve(P), e = P[n - 1], g = 'pcg' + (++gid);
    var c1 = kind === 'fund' ? '#00cfff' : '#3b82f6', c2 = kind === 'fund' ? '#00ff88' : '#00cfff';
    box.innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '" aria-hidden="true"><defs>' +
      '<linearGradient id="' + g + 's" x1="0" x2="1"><stop offset="0" stop-color="' + c1 + '"/><stop offset="1" stop-color="' + c2 + '"/></linearGradient>' +
      '<linearGradient id="' + g + 'a" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="' + c2 + '" stop-opacity=".3"/><stop offset="1" stop-color="' + c2 + '" stop-opacity="0"/></linearGradient>' +
      '<filter id="' + g + 'f" x="-10%" y="-30%" width="120%" height="160%"><feGaussianBlur stdDeviation="5"/></filter></defs>' +
      '<line class="base" x1="0" x2="' + W + '" y1="' + P[0][1].toFixed(1) + '" y2="' + P[0][1].toFixed(1) + '"/>' +
      '<path class="ar" d="' + line + 'L' + W + ' ' + e[1].toFixed(1) + 'L' + W + ' ' + H + 'L0 ' + H + 'Z" fill="url(#' + g + 'a)"/>' +
      '<path class="ln" d="' + line + '" stroke="url(#' + g + 's)" pathLength="1" filter="url(#' + g + 'f)" opacity=".7"/>' +
      '<path class="ln" d="' + line + '" stroke="url(#' + g + 's)" pathLength="1"/>' +
      '<circle class="ring" cx="' + e[0].toFixed(1) + '" cy="' + e[1].toFixed(1) + '" r="5" fill="none" stroke="' + c2 + '" stroke-width="1.5"/>' +
      '<circle class="dot" cx="' + e[0].toFixed(1) + '" cy="' + e[1].toFixed(1) + '" r="5" fill="#fff" stroke="' + c2 + '" stroke-width="3"/></svg>';
  }

  function cardHtml(p, cls) {
    var q = pitch(p);
    return '<article class="pc-card k-' + q.kind + ' ' + cls + '">' +
      '<div class="pc-who"><i class="pc-orb"></i><b>Nexus</b><span>' + esc(q.label) + '</span></div>' +
      '<div class="pc-hero"><b class="pc-num">' + q.num + '</b><span class="pc-what">' + esc(q.what) + '</span></div>' +
      '<div class="pc-chart"></div>' +
      '<div class="pc-cap"><span>' + esc(q.cap[0]) + '</span><span>' + q.cap[1] + '</span></div>' +
      '<div class="pc-say" data-say="' + esc(q.say) + '">' + esc(q.say) + '</div>' +
      '<div class="pc-tint in"><em>Invest</em></div><div class="pc-tint out"><em>Pass</em></div></article>';
  }

  /* Nexus says it the way an AI does: word by word, the orb lit while it talks */
  function speak(card) {
    var el = card.querySelector('.pc-say'), orb = card.querySelector('.pc-orb'), words = el.dataset.say.split(' '), k = 0;
    if (CALM) return;
    clearInterval(speak.h); orb.classList.add('talk');
    var put = function () {
      el.innerHTML = esc(words.slice(0, k).join(' ')) + '<i class="car"></i><span class="rest"> ' + esc(words.slice(k).join(' ')) + '</span>';
    };
    put();
    setTimeout(function () {
      speak.h = setInterval(function () {
        k++; put();
        if (k >= words.length) { clearInterval(speak.h); orb.classList.remove('talk'); setTimeout(function () { el.textContent = el.dataset.say; }, 900); }
      }, 55);
    }, 650);
  }

  /* ------------------------------------------------------------------ the deck */
  function drawDeck() {
    var P = D.pitches, h = '';
    for (var k = Math.min(P.length - 1, S.i + 2); k >= S.i; k--) h += cardHtml(P[k], k === S.i ? 'top' : k === S.i + 1 ? 'back1' : 'back2');
    if (S.i >= P.length) h = '<div class="pc-empty"><i class="pc-orb"></i><b>You’re all caught up</b>' +
      '<span title="A fund: live ' + D.bar.fund_weeks + '+ weeks, +' + D.bar.fund_ret + '% or more since it went live, up over the last 30 days. A deal: $' +
      (D.bar.deal_usd / 1e9) + 'B or more, in the last ' + D.bar.deal_days + ' days, with a live ripple card.">Nexus pitches only when the data is strong. You get a notification when it has one.</span>' +
      '<button type="button" data-tab="board">See every pitch so far</button></div>';
    $('deck').innerHTML = h;
    $('acts').classList.toggle('off', S.i >= P.length);
    var left = P.length - S.i;
    $('nNew').textContent = left > 0 ? left : '';
    [].forEach.call($('deck').querySelectorAll('.pc-card'), function (c) {
      var k = S.i + (c.classList.contains('top') ? 0 : c.classList.contains('back1') ? 1 : 2);
      drawChart(c.querySelector('.pc-chart'), P[k].spark, P[k].kind);
    });
    var t = top();
    if (t) { drag(t); speak(t); }
  }
  function drag(el) {
    var x0 = 0, y0 = 0, dx = 0, on = false, ti = el.querySelector('.pc-tint.in'), to = el.querySelector('.pc-tint.out'), pc = $('pc');
    el.addEventListener('pointerdown', function (e) { if (e.button) return; on = true; x0 = e.clientX; y0 = e.clientY; dx = 0; el.classList.add('drag'); $('deck').classList.add('dragging'); el.setPointerCapture(e.pointerId); });
    el.addEventListener('pointermove', function (e) {
      if (!on) return;
      dx = e.clientX - x0; var dy = (e.clientY - y0) * 0.2, f = Math.max(-1, Math.min(1, dx / 120));
      el.style.transform = 'translate(' + dx + 'px,' + dy + 'px) rotate(' + dx / 16 + 'deg)';
      ti.style.opacity = Math.max(0, f); to.style.opacity = Math.max(0, -f); pc.style.setProperty('--dx', (f * 0.9).toFixed(2));
    });
    function end() {
      if (!on) return; on = false; el.classList.remove('drag'); $('deck').classList.remove('dragging'); el.style.transform = ''; ti.style.opacity = to.style.opacity = ''; pc.style.setProperty('--dx', 0);
      if (dx > 110) yes(); else if (dx < -110) no();
    }
    el.addEventListener('pointerup', end); el.addEventListener('pointercancel', end);
  }
  function top() { return $('deck').querySelector('.pc-card.top'); }
  function flash(side) { var pc = $('pc'); pc.style.setProperty('--dx', side); setTimeout(function () { pc.style.setProperty('--dx', 0); }, 380); }
  function no() {
    var el = top(); if (!el) return;
    el.querySelector('.pc-tint.out').style.opacity = 1; el.classList.add('gone-l'); flash(-0.8);
    setTimeout(function () { S.i++; drawDeck(); }, 340);
  }
  function yes() {
    var el = top(); if (!el) return;
    if (S.bal < 1) { toast('Your balance is $0. Add credit first.'); return; }
    el.querySelector('.pc-tint.in').style.opacity = 1; el.classList.add('park');
    S.pending = D.pitches[S.i]; openSheet(S.pending);
  }

  /* ------------------------------------------------------------------ how much */
  var AMT = 25;
  function nameOf(p) { return p.kind === 'fund' ? p.name : p.ticker + ' ripple card'; }
  function openSheet(p) {
    $('sheetT').textContent = 'Invest in ' + nameOf(p);
    AMT = Math.min(25, S.bal); $('amtR').max = S.bal; $('amtR').value = AMT;
    $('chips').innerHTML = [10, 25, 50].filter(function (v) { return v < S.bal; }).map(function (v) { return '<button type="button" data-a="' + v + '">$' + v + '</button>'; }).join('') +
      '<button type="button" data-a="' + S.bal + '">All</button>';
    setAmt(AMT); $('sheet').hidden = false;
  }
  function setAmt(v) {
    AMT = Math.max(1, Math.min(S.bal, Math.round(v)));
    $('amt').textContent = usd(AMT); $('amtR').value = AMT; $('invest').textContent = 'Invest ' + usd(AMT);
    $('amtSub').textContent = 'of your ' + usd(S.bal) + ' balance';
    $('amtR').style.setProperty('--p', (S.bal > 1 ? 100 * (AMT - 1) / (S.bal - 1) : 100).toFixed(1) + '%');   // the filled part of the track
    [].forEach.call($('chips').children, function (b) { b.classList.toggle('on', +b.dataset.a === AMT); });
  }
  function closeSheet(done) {
    $('sheet').hidden = true;
    var el = top();
    if (done) {
      S.deals.unshift({ p: S.pending, amt: AMT, at: new Date() }); S.bal -= AMT; drawBal();
      $('nDeals').textContent = S.deals.length;
      if (el) { el.classList.remove('park'); el.classList.add('gone-r'); flash(0.9); }
      toast('Invested ' + usd(AMT) + ' in ' + nameOf(S.pending) + '. Nexus is on it.');
      setTimeout(function () { S.i++; drawDeck(); }, 340);
    } else if (el) { el.classList.remove('park'); el.querySelector('.pc-tint.in').style.opacity = ''; }
    S.pending = null;
  }
  function drawBal() { $('bal').textContent = usd(S.bal); var b = $('addc'); b.classList.remove('tick'); void b.offsetWidth; b.classList.add('tick'); }

  /* ------------------------------------------------------------------ my deals */
  function stat(k, v, cls, small) { return '<div class="pc-stat"><span>' + k + '</span><b class="' + (cls || '') + '">' + v + '</b>' + (small ? '<small>' + small + '</small>' : '') + '</div>'; }
  var ICON = {   // a fund: a line going up; a deal: two arrows meeting
    fund: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M4 17l5-5 4 3 7-8"/><path d="M15 7h5v5"/></svg>',
    deal: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 7h6l3 5-3 5H3"/><path d="M21 7h-4l-3 5 3 5h4"/></svg>'
  };
  function icon(kind) { return '<span class="pc-ic ' + kind + '">' + ICON[kind] + '</span>'; }
  function drawDeals() {
    var inv = S.deals.reduce(function (s, d) { return s + d.amt; }, 0);
    $('dealTiles').innerHTML = stat('Invested', usd(inv)) + stat('Worth now', usd(inv)) + stat('Result', pct(0, 2), 'zero', 'since you invested');
    $('dealList').innerHTML = S.deals.length ? S.deals.map(function (d) {
      var p = d.p, dp = p.kind === 'deal' && dealParts(p.name);
      return '<div class="pc-row new">' + icon(p.kind) + '<span class="pc-n"><b>' + esc(nameOf(p)) + '</b><span>' + usd(d.amt) + ' in · just now' +
        (dp ? ' · ' + esc(dp.buyer + ' buys ' + dp.target) : '') + '</span></span><span class="pc-bar2"></span>' +
        '<span class="pc-r zero" title="Moves with ' + esc(p.kind === 'fund' ? 'the fund\'s index' : 'the card\'s index') + ' from the moment you invested">' + pct(0, 2) + '</span></div>';
    }).join('') : '<div class="pc-none"><i class="pc-orb"></i>No deals yet. Swipe right on a pitch you like.</div>';
  }

  /* ------------------------------------------------------------------ the pitchboard: every pick, since it was made */
  var BK = 'all', SHOWN = 40;
  function drawBoard() {
    var rows = D.board.filter(function (r) { return BK === 'all' || r.kind === BK; });
    var up = rows.filter(function (r) { return r.ret > 0; }).length, avg = rows.reduce(function (s, r) { return s + r.ret; }, 0) / (rows.length || 1);
    var best = rows.reduce(function (b, r) { return !b || r.ret > b.ret ? r : b; }, null);
    $('boardTiles').innerHTML = stat('Pitches', rows.length.toLocaleString('en-US')) + stat('Up', up + '/' + rows.length, 'pos', Math.round(100 * up / (rows.length || 1)) + '% of them') +
      stat('Average', pct(avg, 1), avg >= 0 ? 'pos' : 'neg', 'since the pitch') + (best ? stat('Best', pct(best.ret), 'pos', esc(best.kind === 'fund' ? best.name : best.ticker)) : '');
    var cap = Math.max.apply(null, rows.map(function (r) { return Math.abs(r.ret); }).concat([1]));
    $('strip').innerHTML = rows.slice().reverse().map(function (r) {
      var h = Math.max(3, 50 * Math.abs(r.ret) / cap);   // half the strip each way from the zero line
      return '<i title="' + esc(r.kind === 'fund' ? r.name : r.ticker) + ' ' + pct(r.ret) + '"><b class="' + (r.ret >= 0 ? 'up' : 'dn') + '" style="height:' + h.toFixed(1) + '%"></b></i>';
    }).join('');
    $('boardSrc').textContent = 'Cymetica AI’s picks so far · ' + D.as_of;
    $('boardSrc').title = 'Every fund since it went live (its own index history) and every deal-ripple card since it was minted (its index against its base). Today’s pitches are lit green.';
    var bar = 25, live = {};
    D.pitches.forEach(function (p) { live[p.kind + (p.id || p.name)] = 1; });
    $('board').innerHTML = rows.slice(0, SHOWN).map(function (r) {
      var w = Math.min(50, 50 * Math.abs(r.ret) / bar), col = r.ret >= 0 ? 'var(--green)' : 'var(--red)';
      var nm = r.kind === 'fund' ? r.name : r.ticker, sub = r.kind === 'fund' ? 'Fund · since ' + day(r.since) : r.name.replace(/\s*\(\$[\d.]+[BM]\)\s*$/, '').replace(' to acquire ', ' buys ') + ' · ' + day(r.since);
      return '<div class="pc-row' + (live[r.kind + (r.id || r.name)] ? ' new' : '') + '">' + icon(r.kind) +
        '<span class="pc-n"><b>' + esc(nm) + '</b><span title="' + esc(sub) + '">' + esc(sub) + '</span></span>' +
        '<span class="pc-bar2"><i style="' + (r.ret >= 0 ? 'left:50%' : 'right:50%') + ';width:' + w.toFixed(1) + '%;background:' + col + '"></i></span>' +
        '<span class="pc-r ' + (r.ret > 0 ? 'pos' : r.ret < 0 ? 'neg' : 'zero') + '">' + pct(r.ret) + '</span></div>';
    }).join('');
    $('more').hidden = rows.length <= SHOWN;
  }

  /* ------------------------------------------------------------------ wiring */
  function view(v) {
    $('pc').dataset.view = v;
    [].forEach.call(document.querySelectorAll('.pc-tabs button'), function (a) { a.classList.toggle('on', a.dataset.tab === v); });
    if (v === 'deals') { drawDeals(); $('nDeals').textContent = ''; }
    if (v === 'board') drawBoard();
    if (v === 'deck') drawDeck();
  }
  function toast(t) { var el = $('toast'); el.textContent = t; el.hidden = false; clearTimeout(toast.h); toast.h = setTimeout(function () { el.hidden = true; }, 3000); }
  /* the app fills the screen between their header and their chat bar, so a whole card and both buttons are on it */
  function fit() {
    var pc = $('pc'), hdr = document.querySelector('.chat-header'), chat = $('nexus-chat-widget');
    // their chat bar is built after this script runs; until it is there, keep its usual height free
    var t = hdr ? hdr.getBoundingClientRect().bottom : 0, b = chat && chat.offsetHeight ? chat.getBoundingClientRect().top : innerHeight - 66;
    pc.style.setProperty('--pc-h', Math.max(560, b - (pc.getBoundingClientRect().top + scrollY) - 4) + 'px');
    pc.style.setProperty('--pc-top', t + 'px');
  }

  document.addEventListener('click', function (e) {
    var a = e.target.closest('.pc [data-tab]'); if (a) { e.preventDefault(); view(a.dataset.tab); return; }
    var c = e.target.closest('#chips button'); if (c) { setAmt(+c.dataset.a); return; }
    var k = e.target.closest('#boardSeg button');
    if (k) { BK = k.dataset.k; SHOWN = 40; [].forEach.call($('boardSeg').children, function (b) { b.classList.toggle('on', b === k); }); drawBoard(); return; }
    var id = (e.target.closest('button, a') || {}).id;
    if (id === 'no') no(); else if (id === 'yes') yes();
    else if (id === 'invest') closeSheet(true); else if (id === 'cancel') closeSheet(false);
    else if (id === 'more') { SHOWN += 40; drawBoard(); }
    else if (id === 'addc') toast('Mock: on the real page this adds credit from your USDC balance.');
    else if (id === 'push') { e.preventDefault(); hidePush(); view('deck'); }
    else if (e.target === $('sheet')) closeSheet(false);
  });
  $('amtR').addEventListener('input', function () { setAmt(+this.value); });
  document.addEventListener('keydown', function (e) {
    if (!$('sheet').hidden) { if (e.key === 'Escape') closeSheet(false); if (e.key === 'Enter') closeSheet(true); return; }
    if ($('pc').dataset.view !== 'deck' || /INPUT|TEXTAREA/.test(e.target.tagName) || e.target.isContentEditable) return;
    if (e.key === 'ArrowLeft') no(); if (e.key === 'ArrowRight') yes();
  });
  var rz; addEventListener('resize', function () { clearTimeout(rz); rz = setTimeout(function () { fit(); if ($('pc').dataset.view === 'deck') [].forEach.call($('deck').querySelectorAll('.pc-card'), function (c, j, all) {
    var k = S.i + all.length - 1 - j; drawChart(c.querySelector('.pc-chart'), D.pitches[k].spark, D.pitches[k].kind); }); }, 150); });

  function hidePush() { var p = $('push'); if (p.hidden) return; p.classList.add('out'); setTimeout(function () { p.hidden = true; p.classList.remove('out'); }, 350); }
  fit(); drawBal(); $('addc').classList.remove('tick');
  addEventListener('load', function () { fit(); setTimeout(fit, 800); });
  if (/view=(deals|board)/.test(location.search)) view(RegExp.$1); else drawDeck();
  if (D.pitches.length && !/nopush/.test(location.search)) setTimeout(function () {   // the notification Cymetica would send when Nexus has a pitch
    $('pushT').textContent = D.pitches.length + ' new pitch' + (D.pitches.length > 1 ? 'es' : '') + ' for you';
    $('pushS').textContent = D.pitches.map(function (p) { return p.kind === 'fund' ? p.name + ' ' + pct(p.ret) : money(p.size) + ' mega deal'; }).join(' · ');
    $('push').hidden = false; setTimeout(hidePush, 6000);
  }, 1200);
})();
