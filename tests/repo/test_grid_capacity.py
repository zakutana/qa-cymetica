"""The bot grid follows the platform's own refusal, not a constant (T-0009, 2026-10-12).

CLN-0461 (17:01) was refused with HTTP 400 INVALID_CLONE_REQUEST "Maximum 25 trading Paper
bots per user", and tick LAB-0038 showed 25 trading. `wave.MAX_TRADING` stayed 50, so
`bot_grid` computed 25 free slots and tried a clone every tick that could not succeed, and
its held line read "not accepted (HTTP 400, rejected)" instead of saying the cap was reached.

The fixtures are the laboratory loop's own (`tests/meta/test_pipeline_lab_loop.py`): the same
stubbed clone.py, so nothing reaches their side.

THE FIX IS NOT IN YET: a worker cannot edit scripts/, qa/ or tests/meta, so these tests are the
spec, written first and marked xfail(strict) so the suite stays green. The session that makes
the change deletes `pytestmark` below (a strict xfail that passes fails loudly). What they ask
of `scripts/lab.py`:

  * `_capacity_cap(clone_rows) -> {"cap", "id", "at"} | None`: the integer in the NEWEST
    decisive (accepted/rejected) non-`kind` clone outcome whose body `lab.capacity_refusal`
    recognises; None if the newest decisive one is accepted. Both wordings: 'Maximum 25 trading
    Paper bots' and 'Maximum 50 Paper bots per user including paused ones' (T-0014) -- the second
    counts every clone we still own (accepted, not released), paused or not, the first only
    those trading.
  * `bot_grid`: cap = that number, else `wave.MAX_TRADING`; slots = cap - occupied; a refusal
    younger than 6 h holds the grid while nothing has stopped trading since it (the sampler can
    lag the platform's count); an older one lets ONE clone through as a probe; held line and
    `grid["cap"]` say 'cap reached'; a clone answered with a capacity 400 ends the tick (one
    attempt, not GRID_PER_TICK). The `wave.MAX_TRADING` comment ('25 is not their limit') is
    false since 2026-10-12 and goes.
"""

from __future__ import annotations

import importlib.util
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from qa import lab
from qa.marks import SafetyTier, qa

pytestmark = pytest.mark.xfail(
    strict=True, reason="T-0009: the grid fix is written by the operator's session, not a worker")

REPO = Path(__file__).resolve().parent.parent.parent
_SPEC = importlib.util.spec_from_file_location(
    "lab_loop_fixtures", REPO / "tests" / "meta" / "test_pipeline_lab_loop.py")
loop = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(loop)

REFUSAL = ('{"detail": {"error": {"code": "INVALID_CLONE_REQUEST", "message": '
           '"Maximum %d trading Paper bots per user (paused bots do not count) '
           '— pause one before cloning another"}}}')


# CLN-0465..0467 (17:27, T-0014): the wording moved to a cap on ALL our clones, paused ones too.
REFUSAL_TOTAL = ('{"detail": {"error": {"code": "INVALID_CLONE_REQUEST", "message": '
                 '"Maximum %d Paper bots per user including paused ones — delete one '
                 'before cloning another"}}}')


def _clone_rows(clone, refusal_cap: int | None, trading: int, refused_ago_h: float = 0.1,
                body: str = REFUSAL):
    """`trading` accepted clones of ours (each sampled as trading), then, when asked,
    the platform's capacity refusal `refused_ago_h` hours old. Returns the samples."""
    now = datetime.now(timezone.utc)
    samples = []
    for n in range(trading):
        cid = f"CLN-{n + 1:04d}"
        at = (now - timedelta(hours=refused_ago_h + 2)).isoformat()
        clone._append({"id": cid, "type": "intent", "at": at, "source_type": "wta_species",
                       "source_id": f"species-{n}", "paper": True})
        clone._append({"id": cid, "type": "outcome", "at": at, "outcome": "accepted",
                       "http_status": 200, "clone_instance_id": f"inst-{n}", "is_paper": True})
        samples.append({"type": "sample", "kind": "bot", "at": at,
                        "instance_id": f"inst-{n}", "is_trading": True})
    if refusal_cap is not None:
        cid = f"CLN-{trading + 1:04d}"
        at = (now - timedelta(hours=refused_ago_h)).isoformat()
        clone._append({"id": cid, "type": "intent", "at": at, "source_type": "wta_species",
                       "source_id": "refused-species", "paper": True})
        clone._append({"id": cid, "type": "outcome", "at": at, "outcome": "rejected",
                       "http_status": 400, "response": body % refusal_cap})
    return samples


