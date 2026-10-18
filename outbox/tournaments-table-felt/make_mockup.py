"""Build table.html (this folder): the Agent Tournaments table, dressed as a real table.

The operator, 2026-10-18, on /agent-tournaments/table/2: "neni to takove puste? nechtelo by to nejake pozadi lepsi
nebo vice detailu u stolu? nejake chips nebo nevim. zkus vymyslet neco aby to bylo top"

So the oval keeps its ten seats in the live page's order and gains only pictures of numbers the page already has
(GET /api/v1/agent-tournaments/tables/2, saved as table2.json):

* one chip column in front of every seat, one chip per $50 of the bot's money now ($250 x (1 + ROI), at least
  one, at most ten), green when it is up and cyan otherwise -- no tags, no legend. Two earlier tries were turned
  down the same day: a tall $50 column with dashed red rings for losses ("to se mi moc nelibi ty chipy jak jsi
  udelal"), then casino piles in four denominations with a money tag, rank badges on all ten and a today's-trades
  ring round every avatar ("to je moc uz preplacane");
* the pot in the middle as a chip pile and ET10 coins, and the 1st / 2nd / 3rd prizes printed on the felt like
  betting spots instead of cards under the table (where the bottom seat's ROI ran into "2ND");
* felt, a padded rail, an overhead light and a floor under the table; no ELO line on the seats;
* the race under the table across the page's whole width ("a ten race nevidim nikde").

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
DENOMS = ((100, "#00ff88", "#e6edf7"), (25, "#00cfff", "#e6edf7"), (5, "#3b82f6", "#e6edf7"), (1, "#e6edf7", "#3b82f6"))

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


def chip(x, y, face, stripe, k=1.0):
    """One casino chip seen from slightly above: a shaded edge with stripes, a face with six rim spots and an inlay."""
    rx, ry, t = 19 * k, 7 * k, 5 * k
    body = (f'M{x - rx:.1f},{y:.1f} L{x - rx:.1f},{y + t:.1f} A{rx:.1f} {ry:.1f} 0 0 0 {x + rx:.1f},{y + t:.1f} '
            f'L{x + rx:.1f},{y:.1f} A{rx:.1f} {ry:.1f} 0 0 1 {x - rx:.1f},{y:.1f} Z')
    side = f'<path d="{body}" fill="{face}"/><path d="{body}" fill="#06090f" fill-opacity=".38"/>'
    stripes = "".join(
        f'<rect x="{x + f * rx - 1.6 * k:.1f}" y="{y + ry * math.sqrt(1 - f * f):.1f}" width="{3.2 * k:.1f}" height="{t:.1f}" '
        f'fill="{stripe}" fill-opacity=".9"/>' for f in (-0.78, -0.26, 0.26, 0.78))
    a, b = rx * .82, ry * .82
    c = math.pi * (3 * (a + b) - math.sqrt((3 * a + b) * (a + 3 * b)))
    top = (f'<ellipse cx="{x}" cy="{y:.1f}" rx="{rx:.1f}" ry="{ry:.1f}" fill="{face}"/>'
           f'<ellipse cx="{x}" cy="{y:.1f}" rx="{a:.1f}" ry="{b:.1f}" fill="none" stroke="{stripe}" stroke-width="{2.6 * k:.1f}" '
           f'stroke-dasharray="{c / 12:.2f} {c / 12:.2f}"/>'
           f'<ellipse cx="{x}" cy="{y:.1f}" rx="{rx * .52:.1f}" ry="{ry * .52:.1f}" fill="{face}" stroke="#06090f" '
           f'stroke-opacity=".35" stroke-width="{1 * k:.1f}"/>')
    return side + stripes + top


def pile(x, base, amount, k=1.0, cap=6):
    """The amount paid out greedily in $100 / $25 / $5 / $1 chips: one column per denomination, side by side."""
    cols, left = [], round(amount)
    for d, face, stripe in DENOMS:
        n, left = divmod(left, d)
        if n:
            cols.append((min(n, cap), face, stripe))
    if not cols:
        return ""
    gap = 40 * k
    x0 = x - gap * (len(cols) - 1) / 2
    out = []
    for i, (n, face, stripe) in enumerate(cols):
        cx = x0 + i * gap
        out.extend(chip(cx, base - j * 5.2 * k, face, stripe, k) for j in range(n))
    return "".join(out)


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
        badge = f'<span class="rk r{s["rank"]}">{s["rank"]}</span>' if s["rank"] <= 3 else ""
        tag = '<i class="you">YOU</i>' if mine else ""
        house = '<span class="h">H</span>' if s["house"] else ""
        roi_cls = "g" if roi > 0 else ("r" if roi < 0 else "d")
        plate = (f'<div class="plate {"up" if top else "down"}"><b>{tag}{esc(name)}{house}</b>'
                 f'<span class="{roi_cls}">{roi:+.2f}%</span></div>')
        avatars.append(f'<div class="{cls}" style="left:{x}px;top:{y}px">{CROWN if lead else ""}'
                       f'<span class="av" style="color:{col}"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" '
                       f'stroke-width="1.6" stroke-linecap="round">{icon}</svg></span>{badge}{plate}</div>')
        # the pile sits on the felt between the seat and the pot, its amount on a tag under it
        if top:
            sx, base = x, y + 92
        elif bottom:
            sx, base = x, y - 98
        else:
            sx, base = x + (134 if x < cx else -134), y + 4
        n = max(1, min(10, round(eq / 50)))
        face = "#00ff88" if roi > 0 else "#00cfff"
        chips.append("".join(chip(sx, base + 6 - j * 5.2, face, "#e6edf7") for j in range(n)))
    return "".join(avatars), "".join(chips), "".join(labels)


def pot():
    """The $100 as four $25 chips, and the ET10 beside it as a stack of coins."""
    usd = T["pot_usdc"]
    et10 = sum(T["et10_prizes"])
    chips = "".join(chip(0, 40 - j * 6.5, "#00cfff", "#e6edf7", 1.25) for j in range(min(8, round(usd / 25))))
    coins = "".join(
        f'<ellipse cx="0" cy="{40 - j * 6}" rx="17" ry="6.5" fill="#06090f" stroke="#00cfff" stroke-width="2"/>' for j in range(4))
    return (f'<div class="pot"><span class="k">PRIZE POOL</span>'
            f'<div class="row"><svg viewBox="-30 -4 60 56" class="pile">{chips}</svg>'
            f'<b>{money(usd)}</b></div>'
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
.box{position:relative;width:1340px;height:700px;margin:0 auto 10px}

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
.print{position:absolute;left:0;right:0;top:150px;text-align:center;font-family:'Archivo Black';font-size:12px;letter-spacing:.42em;
 color:rgba(0,255,136,.28)}

/* the pot and the prize spots */
.pot{position:absolute;left:50%;top:306px;transform:translate(-50%,-50%);text-align:center}
.pot .k{display:block;font-size:11px;letter-spacing:.3em;color:var(--dim2);font-weight:700}
.pot .row{display:flex;align-items:center;gap:6px;margin-top:2px}
.pot .row b{font-family:'Archivo Black';font-weight:400;font-size:72px;line-height:1.05;color:var(--green);text-shadow:0 0 26px rgba(0,255,136,.45)}
.pot .pile{width:64px;height:60px}.pot .coins{width:46px;height:60px}
.pot .et{font-size:15px;font-weight:700;color:var(--cyan)}
.spots{position:absolute;left:50%;top:384px;transform:translateX(-50%);display:flex;gap:18px}
.spot{width:130px;height:62px;border-radius:999px;text-align:center;padding-top:6px;background:rgba(6,9,15,.35);
 border:1.5px solid rgba(0,255,136,.45)}
.spot span{display:block;font-size:9.5px;letter-spacing:.24em;color:var(--dim2);font-weight:700}
.spot b{display:block;font-family:'Archivo Black';font-weight:400;font-size:18px;color:var(--green);line-height:1.2}
.spot em{display:block;font-style:normal;font-size:10px;color:var(--cyan);font-weight:700}
.spot.p1{border-color:var(--green);box-shadow:0 0 16px rgba(0,255,136,.25),inset 0 0 12px rgba(0,255,136,.12)}
.spot.p2{border-color:rgba(0,207,255,.7)}.spot.p3{border-color:rgba(59,130,246,.7)}

/* chips and the money now */
.chips{position:absolute;inset:0;width:1340px;height:700px;pointer-events:none;overflow:visible}
.eq{position:absolute;transform:translateX(-50%);font-size:12px;font-weight:700;white-space:nowrap;background:rgba(6,9,15,.85);
 border:1px solid var(--line3);border-radius:99px;padding:2px 9px;color:var(--text)}
.eq.g{border-color:rgba(0,255,136,.5)}.eq.r{border-color:rgba(255,68,68,.45)}

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
.key svg{width:30px;height:16px}
.key span:nth-child(4){margin-right:10px}

/* the race, across the whole width */
.race{margin-top:22px;background:var(--navy);border:1px solid var(--line2);border-radius:22px;padding:18px 16px 10px}
.rh{display:flex;align-items:center;gap:22px;padding:0 8px 6px}
.rh h2{font-family:'Archivo Black';font-weight:400;font-size:24px}
.lg{display:flex;gap:16px;font-size:11px;letter-spacing:.12em;color:var(--dim2);font-weight:700}
.lg span{display:flex;align-items:center;gap:7px}.lg i{width:16px;height:3px;border-radius:2px;display:block}
.lg i.me{background:var(--cyan)}.lg i.ld{background:var(--text)}.lg i.fd{background:var(--dim2)}
.togo{margin-left:auto;font-size:12px;color:var(--dim2)}.togo b{color:var(--cyan);font-size:14px}
.race svg{width:100%;height:auto;display:block}
.race .ax{font-family:'JetBrains Mono';font-size:11px;fill:#7f93ad}
.race .glow{filter:drop-shadow(0 0 5px rgba(0,207,255,.8))}
.tagme rect{fill:#00cfff}.tagme text{fill:#06090f;font-family:'JetBrains Mono';font-weight:700;font-size:13px}
.taglead rect{fill:#06090f;stroke:#7f93ad}.taglead text{fill:#e6edf7;font-family:'JetBrains Mono';font-weight:700;font-size:13px}
"""


