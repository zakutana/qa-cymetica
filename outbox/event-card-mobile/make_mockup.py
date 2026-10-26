"""Build index.html and board.html (this folder): the Event Cards deck (/events) on a phone, in the new look, still a card.

The operator, 2026-10-26: on a phone /events is a card you swipe left and right, and that should stay; the new look of
/events/{id} (outbox/event-card-redesign, live since 2026-10-22) is clearer, "ale uz to neni karticka je to siroky panel"
-- at 390 px it is a 2,400 px page. Both URLs run the same deck (event-cards.js, .ec-stack); the detail page only adds
event-card-landing.css. So: the new look's parts, sized for a card that fits the screen.

Kept from today's phone deck, as they work: the card fills the screen with two cards' edges behind it; the card body
scrolls inside the card (today .ec-panel does, 790 in 619); swipe right = Buy (the card flies off and the Buy sheet
opens), swipe left = Skip; Back, Skip, Watch, Sell, Buy in a bar at the card's foot. Taken from the new look: the four
figures first (Since launch the largest), the big chart, no INFO / STATS tabs, the reworked items of
event-card-redesign/spec.txt 12 (no "$1.0683" under an index chart, no Share Price, "— not minted yet").
Changed, named in the answer: the first screen is the deck (the "Give this to your AI agent" block moves under it);
Buy is the rightmost button, under the thumb and the swipe; the left-swipe stamp reads SKIP (today it reads SELL).

Real figures: event-data.json (snapshot.py, Cymetica's public API). The operator's own -$0.07 on this card and his
$0.99 live buying power are read off his signed-in page on 2026-10-26.
Palette: the site's navy, cyan, green, red, blue. Fonts: Archivo Black and JetBrains Mono.
"""
from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
D = json.loads((HERE / "event-data.json").read_text(encoding="utf-8"))
CARD, PTS = D["card"], D["hist"]["points"]
READ = datetime.fromisoformat(D["read_at"])
esc = lambda s: html.escape(str(s), quote=True)

MY_PNL = "-$0.07"          # his position on this card, the red badge on his page
MY_POWER = "$0.99"         # "Live buying power: $0.99 on this card", his page


def pct(v):
    return f"{'+' if v >= 0 else '−'}{abs(v):.2f}%"


def since(c):
    return (c["current_index"] / c["index_base"] - 1) * 100


def launch(c):
    return datetime.fromisoformat(c["created_at"])


def structure(c):
    """"SAIB - Single AI Index Basket (SAIB)" as the new look prints it: "SAIB · Single AI Index Basket"."""
    name = (c.get("vehicle_structure_name") or c.get("vehicle_structure") or "").replace(f' ({c.get("vehicle_structure")})', "")
    return name.replace(" - ", " · ")


def ago(c):
    d = (READ - launch(c)).days
    return f"{d}d ago" if d else "today"


