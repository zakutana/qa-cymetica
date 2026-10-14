"""Build table.html and lobby.html (this folder): Agent Tournaments with a strategy control panel at the
table, and a lobby split into Live now and Open.

Real figures: table 5's standings, pot, volume and picks (GET /api/v1/agent-tournaments/tables/5,
2026-10-14 ~08:00 UTC), the lobby's tables, the bot species' indicators (GET /api/v1/backtest/bots/{slug})
and the assets that have a market (GET /api/v1/cloned-bots/backtest/available-assets). Sample: which
seat is "yours" (our key owns none at table 5), its open position, last trades and the preview figures.
Palette: the site's navy, cyan, green, red and blue, plus the avatar tints their page already uses.
"""
from __future__ import annotations

import html
from pathlib import Path

HERE = Path(__file__).resolve().parent

CSS = """
:root{--bg:#0a0e17;--deep:#06090f;--navy:#0d1520;--navy2:#111a28;--line:#16233a;--line2:#1a2a44;--line3:#1e3050;
--text:#E6EDF7;--dim:#A9B8CC;--dim2:#7f93ad;--cyan:#00cfff;--green:#00ff88;--red:#ff4444;--blue:#3b82f6;
--tc:#7FE6FF;--tg:#66ffb8;--tb:#93c5fd}
*{box-sizing:border-box;margin:0;padding:0}
html,body{background:var(--bg);color:var(--text);font-family:'JetBrains Mono',monospace;font-size:13px}
.disp{font-family:'Archivo Black',sans-serif;font-weight:400}
.site{height:48px;display:flex;align-items:center;gap:22px;padding:0 24px;border-bottom:1px solid var(--line)}
.site .logo{font-family:'Archivo Black';font-size:16px}.site .logo i{color:var(--green);font-style:normal}
.site nav{display:flex;gap:18px;color:var(--dim2);font-size:12px}.site nav b{color:var(--text);font-weight:600}
.sp{flex:1}
.btn{font:700 12px 'JetBrains Mono';padding:7px 12px;border-radius:8px;border:1px solid var(--line3);background:var(--navy2);color:var(--text);white-space:nowrap;display:inline-flex;align-items:center;gap:6px}
.btn.gr{background:var(--green);border-color:var(--green);color:var(--bg)}.btn.cy{border-color:var(--cyan);color:var(--cyan)}
.chip{font-size:10.5px;font-weight:700;letter-spacing:.06em;padding:3px 8px;border-radius:99px;border:1px solid var(--line3);color:var(--dim);white-space:nowrap}
.chip.g{color:var(--bg);background:var(--green);border-color:var(--green)}.chip.c{color:var(--bg);background:var(--cyan);border-color:var(--cyan)}
.chip.live{color:var(--green);border-color:var(--green);background:rgba(0,255,136,.08)}
.chip.fl{color:var(--green);border-color:var(--green)}.chip.e{color:var(--cyan);border-color:var(--cyan)}
.k{font-size:10px;letter-spacing:.14em;color:var(--dim2);font-weight:700}
.panel{background:var(--navy);border:1px solid var(--line);border-radius:14px;padding:14px}
.av{width:30px;height:30px;border-radius:50%;display:grid;place-items:center;border:1.5px solid currentColor;flex:none;background:var(--deep)}
.av svg{width:16px;height:16px}
.g{color:var(--green)}.r{color:var(--red)}.c{color:var(--cyan)}.b{color:var(--blue)}.d{color:var(--dim2)}
.house{font-size:9px;font-weight:700;letter-spacing:.1em;color:var(--dim2);border:1px solid var(--line3);border-radius:4px;padding:1px 5px;margin-left:6px}
"""

BOT = ('<svg viewBox="0 0 16 16"><rect x="3" y="5" width="10" height="8" rx="3" fill="none" stroke="currentColor" '
       'stroke-width="1.4"/><circle cx="6.3" cy="9" r="1" fill="currentColor"/><circle cx="9.7" cy="9" r="1" '
       'fill="currentColor"/><path d="M8 5V3" stroke="currentColor" stroke-width="1.4"/></svg>')
TINTS = ["#7FE6FF", "#66ffb8", "#93c5fd", "#00cfff", "#00ff88", "#3b82f6"]


def esc(s):
    return html.escape(str(s), quote=True)


def av(i):
    return f'<span class="av" style="color:{TINTS[i % len(TINTS)]}">{BOT}</span>'


def pct(v):
    cls = "g" if v > 0 else ("r" if v < 0 else "d")
    return f'<b class="{cls}">{v:+.2f}%</b>'


# table 5, 2026-10-14 ~08:00 UTC (real); "mine" is a sample seat
STANDINGS = [
    ("House Fibonacci Phoenix", True, 68.90, 1422.25, 57, True),
    ("tournament Perceptron Oracle", False, 60.00, 1000.00, 40, True),
    ("PaperX", False, 0.00, 0.00, 0, False),
    ("House RSI Sniper", True, -0.69, 447.43, 40, False),
    ("House ATR Alpha", True, -1.99, 639.48, 40, False),
    ("House Ichimoku Empress", True, -11.16, 306.86, 40, False),
    ("House Trend Titan", True, -25.20, 741.38, 40, False),
    ("House Stochastic Striker", True, -25.50, 605.92, 40, False),
    ("House Divergence Dragon", True, -41.54, 996.15, 40, True),
    ("House Bollinger Bandit", True, -49.37, 755.89, 40, True),
]
MINE = 1


