"""Build index.html (this folder): the Event Cards page (/events/{id}), laid out again.

The operator, 2026-10-21, after asking where "+66.98% since launch" (a list) is on the card (it is on the STATS tab, under
"Index Price: $245.48 +68.66%", inside a 217 px scrolling window): "ta stranka je hnus, navrhni top novy vzhled a podame to.
Toto cislo co chybi tak zobraz a vsechny data zachovej. Jen kdyby neco nedavalo smysl nebo bylo zbytecne predelej."

So everything the page holds stays, and moves: the card gets the room it lacked (the live page puts the whole card in a 351 x
217 px scrolling window), the figures come first (since launch, card index, one day, index price), the chart is large, the
INFO and STATS tabs become one page. What was reworked because it did not make sense is listed in spec.txt, beside the lines
that keep the rest.

Real figures: card 28a1c3df (SAIB: MRNA - Moderna) as GET /api/v1/event-cards/{id} and .../index-history served on
2026-10-21, and the page's own market pressure, Up Next and past-events blocks read from the rendered page
(event-data.json, written by the capture script). Palette: the site's navy, cyan, green, red and blue; its two fonts.
"""
from __future__ import annotations

import html
import json
import re
from datetime import datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
D = json.loads((HERE / "event-data.json").read_text(encoding="utf-8"))
CARD, HIST, PG = D["card"], D["hist"], D["page"]
esc = lambda s: html.escape(str(s), quote=True)

base = CARD["index_base"]
now_idx = CARD["current_index"]
since = (now_idx / base - 1) * 100
pts1d = HIST["1d"]["points"]
day = (pts1d[-1]["index"] / pts1d[0]["index"] - 1) * 100
launch = datetime.fromisoformat(CARD["created_at"])
price, price0 = CARD["pw_index"], CARD["pw_base"]


def pct(v, d=2):
    return f"{'+' if v >= 0 else '-'}{abs(v):.{d}f}%"


def cls(v):
    return "g" if v > 0 else ("r" if v < 0 else "d")


