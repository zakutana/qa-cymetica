"""Build index.html and board.html (this folder): the Event Cards deck (/events) on a phone, as the
operator designed the card himself, on Cymetica's live data.

The operator, 2026-10-26. His own card (his-design.webp, three cards graded Legendary / Rare / Common) is the spec: "muj
navrh co jsem poslal byl 10/10". Round 4 kept my own composition and borrowed parts of his ("3/10"), so round 5 reproduces
his picture part for part, in his order and proportions (measured at 450 px a card, scaled to 370), and changes only:
  - what he asked: the tier names (HOT / WARM / QUIET, his diamond, star and dot), "News sentiment" for BULLISH / BEARISH
    (the under-labels in the site's own words: Negative, Neutral, Positive), no impact row (the score is gone from the
    API: 30 of 647 live cards, none since 2026-09-12; MSG-0251);
  - what the phone forces: the card never scrolls (his rule), so the description moves to his own STATS tab and the
    picture is lower; on short phones the title takes two lines;
  - what the data forces: a linked asset shows its weight in the card (real) where he drew "corr." and a change -- the
    API's association_score is 0 on 646 of 647 cards and there is no per-asset change in it; the price row is the
    card's share price and its change over the period, the row the live card fills ("$1.0683 (+4.30%)");
  - the hues: his violet and gold are forbidden by Cymetica's colour rule, which their build check enforces. The page
    therefore uses blue for his violet tier, cyan for his gold and green for his common. He saw both side by side and
    chose these ("Nech modrou, azurovou a zelenou z jejich palety", 2026-10-26), so the comparison in his hues is gone.
Round 6, after Cymetica's answer (REPLY-0222 to MSG-0251): impact was never switched off -- news cards are scored, M&A-ripple
cards are being scored now, index baskets have no headline and are never scored, and null means "not scored" (0.00 is a
scored neutral). So the impact row is back, as he drew it, and the tier is the impact score, how big the news is: HOT from
8, WARM from 6.5, QUIET below (his own picture graded Legendary 9.0, Rare 7.0, Common 4.0). DROP RATE is the share of live
cards in that tier (snapshot.py counts all of them). A card with no impact score yet reads NOT SCORED YET with its panel
empty ("—"), and a card with no source headline reads INDEX BASKET with no sentiment panel at all, its assets in the room.

On a phone it is a deck you swipe: right flies the card off and opens the Buy sheet (as the live deck does), left skips,
Back returns it, INFO / STATS switch the card's face. ?c=hot|warm|quiet picks the top card; ?s=swipe|buy|stats freezes a
moment for the pictures.
"""
from __future__ import annotations

import html
import json
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

HERE = Path(__file__).resolve().parent
D = json.loads((HERE / "event-data.json").read_text(encoding="utf-8"))
CARDS = D["cards"]
READ = datetime.fromisoformat(D["read_at"])
esc = lambda s: html.escape(str(s), quote=True)

PAPER = "$100,000.00"                       # paper balance, as the page shows it
GLYPH = {"hot": "◆", "warm": "★", "quiet": "●", "unscored": "○", "basket": "▦"}
NAME = {"hot": "HOT", "warm": "WARM", "quiet": "QUIET", "unscored": "NOT SCORED YET", "basket": "INDEX BASKET"}


def pct(v, d=2):
    return f"{'+' if v >= 0 else '−'}{abs(v):.{d}f}%"


def since(c):
    return (c["current_index"] / c["index_base"] - 1) * 100


def day(c):
    p = c["hist"]["points"]
    return (p[-1]["index"] / p[0]["index"] - 1) * 100


def share(c):
    p = c["hist"]["points"][-1]
    return p.get("share_price") or p["index"] / 100


def ago(c):
    t = datetime.fromisoformat(c.get("published_at") or c["created_at"])
    h = (READ - t).total_seconds() / 3600
    return f"{int(h / 24)}d ago" if h >= 24 else (f"{int(h)}h ago" if h >= 1 else f"{int(h * 60)}m ago")


def source(c):
    host = urlparse(c.get("source_url") or "").netloc
    return host[4:] if host.startswith("www.") else host


def structure(c):
    name = (c.get("vehicle_structure_name") or c.get("vehicle_structure") or "").replace(f' ({c.get("vehicle_structure")})', "")
    return name.replace(" - ", " · ") or "Event card"


def sent(c):
    """The news sentiment, or None: not scored (Cymetica: null is not scored, 0.00 is a scored neutral)."""
    return c.get("headline_sentiment_score")


def signed(v, d=2):
    return "—" if v is None else f"{v:+.{d}f}".replace("-", "−")