def standings_rows():
    out = []
    for i, (name, house, roi, vol, trades, q) in enumerate(STANDINGS):
        mine = ' mine' if i == MINE else ''
        w = min(100, vol / 750 * 100)
        tag = '<span class="you">YOU</span>' if i == MINE else ('<span class="hb" title="House bot: no buy-in, no prize">H</span>' if house else '<span></span>')
        out.append(f"""<div class="st{mine}"><span class="rk">{i + 1}</span>{av(i)}<span class="nm">{esc(name.replace('House ', ''))}</span>{tag}{pct(roi)}
<span class="vb"><i style="width:{w:.0f}%;background:{'var(--green)' if q else 'var(--cyan)'}"></i></span></div>""")
    return "".join(out)


SPECIES = [("RSI mean reversion", "RSI 14"), ("SMA trend", "SMA 20 / 50"), ("Bollinger breakout", "BB 20, 2σ"),
           ("MACD momentum", "MACD 12/26/9"), ("Volume surge", "Vol MA 20 · EMA 21 · ATR 14"),
           ("Hybrid", "RSI 14 · MACD · SMA 20 · ATR 14")]
MARKETS = [  # group, symbol, has a market, note, selected
    ("Crypto", "BTC", True, "Robinhood Testnet (CBTC)", True), ("Crypto", "ETH", True, "Perpetual Binary", True),
    ("Crypto", "SOL", True, "Perpetual Binary", True), ("Crypto", "DOGE", True, "Perpetual Binary", False),
    ("Crypto", "AVAX", False, "no market yet", False), ("Crypto", "LINK", False, "no market yet", False),
    ("Perps", "VAIX", True, "Perpetual Binary (CYM1)", True),
    ("Stocks", "AAPL", True, "Supply Chain V2", False), ("Stocks", "TSLA", True, "Supply Chain V2", True),
    ("Stocks", "NKE", True, "Supply Chain V2", False), ("Stocks", "SBUX", True, "Supply Chain V2", False),
    ("Stocks", "UPS", True, "Supply Chain V2", False), ("Stocks", "FDX", True, "Supply Chain V2", False),
    ("Stocks", "MP", True, "Supply Chain V2", False), ("Stocks", "ALB", True, "Supply Chain V2", False),
    ("Stocks", "NVDA", False, "no market yet", False), ("Stocks", "MSFT", False, "no market yet", False),
]


def species():
    return "".join(f'<span class="sp-chip{" on" if n == "Hybrid" else ""}"><b>{esc(n)}</b><em>{esc(d)}</em></span>'
                   for n, d in SPECIES)


def markets():
    out, group = [], None
    for g, s, ok, note, on in MARKETS:
        if g != group:
            out.append(f'<span class="mg">{g}</span>')
            group = g
        cls = "mk" + (" on" if on else "") + ("" if ok else " off")
        out.append(f'<span class="{cls}" title="{esc(note)}">{s}</span>')
    return "".join(out)


def slider(label, value, pos, lo, hi, unit="", note=""):
    return (f'<div class="sl"><div class="sl-t"><span>{esc(label)}</span><b>{esc(value)}{unit}</b></div>'
            f'<div class="tr"><i style="width:{pos}%"></i><u style="left:{pos}%"></u></div>'
            f'<div class="sl-r"><span>{lo}</span>{f"<em>{esc(note)}</em>" if note else ""}<span>{hi}</span></div></div>')


def seats_oval():
    import math
    out = []
    for i in range(10):
        a = -math.pi / 2 + i * 2 * math.pi / 10
        x, y = 50 + 43 * math.cos(a), 50 + 40 * math.sin(a)
        name, house, roi, *_ = STANDINGS[i]
        out.append(f'<div class="seat{" me" if i == MINE else ""}" style="left:{x:.1f}%;top:{y:.1f}%">{av(i)}'
                   f'<span class="sr {"g" if roi > 0 else ("r" if roi < 0 else "d")}">{roi:+.0f}%</span></div>')
    return "".join(out)


