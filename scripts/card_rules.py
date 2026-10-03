"""Judge the two card rules of 2026-10-03 on the settled cards created after them.

    python scripts/card_rules.py          read the listing now and print each rule's verdict

The rules, the date and the criterion are in qa/card_rules.py and were fixed before any card they judge had
settled. This reads `GET /api/v1/event-cards?status=settled` newest first, through the guarded client, until a
page reaches cards older than the rules, and prints what qa.card_rules.evaluate says. SAFE, GETs only, nothing
written: run it again on any later day and the window simply holds more cards.
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa import card_rules as cr  # noqa: E402
from qa.client import build_client, install_client_guard  # noqa: E402
from qa.config import identities, load_dotenv  # noqa: E402
from qa.console import printable  # noqa: E402
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier  # noqa: E402

LISTING = "/api/v1/event-cards"
PAGE = 200
MAX_PAGES = 400


def read_since(client) -> tuple[list[dict], str | None]:
    """Settled cards from newest back to FROM; the second value says why it stopped early, or None."""
    cards: list[dict] = []
    start = cr._at(cr.FROM)
    for page in range(MAX_PAGES):
        response = client.get(LISTING, params={"status": "settled", "limit": PAGE, "offset": page * PAGE})
        if response.status_code != 200:
            return cards, f"page {page} answered HTTP {response.status_code}; a failed read is not an empty window"
        rows = (response.json() or {}).get("cards") or []
        if not rows:
            return cards, None
        cards.extend(rows)
        oldest = min((cr._at(r.get("created_at")) for r in rows if cr._at(r.get("created_at"))), default=None)
        if oldest is not None and oldest < start:
            return cards, None
    return cards, f"stopped after {MAX_PAGES} pages without reaching {cr.FROM}"


def main() -> int:
    printable()
    load_dotenv()
    install_client_guard()
    client = build_client(identities()["anon"], EndpointRegistry.load(), timeout=60.0)
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        cards, why = read_since(client)
    finally:
        CURRENT_TIER.reset(token)
        client.close()
    print(f"rules fixed 2026-10-03, judged on cards created from {cr.FROM}; pass needs n >= {cr.MIN_CARDS} "
          f"and the lower 95 % bound above zero; paper has no costs, so a pass is an upper bound")
    if why:
        print(f"READ INCOMPLETE: {why}")
    for name, row in cr.evaluate(cards).items():
        if row["n"]:
            print(f"  {name:18} {row['verdict']:<13} n={row['n']:<5} mean {row['mean_pct']:+.2f}% "
                  f"[{row['low_pct']:+.2f}, {row['high_pct']:+.2f}] median {row['median_pct']:+.2f}% "
                  f"win {row['win_share'] * 100:.0f}%  unread {row['unread']}")
        else:
            print(f"  {name:18} {row['verdict']:<13} n=0  unread {row['unread']}  ({row['what']})")
    return 1 if why else 0


if __name__ == "__main__":
    raise SystemExit(main())
