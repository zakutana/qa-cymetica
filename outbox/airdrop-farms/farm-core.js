/* Airdrop Farmer, the logic: carried over unchanged from the page before the redesign. */

/* Airdrop Farmer: the design and a local test version in one page.
   ?shot=1 is the state the Build it Better pictures show (render.py), computed by the same code: the Farms tab
   before Start, and Live farms after a 23-day run of that same plan. Without it every control works on test data
   kept in this browser only. Nothing here talks to any server; the farm logos load from DefiLlama's icon CDN. */
const Q = new URLSearchParams(location.search);
const SHOT = Q.has("shot");
let TAB = Q.get("tab") || "farms";
const KEY = "airdrop-farmer-test-v3";
const H = 6;     // every estimate is over six months
const E = .7;    // a bigger wallet gets less per dollar: most airdrops flatten whales
const FIX = 5;   // gas to enter a farm, so the best split does not scatter $50 bets
const fmt = n => Math.round(n).toLocaleString("en-US");
const usd = n => "$" + fmt(n);
const r10 = n => Math.round(n / 10) * 10;
const money = n => n < 100 ? "$" + Math.round(n) : usd(r10(n)); // small amounts to the dollar
const rng = (lo, hi, sep = " – ") => Math.round(lo) === Math.round(hi) ? money(lo) : money(lo) + sep + money(hi);
const kM = v => v >= 1e9 ? +(v / 1e9).toFixed(1) + "B" : Math.round(v / 1e6) + "M";
const logoSvg = () => `<svg><use href="#logo"/></svg>`;
const BOLT = `<svg viewBox="0 0 24 24" fill="currentColor"><path d="M13.5 2 4 14h6.5L9.5 22 20 9.5h-6.6z"/></svg>`;
const $ = s => document.querySelector(s);
function mulberry32(a) { return () => { a |= 0; a = a + 0x6D2B79F5 | 0; let t = Math.imul(a ^ a >>> 15, 1 | a); t = t + Math.imul(t ^ t >>> 7, 61 | t) ^ t; return ((t ^ t >>> 14) >>> 0) / 4294967296; }; }
const rnd = SHOT ? mulberry32(7) : Math.random; // the pictures come out the same every run
// the farms' own logos: embedded where the page carries them (the shareable copy), else from DefiLlama's icon CDN
const ICON = s => (window.LOGOS && window.LOGOS[s]) || `https://icons.llamao.fi/icons/protocols/${s}?w=96`;

