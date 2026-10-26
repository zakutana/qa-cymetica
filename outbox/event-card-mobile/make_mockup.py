"""Build index.html and board.html (this folder): the Event Cards deck (/events) on a phone, a card you swipe that never scrolls.

The operator, 2026-10-26, in four rounds: on a phone /events is a card you swipe left and right, and that stays; round 1 had
too much on a scrolling card ("karta v zadnem pripade nesmi byt scrollovatelna"); round 2 was clean but "6/10"; round 3 got
the figure and the chart right; then he showed the card he once designed himself -- the same card graded by how explosive the
event is, the frame and badge telling you before you read it, coloured "podle kombinace jak silne cislo je v sentimentu a
smer" -- and said "takovy design chci", with three corrections: no Legendary / Rare ("Hot a Big, nebo jine terminy, ktere
nebudou trapne"), no BULLISH / BEARISH ("ma tam byt ten news sentiment"), and no impact meter (the impact score is gone from
the API: 30 of 647 live cards, none created after 2026-09-12; asked in MSG-0251).

So, read from the API and nothing else:
  - the tier is the news sentiment's strength, |headline_sentiment_score|: HOT from 0.7, WARM from 0.3, QUIET below, with
    its DROP RATE, the share of live cards in that tier (snapshot.py counts all of them);
  - the colour is the sentiment's sign: positive green, negative red, zero neither. His picture used purple and gold for
    the tiers; the site's colour rule forbids both, so the tier is carried by how strongly the frame burns, not by a hue;
  - the face: tier strip, the picture (age, source, LIVE, the (i), his P&L where he holds the card), the title, NEWS
    SENTIMENT with its number on a -1..+1 track, SINCE LAUNCH with 1 DAY under it, the chart (green or red by the shown
    period's move), Back, Skip, Watch, Sell, Buy. His linked-assets row shows only on a card of two assets or more: on a
    one-asset card it repeats the title's ticker, and the API's association_score (his "corr.") is 0 on 646 of 647.
  - allocation, amount and Paper | Live: the Buy sheet a right swipe or Buy already opens; description, symbol, market
    cap, card index, index price, per-asset split, structure, upvote, History, Share, Embed: the sheet behind the (i).
Opened on a phone it is a deck you can swipe: right flies the card off and opens the Buy sheet, left skips, Back brings
the last card back, (i) opens the details. ?c=hot|warm|quiet picks the top card and ?s=swipe|buy|info freezes a moment for
the pictures.

Real figures: event-data.json (snapshot.py, Cymetica's public API). His own -$0.07 on the ESTC card and the $100,000 paper
balance are read off the page as he sees it.
"""
from __future__ import annotations

import html
import json
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
D = json.loads((HERE / "event-data.json").read_text(encoding="utf-8"))
CARDS = D["cards"]
READ = datetime.fromisoformat(D["read_at"])
esc = lambda s: html.escape(str(s), quote=True)

MY_PNL = {"9b46ad13-1bdc-4db6-a3d6-89031c2fa07e": "-$0.07"}   # his position, the red badge on his page
PAPER = "$100,000.00"                                          # paper balance, as the page shows it
KEY = {"hot": "hot", "warm": "warm", "quiet": "quiet"}


def pct(v):
    return f"{'+' if v >= 0 else '−'}{abs(v):.2f}%"


def since(c):
    return (c["current_index"] / c["index_base"] - 1) * 100


def day(c):
    p = c["hist"]["points"]
    return (p[-1]["index"] / p[0]["index"] - 1) * 100


def ago(c):
    t = datetime.fromisoformat(c.get("published_at") or c["created_at"])
    h = (READ - t).total_seconds() / 3600
    return f"{int(h / 24)}d ago" if h >= 24 else (f"{int(h)}h ago" if h >= 1 else f"{int(h * 60)}m ago")


def source(c):
    host = urlparse(c.get("source_url") or "").netloc
    return host[4:] if host.startswith("www.") else host


def structure(c):
    """"SAIB - Single AI Index Basket (SAIB)" as the new look prints it: "SAIB · Single AI Index Basket"."""
    name = (c.get("vehicle_structure_name") or c.get("vehicle_structure") or "").replace(f' ({c.get("vehicle_structure")})', "")
    return name.replace(" - ", " · ") or "Event card"


def sent(c):
    return c.get("headline_sentiment_score") or 0


def hue(c):
    s = sent(c)
    return "pos" if s > 0 else ("neg" if s < 0 else "neu")


def drop_rate(t):
    return f'{D["tiers"][t] / D["live_cards"] * 100:.1f}%'


# ---------------------------------------------------------------- the chart: card index, last 24 hours, no text inside
END = 96          # the line ends at 96 % of the width; its last value is tagged above the end
TOP, BOT = 16, 8  # % of the plot kept free above and below the line


