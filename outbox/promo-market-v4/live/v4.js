  /* ===== Promo Market v4, on top of what they shipped as v3 (ET-33031). Its function declarations replace theirs of the
   * same name; their helpers are called as they are. The look only: how an offer is read, held and paid is theirs.
   * What changes (the operator, 2026-11-05): no unique visitors, no clicks, no new users, no tracked link. A brief is a
   * budget in USDC or ET10 that the owner hands out in offers; a promoter says what they want, the owner approves it or
   * sets another amount, the promoter accepts; what is not handed out stays in the brief, which stays open until it
   * is handed out or cancelled. A post that has stayed up 3 days is paid, by the owner's own Pay. ===== */
  const V4_DEF = { USDC: 20, ET10: 50000 };
  const V4_QUICK = { USDC: [20, 50, 100, 250], ET10: [10000, 50000, 100000, 250000] };
  const v4n = (n) => Number(n).toLocaleString('en-US', { maximumFractionDigits: 4 });
  const v4amt = (n, cur, sub) => '<b>' + v4n(n) + '<small>' + esc(cur) + '</small></b>' + (sub ? '<em>' + sub + '</em>' : '');
  const v4eq = (n, cur) => (cur === 'USDC' ? '= $' + v4n(n) : 'paid in ET10');
  S.v4o = {}; S.v4chk = {}; S.v4pay = null; S.v4seen = {};
  const v4hash = (v) => String(v).split(':');
  const v4state = (o, owner) => ({
    pending: owner ? 'waiting for you' : 'sent to the owner',
    countered: owner ? 'waiting for @' + esc(o.handle) + ' to accept' : 'the owner changed the amount',
    approved: owner ? 'agreed · no post yet' : 'agreed · post it',
    posted: 'posted · day ' + Math.min(3, o.days_up + 1) + ' of 3',
    earned: owner ? 'ready for your Pay' : 'waiting for the owner to pay',
    paid: 'paid', declined: 'declined' }[o.state] || o.state);
  const v4chip = (o, owner) => '<span class="chip ' + ({ pending: 'c', countered: 'c', earned: 'g', paid: 'g', posted: 'c' }[o.state] || '') + '">' + v4state(o, owner) + '</span>';
  const v4steps = (o) => {
    const at = { pending: 0, countered: 0, approved: 1, posted: 2, earned: 3, paid: 4 }[o.state] || 0;
    return '<div class="v4steps">' + ['Offer', 'Agreed', 'Posted', '3 days up', 'Paid'].map((t, k) => '<span class="' + (k < at ? 'done' : k === at ? 'now' : '') + '"><i></i>' + t + '</span>').join('') + '</div>';
  };
  function v4after(bid) { load(resultsUrl(+bid), true); load(MINE, true); load(BRIEFS, true); rerender(); if ($('drawer').classList.contains('on')) openBrief(+bid, true); }
  function v4left() {
    const L = (briefsAnswer().stats || {}).left || {}, keys = Object.keys(L);
    return keys.length ? keys.map((c) => '<span class="pos">' + v4n(L[c]) + '</span><small>' + esc(c) + '</small>').join(' ') : '<span class="pos">0</span>';
  }
  function sortBriefs(list) { return list.slice(); }

  /* the top bar's bell: offers waiting for the owner, across the owner's briefs */
  function v3Waiting() {
    return prodsOf().map((p) => p.brief).filter((r) => r && r.brief)
      .map((r) => ({ id: r.brief.id, n: (r.offers || []).filter((o) => o.state === 'pending').length }));
  }

  /* above Open briefs: one line, four pills, How */
  function v3Protect() {
    const R = howAnswer().rules || [], rule = (k) => (R[k] || {}).text || '';
    const pills = [['x', 'Real X accounts only', rule(0)], ['coin', 'You set the amount', rule(1)], ['clock', 'Paid after 3 days up', rule(3)], ['wallet', 'You pay · nothing automatic', rule(4)]];
    return '<section class="v3prot"><span class="v3sh">' + ic('shield') + '</span><div class="v3pt"><b>User protection</b><span>Only real accounts, paid after the post stayed up</span></div>' +
      '<div class="v3pills">' + pills.map((p) => '<span class="v3pill" tabindex="0" data-tip="' + esc(p[2]) + '">' + ic(p[0]) + p[1] + '</span>').join('') + '</div>' +
      '<button class="v3how" data-v3how="1">How ' + ic('down') + '</button></section>';
  }

  /* ---------- Post a brief: a budget, in USDC or ET10 ---------- */
  function defaultForm(path) {
    const prods = prodsOf().filter((x) => !x.site), site = path === V3_SITE || !prods.length;
    const p = site ? null : (prods.find((x) => x.path === path) || prods[0]);
    const cur = (S.form && S.form.cur) || 'USDC';
    const F = { path: site ? V3_SITE : p.path, cur: cur, budget: V4_DEF[cur], say: '', msg: '', site_name: '', site_url: 'https://' };
    F.mats = [{ kind: 'image', title: 'Cover picture', shot: true, url: site ? null : (p.preview_url || null), src: site ? null : pic(p.path),
      size: site ? 'goes with every post · drop one above' : 'goes with every post · now a screenshot of your page; drop your own above' },
      { kind: 'text', title: 'X post', body: '' }];
    if (!site) F.mats.push({ kind: 'link', title: 'Link to the page', url: p.url });
    return F;
  }
  function formBrief(F) {
    const site = F.path === V3_SITE;
    const p = site ? { name: F.site_name || 'Your website', path: null, url: F.site_url } : (prodsOf().find((x) => x.path === F.path) || {});
    return { id: 0, name: p.name, path: p.path, url: p.url, site: site, currency: F.cur, budget: F.budget, left: F.budget, status: 'open', say_line: F.say,
      preview_src: F.mats[0] && F.mats[0].kind === 'image' ? F.mats[0].src : null, materials: F.mats.filter((m) => (m.kind !== 'text' || m.body) && !m.busy) };
  }
  function briefCard(b, preview) {
    const o = S.v4o[b.id], src = v3pic(b);
    return '<article class="bc v3bc"' + (preview ? '' : ' data-brief="' + b.id + '"') + '>' +
      '<div class="img">' + (src ? '<img alt="" src="' + esc(src) + '">' : '<div class="v3noimg">' + ic('globe') + '</div>') + '</div>' +
      '<div class="bd"><div class="nm"><b>' + esc(shortName(b.name)) + '</b>' + v3where(b) + '</div>' +
        (b.say_line ? '<p class="say">' + esc(b.say_line) + '</p>' : '<p class="say dim">—</p>') +
        '<div class="ufg tipl" data-tip="What the owner still has to hand out. The brief stays open until it is handed out or the owner cancels it"><span>Left <span class="i">i</span></span>' + v4amt(b.left, b.currency) + '</div>' +
        '<div class="pays v3pays"><div><b class="v3auto">you say</b><span>per post</span><em>what you want for it</em></div><div><b>3 days</b><span>up, then paid</span><em>by the owner</em></div></div>' +
        (o ? '<button class="btn c full" data-brief="' + b.id + '">' + ic('check') + 'Your offer · ' + v4state(o, false) + '</button>' :
          '<button class="btn g full lg" ' + (preview ? 'disabled' : 'data-brief="' + b.id + '"') + '>Make an offer ' + ic('arrow') + '</button>') +
      '</div></article>';
  }
  function newBrief(path) {
    if (!OWNER) return dash('products');
    if (!need([MINE])) return waitBox('your products');
    if (!S.form || (path && S.form.path !== path)) S.form = defaultForm(path);
    const F = S.form, prods = api(MINE).products, P = (prods.products || []).filter((x) => !x.site), site = F.path === V3_SITE;
    const matRow = (m, i) => m.kind === 'text' ?
      '<div class="mat txt"><div class="th">' + ic('text') + '</div><div><b>' + esc(m.title) + '</b><span>ready-made text, copied by promoters</span></div><button class="x" data-rmmat="' + i + '" aria-label="Remove">' + ic('close') + '</button>' +
        '<textarea class="in" data-mat="' + i + '" placeholder="Write the post promoters can copy">' + esc(m.body) + '</textarea></div>' :
      m.kind === 'link' ? '<div class="mat txt v3link"><div class="th">' + ic('link') + '</div><div><b>' + esc(m.title) + '</b><span>promoters put it in their post</span></div><button class="x" data-rmmat="' + i + '" aria-label="Remove">' + ic('close') + '</button>' +
        '<input class="in" data-matlink="' + i + '" value="' + esc(m.url) + '" placeholder="https://…"></div>' :
      m.shot ? '<div class="mat v3cover"><div class="th">' + (m.src ? '<img alt="" src="' + esc(m.src) + '">' : ic('image')) + '</div>' +
        '<div><b>Cover picture</b><span>' + esc(m.size) + '</span></div><button class="x" data-rmmat="' + i + '" aria-label="Remove">' + ic('close') + '</button></div>' :
      '<div class="mat"><div class="th">' + (m.kind === 'image' && m.src ? '<img alt="" src="' + esc(m.src) + '">' : ic(m.kind === 'video' ? 'video' : 'image')) + '</div>' +
        '<div><b>' + esc(m.title) + '</b><span>' + esc(m.busy ? 'uploading…' : m.err || m.size || '') + '</span></div><button class="x" data-rmmat="' + i + '" aria-label="Remove">' + ic('close') + '</button></div>';
    const b = formBrief(F), busy = F.mats.some((m) => m.busy);
    const ok = F.budget > 0 && !busy && (!site || /^https?:\/\/[^/\s]+\.[^/\s]+/.test(F.site_url));
    return '<div class="wrap"><div class="nbtop"><a class="back" href="#me/products">' + ic('arrow') + 'My products</a><h1>Post a brief</h1><span class="sp" style="flex:1"></span>' +
        '<span class="chip g tipr" data-tip="' + esc(PAGE().products_note) + '">' + ic('lock') + 'The budget stays in your own wallet</span></div>' +
      '<div class="nb v3nb">' +
        '<div class="card"><div class="colh"><span class="no">1</span><b>What and pay</b></div>' +
          '<div class="pick v3pick"><button data-pick="' + V3_SITE + '" class="v3site' + (site ? ' on' : '') + '"><span class="v3g">' + ic('globe') + '</span><div><b>My own website</b><span>any site, also outside Cymetica</span></div><em>any URL</em></button>' +
            P.map((p) => '<button data-pick="' + esc(p.path) + '" class="' + (p.path === F.path ? 'on' : '') + '"><img alt="" src="' + esc(pic(p.path)) + '"><div><b>' + esc(shortName(p.name)) + '</b><span>cymetica.com' + esc(p.path) + '</span></div></button>').join('') + '</div>' +
          (site ? '<div class="v3sitef"><input class="in" id="v3sn" data-v3f="site_name" placeholder="Name, e.g. My Shop" value="' + esc(F.site_name) + '"><input class="in" id="v3su" data-v3f="site_url" placeholder="https://your-site.com" value="' + esc(F.site_url) + '"></div>' : '') +
          '<div class="v3lbl top">' + ic('coin') + 'Budget · paid in</div>' +
          '<div class="seg v4cur">' + ['USDC', 'ET10'].map((c) => '<button data-v4cur="' + c + '" class="' + (F.cur === c ? 'on' : '') + '">' + c + '</button>').join('') + '</div>' +
          '<div class="v3amt v4big"><input class="in" id="v4budget" data-f="budget" inputmode="decimal" value="' + F.budget + '" aria-label="Budget in ' + F.cur + '"><i>' + F.cur + '</i><em id="v4eq">' + v4eq(F.budget, F.cur) + '</em></div>' +
          '<div class="quick">' + V4_QUICK[F.cur].map((v) => '<button data-v4amt="' + v + '">' + v4n(v) + '</button>').join('') + '</div>' +
          '<div class="v3ex" style="margin-top:10px">Promoters say what they want for a post; you approve it or set another amount. What you do not hand out stays here, and the brief stays open until you cancel it.</div>' +
          '<label class="f" style="margin-top:14px">One line for promoters to say <span class="dim" id="saycnt">(' + F.say.length + ' / 280)</span><input class="in" data-f="say" maxlength="280" value="' + esc(F.say) + '" placeholder="optional"></label></div>' +
        '<div class="card"><div class="colh"><span class="no">2</span><b>Materials for promoters</b></div>' +
          '<label class="drop" id="drop">' + ic('upload') + '<b>Drop pictures or a video for promoters</b><span>PNG, JPG, GIF, MP4 or WebM · up to 50 MB each</span><input type="file" id="files" multiple accept="image/png,image/jpeg,image/gif,image/webp,video/mp4,video/webm" hidden></label>' +
          '<div class="mats">' + F.mats.map(matRow).join('') + '</div>' +
          '<div class="acts" style="margin-top:10px"><button class="btn sm" data-addmat="text">' + ic('text') + 'Add a text</button><button class="btn sm" data-addmat="link">' + ic('link') + 'Add a link</button></div></div>' +
        '<div class="card"><div class="colh"><span class="no">3</span><b>As promoters will see it</b></div><div class="preview">' + briefCard(b, true) +
          '<div class="sendbar">' +
            '<div class="note">' + ic('users') + '<span>Open until you have handed out ' + v4n(F.budget) + ' ' + F.cur + ' or cancel it. No end date.</span></div>' +
            '<div class="note">' + ic('shield') + '<span>Opens only when your own ' + F.cur + ', read on-chain, covers ' + v4n(F.budget) + ' ' + F.cur + '.</span></div>' +
            (F.msg ? '<div class="statusrow neg" role="alert">' + esc(F.msg) + '</div>' : '') +
            '<button class="btn g lg full" data-act="publish"' + (ok ? '' : ' disabled') + '>Post the brief ' + ic('arrow') + '</button><a class="btn gh full" href="#me/products">Cancel</a></div></div></div>' +
      '</div></div>';
  }
  function publish(btn) {
    const F = S.form, site = F.path === V3_SITE;
    const bad = F.mats.find((m) => m.err);
    if (bad) { F.msg = bad.title + ': ' + bad.err + ' — remove it or upload it again.'; return rerender(); }
    const materials = F.mats.filter((m) => (m.kind === 'text' ? m.body : true)).map((m) => (m.kind === 'text' ? { kind: 'text', title: m.title, body: m.body } :
      m.kind === 'link' ? { kind: 'link', title: m.title, url: m.url } : m.file_id ? { kind: m.kind, title: m.title, file_id: m.file_id } : { kind: 'image', title: m.title, url: m.url }))
      .filter((m) => (m.kind !== 'image' || m.file_id || m.url) && (m.kind !== 'link' || /^https?:\/\/[^\s/]+\.[^\s]+/.test(m.url || '')));
    const p = prodsOf().find((x) => x.path === F.path) || {};
    const body = { name: site ? F.site_name : p.name, path: site ? null : F.path, budget: F.budget, currency: F.cur, materials: materials };
    if (site) { body.site_url = F.site_url; body.site_name = F.site_name; }
    if (F.say) body.say_line = F.say;
    send('POST', '/api/v1/promo/briefs', body, btn).then((r) => {
      if (!r.ok) { F.msg = msgOf(r.j); return rerender(); }
      S.form = null; toast('Brief posted · your ' + body.currency + ' covers it');
      load(MINE, true); load(BRIEFS, true);
      location.hash = '#mybrief/' + r.j.brief.id;
    });
  }

  /* ---------- a promoter opens the brief ---------- */
  function openBrief(id, again) {
    const b = findBrief(id);
    if (!b) {
      send('GET', '/api/v1/promo/briefs/' + id).then((r) => { if (r.ok && r.j.brief) { S.detail = r.j; learn(r.j.brief.path, r.j.brief.preview_url, r.j.brief.art); openBrief(id); } else toast('Brief not found'); });
      return;
    }
    if (!again && SIGNED) {
      send('GET', '/api/v1/promo/briefs/' + id).then((r) => {
        if (!r.ok) return;
        const was = JSON.stringify(S.v4o[id] || null); S.v4o[id] = r.j.my_offer || null;
        if (JSON.stringify(S.v4o[id]) !== was && $('drawer').classList.contains('on')) openBrief(id, true);
      });
    }
    const mats = b.materials || [];
    $('drawer').innerHTML = '<div class="dh"><img alt="" src="' + esc(v3pic(b) || b.art) + '"><button class="x" data-act="close" aria-label="Close">' + ic('close') + '</button></div><div class="db">' +
      '<div class="meta"><span class="chip g tipl" data-tip="The owner\'s own ' + esc(b.currency) + ' covers this brief, read on-chain ' + esc(when(b.owner_funds && b.owner_funds.checked_at)) + '">' + ic('shield') + 'Funds checked on-chain</span></div>' +
      '<div><h2>' + esc(shortName(b.name)) + '</h2>' + v3where(b) + '</div>' +
      (b.say_line ? '<p class="say" style="margin:0;color:var(--text2)">“' + esc(b.say_line) + '”</p>' : '') +
      '<div class="ufg tipl" data-tip="What the owner still has to hand out. The brief stays open until it is handed out or the owner cancels it"><span>Left in the brief <span class="i">i</span></span><b>' + v4n(b.left) + '<small>of ' + v4n(b.budget) + ' ' + esc(b.currency) + '</small></b></div>' +
      v3OfferBox(b) +
      (mats.length ? '<div class="ch" style="margin:6px 0 0"><h3>Materials to post</h3><span class="chip c">' + mats.length + '</span><span class="sp"></span><span class="dim num" style="font-size:11.5px">from the owner</span></div>' +
        '<div class="mgrid">' + mats.filter((m) => m.kind !== 'text').concat(mats.filter((m) => m.kind === 'text')).map((m) => matTile(m, b.path, b.id)).join('') + '</div>' : '') +
      '<details class="fold"><summary>' + ic('shield') + 'How offers are paid' + ic('down', 'chev') + '</summary><div class="fb">' + rulesGrid().replace('class="rules"', 'class="rules" style="grid-template-columns:1fr 1fr"') + '</div></details>' +
    '</div>';
    show();
  }
  /* the promoter's side of one brief, step by step: X account -> offer -> agreed -> post -> 3 days -> paid */
  function v3OfferBox(b) {
    const o = S.v4o[b.id], c = S.v4chk[b.id], cur = esc(b.currency);
    const head = '<div class="v3obh">' + ic('x') + '<b>' + (o ? 'Your offer' : 'Make an offer') + '</b><span class="sp"></span><span class="chip c">' + (o ? v4state(o, false) : 'with your X') + '</span></div>';
    const st = (k, v) => '<div><span>' + k + '</span><b>' + v + '</b></div>';
    const stats = (r) => '<div class="v3s4">' + st('Followers', fmt(r.followers)) + st('Views a post', fmt(r.views)) + st('Real audience', (r.real || 0) + ' %') + st('Account', esc(r.age)) + '</div>';
    const who = (r) => '<div class="v3who"><span class="v3av">' + esc(String(r.handle || '?')[0].toUpperCase()) + '</span><b>@' + esc(r.handle) + '</b></div>';
    if (o) {
      const asked = o.ask !== o.amount && o.amount != null ? ' <small class="dim">you asked ' + v4n(o.ask) + '</small>' : '';
      const money = '<div class="v3big"><div><span>' + (o.state === 'pending' ? 'You ask' : o.state === 'countered' ? 'The owner offers' : 'Agreed') + '</span><b>' + v4n(o.amount != null ? o.amount : o.ask) + '<small>' + cur + '</small></b></div><em>' + asked + '</em></div>';
      let tail = '';
      if (o.state === 'pending') tail = '<div class="v3done pos">' + ic('check') + 'Sent to the owner · you hear when they answer</div>';
      if (o.state === 'countered') tail = '<div class="v4pair"><button class="btn g lg" data-v4accept="' + b.id + ':' + o.id + '">' + ic('check') + 'Accept ' + v4n(o.amount) + ' ' + cur + '</button><button class="btn gh lg" data-v4reject="' + b.id + ':' + o.id + '">Decline</button></div>';
      if (o.state === 'approved') tail = '<div class="v4post"><div class="v3obnote" style="margin:0 0 8px">Post it from <b>@' + esc(o.handle) + '</b>, the account that was checked, then paste the link of your post.</div>' +
        '<div class="own"><input class="in" id="v4purl" placeholder="Your post on X: https://x.com/…/status/…"><button class="btn c" data-v4post="' + b.id + '">Register post</button></div><div class="dim num" style="font-size:11.5px" id="v4pmsg"></div></div>';
      if (o.state === 'posted') tail = '<div class="v4days"><span class="' + (o.days_up >= 1 ? 'on' : '') + '"></span><span class="' + (o.days_up >= 2 ? 'on' : '') + '"></span><span class="' + (o.days_up >= 3 ? 'on' : '') + '"></span></div><div class="v3obnote" style="margin:6px 0 0">Day ' + Math.min(3, o.days_up + 1) + ' of 3 · keep the post up, it is paid after the third day. <a class="lnk" href="' + esc(o.post_url) + '" target="_blank" rel="noopener">your post ↗</a></div>';
      if (o.state === 'earned') tail = '<div class="v3done pos">' + ic('check') + 'It stayed up 3 days · waiting for the owner to pay</div>';
      if (o.state === 'paid') tail = '<div class="v3done pos">' + ic('coin') + 'Paid · ' + v4n(o.amount) + ' ' + cur + ' sent by the owner</div>';
      return '<div class="v3ob">' + head + who(o) + stats(o) + money + v4steps(o) + tail + '</div>';
    }
    if (!c) return '<div class="v3ob">' + head +
      '<div class="v3obin"><span>@</span><input class="in" id="v4h" placeholder="your X handle" autocomplete="off" maxlength="40"><button class="btn c" data-v4check="' + b.id + '">Check my X</button></div>' +
      (S.v4chk[b.id + ':err'] ? '<div class="v3not">' + ic('close') + '<span>' + esc(S.v4chk[b.id + ':err']) + '</span></div>' : '') +
      '<div class="v3obnote">Cymetica reads your public X: the real views of your own last posts, your followers and the account\'s age. A bought audience is refused.</div></div>';
    if (!c.ok) return '<div class="v3ob no">' + head + who(c) + stats(c) + '<div class="v3not">' + ic('close') + '<span><b>Not eligible.</b> ' + esc(c.why) + '</span></div>' +
      '<button class="btn gh full" data-v4again="' + b.id + '">Try another account</button></div>';
    return '<div class="v3ob">' + head + who(c) + stats(c) +
      '<label class="f" style="margin-top:10px">What do you want for the post?<div class="v3amt v4big"><input class="in" id="v4ask" inputmode="decimal" value="' + Math.min(b.left, V4_QUICK[b.currency][1]) + '"><i>' + cur + '</i></div></label>' +
      (SIGNED ? '<button class="btn g lg full" data-v4send="' + b.id + '" style="margin-top:10px">Send my offer ' + ic('arrow') + '</button>' :
        '<a class="btn g lg full" style="margin-top:10px" href="' + esc(signInHref(location.pathname + '#brief/' + b.id)) + '">Sign in to send my offer ' + ic('arrow') + '</a>') +
      '<div class="v3obnote">The owner approves it or sets another amount. Paid once your post has stayed up 3 days, by the owner\'s own Pay.</div></div>';
  }

  /* ---------- the owner's brief page ---------- */
  function ownerBrief(id) {
    const RU = resultsUrl(id);
    if (!need([RU, HOW])) return dash('products', waitIn('the brief'));
    const r = api(RU); if (!r || !r.brief) return dash('products', '<div class="card"><div class="empty"><b>This brief is not yours, or it does not exist.</b><a class="btn c sm" href="#me/products">My products</a></div></div>');
    const b = r.brief, cur = b.currency, O = r.offers || [], inPlay = O.filter((o) => ['countered', 'approved', 'posted', 'earned'].indexOf(o.state) >= 0);
    learn(b.path, b.preview_url, b.art);
    const open = b.status === 'open', closed = b.status === 'cancelled', agreed = b.budget - b.left - b.paid;
    const chipTxt = open ? '<i class="live"></i>Open · until handed out or cancelled' : closed ? 'Cancelled' : b.status === 'full' ? 'All handed out' : esc(b.status);
    const big = (n) => '<span class="pos">' + v4n(n) + '</span><small>' + esc(cur) + '</small>';
    const inner = '<div class="ph"><a class="back" href="#me/products">' + ic('arrow') + 'My products</a></div>' +
      '<div class="card bdhead"><img alt="" src="' + esc(v3pic(b) || b.art) + '"><div><h1>' + esc(shortName(b.name)) + '</h1><div class="meta">' +
          '<span class="chip ' + (open ? 'g' : '') + '">' + chipTxt + '</span>' +
          '<span class="chip g tipd" data-tip="Your own ' + esc(cur) + ' covers it, read on-chain ' + esc(when(b.owner_funds && b.owner_funds.checked_at)) + '">' + ic('shield') + 'Funds covered</span></div>' +
          (b.say_line ? '<div class="dim" style="margin-top:8px;font-size:13px">“' + esc(b.say_line) + '”</div>' : '') +
          '<div class="dim num" style="font-size:11.5px;margin-top:8px" id="act-msg">' + esc(S.actMsg || '') + '</div></div>' +
        '<div class="acts">' + (closed ? '' : '<button class="btn sm" data-bact="cancel" data-id="' + b.id + '">' + ic('close') + 'Cancel the brief</button>') +
          '<button class="btn sm c" data-copytext="' + esc(location.origin + '/promo-market#brief/' + b.id) + '">' + ic('link') + 'Share</button></div></div>' +
      '<div class="tiles" style="--n:4">' +
        tile('wallet', 'Budget', big(b.budget), 'in your wallet until you pay', 'rgb(0,207,255)') +
        // an ended brief does not say "left": that read as money held for you; the budget never left your wallet
        tile('coin', open ? 'Left to hand out' : 'Stays in your wallet', big(b.left), open ? 'on the market now' : 'never left it · nothing owed', 'rgb(0,255,136)') +
        tile('check', 'Agreed', big(agreed), fmt(inPlay.length) + ' post' + (inPlay.length === 1 ? '' : 's') + ' to pay') +
        tile('briefs', 'Paid', big(b.paid), 'sent by you', 'rgb(59,130,246)') + '</div>' +
      v3Offers(b, r) + (S.v4pay ? v4payBox(b, r) : '') + v3Promoters(b, r);
    return dash('products', inner);
  }
  function v3Offers(b, r) {
    const W = (r.offers || []).filter((o) => o.state === 'pending'), F = r.filtered_out || [], nf = F.reduce((s, f) => s + f[1], 0), cur = esc(b.currency);
    return '<div class="card v3offers" id="v3offers"><div class="tbar"><h3>Offers</h3>' + (W.length ? '<span class="chip g"><i class="live"></i>' + W.length + ' waiting for you</span>' : '') +
        '<span class="sp" style="flex:1"></span><span class="chip r tipr" data-tip="' + esc(F.map((f) => f[1] + ' × ' + f[0]).join(' · ')) + '">' + ic('shield') + nf + ' filtered out by Cymetica</span></div>' +
      (W.length ? '<div class="tscroll"><table class="tbl v3tbl"><thead><tr><th>Promoter</th><th class="n">Followers</th><th class="n">Views a post</th><th class="n">Real audience</th><th class="n">Asks</th><th class="n">You give</th><th></th></tr></thead><tbody>' +
        W.map((o) => '<tr class="v3wait"><td><span class="v3pm"><span class="v3av">' + esc(o.handle[0].toUpperCase()) + '</span><span><b>@' + esc(o.handle) + '</b><small>applied ' + esc(o.applied) + ' · on X ' + esc(o.age) + '</small></span></span></td>' +
          '<td class="n">' + fmt(o.followers) + '</td><td class="n">' + fmt(o.views) + '</td><td class="n">' + o.real + ' %</td><td class="n v3of">' + v4n(o.ask) + ' <small>' + cur + '</small></td>' +
          '<td class="n"><div class="v3amt v4give"><input class="in" id="v4a-' + o.id + '" data-v4ask="' + o.ask + '" data-v4btn="' + o.id + '" inputmode="decimal" value="' + o.ask + '" aria-label="Amount to give in ' + cur + '"><i>' + cur + '</i></div></td>' +
          '<td class="v3act"><button class="btn g sm" id="v4ok-' + o.id + '" data-v4award="' + b.id + ':' + o.id + '">' + ic('check') + 'Approve</button><button class="btn gh sm v3x" data-v4no="' + b.id + ':' + o.id + '" aria-label="Decline" data-tip="Decline">' + ic('close') + '</button></td></tr>').join('') + '</tbody></table></div>' :
        '<div class="empty" style="padding:22px"><span>No promoter is waiting for you.</span></div>') +
      '<div class="v3foot">' + ic('x') + '<span>A promoter says what they want for a post. Approve it, or change the amount and send it back; they accept or not. What you do not hand out stays in the brief.</span></div></div>';
  }
  function v3Promoters(b, r) {
    const rows = (r.offers || []).filter((o) => o.state !== 'pending'), cur = esc(b.currency);
    return '<div class="card v3prom"><div class="tbar"><h3 style="margin:0;font:17px var(--display)">Promoters</h3><span class="chip">' + rows.length + '</span></div>' +
      (rows.length ? '<div class="tscroll"><table class="tbl v3tbl"><thead><tr><th>Promoter</th><th class="n">Amount</th><th>Where it stands</th><th>Post</th><th></th></tr></thead><tbody>' +
        rows.map((o) => '<tr><td><span class="v3pm"><span class="v3av">' + esc(o.handle[0].toUpperCase()) + '</span><span><b>@' + esc(o.handle) + '</b><small>' + fmt(o.followers) + ' followers · on X ' + esc(o.age) + '</small></span></span></td>' +
          '<td class="n"><b class="v3of" style="font-size:15px">' + v4n(o.amount) + '</b> <small class="dim">' + cur + '</small>' + (o.ask !== o.amount ? '<br><small class="dim">asked ' + v4n(o.ask) + '</small>' : '') + '</td>' +
          '<td>' + v4chip(o, true) + '</td><td>' + (o.post_url ? '<a class="lnk" href="' + esc(o.post_url) + '" target="_blank" rel="noopener">post ↗</a>' : '<span class="dim">—</span>') + '</td>' +
          '<td class="v3act">' + (o.state === 'earned' ? '<button class="btn sm g" data-v4pay="' + b.id + ':' + o.id + '">Pay</button>' : '') + '</td></tr>').join('') + '</tbody></table></div>' :
        '<div class="empty"><b>Nobody is agreed</b>' + (b.status === 'open' ? '<span>It is on the market now, with ' + v4n(b.left) + ' ' + cur + ' left.</span><a class="btn c sm" href="#market" style="margin-top:6px">See it on the market</a>' :
          '<span>The brief is ended. ' + v4n(b.left) + ' ' + cur + ' stayed in your wallet.</span>') + '</div>') + '</div>';
  }
  /* the confirmation, as their Pay shows it: whose wallet, what, to where; nothing moves until the owner confirms */
  function v4payBox(b, r) {
    const o = (r.offers || []).find((x) => x.id === S.v4pay.oid); if (!o) return '';
    return '<div class="card pad" id="payouts" style="display:grid;gap:10px"><div class="ch" style="margin:0"><h3>Confirm payout</h3></div>' +
      '<div class="statusrow" role="dialog" aria-label="Confirm payout" style="display:grid;gap:8px;border-color:rgba(0,255,136,.35)">' +
        '<div class="num" style="font-size:12px"><b class="pos">' + v4n(o.amount) + '</b> ' + esc(b.currency) + ' to <b>@' + esc(o.handle) + '</b> on Ethereum<br>from your wallet 0x7Ae3…c41D<br>to their wallet 0x91Bf…20aE</div>' +
        '<div>The post stayed up 3 days. The network fee comes from your own funds.</div>' +
        '<div class="acts"><button class="btn g sm" data-v4payok="1">Confirm and pay</button><button class="btn gh sm" data-v4paycancel="1">Cancel</button></div></div></div>';
  }

  /* ---------- the owner's other pages: My products, and the promoter's Briefs I took ---------- */
  function products() {
    const M = api(MINE).products, prods = M.products || [];
    if (!prods.length) return '<div class="card"><div class="empty">' + holo(46) + '<b>No app of yours yet</b><span>Build an app with Build it Better: once it ships, it is listed here and you can post a brief for it.</span>' +
      '<a class="btn g" href="/build-it-better" style="margin-top:8px">Open Build it Better ' + ic('arrow') + '</a></div></div>';
    const rs = prods.map((p) => p.brief).filter(Boolean), by = {};
    rs.forEach((r) => { const c = r.brief.currency; (by[c] = by[c] || { left: 0, paid: 0 }); by[c].left += r.brief.status === 'open' ? r.brief.left : 0; by[c].paid += r.brief.paid; });
    const sumBy = (k) => Object.keys(by).length ? Object.keys(by).map((c) => '<span class="pos">' + v4n(by[c][k]) + '</span><small>' + esc(c) + '</small>').join(' ') : '<span class="pos">0</span>';
    const waiting = sum(rs, (r) => (r.offers || []).filter((o) => o.state === 'pending').length);
    return '<div class="tiles" style="--n:3">' +
        tile('coin', 'Left in your briefs', sumBy('left'), fmt(M.live_briefs) + ' live brief' + (M.live_briefs === 1 ? '' : 's'), 'rgb(0,255,136)') +
        tile('briefs', 'Offers waiting', fmt(waiting), 'for your answer') +
        tile('wallet', 'Paid', sumBy('paid'), 'sent by you', 'rgb(0,207,255)') + '</div>' +
      '<div class="grid4">' + prods.map(productCard).join('') + '</div>' +
      '<div class="note">' + ic('lock') + '<span>' + esc(PAGE().products_note) + '</span></div>';
  }
  function productCard(p) {
    const r = p.brief, b = r && r.brief, live = b && b.status !== 'cancelled';
    return '<article class="pc" data-product="' + esc(p.path) + '"><div class="img">' + (p.preview_url || !p.site ? '<img alt="" src="' + esc(p.site ? p.preview_url : pic(p.path)) + '">' : '<div class="v3noimg">' + ic('globe') + '</div>') +
        (b ? '<div class="tl"><span class="chip ' + (b.status === 'open' ? 'g' : '') + '">' + (b.status === 'open' ? '<i class="live"></i>Open' : esc(b.status)) + '</span></div>' : '') + '</div>' +
      '<div class="bd"><div class="nm"><b title="' + esc(p.name) + '">' + esc(shortName(p.name)) + '</b></div>' + v3where({ url: p.url, site: p.site, path: p.path }) +
        (b ? '<div class="r3"><div><b class="pos">' + v4n(b.left) + '</b><span>' + esc(b.currency) + (b.status === 'open' ? ' left' : ' kept') + '</span></div><div><b>' + fmt((r.offers || []).filter((o) => o.state === 'pending').length) + '</b><span>offers</span></div></div>' +
          '<a class="btn sm full" href="#mybrief/' + b.id + '">Open the brief ' + ic('arrow') + '</a>' + (live ? '' : '<a class="btn g sm full" href="#new' + esc(p.site ? '/' + V3_SITE : p.path) + '">' + ic('plus') + 'Create brief</a>') :
          '<div class="nob">No brief yet</div><a class="btn g sm full" href="#new' + esc(p.site ? '/' + V3_SITE : p.path) + '">' + ic('plus') + 'Create brief</a>') +
      '</div></article>';
  }
  function taken() {
    const list = (api(MINE).taken || { takes: [] }).takes || [], paid = list.filter((t) => t.offer.state === 'paid');
    return '<div class="tiles" style="--n:3">' + tile('briefs', 'Offers made', fmt(list.length), '') +
        tile('check', 'Agreed', fmt(list.filter((t) => ['approved', 'posted', 'earned', 'paid'].indexOf(t.offer.state) >= 0).length), 'to post, posted or paid') +
        tile('coin', 'Paid', fmt(paid.length), paid.map((t) => v4n(t.offer.amount) + ' ' + t.offer.currency).join(' · ') || 'by the owner', 'rgb(0,255,136)') + '</div>' +
      (list.length ? '<div class="card"><table class="tbl"><thead><tr><th>Brief</th><th class="n">Your offer</th><th>Where it stands</th><th>Post</th></tr></thead><tbody>' +
          list.map((t) => { const b = t.brief || {}, o = t.offer;
            return '<tr data-brief="' + b.id + '"><td><div class="tw" style="gap:12px"><img alt="" src="' + esc(pic(b.path)) + '" style="width:64px;height:36px;border-radius:7px;object-fit:cover"><span class="ttl">' + esc(shortName(b.name)) + '<small>' + v4n(b.left) + ' ' + esc(b.currency) + ' left</small></span></div></td>' +
            '<td class="n pos">' + v4n(o.amount != null ? o.amount : o.ask) + ' <small>' + esc(o.currency) + '</small>' + (o.amount != null && o.amount !== o.ask ? '<br><small class="dim">asked ' + v4n(o.ask) + '</small>' : '') + '</td>' +
            '<td>' + v4chip(o, false) + '</td><td>' + (o.post_url ? '<a class="lnk" href="' + esc(o.post_url) + '" target="_blank" rel="noopener">post ↗</a>' : '<span class="dim">—</span>') + '</td></tr>'; }).join('') + '</tbody></table></div>' :
        '<div class="card"><div class="empty">' + holo(46) + '<b>No offer made yet</b><span>' + esc(PAGE().taken_empty) + '</span><a class="btn g" href="#market" style="margin-top:8px">Open the Promo Market ' + ic('arrow') + '</a></div></div>') +
      '<div class="note">' + ic('wallet') + '<span>The owner pays with their own Pay press once your post has stayed up 3 days. Nothing is paid automatically.</span></div>';
  }

  /* ---------- the clicks of v4 ---------- */
  function v4call(path, body, btn) { return send('POST', path, body, btn); }
  document.addEventListener('keydown', (e) => { if (e.key === 'Enter' && e.target.id === 'v4h') { const b = document.querySelector('[data-v4check]'); if (b) b.click(); } });
  document.addEventListener('input', (e) => {
    const t = e.target;
    if (t.id === 'v4budget' && S.form) { const q = $('v4eq'); if (q) q.textContent = v4eq(S.form.budget, S.form.cur); }
    if (t.dataset.v4btn) { const b = $('v4ok-' + t.dataset.v4btn), same = (parseFloat(t.value) || 0) === +t.dataset.v4ask; if (b) b.innerHTML = ic('check') + (same ? 'Approve' : 'Offer this'); }
  });
  document.addEventListener('click', (e) => {
    const t = e.target.closest('[data-v4cur],[data-v4amt],[data-v4check],[data-v4again],[data-v4send],[data-v4award],[data-v4no],[data-v4accept],[data-v4reject],[data-v4post],[data-v4pay],[data-v4payok],[data-v4paycancel]'); if (!t) return;
    const d = t.dataset;
    if (d.v4cur) { S.form = null; S.form = Object.assign(defaultForm(S.form && S.form.path), { cur: d.v4cur }); S.form.budget = V4_DEF[d.v4cur]; return rerender(); }
    if (d.v4amt) { e.preventDefault(); S.form.budget = +d.v4amt; return rerender(); }
    if (d.v4check) {
      const id = +d.v4check, h = (($('v4h') || {}).value || '').trim().replace(/^@/, ''); if (!h) { if ($('v4h')) $('v4h').focus(); return; }
      return v4call('/api/v1/promo/briefs/' + id + '/offer/check', { handle: h }, t).then((r) => { if (r.ok) { S.v4chk[id] = r.j; delete S.v4chk[id + ':err']; } else S.v4chk[id + ':err'] = msgOf(r.j); openBrief(id, true); });
    }
    if (d.v4again) { const id = +d.v4again; delete S.v4chk[id]; return openBrief(id, true); }
    if (d.v4send) {
      const id = +d.v4send;
      return v4call('/api/v1/promo/briefs/' + id + '/offer/take', { ask: parseFloat(($('v4ask') || {}).value) }, t).then((r) => {
        if (!r.ok) return toast(msgOf(r.j));
        S.v4o[id] = r.j; delete S.v4chk[id]; toast('Offer sent · you hear when the owner answers'); load(MINE, true); openBrief(id, true);
      });
    }
    if (d.v4award || d.v4no) {
      const [bid, oid] = v4hash(d.v4award || d.v4no), body = d.v4no ? { decision: 'decline' } : { decision: 'approve', amount: parseFloat(($('v4a-' + oid) || {}).value) };
      return v4call('/api/v1/promo/briefs/' + bid + '/offers/' + oid, body, t).then((r) => {
        if (!r.ok) return toast(msgOf(r.j));
        toast(d.v4no ? 'Declined' : r.j.state === 'approved' ? 'Agreed · @' + r.j.handle + ' can post' : 'Sent back to @' + r.j.handle + ' with ' + v4n(r.j.amount) + ' ' + r.j.currency); v4after(bid);
      });
    }
    if (d.v4accept || d.v4reject) {
      const [bid, oid] = v4hash(d.v4accept || d.v4reject);
      return v4call('/api/v1/promo/briefs/' + bid + '/offers/' + oid + '/respond', { accept: !!d.v4accept }, t).then((r) => {
        if (!r.ok) return toast(msgOf(r.j)); S.v4o[+bid] = r.j; toast(d.v4accept ? 'Accepted · post it from @' + r.j.handle : 'Declined'); load(MINE, true); openBrief(+bid, true);
      });
    }
    if (d.v4post) {
      const id = +d.v4post, url = (($('v4purl') || {}).value || '').trim(); if (!url) { if ($('v4purl')) $('v4purl').focus(); return; }
      return v4call('/api/v1/promo/briefs/' + id + '/posts', { url: url }, t).then((r) => {
        if (!r.ok) { const m = $('v4pmsg'); if (m) m.textContent = msgOf(r.j); return; }
        S.v4o[id] = r.j; toast('Post registered · paid after 3 days up'); load(MINE, true); openBrief(id, true);
      });
    }
    if (d.v4pay) { const [bid, oid] = v4hash(d.v4pay); S.v4pay = { bid: +bid, oid: +oid }; return rerender(); }
    if (d.v4paycancel) { S.v4pay = null; return rerender(); }
    if (d.v4payok) {
      const p = S.v4pay;
      return v4call('/api/v1/promo/briefs/' + p.bid + '/offers/' + p.oid + '/pay', {}, t).then((r) => {
        S.v4pay = null; toast(r.ok ? 'Paid · ' + v4n(r.j.amount) + ' ' + r.j.currency + ' to @' + r.j.handle : msgOf(r.j)); v4after(p.bid);
      });
    }
  });
