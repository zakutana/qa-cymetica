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


def _quiet(start, end, every=40, hot_rows=(), skip=()):
    """Rounds every `every` min from `start` up to (not including) `end`, none
    at a time in `skip`: the loop running, seeing `hot_rows` or nothing."""
    out, when = [], start
    while when < end:
        if when not in skip:
            out.append(_round(when, hot_rows))
        when += timedelta(minutes=every)
    return out


def _path(hid, start, pxs, every=20, rank=1, in_hot=True, ret=7.0):
    """Rounds every `every` min; the row sits in hot (crypto) at each px."""
    out = []
    for i, px in enumerate(pxs):
        when = start + timedelta(minutes=every * i)
        hot_rows = [(hid, rank, ret, "crypto", px, ret)] if in_hot else []
        out.append(_round(when, hot_rows, [(hid, 10.0, px, 0.1, ret)]))
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
def test_a_basket_is_priced_through_another_headline_when_its_own_row_is_gone():
    """Hot belongs to the basket: when the entry's own headline stops being
    listed, a round that prices the same basket under another headline is
    still the basket's price. Seen live on 2026-09-21: 3 of 9 crypto entries
    unobserved at +6 h because their own row had left the wire."""
    heads = [_headline(1), _headline(2)]
    rounds = [_round(T0)] + _path(1, T0 + timedelta(minutes=20), [100])
    rounds.append(_round(T0 + timedelta(hours=6, minutes=20), [],
                         [(2, 1.0, 106, 0.1, 3.0)]))
    (entry,) = hot.entries(rounds, heads)
    # The whole diary, as reading() passes it: the siblings come from the
    # headline rows in it.
    (six,) = hot.follow([entry], heads + rounds, horizons=(6,))["crypto"]
    assert six["n"] == 1 and six["mean"] == 6.0

    # B02, deep pass of 2026-09-21: the rule's exits read the basket the same
    # way. Before, a trade whose own row had left the wire never exited.
    ruled = ([_round(T0)] + _path(1, T0 + timedelta(minutes=20), [100])
             + [_round(T0 + timedelta(minutes=40), [], [(2, 1.0, 109, 0.1, 3.0)])])
    (trade,) = hot.nexus_rule(heads + ruled)["trades"]
    assert trade["exit"] == "take_profit" and trade["gross"] == 9.0


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_confirmation_reads_the_basket_through_a_sibling_headline():
    """B02's reasoning, carried to NEX-0057's confirmation: the basket is still
    in Hot one round later under another headline, and that round prices it
    through that headline. Before, the entry's own row being gone dropped the
    entry altogether."""
    heads = [_headline(1, published=T0), _headline(2, published=T0)]
    rounds = [_round(T0),
              _round(T0 + timedelta(minutes=20), [(1, 40, 7.0, "crypto", 100, 7.0)],
                     [(1, 1.0, 100, 0.1, 7.0)]),
              _round(T0 + timedelta(minutes=40), [(2, 40, 7.0, "crypto", 102, 7.0)],
                     [(2, 1.0, 102, 0.1, 7.0)]),
              _round(T0 + timedelta(minutes=60), [], [(2, 1.0, 112, 0.1, 7.0)])]
    said = hot.nexus_rule(heads + rounds, rule=hot.VARIANTS["NEX-0057a"])
    assert said["entries"] == 1, "a sibling's price confirms the entry"
    (trade,) = said["trades"]
    assert trade["at"] == _iso(T0 + timedelta(minutes=40))
    assert trade["exit"] == "take_profit"
    assert abs(trade["gross"] - (112 / 102 - 1) * 100) < 1e-6


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_volatility_stop_reads_the_basket_through_a_sibling_headline():
    """B02's reasoning, carried to NEX-0057d's stop: the basket's path before
    the entry is priced under another headline. Read through the entry's own
    row only, it had two points, so no ATR, and the -4 floor stopped a trade
    the basket's own swing says should have ridden a -5 % dip."""
    heads = [_headline(1, published=T0), _headline(2, published=T0)]
    before = [_round(T0 + timedelta(minutes=20 * i), [], [(2, 10.0, px, 0.1, 7.0)])
              for i, px in enumerate([100, 103])]
    rounds = before + _path(1, T0 + timedelta(minutes=40),
                            [100, 103, 97.85, 113.3, 117.42], rank=40)
    assert hot.vol_stop(rounds, 1, "crypto", T0 + timedelta(minutes=60)) == -4.0
    stop = hot.vol_stop(rounds, 1, "crypto", T0 + timedelta(minutes=60), siblings=[2])
    assert stop < -5.0
    (trade,) = hot.nexus_rule(rounds, heads, hot.VARIANTS["NEX-0057d"])["trades"]
    assert trade["exit"] == "take_profit", "the sibling's path widened the stop"
    assert abs(trade["gross"] - (117.42 / 103 - 1) * 100) < 1e-6


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_readings_sort_the_diary_once_not_once_per_basket(monkeypatch):
    """R01, deep pass of 2026-09-21 (3/3): forward() re-sorted the whole diary
    for every basket, and control() hands it hundreds per entry round -- 0.9 s
    at 27 rounds, growing about R^2.3, inside a tick every six hours. The
    readings now index the rounds once per call."""
    heads = [_headline(n, crypto=(f"C{n}A", f"C{n}B", f"C{n}C")) for n in range(1, 41)]
    # A day of rounds before, so the control has a look-back to stand on.
    rounds = _quiet(T0 - timedelta(hours=25), T0) + [_round(T0)]
    for i in range(1, 30):
        when = T0 + timedelta(minutes=20 * i)
        hot_rows = [(1, 1, 7.0, "crypto", 100 + i, 7.0)] if i >= 1 else []
        wire = [(n, 1.0, 50 + n + i, 0.1, 1.0) for n in range(1, 41)]
        rounds.append(_round(when, hot_rows, wire))
    rows = heads + rounds
    calls = {"n": 0}
    real = hot._rounds

    def counted(rs):
        calls["n"] += 1
        return real(rs)
    monkeypatch.setattr(hot, "_rounds", counted)
    found = hot.entries(rows)
    calls["n"] = 0
    said = hot.control(rows, found, horizons=(1.0, 6.0))
    assert calls["n"] <= 4, f"_rounds ran {calls['n']} times for one reading"
    assert said["crypto"][0]["n"] > 0


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


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_control_holds_no_basket_that_was_in_hot_during_the_last_day():
    """A basket that dropped out of Hot three hours ago is the tail of what
    is being measured, not a basket that was never called -- and a day with
    a failed hot read in it cannot say which baskets were never called."""
    heads = [_headline(1), _headline(2, crypto=("DDD", "EEE", "FFF")),
             _headline(3, crypto=("GGG", "HHH", "III"))]
    # The loop ran all day before (row 2 hot throughout, so it is no entry)
    # and between -- the control needs a whole look-back (see the test below).
    hot_2 = [(2, 1, 5.0, "crypto", 10, 5.0)]
    day = _quiet(T0 - timedelta(hours=21), T0, every=20, hot_rows=hot_2)
    was_hot = _round(T0, hot_2, [(2, 1.0, 10, 0.1, 5.0)])
    between = _quiet(T0 + timedelta(minutes=20), T0 + timedelta(hours=3), every=20,
                     skip={T0 + timedelta(hours=1)})
    before = _round(T0 + timedelta(hours=3), [], [])
    entry = _round(T0 + timedelta(hours=3, minutes=20),
                   [(1, 1, 7.0, "crypto", 100, 7.0)],
                   [(1, 1.0, 100, 0.1, 7.0), (2, 1.0, 10, 0.1, 1.0),
                    (3, 1.0, 20, 0.1, 1.0)])
    later = _round(T0 + timedelta(hours=3, minutes=40), [],
                   [(2, 1.0, 11, 0.1, 1.0), (3, 1.0, 21, 0.1, 1.0)])
    rows = heads + day + [was_hot] + between + [before, entry, later]
    found = hot.entries(rows)
    assert [e["row"] for e in found] == [1]
    (short,) = hot.control(rows, found, horizons=(20 / 60,))["crypto"]
    assert short["n"] == 1 and short["mean"] == 5.0, "row 3 only, not row 2"

    # B06, deep pass of 2026-09-21, rule 8: a round whose hot read failed is
    # not a round that saw nothing hot. Row 3 is not on that round's wire
    # either (its wire read failed too), so only the conservative reading --
    # a blind round in the look-back proves no basket absent -- keeps it out.
    blind = {"type": "round", "at": _iso(T0 + timedelta(hours=1)), "ok": False,
             "errors": ["hot: HTTP 503", "wire: HTTP 503"], "hot": None, "wire": []}
    rows = heads + day + [was_hot, blind] + between + [before, entry, later]
    found = hot.entries(rows)
    assert [e["row"] for e in found] == [1]
    (short,) = hot.control(rows, found, horizons=(20 / 60,))["crypto"]
    assert short["n"] == 0, "a basket hot only while we were blind is not a control"
    # A blind round older than the day before the entry is outside the question.
    old = {**blind, "at": _iso(T0 + timedelta(hours=3, minutes=20) - timedelta(hours=25))}
    rows = heads + [old] + day + [was_hot] + between + [before, entry, later]
    (short,) = hot.control(rows, hot.entries(rows), horizons=(20 / 60,))["crypto"]
    assert short["n"] == 1 and short["mean"] == 5.0


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_control_takes_nothing_from_a_look_back_the_loop_did_not_watch():
    """B06's reasoning, rule 8, carried to the rounds that were never taken: a
    stretch longer than GAP_MINUTES with no round, or the day before the first
    round of the diary, is as unknown as a failed hot read -- a basket hot
    only then would join the control as "not in Hot". So an entry whose day
    before holds either brings no control at all."""
    heads = [_headline(1), _headline(3, crypto=("GGG", "HHH", "III"))]
    entry = _round(T0, [(1, 1, 7.0, "crypto", 100, 7.0)],
                   [(1, 1.0, 100, 0.1, 7.0), (3, 1.0, 20, 0.1, 1.0)])
    later = _round(T0 + timedelta(minutes=20), [], [(3, 1.0, 21, 0.1, 1.0)])

    def control_n(day):
        rows = heads + day + [entry, later]
        found = hot.entries(rows)
        assert [e["row"] for e in found] == [1]
        (short,) = hot.control(rows, found, horizons=(20 / 60,))["crypto"]
        return short["n"]

    start = T0 - timedelta(hours=27)
    assert control_n(_quiet(start, T0)) == 1, "a watched day: row 3 is a control"
    assert control_n(_quiet(T0 - timedelta(hours=23), T0)) == 0, \
        "the diary began inside the day before the entry"
    hole = T0 - timedelta(hours=10) - timedelta(minutes=20)
    assert hole in {start + timedelta(minutes=40 * k) for k in range(60)}
    assert control_n(_quiet(start, T0, skip={hole})) == 0, \
        "an 80-minute stretch with no round inside the day before"
    old = start + timedelta(minutes=80)
    assert control_n(_quiet(start, T0, skip={old})) == 1, \
        "a hole older than the day before is outside the question"


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
    """B04, deep pass of 2026-09-21: the stock basket had two members and no
    round after its entry, so it traded nothing with the class gate deleted.
    Each fixture now trades once the one gate under test is relaxed."""
    old = _headline(1, published=T0 - timedelta(hours=3))
    rounds = [_round(T0)] + _path(1, T0 + timedelta(minutes=20), [100, 120])
    assert hot.nexus_rule(rounds, [old])["trades"] == []
    assert len(hot.nexus_rule(rounds, [old], {"max_age_minutes": 240})["trades"]) == 1

    fresh = _headline(2, stock=("XX", "YY", "ZZ"), published=T0)
    stock = [_round(T0)] + [
        _round(T0 + timedelta(minutes=20 * i), [(2, 1, 7.0, "stocks", px, 7.0)],
               [(2, px, 1.0, 7.0, 0.1)])
        for i, px in ((1, 50.0), (2, 55.0))]
    assert hot.nexus_rule(stock, [fresh])["trades"] == []
    (trade,) = hot.nexus_rule(stock, [fresh], {"hot_class": "stocks"})["trades"]
    assert trade["exit"] == "take_profit", "the class gate alone kept it out"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_rule_needs_its_own_threshold_and_rank():
    """B03, deep pass of 2026-09-21: the low-return fixture had no round after
    its entry, so it traded nothing whatever the threshold. Both fixtures now
    run to a take-profit, and trade once the gate under test is relaxed."""
    heads = [_headline(1, published=T0)]
    low = [_round(T0)] + _path(1, T0 + timedelta(minutes=20), [100, 120], ret=5.0)
    assert hot.nexus_rule(low, heads)["trades"] == []
    assert len(hot.nexus_rule(low, heads, {"min_ret_24h": 5.0})["trades"]) == 1
    deep = [_round(T0)] + _path(1, T0 + timedelta(minutes=20), [100, 120], rank=4)
    assert hot.nexus_rule(deep, heads)["trades"] == []
    assert len(hot.nexus_rule(deep, heads, {"max_rank": 4})["trades"]) == 1


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_rule_ignores_a_basket_that_may_have_sat_in_hot_past_thirty_minutes():
    """B05, deep pass of 2026-09-21: NEX-0055's second clock, time in Hot
    <= 30 min, was declared and never read. The diary proves only an upper
    bound -- the entry round minus the last covered round that saw the basket
    absent -- and GAP_MINUTES lets that be 40. Past his 30 it is still an
    entry, just not one under his rule."""
    heads = [_headline(1, published=T0)]
    late = [_round(T0)] + _path(1, T0 + timedelta(minutes=35), [100, 120])
    assert len(hot.entries(late, heads)) == 1
    assert hot.nexus_rule(late, heads)["trades"] == []
    assert len(hot.nexus_rule(late, heads, {"max_minutes_in_hot": 40})["trades"]) == 1


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_nex_0057_drops_the_rank_and_enters_only_once_the_next_round_confirms():
    """His revision: no rank gate; the basket must still be in Hot one round
    later, and the trade starts there, at that round's price."""
    heads = [_headline(1, published=T0)]
    rounds = [_round(T0)] + _path(1, T0 + timedelta(minutes=20),
                                  [100, 102, 111], rank=40)
    variant = hot.VARIANTS["NEX-0057a"]
    said = hot.nexus_rule(rounds, heads, variant)
    (trade,) = said["trades"]
    assert trade["at"] == _iso(T0 + timedelta(minutes=40)), "entered on confirmation"
    assert trade["exit"] == "take_profit"
    assert abs(trade["gross"] - (111 / 102 - 1) * 100) < 1e-6

    blip = [_round(T0)] + _path(1, T0 + timedelta(minutes=20), [100], rank=40) \
        + [_round(T0 + timedelta(minutes=40))]
    assert hot.nexus_rule(blip, heads, variant)["trades"] == []
    assert hot.nexus_rule(rounds, heads)["trades"] == [], "NEX-0055 keeps its rank"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_volatility_stop_widens_with_the_basket_and_never_tightens_past_four():
    """NEX-0057: stop about -1.25x the basket's hourly ATR, floored at -4 %,
    target twice the stop. A quiet basket keeps -4 / +8."""
    quiet = _path(1, T0, [100, 100.1, 100.0, 100.1])
    assert hot.vol_stop(quiet, 1, "crypto", T0 + timedelta(minutes=60)) == -4.0
    wild = _path(1, T0, [100, 104, 100, 104])
    stop = hot.vol_stop(wild, 1, "crypto", T0 + timedelta(minutes=60))
    assert stop < -4.0
    few = _path(1, T0, [100])
    assert hot.vol_stop(few, 1, "crypto", T0) == -4.0, "no history, the floor"

    # B08, deep pass of 2026-09-21: NEX-0057d run through the rule. The basket
    # swings 3 % a round before it enters, so its stop is wider than -4 and
    # the target twice that: a -5 % dip does not stop it and +10 % does not
    # take profit -- the first round past the widened target does.
    heads = [_headline(1, published=T0)]
    before = [_round(T0 + timedelta(minutes=20 * i), [], [(1, 10.0, px, 0.1, 7.0)])
              for i, px in enumerate([100, 103])]
    rounds = before + _path(1, T0 + timedelta(minutes=40),
                            [100, 103, 97.85, 113.3, 117.42], rank=40)
    stop = hot.vol_stop(rounds, 1, "crypto", T0 + timedelta(minutes=60))
    assert 10.0 < -2.0 * stop < 14.0 and stop < -5.0, "the fixture spans both levels"
    (trade,) = hot.nexus_rule(rounds, heads, hot.VARIANTS["NEX-0057d"])["trades"]
    assert trade["at"] == _iso(T0 + timedelta(minutes=60))
    assert trade["exit"] == "take_profit"
    assert abs(trade["gross"] - (117.42 / 103 - 1) * 100) < 1e-6, "target = 2 x stop"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_trade_whose_time_stop_was_never_seen_is_open_not_a_result():
    """Open while the rounds have not reached its end; unobserved once they
    passed it without pricing the basket (B02, deep pass of 2026-09-21: it
    stayed open for ever, where follow() already said unobserved)."""
    heads = [_headline(1, published=T0)]
    rounds = [_round(T0)] + _path(1, T0 + timedelta(minutes=20), [100, 101])
    said = hot.nexus_rule(rounds, heads)
    assert said["trades"] == []
    assert said["open"] == 1 and said["unobserved"] == 0

    later = rounds + [_round(T0 + timedelta(hours=26))]
    said = hot.nexus_rule(later, heads)
    assert said["trades"] == []
    assert said["open"] == 0 and said["unobserved"] == 1


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_verdict_waits_for_a_hundred_and_then_reads_the_t_stat():
    """Each of his three rejections is its own gate (B09, deep pass of
    2026-09-21: no sample had a positive mean below his t, so the t gate
    could be deleted green)."""
    losers = [{"net": -1.0}] * 60 + [{"net": 0.5}] * 40
    assert hot.rule_verdict(losers[:99])["verdict"].startswith("not yet")
    assert hot.rule_verdict(losers)["verdict"].startswith("rejected")
    winners = [{"net": 2.0}] * 70 + [{"net": -1.0}] * 30
    assert hot.rule_verdict(winners)["verdict"].startswith("not rejected")
    faint = [{"net": 1.0}] * 50 + [{"net": -0.9}] * 50
    said = hot.rule_verdict(faint)
    assert said["mean_net"] > 0 and said["expectancy"] > 0 and said["t"] < 1.65
    assert said["verdict"].startswith("rejected"), "the t-stat alone rejects it"
