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

2026-10-17: built (REPLY-0182), both markers gone. The list holds 246 rows and 200 is its ceiling
(`limit=201` is a 422; offset, page, player_id and status are ignored), so the full window is the
live case: our eight credited prizes (ids 4-14) can no longer be read by anyone.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

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


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_summary_counts_credited_prizes_beyond_the_default_window(monkeypatch):
    script = _script()
    monkeypatch.setattr(script, "_client", lambda write=False: _Client())
    monkeypatch.setattr(script, "_get", lambda client, url, **params: client.get(url, params))
    monkeypatch.setattr(script, "load", lambda: [])
    said = script.summary()
    assert said["prizes"] == 10, said
    assert said["et10_credited"] == 8000, said


class _FullClient(_Client):
    """The window full to the brim: 200 rows at limit=200, so more may lie past it."""

    def get(self, url, params=None):
        if url.endswith("/prizes"):
            row = _prizes()[0]
            return _Reply({"terms": {}, "month_committed_et10": 49500.0,
                           "prizes": [dict(row, id=f"P-{i}") for i in range(200)]})
        return super().get(url, params)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_full_window_of_prizes_is_said_unread_not_counted_as_the_total(monkeypatch):
    """B05, deep pass 2026-10-15: a limit=200-only fix reports a cut list as the whole."""
    script = _script()
    monkeypatch.setattr(script, "_client", lambda write=False: _FullClient())
    monkeypatch.setattr(script, "_get", lambda client, url, **params: client.get(url, params))
    monkeypatch.setattr(script, "load", lambda: [])
    said = script.summary()
    assert said.get("prizes") is None and "unread" in str(said).lower(), said
    # B03, deep pass 2026-10-18: the total itself, not only the count -- a sum over the cut list
    # (every fixture row capped, so 0) is the T-0018 undercount said as a figure
    assert said["et10_credited"] is None, said
    assert any("ET10 credited: unread" in line for line in said["lines"]), said


class _DefaultWindowClient(_Client):
    """A server that drops `limit` and answers its default newest fifty again (before REPLY-0182)."""

    def get(self, url, params=None):
        return super().get(url, {k: v for k, v in (params or {}).items() if k != "limit"})


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_list_cut_at_its_default_fifty_is_said_unread_not_counted_as_the_total(monkeypatch):
    """R05, deep pass 2026-10-18: `cut` was only ever 200 rows, so a /prizes that ignores `limit`
    answers 50, and the 2 capped prizes of ours among them were printed as the whole (0 ET10)
    while 8 credited ones lay older. A count equal to a window the server cuts at cannot tell
    "all of them" from "the newest N"."""
    script = _script()
    monkeypatch.setattr(script, "_client", lambda write=False: _DefaultWindowClient())
    monkeypatch.setattr(script, "_get", lambda client, url, **params: client.get(url, params))
    monkeypatch.setattr(script, "load", lambda: [])
    said = script.summary()
    assert said.get("prizes") is None and said["et10_credited"] is None, said
    assert any("ET10 credited: unread" in line for line in said["lines"]), said


class _ShortClient(_Client):
    """Fewer rows than any window: the list is all there is, and is counted."""

    def get(self, url, params=None):
        if url.endswith("/prizes"):
            rows = [r for r in _prizes() if r["id"] <= 30]
            return _Reply({"terms": {}, "month_committed_et10": 0.0, "prizes": rows})
        return super().get(url, params)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_list_shorter_than_every_window_is_the_whole_and_is_counted(monkeypatch):
    """The other side of R05: an unread verdict on every answer would also pass the test above."""
    script = _script()
    monkeypatch.setattr(script, "_client", lambda write=False: _ShortClient())
    monkeypatch.setattr(script, "_get", lambda client, url, **params: client.get(url, params))
    monkeypatch.setattr(script, "load", lambda: [])
    said = script.summary()
    assert said["prizes"] == 8 and said["et10_credited"] == 8000, said
