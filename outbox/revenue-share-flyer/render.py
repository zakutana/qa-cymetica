"""The revenue-share flyer (JOIN THE CYMETICA QUEST): first its background -- Cymetica's sun alone, small and far off,
rendered from the /company mockup's 3D Universe with every orbit, ring, station and its sky hidden, screened into
nebula.py's dark deep space -- then the flyer (index.html) over it as a 1080 x 1350 PNG at 2x.

No ring on it, ever (the operator, 2026-10-23, of the first take: "nikdy uz nedavej ty prstence na zadny letak jsou
hnusne"): the sun's own rings, the orbits and the quest ring of that take are all gone.

    python outbox/revenue-share-flyer/render.py            # both
    python outbox/revenue-share-flyer/render.py flyer      # the flyer only, over the background already made

Needs the mockup served on http://localhost:8793 (the company-mock server in .claude/launch.json) and Playwright's
Chromium, numpy and PIL. Writes space-bg.jpg and flyer-1080x1350.png next to this file; neither is kept in git (they
are made here).
"""
import sys
import time
from pathlib import Path

import numpy as np
from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import nebula  # noqa: E402  (beside this file)
W, H = 1080, 1350
# the camera: from the side and far off, so the sun is a distant star, its centre at 83 % across and 20 % down, beside
# the headline ("aby to slunce bylo vic v dalce v hlubokem vesmiru", then "jeste vic dal" twice: 360 -> 600 -> 900)
POLAR, DIST, SUN_X, SUN_Y = 1.25, 900.0, 0.85, 0.055   # high, over the glass's top edge now that it is one sheet
# the nebula's seed and density (nebula.py): dark deep space, navy and teal
SEED, STRENGTH = 7, 0.5
# the sun's light in the space round it ("z toho slunce zare"): a warm-white core glow and a wide cyan haze, in 2x px
GLOW_CORE, GLOW_WIDE = 150.0, 620.0
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
# the sun's own group (its ball, glow and rays) and the lights, nothing else, over black: no orbit, no ring of the
# sun's, no station, no light on an orbit, no sky (the deep space is nebula.py's). No pulse from the sun either.
ONLY_SUN = """() => { const u = CO.uv, sun = u.sun, par = sun.parent, scene = par.parent;
  u.pulse = () => {}; u.sharePulse = () => {};
  scene.children.forEach((c) => { if (!c.isLight && c !== par) c.visible = false; });
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
    png = HERE / 'sun.png'
    pg.screenshot(path=str(png))
    b.close()
    # the sun over the nebula: the render's own ground (its clear colour) taken back to black, then screened on
    sun = np.asarray(Image.open(png).convert('RGB'), np.float32)
    ground = np.median(np.concatenate([sun[:40, :40].reshape(-1, 3), sun[-40:, :40].reshape(-1, 3)]), axis=0)
    sun = np.clip((sun - ground) / (255 - ground) * 255, 0, 255)
    # its light round it: a warm-white glow close in, fading through the board's cyan into the dark
    hh, ww = sun.shape[:2]
    yy, xx = np.mgrid[0:hh, 0:ww].astype(np.float32)
    r = np.hypot(xx - SUN_X * ww, yy - SUN_Y * hh)
    glow = (np.exp(-(r / GLOW_CORE) ** 2)[..., None] * np.array([255, 226, 180], np.float32) * 0.55
            + np.exp(-(r / GLOW_WIDE) ** 1.4)[..., None] * np.array([40, 150, 190], np.float32) * 0.42)
    light = 255 - (255 - sun) * (255 - np.clip(glow, 0, 255)) / 255
    out = 255 - (255 - nebula.make(SEED, STRENGTH)) * (255 - light) / 255
    Image.fromarray(np.clip(out, 0, 255).astype(np.uint8), 'RGB').save(HERE / 'space-bg.jpg', quality=92, optimize=True)
    png.unlink()
    print('the render\'s ground, taken out:', ground)


def flyer(p, page='index.html'):
    """Render one page of this folder to a PNG beside it: index.html -> flyer-1080x1350.png, any other X.html -> X.png
    (the slogan variants of 2026-10-23 are slogan-v1.html ... each rendered on its own)."""
    out = HERE / ('flyer-1080x1350.png' if page == 'index.html' else Path(page).stem + '.png')
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': W, 'height': H}, device_scale_factor=2)
    pg.goto((HERE / page).as_uri())
    pg.wait_for_function("() => document.fonts.status === 'loaded'", timeout=30000)
    time.sleep(1.5)
    # the drawn frost must cover the glass as the page draws it: its projected outline against the glass's own box
    print('glass box', {k: round(v) for k, v in pg.evaluate("() => window.GLASS_BOX").items() if k in ('left', 'top', 'right', 'bottom')},
          'frost outline', {k: round(v) for k, v in pg.evaluate("() => window.GLASS_PROJ").items()})
    # and the board's content stays on the glass: the call's bottom against the glass's inner bottom, in its own box
    print('room under the call (px, glass coords):', pg.evaluate("""() => { const g = document.querySelector('.glass'), c = document.querySelector('.call');
      return g.clientHeight - parseFloat(getComputedStyle(g).paddingBottom) - (c.offsetTop + c.offsetHeight); }"""))
    pg.screenshot(path=str(out))
    b.close()
    return out


if __name__ == '__main__':
    # render.py            the background, then index.html
    # render.py flyer      index.html over the background already made
    # render.py flyer X.html   that page of this folder, to X.png
    args = sys.argv[1:]
    with sync_playwright() as p:
        if 'flyer' not in args:
            background(p)
        pages = [a for a in args if a.endswith('.html')] or ['index.html']
        for page in pages:
            print('->', flyer(p, page))