def chart(c):
    """The line and its fill are an svg stretched to the plot's box; the last value and its dot are html, so stretching
    cannot squash them. Green or red by the period's move."""
    pts = c["hist"]["points"]
    xs = [datetime.fromisoformat(p["t"]).timestamp() for p in pts]
    ys = [p["index"] for p in pts]
    lo, hi = min(ys), max(ys)
    if hi - lo < 1e-9:
        lo, hi = lo - 1, hi + 1
    X = lambda t: (t - xs[0]) / (xs[-1] - xs[0]) * END
    Y = lambda v: TOP + (hi - v) / (hi - lo) * (100 - TOP - BOT)
    line = " ".join(f"{X(x):.2f},{Y(y):.2f}" for x, y in zip(xs, ys))
    area = f"0,100 {line} {END},100"
    oy = Y(ys[0])
    gid = f'ar-{c["tier"]}'
    return (f'<div class="plot"><svg viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><defs>'
            f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" class="s0"/><stop offset=".75" class="s1"/>'
            '<stop offset="1" class="s2"/></linearGradient></defs>'
            f'<line x1="0" x2="100" y1="{oy:.2f}" y2="{oy:.2f}" class="open"/>'
            f'<polygon points="{area}" fill="url(#{gid})"/><polyline points="{line}" class="ln"/></svg>'
            f'<span class="olab" style="top:{oy:.2f}%">{ys[0]:.2f}</span>'
            f'<span class="dot" style="top:{Y(ys[-1]):.2f}%"></span>'
            f'<span class="tagv{" below" if Y(ys[-1]) < 45 else ""}" style="top:{Y(ys[-1]):.2f}%">{ys[-1]:.2f}</span></div>')


ICON = {
    "back": '<path d="M9 7 4 12l5 5M4 12h11a5 5 0 0 1 0 10h-2"/>',
    "skip": '<path d="M6 6l12 12M18 6 6 18"/>',
    "watch": '<path d="M12 20.5s-7.5-4.6-7.5-10.1A4.3 4.3 0 0 1 12 7.6a4.3 4.3 0 0 1 7.5 2.8c0 5.5-7.5 10.1-7.5 10.1z"/>',
    "sell": '<path d="M3 7l6 6 4-4 8 8M15 17h6v-6"/>',
    "buy": '<path d="M3 17l6-6 4 4 8-8M15 7h6v6"/>',
    "info": '<circle cx="12" cy="12" r="9"/><path d="M12 11v6M12 7.5v.01"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5l3 2"/>',
}


def icon(name, cls="ic"):
    return f'<svg viewBox="0 0 24 24" class="{cls}" aria-hidden="true">{ICON[name]}</svg>'


def card_html(c):
    s, d = since(c), day(c)
    sv = sent(c)
    knob = (sv + 1) / 2 * 100
    pnl = MY_PNL.get(c["id"])
    assets = ""
    if len(c["basket"]) > 1:
        chips = "".join(f'<span class="as"><b>{esc(a["symbol"])}</b><i>{esc(a.get("asset_type") or "")}</i></span>' for a in c["basket"][:3])
        more = f'<span class="as more">+{len(c["basket"]) - 3}</span>' if len(c["basket"]) > 3 else ""
        assets = f'<div class="assets">{chips}{more}</div>'
    return f"""<article class="card t-{c['tier']} {hue(c)} {'up' if s >= 0 else 'down'} {'c-up' if d > 0 else ('c-down' if d < 0 else 'c-flat')}" data-key="{c['tier']}">
<div class="stamp bull">BUY</div><div class="stamp skip">SKIP</div>
<div class="body">
 <div class="tier"><span class="tb"><i></i>{c['tier'].upper()}</span><span class="dr"><span>Drop rate</span><b>{drop_rate(c['tier'])}</b></span></div>
 <div class="art"><img src="{esc(c['image_url'])}" alt="">
  <span class="ago">{icon('clock', 'ic s')}{ago(c)}</span>
  <div class="top2">{f'<span class="pnl" title="Your P&amp;L on this card">{pnl}</span>' if pnl else ''}<span class="pill live"><i></i>LIVE</span><span class="info" aria-label="Details">{icon('info')}</span></div>
  <span class="src">{esc(source(c))}</span></div>
 <h1 class="title">{esc(c['title'])}</h1>
 <div class="sent"><div class="sh"><span class="k">News sentiment</span><b>{f'{sv:+.2f}'.replace('-', '−')}</b></div>
  <div class="track"><i class="knob" style="left:{knob:.1f}%"></i></div><div class="ticks"><span>−1</span><span>0</span><span>+1</span></div></div>
 {assets}
 <div class="stage">{chart(c)}
  <div class="figs"><div class="k">Since launch</div><div class="v">{pct(s)}</div>
   <div class="row2"><div class="day"><span class="{'g' if d > 0 else ('r' if d < 0 else 'd')}">{'▲' if d > 0 else ('▼' if d < 0 else '■')} {pct(d)}</span> <span class="d">1 day</span></div>
   <div class="tog"><span class="on">1d</span><span>5d</span><span>30d</span></div></div></div></div>
</div>
<nav class="actions">
 <span class="act" data-do="back">{icon('back')}<em>Back</em></span>
 <span class="act" data-do="skip">{icon('skip')}<em>Skip</em></span>
 <span class="act watch" data-do="watch">{icon('watch')}<em>Watch</em></span>
 <span class="act bear" data-do="sell">{icon('sell')}<em>Sell</em></span>
 <span class="act bull" data-do="buy">{icon('buy')}<em>Buy</em></span></nav>
</article>"""