/* ---------- farms: the examples from the live points programs, then test data ---------- */
// ref: the amount lo/hi (est. airdrop over 6 months) are given at; cf: gas per 6 months; cp: fees and funding per
// $1,000 per 6 months; ppw: points a week at ref; chip: the one thing a degen needs to know about the farm.
const FARMS = [
  {id: "arcus", o: "o1", ini: "AR", icon: "arcus-perps", name: "Arcus", chip: ["TOKEN CONFIRMED", "g"], how: "Deposit", season: "Season 1", ref: 1000, lo: 260, hi: 940, cf: 1, cp: 0, ppw: 1840, pool: .05, fdv: 250e6, live: {pts: 1}},
  {id: "variational", o: "o2", ini: "VA", icon: "variational", name: "Variational", chip: ["TGE Q4 2026", "g"], how: "Trade", season: "TGE Q4 2026", ref: 800, lo: 180, hi: 720, cf: 0, cp: 42.5, ppw: 420, pool: .32, fdv: 60e6, live: {pts: 1, tge: 30, tk: "VAR", px: .45}},
  {id: "polymarket", o: "o3", ini: "PM", icon: "polymarket-international", name: "Polymarket", chip: ["PAYS DAILY", "c"], how: "LP", season: "LP rewards", ref: 600, lo: 40, hi: 310, cf: 0, cp: 10, ppw: 0, pool: .05, fdv: 5e9, live: {daily: .0004, tk: "pUSD", px: 1}},
  {id: "lighter", o: "o1", ini: "LI", icon: "lighter-perps", name: "Lighter", chip: ["PAYS WEEKLY", "c"], how: "Trade", season: "11M LIT pool", ref: 500, lo: 90, hi: 260, cf: 0, cp: 44, ppw: 0, pool: .011, fdv: 1.6e9, live: {weekly: .007, tk: "LIT", px: 1.92}},
  {id: "risex", o: "o2", ini: "RX", icon: "risex", name: "RISEx", chip: ["POINTS LIVE", "c"], how: "Trade", season: "Season 1", ref: 400, lo: 70, hi: 410, cf: 0, cp: 42.5, ppw: 2730, pool: .08, fdv: 150e6, live: {pts: 1}},
  {id: "nado", o: "o3", ini: "NA", icon: "nado-perps", name: "Nado", chip: ["POINTS → INK", "g"], how: "Trade", season: "Season 2", ref: 400, lo: 60, hi: 300, cf: 0, cp: 40, ppw: 4270, pool: .04, fdv: 300e6, live: {pts: 1, tge: 45, tk: "INK", px: .12}},
  {id: "n1", o: "o4", ini: "N1", icon: "n1-exchange-perps", name: "N1", chip: ["POINTS LIVE", "c"], how: "Trade", season: "Season 1", ref: 300, lo: 30, hi: 250, cf: 0, cp: 43, ppw: 2400, pool: .06, fdv: 100e6, live: {pts: 1}},
  {id: "ostium", o: "o1", ini: "OS", icon: "ostium", name: "Ostium", chip: ["POINTS LIVE", "c"], how: "Trade", season: "Season 2", ref: 300, lo: 40, hi: 190, cf: 0, cp: 40, ppw: 980, pool: .05, fdv: 120e6, live: {pts: 1, cap0: .62, capDay: .0083}},
  {id: "base", o: "o3", ini: "BA", icon: "base-app", name: "Base", chip: ["SPECULATIVE", "m"], how: "Bridge", season: "no points program", lo: null, cf: 3, cp: 0, why: "no points program yet", live: {txs: 1.5}},
  {id: "pacifica", o: "o2", ini: "PA", icon: "pacifica-perps", name: "Pacifica", chip: ["POINTS LIVE", "c"], how: "Trade", season: "Season 1", ref: 250, lo: 20, hi: 140, cf: 0, cp: 40, ppw: 630, pool: .05, fdv: 80e6, live: {pts: 1}},
  {id: "arc", o: "o1", ini: "AC", name: "Arc Testnet", chip: ["FREE", "f"], how: "Testnet", season: "testnet", lo: null, free: 1, why: "no points rate published", live: {txs: 3}},
  {id: "axis", o: "o2", ini: "AX", name: "Axis Robotics", chip: ["FREE", "f"], how: "Tasks", season: "2-week epochs", lo: null, free: 1, why: "no points rate published", live: {tasks: 1, epoch: 14}},
];
// not listed: a farm with nothing to farm now (Extended, its points cap used up; Hyperliquid, no points phase)
if (!SHOT) { // test farms, so the list is long enough to try search and big amounts
  [["Lending", "Deposit", 0, [["Alpha", 400, .26], ["Beta", 600, .22], ["Gamma", 500, .19], ["Delta", 800, .16]]],
   ["Vault", "LP", 8, [["Alpha", 500, .24], ["Beta", 700, .2], ["Gamma", 400, .18], ["Delta", 900, .14]]],
   ["Chain", "Bridge", 4, [["Alpha", 300, .21], ["Beta", 400, .17], ["Gamma", 250, .15]]],
   ["Predict", "LP", 10, [["Alpha", 300, .2]]],
   ["Perp", "Trade", 40, [["Alpha", 400, .27], ["Beta", 300, .22]]],
  ].forEach(([label, how, cp, list], j) => list.forEach(([gr, ref, eff], i) => {
    const mid = (eff + cp / 1000) * ref;
    FARMS.push({id: (label + gr).toLowerCase(), o: ["o1", "o2", "o3", "o4"][(i + j) % 4], ini: label[0] + gr[0], name: label + " " + gr,
      chip: ["POINTS LIVE", "c"], how, season: "test data", ref, lo: r10(mid * .45), hi: r10(mid * 1.55), cf: cp ? 0 : 1, cp,
      ppw: ref * 3, pool: .05, fdv: 200e6, live: {pts: 1}, test: 1});
  }));
  [["Testnet Alpha", "Testnet"], ["Testnet Beta", "Testnet"], ["Tasks Alpha", "Tasks"]].forEach(([name, how], i) =>
    FARMS.push({id: name.replace(" ", "").toLowerCase(), o: ["o2", "o3", "o1"][i], ini: name[0] + name.split(" ")[1][0], name, chip: ["FREE", "f"],
      how, season: "test data", lo: null, free: 1, why: "no points rate published", live: how === "Tasks" ? {tasks: 1, epoch: 14} : {txs: 2}, test: 1}));
}
const BY = Object.fromEntries(FARMS.map(f => [f.id, f]));
// heat 0-100: how much the groups talk about a farm now, from Cymetica's own sentiment engine; EARLY: few talk about
// it yet, and the engine sees potential. Test values here; test farms get a stable number from their id.
const HEAT = {polymarket: 96, variational: 91, lighter: 88, base: 84, arcus: 79, risex: 72, nado: 64, ostium: 55, arc: 47, n1: 41, pacifica: 38, axis: 22};
const EARLY = new Set(["n1", "pacifica", "axis", "lendinggamma", "vaultgamma"]);
FARMS.forEach(f => {
  let h = 0; for (const ch of f.id) h = (h * 31 + ch.charCodeAt(0)) % 997;
  f.heat = HEAT[f.id] ?? 15 + h % 60;
  f.early = EARLY.has(f.id);
});
const byHeat = (a, b) => b.heat - a.heat;

