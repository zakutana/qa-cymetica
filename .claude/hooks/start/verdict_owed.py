"""SessionStart: one line when a Build it Better ticket of ours has shipped and has no verdict from us.

One read of their public board, three seconds at most; a failed read prints nothing. It never fails a session.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BOARD = "/api/v1/build-it-better/requests"
TIMEOUT = 3.0


def ours(rows: list[dict]) -> tuple[set, set]:
    """(the tickets we filed or acted on, those we already sent an accepted verdict on), from state/bb.jsonl."""
    tickets, judged = set(), set()
    for row in rows:
        ticket = row.get("ticket")
        if row.get("type") != "outcome" or not ticket:
            continue
        tickets.add(ticket)
        if row.get("kind") == "verdict" and row.get("outcome") == "accepted":
            judged.add(ticket)
    return tickets, judged


def owed(items: list[dict], rows: list[dict]) -> list[str]:
    """Ours, shipped, and neither we nor their record holds a verdict."""
    tickets, judged = ours(rows)
    return [i.get("ticket") for i in items if isinstance(i, dict) and i.get("ticket") in tickets
            and i.get("ticket") not in judged and i.get("stage") == "shipped" and not i.get("verdict")]


def _rows() -> list[dict]:
    from qa.paths import state_dir

    path = state_dir() / "bb.jsonl"
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            out.append(json.loads(line))
        except ValueError:
            continue
    return out


def _board() -> list[dict]:
    from qa.client import build_client
    from qa.config import identities
    from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier

    client = build_client(identities()["anon"], EndpointRegistry.load(), timeout=TIMEOUT)
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
    rows = _rows()
    if not rows:
        return []
    due = owed(_board(), rows)
    return [f"Shipped, verdict owed: {', '.join(due)} -- python scripts/bb.py get <ticket>"] if due else []


if __name__ == "__main__":
    try:
        print("\n".join(lines()))
    except Exception:  # noqa: BLE001
        pass
