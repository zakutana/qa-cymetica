"""Build card.html (this folder): the Agent Tournaments lobby's table cards, redrawn so the time left and the
whole prize pool read at first glance.

The operator, 2026-10-16, on the lobby card: "jako design je dobry jen chci hned na prvni pohled lepe videt
kolik zbyva casu do konce turnaje a kolik je v potu celkovem co se bude prerozdelovat mezi vyherce. to live
svitici muze byt v rohu a pod tim treba nejaky odpocet". So: the look stays (the card, the oval table, the
avatars, the chips); the glowing LIVE moves to the top-right corner with a countdown under it, and the oval's
centre shows the whole pool that will be split -- the USDC pot plus the ET10 on top -- and how it splits.

Real figures: GET /api/v1/agent-tournaments/lobby, read 2026-10-16 (lobby.json beside this file): pots,
prizes_now (the pot split 60 / 30 / 10 as it stands), et10_per_table, ends_at, day / days, leaders. Sample:
which seat is "yours" on Pro #2 (our lab MACD Hunter, #3, as the operator's screenshot shows).
Palette: the site's navy, cyan, green, red and blue, plus the avatar tints their page already uses.
"""
from __future__ import annotations

import html
import json
import math
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOBBY = json.loads((HERE / "lobby.json").read_text(encoding="utf-8"))
TABLES = {t["id"]: t for t in LOBBY["tables"]}
NOW = datetime.now(timezone.utc)

BOT = ('<svg viewBox="0 0 16 16"><rect x="3" y="5" width="10" height="8" rx="3" fill="none" stroke="currentColor" '
       'stroke-width="1.4"/><circle cx="6.3" cy="9" r="1" fill="currentColor"/><circle cx="9.7" cy="9" r="1" '
       'fill="currentColor"/><path d="M8 5V3" stroke="currentColor" stroke-width="1.4"/></svg>')
CROWN = ('<svg viewBox="0 0 16 10" class="crown"><path d="M1 9 L2.5 2 L6 6 L8 1 L10 6 L13.5 2 L15 9 Z" '
         'fill="#00ff88"/></svg>')
TINTS = ["#7FE6FF", "#66ffb8", "#93c5fd", "#00cfff", "#00ff88", "#3b82f6"]

