"""A run folded where its captures cannot survive leaves a row standing on
bodies nobody can produce.

On 2026-09-29 a cloud session ran a level-V sweep (`run-20260929T094730Z-24cabf49`,
Python 3.12.3, commits at +0000) and folded it there. `keepset.track` wrote the
manifest lines -- id, size, the call -- on that VM, because the bodies were on
its disk, and the commit carried those lines home. `evidence/` and `archive/`
are gitignored (D3), so the bodies did not: they died with the VM. 53 of them
are cited by a ledger row, `test_every_capture_the_committed_state_cites_can_
still_be_produced` has been red on them since, and nothing here removed them --
`prune_runs.py` and `keep.py archive` never saw a file that was never on this
disk. The proof travelled and the thing it proves did not.

Everything that makes a fold safe -- the prune's keep set, the archive's carry,
the guard -- reads the store on THIS machine. A fold made on a host whose disk
is not this one defeats all of it at the one moment it is cheap to refuse. So
the write path refuses, before it attests anything. What stays allowed there is
what moves no row on a run: a check run is exploratory evidence (rule 6),
`--events-only` judges nothing, `--check` writes nothing.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa

CHECK = "tests/x.py::test_a"


def _ledger_module(tmp_path, monkeypatch):
    state = tmp_path / "state"
    (state / "journal").mkdir(parents=True)
    (state / "runs").mkdir(parents=True)
    monkeypatch.setenv("QA_STATE_DIR", str(state))
    path = Path(__file__).resolve().parents[2] / "scripts" / "ledger.py"
    spec = importlib.util.spec_from_file_location("ledger_ephemeral", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    # Nothing here may reach the repository's own git index.
    monkeypatch.setattr(module, "_track_run_record", lambda run_id: None)
    monkeypatch.setattr(module.keepset, "track", lambda **k: None)
    monkeypatch.setattr(module.keepset, "untrack", lambda **k: None)
    return module, state


def _run(state: Path, run_id: str) -> None:
    at = "2026-09-29T09:47:32+00:00"
    (state / "runs" / f"{run_id}.json").write_text(json.dumps({
        "schema": 2, "run_id": run_id, "started_at": at, "finished_at": at,
        "git_head": "abc123", "git_dirty": False,
        "prereg_id": None, "prereg_tag_sha": None,
        "prereg_commit": None, "platform_fingerprint": "sha256:f",
        "fingerprint_drifted": False, "collected": [CHECK], "exit_status": 0,
        "results": [{"nodeid": CHECK, "outcome": "passed"}],
        "record_integrity": {"consistent": True}}), encoding="utf-8")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_run_is_not_folded_on_a_host_whose_disk_will_not_outlive_it(
        tmp_path, monkeypatch):
    ledger_mod, state = _ledger_module(tmp_path, monkeypatch)
    _run(state, "run-cloud")
    monkeypatch.setenv("CLAUDE_CODE_REMOTE", "true")

    with pytest.raises(SystemExit) as refused:
        ledger_mod.main(["--run", "run-cloud"])
    said = str(refused.value)
    assert "run-cloud" in said and "cloud" in said.lower(), said
    assert not (state / "ledger.json").exists(), "the ledger was written anyway"
    from qa.state import read_events
    assert not [e for e in read_events() if e.get("type") == "run_recorded"], (
        "the refused run was attested in the journal anyway")

    # The refusal is about WHERE, not about the run: the same record folds on
    # a host that keeps what it captured.
    monkeypatch.delenv("CLAUDE_CODE_REMOTE")
    assert ledger_mod.main(["--run", "run-cloud"]) == 0
    assert (state / "ledger.json").is_file()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_host_refusal_leaves_the_folds_that_judge_no_run(
        tmp_path, monkeypatch):
    """A journal-only fold moves rows on events, never on a run's captures, and
    `--check` writes nothing -- neither can leave a citation without a body."""
    ledger_mod, state = _ledger_module(tmp_path, monkeypatch)
    _run(state, "run-cloud")
    assert ledger_mod.main(["--run", "run-cloud"]) == 0
    monkeypatch.setenv("CLAUDE_CODE_REMOTE", "true")

    assert ledger_mod.main(["--events-only"]) == 0
    assert ledger_mod.main(["--check"]) in (0, 1)  # answered, not refused