def drop_rate(t):
    return f'{D["tiers"][t] / D["live_cards"] * 100:.1f}%'


def chart(c):
    """His chart: a line and its fill, edge to edge, in the period's colour; no axis, no tag."""
    pts = c["hist"]["points"]
    xs = [datetime.fromisoformat(p["t"]).timestamp() for p in pts]
    ys = [p["index"] for p in pts]
    lo, hi = min(ys), max(ys)
    if hi - lo < 1e-9:
        lo, hi = lo - 1, hi + 1
    X = lambda t: (t - xs[0]) / (xs[-1] - xs[0]) * 100
    Y = lambda v: 14 + (hi - v) / (hi - lo) * 62
    line = " ".join(f"{X(x):.2f},{Y(y):.2f}" for x, y in zip(xs, ys))
    gid = f'g-{c["tier"]}'
    return (f'<svg class="plot" viewBox="0 0 100 100" preserveAspectRatio="none" aria-hidden="true"><defs>'
            f'<linearGradient id="{gid}" x1="0" y1="0" x2="0" y2="1"><stop offset="0" class="s0"/><stop offset="1" class="s1"/></linearGradient></defs>'
            f'<polygon points="0,100 {line} 100,100" fill="url(#{gid})"/><polyline points="{line}" class="ln"/></svg>')


ICON = {
    "back": '<path d="M14.5 6 8.5 12l6 6"/>',
    "skip": '<path d="M6 6.5v11l8-5.5zM17.5 6v12"/>',
    "watch": '<path d="M12 20s-7.5-4.6-7.5-10.1A4.3 4.3 0 0 1 12 7.1a4.3 4.3 0 0 1 7.5 2.8C19.5 15.4 12 20 12 20z"/>',
    "buy": '<path d="M3 16.5l6-6 4 4 8-8M15.5 6.5H21V12"/>',
    "sell": '<path d="M3 7.5l6 6 4-4 8 8M15.5 17.5H21V12"/>',
    "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
}


def icon(name, cls="ic"):
    return f'<svg viewBox="0 0 24 24" class="{cls}" aria-hidden="true">{ICON[name]}</svg>'


