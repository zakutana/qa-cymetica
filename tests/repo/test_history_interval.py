"""Which index-history read a verdict takes, and what it does with it (T-0039, T-0050, OP-0018).

Their windows all end at now (1d, 5d, 30d, all; openapi capture 4f67ff26), so what a read can say
about a moment drifts coarser as the moment ages. `scripts/lab.py::_history(client, card, since)`
picks the interval by the age of `since` at the read, one step coarser while the first point does
not reach it; `verdicts()` caches each read by (card, interval), records which interval each series
came from, and holds a verdict whose benchmark has no point near the window's end yet as WAITING --
never written, since `record_verdict` takes any verdict it is given and a written one settles the
room for good. `lab.py index-at` answers the same reading over one GET, for the desk.

The fake here is THEIR side only, in the live shape measured on 2026-10-12 (see
tests/repo/test_benchmark_span.py): each interval a grid of points from its lookback to now.
"""

from __future__ import annotations

import io
import json
from contextlib import redirect_stdout
from datetime import timedelta

import httpx
import pytest

from qa import lab
from qa.marks import SafetyTier, qa
from tests.repo.test_benchmark_span import BTC, LEG, NOW, START
from tests.repo.test_card_leg_exit import _scripts_lab, _write

# --- the reads: which interval, the coarser step, the cache key ----------------------------------

ANCHOR = START - timedelta(days=60)
STEP = {"1d": timedelta(minutes=5), "5d": timedelta(minutes=30), "30d": timedelta(hours=3),
        "all": timedelta(hours=9)}
LOOKBACK = {"1d": timedelta(days=1), "5d": timedelta(days=5), "30d": timedelta(days=30), "all": None}


class _Response:
    status_code = 200

    def __init__(self, body):
        self.body = body

    def json(self):
        return self.body


