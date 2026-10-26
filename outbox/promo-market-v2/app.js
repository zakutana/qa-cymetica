/* Promo Market v2 mockup: one app with two tabs, Market and My dashboard, on the live site's own data.
 *
 * Every render function reads the live API's own answer through api(path), field names unchanged (data.js holds what
 * those endpoints answered on 2026-10-26). To move this onto cymetica.com, api() becomes fetch(path).then(r => r.json())
 * and the renders stay as they are. The mockup's corner switch shows SAMPLE briefs, for the states the live market
 * cannot show today (no brief is open); the materials a brief carries are new and in SAMPLE only.
 * Numbers first; an explanation is a tooltip or a fold, never a paragraph on the page. */
(function () {
  'use strict';
  const LIVE = window.LIVE, PAGE = window.PAGE, SAMPLE = window.SAMPLE;
  const $ = (id) => document.getElementById(id);
  const ME = 'expire76';

  /* ---------------- helpers ---------------- */
  const esc = (s) => String(s == null ? '' : s).replace(/[&<>"]/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));
  const fmt = (n) => (n == null ? '—' : Math.round(n).toLocaleString('en-US'));
  const usd = (n) => (n == null ? '—' : (Number.isInteger(n) && Math.abs(n) >= 100) ? fmt(n) : Number(n).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }));
  const price = (n) => (Number.isInteger(+n) ? String(+n) : Number(n).toFixed(2));
  const sum = (a, f) => a.reduce((s, x) => s + f(x), 0);
  const dShort = (d) => new Date(String(d).slice(0, 10) + 'T12:00:00Z').toLocaleDateString('en-GB', { day: 'numeric', month: 'short', timeZone: 'UTC' });
  const when = (iso) => (iso ? String(iso).slice(0, 16).replace('T', ' ') + ' UTC' : '');
  const ago = (iso) => { const h = Math.max(0, (Date.parse('2026-10-26T10:16:00Z') - Date.parse(iso)) / 36e5); return h < 1 ? Math.round(h * 60) + 'm ago' : h < 48 ? Math.round(h) + 'h ago' : Math.round(h / 24) + 'd ago'; };
  const weighted = (t) => String(t).replace(/https?:\/\/\S+/g, new Array(24).join('x')).length;
  const linkify = (t) => esc(t).replace(/(https?:\/\/[^\s)]+)/g, '<span class="u">$1</span>');

  const I = {
    market: '<path d="M3 8.5 4.6 4h10.8L17 8.5 M3 8.5h14v8H3z M3 8.5c0 1.4 1 2.3 2.3 2.3S7.7 9.9 7.7 8.5c0 1.4 1 2.3 2.3 2.3s2.3-.9 2.3-2.3c0 1.4 1 2.3 2.3 2.3S17 9.9 17 8.5 M8 16.5v-3.5h4v3.5"/>',
    dash: '<rect x="3" y="3" width="6" height="7" rx="1.5"/><rect x="11" y="3" width="6" height="4" rx="1.5"/><rect x="11" y="9" width="6" height="8" rx="1.5"/><rect x="3" y="12" width="6" height="5" rx="1.5"/>',
    x: '<path d="M4 3.5h3.2l8.8 13H12.8z M15.6 3.5 4.6 16.5"/>',
    reddit: '<circle cx="10" cy="11.6" r="5.4"/><circle cx="14.9" cy="4.3" r="1.3"/><path d="M10 6.2V3.5l3.6.8"/><circle cx="8" cy="11.2" r=".7" fill="currentColor"/><circle cx="12" cy="11.2" r=".7" fill="currentColor"/><path d="M8 13.7c1.2.8 2.8.8 4 0"/>',
    telegram: '<path d="M2.8 9.4 17 3.6l-2.4 12.6-4.6-3.6-2.4 2.3.3-3.7 6.6-6-8.2 4.9z"/>',
    discord: '<path d="M6.2 5.2c2.6-.9 5-.9 7.6 0 1.5 2.2 2.3 4.6 2.4 7.4-1.2 1-2.6 1.7-4 2l-.9-1.5m-3.6 0-.9 1.5c-1.4-.3-2.8-1-4-2 .1-2.8.9-5.2 2.4-7.4"/><circle cx="7.8" cy="10.6" r="1.1"/><circle cx="12.2" cy="10.6" r="1.1"/>',
    linkedin: '<rect x="3" y="3" width="14" height="14" rx="2.5"/><path d="M6.5 8.5v5 M6.5 6.2v.1 M9.5 13.5v-5 M9.5 10.5c0-1.2.9-2 2-2s2 .8 2 2v3"/>',
    youtube: '<rect x="2.5" y="5" width="15" height="10.5" rx="3"/><path d="M8.5 7.9v4.7l4-2.35z" fill="currentColor"/>',
    press: '<rect x="3" y="4" width="11" height="12.5" rx="1.5"/><path d="M14 7.5h2.5v7.5a1.5 1.5 0 0 1-3 0 M5.5 7h6 M5.5 10h6 M5.5 13h4"/>',
    clicks: '<path d="M5 3.5l10 5-4.2 1.2L9 14z M11 10.5l3.5 3.5"/>',
    reads: '<path d="M2.5 10s2.8-5 7.5-5 7.5 5 7.5 5-2.8 5-7.5 5-7.5-5-7.5-5z"/><circle cx="10" cy="10" r="2.2"/>',
    likes: '<path d="M10 16s-6-3.6-6-8a3.3 3.3 0 0 1 6-1.9A3.3 3.3 0 0 1 16 8c0 4.4-6 8-6 8z"/>',
    uniq: '<circle cx="10" cy="7" r="3"/><path d="M4 16.5c.8-3 3.2-4.5 6-4.5s5.2 1.5 6 4.5"/>',
    users: '<circle cx="7.5" cy="7.5" r="2.6"/><circle cx="13.5" cy="8.5" r="2.1"/><path d="M2.8 16c.6-2.6 2.5-3.9 4.7-3.9s4.1 1.3 4.7 3.9 M12.4 12.3c2.2-.3 4 .9 4.6 3.4"/>',
    link: '<path d="M8.5 11.5a3 3 0 0 0 4.2 0l2.6-2.6a3 3 0 0 0-4.2-4.2l-1 1 M11.5 8.5a3 3 0 0 0-4.2 0l-2.6 2.6a3 3 0 0 0 4.2 4.2l1-1"/>',
    today: '<path d="M11 2.5 4.5 11H10l-1 6.5L15.5 9H10z"/>',
    briefs: '<circle cx="10" cy="10" r="6.5"/><circle cx="10" cy="10" r="3.5"/><circle cx="10" cy="10" r=".8" fill="currentColor"/>',
    queues: '<path d="M3 11.5 5 4.5h10l2 7v4H3z M3 11.5h4l1 2h4l1-2h4"/>',
    pages: '<path d="M5 2.5h6.5L15 6v11.5H5z M11.5 2.5V6H15 M7.5 10h5 M7.5 13h5"/>',
    box: '<path d="M10 2.8 16.5 6v8L10 17.2 3.5 14V6z M3.5 6 10 9.2 16.5 6 M10 9.2v8"/>',
    coin: '<circle cx="10" cy="10" r="6.5"/><path d="M10 5.8v8.4 M12.3 7.6c-.5-.7-1.3-1-2.3-1-1.4 0-2.4.7-2.4 1.7 0 2.4 4.8 1.2 4.8 3.6 0 1-1 1.8-2.4 1.8-1.1 0-2-.4-2.5-1.2"/>',
    check: '<path d="M4.5 10.5 8.3 14l7.2-8"/>',
    plus: '<path d="M10 4v12 M4 10h12"/>',
    copy: '<rect x="7" y="7" width="9.5" height="9.5" rx="2"/><path d="M13 7V5a1.5 1.5 0 0 0-1.5-1.5h-6A1.5 1.5 0 0 0 4 5v6.5A1.5 1.5 0 0 0 5.5 13H7"/>',
    ext: '<path d="M8.5 4.5H4.5v11h11v-4 M11.5 3.5h5v5 M16.5 3.5 9 11"/>',
    close: '<path d="M5 5l10 10 M15 5 5 15"/>',
    arrow: '<path d="M4 10h12 M11 5l5 5-5 5"/>',
    chev: '<path d="M7.5 5l5 5-5 5"/>',
    down: '<path d="M5 7.5l5 5 5-5"/>',
    clock: '<circle cx="10" cy="10" r="6.5"/><path d="M10 6.5V10l2.5 1.8"/>',
    agent: '<rect x="5" y="5" width="10" height="10" rx="2"/><rect x="8" y="8" width="4" height="4" rx=".8"/><path d="M8 2.5V5 M12 2.5V5 M8 15v2.5 M12 15v2.5 M2.5 8H5 M2.5 12H5 M15 8h2.5 M15 12h2.5"/>',
    company: '<path d="M3.5 17V7.5l6.5-4 6.5 4V17 M3 17h14 M8 17v-4h4v4"/>',
    key: '<circle cx="7" cy="12.5" r="3.5"/><path d="M9.5 10 16 3.5 M13.5 6l2 2 M11.5 8l1.5 1.5"/>',
    lock: '<rect x="4.5" y="9" width="11" height="8" rx="1.8"/><path d="M7 9V6.8a3 3 0 0 1 6 0V9"/>',
    shield: '<path d="M10 2.8 4.5 5v4.6c0 3.6 2.4 6 5.5 7.6 3.1-1.6 5.5-4 5.5-7.6V5z M7.5 10l1.8 1.8 3.4-3.6"/>',
    radar: '<circle cx="10" cy="10" r="6.5"/><circle cx="10" cy="10" r="3.2"/><path d="M10 10l4.6-4.6"/>',
    kits: '<rect x="3" y="6" width="14" height="10.5" rx="2"/><path d="M7.5 6V4.5h5V6 M3 10.5h14"/>',
    rewards: '<path d="M6 3.5h8v3.5a4 4 0 0 1-8 0z M6 5H3.5c0 2.2 1 3.5 2.8 3.8 M14 5h2.5c0 2.2-1 3.5-2.8 3.8 M10 11v3 M7 16.5h6"/>',
    wallet: '<rect x="3" y="5" width="14" height="11" rx="2"/><path d="M3 8h14 M13 12h1.5"/>',
    upload: '<path d="M10 13V3.5 M6 7.5l4-4 4 4 M3.5 13.5V16h13v-2.5"/>',
    image: '<rect x="3" y="4" width="14" height="12" rx="2"/><circle cx="7.5" cy="8.5" r="1.5"/><path d="M3.5 14.5 8 10.5l3 2.5 2.5-2 3 3"/>',
    video: '<rect x="2.5" y="5" width="11" height="10" rx="2"/><path d="M13.5 8.5 17.5 6v8l-4-2.5"/>',
    text: '<path d="M4 5h12 M4 8.5h12 M4 12h8 M4 15.5h10"/>',
    play: '<path d="M7 5v10l8-5z" fill="currentColor"/>',
    pause: '<path d="M7 5v10 M13 5v10"/>',
    edit: '<path d="M4 16l1-4 8.5-8.5 3 3L8 15z M11.5 5.5l3 3"/>',
    skip: '<path d="M5 5l6 5-6 5z M14 5v10"/>',
    reply: '<path d="M8 5 3.5 9.5 8 14 M3.5 9.5H11a5.5 5.5 0 0 1 5.5 5.5v1"/>',
    mail: '<rect x="3" y="5" width="14" height="10.5" rx="1.8"/><path d="M3.5 6l6.5 5 6.5-5"/>',
    eye: '<path d="M2.5 10s2.8-5 7.5-5 7.5 5 7.5 5-2.8 5-7.5 5-7.5-5-7.5-5z"/><circle cx="10" cy="10" r="2.2"/>',
    funnel: '<path d="M3 4h14l-5.5 6.5V16l-3-1.5v-4z"/>',
    globe: '<circle cx="10" cy="10" r="6.5"/><path d="M3.5 10h13 M10 3.5c2 2 2.8 4 2.8 6.5S12 14.5 10 16.5 M10 3.5C8 5.5 7.2 7.5 7.2 10s.8 4.5 2.8 6.5"/>',
    search: '<circle cx="8.8" cy="8.8" r="5.3"/><path d="M12.8 12.8 16.5 16.5"/>',
    replay: '<path d="M4 10a6 6 0 1 0 2-4.5 M4 3.5V7h3.5"/>',
    orbit: '<circle cx="10" cy="10" r="3.4"/><ellipse cx="10" cy="10" rx="8" ry="3.2" transform="rotate(-20 10 10)"/>'
  };
  const ic = (k, cls) => '<svg' + (cls ? ' class="' + cls + '"' : '') + ' width="16" height="16" viewBox="0 0 20 20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">' + (I[k] || '') + '</svg>';

  // each product's picture (art/, the live site's /static/img/promo-art/): by the product's path, so no product borrows
  // another's (today promo/mine gives Events chart.svg, Airdrop Farmer infil.svg, Usage and the hub supply.svg)
  const ART = { '/gem-screener': 'gem', '/gem-screener/app': 'gem', '/chart-analyzer': 'chart', '/team-dump-radar': 'team',
    '/supply-analyzer': 'supply', '/agent-tournaments': 'casino', '/infiltrator': 'infil', '/company': 'company', '/my-agents': 'agents',
    '/events': 'events', '/airdrop-farmer': 'airdrop', '/build-it-better': 'bib', '/usage': 'usage', '/launch-check': 'launch' };
  const art = (path) => 'art/' + (ART[path] || 'gem') + '.svg';
  // the product's picture is the shot of its page that Build it Better shows (preview_url, the leaderboard's own field);
  // a product without one (Safe Launch Check is no Build it Better app) shows its share image, then our drawing
  const SHOT = {}, BACK = {};
  (LIVE['/api/v1/build-it-better/apps/leaderboard'].apps || []).forEach((a) => { SHOT[a.path] = 'https://cymetica.com' + a.preview_url; });
  const OGPIC = { '/launch-check': 'https://cymetica.com/og/app/launch-check.png?t=Safe%20Launch%20Check%20%E2%80%94%20EventTrader&v=4' };
  const pic = (path) => { const u = SHOT[path] || OGPIC[path] || art(path); BACK[u] = art(path); return u; };
  document.addEventListener('error', (e) => { const t = e.target; if (t.tagName === 'IMG' && BACK[t.src] && t.src !== BACK[t.src]) t.src = BACK[t.src]; }, true);
  const shortName = (n) => String(n || '').split(':')[0];

  function toast(msg) {
    const t = $('toast'); t.innerHTML = ic('check') + esc(msg); t.classList.add('on');
    clearTimeout(toast.h); toast.h = setTimeout(() => t.classList.remove('on'), 2200);
  }
  function copy(text, what) { try { navigator.clipboard.writeText(text); } catch (e) { /* the mockup still says so */ } toast((what || 'Text') + ' copied'); }

  /* ---------------- state ---------------- */
  const S = {
    mode: 'live', sort: 'left', qch: 'reddit', qsel: 0, qtool: '', qpage: null, jsel: 0, radar: 0, kitTool: 0,
    pgSort: 'unique_visitors', pgQ: '', open: {}, posted: [], taken: {}, booted: false,
    form: null
  };
  try { S.mode = localStorage.getItem('pm2-mode') || 'live'; } catch (e) { /* private window */ }

  /* ---------------- api: the live answers (and, switched on, the sample briefs) ---------------- */
  function allBriefs() { return (S.mode === 'sample' ? SAMPLE.briefs : []).concat(S.posted.map((p) => p.brief)); }
  function results(id) {
    const p = S.posted.find((x) => x.brief.id === id);
    if (p) return p.results;
    return SAMPLE.results[id];
  }
  function api(path) {
    if (path === '/api/v1/promo/briefs') {
      const b = allBriefs();
      if (!b.length) return LIVE[path];
      const top = b.slice().sort((p, q) => q.per_user_usdc - p.per_user_usdc)[0];
      return { stats: { up_for_grabs_usdc: +sum(b, (x) => x.up_for_grabs_usdc).toFixed(2), open_briefs: b.length, top_per_user_usdc: top.per_user_usdc,
        top_per_user_name: top.name, as_of: LIVE[path].stats.as_of }, briefs: b, sort: S.sort, how_counted: LIVE[path].how_counted };
    }
    if (path === '/api/v1/promo/mine') {
      const live = LIVE[path], mine = allBriefs().filter((b) => b.mine);
      const prods = live.products.products.map((p) => Object.assign({}, p, { brief: mine.find((b) => b.path === p.path) || null }));
      const rs = mine.map((b) => results(b.id));
      const unpaid = [].concat(...rs.map((r) => r.by_promoter.filter((x) => !x.paid && x.earned_usdc > 0)));
      return { products: Object.assign({}, live.products, { products: prods, live_briefs: mine.length,
        series: mine.map((b, k) => ({ name: b.name, days: Object.values(results(b.id).visitors_by_day) })),
        totals: { up_for_grabs_usdc: +sum(mine, (b) => b.up_for_grabs_usdc).toFixed(2), visitors_14d: sum(rs, (r) => r.visitors_14d),
          new_users: sum(rs, (r) => r.new_users.counted), spent_usdc: +sum(rs, (r) => r.spent_usdc).toFixed(2) },
        payouts: { enabled: true, items: unpaid, pending_usdc: +sum(unpaid, (x) => x.earned_usdc).toFixed(2), pending_count: unpaid.length } }),
      taken: S.mode === 'sample' ? SAMPLE.taken : live.taken };
    }
    const m = path.match(/^\/api\/v1\/promo\/briefs\/(\d+)\/results$/);
    if (m) return results(+m[1]);
    return LIVE[path];
  }

  /* ---------------- the hologram cube ---------------- */
  // the six faces are screens, each showing a product's page (the Universe building's screens, in the page's colours)
  const FACES = ['/gem-screener', '/chart-analyzer', '/agent-tournaments', '/supply-analyzer', '/company', '/airdrop-farmer'];
  const HOLO_INNER = '<div class="core"></div>';
  function holo(size, cls) {
    let sp = '';
    for (let k = 0; k < 10; k++) sp += '<i class="sp" style="left:' + (18 + (k * 37) % 64) + '%;bottom:' + (18 + (k * 13) % 18) + '%;animation-delay:' + (k * 0.5).toFixed(2) + 's"></i>';
    const faces = FACES.map((path, k) => '<div class="f f' + (k + 1) + '"><img alt="" class="' + (k % 3 ? 'on' : '') + '" src="' + pic(path) + '"></div>').join('');
    return '<div class="holo ' + (cls || '') + '" style="--s:' + size + 'px"><div class="aura"></div><div class="pool"></div><div class="beam"></div>' + sp +
      '<div class="cam"><div class="bob"><div class="stage">' + faces + HOLO_INNER + '</div></div></div></div>';
  }
  // the screens light in turn, four of six at a time
  setInterval(() => {
    document.querySelectorAll('.holo:not(.fast) .stage').forEach((st) => {
      const imgs = st.querySelectorAll('.f img'); if (!imgs.length) return;
      const k = (+st.dataset.k || 0); st.dataset.k = k + 1;
      imgs.forEach((im, j) => im.classList.toggle('on', (j + k) % 3 !== 0));
    });
  }, 2400);

  /* ---------------- the loader ---------------- */
  // what the page waits for, and how long each took on 2026-10-26 (our reads, signed in): the shell first, then the
  // four answers in parallel. "Cold start" replays today's wait for the signed-in dashboard's HTML (6 to 8 s).
  const REQS = [['/api/v1/promo/house', 'the market', 430], ['/api/v1/promo/mine', 'your products', 1920],
    ['/api/v1/promo/briefs', 'the briefs', 610], ['/api/v1/creator/expire76/links', 'your visitors', 820]];
  function boot(shellMs) {
    const el = $('boot'), pct = $('bpct'), lbl = $('blbl'), bar = $('bbar'), chips = $('breqs');
    const faces = el.querySelectorAll('.bin .f');
    faces.forEach((f, k) => { f.innerHTML = '<img alt="" src="' + pic(FACES[k]) + '">'; });
    el.classList.remove('gone');
    chips.innerHTML = '<span id="rq-page">page</span>' + REQS.map((r, k) => '<span id="rq' + k + '">' + r[1] + '</span>').join('');
    const t0 = performance.now(), end = shellMs + Math.max(...REQS.map((r) => r[2]));
    let shown = 0;
    (function tick() {
      const t = performance.now() - t0;
      const page = Math.min(1, t / shellMs);
      let reqs = 0, running = null;
      REQS.forEach((r, k) => {
        const tt = Math.max(0, t - shellMs), done = tt >= r[2], f = done ? 1 : Math.min(0.92, 1 - Math.exp(-2.2 * tt / r[2]));
        reqs += f / REQS.length;
        const c = $('rq' + k); if (c) c.className = done ? 'ok' : (t > shellMs ? 'run' : '');
        if (done && faces[k]) { const im = faces[k].querySelector('img'); if (im) im.classList.add('on'); }
        if (t >= end) faces.forEach((f) => { const im = f.querySelector('img'); if (im) im.classList.add('on'); });
        if (!done && t > shellMs && (!running || r[2] > running[2])) running = r;
      });
      const pg = $('rq-page'); if (pg) pg.className = page >= 1 ? 'ok' : 'run';
      const target = page < 1 ? page * 18 * (1 - Math.exp(-3 * page)) / (1 - Math.exp(-3)) : 18 + reqs * 82;
      shown = Math.max(shown, Math.min(t >= end ? 100 : 99, target));
      pct.innerHTML = Math.floor(shown) + '<small>%</small>';
      bar.style.width = shown + '%';
      lbl.textContent = page < 1 ? (shellMs > 2000 ? 'Waiting for the page' : 'Opening the market') : running ? 'Reading ' + running[1] : 'Ready';
      if (t < end + 250) requestAnimationFrame(tick);
      else setTimeout(() => el.classList.add('gone'), 220);
    })();
  }

  /* ---------------- the top bar and the mockup's own controls ---------------- */
  function chrome(r) {
    const onMarket = r === 'market' || r === 'brief' || r === 'board';
    $('tnav').innerHTML = '<a href="#market" class="' + (onMarket ? 'on' : '') + '">' + ic('market') + 'Market</a>' +
      '<a href="#me/products" class="' + (onMarket ? '' : 'on') + '">' + ic('dash') + 'My dashboard</a>';
    $('topnew').innerHTML = ic('plus') + 'Post a brief';
    const as = LIVE['/api/v1/promo/briefs'].stats.as_of;
    $('livechip').innerHTML = '<i class="live"></i>' + (S.mode === 'sample' ? 'sample briefs · live data' : 'live · read ' + when(as).slice(11));
    $('mock').innerHTML = 'MOCKUP <div class="seg">' + [['live', 'Live data'], ['sample', 'Sample briefs']].map((m) =>
      '<button data-mode="' + m[0] + '" class="' + (S.mode === m[0] ? 'on' : '') + '">' + m[1] + '</button>').join('') + '</div>' +
      '<button class="btn sm gh tipr" data-act="replay" data-tip="The loader as it would run on today\'s API timings">' + ic('replay') + 'Loader</button>' +
      '<button class="btn sm gh tipr" data-act="cold" data-tip="Today the signed-in dashboard sends nothing for 6 to 8 s (measured 4 times on 2026-10-26): the same wait, with the loader on screen">' + ic('clock') + 'Cold start</button>';
  }

  /* ---------------- the market ---------------- */
  function briefCard(b, preview) {
    const tk = S.taken[b.id];
    const pays = [['per_post_usdc', 'per post'], ['per_user_usdc', 'per new user'], ['per_visitor_usdc', 'per new visitor']]
      .filter((p) => +b[p[0]] > 0).map((p) => '<div><b>' + price(b[p[0]]) + '<small>USDC</small></b><span>' + p[1] + '</span></div>').join('');
    const mats = (b.materials || []).length;
    return '<article class="bc"' + (preview ? '' : ' data-brief="' + b.id + '"') + '>' +
      '<div class="img"><img alt="" src="' + pic(b.path) + '"><div class="tl">' + (mats ? '<span class="chip c">' + ic('image') + mats + ' materials</span>' : '') +
        '<span class="chip' + (b.days_left <= 2 ? ' r' : '') + '">' + ic('clock') + b.days_left + 'd left</span></div></div>' +
      '<div class="bd"><div class="nm"><b>' + esc(shortName(b.name)) + '</b><a class="lnk" href="' + esc(b.url) + '" target="_blank" rel="noopener">cymetica.com' + esc(b.path) + ' ↗</a></div>' +
        (b.say_line ? '<p class="say">' + esc(b.say_line) + '</p>' : '<p class="say dim">—</p>') +
        '<div class="ufg"><span>Up for grabs</span><b>' + usd(b.up_for_grabs_usdc) + '<small>USDC</small></b></div>' +
        '<div class="pays">' + pays + '</div>' +
        (tk ? '<button class="btn c full" data-brief="' + b.id + '">' + ic('check') + 'Taken · my link</button>' :
          '<button class="btn g full lg" ' + (preview ? 'disabled' : 'data-take="' + b.id + '"') + '>Take it ' + ic('arrow') + '</button>') +
      '</div></article>';
  }
  function sortBriefs(list) {
    const f = { left: (a, b) => b.up_for_grabs_usdc - a.up_for_grabs_usdc, user: (a, b) => b.per_user_usdc - a.per_user_usdc, ending: (a, b) => a.days_left - b.days_left }[S.sort];
    return list.slice().sort(f);
  }
  const RULE_IC = ['uniq', 'shield', 'wallet', 'coin', 'eye', 'clock', 'users'];
  function rulesGrid() {
    return '<div class="rules">' + api('/api/v1/promo/how-counted').rules.map((r, k) =>
      '<div class="rule"><span class="n">' + ic(RULE_IC[k] || 'check') + '</span><div><b>' + esc(r.title) + '</b><span>' + esc(r.text) + '</span></div></div>').join('') + '</div>';
  }
  function market() {
    const B = api('/api/v1/promo/briefs'), st = B.stats, H = PAGE.market_hero;
    const list = sortBriefs(B.briefs);
    const h1 = H.h1.replace('Get paid in USDC.', '<span>Get paid in USDC.</span>');
    return '<div class="wrap">' +
      '<section class="hero"><div>' +
        '<span class="chip g"><i class="live"></i>' + esc(H.chip.toUpperCase()) + '</span>' +
        '<h1>' + h1 + '</h1><p class="lead">' + esc(H.sub) + '</p>' +
        '<div class="ctas"><a class="btn g lg" href="#board">Earn: take a brief ' + ic('arrow') + '</a>' +
        '<a class="btn c lg" href="#new">' + ic('plus') + 'Promote my product</a>' +
        '<button class="btn gh lg" data-act="agent">' + ic('agent') + 'From your AI agent</button></div>' +
        // the market's three numbers in one row under the buttons, not scattered round the cube
        '<div class="tiles hstats" style="--n:3">' +
          tile('coin', 'USDC up for grabs', '<span class="pos">' + usd(st.up_for_grabs_usdc) + '</span><small>USDC</small>', 'every open brief', '#00ff88') +
          tile('briefs', 'Open briefs', fmt(st.open_briefs), 'funds checked on-chain') +
          tile('users', 'Top pay per new user', usd(st.top_per_user_usdc) + '<small>USDC</small>', st.top_per_user_name ? esc(shortName(st.top_per_user_name)) : 'no brief yet', '#3b82f6') +
        '</div></div>' +
        // the Promo Market's building stands in the /company Universe: one green button under the cube goes there
        '<div class="vis">' + holo(150) + '<a class="btn g lg univ" href="https://cymetica.com/company/app#universe" target="_blank" rel="noopener">' +
          ic('orbit') + 'See in the Universe ↗</a></div></section>' +
      '<section class="steps4">' + H.steps.map((s, k) => '<div class="st"><span class="no">' + (k + 1) + '</span><div><b>' + esc(s[0]) + '</b><span>' + esc(s[1]) + '</span></div></div>').join('') + '</section>' +
      '<section id="board"><div class="bhead"><h2>Open briefs</h2><span class="cnt">' + list.length + '</span><span class="sp"></span>' +
        '<div class="seg" id="bsort">' + [['left', 'Most up for grabs'], ['user', 'Best per new user'], ['ending', 'Ending soon']].map((s) =>
          '<button data-sort="' + s[0] + '" class="' + (S.sort === s[0] ? 'on' : '') + '">' + s[1] + '</button>').join('') + '</div></div>' +
        (list.length ? '<div class="grid3">' + list.map((b) => briefCard(b)).join('') + '</div>' :
          '<div class="emptymk">' + holo(54) + '<div><h3>No open briefs right now.</h3><p>' + esc(H.empty) + '</p></div>' +
            '<a class="btn g lg" href="#new">' + ic('plus') + 'Post the first brief</a></div>') + '</section>' +
      '<section class="duo">' +
        '<div class="card"><span class="kick">For builders</span><h3>Get it promoted</h3>' +
          '<div class="how3">' + ['Pick one of the apps you built with Build it Better.', 'Set a price per post, per new user or per new visitor, a budget and 7, 14 or 30 days.', 'Watch the visitors and new users each brief brings, day by day.']
            .map((t, k) => '<div><span class="no">' + (k + 1) + '</span><span>' + esc(t) + '</span></div>').join('') + '</div>' +
          '<div style="display:flex;gap:14px;align-items:center;flex-wrap:wrap"><a class="btn g" href="#new">' + ic('plus') + 'Post a brief</a>' +
          '<span class="note">' + ic('lock') + 'Your budget stays in your own wallet, checked on-chain.</span></div></div>' +
        '<div class="card"><span class="kick">For AI agents and marketing firms</span><h3>Promote from your AI agent</h3>' +
          '<pre class="code">' + linkify(H.agent_prompt) + '</pre><div style="margin-top:12px"><button class="btn c" data-copy="agent_prompt">' + ic('copy') + 'Copy prompt</button></div></div>' +
      '</section>' +
      '<details class="fold"><summary>' + ic('shield') + 'How a new user and a new visitor are counted <span class="dim num">' + api('/api/v1/promo/how-counted').rules.length + ' checks</span>' + ic('down', 'chev') + '</summary><div class="fb">' + rulesGrid() + '</div></details>' +
      '<details class="fold" style="margin-top:10px"><summary>' + ic('clock') + 'What this does not do yet' + ic('down', 'chev') + '</summary><div class="fb"><ol class="steps">' +
        H.not_yet.map((t) => '<li><span>' + esc(t) + '</span></li>').join('') + '</ol></div></details>' +
      '<footer class="foot"><span>' + (S.mode === 'sample' ? 'Briefs: samples · ' : '') + 'Read ' + when(st.as_of) + ' from /api/v1/promo/briefs</span><span style="margin-left:auto">Docs: cymetica.com/api-docs#promo-api</span></footer>' +
    '</div>';
  }

  /* a brief, as a promoter opens it: what it pays, what the owner gave to post, Take it */
  function matTile(m, path) {
    if (m.kind === 'text') return '<div class="mg txt"><div class="mb">' + ic('text') + '<div><b>' + esc(m.title) + '</b><span>ready to post</span></div><span class="sp"></span>' +
      '<button class="btn sm" data-copytext="' + esc(m.body) + '">' + ic('copy') + 'Copy</button></div><div class="tx">' + linkify(m.body) + '</div></div>';
    const th = m.kind === 'image' ? '<img alt="" src="' + esc(m.src || pic(path)) + '">' : m.kind === 'video' ? '<span class="play">' + ic('play') + '</span>' : ic('link');
    const sub = m.size || (m.url || '').replace('https://', '');
    return '<div class="mg"><div class="th">' + th + '</div><div class="mb"><div><b>' + esc(m.title) + '</b><span>' + esc(sub) + '</span></div><span class="sp"></span>' +
      (m.kind === 'link' ? '<button class="btn sm" data-copytext="' + esc(m.url) + '">' + ic('copy') + '</button>' : '<button class="btn sm" data-act="dl" data-what="' + esc(m.file || m.title) + '">' + ic('down') + '</button>') + '</div></div>';
  }
  function openBrief(id) {
    const b = api('/api/v1/promo/briefs').briefs.find((x) => x.id === id); if (!b) return;
    const tk = S.taken[id], spent = b.budget_usdc - b.up_for_grabs_usdc;
    const pays = [['per_post_usdc', 'per post', 'that stays up 7 days'], ['per_user_usdc', 'per new user', 'signed up, own deposit, 14-day check'], ['per_visitor_usdc', 'per new visitor', 'first visit, real browser, paid after 7 days']]
      .filter((p) => +b[p[0]] > 0);
    $('drawer').innerHTML = '<div class="dh"><img alt="" src="' + pic(b.path) + '"><button class="x" data-act="close">' + ic('close') + '</button></div><div class="db">' +
      '<div class="meta"><span class="chip">' + ic('clock') + b.days_left + 'd left</span><span class="chip g tipl" data-tip="The owner\'s own USDC covers this brief and their other open briefs, read on-chain ' + when(b.owner_funds.checked_at) + '">' + ic('shield') + 'Funds checked on-chain</span></div>' +
      '<div><h2>' + esc(shortName(b.name)) + '</h2><a class="lnk" href="' + esc(b.url) + '" target="_blank" rel="noopener">cymetica.com' + esc(b.path) + ' ↗</a></div>' +
      (b.say_line ? '<p class="say" style="margin:0;color:var(--text2)">“' + esc(b.say_line) + '”</p>' : '') +
      '<div class="ufg tipl" data-tip="Shared by every promoter on this brief, first come first paid: when it reaches 0, nothing more is counted"><span>Up for grabs <span class="i">i</span></span><b>' + usd(b.up_for_grabs_usdc) + '<small>of ' + usd(b.budget_usdc) + ' USDC</small></b></div>' +
      '<div class="tile" style="padding:12px 14px"><div class="k">Spent so far</div><div class="meter"><i style="width:' + (100 * spent / b.budget_usdc).toFixed(1) + '%"></i></div></div>' +
      '<div class="pays">' + pays.map((p) => '<div data-tip="' + p[2] + '"><b>' + price(b[p[0]]) + '<small>USDC</small></b><span>' + p[1] + '</span></div>').join('') + '</div>' +
      (tk ? '<div class="mylink"><div><span class="dim num" style="font-size:11px">YOUR LINK</span><br><b>cymetica.com/' + esc(tk.slug) + '</b></div><button class="btn g" data-copytext="https://cymetica.com/' + esc(tk.slug) + '">' + ic('copy') + 'Copy</button></div>' +
          '<div class="own"><input class="in" placeholder="Your post on X: https://x.com/…"><button class="btn c" data-act="registered">Register post</button></div>' :
        '<button class="btn g lg full" data-take="' + b.id + '">Take it · get my link ' + ic('arrow') + '</button>') +
      ((b.materials || []).length ? '<div class="ch" style="margin:6px 0 0"><h3>Materials to post</h3><span class="chip c">' + b.materials.length + '</span><span class="sp"></span><span class="dim num" style="font-size:11.5px">from the owner</span></div>' +
        '<div class="mgrid">' + b.materials.filter((m) => m.kind !== 'text').concat(b.materials.filter((m) => m.kind === 'text')).map((m) => matTile(m, b.path)).join('') + '</div>' : '') +
      '<details class="fold"><summary>' + ic('shield') + 'How results are counted' + ic('down', 'chev') + '</summary><div class="fb">' + rulesGrid().replace('class="rules"', 'class="rules" style="grid-template-columns:1fr 1fr"') + '</div></details>' +
    '</div>';
    show();
  }
  function take(id) {
    const slug = 'c/' + Math.random().toString(36).slice(2, 10);
    S.taken[id] = { slug: slug };
    toast('Taken · your link is cymetica.com/' + slug);
    openBrief(id);
    const g = $('view'); if (location.hash.indexOf('#market') === 0 || location.hash === '' || location.hash === '#board') g.innerHTML = market();
  }
  function agentDrawer() {
    $('drawer').innerHTML = '<div class="db" style="margin-top:0;padding-top:26px"><div class="ch"><h3 style="font-size:22px">Agent prompts</h3><span class="sp"></span><button class="btn sm gh" data-act="close">' + ic('close') + '</button></div>' +
      [['Promote from your AI agent', PAGE.market_hero.agent_prompt, 'agent_prompt'], ['Work my queues', PAGE.queue_prompt, 'queue_prompt'], ['Trade from your own AI agent', PAGE.trade_prompt, 'trade_prompt']].map((p) =>
        '<div class="card pad" style="display:grid;gap:10px"><b>' + p[0] + '</b><pre class="code">' + linkify(p[1]) + '</pre><div><button class="btn c sm" data-copy="' + p[2] + '">' + ic('copy') + 'Copy prompt</button></div></div>').join('') + '</div>';
    show();
  }

  /* ---------------- the dashboard ---------------- */
  function counts() {
    const mine = api('/api/v1/promo/mine'), rw = api('/api/v1/creator/rewards').summary;
    return { products: mine.products.products.length, taken: (mine.taken.takes || []).length, queues: PAGE.rail_counts.queues,
      journalists: api('/api/v1/creator/journalist-requests').stats.open, radar: PAGE.radar.length,
      links: api('/api/v1/creator/expire76/links').summary.links, rewards: rw.paid };
  }
  const NAV = [['MY PRODUCTS', [['products', 'My products', 'box']]],
    ['PROMOTE', [['today', 'Today', 'today'], ['taken', 'Briefs I took', 'briefs'], ['queues', 'Queues', 'queues'], ['journalists', 'Journalists', 'press'],
      ['radar', 'Radar apps', 'radar'], ['kits', 'Kits', 'kits'], ['links', 'Pages & links', 'link'], ['rewards', 'Rewards', 'rewards'],
      ['key', 'Agent key', 'key'], ['company', 'Start an app and a company', 'company']]]];
  const TITLES = { products: 'My products', today: 'Today', taken: 'Briefs I took', queues: 'Queues', journalists: 'Journalists', radar: 'Radar apps',
    kits: 'Kits', links: 'Pages & links', rewards: 'Rewards', key: 'Agent key', company: 'Start an app and a company' };
  function rail(tab) {
    const c = counts(), rw = api('/api/v1/creator/rewards').summary;
    return '<aside class="rail"><div class="me"><span class="av lg">E</span><div><b>' + ME + '</b><span>' + c.products + ' products · ' + c.links + ' links</span></div></div>' +
      NAV.map((g) => '<div class="rsec">' + g[0] + '</div><nav class="rnav">' + g[1].map((t) => {
        const n = c[t[0]];
        return '<a href="#me/' + t[0] + '" class="' + (t[0] === tab ? 'on' : '') + '">' + ic(t[2]) + t[1] + (n != null ? '<span class="n' + (t[0] === 'queues' ? ' hot' : '') + '">' + fmt(n) + '</span>' : '') + '</a>';
      }).join('') + '</nav>').join('') +
      '<div class="rlinks"><a href="#market">' + ic('market') + 'Promo Market</a><a href="https://cymetica.com/' + ME + '" target="_blank" rel="noopener">' + ic('ext') + 'Your public page</a><a href="#" data-act="agent">' + ic('agent') + 'Agent prompts</a></div>' +
      '<div class="earn"><div class="k">Earned promoting · ' + rw.paid + ' posts</div><div class="v">' + fmt(rw.et10) + ' <small>ET10</small></div><div class="s">+ ' + fmt(rw.etlp) + ' ETLP</div></div></aside>';
  }
  function dash(tab, inner) {
    const right = { products: '<a class="btn g" href="#new">' + ic('plus') + 'Post a brief</a>',
      links: '<button class="btn c sm" data-go="#me/kits">' + ic('plus') + 'Create a page</button>',
      queues: '<button class="btn sm" data-act="agent">' + ic('agent') + 'From your agent</button>',
      today: '<button class="btn sm" data-act="agent">' + ic('agent') + 'From your agent</button>' }[tab] || '';
    const sub = { products: 'built with Build it Better', today: dShort('2026-10-26') + ' 2026', queues: 'threads your pages answer',
      journalists: 'interview and article requests', radar: 'post these where their users already are' }[tab] || '';
    const body = inner || '<div class="ph"><h1>' + TITLES[tab] + '</h1>' + (sub ? '<span class="sub">' + sub + '</span>' : '') + '<span class="sp"></span>' + right + '</div>' +
      ({ products: products, today: today, taken: taken, queues: queues, journalists: journalists, radar: radar, kits: kits, links: links,
        rewards: rewards, key: agentKey, company: company }[tab] || products)();
    return '<div class="wrap"><div class="app">' + rail(tab) + '<section class="main">' + body + '</section></div></div>';
  }
  function tile(icon, k, v, s, c, tip) {
    return '<div class="tile"' + (c ? ' style="--c:' + c + '"' : '') + (tip ? ' data-tip="' + esc(tip) + '"' : '') + '><div class="k">' + ic(icon) + k + (tip ? ' <span class="i">i</span>' : '') + '</div><div class="v">' + v + '</div>' + (s ? '<div class="s">' + s + '</div>' : '') + '</div>';
  }
  // a bar per day; several series stack. `labels` are the 14 days.
  const SER = ['#00ff88', '#00cfff', '#3b82f6', '#a9b8cc', '#ff4444'];
  function vbars(series, labels, H, none) {
    const W = 700, n = labels.length, bw = W / n, h = H || 150; let o = '';
    const tot = labels.map((_, i) => sum(series, (s) => s[i] || 0)), max = Math.max(1, ...tot);
    for (let i = 0; i < n; i++) { let y = h; series.forEach((s, k) => { const hh = (s[i] || 0) / max * (h - 8); if (hh > 0) { y -= hh; o += '<rect x="' + (i * bw + bw * 0.18).toFixed(1) + '" y="' + y.toFixed(1) + '" width="' + (bw * 0.64).toFixed(1) + '" height="' + hh.toFixed(1) + '" rx="3" fill="' + SER[k % SER.length] + '" opacity=".92"/>'; } }); }
    let grid = ''; for (let g = 1; g < 4; g++) grid += '<path d="M0 ' + (h * g / 4).toFixed(1) + 'H' + W + '" stroke="#16233a" stroke-dasharray="3 5"/>';
    const empty = !tot.some((x) => x > 0);
    return '<div class="bars"><svg viewBox="0 0 ' + W + ' ' + h + '" preserveAspectRatio="none" style="width:100%;height:' + h + 'px">' + grid + o +
      '<path d="M0 ' + (h - .5) + 'H' + W + '" stroke="#1e3050"/></svg>' + (empty ? '<div class="none"><span>' + esc(none || 'Nothing yet') + '</span></div>' : '') +
      '<div class="dl"><span>' + dShort(labels[0]) + '</span><span>' + dShort(labels[n - 1]) + '</span></div></div>';
  }

  /* my products: each app once, its picture, its traffic; Create brief, then what the brief brought */
  function products() {
    const M = api('/api/v1/promo/mine').products, T = M.totals;
    const series = M.series.map((s) => s.days);
    return '<div class="tiles">' +
        tile('coin', 'Up for grabs in your briefs', '<span class="pos">' + usd(T.up_for_grabs_usdc) + '</span><small>USDC</small>', M.live_briefs + ' live brief' + (M.live_briefs === 1 ? '' : 's'), '#00ff88') +
        tile('eye', 'Visitors brought', fmt(T.visitors_14d), 'last 14 days') +
        tile('users', 'New users', fmt(T.new_users), 'counted and payable', '#3b82f6') +
        tile('wallet', 'Spent', usd(T.spent_usdc) + '<small>USDC</small>', 'earned by promoters', '#00cfff') +
      '</div>' +
      (M.payouts.pending_count ? '<div class="statusrow" style="border-color:rgba(0,255,136,.35)">' + ic('coin') + '<span class="grow"><b style="color:var(--text)">' + M.payouts.pending_count + ' earnings wait for your Pay</b> · ' + usd(M.payouts.pending_usdc) + ' USDC from your own wallet</span><button class="btn g sm" data-act="payall">Review and pay</button></div>' : '') +
      '<div class="card pad"><div class="ch"><h3>Visitors your briefs brought</h3><span class="sp"></span><span class="lgd">' + M.series.map((s, k) => '<span><i style="background:' + SER[k % SER.length] + '"></i>' + esc(shortName(s.name)) + '</span>').join('') + '</span></div>' +
        vbars(series.length ? series : [[]], M.day_labels, 150, 'No visitors from briefs yet') + '</div>' +
      '<div class="grid4">' + M.products.map(productCard).join('') + '</div>' +
      '<div class="note">' + ic('lock') + '<span>' + esc(PAGE.products_note) + '</span></div>';
  }
  function productCard(p) {
    const b = p.brief, r = b && results(b.id), t = p.traffic_30d;
    return '<article class="pc" data-product="' + esc(p.path) + '"><div class="img"><img alt="" src="' + pic(p.path) + '">' +
        (b ? '<div class="tl"><span class="chip g"><i class="live"></i>Live · ' + b.days_left + 'd left</span></div>' : '') + '</div>' +
      '<div class="bd"><div class="nm"><b title="' + esc(p.name) + '">' + esc(shortName(p.name)) + '</b></div><a class="lnk" href="' + esc(p.url) + '" target="_blank" rel="noopener">cymetica.com' + esc(p.path) + ' ↗</a>' +
        '<div class="tr" data-tip="Every visit to the product in the last 30 days, brief or not"><span><b>' + fmt(t.visitors) + '</b> visitors</span><span><b>' + fmt(t.views) + '</b> views</span><span><b>' + fmt(t.uses) + '</b> uses</span></div>' +
        (b ? '<div class="r3"><div><b class="pos">' + usd(b.up_for_grabs_usdc) + '</b><span>USDC left</span></div><div><b>' + fmt(r.visitors_14d) + '</b><span>visitors</span></div><div><b>' + r.new_users.counted + '</b><span>users</span></div></div>' +
          '<a class="btn sm full" href="#mybrief/' + b.id + '">Open the brief ' + ic('arrow') + '</a>' :
          '<div class="nob">No brief yet</div><a class="btn g sm full" href="#new' + esc(p.path) + '">' + ic('plus') + 'Create brief</a>') +
      '</div></article>';
  }
  function openProduct(path) {
    const p = api('/api/v1/promo/mine').products.products.find((x) => x.path === path); if (!p) return;
    const b = p.brief, t = p.traffic_30d;
    $('drawer').innerHTML = '<div class="dh"><img alt="" src="' + pic(p.path) + '"><button class="x" data-act="close">' + ic('close') + '</button></div><div class="db">' +
      '<div><h2>' + esc(shortName(p.name)) + '</h2><a class="lnk" href="' + esc(p.url) + '" target="_blank" rel="noopener">cymetica.com' + esc(p.path) + ' ↗</a>' +
        '<div class="meta" style="margin-top:8px"><span class="chip">Build it Better #' + p.issue_id + '</span>' + (b ? '<span class="chip g"><i class="live"></i>Brief live · ' + b.days_left + 'd left</span>' : '<span class="chip">No brief yet</span>') + '</div></div>' +
      '<div class="tiles" style="--n:3">' + tile('eye', 'Visitors', fmt(t.visitors), '30 days') + tile('reads', 'Views', fmt(t.views), '30 days') + tile('clicks', 'Uses', fmt(t.uses), '30 days') + '</div>' +
      (b ? '<a class="btn g lg full" href="#mybrief/' + b.id + '">Open the brief ' + ic('arrow') + '</a>' : '<a class="btn g lg full" href="#new' + esc(p.path) + '">' + ic('plus') + 'Create a brief for it</a>') +
    '</div>';
    show();
  }

  /* today: the creator's own numbers, the post of the day, a post of their own */
  function linkTiles() {
    const L = api('/api/v1/creator/expire76/links'), s = L.summary, days = L.links[0].series.map((d) => d.day);
    const tot = days.map((_, i) => [sum(L.links, (l) => l.series[i].click), sum(L.links, (l) => l.series[i].read), sum(L.links, (l) => l.series[i].like)]);
    const l14 = (k) => sum(tot, (d) => d[k]);
    const likeTip = 'Corrected on ' + s.likes_correction.date + ': ' + s.likes_excluded + ' of your likes are no longer shown — ' + s.likes_correction.reason;
    return { tiles: '<div class="tiles" style="--n:5">' +
        tile('link', 'Links', fmt(s.links), 'pages and tracked links') +
        tile('clicks', 'Clicks', fmt(s.clicks), '<b>+' + fmt(l14(0)) + '</b> in 14 days', '#00ff88', 'Someone followed a tracked URL') +
        tile('reads', 'Reads', fmt(s.reads), '<b>+' + fmt(l14(1)) + '</b> in 14 days', null, 'A page was opened, or a reader clicked through from it') +
        tile('likes', 'Likes', fmt(s.likes), '<b>+' + fmt(l14(2)) + '</b> in 14 days', '#3b82f6', likeTip) +
        tile('uniq', 'Unique visitors', fmt(s.unique_visitors), 'all time') + '</div>',
      chart: vbars([tot.map((d) => d[0]), tot.map((d) => d[1]), tot.map((d) => d[2])], days, 120, 'No activity in 14 days') };
  }
  function today() {
    const P = PAGE, posts = api('/api/v1/creator/posts'), lt = linkTiles(), m = P.measure;
    const own = posts.posts.map((p) => '<div class="statusrow">' + ic('x') + '<span class="chip r">' + esc(p.reward_status.toUpperCase()) + '</span><span class="grow" title="' + esc(p.url) + '">' + esc(p.reward_note) + '</span><span class="dim">' + dShort(p.replied_at) + '</span></div>').join('');
    return lt.tiles +
      '<div class="card prio"><div class="l"><div class="ch"><span class="kick">Tweet this now · top priority</span><span class="chip c tipd" data-tip="' + esc(P.tweet_note) + '">' + esc(P.tweet_nth) + ' today <span class="i">i</span></span><span class="sp"></span><span class="chip">' + ic('x') + 'X post</span></div>' +
        '<div class="tweet">' + linkify(P.tweet) + '</div>' +
        '<div class="cc"><span>' + P.tweet_chars + ' / 280</span><span class="meter"><i style="width:' + (100 * P.tweet_chars / 280).toFixed(1) + '%"></i></span><span>weighted characters</span></div>' +
        '<div class="acts"><button class="btn g" data-copytext="' + esc(P.tweet) + '">' + ic('copy') + 'Copy the tweet</button>' +
          '<a class="btn" href="https://x.com/intent/post?text=' + encodeURIComponent(P.tweet) + '" target="_blank" rel="noopener">' + ic('x') + 'Open in X ↗</a>' +
          '<button class="btn c" data-act="posted">' + ic('check') + 'Mark posted</button></div></div>' +
        '<div class="r"><img alt="" src="' + esc(P.tweet_img) + '" onerror="this.onerror=null;this.src=\'art/company.svg\'"><div class="meta" style="display:grid"><span>X may not show the link card at once: attach the graphic.</span><button class="btn sm" data-act="dl" data-what="graphic">' + ic('down') + 'Save graphic</button></div></div></div>' +
      '<div class="g2"><div class="card pad"><div class="ch"><h3>Last 14 days</h3><span class="sp"></span><span class="lgd"><span><i style="background:#00ff88"></i>clicks</span><span><i style="background:#00cfff"></i>reads</span><span><i style="background:#3b82f6"></i>likes</span></span></div>' + lt.chart + '</div>' +
        '<div class="card pad" style="display:grid;gap:12px;align-content:start"><div class="ch" style="margin:0"><h3>Wrote your own post?</h3><span class="i tipr" data-tip="' + esc(P.own_post_lead) + '">i</span><span class="sp"></span><span class="chip">up to ' + posts.daily_cap + ' a day</span></div>' +
          '<div class="own"><input class="in" placeholder="https://x.com/you/status/…"><button class="btn c" data-act="registered">Register post</button></div>' + own +
          '<div class="dim num" style="font-size:11.5px">' + esc(posts.rule) + '</div></div></div>' +
      '<div class="measure">' + ic('uniq') + 'All creators, last 30 days: <b>' + m.per_link_day + '</b> clicks per posted link per day <span class="dim">(median ' + m.median + ')</span> · <b>' + fmt(m.links) + '</b> links · <b>' + fmt(m.uniq) + '</b> unique visitors</div>' +
      '<details class="fold"><summary>' + ic('today') + 'Why post, step by step' + ic('down', 'chev') + '</summary><div class="fb" style="display:grid;gap:14px">' +
        '<div class="dim" style="font-size:13.5px">' + esc(P.why_post) + '</div><ol class="steps">' + P.step_by_step.map((s) => '<li><span>' + esc(s) + '</span></li>').join('') + '</ol></div></details>';
  }

  /* briefs I took: my link, what it brought, what I earned */
  function taken() {
    const tk = api('/api/v1/promo/mine').taken, list = tk.takes || [];
    return '<div class="tiles" style="--n:3">' + tile('briefs', 'Briefs taken', fmt(list.length), '') +
        tile('coin', 'Earned, payout pending', '<span class="pos">' + usd(tk.earned_usdc) + '</span><small>USDC</small>', '', '#00ff88') +
        tile('eye', 'Visitors you brought', fmt(sum(list, (t) => t.visitors || 0)), 'through your links') + '</div>' +
      (list.length ? '<div class="card"><table class="tbl"><thead><tr><th>Brief</th><th>Your link</th><th class="n">Visitors</th><th class="n">Posts</th><th class="n">New visitors</th><th class="n">New users</th><th class="n">Earned</th><th></th></tr></thead><tbody>' +
          list.map((t) => '<tr><td><div class="tw" style="gap:12px"><img alt="" src="' + pic(t.path) + '" style="width:64px;height:36px;border-radius:7px;object-fit:cover"><span class="ttl">' + esc(t.name) + '<small>taken ' + dShort(t.taken_at) + '</small></span></div></td>' +
            '<td><span class="lnk">' + esc(t.tracked_url.replace('https://', '')) + '</span></td><td class="n">' + fmt(t.visitors) + '</td><td class="n">' + t.posts + '</td><td class="n">' + fmt(t.new_visitors) + '</td><td class="n">' + t.new_users + '</td>' +
            '<td class="n pos">' + usd(t.earned_usdc) + '</td><td><span class="chip">payout pending</span></td></tr>').join('') + '</tbody></table></div>' :
        '<div class="card"><div class="empty">' + holo(46) + '<b>No brief taken yet</b><span>' + esc(PAGE.taken_empty) + '</span><a class="btn g" href="#market" style="margin-top:8px">Open the Promo Market ' + ic('arrow') + '</a></div></div>') +
      '<div class="note">' + ic('wallet') + '<span>' + esc(PAGE.taken_pay) + '</span></div>';
  }

  /* queues: a list on the left, the thread beside it */
  const CH = [['reddit', 'Reddit', 'reddit'], ['x', 'X / Twitter', 'x'], ['telegram', 'Telegram', 'telegram'], ['discord', 'Discord', 'discord'], ['linkedin', 'LinkedIn', 'linkedin'], ['youtube', 'YouTube', 'youtube']];
  function queues() {
    const P = PAGE, cc = P.channel_counts;
    const opts = '<option>every tool (one mixed queue) (' + fmt(P.queue_total) + ')</option>' + P.queue_tools.map((t) => '<option>' + esc(t[0]) + ' (' + t[1] + ')</option>').join('') +
      P.queue_tools_empty.map((t) => '<option>' + esc(t) + ' (0)</option>').join('');
    let body;
    if (S.qch === 'reddit' || S.qch === 'x') body = queueSplit();
    else if (S.qch === 'telegram' || S.qch === 'discord') body = communities(S.qch);
    else body = '<div class="card"><div class="empty"><b>' + (S.qch === 'linkedin' ? 'LinkedIn' : 'YouTube') + ': next</b><span>Not open yet on the platform.</span></div></div>';
    return '<div class="qbar"><span class="dim num" style="font-size:11px;letter-spacing:1px">QUEUE FOR</span><select class="in" aria-label="Queue for">' + opts + '</select><div class="seg">' + CH.map((c) =>
        '<button data-qch="' + c[0] + '" class="' + (S.qch === c[0] ? 'on' : '') + (cc[c[0]] === 'next' ? ' off' : '') + '">' + ic(c[2]) + c[1] + ' <span class="n">' + esc(cc[c[0]]) + '</span></button>').join('') + '</div></div>' + body;
  }
  function queueSplit() {
    const red = S.qch === 'reddit', D = api(red ? '/api/v1/creator/reddit-leads' : '/api/v1/creator/twitter-leads'), L = D.leads;
    const it = L[Math.min(S.qsel, L.length - 1)];
    const pages = api('/api/v1/creator/reddit-leads').artifacts;
    const list = L.map((l, k) => '<button class="item' + (k === S.qsel ? ' on' : '') + '" data-qsel="' + k + '"><div class="m">' +
      (red ? ic('reddit') + 'r/' + esc(l.subreddit) : ic('x') + esc(l.group_name)) + '<span>· ' + ago(l.posted_at) + '</span><span class="rel">rel ' + l.relevance + '</span></div>' +
      '<div class="t">' + esc(red ? l.title : l.body) + '</div></button>').join('');
    const step = S.qpage == null ? 0 : 1;
    const view = '<div class="meta">' + (red ? '<span class="chip">' + ic('reddit') + 'r/' + esc(it.subreddit) + '</span><span class="chip">' + esc(it.kind) + '</span>' : '<span class="chip">' + ic('x') + esc(it.group_name) + '</span><span class="chip">' + fmt(it.author_followers) + ' followers</span><span class="chip">' + fmt(it.impressions) + ' views</span>') +
        '<span class="chip g">relevance ' + it.relevance + '</span><span class="chip c">→ ' + esc(it.tool_name) + '</span></div>' +
      '<div class="meta">' + (red ? 'u/' : '@') + esc(it.author) + (red ? ' · score ' + it.score : '') + ' · ' + when(it.posted_at) + '</div>' +
      (red ? '<h2>' + esc(it.title) + '</h2>' : '') + '<div class="body">' + esc(it.body) + '</div>' +
      (it.permalink ? '<div><a class="btn sm" href="' + esc(it.permalink) + '" target="_blank" rel="noopener">' + ic(red ? 'reddit' : 'x') + 'Open on ' + (red ? 'Reddit' : 'X') + ' ↗</a></div>' : '') +
      '<div class="stepper">' + PAGE.queue_steps.map((s, k) => '<div class="' + (k <= step ? 'on' : '') + '"><i>' + (k + 1) + '</i>' + esc(red ? s : s.replace('Reddit', 'X')) + '</div>').join('') + '</div>' +
      '<div class="ch" style="margin:0"><b style="font:700 13px var(--sans)">Pick a page</b><span class="dim num" style="font-size:11.5px">— or create one for ' + esc(it.tool_name) + '</span><span class="i tipr" data-tip="' + esc(PAGE.queue_hint) + '">i</span></div>' +
      '<div class="pagepick">' + pages.map((p, k) => '<button data-qpage="' + k + '" class="' + (S.qpage === k ? 'on' : '') + '">' + esc(p.title.replace(' (Claude artifact)', '')) + '<small>' + esc(p.surface) + '</small></button>').join('') + '</div>' +
      '<div class="acts"><button class="btn g" data-act="reply"' + (S.qpage == null ? ' disabled' : '') + '>' + ic('reply') + 'Reply with this page</button>' +
        '<button class="btn c" data-go="#me/kits">' + ic('plus') + 'Create page for ' + esc(it.tool_name) + '</button><button class="btn gh" data-act="skip">' + ic('skip') + 'Skip</button></div>';
    return '<div class="card split"><div class="list">' + list + '</div><div class="view">' + view + '</div></div>';
  }
  function communities(ch) {
    const C = api('/api/v1/creator/channel-posts'), list = C.targets.filter((t) => t[ch]);
    const state = { joined: ['g', 'joined'], pending: ['c', 'join pending'], failed: ['r', 'could not join'], left: ['', 'left'], invite_needed: ['', 'invite needed'] };
    return '<div class="comm">' + list.map((t) => {
      const c = t[ch], s = state[c.join_state] || ['', c.join_state], busy = t[ch + '_busy'];
      return '<div class="card"><div class="ch" style="margin:0"><b>' + esc(t.symbol) + '</b><span class="dim">' + esc(t.name) + '</span><span class="sp"></span><span class="num ' + (t.ret_30d < 0 ? 'neg' : 'pos') + '">' + (t.ret_30d > 0 ? '+' : '') + t.ret_30d.toFixed(1) + '% 30 d</span></div>' +
        '<div class="meta"><a class="lnk" href="' + esc(c.url) + '" target="_blank" rel="noopener">' + ic(ch) + esc(c.handle) + ' ↗</a><span class="chip ' + s[0] + '">' + esc(s[1]) + '</span>' + (busy ? '<span class="chip">posted in 24 h</span>' : '') + '</div>' +
        '<pre class="code" style="max-height:90px">' + linkify(t.default_text) + '</pre>' +
        '<div class="acts"><button class="btn sm g"' + (busy || c.join_state !== 'joined' ? ' disabled' : '') + ' data-act="sent">Post to ' + esc(c.handle) + '</button><button class="btn sm" data-copytext="' + esc(t.default_text) + '">' + ic('copy') + 'Copy</button></div></div>';
    }).join('') + '</div>' + '<div class="note">' + ic('telegram') + '<span>Sent from EventTrader\'s own account, one post per group per 24 h.</span></div>';
  }

  /* journalists: the request beside its list */
  function journalists() {
    const J = api('/api/v1/creator/journalist-requests'), st = J.stats, L = J.requests, it = L[Math.min(S.jsel, L.length - 1)];
    const list = L.map((q, k) => '<button class="item' + (k === S.jsel ? ' on' : '') + '" data-jsel="' + k + '"><div class="m">' + ic('press') + esc(q.outlet) + '<span class="chip' + (q.hours_left < 24 ? ' r' : '') + '" style="height:20px;margin-left:auto">' + Math.round(q.hours_left) + 'h left</span></div><div class="t">' + esc(q.subject) + '</div></button>').join('');
    return '<div class="meta"><span class="chip c">' + st.open + ' open for you</span><span class="chip">' + st.open_all_topics + ' on every topic</span><span class="chip">' + st.pitched + ' pitched</span><span class="chip">' + st.published + ' published</span><span class="i tipl" data-tip="' + esc(PAGE.journalists_lead) + '">i</span></div>' +
      '<div class="card split"><div class="list">' + list + '</div><div class="view">' +
        '<div class="meta"><span class="chip">' + esc(it.outlet) + '</span><span class="chip">' + esc(it.category) + '</span><span class="chip g">relevance ' + (+it.relevance).toFixed(2) + '</span>' + (it.topics || []).map((t) => '<span class="chip c">' + esc(t) + '</span>').join('') + '</div>' +
        '<div class="meta">' + ic('clock') + 'deadline ' + when(it.deadline_at) + ' · <b style="color:' + (it.hours_left < 24 ? 'var(--red)' : 'var(--text)') + '">' + Math.round(it.hours_left) + ' h left</b></div>' +
        '<h2>' + esc(it.subject) + '</h2><div class="body" style="max-height:240px">' + esc(it.query) + '</div>' +
        '<label class="f">Your answer<textarea class="in" rows="5" placeholder="Write your own answer, then email it to the journalist before the deadline."></textarea></label>' +
        '<div class="acts"><button class="btn g" data-act="pitched">' + ic('mail') + 'Mark pitched</button><button class="btn gh" data-act="skip">' + ic('skip') + 'Skip</button></div></div></div>';
  }

  /* radar apps: five apps, one open, its posts ready to copy */
  function radar() {
    const R = PAGE.radar, a = R[S.radar];
    const chips = (l, c) => l.map((x) => '<span class="chip ' + (c || '') + '">' + esc(x) + '</span>').join('');
    return '<div class="rapps">' + R.map((x, k) => '<button data-radar="' + k + '" class="' + (k === S.radar ? 'on' : '') + '"><b>' + esc(x.name) + '</b><span>from ' + esc(x.from) + '</span></button>').join('') + '</div>' +
      '<div class="card pad" style="display:grid;grid-template-columns:1.2fr 1fr;gap:26px"><div style="display:grid;gap:12px;align-content:start">' +
          '<span class="kick">Rebuilt from ' + esc(a.from) + ' · ' + esc(a.from_kind) + '</span><h2 style="margin:0;font:26px var(--display)">' + esc(a.name) + '</h2>' +
          '<div style="color:var(--text2)">' + esc(a.line) + '</div>' +
          '<div class="pledge" style="display:grid;gap:7px">' + a.points.map((p) => '<div class="note" style="color:var(--text2)">' + ic('check') + '<span>' + esc(p) + '</span></div>').join('') + '</div>' +
          '<div class="acts"><button class="btn g" data-act="tracked">' + ic('link') + 'Get my tracked link</button><a class="btn" href="' + esc(a.url) + '" target="_blank" rel="noopener">Open ' + esc(a.name) + ' ↗</a></div></div>' +
        '<div class="who2"><div class="row"><span>Who</span><span style="color:var(--text2)">' + esc(a.who) + '</span></div>' +
          '<div class="row"><span>Subreddits</span>' + chips(a.subs) + '</div><div class="row"><span>X searches</span>' + chips(a.x_searches, 'c') + '</div>' +
          '<div class="row"><span>Telegram</span>' + chips(a.groups, 'b') + '</div></div></div>' +
      '<div class="rgrid"><div class="card pad post"><div class="hd">' + ic('reddit') + 'Reddit post<span class="sp"></span><button class="btn sm" data-copytext="' + esc(a.reddit_title) + '">Copy title</button><button class="btn sm" data-copytext="' + esc(a.reddit_body) + '">Copy body</button></div>' +
          '<div class="ptitle">' + esc(a.reddit_title) + '</div><pre class="code" style="max-height:200px">' + linkify(a.reddit_body) + '</pre></div>' +
        '<div style="display:grid;gap:18px"><div class="card pad post"><div class="hd">' + ic('x') + 'X post<span class="sp"></span><span class="dim num" style="font-size:11px">' + weighted(a.x_post) + ' / 280</span><button class="btn sm" data-copytext="' + esc(a.x_post) + '">Copy</button>' +
            '<a class="btn sm" href="https://x.com/intent/post?text=' + encodeURIComponent(a.x_post) + '" target="_blank" rel="noopener">Open in X ↗</a></div><div class="tweet" style="font-size:13.5px">' + linkify(a.x_post) + '</div></div>' +
          '<div class="card pad post"><div class="hd">' + ic('telegram') + 'Telegram post<span class="i tipr" data-tip="Sent from EventTrader\'s own account, one post per group per 24 h">i</span><span class="sp"></span></div><div class="tweet" style="font-size:13.5px">' + linkify(a.tg_post) + '</div>' +
            '<div class="acts">' + a.groups.map((g) => '<button class="btn sm c" data-act="sent">Post to ' + esc(g) + '</button>').join('') + '</div></div></div></div>';
  }

  /* kits: a page, the post kit, a community kit */
  function catalogue() {
    const named = PAGE.catalogue_named, nm = new Set(named.map((x) => x[0]));
    const tools = PAGE.queue_tools.map((t) => t[0]).concat(PAGE.queue_tools_empty).filter((t) => !nm.has(t)).sort((a, b) => a.toLowerCase().localeCompare(b.toLowerCase()));
    return named.concat(tools.map((t) => [t, 'tool']));
  }
  function kits() {
    const K = api('/api/v1/creator/post-kit'), k = K.kit, cat = catalogue();
    const sel = '<select class="in">' + cat.map((c, i) => '<option' + (i === S.kitTool ? ' selected' : '') + '>' + esc(c[0]) + ' · ' + c[1] + '</option>').join('') + '</select>';
    return '<div class="kits">' +
      '<div class="card"><span class="kick">Page <span class="i tipl" data-tip="' + esc(PAGE.create_page_lead) + '">i</span></span><h3>Create a Claude artifact page</h3>' +
        '<label class="f">Tool, app, product or service <span class="dim">(' + cat.length + ')</span>' + sel + '</label><label class="f">Headline (optional)<input class="in"></label>' +
        '<label class="f">Your pitch (optional — the page\'s opening line)<textarea class="in" rows="3"></textarea></label><button class="btn g" data-act="pagemade">' + ic('plus') + 'Create artifact page</button></div>' +
      '<div class="card"><span class="kick">Post kit</span><h3>Hashtags and tags per outlet</h3><label class="f">Tool, app, product or service' + sel + '</label>' +
        '<div class="tags">' + k.hashtags.map((h) => '<span class="chip g">#' + esc(h) + '</span>').join('') + '<span class="chip c">' + esc(k.x.mention) + '</span></div>' +
        '<div class="outlets">' + [['x', 'X', k.x.rule], ['reddit', 'Reddit', k.reddit.rule], ['telegram', 'Telegram', k.telegram.rule], ['discord', 'Discord', k.discord.rule]].map((o) =>
          '<div><b>' + ic(o[0]) + o[1] + '</b><span>' + esc(o[2]) + '</span></div>').join('') + '</div>' +
        '<button class="btn c" data-copytext="' + esc(k.x.post) + '">' + ic('copy') + 'Copy X post</button>' +
        '<details class="fold"><summary>' + ic('today') + 'Playbook <span class="dim num">' + K.playbook.length + '</span>' + ic('down', 'chev') + '</summary><div class="fb"><ol class="steps">' +
          K.playbook.map((p) => '<li><span><b>' + esc(p.title) + '.</b> ' + esc(p.text) + '</span></li>').join('') + '</ol></div></details></div>' +
      '<div class="card"><span class="kick">Community kit <span class="i tipr" data-tip="' + esc(PAGE.community_lead) + '">i</span></span><h3>Bring Build it Better to a crypto community</h3>' +
        '<label class="f">Community (coin or project)<input class="in" placeholder="e.g. Akash Network"></label><label class="f">Its hashtag (optional)<input class="in" placeholder="#AKT"></label>' +
        '<label class="f">Narrative it rides<select class="in">' + PAGE.narratives.map((n) => '<option>' + esc(n) + '</option>').join('') + '</select></label>' +
        '<button class="btn g" data-act="kitmade">Make the kit</button></div></div>';
  }

  /* pages & links: one table; a row opens what hangs off it */
  function links() {
    const L = api('/api/v1/creator/expire76/links'), lt = linkTiles(), q = S.pgQ.toLowerCase();
    const cols = [['title', 'Page / link'], ['kind', 'Kind'], ['url', 'URL'], ['clicks', 'Clicks', 1], ['reads', 'Reads', 1], ['likes', 'Likes', 1], ['unique_visitors', 'Unique', 1], ['last_activity', 'Last', 1]];
    const rows = L.links.filter((l) => !q || (l.title + ' ' + l.slug).toLowerCase().includes(q))
      .sort((a, b) => (S.pgSort === 'last_activity' ? String(b.last_activity).localeCompare(String(a.last_activity)) : (b[S.pgSort] || 0) - (a[S.pgSort] || 0)));
    const kids = (l) => (l.children || []).map((c) => '<tr class="kid"><td>' + esc(c.title) + '</td><td><span class="chip">' + esc(c.kind) + '</span></td><td><span class="lnk">cymetica.com/c/' + esc(c.slug) + '</span> <span class="dim">→ ' + esc(String(c.target_url).replace('https://', '')) + '</span></td><td class="n">' + fmt(c.clicks) + '</td><td class="n">—</td><td class="n">—</td><td class="n">' + fmt(c.unique_visitors) + '</td><td></td></tr>').join('');
    const kinds = PAGE.link_kinds.map((k) => '<option>' + esc(k) + '</option>').join('');
    return lt.tiles +
      '<div class="card pad"><div class="ch"><h3>Track any other link</h3><span class="i tipl" data-tip="' + esc(PAGE.track_lead) + '">i</span></div>' +
        '<div class="trk"><label class="f">Target (choose a surface or paste a URL)<input class="in" list="surfaces" placeholder="https://…"><datalist id="surfaces">' + catalogue().map((c) => '<option value="' + esc(c[0]) + '">').join('') + '</datalist></label>' +
        '<label class="f">Title<input class="in"></label><label class="f">Kind<select class="in">' + kinds + '</select></label><button class="btn g" data-act="linkmade">' + ic('link') + 'Create link</button></div></div>' +
      '<div class="card"><div class="tbar"><input class="in" id="pgq" placeholder="Search your pages and links" value="' + esc(S.pgQ) + '"><span class="sp" style="flex:1"></span><span class="dim num" style="font-size:12px">' + rows.length + ' tracked links · a row opens its replies and buttons</span></div>' +
        '<table class="tbl"><thead><tr>' + cols.map((c) => '<th class="' + (c[2] ? 'n s' : '') + (S.pgSort === c[0] ? ' on' : '') + '"' + (c[2] ? ' data-pgsort="' + c[0] + '"' : '') + '>' + c[1] + '</th>').join('') + '<th>From</th></tr></thead><tbody>' +
        rows.map((l) => '<tr class="row' + (S.open[l.slug] ? ' open' : '') + '" data-row="' + esc(l.slug) + '"><td><div class="tw">' + ic('chev') + '<span class="ttl">' + esc(l.title.replace(' (Claude artifact)', '')) + '<small>' + (l.children || []).length + ' links under it · since ' + dShort(l.created_at) + '</small></span></div></td>' +
          '<td><span class="chip ' + (l.kind === 'artifact' ? 'c' : '') + '">' + esc(l.kind) + '</span></td><td><span class="lnk">cymetica.com/c/' + esc(l.slug) + '</span> <button class="btn sm gh" style="height:24px;padding:0 6px" data-copytext="https://cymetica.com/c/' + esc(l.slug) + '">' + ic('copy') + '</button></td>' +
          '<td class="n">' + fmt(l.clicks) + '</td><td class="n">' + fmt(l.reads) + '</td><td class="n">' + fmt(l.likes) + '</td><td class="n"><b>' + fmt(l.unique_visitors) + '</b></td><td class="n">' + (l.last_activity ? dShort(l.last_activity) : '—') + '</td>' +
          '<td class="ref">' + (l.top_referrers || []).slice(0, 2).map((r) => esc(r.host.replace('www.', '')) + ' ' + r.count).join(' · ') + '</td></tr>' + (S.open[l.slug] ? kids(l) : '')).join('') +
        '</tbody></table></div>';
  }

  /* rewards */
  function rewards() {
    const R = api('/api/v1/creator/rewards'), s = R.summary;
    const st = { paid: 'g', unverifiable: 'r', failed: 'r', pending: 'c' };
    return '<div class="tiles">' + tile('rewards', 'Posts rewarded', fmt(s.paid), s.unverifiable + ' unverifiable', '#00ff88') + tile('coin', 'ET10 earned', fmt(s.et10), fmt(s.per_post.et10) + ' per post') +
        tile('coin', 'ETLP earned', fmt(s.etlp), fmt(s.per_post.etlp) + ' per post', '#3b82f6') + tile('clock', 'Awaiting verification', fmt(s.pending), 'checked within minutes', null, PAGE.rewards_lead) + '</div>' +
      '<div class="card"><table class="tbl"><thead><tr><th>Where</th><th>Post</th><th>Status</th><th>When</th><th>Note</th><th></th></tr></thead><tbody>' +
        R.recent.map((r) => '<tr><td style="white-space:nowrap">' + esc(r.where) + '</td><td style="max-width:420px">' + esc(r.text) + '</td><td><span class="chip ' + (st[r.reward_status] || '') + '">' + esc(String(r.reward_status).toUpperCase()) + '</span></td>' +
          '<td class="num" style="white-space:nowrap;color:var(--text3)">' + dShort(r.replied_at) + '</td><td class="dim" style="font-size:12px">' + esc(r.reward_note || '') + '</td>' +
          '<td>' + (r.reply_url ? '<a class="lnk" href="' + esc(r.reply_url) + '" target="_blank" rel="noopener">your reply ↗</a>' : '') + '</td></tr>').join('') + '</tbody></table></div>';
  }

  /* agent key and the agent prompts */
  function agentKey() {
    return '<div class="card pad keyrow">' + ic('key') + '<div style="flex:1"><b style="font:17px var(--display)">A key for the agent that works your queues</b><div class="dim num" style="font-size:12px">' + PAGE.active_keys + ' active keys on this account · read + trade, never withdraw · shown once</div></div>' +
        '<span class="i tipr" data-tip="' + esc(PAGE.key_text) + '">i</span><button class="btn g" data-act="keymade">' + ic('plus') + 'Create key</button></div>' +
      '<div class="prompts">' + [['Work my queues', PAGE.queue_prompt, 'queue_prompt', PAGE.key_prompt_lead], ['Promote from your AI agent', PAGE.market_hero.agent_prompt, 'agent_prompt', 'Takes a brief with your key and posts your link.'],
        ['Trade from your own AI agent', PAGE.trade_prompt, 'trade_prompt', PAGE.trade_lead]].map((p) =>
        '<div class="card"><div class="ch" style="margin:0"><h3>' + p[0] + '</h3><span class="i tipr" data-tip="' + esc(p[3]) + '">i</span></div><pre class="code" style="max-height:330px">' + linkify(p[1]) + '</pre><div><button class="btn c sm" data-copy="' + p[2] + '">' + ic('copy') + 'Copy the prompt</button></div></div>').join('') + '</div>';
  }

  /* start an app and a company: the ten steps, one open at a time */
  function company() {
    const C = PAGE.company;
    return '<div class="guide"><div class="gsteps">' + C.steps.map((s, k) => '<details' + (k === 0 ? ' open' : '') + '><summary><i>' + (k + 1) + '</i>' + esc(s[0].replace(/\.$/, '')) + ic('down', 'chev') + '</summary><p>' + esc(s[1]) + '</p></details>').join('') + '</div>' +
      '<div class="card pad" style="display:grid;gap:14px;position:sticky;top:90px">' +
        '<div style="color:var(--text2);font-size:13.5px">' + esc(C.intro) + '</div>' +
        '<div class="tile" style="--c:#00cfff"><div class="k">' + ic('company') + 'Cymetica\'s stake</div><div class="v">1–10<small>%</small></div><div class="s">set by the measured AI compute cost</div></div>' +
        '<a class="btn g" href="https://cymetica.com/company" target="_blank" rel="noopener">' + ic('plus') + 'Create your company ↗</a><a class="btn" href="https://cymetica.com/companies/start/cayman" target="_blank" rel="noopener">Full guide ↗</a>' +
        '<div class="dim" style="font-size:11.5px">' + esc(C.disclaimer) + '</div></div></div>';
  }

  /* ---------------- Post a brief: one screen ---------------- */
  function defaultForm(path) {
    const prods = api('/api/v1/promo/mine').products.products, p = prods.find((x) => x.path === path) || prods[0];
    return { path: p.path, on: { post: true, user: true, visitor: true }, per_post: 2, per_user: 5, per_visitor: 0.05, budget: 50, days: 7, say: '',
      mats: [{ kind: 'image', title: 'Picture for posts', file: p.path.slice(1).replace('/', '-') + '.jpg', size: 'the product page, attached to posts', src: pic(p.path) },
        { kind: 'text', title: 'X post', body: '' }, { kind: 'link', title: 'Product page', url: p.url }] };
  }
  function formBrief(F) {
    const p = api('/api/v1/promo/mine').products.products.find((x) => x.path === F.path);
    return { id: 0, name: p.name, path: p.path, url: p.url, per_post_usdc: F.on.post ? F.per_post : 0, per_user_usdc: F.on.user ? F.per_user : 0,
      per_visitor_usdc: F.on.visitor ? F.per_visitor : 0, budget_usdc: F.budget, up_for_grabs_usdc: F.budget, days: F.days, days_left: F.days,
      status: 'open', say_line: F.say, owner_funds: { state: 'checking', checked_at: null }, mine: true, materials: F.mats.filter((m) => m.kind !== 'text' || m.body) };
  }
  function newBrief(path) {
    if (!S.form || (path && S.form.path !== path)) S.form = defaultForm(path);
    const F = S.form, prods = api('/api/v1/promo/mine').products, P = prods.products;
    const pr = (k, name, sub, v, step, tip) => '<div class="payrow' + (F.on[k] ? '' : ' off') + '"><button class="tog' + (F.on[k] ? ' on' : '') + '" data-tog="' + k + '" aria-label="' + name + '"></button>' +
      '<div' + (tip ? ' data-tip="' + esc(tip) + '"' : '') + '><b>' + name + '</b><span>' + sub + '</span></div><input class="in" data-f="per_' + k + '" inputmode="decimal" value="' + v + '" aria-label="' + name + ' in USDC, step ' + step + '"></div>';
    const matRow = (m, i) => m.kind === 'text' ?
      '<div class="mat txt"><div class="th">' + ic('text') + '</div><div><b>' + esc(m.title) + '</b><span>ready-made text, copied by promoters</span></div><button class="x" data-rmmat="' + i + '">' + ic('close') + '</button>' +
        '<textarea class="in" data-mat="' + i + '" placeholder="Write the post promoters can copy (their link is added at the end)">' + esc(m.body) + '</textarea></div>' :
      '<div class="mat"><div class="th">' + (m.kind === 'image' && m.src ? '<img alt="" src="' + esc(m.src) + '">' : ic(m.kind === 'video' ? 'video' : m.kind === 'link' ? 'link' : 'image')) + '</div>' +
        '<div><b>' + esc(m.title) + '</b><span>' + esc(m.size || m.url || m.file || '') + '</span></div><button class="x" data-rmmat="' + i + '">' + ic('close') + '</button></div>';
    const b = formBrief(F);
    const buy = [['post', F.per_post, 'posts'], ['user', F.per_user, 'new users'], ['visitor', F.per_visitor, 'new visitors']].filter((x) => F.on[x[0]] && x[1] > 0);
    const ok = F.budget >= prods.min_budget_usdc && buy.length && (!F.on.visitor || (F.per_visitor >= 0.01 && F.per_visitor <= 5));
    return '<div class="wrap"><div class="nbtop"><a class="back" href="#me/products">' + ic('arrow') + 'My products</a><h1>Post a brief</h1><span class="sp" style="flex:1"></span>' +
        '<span class="chip g tipr" data-tip="' + esc(PAGE.products_note) + '">' + ic('lock') + 'The budget stays in your own wallet</span></div>' +
      '<div class="nb">' +
        '<div class="card"><div class="colh"><span class="no">1</span><b>Product and pay</b></div>' +
          '<div class="pick">' + P.map((p) => '<button data-pick="' + esc(p.path) + '" class="' + (p.path === F.path ? 'on' : '') + '"><img alt="" src="' + pic(p.path) + '"><div><b>' + esc(shortName(p.name)) + '</b><span>cymetica.com' + esc(p.path) + '</span></div><em>' + fmt(p.traffic_30d.visitors) + ' / 30 d</em></button>').join('') + '</div>' +
          pr('post', 'Per post', 'on X, still up after 7 days', F.per_post, 1, 'Up to 3 posts a brief a day are paid') +
          pr('user', 'Per new user', 'signed up, own deposit, 14-day check', F.per_user, 1, 'Counted only when the user\'s own fees in 14 days reach this price') +
          pr('visitor', 'Per new visitor', 'first visit, no sign-up', F.per_visitor, 0.01, '0.01 to 5 USDC. Counted after a real browser check, never a hosting network, paid 7 days later') +
          '<div class="row2"><label class="f">Budget (USDC) · min ' + prods.min_budget_usdc + '<input class="in" data-f="budget" inputmode="decimal" value="' + F.budget + '"><div class="quick">' + [50, 100, 250, 500].map((v) => '<button data-budget="' + v + '">' + v + '</button>').join('') + '</div></label>' +
            '<label class="f">Runs for<div class="seg" style="height:42px;align-items:center">' + prods.days_choices.map((d) => '<button data-days="' + d + '" class="' + (F.days === d ? 'on' : '') + '">' + d + ' days</button>').join('') + '</div></label></div>' +
          '<label class="f" style="margin-top:14px">One line for promoters to say <span class="dim" id="saycnt">(' + F.say.length + ' / 280)</span><input class="in" data-f="say" maxlength="280" value="' + esc(F.say) + '" placeholder="optional"></label></div>' +
        '<div class="card"><div class="colh"><span class="no">2</span><b>Materials for promoters</b><span class="sp"></span><span class="chip c tipr" data-tip="New: promoters see these on the brief and download or copy them. Each download is counted on your brief\'s page.">NEW</span></div>' +
          '<label class="drop" id="drop">' + ic('upload') + '<b>Drop pictures or a video</b><span>PNG, JPG, GIF, MP4 or WebM · up to 50 MB each</span><input type="file" id="files" multiple accept="image/*,video/*" hidden></label>' +
          '<div class="mats">' + F.mats.map(matRow).join('') + '</div>' +
          '<div class="acts" style="margin-top:10px"><button class="btn sm" data-addmat="text">' + ic('text') + 'Add a text</button><button class="btn sm" data-addmat="link">' + ic('link') + 'Add a link</button></div></div>' +
        '<div class="card"><div class="colh"><span class="no">3</span><b>As promoters will see it</b></div><div class="preview">' + briefCard(b, true) +
          '<div><div class="dim num" style="font-size:11px;letter-spacing:1px;margin-bottom:6px">THIS BUDGET PAYS FOR UP TO</div><div class="buys">' +
            buy.map((x) => '<div><b>' + fmt(Math.floor(F.budget / x[1])) + '</b><span>' + x[2] + '</span></div>').join('') + '</div></div>' +
          '<div class="sendbar"><div class="note">' + ic('users') + '<span>One budget for every promoter who takes it: once ' + usd(F.budget) + ' USDC is spent, nothing more is counted or owed.</span></div><div class="note">' + ic('shield') + '<span>Opens only when your own USDC, read on-chain, covers ' + usd(F.budget) + ' USDC and your other open briefs.</span></div>' +
            '<button class="btn g lg full" data-act="publish"' + (ok ? '' : ' disabled') + '>Post the brief ' + ic('arrow') + '</button><a class="btn gh full" href="#me/products">Cancel</a></div></div></div>' +
      '</div></div>';
  }
  function publish() {
    const b = formBrief(S.form); b.id = 200 + S.posted.length; b.owner_funds = { state: 'covered', checked_at: '2026-10-26T10:16:00+00:00' };
    const days = api('/api/v1/promo/mine').products.day_labels;
    S.posted.push({ brief: b, results: { brief: b, promoters: 0, visitors_14d: 0, visitors_by_day: Object.fromEntries(days.map((d) => [d, 0])), users_by_day: days.map(() => 0),
      new_users: { counted: 0, checking: 0, not_counted: 0 }, new_visitors: { counted: 0, held: 0, not_counted: 0, not_counted_by_reason: [] }, users_not_by_reason: [],
      posts: { paid: 0, checking: 0 }, spent_usdc: 0, clicks: 0, sources: [], by_promoter: [], materials_used: b.materials.map((m) => [m.title, 0]), quotes: [] } });
    S.form = null;
    toast('Brief posted · your USDC covers it');
    location.hash = '#mybrief/' + b.id;
  }

  /* ---------------- a brief's own page: what it brought ---------------- */
  function ownerBrief(id) {
    const r = results(id); if (!r) return dash('products');
    const b = r.brief, spent = r.spent_usdc, days = Object.keys(r.visitors_by_day), vis = Object.values(r.visitors_by_day);
    const reasons = api('/api/v1/promo/how-counted').not_counted_reasons;
    const pays = [['per_post_usdc', 'per post'], ['per_user_usdc', 'per new user'], ['per_visitor_usdc', 'per new visitor']].filter((p) => +b[p[0]] > 0);
    const fun = [['Clicks on the links', r.clicks], ['Unique visitors', r.visitors_14d], ['New visitors counted', r.new_visitors.counted, 1], ['New users checking', r.new_users.checking + r.new_users.counted], ['New users counted', r.new_users.counted, 1]]
      .filter((f, k) => k !== 2 || b.per_visitor_usdc > 0);
    const fmax = Math.max(1, fun[0][1]);
    const srcMax = Math.max(1, ...r.sources.map((s) => s[1]));
    const SRC_IC = { X: 'x', Reddit: 'reddit', Telegram: 'telegram', Discord: 'discord', Other: 'globe' };
    const unpaid = r.by_promoter.filter((p) => !p.paid && p.earned_usdc > 0);
    const notRows = r.users_not_by_reason.map((x) => [reasons[x[0]] || x[0], x[1], 'user']).concat(r.new_visitors.not_counted_by_reason.map((x) => [x.text, x.count, 'visitor']));
    const inner = '<div class="ph"><a class="back" href="#me/products">' + ic('arrow') + 'My products</a></div>' +
      '<div class="card bdhead"><img alt="" src="' + pic(b.path) + '"><div><h1>' + esc(shortName(b.name)) + '</h1><div class="meta">' +
          '<span class="chip g"><i class="live"></i>' + (b.status === 'open' ? 'Open' : esc(b.status)) + ' · ' + b.days_left + 'd left</span>' +
          '<span class="chip g tipd" data-tip="Your own USDC covers it and your other open briefs, read on-chain ' + when(b.owner_funds.checked_at) + '">' + ic('shield') + 'Funds covered</span>' +
          pays.map((p) => '<span class="chip">' + price(b[p[0]]) + ' USDC ' + p[1] + '</span>').join('') + '</div>' +
          (b.say_line ? '<div class="dim" style="margin-top:8px;font-size:13px">“' + esc(b.say_line) + '”</div>' : '') + '</div>' +
        '<div class="acts"><button class="btn sm" data-act="pause">' + ic('pause') + 'Pause</button><button class="btn sm" data-act="addbudget">' + ic('plus') + 'Add budget</button>' +
          '<button class="btn sm" data-act="prices">' + ic('edit') + 'Edit prices</button><button class="btn sm c" data-copytext="https://cymetica.com/creator-dashboard?view=market#brief-' + b.id + '">' + ic('link') + 'Share</button></div></div>' +
      '<div class="tiles" style="--n:6">' +
        '<div class="tile" style="--c:#00cfff" data-tip="Stops at your budget: a result after it is not counted (the budget was spent)"><div class="k">' + ic('wallet') + 'Spent <span class="i">i</span></div><div class="v">' + usd(spent) + '<small>of ' + usd(b.budget_usdc) + '</small></div><div class="meter"><i style="width:' + (100 * spent / b.budget_usdc).toFixed(1) + '%"></i></div></div>' +
        tile('coin', 'Up for grabs', '<span class="pos">' + usd(b.up_for_grabs_usdc) + '</span><small>USDC</small>', r.promoters + ' promoters', '#00ff88') +
        tile('eye', 'Visitors', fmt(r.visitors_14d), 'unique, 14 days') +
        tile('uniq', 'New visitors', fmt(r.new_visitors.counted), fmt(r.new_visitors.held) + ' on 7-day hold', '#00cfff', b.per_visitor_usdc ? 'First visit through a promoter\'s link, real browser, never seen on this brief' : 'Not paid on this brief') +
        tile('users', 'New users', fmt(r.new_users.counted), fmt(r.new_users.checking) + ' in the 14-day check', '#3b82f6') +
        tile('x', 'Posts paid', fmt(r.posts.paid), fmt(r.posts.checking) + ' checking', '#a9b8cc') + '</div>' +
      '<div class="g2"><div class="card pad"><div class="ch"><h3>Visitors by day</h3><span class="sp"></span><span class="lgd"><span><i style="background:#00cfff"></i>visitors</span><span><i style="background:#00ff88"></i>new users</span></span></div>' +
          vbars([r.users_by_day, vis.map((v, i) => v - (r.users_by_day[i] || 0))], days, 190, 'No visitors yet') + '</div>' +
        '<div class="card pad"><div class="ch"><h3>From click to user</h3><span class="i tipr" data-tip="Each step is checked before it is paid: a new visitor after a real browser check and a 7-day hold, a new user after its own deposit and a 14-day check">i</span></div>' +
          '<div class="funnel">' + fun.map((f) => '<div class="fr' + (f[2] ? ' g' : '') + '"><span>' + f[0] + '</span><div class="fb"><i style="width:' + Math.max(f[1] ? 1.5 : 0, 100 * f[1] / fmax).toFixed(1) + '%"></i></div><b>' + fmt(f[1]) + '</b></div>').join('') + '</div>' +
          '<div class="dim num" style="font-size:11.5px;margin-top:12px">Cost per new user: <b style="color:var(--text)">' + (r.new_users.counted ? usd(spent / r.new_users.counted) + ' USDC' : '—') + '</b> · per visitor: <b style="color:var(--text)">' + (r.visitors_14d ? usd(spent / r.visitors_14d) + ' USDC' : '—') + '</b></div></div></div>' +
      '<div class="g2"><div class="card"><div class="tbar"><h3 style="margin:0;font:17px var(--display)">Promoters</h3><span class="sp" style="flex:1"></span>' +
          (unpaid.length ? '<button class="btn g sm" data-act="payall">' + ic('coin') + 'Pay ' + unpaid.length + ' · ' + usd(sum(unpaid, (p) => p.earned_usdc)) + ' USDC</button>' : '') + '</div>' +
          (r.by_promoter.length ? '<table class="tbl"><thead><tr><th>Promoter</th><th class="n">Posts</th><th class="n">Visitors</th>' + (b.per_visitor_usdc ? '<th class="n">New visitors</th>' : '') + '<th class="n">New users</th><th class="n">Earned</th><th></th></tr></thead><tbody>' +
            r.by_promoter.map((p) => '<tr><td><span class="ttl">Promoter ' + p.n + '<small class="lnk">cymetica.com/' + esc(p.slug) + '</small></span></td><td class="n">' + p.posts + '</td><td class="n">' + fmt(p.visitors) + '</td>' +
              (b.per_visitor_usdc ? '<td class="n">' + fmt(p.new_visitors) + '</td>' : '') + '<td class="n">' + p.new_users + '</td><td class="n pos">' + usd(p.earned_usdc) + '</td>' +
              '<td>' + (p.paid ? '<span class="chip g">' + ic('check') + 'paid</span>' : p.earned_usdc > 0 ? '<button class="btn sm g" data-act="pay">Pay</button>' : '') + '</td></tr>').join('') + '</tbody></table>' :
            '<div class="empty"><b>No promoter has taken it yet</b><span>It is on the market now.</span><a class="btn c sm" href="#market" style="margin-top:6px">See it on the market</a></div>') + '</div>' +
        '<div style="display:grid;gap:18px;align-content:start"><div class="card pad"><div class="ch"><h3>Where they came from</h3></div>' +
            (r.sources.length ? '<div class="hbar">' + r.sources.map((s) => '<div class="hr"><span>' + ic(SRC_IC[s[0]] || 'globe') + esc(s[0]) + '</span><div class="hb"><i style="width:' + (100 * s[1] / srcMax).toFixed(1) + '%"></i></div><b>' + fmt(s[1]) + '</b></div>').join('') + '</div>' : '<div class="dim num">No visitors yet.</div>') + '</div>' +
          '<div class="card pad"><div class="ch"><h3>Not counted</h3><span class="chip r">' + fmt(r.new_users.not_counted + r.new_visitors.not_counted) + '</span><span class="i tipr" data-tip="Never paid. The reasons are the platform\'s own checks.">i</span></div>' +
            (notRows.length ? '<div class="hbar">' + notRows.map((x) => '<div class="hr" style="grid-template-columns:1fr 46px"><span>' + esc(x[0]) + ' <span class="dim">· ' + x[2] + '</span></span><b>' + fmt(x[1]) + '</b></div>').join('') + '</div>' : '<div class="dim num">Nothing refused yet.</div>') + '</div></div></div>' +
      '<div class="g2"><div class="card pad"><div class="ch"><h3>Materials</h3><span class="chip c">NEW</span><span class="sp"></span><span class="dim num" style="font-size:11.5px">promoters who used each</span></div>' +
          '<div class="hbar">' + r.materials_used.map((m) => '<div class="hr" style="grid-template-columns:1fr 1.3fr 40px"><span>' + esc(m[0]) + '</span><div class="hb"><i style="width:' + (r.promoters ? 100 * m[1] / r.promoters : 0).toFixed(1) + '%;background:var(--green)"></i></div><b>' + m[1] + '</b></div>').join('') + '</div></div>' +
        '<div class="card pad"><div class="ch"><h3>Quotes from promoters</h3><span class="i tipr" data-tip="A promoter with an audience asks a fixed price for one post. You accept or decline.">i</span></div>' +
          (r.quotes.length ? r.quotes.map((q) => '<div class="quote"><div><b>' + fmt(q.price_usdc) + ' USDC for one post</b><br><span>' + esc(q.audience_url.replace('https://', '')) + ' · ' + fmt(q.audience_size) + ' followers</span></div><div class="acts"><button class="btn sm g" data-act="accept">Accept</button><button class="btn sm gh" data-act="decline">Decline</button></div></div>').join('') :
            '<div class="dim num">No quote yet.</div>') + '</div></div>';
    return dash('products', inner);
  }

  /* ---------------- drawer ---------------- */
  function show() { $('scrim').classList.add('on'); $('drawer').classList.add('on'); }
  function hide() { $('scrim').classList.remove('on'); $('drawer').classList.remove('on'); }

  /* ---------------- router ---------------- */
  function route() {
    const h = location.hash.replace(/^#/, '') || 'market';
    const [r, ...rest] = h.split('/');
    const arg = rest.join('/');
    const v = $('view');
    hide();
    chrome(r);
    if (r === 'me') v.innerHTML = dash(arg || 'products');
    else if (r === 'new') v.innerHTML = newBrief(arg ? '/' + arg : null);
    else if (r === 'mybrief') v.innerHTML = ownerBrief(+arg);
    else { v.innerHTML = market(); if (r === 'board') setTimeout(() => { const b = $('board'); if (b) b.scrollIntoView({ behavior: 'smooth' }); }, 30); if (r === 'brief') openBrief(+arg); }
    if (r !== 'board') window.scrollTo(0, 0);
  }
  function rerender() { const y = window.scrollY; route(); window.scrollTo(0, y); }

  /* ---------------- events ---------------- */
  const PROMPTS = { agent_prompt: () => PAGE.market_hero.agent_prompt, queue_prompt: () => PAGE.queue_prompt, trade_prompt: () => PAGE.trade_prompt };
  document.addEventListener('click', (e) => {
    const t = e.target.closest('[data-act],[data-brief],[data-take],[data-copy],[data-copytext],[data-sort],[data-mode],[data-product],[data-qch],[data-qsel],[data-qpage],[data-jsel],[data-radar],[data-row],[data-pgsort],[data-pick],[data-tog],[data-days],[data-budget],[data-addmat],[data-rmmat],[data-go]');
    if (!t) { if (e.target.id === 'scrim') hide(); return; }
    const d = t.dataset;
    if (d.copytext != null) { e.stopPropagation(); return copy(d.copytext); }
    if (d.copy) return copy(PROMPTS[d.copy](), 'Prompt');
    if (d.take) { e.stopPropagation(); return take(+d.take); }
    if (d.go) { location.hash = d.go; return; }
    if (d.mode) { S.mode = d.mode; try { localStorage.setItem('pm2-mode', S.mode); } catch (x) { /* fine */ } return rerender(); }
    if (d.sort) { S.sort = d.sort; return rerender(); }
    if (d.qch) { if (PAGE.channel_counts[d.qch] === 'next') return; S.qch = d.qch; S.qsel = 0; S.qpage = null; return rerender(); }
    if (d.qsel) { S.qsel = +d.qsel; S.qpage = null; return rerender(); }
    if (d.qpage) { S.qpage = +d.qpage; return rerender(); }
    if (d.jsel) { S.jsel = +d.jsel; return rerender(); }
    if (d.radar) { S.radar = +d.radar; return rerender(); }
    if (d.row) { S.open[d.row] = !S.open[d.row]; return rerender(); }
    if (d.pgsort) { S.pgSort = d.pgsort; return rerender(); }
    if (d.pick) { S.form = defaultForm(d.pick); return rerender(); }
    if (d.tog) { S.form.on[d.tog] = !S.form.on[d.tog]; return rerender(); }
    if (d.days) { S.form.days = +d.days; return rerender(); }
    if (d.budget) { e.preventDefault(); S.form.budget = +d.budget; return rerender(); }
    if (d.addmat) { S.form.mats.push(d.addmat === 'text' ? { kind: 'text', title: 'Post text', body: '' } : { kind: 'link', title: 'Link', url: 'https://' }); return rerender(); }
    if (d.rmmat) { S.form.mats.splice(+d.rmmat, 1); return rerender(); }
    if (d.brief && !e.target.closest('a')) return openBrief(+d.brief);
    if (d.product && !e.target.closest('a,button')) return openProduct(d.product);
    const msg = { posted: 'Marked posted · the checker confirms it is displayed', registered: 'Post registered · checked within minutes', reply: 'Reply written · copy it into the thread',
      skip: 'Skipped', pitched: 'Marked pitched', tracked: 'Your tracked link is ready', sent: 'Queued · sent from EventTrader\'s own account', pagemade: 'Page created · its tracked URL is ready',
      kitmade: 'Kit made', linkmade: 'Link created', keymade: 'Key created · shown once', dl: 'Downloaded ' + (d.what || ''), pay: 'Pay: from your own wallet to the promoter\'s own wallet',
      payall: 'Review: each payout from your own wallet, one press each', pause: 'Brief paused · no new takes', addbudget: 'Add budget: your USDC is checked again on-chain', prices: 'Edit prices',
      accept: 'Quote accepted', decline: 'Quote declined' }[d.act];
    if (d.act === 'close') return hide();
    if (d.act === 'agent') { e.preventDefault(); return agentDrawer(); }
    if (d.act === 'publish') return publish();
    if (d.act === 'replay') return boot(350);
    if (d.act === 'cold') return boot(7500);
    if (msg) toast(msg);
  });
  document.addEventListener('input', (e) => {
    const t = e.target;
    if (t.id === 'pgq') { S.pgQ = t.value; const pos = t.selectionStart; rerender(); const n = $('pgq'); if (n) { n.focus(); n.setSelectionRange(pos, pos); } return; }
    if (!S.form) return;
    if (t.dataset.f) {
      const k = t.dataset.f;
      if (k === 'say') { S.form.say = t.value; const c = $('saycnt'); if (c) c.textContent = '(' + t.value.length + ' / 280)'; return refreshPreview(); }
      S.form[k] = parseFloat(t.value) || 0; return refreshPreview();
    }
    if (t.dataset.mat != null) { S.form.mats[+t.dataset.mat].body = t.value; }
  });
  // the preview follows the form without redrawing the inputs being typed in
  function refreshPreview() {
    const box = document.querySelector('.nb'); if (!box) return;
    const fresh = document.createElement('div'); fresh.innerHTML = newBrief(null);
    const a = box.querySelector('.card:last-child'), b = fresh.querySelector('.nb .card:last-child');
    if (a && b) a.replaceWith(b);
  }
  document.addEventListener('change', (e) => {
    if (e.target.id === 'files' && S.form) {
      [...e.target.files].forEach((f) => S.form.mats.push({ kind: f.type.startsWith('video') ? 'video' : 'image', title: f.name, file: f.name,
        size: (f.size / 1048576).toFixed(1) + ' MB', src: f.type.startsWith('image') ? URL.createObjectURL(f) : null }));
      rerender();
    }
  });
  document.addEventListener('dragover', (e) => { const d = e.target.closest && e.target.closest('#drop'); if (d) { e.preventDefault(); d.classList.add('over'); } });
  document.addEventListener('dragleave', (e) => { const d = e.target.closest && e.target.closest('#drop'); if (d) d.classList.remove('over'); });
  document.addEventListener('drop', (e) => {
    const d = e.target.closest && e.target.closest('#drop'); if (!d || !S.form) return; e.preventDefault();
    [...e.dataTransfer.files].forEach((f) => S.form.mats.push({ kind: f.type.startsWith('video') ? 'video' : 'image', title: f.name, file: f.name,
      size: (f.size / 1048576).toFixed(1) + ' MB', src: f.type.startsWith('image') ? URL.createObjectURL(f) : null }));
    rerender();
  });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') hide(); });
  window.addEventListener('hashchange', route);

  route();
  boot(350);
})();