# ---------------------------------------------------------------- the big chart (index, one day)
def chart():
    W, H, L, R, T, B = 1000, 300, 52, 20, 22, 34
    xs = [datetime.fromisoformat(p["t"]).timestamp() for p in pts1d]
    ys = [p["index"] for p in pts1d]
    lo, hi = min(ys), max(ys)
    pad = (hi - lo) * .18
    lo, hi = lo - pad, hi + pad
    X = lambda t: L + (t - xs[0]) / (xs[-1] - xs[0]) * (W - L - R)
    Y = lambda v: T + (hi - v) / (hi - lo) * (H - T - B)
    line = " ".join(f"{X(x):.1f},{Y(y):.1f}" for x, y in zip(xs, ys))
    area = f"{L},{H - B} {line} {X(xs[-1]):.1f},{H - B}"
    grid = ""
    step = 5 if hi - lo < 40 else 10
    v = (int(lo) // step + 1) * step
    while v < hi:
        grid += f'<line x1="{L}" x2="{W - R}" y1="{Y(v):.1f}" y2="{Y(v):.1f}" class="gl"/><text x="{L - 10}" y="{Y(v) + 4:.1f}" text-anchor="end" class="ax">{v}</text>'
        v += step
    ticks = ""
    for k in range(5):
        t = xs[0] + (xs[-1] - xs[0]) * k / 4
        ticks += f'<text x="{X(t):.1f}" y="{H - 10}" text-anchor="{"start" if k == 0 else ("end" if k == 4 else "middle")}" class="ax">{datetime.fromtimestamp(t, tz=launch.tzinfo).strftime("%H:%M")}</text>'
    open_y = Y(ys[0])
    ex, ey = X(xs[-1]), Y(ys[-1])
    return (f'<svg viewBox="0 0 {W} {H}" class="chart" role="img" aria-label="Card index, last 24 hours"><defs>'
            '<linearGradient id="ar" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#00cfff" stop-opacity=".30"/><stop offset="1" stop-color="#00cfff" stop-opacity="0"/></linearGradient></defs>'
            f'{grid}<line x1="{L}" x2="{W - R}" y1="{open_y:.1f}" y2="{open_y:.1f}" class="open"/>'
            f'<text x="{W - R}" y="{open_y - 7:.1f}" text-anchor="end" class="ax op">24h open {ys[0]:.2f}</text>'
            f'<polygon points="{area}" fill="url(#ar)"/><polyline points="{line}" class="ln"/>{ticks}'
            f'<circle cx="{ex:.1f}" cy="{ey:.1f}" r="9" class="halo"/><circle cx="{ex:.1f}" cy="{ey:.1f}" r="4.5" class="dot"/>'
            f'<g transform="translate({ex - 74:.1f},{ey - 38:.1f})"><rect width="68" height="24" rx="12" class="tag"/><text x="34" y="16.5" text-anchor="middle" class="tagt">{ys[-1]:.2f}</text></g></svg>')


# ---------------------------------------------------------------- market pressure
def mp_spark():
    pts = PG["mp"]["spark"][0]["points"]
    return (f'<svg viewBox="0 0 600 60" preserveAspectRatio="none" class="mps"><line x1="4" y1="30" x2="596" y2="30" class="gl"/>'
            f'<polyline points="{pts}" class="ln g2"/></svg>')


# ---------------------------------------------------------------- up next
def upnext():
    rows = []
    for u in PG["up"]:
        text = re.sub(r"\s+", " ", u["text"])
        m = re.search(r"([\d.]+)\s*([+-][\d.]+%)\s*$", text)
        idx, ch = (m.group(1), m.group(2)) if m else ("", "")
        title = re.search(r'ec-side-up-title">(.*?)</div>', u["html"])
        title = html.unescape(title.group(1)) if title else text
        sp = re.search(r'points="([^"]+)"[^>]*stroke="(#[0-9a-fA-F]{6})"', u["html"])
        col = "#00ff88" if ch.startswith("+") else "#ff4444"
        rows.append(f'<div class="up"><img src="{esc(u["img"])}" alt="" loading="eager"><div class="ut">{esc(title)}</div>'
                    f'<div class="ui"><b>{esc(idx)}</b><span class="{"g" if ch.startswith("+") else "r"}">{esc(ch)}</span></div>'
                    f'<svg viewBox="0 0 60 20" preserveAspectRatio="none" class="us"><polyline points="{sp.group(1) if sp else ""}" fill="none" stroke="{col}" stroke-width="1.5" stroke-linejoin="round"/></svg></div>')
    return "".join(rows)


# ---------------------------------------------------------------- past events
def analogs():
    A = PG["analogs"]
    st = {s.split("%")[0] if False else s: s for s in A["stats"]}
    lines = A["lines"]
    g = ""
    for ln in lines:
        stroke, w = ln["stroke"], float(ln["w"] or 1)
        c = {"#00cfff": "this", "#00ff88": "med"}.get(stroke, "past")
        g += f'<polyline points="{ln["points"]}" class="al {c}"/>'
    return (f'<svg viewBox="0 0 600 200" preserveAspectRatio="none" class="achart"><line x1="8" y1="134.6" x2="592" y2="134.6" class="gl dash"/>{g}</svg>')


def glyph():
    return CARD["image_url"]


CSS = """
:root{--bg:#0a0e17;--deep:#06090f;--navy:#0d1520;--navy2:#111a28;--line:#16233a;--line2:#1a2a44;--line3:#1e3050;
--text:#e6edf7;--dim:#a9b8cc;--dim2:#7f93ad;--cyan:#00cfff;--green:#00ff88;--red:#ff4444;--blue:#3b82f6}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:var(--bg);color:var(--text);font-family:'JetBrains Mono',monospace;font-size:13px}
body{background:radial-gradient(ellipse 60% 40% at 30% -4%,rgba(0,207,255,.09),rgba(0,207,255,0) 70%),var(--bg)}
.g{color:var(--green)}.r{color:var(--red)}.d{color:var(--dim2)}
.wrap{max-width:1560px;margin:0 auto;padding:22px 28px 56px}
.disp{font-family:'Archivo Black',sans-serif;font-weight:400}
.k{font-size:10.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--dim2);font-weight:700}
.panel{background:var(--navy);border:1px solid var(--line2);border-radius:22px;padding:22px 24px}
.btn{display:inline-flex;align-items:center;gap:8px;border:1px solid var(--line3);background:var(--navy2);color:var(--dim);border-radius:10px;padding:8px 13px;font:inherit;font-size:12px;font-weight:700}
.btn.cy{border-color:rgba(0,207,255,.5);color:var(--cyan)}
/* top bar */
.top{display:flex;align-items:center;gap:18px;margin-bottom:18px}
.brand{font-family:'Archivo Black';font-size:20px;letter-spacing:.04em}.brand b{color:var(--cyan);font-weight:400}
.seg{display:flex;gap:4px;background:var(--deep);border:1px solid var(--line2);border-radius:12px;padding:4px}
.seg span{padding:8px 16px;border-radius:9px;color:var(--dim2);font-weight:700;font-size:12px;letter-spacing:.08em}
.seg span.on{background:var(--navy2);color:var(--cyan);box-shadow:0 0 0 1px rgba(0,207,255,.4) inset}
.prog{margin-left:auto;display:flex;align-items:center;gap:10px;color:var(--dim)}
.prog i{display:block;width:120px;height:5px;border-radius:99px;background:var(--line3);overflow:hidden}.prog i b{display:block;height:100%;width:2%;background:var(--green)}
/* grid */
.grid{display:grid;grid-template-columns:minmax(0,1fr) 410px;gap:24px;align-items:start}
.hero{position:relative;padding:0;overflow:hidden;box-shadow:0 0 0 1px rgba(0,207,255,.05),0 24px 50px rgba(0,0,0,.45)}
.stack{height:12px;margin:0 26px;border:1px solid var(--line3);border-top:none;border-radius:0 0 16px 16px;background:var(--navy2)}
.stack.s2{margin:0 52px;height:10px;background:var(--navy);border-color:var(--line2)}
.hh{display:flex;align-items:center;gap:12px;padding:20px 26px 0}
.gl-img{width:120px;height:47px;border-radius:12px;overflow:hidden;border:1px solid var(--line3);flex:none}
.gl-img img{width:100%;height:100%;display:block;object-fit:cover}
.sector{font-size:11px;letter-spacing:.14em;color:var(--cyan);font-weight:700;text-transform:uppercase}
.pill{display:inline-flex;align-items:center;gap:6px;font-size:11px;font-weight:700;letter-spacing:.06em;border:1px solid rgba(0,207,255,.45);color:var(--cyan);border-radius:99px;padding:4px 11px}
.pill.live{color:var(--green);border-color:rgba(0,255,136,.5);background:rgba(0,255,136,.08)}
.pill.live i{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 8px var(--green)}
.hh .sp{margin-left:auto;display:flex;gap:8px;align-items:center}
.vote{display:inline-flex;gap:6px;align-items:center;border:1px solid var(--line3);border-radius:10px;padding:8px 12px;color:var(--dim);font-weight:700}
.title{padding:14px 26px 0;font-family:'Archivo Black';font-weight:400;font-size:38px;line-height:1.1;letter-spacing:-.01em}
.meta{display:flex;gap:14px;align-items:center;padding:10px 26px 0;color:var(--dim);font-size:12.5px}
.chip{display:inline-flex;gap:6px;border:1px solid var(--line3);border-radius:99px;padding:3px 11px;font-size:11.5px;color:var(--dim);font-weight:700}
.fig{display:grid;grid-template-columns:1.5fr 1fr 1fr 1.2fr;gap:12px;padding:20px 26px 0}
.fig>div{background:var(--deep);border:1px solid var(--line2);border-radius:16px;padding:14px 16px;min-width:0}
.fig .v{font-size:30px;font-weight:700;margin-top:6px;line-height:1.05;white-space:nowrap}
.fig .s{font-size:11.5px;color:var(--dim2);margin-top:6px;white-space:nowrap}
.fig .hero1{border-color:rgba(0,255,136,.55);background:linear-gradient(160deg,rgba(0,255,136,.13),rgba(0,255,136,.02) 70%),var(--deep);box-shadow:0 0 28px rgba(0,255,136,.13)}
.fig .hero1 .v{font-family:'Archivo Black';font-weight:400;font-size:46px;color:var(--green);text-shadow:0 0 24px rgba(0,255,136,.4)}
.ch{padding:20px 26px 0}
.chh{display:flex;align-items:center;justify-content:space-between;margin-bottom:6px}
.tog{display:flex;gap:4px;background:var(--deep);border:1px solid var(--line2);border-radius:10px;padding:3px}
.tog span{padding:5px 12px;border-radius:7px;color:var(--dim2);font-weight:700;font-size:12px}.tog span.on{background:var(--navy2);color:var(--text)}
.chart{width:100%;height:auto;display:block}
.chart .gl,.mps .gl,.achart .gl{stroke:var(--line2);stroke-width:1;vector-effect:non-scaling-stroke}
.chart .ax{font-family:'JetBrains Mono';font-size:11px;fill:#7f93ad}.chart .ax.op{fill:#a9b8cc}
.chart .open{stroke:#7f93ad;stroke-opacity:.55;stroke-dasharray:4 5;stroke-width:1}
.chart .ln{fill:none;stroke:#00cfff;stroke-width:2.6;stroke-linejoin:round;filter:drop-shadow(0 0 6px rgba(0,207,255,.5))}
.chart .halo{fill:#00cfff;fill-opacity:.2}.chart .dot{fill:#00cfff}
.chart .tag{fill:#00cfff}.chart .tagt{fill:#06090f;font-family:'JetBrains Mono';font-weight:700;font-size:13px}
.low{display:grid;grid-template-columns:minmax(0,1fr) 400px;gap:22px;padding:22px 26px 0}
.about p{color:var(--dim);line-height:1.7;font-size:13.5px;margin-top:8px}
.about .kv{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:18px}
.about .kv div{background:var(--deep);border:1px solid var(--line2);border-radius:12px;padding:10px 12px}
.about .kv b{display:block;font-size:14px;margin-top:4px;color:var(--text)}
.tok .k{white-space:nowrap}
.tok{display:flex;gap:12px;align-items:center;margin-top:12px;border:1px dashed rgba(0,207,255,.4);border-radius:12px;padding:10px 14px;color:var(--dim);font-size:12.5px}
.tok a{color:var(--cyan);text-decoration:underline}
.alloc{background:var(--deep);border:1px solid var(--line2);border-radius:16px;padding:16px}
.alloc .bal{margin:8px 0 12px;color:var(--cyan);font-weight:700}.alloc .bal u{color:var(--cyan)}
.pc{display:grid;grid-template-columns:repeat(5,1fr);gap:6px}
.pc span{text-align:center;border:1px solid var(--line3);border-radius:9px;padding:8px 0;color:var(--dim);font-weight:700}.pc span.on{border-color:var(--cyan);color:var(--cyan)}
.alloc .amt{margin:12px 0;color:var(--dim)}
.buy{display:block;text-align:center;background:var(--green);color:var(--deep);font-weight:700;border-radius:12px;padding:13px;font-size:15px;box-shadow:0 0 18px rgba(0,255,136,.3)}
.split{margin-top:16px}.split .row{display:grid;grid-template-columns:70px 1fr 54px 64px;gap:10px;align-items:center;margin-top:10px}
.split .bar{height:8px;border-radius:99px;background:var(--line3);overflow:hidden}.split .bar b{display:block;height:100%;width:100%;background:linear-gradient(90deg,var(--cyan),var(--green))}
.split .tag{font-size:9.5px;color:var(--dim2);border:1px solid var(--line3);border-radius:5px;padding:1px 5px;margin-left:6px}
.split .head{display:flex;justify-content:space-between;align-items:center}.split .head a{color:var(--cyan);font-size:11.5px;text-decoration:underline}
.actions{display:grid;grid-template-columns:repeat(3,1fr) 1.5fr 1.5fr;gap:10px;padding:22px 26px 0}
.act{display:flex;align-items:center;justify-content:center;gap:8px;border:1px solid var(--line3);border-radius:12px;padding:13px;font-weight:700;color:var(--dim);background:var(--navy2)}
.act.bull{background:rgba(0,255,136,.12);border-color:var(--green);color:var(--green)}.act.bear{background:rgba(255,68,68,.1);border-color:var(--red);color:var(--red)}
.hints{display:flex;gap:20px;align-items:center;padding:16px 26px 20px;color:var(--dim2);font-size:11.5px}
.hints kbd{border:1px solid var(--line3);border-radius:6px;padding:2px 7px;color:var(--dim);font:inherit;font-weight:700;margin-right:6px}.hints a{margin-left:auto;color:var(--cyan)}
/* sidebar */
.side{display:flex;flex-direction:column;gap:18px}
.sh{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:12px}
.sh h3{font-family:'Archivo Black';font-weight:400;font-size:17px}.sh .sub{color:var(--dim2);font-size:11.5px;margin-top:4px;line-height:1.4}.sh>div:first-child{min-width:0}
.sh .live{display:flex;gap:6px;align-items:center;color:var(--green);font-size:10.5px;font-weight:700;letter-spacing:.06em;white-space:nowrap;margin-top:4px}.sh .live i{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 8px var(--green)}
.sh a{color:var(--cyan);font-size:11.5px;font-weight:700}
.mp{display:grid;grid-template-columns:128px 1fr;gap:16px;align-items:center}
.mp .big{font-family:'Archivo Black';font-size:50px;line-height:1;color:var(--green);text-shadow:0 0 22px rgba(0,255,136,.35)}
.mp .w{color:var(--green);font-weight:700;letter-spacing:.14em;margin-top:6px;font-size:11px}.mp .tr{color:var(--dim2);font-size:11.5px;margin-top:6px}
.track{position:relative;height:9px;border-radius:99px;background:linear-gradient(90deg,rgba(255,68,68,.55),var(--line3) 50%,rgba(0,255,136,.55))}
.track b{position:absolute;top:-4px;width:6px;height:17px;border-radius:3px;background:var(--text);box-shadow:0 0 10px rgba(230,237,247,.6)}
.ticks{display:flex;justify-content:space-between;color:var(--dim2);font-size:10.5px;margin:7px 0 6px}
.mps{width:100%;height:50px;display:block}.mps .ln,.achart .ln{fill:none;stroke-width:2;vector-effect:non-scaling-stroke}.g2{stroke:#00ff88}
.movers{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:14px}
.movers div{background:var(--deep);border:1px solid var(--line2);border-radius:12px;padding:10px 12px;font-size:12px;min-width:0}
.movers b{display:block;margin:5px 0 4px;color:var(--text);font-weight:600;overflow:hidden;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical}
.empty{border:1px dashed var(--line3);border-radius:14px;padding:20px;text-align:center;color:var(--dim);line-height:1.6}
.empty .btn{margin-top:12px}
.up{display:grid;grid-template-columns:46px minmax(0,1fr) auto 56px;gap:12px;align-items:center;padding:10px 0;border-top:1px solid var(--line)}
.up img{width:46px;height:46px;border-radius:10px;object-fit:cover;background:var(--deep)}
.ut{font-size:12px;line-height:1.4;color:var(--text);display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
.ui{text-align:right;font-size:12px}.ui b{display:block;color:var(--dim)}.us{width:56px;height:22px}
/* past events */
.pe{margin-top:34px}
.pe .tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:14px 0}
.pe .tiles div{background:var(--deep);border:1px solid var(--line2);border-radius:14px;padding:14px 16px}
.pe .tiles b{display:block;font-size:26px;margin-top:6px}
.bw{display:flex;gap:12px;flex-wrap:wrap;margin-bottom:14px}.bw span{border:1px solid var(--line3);border-radius:99px;padding:5px 13px;font-size:12px;font-weight:700}
.achart{width:100%;height:280px;display:block;background:var(--deep);border:1px solid var(--line2);border-radius:14px}
.achart .al{fill:none;vector-effect:non-scaling-stroke;stroke-linejoin:round}.achart .past{stroke:#7f93ad;stroke-opacity:.55;stroke-width:1.2}.achart .med{stroke:#00ff88;stroke-width:2.4}.achart .this{stroke:#00cfff;stroke-width:2.6}
.achart .dash{stroke-dasharray:4 5}
.lgd{display:flex;gap:18px;margin-top:10px;color:var(--dim2);font-size:11.5px}.lgd span{display:flex;gap:7px;align-items:center}.lgd i{width:16px;height:3px;border-radius:2px;display:block}
.foot{color:var(--dim2);font-style:italic;font-size:11.5px;margin-top:10px}
"""


def page():
    c = CARD
    sent = c.get("headline_sentiment_score") or 0
    sent_txt = f"Neutral {sent:+.2f}" if abs(sent) < 0.05 else (f"Positive {sent:+.2f}" if sent > 0 else f"Negative {sent:+.2f}")
    pub = f"{launch.day} {launch.strftime('%b')}"
    A = PG["analogs"]
    stats = [re.sub(r"^(Median 30d return|% positive|Past events)", "", s) for s in A["stats"]]
    bw = re.findall(r"([▲▼]\s*[+-][\d.]+%)\s*·\s*(.+?)\s*\((.+?)\)", A["bw"])
    mpt = PG["mp"]
    top_t = re.sub(r"^Most buying\s*", "", mpt["top"]); top_p = re.search(r"([+-][\d.]+%)$", top_t).group(1); top_t = top_t[:-len(top_p)]
    bot_t = re.sub(r"^Most selling\s*", "", mpt["bot"]); bot_p = re.search(r"([+-][\d.]+%)$", bot_t).group(1); bot_t = bot_t[:-len(bot_p)]
    marker = float(re.search(r"calc\(([\d.]+)%", mpt["gauge"]).group(1))
    desc = c["summary"]
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Event Cards: {esc(c["title"])}</title>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body><main class="wrap">
<div class="top"><div class="brand">EVENT<b>CARDS</b></div>
 <div class="seg"><span class="on">PREDICTION MARKET</span><span>ORDER BOOK</span></div>
 <div class="prog"><span>0 / 51</span><i><b></b></i></div>
 <span class="btn">+ Create</span><span class="btn">Top</span></div>
<div class="grid"><div>
<section class="panel hero">
 <div class="hh"><span class="gl-img"><img src="{esc(glyph())}" alt="Technology &amp; AI"></span>
  <span class="pill">SAIB · Single AI Index Basket</span><span class="pill live"><i></i>LIVE</span>
  <div class="sp"><span class="vote">▲ {c.get("upvotes", 0)}</span><span class="btn">History</span><span class="btn">Share</span><span class="btn">Embed</span></div></div>
 <h1 class="title">{esc(c["title"])}</h1>
 <div class="meta"><span>coingecko.com · published {esc(pub)}</span><span class="chip">News sentiment: {esc(sent_txt)}</span></div>
 <div class="fig">
  <div class="hero1"><div class="k">Since launch</div><div class="v">{pct(since)}</div><div class="s">{base:.0f} → {now_idx:.2f} · since {esc(pub)}</div></div>
  <div><div class="k">Card index</div><div class="v">{now_idx:.2f}</div><div class="s">base {base:.0f}</div></div>
  <div><div class="k">1 day</div><div class="v {cls(day)}">{pct(day)}</div><div class="s">index {pts1d[0]["index"]:.2f} → {pts1d[-1]["index"]:.2f}</div></div>
  <div><div class="k">Index price</div><div class="v">${price:,.2f}</div><div class="s">at launch ${price0:,.2f}</div></div>
 </div>
 <div class="ch"><div class="chh"><span class="k">Card index · last 24 hours</span><div class="tog"><span class="on">1d</span><span>5d</span><span>30d</span></div></div>{chart()}</div>
 <div class="low">
  <div class="about"><div class="k">About this card</div><p>{esc(desc)}</p>
   <div class="kv"><div><span class="k">Symbol</span><b>{"EVCDX-SAIB"}</b></div><div><span class="k">Market cap</span><b class="d">— not minted yet</b></div></div>
   <div class="tok"><span class="k">Index token</span><span><a href="#">SAIB coin on Arc — zero platform fees</a> (not the index token)</span></div></div>
  <div><div class="alloc"><div class="k">Allocate from your balance</div>
    <div class="bal">Paper balance $100,000.00 · <u>sign in</u> to go live</div>
    <div class="pc"><span class="on">0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span></div>
    <div class="amt">$0.00 · 0% of available</div><span class="buy">Buy</span></div>
   <div class="split"><div class="head"><span class="k">Per-asset split</span><a href="#">Reset to card weights</a></div>
    <div class="row"><b>MRNA<span class="tag">DIRECT</span></b><span class="bar"><b></b></span><span>100%</span><span class="d">$0.00</span></div>
    <span class="btn cy" style="margin-top:14px">+ Add asset</span></div></div>
 </div>
 <div class="actions"><span class="act">← Back</span><span class="act">Skip</span><span class="act">Watch</span><span class="act bull">Buy →</span><span class="act bear">← Sell</span></div>
 <div class="hints"><span><kbd>←</kbd>Skip</span><span><kbd>→</kbd>Buy</span><span><kbd>W</kbd>Watchlist</span><span><kbd>?</kbd>All shortcuts</span><a href="#">Asset Universe</a></div>
</section><div class="stack"></div><div class="stack s2"></div>
</div>
<aside class="side">
 <section class="panel"><div class="sh"><div><h3>Market pressure</h3><div class="sub">{esc(mpt["sub"])}</div></div><div class="live"><i></i>{esc(mpt["live"].upper())}</div></div>
  <div class="mp"><div><div class="big">{esc(mpt["pct"])}</div><div class="w">BUYING</div><div class="tr">{esc(mpt["trend"])}</div></div>
   <div><div class="track"><b style="left:calc({marker}% - 3px)"></b></div><div class="ticks"><span>All selling</span><span>Balanced</span><span>All buying</span></div>{mp_spark()}</div></div>
  <div class="movers"><div><span class="k">Most buying</span><b>{esc(top_t.strip())}</b><span class="g">{esc(top_p)}</span></div><div><span class="k">Most selling</span><b>{esc(bot_t.strip())}</b><span class="r">{esc(bot_p)}</span></div></div></section>
 <section class="panel"><div class="sh"><div><h3>Your positions</h3><div class="sub">P&amp;L from your own entry price</div></div><a href="#">All positions →</a></div>
  <div class="empty">You have no positions yet. Paper mode gives you $100,000 to practise with, no deposit.<br><span class="btn cy">Start in paper mode</span></div></section>
 <section class="panel"><div class="sh"><div><h3>Up next</h3><div class="sub">The next five cards in your deck</div></div><a href="#">My cards →</a></div>{upnext()}</section>
</aside></div>
<section class="pe"><h3 class="disp" style="font-size:22px">How events like this performed</h3><div class="sub d" style="margin-top:6px">Index of similar past events over the 30 days after each event.</div>
 <div class="tiles"><div><span class="k">Median 30d return</span><b class="g">{esc(stats[0])}</b></div><div><span class="k">% positive</span><b>{esc(stats[1])}</b></div><div><span class="k">Past events</span><b>{esc(stats[2])}</b></div></div>
 <div class="bw">{"".join(f'<span class="{"g" if a.startswith("▲") else "r"}">{esc(a)} · {esc(t)} ({esc(m)})</span>' for a, t, m in bw)}</div>
 {analogs()}
 <div class="lgd"><span class="d">Event day</span><span><i style="background:#00cfff"></i>This event</span><span><i style="background:#00ff88"></i>Median of 2</span><span><i style="background:#7f93ad"></i>Past events</span><span style="margin-left:auto">+30d</span></div>
 <div class="foot">{esc(A["foot"])}</div></section>
</main></body></html>"""


def main():
    (HERE / "index.html").write_text(page(), encoding="utf-8")
    print("index.html written; since launch", pct(since), "| 1d", pct(day), "| index", f"{now_idx:.2f}", "| price", price)


if __name__ == "__main__":
    main()
