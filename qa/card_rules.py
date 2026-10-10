"""Two card rules we fitted ourselves, and the only data allowed to judge them.

Fitted 2026-10-03 on 27 307 settled event cards of the new generation (created from 2026-09-03): the badges
(sentiment, impact) predicted nothing, the basket's asset mix held across both halves -- stock-only cards
drifted down over their 72 h, cards with a crypto leg drifted up. A pattern fitted on seen data is a
hypothesis until data it has not seen agrees (NEXT.md, V3), so the rules, the date and the criterion are fixed
HERE, before a single card created after them has settled:

    short_stock_only    every card whose basket holds only stocks, short (the index return, sign flipped)
    long_with_crypto    every card with at least one crypto leg, long

Judged only on cards created on or after FROM. PASS needs MIN_CARDS cards and the lower 95 % bound of the
mean side-return above zero; FAIL needs the upper bound below zero; between them is INCONCLUSIVE; fewer cards
is NOT ENOUGH. Paper costs nothing (a $10 round trip came back $10.00, TRD-0086/0087), so a pass is an upper
bound on what an account would earn, never the earning itself.

Pure: no I/O. `scripts/card_rules.py` reads the listing and prints this.
"""

from __future__ import annotations

import math
from datetime import datetime
from statistics import mean, pstdev

FROM = "2026-10-04T00:00:00+00:00"
MIN_CARDS = 200
Z95 = 1.96
RULES = {
    "short_stock_only": {"side": -1, "what": "basket only stocks, short"},
    "long_with_crypto": {"side": 1, "what": "at least one crypto leg, long"},
}


def _at(value):
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def rule_of(card: dict) -> str | None:
    """Which rule a card belongs to, by its basket alone; None when neither."""
    types = {str((leg or {}).get("asset_type") or "").lower() for leg in (card or {}).get("basket") or []}
    types.discard("")
    if not types:
        return None
    if "crypto" in types:
        return "long_with_crypto"
    if types == {"stock"}:
        return "short_stock_only"
    return None


CLOSE_GAP_MINUTES = 120    # their index history is thinned to half-hourly points as it ages


def index_at_resolution(card: dict, points) -> float | None:
    """The last published index at or before the card's `contract_spec.resolution_at_utc`, at
    most CLOSE_GAP_MINUTES before it; None when there is none. 2026-10-10: a settled card's
    `current_index` keeps moving after resolution (6fb50de3: 100.42 at resolution, 203.16 shown),
    so it is not what the card settled at. The same rule as
    tests/rest/test_a_settled_card_stops_at_its_resolution.py."""
    resolution = _at(((card or {}).get("contract_spec") or {}).get("resolution_at_utc"))
    if resolution is None:
        return None
    best = None
    for point in points or ():
        moment, value = _at((point or {}).get("t")), (point or {}).get("index")
        if (moment is None or isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value <= 0 or moment > resolution):
            continue
        if best is None or moment > best[0]:
            best = (moment, float(value))
    if best is None or (resolution - best[0]).total_seconds() > CLOSE_GAP_MINUTES * 60:
        return None
    return best[1]


def index_return_pct(card: dict) -> float | None:
    """The card's index move from its base, in percent; None when it cannot be read. A card with
    a resolution time is read at it (`index_at_resolution`, set by the caller from its history),
    never at the `current_index` shown after."""
    now, base = card.get("current_index"), card.get("index_base")
    if ((card.get("contract_spec") or {}).get("resolution_at_utc")) is not None:
        now = card.get("index_at_resolution")
    if (isinstance(now, bool) or isinstance(base, bool)
            or not isinstance(now, (int, float)) or not isinstance(base, (int, float))
            or not base or not math.isfinite(now) or not math.isfinite(base)):
        return None
    return (now / base - 1.0) * 100.0


def evaluate(cards: list[dict]) -> dict:
    """Per rule: n, unread, excluded_before, mean/median of the side-return in %, the 95 % bounds, verdict."""
    start = _at(FROM)
    seen: set = set()
    bucket = {name: {"returns": [], "unread": 0, "excluded_before": 0} for name in RULES}
    for card in cards or []:
        key = card.get("id")
        if key is not None:
            if key in seen:
                continue
            seen.add(key)
        rule = rule_of(card)
        if rule is None:
            continue
        created = _at(card.get("created_at"))
        if created is None or created < start:
            bucket[rule]["excluded_before"] += 1
            continue
        ret = index_return_pct(card)
        if ret is None:
            bucket[rule]["unread"] += 1
            continue
        bucket[rule]["returns"].append(RULES[rule]["side"] * ret)
    out = {}
    for name, b in bucket.items():
        values = b["returns"]
        n = len(values)
        row = {"what": RULES[name]["what"], "n": n, "unread": b["unread"],
               "excluded_before": b["excluded_before"], "mean_pct": None, "median_pct": None,
               "win_share": None, "low_pct": None, "high_pct": None, "verdict": "not enough"}
        if n:
            m = mean(values)
            half = Z95 * pstdev(values) / math.sqrt(n) if n > 1 else float("inf")
            ordered = sorted(values)
            row.update(mean_pct=m, median_pct=ordered[n // 2] if n % 2 else (ordered[n // 2 - 1] + ordered[n // 2]) / 2,
                       win_share=sum(1 for v in values if v > 0) / n, low_pct=m - half, high_pct=m + half)
            if n >= MIN_CARDS:
                row["verdict"] = ("pass" if m - half > 0 else "fail" if m + half < 0 else "inconclusive")
        out[name] = row
    return out
