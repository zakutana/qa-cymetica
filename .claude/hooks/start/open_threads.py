"""SessionStart: one line naming the threads nobody has answered.

Ids only. Not the messages, not a summary of them, not the first words -- the
texts stay on disk and are read with `scripts/correspond.py show <id>` when
somebody actually asks about one. The operator's objection on 2026-09-08, and
it decided this file's shape: *"nebude to doufam nacitat vsechny ty telegram
zpravy najednou do contextu? to je zasrani zbytecne contextu."* Right. A
session needs to KNOW a thread is open; it does not need to be handed it.

So the whole output is one line, and there is none at all when nothing is open.

Why a hook rather than leaving it to be looked up when asked: a session cannot
look up a record it does not know exists. That is not hypothetical -- the same
morning, DEEP-PASS.md could not be read after a /clear because nothing in the
auto-loaded context named it, and the fix was one line in CLAUDE.md. This is
that line, computed instead of written.

**Every channel that waits on them, not Telegram alone.** Until 2026-09-20
this read `scripts/correspond.py` directly, so a2a was invisible at session
start for the ten days its threads sat open -- and a2a is the channel a
session is least likely to remember by itself. It now reads `qa/channels.py`,
the one module that knows all four channels and which side each waits on, so
a fifth channel arrives here by itself. The channels waiting on US are not
printed: the rooms have their own hook, and a filed obligation has the
dashboard.

It never fails a session. Any error at all -- no journal, a half-written line,
a missing module -- exits 0 with nothing printed. A note about correspondence
must not be able to stop the work.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
LIMIT = 10

# What to type when a thread turns out to matter, per channel. A line that
# names an id without saying how to read it sends the session to grep.
READ_WITH = {
    "telegram": "python scripts/correspond.py show <id>",
    "a2a": "python scripts/channels.py status",
}


def _open() -> list[tuple[str, list[str]]]:
    """Unanswered ids per channel, for the channels that wait on them.

    Through `qa/channels.py` rather than through each channel's own script:
    one reader, not two that can drift -- which is exactly what happened to
    `unanswered` itself before this was written.
    """
    sys.path.insert(0, str(REPO_ROOT))
    from qa import channels
    from qa.state import read_events

    events = read_events()
    state = channels.state(events)
    named = channels.labels(events)
    out = []
    for name, channel in state.items():
        if channel["waiting_on"] != "them" or not channel["unanswered"]:
            continue
        marks = [f"{i} ({named[i]})" if i in named else str(i)
                 for i in channel["unanswered"]]
        out.append((name, marks))
    return out


def lines() -> list[str]:
    """What the session start prints, one line or none."""
    waiting = _open()
    if not waiting:
        return []
    parts = []
    for name, ids in waiting:
        shown = ids[:LIMIT]
        marks = ", ".join(shown)
        if len(ids) > len(shown):
            marks += f", +{len(ids) - len(shown)} more"
        how = READ_WITH.get(name)
        parts.append(f"{name}: {marks}" + (f" -- {how}" if how else ""))
    return ["Sent by us and unanswered -- " + " | ".join(parts)]


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
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
