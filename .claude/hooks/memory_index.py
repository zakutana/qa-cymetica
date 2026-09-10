"""One line at session start: how many memories there are and how to read one.

`MEMORY.md` is auto-loaded, so a session knows the memories exist. Until
2026-09-10 nothing told it to open one, and none ever did -- the operator
found that out by asking. The fix cannot be another paragraph in a file: a
line in auto-loaded context is what makes a thing real to a fresh session,
and it must be an index rather than content, or it is the same context waste
as pasting every memory in.

Silent when the directory is absent, and never fails: a hook that can break a
session start is worse than no hook.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent


def main() -> int:
    try:
        import importlib.util

        spec = importlib.util.spec_from_file_location(
            "memories_for_hook", REPO_ROOT / "scripts" / "memories.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        memories = module.load()
        if not memories:
            return 0
        classes = "|".join(module.CLASSES)
        print(f"memory: {len(memories)} files. Before substantive work read the "
              f"ones for this task: python scripts/memories.py --for "
              f"<{classes}>")
    except Exception:  # noqa: BLE001
        return 0
    return 0


if __name__ == "__main__":
    sys.exit(main())
