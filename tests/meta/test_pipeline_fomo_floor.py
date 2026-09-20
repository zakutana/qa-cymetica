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


def _gated(n=12, hot=True):
    """A control the size of a real listing: their Robinhood chain serves the
    gate field on every row of forty. One clean row is not a control, and
    `MIN_CONTROL_ROWS` is what says so."""
    return [_row(f"RH{i}", 200000.0, max_buy=10000.0, hot=hot and i < 3)
            for i in range(n)]


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

    # Per chain, never pooled. Cymetica said on 2026-09-14 that a Robinhood
    # curve reads a single reserve while Solana has only a two-sided pool, so
    # max buy is 0.05 x TVL there and 0.05 x TVL/2 on Solana. A median over
    # the union is neither, and would then be applied to both.
    rh = [_row("RH", 10000.0, max_buy=500.0)] * 3
    sol = [_row("SOL", 10000.0, max_buy=250.0)] * 3
    assert abs(mod.published_ratio(rh) - 0.05) < 1e-9
    assert abs(mod.published_ratio(sol) - 0.025) < 1e-9
    pooled = mod.published_ratio(rh + sol)
    assert pooled != mod.published_ratio(sol), (
        f"pooling gives {pooled}, which is then applied to a chain whose own "
        f"rows say {mod.published_ratio(sol)} -- every solana pool would be "
        f"read as twice the max buy it carries")

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
    gated = mod._chain(_gated(), 0.05)

    # A control of ONE clean row is not a control. With a thin solana token
    # in front of it the answer is still the old, cautious path: one row is
    # not a finding.
    thin_one = mod._chain([_row("CHADSTER", 75.16), _row("OK", 90000.0)], 0.05)
    tiny_control = mod._chain([_row("RH", 200000.0, max_buy=10000.0)], 0.05)
    verdict, reason = mod.decide(thin_one, tiny_control)
    assert verdict == "passed", (verdict, reason)

    # And a row a hair under the floor is serialisation noise, not a breach:
    # $450 of max buy against their $500 is a pool that moved, and two of
    # those must not file anything even against a full control.
    hair = mod._chain([_row("A", 9000.0), _row("B", 9200.0)], 0.05)
    assert mod.decide(hair, gated)[0] == "passed", (
        "the check is firing on rounding, not on a gate that is not running")

    # No control: their gated chain quiet this window.
    quiet = mod._chain(_gated(hot=False), 0.05)
    thin_two = mod._chain([_row("CHADSTER", 75.16), _row("speed", 423.77)], 0.05)
    assert mod.decide(thin_two, quiet)[0] == "inconclusive"

    # Nobody serves the gate at all: mid-deploy, not a finding.
    blind = mod._chain([_row("RH", 200000.0)], None)
    assert mod.decide(thin_two, blind)[0] == "inconclusive"

    # And a quiet market on both sides is a quiet market.
    assert mod.decide(mod._chain([], 0.05), mod._chain([], 0.05))[0] == (
        "inconclusive")

    # The passing sentence must not describe a row it just excused. With one
    # row under the floor and a control too small to file on, the old wording
    # read "every hot row on both chains clears the floor ... the thinnest
    # allowing $4 of max buy against a $500 floor" -- a sentence that refutes
    # itself, and a passing run writes it into detail.reason on a filed row.
    assert "clears the floor" not in reason or "under" not in reason, reason
    thinnest = min(thin_one["thinnest"], tiny_control["thinnest"])
    if thinnest < 500:
        assert "every hot row on both chains clears the floor" not in reason, (
            f"the reason says every row clears a $500 floor while naming "
            f"${thinnest:,.0f} as the thinnest: {reason}")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_figure_quoted_to_them_is_measured_on_the_chain_it_names(
        tmp_path, monkeypatch):
    """One name for two measurements is how a figure is compared with itself.

    `published_ratio` is read per chain and never pooled, because Robinhood
    computes 0.05 x TVL and Solana 0.05 x TVL/2 -- the module says so in those
    words. `_chain(solana_rows, solana_ratio)` judges the breach at Solana's
    ratio, and then every sentence that names the offending pool computed its
    figure with `robinhood["ratio"]`: judged at one number, quoted at another.

    Measured on the shape that reaches it: a Solana pool of $75.16 judged at
    0.025 is $1.88 of max buy and was quoted to the vendor as $3.76 -- twice
    what was measured, on the row filed as #102. Latent until Solana partly
    serves the gate, which is why no fixture caught it: every one of them
    passed 0.05 to both chains, so none could tell the two apart.
    """
    mod = _check()
    solana = mod._chain([_row("CHADSTER", 75.16), _row("SPEED", 423.77),
                         _row("THIN", 900.0)], 0.025)
    robinhood = mod._chain([_row("RH1", 200000.0, max_buy=10000.0),
                            _row("RH2", 300000.0, max_buy=15000.0),
                            _row("RH3", 250000.0, max_buy=12500.0)], 0.05)

    verdict, reason = mod.decide(solana, robinhood)
    assert verdict == "failed", (verdict, reason)
    assert "$1.88" in reason, (
        f"the pool is $75.16 and solana's own ratio is 0.025, so its max buy "
        f"is $1.88; quoting robinhood's 0.05 makes it $3.76, which is twice "
        f"what the breach was judged at: {reason}")
    assert "$3.76" not in reason, reason


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
    # The three that were live in one read at 11:06 CEST: MOON, Zeno and snek,
    # at $1 645, $2 901 and $3 859 of pool. None of them is under a twentieth
    # of the floor, which is what the first version of this check demanded --
    # it passed with these in front of it.
    solana = mod._chain(
        [_row("CHADSTER", 75.16), _row("MOON", 1644.60), _row("Zeno", 2901.15),
         _row("snek", 3859.00), _row("OTC", 620579.53)], 0.05)
    gated = mod._chain(_gated(), 0.05)

    verdict, reason = mod.decide(solana, gated)
    assert verdict == "failed", (verdict, reason)
    assert "solana" in reason and "500" in reason, reason
    assert "served on one chain and not the other" in reason, reason
    # The token is named by ADDRESS: this sentence is quoted into a report
    # that goes to them, a symbol is not unique, and the thinnest row on
    # 2026-09-14 was a memecoin whose chosen name is a racial slur.
    assert "chadster" in reason, reason
    assert "CHADSTER" not in reason, reason

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
    gated = mod._chain(_gated(), 0.05)
    verdict, reason = mod.decide(mod._chain(twice, 0.05), gated)
    assert verdict == "failed", "one token is a finding against a real control"
    assert "1 hot solana token(s)" in reason, (
        f"one coin in two listings was counted as two: {reason}")

    # Without a control that size, one token is not a finding at all.
    tiny = mod._chain([_row("RH", 200000.0, max_buy=10000.0)], 0.05)
    assert mod.decide(mod._chain(twice, 0.05), tiny)[0] == "passed"
