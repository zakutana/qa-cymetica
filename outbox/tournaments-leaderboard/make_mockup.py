"""Build leaderboard.html (this folder): a new Agent Tournaments tab, Leaderboard -- every bot that has sat at
a table, all time, and who leads.

The operator, 2026-10-16: "ted pridat novou zalozku leaderboard a navrhni design kde uvidime vsechny boty na
platforme za cely cas kdo vede zebricek". The tab sits beside Lobby, Top agents and How it works.

Ranked by Elo (the tournament's own all-time rating: every bot starts at 1,500 and each finished table rates
every pair by final rank), ties by tables won, then by average ROI. A house strategy is one row across its
tables; a member's bot is one row. Real figures: every table GET /api/v1/agent-tournaments/tables/{id} lists,
read 2026-10-16 (tables.json): seats, ROI, trades, volume, qualified, house, Elo, wins. No table has finished
yet, so every Elo reads 1,500 and every "won" 0 -- the page shows that honestly, and the order falls to ROI.
"YOU" marks the bots of the signed-in owner (ours: lab MACD Hunter, lab Wave 2 Fibonacci Phoenix, tournament
Perceptron Oracle). Palette: the site's navy, cyan, green, red and blue, plus the avatar tints they use.
"""
from __future__ import annotations

import html
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DATA = json.loads((HERE / "tables.json").read_text(encoding="utf-8"))
OURS = {"lab MACD Hunter", "lab Wave 2 Fibonacci Phoenix", "tournament Perceptron Oracle"}
BOT = ('<svg viewBox="0 0 16 16"><rect x="3" y="5" width="10" height="8" rx="3" fill="none" stroke="currentColor" '
       'stroke-width="1.4"/><circle cx="6.3" cy="9" r="1" fill="currentColor"/><circle cx="9.7" cy="9" r="1" '
       'fill="currentColor"/><path d="M8 5V3" stroke="currentColor" stroke-width="1.4"/></svg>')
TINTS = ["#7FE6FF", "#66ffb8", "#93c5fd", "#00cfff", "#00ff88", "#3b82f6"]


def esc(s):
    return html.escape(str(s), quote=True)


def rows():
    bots = defaultdict(lambda: {"tables": [], "trades": 0, "volume": 0.0, "house": False, "elo": 1500, "wins": 0})
    for t in DATA["tables"]:
        for s in t.get("standings") or []:
            name = s["bot"].replace("House ", "") if s.get("house") else s["bot"]
            b = bots[name]
            b["house"] = bool(s.get("house"))
            b["tables"].append({"label": f'{t["label"]} #{t["id"]}', "roi": s.get("roi_pct") or 0.0,
                                "rank": s.get("rank"), "live": t["status"] == "running",
                                "qualified": s.get("qualified")})
            b["trades"] += s.get("trades") or 0
            b["volume"] += s.get("volume_usdc") or 0.0
            b["elo"] = s.get("elo") or 1500
            b["wins"] += s.get("elo_wins") or 0
    out = []
    for name, b in bots.items():
        rois = [x["roi"] for x in b["tables"]]
        out.append({"name": name, **b, "played": len(b["tables"]), "avg": sum(rois) / len(rois), "best": max(rois),
                    "top3": sum(1 for x in b["tables"] if not x["live"] and (x["rank"] or 99) <= 3),
                    "mine": name in OURS})
    out.sort(key=lambda r: (-r["elo"], -r["wins"], -r["avg"]))
    return out


def pct(v, big=False):
    cls = "g" if v > 0 else ("r" if v < 0 else "d")
    return f'<b class="{cls}{" big" if big else ""}">{v:+.2f}%</b>'


def av(i, size=""):
    return f'<span class="av {size}" style="color:{TINTS[i % len(TINTS)]}">{BOT}</span>'


def form(r):
    """The last five tables, newest first: a finished one by its place, a live one as a pulsing cell with its ROI."""
    cells = []
    for x in r["tables"][-5:][::-1]:
        if x["live"]:
            cells.append(f'<i class="f live" title="{esc(x["label"])}: live, {x["roi"]:+.1f}%"></i>')
        else:
            p = x["rank"] or 10
            cells.append(f'<i class="f {"p1" if p == 1 else ("p3" if p <= 3 else "")}" title="{esc(x["label"])}: #{p}"></i>')
    cells += ['<i class="f none"></i>'] * (5 - len(cells))
    return "".join(cells)


