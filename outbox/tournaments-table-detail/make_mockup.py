"""Build visitor.html and player.html (this folder): the Agent Tournaments table page, laid out again.

The operator, 2026-10-16, on the live table page: "jak odporne to vypada jak jen nahlidnem do stolu kde nehrajem a
kdyz hrajem tak mi ten stul pripada moc maly a ten konfiguracni panel hrozne velky a ta lista napravo zbytecna.
mel by tam byt hlavni stul, pod nim poradi a na strane nekde konfigurace. a vse krasne prehledne."

So the page keeps what it has and changes where it goes: the table big at the top of the main column, the
standings under it (each row carries its prize now, so "If it ended now" goes), the race under that; one side
column -- for a seated owner the bot's panel (its numbers, today's 20 trades, the lanes, stop loss and take
profit, Apply), for a visitor Pick the winner and the rules. The right-hand "Your bot, live" column goes; its
numbers move into the side panel. Nothing new is added.

Real figures: tables 5 and 11 as GET /api/v1/agent-tournaments/tables/{id} served them on 2026-10-16
(../tournaments-leaderboard/tables.json): seats, standings, prizes, race lines, picks, rules. Table 5's seat 29
is ours ("tournament Perceptron Oracle"); its lanes and limits are the ones the operator's screenshot of the live
panel shows. Palette: the site's navy, cyan, green, red and blue, plus the avatar tints they use.
"""
from __future__ import annotations

import html
import importlib.util
import json
import math
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("lobby_card", HERE.parent / "tournaments-lobby-card" / "make_mockup.py")
lc = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lc)
DATA = json.loads((HERE.parent / "tournaments-leaderboard" / "tables.json").read_text(encoding="utf-8"))
TABLES = {t["id"]: t for t in DATA["tables"]}
MINE_SEAT = 29


def esc(s):
    return html.escape(str(s), quote=True)


