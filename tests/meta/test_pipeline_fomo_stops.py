"""Three changes to the memecoin study, from the plan agreed 2026-09-22.

1. Checkpoints at +15 and +30 minutes, each with a due window of its own --
   half the horizon, at most 0.75 h -- so a +15 min reading taken forty
   minutes late is a gap, not a +15 min reading.
2. A signal that fired with no price is quoted once more on the next round,
   as a separate `entry` row with its own `at`. A later entry is a different
   entry: no reader takes it for the signal's price.
3. `stop_study`: a stop and a target over each hot signal's checkpoint path,
   exiting at the first READING past either -- never at the level itself,
   because we only see the path at the points.

NEXT.md, 2026-09-21: *the simulation enters at the price the feed publishes
when it flags, and the first price we verify is a median 67 minutes later*.
These are what would narrow that.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from qa import fomo
from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
T0 = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)
DONE = T0 + timedelta(hours=30)   # every first-day window has closed


def _signal(key="0xabc:2026-09-13T12", price=1.0, at=T0, **extra):
    return {"type": "signal", "at": at.isoformat(), "key": key,
            "token_address": key.rsplit(":", 1)[0], "symbol": "DOGEX",
            "chain": "solana", "conviction": 70.0, "price_usd": price, **extra}


def _path(key, entry, points, at=T0):
    """One checkpoint per (hours, price), read exactly at its mark."""
    out = []
    for hours, price in points:
        out.append({"type": "checkpoint", "key": key, "horizon": f"{hours:g}h",
                    "at": (at + timedelta(hours=hours)).isoformat(),
                    "price_usd": price,
                    "return_pct": fomo.return_since_signal(entry, price)})
    return out


# --- 1. sub-hour checkpoints ------------------------------------------------

@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_fifteen_and_thirty_minutes_are_checkpoints_with_their_own_window():
    """+15 min and +30 min are horizons, and each is due only while it is
    still near: half the horizon, never more than the 0.75 h every hour from
    the second on keeps.

    Without the per-horizon window a +15 min checkpoint was due until +60
    minutes -- a reading taken three times later than its label, filed under
    it."""
    assert fomo.HORIZONS_HOURS[:3] == (0.25, 0.5, 1.0), fomo.HORIZONS_HOURS
    assert fomo.due_tolerance(0.25) == 0.125
    assert fomo.due_tolerance(0.5) == 0.25
    assert fomo.due_tolerance(1.0) == 0.5
    assert fomo.due_tolerance(2.0) == fomo.DUE_TOLERANCE_HOURS == 0.75
    assert fomo.due_tolerance(24.0) == 0.75

    signal = {"key": "0xabc:2026-09-13T12", "at": T0.isoformat()}

    def due_at(minutes):
        return [label for _, label in fomo.due_checkpoints(
            [signal], {}, now=T0 + timedelta(minutes=minutes))]

    assert due_at(10) == []
    assert due_at(16) == ["0.25h"]
    assert due_at(22) == ["0.25h"]
    assert due_at(23) == [], "7.5 minutes is the whole of a +15 min window"
    assert due_at(31) == ["0.5h"]
    assert due_at(46) == [], "a +30 min reading forty minutes late is a gap"
    # The first hour's window is now half an hour, not three quarters.
    assert due_at(61) == ["1h"]
    assert due_at(95) == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_reader_drops_a_sub_hour_reading_by_the_same_window():
    """The writer refuses and the reader drops by ONE rule. A +15 min row
    read at +40 min is not a +15 min reading, whoever wrote it."""
    signal = _signal()
    on_time = {"type": "checkpoint", "key": signal["key"], "horizon": "0.25h",
               "at": (T0 + timedelta(minutes=20)).isoformat()}
    late = {**on_time, "at": (T0 + timedelta(minutes=40)).isoformat()}
    assert fomo.read_late(signal, on_time) is False
    assert fomo.read_late(signal, late) is True
    # Hour two keeps its three quarters.
    two = {**on_time, "horizon": "2h",
           "at": (T0 + timedelta(hours=2.7)).isoformat()}
    assert fomo.read_late(signal, two) is False


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_hourly_curve_does_not_fold_the_minutes_into_hour_zero():
    """`curves()` is the hourly picture the console draws 24 hours wide.
    "0.25h" parsed as `int(0.25)` is hour 0 -- two readings overwriting one
    slot the page never draws. They stay out of the curve; they are in the
    diary for the stop study."""
    key = "0xabc:2026-09-13T12"
    rows = [_signal(key)] + _path(key, 1.0, [(0.25, 3.0), (0.5, 4.0),
                                             (1, 1.1), (2, 1.2)])
    curve = fomo.curves(rows)[0]
    assert [h for h, _ in curve["points"]] == [1, 2], curve["points"]
    assert round(curve["peak"], 6) == 20.0, (
        "the +300 % at fifteen minutes is not in the hourly curve", curve)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_by_horizon_sorts_the_minutes_before_the_first_hour():
    key = "0xabc:2026-09-13T12"
    rows = [_signal(key)] + _path(key, 1.0, [(1, 1.1), (0.5, 1.05),
                                             (0.25, 1.02)])
    labels = [h["horizon"] for h in fomo.basket(rows)["by_horizon"]]
    assert labels == ["0.25h", "0.5h", "1h"], labels


# --- 2. a retried entry is its own row --------------------------------------

def _watch(tmp_path, monkeypatch):
    import importlib

    import qa.state

    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    importlib.reload(qa.state)
    spec = importlib.util.spec_from_file_location(
        "fomo_watch_stops_under_test", REPO / "scripts" / "fomo_watch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _client(handler):
    from qa.client import build_mock_client

    return build_mock_client(handler, timeout=5.0)


def _search(price):
    def handler(request):
        assert "memecoin-terminal/search" in str(request.url)
        return httpx.Response(200, json={"rows": [
            {"address": request.url.params.get("q"), "price_usd": price,
             "liquidity_usd": 5000.0}]})
    return handler


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_signal_with_no_price_is_quoted_once_more_as_its_own_entry(
        tmp_path, monkeypatch):
    """748 of 2571 signals carried `price_usd: null` on 2026-09-22. The next
    round quotes them again, ONCE, and writes what it read as an `entry` row
    with the time it was read. The signal row is never touched and no
    checkpoint's return is computed from the later price: a price read ten
    minutes on is a different entry, and taken for the original it would
    credit the signal with ten minutes it never had."""
    mod = _watch(tmp_path, monkeypatch)
    mod._append(_signal("0xnil:2026-09-13T12", price=None))
    mod._append(_signal("0xhas:2026-09-13T12", price=0.5))
    # Hours old: its moment is gone, and the backlog is not re-quoted.
    mod._append(_signal("0xold:2026-09-13T09", price=None,
                        at=T0 - timedelta(hours=3)))

    first = mod.resolve(_client(_search(0.002)),
                        now=T0 + timedelta(minutes=10))
    entries = [r for r in mod.load() if r["type"] == "entry"]
    assert [e["key"] for e in entries] == ["0xnil:2026-09-13T12"], entries
    entry = entries[0]
    assert entry["price_usd"] == 0.002
    assert entry["at"] == (T0 + timedelta(minutes=10)).isoformat(), (
        "the entry carries the moment IT was read, not the signal's")
    assert first.get("entries") == 1, first

    # Once. A second round does not quote it again.
    mod.resolve(_client(_search(0.003)), now=T0 + timedelta(minutes=12))
    assert len([r for r in mod.load() if r["type"] == "entry"]) == 1

    # The signal row still says it had no price, and its checkpoints stay
    # unmeasured rather than measured from the retry.
    rows = mod.load()
    nil = [r for r in rows if r.get("key") == "0xnil:2026-09-13T12"
           and r["type"] == "signal"]
    assert nil[0]["price_usd"] is None
    mod.resolve(_client(_search(0.004)), now=T0 + timedelta(minutes=16))
    quarter = [r for r in mod.load() if r["type"] == "checkpoint"
               and r["key"] == "0xnil:2026-09-13T12"]
    assert quarter and quarter[0]["return_pct"] is None, quarter


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_retry_that_could_not_be_read_is_tried_again_not_written(
        tmp_path, monkeypatch):
    """Rule 8: a 503 on the retry is not a token with no price. Nothing is
    written and the next round inside the hour tries again."""
    mod = _watch(tmp_path, monkeypatch)
    mod._append(_signal("0xnil:2026-09-13T12", price=None))
    mod.resolve(_client(lambda r: httpx.Response(503)),
                now=T0 + timedelta(minutes=5))
    assert [r for r in mod.load() if r["type"] == "entry"] == []
    mod.resolve(_client(_search(0.002)), now=T0 + timedelta(minutes=8))
    assert len([r for r in mod.load() if r["type"] == "entry"]) == 1


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_entry_counts_say_what_the_retry_bought():
    key = "0xnil:2026-09-13T12"
    rows = [_signal(key, price=None), _signal("0xhas:2026-09-13T12", price=1.0),
            _signal("0xgone:2026-09-13T12", price=None),
            {"type": "entry", "key": key, "price_usd": 0.002,
             "at": (T0 + timedelta(minutes=20)).isoformat()},
            {"type": "entry", "key": "0xgone:2026-09-13T12", "price_usd": None,
             "at": (T0 + timedelta(minutes=20)).isoformat()}]
    said = fomo.entries(rows)
    assert said["signals"] == 3
    assert said["unpriced_at_signal"] == 2
    assert said["retried"] == 2
    assert said["priced_on_retry"] == 1
    assert said["median_delay_min"] == 20.0

    # And no reader takes the retry for the signal's price.
    assert fomo.basket(rows)["n_priced"] == 0
    assert fomo.stop_study(rows + _path(key, None, [(1, 0.004)]),
                           stop_pct=10.0, now=DONE)["n"] == 0


# --- 3. the stop study ------------------------------------------------------

@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_stop_exits_at_the_first_reading_past_it_not_at_its_level():
    """Entry 1.00, stop -10 %. The path reads 0.95 then 0.60: the stop is
    crossed somewhere between the two, and all we know is the 0.60. So the
    trade exits at -40 %, never at -10 % -- a fill at the stop level is a
    price nobody saw."""
    key = "0xabc:2026-09-13T12"
    rows = [_signal(key)] + _path(key, 1.0, [(1, 0.95), (2, 0.60), (3, 3.0), (24, 3.0)])
    said = fomo.stop_study(rows, stop_pct=10.0, cost_pct=0.0, now=DONE)
    assert said["n"] == 1
    assert round(said["mean_net_pct"], 6) == -40.0, said
    assert said["exits"] == {"stop": 1, "target": 0, "last": 0}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_target_exits_at_the_reading_and_no_exit_holds_to_the_last():
    up, flat = "0xup:2026-09-13T12", "0xflat:2026-09-13T12"
    rows = ([_signal(up), _signal(flat)]
            + _path(up, 1.0, [(1, 1.5), (2, 2.4), (3, 0.1), (24, 0.1)])
            + _path(flat, 1.0, [(1, 0.97), (24, 1.05)]))
    said = fomo.stop_study(rows, stop_pct=10.0, target_pct=100.0,
                           cost_pct=0.0, now=DONE)
    assert said["n"] == 2
    assert said["exits"] == {"stop": 0, "target": 1, "last": 1}
    # +140 at the reading past the target, +5 held to the last checkpoint.
    assert round(said["mean_net_pct"], 6) == round((140.0 + 5.0) / 2, 6), said
    assert said["win_rate"] == 1.0

    # RM02 (deep pass of 2026-09-24, 3/3): a path the loop stopped reading
    # before the day was out was SOLD at its last reading as if held the day
    # -- 308 of 1333 trades, the -10 % study -12.1 % where it is -18.8 %.
    # `ten_dollars` leaves the same case out as unread; so does this.
    cut = "0xcut:2026-09-13T12"
    said = fomo.stop_study(rows + [_signal(cut)]
                           + _path(cut, 1.0, [(1, 0.97), (6, 1.30)]),
                           stop_pct=10.0, target_pct=100.0, cost_pct=0.0, now=DONE)
    assert said["n"] == 2, said
    assert said["excluded"]["unread_at_end"] == 1, said["excluded"]

    # RM05 (deep pass of 2026-09-24, 3/3): and a stop or a target is held to
    # the same rule. Counted off a path the loop stopped reading, the trades
    # that fell early stayed and the ones that would have ridden the day went:
    # one rule for every exit, the path is read to its end.
    short = "0xshort:2026-09-13T12"
    said = fomo.stop_study(rows + [_signal(short)]
                           + _path(short, 1.0, [(1, 0.5), (6, 0.4)]),
                           stop_pct=10.0, target_pct=100.0, cost_pct=0.0, now=DONE)
    assert said["n"] == 2, said
    assert said["excluded"]["unread_at_end"] == 1, said["excluded"]
    # READ, not priced: a path the loop did read to the end and found no
    # price on is a coin that stopped trading -- 34 of the 410 stops this
    # rule would otherwise have dropped, the loss the stop exists for. Kept.
    dead = "0xdead:2026-09-13T12"
    said = fomo.stop_study(rows + [_signal(dead)] + _path(dead, 1.0, [(1, 0.5)]) + [
        {"type": "checkpoint", "key": dead, "horizon": "24h",
         "at": (T0 + timedelta(hours=24)).isoformat(), "price_usd": None,
         "return_pct": None}],
        stop_pct=10.0, target_pct=100.0, cost_pct=0.0, now=DONE)
    assert said["n"] == 3, said
    assert said["excluded"]["unread_at_end"] == 0, said["excluded"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_cost_comes_from_their_max_buy_against_our_clip():
    """`radar_max_buy_5pct_usd` is what the radar says moves the price 5 %.
    A clip that size pays 5 % a side; a clip a quarter of it pays a quarter
    of that. A signal the radar published no depth for is charged the
    default round trip, and counted, so the reader sees how much of the
    figure stands on the assumption."""
    deep, bare = "0xdeep:2026-09-13T12", "0xbare:2026-09-13T12"
    rows = ([_signal(deep, radar_max_buy_5pct_usd=4 * fomo.DEFAULT_CLIP_USD),
             _signal(bare)]
            + _path(deep, 1.0, [(1, 1.0), (24, 1.0)])
            + _path(bare, 1.0, [(1, 1.0), (24, 1.0)]))
    said = fomo.stop_study(rows, stop_pct=10.0, now=DONE)
    nets = sorted(t["net_pct"] for t in said["trades"])
    assert [round(n, 6) for n in nets] == [
        -fomo.DEFAULT_ROUND_TRIP_COST_PCT, -2.5], nets
    assert said["cost"]["assumed"] == 1, said["cost"]
    # A fixed cost, when asked for, is charged to every trade alike.
    fixed = fomo.stop_study(rows, stop_pct=10.0, cost_pct=3.0, now=DONE)
    assert [round(t["net_pct"], 6) for t in fixed["trades"]] == [-3.0, -3.0]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_only_closed_windows_and_readings_taken_in_time_are_traded():
    """An open window is left out: counted, it would see the early stops and
    none of the late recoveries. A checkpoint filed under an hour it was not
    read in is not on the path. A signal with no price is not a trade."""
    closed, open_ = "0xa:2026-09-13T12", "0xb:2026-09-14T11"
    nil = "0xc:2026-09-13T12"
    late_row = {"type": "checkpoint", "key": closed, "horizon": "1h",
                "at": (T0 + timedelta(hours=2.6)).isoformat(),
                "price_usd": 0.1, "return_pct": -90.0}
    rows = ([_signal(closed), _signal(open_, at=T0 + timedelta(hours=23)),
             _signal(nil, price=None), late_row]
            + _path(closed, 1.0, [(3, 1.2), (24, 1.3)])
            + _path(open_, 1.0, [(1, 0.5)], at=T0 + timedelta(hours=23)))
    said = fomo.stop_study(rows, stop_pct=10.0, cost_pct=0.0, now=DONE)
    assert said["n"] == 1
    assert round(said["mean_net_pct"], 6) == 30.0, (
        "the late 1h row at 0.1 would have stopped this trade out", said)
    assert said["excluded"]["window_open"] == 1
    assert said["excluded"]["unpriced"] == 1


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_study_counts_the_trades_a_sub_hour_point_could_have_saved():
    """What the +15/+30 min points are for: a stop can only fire at a point,
    so a trade whose path had one before its exit is one where the minutes
    mattered. And the line that every positive figure is an upper bound
    travels with the numbers."""
    dense, sparse = "0xd:2026-09-13T12", "0xs:2026-09-13T12"
    rows = ([_signal(dense), _signal(sparse)]
            + _path(dense, 1.0, [(0.25, 0.8), (1, 0.5), (24, 0.5)])
            + _path(sparse, 1.0, [(1, 0.5), (24, 0.4)]))
    said = fomo.stop_study(rows, stop_pct=10.0, cost_pct=0.0, now=DONE)
    assert said["dense_before_exit"] == 1, said
    assert "unmeasured" in said["caveat"] and "upper bound" in said["caveat"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_path_that_changes_pair_pays_no_gain_and_a_rug_is_a_trade():
    """The first run over the real diary read +31 620 % a trade, and the top
    of it was two tokens. PUMP, live, 2026-09-19..20: 0.0043 at the signal,
    21.72 an hour later, 0.0044 at six hours, and back and forth all day --
    with the pair's `age_seconds` flipping between 37.2 M and 17.6 M in step.
    One pair cannot age twenty million seconds backwards in an hour: their
    terminal answered a DIFFERENT pair for the same address. JUP did the same
    at 1 424 against 0.28.

    A pair whose age moves more than an hour away from the clock between two
    readings is a different pair, and its price is not this coin's -- so the
    path pays no gain, counted as `switched`. It was left out until V3
    (2026-09-23): every switch on record was the main pool drained, a rug.
    A rug is kept: `nub`, the same diary, went 0.00051 -> 0.0000011
    with its liquidity 63 614 -> 0.03 USD, on ONE pair whose age kept time.
    That is the loss the stop exists for, and dropping it would be the
    opposite lie."""
    flip, rug = "0xflip:2026-09-13T12", "0xrug:2026-09-13T12"
    age = 37_227_581
    rows = [_signal(flip, price=0.004302, age_seconds=age),
            _signal(rug, price=0.0005091, age_seconds=3946)]
    for hours, price, pair_age in ((1, 21.72, 17_588_603),
                                   (24, 0.004166, age + 24 * 3600)):
        rows.append({"type": "checkpoint", "key": flip, "horizon": f"{hours}h",
                     "at": (T0 + timedelta(hours=hours)).isoformat(),
                     "price_usd": price, "age_seconds": pair_age,
                     "return_pct": fomo.return_since_signal(0.004302, price)})
    for hours, price in ((1, 1.062e-06), (24, 1.0e-06)):
        rows.append({"type": "checkpoint", "key": rug, "horizon": f"{hours}h",
                     "at": (T0 + timedelta(hours=hours)).isoformat(),
                     "price_usd": price, "age_seconds": 3946 + hours * 3600,
                     "return_pct": fomo.return_since_signal(0.0005091, price)})
    said = fomo.stop_study(rows, stop_pct=10.0, cost_pct=0.0, now=DONE)
    assert said["n"] == 2 and said["switched"] == 1, said
    by_key = {t["key"]: t for t in said["trades"]}
    assert by_key[flip]["switched"] and by_key[flip]["gross_pct"] <= 0.0, (
        "21.72 was the other pair's price, never a gain of this coin's")
    assert not by_key[rug]["switched"]
    # A reading that carries no age cannot say, and is not a break.
    blind = [{k: v for k, v in r.items() if k != "age_seconds"} for r in rows]
    assert fomo.stop_study(blind, stop_pct=10.0, cost_pct=0.0,
                           now=DONE)["n"] == 2


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_report_and_the_brief_print_the_stop_lines(tmp_path, monkeypatch):
    """`fomo_watch.py report` prints stop -10 % alone and with a +100 %
    target; `lab.py brief` prints the same through `say_reading`. A reading
    the lab stored before this change has no `stops` and must still print."""
    mod = _watch(tmp_path, monkeypatch)
    key = "0xabc:2026-09-13T12"
    rows = [_signal(key)] + _path(key, 1.0, [(1, 0.95), (2, 0.60)])
    said = mod.reading(rows, now=DONE)
    lines = "\n".join(mod.say_reading(said))
    assert "stop -10%, no target" in lines, lines
    assert "stop -10% / target +100%" in lines, lines
    assert "upper bound" in lines, lines

    old = {k: v for k, v in said.items() if k not in ("stops", "entries")}
    # C05, deep pass of 2026-09-22: `is not None` passed on [] -- a reading
    # that prints nothing. The old reading prints everything it still has,
    # -- at the least every readout line the new one prints.
    printed = mod.say_reading(old)
    kept = [line for line in mod.say_reading(said)
            if " inside " in line and line.split()[0].endswith("x")]
    assert kept and all(line in printed for line in kept), (printed, kept)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_ten_dollars_into_every_hot_signal_is_answered_honestly():
    """[operator 2026-09-23] "kdybychom se pak treba rozhodnul dat 10$ do
    kazdeho hot signalu ... ze na to je likvidita i cas vse koupit" -- the
    plan's V3. What the diary answered instead was a study that dropped every
    coin whose NEWEST depth was dust (`sellable`): the coins that rugged later
    were taken out of their own history, and the losers with them.

    So the $10 question is asked the way a buyer lives it. A signal is bought
    only if we had its price when it fired and the radar's depth then
    (`max_buy_5pct_usd`) took $10; it is held 24 hours, no stop; the sale is
    capped by what the pool holds then (half its liquidity, the quote side),
    so a drained pool pays about nothing; a path on which their terminal
    switched pair is left out; a swap fee is charged each side, at 0.5, 1 and
    2 %. And "stihli bychom" is the share of hot signals that could have been
    bought at all."""
    def sig(n, **extra):
        return _signal(f"0x{n:03x}:2026-09-13T12", **extra)
    good, drained, unpriced, thin, blind, unread, young, switched = (
        sig(1, radar_max_buy_5pct_usd=5000.0),
        sig(2, price=2.0, radar_max_buy_5pct_usd=3000.0),
        sig(3, price=None, radar_max_buy_5pct_usd=5000.0),
        sig(4, radar_max_buy_5pct_usd=5.0),
        sig(5),
        sig(6, radar_max_buy_5pct_usd=5000.0),
        sig(7, radar_max_buy_5pct_usd=5000.0,
            at=DONE - timedelta(hours=10)),
        sig(8, radar_max_buy_5pct_usd=5000.0, age_seconds=100.0))

    def exit24(signal, price, liquidity, **extra):
        (row,) = _path(signal["key"], signal["price_usd"], [(24, price)])
        return {**row, "liquidity_usd": liquidity, **extra}
    rugged = sig(9, radar_max_buy_5pct_usd=5000.0, age_seconds=100.0)
    rows = [good, drained, unpriced, thin, blind, unread, young, switched, rugged,
            exit24(good, 1.5, 100_000.0), exit24(drained, 2.0, 4.0),
            exit24(thin, 3.0, 100_000.0), exit24(blind, 3.0, 100_000.0),
            # the terminal answered another pair: age jumped by days in a day,
            # and on it the price reads HIGHER -- a switched pair's price is
            # not a price the buyer's own pool paid, so it pays no gain
            exit24(switched, 1.2, 100_000.0, age_seconds=900_000.0),
            # 2026-09-23: every switch on record since 22. 9. was this one --
            # the main pool drained (a rug) and the terminal on the only pool
            # left, twelve cents deep. A real loss, never left out.
            exit24(rugged, 0.9, 0.12, age_seconds=900_000.0)]

    said = fomo.ten_dollars(rows, now=DONE)

    assert said["clip_usd"] == 10.0
    assert said["signals"] == 8, "the open window is not a signal of this study yet"
    assert said["bought"] == 4, said
    assert said["excluded"] == {"unpriced": 1, "too_thin": 1, "depth_unknown": 1,
                                "unread_at_24h": 1}, said
    assert said["switched"] == 2, "a switched pair is counted, and said"
    assert said["could_buy_share"] == pytest.approx(5 / 8), (
        "good, drained, unread, switched and rugged could all have been bought")

    def net(proceeds, depth, fee):
        impact = fomo.RADAR_IMPACT_PCT * 10.0 / depth
        return (proceeds / 10.0 * (1 - fee / 100) ** 2
                * (1 - impact / 100) ** 2 - 1) * 100
    for fee in (0.5, 1.0, 2.0):
        mine = said["by_fee"][fee]
        want = [net(15.0, 5000.0, fee), net(2.0, 3000.0, fee),
                net(10.0, 5000.0, fee),   # switched: capped at the $10 it cost
                net(0.06, 5000.0, fee)]   # rugged: half of $0.12 is all it sells for
        assert mine["mean_net_pct"] == pytest.approx(sum(want) / 4), (fee, mine)
        assert mine["n"] == 4


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_report_opens_with_the_ten_dollar_answer(tmp_path, monkeypatch):
    """The plan's V3 done-when: the report says "$10 into every hot signal =
    X % after costs, n, could buy Y %" -- first, because it is the question
    the operator asked, before the hot-against-control readouts."""
    mod = _watch(tmp_path, monkeypatch)
    key = "0x001:2026-09-13T12"
    signal = _signal(key, radar_max_buy_5pct_usd=5000.0)
    (exit24,) = _path(key, 1.0, [(24, 1.5)])
    said = mod.reading([signal, {**exit24, "liquidity_usd": 100_000.0}],
                       now=DONE)
    first = mod.say_reading(said)[0]
    assert first.startswith("$10 into every hot signal"), first
    assert "n=1" in first and "Could buy 100.0% of 1" in first, first
    assert "after costs at 1% a side" in first, first


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_reading_read_back_off_disk_still_prints_the_ten_dollar_line(
        tmp_path, monkeypatch):
    """`lab.note_fomo_reading` writes the reading to the JSONL diary and
    `lab.load()` reads it back through json.loads -- a dict's numeric keys
    (`by_fee`'s 0.5/1.0/2.0) come back as strings. `say_ten_dollars` formatted
    the key with `:g`, which raised on a string and crashed `lab.py brief`
    (found live, 2026-09-24)."""
    import json

    mod = _watch(tmp_path, monkeypatch)
    key = "0x001:2026-09-13T12"
    signal = _signal(key, radar_max_buy_5pct_usd=5000.0)
    (exit24,) = _path(key, 1.0, [(24, 1.5)])
    said = mod.reading([signal, {**exit24, "liquidity_usd": 100_000.0}], now=DONE)
    stored = json.loads(json.dumps(said))
    assert isinstance(next(iter(stored["ten_dollars"]["by_fee"])), str)
    fresh = "\n".join(mod.say_reading(said))
    stale = "\n".join(mod.say_reading(stored))
    assert stale.startswith("$10 into every hot signal"), stale
    # And the headline's "at 1% a side" figure is still the 1% row, not
    # whichever fee happens to be first in the dict (the fallback silently
    # picked 0.5% off a stored reading).
    assert stale == fresh, (fresh, stale)
    # ...pinned to the 1% row's own figure, since `stale == fresh` holds too
    # when both pick the first fee (deep pass 2026-09-24, B01, 3/3).
    rows = said["ten_dollars"]["by_fee"]
    one = next(v for fee, v in rows.items() if float(fee) == 1.0)
    first = next(v for fee, v in sorted(rows.items(), key=lambda kv: float(kv[0])))
    assert one["mean_net_pct"] != first["mean_net_pct"], "the fixture cannot tell 1% from 0.5%"
    headline = fresh.split(" a trade after costs at 1% a side")[0]
    assert headline.endswith(mod._signed(one["mean_net_pct"])), (headline, one)
