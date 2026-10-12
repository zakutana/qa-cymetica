"""The league's ET10 line must read ALL of our prize records, not the newest fifty (T-0018).

2026-10-12: GET /agent-league/prizes answers the newest 50 records and no more, with no total and
no next page; `?limit=200` returns all 90, `offset`/`page`/`status`/`player_id` are ignored. Eight
of our records (ids 4, 5, 9-14, 1,000 ET10 each, credited 2026-10-09/10) sat past that window, so
`scripts/league.py summary()` printed "0 ET10 credited, 2 prize(s)" while the full list says 8,000
credited and 2 capped. It is the 'a slice I can query is not the composition' mistake again.

The fix is in scripts/league.py (workers cannot write there): ask `/prizes` with `limit=200` in
`summary()` -- and say "unread" if the answer is a full window of 200, since then the list may
still be cut. This test fails on the ASSERTION until then; strict, so it turns red the day it is
fixed and the marker must go.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa

WINDOW = 50


def _script():
    spec = importlib.util.spec_from_file_location(
        "league_script_window", Path(__file__).resolve().parents[2] / "scripts" / "league.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _prizes():
    """Ninety records, newest first: ours credited at the oldest end, capped at the newest."""
    rows = []
    for pid in range(90, 0, -1):
        ours = pid in (90, 63) or pid in (4, 5, 9, 10, 11, 12, 13, 14)
        rows.append({"id": pid, "player_id": 2 if ours else 1,
                     "amount_et10": 1000.0,
                     "status": "capped" if pid > 36 else "credited"})
    return rows


class _Reply:
    def __init__(self, body):
        self.status_code, self._body = 200, body

    def json(self):
        return self._body


class _Client:
    def get(self, url, params=None):
        params = params or {}
        if url.endswith("/me"):
            return _Reply({"players": [{"id": 2}]})
        if url.endswith("/players/2"):
            return _Reply({"id": 2, "answers": 28, "mean_score": 0.9999,
                           "division_name": "Championship", "points": 0})
        rows = _prizes()
        # Their behaviour as read 2026-10-12: newest fifty unless `limit` is given.
        return _Reply({"terms": {}, "month_committed_et10": 49500.0,
                       "prizes": rows[:int(params.get("limit", WINDOW))]})

    def close(self):
        pass


@pytest.mark.xfail(strict=True, reason="league.summary() reads the default window of 50 prize "
                   "records; 8,000 ET10 of ours sit beyond it (T-0018)")
@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_summary_counts_credited_prizes_beyond_the_default_window(monkeypatch):
    script = _script()
    monkeypatch.setattr(script, "_client", lambda write=False: _Client())
    monkeypatch.setattr(script, "_get", lambda client, url, **params: client.get(url, params))
    monkeypatch.setattr(script, "load", lambda: [])
    said = script.summary()
    assert said["prizes"] == 10, said
    assert said["et10_credited"] == 8000, said
