"""The v4 changes, laid on top of THEIR live Agent Tournaments pages (serve.py feeds this their HTML).

Nothing is redrawn: their markup, classes and CSS stay, and only what the spec changes is changed:

  * six seats at every table (cards, the big table, standings, the race), no text left that says ten;
  * an open table's pot and prizes are six buy-ins (their open cards show "when full");
  * three Live Flash tables (real USDC) that show when their header's PAPER | LIVE pill is on LIVE, and the
    join-with-a-wallet panel they open;
  * the seat owner's column on a table page (their own control-panel classes, shipped in their CSS for the owner):
    the NEXUS Tune switch for a paid plan, and the changelog saying who changed what;
  * the race with our trades drawn, touching markers merged into one with a count.

Figures that are real: everything their pages carry, our seat's bot settings, lock and trades (fixtures/owner.json,
read 2026-10-26). Figures that are invented, and marked so in request.md: the Live tables, the wallet and its record,
the Tune log rows after 20 Oct 14:05.
"""
from __future__ import annotations

import math
import re
import sys
from datetime import datetime
from pathlib import Path

import lxml.html as L

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import art  # noqa: E402
import owner  # noqa: E402

SEATS = 6
OWNER_TABLE = 15

RETEXT = [
    (re.compile(r"\b10 agents\."), "6 agents."),
    (re.compile(r"\b10 agents, 1 table"), "6 agents, 1 table"),
    (re.compile(r"\b10 AI agents"), "6 AI agents"),
    (re.compile(r"\b10 seats\b(?! left)"), "6 seats"),
    (re.compile(r"\b10th seat\b"), "6th seat"),
    (re.compile(r"\b10/10\b"), "6/6"),
    (re.compile(r"ROI of the 10 agents"), "ROI of the 6 agents"),
    (re.compile(r"\b10 SEATS LEFT"), "6 SEATS LEFT"),
    (re.compile(r"\b10 seats left"), "6 seats left"),
]


# ------------------------------------------------------------------------------------------------ small helpers

def cls(e) -> set[str]:
    return set((e.get("class") or "").split())


def has(e, name: str) -> bool:
    return name in cls(e)


def frag(markup: str):
    """The children of an HTML fragment, detached from their wrapper."""
    wrap = L.fragment_fromstring(markup, create_parent="div")
    kids = list(wrap)
    for k in kids:
        wrap.remove(k)
    return kids


def retext(root) -> None:
    for e in root.iter():
        if not isinstance(e.tag, str) or e.tag in ("script", "style"):
            continue
        for attr in ("text", "tail"):
            s = getattr(e, attr)
            if s and "10" in s:
                for rx, to in RETEXT:
                    s = rx.sub(to, s)
                setattr(e, attr, s)
        for a in ("aria-label", "title", "content"):
            v = e.get(a)
            if v and "10" in v:
                for rx, to in RETEXT:
                    v = rx.sub(to, v)
                e.set(a, v)


def money(v: float, usd: bool) -> str:
    if usd:
        return f"${v:,.0f}" if abs(v - round(v)) < 1e-9 else f"${v:,.2f}"
    return f"{v:,.0f}"


def num(s: str) -> float:
    return float(re.sub(r"[^\d.]", "", s) or 0)


# ------------------------------------------------------------------------------------------------ seats

def positions(n: int = SEATS):
    """Their ten-seat ellipse, for n seats: x = 50 + 44 sin, y = 50 - 40 cos (phones: 38 and 44)."""
    out = []
    for i in range(n):
        a = 2 * math.pi * i / n
        x, y = 50 + 44 * math.sin(a), 50 - 40 * math.cos(a)
        mx, my = 50 + 38 * math.sin(a), 50 - 44 * math.cos(a)
        c = []
        if y < 49.9:
            c.append("up")
        if x > 50.1:
            c.append("sr")
        elif x < 49.9:
            c.append("sl")
        out.append((f"--x:{x:.1f}%;--y:{y:.1f}%;--mx:{mx:.1f}%;--my:{my:.1f}%", c))
    return out


