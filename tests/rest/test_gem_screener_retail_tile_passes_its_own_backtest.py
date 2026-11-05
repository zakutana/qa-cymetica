"""The Retail tile of the Altseason index against the back-test the panel publishes for it.

The panel's API gives `components.retail.value` (the tile, "Retail turnover") and beside it `components.retail.backtest`, a
pre-registered check of that very tile against the 2017/18, 2021 and 2024/25 tops and the 2018/19, 2022 and 2023 lows, with a
verdict. The index itself is built from `euphoria_retail`, "the older measure". This check passes when the tile passes its own
back-test, or when the tile shows the number the index uses. It does not say which fix is right, and does not judge the panel's design.

SAFE: one anonymous GET.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from tests.rest.test_gem_screener_says_only_what_is_true import _json, _verdict


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_the_retail_tile_passes_its_own_backtest_or_is_the_number_the_index_uses(rest_anon):
    d = _json(rest_anon, "/api/v1/gem-screener/altseason").get("altseason") or {}
    retail = (d.get("components") or {}).get("retail") or {}
    tile, used = retail.get("value"), retail.get("euphoria_retail")
    bt = retail.get("backtest") or {}
    if tile is None or used is None or not bt.get("verdict"):
        raise Inconclusive("the altseason answer has no retail value, no euphoria_retail or no back-test verdict to compare")
    failed = [c for c in bt.get("checks") or [] if c.get("gating") is not False and c.get("pass") is False]
    breaches = []
    if bt["verdict"] == "fail" and abs(tile - used) > 1:
        lows = {k: (v.get("v4") or {}).get("value") for k, v in (bt.get("lows") or {}).items()}
        tops = {k: (v.get("v4") or {}).get("value") for k, v in (bt.get("tops") or {}).items()}
        breaches.append({
            "what": (f"the tile 'Retail turnover' reads {tile:.0f} ('{retail.get('verdict')}') and its own back-test ({bt.get('rules')}, "
                     f"registered {bt.get('registered')}) says {bt['verdict']}: failed {', '.join(c['id'] for c in failed)}; "
                     f"highest week in the top windows {tops}, lowest in the low windows {lows}; the index uses {used:.0f}")})
    _verdict(breaches, 1, f"the retail tile ({tile:.0f}) passes its own back-test or is the number the index uses ({used:.0f})",
             {"altseason": "/api/v1/gem-screener/altseason"})
