/* FOMO Radar redesign mock. Every figure is their live API, read through serve.py (GET only). */
(function () {
  'use strict';
  var API = '/api/v1/clones/fomo-radar/';
  var HOST = 'https://cymetica.com';
  var EXPLORER = { robinhood: 'https://robinhoodchain.blockscout.com/address/', solana: 'https://solscan.io/account/' };
  var state = { chain: 'robinhood', filter: 'all', sig: {}, open: null };
  var $ = function (id) { return document.getElementById(id); };

  // ---------- format (en-US: the page is English) ----------
  function esc(s) {
    return String(s === null || s === undefined ? '' : s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }
  function has(v) { return v !== null && v !== undefined && !(typeof v === 'number' && isNaN(v)); }
  function num(v, d) { return has(v) ? Number(v).toLocaleString('en-US', { maximumFractionDigits: d === undefined ? 2 : d }) : '—'; }
  function usd(v) { return has(v) ? '$' + num(v, 0) : '—'; }
  function usdK(v) {
    if (!has(v)) return '—';
    var a = Math.abs(v);
    if (a >= 1e9) return '$' + (v / 1e9).toFixed(2) + 'B';
    if (a >= 1e6) return '$' + (v / 1e6).toFixed(2) + 'M';
    if (a >= 1e5) return '$' + (v / 1e3).toFixed(0) + 'K';
    return usd(v);
  }
  function pct(v, d) { return has(v) ? (100 * v).toFixed(d === undefined ? 1 : d) + '%' : '—'; }
  function ago(s) {
    if (!has(s)) return '—';
    s = Math.max(0, Math.round(s));
    if (s < 60) return s + 's';
    if (s < 3600) return Math.round(s / 60) + 'm';
    if (s < 86400) return (s / 3600).toFixed(1) + 'h';
    return (s / 86400).toFixed(1) + 'd';
  }
  function dur(s) { if (!s) return '—'; return s < 3600 ? Math.round(s / 60) + ' min' : (s / 3600).toFixed(1) + ' h'; }
  function short(a) { a = String(a || ''); return a.length > 14 ? a.slice(0, 6) + '…' + a.slice(-4) : a; }
  function addr(a, chain) {
    if (!a) return '—';
    return '<a href="' + esc(EXPLORER[chain || state.chain] + a) + '" target="_blank" rel="noopener" title="' + esc(a) + '">' + esc(short(a)) + '</a>'
      + '<button type="button" class="fr-copy" data-copy="' + esc(a) + '" title="Copy address">⧉</button>';
  }
  function getJSON(path) {
    return fetch(API + path, { headers: { Accept: 'application/json' } }).then(function (r) { return r.ok ? r.json() : null; }).catch(function () { return null; });
  }

  // ---------- signals ----------
  var HEAD_RH = ['#', 'Token', 'Conviction', '3× in 72h', 'Smart buyers', 'Wallets / entities', 'ETH in', 'Liquidity', 'First buy', ''];
  var HEAD_SOL = ['#', 'Token', 'Conviction', '3× in 72h', 'Credible wallets', 'Buys / sells 24h', 'Volume 24h', 'Liquidity', 'Pool age', ''];
  var CLS_RH = ['rk', '', '', '', '', 'c-we', '', '', '', ''];
  var CLS_SOL = ['rk', '', '', '', '', '', '', '', 'c-age', ''];

  function tags(r) {
    var h = '';
    if (r.hot) h += '<span class="tag hot">HOT</span>';
    if (r.fresh) h += '<span class="tag fresh">FRESH</span>';
    if (r.exit_signal) h += '<span class="tag exit">EXIT</span>' + (r.exit_reason ? '<span class="exitreason">' + esc(r.exit_reason) + '</span>' : '');
    if (r.thin) h += '<span class="tag thin" title="Largest buy at 5% slippage is under $500">THIN</span>';
    if (r.same_name_on_board) h += '<span class="tag dupe" title="Other launches on this board share this name — the addresses are the identity">SAME NAME ×' + (r.same_name_on_board + 1) + '</span>';
    if (r.same_block_groups || r.atomic_groups) h += '<span class="tag exit" title="Qualified buyers whose first buy landed in the same block / same transaction">CO-BUY</span>';
    if (r.sibling_wallets) h += '<span class="tag ent" title="Sibling wallets resolved into one entity — they cast ONE vote, not ' + (r.sibling_wallets + 1) + '">SIBLINGS −' + r.sibling_wallets + '</span>';
    return h;
  }
  // their probability rule: no number below the minimum sample; a regime-gated figure shows as gated
  function prob(r) {
    if (!has(r.probability_3x_72h)) return { cls: 'none', big: esc(r.probability_display || 'insufficient history'), sub: '' };
    var g = r.probability_3x_72h_gated, sup = has(g) && g < r.probability_3x_72h;
    var big = pct(sup ? g : r.probability_3x_72h), sub = sup
      ? 'gated from ' + pct(r.probability_3x_72h) + ' · ' + esc(r.regime_state || '') : 'raw · ' + esc(r.signal_type || '');
    if (r.type_precision) sub += ' · ' + esc(r.type_precision.display || '');
    return { cls: sup ? 'sup' : '', big: big, sub: sub };
  }
  function cell(cls, main, sub) { return '<div class="fr-c ' + cls + '">' + main + (sub ? '<small>' + sub + '</small>' : '') + '</div>'; }

  function rowRH(r, i) {
    var p = prob(r);
    var dots = (r.top_buyers || []).slice(0, 8).map(function (b) {
      return '<i class="' + (b.gone ? 'gone' : '') + '" title="' + esc(b.wallet_short) + ' · score ' + num(b.score, 0) + (b.gone ? ' · GONE' : '') + '"></i>';
    }).join('');
    return '<div class="fr-row' + (i < 3 ? ' top' : '') + '" data-i="' + i + '">'
      + '<div class="rk">' + (i + 1) + '</div>'
      + '<div class="fr-tok"><div class="top"><span class="sym">' + esc(r.symbol || r.name || 'token') + '</span><span class="nm">' + esc(r.name || '') + '</span></div><div class="tags">' + tags(r) + '</div></div>'
      + '<div class="fr-c fr-conv"><b>' + num(r.conviction, 1) + '</b><div class="fr-bar2"><i style="width:' + Math.max(2, Math.min(100, r.conviction || 0)) + '%"></i></div></div>'
      + '<div class="fr-c fr-p ' + p.cls + '"><b>' + p.big + '</b>' + (p.sub ? '<small title="' + p.sub + '">' + p.sub + '</small>' : '') + '</div>'
      + '<div class="fr-c">' + num(r.qualified_buyers, 0) + ' <small style="display:inline;margin:0">avg score ' + num(r.avg_buyer_score, 1) + '</small><div class="fr-dots">' + (dots || '<span class="fr-none">—</span>') + '</div></div>'
      + cell('c-we', num(r.wallets, 0) + ' / <span style="color:var(--c)">' + num(r.entities, 0) + '</span>',
        r.sibling_wallets ? r.sibling_wallets + ' sibling wallet' + (r.sibling_wallets === 1 ? '' : 's') + ' merged' : 'all independent')
      + cell('', num(r.eth_invested, 3) + ' ETH', usd(r.usd_invested))
      + cell('', usd(r.liquidity_usd) + ' <small style="display:inline;margin:0">' + num(r.liquidity_eth, 3) + ' ETH</small>',
        'max @5% ' + usd(r.max_buy_5pct_usd) + ' · held ' + usd(r.curve_held_usd))
      + cell('', ago(r.first_buy_seconds_ago), has(r.token_age_seconds) ? 'age ' + ago(r.token_age_seconds) : '')
      + '<div class="fr-chev">›</div>'
      + '<div class="m-line">' + num(r.qualified_buyers, 0) + ' smart · ' + usd(r.usd_invested) + ' in · liq ' + usd(r.liquidity_usd) + ' · ' + ago(r.first_buy_seconds_ago) + '</div>'
      + '</div>';
  }
  function rowSOL(r, i) {
    var p = prob(r);
    var cred = r.credibility_available
      ? cell('', '<span style="color:var(--g)">' + num(r.credible_wallet_share * 100, 0) + '%</span>', num(r.qualified_buyers, 0) + ' of ' + num(r.buyers_with_record_seen, 0) + ' indexed buyers · avg ' + num(r.avg_buyer_score, 0))
      : cell('', '<span style="color:var(--mut);font-size:12px">no track record yet</span>', 'ranked by buy pressure');
    var link = r.page_url ? '<a class="out" href="' + esc(r.page_url) + '" target="_blank" rel="noopener" title="Open the pool">↗</a>' : '';
    return '<div class="fr-row' + (i < 3 ? ' top' : '') + '" data-i="' + i + '" data-href="' + esc(r.page_url || '') + '">'
      + '<div class="rk">' + (i + 1) + '</div>'
      + '<div class="fr-tok"><div class="top"><span class="sym">' + esc(r.symbol || r.name || 'token') + '</span><span class="nm">' + esc(r.name || '') + '</span></div><div class="tags">' + tags(r) + '</div></div>'
      + '<div class="fr-c fr-conv"><b>' + num(r.conviction, 1) + '</b><div class="fr-bar2"><i style="width:' + Math.max(2, Math.min(100, r.conviction || 0)) + '%"></i></div><small>' + (r.credibility_available ? 'trader credibility' : 'buy pressure') + '</small></div>'
      + '<div class="fr-c fr-p ' + p.cls + '"><b>' + p.big + '</b>' + (p.sub ? '<small title="' + p.sub + '">' + p.sub + '</small>' : '') + '</div>'
      + cred
      + cell('', '<span class="fr-pos">' + num(r.buys, 0) + '</span> / <span class="fr-neg">' + num(r.sells, 0) + '</span>', '1h ' + num(r.buys_1h, 0) + ' / ' + num(r.sells_1h, 0) + ' · ' + num(r.buyers, 0) + ' buyers')
      + cell('', usdK(r.usd_invested), '1h ' + usdK(r.usd_1h))
      + cell('', usdK(r.liquidity_usd), '')
      + cell('c-age', ago(r.token_age_seconds), '')
      + '<div>' + link + '</div>'
      + '<div class="m-line">' + num(r.buys, 0) + ' buys / ' + num(r.sells, 0) + ' sells · vol ' + usdK(r.usd_invested) + ' · liq ' + usdK(r.liquidity_usd) + ' · ' + ago(r.token_age_seconds) + '</div>'
      + '</div>';
  }

  function walletRow(w, showBought) {
    var basis = showBought
      ? num(w.bought_tokens, 2) + ' bought · ' + num(w.sold_tokens, 2) + ' sold'
        + (has(w.cost_basis_eth) ? ' · basis ' + Number(w.cost_basis_eth).toPrecision(3) + ' ETH/tok' : '')
        + (w.first_buy_block ? ' · blk ' + w.first_buy_block : '') + (w.cluster_size > 1 ? ' · cluster ×' + w.cluster_size : '')
      : num(w.sold_tokens, 2) + ' sold · bought ' + num(w.bought_tokens, 2);
    return '<div class="fr-w"><span>' + addr(w.wallet || w.address, 'robinhood') + '<span class="bs">' + basis + '</span></span>'
      + '<span><span class="sc">' + num(w.score, 0) + '</span>' + (w.gone ? '<span class="gone">GONE</span>' : '') + '</span></div>';
  }
  function detail(r) {
    var p = prob(r);
    var ent = (r.top_entities || []).map(function (e) {
      return '<div class="fr-w"><span>' + addr(e.entity_id || e.entity_short, 'robinhood') + '<span class="bs">' + e.wallets + ' wallet' + (e.wallets === 1 ? '' : 's')
        + (e.rules && e.rules.length ? ' · ' + esc(e.rules.join(', ')) : '') + ' · ' + num(e.eth, 3) + ' ETH · vote ' + num(e.vote_weight, 3) + '</span></span>'
        + '<span class="sc">' + num(e.score, 0) + '</span></div>';
    }).join('') || '<div class="fr-none">No qualified entity on this curve yet.</div>';
    var buyers = (r.top_buyers || []).map(function (b) { return walletRow(b, true); }).join('') || '<div class="fr-none">No tracked buyers yet.</div>';
    var sellers = (r.top_sellers || []).map(function (s) { return walletRow(s, false); }).join('') || '<div class="fr-none">No sellers yet on this curve.</div>';
    var now = Date.now() / 1000;
    var flow = (r.flow || []).map(function (f) {
      return '<div class="fr-w"><span><span class="' + (f.side === 'buy' ? 'buy' : 'sell') + '">' + esc((f.side || '').toUpperCase()) + '</span> ' + addr(f.address, 'robinhood')
        + ' <span style="color:var(--mut)">' + num(f.score, 0) + '</span></span><span>' + (has(f.usd) ? usd(f.usd) : num(f.eth, 4) + ' ETH') + ' · ' + ago(Math.max(0, now - f.ts)) + ' ago</span></div>';
    }).join('') || '<div class="fr-none">No recent trade legs.</div>';
    var page = r.page_url ? (r.page_url.charAt(0) === '/' ? HOST + r.page_url : r.page_url) : '';
    return '<div class="fr-detail"><div class="fr-dtop">'
      + '<span><b>' + num(r.wallets, 0) + '</b> wallets → <b>' + num(r.entities, 0) + '</b> entities · ' + (r.sibling_wallets ? r.sibling_wallets + ' sibling wallet' + (r.sibling_wallets === 1 ? '' : 's') + ' merged' : 'all independent') + '</span>'
      + '<span>3× chance <b>' + p.big + '</b> ' + p.sub + '</span>'
      + '<span>' + esc(short(r.token_address)) + ' <button type="button" data-copy="' + esc(r.token_address) + '">copy</button></span>'
      + (page ? '<a href="' + esc(page) + '" target="_blank" rel="noopener">Token page ↗</a>' : '')
      + (r.explorer_url ? '<a href="' + esc(r.explorer_url) + '" target="_blank" rel="noopener">Explorer ↗</a>' : '')
      + '</div><div class="fr-dgrid">'
      + '<div class="fr-dcol"><h4>Entities — one vote each</h4>' + ent + '</div>'
      + '<div class="fr-dcol"><h4>Buyers — bought / sold / basis</h4>' + buyers + '</div>'
      + '<div class="fr-dcol"><h4>Top sellers</h4>' + sellers + '</div>'
      + '<div class="fr-dcol"><h4>Flow tape (last legs)</h4><div class="fr-tape">' + flow + '</div></div>'
      + '</div></div>';
  }

  function renderRows() {
    var d = (state.sig[state.chain] || {})[state.filter];
    var list = $('rows');
    var rh = state.chain === 'robinhood';
    list.className = 'fr-list ' + (rh ? 'rh' : 'sol');
    if (!d) { list.innerHTML = '<div class="fr-empty">Data temporarily unavailable — retrying</div>'; return; }
    var rows = d.rows || [];
    var head = (rh ? HEAD_RH : HEAD_SOL).map(function (h, k) { return '<div class="' + (rh ? CLS_RH : CLS_SOL)[k] + '">' + h + '</div>'; }).join('');
    if (!rows.length) { list.innerHTML = '<div class="fr-row hd">' + head + '</div><div class="fr-empty">' + esc(d.message || 'No signal matches this filter right now.') + '</div>'; return; }
    list.innerHTML = '<div class="fr-row hd">' + head + '</div>' + rows.map(rh ? rowRH : rowSOL).join('');
    if (rh && state.open !== null) {
      var idx = rows.findIndex(function (r) { return r.token_address === state.open; });
      if (idx >= 0) toggle(idx, true); else state.open = null;
    }
  }
  function toggle(i, keep) {
    var d = state.sig[state.chain][state.filter], r = d.rows[i];
    var list = $('rows'), old = list.querySelector('.fr-detail'), row = list.querySelector('.fr-row[data-i="' + i + '"]');
    var was = row && row.classList.contains('open');
    if (old) old.remove();
    list.querySelectorAll('.fr-row.open').forEach(function (x) { x.classList.remove('open'); });
    if (was && !keep) { state.open = null; return; }
    row.classList.add('open');
    row.insertAdjacentHTML('afterend', detail(r));
    state.open = r.token_address;
  }
  $('rows').addEventListener('click', function (e) {
    if (e.target.closest('a,button')) return;
    var row = e.target.closest('.fr-row[data-i]');
    if (!row) return;
    if (state.chain === 'solana') { if (row.dataset.href) window.open(row.dataset.href, '_blank', 'noopener'); return; }
    toggle(Number(row.dataset.i));
  });

  // ---------- hero, meta, regime ----------
  var REG = { 'risk-on': '', caution: 'cy', 'risk-off': 'rd' };
  function renderMeta(d) {
    var rh = state.chain === 'robinhood';
    if (d.updated_at) $('upd').textContent = new Date(d.updated_at * 1000).toLocaleTimeString('en-GB');
    var g = d.regime;
    if (g && g.label) {
      $('regState').textContent = String(g.state || g.label).toUpperCase();
      $('regState').className = 'v ' + (REG[g.state] || 'cy');
      $('regExp').textContent = 'exposure ×' + num(g.exposure_multiplier, 2) + (g.suppressed ? ' · signals suppressed' : '');
      var det = [];
      if (has(g.median_24h_pct)) det.push('median 24h ' + num(g.median_24h_pct, 1) + '%');
      if (has(g.share_below_open)) det.push(num(100 * g.share_below_open, 0) + '% below their 24h open');
      det.push(num(g.tokens, 0) + ' tracked tokens');
      $('regDet').textContent = det.join(' · ');
    }
    var src = d.wallet_source || {};
    if (rh) {
      var w = d.window_seconds || 0, t = d.window_target_seconds || w || 1;
      $('winNow').textContent = dur(w);
      $('winOf').textContent = d.window_complete ? '' : '/ ' + dur(t);
      $('winBar').style.width = Math.min(100, 100 * w / t) + '%';
      $('winNote').textContent = d.window_complete ? 'window complete' : 'filling to ' + dur(t);
      $('heroPill').textContent = num(d.tokens_tracked, 0) + ' tokens · ' + num(d.wallets_tracked, 0) + ' wallets scored · Robinhood Chain';
      $('scanTrio').innerHTML = '<div><b>' + num(d.tokens_tracked, 0) + '</b><span>tokens</span></div><div><b>' + num(d.wallets_tracked, 0) + '</b><span>wallets</span></div><div><b>' + num(d.trades_indexed, 0) + '</b><span>trades</span></div>';
      var er = d.entity_resolution;
      $('scanNote').innerHTML = er ? 'Entities resolved <b style="color:#fff">' + num(er.multi_wallet_entities, 0) + '</b>' + (er.wallets_in_multi_wallet_entities ? ' from <b style="color:#fff">' + num(er.wallets_in_multi_wallet_entities, 0) + '</b> wallets' : '') : '';
      $('kind').className = 'fr-kind'; $('kind').textContent = 'trader-credibility conviction';
      $('signalSub').textContent = 'Live bonding-curve buys on Robinhood Chain (id 4663). Conviction is the credibility-weighted sum of qualified buyers — a wallet needs a score of 60+ from closed, profitable round trips to count.';
    } else {
      $('winNow').textContent = '24 h'; $('winOf').textContent = ''; $('winBar').style.width = '100%'; $('winNote').textContent = 'window complete';
      $('heroPill').textContent = num(d.tokens_tracked, 0) + ' pools · ' + num(src.wallets_with_record, 0) + ' wallets with a record · Solana';
      if (d.credibility_available) {
        $('scanTrio').innerHTML = '<div><b>' + num(d.tokens_tracked, 0) + '</b><span>pools</span></div><div><b>' + num(d.rows_with_credibility, 0) + '<small style="font-size:12px;color:var(--mut)">/' + num(d.tokens_tracked, 0) + '</small></b><span>credible</span></div><div><b>' + num(src.legs_indexed, 0) + '</b><span>swaps parsed</span></div>';
        $('scanNote').innerHTML = 'Wallets with a record <b style="color:#fff">' + num(src.wallets_with_record, 0) + '</b>';
        $('kind').className = 'fr-kind'; $('kind').textContent = 'trader-credibility conviction';
        $('signalSub').textContent = 'Live Solana pools. Swaps are parsed per wallet from a public Solana RPC and run through the same credibility machinery as Robinhood Chain — a wallet needs a score of 60+ from closed, profitable round trips to count. A pool we have not indexed enough swaps for keeps its buy-pressure number and says so.';
      } else {
        $('scanTrio').innerHTML = '<div><b>' + num(d.tokens_tracked, 0) + '</b><span>pools</span></div>';
        $('scanNote').textContent = '';
        $('kind').className = 'fr-kind off'; $('kind').textContent = 'credibility unavailable — buy pressure only';
        $('signalSub').textContent = src.message || 'Per-wallet credibility is unavailable right now — these rows are ranked by pool-level buy pressure, which is wash-tradeable. No trader score is invented.';
      }
    }
    document.querySelectorAll('[data-n]').forEach(function (b) {
      var x = (state.sig[state.chain] || {})[b.dataset.n];
      b.textContent = x ? (x.rows || []).length : '';
    });
  }

  // ---------- calibration ----------
  function tile(k, v, s, cls) { return '<div class="fr-tile"><div class="k">' + k + '</div><div class="v ' + (cls || '') + '">' + v + '</div>' + (s ? '<div class="s">' + s + '</div>' : '') + '</div>'; }
  function renderCal(c) {
    c = c || {};
    var h = tile('Labelled signals', num(c.n_samples, 0), num(c.min_samples, 0) + ' needed', 'c');
    if (c.sufficient) {
      h += tile('Base rate', has(c.base_rate) ? num(100 * c.base_rate, 2) + '%' : '—', 'share of all signals that hit 3×', 'g');
      h += tile('Brier, out of sample', num(c.brier, 4), 'lower is better');
      h += tile('Base rate Brier', num(c.brier_base, 4), 'the bar to beat');
      h += tile('Fitted / tested on', num(c.n_train, 0) + ' <small>/ ' + num(c.n_test, 0) + '</small>', '');
      h += tile('Method', esc(String(c.method || '—')), '', 'sm');
    } else {
      h += tile('Status', esc(c.headline || 'insufficient history'), '', 'sm');
      h += tile('Target', num(c.target_multiple, 0) + '× within ' + num(c.horizon_hours, 0) + 'h', '', 'sm');
    }
    $('calFit').innerHTML = h;
    var bins = c.bins || [];
    if (!bins.length) {
      $('calBins').innerHTML = '<div class="fr-none" style="margin:auto">No out-of-sample bucket yet — the table appears with the first fit.</div>';
    } else {
      var max = Math.max.apply(null, bins.map(function (b) { return Math.max(b.mean_predicted || 0, b.observed || 0); })) || 1;
      $('calBins').innerHTML = bins.map(function (b) {
        return '<div class="fr-bin"><div class="bars">'
          + '<i class="said" style="height:' + (88 * (b.mean_predicted || 0) / max) + '%"><span>' + num(100 * b.mean_predicted, 1) + '</span></i>'
          + '<i class="was" style="height:' + (88 * (b.observed || 0) / max) + '%"><span>' + num(100 * b.observed, 1) + '</span></i></div></div>';
      }).join('');
      $('calBins').insertAdjacentHTML('afterend', '');
      var lab = document.querySelector('.fr-binlab') || (function () { var x = document.createElement('div'); x.className = 'fr-binlab'; $('calBins').after(x); return x; })();
      lab.innerHTML = bins.map(function (b) { return '<div>' + num(100 * b.lo, 0) + '–' + num(100 * b.hi, 0) + '%<small>n=' + num(b.n, 0) + '</small></div>'; }).join('');
    }
    var tp = c.type_precision || {}, keys = Object.keys(tp);
    $('calTypes').innerHTML = keys.length ? keys.map(function (k) {
      var x = tp[k] || {};
      return '<div class="fr-type"><span class="tag ' + ({ hot: 'hot', fresh: 'fresh', exit: 'exit' }[k] || 'thin') + '">' + esc(k.toUpperCase()) + '</span>'
        + (has(x.precision) ? '<div><span class="v">' + pct(x.precision) + '</span><small>' + esc(x.display || '') + '</small></div>'
          : '<div><span class="v none">' + esc(x.display || '—') + '</span></div>') + '</div>';
    }).join('') : '<div class="fr-none">No labelled signal yet.</div>';
  }

  // ---------- backtest ----------
  var RULES = ['Hold to the horizon', 'Trailing stop 30% below the peak', 'Sell half at 2×, trail the rest 30%'];
  function renderBacktest(d) {
    var b = (d && d.backtest) || {}, g = b.gate || {};
    var st = $('btStatus');
    st.textContent = g.publishable ? 'Published' : 'Withheld';
    st.className = 'fr-status ' + (g.publishable ? 'ok' : 'wh');
    var h = '';
    if (g.matured_signals !== undefined) {
      h += tile('Matured signals', num(g.matured_signals, 0), 'since records began');
      h += tile('With a stored price record', num(g.signals_with_path, 0), pct(g.path_coverage) + ' · ' + pct(g.min_coverage) + ' needed');
      h += tile('Usable samples', num(g.admissible_samples, 0), num(g.min_samples, 0) + ' needed');
    }
    if (b.paths_since_iso) h += tile('Records since', esc(String(b.paths_since_iso).replace('T', ' ').slice(0, 16)), 'UTC', 'sm');
    $('btGate').innerHTML = h;
    $('btGate').style.display = h ? '' : 'none';
    var rows = b.results || [];
    var labels = rows.length ? rows.map(function (r) { return r.policy_label; }).filter(function (v, i, a) { return a.indexOf(v) === i; }) : RULES;
    var grid = '<div class="h"></div><div class="h">6 h</div><div class="h">24 h</div><div class="h">72 h</div>';
    labels.forEach(function (lab) {
      grid += '<div class="rl">' + esc(lab) + '</div>';
      [6, 24, 72].forEach(function (hz) {
        var r = rows.find(function (x) { return x.policy_label === lab && Number(x.horizon_hours) === hz; });
        if (!r) { grid += '<div>—</div>'; return; }
        var o = r.out_of_sample || {};
        grid += '<div><b class="' + ((o.ev_every_signal || 0) >= 0 ? 'fr-pos' : 'fr-neg') + '">' + pct(o.ev_every_signal) + '</b><small>MCC ' + (has(o.mcc) ? num(o.mcc, 2) : '—') + (o.passes_l1_gate ? ' ✓' : '')
          + ' · called ' + pct(o.ev_signals_taken) + ' · n=' + num(o.n || 0, 0) + '</small></div>';
      });
    });
    $('btGrid').innerHTML = grid;
    var reasons = g.reasons || [];
    $('btReasons').innerHTML = g.publishable
      ? (b.negative_ev_everywhere ? '<div>Negative expected value under every exit rule at every horizon.</div>' : '<div>Cell: average return on every signal · MCC · return when called.</div>')
      : (reasons.length ? reasons.map(function (r) { return '<div>' + esc(r) + '</div>'; }).join('')
        : '<div>' + (b.status === 'unavailable' ? 'The stored records are not readable right now.' : 'No result yet.') + '</div>');
  }

  // ---------- traders ----------
  var TSUB = {
    robinhood: 'Wallets ranked by their realized track record on Robinhood Chain bonding curves — closed round trips only, shrunk toward 50 by sample size. A wallet we have never seen close a trade scores exactly 50 and does not count as qualified.',
    solana: 'Solana wallets ranked by their realized track record on DEX swaps parsed from a public RPC — closed round trips only, in SOL, scored by the same formula as Robinhood Chain. A wallet we have never seen close a trade scores exactly 50 and does not count as qualified.'
  };
  function renderTraders(d) {
    $('tradersSub').textContent = TSUB[state.chain];
    var el = $('traders');
    var rows = (d && d.rows) || [];
    if (!d) { el.innerHTML = '<div class="fr-empty">Data temporarily unavailable — retrying</div>'; return; }
    if (!rows.length) { el.innerHTML = '<div class="fr-empty">' + esc(d.message || 'No wallet has closed a round trip in the current window yet.') + '</div>'; return; }
    var q = d.qualified_threshold || 60;
    el.innerHTML = '<div class="fr-lb hd"><div>#</div><div>Wallet</div><div class="sc">Score</div><div class="c-rt">Round trips</div><div class="c-wr">Win rate</div><div>Realized</div><div class="c-hold">Avg hold</div></div>'
      + rows.map(function (t, i) {
        var eth = has(t.realized_eth), val = eth ? t.realized_eth : t.realized_sol;
        return '<div class="fr-lb' + (i < 3 ? ' p' + (i + 1) : '') + '"><div class="rk">' + (i + 1) + '</div>'
          + '<div class="wa"><a href="' + esc(t.explorer_url) + '" target="_blank" rel="noopener" title="' + esc(t.wallet) + '">' + esc(short(t.wallet || t.wallet_short)) + '</a>'
          + '<button type="button" class="fr-copy" data-copy="' + esc(t.wallet) + '" title="Copy address">⧉</button></div>'
          + '<div class="sc"><b>' + num(t.score, 1) + '</b><div class="fr-bar2"><i class="' + (t.score >= q ? '' : 'q') + '" style="width:' + Math.min(100, t.score) + '%"></i></div></div>'
          + '<div class="c-rt">' + num(t.round_trips, 0) + '</div>'
          + '<div class="c-wr">' + num(t.win_rate * 100, 0) + '%</div>'
          + '<div class="' + (val >= 0 ? 'fr-pos' : 'fr-neg') + '">' + (val > 0 ? '+' : '') + num(val, 4) + (eth ? ' ETH' : ' SOL') + '</div>'
          + '<div class="c-hold">' + (has(t.avg_hold_seconds) ? ago(t.avg_hold_seconds) : '—') + '</div></div>';
      }).join('');
  }

  // ---------- entities ----------
  function renderEntities(d) {
    var rh = state.chain === 'robinhood';
    document.querySelectorAll('[data-rh]').forEach(function (x) { x.hidden = !rh; });
    if (!rh) return;
    var er = d && d.entity_resolution;
    if (!er || !er.rules) { $('entBig').textContent = '—'; $('entSub').textContent = 'Resolving entities from the live window…'; return; }
    $('entBig').innerHTML = num(er.wallets_in_multi_wallet_entities, 0) + '<small>wallets →</small>' + num(er.multi_wallet_entities, 0) + '<small>entities</small>';
    $('entSub').innerHTML = '<b>' + num(er.entities, 0) + '</b> entities in the window · <b>' + num(er.edges, 0) + '</b> links drawn';
    document.querySelectorAll('#entRules details[data-rule]').forEach(function (el) {
      var keys = el.dataset.rule.split(','), em = el.querySelector('[data-st]');
      var parts = keys.filter(function (k) { return er.rules[k]; }).map(function (k) {
        return (keys.length > 1 ? ({ same_tx: 'tx', same_block: 'block' }[k] || k) + ' ' : '') + er.rules[k];
      });
      var live = keys.every(function (k) { return er.rules[k] === 'live' || er.rules[k] === 'partial'; });
      em.textContent = parts.join(' · ') || '—';
      em.className = live ? 'live' : 'off';
    });
    $('entFallback').textContent = er.fallback || '';
  }

  // ---------- radar ----------
  var cv = $('scopeCv'), ctx = cv.getContext('2d'), tip = $('scopeTip'), blips = [], hover = null, W = 0, H = 0, DPR = 1;
  function hash(s, k) { var h = 2166136261 ^ k; for (var i = 0; i < s.length; i++) { h ^= s.charCodeAt(i); h = Math.imul(h, 16777619); } return (h >>> 0) / 4294967295; }
  function size() {
    var r = cv.getBoundingClientRect(); DPR = Math.min(2, window.devicePixelRatio || 1);
    W = r.width; H = r.height; cv.width = Math.round(W * DPR); cv.height = Math.round(H * DPR);
  }
  function geom() { var Rx = W * 0.46, Ry = Rx * 0.46, cx = W / 2, cy = H * 0.62; return { Rx: Rx, Ry: Ry, cx: cx, cy: cy, maxH: Math.min(H * 0.42, cy - Ry - 40) }; }
  // labels: strongest first, a label that would cover one already placed is left off (hover still names it)
  function placeLabels(pts) {
    var placed = [];
    pts.slice().sort(function (a, b) { return (b.r.conviction || 0) - (a.r.conviction || 0); }).forEach(function (b) {
      b.show = false;
      if (placed.length >= 8) return;
      var rc = { l: b.x - 40, r: b.x + 40, t: b.top - b.s - 36, b: b.top - b.s - 2 };
      if (placed.some(function (p) { return rc.l < p.r && rc.r > p.l && rc.t < p.b && rc.b > p.t; })) return;
      placed.push(rc); b.show = true;
    });
  }
  function setBlips() {
    var d = (state.sig[state.chain] || {}).all;
    var rows = (d && d.rows) || [];
    var max = Math.max.apply(null, rows.map(function (r) { return r.conviction || 0; }).concat([1]));
    var maxEth = Math.max.apply(null, rows.map(function (r) { return r.usd_invested || 0; }).concat([1]));
    var order = rows.map(function (r, i) { return i; }).sort(function (a, b) { return (rows[b].conviction || 0) - (rows[a].conviction || 0); });
    blips = rows.map(function (r, i) {
      var key = r.token_address || r.symbol || String(i);
      return { r: r, i: i, a: hash(key, 1) * Math.PI * 2, rr: 0.2 + 0.76 * Math.sqrt(hash(key, 7)), h: (r.conviction || 0) / max,
        s: 2.5 + 5.5 * Math.sqrt((r.usd_invested || 0) / maxEth), lab: order.indexOf(i) < 7,
        col: r.exit_signal ? '255,68,68' : (r.fresh ? '0,207,255' : '0,255,136'), lit: 0 };
    });
  }
  function draw(t) {
    if (!W) size();
    var G = geom(), sweep = (t / 6000 * Math.PI * 2) % (Math.PI * 2);
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0); ctx.clearRect(0, 0, W, H);
    // disc
    var grd = ctx.createRadialGradient(G.cx, G.cy, 0, G.cx, G.cy, G.Rx);
    grd.addColorStop(0, 'rgba(0,255,136,.10)'); grd.addColorStop(.7, 'rgba(0,207,255,.04)'); grd.addColorStop(1, 'rgba(0,207,255,0)');
    ctx.fillStyle = grd; ctx.beginPath(); ctx.ellipse(G.cx, G.cy, G.Rx, G.Ry, 0, 0, Math.PI * 2); ctx.fill();
    ctx.lineWidth = 1;
    [0.25, 0.5, 0.75, 1].forEach(function (k, n) {
      ctx.strokeStyle = 'rgba(0,207,255,' + (n === 3 ? .32 : .12) + ')';
      ctx.beginPath(); ctx.ellipse(G.cx, G.cy, G.Rx * k, G.Ry * k, 0, 0, Math.PI * 2); ctx.stroke();
    });
    ctx.strokeStyle = 'rgba(0,207,255,.10)';
    for (var q = 0; q < 6; q++) { var aa = q * Math.PI / 6; ctx.beginPath(); ctx.moveTo(G.cx - Math.cos(aa) * G.Rx, G.cy - Math.sin(aa) * G.Ry); ctx.lineTo(G.cx + Math.cos(aa) * G.Rx, G.cy + Math.sin(aa) * G.Ry); ctx.stroke(); }
    // sweep: a fading wedge on the disc
    var N = 36, span = Math.PI * 0.42;
    for (var k = 0; k < N; k++) {
      var a0 = sweep - span * (k + 1) / N, a1 = sweep - span * k / N;
      ctx.fillStyle = 'rgba(0,255,136,' + (0.22 * Math.pow(1 - k / N, 2)) + ')';
      ctx.beginPath(); ctx.moveTo(G.cx, G.cy);
      for (var s = 0; s <= 4; s++) { var a = a0 + (a1 - a0) * s / 4; ctx.lineTo(G.cx + Math.cos(a) * G.Rx, G.cy + Math.sin(a) * G.Ry); }
      ctx.closePath(); ctx.fill();
    }
    ctx.strokeStyle = 'rgba(160,255,210,.85)'; ctx.lineWidth = 1.5; ctx.shadowColor = 'rgba(0,255,136,.9)'; ctx.shadowBlur = 10;
    ctx.beginPath(); ctx.moveTo(G.cx, G.cy); ctx.lineTo(G.cx + Math.cos(sweep) * G.Rx, G.cy + Math.sin(sweep) * G.Ry); ctx.stroke();
    ctx.shadowBlur = 0;
    // beams, back to front
    var pts = blips.map(function (b) {
      var x = G.cx + Math.cos(b.a) * G.Rx * b.rr, y = G.cy + Math.sin(b.a) * G.Ry * b.rr;
      var dA = ((sweep - b.a) % (Math.PI * 2) + Math.PI * 2) % (Math.PI * 2);
      b.lit = dA < 0.12 ? 1 : Math.max(0, b.lit - 0.012);
      b.x = x; b.y = y; b.top = y - Math.max(10, b.h * G.maxH); return b;
    }).sort(function (a, b) { return a.y - b.y; });
    placeLabels(pts);
    pts.forEach(function (b) {
      var on = hover === b, glow = 0.55 + 0.45 * b.lit + (on ? .4 : 0);
      ctx.fillStyle = 'rgba(' + b.col + ',' + (0.25 + 0.3 * b.lit) + ')';
      ctx.beginPath(); ctx.ellipse(b.x, b.y, b.s * 1.5, b.s * 0.6, 0, 0, Math.PI * 2); ctx.fill();
      var lg = ctx.createLinearGradient(0, b.y, 0, b.top);
      lg.addColorStop(0, 'rgba(' + b.col + ',0.05)'); lg.addColorStop(1, 'rgba(' + b.col + ',' + Math.min(1, .75 * glow) + ')');
      ctx.strokeStyle = lg; ctx.lineWidth = on ? 3 : 2; ctx.beginPath(); ctx.moveTo(b.x, b.y); ctx.lineTo(b.x, b.top); ctx.stroke();
      ctx.shadowColor = 'rgba(' + b.col + ',1)'; ctx.shadowBlur = 12 + 14 * b.lit + (on ? 10 : 0);
      ctx.fillStyle = 'rgba(' + b.col + ',' + Math.min(1, glow) + ')';
      ctx.beginPath(); ctx.arc(b.x, b.top, b.s + (on ? 2 : 0), 0, Math.PI * 2); ctx.fill();
      ctx.shadowBlur = 0;
      if (b.show || on) {
        var lx = Math.max(44, Math.min(W - 44, b.x));
        ctx.font = '800 12px "JetBrains Mono", monospace'; ctx.textAlign = 'center';
        ctx.fillStyle = '#fff'; ctx.fillText(b.r.symbol || b.r.name || '', lx, b.top - b.s - 8);
        ctx.font = '700 10.5px "JetBrains Mono", monospace'; ctx.fillStyle = 'rgba(' + b.col + ',1)';
        ctx.fillText(num(b.r.conviction, 1), lx, b.top - b.s - 22);
      }
    });
    if (!document.hidden) requestAnimationFrame(draw);
  }
  document.addEventListener('visibilitychange', function () { if (!document.hidden) requestAnimationFrame(draw); });
  window.addEventListener('resize', size);
  cv.addEventListener('mousemove', function (e) {
    var r = cv.getBoundingClientRect(), x = e.clientX - r.left, y = e.clientY - r.top, best = null, bd = 18;
    blips.forEach(function (b) { var d = Math.hypot(b.x - x, b.top - y); if (d < bd) { bd = d; best = b; } });
    hover = best;
    if (!best) { tip.hidden = true; return; }
    var p = prob(best.r), sol = state.chain === 'solana';
    tip.hidden = false; tip.style.left = best.x + 'px'; tip.style.top = (best.top - best.s) + 'px';
    tip.innerHTML = '<b>' + esc(best.r.symbol || best.r.name) + '</b>'
      + '<div class="row"><span>Conviction</span><span>' + num(best.r.conviction, 1) + '</span></div>'
      + '<div class="row"><span>3× in 72h</span><span>' + p.big + '</span></div>'
      + (sol ? '<div class="row"><span>Buys / sells</span><span>' + num(best.r.buys, 0) + ' / ' + num(best.r.sells, 0) + '</span></div>'
        : '<div class="row"><span>Smart buyers</span><span>' + num(best.r.qualified_buyers, 0) + '</span></div>')
      + '<div class="row"><span>In</span><span>' + usdK(best.r.usd_invested) + '</span></div>'
      + '<div class="row"><span>' + (sol ? 'Pool age' : 'First buy') + '</span><span>' + ago(sol ? best.r.token_age_seconds : best.r.first_buy_seconds_ago) + '</span></div>';
  });
  cv.addEventListener('mouseleave', function () { hover = null; tip.hidden = true; });
  cv.addEventListener('click', function () {
    if (!hover) return;
    var key = hover.r.token_address;
    if (state.filter !== 'all') setFilter('all');
    var rows = state.sig[state.chain].all.rows, i = rows.findIndex(function (r) { return r.token_address === key; });
    $('signals').scrollIntoView({ behavior: 'smooth' });
    if (state.chain === 'robinhood' && i >= 0) { state.open = null; toggle(i); }
  });

  // ---------- load ----------
  var FILTERS = ['all', 'hot', 'fresh', 'exits'];
  function loadSignals() {
    var chain = state.chain;
    return Promise.all(FILTERS.map(function (f) { return getJSON('signals?chain=' + chain + '&filter=' + f); })).then(function (res) {
      var by = {}; FILTERS.forEach(function (f, i) { by[f] = res[i]; });
      state.sig[chain] = by;
      if (chain !== state.chain) return;
      var d = by.all || by[state.filter];
      if (d) { renderMeta(d); renderCal(d.calibration); renderEntities(d); }
      renderRows(); setBlips();
    });
  }
  function loadAll() {
    var chain = state.chain;
    loadSignals();
    getJSON('traders?chain=' + chain).then(function (d) { if (chain === state.chain) renderTraders(d); });
    renderBacktest(null);
    getJSON('backtest?chain=' + chain).then(function (d) { if (chain === state.chain) renderBacktest(d); });
  }
  function setFilter(f) {
    state.filter = f; state.open = null;
    document.querySelectorAll('#filterChips button').forEach(function (b) { b.classList.toggle('on', b.dataset.filter === f); });
    renderRows();
  }
  $('filterChips').addEventListener('click', function (e) { var b = e.target.closest('button[data-filter]'); if (b) setFilter(b.dataset.filter); });
  $('chainSeg').addEventListener('click', function (e) {
    var b = e.target.closest('button[data-chain]'); if (!b || b.dataset.chain === state.chain) return;
    state.chain = b.dataset.chain; state.open = null;
    document.querySelectorAll('#chainSeg button').forEach(function (x) { x.classList.toggle('on', x === b); });
    $('rows').innerHTML = '<div class="fr-empty">Loading live signals…</div>';
    $('traders').innerHTML = '<div class="fr-empty">Loading wallets…</div>';
    blips = [];
    loadAll();
  });

  // folds, copy, tabs
  document.addEventListener('click', function (e) {
    var f = e.target.closest('[data-fold]');
    if (f) {
      var el = $('fold-' + f.dataset.fold), open = el.hidden;
      el.hidden = !open; f.setAttribute('aria-expanded', String(open));
      return;
    }
    var c = e.target.closest('[data-copy]');
    if (c) {
      if (navigator.clipboard) navigator.clipboard.writeText(c.dataset.copy).catch(function () {});
      c.classList.add('done'); setTimeout(function () { c.classList.remove('done'); }, 1200);
    }
  });
  var tabs = document.querySelectorAll('.fr-tabs a');
  window.addEventListener('scroll', function () {
    var cur = null;
    tabs.forEach(function (a) { var s = document.querySelector(a.getAttribute('href')); if (s && !s.hidden && s.getBoundingClientRect().top < 160) cur = a; });
    tabs.forEach(function (a) { a.classList.toggle('on', a === (cur || tabs[0])); });
  }, { passive: true });

  size();
  requestAnimationFrame(draw);
  loadAll();
  setInterval(function () { if (!document.hidden) loadSignals(); }, 30000);
})();
