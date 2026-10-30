"""The pictures for the Quest steps page, into pics/ (the page loads these).

Fourth take (the operator, 2026-10-30): five steps in his words, each with the pictures he named. Nowhere the second
take's orbit with its companies: the one Universe picture is a near camera on two products.

  step  file                what, and from where
  01    office.webp         LIVE builder, its Start (step 2) at 1920 x 1080, the office in 3D (refused if it drew flat)
        builder-card.webp   the same page's card as it stands, laid back over the office where the page puts it
  02    tools.webp          our robot-arm workshop (scenes/tools.html at 60da77f5, the second take's), kept from git
  03    agent.webp          the Hero Agent (Antigravity, outbox/quest/gen; agent-tall.webp for phones)
        casino.webp         the Agent Casino's building as our Universe mock draws it (u3d.js adCasino), cut out
  04    promo.webp          their Promo Market through our read-only mirror (outbox/promo-market-v3/live, ?v2), with
                            three sample briefs: their market has none open today
        farmer.webp         our Universe mock, near: the Airdrop Farmer, and the Gem Screener brought behind it
  05    podium.webp         our Universe mock's leaderboard (?season0): the monthly ET10 board is not live yet
        web-board.webp      the same leaderboard, its rows, as light
        space.webp          the revenue-share flyer's deep space and sun, behind the first screen

    python outbox/quest-steps/capture.py                 # every one
    python outbox/quest-steps/capture.py farmer casino   # some

Chrome with a real GPU (the office and the Universe are WebGPU), as outbox/quest/render.py does. Live pages are read
anonymously (GET, no cookies, no key); the builder is typed into (a name) and never submitted; the mirror refuses
every method but GET and HEAD.
"""
import functools
import http.server
import io
import socket
import subprocess
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
    # full_page, so a clip taller than the window is taken whole (the clip is in the page's coordinates then)
    sy = page.evaluate('scrollY')
    return Image.open(io.BytesIO(page.screenshot(clip={'x': x, 'y': y + sy, 'width': w, 'height': h}, omit_background=True, full_page=True))).convert('RGBA')


def builder(b):
    """the builder's Start (its step 2) as it stands at 1920 x 1080: the office in 3D, and its card, which the page
    lays over the office at the place the live page puts it (quest.css .ui, from the numbers this prints)"""
    page = b.new_page(viewport={'width': 1920, 'height': 1080}, device_scale_factor=2)
    page.goto('https://cymetica.com/company/app/builder', wait_until='domcontentloaded', timeout=60000)
    time.sleep(12)
    page.fill('#f-name', 'Moonshot Labs')          # typed, never submitted: step 2 shows the office and its tour
    page.click('#b-next')
    time.sleep(12)
    assert page.evaluate("() => document.getElementById('stage').classList.contains('is3d')"), 'the builder drew its flat office, not 3D'
    # the office, its own 3D alone (the tour's "click here" bubble left out: a picture cannot be clicked)
    tag = page.add_style_tag(content=ONLY_3D)
    time.sleep(2)
    img = Image.open(io.BytesIO(page.screenshot())).convert('RGB')
    w, h = img.size                                   # the page's own rounded frame sits in the outer 1 %: cut it
    x0, y0, x1, y1 = int(w * 0.012), int(h * 0.016), int(w * 0.988), int(h * 0.984)
    save(img.crop((x0, y0, x1, y1)), 'office.webp', (2560, 1440))
    tag.evaluate('t => t.remove()')
    # the card as the page draws it, its own glass and rim kept; only the 3D behind it gone
    page.add_style_tag(content="""html, body, main, section.stage { background: transparent !important; }
      section.stage::before, section.stage::after { display: none !important; } canvas, .bz-call { visibility: hidden !important; }""")
    time.sleep(1)
    r = page.evaluate("() => { const r = document.querySelector('section.bz-card').getBoundingClientRect(); return { x: r.left, y: r.top, width: r.width, height: r.height }; }")
    save(shot(page, r, 2), 'builder-card.webp')
    dpr = w / 1920
    print('card in the office picture: left {:.2%} top {:.2%} width {:.2%}'.format(
        (r['x'] - 2 - x0 / dpr) / ((x1 - x0) / dpr), (r['y'] - 2 - y0 / dpr) / ((y1 - y0) / dpr), (r['width'] + 4) / ((x1 - x0) / dpr)))
    page.close()


