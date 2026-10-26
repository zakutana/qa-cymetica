"""The seat owner's view of table 15, in THEIR markup (read 2026-10-26 from the operator's signed-in session: the
`<aside id="atSide">` column, the YOU tags on the seat and the standings row, the race with the owner's trades).

Their CSS for all of it is already in the page everyone gets, so this builds the same markup from our seat's real data
(fixtures/owner.json) and changes only what v4 changes: the NEXUS Tune card (a switch for a paid plan, a check on a
clock, every check a row), the changelog saying who changed what, and the race's trade circles merged where they touch.
"""
from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path

import lxml.html as L

import art

HERE = Path(__file__).resolve().parent
OWNER = json.loads((HERE / "fixtures" / "owner.json").read_text(encoding="utf-8"))
MINE = "lab Wave 2 Perceptron Oracle"


def frag(markup: str):
    wrap = L.fragment_fromstring(markup, create_parent="div")
    kids = list(wrap)
    for k in kids:
        wrap.remove(k)
    return kids


def pct(v: float) -> str:
    return f"{v:+.2f}%"


def usd(v: float) -> str:
    return f"{'−' if v < 0 else '+'}${abs(v):.2f}"


# ------------------------------------------------------------------------------------------------ the column

LOG = [  # the first row is the silence that followed our last trade; the rest replay our real trades of 20 Oct
    ("10-21 08:10", True, "CLOB BTC/USDC on", "no trade for 18 h (last: 20 Oct 14:10)"),
    ("10-20 14:15", False, "no change", "tuned 10 min ago; 1 trade since: −1.05 USDC"),
    ("10-20 14:05", True, "stop loss 5 → 3 %", "2 losses in a row on BTC: −4.42 USDC"),
    ("10-20 14:00", False, "no change", "1 loss: −2.54 USDC"),
]


RISK_WORDS = {1: "Calm", 2: "Calm", 3: "Steady", 4: "Steady", 5: "Balanced", 6: "Balanced", 7: "Bold", 8: "Bold", 9: "All in", 10: "All in"}


def coach_card(end: str) -> str:
    """Two panels, two functions (the operator, 2026-10-26: "coach je top staci aby byl staticky ... a ma byt mimo ten
    risk panel, to je zvlast funkcionalita. risk panel si muze ovladat kazdy i bez coache"):
    the coach -- the icon and on/off, on a paid plan -- and under it the risk, which every owner sets, coach or not
    (an hour before the end, not first: more risk). With the coach on, NEXUS tunes the bot inside that risk."""
    seat = OWNER["my_seat"]
    coach = f"""<section class="at-card v4-coach" data-v4="coach" data-v4-as="pro">
 <div class="v4-coach-h"><span class="v4-plan" data-v4-plan>PRO</span><label class="at-sw v4-sw-lg"><input type="checkbox" checked data-v4-sw aria-label="NEXUS coach on or off"><i></i></label></div>
 <div class="v4-coach-ico-w">{art.coach_icon()}</div>
 <div class="v4-coach-n">NEXUS <b>COACH</b></div>
 <div data-v4-off hidden><span class="at-btn ghost wide">See plans ›</span></div>
 <div class="v4-view" aria-label="Preview as"><button type="button" class="on" data-v4-as="pro">Pro</button><button type="button" data-v4-as="free">Free</button></div>
</section>"""
    risk = f"""<section class="at-card v4-riskcard" data-v4="risk">
 <div class="v4-risk-h"><span class="at-lbl">Risk</span><span class="v4-ctx"><span><b>#{seat["rank"]}</b>/6</span><span><b data-end="{end}">10H</b> left</span></span></div>
 <div class="v4-risk" data-level="5"><div class="v4-gauge-w">{art.gauge(5)}
   <div class="v4-risk-v"><b data-v4-risk-v>5</b><span data-v4-risk-w>{RISK_WORDS[5]}</span></div></div>
  <input type="range" min="1" max="10" step="1" value="5" data-v4-risk aria-label="Risk">
  <div class="v4-risk-f"><span>SAFE</span><span>ALL IN</span></div></div>
 <p class="v4-risk-say">How hard your bot plays: trade size, stop loss and take profit. Change it any time.</p>
</section>"""
    return coach + risk


