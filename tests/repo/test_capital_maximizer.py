"""The Capital Maximizer demo (outbox/capital-maximizer): the cards, the three strategies and the plan are one model.

The operator, 2026-10-28: pick a risk with what it can pour out in a month, an amount of USDC, the finder brings the
three best strategies side by side as skill trees, leverage is tuned inside the tree and the profit follows, pick one
and start; a tab lists every supported platform. Verified DeFi only, no KYC. Later the same day: no good/bad month,
no move switch -- one figure, the potential max profit (the month ETH and BTC rise 20 %, today's rates).

What each test protects (memory: mock figures come from one model; a correct number can be untradeable):
* the four tiers are a ladder on max profit, and each keeps the promise that decides what goes in it;
* the finder's three are the three best of different kinds, the first is the card's figure;
* leverage tuned in the tree stays inside what the tier and the market allow, and the profit is the same computation
  at the new leverage, never a figure scaled by hand;
* the loop arithmetic is right on numbers worked by hand;
* the Platforms tab lists exactly the protocols the routes can use, each audited per DefiLlama;
* the page uses only the site's colours.
"""
from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa

HERE = Path(__file__).resolve().parents[2] / "outbox" / "capital-maximizer"
NODE = shutil.which("node")
TIERS = ("conservative", "medium", "high", "og")

HARNESS = r"""
const fs = require('fs'), vm = require('vm'), path = require('path');
globalThis.window = globalThis;
for (const f of ['data.js', 'cm-core.js']) vm.runInThisContext(fs.readFileSync(path.join(process.argv[1], f), 'utf8'), {filename: f});
process.stdout.write(JSON.stringify(eval(process.argv[2])));
"""