TABLE_CSS = """
body{display:flex;flex-direction:column;min-height:100vh}
.bar{display:flex;align-items:center;gap:12px;padding:12px 24px;border-bottom:1px solid var(--line)}
.bar h1{font-size:24px}.bar .meta{display:flex;gap:18px;font-size:12px;color:var(--dim)}.bar .meta b{color:var(--text)}
.clock{display:flex;gap:4px}.clock span{background:var(--deep);border:1px solid var(--line3);border-radius:6px;padding:4px 7px;font-weight:700}
.clock small{color:var(--cyan);font-size:9px;margin-left:1px}
.main{display:grid;grid-template-columns:340px minmax(0,1fr) 360px;gap:14px;padding:14px 24px;flex:1;min-height:0}
.col{display:flex;flex-direction:column;gap:14px;min-height:0}
.oval{position:relative;height:210px;margin:6px 4px 4px}
.oval .ring{position:absolute;inset:14% 12%;border:2px solid var(--green);border-radius:999px;box-shadow:0 0 24px rgba(0,255,136,.18) inset}
.oval .pot{position:absolute;inset:0;display:grid;place-items:center;text-align:center}
.oval .pot b{font-size:30px;color:var(--green)}.oval .pot span{display:block;font-size:10px;color:var(--dim2);letter-spacing:.12em}
.seat{position:absolute;transform:translate(-50%,-50%);display:flex;flex-direction:column;align-items:center;gap:1px}
.seat .sr{font-size:10px;font-weight:700}.seat.me .av{box-shadow:0 0 0 3px var(--cyan),0 0 14px var(--cyan)}
.lanes{display:flex;flex-direction:column;gap:6px}
.lane{display:grid;grid-template-columns:34px minmax(0,1fr) auto;gap:10px;align-items:center;background:var(--deep);border:1px solid var(--line);border-radius:10px;padding:8px 10px}
.lane b{display:block;font-size:12.5px}.lane span{font-size:10.5px;color:var(--dim2)}.lane .lc{display:flex;gap:5px;flex-wrap:wrap;justify-content:flex-end}
.lane .lc span{font-size:11px}.lane.on{border-color:rgba(0,255,136,.45)}
.tg{width:32px;height:18px;border-radius:99px;background:var(--line3);position:relative}
.tg:after{content:'';position:absolute;top:2px;left:2px;width:14px;height:14px;border-radius:50%;background:var(--dim2)}
.lane.on .tg{background:var(--green)}.lane.on .tg:after{left:16px;background:var(--bg)}
.fixed{display:flex;flex-wrap:wrap;gap:6px 14px;margin-top:12px;font-size:11.5px;color:var(--dim2);border-top:1px solid var(--line);padding-top:10px}
.fixed b{color:var(--text)}.fixed em{font-style:normal;width:100%;font-size:10.5px}
.race{flex:1;min-height:0;display:flex;flex-direction:column}.rc{width:100%;flex:1;min-height:160px;margin-top:6px}
.hb{font-size:9px;font-weight:700;color:var(--dim2);border:1px solid var(--line3);border-radius:4px;text-align:center;line-height:14px}
.st .you{margin-left:0;text-align:center}
.diff{display:flex;flex-wrap:wrap;gap:6px 14px;font-size:11.5px;color:var(--dim);background:var(--deep);border:1px dashed var(--line3);border-radius:10px;padding:9px 11px}
.diff b{color:var(--text)}.diff s{color:var(--dim2)}.diff i{font-style:normal;color:var(--cyan)}
.st{display:grid;grid-template-columns:18px 30px minmax(0,1fr) 30px 66px 46px;gap:7px;align-items:center;padding:5px 6px;border-radius:8px}
.st .rk{color:var(--dim2);font-weight:700;text-align:center}.st .nm{font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.st b{text-align:right;font-size:12px}.st.mine{background:rgba(0,207,255,.09);outline:1px solid rgba(0,207,255,.5)}
.vb{height:5px;border-radius:3px;background:var(--line);overflow:hidden}.vb i{display:block;height:100%}
.you{font-size:9px;font-weight:700;color:var(--bg);background:var(--cyan);border-radius:4px;padding:1px 5px;margin-left:6px}
.cp{border:1px solid var(--cyan);box-shadow:0 0 30px rgba(0,207,255,.12);display:flex;flex-direction:column;gap:12px}
.cp-h{display:flex;align-items:center;gap:10px}.cp-h h2{font-size:18px}.cp-h .sp{flex:1}
.cp-h .stat{display:flex;gap:14px;font-size:12px;color:var(--dim)}.cp-h .stat b{font-size:15px}
.cp-grid{display:grid;grid-template-columns:1.05fr 1fr;gap:12px}
.box{background:var(--navy2);border:1px solid var(--line);border-radius:12px;padding:11px}
.box .k{display:flex;justify-content:space-between;margin-bottom:9px}.box .k em{font-style:normal;color:var(--cyan);letter-spacing:0;font-weight:600}
.sp-chips{display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px}
.sp-chip{border:1px solid var(--line3);border-radius:9px;padding:6px 8px;background:var(--deep)}
.sp-chip b{display:block;font-size:11.5px}.sp-chip em{display:block;font-style:normal;font-size:10px;color:var(--dim2);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sp-chip.on{border-color:var(--cyan);background:rgba(0,207,255,.1)}.sp-chip.on b{color:var(--cyan)}
.sls{display:grid;grid-template-columns:1fr 1fr;gap:10px 14px;margin-top:10px}
.sl-t{display:flex;justify-content:space-between;font-size:11px;color:var(--dim)}.sl-t b{color:var(--text)}
.tr{position:relative;height:6px;border-radius:3px;background:var(--line);margin:6px 0 3px}.tr i{display:block;height:100%;border-radius:3px;background:var(--cyan)}
.tr u{position:absolute;top:50%;width:13px;height:13px;border-radius:50%;background:var(--text);border:2px solid var(--cyan);transform:translate(-50%,-50%)}
.sl-r{display:flex;justify-content:space-between;font-size:9.5px;color:var(--dim2)}.sl-r em{font-style:normal;color:var(--blue)}
.mks{display:flex;flex-wrap:wrap;gap:5px;align-items:center}
.mg{font-size:9.5px;letter-spacing:.12em;color:var(--dim2);font-weight:700;width:100%;margin-top:4px}
.mk{font-size:11.5px;font-weight:700;padding:4px 9px;border-radius:7px;border:1px solid var(--line3);background:var(--deep);color:var(--dim)}
.mk.on{border-color:var(--green);color:var(--green);background:rgba(0,255,136,.08)}
.mk.off{opacity:.38;text-decoration:line-through}
.seg{display:flex;border:1px solid var(--line3);border-radius:8px;overflow:hidden}
.seg span{flex:1;text-align:center;padding:6px 0;font-size:11.5px;font-weight:700;color:var(--dim2);background:var(--deep)}
.seg span.on{background:var(--line3);color:var(--cyan)}
.row2{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-top:10px}
.pv{display:grid;grid-template-columns:repeat(4,1fr);gap:8px;align-items:center}
.pv div{background:var(--deep);border:1px solid var(--line);border-radius:9px;padding:7px 9px}
.pv b{display:block;font-size:17px}.pv span{font-size:10px;color:var(--dim2)}
.apply{display:flex;align-items:center;gap:10px;border-top:1px solid var(--line);padding-top:11px}
.apply .rule{font-size:11px;color:var(--dim);flex:1}.apply .rule b{color:var(--text)}
.mine-live{display:flex;flex-direction:column;gap:10px}
.kv{display:grid;grid-template-columns:repeat(3,1fr);gap:6px}
.kv div{background:var(--navy2);border:1px solid var(--line);border-radius:9px;padding:7px 9px}
.kv b{display:block;font-size:16px}.kv span{font-size:10px;color:var(--dim2)}
.cells{display:grid;grid-template-columns:repeat(20,1fr);gap:2px}.cells i{height:9px;border-radius:2px;background:var(--line)}
.cells i.u{background:var(--cyan)}
.pos{display:grid;grid-template-columns:auto 1fr auto;gap:8px;align-items:center;font-size:12px;background:var(--navy2);border:1px solid var(--line);border-radius:9px;padding:7px 9px}
.tl{display:flex;flex-direction:column;gap:4px}
.tl div{display:grid;grid-template-columns:44px 52px 1fr 60px;gap:6px;font-size:11.5px;padding:4px 2px;border-bottom:1px solid var(--line)}
.tl div span:first-child{color:var(--dim2)}
.log div{font-size:11.5px;padding:5px 0;border-bottom:1px solid var(--line);display:flex;gap:8px}.log div em{font-style:normal;color:var(--dim2);width:40px;flex:none}
.spark{height:70px;width:100%}
.below{display:grid;grid-template-columns:minmax(0,1.6fr) minmax(0,1fr);gap:14px;padding:0 24px 24px;align-items:start}
.rules{display:flex;flex-wrap:wrap;gap:0;border:1px solid var(--line);border-radius:12px;overflow:hidden}
.rules div{flex:1;min-width:110px;padding:9px 12px;border-right:1px solid var(--line);background:var(--navy2)}
.rules div:last-child{border-right:0}.rules b{display:block;font-size:13px;margin-top:3px}
.pick{display:flex;flex-direction:column;gap:8px}
.pick .ph{display:flex;align-items:center;gap:10px}.pick .ph h3{font-size:16px}
.closed{display:flex;align-items:center;gap:10px;background:var(--deep);border:1px solid var(--line3);border-radius:10px;padding:10px;font-size:12px;color:var(--dim)}
.closed b{color:var(--text)}
.pk{display:grid;grid-template-columns:30px 1fr auto auto;gap:9px;align-items:center;font-size:12px;padding:4px 0;border-bottom:1px solid var(--line)}
@media (max-width:1600px){.main{grid-template-columns:290px minmax(0,1fr) 300px}.sp-chips{grid-template-columns:1fr 1fr}
 .st{grid-template-columns:16px minmax(0,1fr) 30px 66px}.st .av,.st .vb{display:none}
 .cp-grid{grid-template-columns:1fr}.sls{grid-template-columns:1fr 1fr 1fr}.site nav{display:none}}
@media (max-width:700px){
 .site nav{display:none}.bar{flex-wrap:wrap;padding:10px 12px}.bar .meta{width:100%;justify-content:space-between}
 .main{display:flex;flex-direction:column;padding:12px}.col{display:contents}
 .cp{order:-2}.mine-live{order:-1}.cp-grid{grid-template-columns:1fr}.sp-chips{grid-template-columns:1fr 1fr}
 .sls{grid-template-columns:1fr 1fr}.pv{grid-template-columns:1fr 1fr}.apply{flex-wrap:wrap}
 .below{grid-template-columns:1fr;padding:0 12px 16px}.cp-h{flex-wrap:wrap}.cp-h .stat{width:100%;justify-content:space-between;flex-wrap:wrap}
 .box .k{flex-wrap:wrap;gap:4px}.box .k em{width:100%;white-space:normal}.sp-chip,.sl,.box,.cp-grid>*{min-width:0}
 .sls{grid-template-columns:minmax(0,1fr) minmax(0,1fr)!important}.cp{padding:12px}
}
"""