def tools(_b):
    """step 2's workshop: the robot arms building an app in light, our three.js scene of the second take
    (scenes/tools.html at 60da77f5, rendered then), kept from git"""
    data = subprocess.run(['git', '-C', str(HERE), 'show', '60da77f5:outbox/quest-steps/pics/tools.webp'], capture_output=True, check=True).stdout
    save(Image.open(io.BytesIO(data)).convert('RGB'), 'tools.webp', quality=84)


def promo(b):
    """step 4's first picture: the Promo Market's own page with briefs up for grabs. Their market has none open today,
    so it is drawn by our read-only mirror of their live page (outbox/promo-market-v3/live, ?v2: their look as it is),
    its sample brief and two more of Cymetica's products beside it, from one model: the counters are the cards' sum.
    The page is cut to its opening (the words, the cube, the counters) and the briefs under it."""
    sys.path.insert(0, str(OUTBOX / 'promo-market-v3' / 'live'))
    import sample
    import serve as mirror
    g = sample.brief()
    more = [dict(g, id=9002, name='Airdrop Farmer', path='/airdrop-farmer', url='https://cymetica.com/airdrop-farmer', art=None,
                 preview_url='/uploads/bb-previews/airdrop-farmer.jpg', budget_usdc=150, up_for_grabs_usdc=150.0, per_user_usdc=4,
                 per_visitor_usdc=0.04, days_left=12, say_line='Sample brief.', materials=[]),
            dict(g, id=9003, name='Agent Casino', path='/agent-casino', url='https://cymetica.com/agent-casino', art='/static/img/promo-art/casino.svg',
                 preview_url='/uploads/bb-previews/agent-casino.jpg', budget_usdc=60, up_for_grabs_usdc=60.0, per_user_usdc=3,
                 per_visitor_usdc=0.03, days_left=9, say_line='Sample brief.', materials=[])]
    briefs = sorted([g] + more, key=lambda x: -x['up_for_grabs_usdc'])
    top = max(briefs, key=lambda x: x['per_user_usdc'])
    stats = {'up_for_grabs_usdc': round(sum(x['up_for_grabs_usdc'] for x in briefs), 2), 'open_briefs': len(briefs),
             'top_per_user_usdc': top['per_user_usdc'], 'top_per_user_name': top['name'], 'as_of': sample.AS_OF}
    own = sample.answers

    def answers():
        a = own()
        a['/api/v1/promo/briefs'] = {'stats': stats, 'briefs': briefs, 'sort': 'left', 'how_counted': []}
        a['/api/v1/promo/house']['market'] = stats
        return a
    sample.answers = answers
    srv = mirror.ThreadingHTTPServer(('127.0.0.1', 0), mirror.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    page = b.new_page(viewport={'width': 1600, 'height': 1000}, device_scale_factor=2)
    page.goto(f'http://127.0.0.1:{srv.server_address[1]}/promo-market?v2', wait_until='domcontentloaded', timeout=60000)
    time.sleep(9)
    # the opening, then the briefs right under it: what stands between them is folded away
    # (the mirror's own v2/v3 switch and their header stay out: both stand fixed over the page)
    r = page.evaluate("""() => { for (const e of document.querySelectorAll('body *')) if (/fixed|sticky/.test(getComputedStyle(e).position)) e.style.display = 'none';
      const hero = document.querySelector('section.hero'), cards = [...document.querySelectorAll('article.bc[data-brief]')];
      const list = cards.length ? cards[0].closest('section') : null;
      for (let s = hero.nextElementSibling; s && s !== list; s = s.nextElementSibling) s.style.display = 'none';
      if (list) for (let s = list.nextElementSibling; s; s = s.nextElementSibling) s.style.display = 'none';
      const a = hero.getBoundingClientRect(), z = (list || hero).getBoundingClientRect();
      return { x: a.left, y: a.top, width: a.width, height: z.bottom - a.top, cards: cards.length }; }""")
    print('promo: briefs drawn', r.pop('cards'))
    time.sleep(1)
    save(shot(page, r, 24).convert('RGB'), 'promo.webp')
    page.close()
    srv.shutdown()


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


def universe(b, query='?season0'):
    """our Universe mock (outbox/company-live) with its ads on, settled, its camera and items ours to move"""
    base = serve(OUTBOX / 'company-live')
    page = b.new_page(viewport={'width': 1600, 'height': 1000}, device_scale_factor=2)
    page.goto(base + 'index.html' + query + '#universe', wait_until='domcontentloaded', timeout=60000)
    time.sleep(16)
    page.wait_for_function("() => window.CO && CO.uv && CO.uv.camera && CO.uv.items.some(it => it.c.id === 'ad-farmer')", timeout=30000)
    return page


# the map's sky, sun, lanes, haze and ships, all of it hidden (what Universe3D keeps of each, u3d.js)
HIDE_SKY = """() => { const uv = CO.uv;
  ['sky', 'dust', 'haze', 'ships', 'sun', 'corona', 'heart', 'fil', 'rays', 'weave', 'beams', 'sparkPts', 'coreFlare', 'coreG', 'arcs', 'fades']
    .forEach(k => { const v = uv[k]; [].concat(v || []).forEach(o => { if (o && o.isObject3D) o.visible = false; else if (o && o.mesh && o.mesh.isObject3D) o.mesh.visible = false; }); }); }"""


def cutout(img, lo=6, hi=46):
    """a thing drawn on black, the black made clear (softer than hologram: a 3D object keeps its dark sides)"""
    img = img.convert('RGBA')
    key = img.convert('RGB').convert('L').point(lambda v: 0 if v < lo else 255 if v > hi else (v - lo) * 255 // (hi - lo))
    img.putalpha(ImageChops.multiply(img.getchannel('A'), key))
    return img.crop(img.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox())


def casino_building(b):
    """step 3, under the hero agent: the Agent Casino's building as the Universe draws it (u3d.js adCasino, the big
    orbital chip), alone on black, then cut out. Nothing else of the map is drawn: no sky, no orbits, no station."""
    page = universe(b)
    page.add_style_tag(content=ONLY_3D)
    page.evaluate(HIDE_SKY)
    page.evaluate("""() => { const uv = CO.uv, it = uv.items.find(x => x.c.id === 'ad-casino'), keep = new Set();
      for (let o = it.plot.root; o; o = o.parent) keep.add(o);
      const hide = (g) => g.children.forEach(c => { if (c.isLight) return; if (keep.has(c)) { if (c !== it.plot.root) hide(c); } else c.visible = false; });
      hide(uv.scene);
      it.plot.ring.visible = false; it.plot.pool.visible = false; it.plot.halo.visible = false;
      it.orbit = null; uv.follow = null; uv.controls.autoRotate = false;
      const p = it.plot.root.position, k = it.plot.k, tgt = p.clone(); tgt.y += (it.plot.top + it.plot.bot) * 0.5 * k;
      const dir = new uv.camera.position.constructor(1, 0.36, 0.55).normalize();
      uv.tween(tgt.clone().add(dir.multiplyScalar((it.plot.top - it.plot.bot) * k * 3.1)), tgt, 0); }""")
    time.sleep(3)
    # only the building's own square of the screen (the map's sun, far off, can still reach into the frame)
    box = page.evaluate("""() => { const uv = CO.uv, it = uv.items.find(x => x.c.id === 'ad-casino'), r = uv.el.getBoundingClientRect();
      const B = new (uv.camera.position.constructor)(), pts = [], hit = it.plot.hit; hit.updateWorldMatrix(true, false);
      for (const sx of [-0.5, 0.5]) for (const sy of [-0.5, 0.5]) for (const sz of [-0.5, 0.5]) {
        B.set(sx, sy, sz).applyMatrix4(hit.matrixWorld).project(uv.camera);
        pts.push([r.left + (B.x + 1) / 2 * r.width, r.top + (1 - B.y) / 2 * r.height]); }
      const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
      return { x: Math.min(...xs), y: Math.min(...ys), width: Math.max(...xs) - Math.min(...xs), height: Math.max(...ys) - Math.min(...ys) }; }""")
    img = shot(page, box, 20).convert('RGB')
    save(cutout(img), 'casino.webp')
    page.close()


def farmer(b):
    """step 4's second picture: the Airdrop Farmer close in the Universe and, farther back, the Gem Screener, as the
    operator's own picture of 2026-10-30 has them ("zoom na airdrop farmer, pak nejak dal do pozadi Gem Screener").
    Composed: the gem is brought behind the farmer for the picture (on the map they stand two orbits apart) and the
    other stations are left out; the camera is near, never the map's whole galaxy (the second take's orbit)."""
    page = universe(b)
    page.add_style_tag(content=ONLY_3D + " .b3.keep, .b3.keep * { visibility: visible !important; }")
    page.evaluate("""() => { const uv = CO.uv, V = uv.camera.position.constructor, up = new V(0, 1, 0);
      const F = uv.items.find(x => x.c.id === 'ad-farmer'), G = uv.items.find(x => x.c.id === 'ad-gem');
      uv.items.forEach(x => { if (x !== F && x !== G && x.plot) x.plot.root.visible = false; });
      F.orbit = null; G.orbit = null; uv.follow = null; uv.controls.autoRotate = false;
      const f = F.plot.root.position.clone(), k = F.plot.k, h = (F.plot.top - F.plot.bot) * k;
      // looking along the farmer's orbit (its lanes sweep across the picture, the sun out of it), a little inwards;
      // the farmer left of the middle, the gem far behind it on the right and a little higher
      const out = new V(f.x, 0, f.z).normalize(), along = up.clone().cross(out).normalize();
      const look = along.clone().addScaledVector(out, -0.22).normalize(), right = look.clone().cross(up).normalize();
      const mid = f.clone(); mid.y += h * 0.5;
      const aim = mid.clone().addScaledVector(right, h * 0.6);
      const cam = aim.clone().addScaledVector(look, -h * 3.6); cam.y += h * 0.6;
      const g = f.clone().addScaledVector(look, h * 8).addScaledVector(right, h * 3.5); g.y -= h * 1.8;
      G.plot.root.position.copy(g);
      [F, G].forEach(x => { x.anchor.set(x.plot.root.position.x, x.plot.root.position.y + (x.plot.top + 0.5) * (x.plot.k || 1), x.plot.root.position.z); if (x.el) x.el.classList.add('keep'); });
      uv.tween(cam, aim, 0); }""")
    time.sleep(3)
    print('farmer, gem on screen (-1..1):', page.evaluate("""() => ['ad-farmer', 'ad-gem'].map(id => { const it = CO.uv.items.find(x => x.c.id === id);
      const p = it.plot.root.position.clone(); p.y += (it.plot.top + it.plot.bot) * 0.5 * it.plot.k; p.project(CO.uv.camera);
      return [+p.x.toFixed(2), +p.y.toFixed(2), +p.z.toFixed(3), it.plot.root.visible]; })"""))
    r = page.evaluate("() => { const r = document.getElementById('uvstage').getBoundingClientRect(); return { x: r.left, y: r.top, width: r.width, height: r.height }; }")
    img = shot(page, {'x': r['x'] + 8, 'y': r['y'] + 8, 'width': r['width'] - 16, 'height': r['height'] - 16}).convert('RGB')
    save(img, 'farmer.webp', (2400, round(2400 * img.height / img.width)))
    page.close()


SHOTS = {'builder': builder, 'tools': tools, 'agent': agent, 'casino': casino_building, 'promo': promo, 'farmer': farmer,
         'board': board, 'sky': sky}


def main(names):
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(channel='chrome', args=GPU)
        for name in names:
            SHOTS[name](b)
        b.close()


if __name__ == '__main__':
    main(sys.argv[1:] or list(SHOTS))
