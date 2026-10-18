"""Build table.html (this folder): the Agent Tournaments table, dressed as a real table.

The operator, 2026-10-18, on /agent-tournaments/table/2: "neni to takove puste? nechtelo by to nejake pozadi lepsi
nebo vice detailu u stolu? nejake chips nebo nevim. zkus vymyslet neco aby to bylo top"

So the oval keeps its ten seats in the live page's order and gains only pictures of numbers the page already has
(GET /api/v1/agent-tournaments/tables/2, saved as table2.json):

* a chip stack in front of every seat: the bot's money now, $250 x (1 + ROI), in $50 chips -- cyan up to the $250
  it started with, green above it, and the chips it lost drawn as dashed red rings;
* a ring round every avatar: today's trades out of the 20 a day (trades_today / daily_allowance);
* the pot in the middle as a chip pile and ET10 coins, and the 1st / 2nd / 3rd prizes printed on the felt like
  betting spots instead of cards under the table (where the bottom seat's ROI ran into "2ND");
* felt, a padded rail, an overhead light and a floor under the table; no ELO line on the seats.

Palette: the site's navy, cyan, green, red and blue, and the avatar tints the API itself serves.
"""
from __future__ import annotations

import html
import json
import math
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent
T = json.loads((HERE / "table2.json").read_text(encoding="utf-8"))
NOW = datetime.now(timezone.utc)
MINE = 1  # seat 1, "lab MACD Hunter", is the operator's bot (the live page tags it YOU when they are signed in)
CHIP = 50.0  # dollars per chip

# The oval box, in px: seat centres sit on the rail, clockwise from top centre (the live page's order).
W, H = 1340, 700
RAIL = (140, 110, 1200, 590)  # left, top, right, bottom
SEATS_XY = [(670, 110), (890, 110), (1157, 212), (1157, 488), (890, 590), (670, 590), (450, 590), (183, 488),
            (183, 212), (450, 110)]

BOTS = {
    "a": '<rect x="4" y="6" width="16" height="12" rx="4"/><circle cx="9" cy="12" r="1.6" fill="currentColor"/>'
         '<circle cx="15" cy="12" r="1.6" fill="currentColor"/><path d="M12 6V3"/><circle cx="12" cy="2.5" r="1" fill="currentColor"/>',
    "b": '<rect x="4" y="7" width="16" height="11" rx="5"/><rect x="7.5" y="10.5" width="9" height="4" rx="2"/>'
         '<path d="M8 7 6.5 4M16 7l1.5-3"/>',
    "c": '<rect x="4" y="6" width="16" height="12" rx="3"/><path d="M8 11h2M14 11h2M9 15h6"/><path d="M2 11v3M22 11v3"/>',
    "d": '<circle cx="12" cy="12" r="7"/><circle cx="12" cy="12" r="3"/><path d="M12 5V2.5M9.5 2.5h5"/>',
    "f": '<rect x="5" y="7" width="14" height="11" rx="4"/><path d="M3 10v5M21 10v5"/><circle cx="9.5" cy="12" r="1.4" fill="currentColor"/>'
         '<circle cx="14.5" cy="12" r="1.4" fill="currentColor"/><path d="M12 7V4"/>',
}
CROWN = '<svg class="crown" viewBox="0 0 16 10"><path d="M1 9 L2.5 2 L6 6 L8 1 L10 6 L13.5 2 L15 9 Z" fill="#00ff88"/></svg>'


def esc(s):
    return html.escape(str(s), quote=True)


def money(v):
    return f"${v:,.0f}" if abs(v - round(v)) < 0.005 else f"${v:,.2f}"


def chip(x, y, fill, ghost=False):
    """One chip seen from slightly above: an edge, a face, and the six spots round its rim."""
    if ghost:
        return (f'<ellipse cx="{x}" cy="{y}" rx="17" ry="6.2" fill="none" stroke="#ff4444" stroke-opacity=".55" '
                f'stroke-width="1.2" stroke-dasharray="3 3"/>')
    return (f'<ellipse cx="{x}" cy="{y + 2}" rx="17" ry="6.2" fill="{fill}" fill-opacity=".55"/>'
            f'<rect x="{x - 17}" y="{y}" width="34" height="2" fill="{fill}" fill-opacity=".55"/>'
            f'<ellipse cx="{x}" cy="{y}" rx="17" ry="6.2" fill="{fill}"/>'
            f'<ellipse cx="{x}" cy="{y}" rx="14.2" ry="5" fill="none" stroke="#e6edf7" stroke-width="1.6" '
            f'stroke-dasharray="3.2 4.2" stroke-opacity=".9"/>'
            f'<ellipse cx="{x}" cy="{y}" rx="8" ry="2.8" fill="none" stroke="#06090f" stroke-opacity=".35"/>')


