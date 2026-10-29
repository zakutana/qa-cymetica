"""The pictures for the Quest steps page, into pics/ (the page loads these).

What each one is, and where it comes from (the operator, 2026-10-29: the office from the tutorial for step 1, "space
robotic tools" and "breed your agent" for step 2, the Promo Market building close and its page for step 3, and nothing
in a panel: every picture melts into the page):

  fly/NNN.webp   the hero's flight in from deep space to Cymetica's sun: outbox/quest/frames/desk/approach, our Universe
                 mock's own render (2026-10-27), every 2nd frame. Not in git: neither are its source frames, so a fresh
                 clone shows fly-0.webp, the first frame, which is kept.
  office.webp    LIVE: cymetica.com/company/app/builder, step 2 (the tutorial's office, the headquarters), its own 3D with
                 every page element hidden (`visibility`, so the canvas keeps its place)
  tools.webp     our scene, scenes/tools.html: two robot arms building an app out of glass panels of light
  agent.webp     the Hero Agent, Antigravity's picture for the Quant Lab (outbox/quest/gen/lab-16x9.png, -9x16 for phones)
  tower.webp     the Promo Market station close: outbox/quest/frames/desk/promo/0089 (the mock's render of their model)
  promo-ui.webp  LIVE: cymetica.com/promo-market's top, every background cleared, so it floats (alpha)
  board.webp     the monthly leaderboard (podium and rows) from our Universe mock (?season0), backgrounds cleared (alpha):
                 the ET10 board is not live yet
  finale.webp    the whole Universe from above: outbox/quest/frames/desk/pullback/0119

    python outbox/quest-steps/capture.py              # every one
    python outbox/quest-steps/capture.py office board # some

Chrome with a real GPU (the Universe and the office are WebGPU), as outbox/quest/render.py does. Live pages are read
anonymously (GET, no cookies, no key); the builder is typed into (a name) and never submitted.
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
OUTBOX = HERE.parent
QUEST = OUTBOX / 'quest'
OUT = HERE / 'pics'
GPU = ['--enable-unsafe-webgpu', '--use-angle=d3d11', '--ignore-gpu-blocklist']

# only the 3D: every element hidden but the canvases (visibility, so nothing moves)
ONLY_3D = "html, body { background: #05070c !important; } body * { visibility: hidden !important; } canvas { visibility: visible !important; }"


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


def save(img, name, size=None, quality=84):
    if size:
        img = img.resize(size, Image.LANCZOS)
    path = OUT / name
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, quality=quality, method=6)
    alpha = ''
    if img.mode == 'RGBA':
        lo, hi = img.getchannel('A').getextrema()
        alpha = f'  alpha {lo}..{hi}'
    print(f'{name} {img.width}x{img.height} {path.stat().st_size // 1024} KB{alpha}')


def fly(_b):
    src = sorted((QUEST / 'frames' / 'desk' / 'approach').glob('*.webp'))[:141:2]
    if not src:
        print('fly: outbox/quest/frames/desk/approach is missing (render.py film); the page shows fly-0.webp')
        return
    (OUT / 'fly').mkdir(parents=True, exist_ok=True)
    for i, f in enumerate(src):
        img = Image.open(f).convert('RGB').resize((1920, 1080), Image.LANCZOS)
        img.save(OUT / 'fly' / f'{i:03d}.webp', quality=62, method=4)
        if i == 0:
            img.save(OUT / 'fly-0.webp', quality=78, method=6)
    total = sum(p.stat().st_size for p in (OUT / 'fly').glob('*.webp'))
    print(f'fly: {len(src)} frames, {total // 1024} KB; fly-0.webp kept')


def office(b):
    page = b.new_page(viewport={'width': 1920, 'height': 1080}, device_scale_factor=2)
    page.goto('https://cymetica.com/company/app/builder', wait_until='domcontentloaded', timeout=60000)
    time.sleep(12)
    page.fill('#f-name', 'Moonshot Labs')          # typed, never submitted: step 2 shows the office and its tour
    page.click('#b-next')
    time.sleep(12)
    page.add_style_tag(content=ONLY_3D)
    time.sleep(2)
    img = Image.open(io.BytesIO(page.screenshot())).convert('RGB')
    page.close()
    w, h = img.size                                   # the page's own rounded frame sits in the outer 1 %: cut it
    img = img.crop((int(w * 0.012), int(h * 0.016), int(w * 0.988), int(h * 0.984)))
    save(img, 'office.webp', (2560, 1440))


def tools(b):
    base = serve(HERE / 'scenes')
    for name, (w, h) in (('tools.webp', (2560, 1440)),):
        page = b.new_page(viewport={'width': w, 'height': h})
        page.goto(base + f'tools.html?w={w}&h={h}', wait_until='load')
        page.wait_for_function('window.READY === true', timeout=120000)
        time.sleep(0.5)
        save(Image.open(io.BytesIO(page.screenshot())).convert('RGB'), name)
        page.close()


def agent(_b):
    save(Image.open(QUEST / 'gen' / 'lab-16x9.png').convert('RGB'), 'agent.webp', quality=82)
    save(Image.open(QUEST / 'gen' / 'lab-9x16.png').convert('RGB'), 'agent-tall.webp', (1080, 1920), quality=80)


def tower(_b):
    img = Image.open(QUEST / 'frames' / 'desk' / 'promo' / '0089.webp').convert('RGB')
    save(img.crop((0, 40, img.width, img.height)), 'tower.webp')          # the label's stub off the top


def finale(_b):
    save(Image.open(QUEST / 'frames' / 'desk' / 'pullback' / '0119.webp').convert('RGB'), 'finale.webp', quality=80)


# every box that covers much of the screen loses its background, so the page's own words, buttons and cube float
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


def promo_ui(b):
    page = b.new_page(viewport={'width': 1600, 'height': 1000}, device_scale_factor=2)
    page.goto('https://cymetica.com/promo-market', wait_until='domcontentloaded', timeout=60000)
    time.sleep(8)
    page.evaluate(CLEAR_BIG)
    time.sleep(1)
    png = page.screenshot(clip={'x': 120, 'y': 86, 'width': 1360, 'height': 392}, omit_background=True)
    page.close()
    save(Image.open(io.BytesIO(png)).convert('RGBA'), 'promo-ui.webp', quality=88)


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
      .modal-card.lbg .mh { visibility: hidden !important; }
      .modal, .modal-card.lbg { background: transparent !important; box-shadow: none !important; border-color: transparent !important;
        -webkit-backdrop-filter: none !important; backdrop-filter: none !important; }
      .modal-card.lbg::before, .modal-card.lbg::after, .modal-card.lbg .uvb-sh { display: none !important; }
    """)
    time.sleep(1.2)
    box = page.evaluate("""() => { const c = document.querySelector('.modal-card.lbg'), h = c.querySelector('.mh');
      const r = c.getBoundingClientRect(), t = h ? h.getBoundingClientRect().bottom : r.top;
      const rows = [...c.querySelectorAll('.lb-r')].slice(0, 3), last = rows.length ? rows[rows.length - 1].getBoundingClientRect().bottom : r.bottom;
      return { x: r.left, y: t, w: r.width, h: last - t + 8 }; }""")
    png = page.screenshot(clip={'x': box['x'], 'y': box['y'], 'width': box['w'], 'height': box['h']}, omit_background=True)
    page.close()
    save(Image.open(io.BytesIO(png)).convert('RGBA'), 'board.webp', quality=88)


SHOTS = {'fly': fly, 'office': office, 'tools': tools, 'agent': agent, 'tower': tower, 'promo-ui': promo_ui, 'board': board, 'finale': finale}


def main(names):
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(channel='chrome', args=GPU)
        for name in names:
            SHOTS[name](b)
        b.close()


if __name__ == '__main__':
    main(sys.argv[1:] or list(SHOTS))
