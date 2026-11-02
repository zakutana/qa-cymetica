// The Supply column as we ask for it, drawn by their own functions inside their page's script. Collector Crypt's figure is the
// one read from Streamflow's public dashboard on 2 Nov 2026 (346.8M locked in vesting, 885M circulating); the rest is their data.
{
  const CARDS = {pct: 39.2, source: 'Streamflow vesting contracts, read 2 Nov'};
  const oldCell = supplyCell;
  supplyCell = function (e) {
    const sp = supplyOf(e);
    if (!sp) return oldCell(e);
    const known = saDil(sp);
    if (known) return oldCell(e);
    if (e.slug === 'collector-crypt') {
      return `<span class="supcell v-bad tipme"${tipAttrs('Dilution, 12 months +' + CARDS.pct + '%', '346.8M CARDS still locked in vesting, unlocking to July 2027. Source: ' + CARDS.source + '.')}>${saPie(sp, 22)}<span class="spn">+${CARDS.pct}%</span></span>`;
    }
    const circ = sp.circulating, max = sp.max_supply;
    if (circ && max && (max - circ) / circ < 0.01) {
      return `<span class="supcell v-good tipme"${tipAttrs('Dilution, 12 months 0%', 'Max supply is reached: no more tokens can come out.')}>${saPie(sp, 22)}<span class="spn">0%</span></span>`;
    }
    const finished = ((e.next_unlock || {}).kind === 'none') && ((e.unlock || {}).no_schedule_pct || 0) > 0;
    const say = finished ? 'The published schedule has finished; the rest of the supply has none. Nothing is assumed.'
      : 'No schedule found on DeFiLlama, the project’s vesting contracts, Tokenomist or DropsTab. Nothing is assumed.';
    return `<span class="supcell v-na tipme"${tipAttrs('Dilution, 12 months: unknown', say)}><span class="gt-unknown" aria-hidden="true"></span><span class="spn">n/a</span></span>`;
  };
}
