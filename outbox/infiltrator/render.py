"""Render mockup.html (this folder) to desktop-1920.png, desktop-1440.png and phone-390.png."""
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
page = here / "mockup.html"
with sync_playwright() as p:
    browser = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    for name, w, h, mobile in (("desktop-1920", 1920, 1080, False), ("desktop-1440", 1440, 900, False),
                               ("phone-390", 390, 844, True)):
        tab = browser.new_page(viewport={"width": w, "height": h}, device_scale_factor=2 if mobile else 1,
                               is_mobile=mobile, has_touch=mobile)
        tab.goto(page.as_uri())
        tab.wait_for_load_state("networkidle")
        tab.wait_for_timeout(500)
        tab.screenshot(path=str(here / f"{name}.png"), full_page=mobile)
        tab.close()
    browser.close()
print("rendered")
