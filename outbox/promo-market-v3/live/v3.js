  /* ================= v3, laid on top of their v2 in the local copy (outbox/promo-market-v3) =================
   * Spliced in at the end of their closure by patch.py: these function declarations replace theirs of the same name
   * (defaultForm, formBrief, briefCard, newBrief), everything else is their own code.
   *   1. a brief can promote any website, not only an app on Cymetica;
   *   2. every price says its unit (USDC, and cents under a dollar);
   *   3. a post is paid by its reach: a price per 1,000 real views, up to a cap, for promoters who pass the bar the
   *      owner sets; a promoter applies with their X handle, Cymetica measures the account, the owner approves;
   *   4. the owner's bell and inbox of promoters who want a brief, with what Cymetica measured;
   *   5. the protection band above Open briefs.
   * The promoters in the inbox are a sample, one model for every figure on the page: the example account in the form
   * is the first of them (6,800 average views). */
  I.bell = '<path d="M5 14.5V9a5 5 0 0 1 10 0v5.5l1.5 1.5h-13z M8.3 17.5a1.9 1.9 0 0 0 3.4 0"/>';
  const V3_SITE = '__site';
  const V3_DEF = { per_post: 3, cap: 40, min_views: 1000, min_followers: 500, min_age: 90, min_real: 70, per_user: 5, per_visitor: 0.05, budget: 50, days: 7 };
  const V3_APPS = [
    { h: 'gemhunter_demo', f: 12400, v: 6800, e: 2.9, r: 88, age: '3.1 y', s: 82 },
    { h: 'alpha_threads_demo', f: 41000, v: 15200, e: 1.6, r: 79, age: '5.0 y', s: 91 },
    { h: 'onchain_notes_demo', f: 4100, v: 2350, e: 4.4, r: 93, age: '1.4 y', s: 74 }];
  const V3_OUT = [['moonfarm_demo', '52,000 followers, 310 avg views (0.6 %): a bought audience'], ['fresh_degen_demo', 'account 9 days old, you asked for 90'],
    ['airdrop_twin_demo', 'same device and wallet as another promoter'], ['6 more', 'under 1,000 avg views over the last 20 posts']];
  const V3_OUT_N = 9;
  const v3cents = (v) => { v = +v || 0; return v > 0 && v < 1 ? '= ' + Math.round(v * 100) + ' ¢' : '= $' + price(v); };
  const v3pay = (F, views) => Math.min(+F.cap || 0, (+F.per_post || 0) * views / 1000);
  const v3host = (u) => { try { const x = new URL(u); return x.host + (x.pathname === '/' ? '' : x.pathname); } catch (e) { return String(u || '').replace(/^https?:\/\//, ''); } };
  const v3k = (v) => (v >= 1000 ? (v / 1000).toFixed(v >= 10000 ? 0 : 1).replace(/\.0$/, '') + 'k' : String(v));
  function v3exText(F) {
    return 'e.g. an account with <b>' + fmt(V3_APPS[0].v) + '</b> avg views: <b class="pos">' + usd(v3pay(F, V3_APPS[0].v)) + ' USDC</b> a post';
  }

  function defaultForm(path) {
    const prods = prodsOf(), site = path === V3_SITE || !prods.length;
    const p = site ? null : (prods.find((x) => x.path === path) || prods[0]);
    const F = Object.assign({ path: site ? V3_SITE : p.path, on: { post: true, user: !site, visitor: true }, say: '', msg: '', site_name: '', site_url: 'https://' }, V3_DEF);
    F.mats = [{ kind: 'image', title: 'Cover picture', shot: true, url: site ? null : (p.preview_url || null), src: site ? null : pic(p.path),
      size: site ? 'goes with every post · drop one above' : 'goes with every post · now a screenshot of your page; drop your own above' },
      { kind: 'text', title: 'X post', body: '' }];
    if (!site) F.mats.push({ kind: 'link', title: 'Link to the page', url: p.url });
    return F;
  }
  function formBrief(F) {
    const site = F.path === V3_SITE;
    const p = site ? { name: F.site_name || 'Your website', path: null, url: F.site_url } : (prodsOf().find((x) => x.path === F.path) || {});
    return { id: 0, name: p.name, path: p.path, url: p.url, site: site, per_post_usdc: F.on.post ? F.per_post : 0, post_cap_usdc: F.cap,
      per_user_usdc: F.on.user && !site ? F.per_user : 0, per_visitor_usdc: F.on.visitor ? F.per_visitor : 0, budget_usdc: F.budget, up_for_grabs_usdc: F.budget,
      days: F.days, days_left: F.days, status: 'open', say_line: F.say, preview_src: F.mats[0] && F.mats[0].kind === 'image' ? F.mats[0].src : null,
      reach: { min_views: F.min_views, min_followers: F.min_followers, min_age: F.min_age, min_real: F.min_real },
      materials: F.mats.filter((m) => (m.kind !== 'text' || m.body) && !m.busy) };
  }

  /* the brief card: every price with its unit; a post priced by reach; Apply with your X */
  function briefCard(b, preview) {
    const tk = S.taken[b.id], byReach = b.post_cap_usdc != null;
    const tiles = [];
    if (+b.per_post_usdc > 0) tiles.push(byReach ? [price(b.per_post_usdc), 'per 1k views', 'max ' + price(b.post_cap_usdc) + ' a post'] : [price(b.per_post_usdc), 'per post', 'up 7 days']);
    if (+b.per_user_usdc > 0) tiles.push([price(b.per_user_usdc), 'per new user', 'after 14 days']);
    if (+b.per_visitor_usdc > 0) tiles.push([price(b.per_visitor_usdc), 'per visitor', v3cents(b.per_visitor_usdc)]);
    const mats = (b.materials || []).length, src = b.preview_src || (b.site ? null : pic(b.path));
    return '<article class="bc v3bc"' + (preview ? '' : ' data-brief="' + b.id + '"') + '>' +
      '<div class="img">' + (src ? '<img alt="" src="' + esc(src) + '">' : '<div class="v3noimg">' + ic('globe') + '</div>') + '<div class="tl">' + (mats ? '<span class="chip c">' + ic('image') + mats + ' materials</span>' : '') +
        '<span class="chip' + (b.days_left <= 2 ? ' r' : '') + '">' + ic('clock') + b.days_left + 'd left</span></div></div>' +
      '<div class="bd"><div class="nm"><b>' + esc(shortName(b.name)) + '</b><a class="lnk" href="' + esc(b.url) + '" target="_blank" rel="noopener">' + esc(b.site ? v3host(b.url) : 'cymetica.com' + b.path) + ' ↗</a></div>' +
        (b.say_line ? '<p class="say">' + esc(b.say_line) + '</p>' : '<p class="say dim">—</p>') +
        '<div class="ufg tipl" data-tip="One budget for every promoter, first come first paid: once it is spent, nothing more is counted or owed"><span>Up for grabs <span class="i">i</span></span><b>' + usd(b.up_for_grabs_usdc) + '<small>USDC</small></b></div>' +
        '<div class="pays v3pays">' + tiles.map((x) => '<div><b>' + x[0] + '<small>USDC</small></b><span>' + x[1] + '</span><em>' + x[2] + '</em></div>').join('') + '</div>' +
        (byReach && b.reach ? '<div class="v3bar">' + ic('shield') + '<span>Open to X accounts with <b>' + fmt(b.reach.min_views) + '+</b> avg views · checked by Cymetica</span></div>' : '') +
        (tk ? '<button class="btn c full" data-brief="' + b.id + '">' + ic('check') + 'Taken · my link</button>' :
          byReach ? '<button class="btn g full lg" ' + (preview ? 'disabled' : 'data-v3apply="' + b.id + '"') + '>' + ic('x') + 'Apply with your X ' + ic('arrow') + '</button>' :
          '<button class="btn g full lg" ' + (preview ? 'disabled' : 'data-take="' + b.id + '"') + '>Take it ' + ic('arrow') + '</button>') +
      '</div></article>';
  }

  /* Post a brief: any website, units on every price, the post priced by reach */
  function newBrief(path) {
    if (!OWNER) return dash('products');
    if (!need([MINE])) return waitBox('your products');
    if (!S.form || (path && S.form.path !== path)) S.form = defaultForm(path);
    const F = S.form, prods = api(MINE).products, P = prods.products || [], site = F.path === V3_SITE;
    const amt = (k, v, cents) => '<div class="v3amt"><input class="in" id="v3-' + k + '" data-f="' + k + '" inputmode="decimal" value="' + v + '" aria-label="' + k + ' in USDC"><i>USDC</i>' +
      (cents ? '<em id="v3c-' + k + '">' + v3cents(v) + '</em>' : '') + '</div>';
    const pr = (k, name, sub, v, tip, off) => '<div class="payrow v3row' + (F.on[k] && !off ? '' : ' off') + '"><button class="tog' + (F.on[k] && !off ? ' on' : '') + '"' + (off ? ' disabled' : ' data-tog="' + k + '"') + ' aria-label="' + name + '"></button>' +
      '<div' + (tip ? ' data-tip="' + esc(tip) + '"' : '') + '><b>' + name + '</b><span>' + sub + '</span></div>' + amt('per_' + k, v, k !== 'post') + '</div>';
    const req = (k, label, sub, unit) => '<label class="v3q"><span>' + label + '</span><div class="v3amt sm"><input class="in" id="v3-' + k + '" data-f="' + k + '" inputmode="numeric" value="' + F[k] + '"><i>' + unit + '</i></div><em>' + sub + '</em></label>';
    const reach = F.on.post ? '<div class="v3reach">' +
        '<div class="v3cap"><span>' + ic('coin') + 'Max for one post</span>' + amt('cap', F.cap) + '</div>' +
        '<div class="v3lbl">' + ic('shield') + 'Who may apply · Cymetica checks it on X</div>' +
        '<div class="v3reqs">' + req('min_views', 'Avg views', 'last 20 posts', 'min') + req('min_followers', 'Followers', 'real ones', 'min') + req('min_age', 'Account age', 'on X', 'days') + req('min_real', 'Real audience', 'not bought', '%') + '</div>' +
        '<div class="v3ex" id="v3ex">' + v3exText(F) + '</div></div>' : '';
    const matRow = (m, i) => m.kind === 'text' ?
      '<div class="mat txt"><div class="th">' + ic('text') + '</div><div><b>' + esc(m.title) + '</b><span>ready-made text, copied by promoters</span></div><button class="x" data-rmmat="' + i + '" aria-label="Remove">' + ic('close') + '</button>' +
        '<textarea class="in" data-mat="' + i + '" placeholder="Write the post promoters can copy (their link is added at the end)">' + esc(m.body) + '</textarea></div>' :
      m.kind === 'link' ? '<div class="mat txt v3link"><div class="th">' + ic('link') + '</div><div><b>' + esc(m.title) + '</b><span>promoters copy it; their own tracked link points here</span></div><button class="x" data-rmmat="' + i + '" aria-label="Remove">' + ic('close') + '</button>' +
        '<input class="in" data-matlink="' + i + '" value="' + esc(m.url) + '" placeholder="https://…"></div>' :
      m.shot ? '<div class="mat v3cover"><div class="th">' + (m.src ? '<img alt="" src="' + esc(m.src) + '">' : ic('image')) + '</div>' +
        '<div><b>Cover picture</b><span>' + esc(m.size) + '</span></div><button class="x" data-rmmat="' + i + '" aria-label="Remove">' + ic('close') + '</button></div>' :
      '<div class="mat"><div class="th">' + (m.kind === 'image' && m.src ? '<img alt="" src="' + esc(m.src) + '">' : ic(m.kind === 'video' ? 'video' : 'image')) + '</div>' +
        '<div><b>' + esc(m.title) + '</b><span>' + esc(m.busy ? 'uploading…' : m.err || m.size || '') + '</span></div><button class="x" data-rmmat="' + i + '" aria-label="Remove">' + ic('close') + '</button></div>';
    const b = formBrief(F), ex = v3pay(F, V3_APPS[0].v);
    const buy = [['post', ex, 'posts like the example'], ['user', site ? 0 : F.per_user, 'new users'], ['visitor', F.per_visitor, 'unique visitors']].filter((x) => F.on[x[0]] && x[1] > 0);
    const busy = F.mats.some((m) => m.busy);
    const ok = F.budget >= prods.min_budget_usdc && buy.length && !busy && (!F.on.visitor || !(F.per_visitor > 0) || (F.per_visitor >= 0.01 && F.per_visitor <= 5)) && (!site || /^https?:\/\/[^/\s]+\.[^/\s]+/.test(F.site_url));
    return '<div class="wrap"><div class="nbtop"><a class="back" href="#me/products">' + ic('arrow') + 'My products</a><h1>Post a brief</h1><span class="sp" style="flex:1"></span>' +
        '<span class="chip g tipr" data-tip="' + esc(PAGE().products_note) + '">' + ic('lock') + 'The budget stays in your own wallet</span></div>' +
      '<div class="nb v3nb">' +
        '<div class="card"><div class="colh"><span class="no">1</span><b>What and pay</b></div>' +
          '<div class="pick v3pick"><button data-pick="' + V3_SITE + '" class="v3site' + (site ? ' on' : '') + '"><span class="v3g">' + ic('globe') + '</span><div><b>My own website</b><span>any site, also outside Cymetica</span></div><em>any URL</em></button>' +
            P.map((p) => '<button data-pick="' + esc(p.path) + '" class="' + (p.path === F.path ? 'on' : '') + '"><img alt="" src="' + esc(pic(p.path)) + '"><div><b>' + esc(shortName(p.name)) + '</b><span>cymetica.com' + esc(p.path) + '</span></div><em>' + fmt((p.traffic_30d || {}).visitors) + ' / 30 d</em></button>').join('') + '</div>' +
          (site ? '<div class="v3sitef"><input class="in" id="v3sn" data-v3f="site_name" placeholder="Name, e.g. My Shop" value="' + esc(F.site_name) + '"><input class="in" id="v3su" data-v3f="site_url" placeholder="https://your-site.com" value="' + esc(F.site_url) + '"></div>' : '') +
          '<div class="v3lbl top">' + ic('coin') + 'Pay · all prices in USDC (1 USDC = $1)</div>' +
          pr('post', 'Per post · by reach', 'per 1,000 real views · post up 7 days', F.per_post, 'Views are read from X by Cymetica; up to 3 posts a brief a day are paid') + reach +
          pr('user', 'Per new user', site ? 'needs Cymetica\'s sign-up tag on your site' : 'spends ≥ this on Cymetica in 14 days · a deposit alone never counts', F.per_user,
            'Counted only when the user\'s own fees in 14 days reach this price, so a deposit and a withdrawal earn nothing', site) +
          pr('visitor', 'Per unique visitor', 'one real person\'s first visit · paid after 7 days', F.per_visitor, '0.01 to 5 USDC. Counted after a real browser check, never a hosting network, paid 7 days later') +
          '<div class="row2"><label class="f">Budget (USDC) · min ' + prods.min_budget_usdc + '<input class="in" data-f="budget" inputmode="decimal" value="' + F.budget + '"><div class="quick">' + [50, 100, 250, 500].map((v) => '<button data-budget="' + v + '">' + v + '</button>').join('') + '</div></label>' +
            '<label class="f">Runs for<div class="seg" style="height:42px;align-items:center">' + (prods.days_choices || [7, 14, 30]).map((d) => '<button data-days="' + d + '" class="' + (F.days === d ? 'on' : '') + '">' + d + ' days</button>').join('') + '</div></label></div>' +
          '<label class="f" style="margin-top:14px">One line for promoters to say <span class="dim" id="saycnt">(' + F.say.length + ' / 280)</span><input class="in" data-f="say" maxlength="280" value="' + esc(F.say) + '" placeholder="optional"></label></div>' +
        '<div class="card"><div class="colh"><span class="no">2</span><b>Materials for promoters</b><span class="sp"></span><span class="chip c tipr" data-tip="Promoters see these on the brief and download or copy them. Each download is counted on your brief\'s page.">NEW</span></div>' +
          '<label class="drop" id="drop">' + ic('upload') + '<b>Drop pictures or a video for promoters</b><span>PNG, JPG, GIF, MP4 or WebM · up to 50 MB each</span><input type="file" id="files" multiple accept="image/png,image/jpeg,image/gif,image/webp,video/mp4,video/webm" hidden></label>' +
          '<div class="mats">' + F.mats.map(matRow).join('') + '</div>' +
          '<div class="acts" style="margin-top:10px"><button class="btn sm" data-addmat="text">' + ic('text') + 'Add a text</button><button class="btn sm" data-addmat="link">' + ic('link') + 'Add a link</button></div></div>' +
        '<div class="card"><div class="colh"><span class="no">3</span><b>As promoters will see it</b></div><div class="preview">' + briefCard(b, true) +
          '<div><div class="dim num" style="font-size:11px;letter-spacing:1px;margin-bottom:6px">THIS BUDGET PAYS FOR UP TO</div><div class="buys">' +
            buy.map((x) => '<div><b>' + fmt(Math.floor(F.budget / x[1])) + '</b><span>' + x[2] + '</span></div>').join('') + '</div></div>' +
          '<div class="sendbar"><div class="note">' + ic('x') + '<span>Promoters apply with their X account. Cymetica measures its real reach and drops the ones under your bar; you approve the rest and their price.</span></div>' +
            '<div class="note">' + ic('users') + '<span>One budget for every promoter, first come first paid: once ' + usd(F.budget) + ' USDC is spent, nothing more is counted or owed.</span></div><div class="note">' + ic('shield') + '<span>Opens only when your own USDC, read on-chain, covers ' + usd(F.budget) + ' USDC and your other open briefs.</span></div>' +
            (F.msg ? '<div class="statusrow neg" role="alert">' + esc(F.msg) + '</div>' : '') +
            '<button class="btn g lg full" data-act="publish"' + (ok ? '' : ' disabled') + '>Post the brief ' + ic('arrow') + '</button><a class="btn gh full" href="#me/products">Cancel</a></div></div></div>' +
      '</div></div>';
  }

  /* the owner's inbox: promoters who want a brief, what Cymetica measured, the price by reach */
  function v3Inbox() {
    const F = S.form || V3_DEF;
    const left = V3_APPS.filter((a) => !a.st);
    const stat = (k, v, tip) => '<div' + (tip ? ' data-tip="' + esc(tip) + '"' : '') + '><span>' + k + '</span><b>' + v + '</b></div>';
    const app = (a, i) => {
      const p = v3pay(F, a.v), capped = p < (+F.per_post || 0) * a.v / 1000;
      return '<div class="v3app' + (a.st ? ' ' + a.st : '') + '"><div class="v3ah"><span class="v3av">' + esc(a.h[0].toUpperCase()) + '</span><div><b>@' + esc(a.h) + '</b><span>applied ' + (i + 1) * 2 + 'h ago · on X ↗</span></div><span class="sp"></span>' +
        '<span class="v3score" data-tip="Cymetica\'s reach score: real views, engagement and audience quality, 0 to 100"><i style="width:' + a.s + '%"></i><b>' + a.s + '</b></span></div>' +
        '<div class="v3stats">' + stat('Followers', fmt(a.f)) + stat('Avg views', fmt(a.v), 'Median views of the last 20 posts') + stat('Engagement', a.e + ' %') + stat('Real audience', a.r + ' %', 'Followers that look like real, active people') + stat('Account', a.age) + '</div>' +
        (a.st === 'ok' ? '<div class="v3done pos">' + ic('check') + 'Accepted at ' + usd(a.price) + ' USDC a post · their link is live</div>' :
          a.st === 'no' ? '<div class="v3done dim">Declined</div>' :
          '<div class="v3offer"><div><span>By reach</span><b>' + usd(p) + '<small>USDC</small></b><em>' + price(F.per_post) + ' × ' + v3k(a.v) + ' views' + (capped ? ' · your max' : '') + '</em></div>' +
            '<div class="v3amt"><input class="in" id="v3p-' + i + '" value="' + p.toFixed(2) + '" inputmode="decimal" aria-label="Your price a post"><i>USDC</i></div>' +
            '<button class="btn g" data-v3acc="' + i + '">' + ic('check') + 'Accept</button><button class="btn gh" data-v3dec="' + i + '">Decline</button></div>') + '</div>';
    };
    $('drawer').innerHTML = '<div class="v3dh"><div><span class="chip c">SAMPLE · how it would look</span><h2>Promoters who want your brief</h2>' +
        '<span class="dim num">Gem Screener · ' + price(F.per_post) + ' USDC per 1,000 views · max ' + price(F.cap) + ' a post</span></div><button class="x" data-act="close" aria-label="Close">' + ic('close') + '</button></div>' +
      '<div class="v3db"><div class="tiles" style="--n:3">' +
        tile('check', 'Passed the check', String(left.length), 'waiting for you', 'rgb(0,255,136)') +
        tile('shield', 'Filtered out', String(V3_OUT_N), 'by Cymetica, never shown', 'rgb(255,68,68)') +
        tile('coin', 'If you accept all', usd(left.reduce((s, a) => s + v3pay(F, a.v), 0)) + '<small>USDC</small>', 'one post each') + '</div>' +
        V3_APPS.map(app).join('') +
        '<details class="fold v3out"><summary>' + ic('shield') + 'Filtered out by Cymetica <span class="dim num">' + V3_OUT_N + '</span>' + ic('down', 'chev') + '</summary><div class="fb">' +
          V3_OUT.map((o) => '<div class="v3orow"><b>' + (o[0][0] === '6' ? o[0] : '@' + esc(o[0])) + '</b><span class="chip r">' + esc(o[1]) + '</span></div>').join('') + '</div></details>' +
        '<div class="dim" style="font-size:12px">Each check reads the account\'s public X: views of the last 20 posts, engagement, follower quality and age. An accepted promoter gets their own link; the post is paid once it has stayed up 7 days, at the price you accepted.</div></div>';
    $('drawer').classList.add('on'); $('scrim').classList.add('on');
  }
  function v3Bell() {
    const n = V3_APPS.filter((a) => !a.st).length, b = $('v3belln');
    if (b) { b.textContent = n; b.style.display = n ? '' : 'none'; }
  }

  /* the protection band, above Open briefs: their own counting rules, and the promoter checks v3 adds */
  function v3Protect() {
    const R = howAnswer().rules || [];
    const pro = [['x', 'X account', 'one per person'], ['eye', 'Real reach', 'avg views, last 20 posts'], ['users', 'No bought audience', 'views against followers'], ['check', 'Owner approves', 'sees the stats, sets the price']];
    const node = (icn, t, s, tip) => '<div class="v3n"' + (tip ? ' data-tip="' + esc(tip) + '"' : '') + '><span class="v3i">' + ic(icn) + '</span><div><b>' + esc(t) + '</b>' + (s ? '<span>' + esc(s) + '</span>' : '') + '</div></div>';
    return '<section class="v3prot"><div class="v3ph"><div><span class="chip g">' + ic('shield') + 'USER PROTECTION</span><h2>Only real people are paid for</h2></div><span class="sp"></span>' +
        '<div class="v3nums">' + [[String(R.length), 'checks on every visitor and user'], ['4', 'checks on every promoter'], ['7 d', 'before a visitor is paid'], ['14 d', 'before a user is paid']]
          .map((x) => '<div><b>' + x[0] + '</b><span>' + x[1] + '</span></div>').join('') + '</div></div>' +
      '<div class="v3lane"><span class="v3lab">' + ic('x') + 'Promoters</span><div class="v3ns">' + pro.map((p) => node(p[0], p[1], p[2])).join('') + '</div></div>' +
      '<div class="v3lane"><span class="v3lab">' + ic('users') + 'Visitors and users</span><div class="v3ns">' + R.map((r, k) => node(RULE_IC[k] || 'check', r.title, '', r.text)).join('') + '</div></div>' +
      '<div class="v3foot">' + ic('lock') + '<span>Bots, farms, bought followers and repeat visits are never paid. A link that looks farmed is taken back whole.</span></div></section>';
  }

  document.addEventListener('input', (e) => {
    const t = e.target, F = S.form; if (!F) return;
    if (t.dataset.v3f) { F[t.dataset.v3f] = t.value; return refreshPreview(); }
    if (t.dataset.f) {
      const x = $('v3ex'); if (x) x.innerHTML = v3exText(F);
      ['per_user', 'per_visitor'].forEach((k) => { const c = $('v3c-' + k); if (c) c.textContent = v3cents(F[k]); });
    }
  });
  document.addEventListener('click', (e) => {
    const t = e.target.closest('[data-v3inbox],[data-v3acc],[data-v3dec],[data-v3apply]'); if (!t) return;
    const d = t.dataset;
    if (d.v3inbox) return v3Inbox();
    if (d.v3apply) return toast('Local copy: applying with X is drawn, not wired');
    const a = V3_APPS[+(d.v3acc || d.v3dec)];
    if (d.v3acc) { a.st = 'ok'; a.price = parseFloat(($('v3p-' + d.v3acc) || {}).value) || v3pay(S.form || V3_DEF, a.v); toast('Accepted @' + a.h + ' (local copy: nothing sent)'); }
    else { a.st = 'no'; }
    v3Bell(); v3Inbox();
  });
  v3Bell();
