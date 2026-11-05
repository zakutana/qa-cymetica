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


# ---- v6: social families and the peak signal -------------------------------------------------------

def _social_table(n=330, **cols):
    base = R.ordinal("2018-01-01")
    t = {"week": [base + 7 * i for i in range(n)]}
    for k in [c for f in R.SOCIAL_FAMILIES.values() for c, _ in f]:
        t[k] = [None] * n
    t.update(cols)
    return t


def test_wikimedia_rows_become_days():
    rows = [{"timestamp": "2021112600", "views": 21497}, {"timestamp": "bad", "views": 1}, {"views": 3}]
    assert R.parse_wikimedia(rows) == {R.ordinal("2021-11-26"): 21497.0}


def test_a_reddit_week_is_sampled_on_its_tuesday_and_friday_and_stands_for_the_week_times_three_and_a_half():
    W = R.ordinal("2024-03-11")            # a Monday: the week holds [W-7, W)
    days = R.sample_days(W - 7, W)
    assert [R.date.fromordinal(d).strftime("%a") for d in days] == ["Tue", "Fri"]
    assert all(W - 7 <= d < W for d in days)
    daily = {days[0]: 100, days[1]: 300}
    assert R.week_sum(daily, W, min_days=2) == 1400.0       # (100 + 300) x 3.5
    assert R.week_sum({days[0]: 100}, W, min_days=2) is None   # one sampled day is not a week
    # a range that starts mid-week keeps only the days inside it
    assert R.sample_days(W - 5, W - 2) == [W - 3]


def test_the_social_index_uses_only_social_columns_and_the_default_still_uses_v5s():
    n = 330
    t = _social_table(n, wiki_bitcoin=[100.0 + (i % 7) for i in range(n)], rd_cc=[50.0 + (i % 5) for i in range(n)])
    t["cb_turn"] = [1.0 + (i % 3) for i in range(n)]
    social = R.compute_index(t, families=R.SOCIAL_FAMILIES)
    assert list(social["families"]) == ["attention", "crowd", "degen"]
    assert "cb_turn" not in social["members"]
    assert social["nfam"][-1] == 2 and social["index"][-1] is not None   # attention + crowd, degen absent: thin
    v5 = R.compute_index(t)
    assert list(v5["families"]) == list(R.FAMILIES) and "wiki_bitcoin" not in v5["members"]


def test_a_social_burst_reads_high_and_a_later_week_does_not_move_an_earlier_one():
    n = 330
    wiki = [100.0] * n
    reddit = [40.0] * n
    for i in range(300, 306):
        wiki[i], reddit[i] = 400.0, 200.0
    t = _social_table(n, wiki_bitcoin=wiki, wiki_ethereum=wiki[:], rd_cc=reddit, rd_btc=reddit[:])
    full = R.compute_index(t, families=R.SOCIAL_FAMILIES)["index"]
    cut = {k: (v[:304] if isinstance(v, list) else v) for k, v in t.items()}
    early = R.compute_index(cut, families=R.SOCIAL_FAMILIES)["index"]
    assert full[303] > 90 and full[250] < 60
    assert early[:304] == full[:304]


def test_the_index_csv_names_the_families_it_was_given():
    n = 330
    t = _social_table(n, wiki_bitcoin=[1.0 + (i % 4) for i in range(n)], rd_cc=[2.0 + (i % 3) for i in range(n)])
    r = R.compute_index(t, families=R.SOCIAL_FAMILIES)
    head = R.index_csv(t, r).splitlines()[0]
    assert head == "week,index,nfam,zone,attention,crowd,degen"


def _weeks(n):
    return [R.ordinal("2020-01-06") + 7 * i for i in range(n)]


def test_the_peak_signal_waits_for_the_fall_and_is_silent_when_the_index_never_got_hot():
    never = [50.0] * 60
    assert R.peak_signals(never) == []
    rise_fall = [30.0] * 10 + [80.0] * 6 + [80 - 8 * k for k in range(1, 13)] + [20.0] * 30
    sig = R.peak_signals(rise_fall)
    assert len(sig) == 1
    # the 4-week mean has fallen 15 below its high only some weeks after the peak, never before it
    assert sig[0] > 15
    assert max(v for v in rise_fall[:sig[0] + 1]) == 80.0


def test_the_peak_signal_does_not_fire_twice_inside_26_weeks_and_fires_again_after():
    one = [30.0] * 10 + [80.0] * 5 + [20.0] * 12
    two = one + [30.0] * 4 + [80.0] * 5 + [20.0] * 12
    three = one + [30.0] * 40 + [80.0] * 5 + [20.0] * 12
    assert len(R.peak_signals(two)) == 1
    assert len(R.peak_signals(three)) == 2


def test_the_signal_score_counts_a_top_within_eight_weeks_and_a_far_signal_as_false():
    weeks = _weeks(200)
    top_pos = 100
    top_date = R.iso(weeks[top_pos])
    s = R.score_signals([top_pos + 5, 20], weeks, (top_date,), other_tops=[])
    assert s["caught"] == 1 and s["tops"][0]["delay"] == 5
    assert s["signals"] == 2 and s["false_alarms"] == 1 and s["false_weeks"] == [20]
    other = R.score_signals([top_pos + 5, 20], weeks, (top_date,), other_tops=[22])
    assert other["false_alarms"] == 0
    miss = R.score_signals([top_pos + 9], weeks, (top_date,), other_tops=[])
    assert miss["caught"] == 0 and miss["tops"][0]["delay"] is None


def test_the_top_window_check_can_ask_for_75_instead_of_70():
    weeks = _weeks(200)
    series = [40.0] * 200
    series[100] = 72.0
    d = R.iso(weeks[100])
    assert R.check_windows(series, weeks, None, (d,), "top")[0]["status"] == "pass"
    assert R.check_windows(series, weeks, None, (d,), "top", top_min=75.0)[0]["status"] == "fail"
