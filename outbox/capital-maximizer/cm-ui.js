/* Capital Maximizer views. Every figure comes from CM (cm-core.js): the tier cards from CM.card, the three
   strategies from CM.top3, a tuned leverage from CM.tune, the dollars from CM.profit. Nothing here computes a return.
   ?step=1..4 &tier= &amount= &pick=0..2 &lev= open a state; &shot=1 freezes it; ?tab=platforms; ?logo=1. */
(function () {
  const D = window.CM_DATA, C = window.CM;
  const q = new URLSearchParams(location.search);
  const shot = q.has('shot');
  if (shot) document.body.classList.add('shot');
  const S = {tab: 'max', step: 1, tier: null, amount: 5000, picks: null, foundFor: null, pick: 0, started: false, filter: 'All'};
  const $ = id => document.getElementById(id);
  const timers = [];
  const later = (ms, f) => timers.push(setTimeout(f, shot ? 0 : ms));
  const stop = () => { while (timers.length) clearTimeout(timers.pop()); };

  /* ---------- formats ---------- */
  const num = v => Math.round(v).toLocaleString('en-US');
  const usd = v => { const a = Math.abs(v); return (v < 0 ? '−' : '+') + '$' + (a < 100 ? a.toFixed(2) : num(a)); };
  const fx = v => '×' + (Math.abs(v - 1) < 0.1 ? v.toFixed(3) : v.toFixed(2));
  const fp = v => {
    const p = (v - 1) * 100, a = Math.abs(p);
    return (p < 0 ? '−' : '+') + (a < 1 ? a.toFixed(2) : a < 10 ? a.toFixed(1) : a.toFixed(0)) + '%';
  };
  const bn = v => v >= 1e9 ? (v / 1e9).toFixed(1) + 'B' : (v / 1e6).toFixed(0) + 'M';
  const pname = p => D.protocols[p].name;
  const icon = p => `https://icons.llamao.fi/icons/protocols/${D.protocols[p].icon}?w=96`;
  const when = iso => new Date(iso.replace('Z', ':00Z')).toLocaleString('en-GB',
    {day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit', timeZone: 'UTC'}) + ' UTC';
  const tierOf = id => C.TIERS.find(t => t.id === id);
  const idx = id => C.TIERS.findIndex(t => t.id === id);
  const liqWhat = r => r.asset === 'USD' ? 'sUSDe' : r.asset;
  const liqTxt = r => r.pLiq === null ? null : `${liqWhat(r)} −${Math.round((1 - r.pLiq) * 100)}%`;
  const hex = (x, y, R) => 'M' + [0, 1, 2, 3, 4, 5].map(k => {
    const a = Math.PI / 180 * (60 * k - 90);
    return `${(x + R * Math.cos(a)).toFixed(2)} ${(y + R * Math.sin(a)).toFixed(2)}`;
  }).join('L') + 'Z';
  const MAXDEF = `Max profit: a month where ETH and BTC rise ${C.MOVE * 100}% and today's rates hold. Each rate is the lowest of today's, the 7-day and the 30-day APY of a DefiLlama pool, read ${when(D.fetched_at)}.`;

  function tween(el, to, fmt, ms = 420) {
    if (!el) return;
    const from = el.dataset.v !== undefined && el.dataset.v !== '' ? +el.dataset.v : to;
    el.dataset.v = to;
    if (shot || from === to) { el.textContent = fmt(to); return; }
    const t0 = performance.now();
    const step = now => {
      const k = Math.min(1, (now - t0) / ms), e = 1 - Math.pow(1 - k, 3);
      el.textContent = fmt(from + (to - from) * e);
      if (k < 1) requestAnimationFrame(step);
    };
    requestAnimationFrame(step);
  }

  /* ---------- the tier emblems: a hexagon socket with a line icon ---------- */
  const ICONS = [
    '<path d="M29 17.5l9 3.4v6.6c0 6-3.9 10-9 12.6-5.1-2.6-9-6.6-9-12.6v-6.6z"/><path d="M25.2 28.6l2.8 2.8 5-5.4"/>',
    '<path d="M29 41V28"/><path d="M29 31.5c-5.2 0-8.2-3-8.2-8.2 5.2 0 8.2 3 8.2 8.2z"/><path d="M29 28.5c0-5.2 3-8.2 8.2-8.2 0 5.2-3 8.2-8.2 8.2z"/>',
    '<path d="M29 41.5c-5.4 0-8.4-3.5-8.4-7.6 0-4.6 4-6.6 4-11.4 3 1.8 4.6 4.1 4.6 6.6 1.5-1 2.4-2.8 2.4-4.7 3.1 2.5 5.4 5.9 5.4 9.4 0 4.3-2.9 7.7-8 7.7z"/>',
    '<rect x="19.5" y="19.5" width="19" height="19" rx="4.5"/>' + [[24.3, 24.3], [33.7, 24.3], [29, 29], [24.3, 33.7], [33.7, 33.7]]
      .map(([x, y]) => `<circle cx="${x}" cy="${y}" r="1.5" style="fill:#ff4444;stroke:none"/>`).join(''),
  ];
  const TONE = ['#00cfff', '#00ff88', '#00ff88', '#ff4444'];
  function emblem(i) {
    return `<svg class="emblem" viewBox="0 0 58 58"><path class="hx" d="${hex(29, 29, 27)}" ${i === 3 ? 'style="stroke:#ff4444"' : ''}/>
      <path class="hi" d="${hex(29, 29, 22)}"/><g class="ic" style="stroke:${TONE[i]}">${ICONS[i]}</g></svg>`;
  }
  const SAY = {
    conservative: () => 'Stablecoins only. No leverage.',
    medium: () => 'Pools, staking, stable loops.',
    high: t => `ETH & BTC loops up to ${t.maxL}×.`,
    og: t => `Loops up to ${t.maxL}×. All in.`,
  };
  const ARROW = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><path d="M4 12h15M13 6l6 6-6 6"/></svg>';

  /* ---------- the rail ---------- */
  function can(n) {
    return n === 1 || (!!S.tier && (n === 2 || (S.amount > 0 && (n === 3 || (n === 4 && !!S.picks)))));
  }
  function renderRail() {
    $('rail').innerHTML = ['Risk', 'Amount', 'Strategies', 'Plan'].map((n, k) => {
      const s = k + 1, cls = s === S.step ? 'on' : s < S.step ? 'done' : '';
      return (k ? `<i class="${s <= S.step ? 'lit' : ''}"></i>` : '') +
        `<button data-step="${s}" class="${cls}" ${can(s) ? '' : 'disabled'}><svg viewBox="-11 -11 22 22"><path d="${hex(0, 0, 9)}"/></svg><span>${n}</span></button>`;
    }).join('');
  }

  /* ---------- step 1 ---------- */
  function renderTiers() {
    $('tiers').innerHTML = C.TIERS.map((t, i) => {
      const c = C.card(t.id), top = C.top3(t.id);
      const assets = [...new Set(top.map(r => r.asset === 'USD' ? 'sUSDe' : r.asset || 'USDC'))].join(' · ');
      return `<button class="frame tier t${i}" data-tier="${t.id}">
        <div class="row1">${emblem(i)}<div class="meter">${[0, 1, 2, 3].map(k => `<i class="${k <= i ? 'on' : ''}"></i>`).join('')}</div></div>
        <h3>${t.name}</h3><div class="say">${SAY[t.id](t)}</div>
        <div class="maxp"><div class="lbl">MAX PROFIT / MONTH</div><div class="big"><b>${fx(c.up)}</b><span>${fp(c.up)}</span></div></div>
        <div class="facts"><div><div class="lbl">LEVERAGE</div><b>${t.maxL === 1 ? 'None' : 'Up to ' + t.maxL + '×'}</b></div>
          <div><div class="lbl">ASSETS</div><b>${assets}</b></div></div>
        <div class="go1"><span>Choose</span>${ARROW}</div></button>`;
    }).join('');
    $('note1').innerHTML = `<span>Max profit = a month where ETH &amp; BTC rise ${C.MOVE * 100}%<span class="tip" title="${MAXDEF}">i</span></span>
      <span>Rates <b>DefiLlama</b> · ${when(D.fetched_at)}</span>`;
  }

  /* ---------- step 2 ---------- */
  function renderAmount() {
    const t = tierOf(S.tier), i = idx(S.tier);
    $('picked').innerHTML = `<span class="picked">${emblem(i)}<b>${t.name}</b><button data-step="1">Change</button></span>`;
    $('quick').innerHTML = [500, 1000, 5000, 25000, 100000].map(a => `<button data-amt="${a}">${num(a)}</button>`).join('');
    $('amt').value = num(S.amount);
    updatePreview();
  }
  function updatePreview() {
    const ok = S.amount > 0, c = C.card(S.tier);
    $('preview').className = 'preview' + (S.tier === 'og' ? ' red' : '');
    $('preview').innerHTML = ok ? `<div class="lbl">MAX PROFIT THIS MONTH<span class="tip" title="${MAXDEF}">i</span></div><b>${usd(C.profit(c.route, S.amount))}</b>` : '';
    $('find').disabled = !ok;
    $('find').classList.toggle('red', S.tier === 'og');
    document.querySelectorAll('#quick button').forEach(b => b.classList.toggle('on', +b.dataset.amt === S.amount));
  }

  /* ---------- the skill tree ---------- */
  /* d is how far a node is grown from the root, w how far to the side; lv and lh say where its label sits when the
     tree flows down (the three side by side) or to the right (the plan) */
  function shape(r) {
    const N = [], E = [], st = r.steps;
    const add = (id, kind, d, w, lv, lh, step) => N.push({id, kind, d, w, lv, lh, step});
    add('root', 'root', 0, 0, 'right', 'below');
    if (r.type === 'vaults') {
      st.filter(s => s.kind === 'vault').forEach((s, k) => {
        add('v' + k, 'node', k === 1 ? 1.95 : 1.45, k - 1, k === 1 ? 'right' : 'below', 'below', s);
        E.push(['root', 'v' + k], ['v' + k, 'apex']);
      });
      add('apex', 'apex', 3.1, 0, 'below', 'below');
    } else if (r.type === 'lp') {
      add('swap', 'node', 1, -0.85, 'left', 'below', st[1]);
      add('lp', 'node', 2, 0, 'right', 'below', st[2]);
      add('apex', 'apex', 3.1, 0, 'below', 'below');
      E.push(['root', 'swap'], ['swap', 'lp'], ['root', 'lp'], ['lp', 'apex']);
    } else {
      const swap = st.find(s => s.kind === 'swap'), stake = st.find(s => s.kind === 'stake');
      const coll = st.find(s => s.kind === 'collateral'), bor = st.find(s => s.kind === 'borrow');
      const side = coll ? 'above' : 'below';
      add('swap', 'node', 1, 0, 'left', side, swap);
      E.push(['root', 'swap']);
      let d = 1, prev = 'swap';
      if (stake) { add('stake', 'node', ++d, 0, 'left', side, stake); E.push([prev, 'stake']); prev = 'stake'; }
      if (coll) {
        add('coll', 'node', ++d, 0, 'left', 'above', coll);
        add('bor', 'node', d, 1, 'right', 'below', bor);
        add('lev', 'lever', 1, 1, 'right', 'below');
        E.push([prev, 'coll'], ['coll', 'bor'], ['bor', 'lev', 1], ['lev', 'swap', 1], ['coll', 'apex']);
        add('apex', 'apex', d + 1.35, 0.5, 'below', 'below');
      } else {
        add('apex', 'apex', d + 1.2, 0, 'below', 'below');
        E.push([prev, 'apex']);
      }
    }
    // off the home chain the USDC first crosses with Circle's CCTP: one node more between the wallet and the rest
    if (awayOf(r).length) {
      N.forEach(n => { if (n.id !== 'root') n.d += 1; });
      E.forEach(e => { if (e[0] === 'root') e[0] = 'cctp'; });
      N.push({id: 'cctp', kind: 'bridge', d: 1, w: 0, lv: 'right', lh: 'below'});
      E.unshift(['root', 'cctp']);
    }
    return {N, E};
  }
  const HOME = 'Ethereum';
  const awayOf = r => [...new Set((r.type === 'vaults' ? r.steps.filter(s => s.chain).map(s => s.chain) : [r.chain]).filter(c => c !== HOME))];
  const RAD = {apex: 38, root: 26, lever: 25, node: 28, bridge: 28};

  function label(n, r) {
    const s = n.step, rt = (v, sign = '+') => `<tspan class="${sign === '+' ? 'e' : 'p'}">${sign}${v.toFixed(2)}%</tspan>`;
    if (n.kind === 'root') return [num(S.amount), 'USDC', 'USDC'];
    if (n.kind === 'bridge') { const to = '→ ' + awayOf(r).map(chainName).join(' · '); return ['Circle CCTP', to, to]; }
    if (n.kind === 'lever') {
      const l = r.pLiq === null ? null : `${r.asset === 'USD' ? 'depeg' : r.asset} −${Math.round((1 - r.pLiq) * 100)}%`;
      return ['Leverage', l ? `liq <tspan class="p">${l}</tspan>` : 'no liquidation', l ? 'liq ' + l : 'no liquidation'];
    }
    if (s.kind === 'swap') return [pname(s.project), s.title, s.title];
    if (s.kind === 'stake') return [pname(s.project), `stake ${rt(s.rate)}`, `stake +${s.rate.toFixed(2)}%`];
    if (s.kind === 'collateral') {
      return [pname(s.project), `collateral${s.rate > 0.01 ? ' ' + rt(s.rate) : ''}`, `collateral${s.rate > 0.01 ? ' +' + s.rate.toFixed(2) + '%' : ''}`];
    }
    if (s.kind === 'borrow') return [pname(s.project), `borrow ${rt(s.rate, '−')}`, `borrow −${s.rate.toFixed(2)}%`];
    if (s.kind === 'vault') return [s.title, `${s.chain} ${rt(s.rate)}`, `${s.chain} +${s.rate.toFixed(2)}%`];
    if (s.kind === 'lp') return [pname(s.project), `fees ${rt(s.rate)}`, `fees +${s.rate.toFixed(2)}%`];
    return ['', '', ''];
  }

  /* what the strategy does, in order, with the user's own dollars: the numbers on the tree's nodes point here */
  function stepRows(r) {
    const A = S.amount, st = r.steps, rows = [];
    const add = (node, text, meta, cls = '') => rows.push({node, text, meta, cls, no: rows.length + 1});
    const yr = (v, sign = '+') => `${sign}${v.toFixed(2)}%/yr`;
    const away = awayOf(r);
    if (away.length) {
      const moved = r.type === 'vaults' ? A * st.filter(s => s.kind === 'vault' && s.chain !== HOME).length / 3 : A;
      add('cctp', `Move ${num(moved)} USDC to ${away.map(chainName).join(' & ')}`, 'Circle CCTP', 'c');
    }
    if (r.type === 'vaults') {
      st.filter(s => s.kind === 'vault').forEach((s, k) =>
        add('v' + k, `Put ${num(A * s.share)} USDC in ${s.title}`, `${pname(s.project)} ${yr(s.rate)}`, 'e'));
    } else if (r.type === 'lp') {
      add('swap', `Swap ${num(A / 2)} USDC → ETH`, pname(st[1].project));
      add('lp', `Pool the ETH + ${num(A / 2)} USDC`, `fees ${yr(st[2].rate)}`, 'e');
    } else {
      const swap = st.find(s => s.kind === 'swap'), stake = st.find(s => s.kind === 'stake');
      const coll = st.find(s => s.kind === 'collateral'), bor = st.find(s => s.kind === 'borrow');
      const tok = r.label.replace(' loop', '').replace('Staked ', '');
      add('swap', `Swap ${num(A)} ${swap.title}`, pname(swap.project));
      if (stake) add('stake', `${tok} earns staking yield`, `${pname(stake.project)} ${yr(stake.rate)}`, 'e');
      if (coll) {
        add('coll', `Deposit the ${tok} as collateral`, pname(coll.project));
        add('bor', `Borrow ${num(A * (r.L - 1))} ${bor.loan} against it`, `${pname(bor.project)} ${yr(bor.rate, '−')}`, 'p');
        add('lev', `Buy more ${tok}, repeat to ${r.L.toFixed(1)}×`, `${num(A * r.L)} USD in ${tok}`, 'c');
      }
    }
    return rows;
  }
  function stepsHtml(r) {
    return `<ol class="stepl">${stepRows(r).map(x => `<li><span class="no">${x.no}</span><span class="tx">${x.text}</span><span class="mt ${x.cls}">${x.meta}</span></li>`).join('')}</ol>`;
  }

  function tree(r, o) {
    const {N, E} = shape(r), V = o.orient === 'v', p = o.id, og = S.tier === 'og';
    const nums = Object.fromEntries(stepRows(r).map(x => [x.node, x.no]));
    const W = V ? 460 : 1120, H = V ? 600 : 400;
    const ds = N.map(n => n.d), ws = N.map(n => n.w), dmax = Math.max(...ds), wmin = Math.min(...ws), wmax = Math.max(...ws);
    const unit = V ? 135 : 150;
    if (V) {                                                     // the money enters at the top and flows down
      const cx = W / 2 - unit * (wmin + wmax) / 2, top = 58, bot = H - 96, dep = (bot - top) / dmax;
      N.forEach(n => { n.x = cx + n.w * unit; n.y = top + n.d * dep; });
    } else {
      const cy = H / 2 - unit * (wmin + wmax) / 2 - (wmax > 0.6 ? 22 : 0), left = 80, right = W - 110, dep = (right - left) / dmax;
      N.forEach(n => { n.x = left + n.d * dep; n.y = cy + n.w * unit; });
    }
    const by = Object.fromEntries(N.map(n => [n.id, n]));
    const g0 = o.grow ? (o.delay || 0) + 0.15 : 0, dly = n => o.grow ? g0 + (n.kind === 'lever' ? dmax * 0.24 + 0.25 : n.d * 0.24) : 0;
    const accent = og ? '#ff4444' : '#00ff88';
    // links
    let links = '', sparks = '';
    E.forEach(([a, b, loopy], k) => {
      const A = by[a], B = by[b], dx = B.x - A.x, dy = B.y - A.y, L = Math.hypot(dx, dy), ux = dx / L, uy = dy / L;
      const x1 = A.x + ux * RAD[A.kind], y1 = A.y + uy * RAD[A.kind], x2 = B.x - ux * RAD[B.kind], y2 = B.y - uy * RAD[B.kind];
      const d = `M${x1.toFixed(1)} ${y1.toFixed(1)}L${x2.toFixed(1)} ${y2.toFixed(1)}`, len = Math.hypot(x2 - x1, y2 - y1);
      const t = dly(A) + 0.12, col = loopy ? '#00cfff' : `url(#${p}lg)`;
      links += `<path class="lk base" d="${d}"/><path class="lk glow" d="${d}" stroke="${loopy ? '#00cfff' : accent}" style="--d:${t}s;filter:blur(2.2px)"/>
        <path class="lk lit" pathLength="1" d="${d}" stroke="${col}" style="--d:${t}s"/>`;
      const n = loopy ? Math.max(2, Math.round(r.L)) : 2, dur = Math.max(1.3, len / 52);
      for (let j = 0; j < n; j++) {
        const b0 = (shot ? 0 : t + 0.55) + j * dur / n, c = loopy ? '#00cfff' : accent;
        sparks += `<circle r="2" fill="${c}" opacity="0" style="filter:drop-shadow(0 0 4px ${c})">
          <animateMotion dur="${dur.toFixed(2)}s" begin="${b0.toFixed(2)}s" repeatCount="indefinite" path="${d}"/>
          <animate attributeName="opacity" values="0;1;1;0" keyTimes="0;.12;.82;1" dur="${dur.toFixed(2)}s" begin="${b0.toFixed(2)}s" repeatCount="indefinite"/></circle>`;
      }
    });
    // nodes
    const nodes = N.map(n => {
      const R = RAD[n.kind], t = dly(n), side = V ? n.lv : n.lh;
      let body = '';
      if (n.kind === 'root') {
        body = `<circle cx="${n.x}" cy="${n.y}" r="${R + 12}" fill="url(#${p}rh)"/>
          <circle cx="${n.x}" cy="${n.y}" r="${R}" fill="url(#${p}rb)" stroke="#00cfff" stroke-opacity=".55" stroke-width="1.2"/>
          <text class="usd" x="${n.x}" y="${n.y + 1}">$</text>`;
      } else if (n.kind === 'apex') {
        body = `<circle cx="${n.x}" cy="${n.y}" r="${R + 26}" fill="url(#${p}ah)"/>
          <path d="${hex(n.x, n.y, R + 7)}" fill="none" stroke="${accent}" stroke-opacity=".35" stroke-width=".8"/>
          <path d="${hex(n.x, n.y, R)}" fill="url(#${p}af)" stroke="${accent}" stroke-width="1.4"/>
          <text class="apx" x="${n.x}" y="${n.y + 1}" style="font-size:${Math.min(19, 62 / (fp(r.up).length * 0.66)).toFixed(1)}px">${fp(r.up)}</text>`;
      } else if (n.kind === 'lever') {
        const g = o.interactive ? C.range(r, S.tier) : null, by2 = V ? n.y - 46 : n.y + 46;
        const dia = (k) => `M${n.x} ${n.y - k}L${n.x + k} ${n.y}L${n.x} ${n.y + k}L${n.x - k} ${n.y}Z`;
        body = `<circle cx="${n.x}" cy="${n.y}" r="${R + 16}" fill="url(#${p}lh)"/>
          <path d="${dia(R + 1)}" fill="#06090f" stroke="#00cfff" stroke-width="1.4"/><path d="${dia(R - 5)}" fill="none" stroke="#00cfff" stroke-opacity=".3" stroke-width=".7"/>
          <text class="lev" x="${n.x}" y="${n.y + 1}">${r.L.toFixed(1)}×</text>` +
          (g ? `<g class="btn ${r.L <= g.min ? 'off' : ''}" data-act="dec" data-col="${o.col}"><circle cx="${n.x - 19}" cy="${by2}" r="12"/><path d="M${n.x - 24} ${by2}h10"/></g>
            <g class="btn ${r.L >= g.max - 1e-9 ? 'off' : ''}" data-act="inc" data-col="${o.col}"><circle cx="${n.x + 19}" cy="${by2}" r="12"/><path d="M${n.x + 14} ${by2}h10M${n.x + 19} ${by2 - 5}v10"/></g>` : '');
      } else if (n.kind === 'bridge') {
        body = `<circle cx="${n.x}" cy="${n.y}" r="${R + 14}" fill="url(#${p}lh)"/>
          <path d="${hex(n.x, n.y, R)}" class="hx" stroke="#00cfff" style="stroke-dasharray:4 3"/>
          <path d="${hex(n.x, n.y, R - 5)}" class="hi"/>
          <clipPath id="${p}c${n.id}"><circle cx="${n.x}" cy="${n.y}" r="16.5"/></clipPath>
          <text class="ini" x="${n.x}" y="${n.y}">C</text>
          <image href="https://icons.llamao.fi/icons/protocols/circle?w=96" x="${n.x - 16.5}" y="${n.y - 16.5}" width="33" height="33" clip-path="url(#${p}c${n.id})"/>`;
      } else {
        const s = n.step, loopy = s.kind === 'borrow';
        body = `<path d="${hex(n.x, n.y, R)}" class="hx" stroke="${loopy ? '#00cfff' : `url(#${p}lg)`}"/>
          <path d="${hex(n.x, n.y, R - 5)}" class="hi"/>
          <clipPath id="${p}c${n.id}"><circle cx="${n.x}" cy="${n.y}" r="16.5"/></clipPath>
          <text class="ini" x="${n.x}" y="${n.y}">${pname(s.project)[0]}</text>
          <image href="${icon(s.project)}" x="${n.x - 16.5}" y="${n.y - 16.5}" width="33" height="33" clip-path="url(#${p}c${n.id})"/>`;
      }
      // the label
      let lab = '';
      if (n.kind === 'apex') {
        const ly = side === 'above' ? n.y - R - 18 : n.y + R + 26;
        lab = `<text class="cap" x="${n.x}" y="${ly}">MAX PROFIT / MO</text>`;
      } else {
        const [t1, t2, plain] = label(n, r);
        const w = Math.max(t1.length * 7.3, plain.length * 6.15) + 20, h = 38;
        const off = n.kind === 'lever' && side === 'below' ? 64 : R + 7;
        let px, py, anchor;
        if (side === 'below') { px = n.x - w / 2; py = n.y + off; anchor = 'middle'; }
        else if (side === 'above') { px = n.x - w / 2; py = n.y - R - 7 - h; anchor = 'middle'; }
        else if (side === 'left') { px = n.x - R - 12 - w; py = n.y - h / 2; anchor = 'end'; }
        else { px = n.x + R + 12; py = n.y - h / 2; anchor = 'start'; }
        const tx = anchor === 'middle' ? px + w / 2 : anchor === 'end' ? px + w - 10 : px + 10;
        lab = `<rect class="pl" x="${px.toFixed(1)}" y="${py.toFixed(1)}" width="${w.toFixed(1)}" height="${h}" rx="7"/>
          <text class="la" x="${tx.toFixed(1)}" y="${(py + 16).toFixed(1)}" style="text-anchor:${anchor}">${t1}</text>
          <text class="lb" x="${tx.toFixed(1)}" y="${(py + 30).toFixed(1)}" style="text-anchor:${anchor}">${t2}</text>`;
      }
      const no = nums[n.id], bx = n.x + R * 0.82, bY = n.y - R * 0.82;
      const badge = no ? `<circle cx="${bx}" cy="${bY}" r="9.5" fill="#06090f" stroke="#00cfff" stroke-width="1.2"/>
        <text x="${bx}" y="${bY + 0.5}" class="num">${no}</text>` : '';
      return `<g class="nd" style="--d:${t}s">${body}${badge}${lab}</g>`;
    }).join('');
    // the backdrop: a fine hexagon lattice fading out from the middle
    const hw = 16 * Math.sqrt(3);
    const lattice = [[0, 0], [hw, 0], [hw / 2, 24], [0, 48], [hw, 48]].map(([x, y]) => `<path class="grid" d="${hex(x, y, 16)}"/>`).join('');
    return `<svg class="tree ${o.grow ? '' : 'static'}" viewBox="0 0 ${W} ${H}" role="img" aria-label="${r.label}, ${r.venue}">
      <defs>
        <linearGradient id="${p}lg" gradientUnits="userSpaceOnUse" ${V ? `x1="0" y1="${H}" x2="0" y2="0"` : `x1="0" y1="0" x2="${W}" y2="0"`}>
          <stop offset="0" stop-color="#00cfff"/><stop offset="1" stop-color="${accent}"/></linearGradient>
        <radialGradient id="${p}rb"><stop offset="0" stop-color="#3b82f6"/><stop offset="1" stop-color="#1e3050"/></radialGradient>
        <radialGradient id="${p}rh"><stop offset="0" stop-color="#3b82f6" stop-opacity=".35"/><stop offset="1" stop-color="#3b82f6" stop-opacity="0"/></radialGradient>
        <radialGradient id="${p}lh"><stop offset="0" stop-color="#00cfff" stop-opacity=".22"/><stop offset="1" stop-color="#00cfff" stop-opacity="0"/></radialGradient>
        <radialGradient id="${p}ah"><stop offset="0" stop-color="${accent}" stop-opacity=".32"/><stop offset="1" stop-color="${accent}" stop-opacity="0"/></radialGradient>
        <linearGradient id="${p}af" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="${og ? '#ff4444' : '#00cfff'}"/><stop offset="1" stop-color="${accent}"/></linearGradient>
        <pattern id="${p}hg" width="${hw.toFixed(2)}" height="48" patternUnits="userSpaceOnUse">${lattice}</pattern>
        <radialGradient id="${p}fade"><stop offset="0" stop-color="#e6edf7" stop-opacity=".9"/><stop offset="1" stop-color="#06090f" stop-opacity="0"/></radialGradient>
        <mask id="${p}m"><rect width="${W}" height="${H}" fill="url(#${p}fade)"/></mask>
      </defs>
      <rect width="${W}" height="${H}" fill="url(#${p}hg)" mask="url(#${p}m)"/>
      ${links}${sparks}${nodes}</svg>`;
  }

  /* ---------- step 3: scan, then three trees ---------- */
  /* the scan reads every supported platform: two rings of logos, the inner fourteen and the outer twenty-two */
  function radarSvg() {
    const P = D.platforms, inner = 14;
    const logos = P.map((p, k) => {
      const ring = k < inner, n = ring ? inner : P.length - inner, j = ring ? k : k - inner, R = ring ? 112 : 182;
      const a = (j / n) * Math.PI * 2 - Math.PI / 2 + (ring ? 0 : 0.12), x = 220 + R * Math.cos(a), y = 220 + R * Math.sin(a);
      return `<g class="p"><clipPath id="rc${k}"><circle cx="${x}" cy="${y}" r="14"/></clipPath>
        <circle class="ring" cx="${x}" cy="${y}" r="17.5"/><text x="${x}" y="${y + 5}" text-anchor="middle" style="font:700 13px Inter;fill:#a9b8cc">${p.name[0]}</text>
        <image href="https://icons.llamao.fi/icons/protocols/${p.icon}?w=96" x="${x - 14}" y="${y - 14}" width="28" height="28" clip-path="url(#rc${k})"/><title>${p.name}</title></g>`;
    }).join('');
    return `<svg viewBox="0 0 440 440">
      <defs><linearGradient id="sw" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#00ff88" stop-opacity="0"/><stop offset="1" stop-color="#00ff88" stop-opacity=".3"/></linearGradient></defs>
      ${[70, 112, 148, 182, 214].map(r => `<path d="${hex(220, 220, r)}" fill="none" stroke="#1e3050" stroke-width=".8"/>`).join('')}
      <path d="M220 6V434M6 220H434" stroke="#1e3050" stroke-width=".6"/>
      <path class="sweep" d="M220 220L220 6A214 214 0 0 1 383.9 82.4Z" fill="url(#sw)"/>
      ${logos}
      <text x="220" y="214" text-anchor="middle" style="font:46px 'Archivo Black',sans-serif;fill:#e6edf7" id="rcount">0</text>
      <text x="220" y="244" text-anchor="middle" style="font:600 10px 'JetBrains Mono',monospace;letter-spacing:.24em;fill:#7f93ad">POOLS READ</text></svg>`;
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
  function scan(done) {
    const f = C.find(S.tier), scanT = 2600;
    $('strats').innerHTML = '';
    $('h3').innerHTML = 'Finding your <em>top 3</em>';
    $('p3').textContent = '';
    $('scan').style.display = '';
    const nChains = new Set(D.platforms.flatMap(p => p.chains)).size;
    $('scan').innerHTML = radarSvg() + `<div class="counts"><div><div class="lbl">PLATFORMS</div><b id="c0">0</b></div>
      <div><div class="lbl">CHAINS</div><b id="c4">0</b></div><div><div class="lbl">POOLS READ</div><b id="c1">0</b></div>
      <div><div class="lbl">ROUTES BUILT</div><b id="c2">0</b></div><div class="k3"><div class="lbl">TOP STRATEGIES</div><b id="c3">0</b></div></div>
      <div class="ticker" id="tick"></div>`;
    count($('rcount'), D.scanned.pools, scanT - 300);
    count($('c0'), D.platforms.length, scanT - 600);
    count($('c4'), nChains, scanT - 600);
    count($('c1'), D.scanned.pools, scanT - 300);
    count($('c2'), f.built, scanT);
    later(scanT - 200, () => count($('c3'), 3, 300));
    const logos = [...document.querySelectorAll('#scan .p')];
    logos.forEach((g, k) => later(120 + (k / logos.length) * (scanT - 500), () => g.classList.add('hit')));
    let ti = 0;
    const tick = () => { const r = D.ticker[ti++ % D.ticker.length]; $('tick').innerHTML = `${pname(r[0])} · ${r[1]} · ${r[2]} · <b>${r[3]}%</b>`; };
    for (let k = 0; k < scanT / 70; k++) later(k * 70, tick);
    later(scanT + 250, done);
  }
  function renderStrategies() {
    if (S.foundFor !== S.tier) {
      S.picks = C.top3(S.tier);
      S.foundFor = S.tier;
      S.pick = 0;
      if (!shot) return scan(() => showStrats(true));
    }
    showStrats(!shot);
  }
  function resultHtml(r, k) {
    const l = liqTxt(r);
    return `<div><div class="lbl">MAX PROFIT / MONTH</div><div class="v" data-usd="${k}" data-v="${C.profit(r, S.amount)}">${usd(C.profit(r, S.amount))}</div></div>
      <div class="x"><small>RETURN</small><span data-ret="${k}">${fx(r.up)} · ${fp(r.up)}</span></div>
      <div class="mini" style="grid-column:1/-1"><div><div class="lbl">LEVERAGE</div><b data-lev="${k}">${r.L > 1 ? r.L.toFixed(1) + '×' : 'None'}</b></div>
        <div class="${l ? 'warn' : ''}"><div class="lbl">LIQUIDATION</div><b data-liq="${k}">${l || 'None'}</b></div>
        <div><div class="lbl">CHAIN</div><b>${r.chain.split(' · ').length > 1 ? r.chain.split(' · ').length + ' chains' : r.chain}</b></div></div>`;
  }
  function rankSvg(k) {
    return `<svg class="rank" viewBox="0 0 44 44"><path d="${hex(22, 22, 20)}"/><text x="22" y="23">${k + 1}</text></svg>`;
  }
  function showStrats(grow) {
    $('scan').style.display = 'none';
    $('h3').innerHTML = 'Your <em>top 3</em>';
    $('p3').textContent = `${D.platforms.length} platforms · ${new Set(D.platforms.flatMap(p => p.chains)).size} chains · ${num(D.scanned.pools)} pools read`;
    const og = S.tier === 'og';
    $('strats').innerHTML = S.picks.map((r, k) => `<div class="frame strat ${k === 0 ? 'best' : ''} ${og ? 'og' : ''}" style="--d:${grow ? k * 0.16 : 0}s">
      <div class="hd">${rankSvg(k)}<div><h3>${r.label}</h3><div class="ven">${r.venue}</div></div>${k === 0 ? '<span class="chip g">TOP PICK</span>' : ''}</div>
      <div data-tree="${k}">${tree(r, {orient: 'v', id: 's' + k, col: k, grow, delay: k * 0.16, interactive: true})}</div>
      <div data-steps="${k}">${stepsHtml(r)}</div>
      <div class="result">${resultHtml(r, k)}</div>
      <button class="sel" data-pick="${k}">SELECT STRATEGY ${ARROW.replace('<svg', '<svg width="16" height="16"')}</button></div>`).join('');
  }

  /* leverage tuned in a tree: the same model at the new leverage, then every figure that shows it */
  function tuneCol(k, L) {
    const r0 = S.picks[k], g = C.range(r0, S.tier);
    if (!g) return;
    L = Math.min(g.max, Math.max(g.min, Math.round(L * 10) / 10));
    if (L === r0.L) return;
    const r = C.tune(r0, L);
    S.picks[k] = r;
    S.started = false;
    if (S.step === 3) {
      const box = document.querySelector(`[data-tree="${k}"]`);
      box.innerHTML = tree(r, {orient: 'v', id: 's' + k, col: k, grow: false, interactive: true});
      box.querySelector('.lev')?.classList.add('bump');
      document.querySelector(`[data-steps="${k}"]`).innerHTML = stepsHtml(r);
      tween(document.querySelector(`[data-usd="${k}"]`), C.profit(r, S.amount), usd);
      document.querySelector(`[data-ret="${k}"]`).textContent = `${fx(r.up)} · ${fp(r.up)}`;
      document.querySelector(`[data-lev="${k}"]`).textContent = r.L.toFixed(1) + '×';
      const lq = document.querySelector(`[data-liq="${k}"]`);
      lq.textContent = liqTxt(r) || 'None';
    }
    if (S.step === 4 && k === S.pick) {
      $('plan').innerHTML = planInner(r, false);
      updateBar(r);
    }
  }

  /* ---------- step 4: the plan ---------- */
  const planInner = (r, grow) => `<div class="planin"><div>${tree(r, {orient: 'h', id: 'pl', col: S.pick, grow, interactive: true})}</div>${stepsHtml(r)}</div>`;
  function renderPlan() {
    const r = S.picks[S.pick];
    $('h4').innerHTML = `${r.label} <em>·</em> ${r.venue}`;
    $('p4').textContent = `#${S.pick + 1} of your top 3 · ${num(S.amount)} USDC`;
    $('plan').innerHTML = planInner(r, !shot);
    const g = C.range(r, S.tier), og = S.tier === 'og';
    const lev = g ? `<div class="frame"><div class="lbl"><span>LEVERAGE</span><span id="levv" style="color:#00cfff">${r.L.toFixed(1)}×</span></div>
        <input type="range" id="lev" min="${g.min}" max="${g.max}" step="${g.step}" value="${r.L}">
        <div class="ends"><span>${g.min.toFixed(1)}×</span><span>${g.max.toFixed(1)}×</span></div></div>`
      : `<div class="frame"><div class="lbl"><span>LEVERAGE</span></div><div class="val">None</div><div class="sub">${r.type === 'vaults' ? 'a third in each vault' : 'nothing borrowed'}</div></div>`;
    $('bar').innerHTML = lev + `<div class="frame"><div class="lbl"><span>LIQUIDATION</span></div><div class="val" id="liqv"></div><div class="sub" id="liqs"></div></div>
      <div class="frame"><div class="lbl"><span>MAX PROFIT / MONTH<span class="tip" title="${MAXDEF}">i</span></span></div>
        <div class="val g" id="pv" ${og ? 'style="color:#ff4444;text-shadow:0 0 36px rgba(255,68,68,.35)"' : ''}></div><div class="sub g" id="ps" ${og ? 'style="color:#ff4444"' : ''}></div></div>
      <div class="go4 ${S.started ? 'started' : ''}" id="go4"><button class="cta ${og ? 'red' : ''} startbtn" id="start">START ${ARROW}</button>
        <button class="cta running" disabled><i class="dot"></i>RUNNING · DEMO</button>
        <div class="chips"><span class="chip c">AI RE-CHECKS EVERY 6 H</span><span class="chip m">${r.chain.toUpperCase()}</span></div></div>`;
    updateBar(r);
  }
  function updateBar(r) {
    const slider = $('lev');
    if (slider) {
      const g = C.range(r, S.tier);
      slider.value = r.L;
      slider.style.setProperty('--f', ((r.L - g.min) / (g.max - g.min || 1) * 100).toFixed(1) + '%');
      $('levv').textContent = r.L.toFixed(1) + '×';
    }
    const l = liqTxt(r);
    $('liqv').textContent = l || 'None';
    $('liqv').className = 'val' + (l ? ' r' : '');
    $('liqs').textContent = !l ? 'nothing borrowed against a price' : r.asset === 'USD' ? 'if sUSDe depegs that far' : 'the loop closes there';
    tween($('pv'), C.profit(r, S.amount), usd);
    $('ps').textContent = `${fx(r.up)} · ${fp(r.up)} on ${num(S.amount)} USDC`;
    $('go4')?.classList.toggle('started', S.started);
  }

  /* ---------- the Platforms tab ---------- */
  const CAT = {'Dexs': 'DEX', 'Liquid Staking': 'Liquid staking', 'Liquid Restaking': 'Restaking', 'Basis Trading': 'Synthetic dollar',
    'CDP': 'Stablecoin', 'Lending': 'Lending', 'Yield': 'Yield', 'Derivatives': 'Perps & pools'};
  const CHAIN = {'Hyperliquid L1': 'Hyperliquid', 'Optimism': 'OP'};
  const chainName = c => CHAIN[c] || c;
  const USE = {vault: 'SUPPLY', stake: 'STAKE', collateral: 'COLLATERAL', borrow: 'BORROW', swap: 'SWAP', lp: 'LP'};
  function usage() {
    const out = {};
    for (const r of C.routes()) for (const s of r.steps) if (s.project) {
      const u = out[s.project] = out[s.project] || {uses: new Set(), routes: new Set()};
      u.uses.add(USE[s.kind]);
      u.routes.add(r.id);
    }
    return out;
  }
  /* every supported platform (data.js platforms: one rule, re-checked on each refresh by rates.py), filtered by what
     it is and by chain; the ones the finder builds routes from today carry a cyan dot */
  function renderPlatforms() {
    const P = D.platforms, U = usage(), cat = p => CAT[p.category] || p.category;
    const cats = ['All', ...new Set(P.map(cat))];
    const chainCount = {};
    P.forEach(p => p.chains.forEach(c => { chainCount[c] = (chainCount[c] || 0) + 1; }));
    const S2 = S.chain || 'All chains';
    const ranked = Object.keys(chainCount).sort((a, b) => chainCount[b] - chainCount[a]);
    const shown = S.allChains ? ranked : ranked.filter((c, k) => chainCount[c] >= 3 || c === S2);
    const chains = ['All chains', ...shown];
    const tvl = P.reduce((t, p) => t + p.tvl, 0);
    $('pp').textContent = `DefiLlama · ${when(D.fetched_at)}`;
    $('pstats').className = 'frame pstats';
    $('pstats').innerHTML = [['PLATFORMS', P.length, 'g'], ['TVL', '$' + bn(tvl), ''], ['CHAINS', Object.keys(chainCount).length, ''],
      ['IN THE FINDER TODAY', P.filter(p => p.in_finder).length, '']]
      .map(([k, v, c]) => `<div class="${c}"><b>${v}</b><span class="lbl">${k}</span></div>`).join('') +
      `<span class="chip c" style="margin-left:auto" title="Circle's CCTP burns USDC on one chain and mints it on another: no bridge pool, no wrapped dollar. Every platform here runs on at least one chain it serves.">CROSS-CHAIN · NATIVE USDC VIA CIRCLE CCTP</span>`;
    $('filters').innerHTML = cats.map(c => `<button data-filter="${c}" class="${S.filter === c ? 'on' : ''}">${c}<i>${c === 'All' ? P.length : P.filter(p => cat(p) === c).length}</i></button>`).join('') +
      '<span class="fsep"></span>' +
      chains.map(c => `<button data-chain="${c}" class="${S2 === c ? 'on' : ''}">${c === 'All chains' ? c : chainName(c)}<i>${c === 'All chains' ? Object.keys(chainCount).length : chainCount[c]}</i></button>`).join('') +
      (ranked.length > shown.length ? `<button data-morechains="1">+${ranked.length - shown.length}</button>` : '');
    // one tile a platform: logo, name, what it is and how much it holds; the rest on hover
    $('plats').innerHTML = P.filter(p => (S.filter === 'All' || cat(p) === S.filter) && (S2 === 'All chains' || p.chains.includes(S2))).map((p, i) => {
      const u = U[p.slug];
      const more = [p.chains.map(chainName).join(', '), p.age_years === null ? 'listed before 2022' : `live ${Math.floor(p.age_years)}+ yr`,
        p.lost_24m ? `$${(p.lost_24m / 1e6).toFixed(2)}M lost in 2 yr` : 'nothing lost in 2 yr',
        u ? `in the finder: ${u.routes.size} routes, ${[...u.uses].join(', ').toLowerCase()}` : 'not in the finder yet', p.site.replace(/^www\./, '')].join(' · ');
      return `<a class="plat" href="https://${p.site}" target="_blank" rel="noopener noreferrer" title="${more}" style="animation:rise .4s ${Math.min(i, 30) * 0.015}s both">
        <svg class="lg" viewBox="0 0 52 52"><path d="${hex(26, 26, 24)}" fill="#06090f" stroke="url(#gEdge)" stroke-width="1.4"/>
          <clipPath id="pc${i}"><circle cx="26" cy="26" r="15"/></clipPath><text x="26" y="31" text-anchor="middle" style="font:700 14px Inter;fill:#a9b8cc">${p.name[0]}</text>
          <image href="https://icons.llamao.fi/icons/protocols/${p.icon}?w=96" x="11" y="11" width="30" height="30" clip-path="url(#pc${i})"/></svg>
        <div class="n"><b>${p.in_finder ? '<span class="live" title="the finder builds routes from it today"></span>' : ''}${p.name}<em class="cc">${p.chains.length > 1 ? p.chains.length + ' chains' : chainName(p.chains[0])}</em></b>
          <small>${cat(p)} · <i>$${bn(p.tvl)}</i></small></div>
        ${p.audited ? `<svg class="ok" viewBox="0 0 20 20"><title>Audited (DefiLlama)</title><path d="${hex(10, 10, 9)}" fill="rgba(0,255,136,.12)" stroke="#00ff88" stroke-width="1.2"/><path d="M6.4 10.2l2.4 2.4 4.8-5" fill="none" stroke="#00ff88" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/></svg>` : ''}</a>`;
    }).join('');
    $('pfoot').innerHTML = '<span class="live"></span> in the finder today · ✓ audited per DefiLlama, live a year or more, under $1M lost in 2 years · hover a tile for more · Cymetica makes its own selection';
  }

  /* ---------- the Positions tab: the routes started, what is in them now, how far from liquidation, EXIT ----------
     A demo clock (1 s = 1 hour) moves the asset's price on a seeded random walk; the value is the same CM.loop / CM.lp
     arithmetic at that price, plus the route's carry for the hours elapsed. */
  const POS = [];
  let posTimer = null;
  const rng = seed => { let s = seed; return () => (s = (s * 16807) % 2147483647) / 2147483647; };
  const gauss = rnd => Math.sqrt(-2 * Math.log(rnd() || 1e-9)) * Math.cos(2 * Math.PI * rnd());
  const pricedR = r => r.asset === 'ETH' || r.asset === 'BTC';
  function carry(r) {
    const sum = role => r.legs.filter(l => l.role === role).reduce((t, l) => t + l.rate * (l.share || 1), 0);
    return {y: sum('stake') + sum('collateral') + sum('supply') + sum('lp'), b: sum('borrow')};
  }
  function valueOf(pos) {
    const r = pos.r, {y, b} = carry(r), t = pos.hours / 8760, P = pricedR(r) ? pos.P : 1;
    let v;
    if (r.type === 'lp') v = C.lp({kind: 'uniswap', fee: 0, P}) + y / 100 * t;
    else if (r.L > 1) v = C.loop({L: r.L, y: 0, b: 0, lt: r.ltv, bonus: 0.05, P}).value + (r.L * y - (r.L - 1) * b) / 100 * t;
    else v = P * (1 + y / 100 * t);
    return pos.amount * v;
  }
  function stepPos(pos) {
    pos.hours += 1;
    if (pricedR(pos.r)) pos.P *= Math.exp(0.0055 * gauss(pos.rnd) + 0.00025);
    pos.path.push(valueOf(pos));
    if (pos.path.length > 120) pos.path.shift();
  }
  function openPosition(r, tier, amount) {
    const pos = {id: POS.length + 1, r, tier, amount, hours: 0, P: 1, path: [amount], rnd: rng(4242 + POS.length * 7919), closed: null};
    for (let k = 0; k < 72; k++) stepPos(pos);                  // three days of history so the line has a shape
    POS.unshift(pos);
    $('poscount').textContent = POS.filter(p => !p.closed).length;
    return pos;
  }
  const liqLeft = pos => pos.r.pLiq === null ? null : 1 - pos.r.pLiq / (pricedR(pos.r) ? pos.P : 1);
  function gaugeSvg(pos) {
    const left = liqLeft(pos), f = left === null ? 1 : Math.max(0, Math.min(1, left / 0.5));
    const col = left === null || left > 0.3 ? '#00ff88' : left > 0.15 ? '#00cfff' : '#ff4444';
    const arc = (a0, a1) => { const p = a => [110 + 84 * Math.cos(Math.PI * (1 - a)), 110 - 84 * Math.sin(Math.PI * (1 - a))];
      const [x0, y0] = p(a0), [x1, y1] = p(a1); return `M${x0.toFixed(1)} ${y0.toFixed(1)}A84 84 0 0 1 ${x1.toFixed(1)} ${y1.toFixed(1)}`; };
    const what = left === null ? 'NO LIQUIDATION' : `${pos.r.asset === 'USD' ? 'sUSDe' : pos.r.asset} TO LIQUIDATION`;
    return `<svg class="gauge" viewBox="0 0 220 172" id="pg${pos.id}">
      <defs><linearGradient id="gg${pos.id}" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#ff4444"/><stop offset=".45" stop-color="#00cfff"/><stop offset="1" stop-color="#00ff88"/></linearGradient></defs>
      <path d="${arc(0, 1)}" fill="none" stroke="url(#gg${pos.id})" stroke-width="10" stroke-linecap="round" opacity=".22"/>
      <path d="${arc(0, Math.max(0.001, f))}" fill="none" stroke="url(#gg${pos.id})" stroke-width="10" stroke-linecap="round"/>
      ${[0, 0.25, 0.5, 0.75, 1].map(a => { const x = 110 + 98 * Math.cos(Math.PI * (1 - a)), y = 110 - 98 * Math.sin(Math.PI * (1 - a)); return `<circle cx="${x.toFixed(1)}" cy="${y.toFixed(1)}" r="1.5" fill="#7f93ad"/>`; }).join('')}
      <g class="needle" style="transform:rotate(${(f * 180 - 90).toFixed(1)}deg)"><path d="M110 110L110 44" stroke="#e6edf7" stroke-width="2" stroke-linecap="round"/><circle cx="110" cy="110" r="6" fill="#06090f" stroke="#e6edf7" stroke-width="2"/></g>
      <text class="t" x="110" y="150" style="fill:${col}">${left === null ? 'SAFE' : '−' + Math.max(0, Math.round(left * 100)) + '%'}</text>
      <text class="s" x="110" y="168">${what}</text></svg>`;
  }
  function sparkPath(pos) {
    const v = pos.path, lo = Math.min(...v, pos.amount), hi = Math.max(...v, pos.amount), sp = hi - lo || 1;
    const pts = v.map((x, k) => `${(k / (v.length - 1) * 400).toFixed(1)} ${(54 - (x - lo) / sp * 48).toFixed(1)}`);
    const base = (54 - (pos.amount - lo) / sp * 48).toFixed(1);
    return {line: 'M' + pts.join('L'), base};
  }
  function posCard(pos) {
    const r = pos.r, i = idx(pos.tier), t = tierOf(pos.tier), away = awayOf(r);
    const flow = away.length ? `Ethereum → ${away.map(chainName).join(' · ')}` : 'Ethereum';
    const who = `<div class="who">${emblem(i)}<div><h3>${r.label}</h3><div class="ven">${r.venue} · ${flow}</div>
      <div class="chips"><span class="chip ${i === 3 ? 'r' : 'c'}">${t.name.toUpperCase()}</span>${r.L > 1 ? `<span class="chip m">${r.L.toFixed(1)}× LEVERAGE</span>` : ''}
      ${pos.closed ? '' : '<span class="chip g">AI RE-CHECKS EVERY 6 H</span>'}</div></div></div>`;
    if (pos.closed) {
      const d = pos.closed.value - pos.amount;
      return `<div class="frame pos closed">${who}<div class="val"><div class="lbl">RETURNED TO YOUR WALLET</div><b>$${num(pos.closed.value)}</b>
        <div class="pnl ${d >= 0 ? 'up' : 'dn'}">${d >= 0 ? '▲' : '▼'} ${usd(d)} · ${fp(pos.closed.value / pos.amount)}</div></div>
        <div class="closedtag">✓ CLOSED · ${num(pos.amount)} USDC IN, ${num(pos.closed.value)} USDC OUT</div></div>`;
    }
    return `<div class="frame pos" id="pos${pos.id}">${who}
      <div class="val"><div class="lbl">IN THE POOL</div><b id="pv${pos.id}"></b><div class="pnl" id="pp${pos.id}"></div>
        <svg class="spark" viewBox="0 0 400 60" preserveAspectRatio="none"><line id="pb${pos.id}" x1="0" x2="400" stroke="#7f93ad" stroke-dasharray="3 4" stroke-width="1"/>
          <path id="pl${pos.id}" fill="none" stroke-width="2" stroke-linejoin="round" vector-effect="non-scaling-stroke"/></svg>
        <div class="since" id="pt${pos.id}"></div></div>
      <div id="pgw${pos.id}">${gaugeSvg(pos)}</div>
      <div class="px"><button class="exitbtn" data-exit="${pos.id}">EXIT</button><small>everything back to your wallet</small></div></div>`;
  }
  function paintPos(pos) {
    const v = valueOf(pos), d = v - pos.amount, up = d >= 0, sp = sparkPath(pos);
    const vb = $('pv' + pos.id);
    if (!vb) return;
    vb.textContent = '$' + num(v);
    vb.style.color = up ? '#e6edf7' : '#ff4444';
    $('pp' + pos.id).className = 'pnl ' + (up ? 'up' : 'dn');
    $('pp' + pos.id).textContent = `${up ? '▲' : '▼'} ${usd(d)} · ${fp(v / pos.amount)}`;
    $('pl' + pos.id).setAttribute('d', sp.line);
    $('pl' + pos.id).setAttribute('stroke', up ? '#00ff88' : '#ff4444');
    $('pb' + pos.id).setAttribute('y1', sp.base);
    $('pb' + pos.id).setAttribute('y2', sp.base);
    const h = pos.hours;
    $('pt' + pos.id).textContent = `open ${Math.floor(h / 24)}d ${h % 24}h · ${num(pos.amount)} USDC put in`;
    $('pgw' + pos.id).innerHTML = gaugeSvg(pos);
  }
  function renderPositions() {
    const open = POS.filter(p => !p.closed), closed = POS.filter(p => p.closed);
    const inPools = open.reduce((t, p) => t + valueOf(p), 0), put = open.reduce((t, p) => t + p.amount, 0);
    const back = closed.reduce((t, p) => t + p.closed.value, 0);
    $('posstats').innerHTML = [['IN THE POOLS', '$' + num(inPools), inPools >= put ? 'g' : ''], ['OPEN ROUTES', open.length, ''],
      ['RETURNED TO WALLET', '$' + num(back), '']].map(([k, v, c]) => `<div class="${c}"><b>${v}</b><span class="lbl">${k}</span></div>`).join('');
    $('poscount').textContent = open.length;
    $('poslist').innerHTML = POS.length ? POS.map(posCard).join('') : `<div class="frame empty">
      <svg viewBox="0 0 64 64"><path d="${hex(32, 32, 28)}" fill="none" stroke="#1e3050" stroke-width="1.5"/><path d="M24 32h16M32 24v16" stroke="#7f93ad" stroke-width="2" stroke-linecap="round"/></svg>
      <h3>No open routes yet</h3><button class="cta" data-step="1">FIND A STRATEGY</button></div>`;
    open.forEach(paintPos);
  }
  function tickPositions() {
    POS.filter(p => !p.closed && !p.exiting).forEach(p => { stepPos(p); paintPos(p); });
    const open = POS.filter(p => !p.closed), inPools = open.reduce((t, p) => t + valueOf(p), 0);
    const b = $('posstats').querySelector('b');
    if (b) b.textContent = '$' + num(inPools);
  }
  function posTicking(on) {
    if (posTimer) { clearInterval(posTimer); posTimer = null; }
    if (on && !shot) posTimer = setInterval(tickPositions, 1000);
  }

  /* EXIT: the route unwinds node by node, the money flows home, the wallet shows what came back */
  function exitSteps(pos) {
    const r = pos.r, st = r.steps, v = valueOf(pos), away = awayOf(r), out = [];
    const node = (project, t1, t2) => out.push({project, t1, t2});
    if (r.type === 'vaults') st.filter(s => s.kind === 'vault').forEach(s => node(s.project, 'Withdraw', `${num(v * s.share)} USDC`));
    else if (r.type === 'lp') { node(st[2].project, 'Remove liquidity', `${num(v)} USD`); node(st[1].project, 'Swap ETH → USDC', `${num(v / 2)} USD`); }
    else {
      const swap = st.find(s => s.kind === 'swap'), coll = st.find(s => s.kind === 'collateral'), bor = st.find(s => s.kind === 'borrow');
      const tok = r.label.replace(' loop', '').replace('Staked ', '');
      if (bor) {
        node(bor.project, `Repay ${bor.loan}`, `${num(pos.amount * (r.L - 1))} ${bor.loan}`);
        node(coll.project, `Withdraw ${tok}`, `${num(v + pos.amount * (r.L - 1))} USD`);
      }
      node(swap.project, `Swap ${tok} → USDC`, `${num(v)} USDC`);
    }
    if (away.length) out.push({project: 'circle', t1: 'Circle CCTP', t2: `${away.map(chainName).join(' · ')} → Ethereum`});
    out.push({wallet: true, t1: 'Your wallet', t2: `${num(v)} USDC`});
    return out;
  }
  function exitPos(id) {
    const pos = POS.find(p => p.id === id);
    if (!pos || pos.closed) return;
    pos.exiting = true;
    const steps = exitSteps(pos), v = valueOf(pos), n = steps.length, W = 1100, gap = W / n, y = 92;
    const xs = steps.map((_, k) => gap / 2 + k * gap);
    const nodes = steps.map((s, k) => {
      const x = xs[k], logo = s.wallet ? '' : `<clipPath id="xc${k}"><circle cx="${x}" cy="${y}" r="17"/></clipPath>
        <text x="${x}" y="${y + 5}" text-anchor="middle" style="font:700 14px Inter;fill:#a9b8cc">${(s.project === 'circle' ? 'C' : pname(s.project)[0])}</text>
        <image href="${s.project === 'circle' ? 'https://icons.llamao.fi/icons/protocols/circle?w=96' : icon(s.project)}" x="${x - 17}" y="${y - 17}" width="34" height="34" clip-path="url(#xc${k})"/>`;
      const body = s.wallet ? `<circle cx="${x}" cy="${y}" r="32" fill="#06090f" stroke="#3b82f6" stroke-width="1.6"/>
        <rect x="${x - 15}" y="${y - 11}" width="30" height="22" rx="4" fill="none" stroke="#00cfff" stroke-width="2"/><path d="M${x + 6} ${y}h9" stroke="#00cfff" stroke-width="2" stroke-linecap="round"/>`
        : `<path class="hx" d="${hex(x, y, 32)}"/>${logo}`;
      return `<g class="xn" data-x="${k}">${body}
        <g class="ok"><circle cx="${x + 24}" cy="${y - 24}" r="9" fill="#00ff88"/><path d="M${x + 20} ${y - 24}l3 3 5-6" fill="none" stroke="#06090f" stroke-width="2" stroke-linecap="round"/></g>
        <text class="xt" x="${x}" y="${y + 58}">${s.t1}</text><text class="xs" x="${x}" y="${y + 76}">${s.t2}</text></g>`;
    }).join('');
    const links = xs.slice(1).map((x, k) => `<line class="lk" data-l="${k}" x1="${xs[k] + 34}" y1="${y}" x2="${x - 34}" y2="${y}"/>`).join('');
    const ov = $('exitov');
    ov.innerHTML = `<div class="exbox"><div class="eyebrow" style="color:#ff4444">EXITING</div><h2>${pos.r.label} <em>→</em> your wallet</h2>
      <svg class="exrail" viewBox="0 0 ${W} 190">${links}${nodes}
        <g class="orb" id="orb" style="transform:translate(${xs[0] - 90}px,${y}px)"><circle r="26" fill="#00ff88" opacity=".14"/><circle r="12" fill="#00ff88" opacity=".35"/><circle r="6" fill="#e6edf7"/></g></svg>
      <div class="excount"><div class="pool"><div class="lbl">IN THE POOL</div><b id="exPool" data-v="${v}">$${num(v)}</b></div><div class="arr">→</div>
        <div class="wal"><div class="lbl">IN YOUR WALLET</div><b id="exWal" data-v="0">$0</b></div></div>
      <ol class="exsteps">${steps.map((s, k) => `<li data-s="${k}">${k + 1} · ${s.t1}</li>`).join('')}</ol></div>`;
    ov.classList.add('on');
    const step = 900;
    steps.forEach((s, k) => later(500 + k * step, () => {
      $('orb').style.transform = `translate(${xs[k]}px,${y}px)`;
      later(650, () => {
        const g = ov.querySelector(`[data-x="${k}"]`);
        if (!g) return;
        g.classList.add('on');
        g.insertAdjacentHTML('beforeend', `<circle class="burst" cx="${xs[k]}" cy="${y}" r="32"/>`);
        if (k) ov.querySelector(`[data-l="${k - 1}"]`).classList.add('on');
        ov.querySelector(`[data-s="${k}"]`).classList.add('on');
        const left = v * (1 - (k + 1) / n);
        tween($('exPool'), left, x => '$' + num(x), 500);
        tween($('exWal'), v - left, x => '$' + num(x), 500);
      });
    }));
    later(500 + n * step + 700, () => {
      pos.closed = {value: v};
      pos.exiting = false;
      const d = v - pos.amount;
      ov.innerHTML = `<div class="exbox final"><span class="ringfx"></span><span class="ringfx b"></span>
        <div class="eyebrow" style="color:#00ff88">EXIT COMPLETE</div>
        <svg class="wallet" viewBox="0 0 64 64" style="margin-top:22px"><path d="${hex(32, 32, 29)}" fill="#06090f" stroke="#00ff88" stroke-width="2"/>
          <rect x="17" y="22" width="30" height="21" rx="4" fill="none" stroke="#00ff88" stroke-width="2.2"/><path d="M38 32.5h9" stroke="#00ff88" stroke-width="2.2" stroke-linecap="round"/></svg>
        <div class="big2"><span id="finV" data-v="0">0</span><small>USDC</small></div>
        <div class="res ${d >= 0 ? 'up' : 'dn'}">${d >= 0 ? '▲' : '▼'} ${usd(d)} · ${fp(v / pos.amount)} on ${num(pos.amount)} USDC</div>
        <div class="where">in your wallet on Ethereum · nothing left in any pool</div>
        <button class="cta" data-done="1">DONE</button></div>`;
      tween($('finV'), v, num, 1100);
    });
  }

  /* ---------- the mark, large ---------- */
  function renderLogo() {
    const mark = $('mark').outerHTML.replace(' id="mark"', '');
    $('sheet').innerHTML = `${mark.replace('<svg', '<svg class="bigmark"')}<div><div class="eyebrow">BY CYMETICA</div>
      <div class="wm" style="margin-top:14px">CAPITAL <em>MAXIMIZER</em></div>
      <div class="sizes">${[96, 48, 24].map(z => `<div>${mark.replace('<svg', `<svg style="width:${z}px;height:${z}px"`)}<br>${z}px</div>`).join('')}</div></div>`;
  }

  /* ---------- navigation ---------- */
  function setTab(tab) {
    S.tab = tab;
    document.querySelectorAll('#tabs button').forEach(b => b.classList.toggle('on', b.dataset.tab === tab));
    $('maxtab').style.display = tab === 'max' ? '' : 'none';
    $('vp').classList.toggle('on', tab === 'platforms');
    $('vpos').classList.toggle('on', tab === 'positions');
    if (tab === 'platforms') renderPlatforms();
    if (tab === 'positions') renderPositions();
    posTicking(tab === 'positions');
  }
  function go(n) {
    if (!can(n)) return;
    stop();
    S.step = n;
    setTab('max');
    document.querySelectorAll('#maxtab .view').forEach(v => v.classList.toggle('on', v.id === 'v' + n));
    renderRail();
    if (n === 1) renderTiers();
    if (n === 2) renderAmount();
    if (n === 3) renderStrategies();
    if (n === 4) renderPlan();
    if (!shot) scrollTo({top: 0, behavior: 'smooth'});
  }

  document.addEventListener('click', e => {
    const el = sel => e.target.closest(sel);
    if (el('[data-tab]')) { const t = el('[data-tab]').dataset.tab; return t === 'max' ? go(S.step) : setTab(t); }
    if (el('[data-step]') && !el('[data-step]').disabled) return go(+el('[data-step]').dataset.step);
    if (el('[data-tier]')) { const t = el('[data-tier]').dataset.tier; if (t !== S.tier) S.foundFor = null; S.tier = t; S.started = false; return go(2); }
    if (el('[data-amt]')) { S.amount = +el('[data-amt]').dataset.amt; $('amt').value = num(S.amount); return updatePreview(); }
    if (el('#find')) return go(3);
    if (el('[data-act]')) { const b = el('[data-act]'), k = +b.dataset.col; return tuneCol(k, S.picks[k].L + (b.dataset.act === 'inc' ? 0.5 : -0.5)); }
    if (el('[data-pick]')) { S.pick = +el('[data-pick]').dataset.pick; S.started = false; return go(4); }
    if (el('#start')) {
      S.started = true;
      $('go4').classList.add('started');
      openPosition(S.picks[S.pick], S.tier, S.amount);
      return later(1100, () => setTab('positions'));
    }
    if (el('[data-exit]')) return exitPos(+el('[data-exit]').dataset.exit);
    if (el('[data-done]')) { $('exitov').classList.remove('on'); return renderPositions(); }
    if (el('[data-filter]')) { S.filter = el('[data-filter]').dataset.filter; return renderPlatforms(); }
    if (el('[data-chain]')) { S.chain = el('[data-chain]').dataset.chain; return renderPlatforms(); }
    if (el('[data-morechains]')) { S.allChains = true; return renderPlatforms(); }
    if (el('#home')) return go(1);
  });
  document.addEventListener('input', e => {
    if (e.target.id === 'lev') tuneCol(S.pick, +e.target.value);
    if (e.target.id === 'amt') { S.amount = +e.target.value.replace(/[^\d.]/g, '') || 0; updatePreview(); renderRail(); }
  });
  $('amt').addEventListener('blur', e => { if (S.amount > 0) e.target.value = num(S.amount); });
  $('amt').addEventListener('keydown', e => { if (e.key === 'Enter' && S.amount > 0) go(3); });

  $('pcount').textContent = D.platforms.length;
  if (q.has('logo')) {
    $('maxtab').style.display = 'none';
    $('vlogo').classList.add('on');
    renderLogo();
  } else {
    if (tierOf(q.get('tier'))) S.tier = q.get('tier');
    if (q.has('amount')) S.amount = +q.get('amount');
    const step = Math.max(1, Math.min(4, +q.get('step') || 1));
    if (step >= 3 && S.tier) {
      S.picks = C.top3(S.tier); S.foundFor = S.tier;
      S.pick = Math.min(2, +q.get('pick') || 0);
      if (q.has('lev') && C.range(S.picks[S.pick], S.tier)) S.picks[S.pick] = C.tune(S.picks[S.pick], +q.get('lev'));
    }
    if (q.get('tab') === 'platforms') { go(1); setTab('platforms'); }
    else if (q.get('tab') === 'positions') {                     // opened straight: one demo route to look at
      const t = S.tier || 'high', r = C.top3(t)[0];
      openPosition(q.has('lev') && C.range(r, t) ? C.tune(r, +q.get('lev')) : r, t, S.amount);
      go(1);
      setTab('positions');
      if (q.has('exit')) exitPos(1);
    } else go(step);
  }
})();
