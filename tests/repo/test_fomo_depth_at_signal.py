"""V3 of the 2026-09-23 plan: the depth at the signal decides the buy, and the
depth at the exit caps the sell -- in every reader, as `ten_dollars` already
does.

`sellable` judged a coin by its NEWEST depth, a reading from the future: a
coin that rugged at hour six was taken out of its own history, and its loss
with it. Switching to the depth at the signal alone let those coins back in
with the dust prints they rugged to -- +73 848 % on a two-cent pool -- and
moved the stop study from -11.7 % to +85 917 %. So the two halves land
together: bought on what the pool held when it fired, sold for no more than
half of what it held at the exit (the quote side), against the clip.

And a path on which their terminal switched pair is a rug (every one of the
60 on record, 2026-09-23), kept as the loss it is: `stop_study` pays it no
gain, `compare` reads its peak only on the pair it was bought on.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from qa import fomo
from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
T0 = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
DONE = T0 + timedelta(hours=30)
DEEP = {"liquidity_usd": 50_000.0, "volume_h24": 90_000.0}


def _signal(key, price=1.0, at=T0, **extra):
    return {"type": "signal", "at": at.isoformat(), "key": key,
            "token_address": key.rsplit(":", 1)[0], "symbol": key[:6],
            "chain": "solana", "conviction": 70.0, "price_usd": price, **extra}


def _read(key, hours, price, entry=1.0, at=T0, kind="checkpoint", **extra):
    return {"type": kind, "key": key, "horizon": f"{hours:g}h",
            "at": (at + timedelta(hours=hours)).isoformat(), "price_usd": price,
            "return_pct": fomo.return_since_signal(entry, price), **extra}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_coin_is_judged_on_the_depth_it_had_when_it_fired():
    """No look-ahead: a pool drained two hours after the signal does not take
    the signal out -- it was bought, and the drain is the sale's problem. A
    delisting read after a signal is unknown for that signal, and a verdict
    for the next one."""
    rug, late, again = "0xrug:2026-09-13T12", "0xlate:2026-09-13T12", \
        "0xlate:2026-09-13T18"
    rows = [
        _signal(rug, **DEEP), _read(rug, 1, 2.0, **DEEP),
        _read(rug, 2, 3.0, liquidity_usd=0.01, volume_h24=0.2),
        _signal(late),
        {"type": "depth", "at": (T0 + timedelta(hours=5)).isoformat(),
         "token_address": "0xLATE", "listed": False},
        _signal(again, at=T0 + timedelta(hours=6)),
    ]
    said = fomo.basket(rows)
    assert (said["n_tradeable"], said["n_untradeable"],
            said["n_depth_unknown"]) == (1, 1, 1), said
    assert said["n_priced"] == 1, "the rug was bought when it fired"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_stats_and_the_basket_sell_for_no_more_than_the_pool_holds():
    """$10 in, a price read 100x up on a pool holding $4: half of it, $2, is
    all the sale fetches -- -80 %, not +9 900 %. A deep pool is not capped,
    and a reading that carries no liquidity (the diary before 2026-09-14)
    cannot be, and stays as it was."""
    dust, deep, old = ("0xdust:2026-09-13T12", "0xdeep:2026-09-13T12",
                       "0xold:2026-09-13T12")
    rows = [_signal(dust, **DEEP), _read(dust, 1, 100.0, liquidity_usd=4.0),
            _signal(deep, **DEEP), _read(deep, 1, 1.5, liquidity_usd=1e6),
            _signal(old), _read(old, 1, 1.2)]
    hour = fomo.stats(rows)["horizons"]["1h"]
    assert hour["resolved"] == 3
    assert hour["mean_pct"] == pytest.approx((-80.0 + 50.0 + 20.0) / 3), hour
    basket = fomo.basket(rows)
    assert basket["pnl_pct"] == pytest.approx((-80.0 + 50.0 + 20.0) / 3), basket
    (at_one,) = basket["by_horizon"]
    assert at_one["pnl_pct"] == pytest.approx((-80.0 + 50.0 + 20.0) / 3)
    assert basket["best"]["key"] == deep, "the dust print is not the best trade"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_stop_study_buys_on_the_signal_and_sells_into_the_exit_pool():
    """The coin that rugged later is in the study (it used to be dropped as
    untradeable off its last reading), and its 5x print on a $100 pool sells
    for $50 against the clip."""
    key = "0xrug:2026-09-13T12"
    rows = [_signal(key, radar_max_buy_5pct_usd=1e6, **DEEP),
            _read(key, 1, 1.0, **DEEP),
            _read(key, 24, 5.0, liquidity_usd=100.0, volume_h24=50.0)]
    said = fomo.stop_study(rows, stop_pct=10.0, cost_pct=0.0, now=DONE)
    assert said["n"] == 1, said["excluded"]
    assert said["mean_net_pct"] == pytest.approx(
        (50.0 / fomo.DEFAULT_CLIP_USD - 1.0) * 100.0), said
    ten = fomo.stop_study(rows, stop_pct=10.0, cost_pct=0.0, now=DONE,
                          clip_usd=10.0)
    assert ten["mean_net_pct"] == pytest.approx(400.0), (
        "$10 fits a $100 pool's $50: a small clip sells the whole print")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_switched_pair_is_kept_as_a_rug_in_the_stop_study_and_compare(
        tmp_path, monkeypatch):
    """A switched pair is kept and pays no gain in `stop_study`; in `compare`
    its peak is read only on the pair it was bought on -- a coin that tripled
    before the switch did pump, one that tripled only on the other pair did
    not."""
    up, down = "0xup:2026-09-13T12", "0xdown:2026-09-13T12"
    rows = [_signal(up, age_seconds=100.0, **DEEP),
            _read(up, 1, 1.0, age_seconds=3700.0),
            _read(up, 24, 3.0, age_seconds=900_000.0, **DEEP),
            _signal(down, age_seconds=100.0, **DEEP),
            _read(down, 1, 1.0, age_seconds=3700.0),
            _read(down, 24, 0.5, age_seconds=900_000.0, **DEEP)]
    said = fomo.stop_study(rows, stop_pct=10.0, cost_pct=0.0, now=DONE)
    assert said["n"] == 2 and said["switched"] == 2, said
    nets = sorted(t["net_pct"] for t in said["trades"])
    assert nets == pytest.approx([-50.0, 0.0]), nets

    tripled, never = "0xtri:2026-09-13T12", "0xnev:2026-09-13T12"
    # Each read to the window's end, as compare counts only such paths (M04,
    # deep pass 2026-10-25); the 24 h reading is on the other pair too.
    study = [_signal(tripled, age_seconds=100.0, **DEEP),
             _read(tripled, 10, 3.5, age_seconds=36_100.0),
             _read(tripled, 20, 0.2, age_seconds=900_000.0),
             _read(tripled, 24, 0.2, age_seconds=914_400.0),
             _signal(never, age_seconds=100.0, **DEEP),
             _read(never, 10, 1.2, age_seconds=36_100.0),
             _read(never, 20, 9.0, age_seconds=900_000.0),
             _read(never, 24, 9.0, age_seconds=914_400.0)]
    hot = fomo.compare(study, multiple=3.0, within_hours=24,
                       now=T0 + timedelta(hours=30))["hot"]
    assert (hot["n"], hot["hits"], hot["switched"]) == (2, 1, 2), hot
    assert "pair_changed" not in hot["excluded"], "kept, not left out"

    spec = importlib.util.spec_from_file_location(
        "fomo_watch_depth", REPO / "scripts" / "fomo_watch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    line = mod.say_stops({"stops": [said]})[0]
    assert "2 kept where their terminal switched pair" in line, line
    # A reading stored in the lab diary before this change still prints.
    old = {k: v for k, v in said.items() if k != "switched"}
    old["excluded"] = {**said["excluded"], "pair_changed": 3}
    line = mod.say_stops({"stops": [old]})[0]
    assert "3 left out where their terminal switched pair" in line, line
