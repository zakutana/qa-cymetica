"""The Orbit Rush flyer: first its background (Cymetica's sun from above, its orbits round it, rendered from the
/company mockup's 3D Universe with every station hidden) and the screen path of one real orbit, then the flyer
(index.html) over them as a 1080 x 1350 PNG at 2x. The five steps sit on that orbit, so the quest ring is the
Universe's own innermost orbit (r = 90), not a circle drawn near it.

    python outbox/orbit-rush-flyer/render.py            # both
    python outbox/orbit-rush-flyer/render.py flyer      # the flyer only, over the background already made

Needs the mockup served on http://localhost:8793 (the company-mock server in .claude/launch.json) and Playwright's
Chromium. Writes universe-bg.jpg, orbit.js and flyer-1080x1350.png next to this file; none is kept in git (they are
made here).
"""
import json
import sys
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
W, H = 1080, 1350
# the camera: 34 degrees from straight down, the sun on the centre line a little below the middle, far enough that
# the quest orbit (r = 90, 666 px across) leaves room for a card on either side
POLAR, DIST, SUN_X, SUN_Y, QUEST_R = 0.6, 350.0, 0.5, 0.585, 90
# a ring between the sun's dashed ring and its outer one, for the words round the sun
LABEL_R = 50
NO_STATIONS = "() => { CO.uv.items.forEach((it) => { if (it.plot) it.plot.root.visible = false; }); }"
# no pulse from the sun to a station: a line from the sun to nowhere once the stations are hidden
NO_PULSE = "() => { CO.uv.pulse = () => {}; CO.uv.sharePulse = () => {}; }"
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
# the quest orbit and the label ring on screen: 720 points round each, in CSS px of the 1080 x 1350 frame, and the
# sun's centre
PROJECT = """([r, lr]) => { const u = CO.uv, c = u.camera, V = c.position.constructor; c.updateMatrixWorld(); c.updateProjectionMatrix();
  const ring = (rr) => { const pts = [];
    for (let k = 0; k < 720; k++) { const a = k / 720 * Math.PI * 2, v = new V(Math.sin(a) * rr, 0, Math.cos(a) * rr).project(c);
      pts.push([+((v.x + 1) / 2 * %d).toFixed(2), +((1 - v.y) / 2 * %d).toFixed(2)]); }
    return pts; };
  const s = u.heartAt.clone().project(c);
  return { pts: ring(r), label: ring(lr), sun: [+((s.x + 1) / 2 * %d).toFixed(2), +((1 - s.y) / 2 * %d).toFixed(2)] }; }""" % (W, H, W, H)


def background(p):
    # the board empty (?board=empty), so no revenue-share board stands over the picture
    b = p.chromium.launch(args=['--enable-unsafe-webgpu', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'])
    pg = b.new_page(viewport={'width': W, 'height': H}, device_scale_factor=2)
    pg.goto('http://localhost:8793/index.html?board=empty#universe')
    t0 = time.time()
    while time.time() - t0 < 120:
        if pg.evaluate("() => !!(window.CO && CO.uv && CO.uv.camera) && CO.uv.frames > 40"):
            break
        time.sleep(1)
    pg.evaluate(NO_PULSE)
    time.sleep(4)
    pg.add_style_tag(content=HIDE)
    time.sleep(2)
    for _ in range(2):
        pg.evaluate(CAMERA, [POLAR, DIST, SUN_X, SUN_Y])
        pg.evaluate(NO_STATIONS)
        time.sleep(4)
    # every pulse already in flight has ended (the longest runs about five seconds)
    time.sleep(4)
    orbit = pg.evaluate(PROJECT, [QUEST_R, LABEL_R])
    (HERE / 'orbit.js').write_text('window.ORBIT = ' + json.dumps(orbit) + ';\n', encoding='utf-8')
    png = HERE / 'universe-bg.png'
    pg.screenshot(path=str(png))
    b.close()
    Image.open(png).convert('RGB').save(HERE / 'universe-bg.jpg', quality=92, optimize=True)
    png.unlink()


def flyer(p):
    b = p.chromium.launch()
    pg = b.new_page(viewport={'width': W, 'height': H}, device_scale_factor=2)
    pg.goto((HERE / 'index.html').as_uri())
    pg.wait_for_function("() => document.fonts.status === 'loaded' && window.FLYER_READY === true", timeout=30000)
    time.sleep(1)
    pg.screenshot(path=str(HERE / 'flyer-1080x1350.png'))
    b.close()


if __name__ == '__main__':
    with sync_playwright() as p:
        if 'flyer' not in sys.argv[1:]:
            background(p)
        flyer(p)
    print('->', HERE / 'flyer-1080x1350.png')
