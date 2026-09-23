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
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa import keepset  # noqa: E402
from qa.state import state_dir  # noqa: E402

# What has no copy anywhere else. Each is outside git because it is appended to
# while a run is in flight, and a dirty tree costs a level-V run.
DIARIES = ("rooms.jsonl", "nexus.jsonl", "paper.jsonl", "lab.jsonl",
           # His answers through the sync door, while the deep lane is full.
           "nexus_shallow.jsonl",
           # The register of what the laboratory has already asked their
           # backtest. It is the memory the whole search stands on, so of all
           # of these it is the one that must not live on a single disk.
           "backtests.jsonl",
           # FOMO Radar's hot signals and their return-since-signal --
           # scripts/fomo_watch.py, added 2026-09-13.
           "fomo_signals.jsonl",
           # Every paper clone, transfer and pause (scripts/clone.py). In git
           # until 2026-09-23, written mid-tick; `release` let go of it.
           "clones.jsonl")
def snapshot_dir() -> Path:
    """Beside the state it archives, not beside the repository.

    `REPO_ROOT / "audits" / "lab"` for the real state dir, because that is its
    parent -- and under QA_STATE_DIR for anything else. Computed per call, not
    at import: as a constant it archived whatever state a test was pointing at
    INTO the repository, and one suite run overwrote the committed archive with
    a tmp_path's empty diaries. Found the hour the first caller was added.
    """
    return state_dir().parent / "audits" / "lab"


def snapshot() -> list[str]:
    """Copy the diaries into audits/, where git can hold them."""
    target = snapshot_dir()
    target.mkdir(parents=True, exist_ok=True)
    copied = []
    # And every department's diaries, found by its shape (plan v2, V9).
    from qa import departments

    found = [p.name for paths in departments.diaries().values() for p in paths]
    for name in dict.fromkeys([*DIARIES, *found]):
        source = state_dir() / name
        if not source.is_file():
            continue
        shutil.copyfile(source, target / name)
        copied.append(name)
    return copied


def _archive(month: str, release: bool) -> int:
    """Bundle, verify, and only then let go. Dry about the last step by default.

    The order is the safety property: a bundle is read back off disk and every
    member hashed against its own name before a single original is released.
    Reversed, a truncated write would take the evidence with it -- and every
    verdict we have sent says these are "provided on request".
    """
    from qa import archive, manifest

    try:
        target = archive.archive_path(month)
    except ValueError as exc:
        raise SystemExit(f"keep: {exc}")

    known = manifest.read()
    stamp = target.name.split(".")[0]
    # EVERYTHING this month's bundle should hold, not just what is new. A tar
    # cannot be appended to, so a rebuild has to be complete or it is a
    # deletion: `pending` alone rewrote the file with the new ids and dropped
    # the rest, while the manifest went on stamping them as archived.
    already = [key for key, row in known.items()
               if (row or {}).get("archive") == stamp]
    ids = sorted(set(archive.pending(known)) | set(already))
    if not ids:
        print("keep: nothing pending; every capture the manifest knows is "
              "already in an archive")
        return _release(month, known) if release else 0

    written, missing = archive.build(ids, target, carry=target)
    good, bad = archive.verify(archive.staged(target), set(ids))
    kept = archive.commit(target, releasable=archive.releasable(good, bad))
    size = target.stat().st_size / 1048576 if target.is_file() else 0.0
    print(f"keep: {written} body(ies) into {target.name}, {size:.1f} MB; "
          f"{len(good)} verified, {len(bad)} BAD, {len(missing)} nowhere"
          + ("" if kept else " — the bundle already there was KEPT"))
    if len(already) and written:
        print(f"   {len(already)} carried forward from the existing bundle")
    if missing:
        print(f"   not on disk: {', '.join(m[:12] for m in missing[:5])}"
              + (" ..." if len(missing) > 5 else ""))

    if not archive.releasable(good, bad):
        print("   nothing released: " + (
            "a member did not hash to its own name, so the whole bundle is "
            f"untrusted ({', '.join(b[:12] for b in bad[:5])})" if bad
            else "the bundle holds nothing"))
        return 1

    stamp = target.name.split(".")[0]
    manifest.write(manifest.merge(
        known, {i: {**known.get(i, {"id": i}), "archive": stamp}
                for i in good}))
    print(f"   manifest stamped: {len(good)} now in {stamp}")

    if not release:
        print("   originals left in git (--release to let go of them)")
        return 0
    return _release(month, manifest.read())


