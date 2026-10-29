"""The pictures for the Quest steps page, into pics/ (the page loads these).

Third take (the operator, 2026-10-29): the first take's layout, and in every step a picture and beside it a piece of
Cymetica's own web, shown as a hologram in the dark, never in a rectangle ("v kazdem kroku nejaky zaber z webu nejak
huste holograficky zobrazeny ... a k tomu zaroven vzdy ten obrazek"). Nowhere the orbit with its companies.

  pictures                                              pieces of their web (backgrounds cleared: alpha)
  office.webp   LIVE builder, step 2: the HQ             web-builder.webp  LIVE builder, step 2: its Start card
  dev.webp      LIVE builder's tour: Development         web-bib.webp      LIVE /build-it-better, its top
  agent.webp    the Hero Agent (Antigravity,             web-casino.webp   LIVE /agent-casino, its table
                outbox/quest/gen; -tall for phones)
  cube.webp     LIVE /promo-market: its cube of light    web-briefs.webp   their Promo Market with a sample brief, from
                                                                           our mirror's picture of 2026-10-27
                                                                           (outbox/promo-market-v3/pictures): their
                                                                           market has no open brief today
  podium.webp   our Universe mock (?season0)             web-board.webp    the same leaderboard, its rows: the monthly
                                                                           ET10 board is not live yet

    python outbox/quest-steps/capture.py              # every one
    python outbox/quest-steps/capture.py dev cube     # some

Chrome with a real GPU (the office is WebGPU), as outbox/quest/render.py does. Live pages are read anonymously (GET,
no cookies, no key); the builder is typed into (a name) and never submitted.
"""
import functools
import http.server
import io
import socket
import sys
import threading
import time
from pathlib import Path

from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUTBOX = HERE.parent
QUEST = OUTBOX / 'quest'
OUT = HERE / 'pics'
GPU = ['--enable-unsafe-webgpu', '--use-angle=d3d11', '--ignore-gpu-blocklist']

# only the 3D: every element hidden but the canvases (visibility, so nothing moves)
ONLY_3D = "html, body { background: #05070c !important; } body * { visibility: hidden !important; } canvas { visibility: visible !important; }"
# every box that covers much of the screen loses its background, so the page's own words, buttons and pictures float
CLEAR_BIG = """() => {
  const A = innerWidth * innerHeight;
  document.documentElement.style.background = 'transparent'; document.body.style.background = 'transparent';
  for (const e of document.querySelectorAll('body *')) {
    const r = e.getBoundingClientRect();
    if (r.width * r.height > A * 0.2) { e.style.background = 'transparent'; e.style.backgroundImage = 'none'; e.style.boxShadow = 'none'; }
  }
  const s = document.createElement('style');
  s.textContent = 'html::before, html::after, body::before, body::after, main::before, main::after, .wrap::before, .wrap::after, section::before, section::after { display: none !important; }';
  document.head.appendChild(s);
}"""
# one element of the page, its own box cleared too, as a picture with alpha
CLEAR_ONE = """(sel) => { const e = document.querySelector(sel);
  e.style.background = 'transparent'; e.style.backgroundImage = 'none'; e.style.boxShadow = 'none'; e.style.borderColor = 'transparent';
  e.style.backdropFilter = 'none'; e.style.webkitBackdropFilter = 'none';
  const r = e.getBoundingClientRect(); return { x: r.left, y: r.top, width: r.width, height: r.height }; }"""


