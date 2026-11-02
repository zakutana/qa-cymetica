// Our improvements on their live Gem Screener. This file goes inside their page's script, before its first render:
// their functions draw the page and these wrap them, so it behaves as it will when built. Every figure is their snapshot
// or their coin route. Numbers match the improvements list.
{
  const N = n => `<span class="gt-n">${n}</span>`;
  const pct = v => (v >= 10 ? Math.round(v) : Number(v.toFixed(1))) + '%';
  const coins = {};   // slug -> the coin route's answer, for the picks: their checks

  // ---- 1-4 the Top Picks card
  const oldRows = cardGateRows;
  cardGateRows = function (e) {
    const html = oldRows(e), l = e.liq || {};
    if (typeof l.impact_pct !== 'number' || l.impact_pct <= 3 || typeof l.vol24h !== 'number') return html;
    // 2 a pick on the volume reading: the slip first, the volume named for what it is
    const at = html.indexOf('data-gate="liquid"');
    if (at < 0) return html;
    const tail = html.slice(at).replace(/<span class="gv"><b>[^<]*<\/b><span>[^<]*<\/span><\/span>/,
      `<span class="gv"><b class="gt-over">${pct(l.impact_pct)} slip${N(2)}</b><span>passes on ${fmtUsd(l.vol24h)} a day, all venues</span></span>`);
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

  // ---- 5 the band word never stands alone
  const oldStrip = levelStrip;
  levelStrip = function (e) {
    const html = oldStrip(e), d = e.dlevel || {};
    if (!d.missing && d.low === d.high) return html;
    return html.replace(/<p class="lvl-line">[^<]*<\/p>/,
      `<p class="lvl-line gt-open">${esc(BAND_NAME[d.band] || '')} so far.${N(5)}</p><p class="gt-note"><b>${d.level} now, ${d.low} to ${d.high} once the rest is in.</b> ${d.missing} of 10 checks have not run.</p>`);
  };

  // ---- 8 the smiley's sentence says its window
  const oldSmiley = holdersSmiley;
  holdersSmiley = function (e) {
    const html = oldSmiley(e);
    if (e.holders_share === 0 && e.holders_share_1y > 0)
      return html.replace(/Holders get [\d.]+% of revenue/, `Holders got ${pct(100 * e.holders_share_1y)} over 12 months, 0% in the last 30 days`);
    return html;
  };

  // ---- 6, 12, 13 the Apps table
  // the page holds these under its internal words (gsInternal), the API under the English ones
  const GATE_FAILS = [['Real revenue', ['malý byznys']], ['Vetted', ['neprověřené']], ['Growing', ['byznys neroste']],
    ['Cheap', ['drahé']], ['Liquid', ['mělká likvidita', 'likvidita neznámá']], ['Dilution', ['heavy dilution', 'supply sources disagree']]];
  const fails = (e, f) => f.some(x => (e.degen_fail || []).includes(x));
  const passed = e => GATE_FAILS.filter(([, f]) => !fails(e, f)).length;
  const dots = e => {
    const bad = GATE_FAILS.filter(([, f]) => fails(e, f)).map(([n]) => n);
    const marks = GATE_FAILS.map(([, f]) => `<i class="${fails(e, f) ? '' : 'ok'}"></i>`).join('');
    const c = 6 - bad.length;
    return `<span class="gt-dots" title="${esc(bad.length ? 'Fails: ' + bad.join(', ') : 'Passes all 6 gates')}">${marks}</span><span class="gt-count${c === 6 ? ' all' : ''}">${c}/6</span>`;
  };
  const oldValue = sortValue;
  sortValue = function (e, key) { return key === 'gates' ? passed(e) : oldValue(e, key); };
  const oldPot = potentialCell;
  potentialCell = function (e) {
    const html = oldPot(e);
    if (typeof e.potential_raw === 'number' && e.potential_raw > UPSIDE_CAP)
      return html + `<span class="gt-capped">capped${N(13)}<br>real ${Math.round(e.potential_raw).toLocaleString('en')}x</span>`;
    return html;
  };
  const oldName = nameCell;
  nameCell = function (e) {
    const html = oldName(e), c = (e.cg || {}).chg7d;
    return typeof c === 'number' && c <= -50 ? html + `<span class="gt-crash">${Math.round(c)}% in 7 days${N(6)}</span>` : html;
  };
  const oldList = renderList;
  renderList = function () {
    oldList();
    if (isChainsView()) return;
    // 12 under the meter, not a column of its own: their table fits 1360 px and has no room for one
    document.querySelectorAll('#tbl-apps tbody tr[data-id]').forEach(tr => {
      const e = findEntity(tr.dataset.id), td = tr.querySelector('td.degencol');
      if (e && td && !td.querySelector('.gt-gates')) td.insertAdjacentHTML('beforeend', `<div class="gt-gates">${dots(e)}</div>`);
    });
    const count = document.getElementById('rowCount');
    const bar = count && count.parentElement;
    if (bar && !document.getElementById('gtSort')) {
      bar.insertAdjacentHTML('afterend', `<button id="gtSort" class="gt-sort">${N(12)}Most gates first</button>`);
      document.getElementById('gtSort').onclick = () => { state.sortKey = 'gates'; state.sortDir = -1; renderList(); };
    }
    const sorter = document.getElementById('gtSort');
    if (sorter) sorter.classList.toggle('on', state.sortKey === 'gates');
  };

  // ---- 10, 11, 14, 15 the lines around the cards
  const oneAway = () => APPS.filter(e => (e.degen_fail || []).length === 1);
  const oldStart = renderStart;
  renderStart = function () {
    oldStart();
    const lag = APPS.filter(e => (e.exit_flags || []).includes('tema_zaostava')).length;
    const title = document.getElementById('startTitle');
    if (title && !document.getElementById('gtLag')) title.insertAdjacentHTML('afterend',
      `<p class="gt-line" id="gtLag">${N(14)}<b>${lag} of ${APPS.length}</b> apps sit in a theme that has lagged BTC over the last month, so no card repeats it.</p>`);
    const why = document.querySelector('#startNear .nq-why');
    if (why && !document.getElementById('gtNear')) why.insertAdjacentHTML('afterend',
      `<span class="gt-line" id="gtNear" style="margin:0 0 0 12px">${N(11)}<b>${(DEGEN.near || []).length} of ${oneAway().length}</b> apps one gate away<a class="gt-more" id="gtNearAll">see all ${oneAway().length}</a></span>`);
    const all = document.getElementById('gtNearAll');
    if (all) all.onclick = ev => { ev.preventDefault(); showApps('all', 'gates'); };
    // 15 the backtest's date and the forward record
    const bt = document.getElementById('startBtLine'), s = DATA.backtest_summary || {}, led = DATA.picks_ledger || {};
    if (bt && !bt.querySelector('.gt-n') && s.generated_at) {
      const day = t => new Date(t).toLocaleDateString('en-GB', {day: 'numeric', month: 'short'});
      const days = Math.round((DATA.generated_at - led.since) / 86400);
      bt.innerHTML = `${N(15)}Backtest of the old gates, run ${day(s.generated_at)}: inconclusive. ${days} days of forward record on these gates, first reading ${day(led.ready_at * 1000)}. A shortlist, not a signal.`;
    }
    const near = document.getElementById('startNear');
    const old = document.getElementById('gtLog');
    if (old) old.remove();
    if (near) near.insertAdjacentHTML('afterend', picksLog());
    document.querySelectorAll('#gtLog [data-open]').forEach(a => { a.onclick = ev => { ev.preventDefault(); openPanel(a.dataset.open); }; });
  };
  // 10: what we saw ourselves: the snapshot the page swapped in on 2 Nov at 08:38 UTC ("Updated 33 h ago") against today's
  function picksLog() {
    const then = ['STONK', 'CARDS', 'SOLV', 'PUMP', 'MET', 'DOLO', 'COW', 'SPK', 'LDO', 'TWT'];
    const now = (DEGEN.shortlist || []).map(k => APPS.find(a => (a.key || a.slug) === k)).filter(Boolean);
    const out = then.filter(s => !now.some(a => a.symbol === s)).map(s => APPS.find(a => a.symbol === s)).filter(Boolean);
    const inn = now.filter(a => !then.includes(a.symbol));
    const name = e => `<a href="#" data-open="${esc(e.key || e.slug)}" style="color:inherit">${esc(e.name)}</a>`;
    const why = e => (e.degen_fail || []).map(f => nearReason(f).full).join(', ') || 'passes';
    const rows = out.map(e => `<tr><td class="out">left</td><td>${name(e)}</td><td class="num">${fmtMult(e.potential)}</td><td>${esc(why(e))}</td></tr>`).join('') +
      inn.map(e => `<tr><td class="in">entered</td><td>${name(e)}</td><td class="num">${fmtMult(e.potential)}</td><td>passes all 6 gates</td></tr>`).join('');
    return `<details class="gt-log" id="gtLog" open><summary>${N(10)}Picks log<small>who came and went, and why, at each refresh</small></summary>
      <table><thead><tr><th colspan="4">Since the snapshot of 31 Oct</th></tr></thead><tbody>${rows}</tbody></table></details>`;
  }

  // ---- 7, 8, 9 the coin panel: after their panel has drawn, and again when it refills
  function panelNotes() {
    const panel = document.getElementById('panel');
    if (!panel || !panel.classList.contains('open')) return;
    const e = findEntity(state.selectedId);
    if (!e || isChainsView()) return;
    gtObserver.disconnect();
    // 7 the window: the report's sentence, and a line under the trajectory
    const g = e.growth6m || {};
    if (typeof g.g === 'number' && g.days) {
      const months = g.days >= 170 ? '6 months' : (g.days < 60 ? g.days + ' days' : Math.round(g.days / 30.4) + ' months');
      if (g.days < 170) panel.querySelectorAll('li, p, div, span').forEach(el => {
        if (el.children.length === 0 && /over 6 months/.test(el.textContent)) el.textContent = el.textContent.replace(/over 6 months/g, 'over ' + months);
      });
      const traj = [...panel.querySelectorAll('section')].find(s => /^\s*Trajectory/i.test(s.textContent));
      if (traj && !traj.querySelector('.gt-fit')) {
        const r2 = g.r2 || 0, sure = r2 >= .7 ? 'steady' : r2 >= .4 ? 'patchy' : 'weak';
        const m = (e.monthly || []).filter(x => !x.partial).slice(-2);
        const move = m.length === 2 && m[0].v ? Math.round(100 * (m[1].v / m[0].v - 1)) : null;
        traj.insertAdjacentHTML('beforeend', `<p class="gt-note gt-fit">${N(7)}<b>${fmtPct(g.g, 0)} a month</b> is a fit over <b>${months}</b>, ${sure === 'weak' ? '<span class="weak">weak fit</span>' : sure + ' fit'} (r² ${r2.toFixed(2)}).${move !== null ? ` Last full month: <b${move < 0 ? ' class="weak"' : ''}>${move > 0 ? '+' : ''}${move}%</b>.` : ''}</p>`);
      }
    }
    // 8 holders, both windows
    const tile = [...panel.querySelectorAll('[class*=tile]')].find(t => /^\s*To holders/i.test(t.textContent));
    if (tile && !panel.querySelector('.gt-hold') && (e.holders_share_1y > 0 || e.holders_share > 0)) {
      const s30 = e.holders_share || 0, s1y = e.holders_share_1y || 0;
      tile.insertAdjacentHTML('beforeend', `<p class="gt-note gt-hold">${N(8)}last 30 days <b${s30 === 0 ? ' class="weak"' : ''}>${pct(100 * s30)}</b> · 12 months <b>${pct(100 * s1y)}</b></p>`);
    }
    // 9 which chain each on-chain sentence was read on
    const rug = ((e.dlevel || {}).checks || []).find(c => c.id === 'rug_power');
    const guard = [...panel.querySelectorAll('section')].find(s => /^\s*Guardians/i.test(s.textContent));
    if (rug && guard && !guard.querySelector('.gt-chain')) {
      const chain = chainOf(rug.source_url), pool = (e.liq || {}).chain;
      const addr = (String(rug.source_url || '').match(/([0-9a-zA-Z]{32,})\/?$/) || [])[1] || '';
      if (chain) guard.insertAdjacentHTML('beforeend', `<p class="gt-note gt-chain">${N(9)}Rug power read on <b>${esc(chain)}</b>${addr ? ' (' + esc(addr.slice(0, 6) + '…' + addr.slice(-4)) + ')' : ''}${pool && norm(pool) !== norm(chain) ? `; the pool it trades in is on <b class="weak">${esc(cap(pool))}</b>` : ''}.</p>`);
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
  function showApps(mode, sort) {
    setView('apps');
    if (mode) setTrustMode(mode);
    if (sort) { state.sortKey = sort; state.sortDir = -1; renderList(); }
  }
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
    [5, 'The band word with its range', () => panelAt('stonkfun', '#lvlCard')],
    [6, 'A flag for a collapsed price', () => { closeIt(); showApps('all', 'potential'); flash(document.querySelector('.gt-crash')); }],
    [7, 'Growth shows window and fit', () => panelAt('stonkfun', '.gt-fit')],
    [8, 'Holders: 30 days beside 12 months', () => panelAt('lido', '.gt-hold')],
    [9, 'On-chain sentences name their chain', () => panelAt('stargate-finance', '.gt-chain')],
    [10, 'Public picks log by name', () => onStart(() => document.getElementById('gtLog'))],
    [11, 'Near misses say how many', () => onStart(() => document.getElementById('gtNear'))],
    [12, 'Six gate dots on each row, sortable', () => { closeIt(); showApps('all', 'gates'); flash(document.getElementById('gtSort')); }],
    [13, 'Capped upside marked', () => { closeIt(); showApps('all', 'potential'); flash(document.querySelector('.gt-capped')); }],
    [14, 'Theme lag: one line, not every row', () => onStart(() => document.getElementById('gtLag'))],
    [15, 'Backtest shows its date', () => onStart(() => document.getElementById('startBtLine'))],
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

  // ---- once their first render has run: the tour, and the picks' checks, then the cards again
  window.gtPeek = () => ({coins, apps: APPS, data: DATA});
  setTimeout(tour, 0);
  Promise.all((DEGEN.shortlist || []).map(k => {
    const e = APPS.find(a => (a.key || a.slug) === k);
    return e ? fetch('/api/v1/gem-screener/coins/' + encodeURIComponent(e.slug), {credentials: 'omit'}).then(r => r.json()).then(c => {
      const t = ((c.degen_level || {}).checks || []).find(x => x.id === 'track_record') || {};
      coins[e.slug] = {track: {verdict: t.verdict, text: t.text, hack: t.context}};
    }).catch(() => {}) : null;
  })).then(() => { if (state.view === 'start') renderStart(); });
}
