/* Airdrop Farmer, the views: the farm seen from above (one light pillar per farm), the amount and the ranked list,
   and the same farm growing on Live farms. The numbers all come from farm-core.js. */

/* ---------- header ---------- */
function header() {
  const n = S.farming ? Object.keys(S.farming.farms).length : 0;
  const status = n ? `<span class="dot"></span><b>FARMING</b> · ${n} farm${n > 1 ? "s" : ""} · ${usd(liveSum())} in` : `<span class="dot idle"></span><b>NOT FARMING</b>`;
  return `<header class="app">
    <a class="brand">${logoSvg()}<div class="w"><span>AIRDROP</span><b>FARMER</b></div></a>
    <nav><a href="?tab=farms" data-tab="farms" class="${TAB === "farms" ? "on" : ""}">Farms</a><a href="?tab=live" data-tab="live" class="${TAB === "live" ? "on" : ""}">Live farms${n ? ` <i>${n}</i>` : ""}</a></nav>
    <div class="status" id="hstatus">${status}</div>
  </header>`;
}

/* ---------- the farm from above: plots on a lattice, a pillar of light on each farm, its logo on top ---------- */
const FD = {tw: 116, th: 58, pw: 26, ph: 13, hmax: 150};
const earnedOf = (f, l) => (l.lo + l.hi) / 2 + l.got + pendUsd(f, l);
function plantTop(f, x, y, ready) {
  const r = 17;
  return `${ready ? `<circle class="halo" cx="${x}" cy="${y}" r="${r + 10}" fill="#00ff88" fill-opacity=".4" filter="url(#soft)"/>` : ""}
    <circle cx="${x}" cy="${y}" r="${r + 2.5}" fill="#06090f" stroke="${ready ? "#00ff88" : "#00cfff"}" stroke-opacity="${ready ? 1 : .55}" stroke-width="2"/>
    ${f.icon ? `<image href="${ICON(f.icon)}" x="${x - r}" y="${y - r}" width="${2 * r}" height="${2 * r}" clip-path="url(#disc)"/>`
      : `<text x="${x}" y="${y + 4}" text-anchor="middle" fill="#00ff88" font-size="11" font-weight="800" font-family="JetBrains Mono,monospace">${f.ini}</text>`}
    ${ready ? `<g transform="translate(${x} ${y - r - 16})"><rect x="-32" y="-10" width="64" height="19" rx="9.5" fill="#00ff88"/><text y="3.5" text-anchor="middle" fill="#06090f" font-size="9.5" font-weight="800" font-family="Inter,sans-serif" letter-spacing="1">HARVEST</text></g>` : ""}`;
}
function fieldSvg(live) {
  const F = S.farming, {tw, th, pw, ph, hmax} = FD;
  const items = live && F ? Object.keys(F.farms).map(id => ({f: BY[id], l: F.farms[id]})) : FARMS.filter(f => S.on[f.id]).map(f => ({f}));
  const val = it => live ? earnedOf(it.f, it.l) : (it.f.free ? 0 : amtOf(it.f.id));
  items.sort((a, b) => val(b) - val(a) || rank(a.f) - rank(b.f)); // the tallest stand at the back
  const cols = 4, n = Math.min(items.length, 16), rows = Math.max(3, Math.ceil(n / cols));
  const plots = [];
  for (let r = 0; r < rows; r++) for (let c = 0; c < cols; c++) plots.push([c, r]);
  plots.sort((p, q) => (p[0] + p[1]) - (q[0] + q[1]) || p[0] - q[0]);
  const ox = rows * tw / 2 + 24, oy = hmax + 70;
  const W = (cols + rows) * tw / 2 + 48, Hh = oy + (cols + rows) * th / 2 + 18;
  const at = (c, r) => [ox + (c - r) * tw / 2, oy + (c + r) * th / 2];
  const vmax = Math.max(1e-9, ...items.slice(0, n).map(val));
  let s = `<ellipse cx="${W / 2}" cy="${oy + (cols + rows) * th / 4}" rx="${W * .5}" ry="${(cols + rows) * th / 2.6}" fill="url(#ground)"/>`;
  plots.forEach(([c, r]) => {
    const [x, y] = at(c, r);
    s += `<polygon points="${x},${y - th / 2} ${x + tw / 2},${y} ${x},${y + th / 2} ${x - tw / 2},${y}" fill="#0d1520" fill-opacity=".92" stroke="#00ff88" stroke-opacity=".18"/>
      <polygon points="${x},${y - th / 4} ${x + tw / 4},${y} ${x},${y + th / 4} ${x - tw / 4},${y}" fill="none" stroke="#00ff88" stroke-opacity=".07"/>`;
  });
  plots.slice(0, n).forEach(([c, r], k) => {
    const it = items[k], f = it.f, [x, y] = at(c, r), v = val(it);
    const h = !live && f.free ? 16 : (live ? 6 : 16) + Math.sqrt(v / vmax) * (hmax - (live ? 6 : 16));
    const ready = live && claimable(f, it.l);
    const side = f.free ? "fl" : "pl";
    const top = f.free ? "#00cfff" : "#00ff88";
    s += `<g class="pillar${ready ? " ready" : ""}"><title>${f.name}: ${live ? money(v) + " earned" : f.free ? "free" : usd(v)}</title>
      <ellipse cx="${x}" cy="${y + 2}" rx="${pw * 1.6}" ry="${ph * 1.6}" fill="${top}" fill-opacity=".12" filter="url(#soft)"/>
      <polygon points="${x - pw},${y} ${x},${y + ph} ${x},${y + ph - h} ${x - pw},${y - h}" fill="url(#${side})"/>
      <polygon points="${x},${y + ph} ${x + pw},${y} ${x + pw},${y - h} ${x},${y + ph - h}" fill="url(#pr)"/>
      <polygon points="${x},${y - ph - h} ${x + pw},${y - h} ${x},${y + ph - h} ${x - pw},${y - h}" fill="${top}" filter="url(#soft)"/>
      <line x1="${x}" y1="${y - h - ph}" x2="${x}" y2="${y - h - 12}" stroke="${top}" stroke-opacity=".5" stroke-dasharray="2 3"/>
      ${plantTop(f, x, y - h - 32, ready)}</g>`;
  });
  if (items.length > n) s += `<text x="${W - 16}" y="${Hh - 6}" text-anchor="end" fill="#7f93ad" font-size="12" font-family="JetBrains Mono,monospace">+${items.length - n} more farms</text>`;
  return `<svg class="field" viewBox="0 0 ${W} ${Hh}">${s}</svg>`;
}

