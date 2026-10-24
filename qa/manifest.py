"""What we held, why, and what it was — kept after the body is gone.

Evidence is addressed by the sha256 of its content, so the id IS the integrity
proof. That is what lets the bodies leave git: a line naming the id, the size
and the call it answered proves what we had and that it has not changed, and
`scripts/verify.py` never promised the vendor a GitHub clone -- it promised the
capture is retained and one message away.

The one property everything rests on: **`call_key` reads the body.** Once a
capture is in the monthly archive the key cannot be recomputed on this machine,
so this module accumulates and a thinner entry never replaces a fuller one.
Rebuilding the manifest from what is currently visible would blank exactly the
oldest half -- the verdicts already sent, whose proof matters most.

Written where `keepset.track` runs, so the manifest and the keep set cannot
grow two ideas of what is held.

More than one process writes it: the pre-commit hook's `keep.py track` and
every fold append what is newly cited, `keep.py archive` stamps what a bundle
holds, and since the company five departments commit and fold side by side.
Each is a read, a merge and a write of the whole file, and two at once dropped
74 of 80 lines in tests/repo/test_manifest_lock.py. So every change goes
through `update`: under the manifest's own lock, re-read the file as it is
now, apply the change, write it back -- never a merge over a copy read
earlier, which is how the archive's stamp wrote over what `track` added while
the bundle was being built.
"""

from __future__ import annotations

import contextlib
import json
import os
import time
from pathlib import Path
from typing import Callable

from qa.evidence import call_key
from qa.keepset import evidence_path
from qa.state import state_dir

# The fields a refresh may overwrite with a fresher reading. Everything else is
# written once, while the body is on disk, and never contradicted.
REFRESHABLE = ("why",)

# How long a writer waits for another one, and how often it asks. Giving up
# means a manifest not written (track never raises), so the wait is long; the
# lock is held only for a read, a merge and a write, so the ask is frequent.
LOCK_WAIT_SECONDS = 120
LOCK_POLL = 0.02
# Windows refuses a replace while another process has the file open -- git
# reading it, the guard in tests/repo, a session's editor (memory "adding a
# writer changes every other writer"). Retried for a moment, then written in
# place: still under the lock, so no other writer can interleave.
REPLACE_TRIES = 100
REPLACE_PAUSE = 0.02


def manifest_path() -> Path:
    """Beside the state it describes, never fixed at import.

    `keep.snapshot_dir` learned this the hard way on 2026-09-12: a constant
    computed at import wrote a test's tmp_path data over the repository's own
    committed archive, and the suite went green doing it.
    """
    return state_dir().parent / "audits" / "evidence-manifest.jsonl"


def entry(evidence_id: str, why: str, root: Path | None = None) -> dict | None:
    """One line, computed while the body is still readable. None if it is not."""
    path = evidence_path(evidence_id, root)
    if not path.is_file():
        return None
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        record = {}
    try:
        call = call_key(record) if isinstance(record, dict) else ""
    except Exception:  # noqa: BLE001 -- a key we cannot derive is not a crash
        call = ""
    return {"id": evidence_id, "bytes": path.stat().st_size,
            "call": call, "why": why, "archive": ""}


def merge(known: dict[str, dict], fresh: dict[str, dict]) -> dict[str, dict]:
    """Accumulate. A fresh reading fills gaps and refreshes `why`, never empties.

    Pure, because this is the rule the manifest lives or dies by and a rule
    worth a test is worth being able to test without a filesystem.
    """
    out = {key: dict(value) for key, value in known.items()}
    for key, value in fresh.items():
        if key not in out:
            out[key] = dict(value)
            continue
        row = out[key]
        for field, new in value.items():
            if field in REFRESHABLE:
                if new:
                    row[field] = new
            elif new and not row.get(field):
                row[field] = new
    return out


