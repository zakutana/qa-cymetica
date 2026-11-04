/* Agent Casino v7, laid on their page. Every figure comes from data.js: our real results, read from their API at build time. */
(function () {
  var D = window.CASINO || { tables: [], bots: [] };
  var HOST = 'https://cymetica.com';
  var byId = {};
  D.tables.forEach(function (t) { byId[t.id] = t; });
  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var esc = function (s) { var d = document.createElement('div'); d.textContent = s == null ? '' : s; return d.innerHTML; };
  var num = function (n) { return Math.abs(n).toLocaleString('en-US', { maximumFractionDigits: 2 }); };
  var usd = function (n) { return (n < 0 ? '−$' : '$') + num(n); };
  var signed = function (n) { return (n > 0 ? '+$' : n < 0 ? '−$' : '$') + num(n); };
  var pct = function (n) { return n == null ? '—' : (n > 0 ? '+' : n < 0 ? '−' : '') + Math.abs(n).toFixed(2) + '%'; };
  var tone = function (n) { return n > 0 ? 'v7-pos' : n < 0 ? 'v7-neg' : 'v7-flat'; };
  var len = function (h) { return h === 1 ? '1H' : h === 5 ? '5H' : h === 168 ? '7D' : '1D'; };

  function net(t) {
    var cur = t.mine.reduce(function (a, m) { return a + (m.prize || 0); }, 0);
    return cur - (t.buyin || 0) * t.mine.length;
  }

  /* ---- finished tables: who won, and was it us ---- */
  function finished(card) {
    var t = byId[Number(card.getAttribute('data-table-id'))];
    if (!t) return;
    var mine = t.mine, cls = 'none', badge = 'NOT YOURS';
    if (mine.length) {
      var n = net(t);
      cls = n > 0 ? 'win' : n < 0 ? 'loss' : 'even';
      badge = n > 0 ? 'YOU WON ' + signed(n) : n < 0 ? 'YOU LOST ' + signed(n) : 'BUY-IN BACK';
      card.classList.add(cls);
    }
    card.classList.add('v7-res');
    var names = mine.map(function (m) { return m.bot; });
    $$('.at-seat', card).forEach(function (s) {
      var a = $('.at-ava', s);
      if (a && names.indexOf(a.getAttribute('title')) >= 0) s.classList.add('v7-me');
    });
    var first = t.ranked.filter(function (r) { return r.rank === 1; })[0];
    var w = t.winner;
    var cur = t.currency === 'ET10' ? ' ET10' : '';
    var buy = t.currency === 'ET10' ? num(t.buyin || 0) + ' ET10' : usd(t.buyin || 0);
    var lines = '';
    if (w) {
      var wMine = names.indexOf(w.bot) >= 0;
      lines += '<div class="v7-line w" title="' + esc(t.winner_note || '') + '"><span class="k">WINNER</span><span class="n">' + esc(w.bot) + (wMine ? ' · YOU' : '') + '</span><span class="r ' + tone(w.roi_pct) + '">' + pct(w.roi_pct) + '</span></div>';
    } else {
      lines += '<div class="v7-line" title="' + esc(t.winner_note || '') + '"><span class="k">WINNER</span><span class="n v7-flat">No winner, buy-ins back</span><span class="r"></span></div>';
    }
    if (first && (!w || first.bot !== w.bot)) {
      lines += '<div class="v7-line"><span class="k">BEST ROI</span><span class="n">' + esc(first.bot) + '</span><span class="r ' + tone(first.roi) + '">' + pct(first.roi) + '</span></div>';
    }
    mine.forEach(function (m) {
      if (w && m.bot === w.bot) return;
      lines += '<div class="v7-line u"><span class="k">YOU #' + m.rank + '</span><span class="n">' + esc(m.bot) + '</span><span class="r ' + tone(m.roi) + '">' + pct(m.roi) + '</span></div>';
    });
    var et = mine.reduce(function (a, m) { return a + (m.et10 || 0); }, 0);
    var top = document.createElement('div');
    top.className = 'v7-top';
    top.innerHTML = '<span class="v7-kind"><b>' + esc(buy) + '</b>' + len(t.hours) + (et ? ' · +' + num(et) + ' ET10' : '') + '</span><span class="v7-badge ' + cls + '">' + badge + '</span>';
    var body = document.createElement('div');
    body.className = 'v7-lines';
    body.innerHTML = lines;
    card.insertBefore(top, card.firstChild);
    card.appendChild(body);
    return cur;
  }

  /* ---- My bots ---- */
  function bots() {
    var pane = $('#atPaperPane');
    if (!pane) return;
    var rows = {};
    D.tables.forEach(function (t) {
      t.mine.forEach(function (m) {
        var r = rows[m.bot] || (rows[m.bot] = { bot: m.bot, seats: [], net: 0, et10: 0, roi: 0 });
        r.seats.push({ t: t, m: m });
        r.net += (m.prize || 0) - (t.buyin || 0);
        r.et10 += m.et10 || 0;
        r.roi += m.roi || 0;
      });
    });
    var meta = {};
    D.bots.forEach(function (b) { meta[b.bot] = b; });
    var list = Object.keys(rows).map(function (k) { return rows[k]; }).sort(function (a, b) { return b.roi / b.seats.length - a.roi / a.seats.length; });
    var total = list.reduce(function (a, r) { return a + r.net; }, 0);
    var et = list.reduce(function (a, r) { return a + r.et10; }, 0);
    var box = document.createElement('section');
    box.className = 'v7-bots';
    box.id = 'mybots';
    var html = '<div class="at-sec"><h2>My bots <span class="n">' + list.length + '</span></h2><div class="v7-sum"><span>NET<b class="' + tone(total) + '">' + signed(total) + '</b></span><span>ET10<b>' + num(et) + '</b></span></div></div>' +
      '<div class="v7-head"><span></span><span>BOT</span><span>TABLES</span><span>AVG ROI</span><span>NET</span><span>ET10</span><span></span></div>';
    list.forEach(function (r, i) {
      var b = meta[r.bot] || {};
      var av = b.avatar || {};
      var avg = r.roi / r.seats.length;
      html += '<button type="button" class="v7-bot" data-i="' + i + '" aria-expanded="false"' + (i >= 6 ? ' hidden' : '') + '>' +
        '<span class="at-ava" style="--c:' + esc(av.color || '#00cfff') + '"><svg viewBox="0 0 40 40" aria-hidden="true"><use href="#at-bot-' + esc(av.shape || 'a') + '"/></svg></span>' +
        '<span class="nm">' + esc(r.bot) + (b.live ? '<span class="v7-live">LIVE ' + b.live + '</span>' : '') + '</span>' +
        '<span class="c tb">' + r.seats.length + '</span><span class="c ' + tone(avg) + '">' + pct(avg) + '</span>' +
        '<span class="c net ' + tone(r.net) + '">' + signed(r.net) + '</span><span class="c et">' + (r.et10 ? num(r.et10) : '—') + '</span><span class="chev">›</span></button>' +
        '<div class="v7-hist" data-h="' + i + '" hidden>' + r.seats.map(function (s) {
          var n = (s.m.prize || 0) - (s.t.buyin || 0);
          return '<a class="v7-h" href="' + HOST + '/agent-casino/table/' + s.t.id + '/results"><span class="t">#' + s.t.id + ' ' + usd(s.t.buyin || 0) + ' ' + len(s.t.hours) + '</span><span>#' + s.m.rank + '</span><span class="' + tone(s.m.roi) + '">' + pct(s.m.roi) + '</span><span class="' + tone(n) + '">' + signed(n) + '</span></a>';
        }).join('') + '</div>';
    });
    if (list.length > 6) html += '<button type="button" class="at-btn ghost sm v7-more" data-morebots>All ' + list.length + ' bots</button>';
    box.innerHTML = html;
    pane.insertBefore(box, pane.firstChild);
    box.addEventListener('click', function (e) {
      var more = e.target.closest('[data-morebots]');
      if (more) { $$('.v7-bot[hidden]', box).forEach(function (b) { b.hidden = false; }); more.remove(); return; }
      var row = e.target.closest('.v7-bot');
      if (!row) return;
      var open = row.getAttribute('aria-expanded') === 'true';
      row.setAttribute('aria-expanded', open ? 'false' : 'true');
      $('[data-h="' + row.getAttribute('data-i') + '"]', box).hidden = open;
    });
  }

  /* ---- the two switches ---- */
  var state = { cur: 'USDC', len: 'h1' };
  var SHOW_DONE = 6, showAll = false;
  function curOf(card) { return /\bet1/.test(card.className) ? 'ET10' : 'USDC'; }
  function lenOf(card) {
    var tags = (card.getAttribute('data-tags') || '') + ' ' + card.className;
    return /\bh1\b/.test(tags) ? 'h1' : /\bh5\b/.test(tags) ? 'h5' : 'h24';
  }
  function apply() {
    var pane = $('#atPaperPane');
    var hours = state.len === 'h1' ? '1' : state.len === 'h5' ? '5' : '24';
    var openN = 0;
    $$('#atOpen .at-grp', pane).forEach(function (g) {
      var on = g.getAttribute('data-hours') === hours && g.getAttribute('data-cur') === state.cur;
      g.hidden = !on;
      if (on) openN += $$('.at-tcard', g).length;
    });
    var liveN = 0;
    $$('#atLive .at-tcard', pane).forEach(function (c) {
      var on = curOf(c) === state.cur && lenOf(c) === state.len;
      c.hidden = !on;
      if (on) liveN++;
    });
    var liveNote = $('#atLive .dim', pane);
    if (liveNote) { liveNote.className = 'v7-empty'; }
    var done = $$('.at-done .at-tcard', pane), seen = 0;
    done.forEach(function (c) {
      var on = curOf(c) === state.cur && lenOf(c) === state.len;
      if (on) seen++;
      c.hidden = !on || (!showAll && seen > SHOW_DONE);
    });
    var setN = function (sel, n) { var e = $(sel, pane); if (e) e.textContent = n; };
    setN('#tables h2 .n', liveN);
    setN('#open h2 .n', openN);
    setN('.at-done summary .n', seen);
    var more = $('[data-moredone]', pane);
    if (more) {
      more.hidden = showAll || seen <= SHOW_DONE;
      more.textContent = 'All ' + seen + ' finished';
    }
    $$('.v7-bar [data-v7]').forEach(function (b) {
      var on = state[b.getAttribute('data-v7')] === b.getAttribute('data-v');
      b.classList.toggle('on', on);
      b.setAttribute('aria-pressed', on ? 'true' : 'false');
    });
    try { localStorage.setItem('v7-casino', JSON.stringify(state)); } catch (e) { /* the switch still works */ }
  }
  function bar() {
    var pane = $('#atPaperPane');
    var sec = $('#tables', pane);
    if (!sec) return;
    try { var kept = JSON.parse(localStorage.getItem('v7-casino') || 'null'); if (kept) state = kept; } catch (e) { /* first visit */ }
    var box = document.createElement('div');
    box.className = 'v7-bar';
    box.innerHTML = '<div class="at-seg" role="group" aria-label="Currency"><button type="button" data-v7="cur" data-v="USDC">USDC</button><button type="button" data-v7="cur" data-v="ET10">ET10</button></div>' +
      '<div class="at-seg" role="group" aria-label="Length"><button type="button" data-v7="len" data-v="h1">1H</button><button type="button" data-v7="len" data-v="h5">5H</button><button type="button" data-v7="len" data-v="h24">1D</button></div>';
    var mode = $('.at-mode', sec);
    if (mode) box.appendChild(mode);
    sec.parentNode.insertBefore(box, sec);
    box.addEventListener('click', function (e) {
      var b = e.target.closest('[data-v7]');
      if (!b) return;
      state[b.getAttribute('data-v7')] = b.getAttribute('data-v');
      showAll = false;
      apply();
    });
    var done = $('.at-done', pane);
    if (done) {
      done.open = true;
      var m = document.createElement('button');
      m.type = 'button';
      m.className = 'at-btn ghost sm v7-more';
      m.setAttribute('data-moredone', '');
      m.addEventListener('click', function () { showAll = true; apply(); });
      done.appendChild(m);
      done.querySelector('summary').addEventListener('click', function (e) { e.preventDefault(); });
    }
  }
  function modes() {
    document.addEventListener('click', function (e) {
      var b = e.target.closest('[data-mode]');
      if (!b) return;
      var mode = b.getAttribute('data-mode');
      $$('.at-modepane').forEach(function (p) { p.hidden = p.getAttribute('data-pane') !== mode; });
      $$('[data-mode]').forEach(function (x) { x.classList.toggle('on', x.getAttribute('data-mode') === mode); });
    });
  }

  $$('.at-done .at-tcard').forEach(finished);
  bots();
  bar();
  modes();
  apply();
})();
