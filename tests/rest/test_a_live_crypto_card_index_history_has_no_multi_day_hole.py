"""A live crypto card's index history has no multi-day hole (2026-10-12, T-0052).

`GET /api/v1/event-cards/{id}/index-history` publishes a card's index, and for a card whose basket
is crypto it is a market that trades around the clock: the card reads `status` live,
`tradeable_now` true, `trading_closes_at` null and `trading_blocked_reason` null. Nothing in
llms.txt, the OpenAPI or the card says its history may stop recording.

**What was seen when this was written** (2026-10-12, anonymous). The BTC proxy
a4a5b71e-de11-4805-b8a3-ed9c3f8f8161 ("SpaceX IPO: Top 10 Crypto Plays", 99% BTC) answered
`interval=30d` with one point every 3 h, 8 a day, on every day of the window except these:

    2026-09-23   5 points, the last at 14:16:52 UTC  (index 137.714)
    2026-09-24   none
    2026-09-25   3 points, the first at 17:54:33 UTC (index 134.256)

a hole of 51.6 h in which the index moved by 3.46. `interval=all` shows the same hole (56.8 h).
It is this card, not the platform: 30408a4b (ZEN, KSM, TRX), 30015006 (BNB, ZEC, ICX) and 5d91bf43,
all crypto-only and older, hold 17, 17 and 18 points inside those same hours with a widest gap of
3.0 to 3.2 h. The one hole every card shares is 2026-09-17 14:40 to 20:59 UTC (6.3 h, 3.0 h grid).
Our own scripts read the proxy as the benchmark of 200 laboratory rooms, so a room whose window
spans the hole was judged against a series that was not recording.

**The list needs `include_user_submitted=true`.** The default list (641 cards) leaves out the proxy,
which is a user-submitted card (`listed_in_default_feed` false, offset 600 of the 661 of the wider
list); the first run of this check read only the default list, judged 12 cards and passed.

**The rule.** For every card in that list that is live, tradeable, not past `trading_closes_at`
and at least MIN_CRYPTO_WEIGHT crypto by basket weight, the widest gap between two consecutive
points of its `interval=30d` history is at most MAX_GAP_HOURS -- and so is the stretch from its newest
point to the server's own clock (the response's Date header), or a recorder that stopped and stayed
stopped would pass (C07, deep pass 2026-10-18). 12 h is four times the 3 h grid and
about twice the platform-wide outage above. A card with no points in the window is named and not
judged (it records nothing at all, which is a different question); one point is no gap.

A pass is the rule holding for the cards the list showed at the moment of the read. `population`
names every card judged with its widest gap, and for each failing card how many OTHER judged
cards recorded a point inside its widest gap -- the control that says card-only or platform-wide.
A pass needs the list to have ended within the pages read, and no more than a quarter of the open
crypto cards' histories unread (non-200, an unreadable time, no Date header); past either it is
Inconclusive, naming them (A02, deep pass 2026-10-25). A hole seen on a card that was read fails
however many others were not read.

**What a pass after about 2026-10-25 means.** The history keeps the hole for as long as its window
does: 30 days, so the stretch of 09-23..25 leaves `30d` around 10-23 to 10-25. A pass after that
is the window healing, not a repair; a repair is a backfill, and it shows before then. The same
follows for any future hole, which this check will read for 30 days.

**Their fix (#202, REPLY-0168, 2026-10-15).** They do not fill in readings that were never taken;
instead `index-history` lists every gap as `gaps: [{from, to, hours}]` beside a `gaps_note` ("A gap
is a stretch with no recorded index reading for this card. No values are filled in for it"). Read
live that day, a4a5b71e's 30d history declares exactly the hole above. So the check holds them to
that: a hole over MAX_GAP_HOURS that the same response does NOT list is the defect; a declared one
is the published behaviour (`declared`). Repaired by the deep pass of 2026-10-15, 0b.

NOT asserted: why (a recorder that stopped, a data job that failed), that every card must have a
point every 3 h, or anything about cards with a stock leg, whose index is allowed to be still while
their market is shut.

SAFE: GETs, anonymous.
"""

