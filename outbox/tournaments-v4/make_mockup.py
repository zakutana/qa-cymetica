"""Build lobby.html, table.html, tune.html and join.html (this folder): Agent Tournaments v4.

The operator, 2026-10-26, looking at the live page (table 15, our seat 87) after v3 shipped as ET-31702:
  * "predelame ... na 6 hracu u stolu": every table is 6 seats, not 10.
  * "Nexus tunes it for you at nahradi ... jen v Pro modu kdyz si platime a bude tam switch ... a at ho sprovozni
    protoze vubec nefunguje, changelog je skoro prazdny a pritom je nas bot prodelecny ... kdyz vidi ze prohrava tak
    ma hned tunit". The live read (2026-10-26, our key) found the cause: it tunes only after 5 NEW closed trades, our
    bot closed its last trade on 20 Oct 14:10, so after its one tune on 21 Oct it has waited six days for trades that
    do not come. So the switch is for a paid NEXUS plan, it checks on a clock, and every check is a row.
  * "Live stoly uz s realnymi USDC ... buy in na 1$ a 5$ ... switch na paper a live": a Paper | Live switch.
  * "musi to byt otevrene i pro externi agenty ... nahraje svou DEX penezenku kde se pak bude zpetne monitorovat
    historie transakci ... podle toho se urci ktery stul": join with a wallet; its on-chain record sets the band.
  * The dots on the race are YOUR TRADES (the legend's second entry): circles that overlap where trades are minutes
    apart. Here markers that touch merge into one with a count.

Real figures (data.json, fetch.py, GET on 2026-10-26): table 15 (ET10 100, running): its standings, race lines, the
pot (100 ET10) and what it splits; our seat's bot settings, NEXUS lock and 17 closed trades. The table is cut to its
six best-ranked seats to show what six looks like. Invented, and said so in request.md: the Live tables' ids and
seat counts, the wallet and its record, the bands' thresholds, and the Tune log's rows after 20 Oct 14:05 (the first
rows replay our real trades of 20 Oct 13:55 to 14:10 as the new rule would have read them).
Palette: the site's navy, cyan, green, red and blue, plus the avatar tints their page already uses.
"""
from __future__ import annotations

import html
import importlib.util
import json
import math
from datetime import datetime, timezone
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, HERE.parent / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


lc = _load("lobby_card", "tournaments-lobby-card/make_mockup.py")
td = _load("table_detail", "tournaments-table-detail/make_mockup.py")
DATA = json.loads((HERE / "data.json").read_text(encoding="utf-8"))
T = DATA["table"]
OWN = DATA["owner"]
MINE = OWN["my_seat"]["seat_id"]
SEATS = 6
NOW = datetime.now(timezone.utc)

# the six best-ranked seats of table 15 (ours is the fifth)
SIX = sorted(T["standings"], key=lambda s: s["rank"])[:SEATS]
SIX_IDS = {s["seat_id"] for s in SIX}

LOCK = ('<svg viewBox="0 0 16 16" width="14" height="14"><rect x="3" y="7" width="10" height="7" rx="2" fill="none" '
        'stroke="currentColor" stroke-width="1.5"/><path d="M5.5 7V5a2.5 2.5 0 0 1 5 0v2" fill="none" '
        'stroke="currentColor" stroke-width="1.5"/></svg>')
WALLET = ('<svg viewBox="0 0 16 16" width="16" height="16"><rect x="1.5" y="3.5" width="13" height="10" rx="2.5" '
          'fill="none" stroke="currentColor" stroke-width="1.5"/><path d="M1.5 6.5h13" stroke="currentColor" '
          'stroke-width="1.5"/><circle cx="11.5" cy="10" r="1" fill="currentColor"/></svg>')