def card_html(c):
    sv, d, s, iv = sent(c), day(c), since(c), c.get("headline_impact_score")
    sd = "none" if sv is None else ("pos" if sv > 0 else ("neg" if sv < 0 else "neu"))
    arrow = {"pos": "▲", "neg": "▼", "neu": "■", "none": "■"}[sd]
    n = len(c["basket"])
    chips = "".join(f'<div class="as"><div class="a1"><b>{esc(a["symbol"])}</b><i>{esc(a.get("asset_type") or "")}</i></div>'
                    f'<div class="a2">weight {a["weight"] * 100:.0f}%</div></div>' for a in c["basket"][:3])
    more = f'<span class="sw">+{n - 3} more</span>' if n > 3 else ""
    scored = c["tier"] in ("hot", "warm", "quiet")
    dr = f'<span class="dr"><span>Drop rate</span><b>{drop_rate(c["tier"])}</b></span>' if scored else ""
    knob = "" if sv is None else f'<i class="knob" style="left:{(sv + 1) / 2 * 100:.1f}%"></i>'
    squares = "".join(f'<i class="{"on" if iv is not None and k < round(iv) else ""}"></i>' for k in range(10))
    panel = "" if c["tier"] == "basket" else (
        f'<div class="sent {sd}"><div class="sh"><span class="sl">{arrow}&nbsp;NEWS SENTIMENT</span><b>{signed(sv)}</b></div>'
        f'<div class="track">{knob}</div><div class="ticks"><span>NEGATIVE</span><span>NEUTRAL</span><span>POSITIVE</span></div>'
        f'<div class="imp"><span>IMPACT</span><div class="sq">{squares}</div><b>{"—" if iv is None else f"{iv:.1f}"}</b></div></div>')
    src = f'<span class="src">{esc(source(c))}</span>' if source(c) else ""
    sym = c.get("evcdx_symbol") or f'EVCDX-{c["basket"][0]["symbol"]}'
    cap = "— not minted yet" if not c.get("arc_coin") and not c.get("pons_coin") else "—"
    split = "".join(f'<div class="srow"><b>{esc(a["symbol"])}</b><span class="bar"><b style="width:{a["weight"] * 100:.0f}%"></b></span>'
                    f'<span>{a["weight"] * 100:.0f}%</span></div>' for a in c["basket"][:3])
    return f"""<article class="card t-{c['tier']} {'c-up' if d >= 0 else 'c-down'}" data-key="{c['tier']}">
<div class="stamp bull">BUY</div><div class="stamp skip">SKIP</div>
<div class="strip"><span class="nm"><i>{GLYPH[c['tier']]}</i>{NAME[c['tier']]}</span>{dr}</div>
<div class="tabs"><span class="tab on" data-tab="info">INFO</span><span class="tab" data-tab="stats">STATS</span><span class="live"><i></i>LIVE</span></div>
<div class="view info-view">
 <div class="art"><span class="orb"></span><span class="ago">{icon('clock', 'ic s')}{ago(c)}</span>{src}</div>
 <h1 class="title">{esc(c['title'])}</h1>
 {panel}
 <div class="la"><div class="lh"><span>LINKED ASSETS</span>{more}</div><div class="chips n{min(n, 3)}">{chips}</div></div>
 <div class="price"><div><b>${share(c):,.4f}</b><span class="{'g' if d >= 0 else 'r'}">{'▲' if d >= 0 else '▼'} {abs(d):.2f}%</span></div>
  <div class="tog"><span class="on">1d</span><span>5d</span><span>30d</span></div></div>
 <div class="chart">{chart(c)}</div>
</div>
<div class="view stats-view">
 <div class="kv">
  <div class="big"><span class="k">Since launch</span><b class="{'g' if s >= 0 else 'r'}">{pct(s)}</b><i>{c['index_base']:.0f} → {c['current_index']:.2f}</i></div>
  <div><span class="k">Card index</span><b>{c['current_index']:.2f}</b><i>base {c['index_base']:.0f}</i></div>
  <div><span class="k">Index price</span><b>${c['pw_index']:,.2f}</b><i>launch ${c['pw_base']:,.2f}</i></div>
  <div><span class="k">Symbol</span><b>{esc(sym)}</b></div>
  <div><span class="k">Market cap</span><b class="d">{cap}</b></div></div>
 <p class="about">{esc(c['summary'])}</p>
 <div class="split"><span class="k">Per-asset split · {esc(structure(c))}</span>{split}</div>
 <div class="links"><span class="btn">▲ {c.get('upvotes', 0)}</span><span class="btn">History</span><span class="btn">Share</span><span class="btn">Embed</span></div>
</div>
<nav class="actions">
 <span class="act" data-do="back">{icon('back')}<em>BACK</em></span>
 <span class="act" data-do="skip">{icon('skip')}<em>SKIP</em></span>
 <span class="act watch" data-do="watch">{icon('watch')}<em>WATCH</em></span>
 <span class="act buy" data-do="buy">{icon('buy')}<em>BUY</em><small>long the dip</small></span>
 <span class="act sell" data-do="sell">{icon('sell')}<em>SELL</em><small>ride the drop</small></span></nav>
</article>"""


def buy_sheet(c):
    return (f'<section class="sheet" data-kind="buy" data-key="{c["tier"]}"><i class="grab"></i>'
            f'<div class="sh1"><b>Buy</b><span class="d">{esc(c["title"].split(" — ")[0][:24])} · ${share(c):,.4f}</span></div>'
            '<div class="seg2"><span class="on">Paper</span><span>Live</span></div>'
            f'<div class="avail">{PAPER} available</div>'
            '<div class="pc"><span class="on">0%</span><span>25%</span><span>50%</span><span>75%</span><span>100%</span></div>'
            '<div class="amt">$0.00</div>'
            '<span class="cta">Confirm Buy</span><span class="cancel" data-close>Cancel</span></section>')


TIERS = {"hot": "59,130,246", "warm": "0,207,255", "quiet": "0,255,136",       # blue, cyan, green: the site's palette
         "unscored": "127,147,173", "basket": "127,147,173"}                     # slate: no score, no colour

