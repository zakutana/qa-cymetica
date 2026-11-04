  // ================================================================= quant-lab-v3 mock: everything below is ours
  var Q3 = { open: false, n: 10, older: false };
  function q3Run() { var id = LAST_GOOD && LAST_GOOD.id; return (M.runs || []).filter(function (r) { return r.id === id; })[0] || null; }
  function q3Windows() { var r = q3Run(); return r && r.windows && r.windows.length ? r.windows : null; }
  function q3Paused() { var m = S.mine; return !!(m && m.status === 'paused'); }
  // the window a setup was chosen on: what it is counted on before that start, it had already seen
  function q3ChosenStart(c) {
    var w = q3Windows() || [], out = null;
    (c.why || []).forEach(function (t) {
      var id = String(t).split(':')[0], f = w.filter(function (x) { return x.id === id; })[0];
      if (f && (out == null || f.start < out)) out = f.start;
    });
    return out;
  }
  function q3Seen(c, w) { var s = q3ChosenStart(c); return !!s && w.start < s; }
  // nearest to passing: enough windows, then enough trades, then the distance to the bar
  function q3Near(a, b) {
    function miss(c) { return (c.windows_won >= (c.windows_needed || 3) ? 0 : 2) + (c.trades >= (c.min_trades || 20) ? 0 : 1); }
    return miss(a) - miss(b) || ((a.bar - a.held) - (b.bar - b.held));
  }
  function q3Parts() {
    var won = M.candidates.filter(function (c) { return c.won; }), out = M.candidates.filter(function (c) { return !c.won; }).sort(q3Near);
    return { won: won.sort(function (a, b) { return b.held - a.held; }), out: out };
  }
  function q3Why(c) {
    if (c.won) return '<b class="q2-up">✓ PASSED</b>';
    var why = c.label === 'below_bar' ? 'under the bar' : c.label === 'too_few_trades' ? 'too few trades' : c.windows_won + ' of ' + c.windows_total + ' windows';
    return '<span class="q2-down">✗ ' + esc(why) + '</span>';
  }
  function q3Row(c, wins) {
    var cells = wins.map(function (ww) {
      var w = (c.windows || []).filter(function (x) { return x.id === ww.id; })[0];
      if (!w) return '<span class="q3-c">—</span>';
      var seen = q3Seen(c, w), thin = w.trades != null && w.trades < 5;
      var tip = (w.trades == null ? '' : w.trades + ' trades · ') + c.market + ' moved ' + pct(w.market_move_pct) + ' · 12 coins held ' + pct(w.basket_move_pct) +
        (seen ? ' · already seen: this window is inside the search period the setup was chosen on' : '') + (thin ? ' · under 5 trades: does not count as a window' : '');
      return '<span class="q3-c ' + (seen ? 'q3-seen' : thin ? 'q3-thin' : w.made_money ? 'q2-up' : 'q2-down') + '" title="' + esc(tip) + '">' + (seen ? 'seen ' : '') + (w.missing ? 'no bars' : pct(w.return_pct)) + '<i>' + (w.trades == null ? '' : w.trades + 't') + '</i></span>';
    }).join('');
    var set = String(c.settings).replace(' / ', ' · ');
    return '<div class="q3-row' + (c.won ? ' q3-won' : '') + '" data-model="' + esc(c.model) + '" data-market="' + esc(c.market) + '">' +
      '<span class="q3-nm" title="' + esc(setupText(c.setup)) + (c.side === 'short' ? ' · short rule' : '') + '">' + esc(setupText(c.setup)) + (c.side === 'short' ? ' <em>short</em>' : '') + '</span>' +
      '<span class="q3-cn">' + coinImgTag(c.market) + esc(c.market) + '</span>' +
      '<span class="q3-set" title="' + esc(set) + '">' + esc(set) + '</span>' + cells +
      '<span class="q3-p ' + (c.held >= 0 ? 'q2-up' : 'q2-down') + '">' + pct(c.held) + '</span>' +
      '<span class="q3-b">' + pct(c.bar) + '</span>' +
      '<span class="q3-t">' + (c.trades == null ? '—' : c.trades) + '</span>' +
      '<span class="q3-v">' + q3Why(c) + '</span></div>';
  }
  function coinImgTag(m) { return '<span class="q2-coin q3-coin">' + coinImg(m) + '</span>'; }
  function q3Head(wins) {
    return '<div class="q3-row q3-hd"><span>Setup</span><span>Coin</span><span>Settings</span>' + wins.map(function (w) {
      var up = w.kind === 'rising';
      return '<span class="q3-wh" title="' + esc('Held-back window, 36 days. The 12 coins held at equal weight moved ' + pct(w.basket_move_pct) + ': information, not the pass rule.') + '">' + esc(day(w.start) + '–' + day(w.end)) +
        '<b class="' + (up ? 'q2-up' : 'q2-down') + '">' + (up ? '↗ ' : '↘ ') + pct(w.basket_move_pct) + '</b></span>';
    }).join('') + '<span title="All windows together">Pooled</span><span title="The bar for this setup, from every combination ever tried">Bar</span><span>Trades</span><span></span></div>';
  }
  function q3Top() {
    var wins = q3Windows();
    if (!wins || !M.candidates.some(function (c) { return c.pooled; })) return false;
    var p = q3Parts(), one = p.won.length > 1 && p.won.every(function (c) { return c.market === p.won[0].market; });
    var html = q3Head(wins);
    if (p.won.length) html += p.won.map(function (c) { return q3Row(c, wins); }).join('');
    else html += '<div class="q3-none">No setup passed.</div>';
    if (one) html += '<div class="q3-note" title="Same coin, same kind of entry: read them as one market\'s result, not ' + p.won.length + ' independent finds">All ' + p.won.length + ' on ' + esc(p.won[0].market) + ': one market\'s result. <i>seen = the window it was chosen on · grey = under 5 trades</i></div>';
    html += '<button type="button" class="q3-more" data-q3="open">' + (Q3.open ? '▾' : '▸') + ' ' + p.out.length + ' thrown out' + (Q3.open ? '' : ' · open the nearest misses') + '</button>';
    if (Q3.open) {
      html += p.out.slice(0, Q3.n).map(function (c) { return q3Row(c, wins); }).join('');
      if (Q3.n < p.out.length) html += '<button type="button" class="q3-more q3-m2" data-q3="more">+ 10 more · ' + (p.out.length - Q3.n) + ' left</button>';
    }
    $('top').innerHTML = html;
    return true;
  }
  function q3Runs() {
    var el = $('runs'), runs = M.runs || [], cur = M.picked ? M.picked.id : (LAST_GOOD ? LAST_GOOD.id : null);
    var show = Q3.older ? runs : runs.filter(function (r, i) { return i < 5 || r.id === cur; });
    el.innerHTML = show.map(function (r) {
      var st = r.status === 'failed' ? '<b class="q2-down" title="' + esc(r.error_label || '') + '">FAILED</b>' : active(r) ? '<b class="q2-cy">RUNNING</b>' : r.nothing_new ? '<b title="Every setup was already tested on the latest prices">NOTHING NEW</b>' : '<b class="q2-up">DONE</b>';
      var names = (r.models || []).map(function (m) { return modelInfo(m.model)[1] + (m.n > 1 ? ' ×' + m.n : ''); }).join(', ');
      var miss = (r.markets_missing || []).map(function (m) { return typeof m === 'string' ? m : m.market; });
      return '<button type="button" class="q3-run' + (r.id === cur ? ' q2-on' : '') + '" data-run="' + r.id + '">' +
        '<b class="q3-id">#' + r.id + '</b><span>' + esc(stamp(r.finished_at || r.requested_at)) + '</span><span>' + st + ' <em>' + esc(r.origin === 'owner' ? 'you' : 'daily') + '</em></span>' +
        '<span title="Combinations this run tried">' + (r.status === 'failed' ? '—' : num(r.tried || 0) + ' tried') + '</span>' +
        '<span title="' + esc(names) + '">' + (r.status === 'failed' || !r.shortlisted ? '—' : r.shortlisted + ' shortlisted · ' + (r.models || []).length + ' models') + '</span>' +
        '<span class="' + (r.won ? 'q2-up' : '') + '">' + (r.status === 'failed' || !r.shortlisted ? '' : (r.won || 0) + ' won') + '</span>' +
        '<span class="q2-down">' + (miss.length ? esc(miss.join(', ')) + ' not loaded' : '') + '</span></button>';
    }).join('') + (runs.length > 5 ? '<button type="button" class="q3-more q3-m2" data-q3="older">' + (Q3.older ? 'Newest 5 only' : 'Older runs · ' + (runs.length - show.length)) + '</button>' : '') +
      (M.picked ? '<button type="button" class="q2-ib" data-run="newest" title="Back to the newest blind test">↺ newest</button>' : '');
    return true;
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest && e.target.closest('[data-q3]'); if (!b) return;
    var k = b.getAttribute('data-q3');
    if (k === 'open') { Q3.open = !Q3.open; Q3.n = 10; renderTop(); }
    else if (k === 'more') { Q3.n += 10; renderTop(); }
    else if (k === 'older') { Q3.older = !Q3.older; renderRuns(); }
  });
  // THE BAR and BLIND draw the winners and the nearest misses, no more
  function q3Bar() {
    if (!q3Windows()) return { list: M.candidates, more: 0 };
    var p = q3Parts(), all = p.won.concat(p.out), cap = Math.max(5, Math.min(14, Math.floor((W - 140) / 120)));
    return { list: all.slice(0, cap), more: Math.max(0, all.length - cap) };
  }
  function q3DrawBlind(p) {
    var wins = q3Windows(), rows = q3Bar().list.slice(0, 5), left = Math.min(280, W * 0.22), right = W - 30, gap = 10, cw = (right - left - gap * (wins.length - 1)) / wins.length;
    txt(wins.length + ' WINDOWS · 36 DAYS EACH · 54 DAYS BEFORE EACH TO CHOOSE', 30, 26, '700 13px ' + MONO, C.dim, 'left');
    var top = 52, hh = 84, rowH = Math.min(58, (H - top - hh - 34) / Math.max(1, rows.length));
    wins.forEach(function (w, i) {
      var a = ease(seg(p, 0.04 + i * 0.16, 0.16 + i * 0.16)), x = left + i * (cw + gap), up = w.kind === 'rising', col = up ? C.green : C.red;
      ctx.globalAlpha = 0.2 + a * 0.8;
      rr(x, top, cw, hh, 12); ctx.fillStyle = up ? 'rgba(0, 255, 136, .09)' : 'rgba(255, 68, 68, .09)'; ctx.fill(); ctx.strokeStyle = col; ctx.lineWidth = 1.5; ctx.stroke();
      txt(day(w.start) + '–' + day(w.end), x + cw / 2, top + 20, '700 12px ' + MONO, C.dim, 'center');
      txt((up ? '↗ ' : '↘ ') + pct(w.basket_move_pct), x + cw / 2, top + 54, '400 ' + (cw < 190 ? 19 : 25) + 'px ' + BLACK, col, 'center', 10);
      ctx.globalAlpha = 1;
    });
    rows.forEach(function (c, r) {
      var y = top + hh + 18 + r * rowH + rowH / 2, enter = ease(seg(p, 0.08, 0.2));
      ctx.globalAlpha = enter;
      coin(c.market, 44, y, 13);
      var lab = setupText(c.setup) + ' · ' + c.market; ctx.font = '700 13px ' + MONO; while (ctx.measureText(lab).width > left - 76 && lab.length > 4) lab = lab.slice(0, -2);
      txt(lab, 66, y, '700 13px ' + MONO, c.won ? C.green : C.text, 'left');
      ctx.globalAlpha = 1;
      wins.forEach(function (ww, i) {
        var w = (c.windows || []).filter(function (x) { return x.id === ww.id; })[0]; if (!w) return;
        var a = ease(seg(p, 0.1 + i * 0.16 + r * 0.012, 0.2 + i * 0.16 + r * 0.012)), x = left + i * (cw + gap) + cw / 2, seen = q3Seen(c, w), thin = w.trades != null && w.trades < 5;
        ctx.globalAlpha = a;
        txt(pct(w.return_pct), x, y - 2, '400 17px ' + BLACK, seen || thin ? C.dim3 : w.made_money ? C.green : C.red, 'center', seen || thin ? 0 : 6);
        txt(seen ? 'SEEN' : (w.trades == null ? '' : w.trades + ' TRADES'), x, y + 16, '700 10px ' + MONO, C.dim3, 'center');
        ctx.globalAlpha = 1;
      });
    });
  }
  // FOUND: one animation, every agent the search found on one screen, each landing in turn
  function q3Cards(x0, pw, p) {
    var all = M.botList.slice().sort(function (a, b) { return b.cand.held - a.cand.held; }), max = 6, list = all.slice(0, max), n = list.length;
    var cols = n <= 1 ? 1 : n <= 4 ? 2 : 3, rows = Math.ceil(n / cols), gap = 12, y0 = 142, ch = Math.min(170, (H - y0 - 22 - gap * (rows - 1)) / rows), cw = (pw - gap * (cols - 1)) / cols;
    list.forEach(function (b, i) {
      var c = b.cand, a = ease(seg(p, 0.5 + i * 0.05, 0.6 + i * 0.05)), x = x0 + (i % cols) * (cw + gap), y = y0 + Math.floor(i / cols) * (ch + gap) + (1 - a) * 30;
      if (a <= 0) return;
      var e = q3Exp(c), live = e && (e.status === 'running' || e.status === 'passed');
      ctx.save(); ctx.globalAlpha = a;
      rr(x, y, cw, ch, 12); ctx.fillStyle = 'rgba(13, 21, 32, .9)'; ctx.fill(); ctx.strokeStyle = 'rgba(0, 255, 136, .4)'; ctx.lineWidth = 1.5; ctx.stroke();
      coin(c.market, x + 24, y + 26, 13);
      var nf = cw < 430 ? 13 : 15, nm = baseOf(c.setup)[1].toUpperCase() + ' · ' + c.market;
      txt(nm, x + 46, y + 20, '400 ' + nf + 'px ' + BLACK, C.text, 'left');
      ctx.font = '700 11px ' + MONO; var st = String(c.settings).replace(' / ', ' · ').replace('entry stricter: ', '').replace('entry looser: ', ''), st0 = st; while (ctx.measureText(st + '…').width > cw - 200 && st.length > 4) st = st.slice(0, -1);
      txt(st === st0 ? st : st + '…', x + 46, y + 38, '700 11px ' + MONO, C.dim, 'left');
      txt(pct(c.held), x + cw - 14, y + 24, '400 24px ' + BLACK, C.green, 'right', 12);
      txt(c.trades + ' TRADES · ' + (live ? 'RUNNING' : 'QUEUED'), x + cw - 14, y + 46, '700 11px ' + MONO, live ? C.green : C.cyan, 'right');
      // its result on each window: a bar and the number
      var wins = q3Windows() || [], hiV = 1, by = y + 60, bh = ch - 60 - 24, base = by + bh * 0.72, bw = (cw - 28) / Math.max(1, wins.length);
      (c.windows || []).forEach(function (w) { hiV = Math.max(hiV, Math.abs(w.return_pct || 0)); });
      wins.forEach(function (ww, k) {
        var w = (c.windows || []).filter(function (q) { return q.id === ww.id; })[0]; if (!w) return;
        var seen = q3Seen(c, w), thin = w.trades != null && w.trades < 5, col = seen || thin ? C.dim3 : w.return_pct >= 0 ? C.green : C.red, h = Math.max(2, Math.abs(w.return_pct) / hiV * bh * 0.5), bx = x + 14 + k * bw;
        ctx.fillStyle = col; ctx.fillRect(bx + 2, w.return_pct >= 0 ? base - h : base, bw - 58, h);
        txt(pct(w.return_pct), bx + bw - 52, base - 6, '700 11px ' + MONO, col, 'left');
        txt(day(w.start), bx + 2, y + ch - 11, '700 10px ' + MONO, C.dim3, 'left');
      });
      ctx.restore();
    });
    if (all.length > max) txt('+' + (all.length - max) + ' MORE', x0 + pw, 118, '700 12px ' + MONO, C.dim, 'right');
    var one = all.length > 1 && all.every(function (b) { return b.cand.market === all[0].cand.market; });
    if (one) txt('ALL ON ' + all[0].cand.market + ': ONE MARKET\'S RESULT', x0 + pw, 92, '700 12px ' + MONO, C.cyan, 'right');
  }
  function q3Exp(c) { return ((S.ov && S.ov.experiments) || []).filter(function (x) { return x.id === c.experiment_id; })[0] || null; }
  function q3Order() {
    var blocks = document.querySelectorAll('section.q2-block');
    if (blocks.length < 3) return;
    var runs = blocks[0], blind = blocks[1], bots = blocks[2];
    bots.parentNode.insertBefore(runs, bots.nextSibling);
    var h = blind.querySelector('h2'); if (h) h.textContent = '🏆 WINNERS';
    [].forEach.call(blind.querySelectorAll('.q2-bh > *'), function (el, i) { if (el.tagName !== 'H2' && !/^top(label|note)$/.test(el.id || '') && !el.classList.contains('sp')) el.hidden = true; });
    var note = document.createElement('div'); note.id = 'q3paused'; note.className = 'q3-paused'; note.hidden = true;
    $('bots').parentNode.insertBefore(note, $('bots'));
  }
  function q3Note() {
    var el = $('q3paused'); if (!el) return;
    el.hidden = !q3Paused() || !((S.ov && S.ov.experiments) || []).length;
    el.innerHTML = '⏸ <b>Company paused.</b> These bots start when you resume it. <a href="/company/app">Open the company</a>';
    el.title = (S.mine && S.mine.run_state && S.mine.run_state.message) || '';
  }

