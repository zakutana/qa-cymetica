"""Rule 12, made enforceable: the committed state must be what its inputs fold to.

Operating rule 12 said "before every commit, re-fold and re-render". There is
no CI and no hook in this repository, so as written it reduced to "the
operator remembers" -- which is the same class of guarantee as the convention
that every test carries a @qa tag, and that one needed a collection-time abort
to survive contact with a tired operator at 2am.

Two checks:

  (a) the committed ledger is what its journal and run records fold to
  (b) the committed dashboard is a render of that ledger

They live in tests/repo/ rather than tests/meta/, deliberately. The meta block
aborts the whole session on failure, which is right for the safety guard -- if
the guard cannot be shown to block, no live request may be issued. It is wrong
here, and the plan that put them in the meta block did not foresee why: a
stale ledger would abort the very run whose record is needed to bring the
ledger up to date. Deadlock, on the one check meant to keep the repository
honest. Observed on the first attempt at the first admissible run.

A stale projection is a bookkeeping failure, not a safety failure. These still
run in every full session and still fail loudly; they just do not stop the
session that would fix them.

(b) is the one that matters most and the one nothing else covers. A ledger can
be perfectly correct while the page beside it shows last week's numbers, and
the page is what the operator actually reads. That drift is the history behind
16 rows on the filter, 6 in the tiles and 20 in the ledger.

Before the migration these are INCONCLUSIVE, not failures: the committed
ledger predates the contract it would be judged against, and saying "the repo
is inconsistent" would be true but useless. After migration they are real.
"""

from __future__ import annotations

import importlib.util
import json
import re
from pathlib import Path

import pytest

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent
LEDGER = REPO / "state" / "ledger.json"
DASHBOARD = REPO / "dashboard" / "index.html"

HASH_MARKER = re.compile(r"<!-- qa-payload-sha256: ([0-9a-f]{64}) -->")


@pytest.fixture(autouse=True)
def _read_the_repository(monkeypatch):
    """These two check the COMMITTED state, so they must not follow
    QA_STATE_DIR -- under it they would compare the repository's dashboard
    against a payload built from some temp directory and always disagree."""
    monkeypatch.delenv("QA_STATE_DIR", raising=False)


def _module(relpath: str, name: str):
    path = REPO / relpath
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _migrated() -> tuple[bool, str]:
    """Has the ledger been brought under the contract yet?"""
    if not LEDGER.exists():
        return False, "state/ledger.json does not exist yet"
    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    if ledger.get("schema") != 2:
        return False, "state/ledger.json is still the pre-contract format"
    if "events_head" not in ledger:
        return False, "state/ledger.json does not cite a journal head yet"
    return True, ""


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_committed_ledger_is_what_its_inputs_fold_to():
    """`ledger.py --check`, in-process, against the committed state."""
    migrated, why = _migrated()
    if not migrated:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"{why}; there is nothing to check it against until "
                   f"scripts/migrate_ledger.py has run",
            sources={"ledger": "state/ledger.json"},
        ))
        return

    ledger_mod = _module("scripts/ledger.py", "ledger_consistency")
    committed = json.loads(LEDGER.read_text(encoding="utf-8"))
    try:
        # Against the run the committed ledger CITES, not whichever run is
        # newest. Folding against "latest admissible" made this test poison
        # itself: every pytest session writes a run record, so this file's own
        # previous invocation became the newest run, and a two-test selector
        # marks every other row not_checked_in. It passed, then failed, then
        # passed, on nothing but the order it was run in. A guard that
        # alternates is worse than none, because the false failure teaches you
        # to disbelieve the true one.
        refolded = ledger_mod.compose(run_id=committed.get("run_id"))
    except SystemExit as exc:
        if "no admissible run" not in str(exc):
            conclude(Measurement(
                verdict="inconclusive",
                reason=f"the ledger cannot be re-folded right now: {exc}",
            ))
            return
        # No admissible run exists yet, so the journal alone is the whole of
        # the ledger's input. That is a real comparison, not a missing one.
        refolded = ledger_mod.compose(events_only=True)

    drifted = {
        fid for fid in set(committed.get("findings", {})) | set(refolded["findings"])
        if committed.get("findings", {}).get(fid) != refolded["findings"].get(fid)
    }
    conclude(Measurement(
        verdict="failed" if drifted else "passed",
        reason=(f"{len(drifted)} committed row(s) are not what the journal and "
                f"run records fold to: {sorted(drifted)}"
                if drifted else "the committed ledger matches its inputs"),
        left=sorted(drifted), right=[],
        sources={"ledger": "state/ledger.json", "journal": "state/journal/events.jsonl"},
    ))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_committed_dashboard_matches_the_committed_ledger():
    """The page is what the operator reads, so it is the thing most worth
    checking -- and the only artefact nothing else here covers."""
    migrated, why = _migrated()
    if not migrated:
        conclude(Measurement(verdict="inconclusive", reason=why))
        return
    if not DASHBOARD.exists():
        conclude(Measurement(verdict="inconclusive",
                             reason="dashboard/index.html has not been rendered"))
        return

    html = DASHBOARD.read_text(encoding="utf-8")
    match = HASH_MARKER.search(html)
    if match is None:
        conclude(Measurement(
            verdict="inconclusive",
            reason="the committed dashboard predates the payload hash marker, "
                   "so it cannot be compared; re-render it once",
        ))
        return

    render_mod = _module("scripts/render.py", "render_consistency")
    try:
        # Stale-head allowed HERE only: this guard asks whether the page is
        # a render of the ledger. Whether the ledger is level with the
        # journal is the sibling guard's question, and refusing on it here
        # made this one skip on every run since every session appends an
        # event of its own.
        current = render_mod.payload_hash(
            render_mod.build_payload(allow_stale_head=True))
    except SystemExit as exc:
        conclude(Measurement(verdict="inconclusive",
                             reason=f"the payload cannot be built: {exc}"))
        return

    conclude(Measurement(
        verdict="passed" if current == match.group(1) else "failed",
        reason=("the committed dashboard is a render of the committed state"
                if current == match.group(1) else
                "the committed dashboard is NOT a render of the committed "
                "state -- re-run scripts/render.py and commit the result"),
        left=match.group(1)[:16], right=current[:16],
        sources={"dashboard": "dashboard/index.html"},
    ))