def serve(directory):
    with socket.socket() as s:
        s.bind(('127.0.0.1', 0))
        port = s.getsockname()[1]

    class Quiet(http.server.SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass
    server = http.server.ThreadingHTTPServer(('127.0.0.1', port), functools.partial(Quiet, directory=str(directory)))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return f'http://127.0.0.1:{port}/'


def hologram(img):
    """a piece of their web as light: what is near black (their page's dark, its panels' fills) goes clear, and only
    what glows -- type, lines, buttons, pictures -- stays, so it never reads as a rectangle on the dark"""
    img = img.convert('RGBA')
    key = img.convert('RGB').convert('L').point(lambda v: 0 if v < 14 else 255 if v > 70 else (v - 14) * 255 // 56)
    img.putalpha(ImageChops.multiply(img.getchannel('A'), key))
    return img


def save(img, name, size=None, quality=86):
    if size:
        img = img.resize(size, Image.LANCZOS)
    if name.startswith('web-'):
        img = hologram(img)
    path = OUT / name
    img.save(path, quality=quality, method=6)
    alpha = ''
    if img.mode == 'RGBA':
        lo, hi = img.getchannel('A').getextrema()
        alpha = f'  alpha {lo}..{hi}'
    print(f'{name} {img.width}x{img.height} {path.stat().st_size // 1024} KB{alpha}')


def shot(page, clip, pad=0):
    x, y, w, h = clip['x'] - pad, clip['y'] - pad, clip['width'] + 2 * pad, clip['height'] + 2 * pad
    return Image.open(io.BytesIO(page.screenshot(clip={'x': x, 'y': y, 'width': w, 'height': h}, omit_background=True))).convert('RGBA')


def builder(b):
    """the builder's step 2: the Start card (web), the office (picture), then the tour to Development (picture)"""
    page = b.new_page(viewport={'width': 1920, 'height': 1080}, device_scale_factor=2)
    page.goto('https://cymetica.com/company/app/builder', wait_until='domcontentloaded', timeout=60000)
    time.sleep(12)
    page.fill('#f-name', 'Moonshot Labs')          # typed, never submitted: step 2 shows the office and its tour
    page.click('#b-next')
    time.sleep(12)
    # the office, its own 3D alone
    tag = page.add_style_tag(content=ONLY_3D)
    time.sleep(2)
    img = Image.open(io.BytesIO(page.screenshot())).convert('RGB')
    w, h = img.size                                   # the page's own rounded frame sits in the outer 1 %: cut it
    save(img.crop((int(w * 0.012), int(h * 0.016), int(w * 0.988), int(h * 0.984))), 'office.webp', (2560, 1440))
    tag.evaluate('t => t.remove()')
    # the Start card, floating: no 3D behind it, no box round it
    tag = page.add_style_tag(content="""html, body, main, section.stage { background: transparent !important; }
      section.stage::before, section.stage::after { display: none !important; } canvas, .bz-call { visibility: hidden !important; }""")
    time.sleep(1)
    save(shot(page, page.evaluate(CLEAR_ONE, 'section.bz-card'), 4), 'web-builder.webp')
    tag.evaluate('t => t.remove()')
    page.evaluate("() => { const c = document.querySelector('section.bz-card'); c.style.background = ''; c.style.boxShadow = ''; c.style.borderColor = ''; }")
    # the tour: Command, the Vault, then Development
    page.click('.bz-call')
    time.sleep(4.5)
    for _ in range(2):
        page.click('.bz-go')
        time.sleep(5)
    page.add_style_tag(content=ONLY_3D)
    time.sleep(2)
    img = Image.open(io.BytesIO(page.screenshot())).convert('RGB')
    w, h = img.size
    img = img.crop((int(w * 0.012), int(h * 0.016), int(w * 0.988), int(h * 0.984))).resize((2560, 1440), Image.LANCZOS)
    save(img.crop((1120, 330, 2240, 1080)), 'dev.webp')       # the tour's own camera, cut to the Development room
    page.close()


def bib(b):
    page = b.new_page(viewport={'width': 1600, 'height': 1000}, device_scale_factor=2)
    page.goto('https://cymetica.com/build-it-better', wait_until='domcontentloaded', timeout=60000)
    time.sleep(7)
    page.evaluate(CLEAR_BIG)
    time.sleep(0.6)
    save(shot(page, page.evaluate(CLEAR_ONE, '.bb-hero'), 6), 'web-bib.webp')
    page.close()


def casino(b):
    page = b.new_page(viewport={'width': 1600, 'height': 1400}, device_scale_factor=2)
    page.goto('https://cymetica.com/agent-casino', wait_until='domcontentloaded', timeout=60000)
    time.sleep(8)
    page.evaluate(CLEAR_BIG)
    time.sleep(0.6)
    save(shot(page, page.evaluate(CLEAR_ONE, 'a.at-big.at-feat'), 4), 'web-casino.webp')
    page.close()


def cube(b):
    page = b.new_page(viewport={'width': 1600, 'height': 1000}, device_scale_factor=3)
    page.goto('https://cymetica.com/promo-market', wait_until='domcontentloaded', timeout=60000)
    time.sleep(8)
    page.evaluate(CLEAR_BIG)
    time.sleep(0.6)
    save(shot(page, page.evaluate(CLEAR_ONE, 'section.hero .holo'), 30), 'cube.webp')
    page.close()


def briefs(_b):
    # their market as our mirror drew it on 2026-10-27, with its one sample brief: the heading and the card
    img = Image.open(OUTBOX / 'promo-market-v3' / 'pictures' / '5-market-v3.png').convert('RGB')
    save(img.crop((318, 858, 782, 1392)), 'web-briefs.webp')


def board(b):
    base = serve(OUTBOX / 'company-live')
    page = b.new_page(viewport={'width': 1600, 'height': 1000}, device_scale_factor=2)
    page.goto(base + 'index.html?season0#universe', wait_until='domcontentloaded', timeout=60000)
    time.sleep(16)
    page.click('#uv-board [data-a="board-all"]')
    time.sleep(2.5)
    page.add_style_tag(content="""
      html, body { background: transparent !important; }
      body * { visibility: hidden !important; }
      .modal-card.lbg, .modal-card.lbg * { visibility: visible !important; }
      .modal-card.lbg .mh, .modal-card.lbg .mh * { visibility: hidden !important; }
      .modal, .modal-card.lbg { background: transparent !important; box-shadow: none !important; border-color: transparent !important;
        -webkit-backdrop-filter: none !important; backdrop-filter: none !important; }
      .modal-card.lbg::before, .modal-card.lbg::after, .modal-card.lbg .uvb-sh { display: none !important; }
    """)
    time.sleep(1.2)
    box = page.evaluate("""() => { const c = document.querySelector('.modal-card.lbg'), r = c.getBoundingClientRect();
      const s = c.querySelector('.lb-pod').getBoundingClientRect();
      const rows = [...c.querySelectorAll('.lb-r')].slice(0, 3), head = c.querySelector('.lb-head').getBoundingClientRect();
      return { podium: { x: s.left - 30, y: s.top - 60, width: s.width + 60, height: s.height + 90 },
               rows: { x: r.left, y: head.top - 10, width: r.width, height: rows[rows.length - 1].getBoundingClientRect().bottom - head.top + 18 } }; }""")
    save(shot(page, box['podium']), 'podium.webp')
    save(shot(page, box['rows']), 'web-board.webp')
    page.close()


def sky(_b):
    # the revenue-share flyer's deep space, Cymetica's sun far off at the top: behind the opening, never flown into
    save(Image.open(OUTBOX / 'revenue-share-flyer' / 'space-bg.jpg').convert('RGB'), 'space.webp', quality=82)


def agent(_b):
    save(Image.open(QUEST / 'gen' / 'lab-16x9.png').convert('RGB'), 'agent.webp', quality=82)
    save(Image.open(QUEST / 'gen' / 'lab-9x16.png').convert('RGB'), 'agent-tall.webp', (1080, 1920), quality=80)


SHOTS = {'builder': builder, 'bib': bib, 'casino': casino, 'cube': cube, 'briefs': briefs, 'board': board, 'agent': agent, 'sky': sky}


def main(names):
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(channel='chrome', args=GPU)
        for name in names:
            SHOTS[name](b)
        b.close()


if __name__ == '__main__':
    main(sys.argv[1:] or list(SHOTS))