/* ---------- Farms tab ---------- */
const RANK = () => Object.fromEntries(FARMS.slice().sort((a, b) => rank(a) - rank(b)).map((f, i) => [f.id, i + 1]));
const toPos = v => Math.round(1000 * Math.sqrt(Math.min(1, Math.max(0, v) / Math.max(1, maxAmt()))));
const fromPos = p => { const v = maxAmt() * Math.pow(p / 1000, 2); return v < 1000 ? Math.round(v / 10) * 10 : v < 5000 ? Math.round(v / 50) * 50 : Math.round(v / 100) * 100; };
const along = v => `calc(11px + (100% - 22px) * ${toPos(v) / 1000})`;

function farmsView() {
  const N = SHOT ? 412 : FARMS.length;
  return `<div class="back">← Back</div><div class="wrap">${header()}
  <section class="hero">
    <div>
      <div class="pill"><span class="dot"></span>${N} FARMS · ONE DEPOSIT</div>
      <h1>Deploy USDC.<br>Farm every airdrop.<br><em>Cymetica does the rest.</em></h1>
      <div class="sub">Chatbots explain airdrops. <b>Cymetica farms them.</b></div>
      <div class="glass glow plan">
        <div class="top"><span class="cap">HOW MUCH USDC?</span><span id="bestslot"></span></div>
        <div class="bigin"><input id="budget" inputmode="decimal" autocomplete="off" value="${fmt(S.budget)}" aria-label="USDC to farm"><span class="token"><i>$</i>USDC</span><button class="max" data-act="max">MAX</button></div>
        <div class="bal">Balance <b id="bal">${fmt(S.balance)}</b> USDC · any farm takes any amount</div>
        <div class="you"><small>YOU FARM ≈</small><b id="kest"></b><span id="kline"></span></div>
        <button class="go" data-act="start" id="gobtn"></button>
        <div class="fine">Costs and fees are shown before anything starts · stop any farm any time</div>
      </div>
    </div>
    <div class="fieldwrap"><div id="field"></div><div class="fcap">Your farm from above: one pillar per farm, as tall as the USDC you plant.</div></div>
  </section>
  <div class="sechead">
    <div><h2>Every farm, best first</h2><p>Ranked by what a dollar farms there. Drag to plant more or less.</p></div>
    <input id="q" class="search" placeholder="Search farms" value="${S.q}" aria-label="Search farms">
  </div>
  <div class="glass list">
    <div class="rowh cols"><div>#</div><div>FARM</div><div>PLANT</div><div>USDC</div><div>EST. AIRDROP · 6 MO</div><div style="text-align:right">ON</div></div>
    <div id="list"></div>
  </div>
  <div class="more" id="more"></div>
  </div>`;
}
function visible() {
  return FARMS.filter(f => f.name.toLowerCase().includes(S.q.toLowerCase())).sort((a, b) => rank(a) - rank(b));
}
function estHTML(f) {
  if (f.free) return `<b>FREE</b><small>no USDC · no estimate</small>`;
  if (f.lo == null) return `<b class="no">no estimate</b><small>${f.why}</small>`;
  const a = S.on[f.id] ? amtOf(f.id) : 0, e = estPlan(f, a);
  if (!e) { const p = rec(f) || f.ref, ep = estPlan(f, p); return `<b class="dim">${rng(ep.lo, ep.hi)}</b><small>if you plant ${usd(p)}</small>`; }
  return `<b>${rng(e.lo, e.hi)}</b><small>est. airdrop in 6 months</small>`;
}
const useBestHTML = f => { const r = rec(f); return !f.free && r && !(S.on[f.id] && amtOf(f.id) === r) ? `<button class="usebest" data-use="${f.id}">best ${usd(r)}</button>` : ""; };
function rowHTML(f, rk) {
  const on = !!S.on[f.id], a = amtOf(f.id), r = rec(f);
  const plant = f.free ? `<span class="freepill">FREE · NO USDC NEEDED</span>`
    : `<div class="trk"><i class="bar"></i><i class="fil" style="width:${along(a)}"></i>${r ? `<i class="notch" style="left:${along(r)}"><em>BEST</em></i>` : ""}
        <input type="range" min="0" max="1000" step="1" value="${toPos(a)}" data-rng="${f.id}" aria-label="USDC into ${f.name}"></div>`;
  return `<div class="row cols ${on ? "on" : "off"}" data-row="${f.id}">
    <div class="rank ${rk <= 3 ? "top" : ""}">${rk}</div>
    <div class="who">${logo(f)}<div><b>${f.name}</b><span class="chip ${f.chip[1]}">${f.chip[0]}</span></div></div>
    <div class="plant">${plant}</div>
    <div>${f.free ? "" : `<div class="amt"><input data-amt="${f.id}" inputmode="decimal" value="${fmt(a)}" aria-label="${f.name} USDC"><span>USDC</span></div>`}<span id="ub-${f.id}">${useBestHTML(f)}</span></div>
    <div class="est" id="est-${f.id}">${estHTML(f)}</div>
    <div><button class="tg ${on ? "on" : ""}" data-tog="${f.id}" aria-label="Farm ${f.name}"></button></div>
  </div>`;
}
function renderList() {
  const L = visible(), R = RANK();
  $("#list").innerHTML = L.length ? L.map(f => rowHTML(f, R[f.id])).join("") : `<div class="more" style="margin:20px 0">No farm matches.</div>`;
  $("#more").innerHTML = SHOT ? `<span>Showing ${L.length} of 412 farms</span><span class="btn">Show 50 more</span>` : `<span>Showing ${L.length} of ${FARMS.length} farms · test data</span>`;
}
// one row's moving parts, without redrawing the slider being dragged or the field being typed in
function updateCard(id) {
  const f = BY[id], row = document.querySelector(`[data-row="${id}"]`);
  if (!row) return;
  const on = !!S.on[id], a = amtOf(id);
  row.classList.toggle("on", on); row.classList.toggle("off", !on);
  row.querySelector(".tg").classList.toggle("on", on);
  const fil = row.querySelector(".fil"); if (fil) fil.style.width = along(a);
  const rg = row.querySelector("[data-rng]"); if (rg && document.activeElement !== rg) rg.value = toPos(a);
  const fi = row.querySelector("[data-amt]"); if (fi && document.activeElement !== fi) fi.value = fmt(a);
  $("#est-" + id).innerHTML = estHTML(f);
  $("#ub-" + id).innerHTML = useBestHTML(f);
}
function updatePlan() {
  const t = planTotals();
  tweenRange($("#kest"), t.lo, t.hi);
  $("#kline").textContent = `in airdrops over 6 months · ${t.n} farms · ${usd(t.a)} planted`;
  $("#bestslot").innerHTML = S.custom ? `<button class="bestbtn" data-act="best">↺ BEST SPLIT</button>` : `<span class="bestok">BEST SPLIT ✓</span>`;
  $("#bal").textContent = fmt(S.balance);
  const bi = $("#budget"); if (bi && document.activeElement !== bi) bi.value = fmt(S.budget);
  $("#gobtn").innerHTML = BOLT + (S.farming ? "UPDATE FARMS" : "START FARMING");
  $("#field").innerHTML = fieldSvg(false);
}

