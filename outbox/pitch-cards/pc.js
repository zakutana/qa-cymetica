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
  var ROBOT = '<svg viewBox="0 0 40 40"><use href="#pc-nexus"/></svg>';

  var S = { bal: 100, deals: [], i: 0, pending: null };

  /* ------------------------------------------------------------------ a pitch, in Nexus's words, from the data */
  function dealParts(name) {
    var m = name.replace(/\s*\(\$[\d.]+[BM]\)\s*$/, '').split(' to acquire ');
    return m.length === 2 ? { buyer: m[0], target: m[1] } : null;
  }
  function money(v) { return v >= 1e9 ? '$' + (v / 1e9).toFixed(1) + 'B' : '$' + Math.round(v / 1e6) + 'M'; }
  function pitch(p) {
    if (p.kind === 'fund') return {
      tag: '<span class="at-tag ok">FUND</span>', when: 'live ' + p.weeks + ' weeks',
      big: '<b class="pos">' + pct(p.ret) + '</b><span>' + esc(p.name) + ' · live since ' + day(p.since) + '</span>',
      color: 'g', facts: [[pct(p.ret30), 'last 30 days'], [pct(p.maxdd), 'worst dip', 'The deepest fall from a high since it went live']],
      say: esc(p.name) + ' is ' + pct(p.ret) + ' since it went live ' + p.weeks + ' weeks ago, and still climbing: ' + pct(p.ret30) + ' in the last 30 days. Want a piece?'
    };
    var dp = dealParts(p.name), rf = D.ripple_fund, bd = D.big_deals;
    return {
      tag: '<span class="at-tag wait">BIG DEAL</span>', when: ago(p.since),
      big: '<b>' + money(p.size) + '</b><span>' + esc(dp ? dp.buyer + ' buys ' + dp.target : p.name) + '</span>',
      color: 'c', facts: [[pct(p.ret), p.ticker + ' card', 'The ripple card on ' + p.ticker + ' since it was minted on ' + day(p.since)],
        rf ? [pct(rf.ret), 'ripple fund', 'The M&A Ripple Fund, live since ' + day(rf.since)] : null,
        bd ? [bd.up + '/' + bd.n, 'big deals up', 'Ripple cards on $10B+ deals so far: ' + bd.up + ' of ' + bd.n + ' up, ' + pct(bd.avg, 2) + ' on average'] : null].filter(Boolean),
      say: (dp ? esc(dp.buyer) + ' is buying ' + esc(dp.target) + ' for ' + money(p.size) + '. ' : 'A ' + money(p.size) + ' deal. ') +
        'A deal this size moves the companies around it. My pick is ' + esc(p.ticker) + ': ' + pct(p.ret) + ' since the news. In?'
    };
  }
  function chart(spark, color) {
    var W = 400, H = 132, P = 6, n = spark.length;
    var lo = Math.min.apply(null, spark), hi = Math.max.apply(null, spark), r = hi - lo || 1;
    var x = function (i) { return P + (W - 2 * P) * i / (n - 1); }, y = function (v) { return P + (H - 2 * P) * (1 - (v - lo) / r); };
    var line = spark.map(function (v, i) { return (i ? 'L' : 'M') + x(i).toFixed(1) + ' ' + y(v).toFixed(1); }).join('');
    var col = color === 'g' ? '#00ff88' : '#00cfff';
    return '<svg class="pc-chart" viewBox="0 0 ' + W + ' ' + H + '" preserveAspectRatio="none" aria-hidden="true">' +
      '<line class="base" x1="0" x2="' + W + '" y1="' + y(spark[0]).toFixed(1) + '" y2="' + y(spark[0]).toFixed(1) + '"/>' +
      '<path d="' + line + 'L' + x(n - 1).toFixed(1) + ' ' + H + 'L' + x(0) + ' ' + H + 'Z" fill="url(#pc-area' + (color === 'g' ? '' : '-c') + ')"/>' +
      '<path class="ln" d="' + line + '" stroke="' + col + '" filter="url(#pc-glow)" vector-effect="non-scaling-stroke"/>' +
      '<circle cx="' + x(n - 1).toFixed(1) + '" cy="' + y(spark[n - 1]).toFixed(1) + '" r="4.5" fill="' + col + '" filter="url(#pc-glow)"/></svg>';
  }
  function cardHtml(p, cls) {
    var q = pitch(p);
    return '<article class="pc-card ' + cls + '">' +
      '<div class="pc-top"><span class="pc-ava">' + ROBOT + '</span><span class="pc-who">NEXUS</span>' + q.tag + '<span class="pc-when">' + esc(q.when) + '</span></div>' +
      '<div class="pc-big">' + q.big + '</div>' + chart(p.spark, q.color) +
      '<div class="pc-facts">' + q.facts.map(function (f) { return '<span class="at-ktag"' + (f[2] ? ' title="' + esc(f[2]) + '"' : '') + '><b>' + esc(f[0]) + '</b>' + esc(f[1]) + '</span>'; }).join('') + '</div>' +
      '<p class="pc-say">' + q.say + '</p>' +
      '<i class="pc-stamp in">INVEST</i><i class="pc-stamp out">PASS</i></article>';
  }

  /* ------------------------------------------------------------------ the deck */
  function drawDeck() {
    var P = D.pitches, h = '';
    for (var k = Math.min(P.length - 1, S.i + 2); k >= S.i; k--) h += cardHtml(P[k], k === S.i ? 'top' : k === S.i + 1 ? 'back1' : 'back2');
    if (S.i >= P.length) h = '<div class="pc-empty">' + ROBOT + '<h3>That’s all for now</h3><p>Nexus pitches only when the data is strong. You get a notification when it has one.</p>' +
      '<span class="at-lbl" title="A fund: live ' + D.bar.fund_weeks + '+ weeks, +' + D.bar.fund_ret + '% or more since it went live, up over the last 30 days. A deal: $' + (D.bar.deal_usd / 1e9) + 'B or more, in the last ' + D.bar.deal_days + ' days, with a live ripple card.">Nexus’s bar ⓘ</span></div>';
    $('deck').innerHTML = h;
    $('acts').classList.toggle('off', S.i >= P.length);
    var left = P.length - S.i;
    $('nNew').textContent = left > 0 ? left : '';
    var top = $('deck').querySelector('.pc-card.top');
    if (top) drag(top);
  }
  function drag(el) {
    var x0 = 0, y0 = 0, dx = 0, on = false, si = el.querySelector('.pc-stamp.in'), so = el.querySelector('.pc-stamp.out');
    el.addEventListener('pointerdown', function (e) { on = true; x0 = e.clientX; y0 = e.clientY; dx = 0; el.classList.add('drag'); el.setPointerCapture(e.pointerId); });
    el.addEventListener('pointermove', function (e) {
      if (!on) return;
      dx = e.clientX - x0; var dy = (e.clientY - y0) * 0.25;
      el.style.transform = 'translate(' + dx + 'px,' + dy + 'px) rotate(' + dx / 18 + 'deg)';
      si.style.opacity = Math.max(0, Math.min(1, dx / 110)); so.style.opacity = Math.max(0, Math.min(1, -dx / 110));
    });
    function end() {
      if (!on) return; on = false; el.classList.remove('drag'); el.style.transform = ''; si.style.opacity = so.style.opacity = '';
      if (dx > 110) yes(); else if (dx < -110) no();
    }
    el.addEventListener('pointerup', end); el.addEventListener('pointercancel', end);
  }
  function top() { return $('deck').querySelector('.pc-card.top'); }
  function no() {
    var el = top(); if (!el) return;
    el.querySelector('.pc-stamp.out').style.opacity = 1; el.classList.add('gone-l');
    setTimeout(function () { S.i++; drawDeck(); }, 330);
  }
  function yes() {
    var el = top(); if (!el) return;
    if (S.bal < 1) { toast('Your balance is $0. Add credit first.'); return; }
    el.querySelector('.pc-stamp.in').style.opacity = 1; el.classList.add('park');
    S.pending = D.pitches[S.i]; openSheet(S.pending);
  }

  /* ------------------------------------------------------------------ how much */
  var AMT = 25;
  function openSheet(p) {
    var name = p.kind === 'fund' ? p.name : p.ticker + ' ripple card';
    $('sheetT').textContent = 'How much for ' + name + '?';
    AMT = Math.min(25, S.bal); $('amtR').max = S.bal; $('amtR').value = AMT;
    $('chips').innerHTML = [10, 25, 50].filter(function (v) { return v < S.bal; }).map(function (v) { return '<button type="button" data-a="' + v + '">$' + v + '</button>'; }).join('') +
      '<button type="button" data-a="' + S.bal + '">All</button>';
    setAmt(AMT); $('sheet').hidden = false;
  }
  function setAmt(v) {
    AMT = Math.max(1, Math.min(S.bal, Math.round(v)));
    $('amt').textContent = usd(AMT); $('amtR').value = AMT; $('invest').textContent = 'Invest ' + usd(AMT);
    $('amtR').style.setProperty('--p', (S.bal > 1 ? 100 * (AMT - 1) / (S.bal - 1) : 100).toFixed(1) + '%');   // the filled part of the track
    [].forEach.call($('chips').children, function (b) { b.classList.toggle('on', +b.dataset.a === AMT); });
  }
  function closeSheet(done) {
    $('sheet').hidden = true;
    var el = top();
    if (done) {
      S.deals.unshift({ p: S.pending, amt: AMT, at: new Date() }); S.bal -= AMT; drawBal();
      if (el) { el.classList.remove('park'); el.classList.add('gone-r'); }
      toast('Invested ' + usd(AMT) + '. Nexus is on it: watch it in My deals.');
      setTimeout(function () { S.i++; drawDeck(); }, 330);
    } else if (el) { el.classList.remove('park'); el.querySelector('.pc-stamp.in').style.opacity = ''; }
    S.pending = null;
  }
  function drawBal() { $('bal').textContent = usd(S.bal); }

  /* ------------------------------------------------------------------ my deals */
  function tile(k, v, cls, small) { return '<div class="pc-tile"><span class="at-lbl">' + k + '</span><b class="' + (cls || '') + '">' + v + '</b>' + (small ? '<small>' + small + '</small>' : '') + '</div>'; }
  function drawDeals() {
    var inv = S.deals.reduce(function (s, d) { return s + d.amt; }, 0);
    $('dealTiles').innerHTML = tile('Invested', usd(inv)) + tile('Now', usd(inv)) + tile('Result', usd(0, 2), '', 'since you invested') + tile('Deals', S.deals.length);
    $('dealList').innerHTML = S.deals.length ? S.deals.map(function (d) {
      var p = d.p, nm = p.kind === 'fund' ? p.name : p.ticker + ' · ' + (dealParts(p.name) ? dealParts(p.name).buyer + ' buys ' + dealParts(p.name).target : p.name);
      return '<div class="pc-row new"><span class="d">just now</span><span class="n">' + (p.kind === 'fund' ? '<span class="at-tag ok">FUND</span>' : '<span class="at-tag wait">DEAL</span>') +
        '<b>' + esc(nm) + '</b></span><span class="d">' + usd(d.amt) + ' in</span><span class="r zero" title="Moves with ' + esc(p.kind === 'fund' ? 'the fund\'s index' : 'the card\'s index') + ' from the moment you invested">' + pct(0, 2) + '</span></div>';
    }).join('') : '<div class="pc-dempty">' + ROBOT + 'No deals yet. Swipe right on a pitch.</div>';
  }

  /* ------------------------------------------------------------------ the pitchboard: every pick, since it was made */
  var BK = 'all', SHOWN = 40;
  function drawBoard() {
    var rows = D.board.filter(function (r) { return BK === 'all' || r.kind === BK; });
    var up = rows.filter(function (r) { return r.ret > 0; }).length, avg = rows.reduce(function (s, r) { return s + r.ret; }, 0) / (rows.length || 1);
    var best = rows.reduce(function (b, r) { return !b || r.ret > b.ret ? r : b; }, null);
    $('boardTiles').innerHTML = tile('Picks', rows.length.toLocaleString('en-US')) + tile('Up', up.toLocaleString('en-US'), 'pos', Math.round(100 * up / (rows.length || 1)) + '% of picks') +
      tile('Average', pct(avg, 2), avg >= 0 ? 'pos' : 'neg', 'since the pick') + (best ? tile('Best', pct(best.ret), 'pos', best.kind === 'fund' ? best.name : best.ticker) : '');
    $('boardSrc').textContent = 'Cymetica AI’s picks so far · as of ' + D.as_of;
    $('boardSrc').title = 'Every fund since it went live (its own index history) and every deal-ripple card since it was minted (its index against its base). The pitches you see in the deck are marked green.';
    var cap = 25, live = {};
    D.pitches.forEach(function (p) { live[p.kind + (p.id || p.name)] = 1; });
    $('board').innerHTML = rows.slice(0, SHOWN).map(function (r) {
      var w = Math.min(50, 50 * Math.abs(r.ret) / cap), col = r.ret >= 0 ? 'var(--at-green)' : 'var(--at-red)';
      var nm = r.kind === 'fund' ? r.name : r.ticker + ' · ' + r.name.replace(/\s*\(\$[\d.]+[BM]\)\s*$/, '');
      return '<div class="pc-row' + (live[r.kind + (r.id || r.name)] ? ' new' : '') + '"><span class="d">' + day(r.since) + '</span>' +
        '<span class="n">' + (r.kind === 'fund' ? '<span class="at-tag ok">FUND</span>' : '<span class="at-tag wait">DEAL</span>') + '<b title="' + esc(nm) + '">' + esc(nm) + '</b></span>' +
        '<span class="pc-bar"><i style="' + (r.ret >= 0 ? 'left:50%' : 'right:50%') + ';width:' + w.toFixed(1) + '%;background:' + col + '"></i></span>' +
        '<span class="r ' + (r.ret > 0 ? 'pos' : r.ret < 0 ? 'neg' : 'zero') + '">' + pct(r.ret) + '</span></div>';
    }).join('');
    $('more').hidden = rows.length <= SHOWN;
  }

  /* ------------------------------------------------------------------ wiring */
  function view(v) {
    $('pc').dataset.view = v;
    [].forEach.call(document.querySelectorAll('.pc .at-nav a'), function (a) { a.classList.toggle('on', a.dataset.tab === v); });
    if (v === 'deals') drawDeals(); if (v === 'board') drawBoard();
  }
  function toast(t) { var el = $('toast'); el.textContent = t; el.hidden = false; clearTimeout(toast.h); toast.h = setTimeout(function () { el.hidden = true; }, 2800); }

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
    else if (id === 'push') { e.preventDefault(); $('push').hidden = true; view('deck'); }
    else if (e.target === $('sheet')) closeSheet(false);
  });
  $('amtR').addEventListener('input', function () { setAmt(+this.value); });
  document.addEventListener('keydown', function (e) {
    if (!$('sheet').hidden) { if (e.key === 'Escape') closeSheet(false); if (e.key === 'Enter') closeSheet(true); return; }
    if ($('pc').dataset.view !== 'deck' || /INPUT|TEXTAREA/.test(e.target.tagName) || e.target.isContentEditable) return;
    if (e.key === 'ArrowLeft') no(); if (e.key === 'ArrowRight') yes();
  });

  drawBal(); drawDeck();
  if (/view=(deals|board)/.test(location.search)) view(RegExp.$1);
  if (D.pitches.length) setTimeout(function () {   // the notification Cymetica would send when Nexus has a pitch
    $('pushT').textContent = 'Nexus has ' + D.pitches.length + ' pitch' + (D.pitches.length > 1 ? 'es' : '') + ' for you';
    $('pushS').textContent = D.pitches.map(function (p) { return p.kind === 'fund' ? p.name + ' ' + pct(p.ret) : money(p.size) + ' deal'; }).join(' · ');
    $('push').hidden = false; setTimeout(function () { $('push').hidden = true; }, 9000);
  }, 1400);
})();
