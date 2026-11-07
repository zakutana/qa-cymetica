"""Screenshots of the v4 copy (serve.py must be running), at the operator's width (2000 px): the pictures for the spec,
taken from THEIR page with the v4 changes on it, from both sides of the workflow.

    python outbox/promo-market-v4/live/render.py        # writes outbox/promo-market-v4/pictures/*.png

Also reports text that runs past its box, which a test cannot see and a picture can.
"""
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "pictures"
OUT.mkdir(exist_ok=True)
OWNER, PROMOTER = "http://127.0.0.1:8792/expire76", "http://127.0.0.1:8808/promoter"
CHECK = """(sel) => { const out = [];
 document.querySelectorAll(sel).forEach(c => { const cr = c.getBoundingClientRect(); if (!cr.width) return;
  c.querySelectorAll('*').forEach(e => { if (e.closest('svg')) return; const r = e.getBoundingClientRect();
   if (e.children.length === 0 && r.width && (r.right > cr.right + 1 || r.left < cr.left - 1)) out.push('past its box: ' + e.textContent.trim().slice(0, 40)); }); });
 return out.slice(0, 12); }"""
BOXES = ".payrow, .pays > div, .v3s4 > div, .mat, .pick button, .v3ob, .tiles .tile, .v4steps span, .v3tbl td"


def ready(page):
    page.wait_for_function("() => document.getElementById('boot').classList.contains('gone')", timeout=60000)
    page.wait_for_timeout(700)
    page.wait_for_function("() => [...document.images].every(i => i.complete)", timeout=30000)


def main():
    bad = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        page = b.new_page(viewport={"width": 2000, "height": 1300})

        def seed(stage, skip=0):
            page.request.post(OWNER.rsplit("/", 1)[0] + "/__v4/seed", data={"stage": stage})
            if skip:
                page.request.post(OWNER.rsplit("/", 1)[0] + "/__v4/skip", data={"days": skip})

        def shot(path, **kw):
            page.evaluate("() => { const b = document.getElementById('v4bar'); if (b) b.style.display = 'none'; }")   # the mock's own bar is not in a picture
            page.screenshot(path=str(path), **kw)

        def at(url, name, full=False):
            page.goto("about:blank")      # a change of the hash alone would not reload the page and its reads
            page.goto(url); ready(page)
            shot(OUT / f"{name}.png", full_page=full)
            bad.extend((name, x) for x in page.evaluate(CHECK, BOXES))

        def drawer(name, hash_="#brief/9001"):
            page.goto("about:blank")      # the same address with the same hash would not reload, and show the last state
            page.goto(PROMOTER + hash_); ready(page); page.wait_for_selector(".v3ob", timeout=15000); page.wait_for_timeout(400)
            shot(OUT / f"{name}.png")
            bad.extend((name, x) for x in page.evaluate(CHECK, BOXES))

        page.request.post(OWNER.rsplit("/", 1)[0] + "/__v4/reset")
        # the owner posts a brief
        at(OWNER + "#new", "1-post-a-brief")
        page.click("[data-v4cur='ET10']"); page.wait_for_timeout(300)
        shot(OUT / "1b-post-a-brief-et10.png")
        # the market, and the promoter's side of the brief
        seed("open")
        at(PROMOTER + "#market", "2-market", full=True)
        page.goto(PROMOTER + "#brief/9001"); ready(page); page.wait_for_selector("#v4h", timeout=15000)
        shot(OUT / "3-promoter-checks-x.png")
        page.fill("#v4h", "gemhunter_demo"); page.click("[data-v4check]"); page.wait_for_selector("#v4ask", timeout=15000); page.wait_for_timeout(300)
        shot(OUT / "4-promoter-offers.png")
        page.click("[data-v4again]") if page.query_selector("[data-v4again]") else None
        # the owner answers
        at(OWNER + "#mybrief/9001", "5-owner-offers", full=True)
        # the promoter is offered another amount
        seed("countered")
        drawer("6-promoter-countered")
        at(OWNER + "#mybrief/9001", "7-owner-waits-for-them", full=True)
        seed("approved"); drawer("8-promoter-agreed")
        seed("posted"); drawer("9-promoter-posted")
        seed("paid", 0); at(PROMOTER + "#me/taken", "10-briefs-i-took")
        seed("posted", 3)
        at(OWNER + "#mybrief/9001", "11-owner-ready-to-pay", full=True)
        page.click("[data-v4pay]"); page.wait_for_timeout(400)
        shot(OUT / "12-owner-confirms-pay.png", full_page=True)
        at(OWNER + "#me/products", "13-my-products", full=True)
        seed("cancelled")      # an ended brief: the budget never left the owner's wallet, so it does not say "left"
        at(OWNER + "#mybrief/9001", "14-ended-brief", full=True)
        at(OWNER + "#me/products", "15-my-products-ended", full=True)
        seed("open")
        b.close()
    for where, what in bad:
        print(f"{where}: {what}")
    print(f"pictures in {OUT}")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
