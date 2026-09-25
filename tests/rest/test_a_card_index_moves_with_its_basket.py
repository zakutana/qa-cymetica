"""A card's index does not move further in one step than its basket can.

The contract is the card's own fields on `GET /api/v1/event-cards/{id}`: an
event card is a basket (`basket[]`, each leg a listed asset with a `weight`
and its `market_cap_rank`), and `current_index` is that basket's value
against `index_base` 100 -- `pw_index` over `pw_base` is the same ratio, the
mean of the legs' prices now against at creation. `GET .../index-history`
publishes the path, point by point. A position's `current_value_usdc` on
`GET /api/v1/event-cards/positions` is its units times that index.

**What was seen when this was written** (2026-09-25):

    d23b4cf2  "Alchemy Expands into APAC ..."   TRX 48.8 %, XTZ 47.2 %, ENJ 4.0 %
              10:27:07 100.437 -> 10:30:21 243.393   (+142.3 % in one step)
    97b827ad  "CME Group to Expand ..."          BCH 97.2 %, UNI 2.8 %, DUSK
              13:19:54 100.704 -> 13:29:25  14.925   (-85.2 % in one step)

TRX, XTZ and BCH are top-200 assets that moved -1 % to -3.5 % that day, and
the cards' own `pw_index` / `pw_base` say the same thing the index does: the
mean leg price went 0.2315 -> 0.5513 and 114.64 -> 17.08 -- one leg priced at
several times, or a fraction of, what it trades at. Our paper position on
d23b4cf2 read +658.52 USDC on 476.85 from that step alone.

**The rule.** A basket whose large-cap legs (`market_cap_rank` at most
LARGE_CAP_RANK) carry at least LARGE_CAP_WEIGHT of its weight cannot move
more than MAX_STEP in one published step of at most STEP_MINUTES. Subjects:
every card we hold an open position on (their positions list), the steps of
the last WINDOW_HOURS. A card outside that shape -- small caps, a stock leg
-- is named and not judged: a memecoin basket can do what this forbids.

The window is what lets a fix show: the history keeps the bad step for its
five-day interval, and a check over all of it could not go green for five
days whatever they did (the growing-log lesson). A repair that snaps the
index back is itself a step, and fails until it leaves the window.

SAFE. GETs only.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

POSITIONS = "/api/v1/event-cards/positions"
CARD = "/api/v1/event-cards/{card}"
HISTORY = "/api/v1/event-cards/{card}/index-history"

# 200, not 100: XTZ is 133 on their own rank, and a top-200 coin does not
# double in an hour either. 60 minutes, not 15: their history is thinned as
# it ages -- 97b827ad's step read 13:19:54 -> 13:29:25 at 14:20 and
# 13:19:54 -> 13:33:18 at 14:40, and at a 15-minute limit the first run of
# this check read no step at all.
LARGE_CAP_RANK = 200
LARGE_CAP_WEIGHT = 0.9
MAX_STEP = 0.40
STEP_MINUTES = 60
WINDOW_HOURS = 24


def _moment(value):
    try:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def large_cap_share(basket) -> float:
    """The weight carried by legs their own rank puts in the top LARGE_CAP_RANK."""
    share = 0.0
    for leg in basket or []:
        rank, weight = leg.get("market_cap_rank"), leg.get("weight")
        if isinstance(rank, int) and rank <= LARGE_CAP_RANK and isinstance(
                weight, (int, float)):
            share += float(weight)
    return share


def jumps(points, since) -> list[dict]:
    """Published steps of at most STEP_MINUTES, inside the window, that moved
    the index by more than MAX_STEP."""
    out = []
    for a, b in zip(points, points[1:]):
        t0, t1 = _moment(a.get("t")), _moment(b.get("t"))
        v0, v1 = a.get("index"), b.get("index")
        if (None in (t0, t1) or not isinstance(v0, (int, float))
                or not isinstance(v1, (int, float)) or v0 <= 0):
            continue
        if t1 < since or (t1 - t0) > timedelta(minutes=STEP_MINUTES):
            continue
        change = v1 / v0 - 1.0
        if abs(change) > MAX_STEP:
            out.append({"from": [a.get("t"), v0], "to": [b.get("t"), v1],
                        "change_pct": round(change * 100, 1)})
    return out


@qa(component="rest.event_cards", tier=SafetyTier.SAFE, surface="rest")
def test_a_card_index_moves_no_further_than_its_basket_can(rest_trusted):
    """Every card we hold, its steps of the last day against its basket."""
    listed = rest_trusted.get(POSITIONS)
    if listed.status_code != 200:
        raise Inconclusive(f"{POSITIONS} answered HTTP {listed.status_code}; "
                           f"a failed read is not an empty book")
    cards = sorted({p.get("card_id") for p in (listed.json() or {}).get("positions") or []
                    if p.get("status") == "open" and p.get("card_id")})
    if not cards:
        raise Inconclusive("no open position, so no card to read")

    since = datetime.now(timezone.utc) - timedelta(hours=WINDOW_HOURS)
    judged, other, unread, breaches = [], [], [], []
    for card_id in cards:
        card = rest_trusted.get(CARD.format(card=card_id))
        history = rest_trusted.get(HISTORY.format(card=card_id))
        if card.status_code != 200 or history.status_code != 200:
            unread.append(f"{card_id[:8]} (HTTP {card.status_code}/{history.status_code})")
            continue
        body = card.json() or {}
        share = large_cap_share(body.get("basket"))
        if share < LARGE_CAP_WEIGHT:
            other.append(f"{card_id[:8]} ({share:.0%} large-cap)")
            continue
        points = (history.json() or {}).get("points") or []
        judged.append(card_id)
        for jump in jumps(points, since):
            breaches.append({
                "card": card_id, "title": str(body.get("title") or "")[:60],
                "basket": [(leg.get("symbol"), leg.get("weight"),
                            leg.get("market_cap_rank")) for leg in body.get("basket") or []],
                "pw_base": body.get("pw_base"), "pw_index": body.get("pw_index"),
                **jump})

    named = []
    if other:
        named.append(f"not a large-cap basket, not judged: {', '.join(other)}")
    if unread:
        named.append(f"unread: {', '.join(unread)}")
    tail = (". NOT in the verdict -- " + " | ".join(named)) if named else ""
    if not judged:
        raise Inconclusive(f"none of the {len(cards)} card(s) we hold is a "
                           f"large-cap basket{tail}")
    conclude(Measurement(
        verdict="failed" if breaches else "passed",
        reason=("; ".join(
            f"{b['card'][:8]} '{b['title']}' ({', '.join(f'{s} {w:.0%}' for s, w, _ in b['basket'] if isinstance(w, (int, float)))}) "
            f"moved {b['change_pct']:+.1f}% in one step, {str(b['from'][0])[11:19]} "
            f"{b['from'][1]:.3f} -> {str(b['to'][0])[11:19]} {b['to'][1]:.3f}; "
            f"pw_index/pw_base {b['pw_index']}/{b['pw_base']}"
            for b in breaches[:4])
            if breaches else
            f"no step of the last {WINDOW_HOURS} h moved any of {len(judged)} "
            f"large-cap basket(s) by more than {MAX_STEP:.0%}") + tail,
        left=[{k: b[k] for k in ("card", "change_pct", "from", "to")} for b in breaches],
        right=f"no step over {MAX_STEP:.0%} on a basket at least "
              f"{LARGE_CAP_WEIGHT:.0%} top-{LARGE_CAP_RANK}",
        population={"held": len(cards), "judged": judged, "not_judged": other,
                    "unread": unread, "window_hours": WINDOW_HOURS},
        sources={"cards": CARD, "history": HISTORY, "positions": POSITIONS}))
