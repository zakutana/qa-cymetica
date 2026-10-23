"""The Cymetica Quest flyer, made again from scratch: first its background (Cymetica's sun and its orbits, rendered from
the /company mockup's 3D Universe with every station hidden), then the flyer itself (index.html) as a 1080 x 1350 PNG at 2x.

    python outbox/company-flyer/render.py            # both
    python outbox/company-flyer/render.py flyer      # the flyer only, over the background already made

Needs the mockup served on http://localhost:8793 (the company-mock server in .claude/launch.json) and Playwright's
Chromium. Writes universe-bg.jpg and flyer-1080x1350.png next to this file; neither is kept in git (they are made here).
"""
import sys
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
W, H = 1080, 1350
# the camera: 63 degrees from straight down, close to the sun, the sun at the right edge a third of the way down -- where
# the first take's green light was ("do pozadi dej to slunce cymeticy ... misto toho zeleneho svetla")
POLAR, DIST, SUN_X, SUN_Y = 1.1, 190.0, 0.79, 0.34
# no company on it ("ty firmy tam nechci videt"): every station, product and slot hidden; the sun, the orbits and the
# lights passing along them stay
NO_STATIONS = "() => { CO.uv.items.forEach((it) => { if (it.plot) it.plot.root.visible = false; }); }"
HIDE = ("#uv-board, .b3, .b3pop, #uvstage .top, .uvlegend, #uv-panel, .tip, .uvtip { display: none !important; }"
        "#uvstage { position: fixed !important; left: 0 !important; top: 0 !important; width: %dpx !important; height: %dpx !important;"
        " margin: 0 !important; border-radius: 0 !important; border: 0 !important; z-index: 99999 !important; }" % (W, H))
CAMERA = """([pol, dist, sx, sy]) => { const u = CO.uv, c = u.camera, t = u.controls.target, V = c.position.constructor, AZ = CO.uvGalaxy.AZ;
  u.tw = null; u.follow = null; u.followAt = null;
  const sun = u.heartAt.clone(), dir = new V(Math.sin(pol) * Math.sin(AZ), Math.cos(pol), Math.sin(pol) * Math.cos(AZ));
  const right = new V(0, 1, 0).cross(dir).normalize(), up = right.clone().cross(dir.clone().negate()).normalize();
  const h = 2 * dist * Math.tan(c.fov * Math.PI / 360), w = h * c.aspect;
  const pan = right.multiplyScalar(-(sx - 0.5) * w).add(up.multiplyScalar((sy - 0.5) * h));
  t.copy(sun).add(pan); c.position.copy(sun).addScaledVector(dir, dist).add(pan); u.controls.update(); }"""


def background(p):
    # the board empty (?board=empty), so no revenue-share pulse crosses the picture
    b = p.chromium.launch(args=['--enable-unsafe-webgpu', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': W, 'height': H}, device_scale_factor=2)
    pg.goto('http://localhost:8793/index.html?board=empty#universe')
    t0 = time.time()
    while time.time() - t0 < 120:
        if pg.evaluate("() => !!(window.CO && CO.uv && CO.uv.camera) && CO.uv.frames > 40"):
            break
        time.sleep(1)
    time.sleep(5)
    pg.add_style_tag(content=HIDE)
    time.sleep(3)
    for _ in range(2):
        pg.evaluate(CAMERA, [POLAR, DIST, SUN_X, SUN_Y])
        pg.evaluate(NO_STATIONS)
        time.sleep(4)
    png = HERE / 'universe-bg.png'
    pg.screenshot(path=str(png))
    b.close()
    Image.open(png).convert('RGB').save(HERE / 'universe-bg.jpg', quality=90, optimize=True)
    png.unlink()


def flyer(p):
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': W, 'height': H}, device_scale_factor=2)
    pg.goto((HERE / 'index.html').as_uri())
    pg.wait_for_load_state('networkidle')
    pg.evaluate('document.fonts.ready')
    pg.wait_for_timeout(700)
    pg.screenshot(path=str(HERE / 'flyer-1080x1350.png'))
    b.close()


if __name__ == '__main__':
    with sync_playwright() as p:
        if 'flyer' not in sys.argv[1:]:
            background(p)
        flyer(p)
    print('wrote', HERE / 'universe-bg.jpg', 'and', HERE / 'flyer-1080x1350.png')
