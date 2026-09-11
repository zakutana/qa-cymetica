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

The writers are two on purpose. The browser may write an operator's note and
nothing else -- add_operator_note, the only one serve.py reaches -- and nothing
the browser can reach writes ours: add_claude_note and mark_read belong to
scripts/rooms.py. tests/meta/test_pipeline_room_notes.py reads the writers out
of this file and holds serve.py to the first.

"Read" is never stored on a note. It is derived from `read` marks, each written
by the reader through the last note it printed -- so a note that lands while
the reader is printing stays unread instead of being swallowed.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from qa.state import file_lock, state_dir

GENERAL = "general"
NOTE_TYPES = ("operator_note", "claude_note")
MAX_TEXT = 4000


class RoomError(ValueError):
    """A write the record refuses -- a room that does not exist, a note that is
    empty or longer than MAX_TEXT. Refused before anything is written."""


def path() -> Path:
    return state_dir() / "rooms.jsonl"


def samples_path() -> Path:
    return state_dir() / "samples.jsonl"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _rows(target: Path) -> list[dict]:
    if not target.is_file():
        return []
    out = []
    # errors="replace": one damaged byte must cost one line, not the whole
    # tab and every reader after it. The line then fails to parse and is
    # skipped like a half-written one.
    for line in target.read_text(encoding="utf-8", errors="replace").splitlines():
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


def known_rooms(rows: list[dict]) -> set[str]:
    """General, and every strategy room that has been opened."""
    return {GENERAL} | {r["id"] for r in rows
                        if r.get("type") == "strategy" and r.get("id")}


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


def _append(build) -> list[dict]:
    """Append what `build` makes of the rows, as one step under the lock.

    `build` sees the rows as they are INSIDE the lock, so an id it derives from
    them cannot be handed to a second writer. Two share this file -- the
    console on the operator's click and the CLI in a session -- and the id is
    what a read mark counts through.
    """
    target = path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(target):
        made = build(_rows(target))
        if made:
            with open(target, "a", encoding="utf-8") as handle:
                for row in made:
                    handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return made


def _next_note_id(rows: list[dict]) -> str:
    used = [number(r.get("id")) for r in rows if r.get("type") in NOTE_TYPES]
    return f"N-{max(used, default=0) + 1:04d}"


def _note(kind: str, room: str, text, **extra):
    def build(rows: list[dict]) -> list[dict]:
        if room not in known_rooms(rows):
            raise RoomError(f"there is no room {room!r}")
        body = str(text or "").strip()
        if not body:
            raise RoomError("an empty note")
        if len(body) > MAX_TEXT:
            raise RoomError(f"a note over {MAX_TEXT} characters")
        return [{"type": kind, "id": _next_note_id(rows), "room": room,
                 "at": _now(), "text": body, **extra}]
    return build


def add_operator_note(room: str, text: str) -> dict:
    """The browser's one write: a note from the operator, into a room that exists."""
    return _append(_note("operator_note", room, text))[0]


def add_claude_note(room: str, text: str, about: str | None = None) -> dict:
    """Ours, from scripts/rooms.py. Never unread: it is not the operator's feedback.

    `about` names the Nexus question it is about -- NEX-0016 -- and the tab
    shows it beside the note.
    """
    return _append(_note("claude_note", room, text,
                         **({"re": about} if about else {})))[0]


def mark_read(through: dict[str, str]) -> list[dict]:
    """One `read` row per room, through the last note the reader printed."""
    def build(rows: list[dict]) -> list[dict]:
        return [{"type": "read", "room": room, "through": note_id, "at": _now()}
                for room, note_id in sorted(through.items())]
    return _append(build) if through else []
