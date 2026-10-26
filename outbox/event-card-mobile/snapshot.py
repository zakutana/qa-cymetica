"""Write event-data.json (this folder): the card the mockup draws and its last day of index, read from Cymetica's public API.

GET only: /api/v1/event-cards/ (the deck /events loads) and /api/v1/event-cards/{id}/index-history?interval=1d (the chart).
"""
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
CARD = "9b46ad13-1bdc-4db6-a3d6-89031c2fa07e"
API = "https://cymetica.com/api/v1/event-cards"


def get(url):
    req = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "qa-cymetica mockup snapshot"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


deck = get(API + "/")["cards"]
pos = next((i for i, c in enumerate(deck) if c["id"] == CARD), None)
if pos is None:
    sys.exit(f"card {CARD} is not in the deck any more")
hist = get(f"{API}/{CARD}/index-history?interval=1d")
out = {"read_at": datetime.now(timezone.utc).isoformat(timespec="seconds"), "deck_size": len(deck), "deck_position": pos,
       "card": deck[pos], "behind": deck[pos + 1:pos + 3],
       "hist": hist}
(HERE / "event-data.json").write_text(json.dumps(out, ensure_ascii=False, indent=1), encoding="utf-8")
print("event-data.json:", out["read_at"], "| deck", len(deck), "| position", pos, "| points", len(hist.get("points", [])))
