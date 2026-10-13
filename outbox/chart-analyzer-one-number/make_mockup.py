"""The Chart Analyzer redesign mockup, built from real data (2026-10-13).

    python make_mockup.py <gem_snapshot.json> <ohlcv_day.json> <ohlcv_hour.json> <pool.json> <out_dir>

Writes mockup.html (one page, responsive, data inline) and renders it with Chrome:
desktop-1920.png, desktop-1440.png, layers-1920.png (the Layers menu open) and phone-390.png.
Candles and pool figures are GeckoTerminal's for the CARDS/USDC Raydium pool (the pool the
live page reads, "LIVE · DEX POOL"); the setups, their study figures, the two support levels and
the verdict are the live Chart Analyzer page's for CARDS 1D, read the same day. Reads files only.
"""
import json
import math
import sys
from datetime import datetime, timezone
from pathlib import Path

gem_path, day_path, hour_path, pool_path, trades_path, h1_path, h4_path, out_dir = sys.argv[1:9]
out = Path(out_dir)
trades = json.loads(Path(trades_path).read_text())["data"]
h1 = sorted(json.loads(Path(h1_path).read_text())["data"]["attributes"]["ohlcv_list"], key=lambda r: r[0])
h4 = sorted(json.loads(Path(h4_path).read_text())["data"]["attributes"]["ohlcv_list"], key=lambda r: r[0])
gem = json.loads(Path(gem_path).read_text(encoding="utf-8"))
day = sorted(json.loads(Path(day_path).read_text())["data"]["attributes"]["ohlcv_list"], key=lambda r: r[0])
hour = json.loads(Path(hour_path).read_text())["data"]["attributes"]["ohlcv_list"]
pool = json.loads(Path(pool_path).read_text())["data"]["attributes"]
app = next(a for a in gem["apps"] if a.get("symbol") == "CARDS")

# The forming candle closes at the pool's price of the same read: the header and the chart are one
# feed on the live page, and two reads a minute apart would show two prices.
live_price = float(pool["base_token_price_usd"])
day[-1] = [day[-1][0], day[-1][1], max(day[-1][2], live_price), min(day[-1][3], live_price), live_price, day[-1][5]]
closes = [r[4] for r in day]


def ema(values, n):
    k, out_, prev = 2 / (n + 1), [], None
    for v in values:
        prev = v if prev is None else v * k + prev * (1 - k)
        out_.append(prev)
    return out_


def sma(values, n):
    return [None if i + 1 < n else sum(values[i + 1 - n:i + 1]) / n for i in range(len(values))]


# The rising trendline: from the September low, the flattest line no later low breaks (log scale).
def month(r):
    return datetime.fromtimestamp(r[0], timezone.utc).month


i0 = min((i for i, r in enumerate(day) if month(r) == 9), key=lambda i: day[i][3])
slopes = [(math.log(day[j][3]) - math.log(day[i0][3])) / (j - i0) for j in range(i0 + 3, len(day) - 1)]
slope = min(slopes)
j1 = i0 + 3 + slopes.index(slope)
trend_now = math.exp(math.log(day[i0][3]) + slope * (len(day) - 1 - i0))

price = float(pool["base_token_price_usd"])
chg24 = float(pool["price_change_percentage"]["h24"])
hi24, lo24 = max(r[2] for r in hour), min(r[3] for r in hour)
high30 = max(r[2] for r in day[-30:])


def pct(level):
    return (level / price - 1) * 100


DATA = {
    "candles": [[r[0], r[1], r[2], r[3], r[4], r[5]] for r in day],
    "ema20": ema(closes, 20), "sma50": sma(closes, 50),
    "supports": [0.152, 0.102],                       # the live page's two support lines
    "trend": {"i0": i0, "p0": day[i0][3], "slope": slope, "j1": j1},
    "markers": [{"n": 1, "i": len(day) - 2, "dir": "down"},   # bearish engulfing, Oct 12
                {"n": 2, "i": len(day) - 5, "dir": "up"}],    # bullish engulfing, Oct 9
    "scored": 10,
}
fmt_usd = lambda v: (f"${v / 1e9:.2f}B" if v >= 1e9 else f"${v / 1e6:.1f}M" if v >= 1e6
                     else f"${v / 1e3:.1f}K" if v >= 1e3 else f"${v:.0f}")
last = day[-1]
o, h, l, c = last[1], last[2], last[3], last[4]
logo = app.get("logo_data") or ""

SETUPS = [  # name, kind, when, textbook direction, tested-on rose first / fell first, built-on line, n
    ("Bearish engulfing after a rise", "Pattern", "1 candle ago", "down", 43, 51, "52% / 44% of 8,487", "100,292", "m1"),
    ("Bullish engulfing after a drop", "Pattern", "4 candles ago", "up", 44, 50, "55% / 41% of 8,932", "103,001", "m2"),
    ("Above a rising trendline", "Structure", "now", "up", 44, 50, "53% / 42% of 6,499", "65,404", "trend"),
    ("Above the 50-bar average", "Indicator", "now", "up", 45, 50, "55% / 42% of 10,509", "85,760", "sma"),
    ("MACD histogram falling", "Indicator", "now", "down", 44, 50, "51% / 44% of 11,335", "115,553", "macd"),
]


def setup_row(s, selected=False):
    name, kind, when, tb, up, dn, built, n, ref = s
    arrow = '<i class="tb up">▲</i>' if tb == "up" else '<i class="tb dn">▼</i>'
    tip = (f"{name}. The textbook calls it {'bullish' if tb == 'up' else 'bearish'}. On exchange charts "
           f"in the study's test years, {up}% rose 10% first and {dn}% fell 10% first within 30 candles "
           f"({n} cases); on the years it was built on, {built}.")
    num = f'<span class="nn">{name.split(" ")[0][:0]}</span>'
    return (f'<li class="setup{" sel" if selected else ""}" title="{tip}">'
            f'<span class="eye on"></span>{arrow}'
            f'<span class="sn"><b>{name}</b><em>{kind} · {when}</em></span>'
            f'<span class="odds"><span class="bar"><s class="u" style="width:{up}%"></s><s class="d" style="width:{dn}%"></s></span>'
            f'<span class="ud"><b class="g">{up}</b><b class="r">{dn}</b></span></span></li>')


setups_html = "".join(setup_row(s, i == 0) for i, s in enumerate(SETUPS))
levels = sorted([
    ("30d high", high30, "r"), ("Price", price, "p"), ("EMA 20", DATA["ema20"][-1], "bl"),
    ("Trendline", trend_now, "c"), ("SMA 50", DATA["sma50"][-1], "sl"),
    ("Support 1", 0.152, "g"), ("Support 2", 0.102, "g"),
], key=lambda r: -r[1])
BELL = ('<svg class="bell" viewBox="0 0 16 16"><path d="M8 2.2a3.9 3.9 0 0 0-3.9 3.9v2.6L2.6 11h10.8L11.9 8.7V6.1A3.9 3.9 0 0 0 8 2.2z'
        'M6.4 12.6a1.6 1.6 0 0 0 3.2 0"/></svg>')
