// Gem Screener, Top Picks: each Degen pick card shows why it is a pick -- the figure behind each of the six gates, beside
// that gate's own bar, with a mini chart of its monthly revenue. Every figure is one the page already holds: the card's
// own text and tooltip, and the Apps table row of the same app (revenue 30d, market cap, 12 months, supply).
(() => {
  const hdr = [...document.querySelectorAll('#tbl-apps thead th')].map(t => t.innerText.replace(/\s+/g, ' ').trim().toLowerCase());
  const col = k => hdr.findIndex(h => h.startsWith(k));
  const C = {rev: col('revenue 30d'), cap: col('market cap'), months: col('12 months'), sup: col('supply')};
  const esc = s => String(s).replace(/[&<>"]/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;'}[c]));
  // each gate's bar, short, from the gate's own definition in the gate row under "Degen picks" (its tooltip carries
  // the whole definition, read live below)
  const BAR = {rev: '$100K+ in 30 days', cap: '$3M+ & vetted', grow: 'grows over 6 mo', slip: '≤ 3% slip or $2M+ vol',
               dil: 'under 25% in 12 mo', up: '2.5x+ cheaper than Hyperliquid'};
  const GATE = {rev: 'real_revenue', cap: 'vetted', grow: 'growing', slip: 'liquid', dil: 'dilution', up: 'cheap'};
  const def = k => { const g = document.querySelector(`#startGates [data-gate="${GATE[k]}"]`); return g ? g.dataset.tip : BAR[k]; };
  const ICON = {
    rev: '<path d="M8 2v12M11 4.6c-.6-.9-1.7-1.4-3-1.4-1.7 0-3 .9-3 2.2 0 3 6 1.7 6 4.8 0 1.3-1.3 2.3-3 2.3-1.4 0-2.6-.6-3.2-1.6"/>',
    cap: '<path d="M8 1.8l5 2v4.1c0 3-2.1 5.3-5 6.3-2.9-1-5-3.3-5-6.3V3.8z"/><path d="M5.7 8l1.6 1.6L10.5 6.4"/>',
    grow: '<path d="M2 12l4-4 2.6 2.6L14 5"/><path d="M10 5h4v4"/>',
    slip: '<path d="M8 2.2c2.6 3 4.2 5.2 4.2 7.2a4.2 4.2 0 0 1-8.4 0c0-2 1.6-4.2 4.2-7.2z"/>',
    dil: '<circle cx="8" cy="8" r="5.6"/><path d="M8 5.2v5.6M5.2 8h5.6"/>',
  };
  const svg = k => `<svg viewBox="0 0 16 16" width="15" height="15" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round">${ICON[k]}</svg>`;

  document.querySelectorAll('#startCards .dcard').forEach(card => {
    if (card.querySelector('.gc-gates')) return;
    const row = document.querySelector(`#tbl-apps tbody tr[data-id="${card.dataset.id}"]`);
    const cell = i => (row && i >= 0 && row.children[i] ? row.children[i].innerText.replace(/\s+/g, ' ').trim() : '');
    const tip = card.dataset.tip || '';
    // Liquid passes on either reading; the card's tooltip states the one that applies
    const slip = tip.match(/([\d.]+)% slippage on a \$10K buy on ([\w.-]+)/);
    const vol = tip.match(/(\$[\d.]+[KMB]?) traded in 24 hours/);
    const growTile = [...card.querySelectorAll('.dc-tile')].find(t => /revenue a month/i.test(t.textContent));
    const grow = growTile ? growTile.querySelector('b').textContent.trim() : null;
    const supCell = row ? row.querySelector('.supcell') : null;
    const supTxt = supCell ? (supCell.querySelector('.spn') || {}).textContent.trim() : '';
    const dil = !supTxt || supTxt === '—' || supTxt === 'n/a' ? 'unknown' : supTxt + ' / 12 mo';
    // the monthly revenue bars the Apps table draws for this app, and the last full month's figure from its tooltip text
    const months = row && C.months >= 0 ? row.children[C.months] : null;
    const bars = months && months.querySelector('svg') ? months.querySelector('svg').outerHTML : '';
    const series = cell(C.months).match(/(\d{4})-(\d{2}): \$([\d.]+[KMB]?)(?! \(partial)/g) || [];
    const last = series.length ? series[series.length - 1].match(/(\d{4})-(\d{2}): (\$[\d.]+[KMB]?)/) : null;
    const monthName = last ? new Date(Date.UTC(+last[1], +last[2] - 1, 1)).toLocaleString('en', {month: 'short', timeZone: 'UTC'}) : null;

    const rows = [
      ['rev', 'Revenue 30 days', cell(C.rev) || '—', last ? `${monthName} ${last[3]}` : ''],
      ['cap', 'Market cap', cell(C.cap) || '—', ''],
      ['grow', 'Revenue growth', grow ? grow + ' / mo' : '—', ''],
      slip ? ['slip', '$10K buy', slip[1] + '% slip', 'on ' + slip[2]] : ['slip', 'Volume 24h', vol ? vol[1] : '—', 'a $10K buy fits'],
      ['dil', 'Dilution', dil, ''],
    ];
    const gates = document.createElement('div');
    gates.className = 'gc-gates';
    gates.innerHTML = `<div class="gc-head"><span>Why it is a pick</span><b>6 / 6 gates</b></div>` + rows.map(([k, name, val, note]) =>
      `<div class="gc-row tipme" tabindex="0" data-tiplong="1" data-tipb="${esc(name)}${note ? ' · ' + esc(note) : ''}" data-tip="Gate: ${esc(def(k))}">
        <i class="gc-ic">${svg(k)}</i><span class="gc-nm">${esc(name)}</span>
        <span class="gc-bars">${k === 'rev' ? bars : ''}</span>
        <span class="gc-vv"><b class="gc-v${val === 'unknown' ? ' na' : ''}">${esc(val)}</b><span class="gc-bar">${esc(BAR[k])}</span></span></div>`).join('');
    const pot = card.querySelector('.dc-pot');
    const label = document.createElement('span');
    label.className = 'gc-up';
    label.innerHTML = `upside<br><em>gate 2.5x+</em>`;
    pot.querySelector('.cardi').before(label);
    pot.after(gates);
    // tokens out and holders' share leave the card: holders' share is the smiley's tooltip, dilution is a gate row
    card.querySelectorAll('.dc-tiles, .dc-why .why.na').forEach(e => e.remove());
  });
})();
