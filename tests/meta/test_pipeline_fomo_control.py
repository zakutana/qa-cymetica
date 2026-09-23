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
def test_the_control_is_chosen_by_the_hash_and_not_by_their_order():
    """L03 (3/3): the capture test showed only that the pick is DETERMINISTIC
    -- taking the first N cold rows in their order is deterministic too, and
    samples whatever their sort favours. Here the list order and the hash
    order disagree, and the hash has to win."""
    import hashlib

    listed = [{"token_address": f"tok{n}", "hot": False} for n in range(12)]
    by_hash = sorted(listed, key=lambda r: hashlib.sha256(
        r["token_address"].encode("utf-8")).hexdigest())
    assert by_hash[:3] != listed[:3], "the fixture cannot tell the two apart"

    picked = fomo.pick_control(listed, 3, set(), at=T0)

    assert [r["token_address"] for r in picked] == [
        r["token_address"] for r in by_hash[:3]]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_coin_called_hot_earlier_this_hour_is_not_its_own_control(
        tmp_path, monkeypatch):
    """R08 (3/3): the pick skipped only rows hot in THIS listing, so a coin
    hot at 12:05 and cooled by 12:25 could be drawn as a control at 12:25 --
    the same coin at the same hour in both arms, pulling the lift toward 1."""
    mod = _module(tmp_path, monkeypatch)
    for chain in ("robinhood", "solana"):
        address = f"{chain}-COLD1"
        mod._append({"type": "signal", "at": T0.isoformat(),
                     "key": fomo.signal_key(address, T0),
                     "token_address": address, "chain": chain,
                     "price_usd": 1.0})
    handler, _ = _feed({}, hot=("HOT1",), cold=("COLD1",))

    said = mod.capture(_client(handler), now=T0 + timedelta(minutes=20))

    assert said["added"] == 2 and said["control"] == 0, said


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_calibration_that_drops_a_field_is_a_new_version(tmp_path,
                                                            monkeypatch):
    """L04 (3/3): 'unchanged' was checked one way -- every field of the NEW
    block equal to the stored row -- so a version that stopped publishing its
    hot precision matched on what was left and was never written, and the
    brief went on quoting a claim they had withdrawn."""
    mod = _module(tmp_path, monkeypatch)
    handler, _ = _feed({})
    mod.capture(_client(handler), now=T0)
    fewer = {k: v for k, v in CALIBRATION.items() if k != "type_precision"}
    handler, _ = _feed({}, calibration=fewer)
    mod.capture(_client(handler), now=T0 + timedelta(minutes=20))

    kept = [r for r in mod.load() if r["type"] == "calibration"
            and r["chain"] == "solana"]
    assert len(kept) == 2 and "hot_precision" not in kept[-1], kept


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


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_one_round_quotes_each_coin_once(tmp_path, monkeypatch):
    """A coin hot in two consecutive hours is two signals, and both come due in
    the same round -- two quotes of one coin at one moment, the same price
    twice. Measured on the live diary 2026-09-19: 262 quotes for 89 coins in
    one round, and the first live tick of the loop spent seven of its eight
    and a half minutes there. The control group doubles the coins; without
    this the tick would outrun the ten minutes a command may take."""
    mod = _module(tmp_path, monkeypatch)
    for hour in (10, 11):
        mod._append({"type": "signal", "key": f"0xabc:2026-09-19T{hour}",
                     "at": T0.replace(hour=hour).isoformat(),
                     "token_address": "0xabc", "price_usd": 1.0})
    mod._append({"type": "control", "key": "control:0xdef:2026-09-19T11",
                 "at": T0.replace(hour=11).isoformat(),
                 "token_address": "0xdef", "price_usd": 1.0})
    handler, requests = _feed({"0xabc": 2.0, "0xdef": 1.5})

    said = mod.resolve(_client(handler), now=T0.replace(hour=13, minute=5))

    quotes = [u for u in requests if "memecoin-terminal/search" in u]
    assert said["checked"] == 2 and said["studied"] == 1, said
    assert len(quotes) == 2, f"{len(quotes)} quotes for two coins: {quotes}"
    written = [r for r in mod.load() if r["type"] in ("checkpoint", "study")]
    assert {r["price_usd"] for r in written if "0xabc" in r["key"]} == {2.0}


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
def test_hot_and_control_are_compared_per_coin_over_one_period_on_one_pair():
    """C5 of the 2026-09-23 review (3/3). The stored 13.1% against 7.4% was
    three comparisons in one: it counted SIGNALS, so a coin the radar called
    hot five times was five hits or five misses of one coin; it set hot
    signals from 2026-09-13 beside a control group that began on 2026-09-19;
    and it had no pair filter, so a coin their terminal answered on another
    pair moved by the other pair's price.

    Now each group is compared over the period both exist, on the first call
    of each coin, and a path whose pair switched is left out -- each said,
    with the Wilson interval over coins."""
    early = T0 - timedelta(hours=1)
    rows = [
        _row("control", "control:c1:T", T0),
        _read("study", "control:c1:T", 30, 3.5, "control"),
        _row("control", "control:c2:T", T0),
        _read("study", "control:c2:T", 30, 1.1, "control"),
        # Before there was a control group: another period.
        _row("signal", "early:T", early),
        {**_read("checkpoint", "early:T", 21, 3.5),
         "at": (early + timedelta(hours=21)).isoformat()},
        # One coin, called hot twice: one coin.
        _row("signal", "twice:T1", T0), _read("checkpoint", "twice:T1", 20, 3.5),
        _row("signal", "twice:T2", T0 + timedelta(minutes=30)),
        {**_read("checkpoint", "twice:T2", 20, 3.5),
         "at": (T0 + timedelta(minutes=30, hours=20)).isoformat()},
        _row("signal", "miss:T", T0), _read("checkpoint", "miss:T", 20, 1.2),
        # Their terminal answered another pair: the age jumped by days.
        _row("signal", "switched:T", T0, age_seconds=100.0),
        {**_read("checkpoint", "switched:T", 20, 9.0), "age_seconds": 900_000.0},
    ]

    said = fomo.compare(rows, multiple=3.0, within_hours=72,
                        now=T0 + timedelta(hours=73))

    hot = said["hot"]
    assert (hot["n"], hot["hits"]) == (2, 1), hot
    assert hot["excluded"]["before_period"] == 1, hot["excluded"]
    assert hot["excluded"]["repeat_call"] == 1, hot["excluded"]
    assert hot["excluded"]["pair_changed"] == 1, hot["excluded"]
    assert (said["control"]["n"], said["control"]["hits"]) == (2, 1), said
    assert said["period_from"] == T0.isoformat(), said


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
        # Never quoted for depth (every signal before 2026-09-14): unknown,
        # which is not untradeable (R07, 2/3).
        {"type": "signal", "key": "nodepth:T", "at": T0.isoformat(),
         "price_usd": 1.0},
        _read("checkpoint", "nodepth:T", 3, 40.0),
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
    assert said["hot"]["excluded"]["depth_unknown"] == 1
    assert said["hot"]["excluded"]["window_open"] == 1
    low, high = said["hot"]["ci"]
    assert 0.0 < low < 0.5 < high < 1.0, "two coins are not a measurement"
