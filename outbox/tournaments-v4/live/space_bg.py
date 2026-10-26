"""The page's backdrop: Cymetica's own 3D Universe, rendered the way the Cymetica Quest flyer's background is
(outbox/company-flyer/render.py: the /company mockup with every station hidden), wide, with the sun far off in the
top-right corner so the table and the standings sit over dark space.

The operator, 2026-10-26, after six rounds of space drawn by hand in CSS gradients and SVG ellipses ("je to trash ...
nejake ty pruhy tam nechapu"): he had pointed at the flyer twice ("koukni na nas letak o cymetica quest tam to bylo
top"), and the flyer is not drawn, it is this render.

    python outbox/tournaments-v4/live/space_bg.py      # writes space-bg.jpg beside this file

Needs the mockup served on http://localhost:8793 (company-mock in .claude/launch.json) and Playwright's Chromium.
"""
import importlib.util
import sys
import time
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("flyer", HERE.parents[1] / "company-flyer" / "render.py")
flyer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(flyer)

W, H = 1280, 720            # rendered at 2x: 2560 x 1440
# the sun far away in the top-right corner, the orbits sweeping under it across the page
POLAR, DIST, SUN_X, SUN_Y = float(sys.argv[1]) if len(sys.argv) > 1 else 1.12, \
    float(sys.argv[2]) if len(sys.argv) > 2 else 320.0, \
    float(sys.argv[3]) if len(sys.argv) > 3 else 0.86, \
    float(sys.argv[4]) if len(sys.argv) > 4 else 0.2
HIDE = flyer.HIDE.replace("width: %dpx" % flyer.W, "width: %dpx" % W).replace("height: %dpx" % flyer.H, "height: %dpx" % H)


def main():
    with sync_playwright() as p:
        b = p.chromium.launch(args=['--enable-unsafe-webgpu', '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
                                    '--ignore-gpu-blocklist'])
        pg = b.new_page(viewport={'width': W, 'height': H}, device_scale_factor=2)
        pg.goto('http://localhost:8793/index.html?board=empty#universe')
        t0 = time.time()
        while time.time() - t0 < 180:
            if pg.evaluate("() => !!(window.CO && CO.uv && CO.uv.camera) && CO.uv.frames > 40"):
                break
            time.sleep(1)
        time.sleep(5)
        pg.add_style_tag(content=HIDE)
        time.sleep(3)
        for _ in range(2):
            pg.evaluate(flyer.CAMERA, [POLAR, DIST, SUN_X, SUN_Y])
            pg.evaluate(flyer.NO_STATIONS)
            time.sleep(4)
        png = HERE / 'space-bg.png'
        pg.screenshot(path=str(png))
        b.close()
    Image.open(png).convert('RGB').save(HERE / 'space-bg.jpg', quality=86, optimize=True, progressive=True)
    png.unlink()
    print('wrote', HERE / 'space-bg.jpg', (HERE / 'space-bg.jpg').stat().st_size // 1024, 'KB', 'camera', POLAR, DIST, SUN_X, SUN_Y)


if __name__ == '__main__':
    main()
