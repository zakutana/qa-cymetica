  /* ===== qa-cymetica look patch: the top 3 cards and the Leverage route. Look only: every figure is the engine's. =====
     A card reads top to bottom as: name, the month's profit, four facts, the tree, the steps, chips, the button.
     Every sentence the API sends is kept, folded under "Details". Rows line up across the three cards (subgrid). */
  var LK_U = 1.0;   // css px per tree unit: one scale for every tree, so a long route is taller, never smaller
  var LK_LABEL = { mint: 'MINT', swap: 'SWAP COST' };   // note kinds their label table does not name yet
  function lkMoney(s) {   // "215,000" -> "$215k"
    var v = Number(String(s).replace(/,/g, ''));
    return v >= 1e6 ? '$' + (v / 1e6).toFixed(v % 1e6 ? 1 : 0) + 'M' : v >= 1e3 ? '$' + Math.round(v / 1e3) + 'k' : '$' + v;
  }
  function lkChips(ev) {
    var out = [], fw = ev.fresh_wallet, m;
    if (fw) out.push([fw.ok ? 'g' : 'd', fw.ok ? 'Fresh wallet ✓' : 'Fresh wallet: not confirmed',
      (fw.checks || []).map(function (c) { return c.n + '. ' + c.text; }).join('\n')]);
    (ev.notes || []).forEach(function (n) {
      if (!n || !n.text) return;
      var k = String(n.kind || ''), t = String(n.text);
      if (k === 'range' && n.range_pct != null) {
        out.push(['i', 'Range ±' + Number(n.range_pct).toFixed(0) + '%', t]);
        if (n.full_range_apy_pct != null) out.push(['d', 'Full range ' + Number(n.full_range_apy_pct).toFixed(0) + '%', t]);
      } else if (k === 'loss' && (m = t.match(/lost \$([\d,]+)/))) out.push(['w', 'Past loss ' + lkMoney(m[1]), t]);
      else if (k === 'maturity' && (m = t.match(/\((\d+) days away\)/))) out.push(['i', 'Matures in ' + m[1] + ' d', t]);
      else if (k === 'exit') out.push(['w', 'Slow exit', t]);
      else if (k === 'borrower' && (m = t.match(/(\d+(?:\.\d+)?)%/))) out.push(['w', 'One borrower ' + m[1] + '%', t]);
      else if (k === 'mint') out.push(['i', 'Bought in an open pool', t]);
    });
    return out.map(function (c) { return '<span class="lk-chip lk-' + c[0] + '" title="' + esc(c[2]) + '">' + esc(c[1]) + '</span>'; }).join('');
  }
  function lkDetails(ev, extra) {
    var list = (ev.notes || []).filter(function (n) { return n && n.text && n.kind !== 'fresh' && (ev.tier === 'og' || !/OG Gambler/.test(String(n.text))); });
    var fw = ev.fresh_wallet, rows = list.map(function (n) {
      var k = String(n.kind || 'note').replace(/[^a-z]/g, '');
      return '<li class="nk-' + k + '"><span class="nl">' + esc(NOTE_LABEL[k] || LK_LABEL[k] || 'NOTE') + '</span><span class="nt">' + esc(n.text) + '</span></li>';
    });
    if (fw && fw.checks) rows.push('<li class="nk-fresh"><span class="nl">FRESH WALLET</span><span class="nt">' +
      fw.checks.map(function (c) { return esc(c.text); }).join(' &middot; ') + '. Read only, nothing is sent.</span></li>');
    var b = ev.rate_basis || {};
    if (b.text) rows.push('<li><span class="nl">RATE</span><span class="nt">' + esc(b.text) + '</span></li>');
    (extra || []).forEach(function (x) { rows.push('<li><span class="nl">' + esc(x[0]) + '</span><span class="nt">' + esc(x[1]) + '</span></li>'); });
    rows.push('<li><span class="nl">RISK</span><span class="nt">' + esc(ev.risk_note) + '</span></li>');
    return '<details class="lk-more"><summary><span>Details</span><i>' + rows.length + '</i></summary><ul class="lk-notes">' + rows.join('') + '</ul></details>';
  }
  // the Plan screen (after SELECT STRATEGY) draws its notes through notesHtml: it takes the same chips and Details
  notesHtml = function (ev) { return '<div class="lk-chips lk-plan">' + lkChips(ev) + '</div>' + lkDetails(ev); };
  function lkTree(ev) {
    var svg = tree(ev, { orient: 'v', interactive: true }), vb = svg.match(/viewBox="(-?\d+) (-?\d+) (\d+) (\d+)"/);
    return vb ? svg.replace('<svg class="tree', '<svg width="' + Math.round(vb[3] * LK_U) + '" height="' + Math.round(vb[4] * LK_U) + '" class="tree') : svg;
  }
  function card(ev, i) {
    var r = ev.rule, same = r && Math.abs((r.profit_month_usd || 0) - (ev.profit_month_usd || 0)) < 0.005;
    var rule = !r ? '' : '<p class="lk-rule"><span>BY THE RULE</span>' + (same ? 'the same' : signed(r.profit_month_usd) + ' &middot; ' + pct(r.net_apy_pct) + '/yr') + '</p>';
    var liq = ev.liquidation
      ? '<b class="neg" title="' + esc(ev.liquidation.text) + '">' + ev.liquidation.distance_pct + '% away</b>'
      : '<b class="none">None</b>';
    var chain = ev.chain_path || [];
    return '<article class="scard lk' + (ev.top_pick ? ' toppick' : '') + '" data-i="' + i + '" style="--cd:' + (i * 0.14).toFixed(2) + 's">' +
      '<div class="hd lk-head"><span class="rankhx"><span>' + (ev.rank || i + 1) + '</span></span><div><h3>' + esc(ev.name) + '</h3><span class="venue">' + esc(ev.venue) + '</span></div>' + (ev.top_pick ? '<span class="tp">TOP PICK</span>' : '') + '</div>' +
      '<div class="lk-hero"><p class="lbl">MAX PROFIT / MONTH <button type="button" class="info" data-tip="maxprofit" aria-label="What max profit assumes">i</button></p>' +
        '<div class="lk-heroline"><div class="pm bump' + (ev.profit_month_usd < 0 ? ' neg' : '') + '">' + signed(ev.profit_month_usd) + '</div>' +
        '<div class="lk-ret"><b>' + pct(ev.return_pct) + '</b><span>×' + ev.multiplier.toFixed(4) + '</span></div></div>' + rule + '</div>' +
      '<div class="lk-facts">' +
        '<span><small>LEVERAGE</small><b' + (ev.leverage > 1 ? '' : ' class="none"') + '>' + (ev.leverage > 1 ? ev.leverage.toFixed(2) + 'x' : 'None') + '</b></span>' +
        '<span><small>LIQUIDATION</small>' + liq + '</span>' +
        '<span><small>' + (chain.length > 1 ? 'CHAINS' : 'CHAIN') + '</small><b>' + esc(chain.join(' → ')) + '</b></span>' +
        '<span><small>COSTS</small><b>' + usd(ev.costs.total_usd) + '</b></span></div>' +
      '<div class="lk-stage">' + lkTree(ev) + '</div>' +
      '<ol class="steps lk-steps">' + stepsHtml(ev) + '</ol>' +
      '<div class="lk-chips">' + lkChips(ev) + '</div>' +
      '<div class="lk-cta"><button type="button" class="sel" data-sel="' + i + '">SELECT STRATEGY →</button></div>' +
      lkDetails(ev) + '</article>';
  }
  function renderLev() {
    var box = $('#lev-route'); if (!box) return;
    var t = S.tier === 'og' ? tierOf('og') : null;
    if (!t || (!t.leverage_route && !t.leverage_route_reason)) { box.hidden = true; box.innerHTML = ''; return; }
    box.hidden = false; box.classList.add('lk');
    var ev = t.leverage_route;
    if (!ev) { box.innerHTML = '<p class="lbl">LEVERAGE ROUTE</p><p class="levnone">' + esc(t.leverage_route_reason) + '</p>'; return; }
    var sc = ev.scenarios || {}, sh = sc.shock_pct || 20, lm = sc.liquidation_move_pct;
    var liq = lm == null ? 'No liquidation' : esc(sc.liquidation_move_asset) + ' down ' + lm.toFixed(1) + '%';
    // the price scale: -shock .. +shock, the liquidation line on it
    var at = lm == null ? null : Math.max(0, 50 - (Math.min(lm, sh) / sh) * 50);
    var scale = '<div class="lk-scale" aria-hidden="true"><i class="lost" style="width:' + (at == null ? 0 : at).toFixed(1) + '%"></i>' +
      (at == null ? '' : '<i class="mark" style="left:' + at.toFixed(1) + '%"></i>') + '<i class="now"></i>' +
      '<span class="l">−' + sh + '%</span><span class="c">today</span><span class="r">+' + sh + '%</span></div>';
    var extra = [];
    if (sc.price_basis !== 'underlying') extra.push(['LOAN', 'This loop borrows the asset it holds against, so the price of the underlying moves collateral and loan together; the liquidation move is the collateral slipping against the loan.']);
    extra.push(['OUTCOMES', 'On ' + usd(ev.amount) + '. Outcomes include the month\'s profit; they are not guaranteed.']);
    box.innerHTML = '<div class="lk-levhead"><p class="lbl">LEVERAGE ROUTE</p><h3>' + esc(ev.name) + '</h3><span class="venue">' + esc(ev.venue) + ' &middot; the highest leverage still in profit after borrow cost</span></div>' +
      '<div class="lk-levstats">' +
        '<span><small>LEVERAGE</small><b>' + ev.leverage.toFixed(2) + 'x</b></span>' +
        '<span><small>MAX PROFIT / MONTH</small><b class="pos">' + signed(ev.profit_month_usd) + '</b></span>' +
        '<span><small>PRICE +' + sh + '%</small><b class="' + (sc.up_usd < 0 ? 'neg' : 'pos') + '">' + signed(sc.up_usd) + '</b></span>' +
        '<span><small>PRICE −' + sh + '%</small><b class="' + (sc.down_usd < 0 ? 'neg' : 'pos') + '">' + signed(sc.down_usd) + '</b>' + (sc.down_liquidated ? '<em>liquidated, the deposit is lost</em>' : '') + '</span>' +
        '<span><small>LIQUIDATED AT</small><b class="neg">' + liq + '</b></span></div>' +
      scale +
      '<div class="lk-chips">' + lkChips(ev) + '</div>' + lkDetails(ev, extra);
  }
  // one scale for the three trees: when the widest does not fit its card, all three shrink together
  function lkFit() {
    var svgs = $$('#top3 .lk-stage .tree'), s = 1, row = window.innerWidth > 1100;   // stacked cards each fit on their own
    function fit(v) { var w = +v.getAttribute('width'), room = v.parentNode.clientWidth - 24; return w && room > 0 ? Math.min(1, room / w) : 1; }
    svgs.forEach(function (v) { s = Math.min(s, fit(v)); });
    svgs.forEach(function (v) { v.style.width = Math.floor(+v.getAttribute('width') * (row ? s : fit(v))) + 'px'; });
  }
  new MutationObserver(lkFit).observe($('#top3'), { childList: true });
  window.addEventListener('resize', lkFit);
  // ?tier=og opens the top 3 straight away (the copy has no other way to link to a state)
  (function () {
    var q = new URLSearchParams(location.search).get('tier'), tries = 0;
    if (!q) return;
    (function wait() {
      var t = tierOf(q);
      if (t) { S.tier = q; S.cardLev = {}; find(); }
      else if (tries++ < 100) setTimeout(wait, 200);
    })();
  })();