def buy_sheet(c):
    return (f'<section class="sheet" data-kind="buy" data-key="{c["tier"]}"><i class="grab"></i>'
            f'<div class="sh1"><b>Buy</b><span class="d">{esc(c["title"].split(" — ")[0][:24])} · index {c["current_index"]:.2f}</span></div>'
            '<div class="seg2"><span class="on">Paper</span><span>Live</span></div>'
            f'<div class="avail">{PAPER} available</div>'
            '<div class="pc"><span class="on">0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span></div>'
            '<div class="amt">$0.00</div>'
            '<span class="buy">Confirm Buy</span><span class="cancel" data-close>Cancel</span></section>')


def info_sheet(c):
    sym = c.get("evcdx_symbol") or f'EVCDX-{c["basket"][0]["symbol"]}'
    split = "".join(f'<div class="srow"><b>{esc(a["symbol"])}</b><span class="bar"><b style="width:{a["weight"] * 100:.0f}%"></b></span>'
                    f'<span>{a["weight"] * 100:.0f}%</span></div>' for a in c["basket"][:4])
    cap = "— not minted yet" if not c.get("arc_coin") and not c.get("pons_coin") else "—"
    return (f'<section class="sheet" data-kind="info" data-key="{c["tier"]}"><i class="grab"></i>'
            f'<div class="sh1"><span class="pill">{esc(structure(c))}</span><span class="vote">▲ {c.get("upvotes", 0)}</span></div>'
            f'<p class="about">{esc(c["summary"])}</p>'
            '<div class="kv">'
            f'<div><span class="k">Card index</span><b>{c["current_index"]:.2f}</b><i>base {c["index_base"]:.0f}</i></div>'
            f'<div><span class="k">Index price</span><b>${c["pw_index"]:,.2f}</b><i>launch ${c["pw_base"]:,.2f}</i></div>'
            f'<div><span class="k">Symbol</span><b>{esc(sym)}</b></div>'
            f'<div><span class="k">Market cap</span><b class="d">{cap}</b></div></div>'
            f'<div class="split"><span class="k">Per-asset split</span>{split}</div>'
            '<div class="links"><span class="btn">History</span><span class="btn">Share</span><span class="btn">Embed</span></div></section>')


