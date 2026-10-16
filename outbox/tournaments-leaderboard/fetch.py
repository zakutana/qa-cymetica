"""Read every Agent Tournaments table the lobby lists (GET, no key) into tables.json beside this file."""
import json
from pathlib import Path

import httpx

HERE = Path(__file__).resolve().parent
B = "https://cymetica.com/api/v1/agent-tournaments"
c = httpx.Client(timeout=60, headers={"User-Agent": "qa-cymetica mockup"})
lobby = c.get(f"{B}/lobby").json()
tables = []
for t in lobby["tables"]:
    d = c.get(f"{B}/tables/{t['id']}").json()
    tables.append(d)
    print(d["id"], d["status"], d.get("label"), len(d.get("standings") or []), "standings")
(HERE / "tables.json").write_text(json.dumps({"lobby": lobby, "tables": tables}), encoding="utf-8")
print("top_agents", json.dumps(lobby.get("top_agents"))[:600])
