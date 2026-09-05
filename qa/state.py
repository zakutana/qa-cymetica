"""State directory seam.

Phase 0 of the hardening plan: the one place that decides where `state/`
lives, so an inner pytest session (pytester) can be pointed at a temp
directory and never touch the committed state. Everything else in this module
-- run loading, admissibility, the event journal, ledger load/write -- arrives
in phase 2.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def state_dir() -> Path:
    """`QA_STATE_DIR` if set, else `<repo>/state`."""
    override = os.environ.get("QA_STATE_DIR")
    return Path(override) if override else REPO_ROOT / "state"