CSS = """
:root{--bg:#0a0e17;--deep:#06090f;--navy:#0d1520;--navy2:#111a28;--line:#16233a;--line2:#1a2a44;--line3:#1e3050;
--text:#E6EDF7;--dim:#A9B8CC;--dim2:#7f93ad;--cyan:#00cfff;--green:#00ff88;--red:#ff4444;--blue:#3b82f6}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:var(--bg);color:var(--text);font-family:'JetBrains Mono',monospace;font-size:13px}
.disp{font-family:'Archivo Black',sans-serif;font-weight:400}
.wrap{max-width:1240px;margin:0 auto;padding:28px 16px 40px}
h2{font-family:'Archivo Black';font-weight:400;font-size:30px;display:flex;align-items:center;gap:12px;margin:8px 0 18px}
h2 .n{font-family:'JetBrains Mono';font-size:13px;font-weight:700;background:var(--cyan);color:var(--bg);border-radius:99px;
 min-width:26px;height:26px;display:grid;place-items:center}
.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:24px;margin-bottom:34px}
.card{position:relative;background:var(--navy);border:1px solid var(--line2);border-radius:22px;padding:20px 22px 18px;
 display:flex;flex-direction:column;min-width:0}
.card.mine{border-color:rgba(0,207,255,.55);box-shadow:0 0 0 1px rgba(0,207,255,.18)}
.head{display:flex;align-items:flex-start;gap:10px}
.head .name{font-family:'Archivo Black';font-size:20px;line-height:1.2;flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.chips{display:flex;align-items:center;gap:8px;margin-top:10px}
.chip{font-size:12px;font-weight:700;letter-spacing:.06em;padding:4px 10px;border-radius:99px;border:1px solid var(--line3);
 color:var(--dim);white-space:nowrap}
.chip.buy{color:var(--bg);background:var(--green);border-color:var(--green);box-shadow:0 0 12px rgba(0,255,136,.35)}
.chip.buy.e{background:var(--cyan);border-color:var(--cyan);box-shadow:0 0 12px rgba(0,207,255,.35)}
.chip.kind{color:var(--blue);border-color:rgba(59,130,246,.6)}
.chip.kind.fl{color:var(--bg);background:var(--green);border-color:var(--green)}
.chip.kind.e{color:var(--cyan);border-color:rgba(0,207,255,.6)}
.chips .len{color:var(--dim);font-size:12.5px;margin-left:2px}
/* the corner: status, and the time left under it */
.corner{display:flex;flex-direction:column;align-items:flex-end;gap:6px;flex:none}
.live{display:inline-flex;align-items:center;gap:7px;font-size:12px;font-weight:700;letter-spacing:.12em;color:var(--green);
 border:1px solid var(--green);background:rgba(0,255,136,.1);border-radius:99px;padding:5px 11px;
 box-shadow:0 0 14px rgba(0,255,136,.45),inset 0 0 8px rgba(0,255,136,.15)}
.live i{width:8px;height:8px;border-radius:50%;background:var(--green);box-shadow:0 0 8px var(--green);animation:pulse 1.6s infinite}
@keyframes pulse{50%{opacity:.35}}
.open{font-size:12px;font-weight:700;letter-spacing:.12em;color:var(--cyan);border:1px solid rgba(0,207,255,.6);border-radius:99px;padding:5px 11px}
.left{text-align:right}
.left .t{font-size:22px;font-weight:700;line-height:1;color:var(--text);letter-spacing:-.01em;font-variant-numeric:tabular-nums}
.left .t small{font-size:12px;color:var(--cyan);margin:0 6px 0 1px;font-weight:700}
.left .t small:last-child{margin-right:0}
.left .t.soon{color:var(--red)}.left .t.soon small{color:var(--red)}
.left .u{font-size:10.5px;color:var(--dim2);letter-spacing:.12em;margin-top:5px}
.bar{height:4px;border-radius:99px;background:var(--line3);margin-top:6px;width:150px;overflow:hidden;margin-left:auto}
.bar b{display:block;height:100%;background:linear-gradient(90deg,var(--cyan),var(--green))}
.left .soft{font-size:12px;color:var(--dim2)}
/* the table */
.oval{position:relative;height:250px;margin:14px 6px 12px}
.oval .ring{position:absolute;inset:13% 9%;border:2px solid var(--green);border-radius:999px;
 background:radial-gradient(ellipse at center,rgba(0,207,255,.10),rgba(13,21,32,0) 70%);
 box-shadow:0 0 26px rgba(0,255,136,.16) inset,0 0 18px rgba(0,255,136,.12)}
.oval.empty .ring{border:2px solid rgba(0,207,255,.55);box-shadow:0 0 26px rgba(0,207,255,.14) inset}
.pool{position:absolute;inset:0;display:grid;place-items:center;text-align:center}
.pool .k{font-size:10.5px;letter-spacing:.16em;color:var(--dim2);font-weight:700}
.pool .usd{font-family:'Archivo Black';font-size:40px;line-height:1.05;color:var(--green);text-shadow:0 0 18px rgba(0,255,136,.35)}
.pool .usd.e{color:var(--cyan);text-shadow:0 0 18px rgba(0,207,255,.35)}
.pool .plus{font-size:15px;font-weight:700;color:var(--cyan);margin-top:2px}
.split{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px;margin:0 0 10px}
.split div{background:var(--navy2);border:1px solid var(--line);border-radius:10px;padding:7px 8px;text-align:center;min-width:0}
.split span{display:block;font-size:10px;letter-spacing:.14em;color:var(--dim2);font-weight:700}
.split b{display:block;font-size:15px;color:var(--green);margin-top:2px;white-space:nowrap}
.split b small{font-size:10px;color:var(--cyan)}
.split em{display:block;font-style:normal;font-size:11px;color:var(--cyan);white-space:nowrap}
.split div:first-child{border-color:rgba(0,255,136,.35)}
.seat{position:absolute;transform:translate(-50%,-50%);display:flex;flex-direction:column;align-items:center}
.av{width:34px;height:34px;border-radius:50%;display:grid;place-items:center;border:1.5px solid currentColor;background:var(--deep)}
.av svg{width:18px;height:18px}
.seat.lead .av{box-shadow:0 0 0 2px var(--green),0 0 14px rgba(0,255,136,.6)}
.seat .crown{position:absolute;top:-11px;width:16px;height:10px}
.seat.me .av{box-shadow:0 0 0 3px var(--cyan),0 0 16px var(--cyan)}
.seat .you{position:absolute;bottom:-16px;font-size:9.5px;font-weight:700;color:var(--bg);background:var(--cyan);border-radius:4px;padding:1px 5px}
.slot{width:30px;height:30px;border-radius:50%;border:1.5px dashed rgba(0,207,255,.6);display:grid;place-items:center;color:var(--cyan);font-weight:700}
/* the foot */
.foot{display:flex;align-items:center;gap:10px;background:var(--deep);border-radius:12px;padding:11px 14px;margin-top:auto}
.foot .who{flex:1;min-width:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tag{font-size:11px;font-weight:700;color:var(--bg);background:var(--cyan);border-radius:5px;padding:2px 7px;margin-right:6px}
.g{color:var(--green)}.r{color:var(--red)}.c{color:var(--cyan)}.d{color:var(--dim2)}
.take{font-family:'Archivo Black';color:var(--cyan);letter-spacing:.03em}
.note{color:var(--dim);font-size:12.5px;margin:-6px 0 20px;max-width:900px;line-height:1.6}
/* the hero: the headline stays, the strip under it is redrawn */
.hero{max-width:1060px;margin-bottom:46px}
.hero h1{font-family:'Archivo Black';font-weight:400;font-size:84px;line-height:1.02;letter-spacing:-.01em}
.hero h1 em{font-style:normal;color:var(--green)}
.kinds{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin-top:30px}
.kind{background:var(--navy);border:1px solid var(--line2);border-radius:18px;padding:16px 18px 14px;min-width:0}
.kind .top{display:flex;align-items:center;gap:10px;margin-bottom:12px}
.kind .top b{font-family:'Archivo Black';font-weight:400;font-size:22px}
.kind .top .chip{margin-left:auto}
.kind table{width:100%;border-collapse:collapse}
.kind th{font-size:10px;letter-spacing:.14em;color:var(--dim2);font-weight:700;text-align:left;padding:0 0 6px}
.kind th:last-child,.kind td:last-child{text-align:right}
.kind td{padding:5px 0;font-size:17px;font-weight:700;white-space:nowrap;border-top:1px solid var(--line)}
.kind td .u{font-size:11px;color:var(--dim2);font-weight:700}
.kind td.win{color:var(--green)}.kind td.win .u{color:var(--green)}
.kind td .arr{color:var(--dim2);font-weight:400;padding:0 8px}
.kind .bonus{display:flex;align-items:center;gap:8px;margin-top:12px;font-size:12px;color:var(--dim)}
.kind .bonus b{color:var(--cyan);border:1px solid rgba(0,207,255,.55);border-radius:99px;padding:3px 10px;
 box-shadow:0 0 10px rgba(0,207,255,.25);white-space:nowrap}
.podium{display:flex;align-items:center;gap:14px;margin-top:16px}
.podium .k{font-size:10.5px;letter-spacing:.14em;color:var(--dim2);font-weight:700;white-space:nowrap}
.podium .bar3{flex:1;display:flex;gap:4px;height:30px}
.podium .bar3 span{display:flex;align-items:center;justify-content:center;gap:6px;border-radius:8px;font-size:12px;font-weight:700;white-space:nowrap}
.podium .p1{flex:60;background:var(--green);color:var(--bg)}
.podium .p2{flex:30;background:rgba(0,255,136,.35);color:var(--text)}
.podium .p3{flex:10;background:rgba(0,255,136,.16);color:var(--text)}
"""


