"""Does FOMO Radar's `hot` predict a pump -- against what?

[operator 2026-09-19] asked the laboratory to find out whether the radar can
predict the memecoins that pump. The diary measured only the coins it called
hot, and a hit rate with nothing beside it cannot say "predicts": on bonding
curves most coins die, and 9% of hot coins tripling means something only next
to how many of the OTHERS tripled.

Their own feed says exactly that, in its `calibration` block (read live
2026-09-19): `hot` reached 3x inside 72 hours for 9.5% of 169, against a base
rate of 3.4%. That is a claim with a number in it, which makes it testable:

  * a CONTROL group -- coins the same feed listed at the same moment and did
    NOT call hot, as many as it did call, chosen by hash so nobody picks them;
  * both groups read at the same horizons, out to 72 hours, so the
    comparison is fair even where hourly sampling misses an intra-hour peak;
  * a pump is judged on the PEAK inside the window, only over windows that
    have fully passed, and only for coins somebody could have bought.

None of it may reach the memecoin tab: control rows and the late readings
carry their own types, so every existing reader stays blind to them.
"""

from __future__ import annotations

import importlib
import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from qa import fomo
from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
T0 = datetime(2026, 9, 19, 12, 0, tzinfo=timezone.utc)
DEEP = {"liquidity_usd": 50000.0, "volume_h24": 90000.0}


