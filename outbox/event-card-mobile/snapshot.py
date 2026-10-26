"""Write event-data.json (this folder): the cards the mockup draws, their last day of index, and how every live card falls
into the heat tiers, read from Cymetica's public API.

GET only: /api/v1/event-cards/?limit=200&offset=N (every live card, page by page; the first 50 are the deck /events
loads) and /api/v1/event-cards/{id}/index-history?interval=1d (each drawn card's chart).

The heat tier is the news sentiment's strength, |headline_sentiment_score|: HOT from 0.7, WARM from 0.3, QUIET below.
(The impact score his first design graded by is gone: set on 30 of 647 live cards on 2026-10-26, none created after
2026-09-12, so the tier cannot use it.) The colour is its sign: positive green, negative red, zero neither.
"""
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
API = "https://cymetica.com/api/v1/event-cards"
# one card of each tier from the deck, the operator's ESTC card in the middle
SHOW = ["5abd6efc", "9b46ad13", "bd6678c4"]
HOT, WARM = 0.7, 0.3


def get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "qa-cymetica mockup snapshot"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8"))


def tier(c):
    s = abs(c.get("headline_sentiment_score") or 0)
    return "hot" if s >= HOT else ("warm" if s >= WARM else "quiet")


cards, offset = [], 0
while True:
    page = get(f"{API}/?limit=200&offset={offset}")
    cards += page["cards"]
    offset += 200
    if offset >= page.get("total", 0) or not page["cards"]:
        break
show = []
for short in SHOW:
    c = next((c for c in cards if c["id"].startswith(short)), None)
    if c is None:
        sys.exit(f"card {short} is not live any more")
    show.append({**c, "tier": tier(c), "hist": get(f'{API}/{c["id"]}/index-history?interval=1d')})
counts = {t: sum(1 for c in cards if tier(c) == t) for t in ("hot", "warm", "quiet")}
out = {"read_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "live_cards": len(cards), "deck_size": min(50, len(cards)),
       "tiers": counts, "thresholds": {"hot": HOT, "warm": WARM}, "cards": show,
       "impact_scored": sum(1 for c in cards if c.get("headline_impact_score") is not None)}
(HERE / "event-data.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("event-data.json:", out["read_at"], "| live", len(cards), "| tiers", counts, "| impact scored", out["impact_scored"],
      "| drawn", [(c["id"][:8], c["tier"], c["headline_sentiment_score"]) for c in show])
