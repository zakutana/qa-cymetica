"""Two card rules we fitted ourselves, judged only on cards created after they were written.

2026-10-03, the laboratory's look at 27 307 settled event cards (new generation, from 2026-09-03): the badges
(sentiment, impact) predicted nothing, while the basket's asset mix held across both halves -- stock-only
cards drifted down (index -0.35 % and -0.55 % over 72 h), cards with a crypto leg drifted up (+0.3 % and
+0.9 %). A pattern we fit on data we have seen is only a hypothesis (NEXT.md, V3: "a pattern we fit gets a
date and is judged only on data after it"), so `qa/card_rules.py` fixes the two rules, the date and the
criterion BEFORE any of those cards settle:

* short every card whose basket is only stocks; long every card with at least one crypto leg;
* only cards created on or after 2026-10-04 (the day after the rules were written);
* PASS only with at least MIN_CARDS cards and a lower 95 % bound of the mean side-return above zero;
  fewer cards is NOT ENOUGH, never a pass or a fail. Paper has no costs (TRD-0086/0087 round-tripped
  exactly), so a pass is an upper bound on what an account would make.

A card with no index, no base or no basket is unread and counted as such, never a zero return.
"""

from __future__ import annotations

from qa import card_rules as cr
from qa.marks import SafetyTier, qa


def _card(created, ret_pct, types, cid=None, base=100.0):
    return {"id": cid or f"c-{created}-{ret_pct}-{'-'.join(types)}", "created_at": created,
            "status": "settled", "index_base": base, "current_index": base * (1 + ret_pct / 100.0),
            "basket": [{"asset_type": t} for t in types]}


def _case_the_rules_and_their_date_are_fixed_before_the_data():
    assert cr.FROM == "2026-10-04T00:00:00+00:00"
    assert set(cr.RULES) == {"short_stock_only", "long_with_crypto"}
    assert cr.RULES["short_stock_only"]["side"] == -1 and cr.RULES["long_with_crypto"]["side"] == 1
    assert cr.MIN_CARDS >= 100


def _case_a_card_belongs_to_one_rule_by_its_basket():
    assert cr.rule_of(_card("2026-10-05T00:00:00+00:00", 0, ["stock", "stock"])) == "short_stock_only"
    assert cr.rule_of(_card("2026-10-05T00:00:00+00:00", 0, ["stock", "crypto"])) == "long_with_crypto"
    assert cr.rule_of(_card("2026-10-05T00:00:00+00:00", 0, ["crypto"])) == "long_with_crypto"
    assert cr.rule_of(_card("2026-10-05T00:00:00+00:00", 0, ["etf"])) is None
    assert cr.rule_of({"basket": []}) is None


def _case_only_cards_created_after_the_rules_were_written_are_judged():
    cards = [_card("2026-10-03T23:59:59+00:00", -5, ["stock"]),      # the day the rule was fitted: out
             _card("2026-09-20T00:00:00+00:00", -5, ["stock"]),      # the sample it was fitted on: out
             _card("2026-10-04T00:00:00+00:00", -1, ["stock"])]
    said = cr.evaluate(cards)
    assert said["short_stock_only"]["n"] == 1
    assert said["short_stock_only"]["excluded_before"] == 2


def _case_the_side_return_is_the_index_return_signed_by_the_rule():
    cards = [_card("2026-10-05T00:00:00+00:00", -2.0, ["stock"]),
             _card("2026-10-05T01:00:00+00:00", 3.0, ["crypto", "stock"])]
    said = cr.evaluate(cards)
    assert abs(said["short_stock_only"]["mean_pct"] - 2.0) < 1e-9      # a fall is a gain for the short
    assert abs(said["long_with_crypto"]["mean_pct"] - 3.0) < 1e-9


def _case_too_few_cards_is_not_enough_never_a_pass_or_a_fail():
    cards = [_card(f"2026-10-05T00:{i:02d}:00+00:00", -1.0, ["stock"]) for i in range(10)]
    assert cr.evaluate(cards)["short_stock_only"]["verdict"] == "not enough"
    assert cr.evaluate([])["long_with_crypto"]["verdict"] == "not enough"


