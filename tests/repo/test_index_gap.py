"""The reading behind the "a live crypto card's index history has no multi-day hole" check (2026-10-12, T-0052).

The BTC proxy a4a5b71e answered `index-history?interval=30d` with a point every 3 h except between
2026-09-23 14:16:52 and 2026-09-25 17:54:33 UTC: 51.6 h, while its index moved 137.71 -> 134.26
and three older crypto-only cards (30408a4b, 30015006, 5d91bf43) held 17 to 18 points inside the same
hours. These cases pin how a gap is read, so a thin series is not a hole, a short one is not read as
long, and an unreadable point is None and not zero.
"""

from qa.marks import SafetyTier, qa
from tests.rest.test_a_live_crypto_card_index_history_has_no_multi_day_hole import widest_gap


def _p(day, hh, mm=0):
    return {"t": f"2026-09-{day:02d}T{hh:02d}:{mm:02d}:00+00:00", "index": 100.0}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_widest_gap_names_its_two_ends_and_its_hours():
    series = [_p(23, 8, 58), _p(23, 11, 57), _p(23, 14, 16), _p(25, 17, 54), _p(25, 20, 59)]
    hours, start, end = widest_gap(series)
    assert abs(hours - (51 + 38 / 60)) < 0.01, hours
    assert start.startswith("2026-09-23T14:16") and end.startswith("2026-09-25T17:54"), (start, end)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_even_three_hour_series_reads_three_hours():
    series = [_p(13, h) for h in range(0, 24, 3)]
    assert widest_gap(series)[0] == 3.0


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_order_the_points_arrive_in_does_not_matter():
    series = [_p(25, 17, 54), _p(23, 14, 16), _p(23, 11, 57)]
    assert round(widest_gap(series)[0], 1) == 51.6


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_fewer_than_two_points_are_no_gap_not_a_zero_gap():
    assert widest_gap([]) is None
    assert widest_gap([_p(23, 8)]) is None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_unreadable_point_makes_the_series_unreadable():
    """Dropping the bad point would close a hole the bad point sat in the middle of."""
    assert widest_gap([_p(23, 8), {"t": "garbage", "index": 1.0}, _p(25, 8)]) is None
    assert widest_gap([_p(23, 8), {"index": 1.0}, _p(25, 8)]) is None
    assert widest_gap(None) is None
    assert widest_gap([_p(23, 8), "not a point", _p(25, 8)]) is None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_history_that_stopped_recording_is_a_hole_up_to_the_servers_now():
    """C07, deep pass 2026-10-18: only the stretches BETWEEN points were measured, so a live card
    whose recorder stopped three days ago -- a point every 3 h up to then, none since -- passed. The
    end is the server's own clock (its Date header), not ours."""
    from tests.rest.test_a_live_crypto_card_index_history_has_no_multi_day_hole import server_now, tail_hole

    grid = [_p(20, h) for h in range(0, 24, 3)]
    now = server_now("Wed, 23 Sep 2026 21:00:00 GMT")
    hole = tail_hole(grid, [], now, 12.0)
    assert hole is not None and round(hole[0], 1) == 72.0 and hole[1] == grid[-1]["t"], hole
    assert tail_hole(grid, [], server_now("Mon, 21 Sep 2026 06:00:00 GMT"), 12.0) is None, "9 h: inside the limit"
    # An open gap the response declares from the newest point on is the published behaviour.
    open_gap = [{"from": grid[-1]["t"], "to": None, "hours": None}]
    assert tail_hole(grid, open_gap, now, 12.0) is None
    closed_elsewhere = [{"from": "2026-09-10T00:00:00+00:00", "to": "2026-09-12T00:00:00+00:00", "hours": 48}]
    assert tail_hole(grid, closed_elsewhere, now, 12.0) is not None, "a gap declared elsewhere declares nothing here"
    assert server_now(None) is None and server_now("not a date") is None, "no Date: the tail is unread, not short"
    assert tail_hole([], [], now, 12.0) is None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_z_suffixed_time_reads_like_an_offset_one():
    series = [{"t": "2026-09-23T00:00:00Z", "index": 1.0}, {"t": "2026-09-23T13:00:00+00:00", "index": 1.0}]
    assert widest_gap(series)[0] == 13.0