/* ---------- the confirmation ---------- */
function openStart() {
  const L = planLines();
  if (!L.length) return toast("Switch on at least one farm");
  const t = planTotals(), need = t.a - liveSum();
  if (need > S.balance) return toast(`Not enough USDC: you need ${usd(need)}, the balance is ${usd(S.balance)}`);
  $("#modal").innerHTML = `<div class="ov" data-act="close"><div class="glass glow modal">
    <div class="cap">${S.farming ? "UPDATE YOUR FARMS" : "START FARMING"}</div>
    <h3>${t.n} farms · ${usd(t.a)}</h3>
    <div class="mnum">≈ ${rng(t.lo, t.hi)}</div><div class="mnuml">est. airdrops over 6 months</div>
    <details><summary>See the ${t.n} farms ▾</summary>
      ${L.map(l => `<div class="ln"><span>${l.f.name}</span><span>${l.f.free ? "free" : usd(l.a)}</span><span>${l.e ? rng(l.e.lo, l.e.hi) : `<small>no estimate</small>`}</span></div>`).join("")}
    </details>
    <div class="kv"><span>Est. cost (fees, funding, gas)</span><b>${usd(t.c)}</b></div>
    <div class="kv"><span>Cymetica fee</span><b style="color:var(--dim)">set by Cymetica</b></div>
    <div class="lead">Cymetica's agent farms from one wallet with your USDC: deposits, hedged trades, quotes, bridges, points, claims.</div>
    <div class="btns"><button class="ghost" data-act="close">Cancel</button><button class="go" data-act="confirm">${BOLT}${S.farming ? "UPDATE FARMS" : "START FARMING"}</button></div>
    ${SHOT ? "" : `<div class="fine">Test data: no USDC moves, nothing leaves this page.</div>`}
  </div></div>`;
}