/* ---------- the maths ---------- */
const curve = (f, x) => Math.pow(Math.max(0, x) / f.ref, E);
function est(f, x, months = H) {
  if (f.lo == null || x <= 0) return null;
  const k = curve(f, x) * months / 6;
  return {lo: f.lo * k, hi: f.hi * k};
}
const cost = (f, x, months = H) => f.free || x <= 0 ? 0 : (f.cf + (f.cp || 0) * x / 1000) * months / 6;
// what a farm brings in six months: the airdrop, plus what it pays out daily on the way (Polymarket's LP rewards)
function estPlan(f, x) {
  const e = est(f, x);
  if (!e) return null;
  const p = f.live.daily ? f.live.daily * x * 180 : 0;
  return {lo: e.lo + p, hi: e.hi + p};
}
const midAt = (f, x) => { const e = estPlan(f, x); return e ? (e.lo + e.hi) / 2 : 0; };
const weekly = (f, x) => midAt(f, x) / 180 * 7 / f.live.px; // a weekly payer pays its estimate out week by week
const ptsWeek = (f, x) => (f.ppw || 0) * x / f.ref; // points are linear in what is deposited
const eff = f => f.lo == null ? -1 : midAt(f, f.ref) / f.ref - (f.cp || 0) / 1000;
// best first: estimated farms by what a dollar earns, then free ones, then the rest
const rank = f => f.lo != null ? 1 - eff(f) : f.free ? 2 : 3;
// the best split of an amount: a first ticket, then a step at a time, always to the farm where the next dollar
// earns most net of costs and gas, at most 20% of the amount in one farm; a farm with no estimate gets nothing
function recommend(B) {
  const a = {}, ok = FARMS.filter(f => f.lo != null && !f.free);
  ok.forEach(f => a[f.id] = 0);
  const step = Math.max(10, Math.ceil(B / 500 / 10) * 10), t0 = Math.max(step, Math.round(B * .05 / 10) * 10);
  let left = B;
  while (left >= step) {
    let best = null, bm = .05, add = 0;
    for (const f of ok) {
      const d = a[f.id] ? step : t0;
      if (d > left || a[f.id] + d > B * .2) continue;
      const m = (midAt(f, a[f.id] + d) - midAt(f, a[f.id]) - (a[f.id] ? 0 : FIX)) / d - (f.cp || 0) / 1000;
      if (m > bm) { bm = m; best = f; add = d; }
    }
    if (!best) break;
    a[best.id] += add; left -= add;
  }
  for (const id in a) a[id] = Math.round(a[id] / 10) * 10;
  return a;
}

