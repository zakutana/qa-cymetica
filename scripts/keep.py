"""Keep what something stands on, and copy what has nowhere else to live.

Two verbs, both idempotent, both safe to run at any moment:

    python scripts/keep.py track      add to git every capture qa/keepset.py
                                      says must survive and git does not have
    python scripts/keep.py snapshot   copy the diaries that live outside git --
                                      the rooms, what Nexus was asked, the
                                      paper orders, the laboratory's notebook --
                                      into audits/lab/, so months of them do
                                      not sit on one disk

`track` runs from three places, and three is the point. `.githooks/pre-commit`
calls it, so a commit that records a new answer brings the capture that answer
cites with it. `scripts/ledger.py` calls it after a fold, which is when a row
starts standing on a new run. The deep pass calls it in step 0, which repairs a
commit made on a machine without the hook -- `core.hooksPath` lives in
`.git/config` and a fresh clone does not have it.

The guard (tests/repo/test_evidence_in_git.py) reads HEAD rather than the
working tree, so the console's fifteen-minute poll cannot make it red. That
holds only while whatever commits the state also commits what the state cites,
which is what this script is for.

The work itself is `qa.keepset.track`, not here: the fold imports it too, and
two copies of that walk would be free to disagree about what "cited" means.
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa import keepset  # noqa: E402
from qa.state import state_dir  # noqa: E402

# What has no copy anywhere else. Each is outside git because it is appended to
# while a run is in flight, and a dirty tree costs a level-V run.
DIARIES = ("rooms.jsonl", "nexus.jsonl", "paper.jsonl", "lab.jsonl")
SNAPSHOT_DIR = REPO_ROOT / "audits" / "lab"


def snapshot() -> list[str]:
    """Copy the diaries into audits/, where git can hold them."""
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    copied = []
    for name in DIARIES:
        source = state_dir() / name
        if not source.is_file():
            continue
        shutil.copyfile(source, SNAPSHOT_DIR / name)
        copied.append(name)
    return copied


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    track_cmd = sub.add_parser("track", help="add the captures that must survive")
    track_cmd.add_argument("--quiet", action="store_true",
                           help="say nothing unless something goes wrong")
    sub.add_parser("snapshot", help="copy the diaries into audits/lab/")
    args = parser.parse_args(argv)

    if args.cmd == "track":
        keepset.track(quiet=args.quiet)
        return 0

    copied = snapshot()
    print(f"keep: copied {len(copied)} diary file(s) into "
          f"{SNAPSHOT_DIR.relative_to(REPO_ROOT).as_posix()}"
          + (f": {', '.join(copied)}" if copied else " (none on disk yet)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
