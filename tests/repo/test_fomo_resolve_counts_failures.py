"""A failed read in `fomo_watch.resolve()` is a failure, not a checkpoint (deep pass 2026-10-25, M02).

Since RM03 (2026-09-24) a 503 writes nothing to the diary -- but `resolve()` still put an error dict
into the same list as the rows it wrote, so `checked` and `studied` counted the failed reads as
checkpoints taken. During an outage the lab tick printed "memecoins +0 signal(s) / 5 checkpoint(s)",
a round that read nothing said as a round that read five (rule 8, one level up from the row). The meta
test of RM03 allowed it: `checked == 0 or all(error)`. Here a count of checkpoints counts rows written,
and the failures are a count of their own, carried to the tick's line.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from qa.marks import SafetyTier, qa
from tests.repo.test_card_leg_exit import _scripts_lab

REPO = Path(__file__).resolve().parent.parent.parent
T0 = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)


def _watch(tmp_path, monkeypatch, name="fomo_watch_failures"):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / "fomo_watch.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _client(handler):
    from qa.client import build_mock_client

    return build_mock_client(handler, timeout=5.0)


def _terminal_down(request):
    """Their feed answers and lists nothing new; their terminal is down."""
    if "fomo-radar/signals" in str(request.url):
        return httpx.Response(200, json={"rows": []})
    return httpx.Response(503, json={"detail": "upstream"})


def _due(mod):
    """At T0+1h: one signal's 1h checkpoint and an older one's 30h study reading are due."""
    mod._append({"type": "signal", "at": T0.isoformat(), "key": "0xabc:2026-09-13T12",
                 "token_address": "0xabc", "chain": "robinhood", "price_usd": 0.002})
    old = T0 - timedelta(hours=29)
    mod._append({"type": "signal", "at": old.isoformat(), "key": f"0xold:{old:%Y-%m-%dT%H}",
                 "token_address": "0xold", "chain": "robinhood", "price_usd": 0.002})


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_failed_read_is_counted_as_a_failure_not_as_a_checkpoint(tmp_path, monkeypatch):
    mod = _watch(tmp_path, monkeypatch)
    _due(mod)
    down = mod.resolve(_client(_terminal_down), now=T0 + timedelta(hours=1))

    assert not [r for r in mod.load() if r.get("type") in ("checkpoint", "study")], (
        "an outage wrote a reading")
    assert (down["checked"], down["studied"]) == (0, 0), (
        f"failed reads counted as readings taken: {down}")
    assert down["checkpoints"] == [], down
    assert down.get("failed") == 2, f"two reads failed and the round must say so: {down}"

    # The same round with their terminal up: two readings, no failure.
    def up(request):
        return httpx.Response(200, json={"rows": [
            {"address": request.url.params.get("q"), "price_usd": 0.003}]})
    ok = mod.resolve(_client(up), now=T0 + timedelta(hours=1, minutes=1))
    assert (ok["checked"], ok["studied"], ok.get("failed")) == (1, 1, 0), ok


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_lab_tick_says_the_failed_reads(tmp_path, monkeypatch):
    """Through the lab's own round, `_fomo_round`, and the line `_say_tick` prints from it."""
    lab = _scripts_lab(tmp_path, monkeypatch)
    _due(_watch(tmp_path, monkeypatch, "fomo_watch_seed"))
    real_sibling = lab._sibling

    def sibling(name):
        module = real_sibling(name)
        if name == "fomo_watch":
            module._client = lambda: _client(_terminal_down)
            module._now = lambda: T0 + timedelta(hours=1)
        return module

    monkeypatch.setattr(lab, "_sibling", sibling)
    monkeypatch.setattr(lab, "_now", lambda: T0 + timedelta(hours=1))
    said = lab._fomo_round()
    assert said["checked"] == 0 and said.get("failed") == 2, said

    lines = []
    lab._say_tick({"session": "LAB-0001", "at": "2026-09-13T13:00:00", "skipped": "",
                   "fomo": said, "hot": {"by": "console"}, "sample": None, "backtests": 0,
                   "known": 0, "cycled": False, "rooms": 0, "orders": 0, "verdicts": 0,
                   "held": [], "decide": [], "may_ask": False, "why": "test", "errors": []},
                  lines.append)
    assert "2 read(s) failed" in lines[0], lines[0]
