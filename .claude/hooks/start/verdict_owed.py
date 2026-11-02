"""SessionStart: one line when a Build it Better ticket of ours has shipped and is waiting for our verdict.

Ours is what state/bb.jsonl acted on and what NEXT.md names, since a ticket filed on their form has no row. One read of
their public board, three seconds per phase and not through the shared brake, which can sleep for minutes; a failed
read prints nothing. It never fails a session.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BOARD = "/api/v1/build-it-better/requests"
TIMEOUT = 3.0
TICKET = re.compile(r"\bET-\d+\b")


def ours(rows: list[dict], named=()) -> tuple[set, dict]:
    """(our tickets, ticket -> when our last accepted verdict went), from state/bb.jsonl and NEXT.md's tickets."""
    tickets, judged = set(named), {}
    for row in rows:
        ticket = row.get("ticket")
        if row.get("type") != "outcome" or not ticket:
            continue
        tickets.add(ticket)
        if row.get("kind") == "verdict" and row.get("outcome") == "accepted":
            judged[ticket] = str(row.get("at") or "")
    return tickets, judged


def owed(items: list[dict], rows: list[dict], named=()) -> list[str]:
    """Ours and shipped, with no verdict yet; or re-shipped since our fail, which the board keeps showing through
    the rework. A verdict given on their form has no time here, so it counts as judged."""
    tickets, judged = ours(rows, named)
    out = []
    for item in items:
        ticket = item.get("ticket") if isinstance(item, dict) else None
        if ticket not in tickets or item.get("stage") != "shipped":
            continue
        ours_at = judged.get(ticket)
        if ours_at is None:
            if not item.get("verdict"):
                out.append(ticket)
        elif item.get("verdict") != "pass" and str(item.get("resolved_at") or "") > ours_at:
            out.append(ticket)
    return out


def _next_tickets() -> set:
    path = Path(os.environ.get("QA_NEXT_FILE") or (REPO_ROOT / "NEXT.md"))
    return set(TICKET.findall(path.read_text(encoding="utf-8"))) if path.is_file() else set()


def _board() -> list[dict]:
    import httpx

    from qa.client import build_client
    from qa.config import identities
    from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier

    client = build_client(identities()["anon"], EndpointRegistry.load(), timeout=TIMEOUT,
                          inner=httpx.HTTPTransport(retries=0))
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        response = client.get(BOARD)
    finally:
        CURRENT_TIER.reset(token)
        client.close()
    if response.status_code != 200:
        return []
    return (response.json() or {}).get("items") or []


def lines() -> list[str]:
    sys.path.insert(0, str(REPO_ROOT))
    from qa.paths import read_events, state_dir

    rows, named = read_events(state_dir() / "bb.jsonl"), _next_tickets()
    if not rows and not named:
        return []
    due = owed(_board(), rows, named)
    return [f"Shipped, verdict owed: {', '.join(due)} -- python scripts/bb.py get <ticket>"] if due else []


if __name__ == "__main__":
    try:
        print("\n".join(lines()))
    except Exception:  # noqa: BLE001
        pass
