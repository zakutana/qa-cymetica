"""The look back, on demand, over a window the caller chooses.

[operator 2026-09-12] *"za tri tydny reknu at se ohledne zpet a zhodnoti jak
pracujem ... tento masivni revizni check muzu spustit vzdy a reknu pro kazdou
oblast at se ohledne dany cas"*.

Until now the only retrospective was step 11 of the deep pass: welded into it,
fired only at seven days or more, one global mark, one fixed window for
everything. This is the same reading with the window handed to the caller.

In tests/repo rather than tests/meta on purpose, the reason
test_deep_pass_process.py gives: a stale answer about our own history is worth
knowing and is not a reason to abort a session that is about to talk to the
vendor.

The script REPORTS. It writes no judgement and reaches no verdict of its own --
that belongs to whoever reads the numbers, the way `lab.py grade` hands back
"not enough data" rather than inventing a correlation.
"""

from __future__ import annotations

import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
NOW = datetime(2026, 9, 12, 18, 0, tzinfo=timezone.utc)


def _module():
    spec = importlib.util.spec_from_file_location(
        "review_under_test", REPO / "scripts" / "review.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_shape_of_window_the_operator_might_name():
    """`all`, a span, a date, and "since I last looked"."""
    review = _module()
    marks = {"lab": {"at": "2026-09-01T00:00:00+00:00"}}

    since, said = review.window("all", "lab", marks, NOW)
    assert since is None and "cel" in said.lower(), said

    since, said = review.window("30d", "lab", marks, NOW)
    assert since == NOW - timedelta(days=30), since

    since, said = review.window("2026-09-05", "lab", marks, NOW)
    assert since == datetime(2026, 9, 5, tzinfo=timezone.utc), since

    since, said = review.window("last", "lab", marks, NOW)
    assert since == datetime(2026, 9, 1, tzinfo=timezone.utc), since


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_last_without_a_mark_says_so_instead_of_quietly_meaning_all():
    """The failure that would be invisible.

    "Since the last review" with no last review is the whole history, and a
    reader told "since your last look" would read a month of findings as a
    week's. It reports the gap in words, in the line the reader sees.
    """
    review = _module()

    since, said = review.window("last", "deep-pass", {}, NOW)

    assert since is None
    assert "nikdy" in said.lower() or "žádn" in said.lower(), said


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_window_that_is_not_a_window_refuses():
    """Operator error, so the message is the whole output -- the house rule."""
    review = _module()
    for bad in ("yesterday", "30", "d30", "2026-13-01", "-5d"):
        with pytest.raises(SystemExit):
            review.window(bad, "lab", {}, NOW)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_triad_verdict_is_read_over_every_pass_not_over_the_slice():
    """`condition` judges the newest three finished passes.

    Handed a historical slice it would pronounce on a tail that is not current
    -- "the triad has stopped removing anything" about a fortnight in March,
    printed under a heading about today. The slice is what gets TABULATED; the
    verdict is computed over the lot.
    """
    review = _module()
    rows = [{"run": f"p{n}", "at": f"2026-09-0{n}T00:00:00+00:00",
             "finished": True, "claimed": 10, "real": 8, "overturned": 0,
             "fixed": 8, "voted": 9, "unanimous": 9, "rule_changes": 0}
            for n in range(1, 7)]

    seen = {}

    def _condition(given):
        seen["n"] = len(given)
        return "a sentence"

    out = review.area_deep_pass(
        since=datetime(2026, 9, 5, tzinfo=timezone.utc),
        passes=lambda: rows, condition=_condition)

    assert seen["n"] == len(rows), (
        f"condition saw {seen['n']} of {len(rows)} passes -- it must see all")
    assert len(out["passes"]) == 2, out["passes"]
    assert out["condition"] == "a sentence"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_window_with_no_passes_in_it_says_so_rather_than_printing_nothing():
    """An empty section reads as "nothing went wrong". It has to read as
    "nothing was measured"."""
    review = _module()
    rows = [{"run": "p1", "at": "2026-08-01T00:00:00+00:00", "finished": True}]

    out = review.area_deep_pass(
        since=datetime(2026, 9, 1, tzinfo=timezone.utc),
        passes=lambda: rows, condition=lambda given: None)

    assert out["passes"] == []
    assert out["gap"], "an empty window must say it is empty"
    assert "2026-08-01"[:7] in out["gap"] or "0" in out["gap"], out["gap"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_reading_the_real_repository_changes_not_one_byte(tmp_path):
    """The design's central promise, as a test rather than a docstring."""
    review = _module()
    import subprocess

    before = subprocess.run(["git", "status", "--porcelain"], cwd=REPO,
                            capture_output=True, text=True).stdout
    stamps = {p: p.stat().st_mtime for p in (REPO / "audits").rglob("*")
              if p.is_file()}

    assert review.main(["--deep-pass", "all"]) == 0

    after = subprocess.run(["git", "status", "--porcelain"], cwd=REPO,
                           capture_output=True, text=True).stdout
    assert after == before, "a read-only review moved the working tree"
    assert {p: p.stat().st_mtime for p in (REPO / "audits").rglob("*")
            if p.is_file()} == stamps, "a read-only review wrote under audits/"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_marks_file_is_read_but_never_written_by_a_read(tmp_path,
                                                            monkeypatch):
    """Peeking must not move the mark, or "since I last looked" drifts away
    from the reviews that were actually written."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path / "state"))
    review = _module()
    path = tmp_path / "audits" / "review.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps({"lab": {"at": "2026-09-01T00:00:00+00:00"}}),
                    encoding="utf-8")
    before = path.read_text(encoding="utf-8")

    marks = review.marks()
    assert marks["lab"]["at"].startswith("2026-09-01")
    review.window("last", "lab", marks, NOW)

    assert path.read_text(encoding="utf-8") == before, (
        "reading moved the checkpoint")
