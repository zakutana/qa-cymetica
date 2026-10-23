/* The /company mockup: the company's Products and its Vault.
 *
 * Products: the products the company (or the account it runs on) built through Build it Better. Their numbers are
 * REAL, read from Cymetica on 2026-10-23: which ones are ours from GET /api/v1/company/products, the figures from
 * GET /api/v1/traffic/mine?days=30 (the page /traffic/mine). Of its vocabularies (visits, unique visitors, views,
 * visitors, uses) one is shown, in a word a degen knows: People = its `unique_visitors` (the operator, 2026-10-23:
 * "vyber z toho nejpodstatnejsi ... a moc se v tom nevyznam co je co").
 *
 * What an app EARNS its owner is live since then: /traffic/mine's `referrals` pays 1,000 ET10 for each new user one's
 * pages bring (what the operator asked for on 2026-10-18, MSG-0192), 0 so far. Fees brought is the revenue share's
 * measure (uv-data.js), a sample split per product: Cymetica serves no fees per product.
 *
 * Vault: everything the company earned, in two piles. ET10 = what its departments earned (accepted bugs, prizes,
 * the League) + the new-user reward; USDC = its balance. Always private.
 */
(function () {
  'use strict';
  var CO = window.CO = window.CO || {};

  // The 7 of /company/products' 13 that are pages this account created (spec 4, A3: My Agents and Events existed before it
  // asked; Usage, Creator rewards, the communities hub and Airdrop Farmer have no page yet), with /traffic/mine's row for
  // each: people (`unique_visitors`), visits, AI-agent visits, and the visits that came from Cymetica's own pages
  // (`from_site`). Gem Screener has a second row, /gem-screener/app (162 people); its people are not added, since a
  // person who opens both would count twice.
  CO.PORTFOLIO_READ = { at: '2026-10-23', days: 30, src: 'GET /api/v1/traffic/mine?days=30' };
  var OURS = [
    { name: 'Gem Screener', path: '/gem-screener', people: 177, visits: 634, ai: 663, fromSite: 547 },
    { name: 'Chart Analyzer', path: '/chart-analyzer', people: 127, visits: 788, ai: 445, fromSite: 745 },
    { name: 'Build a Company', path: '/company', people: 73, visits: 378, ai: 42, fromSite: 351 },
    { name: 'Agent Tournaments', path: '/agent-tournaments', people: 70, visits: 366, ai: 52, fromSite: 359 },
    { name: 'Supply Analyzer', path: '/supply-analyzer', people: 20, visits: 69, ai: 50, fromSite: 60 },
    { name: 'Team Dump Radar', path: '/team-dump-radar', people: 20, visits: 27, ai: 34, fromSite: 19 },
    { name: 'Infiltrator', path: '/infiltrator', people: 6, visits: 15, ai: 21, fromSite: 3 }
  ];
  // the account's people per day over the same 30 days (`unique_daily`, 09-24 to 10-23, the last day not over): no
  // product has its own series, so each product's 30 days take this shape
  var PEOPLE_DAILY = [12, 2, 2, 17, 21, 26, 21, 44, 26, 31, 19, 63, 38, 27, 23, 14, 28, 41, 39, 63, 46, 32, 28, 37, 29, 20, 24, 17, 26, 6];
  // /traffic/mine's `referrals`: 1,000 ET10 for each new user your pages bring, credited at 05:20 UTC; none so far.
  // Account-wide: Cymetica does not say which product brought whom.
  CO.REFERRAL = { et10PerUser: 1000, attributed: 0, qualified: 0, earnedEt10: 0, pendingEt10: 0, at: '05:20 UTC' };

  // the apps of the company on the page: ours carry the real numbers; a fresh or an example company has none.
  // `todayPeople` counts who arrives while the page is open, on top of the 30-day read.
  var APPS = null;
  CO.apps = function () {
    if (!APPS) APPS = (CO.MODE === 'ours' ? OURS : []).map(function (a) { return Object.assign({ url: 'https://cymetica.com' + a.path, todayPeople: 0, newUsers: 0 }, a); });
    return APPS;
  };
  // what an app has earned its owner: the new-user reward (0 until Cymetica says which product brought a user)
  CO.appEarn = function (a) { return { et10: (a.newUsers || 0) * CO.REFERRAL.et10PerUser, usdc: 0 }; };
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
  // has `earned`, what it paid, "0") and the split is a SAMPLE: by people, skewed per product. One number: the fees on
  // what the people it brought traded and on what was traded through it (the operator could not tell a split apart).
  // `days`: the last 30 days, oldest first, the product's people in the account's daily shape (PEOPLE_DAILY).
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
      var apps = CO.apps(), w = apps.map(function (x) { var R = CO.uvRng(hash(x.name)); return x.people * (0.6 + 0.8 * R()); });
      var by = spread(Math.round(total), w);
      FEES = { total: total, of: {} };
      apps.forEach(function (x, i) {
        FEES.of[x.name] = { fees: by[i], share: total ? by[i] / total : 0, days: spread(x.people, PEOPLE_DAILY).map(function (v) { return { v: v }; }) };
      });
    }
    return FEES.of[a.name] || { fees: 0, share: 0, days: [] };
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

  // while the page is open, people keep arriving at the apps: now and then a person, more often at the busier ones
  setInterval(function () {
    var apps = CO.apps(); if (!apps.length || document.hidden || Math.random() < 0.4) return;
    var all = apps.reduce(function (s, x) { return s + x.people; }, 0), r = Math.random() * all, a = apps[0];
    for (var i = 0; i < apps.length; i++) { r -= apps[i].people; if (r < 0) { a = apps[i]; break; } }
    a.todayPeople += 1;
    if (CO.emit) CO.emit('vault');
  }, 7000);
})();
