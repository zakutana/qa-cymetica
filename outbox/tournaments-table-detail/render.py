"""Render player.html and visitor.html (this folder) after a palette scan; report spills and seat overlaps."""
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
ALLOWED = {"#0a0e17", "#06090f", "#0d1520", "#111a28", "#16233a", "#1a2a44", "#1e3050", "#e6edf7", "#a9b8cc",
           "#7f93ad", "#00cfff", "#00ff88", "#ff4444", "#3b82f6", "#7fe6ff", "#66ffb8", "#93c5fd"}
ALLOWED_RGB = {"0,207,255", "0,255,136", "255,68,68", "13,21,32", "59,130,246"}
for name in ("player.html", "visitor.html"):
    src = (here / name).read_text(encoding="utf-8")
    hexes = {h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}\b", src)}
    rgbs = {re.sub(r"\s", "", m) for m in re.findall(r"rgba?\(([\d\s]+,[\d\s]+,[\d\s]+),", src)}
    bad = sorted(hexes - ALLOWED) + sorted(rgbs - ALLOWED_RGB)
    if bad:
        raise SystemExit(f"{name}: off-palette colours {bad}")
print("colours ok")

CHECK = """() => { const out = [];
 document.querySelectorAll('.panel, .st, .top, .tr, .rstrip div, .venue, .pickbar').forEach(c => { const cr = c.getBoundingClientRect();
  c.querySelectorAll('*').forEach(e => { const r = e.getBoundingClientRect();
   if (e.children.length === 0 && r.width && (r.right > cr.right + 1 || r.left < cr.left - 1)) out.push('past: ' + e.textContent.trim().slice(0, 30)); }); });
 const pool = document.querySelector('.big .pool > div'); const pr = pool.getBoundingClientRect();
 const boxes = [...document.querySelectorAll('.big .seat')].map(s => s.getBoundingClientRect());
 document.querySelectorAll('.big .seat .lbl, .big .seat .you').forEach(l => { const r = l.getBoundingClientRect();
  if (r.right > pr.left && r.left < pr.right && r.bottom > pr.top && r.top < pr.bottom) out.push('over pool: ' + l.textContent.trim().slice(0, 20)); });
 const lbls = [...document.querySelectorAll('.big .seat .lbl')].map(l => l.getBoundingClientRect());
 for (let i = 0; i < lbls.length; i++) for (let j = i + 1; j < lbls.length; j++) { const a = lbls[i], b = lbls[j];
  if (a.right > b.left && a.left < b.right && a.bottom > b.top && a.top < b.bottom) out.push('labels overlap ' + i + '/' + j); }
 return out.slice(0, 12); }"""

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    for page, name, w, h in (("player.html", "player-1440", 1440, 900), ("visitor.html", "visitor-1440", 1440, 900),
                             ("player.html", "player-1920", 1920, 1080)):
        tab = browser.new_page(viewport={"width": w, "height": h})
        tab.goto((here / page).as_uri())
        tab.wait_for_load_state("networkidle")
        tab.wait_for_timeout(1000)
        print(name, "wide" if tab.evaluate("document.documentElement.scrollWidth > window.innerWidth") else "fits",
              "height", tab.evaluate("document.documentElement.scrollHeight"), "problems", tab.evaluate(CHECK))
        tab.screenshot(path=str(here / f"{name}.png"), full_page=True)
        tab.close()
    browser.close()
print("rendered")
