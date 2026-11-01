"""SessionStart: one line naming the threads nobody has answered.

Ids only. The operator, 2026-09-08: *"nebude to doufam nacitat vsechny ty telegram zpravy najednou do contextu?"*
A session needs to KNOW a thread is open; the texts stay on disk. None at all when nothing is open, and it never
fails a session.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
LIMIT = 10

READ_WITH = {
    "telegram": "python scripts/correspond.py show <id>",
    "a2a": "python scripts/channels.py status",
}


def _open() -> list[tuple[str, list[str]]]:
    """Unanswered ids per channel, for the channels that wait on them."""
    sys.path.insert(0, str(REPO_ROOT))
    from qa import channels
    from qa.paths import read_events

    events = read_events()
    named = channels.labels(events)
    out = []
    for name, channel in channels.state(events).items():
        if channel["waiting_on"] != "them" or not channel["unanswered"]:
            continue
        out.append((name, [f"{i} ({named[i]})" if i in named else str(i) for i in channel["unanswered"]]))
    return out


def lines() -> list[str]:
    """What the session start prints, one line or none."""
    waiting = _open()
    if not waiting:
        return []
    parts = []
    for name, ids in waiting:
        marks = ", ".join(ids[:LIMIT])
        if len(ids) > LIMIT:
            marks += f", +{len(ids) - LIMIT} more"
        how = READ_WITH.get(name)
        parts.append(f"{name}: {marks}" + (f" -- {how}" if how else ""))
    return ["Sent by us and unanswered -- " + " | ".join(parts)]


def main() -> int:
    try:
        said = lines()
        if said:
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