CSS = """
.wrap{max-width:1240px}
.top{display:flex;align-items:center;gap:14px;padding:22px 0 18px;border-bottom:1px solid var(--line);margin-bottom:22px}
.back{width:38px;height:38px;border-radius:10px;border:1px solid var(--line3);display:grid;place-items:center;color:var(--cyan);font-size:18px}
.top h1{font-family:'Archivo Black';font-weight:400;font-size:34px}
.top .facts{font-size:12.5px;color:var(--dim);margin-left:18px}.top .facts b{color:var(--text)}
.top .corner{margin-left:auto;flex-direction:row;align-items:center;gap:16px}
.top .left .t{font-size:28px}
.page{display:grid;grid-template-columns:minmax(0,1fr) 360px;gap:24px;align-items:start}
.main{display:flex;flex-direction:column;gap:22px;min-width:0}
.panel{background:var(--navy);border:1px solid var(--line2);border-radius:20px;padding:18px 20px;min-width:0}
.ph{display:flex;align-items:center;gap:10px;margin-bottom:12px}
.ph h2{font-family:'Archivo Black';font-weight:400;font-size:20px;margin:0}
.ph .seg{margin-left:auto;display:flex;gap:4px;background:var(--deep);border:1px solid var(--line2);border-radius:10px;padding:3px}
.ph .seg span{padding:5px 11px;border-radius:8px;color:var(--dim2);font-weight:600;font-size:12px}
.ph .seg span.on{background:var(--navy2);color:var(--text)}
.big .oval{height:430px;margin:8px 40px 60px}
.big .oval .ring{inset:12% 10%}
.big .pool .usd{font-size:56px}
.big .pool .plus{font-size:18px}
.big .seat .lbl{position:absolute;top:46px;display:flex;flex-direction:column;align-items:center;white-space:nowrap;background:var(--navy);border:1px solid var(--line2);border-radius:8px;padding:2px 8px;z-index:2}
.big .seat .lbl span{font-size:11.5px;color:var(--dim);max-width:120px;overflow:hidden;text-overflow:ellipsis}
.big .seat .lbl b{font-size:13px}
.big .av{width:42px;height:42px}.big .av svg{width:22px;height:22px}
.big .seat .you{bottom:auto;top:-18px}
.big .split{margin:0}
.big .split b{font-size:18px}
.st{display:grid;grid-template-columns:34px minmax(0,1fr) 110px 190px 150px;align-items:center;gap:12px;padding:9px 12px;
 border-radius:12px;background:var(--deep);margin-top:6px}
.st.hd{background:none;padding:0 12px;font-size:10.5px;letter-spacing:.12em;color:var(--dim2);font-weight:700;margin-top:0}
.st.me{background:rgba(0,207,255,.07);box-shadow:0 0 0 1px rgba(0,207,255,.4) inset}
.st .rk{width:26px;height:26px;border-radius:50%;display:grid;place-items:center;font-weight:700;font-size:12px;color:var(--dim)}
.st .rk.r1{background:var(--green);color:var(--bg)}.st .rk.r2{background:var(--cyan);color:var(--bg)}.st .rk.r3{background:var(--blue);color:var(--bg)}
.st .who{display:flex;align-items:center;gap:10px;min-width:0}
.st .who .nm{overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-weight:600}
.st .roi{text-align:right;font-size:16px}
.st .vol{font-size:12px;color:var(--dim)}
.st .vol i{display:block;height:4px;border-radius:99px;background:var(--line3);margin-top:4px;overflow:hidden}
.st .vol i b{display:block;height:100%;background:var(--green)}
.st .vol i b.part{background:var(--cyan)}
.st .pz{text-align:right;font-size:12.5px;color:var(--dim2)}
.st .pz b{color:var(--green);font-size:14px}.st .pz em{display:block;font-style:normal;color:var(--cyan);font-size:11px}
.h{font-size:9.5px;font-weight:700;color:var(--dim2);border:1px solid var(--line3);border-radius:4px;padding:1px 5px}
.youtag{font-size:9.5px;font-weight:700;color:var(--bg);background:var(--cyan);border-radius:4px;padding:1px 5px}
.race svg{width:100%;height:auto;display:block}
.side{display:flex;flex-direction:column;gap:16px;position:sticky;top:16px}
.k{font-size:10.5px;letter-spacing:.14em;color:var(--dim2);font-weight:700}
.nums{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;margin:12px 0}
.nums div{background:var(--deep);border-radius:10px;padding:8px 10px}
.nums b{display:block;font-size:17px}.nums span{font-size:10.5px;color:var(--dim2)}
.warn{font-size:12px;color:var(--red);margin-bottom:8px}
.cells{display:flex;gap:3px;margin:6px 0 14px}.cells i{flex:1;height:8px;border-radius:2px;background:var(--line3)}
.cells i.u{background:var(--cyan)}
.lane{display:flex;align-items:center;gap:10px;padding:7px 0;border-top:1px solid var(--line);font-size:13px}
.lane .tg{width:30px;height:17px;border-radius:99px;background:var(--line3);position:relative;flex:none}
.lane .tg:after{content:'';position:absolute;top:2px;left:2px;width:13px;height:13px;border-radius:50%;background:var(--dim2)}
.lane.on .tg{background:var(--green)}.lane.on .tg:after{left:15px;background:var(--bg)}
.lane .sc{margin-left:auto;display:flex;gap:4px}
.lane .sc span{font-size:10.5px;font-weight:700;color:var(--green);border:1px solid rgba(0,255,136,.5);border-radius:5px;padding:1px 5px}
.lane .sc span.add{color:var(--dim2);border-color:var(--line3)}
.risk{margin-top:12px}
.sl{display:flex;justify-content:space-between;font-size:13px;margin-top:8px}.sl b{color:var(--text)}
.trk{height:5px;border-radius:99px;background:var(--line3);margin-top:6px;position:relative}
.trk b{position:absolute;left:0;top:0;bottom:0;border-radius:99px;background:var(--cyan)}
.trk i{position:absolute;top:50%;width:14px;height:14px;border-radius:50%;background:var(--text);transform:translate(-50%,-50%)}
.fixed{font-size:11px;color:var(--dim2);margin-top:12px;line-height:1.6}
.apply{display:flex;gap:8px;margin-top:14px}
.apply span{flex:1;text-align:center;border-radius:10px;padding:10px;font-weight:700}
.apply .rs{flex:0 0 auto;border:1px solid var(--line3);color:var(--dim)}
.apply .go{background:var(--green);color:var(--bg);opacity:.45}
.chg{font-size:11.5px;color:var(--dim2);margin-top:12px;border-top:1px solid var(--line);padding-top:10px}
.chg b{color:var(--text)}
.pick{display:flex;align-items:center;gap:10px;padding:8px 0;border-top:1px solid var(--line);font-size:13px}
.pick .p{margin-left:auto;color:var(--dim2);font-size:12px}
.rules{display:grid;grid-template-columns:1fr 1fr;gap:8px 14px;margin-top:10px}
.rules div span{display:block;font-size:10px;letter-spacing:.12em;color:var(--dim2);font-weight:700}
.rules div b{font-size:14px}
.tr{display:grid;grid-template-columns:44px 64px minmax(0,1fr) auto;gap:8px;align-items:center;padding:8px 0;border-top:1px solid var(--line);font-size:13px}
.tr .tm{color:var(--dim2);font-size:12px}
.tr .px{color:var(--dim2);font-size:11px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.all{margin-top:10px;font-size:12px;font-weight:700;color:var(--cyan);text-align:center}
.closed{font-size:11px;font-weight:700;letter-spacing:.1em;color:var(--dim2);border:1px solid var(--line3);border-radius:99px;padding:3px 9px;margin-left:auto}
"""


