"""/traffic/mine: the tile Unique visitors reads more than its own line's days add up to (2026-11-05).

Read at 14 days: the tile says 1,311 and the line "Unique visitors" in the chart under it adds up to 645. Over any
period, the distinct people cannot be more than the people of each day added together, so the two are not one count
under one name. The page's note explains the column Unique (the product figure on a product, hashed addresses
elsewhere) and says nothing of the tile. The tile moved when #251 was fixed: it read 214 before.

**The rule.** In one response, `totals.unique_visitors` is at most the sum of `unique_daily`, within SAME.

VERDICTS. failed: over by more than SAME. passed: within. inconclusive: a failed read, or no tile or no days.

NOT asserted: which count is right. If they answer by naming the tile apart on the page, this still reads failed:
read the page before sending that verdict. SAFE: one GET; the key is sent in the header and never recorded.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

CLAIM = "traffic-mine-tile-fits-its-days"
MINE = "/api/v1/traffic/mine?days=14"
SAME = 2


def tile_over_days(mine: dict) -> tuple[str | None, str, int, int]:
    """The verdict, why, the tile and the sum of its days."""
    tile = (mine.get("totals") or {}).get("unique_visitors")
    days = mine.get("unique_daily") or {}
    if not isinstance(tile, int) or not days:
        return None, "no tile or no days", 0, 0
    added = sum(days.values())
    if tile > added + SAME:
        return "failed", f"the tile Unique visitors reads {tile:,} and its line's {len(days)} days add up to {added:,}", tile, added
    return "passed", f"the tile ({tile:,}) fits its {len(days)} days ({added:,})", tile, added


@qa(component="rest.traffic", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_the_tile_fits_its_days(rest_trusted):
    """The tile against the line's days, in one response."""
    try:
        got = rest_trusted.get(MINE)
        if got.status_code != 200:
            raise Inconclusive(f"{MINE} answered HTTP {got.status_code}")
        verdict, why, tile, added = tile_over_days(got.json())
    except Inconclusive:
        raise
    except Exception as exc:  # noqa: BLE001 - a failed read is not an empty read
        raise Inconclusive(f"{MINE} could not be read ({type(exc).__name__})")
    if verdict is None:
        raise Inconclusive(why)
    conclude(Measurement(verdict=verdict, reason=why, left={"tile": tile}, right={"sum_of_days": added},
                         population={"tolerance": SAME},
                         sources={"mine": f"{MINE} totals.unique_visitors, unique_daily",
                                  "credential": "X-API-Key, trusted tier (value never recorded)"},
                         claim_id=CLAIM))
