"""BOOK: the campaign has to be able to lose.

Their paper balance does not move when a paper position is opened (#87), so
nothing on their side stops an agent deploying 500,000 against a 100,000
bankroll. A campaign that cannot run out of money cannot be measured: a
strategy that would have lost everything looks exactly like one that doubled,
because the only number that ever moves is the count of positions.

So the constraint lives here. `scripts/paper.py` keeps its own book -- what we
started with, what we deployed, what those positions are worth from THEIR
position rows -- and refuses an order the book cannot pay for. That refusal is
the whole reason the campaign means anything, so it gets a test rather than a
comment, and the test is what fails if somebody later makes the cap advisory.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _paper(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    spec = importlib.util.spec_from_file_location(
        "paper_under_test", REPO / "scripts" / "paper.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _trade(mod, trade_id, usdc, position_id="p1"):
    mod._append({"id": trade_id, "type": "intent", "usdc": usdc,
                 "card_id": "c1", "paper": True,
                 "before": {"sim_balance_usdc": "100000.00"}})
    mod._append({"id": trade_id, "type": "outcome", "outcome": "accepted",
                 "position_id": position_id, "http_status": 200})


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_book_counts_what_is_deployed_and_what_it_is_worth(tmp_path, monkeypatch):
    """Equity is cash we have not deployed plus what the positions are worth.

    Both halves matter. Counting only cash would say a fully deployed book is
    broke; counting only positions would ignore what is left to trade with.
    The position values are THEIRS -- current_value_usdc off their own rows --
    so the only thing we contribute is the arithmetic.
    """
    mod = _paper(tmp_path, monkeypatch)
    _trade(mod, "TRD-0001", 6000.0, "p1")
    _trade(mod, "TRD-0002", 4000.0, "p2")

    positions = [
        {"position_id": "p1", "current_value_usdc": 6600.0, "status": "open"},
        {"position_id": "p2", "current_value_usdc": 3500.0, "status": "open"},
    ]
    book = mod.book(positions)

    assert book["deployed"] == 10000.0
    assert book["cash"] == 90000.0, "cash is what has not been committed"
    assert book["value"] == 10100.0
    assert book["equity"] == 100100.0, "up 100 on a 100k bankroll"
    assert book["open"] == 2


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_closed_position_returns_its_money_to_the_book(tmp_path, monkeypatch):
    """A position that is no longer open is no longer deployed.

    Without this the book leaks: every closed trade would keep its notional
    counted as committed forever, and after enough round trips the campaign
    would refuse to trade with a bankroll it still has.
    """
    mod = _paper(tmp_path, monkeypatch)
    _trade(mod, "TRD-0001", 6000.0, "p1")
    positions = [{"position_id": "p1", "current_value_usdc": 6600.0,
                  "status": "closed", "realized_pnl_usdc": 600.0}]

    book = mod.book(positions)
    assert book["deployed"] == 0.0, "a closed position is not deployed capital"
    assert book["cash"] == 100600.0, "the proceeds come back, gain and all"
    assert book["equity"] == 100600.0


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_order_the_book_cannot_pay_for_is_refused(tmp_path, monkeypatch):
    """The refusal that makes the campaign mean something.

    Their side will accept this order -- it accepted every one we have sent,
    and debited nothing. If we accept it too, the campaign has no downside and
    no measurement. `affordable` is the gate, and it is a hard refusal rather
    than a warning because a warning in a loop is a warning nobody reads.
    """
    mod = _paper(tmp_path, monkeypatch)
    _trade(mod, "TRD-0001", 95000.0, "p1")
    positions = [{"position_id": "p1", "current_value_usdc": 95000.0,
                  "status": "open"}]

    ok, why = mod.affordable(6000.0, positions)
    assert ok is False
    assert "5000" in why or "5,000" in why, (
        f"the refusal has to say what is actually left: {why}"
    )

    ok, why = mod.affordable(4999.0, positions)
    assert ok is True, why


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_cap_is_not_advisory(tmp_path, monkeypatch):
    """A later edit that turns the refusal into a print fails here.

    The whole value of the book is that it says no. This reads the source
    rather than the behaviour on purpose: behaviour can be preserved while the
    gate is moved somewhere it never runs.
    """
    source = (REPO / "scripts" / "paper.py").read_text(encoding="utf-8")
    assert "affordable(" in source
    placement = source.index("def buy(")
    tail = source[placement:]
    assert "affordable(" in tail, "buy() no longer consults the book"
    gate = tail.index("affordable(")
    following = tail[gate:gate + 600]
    assert "SystemExit" in following or "raise" in following, (
        "the book's answer must stop the order, not decorate it"
    )
