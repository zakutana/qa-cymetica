"""Does FOMO Radar's `hot` signal actually predict a memecoin moving?

All pure, no network -- `scripts/fomo_watch.py` is the two live rounds that
call these. Fixtures use the real field names captured live on 2026-09-13:
`token_address`, `hot`, `new_qualified_buyers_15m` from FOMO Radar; `price`
from memecoin-terminal's `search`.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from qa import fomo
from qa.marks import SafetyTier, qa

T0 = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)


def _row(token="0xabc", hot=True, symbol="DOGEX"):
    return {"token_address": token, "hot": hot, "symbol": symbol,
           "chain": "robinhood", "conviction": 0.42}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_signal_key_is_the_token_and_the_hour_it_went_hot():
    assert fomo.signal_key("0xABC", T0) == "0xabc:2026-09-13T12"
    assert fomo.signal_key("0xabc", T0 + timedelta(minutes=59)) == (
        "0xabc:2026-09-13T12")
    assert fomo.signal_key("0xabc", T0 + timedelta(hours=1)) == (
        "0xabc:2026-09-13T13")
    assert fomo.signal_key(None, T0) is None
    assert fomo.signal_key("0xabc", "not a date") is None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_new_signals_dedupes_by_token_and_hour_not_by_poll():
    hot_rows = [_row("0xabc"), _row("0xdef"), _row("0xabc")]  # same poll, twice
    found = fomo.new_signals(hot_rows, tracked_keys=set(), at=T0)
    assert [r["token_address"] for r in found] == ["0xabc", "0xdef"], (
        "the same token twice in one poll is one signal, not two")

    # A token already tracked THIS hour is not tracked again; a not-hot row
    # is not a signal at all, whatever else it carries.
    already = {"0xabc:2026-09-13T12"}
    found = fomo.new_signals(
        [_row("0xabc"), _row("0xghi", hot=False)], tracked_keys=already, at=T0)
    assert found == []

    # But the SAME token an hour later is a new signal.
    found = fomo.new_signals([_row("0xabc")], tracked_keys=already,
                             at=T0 + timedelta(hours=1))
    assert len(found) == 1


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_due_checkpoints_fires_only_after_its_own_horizon():
    signal = {"key": "0xabc:2026-09-13T12", "at": T0.isoformat()}
    # Not due at all, one hour in.
    assert fomo.due_checkpoints([signal], done={}, now=T0 + timedelta(minutes=30)) == []

    # 1h is due, 6h and 24h are not.
    due = fomo.due_checkpoints([signal], done={}, now=T0 + timedelta(hours=1, minutes=1))
    assert [h for _, h in due] == ["1h"]

    # 1h already recorded -- not offered again, even though it is still due.
    due = fomo.due_checkpoints([signal], done={"0xabc:2026-09-13T12": {"1h"}},
                               now=T0 + timedelta(hours=1, minutes=1))
    assert due == []

    # A signal with no readable timestamp is never due -- a gap is not a loss.
    broken = {"key": "0xdef:x", "at": "not a date"}
    assert fomo.due_checkpoints([broken], done={}, now=T0 + timedelta(days=2)) == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_return_since_signal_is_ours_not_their_rolling_window():
    assert fomo.return_since_signal(1.0, 1.5) == 50.0
    assert fomo.return_since_signal(1.0, 0.5) == -50.0
    # Not zero: unmeasurable, because their price was never captured at the
    # signal moment or came back unreadable.
    assert fomo.return_since_signal(None, 1.5) is None
    assert fomo.return_since_signal(0, 1.5) is None
    assert fomo.return_since_signal(1.0, None) is None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_stats_reads_the_hit_threshold_as_a_parameter_not_a_constant():
    rows = [
        {"type": "signal", "key": "a", "symbol": "DOGEX", "conviction": 0.9},
        {"type": "signal", "key": "b", "symbol": "PEPEX", "conviction": 0.1},
        {"type": "checkpoint", "key": "a", "horizon": "1h", "return_pct": 30.0},
        {"type": "checkpoint", "key": "b", "horizon": "1h", "return_pct": -10.0},
        {"type": "checkpoint", "key": "a", "horizon": "6h", "return_pct": 5.0},
    ]
    said = fomo.stats(rows, hit_threshold=20.0)
    assert said["tracked"] == 2
    one_hour = said["horizons"]["1h"]
    assert one_hour["resolved"] == 2
    assert one_hour["hit_rate"] == 0.5, "one of two crossed the +20% threshold"
    assert one_hour["mean_pct"] == 10.0
    assert one_hour["top"][0]["symbol"] == "DOGEX"

    # A different threshold reads a different hit rate off the SAME data --
    # the number is not baked into how the rows were written.
    stricter = fomo.stats(rows, hit_threshold=35.0)
    assert stricter["horizons"]["1h"]["hit_rate"] == 0.0

    assert fomo.stats([]) == {
        "tracked": 0, "hit_threshold": fomo.DEFAULT_HIT_THRESHOLD, "horizons": {}}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_one_token_appears_once_in_best_and_worst():
    """A token still hot at 06:00 and again at 07:00 is two tracked signals --
    correct, and right for the hit rate, which is a rate over signals.

    It is wrong for "best and worst", which a reader takes as a list of
    TOKENS. Seen on the console 2026-09-13: the same coin twice at the top
    with the identical +1262.3%, and ASTRO twice below it, so five rows showed
    three coins and the page looked broken to the one person reading it.

    The newest signal for a token wins, because that is the one whose return
    is measured over the freshest entry price.
    """
    rows = []
    for hour, ret in (("06", 1262.3), ("07", 1262.3), ("06", 40.5)):
        token = "0xaaa" if ret > 100 else "0xbbb"
        key = f"{token}:2026-09-13T{hour}"
        rows.append({"type": "signal", "key": key, "token_address": token,
                     "symbol": "NIU" if ret > 100 else "POK",
                     "conviction": 88.3, "price_usd": 1.0})
        rows.append({"type": "checkpoint", "key": key, "horizon": "1h",
                     "price_usd": 2.0, "return_pct": ret})

    one = fomo.stats(rows)["horizons"]["1h"]
    shown = [c["symbol"] for c in one["top"]] + [c["symbol"] for c in one["bottom"]]
    assert len(shown) == len(set(shown)), f"a token listed twice: {shown}"
    assert set(shown) == {"NIU", "POK"}

    # The RATE still counts both signals -- it is a rate over signals fired,
    # and collapsing them would quietly change what the number means.
    assert one["resolved"] == 3, one["resolved"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_hour_of_the_first_day_is_a_checkpoint():
    """[operator 2026-09-13] *"chci videt proswte graf vyvoje ceny po hodinach
    pro kazdy. staci pristich 24h vyvoje"*.

    Three readings (1h, 6h, 24h) cannot draw a curve; they draw two line
    segments, and a memecoin that went up 900% in hour three and gave it all
    back by hour six looks identical to one that did nothing. So the whole
    first day is sampled hour by hour.

    24 checkpoints per signal against their memecoin-terminal, whose own
    server cache is 180s -- spread across a day this is nothing, and the
    register is what stops any hour being asked twice.
    """
    assert fomo.HORIZONS_HOURS == tuple(float(h) for h in range(1, 25)), (
        fomo.HORIZONS_HOURS)

    t0 = T0
    signal = {"key": "0xabc:2026-09-13T12", "at": t0.isoformat()}

    # Just after each mark, that hour and only that hour is offered. Hours 1
    # and 2 are not back-offered at 3.1h -- their prices are gone, and taking
    # them now would file the 3h price under 1h. See the tolerance test below.
    due = fomo.due_checkpoints([signal], {}, now=t0 + timedelta(hours=3.1))
    assert [label for _, label in due] == ["3h"], due

    # Nothing is asked twice: an hour already recorded drops out and the tick
    # then has nothing to do for this signal until the next mark.
    done = {"0xabc:2026-09-13T12": {"3h"}}
    due = fomo.due_checkpoints([signal], done, now=t0 + timedelta(hours=3.1))
    assert due == [], due

    # And the day ends: hour 25 is not a horizon, however long we wait.
    due = fomo.due_checkpoints([signal], {}, now=t0 + timedelta(hours=24.1))
    assert [label for _, label in due] == ["24h"], due
    assert fomo.due_checkpoints([signal], {},
                                now=t0 + timedelta(hours=100)) == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_each_token_gets_its_own_hourly_curve():
    """What the console draws: one series per token, hour by hour.

    `stats()` answers "did the signal work" in aggregate; a curve is a
    different question and needs the points, not the summary. Gaps are real
    -- a token unpriced at hour 4 is a hole, not a zero -- so the series
    carries None there rather than closing over it, and the page can then
    draw a break instead of a straight line through nothing.
    """
    rows = []
    key = "0xabc:2026-09-13T12"
    rows.append({"type": "signal", "key": key, "token_address": "0xabc",
                 "symbol": "DOGEX", "conviction": 71.0, "price_usd": 1.0})
    for hour, ret in ((1, 10.0), (2, 40.0), (4, None), (5, -12.0)):
        rows.append({"type": "checkpoint", "key": key, "horizon": f"{hour}h",
                     "price_usd": None if ret is None else 1 + ret / 100,
                     "return_pct": ret})

    series = fomo.curves(rows)
    assert len(series) == 1
    curve = series[0]
    assert curve["symbol"] == "DOGEX" and curve["conviction"] == 71.0
    assert curve["points"][:2] == [(1, 10.0), (2, 40.0)]
    assert (3, None) in curve["points"], "an hour never sampled is a gap"
    assert (4, None) in curve["points"], "an unpriced hour is a gap, not a 0"
    assert (5, -12.0) in curve["points"]
    assert curve["last"] == -12.0, "the newest reading, for sorting"
    assert curve["peak"] == 40.0, "the best it ever got, which is the story"

    # Curves are ordered so the reader meets the big movers first.
    more = rows + [
        {"type": "signal", "key": "0xbbb:2026-09-13T12", "token_address":
         "0xbbb", "symbol": "TINY", "conviction": 20.0, "price_usd": 1.0},
        {"type": "checkpoint", "key": "0xbbb:2026-09-13T12", "horizon": "1h",
         "price_usd": 1.01, "return_pct": 1.0}]
    assert [c["symbol"] for c in fomo.curves(more)] == ["DOGEX", "TINY"]

    # A signal with no checkpoint at all draws nothing rather than a flat line
    # at zero, which would read as "the signal did nothing".
    only = [{"type": "signal", "key": "0xccc:2026-09-13T12",
             "token_address": "0xccc", "symbol": "NEW", "price_usd": 1.0}]
    assert fomo.curves(only) == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_hour_missed_is_never_filled_with_a_later_price():
    """The worst thing this module could do, and it nearly did it.

    `resolve()` reads the price NOW and files it under whichever horizon is
    due. That is correct when the horizon just came round and a lie when it
    did not: on 2026-09-13 the horizons went from (1, 6, 24) to every hour,
    and 85 signals seven hours old suddenly had hours 2, 3, 4 and 5 "due".
    Resolving them would have written the seven-hour price into the two-hour
    slot, hundreds of times, and drawn the curve the operator had just asked
    for out of numbers that were never observed.

    So a horizon is only due while it is still NEAR -- `DUE_TOLERANCE_HOURS`
    after it comes round. Past that the hour is gone and stays a gap, which
    `curves()` already draws as a break in the line. A hole in a measurement
    is honest; a fabricated point is not, and a fabricated point that looks
    plausible is the worst of the three.
    """
    t0 = T0
    signal = {"key": "0xabc:2026-09-13T12", "at": t0.isoformat()}

    # Just past the first hour: due, obviously.
    due = fomo.due_checkpoints([signal], {}, now=t0 + timedelta(hours=1.1))
    assert [l for _, l in due] == ["1h"], due

    # Seven hours later with only 1h and 6h recorded: the hours in between
    # are NOT offered, because their prices are gone.
    done = {"0xabc:2026-09-13T12": {"1h", "6h"}}
    due = fomo.due_checkpoints([signal], done, now=t0 + timedelta(hours=7.0))
    assert [l for _, l in due] == ["7h"], (
        f"a stale hour was offered for filling with a later price: {due}")

    # The boundary itself, both sides of it.
    late = t0 + timedelta(hours=2 + fomo.DUE_TOLERANCE_HOURS - 0.01)
    assert "2h" in [l for _, l in fomo.due_checkpoints([signal], {}, now=late)]
    later = t0 + timedelta(hours=2 + fomo.DUE_TOLERANCE_HOURS + 0.01)
    assert "2h" not in [l for _, l in fomo.due_checkpoints([signal], {},
                                                           now=later)]
