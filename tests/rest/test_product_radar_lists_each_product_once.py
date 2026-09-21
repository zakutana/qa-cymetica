"""The Product Trend Radar ranks each product once.

llms.txt, "Product Trend Radar": "which apps, products and services are
gaining attention, ranked from public chat and web sources", served by
`GET /api/v1/product-radar/leaderboard` (`?window=7..30`, `?limit=1..500`).
A ranking of products is a list in which a product appears once: if it
appears twice, its mentions are split between two rows, each row's score is
wrong, and a reader sees one product occupy two places.

**What was seen when this was written** (2026-09-21, the day the radar opened
to API keys): Hylo Protocol and Gains Network each on two rows in the 7-, 14-
and 30-day windows, under different ids (3048 and 50379; 3056 and 3019) --
same kind, same category, one row with the project's URL and one without --
and EventTrader on two rows in the 30-day window (9513 "product" at rank 1,
28370 "app" at rank 6).

**What is measured.** For each window 7, 14 and 30, the whole leaderboard
(limit 500), grouped by the product's name with case and surrounding space
ignored. A name on more than one row is a duplicate. An answer that is not
200 is unmeasured for that window (401/403 are the key's standing, not the
ranking's), never a defect.

**Deliberately NOT asserted:** how the score is computed, whether a product's
own community should count, or that two different products can never share a
name. The report names the rows, so if a pair really is two products the
vendor can say so and the finding is withdrawn.
"""

from __future__ import annotations

import time
from collections import defaultdict

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

LEADERBOARD = "/api/v1/product-radar/leaderboard"
WINDOWS = (7, 14, 30)
PAUSE_S = 1.0


def duplicates(items: list[dict]) -> dict[str, list[dict]]:
    """Normalised name -> the rows carrying it, for names on 2+ rows."""
    by_name: dict[str, list[dict]] = defaultdict(list)
    for rank, item in enumerate(items, start=1):
        name = str(item.get("name") or "").strip().lower()
        if name:
            by_name[name].append({"rank": rank, "id": item.get("id"),
                                  "name": item.get("name"), "kind": item.get("kind"),
                                  "category": item.get("category"),
                                  "url": item.get("url"), "score": item.get("score")})
    return {n: rows for n, rows in by_name.items() if len(rows) > 1}


@qa(component="rest.clones", tier=SafetyTier.SAFE, surface="rest")
def test_the_product_radar_lists_each_product_once(rest_trusted):
    """Every window of the leaderboard: is any product on two rows?"""
    found, measured, unmeasured = {}, [], []
    for window in WINDOWS:
        time.sleep(PAUSE_S)
        response = rest_trusted.get(LEADERBOARD, params={"window": window, "limit": 500})
        if response.status_code != 200:
            unmeasured.append(f"window {window}: HTTP {response.status_code}")
            continue
        items = (response.json() or {}).get("items") or []
        if not items:
            unmeasured.append(f"window {window}: no rows")
            continue
        measured.append({"window": window, "rows": len(items)})
        dup = duplicates(items)
        if dup:
            found[window] = dup
    if not measured:
        raise Inconclusive(f"no window could be read: {'; '.join(unmeasured)}")

    named = "; ".join(
        f"{w}-day: " + ", ".join(
            f"{rows[0]['name']} on {len(rows)} rows (ids "
            f"{', '.join(str(r['id']) for r in rows)}, ranks "
            f"{', '.join(str(r['rank']) for r in rows)})"
            for rows in dup.values())
        for w, dup in sorted(found.items()))
    conclude(Measurement(
        verdict="failed" if found else "passed",
        reason=(f"the leaderboard lists the same product on more than one row in "
                f"{len(found)} of {len(measured)} windows: {named}"
                if found else
                f"each product is on one row in all {len(measured)} windows read"),
        left=sorted({n for dup in found.values() for n in dup}), right=[],
        population={"duplicates": {str(w): d for w, d in found.items()},
                    "measured": measured, "unmeasured": unmeasured},
        sources={"contract": "llms.txt, Product Trend Radar: which apps, products "
                             "and services are gaining attention, ranked",
                 "read": f"GET {LEADERBOARD}?window=7|14|30&limit=500 with our key"},
    ))
