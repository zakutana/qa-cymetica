"""The still pictures for the Quest steps page, into pics/ (the page loads these; the clips and their posters are
record.py's).

Fifth take (the operator, 2026-10-30).

  where   file                what, and from where
  top     space.webp          the flyer's nebula and stars (revenue-share-flyer/nebula.py) made sharp at 3840 x 2160
          sun.webp            Cymetica's sun alone, from our Universe mock, its light as alpha
          co-1..5.webp        five companies from our Universe mock, each alone and cut out, to float round the sun
  01      builder-card.webp   the LIVE builder's Start card as it stands, laid over the office clip where the page puts it
  03      agent.webp          the Hero Agent (Antigravity, outbox/quest/gen), drawn by step 3's Quant Lab (anim.js)
  04      promo.webp          their Promo Market through our read-only mirror (outbox/promo-market-v3/live, ?v2), with
                              three sample briefs: their market has none open today

    python outbox/quest-steps/capture.py                 # every one
    python outbox/quest-steps/capture.py sun stations    # some

Chrome with a real GPU (the office and the Universe are WebGPU), as outbox/quest/render.py does. Live pages are read
anonymously (GET, no cookies, no key); the builder is typed into (a name) and never submitted; the mirror refuses
every method but GET and HEAD.
"""
import functools
import http.server
import io
import socket
import sys
import threading
import time
from pathlib import Path

import numpy as np
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
    """the builder's Start card as the live page draws it at 1920 x 1080, its own glass and rim kept, only the 3D behind
    it gone; the page lays it over the office clip (record.py) at the place the live page puts it (quest.css .ui)"""
    page = b.new_page(viewport={'width': 1920, 'height': 1080}, device_scale_factor=2)
    page.goto('https://cymetica.com/company/app/builder', wait_until='domcontentloaded', timeout=60000)
    time.sleep(12)
    page.fill('#f-name', 'Moonshot Labs')          # typed, never submitted: step 2 shows the office and its tour
    page.click('#b-next')
    time.sleep(12)
    page.add_style_tag(content="""html, body, main, section.stage { background: transparent !important; }
      section.stage::before, section.stage::after { display: none !important; } canvas, .bz-call { visibility: hidden !important; }""")
    time.sleep(1)
    r = page.evaluate("() => { const r = document.querySelector('section.bz-card').getBoundingClientRect(); return { x: r.left, y: r.top, width: r.width, height: r.height }; }")
    save(shot(page, r, 2), 'builder-card.webp')
    page.close()


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


def sky(_b):
    """the first screen's deep space, sharp ("ten vesmir ... ma spatne rozliseni ze je jeste rozmazany"): the flyer's
    nebula and stars (revenue-share-flyer/nebula.py) made at 3840 x 2160, landscape, so a wide screen never stretches
    it; the sun is not in it (sun.webp, its own layer, with the companies round it)"""
    sys.path.insert(0, str(OUTBOX / 'revenue-share-flyer'))
    import nebula
    nebula.W, nebula.H = 3840, 2160
    img = Image.fromarray(np.clip(nebula.make(7, 0.5), 0, 255).astype(np.uint8), 'RGB')
    save(img, 'space.webp', quality=88)


def sun(b):
    """Cymetica's sun alone, from our Universe mock (its ball, glow and rays; no orbit, ring or station), on black: the
    page screens it over the sky. Prints how wide its bright ball is, so the page can size the companies by it."""
    sys.path.insert(0, str(OUTBOX / 'revenue-share-flyer'))
    import render as flyer
    page = universe(b, viewport={'width': 700, 'height': 700}, dsf=2)
    page.add_style_tag(content=ONLY_3D)
    for _ in range(3):
        page.evaluate(flyer.CAMERA, [1.25, 170.0, 0.5, 0.5])
        page.evaluate(flyer.ONLY_SUN)
        time.sleep(3)
    img = Image.open(io.BytesIO(page.screenshot())).convert('RGB')
    page.close()
    a = np.asarray(img, np.float32)
    ground = np.median(np.concatenate([a[:40, :40].reshape(-1, 3), a[-40:, -40:].reshape(-1, 3)]), axis=0)
    a = np.clip((a - ground) / (255 - ground) * 255, 0, 255)
    lum = a.mean(axis=2)
    ys, xs = np.nonzero(lum > 225)
    print('sun: its bright ball is', round(float(np.percentile(xs, 98) - np.percentile(xs, 2)) / a.shape[1] * 100, 1), '% of the picture wide')
    # light as alpha: its brightest channel is how much it covers, its colour that light undarkened, so it lays over the
    # sky as light without a blend mode (main is its own stacking context: a screen blend there would see no sky)
    alpha = a.max(axis=2, keepdims=True)
    rgb = np.where(alpha > 0, a * 255 / np.maximum(alpha, 1), 0)
    save(Image.fromarray(np.concatenate([rgb, alpha], axis=2).clip(0, 255).astype(np.uint8), 'RGBA'), 'sun.webp', quality=90)


