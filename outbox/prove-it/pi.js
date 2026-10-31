/* Prove It mock, drawn into their /themes/performance page with their own classes. Two views:
   today  every row carries today's real numbers (data.js, refresh.py); one rule saved (the operator's), the rest are
          Nexus's suggestions; nothing proven, nothing invested.
   sim    one made-up month from ONE model (simulate() below): every figure in every row, the wallet and the log is
          computed from the same daily paths, so the parts always add up. Marked simulated.
   The page sends nothing: no fetch, no form. */
(function () {
  'use strict';
  var D = window.PI_DATA || {};
  var BAL = 1000, MASTER = 1.0;   // the example balance, and the share of it all rules together may use
  var $ = function (id) { return document.getElementById(id); };
  var esc = function (s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); };
  var usd = function (v) { return '$' + Math.round(v).toLocaleString('en-US'); };
  var pct = function (v, d) { return (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(d == null ? 1 : d) + '%'; };
  var cls = function (v) { return v > 0 ? 'pos' : v < 0 ? 'neg' : 'flat'; };

  /* ------------------------------------------------------------------ the operator's sentence and Nexus's read */
  var SENTENCE = [
    ['Nexus, for '], ['event cards', 'what'], [': when you '], ['prove a combination of cards is profitable 70% of the time', 'proof'],
    [', invest my money in it, '], ['100%', 'money'], ['.']
  ];
  var READ = [
    ['What', 'Event cards: any mix Nexus names before it trades.'],
    ['Proof', 'At least <b>70% of trades won</b> and <b>up after fees</b>, over 30 paper trades or more, counted from today.',
      'A coin flip wins 70% of 10 trades 17 times in 100, of 30 trades 2 times in 100: so 30 at least. Up after fees too, because many small wins can still lose money. Only trades after the rule count, on the mix Nexus named first; a new mix starts the count again.'],
    ['Money', 'Up to <b>100%</b> of your balance, only once proven.'],
    ['Stop', 'Down <b>15%</b>: sold, back to paper. <span class="def flat">Nexus\'s default, you did not say one.</span>',
      'Every rule has a stop. Tap to change it.']
  ];

  /* ------------------------------------------------------------------ the products: real numbers in today's view */
  var th = D.themes || {}, fu = D.funds || {}, bo = D.bots || {};
  var top = (th.top || [])[0] || { label: '?', pct: 0 };
  var PRODUCTS = [
    { id: 'cards', name: 'event cards', sub: (D.cards ? D.cards.live.toLocaleString('en-US') : '?') + ' live', rule: 'yours',
      legs: ['≥70% won', 'up after fees', '30 trades', '≤100%', 'stop −15%'], cap: 1.0,
      ctx: 'a backtest or a past week never counts' },
    { id: 'themes', name: 'themes', sub: (th.published || 10) + ' top themes', rule: 'suggest',
      legs: ['1 theme Nexus names', 'beats SPY after fees', '4 weeks in a row', '≤20%', 'stop −10%'], cap: 0.2,
      ctx: 'last ' + (th.period || '5d') + ': ' + esc(top.label) + ' <span class="pos">' + pct(top.pct, 2) + '</span> vs SPY ' + pct(th.spy_pct || 0, 2),
      ctxt: 'Their page measures today\'s 10 names backwards (prices as of ' + (th.as_of || '?') + '). A great week found afterwards is not proof: the count starts when Nexus names a theme.' },
    { id: 'funds', name: 'funds', sub: (fu.count || '?') + ' funds', rule: 'suggest',
      legs: ['1 fund Nexus names', '+3% after fees', '14 days', 'never −8%', '≤20%', 'stop −10%'], cap: 0.2,
      ctx: 'since start: <span class="pos">' + (fu.up || 0) + ' up</span>, <span class="neg">' + (fu.down || 0) + ' down</span>',
      ctxt: 'Best ' + ((fu.best || {}).name || '?') + ' ' + pct((fu.best || {}).pct || 0, 2) + ', worst ' + ((fu.worst || {}).name || '?') + ' ' + pct((fu.worst || {}).pct || 0, 2) + '. Picking the winners afterwards is easy; the count starts when Nexus names one.' },
    { id: 'bots', name: 'bots', sub: 'Quant Lab', rule: 'suggest',
      legs: ['a Quant Lab winner', 'then 30 paper trades up', '≤10%', 'stop −10%'], cap: 0.1,
      ctx: (bo.tried || 0).toLocaleString('en-US') + ' tried, ' + (bo.blind_tested || 0) + ' blind-tested, <span class="' + (bo.won ? 'pos' : 'neg') + '">' + (bo.won || 0) + ' cleared</span>' },
    { id: 'farms', name: 'airdrop farmer', sub: ((D.farms || {}).count || '?') + ' farms', rule: 'none',
      legs: [], cap: 0,
      ctx: 'no rule: Nexus never touches it' },
    { id: 'new', name: 'anything new', sub: 'every launch', rule: 'suggest',
      legs: ['paper from day 1', '+3% after fees', '30 days', '≤10%', 'stop −10%'], cap: 0.1,
      ctx: 'a new product gets a row here by itself, and you a ping' }
  ];

  /* ------------------------------------------------------------------ the month: ONE model for every number */
  // Daily paths, made up, chosen to show three things a gate must do: open (themes), close on its stop (funds), and
  // stay shut when the bar is missed (event cards). Bots stay at 0 cleared, as their lab is today.
  function simulate() {
    var days = [], log = [], cash = BAL;
    var pos = {};   // product id -> {cost, value}
    var cardWins = [1, 1, 0, 1, 0, 1, 1, 0, 1, 1, 0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 1, 0, 1, 0, 0, 1, 1, 0, 1, 1];   // 18 of 30
    var cardWins2 = [1, 1, 0, 1, 1, 0, 1, 0, 1, 1, 1];
    var themeWeeks = [1.2, 0.6, 0.9, 0.4];   // excess over SPY, each week
    var fundPaper = [0.2, 0.5, 0.1, 0.8, 1.2, 0.9, 1.5, 1.9, 1.6, 2.2, 2.5, 2.3, 2.8, 3.2];   // paper, days 1-14
    var fundLive = [-1.0, -2.2, -1.5, -3.8, -5.0, -4.1, -6.6, -7.9, -8.8, -10.3];             // money in, days 15-24
    var themeLive = [0.3, 0.5];
    var newPaper = [0.1, 0.3, -0.2, 0.4, 0.5, 0.3, 0.7, 0.6, 0.9, 0.8, 1.0, 0.7, 1.1, 0.9, 1.2, 1.0, 1.3, 1.1, 1.0, 1.2, 1.1];
    function L(d, m, a, c) { log.push({ d: d, m: m, a: a || '', c: c || '' }); }

    for (var d = 0; d <= 30; d++) {
      var st = {};
      if (d === 0) {
        L(0, 'Rules saved: <b>event cards</b> (yours); themes, funds, bots, anything new (Nexus\'s, taken as they are)');
        L(0, 'Paper tests start: cards mix #1, theme #1, fund #1, Quant Lab daily');
      }
      // event cards: 1.4 paper trades a day; each trade 10% of paper capital, +1.1% won, −1.9% lost
      var mix = d <= 22 ? 1 : 2, n, w, net;
      if (mix === 1) { n = Math.min(30, Math.floor(d * 1.4)); w = sum(cardWins.slice(0, n)); }
      else { n = Math.min(cardWins2.length, Math.floor((d - 22) * 1.4)); w = sum(cardWins2.slice(0, n)); }
      net = (w * 1.1 - (n - w) * 1.9) * 0.1;
      st.cards = { prog: n / 30, line: n + '/30 trades', score: n ? Math.round(100 * w / n) + '% won' : '', net: n ? net : null,
        tone: n >= 10 && w / n < 0.7 ? 'bad' : '', status: 'proving', st: mix === 2 ? 'proving · mix #2' : 'proving' };
      if (d === 22) {
        st.cards.status = 'failed'; st.cards.st = 'not proven';
        L(22, '<b>Event cards</b>: ' + n + ' trades, ' + Math.round(100 * w / n) + '% won, ' + pct(net, 1) + ' after fees. Under your 70%: no money. Mix #2, the count starts again');
      }
      // themes
      var wk = Math.floor(d / 7), ahead = themeWeeks.slice(0, Math.min(4, wk)).filter(function (x) { return x > 0; }).length;
      st.themes = { prog: ahead / 4, line: ahead + '/4 weeks', score: wk ? pct(sum(themeWeeks.slice(0, Math.min(4, wk))), 1) + ' vs SPY' : '', tone: ahead ? 'good' : '', status: 'proving', st: 'proving' };
      if (d === 28) {
        var put = Math.min(BAL * 0.2, cash, BAL * MASTER - invested(pos));
        pos.themes = { cost: put, value: put }; cash -= put;
        L(28, '<b>Themes</b> proved: theme #1 beat SPY 4 weeks in a row, +3.1% over SPY after fees', '+' + usd(put) + ' in', 'pos');
      }
      if (pos.themes) {
        if (d > 28) pos.themes.value = pos.themes.cost * (1 + themeLive[d - 29] / 100);
        st.themes = { prog: 1, line: '4/4 weeks', score: '+3.1% vs SPY', tone: 'good', status: 'unlocked', st: 'proven · in', money: pos.themes.value };
      }
      // funds
      if (d <= 14) {
        var fr = d ? fundPaper[d - 1] : 0;
        st.funds = { prog: d / 14, line: d + '/14 days', score: d ? pct(fr, 1) : '', tone: fr >= 3 ? 'good' : '', status: 'proving', st: 'proving' };
        if (d === 14) {
          var put2 = Math.min(BAL * 0.2, cash, BAL * MASTER - invested(pos));
          pos.funds = { cost: put2, value: put2 }; cash -= put2;
          st.funds = { prog: 1, line: '14/14 days', score: '+3.2%', tone: 'good', status: 'unlocked', st: 'proven · in', money: put2 };
          L(14, '<b>Funds</b> proved: fund #1 +3.2% after fees in 14 days, never below −8%', '+' + usd(put2) + ' in', 'pos');
        }
      } else if (d <= 24) {
        var lr = fundLive[d - 15];
        pos.funds.value = pos.funds.cost * (1 + lr / 100);
        st.funds = { prog: 1, line: 'live ' + pct(lr, 1), score: 'stop at −10%', tone: 'good', status: 'unlocked', st: 'proven · in', money: pos.funds.value };
        if (lr <= -10) {
          cash += pos.funds.value;
          L(24, '<b>Funds</b> hit your stop at ' + pct(lr, 1) + ': sold, back to paper, must prove again', usd(pos.funds.value) + ' back', 'neg');
          st.funds = { prog: 0, line: '0/14 days', score: pct(lr, 1) + ' live', status: 'pulled', st: 'stopped', money: 0 };
          delete pos.funds;
        }
      } else {
        st.funds = { prog: (d - 24) / 14, line: (d - 24) + '/14 days', score: 'again from 0', status: 'pulled', st: 'stopped · on paper', money: 0 };
      }
      // bots: their lab as it is today
      st.bots = { prog: 0, line: (bo.won || 0) + ' cleared', score: (bo.tried || 0).toLocaleString('en-US') + ' tried', status: 'proving', st: 'proving' };
      // anything new: a launch on day 9
      if (d === 9) L(9, '<b>A new product launched</b>: its row added by itself, paper test starts, you got a ping');
      if (d < 9) st['new'] = { prog: 0, line: 'no launch yet', score: '', status: 'waiting', st: 'waiting' };
      else {
        var nd = d - 9, nr = nd ? newPaper[nd - 1] : 0;
        st['new'] = { prog: nd / 30, line: nd + '/30 days', score: nd ? pct(nr, 1) : '', tone: '', status: 'proving', st: 'proving · 1 new' };
      }
      st.farms = { status: 'locked', st: 'no rule' };
      var inv = 0; Object.keys(pos).forEach(function (k) { inv += pos[k].value; });
      days.push({ st: st, cash: cash, inPlay: inv, bal: cash + inv, proven: Object.keys(pos).length, rules: 5, log: log.filter(function (x) { return x.d <= d; }) });
    }
    return days;
  }
  function sum(a) { return a.reduce(function (s, x) { return s + x; }, 0); }
  function invested(pos) { var s = 0; Object.keys(pos).forEach(function (k) { s += pos[k].cost; }); return s; }

  // today: the real state. One rule (his), proving, at 0; the rest suggestions; nothing in.
  var ACC = {};
  function today() {
    var st = {
      cards: { prog: 0, line: '0/30 trades', status: 'proving', st: 'proving' },
      themes: { prog: 0, line: '0/4 weeks', status: 'suggest', st: 'suggested' },
      funds: { prog: 0, line: '0/14 days', status: 'suggest', st: 'suggested' },
      bots: { prog: 0, line: (bo.won || 0) + ' cleared', score: (bo.tried || 0).toLocaleString('en-US') + ' tried', status: 'suggest', st: 'suggested' },
      farms: { status: 'locked', st: 'no rule' },
      'new': { prog: 0, line: 'no launch yet', status: 'suggest', st: 'suggested' }
    };
    var log = [{ d: 'today', m: 'Rule saved: <b>event cards</b>' }, { d: 'today', m: 'Paper test starts: cards mix #1. Nothing proven, nothing invested' }];
    Object.keys(ACC).forEach(function (k) {
      st[k].status = k === 'new' ? 'waiting' : 'proving'; st[k].st = k === 'new' ? 'waiting' : 'proving';
      log.push({ d: 'today', m: 'You took Nexus\'s rule for <b>' + esc(nameOf(k)) + '</b>: paper test starts' });
    });
    return { st: st, cash: BAL, inPlay: 0, bal: BAL, proven: 0, rules: 1 + Object.keys(ACC).length, log: log };
  }
  function nameOf(id) { for (var i = 0; i < PRODUCTS.length; i++) if (PRODUCTS[i].id === id) return PRODUCTS[i].name; return id; }

  /* ------------------------------------------------------------------ drawing */
  function drawSentence(lit) {
    $('sentence').innerHTML = SENTENCE.map(function (p) {
      return p[1] ? '<span class="hl' + (lit ? ' on' : '') + '">' + esc(p[0]) + '</span>' : esc(p[0]);
    }).join('');
  }
  function drawRead(animate) {
    $('read').innerHTML = READ.map(function (r) {
      return '<div class="fp-row"' + (r[2] ? ' title="' + esc(r[2]) + '"' : '') + '><div class="fp-row-label">' + r[0] + '</div><div class="fp-row-value">' + r[1] + '</div></div>';
    }).join('') + '<div class="fp-row"><div class="fp-row-label"></div><div class="fp-row-value pi-saverow"><span class="tp-hold" title="Nexus can never change a saved rule; it can only suggest a new one.">Saved</span></div></div>';
    var rows = [].slice.call($('read').children);
    if (!animate) { rows.forEach(function (e) { e.classList.add('in'); }); drawSentence(true); return; }
    drawSentence(false);
    var spans = [].slice.call($('sentence').querySelectorAll('.hl'));
    rows.forEach(function (row, i) {
      setTimeout(function () { if (spans[i]) spans[i].classList.add('on'); row.classList.add('in'); }, 200 + i * 380);
    });
  }

  function wallet(s) {
    var gain = s.bal - BAL;
    $('wallet').innerHTML = '<tbody><tr>' +
      '<td title="Example balance: what you charged. Nexus buys and sells only inside a proven product; it can never withdraw or send money out."><div class="k">Balance</div><div class="v">' + usd(s.bal) + '</div><div class="s ' + cls(gain) + '">' + (Math.abs(gain) >= 0.5 ? pct(100 * gain / BAL, 1) : 'example') + '</div></td>' +
      '<td title="All rules together never use more than this. Money goes to products in the order they prove themselves."><div class="k">Nexus may use</div><div class="v">' + Math.round(MASTER * 100) + '%</div><div class="s">all rules together</div></td>' +
      '<td><div class="k">In play</div><div class="v">' + usd(s.inPlay) + '</div><div class="s">' + usd(s.cash) + ' cash</div></td>' +
      '<td title="Rules whose product has proven it and holds your money now, out of your rules."><div class="k">Proven</div><div class="v ' + (s.proven ? 'pos' : '') + '">' + s.proven + ' of ' + s.rules + '</div><div class="s">rules</div></td>' +
      '<td class="kill"><button type="button" class="pi-kill" id="kill" title="Sells everything Nexus bought and pauses every rule. One tap.">Stop all</button></td>' +
      '</tr></tbody>';
  }

  function board(s, fresh) {
    $('grid').innerHTML = PRODUCTS.map(function (p, i) {
      var x = s.st[p.id] || {}, status = x.status, money = x.money || 0, capUsd = BAL * p.cap;
      var trc = status === 'unlocked' ? 'in' : (status === 'suggest' || status === 'locked') ? 'off' : '';
      var stc = { unlocked: 'pos', pulled: 'neg', failed: 'neg' }[status] || '';
      var legs = p.legs.map(function (l) { return '<span class="tp-leg">' + esc(l) + '</span>'; }).join('');
      var fill = Math.max(0, Math.min(1, x.prog || 0));
      var tone = status === 'failed' ? 'bad' : (status === 'unlocked' ? 'good' : x.tone || '');
      var proof = p.rule === 'none' ? '<span class="flat">—</span>' :
        '<div class="line"><b>' + esc(x.line || '') + '</b>' + (x.score ? ' · ' + esc(x.score) : '') +
        (x.net != null ? ' · <span class="' + cls(x.net) + '">' + pct(x.net, 1) + '</span> after fees' : '') + '</div>' +
        '<div class="pi-gauge' + (status === 'unlocked' ? ' open' : '') + '" title="The proof so far. The dashed line at the end is your bar; it opens only when every line of the rule holds."><i class="' + tone + '" style="width:' + (fill * 100).toFixed(1) + '%"></i></div>';
      return '<tr class="' + trc + (fresh && fresh[p.id] ? ' new' : '') + '">' +
        '<td class="tp-rank">' + (i + 1) + '</td>' +
        '<td class="tp-theme"><div class="tp-parent">' + esc(p.sub) + '</div><b>' + esc(p.name) + '</b>' +
          '<div class="tp-parent"' + (p.ctxt ? ' title="' + esc(p.ctxt) + '"' : '') + '>' + p.ctx + '</div></td>' +
        '<td>' + (p.rule === 'yours' ? '<div class="tp-parent">yours</div>' : p.rule === 'suggest' ? '<div class="tp-parent">Nexus suggests</div>' : '') +
          (legs ? '<div class="tp-legs">' + legs + '</div>' : '') +
          (status === 'suggest' ? '<button type="button" class="tp-hold" data-use="' + p.id + '" title="Take it as it is; change any line later.">Use it</button>' : '') +
          (p.rule === 'none' ? '<button type="button" class="tp-hold" data-none="1">Write a rule</button>' : '') + '</td>' +
        '<td class="pi-proof"><div class="tp-parent st ' + stc + '">' + esc(x.st || '') + '</div>' + proof + '</td>' +
        '<td class="tp-num">' + (p.cap ? '<span class="' + (money ? 'pos' : 'flat') + '">' + usd(money) + '</span><div class="tp-parent">of ' + usd(capUsd) + '</div>' : '<span class="flat">—</span>') + '</td>' +
        '</tr>';
    }).join('');
  }

  function drawLog(items, freshDay) {
    $('log').innerHTML = items.slice().reverse().map(function (x) {
      return '<tr' + (freshDay != null && x.d === freshDay ? ' class="new"' : '') + '><td>' + (typeof x.d === 'number' ? 'day ' + x.d : esc(x.d)) + '</td><td>' + x.m + '</td>' +
        '<td class="tp-num ' + (x.c || '') + '">' + esc(x.a || '') + '</td></tr>';
    }).join('');
  }

  /* ------------------------------------------------------------------ views and the clock */
  var MODE = 'today', SIM = null, DAY = 0, timer = null;
  function setMode(m) {
    MODE = m;
    [].forEach.call(document.querySelectorAll('.pi-modebar .tp-tab[data-mode]'), function (b) { b.setAttribute('aria-selected', String(b.dataset.mode === m)); });
    $('clock').hidden = m !== 'sim';
    if (m === 'sim') { if (!SIM) SIM = simulate(); DAY = 0; showDay(0); play(true); }
    else { play(false); var s = today(); wallet(s); board(s); drawLog(s.log); }
    $('asof').innerHTML = m === 'sim'
      ? '<b>Simulated</b> · one made-up month from one model · not a forecast'
      : 'Numbers as of <b>' + esc(D.as_of || '?') + '</b> · event cards, themes, fund performance, Airdrop Farmer, our Quant Lab';
    $('foot').textContent = 'Mock of a page Cymetica does not have. Nothing here is sent; the balance is an example. Nexus would trade only inside a product whose rule is proven, and could never withdraw.';
  }
  function showDay(d) {
    var was = DAY, s = SIM[d], fresh = {};
    if (d === was + 1) PRODUCTS.forEach(function (p) {
      var a = (SIM[was].st[p.id] || {}).status, b = (s.st[p.id] || {}).status;
      if (a !== b) fresh[p.id] = 1;
    });
    DAY = d; $('day').value = d; $('dayl').textContent = 'Day ' + d;
    wallet(s); board(s, fresh); drawLog(s.log, d === was + 1 ? d : null);
  }
  function play(on) {
    clearInterval(timer); timer = null;
    $('play').textContent = on ? 'Pause' : 'Play';
    if (!on) return;
    if (DAY >= 30) showDay(0);
    timer = setInterval(function () {
      if (DAY >= 30) { play(false); return; }
      showDay(DAY + 1);
    }, 650);
  }

  function toast(t) {
    var el = document.querySelector('.pi-toast');
    if (!el) { el = document.createElement('div'); el.className = 'pi-toast'; document.body.appendChild(el); }
    el.textContent = t; el.hidden = false; clearTimeout(toast.h); toast.h = setTimeout(function () { el.hidden = true; }, 2600);
  }

  document.addEventListener('click', function (e) {
    var b = e.target.closest('#prove-it button'); if (!b) return;
    if (b.dataset.mode) setMode(b.dataset.mode);
    else if (b.id === 'play') play(!timer);
    else if (b.id === 'send') drawRead(true);
    else if (b.id === 'kill') toast('Mock: on the real page this sells everything Nexus bought and pauses every rule. Nothing sent.');
    else if (b.dataset.use) {
      if (MODE !== 'today') { toast('In the simulated month every suggestion is already taken.'); return; }
      ACC[b.dataset.use] = 1; var s = today(); wallet(s); board(s); drawLog(s.log);
    }
    else if (b.dataset.none) { $('sentence').focus(); toast('Write it in the box above, e.g. “Nexus, airdrop farms: only after …”'); }
  });
  $('day').addEventListener('input', function () { play(false); var d = +this.value; DAY = d; showDay(d); });   // a jump: no marks
  document.addEventListener('keydown', function (e) {
    if (MODE !== 'sim' || e.target.isContentEditable || /INPUT|TEXTAREA/.test(e.target.tagName)) return;
    if (e.code === 'Space') { e.preventDefault(); play(!timer); }
    if (e.key === 'ArrowRight' && DAY < 30) { play(false); showDay(DAY + 1); }
    if (e.key === 'ArrowLeft' && DAY > 0) { play(false); showDay(DAY - 1); }
  });

  drawRead(true);
  setMode(/mode=sim/.test(location.search) ? 'sim' : 'today');
})();