/* ---------- state ---------- */
const DEFAULT = () => ({budget: 5000, balance: 7240, amt: {}, on: {}, last: {}, custom: false, q: "", farming: null, speed: 4});
let S = DEFAULT();
if (!SHOT) try { const s = JSON.parse(localStorage.getItem(KEY) || "null"); if (s) S = Object.assign(DEFAULT(), s); } catch (e) {}
const save = () => { if (SHOT) return; try { localStorage.setItem(KEY, JSON.stringify(S)); } catch (e) {} };
let REC = recommend(S.budget);
const rec = f => f.free ? 0 : (REC[f.id] || 0);
const amtOf = id => S.amt[id] || 0;
const planSum = () => FARMS.reduce((s, f) => s + (S.on[f.id] && !f.free ? amtOf(f.id) : 0), 0);
const liveSum = () => S.farming ? Object.values(S.farming.farms).reduce((s, l) => s + l.amount, 0) : 0;
const maxAmt = () => Math.floor(S.balance + liveSum()); // every farm can take up to all your USDC
// the list starts as the best split of the amount and follows it while you type
function applyBest() {
  FARMS.forEach(f => { const r = rec(f); S.amt[f.id] = f.free ? 0 : r; S.on[f.id] = f.free ? true : r > 0; });
  S.custom = false;
}
if (!S.custom) applyBest();

function toast(t) {
  const el = $("#toast");
  el.innerHTML = `<div class="toast">${t}</div>`;
  clearTimeout(toast.t);
  toast.t = setTimeout(() => el.innerHTML = "", 2600);
}
function floatUp(x, y, text) {
  const el = document.createElement("div");
  el.className = "float"; el.textContent = text;
  el.style.left = x - 24 + "px"; el.style.top = y - 34 + "px";
  document.body.appendChild(el);
  setTimeout(() => el.remove(), 1300);
}
// the initials sit under the logo, so a logo that does not load leaves a named orb, not an empty one
const logo = f => `<span class="logo ${f.o}">${f.ini}${f.icon ? `<img src="${ICON(f.icon)}" alt="" onerror="this.remove()">` : ""}</span>`;


function planTotals() {
  let lo = 0, hi = 0, n = 0, a = 0, c = 0, tok = 0;
  FARMS.forEach(f => {
    if (!S.on[f.id]) return;
    const x = f.free ? 0 : amtOf(f.id), e = estPlan(f, x);
    n++; a += x; c += Math.round(cost(f, x));
    if (f.chip[1] === "g") tok++;
    if (e) { lo += r10(e.lo); hi += r10(e.hi); }
  });
  return {lo, hi, n, a, c, tok};
}
// the big number counts to its new value
function tweenRange(el, lo, hi) {
  const from = el._v || [lo, hi]; el._v = [lo, hi];
  cancelAnimationFrame(el._raf);
  if (SHOT || (from[0] === lo && from[1] === hi)) { el.textContent = rng(lo, hi); return; }
  const t0 = performance.now();
  const step = now => {
    const k = Math.min(1, (now - t0) / 420), e = 1 - Math.pow(1 - k, 3);
    el.textContent = rng(from[0] + (lo - from[0]) * e, from[1] + (hi - from[1]) * e);
    if (k < 1) el._raf = requestAnimationFrame(step);
  };
  el._raf = requestAnimationFrame(step);
}