def tunelog_card() -> str:
    """Every check NEXUS makes is a row, with who and why; it lives in the Changelog tab, not on the coach."""
    rows = "".join(
        f'<li><span class="tm">{tm}</span><span class="at-tag {"ok" if t else "house"}">{"TUNED" if t else "CHECKED"}</span> '
        f'<b>{what}</b> · {why}</li>' for tm, t, what, why in LOG)
    return (f'<section class="at-card at-cl" data-v4="tunelog"><h3><span>NEXUS tunes</span><span class="dim">'
            f'{sum(1 for x in LOG if x[1])}</span></h3><ul class="at-nx-log">{rows}</ul></section>')


def lanes_html() -> str:
    st = OWNER["my_bot_settings"]
    out = ""
    for key, nm in (("perpetual", "Perpetual epochs"), ("clob", "CLOB pairs"), ("event_cards", "Event cards"),
                    ("arena", "Arena"), ("catalog", "Catalog")):
        ln = st["lanes"][key]
        info = st["lane_info"][key]
        if key == "perpetual":
            sc = "".join(f'<button type="button" class="at-pill on" data-perp="{s}" aria-pressed="true">{s}</button>' for s in st["perpetual_universe"])
        elif key in ("clob", "catalog"):
            sc = f'<input class="at-add" type="text" maxlength="40" placeholder="+ {"pair" if key == "clob" else "symbol"}" aria-label="Add" autocomplete="off">'
        else:
            sc = f'<span class="dim">{"standard filters" if key == "event_cards" else "all"}</span>'
        out += (f'<div class="at-lane{" on" if ln["on"] else ""}" data-lane="{key}"><label class="at-sw"><input type="checkbox"{" checked" if ln["on"] else ""} aria-label="{nm} on or off"><i></i></label>'
                f'<div class="ln"><b>{nm}</b><small>{info["hint"] if key != "arena" else "stocks, crypto, prediction markets"}</small></div><div class="sc">{sc}</div></div>')
    return out


def trades_html() -> str:
    rows = ""
    for t in OWNER["your_trades"]:
        px = f'{t["entry"]:.6g} → {t["exit"]:.6g}'
        rows += (f'<div class="lt"><span class="tm">{t["at"][11:16]}</span><b>{t["symbol"]} {"↑" if t["side"] == "buy" else "↓"}</b>'
                 f'<span class="px">{px}</span><span class="{"pos" if t["pnl_usdc"] > 0 else "neg"}">{usd(t["pnl_usdc"]).replace("+$", "+$")}</span></div>')
    return rows