CSS = """
.wrap{max-width:1240px}
.v4hero{margin:6px 0 24px}
.v4hero h1{font-family:'Archivo Black';font-weight:400;font-size:62px;line-height:1.04;letter-spacing:-.01em;margin-top:16px}
.v4hero h1 em{font-style:normal;color:var(--green)}
.v4hero .chip.live{display:inline-block;font-size:12px;padding:6px 14px;letter-spacing:.16em}
.tabsrow{display:flex;align-items:center;gap:20px;margin:0 0 20px;padding-bottom:16px;border-bottom:1px solid var(--line)}
.tabs{display:flex;gap:4px;background:var(--deep);border:1px solid var(--line2);border-radius:14px;padding:4px}
.tabs span{padding:9px 20px;border-radius:10px;color:var(--dim2);font-weight:700;font-size:13px}
.tabs span.on{background:var(--navy2);color:var(--text);box-shadow:0 0 0 1px var(--line3) inset}
.modesw{margin-left:auto;display:flex;gap:4px;background:var(--deep);border:1px solid var(--line2);border-radius:14px;padding:4px}
.modesw span{padding:9px 20px;border-radius:10px;color:var(--dim2);font-weight:700;font-size:13px;letter-spacing:.06em;display:flex;align-items:center;gap:8px}
.modesw span.on{background:var(--cyan);color:var(--bg);box-shadow:0 0 14px rgba(0,207,255,.4)}
.modesw span i{width:8px;height:8px;border-radius:50%;background:var(--bg)}
.livenote{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:12px;margin:0 0 26px}
.livenote div{background:var(--navy);border:1px solid var(--line2);border-radius:14px;padding:12px 16px;min-width:0}
.livenote b{display:block;font-family:'Archivo Black';font-weight:400;font-size:22px;color:var(--cyan);white-space:nowrap}
.livenote span{display:block;font-size:12px;color:var(--dim);margin-top:4px}
.grid.g3{gap:20px}
.g3 .chips{flex-wrap:wrap;gap:6px;min-height:64px;align-content:flex-start}
.g3 .chip.band{color:var(--cyan);border-color:rgba(0,207,255,.6)}
.g3 .oval{height:230px;margin:12px 4px 10px}
.g3 .pool .usd{font-size:38px}
.slot.taken{border:1.5px solid currentColor;background:var(--deep)}
.slot.taken svg{width:16px;height:16px}
/* the table page */
.top .facts{margin-left:18px}
.st{grid-template-columns:30px minmax(0,1fr) 92px 170px 110px}
.big .oval{height:420px;margin:8px 70px 60px}
.big .oval .ring{inset:13% 8%}
.big .av{width:46px;height:46px}.big .av svg{width:24px;height:24px}
.big .seat .lbl{top:50px}
.big .seat .lbl span{max-width:190px}
.apply .go{margin-top:0;display:block}
.side .lrow{grid-template-columns:auto auto 1fr;gap:4px 10px;padding:9px 0}
.side .lrow>div{grid-column:1/-1}
.chg2{margin-top:12px;border-top:1px solid var(--line);padding-top:10px;font-size:11.5px;color:var(--dim2)}
.chg2 b{color:var(--text);display:block;margin-bottom:6px;font-size:12px}
.chg2 div{display:flex;align-items:center;gap:8px;margin-top:4px}
.big .seat.me .lbl{border-color:var(--cyan)}
.who2{display:flex;gap:6px;align-items:center}
.chip.who{font-size:10px;letter-spacing:.1em;padding:2px 8px;border-color:rgba(0,207,255,.6);color:var(--cyan)}
.chip.who.o{border-color:var(--line3);color:var(--dim)}
/* the race */
.race .lg{margin-left:auto;display:flex;gap:16px;font-size:11px;color:var(--dim2);letter-spacing:.08em;font-weight:700;align-items:center}
.race .lg span{display:flex;align-items:center;gap:6px;white-space:nowrap}
.race .lg i{display:inline-block;width:16px;height:3px;border-radius:2px}
.race .lg i.dot{width:11px;height:11px;border-radius:50%;border:2px solid var(--text);background:var(--bg)}
.race .lg i.n{width:16px;height:16px;border-radius:50%;border:2px solid var(--text);background:var(--bg);font-style:normal;font-size:9px;line-height:12px;text-align:center;color:var(--text);font-weight:700}
/* NEXUS Tune */
.tunep{border:1px solid rgba(0,207,255,.45);background:rgba(0,207,255,.05)}
.tunep .hd{display:flex;align-items:center;gap:12px}
.tunep .hd .k{flex:1}
.sw{width:46px;height:26px;border-radius:99px;background:var(--line3);position:relative;flex:none}
.sw:after{content:'';position:absolute;top:3px;left:3px;width:20px;height:20px;border-radius:50%;background:var(--dim2)}
.sw.on{background:var(--green);box-shadow:0 0 14px rgba(0,255,136,.45)}
.sw.on:after{left:23px;background:var(--bg)}
.plan{display:inline-flex;align-items:center;gap:6px;font-size:10.5px;font-weight:700;letter-spacing:.12em;color:var(--cyan);
 border:1px solid rgba(0,207,255,.6);border-radius:99px;padding:3px 9px;white-space:nowrap}
.tunep .sub{font-size:12.5px;color:var(--dim);line-height:1.55;margin:10px 0 0}
.tunep .stat{display:flex;gap:18px;margin:12px 0 4px;font-size:12px;color:var(--dim2)}
.tunep .stat b{color:var(--text);font-size:15px;margin-right:4px}
.tunep .more{margin-top:10px;text-align:center;font-size:12px;font-weight:700;color:var(--cyan)}
.trig{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:10px;margin:14px 0 6px}
.trig div{background:var(--deep);border-radius:12px;padding:10px 12px;min-width:0}
.trig b{display:block;font-family:'Archivo Black';font-weight:400;font-size:24px;color:var(--green);white-space:nowrap}
.trig span{display:block;font-size:10.5px;letter-spacing:.12em;color:var(--dim2);font-weight:700}
.trig em{display:block;font-style:normal;font-size:12px;color:var(--dim);margin-top:2px}
.lg2{margin-top:10px}
.lrow{display:grid;grid-template-columns:104px 74px minmax(0,1fr);gap:12px;align-items:start;padding:10px 0;border-top:1px solid var(--line);font-size:13px}
.lrow .tm{color:var(--dim2);font-size:12px;white-space:nowrap}
.lrow .tg{font-size:10.5px;font-weight:700;letter-spacing:.1em;border-radius:6px;padding:3px 8px;text-align:center;border:1px solid var(--line3);color:var(--dim)}
.lrow .tg.t{color:var(--bg);background:var(--green);border-color:var(--green)}
.lrow b{display:block;font-size:13px}
.lrow em{display:block;font-style:normal;font-size:12px;color:var(--dim);margin-top:2px}
.tunep.off{border-color:var(--line3);background:var(--navy)}
.tunep.off .hd .k{color:var(--dim2)}
.tunep .up{display:block;text-align:center;border-radius:10px;padding:10px;font-weight:700;color:var(--bg);background:var(--cyan);box-shadow:0 0 14px rgba(0,207,255,.35);margin-top:14px}
.tunepair{display:grid;grid-template-columns:minmax(0,1.5fr) minmax(0,1fr);gap:18px;align-items:start;padding:24px;background:var(--bg)}
/* join with a wallet */
.jn{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:22px;align-items:start}
.jn h1{font-family:'Archivo Black';font-weight:400;font-size:44px;line-height:1.05;margin:14px 0 8px}
.jn .lead{font-size:14px;color:var(--dim);margin-bottom:22px}
.stp{display:flex;gap:10px;margin-bottom:22px}
.stp div{flex:1;background:var(--navy);border:1px solid var(--line2);border-radius:12px;padding:10px 12px;font-size:12.5px;color:var(--dim);min-width:0}
.stp div b{display:flex;align-items:center;gap:8px;color:var(--text);margin-bottom:2px}
.stp div b i{font-style:normal;width:20px;height:20px;border-radius:50%;background:var(--cyan);color:var(--bg);display:grid;place-items:center;font-size:11px}
.stp div.done b i{background:var(--green)}
.addr{display:flex;align-items:center;gap:10px;background:var(--deep);border-radius:12px;padding:12px 14px;margin:6px 0 14px}
.addr b{font-size:16px}.addr .ok{margin-left:auto;color:var(--green);font-size:12px;font-weight:700}
.chal{font-size:12px;color:var(--dim);background:var(--deep);border:1px dashed var(--line3);border-radius:10px;padding:8px 12px;margin:-6px 0 14px;word-break:break-word}
.chal span{display:block;font-size:10px;letter-spacing:.12em;color:var(--dim2);font-weight:700;margin-bottom:2px}
.chain{display:flex;gap:6px;margin-bottom:12px}
.chain span{font-size:11px;font-weight:700;letter-spacing:.08em;border:1px solid var(--line3);border-radius:8px;padding:5px 10px;color:var(--dim2)}
.chain span.on{color:var(--cyan);border-color:rgba(0,207,255,.6)}
.rec{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:8px;margin:12px 0}
.rec div{background:var(--deep);border-radius:12px;padding:10px 12px}
.rec b{display:block;font-family:'Archivo Black';font-weight:400;font-size:26px}
.rec span{font-size:10.5px;letter-spacing:.12em;color:var(--dim2);font-weight:700}
.band{display:flex;align-items:center;gap:12px;border:1px solid rgba(0,207,255,.5);background:rgba(0,207,255,.06);border-radius:12px;padding:12px 14px}
.band b{font-family:'Archivo Black';font-weight:400;font-size:18px;color:var(--cyan)}
.band span{font-size:12px;color:var(--dim)}
.tbl{display:grid;grid-template-columns:minmax(0,1fr) 74px 118px;gap:10px;align-items:center;padding:12px 0;border-top:1px solid var(--line);font-size:13px}
.tbl.hd{border-top:none;padding:0 0 4px;font-size:10.5px;letter-spacing:.12em;color:var(--dim2);font-weight:700}
.tbl b{display:block;font-size:15px}.tbl em{display:block;font-style:normal;font-size:11.5px;color:var(--dim)}
.tbl .jo{text-align:center;border-radius:10px;padding:9px 6px;font-weight:700;color:var(--bg);background:var(--green);box-shadow:0 0 14px rgba(0,255,136,.35);white-space:nowrap}
.tbl.lock{opacity:.55}.tbl.lock .jo{background:none;color:var(--dim2);border:1px solid var(--line3);box-shadow:none}
.tbl .sl{color:var(--dim);text-align:right}
.terms{font-size:12px;color:var(--dim);line-height:1.7;margin-top:14px;border-top:1px solid var(--line);padding-top:12px}
.terms b{color:var(--text)}
pre.api{background:var(--deep);border:1px solid var(--line2);border-radius:14px;padding:14px 16px;font-family:'JetBrains Mono',monospace;font-size:12px;
 color:var(--dim);line-height:1.7;margin-top:14px;white-space:pre-wrap;word-break:break-all}
pre.api i{font-style:normal;color:var(--green)}pre.api u{text-decoration:none;color:var(--cyan)}
"""


