"""Commit named paths, one writer at a time: the company's only way into git.

    python scripts/commit.py -m "message" -- PATH [PATH ...]

Five departments edit one working tree side by side (docs/crew-plan.md). Two plain
`git commit`s at once collide on git's index lock, and a `git add -A` takes another
department's half-done edit into the wrong commit -- so a worker's `git add` and `git commit`
are denied in its argv (`qa.crew.DENY_ALL`) and this is what it has instead:

  * it holds one lock (`state/crew/commit.lock`) for the add and the commit together;
  * it commits only the paths it names (`git commit -- PATH`), whatever else is staged;
  * a worker's commit says which department and ticket wrote it, `Crew: <dept> <ticket>`,
    so the week can read who did what without a transcript.

It never pushes and never tags: those are the operator's and the deep pass's (CLAUDE.md).
"""

from __future__ import annotations

import argparse
import contextlib
import os
import subprocess
import sys
import time
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CODE_ROOT))

from qa.crew import crew_dir  # noqa: E402
from qa.state import file_lock  # noqa: E402

LOCK_WAIT_SECONDS = 300


def root() -> Path:
    return Path(os.environ.get("QA_REPO_ROOT") or CODE_ROOT).resolve()


def refused(paths: list[str], base: Path) -> str | None:
    """Why these paths may not be committed, or None.

    A file, by name: a pattern (`docs/*`, `:(glob)**`) or a directory takes in every edit
    under it, another department's half-done one with it -- the sweep this exists to stop.
    """
    if not paths:
        return "name the paths to commit after --"
    for path in paths:
        if path.strip() in ("", ".", "-A", "--all"):
            return f"{path!r} is the whole tree, not a path"
        if path.startswith(":") or any(char in path for char in "*?["):
            return f"{path!r} is a pattern; name each file"
        target = (base / path).resolve()
        if target != base and base not in target.parents:
            return f"{path} is outside the repository"
        if target.is_dir():
            return f"{path} is a directory; name each file"
    return None


def message(text: str) -> str:
    dept, ticket = os.environ.get("QA_CREW_DEPT"), os.environ.get("QA_CREW_TICKET")
    if dept and "Crew:" not in text:
        text = text.rstrip() + f"\n\nCrew: {dept} {ticket or ''}".rstrip()
    return text


def _git(base: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(base), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace")


def commit(text: str, paths: list[str]) -> int:
    base = root()
    why = refused(paths, base)
    if why:
        print(f"[commit] refused: {why}")
        return 2
    lock = crew_dir() / "commit"
    deadline = time.monotonic() + LOCK_WAIT_SECONDS
    while True:
        held = contextlib.ExitStack()
        try:
            held.enter_context(file_lock(lock))
        except OSError:
            # Windows' lock gives up after about ten seconds; another commit is running.
            held.close()
            if time.monotonic() > deadline:
                print("[commit] the commit lock stayed held for five minutes; nothing done")
                return 1
            time.sleep(1.0)
            continue
        with held:
            try:
                added = _git(base, "add", "--", *paths)
                if added.returncode != 0:
                    print(f"[commit] git add failed: {added.stderr.strip()[:300]}")
                    return 1
                done = _git(base, "commit", "-m", message(text), "--", *paths)
            except OSError as exc:
                print(f"[commit] git could not be run: {exc}")
                return 1
            print((done.stdout or done.stderr).strip()[:600])
            return 0 if done.returncode == 0 else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("-m", "--message", required=True)
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args(argv)
    return commit(args.message, args.paths)


if __name__ == "__main__":
    raise SystemExit(main())
