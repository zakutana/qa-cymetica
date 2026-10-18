"""Render table.html (this folder) after a palette scan; report seat plates and chip labels that overlap."""
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
ALLOWED = {"#0a0e17", "#06090f", "#0d1520", "#111a28", "#16233a", "#1a2a44", "#1e3050", "#e6edf7", "#a9b8cc",
           "#7f93ad", "#00cfff", "#00ff88", "#ff4444", "#3b82f6", "#7fe6ff", "#66ffb8", "#93c5fd"}
ALLOWED_RGB = {"0,207,255", "0,255,136", "255,68,68", "13,21,32", "59,130,246", "6,9,15", "230,237,247"}
src = (here / "table.html").read_text(encoding="utf-8")
hexes = {h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}\b", src)}
rgbs = {re.sub(r"\s", "", m) for m in re.findall(r"rgba?\(([\d\s]+,[\d\s]+,[\d\s]+),", src)}
bad = sorted(hexes - ALLOWED) + sorted(rgbs - ALLOWED_RGB)
if bad:
    raise SystemExit(f"off-palette colours {bad}")
print("colours ok:", sorted(hexes))

CHECK = """() => { const out = [];
 const boxes = [...document.querySelectorAll('.plate, .eq, .pot, .spot, .print')].map(e => [e, e.getBoundingClientRect()]);
 for (let i = 0; i < boxes.length; i++) for (let j = i + 1; j < boxes.length; j++) { const [ea, a] = boxes[i], [eb, b] = boxes[j];
  if (ea.contains(eb) || eb.contains(ea)) continue;
  if (a.right > b.left && a.left < b.right && a.bottom > b.top && a.top < b.bottom)
   out.push('overlap: ' + ea.textContent.trim().slice(0, 18) + ' / ' + eb.textContent.trim().slice(0, 18)); }
 return out; }"""

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    for name, w, h in (("table-1440", 1440, 900), ("table-1920", 1920, 1080)):
        tab = browser.new_page(viewport={"width": w, "height": h})
        tab.goto((here / "table.html").as_uri())
        tab.wait_for_load_state("networkidle")
        tab.wait_for_timeout(800)
        print(name, "wide" if tab.evaluate("document.documentElement.scrollWidth > window.innerWidth") else "fits",
              "problems", tab.evaluate(CHECK))
        tab.screenshot(path=str(here / f"{name}.png"), full_page=True)
        tab.close()
    browser.close()
print("rendered")
