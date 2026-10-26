"""Refresh live/fixtures/owner.json: our seat's view of table 15 (GET only, our own key from .env, never written out).

The v4 copy (live/serve.py) reads THEIR pages anonymously; the owner's column, our trades and the NEXUS lock are not in
those pages, so they are read here with our key (QA_TRUSTED_KEY) and the patch draws them in their markup.
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

key = os.environ.get("QA_TRUSTED_KEY")
if not key:
    raise SystemExit("QA_TRUSTED_KEY is not set in .env")
t = httpx.get(f"{B}/tables/{TABLE}", headers={"User-Agent": "qa-cymetica mockup", "X-API-Key": key}, timeout=60).json()
owner = {k: t.get(k) for k in ("my_seat", "my_bot_settings", "my_nexus_lock", "your_trades")}
if not owner["my_seat"]:
    raise SystemExit("no seat of ours at this table")
(HERE / "live" / "fixtures" / "owner.json").write_text(json.dumps(owner, ensure_ascii=False), encoding="utf-8")
print("owner.json:", owner["my_seat"]["bot"], "rank", owner["my_seat"]["rank"], len(owner["your_trades"]), "trades,",
      owner["my_nexus_lock"]["tune_count"], "tune(s)")
