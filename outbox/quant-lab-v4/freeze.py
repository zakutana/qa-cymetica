"""Freeze what the v4 mock reads: company 14's lab as of now (owner key, GET only), their live quant-lab script and
stylesheet, the skills catalogue and the bot species (public GETs).

python outbox/quant-lab-v4/freeze.py
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
pub = httpx.Client(base_url=BASE, timeout=120)
(HERE / "data").mkdir(exist_ok=True)
(HERE / "their").mkdir(exist_ok=True)


def save(name, obj):
    (HERE / "data" / name).write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    print(name, (HERE / "data" / name).stat().st_size)


mine = h.get("/mine").json()
save("mine.json", {k: mine.get(k) for k in ("id", "name", "status", "run_state")})
save("quant-lab.json", h.get("/14/quant-lab").json())
save("search.json", h.get("/14/quant-lab/search").json())
res = h.get("/14/quant-lab/search/results", params={"limit": 200}).json()
# every run's own rows (the page's read stops at the newest 200), so each run in the list can be opened again
rows, seen = [], set()
for run in res.get("runs") or []:
    if run.get("status") != "done":
        continue
    for x in h.get("/14/quant-lab/search/results", params={"limit": 200, "search_id": run["id"]}).json().get("held_back_results") or []:
        if x["id"] not in seen:
            seen.add(x["id"])
            rows.append(x)
res["held_back_results"] = sorted(rows, key=lambda x: (-x["search_id"], x["id"]))
save("results.json", res)
save("memory.json", h.get("/14/quant-lab/search/memory", params={"limit": 60}).json())
save("skills.json", pub.get("/api/v1/skills").json())
save("species.json", pub.get("/api/v1/cloned-bots/available").json())

page = pub.get("/company/app/experiments").text
ver = re.search(r"quant-lab\.js\?v=(\w+)", page).group(1)
for name in ("quant-lab.js", "quant-lab.css"):
    body = pub.get(f"/static/company/{name}", params={"v": ver}).text
    (HERE / "their" / name).write_text(body, encoding="utf-8")
    print(name, ver, len(body))
