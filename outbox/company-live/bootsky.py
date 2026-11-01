"""boot-sky.webp: the flyer's stars as one seamless tile, for what shows before the 3D has started (the loading screens, boot.css) and
behind the page's panels (style.css). White with the star in its alpha, 512 x 512, the same every time. Against the flyer at 1x
(outbox/revenue-share-flyer): a dust of faint stars and a few clear ones, none bright, since a bright one would show the tile's repeat.

    python outbox/company-live/bootsky.py
"""
import os

import numpy as np
from PIL import Image

N = 512
HERE = os.path.dirname(os.path.abspath(__file__))
rng = np.random.default_rng(7)
alpha = np.zeros((N, N), np.float32)


def splat(x, y, peak, sigma):
    # a soft star that wraps round the tile's edges
    r = int(np.ceil(sigma * 3.5))
    xi, yi = int(np.floor(x)), int(np.floor(y))
    for j in range(yi - r, yi + r + 1):
        for i in range(xi - r, xi + r + 1):
            d2 = (i + 0.5 - x) ** 2 + (j + 0.5 - y) ** 2
            alpha[j % N, i % N] += peak * np.exp(-d2 / (2 * sigma * sigma))


for _ in range(2000):                       # the dust
    splat(rng.uniform(0, N), rng.uniform(0, N), 0.024 + 0.2 * rng.random() ** 2.0, 0.62)
for _ in range(150):                        # the clear ones, each with a trace of halo
    x, y, p = rng.uniform(0, N), rng.uniform(0, N), 0.2 + 0.2 * rng.random() ** 1.5
    splat(x, y, p, 0.72)
    splat(x, y, p * 0.05, 2.6)
a = np.clip(alpha, 0, 1)
rgba = np.zeros((N, N, 4), np.uint8)
rgba[..., 0], rgba[..., 1], rgba[..., 2] = 232, 244, 255
rgba[..., 3] = np.round(a * 255).astype(np.uint8)
out = os.path.join(HERE, 'boot-sky.webp')
Image.fromarray(rgba, 'RGBA').save(out, quality=90, alpha_quality=92, method=6)
print(out, os.path.getsize(out) // 1024, 'KB')