levels_html = "".join(
    f'<li class="lv {k}"><span>{lab}</span><b>{v:.4f}</b><em>{"" if k == "p" else f"{pct(v):+.1f}%"}</em>'
    f'<i class="al{" on" if lab == "Trendline" else ""}">{"" if k == "p" else BELL}</i></li>'
    for lab, v, k in levels)

# The coin's Gem Screener card, as its pick card shows it today (tier, upside, revenue, tokens out, meter).
dl = app.get("dlevel") or {}
_v = {c["id"]: c["verdict"] for c in dl.get("checks") or []}
_rank = {"bad": 3, "caution": 2, "good": 1}
_sec = max((_v.get("audit"), _v.get("track_record")), key=lambda x: _rank.get(x, 0))
GUARDS = "".join(
    f'<span class="gd {"good" if v == "good" else "bad" if v == "bad" else "cau" if v == "caution" else "na"}">'
    f'{"✓" if v == "good" else "✗" if v == "bad" else "!" if v == "caution" else "?"} {name}</span>'
    for name, v in (("Rug power", _v.get("rug_power")), ("Holders paid", _v.get("reaches_you")),
                    ("Liquidity", _v.get("slippage")), ("Price run", _v.get("price_run")),
                    ("Security", _sec), ("Team", _v.get("team"))))
meter = "".join(f'<i class="m{c}"></i>' for c in "ggg" + "b" + "uu" + "rrrr")
circ = (app.get("cg") or {}).get("circ") or 0
total = (app.get("cg") or {}).get("total") or 0
tokens_out = round(100 * circ / total) if total else None
FUND = (f'<div class="card fund"><div class="vtop"><span class="h6">Fundamentals</span><a class="lnk">Gem Screener ›</a></div>'
        f'<div class="fgrid"><div><span>Tier</span><b class="g">S</b> <em class="sub">all 6 gates</em></div>'
        f'<div><span>Upside</span><b class="g">{app["potential"]:.1f}x</b></div>'
        f'<div><span>Revenue 30d</span><b>{fmt_usd(app["rev30d"])}</b></div>'
        f'<div><span>Tokens out</span><b>{tokens_out}%</b></div></div>'
        f'<div class="meter"><span>Degen meter</span><span class="cells">{meter}</span><b>{dl.get("level", "?")}<em>/10</em></b></div>'
        f'<div class="guards">{GUARDS}</div></div>')


# Live trades of the pool, newest first, as the pool reports them (GeckoTerminal), the same read as the header.
def trade_row(t):
    a = t["attributes"]
    buy = a["kind"] == "buy"
    px = float(a["price_to_in_usd"] if buy else a["price_from_in_usd"])
    usd = float(a["volume_in_usd"])
    when = a["block_timestamp"][11:19]
    return buy, px, usd, when


rows = [trade_row(t) for t in trades][:18]
vmax = max(r[2] for r in rows) or 1
latest = datetime.fromisoformat(trades[0]["attributes"]["block_timestamp"].replace("Z", "+00:00"))
window = [trade_row(t) for t in trades
          if (latest - datetime.fromisoformat(t["attributes"]["block_timestamp"].replace("Z", "+00:00"))).total_seconds() <= 900]
bought = sum(r[2] for r in window if r[0])
sold = sum(r[2] for r in window if not r[0])
# ---- the chartist: what an expert would say first, from the page's own facts ----------------
def trend_of(rows):
    """UP when the close is above a rising 20-bar EMA, DOWN when below a falling one, else SIDE."""
    cl = [r[4] for r in rows]
    e = ema(cl, 20)
    if cl[-1] > e[-1] and e[-1] > e[-4]:
        return "up"
    if cl[-1] < e[-1] and e[-1] < e[-4]:
        return "down"
    return "side"


weeks = {}
for r in day:
    key = datetime.fromtimestamp(r[0], timezone.utc).isocalendar()[:2]
    w = weeks.setdefault(key, [r[0], r[1], r[2], r[3], r[4], 0])
    w[2], w[3], w[4], w[5] = max(w[2], r[2]), min(w[3], r[3]), r[4], w[5] + r[5]
MTF = [("1H", trend_of(h1)), ("4H", trend_of(h4)), ("1D", trend_of(day)),
       ("1W", trend_of([weeks[k] for k in sorted(weeks)]))]
up30 = (closes[-1] / closes[-31] - 1) * 100
# The lean: textbook signals on the chart now, setups and timeframes alike, one point each.
bull = sum(1 for s in SETUPS if s[3] == "up") + sum(1 for _, t in MTF if t == "up")
bear = sum(1 for s in SETUPS if s[3] == "down") + sum(1 for _, t in MTF if t == "down")
lean = 50 + 50 * (bull - bear) / (bull + bear)
lean_word, lean_cls = (("Leans bullish", "g") if lean > 55 else ("Leans bearish", "r") if lean < 45
                       else ("Balanced", "s"))
arrow = {"up": "↗", "down": "↘", "side": "→"}
mtf_html = "".join(f'<span class="tf {t}"><b>{k}</b>{arrow[t]}</span>' for k, t in MTF)


def gauge(v):
    """A half-circle from bearish (left, red) to bullish (right, green), the needle at v (0-100)."""
    cx, cy, r = 100, 96, 78
    pt = lambda deg, rr=r: (cx + rr * math.cos(math.radians(deg)), cy - rr * math.sin(math.radians(deg)))
    arc = lambda a0, a1, col: (f'<path d="M{pt(a0)[0]:.1f},{pt(a0)[1]:.1f} A{r},{r} 0 0 1 {pt(a1)[0]:.1f},{pt(a1)[1]:.1f}" '
                               f'stroke="{col}" stroke-width="12" fill="none" stroke-linecap="round"/>')
    deg = 180 - 180 * v / 100
    nx, ny = pt(deg, r - 20)
    return (f'<svg viewBox="0 0 200 112" class="gauge">{arc(176, 124, "#ff4444")}{arc(116, 64, "#2a3a52")}{arc(56, 4, "#16d98c")}'
            f'<line x1="{cx}" y1="{cy}" x2="{nx:.1f}" y2="{ny:.1f}" stroke="#e8eef7" stroke-width="3" stroke-linecap="round"/>'
            f'<circle cx="{cx}" cy="{cy}" r="6" fill="#e8eef7"/>'
            f'<text x="16" y="110" fill="#ff4444" font-family="JetBrains Mono" font-size="10">BEAR</text>'
            f'<text x="184" y="110" fill="#16d98c" font-family="JetBrains Mono" font-size="10" text-anchor="end">BULL</text></svg>')


