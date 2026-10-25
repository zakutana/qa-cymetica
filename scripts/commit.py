"""Commit named paths, one writer at a time: the company's only way into git.

    python scripts/commit.py -m "message" -- PATH [PATH ...]

Five departments edit one working tree side by side (docs/crew-plan.md). Two plain
`git commit`s at once collide on git's index lock, and a `git add -A` takes another
department's half-done edit into the wrong commit -- so a worker's `git add` and `git commit`
are denied in its argv (`qa.crew.DENY_ALL`) and this is what it has instead:

  * it holds one lock (`state/crew/commit.lock`) for the add and the commit together;
  * it commits only the paths it names (`git commit -- PATH`), whatever else is staged --
    an ignored one only when git's index already holds it, which is how the run record a
    fold staged goes in (OP-0009);
  * a worker's commit says which department and ticket wrote it, `Crew: <dept> <ticket>`,
    so the week can read who did what without a transcript;
  * every git call it makes carries its marker (`qa.keepset.COMMIT_PY_MARKER`), so the
    pre-commit hook it sets off writes the evidence manifest and renders the page without
    adding either -- an add there lands in the commit of named paths (T-0038) -- and then
    each goes in on its own: "manifest", then "render" when state/ is clean.

It never pushes and never tags: those are the operator's and the deep pass's (CLAUDE.md).
"""

from __future__ import annotations

import argparse
import contextlib
import importlib.util
import os
import subprocess
import sys
import time
from pathlib import Path

CODE_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CODE_ROOT))

from qa.crew import crew_dir  # noqa: E402
from qa.keepset import COMMIT_PY_MARKER  # noqa: E402
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
    """One git call, with the marker in its environment only: `crew.py tidy` calls `commit()`
    in-process, and a marker left in os.environ would silence the next `keep.py track`."""
    return subprocess.run(["git", "-C", str(base), *args], capture_output=True, text=True,
                          encoding="utf-8", errors="replace",
                          env={**os.environ, COMMIT_PY_MARKER: "1"})


def _index_name(base: Path, path: str) -> str:
    """A named path as `git ls-files` lists it: from the repository's root, forward slashes --
    `./a.txt`, `docs\\x.md` and an absolute path inside the tree all name one entry."""
    try:
        return (base / path).resolve().relative_to(base).as_posix()
    except (OSError, ValueError):
        return Path(path).as_posix()


def _add(base: Path, paths: list[str]) -> str | None:
    """Stage the named paths; why not, or None.

    `-f` for what git's index already holds, and only for that. A plain `git add` refuses a
    path under an ignored folder even when the index holds it, so the run record `ledger.py
    --run` staged with `git add -f` under the ignored state/runs/ could not be committed by
    any worker: a company sweep failed three times on it (OP-0009, T-0002). What nothing
    staged stays refused -- a debug run's record, a capture body: the reason those folders
    are ignored at all.

    One `git ls-files -z` for every path, not one git process per path under the commit lock
    every department waits on (deep pass 2026-10-25, R07). `-z` because git quotes a non-ASCII
    path otherwise; each name is compared the way the index lists it (`_index_name`)."""
    listed = _git(base, "ls-files", "-z", "--", *paths)
    in_index = (set(listed.stdout.split("\0")) - {""}) if listed.returncode == 0 else set()
    held = [path for path in paths if _index_name(base, path) in in_index]
    rest = [path for path in paths if path not in held]
    for flags, group in ((["-f"], held), ([], rest)):
        if group:
            added = _git(base, "add", *flags, "--", *group)
            if added.returncode != 0:
                return added.stderr.strip() or f"git add exited {added.returncode}"
    return None


def pass_in_flight() -> bool:
    """The deep pass's own notebook says it runs (`processes.pass_in_flight`)."""
    spec = importlib.util.spec_from_file_location("commit_processes",
                                                  CODE_ROOT / "scripts" / "processes.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return bool(module.pass_in_flight())


def commit(text: str, paths: list[str]) -> int:
    base = root()
    why = refused(paths, base)
    if why:
        print(f"[commit] refused: {why}")
        return 2
    if os.environ.get("QA_CREW_DEPT") and pass_in_flight():
        # A worker's commit landing between the pass's review and its push would go out
        # unreviewed (C8 review). The pass has the tree; the work waits for the next run.
        print("[commit] refused: a deep pass is running")
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
                why = _add(base, paths)
                if why:
                    print(f"[commit] git add failed: {why[:300]}")
                    return 1
                done = _git(base, "commit", "-m", message(text), "--", *paths)
                print((done.stdout or done.stderr).strip()[:600])
                if done.returncode == 0:
                    _follow_ups(base)
            except OSError as exc:
                print(f"[commit] git could not be run: {exc}")
                return 1
            return 0 if done.returncode == 0 else 1


MANIFEST = "audits/evidence-manifest.jsonl"
PAGE = "dashboard/index.html"


def _follow_ups(base: Path) -> None:
    """What the hook wrote and, under the marker, left in the tree: the manifest, then the
    page. Left there, each is a dirty tree nobody owns, which prereg refuses (crew-before-c9,
    item 1). The page goes in only when state/ is clean, so it is a render of what is
    committed."""
    _on_its_own(base, MANIFEST, "manifest")
    state = _git(base, "status", "--porcelain", "--", "state/")
    if state.returncode == 0 and not state.stdout.strip():
        _on_its_own(base, PAGE, "render")


def _on_its_own(base: Path, path: str, subject: str) -> None:
    """Commit one file under its own subject, whenever git status names it.

    Added first, always. The state a commit of named paths used to leave -- the index behind
    HEAD, the tree equal to it (MM) -- is one a bare `git commit -- PATH` cannot fix: it ends
    in "nothing to commit" and puts the index back. After the add there is either a change
    to commit or nothing at all, and nothing is not an error here."""
    status = _git(base, "status", "--porcelain", "--", path)
    if status.returncode != 0 or not status.stdout.strip():
        return
    if _git(base, "add", "--", path).returncode != 0:
        print(f"[commit] {path} is changed and could not be added")
        return
    if _git(base, "diff", "--cached", "--quiet", "--", path).returncode != 1:
        return
    done = _git(base, "commit", "-m", message(subject), "--", path)
    print(f"[commit] {subject}: " + ("committed on its own" if done.returncode == 0
                                      else (done.stdout or done.stderr).strip()[:300]))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("-m", "--message", required=True)
    parser.add_argument("paths", nargs="*")
    args = parser.parse_args(argv)
    return commit(args.message, args.paths)


if __name__ == "__main__":
    raise SystemExit(main())
