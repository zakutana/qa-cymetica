"""MIG: the migration copies, and can be shown to have copied.

The whole plan exists because 71 of 109 state changes came from our own code
re-deriving what it already knew. A migration is the most tempting place to do
that one more time -- to reconstruct what each row "should" have been. This
file is the argument that it did not: every row's content is byte-for-byte
what state/ledger.json@ca0bc45 held, every event names the artefact it came
from, and the judgement calls are separated out so a human signs for them.

It runs the real migration against a temp state directory seeded with the real
source files, so what is tested is the thing that will run.

Fails at 9929860: there is no scripts/migrate_ledger.py.
"""

from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
SOURCES = ("submissions.json", "bounty.json", "ledger.json")


def _migration():
    path = REPO / "scripts" / "migrate_ledger.py"
    spec = importlib.util.spec_from_file_location("migrate_mod", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def staged(tmp_path, monkeypatch):
    """A state directory holding only the migration's real inputs."""
    for name in SOURCES:
        source = REPO / "state" / name
        if source.exists():
            shutil.copy(source, tmp_path / name)
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    return tmp_path


def _legacy() -> dict:
    blob = subprocess.run(["git", "show", "ca0bc45:state/ledger.json"], cwd=REPO,
                          capture_output=True, text=True, check=True).stdout
    return json.loads(blob)["findings"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_migration_is_lossless_and_idempotent(staged):
    """No row is dropped, no content is rewritten, and it runs once."""
    migration = _migration()

    legacy = _legacy()
    rows = migration.rows()

    assert set(legacy) <= set(rows), \
        f"rows lost in migration: {sorted(set(legacy) - set(rows))}"
    assert len(rows) == len(legacy) + 3, \
        "the three findings that existed only in MSG-0002 are missing"

    for fid, before in legacy.items():
        after = rows[fid]
        for field in migration.CONTENT_FIELDS:
            if before.get(field) is not None:
                assert after.get(field) == before[field], f"{fid}.{field} was rewritten"
        # No row arrives already believing anything about itself.
        assert after["check"]["state"] == "UNVERIFIED"
        assert after["check"]["adjudicated_by"] is None
        assert after["filing"]["state"] == "NOT_RAISED"
        assert after["transitions"] == []
        # Critique gap 5: the words are imported; the figures in them are not
        # presented as measured.
        assert after["provenance"]["measured_at"] is None

    # Every copied event says where it was copied from.
    for event in migration.machine_events():
        assert event.get("migrated_from"), event

    assert migration.main([]) == 0, "the dry run failed"
    assert not (staged / "journal" / "events.jsonl").exists(), \
        "the dry run wrote to the journal"

    assert migration.main(["--confirm"]) == 0
    from qa.state import read_events
    first = read_events()
    assert first, "nothing was written"

    with pytest.raises(SystemExit, match="already has events"):
        migration.main(["--confirm"])
    assert read_events() == first, "the second run changed the journal"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_judgement_events_require_confirm(staged):
    """Copies and decisions are different things. Repointing a row at a
    different check is a claim about what adjudicates that finding, and a
    human is answerable for it -- so it is `by: operator`, it carries a
    reason, and the dry run shows it before anything is written."""
    migration = _migration()

    judgements = migration.judgement_events()
    assert judgements

    for event in judgements:
        assert event["by"] == "operator", event
        assert event["type"] in ("rebind_check", "retire_check"), event
        assert (event.get("reason") or "").strip(), event
        assert not event.get("migrated_from"), \
            "a judgement is not a copy and must not claim to be one"

    rebound = {e["finding_id"] for e in judgements if e["type"] == "rebind_check"}
    assert rebound == {
        "CYM-own-reports-unverified", "CYM-tracker-closure-rate",
        "CYM-bounty-filing-unauthenticated", "CYM-anon-tool-surface",
        "CYM-documented-404",
    }
    assert sum(1 for e in judgements
               if e["finding_id"] == "CYM-documented-404") == 26, \
        "each pinned path needs its own check, or the row cannot regress per path"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_day_one_is_twenty_three_rows_and_nothing_verified(staged):
    """The honest reading of yesterday, stated as a test.

    Not because nothing was ever fixed, but because no admissible run has
    adjudicated anything: all 13 existing run records fail admissibility for a
    reason each of them names."""
    migration = _migration()
    migration.main(["--confirm"])

    ledger_mod = importlib.util.module_from_spec(
        importlib.util.spec_from_file_location(
            "ledger_mig", REPO / "scripts" / "ledger.py"))
    sys.modules["ledger_mig"] = ledger_mod
    ledger_mod.__loader__.exec_module(ledger_mod)

    ledger = ledger_mod.compose(events_only=True,
                                seed=staged / "ledger.seed.json")

    from qa.fold import display_state
    counts = ledger["counts"]

    assert len(ledger["findings"]) == 23, len(ledger["findings"])
    assert sum(counts.values()) == 23, counts
    assert counts.get("VERIFIED FIXED", 0) == 0, \
        "something claims to be verified without a run behind it"
    assert counts.get("WITHDRAWN") == 4, counts

    # NOT an exact FIX CLAIMED count. That number is a function of the
    # vendor's tracker at the moment this runs, and they keep answering
    # reports -- it was 10 on day one and is higher now. Pinning it made this
    # test fail for a change on their side, which is a test measuring the
    # wrong thing. What the migration guarantees is that their claims move
    # only the FILING axis and verify nothing.
    assert counts.get("FIX CLAIMED", 0) >= 10, counts

    for fid, row in ledger["findings"].items():
        assert row["check"]["state"] in ("UNVERIFIED", "UNVERIFIABLE"), (fid, row["check"])
        assert not any("::" not in c for c in row.get("checks") or []), \
            f"{fid} still names a check pytest cannot collect: {row['checks']}"
        if display_state(row) == "FIX CLAIMED":
            assert row["obligations"]["reverify"] is True, fid

    # The two withdrawals that had been filed were retracted to the vendor in
    # the CORRECTIONS paragraph of report #54, so neither still owes one.
    for fid in ("CYM-chain_count", "CYM-mcp_tool_count"):
        assert ledger["findings"][fid]["obligations"]["retractions"] == [], fid