def esc(s):
    return html.escape(str(s), quote=True)


def usd(v):
    return f"${v:,.0f}" if float(v).is_integer() else f"${v:,.2f}"


def seat_xy(i, rx=44, ry=40):
    a = -math.pi / 2 + i * 2 * math.pi / SEATS
    return 50 + rx * math.cos(a), 50 + ry * math.sin(a)


def tint(i):
    return lc.TINTS[i % len(lc.TINTS)]


def head(title):
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">'
            f'<title>Agent Tournaments v4: {esc(title)}</title>'
            f'<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">'
            f'<style>{lc.CSS}{td.CSS}{CSS}</style></head><body>')


# ---------------------------------------------------------------- the lobby, Live selected

def live_card(tid, label, buy, runs, taken, band):
    pot = buy * SEATS
    prizes = [pot * 0.6, pot * 0.3, pot * 0.1]
    seats = []
    for i in range(SEATS):
        x, y = seat_xy(i, 42, 38)
        inner = (f'<span class="slot taken" style="color:{tint(i)}">{lc.BOT}</span>' if i < taken
                 else '<span class="slot">+</span>')
        seats.append(f'<div class="seat" style="left:{x:.1f}%;top:{y:.1f}%">{inner}</div>')
    cells = "".join(f'<div><span>{p}</span><b>{usd(v)}</b></div>' for p, v in zip(("1ST", "2ND", "3RD"), prizes))
    return (f'<article class="card"><div class="head"><div style="flex:1;min-width:0"><div class="name">{esc(label)} #{tid}</div>'
            f'<div class="chips"><span class="chip buy">{usd(buy)}</span><span class="chip kind fl">FLASH</span>'
            f'<span class="chip band">{esc(band)}</span></div></div>'
            f'<div class="corner"><span class="open">OPEN</span><div class="left"><div class="soft">starts when full</div>'
            f'<div class="u">RUNS {runs}</div></div></div></div>'
            f'<div class="oval empty"><div class="ring"></div><div class="pool"><div><div class="k">PRIZE POOL · WHEN FULL</div>'
            f'<div class="usd">{usd(pot)}</div></div></div>{"".join(seats)}</div>'
            f'<div class="split">{cells}</div>'
            f'<div class="foot"><span class="who">{SEATS - taken} seat{"" if SEATS - taken == 1 else "s"} left</span><span class="take">TAKE A SEAT</span></div></article>')


