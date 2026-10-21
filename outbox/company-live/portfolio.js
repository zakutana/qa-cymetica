/* The /company mockup: the company's Portfolio and its Vault.
 *
 * Portfolio: the products the company (or the account it runs on) built through Build it Better. Their numbers are
 * REAL, read from Cymetica: GET /api/v1/build-it-better/apps/leaderboard, 30 days, on 2026-10-18 (views, visitors,
 * uses, likes; "visitors" is theirs: distinct daily visitors, summed over the days). Which apps are ours is our own
 * record of the requests we filed.
 *
 * What the apps would EARN is not live: Build it Better apps pay nothing today (their llms.txt: "Build it Better apps
 * are free to use; their public numbers are traffic and likes, not revenue"). The operator asked Cymetica on
 * 2026-10-18 (MSG-0192) for ET10 for every new user an app brings in, and the concept adds a USDC revenue share. The
 * RATE below is a placeholder that makes the picture, named as one wherever it shows.
 *
 * Vault: everything the company earned, in two piles. ET10 = what its departments earned (accepted bugs, prizes,
 * the League) + the proposed new-user reward; USDC = the proposed revenue share. Always private.
 */
(function () {
  'use strict';
  var CO = window.CO = window.CO || {};

  CO.PORTFOLIO_READ = { at: '2026-10-18', days: 30, src: 'GET /api/v1/build-it-better/apps/leaderboard' };
  var OURS = [
    { name: 'Gem Screener', path: '/gem-screener', views: 449, visitors: 221, uses: 206, likes: 1 },
    { name: 'Chart Analyzer', path: '/chart-analyzer', views: 549, visitors: 175, uses: 300, likes: 2 },
    { name: 'Supply Analyzer', path: '/supply-analyzer', views: 70, visitors: 26, uses: 45, likes: 1 }
  ];
  // placeholders until Cymetica sets real rates: ET10 for each visitor an app brings, USDC for each use
  CO.RATE = { et10PerVisitor: 50, usdcPerUse: 0.02, placeholder: true };

  // the apps of the company on the page: ours carry the real numbers; a fresh or an example company has none.
  // `today` counts what arrives while the page is open, on top of the 30-day read, so the vault visibly grows.
  var APPS = null;
  CO.apps = function () {
    if (!APPS) APPS = (CO.MODE === 'ours' ? OURS : []).map(function (a) { return Object.assign({ url: 'https://cymetica.com' + a.path, todayVisitors: 0, todayUses: 0 }, a); });
    return APPS;
  };
  CO.appEarn = function (a) {
    var v = a.visitors + a.todayVisitors, u = a.uses + a.todayUses;
    return { et10: v * CO.RATE.et10PerVisitor, usdc: u * CO.RATE.usdcPerUse };
  };
  // the two piles, and where they came from
  // The Vault shows everything the owner's Cymetica account holds, ET10 and USDC ("vault je prazdny coz je bug, on ma
  // zobrazovat veskere ET10 a USDC co mam na ucte v balancu na cymetice", 2026-10-21): the live build's tile read
  // "0 ET10 paid" (only the bug bounty it had paid) while `vault.et10_balance` in the same response held the balance.
  // CO.ACCOUNT stands for that balance (the mockup's sample; the app reads it from the account); what the company
  // earned after, by department and by app, is listed under it and added on top.
  CO.ACCOUNT = { et10: 12450, usdc: 86.2 };
  CO.vaultTotals = function () {
    var S = CO.S || {}, depts = 0, et10 = 0, usdc = 0, A = CO.ACCOUNT;
    (S.departments || []).forEach(function (d) { depts += d.et10 || 0; });
    depts = Math.max(depts, S.et10 || 0);
    CO.apps().forEach(function (a) { var e = CO.appEarn(a); et10 += e.et10; usdc += e.usdc; });
    return { et10: A.et10 + depts + et10, usdc: A.usdc + usdc, fromDepts: depts, fromApps: et10, earnedEt10: depts + et10, earnedUsdc: usdc };
  };
  CO.fmtEt = function (n) { return Math.round(n).toLocaleString('en-US'); };
  CO.fmtUsd = function (n) { return n >= 100 ? Math.round(n).toLocaleString('en-US') : n.toFixed(2); };

  // while the page is open, people keep arriving at the apps: now and then a visitor, a use
  setInterval(function () {
    var apps = CO.apps(); if (!apps.length || document.hidden) return;
    var a = apps[Math.floor(Math.random() * apps.length)];
    a.todayUses += 1 + (Math.random() < 0.4 ? 1 : 0);
    if (Math.random() < 0.6) a.todayVisitors += 1;
    if (CO.emit) CO.emit('vault');
  }, 7000);
})();