def aside(end: str) -> str:
    seat, st = OWNER["my_seat"], OWNER["my_bot_settings"]
    fx = st["fixed"]
    cap = 25.0
    pnl = seat["pnl_usdc"]
    cells = "<i></i>" * 20
    return f"""<aside class="at-side2" id="atSide"><div class="at-tabs" id="atTabs">
<div class="at-tabbar" role="tablist" aria-label="Your bot"><button type="button" role="tab" class="on" aria-selected="true" data-tab="coach">Coach</button><button type="button" role="tab" aria-selected="false" data-tab="settings" tabindex="-1">Settings</button><button type="button" role="tab" aria-selected="false" data-tab="trades" tabindex="-1">Trade log</button><button type="button" role="tab" aria-selected="false" data-tab="log" tabindex="-1">Changelog</button></div>
<div class="at-pane" role="tabpanel" data-pane="coach">{coach_card(end)}</div>
<div class="at-pane" role="tabpanel" data-pane="settings" hidden>
<section class="at-card at-ctl" id="atCtl" data-seat="87">
 <div class="at-ctl-h"><span class="at-ava you" style="--c:#7FE6FF"><svg viewBox="0 0 40 40" aria-hidden="true"><use href="#at-bot-d"></use></svg></span><div class="who"><span class="at-lbl">Your bot</span><b>{seat["bot"]}</b></div><span class="at-tag you">YOU</span></div>
 <div class="at-capline"><span class="at-lbl">Capital at this table</span><b>${cap:.0f}</b> <span class="cl">P&amp;L <em class="neg">{usd(pnl)}</em> · now <b>${cap + pnl:.2f}</b></span></div>
 <div class="at-tiles at-own3"><div><b>#{seat["rank"]}</b><span>rank</span></div><div><b><span class="neg">{pct(seat["roi_pct"])}</span></b><span>ROI</span></div><div><b class="pos">{seat["wins_now_usdc"]:,.0f} ET10</b><span>prize now</span></div></div>
 <div class="at-allow"><div class="ah"><span class="at-lbl">Today <b>0</b> / <span>{fx["daily_new_trades"]}</span></span><span>resets 00:00 UTC</span></div><div class="at-cells">{cells}</div></div>
 <div class="at-ctl-box"><div class="at-ctl-bh"><span class="at-lbl">What it trades</span><span class="dim">the bot page's market lanes</span></div>{lanes_html()}</div>
 <div class="at-ctl-box"><div class="at-ctl-bh"><span class="at-lbl">Risk</span><span class="dim">per trade</span></div>
  <div class="at-rng"><div class="rh"><span>Stop loss</span><b>{st["stop_loss_pct"]:g}%</b></div><input type="range" min="1" max="20" step="0.5" value="{st["stop_loss_pct"]:g}" aria-label="Stop loss %"><div class="rf"><span>1%</span><span>20%</span></div></div>
  <div class="at-rng"><div class="rh"><span>Take profit</span><b>{st["take_profit_pct"]:g}%</b></div><input type="range" min="5" max="100" step="0.5" value="{st["take_profit_pct"]:g}" aria-label="Take profit %"><div class="rf"><span>5%</span><span>100%</span></div></div>
  <p class="at-fixed">These are fixed for the whole tournament: Max position <b>{fx["max_position_pct"]:g}%</b> · Open positions <b>{fx["max_open_positions"]}</b> · Leverage <b>{fx["leverage_cap"]} max</b> · New trades <b>{fx["daily_new_trades"]} a day</b></p></div>
 <div class="at-ctl-box at-this"><span class="at-lbl">This change</span><p>No change from what runs now.</p><small class="dim">The table log says that you changed something, never what.</small></div>
 <div class="at-vline"><span>Trades on <b>Cymetica</b></span><a href="#">Settings ›</a></div>
 <div class="at-ctl-foot"><div class="at-btns" style="width:100%"><button class="at-btn no" type="button">Reset</button><button class="at-btn go" type="button" disabled>Apply to my bot</button></div></div>
 <p class="at-chcount"><b>2 changes</b> at this table: <span class="v4-who">NEXUS</span> 21 Oct 07:56 · <span class="v4-who o">OWNER</span> 23 Oct 20:53</p>
</section></div>
<div class="at-pane" role="tabpanel" data-pane="trades" hidden><section class="at-card" id="atLast"><h3><span>Recent trades</span><span class="dim">{len(OWNER["your_trades"])} so far</span></h3><div class="at-last">{trades_html()}</div></section></div>
<div class="at-pane" role="tabpanel" data-pane="log" hidden>
 {tunelog_card()}
 <section class="at-card at-cl"><h3><span>Your changes</span><span class="dim">2</span></h3><div class="at-chl"><div class="ch"><time datetime="2026-10-23T20:53:50+00:00">20:53</time><span>{MINE} changed markets</span></div><div class="ch"><time datetime="2026-10-21T07:56:23+00:00">07:56</time><span>{MINE} changed markets</span></div></div></section></div>
</div></aside>"""


# ------------------------------------------------------------------------------------------------ YOU marks

def mark_mine(doc) -> None:
    for s in doc.xpath('//span[contains(@class,"at-seat")][.//span[contains(@class,"at-ava")][@title="%s"]]' % MINE):
        s.set("class", s.get("class") + " you")
        ava = s.xpath('.//span[contains(@class,"at-ava")]')[0]
        ava.addnext(frag('<span class="yt at-tag you">YOU</span>')[0])
    for r in doc.xpath('//div[contains(@class,"at-lr")]'):
        nm = r.xpath('.//div[contains(@class,"nm")]/b')
        if nm and (nm[0].text or "").strip() == MINE:
            r.set("class", r.get("class") + " you")
            nm[0].append(frag('<span class="at-tag you">YOU</span>')[0])
            nm[0].text = (nm[0].text or "") + " "


