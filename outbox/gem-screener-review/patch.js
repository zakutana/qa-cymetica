// The review's ten changes on their live Gem Screener (10 Nov 2026). This file goes inside their page's script, before
// its first render: their functions draw the page and these wrap them, so it behaves as it would when built. Every figure
// is their snapshot's own field or computed from it; nothing is typed. The benchmark is left as it is. Numbers match the
// list in the box at the bottom right.
{
  const N = n => `<span class="gr-n">${n}</span>`;
  const num = v => typeof v === 'number' && isFinite(v);
  const keyOf = e => e.key || e.slug;
  const byUp = (a, b) => (b.potential_raw || b.potential || 0) - (a.potential_raw || a.potential || 0);
  const mult = v => fmtMult(Math.abs(v) < 0.05 ? 0 : v);
  const left = [];   // the picks change 1 took out, for the line under the title

  // ---------------------------------------------------------------- the data, changed once
  // Their page swaps a whole snapshot in when its extras arrive; the marks below survive that copy, and applyChanges runs
  // again after every swap for anything that did not.
  function tierOf(e, up) {
    const t = up >= 10 ? 5 : up >= 5 ? 4 : up >= 2.5 ? 3 : up >= 1.2 ? 2 : 1;
    return (e.reliable || e.young) ? t : Math.min(t, 3);
  }
  function applyChanges() {
    // 1 Growing: an app whose own card says "Not growing" (their exit rule, business weakening) does not pass the gate
    let moved = false;
    APPS.forEach(e => {
      if (e._gr1 || e.degen_ok !== true || !(e.exit_flags || []).includes('byznys_slabne')) return;
      e._gr1 = true; e.degen_ok = false; e.degen_fail = ['byznys neroste']; moved = true;
    });
    if (moved || !DEGEN._gr) {
      const ok = APPS.filter(e => e.degen_ok === true).sort(byUp);
      const notNear = ['malý byznys', 'neprověřené', 'drahé'];
      DEGEN._gr = true;
      DEGEN.n_ok = ok.length;
      DEGEN.shortlist = ok.slice(0, (DEGEN.rules || {}).shortlist || 10).map(keyOf);
      DEGEN.near = APPS.filter(e => Array.isArray(e.degen_fail) && e.degen_fail.length === 1 && !notNear.includes(e.degen_fail[0]))
        .sort(byUp).slice(0, 6).map(keyOf);
      const g = DATA.degen_gates;
      if (g) {
        g.picks = ok.length;
        const grow = (g.gates || []).find(x => x.id === 'growing');
        if (grow && !/Not growing/.test(grow.rule_long || ''))
          grow.rule_long = (grow.rule_long || '') + ' An app whose card says "Not growing" (revenue fell over the last 90 days, or 30-day revenue is far under its best) does not pass.';
      }
    }
    left.length = 0;
    APPS.filter(e => e._gr1).sort(byUp).forEach(e => left.push(e));

    // 8 Chains: nothing is held back, the four inputs count as DeFiLlama gives them. The benchmark stays as it is.
    CHAINS.forEach(e => {
      const a = e.adoption || {}, i = a.inputs || {};
      if (e._gr8 || !a.held_back_any || !num(e.potential_raw) || !num(e.mcap)) return;
      if (![i.users, i.dex_volume_30d, i.tvl, i.stablecoins].every(v => num(v) && v > 0) || !num(BENCH_CHAINS.mult)) return;
      const raw = Math.pow(i.users * i.dex_volume_30d * i.tvl * i.stablecoins, 0.25);
      const up = BENCH_CHAINS.mult / (e.mcap / raw);
      e._gr8 = {was: e.potential_raw, cut: Object.assign({}, a.held_back)};
      e.ps = e.mcap / raw;
      e.potential_raw = up;
      e.potential = Math.min(UPSIDE_CAP, up);
      e.mcap_at_bench = e.mcap * e.potential;
      if (num(e.price)) e.price_at_bench = e.price * e.potential;
      e.tier = tierOf(e, e.potential);
      a.value = raw;
      a.held_back_any = false;
      a.counted = {users: i.users, dex_volume_30d: i.dex_volume_30d};
      a.held_back = {users: 0, dex_volume_30d: 0};
    });

    // 9 Sectors: "ahead of the median sector" counts from 3 points (the page's own arrows already call less than that
    // flat), so a sector 0.1 points ahead is not ahead; and Hot also needs the sector to beat BTC over the month.
    if (!STAGE.holding) {
      STAGE.holding = {name: 'Holding up', glyph: '▲', tone: 'accent', rule: 'above 3M · above 1M · behind BTC', short: '3M ↑ 1M ↑ BTC ↓',
        why: 'Ahead of the other sectors on 3M and 1M, behind BTC over the month',
        long: 'Ahead of the median sector over 3 months and over the last month, but behind BTC over the month: it falls less than the others.'};
      STAGE_ORDER.splice(STAGE_ORDER.indexOf('hot') + 1, 0, 'holding');
      STAGE.hot.rule = 'above 3M · above 1M · beats BTC';
      STAGE.hot.long = 'Ahead of the median sector over 3 months and over the last month, and ahead of BTC over the month.';
    }
    const side = v => v > 0.03 ? 1 : -1;
    THEMES.forEach(th => {
      if (th._gr9 || !num(th.vs_median_1m) || !num(th.vs_median_3m) || !th.stage) return;
      const s1 = side(th.vs_median_1m), s3 = side(th.vs_median_3m);
      const st = s3 > 0 ? (s1 > 0 ? (th.rs1m > 0 ? 'hot' : 'holding') : 'fading') : (s1 > 0 ? 'emerging' : 'falling');
      th._gr9 = {was: th.stage};
      th.stage = st;
    });
  }
  applyChanges();
  const oldApply = applySnapshot;
  applySnapshot = function (snap) {
    const took = oldApply(snap);
    if (took) { applyChanges(); setView(state.view); }
    return took;
  };

  // ---------------------------------------------------------------- Top Picks
  // 1 the line that says who left, under the title
  const oldStart = renderStart;
  renderStart = function () {
    oldStart();
    const title = document.getElementById('startTitle');
    const old = document.getElementById('grLeft');
    if (old) old.remove();
    if (title && left.length) title.insertAdjacentHTML('afterend',
      `<p class="gr-line" id="grLeft">${N(1)}Growing now fails an app whose own card says “Not growing”. Left the picks: <b>${left.map(e => esc(e.name)).join(', ')}</b>.</p>`);
  };

  // 2 the Tier List: a coin cheap enough to be a pick says which gate held it back
  const WHY = {'thin liquidity': 'liquidity', 'heavy dilution': 'dilution', 'supply sources disagree': 'supply data', 'not growing': 'not growing'};
  const oldIcon = tlIcon;
  tlIcon = function (e, t) {
    const html = oldIcon(e, t);
    const fails = (e.degen_fail || []).filter(f => f !== 'drahé');
    if (e.degen_ok === true || !fails.length || !(e.potential >= ((DEGEN.rules || {}).min_potential || 2.5))) return html;
    const words = fails.map(f => { const r = nearReason(f); return WHY[r.short] || WHY[r.full] || r.short; });
    return html.replace(/<\/button>$/, `<span class="gr-why" title="Cheap enough to be a pick. Held back by: ${esc(fails.map(f => nearReason(f).full).join(', '))}.">${esc(words.join(' + '))}</span></button>`);
  };
  const oldTiers = renderTierList;
  renderTierList = function () {
    oldTiers();
    const meta = document.querySelector('#startTiers .tl-meta');
    if (meta && !document.getElementById('grTier')) meta.insertAdjacentHTML('afterend',
      `<p class="gr-line" id="grTier">${N(2)}Under S every coin with an upside of 2.5x or more failed a gate. Each one now says which.</p>`);
  };

  // 3 upside on what reaches the token: the benchmark pays its holders all of its revenue
  const benchShare = () => { const b = APPS.find(a => a.name === BENCH.label); return b && num(b.holders_share) && b.holders_share > 0 ? b.holders_share : 1; };
  const heldUp = e => num(e.holders_share) && num(e.potential_raw) ? e.potential_raw * e.holders_share / benchShare() : null;
  const oldHead = degenCardHead;
  degenCardHead = function (e, info) {
    const html = oldHead(e, info), h = heldUp(e);
    const line = h === null
      ? `<div class="gr-hold">${N(3)}<b class="gr-mute">?</b><small>for holders: share unknown</small></div>`
      : `<div class="gr-hold">${N(3)}<b class="${h < 1 ? 'gr-bad' : (h >= 2.5 ? 'gr-good' : '')}">${mult(h)}</b><small>for holders: they get ${Math.round(100 * e.holders_share)}% of revenue</small></div>`;
    return html + line;
  };

  // ---------------------------------------------------------------- Apps and Chains rows
  // 3 and 4 under the upside of an app, 6 under the upside of a chain
  const oldPot = potentialCell;
  potentialCell = function (e) {
    const html = oldPot(e);
    if (!num(e.potential_raw)) return html;
    const subs = [];
    if (CHAINS.indexOf(e) >= 0) {
      const f = e.potential_fees_raw;
      if (num(f) && f > 0) {
        const apart = Math.max(f, e.potential_raw) / Math.min(f, e.potential_raw) >= 5;
        subs.push(`<span class="gr-sub${apart ? ' gr-bad' : ''}" title="The same chain measured on the fees it keeps or burns, against the median chain. ${apart ? 'The two measures are 5x or more apart.' : ''}">${N(6)}by fees ${f >= UPSIDE_CAP ? '&gt;' + fmtMult(UPSIDE_CAP) : mult(f)}</span>`);
      }
      if (e._gr8) subs.push(`<span class="gr-sub" title="Nothing held back: DEX volume and users count as DeFiLlama gives them. The benchmark is unchanged.">${N(8)}was ${mult(e._gr8.was)} held back</span>`);
    } else {
      const h = heldUp(e), dil = e.sa_dilution_12m_pct;
      if (h !== null && e.holders_share < 0.95)
        subs.push(`<span class="gr-sub${h < 1 ? ' gr-bad' : ''}" title="Upside on the revenue that reaches the token: holders get ${Math.round(100 * e.holders_share)}%, ${esc(BENCH.label || 'the benchmark')}’s get ${Math.round(100 * benchShare())}%.">${N(3)}holders ${mult(h)}</span>`);
      if (num(dil) && dil >= 25)
        subs.push(`<span class="gr-sub gr-bad" title="Upside per token once the next 12 months of new tokens are out: +${Math.round(dil)}% of today’s circulating supply.">${N(4)}after dilution ${mult(e.potential_raw / (1 + dil / 100))}</span>`);
    }
    return subs.length ? `<span class="gr-up">${html}${subs.join('')}</span>` : html;
  };

  // 5 Strength 3M against the market cap, not the price: the price factor times the new tokens of three months
  const oldSila = silaCell;
  silaCell = function (e) {
    const s = silaOf(e), wk = e.sa_week_pct;
    if (CHAINS.indexOf(e) >= 0 || !num(s.ratio) || !num(wk) || wk <= 0) return oldSila(e);
    const grew = Math.pow(1 + wk / 100, 13);
    if (grew < 1.03) return oldSila(e);
    const adj = Object.assign({}, e, {sila3m: Object.assign({}, s, {ratio: s.ratio / grew}), sila6m: null});
    return `<span class="gr-up">${oldSila(adj)}<span class="gr-sub" title="Revenue growth against the market cap’s growth: the supply grows about ${Math.round(100 * (grew - 1))}% in three months at the schedule’s pace.">${N(5)}was ${s.ratio.toFixed(2)}x by price</span></span>`;
  };

  // 7 a chain whose DEX volume AND stablecoins both fell by 30% or more in a year says so beside its name (DEX volume
  // alone fell on most chains: the median chain is down about half, so that alone would mark nearly every row)
  const yearChange = m => {
    const full = (m || []).filter(x => x && !x.partial && num(x.v) && x.v > 0);
    return full.length >= 12 ? full[full.length - 1].v / full[0].v - 1 : null;
  };
  const oldName = nameCell;
  nameCell = function (e) {
    const html = oldName(e);
    if (CHAINS.indexOf(e) < 0) return html;
    const dex = yearChange(e.monthly_dex), st = yearChange(e.monthly_stables);
    if (dex === null || st === null || dex > -0.3 || st > -0.3) return html;
    const tag = `<span class="tag gr-shrink" title="Last full month against the same month a year ago: DEX volume ${fmtPct(100 * dex, 0)}, stablecoins on the chain ${fmtPct(100 * st, 0)}.">${N(7)}shrinking</span>`;
    return html.replace('</span><span class="sym">', tag + '</span><span class="sym">');
  };

  // ---------------------------------------------------------------- Sectors
  // 9 the sector's own return and its return against BTC under the figure against the median
  const oldVs = vsMedCell;
  vsMedCell = function (th, k) {
    const html = oldVs(th, k), own = th[k === '1m' ? 'theme_4w' : 'theme_13w'], rs = th[k === '1m' ? 'rs1m' : 'rs3m'];
    if (!num(own) || !num(rs)) return html;
    return `<span class="gr-up">${html}<span class="gr-sub">itself ${fmtPct(100 * own, 0)}</span><span class="gr-sub ${rs > 0 ? 'gr-good' : 'gr-bad'}">vs BTC ${fmtPct(100 * rs, 0)}</span></span>`;
  };
  const oldStage = stageCell;
  stageCell = function (th) {
    const html = oldStage(th);
    return th._gr9 && th._gr9.was !== th.stage && STAGE[th._gr9.was]
      ? html.replace(/<\/span>$/, `<span class="sub stwas gr-was">${N(9)}today’s page: ${esc(STAGE[th._gr9.was].name)}</span></span>`) : html;
  };
  const oldHot = renderHotNow;
  renderHotNow = function () {
    oldHot();
    const el = document.getElementById('hotNow');
    if (!el || !themesNew()) return;
    const ok = THEMES.filter(th => num(th.theme_4w) && num(th.rs1m));
    const fell = ok.filter(th => th.theme_4w < 0).length, lost = ok.filter(th => th.rs1m <= 0).length;
    const link = th => `<a href="#" data-theme="${esc(th.key)}">${esc(themeName(th))}</a>`;
    const hot = THEMES.filter(th => th.stage === 'hot'), hold = THEMES.filter(th => th.stage === 'holding').sort((a, b) => b.rs1m - a.rs1m);
    const em = THEMES.filter(th => th.stage === 'emerging');
    const lows = ok.map(th => th.theme_4w).sort((a, b) => a - b);
    let s = `${N(9)}<b>Hot right now:</b> `;
    s += hot.length ? hot.map(th => `${link(th)} ${fmtPct(100 * th.rs1m, 0)} vs BTC this month`).join(' · ') + '.'
      : `nothing. ${fell === ok.length ? 'All ' + ok.length : fell + ' of ' + ok.length} sectors fell over the month (${fmtPct(100 * lows[lows.length - 1], 0)} to ${fmtPct(100 * lows[0], 0)}) and ${lost === ok.length ? 'all ' + ok.length : lost + ' of ' + ok.length} lost to BTC.`;
    if (hold.length) s += ` <b>Holding up best:</b> ` + hold.map(th => `${link(th)} (${fmtPct(100 * th.theme_4w, 0)}, ${fmtPct(100 * th.rs1m, 0)} vs BTC)`).join(', ') + '.';
    if (em.length) s += ` <b>Starting to rise against the others:</b> ` + em.map(link).join(', ') + '.';
    el.innerHTML = s;
    el.querySelectorAll('a[data-theme]').forEach(a => a.addEventListener('click', ev => { ev.preventDefault(); openThemePanel(a.dataset.theme); }));
  };

  // 10 Talked about says how many people it rests on
  const oldTalk = talkCell;
  talkCell = function (th) {
    const html = oldTalk(th), a = th.attention || {};
    if (!num(a.people)) return html;
    return `<span class="gr-up">${html}<span class="gr-sub">${N(10)}${a.people} ${a.people === 1 ? 'person' : 'people'}${num(a.total_people) ? ' of ' + a.total_people : ''}</span></span>`;
  };

  // ---------------------------------------------------------------- the tour: where each change is. Ours only.
  function flash(el) {
    if (!el) return;
    el.scrollIntoView({block: 'center', behavior: 'smooth'});
    el.classList.add('gr-flash');
    setTimeout(() => el.classList.remove('gr-flash'), 2600);
  }
  const closeIt = () => { const p = document.getElementById('panel'); if (p && p.classList.contains('open')) closePanel(); };
  const go = (view, find) => { closeIt(); setView(view); setTimeout(() => flash(find()), 250); };
  const withBadge = (root, n) => { const b = [...document.querySelectorAll(root + ' .gr-n')].find(x => x.textContent === String(n)); return b ? (b.closest('tr, .dcard, .tl-row, p') || b.parentElement) : null; };
  const STEPS = [
    [1, 'Top Picks', 'Growing fails a card that says “Not growing”', () => go('start', () => document.getElementById('grLeft'))],
    [2, 'Top Picks', 'Tier List: which gate held a coin back', () => go('start', () => document.querySelector('#startTiers .tl-row.t-A') || document.getElementById('grTier'))],
    [3, 'Top Picks, Apps', 'Upside on what holders get', () => go('start', () => document.querySelector('#startCards .dcard'))],
    [4, 'Apps', 'Upside after a year of new tokens', () => go('apps', () => withBadge('#view-apps', 4))],
    [5, 'Apps', 'Strength 3M by market cap', () => go('apps', () => withBadge('#view-apps', 5))],
    [6, 'Chains', 'Upside by fees on the row', () => go('chains', () => { const bad = document.querySelector('#view-chains .gr-sub.gr-bad'); return bad ? bad.closest('tr') : withBadge('#view-chains', 6); })],
    [7, 'Chains', 'A shrinking chain says so', () => go('chains', () => withBadge('#view-chains', 7))],
    [8, 'Chains', 'Nothing held back', () => go('chains', () => withBadge('#view-chains', 8))],
    [9, 'Sectors', 'Hot must beat BTC; ahead means 3+ points', () => go('sectors', () => document.getElementById('hotNow'))],
    [10, 'Sectors', 'Talked about: how many people', () => go('sectors', () => withBadge('#view-sectors', 10))],
  ];
  function tour() {
    const box = document.createElement('aside');
    box.id = 'grTour';
    const live = 'https://cymetica.com/gem-screener/app';
    box.innerHTML = `<header><span>10 changes · click one</span><span><button id="grClean" title="Hide or show the numbers">numbers</button> <button id="grMin" title="Fold">–</button></span></header>
      <ol>${STEPS.map(([n, where, t]) => `<li data-n="${n}">${N(n)}<span>${esc(t)}<small>${esc(where)}</small></span></li>`).join('')}</ol>
      <footer>The benchmark is unchanged. <a href="${live}" target="_blank" rel="noopener" id="grLive">Open the original ↗</a></footer>`;
    document.body.appendChild(box);
    box.querySelectorAll('li[data-n]').forEach(li => {
      li.onclick = () => {
        box.querySelectorAll('li').forEach(x => x.classList.remove('on'));
        li.classList.add('on');
        STEPS.find(s => String(s[0]) === li.dataset.n)[3]();
      };
    });
    box.querySelector('#grMin').onclick = () => box.classList.toggle('min');
    box.querySelector('#grClean').onclick = () => document.body.classList.toggle('gr-clean');
    box.querySelector('#grLive').onclick = function () { this.href = live + '?view=' + encodeURIComponent(state.view || 'start'); };
  }
  window.grPeek = () => ({apps: APPS, chains: CHAINS, themes: THEMES, degen: DEGEN, left});
  setTimeout(tour, 0);
}