def _release(month: str, known: dict) -> int:
    """Let git go of bodies this month's archive demonstrably holds.

    Separate and re-runnable, because bundling and releasing are different
    decisions and the second one has to be repeatable: the first real run
    archived 1 178 captures and released none, and a release driven by "what
    was pending" would then have had nothing left to act on for ever.

    It re-verifies the archive rather than trusting the manifest's stamp. The
    stamp says we once believed it; the check says the bundle on this disk
    still holds what it claims, and that belief is what the vendor's "provided
    on request" rests on.
    """
    from qa import archive

    target = archive.archive_path(month)
    if not target.is_file():
        raise SystemExit(f"keep: {target.name} is not here; nothing released")

    stamp = target.name.split(".")[0]
    claimed = {key for key, row in known.items()
               if (row or {}).get("archive") == stamp}
    tracked = keepset.tracked_evidence()
    if tracked is None:
        raise SystemExit("keep: git could not list evidence/; nothing released")

    good, bad = archive.verify(target, claimed)
    if not archive.releasable(good, bad):
        print(f"keep: {target.name} did not verify ({len(bad)} bad); "
              f"nothing released")
        return 1

    holds = set(good)
    rel = sorted(tracked & claimed & holds)
    unproved = sorted(tracked - holds)
    print(f"keep: {target.name} verified, {len(good)} member(s); "
          f"{len(rel)} tracked body(ies) to release")
    if unproved:
        print(f"   {len(unproved)} tracked capture(s) this archive does NOT "
              f"hold are left alone: {', '.join(u[:12] for u in unproved[:5])}")
    if not rel:
        print("   nothing to release")
        return 0

    dropped = 0
    for start in range(0, len(rel), keepset.GIT_BATCH):
        chunk = [str(keepset.evidence_path(i).relative_to(REPO_ROOT))
                 .replace("\\", "/") for i in rel[start:start + keepset.GIT_BATCH]]
        done = subprocess.run(["git", "rm", "--cached", "--quiet", *chunk],
                              cwd=REPO_ROOT, capture_output=True, text=True)
        if done.returncode == 0:
            dropped += len(chunk)
        else:
            print(f"   WARNING could not release {len(chunk)}: "
                  f"{done.stderr.strip()[:160]}")
    print(f"   released {dropped} original(s) from git; the bodies stay on disk")
    return 0


def release(name: str) -> int:
    """Let git go of one diary that has moved outside it: `git rm --cached`,
    the file itself untouched on disk.

    protect_state refuses a shell `git rm` aimed under state/, correctly --
    so this names only a file in DIARIES, and only once .gitignore already
    ignores it, and refuses anything else before git is asked a thing.
    """
    if name not in DIARIES:
        raise SystemExit(f"keep: {name!r} is not a diary this script copies "
                         f"into audits/lab/ ({', '.join(DIARIES)}); not a diary "
                         f"to release")
    rel = f"state/{name}"
    # --no-index: a file git still tracks is never "ignored" otherwise.
    if subprocess.run(["git", "check-ignore", "-q", "--no-index", rel],
                      cwd=REPO_ROOT).returncode != 0:
        raise SystemExit(f"keep: {rel} is not gitignored yet -- ignore it "
                         f"first, or git would stage it again")
    done = subprocess.run(["git", "rm", "--cached", "--quiet",
                           "--ignore-unmatch", rel], cwd=REPO_ROOT,
                          capture_output=True, text=True)
    if done.returncode != 0:
        raise SystemExit(f"keep: git rm --cached {rel}: "
                         f"{done.stderr.strip()[:200]}")
    print(f"keep: git let go of {rel}; the file stays on disk")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    track_cmd = sub.add_parser("track", help="add the captures that must survive")
    track_cmd.add_argument("--quiet", action="store_true",
                           help="say nothing unless something goes wrong")
    drop_cmd = sub.add_parser(
        "untrack", help="let go of tracked captures nothing cites any more")
    drop_cmd.add_argument("--quiet", action="store_true")
    sub.add_parser("snapshot", help="copy the diaries into audits/lab/")
    rel_cmd = sub.add_parser(
        "release", help="let git go of a diary that has moved outside it")
    rel_cmd.add_argument("name", help="a file in DIARIES, e.g. clones.jsonl")
    arch = sub.add_parser(
        "archive", help="bundle the capture bodies, verified, into archive/")
    arch.add_argument("--month", required=True, help="YYYY-MM")
    arch.add_argument("--release", action="store_true",
                      help="after verifying, let git go of the originals")
    args = parser.parse_args(argv)

    if args.cmd == "track":
        keepset.track(quiet=args.quiet)
        return 0

    if args.cmd == "untrack":
        keepset.untrack(quiet=args.quiet)
        return 0

    if args.cmd == "archive":
        return _archive(args.month, args.release)

    if args.cmd == "release":
        return release(args.name)

    target = snapshot_dir()
    copied = snapshot()
    try:
        where = target.relative_to(REPO_ROOT).as_posix()
    except ValueError:          # a state dir outside the repo: say where it went
        where = str(target)
    print(f"keep: copied {len(copied)} diary file(s) into {where}"
          + (f": {', '.join(copied)}" if copied else " (none on disk yet)"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
