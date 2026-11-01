"""SessionStart: what is next, what is open, what a ticket is waiting for, and the memories, a few lines at most.

Each source lives in `start/` and is still runnable on its own. One that fails costs its own line only, and
this never fails a session: anything that goes wrong prints nothing.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent / "start"
# The order they are printed in, and the source of each.
SOURCES = (("next_step", "summary"), ("verdict_owed", "lines"), ("open_threads", "lines"), ("memory_index", "lines"))


def _part(name: str):
    spec = importlib.util.spec_from_file_location(f"start_{name}", HERE / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def gather() -> list[str]:
    said: list[str] = []
    for module, function in SOURCES:
        try:
            said.extend(str(line) for line in getattr(_part(module), function)() or [] if str(line).strip())
        except Exception:  # noqa: BLE001 -- a session start never fails
            continue
    return said


def main() -> int:
    try:
        said = gather()
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
