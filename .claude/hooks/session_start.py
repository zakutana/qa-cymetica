"""SessionStart: the one hook -- what is due, what the last pass left, the
threads, the notes, the next step and the memories, in at most eight lines.

Plan v2, V7 (E1). There were six hooks, each printing its own block. Four of 24
runs of the reminders hook timed out and printed nothing, because it scanned
their surface over a growing evidence store (3.4 s of 4.3); the drift then
took all four lines the reminders had and crowded out what was due; and
sessions repeated the reminder in two or three of nine starts.

So every source has a fixed SLOT and a source that says more keeps its slot
and says where the rest is; the drift is read from the cache the patrol and
the laboratory tick write; and one source that fails costs its own slot only.
The sources live in `start/`, each still runnable on its own. It never fails
a session: anything that goes wrong prints nothing.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent / "start"
MAX_LINES = 8
# The order they are printed in, and how many lines each may have.
SLOTS = {"due": 3, "handover": 1, "threads": 1, "notes": 1, "next": 1,
         "memory": 1}
MORE = {"due": "python scripts/processes.py reminders",
        "handover": "DEEP-PASS.md", "next": "NEXT.md"}


def compose(parts: dict[str, list[str]]) -> list[str]:
    """Pure: each source's lines into its slot, in slot order."""
    out: list[str] = []
    for name, room in SLOTS.items():
        said = [line for line in parts.get(name) or [] if line.strip()]
        if len(said) > room and room > 1:
            cut = len(said) - (room - 1)
            said = said[:room - 1] + [f"(+{cut} dalších: {MORE.get(name, name)})"]
        out.extend(said[:room])
    return out[:MAX_LINES]


def gather(sources: dict) -> dict[str, list[str]]:
    """Each source's lines; one that raises says nothing and costs only its
    own slot."""
    out: dict[str, list[str]] = {}
    for name, source in sources.items():
        try:
            out[name] = [str(line) for line in source() or []]
        except Exception:  # noqa: BLE001 -- a session start never fails
            out[name] = []
    return out


def _part(name: str):
    spec = importlib.util.spec_from_file_location(f"start_{name}",
                                                  HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _source(module: str, function: str = "lines"):
    return lambda: getattr(_part(module), function)()


def main() -> int:
    try:
        said = compose(gather({
            "due": _source("reminders"),
            "handover": _source("deep_pass_handover"),
            "threads": _source("open_threads"),
            "notes": _source("room_notes"),
            "next": _source("next_step", "summary"),
            "memory": _source("memory_index"),
        }))
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
