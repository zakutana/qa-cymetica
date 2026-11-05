"""Retail index v5 (qa/retailindex.py): the pure functions, on data built to be wrong as well as right, offline.

The rules are in outbox/retail-index/RESULT.md. These tests hold the parts that must not drift: a week holds only
the days before its Monday, a later week never moves an earlier reading, a slow slide is not read as sleep, a
percentile means what it says, and a window with too few families is not scored.
"""
from __future__ import annotations

import math

from qa import retailindex as R


def _table(n=330, **cols):
    base = R.ordinal("2018-01-01")
    t = {"week": [base + 7 * i for i in range(n)]}
    for k in [c for f in R.FAMILIES.values() for c, _ in f]:
        t[k] = [None] * n
    t.update(cols)
    return t


def test_a_week_holds_only_the_days_before_its_monday():
    W = R.ordinal("2024-03-11")
    daily = {d: 1.0 for d in range(W - 7, W)}
    daily[W] = 1000.0
    daily[W - 8] = 1000.0
    assert R.week_sum(daily, W) == 7.0
    assert R.week_last(daily, W) == 1.0


def test_a_week_with_one_day_missing_is_scaled_and_with_two_is_refused():
    W = R.ordinal("2024-03-11")
    six = {d: 2.0 for d in range(W - 7, W - 1)}
    five = {d: 2.0 for d in range(W - 7, W - 2)}
    assert R.week_sum(six, W) == 14.0
    assert R.week_sum(five, W) is None


def test_a_percentile_means_the_rank_among_the_trailing_weeks_and_waits_for_enough_history():
    up = [float(i) for i in range(100)]
    out = R.trailing_percentile(up, window=208, min_n=52)
    assert out[50] is None and out[51] is not None
    assert out[99] > 99 and out[51] > 99
    flat = R.trailing_percentile([5.0] * 80, min_n=52)
    assert flat[79] == 50.0
    down = R.trailing_percentile([float(100 - i) for i in range(100)], min_n=52)
    assert down[99] < 1


def test_a_slow_slide_detrends_to_a_flat_line_not_to_sleep():
    slide = [1000 * 0.985 ** i for i in range(330)]
    flat = R.detrend(slide)
    late = [v for v in flat[150:] if v is not None]
    assert max(late) - min(late) < 0.01 * max(late)
    pct = R.trailing_percentile([None if v is None else round(v, 9) for v in flat])
    # a real burst on top of the slide reads high, the slide alone does not
    burst = slide[:]
    for i in range(300, 306):
        burst[i] *= 3
    hot = R.trailing_percentile(R.detrend(burst))
    assert hot[303] > 95 and (pct[303] is None or 20 < pct[303] < 80)


def test_a_later_week_never_moves_an_earlier_reading():
    n = 330
    a = [(math.sin(i / 9) + 1) * 50 + i % 7 for i in range(n)]
    t1 = _table(n, cb_turn=a[:], kimchi=a[:], fund=a[:])
    t2 = _table(n, cb_turn=a[:], kimchi=a[:], fund=a[:])
    for i in range(300, n):
        t2["cb_turn"][i] = 1e9
        t2["kimchi"][i] = -1e9
        t2["fund"][i] = 7.0
    r1, r2 = R.compute_index(t1), R.compute_index(t2)
    assert r1["index"][:300] == r2["index"][:300]
    assert r1["index"][305] != r2["index"][305]


def test_the_index_needs_two_families_and_one_family_alone_is_empty():
    n = 330
    wave = [(math.sin(i / 11) + 1) * 40 + 10 for i in range(n)]
    one = R.compute_index(_table(n, fund=wave[:]))
    assert all(v is None for v in one["index"])
    two = R.compute_index(_table(n, fund=wave[:], kimchi=wave[:]))
    scored = [i for i, v in enumerate(two["index"]) if v is not None]
    assert scored and all(two["nfam"][i] == 2 for i in scored)
    three = _table(n, fund=wave[:], kimchi=wave[:], cb_turn=[w + 1 for w in wave])
    assert max(R.compute_index(three)["nfam"]) == 3
    assert max(R.compute_index(three, drop_family="leverage")["nfam"]) == 2


