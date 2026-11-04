/* Quant Lab (ET-33496): the experiments page as a reactor. The lab's last finished search is replayed as five stages
 * (BUILD, BLAST, BLIND, THE BAR, FOUND); while a search runs the stages follow the company WebSocket's search fields
 * (done_jobs, total_jobs, percent, eta_seconds). Reads the owner-only API (/api/v1/company/{id}/quant-lab...), never
 * polls it. Paper only: nothing real is bought or sold. The "Coming soon" view is a SIMULATION of ET-33142 (the search
 * unit is a whole bot setup; the winner starts as a paper bot with exactly that setup) and sends nothing anywhere.
 * Layout and drawing come from the requester's mock; the data comes from our API. */
(function () {
  'use strict';
  var API = '/api/v1/company';
  function $(id) { return document.getElementById(id); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function pct(v) { return v == null ? '—' : (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(2) + '%'; }
  function num(v) { return Number(v).toLocaleString('en-US'); }
  function api(method, path, body) {
    var o = { method: method, credentials: 'same-origin', headers: { Accept: 'application/json' } };
    if (body !== undefined) { o.headers['Content-Type'] = 'application/json'; o.body = JSON.stringify(body); }
    return fetch(API + path, o).then(function (r) {
      return r.text().then(function (t) {
        var j = null; try { j = t ? JSON.parse(t) : null; } catch (e) { j = null; }
        if (!r.ok) {
          var d = j && j.detail; if (Array.isArray(d)) d = d.map(function (x) { return x.msg; }).join('; ');
          // ET-33878: a 401 is the API's own line ("Provide Bearer token or X-API-Key header"), never a person's -- the
          // caller opens the sign-in card instead (noCompany)
          var er = new Error(r.status === 401 ? 'Sign in to use the Quant Lab.' : r.status >= 500 || typeof d !== 'string' || !d ? 'Something went wrong. Try again in a moment.' : d); er.status = r.status; throw er;
        }
        return j;
      });
    });
  }
  var toastT;
  function toast(t) { var el = $('toast'); if (!el) return; el.textContent = t; el.hidden = false; clearTimeout(toastT); toastT = setTimeout(function () { el.hidden = true; }, 3200); }
  function when(s) { if (!s) return null; var t = Date.parse(/(Z|[+-]\d\d:?\d\d)$/.test(s) ? s : s + 'Z'); return isNaN(t) ? null : t; }

  // ---- the catalogue: icons and names as /adm and /skills-n-tools show them
  var MODELS = {
    helix: ['🧬', 'HELIX'], prion: ['🧩', 'PRION'], enzyme: ['⚗️', 'ENZYME'], synapse: ['🧠', 'SYNAPSE'], cortex: ['♞', 'CORTEX'],
    telomere: ['⏳', 'TELOMERE'], immune: ['🛡️', 'IMMUNE'], circadian: ['⏰', 'CIRCADIAN'], mitosis: ['🦠', 'MITOSIS'], crispr: ['🎯', 'CRISPR'],
    stockbull_blue: ['📊', 'StockBot Blue'], stockbear_red: ['📊', 'StockBot Red'], cryptobull_blue: ['📊', 'CryptoBull Blue'],
    cryptobull_red: ['📊', 'CryptoBull Red'], hybrid2_blue: ['📊', 'Hybrid 2 Blue'], hybrid2_red: ['📊', 'Hybrid 2 Red']
  };
  var COMBOS = {
    cell_division: ['🦠', 'Cell Division', 'MITOSIS + TELOMERE + HELIX'], central_dogma: ['🧬', 'Central Dogma', 'HELIX + ENZYME + CRISPR'],
    crispr_cas9_complex: ['🎯', 'CRISPR-Cas9 Complex', 'CRISPR + PRION + ENZYME'], immune_response: ['🛡️', 'Immune Response', 'IMMUNE + CORTEX + CIRCADIAN'],
    neural_network: ['🧠', 'Neural Network', 'SYNAPSE + CORTEX + CRISPR']
  };
  var SKILLS = {
    macd: ['📈', 'MACD Crossover'], rsi: ['⚡', 'RSI Momentum'], boll: ['🔄', 'Bollinger Squeeze'], volt: ['⚡', 'Volume Threshold'],
    ema: ['📈', 'EMA Trend'], volf: ['🔍', 'Volatility Filter'], atr: ['〰️', 'ATR Volatility'], ichi: ['☁️', 'Ichimoku Cloud'],
    // the skills the search replays as candle rules (ET-33966 item 5), by their /adm ids
    macd_crossover: ['📈', 'MACD Crossover'], rsi_momentum: ['⚡', 'RSI Momentum'], bollinger_squeeze: ['🔄', 'Bollinger Squeeze'],
    stochastic_reversal: ['🔁', 'Stochastic Reversal'], ema_trend: ['📈', 'EMA Trend']
  };
  var RULES = Object.keys(MODELS);   // the 16 rules the search replays today: 10 biomimetic + 6 Backtested Strategy
  var DEFAULT_MARKETS = ['BTC', 'ETH', 'SOL', 'BNB', 'XRP', 'ADA', 'DOGE', 'AVAX', 'LINK', 'LTC', 'DOT', 'ATOM'];
  // ET-33966 (5): a candidate id is a model, "skill:<id>" (a skill replayed as a candle rule) or "combo:<id>" (a Named Combination from /adm)
  function modelInfo(k) {
    k = String(k || '?');
    if (k.indexOf('skill:') === 0) return skillOf(k.slice(6));
    if (k.indexOf('combo:') === 0) { var c = COMBOS[k.slice(6)] || ['🧬', k.slice(6), '']; return [c[0], c[1]]; }
    return MODELS[k] || ['🤖', k.toUpperCase()];
  }
  function candidateSetup(id) {
    id = String(id || '');
    return id.indexOf('combo:') === 0 ? { kind: 'combo', base: id.slice(6), skills: [] } : id.indexOf('skill:') === 0 ? { kind: 'skill', base: id, skills: [] } : { kind: 'rule', base: id, skills: [] };
  }

  // coin logos: CoinGecko's, the source our own /perpetual pages load BTC and ETH from
  var COIN = { BTC: '1/large/bitcoin.png', ETH: '279/large/ethereum.png', SOL: '4128/large/solana.png', BNB: '825/large/bnb-icon2_2x.png',
    XRP: '44/large/xrp-symbol-white-128.png', ADA: '975/large/cardano.png', DOGE: '5/large/dogecoin.png', AVAX: '12559/large/Avalanche_Circle_RedWhite_Trans.png',
    LINK: '877/large/chainlink-new-logo.png', LTC: '2/large/litecoin.png', DOT: '12171/large/polkadot.png', ATOM: '1481/large/cosmos_hub.png' };
  function coinUrl(s) { return COIN[s] ? 'https://assets.coingecko.com/coins/images/' + COIN[s] : ''; }
  function coinImg(s) { return coinUrl(s) ? '<img src="' + coinUrl(s) + '" alt="">' : ''; }
  function coinTag(s) { return '<span class="q2-coin">' + coinImg(s) + '</span><b class="q2-ct">' + esc(s) + '</b>'; }

  // the agent: our own picture, cropped to the scene and the head
  var AGENT = '/static/img/quant-lab/agent.webp', HEAD = '/static/img/quant-lab/agent-head.webp';
  function headImg(cls) { return '<img class="' + cls + '" src="' + HEAD + '" alt="">'; }

  function setupKey(s) { return [s.base].concat(s.skills).join('+'); }
  function baseOf(s) { return s.kind === 'combo' ? (COMBOS[s.base] || ['🧬', s.base, '']) : modelInfo(s.base); }
  function skillOf(k) { return SKILLS[k] || ['🧩', String(k)]; }
  function setupChips(s, small) {
    var b = baseOf(s), out = '<span class="q2-chip ' + (s.kind === 'combo' ? 'q2-cc' : s.kind === 'skill' ? 'q2-cs' : 'q2-cm') + '" title="' + esc(s.kind === 'combo' ? 'Named Combination: ' + b[2] : s.kind === 'skill' ? 'Skill, replayed as a candle rule' : s.kind === 'rule' && !/^[a-z]+$/.test(s.base) ? 'Backtested Strategy rule' : 'Model') + '">' + b[0] + ' ' + esc(b[1]) + '</span>';
    s.skills.forEach(function (k) { out += '<span class="q2-chip q2-cs" title="Skill">' + skillOf(k)[0] + (small ? '' : ' ' + esc(skillOf(k)[1])) + '</span>'; });
    return '<div class="q2-chips">' + out + '</div>';
  }
  function setupText(s) {
    var b = baseOf(s);
    return b[0] + ' ' + b[1] + s.skills.map(function (k) { return ' + ' + skillOf(k)[0]; }).join('');
  }

  // ---- one seeded generator for every random-looking thing
  function rng(seed) { return function () { seed |= 0; seed = seed + 0x6D2B79F5 | 0; var t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  // inverse normal (Acklam): the bar is a one-sided 5% test split over every combination tried
  function invNorm(p) {
    var a = [-39.6968302866538, 220.946098424521, -275.928510446969, 138.357751867269, -30.6647980661472, 2.50662827745924],
      b = [-54.4760987982241, 161.585836858041, -155.698979859887, 66.8013118877197, -13.2806815528857],
      c = [-0.00778489400243029, -0.322396458041136, -2.40075827716184, -2.54973253934373, 4.37466414146497, 2.93816398269878],
      d = [0.00778469570904146, 0.32246712907004, 2.445134137143, 3.75440866190742], q, r;
    if (p > 1 - 0.02425) { q = Math.sqrt(-2 * Math.log(1 - p)); return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1); }
    q = p - 0.5; r = q * q;
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
  }

  // ---------------------------------------------------------------- the data: what the API says
  var S = { cid: null, st: null, ov: null, res: null, ws: null, loaded: false, signedOut: false };
  var LIVE = null;        // the running search as the WebSocket (or the status read) reports it
  var FAILS = [], LAST_GOOD = null, DOWN = '', NOTHING_NEW = null, RETESTED = null, FAILED_ALL = { count: 0, searches: [] };
  var SELECTED = null;    // the run picked in the run history (null = the newest blind test)
  function day(iso) { var t = when(iso); return t == null ? '' : new Date(t).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }).toUpperCase(); }
  function stamp(iso) {   // the run date of a row: 30 OCT 16:34 (UTC)
    var t = when(iso); if (t == null) return '—';
    var d = new Date(t); return day(iso) + ' ' + ('0' + d.getUTCHours()).slice(-2) + ':' + ('0' + d.getUTCMinutes()).slice(-2);
  }
  // a failure is named by a plain label, never by the raw error text
  function errLabel(e) { return /closed the connection|OperationalError|connection/i.test(e || '') ? 'database connection lost' : 'the search stopped before it finished'; }
  function downWhy() {
    return 'The last ' + FAILS.length + ' searches failed (' + FAILS.slice().reverse().map(function (f) { return '#' + f.id + ' ' + day(f.requested_at); }).join(', ') + '): ' +
      errLabel(FAILS[0].error) + (LAST_GOOD ? '. Nothing has been tested since ' + day(LAST_GOOD.finished_at) + ', so this replays that search.' : '.');
  }
  function dur(s) { return s == null ? 'ESTIMATING' : s < 90 ? s + ' S' : Math.round(s / 60) + ' MIN'; }
  function active(s) { return !!s && (s.status === 'running' || s.status === 'queued'); }

  function realModel() {
    var st = S.st || {}, ov = S.ov || {}, res = S.res || {}, markets = (st.markets && st.markets.length) ? st.markets : DEFAULT_MARKETS;
    var searches = (res.searches || []).slice();
    if (!searches.length) { [st.search, st.last_finished].forEach(function (x) { if (x && !searches.some(function (y) { return y.id === x.id; })) searches.push(x); }); }
    searches.sort(function (a, b) { return b.id - a.id; });
    FAILED_ALL = (st.failed && typeof st.failed.count === 'number') ? st.failed : (res.failed && typeof res.failed.count === 'number') ? res.failed : { count: searches.filter(function (s) { return s.status === 'failed'; }).length, searches: searches.filter(function (s) { return s.status === 'failed'; }).map(function (s) { return { id: s.id, requested_at: s.requested_at, reason: s.error_label || errLabel(s.error) }; }) };
    FAILS = []; for (var i = 0; i < searches.length && searches[i].status === 'failed'; i++) FAILS.push(searches[i]);
    // the search whose blind test the reactor replays: the newest one that has blind-tested rows. A search that tried
    // nothing new (every setup already in memory) never replaces it (ET-33496).
    var NEWEST_DONE = searches.filter(function (s) { return s.status === 'done'; })[0] || st.last_finished || null;
    LAST_GOOD = st.latest_blind || (res && res.latest_blind) || NEWEST_DONE;
    // the run history (ET-33496 item 8): a clicked run replaces the newest blind test in the reactor and the rows
    var PICK = SELECTED != null ? searches.filter(function (s) { return s.id === SELECTED; })[0] : null;
    if (SELECTED != null && !PICK) SELECTED = null;
    if (PICK) LAST_GOOD = PICK;
    var pickSum = (PICK && PICK.summary) || null;
    if (pickSum && pickSum.markets_searched && pickSum.markets_searched.length) markets = pickSum.markets_searched;
    NOTHING_NEW = NEWEST_DONE && NEWEST_DONE.nothing_new ? NEWEST_DONE : null;
    RETESTED = NEWEST_DONE && NEWEST_DONE.retested > 0 ? NEWEST_DONE : null;
    DOWN = FAILS.length ? downWhy() : '';
    var setups = RULES.map(function (k) { return { kind: 'rule', base: k, skills: [] }; });
    var tried = (pickSum && pickSum.n_tried_total) || st.combinations_tried || 0, k = Math.max(1, Math.min(27, Math.round(tried / (setups.length * markets.length))));
    var held = (res.held_back_results || []);
    var lastRows = held.filter(function (x) { return LAST_GOOD && x.search_id === LAST_GOOD.id; });
    lastRows.sort(function (a, b) { return ((b.search_period || {}).return_pct || 0) - ((a.search_period || {}).return_pct || 0); });
    var cands = lastRows.map(function (x) {
      var s = candidateSetup(x.model), h = x.held_back || {}, b = x.bar || {};
      return { setup: s, setup_key: setupKey(s), model: x.model, market: x.market, settings: x.settings_label || '', entry: x.entry_threshold || 'as_is',
        search: (x.search_period || {}).return_pct, held: h.return_pct, trades: h.trades, bar: b.bar_pct == null ? 1 : b.bar_pct, z: b.z,
        won: x.verdict === 'kept', verdict: x.verdict, experiment_id: x.experiment_id, created_at: x.created_at, search_id: x.search_id,
        // ET-33966: the result on every held-back window beside the 12-coin hold, the pooled verdict, the side, the short-rule note
        pooled: !!x.pooled, side: x.side || 'long', bot_note: x.bot_note || '', windows: x.windows || [], windows_won: x.windows_won,
        windows_total: x.windows_total, windows_needed: x.windows_needed, min_trades: x.min_trades, label: h.label, why: x.why_shortlisted || [] };
    });
    var exps = ov.experiments || [];
    var botList = cands.filter(function (c) { return c.won; }).map(function (c) {
      var e = exps.filter(function (x) { return x.id === c.experiment_id; })[0];
      var pts = e ? curveOf(e) : [];
      if (pts.length < 2) pts = [0, 0];
      return { cand: c, pts: pts, ret: e && e.return_pct != null ? e.return_pct : 0, trades: e ? e.trades : 0, dd: e && e.max_drawdown_pct != null ? e.max_drawdown_pct : 0 };
    });
    var z = cands.length && cands[0].z ? cands[0].z : tried > 1 ? invNorm(1 - 0.05 / tried) : 0;
    return { mode: 'real', setups: setups, markets: markets, settings: k, tried: tried,
      searches: st.searches_total || searches.length, searchesPlus: !st.searches_total && searches.length >= 10, failed: FAILED_ALL.count,
      checked: held.length, won: held.filter(function (x) { return x.verdict === 'kept'; }).length, lastWon: botList.length,
      bots: exps.filter(function (x) { return x.origin === 'search'; }).length, botList: botList, z: z, candidates: cands,
      label: LAST_GOOD ? 'search #' + LAST_GOOD.id + ' · ' + day(LAST_GOOD.finished_at || LAST_GOOD.requested_at) + ' · ' + num(tried) + ' tried' : 'no search yet',
      picked: PICK || null, runs: (res.runs || []),
      failedWhy: FAILED_ALL.searches.slice().reverse().map(function (f) { return '#' + f.id + ' ' + day(f.requested_at) + ' ' + f.reason; }).join(' · ') };
  }
  function curveOf(e) {
    return (e.equity_curve || []).map(function (c) { return Array.isArray(c) ? +c[1] : +c; }).filter(function (v) { return isFinite(v); });
  }

  // ---- SIM: ET-33142, one small model. Setups = today's 16 rules (the simplest case) + models / combinations with skills.
  function simModel() {
    var composed = [
      { kind: 'combo', base: 'central_dogma', skills: ['macd', 'volf'] }, { kind: 'combo', base: 'central_dogma', skills: ['ema'] },
      { kind: 'combo', base: 'immune_response', skills: ['rsi'] }, { kind: 'combo', base: 'immune_response', skills: ['atr', 'volt'] },
      { kind: 'model', base: 'helix', skills: ['ema', 'volf'] }, { kind: 'model', base: 'crispr', skills: ['boll', 'volt'] },
      { kind: 'model', base: 'enzyme', skills: ['rsi', 'boll'] }, { kind: 'model', base: 'cortex', skills: ['ichi'] }];
    var setups = RULES.map(function (k) { return { kind: 'rule', base: k, skills: [] }; }).concat(composed);
    var settings = 27, tried = setups.length * DEFAULT_MARKETS.length * settings, z = invNorm(1 - 0.05 / tried);
    // the five best on the search period; the bar is z x the spread on the blind period (never below 1%)
    var picks = [
      [composed[0], 'ETH', 'SL 5 / TP 30', 'stricter', 31.4, 12.4, 2.1, 71],
      [composed[4], 'SOL', 'SL 3 / TP 15', 'as_is', 26.2, 4.8, 2.0, 64],
      [setups[RULES.indexOf('stockbull_blue')], 'DOT', 'SL 3 / TP 30', 'as_is', 24.9, -2.6, 2.3, 58],
      [composed[2], 'BTC', 'SL 8 / TP 15', 'looser', 21.7, -1.1, 1.6, 49],
      [composed[5], 'AVAX', 'SL 5 / TP 30', 'as_is', 19.8, -7.4, 2.2, 66]];
    var cands = picks.map(function (p) {
      var bar = Math.max(1, Math.round(z * p[6] * 1000) / 1000);
      return { setup: p[0], setup_key: setupKey(p[0]), model: p[0].base, market: p[1], settings: p[2], entry: p[3], search: p[4], held: p[5], trades: p[7],
        bar: bar, won: p[5] > bar, verdict: p[5] > bar ? 'kept' : 'thrown_out' };
    });
    var winners = cands.filter(function (c) { return c.won; });
    var bots = winners.map(function (c, i) {   // the paper bot a winner starts: its equity walk, seeded by its setup
      var r = rng(7 + i), v = 0, pts = [0];
      for (var k = 1; k < 60; k++) { v += (r() - 0.42) * 0.55; pts.push(Math.round(v * 100) / 100); }
      return { cand: c, pts: pts, ret: pts[pts.length - 1], trades: 9, dd: 1.8 };
    });
    return { mode: 'sim', setups: setups, markets: DEFAULT_MARKETS, settings: settings, tried: tried, searches: 1, failed: 0, checked: cands.length,
      won: winners.length, lastWon: winners.length, bots: bots.length, botList: bots, z: z, candidates: cands, label: 'simulated · ' + num(tried) + ' tried' };
  }

  var M = null, SIM = simModel(), REAL = null, MODE = 'real';
  window.QL = { ready: false, mode: null, sim: null };

  // ---------------------------------------------------------------- DOM
  function loading() { return M.mode === 'real' && !S.loaded; }
  function tile(k, ic, n, l, cls, tip, text) {
    // ET-33496 item 5: until the lab's reads answer, a tile says it is loading, never a 0 that is not true
    if (loading()) return '<div class="q2-tile q2-zero q2-ld" title="Loading the lab…"><span class="q2-ic">' + (ic === 'head' ? headImg('q2-hd') : ic) + '</span><span class="q2-n" data-k="' + k + '">…</span><span class="q2-l">' + l + '</span></div>';
    return '<div class="q2-tile ' + (cls || '') + (n === 0 ? ' q2-zero' : '') + '" title="' + esc(tip) + '"><span class="q2-ic">' + (ic === 'head' ? headImg('q2-hd') : ic) + '</span><span class="q2-n" data-k="' + k + '">' + (text || num(n)) + '</span><span class="q2-l">' + l + '</span></div>';
  }
  function renderScore() {
    var real = M.mode === 'real';
    var st = S.st || {}, rt = st.tried_retests || 0;
    $('score').innerHTML =
      tile('searches', '🔎', M.searches, 'Searches', '', real ? 'Searches run: daily, or when you ask' + (M.searchesPlus ? ' (the latest 10 are counted)' : '') : 'One search', M.searchesPlus ? num(M.searches) + '+' : '') +
      tile('failed', '⚠️', M.failed, 'Failed', M.failed ? 'q2-down' : '', M.failed ? M.failedWhy : 'None failed') +
      tile('tried', '🧮', M.tried, 'Tried', 'q2-cy', M.setups.length + ' setups × ' + M.markets.length + ' markets × their settings, each replayed on past prices' +
        (real ? '. Counts finished searches only: a failed search leaves no tries. A re-test of a known setup on newer prices counts as a try' + (rt ? ' (' + num(rt) + ' of them)' : '') + ', because it could be shortlisted too, so it raises the bar' : '')) +
      tile('checked', '🙈', M.checked, 'Blind-tested', '', 'The best few of each search, re-run on the later period the search never saw') +
      tile('won', '🏁', M.won, 'Beat the bar', M.won ? 'q2-up' : 'q2-down', 'Won on the blind period by more than the bar, which rises with every try') +
      tile('bots', 'head', M.bots, 'Agents found', M.bots ? 'q2-up' : '', real ? 'Paper bots started from winners' : 'Paper bots started with exactly the winning setup');
  }
  function gauge(c, lo, hi) {
    function x(v) { return ((v - lo) / (hi - lo) * 100).toFixed(2) + '%'; }
    var a = Math.min(0, c.held), b = Math.max(0, c.held);
    return '<div class="q2-gauge" title="Blind result ' + pct(c.held) + ' against a bar of ' + c.bar.toFixed(2) + '%"><div class="q2-gtr"></div><div class="q2-gz" style="left:' + x(0) + '"></div>' +
      '<div class="q2-gf ' + (c.held < 0 ? 'q2-down' : 'q2-up') + '" style="left:' + x(a) + ';width:calc(' + x(b) + ' - ' + x(a) + ')"></div>' +
      '<div class="q2-gbar" style="left:' + x(c.bar) + '"></div><span class="q2-gbl" style="left:' + x(c.bar) + '">bar ' + c.bar.toFixed(2) + '%</span>' +
      '<div class="q2-gdot" style="left:' + x(c.held) + '"></div></div>';
  }
  function renderTop() {
    $('toplabel').textContent = M.label + (M.candidates.length ? ' · z ' + M.z.toFixed(2) : '');
    var note = $('topnote');
    if (note) {
      var txt = M.mode !== 'real' ? '' : NOTHING_NEW ? 'Search #' + NOTHING_NEW.id + ' (' + day(NOTHING_NEW.finished_at) + ') found nothing new: every setup was already tested on the latest prices' :
        RETESTED ? 'Search #' + RETESTED.id + ' (' + day(RETESTED.finished_at) + ') re-tested ' + num(RETESTED.retested) + ' known setups on new data' : '';
      note.textContent = txt; note.hidden = !txt;
    }
    renderRuns();
    if (loading()) { $('top').innerHTML = '<div class="q2-quiet q2-ld">Loading the lab…</div>'; return; }
    if (!M.candidates.length) {
      var pk = M.picked, why = !pk ? '' : pk.status === 'failed' ? 'Search #' + pk.id + ' failed (' + (pk.error_label || 'stopped before it finished') + '): nothing was blind-tested.'
        : pk.nothing_new ? 'Search #' + pk.id + ' found nothing new: nothing was blind-tested.' : active(pk) ? 'Search #' + pk.id + ' is still running.' : 'Search #' + pk.id + ' shortlisted nothing to blind-test.';
      $('top').innerHTML = '<div class="q2-quiet">' + (S.st && S.st.access && !S.st.access.allowed ? 'The Quant Lab search is on the Pro plan.' : why || 'No blind test yet.') + '</div>'; return;
    }
    var lo = Math.min(-15, Math.min.apply(null, M.candidates.map(function (c) { return c.held; })) - 2), hi = Math.max(15, Math.max.apply(null, M.candidates.map(function (c) { return c.bar; })) + 3);
    $('top').innerHTML = M.candidates.map(function (c, i) {
      return '<div class="top-row ' + (c.won ? 'q2-won' : '') + '" data-model="' + esc(c.model) + '" data-market="' + esc(c.market) + '" data-search="' + c.search + '" data-held="' + c.held + '" data-bar="' + c.bar + '" data-verdict="' + esc(c.verdict) + '">' +
        '<span class="q2-rk">' + (i + 1) + '</span>' + setupChips(c.setup) +
        '<span class="q2-dt" title="Run date (UTC) of search #' + esc(c.search_id == null ? '?' : c.search_id) + '">' + (c.created_at ? esc(stamp(c.created_at)) : '—') + '</span>' +
        '<span class="q2-cw">' + coinTag(c.market) + '</span>' +
        '<div class="q2-set"><b>' + esc(String(c.settings).replace(' / ', ' · ')) + '</b><br>entry ' + esc(String(c.entry).replace('_', ' ')) + '</div>' +
        '<div class="q2-move" title="Search period → blind period, ' + (c.trades == null ? '—' : c.trades) + ' trades"><span class="q2-ma">' + pct(c.search) + '</span><span class="q2-mar">→</span><span class="q2-mb ' + (c.held < 0 ? 'q2-down' : 'q2-up') + '">' + pct(c.held) + '</span></div>' +
        gauge(c, lo, hi) + '<span class="q2-v ' + (c.won ? 'q2-won' : 'q2-lost') + '" title="' + (c.won ? 'Cleared the bar' : 'Thrown out') + '">' + (c.won ? '✓' : '✗') + '</span>' + winStrip(c) + '</div>';
    }).join('');
  }
  // ET-33966 (6): every held-back window's result beside the equal-weight 12-coin hold (information, not the pass
  // rule), and the pass rule's three numbers: "N of M windows made money", the pooled result against the bar, the trades
  function winStrip(c) {
    if (!c.pooled || !c.windows.length) return '';
    var chips = c.windows.map(function (w) {
      var cls = w.missing ? 'q2-miss' : w.made_money ? 'q2-up' : 'q2-down';
      var tip = (w.kind ? w.kind + ' market · ' : '') + (w.trades == null ? '' : w.trades + ' trades · ') + c.market + ' moved ' + pct(w.market_move_pct) +
        ' · equal-weight 12-coin hold ' + pct(w.basket_move_pct) + ' (information, not the pass rule)' +
        (w.reused_from_search ? ' · result stored by search #' + w.reused_from_search + ' (not replayed: a window a setup already failed is never re-tested within 36 days)' : '') + (w.note ? ' · ' + w.note : '');
      return '<span class="q2-rwin ' + cls + '" title="' + esc(tip) + '"><b>' + esc(day(w.start) + '–' + day(w.end)) + '</b> ' + (w.missing ? 'no bars' : pct(w.return_pct)) +
        ' <i>hold ' + pct(w.basket_move_pct) + '</i>' + (w.reused_from_search ? ' <u title="stored by search #' + w.reused_from_search + '">#' + w.reused_from_search + '</u>' : '') + '</span>';
    }).join('');
    var line = c.windows_won + ' of ' + c.windows_total + ' windows made money (needs ' + c.windows_needed + ') · pooled ' + pct(c.held) + ' vs bar ' + pct(c.bar) +
      ' · ' + (c.trades == null ? '—' : c.trades) + ' trades (needs ' + (c.min_trades || 20) + ')' + (c.side === 'short' ? ' · short rule' : '');
    return '<div class="q2-wins"><span class="q2-wsum ' + (c.won ? 'q2-up' : 'q2-down') + '" title="' + esc('Net of fee and slippage. Shortlisted because: ' + (c.why || []).join('; ')) + '">' + esc(line) + '</span>' + chips +
      (c.bot_note ? '<span class="q2-wnote">' + esc(c.bot_note) + '</span>' : '') + '</div>';
  }
  // the run history (ET-33496 items 8, 9): every search with its date, status, what it tried and the models it
  // shortlisted; a click loads that run's own stages and rows, the selected run is kept until "newest" is clicked
  function renderRuns() {
    var el = $('runs'), sub = $('runsub'); if (!el) return;
    if (M.mode !== 'real') { el.innerHTML = '<div class="q2-quiet">The run history shows your real searches. Switch to Real.</div>'; if (sub) sub.textContent = ''; return; }
    if (loading()) { el.innerHTML = '<div class="q2-quiet q2-ld">Loading the runs…</div>'; return; }
    var runs = M.runs || [];
    if (sub) { sub.textContent = runs.length ? runs.length + ' runs · click one to replay it' : ''; sub.title = (S.res && ((S.res.pass_rule || '') + ' ' + (S.res.shortlist_rule || '')).trim()) || ''; }
    if (!runs.length) { el.innerHTML = '<div class="q2-quiet">' + (S.st && S.st.access && !S.st.access.allowed ? 'The Quant Lab search is on the Pro plan.' : 'No search yet.') + '</div>'; return; }
    var cur = M.picked ? M.picked.id : (LAST_GOOD ? LAST_GOOD.id : null);
    el.innerHTML = runs.map(function (r) {
      var st = r.status === 'failed' ? '<b class="q2-down" title="' + esc(r.error_label || '') + '">FAILED</b>' : active(r) ? '<b class="q2-cy">RUNNING</b>'
        : r.nothing_new ? '<b title="Every setup was already tested on the latest prices">NOTHING NEW</b>' : '<b class="q2-up">DONE</b>';
      var tried = r.status === 'failed' ? '—' : num(r.tried || 0) + (r.retested ? ' <i title="re-tests of known setups on newer prices">(' + num(r.retested) + ' re-tests)</i>' : '');
      var models = (r.models || []).map(function (m) { var mi = modelInfo(m.model); return '<span class="q2-chip q2-cm" title="' + esc(mi[1]) + ' shortlisted ' + m.n + '×">' + mi[0] + ' ' + esc(mi[1]) + (m.n > 1 ? ' ×' + m.n : '') + '</span>'; }).join('');
      return '<button type="button" class="q2-run' + (r.id === cur ? ' q2-on' : '') + '" data-run="' + r.id + '">' +
        '<span class="q2-rid">#' + r.id + '</span><span class="q2-rdt">' + esc(stamp(r.finished_at || r.requested_at)) + '</span>' +
        '<span class="q2-rst">' + st + '<em>' + esc(r.origin === 'owner' ? 'you' : 'daily') + '</em></span>' +
        '<span class="q2-rtr" title="Combinations this run tried">' + tried + '</span>' +
        '<span class="q2-rsh" title="Shortlisted for the blind test">' + (r.status === 'failed' ? '—' : (r.shortlisted || 0) + ' shortlisted') + '</span>' +
        '<span class="q2-chips q2-rmd">' + (models || '<i>no shortlist</i>') + learned(r.learning) + '</span>' + runWins(r) + '</button>';
    }).join('') + (M.picked ? '<button type="button" class="q2-ib" data-run="newest" title="Back to the newest blind test">↺ newest</button>' : '');
  }
  // ET-33966 (6): the run's held-back windows (dates, kind, the 12-coin move), "N of M windows made money" for its best
  // setup with the pooled result against the bar and the closed trades, the sides shortlisted, the window results it
  // reused, whether every input was dated, and any market that could not be loaded (with why)
  function d10(s) { return String(s || '').slice(0, 10); }
  function runWins(r) {
    if (r.status === 'failed') return '';
    var out = '', b = r.best;
    if (b) {
      var mi = modelInfo(b.model), verdict = b.passed ? 'PASSED' : String(b.label || '').replace(/_/g, ' ');
      out += '<span class="q2-win q2-wbest ' + (b.passed ? 'q2-up' : 'q2-down') + '" title="' + esc('Best setup of this run: ' + mi[1] + ' on ' + b.market + ' (' + (b.settings_label || '') + ', ' + (b.side || 'long') + ' side). ' +
        'A setup passes only if it made money on three quarters of the windows, its pooled result over all the windows clears the bar once, and it closed ' + (r.min_trades || 20) + '+ trades, net of fee and slippage.') + '">' +
        esc(mi[1] + ' ' + b.market + ': ' + b.windows_won + ' of ' + b.windows_total + ' windows made money · pooled ' + pct(b.return_pct) + ' vs bar ' + pct(b.bar_pct) + ' · ' + (b.trades == null ? '—' : b.trades) + ' trades · ' + verdict) + '</span>';
    }
    (r.windows || []).forEach(function (w) {
      out += '<span class="q2-win ' + (w.kind === 'rising' ? 'q2-up' : w.kind === 'falling' ? 'q2-down' : '') + '" title="' + esc('Held-back window ' + d10(w.start) + ' → ' + d10(w.end) + ' (' + (w.days || 36) + ' days) with its own search period from ' + d10(w.search_start) + ' (' + (w.search_days || 54) + ' days). ' +
        (w.basket_n || (w.markets || []).length) + '-coin equal-weight hold moved ' + pct(w.basket_move_pct) + ': a ' + (w.kind || 'flat') + ' market. The benchmark is information, not the pass rule.') + '">' +
        esc(day(w.start) + '–' + day(w.end) + ' ' + (w.kind || '') + ' ' + pct(w.basket_move_pct)) + '</span>';
    });
    if (r.windows_note) out += '<span class="q2-win q2-wnote" title="' + esc(r.windows_note) + '">' + esc(r.windows_note) + '</span>';
    var sd = r.shortlisted_sides;
    if (sd) out += '<span class="q2-win" title="Shortlisted setups per side. A passing short (Red) rule starts no paper bot on the spot lane (long only); its card says so in one line.">' + esc('long ' + (sd.long || 0) + ' · short ' + (sd.short || 0)) + '</span>';
    if (r.held_back_reused) out += '<span class="q2-win" title="Window results stored by an earlier run and not replayed: a setup is never re-tested on a window it already failed within 36 days, and is tested on the others.">' + esc(num(r.held_back_reused) + ' window results reused') + '</span>';
    if (r.inputs_dated === true) out += '<span class="q2-win" title="Every input of each window\'s shortlist (search-period numbers, regime read, memory) is dated before that window\'s first held-back bar and stored with the run.">inputs dated ✓</span>';
    else if (r.inputs_dated === false) out += '<span class="q2-win q2-down" title="An input of a shortlist is dated after its window\'s first held-back bar.">inputs dated ✗</span>';
    (r.markets_missing || []).forEach(function (m) {
      var name = typeof m === 'string' ? m : (m.market || '?');
      out += '<span class="q2-win q2-miss" title="' + esc(typeof m === 'string' ? 'could not be loaded' : (m.reason || 'could not be loaded')) + '">' + esc(name + ' could not be loaded') + '</span>';
    });
    return out ? '<span class="q2-wins">' + out + '</span>' : '';
  }
  // ET-33846: what a run took from the earlier ones (skipped blind-test losers, new settings, the regime it read)
  function learned(L) {
    if (!L) return '';
    var sk = L.blind_failures_skipped || 0, nw = L.new_settings_explored || 0, rg = L.regimes || {}, cnt = {};
    Object.keys(rg).forEach(function (m) { var c = rg[m] && rg[m].current; if (c) cnt[c] = (cnt[c] || 0) + 1; });
    var rs = Object.keys(cnt).sort(function (a, b) { return cnt[b] - cnt[a]; }).map(function (k) { return k + ' ' + cnt[k]; }).join(', ');
    var tip = sk + ' setups that already failed the blind test were skipped (not blind-tested again for ' + (L.cooldown_days || 36) + ' days). ' +
      num(nw) + ' tries used settings never tried before. Regime at the end of the search period (markets): ' + (rs || 'n/a') + '.' +
      (L.skipped && L.skipped.length ? ' Skipped: ' + L.skipped.slice(0, 5).map(function (x) { return x.model + ' ' + x.market + ' ' + x.settings_label + ' (failed in #' + x.failed_in_search + ')'; }).join('; ') : '');
    return '<span class="q2-chip q2-learn" title="' + esc(tip) + '">🧠 ' + (sk ? sk + ' losers skipped · ' : '') + num(nw) + ' new</span>';
  }
  function spark(pts) {
    var w = 400, h = 64, lo = Math.min.apply(null, pts), hi = Math.max.apply(null, pts), rg = (hi - lo) || 1;
    var d = pts.map(function (v, i) { return (i ? 'L' : 'M') + (i / (pts.length - 1) * w).toFixed(1) + ' ' + (h - 4 - (v - lo) / rg * (h - 8)).toFixed(1); }).join(' ');
    var up = pts[pts.length - 1] >= pts[0];
    return '<svg viewBox="0 0 ' + w + ' ' + h + '" preserveAspectRatio="none"><path d="' + d + ' L' + w + ' ' + h + ' L0 ' + h + 'Z" fill="' + (up ? 'rgba(0,255,136,.12)' : 'rgba(255,68,68,.12)') + '"/><path d="' + d + '" fill="none" stroke="' + (up ? '#00ff88' : '#ff4444') + '" stroke-width="2"/></svg>';
  }
  var WORD = { pending: 'QUEUED', running: 'RUNNING', paused: 'PAUSED', passed: 'MET THE RULE', failed: 'MISSED', void: 'VOID' };
  function cfgChips(x) {
    var c = x.config || {}, hb = x.held_back || {}, out = [];
    var models = c.models && c.models.length ? c.models : hb.model ? [hb.model] : [];
    models.forEach(function (m) { out.push('<span class="q2-chip q2-cm" title="Model">' + modelInfo(m)[0] + ' ' + esc(modelInfo(m)[1]) + '</span>'); });
    (c.skills || []).forEach(function (k) { out.push('<span class="q2-chip q2-cs" title="Skill">' + skillOf(k)[0] + ' ' + esc(skillOf(k)[1]) + '</span>'); });
    return out.length ? '<div class="q2-chips">' + out.join('') + '</div>' : '';
  }
  function botCard(x) {
    var hb = x.held_back || {}, cfg = x.config || {}, st = cfg.settings || {}, pm = st.perpetual_markets;
    var market = hb.market || (Array.isArray(pm) ? pm[0] : typeof pm === 'string' ? pm.split(/[\s,]+/)[0] : '');
    var up = (x.return_pct || 0) > 0, parts = [];
    if (up || x.status === 'passed') parts.push('PROFITABLE');
    parts.push('PAPER'); parts.push(WORD[x.status] || String(x.status || '').toUpperCase());
    var pts = curveOf(x), cool = x.status !== 'running' && x.status !== 'passed';
    var acts = (x.status === 'running' || x.status === 'pending')
      ? '<button data-q="pause" data-id="' + x.id + '" title="Pause">⏸</button>' : '<button data-q="run" data-id="' + x.id + '" title="Run again from the next pass">▶</button>';
    return '<div class="q2-bot' + (cool ? ' q2-cool' : '') + '" data-setup="' + esc(x.title) + '"><div class="q2-bt"><span class="q2-av">' + headImg('') + '</span><div><div class="q2-nm">' + esc(x.title) + (market ? (String(x.title).indexOf(market) < 0 ? ' · ' + esc(market) : '') + ' <span class="q2-coin q2-cs2">' + coinImg(market) + '</span>' : '') + '</div>' +
      '<div class="q2-bst"><i></i>' + parts.join(' · ') + '</div></div><span class="q2-ret ' + ((x.return_pct || 0) >= 0 ? 'q2-up' : 'q2-down') + '">' + pct(x.return_pct) + '</span></div>' +
      (x.origin === 'search' ? '<div class="q2-same" title="The bot trades the setup that won, nothing mapped or swapped">✓ SAME SETUP AS THE WINNER</div>' : '<div class="q2-same" style="color:#7f93ad" title="' + esc(x.config_text || '') + '">' + esc(x.source ? String(x.source).toUpperCase() : 'PAPER CLONE') + '</div>') +
      cfgChips(x) + (pts.length > 1 ? spark(pts) : '') +
      '<div class="q2-acts">' + acts + '<button data-q="vary" data-id="' + x.id + '" title="Vary: the lab proposes the next variation">⟳</button><button data-q="remove" data-id="' + x.id + '" title="Remove">✕</button><button data-q="config" data-id="' + x.id + '" title="Configuration">⚙</button>' +
      '<span class="q2-kp"><span><b>' + (x.trades == null ? '—' : x.trades) + '</b> trades</span><span>DD <b>' + (x.max_drawdown_pct == null ? '—' : Number(x.max_drawdown_pct).toFixed(1) + '%') + '</b></span>' +
      '<span>SL <b>' + (st.stop_loss_pct == null ? '—' : st.stop_loss_pct + '%') + '</b></span><span>TP <b>' + (st.take_profit_pct == null ? '—' : st.take_profit_pct + '%') + '</b></span></span></div></div>';
  }
  function renderBots() {
    var ov = S.ov, r = ov && ov.rule, tip = ov ? ov.rule_text : '';
    $('rule').innerHTML = r ? '<span title="' + esc(tip) + '">🔁 <b>' + r.min_trades + '+</b> trades</span><span title="' + esc(tip) + '">📈 <b>+' + r.min_return_pct + '%</b></span>' +
      '<span title="' + esc(tip) + '">🛡️ DD <b>&lt;' + r.max_drawdown_pct + '%</b></span><span title="' + esc(tip) + '">🗓️ <b>' + r.window_days + 'd × ' + r.repeats + '</b></span>' +
      '<span title="A bot that meets the rule goes to the Trading desk for your approval">🎯 → desk</span>' : '';
    var empty = '<div class="q2-empty">' + headImg('q2-ebot') + '<span class="q2-big">0</span><span>No profitable agent yet. Winners land here as paper bots.</span></div>';
    if (M.mode === 'sim') {
      $('bots').innerHTML = M.botList.map(function (b) {
        var c = b.cand;
        return '<div class="q2-bot" data-setup="' + esc(c.setup_key) + '" title="Simulated"><div class="q2-bt"><span class="q2-av">' + headImg('') + '</span><div><div class="q2-nm">' + esc(baseOf(c.setup)[1]) + ' · ' + esc(c.market) + ' <span class="q2-coin q2-cs2">' + coinImg(c.market) + '</span></div>' +
          '<div class="q2-bst"><i></i>PROFITABLE · PAPER · RUNNING</div></div><span class="q2-ret ' + (b.ret >= 0 ? 'q2-up' : 'q2-down') + '">' + pct(b.ret) + '</span></div>' +
          '<div class="q2-same" title="The bot trades the setup that won, nothing mapped or swapped">✓ SAME SETUP AS THE WINNER</div>' + setupChips(c.setup) +
          spark(b.pts) + '<div class="q2-acts"><button disabled title="Pause">⏸</button><button disabled title="Vary: the lab proposes the next variation">⟳</button><button disabled title="Remove">✕</button>' +
          '<span class="q2-kp"><span><b>' + b.trades + '</b> trades</span><span>DD <b>' + b.dd.toFixed(1) + '%</b></span><span><b>' + esc(c.settings.replace(' / ', ' · ')) + '</b></span></span></div></div>';
      }).join('') || empty;
      return;
    }
    var exps = ((ov && ov.experiments) || []).slice().sort(function (a, b) {
      var ra = a.return_pct == null ? -1e9 : a.return_pct, rb = b.return_pct == null ? -1e9 : b.return_pct;
      return rb - ra || b.id - a.id;   // best paper return first
    });
    $('bots').innerHTML = exps.length ? exps.map(botCard).join('') : empty;
  }
  function renderCaps() {
    var st = S.st || {};
    var SZ = { build_small: ['S', 'Small build'], build_medium: ['M', 'Medium build'], build_large: ['L', 'Large build'], not_possible: ['✗', 'Not possible'] };
    var can = (st.can_tune || []).map(function (t) { return '<li title="' + esc(t) + '">✓ ' + esc(t.split(':')[0]) + '</li>'; });
    if (M.mode === 'sim') can = can.concat(['Skills', 'Named Combinations', 'Winner → bot, same setup'].map(function (t) { return '<li title="ET-33142">✓ ' + esc(t) + ' <span class="q2-sz">NEW</span></li>'; }));
    $('caps').innerHTML = '<div><h3 class="q2-ok">CAN TUNE</h3><ul>' + can.join('') + '</ul></div>' +
      '<div><h3 class="q2-no">CAN\'T YET</h3><ul>' + (st.cannot_tune || []).map(function (c) {
        var s = SZ[c.feasibility] || ['?', 'Not built yet'];
        return '<li title="' + esc(c.line || c.why || '') + '"><span class="q2-sz ' + (c.feasibility === 'not_possible' ? 'q2-x' : '') + '" title="' + s[1] + '">' + s[0] + '</span>' + esc(c.what.replace(/\s*\(.*\)$/, '')) + '</li>';
      }).join('') + '</ul></div>';
    $('capsbtn').title = (st.what_it_does_not_do || []).join(' ');
    $('memn').textContent = num(st.combinations_tried || 0);
    if (st.cost) $('paper').title = st.cost;
    var dl = $('q-log'); dl.hidden = !(st.access && st.access.allowed && S.cid); if (S.cid) dl.href = API + '/' + S.cid + '/quant-lab/search/log';
  }

  // ---------------------------------------------------------------- the reactor
  //  replay  no search running: the last finished search, played over and over. When the newest ones failed, the badge
  //          says so in red; a failure is not a stage, so it has no screen.
  //  live    a search running: the fields the company WebSocket sends while it runs (done_jobs, total_jobs, percent, eta_seconds).
  var BASE = [['build', '🧩', 'BUILD', 3.2, 0.97], ['blast', '💥', 'BLAST', 4.4, 0.97], ['blind', '🙈', 'BLIND', 3.4, 0.97], ['bar', '🚧', 'THE BAR', 5.6, 0.995], ['bot', '🏆', 'FOUND', 7.0, 0.97]];
  var LAB = 'replay', RUN = '', STAGES = BASE, TOTAL = BASE.reduce(function (a, x) { return a + x[3]; }, 0);
  var cv = $('rx'), ctx = cv.getContext('2d'), W = 0, H = 0, DPR = 1, t0 = performance.now(), offset = 0, parts = [], shake = 0, fired = {}, cells = null;
  var paused = false, held = 0;   // paused: the clock stands at `held`
  var C = { bg: '#06090f', navy: '#0d1520', navy2: '#111a28', line: '#16233a', line3: '#1e3050', text: '#e6edf7', dim: '#7f93ad', dim3: '#3a4d68', cyan: '#00cfff', green: '#00ff88', red: '#ff4444', blue: '#3b82f6' };
  var MONO = "'JetBrains Mono', monospace", BLACK = "'Archivo Black', sans-serif";

  function size() { DPR = Math.min(2, window.devicePixelRatio || 1); W = cv.clientWidth; H = cv.clientHeight; cv.width = W * DPR; cv.height = H * DPR; }
  function accessOk() { var a = S.st && S.st.access; return !a || a.allowed; }
  function goTitle() { var a = S.st && S.st.access; return a && !a.allowed ? (a.locked_line || 'The Quant Lab search is on the Pro plan.') : ((S.st && S.st.cost) || 'Search for a profitable agent now'); }
  function rail() {
    var run = LAB === 'live';
    $('rail').innerHTML = '<button class="q2-pp' + (paused ? ' q2-on' : '') + '" data-pp aria-label="' + (paused ? 'Play' : 'Pause') + '">' + (paused ? '▶' : '⏸') + '</button>' +
      STAGES.map(function (s, i) { return '<button data-st="' + i + '"><span class="q2-e">' + s[1] + '</span><span class="q2-t">' + s[2] + '</span><i></i></button>'; }).join('') +
      '<span class="q2-lab" id="lab"></span><button class="q2-go" data-go title="' + esc(goTitle()) + '"' + (run || !accessOk() ? ' disabled' : '') + '>' + (run ? '● RUNNING ' + livePct() + '%' : '⚡ SEARCH NOW') + '</button>';
  }
  function livePct() { return LIVE && LIVE.total_jobs ? Math.floor(LIVE.percent || 0) : 0; }
  function setLab(s, run) {   // what the reactor shows; it starts from its first stage
    LAB = s; RUN = run; fired = {}; parts = []; rings = []; flash = 0; lastStage = -1; labText = null;
    if (paused) held = STAGES[0][3] * STAGES[0][4]; else { t0 = performance.now(); offset = 0; }
    rail();
  }
  function raw() { return paused ? held : (performance.now() - t0) / 1000 + offset; }
  function now() { return raw() % TOTAL; }
  function startOf(i) { var a = 0; for (var k = 0; k < i; k++) a += STAGES[k][3]; return a; }
  function pause(on) {
    if (on === paused) return;
    if (on) { held = now(); paused = true; } else { t0 = performance.now(); offset = held; paused = false; }
    var b = document.querySelector('[data-pp]'); b.textContent = paused ? '▶' : '⏸'; b.setAttribute('aria-label', paused ? 'Play' : 'Pause'); b.classList.toggle('q2-on', paused);
  }
  function goStage(i) {
    if (LAB === 'live') return;   // a running search shows its own stage
    i = (i + STAGES.length) % STAGES.length; fired = {}; parts = []; lastStage = -1;
    if (paused) held = startOf(i) + STAGES[i][3] * STAGES[i][4];
    else { t0 = performance.now(); offset = startOf(i) + 0.001; }
  }
  // the badge beside the stages: which search this is, or that one is running; red when the newest ones failed
  var labText = null;
  function badge() {
    var s, cls = '';
    if (LAB === 'live') { s = '● LIVE'; cls = 'q2-lv'; }
    else if (M.mode === 'real' && !LAST_GOOD) { s = FAILS.length ? '⚠️ LAST ' + FAILS.length + ' FAILED' : '○ NO SEARCH YET'; cls = FAILS.length ? 'q2-fl' : ''; }
    else if (DOWN && M.mode === 'real') { s = '⚠️ LAST ' + FAILS.length + ' FAILED · ↻ REPLAY · ' + RUN; cls = 'q2-fl'; }
    else { s = '↻ REPLAY · ' + RUN; }
    var go = document.querySelector('[data-go]');
    if (go && LAB === 'live') { var gt = '● RUNNING ' + livePct() + '%'; if (go.textContent !== gt) { go.disabled = true; go.textContent = gt; } }
    if (s === labText) return;
    labText = s; var el = $('lab'); if (!el) return; el.textContent = s; el.className = 'q2-lab ' + cls; el.title = LAB === 'live' ? (LIVE && LIVE.phase ? LIVE.phase : '') : (M.mode === 'real' ? DOWN : '');
  }
  function loopP(sec) { return ((performance.now() / 1000) % sec) / sec; }
  function liveStage() {   // [stage, progress] from the search's own fields
    var f = LIVE || {}, ph = f.phase || '';
    if (/shortlist|held-back/.test(ph)) return [2, loopP(STAGES[2][3])];
    if (f.total_jobs > 0 || /combinations/.test(ph)) return [1, f.total_jobs ? Math.min(1, (f.done_jobs || 0) / f.total_jobs) : 0];
    return [0, loopP(STAGES[0][3])];
  }
  function stageAt(t) { var a = 0; for (var i = 0; i < STAGES.length; i++) { if (t < a + STAGES[i][3]) return [i, (t - a) / STAGES[i][3]]; a += STAGES[i][3]; } return [STAGES.length - 1, 1]; }
  function ease(p) { p = Math.max(0, Math.min(1, p)); return 1 - Math.pow(1 - p, 3); }
  function seg(p, a, b) { return Math.max(0, Math.min(1, (p - a) / (b - a))); }

  function rr(x, y, w, h, r) { ctx.beginPath(); ctx.moveTo(x + r, y); ctx.arcTo(x + w, y, x + w, y + h, r); ctx.arcTo(x + w, y + h, x, y + h, r); ctx.arcTo(x, y + h, x, y, r); ctx.arcTo(x, y, x + w, y, r); ctx.closePath(); }
  function txt(s, x, y, font, color, align, glow) {
    ctx.font = font; ctx.fillStyle = color; ctx.textAlign = align || 'left'; ctx.textBaseline = 'middle';
    if (glow) { ctx.shadowColor = color; ctx.shadowBlur = glow; }
    ctx.fillText(s, x, y); ctx.shadowBlur = 0;
  }
  function chip(s, x, y, border, fs) {
    ctx.font = '700 ' + (fs || 13) + 'px ' + MONO; var w = ctx.measureText(s).width + 20, h = (fs || 13) + 14;
    rr(x, y - h / 2, w, h, 8); ctx.fillStyle = C.navy2; ctx.fill(); ctx.strokeStyle = border; ctx.lineWidth = 1.2; ctx.stroke();
    txt(s, x + 10, y + 1, '700 ' + (fs || 13) + 'px ' + MONO, C.text); return w;
  }
  function burst(x, y, color, n, power) {
    for (var i = 0; i < n; i++) { var a = Math.random() * Math.PI * 2, v = (0.5 + Math.random()) * (power || 6); parts.push({ x: x, y: y, vx: Math.cos(a) * v, vy: Math.sin(a) * v - 1, life: 1, c: color, s: 1 + Math.random() * 3 }); }
  }
  function once(key, fn) { if (!fired[key]) { fired[key] = 1; fn(); } }
  function backdrop(t) {
    ctx.fillStyle = C.bg; ctx.fillRect(0, 0, W, H);
    ctx.strokeStyle = 'rgba(30, 48, 80, .35)'; ctx.lineWidth = 1;
    var off = (t * 18) % 40;
    for (var x = -off; x < W; x += 40) { ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, H); ctx.stroke(); }
    for (var y = 0; y < H; y += 40) { ctx.beginPath(); ctx.moveTo(0, y); ctx.lineTo(W, y); ctx.stroke(); }
    var g = ctx.createRadialGradient(W / 2, H / 2, H * 0.2, W / 2, H / 2, W * 0.7); g.addColorStop(0, 'rgba(0, 207, 255, .05)'); g.addColorStop(1, 'rgba(0, 0, 0, .55)');
    ctx.fillStyle = g; ctx.fillRect(0, 0, W, H);
  }
  function scan() {
    ctx.fillStyle = 'rgba(0, 0, 0, .18)'; for (var y = 0; y < H; y += 3) ctx.fillRect(0, y, W, 1);
  }
  var IMG = {};   // the coin logos and the agent's picture, as images the canvas can draw
  Object.keys(COIN).forEach(function (s) { var im = new Image(); im.src = coinUrl(s); IMG[s] = im; });
  IMG.agent = new Image(); IMG.agent.src = AGENT;
  var EYES = [[502 / 1000, 265 / 1016], [574 / 1000, 260 / 1016]];   // where the agent's eyes sit in agent.webp
  function ready(im) { return im && im.complete && im.naturalWidth > 0; }
  function coin(sym, x, y, r, label) {
    ctx.beginPath(); ctx.arc(x, y, r + 2, 0, Math.PI * 2); ctx.fillStyle = C.navy; ctx.fill();
    if (ready(IMG[sym])) { ctx.save(); ctx.beginPath(); ctx.arc(x, y, r, 0, Math.PI * 2); ctx.clip(); ctx.drawImage(IMG[sym], x - r, y - r, r * 2, r * 2); ctx.restore(); }
    else txt(sym, x, y + 1, '800 ' + Math.round(r * 0.62) + 'px ' + MONO, C.cyan, 'center');
    ctx.beginPath(); ctx.arc(x, y, r + 2, 0, Math.PI * 2); ctx.strokeStyle = 'rgba(0, 207, 255, .35)'; ctx.lineWidth = 1.2; ctx.stroke();
    if (label) txt(sym, x, y + r + 13, '700 11px ' + MONO, C.dim, 'center');
  }
  function bigCounter(n, label, sub, x, y, color) {
    txt(num(n), x, y, '400 64px ' + BLACK, color || C.text, 'left', 24);
    txt(label, x + 4, y + 46, '700 15px ' + MONO, C.dim, 'left');
    if (sub) txt(sub, x + 4, y + 72, '700 13px ' + MONO, C.dim3, 'left');
  }

  // 1 BUILD: a setup is assembled (sim: model or combination + skills); then every setup lands in the grid
  function drawBuild(p) {
    var narrow = W < 1300, n = M.setups.length, gx = narrow ? 30 : W * 0.47, cols = narrow ? 4 : M.mode === 'sim' ? 3 : 4, rows = Math.ceil(n / cols),
      cw = (W - gx - 30) / cols, chh = Math.min(42, (H - (narrow ? 180 : 90)) / rows),
      gy = narrow ? 150 : Math.max(60, (H - rows * chh) / 2);   // wide: the grid stands level with the number beside it
    if (M.mode === 'sim') {
      var f = M.candidates[0].setup, b = baseOf(f), pa = ease(seg(p, 0, 0.42)), cx = W * (narrow ? 0.04 : 0.07), cy = narrow ? 80 : H * 0.46;
      var parts3 = [b[0] + ' ' + b[1]].concat(f.skills.map(function (k) { return skillOf(k)[0] + ' ' + skillOf(k)[1]; }));
      var from = [[-320, cy], [W * 0.5, -40], [W * 0.5, H + 40]], xs = cx;
      parts3.forEach(function (s, i) {
        var tx = xs, ty = cy, fx = from[i][0], fy = from[i][1];
        ctx.font = '700 16px ' + MONO; var w = ctx.measureText(s).width + 20;
        var x = fx + (tx - fx) * pa, y = fy + (ty - fy) * pa;
        chip(s, x, y, i ? C.blue : C.green, 16); xs += w + (pa > 0.98 ? 6 : 26);
      });
      if (p > 0.42) {
        once('snap', function () { burst(cx + 260, cy, C.green, 60, 8); shake = 10; });
        var gl = 1 - seg(p, 0.42, 0.62);
        rr(cx - 12, cy - 28, xs - cx + 6, 56, 14); ctx.strokeStyle = 'rgba(0, 255, 136, ' + (0.5 + 0.5 * gl) + ')'; ctx.lineWidth = 2; ctx.shadowColor = C.green; ctx.shadowBlur = 20 + 30 * gl; ctx.stroke(); ctx.shadowBlur = 0;
        txt('= ONE SETUP', narrow ? xs + 10 : cx, narrow ? cy : cy + 58, '700 15px ' + MONO, C.green, 'left', 10);
      }
      if (!narrow) txt('MODEL / COMBO + SKILLS', cx, 50, '700 14px ' + MONO, C.dim, 'left');
    } else if (narrow) {
      txt(n + ' RULES · NO SKILLS · NO COMBOS', 30, 80, '400 24px ' + BLACK, C.cyan, 'left', 14);
    } else {
      txt('TODAY', W * 0.07, 50, '700 14px ' + MONO, C.dim, 'left');
      bigCounter(n, 'RULES · 1 RULE = 1 SETUP', 'NO SKILLS · NO COMBOS', W * 0.07, H * 0.42, C.cyan);
    }
    var shown = Math.floor(ease(seg(p, M.mode === 'sim' ? 0.3 : 0.05, 0.95)) * n);
    for (var i = 0; i < shown; i++) {
      var s = M.setups[i], x = gx + (i % cols) * cw, y = gy + Math.floor(i / cols) * chh;
      var fresh = i === shown - 1;
      rr(x, y, cw - 10, chh - 8, 8); ctx.fillStyle = fresh ? 'rgba(0, 207, 255, .25)' : C.navy; ctx.fill();
      ctx.strokeStyle = s.kind === 'combo' ? 'rgba(0, 255, 136, .55)' : s.skills.length ? 'rgba(59, 130, 246, .7)' : C.line3; ctx.lineWidth = 1; ctx.stroke();
      txt(setupText(s), x + 10, y + (chh - 8) / 2 + 1, '700 ' + (chh < 34 ? 12 : 13) + 'px ' + MONO, C.text, 'left');
      if (fresh) once('s' + i, function () { burst(x + cw / 2, y + chh / 2, C.cyan, 6, 3); });
    }
    if (M.mode === 'sim') txt(n + ' SETUPS', W - 30, narrow ? 130 : 32, '400 22px ' + BLACK, C.green, 'right', 12);
  }

  // 2 BLAST: every setup x every market x every setting, replayed; the counter runs to what was tried
  function cellsFor() {
    if (cells && cells.mode === M.mode) return cells;
    var r = rng(M.mode === 'sim' ? 33142 : (M.tried || 1) % 100000 + 1), v = [];
    for (var i = 0; i < M.setups.length; i++) { v.push([]); for (var j = 0; j < M.markets.length; j++) v[i].push((r() + r() + r() - 1.6) * 14); }
    var hot = M.candidates.map(function (c) {
      var i = M.setups.map(setupKey).indexOf(c.setup_key), j = M.markets.indexOf(c.market); if (i >= 0 && j >= 0 && c.search != null) v[i][j] = c.search; return [i, j];
    });
    cells = { mode: M.mode, v: v, hot: hot }; return cells;
  }
  function drawBlast(p, t) {
    var cl = cellsFor(), n = M.setups.length, m = M.markets.length, x0 = 200, y0 = 70, mw = W - x0 - 330, ch = (H - y0 - 20) / n, cw = mw / m, fs = ch >= 24 ? 13 : 11;
    M.markets.forEach(function (s, j) { coin(s, x0 + j * cw + cw / 2, 26, 13, true); });
    // live: the cells follow the feed's done_jobs, evenly, as a running search does; a replay eases through it
    var live = LAB === 'live', fd = live ? (LIVE || {}) : null, ftot = live ? (fd.total_jobs || 0) : 0;
    var prog = live ? (ftot ? Math.min(1, (fd.done_jobs || 0) / ftot) : 0) : ease(seg(p, 0, 0.82)), hotAt = live ? 0.92 : 0.84;
    var total = n * m, lit = Math.floor(prog * total), k = M.settings, sw = (cw - 8) / Math.ceil(k / 3), sh = (ch - 4) / 3;   // a setting is one rectangle of a three-row block filling the cell
    for (var i = 0; i < n; i++) {
      var s = M.setups[i];
      var lab = setupText(s); if (lab.length > 22) lab = lab.slice(0, 21) + '…';
      txt(lab, x0 - 10, y0 + i * ch + ch / 2, '700 ' + fs + 'px ' + MONO, i * m < lit ? C.dim : C.dim3, 'right');
      for (var j = 0; j < m; j++) {
        var idx = i * m + j, x = x0 + j * cw, y = y0 + i * ch;
        ctx.fillStyle = C.navy; ctx.fillRect(x + 1, y + 1, cw - 2, ch - 2);
        if (idx < lit) {
          var v = cl.v[i][j], a = Math.min(0.85, 0.15 + Math.abs(v) / 30);
          ctx.fillStyle = v >= 0 ? 'rgba(0, 255, 136, ' + a + ')' : 'rgba(255, 68, 68, ' + (a * 0.7) + ')';
          for (var q = 0; q < k; q++) {
            ctx.globalAlpha = 0.72 + 0.28 * (((i * 31 + j * 17 + q * 7) % 10) / 10);   // the settings differ a little, as their results do
            ctx.fillRect(x + 4 + Math.floor(q / 3) * sw, y + 2 + (q % 3) * sh, sw - 1, sh - 1);
          }
          ctx.globalAlpha = 1;
        }
        if (idx === lit && (live ? ftot > 0 : true)) { ctx.fillStyle = '#ffffff'; ctx.shadowColor = C.cyan; ctx.shadowBlur = 24; ctx.fillRect(x, y, cw, ch); ctx.shadowBlur = 0; if (Math.random() < 0.5) burst(x + cw / 2, y + ch / 2, C.cyan, 2, 4); }
      }
    }
    if (lit < total && (!live || ftot > 0)) { var bi = Math.floor(lit / m); ctx.fillStyle = 'rgba(0, 207, 255, .12)'; ctx.fillRect(x0, y0 + bi * ch, mw, ch); }
    if (p > hotAt && !live) {
      var pulse = 0.5 + 0.5 * Math.sin(p * 60);
      cl.hot.forEach(function (h, r) {
        if (h[0] < 0) return; var x = x0 + h[1] * cw, y = y0 + h[0] * ch;
        ctx.strokeStyle = C.green; ctx.lineWidth = 2; ctx.shadowColor = C.green; ctx.shadowBlur = 10 + 14 * pulse; ctx.strokeRect(x - 1, y - 1, cw + 2, ch + 2); ctx.shadowBlur = 0;
        txt(String(r + 1), x + cw + 6, y + ch / 2, '400 13px ' + BLACK, C.green, 'left');
      });
      once('top5', function () { shake = 6; });
    }
    if (live) {   // the feed's numbers: done of total, percent, time left
      txt('● LIVE', W - 296, H * 0.36 - 64, '400 22px ' + BLACK, 'rgba(0, 255, 136, ' + (0.55 + 0.45 * Math.sin(t * 6)) + ')', 'left', 14);
      bigCounter(fd.done_jobs || 0, 'OF ' + num(ftot) + ' · ' + Math.floor(fd.percent || 0) + '%', null, W - 300, H * 0.36, C.green);
      txt(fd.eta_seconds ? 'LEFT ≈ ' + dur(fd.eta_seconds) : ftot && fd.done_jobs >= ftot ? 'ALL REPLAYED' : 'LEFT: ESTIMATING', W - 296, H * 0.36 + 72, '700 15px ' + MONO, C.text, 'left');
      var bw = 270, by = H * 0.36 + 98;
      rr(W - 296, by - 5, bw, 10, 5); ctx.fillStyle = C.navy2; ctx.fill();
      rr(W - 296, by - 5, Math.max(10, bw * prog), 10, 5); ctx.fillStyle = C.green; ctx.shadowColor = C.green; ctx.shadowBlur = 14; ctx.fill(); ctx.shadowBlur = 0;
    } else {
      bigCounter(Math.round(prog * M.tried), 'TRIED', M.setups.length * m * k === M.tried ? M.setups.length + ' × ' + m + ' × ' + k : '', W - 300, H * 0.36, C.cyan);
      txt('ON PAST PRICES', W - 296, H * 0.36 + 98, '700 13px ' + MONO, C.dim3, 'left');
    }
  }

  // 3 BLIND: the best few rise; the last part of history is walled off from the search
  function method() { var m = /(\d+)%\s+of\s+(\d+)\s+days/.exec(((S.st || {}).method || {}).search_period || '') || [0, 60, 90]; return { seen: +m[1], days: +m[2] }; }
  function cardRow(p, yTop) {
    var n = M.candidates.length, gap = 14, w = (W - 60 - gap * (n - 1)) / n;
    M.candidates.forEach(function (c, i) {
      var a = ease(seg(p, i * 0.06, 0.3 + i * 0.06)), x = 30 + i * (w + gap), y = yTop + (1 - a) * 160;
      ctx.globalAlpha = a; rr(x, y, w, 92, 12); ctx.fillStyle = C.navy; ctx.fill(); ctx.strokeStyle = C.line3; ctx.lineWidth = 1; ctx.stroke();
      txt('#' + (i + 1), x + 12, y + 18, '400 14px ' + BLACK, C.dim3, 'left');
      ctx.font = '700 13px ' + MONO; var lab = setupText(c.setup); while (ctx.measureText(lab).width > w - 70 && lab.length > 4) lab = lab.slice(0, -2);
      txt(lab, x + 44, y + 18, '700 13px ' + MONO, C.text, 'left');
      coin(c.market, x + w - 26, y + 26, 16);
      txt(pct(c.search), x + 12, y + 58, '400 30px ' + BLACK, C.cyan, 'left', 14);
      txt('SEEN', x + w - 12, y + 62, '700 12px ' + MONO, C.dim, 'right');
      ctx.globalAlpha = 1;
    });
  }
  function drawBlind(p) {
    cardRow(p, 26);
    var md = method(), x0 = 30, x1 = W - 30, y = H * 0.64, sw = (x1 - x0) * md.seen / 100, gap = Math.max(8, (x1 - x0) / (md.days * 24) * 24);
    var r = rng(md.days), pts = [], v = 0;
    for (var i = 0; i <= 200; i++) { v += (r() - 0.47) * 9; pts.push(v); }
    var lo = Math.min.apply(null, pts), hi = Math.max.apply(null, pts), drawTo = ease(seg(p, 0.15, 0.62));
    ctx.beginPath();
    for (i = 0; i <= 200; i++) { var x = x0 + i / 200 * (x1 - x0); if (x > x0 + sw) break; if (i / 200 > drawTo * md.seen / 100) break; var yy = y + 50 - (pts[i] - lo) / (hi - lo) * 150; i ? ctx.lineTo(x, yy) : ctx.moveTo(x, yy); }
    ctx.strokeStyle = C.cyan; ctx.lineWidth = 2; ctx.shadowColor = C.cyan; ctx.shadowBlur = 10; ctx.stroke(); ctx.shadowBlur = 0;
    ctx.fillStyle = C.cyan; ctx.fillRect(x0, y + 62, sw, 4);
    txt(md.seen + '% SEEN', x0, y + 84, '700 14px ' + MONO, C.cyan, 'left');
    ctx.fillStyle = C.dim3; ctx.fillRect(x0 + sw + 2, y - 60, gap - 4, 130);
    txt('24H', x0 + sw + gap / 2, y + 84, '700 12px ' + MONO, C.dim, 'center');
    var wallX = x0 + sw + gap, drop = ease(seg(p, 0.5, 0.62)), wy = (y - 60) - (1 - drop) * 300;
    if (drop > 0) {
      ctx.save(); rr(wallX, wy, x1 - wallX, 130, 10); ctx.clip();
      ctx.fillStyle = '#0d1520'; ctx.fillRect(wallX, wy, x1 - wallX, 130);
      ctx.strokeStyle = 'rgba(255, 68, 68, .35)'; ctx.lineWidth = 6;
      for (var hx = wallX - 140; hx < x1; hx += 26) { ctx.beginPath(); ctx.moveTo(hx, wy + 130); ctx.lineTo(hx + 130, wy); ctx.stroke(); }
      ctx.restore();
      rr(wallX, wy, x1 - wallX, 130, 10); ctx.strokeStyle = C.red; ctx.lineWidth = 2; ctx.stroke();
      txt('🙈  BLIND · ' + (100 - md.seen) + '%', wallX + (x1 - wallX) / 2, wy + 65, '400 28px ' + BLACK, C.text, 'center', 14);
      if (drop >= 1) once('wall', function () { shake = 14; burst(wallX + (x1 - wallX) / 2, y + 70, C.red, 50, 7); });
    }
    txt(md.days + ' DAYS · HOURLY', x1, y + 84, '700 12px ' + MONO, C.dim3, 'right');
  }

  // 4 THE BAR: each one is re-run on the blind part; a laser at its bar; most smash below it
  function drawBar(p) {
    var n = M.candidates.length, top = 104, bot = H - 50, gap = 26, w = (W - 140 - gap * Math.max(0, n - 1)) / Math.max(1, n);
    var hi = Math.max(36, Math.max.apply(null, M.candidates.map(function (c) { return Math.max(c.search || 0, c.bar); })) + 4);
    var lo = Math.min(-16, Math.min.apply(null, M.candidates.map(function (c) { return c.held; })) - 3);
    function Y(v) { return top + (hi - v) / (hi - lo) * (bot - top); }
    txt('THE BAR RISES WITH EVERY TRY', 30, 24, '700 14px ' + MONO, C.dim, 'left');
    txt('z ' + M.z.toFixed(2) + ' · ' + num(M.tried) + ' TRIES', W - 30, 24, '700 14px ' + MONO, C.green, 'right', 8);
    ctx.strokeStyle = C.dim3; ctx.lineWidth = 1; ctx.setLineDash([4, 6]); ctx.beginPath(); ctx.moveTo(70, Y(0)); ctx.lineTo(W - 30, Y(0)); ctx.stroke(); ctx.setLineDash([]);
    txt('0%', 60, Y(0), '700 12px ' + MONO, C.dim, 'right');
    M.candidates.forEach(function (c, i) {
      var x = 90 + i * (w + gap), st = 0.08 + i * 0.16, run = ease(seg(p, st, st + 0.12)), doneP = p >= st + 0.12;
      txt(setupText(c.setup).split(' + ')[0], x, top - 40, '700 13px ' + MONO, C.text, 'left');
      coin(c.market, x + w - 16, top - 40, 14);
      // the search-period result, a ghost
      ctx.strokeStyle = 'rgba(0, 207, 255, .45)'; ctx.setLineDash([3, 4]); ctx.strokeRect(x + w * 0.1, Y(c.search || 0), w * 0.28, Y(0) - Y(c.search || 0)); ctx.setLineDash([]);
      txt(pct(c.search), x + w * 0.24, Y(c.search || 0) - 12, '700 12px ' + MONO, C.cyan, 'center');
      // the laser
      var broken = doneP && c.won, lz = Y(c.bar), flick = 0.7 + 0.3 * Math.sin(p * 90 + i);
      if (!broken) { ctx.strokeStyle = 'rgba(0, 255, 136, ' + flick + ')'; ctx.lineWidth = 3; ctx.shadowColor = C.green; ctx.shadowBlur = 16; ctx.beginPath(); ctx.moveTo(x, lz); ctx.lineTo(x + w, lz); ctx.stroke(); ctx.shadowBlur = 0; }
      else { ctx.strokeStyle = 'rgba(0, 255, 136, .35)'; ctx.lineWidth = 2; ctx.beginPath(); ctx.moveTo(x, lz); ctx.lineTo(x + w * 0.42, lz + 6); ctx.moveTo(x + w * 0.62, lz - 6); ctx.lineTo(x + w, lz); ctx.stroke(); }
      txt('BAR ' + c.bar.toFixed(2) + '%', x, lz + 14, '700 12px ' + MONO, C.green, 'left');
      // the blind run
      var v = c.held * run, yv = Y(v), y0 = Y(0), col = !doneP ? C.cyan : c.won ? C.green : C.red;
      ctx.fillStyle = col; ctx.shadowColor = col; ctx.shadowBlur = doneP ? 22 : 10;
      ctx.fillRect(x + w * 0.48, Math.min(yv, y0), w * 0.4, Math.max(2, Math.abs(y0 - yv))); ctx.shadowBlur = 0;
      if (doneP) {
        once('b' + i, function () { shake = c.won ? 8 : 16; burst(x + w * 0.68, c.won ? lz : yv, c.won ? C.green : C.red, c.won ? 90 : 55, c.won ? 9 : 7); });
        // a winner's label sits above its bar; a loser's below, even a loser that made money
        txt((c.won ? '✓ ' : '✗ ') + pct(c.held), x + w * 0.68, c.won ? yv - 20 : Math.max(yv, y0) + 22, '400 22px ' + BLACK, c.won ? C.green : C.red, 'center', 16);
      }
    });
    if (!n) txt('NOTHING TO TEST YET', W / 2, H / 2, '400 28px ' + BLACK, C.dim3, 'center');
  }

  // 5 FOUND: a winner becomes a paper bot with the very same setup; no winner, no agent
  var flash = 0, rings = [], ringX = 0, ringY = 0;
  function hexPath(cx, cy, r, rot) {
    ctx.beginPath();
    for (var k = 0; k < 6; k++) { var a = rot + k * Math.PI / 3; ctx[k ? 'lineTo' : 'moveTo'](cx + Math.cos(a) * r, cy + Math.sin(a) * r); }
    ctx.closePath();
  }
  function bolt(x1, y1, x2, y2, color) {
    ctx.beginPath(); ctx.moveTo(x1, y1);
    for (var k = 1; k < 7; k++) { var f = k / 7; ctx.lineTo(x1 + (x2 - x1) * f + (Math.random() - 0.5) * 26, y1 + (y2 - y1) * f + (Math.random() - 0.5) * 26); }
    ctx.lineTo(x2, y2); ctx.strokeStyle = color; ctx.lineWidth = 1.6; ctx.shadowColor = color; ctx.shadowBlur = 14; ctx.stroke(); ctx.shadowBlur = 0;
  }
  function slam(s, x, y, size, p0, p, color) {   // a title that lands hard, split into cyan and green for a beat
    var a = ease(seg(p, p0, p0 + 0.06)), sc = 1 + (1 - a) * 1.4, gl = (1 - seg(p, p0 + 0.06, p0 + 0.16)) * 5;
    if (a <= 0) return;
    ctx.save(); ctx.globalAlpha = a; ctx.translate(x, y); ctx.scale(sc, sc);
    if (gl > 0.2) { txt(s, -gl, 0, '400 ' + size + 'px ' + BLACK, C.cyan, 'left'); txt(s, gl, 0, '400 ' + size + 'px ' + BLACK, C.green, 'left'); }
    txt(s, 0, 0, '400 ' + size + 'px ' + BLACK, color || C.text, 'left', 22); ctx.restore();
  }
  // the agent's picture, its edges melted into the dark so it is not a framed photo
  function agentBox() { var ih = H * 1.25, iw = ih * 1000 / 1016; return { x: W * 0.02, y: -H * 0.08, w: iw, h: ih }; }
  var AGM = null;   // the picture with its edges faded to transparent, made once: the grid shows through, no frame
  function agentMasked() {
    if (AGM || !ready(IMG.agent)) return AGM;
    var c = document.createElement('canvas'); c.width = 1000; c.height = 1016;
    var x = c.getContext('2d'); x.drawImage(IMG.agent, 0, 0, 1000, 1016); x.globalCompositeOperation = 'destination-in';
    [[1000, 0, [[0, 0], [0.16, 1], [0.64, 1], [1, 0]]], [0, 1016, [[0, 0], [0.06, 1], [0.7, 1], [1, 0]]]].forEach(function (m) {
      var gr = x.createLinearGradient(0, 0, m[0], m[1]); m[2].forEach(function (s) { gr.addColorStop(s[0], 'rgba(0, 0, 0, ' + s[1] + ')'); });
      x.fillStyle = gr; x.fillRect(0, 0, 1000, 1016);
    });
    AGM = c; return AGM;
  }
  function drawBot(p, t) {
    var g = agentBox();
    if (!M.lastWon) {   // no winner: the agent stays dark
      var a = ease(seg(p, 0, 0.25)), jit = Math.random() < 0.06 ? (Math.random() - 0.5) * 12 : 0;
      var dark = agentMasked();
      if (dark) { ctx.save(); ctx.globalAlpha = a; ctx.filter = 'grayscale(1) brightness(.35)'; ctx.drawImage(dark, g.x + jit, g.y, g.w, g.h); ctx.restore(); }
      txt('0', W * 0.47, H * 0.42, '400 150px ' + BLACK, C.red, 'center', 30);
      slam('NO WINNER', W * 0.56, H * 0.36, 44, 0.1, p);
      slam('NO PROFITABLE AGENT', W * 0.56, H * 0.36 + 56, 44, 0.18, p);
      var nc = M.candidates.length;
      txt(nc + ' BLIND-TESTED · ' + nc + ' THROWN OUT', W * 0.56, H * 0.36 + 112, '700 15px ' + MONO, C.dim, 'left');
      return;
    }
    var b = M.botList[0], c = b.cand, cx = g.x + g.w * 0.55, cy = g.y + g.h * 0.42;
    ringX = cx; ringY = cy;
    // 1 charge: the winning setup flies in and is crushed into a core
    if (p < 0.15) {
      var f = ease(seg(p, 0, 0.11)), orb = 6 + 40 * seg(p, 0.05, 0.15);
      ctx.save(); ctx.globalAlpha = 1 - seg(p, 0.08, 0.12);
      chip(setupText(c.setup), 40 + (cx - 160 - 40) * f, cy + Math.sin(p * 40) * 3, C.green, 16); ctx.restore();
      var gr = ctx.createRadialGradient(cx, cy, 0, cx, cy, orb * 2.2); gr.addColorStop(0, '#ffffff'); gr.addColorStop(0.35, 'rgba(0, 255, 136, .9)'); gr.addColorStop(1, 'rgba(0, 255, 136, 0)');
      ctx.fillStyle = gr; ctx.beginPath(); ctx.arc(cx, cy, orb * 2.2, 0, Math.PI * 2); ctx.fill();
      for (var k = 0; k < 4; k++) { var an = Math.random() * Math.PI * 2, d = 120 + Math.random() * 120; bolt(cx, cy, cx + Math.cos(an) * d, cy + Math.sin(an) * d, k % 2 ? C.cyan : C.green); }
      shake = Math.max(shake, 3 * seg(p, 0.05, 0.15));
      return;
    }
    once('flash', function () { flash = 1; shake = 26; burst(cx, cy, C.green, 160, 13); burst(cx, cy, C.cyan, 90, 9); rings.push(0, -0.12, -0.24); });   // three waves, a beat apart
    // 2 materialise: a pillar of light and two hex rings, the agent built from the floor up under a scan beam, a hologram until it is whole
    var rev = ease(seg(p, 0.16, 0.42)), zoom = 1 + 0.035 * seg(p, 0.42, 1), R = g.h * 0.5;
    var pil = ctx.createLinearGradient(cx - 110, 0, cx + 110, 0); pil.addColorStop(0, 'rgba(0, 255, 136, 0)'); pil.addColorStop(0.5, 'rgba(0, 255, 136, .16)'); pil.addColorStop(1, 'rgba(0, 255, 136, 0)');
    ctx.fillStyle = pil; ctx.fillRect(cx - 110, 0, 220, H);
    ctx.lineWidth = 2; ctx.setLineDash([10, 8]);
    hexPath(cx, cy, R * 0.86, t * 0.6); ctx.strokeStyle = 'rgba(0, 207, 255, .5)'; ctx.stroke();
    hexPath(cx, cy, R * 0.98, -t * 0.4); ctx.strokeStyle = 'rgba(0, 255, 136, .4)'; ctx.stroke(); ctx.setLineDash([]);
    var am = agentMasked();
    if (am) {
      var top = g.y + g.h * (1 - rev), ex0 = g.x + g.w * EYES[0][0], ey0 = g.y + g.h * EYES[0][1];
      ctx.save(); ctx.beginPath(); ctx.rect(g.x - 20, top, g.w + 40, g.h); ctx.clip();
      ctx.translate(ex0, ey0); ctx.scale(zoom, zoom); ctx.translate(-ex0, -ey0);   // a slow push in on the face
      if (rev < 1) ctx.globalAlpha = 0.7 + Math.random() * 0.3;
      ctx.drawImage(am, g.x, g.y, g.w, g.h);
      if (rev < 1) {   // hologram: a cyan cast over the agent only, and a few torn slices
        ctx.globalAlpha = 0.5; ctx.filter = 'sepia(1) hue-rotate(130deg) saturate(4)'; ctx.drawImage(am, g.x, g.y, g.w, g.h);
        ctx.filter = 'none'; ctx.globalAlpha = 0.9;
        for (var sl = 0; sl < 3; sl++) { var sy = top + Math.random() * (g.y + g.h - top), sh = 4 + Math.random() * 14, off = (Math.random() - 0.5) * 30;
          ctx.drawImage(am, 0, (sy - g.y) / g.h * 1016, 1000, sh / g.h * 1016, g.x + off, sy, g.w, sh); }
      } else {   // alive: the eyes burn
        ctx.globalCompositeOperation = 'lighter';
        EYES.forEach(function (e) {
          var x = g.x + g.w * e[0], y = g.y + g.h * e[1], rad = 16 * (0.85 + 0.35 * Math.sin(t * 4));
          var eg = ctx.createRadialGradient(x, y, 0, x, y, rad); eg.addColorStop(0, 'rgba(0, 255, 136, .9)'); eg.addColorStop(1, 'rgba(0, 255, 136, 0)');
          ctx.fillStyle = eg; ctx.beginPath(); ctx.arc(x, y, rad, 0, Math.PI * 2); ctx.fill();
        });
        ctx.globalCompositeOperation = 'source-over';
      }
      ctx.restore();
      if (rev < 1) {
        ctx.fillStyle = '#ffffff'; ctx.shadowColor = C.green; ctx.shadowBlur = 30; ctx.fillRect(g.x + g.w * 0.1, top - 2, g.w * 0.8, 4); ctx.shadowBlur = 0;
        if (Math.random() < 0.7) { burst(g.x + g.w * 0.12, top, C.green, 2, 4); burst(g.x + g.w * 0.88, top, C.cyan, 2, 4); }
      } else if (Math.random() < 0.25) {
        parts.push({ x: g.x + g.w * (0.3 + Math.random() * 0.5), y: H * 0.95, vx: (Math.random() - 0.5) * 0.6, vy: -1.5 - Math.random() * 2, g: -0.01, life: 1, c: Math.random() < 0.5 ? C.green : C.cyan, s: 1.5 + Math.random() * 2 });
      }
    }
    // 3 the title lands
    var px0 = W * 0.4, pw = W - px0 - 40;
    slam('PROFITABLE AGENT', px0, 56, 50, 0.38, p);
    slam('FOUND', px0, 112, 50, 0.44, p, C.green);
    once('t1', function () { if (p >= 0.44) shake = Math.max(shake, 12); });
    // 4 its card: the same setup, now trading on paper
    var pa = ease(seg(p, 0.5, 0.62)), dx = (1 - pa) * 120;
    if (pa <= 0) return;
    ctx.save(); ctx.globalAlpha = pa; ctx.translate(dx, 0);
    coin(c.market, px0 + 16, 170, 16);
    txt(baseOf(c.setup)[1].toUpperCase() + ' · ' + c.market, px0 + 44, 170, '400 24px ' + BLACK, C.text, 'left');
    txt('● PAPER · TRADES THE SETUP THAT WON', px0, 204, '700 13px ' + MONO, C.green, 'left', 6);
    var cxp = px0; [baseOf(c.setup)[0] + ' ' + baseOf(c.setup)[1]].concat(c.setup.skills.map(function (k) { return skillOf(k)[0] + ' ' + skillOf(k)[1]; })).forEach(function (s, i) { cxp += chip(s, cxp, 238, i ? C.blue : C.green, 14) + 8; });
    txt('✓ SAME SETUP', cxp + 8, 238, '700 14px ' + MONO, C.green, 'left', 8);
    var drawn = Math.max(2, Math.floor(ease(seg(p, 0.58, 0.96)) * b.pts.length)), lo = Math.min.apply(null, b.pts), hi = Math.max.apply(null, b.pts), ex = px0, ew = pw - 200, ey = 278, eh = H - ey - 56;
    rr(ex - 10, ey - 10, pw + 10, eh + 20, 14); ctx.fillStyle = 'rgba(13, 21, 32, .85)'; ctx.fill(); ctx.strokeStyle = 'rgba(0, 255, 136, .35)'; ctx.lineWidth = 1.5; ctx.stroke();
    ctx.beginPath();
    for (var i = 0; i < drawn; i++) { var qx = ex + 10 + i / (b.pts.length - 1) * (ew - 20), qy = ey + 10 + (eh - 20) - (b.pts[i] - lo) / ((hi - lo) || 1) * (eh - 20); i ? ctx.lineTo(qx, qy) : ctx.moveTo(qx, qy); }
    ctx.strokeStyle = C.green; ctx.lineWidth = 3; ctx.shadowColor = C.green; ctx.shadowBlur = 14; ctx.stroke(); ctx.shadowBlur = 0;
    var shownRet = M.mode === 'sim' ? b.pts[drawn - 1] : b.ret;
    txt(pct(shownRet), px0 + pw - 20, ey + eh / 2 - 8, '400 44px ' + BLACK, shownRet >= 0 ? C.green : C.red, 'right', 18);
    txt('LIVE · PAPER', px0 + pw - 20, ey + eh / 2 + 30, '700 12px ' + MONO, C.dim, 'right');
    ctx.restore();
  }

  var DRAW = { build: drawBuild, blast: drawBlast, blind: drawBlind, bar: drawBar, bot: drawBot }, lastStage = -1;
  function frame() {
    var t, si, p;
    if (LAB === 'live') { var ls = liveStage(); si = ls[0]; p = ls[1]; t = performance.now() / 1000; }
    else { t = now(); var sp = stageAt(t); si = sp[0]; p = sp[1]; }
    if (si !== lastStage) { if (si === 0) fired = {}; lastStage = si; parts = []; rings = []; flash = 0; }
    ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    backdrop(t);
    if (shake > 0.3) { ctx.translate((Math.random() - 0.5) * shake, (Math.random() - 0.5) * shake); shake *= 0.86; } else shake = 0;
    DRAW[STAGES[si][0]](p, t);
    for (var r = rings.length - 1; r >= 0; r--) {   // shockwaves: each a radius growing out of the birth point
      rings[r] += 0.022; if (rings[r] > 1) { rings.splice(r, 1); continue; }
      var rr0 = rings[r]; if (rr0 <= 0) continue;
      ctx.beginPath(); ctx.arc(ringX, ringY, rr0 * W * 0.7, 0, Math.PI * 2); ctx.strokeStyle = 'rgba(0, 255, 136, ' + (1 - rr0) * 0.8 + ')'; ctx.lineWidth = 6 * (1 - rr0) + 1; ctx.stroke();
    }
    for (var i = parts.length - 1; i >= 0; i--) {
      var q = parts[i]; q.x += q.vx; q.y += q.vy; q.vy += q.g == null ? 0.12 : q.g; q.vx *= 0.98; q.life -= 0.018;
      if (q.life <= 0) { parts.splice(i, 1); continue; }
      ctx.globalAlpha = q.life; ctx.fillStyle = q.c; ctx.fillRect(q.x, q.y, q.s, q.s);
    }
    ctx.globalAlpha = 1; ctx.setTransform(DPR, 0, 0, DPR, 0, 0);
    if (flash > 0.02) { ctx.fillStyle = 'rgba(230, 237, 247, ' + flash + ')'; ctx.fillRect(0, 0, W, H); flash *= 0.86; }
    scan();
    var btns = document.querySelectorAll('[data-st]');
    for (var j = 0; j < btns.length; j++) { btns[j].className = j === si ? 'q2-on' : j < si ? 'q2-done' : ''; btns[j].lastChild.style.width = j === si ? (p * 100) + '%' : '0'; }
    badge();
    window.QL.t = t; window.QL.stage = si; window.QL.paused = paused; window.QL.lab = LAB;
    requestAnimationFrame(frame);
  }

  // ---------------------------------------------------------------- state: modes, data, live
  function runLabel() { return MODE === 'sim' ? 'LAST SEARCH' : LAST_GOOD ? day(LAST_GOOD.finished_at) : ''; }
  var curKey = null;
  function enterState() {
    if (MODE === 'real' && active(LIVE)) setLab('live', '');
    else setLab('replay', runLabel());
  }
  function paint() {
    M = MODE === 'sim' ? SIM : REAL; cells = null;
    $('simtag').hidden = MODE !== 'sim';
    renderScore(); renderTop(); renderBots(); renderCaps();
    window.QL.mode = MODE;
    window.QL.sim = { setups: SIM.setups.length, markets: SIM.markets, settings: SIM.settings, tried: SIM.tried, checked: SIM.checked, bots: SIM.bots, z: SIM.z,
      candidates: SIM.candidates.map(function (c) { return { setup_key: c.setup_key, market: c.market, search: c.search, held: c.held, bar: c.bar, won: c.won }; }) };
    var key = MODE + '|' + (MODE === 'real' && active(LIVE) ? 'live' : 'replay') + '|' + (MODE === 'real' && LAST_GOOD ? LAST_GOOD.id : '');
    if (key !== curKey) {   // the lab's state changed: the reactor starts over; a data refresh alone does not reset it
      var keep = window.QL.stage || 0; curKey = key; enterState();
      if (paused) { keep = Math.min(keep, STAGES.length - 1); held = startOf(keep) + STAGES[keep][3] * STAGES[keep][4]; }
    } else { rail(); labText = null; }
    [].forEach.call(document.querySelectorAll('[data-mode]'), function (b) { b.className = b.getAttribute('data-mode') === MODE ? 'q2-on' : ''; });
  }
  function apply() {
    REAL = realModel();
    var s = S.st && S.st.search;
    if (SELECTED != null && LIVE == null && active(s)) SELECTED = null;   // a new search starting takes the reactor live
    LIVE = active(s) ? s : null;   // a fresh status read is the truth; the socket moves it between reads
    paint();
  }
  function setMode(m) { MODE = m; curKey = null; paint(); }

  // ET-33496 item 5: the three reads run at once (they ran one after the other, ~6.5 s of zeros); the results read
  // answers 403 for a plan without the search, which is simply no results
  function loadAll() {
    if (!S.cid) return Promise.resolve();
    function soft(p) { return api('GET', '/' + S.cid + p).catch(function () { return null; }); }
    return Promise.all([soft('/quant-lab'), soft('/quant-lab/search'), soft('/quant-lab/search/results?limit=200')]).then(function (r) {
      S.ov = r[0]; S.st = r[1]; S.res = (S.st && S.st.access && S.st.access.allowed) ? r[2] : null;
      S.loaded = true; apply();
    });
  }
  var reloadT;
  function later() { clearTimeout(reloadT); reloadT = setTimeout(loadAll, 600); }

  // the company socket: progress, combinations and time left are pushed, never polled
  var backoff = 1000;
  function connect() {
    try { S.ws = new WebSocket((location.protocol === 'https:' ? 'wss://' : 'ws://') + location.host + '/ws/company/' + S.cid); } catch (e) { return; }
    S.ws.onopen = function () { if (backoff > 1000) later(); backoff = 1000; };
    S.ws.onmessage = function (m) {
      var d; try { d = JSON.parse(m.data); } catch (e) { return; }
      if (d.type === 'search' && d.search) {
        var was = LIVE && LIVE.status;
        if (S.st) S.st.search = d.search;
        if (active(d.search)) { LIVE = d.search; if (MODE === 'real' && LAB !== 'live') paint(); }
        else { LIVE = null; later(); }
        if (was && was !== d.search.status) later();
      } else if (d.type === 'event' && /^(quant_search|bot_experiment|approval_)/.test(d.kind || '')) later();
    };
    S.ws.onclose = function () { setTimeout(connect, backoff); backoff = Math.min(backoff * 2, 30000); };
  }

  // ---------------------------------------------------------------- the owner's controls: rule, add bot, bot actions, memory
  function modal(html) { $('xm-card').innerHTML = html; $('xm').hidden = false; }
  function close() { $('xm').hidden = true; }
  function fail(id, er) { if (er && er.status === 401) { close(); return noCompany(true); } var m = $(id); if (m) { m.textContent = er.message; m.hidden = false; } }
  // ET-33878: a visitor with no company (signed out, or signed in without one) gets the company builder's card, not
  // an API error line. One button: Start a company.
  function noCompany(signedOut) {
    if (signedOut) S.signedOut = true;
    var so = S.signedOut;
    modal('<div class="q2-gate"><button class="xx" data-q="close" title="Back">×</button>' +
      (so ? '<h3>Sign up first.</h3><p>A company belongs to a Cymetica account.</p>'
          : '<h3>Start a company first.</h3><p>The Quant Lab works for your company. You do not have one yet.</p>') +
      '<div class="q2-gb"><a class="q2-gogo" href="/company/app/builder">Start a company →</a></div></div>');
  }
  function oops(er) { if (er && er.status === 401) return noCompany(true); toast(er.message); }
  function sources() {
    var ov = S.ov || {};
    return (ov.board || []).map(function (b) { return '<option value="' + esc(b.source) + '">' + esc(b.name) + ' (backtest ' + pct(b.backtest_return_pct) + ')</option>'; }).join('') +
      (ov.my_bots || []).map(function (b) { return '<option value="bot:' + esc(b.instance_id) + '">My bot: ' + esc(b.name) + '</option>'; }).join('');
  }
  function side(p) {
    return '<label class="fl">Bot<select id="' + p + 'src">' + sources() + '</select></label>' +
      '<label class="fl">Stop-loss % (1-20, blank = the bot\'s own)<input id="' + p + 'sl" type="number" min="1" max="20" step="0.5"></label>' +
      '<label class="fl">Take-profit % (5-100)<input id="' + p + 'tp" type="number" min="5" max="100" step="1"></label>' +
      '<label class="fl">Position size % (1-50)<input id="' + p + 'mp" type="number" min="1" max="50" step="1"></label>' +
      '<label class="fl">RSI period (2-200)<input id="' + p + 'rsi" type="number" min="2" max="200" step="1"></label>';
  }
  function readSide(p) {
    var s = {}, cfg = {};
    [['sl', 'stop_loss_pct'], ['tp', 'take_profit_pct'], ['mp', 'max_position_pct']].forEach(function (k) { var v = $(p + k[0]).value; if (v !== '') s[k[1]] = +v; });
    if (Object.keys(s).length) cfg.settings = s;
    if ($(p + 'rsi').value !== '') cfg.indicators = { rsi: { period: +$(p + 'rsi').value } };
    var out = { source: $(p + 'src').value };
    if (Object.keys(cfg).length) out.config = cfg;
    return out;
  }
  function addForm() {
    modal('<div class="mh"><h3 title="The lab clones it on paper, arms it with paper capital and judges it on its own results against your rule. Nothing real is bought or sold.">Add a bot to the lab</h3><button class="xx" data-q="close">×</button></div>' +
      '<div class="form">' + side('qa-') + '<label class="fl"><span><input type="checkbox" id="qa-vs"> Head-to-head against a second bot</span></label><div id="qa-v" hidden>' + side('qb-') + '</div></div>' +
      '<p class="xerr" id="qa-err" hidden></p><div class="mf"><button class="btn" data-q="close">Cancel</button><button class="btn gr" data-q="add-go" title="It starts on the lab\'s next pass">Add bot</button></div>');
    $('qa-vs').addEventListener('change', function () { $('qa-v').hidden = !this.checked; });
  }
  function ruleForm() {
    var r = (S.ov || {}).rule; if (!r) return;
    function f(id, label, v, min, max, step) { return '<label class="fl">' + label + '<input id="qr-' + id + '" type="number" min="' + min + '" max="' + max + '" step="' + step + '" value="' + v + '"></label>'; }
    modal('<div class="mh"><h3 title="A bot goes to the Trading desk only when it meets every line, window after window.">Your rule</h3><button class="xx" data-q="close">×</button></div><div class="form">' +
      f('window_days', 'Window (days)', r.window_days, 1, 30, 1) + f('min_trades', 'Closed trades at least', r.min_trades, 3, 500, 1) +
      f('min_return_pct', 'Return at least (%)', r.min_return_pct, -50, 1000, 0.5) + f('max_drawdown_pct', 'Drawdown under (%)', r.max_drawdown_pct, 1, 100, 1) +
      f('repeats', 'Windows in a row', r.repeats, 1, 5, 1) + f('max_running', 'Paper bots at once', r.max_running, 1, (S.ov.plan && S.ov.plan.trading_cap) || 10, 1) +
      f('capital_usd', 'Paper capital per bot (USDC)', r.capital_usd, 100, 25000, 100) +
      '<label class="fl"><span><input type="checkbox" id="qr-auto"' + (r.auto ? ' checked' : '') + '> The lab proposes the next variation itself</span></label>' +
      '<label class="fl"><span><input type="checkbox" id="qr-t"' + (r.handoff.indexOf('tournament') >= 0 ? ' checked' : '') + '> Hand-off: a seat at a paper tournament table</span></label>' +
      '<label class="fl"><span><input type="checkbox" id="qr-l"' + (r.handoff.indexOf('live') >= 0 ? ' checked' : '') + '> Hand-off: a live copy (paused and unfunded until you fund it)</span></label>' +
      '</div><p class="xerr" id="qr-err" hidden></p><div class="mf"><button class="btn" data-q="close">Cancel</button><button class="btn gr" data-q="rule-go">Save rule</button></div>');
  }
  function configView(id) {
    var x = ((S.ov || {}).experiments || []).filter(function (r) { return r.id === id; })[0];
    if (!x) return;
    var c = x.config || {}, st = c.settings || {}, hb = x.held_back;
    var lines = [['Bot model', (c.models && c.models.length ? c.models.join(', ') : (hb && hb.model) || x.source)],
      ['Market', st.perpetual_markets || (hb && hb.market) || 'the bot\'s own'],
      ['Skills and algorithms', [].concat(c.skills || [], Object.keys(c.indicators || {}).map(function (k) { return k.toUpperCase() + ' ' + JSON.stringify(c.indicators[k]); })).join(', ') || 'the bot\'s own'],
      ['Settings', ['stop_loss_pct', 'take_profit_pct', 'max_position_pct'].filter(function (k) { return st[k] != null; }).map(function (k) { return k.replace(/_pct$/, '').replace(/_/g, '-') + ' ' + st[k] + '%'; }).join(', ') || 'the bot\'s own']];
    modal('<div class="mh"><h3 title="Paper bot. Going live waits for your approval at the Trading desk.">' + esc(x.title) + '</h3><button class="xx" data-q="close">×</button></div><div class="form">' +
      lines.map(function (l) { return '<label class="fl">' + esc(l[0]) + '<span>' + esc(l[1]) + '</span></label>'; }).join('') +
      '</div><div class="mf"><button class="btn" data-q="close">Close</button></div>');
  }
  function memory(offset) {
    return api('GET', '/' + S.cid + '/quant-lab/search/memory?limit=60&offset=' + (offset || 0)).then(function (j) {
      var rows = j.combinations.map(function (x) {
        var t = x.search_period || {}, h = x.held_back;
        return '<tr><td>' + esc(x.model) + '</td><td>' + esc(x.market) + '</td><td>' + esc(x.settings_label || '') + '</td>' +
          '<td>' + pct(t.return_pct) + ' (' + (t.trades == null ? '—' : t.trades) + ')</td><td>' + (h ? pct(h.return_pct) + ' (' + h.trades + ')' : 'not checked') + '</td><td>' + esc(String(x.verdict || '').replace('_', ' ')) + '</td></tr>';
      }).join('');
      modal('<div class="mh"><h3 title="Model, market, settings, return on the search period (trades), return on the held-back period (trades), verdict. Newest first.">What was tested (' + num(j.total) + ')</h3><button class="xx" data-q="close">×</button></div>' +
        '<div style="max-height:55vh;overflow:auto"><table style="width:100%;font-size:12px"><tr><th align="left">Model</th><th align="left">Market</th><th align="left">Settings</th><th align="left">Search period</th><th align="left">Held-back</th><th align="left">Verdict</th></tr>' + rows + '</table></div>' +
        '<div class="mf">' + (offset ? '<button class="btn" data-s="page" data-o="' + Math.max(0, offset - 60) + '">Newer</button>' : '') + (offset + 60 < j.total ? '<button class="btn" data-s="page" data-o="' + (offset + 60) + '">Older</button>' : '') + '<button class="btn" data-q="close">Close</button></div>');
    }, oops);
  }
  function startSearch(b) {
    if (MODE === 'sim') { toast('Switch to Real to run a search.'); return; }
    if (active(LIVE)) return;
    if (!S.cid) return noCompany();
    b.disabled = true;
    api('POST', '/' + S.cid + '/quant-lab/search').then(function (j) {
      toast(j.already_running ? 'A search is already running.' : 'Search started.');
      if (j.search) { if (S.st) S.st.search = j.search; if (active(j.search)) { LIVE = j.search; paint(); } }
    }, function (er) { b.disabled = false; oops(er); rail(); });
  }

  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-mode]'); if (b) return setMode(b.getAttribute('data-mode'));
    if (e.target.closest('[data-pp]')) return pause(!paused);
    var go = e.target.closest('[data-go]'); if (go) return startSearch(go);
    var s = e.target.closest('[data-st]'); if (s) return goStage(+s.getAttribute('data-st'));
    var rb = e.target.closest('[data-run]');
    if (rb) { var rv = rb.getAttribute('data-run'); SELECTED = rv === 'newest' ? null : +rv; apply(); return; }
    var sb = e.target.closest('[data-s]');
    if (sb && !S.cid) return noCompany();
    if (sb) { var a = sb.getAttribute('data-s'); if (a === 'memory') return memory(0); if (a === 'page') return memory(+sb.getAttribute('data-o')); }
    var qb = e.target.closest('[data-q]'); if (!qb) return;
    var q = qb.getAttribute('data-q'), id = qb.getAttribute('data-id');
    if (q === 'close') return close();
    if (!S.cid) return noCompany();
    if (!S.ov) return;
    if (q === 'config') return configView(+id);
    if (q === 'add') return addForm();
    if (q === 'rule') return ruleForm();
    if (q === 'add-go') {
      var body = readSide('qa-');
      if ($('qa-vs').checked) body.versus = readSide('qb-');
      qb.disabled = true;
      return api('POST', '/' + S.cid + '/quant-lab/experiments', body).then(function () { close(); toast('Added. It starts on the lab\'s next pass.'); loadAll(); },
        function (er) { qb.disabled = false; fail('qa-err', er); });
    }
    if (q === 'rule-go') {
      var r = {};
      ['window_days', 'min_trades', 'min_return_pct', 'max_drawdown_pct', 'repeats', 'max_running', 'capital_usd'].forEach(function (k) { r[k] = +$('qr-' + k).value; });
      r.auto = $('qr-auto').checked;
      r.handoff = [].concat($('qr-t').checked ? ['tournament'] : [], $('qr-l').checked ? ['live'] : []);
      return api('PUT', '/' + S.cid + '/quant-lab/rule', r).then(function () { close(); toast('Rule saved.'); loadAll(); }, function (er) { fail('qr-err', er); });
    }
    if (q === 'remove') {
      return api('DELETE', '/' + S.cid + '/quant-lab/experiments/' + id).then(function () { toast('Removed from the lab.'); loadAll(); }, oops);
    }
    if (q === 'pause' || q === 'run' || q === 'vary') {
      qb.disabled = true;
      return api('POST', '/' + S.cid + '/quant-lab/experiments/' + id + '/' + q).then(function () {
        toast(q === 'pause' ? 'Paused.' : q === 'run' ? 'It runs again from the next pass.' : 'The next variation is queued.'); loadAll();
      }, function (er) { qb.disabled = false; oops(er); });
    }
  });
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') close();
    if (e.target.closest && e.target.closest('input, textarea, select')) return;
    if (e.key === ' ') { e.preventDefault(); pause(!paused); }
    else if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') { pause(true); goStage(stageAt(now())[0] + (e.key === 'ArrowRight' ? 1 : -1)); }
  });
  window.addEventListener('resize', size);

  // ---------------------------------------------------------------- start
  size();
  REAL = realModel();
  MODE = /[?&]mode=sim/.test(location.search) ? 'sim' : 'real';
  setLab('replay', '');
  paint();
  requestAnimationFrame(frame);
  window.QL.ready = true;
  // the company id only (GET /mine/id), not the whole office (GET /office took ~2.6 s before anything else could start)
  api('GET', '/mine/id').then(function (o) {
    S.cid = o.id; connect(); return loadAll().then(function () {
      var m = /[?&]bot=(\d+)/.exec(location.search); if (m && S.ov) configView(+m[1]);
    });
  }, function (er) {
    S.signedOut = !!(er && er.status === 401);
    S.loaded = true; paint();
    $('bots').innerHTML = '<div class="q2-quiet">Open your company to see its lab.</div>';
  });
})();
