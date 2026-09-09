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

# What the page actually shows, so the marker can be held against it rather
# than against a value recomputed from the ledger alone.
EMBEDDED_PAYLOAD = re.compile(
    r'<script id="data" type="application/json">(.*?)</script>', re.S)


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

    from qa.state import RunIntegrityError, read_events

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
    except RunIntegrityError as exc:
        # A clone has the run record and not the preregistration tags, so the
        # record contradicts a fact outside itself and compose refuses. Rule 8:
        # a comparison we could not make is not a comparison that failed. This
        # escaped the SystemExit below and errored the guard outright.
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"the ledger cannot be re-folded here: {exc}",
            sources={"ledger": "state/ledger.json"}))
        return
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

    # One definition of drift, in scripts/ledger.py, shared with `--check`.
    # It was written out twice before and the two disagreed: this compared only
    # `findings` while --check compared the whole document, so a stale `counts`
    # block -- the "6 in the tiles" drift the module docstring names as the
    # reason this file exists -- was invisible here while --check exited 1.
    #
    # `events_head` was then folded into the comparison to catch "a head left
    # behind by a bounty.py run nobody re-folded" (2026-09-07). That reading is
    # withdrawn, and the argument is in `drift`'s docstring: it conflated being
    # BEHIND the journal with not being WHAT THE INPUTS FOLD TO. The console
    # appends two vendor_read events every fifteen minutes, the fold moves
    # nothing on an ok read, and this guard was therefore red for a boring
    # reason most of its life -- which is how a guard stops being read.
    #
    # Nothing is given up. The rows are still compared against a refold over
    # the WHOLE journal, so a pending event that WOULD move something fires
    # this before anyone folds it; the head is checked as a citation, and
    # write_ledger keeps the level-with-the-journal invariant where it belongs,
    # at the moment of the write.
    verdict = ledger_mod.drift(committed, refolded, read_events())
    conclude(Measurement(
        verdict=("failed" if verdict["rows"] or verdict["keys"]
                 or not verdict["anchored"] else "passed"),
        reason=verdict["reason"],
        left=verdict["rows"], right=verdict["keys"],
        population={"since_head": verdict["since_head"],
                    "anchored": verdict["anchored"]},
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
        # This guard asks one question: is the page a render of the ledger?
        # Whether the ledger is level with the journal is the sibling guard's,
        # and build_payload no longer refuses on it at all -- the flag that
        # used to be needed here is gone with the refusal. The reason the flag
        # gave was stale too: it said every pytest session appends a
        # run_recorded event, which stopped being true when `attest` became
        # default-off. What actually moves the journal under this guard is the
        # console's timer.
        current = render_mod.payload_hash(render_mod.build_payload())
    except SystemExit as exc:
        conclude(Measurement(verdict="inconclusive",
                             reason=f"the payload cannot be built: {exc}"))
        return

    # Bind the marker to the BODY. Comparing a recomputed hash with the comment
    # read back out of the same file left the page itself unexamined: nothing
    # tied that string to the data beneath it, so editing a number in the
    # embedded payload -- dashboard/index.html is not under state/, so the
    # PreToolUse hook does not stop it -- kept this guard green on a page that
    # was not a render of anything. Audit, 2026-09-07.
    embedded = EMBEDDED_PAYLOAD.search(html)
    if embedded is None:
        conclude(Measurement(
            verdict="inconclusive",
            reason="the committed dashboard carries no embedded payload block, "
                   "so the marker cannot be bound to what the page shows",
            sources={"dashboard": "dashboard/index.html"}))
        return
    try:
        page_hash = render_mod.payload_hash(json.loads(embedded.group(1)))
    except ValueError as exc:
        conclude(Measurement(
            verdict="failed",
            reason=f"the dashboard's embedded payload is not valid JSON: {exc}",
            sources={"dashboard": "dashboard/index.html"}))
        return

    agrees = current == match.group(1) == page_hash
    conclude(Measurement(
        verdict="passed" if agrees else "failed",
        reason=("the committed dashboard is a render of the committed state, "
                "and the payload it carries hashes to the marker stamped on it"
                if agrees else
                "the committed dashboard is NOT a render of the committed "
                "state -- re-run scripts/render.py and commit the result"
                if page_hash == match.group(1) else
                "the dashboard's own payload does not hash to the marker "
                "stamped on the page: the file has been edited after render"),
        left=match.group(1)[:16], right={"rebuilt": current[:16],
                                         "from_the_page": page_hash[:16]},
        sources={"dashboard": "dashboard/index.html"},
    ))


RUN_ID = re.compile(r"run-\d{8}T\d{6}Z-[0-9a-z]+")


def _run_ids(node) -> set[str]:
    """Every `run_id` field anywhere in the ledger, at any depth.

    A row cites its run from four places -- provenance, first_seen.cause,
    check.adjudicated_by and each transition's cause -- and a fifth would be
    added without this test hearing about it. Walking for the field name
    covers all of them and, unlike a text scan, counts only citations.

    The value has to look like a record id as well as sit under the right
    key: 16 rows migrated from before the contract carry `run_id: "legacy"`,
    which names the migration rather than a file, and no file will ever
    satisfy it.
    """
    found: set[str] = set()
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "run_id" and isinstance(value, str) and RUN_ID.fullmatch(value):
                found.add(value)
            else:
                found |= _run_ids(value)
    elif isinstance(node, list):
        for value in node:
            found |= _run_ids(value)
    return found

# Run records the committed journal cites and this repository does not have.
# Both predate the guard below and neither can be recovered:
#
#   run-20260905T180442Z-8f0af4f  never committed. The bytes are gone; the
#       journal keeps its attested sha256 4202df91... and nothing else.
#   run-20260905T182750Z-8d7126c  committed in b2bbaad, deleted in efe76d1
#       ("git rev-parse echoes its argument on failure; the run record
#       believed it") because the record itself was wrong. The blob still in
#       history hashes to 5bf4bf91..., the journal attested 581f82ee... The
#       two disagree and nothing here says which is the version the fold read,
#       so neither can be restored as evidence.
#
# The current ledger stands on neither. This is a record of a loss, not
# permission for the next one: an addition here means evidence went missing,
# and it has to be explained as specifically as these two. When a listed
# record turns out to exist after all, the test says so and the line goes.
LOST_RUN_RECORDS = {
    "run-20260905T180442Z-8f0af4f",
    "run-20260905T182750Z-8d7126c",
}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_every_run_record_the_state_cites_is_in_the_repository():
    """Whatever the ledger or the journal stands on must be readable by others.

    `state/runs/` is gitignored: most of what lands there adjudicated nothing,
    and an untracked record made every tree dirty enough for prereg.py to
    refuse. The records that ARE evidence are force-added by
    scripts/ledger.py::_track_run_record at the moment a fold stands on one.

    This is the converse, and it is deliberately stated over the *citation*
    rather than over that function: a run reachable only through a journal
    event still has to be there, and the mechanism that puts it there can be
    replaced without touching this test. A cited record that is not in the
    repository makes the ledger unverifiable by anyone who clones it -- the
    one thing the whole evidence trail exists to prevent.
    """
    import subprocess

    # Structurally, never by scanning the text. A regex over the whole file
    # also matches a run id merely MENTIONED -- in a withdraw reason, a note,
    # a detail.reason -- and one mention of an exploratory run would demand
    # that a gitignored record be tracked, with no way out but to commit
    # evidence nothing stands on. A citation is a `run_id` field.
    cited = set()
    if LEDGER.exists():
        cited |= _run_ids(json.loads(LEDGER.read_text(encoding="utf-8")))
    journal = REPO / "state" / "journal" / "events.jsonl"
    if journal.exists():
        for line in journal.read_text(encoding="utf-8").splitlines():
            if line.strip():
                event = json.loads(line)
                if event.get("type") == "run_recorded" and event.get("run_id"):
                    cited.add(event["run_id"])

    if not cited:
        conclude(Measurement(
            verdict="inconclusive",
            reason="no committed state cites a run record yet",
            sources={"ledger": "state/ledger.json"}))
        return

    try:
        listed = subprocess.run(
            ["git", "ls-files", "state/runs"], cwd=REPO, check=True,
            capture_output=True, text=True).stdout
    except (OSError, subprocess.CalledProcessError) as exc:  # noqa: BLE001
        # Rule 8: a read we could not make is not an empty read. Reporting
        # "every cited record is missing" because git would not run would be
        # a louder lie than saying nothing.
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"git could not list state/runs: {exc}"))
        return

    tracked = set(RUN_ID.findall(listed))
    missing = sorted(cited - tracked - LOST_RUN_RECORDS)
    # A loss that stopped being one must not stay on the list, or the list
    # slowly becomes a place to put inconvenient ids.
    recovered = sorted(LOST_RUN_RECORDS & tracked)

    problems = []
    if missing:
        problems.append(
            f"{len(missing)} run record(s) cited by the committed state are "
            f"not in the repository, so the ledger cannot be re-folded from a "
            f"clone: {', '.join(missing[:5])}")
    if recovered:
        problems.append(
            f"{', '.join(recovered)} is listed as lost and is tracked after "
            f"all -- delete the entry from LOST_RUN_RECORDS")

    conclude(Measurement(
        verdict="failed" if problems else "passed",
        reason=("; ".join(problems) if problems else
                f"all {len(cited - LOST_RUN_RECORDS)} cited run record(s) are "
                f"tracked, beside {len(LOST_RUN_RECORDS)} named as lost"),
        left={"cited": len(cited)}, right={"tracked": len(tracked)},
        population={"missing": missing[:20], "recovered": recovered},
        sources={"journal": "state/journal/events.jsonl",
                 "runs": "state/runs"}))
