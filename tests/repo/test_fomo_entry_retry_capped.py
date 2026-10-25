"""An entry retry is one of the round's quotes: inside its cap, and shared with the coin's checkpoint
(deep pass 2026-10-25, M05).

`resolve()` promises "at most `cap` coins quoted" and one quote per coin per round (262 quotes for 89
coins in one round of 2026-09-19 is why). The entry retries -- a signal that fired with no price,
quoted once more inside its first hour -- called `_listing` directly, ahead of both: uncounted against
the cap, and a second search for a coin whose +15 min checkpoint was due in the same round.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
T0 = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)


def _watch(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    spec = importlib.util.spec_from_file_location("fomo_watch_entry_cap",
                                                  REPO / "scripts" / "fomo_watch.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _terminal(asked):
    from qa.client import build_mock_client

    def handler(request):
        asked.append(request.url.params.get("q"))
        return httpx.Response(200, json={"rows": [
            {"address": request.url.params.get("q"), "price_usd": 0.003}]})
    return build_mock_client(handler, timeout=5.0)


def _unpriced(mod, token, at=T0):
    mod._append({"type": "signal", "at": at.isoformat(), "key": f"{token}:{at:%Y-%m-%dT%H}",
                 "token_address": token, "chain": "solana", "price_usd": None})


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_entry_retry_and_its_coins_checkpoint_share_one_quote(tmp_path, monkeypatch):
    mod = _watch(tmp_path, monkeypatch)
    _unpriced(mod, "SoLone")
    asked: list = []
    said = mod.resolve(_terminal(asked), now=T0 + timedelta(minutes=15))
    assert (said["entries"], said["checked"]) == (1, 1), said
    assert asked == ["SoLone"], f"one coin, one moment, {len(asked)} searches: {asked}"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_entry_retries_spend_the_rounds_cap(tmp_path, monkeypatch):
    mod = _watch(tmp_path, monkeypatch)
    _unpriced(mod, "SoLa")
    _unpriced(mod, "SoLb")
    asked: list = []
    # Five minutes in: nothing is due but the two retries, and the round may quote one coin.
    said = mod.resolve(_terminal(asked), now=T0 + timedelta(minutes=5), cap=1)
    assert len(asked) == 1, f"a round capped at one coin quoted {len(asked)}: {asked}"
    assert (said["entries"], said["deferred"]) == (1, 1), said
    # The one held back is still young, and is read on the next round.
    again = mod.resolve(_terminal(asked), now=T0 + timedelta(minutes=6), cap=1)
    assert again["entries"] == 1 and len(set(asked)) == 2, (again, asked)
