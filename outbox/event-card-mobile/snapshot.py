"""Write event-data.json (this folder): the cards the mockup draws, their last day of index, and how every live card falls
into the tiers, read from Cymetica's public API.

GET only: /api/v1/event-cards/?limit=200&offset=N (every live card, page by page; the first 50 are the deck /events
loads) and /api/v1/event-cards/{id}/index-history?interval=1d (each drawn card's chart).

The tier is the impact score, headline_impact_score (0-10, how big the news is): HOT from 8, WARM from 6.5, QUIET below --
his own design graded Legendary 9.0, Rare 7.0, Common 4.0. Cymetica, 2026-10-26 (REPLY-0222 to MSG-0251): news cards are
scored, M&A-ripple cards are being scored now, index-basket cards have no headline and are never scored, and a null
sentiment or impact means "not scored" (0.00 means scored neutral). So a card with no impact score is NOT SCORED YET, and a
card with no source headline is an INDEX BASKET.
"""
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
API = "https://cymetica.com/api/v1/event-cards"
# one card of each kind: HOT, WARM (the operator's ESTC card), QUIET, a ripple card not scored yet, an index basket
SHOW = ["082f75e0", "9b46ad13", "46320d35", "5abd6efc", "f701f397"]
HOT, WARM = 8.0, 6.5


def get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "qa-cymetica mockup snapshot"})
    with urllib.request.urlopen(req, timeout=40) as r:
        return json.loads(r.read().decode("utf-8"))


def tier(c):
    if not c.get("source_url"):
        return "basket"
    i = c.get("headline_impact_score")
    if i is None:
        return "unscored"
    return "hot" if i >= HOT else ("warm" if i >= WARM else "quiet")


cards, offset = [], 0
while True:
    page = get(f"{API}/?limit=200&offset={offset}")
    cards += page["cards"]
    offset += 200
    if offset >= page.get("total", 0) or not page["cards"]:
        break
show = []
for key in SHOW:
    c = next((c for c in cards if c["id"].startswith(key) or c["title"] == key), None)
    if c is None:
        sys.exit(f"card {key} is not live any more")
    show.append({**c, "tier": tier(c), "hist": get(f'{API}/{c["id"]}/index-history?interval=1d')})
counts = {t: sum(1 for c in cards if tier(c) == t) for t in ("hot", "warm", "quiet", "unscored", "basket")}
out = {"read_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "live_cards": len(cards), "deck_size": min(50, len(cards)),
       "tiers": counts, "deck_tiers": {t: sum(1 for c in cards[:50] if tier(c) == t) for t in counts},
       "thresholds": {"hot": HOT, "warm": WARM}, "cards": show}
(HERE / "event-data.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("event-data.json:", out["read_at"], "| live", len(cards), "| tiers", counts, "| first 50", out["deck_tiers"],
      "| drawn", [(c["id"][:8], c["tier"], c.get("headline_impact_score"), c.get("headline_sentiment_score"), len(c["hist"].get("points", []))) for c in show])
