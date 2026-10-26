"""Render the phone mockup (index.html, this folder) in its three states and the board beside today's card, after a palette
scan; check that what the card carries today is on the new one and that no text spills out of its box."""
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

# what today's phone card shows (INFO and STATS), each still somewhere on the new card
HAS = ["LIVE", "FEATURED", "SAIB · Single AI Index Basket", "CRM to acquire Braze", "streetinsider.com", "Sentiment -0.60",
       "Since launch", "Card index", "1 day", "Index price", "$102.43", "106.83", "1d", "5d", "30d",
       "Allocate from your balance", "Live buying power", "0%", "25%", "50%", "75%", "100%", "$0.00 · 0% of available", "Buy",
       "Per-asset split", "Reset to card weights", "ESTC", "+ Add asset", "About this card", "ripple effect", "Symbol", "EVCDX-ESTC",
       "Market cap", "not minted yet", "History", "Share", "Embed", "▲ 0", "Back", "Skip", "Watch", "Sell", "0 / 50", "-$0.07"]
SPILL = """() => { const out = [];
 document.querySelectorAll('.card.a .tiles>div, .card.a .hero1, .card.a .kv div, .card.a .act, .card.a .pill, .card.a .chip, .card.a .row1, .card.a .meta, .card.a .pc span, .card.a .srow, .top').forEach(c => {
  const cr = c.getBoundingClientRect();
  c.querySelectorAll('*').forEach(e => { const r = e.getBoundingClientRect();
   if (r.width && !['polyline','path','line','circle','rect','text','g','polygon','svg','stop','linearGradient','defs'].includes(e.tagName)
       && (r.right > cr.right + 1 || r.left < cr.left - 1)) out.push(e.textContent.trim().slice(0, 30)); }); });
 const card = document.querySelector('.card.a').getBoundingClientRect();
 if (card.right > innerWidth + 1) out.push('card wider than the screen');
 return out.slice(0, 12); }"""
FOLD = """() => { const b = document.querySelector('.card.a .body').getBoundingClientRect();
 const at = s => { const e = document.querySelector(s); return e ? Math.round(e.getBoundingClientRect().bottom - b.bottom) : null; };
 return {chart_bottom_below_fold: at('.card.a .chart'), tiles_bottom_below_fold: at('.card.a .tiles'),
         title_lines: Math.round(document.querySelector('.card.a .title').getBoundingClientRect().height / 25.6),
         actions_top: Math.round(document.querySelector('.card.a .actions').getBoundingClientRect().top)}; }"""
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    for (w, h), states in (((390, 844), ("rest", "swipe", "scroll")), ((360, 740), ("rest",))):
        for s in states:
            t = b.new_page(viewport={"width": w, "height": h}, device_scale_factor=2, is_mobile=True, has_touch=True)
            t.goto((here / "index.html").as_uri() + f"?s={s}")
            t.wait_for_load_state("networkidle")
            t.wait_for_timeout(900)
            if s == "rest":
                txt = t.evaluate("""() => { const b = document.querySelector('.card.a'); return b.innerText + ' ' + document.querySelector('.top').innerText; }""")
                missing = [x for x in HAS if x.lower() not in txt.replace("−", "-").lower()]
                print(w, h, "| missing:", missing, "| spill:", t.evaluate(SPILL), "|", t.evaluate(FOLD))
            t.screenshot(path=str(here / f"phone-{s}-{w}.png"))
            t.close()
    t = b.new_page(viewport={"width": 1708, "height": 1010}, device_scale_factor=2)
    t.goto((here / "board.html").as_uri())
    t.wait_for_load_state("networkidle")
    t.wait_for_timeout(1500)
    t.screenshot(path=str(here / "board.png"), full_page=True)
    b.close()
print("rendered")
