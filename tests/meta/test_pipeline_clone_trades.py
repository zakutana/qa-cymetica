"""The paper-bot trade checks can say "no" before they are trusted to say "yes".

`qa/clonetrades.py` holds the pure parts of the 2026-10-04 verification of our
paper clones' trades (the operator: "did the bots really earn, can their trades
be verified, is it fake or a bug?"); `tests/rest/test_a_paper_bot_trade_says_what_happened.py`
judges live data with them. Each judgement is refuted here, offline, on the
shapes seen live that day, and each is shown to pass the fix that must clear it.
Nine were written and merged to three, one per reading (the tests/meta ceiling).
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


def _one(**kw):
    return ct.epoch_bets([_bet(**kw)])[0]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_bet_is_judged_on_the_price_at_its_epoch_end():
    """Only settled 5-minute bets are read; an exit from after the epoch is caught
    and matched to the close; a reversed result is a flip; the fix passes; a move
    inside the tolerance is called neither way; a missing reference is unread."""
    rows = [_bet(), _bet(id="t2", trade_type="arena", epoch_end=None),
            _bet(id="t3", is_closed=False, price_at_exit=None), {"id": "junk"}]
    bets = ct.epoch_bets(rows)
    assert [b["id"] for b in bets] == ["t1"]
    assert (bets[0]["epoch_end_s"], bets[0]["closed_s"]) == (1790277900, 1790277953)

    # ETH ep5967592, 2026-09-24: ended 19:25:00 at 2694.62 (Binance), closed
    # 19:25:53 at 2697.01 -- the price of that second. Still up against entry.
    r = ct.settlement_reading(bets[0], ref_end=2694.62, ref_closed=2697.01)
    assert r["off_end"] and r["at_closed"] and r["due"] is True and not r["flipped"]

    # ETH ep5970201, 2026-10-03: YES entered at 2687.54, paid on 2688.14 of
    # 20:50:18, while 20:50:00 stood at 2687.21 -- below entry.
    r = ct.settlement_reading(_one(price_at_entry="2687.54", price_at_exit="2688.14",
                                   epoch_end="2026-10-03T20:50:00+00:00",
                                   closed_at="2026-10-03T20:50:18+00:00"),
                              ref_end=2687.21, ref_closed=2688.13)
    assert r["off_end"] and r["flipped"] and r["due"] is False

    # The fix: exit taken at epoch_end, a source a cent away.
    r = ct.settlement_reading(_one(price_at_exit="2694.63"), ref_end=2694.62, ref_closed=2697.01)
    assert not r["off_end"] and not r["flipped"]
    assert ct.judge_settlement([r])["off_end"] == [] and ct.judge_settlement([r])["flipped"] == []

    # ETH ep5967590: 2689.79 against 2689.77 is 0.0007 %; no flip is claimed.
    r = ct.settlement_reading(_one(price_at_entry="2689.79", price_at_exit="2689.78"),
                              ref_end=2689.77, ref_closed=2689.77)
    assert r["due"] is None and not r["flipped"]

    assert ct.settlement_reading(bets[0], ref_end=None, ref_closed=None) is None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_pause_reason_on_a_bet_that_ran_to_its_epoch_end_is_caught():
    """MACD Hunter 31d18d91, 2026-10-03: one BTC YES of epoch 5970199, closed
    20:40:05 at the epoch's price, labelled exit_reason stop_loss -- the bot's
    pause, not how the bet ended. A bet really closed early is not flagged."""
    end = "2026-10-03T20:40:00+00:00"
    rows = [_bet(id="sl", exit_reason="stop_loss", resolution_path=None, epoch_end=end,
                 closed_at="2026-10-03T20:40:05+00:00"),
            _bet(id="ok", epoch_end=end, closed_at="2026-10-03T20:40:02+00:00"),
            _bet(id="early", exit_reason="take_profit", epoch_end=end,
                 closed_at="2026-10-03T20:38:00+00:00")]
    assert [b["id"] for b in ct.pause_reason_on_full_term(ct.epoch_bets(rows))] == ["sl"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_clone_deciding_on_another_rule_than_its_description_is_caught():
    """Bollinger Bandit, 2026-10-04: described by its Bollinger Bands, its clone's
    live_decision_source STAT, differs_from_display true. Cleared by a clone that
    decides on its own strategy, or by a description of what it decides on; a
    clone with no field (Perceptron Oracle's was null) claims nothing."""
    species = {"s1": {"id": "s1", "name": "Bollinger Bandit",
                      "description": "Exploits volatility expansions and contractions using Bollinger Bands.",
                      "primary_indicators": [{"name": "Bollinger_Bands"}, {"name": "Bandwidth"}]}}
    other = {"id": "c1", "type": "wta_species", "source_id": "s1", "source_name": "Bollinger Bandit",
             "live_decision_source": {"strategy_symbol": "STAT",
                                      "label": "Epoch-number parity heuristic (streak continuation or reversion)",
                                      "differs_from_display": True}}
    found = ct.decision_source_contradictions([other], species)
    assert len(found) == 1 and found[0]["named"] == ["Bollinger"]

    own = dict(other, live_decision_source={"strategy_symbol": "BOLL", "label": "Bollinger Bands",
                                            "differs_from_display": False})
    assert ct.decision_source_contradictions([own], species) == []
    redescribed = {"s1": dict(species["s1"], description="Bets on epoch-number parity.",
                              primary_indicators=[])}
    assert ct.decision_source_contradictions([other], redescribed) == []
    # Deep pass 2026-10-05 (T24): the description alone, the indicators left as they were --
    # the case above also empties the indicators, so it cannot tell the two paths apart.
    described_otherwise = {"s1": dict(species["s1"], description="Bets on epoch-number parity.")}
    assert ct.decision_source_contradictions([other], described_otherwise) == []
    assert ct.decision_source_contradictions([dict(other, live_decision_source=None)], species) == []
    # ... and (T14) a population it could not judge is counted as such, never as clean.
    assert ct.decision_source_reads([other, own], species) == 2
    assert ct.decision_source_reads([other], {}) == 0, "clones whose species do not join were read"
    renamed = dict(other, live_decision_source={"strategy_symbol": "STAT", "differs": True})
    assert ct.decision_source_reads([renamed], species) == 0, "a renamed flag was read"
    # Deep pass 2026-10-10, B06: a differing clone whose species carries no readable
    # primary_indicators cannot be held to its description -- it is unread, not judged clean,
    # whatever the other species carry. One that decides on its own rule is still read.
    stripped = {"s1": dict(species["s1"], primary_indicators=[])}
    assert ct.decision_source_reads([other], stripped) == 0, "an unreadable species was judged clean"
    assert ct.decision_source_unread([other], stripped) == ["c1"]
    assert ct.decision_source_reads([own], stripped) == 1 and ct.decision_source_unread([own], stripped) == []
    assert ct.decision_source_unread([other], species) == []
    assert ct.decision_source_contradictions([renamed], species) == []
