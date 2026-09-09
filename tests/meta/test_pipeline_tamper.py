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
def test_a_run_that_did_not_honour_its_preregistration_is_refused():
    """Gap 1's last door: a real tag, and a different selector.

    Level V is the only level that may close a finding, and it was granted on
    a clean tree, a preregistration id, and the tag pointing at HEAD. Nothing
    compared the selector the tag committed to against what the session
    actually collected. So: preregister the suite, run the single check you
    expect to pass, file the pass as a verification. The tag proved when the
    commitment was written and nothing proved it was kept -- the same shape as
    the two edited strings, one level up.

    Both directions are checked and mean different things. Collecting outside
    the selector is running MORE than was declared. A declared token that
    collected nothing is running LESS, which is the shape of narrowing to a
    result you like.

    The selector itself is read from git at the tag, never from the working
    tree, so editing the preregistration afterwards changes nothing.
    """
    from qa.state import _honoured_preregistration, _selector_covers

    assert _selector_covers("tests/meta", "tests/meta/test_x.py::test_y")
    assert _selector_covers("a.py::test_b", "a.py::test_b[param]")
    assert _selector_covers("a.py::test_b", "a.py::test_b")
    assert not _selector_covers("tests/meta", "tests/rest/test_x.py::test_y")
    assert not _selector_covers("a.py::test_b", "a.py::test_bb")

    selector = 'tests/meta "tests/rest/a.py::test_one" "tests/rest/b.py::test_two"'
    one = "tests/rest/a.py::test_one"
    two = "tests/rest/b.py::test_two"
    meta = "tests/meta/test_guard_is_real.py::test_g"

    def check(collected):
        return _honoured_preregistration({"prereg_id": "PRE-0001",
                                          "collected": collected}, selector)

    assert check([meta, one, two]) == [], "a run that kept its word was refused"

    ran_less = check([one])
    assert ran_less and "collected nothing under it" in ran_less[0], ran_less
    assert two in ran_less[0] and "tests/meta" in ran_less[0], \
        "the refusal does not name what was promised and skipped"

    ran_more = check([meta, one, two, "tests/rest/c.py::test_three"])
    assert ran_more and "did not preregister" in ran_more[0], ran_more

    # A run that collected nothing is a different problem, named elsewhere;
    # this check must not claim it as a broken promise as well.
    assert check([]) == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_concurrent_writers_cannot_break_the_chain(tmp_path):
    """Two processes appending at once must not corrupt the journal.

    append_event reads the whole journal, derives seq and chain from what it
    read, and only then writes. Unserialised, two writers inside that window
    derive the same seq, and the result is not a lost event: read_events
    raises from then on, so the ledger cannot fold, the page cannot render and
    every session aborts -- with rule 4 forbidding a hand repair, which leaves
    no exit that does not break another rule. Three writers reproduced it on
    the first attempt, at line 3 of 36.

    It went unnoticed while every writer was an operator typing one command.
    `serve.py --ask` appends on a timer, unattended, and can land in the
    middle of a sweep, so the window is now real.

    Subprocesses, not threads: the lock is a cross-PROCESS one, and threads
    would not exercise it.
    """
    import subprocess
    import sys
    from pathlib import Path

    repo = Path(__file__).resolve().parent.parent.parent
    writer = tmp_path / "writer.py"
    writer.write_text(
        "import os, sys\n"
        "os.environ['QA_STATE_DIR'] = sys.argv[1]\n"
        "sys.path.insert(0, sys.argv[2])\n"
        "from qa.state import append_event\n"
        "who = sys.argv[3]\n"
        "for i in range(8):\n"
        "    append_event({'type': 'note', 'at': '2026-09-05T00:00:0%d+00:00' % i,\n"
        "                  'by': 'agent', 'source': 'w-' + who,\n"
        "                  'finding_id': 'CYM-a', 'note': who + '-' + str(i)})\n",
        encoding="utf-8")

    (tmp_path / "journal").mkdir(parents=True, exist_ok=True)
    procs = [subprocess.Popen([sys.executable, str(writer), str(tmp_path),
                               str(repo), who])
             for who in ("A", "B", "C")]
    for p in procs:
        assert p.wait(timeout=120) == 0, "a writer failed outright"

    import os

    from qa.state import read_events

    os.environ["QA_STATE_DIR"] = str(tmp_path)
    try:
        events = read_events()          # raises JournalError if the chain broke
    finally:
        os.environ.pop("QA_STATE_DIR", None)

    assert len(events) == 24, f"24 appends, {len(events)} survived"
    assert [e["seq"] for e in events] == list(range(1, 25)), "sequence is not dense"
    assert len({e["note"] for e in events}) == 24, "an append was lost or doubled"