from __future__ import annotations

from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

LIST = "/api/v1/event-cards"
HISTORY = "/api/v1/event-cards/{card}/index-history"
CLAIM = "live-crypto-card-index-history-has-no-multi-day-hole"
MAX_GAP_HOURS = 12.0
MIN_CRYPTO_WEIGHT = 0.9
PAGE = 100
MAX_PAGES = 12


def _when(value) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def widest_gap(points) -> tuple[float, str, str] | None:
    """The widest gap between two consecutive points of a history, as (hours, from, to): the times
    as they are written. None when fewer than two points, or when any point cannot be read -- a
    bad point dropped would close the hole it sat inside."""
    if not isinstance(points, list):
        return None
    times = []
    for point in points:
        when = _when(point.get("t")) if isinstance(point, dict) else None
        if when is None:
            return None
        times.append((when, point["t"]))
    if len(times) < 2:
        return None
    times.sort(key=lambda pair: pair[0])
    best = max(zip(times, times[1:]), key=lambda ab: ab[1][0] - ab[0][0])
    return ((best[1][0] - best[0][0]).total_seconds() / 3600.0, best[0][1], best[1][1])


DECLARE_SLACK_HOURS = 1.0


def declared(hole_from, hole_to, gaps) -> bool:
    """A hole between two points is declared when one entry of the response's `gaps` list starts
    and ends within DECLARE_SLACK_HOURS of it: the list names that stretch, not a part of it."""
    a, b = _when(hole_from), _when(hole_to)
    if a is None or b is None or not isinstance(gaps, list):
        return False
    for gap in gaps:
        if not isinstance(gap, dict):
            continue
        ga, gb = _when(gap.get("from")), _when(gap.get("to"))
        if ga is None or gb is None:
            continue
        if (abs((ga - a).total_seconds()) <= DECLARE_SLACK_HOURS * 3600
                and abs((gb - b).total_seconds()) <= DECLARE_SLACK_HOURS * 3600):
            return True
    return False


def undeclared_holes(points, gaps, max_hours: float) -> list[tuple[float, str, str]]:
    """Every stretch between two consecutive points longer than `max_hours` that `gaps` does not
    declare, as (hours, from, to), in time order. Every hole, not only the widest: a declared
    51.6 h hole must not hide an undeclared 20 h one (A03, deep pass 2026-10-15). Points whose
    time cannot be read are dropped by the caller's widest_gap() check first."""
    times = sorted((when, point["t"]) for point in points or [] if isinstance(point, dict)
                   for when in [_when(point.get("t"))] if when is not None)
    out = []
    for (a, a_raw), (b, b_raw) in zip(times, times[1:]):
        hours = (b - a).total_seconds() / 3600.0
        if hours > max_hours and not declared(a_raw, b_raw, gaps):
            out.append((hours, a_raw, b_raw))
    return out


def server_now(date_header) -> datetime | None:
    """The server's own clock from a response's Date header, or None: the tail of a history is
    measured against their now, never ours (a first look from our clock is a claim about us)."""
    if not isinstance(date_header, str):
        return None
    try:
        when = parsedate_to_datetime(date_header)
    except (TypeError, ValueError, IndexError):
        return None
    if when is None:
        return None
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)