def esc(s):
    return html.escape(str(s), quote=True)


def money(t, v):
    return f"{v:,.0f} ET10" if t["currency"] == "ET10" else f"${v:,.0f}"


def countdown(t):
    end = datetime.fromisoformat(t["ends_at"])
    s = max(0, int((end - NOW).total_seconds()))
    d, h, m, sec = s // 86400, s % 86400 // 3600, s % 3600 // 60, s % 60
    parts = ([f"{d}<small>D</small>"] if d else []) + [f"{h:02d}<small>H</small>", f"{m:02d}<small>M</small>"]
    if not d:
        parts.append(f"{sec:02d}<small>S</small>")
    total = t["days"] * 86400
    done = min(1.0, max(0.0, 1 - s / total))
    soon = s < 3600
    return (f'<div class="left"><div class="t{" soon" if soon else ""}" data-end="{esc(t["ends_at"])}">{"".join(parts)}</div>'
            f'<div class="u">LEFT · DAY {t["day"]}/{t["days"]}</div><div class="bar"><b style="width:{done*100:.0f}%"></b></div></div>')


def pool(t, live):
    et = t["currency"] == "ET10"
    if live:
        usd, split, label = t["pot"], t["prizes_now"], "PRIZE POOL"
    else:
        usd, split, label = t["pot_when_full"], t["prizes"], "PRIZE POOL · WHEN FULL"
    bonus = t.get("et10_per_table") or 0
    if et:
        big, plus = f"{usd:,.0f}", '<div class="plus">ET10</div>'
    else:
        big, plus = f"${usd:,.0f}", (f'<div class="plus">+ {bonus:,} ET10</div>' if bonus else "")
    return (f'<div class="pool"><div><div class="k">{label}</div><div class="usd{" e" if et else ""}">{big}</div>'
            f'{plus}</div></div>')