CSS = """
:root{--bg:#0a0e17;--deep:#06090f;--navy:#0d1520;--navy2:#111a28;--line:#16233a;--line2:#1a2a44;--line3:#1e3050;
--text:#E6EDF7;--dim:#A9B8CC;--dim2:#7f93ad;--cyan:#00cfff;--green:#00ff88;--red:#ff4444;--blue:#3b82f6}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:var(--bg);color:var(--text);font-family:'JetBrains Mono',monospace;font-size:13px}
.wrap{max-width:1240px;margin:0 auto;padding:0 16px 48px}
.sub{display:flex;align-items:center;gap:26px;padding:22px 0;border-bottom:1px solid var(--line)}
.brand{display:flex;align-items:center;gap:12px}
.brand .logo{width:46px;height:46px;border-radius:50%;border:3px dotted var(--green);display:grid;place-items:center;
 box-shadow:0 0 0 2px var(--cyan) inset}
.brand .logo i{width:6px;height:12px;border-radius:3px;background:var(--cyan);margin:0 2px;display:inline-block}
.brand small{display:block;font-size:11px;letter-spacing:.3em;color:var(--cyan);font-weight:700}
.brand b{font-family:'Archivo Black';font-weight:400;font-size:20px;letter-spacing:.02em}
.tabs{display:flex;gap:8px}
.tabs span{font-size:16px;color:var(--dim2);padding:10px 16px;border-radius:12px;border:1px solid transparent}
.tabs span.on{color:var(--text);background:rgba(0,207,255,.08);border-color:var(--line3)}
.tabs .new{font-size:9.5px;font-weight:700;color:var(--bg);background:var(--green);border-radius:4px;padding:1px 5px;margin-left:6px;vertical-align:3px}
.title{display:flex;align-items:flex-end;gap:16px;margin:30px 0 18px;flex-wrap:wrap}
.title h1{font-family:'Archivo Black';font-weight:400;font-size:44px;line-height:1}
.title .chip{font-size:12px;font-weight:700;letter-spacing:.12em;color:var(--cyan);border:1px solid rgba(0,207,255,.55);border-radius:99px;padding:5px 11px}
.title .how{margin-left:auto;font-size:12px;color:var(--dim2)}
.title .how b{color:var(--text)}
.i{display:inline-grid;place-items:center;width:16px;height:16px;border-radius:50%;border:1px solid var(--dim2);font-size:10px;margin-left:6px;color:var(--dim2)}
.kpis{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:22px}
.kpi{background:var(--navy);border:1px solid var(--line2);border-radius:14px;padding:12px 16px}
.kpi b{display:block;font-family:'Archivo Black';font-weight:400;font-size:28px;line-height:1.1}
.kpi span{font-size:11px;letter-spacing:.12em;color:var(--dim2);font-weight:700}
.bar{display:flex;align-items:center;gap:10px;margin-bottom:16px;flex-wrap:wrap}
.seg{display:flex;gap:4px;background:var(--deep);border:1px solid var(--line2);border-radius:12px;padding:4px}
.seg span{padding:7px 12px;border-radius:9px;color:var(--dim2);font-weight:600}
.seg span.on{background:var(--navy2);color:var(--text);border:1px solid var(--line3)}
.tog{display:flex;align-items:center;gap:8px;color:var(--dim)}
.tog i{width:32px;height:18px;border-radius:99px;background:var(--green);position:relative}
.tog i:after{content:'';position:absolute;top:2px;left:16px;width:14px;height:14px;border-radius:50%;background:var(--bg)}
.search{margin-left:auto;border:1px solid var(--line2);border-radius:12px;padding:9px 14px;color:var(--dim2);min-width:220px;background:var(--deep)}
.podium{display:grid;grid-template-columns:1fr 1.15fr 1fr;gap:16px;align-items:end;margin-bottom:22px}
.pc{background:var(--navy);border:1px solid var(--line2);border-radius:20px;padding:18px;display:flex;flex-direction:column;align-items:center;gap:8px;text-align:center;min-width:0}
.pc.p1{border-color:rgba(0,255,136,.55);box-shadow:0 0 24px rgba(0,255,136,.14);padding-top:24px}
.pc .place{font-family:'Archivo Black';font-size:13px;letter-spacing:.1em;color:var(--dim2)}
.pc.p1 .place{color:var(--green)}
.pc .nm{font-family:'Archivo Black';font-weight:400;font-size:18px;max-width:100%;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pc .elo{font-size:30px;font-weight:700;line-height:1}
.pc .elo small{font-size:11px;color:var(--dim2);letter-spacing:.12em;margin-left:4px}
.pc .stats{display:flex;gap:16px;font-size:12px;color:var(--dim2)}
.pc .stats b{display:block;font-size:15px;color:var(--text)}
.av{width:30px;height:30px;border-radius:50%;display:grid;place-items:center;border:1.5px solid currentColor;flex:none;background:var(--deep)}
.av svg{width:16px;height:16px}
.av.xl{width:62px;height:62px;border-width:2px}.av.xl svg{width:32px;height:32px}
.pc.p1 .av.xl{box-shadow:0 0 0 3px var(--green),0 0 22px rgba(0,255,136,.55)}
table{width:100%;border-collapse:separate;border-spacing:0 6px}
th{font-size:10.5px;letter-spacing:.12em;color:var(--dim2);font-weight:700;text-align:right;padding:0 12px 4px;white-space:nowrap}
th:nth-child(1),th:nth-child(2){text-align:left}
th.sort{color:var(--cyan)}
td{background:var(--navy);padding:10px 12px;text-align:right;white-space:nowrap;font-size:13.5px;border-top:1px solid var(--line);border-bottom:1px solid var(--line)}
td:first-child{border-left:1px solid var(--line);border-radius:12px 0 0 12px;text-align:left;width:52px}
td:last-child{border-right:1px solid var(--line);border-radius:0 12px 12px 0}
tr.mine td{background:rgba(0,207,255,.06);border-color:rgba(0,207,255,.35)}
td.bot{text-align:left;max-width:360px}
td.bot .in{display:flex;align-items:center;gap:10px;min-width:0}
td.bot .nm{overflow:hidden;text-overflow:ellipsis;font-weight:600}
.rk{font-family:'Archivo Black';font-size:16px;color:var(--dim)}
.h{font-size:9.5px;font-weight:700;color:var(--dim2);border:1px solid var(--line3);border-radius:4px;padding:1px 5px}
.you{font-size:9.5px;font-weight:700;color:var(--bg);background:var(--cyan);border-radius:4px;padding:1px 5px}
.at{font-size:10.5px;color:var(--green);border:1px solid rgba(0,255,136,.45);border-radius:99px;padding:1px 7px;white-space:nowrap}
.g{color:var(--green)}.r{color:var(--red)}.d{color:var(--dim2)}.c{color:var(--cyan)}
.big{font-size:20px}
.f{display:inline-block;width:12px;height:12px;border-radius:3px;background:var(--line3);margin-left:4px}
.f.p1{background:var(--green)}.f.p3{background:var(--cyan)}.f.none{background:transparent;border:1px dashed var(--line3)}
.f.live{background:var(--green);opacity:.55;box-shadow:0 0 8px var(--green);animation:pulse 1.6s infinite}
@keyframes pulse{50%{opacity:.2}}
.foot{margin-top:14px;font-size:12px;color:var(--dim2);display:flex;gap:16px;flex-wrap:wrap;align-items:center}
.foot .f{margin-left:0;margin-right:4px;vertical-align:-1px}
"""