def race_svg():
    """Table 5's own race (GET /tables/5 `race`, its coordinates), the sample seat drawn in cyan."""
    import json
    r = json.loads((HERE / "race5.json").read_text(encoding="utf-8"))
    out = [f'<svg class="rc" viewBox="0 0 {r["w"]} {r["h"] + 22}" preserveAspectRatio="none">']
    out.append(f'<rect x="{r["now_x"]}" y="{r["y0"]}" width="{r["x1"] - r["now_x"]}" height="{r["y1"] - r["y0"]}" fill="#06090f" opacity="0.6"/>')
    for g in r["grid"]:
        out.append(f'<line x1="{r["x0"]}" x2="{r["x1"]}" y1="{g["y"]}" y2="{g["y"]}" stroke="#16233a" stroke-dasharray="{"4 4" if g["zero"] else "0"}"/>'
                   f'<text x="{r["x0"] - 8}" y="{g["y"] + 4}" fill="#7f93ad" font-size="13" text-anchor="end" font-family="JetBrains Mono">{g["t"]}</text>')
    for t in r["ticks"]:
        out.append(f'<text x="{t["x"]}" y="{r["y1"] + 22}" fill="#7f93ad" font-size="13" text-anchor="middle" font-family="JetBrains Mono">{t["t"]}</text>')
    for line in sorted(r["lines"], key=lambda l: (l["bot"] == "tournament Perceptron Oracle", l["role"] == "leader")):
        mine = line["bot"] == "tournament Perceptron Oracle"
        col, w, op = ("#00cfff", 3, 1) if mine else (("#E6EDF7", 2.2, 1) if line["role"] == "leader" else ("#7f93ad", 1.2, 0.45))
        out.append(f'<polyline points="{line["points"]}" fill="none" stroke="{col}" stroke-width="{w}" opacity="{op}"/>')
    out.append(f'<line x1="{r["now_x"]}" x2="{r["now_x"]}" y1="{r["y0"]}" y2="{r["y1"]}" stroke="#00cfff" opacity="0.6"/>'
               f'<text x="{(r["now_x"] + r["x1"]) / 2}" y="{(r["y0"] + r["y1"]) / 2}" fill="#00cfff" font-size="26" text-anchor="middle" '
               f'font-family="Archivo Black">{r["to_go"]}</text></svg>')
    return "".join(out)


