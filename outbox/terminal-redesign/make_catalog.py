"""Build catalog.js for the terminal mockup from Cymetica's live public catalogue (read 2026-10-17).

Sources: /api/v1/cloned-bots/available (bots), /api/v1/trading-models (20 algos), /api/v1/skills (29 skills),
and /static/js/terminal.js (the 8 classic algos and 6 risk skills the terminal defines itself).
Icons are Font Awesome names: the platform's own where it gives one, else picked here (its avatars 404).
Usage: python make_catalog.py <dir with avail.json, models.json, skills.json> <out catalog.js>
"""
import json
import re
import sys
import urllib.request
from pathlib import Path

src, dst = Path(sys.argv[1]), Path(sys.argv[2])
UA = {"User-Agent": "qa-cymetica"}
load = lambda n: json.loads((src / n).read_text(encoding="utf-8"))
avail, models, skills = load("avail.json"), load("models.json")["models"], load("skills.json")["skills"]
tjs = urllib.request.urlopen(urllib.request.Request("https://cymetica.com/static/js/terminal.js?v=20261010-3", headers=UA),
                             timeout=30).read().decode("utf-8", "replace")

BOT_ICON = {"MACD": "crosshairs", "RSI": "gauge-high", "BOLL": "mask", "VOL": "chart-column", "TREND": "arrow-trend-up",
            "STOCH": "hand-fist", "ICHI": "crown", "FIB": "fire", "ATR": "arrows-up-down", "DIV": "dragon",
            "PCPN": "brain", "LIQHUNT": "bullseye", "STAT": "chart-simple", "SYNC": "arrows-rotate",
            "FADE": "arrow-trend-down", "CORR": "link", "CRASH": "burst", "VORTX": "hurricane", "GLOOM": "moon",
            "SENT": "water", "DELTA": "bolt", "DREAD": "newspaper"}
CLASSIC_ICON = {"macd": "chart-simple", "rsi": "gauge", "boll": "water", "vol": "bolt", "fib": "bullseye",
                "mr": "arrows-rotate", "ema": "code-merge", "adx": "compass"}
MODEL_ICON = {"MITOSIS": "circle-nodes", "MIRAGE": "ghost", "DRIFT": "wind", "RUPTURE": "burst", "ANCHOR": "anchor",
              "ENDGAME": "flag-checkered", "RECOIL": "rotate-left", "VERDICT": "gavel", "FLUX": "wave-square",
              "SIGNAL": "tower-broadcast", "ORACLE": "eye"}
LOCAL_SKILL_ICON = {"sl": "shield-halved", "tp": "sack-dollar", "size": "scale-balanced", "time": "clock",
                    "div": "chart-pie", "ai": "robot"}
SKILL_ICON = {"tachometer-alt": "gauge", "spiral": "hurricane"}

bots = []
for b in avail["wta_species"] + avail["perpetual_agents"]:
    lds = b.get("live_decision_source") or {}
    bots.append({"name": b["name"], "sym": b["symbol"], "icon": BOT_ICON.get(b["symbol"], "robot"),
                 "kind": "Indicator species" if b["type"] == "wta_species" else "Perpetual agent",
                 "tagline": b.get("tagline"), "desc": b.get("description"), "style": b.get("strategy_type"),
                 "risk": b.get("risk_profile"), "rule": lds.get("label"),
                 "ind": [{"n": i["name"], "p": i.get("params") or {}} for i in b.get("primary_indicators") or []],
                 "clones": b.get("total_clones"), "trades": b.get("total_trades"), "wr": b.get("win_rate")})

algos = []
a0, s0 = tjs.find("var ALGOS"), tjs.find("var SKILLS")
for m in re.finditer(r"\{ id: '(\w+)', icon: '[^']*', name: '([^']+)', desc: '([^']+)', params: \[(.*?)\]\}", tjs[a0:s0], re.S):
    params = [{"label": p[0], "min": float(p[1]), "max": float(p[2]), "def": float(p[3])} for p in
              re.findall(r"label: '([^']+)', min: ([\d.]+), max: ([\d.]+), step: [\d.]+, default: ([\d.]+)", m.group(4))]
    algos.append({"name": m.group(2), "icon": CLASSIC_ICON.get(m.group(1), "chart-line"), "cat": "Technical indicator",
                  "desc": m.group(3), "params": params, "free": True})
for x in models:
    algos.append({"name": x["name"], "sym": x["symbol"], "icon": MODEL_ICON.get(x["symbol"], x["icon"]),
                  "cat": x["category"].replace("_", " ").capitalize(), "tagline": x.get("tagline"), "desc": x.get("description"),
                  "eli5": x.get("eli5"), "ex": x.get("example"), "level": x.get("complexity_level"),
                  "defaults": x.get("default_parameters") or {}, "free": not x.get("is_premium"), "price": x.get("price_usdc")})

out_skills = []
e0 = tjs.find("];", s0)
for m in re.finditer(r"\{ id: '(\w+)', icon: '[^']*', name: '([^']+)', desc: '([^']+)' \}", tjs[s0:e0]):
    out_skills.append({"name": m.group(2), "icon": LOCAL_SKILL_ICON.get(m.group(1), "shield-halved"), "cat": "Risk",
                       "desc": m.group(3), "free": True, "slot": "risk"})
for x in skills:
    out_skills.append({"name": x["name"], "icon": SKILL_ICON.get(x["icon"], x["icon"]),
                       "cat": x["category"].replace("_", " ").capitalize(), "desc": x.get("description"),
                       "eli5": x.get("eli5"), "ex": x.get("example"), "slot": x.get("slot_type"),
                       "free": not x.get("is_premium"), "live": x.get("is_implemented"),
                       "used": [u["name"] for u in x.get("used_by_species") or []]})

body = json.dumps({"bots": bots, "algos": algos, "skills": out_skills}, ensure_ascii=False, indent=0)
dst.write_text("/* Cymetica's public catalogue, read 2026-10-17 (see make_catalog.py in the session scratchpad). */\n"
               "const CAT=" + body + ";\n", encoding="utf-8")
print(len(bots), "bots", len(algos), "algos", len(out_skills), "skills", dst.stat().st_size, "bytes")