def key():
    sw = "".join(f'<span><svg viewBox="-21 -9 42 22">{chip(0, 0, face, stripe)}</svg>${d}</span>' for d, face, stripe in DENOMS)
    return ('<div class="key">' + sw + '<span>pile = the bot\'s money now · it sat down with $250</span>'
            '<span><svg viewBox="0 0 16 16"><circle cx="8" cy="8" r="6" fill="none" stroke="#1e3050" stroke-width="2"/>'
            '<circle cx="8" cy="8" r="6" fill="none" stroke="#00cfff" stroke-width="2" stroke-dasharray="22 38" transform="rotate(-90 8 8)"/></svg>'
            "today's trades of 20</span></div>")


def race():
    """The live page's race lines (GET .../tables/2 "race"), stretched to the page's width: field grey, leader white,
    our seat cyan, the time left hatched."""
    r = T["race"]
    RW, RH, X0, X1, Y0, Y1 = 1336, 330, 64, 1320, 22, 292

    def X(v):
        return X0 + (v - r["x0"]) * (X1 - X0) / (r["x1"] - r["x0"])

    def Y(v):
        return Y0 + (v - r["y0"]) * (Y1 - Y0) / (r["y1"] - r["y0"])

    def pts(p):
        return " ".join(f"{X(float(a)):.1f},{Y(float(b)):.1f}" for a, b in (q.split(",") for q in p.split()))

    nx = X(r["now_x"])
    out = ['<defs><pattern id="hatch" width="8" height="8" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
           '<line x1="0" y1="0" x2="0" y2="8" stroke="#1e3050" stroke-width="2"/></pattern></defs>',
           f'<rect x="{nx:.1f}" y="{Y0}" width="{X1 - nx:.1f}" height="{Y1 - Y0}" fill="url(#hatch)" opacity=".8"/>']
    for g in r["grid"]:
        y = Y(g["y"])
        dash = ' stroke-dasharray="5 5"' if g["zero"] else ""
        out.append(f'<line x1="{X0}" x2="{X1}" y1="{y:.1f}" y2="{y:.1f}" stroke="{"#1e3050" if g["zero"] else "#16233a"}"{dash}/>'
                   f'<text x="{X0 - 12}" y="{y + 4:.1f}" text-anchor="end" class="ax">{esc(g["t"])}</text>')
    for tk in r["ticks"]:
        out.append(f'<text x="{X(tk["x"]):.1f}" y="{RH - 8}" text-anchor="middle" class="ax">{tk["t"]}</text>')
    out.append(f'<line x1="{nx:.1f}" x2="{nx:.1f}" y1="{Y0 - 6}" y2="{Y1}" stroke="#00cfff" stroke-opacity=".6"/>')
    lines = sorted(r["lines"], key=lambda ln: (ln["seat_id"] == MINE, ln["role"] == "leader"))
    for ln in lines:
        me, lead = ln["seat_id"] == MINE, ln["role"] == "leader"
        col, wid, op = ("#00cfff", 3, 1) if me else (("#e6edf7", 2.4, 1) if lead else ("#7f93ad", 1.3, .5))
        glow = ' class="glow"' if me else ""
        out.append(f'<polyline points="{pts(ln["points"])}" fill="none" stroke="{col}" stroke-width="{wid}" opacity="{op}"'
                   f' stroke-linejoin="round"{glow}/>')
        ey = Y(ln["end_y"])
        dot = "#00cfff" if me else ("#e6edf7" if lead else ("#ff4444" if ln["roi"] < 0 else "#7f93ad"))
        out.append(f'<circle cx="{nx:.1f}" cy="{ey:.1f}" r="{5 if me or lead else 3}" fill="{dot}"/>')
        if me or lead:
            name = ln["bot"].replace("House ", "")
            txt = f'YOU #{ln["rank"]} {ln["roi"]:+.2f}%' if me else f'#1 {name} {ln["roi"]:+.1f}%'
            w = 8.2 * len(txt) + 22
            cls = "tagme" if me else "taglead"
            out.append(f'<g class="{cls}"><rect x="{nx - w - 12:.1f}" y="{ey - 14:.1f}" width="{w:.1f}" height="28" rx="14"/>'
                       f'<text x="{nx - w / 2 - 12:.1f}" y="{ey + 4.5:.1f}" text-anchor="middle">{esc(txt)}</text></g>')
    s_left = max(0, int((datetime.fromisoformat(T["ends_at"]) - NOW).total_seconds()))
    togo = (f'{s_left // 86400}D {s_left % 86400 // 3600:02d}H' if s_left >= 86400
            else f'{s_left // 3600}H {s_left % 3600 // 60:02d}M')
    legend = ('<div class="lg"><span><i class="me"></i>YOU</span><span><i class="ld"></i>LEADER</span>'
              '<span><i class="fd"></i>FIELD</span></div>')
    return (f'<section class="race"><div class="rh"><h2>The race</h2>{legend}'
            f'<div class="togo"><b>{togo}</b> to go · {esc(r["ends"])}</div></div>'
            f'<svg viewBox="0 0 {RW} {RH}">{"".join(out)}</svg></section>')


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
<svg class="chips" viewBox="0 0 {W} {H}">{chips}</svg>{labels}{avatars}</div></section>
{race()}
</main></body></html>"""


def main():
    (HERE / "table.html").write_text(page(), encoding="utf-8")
    print("table.html written")


if __name__ == "__main__":
    main()
