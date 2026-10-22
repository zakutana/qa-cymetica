/* The /company mockup: the panel that slides in on the Universe's right side when one of our two products is clicked
 * (the map flies to it first, app.js openAd). Gem Screener shows its Gem Tier List -- the one on its own page, the same
 * rows and the same rule, drawn from the same snapshot (uv-snap.js) -- and a Visit button; Agent Casino shows how many
 * agents are at the tables, the money in the pots, one live table's ranking and a Go play link. Numbers first; what
 * explains one is a tooltip. */
(function () {
  'use strict';
  var CO = window.CO = window.CO || {};
  var SNAP = CO.SNAP || { gem: { apps: [] }, casino: {} };

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function usd(n) {
    if (n == null || !isFinite(n)) return '—';
    var a = Math.abs(n);
    if (a >= 1e9) return '$' + (a / 1e9).toFixed(a >= 1e10 ? 1 : 2) + 'B';
    if (a >= 1e6) return '$' + (a / 1e6).toFixed(1) + 'M';
    if (a >= 1e3) return '$' + (a / 1e3).toFixed(0) + 'K';
    return '$' + a.toFixed(0);
  }
  // the page's own: 34x, 9.9x, 10x
  function mult(x) { return (x >= 9.95 ? Math.round(x) : Math.round(x * 10) / 10) + 'x'; }
  function dur(h) { if (h == null) return ''; return h >= 24 ? Math.floor(h / 24) + 'd ' + (h % 24) + 'h' : h + 'h'; }
  function pct(v) { return (v > 0 ? '+' : '') + (Math.round(v * 10) / 10).toFixed(1) + '%'; }

  /* ---------------- Gem Screener: the Gem Tier List, as its page builds it ---------------- */
  // S is the page's picks; A to F by the upside its Apps table shows, each app in one row (its TL_TIERS / tierModel)
  var TIERS = [
    { k: 'S', cap: 'picks', size: 38, up: true },
    { k: 'A', cap: '10x+', min: 10, size: 36, up: true },
    { k: 'B', cap: '5 to 10x', min: 5, size: 34, up: true },
    { k: 'C', cap: '2 to 5x', min: 2, size: 30 },
    { k: 'D', cap: '1 to 2x', min: 1, size: 28 },
    { k: 'F', cap: 'under 1x', min: -Infinity, size: 26 }
  ];
  function tierModel(g) {
    var rows = TIERS.map(function (t) { return { t: t, apps: [] }; }), unranked = 0;
    (g.apps || []).forEach(function (e) {
      if (e.pick) { rows[0].apps.push(e); return; }
      if (e.p == null) { unranked++; return; }
      var ur = Math.round(e.p * 10) / 10;                 // the tier follows the number the icon shows (9.96 reads 10x)
      for (var i = 1; i < rows.length; i++) if (ur >= rows[i].t.min) { rows[i].apps.push(e); return; }
    });
    rows.forEach(function (r) { r.apps.sort(function (a, b) { return (b.pr != null ? b.pr : b.p || 0) - (a.pr != null ? a.pr : a.p || 0); }); });
    return { rows: rows, total: (g.apps || []).length, unranked: unranked };
  }
  function ico(e, t) {
    var up = e.p == null ? '' : (e.cap ? '>' : '') + mult(e.p);
    var tip = e.n + '. ' + (up ? 'Upside ' + up + '. ' : '') + 'Market cap ' + usd(e.m) + '. Revenue ' + usd(e.r) + ' in 30 days.';
    var init = String(e.n || e.s || '?').replace(/[^A-Za-z0-9]/g, '').slice(0, 2).toUpperCase() || '?';
    return '<span class="tl-ico" title="' + esc(tip) + '"><span class="tl-c" style="width:' + t.size + 'px;height:' + t.size + 'px" data-init="' + esc(init) + '">' +
      (e.l ? '<img src="' + esc(e.l) + '" alt="" width="' + t.size + '" height="' + t.size + '" loading="lazy" decoding="async">' : esc(init)) + '</span>' +
      '<span class="tl-sym">' + esc(String(e.s || e.n).toUpperCase()) + '</span>' + (t.up && up ? '<span class="tl-up">' + esc(up) + '</span>' : '') + '</span>';
  }
  var GEM_SVG = '<svg viewBox="0 0 24 24" aria-hidden="true" fill="currentColor"><path d="M6 3h12l4 6-10 12L2 9z"/></svg>';
  function gemBody(g) {
    var m = tierModel(g);
    var segs = m.rows.map(function (r) { return '<i class="b-' + r.t.k + '" style="flex:' + Math.max(r.apps.length, 1) + ' 1 0"></i>'; }).join('');
    var rows = m.rows.map(function (r) {
      var t = r.t, n = r.apps.length;
      var items = n ? r.apps.map(function (e) { return ico(e, t); }).join('') + '<span class="tl-ico tl-more" hidden title="The lowest-upside apps of this row are on the Gem Screener\'s Apps tab."><span class="tl-c" style="width:' + t.size + 'px;height:' + t.size + 'px">+0</span><span class="tl-sym">more</span></span>'
        : '<span class="tl-none">none today</span>';
      return '<div class="tl-row t-' + t.k + '" role="group" aria-label="Tier ' + t.k + ', ' + esc(t.cap) + ', ' + n + ' apps">' +
        '<div class="tl-label"><span class="tl-letter">' + t.k + '</span><span class="tl-range">' + (t.k === 'S' ? GEM_SVG : '') + esc(t.cap) + '</span></div><div class="tl-items">' + items + '</div></div>';
    }).join('');
    return '<div class="tl-cap">Live ranking</div><h3 class="tl-title"><span class="tl-live" aria-hidden="true"></span>Gem Tier List</h3>' +
      '<div class="tl-meta"><span><b>' + m.total + '</b> vetted apps · <b>' + usd(g.minRev) + '+</b> revenue in 30 days · ranked by upside</span><span class="tl-bar" aria-hidden="true">' + segs + '</span></div>' + rows +
      '<div class="uvp-asof">as of ' + esc(g.asOf) + '</div>';
  }
  // a row never shows more than two lines of icons: past that the lowest-upside apps fold into one "+N" tile (its page's fitTierRows)
  function fitRows(root) {
    Array.prototype.forEach.call(root.querySelectorAll('.tl-items'), function (box) {
      var icons = Array.prototype.slice.call(box.querySelectorAll('.tl-ico:not(.tl-more)')), more = box.querySelector('.tl-more');
      if (!icons.length || !more) return;
      icons.forEach(function (b) { b.hidden = false; }); more.hidden = true;
      var tops = [];
      icons.forEach(function (b) { if (tops.indexOf(b.offsetTop) < 0) tops.push(b.offsetTop); });
      if (tops.length <= 2) return;
      var cut = icons.length;
      for (var i = 0; i < icons.length; i++) if (icons[i].offsetTop >= tops[2]) { cut = i; break; }
      var keep = Math.max(cut - 1, 1);
      icons.forEach(function (b, i) { b.hidden = i >= keep; });
      more.querySelector('.tl-c').textContent = '+' + (icons.length - keep); more.hidden = false;
    });
  }

  /* ---------------- Agent Casino: the tables, as Agent Tournaments' lobby has them ---------------- */
  function casinoBody(c) {
    var tb = c.table, head = '';
    var kpi = function (n, l, cls, tip) { return '<div class="uvk' + (cls ? ' ' + cls : '') + '"' + (tip ? ' title="' + esc(tip) + '"' : '') + '><b>' + n + '</b><span>' + l + '</span></div>'; };
    head = '<div class="uvks">' + kpi(c.agents, 'agents trading', 'g', 'Bots seated at a table that is running. House bots included.') + kpi(c.live, 'live table' + (c.live === 1 ? '' : 's'), 'c') + kpi(c.openSeats, 'open seats', '', 'Free seats on the ' + (c.open || []).length + ' tables that have not started.') + '</div>' +
      '<div class="uvpot" title="Buy-ins of the tables that are running. ' + esc(c.mode === 'paper' ? 'Paper tables: no real money moves.' : '') + '"><span>In the pots</span><b>' + (c.potEt10 || 0).toLocaleString('en-US') + ' <i>ET10</i></b><b>$' + (c.potUsdc || 0).toLocaleString('en-US') + ' <i>USDC</i></b><em class="uvmode">' + esc(String(c.mode || '').toUpperCase()) + '</em></div>';
    var live = '';
    if (tb) {
      var rows = tb.seats.slice(0, 6).map(function (s, i) {
        var cls = s.roi > 0 ? 'g' : (s.roi < 0 ? 'r' : '');
        return '<div class="uvr"><span class="rk">' + (i + 1) + '</span><i class="av" style="background:' + esc(s.color) + '"></i><span class="bn">' + esc(s.bot) + '</span><b class="' + cls + '">' + pct(s.roi) + '</b></div>';
      }).join('');
      live = '<div class="uvsec"><span class="tl-live" aria-hidden="true"></span>Live table <b>#' + tb.id + '</b> <span class="sub">' + esc(tb.label) + ' · day ' + tb.day + ' of ' + tb.days + ' · ends in ' + dur(tb.hoursLeft) + '</span></div>' +
        '<div class="uvboard">' + rows + (tb.seats.length > 6 ? '<a class="uvmore" href="https://cymetica.com' + esc(tb.url) + '" target="_blank" rel="noopener">+' + (tb.seats.length - 6) + ' more · ' + tb.seated + ' of 10 seats, ' + tb.house + ' house bots ↗</a>' : '') + '</div>';
    } else live = '<div class="uvsec">No table is running right now</div>';
    var open = (c.open || []).map(function (t) {
      return '<a class="uvchip" href="https://cymetica.com' + esc(t.url) + '" target="_blank" rel="noopener" title="' + esc(t.free + ' free seats · ' + t.days + ' day' + (t.days === 1 ? '' : 's')) + '"><b>' + esc(t.label) + '</b>' + (t.currency === 'USDC' ? ' $' + t.buyin : '') + '</a>';
    }).join('');
    return head + live + (open ? '<div class="uvsec">Open now <span class="sub">pick a seat</span></div><div class="uvchips">' + open + '</div>' : '') + '<div class="uvp-asof">as of ' + esc(c.asOf) + '</div>';
  }

  /* ---------------- Promo Market: Cymetica's building where a company hires promotion (../promo-market) ---------------- */
  // the market's own data file (one model for both pages); the buttons open the market's mockup, the build's /creator-dashboard
  var MARKET = '../promo-market/index.html';
  function promoBody() {
    var M = window.PM && window.PM.market; if (!M) return '<div class="uvsec">The market did not load</div>';
    // what a promoter cares about: what is up for grabs, and what one post and one new user pay (USDC); then the
    // owner's own products that have a brief, with what each brought
    var b = M.briefs.slice(), sum = function (f) { return b.reduce(function (s, x) { return s + f(x); }, 0); };
    var top = b.slice().sort(function (p, q) { return q.per_user - p.per_user; })[0];
    var kpi = function (n, l, cls) { return '<div class="uvk' + (cls ? ' ' + cls : '') + '"><b>' + n + '</b><span>' + l + '</span></div>'; };
    var row = function (x, i, right) { return '<a class="uvr" href="' + MARKET + '#market" target="_blank" rel="noopener"><span class="rk">' + (i + 1) + '</span><i class="av" style="background:#00cfff"></i><span class="bn">' + esc(x.name) + '</span>' + right + '</a>'; };
    var best = b.sort(function (p, q) { return q.left - p.left; }).slice(0, 4).map(function (x, i) {
      return row(x, i, '<b class="g">' + x.left.toLocaleString('en-US') + ' <i class="uvu">USDC · ' + x.per_post + ' / post · ' + x.per_user + ' / user</i></b>'); }).join('');
    var mine = (M.mine || []).filter(function (p) { return p.brief; }).map(function (p) { return M.briefs.filter(function (x) { return x.key === p.brief; })[0]; }).filter(Boolean).map(function (x, i) {
      return row(x, i, '<b>' + x.visitors.toLocaleString('en-US') + ' <i class="uvu">visitors</i> · ' + x.users + ' <i class="uvu">new users</i></b>'); }).join('');
    return '<div class="uvks">' + kpi(sum(function (x) { return x.left; }).toLocaleString('en-US'), 'USDC up for grabs', 'g') + kpi(b.length, 'open briefs', 'c') +
        kpi(top.per_user, 'USDC top per new user') + '</div>' +
      '<div class="uvsec">Most up for grabs <span class="sub">per post · per new user</span></div><div class="uvboard">' + best + '</div>' +
      (mine ? '<div class="uvsec">Your products <span class="sub">what your briefs brought</span></div><div class="uvboard">' + mine + '</div>' : '') +
      '<div class="uvp-asof">as of ' + esc(window.PM.day) + ' · sample briefs</div>';
  }

  var SPEC = {
    promo: { house: true, icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round"><circle cx="12" cy="6" r="2"/><path d="M12 8v13 M8 21h8 M6.5 10.5a7.5 7.5 0 0 1 11 0 M4 7.5a11 11 0 0 1 16 0"/></svg>',
      tag: 'Hire creators, agents and firms', body: promoBody,
      foot: '<a class="uvp-go" href="' + MARKET + '#me/products" target="_blank" rel="noopener">Post a brief <span aria-hidden="true">↗</span></a><a class="uvp-go alt" href="' + MARKET + '#market" target="_blank" rel="noopener">Open the market <span aria-hidden="true">↗</span></a>' },
    gem: { icon: '<svg viewBox="0 0 24 24" fill="currentColor"><path d="M6 3h12l4 6-10 12L2 9z"/></svg>', tag: 'Revenue-driven AI research', go: 'Visit Gem Screener', body: function () { return gemBody(SNAP.gem); } },
    casino: { icon: '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linejoin="round"><path d="M12 2.5 20 7v10l-8 4.5L4 17V7z"/><path d="M12 12 4 7 M12 12l8-5 M12 12v9.5"/></svg>', tag: 'AI agents at the tables', go: 'Go play', body: function () { return casinoBody(SNAP.casino); } }
  };

  function productView(it) {
    var s = SPEC[it.ad.key]; if (!s) return null;
    // who made it, big and first: the company that holds the slot the product stands on (ours, bought by the operator);
    // a click opens its office
    var me = CO.profile ? CO.profile() : {}, who = (CO.S && CO.S.company && CO.S.company.name) || 'My Company';
    // drawn as the plate over a station on the map (style.css .mkb), in the company's colour
    var owner = '<div class="mkrow" style="--acc:' + CO.accentHex(me.accent) + '"><a href="#" class="mkb" data-a="owner" title="Made by ' + esc(who) + ': open its office">' +
      '<span class="mkt">MADE BY</span><span class="mkr">' + esc(who) + '</span><span class="mkp"></span></a></div>';
    // (Cymetica's own building has no maker row: it is the platform's, not a company's)
    return { cls: 'k-' + it.ad.key, acc: CO.accentHex(it.c.accent), icon: s.icon, title: it.c.name,
      sub: esc(s.tag) + ' · ' + esc(CO.uvSlotName(it)), body: (s.house ? '' : owner) + s.body(),
      foot: s.foot || '<a class="uvp-go" href="' + esc(it.ad.url) + '" target="_blank" rel="noopener">' + esc(s.go) + ' <span aria-hidden="true">↗</span></a>' };
  }

  CO.uvPanel = {
    el: null, cur: null,
    width: function () { return this.el ? this.el.offsetWidth : 0; },
    isOpen: function () { return !!this.cur; },
    // a map item (CO.uvPlan's) in, a product or a company; the panel slides in, or just changes its content when one is already open
    show: function (it) {
      var el = this.el || (this.el = document.getElementById('uv-panel')); if (!el) return;
      var v = it.ad ? productView(it) : null; if (!v) return;
      this.cur = it;
      el.style.setProperty('--acc', v.acc);
      el.className = 'uvp ' + v.cls;
      el.innerHTML = '<div class="uvp-h"><span class="uvp-ico">' + v.icon + '</span><div class="uvp-t"><b>' + esc(v.title) + '</b><span>' + v.sub + '</span></div>' +
        '<button type="button" class="uvp-x" data-a="close" title="Close (Esc)">×</button></div>' +
        '<div class="uvp-b">' + v.body + '</div><div class="uvp-f">' + v.foot + '</div>';
      el.hidden = false;
      void el.offsetWidth;                                  // so the slide starts from where it stood
      el.classList.add('on');
      if (it.ad && it.ad.key === 'gem') fitRows(el);
    },
    hide: function () {
      var el = this.el; this.cur = null; if (!el) return;
      el.classList.remove('on');
      setTimeout(function () { if (!CO.uvPanel.cur) el.hidden = true; }, 320);
    },
    refit: function () { if (this.cur && this.cur.ad && this.cur.ad.key === 'gem' && this.el) fitRows(this.el); }
  };

  document.addEventListener('DOMContentLoaded', function () {
    var el = document.getElementById('uv-panel'); if (!el) return;
    CO.uvPanel.el = el;
    // a logo that does not load: the app's initials, as its page does
    el.addEventListener('error', function (e) {
      var t = e.target; if (!t || t.tagName !== 'IMG') return;
      var c = t.parentNode; if (c) c.textContent = c.getAttribute('data-init') || '?';
    }, true);
    window.addEventListener('resize', function () { CO.uvPanel.refit(); });
  });
})();
