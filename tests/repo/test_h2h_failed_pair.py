"""A head-to-head pair that never started is tried again -- later, and not for ever (crew-before-c9 point 11).

`h2h_step` (scripts/lab.py) counted a cell as paired as soon as ANY h2h room named it, so a pair
whose launch stopped before a verdict (a clone refused, a read timed out) held its cell for good:
the improved bot was never put against its defaults. The opposite was R08 (deep pass 2026-10-11):
a pair cloned again every tick the second clone keeps failing leaves one more clone each time. So
the grid's rule, spaced: a launch that never ran is tried again, at most `GRID_LAUNCH_TRIES` times,
and not before `H2H_RETRY_AFTER` since the last one stopped. A pair open or judged holds its cell.

The fixtures are the laboratory loop's own (tests/meta/test_pipeline_lab_loop.py), as
tests/repo/test_grid_capacity.py uses them: clone.py stubbed, nothing reaches their side.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

from qa import lab
from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
_SPEC = importlib.util.spec_from_file_location(
    "lab_loop_fixtures_h2h", REPO / "tests" / "meta" / "test_pipeline_lab_loop.py")
loop = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(loop)

KEY = "bot:sp-a:SL 10 / TP 20"


def _row(status: str, verdict: str | None, hours_ago: float, now: datetime) -> dict:
    return {"room": "STR-x", "section": "h2h", "key": KEY, "status": status, "verdict": verdict,
            "at": (now - timedelta(hours=hours_ago)).isoformat()}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_which_cells_a_head_to_head_holds():
    now = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
    after = lab.H2H_RETRY_AFTER.total_seconds() / 3600
    failed = lambda hours: _row("stopped", None, hours, now)  # noqa: E731
    assert lab.h2h_paired([failed(after / 2)], now) == {KEY}, "retried before its spacing"
    assert lab.h2h_paired([failed(after + 1)], now) == set(), "a failed pair held for good"
    assert lab.h2h_paired([failed(after + 3)] * lab.GRID_LAUNCH_TRIES, now) == {KEY}, (
        "tried past GRID_LAUNCH_TRIES")
    assert lab.h2h_paired([_row("running", None, 50, now)], now) == {KEY}, "an open pair"
    assert lab.h2h_paired([failed(after + 1), _row("stopped", "survived", 1, now)], now) == {KEY}
    # Only head-to-head rooms take a cell: the grid's own rooms are what proved it.
    assert lab.h2h_paired([{**failed(1), "section": "bots"}], now) == set()


def _proven_cell_with_a_failed_pair(tmp_path, monkeypatch, stopped_hours_ago: float):
    import qa.rooms as qa_rooms

    scripts_lab = loop._scripts_lab(tmp_path, monkeypatch)
    _, calls = loop._clonepad(scripts_lab, tmp_path, monkeypatch, [])
    band = lab.GRID_BANDS[2]
    old = (datetime.now(timezone.utc) - timedelta(days=9)).isoformat()
    stopped = (datetime.now(timezone.utc) - timedelta(hours=stopped_hours_ago)).isoformat()
    proposals, rows = [], []
    for n in (1, 2):
        proposals.append({"type": "proposal", "id": f"OUR-000{n}", "kind": "bot",
                          "ref": loop.MACD["id"], "instance": f"old-{n}", "variant": "x",
                          "settings": dict(band), "why": "grid"})
        rows += [{"type": "strategy", "id": f"STR-000{n}", "origin": f"OUR-000{n}",
                  "kind": "bot", "ref": loop.MACD["id"], "title": "Grid · MACD Hunter", "at": old},
                 {"type": "status", "room": f"STR-000{n}", "status": "stopped", "why": "x",
                  "at": old},
                 {"type": "verdict", "room": f"STR-000{n}", "verdict": "survived",
                  "return_pct": 3.0, "at": old}]
    rows += [{"type": "strategy", "id": "STR-0900", "origin": "OUR-0009", "kind": "bot",
              "ref": loop.MACD["id"], "title": "H2H · MACD Hunter", "section": "h2h",
              "settings": dict(band), "at": stopped},
             {"type": "status", "room": "STR-0900", "status": "stopped",
              "why": "the original clone was refused (their clone answered 503)", "at": stopped}]
    loop._write(tmp_path, "lab.jsonl", proposals)
    loop._write(tmp_path, "rooms.jsonl", rows)
    pinned = scripts_lab._sibling

    class H2H:
        @staticmethod
        def start_matchup(original, improved, days, title, room):
            return {"outcome": "accepted", "slug": "abc123", "room": room}

        @staticmethod
        def results():
            return []

    monkeypatch.setattr(scripts_lab, "_sibling", lambda n: H2H if n == "h2h" else pinned(n))
    did = scripts_lab.h2h_step()
    return did, [c for c in calls if c[0] == "clone"], qa_rooms.load()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_pair_that_never_started_is_paired_again_once_its_spacing_passed(tmp_path, monkeypatch):
    hours = lab.H2H_RETRY_AFTER.total_seconds() / 3600 + 1
    did, clones, stored = _proven_cell_with_a_failed_pair(tmp_path, monkeypatch, hours)
    assert len(clones) == 2 and did["orders"] == 1, (did, clones)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_pair_that_just_failed_is_not_cloned_again_yet(tmp_path, monkeypatch):
    """R08's half, from a stored record rather than inside one run."""
    hours = lab.H2H_RETRY_AFTER.total_seconds() / 3600 / 2
    did, clones, _ = _proven_cell_with_a_failed_pair(tmp_path, monkeypatch, hours)
    assert clones == [] and did["rooms"] == 0, (did, clones)
