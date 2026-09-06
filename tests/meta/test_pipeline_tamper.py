"""Every hand-edit the plan's negative control names, refused.

The plan's own verification step: change one byte in state/ledger.json, one in
a run record, one in the journal, and check that each is caught. Run once as
an exercise, these prove nothing tomorrow. Here they run every session.

Critique gap 1 is the interesting one. Run records were the only input to the
whole pipeline that nothing corroborated: level V is granted from fields the
file asserts ABOUT ITSELF -- `git_dirty: false`, `prereg_commit: <sha>` -- so
editing two strings bought a verification carrying a real run id. Everything
else is chained, hashed or cross-checked; this was the way in. Two
corroborations close it, both against facts the file does not control: the
preregistration tag, re-resolved from git, and the file's own hash as attested
by the journal when it was first composed.
"""

from __future__ import annotations

import json

import pytest

from qa.marks import SafetyTier, qa


def _ledger(**over) -> dict:
    row = {
        "id": "CYM-a", "title": "t", "severity": "S3-CONTRACT",
        "checks": ["tests/a.py::test_x"],
        "first_seen": {"at": "2026-09-05T00:00:00+00:00",
                       "cause": {"run_id": "run-1"}},
        "reproductions": 1,
        "check": {"state": "REPRODUCING", "adjudicated_by": None,
                  "pinned_fingerprint": None},
        "filing": {"state": "NOT_RAISED", "adjudicated_by": None,
                   "reports": [], "refused": []},
        "transitions": [], "regressions": [],
    }
    row.update(over)
    return {"schema": 2, "findings": {"CYM-a": row}}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("key,value", [
    ("verified_note", "looks fine to me"),
    ("verified_fixed_at", "2026-09-05T00:00:00+00:00"),
    ("verified_by_run", "run-1"),
    ("backfilled_from", "ledger@ca0bc45"),
])
def test_a_hand_written_key_is_refused(tmp_path, key, value):
    """Four keys no code writes. All four were in the committed ledger."""
    from qa.state import LedgerError, load_ledger

    path = tmp_path / "ledger.json"
    path.write_text(json.dumps(_ledger(**{key: value})), encoding="utf-8")
    with pytest.raises(LedgerError, match=key):
        load_ledger(path)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_state_change_without_a_cause_is_refused(tmp_path):
    from qa.state import LedgerError, load_ledger

    path = tmp_path / "ledger.json"
    path.write_text(json.dumps(_ledger(transitions=[
        {"axis": "check", "from": "REPRODUCING", "to": "PASSING",
         "cause": {}, "at": "2026-09-05T00:00:00+00:00"}])), encoding="utf-8")
    with pytest.raises(LedgerError, match="run_id"):
        load_ledger(path)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_run_record_edited_after_attestation_is_refused(tmp_path):
    """Critique gap 1, the half that needs no git.

    A record can no longer be improved after the journal has said what it
    contained -- which is what an operator hand-editing `git_dirty` to false
    would be doing.
    """
    import hashlib

    from qa.state import run_integrity

    path = tmp_path / "run-1.json"
    record = {"schema": 2, "run_id": "run-1", "git_dirty": True,
              "results": [], "collected": []}
    path.write_text(json.dumps(record), encoding="utf-8")
    attested = hashlib.sha256(path.read_bytes()).hexdigest()

    events = [{"type": "run_recorded", "at": "2026-09-05T00:00:00+00:00",
               "by": "agent", "source": "scripts/ledger.py",
               "run_id": "run-1", "file_sha256": attested}]

    assert run_integrity(record, path=path, events=events) == []

    record["git_dirty"] = False        # the edit that would buy level V
    path.write_text(json.dumps(record), encoding="utf-8")
    problems = run_integrity(record, path=path, events=events)
    assert problems and "changed since the journal attested" in problems[0]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_run_claiming_a_preregistration_that_does_not_exist_is_refused(tmp_path):
    """The other half: the record may name any commit it likes, but the tag
    lives in the repository's object store and is not ours to assert."""
    from qa.state import run_integrity

    record = {"schema": 2, "run_id": "run-1", "prereg_id": "PRE-9999",
              "prereg_commit": "0" * 40, "results": [], "collected": []}
    problems = run_integrity(record, path=None, events=[])
    assert problems and "PRE-9999" in problems[0]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_single_test_run_closes_nothing(tmp_path):
    """The plan's last negative control. A one-result run may open a defect
    and may never close a row it did not adjudicate -- the failure that let a
    targeted re-run silently verify everything it never touched."""
    from qa.fold import display_state, fold

    from tests.meta.test_pipeline_fold import (CHECK_A, CHECK_B, FP1,
                                               fold_run, ledger, row)

    state = ledger(
        row("CYM-a", check_state="REPRODUCING", checks=[CHECK_A], pinned=FP1),
        row("CYM-b", check_state="REPRODUCING", checks=[CHECK_B], pinned=FP1),
    )
    before = {fid: display_state(r) for fid, r in state["findings"].items()}

    single = fold_run("run-single", [(CHECK_A, "passed")])
    single["collected"] = [CHECK_A]
    after = fold(state, run=single, events=[])

    assert display_state(after["findings"]["CYM-b"]) == before["CYM-b"]
    assert after["findings"]["CYM-b"]["check"]["not_checked_in"] == "run-single"
    assert "VERIFIED" not in display_state(after["findings"]["CYM-b"])
