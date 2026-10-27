"""Screenshots of the v3 copy (serve.py must be running on 8792), at the operator's width (2000 px): the pictures for
the spec, taken from THEIR page with the v3 changes on it.

    python outbox/promo-market-v3/live/render.py        # writes outbox/promo-market-v3/pictures/*.png

Also reports text that runs past its box, which a test cannot see and a picture can.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "pictures"
OUT.mkdir(exist_ok=True)
BASE = "http://127.0.0.1:8792"
CHECK = """(sel) => { const out = [];
 document.querySelectorAll(sel).forEach(c => { const cr = c.getBoundingClientRect(); if (!cr.width) return;
  c.querySelectorAll('*').forEach(e => { if (e.closest('svg')) return; const r = e.getBoundingClientRect();
   if (e.children.length === 0 && r.width && (r.right > cr.right + 1 || r.left < cr.left - 1)) out.push('past its box: ' + e.textContent.trim().slice(0, 40)); }); });
 return out.slice(0, 12); }"""
BOXES = ".payrow, .v3q, .v3cap, .pays > div, .v3stats > div, .v3offer, .v3n, .v3nums > div, .mat, .pick button, .buys > div"


def ready(page):
    page.wait_for_function("() => document.getElementById('boot').classList.contains('gone')", timeout=60000)
    page.wait_for_timeout(700)
    page.wait_for_function("() => [...document.images].every(i => i.complete)", timeout=30000)


def main():
    bad = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 2000, "height": 1300})

        def at(url, name, full=False):
            page.goto(BASE + url); ready(page)
            page.screenshot(path=str(OUT / f"{name}.png"), full_page=full)
            bad.extend((name, x) for x in page.evaluate(CHECK, BOXES))

        at("/expire76#new", "1-post-a-brief")
        page.click("[data-pick='__site']"); page.wait_for_timeout(300)
        page.fill("#v3sn", "Ironstar Shop"); page.fill("#v3su", "https://example.com/shop"); page.wait_for_timeout(300)
        page.screenshot(path=str(OUT / "2-own-website.png"))
        at("/expire76?v2#mybrief/9001", "3-brief-page-v2-now", full=True)
        at("/expire76#mybrief/9001", "4-brief-page-v3", full=True)
        at("/promo-market", "5-market-v3", full=True)
        page.click("article[data-brief='9001'] .btn.g"); page.wait_for_timeout(500)
        page.screenshot(path=str(OUT / "6-promoter-asks.png"))
        page.fill("#v3xh", "gemhunter_demo"); page.click("[data-v3check]"); page.wait_for_timeout(700)
        page.screenshot(path=str(OUT / "7-promoter-offer.png"))
        page.click("[data-v3change]"); page.wait_for_timeout(300)
        page.fill("#v3xh", "moonfarm_demo"); page.click("[data-v3check]"); page.wait_for_timeout(700)
        page.screenshot(path=str(OUT / "8-promoter-refused.png"))
        at("/promo-market?v2", "9-market-v2-now", full=True)
        b.close()
    for where, what in bad:
        print(f"{where}: {what}")
    print(f"pictures in {OUT}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
