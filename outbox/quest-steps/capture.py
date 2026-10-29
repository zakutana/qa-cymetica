"""The real pictures for the Quest steps page, into pics/ as webp (the page loads these; kept in git, small).

Live: Cymetica's own pages, read anonymously (GET, no cookies, no key), each clipped to the part that shows the step and
none of the site header or the counters that read zero today (an empty market on a page that sells it argues with it).
Mock: the leaderboard with the monthly ET10 prizes exists only in our Universe mock (outbox/company-live, ?season0),
served here from the folder, so the page's prize and the picture's prize are the same figures (uv-data.js CO.SEASON).

    python outbox/quest-steps/capture.py              # every shot
    python outbox/quest-steps/capture.py casino promo # some

Chrome with a real GPU (the Universe is WebGPU; swiftshader draws it far too slowly), as outbox/quest/render.py does.
Prints where the hotspot controls landed in each picture (fractions), for QUEST.spots in quest.js.
"""
import functools
import http.server
import io
import socket
import sys
import threading
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
MOCK = HERE.parent / 'company-live'
OUT = HERE / 'pics'
SCALE = 2

# name: address ('mock:' = the Universe mock), viewport, settle seconds, clip (css px: x, y, w, h; None = the viewport),
# the control a hotspot points at (its text), and whether to open the mock's full leaderboard first
SHOTS = {
    'universe': dict(url='https://cymetica.com/company/app#universe', vp=(1600, 1000), wait=16,
                     clip=(540, 40, 1060, 690), spot='Start a company'),
    'season': dict(url='mock:index.html?season0#universe', vp=(1600, 900), wait=16, clip=(0, 96, 1600, 804)),
    'leaderboard': dict(url='mock:index.html?season0#universe', vp=(1600, 900), wait=16, board=True, clip=(300, 54, 1000, 744)),
    'bib': dict(url='https://cymetica.com/build-it-better', vp=(1600, 1000), wait=6, clip=(180, 206, 1240, 396), spot='Name your app'),
    'casino': dict(url='https://cymetica.com/agent-casino', vp=(1600, 1400), wait=8, clip=(880, 408, 530, 650)),
    'promo': dict(url='https://cymetica.com/promo-market', vp=(1600, 1000), wait=8, clip=(120, 86, 1360, 392), spot='Promote my product'),
    'promo-steps': dict(url='https://cymetica.com/promo-market', vp=(1600, 1000), wait=8, clip=(120, 612, 1360, 120)),
}

HIDE_MOCK_BAR = """() => { for (const e of document.querySelectorAll('body *')) {
  if (e.childElementCount && /^\\s*MOCKUP/.test(e.textContent) && e.getBoundingClientRect().width < 400) { e.style.visibility = 'hidden'; } } }"""


def serve():
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    server = http.server.ThreadingHTTPServer(('127.0.0.1', port), functools.partial(Quiet, directory=str(MOCK)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f'http://127.0.0.1:{port}/'


def main(names):
    OUT.mkdir(exist_ok=True)
    base = serve()
    with sync_playwright() as p:
        b = p.chromium.launch(channel='chrome', args=['--enable-unsafe-webgpu', '--use-angle=d3d11', '--ignore-gpu-blocklist'])
        for name in names:
            s = SHOTS[name]
            ctx = b.new_context(viewport={'width': s['vp'][0], 'height': s['vp'][1]}, device_scale_factor=SCALE)
            page = ctx.new_page()
            url = base + s['url'][5:] if s['url'].startswith('mock:') else s['url']
            page.goto(url, wait_until='domcontentloaded', timeout=60000)
            time.sleep(s['wait'])
            if s['url'].startswith('mock:'):
                page.evaluate(HIDE_MOCK_BAR)
            if s.get('board'):
                page.click('#uv-board [data-a="board-all"]')
                time.sleep(2.5)
            x, y, w, h = s['clip']
            png = page.screenshot(clip={'x': x, 'y': y, 'width': w, 'height': h})
            img = Image.open(io.BytesIO(png)).convert('RGB')
            img.save(OUT / f'{name}.webp', quality=86, method=6)
            line = f'{name}.webp {img.width}x{img.height} {(OUT / f"{name}.webp").stat().st_size // 1024} KB'
            if s.get('spot'):
                # the control itself (the clickable ancestor of its text), as fractions of the picture: x, y, w, h
                el = page.get_by_text(s['spot'], exact=False).first
                r = el.evaluate("e => { const c = e.closest('a,button') || e, b = c.getBoundingClientRect(); return [b.x, b.y, b.width, b.height]; }")
                box = [(r[0] - x) / w, (r[1] - y) / h, r[2] / w, r[3] / h]
                line += f"  spot '{s['spot']}' box [{', '.join(f'{v:.4f}' for v in box)}]"
            print(line)
            ctx.close()
        b.close()


if __name__ == '__main__':
    main(sys.argv[1:] or list(SHOTS))
