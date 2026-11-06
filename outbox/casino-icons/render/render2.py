"""Render five more directions of the six casino bot heads: python outbox/casino-icons/render/render2.py [samples] [styles] [bots]

heads2.html, on heads.html's pipeline (v1 stays heads.html + render.py). Writes heads/<style>/<bot>.webp, 256 px.
Differences from v1: the LEDs' exact colour is put back from the emit layer (ACES and the bloom washed the pale tints to white),
the bloom only lands outside the LEDs, and 'portrait' gets a round seat with a backlight in the bot's colour baked in.
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
S = 768
BOTS = [("a", "#00cfff"), ("b", "#00ff88"), ("c", "#3b82f6"), ("d", "#7FE6FF"), ("e", "#66ffb8"), ("f", "#93c5fd")]
STYLES = ["ceramic", "glass", "neon", "portrait", "mecha"]
TURN = -0.32
SEAT = np.array([7, 11, 18], "float32") / 255     # #070b12


def png(url: str) -> np.ndarray:
    return np.asarray(Image.open(io.BytesIO(base64.b64decode(url.split(",", 1)[1]))).convert("RGBA")).astype("float32") / 255


def blur(a: np.ndarray, r: float) -> np.ndarray:
    chans = [np.asarray(Image.fromarray((np.clip(a[..., k], 0, 1) * 255).astype("uint8")).filter(ImageFilter.GaussianBlur(r))) for k in range(a.shape[2])]
    return np.stack(chans, -1).astype("float32") / 255


def hexrgb(h: str) -> np.ndarray:
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], "float32") / 255


def serve():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(HERE))
    handler.log_message = lambda *a, **k: None
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def compose(style: str, head: np.ndarray, emit: np.ndarray, hex_: str) -> np.ndarray:
    col = hexrgb(hex_)
    m = np.clip(emit.max(axis=2, keepdims=True) / col.max(), 0, 1)          # where an LED is, and how much of the pixel
    a = head[..., 3:4]
    prem = head[..., :3] * a * (1 - m) + emit                                  # the LED in its exact colour
    k = S / 256
    bloom = np.clip(blur(emit, 1.6 * k) * .7 + blur(emit, 5 * k) * .6, 0, 1) * (1 - m)
    prem = 1 - (1 - prem) * (1 - bloom)
    alpha = np.clip(a + bloom.max(axis=2, keepdims=True) * (1 - a), 0, 1)
    if style == "portrait":
        # a round seat: dark, lit from behind in the bot's colour, the head over it, cut to a circle
        yy, xx = np.mgrid[0:S, 0:S].astype("float32") / S
        d = np.sqrt((xx - .5) ** 2 + (yy - .36) ** 2)
        glow = np.clip(1 - d / .62, 0, 1) ** 1.4
        bg = SEAT + (col * .6 - SEAT) * glow[..., None]
        prem = prem + bg * (1 - alpha)
        alpha = np.ones_like(alpha)
        r = np.sqrt((xx - .5) ** 2 + (yy - .5) ** 2) * S
        alpha = alpha * np.clip(S / 2 - 1 - r, 0, 1)[..., None]
        prem = prem * np.clip(S / 2 - 1 - r, 0, 1)[..., None]
    colr = np.divide(prem, alpha, out=np.zeros_like(prem), where=alpha > 1e-4)
    return (np.clip(np.dstack([colr, alpha]), 0, 1) * 255).astype("uint8")


def main() -> int:
    samples = int(sys.argv[1]) if len(sys.argv) > 1 else 48
    styles = sys.argv[2].split(",") if len(sys.argv) > 2 and sys.argv[2] != "all" else STYLES
    only = sys.argv[3] if len(sys.argv) > 3 else ""
    srv = serve()
    with sync_playwright() as p:
        browser = p.chromium.launch(args=["--use-angle=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist", "--enable-unsafe-swiftshader"])
        page = browser.new_page(viewport={"width": S, "height": S})
        page.on("console", lambda m: print("page:", m.text) if m.type == "error" else None)
        page.on("pageerror", lambda e: print("error:", e))
        page.goto(f"http://127.0.0.1:{srv.server_address[1]}/heads2.html?s={S}&n={samples}", wait_until="load")
        page.wait_for_function("window.layers !== undefined", timeout=120000)
        for style in styles:
            (OUT / style).mkdir(parents=True, exist_ok=True)
            for bot, hex_ in BOTS:
                if only and bot not in only:
                    continue
                print("rendering", style, bot, flush=True)
                head = png(page.evaluate(f"layers.head('{style}', '{bot}', '{hex_}', {TURN})"))
                emit = png(page.evaluate(f"layers.emit('{style}', '{bot}', '{hex_}', {TURN})"))[..., :3]
                rgba = compose(style, head, emit, hex_)
                im = Image.fromarray(rgba, "RGBA").convert("RGBa").resize((256, 256), Image.LANCZOS).convert("RGBA")
                im.save(OUT / style / f"{bot}.webp", quality=92, method=6, exact=True)
        browser.close()
    srv.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
