"""The reading behind the Agent Tournaments "a running table does not go dead" check (2026-10-12, T-0043).

Table 2 (Pro, started 2026-10-11 16:46 UTC) answered volume_usdc 5604.4 at 08:20 and again at 20:25 UTC
on 2026-10-12, every standing unchanged, while table 11 -- the same house bots, two hours old -- had
closed 20 trades per bot. Its own `race` lines say when it stopped: every seat's ROI point is the
same from index 14 on, 13.7 h of a 168 h table. These cases pin how that is read, so a quiet seat
cannot be mistaken for a quiet table, a table that starts slowly is not a stop, and a stop that
the table has since traded out of is still read from its history.
"""

from qa.marks import SafetyTier, qa
from tests.rest.test_agent_tournaments_running_table_keeps_trading import longest_still_hours

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
def test_a_stop_the_table_traded_out_of_is_still_in_its_history():
    """Why the rule reads the whole race and not its tail: a daily allowance leaves a dead stretch
    that the next morning's trades do not undo, and a check that read only the tail would pass at
    00:01 and fail at 03:00 on the same table."""
    stopped_then_resumed = _line([164.2, 150] + [121.1] * 16 + [130, 131, 132])
    assert longest_still_hours(_race(stopped_then_resumed), 7) >= 15.0


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
