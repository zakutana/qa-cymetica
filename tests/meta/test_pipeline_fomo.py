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