CSS = """
:root{--bg:#0a0e17;--deep:#06090f;--navy:#0d1520;--navy2:#111a28;--line:#16233a;--line2:#1a2a44;--line3:#1e3050;
--text:#e6edf7;--dim:#a9b8cc;--dim2:#7f93ad;--cyan:#00cfff;--green:#00ff88;--red:#ff4444;--blue:#3b82f6}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
html,body{height:100%;overflow:hidden;background:var(--bg);color:var(--text);font-family:'JetBrains Mono',monospace;font-size:13px;-webkit-font-smoothing:antialiased}
body{position:relative;background:radial-gradient(ellipse 90% 34% at 20% -6%,rgba(0,207,255,.10),rgba(0,207,255,0) 70%),var(--bg);overscroll-behavior:none}
/* the page's glow takes the top card's colour */
body::before{content:'';position:absolute;left:-20%;right:-20%;bottom:-6%;height:64%;pointer-events:none;transition:background .4s;
 background:radial-gradient(ellipse 60% 55% at 50% 72%,rgba(var(--glow,127,147,173),.18),rgba(var(--glow,127,147,173),0) 70%)}
body[data-hue=pos]{--glow:0,255,136}body[data-hue=neg]{--glow:255,68,68}body[data-hue=neu]{--glow:127,147,173}
.g{color:var(--green)}.r{color:var(--red)}.d{color:var(--dim2)}
.k{font-size:9.5px;letter-spacing:.18em;text-transform:uppercase;color:var(--dim);font-weight:700}
/* the line above the deck: live, progress; the site's menu button sits at the right */
.top{position:absolute;top:0;left:0;right:0;height:52px;display:flex;align-items:center;gap:12px;padding:0 66px 0 18px;z-index:2}
.lv{display:flex;align-items:center;gap:7px;color:var(--cyan);font-size:11px;font-weight:700;letter-spacing:.12em;white-space:nowrap}.lv i{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 8px var(--green)}
.prog{margin-left:auto;display:flex;align-items:center;gap:8px;color:var(--dim);font-size:11px;font-weight:700;white-space:nowrap}
.prog i{display:block;width:60px;height:4px;border-radius:99px;background:var(--line3);overflow:hidden}.prog i b{display:block;height:100%;width:3%;background:var(--green)}
.menu{position:absolute;top:4px;right:10px;width:44px;height:44px;border-radius:50%;border:1px solid var(--line3);background:rgba(13,21,32,.92);display:grid;place-items:center;z-index:2}
.menu i{display:block;width:18px;height:2px;background:var(--cyan);border-radius:2px;box-shadow:0 -6px 0 var(--cyan),0 6px 0 var(--cyan)}

/* the deck */
.deck{position:absolute;top:54px;left:10px;right:10px;bottom:22px;z-index:1}
.card{--hue:127,147,173;--ln:0,207,255;position:absolute;inset:0;border-radius:28px;overflow:hidden;touch-action:none;user-select:none;
 background:linear-gradient(180deg,rgba(var(--hue),.10),rgba(var(--hue),0) 32%),var(--navy);
 border:1.5px solid var(--line3);transform-origin:50% 100%;transition:transform .32s cubic-bezier(.2,.8,.2,1),opacity .32s,box-shadow .3s}
.card.pos{--hue:0,255,136}.card.neg{--hue:255,68,68}
.card.c-up{--ln:0,255,136}.card.c-down{--ln:255,68,68}
.card.dragging{transition:none}
.card.b1{transform:translateY(10px) scale(.955);filter:brightness(.8)}
.card.b2{transform:translateY(20px) scale(.91);filter:brightness(.6)}
.card.b2 .body,.card.b2 .actions{visibility:hidden}
/* how hot the news is: the frame burns in the sentiment's colour, hardest on HOT */
.card.t-hot{border-color:rgba(var(--hue),.9);box-shadow:inset 0 1px 0 rgba(230,237,247,.18),inset 0 0 50px rgba(var(--hue),.10),0 0 0 1px rgba(var(--hue),.25),0 0 70px rgba(var(--hue),.35),0 28px 60px rgba(0,0,0,.55)}
.card.t-warm{border-color:rgba(var(--hue),.5);box-shadow:inset 0 1px 0 rgba(230,237,247,.14),0 0 40px rgba(var(--hue),.16),0 28px 60px rgba(0,0,0,.55)}
.card.t-quiet{border-color:var(--line3);background:var(--navy);box-shadow:inset 0 1px 0 rgba(230,237,247,.10),0 28px 60px rgba(0,0,0,.55)}
.body{position:absolute;inset:0;display:flex;flex-direction:column;overflow:hidden}
.tier{flex:none;display:flex;align-items:center;justify-content:space-between;height:40px;padding:0 18px;
 background:linear-gradient(90deg,rgba(var(--hue),.24),rgba(var(--hue),.04));border-bottom:1px solid rgba(var(--hue),.22)}
.t-warm .tier{background:linear-gradient(90deg,rgba(var(--hue),.13),rgba(var(--hue),.02))}
.t-quiet .tier{background:rgba(127,147,173,.05);border-bottom-color:var(--line2)}
.tb{display:flex;align-items:center;gap:9px;font-weight:700;font-size:12px;letter-spacing:.26em;color:rgb(var(--hue))}
.t-hot .tb{text-shadow:0 0 14px rgba(var(--hue),.8)}.t-quiet .tb{color:var(--dim)}
.tb i{width:8px;height:8px;border-radius:50%;background:rgb(var(--hue));box-shadow:0 0 10px rgb(var(--hue))}
.t-hot .tb i{animation:beat 1.6s ease-in-out infinite}.t-quiet .tb i{box-shadow:none;background:var(--dim2)}
@keyframes beat{50%{box-shadow:0 0 2px rgb(var(--hue));transform:scale(.7)}}
.dr{text-align:right;line-height:1.15}.dr span{display:block;font-size:8px;letter-spacing:.2em;text-transform:uppercase;color:var(--dim2)}
.dr b{font-size:12px;color:rgb(var(--hue))}.t-quiet .dr b{color:var(--dim)}
/* the picture */
.art{position:relative;flex:none;height:clamp(78px,15vh,132px);margin:12px 14px 0;border-radius:16px;overflow:hidden;border:1px solid rgba(230,237,247,.08);background:var(--deep)}
.art img{width:100%;height:100%;object-fit:cover;object-position:50% 12%;display:block}
.art::after{content:'';position:absolute;inset:0;background:linear-gradient(180deg,rgba(6,9,15,.15),rgba(6,9,15,0) 40%,rgba(6,9,15,.55))}
.ago,.src,.pnl{display:inline-flex;align-items:center;gap:5px;font-size:10.5px;font-weight:700;border-radius:8px;padding:4px 8px;background:rgba(6,9,15,.78);color:var(--text)}
.ago,.src{position:absolute;z-index:2}.ago{top:9px;left:9px}.src{bottom:9px;right:9px;color:var(--dim)}
.pnl{color:var(--red);border:1px solid rgba(255,68,68,.5);border-radius:99px;padding:4px 9px}
.ic.s{width:12px;height:12px}
.top2{position:absolute;top:8px;right:8px;z-index:2;display:flex;gap:6px;align-items:center}
.pill{display:inline-flex;align-items:center;gap:6px;font-size:10px;font-weight:700;letter-spacing:.08em;border:1px solid rgba(0,207,255,.45);color:var(--cyan);border-radius:99px;padding:5px 10px;background:rgba(6,9,15,.72);white-space:nowrap}
.pill.live{color:var(--green);border-color:rgba(0,255,136,.5)}.pill.live i{width:6px;height:6px;border-radius:50%;background:var(--green);box-shadow:0 0 8px var(--green)}
.info{width:30px;height:30px;border-radius:50%;background:rgba(6,9,15,.72);border:1px solid rgba(230,237,247,.22);display:grid;place-items:center;color:var(--text);cursor:pointer}
.info .ic{width:17px;height:17px}
.title{flex:none;margin:12px 18px 0;font-family:'Archivo Black',sans-serif;font-weight:400;font-size:20px;line-height:1.16;
 display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}
/* news sentiment: the number and where it sits between -1 and +1 */
.sent{flex:none;margin:12px 14px 0;padding:10px 14px 8px;border-radius:14px;background:rgba(6,9,15,.55);border:1px solid rgba(230,237,247,.07)}
.sent .sh{display:flex;align-items:center;justify-content:space-between}.sent .sh b{font-size:17px;color:rgb(var(--hue))}.neu .sent .sh b{color:var(--dim)}
.track{position:relative;height:5px;margin:10px 2px 0;border-radius:99px;background:linear-gradient(90deg,#ff4444,rgba(127,147,173,.35) 50%,#00ff88)}
.knob{position:absolute;top:50%;width:15px;height:15px;transform:translate(-50%,-50%);border-radius:50%;background:#e6edf7;border:3px solid rgb(var(--hue));box-shadow:0 0 12px rgba(var(--hue),.9)}
.neu .knob{border-color:var(--dim2);box-shadow:none}
.ticks{display:flex;justify-content:space-between;margin-top:6px;font-size:9px;color:var(--dim2)}
.assets{flex:none;display:flex;gap:6px;margin:10px 14px 0;overflow:hidden}
.as{display:inline-flex;align-items:baseline;gap:6px;border:1px solid var(--line3);border-radius:10px;padding:6px 10px;background:rgba(6,9,15,.5)}.as b{font-size:12px}.as i{font-style:normal;font-size:8.5px;letter-spacing:.12em;text-transform:uppercase;color:var(--dim2)}
/* the figure on top of the chart; the chart down to the card's foot */
.stage{position:relative;flex:1;min-height:0;margin-top:10px}
.figs{position:absolute;left:18px;right:14px;top:2px;z-index:2}
.row2{display:flex;align-items:center;justify-content:space-between;gap:10px;margin-top:6px}
.figs .v{font-family:'Archivo Black',sans-serif;font-size:min(50px,12.6vw);line-height:1;margin-top:6px;white-space:nowrap;
 background:linear-gradient(180deg,#e6edf7 0%,#00ff88 62%);-webkit-background-clip:text;background-clip:text;color:transparent;filter:drop-shadow(0 0 20px rgba(0,255,136,.42))}
.down .figs .v{background:linear-gradient(180deg,#e6edf7 0%,#ff4444 62%);-webkit-background-clip:text;background-clip:text;filter:drop-shadow(0 0 20px rgba(255,68,68,.42))}
.figs .day{font-size:12.5px;font-weight:700;white-space:nowrap}.figs .day .d{font-weight:400;font-size:10.5px;margin-left:4px}
.tog{flex:none;display:flex;gap:2px;background:rgba(6,9,15,.55);border:1px solid rgba(230,237,247,.12);border-radius:11px;padding:3px}
.tog span{min-width:36px;text-align:center;padding:6px 0;border-radius:8px;color:var(--dim2);font-weight:700;font-size:11px}.tog span.on{background:rgba(230,237,247,.12);color:var(--text)}
.plot{position:absolute;left:0;right:0;top:112px;bottom:80px}
.plot .tagv.below{transform:translate(-100%,60%)}
.plot svg{position:absolute;inset:0;width:100%;height:100%;overflow:visible}
.plot .s0{stop-color:rgb(var(--ln));stop-opacity:.36}.plot .s1{stop-color:rgb(var(--ln));stop-opacity:.06}.plot .s2{stop-color:rgb(var(--ln));stop-opacity:0}
.plot .open{stroke:#7f93ad;stroke-opacity:.5;stroke-dasharray:3 5;stroke-width:1;vector-effect:non-scaling-stroke}
.plot .ln{fill:none;stroke:rgb(var(--ln));stroke-width:2.6;stroke-linejoin:round;stroke-linecap:round;vector-effect:non-scaling-stroke;filter:drop-shadow(0 0 6px rgba(var(--ln),.75))}
.plot .olab,.plot .tagv,.plot .dot{position:absolute}
.plot .olab{left:18px;margin-top:5px;font-size:9.5px;color:var(--dim2)}
.plot .dot{left:96%;width:10px;height:10px;transform:translate(-50%,-50%);border-radius:50%;background:rgb(var(--ln));box-shadow:0 0 0 5px rgba(var(--ln),.22),0 0 16px rgba(var(--ln),.9)}
.plot .tagv{left:96%;transform:translate(-100%,-160%);margin-left:4px;background:rgb(var(--ln));color:var(--deep);font-weight:700;font-size:11.5px;border-radius:99px;padding:3px 9px}
/* the bar floats on glass over the chart's foot */
.actions{position:absolute;left:12px;right:12px;bottom:12px;z-index:3;display:grid;grid-template-columns:1fr 1fr 1fr 1.25fr 1.6fr;gap:7px;isolation:isolate}
.actions::before{content:'';position:absolute;z-index:-1;left:-12px;right:-12px;bottom:-12px;top:-40px;background:linear-gradient(180deg,rgba(13,21,32,0),rgba(13,21,32,.92) 55%)}
.act{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;height:58px;border-radius:17px;border:1px solid rgba(230,237,247,.10);
 background:rgba(17,26,40,.78);color:var(--dim);box-shadow:inset 0 1px 0 rgba(230,237,247,.08);cursor:pointer;transition:transform .12s}
.act:active{transform:scale(.94)}
.act em{font-style:normal;font-size:9.5px;font-weight:700;letter-spacing:.12em;text-transform:uppercase}
.ic{width:20px;height:20px;fill:none;stroke:currentColor;stroke-width:2;stroke-linecap:round;stroke-linejoin:round}
.act.watch{color:var(--cyan)}
.act.bear{color:var(--red);border-color:rgba(255,68,68,.5);background:rgba(255,68,68,.09)}
.act.bull{color:var(--deep);border-color:var(--green);background:var(--green);box-shadow:inset 0 1px 0 rgba(230,237,247,.45),0 0 24px rgba(0,255,136,.42)}
/* swipe stamps (today .ec-stamp), while dragging */
.stamp{position:absolute;top:58px;z-index:4;font-family:'Archivo Black',sans-serif;font-size:32px;letter-spacing:.08em;border:3px solid;border-radius:12px;padding:2px 14px;opacity:0;background:rgba(6,9,15,.6);pointer-events:none}
.stamp.bull{left:22px;color:var(--green);transform:rotate(-12deg)}.stamp.skip{right:22px;color:var(--dim);transform:rotate(12deg)}
.card.a.drag-right{border-color:var(--green);box-shadow:0 0 0 1px rgba(0,255,136,.5),0 0 50px rgba(0,255,136,.34),0 28px 60px rgba(0,0,0,.55)}
/* sheets: the Buy sheet (a right swipe or Buy opens it today) and the details behind the (i) */
.scrim{position:absolute;inset:0;background:rgba(6,9,15,.62);-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);z-index:30;opacity:0;pointer-events:none;transition:opacity .25s}
.sheet{position:absolute;left:0;right:0;bottom:0;z-index:31;background:rgba(13,21,32,.97);border:1px solid rgba(0,207,255,.25);border-bottom:none;border-radius:28px 28px 0 0;padding:10px 18px 24px;
 box-shadow:inset 0 1px 0 rgba(230,237,247,.16),0 -20px 60px rgba(0,0,0,.6);transform:translateY(105%);transition:transform .32s cubic-bezier(.2,.8,.2,1)}
.sheets-open .scrim{opacity:1;pointer-events:auto}.sheet.open{transform:none}
.grab{display:block;width:42px;height:4px;border-radius:9px;background:var(--line3);margin:0 auto 14px}
.sh1{display:flex;align-items:center;justify-content:space-between;gap:10px}.sh1 b{font-family:'Archivo Black',sans-serif;font-weight:400;font-size:26px}
.vote{display:inline-flex;border:1px solid var(--line3);border-radius:9px;padding:4px 10px;color:var(--dim);font-weight:700;font-size:11px}
.seg2{display:flex;gap:4px;background:var(--deep);border:1px solid var(--line2);border-radius:14px;padding:4px;margin-top:14px}
.seg2 span{flex:1;text-align:center;padding:11px 0;border-radius:10px;color:var(--dim2);font-weight:700;font-size:12.5px}.seg2 span.on{background:var(--navy2);color:var(--cyan);box-shadow:0 0 0 1px rgba(0,207,255,.4) inset}
.avail{margin-top:12px;color:var(--cyan);font-weight:700;font-size:12.5px}
.pc{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-top:10px}
.pc span{text-align:center;border:1px solid var(--line3);border-radius:12px;padding:13px 0;color:var(--dim);font-weight:700;font-size:12.5px}.pc span.on{border-color:var(--cyan);color:var(--cyan);box-shadow:0 0 14px rgba(0,207,255,.25)}
.amt{margin:16px 0;text-align:center;font-family:'Archivo Black',sans-serif;font-size:46px;background:linear-gradient(180deg,#e6edf7 0%,#00ff88 90%);-webkit-background-clip:text;background-clip:text;color:transparent}
.buy{display:block;text-align:center;background:var(--green);color:var(--deep);font-weight:700;border-radius:16px;padding:17px;font-size:16px;box-shadow:inset 0 1px 0 rgba(230,237,247,.45),0 0 28px rgba(0,255,136,.4)}
.cancel{display:block;text-align:center;margin-top:12px;color:var(--dim2);font-weight:700;font-size:12.5px;cursor:pointer}
.about{color:var(--dim);line-height:1.6;font-size:12.5px;margin-top:14px}
.kv{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:14px}
.kv div{background:var(--deep);border:1px solid var(--line2);border-radius:14px;padding:11px 13px;min-width:0}.kv b{display:block;font-size:14px;margin-top:5px;color:var(--text);white-space:nowrap}.kv b.d{color:var(--dim)}.kv i{display:block;font-style:normal;font-size:10px;color:var(--dim2);margin-top:3px}
.split{margin-top:14px}.srow{display:grid;grid-template-columns:56px 1fr 40px;gap:10px;align-items:center;margin-top:9px;font-size:12px}
.srow .bar{height:7px;border-radius:99px;background:var(--line3);overflow:hidden}.srow .bar b{display:block;height:100%;background:linear-gradient(90deg,var(--cyan),var(--green))}
.links{display:grid;grid-template-columns:repeat(3,1fr);gap:8px;margin-top:16px}
.btn{display:inline-flex;align-items:center;justify-content:center;border:1px solid var(--line3);background:var(--navy2);color:var(--dim);border-radius:12px;padding:12px 0;font-size:12px;font-weight:700}
@media (max-height:700px){.title{font-size:18px}.figs .v{font-size:min(40px,11vw)}.plot{top:96px;bottom:72px}.act{height:52px}.sent{padding:8px 12px 6px}.tier{height:36px}}
/* opened on a computer: the phone, 390 x 844, in the middle of the window */
@media (min-width:600px){html{height:auto;overflow:auto;background:#06090f}
 body{width:390px;height:844px;margin:24px auto;border:1px solid var(--line3);border-radius:34px;overflow:hidden}}
"""

