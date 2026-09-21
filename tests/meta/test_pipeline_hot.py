"""qa/hot.py: the Hot headlines study, over synthetic rounds.

A round is what `scripts/hot_watch.py capture` writes every tick: the hot top
100 as `[id, rank, hot, cls, px, ret]` and the wire (the newest 500) as
`[id, s_px, c_px, s_ret, c_ret]`. A headline row carries its baskets once.
Shapes captured live on 2026-09-21 (GET /api/v1/headlines?filter=hot and
?limit=500).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from qa import hot
from qa.marks import SafetyTier, qa

T0 = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)


def _iso(when):
    return when.isoformat(timespec="seconds")


def _headline(hid, crypto=("AAA", "BBB", "CCC"), stock=("XX", "YY"),
              published=T0):
    return {"type": "headline", "id": hid, "at": _iso(published),
            "published_at": _iso(published),
            "crypto_members": list(crypto), "stock_members": list(stock),
            "crypto_fp": hot.basket_fp(crypto, "crypto"),
            "stock_fp": hot.basket_fp(stock, "stocks")}


def _round(when, hot_rows=(), wire=()):
    return {"type": "round", "at": _iso(when), "ok": True,
            "hot": [list(r) for r in hot_rows], "wire": [list(w) for w in wire]}


def _path(hid, start, pxs, every=20, rank=1, in_hot=True):
    """Rounds every `every` min; the row sits in hot (crypto) at each px."""
    out = []
    for i, px in enumerate(pxs):
        when = start + timedelta(minutes=every * i)
        hot_rows = [(hid, rank, 7.0, "crypto", px, 7.0)] if in_hot else []
        out.append(_round(when, hot_rows, [(hid, 10.0, px, 0.1, 7.0)]))
    return out


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_basket_fingerprint_ignores_order_and_names_its_class():
    assert hot.basket_fp(["B", "A"], "crypto") == hot.basket_fp(["A", "B"], "crypto")
    assert hot.basket_fp(["A"], "crypto") != hot.basket_fp(["A"], "stocks")
    assert hot.basket_fp([], "crypto") is None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_entry_fires_once_when_a_covered_round_saw_the_basket_absent():
    heads = [_headline(1)]
    rounds = [_round(T0)] + _path(1, T0 + timedelta(minutes=20), [100, 101, 102])
    found = hot.entries(rounds, heads)
    assert len(found) == 1
    assert found[0]["row"] == 1 and found[0]["px"] == 100
    assert found[0]["at"] == _iso(T0 + timedelta(minutes=20))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_no_entry_after_an_uncovered_gap():
    """Present after a two-hour hole: we do not know when it came in."""
    heads = [_headline(1)]
    rounds = [_round(T0)] + _path(1, T0 + timedelta(hours=2), [100, 101])
    assert hot.entries(rounds, heads) == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_basket_re_entering_within_a_day_is_not_a_second_entry():
    heads = [_headline(1)]
    rounds = ([_round(T0)] + _path(1, T0 + timedelta(minutes=20), [100])
              + [_round(T0 + timedelta(minutes=40))]
              + _path(1, T0 + timedelta(minutes=60), [103]))
    assert len(hot.entries(rounds, heads)) == 1


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_two_rows_on_one_basket_are_one_entry():
    heads = [_headline(1), _headline(2)]
    first = T0 + timedelta(minutes=20)
    rounds = [_round(T0), _round(first, [(1, 1, 7.0, "crypto", 100, 7.0),
                                         (2, 2, 7.0, "crypto", 100, 7.0)])]
    assert len(hot.entries(rounds, heads)) == 1


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_round_whose_hot_read_failed_is_a_gap_not_an_empty_hot_tab():
    """Rule 8: a failed read is not an empty read. Were it one, the round
    after it would call every basket on the tab a fresh entry."""
    heads = [_headline(1)]
    rounds = _path(1, T0, [100])
    rounds.append({"type": "round", "at": _iso(T0 + timedelta(minutes=20)),
                   "ok": False, "hot": None, "wire": []})
    rounds += _path(1, T0 + timedelta(minutes=40), [101])
    assert hot.entries(rounds, heads) == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_forward_return_with_no_round_near_the_horizon_is_unobserved():
    rounds = _path(1, T0, [100, 110])
    assert hot.forward(rounds, 1, "crypto", T0, 100.0, hours=6) is None
    assert hot.forward(rounds, 1, "crypto", T0, 100.0,
                       hours=20 / 60) == 10.0


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_follow_counts_unobserved_apart_from_the_measured():
    heads = [_headline(1)]
    rounds = [_round(T0)] + _path(1, T0 + timedelta(minutes=20), [100, 104])
    said = hot.follow(hot.entries(rounds, heads), rounds, horizons=(20 / 60, 6))
    short, long_ = said["crypto"]
    assert short["n"] == 1 and short["mean"] == 4.0
    # Six hours after entry has not happened yet in this diary: open, not
    # unobserved. Only a horizon the rounds have passed can be missed.
    assert long_["n"] == 0 and long_["unobserved"] == 0 and long_["open"] == 1

    later = rounds + [_round(T0 + timedelta(hours=8))]
    long_ = hot.follow(hot.entries(later, heads), later, horizons=(6,))["crypto"][0]
    assert long_["unobserved"] == 1 and long_["open"] == 0


# NEX-0055, verbatim in the parts that are tested: crypto only, ret_24h >= 6,
# >= 3 members, rank <= 3, published <= 60 min, in Hot <= 30 min; TP +8 %,
# stop -4 %, 24 h time stop; ~0.20 % round trip; N >= 100 before a verdict.

@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_rule_takes_profit_at_the_first_round_past_eight_percent():
    heads = [_headline(1, published=T0)]
    rounds = [_round(T0)] + _path(1, T0 + timedelta(minutes=20),
                                  [100, 103, 109, 95])
    said = hot.nexus_rule(rounds, heads)
    (trade,) = said["trades"]
    assert trade["exit"] == "take_profit"
    assert trade["gross"] == 9.0, "exits at the round it saw, not at the level"
    assert abs(trade["net"] - 8.8) < 1e-9
    assert said["verdict"].startswith("not yet")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_rule_ignores_a_stale_headline_and_a_stock_basket():
    old = _headline(1, published=T0 - timedelta(hours=3))
    rounds = [_round(T0)] + _path(1, T0 + timedelta(minutes=20), [100, 120])
    assert hot.nexus_rule(rounds, [old])["trades"] == []

    fresh = _headline(2, published=T0)
    stock = [_round(T0), _round(T0 + timedelta(minutes=20),
                                [(2, 1, 7.0, "stocks", 50, 7.0)],
                                [(2, 50, 1.0, 7.0, 0.1)])]
    assert hot.nexus_rule(stock, [fresh])["trades"] == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_rule_needs_its_own_threshold_and_rank():
    heads = [_headline(1, published=T0)]
    low = [_round(T0), _round(T0 + timedelta(minutes=20),
                              [(1, 1, 5.0, "crypto", 100, 5.0)],
                              [(1, 10.0, 100, 0.1, 5.0)])]
    assert hot.nexus_rule(low, heads)["trades"] == []
    deep = [_round(T0)] + _path(1, T0 + timedelta(minutes=20), [100, 120], rank=4)
    assert hot.nexus_rule(deep, heads)["trades"] == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_trade_whose_time_stop_was_never_seen_is_open_not_a_result():
    heads = [_headline(1, published=T0)]
    rounds = [_round(T0)] + _path(1, T0 + timedelta(minutes=20), [100, 101])
    said = hot.nexus_rule(rounds, heads)
    assert said["trades"] == []
    assert said["open"] == 1


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_verdict_waits_for_a_hundred_and_then_reads_the_t_stat():
    losers = [{"net": -1.0}] * 60 + [{"net": 0.5}] * 40
    assert hot.rule_verdict(losers[:99])["verdict"].startswith("not yet")
    assert hot.rule_verdict(losers)["verdict"].startswith("rejected")
    winners = [{"net": 2.0}] * 70 + [{"net": -1.0}] * 30
    assert hot.rule_verdict(winners)["verdict"].startswith("not rejected")