CSS = """
:root{--bg:#0a0e17;--deep:#06090f;--navy:#0d1520;--navy2:#111a28;--line2:#1a2a44;--line3:#1e3050;
--text:#e6edf7;--dim:#a9b8cc;--dim2:#7f93ad;--cyan:#00cfff;--green:#00ff88;--red:#ff4444;--blue:#3b82f6;
--mono:'Space Mono',monospace;--serif:'Source Serif 4',Georgia,serif}
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
html,body{height:100%;overflow:hidden;background:var(--deep);color:var(--text);font-family:var(--mono);font-size:12px;-webkit-font-smoothing:antialiased}
body{position:relative;overscroll-behavior:none}
.g{color:var(--green)}.r{color:var(--red)}.d{color:var(--dim2)}
.k{font-size:8.5px;letter-spacing:.2em;text-transform:uppercase;color:var(--dim2);font-weight:700}
.top{position:absolute;top:0;left:0;right:0;height:52px;display:flex;align-items:center;gap:12px;padding:0 66px 0 18px;z-index:2}
.lv{display:flex;align-items:center;gap:7px;color:var(--cyan);font-size:10.5px;font-weight:700;letter-spacing:.14em}.lv i{width:7px;height:7px;border-radius:50%;background:var(--green);box-shadow:0 0 8px var(--green)}
.prog{margin-left:auto;display:flex;align-items:center;gap:8px;color:var(--dim);font-size:10.5px;font-weight:700;white-space:nowrap}
.prog i{display:block;width:60px;height:4px;border-radius:99px;background:var(--line3);overflow:hidden}.prog i b{display:block;height:100%;width:3%;background:var(--green)}
.menu{position:absolute;top:4px;right:10px;width:44px;height:44px;border-radius:50%;border:1px solid var(--line3);background:rgba(13,21,32,.92);display:grid;place-items:center;z-index:2}
.menu i{display:block;width:18px;height:2px;background:var(--cyan);border-radius:2px;box-shadow:0 -6px 0 var(--cyan),0 6px 0 var(--cyan)}

/* the deck */
.deck{position:absolute;top:54px;left:10px;right:10px;bottom:20px;z-index:1}
.card{--t:0,207,255;--ln:0,255,136;position:absolute;inset:0;display:flex;flex-direction:column;border-radius:24px;overflow:hidden;touch-action:none;user-select:none;
 border:1.5px solid rgba(var(--t),.55);
 background:linear-gradient(180deg,rgba(var(--t),.17) 0,rgba(var(--t),.06) 24%,rgba(var(--t),.02) 48%,rgba(var(--t),0) 70%),var(--bg);
 box-shadow:inset 0 1px 0 rgba(230,237,247,.10),0 22px 50px rgba(0,0,0,.6),0 26px 70px -18px rgba(var(--t),.55);
 transform-origin:50% 100%;transition:transform .32s cubic-bezier(.2,.8,.2,1),opacity .32s}
.card.c-down{--ln:255,68,68}
.card.dragging{transition:none}
.card.b1{transform:translateY(10px) scale(.955);filter:brightness(.75)}
.card.b2{transform:translateY(20px) scale(.91);filter:brightness(.55)}
.card.b2>*{visibility:hidden}
/* his strip: glyph and name in the tier's colour, the drop rate at the right */
.strip{flex:none;display:flex;align-items:center;justify-content:space-between;height:41px;padding:0 16px 0 18px;
 background:linear-gradient(180deg,rgba(var(--t),.20),rgba(var(--t),.09));border-bottom:1px solid rgba(var(--t),.16)}
.nm{display:flex;align-items:center;gap:10px;font-weight:700;font-size:11px;letter-spacing:.3em;color:rgb(var(--t))}.nm i{font-style:normal;font-size:11px;letter-spacing:0}
.dr{text-align:right;line-height:1.25}.dr span{display:block;font-size:7px;letter-spacing:.2em;text-transform:uppercase;color:var(--dim2)}.dr b{font-size:11px;color:rgb(var(--t))}
.tabs{flex:none;display:flex;align-items:center;gap:22px;height:48px;padding:0 16px 0 18px}
.tab{position:relative;font-size:11.5px;font-weight:700;letter-spacing:.16em;color:var(--dim2);padding:6px 0;cursor:pointer}
.tab.on{color:var(--cyan)}.tab.on::after{content:'';position:absolute;left:0;right:0;bottom:-3px;height:2px;border-radius:2px;background:var(--cyan)}
.live{margin-left:auto;display:inline-flex;align-items:center;gap:7px;font-size:11px;font-weight:700;letter-spacing:.16em;color:var(--green);border:1px solid rgba(0,255,136,.42);background:rgba(0,255,136,.06);border-radius:9px;padding:6px 12px}
.live i{width:6px;height:6px;border-radius:50%;background:var(--green);box-shadow:0 0 8px var(--green)}
.view{flex:1;min-height:0;display:flex;flex-direction:column}
.stats-view{display:none;padding:4px 18px 0}
.card.stats .info-view{display:none}.card.stats .stats-view{display:flex}
/* his picture: a dark hatched panel and a soft orb in the tier's colour */
.art{position:relative;flex:none;height:112px;margin:4px 18px 0;border-radius:14px;overflow:hidden;border:1px solid rgba(230,237,247,.06);
 background:repeating-linear-gradient(135deg,rgba(230,237,247,.028) 0 1px,rgba(0,0,0,0) 1px 6px),linear-gradient(180deg,rgba(13,21,32,.9),rgba(6,9,15,.9))}
.orb{position:absolute;left:62%;top:52%;width:150px;height:150px;transform:translate(-50%,-50%);border-radius:50%;filter:blur(22px);
 background:radial-gradient(circle,rgba(var(--t),.75) 0,rgba(var(--t),.35) 34%,rgba(var(--t),0) 70%)}
.ago,.src{position:absolute;z-index:2;display:inline-flex;align-items:center;gap:6px;font-size:10px;border-radius:7px;padding:4px 9px;background:rgba(6,9,15,.82);color:var(--text)}
.ago{top:10px;left:10px}.src{bottom:10px;right:10px}
.ic.s{width:11px;height:11px}
.title{flex:none;margin:14px 18px 0;font-family:var(--serif);font-weight:600;font-size:24px;line-height:1.2;letter-spacing:-.012em;color:#e6edf7;
 display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden}
/* news sentiment: his panel, his slider */
.sent{--sd:127,147,173;flex:none;margin:14px 18px 0;padding:13px 15px 11px;border-radius:14px;background:rgba(6,9,15,.5);border:1px solid rgba(230,237,247,.06)}
.sent.pos{--sd:0,255,136}.sent.neg{--sd:255,68,68}
.sent .sh{display:flex;align-items:center;justify-content:space-between}
.sent .sl{font-size:12px;font-weight:700;letter-spacing:.16em;color:rgb(var(--sd))}.sent.neu .sl{color:var(--dim)}
.sent .sh b{font-size:15px;color:var(--text)}
.track{position:relative;height:4px;margin:13px 1px 0;border-radius:99px;background:linear-gradient(90deg,#ff4444,rgba(127,147,173,.38) 50%,#00ff88)}
.knob{position:absolute;top:50%;width:15px;height:15px;transform:translate(-50%,-50%);border-radius:50%;background:#e6edf7;box-shadow:0 0 0 3px rgba(var(--sd),.45),0 0 14px rgba(var(--sd),.95)}
.ticks{display:flex;justify-content:space-between;margin-top:8px;font-size:7.5px;letter-spacing:.16em;color:var(--dim2)}
.sent.none .sl{color:var(--dim2)}.sent.none .sh b{color:var(--dim2)}.sent.none .track{opacity:.35}
/* his impact row: ten squares in the tier's colour */
.imp{display:flex;align-items:center;gap:10px;margin-top:10px;padding-top:9px;border-top:1px solid rgba(230,237,247,.06)}
.imp>span{font-size:8.5px;letter-spacing:.2em;color:var(--dim2)}
.sq{flex:1;display:flex;gap:4px}.sq i{flex:1;height:10px;border-radius:2px;background:rgba(230,237,247,.07)}
.sq i.on{background:rgb(var(--t));box-shadow:0 0 6px rgba(var(--t),.55)}
.imp b{min-width:26px;text-align:right;font-size:13px;color:rgb(var(--t))}
.t-unscored .imp b,.t-basket .imp b{color:var(--dim2)}
.t-unscored .nm,.t-basket .nm{color:var(--dim)}.t-unscored .orb,.t-basket .orb{opacity:.45}
.card.bx{transform:translateY(20px) scale(.91);visibility:hidden}
/* linked assets */
.la{flex:none;margin:13px 18px 0}
.lh{display:flex;justify-content:space-between;font-size:8.5px;letter-spacing:.2em;color:var(--dim2)}.lh .sw{letter-spacing:.06em}
.chips{display:grid;gap:9px;margin-top:8px}.chips.n1{grid-template-columns:1fr}.chips.n2{grid-template-columns:1fr 1fr}.chips.n3{grid-template-columns:1fr 1fr 1fr}
.as{border-radius:11px;padding:9px 11px;background:rgba(6,9,15,.5);border:1px solid rgba(230,237,247,.07);min-width:0}
.a1{display:flex;align-items:center;justify-content:space-between;gap:6px}.a1 b{font-size:13.5px}
.a1 i{font-style:normal;font-size:6.5px;letter-spacing:.14em;text-transform:uppercase;color:var(--dim2);border:1px solid rgba(230,237,247,.12);border-radius:4px;padding:1px 4px}
.a2{margin-top:5px;font-size:9.5px;color:var(--dim2)}
/* his price row and chart */
.price{flex:none;display:flex;align-items:center;justify-content:space-between;margin:13px 18px 0}
.price b{font-size:19px;letter-spacing:.01em}.price div>span{margin-left:8px;font-size:11px;font-weight:700}
.tog{display:flex;gap:5px}.tog span{min-width:34px;text-align:center;padding:6px 0;border-radius:7px;border:1px solid rgba(230,237,247,.08);background:rgba(6,9,15,.4);color:var(--dim2);font-size:10.5px;font-weight:700}
.tog span.on{color:var(--cyan);border-color:rgba(0,207,255,.45);background:rgba(0,207,255,.08)}
.chart{position:relative;flex:1;min-height:0;margin-top:6px}
.plot{position:absolute;inset:0;width:100%;height:100%}
.plot .s0{stop-color:rgb(var(--ln));stop-opacity:.34}.plot .s1{stop-color:rgb(var(--ln));stop-opacity:0}
.plot .ln{fill:none;stroke:rgb(var(--ln));stroke-width:1.8;stroke-linejoin:round;vector-effect:non-scaling-stroke}
/* his buttons */
.actions{flex:none;display:grid;grid-template-columns:1fr 1fr 1fr 1.62fr 1.62fr;gap:8px;padding:8px 16px 14px}
.act{display:flex;flex-direction:column;align-items:center;justify-content:center;gap:4px;height:70px;border-radius:12px;border:1px solid rgba(230,237,247,.07);
 background:rgba(17,26,40,.55);color:var(--dim);cursor:pointer;transition:transform .12s}
.act:active{transform:scale(.95)}
.act em{font-style:normal;font-size:9.5px;font-weight:700;letter-spacing:.12em}
.act small{font-size:7.5px;color:var(--dim2);letter-spacing:.02em}
.ic{width:19px;height:19px;fill:none;stroke:currentColor;stroke-width:1.9;stroke-linecap:round;stroke-linejoin:round}
.act.watch{color:var(--cyan)}
.act.buy{color:var(--green);border-color:rgba(0,255,136,.38);background:rgba(0,255,136,.07)}
.act.sell{color:var(--red);border-color:rgba(255,68,68,.38);background:rgba(255,68,68,.07)}
/* STATS: what the live STATS tab and the description hold */
.stats-view .kv{display:grid;grid-template-columns:1fr 1fr;gap:9px}
.kv div{background:rgba(6,9,15,.5);border:1px solid rgba(230,237,247,.07);border-radius:12px;padding:11px 12px;min-width:0}
.kv div.big{grid-column:1/-1}.kv div.big b{font-size:26px}
.kv b{display:block;font-size:14px;margin-top:5px;color:var(--text);white-space:nowrap}.kv b.d{color:var(--dim);font-size:12px}.kv b.g{color:var(--green)}.kv b.r{color:var(--red)}
.kv i{display:block;font-style:normal;font-size:9.5px;color:var(--dim2);margin-top:3px}
.about{margin-top:12px;color:var(--dim);font-size:11px;line-height:1.7;display:-webkit-box;-webkit-line-clamp:5;-webkit-box-orient:vertical;overflow:hidden}
.split{margin-top:12px}.srow{display:grid;grid-template-columns:52px 1fr 40px;gap:10px;align-items:center;margin-top:8px;font-size:11px}
.srow .bar{height:6px;border-radius:99px;background:var(--line3);overflow:hidden}.srow .bar b{display:block;height:100%;background:rgb(var(--t))}
.links{display:grid;grid-template-columns:.8fr 1fr 1fr 1fr;gap:7px;margin-top:12px}
.btn{display:inline-flex;align-items:center;justify-content:center;border:1px solid rgba(230,237,247,.08);background:rgba(17,26,40,.55);color:var(--dim);border-radius:10px;padding:10px 0;font-size:10.5px;font-weight:700}
/* swipe stamps (today .ec-stamp), while dragging */
.stamp{position:absolute;top:104px;z-index:4;font-family:var(--mono);font-weight:700;font-size:30px;letter-spacing:.12em;border:3px solid;border-radius:10px;padding:0 14px;opacity:0;background:rgba(6,9,15,.7);pointer-events:none}
.stamp.bull{left:24px;color:var(--green);transform:rotate(-12deg)}.stamp.skip{right:24px;color:var(--dim);transform:rotate(12deg)}
.card.a.drag-right{border-color:var(--green)}
/* the Buy sheet a right swipe or Buy opens */
.scrim{position:absolute;inset:0;background:rgba(6,9,15,.62);-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);z-index:30;opacity:0;pointer-events:none;transition:opacity .25s}
.sheet{position:absolute;left:0;right:0;bottom:0;z-index:31;background:var(--bg);border:1px solid rgba(0,207,255,.25);border-bottom:none;border-radius:24px 24px 0 0;padding:10px 18px 24px;
 box-shadow:inset 0 1px 0 rgba(230,237,247,.12),0 -20px 60px rgba(0,0,0,.6);transform:translateY(105%);transition:transform .32s cubic-bezier(.2,.8,.2,1)}
.sheets-open .scrim{opacity:1;pointer-events:auto}.sheet.open{transform:none}
.grab{display:block;width:42px;height:4px;border-radius:9px;background:var(--line3);margin:0 auto 14px}
.sh1{display:flex;align-items:baseline;justify-content:space-between;gap:10px}.sh1 b{font-family:var(--serif);font-weight:600;font-size:28px}
.seg2{display:flex;gap:4px;background:var(--deep);border:1px solid var(--line2);border-radius:12px;padding:4px;margin-top:14px}
.seg2 span{flex:1;text-align:center;padding:10px 0;border-radius:9px;color:var(--dim2);font-weight:700;font-size:11.5px}.seg2 span.on{background:var(--navy2);color:var(--cyan);box-shadow:0 0 0 1px rgba(0,207,255,.4) inset}
.avail{margin-top:12px;color:var(--cyan);font-weight:700;font-size:11.5px}
.pc{display:grid;grid-template-columns:repeat(5,1fr);gap:6px;margin-top:10px}
.pc span{text-align:center;border:1px solid var(--line3);border-radius:10px;padding:12px 0;color:var(--dim);font-weight:700;font-size:11.5px}.pc span.on{border-color:var(--cyan);color:var(--cyan)}
.amt{margin:16px 0;text-align:center;font-weight:700;font-size:40px}
.cta{display:block;text-align:center;color:var(--green);border:1px solid rgba(0,255,136,.45);background:rgba(0,255,136,.10);font-weight:700;letter-spacing:.12em;border-radius:12px;padding:16px;font-size:13px}
.cancel{display:block;text-align:center;margin-top:12px;color:var(--dim2);font-weight:700;font-size:11.5px;cursor:pointer}
@media (max-height:780px){.art{height:76px}.title{font-size:22px;-webkit-line-clamp:2}.la{margin-top:11px}.price{margin-top:11px}
 .ticks{display:none}.chips .a2{display:none}.as{padding:8px 10px}.act{height:64px}}
@media (max-height:700px){.art{height:50px}.title{font-size:20px;margin-top:10px}.sent{margin-top:10px;padding:9px 13px 8px}.track{margin-top:9px}
 .imp{margin-top:8px;padding-top:7px}.tabs{height:40px}.strip{height:36px}.act{height:56px}.act small{display:none}.la{margin-top:9px}.price{margin-top:9px}}
/* opened on a computer: the phone, 390 x 844, in the middle of the window */
@media (min-width:600px){html{height:auto;overflow:auto;background:#06090f}
 body{width:390px;height:844px;margin:24px auto;border:1px solid var(--line3);border-radius:34px;overflow:hidden}}
"""