def tail_hole(points, gaps, now: datetime | None, max_hours: float) -> tuple[float, str, str] | None:
    """The stretch from the newest point to `now` (the server's clock), as (hours, from, to), when it
    is longer than `max_hours` and no entry of `gaps` declares it open from that point (`to` empty or
    reaching now). None otherwise.

    C07, deep pass 2026-10-18: only stretches between two points were measured, so a live card whose
    recorder stopped three days ago -- the incident's own shape, still running -- passed."""
    if now is None:
        return None
    times = sorted(when for point in points or [] if isinstance(point, dict)
                   for when in [_when(point.get("t"))] if when is not None)
    if not times:
        return None
    last = times[-1]
    hours = (now - last).total_seconds() / 3600.0
    if hours <= max_hours:
        return None
    slack = DECLARE_SLACK_HOURS * 3600
    for gap in gaps if isinstance(gaps, list) else []:
        if not isinstance(gap, dict):
            continue
        start, end = _when(gap.get("from")), _when(gap.get("to"))
        if start is not None and abs((start - last).total_seconds()) <= slack and (
                end is None or (now - end).total_seconds() <= slack):
            return None
    raw = next(p["t"] for p in points if isinstance(p, dict) and _when(p.get("t")) == last)
    return (hours, raw, now.isoformat(timespec="seconds"))


def too_much_unread(subjects: int, unread: list) -> bool:
    """Whether the cards whose history could not be read are more than a quarter of the open crypto
    cards: then a pass would rest on what was not read (rule 8). A02, deep pass 2026-10-25: only
    `if not judged` stopped a pass, so a 500 on 19 of 20 cards passed as "all 1 open crypto card(s)".
    A hole seen on a card that was read is a defect however many were not."""
    return len(unread) > subjects // 4


def _crypto_share(basket) -> float:
    legs = [leg for leg in basket or [] if isinstance(leg, dict)]
    total = sum(float(leg.get("weight") or 0) for leg in legs)
    if total <= 0:
        return 0.0
    return sum(float(leg.get("weight") or 0) for leg in legs if leg.get("asset_type") == "crypto") / total


def _is_open(card: dict, now: datetime) -> bool:
    closes = _when(card.get("trading_closes_at"))
    return (card.get("status") == "live" and card.get("tradeable_now") is True
            and (closes is None or closes > now))