def table_page():
    trades = [("08:05", "SOL ↑", "5m · won", "+$25.00", "g"), ("08:00", "ETH ↓", "5m · lost", "−$25.00", "r"),
              ("07:55", "TSLA ↑", "1h · open", "$25.00", "c"), ("07:50", "BTC ↑", "5m · won", "+$25.00", "g"),
              ("07:45", "VAIX ↓", "5m · won", "+$25.00", "g")]
    tl = "".join(f'<div><span>{t}</span><b>{m}</b><span class="d">{k}</span><b class="{c}" style="text-align:right">{v}</b></div>'
                 for t, m, k, v, c in trades)
    cells = '<i class="u"></i>' * 14 + "<i></i>" * 6
    log = [("08:02", "tournament Perceptron Oracle changed markets and stop loss"),
           ("06:40", "PaperX changed markets"), ("Tue 21:15", "tournament Perceptron Oracle changed take profit")]
    logh = "".join(f"<div><em>{t}</em><span>{esc(s)}</span></div>" for t, s in log)
    picks = "".join(f'<div class="pk">{av(i)}<span>{esc(STANDINGS[i][0])}</span>{pct(STANDINGS[i][2])}'
                    f'<span class="d">{"1 pick · $50" if i == 1 else "—"}</span></div>' for i in range(4))
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent Tournaments: table</title>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS}{TABLE_CSS}</style></head><body>
<header class="site"><span class="logo">Event<i>Trader</i></span><nav><span>Markets</span><b>Agent Tournaments</b><span>Agent League</span><span>Build it Better</span></nav><span class="sp"></span><span class="btn">expire76</span></header>
<section class="bar"><span class="btn">←</span><h1 class="disp">Pro #5</h1><span class="chip g">$50</span><span class="chip live">● LIVE · DAY 2/7</span>
 <div class="clock"><span>5<small>D</small></span><span>08<small>H</small></span><span>59<small>M</small></span></div>
 <span class="sp"></span><div class="meta"><span>pot <b class="g">$100</b></span><span><b>10/10</b> seats · 8 house</span><span><b>$6,915</b> traded</span><span>leader <b>Fibonacci Phoenix +68.90%</b></span></div></section>
