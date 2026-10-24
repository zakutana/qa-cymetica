"""The patrol holds our daily volume on their host, not only its busiest minute (NEXT.md 2026-10-18).

docs/crew-before-c9.md point 10: on 2026-10-09 we made 48,557 requests to cymetica.com (39,784 of them
the FOMO collector's, to a route absent from /api-docs) while REPLY-0030 asks for no load or volume
testing. The patrol's only traffic ceiling was `peak_requests_per_minute` (70): the brake holds every
process to 60 a minute, which still allows 86,400 a day, so a flat ~2,000 an hour never lit it. The
collector got its own 10,000-a-day cap on 2026-10-18 (1b636163); the patrol, which sees every process's
requests in state/timings.jsonl, now holds the day too.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _module():
    spec = importlib.util.spec_from_file_location("processes_daily", REPO / "scripts" / "processes.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _timings(root: Path, days: dict, host: str = "cymetica.com") -> None:
    """`days` maps a UTC date to how many requests it holds. Each day's rows are spread one minute
    apart in runs of 50, so no minute passes the per-minute ceiling and only the day can fire."""
    target = root / "state" / "timings.jsonl"
    target.parent.mkdir(parents=True, exist_ok=True)
    with open(target, "a", encoding="utf-8") as fh:
        for day, count in days.items():
            start = datetime.combine(day, datetime.min.time(), tzinfo=timezone.utc)
            for n in range(count):
                at = (start + timedelta(minutes=n // 50)).isoformat(timespec="seconds")
                fh.write(json.dumps({"at": at, "method": "GET", "host": host, "path": "/x",
                                     "status": 200}) + "\n")


def _days_ago(n: int):
    # Stamped from now, never a fixed date: a fixed date slides out of the patrol's seven-day window
    # and the fixture then counts zero (B06, deep pass 2026-10-15). Whole days before today, so every
    # row is inside the window whatever the hour.
    return (datetime.now(timezone.utc) - timedelta(days=n)).date()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_day_over_the_ceiling_lights_the_patrol(tmp_path):
    mod = _module()
    ceiling = mod.CEILINGS["peak_requests_per_day"]
    # The ceiling stays under the day that prompted it and above an honest day without the collector.
    assert 19_359 < ceiling < 48_557, ceiling
    _timings(tmp_path, {_days_ago(2): ceiling + 1})
    measured = mod.sizes(tmp_path)
    assert measured["peak_requests_per_day"] == ceiling + 1, measured
    assert measured["peak_requests_per_minute"] <= mod.CEILINGS["peak_requests_per_minute"], (
        "the fixture was meant to be quiet in every minute, so only the day fires")
    lines = mod.flags({"parts": {}, "sizes": measured})
    assert any(line.startswith("peak_requests_per_day") for line in lines), lines


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_same_volume_over_two_days_and_another_host_lights_nothing(tmp_path):
    mod = _module()
    ceiling = mod.CEILINGS["peak_requests_per_day"]
    half = ceiling // 2 + 1
    _timings(tmp_path, {_days_ago(3): half, _days_ago(2): half})
    # Requests to a host that is not theirs are not their load.
    _timings(tmp_path, {_days_ago(2): ceiling}, host="api.coingecko.com")
    measured = mod.sizes(tmp_path)
    assert measured["peak_requests_per_day"] == half, measured
    assert not [line for line in mod.flags({"parts": {}, "sizes": measured})
                if line.startswith("peak_requests_per_day")]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_day_older_than_the_window_is_not_held_against_today(tmp_path):
    """The window is the per-minute ceiling's: the last seven days, and nothing before the brake. A
    week-old flood is the week's history, not a warning that can never clear (the defect of a
    ceiling over a growing log)."""
    mod = _module()
    _timings(tmp_path, {_days_ago(9): mod.CEILINGS["peak_requests_per_day"] + 1, _days_ago(1): 10})
    assert mod.sizes(tmp_path)["peak_requests_per_day"] == 10
