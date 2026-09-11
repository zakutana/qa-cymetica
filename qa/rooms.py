"""The Nexus rooms: strategies, the operator's notes, and what we sampled.

The operator asked on 2026-09-11 to see what we write to Nexus the way they see
the correspondence on a bug -- a General room, one room per strategy that comes
out of it, their own feedback written into each. docs/nexus-rooms-plan.md is
the plan; this module is where that record lives.

Two append-only files under state/, both gitignored for the reason
state/nexus.jsonl is:

  rooms.jsonl    strategies, links, the operator's notes, ours, read marks
  samples.jsonl  what the console's sampler read from their API

Both are written while a sweep may be running -- a note typed into the console,
a sample on a timer -- and a tree that is dirty during a run is a tree no run
can reach level V from. Neither is in the dashboard's payload, for the same
reason one step removed: anything in the payload rewrites dashboard/index.html.
The console serves them at /rooms.json instead.

This half READS. The writers arrive with the endpoint that needs them, and they
are two on purpose: the browser may write an operator's note and nothing else,
and nothing the browser can reach writes ours.

"Read" is never stored on a note. It is derived from `read` marks, each written
by the reader through the last note it printed -- so a note that lands while
the reader is printing stays unread instead of being swallowed.
"""

from __future__ import annotations

import json
from pathlib import Path

from qa.state import state_dir

GENERAL = "general"


def path() -> Path:
    return state_dir() / "rooms.jsonl"


def samples_path() -> Path:
    return state_dir() / "samples.jsonl"


def _rows(target: Path) -> list[dict]:
    if not target.is_file():
        return []
    out = []
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            # A half-written line is normal while another process appends.
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def load() -> list[dict]:
    return _rows(path())


def load_samples() -> list[dict]:
    return _rows(samples_path())


def number(note_id) -> int:
    """N-0007 -> 7. Anything else is 0, which no mark can reach."""
    try:
        return int(str(note_id).split("-", 1)[1])
    except (IndexError, ValueError):
        return 0


def read_marks(rows: list[dict]) -> dict[str, int]:
    """Per room, the highest note number a `read` mark reaches."""
    marks: dict[str, int] = {}
    for row in rows:
        if row.get("type") == "read":
            room = row.get("room") or GENERAL
            marks[room] = max(marks.get(room, 0), number(row.get("through")))
    return marks


def is_read(note: dict, marks: dict[str, int]) -> bool:
    n = number(note.get("id"))
    return 0 < n <= marks.get(note.get("room") or GENERAL, 0)


def unread(rows: list[dict]) -> list[dict]:
    """The operator's notes no reader has printed yet, oldest first."""
    marks = read_marks(rows)
    return [r for r in rows
            if r.get("type") == "operator_note" and not is_read(r, marks)]