let moved = {usd: 0, n: new Set()};
function setAmt(id, v, quiet) {
  const f = BY[id];
  if (f.free) return;
  v = Math.max(0, Math.round(v || 0));
  let over = planSum() - (S.on[id] ? amtOf(id) : 0) + v - maxAmt();
  if (over > 0) {
    const others = FARMS.filter(g => g.id !== id && S.on[g.id] && !g.free && amtOf(g.id) > 0).sort((a, b) => rank(b) - rank(a));
    for (const g of others) {
      if (over <= 0) break;
      const take = Math.min(amtOf(g.id), over);
      S.amt[g.id] -= take; if (!S.amt[g.id]) S.on[g.id] = false;
      over -= take; moved.usd += take; moved.n.add(g.id);
      updateCard(g.id);
    }
    if (over > 0) { v -= over; if (!quiet) toast(`That is all your USDC: ${usd(maxAmt())}`); }
  }
  S.amt[id] = v; S.on[id] = v > 0; S.custom = true;
  if (v > 0) S.last[id] = v;
  S.budget = planSum();
  updateCard(id); updatePlan(); save();
  if (!quiet) tellMoved(f);
}
function tellMoved(f) {
  if (moved.usd > 0) toast(`${usd(moved.usd)} moved to ${f.name} from ${moved.n.size} farm${moved.n.size > 1 ? "s" : ""} that farm less`);
  moved = {usd: 0, n: new Set()};
}
// typing an amount means "split it for me"; on Enter, leaving the field or MAX it is held to the balance
function setBudget(B, commit) {
  B = Math.max(0, Math.round(B || 0));
  const most = maxAmt();
  if (commit && B > most) { B = most; toast(`Only ${usd(most)} USDC in your balance`); }
  S.budget = B; REC = recommend(B); applyBest();
  renderList(); updatePlan(); save();
}

/* ---------- start farming ---------- */
const FIRST = {Deposit: (n, f) => `Deposited ${n} into <b>${f}</b>`, Trade: (n, f) => `<b>${f}</b>: hedged positions opened, ${n}`,
  LP: (n, f) => `Quoting liquidity on <b>${f}</b> with ${n}`, Bridge: (n, f) => `Bridged ${n} to <b>${f}</b>`,
  Testnet: (n, f) => `<b>${f}</b>: testnet wallet set up`, Tasks: (n, f) => `<b>${f}</b>: first task started`};
const planLines = () => FARMS.filter(f => S.on[f.id]).sort((a, b) => rank(a) - rank(b)).map(f => ({f, a: f.free ? 0 : amtOf(f.id), e: estPlan(f, f.free ? 0 : amtOf(f.id))}));

function feed(txt, c = "cyan", d) {
  const F = S.farming;
  F.feed.unshift({d: d == null ? F.day : d, txt, c});
  F.feed.sort((p, q) => q.d - p.d);
  F.feed.length = Math.min(F.feed.length, 40);
}
function startFarms() {
  if (!S.farming) S.farming = {day: 0, farms: {}, hist: [{d: 0, lo: 0, hi: 0}], feed: [], claimed: 0, cost: 0, claims: []};
  const F = S.farming;
  planLines().forEach(({f, a}) => {
    const l = F.farms[f.id];
    if (!l) {
      F.farms[f.id] = {amount: a, start: F.day, pts: 0, lo: 0, hi: 0, cost: 0, n: 0, claim: 0, week: 0, got: 0, cap: f.live.cap0 || 0, tge: f.live.tge ? F.day + f.live.tge : null, done: false};
      S.balance -= a;
      feed(FIRST[f.how](usd(a), f.name), "cyan");
    } else if (l.amount !== a) {
      S.balance -= a - l.amount;
      feed(`<b>${f.name}</b>: ${a > l.amount ? "added" : "withdrew"} ${usd(Math.abs(a - l.amount))}`, "cyan");
      l.amount = a;
    }
  });
  for (const id of Object.keys(F.farms)) if (!S.on[id]) stopFarm(id, true);
  if (S.farming && !Object.keys(S.farming.farms).length) S.farming = null;
}
function confirmStart() { startFarms(); $("#modal").innerHTML = ""; save(); go("live"); }
const tokAmt = (f, n) => f.live.tge ? fmt(n) : f.live.weekly ? n.toFixed(1) : n.toFixed(2);
const pendUsd = (f, l) => (l.claim + (l.week || 0)) * (f.live.px || 0);
const claimable = (f, l) => f.live.daily ? l.claim >= 1 : l.claim > 0;
function claimFarm(id) {
  const F = S.farming, l = F && F.farms[id], f = BY[id];
  if (!l || !claimable(f, l)) return 0;
  const v = l.claim * f.live.px;
  l.got += v; F.claimed += v; F.claims.push(F.day);
  feed(`Claimed <em>${tokAmt(f, l.claim)} ${f.live.tk}</em> (${money(v)}) from <b>${f.name}</b>`, "green");
  if (f.live.tge) l.done = true;
  l.claim = 0;
  return v;
}
function stopFarm(id, quiet) {
  const F = S.farming, l = F && F.farms[id];
  if (!l) return;
  if (l.claim > 0) claimFarm(id);
  const back = Math.max(0, l.amount - l.cost);
  S.balance += back;
  delete F.farms[id];
  S.on[id] = false; S.amt[id] = 0; S.custom = true;
  feed(`<b>${BY[id].name}</b> stopped: ${usd(back)} back to your balance`, "red");
  if (!Object.keys(F.farms).length) { S.farming = null; if (!quiet) toast("All farms stopped"); }
  else if (!quiet) toast(`${BY[id].name} stopped · ${usd(back)} back`);
  S.budget = planSum();
}

