"""The six pictures the Build it Better request attaches and links (spec/, WebP): the form takes six at most.

1 the first screen at 1920 x 1080 (headline and face-off), 2 the catalog, 3 the request form, 4 the board, 5 the bottom
tiles, 6 the phone. Rendered through serve.py like render.py; the board's lazy pictures are loaded before each shot.
"""
import sys
import threading
from io import BytesIO
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

here = Path(__file__).resolve().parent
sys.path.insert(0, str(here))
import serve  # noqa: E402

OUT = here / "spec"
OUT.mkdir(exist_ok=True)
BOX = """(sel) => { const r = document.querySelector(sel).getBoundingClientRect(); return [r.left, r.top + scrollY, r.width, r.height]; }"""


def save(png, name, width=None):
    im = Image.open(BytesIO(png)).convert("RGB")
    if width and im.width > width:
        im = im.resize((width, round(im.height * width / im.width)), Image.LANCZOS)
    im.save(OUT / name, "WEBP", quality=82, method=6)
    print(name, im.size, (OUT / name).stat().st_size // 1024, "KB")


srv = serve.make(0)
threading.Thread(target=srv.serve_forever, daemon=True).start()
url = f"http://127.0.0.1:{srv.server_address[1]}/build-it-better"
with sync_playwright() as p:
    b = p.chromium.launch(channel="chrome", args=["--disable-lcd-text", "--font-render-hinting=none"])

    def page(w, h):
        t = b.new_page(viewport={"width": w, "height": h})
        t.goto(url)
        t.wait_for_selector("#bb-board .bb-card", timeout=20000)
        t.wait_for_selector("#bb-cat-track .cat-card img", timeout=20000)
        t.evaluate("document.querySelectorAll('#bb-board img[loading=lazy]').forEach(i => i.loading = 'eager')")
        t.wait_for_timeout(3500)
        return t

    def hide_fixed(t):   # the site's fixed bars land in the middle of a full-page cut; a section picture goes without them
        t.evaluate("""() => document.querySelectorAll('body *').forEach(e => { const s = getComputedStyle(e);
            if (s.position === 'fixed') e.style.setProperty('display', 'none', 'important'); })""")   # not sticky: How it works is
        t.wait_for_timeout(300)

    def section(t, sel, name, pad=24, top=0):
        x, y, w, h = t.evaluate(BOX, sel)
        save(t.screenshot(full_page=True, clip={"x": max(0, x - pad), "y": y - pad - top, "width": w + 2 * pad, "height": h + 2 * pad + top}), name)

    t = page(1920, 1080)
    save(t.screenshot(), "1-first-screen.webp")
    hide_fixed(t)
    section(t, ".bb-cat", "2-catalog.webp")
    t.close()

    t = page(1440, 900)
    hide_fixed(t)
    section(t, ".bb-request", "3-request.webp")
    section(t, ".bb-boardsec", "4-board.webp")
    x, y, w, h = t.evaluate(BOX, ".bb-closed")
    _, y2, _, h2 = t.evaluate(BOX, ".bb-tiles")
    save(t.screenshot(full_page=True, clip={"x": x - 24, "y": y - 24, "width": w + 48, "height": y2 + h2 - y + 24}), "5-bottom.webp")
    t.close()

    t = page(390, 844)
    hide_fixed(t)
    _, top, _, _ = t.evaluate(BOX, ".bb-top")
    x, y, w, h = t.evaluate(BOX, ".bb-vs-wrap")
    shot = t.screenshot(full_page=True, clip={"x": 0, "y": top - 10, "width": 390, "height": y + h + 30 - top + 10})
    save(shot, "6-phone.webp")
    t.close()
    b.close()
srv.shutdown()
