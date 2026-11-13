"""Their quant-lab.js (their/, freeze.py) with the v4 hooks and a new BLIND stage; data/ingredients.json from their data.

python outbox/quant-lab-v4/build.py
"""
import json
import re
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
js = (HERE / "their" / "quant-lab.js").read_text(encoding="utf-8")


def sub(old: str, new: str) -> None:
    global js
    if js.count(old) != 1:
        raise SystemExit(f"{js.count(old)} matches: {old[:70]}")
    js = js.replace(old, new)


# the v4 page draws the runs list, the winners and the bots itself (v4.js); their script keeps the reactor and the data
sub("  function q3Runs() {\n", "  function q3Runs() {\n    if (window.V4 && V4.runs && V4.runs()) return true;\n")
sub("    renderRuns();\n    if (loading()) { $('top').innerHTML",
    "    renderRuns();\n    if (!loading() && window.V4 && V4.top && V4.top()) return;\n    if (loading()) { $('top').innerHTML")
sub("    var exps = ((ov && ov.experiments) || []).slice().sort(function (a, b) {",
    "    if (window.V4 && V4.bots && V4.bots()) return;\n    var exps = ((ov && ov.experiments) || []).slice().sort(function (a, b) {")
# BLIND: a run asked with the two questions has weeks (or Flash hours): show them, not a row of every shortlisted card
sub("  function drawBlind(p) {\n", "  function drawBlind(p) {\n    var r5 = q3Run(); if (r5 && r5.profile) return v4DrawBlind(p, r5);\n")
# an older run without windows: its card row holds six at most, so the cards never sit on each other
sub("    var n = M.candidates.length, gap = 14, w = (W - 60 - gap * (n - 1)) / n;\n    M.candidates.forEach(function (c, i) {",
    "    var CR = M.candidates.slice(0, 6), n = CR.length, gap = 14, w = (W - 60 - gap * (n - 1)) / n;\n    CR.forEach(function (c, i) {")
# THE BAR: a profile run holds the winners and the nearest misses only, as an older run with windows does
sub("    if (!q3Windows()) return { list: M.candidates, more: 0 };",
    "    var r6 = q3Run(); if (!q3Windows() && !(r6 && r6.profile)) return { list: M.candidates.slice(0, 8), more: Math.max(0, M.candidates.length - 8) };")
# FOUND: a long name stops before the result on its right
sub("      txt(nm, x + 46, y + 20, '400 ' + nf + 'px ' + BLACK, C.text, 'left');",
    "      ctx.font = '400 ' + nf + 'px ' + BLACK; while (ctx.measureText(nm).width > cw - 46 - 150 && nm.length > 4) nm = nm.slice(0, -2);\n"
    "      txt(nm, x + 46, y + 20, '400 ' + nf + 'px ' + BLACK, C.text, 'left');")
sub("  // ---------------------------------------------------------------- start\n",
    (HERE / "blind.js").read_text(encoding="utf-8") + "  // ---------------------------------------------------------------- start\n")
sub("  window.QL = { ready: false, mode: null, sim: null };\n",
    "  window.QL = { ready: false, mode: null, sim: null };\n"
    "  window.QL.M = function () { return M; }; window.QL.S = S; window.QL.live = function () { return LIVE; };\n"
    "  window.QL.pick = function (id) { SELECTED = id; apply(); }; window.QL.size = size; window.QL.repaint = paint;\n"
    "  window.QL.cur = function () { return LAST_GOOD; }; window.QL.goStage = goStage;\n"
    "  window.QL.tools = { pct: pct, num: num, esc: esc, day: day, stamp: stamp, coinImg: coinImg, modelInfo: modelInfo, headImg: headImg, curveOf: curveOf };\n")
sub("  window.QL.ready = true;\n", "  window.QL.ready = true;\n  if (window.V4 && V4.init) V4.init();\n")
(HERE / "quant-lab.js").write_text(js, encoding="utf-8")
print("built", len(js), "js")