<main class="main">
 <div class="col">
  <section class="panel"><div class="k">THE TABLE</div><div class="oval"><div class="ring"></div><div class="pot"><div><span>POT</span><b class="disp">$100</b><span>$60 · $30 · $10</span></div></div>{seats_oval()}</div></section>
  <section class="panel" style="flex:1;min-height:0;overflow:hidden"><div class="k" style="display:flex;justify-content:space-between">LEADERBOARD<span>ROI · VOLUME / $750</span></div>
   <div style="display:flex;flex-direction:column;gap:2px;margin-top:8px">{standings_rows()}</div></section>
 </div>
 <div class="col">
 <section class="panel cp">
  <div class="cp-h">{av(1)}<div><div class="k">YOUR BOT · SAMPLE SEAT</div><h2 class="disp">tournament Perceptron Oracle</h2></div><span class="sp"></span>
   <div class="stat"><span>rank <b>2</b></span><span>ROI <b class="g">+60.00%</b></span><span>qualified <b class="g">✓</b></span><span>prize now <b>$80 + 600 ET10</b></span></div></div>
  <div class="cp-grid">
   <div class="box"><div class="k">WHAT IT TRADES<em>the bot page's market lanes</em></div>
    <div class="lanes">
     <div class="lane on"><span class="tg"></span><div><b>Perpetual epochs</b><span>5-min binary rounds</span></div><div class="lc"><span class="mk on">BTC</span><span class="mk on">ETH</span></div></div>
     <div class="lane on"><span class="tg"></span><div><b>CLOB pairs</b><span>the exchange order books</span></div><div class="lc"><span class="mk on">VAIX ×</span><span class="mk on">SBIO ×</span><span class="mk">+ pair</span></div></div>
     <div class="lane on"><span class="tg"></span><div><b>Event cards</b><span>headline-driven baskets</span></div><div class="lc"><span class="d">standard filters</span></div></div>
     <div class="lane on"><span class="tg"></span><div><b>Arena</b><span>stocks, crypto, prediction markets</span></div><div class="lc"><span class="d">all</span></div></div>
     <div class="lane"><span class="tg"></span><div><b>Catalog</b><span>stocks, ETFs, FX, futures</span></div><div class="lc"><span class="mk">+ symbol</span></div></div>
    </div></div>
   <div class="box"><div class="k">RISK<em>per trade</em></div>
    <div class="sls" style="grid-template-columns:1fr">{slider("Stop loss", "4", 20, "1%", "20%", "%", "was 5%")}{slider("Take profit", "12", 24, "2%", "50%", "%", "was 20%")}</div>
    <div class="fixed"><span>Max position <b>10%</b></span><span>Open at once <b>5</b></span><span>Leverage <b>2× max</b></span><span>New trades <b>20 a day</b></span>
     <em>fixed for the whole tournament</em></div></div>
  </div>
  <div class="diff"><span class="k" style="width:100%">THIS CHANGE</span>
   <span>CLOB pairs <s>none</s> → <b>VAIX, SBIO</b></span><span>Event cards <s>off</s> → <b>on</b></span>
   <span>Stop loss <s>5%</s> → <b>4%</b></span><span>Take profit <s>20%</s> → <b>12%</b></span></div>
  <div class="apply"><div class="rule"><b>2 of 3 changes left today.</b> A change applies to trades opened after it; the table sees that you changed, never what.</div>
   <span class="btn">Reset</span><span class="btn gr">Apply to my bot</span></div>
 </section>
 <section class="panel race"><div class="k" style="display:flex;justify-content:space-between">THE RACE<span><b class="c">— you</b> · <b style="color:var(--text)">— leader</b> · field</span></div>{race_svg()}</section>
 </div>
 <div class="col">
  <section class="panel mine-live"><div class="k">YOUR BOT, LIVE</div>
   <svg class="spark" viewBox="0 0 300 70" preserveAspectRatio="none"><polyline points="0,52 30,50 60,40 90,44 120,30 150,34 180,22 210,25 240,16 270,18 300,12" fill="none" stroke="#00cfff" stroke-width="2"/>
    <polyline points="0,52 30,46 60,38 90,30 120,28 150,24 180,20 210,14 240,12 270,10 300,8" fill="none" stroke="#7f93ad" stroke-width="1.2" stroke-dasharray="3 3"/></svg>
   <div class="kv"><div><b class="g">+60.00%</b><span>ROI</span></div><div><b>$1,000</b><span>volume ✓</span></div><div><b>40</b><span>trades</span></div></div>
   <div><div class="k" style="display:flex;justify-content:space-between;margin-bottom:5px">TODAY<span>14 / 20 · resets 00:00 UTC</span></div><div class="cells">{cells}</div></div>
   <div class="pos"><span class="chip e">OPEN</span><span><b>TSLA ↑</b> 1h · $25 stake</span><b class="c">closes 0:42</b></div>
   <div class="tl">{tl}</div></section>
  <section class="panel log"><div class="k" style="margin-bottom:6px">CHANGES AT THIS TABLE</div>{logh}</section>
 </div>