JS = """
const deck = document.querySelector('.deck');
const byKey = {};
document.querySelectorAll('.card').forEach(c => byKey[c.dataset.key] = c);
const q = new URLSearchParams(location.search);
let order = ORDER.slice();
const first = q.get('c');
if (first && order.includes(first)) while (order[0] !== first) order.push(order.shift());
const scrim = document.querySelector('.scrim');

function layout() {
  order.forEach((k, i) => {
    const el = byKey[k];
    el.classList.remove('a', 'b1', 'b2', 'drag-right');
    el.style.transform = ''; el.style.opacity = '';
    el.classList.add(i === 0 ? 'a' : i === 1 ? 'b1' : 'b2');
    el.style.zIndex = 10 - i;
    el.querySelectorAll('.stamp').forEach(s => s.style.opacity = 0);
  });
  const top = byKey[order[0]];
  document.body.dataset.hue = top.classList.contains('pos') ? 'pos' : top.classList.contains('neg') ? 'neg' : 'neu';
}
function openSheet(kind, key) {
  document.querySelectorAll('.sheet').forEach(s => s.classList.toggle('open', s.dataset.kind === kind && s.dataset.key === key));
  document.body.classList.add('sheets-open');
}
function closeSheets() {
  document.querySelectorAll('.sheet').forEach(s => s.classList.remove('open'));
  document.body.classList.remove('sheets-open');
}
function fly(dir, instant) {
  const el = byKey[order[0]], key = order[0];
  const w = innerWidth * 1.4;
  if (instant) el.classList.add('dragging');
  el.style.transform = dir === 'down' ? `translateY(${innerHeight}px)` : `translateX(${dir === 'right' ? w : -w}px) rotate(${dir === 'right' ? 22 : -22}deg)`;
  el.style.opacity = 0;
  const done = () => {
    el.classList.add('dragging');
    order.push(order.shift()); layout();
    requestAnimationFrame(() => requestAnimationFrame(() => el.classList.remove('dragging')));
    if (dir === 'right') openSheet('buy', key);
  };
  instant ? done() : setTimeout(done, 300);
}
document.querySelectorAll('.card').forEach(el => {
  let x0 = null, y0 = 0, dx = 0;
  const bull = el.querySelector('.stamp.bull'), skip = el.querySelector('.stamp.skip');
  el.addEventListener('pointerdown', e => {
    if (!el.classList.contains('a') || e.target.closest('.act, .info, .tog')) return;
    x0 = e.clientX; y0 = e.clientY; dx = 0; el.classList.add('dragging'); el.setPointerCapture(e.pointerId);
  });
  el.addEventListener('pointermove', e => {
    if (x0 === null) return;
    dx = e.clientX - x0;
    el.style.transform = `translateX(${dx}px) rotate(${dx * 0.055}deg)`;
    const r = Math.min(Math.abs(dx) / 110, 1);
    bull.style.opacity = dx > 20 ? r : 0; skip.style.opacity = dx < -20 ? r : 0;
    el.classList.toggle('drag-right', dx > 40);
  });
  const end = () => {
    if (x0 === null) return;
    x0 = null; el.classList.remove('dragging');
    if (Math.abs(dx) > 110) fly(dx > 0 ? 'right' : 'left');
    else { el.style.transform = ''; bull.style.opacity = 0; skip.style.opacity = 0; el.classList.remove('drag-right'); }
  };
  el.addEventListener('pointerup', end); el.addEventListener('pointercancel', end);
  el.querySelector('.info').addEventListener('click', () => openSheet('info', el.dataset.key));
  el.querySelectorAll('.act').forEach(b => b.addEventListener('click', () => {
    const d = b.dataset.do;
    if (d === 'skip') fly('left');
    else if (d === 'buy') fly('right');
    else if (d === 'watch') fly('down');
    else if (d === 'back') { order.unshift(order.pop()); layout(); }
  }));
});
scrim.addEventListener('click', closeSheets);
document.querySelectorAll('[data-close]').forEach(b => b.addEventListener('click', closeSheets));
document.querySelectorAll('.sheet').forEach(s => s.addEventListener('click', e => { if (e.target.classList.contains('grab')) closeSheets(); }));
layout();
const s = q.get('s');
if (s === 'swipe') {
  const el = byKey[order[0]];
  el.classList.add('dragging', 'drag-right');
  el.style.transform = 'translateX(96px) rotate(5.3deg)';
  el.querySelector('.stamp.bull').style.opacity = .95;
} else if (s === 'buy') { document.querySelectorAll('.card,.sheet,.scrim').forEach(e => e.style.transition = 'none'); fly('right', true); }
else if (s === 'info') { document.querySelectorAll('.sheet,.scrim').forEach(e => e.style.transition = 'none'); openSheet('info', order[0]); }
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
    order = [c["tier"] for c in CARDS]
    top = next(c for c in CARDS if c["tier"] == "warm")          # his ESTC card on top when opened
    order = [top["tier"]] + [k for k in order if k != top["tier"]]
    cards = "".join(card_html(c) for c in CARDS)
    sheets = "".join(buy_sheet(c) + info_sheet(c) for c in CARDS)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no">
<title>Event Cards on a phone</title>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=JetBrains+Mono:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>{CSS}</style></head><body>
<header class="top"><span class="lv"><i></i>LIVE</span><span class="prog">0 / {D["deck_size"]}<i><b></b></i></span></header>
<span class="menu" aria-label="Menu"><i></i></span>
<main class="deck">{cards}<div class="scrim"></div>{sheets}</main>
<script>const ORDER = {json.dumps(order)};{JS}</script></body></html>"""