JS = """
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
    el.classList.remove('a', 'b1', 'b2', 'bx', 'drag-right');
    el.style.transform = ''; el.style.opacity = '';
    el.classList.add(i === 0 ? 'a' : i === 1 ? 'b1' : i === 2 ? 'b2' : 'bx');
    el.style.zIndex = 10 - i;
    el.querySelectorAll('.stamp').forEach(s => s.style.opacity = 0);
  });
}
function openSheet(key) {
  document.querySelectorAll('.sheet').forEach(s => s.classList.toggle('open', s.dataset.key === key));
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
    if (dir === 'right') openSheet(key);
  };
  instant ? done() : setTimeout(done, 300);
}
document.querySelectorAll('.card').forEach(el => {
  let x0 = null, dx = 0;
  const bull = el.querySelector('.stamp.bull'), skip = el.querySelector('.stamp.skip');
  el.addEventListener('pointerdown', e => {
    if (!el.classList.contains('a') || e.target.closest('.act, .tab, .tog')) return;
    x0 = e.clientX; dx = 0; el.classList.add('dragging'); el.setPointerCapture(e.pointerId);
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
  el.querySelectorAll('.tab').forEach(t => t.addEventListener('click', () => {
    el.querySelectorAll('.tab').forEach(x => x.classList.toggle('on', x === t));
    el.classList.toggle('stats', t.dataset.tab === 'stats');
  }));
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
layout();
const s = q.get('s');
if (s === 'swipe') {
  const el = byKey[order[0]];
  el.classList.add('dragging', 'drag-right');
  el.style.transform = 'translateX(96px) rotate(5.3deg)';
  el.querySelector('.stamp.bull').style.opacity = .95;
} else if (s === 'buy') { document.querySelectorAll('.card,.sheet,.scrim').forEach(e => e.style.transition = 'none'); fly('right', true); }
else if (s === 'stats') { byKey[order[0]].querySelector('.tab[data-tab=stats]').click(); }
"""

