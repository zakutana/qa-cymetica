"""The Yield Booster demo (outbox/yield-booster): the cards, the finder and the pipe's end are one model.

The operator, 2026-10-28: pick a risk (Conservative, Medium, High Risk, OG Gambler) with what each can pour out in a
month, type an amount of USDC, a strategy finder looks for the best route right now, the route is drawn as pipes with
water, the month's result at the end, Start. Verified DeFi only, no KYC.

What each test protects (memory: mock figures come from one model; a correct number can be untradeable):
* the four tiers are a ladder: each pays more in a good month and loses more in a bad one than the tier below it;
* each tier keeps the promise written on its card: Conservative never loses, Medium never more than 15 %, High Risk
  never more than half and is never liquidated in the bad month, OG Gambler needs at least a 5 % move to liquidate;
* the finder picks only from the allowlist, only a route that fits the tier, and the best of those -- so the number
  on a card is the number at the end of the pipe, for whatever amount is typed;
* the loop arithmetic is right on numbers worked by hand, so "x1.40" is a computation and not a typed figure;
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

HERE = Path(__file__).resolve().parents[2] / "outbox" / "yield-booster"
NODE = shutil.which("node")
TIERS = ("conservative", "medium", "high", "og")
MOVES = (0.1, 0.2, 0.3)

HARNESS = r"""
const fs = require('fs'), vm = require('vm'), path = require('path');
globalThis.window = globalThis;
for (const f of ['data.js', 'yb-core.js']) vm.runInThisContext(fs.readFileSync(path.join(process.argv[1], f), 'utf8'), {filename: f});
process.stdout.write(JSON.stringify(eval(process.argv[2])));
"""


def js(expr: str):
    if NODE is None:
        pytest.skip("node is not on PATH")
    out = subprocess.run([NODE, "-e", HARNESS, str(HERE), expr], capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    return json.loads(out.stdout)


def finds():
    """Every tier at every move the page offers, as the page computes it."""
    return js("Object.fromEntries(%s.map(s => [s, Object.fromEntries(%s.map(t => [t, YB.find(t, s)]))]))"
              % (json.dumps(MOVES), json.dumps(TIERS)))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_tiers_are_a_ladder():
    """A riskier tier pays more in the good month and loses more in the bad one, at every move the page offers."""
    for s, by_tier in finds().items():
        ups = [by_tier[t]["best"]["up"] for t in TIERS]
        bads = [by_tier[t]["best"]["bad"] for t in TIERS]
        assert ups == sorted(ups) and len(set(ups)) == 4, (s, ups)
        assert bads == sorted(bads, reverse=True), (s, bads)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_each_tier_keeps_the_promise_on_its_card():
    for s, by_tier in finds().items():
        s = float(s)
        c, m, h, o = (by_tier[t]["best"] for t in TIERS)
        assert c["bad"] >= 1 and c["L"] == 1 and c["stables"] and c["pLiq"] is None
        assert len({leg["project"] for leg in c["legs"] if leg["role"] == "supply"}) == 3     # never one basket
        assert m["bad"] >= 0.85 and not m["liqInBad"]
        assert h["bad"] >= 0.5 and not h["liqInBad"]
        assert h["pLiq"] is None or h["pLiq"] <= 1 - s - 0.05                                # a margin past the bad month
        assert o["pLiq"] is None or o["pLiq"] <= 0.95                                        # not a normal day's move
        for r in (c, m, h, o):
            assert r["up"] > 1, r["id"]                                                      # never a route that costs


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_finder_picks_the_best_route_that_fits_and_only_from_the_allowlist():
    data = js("({allow: Object.keys(YB_DATA.protocols), pools: YB_DATA.pools.map(p => p.id)})")
    for s, by_tier in finds().items():
        for t, f in by_tier.items():
            best = f["best"]
            assert best["id"] in {r["id"] for r in f["fit"]}
            assert best["up"] == max(r["up"] for r in f["fit"])
            assert f["built"] >= len(f["fit"]) + len(f["rejected"]) and all(r["reason"] for r in f["rejected"])
            for leg in best["legs"]:
                assert leg["project"] in data["allow"] and leg["pool"] in data["pools"], (t, leg)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_card_is_the_pipe_end_for_any_amount():
    """The card, the amount screen and the end of the pipe all read YB.result; the dollars are the amount times it."""
    r = js("[1000, 5000, 123456].map(a => ['high', 'og', 'conservative'].map(t => "
           "({a, card: YB.card(t, 0.2), res: YB.result(t, 0.2, a), best: YB.find(t, 0.2).best})))")
    for row in r:
        for x in row:
            assert x["card"]["up"] == x["best"]["up"] and x["card"]["bad"] == x["best"]["bad"]
            assert x["res"]["upUsd"] == pytest.approx(x["a"] * (x["best"]["up"] - 1))
            assert x["res"]["badUsd"] == pytest.approx(x["a"] * (x["best"]["bad"] - 1))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_loop_arithmetic_on_numbers_worked_by_hand():
    """A month is (1+APY)^(1/12). Two-times leverage, no rates, the asset up 20 %: 2 x 1.2 - 1 = 1.40. Liquidation
    at debt/collateral = LTV: L=2 at 0.86 when the price is 1/(2 x 0.86) = 0.5814. L=5 at 0.86, liquidated, bonus
    4.38 %, the price down 20 %: 5 - 4 x 1.0438 / 0.9302 tokens left, worth 0.8 each = 0.4084."""
    m = js("YB.month(12.682503013196977)")
    assert m == pytest.approx(1.01, abs=1e-12)
    a = js("YB.loop({L: 2, y: 0, b: 0, lt: 0.86, bonus: 0, P: 1.2})")
    assert a["value"] == pytest.approx(1.4) and not a["liquidated"] and a["pLiq"] == pytest.approx(1 / 1.72)
    z = js("YB.loop({L: 5, y: 0, b: 0, lt: 0.86, bonus: 0.0438, P: 0.8})")
    p = 4 / (5 * 0.86)
    assert z["liquidated"] and z["value"] == pytest.approx((5 - 4 * 1.0438 / p) * 0.8)
    lp = js("YB.lp({kind: 'uniswap', fee: 0, P: 1.21})")
    assert lp == pytest.approx(1.1)                                   # a full-range pool holds sqrt(P)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_snapshot_is_dated_small_and_traceable():
    """Every rate is a DefiLlama pool by id with the time it was read; never the 11 MB dump in git."""
    text = (HERE / "data.js").read_text(encoding="utf-8")
    assert len(text.encode()) < 80_000
    d = js("YB_DATA")
    assert re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\dZ", d["fetched_at"])
    assert d["source"].startswith("https://yields.llama.fi")
    assert all(re.fullmatch(r"[0-9a-f-]{36}", p["id"]) for p in d["pools"])
    assert d["scanned"]["pools"] >= len(d["pools"])


ALLOWED = {"#00cfff", "#00ff88", "#ff4444", "#3b82f6", "#e6edf7", "#a9b8cc", "#7f93ad", "#1e3050", "#06090f",
           "#0d1520", "#0a0e17"}
ALLOWED_RGB = {"0,207,255", "0,255,136", "255,68,68", "59,130,246", "6,9,15", "13,21,32", "30,48,80", "10,14,23",
               "127,147,173", "230,237,247", "169,184,204"}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_only_the_site_colours():
    """Cyan, green, red, blue and the navy and slate tones (the vendor's palette rule); no purple, gold or orange."""
    src = "".join((HERE / n).read_text(encoding="utf-8") for n in ("mock.html", "yb-core.js", "yb-ui.js"))
    hexes = {h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}\b", src)}
    rgbs = {re.sub(r"\s", "", m) for m in re.findall(r"rgba?\(([\d\s]+,[\d\s]+,[\d\s]+),", src)}
    assert not (hexes - ALLOWED) and not (rgbs - ALLOWED_RGB), (sorted(hexes - ALLOWED), sorted(rgbs - ALLOWED_RGB))
    assert not re.findall(r"#[0-9a-fA-F]{3}\b", src)                 # a short hex would slip past the scan
