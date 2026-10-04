"""The paper-bot trade checks can say "no" before they are trusted to say "yes".

`qa/clonetrades.py` holds the pure parts of the 2026-10-04 verification of our
paper clones' trades (the operator: "did the bots really earn, can their trades
be verified, is it fake or a bug?"); `tests/rest/test_a_paper_bot_trade_says_what_happened.py`
judges live data with them. Each judgement is refuted here, offline, on the
shapes seen live that day, and each is shown to pass the fix that must clear it.
"""

from __future__ import annotations

from qa import clonetrades as ct
from qa.marks import SafetyTier, qa


def _bet(**kw):
    """One settled 5-minute bet as /cloned-bots/{id}/activity serves it."""
    row = {
        "id": "t1", "symbol": "ETH", "side": "buy", "trade_type": "wta",
        "price_at_entry": "2694.010000", "price_at_exit": "2697.010000",
        "profit_usdc": "25.000000", "is_closed": True, "is_winner": True,
        "exit_reason": "epoch_resolved", "resolution_path": "epoch_close",
        "epoch_id": "5967592",
        "epoch_start": "2026-09-24T19:20:00+00:00", "epoch_end": "2026-09-24T19:25:00+00:00",
        "executed_at": "2026-09-24T19:20:44.000000+00:00",
        "closed_at": "2026-09-24T19:25:53.500000+00:00",
    }
    row.update(kw)
    return row


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_only_settled_epoch_bets_are_read():
    rows = [_bet(), _bet(id="t2", trade_type="arena", epoch_end=None),
            _bet(id="t3", is_closed=False, price_at_exit=None), {"id": "junk"}]
    bets = ct.epoch_bets(rows)
    assert [b["id"] for b in bets] == ["t1"]
    assert bets[0]["epoch_end_s"] == 1790277900
    assert bets[0]["closed_s"] == 1790277953


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_exit_from_after_the_epoch_is_caught_and_matched_to_the_close():
    """ETH ep5967592 on 2026-09-24: the epoch ended 19:25:00 at 2694.62
    (Binance), the bet was closed 19:25:53 and its exit is 2697.01 -- the
    market price of that second."""
    bet = ct.epoch_bets([_bet()])[0]
    r = ct.settlement_reading(bet, ref_end=2694.62, ref_closed=2697.01)
    assert r["off_end"] and r["at_closed"]
    assert r["due"] is True and not r["flipped"]   # still up against its own entry


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_outcome_that_the_epoch_end_reverses_is_a_flip():
    """ETH ep5970201 on 2026-10-03: a YES entered at 2687.54, paid on an exit of
    2688.14 (20:50:18), while the price at 20:50:00 was 2687.21 -- below entry."""
    bet = ct.epoch_bets([_bet(price_at_entry="2687.54", price_at_exit="2688.14",
                              epoch_end="2026-10-03T20:50:00+00:00",
                              closed_at="2026-10-03T20:50:18+00:00")])[0]
    r = ct.settlement_reading(bet, ref_end=2687.21, ref_closed=2688.13)
    assert r["off_end"] and r["flipped"] and r["due"] is False


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_fix_settling_at_the_epoch_end_passes():
    """Exit taken at epoch_end, a source a few cents away: nothing to report."""
    bet = ct.epoch_bets([_bet(price_at_exit="2694.63")])[0]
    r = ct.settlement_reading(bet, ref_end=2694.62, ref_closed=2697.01)
    assert not r["off_end"] and not r["flipped"]
    summary = ct.judge_settlement([r])
    assert summary["off_end"] == [] and summary["flipped"] == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_move_inside_the_tolerance_is_not_called_either_way():
    """ETH ep5967590: entry 2689.79 against 2689.77 at the end is 0.0007 % --
    a different price source could put it on either side; no flip is claimed."""
    bet = ct.epoch_bets([_bet(price_at_entry="2689.79", price_at_exit="2689.78",
                              is_winner=True)])[0]
    r = ct.settlement_reading(bet, ref_end=2689.77, ref_closed=2689.77)
    assert r["due"] is None and not r["flipped"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_missing_reference_is_unread_not_a_pass():
    bet = ct.epoch_bets([_bet()])[0]
    r = ct.settlement_reading(bet, ref_end=None, ref_closed=None)
    assert r is None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_pause_reason_on_a_bet_that_ran_to_its_epoch_end_is_caught():
    """MACD Hunter 31d18d91, 2026-10-03: one BTC YES of epoch 5970199, closed
    20:40:05 at the epoch's price, labelled exit_reason stop_loss -- the bot's
    pause, not how the bet ended."""
    rows = [_bet(id="sl", exit_reason="stop_loss", resolution_path=None,
                 epoch_end="2026-10-03T20:40:00+00:00", closed_at="2026-10-03T20:40:05+00:00"),
            _bet(id="ok", exit_reason="epoch_resolved",
                 epoch_end="2026-10-03T20:40:00+00:00", closed_at="2026-10-03T20:40:02+00:00"),
            _bet(id="early", exit_reason="take_profit",
                 epoch_end="2026-10-03T20:40:00+00:00", closed_at="2026-10-03T20:38:00+00:00")]
    flagged = ct.pause_reason_on_full_term(ct.epoch_bets(rows))
    assert [b["id"] for b in flagged] == ["sl"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_clone_deciding_on_another_rule_than_its_description_is_caught():
    """Bollinger Bandit, 2026-10-04: described by its Bollinger Bands, its clone's
    live_decision_source STAT, differs_from_display true."""
    species = {"s1": {"id": "s1", "name": "Bollinger Bandit",
                      "description": "Exploits volatility expansions and contractions using Bollinger Bands.",
                      "primary_indicators": [{"name": "Bollinger_Bands"}, {"name": "Bandwidth"}]}}
    clone = {"id": "c1", "type": "wta_species", "source_id": "s1", "source_name": "Bollinger Bandit",
             "live_decision_source": {"strategy_symbol": "STAT",
                                      "label": "Epoch-number parity heuristic (streak continuation or reversion)",
                                      "differs_from_display": True}}
    found = ct.decision_source_contradictions([clone], species)
    assert len(found) == 1 and found[0]["named"] == ["Bollinger"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_fixes_clear_the_decision_source_check():
    """Either the clone decides on its species' own strategy, or the species is
    described by what its clone actually decides on."""
    species = {"s1": {"id": "s1", "name": "Bollinger Bandit",
                      "description": "Exploits volatility using Bollinger Bands.",
                      "primary_indicators": [{"name": "Bollinger_Bands"}]}}
    own = {"id": "c1", "type": "wta_species", "source_id": "s1",
           "live_decision_source": {"strategy_symbol": "BOLL", "label": "Bollinger Bands",
                                    "differs_from_display": False}}
    assert ct.decision_source_contradictions([own], species) == []
    redescribed = {"s1": dict(species["s1"], description="Bets on epoch-number parity.",
                              primary_indicators=[])}
    other = dict(own, live_decision_source={"strategy_symbol": "STAT", "label": "parity",
                                            "differs_from_display": True})
    assert ct.decision_source_contradictions([other], redescribed) == []
    # no field, nothing claimed (Perceptron Oracle's clone carried null)
    assert ct.decision_source_contradictions([dict(own, live_decision_source=None)], species) == []