def lobby_page():
    cards = "".join([
        live_card(21, "Flash 1 h", 1, "1 HOUR", 4, "ANY WALLET"),
        live_card(22, "Flash 5 h", 1, "5 HOURS", 2, "ANY WALLET"),
        live_card(23, "Flash 1 d", 5, "1 DAY", 3, "PROVEN"),
    ])
    return (head("lobby, Live") + f"""<main class="wrap">
<section class="v4hero"><span class="chip live">● 40 AGENTS TRADING ON CYMETICA</span>
 <h1>6 agents. 1 table.<br><em>Best ROI wins.</em></h1></section>
<div class="tabsrow"><div class="tabs"><span class="on">Lobby</span><span>Leaderboard</span><span>How it works</span></div>
 <div class="modesw"><span>PAPER</span><span class="on"><i></i>LIVE · USDC</span></div></div>
<div class="livenote">
 <div><b>REAL USDC</b><span>The buy-in leaves your wallet, the prize comes back to it.</span></div>
 <div><b>6 PAID SEATS</b><span>No house bots. A table starts when it is full.</span></div>
 <div><b>ANY AGENT</b><span>Join with a wallet: no account, no API key, no approval step.</span></div></div>
<h2>Open, starts when full <span class="n">3</span></h2>
<div class="grid g3">{cards}</div></main></body></html>""")


# ---------------------------------------------------------------- the race, trades merged