BOARD_CSS = """
*{box-sizing:border-box;margin:0;padding:0}
body{background:#06090f;color:#e6edf7;font-family:'Space Mono',monospace;padding:28px 32px 34px;width:1702px}
h1{font-family:'Source Serif 4',serif;font-weight:600;font-size:30px}
.sub{color:#7f93ad;font-size:12px;margin-top:6px;line-height:1.6}
.lab{font-size:11px;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#a9b8cc;margin:28px 0 10px}.lab b{color:#00ff88}.lab i{font-style:normal;color:#ff4444}
.his{display:block;width:1176px;border-radius:14px}
.row{display:flex;gap:26px;align-items:flex-start}
.ph{width:390px;flex:none}
.ph iframe{display:block;width:390px;height:844px;border:1px solid #1e3050;border-radius:28px;background:#06090f}
.ph .note{color:#7f93ad;font-size:11px;margin-top:8px}
"""


# The same deck as an Artifact the operator opens on his phone (2026-10-26, "dej mi to do artifactu at si to muzu na mobilu
# otevrit a zaswipovat"): the viewer supplies the document skeleton and its own viewport meta, keeps a 16 px side gutter,
# and passes no query string, so the deck opens on his ESTC card and the five kinds are reached by swiping.
ARTIFACT_CSS = """
:root{color-scheme:dark}
.deck{left:16px;right:16px}.top{padding-left:20px}
"""


