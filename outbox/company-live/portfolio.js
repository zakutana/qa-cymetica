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

  // Read again on 2026-10-23 from the live build's own source of the tab, GET /api/v1/company/products: it lists 13, of
  // which these 7 are pages this account created (spec 4, A3: My Agents and Events existed before it asked, Usage, Creator
  // rewards, the communities hub and Airdrop Farmer have no page yet). `builds`: the requests filed for it.
  CO.PORTFOLIO_READ = { at: '2026-10-23', days: 30, src: 'GET /api/v1/company/products' };
  var OURS = [
    { name: 'Gem Screener', path: '/gem-screener', views: 495, visitors: 248, uses: 224, likes: 1, builds: 11 },
    { name: 'Chart Analyzer', path: '/chart-analyzer', views: 728, visitors: 207, uses: 351, likes: 2, builds: 5 },
    { name: 'Agent Tournaments', path: '/agent-tournaments', views: 215, visitors: 62, uses: 145, likes: 2, builds: 5 },
    { name: 'Supply Analyzer', path: '/supply-analyzer', views: 73, visitors: 29, uses: 47, likes: 1, builds: 2 },
    { name: 'Build a Company', path: '/company', views: 37, visitors: 25, uses: 26, likes: 0, builds: 5 },
    { name: 'Team Dump Radar', path: '/team-dump-radar', views: 38, visitors: 21, uses: 12, likes: 1, builds: 2 },
    { name: 'Infiltrator', path: '/infiltrator', views: 20, visitors: 14, uses: 17, likes: 1, builds: 1 }
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
  // Fees brought, per product: the revenue share's measure (uv-data.js, CO.uvRevenue) split over the company's products,
  // so the panels add up to the company's line on the board. Cymetica serves no per-product figure (GET /company/products
  // has `earned`, what it paid, "0") and the split is a SAMPLE: by visitors and uses, skewed per product. `users`: the
  // fees paid by the people who came through it; `volume`: the fees on what was traded through the product itself.
  // `days`: the last 30 days, oldest first, visitors and fees, summing to the 30-day figures.
  var FEES = null;
  function hash(s) { var h = 7; for (var i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) % 100003; return h; }
  function spread(total, w) {
    // whole numbers in proportion to w that add up to total exactly (largest remainder)
    var sw = w.reduce(function (s, x) { return s + x; }, 0) || 1, raw = w.map(function (x) { return total * x / sw; }), out = raw.map(Math.floor);
    var left = total - out.reduce(function (s, x) { return s + x; }, 0);
    raw.map(function (x, i) { return [x - out[i], i]; }).sort(function (a, b) { return b[0] - a[0]; }).slice(0, left).forEach(function (r) { out[r[1]]++; });
    return out;
  }
  CO.appFees = function (a) {
    var S = CO.S || {}, total = CO.uvRevenue ? CO.uvRevenue({ id: 0, status: S.company && S.company.status }) : 0;
    if (!FEES || FEES.total !== total) {
      var apps = CO.apps(), w = apps.map(function (x) { var R = CO.uvRng(hash(x.name)); return (x.visitors + x.uses) * (0.6 + 0.8 * R()); });
      var by = spread(Math.round(total), w);
      FEES = { total: total, of: {} };
      apps.forEach(function (x, i) {
        var R = CO.uvRng(hash(x.name) + 11), f = by[i], users = Math.round(f * (0.35 + 0.4 * R()));
        var wv = [], wf = [];
        for (var d = 0; d < 30; d++) { var g = 0.7 + d / 60; wv.push(g * (0.45 + R())); wf.push(g * (0.3 + R() * 1.4)); }
        var dv = spread(x.visitors, wv), df = spread(f, wf);
        FEES.of[x.name] = { fees: f, users: users, volume: f - users, share: total ? f / total : 0, days: dv.map(function (v, k) { return { v: v, f: df[k] }; }) };
      });
    }
    return FEES.of[a.name] || { fees: 0, users: 0, volume: 0, share: 0, days: [] };
  };
  CO.appFeesTotal = function () { CO.appFees(CO.apps()[0] || { name: '' }); return FEES ? Math.round(FEES.total) : 0; };

  // A product's logo, set by its owner on the Products tab: the picture he picks, cut to a square from its middle and drawn
  // at 160 px (the operator, 2026-10-23: "chci moznost taky pridat si ikonku ke kazdemu produktu. nejake logo"). Until he
  // sets one, the product shows its initials. Kept in this browser, by product name.
  var LKEY = 'co.prodlogo.v1';
  CO.LOGO_PX = 160;
  CO.LOGO_TYPES = ['image/png', 'image/jpeg', 'image/svg+xml', 'image/webp'];
  function logos() { try { return JSON.parse(localStorage.getItem(LKEY) || '{}') || {}; } catch (e) { return {}; } }
  CO.prodLogo = function (name) { return String(logos()[String(name || '').toLowerCase()] || ''); };
  CO.setProdLogo = function (name, url) {
    if (CO.RO) return false;
    var m = logos(), k = String(name || '').toLowerCase();
    if (url) m[k] = url; else delete m[k];
    try { localStorage.setItem(LKEY, JSON.stringify(m)); return true; } catch (e) { return false; }
  };
  CO.prodInitials = function (name) {
    var w = String(name || '?').split(/\s+/).filter(function (x) { return x && !/^(a|an|the|of|for|and)$/i.test(x); });
    if (!w.length) w = ['?'];
    return (w.length > 1 ? w[0][0] + w[1][0] : w[0].slice(0, 2)).toUpperCase();
  };
  // read a picked file into the square 160 px PNG the mockup keeps; refuses what is not a picture or is over 2 MB
  CO.readLogo = function (file) {
    return new Promise(function (ok, no) {
      if (!file || CO.LOGO_TYPES.indexOf(file.type) < 0) return no(new Error('PNG, JPG, SVG or WebP only'));
      if (file.size > 2 * 1024 * 1024) return no(new Error('over 2 MB'));
      var fr = new FileReader();
      fr.onerror = function () { no(new Error('could not read the file')); };
      fr.onload = function () {
        var img = new Image();
        img.onerror = function () { no(new Error('not a picture this browser can draw')); };
        img.onload = function () {
          var P = CO.LOGO_PX, cv = document.createElement('canvas'), g = cv.getContext('2d');
          var w = img.naturalWidth || P, h = img.naturalHeight || P, s = Math.min(w, h);
          cv.width = cv.height = P;
          g.imageSmoothingQuality = 'high';
          g.drawImage(img, (w - s) / 2, (h - s) / 2, s, s, 0, 0, P, P);
          ok(cv.toDataURL('image/png'));
        };
        img.src = fr.result;
      };
      fr.readAsDataURL(file);
    });
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