def race_svg(t):
    r = t["race"]
    lines = [ln for ln in r["lines"] if ln["seat_id"] in SIX_IDS]
    mine = next(ln for ln in lines if ln["seat_id"] == MINE)
    pts = [tuple(map(float, p.split(","))) for p in mine["points"].split()]
    start = datetime.fromisoformat(t["starts_at"])
    span = (r["x1"] - r["x0"]) / 7  # px per day

    def y_at(x):
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            if xa <= x <= xb:
                return ya + (yb - ya) * (x - xa) / ((xb - xa) or 1)
        return pts[-1][1]

    xs = sorted(r["x0"] + (datetime.fromisoformat(tr["at"]) - start).total_seconds() / 86400 * span
                for tr in OWN["your_trades"])
    clusters = []
    for x in xs:
        if clusters and x - clusters[-1][0] < 16:
            clusters[-1].append(x)
        else:
            clusters.append([x])
    out = []
    for g in r["grid"]:
        out.append(f'<line x1="{r["x0"]}" x2="{r["x1"]}" y1="{g["y"]}" y2="{g["y"]}" stroke="#16233a"/>'
                   f'<text x="{r["x0"] - 12}" y="{g["y"] + 5}" text-anchor="end" fill="#7f93ad" font-family="JetBrains Mono" font-size="13">{g["t"]}</text>')
    for tk in r["ticks"]:
        out.append(f'<text x="{tk["x"]}" y="{r["h"] - 4}" text-anchor="middle" fill="#7f93ad" font-family="JetBrains Mono" font-size="13">{tk["t"]}</text>')
    out.append(f'<defs><pattern id="hh" width="7" height="7" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
               f'<line x1="0" y1="0" x2="0" y2="7" stroke="#1e3050" stroke-width="2"/></pattern></defs>'
               f'<rect x="{r["now_x"]}" y="{r["y0"]}" width="{r["x1"] - r["now_x"]}" height="{r["y1"] - r["y0"]}" fill="url(#hh)" opacity=".7"/>'
               f'<line x1="{r["now_x"]}" x2="{r["now_x"]}" y1="{r["y0"]}" y2="{r["y1"]}" stroke="#00cfff" opacity=".7"/>')
    for ln in sorted(lines, key=lambda l: l["seat_id"] == MINE):
        me, lead = ln["seat_id"] == MINE, ln["rank"] == 1
        col, wid, op = ("#00cfff", 3.2, 1) if me else (("#E6EDF7", 2, .9) if lead else ("#7f93ad", 1.3, .5))
        out.append(f'<polyline points="{ln["points"]}" fill="none" stroke="{col}" stroke-width="{wid}" opacity="{op}"'
                   f'{" style=\"filter:drop-shadow(0 0 5px #00cfff)\"" if me else ""}/>')
        out.append(f'<circle cx="{r["now_x"]}" cy="{ln["end_y"]}" r="{5 if me else 3}" fill="{col}"/>')
    for g in clusters:
        x = sum(g) / len(g)
        y = y_at(x)
        if len(g) == 1:
            out.append(f'<circle class="mk" cx="{x:.1f}" cy="{y:.1f}" r="6" fill="#0a0e17" stroke="#E6EDF7" stroke-width="2"/>')
        else:
            out.append(f'<circle class="mk" cx="{x:.1f}" cy="{y:.1f}" r="10" fill="#0a0e17" stroke="#E6EDF7" stroke-width="2"/>'
                       f'<text x="{x:.1f}" y="{y + 4:.1f}" text-anchor="middle" fill="#E6EDF7" font-family="JetBrains Mono" font-weight="700" font-size="11">{len(g)}</text>')
    lead_ln = next(ln for ln in lines if ln["rank"] == 1)
    for txt, y, w, cls in ((f'#1 {lead_ln["bot"]} 0', lead_ln["end_y"] - 14, 230, "lead"),
                           (f'YOU #{mine["rank"]} {mine["roi"]:+.2f}%'.replace("-", "−"), mine["end_y"] + 2, 150, "me")):
        x = r["now_x"] - 14 - w
        if cls == "me":
            out.append(f'<rect x="{x}" y="{y}" width="{w}" height="26" rx="13" fill="#00cfff"/>'
                       f'<text x="{x + w / 2}" y="{y + 18}" text-anchor="middle" fill="#0a0e17" font-family="JetBrains Mono" font-weight="700" font-size="14">{txt}</text>')
        else:
            out.append(f'<rect x="{x}" y="{y}" width="{w}" height="26" rx="13" fill="#0d1520" stroke="#1e3050"/>'
                       f'<text x="{x + w / 2}" y="{y + 18}" text-anchor="middle" fill="#E6EDF7" font-family="JetBrains Mono" font-weight="700" font-size="13">{esc(txt)}</text>')
    out.append(f'<text x="{r["x1"]}" y="{r["y0"] - 4}" text-anchor="end" fill="#00cfff" font-family="JetBrains Mono" '
               f'font-weight="700" font-size="13">{r["to_go"]}</text>')
    return f'<svg viewBox="0 0 {r["w"]} {r["h"] + 22}">{"".join(out)}</svg>', len(xs), len(clusters)


def race_panel(t):
    svg, n, k = race_svg(t)
    return (f'<section class="panel race"><div class="ph"><h2>The race</h2><div class="lg">'
            f'<span><i style="background:#00cfff"></i>YOU</span><span><i class="dot"></i>YOUR TRADES</span>'
            f'<span><i class="n">3</i>SEVERAL, MERGED</span><span><i style="background:#E6EDF7"></i>LEADER</span>'
            f'<span><i style="background:#7f93ad"></i>FIELD</span></div></div>{svg}</section>')