/* ---------- Live farms tab ---------- */
function liveRowHTML(id, l) {
  const f = BY[id], L = f.live, st = liveStatus(f, l), F = S.farming;
  const earning = !l.done && !(L.cap0 != null && l.cap >= 1);
  const grown = Math.min(100, (F.day - l.start) / 180 * 100);
  const line = L.pts ? `<em>${fmt(l.pts)} pts</em>${earning ? ` · +${fmt(ptsWeek(f, l.amount) / 7)} today` : ""}`
    : L.daily ? `<em>${(l.claim + l.got).toFixed(2)} ${L.tk}</em> paid · +${(L.daily * l.amount).toFixed(2)} a day`
    : L.weekly ? `<em>${l.week.toFixed(1)} ${L.tk}</em> this week`
    : `<em>${Math.floor(l.n)} ${L.tasks ? "tasks" : "txs"}</em> · +${L.txs || L.tasks} a day`;
  const p = pendUsd(f, l), lo = l.lo + l.got + p, hi = l.hi + l.got + p, any = f.lo != null || l.got || p;
  const ready = claimable(f, l);
  return `<div class="lrow lcols ${ready ? "ready" : ""}">
    <div class="who">${logo(f)}<div><b>${f.name}</b><span class="chip ${st[0]}">${st[1]}</span></div></div>
    <div class="cell"><small>IN</small><b>${l.amount ? usd(l.amount) : "free"}</b></div>
    <div class="growth"><div class="gbar"><i style="width:${grown}%"></i></div><small>${line}</small></div>
    <div class="est">${any ? `<b>${rng(lo, hi)}</b><small>earned so far</small>` : `<b class="no">no estimate</b><small>${f.why}</small>`}</div>
    <div class="acts">${ready ? `<button class="harv" data-claim="${id}">Harvest ${tokAmt(f, l.claim)} ${L.tk}</button>` : ""}<button class="stop" data-stop="${id}">Stop</button></div>
  </div>`;
}
function liveView() {
  const F = S.farming;
  if (!F) return `<div class="back">← Back</div><div class="wrap">${header()}
    <div class="glass emptylive"><b>Nothing planted yet</b>Type an amount on the Farms tab and press Start farming.<br>
    <button class="go" data-tab="farms">${BOLT}GO TO FARMS</button></div></div>`;
  const T = totals(), P = projection(), ids = Object.keys(F.farms).sort((a, b) => rank(BY[a]) - rank(BY[b]));
  let perDay = 0, ready = 0;
  ids.forEach(id => {
    const f = BY[id], l = F.farms[id], L = f.live;
    if (claimable(f, l)) ready += l.claim * L.px;
    if (l.done || (L.cap0 != null && l.cap >= 1)) return;
    const e = est(f, l.amount); if (e && (L.pts || L.daily)) perDay += (e.lo + e.hi) / 2 / 180;
    if (L.daily) perDay += L.daily * l.amount;
    if (L.weekly) perDay += weekly(f, l.amount) / 7 * L.px;
  });
  const seen = new Set(), ev = F.feed.filter(e => { const k = e.txt.replace(/<[^>]+>/g, "").split(/[:+\d]/)[0]; return !seen.has(k) && seen.add(k); })
    .slice(0, 3).map(e => `<span class="ev"><i style="background:var(--${e.c})"></i><time>${ago(e.d)}</time><span>${e.txt}</span></span>`).join("");
  return `<div class="back">← Back</div><div class="wrap">${header()}
  <section class="lhero">
    <div class="glass glow earnp">
      <span class="cap">EARNED SO FAR</span>
      <div class="big">${rng(T.lo, T.hi)}</div>
      <div class="today"><em>+${money(perDay)} today</em><span>day ${Math.floor(F.day)} of your 6 months · ${ids.length} farms · ${usd(liveSum())} planted</span></div>
      <button class="go" data-act="claimall" ${ready > 0 ? "" : "disabled"}>${BOLT}${ready > 0 ? `HARVEST ${money(ready)}` : "NOTHING TO HARVEST YET"}</button>
      <div class="fine"><button data-act="stopall">Stop all farms</button></div>
    </div>
    <div class="fieldwrap">${fieldSvg(true)}<div class="fcap">Each pillar grows with what its farm has earned. A lit one is ready to harvest.</div></div>
  </section>
  <div class="glass chartp"><span class="cap">YOUR 6 MONTHS</span>${liveChart(F, P)}<div class="ticker"><span class="cap">CYMETICA 24/7</span>${ev}</div></div>
  <div class="sechead" style="margin-top:30px"><div><h2>Your farms</h2></div></div>
  <div class="glass list">${ids.map(id => liveRowHTML(id, F.farms[id])).join("")}</div>
  </div>`;
}

