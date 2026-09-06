"""Freeze what a run will measure, before it measures anything.

Level V -- the only admissibility level that may verify a fix -- requires a
clean tree and a preregistration tag whose commit is HEAD. None of the 13
committed run records has one, which is why the honest reading of yesterday is
zero verified findings.

That requirement is worth nothing if meeting it is awkward, because then it
gets skipped and the standard quietly becomes whatever was convenient. So this
script makes it one command:

    python scripts/prereg.py new --selector tests --window 30 --tag
    pytest tests --prereg PRE-0001
    python scripts/ledger.py --run <run_id>

It refuses a dirty tree rather than recording one, because a preregistration
made after the code moved is a description, not a commitment.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa.state import state_dir  # noqa: E402

PREREG_DIR_NAME = "preregistrations"


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=REPO_ROOT, capture_output=True,
                          text=True, encoding="utf-8", errors="replace", check=True).stdout.strip()


def prereg_dir() -> Path:
    return state_dir() / PREREG_DIR_NAME


def next_id() -> str:
    existing = sorted(prereg_dir().glob("PRE-*.md")) if prereg_dir().exists() else []
    numbers = [int(m.group(1)) for p in existing
               if (m := re.match(r"PRE-(\d{4})", p.name))]
    return f"PRE-{(max(numbers) + 1 if numbers else 1):04d}"


def tree_is_clean() -> tuple[bool, str]:
    dirty = _git("status", "--porcelain")
    return (not dirty), dirty


def create(selector: str, window: int, tag: bool, note: str | None) -> str:
    clean, dirty = tree_is_clean()
    if not clean:
        raise SystemExit(
            "refusing to preregister against a dirty tree.\n\n"
            "A preregistration made after the code moved is a description of "
            "what happened, not a commitment made in advance -- and the whole "
            "value of the tag is that it was written first. Commit or stash:\n\n"
            + dirty
        )

    prereg_id = next_id()
    head = _git("rev-parse", "HEAD")
    at = datetime.now(timezone.utc).isoformat(timespec="seconds")

    body = f"""# {prereg_id}

    Registered  {at}
    Commit      {head}
    Selector    {selector}
    Window      {window}s

## What this run will measure

Every check the selector `{selector}` collects, run once, against the live
platform at the commit above.

## What counts as a result

The run record this produces. A check that fails opens or holds a finding; a
check that passes under the fingerprint the row last failed under verifies it;
anything else -- skipped, errored, inconclusive -- moves nothing.

## Terminal condition

The run ends when the selector is exhausted, or when the rate-limit budget
stops it. A run stopped early is partial and may not verify anything, which
the run record records as `record_integrity.budget_truncated`.

## Snapshot window

Sources compared with each other must be fetched within {window}s. Outside
that, the comparison is inconclusive rather than a contradiction, because a
difference produced by latency is our artefact, not their defect.

{('## Note\\n\\n' + note) if note else ''}
"""

    prereg_dir().mkdir(parents=True, exist_ok=True)
    path = prereg_dir() / f"{prereg_id}.md"
    path.write_text(body, encoding="utf-8")

    print(f"-> {path}")
    print(f"   commit {head[:12]}  selector {selector!r}  window {window}s")

    if tag:
        # Commit the preregistration first, so the tag it carries points at a
        # commit that contains it. Otherwise the tag names a tree in which the
        # registration does not exist.
        _git("add", str(path))
        subprocess.run(["git", "commit", "-m", f"preregister {prereg_id}: {selector}"],
                       cwd=REPO_ROOT, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
        head = _git("rev-parse", "HEAD")
        subprocess.run(["git", "tag", "-a", f"prereg/{prereg_id}",
                        "-m", f"{prereg_id}: {selector} at {at}"],
                       cwd=REPO_ROOT, check=True, capture_output=True, text=True, encoding="utf-8", errors="replace")
        print(f"   tagged prereg/{prereg_id} -> {head[:12]}")
        print(f"\nNow run:  pytest {selector} --prereg {prereg_id}")
    else:
        print("\nNot tagged (--tag to tag). Without a tag whose commit is HEAD, "
              "the run is level R at best and may not verify anything.")

    return prereg_id


def check(prereg_id: str) -> int:
    """Does this preregistration's tag resolve to the current HEAD?"""
    try:
        tagged = _git("rev-parse", f"prereg/{prereg_id}^{{commit}}")
    except subprocess.CalledProcessError:
        print(f"no tag prereg/{prereg_id}")
        return 1

    head = _git("rev-parse", "HEAD")
    clean, dirty = tree_is_clean()
    ok = tagged == head and clean

    print(f"{prereg_id}: tag {tagged[:12]}  HEAD {head[:12]}  "
          f"tree {'clean' if clean else 'DIRTY'}")
    if not ok:
        print("A run made now would be level R, not V:")
        if tagged != head:
            print("  the tag does not point at HEAD -- commit moved since "
                  "preregistration, so re-register")
        if not clean:
            print(f"  uncommitted changes:\n{dirty}")
    return 0 if ok else 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="prereg.py", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("new", help="freeze a run's configuration")
    p.add_argument("--selector", default="tests")
    p.add_argument("--window", type=int, default=30)
    p.add_argument("--tag", action="store_true",
                   help="commit the registration and tag it (required for level V)")
    p.add_argument("--note", default=None)

    p = sub.add_parser("check", help="would a run now reach level V?")
    p.add_argument("prereg_id")

    args = parser.parse_args(argv)
    if args.command == "new":
        create(args.selector, args.window, args.tag, args.note)
        return 0
    return check(args.prereg_id)


if __name__ == "__main__":
    raise SystemExit(main())