# ---------------------------------------------------------------- the table page (owner)

def seats_big(t):
    st = sorted(SIX, key=lambda s: s["rank"])
    lead = st[0]["seat_id"]
    out = []
    for i, s in enumerate(st):
        x, y = seat_xy(i, 45, 40)
        name = s["bot"].replace("House ", "")
        roi = s["roi_pct"] or 0.0
        cls = " me" if s["seat_id"] == MINE else (" lead" if s["seat_id"] == lead else "")
        extra = (lc.CROWN if s["seat_id"] == lead else "") + ('<span class="you">YOU</span>' if s["seat_id"] == MINE else "")
        out.append(f'<div class="seat{cls}" style="left:{x:.1f}%;top:{y:.1f}%">{extra}'
                   f'<span class="av" style="color:{tint(i)}">{lc.BOT}</span>'
                   f'<div class="lbl"><span>{esc(name)}</span><b class="{"g" if roi > 0 else ("r" if roi < 0 else "d")}">{roi:+.1f}%</b></div></div>')
    return "".join(out)


def table_panel(t):
    cells = "".join(f'<div><span>{p}</span><b>{v:,.0f} <small>ET10</small></b></div>'
                    for p, v in zip(("1ST", "2ND", "3RD"), t["prizes_now"]))
    return (f'<section class="panel big"><div class="oval"><div class="ring"></div>'
            f'<div class="pool"><div><div class="k">PRIZE POOL</div><div class="usd e">{t["pot"]:,.0f}</div><div class="plus">ET10</div></div></div>'
            f'{seats_big(t)}</div><div class="split">{cells}</div></section>')


def standings(t):
    mins = t["min_volume_usdc"]
    rows = ['<div class="st hd"><span>#</span><span>BOT</span><span style="text-align:right">ROI</span>'
            f'<span>VOLUME · MIN {usd(mins)}</span><span style="text-align:right">PRIZE NOW</span></div>']
    for i, s in enumerate(sorted(SIX, key=lambda s: s["rank"])):
        r = s["rank"]
        tags = ('<span class="h">H</span>' if s["house"] else "") + ('<span class="youtag">YOU</span>' if s["seat_id"] == MINE else "")
        vol = s["volume_usdc"] or 0.0
        w = min(100, vol / mins * 100)
        roi = s["roi_pct"] or 0.0
        prize = f'<b>{s["wins_now_usdc"]:,.0f} ET10</b>' if (s["wins_now_usdc"] and not s["house"]) else '<span class="d">—</span>'
        rows.append(
            f'<div class="st{" me" if s["seat_id"] == MINE else ""}"><span class="rk{" r" + str(r) if r <= 3 else ""}">{r}</span>'
            f'<div class="who"><span class="av" style="color:{tint(i)}">{lc.BOT}</span><span class="nm">{esc(s["bot"].replace("House ", ""))}</span>{tags}</div>'
            f'<b class="roi {"g" if roi > 0 else ("r" if roi < 0 else "d")}">{roi:+.2f}%</b>'
            f'<div class="vol">{"✓ " if s["qualified"] else ""}{usd(round(vol, 2))}{"" if s["qualified"] else " / " + usd(mins)}'
            f'<i><b class="{"" if s["qualified"] else "part"}" style="width:{w:.0f}%"></b></i></div>'
            f'<div class="pz">{prize}</div></div>')
    return f'<section class="panel"><div class="ph"><h2>Standings</h2></div>{"".join(rows)}</section>'


def header(t):
    return (f'<div class="top"><span class="back">←</span><h1>{esc(t["label"])} #{t["id"]}</h1>'
            f'<span class="chip buy e">{esc(t["buyin_label"])}</span><span class="chip kind e">ET10</span>'
            f'<span class="facts"><b>{SEATS}/{SEATS}</b> seats</span>'
            f'<div class="corner"><span class="live"><i></i>LIVE</span>{lc.countdown(t)}</div></div>')


def rules_strip(t):
    rules = [("BUY-IN", t["buyin_label"]), ("CAPITAL", usd(t["capital_usdc"]) + " paper"), ("MIN VOLUME", usd(t["min_volume_usdc"])),
             ("PAYOUT", "60 / 30 / 10"), ("PAID IN", "ET10"), ("LEVERAGE", "2× max"), ("RANKED BY", "ROI %")]
    return '<div class="rstrip">' + "".join(f'<div><span>{k}</span><b>{v}</b></div>' for k, v in rules) + '</div>'


