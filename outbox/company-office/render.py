"""Render mockup.html (this folder) to desktop-1920.png, desktop-1440.png and phone-390.png,
after a scan that refuses any colour outside the site's palette."""
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
page = here / "mockup.html"

ALLOWED = {"#0a0e17", "#06090f", "#0d1520", "#111a28", "#16233a", "#1a2a44", "#1e3050", "#0c1422", "#101b2d",
           "#e6edf7", "#a9b8cc", "#7f93ad", "#00cfff", "#00ff88", "#ff4444", "#3b82f6"}
ALLOWED_RGB = {"0,207,255", "0,255,136", "255,68,68", "6,9,15"}
src = page.read_text(encoding="utf-8")
hexes = {h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}\b", src)}
rgbs = {re.sub(r"\s", "", m) for m in re.findall(r"rgba?\(([\d\s]+,[\d\s]+,[\d\s]+),", src)}
bad = sorted(hexes - ALLOWED) + sorted(rgbs - ALLOWED_RGB)
print("colours:", sorted(hexes), sorted(rgbs))
if bad:
    raise SystemExit(f"off-palette colours: {bad}")

with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    for name, w, h, mobile in (("desktop-1920", 1920, 1080, False), ("desktop-1440", 1440, 900, False),
                               ("phone-390", 390, 844, True)):
        tab = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=2 if mobile else 1,
                               is_mobile=mobile, has_touch=mobile)
        tab.goto(page.as_uri())
        tab.wait_for_load_state("networkidle")
        tab.wait_for_timeout(600)
        over = tab.evaluate("document.documentElement.scrollWidth > window.innerWidth")
        tall = tab.evaluate("document.documentElement.scrollHeight")
        print(name, "horizontal overflow" if over else "fits", "height", tall)
        tab.screenshot(path=str(here / f"{name}.png"), full_page=mobile)
        tab.close()
    browser.close()
print("rendered")
