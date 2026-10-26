"""Read the live Agent Tournaments data the v4 pictures are drawn from (GET only) into data.json beside this file.

Public, no key: the lobby (rules, tiers, modes) and table 15 (standings, race, changes). With our own X-API-Key
(QA_TRUSTED_KEY, read from .env, never written out): our seat's view of the same table -- its bot settings, its
NEXUS lock and tunes, its closed trades. That is the owner view the Tune picture replays.
"""
import json
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parent.parent / ".env")
B = "https://cymetica.com/api/v1/agent-tournaments"
TABLE = 15

pub = httpx.Client(timeout=60, headers={"User-Agent": "qa-cymetica mockup"})
lobby = pub.get(f"{B}/lobby").json()
table = pub.get(f"{B}/tables/{TABLE}").json()

key = os.environ.get("QA_TRUSTED_KEY")
owner = {}
if key:
    mine = httpx.Client(timeout=60, headers={"User-Agent": "qa-cymetica mockup", "X-API-Key": key})
    t = mine.get(f"{B}/tables/{TABLE}").json()
    owner = {k: t.get(k) for k in ("my_seat", "my_bot_settings", "my_nexus_lock", "your_trades")}

(HERE / "data.json").write_text(json.dumps({"lobby": lobby, "table": table, "owner": owner}), encoding="utf-8")
print("table", table["id"], table["status"], len(table["standings"]), "standings;",
      "owner view" if owner.get("my_seat") else "NO owner view",
      "| live mode:", lobby.get("rules", {}).get("modes"))