def seat_title(s) -> str | None:
    for a in s.iter():
        if isinstance(a.tag, str) and has(a, "at-ava") and a.get("title"):
            return a.get("title")
    return None


def is_filled(s) -> bool:
    return not has(s, "empty")


def reseat(tbl, keep_titles: set[str] | None = None) -> int:
    """Cut a table to six seats, keeping the leader, every member's seat and the seats named in keep_titles first,
    and lay them out round the felt. Returns how many of the six are taken."""
    seats = [c for c in tbl if isinstance(c.tag, str) and has(c, "at-seat")]

    def rank(i_s):
        i, s = i_s
        t = seat_title(s) or ""
        if keep_titles is not None:
            return (0 if t in keep_titles else 9, i)
        if has(s, "lead"):
            return (0, i)
        if is_filled(s) and not t.startswith("House "):
            return (1, i)
        return (2 if is_filled(s) else 3, i)

    order = sorted(enumerate(seats), key=rank)[:SEATS]
    keep = sorted(i for i, _ in order)
    for i, s in enumerate(seats):
        if i not in keep:
            tbl.remove(s)
    kept = [s for i, s in enumerate(seats) if i in keep]
    for s, (style, extra) in zip(kept, positions(len(kept))):
        s.set("style", style)
        s.set("class", " ".join([c for c in (s.get("class") or "").split() if c not in ("up", "sr", "sl")] + extra))
    return sum(1 for s in kept if is_filled(s))


# ------------------------------------------------------------------------------------------------ cards

def seats_left_text(k: int) -> str:
    return f"{k} seat{'' if k == 1 else 's'} left"


def card(c, six_buyins: bool) -> None:
    tbl = c.xpath('.//div[contains(@class,"at-tbl")]')
    if not tbl:
        return
    taken = reseat(tbl[0])
    left = SEATS - taken
    opened = bool(c.xpath('.//*[contains(@class,"at-st") and contains(@class,"open")]'))
    if not opened:
        return
    for e in c.xpath('.//span[contains(@class,"at-cdl") and contains(text(),"SEATS LEFT")]'):
        e.text = re.sub(r"^\d+ SEATS? LEFT", f"{left} SEAT{'' if left == 1 else 'S'} LEFT", e.text)
    for e in c.xpath('.//span[contains(@class,"who") and contains(text(),"seats left")]'):
        e.text = re.sub(r"^\d+ seats? left", seats_left_text(left), e.text)
    if six_buyins:       # an open table shows what it will pay when FULL: six buy-ins, not ten
        for v in c.xpath('.//*[@data-at-pot]'):
            usd = v.text.strip().startswith("$")
            v.text = money(num(v.text) * 0.6, usd)
        for b in c.xpath('.//div[contains(@class,"at-c3")]//b'):
            usd = (b.text or "").strip().startswith("$")
            b.text = money(num(b.text or "") * 0.6, usd)


# ------------------------------------------------------------------------------------------------ the head: the buy-in once, a small clock
# The operator, 2026-10-26, first look: the name, the buy-in chip and the kind tag said the same thing three times
# ("ET10 100 #15", "100 ET10", "ET10"). Second look: the big stopwatch was amateurish and took the corner; the length is a
# small clock under the buy-in, no FLASH word, and ET10 gets its own coin. The corner keeps their LIVE and countdown.

FLASH_TIERS = {"fmicro", "fpro"}


def dur_label(seconds: float) -> str:
    h = round(seconds / 3600)
    return f"{h}H" if h < 24 else f"{round(h / 24)}D"


def dur_pill(dur: str, status: str, start: str | None = None, end: str | None = None) -> str:
    frac = 1.0 if status == "done" else 0.0
    if status == "live" and start and end:
        a, b = datetime.fromisoformat(start), datetime.fromisoformat(end)
        frac = min(1.0, max(0.0, (datetime.now(a.tzinfo) - a) / (b - a)))
    # data-v4-*, never data-end: their page ticker rewrites the text of every [data-end] element
    data = f' data-v4-start="{start}" data-v4-end="{end}"' if (status == "live" and start and end) else ""
    return f'<span class="v4-dur is-{status}"{data} title="Runs {dur}">{art.mini_clock(frac, status == "live")}<b>{dur}</b></span>'


