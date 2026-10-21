"""Load the live Gem Screener (GET), add patch.css and patch.js, and save start-1440.png (Top Picks: no Hot sectors,
the top background, the new cards with the table's smileys), apps-1440.png and chains-1440.png (the Supply column),
plus the same views as served (*-before.png). Palette-scans the patch first."""
import re
from pathlib import Path

from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
css = (here / "patch.css").read_text(encoding="utf-8")
js = (here / "patch.js").read_text(encoding="utf-8")
src = css + js
ALLOWED = {"#00cfff", "#00ff88", "#ff4444", "#3b82f6", "#e6edf7", "#a9b8cc", "#7f93ad", "#1e3050", "#06090f",
           "#0d1520", "#070b13"}  # the header's near-black base, and the site navy kept for the panels
ALLOWED_RGB = {"0,207,255", "0,255,136", "255,68,68", "6,9,15"}
hexes = {h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}\b", src)} | {"#" + h.lower() for h in re.findall(r"%23([0-9a-fA-F]{6})", src)}
rgbs = {re.sub(r"\s", "", m) for m in re.findall(r"rgba?\(([\d\s]+,[\d\s]+,[\d\s]+),", src)}
bad = sorted(hexes - ALLOWED) + sorted(rgbs - ALLOWED_RGB)
if bad:
    raise SystemExit(f"off-palette colours {bad}")
print("colours ok")

HIDE_FIXED = """() => { for (const e of document.querySelectorAll('body *')) {
  if (getComputedStyle(e).position === 'fixed' && e.getBoundingClientRect().top > 300) e.style.display = 'none'; } }"""
URL = "https://cymetica.com/gem-screener/app?view="

with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])
    t = b.new_page(viewport={"width": 1440, "height": 900})
    for view in ("start", "apps", "chains"):
        # every view is loaded from Apps, so the table (and its smileys) is in the page when the patch runs
        t.goto(URL + "apps", wait_until="load", timeout=90000)
        t.wait_for_timeout(6000)
        if view != "apps":
            t.click(f'a[href*="view={view}"], [data-view="{view}"]')
            t.wait_for_timeout(2500)
        if view != "start":  # the table fills in after load; patch it only once its Supply cells exist
            t.wait_for_selector(".view.active .supcell", timeout=60000)
            t.wait_for_timeout(1500)
        t.evaluate(HIDE_FIXED)
        t.screenshot(path=str(here / f"{view}-before.png"), full_page=True)
        t.add_style_tag(content=css)
        t.wait_for_timeout(300)
        # the page re-renders its tables on live updates, which can wipe the patch's text changes: apply it, and
        # again until the active view's Supply cells carry them (a "—" left over means the table was redrawn)
        for _ in range(5):
            t.evaluate(js)
            t.wait_for_timeout(800)
            left = t.evaluate("() => [...document.querySelectorAll('.view.active .supcell .spn')]"
                              ".filter(e => e.textContent.trim() === '—').length")
            if view == "start" or left == 0:
                break
        n = t.evaluate("""() => ({cards: document.querySelectorAll('#startCards .gs-stats').length,
          smileys: document.querySelectorAll('#startCards .dc-name .nmicon').length,
          na: [...document.querySelectorAll('.supcell .spn')].filter(e => e.textContent === 'n/a').length,
          lt: [...document.querySelectorAll('.supcell .spn')].filter(e => e.textContent === '<0.1%').length,
          top: getComputedStyle(document.querySelector('.shell')).getPropertyValue('--gs-top')})""")
        print(view, n)
        t.screenshot(path=str(here / f"{view}-1440.png"), full_page=True)
    # the header's light follows the logo on wide screens: the top of Top Picks at 1920 and 2560
    for w in (1920, 2560):
        t2 = b.new_page(viewport={"width": w, "height": 900})
        t2.goto(URL + "apps", wait_until="load", timeout=90000)
        t2.wait_for_timeout(6000)
        t2.click('a[href*="view=start"], [data-view="start"]')
        t2.wait_for_timeout(2500)
        t2.evaluate(HIDE_FIXED)
        t2.add_style_tag(content=css)
        t2.evaluate(js)
        t2.wait_for_timeout(800)
        t2.screenshot(path=str(here / f"head-{w}.png"), clip={"x": 0, "y": 0, "width": w, "height": 420})
        t2.close()
    b.close()
print("rendered")