def who_tags(doc) -> None:
    """The changelog says who changed each setting, NEXUS or the owner; today it says only that it changed."""
    tune = {x["at"][:16] for x in OWNER["my_nexus_lock"]["tunes"]}
    for ch in doc.xpath('//div[contains(@class,"at-chl")]/div[contains(@class,"ch")]'):
        t = ch.find("time")
        sp = ch.find("span")
        if t is None or sp is None or sp.xpath('.//*[contains(@class,"v4-who")]'):
            continue
        nexus = (t.get("datetime") or "")[:16] in tune
        em = L.fragment_fromstring(f'<span class="v4-who{"" if nexus else " o"}">{"NEXUS" if nexus else "OWNER"}</span>')
        em.tail = " " + (sp.text or "").replace(MINE + " ", "")
        sp.text = None
        sp.insert(0, em)


# ------------------------------------------------------------------------------------------------ the race

def owner_race(doc) -> None:
    sec = doc.xpath('//section[contains(@class,"at-race")]')
    pb = doc.xpath('//span[contains(@class,"at-pb")][@data-start]')
    if not sec or not pb:
        return
    svg = sec[0].find(".//svg")
    mine = next((p for p in svg.findall("polyline") if (p.findtext("title") or "").startswith(MINE)), None)
    if mine is None:
        return
    pts = [tuple(map(float, p.split(","))) for p in mine.get("points").split()]
    start, end = (datetime.fromisoformat(pb[0].get(k)) for k in ("data-start", "data-end"))
    x0 = pts[0][0]
    x1 = 1160.0         # the race's right edge, the table's end

    def y_at(x):
        for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
            if xa <= x <= xb:
                return ya + (yb - ya) * (x - xa) / ((xb - xa) or 1)
        return pts[-1][1]

    span = (end - start).total_seconds()
    xs = sorted(x0 + (datetime.fromisoformat(t["at"]) - start).total_seconds() / span * (x1 - x0) for t in OWNER["your_trades"])
    groups: list[list[float]] = []
    for x in xs:
        if groups and x - groups[-1][0] < 16:      # touching circles become one
            groups[-1].append(x)
        else:
            groups.append([x])
    for k, v in (("stroke", "#00cfff"), ("stroke-width", "3.6"), ("stroke-linecap", "round"), ("filter", "url(#at-race-glow)")):
        mine.set(k, v)
    mine.attrib.pop("stroke-opacity", None)
    mine.attrib.pop("stroke-dasharray", None)
    mine.find("title").text = f"{MINE} (you) {pct(OWNER['my_seat']['roi_pct'])}"
    svg.remove(mine)
    lead = [p for p in svg.findall("polyline") if p.get("stroke") == "#A9B8CC"]
    (lead[0] if lead else svg.findall("polyline")[-1]).addnext(mine)
    out = ""
    for g in groups:
        x = sum(g) / len(g)
        y = y_at(x)
        if len(g) == 1:
            out += f'<circle class="v4-mk" cx="{x:.1f}" cy="{y:.1f}" r="5.5" fill="#0a0e17" stroke="#E6EDF7" stroke-width="2.2"></circle>'
        else:
            out += (f'<circle class="v4-mk" cx="{x:.1f}" cy="{y:.1f}" r="9.5" fill="#0a0e17" stroke="#E6EDF7" stroke-width="2.2"></circle>'
                    f'<text x="{x:.1f}" y="{y + 4:.1f}" text-anchor="middle" font-size="11" font-weight="800" fill="#E6EDF7">{len(g)}</text>')
    for e in reversed(frag(f"<svg>{out}</svg>")[0]):
        mine.addnext(e)
    now_x, end_y = pts[-1]
    for c in svg.findall("circle"):
        if c.get("r") == "3" and abs(float(c.get("cy")) - end_y) < 0.05:
            c.set("r", "6")
            c.set("fill", "#00cfff")
    label = f'YOU #{OWNER["my_seat"]["rank"]} {pct(OWNER["my_seat"]["roi_pct"]).replace("-", "−")}'
    w = 16 + 7.6 * len(label)
    g = frag(f'<svg><g><rect x="{now_x - 14 - w:.1f}" y="{end_y - 7.9:.1f}" width="{w:.1f}" height="26" rx="8" fill="#00cfff"></rect>'
             f'<text x="{now_x - 14 - w + 12:.1f}" y="{end_y + 10:.1f}" font-size="13" font-weight="800" fill="#0a0e17">{label}</text></g></svg>')[0][0]
    svg.append(g)
    leg = doc.xpath('//div[contains(@class,"at-race-legend")]')
    if leg:
        leg[0].insert(0, frag('<span><i style="background:#00cfff"></i>You</span>')[0])
        leg[0].insert(1, frag('<span><i class="ring"></i>Your trades</span>')[0])
        leg[0].insert(2, frag('<span><i class="ring v4-n">3</i>Several, merged</span>')[0])
    lab = svg.get("aria-label") or ""
    svg.set("aria-label", lab + f" {label}.")