def buy_html(buy: str, big: bool = False) -> str:
    m = re.fullmatch(r"([\d,.]+)\s*ET10", buy.strip())
    if not m:
        return buy.strip()
    return f'{m.group(1)}{art.coin("v4-coin lg" if big else "v4-coin")}<small>ET10</small>'


def restyle_head(c, head, big: bool = False) -> None:
    """The buy-in once (ET10 with its coin), the length as a small clock under it, and the corner as they draw it:
    LIVE and the countdown, OPEN and "starts when full", DONE and the end date."""
    buy = head.xpath('.//*[contains(@class,"at-buyin")]')[0].text_content().strip()
    kinds = head.xpath('.//*[contains(@class,"at-kind")]')
    flash = bool(set((c.get("class") or "").split()) & FLASH_TIERS) or bool(c.get("data-v4-live")) or any(
        "flash" in cls(k) for k in kinds)
    corner = head.xpath('./div[contains(@class,"at-corner")]')[0]
    st = corner.xpath('./span[contains(@class,"at-st")]')[0]
    status = "live" if "live" in cls(st) else ("open" if "open" in cls(st) else "done")
    pb = corner.xpath('.//*[@data-pb]')
    start, end = (pb[0].get("data-start"), pb[0].get("data-end")) if pb else (None, None)
    runs = " ".join(corner.xpath('.//span[contains(@class,"at-cdl")]/text()'))
    m = re.search(r"RUNS (\d+) (DAY|HOUR)", runs)
    dur = (c.get("data-v4-dur") or (dur_label((datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds()) if start else None)
           or (f'{m.group(1)}{m.group(2)[0]}' if m else None) or ("1D" if flash else "7D"))
    if status == "live":
        note = L.tostring(corner.xpath('./span[contains(@class,"at-cdn")]')[0], encoding="unicode", with_tail=False)
    elif status == "open":
        note = '<span class="v4-note">starts when full</span>'
    else:
        ended = re.search(r"ENDED [\d/]+", runs)
        note = f'<span class="v4-note">{ended.group(0).lower() if ended else ""}</span>'
    st_html = L.tostring(st, encoding="unicode", with_tail=False)
    band = head.xpath('.//*[contains(@class,"v4-band")]')
    band_html = f'<span class="v4-band">{band[0].text_content()}</span>' if band else ""
    pill = dur_pill(dur, status, start, end)
    new_corner = frag(f'<div class="at-corner v4-corner">{st_html}{note}</div>')[0]
    corner.getparent().replace(corner, new_corner)
    if big:                      # the table page: the title is the buy-in, the table number and the clock beside it
        h1 = head.xpath('.//h1')[0]
        tid = re.search(r"#\d+", h1.text_content())
        for e in head.xpath('.//*[contains(@class,"at-buyin") or contains(@class,"at-kind")]'):
            e.getparent().remove(e)
        new_h1 = frag(f'<h1 class="at-rtitle v4-title"><span class="v4-buy">{buy_html(buy, True)}</span>'
                      f'<span class="v4-id">{tid.group(0) if tid else ""}</span>{pill}</h1>')[0]
        h1.getparent().replace(h1, new_h1)
        return
    old_tl = head.xpath('./div[contains(@class,"at-tl")]')[0]
    new_tl = frag(f'<div class="at-tl v4-tl"><span class="v4-buy">{buy_html(buy)}</span><div class="v4-sub">{pill}{band_html}</div></div>')[0]
    old_tl.getparent().replace(old_tl, new_tl)


def restyle_card(c) -> None:
    head = c.xpath('.//div[contains(@class,"at-thead")]')
    if head:
        restyle_head(c, head[0])


MODE_SWITCH = ('<div class="v4-mode" role="group" aria-label="Paper or Live tables">'
               '<button type="button" class="on" data-v4-mode="paper">PAPER</button>'
               '<button type="button" data-v4-mode="live"><i></i>LIVE · USDC</button></div>')


# ------------------------------------------------------------------------------------------------ Live tables

LIVE_TABLES = [  # id, name, buy-in, runs, seats taken, band; invented, and said so in request.md
    (21, "Flash 1 h", 1, "1 HOUR", 4, "ANY WALLET"),
    (22, "Flash 5 h", 1, "5 HOURS", 2, "ANY WALLET"),
    (23, "Flash 1 d", 5, "1 DAY", 3, "PROVEN"),
]
TINT = ["#7FE6FF", "#00ff88", "#66ffb8", "#93c5fd", "#3b82f6", "#00cfff"]
BOTS = "dabcef"


def live_card(tid, name, buy, runs, taken, band) -> str:
    pot = buy * SEATS
    seats = []
    for i, (style, extra) in enumerate(positions()):
        c = " ".join(["at-seat"] + ([] if i < taken else ["empty", "open"]) + extra)
        inner = (f'<span class="at-ava " style="--c:{TINT[i % len(TINT)]}"><svg viewbox="0 0 40 40" aria-hidden="true">'
                 f'<use href="#at-bot-{BOTS[i % len(BOTS)]}"></use></svg></span>' if i < taken else '<span class="at-ava"></span>')
        seats.append(f'<span class="{c}" style="{style}">{inner}</span>')
    cells = "".join(
        f'<div role="listitem"{" class=w" if k == 0 else ""}><span class="k">{p}</span><b>{money(pot * share, True)}</b></div>'
        for k, (p, share) in enumerate((("1ST", .6), ("2ND", .3), ("3RD", .1))))
    left = SEATS - taken
    return (f'<a class="at-tcard pro" href="#wallet" data-v4-live="{tid}" data-table-id="{tid}" data-v4-dur="{runs.split()[0]}{runs.split()[1][0]}">'
            f'<div class="at-thead"><div class="at-tl"><span class="at-tname">{name} #{tid}</span><div class="at-tsub">'
            f'<span class="at-buyin">${buy}</span><span class="at-kind flash" title="Real USDC">FLASH</span>'
            f'<span class="v4-band">{band}</span></div></div><div class="at-corner"><span class="at-st open">OPEN</span>'
            f'<span class="at-cdl big">starts when full</span><span class="at-cdl">{left} SEAT{"" if left == 1 else "S"} LEFT · RUNS {runs}</span></div></div>'
            f'<div class="at-tbl" aria-label="The table"><div class="at-felt"><span class="at-trk" aria-hidden="true"><i class="t">AGENT TOURNAMENTS</i>'
            f'<i class="b">BEST ROI WINS</i></span><div class="at-pot"><span class="k">PRIZE POOL · WHEN FULL</span>'
            f'<span class="v" data-at-pot>${pot}</span><span class="s">real USDC</span></div></div>{"".join(seats)}</div>'
            f'<div class="at-c3" role="list" aria-label="Prizes, 1st to 3rd">{cells}</div>'
            f'<div class="at-tfoot"><span class="who">{seats_left_text(left)}</span><span class="v cy">TAKE A SEAT</span></div></a>')


WALLET = """
<div class="v4-modal" id="atWalletV4" hidden role="dialog" aria-label="Join with a wallet"><div class="v4-modal-bg" data-v4-close></div>
<div class="at-card v4-wallet"><button class="v4-x" data-v4-close aria-label="Close">×</button>
 <span class="at-kick"><i class="at-dot"></i>Any agent can play</span>
 <h2 class="v4-h">Join with a wallet.</h2>
 <p class="v4-lead">No account. No API key. No one has to approve the seat. <b>Preview: nothing is sent.</b></p>
 <div class="v4-steps"><div class="done"><b><i>1</i>Connect</b>Sign a one-time message. Nothing is sent, no gas.</div>
  <div class="done"><b><i>2</i>Record</b>We read its swaps from the chain.</div>
  <div><b><i>3</i>Pay and sit</b>The buy-in must come from this same wallet.</div></div>
 <div class="v4-cols"><div class="at-ctl-box"><div class="at-ctl-bh"><span class="at-lbl">YOUR WALLET</span><span class="v4-chains"><b class="on">ETHEREUM</b><b>SOLANA</b></span></div>
  <div class="v4-addr"><b>0x7a3F…c91E</b><span>✓ OWNERSHIP PROVEN</span></div>
  <div class="v4-chal"><span>MESSAGE SIGNED</span>Join Flash 1 d #23 · nonce 8f3a91c2 · valid 5 min</div>
  <div class="at-lbl">ITS RECORD, READ FROM THE CHAIN · LAST 90 DAYS</div>
  <div class="at-tiles v4-rec"><div><b>214</b><span>DEX swaps</span></div><div><b>$38,420</b><span>Volume</span></div>
   <div><b class="pos">+6.4%</b><span>Realised ROI</span></div><div><b>41</b><span>Active days</span></div></div>
  <div class="v4-band-box"><b>PROVEN</b><span>Can sit at $1 and $5 tables. A wallet with no record sits at $1 tables.</span></div></div>
 <div class="at-ctl-box"><div class="at-ctl-bh"><span class="at-lbl">TABLES FOR THIS WALLET</span><span class="dim">LIVE · USDC</span></div>
  <div class="v4-trows">{rows}</div>
  <p class="v4-terms"><b>Held, not spent:</b> the buy-in is held until the table starts; leave before it starts and it returns.<br>
   <b>Paid back:</b> the prize arrives in USDC at this same wallet, and only there, when the table ends.<br>
   <b>One wallet, one seat</b> per table. Its swaps in the table's days are what it is ranked on.</p></div></div>
 <pre class="v4-api"><i>POST</i> /api/v1/agent-tournaments/join
{ "wallet": "0x7a3F…c91E", "signature": "0x…",
  "live": true, "buyin": 5, "hours": 24 }
<i>→ 200</i> { "table": 23, "seat": 4, "pay": { "usdc": 5, "from": "0x7a3F…c91E" } }</pre></div></div>
"""


def live_section() -> list:
    cards = "".join(live_card(*t) for t in LIVE_TABLES)
    rows = "".join(
        f'<div class="v4-trow"><div><b>{n} #{i}</b><em>Flash · {r.lower()} · {"any wallet" if b == 1 else "proven wallets"}</em></div>'
        f'<span>{SEATS - t}/{SEATS} left</span><span class="v4-join">Join · pay ${b}</span></div>'
        for (i, n, b, r, t, _band) in LIVE_TABLES)
    sec = (f'<div id="atLiveV4"><div class="at-sec"><h2>Open, starts when full <span class="n">{len(LIVE_TABLES)}</span></h2>{MODE_SWITCH}</div>'
           f'<p class="dim at-secnote">Real USDC. 6 paid seats, no house bots, and a table starts when it is full. '
           f'Join with a wallet: sign a message, no account and no approval. Preview: nothing here moves money.</p>'
           f'<div class="at-tables">{cards}</div></div>')
    nodes = frag(sec)
    for c in nodes[0].xpath('.//a[contains(@class,"at-tcard")]'):
        restyle_card(c)
    return nodes + frag(WALLET.replace("{rows}", rows))


# ------------------------------------------------------------------------------------------------ the race

def race(doc, kept_names: set[str]) -> None:
    sec = doc.xpath('//section[contains(@class,"at-race")]')
    if not sec:
        return
    svg = sec[0].find(".//svg")
    drop_y = []
    keep_y = []
    for pl in svg.findall("polyline"):
        title = (pl.findtext("title") or "")
        name = re.sub(r"\s[+-][\d.]+%$", "", title)
        pts = pl.get("points", "").split()
        end_y = float(pts[-1].split(",")[1]) if pts else None
        if name in kept_names:
            keep_y.append(end_y)
        else:
            svg.remove(pl)
            drop_y.append(end_y)
    for c in svg.findall("circle"):
        if c.get("r") == "3" and float(c.get("cy")) in drop_y and float(c.get("cy")) not in keep_y:
            svg.remove(c)


# ------------------------------------------------------------------------------------------------ pages

def inject(doc) -> None:
    head = doc.find("head")
    head.append(frag('<link rel="stylesheet" href="/__v4/v4.css">')[0])
    body = doc.find("body")
    body.insert(0, frag(art.SPRITE)[0])      # the gradients every v4 picture uses, once per page
    body.append(frag('<script src="/__v4/v4.js" defer></script>')[0])


def lobby(doc) -> None:
    # the table cards, and the hero's "next to fill" card (the same card)
    for c in doc.xpath('//a[contains(@class,"at-tcard") or contains(@class,"at-feat")]'):
        card(c, six_buyins=True)
    owner.install_lobby(doc)        # their signed-in hero ("Your agent") and the YOU marks on our card
    for c in doc.xpath('//a[contains(@class,"at-tcard") or contains(@class,"at-feat")]'):
        restyle_card(c)
    filters = doc.xpath('//div[@id="tables"]/div[contains(@class,"at-seg")]')
    if filters:                     # the Paper | Live switch beside their filters (one setting with their header pill)
        filters[0].addprevious(frag(MODE_SWITCH)[0])
    for kinds in doc.xpath('//div[contains(@class,"at-kinds")]'):     # the hero's three tiles, with icons, no Week
        kinds.getparent().replace(kinds, frag(art.hero_tiles())[0])
    anchor = doc.xpath('//details[contains(@class,"at-done")]')
    if anchor:
        parent = anchor[0].getparent()
        pos = parent.index(anchor[0])
        for k, e in enumerate(live_section()):
            parent.insert(pos + k, e)


def table(doc) -> None:
    rows = doc.xpath('//div[contains(@class,"at-lr")]')
    keep: list = []
    for r in rows:
        mine = not r.xpath('.//span[contains(@class,"at-h")]')
        if mine:
            keep.append(r)
    for r in rows:
        if len(keep) < SEATS and r not in keep:
            keep.append(r)
    keep = [r for r in rows if r in keep][:SEATS]
    names = set()
    for r in rows:
        if r not in keep:
            r.getparent().remove(r)
    for i, r in enumerate(keep, 1):
        nm = r.xpath('.//div[contains(@class,"nm")]/b')[0]
        full = (nm.text or "").strip()
        house = bool(r.xpath('.//span[contains(@class,"at-h")]'))
        names.add(("House " if house else "") + full)
        cell = r.xpath('./span[contains(@class,"no")]')[0]
        if not cell.xpath('.//*[contains(@class,"at-medal")]'):
            cell.text = str(i)
    for t in doc.xpath('//section[contains(@class,"at-o-tbl")]//div[contains(@class,"at-tbl")]'):
        reseat(t, keep_titles=names)
    race(doc, names)
    picks = doc.xpath('//*[@id="atPicks"]/@data-table')
    if picks and int(picks[0]) == OWNER_TABLE:
        owner.install(doc)          # the seat owner's view, in their markup
    else:
        owner.who_tags(doc)
    head = doc.xpath('//div[contains(@class,"at-rhead")]')
    if head:                        # said once, the stopwatch beside it; the strip of seven rules goes
        restyle_head(head[0], head[0], big=True)
    for strip in doc.xpath('//div[contains(@class,"at-rstrip")]'):
        strip.getparent().remove(strip)


def patch_html(page: str, html: str) -> str:
    doc = L.document_fromstring(html)
    if page == "lobby":
        lobby(doc)
    elif page == "table":
        table(doc)
    retext(doc)
    inject(doc)
    return L.tostring(doc, encoding="unicode", method="html", doctype="<!DOCTYPE html>")
