"""Where things live under state/, a lock, the journal as a plain log, and the list of filed bugs."""

from __future__ import annotations

import contextlib
import json
import os
import threading
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
    """An exclusive cross-process lock on one state file, through a .lock file beside it. Not reentrant.

    `poll` asks that often until `timeout`. Without it the wait is the OS's own, and on Windows LK_LOCK gives up
    with OSError after about ten seconds: never hold one across a network call."""
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


def atomic_write(target: Path, text: str) -> None:
    """Whole or not at all. A tmp per writer, and a replace tried again: on Windows it raises PermissionError
    while another process holds the file open."""
    target.parent.mkdir(parents=True, exist_ok=True)
    tmp = target.with_name(f"{target.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(text, encoding="utf-8")
    for attempt in range(20):
        try:
            tmp.replace(target)
            return
        except PermissionError:
            if attempt == 19:
                tmp.unlink(missing_ok=True)
                raise
            time.sleep(0.05)


def read_events(path: Path | None = None) -> list[dict]:
    """Every event in the journal, oldest first. A line that is not whole is skipped.

    split("\\n"), not splitlines(): an old line may hold a vendor's U+2028 or U+0085, and that is inside a line."""
    target = path or journal_path()
    if not target.exists():
        return []
    events = []
    for line in target.read_text(encoding="utf-8").split("\n"):
        if line.strip():
            try:
                events.append(json.loads(line))
            except ValueError:
                continue
    return events


def append_event(event: dict, path: Path | None = None, make_id=None) -> str:
    """One line onto the journal. `make_id(events)` names the event under the lock, so two writers cannot take
    one id. Whoever must not repeat itself checks read_events first.

    Plain ASCII on disk: their text may hold line separators or half an emoji. A process killed mid-write leaves
    a last line with no newline, and the next event must not fuse with it."""
    target = path or journal_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(target):
        if make_id is not None:
            event["msg_id"] = make_id(read_events(target))
        cut = False
        if target.exists() and target.stat().st_size:
            with open(target, "rb") as fh:
                fh.seek(-1, os.SEEK_END)
                cut = fh.read(1) != b"\n"
        with open(target, "a", encoding="utf-8", newline="\n") as fh:
            fh.write(("\n" if cut else "") + json.dumps(event, sort_keys=True) + "\n")
    return "appended"


def load_filed() -> dict:
    """{"rows": [...]}: one row per bug we hold a report for."""
    path = filed_path()
    if not path.exists():
        return {"rows": []}
    return json.loads(path.read_text(encoding="utf-8"))


def save_filed(data: dict) -> None:
    atomic_write(filed_path(), json.dumps(data, indent=1, ensure_ascii=False) + "\n")


@contextlib.contextmanager
def updating_filed():
    """filed.json under its lock: load, let the caller change it, save. Nobody holds a copy across a long wait."""
    with file_lock(filed_path(), poll=0.05, timeout=60.0):
        data = load_filed()
        yield data
        save_filed(data)