def install_lobby(doc) -> None:
    """The lobby as the owner of seat 87 sees it: their hero shows "Your agent" instead of "Next to fill", and our
    card at table 15 carries the YOU marks. Markup read from the operator's signed-in session, 2026-10-26."""
    card = doc.xpath('//a[@data-table-id="15"]')
    if not card:
        return
    card = card[0]
    seat = OWNER["my_seat"]
    end = (card.xpath('.//*[@data-end]/@data-end') or [""])[0]
    vol = min(100, round(seat["volume_usdc"] / (seat["volume_usdc"] + seat["volume_to_qualify_usdc"]) * 100))
    me = frag(f"""<a class="at-me" href="/agent-tournaments/table/15" aria-label="Your agent at ET10 100 #15">
 <div class="top"><span class="at-ava you" style="--c:#7FE6FF" title="{seat["bot"]}"><svg viewBox="0 0 40 40" aria-hidden="true"><use href="#at-bot-d"></use></svg></span><div class="who"><b>{seat["bot"]}</b><span>YOUR AGENT · ET10 100 #15</span></div><span class="at-live"><i class="at-dot"></i>LIVE</span></div>
 <div class="at-big2"><div><span class="at-lbl">Rank</span><div class="at-rank">#{seat["rank"]}<small>/6</small></div></div><div style="text-align:right"><span class="at-lbl">ROI</span><div class="at-roi-big"><span class="neg">{pct(seat["roi_pct"])}</span></div></div></div>
 <div class="at-mini3"><div><span class="at-lbl">Ends in</span><span class="v" data-end="{end}">10H</span></div><div><span class="at-lbl">Wins now</span><span class="v pos">{seat["wins_now_usdc"]:,.0f} ET10</span></div><div><span class="at-lbl">Volume</span><span class="v">{vol}%</span><div class="at-meter"><i style="width:{vol}%"></i></div></div></div>
 <p class="at-hint">${seat["volume_to_qualify_usdc"]:.2f} more volume to lock it</p><span class="at-btn ghost wide" style="margin-top:12px">WATCH</span></a>""")[0]
    for feat in doc.xpath('//a[contains(@class,"at-feat")]'):
        feat.getparent().replace(feat, me)
    card.set("class", card.get("class") + " mine")
    for s in card.xpath('.//span[contains(@class,"at-seat")][.//span[contains(@class,"at-ava")][@title="%s"]]' % MINE):
        s.set("class", s.get("class") + " you")
        s.xpath('.//span[contains(@class,"at-ava")]')[0].addnext(frag('<span class="yt at-tag you">YOU</span>')[0])
    foot = card.xpath('.//div[contains(@class,"at-tfoot")]')[0]
    for k in list(foot):
        foot.remove(k)
    for k in frag(f'<span class="who"><span class="at-tag you">YOU</span><b>{seat["bot"]}</b></span>'
                  f'<span class="v"><span class="cy">#{seat["rank"]}</span> · <span class="neg">{pct(seat["roi_pct"])}</span></span>'):
        foot.append(k)


def install(doc) -> None:
    mark_mine(doc)
    owner_race(doc)
    end = (doc.xpath('//span[contains(@class,"at-pb")]/@data-end') or [""])[0]
    room = doc.xpath('//*[@id="atRoom"]')[0]
    room.set("class", (room.get("class") or "") + " has-side")
    room.append(L.fragment_fromstring(aside(end)))
    who_tags(doc)
