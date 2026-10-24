"""Which captured responses have to survive, and why.

`evidence/` was 469 MB on disk and 7 747 files in git on 2026-09-12, growing
40-170 MB a day, and nothing in the pipeline reads it by machine. What does
stand on it is smaller and nameable, and this module is the one place that says
which -- so the tracker, the pruner and the guard cannot grow three ideas of
"cited":

    their-words  the vendor's own answer, cited by a journal event the fold
                 refuses to move a filing state without (qa/fold.py:463)
    promised     the request and response behind a verdict or a report we have
                 already sent: scripts/verify.py tells them in every message
                 that those are "provided on request", and scripts/submit.py
                 says "evidence retained" in every report
    row          what a ledger row stands on now and stood on at each
                 transition -- the run record's results for that row's checks
    trade        what our own paper orders and clones were recorded against

Everything else is working material: worth a few days while somebody is
investigating a surface, and nothing after that.

[operator 2026-09-12] decided the shape -- CLAUDE.md, "What we keep, and what we
let go": git keeps what something cites, the disk keeps the rest three days.

Two sets, because they answer two different questions:

    must_keep()       everything above, read from the files on this machine.
                      The tracker adds these to git; the pruner never deletes
                      one.
    must_be_tracked() the subset a CLONE has to be able to verify, computed
                      from the COMMITTED journal and ledger. The console
                      appends an event every fifteen minutes, so a guard
                      reading the working tree would be red half the day over
                      captures no clone can see yet.

Ids that are not a sha256 are not captures at all: `scripts/migrate_ledger.py`
wrote 23 provenance strings on 2026-09-04 -- `bounty.json#report-46`,
`submissions.json#agent-names` -- naming a source file and a key inside it,
before the evidence store existed. `legacy_citations()` returns them so a guard
can say so rather than reporting 23 missing files.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
from pathlib import Path

from qa.state import ledger_path, read_events, runs_dir, state_dir

REPO_ROOT = Path(__file__).resolve().parent.parent

HASH = re.compile(r"^[0-9a-f]{64}$")

# The event types the fold will not move a filing state without: their answer
# had to have been captured. Plus the inbound a2a message, which is the same
# kind of thing arriving through the other door.
VENDOR_WORDS = frozenset({"filing_outcome", "verification_outcome",
                          "vendor_status", "reply", "a2a_outcome", "message"})

# The events that record something going OUT with a promise attached. Each
# names the run its numbers came from and the finding it was about, so the
# evidence it promised is that run's results for that finding's checks.
PROMISES = frozenset({"verification_intent", "verification_outcome",
                      "filing_intent", "filing_outcome"})

TRADE_RECORDS = ("paper.jsonl", "clones.jsonl")

# git chokes on a command line of thousands of paths, and Windows sooner.
GIT_BATCH = 200

# Set by scripts/commit.py in the environment of every git call it makes, so the hook it
# sets off knows the commit names its own paths. Inside `git commit -- PATH` a `git add` lands
# in the temporary index the commit is built from: the manifest rode into desk 3280994c
# (+971 lines) and the page into four commits in nine minutes (T-0038, OP-0016). Under it,
# `track` writes the manifest and does not add it, the hook renders the page and does not
# add it, and commit.py commits each on its own. Not GIT_INDEX_FILE -- `git rev-parse
# --git-path index` returns exactly that, so a comparison never fires, and a session's own
# `git commit -- PATH` needs the manifest to travel with its state; not QA_CREW_DEPT --
# `console poll` and a manual run go without it. .githooks/pre-commit spells the name too.
COMMIT_PY_MARKER = "QA_COMMIT_PY"


def under_commit_py() -> bool:
    """The hook is running for a commit scripts/commit.py makes."""
    return bool(os.environ.get(COMMIT_PY_MARKER))


def evidence_path(evidence_id: str, root: Path | None = None) -> Path:
    """Where a capture lives. Through `evidence_root` so a test session -- which
    sets QA_STATE_DIR -- looks in its own store rather than the repository's."""
    from qa.evidence import evidence_root

    digest = str(evidence_id).split(":")[-1]
    base = root if root is not None else evidence_root()
    return base / "sha256" / digest[:2] / f"{digest}.json"