@qa(component="rest.event_cards", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_live_crypto_card_index_history_has_no_multi_day_hole(rest_anon):
    """Every open crypto card's 30-day index history against the 12 h it may go without a point."""
    cards, offset = [], 0
    for _ in range(MAX_PAGES):
        page = rest_anon.get(LIST, params={"limit": PAGE, "offset": offset,
                                           "include_user_submitted": "true"})
        if page.status_code != 200:
            raise Inconclusive(f"{LIST} answered HTTP {page.status_code} at offset {offset}")
        rows = (page.json() or {}).get("cards") or []
        cards += [r for r in rows if isinstance(r, dict)]
        if len(rows) < PAGE:
            break
        offset += PAGE
    else:
        # A02, deep pass 2026-10-25: twelve full pages and no short one -- the list goes on past
        # what was read, and a pass over the first 1200 cards is not a pass over the list.
        raise Inconclusive(f"{LIST} answered a full page of {PAGE} at each of {MAX_PAGES} offsets, so "
                           f"the list goes on past the {MAX_PAGES * PAGE} cards read; a card past them "
                           f"is not judged, and a pass would not be about the list")
    now = datetime.now(timezone.utc)
    subjects = [c for c in cards if _is_open(c, now) and _crypto_share(c.get("basket")) >= MIN_CRYPTO_WEIGHT]
    if not subjects:
        raise Inconclusive(f"no open crypto card among the {len(cards)} the list showed")

    judged, empty, unread, series = [], [], [], {}
    for card in subjects:
        cid = card.get("id")
        read = rest_anon.get(HISTORY.format(card=cid), params={"interval": "30d"})
        if read.status_code != 200:
            unread.append(f"{str(cid)[:8]}: HTTP {read.status_code}")
            continue
        body = read.json() or {}
        points = body.get("points")
        if not points:
            empty.append(str(cid)[:8])
            continue
        gap = widest_gap(points)
        if gap is None and len(points) >= 2:
            unread.append(f"{str(cid)[:8]}: a point's time is unreadable")
            continue
        theirs = server_now(read.headers.get("date"))
        if theirs is None:
            unread.append(f"{str(cid)[:8]}: no Date header to measure its newest point against")
            continue
        series[cid] = sorted(t for t in (_when(p.get("t")) for p in points) if t is not None)
        open_holes = undeclared_holes(points, body.get("gaps"), MAX_GAP_HOURS)
        # C07: and from the newest point to their now -- a recorder that stopped and stays stopped
        tail = tail_hole(points, body.get("gaps"), theirs, MAX_GAP_HOURS)
        if tail:
            open_holes.append(tail)
        worst = max(open_holes, key=lambda h: h[0]) if open_holes else None
        judged.append({"id": cid, "title": (card.get("title") or "")[:60], "points": len(points),
                       "widest_gap_hours": round(gap[0], 1) if gap else 0.0,
                       "from": gap[1] if gap else None, "to": gap[2] if gap else None,
                       # every hole over the limit was declared (A03: not only the widest)
                       "declared": not open_holes,
                       "undeclared": [{"hours": round(h, 1), "from": a, "to": b} for h, a, b in open_holes],
                       "undeclared_widest_hours": round(worst[0], 1) if worst else 0.0,
                       "undeclared_from": worst[1] if worst else None,
                       "undeclared_to": worst[2] if worst else None})
    if not judged:
        raise Inconclusive(f"no open crypto card had a readable 30d history ({len(subjects)} open, "
                           f"empty {empty}, unread {unread[:3]})")

    declared_holes = [j for j in judged if j["widest_gap_hours"] > MAX_GAP_HOURS and j["declared"]]
    holes = [j for j in judged if not j["declared"]]
    if not holes and too_much_unread(len(subjects), unread):
        raise Inconclusive(f"{len(unread)} of {len(subjects)} open crypto cards' 30-day histories could "
                           f"not be read, more than a quarter: {'; '.join(unread[:12])}; the {len(judged)} "
                           f"read kept their points, which does not make the rest whole")
    for hole in holes:
        # The card's widest UNDECLARED hole is the one named and controlled for.
        hole["widest_gap_hours"] = hole["undeclared_widest_hours"]
        hole["from"], hole["to"] = hole["undeclared_from"], hole["undeclared_to"]
        a, b = _when(hole["from"]), _when(hole["to"])
        # Only a card that already had history when the hole began can be a control for it.
        existed = [o for o in judged if o["id"] != hole["id"] and series[o["id"]][0] < a]
        hole["other_cards_with_a_point_inside"] = sum(
            1 for o in existed if any(a < t < b for t in series[o["id"]]))
        hole["other_cards_judged"] = len(existed)
    named = "; ".join(
        f"{h['id']} ({h['title']!r}): {h['widest_gap_hours']} h with no point, {h['from']} to {h['to']}; "
        f"{h['other_cards_with_a_point_inside']} of {h['other_cards_judged']} other open crypto cards "
        f"that already had history recorded a point inside it" for h in holes)
    conclude(Measurement(
        verdict="failed" if holes else "passed",
        reason=(f"{len(holes)} of {len(judged)} open crypto card(s) have a hole of more than "
                f"{MAX_GAP_HOURS:g} h in their 30-day index history that the history's own gaps list "
                f"does not declare, while the card reads live and tradeable. {named}" if holes else
                f"all {len(judged)} open crypto card(s) with a 30-day history kept a point within "
                f"every {MAX_GAP_HOURS:g} h, up to the server's own now, or declared the gap"
                + (f" ({len(declared_holes)} declared: "
                   + "; ".join(f"{h['id']} {h['widest_gap_hours']} h" for h in declared_holes) + ")"
                   if declared_holes else "")),
        left={"open_crypto_cards_with_an_undeclared_hole": len(holes)},
        right={"open_crypto_cards_with_an_undeclared_hole": 0},
        population={"listed": len(cards), "open_crypto": len(subjects), "judged": judged,
                    "declared_holes": [h["id"] for h in declared_holes],
                    "no_points_in_window": empty, "unread": unread},
        sources={"history": f"{HISTORY} interval=30d points[].t",
                 "list": f"{LIST} status, tradeable_now, trading_closes_at, basket[].asset_type and weight"},
        claim_id=CLAIM))
