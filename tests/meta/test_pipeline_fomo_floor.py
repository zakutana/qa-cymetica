"""The decision behind the tradeability-floor check, without the network.

The live check is `tests/rest/test_fomo_radar_hot_clears_its_tradeability_
floor.py`. What is unit-tested here is its judgement, because the judgement
rests on a contract Cymetica stated in a Telegram message on 2026-09-14 and on
a unit conversion read off their own rows -- two things that can move without
anyone here noticing.

Their claim: *"a row is only HOT now if it's also TRADEABLE -- its 5%-slippage
max buy (max_buy_5pct_usd) is at least $500 ... an unreadable reserve fails
closed to not-hot ... The raw burst is still on the row as hot_pressure."*

Measured the same morning: their Robinhood rows carry the mechanism and
honour it (thinnest hot row $1 447 of max buy, none `thin`), their Solana rows
carry none of the three fields, and two of twenty hot Solana tokens quoted
pools of $75.16 and $423.77. The check's whole force is that comparison, so
every way it could report without it is pinned here.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _check():
    spec = importlib.util.spec_from_file_location(
        "fomo_floor_check", REPO / "tests" / "rest"
        / "test_fomo_radar_hot_clears_its_tradeability_floor.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _row(symbol, pool, hot=True, max_buy=None, token=None):
    row = {"symbol": symbol, "token_address": token or symbol.lower(),
           "liquidity_usd": pool, "hot": hot}
    if max_buy is not None:
        row["max_buy_5pct_usd"] = max_buy
    return row


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_unit_conversion_comes_off_their_rows_not_off_our_arithmetic():
    """Their floor is stated in max-buy and one chain serves only a pool.

    The bridge is `max_buy_5pct_usd / liquidity_usd`, which was 0.0500 to four
    decimal places on every Robinhood row serving both -- minimum, median and
    maximum alike. Read on every run rather than baked in: if they change how
    a 5% max buy is computed, the comparison follows them instead of quietly
    measuring the wrong thing.
    """
    mod = _check()
    rows = [_row("A", 10000.0, max_buy=500.0), _row("B", 620579.53,
                                                    max_buy=31028.98)]
    # 1e-6, not 1e-9: these are their own rounded figures off a live row, and
    # a tolerance tighter than their serialisation is a test about floats.
    assert abs(mod.published_ratio(rows) - 0.05) < 1e-6

    # No row serves both -> no bridge, and the caller must not invent one.
    assert mod.published_ratio([_row("C", 1000.0)]) is None

    # Their own field wins wherever it is served; the pool is the fallback.
    assert mod.max_buy(_row("D", 1000.0, max_buy=7.0), 0.05) == 7.0
    assert mod.max_buy(_row("E", 1000.0), 0.05) == 50.0
    assert mod.max_buy({"hot": True}, 0.05) is None, (
        "a row we cannot measure is not a row we have caught")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_one_thin_row_is_not_a_finding_and_a_gated_control_is_required():
    """Three ways this check must stay quiet, and each one happened or nearly
    did on 2026-09-14.

    A single thin row mid-index is ordinary in a new-pair feed and a pool can
    drain between their gate and the response being serialised. A read where
    their gated chain returns no hot row has no control. And a read where
    nobody serves the gate field at all cannot measure their floor in the unit
    they stated it in -- that is the feed mid-deploy, which rule 10 says is not
    a defect.
    """
    mod = _check()
    gated = mod._chain([_row("RH", 200000.0, max_buy=10000.0)], 0.05)

    one_thin = mod._chain([_row("CHADSTER", 75.16), _row("OK", 90000.0)], 0.05)
    verdict, reason = mod.decide(one_thin, gated)
    assert verdict == "passed", (verdict, reason)

    # No control: their gated chain quiet this read.
    quiet = mod._chain([_row("RH", 200000.0, max_buy=10000.0, hot=False)], 0.05)
    thin_two = mod._chain([_row("CHADSTER", 75.16), _row("speed", 423.77)], 0.05)
    assert mod.decide(thin_two, quiet)[0] == "inconclusive"

    # Nobody serves the gate at all: mid-deploy, not a finding.
    blind = mod._chain([_row("RH", 200000.0)], None)
    assert mod.decide(thin_two, blind)[0] == "inconclusive"

    # And a quiet market on both sides is a quiet market.
    assert mod.decide(mod._chain([], 0.05), mod._chain([], 0.05))[0] == (
        "inconclusive")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_two_thin_tokens_beside_a_gated_chain_is_the_finding():
    """What we actually read at 08:00 UTC on 2026-09-14, and the sentence it
    has to produce -- naming the chain, the token and both numbers, because a
    report that says "some rows are thin" cannot be acted on.

    And the other shape: if the gated chain breaches too, the floor is not
    running anywhere, which is still a defect and a DIFFERENT sentence. A
    check that reported both as "solana is ungated" would send them looking in
    the wrong place.
    """
    mod = _check()
    solana = mod._chain(
        [_row("CHADSTER", 75.16), _row("$speed", 423.77),
         _row("OTC", 620579.53)], 0.05)
    gated = mod._chain([_row("RH", 200000.0, max_buy=10000.0)], 0.05)

    verdict, reason = mod.decide(solana, gated)
    assert verdict == "failed", (verdict, reason)
    assert "solana" in reason and "CHADSTER" in reason, reason
    assert "75.16" in reason and "500" in reason, reason
    assert "not applied to this chain" in reason, reason

    both = mod._chain([_row("RH1", 75.0, max_buy=3.75),
                       _row("RH2", 420.0, max_buy=21.0)], 0.05)
    verdict, reason = mod.decide(solana, both)
    assert verdict == "failed"
    assert "not running on either chain" in reason, reason
    assert "not applied to this chain" not in reason, (
        "one chain's gap and no gate at all must not read the same")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_token_hot_twice_in_one_read_is_one_breach():
    """The endpoint answers the same token on more than one listing, and
    `MIN_BREACHES` is two DISTINCT tokens. Counting rows instead would let one
    coin appearing in two filters file a finding on its own -- which is how
    the console came to show the same coin twice at +1262.3% on 2026-09-13.
    """
    mod = _check()
    twice = [_row("CHADSTER", 75.16, token="0xchad"),
             _row("CHADSTER", 75.16, token="0xchad")]
    assert len(mod.breaches(twice, 0.05)) == 1
    gated = mod._chain([_row("RH", 200000.0, max_buy=10000.0)], 0.05)
    assert mod.decide(mod._chain(twice, 0.05), gated)[0] == "passed"
