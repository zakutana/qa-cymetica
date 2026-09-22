"""Which case a vendor check judges -- driven whole, offline, on stub clients.

Three checks written on 2026-09-21 were each one line away from a false pass,
and every one of the three was the same shape: the check judged a case, not
THE case its report is about (R03, R09, R10 and the audit's A01-A03, deep pass
of 2026-09-21). A helper test would not have seen it: the subject is chosen
inside the test function, so the whole function is what runs here, with the
network replaced by stubs.

Not in test_pipeline_check_quality.py: that file judges each reconciliation
claim against a captured source, one parametrised rule at a time; these are
decisions made in Python inside a single check, with no capture to read.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from qa.marks import Inconclusive, SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _load(relative: str, name: str):
    spec = importlib.util.spec_from_file_location(name, REPO / relative)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class _Response:
    def __init__(self, status: int, body):
        self.status_code, self._body = status, body

    def json(self):
        return self._body


class _Rest:
    """GET only, answered from a map of path -> (status, body)."""

    def __init__(self, answers: dict):
        self.answers, self.asked = answers, []

    def get(self, path, **_):
        self.asked.append(path)
        status, body = self.answers.get(path, (404, {}))
        return _Response(status, body)


# --------------------------------------------------------------- #117 -------

A, B = "a4a5b71e-de11-4805-b8a3-ed9c3f8f8161", "b0b0b0b0-0000-4000-8000-000000000001"


def _buy(trade_id, card, at, status, outcome):
    return [{"id": trade_id, "type": "intent", "card_id": card, "usdc": 1000.0,
             "at": f"2026-09-21T{at}+00:00"},
            {"id": trade_id, "type": "outcome", "http_status": status,
             "outcome": outcome, "response": "Buy failed" if status >= 500 else ""}]


def _card(tradeable: bool):
    return (200, {"status": "live", "tradeable_now": tradeable,
                  "trading_blocked_reason": None if tradeable else "market closed",
                  "basket": []})


def _run_buy_check(monkeypatch, rows, cards):
    check = _load("tests/rest/test_a_tradeable_card_takes_a_paper_buy.py",
                  "paper_buy_check_under_test")
    monkeypatch.setattr(check, "_paper", lambda: type("P", (), {
        "load": staticmethod(lambda: rows)})())
    rest = _Rest({f"/api/v1/event-cards/{card}": answer
                  for card, answer in cards.items()})
    check.test_a_card_that_reads_tradeable_now_takes_a_paper_buy(rest)
    return rest


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_card_that_failed_and_was_never_tried_again_still_fails_117(monkeypatch):
    """A01, deep pass of 2026-09-21 (3/3). After R03 the subject was the card
    of the NEWEST 5xx buy, so card A answering 500, card B answering 500, and
    B then accepted, passed #117 with A never tried again -- against the
    docstring's own "a card nobody tries again stays failed". Every card whose
    newest buy is a 5xx is judged."""
    rows = (_buy("TRD-1", A, "17:01:28", 500, "unknown")
            + _buy("TRD-2", B, "17:05:00", 500, "unknown")
            + _buy("TRD-3", B, "17:09:00", 200, "accepted"))
    with pytest.raises(AssertionError, match=A):
        _run_buy_check(monkeypatch, rows, {A: _card(True), B: _card(True)})

    # A buy of A itself that lands is the fix.
    fixed = rows + _buy("TRD-4", A, "17:20:00", 200, "accepted")
    _run_buy_check(monkeypatch, fixed, {A: _card(True), B: _card(True)})

    # A card that no longer reads tradeable cannot show the defect or its fix.
    with pytest.raises(Inconclusive):
        _run_buy_check(monkeypatch, rows, {A: _card(False), B: _card(True)})

    # A card that cannot be read is unmeasured (rule 8), never a pass.
    with pytest.raises(Inconclusive):
        _run_buy_check(monkeypatch, rows, {A: (503, {}), B: _card(True)})

    # A stated refusal on the failed card is the gate working, not the fix.
    refused = rows + _buy("TRD-5", A, "17:30:00", 400, "refused")
    with pytest.raises(Inconclusive):
        _run_buy_check(monkeypatch, refused, {A: _card(True), B: _card(True)})


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_buy_is_judged_by_what_the_card_said_when_it_was_placed_117(
        monkeypatch):
    """A03, deep pass of 2026-09-22: the contract is tradeable_now AT the
    buy, and the check could only read it today. paper.py now records the
    card's own gate in the intent; a 5xx on a card that read NOT tradeable
    then is the gate's business, however it reads now, and one that read
    tradeable then fails even if it has since shut."""
    shut_then = _buy("TRD-1", A, "17:01:28", 500, "unknown")
    shut_then[0]["card_before"] = {"tradeable_now": False,
                                   "trading_blocked_reason": "market closed"}
    with pytest.raises(Inconclusive):
        _run_buy_check(monkeypatch, shut_then, {A: _card(True)})

    open_then = _buy("TRD-1", A, "17:01:28", 500, "unknown")
    open_then[0]["card_before"] = {"tradeable_now": True,
                                   "trading_blocked_reason": None}
    with pytest.raises(AssertionError, match=A):
        _run_buy_check(monkeypatch, open_then, {A: _card(False)})


# --------------------------------------------------------------- #116 -------

class _Mcp:
    def __init__(self, methodology: str, inception: str, ret: float = -19.05):
        self.methodology, self.inception, self.ret = methodology, inception, ret

    def call(self, name, args):
        if name == "get_fund_methodology":
            return {"result": {"methodology": {"returns": self.methodology}}}
        return {"result": {"fund": {"inception_date": self.inception,
                                    "return_since_inception_pct": self.ret,
                                    "last_composition_change": "2026-08-17"}}}


HISTORY = {"/api/v1/fta-fund/history": (200, {
    "inception": "2026-08-09",
    "points": [{"t": "2026-08-21", "v": 100.0}, {"t": "2026-09-20", "v": 119.05}]})}


def _run_fta_check(methodology: str, inception: str = "2026-07-26"):
    check = _load("tests/mcp/test_fta_crypto_return_starts_where_its_record_does.py",
                  "fta_check_under_test")
    check.test_the_fta_crypto_return_starts_where_its_own_record_does(
        _Mcp(methodology, inception), _Rest(HISTORY))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_denial_of_a_pro_forma_stretch_is_not_a_disclosure_of_one_116():
    """A03, deep pass of 2026-09-21 (3/3). R09 made the fix a DISCLOSURE, and
    a regex looked for "pro forma" anywhere: "nothing backfilled, no
    pro-forma, no backtest" denies the stretch and was read as disclosing it,
    so the rewording passed with the return still starting 14 days early."""
    with pytest.raises(AssertionError, match="discloses no pro-forma"):
        _run_fta_check("Return is measured since the fund's own inception from "
                       "real market prices -- nothing backfilled, no pro-forma, "
                       "no backtest.")
    with pytest.raises(AssertionError, match="discloses no pro-forma"):
        _run_fta_check("Returns are never pro forma: nothing backfilled.")
    # A02, deep pass of 2026-09-22: "nothing" was not a negation, so the
    # denial their page could write next passed as a disclosure.
    with pytest.raises(AssertionError, match="discloses no pro-forma"):
        _run_fta_check("Measured since inception: nothing backfilled or "
                       "pro-forma.")
    with pytest.raises(AssertionError, match="discloses no pro-forma"):
        _run_fta_check("Neither backfilled nor pro-forma.")

    _run_fta_check("Return since inception includes a pro-forma period before "
                   "the first held position: today's composition applied to "
                   "past closes.")
    # A negation in the sentence before is not a denial of this one.
    _run_fta_check("No backfill. Pro-forma: the stretch before the first "
                   "position applies today's composition to past closes.")

    with pytest.raises(Inconclusive):
        _run_fta_check("")


# ------------------------------------------------- a refused clone says why -

PCPN, RSI = "23441934-8475-4aa0-bbff-75c03ecd3284", "70a47f2a-e1d5-40dc-9c01-bd9b9a2d3c80"
AGAIN = {"detail": "Invalid clone request. Please try again."}
OPENAPI_CLONE = (200, {"paths": {"/api/v1/cloned-bots/clone": {"post": {
    "responses": {"200": {}, "422": {}}}}}})


def _cloned(clone_id, source, at, status, outcome):
    return [{"id": clone_id, "type": "intent", "source_type": "wta_species",
             "source_id": source, "paper": True, "at": f"2026-09-22T{at}+00:00"},
            {"id": clone_id, "type": "outcome", "http_status": status,
             "outcome": outcome, "evidence_id": f"ev-{clone_id}",
             # What the record said until 2026-09-22 -- never read: the check
             # takes the body from the capture.
             "response": "{}"}]


def _run_clone_check(monkeypatch, rows, bodies):
    check = _load("tests/rest/test_a_refused_clone_says_why.py",
                  "refused_clone_check_under_test")
    monkeypatch.setattr(check, "_clones", lambda: type("C", (), {
        "load": staticmethod(lambda: rows)})())
    monkeypatch.setattr(check, "their_body",
                        lambda attempt: bodies.get(attempt["id"]))
    check.test_a_refused_paper_clone_says_why(
        _Rest({"/openapi-public.json": OPENAPI_CLONE}))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_clone_refusal_that_asks_for_the_retry_it_refuses_fails(monkeypatch):
    """CLN-0017 and CLN-0020: the same paper clone, refused twice with "Please
    try again". Judged per source by its newest attempt -- the #117 lesson: a
    different species cloned afterwards is not the fix -- and on their body
    from the capture, never on our record's `response`, which read `{}`."""
    rows = (_cloned("CLN-0017", PCPN, "13:39:02", 400, "rejected")
            + _cloned("CLN-0014", RSI, "13:39:30", 200, "accepted")
            + _cloned("CLN-0020", PCPN, "17:47:14", 400, "rejected"))
    twice = {"CLN-0017": AGAIN, "CLN-0020": AGAIN}
    with pytest.raises(AssertionError, match="Please try again"):
        _run_clone_check(monkeypatch, rows, twice)
    # Another species cloned AFTER it is not the fix.
    later = rows + _cloned("CLN-0021", RSI, "18:00:00", 200, "accepted")
    with pytest.raises(AssertionError, match=PCPN):
        _run_clone_check(monkeypatch, later, twice)

    # Refused once, never retried: the advice has not been tested.
    with pytest.raises(Inconclusive):
        _run_clone_check(monkeypatch, rows[:4], {"CLN-0017": AGAIN})

    # A capture that cannot be read is unmeasured, not an empty body.
    with pytest.raises(Inconclusive):
        _run_clone_check(monkeypatch, rows, {"CLN-0017": AGAIN})

    # A refusal with nothing in it fails on its own.
    with pytest.raises(AssertionError, match="no detail"):
        _run_clone_check(monkeypatch, rows, {"CLN-0017": AGAIN, "CLN-0020": {}})

    # The fixes: the clone is made, or the refusal names its reason.
    made = rows + _cloned("CLN-0030", PCPN, "18:30:00", 200, "accepted")
    _run_clone_check(monkeypatch, made, twice)
    named = rows + _cloned("CLN-0031", PCPN, "18:40:00", 409, "rejected")
    _run_clone_check(monkeypatch, named, {**twice, "CLN-0031": {
        "detail": "You already hold a paper clone of this species."}})
