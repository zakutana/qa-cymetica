// Our improvements on their live Gem Screener. This file goes inside their page's script, before its first render:
// their functions draw the page and these wrap them, so it behaves as it will when built. Every figure is their snapshot
// or their coin route. Numbers match the list in the box at the bottom right.
{
  const N = n => `<span class="gt-n">${n}</span>`;
  const pct = v => (v >= 10 ? Math.round(v) : Number(v.toFixed(1))) + '%';
  const coins = {};   // slug -> the coin route's answer, for the picks: their checks

  // ---- 1-4 the Top Picks card
  const oldRows = cardGateRows;
  cardGateRows = function (e) {
    const html = oldRows(e), l = e.liq || {};
    if (typeof l.impact_pct !== 'number' || l.impact_pct <= 3 || typeof l.vol24h !== 'number') return html;
    // 2 over 3 % in the pool: the slip first, the volume named for what it is, and whether it carries the gate
    const at = html.indexOf('data-gate="liquid"');
    if (at < 0) return html;
    const carried = l.vol24h >= (((DEGEN.rules || {}).liquid || {}).vol_pass || 2e6);
    const tail = html.slice(at).replace(/<span class="gv"><b>[^<]*<\/b><span>[^<]*<\/span><\/span>/,
      `<span class="gv"><b class="gt-over">${pct(l.impact_pct)} slip${N(2)}</b><span>${carried ? 'passes on' : 'only'} ${fmtUsd(l.vol24h)} a day, all venues</span></span>`);
    return html.slice(0, at) + tail;
  };
  function watchOut(e) {
    const items = [], track = ((coins[e.slug] || {}).track || {});
    let hot = false;
    if (track.verdict === 'bad') {
      hot = true;
      const said = String(track.hack || '').match(/exploit on (\d{4}-\d{2}-\d{2}), (\$[\d.]+[KMB]?)/);
      items.push(`<div>${N(1)}<b>${esc(track.text)}</b>${said ? `: ${esc(said[2])}, ${esc(new Date(said[1]).toLocaleDateString('en-GB', {day: 'numeric', month: 'short', year: 'numeric'}))}` : ''}</div>`);
    }
    if ((e.exit_flags || []).includes('byznys_slabne') && typeof e.rev30d_vs_high === 'number')
      items.push(`<div>${N(4)}Not growing: 30-day revenue is <b>${Math.round(100 * e.rev30d_vs_high)}%</b> of its best</div>`);
    if (typeof dil12Of(e) !== 'number') items.push(`<div>Dilution unknown: no schedule published</div>`);
    if (!items.length) return '';
    return `<div class="dc-watch${hot ? '' : ' calm'}"><span class="dc-watch-h">${N(3)}Watch out</span>${items.join('')}</div>`;
  }
  const oldCard = degenCard;
  degenCard = function (e) {
    return oldCard(e).replace('<div class="dc-risk">', watchOut(e) + '<div class="dc-risk">');
  };

  // ---- 5 the smiley's sentence says its window
  const oldSmiley = holdersSmiley;
  holdersSmiley = function (e) {
    const html = oldSmiley(e);
    if (e.holders_share === 0 && e.holders_share_1y > 0)
      return html.replace(/Holders get [\d.]+% of revenue/, `Holders got ${pct(100 * e.holders_share_1y)} over 12 months, 0% in the last 30 days`);
    return html;
  };

  // ---- 7, 8, 9 the lines around the cards
  const oneAway = () => APPS.filter(e => (e.degen_fail || []).length === 1);
  const oldStart = renderStart;
  renderStart = function () {
    oldStart();
    const why = document.querySelector('#startNear .nq-why');
    if (why && !document.getElementById('gtNear')) why.insertAdjacentHTML('afterend',
      `<span class="gt-line" id="gtNear" style="margin:0 0 0 12px">${N(8)}<b>${(DEGEN.near || []).length} of ${oneAway().length}</b> apps one gate away</span>`);
    // 9 the backtest's date and the forward record
    const bt = document.getElementById('startBtLine'), s = DATA.backtest_summary || {}, led = DATA.picks_ledger || {};
    if (bt && !bt.querySelector('.gt-n') && s.generated_at) {
      const day = t => new Date(t).toLocaleDateString('en-GB', {day: 'numeric', month: 'short'});
      const days = Math.round((DATA.generated_at - led.since) / 86400);
      bt.innerHTML = `${N(9)}Backtest of the old gates, run ${day(s.generated_at)}: inconclusive. ${days} days of forward record on these gates, first reading ${day(led.ready_at * 1000)}. A shortlist, not a signal.`;
    }
    const near = document.getElementById('startNear');
    const old = document.getElementById('gtLog');
    if (old) old.remove();
    if (near) near.insertAdjacentHTML('afterend', picksLog());
    document.querySelectorAll('#gtLog [data-open]').forEach(a => { a.onclick = ev => { ev.preventDefault(); openPanel(a.dataset.open); }; });
  };
  // 7: what we saw ourselves: the snapshot the page swapped in on 2 Nov at 08:38 UTC ("Updated 33 h ago") against today's
  function picksLog() {
    const then = ['STONK', 'CARDS', 'SOLV', 'PUMP', 'MET', 'DOLO', 'COW', 'SPK', 'LDO', 'TWT'];
    const now = (DEGEN.shortlist || []).map(k => APPS.find(a => (a.key || a.slug) === k)).filter(Boolean);
    const out = then.filter(s => !now.some(a => a.symbol === s)).map(s => APPS.find(a => a.symbol === s)).filter(Boolean);
    const inn = now.filter(a => !then.includes(a.symbol));
    const name = e => `<a href="#" data-open="${esc(e.key || e.slug)}" style="color:inherit">${esc(e.name)}</a>`;
    const why = e => (e.degen_fail || []).map(f => nearReason(f).full).join(', ') || 'passes';
    const rows = out.map(e => `<tr><td class="out">left</td><td>${name(e)}</td><td class="num">${fmtMult(e.potential)}</td><td>${esc(why(e))}</td></tr>`).join('') +
      inn.map(e => `<tr><td class="in">entered</td><td>${name(e)}</td><td class="num">${fmtMult(e.potential)}</td><td>passes all 6 gates</td></tr>`).join('');
    return `<details class="gt-log" id="gtLog" open><summary>${N(7)}Picks log<small>who came and went, and why, at each refresh</small></summary>
      <table><thead><tr><th colspan="4">Since the snapshot of 31 Oct</th></tr></thead><tbody>${rows}</tbody></table></details>`;
  }

  // ---- 10 a near miss on hover: the same card as a pick, with the gate it fails marked. It opens downward, off the picks
  const FAILED_ROW = {'malý byznys': 'revenue', 'neprověřené': 'vetted', 'byznys neroste': 'growing', 'mělká likvidita': 'liquid',
    'likvidita neznámá': 'liquid', 'heavy dilution': 'dilution', 'supply sources disagree': 'dilution'};
  const nearCard = e => {
    const G = degenGates(), ng = G.gates.length, fails = e.degen_fail || [];
    let html = degenCard(e).replace('<span>Why it is a pick</span>', '<span>Why it is not a pick</span>')
      .replace(`<b>${ng} / ${ng} gates</b>`, `<b class="gt-short">${ng - fails.length} / ${ng} gates</b>`);
    fails.forEach(f => {
      const row = FAILED_ROW[f];
      if (row) html = html.replace(`<div class="dc-gate" data-gate="${row}"`, `<div class="dc-gate gt-failed" data-gate="${row}"`)
        .replace(`<div class="dc-gate na" data-gate="${row}"`, `<div class="dc-gate na gt-failed" data-gate="${row}"`);
      if (f === 'drahé') html = html.replace('<div class="dc-pot">', '<div class="dc-pot gt-failed-up">');
    });
    return html;
  };
  let tip = null;
  const hideTip = () => { if (tip) tip.hidden = true; };
  function showTip(cube) {
    const e = findEntity(cube.dataset.id);
    if (!e) return;
    if (!tip) { tip = document.createElement('div'); tip.id = 'gtNearTip'; tip.setAttribute('role', 'tooltip'); document.body.appendChild(tip); }
    tip.innerHTML = nearCard(e);
    tip.hidden = false;
    const r = cube.getBoundingClientRect(), h = tip.offsetHeight, w = tip.offsetWidth;
    // under the cube where it fits, else beside it: the cube stays in sight either way
    if (r.bottom + 8 + h <= innerHeight) {
      tip.style.top = (r.bottom + 8) + 'px';
      tip.style.left = Math.max(8, Math.min(innerWidth - w - 8, r.left + r.width / 2 - w / 2)) + 'px';
    } else {
      tip.style.top = Math.max(8, innerHeight - h - 8) + 'px';
      tip.style.left = (r.right + 8 + w <= innerWidth ? r.right + 8 : Math.max(8, r.left - w - 8)) + 'px';
    }
  }
  if (matchMedia('(hover: hover)').matches) {
    document.addEventListener('mouseover', ev => {
      const cube = ev.target.closest && ev.target.closest('#startNear .nq-cube');
      if (cube) showTip(cube); else hideTip();
    });
    document.addEventListener('focusin', ev => {
      const cube = ev.target.closest && ev.target.closest('#startNear .nq-cube');
      if (cube) showTip(cube); else hideTip();
    });
    addEventListener('scroll', hideTip, true);
  }

  // ---- 6 which chain each on-chain sentence was read on; 5 holders, both windows: after their panel has drawn
  function panelNotes() {
    const panel = document.getElementById('panel');
    if (!panel || !panel.classList.contains('open')) return;
    const e = findEntity(state.selectedId);
    if (!e || isChainsView()) return;
    gtObserver.disconnect();
    const tile = [...panel.querySelectorAll('[class*=tile]')].find(t => /^\s*To holders/i.test(t.textContent));
    if (tile && !panel.querySelector('.gt-hold') && (e.holders_share_1y > 0 || e.holders_share > 0)) {
      const s30 = e.holders_share || 0, s1y = e.holders_share_1y || 0;
      tile.insertAdjacentHTML('beforeend', `<p class="gt-note gt-hold">${N(5)}last 30 days <b${s30 === 0 ? ' class="weak"' : ''}>${pct(100 * s30)}</b> · 12 months <b>${pct(100 * s1y)}</b></p>`);
    }
    const rug = ((e.dlevel || {}).checks || []).find(c => c.id === 'rug_power');
    const guard = [...panel.querySelectorAll('section')].find(s => /^\s*Guardians/i.test(s.textContent));
    if (rug && guard && !guard.querySelector('.gt-chain')) {
      const chain = chainOf(rug.source_url), pool = (e.liq || {}).chain;
      const addr = (String(rug.source_url || '').match(/([0-9a-zA-Z]{32,})\/?$/) || [])[1] || '';
      if (chain) guard.insertAdjacentHTML('beforeend', `<p class="gt-note gt-chain">${N(6)}Rug power read on <b>${esc(chain)}</b>${addr ? ' (' + esc(addr.slice(0, 6) + '…' + addr.slice(-4)) + ')' : ''}${pool && norm(pool) !== norm(chain) ? `; the pool it trades in is on <b class="weak">${esc(cap(pool))}</b>` : ''}.</p>`);
    }
    gtObserver.observe(panel, {childList: true, subtree: true});
  }
  const norm = s => String(s).toLowerCase().replace(/[^a-z]/g, '');
  const cap = s => String(s).charAt(0).toUpperCase() + String(s).slice(1);
  const chainOf = u => {
    const h = (String(u || '').match(/^https?:\/\/(?:www\.)?([^/]+)/) || [])[1] || '';
    return ({'etherscan.io': 'Ethereum', 'solscan.io': 'Solana', 'arbiscan.io': 'Arbitrum', 'basescan.org': 'Base', 'bscscan.com': 'BSC', 'polygonscan.com': 'Polygon',
      'hyperevmscan.io': 'HyperEVM', 'optimistic.etherscan.io': 'Optimism', 'snowtrace.io': 'Avalanche', 'mantlescan.xyz': 'Mantle', 'sonicscan.org': 'Sonic'})[h] || '';
  };
  const gtObserver = new MutationObserver(() => { clearTimeout(window.gtT); window.gtT = setTimeout(panelNotes, 150); });
  gtObserver.observe(document.getElementById('panel'), {childList: true, subtree: true});

  // ---- the tour: where each improvement is. Ours only, it never goes in a picture for them
  function flash(el) {
    if (!el) return;
    el.scrollIntoView({block: 'center', behavior: 'smooth'});
    el.classList.add('gt-flash');
    setTimeout(() => el.classList.remove('gt-flash'), 2200);
  }
  const closeIt = () => { const p = document.getElementById('panel'); if (p.classList.contains('open')) closePanel(); };
  const card = sym => [...document.querySelectorAll('#startCards .dcard')].find(c => (c.querySelector('.sym') || {}).textContent === sym);
  const key = slug => (APPS.find(a => a.slug === slug) || {}).key;
  const panelAt = (slug, sel) => { setView('start'); openPanel(key(slug)); setTimeout(() => flash(document.querySelector('#panel ' + sel)), 1500); };
  const onStart = el => { closeIt(); setView('start'); setTimeout(() => flash(el()), 60); };
  const STEPS = [
    [1, 'Exploit in the last year on the card', () => onStart(() => card('TWT'))],
    [2, 'Liquid: the slip beside the volume', () => onStart(() => card('DOLO'))],
    [3, "A pick's own warnings on the card", () => onStart(() => card('MET'))],
    [4, '"Not growing" says why', () => onStart(() => card('COW'))],
    [5, 'Holders: 30 days beside 12 months', () => panelAt('lido', '.gt-hold')],
    [6, 'On-chain sentences name their chain', () => panelAt('stargate-finance', '.gt-chain')],
    [7, 'Public picks log by name', () => onStart(() => document.getElementById('gtLog'))],
    [8, 'Near misses say how many', () => onStart(() => document.getElementById('gtNear'))],
    [9, 'Backtest shows its date', () => onStart(() => document.getElementById('startBtLine'))],
    [10, 'Near miss on hover: the card, gate marked', () => onStart(() => document.querySelector('#startNear .nq-lane'))],
  ];
  function tour() {
    const box = document.createElement('aside');
    box.id = 'gtTour';
    box.innerHTML = `<header><span>Improvements, click one</span><span><button id="gtClean" title="Hide the numbers">numbers off</button> <button id="gtMin">–</button></span></header>
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
  }

  // ---- once their first render has run: the tour, and the checks of the picks and near misses, then the cards again
  window.gtPeek = () => ({coins, apps: APPS, data: DATA, nearCard, showTip});
  setTimeout(tour, 0);
  Promise.all([...(DEGEN.shortlist || []), ...(DEGEN.near || [])].map(k => {
    const e = APPS.find(a => (a.key || a.slug) === k);
    return e ? fetch('/api/v1/gem-screener/coins/' + encodeURIComponent(e.slug), {credentials: 'omit'}).then(r => r.json()).then(c => {
      const t = ((c.degen_level || {}).checks || []).find(x => x.id === 'track_record') || {};
      coins[e.slug] = {track: {verdict: t.verdict, text: t.text, hack: t.context}};
    }).catch(() => {}) : null;
  })).then(() => { if (state.view === 'start') renderStart(); });
}
