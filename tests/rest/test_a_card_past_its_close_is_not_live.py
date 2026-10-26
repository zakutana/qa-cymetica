"""An event card whose trading has closed does not stay live (2026-10-26).

Found 2026-10-26 while drawing the phone deck (outbox/event-card-mobile): GET /api/v1/event-cards, every live card (647, the
list /events deals its deck from), holds six news cards whose contract resolves at trading close (contract_spec
"resolution_basis": "trading_close") and whose trading_closes_at -- the same moment as resolution_at_utc -- passed between
2026-08-15 and 2026-09-15, six to ten weeks earlier. All six read status "live". llms.txt: "A card is tradeable when
status=live; trading_closes_at is null on open-ended cards (they trade until they resolve)". Their tradeable_now is false,
and trading_blocked_reason gives the US market's hours or a price that has not refreshed, never that trading closed; none is
settled. The same day Cymetica wrote (REPLY-0222) that "news cards leave the live list after 72 hours".

**The rule.** No card in the live list has a close more than GRACE_HOURS behind the read: a card past its close is settled,
closed or gone from the live list. The close is trading_closes_at, or, when that is empty, contract_spec.resolution_at_utc
on a card whose resolution_basis is "trading_close". An open-ended card (no close) is never judged.

VERDICTS. failed: a live card's close is more than GRACE_HOURS past. passed: none is, with the whole list read. inconclusive:
the list cannot be read whole (a failed page, or fewer cards than its total), it is empty, or a live card's close cannot be
parsed and no other card fails.

NOT asserted: whether such a card can be bought (tradeable_now is false on all six); the settled card's index (see
test_a_settled_card_stops_at_its_resolution); open-ended cards, which trade until they resolve.
SAFE. GETs only, anonymous.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import httpx

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude
from tests.rest.test_gem_screener_numbers_match_their_sources import get_patiently

LISTING = "/api/v1/event-cards/"
PAGE = 200
MAX_PAGES = 20
GRACE_HOURS = 24          # a settlement job's day
UNREADABLE = object()


def _moment(value):
    if value in (None, ""):
        return None
    try:
        moment = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return UNREADABLE
    return moment if moment.tzinfo else moment.replace(tzinfo=timezone.utc)


def close_of(card: dict):
    """When the card's trading closes: a datetime, None for an open-ended card, or UNREADABLE."""
    close = _moment(card.get("trading_closes_at"))
    if close is None:
        spec = card.get("contract_spec") or {}
        if spec.get("resolution_basis") == "trading_close":
            close = _moment(spec.get("resolution_at_utc"))
    return close


def judge(cards: list[dict], total, now: datetime) -> tuple[str | None, str, list[dict]]:
    """(verdict, why, past): "failed", "passed", or None for inconclusive, over every card of the live list."""
    if not cards:
        return None, "the live list holds no card", []
    if not isinstance(total, int) or len(cards) < total:
        return None, f"the live list was read in part ({len(cards)} of {total})", []
    past, unread = [], []
    for k, card in enumerate(cards):
        if card.get("status") != "live":
            continue
        close = close_of(card)
        if close is UNREADABLE:
            unread.append(str(card.get("id"))[:8])
        elif close is not None and now - close > timedelta(hours=GRACE_HOURS):
            past.append({"card": str(card.get("id"))[:8], "position": k, "title": str(card.get("title") or "")[:60],
                         "close": close.isoformat(), "days_past": round((now - close).total_seconds() / 86400, 1),
                         "tradeable_now": card.get("tradeable_now"),
                         "trading_blocked_reason": str(card.get("trading_blocked_reason") or "")[:90]})
    if past:
        past.sort(key=lambda p: p["close"])
        return "failed", (f"{len(past)} of {len(cards)} live cards closed more than {GRACE_HOURS} h ago and still read status "
                          f"live, the oldest closed {past[0]['close'][:10]} ({past[0]['days_past']} days): "
                          + "; ".join(f"{p['card']} closed {p['close'][:10]}" for p in past[:6])), past
    if unread:
        return None, f"{len(unread)} live card(s) carry a close this check cannot read: {unread[:5]}", []
    return "passed", f"no live card of {len(cards)} is more than {GRACE_HOURS} h past its close", []


@qa(component="rest.event_cards", tier=SafetyTier.SAFE, surface="rest")
def test_a_card_past_its_close_is_not_live(rest_anon):
    """No card in the live list is more than a day past its trading close."""
    cards, total = [], None
    for page in range(MAX_PAGES):
        try:
            got = get_patiently(rest_anon, LISTING, params={"limit": PAGE, "offset": page * PAGE})
        except httpx.HTTPError as exc:
            raise Inconclusive(f"{LISTING} could not be read: {type(exc).__name__}")
        if got.status_code != 200:
            raise Inconclusive(f"{LISTING}?offset={page * PAGE} answered HTTP {got.status_code}; a failed read is not an empty list")
        body = got.json() or {}
        total = body.get("total")
        batch = body.get("cards") or []
        cards += batch
        if not batch or (isinstance(total, int) and len(cards) >= total):
            break
    now = datetime.now(timezone.utc)
    verdict, why, past = judge(cards, total, now)
    if verdict is None:
        raise Inconclusive(why)
    conclude(Measurement(
        verdict=verdict,
        reason=(f"{why}. llms.txt says a card is tradeable when status=live; these are past the close their own contract "
                f"names and still sit in the list /events deals its deck from" if verdict == "failed" else why),
        left={"live_cards_past_close": len(past)},
        right={"live_cards_past_close": 0},
        population={"past": past[:20], "live_cards": len(cards), "total": total, "read_at": now.isoformat(timespec="seconds")},
        sources={"listing": f"{LISTING}?limit={PAGE}&offset=0..", "fields": "status, trading_closes_at, "
                 "contract_spec.resolution_basis, contract_spec.resolution_at_utc"}))
