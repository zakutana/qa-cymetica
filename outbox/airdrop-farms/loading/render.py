"""Render the loading screen (index.html) into pictures/: three frozen moments of the work (?shot=1&p=N) at 1440,
after a colour scan that refuses any hue outside the site's cyan-to-green family and its navy and slate tones
(no orange, purple or gold)."""
import colorsys
import re
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
out = here / "pictures"
out.mkdir(exist_ok=True)
src = (here / "index.html").read_text(encoding="utf-8")

bad = []
for h in {h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}\b", src)}:
    r, g, b = (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))
    hue, light, sat = colorsys.rgb_to_hls(r, g, b)
    if sat > 0.25 and light < 0.95 and not (0.38 <= hue <= 0.62):   # 137-223 deg: green, aqua, cyan, sky
        bad.append(h)
if bad:
    raise SystemExit(f"off-palette colours {sorted(bad)}")
print("colours ok")

url = (here / "index.html").as_uri()
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    errors = []
    for w in [int(a) for a in sys.argv[1:]] or [1440]:
        t = b.new_page(viewport={"width": w, "height": 900}, device_scale_factor=1)
        t.on("pageerror", lambda e: errors.append(str(e)))
        for n, pct in enumerate((12, 55, 100), 1):
            t.goto(f"{url}?shot=1&p={pct}", wait_until="networkidle")
            t.wait_for_timeout(1200)
            t.screenshot(path=str(out / f"{n}-loading-{pct}-{w}.png"))
        print(w, "overflow px:", t.evaluate("() => document.documentElement.scrollWidth - innerWidth"))
    b.close()
print("page errors:", errors or "none")