def page():
    rs = rows()
    live_tables = sum(1 for t in DATA["tables"] if t["status"] == "running")
    finished = sum(1 for t in DATA["tables"] if t["status"] in ("finished", "done", "ended"))
    podium_order = [1, 0, 2]
    pod = []
    for i in podium_order:
        r = rs[i]
        cls = "pc p1" if i == 0 else "pc"
        pod.append(f'<div class="{cls}"><span class="place">{("1ST", "2ND", "3RD")[i]}</span>{av(i, "xl")}'
                   f'<span class="nm">{esc(r["name"])}</span>'
                   f'<span>{"<span class=h>H</span> " if r["house"] else ""}{"<span class=you>YOU</span>" if r["mine"] else ""}</span>'
                   f'<span class="elo">{r["elo"]:,}<small>ELO</small></span>'
                   f'<div class="stats"><span><b>{r["played"]}</b>tables</span><span><b>{r["wins"]}</b>won</span>'
                   f'<span>{pct(r["avg"])}avg ROI</span></div></div>')
    body = []
    for n, r in enumerate(rs, 1):
        live = next((x for x in r["tables"] if x["live"]), None)
        at = f' <span class="at">● {esc(live["label"])}</span>' if live else ""
        tags = ('<span class="h">H</span>' if r["house"] else "") + ('<span class="you">YOU</span>' if r["mine"] else "")
        body.append(
            f'<tr class="{"mine" if r["mine"] else ""}"><td><span class="rk">{n}</span></td>'
            f'<td class="bot"><div class="in">{av(n)}<span class="nm">{esc(r["name"])}</span>{tags}{at}</div></td>'
            f'<td><b>{r["elo"]:,}</b></td><td>{r["played"]}</td><td>{r["wins"]}</td><td>{r["top3"]}</td>'
            f'<td>{pct(r["avg"])}</td><td>{pct(r["best"])}</td><td class="d">{r["trades"]:,}</td>'
            f'<td><b class="d">$0</b> <span class="d">+ 0 ET10</span></td><td>{form(r)}</td></tr>')
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent Tournaments: leaderboard</title>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><main class="wrap">
<nav class="sub"><div class="brand"><span class="logo"><span><i></i><i></i></span></span><div><small>AGENT</small><b>TOURNAMENTS</b></div></div>
 <div class="tabs"><span>Lobby</span><span>Top agents</span><span class="on">Leaderboard<span class="new">NEW</span></span><span>How it works</span></div></nav>
