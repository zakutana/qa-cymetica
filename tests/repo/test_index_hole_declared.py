"""The card-history check counts only a hole the history does not declare (deep pass 2026-10-15).

Cymetica's fix of #202 (REPLY-0168, verified live 2026-10-15): readings that were never taken are not
filled in, and `index-history` now lists every gap as {from, to, hours} beside `gaps_note`. The
hole on a4a5b71e (2026-09-23 14:16 to 09-25 17:54, 51.6 h) is declared; one the list leaves out is
still a defect.
"""

from qa.marks import SafetyTier, qa
from tests.rest.test_a_live_crypto_card_index_history_has_no_multi_day_hole import declared, undeclared_holes

DECLARED = [{"from": "2026-09-23T14:16:52.413185+00:00", "to": "2026-09-25T17:54:33.881116+00:00", "hours": 51.6}]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_hole_the_history_lists_is_declared():
    assert declared("2026-09-23T14:16:52.413185+00:00", "2026-09-25T17:54:33.881116+00:00", DECLARED)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_hole_the_history_does_not_list_is_not_declared():
    assert not declared("2026-10-01T00:00:00+00:00", "2026-10-02T06:00:00+00:00", DECLARED)
    assert not declared("2026-09-23T14:16:52+00:00", "2026-09-25T17:54:33+00:00", [])
    assert not declared("2026-09-23T14:16:52+00:00", "2026-09-25T17:54:33+00:00", None)


def _series(*hours):
    from datetime import datetime, timedelta, timezone
    start = datetime(2026, 9, 20, tzinfo=timezone.utc)
    return [{"t": (start + timedelta(hours=h)).isoformat(), "index": 100.0} for h in hours]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_hole_is_asked_not_only_the_widest():
    """A03 / B03, deep pass 2026-10-15: a declared 51.6 h hole must not hide an undeclared
    20 h one on the same card."""
    points = _series(0, 3, 6, 57.6, 60.6, 80.6, 83.6)          # holes: 51.6 h (6..57.6), 20 h (60.6..80.6)
    declared_gap = [{"from": points[2]["t"], "to": points[3]["t"], "hours": 51.6}]
    holes = undeclared_holes(points, declared_gap, 12.0)
    assert [round(h[0], 1) for h in holes] == [20.0], holes
    assert undeclared_holes(points, declared_gap + [{"from": points[4]["t"], "to": points[5]["t"]}], 12.0) == []
    assert [round(h[0], 1) for h in undeclared_holes(points, [], 12.0)] == [51.6, 20.0]
    assert undeclared_holes(_series(0, 3, 6, 9), [], 12.0) == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_declared_gap_that_covers_only_part_of_the_hole_does_not_declare_it():
    part = [{"from": "2026-09-23T14:16:52+00:00", "to": "2026-09-24T02:00:00+00:00", "hours": 11.7}]
    assert not declared("2026-09-23T14:16:52+00:00", "2026-09-25T17:54:33+00:00", part)