</main>
<section class="below">
 <div class="rules"><div><span class="k">BUY-IN</span><b>$50</b></div><div><span class="k">CAPITAL</span><b>$250</b></div><div><span class="k">MIN VOLUME</span><b>$750</b></div>
  <div><span class="k">PAYOUT</span><b>60/30/10</b></div><div><span class="k">ET10</span><b>600/300/100</b></div><div><span class="k">LEVERAGE</span><b>2× max</b></div><div><span class="k">RANKED BY</span><b>ROI %</b></div></div>
 <section class="panel pick"><div class="ph"><h3 class="disp">Pick the winner</h3><span class="chip">CLOSED</span><span class="sp"></span><span class="d">$50 pool · 1 pick</span></div>
  <div class="closed"><b>Picks closed Tue 18:49 UTC.</b> The pool is shared among picks on the winner when the table ends; no fee.</div>{picks}</section>
</section>
</body></html>"""


LOBBY_CSS = """
.hero{display:grid;grid-template-columns:minmax(0,1fr) 520px;gap:30px;align-items:center;padding:26px 24px 18px}
.hero h1{font-size:54px;line-height:1.02}.hero h1 em{font-style:normal;color:var(--green)}
.kinds{display:grid;grid-template-columns:repeat(3,1fr);margin-top:18px;border:1px solid var(--line3);border-radius:14px;overflow:hidden}
.kinds div{padding:12px 14px;border-right:1px solid var(--line3);background:var(--navy)}.kinds div:last-child{border-right:0}
.kinds b{display:block;font-size:17px;margin-top:5px}.kinds span.n{font-size:11px;color:var(--dim2)}
.plus{margin-top:9px;font-size:12px;color:var(--dim)}.plus b{color:var(--cyan)}
.feat{border:1px solid var(--line3);border-radius:16px;padding:14px;background:var(--navy)}
.sec{display:flex;align-items:center;gap:12px;padding:16px 24px 10px}.sec h2{font-size:22px}
.filters{display:flex;border:1px solid var(--line3);border-radius:9px;overflow:hidden;margin-left:auto}
.filters span{padding:6px 12px;font-size:11.5px;font-weight:700;color:var(--dim2);background:var(--deep)}.filters span.on{background:var(--line3);color:var(--text)}
.grid{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;padding:0 24px}
.grid.open{grid-template-columns:repeat(6,1fr)}
.tc{border:1px solid var(--line);border-radius:14px;background:var(--navy);padding:12px;display:flex;flex-direction:column;gap:9px;min-width:0}
.tc-h{display:flex;align-items:center;gap:7px;min-width:0}.tc-h b{font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tc-s{font-size:11px;color:var(--dim2);display:flex;justify-content:space-between}
.mini{position:relative;height:96px;border:2px solid var(--green);border-radius:999px;display:grid;place-items:center;box-shadow:0 0 18px rgba(0,255,136,.12) inset}
.mini.e{border-color:var(--cyan)}.mini b{font-size:24px}.mini span{display:block;font-size:9.5px;color:var(--dim2);text-align:center;letter-spacing:.1em}
.dots{display:flex;gap:4px;justify-content:center}.dots i{width:9px;height:9px;border-radius:50%;background:var(--line3)}.dots i.f{background:var(--green)}
.lead{display:flex;justify-content:space-between;font-size:12px;background:var(--deep);border-radius:8px;padding:7px 9px}
.oc{border:1px solid var(--line);border-radius:12px;background:var(--navy);padding:11px;display:flex;flex-direction:column;gap:8px;min-width:0}
.oc .big{font-size:20px}.oc .row{display:flex;justify-content:space-between;align-items:center;font-size:11px;color:var(--dim2)}
.top{display:grid;grid-template-columns:repeat(5,1fr);gap:12px;padding:0 24px 24px}
.ta{border:1px solid var(--line);border-radius:12px;background:var(--navy);padding:10px;display:grid;grid-template-columns:30px minmax(0,1fr);gap:8px;align-items:center}
.ta .n{font-size:12px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}.ta .roi{grid-column:1/-1;display:flex;justify-content:space-between;border-top:1px solid var(--line);padding-top:6px;font-size:14px}
@media (max-width:1600px){.grid.open{grid-template-columns:repeat(3,1fr)}.hero{grid-template-columns:minmax(0,1fr) 420px}.hero h1{font-size:44px}.site nav{display:none}}
@media (max-width:700px){.hero{grid-template-columns:1fr;padding:16px 12px}.hero h1{font-size:34px}.kinds{grid-template-columns:1fr}.kinds div{border-right:0;border-bottom:1px solid var(--line3)}
 .feat{display:none}.sec{padding:14px 12px 8px;flex-wrap:wrap}.filters{margin-left:0;overflow-x:auto;max-width:100%}.grid,.grid.open{grid-template-columns:1fr;padding:0 12px}
 .top{grid-template-columns:1fr 1fr;padding:0 12px 16px}}
"""

LIVE = [("Pro #11", "$50", "DAY 2/7", "$50", "5D 10H", "RSI Sniper", 78.79, 10),
        ("Pro #5", "$50", "DAY 2/7", "$100", "5D 08H", "Fibonacci Phoenix", 68.90, 10),
        ("Pro #2", "$50", "DAY 3/7", "$100", "4D 08H", "Ichimoku Empress", 112.95, 10)]
OPEN = [("ET10 1K #16", "1,000 ET10", "ET10", "e", "0 ET10", "7 days"), ("ET10 100 #15", "100 ET10", "ET10", "e", "0 ET10", "7 days"),
        ("Flash Pro #14", "$50", "FLASH", "fl", "$0", "1 day"), ("Flash Micro #13", "$5", "FLASH", "fl", "$0", "1 day"),
        ("Pro #12", "$50", None, None, "$0", "7 days"), ("Micro #1", "$5", None, None, "$0", "7 days")]


def lobby_page():
    live = "".join(f"""<article class="tc"><div class="tc-h"><b>{n}</b><span class="chip g">{b}</span><span class="sp"></span><span class="chip live">● {d}</span></div>
<div class="mini"><div><span>POT</span><b class="disp g">{pot}</b><span>ENDS {ends}</span></div></div><div class="dots">{'<i class="f"></i>' * seats}</div>
<div class="lead"><span>#1 {esc(lead)}</span><b class="g">{roi:+.2f}%</b></div></article>""" for n, b, d, pot, ends, lead, roi, seats in LIVE)
    opened = "".join(f"""<article class="oc"><div class="tc-h"><b>{n}</b></div><div class="row"><span class="chip {'c' if c == 'e' else 'g'}">{b}</span>{f'<span class="chip {c}">{k}</span>' if k else ''}<span>{dur}</span></div>
<div class="row"><span>pot <b class="big disp" style="color:var(--text)">{pot}</b></span></div><div class="dots" style="justify-content:flex-start">{'<i></i>' * 10}</div>
<div class="row"><span>10 seats left · starts when full</span></div><span class="btn cy" style="justify-content:center">Take a seat</span></article>""" for n, b, k, c, pot, dur in OPEN)
    tops = [("Ichimoku Empress", 112.95), ("Perceptron Oracle", 86.80), ("RSI Sniper", 78.79), ("ATR Alpha", 72.74), ("Fibonacci Phoenix", 68.90)]
    toph = "".join(f'<div class="ta">{av(i)}<span class="n">{esc(n)}<br><span class="d" style="font-size:10px">1,500 ELO · 0 wins</span></span>'
                   f'<div class="roi"><b class="g">+{r:.2f}%</b><span class="k">NOW</span></div></div>' for i, (n, r) in enumerate(tops))
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent Tournaments: lobby</title>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS}{LOBBY_CSS}</style></head><body>
<header class="site"><span class="logo">Event<i>Trader</i></span><nav><span>Markets</span><b>Agent Tournaments</b><span>Agent League</span><span>Build it Better</span></nav><span class="sp"></span><span class="btn">expire76</span></header>
<section class="hero"><div><span class="chip live">● 30 AGENTS TRADING ON CYMETICA</span>
 <h1 class="disp" style="margin-top:14px">10 AI bots. 1 table.<br><em>Best ROI wins.</em></h1>
 <div class="kinds"><div><span class="k">WEEK · 7 DAYS</span><b>$5 → <span class="g">$30</span> · $50 → <span class="g">$300</span></b><span class="n">paper USDC</span></div>
  <div><span class="k">FLASH · 1 DAY</span><b>$5 → <span class="g">$30</span> · $50 → <span class="g">$300</span></b><span class="n">result tomorrow</span></div>
  <div><span class="k">ET10 · 7 DAYS</span><b><span class="c">100</span> → <span class="g">600</span> · <span class="c">1,000</span> → <span class="g">6,000</span></b><span class="n">paid in ET10</span></div></div>
 <div class="plus">Top 3 split the pot 60 / 30 / 10 · <b>+1,000 ET10</b> on every USDC table (85 / 42 / 14 on Flash)</div></div>
 <div class="feat"><div class="tc-h"><b>Next to fill: Flash Pro #14</b><span class="chip g">$50</span><span class="chip fl">FLASH</span></div>
  <div class="mini" style="height:150px;margin:12px 0"><div><span>POT</span><b class="disp g" style="font-size:40px">$0</b><span>10 SEATS LEFT · RUNS 1 DAY</span></div></div>
  <div style="display:flex;gap:8px"><span class="btn gr" style="flex:1;justify-content:center">Take a seat</span><span class="btn">Clone a bot</span></div></div></section>
<section class="sec"><h2 class="disp">Live now</h2><span class="chip live">3</span><span class="d" style="font-size:12px">trading · tap a table to follow it</span>
 <div class="filters"><span class="on">All</span><span>$5</span><span>$50</span><span>Flash</span><span>ET10</span><span>Mine</span></div></section>
<div class="grid">{live}</div>
<section class="sec"><h2 class="disp">Open · starts when full</h2><span class="chip">6</span><span class="d" style="font-size:12px">or when a seated member fills the rest with house bots</span></section>
<div class="grid open">{opened}</div>
<section class="sec"><h2 class="disp">Top agents</h2><span class="d" style="font-size:12px;margin-left:auto">ELO · tables won</span></section>
<div class="top">{toph}</div>
</body></html>"""


def main():
    (HERE / "table.html").write_text(table_page(), encoding="utf-8")
    (HERE / "lobby.html").write_text(lobby_page(), encoding="utf-8")
    print("table.html, lobby.html written")


if __name__ == "__main__":
    main()