def money(v):
    return f"${v:,.0f}" if float(v).is_integer() else f"${v:,.2f}"


def seats_big(t, mine_seat=None):
    out = []
    st = {s["seat_id"]: s for s in t["standings"]}
    order = [s["seat_id"] for s in t["seats"]]
    lead = min(t["standings"], key=lambda s: s["rank"])["seat_id"]
    for i, sid in enumerate(order[:10]):
        s = st[sid]
        a = -math.pi / 2 + i * 2 * math.pi / 10
        x, y = 50 + 45 * math.cos(a), 50 + 40 * math.sin(a)
        name = s["bot"].replace("House ", "")
        roi = s["roi_pct"] or 0.0
        cls = " me" if sid == mine_seat else (" lead" if sid == lead else "")
        extra = (lc.CROWN if sid == lead else "") + ('<span class="you">YOU</span>' if sid == mine_seat else "")
        out.append(f'<div class="seat{cls}" style="left:{x:.1f}%;top:{y:.1f}%">{extra}'
                   f'<span class="av" style="color:{lc.TINTS[i % len(lc.TINTS)]}">{lc.BOT}</span>'
                   f'<div class="lbl"><span>{esc(name)}</span><b class="{"g" if roi > 0 else ("r" if roi < 0 else "d")}">{roi:+.1f}%</b></div></div>')
    return "".join(out)


def table_panel(t, mine_seat=None):
    return (f'<section class="panel big"><div class="oval"><div class="ring"></div>{lc.pool(t, True)}{seats_big(t, mine_seat)}</div>'
            f'{lc.split_strip(t, True)}</section>')


def standings(t, mine_seat=None):
    rows = ['<div class="st hd"><span>#</span><span>BOT</span><span style="text-align:right">ROI</span><span>VOLUME · MIN '
            f'{money(t["min_volume_usdc"])}</span><span style="text-align:right">PRIZE NOW</span></div>']
    mins = t["min_volume_usdc"]
    for i, s in enumerate(sorted(t["standings"], key=lambda s: s["rank"])):
        r = s["rank"]
        name = s["bot"].replace("House ", "")
        tags = ('<span class="h">H</span>' if s["house"] else "") + ('<span class="youtag">YOU</span>' if s["seat_id"] == mine_seat else "")
        vol = s["volume_usdc"] or 0.0
        w = min(100, vol / mins * 100)
        prize = ("no prize · house" if s["house"] else
                 (f'<b>{money(s["wins_now_usdc"])}</b>' + (f'<em>+ {s["et10_now"]} ET10</em>' if s.get("et10_now") else "")
                  if s["wins_now_usdc"] else "—"))
        roi = s["roi_pct"] or 0.0
        rows.append(
            f'<div class="st{" me" if s["seat_id"] == mine_seat else ""}"><span class="rk{" r" + str(r) if r <= 3 else ""}">{r}</span>'
            f'<div class="who"><span class="av" style="color:{lc.TINTS[i % len(lc.TINTS)]}">{lc.BOT}</span><span class="nm">{esc(name)}</span>{tags}</div>'
            f'<b class="roi {"g" if roi > 0 else ("r" if roi < 0 else "d")}">{roi:+.2f}%</b>'
            f'<div class="vol">{"✓ " if s["qualified"] else ""}{money(round(vol, 2))}{"" if s["qualified"] else " / " + money(mins)}'
            f'<i><b class="{"" if s["qualified"] else "part"}" style="width:{w:.0f}%"></b></i></div>'
            f'<div class="pz">{prize}</div></div>')
    return (f'<section class="panel"><div class="ph"><h2>Standings</h2><div class="seg"><span class="on">All</span>'
            f'<span>Qualified</span></div></div>{"".join(rows)}</section>')


