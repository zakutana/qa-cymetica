"""Render card.html (this folder) after a scan that refuses any colour outside the site's palette and the
avatar tints their page already uses, and report anything that runs past a card or overlaps the pool."""
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
ALLOWED = {"#0a0e17", "#06090f", "#0d1520", "#111a28", "#16233a", "#1a2a44", "#1e3050", "#e6edf7", "#a9b8cc",
           "#7f93ad", "#00cfff", "#00ff88", "#ff4444", "#3b82f6", "#7fe6ff", "#66ffb8", "#93c5fd"}
ALLOWED_RGB = {"0,207,255", "0,255,136", "255,68,68", "13,21,32", "59,130,246"}
src = (here / "card.html").read_text(encoding="utf-8")
hexes = {h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}\b", src)}
rgbs = {re.sub(r"\s", "", m) for m in re.findall(r"rgba?\(([\d\s]+,[\d\s]+,[\d\s]+),", src)}
bad = sorted(hexes - ALLOWED) + sorted(rgbs - ALLOWED_RGB)
if bad:
    raise SystemExit(f"card.html: off-palette colours {bad}")
print("colours ok")

CHECK = """() => { const out = [];
 document.querySelectorAll('.kind, .podium span').forEach(c => { const cr = c.getBoundingClientRect();
  c.querySelectorAll('*').forEach(e => { const r = e.getBoundingClientRect();
   if (e.children.length === 0 && r.width && (r.right > cr.right + 1 || r.left < cr.left - 1)) out.push('past kind: ' + e.textContent.trim().slice(0, 30)); });
  if (c.scrollWidth > c.clientWidth + 1) out.push('overflow: ' + c.textContent.trim().slice(0, 30)); });
 document.querySelectorAll('.card').forEach(c => { const cr = c.getBoundingClientRect();
  c.querySelectorAll('*').forEach(e => { const r = e.getBoundingClientRect();
   if (e.children.length === 0 && r.width && (r.right > cr.right + 1 || r.left < cr.left - 1)) out.push('past card: ' + e.textContent.trim().slice(0, 30)); });
  const pool = c.querySelector('.pool > div'); if (!pool) return; const pr = pool.getBoundingClientRect();
  c.querySelectorAll('.seat').forEach(s => { const r = s.getBoundingClientRect();
   if (r.right > pr.left && r.left < pr.right && r.bottom > pr.top && r.top < pr.bottom) out.push('seat over pool in ' + c.querySelector('.name').textContent); });
  c.querySelectorAll('.you').forEach(y => { const r = y.getBoundingClientRect();
   if (r.right > pr.left && r.left < pr.right && r.bottom > pr.top && r.top < pr.bottom) out.push('YOU over pool'); }); });
 return out; }"""

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    for name, w, h in (("cards-1440", 1440, 2000), ("cards-1920", 1920, 2000)):
        tab = browser.new_page(viewport={"width": w, "height": h})
        tab.goto((here / "card.html").as_uri())
        tab.wait_for_load_state("networkidle")
        tab.wait_for_timeout(1200)
        print(name, "wide" if tab.evaluate("document.documentElement.scrollWidth > window.innerWidth") else "fits",
              "height", tab.evaluate("document.documentElement.scrollHeight"), "problems", tab.evaluate(CHECK))
        tab.screenshot(path=str(here / f"{name}.png"), full_page=True)
        tab.locator(".hero").screenshot(path=str(here / (name.replace("cards", "hero") + ".png")))
        tab.close()
    browser.close()
print("rendered")
