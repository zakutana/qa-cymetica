  // ---------------------------------------------------------------- v4: BLIND for a run asked with the two questions
  // The weeks (or Flash hours) it chose on, then the ones it never saw behind a wall; the wall lifts, each unseen week
  // shows what its coin did, and the best few setups light up week by week: green made money, red lost.
  function v4DrawBlind(p, r) {
    var fl = !!r.flash, sel = 0, jud = 0, unit = fl ? 'HOURS' : 'WEEKS';
    if (fl) { var hs = (r.history || {})[(r.search_markets || ['BTC'])[0]] || {}; sel = hs.selection_windows || 0; jud = hs.judged_windows || 0; }
    else { sel = (r.selection || {}).weeks || 0; jud = (r.judged || {}).weeks || 0; }
    if (!sel || !jud) return;
    var x0 = 30, x1 = W - 30, gap = 18, tw = x1 - x0 - gap, sw = tw * sel / (sel + jud), jx = x0 + sw + gap, jw = x1 - jx;
    var ty = 64, th = Math.max(30, Math.min(44, H * 0.09));
    txt(num(sel) + ' ' + unit + ' TO CHOOSE', x0, 30, '700 13px ' + MONO, C.cyan, 'left');
    txt(num(jud) + ' ' + unit + ' IT NEVER SAW', x1, 30, '700 13px ' + MONO, C.text, 'right');
    // the weeks it chose on fill in
    var sb = Math.min(sel, 52), fill = ease(seg(p, 0.02, 0.24)), cwS = sw / sb;
    for (var i = 0; i < sb; i++) {
      if (i / sb > fill) break;
      ctx.fillStyle = 'rgba(0, 207, 255, ' + (0.35 + 0.4 * (i % 2)) + ')'; ctx.fillRect(x0 + i * cwS + 1, ty, Math.max(1, cwS - 2), th);
    }
    txt('CHOSEN HERE', x0, ty + th + 18, '700 11px ' + MONO, C.cyan, 'left');
    // the rows the reactor lights: the winners first, then the nearest misses; their windows are the unseen weeks
    var all = M.candidates.slice().sort(function (a, b) { return (b.won - a.won) || (b.held - a.held); });
    var ref = all.filter(function (c) { return (c.windows || []).length; })[0];
    var wins = ref ? ref.windows.filter(function (w) { return !w.seen; }) : [];
    var nb = wins.length || Math.min(jud, 60), cw = jw / nb;
    var lift = ease(seg(p, 0.42, 0.56)), drop = ease(seg(p, 0.24, 0.34));
    // what each unseen week was: its coin's kind
    for (i = 0; i < nb; i++) {
      var w = wins[i], col = !w ? 'rgba(127, 147, 173, .22)' : w.kind === 'rising' ? 'rgba(0, 255, 136, .55)' : w.kind === 'falling' ? 'rgba(255, 68, 68, .55)' : 'rgba(127, 147, 173, .35)';
      ctx.globalAlpha = 0.25 + 0.75 * lift; ctx.fillStyle = col; ctx.fillRect(jx + i * cw + 1, ty, Math.max(1, cw - 2), th); ctx.globalAlpha = 1;
    }
    if (wins.length) {
      ctx.globalAlpha = lift;
      var lx = jx; [['RISING', C.green], ['FALLING', C.red], ['RANGE', C.dim]].forEach(function (k) {
        ctx.fillStyle = k[1]; ctx.fillRect(lx, ty + th + 12, 10, 10); txt(k[0], lx + 16, ty + th + 18, '700 11px ' + MONO, C.dim, 'left'); lx += 94;
      });
      txt(ref.market + ' WEEKS', x1, ty + th + 18, '700 11px ' + MONO, C.dim3, 'right');
      ctx.globalAlpha = 1;
    }
    // the wall: down while it chooses, up when it judges
    if (drop > 0 && lift < 1) {
      var wy = ty - 8 - (1 - drop) * 160 - lift * (th + 60), wh = th + 16;
      ctx.save(); ctx.globalAlpha = 1 - lift; rr(jx - 4, wy, jw + 8, wh, 10); ctx.clip();
      ctx.fillStyle = '#0d1520'; ctx.fillRect(jx - 4, wy, jw + 8, wh);
      ctx.strokeStyle = 'rgba(255, 68, 68, .35)'; ctx.lineWidth = 6;
      for (var hx = jx - wh - 10; hx < x1 + 10; hx += 26) { ctx.beginPath(); ctx.moveTo(hx, wy + wh); ctx.lineTo(hx + wh, wy); ctx.stroke(); }
      ctx.restore();
      ctx.globalAlpha = 1 - lift; rr(jx - 4, wy, jw + 8, wh, 10); ctx.strokeStyle = C.red; ctx.lineWidth = 2; ctx.stroke();
      txt('🙈  BLIND', jx + jw / 2, wy + wh / 2, '400 22px ' + BLACK, C.text, 'center', 12); ctx.globalAlpha = 1;
      if (drop >= 1) once('v4wall', function () { shake = 10; burst(jx + jw / 2, ty + th / 2, C.red, 40, 6); });
    }
    // the setups, week by week
    var top = ty + th + 52, rowH = Math.max(34, Math.min(52, (H - top - 16) / 5)), n = Math.max(1, Math.min(5, Math.floor((H - top - 10) / rowH)));
    all.slice(0, n).forEach(function (c, r2) {
      var y = top + r2 * rowH + rowH / 2, en = ease(seg(p, 0.56 + r2 * 0.03, 0.64 + r2 * 0.03));
      if (en <= 0) return;
      ctx.globalAlpha = en;
      coin(c.market, x0 + 12, y, 12);
      var nm = c.flash ? (c.model_label || c.model).replace(/^Flash /, '') + (c.side === 'short' ? ' ↘' : ' ↗') : setupText(c.setup) + (c.side === 'short' ? ' ↘' : '');
      ctx.font = '700 13px ' + MONO; while (ctx.measureText(nm).width > sw - 40 && nm.length > 4) nm = nm.slice(0, -2);
      txt(nm, x0 + 32, y - 7, '700 13px ' + MONO, c.won ? C.green : C.text, 'left');
      var kk = c.kind && c.kinds && c.kinds[c.kind] ? c.kinds[c.kind] : null;
      txt((c.won ? '✓ ' : '✗ ') + (kk ? kk.won + '/' + kk.windows + ' ' + (c.kind === 'bull' ? 'RISING' : c.kind === 'bear' ? 'FALLING' : 'WEEKS') + ' · ' : '') + pct(c.held), x0 + 32, y + 10, '700 11px ' + MONO, c.won ? C.green : C.red, 'left');
      ctx.globalAlpha = 1;
      var cw2 = c.windows || [];
      if (cw2.length) {
        var byId = {}; cw2.forEach(function (w) { byId[w.id] = w; });
        for (var j = 0; j < nb; j++) {
          var ww = wins[j] && byId[wins[j].id], a = ease(seg(p, 0.6 + j / nb * 0.3 + r2 * 0.01, 0.62 + j / nb * 0.3 + r2 * 0.01));
          if (!ww || a <= 0) continue;
          var thin = ww.trades != null && ww.trades < 5;
          ctx.globalAlpha = a; ctx.fillStyle = thin ? C.dim3 : ww.made_money ? C.green : 'rgba(255, 68, 68, .75)';
          rr(jx + j * cw + 1.5, y - rowH * 0.3, Math.max(1, cw - 3), rowH * 0.6, Math.min(4, cw / 3)); ctx.fill(); ctx.globalAlpha = 1;
        }
      } else if (c.windows_total) {
        var share = c.windows_won / c.windows_total, a2 = ease(seg(p, 0.62 + r2 * 0.02, 0.9));
        rr(jx, y - 9, jw, 18, 9); ctx.fillStyle = 'rgba(255, 68, 68, .22)'; ctx.fill();
        var fw = Math.max(3, jw * share * a2); rr(jx, y - 9, fw, 18, Math.min(9, fw / 2)); ctx.fillStyle = C.green; ctx.fill();
        txt(num(c.windows_won) + ' / ' + num(c.windows_total) + ' WON', jx + jw - 10, y + 1, '700 11px ' + MONO, C.text, 'right');
      }
    });
  }
