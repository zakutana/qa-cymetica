/* Pitch Cards mock. Nexus pitches only what clears its bar (refresh.py: a fund live 8+ weeks, +5% since it went live
   and up this month; a $10B+ deal this week with a live ripple card). Swipe left to pass, right to invest an amount.
   Every number on a card and on the pitchboard is Cymetica's live data (data.js); the $100 balance is the example the
   operator gave. Investing moves only this page's own counters: the page sends nothing. */
(function () {
  'use strict';
  var D = window.PC_DATA || { pitches: [], board: [] };
  var $ = function (id) { return document.getElementById(id); };
  var pc = $('pc');
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
  var pct = function (v, d) { return (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(d == null ? 1 : d) + '%'; };
  var usd = function (v, d) { return '$' + v.toLocaleString('en-US', { minimumFractionDigits: d || 0, maximumFractionDigits: d || 0 }); };
  var MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  var day = function (iso) { var p = iso.slice(0, 10).split('-'); return (+p[2]) + ' ' + MON[+p[1] - 1]; };
  var NOW = D.as_of ? new Date(D.as_of.replace(' UTC', 'Z').replace(' ', 'T')) : new Date();
  var ago = function (iso) { var n = Math.max(0, Math.round((NOW - new Date(iso.slice(0, 10) + 'T00:00:00Z')) / 864e5)); return n === 0 ? 'today' : n === 1 ? 'yesterday' : n + ' days ago'; };
  var CALM = window.matchMedia && matchMedia('(prefers-reduced-motion: reduce)').matches;
  D.pitches.sort(function (a, b) { return b.ret - a.ret; });   // the strongest result opens the deck
  var S = { bal: 100, deals: [], i: 0, pending: null };

  /* ------------------------------------------------------------------ where things stand: the render's own pixels (2560 x 1440) */
  var FINGER = { x: 1664, y: 590 };
  function layout() {
    var W = innerWidth, H = innerHeight, narrow = W < 1100, s, x0, y0, cw, ch, cx, cy;
    pc.classList.toggle('narrow', narrow);
    if (!narrow) {
      s = Math.max(W / 2560, H / 1440); y0 = Math.min(0, (H - 1440 * s) * .25);
      x0 = Math.min(0, W - 2560 * s + 143 * s);               // the far arm may leave the screen, for room on the left
      ch = Math.max(470, Math.min(H - 186, 650)); cw = Math.max(380, Math.min(ch * .76, 500));
      cx = (FINGER.x + 88) * s + x0 - cw;                     // his finger and first knuckles lie on the card's right edge
      cy = Math.max(78, Math.min((FINGER.y + 90) * s + y0 - ch * .47, H - ch - 96));
      var cl = Math.max(40, W * .055), cww = cx - cl - 36;
      pc.style.setProperty('--copyl', cl + 'px'); pc.style.setProperty('--copyw', cww + 'px');
      pc.style.setProperty('--fs', Math.min(76, cww / 12.4).toFixed(1) + 'px');
      $('copy').style.display = cww < 300 ? 'none' : '';
    } else {
      cw = Math.min(W - 24, 470); cx = (W - cw) / 2;
      s = Math.max(.34, Math.min(.56, cw / 960));
      x0 = W / 2 + 22 - 2080 * s;                             // his face over the card, between the name and the balance
      var chin = 12 + 405 * s;                                // his whole face above the card when the screen has the room
      cy = Math.max(100, Math.min(chin - 6, H - 132 - 430)); ch = H - cy - 54 - 16 - 50 - 12;   // then the card, buttons, tabs
      y0 = cy >= chin - 6 ? cy + 6 - 705 * s : cy - 24 - 490 * s;   // his chin on the card's top edge; on a short screen, his eyes just over it
    }
    var v = { '--s': s.toFixed(4), '--x0': x0.toFixed(1) + 'px', '--y0': y0.toFixed(1) + 'px', '--cx': Math.round(cx) + 'px', '--cy': Math.round(cy) + 'px', '--cw': Math.round(cw) + 'px', '--ch': Math.round(ch) + 'px' };   // whole pixels keep the type sharp
    Object.keys(v).forEach(function (k) { pc.style.setProperty(k, v[k]); });
  }

  /* ------------------------------------------------------------------ a pitch, in Nexus's words, from the data */
  function dealParts(name) {
    var m = name.replace(/\s*\(\$[\d.]+[BM]\)\s*$/, '').split(' to acquire ');
    var short = function (s) { return s.replace(/,?\s+(Corporation|Corp\.?|Inc\.?|Holdings|plc|Ltd\.?|Group)$/i, ''); };
    return m.length === 2 ? { buyer: short(m[0]), target: short(m[1]) } : null;
  }
  function money(v) { return v >= 1e9 ? '$' + (v / 1e9).toFixed(1) + 'B' : '$' + Math.round(v / 1e6) + 'M'; }
  function pitch(p) {
    if (p.kind === 'fund') return {
      tag: 'Fund', right: p.weeks + ' weeks live', num: pct(p.ret), sub: p.name, subs: 'since it went live, ' + day(p.since), cmp: 'vs the other ' + p.peers.length + ' funds',
      say: (p.rank === 1 ? 'The best of ' + p.of + ' funds, still climbing: ' : 'Still climbing: ') + pct(p.ret30) + ' in 30 days. Want a piece?'
    };
    var dp = dealParts(p.name);
    return {
      tag: 'Mega deal · ' + money(p.size), right: ago(p.since), num: pct(p.ret), sub: p.ticker + ' ripple card', subs: 'since the news', cmp: 'vs the other ' + p.peers.length + ' mega deals',
      say: (dp ? dp.buyer + ' is buying ' + dp.target + ' for ' + money(p.size) + '. ' : '') + 'Deals this big ripple out, and ' + p.ticker + ' is my pick. In?'
    };
  }
  function nameOf(p) { return p.kind === 'fund' ? p.name : p.ticker + ' ripple card'; }

  /* the chart: his line lit, the rest of the field faint behind it; every point real, x in days since each one's first day */
  /* A long stretch with no reading (a fund page gives its first day, then nothing for weeks) is split off and not drawn:
     the line starts at its first real run, at its true height over the zero line, not with a straight run that never existed. */
  function dense(pts) {
    var steps = pts.slice(1).map(function (q, i) { return q[0] - pts[i][0]; }).sort(function (a, b) { return a - b; });
    var med = steps[steps.length >> 1] || 0, gap = Math.max(med * 12, (pts[pts.length - 1][0] - pts[0][0]) * .08);
    for (var i = 1; i < Math.min(pts.length, 4); i++) if (pts[i][0] - pts[i - 1][0] > gap) return { head: pts.slice(0, i + 1), rest: pts.slice(i) };
    return { head: null, rest: pts };
  }
  /* at most n readings evenly through the time, the last one exact: a confident line, not hourly noise */
  function calm(pts, n) {
    if (pts.length <= n) return pts;
    var t0 = pts[0][0], span = pts[pts.length - 1][0] - t0, out = [pts[0]], j = 1;
    for (var k = 1; k < n; k++) {
      var upto = t0 + span * k / (n - 1), sum = 0, c = 0, last = out[out.length - 1];
      while (j < pts.length && pts[j][0] <= upto) { sum += pts[j][1]; c++; j++; }
      if (c) out.push([upto, sum / c]); else out.push([upto, last[1]]);
    }
    out[out.length - 1] = pts[pts.length - 1];
    return out;
  }
  function curve(P) {   // monotone, so the line never overshoots a reading
    var n = P.length, i, dx = [], m = [], t = [];
    if (n < 3) return P.map(function (q, k) { return (k ? 'L' : 'M') + q[0].toFixed(1) + ' ' + q[1].toFixed(1); }).join('');
    for (i = 0; i < n - 1; i++) { dx[i] = (P[i + 1][0] - P[i][0]) || 1e-6; m[i] = (P[i + 1][1] - P[i][1]) / dx[i]; }
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
      d += 'C' + (P[i][0] + h).toFixed(1) + ' ' + (P[i][1] + t[i] * h).toFixed(1) + ' ' + (P[i + 1][0] - h).toFixed(1) + ' ' + (P[i + 1][1] - t[i + 1] * h).toFixed(1) + ' ' + P[i + 1][0].toFixed(1) + ' ' + P[i + 1][1].toFixed(1);
    }
    return d;
  }
  function drawChart(box, p) {
    var W = box.clientWidth, H = box.clientHeight, L = p.line;
    if (!W || !H || !L || L.length < 2) return;
    var end = L[L.length - 1][0], lo = 0, hi = 0;
    var own = dense(L), mine = calm(own.rest, 36), d0 = mine[0][0];
    var field = p.peers.filter(function (q) { return q.length > 1; }).map(function (q) { return calm(dense(q).rest.filter(function (r) { return r[0] >= d0; }), 34); })
      .filter(function (q) { return q.length > 1 && q[q.length - 1][0] - q[0][0] > (end - d0) * .6; });   // a stub of a line says nothing
    mine.concat.apply(mine, field).forEach(function (q) { lo = Math.min(lo, q[1]); hi = Math.max(hi, q[1]); });
    var last = L[L.length - 1][1], f = 1 - (last - lo) / ((hi - lo) || 1), top = Math.max(H * .1, 14), bot = H * .1, R = W - 14;
    if (!pc.classList.contains('narrow')) {   // on a big screen the line ends exactly under his fingertip, whatever the data
      var css = getComputedStyle(pc), v = function (k) { return parseFloat(css.getPropertyValue(k)); };   // from the layout, not the screen: the card may be mid-turn
      var fx = (FINGER.x - 4) * v('--s') + v('--x0') - (v('--cx') + 1.5 + box.offsetLeft), fy = (FINGER.y + 2) * v('--s') + v('--y0') - (v('--cy') + 1.5 + box.offsetTop);
      R = Math.max(W * .6, Math.min(W - 14, fx));
      if (f < .92) top = Math.max(8, Math.min(H * .6, (fy - (H - bot) * f) / (1 - f)));
    }
    var X = function (d) { return 2 + (R - 2) * (d - d0) / ((end - d0) || 1); }, Y = function (v) { return top + (H - top - bot) * (1 - (v - lo) / ((hi - lo) || 1)); };
    var path = function (pts) { return pts.map(function (q, i) { return (i ? 'L' : 'M') + X(q[0]).toFixed(1) + ' ' + Y(q[1]).toFixed(1); }).join(''); };
    var d = path(mine), tx = X(end), ty = Y(last);
    box.innerHTML = '<svg viewBox="0 0 ' + W + ' ' + H + '" aria-hidden="true">' +
      field.map(function (q) { return '<path class="peer" d="' + path(q) + '"/>'; }).join('') +
      '<path class="ln glow" pathLength="1" d="' + d + '"/><path class="ln core" pathLength="1" d="' + d + '"/>' +
      '<g class="tipd"><circle cx="' + tx.toFixed(1) + '" cy="' + ty.toFixed(1) + '" r="11" fill="#00ff88" opacity=".22"/><circle cx="' + tx.toFixed(1) + '" cy="' + ty.toFixed(1) + '" r="4.5" fill="#eafff4"/></g></svg>' +
      '<span class="pc-cmp">' + esc(pitch(p).cmp) + '</span>';
  }

  function frontHtml(p) {
    var q = pitch(p);
    return '<div class="pc-tag"><span>' + esc(q.tag) + '</span><em>' + esc(q.right) + '</em></div>' +
      '<b class="pc-num' + (p.ret < 0 ? ' neg' : '') + '" data-num="' + esc(q.num) + '">' + esc(q.num) + '</b>' +
      '<div class="pc-sub">' + esc(q.sub) + (q.subs ? '<span>' + esc(q.subs) + '</span>' : '') + '</div>' +
      '<div class="pc-chart"></div>' +
      '<div class="pc-say" data-say="' + esc(q.say) + '">' + esc(q.say) + '</div>' +
      '<div class="pc-tint in"><em>Invest</em></div><div class="pc-tint out"><em>Pass</em></div><i class="pc-scan"></i>';
  }

  /* the number runs up to its value as the pane comes on */
  function countUp(el) {
    var t = el.dataset.num, m = t.match(/^([^\d]*)([\d.]+)(.*)$/); if (!m || CALM) return;
    var v = +m[2], dec = (m[2].split('.')[1] || '').length, t0 = performance.now(), dur = 900;
    (function tick(now) {
      var f = Math.min(1, (now - t0) / dur), e = 1 - Math.pow(1 - f, 3);
      el.textContent = m[1] + (v * e).toFixed(dec) + m[3];
      if (f < 1) requestAnimationFrame(tick); else el.textContent = t;
    })(t0);
  }
  /* Nexus says it the way an AI does: word by word */
  function speak(card) {
    var el = card.querySelector('.pc-say'), words = el.dataset.say.split(' '), k = 0;
    if (CALM) return;
    clearInterval(speak.h);
    var put = function () { el.innerHTML = esc(words.slice(0, k).join(' ')) + '<i class="car"></i><span class="rest"> ' + esc(words.slice(k).join(' ')) + '</span>'; };
    put();
    speak.t = setTimeout(function () {
      speak.h = setInterval(function () {
        k++; put();
        if (k >= words.length) { clearInterval(speak.h); setTimeout(function () { if (el.isConnected) el.textContent = el.dataset.say; }, 700); }
      }, 62);
    }, 1050);
  }

  /* ------------------------------------------------------------------ the deck */
  function top() { return $('deck').querySelector('.pc-card.top'); }
  function drawDeck(fresh) {
    var P = D.pitches, h = '';
    clearTimeout(speak.t); clearInterval(speak.h);
    S.pending = null; acts(false);
    for (var k = Math.min(P.length - 1, S.i + 2); k >= S.i; k--)
      h += '<article class="pc-card k-' + P[k].kind + ' ' + (k === S.i ? 'top' : k === S.i + 1 ? 'back1' : 'back2') + '" data-k="' + k + '">' + frontHtml(P[k]) + '</article>';
    if (S.i >= P.length) h = '<div class="pc-empty"><b>That’s all<br><span>for now.</span></b><small title="A fund: live ' + D.bar.fund_weeks + '+ weeks, +' + D.bar.fund_ret + '% or more since it went live, up over the last 30 days. A deal: $' +
      (D.bar.deal_usd / 1e9) + 'B or more, in the last ' + D.bar.deal_days + ' days, with a live ripple card.">Nexus pitches only when the data is strong. You get a notification when there’s a new one.</small>' +
      '<button type="button" data-tab="board">SEE EVERY PITCH →</button></div>';
    $('deck').innerHTML = h;
    pc.classList.toggle('done', S.i >= P.length);
    $('acts').classList.toggle('off', S.i >= P.length);
    var left = P.length - S.i;
    $('nNew').textContent = left > 0 ? left : '';
    redraw();
    var t = top();
    if (t) {
      drag(t);
      if (fresh !== false) { t.classList.add('born'); setTimeout(function () { t.classList.remove('born'); }, 700); countUp(t.querySelector('.pc-num')); look(); }
      speak(t);
    }
  }
  function redraw() { [].forEach.call($('deck').querySelectorAll('.pc-card'), function (c) { if (c.querySelector('.pc-chart')) drawChart(c.querySelector('.pc-chart'), D.pitches[+c.dataset.k]); }); }
  function look() { var n = document.querySelector('.pc-nx'); n.classList.remove('flash'); void n.offsetWidth; n.classList.add('flash'); }
  function drag(el) {
    var x0 = 0, y0 = 0, dx = 0, on = false, ti = el.querySelector('.pc-tint.in'), to = el.querySelector('.pc-tint.out');
    el.addEventListener('pointerdown', function (e) { if (e.button || el.classList.contains('flipped')) return; on = true; x0 = e.clientX; y0 = e.clientY; dx = 0; el.classList.add('drag'); $('deck').classList.add('dragging'); el.setPointerCapture(e.pointerId); });
    el.addEventListener('pointermove', function (e) {
      if (!on) return;
      dx = e.clientX - x0; var dy = (e.clientY - y0) * 0.2, f = Math.max(-1, Math.min(1, dx / 120));
      el.style.setProperty('--tx', dx + 'px'); el.style.setProperty('--ty', dy + 'px'); el.style.setProperty('--r', dx / 22 + 'deg');
      ti.style.opacity = Math.max(0, f); to.style.opacity = Math.max(0, -f);
    });
    function end() {
      if (!on) return; on = false; el.classList.remove('drag'); $('deck').classList.remove('dragging');
      ['--tx', '--ty', '--r'].forEach(function (k) { el.style.removeProperty(k); }); ti.style.opacity = to.style.opacity = '';
      if (dx > 110) yes(); else if (dx < -110) no();
    }
    el.addEventListener('pointerup', end); el.addEventListener('pointercancel', end);
  }
  function no() {
    var el = top(); if (!el || el.classList.contains('flipped')) return;
    el.querySelector('.pc-tint.out').style.opacity = 1; el.classList.add('gone-l');
    setTimeout(function () { S.i++; drawDeck(); }, 300);
  }
  function yes() {
    var el = top(); if (!el || el.classList.contains('flipped')) return;
    if (S.bal < 1) { toast('Your balance is $0. Add credit first.'); return; }
    S.pending = D.pitches[S.i]; flip(el, true);
  }

  /* ------------------------------------------------------------------ how much: the card turns over */
  var AMT = 25, PASS_HTML = $('no').innerHTML, GO_HTML = $('yes').innerHTML;
  /* the back is the front with one thing changed: the big number is yours now, the line it is going into stays in view, and the two buttons stay where the thumb is */
  function backHtml(p) {
    return '<div class="pc-tag"><span>Invest in</span><em>' + esc(pitch(p).right) + '</em></div>' +
      '<label class="pc-amt"><span>$</span><input id="amt" inputmode="numeric" autocomplete="off" maxlength="6" aria-label="Amount"></label>' +
      '<div class="pc-sub">' + esc(nameOf(p)) + '<span id="amtSub"></span></div><div class="pc-chart"></div><div class="pc-chips" id="chips">' +
      [10, 25, 50].filter(function (v) { return v < S.bal; }).map(function (v) { return '<button type="button" data-a="' + v + '">$' + v + '</button>'; }).join('') +
      '<button type="button" data-a="' + S.bal + '">All</button></div>';
  }
  function acts(flipped) {
    $('no').innerHTML = flipped ? 'Not now' : PASS_HTML;
    if (!flipped) $('yes').innerHTML = GO_HTML;
  }
  function flip(el, toBack) {
    el.classList.add('turn');
    setTimeout(function () {
      var p = D.pitches[+el.dataset.k];
      if (toBack) {
        el.classList.add('flipped'); el.innerHTML = backHtml(p); drawChart(el.querySelector('.pc-chart'), p);
        acts(true); AMT = Math.min(25, S.bal); setAmt(AMT);
        $('amt').addEventListener('input', function () { var v = this.value.replace(/\D/g, ''); this.value = v; setAmt(+v || 0, true); });
      } else {
        el.classList.remove('flipped'); el.innerHTML = frontHtml(p); drawChart(el.querySelector('.pc-chart'), p); drag(el); acts(false);
      }
      el.classList.remove('turn');
    }, 170);
  }
  function setAmt(v, typing) {
    AMT = Math.max(0, Math.min(S.bal, Math.round(v)));
    var i = $('amt'); if (!typing || +i.value > S.bal) i.value = AMT;
    i.style.width = Math.max(1, String(i.value).length) * .74 + 'em';
    $('amtSub').textContent = 'of your ' + usd(S.bal);
    $('yes').innerHTML = 'Invest ' + usd(AMT);
    [].forEach.call($('chips').children, function (b) { b.classList.toggle('on', +b.dataset.a === AMT); });
  }
  function invest() {
    var el = top(), p = S.pending;
    if (AMT < 1) { toast('Enter an amount first.'); return; }
    S.deals.unshift({ p: p, amt: AMT, at: new Date() }); S.bal -= AMT; drawBal();
    $('nDeals').textContent = S.deals.length;
    el.classList.add('gone-r'); look();             // the card goes to him, and behind him
    toast('Invested ' + usd(AMT) + ' in ' + nameOf(p));
    acts(false);
    S.pending = null;
    setTimeout(function () { S.i++; drawDeck(); }, 520);
  }
  function drawBal() { $('bal').textContent = usd(S.bal); var b = $('addc'); b.classList.remove('tick'); void b.offsetWidth; b.classList.add('tick'); }

  /* ------------------------------------------------------------------ my deals */
  function stat(k, v, cls, small) { return '<div class="pc-stat"><span>' + k + '</span><b class="' + (cls || '') + '">' + v + '</b>' + (small ? '<small>' + small + '</small>' : '') + '</div>'; }
  function spark(p) {   // what you bought into: its line so far
    var pts = calm(dense(p.line).rest, 18), W = 150, H = 40, lo = Infinity, hi = -Infinity, end = pts[pts.length - 1][0], t0 = pts[0][0];
    pts.forEach(function (q) { lo = Math.min(lo, q[1]); hi = Math.max(hi, q[1]); });
    return '<svg class="pc-spark" viewBox="0 0 ' + W + ' ' + H + '" aria-hidden="true"><path d="' + curve(pts.map(function (q) { return [W * (q[0] - t0) / ((end - t0) || 1), 3 + (H - 6) * (1 - (q[1] - lo) / ((hi - lo) || 1))]; })) + '"/></svg>';
  }
  function drawDeals() {
    var inv = S.deals.reduce(function (s, d) { return s + d.amt; }, 0);
    $('dealTiles').innerHTML = stat('Invested', usd(inv)) + stat('Worth now', usd(inv)) + stat('Result', pct(0), 'zero');
    $('dealList').innerHTML = S.deals.length ? S.deals.map(function (d) {
      var p = d.p, dp = p.kind === 'deal' && dealParts(p.name);
      return '<div class="pc-row"><span class="pc-n"><b>' + esc(nameOf(p)) + '</b><span>' + (dp ? esc(dp.buyer + ' buys ' + dp.target) : 'Fund') + '</span></span>' + spark(p) +
        '<span class="pc-r zero" title="Moves with ' + esc(p.kind === 'fund' ? 'the fund\'s index' : 'the card\'s index') + ' from the moment you invested">' + usd(d.amt) + '<small>just in</small></span></div>';
    }).join('') : '<div class="pc-none"><img src="/_pc/nexus-face.webp" alt="">No deals yet. Swipe right on a pitch you like.</div>';
  }

  /* ------------------------------------------------------------------ the pitchboard: every pick, since it was made */
  var BK = 'all', SHOWN = 40;
  function drawBoard() {
    var rows = D.board.filter(function (r) { return BK === 'all' || r.kind === BK; });
    var up = rows.filter(function (r) { return r.ret > 0; }).length, avg = rows.reduce(function (s, r) { return s + r.ret; }, 0) / (rows.length || 1);
    var best = rows.reduce(function (b, r) { return !b || r.ret > b.ret ? r : b; }, null);
    $('boardTiles').innerHTML = stat('Up', up + '/' + rows.length) + stat('Average', pct(avg, 1), avg >= 0 ? 'pos' : 'neg') + (best ? stat('Best', pct(best.ret), 'pos') : '');
    var cap = Math.max.apply(null, rows.map(function (r) { return Math.abs(r.ret); }).concat([1]));
    $('strip').innerHTML = rows.slice().reverse().map(function (r) {
      var h = Math.max(3, 50 * Math.abs(r.ret) / cap);   // half the strip each way from the zero line
      return '<i title="' + esc(r.kind === 'fund' ? r.name : r.ticker) + ' ' + pct(r.ret) + '"><b class="' + (r.ret >= 0 ? 'up' : 'dn') + '" style="height:' + h.toFixed(1) + '%"></b></i>';
    }).join('');
    $('boardSrc').textContent = 'Cymetica AI’s picks so far · ' + D.as_of;
    $('boardSrc').title = 'Every fund since it went live (its own index history) and every deal-ripple card since it was minted (its index against its base).';
    $('board').innerHTML = rows.slice(0, SHOWN).map(function (r) {
      var nm = r.kind === 'fund' ? r.name : r.ticker, sub = r.kind === 'fund' ? 'Fund' : r.name.replace(/\s*\(\$[\d.]+[BM]\)\s*$/, '').replace(' to acquire ', ' buys ');
      return '<div class="pc-row"><span class="pc-n"><b>' + esc(nm) + '</b><span title="' + esc(sub) + '">' + esc(sub) + '</span></span>' +
        '<span class="pc-r ' + (r.ret > 0 ? 'pos' : r.ret < 0 ? 'neg' : 'zero') + '">' + pct(r.ret) + '<small>' + day(r.since) + '</small></span></div>';
    }).join('');
    $('more').hidden = rows.length <= SHOWN;
  }

  /* ------------------------------------------------------------------ wiring */
  function view(v) {
    pc.dataset.view = v; pc.scrollTop = 0;
    $('deck').style.display = $('acts').style.display = v === 'deck' ? '' : 'none';
    [].forEach.call(document.querySelectorAll('.pc-tabs button'), function (a) { a.classList.toggle('on', a.dataset.tab === v); });
    if (v === 'deals') { drawDeals(); $('nDeals').textContent = ''; }
    if (v === 'board') drawBoard();
    if (v === 'deck') drawDeck(false);
  }
  function toast(t) { var el = $('toast'); el.textContent = t; el.hidden = false; clearTimeout(toast.h); toast.h = setTimeout(function () { el.hidden = true; }, 3000); }

  document.addEventListener('click', function (e) {
    var a = e.target.closest('.pc [data-tab]'); if (a) { e.preventDefault(); view(a.dataset.tab); return; }
    var k = e.target.closest('#boardSeg button');
    if (k) { BK = k.dataset.k; SHOWN = 40; [].forEach.call($('boardSeg').children, function (b) { b.classList.toggle('on', b === k); }); drawBoard(); return; }
    var c = e.target.closest('#chips button'); if (c) { setAmt(+c.dataset.a); return; }
    var id = (e.target.closest('button, a') || {}).id, t = top(), turned = t && t.classList.contains('flipped');
    if (id === 'no') { if (turned) { S.pending = null; flip(t, false); } else no(); }
    else if (id === 'yes') { if (turned) invest(); else yes(); }
    else if (id === 'more') { SHOWN += 40; drawBoard(); }
    else if (id === 'addc') toast('Mock: on the real page this adds credit from your USDC balance.');
    else if (id === 'push') { e.preventDefault(); hidePush(); view('deck'); }
  });
  document.addEventListener('keydown', function (e) {
    var t = top();
    if (t && t.classList.contains('flipped')) { if (e.key === 'Escape' || e.key === 'ArrowLeft') { S.pending = null; flip(t, false); } if (e.key === 'Enter' || e.key === 'ArrowRight') invest(); return; }
    if (pc.dataset.view !== 'deck' || /INPUT|TEXTAREA/.test(e.target.tagName) || e.target.isContentEditable) return;
    if (e.key === 'ArrowLeft') no(); if (e.key === 'ArrowRight') yes();
  });
  var rz; addEventListener('resize', function () { layout(); clearTimeout(rz); rz = setTimeout(redraw, 120); });
  if (!CALM && window.matchMedia && matchMedia('(hover: hover)').matches) addEventListener('pointermove', function (e) {   // the light in the glass follows the pointer
    var c = top(); if (!c) return;
    var r = c.getBoundingClientRect();
    c.style.setProperty('--gx', (100 * (e.clientX - r.left) / r.width).toFixed(1) + '%'); c.style.setProperty('--gy', (100 * (e.clientY - r.top) / r.height).toFixed(1) + '%');
  });

  function hidePush() { var p = $('push'); if (p.hidden) return; p.classList.add('out'); setTimeout(function () { p.hidden = true; p.classList.remove('out'); }, 350); }
  layout(); $('bal').textContent = usd(S.bal);
  var q = location.search.match(/view=(deals|board)/);
  if (q) view(q[1]); else drawDeck();
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(function () { layout(); redraw(); });
  if (D.pitches.length && !/nopush/.test(location.search)) setTimeout(function () {   // the notification Cymetica would send when Nexus has a pitch
    $('pushT').textContent = D.pitches.length + ' new pitch' + (D.pitches.length > 1 ? 'es' : '') + ' for you';
    $('pushS').textContent = D.pitches.map(function (p) { return p.kind === 'fund' ? p.name + ' ' + pct(p.ret) : money(p.size) + ' mega deal'; }).join(' · ');
    $('push').hidden = false; setTimeout(hidePush, 6000);
  }, 2400);
})();
