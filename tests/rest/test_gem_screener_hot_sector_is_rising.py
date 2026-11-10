"""The Sectors tab's "Hot" against what the sector itself did.

The stage "Hot" ("Hot right now" above the table, the ▲ HOT pill in it) is given to a sector ahead of the median sector over
three months and over the last month. It is relative only: in a month when every sector falls, the ones that fall least read
Hot. This check fails while a sector carries the stage Hot although its own basket fell over the month AND lost to BTC over
the month (theme_4w < 0 and rs1m < 0 in the Sectors tab's own snapshot). It passes when no such sector is Hot, whatever rule
gets there. It does not judge the stage rule itself or the other stages.

SAFE: one anonymous GET of the Sectors tab.
"""

from __future__ import annotations

import httpx

from qa import gemaudit as g
from qa.marks import Inconclusive, SafetyTier, qa
from tests.rest.test_gem_screener_numbers_match_their_sources import get_patiently
from tests.rest.test_gem_screener_says_only_what_is_true import _verdict

SECTORS = "/gem-screener/app?view=sectors"   # the tab's own URL: each view is its own cache entry on their side


@qa(component="rest.gem_screener", tier=SafetyTier.SAFE, surface="rest")
def test_a_hot_sector_did_not_fall_and_lose_to_btc_over_the_month(rest_anon):
    try:
        response = get_patiently(rest_anon, SECTORS, headers={"Accept": "text/html"})
    except httpx.HTTPError as exc:
        raise Inconclusive(f"{SECTORS} could not be read: {type(exc).__name__}")
    if response.status_code != 200:
        raise Inconclusive(f"{SECTORS} answered HTTP {response.status_code}")
    try:
        snap = g.parse_snapshot(response.text)
    except Exception as exc:  # noqa: BLE001 - an unreadable page is unmeasured, never a pass or a fail
        raise Inconclusive(f"{SECTORS}: {type(exc).__name__}: {str(exc)[:120]}")
    themes = [t for t in snap.get("themes") or [] if t.get("stage")]
    if not themes:
        raise Inconclusive("the Sectors tab's snapshot has no sector with a stage")
    hot = [t for t in themes if t.get("stage") == "hot"]
    measured = [t for t in themes if isinstance(t.get("theme_4w"), (int, float)) and isinstance(t.get("rs1m"), (int, float))]
    fell = sum(1 for t in measured if t["theme_4w"] < 0)
    lost = sum(1 for t in measured if t["rs1m"] < 0)
    breaches = [{"what": (f"{t.get('name')} is Hot: its basket {100 * t['theme_4w']:+.0f}% over the month, {100 * t['rs1m']:+.0f}% against BTC, "
                          f"{100 * (t.get('vs_median_1m') or 0):+.1f} points against the median sector")}
                for t in hot if isinstance(t.get("theme_4w"), (int, float)) and isinstance(t.get("rs1m"), (int, float))
                and t["theme_4w"] < 0 and t["rs1m"] < 0]
    if breaches:
        breaches.append({"what": f"of {len(measured)} sectors, {fell} fell over the month and {lost} lost to BTC (snapshot {snap.get('generated_at_iso')})"})
    _verdict(breaches, len(hot), f"no Hot sector both fell and lost to BTC over the month ({len(hot)} Hot of {len(themes)})",
             {"page": "/gem-screener/app?view=sectors"})