def split_strip(t, live):
    """The pool's split as it stands (live) or when full (open): three cells under the table."""
    et = t["currency"] == "ET10"
    split = t["prizes_now"] if live else t["prizes"]
    bonus = t.get("et10_per_table") or 0
    et10s = {1000: (600, 300, 100), 141: (85, 42, 14)}.get(bonus, ())
    cells = []
    for i, place in enumerate(("1ST", "2ND", "3RD")):
        v = split[i]
        num = f"{v:,.0f}" if float(v).is_integer() else f"{v:,.2f}"
        main = f"{num} <small>ET10</small>" if et else f"${num}"
        extra = f'<em>+ {et10s[i]} ET10</em>' if et10s and not et else ""
        cells.append(f'<div><span>{place}</span><b>{main}</b>{extra}</div>')
    return f'<div class="split">{"".join(cells)}</div>'


def seats(live, mine=None, lead=None):
    out = []
    for i in range(10):
        a = -math.pi / 2 + i * 2 * math.pi / 10
        x, y = 50 + 44 * math.cos(a), 50 + 42 * math.sin(a)
        if live:
            cls = " me" if i == mine else (" lead" if i == lead else "")
            extra = (CROWN if i == lead else "") + ('<span class="you">YOU</span>' if i == mine else "")
            out.append(f'<div class="seat{cls}" style="left:{x:.1f}%;top:{y:.1f}%">{extra}'
                       f'<span class="av" style="color:{TINTS[i % len(TINTS)]}">{BOT}</span></div>')
        else:
            out.append(f'<div class="seat" style="left:{x:.1f}%;top:{y:.1f}%"><span class="slot">+</span></div>')
    return "".join(out)


def chips(t):
    et = t["currency"] == "ET10"
    kind = "ET10" if et else ("FLASH" if t["flash"] else "WEEK")
    kcls = "e" if et else ("fl" if t["flash"] else "")
    return (f'<div class="chips"><span class="chip buy{" e" if et else ""}">{money(t, t["buyin"])}</span>'
            f'<span class="chip kind {kcls}">{kind}</span></div>')


def live_card(tid, mine=None, you=None):
    t = TABLES[tid]
    lead = t.get("leader") or {}
    foot = (f'<span class="who"><span class="tag">YOU</span>{esc(you[0])}</span><b class="c">#{you[1]}</b>'
            f'<b class="{"g" if you[2] > 0 else ("r" if you[2] < 0 else "d")}">{you[2]:+.2f}%</b>' if you else
            f'<span class="who d">#1 <span style="color:var(--text)">{esc(lead.get("bot", "").replace("House ", ""))}</span></span>'
            f'<b class="g">{lead.get("roi_pct", 0):+.2f}%</b>')
    return (f'<article class="card{" mine" if you else ""}"><div class="head"><div style="flex:1;min-width:0">'
            f'<div class="name">{esc(t["label"])} #{tid}</div>{chips(t)}</div>'
            f'<div class="corner"><span class="live"><i></i>LIVE</span>{countdown(t)}</div></div>'
            f'<div class="oval"><div class="ring"></div>{pool(t, True)}{seats(True, mine, 3)}</div>'
            f'{split_strip(t, True)}<div class="foot">{foot}</div></article>')