def _module(tmp_path, monkeypatch):
    import qa.state

    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    importlib.reload(qa.state)
    spec = importlib.util.spec_from_file_location(
        "fomo_watch_control", REPO / "scripts" / "fomo_watch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _client(handler):
    from qa.client import build_mock_client

    return build_mock_client(handler, timeout=5.0)


CALIBRATION = {"target_multiple": 3.0, "horizon_hours": 72, "base_rate": 0.034,
               "type_precision": {"hot": {"n": 169, "hits": 16,
                                          "precision": 0.0947}}}


def _feed(prices, calibration=CALIBRATION, hot=("HOT1",),
          cold=("COLD1", "COLD2", "COLD3", "COLD4")):
    """Their feed: `filter=hot` answers the hot rows only, no filter answers
    everything it lists. Both carry the calibration block."""
    requests = []

    def handler(request):
        url = str(request.url)
        requests.append(url)
        if "fomo-radar/signals" in url:
            chain = request.url.params.get("chain")
            rows = [{"token_address": f"{chain}-{t}", "hot": True, "symbol": t}
                    for t in hot]
            if request.url.params.get("filter") != "hot":
                rows += [{"token_address": f"{chain}-{t}", "hot": False,
                          "symbol": t} for t in cold]
                rows.append({"token_address": "", "hot": False})
            body = {"rows": rows}
            if calibration is not None:
                body["calibration"] = calibration
            return httpx.Response(200, json=body)
        if "memecoin-terminal/search" in url:
            wanted = request.url.params.get("q")
            return httpx.Response(200, json={"rows": [
                {"address": wanted, "price_usd": prices.get(wanted, 1.0),
                 **DEEP}]})
        return httpx.Response(404)
    return handler, requests


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_capture_tracks_a_matched_control_from_the_same_feed(tmp_path,
                                                             monkeypatch):
    mod = _module(tmp_path, monkeypatch)
    handler, _ = _feed({})

    said = mod.capture(_client(handler), now=T0)
    again = mod.capture(_client(handler), now=T0 + timedelta(minutes=20))

    rows = mod.load()
    hot = [r for r in rows if r["type"] == "signal"]
    control = [r for r in rows if r["type"] == "control"]
    assert len(hot) == 2 and len(control) == 2, (
        f"{len(hot)} hot and {len(control)} control: one of each per chain, "
        f"as many controls as the round called hot")
    assert all(r["key"].startswith("control:") for r in control)
    assert {r["chain"] for r in control} == {"robinhood", "solana"}
    assert all("COLD" in r["token_address"] for r in control)
    assert all(r["price_usd"] == 1.0 and r["liquidity_usd"] == 50000.0
               for r in control), "a control is priced like a signal"
    assert said["control"] == 2 and again["control"] == 0, (
        "the same hour tracked the same controls twice")

    # Chosen by hash, not by position in their list: rebuilt from nothing,
    # the same round picks the same coins.
    (tmp_path / "again").mkdir()
    fresh = _module(tmp_path / "again", monkeypatch)
    fresh.capture(_client(handler), now=T0)
    assert ({r["token_address"] for r in fresh.load() if r["type"] == "control"}
            == {r["token_address"] for r in control})


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_round_that_called_nothing_hot_tracks_no_control(tmp_path,
                                                           monkeypatch):
    """Matched in time as well as in number: a control from a quiet hour
    compares the radar against a different market."""
    mod = _module(tmp_path, monkeypatch)
    handler, _ = _feed({}, hot=())

    said = mod.capture(_client(handler), now=T0)

    assert said["added"] == 0 and said["control"] == 0
    assert not [r for r in mod.load() if r["type"] == "control"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_their_calibration_is_kept_when_it_changes(tmp_path, monkeypatch):
    """Their claim is the number our measurement is held against, and it moves
    as their model retrains -- so each version is kept, once."""
    mod = _module(tmp_path, monkeypatch)
    handler, _ = _feed({})
    mod.capture(_client(handler), now=T0)
    mod.capture(_client(handler), now=T0 + timedelta(minutes=20))
    moved = {**CALIBRATION, "base_rate": 0.036}
    handler, _ = _feed({}, calibration=moved)
    mod.capture(_client(handler), now=T0 + timedelta(minutes=40))

    # Per chain: each chain's feed carries its own, and they need not agree.
    kept = [r for r in mod.load() if r["type"] == "calibration"
            and r["chain"] == "solana"]
    assert [r["base_rate"] for r in kept] == [0.034, 0.036], kept
    assert kept[0]["hot_precision"] == 0.0947 and kept[0]["hot_n"] == 169


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_both_groups_are_read_out_to_72_hours_and_the_tab_sees_neither(
        tmp_path, monkeypatch):
    mod = _module(tmp_path, monkeypatch)
    handler, _ = _feed({})
    mod.capture(_client(handler), now=T0)
    tab_before = (fomo.basket(mod.load()), fomo.stats(mod.load()))

    for hours in (1, 30, 72):
        mod.resolve(_client(handler), now=T0 + timedelta(hours=hours,
                                                         minutes=5))

    rows = mod.load()
    hot_1h = [r for r in rows if r["type"] == "checkpoint"]
    study = [r for r in rows if r["type"] == "study"]
    assert len(hot_1h) == 2 and {r["horizon"] for r in hot_1h} == {"1h"}, (
        "the hot diary's own hours are unchanged")
    by = {(r["group"], r["horizon"]) for r in study}
    assert by == {("control", "1h"), ("hot", "30h"), ("control", "30h"),
                  ("hot", "72h"), ("control", "72h")}, by

    # The tab reads exactly what it read before, whatever the study wrote.
    only_hot = [r for r in rows if r["type"] not in ("control", "study",
                                                     "calibration")]
    assert fomo.basket(rows) == fomo.basket(only_hot)
    assert fomo.stats(rows) == fomo.stats(only_hot)
    assert fomo.curves(rows) == fomo.curves(only_hot)
    assert tab_before[0]["tracked"] == fomo.basket(rows)["tracked"]


def _row(kind, key, at, price=1.0, **extra):
    return {"type": kind, "key": key, "at": at.isoformat(), "price_usd": price,
            **DEEP, **extra}


def _read(kind, key, hours, price, group=None):
    row = {"type": kind, "key": key, "horizon": f"{hours:g}h",
           "at": (T0 + timedelta(hours=hours)).isoformat(),
           "price_usd": price, "return_pct": (price - 1.0) * 100.0, **DEEP}
    if group:
        row["group"] = group
    return row


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_pump_is_its_peak_inside_a_window_that_has_passed():
    """Their label is "reached 3x inside 72 hours", so a coin that tripled at
    hour twenty and died by seventy-two DID pump. A window still open is not
    counted either way -- a hit could be seen early but a miss cannot, and
    counting only the early hits inflates the rate. A coin nobody could have
    bought is not counted at all."""
    rows = [
        _row("signal", "h1:T", T0), _read("checkpoint", "h1:T", 20, 3.2),
        _read("study", "h1:T", 72, 0.5, "hot"),
        _row("signal", "h2:T", T0), _read("checkpoint", "h2:T", 5, 1.4),
        _row("signal", "thin:T", T0, liquidity_usd=0.02, volume_h24=0.25),
        _read("checkpoint", "thin:T", 3, 40.0),
        _row("signal", "young:T", T0 + timedelta(hours=10)),
        _read("checkpoint", "young:T", 12, 5.0),
        _row("control", "control:c1:T", T0),
        _read("study", "control:c1:T", 30, 1.6, "control"),
        _row("control", "control:c2:T", T0),
        _read("study", "control:c2:T", 48, 3.5, "control"),
        _row("control", "control:c3:T", T0),
        _read("study", "control:c3:T", 2, 0.9, "control"),
        _row("control", "control:c4:T", T0),
        _read("study", "control:c4:T", 6, 1.1, "control"),
    ]

    said = fomo.compare(rows, multiple=3.0, within_hours=72,
                        now=T0 + timedelta(hours=73))

    assert said["hot"]["n"] == 2 and said["hot"]["hits"] == 1, said["hot"]
    assert said["control"]["n"] == 4 and said["control"]["hits"] == 1, said
    assert said["hot"]["rate"] == 0.5 and said["control"]["rate"] == 0.25
    assert said["lift"] == 2.0
    assert said["hot"]["excluded"]["untradeable"] == 1
    assert said["hot"]["excluded"]["window_open"] == 1
    low, high = said["hot"]["ci"]
    assert 0.0 < low < 0.5 < high < 1.0, "two coins are not a measurement"
