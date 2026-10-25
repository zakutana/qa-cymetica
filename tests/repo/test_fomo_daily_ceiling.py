"""The FOMO collector stops for the day at a ceiling of requests (NEXT.md 2026-10-11; deep pass 2026-10-18).

docs/crew-before-c9.md point 10 (conduct, high): on 2026-10-09 the collector made 48,557 requests to
cymetica.com, 39,784 of them to /api/v1/clones/memecoin-terminal/search -- a route absent from /api-docs --
at a flat ~2,000 an hour (`serve.py --fomo 1`, QUOTES_PER_MINUTE 60), while REPLY-0030 asks for no load or
volume testing. The per-round quote cap spreads a burst over the next rounds; nothing ever stopped the day.
The deep pass of 2026-10-18 first left this line for "the day's request counts measured first", and the
week's outside reader was right that a ceiling needs no measurement: the collector counts its own requests.

Deep pass 2026-10-25, M01: that count lived inside `run()`, the console's loop, in its own memory. The
lab's round -- `watch.tick(watch._client())`, a new process every twenty minutes -- and a hand run never
went through it: about 9,700 quotes a day uncounted at the median round, 40,000 at the p99. The count now
lives in state/fomo_requests.json, under its lock, and `tick()` -- the one entry every round goes through
-- reads it before a round and counts every request the round makes. Two loads of the script on one state
directory stand in for two processes.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from qa.marks import SafetyTier, qa
from tests.repo.test_card_leg_exit import _scripts_lab

REPO = Path(__file__).resolve().parent.parent.parent
START = datetime(2026, 10, 18, 9, 0, tzinfo=timezone.utc)


def _script(tmp_path, monkeypatch, name="fomo_watch_ceiling", clock=None, ceiling=5):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / "fomo_watch.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    clock = clock or [START]
    module._now = lambda: clock[0]
    module.DAILY_REQUESTS = ceiling
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


def _loop(tmp_path, monkeypatch, rounds, start, step=timedelta(minutes=1), per_round=3, ceiling=5):
    """The console's loop, with a round that makes `per_round` requests through the client it is
    handed -- the counting happens in the real `tick()`, which is the point."""
    clock = [start]
    fw = _script(tmp_path, monkeypatch, clock=clock, ceiling=ceiling)
    ticks = []

    def capture(client, now=None):
        for _ in range(per_round):
            client.get("/api/v1/clones/memecoin-terminal/search")
        ticks.append(clock[0])
        return {}

    monkeypatch.setattr(fw, "capture", capture)
    monkeypatch.setattr(fw, "resolve", lambda client, now=None, cap=None: {})
    client = _Client()
    fw.run(_Stop(rounds, clock, step), every=60, client=client)
    return fw, client, ticks


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_rounds_stop_for_the_rest_of_the_day_once_the_ceiling_is_reached(tmp_path, monkeypatch):
    fw, client, ticks = _loop(tmp_path, monkeypatch, rounds=6, start=START)
    assert len(ticks) == 2, f"3 + 3 requests reach the ceiling of 5; the next four rounds wait ({len(ticks)} ran)"
    assert client.calls == 6, "every request went through to the real client, and was counted"
    assert fw.requests_today() == 6


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_new_utc_day_starts_the_count_again(tmp_path, monkeypatch):
    start = datetime(2026, 10, 18, 23, 57, tzinfo=timezone.utc)
    _, client, ticks = _loop(tmp_path, monkeypatch, rounds=6, start=start)
    assert [t.date().isoformat() for t in ticks] == ["2026-10-18", "2026-10-18", "2026-10-19", "2026-10-19"], ticks


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_ceiling_sits_far_under_the_day_that_asked_for_it():
    spec = importlib.util.spec_from_file_location("fomo_watch_ceiling_constant",
                                                  REPO / "scripts" / "fomo_watch.py")
    fw = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(fw)
    assert 0 < fw.DAILY_REQUESTS <= 48_557 // 4, (
        f"{fw.DAILY_REQUESTS} a day: the 2026-10-09 volume that REPLY-0030 rules out was 48,557")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_counting_client_hands_everything_else_to_the_real_one(tmp_path, monkeypatch):
    fw = _script(tmp_path, monkeypatch)
    real = _Client()
    counted = fw._Counted(real)
    counted.close()
    assert real.closed, "close() reaches the real client"
    assert counted.get("/x") == "/x" and fw.requests_today() == 1 and real.calls == 1


# --- every path that runs a round: the lab's, a hand run's --------------------------------------


def _platform(calls):
    """Both chains answer with nothing new: two requests a round, nothing else due."""
    from qa.client import build_mock_client

    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(200, json={"rows": []})
    return build_mock_client(handler, timeout=5.0)


def _lab(tmp_path, monkeypatch, calls, clock, ceiling=5):
    lab = _scripts_lab(tmp_path, monkeypatch)
    real_sibling = lab._sibling

    def sibling(name):
        module = real_sibling(name)
        if name == "fomo_watch":
            module._client = lambda: _platform(calls)
            module._now = lambda: clock[0]
            module.DAILY_REQUESTS = ceiling
        return module

    monkeypatch.setattr(lab, "_sibling", sibling)
    return lab


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_lab_round_is_held_by_a_day_the_console_spent(tmp_path, monkeypatch):
    _loop(tmp_path, monkeypatch, rounds=3, start=START)          # the console: 6 of 5 spent
    calls: list = []
    lab = _lab(tmp_path, monkeypatch, calls, [START + timedelta(minutes=5)])
    said = lab._fomo_round()
    assert calls == [], f"the lab's round asked their host past the day's ceiling: {calls}"
    assert said.get("held") and "ceiling" in said["held"], said

    lines = []
    lab._say_tick({"session": "LAB-0001", "at": "2026-10-18T09:05:00", "skipped": "",
                   "fomo": said, "hot": {"by": "console"}, "sample": None, "backtests": 0,
                   "known": 0, "cycled": False, "rooms": 0, "orders": 0, "verdicts": 0,
                   "held": [], "decide": [], "may_ask": False, "why": "test", "errors": []},
                  lines.append)
    assert "memecoins held" in lines[0], lines[0]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_labs_own_rounds_are_counted(tmp_path, monkeypatch):
    """Each lab round loads the script afresh (`_sibling`), as each tick is a new process: a count
    held in memory starts at zero every time."""
    calls: list = []
    clock = [START]
    lab = _lab(tmp_path, monkeypatch, calls, clock)
    said = []
    for _ in range(4):
        said.append(lab._fomo_round())
        clock[0] += timedelta(minutes=20)
    assert len(calls) == 6, f"2 + 2 + 2 reach the ceiling of 5, the fourth round waits ({len(calls)} made)"
    assert said[3].get("held"), said
    assert _script(tmp_path, monkeypatch, "fomo_watch_reader", clock=[START]).requests_today() == 6


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_hand_run_is_counted_and_held(tmp_path, monkeypatch, capsys):
    calls: list = []
    fw = _script(tmp_path, monkeypatch, ceiling=3)
    fw._client = lambda: _platform(calls)
    assert fw._run(fw.capture) == 0
    assert len(calls) == 2 and fw.requests_today() == 2
    assert fw._run(fw.capture) == 0                          # 2 < 3: runs, ends at 4
    assert fw._run(fw.capture) == 0                          # 4 >= 3: held
    assert len(calls) == 4, calls
    assert "ceiling" in capsys.readouterr().out


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_unreadable_count_is_a_spent_day_not_a_fresh_one(tmp_path, monkeypatch):
    """Rule 8 on our own file: a count we cannot read is not zero. The day is held, and the next UTC
    day starts clean."""
    clock = [START]
    fw = _script(tmp_path, monkeypatch, clock=clock)
    fw.requests_path().write_text("{not json", encoding="utf-8")
    calls: list = []
    said = fw.tick(_platform(calls))
    assert said.get("held") and calls == [], said
    clock[0] += timedelta(days=1)
    assert fw.tick(_platform(calls)).get("held") is None and len(calls) == 2
