"""Readings of the Gem Screener checks that must hold when their fix lands (2026-11-04). No network."""

from __future__ import annotations

from qa.marks import SafetyTier, qa
from tests.rest.test_gem_screener_says_only_what_is_true import incomplete_sentence_is_unguarded, unit_is_of_circulating


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_unit_that_names_another_denominator_is_not_of_circulating():
    filed = "% of circulating supply"       # #273 as filed: the same word for two denominators
    fixed = "% of the supply unlocked today on DefiLlama's schedule (next_unlock.pct_of_circ is of CoinGecko circulating)"
    assert unit_is_of_circulating(filed) is True
    assert unit_is_of_circulating(fixed) is False
    assert unit_is_of_circulating(None) is False


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_pie_slice_renamed_to_what_is_not_read_does_not_say_free_to_sell():
    from tests.rest.test_gem_screener_small_words import says_free_to_sell
    assert says_free_to_sell("Free to sell") is True                                   # #286 as filed
    assert says_free_to_sell("Free") is True                                           # a label that claims a float
    assert says_free_to_sell("Not shown locked (vesting or staking not read)") is False  # their fix
    assert says_free_to_sell(None) is True


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_incomplete_prices_sentence_is_a_fault_only_where_nothing_guards_it():
    sentence = "return '<b>Prices of the moment were incomplete at this update</b> (' + live + ' of ' + asked"
    old = "var low = p.lowest_basket || {};\n  " + sentence      # #264 as filed: said whatever the data
    fixed = "var low = p.lowest_basket || {}, live = p.live_coins || 0;\n  if (live < asked) {\n    " + sentence
    assert incomplete_sentence_is_unguarded(old) is True
    assert incomplete_sentence_is_unguarded(fixed) is False
    assert incomplete_sentence_is_unguarded("a page without the sentence") is False
