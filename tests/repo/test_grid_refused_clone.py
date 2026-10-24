"""The grid does not clone a species again every tick after a clone that failed (crew-before-c9 point 9).

`wave.launch_one` returns before any room when the clone itself fails, so the register has no row,
GRID_LAUNCH_TRIES (which counts stopped rooms) never counts it, and `grid_next` proposes the same
cell on the next tick. The capacity refusal is T-0009's spec (tests/repo/test_grid_capacity.py).
This is the rest of point 9: a refusal that is not the cap (their 400/409 on the species) and a
clone whose POST timed out after it left -- `unknown`, it may have landed, and every retry can be
one more unlinked paper clone, every 20 minutes. Such a species waits `CLONE_RETRY_AFTER` after its
last failed clone, and after GRID_LAUNCH_TRIES of them is left until a clone of it is accepted.

The fixtures are the laboratory loop's own, as test_grid_capacity.py uses them: nothing reaches
their side.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

from qa import lab
from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
_SPEC = importlib.util.spec_from_file_location(
    "lab_loop_fixtures_refused", REPO / "tests" / "meta" / "test_pipeline_lab_loop.py")
loop = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(loop)

CAPACITY = ('{"detail": {"error": {"code": "INVALID_CLONE_REQUEST", "message": "Maximum 50 '
            'Paper bots per user including paused ones"}}}')


def _clone(rows: list, n: int, species: str, hours_ago: float, now: datetime,
           outcome: str | None, response: str = "") -> None:
    at = (now - timedelta(hours=hours_ago)).isoformat()
    cid = f"CLN-{n:04d}"
    rows.append({"id": cid, "type": "intent", "at": at, "source_type": "wta_species",
                 "source_id": species, "paper": True})
    if outcome:
        rows.append({"id": cid, "type": "outcome", "at": at, "outcome": outcome,
                     "http_status": 400 if outcome == "rejected" else None,
                     "clone_instance_id": f"inst-{n}" if outcome == "accepted" else None,
                     "response": response})


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_which_species_a_failed_clone_holds():
    now = datetime(2026, 10, 25, 12, 0, tzinfo=timezone.utc)
    after = lab.CLONE_RETRY_AFTER.total_seconds() / 3600

    def held(*clones) -> dict:
        rows: list = []
        for n, (species, hours, outcome, *body) in enumerate(clones, 1):
            _clone(rows, n, species, hours, now, outcome, *body)
        return lab.clone_failures(rows, now)

    assert "sp-a" in held(("SP-A", after / 2, "unknown")), "a clone that may have landed, again"
    assert held(("sp-a", after + 1, "unknown")) == {}, "held for good by one timeout"
    assert "sp-a" in held(("sp-a", after / 2, None)), "an intent with no outcome may have landed"
    assert "sp-a" in held(("sp-a", after / 2, "rejected", '{"detail": "Invalid clone request."}'))
    three = [("sp-a", after * (4 - k), "rejected", "{}") for k in range(lab.GRID_LAUNCH_TRIES)]
    assert "sp-a" in held(*[(s, h + 100, o, b) for s, h, o, b in three]), "tried past its tries"
    assert held(*[(s, h + 100, o, b) for s, h, o, b in three], ("sp-a", 50, "accepted")) == {}, (
        "an accepted clone of the species since")
    assert held(("sp-a", 0.1, "rejected", CAPACITY)) == {}, "the cap is T-0009's rule, not this"
    assert held(("sp-a", 0.1, "not_sent")) == {}, "nothing left our side: nothing to land"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_grid_skips_a_species_whose_clone_just_timed_out(tmp_path, monkeypatch):
    scripts_lab = loop._scripts_lab(tmp_path, monkeypatch)
    _, calls = loop._clonepad(scripts_lab, tmp_path, monkeypatch, [])
    monkeypatch.setattr(lab, "GRID_PER_TICK", 3)
    clone = scripts_lab._sibling("clone")
    now = datetime.now(timezone.utc)
    rows: list = []
    _clone(rows, 1, loop.TITAN["id"], 0.5, now, "unknown")
    for row in rows:
        clone._append(row)

    did = scripts_lab.bot_grid()

    cloned = [c[2] for c in calls if c[0] == "clone"]
    assert loop.TITAN["id"] not in cloned, cloned
    assert cloned == [loop.MACD["id"], loop.DOOM["id"], loop.LIQ["id"]], cloned
    assert any("Trend Titan" in h and "CLN-0001" in h for h in did["held"]), did["held"]
