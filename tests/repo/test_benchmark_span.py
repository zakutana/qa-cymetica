"""A verdict's benchmark must cover the room's own span, not the stretch the proxy happened to record in it (T-0036, T-0039, OP-0018).

2026-10-12, read live through our client (GET /event-cards/a4a5b71e.../index-history, the BTC proxy):

    interval   points   median gap   max gap     first point
    1d           289      4.9 min     7 min       10-11 19:59
    5d           241      30 min      44 min      10-07 19:59
    30d          224      3.0 h       51.6 h      09-12 20:50
    all          107      9.8 h       54 h        08-29 01:43

`scripts/lab.py::_history` read every verdict series with `interval=all`, which is 107 points over
44 days, not the 300 the schema promises. A 24 h window ending at the last point holds THREE of them,
the first 8.5 h after the window's start: a span of 15.5 h of 24. `qa/lab.py::verdict` took the first
and last point inside [start, until] and divided, so the room's return (our fill to our sale, 24 h) was
set against a BTC leg of 15.5-19.6 h, and 'refuted if ret <= benchmark' compared two different spans.

What the manager decided (OP-0018); 2 and 3 are held below, 1 and 4 (the reads) in
tests/repo/test_history_interval.py, and the card leg of it (T-0050) in test_card_leg_exit.py:

  1. `_history(client, card, since)` picks the interval by the age of `since` at the read (1d, 5d, 30d,
     all -- every window ends at now, so 1d never covers a 1-day room at its close), one step coarser
     while the first point does not reach `since`; the verdict caches each read by (card, interval)
     and records which interval each series came from.
  2. The benchmark is the proxy's value AT start and AT until, linear between the points around each
     (`qa.lab.index_at`, in the formula's fingerprint). A point on one side only counts within 1 h;
     beyond it the start is None (inconclusive) and the end waits, as an unread read does. A wider
     gap than 1 h is named in `why`, and the verdict still counts. Never the first/last point inside.
  3. Legs are NOT interpolated: their index is written when it moves, a US card stands still at
     night, so coverage is from measured points only (`_inside` and `_early` unchanged).
  4. `lab.py index-at <card> <time>...` is the same helper over one GET, for the desk.

Verdicts already written stand: nothing here rewrites a diary.
"""

from __future__ import annotations

import inspect
from datetime import datetime, timedelta, timezone

import pytest

from qa import lab
from qa.marks import SafetyTier, qa

START = datetime(2026, 10, 12, 17, 28, tzinfo=timezone.utc)
NOW = START + timedelta(days=1, hours=1)
BTC = "a4a5b71e-de11-4805-b8a3-ed9c3f8f8161"
LEG = "e22876b3-a32b-469e-8136-71ecf8b82ffb"


def _rows(offsets_h, value):
    return [{"t": (START + timedelta(hours=h)).isoformat(), "index": float(value(h))}
            for h in offsets_h]


def _acceptance(**over):
    base = {"at": START.isoformat(), "window_days": 1, "stop_pct": 50.0,
            "legs": [{"card": "card-a", "side": "bull", "share": 1.0}],
            "benchmark_card": "btc"}
    base.update(over)
    return base


def _room():
    """Our leg, read every hour over the whole day: 100 to 120, so it ran the full 24 h."""
    return _rows(range(25), lambda h: 100.0 + 20.0 * h / 24.0)


def _btc(offsets_h):
    """BTC rises one point an hour, so its value at any moment is 100 + hours since START."""
    return _rows(offsets_h, lambda h: 100.0 + h)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_benchmark_is_the_proxys_value_at_start_and_at_until():
    # Points as sparse as the `all` read gives: six hours apart, none on either end of the window.
    series = {"card-a": _room(), "btc": _btc([-3, 3, 9, 15, 21, 27])}
    said = lab.verdict(_acceptance(), series, NOW)
    # BTC at start 100, at until 124: +24%. The first and last point inside read 103 and 121: +17.48%.
    assert said["benchmark_pct"] == pytest.approx(24.0), said
    # Our +20% (less whatever the gate charges) lost to +24%, and it survived against +17.48%.
    assert said["verdict"] == "refuted", said


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_control_a_proxy_with_points_on_both_ends_is_the_plain_ratio():
    series = {"card-a": _room(), "btc": _btc([0, 6, 12, 18, 24])}
    said = lab.verdict(_acceptance(), series, NOW)
    assert said["benchmark_pct"] == pytest.approx(24.0), said
    assert said["verdict"] == "refuted", said
    assert said["benchmark_gap_h"] == 0.0, said
    assert "gap" not in said["why"], said


