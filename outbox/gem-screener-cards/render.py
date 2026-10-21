"""Load the live Gem Screener (GET), add cards.css and cards.js, and save cards-1440.png (the Degen pick cards),
card-1440.png (the first card alone, at 2x) and cards-before-1440.png (the same cards as served). Prints, per card,
the gate figures it found, so a figure the page does not hold shows up as a dash here and not as a guess."""
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
css = (here / "cards.css").read_text(encoding="utf-8")
js = (here / "cards.js").read_text(encoding="utf-8")
ALLOWED = {"#00ff88", "#a9b8cc", "#7f93ad", "#e6edf7"}
ALLOWED_RGB = {"0,255,136", "6,9,15"}
src = css + js
hexes = {h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}\b", src)}
rgbs = {re.sub(r"\s", "", m) for m in re.findall(r"rgba?\(([\d\s]+,[\d\s]+,[\d\s]+),", src)}
bad = sorted(hexes - ALLOWED) + sorted(rgbs - ALLOWED_RGB)
if bad:
    raise SystemExit(f"off-palette colours {bad}")
print("colours ok")

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    t = b.new_page(viewport={"width": 1440, "height": 900}, device_scale_factor=2)
    t.goto("https://cymetica.com/gem-screener/app?view=apps", wait_until="load", timeout=90000)
    t.wait_for_selector("#tbl-apps tbody tr", timeout=60000)
    # the Supply Analyzer batch arrives after the table: wait for a % in the Supply column while the Apps view is up
    t.wait_for_function("() => [...document.querySelectorAll('#tbl-apps .supcell .spn')].some(e => /%/.test(e.textContent))", timeout=90000)
    t.wait_for_timeout(2500)
    t.click('a[href*="view=start"], [data-view="start"]')
    t.wait_for_selector("#startCards .dcard", timeout=60000)
    t.wait_for_timeout(1500)
    grid = t.query_selector("#startCards")
    t.add_style_tag(content=".stickytop { position: static !important; }")
    grid.screenshot(path=str(here / "cards-before-1440.png"))
    t.add_style_tag(content=css + ' .stickytop { position: static !important; }')  # the sticky header would cover an element shot
    t.evaluate(js)
    t.wait_for_timeout(1200)
    for line in t.evaluate("""() => [...document.querySelectorAll('#startCards .dcard')].map(c => (c.querySelector('.dc-name b') || {}).textContent
        + ' | ' + [...c.querySelectorAll('.gc-row')].map(r => r.querySelector('.gc-nm').textContent + ' ' + r.querySelector('.gc-v').textContent
        + (r.querySelector('.gc-bars svg') ? ' [bars]' : '')).join(' · '))"""):
        print(line)
    t.mouse.move(2, 2)
    t.wait_for_timeout(600)
    grid.screenshot(path=str(here / "cards-1440.png"))
    t.query_selector("#startCards .dcard").screenshot(path=str(here / "card-1440.png"))
    b.close()
print("rendered")
