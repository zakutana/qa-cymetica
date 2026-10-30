/* Quant Lab v2: the experiments page for degens. Two modes:
 *  real  our company's last search, exactly as their API returned it (data.js): 16 rules x 12 markets x 9 settings,
 *        5 blind-tested, 0 cleared the bar, no bot.
 *  sim   how ET-33142 is meant to work: the search unit is a whole bot setup (a model or a Named Combination, plus
 *        skills), and a winner starts as a paper bot with exactly that setup. Every number comes from SIM below.
 * Names, icons and limits are theirs: /adm (models, combinations), /skills-n-tools (skills), their search API (method,
 * bar). The page sends nothing anywhere. */
(function () {
  'use strict';
  var D = window.QL_DATA;
  function $(id) { return document.getElementById(id); }
  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"']/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]; }); }
  function pct(v) { return v == null ? '—' : (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(2) + '%'; }
  function num(v) { return Number(v).toLocaleString('en-US'); }

  // ---- their catalogue: icons and names as /adm and /skills-n-tools show them
  var MODELS = {
    helix: ['🧬', 'HELIX'], prion: ['🧩', 'PRION'], enzyme: ['⚗️', 'ENZYME'], synapse: ['🧠', 'SYNAPSE'], cortex: ['♞', 'CORTEX'],
    telomere: ['⏳', 'TELOMERE'], immune: ['🛡️', 'IMMUNE'], circadian: ['⏰', 'CIRCADIAN'], mitosis: ['🦠', 'MITOSIS'], crispr: ['🎯', 'CRISPR'],
    stockbull_blue: ['📊', 'StockBot Blue'], stockbear_red: ['📊', 'StockBot Red'], cryptobull_blue: ['📊', 'CryptoBull Blue'],
    cryptobull_red: ['📊', 'CryptoBull Red'], hybrid2_blue: ['📊', 'Hybrid 2 Blue'], hybrid2_red: ['📊', 'Hybrid 2 Red']
  };
  var COMBOS = { central_dogma: ['🧬', 'Central Dogma', 'HELIX + ENZYME + CRISPR'], immune_response: ['🛡️', 'Immune Response', 'IMMUNE + CORTEX + CIRCADIAN'] };
  var SKILLS = {
    macd: ['📈', 'MACD Crossover'], rsi: ['⚡', 'RSI Momentum'], boll: ['🔄', 'Bollinger Squeeze'], volt: ['⚡', 'Volume Threshold'],
    ema: ['📈', 'EMA Trend'], volf: ['🔍', 'Volatility Filter'], atr: ['〰️', 'ATR Volatility'], ichi: ['☁️', 'Ichimoku Cloud']
  };
  var RULES = Object.keys(MODELS);   // the 16 rules the search replays today: 10 biomimetic + 6 Backtested Strategy

  // coin logos: CoinGecko's, the source their own /perpetual pages load BTC and ETH from
  var COIN = { BTC: '1/large/bitcoin.png', ETH: '279/large/ethereum.png', SOL: '4128/large/solana.png', BNB: '825/large/bnb-icon2_2x.png',
    XRP: '44/large/xrp-symbol-white-128.png', ADA: '975/large/cardano.png', DOGE: '5/large/dogecoin.png', AVAX: '12559/large/Avalanche_Circle_RedWhite_Trans.png',
    LINK: '877/large/chainlink-new-logo.png', LTC: '2/large/litecoin.png', DOT: '12171/large/polkadot.png', ATOM: '1481/large/cosmos_hub.png' };
  function coinUrl(s) { return COIN[s] ? 'https://assets.coingecko.com/coins/images/' + COIN[s] : ''; }
  function coinTag(s) { return '<span class="q2-coin"><img src="' + coinUrl(s) + '" alt=""></span><b class="q2-ct">' + esc(s) + '</b>'; }

  // the agent: our own picture (the Quest steps page's, outbox/quest-steps/pics/agent.webp), cropped to the scene and the head
  var AGENT = 'pics/agent.webp', HEAD = 'pics/agent-head.webp';
  function headImg(cls) { return '<img class="' + cls + '" src="' + HEAD + '" alt="">'; }

  function setupKey(s) { return [s.base].concat(s.skills).join('+'); }
  function baseOf(s) { return s.kind === 'combo' ? COMBOS[s.base] : MODELS[s.base]; }
  function setupChips(s, small) {
    var b = baseOf(s), out = '<span class="q2-chip ' + (s.kind === 'combo' ? 'q2-cc' : 'q2-cm') + '" title="' + esc(s.kind === 'combo' ? 'Named Combination: ' + b[2] : s.kind === 'rule' && !/^[a-z]+$/.test(s.base) ? 'Backtested Strategy rule' : 'Model') + '">' + b[0] + ' ' + esc(b[1]) + '</span>';
    s.skills.forEach(function (k) { out += '<span class="q2-chip q2-cs" title="Skill">' + SKILLS[k][0] + (small ? '' : ' ' + esc(SKILLS[k][1])) + '</span>'; });
    return '<div class="q2-chips">' + out + '</div>';
  }
  function setupText(s) {
    var b = baseOf(s);
    return b[0] + ' ' + b[1] + s.skills.map(function (k) { return ' + ' + SKILLS[k][0]; }).join('');
  }

  // ---- one seeded generator for every random-looking thing
  function rng(seed) { return function () { seed |= 0; seed = seed + 0x6D2B79F5 | 0; var t = Math.imul(seed ^ seed >>> 15, 1 | seed); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
  // inverse normal (Acklam): their bar is a one-sided 5% test split over every combination tried (z = 4.0213 at 1,728)
  function invNorm(p) {
    var a = [-39.6968302866538, 220.946098424521, -275.928510446969, 138.357751867269, -30.6647980661472, 2.50662827745924],
      b = [-54.4760987982241, 161.585836858041, -155.698979859887, 66.8013118877197, -13.2806815528857],
      c = [-0.00778489400243029, -0.322396458041136, -2.40075827716184, -2.54973253934373, 4.37466414146497, 2.93816398269878],
      d = [0.00778469570904146, 0.32246712907004, 2.445134137143, 3.75440866190742], q, r;
    if (p > 1 - 0.02425) { q = Math.sqrt(-2 * Math.log(1 - p)); return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1); }
    q = p - 0.5; r = q * q;
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1);
  }

  // ---- REAL: our company's last finished search, as the API returned it
  function realModel() {
    var done = D.searches.filter(function (s) { return s.status === 'done'; })[0], sm = done.summary;
    var setups = RULES.map(function (k) { return { kind: 'rule', base: k, skills: [] }; });
    var cands = D.held_back.map(function (x) {
      var s = { kind: 'rule', base: x.model, skills: [] };
      return { setup: s, setup_key: setupKey(s), model: x.model, market: x.market, settings: x.settings_label, entry: x.entry_threshold,
        search: x.search.return_pct, held: x.held.return_pct, trades: x.held.trades, bar: x.bar.bar_pct, won: x.verdict === 'kept', verdict: x.verdict };
    });
    return { mode: 'real', setups: setups, markets: D.markets, settings: D.combinations_tried / (D.models * D.markets.length), tried: D.combinations_tried,
      searches: D.searches.length, failed: D.searches.filter(function (s) { return s.status === 'failed'; }).length,
      checked: sm.held_back_checked, won: sm.won, bots: D.experiments.length, z: D.held_back.length ? D.held_back[0].bar.z : invNorm(1 - 0.05 / D.combinations_tried),
      candidates: cands, label: 'search #' + done.id + ' · ' + new Date(done.finished_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }) + ' · ' + num(D.combinations_tried) + ' tried',
      failedWhy: D.searches.filter(function (s) { return s.status === 'failed'; }).map(function (s) { return '#' + s.id + ' ' + (s.error || '').split(':')[0]; }).join(' · ') };
  }

  // ---- SIM: ET-33142, one small model. Setups = today's 16 rules (the simplest case) + models / combinations with skills.
  function simModel() {
    var composed = [
      { kind: 'combo', base: 'central_dogma', skills: ['macd', 'volf'] }, { kind: 'combo', base: 'central_dogma', skills: ['ema'] },
      { kind: 'combo', base: 'immune_response', skills: ['rsi'] }, { kind: 'combo', base: 'immune_response', skills: ['atr', 'volt'] },
      { kind: 'model', base: 'helix', skills: ['ema', 'volf'] }, { kind: 'model', base: 'crispr', skills: ['boll', 'volt'] },
      { kind: 'model', base: 'enzyme', skills: ['rsi', 'boll'] }, { kind: 'model', base: 'cortex', skills: ['ichi'] }];
    var setups = RULES.map(function (k) { return { kind: 'rule', base: k, skills: [] }; }).concat(composed);
    var settings = 27, tried = setups.length * D.markets.length * settings, z = invNorm(1 - 0.05 / tried);
    // the five best on the search period; sd is each one's spread on the blind period, so its bar is z x sd (never below 1%)
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
    return { mode: 'sim', setups: setups, markets: D.markets, settings: settings, tried: tried, searches: 1, failed: 0, checked: cands.length,
      won: winners.length, bots: bots.length, botList: bots, z: z, candidates: cands, label: 'simulated · ' + num(tried) + ' tried' };
  }

  var M = null, SIM = simModel(), REAL = realModel();
  window.QL = { ready: false, mode: null, sim: null };

  // ---------------------------------------------------------------- DOM
  function tile(k, ic, n, l, cls, tip) {
    return '<div class="q2-tile ' + (cls || '') + (n === 0 ? ' q2-zero' : '') + '" title="' + esc(tip) + '"><span class="q2-ic">' + (ic === 'head' ? headImg('q2-hd') : ic) + '</span><span class="q2-n" data-k="' + k + '">' + num(n) + '</span><span class="q2-l">' + l + '</span></div>';
  }
  function renderScore() {
    $('score').innerHTML =
      tile('searches', '🔎', M.searches, 'Searches', '', M.mode === 'real' ? 'Searches run: daily, or when you ask' : 'One search') +
      tile('failed', '⚠️', M.failed, 'Failed', M.failed ? 'q2-down' : '', M.failed ? M.failedWhy : 'None failed') +
      tile('tried', '🧮', M.tried, 'Tried', 'q2-cy', M.setups.length + ' setups × ' + M.markets.length + ' markets × ' + M.settings + ' settings, each replayed on past prices') +
      tile('checked', '🙈', M.checked, 'Blind-tested', '', 'The best few, re-run on the later period the search never saw') +
      tile('won', '🏁', M.won, 'Beat the bar', M.won ? 'q2-up' : 'q2-down', 'Won on the blind period by more than the bar, which rises with every try') +
      tile('bots', 'head', M.bots, 'Agents found', M.bots ? 'q2-up' : '', M.mode === 'real' ? 'Paper bots started from winners' : 'Paper bots started with exactly the winning setup');
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
    $('toplabel').textContent = M.label + ' · z ' + M.z.toFixed(2);
    var lo = Math.min(-15, Math.min.apply(null, M.candidates.map(function (c) { return c.held; })) - 2), hi = Math.max(15, Math.max.apply(null, M.candidates.map(function (c) { return c.bar; })) + 3);
    $('top').innerHTML = M.candidates.map(function (c, i) {
      return '<div class="top-row ' + (c.won ? 'q2-won' : '') + '" data-model="' + esc(c.model) + '" data-market="' + esc(c.market) + '" data-search="' + c.search + '" data-held="' + c.held + '" data-bar="' + c.bar + '" data-verdict="' + esc(c.verdict) + '">' +
        '<span class="q2-rk">' + (i + 1) + '</span>' + setupChips(c.setup) +
        '<span class="q2-cw">' + coinTag(c.market) + '</span>' +
        '<div class="q2-set"><b>' + esc(c.settings.replace(' / ', ' · ')) + '</b><br>entry ' + esc(c.entry.replace('_', ' ')) + '</div>' +
        '<div class="q2-move" title="Search period → blind period, ' + c.trades + ' trades"><span class="q2-ma">' + pct(c.search) + '</span><span class="q2-mar">→</span><span class="q2-mb ' + (c.held < 0 ? 'q2-down' : 'q2-up') + '">' + pct(c.held) + '</span></div>' +
        gauge(c, lo, hi) + '<span class="q2-v ' + (c.won ? 'q2-won' : 'q2-lost') + '" title="' + (c.won ? 'Cleared the bar' : 'Thrown out') + '">' + (c.won ? '✓' : '✗') + '</span></div>';
    }).join('');
  }
  function spark(pts) {
    var w = 400, h = 64, lo = Math.min.apply(null, pts), hi = Math.max.apply(null, pts), rg = (hi - lo) || 1;
    var d = pts.map(function (v, i) { return (i ? 'L' : 'M') + (i / (pts.length - 1) * w).toFixed(1) + ' ' + (h - 4 - (v - lo) / rg * (h - 8)).toFixed(1); }).join(' ');
    var up = pts[pts.length - 1] >= 0;
    return '<svg viewBox="0 0 ' + w + ' ' + h + '" preserveAspectRatio="none"><path d="' + d + ' L' + w + ' ' + h + ' L0 ' + h + 'Z" fill="' + (up ? 'rgba(0,255,136,.12)' : 'rgba(255,68,68,.12)') + '"/><path d="' + d + '" fill="none" stroke="' + (up ? '#00ff88' : '#ff4444') + '" stroke-width="2"/></svg>';
  }
  function renderBots() {
    var r = D.rule;
    $('rule').innerHTML = '<span title="' + esc(D.rule_text) + '">🔁 <b>' + r.min_trades + '+</b> trades</span><span title="' + esc(D.rule_text) + '">📈 <b>+' + r.min_return_pct + '%</b></span>' +
      '<span title="' + esc(D.rule_text) + '">🛡️ DD <b>&lt;' + r.max_drawdown_pct + '%</b></span><span title="' + esc(D.rule_text) + '">🗓️ <b>' + r.window_days + 'd × ' + r.repeats + '</b></span>' +
      '<span title="A bot that meets the rule goes to the Trading desk for your approval">🎯 → desk</span>';
    if (M.mode === 'sim') {
      $('bots').innerHTML = M.botList.map(function (b) {
        var c = b.cand;
        return '<div class="q2-bot" data-setup="' + esc(c.setup_key) + '"><div class="q2-bt"><span class="q2-av">' + headImg('') + '</span><div><div class="q2-nm">' + esc(baseOf(c.setup)[1]) + ' · ' + esc(c.market) + ' <span class="q2-coin q2-cs2"><img src="' + coinUrl(c.market) + '" alt=""></span></div>' +
          '<div class="q2-bst"><i></i>PROFITABLE · PAPER · RUNNING</div></div><span class="q2-ret ' + (b.ret >= 0 ? 'q2-up' : 'q2-down') + '">' + pct(b.ret) + '</span></div>' +
          '<div class="q2-same" title="The bot trades the setup that won, nothing mapped or swapped">✓ SAME SETUP AS THE WINNER</div>' + setupChips(c.setup) +
          spark(b.pts) + '<div class="q2-acts"><button title="Pause">⏸</button><button title="Vary: the lab proposes the next variation">⟳</button><button title="Remove">✕</button>' +
          '<span class="q2-kp"><span><b>' + b.trades + '</b> trades</span><span>DD <b>' + b.dd.toFixed(1) + '%</b></span><span><b>' + esc(c.settings.replace(' / ', ' · ')) + '</b></span></span></div></div>';
      }).join('');
    } else if (D.experiments.length) {
      $('bots').innerHTML = D.experiments.map(function (x) {
        return '<div class="q2-bot" data-setup="' + esc(x.title) + '"><div class="q2-bt"><span class="q2-av">' + headImg('') + '</span><div><div class="q2-nm">' + esc(x.title) + '</div><div class="q2-bst"><i></i>' + esc(String(x.status).toUpperCase()) + '</div></div>' +
          '<span class="q2-ret ' + ((x.return_pct || 0) >= 0 ? 'q2-up' : 'q2-down') + '">' + pct(x.return_pct) + '</span></div></div>';
      }).join('');
    } else {
      $('bots').innerHTML = '<div class="q2-empty">' + headImg('q2-ebot') + '<span class="q2-big">0</span><span>No profitable agent yet. Winners land here as paper bots.</span></div>';
    }
  }
  function renderCaps() {
    var SZ = { build_small: ['S', 'Small build'], build_medium: ['M', 'Medium build'], build_large: ['L', 'Large build'], not_possible: ['✗', 'Not possible'] };
    var can = D.can_tune.map(function (t) { return '<li title="' + esc(t) + '">✓ ' + esc(t.split(':')[0]) + '</li>'; });
    if (M.mode === 'sim') can = can.concat(['Skills', 'Named Combinations', 'Winner → bot, same setup'].map(function (t) { return '<li title="ET-33142">✓ ' + esc(t) + ' <span class="q2-sz">NEW</span></li>'; }));
    $('caps').innerHTML = '<div><h3 class="q2-ok">CAN TUNE</h3><ul>' + can.join('') + '</ul></div>' +
      '<div><h3 class="q2-no">CAN\'T YET</h3><ul>' + D.cannot_tune.map(function (c) {
        var s = SZ[c.size] || ['?', c.size];
        return '<li><span class="q2-sz ' + (c.size === 'not_possible' ? 'q2-x' : '') + '" title="' + s[1] + '">' + s[0] + '</span>' + esc(c.what.replace(/\s*\(.*\)$/, '')) + '</li>';
      }).join('') + '</ul></div>';
    $('capsbtn').title = D.does_not_do.join(' ');
    $('memn').textContent = num(M.tried);
    $('paper').title = D.cost;
  }

  // ---------------------------------------------------------------- the lab's state: what the reactor shows
  //  replay  no search running: the last finished search, played over and over. When the newest ones failed, the badge
  //          says so in red (how many, then which day is playing); a failure is not a stage, so it has no screen
  //          (the operator, 2026-10-30: "TO NECHAPU TU FAILED ZALOZKU").
  //  live    a search running: the fields their WebSocket sends while it runs (done_jobs, total_jobs, percent, eta_seconds).
  //          In this mock only Search now starts it, and it is a preview: a timer at #3's real pace, nothing is sent.
  var byNew = D.searches.slice().sort(function (a, b) { return a.requested_at < b.requested_at ? 1 : -1; });
  var FAILS = [];   // the failed searches in a row, newest first
  for (var fi = 0; fi < byNew.length && byNew[fi].status === 'failed'; fi++) FAILS.push(byNew[fi]);
  var LAST_GOOD = byNew.filter(function (s) { return s.status === 'done'; })[0];
  var PACE = (Date.parse(LAST_GOOD.finished_at) - Date.parse(LAST_GOOD.requested_at)) / 1000 / LAST_GOOD.total_jobs;   // seconds a combination, #3's
  function day(iso) { return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }).toUpperCase(); }
  function errLabel(e) { return /closed the connection|OperationalError/.test(e || '') ? 'database connection lost' : String(e || 'no reason given').split(':')[0]; }   // never the raw text (#232)
  var DOWN = '';   // the badge's tooltip while the newest searches have failed, '' when they have not
  function downWhy() {
    return 'The last ' + FAILS.length + ' searches failed (' + FAILS.slice().reverse().map(function (f) { return '#' + f.id + ' ' + day(f.requested_at); }).join(', ') + '): ' +
      errLabel(FAILS[0].error) + '. Nothing has been tested since ' + day(LAST_GOOD.finished_at) + ', so this replays that search.';
  }
  function dur(s) { return s < 90 ? s + ' S' : Math.round(s / 60) + ' MIN'; }   // their page's own rounding
  function feed(p) {   // a running search as their WebSocket reports it, here from a timer
    var f = seg(p, 0, 0.9), total = M.tried;
    return { status: 'running', done_jobs: Math.round(total * f), total_jobs: total, percent: Math.floor(f * 100), eta_seconds: Math.round((1 - f) * total * PACE) };
  }

  // ---------------------------------------------------------------- the reactor
  var BASE = [['build', '🧩', 'BUILD', 3.2, 0.97], ['blast', '💥', 'BLAST', 4.4, 0.97], ['blind', '🙈', 'BLIND', 3.4, 0.97], ['bar', '🚧', 'THE BAR', 5.6, 0.995], ['bot', '🏆', 'FOUND', 7.0, 0.97]];
  // a stage: key, icon, word, seconds, where a paused stage stands (its finished picture)
  function stagesFor(s) {
    var st = BASE.map(function (x) { return x.slice(); });
    if (s === 'live') st[1][3] = 12;   // the search itself is the long part
    return st;
  }
  var LAB = 'replay', RUN = '', STAGES = BASE, TOTAL = 0;
  var cv = $('rx'), ctx = cv.getContext('2d'), W = 0, H = 0, DPR = 1, t0 = performance.now(), offset = 0, parts = [], shake = 0, fired = {}, cells = null;
  var paused = false, held = 0;   // paused: the clock stands at `held`
  var C ={ bg: '#06090f', navy: '#0d1520', navy2: '#111a28', line: '#16233a', line3: '#1e3050', text: '#e6edf7', dim: '#7f93ad', dim3: '#3a4d68', cyan: '#00cfff', green: '#00ff88', red: '#ff4444', blue: '#3b82f6' };
  var MONO = "'JetBrains Mono', monospace", BLACK = "'Archivo Black', sans-serif";

  function size() { DPR = Math.min(2, window.devicePixelRatio || 1); W = cv.clientWidth; H = cv.clientHeight; cv.width = W * DPR; cv.height = H * DPR; }
  function rail() {
    $('rail').innerHTML = '<button class="q2-pp' + (paused ? ' q2-on' : '') + '" data-pp aria-label="' + (paused ? 'Play' : 'Pause') + '">' + (paused ? '▶' : '⏸') + '</button>' +
      STAGES.map(function (s, i) { return '<button data-st="' + i + '"><span class="q2-e">' + s[1] + '</span><span class="q2-t">' + s[2] + '</span><i></i></button>'; }).join('') +
      '<span class="q2-lab" id="lab"></span><button class="q2-go" data-go title="' + esc(D.cost) + '">⚡ SEARCH NOW</button>';
  }
  function setLab(s, run) {   // what the reactor shows; it starts from its first stage
    LAB = s; RUN = run; STAGES = stagesFor(s); TOTAL = STAGES.reduce(function (a, x) { return a + x[3]; }, 0);
    fired = {}; parts = []; rings = []; flash = 0; lastStage = -1; labText = null;
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
    i = (i + STAGES.length) % STAGES.length; fired = {}; parts = []; lastStage = -1;
    if (paused) held = startOf(i) + STAGES[i][3] * STAGES[i][4];
    else { t0 = performance.now(); offset = startOf(i) + 0.001; }
  }
  // the badge beside the stages: which search this is, or that one is running; red when the newest ones failed
  var labText = null;
  function badge(si, p) {
    var k = STAGES[si][0], s, cls;
    if (LAB === 'live') {
      var f = k === 'blast' ? feed(p) : null, pc = f ? f.percent : si < 1 ? 0 : 100;
      s = '● LIVE · PREVIEW · NOTHING SENT'; cls = 'q2-lv';
      var go = document.querySelector('[data-go]'), gt = '● RUNNING ' + pc + '%'; if (go && go.textContent !== gt) { go.disabled = true; go.textContent = gt; }
    } else if (DOWN) { s = '⚠️ LAST ' + FAILS.length + ' FAILED · ↻ REPLAY · ' + RUN; cls = 'q2-fl'; }
    else { s = '↻ REPLAY · ' + RUN; cls = ''; }
    if (s === labText) return;
    labText = s; var el = $('lab'); el.textContent = s; el.className = 'q2-lab ' + cls; el.title = LAB === 'live' ? '' : DOWN;
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
  var EYES = [[502 / 1000, 265 / 1016], [574 / 1000, 260 / 1016]];   // where the agent's eyes sit in pics/agent.webp
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
    // narrow screens: the assembly on top, the grid under it, instead of side by side
    var narrow = W < 1300, n = M.setups.length, gx = narrow ? 30 : W * 0.47, cols = narrow ? 4 : M.mode === 'sim' ? 3 : 4, rows = Math.ceil(n / cols),
      cw = (W - gx - 30) / cols, chh = Math.min(42, (H - (narrow ? 180 : 90)) / rows),
      gy = narrow ? 150 : Math.max(60, (H - rows * chh) / 2);   // wide: the grid stands level with the number beside it
    if (M.mode === 'sim') {
      var f = M.candidates[0].setup, b = baseOf(f), pa = ease(seg(p, 0, 0.42)), cx = W * (narrow ? 0.04 : 0.07), cy = narrow ? 80 : H * 0.46;
      var parts3 = [b[0] + ' ' + b[1]].concat(f.skills.map(function (k) { return SKILLS[k][0] + ' ' + SKILLS[k][1]; }));
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
    var r = rng(M.mode === 'sim' ? 33142 : 1728), v = [];
    for (var i = 0; i < M.setups.length; i++) { v.push([]); for (var j = 0; j < M.markets.length; j++) v[i].push((r() + r() + r() - 1.6) * 14); }
    var hot = M.candidates.map(function (c) {
      var i = M.setups.map(setupKey).indexOf(c.setup_key), j = M.markets.indexOf(c.market); if (i >= 0 && j >= 0) v[i][j] = c.search; return [i, j];
    });
    cells = { mode: M.mode, v: v, hot: hot }; return cells;
  }
  function drawBlast(p, t) {
    // the grid fills the screen's height and runs to the counter (the operator, 2026-10-30: "nevyuziva celou plochu")
    var cl = cellsFor(), n = M.setups.length, m = M.markets.length, x0 = 200, y0 = 70, mw = W - x0 - 330, ch = (H - y0 - 20) / n, cw = mw / m, fs = ch >= 24 ? 13 : 11;
    M.markets.forEach(function (s, j) { coin(s, x0 + j * cw + cw / 2, 26, 13, true); });
    // live: the cells follow the feed's done_jobs, evenly, as a running search does; a replay eases through it
    var live = LAB === 'live', fd = live ? feed(p) : null, prog = live ? fd.done_jobs / fd.total_jobs : ease(seg(p, 0, 0.82)), hotAt = live ? 0.92 : 0.84;
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
        if (idx === lit) { ctx.fillStyle = '#ffffff'; ctx.shadowColor = C.cyan; ctx.shadowBlur = 24; ctx.fillRect(x, y, cw, ch); ctx.shadowBlur = 0; if (Math.random() < 0.5) burst(x + cw / 2, y + ch / 2, C.cyan, 2, 4); }
      }
    }
    if (lit < total) { var bi = Math.floor(lit / m); ctx.fillStyle = 'rgba(0, 207, 255, .12)'; ctx.fillRect(x0, y0 + bi * ch, mw, ch); }
    if (p > hotAt) {
      var pulse = 0.5 + 0.5 * Math.sin(p * 60);
      cl.hot.forEach(function (h, r) {
        if (h[0] < 0) return; var x = x0 + h[1] * cw, y = y0 + h[0] * ch;
        ctx.strokeStyle = C.green; ctx.lineWidth = 2; ctx.shadowColor = C.green; ctx.shadowBlur = 10 + 14 * pulse; ctx.strokeRect(x - 1, y - 1, cw + 2, ch + 2); ctx.shadowBlur = 0;
        txt(String(r + 1), x + cw + 6, y + ch / 2, '400 13px ' + BLACK, C.green, 'left');
      });
      once('top5', function () { shake = 6; });
    }
    if (live) {   // the feed's numbers, as their page words them: done of total, percent, time left
      txt('● LIVE', W - 296, H * 0.36 - 64, '400 22px ' + BLACK, 'rgba(0, 255, 136, ' + (0.55 + 0.45 * Math.sin(t * 6)) + ')', 'left', 14);
      bigCounter(fd.done_jobs, 'OF ' + num(fd.total_jobs) + ' · ' + fd.percent + '%', null, W - 300, H * 0.36, C.green);
      txt(fd.eta_seconds ? 'LEFT ≈ ' + dur(fd.eta_seconds) : 'ALL REPLAYED', W - 296, H * 0.36 + 72, '700 15px ' + MONO, C.text, 'left');
      var bw = 270, by = H * 0.36 + 98;
      rr(W - 296, by - 5, bw, 10, 5); ctx.fillStyle = C.navy2; ctx.fill();
      rr(W - 296, by - 5, Math.max(10, bw * prog), 10, 5); ctx.fillStyle = C.green; ctx.shadowColor = C.green; ctx.shadowBlur = 14; ctx.fill(); ctx.shadowBlur = 0;
    } else {
      bigCounter(Math.round(prog * M.tried), 'TRIED', M.setups.length + ' × ' + m + ' × ' + k, W - 300, H * 0.36, C.cyan);
      txt('ON PAST PRICES', W - 296, H * 0.36 + 98, '700 13px ' + MONO, C.dim3, 'left');
    }
  }

  // 3 BLIND: the best few rise; the last part of history is walled off from the search
  function method() { var m = /(\d+)%\s+of\s+(\d+)\s+days/.exec(D.method.search_period) || [0, 60, 90]; return { seen: +m[1], days: +m[2] }; }
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
    var n = M.candidates.length, top = 104, bot = H - 50, gap = 26, w = (W - 140 - gap * (n - 1)) / n;
    var hi = Math.max(36, Math.max.apply(null, M.candidates.map(function (c) { return Math.max(c.search, c.bar); })) + 4);
    var lo = Math.min(-16, Math.min.apply(null, M.candidates.map(function (c) { return c.held; })) - 3);
    function Y(v) { return top + (hi - v) / (hi - lo) * (bot - top); }
    txt('THE BAR RISES WITH EVERY TRY', 30, 24, '700 14px ' + MONO, C.dim, 'left');
    txt('z ' + M.z.toFixed(2) + ' · ' + num(M.tried) + ' TRIES', W - 30, 24, '700 14px ' + MONO, C.green, 'right', 8);
    ctx.strokeStyle = C.dim3; ctx.lineWidth = 1; ctx.setLineDash([4, 6]); ctx.beginPath(); ctx.moveTo(70, Y(0)); ctx.lineTo(W - 30, Y(0)); ctx.stroke(); ctx.setLineDash([]);
    txt('0%', 60, Y(0), '700 12px ' + MONO, C.dim, 'right');
    M.candidates.forEach(function (c, i) {
      var x = 90 + i * (w + gap), cx = x + w / 2, st = 0.08 + i * 0.16, run = ease(seg(p, st, st + 0.12)), doneP = p >= st + 0.12;
      txt(setupText(c.setup).split(' + ')[0], x, top - 40, '700 13px ' + MONO, C.text, 'left');
      coin(c.market, x + w - 16, top - 40, 14);
      // the search-period result, a ghost
      ctx.strokeStyle = 'rgba(0, 207, 255, .45)'; ctx.setLineDash([3, 4]); ctx.strokeRect(x + w * 0.1, Y(c.search), w * 0.28, Y(0) - Y(c.search)); ctx.setLineDash([]);
      txt(pct(c.search), x + w * 0.24, Y(c.search) - 12, '700 12px ' + MONO, C.cyan, 'center');
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
    if (!M.won) {   // no winner: the agent stays dark
      var a = ease(seg(p, 0, 0.25)), jit = Math.random() < 0.06 ? (Math.random() - 0.5) * 12 : 0;
      var dark = agentMasked();
      if (dark) { ctx.save(); ctx.globalAlpha = a; ctx.filter = 'grayscale(1) brightness(.35)'; ctx.drawImage(dark, g.x + jit, g.y, g.w, g.h); ctx.restore(); }
      txt('0', W * 0.47, H * 0.42, '400 150px ' + BLACK, C.red, 'center', 30);
      slam('NO WINNER', W * 0.56, H * 0.36, 44, 0.1, p);
      slam('NO PROFITABLE AGENT', W * 0.56, H * 0.36 + 56, 44, 0.18, p);
      txt(M.checked + ' BLIND-TESTED · ' + M.checked + ' THROWN OUT', W * 0.56, H * 0.36 + 112, '700 15px ' + MONO, C.dim, 'left');
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
    var cxp = px0; [baseOf(c.setup)[0] + ' ' + baseOf(c.setup)[1]].concat(c.setup.skills.map(function (k) { return SKILLS[k][0] + ' ' + SKILLS[k][1]; })).forEach(function (s, i) { cxp += chip(s, cxp, 238, i ? C.blue : C.green, 14) + 8; });
    txt('✓ SAME SETUP', cxp + 8, 238, '700 14px ' + MONO, C.green, 'left', 8);
    var drawn = Math.max(2, Math.floor(ease(seg(p, 0.58, 0.96)) * b.pts.length)), lo = Math.min.apply(null, b.pts), hi = Math.max.apply(null, b.pts), ex = px0, ew = pw - 200, ey = 278, eh = H - ey - 56;
    rr(ex - 10, ey - 10, pw + 10, eh + 20, 14); ctx.fillStyle = 'rgba(13, 21, 32, .85)'; ctx.fill(); ctx.strokeStyle = 'rgba(0, 255, 136, .35)'; ctx.lineWidth = 1.5; ctx.stroke();
    ctx.beginPath();
    for (var i = 0; i < drawn; i++) { var qx = ex + 10 + i / (b.pts.length - 1) * (ew - 20), qy = ey + 10 + (eh - 20) - (b.pts[i] - lo) / ((hi - lo) || 1) * (eh - 20); i ? ctx.lineTo(qx, qy) : ctx.moveTo(qx, qy); }
    ctx.strokeStyle = C.green; ctx.lineWidth = 3; ctx.shadowColor = C.green; ctx.shadowBlur = 14; ctx.stroke(); ctx.shadowBlur = 0;
    txt(pct(b.pts[drawn - 1]), px0 + pw - 20, ey + eh / 2 - 8, '400 44px ' + BLACK, b.pts[drawn - 1] >= 0 ? C.green : C.red, 'right', 18);
    txt('LIVE · PAPER', px0 + pw - 20, ey + eh / 2 + 30, '700 12px ' + MONO, C.dim, 'right');
    ctx.restore();
  }

  var DRAW = { build: drawBuild, blast: drawBlast, blind: drawBlind, bar: drawBar, bot: drawBot }, lastStage = -1;
  function frame() {
    if (LAB === 'live' && raw() >= TOTAL) { DOWN = ''; setLab('replay', 'PREVIEW RUN'); }   // the run finished: it is now the last search
    var t = now(), sp = stageAt(t), si = sp[0], p = sp[1];
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
    badge(si, p);
    window.QL.t = t; window.QL.stage = si; window.QL.paused = paused; window.QL.lab = LAB;
    requestAnimationFrame(frame);
  }

  // ---------------------------------------------------------------- modes
  function setMode(m) {
    M = m === 'sim' ? SIM : REAL; cells = null;
    var keep = window.QL.stage || 0;
    DOWN = m === 'real' && FAILS.length ? downWhy() : '';
    setLab('replay', m === 'sim' ? 'LAST SEARCH' : day(LAST_GOOD.finished_at));
    if (paused) { keep = Math.min(keep, STAGES.length - 1); held = startOf(keep) + STAGES[keep][3] * STAGES[keep][4]; }   // a paused page stays paused, on the same stage
    [].forEach.call(document.querySelectorAll('[data-mode]'), function (b) { b.className = b.getAttribute('data-mode') === m ? 'q2-on' : ''; });
    $('simtag').hidden = m !== 'sim';
    renderScore(); renderTop(); renderBots(); renderCaps();
    window.QL.mode = m;
    window.QL.sim = { setups: SIM.setups.length, markets: SIM.markets, settings: SIM.settings, tried: SIM.tried, checked: SIM.checked, bots: SIM.bots, z: SIM.z,
      candidates: SIM.candidates.map(function (c) { return { setup_key: c.setup_key, market: c.market, search: c.search, held: c.held, bar: c.bar, won: c.won }; }) };
  }
  document.addEventListener('click', function (e) {
    var b = e.target.closest('[data-mode]'); if (b) return setMode(b.getAttribute('data-mode'));
    if (e.target.closest('[data-pp]')) return pause(!paused);
    if (e.target.closest('[data-go]')) {   // their Search now would POST; this mock only plays what a running search looks like
      if (LAB === 'live') return;
      pause(false); return setLab('live', '');
    }
    var s = e.target.closest('[data-st]');
    if (s) goStage(+s.getAttribute('data-st'));
  });
  document.addEventListener('keydown', function (e) {
    if (e.target.closest('input, textarea')) return;
    if (e.key === ' ') { e.preventDefault(); pause(!paused); }
    else if (e.key === 'ArrowRight' || e.key === 'ArrowLeft') { pause(true); goStage(stageAt(now())[0] + (e.key === 'ArrowRight' ? 1 : -1)); }
  });
  window.addEventListener('resize', size);
  size();
  setMode(/[?&]mode=sim/.test(location.search) ? 'sim' : 'real');
  requestAnimationFrame(frame);
  window.QL.ready = true;
})();
