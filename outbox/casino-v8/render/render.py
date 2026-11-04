"""Render the table once, offline, into outbox/casino-v8/art/: python outbox/casino-v8/render/render.py [samples]

table.webp   the object, with alpha
glow.webp    the LED line's bloom, the reflection and the pool of light on the floor, as colour and alpha
railmask.webp  the rail's top as alpha, the mask the moving light runs in
geometry.js  where the seats and the felt land, so the HTML laid over the picture sits on it
"""
from __future__ import annotations

import base64
import functools
import http.server
import io
import json
import sys
import threading
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
ART = HERE.parent / "art"
ART.mkdir(exist_ok=True)
W, H = 1600, 1100


def png(url: str) -> Image.Image:
    return Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1]))).convert("RGBA")


def blur(a: np.ndarray, r: float) -> np.ndarray:
    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype("uint8"))
    return np.asarray(im.filter(ImageFilter.GaussianBlur(r))).astype("float32") / 255


def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(HERE))
    handler.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main() -> int:
    samples = int(sys.argv[1]) if len(sys.argv) > 1 else 48
    srv = serve()
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist", "--enable-unsafe-swiftshader"])
        page = browser.new_page(viewport={"width": W, "height": H})
        page.on("console", lambda m: print("page:", m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: print("error:", e))
        page.goto(f"http://127.0.0.1:{srv.server_address[1]}/scene.html?w={W}&h={H}&n={samples}", wait_until="load")
        page.wait_for_function("window.layers !== undefined", timeout=120000)
        page.evaluate("window.ready")
        page.wait_for_timeout(300)
        geometry = page.evaluate("layers.geometry()")
        layers = {}
        for name in ("table", "emit", "railmask", "mirror"):
            print("rendering", name, flush=True)
            layers[name] = png(page.evaluate(f"layers.{name}()"))
        browser.close()
    srv.shutdown()

    table = layers["table"]
    table.save(ART / "table.webp", quality=92, method=6, exact=False)

    # the rail's top as alpha: white on the mask, nothing else
    rail = np.asarray(layers["railmask"]).astype("float32") / 255
    mask = np.clip(rail[..., 0], 0, 1) * rail[..., 3]
    out = np.zeros((*mask.shape, 4), "uint8"); out[..., :3] = 255; out[..., 3] = (mask * 255).astype("uint8")
    Image.fromarray(out).save(ART / "railmask.webp", quality=90, method=6)

    # the glow layer: bloom of the lit parts, the mirror image fading with depth, the pool on the floor. Black is nothing under screen.
    emit = np.asarray(layers["emit"]).astype("float32")[..., :3] / 255
    bloom = blur(emit, 5) * .9 + blur(emit, 16) * .9 + blur(emit, 46) * 1.0 + blur(emit, 110) * 1.1
    mir = np.asarray(layers["mirror"]).astype("float32") / 255
    mirror = mir[..., :3] * mir[..., 3:4]
    yy, xx = np.mgrid[0:H, 0:W].astype("float32")
    fx, fy = geometry["floor"][0] * W, geometry["floor"][1] * H
    # the reflection is strongest at the foot and gone a little below it
    fade = np.clip(1 - np.abs(yy - fy) / (H * .30), 0, 1) ** 1.6
    mirror = blur(mirror * fade[..., None], 3.5) * .5
    # a soft pool of cool light under the table
    d = np.sqrt(((xx - fx) / (W * .36)) ** 2 + ((yy - fy) / (H * .23)) ** 2)
    pool = np.clip(1 - d, 0, 1) ** 2.2
    col = np.array([0.0, 207 / 255, 1.0], "float32")
    side = np.clip((xx - fx) / (W * .3) * .5 + .5, 0, 1)[..., None]
    tint = col * (1 - side) + np.array([0.0, 1.0, 136 / 255], "float32") * side
    floor = pool[..., None] * tint * .17
    glow = np.clip(1 - (1 - np.clip(bloom, 0, 1)) * (1 - np.clip(mirror, 0, 1)) * (1 - floor), 0, 1)
    # as colour and alpha, not black under a blend mode: the card that carries it is its own stacking context, so screen would see nothing below
    alpha = glow.max(axis=2)
    colour = np.divide(glow, alpha[..., None], out=np.zeros_like(glow), where=alpha[..., None] > 1e-4)
    rgba = np.dstack([colour, alpha])
    Image.fromarray((np.clip(rgba, 0, 1) * 255).astype("uint8"), "RGBA").save(ART / "glow.webp", quality=88, method=6, exact=True)

    (ART / "geometry.js").write_text("window.CASINO_TABLE=" + json.dumps(geometry) + ";\n", encoding="utf8")
    print(json.dumps(geometry))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