# ---------------------------------------------------------------------------
# Rule 12, asked as one question instead of two
# ---------------------------------------------------------------------------
def _journal(*types) -> list[dict]:
    """A journal-shaped list: dense seq from 1, each line with its own chain.

    Hand-built rather than appended through qa.state, because `drift` is pure
    and reads only `seq`, `chain` and `type`. The chain values need only be
    distinct; what they hash to is `read_events`'s question, and it is asked
    on every load already.
    """
    return [{"seq": i, "chain": f"chain-{i:02d}", "type": t,
             "at": f"2026-09-05T00:00:{i:02d}+00:00",
             "by": "agent", "source": "test"}
            for i, t in enumerate(types, start=1)]


def _committed(head_seq: int, head_chain: str, **over) -> dict:
    led = {"schema": 2, "run_id": "run-1", "run_level": "V",
           "counts": {"STILL REPRODUCIBLE": 1},
           "events_head": {"seq": head_seq, "chain": head_chain}}
    led.update(_ledger())
    led["events_head"] = {"seq": head_seq, "chain": head_chain}
    led.update(over)
    return led


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_events_the_fold_does_not_read_are_counted_not_charged():
    """An event that moved no row must not read as a stale projection.

    Rule 12's guard compared the committed ledger to a refold key by key,
    `events_head` among them. That key is the journal's head at the moment of
    the compose, so the console -- `serve.py --ask 15`, two `vendor_read`
    events per tick -- put the guard in the red within fifteen minutes of
    every fold and left it there. The fold reads `vendor_read` only to set or
    clear `stale_from`; an `ok` read moves nothing. So the guard spent most of
    its life red for the most boring reason available, which is how a guard
    stops being read.

    The question rule 12 actually asks is whether the committed rows are what
    the inputs fold to. That is asked by comparing the ROWS, against a refold
    over the WHOLE journal -- pending events included -- so an event that
    would move something still turns this red. The head is then not a
    comparison at all but a citation, and the honest check on a citation is
    that it points at a line the journal really has.
    """
    from scripts.ledger import drift

    events = _journal("vendor_read", "vendor_read", "note", "vendor_read")
    committed = _committed(1, "chain-01")
    refolded = _committed(4, "chain-04")

    d = drift(committed, refolded, events)
    assert d["rows"] == [], d
    assert d["keys"] == [], "events_head is a citation, not a compared key"
    assert d["anchored"] is True
    assert d["since_head"] == {"vendor_read": 2, "note": 1}
    assert "none moved a row" in d["reason"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_pending_event_that_moves_a_row_is_still_caught():
    """The half that must not be lost. Counting the suffix by type is a
    report, never the verdict: the verdict is that the rows agree with a
    refold that already read every pending event."""
    from scripts.ledger import drift

    events = _journal("vendor_read", "withdraw")
    committed = _committed(1, "chain-01")
    moved = _committed(2, "chain-02")
    moved["findings"]["CYM-a"]["filing"]["state"] = "WITHDRAWN"

    d = drift(committed, moved, events)
    assert d["rows"] == ["CYM-a"], d
    assert "CYM-a" in d["reason"]
    assert d["anchored"] is True, "the head is fine; it is the row that drifted"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_other_top_level_key_is_still_compared():
    """`counts` is the one the module docstring of tests/repo names: a ledger
    whose rows are right beside tiles that are not. Only `events_head` is
    exempt, and only because it is checked as a citation instead."""
    from scripts.ledger import drift

    events = _journal("note")
    committed = _committed(1, "chain-01", counts={"VERIFIED FIXED": 9})
    refolded = _committed(1, "chain-01")

    d = drift(committed, refolded, events)
    assert d["keys"] == ["counts"], d
    assert "counts" in d["reason"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
@pytest.mark.parametrize("seq,chain,why", [
    (2, "not-the-chain", "a head the journal does not have at that line"),
    (9, "chain-03", "a head past the end of the journal"),
    (-1, "chain-01", "a head before the beginning"),
])
def test_a_head_the_journal_cannot_confirm_is_refused(seq, chain, why):
    """The citation, checked. A ledger folded against some other journal --
    a temp state directory leaking into the repository, a journal rewritten
    underneath it -- names a line that is not there, and that is exactly what
    `events_head` is for. Demoting it from a compared key to a citation must
    not demote it to nothing.

    What this no longer catches, said plainly: a head hand-rolled BACKWARDS to
    an older line the journal really has. It passes here, over-reports the
    suffix, and moves nothing else -- the rows are still compared against the
    whole journal. `write_ledger` refuses that ledger at the moment it is
    written (qa/state.py), which is where the invariant belongs.
    """
    from scripts.ledger import drift

    events = _journal("note", "note", "note")
    d = drift(_committed(seq, chain), _committed(3, "chain-03"), events)
    assert d["anchored"] is False, why
    assert "journal" in d["reason"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_empty_journal_anchors_at_zero():
    """A repository before its first event. `head()` returns seq 0 and an
    empty chain, and that is a citation like any other."""
    from scripts.ledger import drift

    d = drift(_committed(0, ""), _committed(0, ""), [])
    assert d["anchored"] is True and d["rows"] == [] and d["since_head"] == {}