def parse(text: str) -> dict[str, dict]:
    """id -> line, from the text of a manifest wherever it came from.

    Separate from `read` so a caller can hand it the COMMITTED manifest. The
    guard in tests/repo/test_evidence_in_git.py promises "every cited id is in
    the committed manifest" and reads its citations out of HEAD for exactly
    that reason -- and then read the manifest from the working tree, where a
    line staged but not committed is indistinguishable from one a clone holds.
    """
    out: dict[str, dict] = {}
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict) and row.get("id"):
            out[str(row["id"])] = row
    return out


def read(path: Path | None = None) -> dict[str, dict]:
    """Every line we have. A half-written line is skipped, never guessed at."""
    target = path or manifest_path()
    try:
        return parse(target.read_text(encoding="utf-8"))
    except OSError:
        return {}


def _lock_once(handle) -> None:
    """Take the lock now or raise OSError: never the OS's own wait."""
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)


def _unlock(handle) -> None:
    if os.name == "nt":
        import msvcrt

        handle.seek(0)
        msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


@contextlib.contextmanager
def _held(target: Path):
    """The manifest's own lock, `<manifest>.lock` beside it (gitignored), asked for every
    20 ms until LOCK_WAIT_SECONDS.

    The same lock file and the same byte `qa.state.file_lock` would take, but not its wait:
    on Windows that is LK_LOCK, which retries once a SECOND, so two contending writers
    queue in whole seconds -- 80 refreshes took 92 s in tests/repo/test_manifest_lock.py.
    """
    lock_path = target.with_name(target.name + ".lock")
    handle = open(lock_path, "a+b")
    try:
        deadline = time.monotonic() + LOCK_WAIT_SECONDS
        while True:
            try:
                _lock_once(handle)
                break
            except OSError:
                if time.monotonic() > deadline:
                    raise
                time.sleep(LOCK_POLL)
        try:
            yield
        finally:
            _unlock(handle)
    finally:
        handle.close()


def _text(entries: dict[str, dict]) -> str:
    """Sorted by id, one line each, so an unchanged manifest has no diff."""
    lines = [json.dumps(entries[key], ensure_ascii=False, sort_keys=True)
             for key in sorted(entries)]
    return "\n".join(lines) + ("\n" if lines else "")


def _replace(text: str, target: Path) -> None:
    """Whole or not at all, for a reader that takes no lock (git add, the guard): a
    temporary file of this writer's own, then a replace."""
    tmp = target.with_name(f"{target.name}.{os.getpid()}.tmp")
    try:
        tmp.write_text(text, encoding="utf-8")
        for _ in range(REPLACE_TRIES):
            try:
                os.replace(tmp, target)
                return
            except PermissionError:
                time.sleep(REPLACE_PAUSE)
        target.write_text(text, encoding="utf-8")
    finally:
        tmp.unlink(missing_ok=True)


def update(change: Callable[[dict[str, dict]], dict[str, dict]],
           path: Path | None = None) -> tuple[dict[str, dict], dict[str, dict]]:
    """The one way the manifest is changed. Returns (before, after).

    Under the lock, `change` is handed the manifest as it is NOW and returns what
    it should be. A caller that read the manifest earlier -- the archive, before a
    build of several minutes -- merges into this reading, never into its own.
    """
    target = path or manifest_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with _held(target):
        before = read(target)
        after = change(before)
        _replace(_text(after), target)
    return before, after


def write(entries: dict[str, dict], path: Path | None = None) -> int:
    """Replace the manifest with `entries`, through `update`."""
    _, after = update(lambda _known: entries, path)
    return len(after)


def refresh(keep: dict[str, str], root: Path | None = None,
            path: Path | None = None) -> tuple[int, int]:
    """Fold what is on disk now into what the manifest already knows.

    Returns (added, held). `added` counts ids the manifest had never seen, so a
    run that adds nothing is a run where every cited capture was already
    proved -- which is the steady state, not a failure. The bodies are read
    before the lock is taken; only the merge and the write hold it.
    """
    fresh = {}
    for evidence_id, why in keep.items():
        row = entry(evidence_id, why, root)
        if row is not None:
            fresh[evidence_id] = row
    known, merged = update(lambda current: merge(current, fresh), path)
    return len(set(merged) - set(known)), len(merged)