def _ids(node, into: set[str]) -> None:
    """Every evidence id under a record, wherever it is spelled."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ("evidence_id", "evidence_ids"):
                values = value if isinstance(value, list) else [value]
                for item in values:
                    if isinstance(item, str) and item:
                        into.add(item.split(":")[-1])
            else:
                _ids(value, into)
    elif isinstance(node, list):
        for item in node:
            _ids(item, into)


def _rows(path: Path) -> list[dict]:
    """A .jsonl we do not own the writer of. A half-written line is normal."""
    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []
    out = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def _checks_of(ledger: dict) -> dict[str, set[str]]:
    findings = ledger.get("findings") or {}
    return {fid: {c for c in (row.get("checks") or []) if isinstance(c, str)}
            for fid, row in findings.items() if isinstance(row, dict)}


def _run_evidence(run: dict | None, nodeids: set[str]) -> set[str]:
    """What one run captured for one row's checks.

    Parametrised ids are matched on their function, because a row names the
    function and a record names every case of it.
    """
    if not isinstance(run, dict):
        return set()
    found: set[str] = set()
    for result in run.get("results") or []:
        nodeid = str(result.get("nodeid") or "")
        if nodeids and nodeid not in nodeids and nodeid.split("[")[0] not in nodeids:
            continue
        for item in result.get("evidence_ids") or []:
            if isinstance(item, str) and item:
                found.add(item.split(":")[-1])
    return found


def _run_ids_of(row: dict) -> set[str]:
    """Every run this row has ever stood on: now, and at each transition."""
    out: set[str] = set()

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "run_id" and isinstance(value, str) and value:
                    out.add(value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    walk(row)
    return out


def cited(events: list[dict], ledger: dict, load_run, trades=()) -> dict[str, str]:
    """evidence id -> the one reason it may never be deleted.

    Pure over its inputs so both callers -- the working tree and HEAD -- get the
    same answer from the same code.
    """
    kept: dict[str, str] = {}

    def note(ids, reason):
        for item in ids:
            if HASH.match(item):
                kept.setdefault(item, reason)

    for event in events:
        if event.get("type") in VENDOR_WORDS:
            found: set[str] = set()
            _ids(event, found)
            note(found, "their-words")

    checks_of = _checks_of(ledger)
    runs: dict[str, dict | None] = {}

    def record(run_id: str):
        if run_id not in runs:
            runs[run_id] = load_run(run_id)
        return runs[run_id]

    for event in events:
        if event.get("type") not in PROMISES:
            continue
        # A verification names one run and one finding; a filing (since B4
        # of the review of 2026-09-23) names the run behind each finding.
        pairs = [(event.get("run_id"), event.get("finding_id"))]
        pairs += [(run, fid) for fid, run in (event.get("runs") or {}).items()]
        for run_id, finding_id in pairs:
            if not isinstance(run_id, str) or not isinstance(finding_id, str):
                continue
            note(_run_evidence(record(run_id), checks_of.get(finding_id, set())),
                 "promised")

    for finding_id, row in (ledger.get("findings") or {}).items():
        if not isinstance(row, dict):
            continue
        nodeids = checks_of.get(finding_id, set())
        for run_id in _run_ids_of(row):
            note(_run_evidence(record(run_id), nodeids), "row")

    for row in trades:
        found = set()
        _ids(row, found)
        note(found, "trade")

    return kept


def legacy_citations(events: list[dict]) -> set[str]:
    """Citations that name a pre-contract source rather than a capture."""
    found: set[str] = set()
    for event in events:
        _ids(event, found)
    return {item for item in found if not HASH.match(item)}


def _load_run_from_disk(run_id: str) -> dict | None:
    path = runs_dir() / f"{run_id}.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


class UnreadableLedger(Exception):
    """The ledger is on disk and will not parse. Not a ledger citing nothing."""


def _ledger_as_written() -> dict:
    """The rows as they are on disk, not as the contract wants them.

    `qa.state.load_ledger` validates and raises on a row missing a field, and a
    keep set that inherits that refuses to name anything. What this needs from
    the ledger is which runs a row has stood on, so the parse stays lenient
    about the SHAPE of a row: one too malformed to say loses nothing else.

    It was lenient about the FILE as well, and that is a different thing. A
    ledger caught mid-write returned `{}` from here without raising, `must_keep`
    came back silently thin instead of refusing, and `prune_runs --apply` then
    deleted captures a row stands on -- the request and response every verdict
    we have sent promises the vendor "on request". The journal read one line
    above has always refused: `read_events` raises on a truncated line, and both
    sweeps in the pruner then keep everything and print why. This is rule 8 over
    the second of the two files, and the safe direction is the same: a pile that
    grows beats evidence that is gone.

    Absent is still empty, as it is for the journal. A state directory that has
    never been folded has no rows, and refusing there would mean nothing is ever
    pruned on it.
    """
    path = ledger_path()
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise UnreadableLedger(f"{path.name}: {exc}") from exc


def must_keep() -> dict[str, str]:
    """The whole set, from this machine: git keeps it, the pruner never cuts it."""
    trades = []
    for name in TRADE_RECORDS:
        trades.extend(_rows(state_dir() / name))
    return cited(read_events(), _ledger_as_written(), _load_run_from_disk,
                 trades)


def _committed(rel: str) -> str | None:
    result = subprocess.run(["git", "show", f"HEAD:{rel}"], cwd=REPO_ROOT,
                            capture_output=True, text=True, encoding="utf-8",
                            errors="replace")
    return result.stdout if result.returncode == 0 else None


def committed_sources() -> tuple[list[dict], dict] | None:
    """The journal and the ledger as a clone would read them, or None."""
    raw_events = _committed("state/journal/events.jsonl")
    raw_ledger = _committed("state/ledger.json")
    if raw_events is None or raw_ledger is None:
        return None
    events = []
    for line in raw_events.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            return None
    try:
        ledger = json.loads(raw_ledger)
    except json.JSONDecodeError:
        return None
    return events, ledger


def must_be_tracked() -> dict[str, str] | None:
    """What a clone must have to check us. None when git cannot be read."""
    sources = committed_sources()
    if sources is None:
        return None
    events, ledger = sources
    return cited(events, ledger, _load_run_from_disk)


def track(quiet: bool = False) -> int:
    """Add every capture that must survive and git does not yet hold.

    Here rather than in the CLI because three callers need it -- the commit
    hook, the fold, and the deep pass -- and a second copy of this walk would
    be free to disagree with `must_keep` about what "cited" means.

    Never raises. Bookkeeping may not be the reason a commit cannot be made;
    the guard reports the same gap afterwards, where somebody is looking.
    """
    try:
        keep = must_keep()
        held = tracked_evidence()
    except Exception as exc:  # noqa: BLE001
        if not quiet:
            print(f"keep: could not work out what to keep: {exc}")
        return 0
    if held is None:
        if not quiet:
            print("keep: git could not be read; nothing added")
        return 0

    # Since D3 the manifest is the ONLY thing this adds. The bodies stay on
    # disk and go to `archive/` monthly; git holds 228 KB of proof where it
    # held 167 MB of JSON, and `tracked_evidence()` is expected to be empty.
    # `call_key` reads the body, so the line has to be written while the
    # capture is still here -- which is exactly when this runs. Imported inside
    # the function, not at module scope: qa.manifest reads `evidence_path`
    # from this module.
    from qa import manifest as _manifest

    try:
        added_lines, total = _manifest.refresh(keep)
        wanted = [str(_manifest.manifest_path().relative_to(REPO_ROOT))
                  .replace("\\", "/")]
    except Exception as exc:  # noqa: BLE001 -- same rule as above: never block
        if not quiet:
            print(f"keep: WARNING the manifest was not written: {exc}")
        return 0

    # Under scripts/commit.py the manifest is written and not added: an add here is a commit
    # of it under somebody else's message, and commit.py commits it on its own right after.
    if not under_commit_py():
        result = subprocess.run(["git", "add", "-f", *wanted], cwd=REPO_ROOT,
                                capture_output=True, text=True)
        if result.returncode != 0:
            if not quiet:
                print(f"keep: WARNING could not add the manifest: "
                      f"{result.stderr.strip()[:200]}")
            return 0
    if added_lines and not quiet:
        print(f"keep: {added_lines} new capture(s) proved, {total} in the "
              f"manifest; bodies stay on disk for `keep.py archive`")
    return added_lines


def untrackable(keep: dict, held: set[str] | None) -> tuple[list[str], str]:
    """Which tracked captures nothing stands on any more, and why not to guess.

    Pure, and separate from the command that acts on it, because the refusals
    matter more than the list. `track` only ever added, so the keep set could
    only grow: folding the ledger onto a fresh verification run on 2026-09-12
    left 115 captures from the previous run in git with nothing citing them,
    the guard went red, and no mechanism could clear it.

    Two refusals, both one command away from deleting what every verdict we
    have sent promises the vendor on request:

      * an EMPTY keep set is never a licence to drop everything. It is what a
        lenient parse, a half-written row or an unreadable file looks like.
      * git unreadable is not "git holds nothing".
    """
    if not keep:
        return [], ("the keep set came back empty, which is what an unreadable "
                    "record looks like; nothing is dropped on it")
    if held is None:
        return [], "git could not be read; nothing is dropped"
    return sorted(held - set(keep)), ""


def untrack(quiet: bool = False) -> int:
    """Let go of tracked captures nothing cites. They stay on disk.

    `git rm --cached` only: the bytes remain in the working tree until the
    pruner's own three-day rule reaches them, and they remain in history
    either way, so nothing a verdict cited becomes unrecoverable.
    """
    try:
        keep, held = must_keep(), tracked_evidence()
    except Exception as exc:  # noqa: BLE001
        if not quiet:
            print(f"keep: could not work out what to keep: {exc}")
        return 0

    dropping, why = untrackable(keep, held)
    if why and not quiet:
        print(f"keep: {why}")
    paths = []
    for evidence_id in dropping:
        path = evidence_path(evidence_id)
        paths.append(str(path.relative_to(REPO_ROOT)).replace("\\", "/"))

    gone = 0
    for start in range(0, len(paths), GIT_BATCH):
        chunk = paths[start:start + GIT_BATCH]
        result = subprocess.run(["git", "rm", "--cached", "-q", "--", *chunk],
                                cwd=REPO_ROOT, capture_output=True, text=True)
        if result.returncode == 0:
            gone += len(chunk)
        elif not quiet:
            print(f"keep: WARNING could not untrack {len(chunk)} capture(s): "
                  f"{result.stderr.strip()[:200]}")
    if gone and not quiet:
        print(f"keep: untracked {gone} capture(s) nothing cites any more")
    return gone


def tracked_evidence() -> set[str] | None:
    """Evidence ids git currently holds, or None when git cannot be read."""
    result = subprocess.run(["git", "ls-files", "evidence"], cwd=REPO_ROOT,
                            capture_output=True, text=True)
    if result.returncode != 0:
        return None
    out = set()
    for line in result.stdout.split():
        stem = Path(line.strip()).stem
        if HASH.match(stem):
            out.add(stem)
    return out
