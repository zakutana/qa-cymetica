"""The revenue-share flyer (BE EARLY.): first its background (Cymetica's sun alone, big, top right, rendered from the
/company mockup's 3D Universe with every orbit, ring, station and nebula hidden), then the flyer (index.html) over it
as a 1080 x 1350 PNG at 2x.

No ring on it, ever (the operator, 2026-10-23, of the first take: "nikdy uz nedavej ty prstence na zadny letak jsou
hnusne"): the sun's own rings, the orbits and the quest ring of that take are all gone.

    python outbox/revenue-share-flyer/render.py            # both
    python outbox/revenue-share-flyer/render.py flyer      # the flyer only, over the background already made

Needs the mockup served on http://localhost:8793 (the company-mock server in .claude/launch.json) and Playwright's
Chromium. Writes sun-bg.jpg and flyer-1080x1350.png next to this file; neither is kept in git (they are made here).
"""
import sys
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
W, H = 1080, 1350
# the camera: from the side, close, the sun's centre at 80 % across and 22 % down, beside the headline, low enough that
# its lower glow lies behind the glass's top right and comes through it frosted
POLAR, DIST, SUN_X, SUN_Y = 1.25, 150.0, 0.8, 0.22
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
# keep the lights, the sky's dark sphere and its stars, and the sun's own group (its ball, glow and rays); the sun's
# rings beside it, every orbit, station, light on an orbit and the nebula go. No pulse from the sun either.
ONLY_SUN = """() => { const u = CO.uv, sun = u.sun, par = sun.parent, scene = par.parent;
  u.pulse = () => {}; u.sharePulse = () => {};
  const sky = (d) => d.geometry && d.geometry.parameters && d.geometry.parameters.radius === 4200;
  scene.children.forEach((c) => {
    if (c.isLight || c === par) return;
    if (c.children.some(sky)) { c.children.forEach((d) => { d.visible = d.isPoints || sky(d); }); return; }
    c.visible = false; });
  par.children.forEach((c) => { c.visible = c === sun; }); }"""


def background(p):
    b = p.chromium.launch(args=['--enable-unsafe-webgpu', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': W, 'height': H}, device_scale_factor=2)
    pg.goto('http://localhost:8793/index.html?board=empty#universe')
    t0 = time.time()
    while time.time() - t0 < 120:
        if pg.evaluate("() => !!(window.CO && CO.uv && CO.uv.camera) && CO.uv.frames > 40"):
            break
        time.sleep(1)
    pg.add_style_tag(content=HIDE)
    for _ in range(3):
        pg.evaluate(CAMERA, [POLAR, DIST, SUN_X, SUN_Y])
        pg.evaluate(ONLY_SUN)
        time.sleep(4)
    png = HERE / 'sun-bg.png'
    pg.screenshot(path=str(png))
    b.close()
    Image.open(png).convert('RGB').save(HERE / 'sun-bg.jpg', quality=92, optimize=True)
    png.unlink()


def flyer(p):
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': W, 'height': H}, device_scale_factor=2)
    pg.goto((HERE / 'index.html').as_uri())
    pg.wait_for_function("() => document.fonts.status === 'loaded'", timeout=30000)
    time.sleep(1.5)
    # the drawn frost must cover the glass as the page draws it: its projected outline against the glass's own box
    print('glass box', {k: round(v) for k, v in pg.evaluate("() => window.GLASS_BOX").items() if k in ('left', 'top', 'right', 'bottom')},
          'frost outline', {k: round(v) for k, v in pg.evaluate("() => window.GLASS_PROJ").items()})
    pg.screenshot(path=str(HERE / 'flyer-1080x1350.png'))
    b.close()


if __name__ == '__main__':
    with sync_playwright() as p:
        if 'flyer' not in sys.argv[1:]:
            background(p)
        flyer(p)
    print('->', HERE / 'flyer-1080x1350.png')
