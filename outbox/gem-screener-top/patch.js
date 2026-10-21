// Gem Screener patch, the part CSS cannot do. Everything shown comes from the page itself: each card's own text,
// and the Holders-paid smiley the Apps table already shows beside the same project's name.
(() => {
  // the header's light starts at the gem: the logo sits at x=32 at 1440 px and further right on wide screens
  const logo = document.querySelector('.gs-logo img'), hd = document.querySelector('header.top');
  if (logo && hd) hd.style.setProperty('--logo-x', Math.round(logo.getBoundingClientRect().left) + 'px');

  // the top background ends where the content starts: "Degen picks" on Top Picks, the table on Apps and Chains
  const view = document.querySelector('.view.active');
  const end = view && (view.id === 'view-start'
    ? [...view.querySelectorAll('.st-h')].find(h => /degen picks/i.test(h.textContent))
    : view.querySelector('table'));
  const shell = document.querySelector('.shell');
  if (end && shell) shell.style.setProperty('--gs-top',
    Math.round(end.getBoundingClientRect().top - shell.getBoundingClientRect().top) + 'px');

  // the table's smileys, by project name
  const icons = {};
  document.querySelectorAll('#tbl-apps tbody tr').forEach(r => {
    const nm = r.querySelector('.nm'); const ic = r.querySelectorAll('.nmicon');
    if (nm && ic.length) icons[nm.textContent.trim()] = [...ic].map(i => i.cloneNode(true));
  });

  const esc = s => s.replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  const short = [ // the "Watch out" sentence, cut into its parts
    [/the theme has lagged BTC over the last month/i, () => 'theme lags BTC'],
    [/only (\d+) days of history/i, m => m[1] + ' days of history'],
    [/the business is no longer growing/i, () => 'not growing'],
  ];

  document.querySelectorAll('#startCards .dcard').forEach(card => {
    if (card.querySelector('.gs-stats')) return;
    const name = (card.querySelector('.dc-name b') || {}).textContent || '';
    (icons[name.trim()] || []).forEach(i => card.querySelector('.dc-name b').appendChild(i));

    const fdv = [...card.querySelectorAll('.dc-fdv:not(.dc-size-note)')].map(e => e.textContent).join(' ');
    const out = (fdv.match(/(\d+)% of tokens out/) || [])[1];
    const whys = [...card.querySelectorAll('.dc-why .why')];
    let rev = null, hold = null; const tags = [];
    whys.forEach(w => {
      const t = w.textContent.trim(); let m;
      if ((m = t.match(/^revenue ([+-]\d+%) a month$/))) rev = m[1];
      else if ((m = t.match(/^(\d+)% of revenue to holders$/))) hold = m[1] + '%';
      else tags.push(`<i class="${w.classList.contains('na') ? 'n' : ''}" ${w.dataset.tip ? `title="${esc(w.dataset.tip)}"` : ''}>${esc(t
        .replace(/^revenue rising in the .* theme$/, 'theme revenue rising'))}</i>`);
    });
    const exit = (card.querySelector('.dc-exit') || {}).textContent || '';
    short.forEach(([re, f]) => { const m = exit.match(re); if (m) tags.push(`<i class="w" title="${esc(exit)}">${esc(f(m))}</i>`); });

    const stats = document.createElement('div');
    stats.className = 'gs-stats';
    stats.innerHTML =
      `<div><b>${out ? out + '%' : '—'}</b><span>tokens out</span></div>` +
      `<div><b class="${rev ? 'g' : 'na'}">${rev || '—'}</b><span>revenue / mo</span></div>` +
      `<div><b class="${hold ? 'g' : 'na'}">${hold || '—'}</b><span>to holders</span></div>`;
    const tg = document.createElement('div');
    tg.className = 'gs-tags';
    tg.innerHTML = tags.join('');
    card.querySelector('.dc-pot').after(stats, tg);
  });

  // Supply: "—" says what it is, and a dilution that rounds to 0.0 but is not zero reads "<0.1%"
  document.querySelectorAll('.supcell').forEach(s => {
    const n = s.querySelector('.spn'); if (!n) return;
    const t = n.textContent.trim();
    if (t === '—') n.textContent = 'n/a';
    else if (/^\+0\.0%$/.test(t) && !/^0 new /.test(s.dataset.tip || '')) n.textContent = '<0.1%';
  });
})();
