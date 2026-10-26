"""Render the phone mockup (index.html, this folder) in its four states and the board beside today's card, after a palette
scan; check that what the card carries today is on the face or on a sheet, that the card never scrolls at any phone height,
and that no text spills out of its box."""
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
ALLOWED = {"#0a0e17", "#06090f", "#0d1520", "#111a28", "#16233a", "#1a2a44", "#1e3050", "#e6edf7", "#a9b8cc", "#7f93ad",
           "#00cfff", "#00ff88", "#ff4444", "#3b82f6"}
ALLOWED_RGB = {"0,207,255", "0,255,136", "255,68,68", "230,237,247", "6,9,15", "13,21,32", "0,0,0"}
for name in ("index.html", "board.html"):
    page = (here / name).read_text(encoding="utf-8")
    hexes = {h.lower() for h in re.findall(r"(?<![\w/=&?%.-])#[0-9a-fA-F]{6}(?![0-9a-fA-F])", page)}
    rgbs = {re.sub(r"\s", "", m) for m in re.findall(r"rgba?\(([\d\s]+,[\d\s]+,[\d\s]+),", page)}
    bad = sorted(hexes - ALLOWED) + sorted(rgbs - ALLOWED_RGB)
    if bad:
        raise SystemExit(f"{name}: off-palette colours {bad}")
print("colours ok")

# everything today's card, its STATS tab and the new page hold is on the face or on one of the two sheets
FACE = ["LIVE", "CRM to acquire Braze", "Negative -0.60", "5d ago", "Since launch", "+6.83%", "1 day", "+4.30%", "1d", "5d", "30d",
        "106.83", "-$0.07", "Sell", "Buy"]
BUY = ["Buy", "Paper", "Live", "$100,000.00 available", "0%", "25%", "50%", "75%", "100%", "$0.00", "Confirm Buy", "Cancel"]
INFO = ["SAIB · Single AI Index Basket", "▲ 0", "ripple effect", "Card index", "base 100", "Index price", "$102.43", "launch $95.88",
        "Symbol", "EVCDX-ESTC", "Market cap", "not minted yet", "Per-asset split", "ESTC", "100%", "History", "Share", "Embed"]
SPILL = """() => { const out = [];
 document.querySelectorAll('.card.a .figs>div, .card.a .meta, .card.a .chip, .card.a .tog span, .card.a .act, .card.a .pill, .top, .sheet .kv>div, .sheet .pc span, .sheet .seg2 span, .sheet .btn').forEach(c => {
  if (!c.offsetParent && getComputedStyle(c).position !== 'fixed') return;
  const cr = c.getBoundingClientRect();
  c.querySelectorAll('*').forEach(e => { const r = e.getBoundingClientRect();
   if (r.width && !['polyline','path','line','circle','rect','svg','stop','linearGradient','defs','polygon'].includes(e.tagName)
       && (r.right > cr.right + 1 || r.left < cr.left - 1)) out.push(e.textContent.trim().slice(0, 30)); }); });
 const card = document.querySelector('.card.a').getBoundingClientRect();
 if (card.right > innerWidth + 1 && !document.body.classList.contains('swipe')) out.push('card wider than the screen');
 const body = document.querySelector('.card.a .body').getBoundingClientRect();
 document.querySelectorAll('.card.a .plot *').forEach(e => { const r = e.getBoundingClientRect(); if (r.width && (r.right > body.right - 8 || r.left < body.left)) out.push('chart part outside the card: ' + e.className); });
 return out.slice(0, 12); }"""
FIT = """() => { const b = document.querySelector('.card.a .body'); const t = document.querySelector('.card.a .title');
 const p = document.querySelector('.plot').getBoundingClientRect(); const sh = document.querySelector('#more').getBoundingClientRect();
 return {scrolls: b.scrollHeight - b.clientHeight, title_lines: Math.round(t.getBoundingClientRect().height / (parseFloat(getComputedStyle(t).lineHeight))),
         chart_height: Math.round(p.height)}; }"""
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    for (w, h) in ((390, 844), (360, 740), (375, 667), (360, 640)):
        t = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=2, is_mobile=True, has_touch=True)
        t.goto((here / "index.html").as_uri() + "?s=rest")
        t.wait_for_load_state("networkidle")
        t.wait_for_timeout(700)
        txt = t.evaluate("() => document.querySelector('.card.a').innerText + ' ' + document.querySelector('.top').innerText").replace("−", "-")
        fit = t.evaluate(FIT)
        missing = [x for x in FACE if x.lower() not in txt.lower()]
        print(f"{w}x{h} face | missing {missing} | spill {t.evaluate(SPILL)} | {fit}", "| SCROLLS" if fit["scrolls"] > 1 else "| no scroll")
        t.screenshot(path=str(here / f"phone-rest-{w}x{h}.png"))
        t.close()
    for s, names in (("swipe", None), ("buy", BUY), ("info", INFO)):
        t = b.new_page(viewport={"width": 390, "height": 844}, device_scale_factor=2, is_mobile=True, has_touch=True)
        t.goto((here / "index.html").as_uri() + f"?s={s}")
        t.wait_for_load_state("networkidle")
        t.wait_for_timeout(700)
        if names:
            txt = t.evaluate("() => document.querySelector('.sheet:not([style*=none])') ? [...document.querySelectorAll('.sheet')].filter(e => e.offsetParent).map(e => e.innerText).join(' ') : ''").replace("−", "-")
            top = t.evaluate("() => Math.round([...document.querySelectorAll('.sheet')].filter(e => e.offsetParent)[0].getBoundingClientRect().top)")
            print(f"390x844 {s} sheet | missing {[x for x in names if x.lower() not in txt.lower()]} | spill {t.evaluate(SPILL)} | top at {top}px")
        t.screenshot(path=str(here / f"phone-{s}-390.png"))
        t.close()
    t = b.new_page(viewport={"width": 2180, "height": 1010}, device_scale_factor=1.5)
    t.goto((here / "board.html").as_uri())
    t.wait_for_load_state("networkidle")
    t.wait_for_timeout(1500)
    t.screenshot(path=str(here / "board.png"), full_page=True)
    b.close()
print("rendered")
