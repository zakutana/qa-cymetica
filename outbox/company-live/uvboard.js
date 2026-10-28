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
          '<div class="uvb-n"><b>Open slot</b><span>bring ' + usd(b.floor) + ' of revenue · 30 d</span></div><div class="uvb-s"><b>' + pct + '%</b><span>≈ ' + usd(b.pot[i]) + ' / mo</span></div></div>';
      }
      return '<div class="uvb-r pl' + (i + 1) + (r.mine ? ' me' : '') + '"><i class="uvb-rk">' + (i + 1) + '</i>' + CO.stationIcon(r.c.skin, r.c.accent) +
        '<div class="uvb-n">' + name(r.c, r.mine) + '<span>' + usd(r.rev) + ' revenue · 30 d</span></div>' +
        '<div class="uvb-s"><b>' + pct + '%</b><span>≈ ' + usd(r.month) + ' / mo</span></div></div>';
    }).join('');
    var none = !b.top.length, all = b.pot.reduce(function (s, v) { return s + v; }, 0);
    return '<button type="button" class="uvb-pill" data-a="board-fold" title="The top 3 share Cymetica\'s revenue">TOP 3 <i>' + CO.SHARE.join(' · ') + '%</i></button>' +
      '<div class="uvb-in"><i class="uvb-sh"></i><div class="uvb-h"><span class="uvb-live"></span><b>REVENUE SHARE</b><span>TOP 3</span></div>' +
      '<div class="uvb-sub" title="Ranked by the revenue each company brought Cymetica in 30 days: what its users paid on their volume, plays and subscriptions. Its own accounts do not count. Paid monthly in USDC.">' +
        CO.SHARE.join('% · ') + '% of Cymetica revenue</div>' +
      (none ? '<div class="uvb-hero"><b>All 3 slots are open.</b><span>Be the first company to take one.</span></div>' : '') + rows +
      '<div class="uvb-f"><span>' + (none ? 'Up for grabs <b>≈ ' + usd(all) + ' / mo</b>' : 'Platform revenue · 30 d <b>' + usd(b.fees) + '</b>') + ' · qualify at <b>' + usd(b.floor) + '</b></span>' +
        '<button type="button" data-a="board-all">Full leaderboard →</button></div></div>';
  }

  // ---- SEASON 0 (?season0, uv-data.js CO.uvBoard): the same glass, points instead of a share of revenue
  function pts(n) { return Math.round(n).toLocaleString('en-US'); }
  function et10(n) { return Math.round(n).toLocaleString('en-US') + ' ET10'; }
  function k(n) { return n >= 1000 ? (n / 1000).toFixed(n >= 10000 ? 0 : 1) + 'k' : String(n); }
  // what a company's points are made of, small and always the same three: signed-in users, signed-out visitors, trading agents
  // (on the board's narrow rows only the two that fit; all three, with their points, are in the leaderboard and in this tooltip)
  function mix(p) { return '<u title="' + p.users + ' users, ' + p.visitors + ' visitors, $' + k(p.volume) + ' agent volume">' + p.users + ' users · ' + p.visitors + ' visitors</u>'; }
  function hudSeason(b) {
    var K = CO.SEASON;
    var rows = b.prizes.map(function (prize, i) {
      var r = b.top[i];
      if (!r) {
        return '<div class="uvb-r pl' + (i + 1) + ' open"><i class="uvb-rk">' + (i + 1) + '</i><span class="uvb-seat" aria-hidden="true">+</span>' +
          '<div class="uvb-n"><b>Open slot</b><span>bring ' + b.floor + ' pts</span></div><div class="uvb-s"><b>' + k(prize) + '</b><span>ET10</span></div></div>';
      }
      // the board says three things: who, how many points, what they win -- and the prize is the big number (the operator, 2026-10-28);
      // users / visitors / agents are in the leaderboard
      return '<div class="uvb-r pl' + (i + 1) + (r.mine ? ' me' : '') + '"><i class="uvb-rk">' + (i + 1) + '</i>' + CO.stationIcon(r.c.skin, r.c.accent) +
        '<div class="uvb-n">' + name(r.c, r.mine) + '<span>' + pts(r.total) + ' pts</span></div>' +
        '<div class="uvb-s"><b>' + k(prize) + '</b><span>ET10</span></div></div>';
    }).join('');
    var none = !b.top.length;
    return '<button type="button" class="uvb-pill" data-a="board-fold" title="The top 3 of the month win ET10">TOP 3 <i>' + K.name.toUpperCase() + '</i></button>' +
      '<div class="uvb-in"><i class="uvb-sh"></i><div class="uvb-h"><span class="uvb-live"></span><b>' + K.name.toUpperCase() + '</b><span>TOP 3</span></div>' +
      '<div class="uvb-sub" title="Points for real use of a company\'s products this month: 10 per active user (+1 per further active day, at most 20), signed-out visitors count less, trading agents add 1 point per 100 USDC of fee-paying volume. The owner\'s own accounts earn nothing. The prize amounts are a sample: Cymetica sets the prize.">' +
        K.month + ' · most points wins</div>' +
      (none ? '<div class="uvb-hero"><b>All 3 slots are open.</b><span>Be the first company to reach ' + b.floor + ' points.</span></div>' : '') + rows +
      '<div class="uvb-f"><span><b>' + b.left + ' d</b> left · <b>' + b.floor + ' pts</b> to qualify</span>' +
        '<button type="button" data-a="board-all">Full leaderboard →</button></div></div>';
  }
  function tableSeason(mine) {
    var b = CO.uvBoard(mine), K = CO.SEASON, cut = false;
    var line = function (none) { return '<div class="lb-cut"><span>' + b.floor + ' points · the line to qualify' + (none ? ' · nobody above it yet' : '') + '</span></div>'; };
    var rows = b.rows.map(function (r, i) {
      var right = r.prize ? '<b class="sh">' + pts(r.total) + '</b><span>' + et10(r.prize) + '</span>'
        : r.qualifies ? '<b class="sh ok">' + pts(r.total) + '</b><span class="ok">qualifies</span>' : '<b class="sh dim">' + pts(r.total) + '</b><span>' + (b.floor - r.total) + ' to qualify</span>';
      var pre = !cut && !r.qualifies ? (cut = true, line(i === 0)) : '';
      return pre + '<div class="lb-r s0' + (r.prize ? ' top pl' + r.rank : '') + (r.mine ? ' me' : '') + (r.qualifies ? '' : ' below') + '"><i class="lb-rk">' + r.rank + '</i>' + CO.stationIcon(r.c.skin, r.c.accent) +
        '<div class="lb-n">' + name(r.c, r.mine) + '</div>' +
        '<div class="lb-v" title="' + r.p.users + ' active users: ' + r.p.pu + ' points">' + r.p.users + '<small>' + pts(r.p.pu) + ' pts</small></div>' +
        '<div class="lb-v" title="signed-out returning visitors, at most 25% of the signed-in points">' + r.p.visitors + '<small>' + pts(r.p.pv) + ' pts</small></div>' +
        '<div class="lb-v" title="fee-paying volume of the company\'s own agents, 1 point per 100 USDC, at most 30% of the company\'s points">$' + k(r.p.volume) + '<small>' + pts(r.p.pa) + ' pts</small></div>' +
        '<div class="lb-s">' + right + '</div></div>';
    }).join('');
    var seats = b.prizes.map(function (prize, i) {
      return '<div class="lb-seat pl' + (i + 1) + '"><i>' + (i + 1) + '</i><b>' + pts(prize) + '</b><span>ET10</span></div>';
    }).join('');
    return '<div class="mh lbh"><span class="uvb-live"></span><h3>' + K.name.toUpperCase() + ' · ' + K.month.split(' ')[0].toUpperCase() + '</h3><span class="lbt">LEADERBOARD</span><button class="btn" data-a="close">×</button></div>' +
      '<div class="lb-rule"><div class="lb-seats">' + seats + '</div>' +
        '<div class="lb-who"><h4>Who gets a slot</h4>' +
          '<div class="lb-c"><i>1</i><b>Top 3</b><span>by points this month; ' + b.left + ' days left</span></div>' +
          '<div class="lb-c"><i>2</i><b>' + b.floor + '+</b><span>points in the month, or the slot stays open</span></div>' +
          '<div class="lb-c"><i>3</i><b>Month end</b><span>the ranking decides; then every company starts again from zero</span></div>' +
          '<p>A user counts once they used a product on 2 different days: 10 points, +1 per further active day, at most 20. Visitors without an account: 1 point each, at most 25% of the signed-in points. Trading agents: 1 point per 100 USDC of fee-paying volume, at most 30%. The owner\'s own accounts earn nothing. The ET10 amounts are a sample.</p></div></div>' +
      '<div class="lb-head s0"><span>#</span><span></span><span>Company</span><span>Users</span><span>Visitors</span><span>Agents</span><span>Points</span></div>' +
      '<div class="lb">' + rows + (cut ? '' : line(false)) + '</div>';
  }

  var last = '';
  CO.uvBoardRender = function (mine) {
    var el = document.getElementById('uv-board'); if (!el || !CO.uvBoard) return;
    var b0 = CO.uvBoard(mine), html = b0.season ? hudSeason(b0) : hud(b0);
    if (html !== last) { el.innerHTML = html; last = html; }
  };

  // the full leaderboard, for the modal: every company, the fees it brought, its share or how far it is from the floor. On top,
  // big, who gets a seat ("zretelneji vysvetli nebo zvetsi kdo ma pravo na sloty", 2026-10-23): the three seats and what
  // each pays, the three conditions, what counts as fees brought; in the list, the line at the floor
  CO.uvBoardTable = function (mine) {
    if (CO.SEASON0) return tableSeason(mine);
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
        '<div class="lb-who"><h4>Who gets a slot</h4>' +
          '<div class="lb-c"><i>1</i><b>Top 3</b><span>by revenue brought to Cymetica in the last 30 days</span></div>' +
          '<div class="lb-c"><i>2</i><b>' + usd(b.floor) + '+</b><span>of revenue in those 30 days, or the slot stays open</span></div>' +
          '<div class="lb-c"><i>3</i><b>Month end</b><span>the ranking then decides; paid in USDC from that month\'s revenue</span></div>' +
          '<p>Revenue brought = what Cymetica earned from the users your products brought: their trading volume, plays and subscriptions. Revenue from your own accounts does not count.</p></div></div>' +
      '<div class="lb-head"><span>#</span><span></span><span>Company</span><span>Revenue brought · 30 d</span><span>Share</span></div>' +
      '<div class="lb">' + rows + (cut ? '' : line(false)) + '</div>';
  };
})();