def stations(b):
    """five companies from our Universe mock, each alone on black and cut out (u3d.js makeStation, five looks), for the
    first screen: they float round the sun, none bigger than an eighth of it (quest.css #sun)"""
    page = universe(b, viewport={'width': 600, 'height': 600}, dsf=1)
    page.add_style_tag(content=ONLY_3D)
    page.evaluate(HIDE_SKY)
    ids = page.evaluate("""() => { const seen = new Set(), out = [];
      for (const it of CO.uv.items) { if (it.kind || !it.plot || !it.c.skin || seen.has(it.c.skin)) continue; seen.add(it.c.skin); out.push(it.c.id); }
      return out.slice(0, 5); }""")
    for n, cid in enumerate(ids, 1):
        page.evaluate("""([id, fixed]) => { const uv = CO.uv, it = uv.items.find(x => x.c.id === id), keep = new Set();
          uv.items.forEach(x => { if (x.plot) x.plot.root.visible = x === it; });
          for (let o = it.plot.root; o; o = o.parent) keep.add(o);
          const hide = (g) => g.children.forEach(c => { if (c.isLight) return; if (keep.has(c)) { if (c !== it.plot.root) hide(c); } else c.visible = false; });
          hide(uv.scene);
          ['ring', 'pool', 'halo'].forEach(k => { if (it.plot[k]) it.plot[k].visible = false; });
          it.orbit = null; uv.follow = null; uv.controls.autoRotate = false;
          const p = it.plot.root.position, k = it.plot.k || 1, tgt = p.clone(); tgt.y += (it.plot.top + it.plot.bot) * 0.5 * k;
          // the camera beside the station along its orbit, a little sunward and above: the sun out of the picture, to one
          // side (straight behind the station it shows; between them its glow floods the lens)
          const V = uv.camera.position.constructor, out = new V(p.x, 0, p.z).normalize(), along = new V(0, 1, 0).cross(out);
          const dir = fixed ? new V(1, 0.5, 0.7).normalize() : along.multiplyScalar(0.85).addScaledVector(out, -0.35); dir.y = fixed ? dir.y : 0.55; dir.normalize();
          uv.tween(tgt.clone().add(dir.multiplyScalar(Math.max(it.plot.top - it.plot.bot, it.plot.b.foot * 2) * k * 9.0)), tgt, 0); }""", [cid, n == 2])
        time.sleep(2.5)
        # only the station's own square of the screen: its body's box, projected
        box = page.evaluate("""(id) => { const uv = CO.uv, it = uv.items.find(x => x.c.id === id), r = uv.el.getBoundingClientRect();
          const V = uv.camera.position.constructor, bb = new (uv.camera.position.constructor)(), pts = [];
          const body = it.plot.body || it.plot.root; body.updateWorldMatrix(true, true);
          const lo = new V(Infinity, Infinity, Infinity), hi = new V(-Infinity, -Infinity, -Infinity);
          body.traverse(o => { if (!o.isMesh || !o.visible || !o.geometry) return; o.geometry.computeBoundingBox(); const g = o.geometry.boundingBox;
            for (const x of [g.min.x, g.max.x]) for (const y of [g.min.y, g.max.y]) for (const z of [g.min.z, g.max.z]) { const p = new V(x, y, z).applyMatrix4(o.matrixWorld); lo.min(p); hi.max(p); } });
          for (const x of [lo.x, hi.x]) for (const y of [lo.y, hi.y]) for (const z of [lo.z, hi.z]) { bb.set(x, y, z).project(uv.camera); pts.push([r.left + (bb.x + 1) / 2 * r.width, r.top + (1 - bb.y) / 2 * r.height]); }
          const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
          return { x: Math.max(r.left, Math.min(...xs)), y: Math.max(r.top, Math.min(...ys)), width: Math.min(r.right, Math.max(...xs)) - Math.max(r.left, Math.min(...xs)),
                   height: Math.min(r.bottom, Math.max(...ys)) - Math.max(r.top, Math.min(...ys)) }; }""", cid)
        img = shot(page, box, 6).convert('RGB')
        save(cutout(img, lo=10, hi=50, edge=0.08), f'co-{n}.webp')
    page.close()


def agent(_b):
    # the Hero Agent (Antigravity, outbox/quest/gen): step 3's Quant Lab draws it out of a hologram scan (anim.js)
    save(Image.open(QUEST / 'gen' / 'lab-16x9.png').convert('RGB'), 'agent.webp', quality=82)


