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
  const oldStart = renderStart;
  renderStart = function () {
    oldStart();
    const title = document.getElementById('startTitle');
    if (title && left.length && !document.getElementById('saLeft')) {
      const s = SA_MOCK.sources[left[0].slug];
      title.insertAdjacentHTML('afterend', `<p class="gt-line" id="saLeft">${N(3)}<b>${esc(left[0].name)}</b> left the picks: +${s.pct}% new tokens in 12 months, over the ${LINE}% line. Schedule from ${esc(s.source)}, read ${esc(SA_MOCK.read)}.</p>`);
    }
  };

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
    [3, 'Top Picks: Collector Crypt out, Rhea in', () => { closeIt(); setView('start'); setTimeout(() => flash(document.getElementById('saLeft')), 100); }],
    [4, 'Column: no figure, dashed ring', () => inApps(firstNone())],
    [5, 'Column: max supply reached, 0%', () => inApps(firstMax())],
    [6, 'Column: Jupiter, schedule finished', () => inApps('jupiter')],
    [7, 'Column: where it looked', () => inApps(firstNone())],
    [8, 'Column: Lombard reads its schedule', () => inApps('lombard')],
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