def race(t, mine_seat=None):
    r = t["race"]
    lines = []
    for ln in r["lines"]:
        me = ln.get("seat_id") == mine_seat
        lead = ln.get("rank") == 1
        col, wid, op = ("#00cfff", 3, 1) if me else (("#E6EDF7", 2, .9) if lead else ("#7f93ad", 1.2, .45))
        lines.append(f'<polyline points="{ln["points"]}" fill="none" stroke="{col}" stroke-width="{wid}" opacity="{op}"/>')
    zero = r["y0"] + (r["y1"] - r["y0"]) * 0.5
    end = max(float(p.split(",")[0]) for ln in r["lines"] for p in ln["points"].split())
    mid = (end + r["x1"]) / 2
    from datetime import datetime
    s = max(0, int((datetime.fromisoformat(t["ends_at"]) - lc.NOW).total_seconds()))
    togo = f'{s // 86400}D {s % 86400 // 3600:02d}H TO GO' if s >= 86400 else f'{s // 3600:02d}H {s % 3600 // 60:02d}M TO GO'
    return (f'<section class="panel race"><div class="ph"><h2>The race</h2></div>'
            f'<svg viewBox="0 0 {r["w"]} {r["h"]}"><line x1="{r["x0"]}" x2="{r["x1"]}" y1="{zero}" y2="{zero}" stroke="#1e3050" stroke-dasharray="4 4"/>'
            f'<line x1="{end:.1f}" x2="{end:.1f}" y1="{r["y0"]}" y2="{r["y1"]}" stroke="#1e3050"/>'
            f'<text x="{mid:.1f}" y="{zero - 8:.1f}" text-anchor="middle" fill="#00cfff" font-family="JetBrains Mono" font-weight="700" font-size="26">{togo}</text>'
            f'{"".join(lines)}</svg></section>')


def header(t):
    return (f'<div class="top"><span class="back">←</span><h1>{esc(t["label"])} #{t["id"]}</h1>'
            f'<span class="chip buy">{money(t["buyin"])}</span><span class="chip kind">{"FLASH" if t["flash"] else "WEEK"}</span>'
            f'<span class="facts"><b>{t["seats_taken"]}/10</b> seats</span>'
            f'<div class="corner"><span class="live"><i></i>LIVE</span>{lc.countdown(t)}</div></div>')


def bot_panel(t):
    s = next(x for x in t["standings"] if x["seat_id"] == MINE_SEAT)
    lanes = [("Perpetual epochs", True, ["BTC", "ETH"]), ("CLOB pairs", False, ["+ pair"]),
             ("Event cards", True, []), ("Arena", False, []), ("Catalog", False, ["+ symbol"])]
    lane_html = "".join(
        f'<div class="lane{" on" if on else ""}"><span class="tg"></span>{n}<span class="sc">'
        + "".join(f'<span class="{"add" if x.startswith("+") else ""}">{x}</span>' for x in sc) + '</span></div>'
        for n, on, sc in lanes)
    used = s.get("trades_today") or 0
    cells = "".join(f'<i class="{"u" if k < used else ""}"></i>' for k in range(20))
    state = f'<div class="warn">{esc(s["bot_state_label"])}</div>' if s.get("bot_state") != "trading" else ""
    return f"""<section class="panel">
 <div class="ph"><span class="av" style="color:#7FE6FF">{lc.BOT}</span><div style="min-width:0"><div class="k">YOUR BOT</div>
  <b style="font-size:14px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;display:block">{esc(s["bot"])}</b></div><span class="youtag" style="margin-left:auto">YOU</span></div>
 {state}
 <div class="nums"><div><b>#{s["rank"]}</b><span>rank</span></div><div><b class="g">{s["roi_pct"]:+.2f}%</b><span>ROI</span></div>
  <div><b class="g">{money(s["wins_now_usdc"])}</b><span>prize now</span></div></div>
 <div class="k">TODAY {used} / 20 · RESETS 00:00 UTC</div><div class="cells">{cells}</div>
 <div class="k">WHAT IT TRADES</div>{lane_html}
 <div class="risk"><div class="k">RISK · PER TRADE</div>
  <div class="sl"><span>Stop loss</span><b>20%</b></div><div class="trk"><b style="width:100%"></b><i style="left:100%"></i></div>
  <div class="sl"><span>Take profit</span><b>100%</b></div><div class="trk"><b style="width:100%"></b><i style="left:100%"></i></div></div>
 <div class="fixed">Fixed for the tournament: max position 10% · 9 open · 2× leverage · 20 new trades a day</div>
 <div class="apply"><span class="rs">Reset</span><span class="go">Apply to my bot</span></div>
 <div class="chg"><b>1 change</b> at this table · 19:34 tournament Perceptron Oracle changed markets</div>
</section>
{recent_trades()}"""