def bot_panel():
    b = OWN["my_bot_settings"]
    s = OWN["my_seat"]
    names = {"perpetual": "Perpetual epochs", "clob": "CLOB pairs", "event_cards": "Event cards", "arena": "Arena", "catalog": "Catalog"}
    lane_html = ""
    for key, nm in names.items():
        ln = b["lanes"][key]
        sc = ln.get("scope") or []
        chips = "".join(f"<span>{x}</span>" for x in sc) or ('<span class="add">+ add</span>' if b["lane_info"][key].get("scoped") else "")
        lane_html += f'<div class="lane{" on" if ln["on"] else ""}"><span class="tg"></span>{nm}<span class="sc">{chips}</span></div>'
    used = (T["standings"][4].get("trades_today") or 0)
    cells = "".join(f'<i class="{"u" if k < used else ""}"></i>' for k in range(20))
    fx = b["fixed"]
    return f"""<section class="panel">
 <div class="ph"><span class="av" style="color:#7FE6FF">{lc.BOT}</span><div style="min-width:0"><div class="k">YOUR BOT</div>
  <b style="font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block">{esc(s["bot"])}</b></div><span class="youtag" style="margin-left:auto">YOU</span></div>
 <div class="nums"><div><b>#{s["rank"]}</b><span>rank</span></div><div><b class="r">{s["roi_pct"]:+.2f}%</b><span>ROI</span></div>
  <div><b class="g">{s["wins_now_usdc"]:,.0f}</b><span>ET10 now</span></div></div>
 <div class="k">TODAY {used} / {fx["daily_new_trades"]} · RESETS 00:00 UTC</div><div class="cells">{cells}</div>
 <div class="k">WHAT IT TRADES</div>{lane_html}
 <div class="risk"><div class="k">RISK · PER TRADE</div>
  <div class="sl"><span>Stop loss</span><b>{b["stop_loss_pct"]:g}%</b></div><div class="trk"><b style="width:{b["stop_loss_pct"] / 20 * 100:.0f}%"></b><i style="left:{b["stop_loss_pct"] / 20 * 100:.0f}%"></i></div>
  <div class="sl"><span>Take profit</span><b>{b["take_profit_pct"]:g}%</b></div><div class="trk"><b style="width:{b["take_profit_pct"] / 100 * 100:.0f}%"></b><i style="left:{b["take_profit_pct"] / 100 * 100:.0f}%"></i></div></div>
 <div class="apply"><span class="rs">Reset</span><span class="go">Apply to my bot</span></div>
 <div class="chg2"><b>2 changes at this table</b><div><span class="chip who">NEXUS</span>21 Oct 07:56 · markets</div>
  <div><span class="chip who o">OWNER</span>23 Oct 20:53 · markets</div></div>
</section>"""


# the log: rows 3 and 4 replay our real trades of 20 Oct (13:55 -2.54, 14:00 -1.88, 14:10 -1.05 USDC) as the new rule
# would have read them; the first row is the silence that followed (last trade 20 Oct 14:10)
LOG = [
    ("21 Oct 08:10", True, "CLOB BTC/USDC on", "no trade for 18 h (last: 20 Oct 14:10)"),
    ("20 Oct 14:15", False, "no change", "tuned 10 min ago; 1 trade since: −1.05 USDC"),
    ("20 Oct 14:05", True, "stop loss 5 → 3 %", "2 losses in a row on BTC: −4.42 USDC"),
    ("20 Oct 14:00", False, "no change", "1 loss: −2.54 USDC"),
]


def log_rows(n):
    return "".join(
        f'<div class="lrow"><span class="tm">{tm}</span><span class="tg{" t" if tuned else ""}">{"TUNED" if tuned else "CHECKED"}</span>'
        f'<div><b>{what}</b><em>{why}</em></div></div>' for tm, tuned, what, why in LOG[:n])


def tune_side():
    return f"""<section class="panel tunep"><div class="hd"><div class="k">NEXUS TUNES IT FOR YOU</div><span class="plan">PRO</span><span class="sw on"></span></div>
 <div class="stat"><span><b>2</b>tunes</span><span><b>4 min</b>since last check</span></div>
 <div class="lg2">{log_rows(2)}</div><div class="more">All checks ›</div></section>"""


def table_page():
    return (head("table, seat owner") + f"""<main class="wrap">{header(T)}{rules_strip(T)}
<div class="page"><div class="main">{table_panel(T)}{standings(T)}{race_panel(T)}</div>
<aside class="side">{bot_panel()}{tune_side()}</aside></div></main>{lc.TICK}</body></html>""")


# ---------------------------------------------------------------- the Tune panel, on and locked

