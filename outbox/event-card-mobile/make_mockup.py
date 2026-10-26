"""Build index.html and board.html (this folder): the Event Cards deck (/events) on a phone, still a card, and it never scrolls.

The operator, 2026-10-26: on a phone /events is a card you swipe left and right, and that stays. The new look of
/events/{id} (outbox/event-card-redesign) is clearer but is a 2,400 px page at 390 px. Round 1 of this folder drew the card
with everything the page holds and a scrolling body; his verdict: "moc informaci ... karta v zadnem pripade nesmi byt
scrollovatelna, na mobilu nikdo nechce scrollovat ... jen to co degen potrebuje videt, co nejmene textu".

So the face holds what a trader decides on, and nothing else: the card's picture with LIVE and the position's P&L,
the title, the news mood and age, SINCE LAUNCH (largest) and 1 DAY, the chart with 1d / 5d / 30d, and the bar
Back, Skip, Watch, Sell, Buy. It fits the screen whatever its height: the chart takes what is left.
Where the rest went (nothing is removed from the platform, only from the face):
  - allocation 0-100 %, amount, Paper | Live, Confirm: the Buy sheet, which a right swipe or Buy already opens
    (live template ec-buy-sheet-tpl: allocation, amount, mode, confirm), drawn in this look;
  - description, symbol, market cap, card index, index price, per-asset split, structure, upvote, History, Share,
    Embed: one more sheet behind an (i) on the picture. That sheet is new in the sense that the face has a button
    for it; its content is what the page holds today (outbox/event-card-redesign/spec.txt 5 to 7, 12).
Taken from the live deck as it is: two cards' edges behind, swipe right = Buy (the Buy sheet opens), swipe left =
Skip, the stamp while dragging, the bar at the foot, Buy rightmost under the thumb.

Real figures: event-data.json (snapshot.py, Cymetica's public API, read 2026-10-26). His own -$0.07 on this card and
the $100,000 paper balance are read off the page as he sees it.
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
PAPER = "$100,000.00"      # paper balance, as the page shows it


def pct(v):
    return f"{'+' if v >= 0 else '−'}{abs(v):.2f}%"


def since(c):
    return (c["current_index"] / c["index_base"] - 1) * 100


def launch(c):
    return datetime.fromisoformat(c["created_at"])


def ago(c):
    d = (READ - launch(c)).days
    return f"{d}d ago" if d else "today"


def structure(c):
    """"SAIB - Single AI Index Basket (SAIB)" as the new look prints it: "SAIB · Single AI Index Basket"."""
    name = (c.get("vehicle_structure_name") or c.get("vehicle_structure") or "").replace(f' ({c.get("vehicle_structure")})', "")
    return name.replace(" - ", " · ")


def sentiment(c):
    s = c.get("headline_sentiment_score") or 0
    word = "Positive" if s > 0.05 else ("Negative" if s < -0.05 else "Neutral")
    return word, f"{s:+.2f}".replace("-", "−"), ("g" if s > 0.05 else ("r" if s < -0.05 else ""))


# ---------------------------------------------------------------- the chart: card index, last 24 hours, no text inside
def chart():
    """The line and its fill are an svg stretched to whatever height is left; the last value and its dot are html, so
    stretching cannot squash them."""
    xs = [datetime.fromisoformat(p["t"]).timestamp() for p in PTS]
    ys = [p["index"] for p in PTS]
    lo, hi = min(ys), max(ys)
    pad = (hi - lo) * .14 or 1
    lo, hi = lo - pad, hi + pad
    X = lambda t: (t - xs[0]) / (xs[-1] - xs[0]) * 100
    Y = lambda v: (hi - v) / (hi - lo) * 100
    line = " ".join(f"{X(x):.2f},{Y(y):.2f}" for x, y in zip(xs, ys))
    area = f"0,100 {line} 100,100"
    grid = "".join(f'<line x1="0" x2="100" y1="{g}" y2="{g}" class="gl"/>' for g in (25, 50, 75))
    oy = Y(ys[0])
    return (f'<div class="plot"><svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><defs>'
            '<linearGradient id="ar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#00cfff" stop-opacity=".34"/>'
            '<stop offset="1" stop-color="#00cfff" stop-opacity="0"/></linearGradient></defs>'
            f'{grid}<line x1="0" x2="100" y1="{oy:.2f}" y2="{oy:.2f}" class="open"/>'
            f'<polygon points="{area}" fill="url(#ar)"/><polyline points="{line}" class="ln"/></svg>'
            f'<span class="olab" style="top:{oy:.2f}%">{ys[0]:.2f}</span>'
            f'<span class="dot" style="top:{Y(ys[-1]):.2f}%"></span>'
            f'<span class="tagv" style="top:{Y(ys[-1]):.2f}%">{ys[-1]:.2f}</span></div>')


ICON = {
    "back": '<path d="M9 7 4 12l5 5M4 12h11a5 5 0 0 1 0 10h-2"/>',
    "skip": '<path d="M6 6l12 12M18 6 6 18"/>',
    "watch": '<path d="m12 3.5 2.6 5.3 5.9.9-4.3 4.1 1 5.8L12 16.9l-5.2 2.7 1-5.8-4.3-4.1 5.9-.9z"/>',
    "sell": '<path d="M12 4v15M6 13l6 6 6-6"/>',
    "buy": '<path d="M12 20V5M6 11l6-6 6 6"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.01"/>',
}


def icon(name):
    return f'<svg viewBox="0 0 24 24" class="ic" aria-hidden="true">{ICON[name]}</svg>'


def face(c, full):
    """One card. The active card carries everything; a card behind shows only its top, which is all that shows."""
    s = since(c)
    word, num, tone = sentiment(c)
    head = (f'<div class="ban"><img src="{esc(c["image_url"])}" alt="">'
            + ('<span class="info" aria-label="Details">' + icon("info") + '</span>' if full else "")
            + (f'<span class="pnl" title="Your P&amp;L on this card">{MY_PNL}</span>' if full else "") + '</div>'
            f'<h1 class="title">{esc(c["title"])}</h1>'
            f'<div class="meta"><span class="pill live"><i></i>LIVE</span><span class="chip {tone}">{word} {num}</span><span class="age">{ago(c)}</span></div>')
    if not full:
        return head
    day = (PTS[-1]["index"] / PTS[0]["index"] - 1) * 100
    figs = (f'<div class="figs"><div class="hero1 {"up" if s >= 0 else "down"}"><div class="k">Since launch</div><div class="v">{pct(s)}</div></div>'
            f'<div class="fig2"><div class="k">1 day</div><div class="v {"g" if day > 0 else "r"}">{pct(day)}</div></div></div>')
    ch = (f'<div class="chart"><div class="tog"><span class="on">1d</span><span>5d</span><span>30d</span></div>{chart()}</div>')
    return head + figs + ch


def card_html(c, cls, full):
    stamps = ('<div class="stamp bull">BUY</div><div class="stamp skip">SKIP</div>') if full else ""
    bar = ('<nav class="actions">'
           f'<span class="act">{icon("back")}</span>'
           f'<span class="act">{icon("skip")}</span>'
           f'<span class="act">{icon("watch")}</span>'
           f'<span class="act bear">{icon("sell")}<em>Sell</em></span>'
           f'<span class="act bull">{icon("buy")}<em>Buy</em></span></nav>')
    return f'<article class="card {cls}">{stamps}<div class="body">{face(c, full)}</div>{bar}</article>'


def buy_sheet(c):
    return ('<div class="scrim"></div><section class="sheet" id="buy"><i class="grab"></i>'
            f'<div class="sh1"><b>Buy</b><span class="d">{esc(c["title"].split(" — ")[0])} · index {c["current_index"]:.2f}</span></div>'
            '<div class="seg2"><span class="on">Paper</span><span>Live</span></div>'
            f'<div class="avail">{PAPER} available</div>'
            '<div class="pc"><span class="on">0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span></div>'
            '<div class="amt">$0.00</div>'
            '<span class="buy">Confirm Buy</span><span class="cancel">Cancel</span></section>')


def info_sheet(c):
    sym = c.get("evcdx_symbol") or f'EVCDX-{c["basket"][0]["symbol"]}'
    split = "".join(f'<div class="srow"><b>{esc(a["symbol"])}</b><span class="bar"><b style="width:{a["weight"] * 100:.0f}%"></b></span>'
                    f'<span>{a["weight"] * 100:.0f}%</span></div>' for a in c["basket"])
    return ('<div class="scrim"></div><section class="sheet" id="more"><i class="grab"></i>'
            f'<div class="sh1"><span class="pill">{esc(structure(c))}</span><span class="vote">▲ {c.get("upvotes", 0)}</span></div>'
            f'<p class="about">{esc(c["summary"])}</p>'
            '<div class="kv">'
            f'<div><span class="k">Card index</span><b>{c["current_index"]:.2f}</b><i>base {c["index_base"]:.0f}</i></div>'
            f'<div><span class="k">Index price</span><b>${c["pw_index"]:,.2f}</b><i>launch ${c["pw_base"]:,.2f}</i></div>'
            f'<div><span class="k">Symbol</span><b>{esc(sym)}</b></div>'
            '<div><span class="k">Market cap</span><b class="d">— not minted yet</b></div></div>'
            f'<div class="split"><span class="k">Per-asset split</span>{split}</div>'
            '<div class="links"><span class="btn">History</span><span class="btn">Share</span><span class="btn">Embed</span></div></section>')


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
.lv{display:flex;align-items:center;gap:7px;color:var(--cyan);font-size:11px;font-weight:700;letter-spacing:.1em;white-space:nowrap}.lv i{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 8px var(--green)}
.prog{margin-left:auto;display:flex;align-items:center;gap:8px;color:var(--dim);font-size:11px;font-weight:700;white-space:nowrap}
.prog i{display:block;width:60px;height:4px;border-radius:99px;background:var(--line3);overflow:hidden}.prog i b{display:block;height:100%;width:3%;background:var(--green)}
.menu{position:absolute;top:4px;right:10px;width:44px;height:44px;border-radius:50%;border:1px solid var(--line3);background:rgba(13,21,32,.92);display:grid;place-items:center}
.menu i{display:block;width:18px;height:2px;background:var(--cyan);border-radius:2px;box-shadow:0 -6px 0 var(--cyan),0 6px 0 var(--cyan)}
/* the deck */
.deck{position:absolute;top:54px;left:10px;right:10px;bottom:24px}
.card{position:absolute;inset:0;border-radius:26px;background:var(--navy);border:1px solid var(--line2);overflow:hidden;display:flex;flex-direction:column;
 box-shadow:0 0 0 1px rgba(0,207,255,.05),0 22px 44px rgba(0,0,0,.5);transform-origin:50% 100%}
.card.b1{transform:translateY(9px) scale(.955);background:var(--navy2);border-color:var(--line3)}
.card.b2{transform:translateY(18px) scale(.91);background:var(--navy2);border-color:var(--line2);box-shadow:none}
.card.b2 .body,.card.b2 .actions{visibility:hidden}
.body{flex:1;min-height:0;display:flex;flex-direction:column;padding:12px 14px 12px;overflow:hidden}
.ban{position:relative;flex:none;height:clamp(72px,13vh,112px);border-radius:16px;overflow:hidden;border:1px solid var(--line3);background:var(--deep)}
.ban img{width:100%;height:100%;object-fit:cover;object-position:50% 52%;display:block}
.pill{display:inline-flex;align-items:center;gap:6px;font-size:10px;font-weight:700;letter-spacing:.06em;border:1px solid rgba(0,207,255,.45);color:var(--cyan);border-radius:99px;padding:4px 10px;background:rgba(6,9,15,.82);white-space:nowrap}
.pill.live{color:var(--green);border-color:rgba(0,255,136,.5)}.pill.live i{width:6px;height:6px;border-radius:50%;background:var(--green);box-shadow:0 0 8px var(--green)}
.info{position:absolute;top:6px;right:6px;width:36px;height:36px;border-radius:50%;background:rgba(6,9,15,.82);border:1px solid var(--line3);display:grid;place-items:center;color:var(--dim)}
.info .ic{width:19px;height:19px}
.pnl{position:absolute;bottom:9px;right:9px;font-size:11px;font-weight:700;color:var(--red);border:1px solid rgba(255,68,68,.55);background:rgba(6,9,15,.86);border-radius:8px;padding:3px 8px}
.title{flex:none;font-family:'Archivo Black',sans-serif;font-weight:400;font-size:21px;line-height:1.14;margin-top:11px;
 display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.meta{flex:none;display:flex;align-items:center;gap:8px;margin-top:9px;color:var(--dim2);font-size:11px}.meta .age{margin-left:auto}
.meta .pill{background:transparent;padding:3px 10px}
.chip{display:inline-flex;border:1px solid var(--line3);border-radius:99px;padding:3px 10px;font-size:10.5px;font-weight:700;white-space:nowrap;color:var(--dim)}
.chip.r{color:var(--red);border-color:rgba(255,68,68,.5)}.chip.g{color:var(--green);border-color:rgba(0,255,136,.5)}
.figs{flex:none;display:grid;grid-template-columns:1.5fr 1fr;gap:9px;margin-top:12px}
.hero1,.fig2{border-radius:16px;padding:11px 14px;min-width:0}
.hero1{border:1px solid rgba(0,255,136,.55);background:linear-gradient(160deg,rgba(0,255,136,.14),rgba(0,255,136,.02) 70%),var(--deep);box-shadow:0 0 26px rgba(0,255,136,.12)}
.hero1 .v{font-family:'Archivo Black',sans-serif;font-size:37px;line-height:1.02;margin-top:5px;color:var(--green);text-shadow:0 0 22px rgba(0,255,136,.42);white-space:nowrap}
.hero1.down{border-color:rgba(255,68,68,.55);background:linear-gradient(160deg,rgba(255,68,68,.13),rgba(255,68,68,.02) 70%),var(--deep)}
.hero1.down .v{color:var(--red);text-shadow:0 0 22px rgba(255,68,68,.4)}
.fig2{background:var(--deep);border:1px solid var(--line2)}.fig2 .v{font-size:21px;font-weight:700;margin-top:9px;white-space:nowrap}
/* the chart takes whatever height is left, so the card never needs a scroll */
.chart{flex:1;min-height:90px;display:flex;flex-direction:column;margin-top:12px}
.tog{flex:none;align-self:flex-end;display:flex;gap:3px;background:var(--deep);border:1px solid var(--line2);border-radius:10px;padding:3px}
.tog span{min-width:40px;text-align:center;padding:6px 0;border-radius:7px;color:var(--dim2);font-weight:700;font-size:11.5px}.tog span.on{background:var(--navy2);color:var(--text);box-shadow:0 0 0 1px rgba(0,207,255,.35) inset}
.plot{position:relative;flex:1;min-height:0;margin-top:4px;margin-right:68px}
.plot svg{position:absolute;inset:6px 0 6px 0;width:100%;height:calc(100% - 12px);overflow:visible}
.plot .gl{stroke:var(--line2);stroke-width:1;vector-effect:non-scaling-stroke}
.plot .open{stroke:#7f93ad;stroke-opacity:.6;stroke-dasharray:3 4;stroke-width:1;vector-effect:non-scaling-stroke}
.plot .ln{fill:none;stroke:#00cfff;stroke-width:2.4;stroke-linejoin:round;vector-effect:non-scaling-stroke;filter:drop-shadow(0 0 5px rgba(0,207,255,.5))}
.plot .olab,.plot .tagv,.plot .dot{position:absolute;transform:translateY(-50%)}
.plot .olab{left:0;margin-top:6px;font-size:9.5px;color:var(--dim2)}
.plot .dot{right:0;width:9px;height:9px;margin-right:-4.5px;border-radius:50%;background:var(--cyan);box-shadow:0 0 0 5px rgba(0,207,255,.22)}
.plot .tagv{left:100%;margin-left:12px;background:var(--cyan);color:var(--deep);font-weight:700;font-size:11.5px;border-radius:99px;padding:3px 9px}
/* the bar at the card's foot */
.actions{flex:none;display:grid;grid-template-columns:1fr 1fr 1fr 1.4fr 1.8fr;gap:7px;padding:10px 12px 12px;border-top:1px solid var(--line2);background:rgba(6,9,15,.55)}
.act{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;height:56px;border-radius:15px;border:1px solid var(--line3);background:var(--navy2);color:var(--dim)}
.act em{font-style:normal;font-size:10.5px;font-weight:700;letter-spacing:.1em;text-transform:uppercase}
.ic{width:21px;height:21px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.act.bear{color:var(--red);border-color:rgba(255,68,68,.6);background:rgba(255,68,68,.08)}
.act.bull{color:var(--deep);border-color:var(--green);background:var(--green);box-shadow:0 0 18px rgba(0,255,136,.35)}
/* swipe stamps (today .ec-stamp), shown while dragging */
.stamp{position:absolute;top:22px;z-index:3;font-family:'Archivo Black',sans-serif;font-size:30px;letter-spacing:.08em;border:3px solid;border-radius:12px;padding:2px 14px;opacity:0;background:rgba(6,9,15,.6)}
.stamp.bull{left:20px;color:var(--green);transform:rotate(-12deg)}.stamp.skip{right:20px;color:var(--dim);transform:rotate(12deg)}
/* sheets: the Buy sheet (a right swipe or Buy opens it today) and the details behind the (i) */
.scrim{position:absolute;inset:0;background:rgba(6,9,15,.72);z-index:5;display:none}
.sheet{position:absolute;left:0;right:0;bottom:0;z-index:6;display:none;background:var(--navy);border:1px solid var(--line3);border-bottom:none;border-radius:26px 26px 0 0;padding:10px 16px 22px;box-shadow:0 -20px 50px rgba(0,0,0,.55)}
.grab{display:block;width:42px;height:4px;border-radius:9px;background:var(--line3);margin:0 auto 14px}
.sh1{display:flex;align-items:center;justify-content:space-between;gap:10px}.sh1 b{font-family:'Archivo Black',sans-serif;font-weight:400;font-size:24px}
.vote{display:inline-flex;border:1px solid var(--line3);border-radius:9px;padding:4px 10px;color:var(--dim);font-weight:700;font-size:11px}
.seg2{display:flex;gap:4px;background:var(--deep);border:1px solid var(--line2);border-radius:12px;padding:4px;margin-top:14px}
.seg2 span{flex:1;text-align:center;padding:10px 0;border-radius:9px;color:var(--dim2);font-weight:700;font-size:12.5px}.seg2 span.on{background:var(--navy2);color:var(--cyan);box-shadow:0 0 0 1px rgba(0,207,255,.4) inset}
.avail{margin-top:12px;color:var(--cyan);font-weight:700;font-size:12.5px}
.pc{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-top:10px}
.pc span{text-align:center;border:1px solid var(--line3);border-radius:10px;padding:12px 0;color:var(--dim);font-weight:700;font-size:12.5px}.pc span.on{border-color:var(--cyan);color:var(--cyan)}
.amt{margin:16px 0 16px;text-align:center;font-family:'Archivo Black',sans-serif;font-size:40px}
.buy{display:block;text-align:center;background:var(--green);color:var(--deep);font-weight:700;border-radius:14px;padding:16px;font-size:16px;box-shadow:0 0 22px rgba(0,255,136,.32)}
.cancel{display:block;text-align:center;margin-top:12px;color:var(--dim2);font-weight:700;font-size:12.5px}
.about{color:var(--dim);line-height:1.6;font-size:12.5px;margin-top:14px}
.kv{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:14px}
.kv div{background:var(--deep);border:1px solid var(--line2);border-radius:12px;padding:10px 12px;min-width:0}.kv b{display:block;font-size:14px;margin-top:5px;color:var(--text);white-space:nowrap}.kv b.d{color:var(--dim)}.kv i{display:block;font-style:normal;font-size:10px;color:var(--dim2);margin-top:3px}
.split{margin-top:14px}.srow{display:grid;grid-template-columns:56px 1fr 40px;gap:10px;align-items:center;margin-top:9px;font-size:12px}
.srow .bar{height:7px;border-radius:99px;background:var(--line3);overflow:hidden}.srow .bar b{display:block;height:100%;background:linear-gradient(90deg,var(--cyan),var(--green))}
.links{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:16px}
.btn{display:inline-flex;align-items:center;justify-content:center;border:1px solid var(--line3);background:var(--navy2);color:var(--dim);border-radius:10px;padding:11px 0;font-size:12px;font-weight:700}
/* the states the board pictures */
.swipe .card.a{transform:translateX(96px) rotate(5.3deg);border-color:var(--green);box-shadow:0 0 0 1px rgba(0,255,136,.5),0 0 44px rgba(0,255,136,.32),0 22px 44px rgba(0,0,0,.5)}
.swipe .card.a .stamp.bull{opacity:.95}
.swipe .card.b1{transform:translateY(5px) scale(.975)}
.buy-open .card.a,.more-open .card.a{}
.buy-open .card.a{display:none}.buy-open .card.b1{transform:none}.buy-open .card.b2{transform:translateY(9px) scale(.955)}
.buy-open .scrim,.buy-open #buy,.more-open .scrim,.more-open #more{display:block}
@media (max-height:700px){.ban img{object-position:50% 64%}.title{font-size:19px}.hero1 .v{font-size:32px}.act{height:50px}}
/* opened on a computer: the phone, 390 x 844, in the middle of the window */
@media (min-width:600px){html{height:auto;overflow:auto;background:#06090f}
 body{position:relative;width:390px;height:844px;margin:24px auto;border:1px solid var(--line3);border-radius:34px;overflow:hidden}}
"""

