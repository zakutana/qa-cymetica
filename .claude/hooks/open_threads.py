"""SessionStart: one line naming the telegram threads nobody has answered.

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

It never fails a session. Any error at all -- no journal, a half-written line,
a missing scripts/correspond.py -- exits 0 with nothing printed. A note about
correspondence must not be able to stop the work.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LIMIT = 10


def _threads() -> list[dict]:
    """Delegate to scripts/correspond.py: one reader, not two that can drift."""
    spec = importlib.util.spec_from_file_location(
        "correspond_hook", REPO_ROOT / "scripts" / "correspond.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    from qa.state import read_events

    return module.open_threads(read_events())


def main() -> int:
    try:
        unanswered = _threads()
        if not unanswered:
            return 0

        marks = []
        for thread in unanswered[:LIMIT]:
            via = thread["sent"].get("via")
            marks.append(f"{thread['msg_id']} ({via})" if via else thread["msg_id"])
        if len(unanswered) > LIMIT:
            marks.append(f"+{len(unanswered) - LIMIT} more")

        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
        print(f"Telegram, sent by the operator and unanswered: {', '.join(marks)}"
              f" -- text with: python scripts/correspond.py show <id>")
    except Exception:
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