def test_two_runs_over_one_table_give_the_same_index():
    n = 330
    wave = [(math.sin(i / 13) + 1) * 45 + (i * 7) % 11 for i in range(n)]
    t = _table(n, fund=wave[:], kimchi=wave[:], breadth=wave[:])
    assert R.compute_index(t) == R.compute_index(t)


def test_a_zigzag_finds_a_top_after_a_40_percent_fall_and_a_bottom_after_a_67_percent_rise():
    path = [100, 130, 180, 200, 150, 119, 100, 110, 140, 170, 175]
    assert R.zigzag(path) == [(3, "top"), (6, "bottom")]
    assert R.zigzag([100, 110, 105, 115, 120]) == []


def test_spearman_is_one_for_a_rise_minus_one_for_a_fall_and_handles_ties():
    xs = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0]
    assert R.spearman(xs, [x * 3 for x in xs]) == 1.0
    assert abs(R.spearman(xs, [-x for x in xs]) + 1.0) < 1e-12
    assert R.spearman(xs, [1.0] * len(xs)) is None
    assert R.spearman(xs[:5], xs[:5]) is None


def test_a_top_window_is_not_scored_without_two_families_and_is_marked_thin_with_two():
    weeks = [R.ordinal("2018-01-01") + 7 * i for i in range(40)]
    series = [None] * 3 + [80.0] * 37
    one = R.check_windows(series, weeks, [1] * 40, ("2018-01-15",), "top")
    two = R.check_windows(series, weeks, [2] * 40, ("2018-01-15",), "top")
    three = R.check_windows(series, weeks, [3] * 40, ("2018-01-15",), "top")
    assert one[0]["status"] == "not scorable"
    assert two[0]["status"] == "pass" and two[0]["thin"] is True
    assert three[0]["status"] == "pass" and three[0]["thin"] is False
    low = R.check_windows([50.0] * 40, weeks, None, ("2018-01-15",), "low")
    assert low[0]["status"] == "fail"


def test_the_block_bootstrap_is_the_same_twice_and_its_interval_holds_the_difference():
    flags = [i % 20 < 5 for i in range(300)]
    fwd = [(-0.2 if flags[i] else 0.1) + ((i * 37) % 10 - 5) / 200 for i in range(300)]
    a = R.block_bootstrap_diff(flags, fwd, draws=300, seed=1)
    b = R.block_bootstrap_diff(flags, fwd, draws=300, seed=1)
    assert a == b
    assert a["lo"] < a["diff"] < a["hi"] and a["hi"] < 0


def test_the_sources_parse_to_the_monday_that_opens_the_week():
    monday = R.ordinal("2026-10-26")
    ts = (monday - R.ordinal("1970-01-01")) * 86400
    k = [[ts * 1000, "1", "2", "0.5", "7.5", "9", 0, "123.0"]]
    assert R.parse_binance_weeks(k) == {monday: (7.5, 123.0)}
    u = [{"candle_date_time_utc": "2026-10-26T00:00:00", "trade_price": 10, "candle_acc_trade_price": 55}]
    assert R.parse_upbit_weeks(u) == {monday: (10.0, 55.0)}
    cb = [[ts, 1, 2, 1.5, 4.0, 3.0]]
    assert R.parse_coinbase_candles(cb) == {monday: (4.0, 12.0)}


def test_the_top_zone_share_counts_scored_weeks_and_the_longest_run():
    series = [None, 10, 80, 80, 80, 20, 76, 30]
    share, longest = R.top_zone_share(series)
    assert abs(share - 4 / 7) < 1e-12 and longest == 3
