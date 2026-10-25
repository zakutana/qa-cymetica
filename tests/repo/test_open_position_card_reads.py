"""The open-position check: only a 404 is a card that is gone; any other failed read is unread (C06).

Deep pass 2026-10-25 (3 of 3), on the check repaired the same day (f0f1a37c): its docstring says a
position whose card_id 404s points at a card that stopped existing, and a read that fails is unread.
The code put every non-200 card read -- a 503, a 429 after the client's retry, a 403 -- into
`unresolved`, and the check FAILED "no longer resolve" on a read that failed. The existing unread cap
(more than a quarter unread is no sample) now applies to those reads too.
"""

import contextvars

import pytest

from qa.marks import Inconclusive, SafetyTier, qa
from tests.rest import test_build_recipes as check

SELF = qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")


class _Answer:
    def __init__(self, status, body):
        self.status_code, self._body = status, body

    def json(self):
        return self._body


class _Rest:
    def __init__(self, answers):
        self.answers = answers

    def get(self, path, **_):
        return _Answer(*self.answers.get(path, (404, {"detail": "Not Found"})))


def _run(open_cards: dict):
    """The check over open positions in `open_cards` (card id -> the status its read answers)."""
    rows = [{"card_id": c, "status": "open"} for c in open_cards]
    answers = {check.POSITIONS: (200, {"positions": rows}),
               **{check.CARD.format(card_id=c): (s, {"id": c}) for c, s in open_cards.items()}}
    return contextvars.copy_context().run(check.test_every_card_we_hold_a_position_in_still_resolves,
                                          _Rest(answers))


@SELF
@pytest.mark.parametrize("status", [503, 429, 403, 500])
def test_a_card_read_that_fails_is_unread_not_gone(status):
    with pytest.raises(Inconclusive, match=f"HTTP {status}"):
        _run({"a": status})  # one card, unread: more than a quarter of the sample


@SELF
def test_one_failed_read_among_many_is_named_and_does_not_fail():
    try:  # an Inconclusive would skip this test instead of failing it
        _run({"a": 200, "b": 200, "c": 200, "d": 200, "e": 503})
    except Inconclusive as exc:
        raise AssertionError(f"inconclusive where a pass was due: {exc}") from exc


@SELF
def test_a_404_is_still_a_card_that_is_gone():
    with pytest.raises(AssertionError, match="no longer resolve"):
        _run({"a": 200, "gone": 404})
    with pytest.raises(AssertionError, match="gone"):
        _run({"a": 200, "b": 503, "gone": 404})  # a gone card fails, whatever else was unread
