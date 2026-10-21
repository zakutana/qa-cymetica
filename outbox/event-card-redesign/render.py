"""Render index.html (this folder) at 1440 and 1920 after a palette scan; check that everything the live page holds is on the
new one (a list of what the live page shows, checked against the rendered text) and that nothing overlaps or spills."""
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
src = (here / "index.html").read_text(encoding="utf-8") + (here / "make_mockup.py").read_text(encoding="utf-8")
ALLOWED = {"#0a0e17", "#06090f", "#0d1520", "#111a28", "#16233a", "#1a2a44", "#1e3050", "#e6edf7", "#a9b8cc", "#7f93ad",
           "#00cfff", "#00ff88", "#ff4444", "#3b82f6"}
ALLOWED_RGB = {"0,207,255", "0,255,136", "255,68,68", "230,237,247", "0,0,0"}
page = (here / "index.html").read_text(encoding="utf-8")
hexes = {h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}\b", page) if not re.search(r"[0-9a-f]{20,}", h)}
rgbs = {re.sub(r"\s", "", m) for m in re.findall(r"rgba?\(([\d\s]+,[\d\s]+,[\d\s]+),", page)}
bad = sorted(h for h in hexes - ALLOWED) + sorted(rgbs - ALLOWED_RGB)
# image URLs carry hashes that look like colours; only a real #rrggbb outside a URL counts
bad = [h for h in bad if re.search(r"(?<![\w/=&?%.-])" + re.escape(h) + r"(?![0-9a-fA-F])", page, re.I) or h.startswith("#") is False]
if bad:
    raise SystemExit(f"off-palette colours {bad}")
print("colours ok")

HAS = ["SAIB: MRNA — Moderna", "coingecko.com", "published", "News sentiment", "Neutral +0.00", "Allocate from your balance",
       "Paper balance $100,000.00", "sign in", "0%", "25%", "50%", "75%", "100%", "$0.00 · 0% of available", "Buy", "Per-asset split",
       "Reset to card weights", "MRNA", "+ Add asset", "1d", "5d", "30d", "Back", "Skip", "Watch", "Sell", "History", "Share", "Embed",
       "Create", "Top", "0 / 51", "PREDICTION MARKET", "ORDER BOOK", "Market pressure", "Buying vs selling across all 51 cards",
       "BUYING", "Most buying", "Most selling", "Your positions", "P&L from your own entry price", "All positions", "Start in paper mode",
       "Up next", "My cards", "How events like this performed", "Median 30d return", "% positive", "Past events", "Asset Universe",
       "All shortcuts", "Symbol", "Market cap", "Card index", "Index price", "SAIB coin on Arc", "Single AI Index Basket", "LIVE",
       "Grounded in real same-sector past events", "Since launch", "Watchlist"]
CHECK = """() => { const out = [];
 document.querySelectorAll('.panel, .fig>div, .up, .movers div, .act, .btn, .chip, .pill').forEach(c => { const cr = c.getBoundingClientRect();
  c.querySelectorAll('*').forEach(e => { const r = e.getBoundingClientRect();
   if (e.children.length === 0 && r.width && e.tagName !== 'polyline' && (r.right > cr.right + 1 || r.left < cr.left - 1)) out.push('past: ' + e.textContent.trim().slice(0, 30)); }); });
 return out.slice(0, 12); }"""
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    for w, h in ((1440, 900), (1920, 1080)):
        t = b.new_page(viewport={"width": w, "height": h})
        t.goto((here / "index.html").as_uri())
        t.wait_for_load_state("networkidle")
        t.wait_for_timeout(1200)
        txt = t.evaluate("() => document.body.innerText")
        missing = [s for s in HAS if s.lower() not in txt.lower()]
        print(w, "wide" if t.evaluate("document.documentElement.scrollWidth > window.innerWidth") else "fits", "height",
              t.evaluate("document.documentElement.scrollHeight"), "| missing:", missing, "| problems:", t.evaluate(CHECK))
        t.screenshot(path=str(here / f"page-{w}.png"), full_page=True)
        t.close()
    b.close()
print("rendered")