def js(expr: str):
    if NODE is None:
        pytest.skip("node is not on PATH")
    out = subprocess.run([NODE, "-e", HARNESS, str(HERE), expr], capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def tops():
    return js("Object.fromEntries(%s.map(t => [t, {top: CM.top3(t), find: CM.find(t), card: CM.card(t), "
              "ranges: CM.top3(t).map(r => CM.range(r, t))}]))" % json.dumps(TIERS))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_tiers_are_a_ladder_on_max_profit():
    t = tops()
    ups = [t[k]["card"]["up"] for k in TIERS]
    assert ups == sorted(ups) and len(set(ups)) == 4, ups
    assert js("CM.MOVE") == 0.2


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_strategy_offered_keeps_its_tiers_promise():
    """The page no longer shows the bad month, but it still decides what a tier may offer."""
    t = tops()
    for r in t["conservative"]["top"]:
        assert r["bad"] >= 1 and r["L"] == 1 and r["stables"] and r["pLiq"] is None
        assert len({leg["project"] for leg in r["legs"] if leg["role"] == "supply"}) == 3
    for r in t["medium"]["top"]:
        assert r["bad"] >= 0.85 and not r["liqInBad"]
    for r in t["high"]["top"]:
        assert r["bad"] >= 0.5 and not r["liqInBad"] and (r["pLiq"] is None or r["pLiq"] <= 0.75)
    for r in t["og"]["top"]:
        assert r["pLiq"] is None or r["pLiq"] <= 0.95
    assert all(r["up"] > 1 for k in TIERS for r in t[k]["top"])


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_finder_brings_the_three_best_of_different_kinds():
    data = js("({allow: Object.keys(CM_DATA.protocols), pools: CM_DATA.pools.map(p => p.id)})")
    for k, v in tops().items():
        top, fit = v["top"], {r["id"] for r in v["find"]["fit"]}
        assert len(top) == 3, k
        assert len({r["family"] for r in top}) == 3, [r["family"] for r in top]
        assert [r["up"] for r in top] == sorted((r["up"] for r in top), reverse=True)
        assert top[0]["id"] == v["find"]["best"]["id"] and v["card"]["route"]["id"] == top[0]["id"]
        assert all(r["id"] in fit for r in top)
        for r in top:
            for leg in r["legs"]:
                assert leg["project"] in data["allow"] and leg["pool"] in data["pools"], (k, leg)
            assert all(st["project"] in data["allow"] for st in r["steps"] if st.get("project"))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_leverage_tuned_in_the_tree_stays_inside_the_tier_and_the_market():
    """Every tenth between the ends of the range is a route the market would open, never closer than a 5 % move to
    liquidation, never above the tier's cap; at the strategy's own leverage the tuned route is the same route."""
    out = js("""(() => { const rows = [];
      for (const t of %s) for (const r of CM.top3(t)) { const g = CM.range(r, t); if (!g) continue;
        const ls = []; for (let L = g.min; L <= g.max + 1e-9; L += g.step) ls.push(+L.toFixed(1));
        rows.push({t, max: CM.TIERS.find(x => x.id === t).maxL, g, L: r.L, up: r.up, same: CM.tune(r, r.L).up,
          tuned: ls.map(L => { const x = CM.tune(r, L); return {L, up: x.up, pLiq: x.pLiq, ltv: x.ltv}; })}); }
      return rows; })()""" % json.dumps(TIERS))
    assert out, "no strategy with a leverage to tune"
    for row in out:
        g = row["g"]
        assert g["min"] <= row["L"] <= g["max"] <= row["max"] and g["step"] == 0.1
        assert row["same"] == row["up"]
        for x in row["tuned"]:
            assert x["pLiq"] <= 0.95 and (x["L"] - 1) / x["L"] < x["ltv"], (row["t"], x)
        assert row["tuned"][-1]["up"] >= row["tuned"][0]["up"]       # more leverage, more max profit


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_dollars_are_the_amount_times_the_profit():
    r = js("[1000, 5000, 123456].map(a => CM.TIERS.map(t => { const s = CM.top3(t.id)[1]; "
           "return {a, up: s.up, usd: CM.profit(s, a), tuned: CM.tune(s, 1.7) && CM.profit(CM.tune(s, 1.7), a), "
           "tup: CM.tune(s, 1.7) && CM.tune(s, 1.7).up}; }))")
    for row in r:
        for x in row:
            assert x["usd"] == pytest.approx(x["a"] * (x["up"] - 1))
            if x["tuned"] is not None:
                assert x["tuned"] == pytest.approx(x["a"] * (x["tup"] - 1))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_loop_arithmetic_on_numbers_worked_by_hand():
    """A month is (1+APY)^(1/12). Two-times leverage, no rates, the asset up 20 %: 2 x 1.2 - 1 = 1.40. Liquidation
    at debt/collateral = LTV: L=2 at 0.86 when the price is 1/(2 x 0.86) = 0.5814. L=5 at 0.86, liquidated, bonus
    4.38 %, the price down 20 %: 5 - 4 x 1.0438 / 0.9302 tokens left, worth 0.8 each."""
    assert js("CM.month(12.682503013196977)") == pytest.approx(1.01, abs=1e-12)
    a = js("CM.loop({L: 2, y: 0, b: 0, lt: 0.86, bonus: 0, P: 1.2})")
    assert a["value"] == pytest.approx(1.4) and not a["liquidated"] and a["pLiq"] == pytest.approx(1 / 1.72)
    z = js("CM.loop({L: 5, y: 0, b: 0, lt: 0.86, bonus: 0.0438, P: 0.8})")
    assert z["liquidated"] and z["value"] == pytest.approx((5 - 4 * 1.0438 / (4 / 4.3)) * 0.8)
    assert js("CM.lp({kind: 'uniswap', fee: 0, P: 1.21})") == pytest.approx(1.1)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_platforms_tab_is_the_allowlist_from_defillama():
    text = (HERE / "data.js").read_text(encoding="utf-8")
    assert len(text.encode()) < 80_000
    d = js("CM_DATA")
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\dZ", d["fetched_at"]) and "api.llama.fi/protocols" in d["source"]
    assert all(re.fullmatch(r"[0-9a-f-]{36}", p["id"]) for p in d["pools"])
    used = {p["project"] for p in d["pools"]} | {"uniswap-v3", "curve-dex"}          # the swaps
    assert used == set(d["protocols"]), used ^ set(d["protocols"])
    for k, p in d["protocols"].items():
        assert p["audited"] and p["tvl"] > 0 and p["category"] and p["site"] and "/" not in p["site"], k
    assert sum(p["pools_read"] for p in d["protocols"].values()) == d["scanned"]["pools"]


ALLOWED = {"#00cfff", "#00ff88", "#ff4444", "#3b82f6", "#e6edf7", "#a9b8cc", "#7f93ad", "#1e3050", "#06090f",
           "#0d1520", "#0a0e17"}
ALLOWED_RGB = {"0,207,255", "0,255,136", "255,68,68", "59,130,246", "6,9,15", "13,21,32", "30,48,80", "10,14,23",
               "127,147,173", "230,237,247", "169,184,204"}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_only_the_site_colours_and_the_new_name():
    """Cyan, green, red, blue and the navy and slate tones (the vendor's palette rule); no purple, gold or orange.
    And the product is Capital Maximizer everywhere a person reads it."""
    src = "".join((HERE / n).read_text(encoding="utf-8") for n in ("mock.html", "cm-core.js", "cm-ui.js"))
    hexes = {h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}\b", src)}
    rgbs = {re.sub(r"\s", "", m) for m in re.findall(r"rgba?\(([\d\s]+,[\d\s]+,[\d\s]+),", src)}
    assert not (hexes - ALLOWED) and not (rgbs - ALLOWED_RGB), (sorted(hexes - ALLOWED), sorted(rgbs - ALLOWED_RGB))
    assert not re.findall(r"#[0-9a-fA-F]{3}\b", src)
    assert "<title>Capital Maximizer</title>" in src and not re.search(r"yield booster", src, re.I)
