"""The monthly bundle the capture bodies move into, and the check before the move.

D2 of docs/data-plan.md. `qa/manifest.py` keeps the proof; this keeps the thing
itself. The ordering is the entire safety property and it is worth saying once
in full:

    build the bundle -> read it back off disk -> hash every member against its
    own name -> only then let go of the originals.

Evidence is addressed by the sha256 of its content, so hashing a member against
its name is the integrity check. Comparing the tar to the bytes still in memory
would prove only that memory agrees with itself.

`.tar.xz`, not the `.tar.zst` the plan named: lzma is in the standard library
and measured the same ratio on this store (9:1, 167 MB -> ~18 MB). An archive
whose whole job is to open when somebody finally asks should not need a package
to be installed first.
"""

from __future__ import annotations

import io
import json
import os
import re
import tarfile
from pathlib import Path

from qa.evidence import content_id
from qa.keepset import evidence_path
from qa.state import file_lock, state_dir

MONTH = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")


def archive_path(month: str, root: Path | None = None) -> Path:
    """`archive/evidence-YYYY-MM.tar.xz`, beside the state it came from.

    A month that is not a month raises rather than naming a file nothing will
    ever look for again. Beside the state rather than fixed at import, for the
    reason `keep.snapshot_dir` records: a constant computed at import once let
    a passing test write over the repository's own archive.
    """
    if not MONTH.match(str(month or "")):
        raise ValueError(f"{month!r} is not a month: use YYYY-MM")
    base = Path(root) if root is not None else state_dir().parent
    return base / "archive" / f"evidence-{month}.tar.xz"


def pending(known: dict[str, dict]) -> list[str]:
    """Manifest entries not yet in any archive. Pure."""
    return sorted(key for key, row in known.items()
                  if not (row or {}).get("archive"))


def _id_of(raw: bytes) -> str | None:
    """The evidence id a stored body should carry, recomputed the ONE way.

    Through `qa.evidence.content_id`, never a second sha256 here: the id is
    taken over the record minus its volatile fields, while the file on disk is
    indented and keeps them. A verifier that hashed the file bytes condemned
    every capture in the store the first time it ran.
    """
    try:
        record = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        return None
    if not isinstance(record, dict):
        return None
    return content_id(record)


def staged(path: Path) -> Path:
    """Where a bundle is written before it has earned the real name."""
    return path.with_name(path.name + ".new")


def running(path: Path):
    """One run per month: the lock held from build to the manifest's stamp.

    Every run of a month writes the same staged file, so a second run truncates
    the first one's bundle under its verify (2026-10-25, two sessions obeying
    one reminder). Asked once and never waited for: a run takes minutes, and a
    caller queued behind it would rebuild what it has just bundled. OSError
    when another run holds it.
    """
    return file_lock(path, poll=0.05, timeout=0)


def members(path: Path) -> set[str]:
    """The ids a bundle holds, by name. Cheap: no hashing, no extraction."""
    if not Path(path).is_file():
        return set()
    with tarfile.open(path, "r:xz") as bundle:
        return {Path(m.name).name[:-5] if m.name.endswith(".json")
                else Path(m.name).name
                for m in bundle.getmembers() if m.isfile()}


def build(ids, path: Path, root: Path | None = None,
          carry: Path | None = None) -> tuple[int, list[str]]:
    """Write the bundle BESIDE the real one. Returns (written, missing).

    Never over the top of it. `tarfile` truncates and xz cannot append, so
    writing straight to the target meant a second run in the same month
    rebuilt it from whatever happened to be pending and dropped everything the
    first run had put there -- while the manifest went on stamping the lost
    ones as archived. Three independent reviewers reproduced that on
    2026-09-12; `commit()` is the other half of the fix.

    `carry` names an existing bundle to take a member from when its body is no
    longer on disk. That case is the archive's whole purpose: once `must_keep`
    stops citing a capture the pruner deletes the body, and rebuilding from
    disk alone would drop exactly the old captures this exists to hold.

    A body in neither place is REPORTED, never quietly skipped: bundling 900 of
    1 178 and reporting success is how an archive comes to be trusted for what
    it does not contain.
    """
    wanted, missing, written = list(ids), [], 0
    held = {}
    if carry is not None and Path(carry).is_file():
        with tarfile.open(carry, "r:xz") as old:
            for member in old.getmembers():
                if not member.isfile():
                    continue
                name = Path(member.name).name
                held[name[:-5] if name.endswith(".json") else name] = (
                    member, old.extractfile(member).read())

    target = staged(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(target, "w:xz") as bundle:
        for evidence_id in wanted:
            source = evidence_path(evidence_id, root)
            arcname = f"sha256/{evidence_id[:2]}/{evidence_id}.json"
            if source.is_file():
                bundle.add(source, arcname=arcname)
            elif evidence_id in held:
                member, raw = held[evidence_id]
                info = tarfile.TarInfo(arcname)
                info.size = len(raw)
                info.mtime = member.mtime
                bundle.addfile(info, io.BytesIO(raw))
            else:
                missing.append(evidence_id)
                continue
            written += 1
    return written, missing


def commit(path: Path, releasable: bool) -> bool:
    """Put the staged bundle in place, or throw it away. Never in between.

    The bundle already there is what the vendor's "provided on request" rests
    on, so a write that did not verify must cost nothing at all.
    """
    pending_path = staged(path)
    if not pending_path.is_file():
        return False
    if not releasable:
        pending_path.unlink()
        return False
    os.replace(pending_path, path)
    return True


def verify(path: Path, expected: set[str]) -> tuple[list[str], list[str]]:
    """Read the archive back and hash every member against its own name.

    Returns (good, bad). `good` is what the archive demonstrably holds; `bad` is
    every member whose content does not hash to the name it is filed under. An
    id in `expected` that is in neither list was never put in -- `build` already
    said so -- and that is not corruption.
    """
    good: list[str] = []
    bad: list[str] = []
    with tarfile.open(path, "r:xz") as bundle:
        for member in bundle.getmembers():
            if not member.isfile():
                continue
            name = Path(member.name).name
            evidence_id = name[:-5] if name.endswith(".json") else name
            source = bundle.extractfile(member)
            if source is None:
                bad.append(evidence_id)
                continue
            if _id_of(source.read()) == evidence_id:
                good.append(evidence_id)
            else:
                bad.append(evidence_id)
    return good, bad


def releasable(good: list[str], bad: list[str]) -> bool:
    """Whether the originals may now be let go of.

    One bad member condemns the whole bundle. The archive is a single artefact
    and a partial trust in it is no trust: if lzma or the disk mangled one
    member there is no reason to believe the rest, and the cost of keeping 167
    MB a while longer is nothing beside the cost of finding out later.
    """
    return bool(good) and not bad
