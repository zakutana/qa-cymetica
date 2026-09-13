"""The two live rounds around qa/fomo.py. Real field shapes captured live on
2026-09-13: fomo-radar's `{"rows": [{"token_address","hot","symbol",...}]}`
and memecoin-terminal's `{"rows": [{"address","price_usd",...}]}`.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
T0 = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)


def _module(tmp_path, monkeypatch):
    import importlib

    import qa.state

    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    importlib.reload(qa.state)
    spec = importlib.util.spec_from_file_location(
        "fomo_watch_under_test", REPO / "scripts" / "fomo_watch.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _client(handler):
    from qa.client import build_mock_client

    return build_mock_client(handler, timeout=5.0)


def _fomo_row(token="0xabc", hot=True, symbol="DOGEX"):
    return {"token_address": token, "hot": hot, "symbol": symbol,
           "conviction": 0.5, "new_qualified_buyers_15m": 4}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_capture_writes_one_signal_per_token_with_its_price(tmp_path,
                                                             monkeypatch):
    mod = _module(tmp_path, monkeypatch)

    # Distinct addresses per chain -- a real Robinhood Chain address and a
    # real Solana address are never the same string.
    by_chain = {"robinhood": "0xabc", "solana": "SoLabc111"}

    def handler(request):
        url = str(request.url)
        if "fomo-radar/signals" in url:
            chain = request.url.params.get("chain")
            return httpx.Response(200, json={"rows": [_fomo_row(by_chain[chain])]})
        if "memecoin-terminal/search" in url:
            wanted = request.url.params.get("q")
            return httpx.Response(200, json={"rows": [
                {"address": wanted, "price_usd": 0.002}]})
        return httpx.Response(404)

    result = mod.capture(_client(handler), now=T0)
    assert result["added"] == 2, "one signal for each chain's own token"
    rows = mod.load()
    signals = [r for r in rows if r["type"] == "signal"]
    assert len(signals) == 2
    assert {s["token_address"] for s in signals} == set(by_chain.values())
    assert all(s["price_usd"] == 0.002 for s in signals)
    assert signals[0]["key"] == "0xabc:2026-09-13T12"

    # Running capture() again the same hour must not duplicate the signal.
    again = mod.capture(_client(handler), now=T0 + timedelta(minutes=5))
    assert again["added"] == 0
    assert len([r for r in mod.load() if r["type"] == "signal"]) == 2


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_capture_survives_a_price_lookup_that_fails(tmp_path, monkeypatch):
    """A signal is still tracked even when the price call fails -- rule 8: a
    failed read is not an empty read, and it must not cost us the signal
    itself, only the price on it."""
    mod = _module(tmp_path, monkeypatch)
    by_chain = {"robinhood": "0xdef", "solana": "SoLdef222"}

    def handler(request):
        if "fomo-radar/signals" in str(request.url):
            chain = request.url.params.get("chain")
            return httpx.Response(200, json={"rows": [_fomo_row(by_chain[chain])]})
        return httpx.Response(500)

    result = mod.capture(_client(handler), now=T0)
    assert result["added"] == 2
    signals = [r for r in mod.load() if r["type"] == "signal"]
    assert all(s["price_usd"] is None for s in signals)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_resolve_checkpoints_only_what_is_due_and_computes_our_own_return(
        tmp_path, monkeypatch):
    mod = _module(tmp_path, monkeypatch)
    mod._append({"type": "signal", "at": T0.isoformat(),
                "key": "0xabc:2026-09-13T12", "token_address": "0xabc",
                "symbol": "DOGEX", "chain": "robinhood", "conviction": 0.5,
                "price_usd": 0.002})

    def handler(request):
        assert "memecoin-terminal/search" in str(request.url)
        return httpx.Response(200, json={"rows": [
            {"address": "0xabc", "price_usd": 0.003,
             "change_h1": 999.0}]})  # their rolling window -- must be ignored

    # Not due yet, thirty minutes in.
    early = mod.resolve(_client(handler), now=T0 + timedelta(minutes=30))
    assert early["checked"] == 0

    due = mod.resolve(_client(handler), now=T0 + timedelta(hours=1, minutes=1))
    assert due["checked"] == 1
    checkpoint = due["checkpoints"][0]
    assert checkpoint["horizon"] == "1h"
    assert checkpoint["return_pct"] == 50.0, (
        f"OUR return from 0.002 to 0.003 is +50%%, not their own 999%% "
        f"rolling window: {checkpoint}")

    # The same horizon is not checkpointed twice.
    again = mod.resolve(_client(handler), now=T0 + timedelta(hours=2))
    assert again["checked"] == 0


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_run_survives_a_round_that_raises_and_stops_on_the_event(tmp_path,
                                                                  monkeypatch):
    """The same rule scripts/sampler.py::run follows: nothing a round does may
    end the loop, because this is meant to run for hours inside a server the
    operator started once. A fake `stop` (a threading.Event set after N
    waits) stands in for time."""
    import threading

    mod = _module(tmp_path, monkeypatch)
    calls = []

    def handler(request):
        calls.append(str(request.url))
        if len(calls) == 2:
            raise RuntimeError("their API is briefly unreachable")
        return httpx.Response(200, json={"rows": []})

    client = _client(handler)
    stop = threading.Event()

    class _CountingEvent(threading.Event):
        def wait(self, timeout=None):  # noqa: D102 -- stand-in for real time
            self.rounds = getattr(self, "rounds", 0) + 1
            if self.rounds >= 3:
                self.set()
            return self.is_set()

    fast_stop = _CountingEvent()
    rounds = mod.run(fast_stop, every=0, client=client)
    assert rounds == 3, "a round that raised must not end the loop early"