# ---------------------------------------------------------------- the chart: card index, last 24 hours
def chart():
    W, H, L, R, T, B = 342, 136, 30, 6, 12, 22
    xs = [datetime.fromisoformat(p["t"]).timestamp() for p in PTS]
    ys = [p["index"] for p in PTS]
    lo, hi = min(ys), max(ys)
    pad = (hi - lo) * .22 or 1
    lo, hi = lo - pad, hi + pad
    X = lambda t: L + (t - xs[0]) / (xs[-1] - xs[0]) * (W - L - R)
    Y = lambda v: T + (hi - v) / (hi - lo) * (H - T - B)
    line = " ".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in zip(xs, ys))
    area = f"{L},{H - B} {line} {X(xs[-1]):.1f},{H - B}"
    grid, v = "", int(lo) + 1
    step = 2 if hi - lo < 12 else 5
    v = (int(lo) // step + 1) * step
    while v < hi:
        grid += (f'<line x1="{L}" x2="{W - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="gl"/>'
                 f'<text x="{L - 6}" y="{Y(v) + 3.5:.1f}" text-anchor="end" class="ax">{v}</text>')
        v += step
    ticks = ""
    for k in range(4):
        t = xs[0] + (xs[-1] - xs[0]) * k / 3
        anchor = "start" if k == 0 else ("end" if k == 3 else "middle")
        ticks += f'<text x="{X(t):.1f}" y="{H - 6}" text-anchor="{anchor}" class="ax">{datetime.fromtimestamp(t, tz=READ.tzinfo):%H:%M}</text>'
    oy, ex, ey = Y(ys[0]), X(xs[-1]), Y(ys[-1])
    return (f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="Card index, last 24 hours"><defs>'
            '<linearGradient id="ar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#00cfff" stop-opacity=".32"/>'
            '<stop offset="1" stop-color="#00cfff" stop-opacity="0"/></linearGradient></defs>'
            f'{grid}<line x1="{L}" x2="{W - R}" y1="{oy:.1f}" y2="{oy:.1f}" class="open"/>'
            f'<text x="{W - R - 2}" y="{oy - 5:.1f}" text-anchor="end" class="ax op">24h open {ys[0]:.2f}</text>'
            f'<polygon points="{area}" fill="url(#ar)"/><polyline points="{line}" class="ln"/>{ticks}'
            f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="7" class="halo"/><circle cx="{ex:.1f}" cy="{ey:.1f}" r="3.6" class="dot"/>'
            f'<g transform="translate({ex - 58:.1f},{ey - 27:.1f})"><rect width="54" height="19" rx="9.5" class="tag"/>'
            f'<text x="27" y="13.4" text-anchor="middle" class="tagt">{ys[-1]:.2f}</text></g></svg>')


ICON = {
    "back": '<path d="M9 7 4 12l5 5M4 12h11a5 5 0 0 1 0 10h-2"/>',
    "skip": '<path d="M6 6l12 12M18 6 6 18"/>',
    "watch": '<path d="m12 3.5 2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z"/>',
    "sell": '<path d="M12 4v15M6 13l6 6 6-6"/>',
    "buy": '<path d="M12 20V5M6 11l6-6 6 6"/>',
}


def icon(name):
    return f'<svg viewBox="0 0 24 24" class="ic" aria-hidden="true">{ICON[name]}</svg>'


def face(c, full):
    """One card. The active card carries everything; a card behind shows only its top, which is all that shows."""
    s = since(c)
    sent = c.get("headline_sentiment_score") or 0
    head = (f'<div class="ban"><img src="{esc(c["image_url"])}" alt="">'
            + ('<div class="badges"><span class="pill live"><i></i>LIVE</span>'
               + ('<span class="pill">FEATURED</span>' if c.get("is_featured") else "") + '</div>')
            + (f'<span class="pnl" title="Your P&amp;L on this card">{MY_PNL}</span>' if full else "") + '</div>'
            f'<div class="row1"><span class="pill">{esc(structure(c))}</span>'
            f'<span class="vote" title="Upvote">▲ {c.get("upvotes", 0)}</span></div>'
            f'<h1 class="title">{esc(c["title"])}</h1>'
            f'<div class="meta"><span>streetinsider.com · {ago(c)}</span>'
            f'<span class="chip {"r" if sent < 0 else ("g" if sent > 0 else "")}" title="News sentiment">Sentiment {sent:+.2f}</span></div>'
            f'<div class="hero1 {"up" if s >= 0 else "down"}"><div><div class="k">Since launch</div><div class="v">{pct(s)}</div></div>'
            f'<div class="hs"><b>{c["index_base"]:.0f} → {c["current_index"]:.2f}</b><span>since {launch(c).day} {launch(c):%b}</span></div></div>')
    if not full:
        return head
    day = (PTS[-1]["index"] / PTS[0]["index"] - 1) * 100
    tiles = (f'<div class="tiles"><div><div class="k">Card index</div><div class="v">{c["current_index"]:.2f}</div><div class="s">base {c["index_base"]:.0f}</div></div>'
             f'<div><div class="k">1 day</div><div class="v {"g" if day > 0 else "r"}">{pct(day)}</div><div class="s">from {PTS[0]["index"]:.2f}</div></div>'
             f'<div><div class="k">Index price</div><div class="v">${c["pw_index"]:,.2f}</div><div class="s">launch ${c["pw_base"]:,.2f}</div></div></div>')
    ch = (f'<div class="chh"><span class="k">Card index · 24h</span><div class="tog"><span class="on">1d</span><span>5d</span><span>30d</span></div></div>{chart()}')
    sym = c.get("evcdx_symbol") or f'EVCDX-{c["basket"][0]["symbol"]}'
    split = "".join(f'<div class="srow"><b>{esc(a["symbol"])}</b><span class="bar"><b style="width:{a["weight"] * 100:.0f}%"></b></span>'
                    f'<span>{a["weight"] * 100:.0f}%</span><span class="d">$0.00</span></div>' for a in c["basket"])
    more = (f'<section class="sec" id="trade"><div class="alloc"><div class="k">Allocate from your balance</div>'
            f'<div class="bal">Live buying power: {MY_POWER} on this card</div>'
            '<div class="pc"><span class="on">0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span></div>'
            '<div class="amt">$0.00 · 0% of available</div><span class="buy">Buy</span></div>'
            f'<div class="split"><div class="sh"><span class="k">Per-asset split</span><a>Reset to card weights</a></div>{split}'
            '<span class="btn cy">+ Add asset</span></div></section>'
            f'<section class="sec"><div class="k">About this card</div><p class="about">{esc(c["summary"])}</p>'
            f'<div class="kv"><div><span class="k">Symbol</span><b>{esc(sym)}</b></div>'
            '<div><span class="k">Market cap</span><b class="d">— not minted yet</b></div></div></section>'
            '<div class="links"><span class="btn">History</span><span class="btn">Share</span><span class="btn">Embed</span></div>')
    return head + tiles + ch + more


def card_html(c, cls, full):
    stamps = ('<div class="stamp bull">BUY</div><div class="stamp skip">SKIP</div>') if full else ""
    bar = ('<nav class="actions">'
           f'<span class="act">{icon("back")}<em>Back</em></span>'
           f'<span class="act">{icon("skip")}<em>Skip</em></span>'
           f'<span class="act">{icon("watch")}<em>Watch</em></span>'
           f'<span class="act bear">{icon("sell")}<em>Sell</em></span>'
           f'<span class="act bull">{icon("buy")}<em>Buy</em></span></nav>')
    return f'<article class="card {cls}">{stamps}<div class="body">{face(c, full)}</div>{bar}</article>'


CSS = """
:root{--bg:#0a0e17;--deep:#06090f;--navy:#0d1520;--navy2:#111a28;--line:#16233a;--line2:#1a2a44;--line3:#1e3050;
--text:#e6edf7;--dim:#a9b8cc;--dim2:#7f93ad;--cyan:#00cfff;--green:#00ff88;--red:#ff4444;--blue:#3b82f6}
*{box-sizing:border-box;margin:0;padding:0}
html,body{height:100%;overflow:hidden;background:var(--bg);color:var(--text);font-family:'JetBrains Mono',monospace;font-size:13px;-webkit-font-smoothing:antialiased}
body{background:radial-gradient(ellipse 90% 40% at 20% -6%,rgba(0,207,255,.10),rgba(0,207,255,0) 70%),var(--bg)}
.g{color:var(--green)}.r{color:var(--red)}.d{color:var(--dim2)}
.k{font-size:9.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--dim2);font-weight:700}
/* the line above the deck: live, progress; the site's menu button sits at the right */
.top{position:absolute;top:0;left:0;right:0;height:52px;display:flex;align-items:center;gap:12px;padding:0 66px 0 16px}
.lv{display:flex;align-items:center;gap:7px;color:var(--cyan);font-size:11px;white-space:nowrap}.lv i{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 8px var(--green)}
.prog{margin-left:auto;display:flex;align-items:center;gap:8px;color:var(--dim);font-size:11px;font-weight:700;white-space:nowrap}
.prog i{display:block;width:46px;height:4px;border-radius:99px;background:var(--line3);overflow:hidden}.prog i b{display:block;height:100%;width:3%;background:var(--green)}
.menu{position:absolute;top:4px;right:10px;width:44px;height:44px;border-radius:50%;border:1px solid var(--line3);background:rgba(13,21,32,.92);display:grid;place-items:center}
.menu i{display:block;width:18px;height:2px;background:var(--cyan);border-radius:2px;box-shadow:0 -6px 0 var(--cyan),0 6px 0 var(--cyan)}
/* the deck */
.deck{position:absolute;top:54px;left:10px;right:10px;bottom:24px}
.card{position:absolute;inset:0;border-radius:24px;background:var(--navy);border:1px solid var(--line2);overflow:hidden;display:flex;flex-direction:column;
 box-shadow:0 0 0 1px rgba(0,207,255,.05),0 22px 44px rgba(0,0,0,.5);transform-origin:50% 100%}
.card.b1{transform:translateY(9px) scale(.955);background:var(--navy2);border-color:var(--line3)}
.card.b2{transform:translateY(18px) scale(.91);background:var(--navy2);border-color:var(--line2);box-shadow:none}
.card.b2 .body,.card.b2 .actions{visibility:hidden}
.body{flex:1;overflow-y:auto;padding:12px 14px 18px;scrollbar-width:none}.body::-webkit-scrollbar{display:none}
.ban{position:relative;height:118px;border-radius:16px;overflow:hidden;border:1px solid var(--line3);background:var(--deep)}
.ban img{width:100%;height:100%;object-fit:cover;object-position:50% 42%;display:block}
.badges{position:absolute;top:9px;right:9px;display:flex;gap:6px}
.pill{display:inline-flex;align-items:center;gap:6px;font-size:10px;font-weight:700;letter-spacing:.06em;border:1px solid rgba(0,207,255,.45);color:var(--cyan);border-radius:99px;padding:4px 10px;background:rgba(6,9,15,.82);white-space:nowrap}
.pill.live{color:var(--green);border-color:rgba(0,255,136,.5)}.pill.live i{width:6px;height:6px;border-radius:50%;background:var(--green);box-shadow:0 0 8px var(--green)}
.pnl{position:absolute;bottom:9px;right:9px;font-size:11px;font-weight:700;color:var(--red);border:1px solid rgba(255,68,68,.55);background:rgba(6,9,15,.86);border-radius:8px;padding:3px 8px}
.row1{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:12px}
.vote{display:inline-flex;align-items:center;gap:5px;border:1px solid var(--line3);border-radius:9px;padding:4px 10px;color:var(--dim);font-weight:700;font-size:11px}
.title{font-family:'Archivo Black',sans-serif;font-weight:400;font-size:22.5px;line-height:1.14;letter-spacing:-.005em;margin-top:11px;
 display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
.meta{display:flex;align-items:center;justify-content:space-between;gap:8px;margin-top:8px;color:var(--dim2);font-size:11px}
.chip{display:inline-flex;border:1px solid var(--line3);border-radius:99px;padding:3px 9px;font-size:10.5px;font-weight:700;white-space:nowrap;color:var(--dim)}
.chip.r{color:var(--red);border-color:rgba(255,68,68,.5)}.chip.g{color:var(--green);border-color:rgba(0,255,136,.5)}
.hero1{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:14px;border-radius:16px;padding:12px 15px;
 border:1px solid rgba(0,255,136,.55);background:linear-gradient(160deg,rgba(0,255,136,.14),rgba(0,255,136,.02) 70%),var(--deep);box-shadow:0 0 26px rgba(0,255,136,.12)}
.hero1 .v{font-family:'Archivo Black',sans-serif;font-size:40px;line-height:1.02;margin-top:4px;color:var(--green);text-shadow:0 0 22px rgba(0,255,136,.42)}
.hero1.down{border-color:rgba(255,68,68,.55);background:linear-gradient(160deg,rgba(255,68,68,.13),rgba(255,68,68,.02) 70%),var(--deep);box-shadow:0 0 26px rgba(255,68,68,.1)}
.hero1.down .v{color:var(--red);text-shadow:0 0 22px rgba(255,68,68,.4)}
.hs{text-align:right;font-size:11px;color:var(--dim2);line-height:1.6}.hs b{display:block;color:var(--dim);font-weight:700}
.tiles{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin-top:9px}
.tiles>div{background:var(--deep);border:1px solid var(--line2);border-radius:13px;padding:9px 10px;min-width:0}
.tiles .k{font-size:9px;letter-spacing:.08em;white-space:nowrap}
.tiles .v{font-size:16.5px;font-weight:700;margin-top:5px;white-space:nowrap}.tiles .s{font-size:10px;color:var(--dim2);margin-top:3px;white-space:nowrap}
.chh{display:flex;align-items:center;justify-content:space-between;margin-top:16px}
.tog{display:flex;gap:3px;background:var(--deep);border:1px solid var(--line2);border-radius:10px;padding:3px}
.tog span{min-width:40px;text-align:center;padding:6px 0;border-radius:7px;color:var(--dim2);font-weight:700;font-size:11.5px}.tog span.on{background:var(--navy2);color:var(--text);box-shadow:0 0 0 1px rgba(0,207,255,.35) inset}
.chart{width:100%;height:auto;display:block;margin-top:6px}
.chart .gl{stroke:var(--line2);stroke-width:1}
.chart .ax{font-family:'JetBrains Mono';font-size:9px;fill:#7f93ad}.chart .ax.op{fill:#a9b8cc}
.chart .open{stroke:#7f93ad;stroke-opacity:.55;stroke-dasharray:3 4;stroke-width:1}
.chart .ln{fill:none;stroke:#00cfff;stroke-width:2.2;stroke-linejoin:round;filter:drop-shadow(0 0 5px rgba(0,207,255,.5))}
.chart .halo{fill:#00cfff;fill-opacity:.22}.chart .dot{fill:#00cfff}.chart .tag{fill:#00cfff}.chart .tagt{fill:#06090f;font-family:'JetBrains Mono';font-weight:700;font-size:11px}
.sec{margin-top:18px}
.alloc{background:var(--deep);border:1px solid var(--line2);border-radius:16px;padding:14px}
.bal{margin:7px 0 11px;color:var(--cyan);font-weight:700;font-size:12px}
.pc{display:grid;grid-template-columns:repeat(5,1fr);gap:5px}
.pc span{text-align:center;border:1px solid var(--line3);border-radius:9px;padding:9px 0;color:var(--dim);font-weight:700;font-size:11.5px}.pc span.on{border-color:var(--cyan);color:var(--cyan)}
.amt{margin:11px 0;color:var(--dim);font-size:12px}
.buy{display:block;text-align:center;background:var(--green);color:var(--deep);font-weight:700;border-radius:12px;padding:12px;font-size:14px;box-shadow:0 0 18px rgba(0,255,136,.3)}
.split{margin-top:14px}.sh{display:flex;justify-content:space-between;align-items:center}.sh a{color:var(--cyan);font-size:11px;text-decoration:underline}
.srow{display:grid;grid-template-columns:52px 1fr 40px 46px;gap:9px;align-items:center;margin-top:10px;font-size:12px}
.srow .bar{height:7px;border-radius:99px;background:var(--line3);overflow:hidden}.srow .bar b{display:block;height:100%;background:linear-gradient(90deg,var(--cyan),var(--green))}
.btn{display:inline-flex;align-items:center;justify-content:center;gap:7px;border:1px solid var(--line3);background:var(--navy2);color:var(--dim);border-radius:10px;padding:9px 13px;font-size:12px;font-weight:700}
.btn.cy{border-color:rgba(0,207,255,.5);color:var(--cyan);margin-top:12px}
.about{color:var(--dim);line-height:1.65;font-size:12.5px;margin-top:8px}
.kv{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:12px}
.kv div{background:var(--deep);border:1px solid var(--line2);border-radius:12px;padding:10px 12px;min-width:0}.kv b{display:block;font-size:13px;margin-top:4px;color:var(--text);white-space:nowrap}.kv b.d{color:var(--dim)}
.links{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:16px}
/* the bar at the card's foot */
.actions{flex:none;display:grid;grid-template-columns:1fr 1fr 1fr 1.15fr 1.45fr;gap:7px;padding:10px 12px 12px;border-top:1px solid var(--line2);background:rgba(6,9,15,.55)}
.act{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;height:54px;border-radius:14px;border:1px solid var(--line3);background:var(--navy2);color:var(--dim)}
.act em{font-style:normal;font-size:10px;font-weight:700;letter-spacing:.1em;text-transform:uppercase}
.ic{width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.act.bear{color:var(--red);border-color:rgba(255,68,68,.6);background:rgba(255,68,68,.08)}
.act.bull{color:var(--deep);border-color:var(--green);background:var(--green);box-shadow:0 0 18px rgba(0,255,136,.35)}
/* swipe stamps (today .ec-stamp), shown while dragging */
.stamp{position:absolute;top:22px;z-index:3;font-family:'Archivo Black',sans-serif;font-size:30px;letter-spacing:.08em;border:3px solid;border-radius:12px;padding:2px 14px;opacity:0;background:rgba(6,9,15,.6)}
.stamp.bull{left:20px;color:var(--green);transform:rotate(-12deg)}.stamp.skip{right:20px;color:var(--dim);transform:rotate(12deg)}
/* the states the board pictures */
.swipe .card.a{transform:translateX(96px) rotate(5.3deg);border-color:var(--green);box-shadow:0 0 0 1px rgba(0,255,136,.5),0 0 44px rgba(0,255,136,.32),0 22px 44px rgba(0,0,0,.5)}
.swipe .card.a .stamp.bull{opacity:.95}
.swipe .card.b1{transform:translateY(5px) scale(.975)}
@media (max-height:760px){.ban{height:84px}.hero1 .v{font-size:34px}}
"""

BOARD_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#06090f;color:#e6edf7;font-family:'JetBrains Mono',monospace;padding:28px 32px 34px}
h1{font-family:'Archivo Black',sans-serif;font-weight:400;font-size:26px}h1 b{color:#00cfff;font-weight:400}
.sub{color:#7f93ad;font-size:13px;margin-top:6px}
.row{display:flex;gap:28px;margin-top:22px;align-items:flex-start}
.ph{width:390px}.ph .lab{font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#a9b8cc;margin-bottom:10px;height:16px}
.ph .lab b{color:#00ff88}.ph .lab.old{color:#7f93ad}
.ph iframe,.ph img{display:block;width:390px;height:844px;border:1px solid #1e3050;border-radius:28px;background:#0a0e17}
.ph .note{color:#7f93ad;font-size:11.5px;margin-top:10px;line-height:1.5}
"""


def page():
    c, behind = CARD, D["behind"]
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Event Cards on a phone</title>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<header class="top"><span class="lv"><i></i>Live · updated {READ:%H:%M} UTC</span><span class="prog">0 / {D["deck_size"]}<i><b></b></i></span></header>
<span class="menu" aria-label="Menu"><i></i></span>
<main class="deck">{card_html(behind[1], "b2", False) if len(behind) > 1 else ""}{card_html(behind[0], "b1", False) if behind else ""}{card_html(c, "a", True)}</main>
<script>
const s = new URLSearchParams(location.search).get('s') || 'rest';
document.body.classList.add(s);
if (s === 'scroll') {{ const b = document.querySelector('.card.a .body'); b.scrollTop = document.getElementById('trade').offsetTop - 14; }}
</script></body></html>"""


def board():
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Event Cards on a phone, today and new</title>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>{BOARD_CSS}</style></head><body>
<h1>EVENT<b>CARDS</b> · on a phone</h1>
<div class="sub">/events and /events/{{id}} at 390 × 844 · still one card you swipe · the new look's figures and chart inside it</div>
<div class="row">
<div class="ph"><div class="lab old">Today · /events (signed out)</div><img src="today-card.png" alt="">
 <div class="note">INFO / STATS tabs, figures on the second tab, chart at the bottom of the scroll</div></div>
<div class="ph"><div class="lab"><b>New</b> · the card</div><iframe src="index.html?s=rest"></iframe>
 <div class="note">Since launch, 1 day, index, price and the chart before any scroll</div></div>
<div class="ph"><div class="lab"><b>New</b> · swipe right = Buy</div><iframe src="index.html?s=swipe"></iframe>
 <div class="note">Right: Buy, the Buy sheet opens · Left: Skip</div></div>
<div class="ph"><div class="lab"><b>New</b> · scrolled inside the card</div><iframe src="index.html?s=scroll"></iframe>
 <div class="note">Allocate, per-asset split, about, symbol, market cap</div></div>
</div></body></html>"""


def main():
    (HERE / "index.html").write_text(page(), encoding="utf-8")
    (HERE / "board.html").write_text(board(), encoding="utf-8")
    day = (PTS[-1]["index"] / PTS[0]["index"] - 1) * 100
    print("written; since launch", pct(since(CARD)), "| 1 day", pct(day), "| index", f'{CARD["current_index"]:.2f}', "| price", CARD["pw_index"])


if __name__ == "__main__":
    main()
