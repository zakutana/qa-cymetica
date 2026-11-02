// The Supply Analyzer request on their live Gem Screener: this goes inside their page script, before its first render. The batch
// already carries the other sources (serve.py overlay); here the gate reads them, and the column, tooltip and Next unlock say so.
{
  const N = n => `<span class="gt-n">${n}</span>`;
  const SOURCES_READ = 'DeFiLlama, the project’s vesting contracts, Tokenomist and DropsTab';

  // ---- 3 the gate reads the figures, its rule unchanged: a pick can leave, the next by upside comes in
  const LINE = (DEGEN.rules || {}).dilution_12m_red_pct || 25;
  const left = [];
  Object.keys(SA_MOCK.sources).forEach(slug => {
    const e = APPS.find(a => a.slug === slug), s = SA_MOCK.sources[slug];
    if (!e) return;
    e.sa_dilution_12m_pct = s.pct;
    if (s.pct < LINE) return;
    e.degen_fail = (e.degen_fail || []).concat(['heavy dilution']);
    if (e.degen_ok) { e.degen_ok = false; left.push(e); }
  });
  if (left.length) {
    const ok = APPS.filter(a => a.degen_ok).sort((a, b) => (b.potential || 0) - (a.potential || 0));
    DEGEN.shortlist = ok.slice(0, (DEGEN.rules || {}).shortlist || 10).map(a => a.key || a.slug);
    DEGEN.n_ok = ok.length;
    if (DATA.degen_gates) DATA.degen_gates.picks = ok.length;
    const near = (DEGEN.near || []).concat(left.map(e => e.key || e.slug));
    DEGEN.near = near.map(k => APPS.find(a => (a.key || a.slug) === k)).filter(Boolean)
      .sort((a, b) => (b.potential || 0) - (a.potential || 0)).slice(0, 6).map(a => a.key || a.slug);
  }

  // ---- 9 the column says what its number is; the panel's Supply card keeps its name, it holds the whole supply
  [COLS_APPS, COLS_CHAINS].forEach(list => list.forEach(c => { if (c.key === 'supply') { c.label = 'Dilution 12M'; c.en = 'Dilution 12M'; } }));

  // ---- 4-8 the Supply column
  const finished = e => {
    const when = SA_MOCK.finished[e.slug];
    return when ? {when, none: (e.unlock || {}).tbd_pct} : null;
  };
  const oldCell = supplyCell;
  supplyCell = function (e) {
    const sp = supplyOf(e);
    if (!sp || isChainsView()) return oldCell(e);
    const d = saDil(sp);
    if (d && d.at_max) return `<span class="supcell v-good tipme"${tipAttrs('Dilution, 12 months: 0%', 'Max supply is reached: no more tokens can come out.')}>${saPie(sp, 22)}<span class="spn">${N(5)}0%</span></span>`;
    if (d && d.source) return `<span class="supcell v-bad tipme"${tipAttrs('Dilution, 12 months ' + saPct(d.pct), saDilLine(sp, e.symbol) + ', to ' + d.until + '. Source: ' + d.source + ', read ' + SA_MOCK.read + '.')}>${saPie(sp, 22)}<span class="spn">${N(e.slug === 'lombard' ? 8 : 1)}${saPct(d.pct)}</span></span>`;
    if (d) return oldCell(e);
    const done = finished(e), drop = SA_MOCK.dropstab[e.slug];
    let say, mark = 7;
    if (done && Math.abs(done.none) === 0 && done.none !== null && done.none !== undefined) {
      return `<span class="supcell v-good tipme"${tipAttrs('Dilution, 12 months: 0%', 'The published schedule finished in ' + done.when + ' and covered the whole supply.')}>${saPie(sp, 22)}<span class="spn">${N(6)}0%</span></span>`;
    }
    if (done) {
      mark = 6;
      say = `The published schedule finished in ${done.when}.` + (done.none ? ` ${done.none}% of the supply never had one.` : '') + ' Nothing is assumed for the rest.';
    } else if (drop) {
      mark = 1;
      say = 'Schedule found on DropsTab' + (drop.next ? `, next unlock ${dayOf(drop.next.ts)}: ${saTok(drop.next.tokens)} ${e.symbol} to ${drop.next.who}` : '') + '. The 12-month figure comes with the build.';
    } else {
      say = `No schedule found on ${SOURCES_READ}. Nothing is assumed.`;
    }
    return `<span class="supcell v-na tipme"${tipAttrs('Dilution, 12 months: ' + (done ? 'schedule finished' : drop ? 'on DropsTab' : 'unknown'), say)}><span class="sa-ring" aria-hidden="true"></span><span class="spn">${N(mark)}n/a</span></span>`;
  };

  // ---- 2 the card's Next unlock row names its source; 6-7 what it says when there is no figure
  const oldNext = saNextRow;
  saNextRow = function (sp, sym) {
    const html = oldNext(sp, sym), t = (sp && sp.tiles && sp.tiles.next_unlock_row) || {};
    const slug = ((sp && sp.token) || {}).slug, done = SA_MOCK.finished[slug], drop = SA_MOCK.dropstab[slug];
    if (t.source) return html.replace('</div>', '') + `<span class="sa-src">${N(2)}Source: ${esc(t.source)}, read ${esc(SA_MOCK.read)}</span></div>`;
    const swap = text => html.replace(/No vesting or unlock schedule on any feed we read; nothing is assumed in its place\./, text).replace(/The schedule on file has no tranche ahead\./, text);
    if (t.at_max) return swap('Max supply is reached: no more tokens can come out.');
    if (done) return swap(`The published schedule finished in ${done}.`);
    if (drop) return swap('Schedule found on DropsTab; the figure comes with the build.');
    return swap(`No schedule found on ${SOURCES_READ}. Nothing is assumed.`);
  };

  // ---- 10 the Supply card: the whole supply as one donut, from the figures the tiles already hold
  function donutParts(sp) {
    const T = (sp && sp.tiles) || {}, sl = saSlices(sp), whole = (T.circulating || {}).of, d = saDil(sp);
    // What is out is the Circulating tile's figure. Their pie's vesting and paid-out slices are next year's tokens, not out yet,
    // so they are counted once, under "coming in 12 months"; a burned token is not in the supply at all.
    const out = (T.circulating || {}).tokens || (sl.free + sl.staked_free + sl.staked_locked);
    const staked = Math.min(sl.staked_free + sl.staked_locked, out), kept = Math.min(sl.bb_kept, out - staked);
    const parts = [
      // "free to sell" is a claim about staking: where staking is unknown it says only what is known
      {k: 'free', label: (sp.unknown_names || []).includes('staking') ? 'In circulation' : 'Free to sell', v: out - staked - kept, c: 'var(--accent)'},
      {k: 'staked', label: 'Staked', v: staked, c: 'var(--band-blue)'},
      {k: 'bought', label: 'Bought back, kept', v: kept, c: 'var(--good)'},
    ].filter(p => p.v > 0);
    if (!whole || whole <= out * 1.001) return {parts, out, whole: whole || null, open: !whole};
    const rest = whole - out;
    if (d) {
      const soon = Math.min(d.new_tokens_12m || 0, rest);
      if (soon > 0) parts.push({k: 'soon', label: 'Coming in 12 months', v: soon, c: 'var(--bad)'});
      if (rest - soon > 0) parts.push({k: 'later', label: 'After that, or never issued', v: rest - soon, c: 'var(--line, #2a3648)', ghost: true});
    } else {
      const ended = SA_MOCK.finished[((sp && sp.token) || {}).slug];
      parts.push({k: 'unknown', label: ended ? 'Not out, schedule finished' : 'Not out yet, no schedule', v: rest, c: 'var(--muted)', dashed: true});
    }
    return {parts, out, whole};
  }
  // One pie in a tile: the ring, its figure in the centre, the legend under it. Each part is {label, v, c, shown?, dashed?}.
  function pie(parts, center, sub, tone, note) {
    const total = parts.reduce((n, p) => n + p.v, 0), R = 44, W = 15, C = 2 * Math.PI * R;
    let at = 0;
    const arcs = !total ? `<circle cx="60" cy="60" r="${R}" fill="none" stroke="var(--muted)" stroke-width="${W}" style="stroke-dasharray:3 3;opacity:.55"/>` : parts.map(p => {
      const len = C * p.v / total, gap = parts.length > 1 ? Math.min(1.5, len / 3) : 0;
      const dash = p.dashed ? 'style="stroke-dasharray:3 3;opacity:.55"' : `stroke-dasharray="${(len - gap).toFixed(2)} ${(C - len + gap).toFixed(2)}"`;
      const arc = `<circle cx="60" cy="60" r="${R}" fill="none" stroke="${p.c}" stroke-width="${W}" ${dash} stroke-dashoffset="${(-at).toFixed(2)}"/>`;
      at += len;
      return arc;
    }).join('');
    const rows = parts.map(p => `<li><i style="background:${p.c}${p.dashed ? ';opacity:.55' : ''}"></i><span>${esc(p.label)}</span><b>${esc(p.shown || saTok(p.v))}</b></li>`).join('');
    return `<div class="sa-ringbox"><svg viewBox="0 0 120 120" role="img">${arcs}</svg><div class="sa-center ${tone || ''}"><b>${center}</b>${sub ? `<span>${esc(sub)}</span>` : ''}</div></div><ul class="sa-legend">${rows}</ul>${note ? `<p class="sa-note">${esc(note)}</p>` : ''}`;
  }
  const FILL = {'v-bad': 'var(--bad)', 'v-good': 'var(--good)', 'v-caution': 'var(--band-blue)'};
  function circPie(sp) {
    const {parts, out, whole, open} = donutParts(sp), c = (sp.tiles || {}).circulating || {};
    if (!parts.length) return pie([], 'n/a', '', 'v-na', 'No circulating supply on any feed we read.');
    const pct = typeof c.pct === 'number' ? c.pct : (whole ? 100 * out / whole : null);
    return pie(parts, pct === null ? esc(saTok(out)) : (pct >= 99.95 ? '100%' : pct.toFixed(1) + '%'), pct === null ? 'out' : 'is out', '', open ? 'No max supply: what is still to come cannot be drawn.' : '');
  }
  function fdvPie(sp) {
    const f = (sp.tiles || {}).fdv;
    if (!f || !f.market_cap_usd || !f.fdv_usd) return pie([], 'n/a', '', 'v-na', 'No market cap stated.');
    const cap = Math.min(f.market_cap_usd, f.fdv_usd), cls = saFdvCls(f.x);
    return pie([{label: 'Market cap', v: cap, c: 'var(--accent)', shown: saUsd(f.market_cap_usd)},
      {label: 'Rest of FDV', v: Math.max(f.fdv_usd - cap, 0), c: FILL[cls] || 'var(--line, #2a3648)', shown: saUsd(f.fdv_usd - cap)}], f.x.toFixed(1) + '×', 'FDV to cap', cls);
  }
  function dilPie(sp, e) {
    const d = saDil(sp), circ = ((sp.tiles || {}).circulating || {}).tokens, done = finished(e), drop = SA_MOCK.dropstab[e.slug];
    const here = [{label: 'In circulation now', v: circ || 0, c: 'var(--accent)'}];
    if (!d && done && done.none !== null && done.none !== undefined && Math.abs(done.none) === 0) {
      return pie(here, '0%', '12 months', 'v-good', `The published schedule finished in ${done.when} and covered the whole supply.`);
    }
    if (!d) {
      const say = done ? `The published schedule finished in ${done.when}.` + (done.none ? ` ${done.none}% of the supply never had one.` : '')
        : drop ? 'Schedule found on DropsTab; the figure comes with the build.' : 'No schedule found on any source. Nothing is assumed.';
      return pie([], 'n/a', '', 'v-na', say);
    }
    const cls = saDilCls(d.pct), fresh = d.new_tokens_12m || (circ ? circ * d.pct / 100 : 0), parts = here.slice();
    if (fresh > 0) parts.push({label: 'New in 12 months', v: fresh, c: FILL[cls] || 'var(--bad)'});
    return pie(parts, d.at_max ? '0%' : saColPct(d.pct), '12 months', cls, d.at_max ? 'Max supply is reached.' : saDilLine(sp, e.symbol));
  }
  const oldSupplyCard = supplyCard;
  supplyCard = function (e) {
    const html = oldSupplyCard(e), sp = supplyOf(e);
    if (!sp || !sp.tiles) return html;
    const box = document.createElement('div');
    box.innerHTML = html;
    const fill = (key, inner, mark) => {
      const tile = box.querySelector(`.satile[data-k="${key}"]`);
      if (!tile) return;
      const head = tile.querySelector('.sk');
      tile.innerHTML = '';
      tile.appendChild(head);
      tile.classList.add('sa-pie');
      tile.insertAdjacentHTML('beforeend', inner + mark);
    };
    fill('circ', circPie(sp), N(10));
    fill('fdv', fdvPie(sp), '');
    fill('dil', dilPie(sp, e), '');
    return box.innerHTML;
  };

  // ---- the box: where each one is. Ours only, it never goes in a picture for them
  function row(slug) { return document.querySelector(`#tbl-apps tbody tr[data-id="${(APPS.find(a => a.slug === slug) || {}).key}"]`); }
  function flash(el) {
    if (!el) return;
    el.scrollIntoView({block: 'center', behavior: 'smooth'});
    el.classList.add('gt-flash');
    setTimeout(() => el.classList.remove('gt-flash'), 2400);
  }
  const closeIt = () => { if (document.getElementById('panel').classList.contains('open')) closePanel(); };
  // all apps, with the revenue floor off: Lombard is under it
  const inApps = slug => {
    closeIt(); setView('apps'); setTrustMode('all');
    const floor = document.getElementById('floorRange');
    if (floor) { floor.value = 0; floor.dispatchEvent(new Event('input', {bubbles: true})); }
    setTimeout(() => { const r = row(slug); flash(r && r.querySelector('.supcell')); }, 300);
  };
  const firstMax = () => (APPS.find(a => { const s = supplyOf(a), d = saDil(s); return d && d.at_max; }) || {}).slug;
  const firstNone = () => (APPS.find(a => { const s = supplyOf(a); return s && !saDil(s) && !SA_MOCK.finished[a.slug] && !SA_MOCK.dropstab[a.slug]; }) || {}).slug;
  const STEPS = [
    [1, 'Column: Collector Crypt reads +39%', () => inApps('collector-crypt')],
    [2, 'Card: Next unlock names its source', () => { setView('start'); openPanel((APPS.find(a => a.slug === 'collector-crypt') || {}).key); setTimeout(() => flash(document.querySelector('#panel .sa-src')), 1500); }],
    [3, 'Top Picks: Collector Crypt out, Rhea in', () => { closeIt(); setView('start'); setTimeout(() => flash(document.getElementById('startNear')), 100); }],
    [4, 'Column: no figure, dashed ring', () => inApps(firstNone())],
    [5, 'Column: max supply reached, 0%', () => inApps(firstMax())],
    [6, 'Column: Jupiter, schedule finished', () => inApps('jupiter')],
    [7, 'Column: where it looked', () => inApps(firstNone())],
    [8, 'Column: Lombard reads its schedule', () => inApps('lombard')],
    [10, 'Supply card: three pies in place of the tiles', () => { setView('start'); openPanel((APPS.find(a => a.slug === 'up') || {}).key); setTimeout(() => flash(document.querySelector('#panel #supplyCard')), 1500); }],
  ];
  setTimeout(() => {
    const box = document.createElement('aside');
    box.id = 'gtTour';
    box.innerHTML = `<header><span>Supply Analyzer, click one, hover the cell</span><span><button id="gtClean">numbers off</button> <button id="gtMin">–</button></span></header>
      <ol>${STEPS.map(([n, t]) => `<li data-n="${n}">${N(n)}<span>${esc(t)}</span></li>`).join('')}</ol>`;
    document.body.appendChild(box);
    box.querySelectorAll('li[data-n]').forEach(li => {
      li.onclick = () => {
        box.querySelectorAll('li').forEach(x => x.classList.remove('on'));
        li.classList.add('on');
        STEPS.find(s => String(s[0]) === li.dataset.n)[2]();
      };
    });
    box.querySelector('#gtMin').onclick = () => box.classList.toggle('min');
    box.querySelector('#gtClean').onclick = () => document.body.classList.add('gt-clean');
  }, 0);
  window.saPeek = () => ({apps: APPS, degen: DEGEN, sup: supplyOf, saDil});
}