class _Their:
    """Their index-history in the live shape: each interval a grid of points from (now - its
    lookback) to now, `all` from the start of their record. `starts` holds a card back (its index
    is first written then), `idle` holds back one interval's read of it, `cut` stops it (no point
    after it yet), `status` fails it."""

    def __init__(self, now, index, starts=None, idle=None, cut=None, status=None):
        self.now, self.index = now, index
        self.starts, self.idle = starts or {}, idle or {}
        self.cut, self.status = cut or {}, status or {}
        self.asked: list[tuple[str, object]] = []

    def close(self):
        pass

    def get(self, path, params=None, **_):
        card = path.split("/event-cards/")[1].split("/")[0]
        interval = (params or {}).get("interval")
        self.asked.append((card, interval))
        if interval not in STEP:
            return _Response({"points": []})      # the assertion on `asked` says so
        if self.status.get((card, interval)):
            response = _Response({})
            response.status_code = self.status[(card, interval)]
            return response
        step, back = STEP[interval], LOOKBACK[interval]
        first = max(ANCHOR if back is None else self.now - back, self.starts.get(card, ANCHOR),
                    self.idle.get((card, interval), ANCHOR))
        last = min(self.now, self.cut.get(card, self.now))
        at = ANCHOR + step * -((ANCHOR - first) // step)
        points = []
        while at <= last:
            points.append({"t": at.isoformat(), "index": self.index[card](at)})
            at += step
        return _Response({"interval": interval, "points": points})


def _hours(at):
    return (at - START).total_seconds() / 3600


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_interval_follows_the_age_of_since_and_steps_coarser_until_it_reaches_it(
        tmp_path, monkeypatch):
    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    for age, want in ((timedelta(hours=3), "1d"), (timedelta(days=1, minutes=20), "5d"),
                      (timedelta(days=7), "30d"), (timedelta(days=40), "all")):
        their = _Their(NOW, {BTC: lambda at: 100.0 + _hours(at)})
        got = scripts_lab._history(their, BTC, NOW - age, now=NOW)
        assert got["interval"] == want and their.asked == [(BTC, want)], (age, got["interval"], their.asked)
        assert lab._points(got["points"])[0][0] <= NOW - age, "the read does not reach since"

    # A card idle at the window's start: its 5d read begins after `since` (the index was not
    # written while it stood still), so 30d is read next, and it reaches.
    their = _Their(NOW, {LEG: lambda at: 100.0}, idle={(LEG, "5d"): NOW - timedelta(days=1)})
    got = scripts_lab._history(their, LEG, NOW - timedelta(days=2), now=NOW)
    assert [i for _, i in their.asked] == ["5d", "30d"] and got["interval"] == "30d", their.asked
    # A card whose index begins after `since`: no read reaches it, so `all` is taken whatever it
    # holds -- and an empty answer reaches nothing either.
    their = _Their(NOW, {LEG: lambda at: 100.0}, starts={LEG: NOW - timedelta(hours=10)})
    got = scripts_lab._history(their, LEG, NOW - timedelta(hours=12), now=NOW)
    assert [i for _, i in their.asked] == ["1d", "5d", "30d", "all"], their.asked
    assert got["interval"] == "all" and got["points"], got
    their = _Their(NOW, {LEG: lambda at: 100.0}, starts={LEG: NOW + timedelta(hours=1)})
    got = scripts_lab._history(their, LEG, NOW - timedelta(hours=12), now=NOW)
    assert [i for _, i in their.asked] == ["1d", "5d", "30d", "all"], their.asked
    assert (got["interval"], got["points"]) == ("all", []), got

    # A read that FAILED is not a coarser step: the verdict waits on it (rule 8).
    their = _Their(NOW, {BTC: lambda at: 100.0}, status={(BTC, "5d"): 502})
    with pytest.raises(scripts_lab.Unread):
        scripts_lab._history(their, BTC, NOW - timedelta(days=1, minutes=20), now=NOW)
    assert their.asked == [(BTC, "5d")], their.asked


def _running(room, start, days, leg, benchmark=BTC):
    return [{"type": "strategy", "id": room, "origin": f"NEX-{room[-4:]}", "title": room,
             "at": start.isoformat()},
            {"type": "acceptance", "room": room, "window_days": float(days), "stop_pct": 50.0,
             "legs": [{"card": leg, "side": "bull", "share": 1.0}], "benchmark_card": benchmark,
             "adopted": True, "why": "test", "at": start.isoformat()},
            {"type": "status", "room": room, "status": "running", "why": "test",
             "at": start.isoformat()}]


def _rising(start, days, pct):
    span = timedelta(days=days).total_seconds()
    return lambda at: 100.0 + pct * (at - start).total_seconds() / span


def _wire(scripts_lab, monkeypatch, their):
    monkeypatch.setattr("qa.client.build_client", lambda *a, **k: their)
    monkeypatch.setattr(scripts_lab, "_closes_at", lambda client, card: None)
    monkeypatch.setattr(scripts_lab, "pass_in_flight", lambda: False)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_verdict_reads_each_card_once_per_interval_and_records_which(tmp_path, monkeypatch):
    import qa.rooms as qa_rooms

    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    legs = {"STR-0001": "c" * 8 + "-0001-4000-8000-000000000001",
            "STR-0002": "c" * 8 + "-0002-4000-8000-000000000002",
            "STR-0003": "c" * 8 + "-0003-4000-8000-000000000003"}
    opened = {"STR-0001": (START, 1), "STR-0002": (START + timedelta(minutes=10), 1),
              "STR-0003": (START - timedelta(days=6), 7)}
    _write(tmp_path, "rooms.jsonl", [row for room, (at, days) in opened.items()
                                     for row in _running(room, at, days, legs[room])])
    # BTC +8% over the 1-day rooms' day, +108% over the week-old room's seven; each leg beats it.
    index = {BTC: lambda at: 300.0 + _hours(at)}
    index.update({legs[room]: _rising(at, days, 30.0 if days == 1 else 200.0)
                  for room, (at, days) in opened.items()})
    their = _Their(NOW, index)
    _wire(scripts_lab, monkeypatch, their)

    said = {s["room"]: s for s in scripts_lab.verdicts(now=NOW)}

    assert sorted(said) == ["STR-0001", "STR-0002", "STR-0003"], said
    assert all(interval in STEP for _, interval in their.asked), their.asked
    # Two 1-day rooms read the proxy on 5d ONCE between them; the week-old room on 30d.
    assert their.asked.count((BTC, "5d")) == 1 and their.asked.count((BTC, "30d")) == 1, their.asked
    assert len(their.asked) == len(set(their.asked)), f"a read was made twice: {their.asked}"
    assert said["STR-0001"]["intervals"] == {legs["STR-0001"]: "5d", BTC: "5d"}, said["STR-0001"]
    assert said["STR-0003"]["intervals"] == {legs["STR-0003"]: "30d", BTC: "30d"}, said["STR-0003"]
    for room in said:
        assert said[room]["verdict"] == "survived", said[room]
        stored = qa_rooms.verdict_of(qa_rooms.load(), room)
        assert stored["intervals"] == said[room]["intervals"], "the diary does not say what was read"
    # BTC 300 -> 324 over the day, read at the window's ends.
    assert said["STR-0001"]["benchmark_pct"] == pytest.approx(8.0), said["STR-0001"]
    assert said["STR-0003"]["benchmark_pct"] == pytest.approx((324.0 / 156.0 - 1) * 100), said["STR-0003"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_benchmark_with_no_point_near_the_close_waits_and_is_not_written(tmp_path, monkeypatch):
    """The trap the spec does not name: `record_verdict` takes any truthy verdict, and a written
    "waiting" would settle the room for good. Driven through verdicts(), not lab.verdict alone."""
    import qa.rooms as qa_rooms

    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    _write(tmp_path, "rooms.jsonl", _running("STR-0001", START, 1, LEG))
    end = START + timedelta(days=1)
    their = _Their(end + timedelta(minutes=20),
                   {BTC: lambda at: 100.0 + _hours(at), LEG: _rising(START, 1, 30.0)},
                   cut={BTC: end - timedelta(hours=2)})
    _wire(scripts_lab, monkeypatch, their)

    said = scripts_lab.verdicts(now=their.now)
    assert [s.get("verdict") for s in said] == ["waiting"], said
    assert "benchmark" in said[0]["why"], said
    rows = qa_rooms.load()
    assert qa_rooms.verdict_of(rows, "STR-0001") is None, "a waiting verdict was written down"
    assert qa_rooms.status_of(rows, "STR-0001") == "running"
    assert scripts_lab._tally_verdicts(said)["verdicts"] == 0

    # Within the hour on one side, it stands: the next call, the newest point 30 min before the close.
    their.cut = {BTC: end - timedelta(minutes=30)}
    their.now = end + timedelta(minutes=40)
    said = scripts_lab.verdicts(now=their.now)
    assert [s.get("verdict") for s in said] == ["survived"], said
    assert said[0]["benchmark_pct"] == pytest.approx(23.5), said
    assert qa_rooms.verdict_of(qa_rooms.load(), "STR-0001")["verdict"] == "survived"


# --- index-at -----------------------------------------------------------------------------------


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_index_at_answers_the_benchmark_reading_over_one_get(tmp_path, monkeypatch):
    from qa.client import build_client
    from qa.config import identities
    from qa.safety import EndpointRegistry

    scripts_lab = _scripts_lab(tmp_path, monkeypatch)
    their = _Their(NOW, {BTC: lambda at: 100.0 + _hours(at)})
    seen = []

    def answer(request):
        seen.append((request.method, request.url.path, dict(request.url.params)))
        response = their.get(request.url.path, params=dict(request.url.params))
        return httpx.Response(response.status_code, json=response.body)
    guarded = build_client(identities()["anon"], EndpointRegistry.load(),
                           base_url="https://cymetica.com", inner=httpx.MockTransport(answer))
    monkeypatch.setattr("qa.client.build_client", lambda *a, **k: guarded)
    monkeypatch.setattr(scripts_lab, "_now", lambda: NOW)

    printed = io.StringIO()
    with redirect_stdout(printed):
        code = scripts_lab.main(["index-at", BTC, (START + timedelta(minutes=10)).isoformat(),
                                 (START + timedelta(hours=20, minutes=45)).isoformat(), "--json"])
    assert code == 0
    said = json.loads(printed.getvalue())
    assert said["card"] == BTC and said["interval"] == "5d", said
    assert [r["value"] for r in said["at"]] == pytest.approx([100.0 + 10 / 60, 120.75]), said
    assert [r["how"] for r in said["at"]] == ["between", "between"], said
    assert {method for method, _, _ in seen} == {"GET"}, seen
    assert [params.get("interval") for _, _, params in seen] == ["5d"], seen
