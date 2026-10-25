(function () {
  'use strict';
  var S = window.SNAP, P = S.public, A = S.activity, M = S.mine;
  var C = { green: '#00ff88', cyan: '#00cfff', red: '#ff4444', blue: '#3d7bff', text: '#e6f1ff', muted: '#7d8fa8', line: '#1b2536' };
  var MON = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

  function $(id) { return document.getElementById(id); }
  function nf(n) { return n == null ? '–' : Math.round(n).toLocaleString('en-US'); }
  function usd(n) {
    if (n >= 1e6) return '$' + (n / 1e6).toFixed(2) + 'M';
    if (n >= 1e4) return '$' + (n / 1e3).toFixed(1) + 'K';
    return '$' + nf(n);
  }
  function pc(part, whole) { return whole ? (100 * part / whole).toFixed(part / whole < 0.1 ? 1 : 0) + '%' : '–'; }
  function md(day) { var p = day.split('-'); return MON[+p[1] - 1] + ' ' + (+p[2]); }
  function sum(a) { return a.reduce(function (s, x) { return s + x; }, 0); }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]; }); }
  function tip(t) { return '<span class="tip" data-t="' + esc(t) + '">i</span>'; }
  function vals(obj, days) { return days.map(function (d) { return obj[d] || 0; }); }

  var DAYS = P.day_labels, TODAY = P.today;
  var SPAN = md(DAYS[0]) + ' – ' + md(DAYS[DAYS.length - 1]);
  function header(active) {
    return '<div class="top"><h1>' + (active === 'site' ? 'LIVE TRAFFIC' : 'YOUR PAGES') + '</h1>' +
      '<span class="live"><i></i>LIVE · 20 s</span>' +
      '<span class="switch"><a href="index.html" class="' + (active === 'site' ? 'on' : '') + '">Whole site</a>' +
      '<a href="mine.html" class="' + (active === 'mine' ? 'on' : '') + '">Your pages</a></span>' +
      '<span class="sp"></span>' +
      '<span class="span"><em>' + SPAN + '</em> · ' + DAYS.length + ' days · Pacific ' +
      tip('"14 days" is the last 14 full days plus today so far, so ' + DAYS.length + ' days are counted.') + '</span>' +
      '<span class="seg"><b>7D</b><b class="on">14D</b><b>30D</b><b>90D</b></span></div>';
  }
  function units(withActions) {
    var u = '<div class="units">' + (withActions ? '' :
      '<span class="unit"><span class="d" style="background:' + C.text + '"></span><b>VIEW</b> one of your pages opened ' +
      tip('Every time a page is opened: arriving from outside, or clicking through from another page of the site.') + '</span>') +
      '<span class="unit"><span class="d" style="background:' + C.cyan + '"></span><b>ARRIVAL</b> first page opened from outside ' +
      tip('Someone comes from a search, a link or a chat and opens a page. The pages they open after it are not arrivals.') + '</span>' +
      '<span class="unit"><span class="d" style="background:' + C.blue + '"></span><b>REQUEST</b> every page and API call ' +
      tip('Every page load and every API call a page or an agent makes, arrivals included. One page load is often 10+ requests.') + '</span>';
    if (withActions) {
      u += '<span class="unit"><span class="d" style="background:' + C.green + '"></span><b>ACTION</b> something an account did ' +
        tip('A sign-up, an order, a fill, a cloned bot. Counted from the accounts, not from page traffic.') + '</span>';
    }
    return u + '</div>';
  }

  /* ---------- charts: bars (stacked) + optional line, own axis, no dual axis ---------- */
  function chart(el, days, stacks, line) {
    var w = el.clientWidth || 560, h = 190, l = 44, r = 10, t = 10, b = 24;
    var totals = days.map(function (_, i) { return sum(stacks.map(function (s) { return s.values[i]; })); });
    var max = Math.max.apply(null, totals.concat(line ? line.values : []).concat([1]));
    var step = Math.pow(10, Math.floor(Math.log10(max))), top = Math.ceil(max / step) * step;
    if (top / step > 6) { step *= 2; top = Math.ceil(max / step) * step; }
    var y = function (v) { return t + (h - t - b) * (1 - v / top); };
    var bw = (w - l - r) / days.length, svg = '';
    for (var g = 0; g <= top; g += step) {
      svg += '<line x1="' + l + '" x2="' + (w - r) + '" y1="' + y(g) + '" y2="' + y(g) + '" stroke="' + C.line + '"/>' +
        '<text x="' + (l - 8) + '" y="' + (y(g) + 4) + '" fill="' + C.muted + '" font-size="10" text-anchor="end">' +
        (g >= 1e6 ? (g / 1e6) + 'M' : g >= 1e3 ? (g / 1e3) + 'K' : g) + '</text>';
    }
    days.forEach(function (d, i) {
      var x = l + i * bw + bw * 0.18, base = 0;
      stacks.forEach(function (s) {
        var v = s.values[i]; if (!v) return;
        svg += '<rect x="' + x + '" y="' + y(base + v) + '" width="' + (bw * 0.64) + '" height="' + (y(base) - y(base + v)) +
          '" rx="2" fill="' + s.color + '" opacity="' + (d === TODAY ? 0.45 : 0.9) + '"/>';
        base += v;
      });
      if (i % 2 === 0 || days.length < 9) {
        svg += '<text x="' + (l + i * bw + bw / 2) + '" y="' + (h - 7) + '" fill="' + C.muted + '" font-size="10" text-anchor="middle">' + md(d) + '</text>';
      }
    });
    if (line) {
      var pts = line.values.map(function (v, i) { return (l + i * bw + bw / 2) + ',' + y(v); }).join(' ');
      svg += '<polyline points="' + pts + '" fill="none" stroke="' + line.color + '" stroke-width="2"/>';
      line.values.forEach(function (v, i) { svg += '<circle cx="' + (l + i * bw + bw / 2) + '" cy="' + y(v) + '" r="2.4" fill="' + line.color + '"/>'; });
    }
    el.innerHTML = '<svg class="chart" viewBox="0 0 ' + w + ' ' + h + '" width="' + w + '" height="' + h + '">' + svg + '</svg>';
  }

  /* ---------- bar lists ---------- */
  function rows(list, opts) {
    // list: [{n, v, rest?, h24?, cls?, t?}] ; opts: {color, total, totalLabel, h24}
    var max = Math.max.apply(null, list.filter(function (r) { return !r.rest && !r.cls; }).map(function (r) { return r.v; }).concat([1]));
    var cls = opts.h24 ? 'row r24' : 'row';
    var out = '<div class="rows">';
    if (opts.h24) out += '<div class="' + cls + ' head"><span>Area</span><span></span><span class="val">' + DAYS.length + ' days</span><span class="pc">share</span><span class="h24">24 h</span></div>';
    list.forEach(function (r) {
      var share = pc(r.v, opts.total);
      out += '<div class="' + cls + (r.rest ? ' rest' : '') + (r.cls ? ' ' + r.cls : '') + '"><span class="n">' + esc(r.n) + (r.t ? ' ' + tip(r.t) : '') + '</span>' +
        '<span class="bar"><i style="width:' + Math.min(100, 100 * r.v / max).toFixed(1) + '%;background:' + (r.cls === 'gap' ? C.red : r.rest ? C.muted : opts.color) + '"></i></span>' +
        '<span class="val">' + nf(r.v) + '</span><span class="pc">' + (r.cls === 'gap' ? '' : share) + '</span>' +
        (opts.h24 ? '<span class="h24">' + (r.h24 == null ? '–' : nf(r.h24)) + '</span>' : '') + '</div>';
    });
    out += '<div class="' + cls + ' sum"><span class="n">' + opts.totalLabel + '</span><span></span><span class="val">' + nf(opts.total) +
      '</span><span class="pc">100%</span>' + (opts.h24 ? '<span class="h24">' + nf(opts.total24) + '</span>' : '') + '</div>';
    return out + '</div>';
  }

  var SOURCE = { google: 'Google', x: 'X', telegram: 'Telegram', github: 'GitHub', duckduckgo: 'DuckDuckGo', linkedin: 'LinkedIn', internal: 'From the site itself' };
  function sourceName(s) { return s === 'external-withheld' ? 'Referrer hidden' : (SOURCE[s] || s); }
  var HIDDEN_TIP = 'Arrived from another site that did not send its address.';

  /* ---------- requests by area: named areas, then the two catch-alls ---------- */
  function areaList(seg) {
    var range = A.requests[seg].range, day = A.requests[seg]['24h'];
    var by24 = {}; day.forEach(function (r) { by24[r.area] = r.requests; });
    var named = range.filter(function (r) { return r.area !== 'Other pages' && r.area !== 'Everything else'; });
    var out = named.map(function (r) { return { n: r.area, v: r.requests, h24: by24[r.area] }; });
    range.forEach(function (r) {
      if (r.area === 'Other pages') out.push({ n: 'Other pages', v: r.requests, h24: by24[r.area], rest: true, t: 'Pages that are in no named area above. (Your definition goes here.)' });
    });
    range.forEach(function (r) {
      if (r.area === 'Everything else') out.push({ n: 'All other areas', v: r.requests, h24: by24[r.area], rest: true, t: 'Named areas too small for this list, added together.' });
    });
    return { list: out, total: sum(range.map(function (r) { return r.requests; })), total24: sum(day.map(function (r) { return r.requests; })) };
  }

  /* =================================== WHOLE SITE =================================== */
  function site() {
    var hum = areaList('human'), bot = areaList('ai_agent'), ai = P.ai_agents;
    var srcSum = sum(P.by_source.map(function (s) { return s.hits; })), pathSum = sum(P.top_paths.map(function (p) { return p.hits; }));
    var famSum = sum(ai.top.map(function (f) { return f.hits; }));
    var act = {}; A.actions.forEach(function (a) { act[a.key] = a; });
    var vol = A.volume_daily, volC = sum(vals(vol.customers, DAYS)), volP = sum(vals(vol.platform, DAYS)), volE = sum(vals(vol.event_cards, DAYS));
    var n24 = act.clob_notional['24h'];
    var gap = ai.total - bot.total;

    var h = header('site') + units(true);
    h += '<div class="grid g2">' +
      '<div class="kgroup k3"><div class="who"><span class="d" style="width:8px;height:8px;border-radius:2px;background:' + C.cyan + '"></span><b>PEOPLE</b> · ' + SPAN + '</div>' +
      '<div class="k"><div class="l">Arrivals <span class="chip arr">ARR</span></div><div class="v cy">' + nf(P.total) + '</div><div class="s"><b>' + nf(P.daily[TODAY]) + '</b> today so far</div></div>' +
      '<div class="k"><div class="l">Unique people ' + tip('Distinct hashed IPs that arrived. No IP is stored.') + '</div><div class="v gr">' + nf(P.unique_total) + '</div><div class="s"><b>' + (P.total / P.unique_total).toFixed(1) + '</b> arrivals each</div></div>' +
      '<div class="k"><div class="l">Requests <span class="chip req">REQ</span></div><div class="v">' + nf(hum.total) + '</div><div class="s"><b>' + Math.round(hum.total / P.total) + '</b> per arrival</div></div></div>' +
      '<div class="kgroup k3"><div class="who"><span class="d" style="width:8px;height:8px;border-radius:2px;background:' + C.blue + '"></span><b>AI AGENTS</b> · ' + SPAN + '</div>' +
      '<div class="k"><div class="l">Requests <span class="chip req">REQ</span></div><div class="v bl">' + nf(ai.total) + '</div><div class="s"><b>' + nf(ai.daily[TODAY]) + '</b> today so far</div></div>' +
      '<div class="k"><div class="l">Unique agents ' + tip('One per agent family per hashed IP.') + '</div><div class="v gr">' + nf(ai.unique_total) + '</div><div class="s"><b>' + ai.families + '</b> families</div></div>' +
      '<div class="k"><div class="l">Bots filtered ' + tip('Crawlers and scripts that are neither people nor known AI agents. Not counted anywhere else on this page.') + '</div><div class="v mu">' + nf(P.bots) + '</div><div class="s">left out of every number</div></div></div></div>';

    h += '<div class="grid g2 sec">' +
      '<div class="card"><h3>People per day <span class="chip arr">ARR</span><span class="tot">' + nf(P.total) + ' arrivals</span></h3><div id="c-people"></div>' +
      '<div class="legend"><span><i style="background:' + C.cyan + '"></i>Arrivals</span><span><i class="ln" style="background:' + C.text + '"></i>Unique people</span><span>Today is lighter: the day is not over</span></div></div>' +
      '<div class="card"><h3>AI agents per day <span class="chip req">REQ</span><span class="tot">' + nf(ai.total) + ' requests</span></h3><div id="c-agents"></div>' +
      '<div class="legend"><span><i style="background:' + C.blue + '"></i>Requests</span><span>' + nf(ai.unique_total) + ' unique agents in ' + DAYS.length + ' days</span></div></div></div>';

    h += '<div class="sec"><div class="sec-h"><h2>Where people arrive</h2><span class="chip arr">ARRIVALS</span><span class="win">' + SPAN + ' · every list adds up to ' + nf(P.total) + '</span></div>' +
      '<div class="grid g2"><div class="card"><h3>From</h3>' +
      rows(P.by_source.map(function (s) { return { n: sourceName(s.source), v: s.hits, t: s.source === 'external-withheld' ? HIDDEN_TIP : null }; })
        .concat([{ n: 'Other sources', v: P.total - srcSum, rest: true }]), { color: C.cyan, total: P.total, totalLabel: 'All arrivals' }) + '</div>' +
      '<div class="card"><h3>Landed on</h3>' +
      rows(P.top_paths.map(function (p) { return { n: p.path, v: p.hits }; })
        .concat([{ n: 'Every other page', v: P.total - pathSum, rest: true }]), { color: C.cyan, total: P.total, totalLabel: 'All arrivals' }) + '</div></div></div>';

    h += '<div class="sec"><div class="sec-h"><h2>What they open next</h2><span class="chip req">REQUESTS</span><span class="win">' + SPAN + ' and the last 24 h, side by side</span></div>' +
      '<div class="grid g2"><div class="card"><h3>People <span class="tot">' + nf(hum.total) + ' requests</span></h3>' +
      rows(hum.list, { color: C.cyan, total: hum.total, total24: hum.total24, totalLabel: 'All requests', h24: true }) + '</div>' +
      '<div class="card"><h3>AI agents <span class="tot">' + nf(bot.total) + ' requests</span></h3>' +
      rows(bot.list.concat(gap ? [{ n: 'Not in the list', v: gap, cls: 'gap', t: 'AI-agent requests (' + nf(ai.total) + ') minus this list. Both are every request an agent makes, so this should be 0.' }] : []),
        { color: C.blue, total: bot.total, total24: bot.total24, totalLabel: 'All requests in the list', h24: true }) + '</div></div></div>';

    function card(key, label, t, v, pf, h24) {
      return '<div class="act"><div class="l">' + label + ' ' + tip(t) + '</div><div class="v">' + v + '</div><div class="pf bl">' + pf + '</div>' +
        '<div class="h">Last 24 h: ' + h24 + '</div></div>';
    }
    var su = act.signups, or = act.clob_orders, tr = act.clob_trades, no = act.clob_notional, ec = act.event_card_orders, bc = act.bot_clones;
    h += '<div class="sec"><div class="sec-h"><h2>What accounts did</h2><span class="chip ac">ACTIONS</span>' +
      '<span class="win"><b class="gr">■</b> customer-participating ' + tip('A customer account is on at least one side of it. Bots a customer runs count as the customer. Participation, not proof of outside volume.') +
      ' &nbsp; <b class="bl">■</b> platform-only ' + tip('System, test, market-maker and internal accounts on every side.') + ' &nbsp; · ' + SPAN + '</span></div>' +
      '<div class="acts">' +
      card('signups', 'Sign-ups', 'New accounts.', nf(su.range.customers), '+ ' + nf(su.range.platform) + ' platform-only', '<b>' + nf(su['24h'].customers) + '</b> · ' + nf(su['24h'].platform)) +
      card('orders', 'Orders placed', 'Orders sent to the exchange (CLOB), filled or not.', nf(or.range.customers), '+ ' + nf(or.range.platform) + ' platform-only', '<b>' + nf(or['24h'].customers) + '</b> · ' + nf(or['24h'].platform)) +
      card('trades', 'Trades filled', 'Orders that executed on the exchange (CLOB).', nf(tr.range.customers), '+ ' + nf(tr.range.platform) + ' platform-only', '<b>' + nf(tr['24h'].customers) + '</b> · ' + nf(tr['24h'].platform)) +
      card('notional', 'Traded notional', 'Price × quantity of every filled CLOB trade, in the pair\'s quote currency (USDC for */USDC).', usd(no.range.customers), '+ ' + usd(no.range.platform) + ' platform-only', '<b>' + usd(no['24h'].customers) + '</b> · ' + usd(no['24h'].platform)) +
      card('cards', 'Event-card orders', 'Every event-card order placed; filled ones are those that executed.', nf(ec.range.orders), nf(ec.range.filled) + ' filled · ' + usd(ec.range.filled_usdc), '<b>' + nf(ec['24h'].orders) + '</b>') +
      card('clones', 'Bots cloned', 'Counted under customers.', nf(bc.range.total), nf(bc.range.paper) + ' paper · ' + nf(bc.range.live) + ' live', '<b>' + nf(bc['24h'].total) + '</b> (' + nf(bc['24h'].live) + ' live)') +
      '</div></div>';

    h += '<div class="sec"><div class="sec-h"><h2>Traded volume per day</h2><span class="chip ac">ACTIONS</span><span class="win">the bars add up to the totals · ' + SPAN + '</span></div>' +
      '<div class="card"><div class="vol-head">' +
      '<div><div class="l">Customer-participating</div><div class="big">' + usd(volC) + '</div></div>' +
      '<div><div class="l">Platform-only</div><div class="m bl">' + usd(volP) + '</div></div>' +
      '<div><div class="l">Event cards</div><div class="m cy">' + usd(volE) + '</div></div>' +
      '<div><div class="l">Last 24 h, both</div><div class="m">' + usd(n24.customers + n24.platform) + '</div></div></div>' +
      '<div id="c-vol"></div><div class="legend"><span><i style="background:' + C.green + '"></i>Customer-participating</span><span><i style="background:' + C.blue + '"></i>Platform-only</span><span><i style="background:' + C.cyan + '"></i>Event cards</span><span>USDC · updated every 10 min</span></div></div></div>';

    h += '<div class="sec"><div class="sec-h"><h2>AI agents by family</h2><span class="chip req">REQUESTS</span><span class="win">' + SPAN + ' · adds up to ' + nf(ai.total) + '</span></div>' +
      '<div class="card"><h3>Family <span class="tot">' + nf(ai.unique_total) + ' unique agents</span></h3>' + rows(ai.top.map(function (f) { return { n: f.agent, v: f.hits }; }).concat([{ n: (ai.families - ai.top.length) + ' more families', v: ai.total - famSum, rest: true }]),
        { color: C.blue, total: ai.total, totalLabel: 'All AI-agent requests' }) + '</div></div>';

    h += '<div class="foot"><span>Days cut at midnight Pacific</span><span>Unique = hashed IP, none stored</span><span>Bots filtered are in no other number</span><span>Read ' + P.generated_at.slice(0, 16).replace('T', ' ') + ' UTC</span></div>';
    $('app').innerHTML = h;
    chart($('c-people'), DAYS, [{ values: vals(P.daily, DAYS), color: C.cyan }], { values: vals(P.unique_daily, DAYS), color: C.text });
    chart($('c-agents'), DAYS, [{ values: vals(ai.daily, DAYS), color: C.blue }]);
    chart($('c-vol'), DAYS, [{ values: vals(vol.customers, DAYS), color: C.green }, { values: vals(vol.platform, DAYS), color: C.blue }, { values: vals(vol.event_cards, DAYS), color: C.cyan }]);
  }

  /* =================================== YOUR PAGES =================================== */
  function mine() {
    var T = M.totals, items = M.items.map(function (r) {
      return { kind: r[0], label: r[1], path: r[2], views: r[3], unique: r[4], ai: r[5], site: r[6], beacon: r[7] };
    });
    var inside = (M.by_source.filter(function (s) { return s[0] === 'internal'; })[0] || [0, 0])[1];
    var outside = T.visits - inside;
    var viewed = items.filter(function (i) { return i.views > 0; }).sort(function (a, b) { return b.views - a.views; });
    var aiOnly = items.filter(function (i) { return i.views === 0 && i.ai > 0; });
    var zero = M.zero_rows, zeroN = sum(Object.keys(zero).map(function (k) { return zero[k]; }));
    var pages = items.length + zeroN, ext = M.by_source.filter(function (s) { return s[0] !== 'internal'; });

    var h = header('mine') + units(false);
    h += '<div class="kgroup k4"><div class="who"><b>YOUR ' + pages + ' PAGES</b> · apps, shipped pages, features, event cards, companies, League · ' + SPAN + '</div>' +
      '<div class="k"><div class="l">Page views <span class="chip vw">VIEW</span> ' + tip('Every time one of your pages is opened: arriving from outside or clicking through from another page of the site.') + '</div><div class="v">' + nf(T.visits) + '</div>' +
      '<div class="splitbar"><i style="width:' + (100 * outside / T.visits) + '%;background:' + C.cyan + '"></i><i style="width:' + (100 * inside / T.visits) + '%;background:' + C.blue + '"></i></div>' +
      '<div class="s"><b class="cy">' + nf(outside) + '</b> arrivals · <b class="bl">' + nf(inside) + '</b> from the site</div></div>' +
      '<div class="k"><div class="l">Arrivals <span class="chip arr">ARR</span></div><div class="v cy">' + nf(outside) + '</div><div class="s"><b>' + pc(outside, P.total) + '</b> of the site\'s ' + nf(P.total) + '</div></div>' +
      '<div class="k"><div class="l">Unique people ' + tip('Distinct hashed IPs that opened at least one of your pages.') + '</div><div class="v gr">' + nf(T.unique_visitors) + '</div><div class="s"><b>' + (T.visits / T.unique_visitors).toFixed(1) + '</b> views each</div></div>' +
      '<div class="k"><div class="l">AI-agent requests <span class="chip req">REQ</span></div><div class="v bl">' + nf(T.ai_agent_visits) + '</div><div class="s">on <b>' + (viewed.filter(function (i) { return i.ai > 0; }).length + aiOnly.length) + '</b> of your pages</div></div></div>';

    h += '<div class="grid g2 sec">' +
      '<div class="card"><h3>Page views per day <span class="tot">' + nf(T.visits) + '</span></h3><div id="c-views"></div>' +
      '<div class="legend"><span><i style="background:' + C.cyan + '"></i>Page views</span><span><i class="ln" style="background:' + C.text + '"></i>Unique people</span></div></div>' +
      '<div class="card"><h3>AI-agent requests per day <span class="tot">' + nf(T.ai_agent_visits) + '</span></h3><div id="c-ai"></div>' +
      '<div class="legend"><span><i style="background:' + C.blue + '"></i>Requests</span></div></div></div>';

    h += '<div class="grid g2 sec" style="grid-template-columns: 1fr 1.25fr; align-items: start">' +
      '<div class="card"><h3>Arrivals came from <span class="chip arr">ARR</span><span class="tot">' + nf(outside) + '</span></h3>' +
      rows(ext.map(function (s) { return { n: sourceName(s[0]), v: s[1], t: s[0] === 'external-withheld' ? HIDDEN_TIP : null }; }), { color: C.cyan, total: outside, totalLabel: 'All arrivals' }) + '</div>' +
      '<div class="card"><h3>Users you brought <span class="tot">' + nf(M.referrals.per_user_et10) + ' ET10 per qualified user</span></h3>' +
      '<div class="strip" style="grid-template-columns:repeat(4,1fr)">' +
      '<div><div class="v">' + nf(M.referrals.attributed) + '</div><div class="l">Registered</div></div>' +
      '<div><div class="v">' + nf(M.referrals.qualified) + '</div><div class="l">First deposit</div></div>' +
      '<div><div class="v gr">' + nf(M.referrals.earned_et10) + '</div><div class="l">ET10 earned</div></div>' +
      '<div><div class="v">' + nf(M.referrals.pending_et10) + '</div><div class="l">ET10 on the way</div></div></div>' +
      '<div class="legend" style="margin-top:12px"><span>Counted when someone registers through your cymetica.com/c/ link and deposits · paid daily 05:20 UTC</span></div></div></div>';

    var maxV = viewed[0].views;
    var body = viewed.map(function (i) {
      var k = i.kind === 'App' ? 'app' : i.kind === 'Shipped page' ? 'shp' : '';
      var b = i.beacon, bc = b == null ? '<span class="beacon">—</span>' :
        (sum(b) === 0 ? '<span class="zero">0 · 0 · 0</span> ' + tip('The app counter shows nothing for a page with ' + nf(i.views) + ' views.') :
          '<span class="beacon"><b>' + nf(b[0]) + '</b> · ' + nf(b[2]) + ' · ' + nf(b[3]) + '</span>');
      return '<tr><td class="pg"><span class="kind ' + k + '">' + esc(i.kind) + '</span><span class="t">' + esc(i.label) + '</span><div class="p">' + esc(i.path) + '</div></td>' +
        '<td class="views">' + nf(i.views) + '<span class="mini"><i style="width:' + (100 * i.views / maxV) + '%;background:' + C.cyan + '"></i></span></td>' +
        '<td class="cy">' + nf(i.views - i.site) + '</td><td>' + nf(i.site) + '</td><td>' + nf(i.unique) + '</td><td class="bl">' + nf(i.ai) + '</td><td>' + bc + '</td></tr>';
    }).join('');
    h += '<div class="sec"><div class="sec-h"><h2>Your pages</h2><span class="win">sorted by views · ' + SPAN + '</span></div><div class="card">' +
      '<table class="pages"><thead><tr><th>Page</th><th>Views</th><th>Arrivals</th><th>From site</th><th>Unique</th><th>AI agents</th><th>App opens · uses · likes ' +
      tip('From the app\'s own counter, for apps only.') + '</th></tr></thead><tbody>' + body +
      '<tr class="more"><td colspan="7">+ ' + aiOnly.length + ' pages seen only by AI agents (' + nf(sum(aiOnly.map(function (i) { return i.ai; }))) + ' requests) &nbsp;▸</td></tr>' +
      '<tr class="more"><td colspan="7">+ ' + zeroN + ' pages with no traffic yet (' + Object.keys(zero).map(function (k) { return zero[k] + ' ' + k.toLowerCase() + (zero[k] > 1 ? 's' : ''); }).join(' · ') + ') &nbsp;▸</td></tr>' +
      '<tr class="sum"><td><b>All your pages</b></td><td class="views">' + nf(T.visits) + '</td><td class="cy">' + nf(outside) + '</td><td>' + nf(inside) + '</td><td>' + nf(T.unique_visitors) + '</td><td class="bl">' + nf(T.ai_agent_visits) + '</td><td></td></tr>' +
      '</tbody></table></div></div>';

    h += '<div class="foot"><span>Only you see this page</span><span>Days cut at midnight Pacific</span><span>Unique = hashed IP, none stored</span><span>Read ' + M.generated_at.slice(0, 16).replace('T', ' ') + ' UTC</span></div>';
    $('app').innerHTML = h;
    chart($('c-views'), DAYS, [{ values: vals(M.daily, DAYS), color: C.cyan }], { values: vals(M.unique_daily, DAYS), color: C.text });
    chart($('c-ai'), DAYS, [{ values: vals(M.ai_agent_daily, DAYS), color: C.blue }]);
  }

  (document.body.dataset.page === 'mine' ? mine : site)();
})();
