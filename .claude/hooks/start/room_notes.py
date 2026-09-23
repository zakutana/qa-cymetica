"""SessionStart: one line saying the operator has written in the Nexus rooms.

Counts, by room. Never the notes -- those are read with
`python scripts/rooms.py unread`, which prints them in full and marks them
read. The shape is open_threads.py's, for the same two reasons: a session cannot
read a record it does not know exists, and it must not be handed text nobody
asked for (memory: a-mechanism-the-operator-must-run-is-not-a-mechanism).

Nothing at all when nothing is waiting, and it never fails a session: any error
exits 0 in silence. A note about notes must not be able to stop the work.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]


def lines() -> list[str]:
    """What the session start prints, one line or none."""
    sys.path.insert(0, str(REPO_ROOT))
    from qa import rooms

    waiting = rooms.unread(rooms.load())
    if not waiting:
        return []
    by_room: dict[str, int] = {}
    for note in waiting:
        room = note.get("room") or rooms.GENERAL
        by_room[room] = by_room.get(room, 0) + 1
    counts = ", ".join(f"{room}: {n}" for room, n in sorted(by_room.items()))
    return [f"Rooms: {len(waiting)} note(s) from the operator unread ({counts})"
            f" -- read them with: python scripts/rooms.py unread"]


def main() -> int:
    try:
        said = lines()
        if not said:
            return 0
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
        print("\n".join(said))
    except Exception:  # noqa: BLE001
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
