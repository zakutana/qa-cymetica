"""SessionStart: one line when nobody has ticked the Agent Casino for a day. A reminder: they start it."""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
QUIET_HOURS = 24


def quiet(rows: list[dict], now: datetime) -> list[str]:
    ticks = [r.get("at") for r in rows if r.get("type") == "tick" and r.get("at")]
    if not ticks:
        return []
    hours = int((now - datetime.fromisoformat(ticks[-1])).total_seconds() // 3600)
    if hours < QUIET_HOURS:
        return []
    return [f"Agent Casino se netestuje už {hours} h -- řekni: /loop 30m jdi do casina"]


def lines() -> list[str]:
    sys.path.insert(0, str(REPO_ROOT))
    from qa.paths import read_events, state_dir

    return quiet(read_events(state_dir() / "casino.jsonl"), datetime.now(timezone.utc))
