"""boot-sky.webp and boot-sky-2x.webp: the stars of u3d.js deepSky as one seamless tile, for what shows before the 3D has started (the loading
screens, boot.css). White with the star in its alpha, 1024 css px square, the same every time, a file for each kind of screen: his is 4K at
150 %, where a 1x tile is stretched into sand ("strasne velka density hvezd" of the first tile, measured even and gritty). The counts are
the sky's own at the entry pages' lens (SKY in u3d.js, fov 30 on a 1267 px window: 5390 dust, 390 clear and 4 bright per css Mpx), the
sizes the shader's in device px, the brightness its range in alpha.

    python outbox/company-live/bootsky.py
"""
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
DUST, CLEAR, BRIGHT = 4500, 410, 5


def tile(scale, name, seed=7):
    n = 1024 * scale
    rng = np.random.default_rng(seed)
    alpha = np.zeros((n, n), np.float32)

    def splat(x, y, peak, sigma):
        # a soft star that wraps round the tile's edges
        r = int(np.ceil(sigma * 3.5))
        xi, yi = int(np.floor(x)), int(np.floor(y))
        for j in range(yi - r, yi + r + 1):
            for i in range(xi - r, xi + r + 1):
                d2 = (i + 0.5 - x) ** 2 + (j + 0.5 - y) ** 2
                alpha[j % n, i % n] += peak * np.exp(-d2 / (2 * sigma * sigma))

    # at 1x the star is drawn at the shader's size; at 2x a little wider, since the file is shown at 0.75 on his 150 %
    k = 1.0 if scale == 1 else 1.33
    for _ in range(DUST):
        splat(rng.uniform(0, n), rng.uniform(0, n), 0.035 + 0.26 * rng.random() ** 2.6, 0.55 * k)
    for _ in range(CLEAR):
        splat(rng.uniform(0, n), rng.uniform(0, n), 0.22 + 0.28 * rng.random() ** 1.5, 0.62 * k)
    for _ in range(BRIGHT):
        x, y, p = rng.uniform(0, n), rng.uniform(0, n), 0.7 + 0.25 * rng.random()
        splat(x, y, p, 0.8 * k)
        splat(x, y, p * 0.05, 2.8 * k)
    rgba = np.zeros((n, n, 4), np.uint8)
    rgba[..., 0], rgba[..., 1], rgba[..., 2] = 232, 244, 255
    rgba[..., 3] = np.round(np.clip(alpha, 0, 1) * 255).astype(np.uint8)
    out = os.path.join(HERE, name)
    Image.fromarray(rgba, 'RGBA').save(out, quality=88, alpha_quality=88, method=6)
    print(out, os.path.getsize(out) // 1024, 'KB')


tile(1, 'boot-sky.webp')
tile(2, 'boot-sky-2x.webp')
