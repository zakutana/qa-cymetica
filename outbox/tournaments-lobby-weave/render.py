"""Load the live lobby (cymetica.com/agent-tournaments, GET), add lobby-weave.css, and save lobby-1440.png beside
this file -- the page exactly as they serve it, plus the patch. The fixed Nexus prompt bar is hidden for the full-page
capture only (it would otherwise be painted once mid-page)."""
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
css = (here / "lobby-weave.css").read_text(encoding="utf-8")
ALLOWED = {"#00ff88"}
ALLOWED_RGB = {"6,9,15", "0,255,136"}
hexes = {h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}\b", css)} | {"#" + h.lower() for h in re.findall(r"%23([0-9a-fA-F]{6})", css)}
rgbs = {re.sub(r"\s", "", m) for m in re.findall(r"rgba?\(([\d\s]+,[\d\s]+,[\d\s]+),", css)}
bad = sorted(hexes - ALLOWED) + sorted(rgbs - ALLOWED_RGB)
if bad:
    raise SystemExit(f"off-palette colours {bad}")
print("colours ok:", sorted(hexes))

HIDE_FIXED = """() => { for (const e of document.querySelectorAll('body *')) {
  const cs = getComputedStyle(e); const r = e.getBoundingClientRect();
  if (cs.position === 'fixed' && r.top > 300) e.style.display = 'none'; } }"""

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    for name, patched in (("lobby-before-1440", False), ("lobby-1440", True)):
        t = b.new_page(viewport={"width": 1440, "height": 900})
        t.goto("https://cymetica.com/agent-tournaments", wait_until="networkidle")
        t.wait_for_timeout(1200)
        if patched:
            t.add_style_tag(content=css)
        t.evaluate(HIDE_FIXED)
        t.wait_for_timeout(400)
        t.screenshot(path=str(here / f"{name}.png"), full_page=True)
        t.close()
    b.close()
print("rendered")