/* ---------- wiring ---------- */
function render() {
  if (TAB === "logo") { $("#root").innerHTML = sheet(); return; }
  if (TAB === "live") { $("#root").innerHTML = liveView(); ribbon(); return; }
  $("#root").innerHTML = farmsView();
  renderList(); updatePlan(); ribbon();
}
document.addEventListener("click", e => {
  const t = e.target.closest("[data-tab],[data-tog],[data-use],[data-act],[data-speed]");
  if (!t || SHOT) return;
  const d = t.dataset;
  if (d.tab) return e.preventDefault(); // switched on pointerdown, below
  if (d.tog) {
    const f = BY[d.tog];
    if (S.on[f.id]) { S.on[f.id] = false; S.custom = true; if (!f.free) { S.last[f.id] = amtOf(f.id) || S.last[f.id]; S.amt[f.id] = 0; } S.budget = planSum(); updateCard(f.id); updatePlan(); save(); }
    else if (f.free) { S.on[f.id] = true; S.custom = true; updateCard(f.id); updatePlan(); save(); }
    else setAmt(f.id, Math.min(rec(f) || S.last[f.id] || 300, maxAmt()));
    return;
  }
  if (d.use) return setAmt(d.use, rec(BY[d.use]));
  if (d.speed != null) { S.speed = +d.speed; ribbon(); save(); return; }
  switch (d.act) {
    case "max": setBudget(maxAmt(), true); break;
    case "best": REC = recommend(S.budget); applyBest(); renderList(); updatePlan(); save(); toast("Best split for " + usd(S.budget)); break;
    case "start": openStart(); break;
    case "close": if (e.target === t) $("#modal").innerHTML = ""; break;
    case "confirm": confirmStart(); break;
    case "stopall-ok": $("#modal").innerHTML = ""; Object.keys(S.farming.farms).forEach(id => stopFarm(id, true)); save(); toast("All farms stopped"); render(); break;
    case "reset": try { localStorage.removeItem(KEY); } catch (err) {} S = DEFAULT(); REC = recommend(S.budget); applyBest(); go("farms"); toast("Test reset"); break;
  }
});
// the live tab redraws twice a second, so the tabs and its buttons act on pointerdown
document.addEventListener("pointerdown", e => {
  if (SHOT || e.button) return;
  const t = e.target.closest("[data-tab],[data-claim],[data-stop],[data-act=claimall],[data-act=stopall]");
  if (!t) return;
  const d = t.dataset;
  if (d.tab) return go(d.tab);
  if (d.act === "stopall") return openStopAll();
  if (d.claim) { const v = claimFarm(d.claim); if (v) floatUp(e.clientX, e.clientY, "+" + money(v)); }
  else if (d.stop) stopFarm(d.stop);
  else if (d.act === "claimall") { if (!S.farming) return; const v = Object.keys(S.farming.farms).reduce((s, id) => s + claimFarm(id), 0); if (v) floatUp(e.clientX, e.clientY, "+" + money(v)); }
  save(); render();
});
document.addEventListener("input", e => {
  const t = e.target;
  if (t.dataset.rng) { setAmt(t.dataset.rng, fromPos(+t.value), true); return; }
  if (t.dataset.amt) { setAmt(t.dataset.amt, +t.value.replace(/[^\d.]/g, "")); return; }
  if (t.id === "budget") { setBudget(+t.value.replace(/[^\d.]/g, ""), false); return; }
  if (t.id === "q") { S.q = t.value; renderList(); save(); }
});
document.addEventListener("change", e => { if (e.target.dataset && e.target.dataset.rng) tellMoved(BY[e.target.dataset.rng]); });
document.addEventListener("focusout", e => {
  const t = e.target;
  if (t.dataset && t.dataset.amt) t.value = fmt(amtOf(t.dataset.amt));
  if (t.id === "budget") { if (S.budget > maxAmt()) setBudget(S.budget, true); t.value = fmt(S.budget); }
});
document.addEventListener("keydown", e => {
  if (e.key === "Escape") $("#modal").innerHTML = "";
  if (e.key === "Enter" && (e.target.id === "budget" || (e.target.dataset && e.target.dataset.amt))) e.target.blur();
});

let tick = 0;
setInterval(() => {
  if (SHOT || !S.farming || !S.speed) return;
  advance(.25 / S.speed);
  if (++tick % 2 === 0) {
    save();
    if (TAB === "live" && !$("#modal").innerHTML) $("#root").innerHTML = liveView();
    else if (TAB === "farms" && $("#hstatus")) $("#hstatus").innerHTML = `<span class="dot"></span><b>FARMING</b> · ${Object.keys(S.farming.farms).length} farms · ${usd(liveSum())} in`;
  }
}, 250);

// the pictures: the same plan before Start (Farms) and 23 days into it (Live farms), the weekly pays claimed on days 7 and 14
if (SHOT && TAB === "live") {
  startFarms();
  const runTo = d => { while (S.farming.day < d - 1e-9) advance(Math.min(.25, d - S.farming.day)); };
  runTo(7.4); claimFarm("lighter");
  runTo(14.4); claimFarm("lighter"); claimFarm("polymarket");
  runTo(23 + .6 / 24);
}
render();
if (SHOT && Q.has("modal")) openStart();
