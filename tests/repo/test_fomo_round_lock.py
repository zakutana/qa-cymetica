"""One FOMO round at a time, across every process (deep pass 2026-10-25, M06).

The console runs a round a minute in a thread (`serve.py --fomo`), the lab tick runs one in its own
process every twenty minutes unless the console says it collects, and anyone can run `fomo_watch.py
capture` or `resolve` by hand. Nothing held a round whole: two that overlapped both read the diary
before either wrote, and both wrote the same signal (or the same checkpoint) -- a coin counted twice in
the study, and a second search spent on it. A round now takes `state/fomo_round.lock` without waiting;
one that finds it held makes no request, writes nothing, and says it skipped.

Two loads of the script on one state directory stand in for two processes.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime, timezone
from pathlib import Path

import httpx

from qa.marks import SafetyTier, qa
from tests.repo.test_card_leg_exit import _scripts_lab

REPO = Path(__file__).resolve().parent.parent.parent
T0 = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)


def _watch(tmp_path, monkeypatch, name):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / "fomo_watch.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module._now = lambda: T0
    return module


def _client(handler):
    from qa.client import build_mock_client

    return build_mock_client(handler, timeout=5.0)


def _platform(calls, during_search=None):
    """One hot coin on solana. `during_search` runs inside the first price search -- a second round
    landing while the first is in flight."""
    def handler(request):
        calls.append(str(request.url))
        if "fomo-radar/signals" in str(request.url):
            if request.url.params.get("chain") != "solana" or request.url.params.get("filter") != "hot":
                return httpx.Response(200, json={"rows": []})
            return httpx.Response(200, json={"rows": [
                {"token_address": "SoLhot", "hot": True, "symbol": "HOT"}]})
        if during_search is not None and not during_search.get("done"):
            during_search["done"] = True
            during_search["said"] = during_search["round"]()
        return httpx.Response(200, json={"rows": [
            {"address": request.url.params.get("q"), "price_usd": 0.002}]})
    return handler


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_round_that_lands_inside_another_skips_it(tmp_path, monkeypatch):
    first = _watch(tmp_path, monkeypatch, "fomo_watch_round_first")
    second = _watch(tmp_path, monkeypatch, "fomo_watch_round_second")
    inner_calls: list = []
    nested = {"round": lambda: second.tick(_client(_platform(inner_calls)))}
    outer_calls: list = []
    first.tick(_client(_platform(outer_calls, during_search=nested)))

    keys = [r["key"] for r in first.load() if r.get("type") == "signal"]
    assert keys == ["solhot:2026-09-13T12"], f"two overlapping rounds wrote one coin twice: {keys}"
    assert inner_calls == [], f"the round that found another running asked their host: {inner_calls}"
    assert nested["said"].get("skipped"), nested["said"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_lab_round_and_a_hand_run_skip_while_a_round_runs(tmp_path, monkeypatch, capsys):
    holder = _watch(tmp_path, monkeypatch, "fomo_watch_round_holder")
    lab = _scripts_lab(tmp_path, monkeypatch)
    calls: list = []
    real_sibling = lab._sibling

    def sibling(name):
        module = real_sibling(name)
        if name == "fomo_watch":
            module._client = lambda: _client(_platform(calls))
            module._now = lambda: T0
        return module

    monkeypatch.setattr(lab, "_sibling", sibling)
    hand = _watch(tmp_path, monkeypatch, "fomo_watch_round_hand")
    hand._client = lambda: _client(_platform(calls))

    with holder.round_lock() as held:
        assert held
        said = lab._fomo_round()
        assert hand._run(hand.capture) == 0
    assert calls == [], f"a round ran beside the one holding the lock: {calls}"
    assert said.get("skipped"), said
    assert "another round" in capsys.readouterr().out
    assert not [r for r in holder.load() if r.get("type") == "signal"]

    lines = []
    lab._say_tick({"session": "LAB-0001", "at": "2026-09-13T12:00:00", "skipped": "",
                   "fomo": said, "hot": {"by": "console"}, "sample": None, "backtests": 0,
                   "known": 0, "cycled": False, "rooms": 0, "orders": 0, "verdicts": 0,
                   "held": [], "decide": [], "may_ask": False, "why": "test", "errors": []},
                  lines.append)
    assert "memecoins skipped" in lines[0], lines[0]

    # Released, the next round runs.
    assert lab._fomo_round()["added"] == 1 and calls
