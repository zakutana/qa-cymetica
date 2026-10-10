"""A settled card's index is its value at resolution.

The contract is the card's own fields on `GET /api/v1/event-cards?status=settled`:
`contract_spec.resolution_at_utc` is when the card resolves (`trading_closes_at`
is the same moment), its methodology "last-tick" with a 30 s `max_price_staleness`;
`current_index` against `index_base` 100 is the figure a settled card shows.
`GET .../index-history` publishes the path, point by point.

**What was seen when this was written** (2026-10-10, 25 newest settled cards):
13 of 25 show a `current_index` more than 0.5 % from their index at resolution,
the history running on for a day or more after trading closed.

    6fb50de3  "KMM Group Expands Leadership ..."   stocks, XMTR 37 %, PATK 24 %, TSGMY 24 %
              resolution 2026-10-08 09:06 UTC at 100.42
              2026-10-09 11:28 99.80 -> 11:59 203.23; settled current_index 203.16
    50c6fca6  crypto basket, 100.47 at resolution, 93.13 settled, 182 points after it

The 6fb50de3 step is one leg: TSGMY, an OTC ADR quoted at $66.00 with no volume
from 24 September, printed 200 ADRs at $355 on 8 October, while the Tokyo shares
it stands for (6101.T) moved 5,710 -> 5,580 yen. Whatever the print, it came after
the card had resolved.

**The rule.** For every settled card that resolved between MIN_AGE_HOURS and
WINDOW_HOURS ago, `current_index` is within MAX_DRIFT_PCT of the last published
point at or before `resolution_at_utc` (that point at most CLOSE_GAP_MINUTES
before it). A card with no resolution time, no point near it or no current index
is unread, never agreement. The window lets a fix show: cards resolved before it
keep their history and are not judged again.

SAFE. GETs only, anonymous.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

LISTING = "/api/v1/event-cards"
HISTORY = "/api/v1/event-cards/{card}/index-history"

MAX_DRIFT_PCT = 0.5
CLOSE_GAP_MINUTES = 120     # their history is thinned to half-hourly points as it ages
MIN_AGE_HOURS = 2           # leave a settlement job its hour
WINDOW_HOURS = 72
MIN_JUDGED = 5
PAGE = 50


def _moment(value):
    try:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def drift_after_resolution(card: dict, points) -> dict | None:
    """The card's index at its resolution against the index it shows settled, or None when
    either cannot be read."""
    resolution = _moment(((card or {}).get("contract_spec") or {}).get("resolution_at_utc"))
    now = (card or {}).get("current_index")
    if resolution is None or isinstance(now, bool) or not isinstance(now, (int, float)):
        return None
    dated = [(_moment(p.get("t")), p.get("index")) for p in points or () if isinstance(p, dict)]
    dated = [(t, v) for t, v in dated if t is not None and isinstance(v, (int, float))
             and not isinstance(v, bool) and v > 0]
    before = [(t, v) for t, v in dated if t <= resolution]
    if not before:
        return None
    t_close, at_close = max(before, key=lambda tv: tv[0])
    if resolution - t_close > timedelta(minutes=CLOSE_GAP_MINUTES):
        return None
    after = sorted((tv for tv in dated if tv[0] > resolution), key=lambda tv: tv[0])
    return {"card": str(card.get("id") or "")[:8], "resolution": resolution.isoformat(),
            "at_resolution": at_close, "current": now,
            "drift_pct": (now / at_close - 1.0) * 100.0, "points_after": len(after),
            "last_point": after[-1][0].isoformat() if after else None}


@qa(component="rest.event_cards", tier=SafetyTier.SAFE, surface="rest")
def test_a_settled_card_shows_its_index_at_resolution(rest_anon):
    """Every card settled in the last three days shows the index it had when it resolved."""
    listed = rest_anon.get(LISTING, params={"status": "settled", "limit": PAGE})
    if listed.status_code != 200:
        raise Inconclusive(f"{LISTING}?status=settled answered HTTP {listed.status_code}; "
                           f"a failed read is not an empty list")
    cards = (listed.json() or {}).get("cards") or []
    now = datetime.now(timezone.utc)
    subjects = []
    for card in cards:
        resolution = _moment(((card or {}).get("contract_spec") or {}).get("resolution_at_utc"))
        if (card.get("status") == "settled" and resolution is not None
                and now - timedelta(hours=WINDOW_HOURS) <= resolution <= now - timedelta(hours=MIN_AGE_HOURS)):
            subjects.append(card)
    if not subjects:
        raise Inconclusive(f"no card on the first {PAGE} settled resolved in the last {WINDOW_HOURS} h")
    judged, unread = [], []
    for card in subjects:
        history = rest_anon.get(HISTORY.format(card=card["id"]))
        if history.status_code != 200:
            unread.append(f"{card['id'][:8]} (HTTP {history.status_code})")
            continue
        seen = drift_after_resolution(card, (history.json() or {}).get("points"))
        if seen is None:
            unread.append(f"{card['id'][:8]} (no point near its resolution)")
            continue
        seen["title"] = str(card.get("title") or "")[:60]
        judged.append(seen)
    if len(judged) < MIN_JUDGED:
        raise Inconclusive(f"only {len(judged)} of {len(subjects)} settled cards could be read: {unread[:5]}")
    moved = sorted((j for j in judged if abs(j["drift_pct"]) > MAX_DRIFT_PCT),
                   key=lambda j: -abs(j["drift_pct"]))
    conclude(Measurement(
        verdict="failed" if moved else "passed",
        reason=(f"{len(moved)} of {len(judged)} cards settled in the last {WINDOW_HOURS} h show an index more "
                f"than {MAX_DRIFT_PCT}% from the one they had at resolution_at_utc, their history running on "
                f"after trading closed: "
                + "; ".join(f"{m['card']} {m['at_resolution']:.2f} at {m['resolution'][:16]} UTC, shown "
                            f"{m['current']:.2f} ({m['drift_pct']:+.1f}%, {m['points_after']} points after, "
                            f"the last {str(m['last_point'])[:16]})" for m in moved[:4])
                if moved else
                f"all {len(judged)} cards settled in the last {WINDOW_HOURS} h show their index at resolution"),
        left={"cards_moved_after_resolution": len(moved), "judged": len(judged)},
        right={"cards_moved_after_resolution": 0},
        population={"moved": moved[:15], "judged": len(judged), "unread": unread},
        sources={"listing": f"{LISTING}?status=settled&limit={PAGE}", "history": HISTORY}))