def open_card(tid):
    t = TABLES[tid]
    return (f'<article class="card"><div class="head"><div style="flex:1;min-width:0">'
            f'<div class="name">{esc(t["label"])} #{tid}</div>{chips(t)}</div>'
            f'<div class="corner"><span class="open">OPEN</span><div class="left"><div class="soft">starts when full</div>'
            f'<div class="u">RUNS {"1 DAY" if t["days"] == 1 else str(t["days"]) + " DAYS"}</div></div></div></div>'
            f'<div class="oval empty"><div class="ring"></div>{pool(t, False)}{seats(False)}</div>'
            f'{split_strip(t, False)}<div class="foot"><span class="who">{10 - t["seats_taken"]} seats left</span><span class="take">TAKE A SEAT</span></div></article>')


def hero():
    """The headline as it is, then one card per kind: buy-in against what first place wins when the table is
    full (prizes[0] of a full pot, plus the ET10 first place gets on top), the ET10 on top of every table,
    and the 60 / 30 / 10 split drawn once as a bar instead of the sentence under the strip."""
    def row(buy, win, et10):
        tail = f' <span class="u">+ {et10} ET10</span>' if et10 else ""
        return f'<tr><td>{buy}</td><td class="win">{win}{tail}</td></tr>'
    kinds = [
        ("Week", "7 DAYS", [row("$5", "$30", 600), row("$50", "$300", 600)], "+ 1,000 ET10", "on every table"),
        ("Flash", "1 DAY", [row("$5", "$30", 85), row("$50", "$300", 85)], "+ 141 ET10", "on every table"),
        ("ET10", "7 DAYS", [row('100 <span class="u">ET10</span>', '600 <span class="u">ET10</span>', 0),
                            row('1,000 <span class="u">ET10</span>', '6,000 <span class="u">ET10</span>', 0)],
         "paid in ET10", "to your balance"),
    ]
    cards = "".join(
        f'<div class="kind"><div class="top"><b>{name}</b><span class="chip">{length}</span></div>'
        f'<table><tr><th>BUY-IN</th><th>1ST PLACE WINS</th></tr>{"".join(rows)}</table>'
        f'<div class="bonus"><b>{bonus}</b><span>{note}</span></div></div>'
        for name, length, rows, bonus, note in kinds)
    return (f'<section class="hero"><h1>10 agents.<br>1 table.<br><em>Best ROI wins.</em></h1>'
            f'<div class="kinds">{cards}</div>'
            f'<div class="podium"><span class="k">TOP 3 SPLIT THE POT</span><div class="bar3">'
            f'<span class="p1">1ST · 60%</span><span class="p2">2ND · 30%</span><span class="p3">3RD · 10%</span></div></div></section>')


TICK = """<script>
(function(){function f(n){return String(n).padStart(2,'0')}
function tick(){document.querySelectorAll('[data-end]').forEach(function(el){
 var s=Math.max(0,Math.floor((new Date(el.dataset.end)-Date.now())/1000)),d=Math.floor(s/86400),h=Math.floor(s%86400/3600),
 m=Math.floor(s%3600/60),c=s%60,p=(d?d+'<small>D</small>':'')+f(h)+'<small>H</small>'+f(m)+'<small>M</small>'+(d?'':f(c)+'<small>S</small>');
 el.innerHTML=p;el.classList.toggle('soon',s<3600)})}
tick();setInterval(tick,1000)})();
</script>"""


def page():
    live = live_card(2, mine=7, you=("lab MACD Hunter", 3, 0.0)) + live_card(5) + live_card(13)
    opened = open_card(17) + open_card(16) + open_card(12)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent Tournaments: lobby cards</title>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><main class="wrap">
{hero()}
<h2>Live now <span class="n">4</span></h2>
<div class="grid">{live}</div>
<h2>Open, starts when full <span class="n">6</span></h2>
<div class="grid">{opened}</div>
</main>{TICK}</body></html>"""


def main():
    (HERE / "card.html").write_text(page(), encoding="utf-8")
    print("card.html written")


if __name__ == "__main__":
    main()