# --- the helper ----------------------------------------------------------------------------------


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_index_at_reads_a_point_between_its_neighbours_or_one_side_within_an_hour():
    points = _btc([0, 6, 12])
    on = lab.index_at(points, START + timedelta(hours=6))
    assert (on["value"], on["how"], on["gap_h"]) == (106.0, "point", 0.0), on
    between = lab.index_at(points, START + timedelta(hours=7, minutes=30))
    assert between["value"] == pytest.approx(107.5) and between["how"] == "between", between
    assert between["gap_h"] == pytest.approx(6.0), "the gap is the span it was read across"
    # One side only: the nearest point within the hour is the value there, on either side.
    late = lab.index_at(points, START + timedelta(hours=12, minutes=40))
    assert (late["value"], late["how"], late["side"]) == (112.0, "nearest", "before"), late
    early = lab.index_at(points, START - timedelta(minutes=50))
    assert (early["value"], early["how"], early["side"]) == (100.0, "nearest", "after"), early
    # Beyond the hour there is no value -- the read does not reach the moment -- and it says how far.
    beyond = lab.index_at(points, START + timedelta(hours=14))
    assert (beyond["value"], beyond["how"]) == (None, "before"), beyond
    assert beyond["gap_h"] == pytest.approx(2.0), beyond
    assert lab.index_at(points, START - timedelta(hours=2))["how"] == "after"
    nothing = lab.index_at([], START)
    assert (nothing["value"], nothing["how"], nothing["gap_h"]) == (None, "none", None), nothing
    # The same reading from a datetime and from its ISO text, and from [t, v] pairs.
    pairs = [[p["t"], p["index"]] for p in points]
    assert lab.index_at(pairs, (START + timedelta(hours=3)).isoformat())["value"] == pytest.approx(103.0)


