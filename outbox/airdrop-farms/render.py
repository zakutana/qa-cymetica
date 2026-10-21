"""Render mock.html into the numbered pictures of the Build it Better request (1-build-it-better/), after a palette
scan of the mock: only the site's colours (cyan, green, red, blue, the navy and slate text tones)."""
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
out = here / "1-build-it-better"
out.mkdir(exist_ok=True)
src = (here / "mock.html").read_text(encoding="utf-8")
ALLOWED = {"#00cfff", "#00ff88", "#ff4444", "#3b82f6", "#e6edf7", "#a9b8cc", "#7f93ad", "#1e3050", "#06090f",
           "#0d1520", "#0a0e17"}
ALLOWED_RGB = {"0,207,255", "0,255,136", "255,68,68", "59,130,246", "6,9,15", "13,21,32", "30,48,80", "10,14,23",
               "127,147,173"}
hexes = {h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}\b", src)}
rgbs = {re.sub(r"\s", "", m) for m in re.findall(r"rgba?\(([\d\s]+,[\d\s]+,[\d\s]+),", src)}
bad = sorted(hexes - ALLOWED) + sorted(rgbs - ALLOWED_RGB)
if bad:
    raise SystemExit(f"off-palette colours {bad}")
print("colours ok:", " ".join(sorted(hexes)))

url = (here / "mock.html").as_uri()
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    for w in [int(a) for a in sys.argv[1:]] or [1440]:
        t = b.new_page(viewport={"width": w, "height": 900}, device_scale_factor=1)
        t.goto(url + "?tab=farms", wait_until="networkidle")
        t.wait_for_timeout(800)
        over = t.evaluate("() => document.documentElement.scrollWidth - innerWidth")
        print(w, "horizontal overflow px:", over)
        t.screenshot(path=str(out / f"1-farms-{w}.png"), full_page=True)
        if w == 1440:
            box = t.evaluate("""() => { const a = document.querySelector('.thead').getBoundingClientRect(),
                c = document.querySelector('.sim').getBoundingClientRect();
                return {x: a.left - 1, y: a.top + scrollY - 1, width: a.width + 2, height: c.bottom - a.top + 2}; }""")
            t.screenshot(path=str(out / "2-farm-simulator-closeup.png"), clip=box, full_page=True)
            t.goto(url + "?tab=live", wait_until="networkidle")
            t.wait_for_timeout(800)
            t.screenshot(path=str(out / "3-live-farms-1440.png"), full_page=True)
            t.goto(url + "?tab=logo", wait_until="networkidle")
            t.wait_for_timeout(500)
            h = t.evaluate("() => document.querySelector('.sheet').getBoundingClientRect().bottom")
            t.screenshot(path=str(out / "4-logo.png"), clip={"x": 220, "y": 0, "width": 1000, "height": h})
        t.close()
    b.close()
print("rendered")
