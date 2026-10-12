"""A verdict's benchmark must cover the room's own span, not the stretch the proxy happened to record in it (T-0036).

2026-10-12, read live through our client (GET /event-cards/a4a5b71e.../index-history, the BTC proxy):

    interval   points   median gap   max gap     first point
    1d           289      4.9 min     7 min       10-11 19:59
    5d           241      30 min      44 min      10-07 19:59
    30d          224      3.0 h       51.6 h      09-12 20:50
    all          107      9.8 h       54 h        08-29 01:43

`scripts/lab.py::_history` reads every verdict series with `interval=all`, which is 107 points over
44 days, not the 300 the schema promises. A 24 h window ending at the last point holds THREE of them,
the first 8.5 h after the window's start: a span of 15.5 h of 24. `qa/lab.py::verdict` takes the first
and last point inside [start, until] and divides, so the room's return (our fill to our sale, 24 h) is
set against a BTC leg of 15.5-19.6 h, and 'refuted if ret <= benchmark' compares two different spans.

The fix is the session's (qa/ and scripts/ are closed to workers). What it must do, from the ticket:
read the finest interval that covers the window (5d/30d/all, never `all` for a 1-day room), take the
proxy's value AT start and AT until by interpolating between the points around each, say a gap over
1 h, and never fall back to a shorter span. `formula_fingerprint()` moves with it; verdicts already
written stand.

This test holds the verdict to that: the benchmark is the proxy's value at `until` over its value at
`start`, whatever the spacing of the points. Strict xfail: it fails on the ASSERTION today and turns
red the day the fix lands, and the marker must go then. The control beside it passes now and must keep
passing: points exactly on both ends are the plain ratio.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from qa import lab
from qa.marks import SafetyTier, qa

START = datetime(2026, 10, 12, 17, 28, tzinfo=timezone.utc)
NOW = START + timedelta(days=1, hours=1)


def _rows(offsets_h, value):
    return [{"t": (START + timedelta(hours=h)).isoformat(), "index": float(value(h))}
            for h in offsets_h]


def _acceptance():
    return {"at": START.isoformat(), "window_days": 1, "stop_pct": 50.0,
            "legs": [{"card": "card-a", "side": "bull", "share": 1.0}],
            "benchmark_card": "btc"}


def _room():
    """Our leg, read every hour over the whole day: 100 to 120, so it ran the full 24 h."""
    return _rows(range(25), lambda h: 100.0 + 20.0 * h / 24.0)


def _btc(offsets_h):
    """BTC rises one point an hour, so its value at any moment is 100 + hours since START."""
    return _rows(offsets_h, lambda h: 100.0 + h)


@pytest.mark.xfail(strict=True, reason="verdict() takes the proxy's first and last point inside the "
                   "window, a 17.48% leg for a 24% day (T-0036)")
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
