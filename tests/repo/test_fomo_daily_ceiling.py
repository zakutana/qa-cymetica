"""The FOMO collector stops for the day at a ceiling of requests (NEXT.md 2026-10-11; deep pass 2026-10-18).

docs/crew-before-c9.md point 10 (conduct, high): on 2026-10-09 the collector made 48,557 requests to
cymetica.com, 39,784 of them to /api/v1/clones/memecoin-terminal/search -- a route absent from /api-docs --
at a flat ~2,000 an hour (`serve.py --fomo 1`, QUOTES_PER_MINUTE 60), while REPLY-0030 asks for no load or
volume testing. The per-round quote cap spreads a burst over the next rounds; nothing ever stopped the day.
The deep pass of 2026-10-18 first left this line for "the day's request counts measured first", and the
week's outside reader was right that a ceiling needs no measurement: the collector counts its own requests.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _script():
    spec = importlib.util.spec_from_file_location("fomo_watch_ceiling", REPO / "scripts" / "fomo_watch.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Client:
    def __init__(self):
        self.calls, self.closed = 0, False

    def get(self, path, params=None):
        self.calls += 1
        return path

    def close(self):
        self.closed = True


class _Stop:
    """Lets `rounds` rounds run, then ends the loop; moves the clock as a round's wait would."""

    def __init__(self, rounds, clock, step=timedelta(minutes=1)):
        self.left, self.clock, self.step = rounds, clock, step

    def wait(self, every):
        self.left -= 1
        self.clock[0] += self.step
        return self.left <= 0


def _loop(monkeypatch, rounds, start, step=timedelta(minutes=1), per_round=3, ceiling=5):
    fw = _script()
    clock = [start]
    monkeypatch.setattr(fw, "_now", lambda: clock[0])
    monkeypatch.setattr(fw, "DAILY_REQUESTS", ceiling)
    ticks = []

    def fake_tick(client, cap=None):
        for _ in range(per_round):
            client.get("/api/v1/clones/memecoin-terminal/search")
        ticks.append(clock[0])

    monkeypatch.setattr(fw, "tick", fake_tick)
    client = _Client()
    fw.run(_Stop(rounds, clock, step), every=60, client=client)
    return fw, client, ticks


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_rounds_stop_for_the_rest_of_the_day_once_the_ceiling_is_reached(monkeypatch):
    start = datetime(2026, 10, 18, 9, 0, tzinfo=timezone.utc)
    _, client, ticks = _loop(monkeypatch, rounds=6, start=start)
    assert len(ticks) == 2, f"3 + 3 requests reach the ceiling of 5; the next four rounds wait ({len(ticks)} ran)"
    assert client.calls == 6, "every request went through to the real client, and was counted"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_new_utc_day_starts_the_count_again(monkeypatch):
    start = datetime(2026, 10, 18, 23, 57, tzinfo=timezone.utc)
    _, client, ticks = _loop(monkeypatch, rounds=6, start=start)
    assert [t.date().isoformat() for t in ticks] == ["2026-10-18", "2026-10-18", "2026-10-19", "2026-10-19"], ticks


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_ceiling_sits_far_under_the_day_that_asked_for_it():
    fw = _script()
    assert 0 < fw.DAILY_REQUESTS <= 48_557 // 4, (
        f"{fw.DAILY_REQUESTS} a day: the 2026-10-09 volume that REPLY-0030 rules out was 48,557")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_counting_client_hands_everything_else_to_the_real_one():
    fw = _script()
    real = _Client()
    counted = fw._Counted(real)
    counted.close()
    assert real.closed, "close() reaches the real client"
    assert counted.get("/x") == "/x" and counted.made == 1 and real.calls == 1
