"""Where things live under state/, a lock, the journal as a plain log, and the list of filed bugs."""

from __future__ import annotations

import contextlib
import json
import os
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def state_dir() -> Path:
    """state/, or QA_STATE_DIR so a test never touches the real one."""
    override = os.environ.get("QA_STATE_DIR")
    return Path(override) if override else REPO_ROOT / "state"


def journal_path() -> Path:
    return state_dir() / "journal" / "events.jsonl"


def filed_path() -> Path:
    return state_dir() / "filed.json"


@contextlib.contextmanager
def file_lock(path: Path, poll: float | None = None, timeout: float = 120.0):
    """An exclusive cross-process lock on one state file, through a .lock file beside it.

    `poll` asks that often until `timeout`; without it the wait is the OS's own."""
    lock_path = path.with_name(path.name + ".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    handle = open(lock_path, "a+b")

    def take(wait: bool) -> None:
        if os.name == "nt":
            import msvcrt

            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK if wait else msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(handle.fileno(), fcntl.LOCK_EX | (0 if wait else fcntl.LOCK_NB))

    try:
        if poll is None:
            take(wait=True)
        else:
            deadline = time.monotonic() + timeout
            while True:
                try:
                    take(wait=False)
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        raise
                    time.sleep(poll)
        try:
            yield
        finally:
            if os.name == "nt":
                import msvcrt

                handle.seek(0)
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
    finally:
        handle.close()


def read_events(path: Path | None = None) -> list[dict]:
    """Every event in the journal, oldest first. A line that is not whole is skipped."""
    target = path or journal_path()
    if not target.exists():
        return []
    events = []
    for line in target.read_text(encoding="utf-8").splitlines():
        try:
            events.append(json.loads(line))
        except ValueError:
            continue
    return events


def append_event(event: dict, path: Path | None = None) -> str:
    """One line onto the journal. Whoever must not repeat itself checks read_events first."""
    target = path or journal_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(target):
        with open(target, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(json.dumps(event, ensure_ascii=False, sort_keys=True) + "\n")
    return "appended"


def load_filed() -> dict:
    """{"rows": [...]}: one row per bug we hold a report for."""
    path = filed_path()
    if not path.exists():
        return {"rows": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save_filed(data: dict) -> None:
    path = filed_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    tmp.write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(tmp, path)
