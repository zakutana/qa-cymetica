/* Chart Analyzer, trend patch. The verdict has two states, BULL TREND or BEAR TREND, read from a flip line on the
 * candles; the distance to that line is how close the trend is to breaking; a 9-13 count sits on the candles.
 * Runs inside their page after their helper scripts and before their main script. Every figure comes from trend.js. */
(function () {
  'use strict';
  var C = window.czaTrendCalc, DESK = window.czaDesk;
  if (!C || !DESK) return;

  var S = null, H = null;
  var T = { trend: null, count: null, sig: '', closedN: 0, pool: null, chips: {}, chipsFor: '', timer: 0 };
  var TF_WORD = { '1h': 'hourly', '4h': '4-hour', '1d': 'daily', '5d': '5-day', '1w': 'weekly', '2w': '2-week', '1M': 'monthly' };
  var ORDER = ['1h', '4h', '1d', '5d', '1w', '2w', '1M'], CHIPS = ['1h', '4h', '1d', '1w'];
  var MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  var LKEY = 'cza.trend.v1', layers = { flip: true, count: true };

  // First visit: a clean chart. Their layers stay in their menu, switched off; ours are on.
  try {
    if (!localStorage.getItem('cza.trend.seed')) {
      localStorage.setItem('cza.trend.seed', '1');
      if (!localStorage.getItem('cza.layers.v1'))
        localStorage.setItem('cza.layers.v1', JSON.stringify({ levels: true, lines: false, channels: false, forms: false, patterns: false, projections: false, weekly: false }));
      if (!localStorage.getItem('cza.ma.v1')) {
        localStorage.setItem('cza.ma.v1', JSON.stringify([
          { type: 'EMA', len: 20, src: 'close', color: '#00cfff', w: 2, on: false },
          { type: 'SMA', len: 50, src: 'close', color: '#3b82f6', w: 2, on: false },
          { type: 'SMA', len: 200, src: 'close', color: '#e6f4ff', w: 2, on: false }]));
        if (window.czaMA && window.czaMA.reload) window.czaMA.reload();
      }
    }
    var raw = localStorage.getItem(LKEY), o = raw && JSON.parse(raw);
    if (o) { if (typeof o.flip === 'boolean') layers.flip = o.flip; if (typeof o.count === 'boolean') layers.count = o.count; }
  } catch (e) {}

  function $(id) { return document.getElementById(id); }
  function el(tag, cls, txt) { var n = document.createElement(tag); if (cls) n.className = cls; if (txt != null) n.textContent = txt; return n; }
  function px(v) { return DESK.px ? DESK.px(v) : C.fmt(v); }
  C.fmt = function (v) { return px(v); };                  // one price format: the page's own
  function tfLbl(tf) { return tf === '1M' ? '1M' : String(tf || '').toUpperCase(); }
  function who() { return S ? (S.contract ? 'c:' + S.contract + '|' + S.chain : 's:' + S.sym) : ''; }
  function sgn(p) { return (p >= 0 ? '+' : '−') + Math.abs(p).toFixed(1) + '%'; }
  function when(t, tf) {
    var d = new Date((t > 1e11 ? t : t * 1000)), s = d.getUTCDate() + ' ' + MONTHS[d.getUTCMonth()];
    if (d.getUTCFullYear() !== new Date().getUTCFullYear()) s += ' ' + d.getUTCFullYear();
    if (tf === '1h' || tf === '4h') s += ' ' + ('0' + d.getUTCHours()).slice(-2) + ':00';
    return s;
  }

  // ── the figures: computed once per change of the candles or the live price ─────────────────────────────
  function ensure() {
    if (!S) return;
    var rows = S.rows || [], d = S.data, n = rows.length;
    if (!n) { T.trend = T.count = null; T.sig = ''; return; }
    var forming = !!(d && d.last_candle_forming), last = rows[n - 1];
    var p = T.pool && T.pool.price > 0 && !S.replay ? +T.pool.price : null;
    var sig = [who(), S.tf, n, last[0], last[4], forming, p].join('|');
    if (sig === T.sig) return;
    T.sig = sig;
    var use = rows;
    if (p != null) {                                       // the live price is the forming candle's close
      use = rows.slice();
      if (forming) use[n - 1] = [last[0], last[1], Math.max(last[2], p), Math.min(last[3], p), p, last[5]];
      else use.push([last[0] + 1, p, p, p, p, 0]);
    }
    var open = forming || p != null;
    T.trend = C.flipLine(use, { forming: open });
    T.count = C.count913(use, { forming: open });
    T.closedN = open ? use.length - 1 : use.length;
  }

  // ── other timeframes: the same rule on the candles that timeframe opens with ──────────────────────────
  function frames(tf) {
    var q = S.contract ? { contract: S.contract, chain: S.chain, tf: tf } : { symbol: S.sym, tf: tf };
    q.chip = true;                                         // a lookup for the chips or a built timeframe, not the page's own subscribe
    return window.czaMockFrames(q);
  }
  function analysisOf(res) {
    var a = null; ((res && res.frames) || []).forEach(function (f) { if (f && f.type === 'analysis' && f.candles && f.candles.length) a = f; });
    return a;
  }
  function build(c, from, to) {
    if (to === '4h') return C.toBuckets(c, 14400);
    var daily = from === '1d' ? c : C.toBuckets(c, 86400);
    if (to === '1d') return daily;
    if (to === '5d') return C.toBlocks(daily, 5);
    if (to === '1w') return C.toWeeks(daily);
    if (to === '2w') return C.toBlocks(C.toWeeks(daily), 2);
    if (to === '1M') return C.toMonths(daily);
    return null;
  }
  function compose(tf) {                                   // a timeframe too young for their score, built from shorter candles
    var srcs = ['1d', '4h', '1h'].filter(function (x) { return ORDER.indexOf(x) < ORDER.indexOf(tf); }), k = 0;
    function next() {
      if (k >= srcs.length) return Promise.resolve(null);
      var src = srcs[k++];
      return frames(src).then(function (res) {
        var a = analysisOf(res), rows = a && build(a.candles, src, tf);
        return rows && rows.length >= 2 ? { rows: rows, forming: true, from: src, identity: a.identity, symbol: a.symbol } : next();
      }, next);
    }
    return next();
  }
  function rowsFor(tf) {
    return frames(tf).then(function (res) {
      var a = analysisOf(res);
      return a ? { rows: a.candles, forming: !!a.last_candle_forming } : compose(tf);
    }, function () { return compose(tf); });
  }
  function loadChips() {
    if (!window.czaMockFrames || !S) return;
    var w = who();
    if (T.chipsFor !== w) { T.chipsFor = w; T.chips = {}; }
    CHIPS.forEach(function (tf) {
      if (tf === S.tf || T.chips[tf]) return;
      T.chips[tf] = 'wait';
      rowsFor(tf).then(function (r) {
        if (T.chipsFor !== w) return;
        var tr = r ? C.flipLine(r.rows, { forming: r.forming }) : null;
        T.chips[tf] = tr && tr.ok ? tr.side : r ? 'young' : 'none';
        chips();
      }, function () { if (T.chipsFor === w) { T.chips[tf] = 'na'; chips(); } });
    });
  }
  function align() {
    var a = { bull: 0, bear: 0, total: 0 };
    CHIPS.forEach(function (tf) { var s = T.chips[tf]; if (s === 'bull' || s === 'bear') { a[s]++; a.total++; } });
    return a;
  }

  // ── the verdict card ───────────────────────────────────────────────────────────────────────────────────
  function layRow(label, col, key) {
    var lab = el('label', 'cza-sw cza-lay cza-chk'), inp = el('input'), sw = el('s');
    inp.type = 'checkbox'; inp.checked = layers[key];
    inp.addEventListener('change', function () {
      layers[key] = inp.checked; try { localStorage.setItem(LKEY, JSON.stringify(layers)); } catch (e) {}
      if (H) H.redraw();
    });
    sw.style.background = col;
    lab.appendChild(inp); lab.appendChild(el('i')); lab.appendChild(sw); lab.appendChild(document.createTextNode(label));
    return lab;
  }
  function mount() {
    var card = $('czaRead'); if (!card) return false;
    if ($('ctHero')) return true;
    var top = card.querySelector('.cza-read-top'), lbl = el('span', 'cza-lbl', 'Trend'); lbl.id = 'ctLbl';
    top.insertBefore(lbl, top.firstChild);
    var hero = el('div', 'ct-hero'); hero.id = 'ctHero';
    card.insertBefore(hero, top.nextSibling);
    var det = $('czaDetails'), edge = card.querySelector('.cza-edge'), why = $('czaEdgeWhy');
    if (det && edge) {                                     // their Edge line now lives under "How it's measured"
      var wrap = el('div', 'ct-edge'), sm = det.querySelector('summary');
      wrap.appendChild(edge); if (why) wrap.appendChild(why);
      det.insertBefore(wrap, sm ? sm.nextSibling : det.firstChild);
    }
    var menu = $('czaLayersMenu');
    if (menu) {
      var grp = el('div', 'cza-lgrp'); grp.id = 'ctLay';
      grp.appendChild(el('div', 'cza-lbl', 'Trend'));
      grp.appendChild(layRow('Flip line', '#00ff88', 'flip')); grp.appendChild(layRow('9-13 count', '#00cfff', 'count'));
      menu.insertBefore(grp, menu.firstChild);
      if (DESK.countLayers) DESK.countLayers();
    }
    return true;
  }
  function countWords(c) {
    var d = function (x) { return x === 'up' ? 'up' : 'down'; }, main = 'no count running', hint = '';
    if (c.last13 && c.last13.ago <= 2) { main = '13 printed ' + ago(c.last13.ago); hint = 'a long ' + (c.last13.dir === 'up' ? 'rally' : 'sell-off') + ' is usually spent here'; }
    else if (c.last9 && c.last9.ago <= 2) { main = d(c.last9.dir) + ' 9 printed ' + ago(c.last9.ago); hint = (c.last9.dir === 'up' ? 'rallies' : 'sell-offs') + ' often pause here'; }
    else if (c.now && c.now.n) { main = d(c.now.dir) + ' ' + c.now.n + ' of 9'; hint = c.now.n >= 7 ? (9 - c.now.n) + ' more and the ' + (c.now.dir === 'up' ? 'rally' : 'sell-off') + ' is stretched' : ''; }
    if (c.countdown && c.countdown.n > 0 && !(c.last13 && c.last13.ago <= 2)) hint = (hint ? hint + ' · ' : '') + 'countdown ' + c.countdown.n + ' of 13';
    return { main: main, hint: hint };
  }
  function ago(n) { return n === 0 ? 'on the last candle' : n + ' candle' + (n > 1 ? 's' : '') + ' ago'; }
  function chips() {
    var box = $('ctTfs'); if (!box || !S) return;
    box.textContent = '';
    CHIPS.forEach(function (tf) {
      var s = T.chips[tf], b = el('button', 'cza-tchip ct-tf ' + (s === 'bull' ? 'pos' : s === 'bear' ? 'neg' : 'na') + (tf === S.tf ? ' on' : ''),
        tfLbl(tf) + ' ' + (s === 'bull' ? '▲' : s === 'bear' ? '▼' : '·'));
      b.type = 'button';
      b.title = tfLbl(tf) + ': ' + (s === 'bull' ? 'bull trend' : s === 'bear' ? 'bear trend' : s === 'young' ? 'too few candles for a trend' : s === 'none' || s === 'na' ? 'no candles for this coin yet' : 'reading') + (s === 'bull' || s === 'bear' ? ', by the same flip line.' : '.');
      b.addEventListener('click', function () { var t = document.querySelector('.cza-tf button[data-tf="' + tf + '"]'); if (t && tf !== S.tf) t.click(); });
      box.appendChild(b);
    });
    var a = align(), w = el('span', 'ct-align');
    if (a.total >= 2) {
      w.textContent = a.bull === a.total ? 'ALL BULL' : a.bear === a.total ? 'ALL BEAR' : 'MIXED';
      w.className = 'ct-align ' + (a.bull === a.total ? 'pos' : a.bear === a.total ? 'neg' : '');
    }
    box.appendChild(w);
    var say = $('ctSay'), t = T.trend;
    if (say && t && t.ok) {
      var lines = C.sentence(t, T.count, TF_WORD[S.tf] || S.tf, null), al = alignLine(t);
      if (lines.length < 2 && al) lines.push(al);
      say.textContent = '';
      lines.forEach(function (x) { say.appendChild(el('span', null, x + ' ')); });
    }
  }
  function alignLine(t) {                                  // what the other timeframes say about this trend
    var here = ORDER.indexOf(S.tf), hi = [], lo = [], known = 0;
    CHIPS.forEach(function (tf) {
      var s = T.chips[tf]; if (tf === S.tf || (s !== 'bull' && s !== 'bear')) return;
      known++; if (s !== t.side) (ORDER.indexOf(tf) > here ? hi : lo).push(tfLbl(tf));
    });
    if (!known) return '';
    if (!hi.length && !lo.length) return 'Every timeframe agrees.';
    if (hi.length) return 'The ' + hi.join(' and ') + ' trend is still ' + (t.side === 'bull' ? 'bear, so this is a bounce until that turns.' : 'bull, so this is a pullback inside it.');
    return 'Shorter timeframes (' + lo.join(', ') + ') have already turned ' + (t.side === 'bull' ? 'down.' : 'up.');
  }
  function hero() {
    if (!S || !mount()) return;
    ensure();
    var box = $('ctHero'), card = $('czaRead'), t = T.trend, tf = S.tf, d = S.data || {};
    $('ctLbl').textContent = 'Trend · ' + tfLbl(tf);
    box.textContent = '';
    if (!t) { card.setAttribute('data-ct', ''); return; }
    var word = el('div', 'ct-word');
    if (!t.ok) {
      card.setAttribute('data-ct', 'young');
      word.appendChild(el('span', null, 'TOO')); word.appendChild(el('span', 'ct-w2', 'YOUNG'));
      box.appendChild(word);
      box.appendChild(el('p', 'ct-since', t.have + ' of ' + t.need + ' ' + (TF_WORD[tf] || tf) + ' candles'));
      box.appendChild(el('p', 'ct-rule', 'The chart is drawn. A trend needs ' + t.need + ' closed candles; a shorter timeframe has one.'));
    } else {
      var bull = t.side === 'bull';
      card.setAttribute('data-ct', t.side);
      T.chips[tf] = t.side;
      word.appendChild(el('span', null, bull ? 'BULL' : 'BEAR')); word.appendChild(el('span', 'ct-w2', 'TREND'));
      box.appendChild(word);
      box.appendChild(el('p', 'ct-since', t.last_flip ? 'since ' + when(t.last_flip.t, tf) + ' · ' + sgn(t.since_flip_pct) + ' since the flip'
        : 'since the first candle on this chart'));
      var m = el('div', 'ct-meter'), st = el('div', 'ct-m-st'), mt = el('div', 'ct-m-top'), tw = TF_WORD[tf] || tf;
      var w = t.breaking ? 'BREAKING' : t.word;
      st.appendChild(el('i', 'ct-chip ' + (t.breaking || w === 'AT THE EDGE' ? 'edge' : w === 'CLOSE' ? 'close' : 'room'), w));
      st.appendChild(el('span', null, t.dist_atr < 1 ? 'under one average ' + tw + ' candle away' : t.dist_atr.toFixed(1) + ' average ' + tw + ' candles away'));
      m.appendChild(st);
      mt.appendChild(el('b', 'ct-dist', t.dist_pct.toFixed(1) + '%'));
      mt.appendChild(el('span', null, t.breaking ? 'through the flip' : bull ? 'above the flip' : 'under the flip'));
      m.appendChild(mt);
      var tr = el('div', 'ct-track'), f = t.breaking ? 0 : Math.max(0.03, Math.min(1, t.dist_atr / 5));
      tr.style.setProperty('--f', (f * 100).toFixed(1) + '%');
      tr.title = 'From the flip line (left) to the price now, in average candle ranges (ATR): the marked zone is one range, the full bar is five.';
      tr.appendChild(el('i', 'ct-zone')); tr.appendChild(el('i', 'ct-fill')); tr.appendChild(el('i', 'ct-dot'));
      m.appendChild(tr);
      var ends = el('div', 'ct-m-ends'), e1 = el('span', null, 'FLIP '), e2 = el('span', null, 'NOW ');
      e1.appendChild(el('b', null, px(t.flip))); e2.appendChild(el('b', null, px(t.price)));
      ends.appendChild(e1); ends.appendChild(e2); m.appendChild(ends);
      m.appendChild(el('p', 'ct-rule', (tf === '1h' ? 'An ' : 'A ') + (TF_WORD[tf] || tf) + ' close ' + (bull ? 'below ' : 'above ') + px(t.flip) + ' turns it ' + (bull ? 'bear' : 'bull') + '.'));
      box.appendChild(m);
    }
    var tfs = el('div', 'ct-tfs'); tfs.id = 'ctTfs'; box.appendChild(tfs);
    if (T.count) {
      var cw = countWords(T.count), cr = el('div', 'ct-count');
      cr.appendChild(el('span', 'cza-lbl', '9-13 count')); cr.appendChild(el('b', null, cw.main));
      if (cw.hint) cr.appendChild(el('span', 'ct-hint', cw.hint));
      cr.title = 'A DeMark-style count: 9 closes in a row beyond the close four candles earlier, then a countdown to 13. It marks a stretched move; it is not the verdict.';
      box.appendChild(cr);
    }
    if (t.ok) { var say = el('p', 'ct-say'); say.id = 'ctSay'; box.appendChild(say); }
    if (d.ct_composed) box.appendChild(el('p', 'ct-note', tfLbl(tf) + ' candles built from ' + tfLbl(d.ct_composed.from) + ' candles: ' + d.ct_composed.n + ' on the chart.'));
    chips();
  }
  function soon() { if (!T.timer) T.timer = setTimeout(function () { T.timer = 0; hero(); }, 300); }

  // ── setups: for the trend, against it; a clicked row opens in place ────────────────────────────────────
  function regroup() {
    var box = $('czaSetups'), d = S && S.data; if (!box || !d) return;
    var side = T.trend && T.trend.ok ? T.trend.side : null, by = {}, fo = [], ag = [], ot = [];
    (d.setups || []).forEach(function (s) { by[s.key] = s; });
    Array.prototype.forEach.call(box.querySelectorAll('.cza-su[data-k]'), function (r) {
      var s = by[r.getAttribute('data-k')], ts = s && s.textbook_side, g = r.querySelector('.cza-su-g');
      if (r.title) { r.setAttribute('data-tip', r.title); r.removeAttribute('title'); }
      if (g) g.textContent = g.textContent.split(' · ').slice(0, 2).join(' · ');
      if (!side || (ts !== 'bullish' && ts !== 'bearish')) ot.push(r);
      else if ((ts === 'bullish') === (side === 'bull')) fo.push(r); else ag.push(r);
    });
    box.textContent = '';
    var head = function (txt, n, cls) { var h = el('div', 'ct-gh ' + (cls || '')); h.appendChild(el('span', null, txt)); h.appendChild(el('b', null, String(n))); box.appendChild(h); };
    if (d.ct_composed) { box.appendChild(el('div', 'cza-none', 'Setups need 60 candles. Trend and count do not.')); return; }
    if (!fo.length && !ag.length && !ot.length) { box.appendChild(el('div', 'cza-none', 'No setup on this chart right now.')); return; }
    if (side) {
      head('FOR THE ' + (side === 'bull' ? 'BULL' : 'BEAR') + ' TREND', fo.length, side === 'bull' ? 'pos' : 'neg'); fo.forEach(function (r) { box.appendChild(r); });
      head('AGAINST IT', ag.length, side === 'bull' ? 'neg' : 'pos'); ag.forEach(function (r) { box.appendChild(r); });
      if (ot.length) { head('NO SIDE', ot.length); ot.forEach(function (r) { box.appendChild(r); }); }
    } else ot.forEach(function (r) { box.appendChild(r); });
  }
  function syncDetail() {
    var box = $('czaSetups'), card = $('czaSetCard'); if (!box) return;
    var old = box.querySelector('.ct-detail'), lit = box.querySelector('.cza-su.lit');
    if (!lit || !card || card.hidden) { if (old) old.parentNode.removeChild(old); return; }
    var txt = []; Array.prototype.forEach.call(card.querySelectorAll('span'), function (n) { txt.push(n.textContent); });
    var key = lit.getAttribute('data-k') + '|' + txt.join(' ');
    if (old && old.getAttribute('data-for') === key && old.previousSibling === lit) return;
    if (old) old.parentNode.removeChild(old);
    var dv = el('div', 'ct-detail'); dv.setAttribute('data-for', key);
    txt.forEach(function (x) { dv.appendChild(el('p', null, x)); });
    lit.parentNode.insertBefore(dv, lit.nextSibling);
  }

  // ── the chart layer: the flip line, its fill, the flip tags, the count ────────────────────────────────
  function drawLayer(s, geo, state, h) {
    ensure();
    var t = T.trend, c = T.count, all = h.rows, n = all.length;
    if (!n) return;
    var a = Math.max(0, geo.s0), b = Math.min(geo.e, n), step = geo.step, half = step / 2, i;
    if (layers.flip && t && t.ok) {
      var lineAt = function (k) { return k < t.line.length ? t.line[k] : t.flip; }, sideAt = function (k) { return k < t.sides.length ? t.sides[k] : t.side; };
      var runs = [], cur = null;
      for (i = a; i < b; i++) {
        var v = lineAt(i), sd = sideAt(i);
        if (v == null || !sd) { cur = null; continue; }
        if (!cur || cur.side !== sd) { cur = { side: sd, pts: [], cl: [] }; runs.push(cur); }
        var x = h.X(i), y = h.Y(v);
        cur.pts.push((x - half).toFixed(1) + ',' + y.toFixed(1), (x + half).toFixed(1) + ',' + y.toFixed(1));
        cur.cl.push(x.toFixed(1) + ',' + h.Y(all[i][4]).toFixed(1));
      }
      var gf = h.svg('g', { 'class': 'ct-fills', 'clip-path': 'url(#czClip)' }), gl = h.svg('g', { 'class': 'ct-lines', 'clip-path': 'url(#czClip)' });
      runs.forEach(function (r) {
        gf.appendChild(h.svg('polygon', { points: r.pts.concat(r.cl.slice().reverse()).join(' '), 'class': 'ct-area ' + r.side }));
        gl.appendChild(h.svg('polyline', { points: r.pts.join(' '), 'class': 'ct-line ' + r.side }));
      });
      var firstG = s.querySelector('g'); if (firstG) s.insertBefore(gf, firstG); else s.appendChild(gf);
      s.appendChild(gl);
      var gt = h.svg('g', { 'class': 'ct-tags', 'clip-path': 'url(#czClip)' });
      t.flips.forEach(function (f) {
        if (f.i < a || f.i >= b) return;
        var up = f.side === 'bull', fx = h.X(f.i), fy = h.Y(t.line[f.i]) + (up ? 8 : -22), g = h.svg('g', { 'class': 'ct-tag ' + f.side });
        g.appendChild(h.svg('rect', { x: fx - 19, y: fy, width: 38, height: 15, rx: 4 }));
        g.appendChild(h.svg('text', { x: fx, y: fy + 11, 'text-anchor': 'middle' }, up ? 'BULL' : 'BEAR'));
        gt.appendChild(g);
      });
      s.appendChild(gt);
      if (geo.e >= n) {                                    // the flip price on the axis, clear of the price tag
        var right = geo.mL + geo.pw, fy0 = h.Y(t.flip), top = geo.mT, bot = geo.mT + geo.ch, yIn = fy0 >= top && fy0 <= bot;
        var ty = Math.max(top + 9, Math.min(bot - 9, fy0)), py = h.Y(all[n - 1][4]);
        var gap = t.side === 'bull' && S.data && S.data.last_candle_forming ? 36 : 20;   // their FORMING label sits under the price tag
        if (Math.abs(ty - py) < gap) ty = py + (t.side === 'bull' ? gap : -20);
        if (yIn) s.appendChild(h.svg('line', { x1: h.X(n - 1) + half, x2: right, y1: fy0, y2: fy0, 'class': 'ct-ext ' + t.side }));
        var ax = h.svg('g', { 'class': 'ct-ax ' + t.side });
        ax.appendChild(h.svg('rect', { x: right + 3, y: ty - 9, width: geo.mR - 5, height: 18, rx: 3 }));
        ax.appendChild(h.svg('text', { x: right + 8, y: ty + 4 }, px(t.flip)));
        s.appendChild(ax);
        if (yIn) s.appendChild(h.svg('text', { x: right - 6, y: fy0 + (t.side === 'bull' ? 13 : -6), 'text-anchor': 'end', 'class': 'ct-axl ' + t.side }, 'FLIP'));
      }
    }
    if (layers.count && c) {
      var lastClosed = T.closedN - 1, runStart = c.now && c.now.n ? lastClosed - c.now.n + 1 : Infinity, gc = h.svg('g', { 'class': 'ct-count-l', 'clip-path': 'url(#czClip)' });
      c.marks.forEach(function (m) {
        if (m.i < a || m.i >= b) return;
        var nine = m.kind === 'setup' && m.n === 9, th = m.kind === 'countdown' && m.n === 13;
        if (!nine && !th && !(m.kind === 'setup' && m.i >= runStart && step >= 7)) return;
        var r = all[m.i], up = m.dir === 'up', mx = h.X(m.i), big = nine || th, off = th ? 30 : big ? 13 : 7;
        var my = up ? h.Y(r[2]) - off : h.Y(r[3]) + off + 7;
        if (big) gc.appendChild(h.svg('circle', { cx: mx, cy: my - 3.5, r: 8.5, 'class': th ? 'ct-r13' : 'ct-r9' }));
        gc.appendChild(h.svg('text', { x: mx, y: my, 'text-anchor': 'middle', 'class': 'ct-n' + (th ? ' th' : nine ? ' nine' : '') }, String(m.n)));
      });
      s.appendChild(gc);
    }
  }

  // ── wiring into their page ─────────────────────────────────────────────────────────────────────────────
  var bind0 = DESK.bind, render0 = DESK.render, reset0 = DESK.reset, pool0 = DESK.onPool, candle0 = DESK.onCandle;
  DESK.bind = function (s, h) {
    S = s; H = h;
    var r0 = h.redraw; h.redraw = function () { r0(); syncDetail(); };
    bind0(s, h);
  };
  DESK.render = function (d) { render0(d); hero(); regroup(); syncDetail(); loadChips(); };
  DESK.reset = function () {
    reset0(); T.trend = T.count = null; T.sig = ''; T.pool = null;
    var b = $('ctHero'), c = $('czaRead'); if (b) b.textContent = ''; if (c) c.setAttribute('data-ct', '');
  };
  DESK.onPool = function (m) { pool0(m); T.pool = m; soon(); if (H) H.redraw(); };
  DESK.onCandle = function () { candle0(); soon(); };
  if (window.czaMA) {
    var maDraw0 = window.czaMA.draw;
    window.czaMA.draw = function (s, geo, state, h) { maDraw0.apply(this, arguments); try { drawLayer(s, geo, state, h); } catch (e) { if (window.console) console.error('trend layer', e); } };
  }
  window.czaTrend = {
    // their socket answered TOO_LITTLE_HISTORY: the timeframe opens anyway, on candles built from shorter ones
    young: function (m, state, render, setTf, fallback) {
      var tf = state.tf, w = who();
      if (ORDER.indexOf(tf) <= 0 || !window.czaMockFrames) return false;
      compose(tf).then(function (r) {
        if (!S || S.tf !== tf || who() !== w) return;
        if (!r) { if (fallback) fallback(m); return; }
        if (r.rows.length < 40) state.span = 0;            // a short series shows every candle (their default view hides the oldest behind the right gap)
        render({ type: 'analysis', identity: m.identity || r.identity, symbol: r.symbol, timeframe: tf, candles: r.rows, candles_used: r.rows.length,
                 last_candle_forming: true, setups: [], structures: [], patterns: [], indicators: {}, ct_composed: { from: r.from, n: r.rows.length } }, true);
        var lv = $('czaLive'), lt = $('czaLiveTxt');
        if (lv && lt) { lv.className = 'cza-live on'; lt.textContent = 'built from ' + tfLbl(r.from); }
      }, function () { if (fallback) fallback(m); });
      return true;
    },
    state: T
  };
})();
