"""The reading behind the Agent Tournaments "a running table does not go dead" check (2026-10-12, T-0043).

Table 2 (Pro, started 2026-10-11 16:46 UTC) answered volume_usdc 5604.4 at 08:20 and again at 20:25 UTC
on 2026-10-12, every standing unchanged, while table 11 -- the same house bots, two hours old -- had
closed 20 trades per bot. Its own `race` lines say when it stopped: every seat's ROI point is the
same from index 14 on, 13.7 h of a 168 h table. These cases pin how that is read, so a quiet seat
cannot be mistaken for a quiet table, a table that starts slowly is not a stop, and a stop that
the table has since traded out of is still read while it sits inside the last 48 h of its history (T-0059:
a window, so that a real fix by Cymetica clears the read in two days, not seven).
"""

from qa.marks import SafetyTier, qa
from tests.rest.test_agent_tournaments_running_table_keeps_trading import WINDOW_H, longest_still_hours

X0, X1 = 54.0, 1160.0                       # race.x0 / race.x1 on table 2; 7 days wide
PX_PER_H = (X1 - X0) / (7 * 24)             # 6.58 px an hour


def _line(ys, step=PX_PER_H):
    return {"seat_id": 1, "points": " ".join(f"{X0 + i * step:.1f},{y}" for i, y in enumerate(ys))}


def _race(*lines):
    return {"x0": X0, "x1": X1, "lines": list(lines)}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_seat_flat_for_thirteen_hours_reads_thirteen_hours():
    moving_then_flat = _line([164.2, 150, 140] + [121.1] * 14)         # last change at index 3 of 0..16
    never_moved = _line([164.2] * 17)
    hours = longest_still_hours(_race(moving_then_flat, never_moved), 7)
    assert abs(hours - 13.0) < 0.2, hours


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_one_seat_still_trading_leaves_no_long_stretch():
    flat = _line([164.2, 150] + [121.1] * 20)
    trading = _line([164.2, 150] + [121.1] * 10 + [140, 141, 142, 143, 144, 145, 146, 147, 148, 149])
    assert longest_still_hours(_race(flat, trading), 7) <= 11.2, "one seat moving at hour 12 splits the stretch"
    keeps_moving = _line([164.2, 150] + [100 + i for i in range(20)])
    assert longest_still_hours(_race(flat, keeps_moving), 7) <= 1.2


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_stop_the_table_traded_out_of_is_still_in_its_window():
    """Why the rule reads a window and not the tail: a daily allowance leaves a dead stretch that
    the next morning's trades do not undo, and a check that read only the tail would pass at
    00:01 and fail at 03:00 on the same table."""
    stopped_then_resumed = _line([164.2, 150] + [121.1] * 16 + [130, 131, 132])
    assert longest_still_hours(_race(stopped_then_resumed), 7) >= 15.0


def _daily(burst_h, offset_h, total_h, gap_first_h=0):
    """A seat that closes trades only in the first `burst_h` hours of each 24 h cycle that starts at
    `offset_h` -- the 20-a-UTC-day regime, one ROI point an hour."""
    ys, y = [], 164.2
    for h in range(total_h + 1):
        if h and gap_first_h <= h and (h - offset_h) % 24 < burst_h:
            y += 3.0
        ys.append(y)
    return _line(ys)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_daily_allowance_fails_every_read_whatever_the_hour():
    """Requirement (a), T-0059: 20 trades a UTC day leaves a quiet stretch of up to 24 h that sits
    whole in any WINDOW_H, so a read at any hour of day 2 to 7 fails, not just the one after midnight."""
    for burst_h in (1, 2, 6):
        for read_h in range(WINDOW_H, 7 * 24 + 1):
            hours = longest_still_hours(_race(_daily(burst_h, 0, read_h)), 7)
            assert hours >= 12.0, (burst_h, read_h, hours)
    # table 5's first day was dead for longer than a day, and still fails
    assert longest_still_hours(_race(_daily(1, 0, 100, gap_first_h=30)), 7) >= 12.0


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_fix_clears_the_read_within_the_window():
    """Requirement (b), T-0059: a table dead 23 h a day for four days that trades every hour from
    hour F on reads clean once the fix is WINDOW_H old -- not when the table leaves the lobby."""
    fix_h = 96
    for read_h in range(fix_h + WINDOW_H, 7 * 24 + 1):
        ys = _daily(1, 0, fix_h)["points"].split()
        y = float(ys[-1].split(",")[1])
        hourly = [y + 2.0 * i for i in range(1, read_h - fix_h + 1)]
        line = _line([float(p.split(",")[1]) for p in ys] + hourly)
        assert longest_still_hours(_race(line), 7) < 12.0, read_h
    # and the window is what clears it: the same table read from the start still fails
    ys = _daily(1, 0, fix_h)["points"].split()
    line = _line([float(p.split(",")[1]) for p in ys] + [300 + 2.0 * i for i in range(1, 49)])
    assert longest_still_hours(_race(line), 7, window_h=None) >= 12.0
    assert longest_still_hours(_race(line), 7) < 12.0


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_window_is_two_days_and_no_less():
    """A quiet stretch of up to 24 h sits whole in 48 h and not in a shorter window; the number is
    fixed here so that narrowing it cannot quietly let a daily allowance through."""
    assert 48 <= WINDOW_H <= 60, WINDOW_H


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_slow_start_is_not_a_stop():
    """Nothing moves for the first 14 h, then a seat trades: the run before the first move is not a stretch."""
    slow = _line([164.2] * 15 + [150, 140, 130])
    assert longest_still_hours(_race(slow), 7) <= 1.2


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_seat_that_never_traded_is_not_a_stop():
    """A member with 0 trades is flat from the first point; a table nobody traded on has not stopped."""
    never_moved = _line([164.2] * 20)
    assert longest_still_hours(_race(never_moved), 7) is None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_unreadable_race_is_none_not_zero():
    assert longest_still_hours({}, 7) is None
    assert longest_still_hours({"x0": X0, "x1": X1, "lines": [{"points": "garbage"}]}, 7) is None
    assert longest_still_hours({"x0": X0, "x1": X0, "lines": [_line([1, 2])]}, 7) is None, "zero-width axis"
    assert longest_still_hours(_race(_line([1, 2, 3])), 0) is None