/* ---------- the clock ---------- */
function advance(dd) {
  const F = S.farming;
  const d0 = F.day; F.day += dd;
  for (const [id, l] of Object.entries(F.farms)) {
    const f = BY[id], L = f.live;
    if (l.done) continue;
    const dc = cost(f, l.amount) / 180 * dd; l.cost += dc; F.cost += dc;
    let earning = !L.wait;
    if (L.cap0 != null) {
      const before = l.cap; l.cap = Math.min(1, l.cap + L.capDay * dd);
      if (before < .8 && l.cap >= .8) feed(`<b>${f.name}</b> ${Math.round(l.cap * 100)}% of its points cap used`, "red");
      if (before < 1 && l.cap >= 1) feed(`<b>${f.name}</b> points cap reached: stop it to free ${usd(l.amount)}`, "red");
      if (l.cap >= 1) earning = false;
    }
    if (earning && (L.pts || L.daily)) {
      if (L.pts) l.pts += ptsWeek(f, l.amount) / 7 * dd;
      const e = est(f, l.amount); l.lo += e.lo / 180 * dd; l.hi += e.hi / 180 * dd;
    }
    if (L.daily) l.claim += L.daily * l.amount * dd;
    if (L.weekly) l.week += weekly(f, l.amount) / 7 * dd;
    if (L.txs || L.tasks) l.n += (L.txs || L.tasks) * dd;
  }
  for (let d = Math.floor(d0) + 1; d <= Math.floor(F.day); d++) {
    let gained = 0, k = 0;
    const log = (txt, c) => feed(txt, c, d - .46 + rnd() * .45); // late in the day just ended
    for (const [id, l] of Object.entries(F.farms)) {
      const f = BY[id], L = f.live;
      if (L.pts && !l.done && (L.cap0 == null || l.cap < 1)) { gained += ptsWeek(f, l.amount) / 7; k++; }
      if (L.weekly && (d - Math.ceil(l.start)) % 7 === 0) { l.claim += l.week; log(`<b>${f.name}</b> paid <em>${l.week.toFixed(1)} ${L.tk}</em>, ready to claim`, "green"); l.week = 0; }
      if (L.epoch && (d - Math.ceil(l.start)) % L.epoch === 0) log(`<b>${f.name}</b> epoch closed: ${Math.round(l.n)} tasks counted`, "blue");
      if (l.tge != null && !l.done && !l.claim && d >= l.tge) {
        const seed = (id.length * 97 + d * 13) % 100 / 100, v = l.lo + (l.hi - l.lo) * (.25 + .5 * seed);
        l.claim = v / L.px; l.lo = l.hi = 0;
        log(`<b>${L.tk}</b> launched: <em>${fmt(l.claim)} ${L.tk}</em> (${money(v)}) ready to claim`, "green");
      }
      if (f.how === "Trade" && L.pts && d % 3 === 0 && rnd() < .5) log(`<b>${f.name}</b> hedge rebalanced`, "cyan");
      if (L.daily && d % 2 === 0) log(`<b>${f.name}</b> quotes refreshed on ${4 + d % 5} markets`, "cyan");
    }
    if (k) log(`Points synced <em>+${fmt(gained)}</em> on ${k} farm${k > 1 ? "s" : ""}`, "green");
    F.hist.push({d, ...totals()});
  }
}
function totals() {
  const F = S.farming; let lo = 0, hi = 0;
  for (const [id, l] of Object.entries(F.farms)) { const p = pendUsd(BY[id], l); lo += l.lo + p; hi += l.hi + p; }
  return {lo: lo + F.claimed, hi: hi + F.claimed};
}
// where the running plan lands at six months: what is earned plus the plan's estimate for the days left,
// so on day 0 it is exactly the number the Farms tab showed at Start
function projection() {
  const F = S.farming, T = totals(); let lo = T.lo, hi = T.hi;
  for (const [id, l] of Object.entries(F.farms)) {
    const f = BY[id], e = estPlan(f, l.amount), left = Math.max(0, 180 - (F.day - l.start)) / 180;
    if (e && !l.done && !(f.live.cap0 != null && l.cap >= 1)) { lo += e.lo * left; hi += e.hi * left; }
  }
  return {lo, hi};
}