def stack(x, base, equity, capital):
    """$50 chips, bottom up: cyan to the starting capital, green above it; lost chips as dashed red rings."""
    n = max(0, round(equity / CHIP))
    start = round(capital / CHIP)
    parts = []
    for k in range(max(n, start)):
        y = base - k * 6
        if k < n:
            parts.append(chip(x, y, "#00cfff" if k < start else "#00ff88"))
        else:
            parts.append(chip(x, y, "", ghost=True))
    return "".join(parts)


def allowance_ring(used, of):
    r, c = 37, 2 * math.pi * 37
    frac = min(1.0, used / of) if of else 0
    return (f'<svg class="ring" viewBox="0 0 84 84"><circle cx="42" cy="42" r="{r}" fill="none" stroke="#1e3050" stroke-width="3"/>'
            f'<circle cx="42" cy="42" r="{r}" fill="none" stroke="#00cfff" stroke-width="3" stroke-linecap="round" '
            f'stroke-dasharray="{frac * c:.1f} {c:.1f}" transform="rotate(-90 42 42)"/></svg>')


def seats():
    st = {s["seat_id"]: s for s in T["standings"]}
    cap = T["capital_usdc"]
    avatars, chips, labels = [], [], []
    cx, cy = W / 2, H / 2
    for i, seat in enumerate(T["seats"][:10]):
        x, y = SEATS_XY[i]
        s = st[seat["seat_id"]]
        roi = s["roi_pct"] or 0.0
        eq = cap * (1 + roi / 100)
        mine, lead = seat["seat_id"] == MINE, s["rank"] == 1
        name = s["bot"].replace("House ", "")
        col = seat["avatar"]["color"]
        icon = BOTS.get(seat["avatar"]["shape"], BOTS["b"])
        top = y < cy - 150
        bottom = y > cy + 150
        cls = "seat" + (" me" if mine else "") + (" lead" if lead else "")
        badge = f'<span class="rk r{s["rank"]}">{s["rank"]}</span>'
        tag = '<i class="you">YOU</i>' if mine else ""
        house = '<span class="h">H</span>' if s["house"] else ""
        roi_cls = "g" if roi > 0 else ("r" if roi < 0 else "d")
        plate = (f'<div class="plate {"up" if top else "down"}"><b>{tag}{esc(name)}{house}</b>'
                 f'<span class="{roi_cls}">{roi:+.2f}%</span></div>')
        avatars.append(f'<div class="{cls}" style="left:{x}px;top:{y}px">{CROWN if lead else ""}'
                       f'{allowance_ring(s["trades_today"], s["daily_allowance"])}'
                       f'<span class="av" style="color:{col}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                       f'stroke-width="1.6" stroke-linecap="round">{icon}</svg></span>{badge}{plate}</div>')
        # the stack sits on the felt between the seat and the pot
        if top:
            sx, base = x, y + 112
        elif bottom:
            sx, base = x, y - 52
        else:
            sx, base = x + (124 if x < cx else -124), y + 22
        chips.append(stack(sx, base, eq, cap))
        lx = sx + 26
        labels.append(f'<span class="eq {roi_cls}" style="left:{lx}px;top:{base - 8}px">{money(eq)}</span>')
    return "".join(avatars), "".join(chips), "".join(labels)


def pot():
    pile = "".join(chip(x, b - k * 5, "#00ff88") for x, b, n in ((-34, 30, 3), (0, 34, 4), (34, 30, 2)) for k in range(n))
    coins = "".join(
        f'<circle cx="{x}" cy="{y}" r="11" fill="#06090f" stroke="#00cfff" stroke-width="2"/>'
        f'<text x="{x}" y="{y + 3.5}" text-anchor="middle" font-family="JetBrains Mono" font-weight="700" font-size="9" fill="#00cfff">ET</text>'
        for x, y in ((-14, 22), (10, 26), (-2, 6)))
    usd = T["pot_usdc"]
    et10 = sum(T["et10_prizes"])
    return (f'<div class="pot"><span class="k">PRIZE POOL</span>'
            f'<div class="row"><svg viewBox="-56 -6 112 48" class="pile">{pile}</svg>'
            f'<b>{money(usd)}</b><svg viewBox="-30 -8 60 48" class="coins">{coins}</svg></div>'
            f'<span class="et">+ {et10:,} ET10</span></div>')


def spots():
    names = ("1ST", "2ND", "3RD")
    cls = ("p1", "p2", "p3")
    out = []
    for n, c, usd, et in zip(names, cls, T["prizes_now_usdc"], T["et10_prizes"]):
        out.append(f'<div class="spot {c}"><span>{n}</span><b>{money(usd)}</b><em>+ {et:,} ET10</em></div>')
    return '<div class="spots">' + "".join(out) + "</div>"


def countdown():
    end = datetime.fromisoformat(T["ends_at"])
    start = datetime.fromisoformat(T["starts_at"])
    s = max(0, int((end - NOW).total_seconds()))
    d, h, m = s // 86400, s % 86400 // 3600, s % 3600 // 60
    parts = ([(d, "D")] if d else []) + [(h, "H"), (m, "M")]
    t = "".join(f'{v:02d}<small>{u}</small>' if k else f'{v}<small>{u}</small>' for k, (v, u) in enumerate(parts))
    pct = max(0.0, min(100.0, (NOW - start).total_seconds() / (end - start).total_seconds() * 100))
    return (f'<div class="corner"><span class="live"><i></i>LIVE</span><div class="left"><div class="t">{t}</div>'
            f'<div class="u">LEFT · DAY {T["day"]}/{T["days"]}</div><div class="bar"><b style="width:{pct:.1f}%"></b></div></div></div>')


CSS = """
:root{--bg:#0a0e17;--deep:#06090f;--navy:#0d1520;--navy2:#111a28;--line:#16233a;--line2:#1a2a44;--line3:#1e3050;
--text:#e6edf7;--dim:#a9b8cc;--dim2:#7f93ad;--cyan:#00cfff;--green:#00ff88;--red:#ff4444;--blue:#3b82f6}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:var(--bg);color:var(--text);font-family:'JetBrains Mono',monospace;font-size:13px}
.g{color:var(--green)}.r{color:var(--red)}.d{color:var(--dim2)}
.wrap{max-width:1400px;margin:0 auto;padding:24px 16px 40px}
.top{display:flex;align-items:center;gap:14px;padding:0 4px 18px}
.back{width:38px;height:38px;border-radius:10px;border:1px solid var(--line3);display:grid;place-items:center;color:var(--cyan);font-size:18px}
.top h1{font-family:'Archivo Black';font-weight:400;font-size:34px}
.chip{font-size:12px;font-weight:700;letter-spacing:.06em;padding:4px 10px;border-radius:99px;border:1px solid var(--line3);color:var(--dim)}
.chip.buy{color:var(--bg);background:var(--green);border-color:var(--green);box-shadow:0 0 12px rgba(0,255,136,.35)}
.chip.kind{color:var(--blue);border-color:rgba(59,130,246,.6)}
.facts{font-size:12.5px;color:var(--dim);margin-left:6px}.facts b{color:var(--text)}
.corner{margin-left:auto;display:flex;align-items:center;gap:18px}
.live{display:inline-flex;align-items:center;gap:7px;font-size:12px;font-weight:700;letter-spacing:.12em;color:var(--green);
 border:1px solid var(--green);background:rgba(0,255,136,.1);border-radius:99px;padding:5px 11px;box-shadow:0 0 14px rgba(0,255,136,.45)}
.live i{width:8px;height:8px;border-radius:50%;background:var(--green);box-shadow:0 0 8px var(--green);animation:pulse 1.6s infinite}
@keyframes pulse{50%{opacity:.35}}
.left{text-align:right}
.left .t{font-family:'Archivo Black';font-size:30px;line-height:1;font-variant-numeric:tabular-nums}
.left .t small{font-family:'JetBrains Mono';font-weight:700;font-size:15px;color:var(--cyan);margin:0 8px 0 2px}
.left .t small:last-child{margin-right:0}
.left .u{font-size:10.5px;color:var(--dim2);letter-spacing:.14em;margin-top:6px}
.bar{height:4px;border-radius:99px;background:var(--line3);margin-top:7px;width:170px;margin-left:auto;overflow:hidden}
.bar b{display:block;height:100%;background:linear-gradient(90deg,var(--cyan),var(--green))}

/* the room */
.room{position:relative;border-radius:26px;overflow:hidden;border:1px solid var(--line2);
 background:radial-gradient(ellipse 55% 60% at 50% -8%,rgba(0,207,255,.16),rgba(0,207,255,0) 70%),
  radial-gradient(ellipse 70% 50% at 50% 108%,rgba(0,255,136,.07),rgba(0,255,136,0) 70%),var(--deep)}
.floor{position:absolute;left:-20%;right:-20%;bottom:-6%;height:62%;transform:perspective(520px) rotateX(62deg);transform-origin:bottom;
 background-image:linear-gradient(rgba(0,207,255,.10) 1px,rgba(0,207,255,0) 1px),linear-gradient(90deg,rgba(0,207,255,.10) 1px,rgba(0,207,255,0) 1px);
 background-size:56px 56px;-webkit-mask-image:linear-gradient(to top,rgba(6,9,15,1),rgba(6,9,15,0));mask-image:linear-gradient(to top,rgba(6,9,15,1),rgba(6,9,15,0))}
.beam{position:absolute;left:50%;top:0;width:900px;height:100%;transform:translateX(-50%);
 background:conic-gradient(from 180deg at 50% -10%,rgba(0,207,255,0) 160deg,rgba(0,207,255,.06) 172deg,rgba(0,207,255,.06) 188deg,rgba(0,207,255,0) 200deg)}
.box{position:relative;width:1340px;height:700px;margin:0 auto}

/* the table: shadow, padded rail, neon edge, felt, printed line */
.shadow{position:absolute;left:150px;right:150px;top:150px;bottom:40px;border-radius:999px;background:rgba(6,9,15,.9);filter:blur(28px)}
.rail{position:absolute;left:140px;top:110px;width:1060px;height:480px;border-radius:999px;
 background:linear-gradient(180deg,#1a2a44,#111a28 30%,#06090f);
 box-shadow:0 0 0 1px #1e3050,inset 0 2px 0 rgba(230,237,247,.10),inset 0 -6px 14px rgba(6,9,15,.8)}
.felt{position:absolute;inset:24px;border-radius:999px;overflow:hidden;
 background:radial-gradient(ellipse 60% 70% at 50% 42%,rgba(0,255,136,.16),rgba(0,207,255,.07) 45%,rgba(13,21,32,0) 80%),#0d1520;
 box-shadow:0 0 0 2px var(--green),0 0 22px rgba(0,255,136,.35),inset 0 0 50px rgba(6,9,15,.9)}
.felt:before{content:'';position:absolute;inset:0;opacity:.22;mix-blend-mode:overlay;
 background-image:url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='.9' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 .6 0'/></filter><rect width='160' height='160' filter='url(%23n)'/></svg>")}
.felt:after{content:'';position:absolute;inset:58px 70px;border-radius:999px;border:1.5px dashed rgba(0,255,136,.22)}
.print{position:absolute;left:0;right:0;top:150px;text-align:center;font-family:'Archivo Black';font-size:12px;letter-spacing:.42em;
 color:rgba(0,255,136,.28)}

/* the pot and the prize spots */
.pot{position:absolute;left:50%;top:330px;transform:translate(-50%,-50%);text-align:center}
.pot .k{display:block;font-size:11px;letter-spacing:.3em;color:var(--dim2);font-weight:700}
.pot .row{display:flex;align-items:center;gap:6px;margin-top:2px}
.pot .row b{font-family:'Archivo Black';font-weight:400;font-size:72px;line-height:1.05;color:var(--green);text-shadow:0 0 26px rgba(0,255,136,.45)}
.pot .pile{width:112px;height:48px}.pot .coins{width:60px;height:48px}
.pot .et{font-size:15px;font-weight:700;color:var(--cyan)}
.spots{position:absolute;left:50%;top:440px;transform:translateX(-50%);display:flex;gap:18px}
.spot{width:130px;height:62px;border-radius:999px;text-align:center;padding-top:6px;background:rgba(6,9,15,.35);
 border:1.5px solid rgba(0,255,136,.45)}
.spot span{display:block;font-size:9.5px;letter-spacing:.24em;color:var(--dim2);font-weight:700}
.spot b{display:block;font-family:'Archivo Black';font-weight:400;font-size:18px;color:var(--green);line-height:1.2}
.spot em{display:block;font-style:normal;font-size:10px;color:var(--cyan);font-weight:700}
.spot.p1{border-color:var(--green);box-shadow:0 0 16px rgba(0,255,136,.25),inset 0 0 12px rgba(0,255,136,.12)}
.spot.p2{border-color:rgba(0,207,255,.7)}.spot.p3{border-color:rgba(59,130,246,.7)}

/* chips and the money now */
.chips{position:absolute;inset:0;width:1340px;height:700px;pointer-events:none;overflow:visible}
.eq{position:absolute;font-size:12px;font-weight:700;white-space:nowrap;text-shadow:0 1px 2px #06090f}
.eq.d{color:var(--dim)}

/* the seats */
.seat{position:absolute;width:84px;height:84px;transform:translate(-50%,-50%);display:grid;place-items:center}
.seat .ring{position:absolute;inset:0;width:84px;height:84px}
.av{width:62px;height:62px;border-radius:50%;display:grid;place-items:center;border:2px solid currentColor;
 background:radial-gradient(circle at 50% 35%,#16233a,#06090f 75%);box-shadow:0 6px 16px rgba(6,9,15,.9)}
.av svg{width:30px;height:30px}
.seat.lead .av{box-shadow:0 0 0 3px var(--green),0 0 22px rgba(0,255,136,.7)}
.seat.me .av{box-shadow:0 0 0 3px var(--cyan),0 0 22px rgba(0,207,255,.8)}
.seat .crown{position:absolute;top:-14px;width:22px;height:14px;filter:drop-shadow(0 0 6px rgba(0,255,136,.8))}
.plate .you{font-style:normal;font-size:10px;font-weight:700;color:var(--bg);background:var(--cyan);border-radius:5px;padding:2px 6px;z-index:3}
.seat.me .crown{display:none}
.rk{position:absolute;right:2px;top:4px;width:22px;height:22px;border-radius:50%;display:grid;place-items:center;font-size:11px;font-weight:700;
 background:var(--navy2);border:1px solid var(--line3);color:var(--dim);z-index:2}
.rk.r1{background:var(--green);color:var(--bg);border:none}.rk.r2{background:var(--cyan);color:var(--bg);border:none}
.rk.r3{background:var(--blue);color:var(--bg);border:none}
.plate{position:absolute;left:50%;transform:translateX(-50%);display:flex;flex-direction:column;align-items:center;white-space:nowrap;
 background:rgba(6,9,15,.85);border:1px solid var(--line2);border-radius:9px;padding:3px 10px;z-index:2}
.plate.down{top:84px}.plate.up{bottom:84px}
.seat.me .plate{border-color:rgba(0,207,255,.6)}
.plate b{font-size:12.5px;display:flex;align-items:center;gap:6px}
.plate span{font-size:13px;font-weight:700}
.h{font-size:9px;font-weight:700;color:var(--dim2);border:1px solid var(--line3);border-radius:4px;padding:0 4px}

/* the key */
.key{display:flex;justify-content:center;gap:26px;padding:0 0 18px;font-size:11px;color:var(--dim2);position:relative}
.key span{display:flex;align-items:center;gap:7px}
.key svg{width:34px;height:16px}
"""


def key():
    return ('<div class="key">'
            f'<span><svg viewBox="-17 -8 34 16">{chip(0, 0, "#00cfff")}</svg>$50 · started with $250</span>'
            f'<span><svg viewBox="-17 -8 34 16">{chip(0, 0, "#00ff88")}</svg>won above it</span>'
            f'<span><svg viewBox="-17 -8 34 16">{chip(0, 0, "", ghost=True)}</svg>lost</span>'
            '<span><svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="6" fill="none" stroke="#1e3050" stroke-width="2"/>'
            '<circle cx="8" cy="8" r="6" fill="none" stroke="#00cfff" stroke-width="2" stroke-dasharray="22 38" transform="rotate(-90 8 8)"/></svg>'
            "today's trades of 20</span></div>")


def page():
    avatars, chips, labels = seats()
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent Tournaments: Pro #{T["id"]}</title>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><main class="wrap">
<div class="top"><span class="back">←</span><h1>{esc(T["label"])} #{T["id"]}</h1><span class="chip buy">{money(T["buyin_usdc"])}</span>
<span class="chip kind">{"FLASH" if T["flash"] else "WEEK"}</span>
<span class="facts"><b>{T["seats_taken"]}/10</b> seats · <b>{money(T["volume_usdc"])}</b> traded</span>{countdown()}</div>
<section class="room"><div class="beam"></div><div class="floor"></div>
<div class="box"><div class="shadow"></div>
<div class="rail"><div class="felt"></div></div>
{pot()}{spots()}
<svg class="chips" viewBox="0 0 {W} {H}">{chips}</svg>{labels}{avatars}</div>{key()}</section>
</main></body></html>"""


def main():
    (HERE / "table.html").write_text(page(), encoding="utf-8")
    print("table.html written")


if __name__ == "__main__":
    main()