# ---------------------------------------------------------------- the ingredients, every word from their own data
D = HERE / "data"
res = json.loads((D / "results.json").read_text(encoding="utf-8"))
st = json.loads((D / "search.json").read_text(encoding="utf-8"))
lab = json.loads((D / "quant-lab.json").read_text(encoding="utf-8"))
skills = {s["id"]: s for s in json.loads((D / "skills.json").read_text(encoding="utf-8"))["skills"]}
species = json.loads((D / "species.json").read_text(encoding="utf-8"))
rows = res["held_back_results"]
cand = next(r["candidates"] for r in res["runs"] if r.get("candidates") and r["candidates"].get("model_ids"))
flash = next(r["candidates"] for r in res["runs"] if r.get("candidates") and r["candidates"].get("signals"))

cat = js[js.index("  var MODELS = {"):js.index("  var RULES =")]
MODELS = {k: (i, n) for k, i, n in re.findall(r"(\w+): \['([^']+)', '([^']+)'\]", cat[:cat.index("var COMBOS")])}
COMBOS = {k: (i, n, parts) for k, i, n, parts in re.findall(r"(\w+): \['([^']+)', '([^']+)', '([^']+)'\]", cat[cat.index("var COMBOS"):cat.index("var SKILLS")])}
SKILLN = {k: (i, n) for k, i, n in re.findall(r"(\w+): \['([^']+)', '([^']+)'\]", cat[cat.index("var SKILLS"):])}

IND = {"rsi_14": "RSI 14", "macd_hist": "MACD hist", "volume_ratio": "Volume ×avg", "bb_width": "BB width", "ema_9": "EMA 9", "ema_21": "EMA 21",
       "ema_50": "EMA 50", "sma_20": "SMA 20", "stoch_k": "Stoch %K", "stoch_d": "Stoch %D", "close": "Close", "bb_lower": "BB lower"}


def word(t):
    return IND.get(t, t)


def conds(text):
    out = []
    for part in text.split(" and "):
        m = re.match(r"\s*([a-z_0-9]+)\s*([<>])\s*([a-z_0-9.]+)\s*$", part)
        if m:
            out.append(m.groups())
    return out


def rule_of(model):
    """The entry rule as their labels give it: the stricter and the looser version side by side (the lab's own two
    variants of each model's rule), merged into ranges. None when no label carries one."""
    v = {}
    for x in rows:
        if x["model"] != model:
            continue
        m = re.search(r"entry (stricter|looser): (.*)$", x.get("settings_label") or "")
        if m and " or " not in m.group(2):
            v[m.group(1)] = conds(m.group(2))
    if not v:
        return None
    a, b = v.get("stricter"), v.get("looser")
    base = a or b
    chips = []
    for i, (ind, op, val) in enumerate(base):
        other = (b if a else a) or []
        o = other[i] if i < len(other) and other[i][0] == ind and other[i][1] == op else None
        if o and o[2] != val and re.match(r"^[\d.]+$", val) and re.match(r"^[\d.]+$", o[2]):
            lo, hi = sorted([float(val), float(o[2])])
            val = f"{lo:g}–{hi:g}"
        chips.append(f"{word(ind)} {op} {word(val)}")
    return chips


def stats(model):
    mine = [x for x in rows if x["model"] == model]
    won = [x for x in mine if x["verdict"] == "kept"]
    best = max(mine, key=lambda x: (x.get("held_back") or {}).get("return_pct") or -1e9, default=None)
    bh = (best or {}).get("held_back") or {}
    return {"tested": len(mine), "won": len(won), "runs": sorted({x["search_id"] for x in mine}, reverse=True)[:6],
            "best": None if best is None else {"pct": bh.get("return_pct"), "market": best["market"], "run": best["search_id"]}}


