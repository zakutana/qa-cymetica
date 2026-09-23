"""SessionStart: what is due, and the words that start it.

[operator 2026-09-12] refused a scheduler -- they launch every run, as they
have all along, and asked to be reminded instead. This is that reminder, and it
is the whole of the mechanism: a line at the start of a session naming what is
on the table, which CLAUDE.md tells the session to repeat in its first answer,
because hook output is not something they read.

Silent when nothing is due. That is the load-bearing half: they run the deep
pass every evening already, so a line that appears every evening is a line they
stop reading, and the rules in scripts/processes.py are written to fire only
when a night actually went by.

Same shape as the four hooks beside it -- an index, never the content, never a
failure. Any error exits 0 in silence: a note about what is due may not be the
reason a session does not start. It answers from files only; nothing here
reaches the vendor, whose channel is measured by checks that count our
questions.
"""

from __future__ import annotations

import importlib.util
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("QA_REPO_ROOT")
            or Path(__file__).resolve().parents[3])
LIMIT = 4


def lines() -> list[str]:
    """Everything that is due; the session start keeps what fits its slot."""
    source = ROOT / "scripts" / "processes.py"
    if not source.is_file():
        return []
    spec = importlib.util.spec_from_file_location("processes_for_hook", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.reminders(module.facts(), datetime.now(timezone.utc))


def main() -> int:
    try:
        due = lines()
        if not due:
            return 0
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass
        for line in due[:LIMIT]:
            print(line)
        if len(due) > LIMIT:
            print(f"(+{len(due) - LIMIT} dalších: python scripts/processes.py "
                  f"reminders)")
    except Exception:  # noqa: BLE001
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