# --- the verdict's two ends ----------------------------------------------------------------------


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_one_sided_start_counts_within_an_hour_and_is_inconclusive_beyond_it():
    # The proxy's history begins 40 min into the window: its first point stands for the start.
    near = lab.verdict(_acceptance(), {"card-a": _room(), "btc": _btc([40 / 60, 6, 12, 18, 24])}, NOW)
    assert near["benchmark_pct"] == pytest.approx((124.0 / (100.0 + 40 / 60) - 1) * 100), near
    # Two hours in: nothing measured the start, and a later first point is not it.
    far = lab.verdict(_acceptance(), {"card-a": _room(), "btc": _btc([2, 6, 12, 18, 24])}, NOW)
    assert far["verdict"] == "inconclusive" and far["benchmark_pct"] is None, far
    assert "start" in far["why"], far


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_one_sided_end_counts_within_an_hour_and_waits_beyond_it():
    # Read 20 min after the close, the proxy's newest point 30 min before it: that point stands.
    near = lab.verdict(_acceptance(), {"card-a": _room(), "btc": _btc([0, 6, 12, 18, 23.5])},
                       START + timedelta(days=1, minutes=20))
    assert near["benchmark_pct"] == pytest.approx(23.5) and near["verdict"] == "refuted", near
    # Its newest point two hours before the close and none after it yet: the verdict waits, the
    # way it waits on a read that failed -- not inconclusive, and not judged on a shorter span.
    far = lab.verdict(_acceptance(), {"card-a": _room(), "btc": _btc([0, 6, 12, 18, 22])},
                      START + timedelta(days=1, minutes=20))
    assert far["verdict"] == "waiting", far
    assert "benchmark" in far["why"] and "2.0 h" in far["why"], far
    # Once a point after the close arrives, the end is read between the two around it.
    later = lab.verdict(_acceptance(), {"card-a": _room(), "btc": _btc([0, 6, 12, 18, 22, 25])},
                        START + timedelta(days=1, hours=2))
    assert later["benchmark_pct"] == pytest.approx(24.0), later
    assert later["verdict"] == "refuted", later


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_refutation_that_needs_no_benchmark_does_not_wait_for_one():
    """Deep pass 2026-10-25, R02. `waiting` was returned as soon as the benchmark's end was unread,
    before the two refutations that never read it: a room that LOST waited -- for ever, if the
    proxy stopped publishing -- though no benchmark value can make a loss survive. Only what the
    benchmark decides waits for it."""
    stale = _btc([0, 6, 12, 18, 22])   # newest point 2 h before the close, none after it yet
    at = START + timedelta(days=1, minutes=20)

    lost = lab.verdict(_acceptance(), {"card-a": _rows(range(25), lambda h: 100.0 - 10.0 * h / 24.0),
                                       "btc": stale}, at)
    assert lost["verdict"] == "refuted" and "returned" in lost["why"], lost

    # Up 30 % by noon, back to +10 % at the close: positive, but 15 % off its peak, past a 5 % stop.
    def climb_and_fall(h):
        return 100.0 + 30.0 * h / 12.0 if h <= 12 else 130.0 - 20.0 * (h - 12) / 12.0
    fell = lab.verdict(_acceptance(stop_pct=5.0),
                       {"card-a": _rows(range(25), climb_and_fall), "btc": stale}, at)
    assert fell["verdict"] == "refuted" and "drawdown" in fell["why"], fell

    # A room that is up and inside its stop is decided by the benchmark alone: that one waits.
    up = lab.verdict(_acceptance(), {"card-a": _room(), "btc": stale}, at)
    assert up["verdict"] == "waiting", up


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_gap_over_an_hour_is_named_in_why_and_the_verdict_still_counts():
    # The 30d read's 3 h spacing around the window's end: interpolated, said, and judged.
    said = lab.verdict(_acceptance(), {"card-a": _room(), "btc": _btc([0, 6, 12, 18, 22.5, 25.5])}, NOW)
    assert said["verdict"] == "refuted", said
    assert said["benchmark_pct"] == pytest.approx(24.0), said
    assert said["benchmark_gap_h"] == pytest.approx(3.0), said
    assert "3.0 h" in said["why"], said
    # A room that beat it survives, gap named all the same.
    won = lab.verdict(_acceptance(), {"card-a": _rows(range(25), lambda h: 100.0 + 30.0 * h / 24.0),
                                      "btc": _btc([0, 6, 12, 18, 22.5, 25.5])}, NOW)
    assert won["verdict"] == "survived" and "3.0 h" in won["why"], won


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_leg_is_not_interpolated_its_coverage_is_from_measured_points():
    # The leg's last point inside the window is 6 h before its end, and the next one 6 h after it.
    # Interpolated to the end like the benchmark it would cover the whole day; measured, 18 of 24 h.
    leg = _rows([0, 6, 12, 18, 30], lambda h: 100.0 + h)
    said = lab.verdict(_acceptance(), {"card-a": leg, "btc": _btc([0, 6, 12, 18, 24])}, NOW)
    assert said["verdict"] == "inconclusive", said
    assert said["coverage"] == pytest.approx(0.75), said
    # Inside the floor, the leg exits at its last measured point, not at a value made up for the end.
    leg = _rows([0, 6, 12, 20, 30], lambda h: 100.0 + h)
    said = lab.verdict(_acceptance(), {"card-a": leg, "btc": _btc([0, 6, 12, 18, 24])}, NOW)
    (judged,) = said["legs"]
    assert judged["exit_index"] == pytest.approx(120.0) and judged["gross_return_pct"] == pytest.approx(20.0)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_helper_is_in_the_formula_fingerprint(monkeypatch):
    hashed = []
    real = inspect.getsource

    def watch(obj):
        hashed.append(obj)
        return real(obj)
    monkeypatch.setattr(inspect, "getsource", watch)
    assert lab.formula_fingerprint() != "unknown"
    assert lab.index_at in hashed, "a change to how the benchmark is read would not move the formula"
    assert lab.verdict in hashed
