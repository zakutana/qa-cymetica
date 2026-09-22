"""scripts/hot_watch.py: the live round around qa/hot.py, over a mock client.

Field shapes captured live on 2026-09-21: GET /api/v1/headlines answers
`{"items": [{id, headline, published_at, source, tags, tickers, value_usd,
event_card_id, hotidx: {hot, hot_class, stock_px, crypto_px, stock_ret_24h,
crypto_ret_24h, stock_members, crypto_members}}], "filters", "mode"}`, and
GET /api/v1/event-cards/{id}/index-history answers `{"points": [{t, index}]}`.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
T0 = datetime(2026, 9, 21, 12, 0, tzinfo=timezone.utc)


def _module(tmp_path, monkeypatch):
    import importlib

    import qa.state

    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    importlib.reload(qa.state)
    spec = importlib.util.spec_from_file_location(
        "hot_watch_under_test", REPO / "scripts" / "hot_watch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _client(handler):
    from qa.client import build_mock_client

    return build_mock_client(handler, timeout=5.0)


def _item(hid, px=100.0, ret=7.0, cls="crypto", card="card-1"):
    return {"id": hid, "headline": f"headline {hid}", "source": "Wire",
            "published_at": T0.isoformat(), "tags": ["crypto"], "tickers": [],
            "value": None, "value_usd": None, "event_card_id": card,
            "hotidx": {"hot": ret, "hot_class": cls,
                       "crypto_px": px, "crypto_ret_24h": ret,
                       "stock_px": 50.0, "stock_ret_24h": 0.5,
                       "crypto_members": ["AAA", "BBB", "CCC"],
                       "stock_members": ["XX"]}}


def _handler(hot_items, wire_items, fail_hot=False):
    def handler(request):
        params = request.url.params
        if request.url.path == "/api/v1/headlines":
            if params.get("filter") == "hot":
                if fail_hot:
                    return httpx.Response(503)
                return httpx.Response(200, json={"items": hot_items, "mode": "hot"})
            return httpx.Response(200, json={"items": wire_items, "mode": "feed"})
        return httpx.Response(404)
    return handler


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_capture_writes_one_round_and_each_headline_once(tmp_path, monkeypatch):
    mod = _module(tmp_path, monkeypatch)
    items = [_item(1), _item(2, px=5.0)]
    said = mod.capture(_client(_handler(items[:1], items)), now=T0)
    assert said["ok"] and said["headlines"] == 2

    rows = mod.load()
    (rnd,) = [r for r in rows if r["type"] == "round"]
    assert rnd["hot"] == [[1, 1, 7.0, "crypto", 100.0, 7.0]]
    assert [1, 50.0, 100.0, 0.5, 7.0] in rnd["wire"]
    head = next(r for r in rows if r["type"] == "headline" and r["id"] == 1)
    assert head["crypto_fp"] == "crypto:AAA,BBB,CCC"
    assert head["event_card_id"] == "card-1"

    again = mod.capture(_client(_handler(items[:1], items)),
                        now=T0 + timedelta(minutes=20))
    assert again["headlines"] == 0
    assert len([r for r in mod.load() if r["type"] == "headline"]) == 2


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_failed_hot_read_is_written_as_none_not_as_an_empty_tab(tmp_path,
                                                                    monkeypatch):
    mod = _module(tmp_path, monkeypatch)
    said = mod.capture(_client(_handler([], [_item(1)], fail_hot=True)), now=T0)
    assert said["ok"] is False
    (rnd,) = [r for r in mod.load() if r["type"] == "round"]
    assert rnd["hot"] is None and rnd["errors"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_tick_reads_the_diary_once(tmp_path, monkeypatch):
    """R11, deep pass of 2026-09-21 (3/3): capture() and resolve() each parsed
    the whole diary, about 2 MB more every day, on every tick. The tick reads
    it once and hands it to both; what capture wrote is in the hand-off."""
    mod = _module(tmp_path, monkeypatch)
    wire = [_item(1)]
    mod.capture(_client(_handler([], wire)), now=T0)
    loads = {"n": 0}
    real = mod.load

    def counted():
        loads["n"] += 1
        return real()
    monkeypatch.setattr(mod, "load", counted)
    monkeypatch.setattr(mod, "_now", lambda: T0 + timedelta(minutes=20))
    said = mod.tick(_client(_handler(wire, wire)))
    assert loads["n"] == 1, f"the diary was read {loads['n']} times in one tick"
    assert said["capture"]["ok"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_read_that_outlives_its_deadline_is_a_failed_read_not_a_hung_tick(
        tmp_path, monkeypatch):
    """2026-09-21 18:06: the `limit=500` wire read hung a tick for 15 minutes.
    httpx's timeout is between bytes, so an answer that trickles never trips
    it. A read now has a deadline for the WHOLE answer, and past it the round
    is written with that read failed -- the hot rows still land."""
    mod = _module(tmp_path, monkeypatch)
    monkeypatch.setattr(mod, "READ_DEADLINE_S", 0.0)
    said = mod.capture(_client(_handler([_item(1)], [_item(1)])), now=T0)
    assert said["ok"] is False
    assert any("deadline" in e for e in said["errors"]), said["errors"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_card_is_priced_afterwards_from_its_own_history(tmp_path, monkeypatch):
    """The card behind an entry is read once its day has passed, from
    index-history -- never sampled on the way. A card it could not price is
    counted as unobserved, never dropped."""
    mod = _module(tmp_path, monkeypatch)
    wire = [_item(1)]
    mod.capture(_client(_handler([], wire)), now=T0)
    mod.capture(_client(_handler(wire, wire)), now=T0 + timedelta(minutes=20))

    asked = []

    def history(request):
        asked.append(request.url.path)
        pts = [{"t": (T0 + timedelta(hours=h)).isoformat(), "index": 100 + h}
               for h in range(0, 30)]
        return httpx.Response(200, json={"points": pts})

    early = mod.resolve(_client(history), now=T0 + timedelta(hours=3))
    assert early["cards"] == 0 and not asked, "not before the day is out"

    later = mod.resolve(_client(history), now=T0 + timedelta(hours=25))
    assert later["cards"] == 1
    assert asked == ["/api/v1/event-cards/card-1/index-history"]
    (card,) = [r for r in mod.load() if r["type"] == "card"]
    assert card["card_id"] == "card-1" and card["ok"]

    mod.resolve(_client(history), now=T0 + timedelta(hours=26))
    assert len(asked) == 1, "a card is read once"

    # Entry at T0+20 min; the history's points are hourly, so the entry point
    # is T0 (20 min off, inside the 30 allowed) at index 100, and +6 h is T0+6h
    # at 106. A horizon with no point near it is not a result.
    said = mod.card_follow(mod.load(), horizons=(6.0, 40.0))
    assert said[6.0]["n"] == 1 and said[6.0]["mean"] == 6.0
    assert said[40.0]["n"] == 0

    # B07, deep pass of 2026-09-21: a card whose read failed, or whose history
    # stops short of the horizon, was dropped -- `unobserved` was a hard 0.
    # Both are counted now; a horizon the diary has not reached yet is open.
    entry_at = (T0 + timedelta(minutes=20)).isoformat()
    base = {"type": "card", "at": (T0 + timedelta(hours=25)).isoformat(),
            "fp": "crypto:DDD,EEE,FFF", "entry_at": entry_at}
    # Two distinct entries: rows on one (fp, entry_at) are attempts at ONE card.
    failed = {**base, "fp": "crypto:GGG,HHH,III", "card_id": "card-2", "ok": False,
              "status": 503, "points": []}
    short = {**base, "card_id": "card-3", "ok": True, "status": 200,
             "points": [[T0.isoformat(), 100], [(T0 + timedelta(hours=1)).isoformat(), 101]]}
    said = mod.card_follow(mod.load() + [failed, short], horizons=(6.0, 40.0))
    assert said[6.0]["n"] == 1 and said[6.0]["unobserved"] == 2
    assert said[6.0]["open"] == 0
    assert said[40.0]["n"] == 0 and said[40.0]["open"] == 3


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_card_whose_read_failed_is_read_again_and_counted_once(tmp_path,
                                                                  monkeypatch):
    """Rule 8: a failed read is not a read. resolve() wrote one row per entry
    and took ANY row as done, so a card whose read failed once -- a 503, a
    timeout -- was never read again. It is retried up to MAX_CARD_TRIES, and
    card_follow reads one row per entry, the ok one if there is one, so the
    attempts are not counted as entries."""
    mod = _module(tmp_path, monkeypatch)
    wire = [_item(1)]
    mod.capture(_client(_handler([], wire)), now=T0)
    mod.capture(_client(_handler(wire, wire)), now=T0 + timedelta(minutes=20))
    asked = []

    def down(request):
        asked.append(request.url.path)
        return httpx.Response(503)

    def up(request):
        asked.append(request.url.path)
        pts = [{"t": (T0 + timedelta(hours=h)).isoformat(), "index": 100 + h}
               for h in range(0, 30)]
        return httpx.Response(200, json={"points": pts})

    mod.resolve(_client(down), now=T0 + timedelta(hours=25))
    mod.resolve(_client(up), now=T0 + timedelta(hours=26))
    assert len(asked) == 2, "a failed card read is read again"
    mod.resolve(_client(up), now=T0 + timedelta(hours=27))
    assert len(asked) == 2, "and once it is read, it is done"
    said = mod.card_follow(mod.load(), horizons=(6.0,))
    assert said[6.0]["n"] == 1 and said[6.0]["unobserved"] == 0, \
        "two attempts at one card are one entry"

    # A card that never answers stops costing a GET every tick.
    mod2 = _module(tmp_path / "b", monkeypatch)
    mod2.capture(_client(_handler([], wire)), now=T0)
    mod2.capture(_client(_handler(wire, wire)), now=T0 + timedelta(minutes=20))
    asked.clear()
    for h in range(mod2.MAX_CARD_TRIES + 2):
        mod2.resolve(_client(down), now=T0 + timedelta(hours=25 + h))
    assert len(asked) == mod2.MAX_CARD_TRIES
    said = mod2.card_follow(mod2.load(), horizons=(6.0,))
    assert said[6.0]["n"] == 0 and said[6.0]["unobserved"] == 1
