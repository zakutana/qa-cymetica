"""What the "a live crypto card's index history has no multi-day hole" check may pass on (A02, deep pass 2026-10-25).

Three readers reproduced it: a card whose history read failed went to `unread` and only `if not judged`
stopped a pass, so a 500 on 19 of 20 open crypto cards passed as "all 1 open crypto card(s)". And the
list was read twelve full pages deep with no check that it had ended, so a cut list passed as the list.
Here the whole check runs against a fake platform (its own `conclude` decides); its measurement is taken
back off this test afterwards so the recorder does not file it under the vendor claim.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

from qa.marks import SafetyTier, qa
from tests.rest.test_a_live_crypto_card_index_history_has_no_multi_day_hole import (
    test_live_crypto_card_index_history_has_no_multi_day_hole as check,
)


class _Reply:
    def __init__(self, status: int, body=None, date: str | None = None):
        self.status_code, self._body = status, body
        self.headers = {"date": date} if date else {}

    def json(self):
        return self._body


def _card(i: int, live: bool = True) -> dict:
    return {"id": f"{i:08d}-0000", "title": f"card {i}", "status": "live" if live else "closed",
            "tradeable_now": live, "trading_closes_at": None,
            "basket": [{"asset_type": "crypto", "weight": 1.0}]}


class _Platform:
    """`open_cards` live crypto cards on the first page; `broken` of them answer their history with a 500;
    `holed` one has a 30 h undeclared hole; `endless` answers every page of the list full."""

    def __init__(self, open_cards: int, broken: int = 0, holed: bool = False, endless: bool = False):
        self.open_cards, self.broken, self.holed, self.endless = open_cards, broken, holed, endless
        self.now = datetime.now(timezone.utc).replace(microsecond=0)

    def get(self, url, params=None):
        params = params or {}
        if url == "/api/v1/event-cards":
            offset = int(params.get("offset", 0))
            if self.endless:
                rows = [_card(offset + k, live=(offset + k) < self.open_cards) for k in range(100)]
            else:
                rows = [_card(k) for k in range(self.open_cards)] if offset == 0 else []
            return _Reply(200, {"cards": rows})
        index = int(url.split("/")[-2].split("-")[0])
        if index < self.broken:
            return _Reply(500, {"detail": "Internal Server Error"})
        hours = range(0, 72, 3)
        if self.holed and index == self.open_cards - 1:
            hours = [h for h in hours if not 30 <= h <= 57]          # 30 h with no point, undeclared
        points = [{"t": (self.now - timedelta(hours=h + 1)).isoformat(), "index": 100.0} for h in hours]
        return _Reply(200, {"points": sorted(points, key=lambda p: p["t"]), "gaps": []},
                      date=format_datetime(self.now, usegmt=True))


def _drive(client) -> tuple[str, str]:
    from qa.marks import Inconclusive
    from qa.measure import CURRENT_MEASUREMENT

    CURRENT_MEASUREMENT.set(None)
    try:
        check(client)
        verdict, reason = "passed", ""
    except AssertionError as exc:
        verdict, reason = "failed", str(exc)
    except Inconclusive as exc:
        verdict, reason = "inconclusive", str(exc)
    finally:
        measured = CURRENT_MEASUREMENT.get()
        CURRENT_MEASUREMENT.set(None)          # not this test's own record
    return verdict, (measured.reason if measured is not None and measured.reason else reason)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_pass_may_not_rest_on_one_card_of_twenty():
    verdict, reason = _drive(_Platform(open_cards=20, broken=19))
    assert verdict == "inconclusive", (verdict, reason)
    assert "19" in reason and "00000000" in reason, "the unread cards are named, not only counted"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_few_unread_cards_leave_the_rest_judged():
    """The other side: up to a quarter unread, the cards that were read still decide."""
    verdict, reason = _drive(_Platform(open_cards=20, broken=5))
    assert verdict == "passed", (verdict, reason)
    verdict, reason = _drive(_Platform(open_cards=20))
    assert verdict == "passed", (verdict, reason)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_hole_seen_is_a_hole_however_many_were_unread():
    verdict, reason = _drive(_Platform(open_cards=20, broken=19, holed=True))
    assert verdict == "failed", (verdict, reason)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_list_that_never_ended_is_not_read_as_the_whole_list():
    verdict, reason = _drive(_Platform(open_cards=3, endless=True))
    assert verdict == "inconclusive", (verdict, reason)
    assert "1200" in reason or "1,200" in reason, reason
