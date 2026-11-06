/* One Traffic page (mock). Their chart settings from /traffic, /traffic/mine and /app-usage, fed by the snapshot in data.js.
   The range switch is the fix the operator asked for: every range is already in memory, the chip answers at once,
   and a panel that is still waiting says Loading instead of sitting on the old picture. */
(function () {
    'use strict';
    var S = window.SNAP || {};
    var $ = function (id) { return document.getElementById(id); };
    var root = $('one');
    var days = 14, aud = 'combined', auAll = false, actWin = '24h', hMetric = 'users', hRange = 30;
    var ACCENT = '#00cfff', POS = '#00ff88', BLUE = '#3b82f6', NEG = '#ff4444', GRID = 'rgba(0,150,255,0.10)', TEXT = '#a9b8cc';
    var STACK = ['#00cfff', '#00ff88', '#3b82f6', '#0ea5e9', '#14b8a6', '#22c55e', '#60a5fa', '#2dd4bf', '#1d4ed8', '#0891b2', '#15803d', '#93c5fd', '#5eead4'];
    var charts = {};
    if (window.Chart) { Chart.defaults.color = TEXT; Chart.defaults.font.family = "system-ui, -apple-system, 'Segoe UI', Roboto, sans-serif"; }

    function P() { return S['public-' + days] || {}; }
    function A() { var a = S['activity-' + days]; return a && !a.error ? a : null; }
    function M() { return S['mine-' + days] || {}; }
    var U = S['app-usage'] || {}, H = S['app-usage-history'] || {}, PR = S.products || {};
    var PRODUCT = {}; (PR.products || []).forEach(function (p) { PRODUCT[p.path] = p; });
    var USAGE = {}; ['combined', 'humans', 'ai_agents'].forEach(function (t) { USAGE[t] = {}; (U[t] || []).forEach(function (r) { if (r.path) USAGE[t][r.path] = r; }); });

    function nf(n) { return (n == null) ? '–' : Number(n).toLocaleString('en-US'); }
    function usd(n) { return (n == null) ? '–' : '$' + Number(n).toLocaleString('en-US', { maximumFractionDigits: 0 }); }
    function ser(labels, map) { return labels.map(function (l) { return (map && map[l] != null) ? map[l] : 0; }); }
    function short(labels) { return labels.map(function (l) { return l.slice(5); }); }
    function el(tag, cls, text) { var n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; }
    function md(iso) { var M_ = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']; return iso ? M_[+iso.slice(5, 7) - 1] + ' ' + (+iso.slice(8, 10)) : ''; }

    function chart(id, cfg) {
        if (charts[id]) { charts[id].data = cfg.data; charts[id].options = cfg.options; charts[id].update('none'); return charts[id]; }
        var c = $(id); if (!c || !window.Chart) return null;
        charts[id] = new Chart(c.getContext('2d'), cfg);
        return charts[id];
    }
    function listRows(id, rows, name, val, emptyText) {
        var ul = $(id); ul.textContent = '';
        if (!rows || !rows.length) { var li0 = el('li'); li0.appendChild(el('span', 'p', emptyText || 'None yet.')); ul.appendChild(li0); return; }
        var max = rows.reduce(function (m, r) { return Math.max(m, r[val] || 0); }, 1);
        rows.forEach(function (r) {
            var li = el('li');
            var p = el('span', 'p', r[name]); if (name !== 'path') p.style.fontFamily = 'inherit';
            var bar = el('span', 'bar'); bar.style.width = Math.max(4, Math.round(60 * (r[val] / max))) + 'px';
            li.appendChild(p); li.appendChild(bar); li.appendChild(el('span', 'n', nf(r[val]))); ul.appendChild(li);
        });
    }

    /* ---------- site (/traffic) ---------- */
    function site() {
        var d = P(), labels = d.day_labels || [], ai = d.ai_agents || {};
        $('k-total').textContent = nf(d.total);
        $('k-unique').textContent = nf(d.unique_total);
        $('k-today').textContent = nf(labels.length ? (d.daily || {})[labels[labels.length - 1]] : null);
        $('k-agents').textContent = nf(ai.total);
        $('k-agents-u').textContent = nf(ai.unique_total);
        $('k-bots').textContent = nf(d.bots);
        chart('tl-line', { type: 'line', data: { labels: short(labels), datasets: [
            { label: 'Arrivals', data: ser(labels, d.daily), borderColor: ACCENT, backgroundColor: 'rgba(0,207,255,0.12)', fill: true, tension: 0.3, pointRadius: 0, borderWidth: 2 },
            { label: 'Unique visitors', data: ser(labels, d.unique_daily), borderColor: POS, backgroundColor: 'rgba(0,255,136,0.10)', fill: true, tension: 0.3, pointRadius: 0, borderWidth: 2 },
            { label: 'AI-agent requests (dashed)', data: ser(labels, ai.daily), yAxisID: 'yAgents', borderColor: BLUE, backgroundColor: 'transparent', fill: false, tension: 0.3, pointRadius: 0, borderWidth: 2, borderDash: [6, 4] },
            { label: 'Unique AI agents (dotted)', data: ser(labels, ai.unique_daily), yAxisID: 'yAgents', borderColor: POS, backgroundColor: 'transparent', fill: false, tension: 0.3, pointRadius: 0, borderWidth: 2, borderDash: [2, 3] }] },
            options: { responsive: true, maintainAspectRatio: false, animation: false, interaction: { mode: 'index', intersect: false },
                plugins: { legend: { labels: { boxWidth: 12, usePointStyle: true } } },
                scales: { x: { grid: { color: GRID }, ticks: { maxRotation: 0, autoSkip: true } },
                    y: { grid: { color: GRID }, beginAtZero: true, ticks: { precision: 0 }, title: { display: true, text: 'Humans' } },
                    yAgents: { position: 'right', grid: { display: false }, beginAtZero: true, ticks: { precision: 0, color: BLUE }, title: { display: true, text: 'AI agents', color: BLUE } } } } });
        var src = (d.by_source || []).slice(0, 10);
        chart('tl-src', { type: 'bar', data: { labels: src.map(function (r) { return r.source; }), datasets: [{ label: 'Arrivals', data: src.map(function (r) { return r.hits; }), backgroundColor: ACCENT, borderRadius: 4 }] },
            options: { indexAxis: 'y', responsive: true, maintainAspectRatio: false, animation: false, plugins: { legend: { display: false } },
                scales: { x: { grid: { color: GRID }, beginAtZero: true, ticks: { precision: 0 } }, y: { grid: { display: false } } } } });
        listRows('tl-paths', (d.top_paths || []).slice(0, 12), 'path', 'hits', 'No page data yet.');
        var top = (d.top_paths || []).slice(0, 12).reduce(function (s, r) { return s + r.hits; }, 0);
        $('tl-paths-note').textContent = 'Each number is how many arrivals LANDED on that page over the whole selected range. These 12 pages hold ' + nf(top) + ' of the ' + nf(d.total) + ' arrivals; the rest landed on other pages. Arrivals count only the first page of someone coming from outside, so they are far fewer than Unique visitors (' + nf(d.unique_total) + ').';
        listRows('tl-agents-list', (ai.top || []).slice(0, 12), 'agent', 'hits', 'No AI-agent requests yet in this range.');
    }

    function activity() {
        var a = A(), labels = (P().day_labels || []);
        var miss = !a;
        ['tl-do', 'tl-vol'].forEach(function (id) { $(id).classList.toggle('one-missing', miss); });
        if (miss) {
            $('tl-vol-note').textContent = 'Their activity API answered 503 after 60 s for ' + days + ' days when this mock was built, so there is no volume here. Every other range works.';
            $('tl-do-note').textContent = $('tl-vol-note').textContent;
            if (charts['tl-vol-chart']) { charts['tl-vol-chart'].data.datasets = []; charts['tl-vol-chart'].update('none'); }
            return;
        }
        var v = a.volume_daily || {};
        var sets = [{ label: 'Customer-participating (USD)', data: ser(labels, v.customers), backgroundColor: POS, borderRadius: 4, stack: 'v' },
            { label: 'Platform accounts (USD)', data: ser(labels, v.platform), backgroundColor: BLUE, borderRadius: 4, stack: 'v' }];
        if (v.event_cards) sets.push({ label: 'Event cards (USDC)', data: ser(labels, v.event_cards), backgroundColor: ACCENT, borderRadius: 4, stack: 'v' });
        chart('tl-vol-chart', { type: 'bar', data: { labels: short(labels), datasets: sets },
            options: { responsive: true, maintainAspectRatio: false, animation: false,
                plugins: { tooltip: { callbacks: { label: function (c) { return c.dataset.label + ': ' + usd(c.parsed.y); } } } },
                scales: { x: { stacked: true, grid: { display: false } }, y: { stacked: true, beginAtZero: true, grid: { color: GRID }, ticks: { callback: function (x) { return usd(x); } } } } } });
        var defs = a.definitions || {};
        $('tl-vol-note').textContent = (defs.volume || '') + ' Updated every 10 minutes.';
        drawDo();
        var tb = $('tl-acts').querySelector('tbody'); tb.textContent = '';
        function cell(x, unit, side) {
            if (x == null) return '–';
            if (unit === 'usd') return usd(x[side]);
            if (unit === 'event_cards') return side === 'customers' ? nf(x.orders) + ' (' + nf(x.filled) + ' filled)' : '–';
            if (unit === 'clones') return side === 'customers' ? nf(x.total) + ' (' + nf(x.live) + ' live)' : '–';
            return nf(x[side]);
        }
        (a.actions || []).forEach(function (r) {
            var tr = el('tr');
            [r.label, cell(r['24h'], r.unit, 'customers'), cell(r['24h'], r.unit, 'platform'), cell(r.range, r.unit, 'customers'), cell(r.range, r.unit, 'platform')]
                .forEach(function (t) { tr.appendChild(el('td', null, t)); });
            tb.appendChild(tr);
        });
        $('tl-do-note').textContent = (defs.human_requests || '') + ' ' + (defs.areas || '') + ' ' + (defs.segments || '');
    }
    function drawDo() {
        var a = A(); if (!a) return;
        var req = a.requests || {}, rt = a.request_totals || {};
        listRows('tl-do-human', (req.human || {})[actWin], 'area', 'requests', 'No requests in this window.');
        listRows('tl-do-agent', (req.ai_agent || {})[actWin], 'area', 'requests', 'No requests in this window.');
        $('tl-do-human-total').textContent = (rt.human || {})[actWin] != null ? '· ' + nf(rt.human[actWin]) + ' in total' : '';
        $('tl-do-agent-total').textContent = (rt.ai_agent || {})[actWin] != null ? '· ' + nf(rt.ai_agent[actWin]) + ' in total' : '';
        $('tl-do-range').textContent = actWin === '24h' ? 'last 24 h' : 'since ' + String(a.since || '').slice(0, 10);
    }

    /* ---------- apps (/app-usage), one format for theirs and yours ---------- */
    function appTable(table, rows, opts) {
        table.textContent = '';
        var head = el('thead'), tr = el('tr');
        var cols = [['#', ''], ['App', ''], ['Unique visitors', 'n']];
        if (opts.views) cols.push(['Page views', 'n']);
        cols.push(['Came back', 'n'], ['Uses', 'n']);
        cols.forEach(function (h, i) {
            var th = el('th', h[1], h[0]);
            var tip = (opts.tips || APP_TIPS)[h[0]]; if (tip) th.setAttribute('data-tip', tip);
            tr.appendChild(th);
        });
        head.appendChild(tr); table.appendChild(head);
        var body = el('tbody');
        rows.forEach(function (r, i) {
            var row = el('tr', r.yours ? 'yours' : '');
            row.appendChild(el('td', 'rk', String(r.rank || i + 1)));
            var td = el('td');
            if (r.path) { var a = el('a', null, r.app); a.href = 'https://cymetica.com' + r.path; td.appendChild(a); } else td.appendChild(el('span', 'nm', r.app));
            if (r.yours && opts.tagYours) td.appendChild(el('span', 'tag', 'yours'));
            row.appendChild(td);
            row.appendChild(el('td', 'n', nf(r.users)));
            if (opts.views) row.appendChild(el('td', 'n', nf(r.views)));
            var cb = el('td', 'n' + (r.came == null ? ' mute' : ''), r.came == null ? '–' : r.came + '%');
            if (r.came != null) { var b = el('span', 'au-bar'); b.style.width = (r.came * 0.4) + 'px'; cb.appendChild(b); }
            row.appendChild(cb);
            row.appendChild(el('td', 'n' + (r.uses == null ? ' mute' : ''), r.uses == null ? '·' : nf(r.uses)));
            body.appendChild(row);
        });
        table.appendChild(body);
    }
    /* ---------- tooltips: one short line per column and tile ---------- */
    var APP_TIPS = {
        'Unique visitors': 'Distinct people who used the app, all its pages and tools, each counted once. Counted by account or browser, so it is not the same number as the site\'s Unique visitors.',
        'Page views': 'Every page of the app a person opened. AI agents are not counted.',
        'Came back': 'Share of these visitors who used the app on two or more days in the last 30 days.',
        Uses: 'Page loads where the visitor did something: clicked, typed or filled in. Opening a page and leaving is not a use.'
    };
    var TIPS = [
        ['#k-total + .k', 'The first page someone opens when they come from outside: search, a link, a chat. The pages they open after it are not counted.'],
        ['#k-unique + .k', 'Distinct people who opened any page of the site, each counted once. Counted by IP address.'],
        ['#k-today + .k', 'Arrivals since midnight today, Pacific time.'],
        ['#k-agents + .k', 'Every request an AI agent made. One crawler reading 300 pages is 300.'],
        ['#k-agents-u + .k', 'Distinct AI agents: one per agent family per IP address.'],
        ['#k-bots + .k', 'Cymetica does not say what this counts.'],
        ['#m-visits + .k', 'Every page a person opened on your pages. AI agents and background calls are not counted.'],
        ['#m-unique + .k', 'Distinct people who opened any of your pages, each counted once. Counted by IP address.'],
        ['#m-agents + .k', 'Every request an AI agent made to your pages.'],
        ['#m-items + .k', 'Pages, apps and products you created.'],
        ['.tm-table th:nth-child(2)', 'Every time a person opened the page.'],
        ['.tm-table th:nth-child(3)', 'Distinct people who opened this one page, each counted once. Counted by IP address.'],
        ['.tm-table th:nth-child(4)', 'Requests AI agents made to this page.'],
        ['.tm-table th:nth-child(5)', 'Cymetica does not say what this counts.'],
        ['.tl-acts th:nth-child(2)', 'Actions with a customer account on at least one side, in the last 24 hours.'],
        ['.tl-acts th:nth-child(3)', 'Actions where every side is a system, test, market-maker or internal account, in the last 24 hours.'],
        ['.tl-acts th:nth-child(4)', 'Actions with a customer account on at least one side, over the selected range.'],
        ['.tl-acts th:nth-child(5)', 'Actions where every side is a system, test, market-maker or internal account, over the selected range.']
    ];
    function tips() {
        TIPS.forEach(function (t) { document.querySelectorAll(t[0]).forEach(function (n) { n.setAttribute('data-tip', t[1]); }); });
        var box = el('div', 'one-tip'); box.id = 'one-tip'; document.body.appendChild(box);
        function hide() { box.classList.remove('on'); }
        document.addEventListener('mouseover', function (e) {
            var n = e.target.closest ? e.target.closest('[data-tip]') : null;
            if (!n) { hide(); return; }
            box.textContent = n.getAttribute('data-tip'); box.classList.add('on');
            var r = n.getBoundingClientRect(), w = box.offsetWidth, h = box.offsetHeight;
            var x = Math.min(Math.max(8, r.left + r.width / 2 - w / 2), window.innerWidth - w - 8);
            var y = r.top - h - 8; if (y < 8) y = r.bottom + 8;
            box.style.left = x + 'px'; box.style.top = y + 'px';
        });
        window.addEventListener('scroll', hide, { passive: true });
    }

    var AUD = { combined: ['Most used by everyone', 'People and AI agents together, each user counted once.'],
        humans: ['Most used by people', 'Visitors in a web browser.'],
        ai_agents: ['Most used by AI agents', 'Outside AI agents using the site, the API or the MCP server. Training and search crawlers are not counted.'] };
    function apps() {
        var w = U.window || {};
        $('au-window').textContent = 'last ' + (w.days || 30) + ' days · ' + (w.since || '') + ' to today (UTC)';
        $('au-title').textContent = AUD[aud][0];
        $('au-sub').textContent = AUD[aud][1];
        document.querySelectorAll('.au-tab').forEach(function (t) { t.setAttribute('aria-selected', String(t.getAttribute('data-aud') === aud)); });
        var all = (U[aud] || []).map(function (r) {
            var p = PRODUCT[r.path];
            return { rank: r.rank, app: r.app, path: r.path, users: r.users, came: r.came_back_pct, uses: p ? p.uses : null, yours: !!p };
        });
        var tips = Object.assign({}, APP_TIPS, { 'Unique visitors': aud === 'humans' ? APP_TIPS['Unique visitors'] : aud === 'ai_agents' ? 'Distinct outside AI agents that used the app in the last 30 days, each counted once.' : 'Distinct people and AI agents that used the app in the last 30 days, each counted once.',
            Uses: APP_TIPS.Uses + ' Cymetica publishes it only for apps in a company, so the other rows show a dot.' });
        appTable($('au-table'), auAll ? all : all.slice(0, 15), { tagYours: true, tips: tips });
        $('au-more').textContent = auAll ? 'Show top 15' : 'Show all ' + all.length;
        var t = U.totals || {};
        var st = $('au-stats'); st.textContent = '';
        [[nf(t.humans), 'People'], [nf(t.ai_agents), 'Outside AI agents'], [(w.days || 30) + ' days', (w.since || '') + ' to today']].forEach(function (x) {
            var b = el('div', 'au-stat'); b.appendChild(el('div', 'v', x[0])); b.appendChild(el('div', 'k', x[1])); st.appendChild(b);
        });
    }

    /* Usage over time: their card() from /app-usage, unchanged in what it draws */
    function history() {
        var grid = $('au-history-grid'); grid.textContent = '';
        var sessions = hMetric === 'sessions';
        var src = sessions ? (H.sessions || {}).apps : H[aud === 'ai_agents' ? 'ai_agents' : aud];
        if (sessions && aud === 'ai_agents') { $('au-history-sub').textContent = 'Sessions are only recorded for visitors in a web browser, so there are none to show for AI agents. Switch to Users to see them.'; return; }
        var allDays = H.days || [], cut = allDays.indexOf(H.today); if (cut < 0) cut = allDays.length;
        var dd = allDays.slice(0, cut).slice(-hRange);
        var rows = [];
        (src || []).forEach(function (s) {
            var vals = (sessions ? s.sessions : s.users).slice(0, cut).slice(-hRange);
            var peak = Math.max.apply(null, vals.map(function (v) { return v == null ? -1 : v; }));
            if (peak >= 0) rows.push({ s: s, v: vals, peak: peak });
        });
        rows.sort(function (x, y) { return y.peak - x.peak; });
        $('au-history-title').textContent = 'Usage over time: ' + (sessions ? 'browser sessions' : AUD[aud][0].replace('Most used by ', ''));
        $('au-history-sub').textContent = (sessions ? 'Browser sessions' : 'Users') + ' per day for each app over the last ' + hRange + ' full days, ' + md(dd[0]) + ' to ' + md(dd[dd.length - 1]) + ' (UTC). The number is the latest full day. Each chart has its own scale, so compare shapes and read the numbers for size.';
        var W = 240, Hh = 64, PAD = 4, NS = 'http://www.w3.org/2000/svg';
        rows.forEach(function (r) {
            var last = r.v.length - 1; while (last >= 0 && r.v[last] == null) last--;
            var n = Math.max(r.v.length - 1, 1);
            var box = el('div', 'au-card'), head = el('div', 'au-card-head');
            var name = el(r.s.path ? 'a' : 'span', 'au-card-name', r.s.app); if (r.s.path) name.href = 'https://cymetica.com' + r.s.path;
            head.appendChild(name); head.appendChild(el('span', 'au-card-val', nf(r.v[last]))); box.appendChild(head);
            var svg = document.createElementNS(NS, 'svg'); svg.setAttribute('class', 'au-spark'); svg.setAttribute('viewBox', '0 0 ' + W + ' ' + Hh); svg.setAttribute('preserveAspectRatio', 'none');
            var pts = [];
            r.v.forEach(function (u, i) { if (u != null) pts.push((i / n * W).toFixed(1) + ',' + (Hh - PAD - (r.peak ? u / r.peak : 0) * (Hh - 2 * PAD)).toFixed(1)); });
            var base = document.createElementNS(NS, 'line'); base.setAttribute('class', 'base'); base.setAttribute('x1', 0); base.setAttribute('x2', W); base.setAttribute('y1', Hh - PAD); base.setAttribute('y2', Hh - PAD); svg.appendChild(base);
            var line = document.createElementNS(NS, 'polyline'); line.setAttribute('class', 'line'); line.setAttribute('points', pts.join(' ')); svg.appendChild(line);
            var plot = el('div', 'au-plot'); plot.appendChild(svg); box.appendChild(plot);
            box.appendChild(el('div', 'au-card-foot', md(dd[last]) + ' · peak ' + nf(r.peak)));
            grid.appendChild(box);
        });
    }

    /* ---------- yours (/traffic/mine) ---------- */
    function yourApps(m) {
        return (m.items || []).filter(function (i) { return i.kind === 'app'; }).map(function (i) {
            var b = i.app_beacon || {}, u = USAGE.combined[i.path] || null;
            return { app: i.label, path: i.path, users: b.visitors, uses: b.uses, came: u ? u.came_back_pct : null, rankSite: u ? u.rank : null,
                views: i.visits, unique: i.unique_visitors, agents: i.ai_agent_visits };
        }).sort(function (x, y) { return (y.users || 0) - (x.users || 0); });
    }
    function mine() {
        var m = M(), labels = m.day_labels || [], t = m.totals || {};
        $('m-visits').textContent = nf(t.visits); $('m-unique').textContent = nf(t.unique_visitors);
        $('m-agents').textContent = nf(t.ai_agent_visits); $('m-items').textContent = nf((m.items || []).length);
        chart('tm-line', { type: 'line', data: { labels: short(labels), datasets: [
            { label: 'Page views', data: ser(labels, m.daily), borderColor: ACCENT, backgroundColor: 'transparent', tension: 0.25, pointRadius: 2, borderWidth: 2 },
            { label: 'Unique visitors', data: ser(labels, m.unique_daily), borderColor: POS, backgroundColor: 'transparent', tension: 0.25, pointRadius: 2, borderWidth: 2 },
            { label: 'AI-agent requests', data: ser(labels, m.ai_agent_daily), borderColor: BLUE, backgroundColor: 'transparent', tension: 0.25, pointRadius: 2, borderWidth: 2 }] },
            options: { responsive: true, maintainAspectRatio: false, animation: false, interaction: { mode: 'index', intersect: false },
                scales: { x: { grid: { color: GRID } }, y: { beginAtZero: true, grid: { color: GRID }, ticks: { precision: 0 } } } } });
        var sets = (m.unique_daily_by_item || []).map(function (s, i) {
            var name = s.kind === 'other' ? 'Other pages' : (s.label || s.path || '').split(' · ')[0];
            if (name.length > 38) name = name.slice(0, 36) + '…';
            return { label: name, data: ser(labels, s.data), backgroundColor: STACK[i % STACK.length], borderWidth: 0, stack: 'people', maxBarThickness: 28 };
        });
        chart('tm-stack', { type: 'bar', data: { labels: short(labels), datasets: sets },
            options: { responsive: true, maintainAspectRatio: false, animation: false, interaction: { mode: 'index', intersect: false },
                plugins: { legend: { display: true, position: 'right', labels: { boxWidth: 10, font: { size: 11 } } },
                    tooltip: { filter: function (it) { return it.raw > 0; }, callbacks: { footer: function () { return 'A person on two pages the same day counts in both.'; } } } },
                scales: { x: { stacked: true, grid: { color: GRID } }, y: { stacked: true, beginAtZero: true, grid: { color: GRID }, ticks: { precision: 0 } } } } });
        function fill(id, rows, key) {
            var ul = $(id); ul.textContent = '';
            (rows || []).forEach(function (r) { var li = el('li'); li.appendChild(el('span', null, r[key])); li.appendChild(el('span', 'n', nf(r.hits))); ul.appendChild(li); });
            if (!ul.children.length) ul.appendChild(el('li', null, 'None yet'));
        }
        fill('tm-sources', m.by_source, 'source'); fill('tm-refs', m.referrers, 'host');
        var ya = yourApps(m);
        appTable($('ya-table'), ya, { views: true });
        $('ya-unit').textContent = ya.length + ' apps · last ' + days + ' days';
        var tb = $('tm-items'); tb.textContent = '';
        (m.items || []).forEach(function (it) {
            var tr = el('tr'), td = el('td');
            td.appendChild(el('span', 'tm-kind', it.kind_label || it.kind));
            var a = el('a', null, it.label || it.path); a.href = 'https://cymetica.com' + it.path; td.appendChild(a);
            if (it.app_beacon) td.appendChild(el('span', 'tm-sub', 'Whole product, all its pages and tools: ' + nf(it.app_beacon.visitors) + ' people · ' + nf(it.app_beacon.uses) + ' uses · ' + nf(it.app_beacon.likes) + ' likes'));
            tr.appendChild(td);
            [it.visits, it.unique_visitors, it.ai_agent_visits, it.from_site].forEach(function (n) { tr.appendChild(el('td', null, nf(n))); });
            tb.appendChild(tr);
        });
        $('tm-items-unit').textContent = nf((m.items || []).length) + ' pages · last ' + days + ' days';
        var r = m.referrals || {};
        $('tm-ref-intro').textContent = 'Every visitor who clicks one of your tracked links and then registers is attributed to you. They count once they make their first deposit: ' + nf(r.per_user_et10) + ' ET10 per qualified user, ' + (r.schedule || '') + '.';
        $('r-att').textContent = nf((r.attributed || 0) + (r.qualified || 0) + (r.paid || 0));
        $('r-q').textContent = nf(r.qualified_total); $('r-e').textContent = nf(r.earned_et10); $('r-p').textContent = nf(r.pending_et10);
        $('tm-ref-empty').hidden = (r.rows || []).length > 0;
    }

    /* ---------- one table of what each number counts ---------- */
    function defs() {
        var a = A() || S['activity-14'] || {}, ad = a.definitions || {}, pd = PR.definitions || {};
        // [number, shown in, what it counts, their own words (tooltip)]; '?' in the third = Cymetica never defined it
        var rows = [
            ['Basic view'],
            ['Arrivals', 'Visitors over time', 'The first page someone opens when they come from outside (search, a link, a chat). The pages they open after it are not counted.', ad.visits],
            ['Unique visitors', 'Visitors over time', 'Distinct people who opened any page of the site. Counted by IP address, so one person on two networks counts twice.', ad.unique_visitors],
            ['AI-agent requests', 'Visitors over time', 'Every request an AI agent made. One crawler reading 300 pages is 300.'],
            ['Unique AI agents', 'Visitors over time', 'Distinct AI agents.'],
            ['Bots filtered', 'Visitors over time', '?'],
            ['Volume', 'Volume generated', 'Dollar value of every filled trade, per day.', ad.volume],
            ['Unique visitors (apps)', 'Apps, Your apps', 'Distinct people who used the app, all its pages and tools together. Counted by account or browser, not by IP, so it is a different number from the site\'s Unique visitors. Cymetica called it "Users" on /app-usage and "people" on /traffic/mine.', (U.definitions || {}).users],
            ['Page views', 'Your traffic, Your apps', 'Every page a person opened on your pages. AI agents and background calls are not counted.', ad.human_requests],
            ['Came back', 'Apps, Your apps', 'Share of the unique visitors who used the app on two or more days.'],
            ['Uses', 'Apps, Your apps', 'Page loads where the visitor did something: clicked, typed or filled in.', pd.uses],
            ['People per day by page', 'Your traffic', 'Distinct people per page per day. One person on two of your pages counts in both.'],
            ['Advanced view'],
            ['Top pages', 'Top pages', 'Arrivals per page they landed on. Not people, so it is much smaller than Unique visitors.', ad.top_pages],
            ['Requests', 'What visitors do', 'Every page opened, the first one and all after it; for AI agents also API calls.', ad.requests],
            ['Sessions', 'Usage over time', 'Visits in a web browser. One person can have many.'],
            ['Unique', 'All your pages', 'Distinct people who opened that one page, counted by IP address.'],
            ['From another page here', 'All your pages', '?']
        ];
        var t = $('defs-table'); t.textContent = '';
        var head = el('thead'), hr = el('tr');
        ['Number', 'Shown in', 'What it counts'].forEach(function (h) { hr.appendChild(el('th', null, h)); });
        head.appendChild(hr); t.appendChild(head);
        var b = el('tbody'), n = 0;
        rows.forEach(function (r) {
            var tr = el('tr');
            if (r.length === 1) { var g = el('td', 'grp', r[0]); g.colSpan = 3; tr.appendChild(g); b.appendChild(tr); return; }
            n++;
            tr.appendChild(el('td', null, r[0]));
            tr.appendChild(el('td', 'who', r[1]));
            var und = r[2] === '?';
            var wd = el('td', 'what' + (und ? ' undef' : ''), und ? 'Cymetica does not say what this counts.' : r[2]);
            if (r[3]) wd.title = 'Their words: ' + r[3];
            tr.appendChild(wd); b.appendChild(tr);
        });
        t.appendChild(b);
        $('defs-count').textContent = n + ' numbers';
    }

    /* ---------- Claude's basic ---------- */
    function spark(vals, colour) {
        var max = Math.max.apply(null, vals.concat([1])), n = Math.max(vals.length - 1, 1);
        var pts = vals.map(function (v, i) { return (i / n * 100).toFixed(1) + ',' + (32 - v / max * 28).toFixed(1); }).join(' ');
        return '<svg viewBox="0 0 100 34" preserveAspectRatio="none"><polyline points="' + pts + '" fill="none" stroke="' + colour + '" stroke-width="2" vector-effect="non-scaling-stroke"/></svg>';
    }
    function delta(now, before) {
        if (!before) return ['flat', 'no week before'];
        var pc = Math.round((now - before) / before * 100);
        return [pc > 2 ? 'up' : pc < -2 ? 'down' : 'flat', (pc > 0 ? '+' : '') + pc + '% vs 7-day average'];
    }
    function claude() {
        var p = S['public-14'] || {}, m = S['mine-14'] || {}, a = S['activity-14'] || {};
        var L = p.day_labels || [], y = L[L.length - 2], prev = L.slice(L.length - 9, L.length - 2);
        $('c-yday-label').textContent = md(y) + ', the last full Pacific day';
        function avg(map) { return prev.reduce(function (s, k) { return s + ((map || {})[k] || 0); }, 0) / (prev.length || 1); }
        var vol = (a.volume_daily || {}).customers || {};
        var tiles = [
            ['Site visitors', (p.unique_daily || {}), 'pos', POS, nf],
            ['Arrivals from outside', (p.daily || {}), '', ACCENT, nf],
            ['People on your pages', (m.unique_daily || {}), 'pos', POS, nf],
            ['Customer volume', vol, '', ACCENT, usd]];
        var box = $('c-tiles'); box.textContent = '';
        tiles.forEach(function (t) {
            var now = t[1][y] || 0, dl = delta(now, avg(t[1]));
            var div = el('div', 'c-tile ' + t[2]);
            div.innerHTML = '<div class="v"></div><div class="k"></div><div class="d ' + dl[0] + '"></div>' + spark(L.slice(0, -1).map(function (k) { return t[1][k] || 0; }), t[3]);
            div.querySelector('.v').textContent = t[4](now); div.querySelector('.k').textContent = t[0]; div.querySelector('.d').textContent = dl[1];
            box.appendChild(div);
        });
        var items = (m.unique_daily_by_item || []).filter(function (s) { return s.kind !== 'other'; }).map(function (s) {
            return { name: (s.label || s.path).split(' · ')[0], now: s.data[y] || 0, before: avg(s.data) };
        }).sort(function (x, z) { return z.now - x.now; }).slice(0, 9);
        var mx = Math.max.apply(null, items.map(function (i) { return i.now; }).concat([1]));
        var ul = $('c-apps'); ul.textContent = '';
        items.forEach(function (i) {
            var li = el('li'); li.appendChild(el('span', 'nm', i.name));
            var bw = el('span'); var bar = el('span', 'bar'); bar.style.width = Math.max(3, i.now / mx * 120) + 'px'; bar.style.display = 'block'; bw.appendChild(bar); li.appendChild(bw);
            li.appendChild(el('span', 'n', nf(i.now)));
            var dl = i.before ? Math.round((i.now - i.before) / i.before * 100) : null;
            li.appendChild(el('span', 'd ' + (dl == null ? 'flat' : dl > 2 ? 'up' : dl < -2 ? 'down' : 'flat'), dl == null ? 'new' : (dl > 0 ? '+' : '') + dl + '%'));
            ul.appendChild(li);
        });
        var pd = P(), md_ = M(), LL = pd.day_labels || [];
        var share = LL.map(function (k) { var s = (pd.unique_daily || {})[k] || 0; return s ? Math.round(((md_.unique_daily || {})[k] || 0) / s * 1000) / 10 : 0; });
        chart('c-share', { type: 'bar', data: { labels: short(LL), datasets: [
            { type: 'bar', label: 'People on your pages', data: ser(LL, md_.unique_daily), backgroundColor: POS, borderRadius: 3, yAxisID: 'y' },
            { type: 'line', label: 'Share of site visitors %', data: share, borderColor: ACCENT, backgroundColor: 'transparent', tension: 0.3, pointRadius: 0, borderWidth: 2, yAxisID: 'yS' }] },
            options: { responsive: true, maintainAspectRatio: false, animation: false, interaction: { mode: 'index', intersect: false },
                plugins: { legend: { labels: { boxWidth: 10 } } },
                scales: { x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true } }, y: { beginAtZero: true, grid: { color: GRID }, ticks: { precision: 0 } },
                    yS: { position: 'right', beginAtZero: true, grid: { display: false }, ticks: { color: ACCENT, callback: function (v) { return v + '%'; } } } } } });
        $('c-share-note').textContent = 'Over ' + days + ' days ' + nf((md_.totals || {}).unique_visitors) + ' of the site\'s ' + nf(pd.unique_total) + ' visitors opened one of your pages (' + (pd.unique_total ? Math.round((md_.totals || {}).unique_visitors / pd.unique_total * 100) : 0) + '%).';
        var ya = yourApps(md_);
        var t = $('c-table'); t.textContent = '';
        var hr = el('tr'); [['App', ''], ['People', 'n'], ['Uses', 'n'], ['Uses / person', 'n'], ['Came back', 'n'], ['Rank on the site', 'n']].forEach(function (h) { hr.appendChild(el('th', h[1], h[0])); });
        var th = el('thead'); th.appendChild(hr); t.appendChild(th);
        var tb = el('tbody');
        ya.forEach(function (r) {
            var tr = el('tr');
            var td = el('td'); var a2 = el('a', null, r.app); a2.href = 'https://cymetica.com' + r.path; td.appendChild(a2); tr.appendChild(td);
            tr.appendChild(el('td', 'n', nf(r.users)));
            tr.appendChild(el('td', 'n', nf(r.uses)));
            tr.appendChild(el('td', 'n', r.users ? (r.uses / r.users).toFixed(2) : '–'));
            tr.appendChild(el('td', 'n', r.came == null ? '–' : r.came + '%'));
            tr.appendChild(el('td', 'n', r.rankSite ? '#' + r.rankSite + ' of 40' : '–'));
            tb.appendChild(tr);
        });
        t.appendChild(tb);
        $('c-table-unit').textContent = 'last ' + days + ' days · how many, how much they do, whether they come back';
        chart('c-site', { type: 'line', data: { labels: short(LL), datasets: [
            { label: 'Unique visitors', data: ser(LL, pd.unique_daily), borderColor: POS, backgroundColor: 'rgba(0,255,136,0.10)', fill: true, tension: 0.3, pointRadius: 0, borderWidth: 2 },
            { label: 'Arrivals', data: ser(LL, pd.daily), borderColor: ACCENT, backgroundColor: 'rgba(0,207,255,0.12)', fill: true, tension: 0.3, pointRadius: 0, borderWidth: 2 }] },
            options: { responsive: true, maintainAspectRatio: false, animation: false, interaction: { mode: 'index', intersect: false }, plugins: { legend: { labels: { boxWidth: 10 } } },
                scales: { x: { grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true } }, y: { beginAtZero: true, grid: { color: GRID }, ticks: { precision: 0 } } } } });
        var aa = A() || {}, v = aa.volume_daily || {};
        chart('c-vol', { type: 'bar', data: { labels: short(LL), datasets: [
            { label: 'Customers', data: ser(LL, v.customers), backgroundColor: POS, borderRadius: 3, stack: 'v' },
            { label: 'Platform', data: ser(LL, v.platform), backgroundColor: BLUE, borderRadius: 3, stack: 'v' }] },
            options: { responsive: true, maintainAspectRatio: false, animation: false, plugins: { legend: { labels: { boxWidth: 10 } } },
                scales: { x: { stacked: true, grid: { display: false }, ticks: { maxRotation: 0, autoSkip: true } }, y: { stacked: true, beginAtZero: true, grid: { color: GRID }, ticks: { callback: function (x) { return usd(x); } } } } } });
    }

    function renderRange() { site(); activity(); mine(); }
    function renderAll() { renderRange(); apps(); history(); }

    /* ---------- controls ---------- */
    document.querySelectorAll('.one-days').forEach(function (btn) {
        btn.addEventListener('click', function () {
            days = parseInt(btn.getAttribute('data-days'), 10) || 14;
            document.querySelectorAll('.one-days').forEach(function (b) { var on = b === btn; b.classList.toggle('on', on); b.setAttribute('aria-selected', String(on)); });
            btn.classList.add('busy');
            document.querySelectorAll('.one-chart').forEach(function (p) { p.classList.add('loading'); });
            requestAnimationFrame(function () {   // the chip has already changed; the data is in memory, so the picture follows in the next frame
                renderRange();
                btn.classList.remove('busy');
                document.querySelectorAll('.one-chart').forEach(function (p) { p.classList.remove('loading'); });
            });
        });
    });
    document.querySelectorAll('.one-view').forEach(function (btn) {
        btn.addEventListener('click', function () {
            root.setAttribute('data-view', btn.getAttribute('data-view'));
            if (btn.hasAttribute('data-basic')) root.setAttribute('data-basic', btn.getAttribute('data-basic'));
            document.querySelectorAll('.one-view').forEach(function (b) { var on = b === btn; b.classList.toggle('on', on); b.setAttribute('aria-selected', String(on)); });
        });
    });
    document.querySelectorAll('.au-tab').forEach(function (t) { t.addEventListener('click', function () { aud = t.getAttribute('data-aud'); apps(); history(); }); });
    $('au-more').addEventListener('click', function () { auAll = !auAll; apps(); });
    document.querySelectorAll('.tl-do-chip').forEach(function (btn) {
        btn.addEventListener('click', function () { actWin = btn.getAttribute('data-win'); document.querySelectorAll('.tl-do-chip').forEach(function (b) { b.classList.toggle('on', b === btn); }); drawDo(); });
    });
    document.querySelectorAll('.au-metric').forEach(function (btn) {
        btn.addEventListener('click', function () {
            if (btn.hasAttribute('data-metric')) { hMetric = btn.getAttribute('data-metric'); document.querySelectorAll('[data-metric]').forEach(function (b) { b.setAttribute('aria-pressed', String(b === btn)); }); }
            else { hRange = +btn.getAttribute('data-range'); document.querySelectorAll('.au-range').forEach(function (b) { b.setAttribute('aria-pressed', String(b === btn)); }); }
            history();
        });
    });
    var q = new URLSearchParams(location.search);
    if (q.get('view')) document.querySelector('.one-view[data-view="' + q.get('view') + '"]').click();
    tips();
    $('one-gen').textContent = 'Mock data: Cymetica\'s own APIs read ' + String((S['public-14'] || {}).generated_at || '').slice(0, 16).replace('T', ' ') + ' UTC.';
    renderAll();
})();