def _grid(tmp_path, monkeypatch, *, refusal_cap, trading, refused_ago_h=0.1, refuse=False,
          sampled_trading=None, body=REFUSAL):
    """One bot_grid() tick over a clone record seeded as asked. With `refuse`, a clone the
    grid attempts is answered with the platform's capacity 400. Returns (did, clone calls)."""
    import qa.rooms as qa_rooms

    scripts_lab = loop._scripts_lab(tmp_path, monkeypatch)
    sent, calls = loop._clonepad(scripts_lab, tmp_path, monkeypatch, [])
    monkeypatch.setattr(lab, "GRID_PER_TICK", 3)
    clone = scripts_lab._sibling("clone")
    samples = _clone_rows(clone, refusal_cap, trading, refused_ago_h, body)
    if sampled_trading is not None:     # the rest were paused AFTER the refusal
        samples += [{"type": "sample", "kind": "bot", "instance_id": row["instance_id"],
                     "at": datetime.now(timezone.utc).isoformat(), "is_trading": False}
                    for row in samples[sampled_trading:]]
    qa_rooms.append_samples(samples)
    if refuse:
        def _refused(source_type, source_id, name, nexus_id, confirm):
            calls.append(("clone", source_type, source_id, nexus_id, confirm))
            cid = clone._next_id(clone.load())
            at = datetime.now(timezone.utc).isoformat()
            clone._append({"id": cid, "type": "intent", "at": at, "source_type": source_type,
                           "source_id": source_id, "paper": True})
            out = {"id": cid, "type": "outcome", "at": at, "outcome": "rejected",
                   "http_status": 400, "clone_instance_id": None, "is_paper": None,
                   "response": REFUSAL % 25}
            clone._append(out)
            return out
        clone.clone = _refused
    return scripts_lab.bot_grid(), [c for c in calls if c[0] == "clone"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_cap_is_read_from_the_newest_capacity_refusal(tmp_path, monkeypatch):
    """CLN-0058 said 'Maximum 5', CLN-0461 says 25: the newest refusal is the cap; a clone
    accepted after it means the refusal no longer binds."""
    scripts_lab = loop._scripts_lab(tmp_path, monkeypatch)
    clone = scripts_lab._sibling("clone")
    assert scripts_lab._capacity_cap(clone.load()) is None
    _clone_rows(clone, 5, 0, refused_ago_h=50)
    assert scripts_lab._capacity_cap(clone.load())["cap"] == 5
    # Stamped relative to now and after the 50 h refusal, so "newest" by time and by append order
    # agree (B06, deep pass 2026-10-15: hard-coded 2026-10-12 stamps fell behind now-50h on 10-14).
    now = datetime.now(timezone.utc)
    at = lambda hours: (now - timedelta(hours=hours)).isoformat(timespec="seconds")  # noqa: E731
    _clone_rows_newer = {"id": "CLN-0900", "type": "outcome", "at": at(2),
                         "outcome": "rejected", "http_status": 400,
                         "response": REFUSAL % 25}
    clone._append({"id": "CLN-0900", "type": "intent", "at": at(2.01),
                   "source_type": "wta_species", "source_id": "x", "paper": True})
    clone._append(_clone_rows_newer)
    assert scripts_lab._capacity_cap(clone.load())["cap"] == 25
    assert scripts_lab._capacity_cap(clone.load())["id"] == "CLN-0900"
    clone._append({"id": "CLN-0901", "type": "intent", "at": at(1),
                   "source_type": "wta_species", "source_id": "y", "paper": True})
    clone._append({"id": "CLN-0901", "type": "outcome", "at": at(0.99),
                   "outcome": "accepted", "http_status": 200, "clone_instance_id": "inst-y"})
    assert scripts_lab._capacity_cap(clone.load()) is None, "an accepted clone after the refusal"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_grid_at_the_platforms_cap_holds_and_says_so(tmp_path, monkeypatch):
    """T-0009: 2 trading of a cap of 2 they told us -> no clone attempt at all, and the held
    line says the cap was reached, not 'not accepted (HTTP 400, rejected)'."""
    did, attempts = _grid(tmp_path, monkeypatch, refusal_cap=2, trading=2)
    assert attempts == [], attempts
    assert did["rooms"] == 0 and did["orders"] == 0, did
    assert any("cap reached" in h for h in did["held"]), did["held"]
    assert did["grid"]["cap"] == 2, did["grid"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_capacity_400_stops_the_grid_for_the_tick(tmp_path, monkeypatch):
    """Nothing known yet: the first clone is answered 'Maximum 25 trading Paper bots' -> one
    attempt, not GRID_PER_TICK, no orphan room, and the held line says 'cap reached'."""
    did, attempts = _grid(tmp_path, monkeypatch, refusal_cap=None, trading=0, refuse=True)
    assert len(attempts) == 1, attempts
    assert did["rooms"] == 0 and did["orders"] == 0, did
    assert any("cap reached" in h for h in did["held"]), did["held"]
    assert not any("HTTP 400" in h for h in did["held"]), did["held"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_slots_follow_the_refusal_when_a_bot_pauses(tmp_path, monkeypatch):
    """Cap 3 told us, 2 trading now: one slot, one clone -- not the constant's 48."""
    did, attempts = _grid(tmp_path, monkeypatch, refusal_cap=3, trading=3, sampled_trading=2)
    assert len(attempts) == 1, attempts
    assert did["orders"] == 1, did


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_refusal_is_asked_again_after_six_hours_with_one_clone(tmp_path, monkeypatch):
    """A cap can be raised: a refusal older than the probe interval lets exactly one clone
    through (the refusal says 25 of 25, so the slot count alone would be zero forever)."""
    did, attempts = _grid(tmp_path, monkeypatch, refusal_cap=2, trading=2, refused_ago_h=7.0)
    assert len(attempts) == 1, attempts


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_cap_on_all_clones_counts_the_paused_ones_too(tmp_path, monkeypatch):
    """T-0014: 'Maximum 3 Paper bots per user including paused ones'. Three clones of ours,
    all paused since (0 trading): trading-only arithmetic says 3 free slots, the platform says
    none -- the grid counts every clone we still own and holds ('cap reached')."""
    did, attempts = _grid(tmp_path, monkeypatch, refusal_cap=3, trading=3, sampled_trading=0,
                          body=REFUSAL_TOTAL)
    assert attempts == [], attempts
    assert any("cap reached" in h for h in did["held"]), did["held"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_sampler_that_lags_the_platform_does_not_retry_every_tick(tmp_path, monkeypatch):
    """The sampler reads 1 trading, the platform counted 2 and refused (cap 2): the refusal
    is fresh and nothing has stopped trading since -> hold, do not ask again."""
    did, attempts = _grid(tmp_path, monkeypatch, refusal_cap=2, trading=1)
    assert attempts == [], attempts
    assert any("cap reached" in h for h in did["held"]), did["held"]
