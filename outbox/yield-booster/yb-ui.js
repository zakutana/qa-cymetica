/* Yield Booster views. Every figure comes from YB (yb-core.js): the cards from YB.card, the dollars from YB.result,
   the finder's rows from YB.find, the pipes from the route YB.find picked. Nothing here computes a return.
   ?step=1..4 &tier= &amount= &move= open a state; &shot=1 freezes it at its end; ?logo=1 shows the mark large. */
(function () {
  const D = window.YB_DATA, Y = window.YB;
  const q = new URLSearchParams(location.search);
  const S = {step: 1, tier: q.get('tier'), s: Y.MOVES.includes(+q.get('move')) ? +q.get('move') : 0.2,
    amount: q.has('amount') ? +q.get('amount') : 5000, started: false};
  const shot = q.has('shot');
  if (shot) document.body.classList.add('shot');
  const $ = id => document.getElementById(id);
  const timers = [];
  const later = (ms, f) => timers.push(setTimeout(f, shot ? 0 : ms));
  const stopTimers = () => { while (timers.length) clearTimeout(timers.pop()); };

  /* ---------- formats ---------- */
  const fx = v => '×' + (Math.abs(v - 1) < 0.1 ? v.toFixed(3) : v.toFixed(2));
  const fp = v => {
    const p = (v - 1) * 100, a = Math.abs(p);
    return (p < 0 ? '−' : '+') + (a < 1 ? a.toFixed(2) : a < 10 ? a.toFixed(1) : a.toFixed(0)) + '%';
  };
  const usd = v => {
    const a = Math.abs(v);
    return (v < 0 ? '−' : '+') + '$' + (a < 100 ? a.toFixed(2) : Math.round(a).toLocaleString('en-US'));
  };
  const num = v => Math.round(v).toLocaleString('en-US');
  const yr = r => r.toFixed(2) + '% / yr';
  const tierOf = id => Y.TIERS.find(t => t.id === id);
  const idx = id => Y.TIERS.findIndex(t => t.id === id);
  const pname = p => D.protocols[p].name;
  const icon = p => `https://icons.llamao.fi/icons/protocols/${D.protocols[p].icon}?w=96`;
  const when = iso => {
    const d = new Date(iso.replace('Z', ':00Z'));
    return d.toLocaleString('en-GB', {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'UTC'}) + ' UTC';
  };

  /* what a tier promises, said from its own rule */
  function say(t) {
    if (t.maxL === 1) return 'Stablecoins only. No leverage, no loss.';
    if (t.safeLiq && t.worst < 0.5) return `Loses at most ${t.worst * 100}% in a bad month. Never liquidated.`;
    if (t.safeLiq) return `Up to ${t.maxL}× leverage. Loses at most half.`;
    return `Up to ${t.maxL}× leverage. Can be liquidated.`;
  }
  const priced = c => c.asset === 'ETH' || c.asset === 'BTC';
  function labels(c) {
    const pc = Math.round(S.s * 100);
    return priced(c) ? [`if ${c.asset} +${pc}%`, `if ${c.asset} −${pc}%`] : ['rates hold', 'yields halve'];
  }
  function exposure(r) {
    if (r.type === 'vaults') return 'STABLECOINS ONLY';
    if (r.type === 'lp') return 'ETH/USDC POOL';
    if (r.type === 'stableloop') return r.L > 1 ? `sUSDe ${r.L}×` : 'sUSDe';
    return r.L > 1 ? `${r.asset} ${r.L}×` : `STAKED ${r.asset}`;
  }
  function chips(c, i) {
    const out = [`<span class="chip ${i === 3 ? 'r' : 'c'}">${exposure(c.route)}</span>`];
    out.push(c.liqDrop === null ? '<span class="chip g">NO LIQUIDATION</span>'
      : `<span class="chip ${i === 3 ? 'r' : 'm'}">LIQUIDATION AT ${c.asset} −${Math.round(c.liqDrop * 100)}%</span>`);
    return out;
  }
  function pair(c) {
    const [lu, ld] = labels(c);
    return `<div class="pair"><div class="up"><small>GOOD MONTH</small><b>${fx(c.up)}</b><span>${fp(c.up)}</span><small>${lu}</small></div>
      <div class="dn ${c.bad >= 1 ? 'flat' : ''}"><small>BAD MONTH</small><b>${fx(c.bad)}</b><span>${fp(c.bad)}</span><small>${ld}</small></div></div>`;
  }

  /* ---------- step 1 ---------- */
  function renderTiers() {
    $('moves').innerHTML = Y.MOVES.map(m => `<button data-move="${m}" class="${m === S.s ? 'on' : ''}">±${Math.round(m * 100)}%</button>`).join('');
    $('tiers').innerHTML = Y.TIERS.map((t, i) => {
      const c = Y.card(t.id, S.s);
      return `<button class="tier t${i} ${S.tier === t.id ? 'sel' : ''}" data-tier="${t.id}">
        <div class="top"><h3>${t.name}</h3><div class="bars">${[0, 1, 2, 3].map(k => `<i class="${k <= i ? 'on' : ''}"></i>`).join('')}</div></div>
        <div class="say">${say(t)}</div>${pair(c)}<div class="chips">${chips(c, i).join('')}</div></button>`;
    }).join('');
    $('foot1').innerHTML = `<span>Rates: <b>DefiLlama</b> · read <b>${when(D.fetched_at)}</b></span>
      <span><b>${num(D.scanned.pools)}</b> pools · <b>${D.scanned.protocols}</b> protocols · <b>${D.scanned.chains}</b> chains</span>
      <span class="tip" title="Each rate is the lowest of today's, the 7-day and the 30-day APY of a DefiLlama pool, so a one-day spike does not make the month. A month is (1 + APY) to the power 1/12. Liquidation is where a loop's debt reaches the market's LTV.">i</span>`;
  }

  /* ---------- step 2 ---------- */
  function monthBoxes(r) {
    const [lu, ld] = labels(r);
    return `<div class="up"><small>GOOD MONTH</small><b>${usd(r.upUsd)}</b><span>${fx(r.up)} · ${lu}</span></div>
      <div class="dn ${r.bad >= 1 ? 'flat' : ''}"><small>BAD MONTH</small><b>${usd(r.badUsd)}</b><span>${fx(r.bad)} · ${ld}</span></div>`;
  }
  function renderAmount() {
    const t = tierOf(S.tier), i = idx(S.tier), c = Y.card(S.tier, S.s);
    $('picked').className = `glass picked t${i}`;
    $('picked').innerHTML = `<div class="cap">YOUR RISK</div><h3>${t.name}</h3><div class="say">${say(t)}</div>${pair(c)}
      <div style="display:flex;flex-wrap:wrap;gap:6px">${chips(c, i).join('')}</div>
      <div style="margin-top:14px"><button class="link" data-go="1">Change</button></div>`;
    $('quick').innerHTML = [100, 1000, 10000, 50000].map(a => `<button data-amt="${a}" class="${a === S.amount ? 'on' : ''}">${num(a)}</button>`).join('');
    updateMonth();
  }
  function updateMonth() {
    const ok = S.amount > 0;
    $('month2').innerHTML = ok ? monthBoxes(Y.result(S.tier, S.s, S.amount)) : '';
    $('find').disabled = !ok;
    document.querySelectorAll('#quick button').forEach(b => b.classList.toggle('on', +b.dataset.amt === S.amount));
  }

  /* ---------- step 3: the finder ---------- */
  function radarSvg() {
    const ids = Object.keys(D.protocols), n = ids.length;
    const logos = ids.map((p, k) => {
      const a = (k / n) * Math.PI * 2 - Math.PI / 2, x = 200 + 152 * Math.cos(a), y = 200 + 152 * Math.sin(a);
      return `<g class="p" data-k="${k}"><clipPath id="rc${k}"><circle cx="${x}" cy="${y}" r="17"/></clipPath>
        <circle class="ring" cx="${x}" cy="${y}" r="21"/><text class="mono" x="${x}" y="${y}">${pname(p)[0]}</text>
        <image href="${icon(p)}" x="${x - 17}" y="${y - 17}" width="34" height="34" clip-path="url(#rc${k})"/>
        <title>${pname(p)}</title></g>`;
    }).join('');
    return `<svg viewBox="0 0 400 400">
      <defs><linearGradient id="sw" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#00ff88" stop-opacity="0"/><stop offset="1" stop-color="#00ff88" stop-opacity=".35"/></linearGradient></defs>
      ${[60, 110, 152, 188].map(r => `<circle cx="200" cy="200" r="${r}" fill="none" stroke="#1e3050" stroke-width="1"/>`).join('')}
      <path d="M200 12V388M12 200H388" stroke="#1e3050" stroke-width="1"/>
      <path class="sweep" d="M200 200L200 12A188 188 0 0 1 362.8 106Z" fill="url(#sw)"/>
      ${logos}
      <text x="200" y="196" text-anchor="middle" style="font:44px 'Archivo Black',sans-serif;fill:#e6edf7" id="rcount">0</text>
      <text x="200" y="224" text-anchor="middle" style="font:700 10px 'JetBrains Mono',monospace;letter-spacing:.2em;fill:#7f93ad">POOLS READ</text>
    </svg><div class="ticker" id="tick"></div>`;
  }
  function count(el, to, ms) {
    if (shot) { el.textContent = num(to); return; }
    const t0 = performance.now();
    const step = now => {
      const k = Math.min(1, (now - t0) / ms);
      el.textContent = num(to * (1 - Math.pow(1 - k, 3)));
      if (k < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }
  function rowHtml(r, kind) {
    const lab = r.type === 'vaults' ? r.steps.slice(1).map(s => `${s.title} (${s.chain})`).join(' · ') : r.label;
    const v = kind === 'best' ? '<span class="chip g">★ BEST</span>' : kind === 'fit' ? '<span class="chip c">✓ FITS</span>'
      : `<span class="chip r" style="letter-spacing:0">✗ ${r.reason}</span>`;
    return `<div class="rrow ${kind === 'no' ? 'no' : ''} ${kind === 'best' ? 'best' : ''}"><div class="lab" title="${lab}">${lab}</div>
      <div class="x u">${fx(r.up)}</div><div class="x d">${fx(r.bad)}</div><div class="v">${v}</div></div>`;
  }
  function runFinder() {
    stopTimers();
    const f = Y.find(S.tier, S.s), t = tierOf(S.tier);
    $('radar').className = 'glass radar';
    $('radar').innerHTML = radarSvg();
    $('counts').innerHTML = `<div><small>POOLS READ</small><b id="c1">0</b></div><div><small>ROUTES BUILT</small><b id="c2">0</b></div>
      <div class="fitn"><small>FIT ${t.name.toUpperCase()}</small><b id="c3">0</b></div>`;
    $('rows').innerHTML = '';
    $('found').className = 'found';
    const scan = 2400;
    count($('rcount'), D.scanned.pools, scan);
    count($('c1'), D.scanned.pools, scan);
    count($('c2'), f.built, scan + 400);
    count($('c3'), f.fit.length, scan + 800);
    const logos = [...document.querySelectorAll('#radar .p')];
    logos.forEach((g, k) => later(150 + (k / logos.length) * (scan - 300), () => g.classList.add('hit')));
    let ti = 0;
    const tick = () => {
      const r = D.ticker[ti++ % D.ticker.length];
      $('tick').innerHTML = `${pname(r[0])} · ${r[1]} · ${r[2]} · <b>${r[3]}%</b>`;
    };
    if (shot) tick(); else for (let k = 0; k < scan / 70; k++) later(k * 70, tick);
    // the most tempting route turned down for each reason, so the list shows why, not one reason five times
    const kinds = new Set(), rej = [];
    for (const r of f.rejected) {
      const kind = r.reason.replace(/[\d.%×−-]+/g, '#');
      if (!kinds.has(kind) && rej.length < 5) { kinds.add(kind); rej.push(r); }
    }
    const fits = f.fit.slice(1, 1 + (8 - rej.length)).reverse();
    const order = [...rej.map(r => [r, 'no']), ...fits.map(r => [r, 'fit']), [f.best, 'best']];
    order.forEach(([r, kind], k) => later(700 + k * 330, () => $('rows').insertAdjacentHTML('beforeend', rowHtml(r, kind))));
    const end = 700 + order.length * 330 + 200;
    later(end, () => {
      $('radar').classList.add('done');
      $('found').innerHTML = `<div class="lab"><small>BEST ROUTE FOR ${t.name.toUpperCase()}</small>${f.best.label}</div>
        <button class="go" data-go="4">SHOW THE ROUTE →</button>`;
      $('found').classList.add('on');
    });
    if (!shot) later(end + 1900, () => { if (S.step === 3) go(4); });
  }

  /* ---------- step 4: the route as pipes ---------- */
  const NW = 178, NH = 110;
  function nodeSvg(st, x, y, k, t) {
    const x0 = x - NW / 2, y0 = y - NH / 2, p = st.project;
    let act = st.title, rate = '', cls = 'earn';
    if (st.kind === 'swap') rate = 'swap';
    if (st.kind === 'stake') { act = `stake → ${st.title}`; rate = '+' + yr(st.rate); }
    if (st.kind === 'collateral') { act = 'deposit as collateral'; rate = st.rate > 0.01 ? '+' + yr(st.rate) : `max LTV ${Math.round(st.ltv * 100)}%`; }
    if (st.kind === 'borrow') { act = st.title.replace('Borrow', 'borrow'); rate = '−' + yr(st.rate); cls = 'pay'; }
    if (st.kind === 'vault') rate = '+' + yr(st.rate);
    if (st.kind === 'lp') { act = `pool ${st.title}`; rate = '+' + st.rate.toFixed(2) + '% fees / yr'; }
    if (rate === 'swap' || rate.startsWith('max')) cls = 'muted';
    return `<g class="node" data-n="${k}" style="--t:${t}"><rect class="card" x="${x0}" y="${y0}" width="${NW}" height="${NH}" rx="16"/>
      <clipPath id="nc${k}"><circle cx="${x0 + 30}" cy="${y0 + 30}" r="18"/></clipPath>
      <circle cx="${x0 + 30}" cy="${y0 + 30}" r="21" fill="#06090f" stroke="#1e3050"/>
      <text class="mono" x="${x0 + 30}" y="${y0 + 30}">${pname(p)[0]}</text>
      <image href="${icon(p)}" x="${x0 + 12}" y="${y0 + 12}" width="36" height="36" clip-path="url(#nc${k})"/>
      <text class="nm" x="${x0 + 60}" y="${y0 + 28}">${pname(p)}</text>
      <text class="ch" x="${x0 + 60}" y="${y0 + 45}">${st.chain.toUpperCase()}</text>
      <text class="ac" x="${x0 + 16}" y="${y0 + 76}">${act}</text>
      <text class="rt ${cls}" x="${x0 + 16}" y="${y0 + 96}" ${cls === 'muted' ? 'style="fill:#7f93ad"' : ''}>${rate}</text></g>`;
  }
  function sourceSvg(x, y) {
    return `<g class="node" data-n="src" style="--t:0s"><circle cx="${x}" cy="${y}" r="50" fill="#3b82f6" opacity=".16"/>
      <circle cx="${x}" cy="${y}" r="40" fill="#3b82f6" stroke="#00cfff" stroke-opacity=".5" stroke-width="2"/>
      <text class="mono" x="${x}" y="${y}" style="font-size:34px">$</text>
      <text x="${x}" y="${y + 76}" text-anchor="middle" style="font:20px 'Archivo Black',sans-serif;fill:#e6edf7">${num(S.amount)}</text>
      <text x="${x}" y="${y + 96}" text-anchor="middle" style="font:700 11px 'JetBrains Mono',monospace;letter-spacing:.16em;fill:#a9b8cc">USDC</text></g>`;
  }
  const curve = (x1, y1, x2, y2) => { const m = (x2 - x1) / 2; return `M${x1} ${y1}C${x1 + m} ${y1} ${x2 - m} ${y2} ${x2} ${y2}`; };

  /* positions and pipes for the four shapes a route can take */
  function layout(r) {
    const steps = r.steps.slice(1), nodes = [], pipes = [], extra = [];
    const TX = 1110, TW = 150, ty = 230;                         // the tank
    const src = {x: 100, y: 230};
    if (r.type === 'vaults') {
      steps.forEach((st, k) => nodes.push({st, x: 600, y: 95 + k * 135}));
      nodes.forEach((n, k) => pipes.push({d: curve(150, 230, n.x - NW / 2, n.y), from: 'src', to: k,
        label: Math.round(n.st.share * 100) + '%', lx: n.x - NW / 2 - 44, ly: n.y - 16}));
      nodes.forEach((n, k) => pipes.push({d: curve(n.x + NW / 2, n.y, TX - TW / 2, 200 + k * 30), from: k, to: 'tank'}));
    } else if (r.type === 'lp') {
      nodes.push({st: steps[0], x: 400, y: 112}, {st: steps[1], x: 760, y: 230});
      pipes.push({d: curve(150, 222, 400 - NW / 2, 112), from: 'src', to: 0, label: '50% → ETH', lx: 250, ly: 100});
      pipes.push({d: curve(400 + NW / 2, 112, 760 - NW / 2, 205), from: 0, to: 1});
      pipes.push({d: `M150 238C300 238 300 330 440 330S620 255 ${760 - NW / 2} 255`, from: 'src', to: 1, label: '50% USDC', lx: 440, ly: 306});
      pipes.push({d: `M${760 + NW / 2} 230L${TX - TW / 2} 230`, from: 1, to: 'tank'});
    } else {
      const main = steps.filter(s => s.kind !== 'borrow'), borrow = steps.find(s => s.kind === 'borrow');
      const y0 = borrow ? 150 : 230, xs = main.map((_, k) => main.length === 1 ? 560 : 330 + k * (560 / (main.length - 1)));
      src.y = y0;
      main.forEach((st, k) => nodes.push({st, x: xs[k], y: y0}));
      pipes.push({d: `M150 ${y0}L${xs[0] - NW / 2} ${y0}`, from: 'src', to: 0});
      for (let k = 1; k < main.length; k++) pipes.push({d: `M${xs[k - 1] + NW / 2} ${y0}L${xs[k] - NW / 2} ${y0}`, from: k - 1, to: k});
      const last = main.length - 1;
      if (borrow) {
        const bx = xs[last], by = 350, sx = xs[0], rr = 26;
        nodes.push({st: borrow, x: bx, y: by});
        const b = nodes.length - 1;
        pipes.push({d: `M${bx} ${y0 + NH / 2}L${bx} ${by - NH / 2}`, from: last, to: b});
        pipes.push({d: `M${bx - NW / 2} ${by}L${sx + rr} ${by}Q${sx} ${by} ${sx} ${by - rr}L${sx} ${y0 + NH / 2}`, from: b, to: 0, debt: true,
          badge: {x: (sx + bx) / 2, y: by, text: `↻ ${r.L}× LEVERAGE`}});
      }
      pipes.push({d: curve(xs[last] + NW / 2, y0, TX - TW / 2, borrow ? 200 : 230), from: last, to: 'tank', after: true});
    }
    return {src, nodes, pipes, tank: {x: TX, y: ty, w: TW}};
  }

  function measure(ds) {
    const ns = 'http://www.w3.org/2000/svg', svg = document.createElementNS(ns, 'svg');
    svg.setAttribute('style', 'position:absolute;width:0;height:0;visibility:hidden');
    document.body.appendChild(svg);
    const out = ds.map(d => { const p = document.createElementNS(ns, 'path'); p.setAttribute('d', d); svg.appendChild(p); return p.getTotalLength(); });
    svg.remove();
    return out;
  }

  function renderRoute() {
    stopTimers();
    const res = Y.result(S.tier, S.s, S.amount), r = res.route, i = idx(S.tier), L = layout(r);
    const [lu, ld] = labels(res);
    $('rtitle').textContent = r.label;
    $('rchips').innerHTML = chips(res, i).join('') + `<span class="chip m">${r.chain.toUpperCase()}</span>`;
    // timing: water runs pipe by pipe; a node lights when its water arrives; the tank fills last
    // a pipe starts when the node it leaves is lit; a node is lit when every pipe into it has arrived (the loop's
    // borrowed water back into the swap does not count); the way out to the tank waits until the loop has gone round
    const lens = measure(L.pipes.map(p => p.d));
    const hasLoop = L.pipes.some(p => p.debt), laps = r.L > 1 ? Math.min(4, Math.ceil(r.L)) : 0, lapT = 0.55;
    const lit = {src: 0.25}, into = {}, left = {};
    L.pipes.forEach(p => { if (!p.debt) left[p.to] = (left[p.to] || 0) + 1; });
    let todo = L.pipes.map((p, k) => k);
    while (todo.length) {
      const before = todo.length;
      todo = todo.filter(k => {
        const p = L.pipes[k];
        if (!(p.from in lit) || (p.after && hasLoop && lit.loop === undefined)) return true;
        p.len = lens[k];
        p.dur = Math.max(0.35, p.len * 0.0021);
        p.t = p.after && hasLoop ? Math.max(lit[p.from], lit.loop + laps * lapT) : lit[p.from];
        const end = p.t + p.dur;
        if (p.debt) lit.loop = end;
        else {
          into[p.to] = Math.max(into[p.to] || 0, end);
          if (--left[p.to] === 0) lit[p.to] = into[p.to];
        }
        return false;
      });
      if (todo.length === before) throw new Error('pipes do not connect');
    }
    const s = n => `${n.toFixed(2)}s`;
    const pipeSvg = L.pipes.map(p => {
      const st = `--len:${p.len.toFixed(1)};--t:${s(p.t)};--dur:${s(p.dur)}`;
      const grad = p.debt ? 'url(#wd)' : 'url(#wg)';
      return `<g style="${st}"><path class="casing" d="${p.d}" stroke-width="20"/><path class="glasspipe" d="${p.d}" stroke-width="13"/>
        <path class="water" d="${p.d}" stroke="${grad}" stroke-width="9"/><path class="bubbles" d="${p.d}" stroke-width="3"/>
        ${p.label ? `<text class="share" x="${p.lx}" y="${p.ly}">${p.label}</text>` : ''}
        ${p.badge ? `<g class="badge" style="--t:${s(p.t + p.dur)}"><rect x="${p.badge.x - 84}" y="${p.badge.y - 16}" width="168" height="32" rx="16"/>
          <text x="${p.badge.x}" y="${p.badge.y}" id="lap">${shot ? p.badge.text : '↻ 1× LEVERAGE'}</text></g>` : ''}</g>`;
    }).join('');
    const nodeSvgs = L.nodes.map((n, k) => nodeSvg(n.st, n.x, n.y, k, s(lit[k]))).join('');
    // the tank fills with the good month: a quarter for nothing, near full at x2
    const tk = L.tank, top = 80, h = 300, lvl = 0.22 + 0.68 * Math.min(1, Math.max(0, res.up - 1)), tx0 = tk.x - tk.w / 2;
    const badc = res.bad >= 1 ? '#a9b8cc' : '#ff4444';
    const val = usd(res.upUsd), fs = Math.min(26, (tk.w - 18) / (val.length * 0.66));
    const tank = `<g class="tank"><rect class="shell" x="${tx0}" y="${top}" width="${tk.w}" height="${h}" rx="22"/>
      <clipPath id="tc"><rect x="${tx0 + 3}" y="${top + 3}" width="${tk.w - 6}" height="${h - 6}" rx="19"/></clipPath>
      <g clip-path="url(#tc)"><g class="liq" style="--t:${s(lit.tank - 0.2)}">
        <rect x="${tx0}" y="${top + h * (1 - lvl)}" width="${tk.w}" height="${h * lvl}" fill="url(#wt)"/>
        <path class="wave" d="M${tx0} ${top + h * (1 - lvl)}${Array.from({length: 6}, (_, k) => `q15 -9 30 0t30 0`).join('')}V${top + h}H${tx0}Z" fill="#00ff88" opacity=".35"/>
      </g></g>
      <text class="k" x="${tk.x}" y="${top - 14}">THIS MONTH</text>
      <g class="figs" style="--t:${s(lit.tank + 0.5)}">
        <text class="v" x="${tk.x}" y="${top + 150}" style="font-size:${fs.toFixed(1)}px">${val}</text>
        <text class="k" x="${tk.x}" y="${top + 176}" style="fill:#e6edf7">${lu.toUpperCase()}</text>
        <text x="${tk.x}" y="${top + h + 26}" style="font:17px 'Archivo Black',sans-serif;fill:${badc}">${usd(res.badUsd)}</text>
        <text class="k" x="${tk.x}" y="${top + h + 44}" style="fill:${badc}">${ld.toUpperCase()}</text>
      </g></g>`;
    $('pipes').innerHTML = `<svg viewBox="0 0 1240 440" role="img" aria-label="${r.label}">
      <defs>
        <linearGradient id="wg" gradientUnits="userSpaceOnUse" x1="100" y1="0" x2="1100" y2="0"><stop offset="0" stop-color="#00cfff"/><stop offset="1" stop-color="#00ff88"/></linearGradient>
        <linearGradient id="wd" gradientUnits="userSpaceOnUse" x1="900" y1="0" x2="300" y2="0"><stop offset="0" stop-color="#3b82f6"/><stop offset="1" stop-color="#00cfff"/></linearGradient>
        <linearGradient id="wt" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#00ff88" stop-opacity=".85"/><stop offset="1" stop-color="#00cfff" stop-opacity=".55"/></linearGradient>
      </defs>
      ${pipeSvg}${sourceSvg(L.src.x, L.src.y)}${nodeSvgs}${tank}</svg>`;
    // lap counter on the loop badge: 1x, then each lap adds leverage until L
    if (laps && !shot) {
      const t0 = lit.loop * 1000;
      for (let k = 1; k <= laps; k++) {
        const v = k === laps ? r.L : Math.min(r.L, 1 + (r.L - 1) * k / laps);
        later(t0 + k * lapT * 1000, () => { const el = $('lap'); if (el) el.textContent = `↻ ${+v.toFixed(1)}× LEVERAGE`; });
      }
    }
    Object.entries(lit).forEach(([k, v]) => { if (k !== 'tank' && k !== 'loop') later(v * 1000, () => document.querySelector(`.node[data-n="${k}"]`)?.classList.add('lit')); });
    const liq = res.liqDrop === null ? `<b>None</b><span>no borrowing against a price</span>`
      : `<b>${res.asset} −${Math.round(res.liqDrop * 100)}%</b><span>the loop closes there</span>`;
    $('outcome').className = 'outcome' + (S.started ? ' started' : '');
    $('outcome').innerHTML = `<div class="up"><small>GOOD MONTH · ${lu.toUpperCase()}</small><b>${usd(res.upUsd)}</b><span>${fx(res.up)} · ${fp(res.up)}</span></div>
      <div class="dn ${res.bad >= 1 ? 'flat' : ''}"><small>BAD MONTH · ${ld.toUpperCase()}</small><b>${usd(res.badUsd)}</b><span>${fx(res.bad)} · ${fp(res.bad)}</span></div>
      <div class="lq"><small>LIQUIDATION</small>${liq}</div>
      <div class="start"><button class="go ${i === 3 ? 'red' : ''} notrun" id="start">START</button>
        <button class="go running" disabled style="background:#00ff88;color:#06090f"><i class="dot"></i>RUNNING · DEMO</button>
        <div class="chips"><span class="chip c">AI RE-CHECKS EVERY 6 H</span><span class="chip m">${num(S.amount)} USDC</span></div></div>`;
  }

  /* ---------- the logo, large ---------- */
  function renderLogo() {
    const mark = document.querySelector('.brand svg').outerHTML;
    $('sheet').innerHTML = `${mark.replace('<svg', '<svg class="big"')}<div><div class="cap">CYMETICA</div>
      <div class="wm">YIELD <em>BOOSTER</em></div>
      <div class="sizes">${[96, 48, 24].map(z => `<div>${mark.replace('<svg', `<svg style="width:${z}px;height:${z}px"`)}<br>${z}px</div>`).join('')}</div></div>`;
  }

  /* ---------- navigation ---------- */
  function can(n) { return n === 1 || (S.tier && (n === 2 || S.amount > 0)); }
  function go(n) {
    if (!can(n)) return;
    stopTimers();
    S.step = n;
    document.querySelectorAll('.view').forEach(v => v.classList.toggle('on', v.id === 'v' + n));
    document.querySelectorAll('#steps button').forEach(b => {
      const k = +b.dataset.go;
      b.className = k === n ? 'on' : k < n ? 'done' : '';
      b.disabled = !can(k);
    });
    if (n === 1) renderTiers();
    if (n === 2) renderAmount();
    if (n === 3) runFinder();
    if (n === 4) renderRoute();
    if (!shot) scrollTo({top: 0, behavior: 'smooth'});
  }

  document.addEventListener('click', e => {
    const g = e.target.closest('[data-go]');
    if (g && !g.disabled) return go(+g.dataset.go);
    const t = e.target.closest('[data-tier]');
    if (t) { S.tier = t.dataset.tier; S.started = false; return go(2); }
    const m = e.target.closest('[data-move]');
    if (m) { S.s = +m.dataset.move; return renderTiers(); }
    const a = e.target.closest('[data-amt]');
    if (a) { S.amount = +a.dataset.amt; $('amt').value = num(S.amount); return updateMonth(); }
    if (e.target.closest('#find')) return go(3);
    if (e.target.closest('#start')) { S.started = true; $('outcome').classList.add('started'); return; }
    if (e.target.closest('#home')) return go(1);
  });
  $('amt').addEventListener('input', e => {
    S.amount = +e.target.value.replace(/[^\d.]/g, '') || 0;
    updateMonth();
  });
  $('amt').addEventListener('blur', e => { if (S.amount > 0) e.target.value = num(S.amount); });
  $('amt').addEventListener('keydown', e => { if (e.key === 'Enter' && S.amount > 0) go(3); });

  if (q.has('logo')) {
    document.querySelectorAll('.view').forEach(v => v.classList.toggle('on', v.id === 'vlogo'));
    renderLogo();
  } else {
    if (!tierOf(S.tier)) S.tier = null;
    $('amt').value = num(S.amount);
    go(Math.max(1, Math.min(4, +q.get('step') || 1)));
  }
})();
