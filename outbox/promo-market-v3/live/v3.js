  /* ================= v3, laid on top of their v2 in the local copy (outbox/promo-market-v3) =================
   * Spliced in at the end of their closure by patch.py: these function declarations replace theirs of the same name
   * (chrome, defaultForm, formBrief, briefCard, newBrief), everything else is their own code.
   *   1. a brief can promote any website, not only an app on Cymetica;
   *   2. every price says its unit (USDC, and cents under a dollar);
   *   3. a post is priced for each promoter: the promoter gives their X handle, Cymetica measures the account's real
   *      reach, and the offer is the visitors it expects from one post x the owner's price per visitor, rounded
   *      (the operator, 2026-10-27). The owner sets no price per post, only whether posts are paid;
   *   4. the owner sees the offers on the brief's own page and approves them; the bell counts the ones waiting;
   *   5. a slim user-protection line above Open briefs.
   * The sample brief, its promoters and the stand-in engine (/__v3/x/<handle>) are sample.py: one model. */
  I.bell = '<path d="M5 14.5V9a5 5 0 0 1 10 0v5.5l1.5 1.5h-13z M8.3 17.5a1.9 1.9 0 0 0 3.4 0"/>';
  const V3_SITE = '__site';
  const V3_DEF = { per_user: 5, per_visitor: 0.05, budget: 50, days: 7 };
  const V3_EX = 136;   // the form's example: visitors the engine expects from @gemhunter_demo (sample.py)
  const v3cents = (v) => { v = +v || 0; return v > 0 && v < 1 ? '= ' + Math.round(v * 100) + ' ¢' : '= $' + price(v); };
  // the offer, rounded so it reads well (sample.py nice): halves under 10, whole USDC to 100, fives above
  const v3nice = (u) => { const s = u < 10 ? 0.5 : u < 100 ? 1 : 5; return Math.max(s, Math.round(u / s) * s); };
  const v3host = (u) => { try { const x = new URL(u); return x.host + (x.pathname === '/' ? '' : x.pathname); } catch (e) { return String(u || '').replace(/^https?:\/\//, ''); } };
  const v3offerLine = (pv) => 'Offer = visitors Cymetica expects from their X × ' + price(pv) + ' USDC, rounded · e.g. ~' + V3_EX + ' visitors → <b class="pos">' + price(v3nice(V3_EX * pv)) + ' USDC</b>';
  S.v3x = {}; S.v3dec = {};

  /* the top bar: theirs, and the bell counts the offers waiting for the owner */
  function chrome(r) {
    const onMarket = r === 'market' || r === 'brief' || r === 'board';
    $('tnav').innerHTML = '<a href="#market" class="' + (onMarket ? 'on' : '') + '">' + ic('market') + 'Market</a>' +
      '<a href="#me/' + (OWNER ? 'products' : 'today') + '" class="' + (onMarket ? '' : 'on') + '">' + ic('dash') + 'My dashboard</a>';
    $('topnew').innerHTML = ic('plus') + 'Post a brief';
    $('topnew').setAttribute('href', SIGNED ? (OWNER ? '#new' : '/creator-dashboard?tab=products') : signInHref('/creator-dashboard'));
    $('topuniv').innerHTML = ic('orbit') + 'See in the Universe ↗';
    const as = briefsAnswer().stats.as_of;
    $('livechip').innerHTML = '<i class="live"></i>' + (as ? 'live · read ' + when(as).slice(11) : 'live');
    v3Bell();
  }
  function v3Waiting() {
    return prodsOf().map((p) => p.brief).filter((r) => r && r.brief && r.brief.post_by_reach)
      .map((r) => ({ id: r.brief.id, n: (r.offers || []).filter((o) => o.state === 'pending' && !S.v3dec[r.brief.id + ':' + o.handle]).length }));
  }
  function v3Bell() {
    const b = $('v3belln'); if (!b) return;
    const n = v3Waiting().reduce((s, x) => s + x.n, 0);
    b.textContent = n; b.style.display = n ? '' : 'none';
    $('v3bell').setAttribute('data-tip', n ? n + ' promoter' + (n === 1 ? '' : 's') + ' want your brief' : 'No offer waiting');
  }

  /* Post a brief: any website, units on every price, the post priced for each promoter */
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
    return { id: 0, name: p.name, path: p.path, url: p.url, site: site, per_post_usdc: 0, post_by_reach: !!F.on.post,
      per_user_usdc: F.on.user && !site ? F.per_user : 0, per_visitor_usdc: F.on.visitor ? F.per_visitor : 0, budget_usdc: F.budget, up_for_grabs_usdc: F.budget,
      days: F.days, days_left: F.days, status: 'open', say_line: F.say, preview_src: F.mats[0] && F.mats[0].kind === 'image' ? F.mats[0].src : null,
      materials: F.mats.filter((m) => (m.kind !== 'text' || m.body) && !m.busy) };
  }

  /* the brief card: every price with its unit; a post priced by the promoter's reach */
  function briefCard(b, preview) {
    const tk = S.taken[b.id];
    const tiles = [];
    if (b.post_by_reach) tiles.push(['<b class="v3auto">by reach</b>', 'per post', 'for your X']);
    else if (+b.per_post_usdc > 0) tiles.push(['<b>' + price(b.per_post_usdc) + '<small>USDC</small></b>', 'per post', 'up 7 days']);
    if (+b.per_user_usdc > 0) tiles.push(['<b>' + price(b.per_user_usdc) + '<small>USDC</small></b>', 'per new user', 'after 14 days']);
    if (+b.per_visitor_usdc > 0) tiles.push(['<b>' + price(b.per_visitor_usdc) + '<small>USDC</small></b>', 'per visitor', v3cents(b.per_visitor_usdc)]);
    const src = b.preview_src || (b.site ? null : pic(b.path));
    return '<article class="bc v3bc"' + (preview ? '' : ' data-brief="' + b.id + '"') + '>' +
      '<div class="img">' + (src ? '<img alt="" src="' + esc(src) + '">' : '<div class="v3noimg">' + ic('globe') + '</div>') + '<div class="tl">' +
        '<span class="chip' + (b.days_left <= 2 ? ' r' : '') + '">' + ic('clock') + b.days_left + 'd left</span></div></div>' +
      '<div class="bd"><div class="nm"><b>' + esc(shortName(b.name)) + '</b><a class="lnk" href="' + esc(b.url) + '" target="_blank" rel="noopener">' + esc(b.site ? v3host(b.url) : 'cymetica.com' + b.path) + ' ↗</a></div>' +
        (b.say_line ? '<p class="say">' + esc(b.say_line) + '</p>' : '<p class="say dim">—</p>') +
        '<div class="ufg tipl" data-tip="One budget for every promoter, first come first paid: once it is spent, nothing more is counted or owed"><span>Up for grabs <span class="i">i</span></span><b>' + usd(b.up_for_grabs_usdc) + '<small>USDC</small></b></div>' +
        '<div class="pays v3pays">' + tiles.map((x) => '<div>' + x[0] + '<span>' + x[1] + '</span><em>' + x[2] + '</em></div>').join('') + '</div>' +
        (tk ? '<button class="btn c full" data-brief="' + b.id + '">' + ic('check') + 'Taken · my link</button>' :
          // a post priced by reach opens the brief, where the promoter's X handle gives the offer
          '<button class="btn g full lg" ' + (preview ? 'disabled' : (b.post_by_reach ? 'data-brief="' : 'data-take="') + b.id + '"') + '>' + (b.post_by_reach ? 'See my offer ' : 'Take it ') + ic('arrow') + '</button>') +
      '</div></article>';
  }

  function newBrief(path) {
    if (!OWNER) return dash('products');
    if (!need([MINE])) return waitBox('your products');
    if (!S.form || (path && S.form.path !== path)) S.form = defaultForm(path);
    const F = S.form, prods = api(MINE).products, P = prods.products || [], site = F.path === V3_SITE;
    const amt = (k, v) => '<div class="v3amt"><input class="in" id="v3-' + k + '" data-f="' + k + '" inputmode="decimal" value="' + v + '" aria-label="' + k + ' in USDC"><i>USDC</i>' +
      '<em id="v3c-' + k + '">' + v3cents(v) + '</em></div>';
    const tog = (k, off) => '<button class="tog' + (F.on[k] && !off ? ' on' : '') + '"' + (off ? ' disabled' : ' data-tog="' + k + '"') + ' aria-label="' + k + '"></button>';
    const pr = (k, name, sub, v, tip, off) => '<div class="payrow v3row' + (F.on[k] && !off ? '' : ' off') + '">' + tog(k, off) +
      '<div' + (tip ? ' data-tip="' + esc(tip) + '"' : '') + '><b>' + name + '</b><span>' + sub + '</span></div>' + amt('per_' + k, v) + '</div>';
    const post = '<div class="payrow v3row v3post' + (F.on.post ? '' : ' off') + '">' + tog('post') +
        '<div data-tip="The promoter gives their X handle; Cymetica measures the account\'s real reach and prices the post for them. You approve each one."><b>Per post · priced for each promoter</b><span>paid for the post itself, before any visitor</span></div>' +
        '<span class="v3autopill">' + ic('x') + 'auto</span></div>' +
      (F.on.post ? '<div class="v3ex" id="v3ex">' + v3offerLine(F.per_visitor) + '</div>' : '');
    const matRow = (m, i) => m.kind === 'text' ?
      '<div class="mat txt"><div class="th">' + ic('text') + '</div><div><b>' + esc(m.title) + '</b><span>ready-made text, copied by promoters</span></div><button class="x" data-rmmat="' + i + '" aria-label="Remove">' + ic('close') + '</button>' +
        '<textarea class="in" data-mat="' + i + '" placeholder="Write the post promoters can copy (their link is added at the end)">' + esc(m.body) + '</textarea></div>' :
      m.kind === 'link' ? '<div class="mat txt v3link"><div class="th">' + ic('link') + '</div><div><b>' + esc(m.title) + '</b><span>promoters copy it; their own tracked link points here</span></div><button class="x" data-rmmat="' + i + '" aria-label="Remove">' + ic('close') + '</button>' +
        '<input class="in" data-matlink="' + i + '" value="' + esc(m.url) + '" placeholder="https://…"></div>' :
      m.shot ? '<div class="mat v3cover"><div class="th">' + (m.src ? '<img alt="" src="' + esc(m.src) + '">' : ic('image')) + '</div>' +
        '<div><b>Cover picture</b><span>' + esc(m.size) + '</span></div><button class="x" data-rmmat="' + i + '" aria-label="Remove">' + ic('close') + '</button></div>' :
      '<div class="mat"><div class="th">' + (m.kind === 'image' && m.src ? '<img alt="" src="' + esc(m.src) + '">' : ic(m.kind === 'video' ? 'video' : 'image')) + '</div>' +
        '<div><b>' + esc(m.title) + '</b><span>' + esc(m.busy ? 'uploading…' : m.err || m.size || '') + '</span></div><button class="x" data-rmmat="' + i + '" aria-label="Remove">' + ic('close') + '</button></div>';
    const b = formBrief(F), ex = v3nice(V3_EX * F.per_visitor);
    const buy = [['post', ex, 'posts like the example'], ['user', site ? 0 : F.per_user, 'new users'], ['visitor', F.per_visitor, 'unique visitors']].filter((x) => F.on[x[0]] && x[1] > 0);
    const busy = F.mats.some((m) => m.busy);
    const ok = F.budget >= prods.min_budget_usdc && buy.length && !busy && F.per_visitor >= 0.01 && F.per_visitor <= 5 && (!site || /^https?:\/\/[^/\s]+\.[^/\s]+/.test(F.site_url));
    return '<div class="wrap"><div class="nbtop"><a class="back" href="#me/products">' + ic('arrow') + 'My products</a><h1>Post a brief</h1><span class="sp" style="flex:1"></span>' +
        '<span class="chip g tipr" data-tip="' + esc(PAGE().products_note) + '">' + ic('lock') + 'The budget stays in your own wallet</span></div>' +
      '<div class="nb v3nb">' +
        '<div class="card"><div class="colh"><span class="no">1</span><b>What and pay</b></div>' +
          '<div class="pick v3pick"><button data-pick="' + V3_SITE + '" class="v3site' + (site ? ' on' : '') + '"><span class="v3g">' + ic('globe') + '</span><div><b>My own website</b><span>any site, also outside Cymetica</span></div><em>any URL</em></button>' +
            P.map((p) => '<button data-pick="' + esc(p.path) + '" class="' + (p.path === F.path ? 'on' : '') + '"><img alt="" src="' + esc(pic(p.path)) + '"><div><b>' + esc(shortName(p.name)) + '</b><span>cymetica.com' + esc(p.path) + '</span></div><em>' + fmt((p.traffic_30d || {}).visitors) + ' / 30 d</em></button>').join('') + '</div>' +
          (site ? '<div class="v3sitef"><input class="in" id="v3sn" data-v3f="site_name" placeholder="Name, e.g. My Shop" value="' + esc(F.site_name) + '"><input class="in" id="v3su" data-v3f="site_url" placeholder="https://your-site.com" value="' + esc(F.site_url) + '"></div>' : '') +
          '<div class="v3lbl top">' + ic('coin') + 'Pay · all prices in USDC (1 USDC = $1)</div>' +
          pr('visitor', 'Per unique visitor', 'one real person\'s first visit · paid after 7 days', F.per_visitor, '0.01 to 5 USDC. Counted after a real browser check, never a hosting network, paid 7 days later') +
          post +
          pr('user', 'Per new user', site ? 'needs Cymetica\'s sign-up tag on your site' : 'spends ≥ this on Cymetica in 14 days · a deposit alone never counts', F.per_user,
            'Counted only when the user\'s own fees in 14 days reach this price, so a deposit and a withdrawal earn nothing', site) +
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
          '<div class="sendbar">' +
            '<div class="note">' + ic('users') + '<span>One budget for every promoter, first come first paid: once ' + usd(F.budget) + ' USDC is spent, nothing more is counted or owed.</span></div><div class="note">' + ic('shield') + '<span>Opens only when your own USDC, read on-chain, covers ' + usd(F.budget) + ' USDC and your other open briefs.</span></div>' +
            (F.msg ? '<div class="statusrow neg" role="alert">' + esc(F.msg) + '</div>' : '') +
            '<button class="btn g lg full" data-act="publish"' + (ok ? '' : ' disabled') + '>Post the brief ' + ic('arrow') + '</button><a class="btn gh full" href="#me/products">Cancel</a></div></div></div>' +
      '</div></div>';
  }

  /* a promoter opens the brief: their X handle in, the offer for one post out (their drawer, this box above Take it) */
  function v3OfferBox(b, tk) {
    if (!b.post_by_reach || tk) return '';
    const x = S.v3x[b.id] || {}, r = x.res, pv = b.per_visitor_usdc;
    const head = '<div class="v3obh">' + ic('x') + '<b>Paid per post</b><span class="sp"></span><span class="chip c">priced for your X</span></div>';
    if (!r) return '<div class="v3ob">' + head +
      '<div class="v3obin"><span>@</span><input class="in" id="v3xh" placeholder="your X handle" value="' + esc(x.h || '') + '" autocomplete="off"><button class="btn c" data-v3check="' + b.id + '">Check my offer</button></div>' +
      '<div class="v3obnote">Cymetica reads your public X: the real views of your last 20 posts and how much of your audience is real.</div></div>';
    const who = '<div class="v3who"><span class="v3av">' + esc(r.handle[0].toUpperCase()) + '</span><b>@' + esc(r.handle) + '</b><span class="sp"></span><button class="lnk v3chg" data-v3change="' + b.id + '">change</button></div>';
    const st = (k, v) => '<div><span>' + k + '</span><b>' + v + '</b></div>';
    const stats = '<div class="v3s4">' + st('Followers', fmt(r.followers)) + st('Views a post', fmt(r.views)) + st('Real audience', r.real + ' %') + st('Account', esc(r.age)) + '</div>';
    if (!r.ok) return '<div class="v3ob no">' + head + who + stats + '<div class="v3not">' + ic('close') + '<span><b>Not eligible.</b> ' + esc(r.why) + '</span></div></div>';
    return '<div class="v3ob">' + head + who + stats +
      '<div class="v3big"><div><span>Your offer for one post</span><b>' + price(r.offer) + '<small>USDC</small></b></div><em>~' + fmt(r.expected) + ' visitors expected<br>× ' + price(pv) + ' USDC, rounded</em></div>' +
      (x.sent ? '<div class="v3done pos">' + ic('check') + 'Sent to the owner · your link arrives when they approve</div>' :
        '<button class="btn g lg full" data-v3take="' + b.id + '">Take the offer ' + ic('arrow') + '</button>') +
      '<div class="v3obnote">Paid for the post itself once it has stayed up 7 days, whatever it brings. Visitors above ~' + fmt(r.expected) + ' are paid ' + price(pv) + ' USDC each on top.</div></div>';
  }

  /* the owner's brief page, trimmed (the operator, 2026-10-27): four numbers, the offers waiting, visitors by day with
   * the count on hover, one Promoters table. Gone from v2's page: New visitors, Posts paid, Where they came from, Not
   * counted, Materials, Quotes from promoters. */
  const v3decided = (b, o) => S.v3dec[b.id + ':' + o.handle];
  function v3Offers(b, r) {
    if (!b.post_by_reach) return '';
    const O = (r.offers || []).filter((o) => o.state === 'pending' && !v3decided(b, o)), F = r.filtered_out || [], nf = F.reduce((s, f) => s + f[1], 0);
    return '<div class="card v3offers" id="v3offers"><div class="tbar"><h3>Offers for a post</h3>' + (O.length ? '<span class="chip g"><i class="live"></i>' + O.length + ' waiting for you</span>' : '') +
        '<span class="sp" style="flex:1"></span><span class="chip r tipr" data-tip="' + esc(F.map((f) => f[1] + ' × ' + f[0]).join(' · ')) + '">' + ic('shield') + nf + ' filtered out by Cymetica</span></div>' +
      (O.length ? '<div class="tscroll"><table class="tbl v3tbl"><thead><tr><th>Promoter</th><th class="n">Followers</th><th class="n">Views a post</th><th class="n">Real audience</th><th class="n">Visitors expected</th><th class="n">Offer</th><th></th></tr></thead><tbody>' +
        O.map((o) => '<tr class="v3wait"><td><span class="v3pm"><span class="v3av">' + esc(o.handle[0].toUpperCase()) + '</span><span><b>@' + esc(o.handle) + '</b><small>applied ' + esc(o.applied || '') + ' · on X ' + esc(o.age) + '</small></span></span></td>' +
          '<td class="n">' + fmt(o.followers) + '</td><td class="n">' + fmt(o.views) + '</td><td class="n">' + o.real + ' %</td><td class="n">~' + fmt(o.expected) + '</td>' +
          '<td class="n v3of">' + price(o.offer) + ' <small>USDC</small></td><td class="v3act"><button class="btn g sm" data-v3ok="' + b.id + ':' + o.handle + '">' + ic('check') + 'Approve</button><button class="btn gh sm v3x" data-v3no="' + b.id + ':' + o.handle + '" aria-label="Decline" data-tip="Decline">' + ic('close') + '</button></td></tr>').join('') + '</tbody></table></div>' :
        '<div class="empty" style="padding:22px"><span>No promoter is waiting for you.</span></div>') +
      '<div class="v3foot">' + ic('x') + '<span>Offer = visitors Cymetica expects from their X × ' + price(b.per_visitor_usdc) + ' USDC, rounded. Paid for the post itself once it has stayed up 7 days.</span></div></div>';
  }

  /* visitors by day: a column per day, the count on hover (v2's chart shows none) */
  function v3Chart(days, visitors, users) {
    const max = Math.max(1, ...visitors), H = 190;
    return '<div class="v3chart" style="height:' + H + 'px">' + days.map((d, i) => {
      const v = visitors[i] || 0, u = users[i] || 0, hv = v / max * (H - 8);
      return '<div class="v3col" data-tip="' + esc(dShort(d) + ' · ' + v + ' visitor' + (v === 1 ? '' : 's') + (u ? ' · ' + u + ' new user' + (u === 1 ? '' : 's') : '')) + '"><span class="v3bar" style="height:' + hv.toFixed(1) + 'px"><i style="height:' + (v ? 100 * u / v : 0).toFixed(1) + '%"></i></span></div>';
    }).join('') + '</div><div class="dl" style="display:flex;justify-content:space-between"><span>' + dShort(days[0]) + '</span><span>' + dShort(days[days.length - 1]) + '</span></div>';
  }

  /* Promoters, full width: the ones who took the brief, their post, what they brought and earned. The offers still
   * waiting are the table above; an approved one moves here (the old Paid rows in Offers were the same list). */
  function v3Promoters(b, r) {
    const byp = r.by_promoter || [], O = r.offers || [];
    const rows = byp.map((p) => ({ p: p, o: O.find((o) => o.promoter === p.n) }));
    O.filter((o) => o.state === 'pending' && v3decided(b, o) === 'approved').forEach((o) => rows.push({ p: null, o: o }));
    const unpaid = byp.filter((p) => !p.paid && p.earned_usdc > 0);
    const chip = (x) => !x.o ? '' : (x.p ? ({ paid: '<span class="chip g">' + ic('check') + 'paid</span>', posted: '<span class="chip c" data-tip="Paid once the post has stayed up 7 days">posted</span>' }[x.o.state] || '') :
      '<span class="chip" data-tip="Their link is live; paid once the post has stayed up 7 days">approved · no post yet</span>');
    return '<div class="card v3prom"><div class="tbar"><h3 style="margin:0;font:17px var(--display)">Promoters</h3><span class="chip">' + rows.length + '</span><span class="sp" style="flex:1"></span>' +
        (unpaid.length ? '<button class="btn g sm" data-payall="' + b.id + '">' + ic('coin') + 'Pay ' + unpaid.length + ' · ' + usd(sum(unpaid, (p) => p.earned_usdc)) + ' USDC</button>' : '') + '</div>' +
      (rows.length ? '<table class="tbl v3tbl"><thead><tr><th>Promoter</th><th>Post</th><th class="n">Visitors</th><th class="n">New users</th><th class="n">Earned</th><th></th></tr></thead><tbody>' +
        rows.map((x) => { const p = x.p, h = x.o && x.o.handle; return '<tr><td><span class="v3pm"><span class="v3av">' + esc((h || 'P')[0].toUpperCase()) + '</span><span><b>' + (h ? '@' + esc(h) : 'Promoter ' + p.n) + '</b>' +
            '<small>' + (p ? 'cymetica.com/' + esc(p.slug) : 'link goes live when they post') + '</small></span></span></td>' +
          '<td>' + (x.o ? '<b class="v3of" style="font-size:15px">' + price(x.o.offer) + '</b> <small class="dim">USDC</small> ' : '') + chip(x) + '</td>' +
          '<td class="n">' + (p ? fmt(p.visitors) : '—') + '</td><td class="n">' + (p ? p.new_users : '—') + '</td><td class="n pos">' + (p ? usd(p.earned_usdc) : '—') + '</td>' +
          '<td class="v3act">' + (p && !p.paid && (p.pending_ids || []).length ? '<button class="btn sm g" data-payids="' + (p.pending_ids || []).join(',') + '">Pay</button>' : '') + '</td></tr>'; }).join('') + '</tbody></table>' :
        '<div class="empty"><b>No promoter has taken it yet</b><span>It is on the market now.</span><a class="btn c sm" href="#market" style="margin-top:6px">See it on the market</a></div>') + '</div>';
  }

  function ownerBrief(id) {
    const RU = resultsUrl(id);
    if (!need([RU, HOW])) return dash('products', waitIn('the brief'));
    const r = api(RU); if (!r || !r.brief) return dash('products', '<div class="card"><div class="empty"><b>This brief is not yours, or it does not exist.</b><a class="btn c sm" href="#me/products">My products</a></div></div>');
    const b = r.brief, spent = r.spent_usdc || 0, days = Object.keys(r.visitors_by_day || {}), vis = Object.values(r.visitors_by_day || {});
    learn(b.path, b.preview_url, b.art);
    const ubd = Array.isArray(r.users_by_day) ? r.users_by_day : days.map((d) => (r.users_by_day || {})[d] || 0);
    const nu = r.new_users || { counted: 0, checking: 0, not_counted: 0 };
    const pays = [['per_user_usdc', 'per new user'], ['per_visitor_usdc', 'per visitor']].filter((p) => +b[p[0]] > 0);
    const fun = [['Clicks on the links', r.clicks || 0], ['Unique visitors', r.visitors_14d || 0], ['New users checking', (nu.checking || 0) + (nu.counted || 0)], ['New users counted', nu.counted || 0, 1]];
    const fmax = Math.max(1, ...fun.map((f) => f[1]));
    const live = b.status === 'open';
    const fundTip = b.owner_funds && b.owner_funds.checked_at ? 'Your own USDC covers it and your other open briefs, read on-chain ' + when(b.owner_funds.checked_at) : 'Your own USDC is read on-chain while it runs';
    const covered = !b.owner_funds || b.owner_funds.state !== 'short';
    const inner = '<div class="ph"><a class="back" href="#me/products">' + ic('arrow') + 'My products</a></div>' +
      '<div class="card bdhead"><img alt="" src="' + esc(pic(b.path)) + '"><div><h1>' + esc(shortName(b.name)) + '</h1><div class="meta">' +
          '<span class="chip ' + (live ? 'g' : '') + '">' + (live ? '<i class="live"></i>Open' : esc(b.status)) + ' · ' + b.days_left + 'd left</span>' +
          '<span class="chip ' + (covered ? 'g' : 'r') + ' tipd" data-tip="' + esc(fundTip) + '">' + ic('shield') + (covered ? 'Funds covered' : 'Funds short') + '</span>' +
          (b.post_by_reach ? '<span class="chip">post: priced per promoter</span>' : '') + pays.map((p) => '<span class="chip">' + price(b[p[0]]) + ' USDC ' + p[1] + '</span>').join('') + '</div>' +
          (b.say_line ? '<div class="dim" style="margin-top:8px;font-size:13px">“' + esc(b.say_line) + '”</div>' : '') +
          '<div class="dim num" style="font-size:11.5px;margin-top:8px" id="act-msg">' + esc(S.actMsg || '') + '</div></div>' +
        '<div class="acts">' + (b.status === 'paused' ? '<button class="btn sm" data-bact="resume" data-id="' + b.id + '">' + ic('play') + 'Resume</button>' : live ? '<button class="btn sm" data-bact="pause" data-id="' + b.id + '">' + ic('pause') + 'Pause</button>' : '') +
          (live || b.status === 'paused' ? '<button class="btn sm" data-bact="add_budget" data-id="' + b.id + '">' + ic('plus') + 'Add budget</button><button class="btn sm" data-bact="edit_prices" data-id="' + b.id + '">' + ic('edit') + 'Edit prices</button>' : '') +
          '<button class="btn sm c" data-copytext="' + esc(location.origin + '/promo-market#brief/' + b.id) + '">' + ic('link') + 'Share</button></div></div>' +
      '<div class="tiles" style="--n:4">' +
        '<div class="tile" style="--c:rgb(0,207,255)" data-tip="Stops at your budget: a result after it is not counted"><div class="k">' + ic('wallet') + 'Spent <span class="i">i</span></div><div class="v">' + usd(spent) + '<small>of ' + usd(b.budget_usdc) + '</small></div><div class="meter"><i style="width:' + (b.budget_usdc ? 100 * spent / b.budget_usdc : 0).toFixed(1) + '%"></i></div></div>' +
        tile('coin', 'Up for grabs', '<span class="pos">' + usd(b.up_for_grabs_usdc) + '</span><small>USDC</small>', fmt(r.promoters) + ' promoters', 'rgb(0,255,136)') +
        tile('eye', 'Visitors', fmt(r.visitors_14d), 'unique, 14 days') +
        tile('users', 'New users', fmt(nu.counted), fmt(nu.checking) + ' in the 14-day check', 'rgb(59,130,246)') + '</div>' +
      v3Offers(b, r) +
      '<div class="g2"><div class="card pad"><div class="ch"><h3>Visitors by day</h3><span class="sp"></span><span class="lgd"><span><i style="background:' + SER[1] + '"></i>visitors</span><span><i style="background:' + SER[0] + '"></i>new users</span></span></div>' +
          (vis.some((v) => v > 0) ? v3Chart(days, vis, ubd) : '<div class="dim num">No visitors yet</div>') + '</div>' +
        '<div class="card pad"><div class="ch"><h3>From click to user</h3></div>' +
          '<div class="funnel">' + fun.map((f) => '<div class="fr' + (f[2] ? ' g' : '') + '"><span>' + f[0] + '</span><div class="fb"><i style="width:' + Math.max(f[1] ? 1.5 : 0, 100 * f[1] / fmax).toFixed(1) + '%"></i></div><b>' + fmt(f[1]) + '</b></div>').join('') + '</div>' +
          '<div class="dim num" style="font-size:11.5px;margin-top:12px">Cost per new user: <b style="color:var(--text)">' + (nu.counted ? usd(spent / nu.counted) + ' USDC' : '—') + '</b> · per visitor: <b style="color:var(--text)">' + (r.visitors_14d ? usd(spent / r.visitors_14d) + ' USDC' : '—') + '</b></div></div></div>' +
      ((S.pay || S.payMsg) ? payBox(((api(MINE) || {}).products || {}).payouts && { ...api(MINE).products.payouts, items: (api(MINE).products.payouts.items || []).filter((x) => String(x.brief_id) === String(b.id)) }) : '') +
      v3Promoters(b, r);
    return dash('products', inner);
  }

  /* above Open briefs: one line, the details in the fold their page already has */
  function v3Protect() {
    const R = howAnswer().rules || [], rule = (re) => (R.find((r) => re.test(r.title)) || {}).text || '';
    const pills = [['uniq', 'Real people only', rule(/visitor/i)], ['users', 'One person, one user', rule(/one person/i)],
      ['x', 'Fake X accounts filtered', 'Cymetica reads each promoter\'s public X: real views, real followers, account age. Bought audiences and new accounts are refused.'],
      ['clock', 'Paid after a 7–14 day check', rule(/14 days/i)]];
    return '<section class="v3prot"><span class="v3sh">' + ic('shield') + '</span><div class="v3pt"><b>User protection</b><span>Only real people are paid for</span></div>' +
      '<div class="v3pills">' + pills.map((p) => '<span class="v3pill" data-tip="' + esc(p[2]) + '">' + ic(p[0]) + p[1] + '</span>').join('') + '</div>' +
      '<button class="v3how" data-v3how="1">How ' + ic('down') + '</button></section>';
  }

  function v3check(id) {
    const h = (($('v3xh') || {}).value || '').trim().replace(/^@/, '');
    if (!h) { const i = $('v3xh'); if (i) i.focus(); return; }
    const b = findBrief(id); if (!b) return;
    fetch('/__v3/x/' + encodeURIComponent(h) + '?pv=' + b.per_visitor_usdc).then((r) => r.json()).then((res) => { S.v3x[id] = { h: h, res: res }; openBrief(id); });
  }
  document.addEventListener('keydown', (e) => { if (e.key === 'Enter' && e.target.id === 'v3xh') { const btn = document.querySelector('[data-v3check]'); if (btn) v3check(+btn.dataset.v3check); } });
  document.addEventListener('input', (e) => {
    const t = e.target, F = S.form; if (!F) return;
    if (t.dataset.v3f) { F[t.dataset.v3f] = t.value; return refreshPreview(); }
    if (t.dataset.f) {
      const x = $('v3ex'); if (x) x.innerHTML = v3offerLine(F.per_visitor);
      ['per_user', 'per_visitor'].forEach((k) => { const c = $('v3c-' + k); if (c) c.textContent = v3cents(F[k]); });
    }
  });
  document.addEventListener('click', (e) => {
    const t = e.target.closest('[data-v3inbox],[data-v3ok],[data-v3no],[data-v3check],[data-v3change],[data-v3take],[data-v3how]'); if (!t) return;
    const d = t.dataset;
    if (d.v3inbox) {
      const w = v3Waiting().find((x) => x.n) || v3Waiting()[0];
      if (!w) return toast('No offer waiting');
      location.hash = '#mybrief/' + w.id;
      return setTimeout(() => { const o = $('v3offers'); if (o) o.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, 400);
    }
    if (d.v3ok || d.v3no) { S.v3dec[d.v3ok || d.v3no] = d.v3ok ? 'approved' : 'declined'; toast((d.v3ok ? 'Approved' : 'Declined') + ' (local copy: nothing sent)'); return rerender(); }
    if (d.v3check) return v3check(+d.v3check);
    if (d.v3change) { S.v3x[+d.v3change] = { h: (S.v3x[+d.v3change] || {}).h }; return openBrief(+d.v3change); }
    if (d.v3take) { S.v3x[+d.v3take].sent = true; toast('Offer sent to the owner (local copy: nothing sent)'); return openBrief(+d.v3take); }
    if (d.v3how) { const f = document.querySelector('details.fold'); if (f) { f.open = true; f.scrollIntoView({ behavior: 'smooth', block: 'center' }); } }
  });
