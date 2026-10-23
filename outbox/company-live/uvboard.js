/* The /company mockup: the Universe's revenue-share board (the operator, 2026-10-22). A HUD fixed over the map's top-left,
 * glass you see the galaxy through, that never moves with it: the top 3 companies by the fees they brought Cymetica in 30 days, each with its share
 * of every fee on Cymetica (5% / 3% / 1%) and about what that pays a month; under it the full leaderboard. Every figure
 * comes from CO.uvBoard (uv-data.js), one model, so the board, the leaderboard and the gold pulses agree. */
(function () {
  'use strict';
  var CO = window.CO = window.CO || {};

  function esc(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function usd(n) { return '$' + Math.round(n).toLocaleString('en-US'); }
  var LOCK = '<svg class="lk" viewBox="0 0 12 12" aria-hidden="true"><path d="M3.5 5.2V3.8a2.5 2.5 0 0 1 5 0v1.4" fill="none" stroke="currentColor" stroke-width="1.3"/><rect x="2.4" y="5.2" width="7.2" height="5.3" rx="1.2" fill="currentColor"/></svg>';
  function name(c, mine) {
    return '<b>' + (!c.public && !mine ? LOCK : '') + esc(c.name) + '</b>' + (mine ? '<em class="you">YOU</em>' : '');
  }

  // the HUD: three places. One nobody holds is an open seat that shows what it pays a month and what it takes ("neco
  // motivacniho", 2026-10-23: at first nobody will have reached the floor), and with no seat taken at all the board says so
  function hud(b) {
    var rows = CO.SHARE.map(function (pct, i) {
      var r = b.top[i];
      if (!r) {
        return '<div class="uvb-r pl' + (i + 1) + ' open"><i class="uvb-rk">' + (i + 1) + '</i><span class="uvb-seat" aria-hidden="true">+</span>' +
          '<div class="uvb-n"><b>Open seat</b><span>bring ' + usd(b.floor) + ' in fees · 30 d</span></div><div class="uvb-s"><b>' + pct + '%</b><span>≈ ' + usd(b.pot[i]) + ' / mo</span></div></div>';
      }
      return '<div class="uvb-r pl' + (i + 1) + (r.mine ? ' me' : '') + '"><i class="uvb-rk">' + (i + 1) + '</i>' + CO.stationIcon(r.c.skin, r.c.accent) +
        '<div class="uvb-n">' + name(r.c, r.mine) + '<span>' + usd(r.rev) + ' fees · 30 d</span></div>' +
        '<div class="uvb-s"><b>' + pct + '%</b><span>≈ ' + usd(r.month) + ' / mo</span></div></div>';
    }).join('');
    var none = !b.top.length, all = b.pot.reduce(function (s, v) { return s + v; }, 0);
    return '<button type="button" class="uvb-pill" data-a="board-fold" title="The top 3 get a share of every fee on Cymetica">TOP 3 <i>' + CO.SHARE.join(' · ') + '%</i></button>' +
      '<div class="uvb-in"><i class="uvb-sh"></i><div class="uvb-h"><span class="uvb-live"></span><b>REVENUE SHARE</b><span>TOP 3</span></div>' +
      '<div class="uvb-sub" title="Ranked by the fees each company brought Cymetica in 30 days: what its users paid in fees on their volume, plays and subscriptions. Its own accounts do not count. Paid monthly in USDC.">' +
        CO.SHARE.join('% · ') + '% of every fee on Cymetica</div>' +
      (none ? '<div class="uvb-hero"><b>All 3 seats are open.</b><span>Be the first company to take one.</span></div>' : '') + rows +
      '<div class="uvb-f"><span>' + (none ? 'Up for grabs <b>≈ ' + usd(all) + ' / mo</b>' : 'Platform fees · 30 d <b>' + usd(b.fees) + '</b>') + ' · qualify at <b>' + usd(b.floor) + '</b></span>' +
        '<button type="button" data-a="board-all">Full leaderboard →</button></div></div>';
  }

  var last = '';
  CO.uvBoardRender = function (mine) {
    var el = document.getElementById('uv-board'); if (!el || !CO.uvBoard) return;
    var html = hud(CO.uvBoard(mine));
    if (html !== last) { el.innerHTML = html; last = html; }
  };

  // the full leaderboard, for the modal: every company, the fees it brought, its share or how far it is from the floor. On top,
  // big, who gets a seat ("zretelneji vysvetli nebo zvetsi kdo ma pravo na sloty", 2026-10-23): the three seats and what
  // each pays, the three conditions, what counts as fees brought; in the list, the line at the floor
  CO.uvBoardTable = function (mine) {
    var b = CO.uvBoard(mine), cut = false;
    var line = function (none) { return '<div class="lb-cut"><span>' + usd(b.floor) + ' · the line to qualify' + (none ? ' · nobody above it yet' : '') + '</span></div>'; };
    var rows = b.rows.map(function (r, i) {
      var right = r.share ? '<b class="sh">' + r.share + '%</b><span>≈ ' + usd(r.month) + ' / mo</span>'
        : r.qualifies ? '<span class="ok">qualifies</span>' : '<span>' + usd(b.floor - r.rev) + ' to qualify</span>';
      var pre = !cut && !r.qualifies ? (cut = true, line(i === 0)) : '';
      return pre + '<div class="lb-r' + (r.share ? ' top pl' + r.rank : '') + (r.mine ? ' me' : '') + (r.qualifies ? '' : ' below') + '"><i class="lb-rk">' + r.rank + '</i>' + CO.stationIcon(r.c.skin, r.c.accent) +
        '<div class="lb-n">' + name(r.c, r.mine) + '</div><div class="lb-v">' + usd(r.rev) + '</div><div class="lb-s">' + right + '</div></div>';
    }).join('');
    // (who holds a seat is the list's first rows; under the amount it was one line too many: "to podtim uz nezobrazuj")
    var seats = CO.SHARE.map(function (pct, i) {
      return '<div class="lb-seat pl' + (i + 1) + '"><i>' + (i + 1) + '</i><b>' + pct + '%</b><span>≈ ' + usd(b.pot[i]) + ' / mo</span></div>';
    }).join('');
    // the board's own glass and type (the modal card's class lbg, uvpanel.css: "udelat to husté krasne jako ten postranni panel")
    return '<div class="mh lbh"><span class="uvb-live"></span><h3>REVENUE SHARE</h3><span class="lbt">LEADERBOARD</span><button class="btn" data-a="close">×</button></div>' +
      '<div class="lb-rule"><div class="lb-seats">' + seats + '</div>' +
        '<div class="lb-who"><h4>Who gets a seat</h4>' +
          '<div class="lb-c"><i>1</i><b>Top 3</b><span>by fees brought to Cymetica in the last 30 days</span></div>' +
          '<div class="lb-c"><i>2</i><b>' + usd(b.floor) + '+</b><span>of fees in those 30 days, or the seat stays open</span></div>' +
          '<div class="lb-c"><i>3</i><b>Month end</b><span>the ranking then decides; paid in USDC from that month\'s fees</span></div>' +
          '<p>Fees brought = what Cymetica earned from the users your products brought: their trading volume, plays and subscriptions. Fees paid by your own accounts do not count.</p></div></div>' +
      '<div class="lb-head"><span>#</span><span></span><span>Company</span><span>Fees brought · 30 d</span><span>Share</span></div>' +
      '<div class="lb">' + rows + (cut ? '' : line(false)) + '</div>';
  };
})();