/* ---------- Live farms tab ---------- */
function ago(d) {
  const m = Math.round((S.farming.day - d) * 1440);
  return m < 2 ? "just now" : m < 60 ? `${m}m ago` : m < 1440 ? `${Math.round(m / 60)}h ago` : `${Math.round(m / 1440)}d ago`;
}
function liveStatus(f, l) {
  const L = f.live, F = S.farming;
  if (l.done) return ["m", "CLAIMED"];
  if (claimable(f, l)) return ["s", "CLAIMABLE"];
  if (L.cap0 != null && l.cap >= 1) return ["m", "CAP REACHED"];
  if (L.cap0 != null && l.cap >= .8) return ["c", `CAP ${Math.round(l.cap * 100)}% USED`];
  if (L.tge && l.tge - F.day <= 10) return ["c", `TGE IN ${Math.max(1, Math.ceil(l.tge - F.day))} D`];
  if (L.epoch) return ["c", `EPOCH ENDS IN ${L.epoch - (Math.floor(F.day - l.start) % L.epoch)} D`];
  if (L.txs && !f.free) return ["m", "NO POINTS YET"];
  return ["lv", "FARMING"];
}
// a live farm's ring: how far into its six months it is, what it has earned in the middle

function liveChart(F, P) {
  const W = 760, Hh = 168, L = 2, R = 2, T = 26, B = 22;
  const hist = F.hist.concat([{d: F.day, ...totals()}]), now = hist[hist.length - 1];
  const top = Math.max(50, P.hi) * 1.08;
  const x = d => L + Math.min(180, d) / 180 * (W - L - R), y = v => Hh - B - v / top * (Hh - T - B);
  const mid = p => (p.lo + p.hi) / 2;
  const area = `M${x(0)} ${y(0)} ` + hist.map(p => `L${x(p.d).toFixed(1)} ${y(mid(p)).toFixed(1)}`).join(" ") + ` L${x(now.d).toFixed(1)} ${y(0)} Z`;
  const line = hist.map((p, i) => `${i ? "L" : "M"}${x(p.d).toFixed(1)} ${y(mid(p)).toFixed(1)}`).join(" ");
  const pm = (P.lo + P.hi) / 2;
  const band = `M${x(now.d)} ${y(now.hi)} L${x(180)} ${y(P.hi)} L${x(180)} ${y(P.lo)} L${x(now.d)} ${y(now.lo)} Z`;
  const nx = x(now.d), right = nx > W - 200;
  return `<svg viewBox="0 0 ${W} ${Hh}">
    <line x1="${L}" x2="${W - R}" y1="${y(0)}" y2="${y(0)}" stroke="#1e3050"/>
    <path d="${band}" fill="url(#projfill)"/>
    <path d="M${nx} ${y(mid(now))} L${x(180)} ${y(pm)}" stroke="#00cfff" stroke-width="2" stroke-dasharray="5 6" fill="none" stroke-opacity=".8"/>
    <path d="${area}" fill="url(#earnfill)"/>
    <path d="${line}" stroke="#00ff88" stroke-width="3" fill="none" filter="url(#soft)"/>
    ${F.claims.map(d => `<circle cx="${x(d)}" cy="${y(mid(hist.reduce((b, p) => Math.abs(p.d - d) < Math.abs(b.d - d) ? p : b, hist[0])))}" r="3.5" fill="#e6edf7"/>`).join("")}
    <circle cx="${nx}" cy="${y(mid(now))}" r="12" fill="#00ff88" fill-opacity=".18"/><circle cx="${nx}" cy="${y(mid(now))}" r="5.5" fill="#00ff88" filter="url(#soft)"/>
    <circle cx="${x(180)}" cy="${y(pm)}" r="5" fill="#06090f" stroke="#00cfff" stroke-width="2"/>
    <text x="${x(180) - 4}" y="${Math.max(12, y(P.hi) - 8)}" text-anchor="end" fill="#00cfff" font-size="12" font-weight="700">6 months ≈ ${rng(P.lo, P.hi)}</text>
    <text x="${L}" y="${Hh - 5}" fill="#7f93ad" font-size="11">${SHOT ? "28 Sep" : "start"}</text>
    ${nx > 90 ? `<text x="${nx + (right ? -8 : 8)}" y="${Hh - 5}" text-anchor="${right ? "end" : "start"}" fill="#00ff88" font-size="11" font-weight="700">now</text>` : ""}
    <text x="${W - R}" y="${Hh - 5}" text-anchor="end" fill="#7f93ad" font-size="11">${SHOT ? "27 Mar" : "6 months"}</text>
  </svg>`;
}

