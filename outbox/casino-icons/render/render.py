"""Render the six casino bot heads offline into outbox/casino-icons/heads/: python outbox/casino-icons/render/render.py [samples]

The table's pipeline (outbox/casino-v8/render/render.py): three.js in headless Chromium, many jittered frames averaged,
then the LEDs' bloom made here from an emit-only layer. Each head: <bot>.webp, 256 px, transparent.
"""
from __future__ import annotations

import base64
import functools
import http.server
import io
import sys
import threading
from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter
from playwright.sync_api import sync_playwright

HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "heads"
OUT.mkdir(exist_ok=True)
S = 768            # rendered, then reduced to 256
BOTS = [("a", "#00cfff"), ("b", "#00ff88"), ("c", "#3b82f6"), ("d", "#7FE6FF"), ("e", "#66ffb8"), ("f", "#93c5fd")]
TURN = -0.32       # a slight three-quarter turn, the same for all


def png(url: str) -> np.ndarray:
    return np.asarray(Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1]))).convert("RGBA")).astype("float32") / 255


def blur(a: np.ndarray, r: float) -> np.ndarray:
    chans = [np.asarray(Image.fromarray((np.clip(a[..., k], 0, 1) * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(r))) for k in range(a.shape[2])]
    return np.stack(chans, -1).astype("float32") / 255


def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(HERE))
    handler.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def main() -> int:
    samples = int(sys.argv[1]) if len(sys.argv) > 1 else 48
    only = sys.argv[2] if len(sys.argv) > 2 else ""
    srv = serve()
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist", "--enable-unsafe-swiftshader"])
        page = browser.new_page(viewport={"width": S, "height": S})
        page.on("console", lambda m: print("page:", m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: print("error:", e))
        page.goto(f"http://127.0.0.1:{srv.server_address[1]}/heads.html?s={S}&n={samples}", wait_until="load")
        page.wait_for_function("window.layers !== undefined", timeout=120000)
        for bot, hex_ in BOTS:
            if only and bot not in only:
                continue
            print("rendering", bot, flush=True)
            head = png(page.evaluate(f"layers.head('{bot}', '{hex_}', {TURN})"))
            emit = png(page.evaluate(f"layers.emit('{bot}', '{hex_}', {TURN})"))[..., :3]
            # bloom: a tight halo and a soft one, kept small so it stays round the LEDs
            bloom = np.clip(blur(emit, S / 256 * 1.6) * .7 + blur(emit, S / 256 * 5) * .6, 0, 1)
            a = head[..., 3:4]
            prem = head[..., :3] * a
            prem = 1 - (1 - prem) * (1 - bloom)                       # screen the bloom over the head
            alpha = np.clip(a + bloom.max(axis=2, keepdims=True) * (1 - a), 0, 1)
            col = np.divide(prem, alpha, out=np.zeros_like(prem), where=alpha > 1e-4)
            rgba = (np.clip(np.dstack([col, alpha]), 0, 1) * 255).astype("uint8")
            im = Image.fromarray(rgba, "RGBA").convert("RGBa").resize((256, 256), Image.LANCZOS).convert("RGBA")
            im.save(OUT / f"{bot}.webp", quality=92, method=6, exact=True)
        browser.close()
    srv.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