def page(artifact=False):
    order = [c["tier"] for c in CARDS]
    order = ["warm"] + [k for k in order if k != "warm"]          # his ESTC card on top when opened
    tiers = "".join(f".card.t-{k}{{--t:{v}}}" for k, v in TIERS.items())
    head = ('<title>Event Card Swipe Deck</title>\n'
            '<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Source+Serif+4:opsz,wght@8..60,600&display=swap" rel="stylesheet">\n'
            f'<style>{CSS}{tiers}{ARTIFACT_CSS if artifact else ""}</style>')
    body = f"""<header class="top"><span class="lv"><i></i>LIVE</span><span class="prog">0 / {D["deck_size"]}<i><b></b></i></span></header>
<span class="menu" aria-label="Menu"><i></i></span>
<main class="deck">{"".join(card_html(c) for c in CARDS)}<div class="scrim"></div>{"".join(buy_sheet(c) for c in CARDS)}</main>
<script>const ORDER = {json.dumps(order)};{JS}</script>"""
    if artifact:
        return head + "\n" + body + "\n"
    return (f'<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,'
            f'initial-scale=1,maximum-scale=1,user-scalable=no">\n{head}</head><body>\n{body}</body></html>')


def board():
    t = D["tiers"]
    ph = lambda q, note="": f'<div class="ph"><iframe src="index.html?{q}"></iframe>{f"<div class=note>{note}</div>" if note else ""}</div>'
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><title>Event Cards on a phone: his design, built</title>
<link href="https://fonts.googleapis.com/css2?family=Space+Mono:wght@400;700&family=Source+Serif+4:opsz,wght@8..60,600&display=swap" rel="stylesheet">
<style>{BOARD_CSS}</style></head><body>
<h1>Event Cards on a phone</h1>
<div class="sub">Tier = impact score (HOT ≥ 8, WARM ≥ 6.5, QUIET below) · {D["live_cards"]} live cards: {t["hot"]} hot, {t["warm"]} warm, {t["quiet"]} quiet, {t["unscored"]} not scored yet, {t["basket"]} index baskets · never scrolls</div>
<div class="lab">His design</div><img class="his" src="his-design.webp" alt="">
<div class="lab"><b>Built</b> · HOT · WARM · QUIET · not scored yet</div>
<div class="row">{ph("c=hot")}{ph("c=warm")}{ph("c=quiet")}{ph("c=unscored")}</div>
<div class="lab"><b>Built</b> · index basket · swipe right · Buy sheet · STATS tab</div>
<div class="row">{ph("c=basket")}{ph("s=swipe", "Right: Buy sheet opens · Left: Skip")}{ph("s=buy", "Allocation, amount, Paper | Live")}{ph("s=stats", "Since launch, index, price, symbol, market cap, description, split")}</div>
</body></html>"""


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    (HERE / "index.html").write_text(page(), encoding="utf-8")
    (HERE / "artifact.html").write_text(page(artifact=True), encoding="utf-8")
    (HERE / "board.html").write_text(board(), encoding="utf-8")
    print("written;", ", ".join(f'{c["tier"]} {c["id"][:8]} impact {c.get("headline_impact_score")} sentiment {signed(sent(c))} '
                                f'share ${share(c):.4f} 1d {pct(day(c))}' for c in CARDS))


if __name__ == "__main__":
    main()
