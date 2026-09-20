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


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_lab_area_filters_every_diary_on_its_own_clock():
    """Five diaries, one window, and every row in them carries `at`.

    No git archaeology: the laboratory's files are append-only, unlike the deep
    pass's notebook which is overwritten and survives only as commits. An
    earlier draft of this plan proposed `git log -p` over the archive for
    exactly this and it was wasted work.
    """
    review = _module()
    since = datetime(2026, 9, 12, tzinfo=timezone.utc)
    lab_rows = [
        {"type": "session", "state": "closed", "at": "2026-09-11T10:00:00+00:00",
         "session": "LAB-0001", "lessons": ["old"], "next": []},
        {"type": "session", "state": "closed", "at": "2026-09-12T12:00:00+00:00",
         "session": "LAB-0002", "lessons": ["new one", "new two"], "next": ["a"]},
        {"type": "session", "state": "open", "at": "2026-09-12T13:00:00+00:00",
         "session": "LAB-0003"},
    ]
    room_rows = [
        {"type": "strategy", "room": "STR-0001", "at": "2026-09-10T09:00:00+00:00"},
        {"type": "strategy", "room": "STR-0002", "at": "2026-09-12T09:00:00+00:00"},
        {"type": "verdict", "room": "STR-0001", "at": "2026-09-12T09:30:00+00:00",
         "verdict": "survived"},
    ]

    # Five diaries, and the stub used to hand every one of them `[]` -- so the
    # `_within` wrappers on asked / answered / gave_up / backtests / orders
    # filtered empty lists and only the two above were ever measured. Dropping
    # `_within` from the backtests line left this green while the retrospective
    # reported every backtest ever run under a "last 7 days" heading. Each
    # diary now carries one row inside the window and one before it, so every
    # wrapper has something to cut. 3/3, deep pass of 2026-09-13.
    old, new = "2026-09-01T09:00:00+00:00", "2026-09-12T09:00:00+00:00"
    diary = {
        "nexus.jsonl": [
            {"type": "question", "at": old}, {"type": "question", "at": new},
            {"type": "answer", "at": old}, {"type": "answer", "at": new},
            {"type": "gave_up", "at": old}, {"type": "gave_up", "at": new},
        ],
        "backtests.jsonl": [{"at": old}, {"at": new}],
        "paper.jsonl": [{"type": "intent", "at": old},
                        {"type": "intent", "at": new},
                        {"type": "outcome", "at": new}],
    }

    out = review.area_lab(since, lab=lambda: lab_rows, rooms=lambda: room_rows,
                          diaries=lambda name: diary.get(name, []),
                          grade=lambda: None)

    assert [s["session"] for s in out["sessions"]] == ["LAB-0002"], out["sessions"]
    assert out["lessons"] == ["new one", "new two"], out["lessons"]
    assert [r["room"] for r in out["rooms"]] == ["STR-0002"], out["rooms"]
    assert len(out["verdicts"]) == 1

    for key in ("asked", "answered", "gave_up", "backtests", "orders"):
        assert len(out[key]) == 1, (
            f"{key} carries {len(out[key])} row(s): one is inside the window "
            f"and one is eleven days before it, so anything but 1 means that "
            f"diary is not being filtered on the window at all")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_grade_refusal_reaches_the_screen_verbatim():
    """`lab.py grade` refusing below its floor IS the answer, not a gap.

    Swallowed as an empty section it would read as "the filter works"; the
    whole point of that refusal is that we do not yet know.
    """
    review = _module()
    refusal = {"verdict": "not enough data",
               "why": "0 closed verdict(s) and the floor is 6"}

    out = review.area_lab(datetime(2026, 9, 1, tzinfo=timezone.utc),
                          lab=list, rooms=list, diaries=lambda name: [],
                          grade=lambda: refusal)

    assert out["grade"]["why"] == refusal["why"]
    assert refusal["why"] in review._render_lab(out, "celá historie")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_checkpoint_is_stamped_only_by_the_checkpoint_command(tmp_path,
                                                                monkeypatch):
    """And only for the areas named, because a review that covered one area
    must not move the line the other one draws from."""
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path / "state"))
    review = _module()

    assert review.main(["checkpoint", "--area", "lab"]) == 0

    known = review.marks()
    assert "lab" in known and known["lab"]["at"], known
    assert "deep-pass" not in known, (
        "stamping one area moved another area's line")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_nexus_row_types_are_read_off_the_real_diary_not_guessed():
    """The vocabulary this reader depends on, pinned against the data.

    The first draft counted `type == "ask"`. The diary says `question`, so it
    reported "0 otázek Nexusovi" on a line directly above a lesson saying one
    had been asked. Guessing a field name is how a retrospective quietly halves
    itself; this fails the day the vocabulary moves.
    """
    import json as _json

    from qa.state import state_dir

    path = state_dir() / "nexus.jsonl"
    if not path.is_file():
        pytest.skip("no Nexus diary on this machine")
    types = {_json.loads(line).get("type")
             for line in path.read_text(encoding="utf-8").splitlines()
             if line.strip()}

    assert {"question", "answer", "gave_up"} <= types, (
        f"review.area_lab counts question/answer/gave_up; the diary holds "
        f"{sorted(t for t in types if t)}")

    # Through the READER, not against a literal. The three words above were
    # written twice -- once here and once in scripts/review.py -- so reverting
    # the reader to the historical `type == "ask"` left this green while the
    # retrospective printed "0 otázek Nexusovi" again, which is the incident
    # this docstring cites. Now the diary's own rows go through `area_lab` and
    # the counts have to be non-zero. 3/3, deep pass of 2026-09-13.
    rows = [_json.loads(line)
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    review = _module()
    out = review.area_lab(datetime(2020, 1, 1, tzinfo=timezone.utc),
                          lab=list, rooms=list,
                          diaries=lambda name: rows if name == "nexus.jsonl"
                          else [],
                          grade=lambda: None)
    empty = [k for k in ("asked", "answered", "gave_up") if not out[k]]
    assert not empty, (
        f"the diary holds {sorted(t for t in types if t)} and area_lab counted "
        f"nothing for {empty} -- the reader and this test are naming different "
        f"words for the same rows")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_one_half_written_line_does_not_empty_a_diary(tmp_path, monkeypatch):
    """A diary is appended to while this reads it, so the last line may be torn.

    The reader parsed the whole file in one comprehension inside a single
    `except json.JSONDecodeError: return []`, so a line caught mid-append did
    not cost that line -- it cost the file. The retrospective would then say
    "0 questions to Nexus" over a diary holding hundreds, and say it with the
    same confidence as a true zero. `qa/lab.py::load` has always done this
    correctly, one line at a time, with the reason in its own comment: "a
    half-written line is normal while another process appends".
    """
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    good = [{"type": "question", "id": "NEX-1"},
            {"type": "answer", "id": "NEX-1"},
            {"type": "question", "id": "NEX-2"}]
    (tmp_path / "nexus.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in good) + '{"type": "quest',
        encoding="utf-8")

    review = _module()
    rows = review._diaries_default()("nexus.jsonl")
    assert len(rows) == len(good), (
        f"one torn line emptied a diary of {len(good)} rows: got {rows}")
