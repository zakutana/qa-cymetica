"""Freeze what the page reads: company 14 after search #19, and their live script and stylesheet. GET only.

python outbox/quant-lab-v3/freeze.py
"""
import json
import os
import re
from pathlib import Path

import httpx
from dotenv import load_dotenv

HERE = Path(__file__).resolve().parent
load_dotenv(HERE.parents[1] / ".env")
BASE = "https://cymetica.com"
h = httpx.Client(base_url=BASE + "/api/v1/company", timeout=180, headers={"X-API-Key": os.environ["QA_TRUSTED_KEY"]})
(HERE / "data").mkdir(exist_ok=True)
(HERE / "their").mkdir(exist_ok=True)


def save(name, obj):
    (HERE / "data" / name).write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    print(name, (HERE / "data" / name).stat().st_size)


mine = h.get("/mine").json()
save("mine.json", {k: mine.get(k) for k in ("id", "name", "status", "run_state")})
save("quant-lab.json", h.get("/14/quant-lab").json())
save("search.json", h.get("/14/quant-lab/search").json())
save("results.json", h.get("/14/quant-lab/search/results", params={"limit": 200}).json())
save("memory.json", h.get("/14/quant-lab/search/memory", params={"limit": 60}).json())

page = httpx.get(BASE + "/company/app/experiments", timeout=60).text
ver = re.search(r"quant-lab\.js\?v=(\w+)", page).group(1)
for name in ("quant-lab.js", "quant-lab.css"):
    body = httpx.get(f"{BASE}/static/company/{name}?v={ver}", timeout=60).text
    (HERE / "their" / name).write_text(body, encoding="utf-8")
    print(name, ver, len(body))