CHARTIST = f"""<div class="card chartist">
 <div class="vtop"><span class="h6">Chart read · 1D</span><span class="ai">AI chartist</span></div>
 <div class="read"><div class="big up">UPTREND <i>↗</i></div><div class="subread">+{up30:.0f}% in 30 days · short-term pullback</div></div>
 <div class="leanrow">{gauge(lean)}<div class="leantxt"><b class="{lean_cls}">{lean_word}</b><span>{bull} vs {bear} signals</span></div></div>
 <div class="mtf"><span class="lab">Trend</span>{mtf_html}</div>
 <ul class="keys">
  <li><span>Watch</span><b class="c">{trend_now:.3f}</b><em>below → 0.152</em></li>
  <li><span>Risk</span><b class="r">{high30:.3f}</b><em>bearish engulfing</em></li>
  <li class="flow2"><span>Flow 15m</span><b class="r">{fmt_usd(sold)}</b><em>sold vs <i class="g">{fmt_usd(bought)}</i> bought</em></li>
 </ul>
 <div class="edge"><span>Edge</span><b>NO VERDICT</b><span class="ii" title="The study measured exchange candles, not this pool. For a chart like this on an exchange its table reads: rose 10% first 44%, fell 10% first 53% within 30 candles; every chart: 45% / 51%.">i</span></div>
 <div class="ask"><span>Ask the chartist…</span><b>↵</b></div>
</div>"""

TRADES = (f'<div class="card trades"><div class="vtop"><span class="h6">Live trades</span>'
          f'<span class="flow" title="Bought and sold in this pool over the last 15 minutes"><b class="g">▲ {fmt_usd(bought)}</b> '
          f'<b class="r">▼ {fmt_usd(sold)}</b> <em>15 min</em></span></div>'
          f'<div class="th"><span>Price</span><span>Size</span><span>Time UTC</span></div><ul>'
          + "".join(f'<li style="--w:{max(2, round(100 * u / vmax))}%" class="{"b" if b else "s"}"><b>{p:.4f}</b>'
                    f'<span>{fmt_usd(u) if u >= 1 else "&lt;$1"}</span><em>{w}</em></li>' for b, p, u, w in rows)
          + '</ul></div>')

# The site header's nine tool icons, drawn plainly (home, swap, gems, loop, AI, card, chart, target, more).
NAV_ICONS = ["M2.5 7.5 8 3l5.5 4.5V13H2.5z", "M3 5h9l-2-2M13 11H4l2 2", "M4 3h8l2 3-6 7-6-7z",
             "M12.5 6A5 5 0 1 0 13 9.5M13 3v3h-3", "M8 2l1.6 4.4L14 8l-4.4 1.6L8 14l-1.6-4.4L2 8l4.4-1.6z",
             "M2 4h12v8H2zM2 7h12", "M2 13h12M3 10l3-3 3 2 4-5",
             "M8 2.5a5.5 5.5 0 1 0 0 11a5.5 5.5 0 1 0 0-11M8 6a2 2 0 1 0 0 4a2 2 0 1 0 0-4", "M8 3v10M3 8h10"]
TF = "".join(f'<button class="{"on" if t == "1D" else ""}">{t}</button>' for t in ("1H", "4H", "1D", "5D", "1W", "2W", "1M"))
RANGE = "".join(f'<button class="{"on" if t == "Fit" else ""}">{t}</button>' for t in ("90", "180", "All", "Fit"))


def check(label, on, sw=None, extra=""):
    swatch = f'<i class="sw" style="background:{sw}"></i>' if sw else '<i class="sw none"></i>'
    return f'<label class="ck"><span class="box{" on" if on else ""}"></span>{swatch}{label}{extra}</label>'


LAYERS = (
    '<div class="pop" id="layersPop"><div class="popcol"><h6>Levels</h6>'
    + check("Support", True, "var(--green)") + check("Resistance", True, "var(--red)")
    + check("Trendlines", True, "var(--cyan)") + check("Channels", True, "var(--blue)")
    + check("Wedges & triangles", True, "var(--blue)") + check("Fibonacci", False)
    + '</div><div class="popcol"><h6>Signals</h6>'
    + check("Pattern markers", True, "var(--cyan)") + check("Weekly Signal", True, "var(--green)")
    + check("Analyzer calls", False) + check("My bots", False) + check("Gem Screener picks", False)
    + '</div><div class="popcol"><h6>Indicators</h6>'
    + check("EMA 20", True, "var(--blue)") + check("SMA 50", True, "var(--dim)")
    + check("RSI", False) + check("MACD", False)
    + check("ATR", False, None, '<span class="inl">14 · cyan · 1.5 px</span>')
    + check("Volume", True, "var(--faint)")
    + '<div class="seg"><span>Volume profile</span><button class="on">Off</button><button>Total</button><button>Delta</button></div>'
    + check("Volume delta + CVD", False)
    + '</div></div>')

