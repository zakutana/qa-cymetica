"""Rule 12, made enforceable: the committed state must be what its inputs fold to.

Operating rule 12 said "before every commit, re-fold and re-render". There is
no CI and no hook in this repository, so as written it reduced to "the
operator remembers" -- which is the same class of guarantee as the convention
that every test carries a @qa tag, and that one needed a collection-time abort
to survive contact with a tired operator at 2am.

Two checks, both in the meta block, so they run before any live request:

  (a) the committed ledger is what its journal and run records fold to
  (b) the committed dashboard is a render of that ledger

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

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent
LEDGER = REPO / "state" / "ledger.json"
DASHBOARD = REPO / "dashboard" / "index.html"

HASH_MARKER = re.compile(r"<!-- qa-payload-sha256: ([0-9a-f]{64}) -->")


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
        refolded = ledger_mod.compose()
    except SystemExit as exc:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"the ledger cannot be re-folded right now: {exc}",
        ))
        return

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
        current = render_mod.payload_hash(render_mod.build_payload())
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