/* ---------- logo sheet ---------- */
function sheet() {
  const sz = n => logoSvg().replace("<svg", `<svg style="width:${n}px;height:${n}px"`);
  return `<div class="sheet"><div class="bigl">${logoSvg()}</div>
    <div><div class="wm">${logoSvg()}<div><span>AIRDROP</span><b>FARMER</b></div></div>
      <div class="sizes">${[64, 40, 24, 16].map(n => `<div>${sz(n)}${n}</div>`).join("")}</div></div></div>`;
}


function ribbon() {
  if (SHOT) return;
  $("#ribbon").innerHTML = `<div class="ribbon"><b>TEST DATA</b><span>nothing leaves this page</span>
    <span>1 day =</span>${[[4, "4 s"], [1, "1 s"], [0, "pause"]].map(([v, t]) => `<button data-speed="${v}" class="${S.speed === v ? "on" : ""}">${t}</button>`).join("")}
    <button data-act="reset">Reset</button></div>`;
}

function go(tab) {
  TAB = tab;
  try { const u = new URL(location.href); u.searchParams.set("tab", tab); history.replaceState(null, "", u); } catch (e) {} // a framed copy may refuse it
  render(); scrollTo(0, 0);
}
function openStopAll() {
  $("#modal").innerHTML = `<div class="ov" data-act="close"><div class="glass modal" style="width:440px"><div class="cap">STOP ALL</div>
    <h3>Stop every farm?</h3><div class="lead">Anything claimable is claimed first, positions are closed and about ${usd(Object.values(S.farming.farms).reduce((s, l) => s + Math.max(0, l.amount - l.cost), 0))} goes back to your balance.</div>
    <div class="btns"><button class="ghost" data-act="close">Cancel</button><button class="go" style="background:var(--red);box-shadow:none;color:var(--text)" data-act="stopall-ok">STOP ALL</button></div></div></div>`;
}