html = f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Chart Analyzer, a degen layout (mockup)</title>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;700&display=swap" rel="stylesheet">
<style>
:root{{--bg:#0a0e17;--panel:#0d1420;--panel2:#111a28;--line:rgba(0,150,255,.13);--line2:rgba(0,150,255,.22);
--text:#e8eef7;--dim:#8ea3bd;--faint:#5d7391;--cyan:#00cfff;--green:#00ff88;--cg:#16d98c;--red:#ff4444;--blue:#3b82f6;
--mono:'JetBrains Mono',ui-monospace,monospace;--ui:'Inter',system-ui,sans-serif;--head:'Archivo Black',var(--ui)}}
*{{box-sizing:border-box;margin:0;padding:0}}
html,body{{background:var(--bg);color:var(--text);font:13px/1.35 var(--ui)}}
button{{font:inherit;color:inherit;background:none;border:0;cursor:pointer}}
.site{{height:48px;display:flex;align-items:center;gap:20px;padding:0 16px;border-bottom:1px solid var(--line)}}
.brand b{{font:15px var(--head);letter-spacing:.2px}} .brand i{{display:block;font-style:normal;font-size:10px;color:var(--dim)}}
.nav{{display:flex;gap:6px;margin:0 auto;padding:4px;border:1px solid var(--line);border-radius:12px}}
.nav span{{width:30px;height:28px;border-radius:8px;display:grid;place-items:center;color:var(--dim)}}
.nav span.on{{background:rgba(0,207,255,.12);color:var(--cyan)}}
.nav svg{{width:16px;height:16px;stroke:currentColor;fill:none;stroke-width:1.7}}
.acct{{display:flex;gap:14px;align-items:center;color:var(--dim);font:12px var(--mono)}}
.acct .live{{color:var(--green);border:1px solid rgba(0,255,136,.35);border-radius:6px;padding:3px 8px}}
.coinbar{{height:62px;display:flex;align-items:center;gap:26px;padding:0 16px;border-bottom:1px solid var(--line);background:var(--panel)}}
.coin{{display:flex;align-items:center;gap:12px}}
.coin img{{width:38px;height:38px;border-radius:50%;box-shadow:0 0 0 2px rgba(0,207,255,.45)}}
.coin b{{font:20px var(--head);display:block;letter-spacing:.2px}}
.coin em{{font-style:normal;font:11px var(--mono);color:var(--dim);letter-spacing:.6px}}
.px{{display:flex;flex-direction:column}} .px b{{font:700 24px var(--mono);color:var(--red)}} .px em{{font:600 12px var(--mono);color:var(--red);font-style:normal}}
.stat{{display:flex;flex-direction:column;gap:3px}} .stat span{{font-size:11px;color:var(--dim)}} .stat b{{font:500 13px var(--mono)}}
.cbr{{margin-left:auto;display:flex;align-items:center;gap:10px}}
.gs{{display:flex;align-items:center;gap:8px;border:1px solid rgba(0,255,136,.35);border-radius:8px;padding:6px 10px;font:12px var(--mono)}}
.gs .tier{{background:var(--green);color:#04140c;font:12px var(--head);border-radius:4px;padding:1px 6px}}
.btn{{border:1px solid var(--line2);border-radius:8px;padding:7px 12px;font:600 12px var(--ui)}}
.btn.pri{{border-color:var(--cyan);color:var(--cyan)}}
.grid{{display:grid;grid-template-columns:var(--lw,330px) minmax(0,1fr) var(--rw,384px);gap:8px;padding:8px;height:calc(100vh - 110px);min-height:640px}}
.fund{{padding:14px 16px}}
.fund .lnk{{font:600 12px var(--ui);color:var(--cyan)}}
.fgrid{{display:grid;grid-template-columns:1fr 1fr;gap:12px 10px;margin-top:12px}}
.fgrid span{{display:block;font-size:11px;color:var(--dim);margin-bottom:2px}} .fgrid b{{font:700 15px var(--mono)}} .fgrid b.g{{color:var(--green)}}
.meter{{display:flex;align-items:center;gap:10px;margin-top:14px;padding-top:12px;border-top:1px solid var(--line)}}
.meter span:first-child{{font-size:11px;color:var(--dim);white-space:nowrap}}
.cells{{display:flex;gap:3px;flex:1}} .cells i{{flex:1;height:12px;border-radius:2px}}
.cells .mg{{background:var(--green)}} .cells .mb{{background:var(--blue)}} .cells .mu{{border:1px dashed var(--faint)}} .cells .mr{{background:rgba(255,68,68,.18)}}
.meter b{{font:700 16px var(--mono);color:var(--blue)}} .meter b em{{font-style:normal;font-size:11px;color:var(--dim)}}
.card{{background:var(--panel);border:1px solid var(--line);border-radius:10px}}
.left,.right{{display:flex;flex-direction:column;gap:8px;min-height:0}}
.h6,h6{{font:600 10.5px var(--ui);letter-spacing:1.4px;text-transform:uppercase;color:var(--dim)}}
.verdict{{padding:16px}}
.vtop{{display:flex;justify-content:space-between;align-items:center}}
.dot{{font:10.5px var(--mono);color:var(--green);letter-spacing:.8px}} .dot:before{{content:"";display:inline-block;width:7px;height:7px;border-radius:50%;background:var(--green);margin-right:6px;box-shadow:0 0 8px var(--green)}}
.vword{{font:34px var(--head);color:var(--blue);margin:14px 0 6px;letter-spacing:.3px}}
.vwhy{{color:var(--dim);font-size:13px}} .vwhy b{{color:var(--text);font-weight:600}}
.ii{{display:inline-grid;place-items:center;width:15px;height:15px;border:1px solid var(--faint);border-radius:50%;font:10px var(--mono);color:var(--dim);margin-left:4px;vertical-align:1px}}
.sum{{margin-top:16px;padding-top:14px;border-top:1px solid var(--line);display:grid;gap:10px}}
.sumrow{{display:flex;align-items:baseline;justify-content:space-between}}
.sumrow span{{color:var(--dim)}} .sumrow b{{font:700 15px var(--mono)}}
.flip{{font-size:13px;color:var(--text);line-height:1.45}} .flip b{{color:var(--cyan)}}
.levels{{padding:14px 16px}}
.lv.bl b{{color:#5b9bff}} .lv.sl b{{color:var(--dim)}}
.fgrid em.sub{{font-style:normal;font-size:11px;color:var(--dim);margin-left:4px}}
.trades{{flex:1;min-height:0;display:flex;flex-direction:column;overflow:hidden}}
.trades .flow{{font:11px var(--mono);color:var(--dim)}} .flow b.g{{color:var(--green)}} .flow b.r{{color:var(--red)}} .flow em{{font-style:normal;color:var(--faint);margin-left:4px}}
.trades .th{{display:grid;grid-template-columns:1fr 1fr 1fr;font-size:10px;color:var(--faint);padding:10px 6px 4px;text-transform:uppercase;letter-spacing:1px}}
.trades .th span+span,.trades li span,.trades li em{{text-align:right}}
.trades ul{{list-style:none;overflow:hidden;flex:1}}
.trades li{{display:grid;grid-template-columns:1fr 1fr 1fr;font:12px var(--mono);padding:3px 6px;position:relative}}
.trades li:before{{content:"";position:absolute;right:0;top:1px;bottom:1px;width:var(--w);opacity:.13;border-radius:2px}}
.trades li.b:before{{background:var(--green)}} .trades li.s:before{{background:var(--red)}}
.trades li b{{font-weight:500}} .trades li.b b{{color:var(--cg)}} .trades li.s b{{color:var(--red)}} .trades li em{{font-style:normal;color:var(--dim)}}
.levels ul{{list-style:none;margin-top:10px;display:grid;gap:2px}}
.lv{{display:grid;grid-template-columns:1fr auto 66px;gap:8px;align-items:center;padding:7px 8px;border-radius:6px;font:13px var(--mono)}}
.lv span{{font:13px var(--ui);color:var(--dim)}} .lv em{{font-style:normal;text-align:right;color:var(--dim)}}
.lv.p{{background:rgba(255,68,68,.08)}} .lv.p span,.lv.p b{{color:var(--red);font-weight:700}}
.lv.g b{{color:var(--green)}} .lv.r b{{color:var(--red)}} .lv.c b{{color:var(--cyan)}}
.lv:before{{content:"";width:3px;height:16px;border-radius:2px;position:absolute;margin-left:-8px}}
.mini{{font-size:11.5px;color:var(--faint);padding:10px 8px 0}}
.chartpane{{display:flex;flex-direction:column;min-width:0;position:relative}}
.tools{{height:42px;display:flex;align-items:center;gap:6px;padding:0 10px;border-bottom:1px solid var(--line);white-space:nowrap}}
.grp{{display:flex;gap:2px;padding-right:8px;margin-right:4px;border-right:1px solid var(--line)}}
.grp button{{padding:5px 8px;border-radius:6px;font:600 12px var(--mono);color:var(--dim)}}
.grp button.on{{background:rgba(0,207,255,.14);color:var(--cyan)}}
.dd{{padding:5px 9px;border-radius:6px;font:600 12px var(--ui);color:var(--text);display:flex;gap:6px;align-items:center}}
.dd:after{{content:"▾";color:var(--dim);font-size:10px}} .dd .n{{font:11px var(--mono);background:rgba(0,207,255,.14);color:var(--cyan);border-radius:4px;padding:0 5px}}
.dd.open{{background:rgba(0,207,255,.12)}}
.tg{{display:flex;gap:6px;align-items:center;font:600 12px var(--ui);color:var(--dim);padding:5px 6px}}
.tg i{{width:24px;height:13px;border-radius:7px;background:var(--panel2);border:1px solid var(--line2);position:relative}}
.tg i:after{{content:"";position:absolute;top:1px;left:1px;width:9px;height:9px;border-radius:50%;background:var(--faint)}}
.tg.on{{color:var(--text)}} .tg.on i{{background:rgba(0,207,255,.25);border-color:var(--cyan)}} .tg.on i:after{{left:12px;background:var(--cyan)}}
.tools .sp{{margin-left:auto}}
#chart{{flex:1;min-height:0;position:relative}}
#chart svg{{position:absolute;inset:0;width:100%;height:100%}}
.legend{{position:absolute;top:8px;left:12px;font:12px var(--mono);color:var(--dim);display:grid;gap:3px;pointer-events:none}}
.legend b{{color:var(--text);font-weight:500}} .legend .g{{color:var(--cg)}} .legend .r{{color:var(--red)}} .legend .c{{color:var(--cyan)}} .legend .bl{{color:#5b9bff}} .legend .sl{{color:var(--dim)}}
.callout{{position:absolute;background:rgba(13,20,32,.95);border:1px solid var(--cyan);border-radius:8px;padding:8px 10px;font-size:12px;width:250px;box-shadow:0 8px 24px rgba(0,0,0,.5)}}
.callout b{{display:block;font-size:12.5px;margin-bottom:3px}} .callout span{{color:var(--dim)}} .callout .g{{color:var(--green);font-family:var(--mono)}} .callout .r{{color:var(--red);font-family:var(--mono)}}
.pop{{display:none;position:absolute;top:44px;left:var(--popx,560px);z-index:5;background:#0e1724;border:1px solid var(--line2);border-radius:10px;padding:14px 16px;gap:26px;box-shadow:0 16px 40px rgba(0,0,0,.6)}}
body.layers .pop{{display:flex}}
.popcol{{display:flex;flex-direction:column;gap:7px;min-width:170px}} .popcol h6{{margin-bottom:3px}}
.ck{{display:flex;align-items:center;gap:8px;font-size:12.5px;white-space:nowrap}}
.ck .box{{width:14px;height:14px;border-radius:4px;border:1.5px solid var(--faint)}}
.ck .box.on{{background:var(--cyan);border-color:var(--cyan);box-shadow:inset 0 0 0 2px #0e1724}}
.ck .sw{{width:14px;height:3px;border-radius:2px}} .ck .sw.none{{background:transparent}}
.ck .inl{{font:11px var(--mono);color:var(--faint);margin-left:4px}}
.seg{{display:flex;align-items:center;gap:4px;font-size:12.5px;margin:2px 0 2px 22px}} .seg span{{margin-right:6px}}
.seg button{{font:600 11px var(--mono);padding:2px 7px;border-radius:5px;border:1px solid var(--line2);color:var(--dim)}} .seg button.on{{color:var(--cyan);border-color:var(--cyan)}}
.right .card{{padding:14px 12px 10px}}
.sethead{{display:flex;justify-content:space-between;align-items:baseline;padding:0 4px}}
.sethead .cols{{font:10.5px var(--mono);color:var(--faint)}} .sethead .cols b{{color:var(--green);font-weight:500}} .sethead .cols i{{color:var(--red);font-style:normal}}
.setups{{list-style:none;margin-top:10px;display:grid;gap:4px}}
.setup{{display:grid;grid-template-columns:16px 12px 1fr 92px;gap:8px;align-items:center;padding:8px 6px;border-radius:8px;border:1px solid transparent}}
.setup.sel{{border-color:var(--cyan);background:rgba(0,207,255,.07)}}
.setup .sn b{{display:block;font-weight:600;font-size:12.5px}} .setup .sn em{{font-style:normal;font-size:11px;color:var(--faint)}}
.eye{{width:14px;height:14px;border-radius:4px;border:1.5px solid var(--faint)}} .eye.on{{background:var(--cyan);border-color:var(--cyan);box-shadow:inset 0 0 0 2px var(--panel)}}
.tb{{font-style:normal;font-size:11px}} .tb.up{{color:var(--green)}} .tb.dn{{color:var(--red)}}
.odds .bar{{display:flex;height:5px;border-radius:3px;background:var(--panel2);overflow:hidden}}
.odds s{{display:block;height:100%}} .odds s.u{{background:var(--cg)}} .odds s.d{{background:var(--red);margin-left:auto}}
.ud{{display:flex;justify-content:space-between;font:12px var(--mono);margin-top:4px}} .ud .g{{color:var(--cg);font-weight:500}} .ud .r{{color:var(--red);font-weight:500}}
.base{{display:grid;grid-template-columns:1fr 92px;gap:8px;padding:8px 6px 8px 42px;border-top:1px dashed var(--line2);margin-top:6px;color:var(--dim);font-size:12px}}
.base .ud{{margin:0}}
.wk{{margin-top:6px;padding:8px 6px 4px 44px;color:var(--faint);font-size:11.5px}}
.foot{{display:flex;gap:16px;padding:10px 6px 0;border-top:1px solid var(--line);margin-top:10px;font-size:12px}}
.foot a{{color:var(--cyan);text-decoration:none}}
.below{{padding:4px 8px 24px;display:grid;gap:8px}}
.acc{{display:flex;align-items:center;gap:10px;padding:13px 16px;font:600 13px var(--ui)}} .acc:before{{content:"▸";color:var(--cyan)}}
.acc span{{color:var(--dim);font-weight:400}}
.disc{{color:var(--faint);font-size:11.5px;padding:2px 8px}}
.howto{{margin-top:auto;display:grid;gap:6px}}
.chartist{{padding:16px}}
.chartist .ai{{font:600 10.5px var(--mono);color:var(--cyan);border:1px solid rgba(0,207,255,.4);border-radius:5px;padding:2px 6px;letter-spacing:.5px}}
.read{{margin-top:10px}}
.leanrow{{display:flex;align-items:center;gap:12px;margin-top:8px}}
.leantxt b{{display:block;font:16px var(--head)}} .leantxt b.g{{color:var(--green)}} .leantxt b.r{{color:var(--red)}} .leantxt b.s{{color:var(--dim)}}
.leantxt span{{display:block;font-size:11.5px;color:var(--dim);margin-top:3px;line-height:1.35}}
.big{{font:31px var(--head);letter-spacing:.3px;line-height:1;white-space:nowrap}} .big.up{{color:var(--green)}} .big.down{{color:var(--red)}} .big i{{font-style:normal}}
.subread{{font:600 12px var(--mono);color:var(--cyan);margin-top:7px}}
.gauge{{width:146px;height:auto;flex:none}}
.mtf{{display:flex;gap:6px;align-items:center;margin-top:10px;flex-wrap:wrap}} .mtf .lab{{font-size:11px;color:var(--dim);margin-right:2px}}
.tf{{display:flex;gap:4px;align-items:center;font:600 12px var(--mono);padding:3px 7px;border-radius:6px;border:1px solid var(--line2)}}
.tf b{{font-weight:600;color:var(--dim)}} .tf.up{{color:var(--green);border-color:rgba(0,255,136,.35)}} .tf.down{{color:var(--red);border-color:rgba(255,68,68,.35)}} .tf.side{{color:var(--dim)}}
.says{{list-style:none;margin-top:12px;display:grid;gap:8px;font-size:13px;line-height:1.42}}
.says li{{padding-left:12px;position:relative}} .says li:before{{content:"";position:absolute;left:0;top:7px;width:5px;height:5px;border-radius:50%;background:var(--cyan)}}
.says b{{font-weight:600}} .says em{{font-style:normal;font-family:var(--mono);color:var(--cyan)}} .says em.r{{color:var(--red)}} .says em.g{{color:var(--green)}}
.keys{{list-style:none;margin-top:12px;display:grid;gap:6px}}
.keys li{{display:grid;grid-template-columns:62px 58px 1fr;gap:8px;align-items:baseline;font-size:12.5px}}
.keys span{{font:600 10.5px var(--ui);letter-spacing:1px;text-transform:uppercase;color:var(--dim)}}
.keys b{{font:700 14px var(--mono)}} .keys b.c{{color:var(--cyan)}} .keys b.r{{color:var(--red)}}
.keys em{{font-style:normal;color:var(--dim)}} .keys i.g{{font-style:normal;color:var(--green)}}
.edge{{margin-top:12px;padding-top:10px;border-top:1px solid var(--line);font-size:12px;color:var(--dim);display:grid;grid-template-columns:auto auto 1fr;gap:3px 8px;align-items:baseline}}
.edge>span:first-child{{font:600 10.5px var(--ui);letter-spacing:1.2px;text-transform:uppercase}}
.edge b{{font:13px var(--head);color:var(--blue)}} .edge em{{grid-column:1/-1;font-style:normal;line-height:1.4}}
.ask{{margin-top:12px;display:flex;justify-content:space-between;align-items:center;border:1px solid var(--line2);border-radius:8px;padding:8px 10px;color:var(--faint);font-size:12.5px}} .ask b{{color:var(--cyan)}}
.lv{{grid-template-columns:1fr auto 60px 18px !important}}
.al svg.bell{{width:14px;height:14px;stroke:var(--faint);fill:none;stroke-width:1.4;display:block}} .al.on svg{{stroke:var(--cyan);fill:rgba(0,207,255,.3)}}
.mini2{{font-size:11px;color:var(--faint);display:flex;align-items:center;gap:4px}} .mini2 svg{{width:12px;height:12px;stroke:var(--faint);fill:none;stroke-width:1.4}}
.levels .vtop{{margin-bottom:2px}}
.guards{{display:flex;flex-wrap:wrap;gap:5px;margin-top:12px}}
.gd{{font:600 11px var(--ui);padding:3px 7px;border-radius:5px;border:1px solid}}
.gd.good{{color:var(--green);border-color:rgba(0,255,136,.35)}} .gd.bad{{color:var(--red);border-color:rgba(255,68,68,.35)}}
.gd.cau{{color:var(--cyan);border-color:rgba(0,207,255,.35)}} .gd.na{{color:var(--faint);border-style:dashed;border-color:var(--faint)}}
.vword{{white-space:nowrap}} .tools{{overflow:hidden}} .left{{overflow:hidden}}
/* a laptop (1440 x 900): the same three columns, tighter */
@media (max-width:1600px){{.grid{{--lw:296px;--rw:340px}} .coinbar{{gap:18px}}
 .vword{{font-size:26px;margin:10px 0 4px}} .verdict{{padding:14px}} .sum{{margin-top:12px;padding-top:10px;gap:8px}}
 .lv{{padding:5px 8px}} .levels{{padding:12px 14px}} .fund{{padding:12px 14px}} .fgrid{{gap:8px 10px;margin-top:8px}} .meter{{margin-top:10px;padding-top:10px}}
 .acc{{padding:10px 14px}} .tools .fs,.tools .rp,.lv.bl,.lv.sl,.keys .flow2,.howto .acc,.guards{{display:none}}
 .chartist{{padding:13px 14px}} .big{{font-size:26px}} .gauge{{width:112px}} .says{{gap:6px;font-size:12.5px;margin-top:10px}}
 .setup{{grid-template-columns:16px 12px 1fr 84px}} .base{{grid-template-columns:1fr 84px}}}}
.agent{{font:600 12px var(--ui)}}
/* phone */
@media (max-width:700px){{
 .nav,.acct .hide,.stat.wide,.cbr .btn.hide,.cbr .agent{{display:none}}
 .site{{height:44px}}
 .coinbar{{height:auto;flex-wrap:wrap;gap:10px 16px;padding:10px 12px}}
 .coin b{{font-size:17px}} .px b{{font-size:20px}}
 .cbr{{margin-left:0;width:100%;justify-content:space-between}}
 .grid{{display:flex;flex-direction:column;height:auto;padding:6px;gap:6px}}
 .left,.right{{display:contents}}
 .chartist{{order:1}} .chartpane{{order:2;height:380px}} .right .card:first-child{{order:3}} .levels{{order:4}} .howto{{order:9}}
 .fund,.trades,.callout,.legend div:nth-child(2),.acc span{{display:none}}
 .legend{{font-size:11px;left:8px;top:6px}} .legend .ohlc{{display:none}}
 .verdict{{padding:10px 12px;display:grid;grid-template-columns:auto 1fr;gap:4px 12px;align-items:center}}
 .vtop{{grid-column:1/-1}} .vword{{font-size:20px;margin:0}} .vwhy{{font-size:12px}}
 .sum{{display:none}}
 .tools{{overflow-x:auto;gap:4px}} .tools .hide{{display:none}}
 .setups{{display:flex;overflow-x:auto;gap:8px;scroll-snap-type:x mandatory}}
 .setup{{min-width:300px;scroll-snap-align:start;border-color:var(--line2)}}
 .base,.wk{{padding-left:6px}}
}}
</style></head>
<body class="__STATE__">
<header class="site">
 <div class="brand"><b>EventTrader</b><i>Financial AI Models</i></div>
 <nav class="nav">{''.join(f'<span class="{"on" if k == 6 else ""}"><svg viewBox="0 0 16 16"><path d="{d}"/></svg></span>' for k, d in enumerate(NAV_ICONS))}</nav>
 <div class="acct"><span class="hide">expire76</span><span class="live">● LIVE</span></div>
</header>
<section class="coinbar">
 <div class="coin"><img src="{logo}" alt=""><div><b>Collector Crypt</b><em>CARDS / USDC · RAYDIUM · SOLANA ▾</em></div></div>
 <div class="px"><b>{price:.4f}</b><em>{chg24:+.2f}% 24h</em></div>
 <div class="stat"><span>24h high</span><b>{hi24:.4f}</b></div>
 <div class="stat"><span>24h low</span><b>{lo24:.4f}</b></div>
 <div class="stat"><span>24h volume</span><b>{fmt_usd(float(pool['volume_usd']['h24']))}</b></div>
 <div class="stat wide"><span>Pool liquidity</span><b>{fmt_usd(float(pool['reserve_in_usd']))}</b></div>
 <div class="stat wide"><span>Market cap</span><b>{fmt_usd(float(pool['market_cap_usd']))}</b></div>
 <div class="stat wide"><span>FDV</span><b>{fmt_usd(float(pool['fdv_usd']))}</b></div>
 <div class="cbr">
  <a class="gs"><span class="tier">S</span>Gem Screener · {app['potential']:.1f}x upside ›</a>
  <button class="btn agent">Ask your AI ›</button>
  <button class="btn hide">Share</button><button class="btn pri">+ New</button>
 </div>
</section>
<main class="grid">
 <aside class="left">
  {CHARTIST}
  {FUND}
  <div class="howto"><div class="card acc">How it's measured</div>
   <div class="disc">A read of the chart, never a promise or a forecast. Not financial advice; it places no orders.</div></div>
 </aside>
 <section class="card chartpane">
  <div class="tools">
   <div class="grp">{TF}</div><div class="grp hide">{RANGE}</div>
   <button class="dd hide">Candles</button>
   <button class="dd layersbtn">Layers <span class="n">8</span></button>
   <span class="tg on hide"><i></i>Log</span><span class="tg hide rp"><i></i>Replay</span>
   <span class="sp"></span><span class="tg hide fs" style="color:var(--faint)">⤢ Full screen</span>
  </div>
  {LAYERS}
  <div id="chart"><svg id="svg"></svg>
   <div class="legend"><div><b>CARDS/USDC · 1D · Raydium</b><span class="ohlc">&nbsp; O <b>{o:.4f}</b> H <b>{h:.4f}</b> L <b>{l:.4f}</b> C <b class="{'g' if c >= o else 'r'}">{c:.4f}</b></span></div>
   <div><span class="bl">EMA 20 <b class="bl">{DATA['ema20'][-1]:.4f}</b></span> &nbsp; <span class="sl">SMA 50 <b class="sl">{DATA['sma50'][-1]:.4f}</b></span> &nbsp; Vol <b>{fmt_usd(last[5])}</b></div></div>
  </div>
 </section>
 <aside class="right"><div class="card">
  <div class="sethead"><span class="h6">Setups now · 5</span><span class="cols" title="Of exchange charts with the same setup, in the years the study was tested on: the share that rose 10% first, and the share that fell 10% first, within 30 candles."><b>↑ rose first</b> · <i>↓ fell first</i></span></div>
  <ul class="setups">{setups_html}</ul>
  <div class="base"><span>Average chart</span><span class="odds"><span class="bar"><s class="u" style="width:45%"></s><s class="d" style="width:51%"></s></span><span class="ud"><b class="g">45</b><b class="r">51</b></span></span></div>
  <div class="wk">Weekly Signal · needs 42 weeks of candles</div>
  <div class="foot"><a>The study ›</a><a>Calls ledger ›</a><a>How it's measured ›</a></div>
 </div>
 <div class="card levels"><div class="vtop"><span class="h6">Key levels · log</span><span class="mini2">{BELL} alert me when crossed</span></div><ul>{levels_html}</ul></div>
 {TRADES}
 </aside>
</main>
<script>
const D = {json.dumps(DATA)};
const MONTHS = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"];
function draw() {{
  const box = document.getElementById('chart'), svg = document.getElementById('svg');
  const W = box.clientWidth, H = box.clientHeight, phone = W < 600;
  const axisW = phone ? 54 : 70, timeH = 22, padTop = phone ? 44 : 52;
  const C = D.candles, N = C.length, show = Math.min(N, phone ? 80 : 150), first = N - show, slots = show + (phone ? 3 : 7);
  const plotW = W - axisW, cw = plotW / slots, volH = (H - timeH) * 0.15, priceH = H - timeH - volH - padTop - 10;
  const vis = C.slice(first);
  let lo = Math.min(...vis.map(r => r[3]), ...D.supports) * 0.96, hi = Math.max(...vis.map(r => r[2])) * 1.09;
  const L = Math.log, y = p => padTop + (L(hi) - L(p)) / (L(hi) - L(lo)) * priceH, x = i => (i - first + 0.5) * cw;
  const vmax = Math.max(...vis.map(r => r[5])), vy0 = H - timeH;
  let s = '';
  // grid + price axis
  const ticks = [0.04,0.05,0.06,0.08,0.1,0.12,0.15,0.2,0.25,0.3,0.4,0.5].filter(t => t > lo && t < hi);
  for (const t of ticks) {{ s += `<line x1="0" x2="${{plotW}}" y1="${{y(t)}}" y2="${{y(t)}}" stroke="rgba(0,150,255,.07)"/><text x="${{plotW + 8}}" y="${{y(t) + 4}}" fill="#5d7391" font-family="JetBrains Mono" font-size="11">${{t.toFixed(t < .1 ? 3 : 2)}}</text>`; }}
  let lastM = -1;
  for (let i = first; i < N; i++) {{ const d = new Date(C[i][0] * 1000), m = d.getUTCMonth();
    if (m !== lastM && d.getUTCDate() <= 3) {{ s += `<line x1="${{x(i)}}" x2="${{x(i)}}" y1="${{padTop - 10}}" y2="${{vy0}}" stroke="rgba(0,150,255,.06)"/><text x="${{x(i)}}" y="${{H - 6}}" fill="#5d7391" font-family="JetBrains Mono" font-size="11" text-anchor="middle">${{MONTHS[m]}}</text>`; lastM = m; }} }}
  s += `<line x1="${{plotW}}" x2="${{plotW}}" y1="0" y2="${{vy0}}" stroke="rgba(0,150,255,.13)"/><line x1="0" x2="${{W}}" y1="${{vy0}}" y2="${{vy0}}" stroke="rgba(0,150,255,.13)"/>`;
  // scored window
  const sw0 = x(N - D.scored) - cw / 2, sw1 = x(N - 1) + cw / 2;
  s += `<rect x="${{sw0}}" y="${{padTop - 18}}" width="${{sw1 - sw0}}" height="${{vy0 - padTop + 18}}" fill="rgba(0,207,255,.05)" stroke="rgba(0,207,255,.25)" stroke-dasharray="3 4"/>` + (phone ? '' : `<text x="${{sw0 + 4}}" y="${{padTop - 6}}" fill="#00cfff" opacity=".8" font-family="JetBrains Mono" font-size="10" letter-spacing="1">SCORED · 10</text>`);
  // volume
  for (let i = first; i < N; i++) {{ const r = C[i], up = r[4] >= r[1], hgt = r[5] / vmax * volH;
    s += `<rect x="${{x(i) - cw * .34}}" y="${{vy0 - hgt}}" width="${{cw * .68}}" height="${{hgt}}" fill="${{up ? '#16d98c' : '#ff4444'}}" opacity=".28"/>`; }}
  // supports
  for (const [k, lv] of D.supports.entries()) {{
    let i1 = first; for (let i = first; i < N; i++) if (Math.abs(C[i][3] / lv - 1) < .03) {{ i1 = i; break; }}
    s += `<line x1="${{x(i1)}}" x2="${{plotW}}" y1="${{y(lv)}}" y2="${{y(lv)}}" stroke="#00ff88" stroke-width="1.2" opacity=".75"/>`;
    for (let i = first; i < N; i++) if (Math.abs(C[i][3] / lv - 1) < .025) s += `<circle cx="${{x(i)}}" cy="${{y(lv)}}" r="3.2" fill="#0a0e17" stroke="#00ff88" stroke-width="1.3"/>`;
    s += `<rect x="${{plotW + 2}}" y="${{y(lv) - 9}}" width="${{axisW - 4}}" height="18" rx="4" fill="#00ff88"/><text x="${{plotW + axisW / 2}}" y="${{y(lv) + 4}}" fill="#04140c" font-family="JetBrains Mono" font-weight="700" font-size="11" text-anchor="middle">S${{k + 1}} ${{lv.toFixed(3)}}</text>`; }}
  // rising trendline (log)
  const T = D.trend, ty = i => y(Math.exp(L(T.p0) + T.slope * (i - T.i0)));
  s += `<line x1="${{x(T.i0)}}" y1="${{ty(T.i0)}}" x2="${{plotW}}" y2="${{ty(T.i0 + (plotW / cw - (T.i0 - first) - .5))}}" stroke="#00cfff" stroke-width="1.5"/>`;
  s += `<circle cx="${{x(T.i0)}}" cy="${{ty(T.i0)}}" r="3.2" fill="#0a0e17" stroke="#00cfff" stroke-width="1.3"/><circle cx="${{x(T.j1)}}" cy="${{ty(T.j1)}}" r="3.2" fill="#0a0e17" stroke="#00cfff" stroke-width="1.3"/>`;
  // averages
  const path = (arr, col) => {{ let p = ''; for (let i = first; i < N; i++) if (arr[i] != null) p += (p ? 'L' : 'M') + x(i).toFixed(1) + ',' + y(arr[i]).toFixed(1);
    return `<path d="${{p}}" fill="none" stroke="${{col}}" stroke-width="1.3" opacity=".85"/>`; }};
  s += path(D.ema20, '#3b82f6') + path(D.sma50, '#8ea3bd');
  // candles
  for (let i = first; i < N; i++) {{ const [t, o, h, l, c] = C[i], up = c >= o, col = up ? '#16d98c' : '#ff4444';
    const bt = y(Math.max(o, c)), bb = y(Math.min(o, c));
    s += `<line x1="${{x(i)}}" x2="${{x(i)}}" y1="${{y(h)}}" y2="${{y(l)}}" stroke="${{col}}" stroke-width="1"/>`;
    s += `<rect x="${{x(i) - cw * .36}}" y="${{bt}}" width="${{cw * .72}}" height="${{Math.max(1, bb - bt)}}" fill="${{col}}"/>`; }}
  // pattern markers
  for (const m of D.markers) {{ const r = C[m.i], cx = x(m.i), cy = y(r[2]) - 16, sel = m.n === 1;
    if (sel) s += `<circle cx="${{cx}}" cy="${{cy}}" r="15" fill="rgba(0,207,255,.18)"/><line x1="${{cx}}" x2="${{cx}}" y1="${{cy + 9}}" y2="${{y(r[2]) - 2}}" stroke="#00cfff"/>`;
    s += `<circle cx="${{cx}}" cy="${{cy}}" r="9" fill="${{sel ? '#00cfff' : '#0a0e17'}}" stroke="#00cfff" stroke-width="1.5"/><text x="${{cx}}" y="${{cy + 4}}" fill="${{sel ? '#04121a' : '#e8eef7'}}" font-family="JetBrains Mono" font-weight="700" font-size="11" text-anchor="middle">${{m.n}}</text>`; }}
  // price line + tag
  const last = C[N - 1], lc = last[4], lcol = lc >= last[1] ? '#16d98c' : '#ff4444';
  s += `<line x1="0" x2="${{plotW}}" y1="${{y(lc)}}" y2="${{y(lc)}}" stroke="${{lcol}}" stroke-dasharray="2 3" opacity=".7"/><rect x="${{plotW + 2}}" y="${{y(lc) - 10}}" width="${{axisW - 4}}" height="20" rx="4" fill="${{lcol}}"/><text x="${{plotW + axisW / 2}}" y="${{y(lc) + 4}}" fill="#04140c" font-family="JetBrains Mono" font-weight="700" font-size="11.5" text-anchor="middle">${{lc.toFixed(4)}}</text>`;
  // the selected setup's callout: in the empty sky left of both markers, a thin line to its own
  const m1 = D.markers[0], m2 = D.markers[1], cx1 = x(m1.i), cy1 = y(C[m1.i][2]) - 16, cx2 = x(m2.i);
  const cwid = 250, coL = Math.max(8, cx2 - cwid - 40), coT = padTop + 4;
  if (!phone) s += `<path d="M${{coL + cwid}},${{coT + 18}} L${{cx1 - 11}},${{cy1}}" stroke="#00cfff" stroke-width="1" opacity=".7" fill="none"/>`;
  svg.setAttribute('viewBox', `0 0 ${{W}} ${{H}}`); svg.innerHTML = s;
  let co = document.querySelector('.callout'); if (!co) {{ co = document.createElement('div'); co.className = 'callout'; box.appendChild(co); }}
  co.innerHTML = '<b>1 · Bearish engulfing after a rise</b><span>Confirmed 1 candle ago. Textbook: bearish. On exchange charts: </span><span class="g">↑43%</span> <span class="r">↓51%</span><span>, about the average chart.</span>';
  co.style.width = cwid + 'px'; co.style.left = coL + 'px'; co.style.top = coT + 'px';
  const lb = document.querySelector('.layersbtn'); if (lb) document.documentElement.style.setProperty('--popx', (lb.offsetLeft) + 'px');
}}
if (location.search.includes('layers')) {{ document.body.classList.add('layers'); document.querySelector('.layersbtn').classList.add('open'); }}
document.fonts.ready.then(draw); window.addEventListener('resize', draw);
</script>
</body></html>"""

page = out / "mockup.html"
page.write_text(html.replace("__STATE__", ""), encoding="utf-8")

from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    for name, w, h, q, mobile in (("desktop-1920", 1920, 1080, "", False), ("desktop-1440", 1440, 900, "", False),
                                  ("layers-1920", 1920, 1080, "?layers", False), ("phone-390", 390, 844, "", True)):
        tab = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=2 if mobile else 1,
                               is_mobile=mobile, has_touch=mobile)
        tab.goto(page.resolve().as_uri() + q)
        tab.wait_for_load_state("networkidle")
        tab.wait_for_timeout(600)
        tab.screenshot(path=str(out / f"{name}.png"), full_page=mobile)
        tab.close()
    browser.close()
print("trend from", day[i0][0], "slope", round(slope, 5), "today", round(trend_now, 4), "30d high", high30,
      "24h", round(hi24, 4), round(lo24, 4), "price", price)