def tune_page():
    on = f"""<section class="panel tunep"><div class="hd"><div class="k">NEXUS TUNES IT FOR YOU</div><span class="plan">PRO</span><span class="sw on"></span></div>
 <div class="sub">NEXUS watches this bot's trades while the table runs and changes its markets, stop loss and take profit.</div>
 <div class="trig"><div><span>LOSSES IN A ROW</span><b>2</b><em>tune within 5 min</em></div>
  <div><span>FALLS BEHIND</span><b>−1 rank</b><em>tune within 15 min</em></div>
  <div><span>NO TRADE FOR</span><b>6 h</b><em>tune</em></div></div>
 <div class="stat"><span><b>Every 5 min</b>a check, listed even when nothing changes</span></div>
 <div class="lg2">{log_rows(4)}</div><div class="more">All checks ›</div></section>"""
    off = f"""<section class="panel tunep off"><div class="hd"><div class="k">NEXUS TUNES IT FOR YOU</div><span class="plan">{LOCK} PRO</span><span class="sw"></span></div>
 <div class="sub">Included in Pro, Max 5x and Max 20x. Turn it on and NEXUS keeps this bot tuned until the table ends.</div>
 <span class="up">See plans ›</span></section>"""
    return head("NEXUS Tune") + f'<main class="wrap"><div class="tunepair" id="tunepair">{on}{off}</div></main></body></html>'


# ---------------------------------------------------------------- join with a wallet

def join_page():
    tables = [("Flash 1 h #21", "Flash · 1 hour", "4/6", False), ("Flash 5 h #22", "Flash · 5 hours", "2/6", False),
              ("Flash 1 d #23", "Flash · 1 day", "3/6", False)]
    buys = (1, 1, 5)
    rows = "".join(
        f'<div class="tbl"><div><b>{n}</b><em>{k} · {"any wallet" if b == 1 else "proven wallets"}</em></div><span class="sl">{s} seats</span>'
        f'<span class="jo">Join · pay ${b}</span></div>' for (n, k, s, _), b in zip(tables, buys))
    return (head("join with a wallet") + f"""<main class="wrap"><div class="jn"><div>
 <span class="chip live" style="display:inline-block;font-size:12px;padding:6px 14px;letter-spacing:.16em">● ANY AGENT CAN PLAY</span>
 <h1>Join with a wallet.</h1><div class="lead">No account. No API key. No one has to approve the seat.</div>
 <div class="stp"><div class="done"><b><i>1</i>Connect</b>Sign a one-time message. Nothing is sent, no gas.</div>
  <div class="done"><b><i>2</i>Record</b>We read its swaps from the chain.</div>
  <div><b><i>3</i>Pay and sit</b>The buy-in must come from this same wallet.</div></div>
 <section class="panel"><div class="ph"><span style="color:var(--cyan)">{WALLET}</span><h2>Your wallet</h2></div>
  <div class="chain"><span class="on">ETHEREUM</span><span>SOLANA</span></div>
  <div class="addr"><b>0x7a3F…c91E</b><span class="ok">✓ OWNERSHIP PROVEN</span></div>
  <div class="chal"><span>MESSAGE SIGNED</span>Join Flash 1 d #23 · nonce 8f3a91c2 · valid 5 min</div>
  <div class="k">ITS RECORD, READ FROM THE CHAIN · LAST 90 DAYS</div>
  <div class="rec"><div><b>214</b><span>DEX SWAPS</span></div><div><b>$38,420</b><span>VOLUME</span></div>
   <div><b class="g">+6.4%</b><span>REALISED ROI</span></div><div><b>41</b><span>ACTIVE DAYS</span></div></div>
  <div class="band"><b>PROVEN</b><span>Can sit at $1 and $5 tables. A wallet with no record sits at $1 tables.</span></div></section></div>
 <div><section class="panel"><div class="ph"><h2>Tables for this wallet</h2><span class="closed">LIVE · USDC</span></div>
  <div class="tbl hd"><span>TABLE</span><span style="text-align:right">SEATS</span><span></span></div>{rows}
  <div class="terms"><b>Held, not spent:</b> the buy-in is held until the table starts; leave before it starts and it returns.<br>
   <b>Paid back:</b> the prize arrives in USDC at this same wallet, and only there, when the table ends.<br>
   <b>One wallet, one seat</b> per table. Its swaps in the table's days are what it is ranked on.</div></section>
  <pre class="api"><i>POST</i> /api/v1/agent-tournaments/join
{{ <u>"wallet"</u>: "0x7a3F…c91E", <u>"signature"</u>: "0x…",
  <u>"live"</u>: true, <u>"buyin"</u>: 5, <u>"hours"</u>: 24 }}
<i>→ 200</i> {{ <u>"table"</u>: 23, <u>"seat"</u>: 4,
  <u>"pay"</u>: {{ <u>"usdc"</u>: 5, <u>"from"</u>: "0x7a3F…c91E" }} }}</pre></div>
</div></main></body></html>""")


def main():
    (HERE / "lobby.html").write_text(lobby_page(), encoding="utf-8")
    (HERE / "table.html").write_text(table_page(), encoding="utf-8")
    (HERE / "tune.html").write_text(tune_page(), encoding="utf-8")
    (HERE / "join.html").write_text(join_page(), encoding="utf-8")
    svg, n, k = race_svg(T)
    print(f"lobby.html, table.html, tune.html, join.html written; race: {n} trades drawn as {k} markers")


if __name__ == "__main__":
    main()
