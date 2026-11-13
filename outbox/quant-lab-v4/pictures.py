"""The six pictures for the request, shot from the running mock (serve.py) at 1440 wide, saved as webp in pictures/.

python outbox/quant-lab-v4/serve.py --quiet   (in another shell)
python outbox/quant-lab-v4/pictures.py
"""
import io
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE / "pictures"
OUT.mkdir(exist_ok=True)
URL = "http://127.0.0.1:8811/company/app/experiments"


def save(png: bytes, name: str, max_h: int | None = None):
    im = Image.open(io.BytesIO(png)).convert("RGB")
    if max_h and im.height > max_h:
        im = im.crop((0, 0, im.width, max_h))
    im.save(OUT / f"{name}.webp", "WEBP", quality=88, method=6)
    print(name, im.size)


def stage(pg, i, wait):
    pg.evaluate("i => { const pp = document.querySelector('[data-pp]'); if (pp.classList.contains('q2-on')) pp.click(); document.querySelector('[data-st=\"' + i + '\"]').click(); }", i)
    pg.wait_for_timeout(wait)
    pg.evaluate("() => document.querySelector('[data-pp]').click()")
    pg.wait_for_timeout(300)


with sync_playwright() as p:
    b = p.chromium.launch()
    pg = b.new_page(viewport={"width": 1440, "height": 900})
    pg.goto(URL + "#runs", wait_until="load")
    pg.wait_for_timeout(5000)
    pg.evaluate("() => document.querySelector('[data-run=\"25\"]').click()")
    pg.wait_for_timeout(1200)
    stage(pg, 2, 2900)
    save(pg.screenshot(full_page=True), "picture-1-runs-winner", 1700)
    save(pg.locator("#rx").screenshot(), "picture-2-blind")
    pg.evaluate("() => location.hash = 'bots'")
    pg.wait_for_timeout(800)
    save(pg.screenshot(), "picture-3-bots")
    pg.evaluate("() => location.hash = 'ingredients'")
    pg.wait_for_timeout(800)
    save(pg.screenshot(full_page=True), "picture-4-ingredients", 1300)
    pg.click('[data-ing="immune"]')
    pg.wait_for_timeout(500)
    save(pg.screenshot(), "picture-5-ingredient-open")
    pg.keyboard.press("Escape")
    pg.evaluate("() => location.hash = 'live'")
    pg.wait_for_timeout(600)
    pg.click("[data-v4demo]")
    pg.wait_for_timeout(2500)
    save(pg.screenshot(full_page=True), "picture-6-live-search", 1300)
    b.close()
