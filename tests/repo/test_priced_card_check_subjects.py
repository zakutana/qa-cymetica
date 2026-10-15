"""Which case the #priceable check judges -- driven whole, offline, on stubs.

T-0005, 2026-10-12: card 8ffd61fa read tradeable_now true and was refused HTTP
400 "Basket is not fully priceable right now" twice, TRD-0113 and TRD-0115. The
check written for it is a sibling of #117's, and the mistake that sibling made
three times is judging a case rather than THE case, so each decision it takes
is asserted here: what is a subject, what is the fix, what is unmeasured.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from qa.marks import Inconclusive, SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
A = "8ffd61fa-f469-45be-a717-a4dcfe9f9508"
B = "b0b0b0b0-0000-4000-8000-000000000002"
UNPRICED = '{"detail": "Basket is not fully priceable right now -- try again shortly"}'
WORDING_0913 = ("{\"detail\": \"This card's price is not currently available. "
                "Its index has not refreshed recently.\"}")


def _check():
    spec = importlib.util.spec_from_file_location(
        "priced_check_under_test",
        REPO / "tests" / "rest" / "test_a_tradeable_card_can_be_priced.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    # The refusals below are stamped 2026-10-12; the check reads them as of that evening, so its
    # 48 h age bound (R01, deep pass 2026-10-15) judges them as the day they happened.
    from datetime import datetime, timezone
    mod.NOW = lambda: datetime(2026, 10, 12, 20, 0, tzinfo=timezone.utc)
    return mod


class _Response:
    def __init__(self, status, body):
        self.status_code, self._body = status, body

    def json(self):
        return self._body


class _Rest:
    def __init__(self, answers):
        self.answers = answers

    def get(self, path, **_):
        status, body = self.answers.get(path, (404, {}))
        return _Response(status, body)


def _gate(tradeable=True, reason=None):
    return {"http_status": 200, "status": "live", "tradeable_now": tradeable,
            "trading_blocked_reason": reason}


def _buy(trade_id, card, at, status, outcome, response="", gate="default"):
    intent = {"id": trade_id, "type": "intent", "card_id": card, "usdc": 593.63,
              "at": f"2026-10-12T{at}+00:00"}
    if gate == "default":
        intent["card_before"] = _gate()
    elif gate is not None:
        intent["card_before"] = gate
    return [intent, {"id": trade_id, "type": "outcome", "http_status": status,
                     "outcome": outcome, "response": response}]


def _card(tradeable=True):
    return (200, {"status": "live", "tradeable_now": tradeable,
                  "trading_blocked_reason": None if tradeable else "closed",
                  "basket": [{"symbol": "ARB", "weight": 0.5}]})


def _run(monkeypatch, rows, cards, now=None):
    check = _check()
    if now is not None:
        check.NOW = lambda: now
    monkeypatch.setattr(check, "_paper", lambda: type("P", (), {
        "load": staticmethod(lambda: rows)})())
    rest = _Rest({f"/api/v1/event-cards/{c}": a for c, a in cards.items()})
    check.test_a_card_that_reads_tradeable_now_can_be_priced(rest)


STRUCK = (_buy("TRD-1", A, "16:25:40", 400, "unknown", UNPRICED)
          + _buy("TRD-2", A, "16:48:13", 400, "unknown", UNPRICED))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_card_refused_as_unpriceable_while_tradeable_fails(monkeypatch):
    with pytest.raises(AssertionError, match=A):
        _run(monkeypatch, STRUCK, {A: _card(True)})


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_refusal_older_than_its_age_bound_is_unmeasured_not_a_failure(monkeypatch):
    """R01, deep pass 2026-10-15: today's tradeable_now joined to a refusal days old says nothing
    about now; the same refusal inside the bound still fails."""
    from datetime import datetime, timezone
    with pytest.raises(Inconclusive, match="fresh buy is owed"):
        _run(monkeypatch, STRUCK, {A: _card(True)}, now=datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc))
    with pytest.raises(AssertionError, match=A):
        _run(monkeypatch, STRUCK, {A: _card(True)}, now=datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_buy_that_lands_since_is_the_fix(monkeypatch):
    fixed = STRUCK + _buy("TRD-3", A, "17:10:00", 200, "accepted")
    _run(monkeypatch, fixed, {A: _card(True)})


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_another_cards_accepted_buy_is_not_the_fix(monkeypatch):
    rows = STRUCK + _buy("TRD-3", B, "17:10:00", 200, "accepted")
    with pytest.raises(AssertionError, match=A):
        _run(monkeypatch, rows, {A: _card(True), B: _card(True)})


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_card_no_longer_tradeable_or_unreadable_is_unmeasured(monkeypatch):
    with pytest.raises(Inconclusive):
        _run(monkeypatch, STRUCK, {A: _card(False)})
    with pytest.raises(Inconclusive):
        _run(monkeypatch, STRUCK, {A: (503, {})})


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_refusal_that_was_not_about_pricing_is_no_subject(monkeypatch):
    rows = (_buy("TRD-1", A, "10:00:00", 400, "unknown", '{"detail": "Event Card not found"}')
            + _buy("TRD-2", A, "10:05:00", 409, "unknown", UNPRICED)
            + _buy("TRD-3", A, "10:10:00", 500, "unknown", "Buy failed"))
    with pytest.raises(Inconclusive):
        _run(monkeypatch, rows, {A: _card(True)})


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_refusal_the_card_did_not_promise_against_is_no_subject(monkeypatch):
    """A card that read false at the buy, one that read true with a reason, and
    a buy from before the gate was recorded (TRD-0007, 2026-09-13) say nothing
    about the contract's `true`."""
    rows = (_buy("TRD-1", A, "10:00:00", 400, "unknown", UNPRICED, gate=_gate(False, "closed"))
            + _buy("TRD-2", A, "10:05:00", 400, "unknown", UNPRICED, gate=_gate(True, "stale"))
            + _buy("TRD-3", A, "10:10:00", 400, "unknown", WORDING_0913, gate=None))
    with pytest.raises(Inconclusive):
        _run(monkeypatch, rows, {A: _card(True)})


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_earlier_wording_of_the_refusal_is_a_subject_when_the_gate_was_read(monkeypatch):
    rows = _buy("TRD-1", A, "10:00:00", 400, "unknown", WORDING_0913)
    with pytest.raises(AssertionError, match=A):
        _run(monkeypatch, rows, {A: _card(True)})
