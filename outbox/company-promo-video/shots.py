"""The reference stills for the Cymetica Quest promo video (Google Veo 3.1), rendered from the /company mockup: 16:9,
1920 x 1080, the page's UI hidden unless the shot is about it.

    python outbox/company-promo-video/shots.py

Needs the mockup served on http://localhost:8793 (company-mock in .claude/launch.json) and Playwright's Chromium.
Writes shots/*.png next to this file (kept out of git: they are made here).
"""
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE / 'shots'
W, H = 1920, 1080
BASE = 'http://localhost:8793/index.html'
ARGS = ['--enable-unsafe-webgpu', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist']
PIN = ("#{id} {{ position: fixed !important; left: 0 !important; top: 0 !important; width: %dpx !important; height: %dpx !important;"
       " margin: 0 !important; border-radius: 0 !important; border: 0 !important; z-index: 99999 !important; }}" % (W, H))
NO_UI = "#uv-board, .b3, .b3pop, #uvstage .top, .uvlegend, #uv-panel, .tip, .uvtip { display: none !important; }"
NO_PLATES = ".b3, .b3pop { display: none !important; }"
# no example amounts in the video, as on the flyer ("nepis tam zadne priklady"): what a seat pays a month, the fees, the floor
NO_FIGURES = " .uvb-s span, .uvb-f > span, .uvb-r.open .uvb-n span, .lb-seat span, .lb-s span { visibility: hidden !important; }"
ONLY = set(sys.argv[1:])   # shot names to make again; none: all
CAMERA = """([pol, dist, sx, sy, daz]) => { const u = CO.uv, c = u.camera, t = u.controls.target, V = c.position.constructor, AZ = CO.uvGalaxy.AZ + daz;
  u.tw = null; u.follow = null; u.followAt = null;
  const sun = u.heartAt.clone(), dir = new V(Math.sin(pol) * Math.sin(AZ), Math.cos(pol), Math.sin(pol) * Math.cos(AZ));
  const right = new V(0, 1, 0).cross(dir).normalize(), up = right.clone().cross(dir.clone().negate()).normalize();
  const h = 2 * dist * Math.tan(c.fov * Math.PI / 360), w = h * c.aspect;
  const pan = right.multiplyScalar(-(sx - 0.5) * w).add(up.multiplyScalar((sy - 0.5) * h));
  t.copy(sun).add(pan); c.position.copy(sun).addScaledVector(dir, dist).add(pan); u.controls.update(); }"""
STATIONS = "(on) => { CO.uv.items.forEach((it) => { if (it.plot) it.plot.root.visible = on; }); }"


def ui(pg, css):
    # one shot's own UI rules, replacing the last shot's (they piled up: a board hidden for one shot stayed hidden)
    pg.evaluate("""(css) => { document.querySelectorAll('style[data-shot]').forEach((s) => s.remove());
      const s = document.createElement('style'); s.setAttribute('data-shot', ''); s.textContent = css; document.head.appendChild(s); }""", css)


def ready(pg, probe, wait=5):
    t0 = time.time()
    while time.time() - t0 < 120:
        if pg.evaluate(probe):
            break
        time.sleep(1)
    time.sleep(wait)


def universe(p, query, shots):
    b = p.chromium.launch(args=ARGS)
    pg = b.new_page(viewport={'width': W, 'height': H}, device_scale_factor=1)
    pg.goto(BASE + query + '#universe')
    ready(pg, "() => !!(window.CO && CO.uv && CO.uv.camera) && CO.uv.frames > 40")
    pg.add_style_tag(content=PIN.format(id='uvstage'))
    time.sleep(3)
    for name, fn in shots:
        if ONLY and name not in ONLY:
            continue
        fn(pg)
        pg.screenshot(path=str(OUT / name))
        print('wrote', name)
    b.close()


def cam(pol, dist, sx=0.5, sy=0.5, daz=0.0, stations=True, css=NO_UI):
    def go(pg):
        ui(pg, css)
        pg.evaluate(STATIONS, stations)
        for _ in range(2):
            pg.evaluate(CAMERA, [pol, dist, sx, sy, daz])
            time.sleep(3)
    return go


def fly(item, css=NO_UI, closer=1.0):
    def go(pg):
        ui(pg, css)
        pg.evaluate(STATIONS, True)
        pg.evaluate("(id) => CO.uv.flyTo(id, null, 10)", item)
        time.sleep(3)
        if closer != 1.0:
            pg.evaluate("(k) => { const u = CO.uv; u.camera.position.lerp(u.controls.target, k); u.controls.update(); }", 1 - closer)
        time.sleep(2)
    return go


def home(css):
    def go(pg):
        ui(pg, css)
        pg.evaluate(STATIONS, True)
        pg.evaluate("() => CO.uv.fit()")
        time.sleep(4)
    return go


def office(p):
    b = p.chromium.launch(args=ARGS)
    pg = b.new_page(viewport={'width': W, 'height': H}, device_scale_factor=1)
    pg.goto(BASE)
    ready(pg, "() => !!document.querySelector('#office3d canvas') && !!document.querySelector('.dpp')", wait=12)
    pg.add_style_tag(content=PIN.format(id='stage') + " #stage .strip, #stage .top, #stage .zoom, .tip { display: none !important; }")
    time.sleep(6)
    pg.screenshot(path=str(OUT / '03-office.png'))
    print('wrote 03-office.png')
    b.close()


def endcard(p):
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': W, 'height': H}, device_scale_factor=1)
    pg.goto((HERE / 'endcard.html').as_uri())
    pg.wait_for_load_state('networkidle')
    pg.evaluate('document.fonts.ready')
    pg.wait_for_timeout(700)
    pg.screenshot(path=str(OUT / '11-endcard.png'))
    print('wrote 11-endcard.png')
    b.close()


if __name__ == '__main__':
    OUT.mkdir(exist_ok=True)
    with sync_playwright() as p:
        universe(p, '?board=empty', [
            ('00-endcard-bg.png', cam(1.1, 300, 0.83, 0.5, stations=False)),
            ('01-sun.png', cam(1.12, 150, 0.5, 0.5, stations=False)),
            ('02-universe.png', cam(1.0, 520, 0.5, 0.52)),
            ('04-gem.png', fly('ad-gem', closer=0.8)),
            ('05-casino.png', fly('ad-casino', closer=0.8)),
            ('06-farmer.png', fly('ad-farmer', closer=0.75)),
            ('07-promo.png', fly('ad-promo', closer=0.8)),
            ('10-seats-open.png', home(NO_PLATES + NO_FIGURES)),
        ])
        universe(p, '', [
            ('08-board.png', home("#uv-panel, .tip { display: none !important; }" + NO_FIGURES)),
            ('09-leaderboard.png', lambda pg: (ui(pg, '.modal { z-index: 100000 !important; } #uv-panel, .tip { display: none !important; }' + NO_FIGURES), pg.evaluate("() => document.querySelector('[data-a=\"board-all\"]').click()"), time.sleep(2))),
        ])
        if not ONLY or "03-office.png" in ONLY:
            office(p)
        if not ONLY or "11-endcard.png" in ONLY:
            endcard(p)
