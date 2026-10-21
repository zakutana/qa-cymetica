// Gem Screener, Top Picks: "Live Gem Revenue Generating Tier List", a section before "Degen picks". Drawn from the page's
// own Apps table (its default set: vetted apps with $100K+ revenue in 30 days) and its own Degen picks; each icon opens the
// same side panel a row of that table opens, by that row's own click. Nothing is computed that the page does not already hold
// except the tier an app falls in.
(() => {
  const view = document.getElementById('view-start');
  const anchor = view && [...view.querySelectorAll('.st-h')].find(h => /degen picks/i.test(h.textContent));
  if (!anchor || view.querySelector('.gt-wrap')) return;

  const upside = r => {
    for (const c of [...r.children].reverse()) {
      const m = (c.textContent || '').trim().match(/^([\d.,]+)x$/);
      if (m) return parseFloat(m[1].replace(/,/g, ''));
    }
    return null;
  };
  const cell = (r, i) => ((r.children[i] || {}).innerText || '').replace(/\s+/g, ' ').trim();
  const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));

  const picks = new Set([...document.querySelectorAll('#startCards .dcard')].map(c => c.dataset.id));
  const apps = [...document.querySelectorAll('#tbl-apps tbody tr')].map(r => ({
    row: r, id: r.dataset.id, name: (r.querySelector('.nm') || {}).textContent || '', sym: (r.querySelector('.sym') || {}).textContent || '',
    logo: (r.querySelector('img.ico') || {}).src || '', up: upside(r), cap: cell(r, 4), rev: cell(r, 5),
  })).filter(a => a.up !== null);

  // S: the Degen picks. The rest by upside, the bands the operator drew: 10x+, 5 to 10x, 2 to 5x, 1 to 2x, under 1x.
  const TIERS = [
    {k: 's', letter: 'S', sub: 'picks', test: a => picks.has(a.id)},
    {k: 'a', letter: 'A', sub: '10x+', test: a => a.up >= 10},
    {k: 'b', letter: 'B', sub: '5 to 10x', test: a => a.up >= 5},
    {k: 'c', letter: 'C', sub: '2 to 5x', test: a => a.up >= 2},
    {k: 'd', letter: 'D', sub: '1 to 2x', test: a => a.up >= 1},
    {k: 'f', letter: 'F', sub: 'under 1x', test: () => true},
  ];
  const MAX = 24; // two rows at the widths of the pictures; the lowest upside beyond it folds into one "+N" tile
  const used = new Set();
  const rows = TIERS.map(t => {
    const list = apps.filter(a => !used.has(a.id) && t.test(a)).sort((x, y) => y.up - x.up);
    list.forEach(a => used.add(a.id));
    return {...t, list};
  });

  const fmt = u => (u >= 100 ? Math.round(u) : u >= 10 ? Math.round(u) : u >= 1 ? u.toFixed(1) : u.toFixed(2).replace(/0+$/, '')) + 'x';
  // the upside shows under the symbol in the three top tiers, where the apps are few and the number is the point
  const tile = (a, k) => `<button type="button" class="gt-app tipme" data-id="${esc(a.id)}" data-tipb="${esc(a.name)}"
      data-tip="${esc(fmt(a.up))} upside · market cap ${esc(a.cap)} · revenue ${esc(a.rev)} in 30 days" aria-label="${esc(a.name)}, ${esc(fmt(a.up))} upside">
      <img src="${esc(a.logo)}" alt="" width="64" height="64" decoding="async"><span>${esc(a.sym)}</span>${'sab'.includes(k) ? `<em class="gt-x">${esc(fmt(a.up))}</em>` : ''}</button>`;

  const html = rows.map(t => {
    const shown = t.list.slice(0, MAX), more = t.list.length - shown.length;
    return `<div class="gt-row gt-${t.k}"><div class="gt-lab"><b>${t.letter}</b><span>${t.k === 's' ? '<i class="gt-gem"></i>' : ''}${esc(t.sub)}</span></div>
      <div class="gt-ico">${shown.map(a => tile(a, t.k)).join('')}${more > 0 ? `<button type="button" class="gt-more" data-go="apps">+${more}</button>` : ''}${t.list.length ? '' : '<em>none today</em>'}</div></div>`;
  }).join('');

  // one thin bar of how the apps fall into the tiers, segments as wide as the tiers are full
  const dist = rows.map(t => `<i class="gt-seg gt-${t.k}" style="flex-grow:${Math.max(t.list.length, 0.6)}" title="${t.letter}: ${t.list.length}"></i>`).join('');

  const wrap = document.createElement('section');
  wrap.className = 'gt-wrap';
  wrap.setAttribute('aria-label', 'Gem Tier List');
  wrap.innerHTML = `<h3 class="st-h">Live ranking</h3>
    <div class="dp-head"><h2 class="lb-title"><i class="gt-live"></i>Gem Tier List</h2></div>
    <div class="gt-subrow"><div class="gt-sub"><b>${apps.length}</b> vetted apps · <b>$100K+</b> revenue in 30 days · ranked by upside</div><div class="gt-dist">${dist}</div></div>
    <div class="gt-tiers">${html}</div>`;
  anchor.before(wrap);

  // a click on an icon is a click on that app's row in the Apps table: the same side panel opens
  const byId = new Map(apps.map(a => [a.id, a]));
  wrap.addEventListener('click', e => {
    const more = e.target.closest('.gt-more');
    if (more) { const tab = document.querySelector('a[href*="view=apps"], [data-view="apps"]'); if (tab) tab.click(); return; }
    const b = e.target.closest('.gt-app');
    const a = b && byId.get(b.dataset.id);
    if (a) a.row.click();
  });
})();
