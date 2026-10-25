"""The /movers check reads the listing whole by the listing's own total (deep pass 2026-10-25, B01).

81185fc1 re-pointed the check at /api/v1/event-cards/movers, the request the page makes. From then on
the listing was paged only up to the `total` that /movers states -- the endpoint under test -- and the
0.95 completeness guard was held to that same number; the listing's own `total` was never read. So
/movers saying 600 of a listing of 647 left 47 cards unread, and a true top-ten card among them passed
unseen. Three readers reproduced it. These drive the whole check over a stubbed site.
"""

import importlib.util
from pathlib import Path

import pytest

from qa.marks import Inconclusive, SafetyTier, qa
from tests.rest.test_movers_page_ranks_every_card import boards

REPO = Path(__file__).resolve().parent.parent.parent
SELF = qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")


def _check():
    spec = importlib.util.spec_from_file_location(
        "movers_listing_total_under_test", REPO / "tests" / "rest" / "test_movers_page_ranks_every_card.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    mod.PAUSE_S = 0
    mod.PAGE_SIZE = 10  # 25 cards over three pages, so where the paging stops matters
    return mod


class _Response:
    def __init__(self, status, body, text=""):
        self.status_code, self._body, self.text = status, body, text

    def json(self):
        return self._body


def _card(i, cur, base="100.0"):
    return {"id": f"c{i}", "title": f"card {i}", "index_base": base, "current_index": str(cur)}


# Cards 0-19 move -12 % .. +7 %. Of 20-24 only c22 moves (-50 %, the biggest loser of all); the other
# four have no base, so they have no move and are ranked nowhere.
LISTING = [_card(i, 100 + (i - 12) * 1.0) for i in range(20)] + [
    _card(20, 5, base="0"), _card(21, 5, base="0"), _card(22, 50.0), _card(23, 5, base="0"), _card(24, 5, base="0")]


class _Site:
    def __init__(self, check, movers, listing, listing_total):
        self.check, self.movers, self.listing, self.listing_total = check, movers, listing, listing_total

    def get(self, path, params=None, headers=None):
        params = params or {}
        if path == self.check.PAGE:
            board = ("var el = document.getElementById('pm-gainers'); function load() { "
                     "fetch('/api/v1/event-cards/movers?limit=10', { credentials: 'same-origin' }); }")
            return _Response(200, None, f"<html><script>{board}</script></html>")
        if path == "/api/v1/event-cards/movers":
            return _Response(200, self.movers)
        if path == self.check.LISTING and str(params.get("limit")) == "500":
            return _Response(422, {"detail": "limit"})
        if path == self.check.LISTING:
            start = int(params.get("offset") or 0)
            return _Response(200, {"cards": self.listing[start:start + int(params["limit"])],
                                   "total": self.listing_total})
        return _Response(404, {})


def _movers(cards, total):
    """The /movers answer for a ranking over `cards`, stating `total`: whole card rows, as it serves them."""
    by_id = {c["id"]: c for c in cards}
    ranked = boards(cards)
    return {"total": total, "ranked": total, "gainers": [by_id[r["id"]] for r in ranked["gainers"]],
            "losers": [by_id[r["id"]] for r in ranked["losers"]], "most_active": []}


def _run(check, site):
    check.test_the_movers_boards_rank_every_card_of_the_listing(site)


@SELF
def test_a_top_card_past_the_total_movers_states_is_read_and_fails():
    """/movers ranks the first 20 and says 20; the listing says 25. The biggest loser of all is card 22."""
    check = _check()
    site = _Site(check, _movers(LISTING[:20], 20), LISTING, 25)
    with pytest.raises(AssertionError, match="1 of the 10 biggest losers"):
        _run(check, site)


@SELF
def test_a_listing_read_short_of_its_own_total_is_inconclusive():
    """The listing says 25 and answers 20: read short of its own total, whatever /movers says."""
    check = _check()
    site = _Site(check, _movers(LISTING[:20], 20), LISTING[:20], 25)
    with pytest.raises(Inconclusive, match="read 20 of the 25"):
        _run(check, site)


@SELF
def test_boards_drawn_from_the_whole_listing_pass():
    check = _check()
    site = _Site(check, _movers(LISTING, 25), LISTING, 25)
    try:  # an Inconclusive would skip this test instead of failing it
        _run(check, site)
    except Inconclusive as exc:
        raise AssertionError(f"inconclusive where a pass was due: {exc}") from exc