def board():
    t = D["tiers"]
    lab = {c["tier"]: f'{c["tier"].upper()} · sentiment {sent(c):+.2f}'.replace("-", "−") for c in CARDS}
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Event Cards on a phone, today and new</title>
<link href="https://fonts.googleapis.com/css2?family=Archivo+Black&family=JetBrains+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>{BOARD_CSS}</style></head><body>
<h1>EVENT<b>CARDS</b> · on a phone</h1>
<div class="sub">The frame burns as hard as the news sentiment is strong (HOT from 0.7, WARM from 0.3, QUIET below), in its colour · {D["live_cards"]} live cards: {t["hot"]} hot, {t["warm"]} warm, {t["quiet"]} quiet · it never scrolls</div>
<div class="row">
<div class="ph"><div class="lab old">Today · /events (signed out)</div><img src="today-card.png" alt=""></div>
<div class="ph"><div class="lab"><b>New</b> · {lab["hot"]}</div><iframe src="index.html?c=hot"></iframe></div>
<div class="ph"><div class="lab"><b>New</b> · {lab["warm"]}</div><iframe src="index.html?c=warm"></iframe></div>
<div class="ph"><div class="lab"><b>New</b> · {lab["quiet"]}</div><iframe src="index.html?c=quiet"></iframe></div>
</div>
<div class="row">
<div class="ph"><div class="lab"><b>New</b> · swipe right</div><iframe src="index.html?s=swipe"></iframe>
 <div class="note">Right: Buy sheet opens · Left: Skip</div></div>
<div class="ph"><div class="lab"><b>New</b> · Buy sheet</div><iframe src="index.html?s=buy"></iframe>
 <div class="note">Allocation, amount, Paper | Live</div></div>
<div class="ph"><div class="lab"><b>New</b> · (i) details</div><iframe src="index.html?s=info"></iframe>
 <div class="note">Description, symbol, market cap, split, History, Share, Embed</div></div>
</div></body></html>"""


def main():
    import sys
    sys.stdout.reconfigure(encoding="utf-8")
    (HERE / "index.html").write_text(page(), encoding="utf-8")
    (HERE / "board.html").write_text(board(), encoding="utf-8")
    print("written;", ", ".join(f'{c["tier"]} {c["id"][:8]} sentiment {sent(c):+.2f} since {pct(since(c))} 1d {pct(day(c))}' for c in CARDS))


if __name__ == "__main__":
    main()