def _case_a_pass_needs_the_lower_bound_above_zero_not_just_a_positive_mean():
    n = cr.MIN_CARDS
    steady = [_card(f"2026-10-05T{i // 60:02d}:{i % 60:02d}:00+00:00", -0.5, ["stock"], cid=f"s{i}") for i in range(n)]
    assert cr.evaluate(steady)["short_stock_only"]["verdict"] == "pass"
    # Same mean, but swinging +-20 %: the bound straddles zero, so it is not a pass.
    noisy = [_card(f"2026-10-05T{i // 60:02d}:{i % 60:02d}:00+00:00", (-20.5 if i % 2 else 19.5), ["stock"],
                   cid=f"n{i}") for i in range(n)]
    said = cr.evaluate(noisy)["short_stock_only"]
    assert said["mean_pct"] > 0 and said["verdict"] == "inconclusive", said
    # A clear loss is a fail.
    losing = [_card(f"2026-10-05T{i // 60:02d}:{i % 60:02d}:00+00:00", 0.6, ["stock"], cid=f"l{i}") for i in range(n)]
    assert cr.evaluate(losing)["short_stock_only"]["verdict"] == "fail"


def _case_a_card_with_nothing_to_read_is_unread_never_a_zero_return():
    broken = [{"id": "x1", "created_at": "2026-10-05T00:00:00+00:00", "basket": [{"asset_type": "stock"}],
               "current_index": None, "index_base": 100.0},
              {"id": "x2", "created_at": "2026-10-05T00:00:00+00:00", "basket": [{"asset_type": "stock"}],
               "current_index": 101.0, "index_base": 0},
              {"id": "x3", "created_at": "2026-10-05T00:00:00+00:00", "basket": [{"asset_type": "stock"}]}]
    said = cr.evaluate(broken)["short_stock_only"]
    assert said["n"] == 0 and said["unread"] == 3
    assert said["mean_pct"] is None


def _case_a_card_counted_twice_by_the_listing_is_judged_once():
    one = _card("2026-10-05T00:00:00+00:00", -1.0, ["stock"], cid="same")
    assert cr.evaluate([one, dict(one)])["short_stock_only"]["n"] == 1


def _case_a_settled_card_is_judged_at_its_resolution_not_after():
    """2026-10-10: their settled cards keep moving after resolution_at_utc (6fb50de3 100.42 at
    resolution, 203.16 shown), and this test read the shown figure: short_stock_only at a
    -98 % median on six cards, four of them one basket doubled by a stale OTC leg."""
    card = dict(_card("2026-10-05T09:06:53+00:00", 103.16, ["stock"], cid="6fb50de3"),
                contract_spec={"resolution_at_utc": "2026-10-08T09:06:53+00:00"})
    points = [{"t": "2026-10-08T08:59:33+00:00", "index": 100.42},
              {"t": "2026-10-09T11:59:14+00:00", "index": 203.23}]
    assert cr.index_at_resolution(card, points) == 100.42
    assert cr.index_at_resolution(card, points[1:]) is None, "no point at or before resolution"
    assert cr.index_at_resolution(card, [{"t": "2026-10-08T04:00:00+00:00", "index": 100.0}]) is None
    assert abs(cr.index_return_pct(dict(card, index_at_resolution=100.42)) - 0.42) < 1e-9
    said = cr.evaluate([card])["short_stock_only"]
    assert said["n"] == 0 and said["unread"] == 1, (
        "a card with a resolution time and no reading at it was judged on the index shown after")


# Folded on the deep pass of 2026-10-04 (tests/meta grows only by replacement): eight functions became two; every case is a _case_ helper.


def _case_the_card_rules_read_only_what_they_were_fixed_to_read():
    _case_the_rules_and_their_date_are_fixed_before_the_data()
    _case_a_card_belongs_to_one_rule_by_its_basket()
    _case_only_cards_created_after_the_rules_were_written_are_judged()
    _case_the_side_return_is_the_index_return_signed_by_the_rule()
    _case_a_card_with_nothing_to_read_is_unread_never_a_zero_return()
    _case_a_card_counted_twice_by_the_listing_is_judged_once()
    _case_a_settled_card_is_judged_at_its_resolution_not_after()


def _case_a_card_rule_passes_only_on_enough_cards_and_a_bound_above_zero():
    _case_too_few_cards_is_not_enough_never_a_pass_or_a_fail()
    _case_a_pass_needs_the_lower_bound_above_zero_not_just_a_positive_mean()


# Folded on the deep pass of 2026-10-04 (tests/meta grows only by replacement): two functions became one.


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_card_rules_are_fixed_before_the_data_and_judged_only_on_enough_cards():
    _case_the_card_rules_read_only_what_they_were_fixed_to_read()
    _case_a_card_rule_passes_only_on_enough_cards_and_a_bound_above_zero()
