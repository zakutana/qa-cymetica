"""How long each real request to their host took, and how it ended.

One line per request that reached the network, into `state/timings.jsonl`
(gitignored: it is written during runs, and a tracked file changing mid-run
costs the run its level V). Written by `SafetyTransport`, read by
`scripts/timeouts.py`. `response.elapsed` cannot serve: httpx sets it only
after the client has closed the response, and the transport is done before.
"""

from __future__ import annotations

import json
import time
from datetime import datetime, timezone

from qa.state import file_lock, state_dir


def path():
    return state_dir() / "timings.jsonl"


def record(request, started: float, tier=None, status: int | None = None,
           error: str | None = None, to: str = "headers") -> None:
    """Append one request's timing. Never raises: a diary that cannot be
    written must not fail the request it describes."""
    from qa.evidence import redact
    from qa.safety import CURRENT_NODEID

    row = {"at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
           "method": request.method, "host": request.url.host,
           "path": redact(request.url.path), "status": status, "error": error,
           "ms": int((time.perf_counter() - started) * 1000), "to": to,
           "tier": getattr(tier, "value", tier), "nodeid": CURRENT_NODEID.get()}
    target = path()
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        with file_lock(target):
            with open(target, "a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    except OSError:
        pass
