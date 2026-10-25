"""A price read that failed when a signal fired is recorded as a failed read, never as an unpriced coin
(deep pass 2026-10-25, M03).

`capture()` priced each new signal (and each control) through `_quote`, which answers None on ANY
non-200. So a 503 wrote the signal with `price_usd: None` and nothing else: the row a coin their
terminal did not know yet writes (748 of 2571 signals on 2026-09-22 were read that way). Rule 8, the
shape RM03 fixed in `resolve()` a month earlier. The signal is still kept -- losing it would cost the
study a hot call (tests/meta/test_pipeline_fomo_watch.py, L01) -- but the row says its read failed, the
round counts it, and `fomo.entries` tells the two apart.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx

from qa import fomo
from qa.marks import SafetyTier, qa
from tests.repo.test_card_leg_exit import _scripts_lab

REPO = Path(__file__).resolve().parent.parent.parent
T0 = datetime(2026, 9, 13, 12, 0, tzinfo=timezone.utc)


def _watch(tmp_path, monkeypatch, name="fomo_watch_failed_quote"):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    spec = importlib.util.spec_from_file_location(name, REPO / "scripts" / "fomo_watch.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _client(handler):
    from qa.client import build_mock_client

    return build_mock_client(handler, timeout=5.0)


def _handler(search):
    """Solana lists one hot coin and one it did not call; Robinhood lists nothing."""
    def handler(request):
        if "fomo-radar/signals" in str(request.url):
            if request.url.params.get("chain") != "solana":
                return httpx.Response(200, json={"rows": []})
            rows = [{"token_address": "SoLhot", "hot": True, "symbol": "HOT"}]
            if request.url.params.get("filter") != "hot":
                rows.append({"token_address": "SoLcold", "hot": False, "symbol": "COLD"})
            return httpx.Response(200, json={"rows": rows})
        return search(request)
    return handler


def _down(request):
    return httpx.Response(503, json={"detail": "upstream"})


def _unknown(request):
    return httpx.Response(200, json={"rows": []})


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_failed_price_read_is_written_as_one(tmp_path, monkeypatch):
    mod = _watch(tmp_path, monkeypatch)
    said = mod.capture(_client(_handler(_down)), now=T0)
    rows = {r["type"]: r for r in mod.load() if r.get("type") in ("signal", "control")}
    assert set(rows) == {"signal", "control"}, "the signal and its control are kept"
    for kind, row in rows.items():
        assert row["price_usd"] is None
        assert "503" in str(row.get("quote_error")), (
            f"the {kind}'s failed read was written as a coin with no price: {row}")
    assert said.get("quote_failed") == 2, said

    # Their terminal answering and not knowing the coin is the other row, and stays it.
    (tmp_path / "unknown").mkdir()
    other = _watch(tmp_path / "unknown", monkeypatch, "fomo_watch_unknown_coin")
    said = other.capture(_client(_handler(_unknown)), now=T0)
    signal = next(r for r in other.load() if r.get("type") == "signal")
    assert signal["price_usd"] is None and "quote_error" not in signal, signal
    assert said.get("quote_failed") == 0, said


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_entries_tell_a_failed_read_from_a_coin_not_yet_known():
    at = T0.isoformat()
    rows = [{"type": "signal", "key": "a:1", "at": at, "price_usd": None,
             "quote_error": "HTTP 503"},
            {"type": "signal", "key": "b:1", "at": at, "price_usd": None},
            {"type": "signal", "key": "c:1", "at": at, "price_usd": 0.002}]
    said = fomo.entries(rows)
    assert said["unpriced_at_signal"] == 2, said
    assert said.get("failed_read_at_signal") == 1, said


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_lab_round_counts_the_failed_price_reads(tmp_path, monkeypatch):
    """Through `_fomo_round`: the signal's and the control's failed quote, and the entry retry the
    same round makes for the unpriced signal -- three failed reads, none of them a feed's."""
    lab = _scripts_lab(tmp_path, monkeypatch)
    real_sibling = lab._sibling

    def sibling(name):
        module = real_sibling(name)
        if name == "fomo_watch":
            module._client = lambda: _client(_handler(_down))
            module._now = lambda: T0
        return module

    monkeypatch.setattr(lab, "_sibling", sibling)
    said = lab._fomo_round()
    assert said["added"] == 1 and said["failed"] == 3, said
    assert fomo.entries(_watch(tmp_path, monkeypatch, "fomo_watch_reader").load())[
        "failed_read_at_signal"] == 1