def universe(b, query='?season0', viewport=None, dsf=2):
    """our Universe mock (outbox/company-live) with its ads on, settled, its camera and items ours to move"""
    base = serve(OUTBOX / 'company-live')
    page = b.new_page(viewport=viewport or {'width': 1600, 'height': 1000}, device_scale_factor=dsf)
    page.goto(base + 'index.html' + query + '#universe', wait_until='domcontentloaded', timeout=60000)
    time.sleep(16)
    page.wait_for_function("() => window.CO && CO.uv && CO.uv.camera && CO.uv.items.some(it => it.c.id === 'ad-farmer')", timeout=30000)
    return page


# the map's sky, sun, lanes, haze and ships, all of it hidden (what Universe3D keeps of each, u3d.js)
HIDE_SKY = """() => { const uv = CO.uv;
  ['sky', 'dust', 'haze', 'ships', 'sun', 'corona', 'heart', 'fil', 'rays', 'weave', 'beams', 'sparkPts', 'coreFlare', 'coreG', 'arcs', 'fades']
    .forEach(k => { const v = uv[k]; [].concat(v || []).forEach(o => { if (o && o.isObject3D) o.visible = false; else if (o && o.mesh && o.mesh.isObject3D) o.mesh.visible = false; }); }); }"""


def cutout(img, lo=6, hi=46, edge=0.0):
    """a thing drawn on black, the black made clear (softer than hologram: a 3D object keeps its dark sides); `edge`
    fades the outer share of each side to clear too, for a haze of the map that reaches into the frame"""
    img = img.convert('RGBA')
    key = img.convert('RGB').convert('L').point(lambda v: 0 if v < lo else 255 if v > hi else (v - lo) * 255 // (hi - lo))
    img.putalpha(ImageChops.multiply(img.getchannel('A'), key))
    if edge:
        w, h = img.size
        ex, ey = np.clip(np.minimum(np.arange(w), np.arange(w)[::-1]) / (w * edge), 0, 1), np.clip(np.minimum(np.arange(h), np.arange(h)[::-1]) / (h * edge), 0, 1)
        img.putalpha(Image.fromarray((np.asarray(img.getchannel('A'), np.float32) * np.outer(ey, ex)).astype(np.uint8), 'L'))
    return img.crop(img.getchannel('A').point(lambda v: 255 if v > 8 else 0).getbbox())


# the farmer's composition: the other stations left out, the two frozen on their orbits, the gem brought behind the
# farmer, a still camera (record.py films the same)
FARMER_SHOT = """() => { const uv = CO.uv, V = uv.camera.position.constructor, up = new V(0, 1, 0);
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
  uv.tween(cam, aim, 0); }"""


def farmer(b):
    """step 4's second picture: the Airdrop Farmer close in the Universe and, farther back, the Gem Screener, as the
    operator's own picture of 2026-10-30 has them ("zoom na airdrop farmer, pak nejak dal do pozadi Gem Screener").
    Composed: the gem is brought behind the farmer for the picture (on the map they stand two orbits apart) and the
    other stations are left out; the camera is near, never the map's whole galaxy (the second take's orbit)."""
    page = universe(b)
    page.add_style_tag(content=ONLY_3D + " .b3.keep, .b3.keep * { visibility: visible !important; }")
    page.evaluate(FARMER_SHOT)
    time.sleep(3)
    print('farmer, gem on screen (-1..1):', page.evaluate("""() => ['ad-farmer', 'ad-gem'].map(id => { const it = CO.uv.items.find(x => x.c.id === id);
      const p = it.plot.root.position.clone(); p.y += (it.plot.top + it.plot.bot) * 0.5 * it.plot.k; p.project(CO.uv.camera);
      return [+p.x.toFixed(2), +p.y.toFixed(2), +p.z.toFixed(3), it.plot.root.visible]; })"""))
    r = page.evaluate("() => { const r = document.getElementById('uvstage').getBoundingClientRect(); return { x: r.left, y: r.top, width: r.width, height: r.height }; }")
    img = shot(page, {'x': r['x'] + 8, 'y': r['y'] + 8, 'width': r['width'] - 16, 'height': r['height'] - 16}).convert('RGB')
    save(img, 'farmer.webp', (2400, round(2400 * img.height / img.width)))
    page.close()


SHOTS = {'sky': sky, 'sun': sun, 'stations': stations, 'builder': builder, 'agent': agent, 'promo': promo}


def main(names):
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(channel='chrome', args=GPU)
        for name in names:
            SHOTS[name](b)
        b.close()


if __name__ == '__main__':
    main(sys.argv[1:] or list(SHOTS))