<div class="title"><h1>Leaderboard</h1><span class="chip">ALL TIME</span>
 <span class="how">Ranked by <b>Elo</b>, then tables won, then average ROI<span class="i" title="Every bot starts at 1,500. Each finished table rates every pair of its bots by final rank. A house strategy is one row across its tables.">i</span></span></div>
<div class="kpis"><div class="kpi"><b>{len(rs)}</b><span>BOTS RANKED</span></div><div class="kpi"><b class="g">{live_tables}</b><span>TABLES LIVE</span></div>
 <div class="kpi"><b>{finished}</b><span>TABLES FINISHED</span></div><div class="kpi"><b>$0 <span class="c" style="font-size:18px">+ 0 ET10</span></b><span>PAID TO WINNERS</span></div></div>
<div class="bar"><div class="seg"><span class="on">All time</span><span>30 days</span><span>7 days</span></div>
 <div class="seg"><span class="on">All</span><span>Week</span><span>Flash</span><span>ET10</span></div>
 <div class="seg"><span class="on">All bots</span><span>Members</span><span>House</span><span>Mine</span></div>
 <span class="search">Search a bot</span></div>
<div class="podium">{"".join(pod)}</div>
<table><tr><th>#</th><th>BOT</th><th class="sort">ELO ▼</th><th>TABLES</th><th>WON</th><th>TOP 3</th><th>AVG ROI</th><th>BEST ROI</th><th>TRADES</th><th>PRIZES</th><th>LAST 5</th></tr>
{"".join(body)}</table>
<div class="foot"><span><i class="f p1"></i>1st</span><span><i class="f p3"></i>2nd-3rd</span><span><i class="f"></i>4th-10th</span><span><i class="f live"></i>playing now</span>
 <span>No table has finished yet, so every bot is still at 1,500 Elo and the order falls to average ROI.</span></div>
</main></body></html>"""


def main():
    (HERE / "leaderboard.html").write_text(page(), encoding="utf-8")
    print("leaderboard.html written,", len(rows()), "bots")


if __name__ == "__main__":
    main()
