/* Capital Maximizer: one model for every figure the page shows -- the cards, the three strategies, the plan.
   Rates come from data.js (DefiLlama, each by pool id). A month is (1+APY)^(1/12).
   Max profit, the one figure shown: the month ETH and BTC rise by MOVE and today's rates hold.
   The bad month (ETH and BTC down by MOVE, yields halved, borrowing as today) is never shown; it decides what each
   tier may offer. A loop is liquidated where its debt reaches the market's LTV. */
(function (root) {
  const D = root.CM_DATA;
  const MOVE = 0.2;
  const STEP = 0.1;                 // leverage is tuned in tenths
  const LEVERS = [1.5, 2, 2.5, 3, 4, 5];
  // worst: the most a bad month may take; safeLiq: liquidation must sit 5 points past the bad month
  const TIERS = [
    {id: 'conservative', name: 'Conservative', worst: 0, maxL: 1, safeLiq: true, types: ['vaults']},
    {id: 'medium', name: 'Medium', worst: 0.15, maxL: 3, safeLiq: true, types: ['stableloop', 'lp', 'loop']},
    {id: 'high', name: 'High Risk', worst: 0.5, maxL: 3, safeLiq: true, types: ['stableloop', 'lp', 'loop']},
    {id: 'og', name: 'OG Gambler', worst: 1, maxL: 5, safeLiq: false, types: ['stableloop', 'lp', 'loop']},
  ];
  const NEAREST = 0.95;             // no route is ever closer than a 5 % move to liquidation

  const month = apy => Math.pow(1 + apy / 100, 1 / 12);
  const tenth = L => Math.round(L * 10) / 10;
  const stakeOf = sym => D.pools.find(p => p.role === 'stake' && p.symbol === sym);
  const name = project => D.protocols[project].name;

  /* one dollar of equity at L times leverage after the month: collateral L earning y, debt L-1 costing b */
  function loop({L, y, b, lt, bonus, P}) {
    const debt = L - 1, pLiq = debt > 0 ? debt / (L * lt) : null;
    if (pLiq !== null && P <= pLiq) {
      const left = Math.max(0, L - debt * (1 + bonus) / pLiq);    // tokens the liquidator leaves behind
      return {value: left * P, liquidated: true, pLiq};
    }
    return {value: L * P * month(y) - debt * month(b), liquidated: false, pLiq};
  }

  /* one dollar in an ETH/USDC pool: a full-range Uniswap position holds sqrt(P), a GMX GM pool half and half */
  function lp({kind, fee, P}) {
    return (kind === 'uniswap' ? Math.sqrt(P) : (1 + P) / 2) * month(fee);
  }

  const bonusOf = m => m.project === 'morpho-blue' ? Math.min(0.15, 1 / (0.3 * m.ltv + 0.7) - 1) : 0.05;

  function vaultRoutes() {
    const v = D.pools.filter(p => p.role === 'vault'), out = [];
    for (let i = 0; i < v.length; i++) for (let j = i + 1; j < v.length; j++) for (let k = j + 1; k < v.length; k++) {
      const three = [v[i], v[j], v[k]];
      if (new Set(three.map(p => p.project)).size < 3) continue;
      three.sort((a, b) => b.apy - a.apy);
      const avg = f => three.reduce((t, p) => t + f(p), 0) / 3;
      out.push({
        id: 'vaults:' + three.map(p => p.id.slice(0, 8)).join('+'), type: 'vaults', L: 1, asset: null, stables: true,
        family: 'vaults|' + three.map(p => p.project).sort().join('+'),
        label: 'Stable split', venue: three.map(p => name(p.project)).join(' · '),
        chain: [...new Set(three.map(p => p.chain))].join(' · '),
        up: avg(p => month(p.apy)), bad: avg(p => month(p.apy / 2)), pLiq: null, liqInBad: false,
        legs: three.map(p => ({project: p.project, pool: p.id, role: 'supply', rate: p.apy, share: 1 / 3})),
        steps: [{kind: 'source'}, ...three.map(p => ({kind: 'vault', project: p.project, title: p.name, chain: p.chain,
          rate: p.apy, share: 1 / 3}))],
      });
    }
    return out;
  }

  function lpRoutes(s) {
    return D.pools.filter(p => p.role === 'lp').map(p => ({
      id: 'lp:' + p.id.slice(0, 8), type: 'lp', L: 1, asset: 'ETH', stables: false, family: 'lp|' + p.project,
      label: 'ETH/USDC pool', venue: `${name(p.project)} · ${p.name.replace('ETH/USDC ', '').replace('GM ETH-USDC', 'GM')}`,
      chain: p.chain,
      up: lp({kind: p.kind, fee: p.apy, P: 1 + s}), bad: lp({kind: p.kind, fee: p.apy / 2, P: 1 - s}),
      pLiq: null, liqInBad: false,
      legs: [{project: p.project, pool: p.id, role: 'lp', rate: p.apy}],
      steps: [{kind: 'source'},
        {kind: 'swap', project: p.project, title: 'Half to ETH', chain: p.chain},
        {kind: 'lp', project: p.project, title: p.name, chain: p.chain, rate: p.apy}],
    }));
  }

  function holdRoutes(s) {                                       // L = 1: just hold the staked token
    return D.pools.filter(p => p.role === 'stake').map(st => {
      const usd = st.asset === 'USD', up = usd ? 1 : 1 + s, dn = usd ? 1 : 1 - s;
      return {
        id: 'hold:' + st.id.slice(0, 8), type: usd ? 'stableloop' : 'loop', L: 1, asset: st.asset, stables: usd,
        family: 'hold|' + st.project, label: `Staked ${st.token}`, venue: name(st.project), chain: st.chain,
        up: up * month(st.apy), bad: dn * month(st.apy / 2), pLiq: null, liqInBad: false,
        legs: [{project: st.project, pool: st.id, role: 'stake', rate: st.apy}],
        steps: [{kind: 'source'},
          {kind: 'swap', project: usd ? 'curve-dex' : 'uniswap-v3', title: usd ? 'USDC → USDe' : 'USDC → ' + st.token, chain: st.chain},
          {kind: 'stake', project: st.project, title: st.token, chain: st.chain, rate: st.apy}],
      };
    });
  }

  /* a loop: buy the collateral, deposit it, borrow, buy more, until the position is L times the money put in;
     null where the market would not lend that much */
  function loopRoute(m, L, s) {
    L = tenth(L);
    if ((L - 1) / L >= m.ltv) return null;
    const st = m.stake ? stakeOf(m.stake) : null, usd = m.asset === 'USD';
    const y = m.apy + (st ? st.apy : 0), bonus = bonusOf(m);
    const g = loop({L, y, b: m.borrow, lt: m.ltv, bonus, P: usd ? 1 : 1 + s});
    const w = loop({L, y: y / 2, b: m.borrow, lt: m.ltv, bonus, P: usd ? 1 : 1 - s});
    const legs = [{project: m.project, pool: m.id, role: 'collateral', rate: m.apy},
      {project: m.project, pool: m.loan_pool || m.id, role: 'borrow', rate: m.borrow}];
    if (st) legs.unshift({project: st.project, pool: st.id, role: 'stake', rate: st.apy});
    const steps = [{kind: 'source'},
      {kind: 'swap', project: usd ? 'curve-dex' : 'uniswap-v3', chain: m.chain, title: usd ? 'USDC → USDe' : `USDC → ${m.token}`}];
    if (st) steps.push({kind: 'stake', project: st.project, title: m.token, chain: m.chain, rate: st.apy});
    steps.push({kind: 'collateral', project: m.project, title: 'Collateral', chain: m.chain, rate: m.apy, ltv: m.ltv},
      {kind: 'borrow', project: m.project, title: 'Borrow ' + m.loan, chain: m.chain, rate: m.borrow, loan: m.loan});
    return {
      id: `loop:${m.id.slice(0, 8)}:${L}`, type: usd ? 'stableloop' : 'loop', L, asset: m.asset, stables: usd,
      family: `${usd ? 'stableloop' : 'loop'}|${m.asset}|${m.project}`, market: m.id, ltv: m.ltv,
      label: `${m.token} loop`, venue: name(m.project), chain: m.chain,
      up: g.value, bad: w.value, pLiq: g.pLiq, liqInBad: w.liquidated, legs, steps,
    };
  }

  function loopRoutes(s) {
    const out = [];
    for (const m of D.pools.filter(p => p.role === 'market')) for (const L of LEVERS) {
      const r = loopRoute(m, L, s);
      if (r) out.push(r);
    }
    return out;
  }

  const cache = {};
  function routes(s = MOVE) {
    if (!cache[s]) cache[s] = [...vaultRoutes(), ...lpRoutes(s), ...holdRoutes(s), ...loopRoutes(s)];
    return cache[s];
  }

  const pct = x => Math.round(x * 100) + '%';
  function reject(t, r, s) {
    if (r.L > t.maxL) return `${r.L}× leverage, ${t.name} stops at ${t.maxL}×`;
    if (r.pLiq !== null && r.pLiq > NEAREST) return `liquidated by a ${pct(1 - r.pLiq)} move`;
    if (r.up <= 1) return 'costs more than it pays';
    if (r.liqInBad && t.safeLiq) return `liquidated if ${r.asset} falls ${pct(s)}`;
    if (r.bad < 1 - t.worst) return `loses ${pct(1 - r.bad)} in a bad month`;
    if (t.safeLiq && r.pLiq !== null && r.pLiq > 1 - s - 0.05) return `liquidation at ${pct(1 - r.pLiq)}, too close`;
    return null;
  }

  const tierOf = id => TIERS.find(x => x.id === id);
  function find(tierId, s = MOVE) {
    const t = tierOf(tierId);
    const all = routes(s).filter(r => t.types.includes(r.type));
    const fit = [], rejected = [];
    for (const r of all) {
      const reason = reject(t, r, s);
      if (reason) rejected.push(Object.assign({}, r, {reason})); else fit.push(r);
    }
    fit.sort((a, b) => b.up - a.up);
    rejected.sort((a, b) => b.up - a.up);
    return {tier: t.id, s, scanned: D.scanned, built: all.length, fit, rejected, best: fit[0]};
  }

  /* the three best of different kinds: one per family, so three loops on one market at three leverages never fill it */
  function top3(tierId, s = MOVE) {
    const seen = new Set(), out = [];
    for (const r of find(tierId, s).fit) {
      if (seen.has(r.family)) continue;
      seen.add(r.family);
      out.push(r);
      if (out.length === 3) break;
    }
    return out;
  }

  /* how far the leverage of a loop may be tuned: from 1.5x to the tier's cap, while the market would still lend and
     liquidation stays at least a 5 % move away */
  function range(r, tierId) {
    if (!r.market) return null;
    const m = D.pools.find(p => p.id === r.market), t = tierOf(tierId);
    let max = 1.5;
    for (let L = 1.5; L <= t.maxL + 1e-9; L = tenth(L + STEP)) {
      const x = loopRoute(m, L, MOVE);
      if (!x || x.pLiq > NEAREST) break;
      max = L;
    }
    return {min: 1.5, max, step: STEP};
  }

  function tune(r, L, s = MOVE) {
    if (!r.market) return null;
    return loopRoute(D.pools.find(p => p.id === r.market), L, s);
  }

  const profit = (r, amount) => amount * (r.up - 1);
  function card(tierId) {
    const route = top3(tierId)[0];
    return {up: route.up, route};
  }

  root.CM = {MOVE, TIERS, month, loop, lp, routes, find, top3, range, tune, profit, card};
})(typeof window !== 'undefined' ? window : globalThis);
