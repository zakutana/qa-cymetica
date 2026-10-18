"""The reading behind the "VAIX orderbook arbitrage does not use an excluded venue" check (2026-10-13, T-0053).

On 2026-10-12 22:32 UTC `excluded_venues` named base, arbitrum and solana as `price_divergence` while
`arbitrage` bought on base. These cases pin how a leg is read, so a book without either block is not a
defect, a malformed one is unreadable and not clean, and only a leg that is a key of the excluded
set is named.
"""

from qa.marks import SafetyTier, qa
from tests.rest.test_vaix_orderbook_arbitrage_does_not_use_an_excluded_venue import excluded_legs

EXCLUDED = {"base": {"mid": "0.00031077", "divergence_pct": "-83.75", "reason": "price_divergence"},
            "solana": {"mid": "0.000372235", "divergence_pct": "-80.54", "reason": "price_divergence"}}
ARB = {"buy_chain": "base", "sell_chain": "ethereum", "buy_price": "0.00031077",
       "sell_price": "0.00191274", "potential_profit_pct": "514.48"}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_buy_leg_on_an_excluded_chain_is_named_with_its_own_words():
    legs = excluded_legs({"arbitrage": ARB, "excluded_venues": EXCLUDED})
    assert list(legs) == ["buy_chain"]
    assert legs["buy_chain"] == {"chain": "base", "price": "0.00031077", "excluded_mid": "0.00031077",
                                 "divergence_pct": "-83.75", "reason": "price_divergence"}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_both_legs_are_read_when_both_are_excluded():
    arb = dict(ARB, sell_chain="solana", sell_price="0.000372235")
    assert set(excluded_legs({"arbitrage": arb, "excluded_venues": EXCLUDED})) == {"buy_chain", "sell_chain"}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_legs_on_chains_the_book_kept_are_clean():
    arb = dict(ARB, buy_chain="arbitrum")
    assert excluded_legs({"arbitrage": arb, "excluded_venues": {"base": EXCLUDED["base"]}}) == {}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_book_without_an_arbitrage_or_without_exclusions_is_clean_not_unreadable():
    assert excluded_legs({"excluded_venues": EXCLUDED}) == {}
    assert excluded_legs({"arbitrage": None, "excluded_venues": EXCLUDED}) == {}
    assert excluded_legs({"arbitrage": ARB}) == {}
    assert excluded_legs({"arbitrage": ARB, "excluded_venues": {}}) == {}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_book_of_the_wrong_shape_is_unreadable_not_clean():
    assert excluded_legs(None) is None
    assert excluded_legs([]) is None
    assert excluded_legs({"arbitrage": "base", "excluded_venues": EXCLUDED}) is None
    assert excluded_legs({"arbitrage": ARB, "excluded_venues": ["base"]}) is None
    # B08, deep pass 2026-10-15: an arbitrage block whose leg keys are renamed is a book we can no
    # longer read, not a clean one.
    renamed = {"buy_venue": "base", "sell_venue": "ethereum", "buy_price": 1.0, "sell_price": 2.0}
    assert excluded_legs({"arbitrage": renamed, "excluded_venues": EXCLUDED}) is None
    # B05, deep pass 2026-10-18: ONE leg renamed. The guard asked whether ANY leg was readable, so
    # buying on excluded base under a new key read as clean on the strength of the sell leg alone.
    half = {"buy_venue": "base", "sell_chain": "ethereum", "buy_price": 1.0, "sell_price": 2.0}
    assert excluded_legs({"arbitrage": half, "excluded_venues": EXCLUDED}) is None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_excluded_leg_is_named_even_when_the_other_leg_is_unread():
    """The other side of B05: an unread leg withholds "clean", not a defect the read leg shows."""
    half = {"buy_chain": "base", "sell_venue": "ethereum", "buy_price": "0.00031077"}
    assert list(excluded_legs({"arbitrage": half, "excluded_venues": EXCLUDED})) == ["buy_chain"]
