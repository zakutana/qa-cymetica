  /* ===== Promo Market v4, on top of what they shipped as v3 (ET-33031). Its function declarations replace theirs of the
   * same name; their helpers are called as they are; four of theirs (rail, today, chrome, rerender) are wrapped: patch.py
   * gives theirs the name with a 0. The look only: how an X account is read, how credit is locked and moved is theirs.
   * What changes (the operator, 2026-11-05 and 2026-11-10): no unique visitors, no clicks, no new users, no tracked link.
   * A brief is a budget in USDC or ET10 with no end date; the owner can add funds to it. A creator sees Open briefs lit
   * in the dashboard's menu and takes one with their X handle: nothing about their account is shown to them. The owner
   * is told, sees the account, its expected reach and a suggested amount, and sends an amount: it is locked from the
   * owner's credit. The creator sees the amount and accepts it or not, then posts the prepared materials. After the
   * post has stayed up 3 days the owner approves and the locked amount moves to the creator. ===== */
  const V4_ROLE = BOOT.v4role || 'market', V4_OWNER = V4_ROLE === 'owner';
  const V4_DEF = { USDC: 100, ET10: 50000 };
  const V4_QUICK = { USDC: [50, 100, 250, 500], ET10: [10000, 50000, 100000, 200000] };
  const V4_ADD = { USDC: [25, 50, 100], ET10: [10000, 25000, 50000] };
  const v4n = (n) => Number(n).toLocaleString('en-US', { maximumFractionDigits: 4 });
  const v4amt = (n, cur, sub) => '<b>' + v4n(n) + '<small>' + esc(cur) + '</small></b>' + (sub ? '<em>' + sub + '</em>' : '');
  /* under the amount: what the owner's credit covers, in red when the budget is above it */
  const v4eq = (n, cur) => { const free = v4credit(cur).free; return n > free ? '<span class="neg">above your free credit of ' + v4n(free) + ' ' + cur + '</span>' : 'from your credit · ' + v4n(free) + ' ' + cur + ' free'; };
  S.v4o = {}; S.v4chk = {}; S.v4pay = null; S.v4add = false;
  const v4hash = (v) => String(v).split(':');
  const v4state = (o, owner) => ({
    pending: owner ? 'waiting for you' : 'sent to the owner',
    offered: owner ? 'offer sent · no answer yet' : 'the owner\'s offer · answer it',
    approved: owner ? 'accepted · no post yet' : 'accepted · post it',
    posted: 'posted · day ' + Math.min(3, o.days_up + 1) + ' of 3',
    earned: owner ? 'ready for your approval' : 'waiting for the owner\'s approval',
    paid: 'paid', declined: 'declined' }[o.state] || o.state);
  const v4chip = (o, owner) => '<span class="chip ' + ({ pending: 'c', offered: owner ? 'c' : 'g', approved: 'c', earned: 'g', paid: 'g', posted: 'c' }[o.state] || '') + '">' + v4state(o, owner) + '</span>';
  const v4steps = (o) => {
    const at = { pending: 0, offered: 1, approved: 2, posted: 3, earned: 4, paid: 5 }[o.state] || 0;
    return '<div class="v4steps">' + ['Taken', 'Offer', 'Accepted', 'Posted', '3 days', 'Paid'].map((t, k) => '<span class="' + (k < at ? 'done' : k === at ? 'now' : '') + '"><i></i>' + t + '</span>').join('') + '</div>';
  };
  /* the promoter's button on a brief they took: the owner's amount is the one thing that asks for an answer */
  const v4yours = (b, o, cls) => o.state === 'offered' ?
    '<button class="btn g ' + cls + '" data-brief="' + b.id + '">The owner offers ' + v4n(o.amount) + ' ' + esc(b.currency) + ' ' + ic('arrow') + '</button>' :
    '<button class="btn c ' + cls + '" data-brief="' + b.id + '">' + ic('check') + 'Yours · ' + v4state(o, false) + '</button>';
  const v4credit = (cur) => ((api(MINE) || {}).credit || {})[cur] || { free: 0, locked: 0 };
  const v4takes = () => (((api(MINE) || {}).taken || {}).takes || []);
  /* the promoter's own request on a brief: what an action or the last poll said, else what Briefs I took says */
  function v4mine(id) {
    if (S.v4o[id] !== undefined) return S.v4o[id];
    const t = v4takes().filter((x) => x.brief && x.brief.id === id && x.offer.state !== 'declined').pop();
    return t ? t.offer : null;
  }
  function v4after(bid) { load(resultsUrl(+bid), true); load(MINE, true); load(BRIEFS, true); rerender(); if ($('drawer').classList.contains('on')) openBrief(+bid, true); }
  function v4left() {
    const L = (briefsAnswer().stats || {}).left || {}, keys = Object.keys(L);
    return keys.length ? keys.map((c) => '<span class="pos">' + v4n(L[c]) + '</span><small>' + esc(c) + '</small>').join(' ') : '<span class="pos">0</span>';
  }
  function sortBriefs(list) { return list.slice(); }

  /* the top bar's bell: promoters waiting for the owner, across the owner's briefs */
  function v3Waiting() {
    return prodsOf().map((p) => p.brief).filter((r) => r && r.brief)
      .map((r) => ({ id: r.brief.id, n: (r.offers || []).filter((o) => o.state === 'pending').length }));
  }

  /* above Open briefs: one line, four pills, How */
  function v3Protect() {
    const R = howAnswer().rules || [], rule = (k) => (R[k] || {}).text || '';
    const pills = [['x', 'Real X accounts only', rule(0)], ['coin', 'The owner names the amount', rule(1)], ['lock', 'Locked with the offer', rule(3)], ['clock', 'Paid after 3 days up', rule(4)]];
    return '<section class="v3prot"><span class="v3sh">' + ic('shield') + '</span><div class="v3pt"><b>User protection</b><span>Only real accounts, locked with the offer, paid after the post stayed up</span></div>' +
      '<div class="v3pills">' + pills.map((p) => '<span class="v3pill" tabindex="0" data-tip="' + esc(p[2]) + '">' + ic(p[0]) + p[1] + '</span>').join('') + '</div>' +
      '<button class="v3how" data-v3how="1">How ' + ic('down') + '</button></section>';
  }

  /* ---------- the creator's dashboard: Open briefs lit in the menu, and what can be earned on top of Today ---------- */
  function v4open() { const A = briefsAnswer(); return A.briefs || []; }
  function rail(tab) {
    const html = rail0(tab);
    if (V4_OWNER) return html;
    need([BRIEFS]);
    const n = v4open().length, mark = '<div class="rsec">PROMOTE</div><nav class="rnav">';
    return html.replace(mark, mark + '<a href="#market" class="v4open' + (n ? ' lit' : '') + '">' + ic('coin') + 'Open briefs<span class="n">' + n + '</span></a>');
  }
  function v4earn() {
    const L = v4open(); if (!L.length) return '';
    return '<div class="card v4earn"><div class="v4eh"><span class="kick">Earn now</span><span class="chip g"><i class="live"></i>' + L.length + ' open brief' + (L.length === 1 ? '' : 's') + '</span>' +
        '<span class="sp" style="flex:1"></span><span class="v4et">' + v4left() + ' <em>to hand out</em></span></div>' +
      L.map((b) => { const o = v4mine(b.id), src = v3pic(b), has = o && o.amount != null;
        /* once the owner named an amount, the row's number is that amount: it is the promoter's, the brief's rest is not */
        return '<div class="v4er" data-brief="' + b.id + '">' + (src ? '<img alt="" src="' + esc(src) + '">' : '<span class="v3noimg">' + ic('globe') + '</span>') +
          '<div class="v4en"><b>' + esc(shortName(b.name)) + '</b><span>' + esc(b.say_line || 'Post about it on X') + '</span></div>' +
          '<div class="v4el' + (has ? ' mine' : '') + '"><b>' + v4n(has ? o.amount : b.left) + '<small>' + esc(b.currency) + '</small></b><span>' +
            (!has ? 'left to hand out' : o.state === 'offered' ? 'offered to you' : o.state === 'paid' ? 'paid to you' : 'locked for you') + '</span></div>' +
          (o && o.state === 'offered' ? '<button class="btn g lg" data-brief="' + b.id + '">Answer ' + ic('arrow') + '</button>' :
           o ? v4yours(b, o, '') :
            '<button class="btn g lg" data-brief="' + b.id + '">Take it ' + ic('arrow') + '</button>') + '</div>'; }).join('') +
      '<div class="v4ef">' + ic('x') + '<span>Take a brief with your X account. The owner sends you an amount: accept it, post the prepared materials, and after 3 days up it is yours.</span>' +
        '<a class="lnk" href="#market">all open briefs ' + ic('arrow') + '</a></div></div>';
  }
  function today() { return (V4_OWNER ? '' : v4earn()) + today0(); }
  function chrome(r) {
    chrome0(r);
    if (V4_OWNER) return;
    const n = v4open().length, a = $('tnav').querySelector('a[href="#market"]');
    if (a && n) a.insertAdjacentHTML('beforeend', '<span class="v4badge">' + n + '</span>');
  }
  /* a redraw keeps what is being typed in a v4 field: the other window can change this page at any moment */
  function v4keep(draw) {
    const kept = {}, a = document.activeElement, fid = a && /^v4/.test(a.id || '') ? a.id : null, pos = fid ? a.selectionStart : null;
    document.querySelectorAll('input[id^="v4"][data-v4dirty]').forEach((n) => { kept[n.id] = n.value; });
    draw();
    Object.keys(kept).forEach((id) => { const n = $(id); if (n) { n.value = kept[id]; n.dataset.v4dirty = '1'; } });
    if (fid) { const n = $(fid); if (n && document.activeElement !== n) { n.focus(); try { n.setSelectionRange(pos, pos); } catch (e) { /* not a text field */ } } }
  }
  function rerender() { v4keep(rerender0); }

  /* ---------- Post a brief: a budget, in USDC or ET10, no end date ---------- */
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
    const o = preview ? null : v4mine(b.id), src = v3pic(b);
    return '<article class="bc v3bc"' + (preview ? '' : ' data-brief="' + b.id + '"') + '>' +
      '<div class="img">' + (src ? '<img alt="" src="' + esc(src) + '">' : '<div class="v3noimg">' + ic('globe') + '</div>') + '</div>' +
      '<div class="bd"><div class="nm"><b>' + esc(shortName(b.name)) + '</b>' + v3where(b) + '</div>' +
        (b.say_line ? '<p class="say">' + esc(b.say_line) + '</p>' : '<p class="say dim">—</p>') +
        '<div class="ufg tipl" data-tip="What the owner still has to hand out. The brief stays open until it is handed out or the owner cancels it"><span>Left <span class="i">i</span></span>' + v4amt(b.left, b.currency) + '</div>' +
        '<div class="pays v3pays"><div><b class="v3auto">an offer</b><span>from the owner</span><em>you accept it or not</em></div><div><b>3 days</b><span>up, then paid</span><em>locked for you first</em></div></div>' +
        (o ? v4yours(b, o, 'full') :
          '<button class="btn g full lg" ' + (preview ? 'disabled' : 'data-brief="' + b.id + '"') + '>Take this brief ' + ic('arrow') + '</button>') +
      '</div></article>';
  }
  function newBrief(path) {
    if (!OWNER) return dash('products');
    if (!need([MINE])) return waitBox('your products');
    if (!S.form || (path && S.form.path !== path)) S.form = defaultForm(path);
    const F = S.form, prods = api(MINE).products, P = (prods.products || []).filter((x) => !x.site), site = F.path === V3_SITE, free = v4credit(F.cur).free;
    const matRow = (m, i) => m.kind === 'text' ?
      '<div class="mat txt"><div class="th">' + ic('text') + '</div><div><b>' + esc(m.title) + '</b><span>ready-made text, copied by promoters</span></div><button class="x" data-rmmat="' + i + '" aria-label="Remove">' + ic('close') + '</button>' +
        '<textarea class="in" data-mat="' + i + '" placeholder="Write the post promoters can copy">' + esc(m.body) + '</textarea></div>' :
      m.kind === 'link' ? '<div class="mat txt v3link"><div class="th">' + ic('link') + '</div><div><b>' + esc(m.title) + '</b><span>promoters put it in their post</span></div><button class="x" data-rmmat="' + i + '" aria-label="Remove">' + ic('close') + '</button>' +
        '<input class="in" data-matlink="' + i + '" value="' + esc(m.url) + '" placeholder="https://…"></div>' :
      m.shot ? '<div class="mat v3cover"><div class="th">' + (m.src ? '<img alt="" src="' + esc(m.src) + '">' : ic('image')) + '</div>' +
        '<div><b>Cover picture</b><span>' + esc(m.size) + '</span></div><button class="x" data-rmmat="' + i + '" aria-label="Remove">' + ic('close') + '</button></div>' :
      '<div class="mat"><div class="th">' + (m.kind === 'image' && m.src ? '<img alt="" src="' + esc(m.src) + '">' : ic(m.kind === 'video' ? 'video' : 'image')) + '</div>' +
        '<div><b>' + esc(m.title) + '</b><span>' + esc(m.busy ? 'uploading…' : m.err || m.size || '') + '</span></div><button class="x" data-rmmat="' + i + '" aria-label="Remove">' + ic('close') + '</button></div>';
    const b = formBrief(F), busy = F.mats.some((m) => m.busy), over = F.budget > free;
    const ok = F.budget > 0 && !over && !busy && (!site || /^https?:\/\/[^/\s]+\.[^/\s]+/.test(F.site_url));
    return '<div class="wrap"><div class="nbtop"><a class="back" href="#me/products">' + ic('arrow') + 'My products</a><h1>Post a brief</h1><span class="sp" style="flex:1"></span>' +
        '<span class="chip g tipr" data-tip="' + esc(PAGE().products_note) + '">' + ic('lock') + 'Locked only when you send an offer</span></div>' +
      '<div class="nb v3nb">' +
        '<div class="card"><div class="colh"><span class="no">1</span><b>What and pay</b></div>' +
          '<div class="pick v3pick"><button data-pick="' + V3_SITE + '" class="v3site' + (site ? ' on' : '') + '"><span class="v3g">' + ic('globe') + '</span><div><b>My own website</b><span>any site, also outside Cymetica</span></div><em>any URL</em></button>' +
            P.map((p) => '<button data-pick="' + esc(p.path) + '" class="' + (p.path === F.path ? 'on' : '') + '"><img alt="" src="' + esc(pic(p.path)) + '"><div><b>' + esc(shortName(p.name)) + '</b><span>cymetica.com' + esc(p.path) + '</span></div></button>').join('') + '</div>' +
          (site ? '<div class="v3sitef"><input class="in" id="v3sn" data-v3f="site_name" placeholder="Name, e.g. My Shop" value="' + esc(F.site_name) + '"><input class="in" id="v3su" data-v3f="site_url" placeholder="https://your-site.com" value="' + esc(F.site_url) + '"></div>' : '') +
          '<div class="v3lbl top">' + ic('coin') + 'Budget · paid in</div>' +
          '<div class="seg v4cur">' + ['USDC', 'ET10'].map((c) => '<button data-v4cur="' + c + '" class="' + (F.cur === c ? 'on' : '') + '">' + c + '</button>').join('') + '</div>' +
          '<div class="v3amt v4big"><input class="in" id="v4budget" data-f="budget" inputmode="decimal" value="' + F.budget + '" aria-label="Budget in ' + F.cur + '"><i>' + F.cur + '</i><em id="v4eq">' + v4eq(F.budget, F.cur) + '</em></div>' +
          '<div class="quick">' + V4_QUICK[F.cur].map((v) => '<button data-v4amt="' + v + '">' + v4n(v) + '</button>').join('') + '</div>' +
          '<div class="v3ex" style="margin-top:10px">A promoter takes the brief with their X account. You see their expected reach and a suggested amount, and send them your amount: only then it is locked from your credit. They accept it or not. What you do not hand out stays here; add funds any time.</div>' +
          '<label class="f" style="margin-top:14px">One line for promoters to say <span class="dim" id="saycnt">(' + F.say.length + ' / 280)</span><input class="in" data-f="say" maxlength="280" value="' + esc(F.say) + '" placeholder="optional"></label></div>' +
        '<div class="card"><div class="colh"><span class="no">2</span><b>Materials for promoters</b></div>' +
          '<label class="drop" id="drop">' + ic('upload') + '<b>Drop pictures or a video for promoters</b><span>PNG, JPG, GIF, MP4 or WebM · up to 50 MB each</span><input type="file" id="files" multiple accept="image/png,image/jpeg,image/gif,image/webp,video/mp4,video/webm" hidden></label>' +
          '<div class="mats">' + F.mats.map(matRow).join('') + '</div>' +
          '<div class="acts" style="margin-top:10px"><button class="btn sm" data-addmat="text">' + ic('text') + 'Add a text</button><button class="btn sm" data-addmat="link">' + ic('link') + 'Add a link</button></div></div>' +
        '<div class="card"><div class="colh"><span class="no">3</span><b>As promoters will see it</b></div><div class="preview">' + briefCard(b, true) +
          '<div class="sendbar">' +
            '<div class="note">' + ic('clock') + '<span>No end date: open until you have handed out ' + v4n(F.budget) + ' ' + F.cur + ' or cancel it.</span></div>' +
            '<div class="note' + (over ? ' v4over' : '') + '">' + ic('wallet') + '<span>' + (over ? 'Above your free credit of ' + v4n(free) + ' ' + F.cur + '.' : 'Covered by your Cymetica credit: ' + v4n(free) + ' ' + F.cur + ' free.') + '</span></div>' +
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
      S.form = null; toast('Brief posted · it is on the market');
      load(MINE, true); load(BRIEFS, true);
      location.hash = '#mybrief/' + r.j.brief.id;
    });
  }

  /* ---------- a promoter opens the brief ---------- */
  function openBrief(id, again) {
    const b = findBrief(id);
    if (!b) {
      send('GET', '/api/v1/promo/briefs/' + id).then((r) => { if (r.ok && r.j.brief) { S.detail = r.j; S.v4o[id] = r.j.my_offer || null; learn(r.j.brief.path, r.j.brief.preview_url, r.j.brief.art); openBrief(id, true); } else toast('Brief not found'); });
      return;
    }
    if (!again && SIGNED) {
      send('GET', '/api/v1/promo/briefs/' + id).then((r) => {
        if (!r.ok) return;
        const was = JSON.stringify(v4mine(id)); S.v4o[id] = r.j.my_offer || null;
        if (JSON.stringify(S.v4o[id]) !== was && $('drawer').classList.contains('on')) openBrief(id, true);
      });
    }
    const mats = b.materials || [], o = v4mine(id), go = o && o.state === 'approved';
    $('drawer').innerHTML = '<div class="dh"><img alt="" src="' + esc(v3pic(b) || b.art) + '"><button class="x" data-act="close" aria-label="Close">' + ic('close') + '</button></div><div class="db" data-v4brief="' + id + '">' +
      '<div class="meta"><span class="chip g tipl" data-tip="The owner\'s Cymetica credit covers what is left. An amount is locked from it the moment the owner sends you an offer">' + ic('shield') + 'Covered by the owner\'s credit</span></div>' +
      '<div><h2>' + esc(shortName(b.name)) + '</h2>' + v3where(b) + '</div>' +
      (b.say_line ? '<p class="say" style="margin:0;color:var(--text2)">“' + esc(b.say_line) + '”</p>' : '') +
      '<div class="ufg tipl" data-tip="What the owner still has to hand out. The brief stays open until it is handed out or the owner cancels it"><span>Left in the brief <span class="i">i</span></span><b>' + v4n(b.left) + '<small>of ' + v4n(b.budget) + ' ' + esc(b.currency) + '</small></b></div>' +
      v3OfferBox(b) +
      (mats.length ? '<div class="ch" style="margin:6px 0 0"><h3>' + (go ? 'Post these' : 'Materials to post') + '</h3><span class="chip ' + (go ? 'g' : 'c') + '">' + mats.length + '</span><span class="sp"></span><span class="dim num" style="font-size:11.5px">prepared by the owner</span></div>' +
        '<div class="mgrid">' + mats.filter((m) => m.kind !== 'text').concat(mats.filter((m) => m.kind === 'text')).map((m) => matTile(m, b.path, b.id)).join('') + '</div>' : '') +
      '<details class="fold"><summary>' + ic('shield') + 'How offers are paid' + ic('down', 'chev') + '</summary><div class="fb">' + rulesGrid().replace('class="rules"', 'class="rules" style="grid-template-columns:1fr 1fr"') + '</div></details>' +
    '</div>';
    show();
  }
  /* the post, ready in X: the owner's text and link */
  function v4intent(b) {
    const M = b.materials || [], t = M.find((m) => m.kind === 'text'), l = M.find((m) => m.kind === 'link');
    const text = [t && t.body, l && l.url].filter(Boolean).join(' ') || b.say_line || b.url || '';
    return 'https://x.com/intent/post?text=' + encodeURIComponent(text);
  }
  /* the promoter's side of one brief, step by step: take with the X handle -> the owner's offer -> accept or not ->
   * post -> 3 days -> paid. Nothing about the promoter's own account is shown here: the owner looks at it. */
  function v3OfferBox(b) {
    const o = v4mine(b.id), cur = esc(b.currency), pair = b.id + ':' + (o ? o.id : 0), err = S.v4chk[b.id + ':err'];
    const head = '<div class="v3obh">' + ic('x') + '<b>' + (o ? 'Your brief' : 'Take this brief') + '</b><span class="sp"></span><span class="chip ' + (o && ['offered', 'approved', 'paid'].indexOf(o.state) >= 0 ? 'g' : 'c') + '">' + (o ? v4state(o, false) : 'with your X') + '</span></div>';
    const who = (r) => '<div class="v3who"><span class="v3av">' + esc(String(r.handle || '?')[0].toUpperCase()) + '</span><b>@' + esc(r.handle) + '</b></div>';
    if (o) {
      let money = '', tail = '';
      if (o.state === 'pending') {
        tail = '<div class="v3done pos">' + ic('check') + 'Sent to the owner · they look at your X and send you an amount</div><button class="btn gh sm v4quiet" data-v4pass="' + pair + '" data-v4was="pending">Withdraw my request</button>';
      } else if (o.state === 'offered') {
        money = '<div class="v3big v4lock v4offer"><div><span>The owner offers you</span><b>' + v4n(o.amount) + '<small>' + cur + '</small></b></div>' +
          '<em>' + ic('lock') + 'locked for you · paid after your post stayed up 3 days</em></div>';
        tail = '<div class="v4yn"><button class="btn g lg" data-v4yes="' + pair + '">' + ic('check') + 'Accept · ' + v4n(o.amount) + ' ' + cur + '</button>' +
          '<button class="btn gh lg" data-v4pass="' + pair + '" data-v4was="offered">No, thanks</button></div>';
      } else {
        money = '<div class="v3big v4lock' + (o.state === 'paid' ? ' paid' : '') + '"><div><span>' + (o.state === 'paid' ? 'Paid to you' : 'Locked for you') + '</span><b>' + v4n(o.amount) + '<small>' + cur + '</small></b></div>' +
          '<em>' + (o.state === 'paid' ? 'in your Cymetica credit' : ic('lock') + 'from the owner\'s credit · yours after 3 days up') + '</em></div>';
      }
      if (o.state === 'approved') tail = '<div class="v4post"><div class="v4do"><span class="no">1</span><div><b>Post it from @' + esc(o.handle) + '</b><span>the account you took it with · the text and the link are ready</span></div>' +
          '<a class="btn g" href="' + esc(v4intent(b)) + '" target="_blank" rel="noopener">' + ic('x') + 'Open in X ↗</a></div>' +
        '<div class="v4do"><span class="no">2</span><div><b>Paste the link of your post</b><span>the 3 days start now</span></div></div>' +
        '<div class="own"><input class="in" id="v4purl" placeholder="https://x.com/…/status/…"><button class="btn c" data-v4post="' + b.id + '">Register post</button></div><div class="dim num" style="font-size:11.5px" id="v4pmsg"></div>' +
        '<button class="btn gh sm v4quiet" data-v4pass="' + pair + '" data-v4was="approved">Pass on it · unlock the amount</button></div>';
      if (o.state === 'posted') tail = '<div class="v4days"><span class="' + (o.days_up >= 1 ? 'on' : '') + '"></span><span class="' + (o.days_up >= 2 ? 'on' : '') + '"></span><span class="' + (o.days_up >= 3 ? 'on' : '') + '"></span></div><div class="v3obnote" style="margin:6px 0 0">Day ' + Math.min(3, o.days_up + 1) + ' of 3 · keep the post up; after the third day the owner approves and it is yours. <a class="lnk" href="' + esc(o.post_url) + '" target="_blank" rel="noopener">your post ↗</a></div>';
      if (o.state === 'earned') tail = '<div class="v4days"><span class="on"></span><span class="on"></span><span class="on"></span></div><div class="v3done pos">' + ic('check') + 'It stayed up 3 days · waiting for the owner\'s approval</div>';
      if (o.state === 'paid') tail = '<div class="v3done pos">' + ic('coin') + 'Paid · ' + v4n(o.amount) + ' ' + cur + ' moved to your Cymetica credit</div>';
      return '<div class="v3ob">' + head + who(o) + money + v4steps(o) + tail + '</div>';
    }
    return '<div class="v3ob">' + head +
      (SIGNED ? '<div class="v3obin"><span>@</span><input class="in" id="v4h" placeholder="your X handle" autocomplete="off" maxlength="40" value="' + esc(S.v4chk[b.id + ':h'] || '') + '">' +
          '<button class="btn g" data-v4send="' + b.id + '">Take this brief ' + ic('arrow') + '</button></div>' +
          (err ? '<div class="v3not">' + ic('close') + '<span>' + esc(err) + '</span></div>' : '') :
        '<a class="btn g lg full" href="' + esc(signInHref(location.pathname + '#brief/' + b.id)) + '">Sign in to take this brief ' + ic('arrow') + '</a>') +
      '<div class="v3obnote">Your request goes to the owner. They look at your X and send you an amount; you accept it or not. After your post has stayed up 3 days, it is yours.</div></div>';
  }

  /* ---------- the owner's brief page ---------- */
  function ownerBrief(id) {
    const RU = resultsUrl(id);
    if (!need([RU, HOW])) return dash('products', waitIn('the brief'));
    const r = api(RU); if (!r || !r.brief || STATE[RU] === 'err') return dash('products', '<div class="card"><div class="empty"><b>This brief is not yours, or it does not exist.</b><a class="btn c sm" href="#me/products">My products</a></div></div>');
    const b = r.brief, cur = b.currency, O = r.offers || [], held = O.filter((o) => ['offered', 'approved', 'posted', 'earned'].indexOf(o.state) >= 0), cr = b.credit || { free: 0, locked: 0 };
    learn(b.path, b.preview_url, b.art);
    const open = b.status === 'open', closed = b.status === 'cancelled';
    const chipTxt = open ? '<i class="live"></i>Open · no end date' : closed ? 'Cancelled' : b.status === 'full' ? 'All handed out · add funds to open it again' : esc(b.status);
    const big = (n) => '<span class="pos">' + v4n(n) + '</span><small>' + esc(cur) + '</small>';
    const inner = '<div class="ph"><a class="back" href="#me/products">' + ic('arrow') + 'My products</a></div>' +
      '<div class="card bdhead"><img alt="" src="' + esc(v3pic(b) || b.art) + '"><div><h1>' + esc(shortName(b.name)) + '</h1><div class="meta">' +
          '<span class="chip ' + (open ? 'g' : '') + '">' + chipTxt + '</span>' +
          '<span class="chip g tipd" data-tip="' + esc(PAGE().products_note) + '">' + ic('shield') + 'Covered by your credit</span></div>' +
          (b.say_line ? '<div class="dim" style="margin-top:8px;font-size:13px">“' + esc(b.say_line) + '”</div>' : '') +
          '<div class="dim num" style="font-size:11.5px;margin-top:8px" id="act-msg">' + esc(S.actMsg || '') + '</div></div>' +
        '<div class="acts">' + (closed ? '' : '<button class="btn sm g" data-v4addopen="1">' + ic('plus') + 'Add funds</button><button class="btn sm" data-bact="cancel" data-id="' + b.id + '">' + ic('close') + 'Cancel the brief</button>') +
          '<button class="btn sm c" data-copytext="' + esc(location.origin + '/promo-market#brief/' + b.id) + '">' + ic('link') + 'Share</button></div></div>' +
      '<div class="tiles" style="--n:4">' +
        tile('wallet', 'Budget', big(b.budget), closed ? 'the brief is ended' : 'add funds any time', 'rgb(0,207,255)') +
        // an ended brief does not say "left": that read as money held for you; what was not handed out was never locked
        tile('coin', open ? 'Left to hand out' : closed ? 'Free in your credit again' : 'Left to hand out', big(b.left), open ? 'on the market now · not locked' : closed ? 'it was never locked' : 'add funds to open it again', 'rgb(0,255,136)') +
        tile('lock', 'Locked', big(b.locked), fmt(held.length) + ' promoter' + (held.length === 1 ? '' : 's') + ' · moves when you approve', 'rgb(0,207,255)', 'Locked from your Cymetica credit when you sent a promoter an offer. It moves to them when you approve their post after 3 days up, and is unlocked if they say no or pass') +
        tile('briefs', 'Paid', big(b.paid), 'moved to promoters', 'rgb(59,130,246)') + '</div>' +
      '<div class="note v4credit">' + ic('wallet') + '<span>Your Cymetica credit: <b>' + v4n(cr.free) + ' ' + esc(cur) + '</b> free · <b>' + v4n(cr.locked) + ' ' + esc(cur) + '</b> locked</span></div>' +
      (S.v4add && !closed ? v4addBox(b) : '') +
      v3Offers(b, r) + (S.v4pay ? v4payBox(b, r) : '') + v3Promoters(b, r);
    return dash('products', inner);
  }
  /* Add funds: the brief gets more to hand out, from the owner's free credit */
  function v4addBox(b) {
    const cur = esc(b.currency), room = Math.max(0, (b.credit || {}).free - b.left);
    return '<div class="card pad v4add" id="v4addbox"><div class="ch" style="margin:0"><h3>Add funds to this brief</h3><span class="sp"></span><span class="dim num" style="font-size:12px">your free credit covers ' + v4n(room) + ' ' + cur + ' more</span></div>' +
      '<div class="v4addrow"><div class="v3amt v4big"><input class="in" id="v4addamt" inputmode="decimal" value="' + V4_ADD[b.currency][0] + '" aria-label="Amount to add in ' + cur + '"><i>' + cur + '</i></div>' +
        '<div class="quick">' + V4_ADD[b.currency].map((v) => '<button data-v4addq="' + v + '">+ ' + v4n(v) + '</button>').join('') + '</div>' +
        '<button class="btn g lg" data-v4add="' + b.id + '">' + ic('plus') + 'Add to the brief</button><button class="btn gh" data-v4addclose="1">Cancel</button></div>' +
      '<div class="dim num" style="font-size:12px" id="v4addmsg">Nothing is locked by adding: it only raises what you can hand out.</div></div>';
  }
  function v3Offers(b, r) {
    const W = (r.offers || []).filter((o) => o.state === 'pending'), F = r.filtered_out || [], nf = F.reduce((s, f) => s + f[1], 0), cur = esc(b.currency);
    return '<div class="card v3offers" id="v3offers"><div class="tbar"><h3>Promoters who want this brief</h3>' + (W.length ? '<span class="chip g"><i class="live"></i>' + W.length + ' waiting for you</span>' : '') +
        '<span class="sp" style="flex:1"></span>' + (nf ? '<span class="chip r tipr" data-tip="' + esc(F.map((f) => f[1] + ' × ' + f[0]).join(' · ')) + '">' + ic('shield') + nf + ' filtered out by Cymetica</span>' : '') + '</div>' +
      (W.length ? '<div class="tscroll"><table class="tbl v3tbl"><thead><tr><th>Promoter</th><th class="n">Followers</th><th class="n">Views a post</th><th class="n">Real audience</th><th class="n">Expected reach</th><th class="n">You offer</th><th></th></tr></thead><tbody>' +
        W.map((o) => '<tr class="v3wait"><td><span class="v3pm"><span class="v3av">' + esc(o.handle[0].toUpperCase()) + '</span><span><b>@' + esc(o.handle) + '</b><small>applied ' + esc(o.applied) + ' · on X ' + esc(o.age) + '</small>' +
            '<a class="lnk v4x" href="https://x.com/' + esc(o.handle) + '" target="_blank" rel="noopener">' + ic('x') + 'check on X ↗</a></span></span></td>' +
          '<td class="n">' + fmt(o.followers) + '</td><td class="n">' + fmt(o.views) + '</td><td class="n">' + o.real + ' %</td>' +
          '<td class="n v4reach"><b>' + v4n(o.reach_lo) + '–' + v4n(o.reach_hi) + '</b><small>real views</small></td>' +
          '<td class="n"><div class="v3amt v4give"><input class="in" id="v4a-' + o.id + '" inputmode="decimal" value="' + o.suggest + '" aria-label="Amount to offer in ' + cur + '"><i>' + cur + '</i></div>' +
            '<small class="v4sug tipl" data-tip="Expected reach × ' + v4n(o.rate) + ' ' + cur + ' per 1,000 real views, never above what the brief has left. Change it as you like">' + ic('check') + 'suggested ' + v4n(o.suggest) + '</small></td>' +
          '<td class="v3act"><button class="btn g sm" data-v4award="' + b.id + ':' + o.id + '">' + ic('lock') + 'Send offer</button><button class="btn gh sm v3x" data-v4no="' + b.id + ':' + o.id + '" aria-label="Decline" data-tip="Decline">' + ic('close') + '</button></td></tr>').join('') + '</tbody></table></div>' :
        '<div class="empty" style="padding:22px"><span>No promoter is waiting for you.</span></div>') +
      '<div class="v3foot">' + ic('x') + '<span>Check the account on X, then send your amount: the suggestion comes from the reach a post of theirs is expected to get. It is locked from your credit while the offer is out; the promoter accepts it or not. It moves to them only when you approve their post after 3 days up.</span></div></div>';
  }
  function v3Promoters(b, r) {
    const rows = (r.offers || []).filter((o) => o.state !== 'pending'), cur = esc(b.currency), pair = (o) => b.id + ':' + o.id;
    return '<div class="card v3prom" id="v4prom"><div class="tbar"><h3 style="margin:0;font:17px var(--display)">Your offers</h3><span class="chip">' + rows.length + '</span></div>' +
      (rows.length ? '<div class="tscroll"><table class="tbl v3tbl"><thead><tr><th>Promoter</th><th class="n">Amount</th><th>Where it stands</th><th>Post</th><th></th></tr></thead><tbody>' +
        rows.map((o) => '<tr><td><span class="v3pm"><span class="v3av">' + esc(o.handle[0].toUpperCase()) + '</span><span><b>@' + esc(o.handle) + '</b><small>' + fmt(o.followers) + ' followers · on X ' + esc(o.age) + '</small></span></span></td>' +
          '<td class="n"><b class="v3of" style="font-size:15px">' + v4n(o.amount) + '</b> <small class="dim">' + cur + '</small><br><small class="dim">' + (o.state === 'paid' ? 'paid' : ic('lock') + 'locked') + '</small></td>' +
          '<td>' + v4chip(o, true) + '</td><td>' + (o.post_url ? '<a class="lnk" href="' + esc(o.post_url) + '" target="_blank" rel="noopener">post ↗</a>' : '<span class="dim">—</span>') + '</td>' +
          '<td class="v3act">' + (o.state === 'earned' ? '<button class="btn sm g" data-v4pay="' + pair(o) + '">' + ic('check') + 'Approve</button>' :
            o.state === 'approved' || o.state === 'offered' ? '<button class="btn sm gh" data-v4no="' + pair(o) + '" data-v4back="1" data-tip="' + (o.state === 'offered' ? 'No answer yet' : 'No post yet') + ': take it back and unlock the amount">Take back</button>' : '') + '</td></tr>').join('') + '</tbody></table></div>' :
        '<div class="empty"><b>No offer sent yet</b>' + (b.status === 'cancelled' ? '<span>The brief is ended. ' + v4n(b.left) + ' ' + cur + ' is free in your credit again.</span>' :
          b.status === 'open' ? '<span>It is on the market now, with ' + v4n(b.left) + ' ' + cur + ' to hand out.</span><a class="btn c sm" href="#market" style="margin-top:6px">See it on the market</a>' : '') + '</div>') + '</div>';
  }
  /* the owner's Approve: what was checked, what moves, from where to where; nothing moves until the owner confirms */
  function v4payBox(b, r) {
    const o = (r.offers || []).find((x) => x.id === S.v4pay.oid); if (!o || o.state !== 'earned') return '';
    const ok = (t) => '<div class="v4ck">' + ic('check') + '<span>' + t + '</span></div>';
    return '<div class="card pad v4appr" id="payouts"><div class="ch" style="margin:0"><h3>Approve and pay @' + esc(o.handle) + '</h3><span class="sp"></span><a class="btn sm" href="' + esc(o.post_url) + '" target="_blank" rel="noopener">' + ic('x') + 'See the post ↗</a></div>' +
      '<div class="v4cks">' + ok('The post is up now') + ok('Posted from @' + esc(o.handle) + ', the account that took the brief') + ok('It stayed up 3 of 3 days') + '</div>' +
      '<div class="statusrow" role="dialog" aria-label="Approve and pay" style="border-color:rgba(0,255,136,.35)">' + ic('lock') +
        '<span class="grow"><b class="pos">' + v4n(o.amount) + ' ' + esc(b.currency) + '</b> moves from your locked credit to @' + esc(o.handle) + '\'s Cymetica credit. It cannot be taken back.</span>' +
        '<button class="btn g" data-v4payok="1">' + ic('check') + 'Approve · release ' + v4n(o.amount) + ' ' + esc(b.currency) + '</button><button class="btn gh sm" data-v4paycancel="1">Not yet</button></div></div>';
  }

  /* ---------- the owner's other pages: My products, and the promoter's Briefs I took ---------- */
  function products() {
    const M = api(MINE).products, prods = M.products || [], C = api(MINE).credit || {};
    if (!prods.length) return '<div class="card"><div class="empty">' + holo(46) + '<b>No app of yours yet</b><span>Build an app with Build it Better: once it ships, it is listed here and you can post a brief for it.</span>' +
      '<a class="btn g" href="/build-it-better" style="margin-top:8px">Open Build it Better ' + ic('arrow') + '</a></div></div>';
    const rs = prods.map((p) => p.brief).filter(Boolean), by = {};
    rs.forEach((r) => { const c = r.brief.currency; (by[c] = by[c] || { left: 0, paid: 0 }); by[c].left += r.brief.status === 'open' ? r.brief.left : 0; by[c].paid += r.brief.paid; });
    const sumBy = (k) => Object.keys(by).length ? Object.keys(by).map((c) => '<span class="pos">' + v4n(by[c][k]) + '</span><small>' + esc(c) + '</small>').join(' ') : '<span class="pos">0</span>';
    const waiting = sum(rs, (r) => (r.offers || []).filter((o) => o.state === 'pending').length);
    const credit = Object.keys(C).map((c) => '<b>' + v4n(C[c].free) + ' ' + esc(c) + '</b> free' + (C[c].locked ? ' · <b>' + v4n(C[c].locked) + ' ' + esc(c) + '</b> locked' : '')).join(' &nbsp;·&nbsp; ');
    return '<div class="tiles" style="--n:3">' +
        tile('coin', 'Left in your briefs', sumBy('left'), fmt(M.live_briefs) + ' live brief' + (M.live_briefs === 1 ? '' : 's'), 'rgb(0,255,136)') +
        tile('briefs', 'Promoters waiting', fmt(waiting), 'for your answer') +
        tile('wallet', 'Paid', sumBy('paid'), 'moved to promoters', 'rgb(0,207,255)') + '</div>' +
      (credit ? '<div class="note v4credit">' + ic('wallet') + '<span>Your Cymetica credit: ' + credit + '</span></div>' : '') +
      '<div class="grid4">' + prods.map(productCard).join('') + '</div>' +
      '<div class="note">' + ic('lock') + '<span>' + esc(PAGE().products_note) + '</span></div>';
  }
  function productCard(p) {
    const r = p.brief, b = r && r.brief, live = b && b.status !== 'cancelled', w = r ? (r.offers || []).filter((o) => o.state === 'pending').length : 0;
    return '<article class="pc" data-product="' + esc(p.path) + '"><div class="img">' + (p.preview_url || !p.site ? '<img alt="" src="' + esc(p.site ? p.preview_url : pic(p.path)) + '">' : '<div class="v3noimg">' + ic('globe') + '</div>') +
        (b ? '<div class="tl"><span class="chip ' + (b.status === 'open' ? 'g' : '') + '">' + (b.status === 'open' ? '<i class="live"></i>Open' : esc(b.status)) + '</span></div>' : '') + '</div>' +
      '<div class="bd"><div class="nm"><b title="' + esc(p.name) + '">' + esc(shortName(p.name)) + '</b></div>' + v3where({ url: p.url, site: p.site, path: p.path }) +
        (b ? '<div class="r3"><div><b class="pos">' + v4n(b.left) + '</b><span>' + esc(b.currency) + (b.status === 'cancelled' ? ' free again' : ' left') + '</span></div><div><b' + (w ? ' class="pos"' : '') + '>' + fmt(w) + '</b><span>waiting</span></div></div>' +
          '<a class="btn sm full' + (w ? ' g' : '') + '" href="#mybrief/' + b.id + '">' + (w ? 'Answer ' + w + ' promoter' + (w === 1 ? '' : 's') : 'Open the brief') + ' ' + ic('arrow') + '</a>' + (live ? '' : '<a class="btn g sm full" href="#new' + esc(p.site ? '/' + V3_SITE : p.path) + '">' + ic('plus') + 'Create brief</a>') :
          '<div class="nob">No brief yet</div><a class="btn g sm full" href="#new' + esc(p.site ? '/' + V3_SITE : p.path) + '">' + ic('plus') + 'Create brief</a>') +
      '</div></article>';
  }
  function taken() {
    const list = v4takes(), by = (states) => { const m = {}; list.filter((t) => states.indexOf(t.offer.state) >= 0).forEach((t) => { m[t.offer.currency] = (m[t.offer.currency] || 0) + t.offer.amount; });
      return Object.keys(m).length ? Object.keys(m).map((c) => '<span class="pos">' + v4n(m[c]) + '</span><small>' + esc(c) + '</small>').join(' ') : '<span class="pos">0</span>'; };
    return '<div class="tiles" style="--n:3">' + tile('briefs', 'Briefs taken', fmt(list.filter((t) => t.offer.state !== 'declined').length), '') +
        tile('lock', 'Locked for you', by(['offered', 'approved', 'posted', 'earned']), 'yours after 3 days up', 'rgb(0,207,255)') +
        tile('coin', 'Paid', by(['paid']), 'in your Cymetica credit', 'rgb(0,255,136)') + '</div>' +
      (list.length ? '<div class="card"><table class="tbl"><thead><tr><th>Brief</th><th class="n">Amount</th><th>Where it stands</th><th>Post</th></tr></thead><tbody>' +
          list.map((t) => { const b = t.brief || {}, o = t.offer;
            return '<tr data-brief="' + b.id + '"><td><div class="tw" style="gap:12px"><img alt="" src="' + esc(pic(b.path)) + '" style="width:64px;height:36px;border-radius:7px;object-fit:cover"><span class="ttl">' + esc(shortName(b.name)) + '<small>as @' + esc(o.handle) + '</small></span></div></td>' +
            '<td class="n pos">' + (o.amount != null ? v4n(o.amount) + ' <small>' + esc(o.currency) + '</small>' : '<small class="dim">the owner sends it</small>') + '</td>' +
            '<td>' + v4chip(o, false) + '</td><td>' + (o.post_url ? '<a class="lnk" href="' + esc(o.post_url) + '" target="_blank" rel="noopener">post ↗</a>' : '<span class="dim">—</span>') + '</td></tr>'; }).join('') + '</tbody></table></div>' :
        '<div class="card"><div class="empty">' + holo(46) + '<b>No brief taken yet</b><span>' + esc(PAGE().taken_empty) + '</span><a class="btn g" href="#market" style="margin-top:8px">See open briefs ' + ic('arrow') + '</a></div></div>') +
      '<div class="note">' + ic('lock') + '<span>' + esc(PAGE().taken_pay) + '</span></div>';
  }

  /* ---------- the clicks of v4 ---------- */
  function v4call(path, body, btn) { return send('POST', path, body, btn); }
  /* Cancel the brief ends it for good: the first click asks, the second does it (their briefAct runs on the second) */
  document.addEventListener('click', (e) => {
    const t = e.target.closest('[data-bact="cancel"]'); if (!t || t.dataset.v4sure) return;
    e.preventDefault(); e.stopPropagation();
    const was = t.innerHTML; t.dataset.v4sure = '1'; t.classList.add('v4sure'); t.innerHTML = ic('close') + 'End it for good? Click again';
    setTimeout(() => { if (t.isConnected) { delete t.dataset.v4sure; t.classList.remove('v4sure'); t.innerHTML = was; } }, 4000);
  }, true);
  /* Open briefs in the menu lands on the briefs, not on the market's headline above them */
  document.addEventListener('click', (e) => {
    if (e.target.closest('.rnav a.v4open, .v4earn a[href="#market"]')) setTimeout(() => { const c = document.querySelector('article.bc'); if (c) c.scrollIntoView({ behavior: 'smooth', block: 'center' }); }, 450);
  });
  document.addEventListener('keydown', (e) => { if (e.key === 'Enter' && e.target.id === 'v4h') { const b = document.querySelector('[data-v4send]'); if (b) b.click(); } });
  document.addEventListener('input', (e) => {
    const t = e.target;
    if (t.id === 'v4budget' && S.form) { const q = $('v4eq'); if (q) q.innerHTML = v4eq(S.form.budget, S.form.cur); return; }
    if (/^v4/.test(t.id || '')) t.dataset.v4dirty = '1';
  });
  document.addEventListener('click', (e) => {
    const t = e.target.closest('[data-v4cur],[data-v4amt],[data-v4send],[data-v4yes],[data-v4pass],[data-v4award],[data-v4no],[data-v4post],[data-v4pay],[data-v4payok],[data-v4paycancel],[data-v4addopen],[data-v4addclose],[data-v4addq],[data-v4add],[data-v4go],[data-v4x]'); if (!t) return;
    const d = t.dataset;
    if (d.v4go || d.v4x) return v4popClick(d);
    if (d.v4cur) { S.form = Object.assign(defaultForm(S.form && S.form.path), { cur: d.v4cur }); S.form.budget = V4_DEF[d.v4cur]; return rerender(); }
    if (d.v4amt) { e.preventDefault(); S.form.budget = +d.v4amt; return rerender(); }
    if (d.v4send) {
      const id = +d.v4send, h = (($('v4h') || {}).value || '').trim().replace(/^@/, ''); if (!h) { if ($('v4h')) $('v4h').focus(); return; }
      return v4call('/api/v1/promo/briefs/' + id + '/offer/take', { handle: h }, t).then((r) => {
        if (!r.ok) { S.v4chk[id + ':err'] = msgOf(r.j); S.v4chk[id + ':h'] = h; return openBrief(id, true); }
        S.v4o[id] = r.j; delete S.v4chk[id + ':err']; delete S.v4chk[id + ':h']; toast('Sent to the owner · you hear here when they send an amount'); load(MINE, true); openBrief(id, true);
      });
    }
    if (d.v4yes) {
      const [bid, oid] = v4hash(d.v4yes);
      return v4call('/api/v1/promo/briefs/' + bid + '/offers/' + oid + '/accept', {}, t).then((r) => {
        if (!r.ok) return toast(msgOf(r.j));
        v4popDone(oid); S.v4o[+bid] = r.j; toast('Accepted · ' + v4n(r.j.amount) + ' ' + r.j.currency + ' is locked for you · post it'); load(MINE, true); load(BRIEFS, true); openBrief(+bid, true);
      });
    }
    if (d.v4pass) {
      const [bid, oid] = v4hash(d.v4pass);
      return v4call('/api/v1/promo/briefs/' + bid + '/offers/' + oid + '/pass', {}, t).then((r) => {
        if (!r.ok) return toast(msgOf(r.j));
        v4popDone(oid); S.v4o[+bid] = null;
        toast(({ pending: 'Request withdrawn', offered: 'You said no' }[d.v4was] || 'You passed on it') + ' · the brief is open for you again'); load(MINE, true); load(BRIEFS, true); openBrief(+bid, true);
      });
    }
    if (d.v4award || d.v4no) {
      const [bid, oid] = v4hash(d.v4award || d.v4no), body = d.v4no ? { decision: 'decline' } : { decision: 'accept', amount: parseFloat(($('v4a-' + oid) || {}).value) };
      return v4call('/api/v1/promo/briefs/' + bid + '/offers/' + oid, body, t).then((r) => {
        if (!r.ok) return toast(msgOf(r.j));
        v4popDone(oid);
        toast(d.v4back ? 'Taken back · ' + v4n(r.j.amount) + ' ' + r.j.currency + ' is unlocked' : d.v4no ? 'Declined' : 'Offer of ' + v4n(r.j.amount) + ' ' + r.j.currency + ' sent to @' + r.j.handle + ' · locked until they answer');
        v4after(bid);
      });
    }
    if (d.v4post) {
      const id = +d.v4post, url = (($('v4purl') || {}).value || '').trim(); if (!url) { if ($('v4purl')) $('v4purl').focus(); return; }
      return v4call('/api/v1/promo/briefs/' + id + '/posts', { url: url }, t).then((r) => {
        if (!r.ok) { const m = $('v4pmsg'); if (m) m.textContent = msgOf(r.j); return; }
        v4popDone(r.j.id); S.v4o[id] = r.j; toast('Post registered · yours after 3 days up'); load(MINE, true); openBrief(id, true);
      });
    }
    if (d.v4pay) { const [bid, oid] = v4hash(d.v4pay); S.v4pay = { bid: +bid, oid: +oid }; rerender(); return setTimeout(() => { const n = $('payouts'); if (n) n.scrollIntoView({ behavior: 'smooth', block: 'center' }); }, 60); }
    if (d.v4paycancel) { S.v4pay = null; return rerender(); }
    if (d.v4payok) {
      const p = S.v4pay;
      return v4call('/api/v1/promo/briefs/' + p.bid + '/offers/' + p.oid + '/pay', {}, t).then((r) => {
        if (r.ok) v4popDone(p.oid); S.v4pay = null; toast(r.ok ? 'Approved · ' + v4n(r.j.amount) + ' ' + r.j.currency + ' moved to @' + r.j.handle : msgOf(r.j)); v4after(p.bid);
      });
    }
    if (d.v4addopen) { S.v4add = true; rerender(); return setTimeout(() => { const n = $('v4addamt'); if (n) { n.focus(); n.select(); } }, 60); }
    if (d.v4addclose) { S.v4add = false; return rerender(); }
    if (d.v4addq) { const n = $('v4addamt'); if (n) { n.value = d.v4addq; n.dataset.v4dirty = '1'; } return; }
    if (d.v4add) {
      const bid = +d.v4add, amount = parseFloat(($('v4addamt') || {}).value);
      return send('PATCH', '/api/v1/promo/briefs/' + bid, { action: 'add_budget', amount: amount }, t).then((r) => {
        if (!r.ok) { const m = $('v4addmsg'); if (m) { m.textContent = msgOf(r.j); m.classList.add('neg'); } return; }
        S.v4add = false; toast('Added ' + v4n(amount) + ' ' + r.j.currency + ' · ' + v4n(r.j.left) + ' ' + r.j.currency + ' to hand out'); v4after(bid);
      });
    }
  });

  /* ---------- the two windows: what the other side did shows here by itself, and pops up ---------- */
  const V4_KEY = 'v4:' + V4_ROLE;
  const v4store = (k, v) => { try { if (v === undefined) return JSON.parse(sessionStorage.getItem(V4_KEY + k)); sessionStorage.setItem(V4_KEY + k, JSON.stringify(v)); } catch (e) { /* private window */ } return null; };
  let v4ver = null, v4since = v4store('since'), v4pops = v4store('pops') || [];
  function v4popDraw() {
    let box = $('v4pop');
    if (!box) { box = document.createElement('div'); box.id = 'v4pop'; box.setAttribute('role', 'status'); box.setAttribute('aria-live', 'polite'); document.body.appendChild(box); }
    box.innerHTML = v4pops.slice(-3).map((p) => '<div class="v4n"><span class="v4ni">' + ic(V4_OWNER ? 'users' : 'coin') + '</span><div><b>' + esc(p.text) + '</b><small>' + (V4_OWNER ? 'your brief' : 'from the owner') + ' · just now</small></div>' +
      '<button class="btn g sm" data-v4go="' + p.n + '">' + esc(p.go) + ' ' + ic('arrow') + '</button><button class="x" data-v4x="' + p.n + '" aria-label="Dismiss">' + ic('close') + '</button></div>').join('');
  }
  /* answered here: what popped up about that offer has done its job */
  function v4popDone(oid) { const n = v4pops.length; v4pops = v4pops.filter((x) => x.offer !== +oid); if (v4pops.length !== n) { v4store('pops', v4pops); v4popDraw(); } }
  function v4popClick(d) {
    const n = +(d.v4go || d.v4x), p = v4pops.find((x) => x.n === n);
    v4pops = v4pops.filter((x) => x.n !== n); v4store('pops', v4pops); v4popDraw();
    if (!d.v4go || !p || !p.brief) return;
    const to = (V4_OWNER ? '#mybrief/' : '#brief/') + p.brief;
    if (location.hash === to) route(false); else location.hash = to;
    if (V4_OWNER) setTimeout(() => { const o = $(p.go === 'Review' ? 'v3offers' : 'v4prom'); if (o) o.scrollIntoView({ behavior: 'smooth', block: 'start' }); }, 400);
  }
  /* read again what the other window may have changed */
  function v4fresh() {
    load(MINE, true); load(BRIEFS, true);
    const h = hashOf().split('/');
    if (h[0] === 'mybrief') load(resultsUrl(+h[1]), true);
    if (V4_OWNER || !SIGNED) return;
    const ids = {}; v4open().forEach((b) => { ids[b.id] = 1; }); v4takes().forEach((t) => { if (t.brief) ids[t.brief.id] = 1; }); Object.keys(S.v4o).forEach((k) => { ids[k] = 1; });
    Object.keys(ids).forEach((k) => { const id = +k;
      send('GET', '/api/v1/promo/briefs/' + id).then((r) => {
        const on = $('drawer').querySelector('[data-v4brief="' + id + '"]') && $('drawer').classList.contains('on');
        if (!r.ok) { delete S.v4o[id]; delete S.v4chk[id]; if (on) hide(); return rerender(); }
        const sig = (o, b) => JSON.stringify([o, b && b.left, b && b.status]), old = findBrief(id), was = sig(v4mine(id), old);
        S.v4o[id] = r.j.my_offer || null; if (!old || (S.detail && S.detail.brief && S.detail.brief.id === id)) S.detail = r.j;
        if (sig(S.v4o[id], r.j.brief) === was) return;
        rerender(); if (on) v4keep(() => openBrief(id, true));
      });
    });
  }
  function v4poll() {
    fetch('/__v4/state?since=' + (v4since == null ? 1e9 : v4since), { headers: { Accept: 'application/json' } }).then((r) => r.json()).then((s) => {
      const day = $('v4day'); if (day) day.textContent = 'day +' + Math.round(s.offset * 10) / 10;
      if (v4since == null) v4since = s.last;                                   // a first look: only what happens from now on
      else if (s.last < v4since) { v4since = 0; v4pops = []; v4store('pops', v4pops); v4popDraw(); }   // the sample was reset
      (s.news || []).forEach((p) => { if (p.n > v4since) { v4since = p.n; v4pops = v4pops.filter((x) => x.offer !== p.offer); v4pops.push(p); } });
      if ((s.news || []).length) { v4store('pops', v4pops); v4popDraw(); }
      v4store('since', v4since);
      if (v4ver !== null && s.ver !== v4ver) v4fresh();
      v4ver = s.ver;
    }).catch(() => { /* the mock's server is not there: the page stays as it is */ });
  }
  v4popDraw(); v4poll(); setInterval(v4poll, 1500);