BOARD_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#06090f;color:#e6edf7;font-family:'JetBrains Mono',monospace;padding:28px 32px 34px}
h1{font-family:'Archivo Black',sans-serif;font-weight:400;font-size:26px}h1 b{color:#00cfff;font-weight:400}
.sub{color:#7f93ad;font-size:13px;margin-top:6px}
.row{display:flex;gap:26px;margin-top:22px;align-items:flex-start}
.ph{width:390px;flex:none}.ph .lab{font-size:12px;font-weight:700;letter-spacing:.12em;text-transform:uppercase;color:#a9b8cc;margin-bottom:10px;height:16px}
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
<header class="top"><span class="lv"><i></i>LIVE</span><span class="prog">0 / {D["deck_size"]}<i><b></b></i></span></header>
<span class="menu" aria-label="Menu"><i></i></span>
<main class="deck">{card_html(behind[1], "b2", False) if len(behind) > 1 else ""}{card_html(behind[0], "b1", False) if behind else ""}{card_html(c, "a", True)}
{buy_sheet(c)}{info_sheet(c)}</main>
<script>
const s = new URLSearchParams(location.search).get('s') || 'rest';
document.body.classList.add(s === 'buy' ? 'buy-open' : s === 'info' ? 'more-open' : s);
</script></body></html>"""


def board():
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Event Cards on a phone, today and new</title>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>{BOARD_CSS}</style></head><body>
<h1>EVENT<b>CARDS</b> · on a phone</h1>
<div class="sub">/events at 390 × 844 · one card you swipe · it never scrolls</div>
<div class="row">
<div class="ph"><div class="lab old">Today · /events (signed out)</div><img src="today-card.png" alt="">
 <div class="note">INFO / STATS tabs, a scrolling body, figures on the second tab</div></div>
<div class="ph"><div class="lab"><b>New</b> · the card</div><iframe src="index.html?s=rest"></iframe>
 <div class="note">All of it on one face; the chart takes the height that is left</div></div>
<div class="ph"><div class="lab"><b>New</b> · swipe right</div><iframe src="index.html?s=swipe"></iframe>
 <div class="note">Right: Buy sheet opens · Left: Skip</div></div>
<div class="ph"><div class="lab"><b>New</b> · Buy sheet</div><iframe src="index.html?s=buy"></iframe>
 <div class="note">Where the allocation went</div></div>
<div class="ph"><div class="lab"><b>New</b> · (i) details</div><iframe src="index.html?s=info"></iframe>
 <div class="note">Description, symbol, market cap, split, History, Share, Embed</div></div>
</div></body></html>"""


def main():
    (HERE / "index.html").write_text(page(), encoding="utf-8")
    (HERE / "board.html").write_text(board(), encoding="utf-8")
    day = (PTS[-1]["index"] / PTS[0]["index"] - 1) * 100
    print("written; since launch", pct(since(CARD)), "| 1 day", pct(day), "| index", f'{CARD["current_index"]:.2f}', "| price", CARD["pw_index"])


if __name__ == "__main__":
    main()