def recent_trades():
    """The seat's last five trades, as the live page listed them on 2026-10-15 (the operator's screenshot)."""
    trades = [("04:35", "BTC", "↓", "81,469.5 → 81,503.1", -25), ("03:10", "ETH", "↑", "2,375.95 → 2,370.13", -25),
              ("03:10", "BTC", "↑", "81,330.9 → 81,271.9", -25), ("03:00", "ETH", "↑", "2,380.66 → 2,366.54", -25),
              ("02:45", "ETH", "↑", "2,377.58 → 2,369.81", -25)]
    rows = "".join(
        f'<div class="tr"><span class="tm">{tm}</span><b>{sym} <span class="{"g" if d == "↑" else "r"}">{d}</span></b>'
        f'<span class="px">{px}</span><b class="{"g" if pnl > 0 else "r"}">{"+" if pnl > 0 else "−"}${abs(pnl)}</b></div>'
        for tm, sym, d, px, pnl in trades)
    return (f'<section class="panel"><div class="ph"><h2>Recent trades</h2><span class="k" style="margin-left:auto">$25 EACH</span></div>'
            f'{rows}<div class="all">All 51 trades ›</div></section>')


def visitor_side(t):
    p = t["picks"]
    by = {x["seat_id"]: x for x in p.get("by_seat") or []}
    rows = "".join(
        f'<div class="pick"><span class="av" style="color:{lc.TINTS[i % len(lc.TINTS)]}">{lc.BOT}</span>'
        f'{esc(s["bot"].replace("House ", ""))}<span class="p">{(str(by[s["seat_id"]]["pickers"]) + " pick") if s["seat_id"] in by else "no picks"}</span></div>'
        for i, s in enumerate(sorted(t["standings"], key=lambda s: s["rank"])[:5]))
    rules = [("BUY-IN", money(t["buyin"])), ("CAPITAL", money(t["capital_usdc"])), ("MIN VOLUME", money(t["min_volume_usdc"])),
             ("PAYOUT", "60 / 30 / 10"), ("ET10", "600 / 300 / 100" if not t["flash"] else "85 / 42 / 14"),
             ("LEVERAGE", "2× max"), ("RANKED BY", "ROI %")]
    rh = "".join(f'<div><span>{k}</span><b>{v}</b></div>' for k, v in rules)
    return f"""<section class="panel"><div class="ph"><h2>Pick the winner</h2><span class="closed">CLOSED</span></div>
 <div class="k" style="margin-bottom:6px">{money(p["pool_usdc"])} POOL · {p["pickers"]} PICKER</div>{rows}</section>
<section class="panel"><div class="ph"><h2>Rules</h2></div><div class="rules">{rh}</div></section>"""


def page(t, side, mine_seat=None):
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Agent Tournaments: {esc(t["label"])} #{t["id"]}</title>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{lc.CSS}{CSS}</style></head><body><main class="wrap">{header(t)}
<div class="page"><div class="main">{table_panel(t, mine_seat)}{standings(t, mine_seat)}{race(t, mine_seat)}</div>
<aside class="side">{side}</aside></div></main>{lc.TICK}</body></html>"""


def main():
    (HERE / "player.html").write_text(page(TABLES[5], bot_panel(TABLES[5]), MINE_SEAT), encoding="utf-8")
    (HERE / "visitor.html").write_text(page(TABLES[11], visitor_side(TABLES[11])), encoding="utf-8")
    print("player.html, visitor.html written")


if __name__ == "__main__":
    main()
