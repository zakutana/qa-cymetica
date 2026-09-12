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
"""

from __future__ import annotations

import json
from pathlib import Path

from qa.evidence import call_key
from qa.keepset import evidence_path
from qa.state import state_dir

# The fields a refresh may overwrite with a fresher reading. Everything else is
# written once, while the body is on disk, and never contradicted.
REFRESHABLE = ("why",)


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


def read(path: Path | None = None) -> dict[str, dict]:
    """Every line we have. A half-written line is skipped, never guessed at."""
    target = path or manifest_path()
    out: dict[str, dict] = {}
    try:
        text = target.read_text(encoding="utf-8")
    except OSError:
        return out
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


def write(entries: dict[str, dict], path: Path | None = None) -> int:
    """Sorted by id, one line each, so an unchanged manifest has no diff."""
    target = path or manifest_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(entries[key], ensure_ascii=False, sort_keys=True)
             for key in sorted(entries)]
    target.write_text("\n".join(lines) + ("\n" if lines else ""),
                      encoding="utf-8")
    return len(lines)


def refresh(keep: dict[str, str], root: Path | None = None,
            path: Path | None = None) -> tuple[int, int]:
    """Fold what is on disk now into what the manifest already knows.

    Returns (added, held). `added` counts ids the manifest had never seen, so a
    run that adds nothing is a run where every cited capture was already
    proved -- which is the steady state, not a failure.
    """
    known = read(path)
    fresh = {}
    for evidence_id, why in keep.items():
        row = entry(evidence_id, why, root)
        if row is not None:
            fresh[evidence_id] = row
    merged = merge(known, fresh)
    added = len(set(merged) - set(known))
    write(merged, path)
    return added, len(merged)
