"""Load the live Gem Screener (GET), add tiers.css and tiers.js, and save: tiers-1440.png and tiers-1920.png (the section
with a little of the page around it), tiers-panel-1440.png (an icon clicked: the same side panel the Apps table opens) and
tiers-top-1440.png (Top Picks from the Altseason panel down to the first Degen pick cards). Prints the tier counts and
whether the click opened the panel. Palette-scans the patch first."""
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
css = (here / "tiers.css").read_text(encoding="utf-8")
js = (here / "tiers.js").read_text(encoding="utf-8")
ALLOWED = {"#00cfff", "#00ff88", "#3b82f6", "#7f93ad", "#a9b8cc", "#e6edf7", "#1e3050", "#1a2a44", "#06090f", "#0d1520"}
ALLOWED_RGB = {"0,207,255", "0,255,136", "59,130,246", "127,147,173", "6,9,15", "230,237,247"}
src = css + js
hexes = {h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}\b", src)}
rgbs = {re.sub(r"\s", "", m) for m in re.findall(r"rgba?\(([\d\s]+,[\d\s]+,[\d\s]+),", src)}
bad = sorted(hexes - ALLOWED) + sorted(rgbs - ALLOWED_RGB)
if bad:
    raise SystemExit(f"off-palette colours {bad}")
print("colours ok")

HIDE_FIXED = """() => { for (const e of document.querySelectorAll('body *')) {
  if (getComputedStyle(e).position === 'fixed' && e.getBoundingClientRect().top > 300 && !e.closest('aside.panel')) e.style.display = 'none'; } }"""
COUNTS = """() => ({tiers: [...document.querySelectorAll('.gt-row')].map(r => r.className.replace('gt-row gt-', '') + ':' + r.querySelectorAll('.gt-app').length
   + (r.querySelector('.gt-more') ? '+' + r.querySelector('.gt-more').textContent : '')).join('  '),
   total: document.querySelectorAll('.gt-app').length, rows: document.querySelectorAll('#tbl-apps tbody tr').length,
   dupes: (() => { const ids = [...document.querySelectorAll('.gt-app')].map(b => b.dataset.id); return ids.length - new Set(ids).size; })()})"""

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    for w in (1440, 1920):
        t = b.new_page(viewport={"width": w, "height": 900})
        t.goto("https://cymetica.com/gem-screener/app?view=apps", wait_until="load", timeout=90000)
        t.wait_for_selector("#tbl-apps tbody tr", timeout=60000)
        t.wait_for_timeout(4000)
        t.click('a[href*="view=start"], [data-view="start"]')
        t.wait_for_selector("#startCards .dcard", timeout=60000)
        t.wait_for_timeout(1500)
        t.add_style_tag(content=css + ' main.measure::before { display: none !important; }')  # their top mesh, which a separate request removes, is hidden so these pictures show the tier list alone
        t.evaluate(js)
        t.wait_for_timeout(1500)
        t.evaluate(HIDE_FIXED)
        print(w, t.evaluate(COUNTS))
        sec = t.query_selector(".gt-wrap")
        box = sec.bounding_box()
        t.screenshot(path=str(here / f"tiers-{w}.png"), full_page=True,
                     clip={"x": 0, "y": box["y"] - 24, "width": w, "height": box["height"] + 48})
        if w == 1440:
            h3 = t.query_selector("#view-start .altpanel").bounding_box()
            t.screenshot(path=str(here / "tiers-top-1440.png"), full_page=True,
                         clip={"x": 0, "y": h3["y"] - 8, "width": w, "height": box["y"] + box["height"] + 620 - h3["y"]})
            # a click on an icon: the side panel opens, as it does from a row of the Apps table
            first = t.query_selector(".gt-s .gt-app")
            name = first.get_attribute("data-tipb")
            t.evaluate("() => document.querySelector('.gt-wrap').scrollIntoView({block: 'center'})")
            first.click()
            t.wait_for_timeout(2500)
            opened = t.evaluate("() => { const p = document.querySelector('aside.panel'); return !!p && p.getBoundingClientRect().width > 200 && p.getBoundingClientRect().left < innerWidth - 200; }")
            title = t.evaluate("() => (document.querySelector('aside.panel') || {}).innerText ? document.querySelector('aside.panel').innerText.slice(0, 60).replace(/\\s+/g, ' ') : null")
            print("clicked", name, "-> panel opened:", opened, "|", title)
            t.screenshot(path=str(here / "tiers-panel-1440.png"))
        t.close()
    b.close()
print("rendered")