exps = {}
for e in lab.get("experiments") or []:
    sr = (e.get("config") or {}).get("signal_rule") or {}
    name = (sr.get("name") or "").split(" on ")[0]
    if name and sr.get("buy"):
        exps[name] = {"buy": sr["buy"], "sell": sr.get("sell"), "indicators": sr.get("indicators") or []}

sides = defaultdict(set)
for x in rows:
    sides[x["model"]].add(x.get("side") or "long")
helix = next((s for s in species["wta_species"] if (s.get("live_decision_source") or {}).get("strategy_symbol") == "HELIX"), None)

items = []
for k in cand["model_ids"]:
    icon, name = MODELS.get(k, ("🤖", k.upper()))
    it = {"id": k, "group": "models", "icon": icon, "name": name, "sides": sorted(sides[k]) or (["short"] if k.endswith("_red") else ["long"]),
          "rule": rule_of(k), "stats": stats(k), "in": [c for c, (_, _, p) in COMBOS.items() if name.upper() in p.upper().split(" + ")]}
    if k in exps:
        it["exact"] = exps[k]
    if k == "helix" and helix:
        it["about"] = helix["live_decision_source"]["label"]
        it["source"] = "/api/v1/cloned-bots/available (MACD Hunter, live decision source HELIX)"
    it["family"] = "Backtested Strategy" if "_" in k else "Biomimetic model"
    items.append(it)
for sid in cand["skills"]:
    k = sid.split(":", 1)[1]
    s = skills.get(k, {})
    icon, name = SKILLN.get(k, ("🧩", s.get("name", k)))
    items.append({"id": sid, "group": "skills", "icon": icon, "name": s.get("name", name), "sides": sorted(sides[sid]) or ["long"],
                  "about": s.get("eli5") or s.get("description"), "example": s.get("example"), "rule": rule_of(sid), "stats": stats(sid),
                  "used_by": [u["name"] for u in s.get("used_by_species") or []], "source": "/api/v1/skills"})
for nr in cand.get("not_replayable") or []:
    k = nr["id"].split(":", 1)[1]
    s = skills.get(k, {})
    items.append({"id": nr["id"], "group": "skills", "off": nr["why"], "icon": SKILLN.get(k, ("🧩", ""))[0], "name": s.get("name", k),
                  "about": s.get("eli5") or s.get("description"), "example": s.get("example"), "source": "/api/v1/skills"})
for cid in cand["combos"]:
    k = cid.split(":", 1)[1]
    icon, name, parts = COMBOS.get(k, ("🧬", k, ""))
    items.append({"id": cid, "group": "combos", "icon": icon, "name": name, "parts": parts.split(" + "), "sides": sorted(sides[cid]) or ["long"],
                  "stats": stats(cid), "vote": "2 of 3",
                  "source": "the lab's own rule text: each entry is the three models' entries paired, so any two of the three agreeing open it"})
fam_rows = defaultdict(list)
for x in rows:
    if str(x["model"]).startswith("flash:"):
        fam_rows[x["model"]].append(x)
for f, w in zip(flash["families"], flash["family_words"]):
    k = "flash:" + f
    fr = fam_rows.get(k, [])
    hits = [((x.get("direction") or {}).get("unseen") or {}).get("hit_pct") for x in fr]
    hits = [h for h in hits if h is not None]
    labels = sorted({x["settings_label"] for x in fr})
    items.append({"id": k, "group": "flash", "icon": "⚡", "name": w[0].upper() + w[1:], "sides": sorted(sides[k]),
                  "examples": labels[:4], "variants": len(labels), "stats": stats(k),
                  "hit": None if not hits else {"lo": min(hits), "hi": max(hits), "n": len(hits)}, "source": "the lab's own signal labels (search #27)"})
(D / "ingredients.json").write_text(json.dumps({"items": items, "flash_signals": flash["signals"]}, ensure_ascii=False, indent=1), encoding="utf-8")
print("ingredients", len(items))
