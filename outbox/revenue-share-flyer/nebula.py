"""The flyer's deep space: a nebula in dark purple and its stars, 2160 x 2700 (the flyer at 2x), the same every time
for one seed. The operator, 2026-10-23: "aby to slunce bylo vic v dalce v hlubokem vesmiru a vic ten vesmir na
pozadi ... barvy takove temne fialove". Value noise in octaves (no scipy here), a band of cloud from the lower left
to the upper right, thickest round where the distant sun stands, dark lanes of dust, a soft shoulder so nothing
blows out, then the stars screened over it.
"""
import numpy as np
from PIL import Image, ImageFilter

W, H = 2160, 2700


def make(seed=7):
    """The nebula as an RGB float array (0..255), H x W."""
    rng = np.random.default_rng(seed)

    def noise(scale):
        # smooth value noise: a random grid `scale` px apart, upscaled bicubic, 0..1
        gw, gh = W // scale + 3, H // scale + 3
        g = (rng.random((gh, gw)) * 255).astype(np.uint8)
        im = Image.fromarray(g, 'L').resize((gw * scale, gh * scale), Image.BICUBIC)
        ox, oy = rng.integers(0, scale), rng.integers(0, scale)
        return np.asarray(im, dtype=np.float32)[oy:oy + H, ox:ox + W] / 255.0

    def fbm(base, octaves, gain=0.55):
        out, amp, tot, s = np.zeros((H, W), np.float32), 1.0, 0.0, base
        for _ in range(octaves):
            out += amp * noise(max(4, int(s)))
            tot += amp; amp *= gain; s /= 2
        return out / tot

    yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
    u, v = xx / W, yy / H
    # where the cloud lives: a band from the lower left to the upper right, thickest round the distant sun, and dark
    # where the headline stands, top left
    band = np.exp(-((v - (0.95 - 0.85 * u)) ** 2) / (2 * 0.17 ** 2))
    glow = np.exp(-(((u - 0.74) ** 2) / (2 * 0.26 ** 2) + ((v - 0.22) ** 2) / (2 * 0.2 ** 2)))
    mask = np.clip(0.75 * band + 0.65 * glow, 0, 1)
    mask *= 1 - 0.75 * np.exp(-(((u - 0.18) ** 2) / (2 * 0.22 ** 2) + ((v - 0.13) ** 2) / (2 * 0.12 ** 2)))

    big, mid, fine = fbm(700, 6), fbm(260, 5), fbm(90, 4)
    ridge = 1 - np.abs(2 * fbm(380, 5) - 1)                 # filaments
    dust = fbm(220, 5)
    d = mask * (0.5 * big + 0.35 * mid + 0.15 * fine) ** 1.8 * 1.95
    d += mask * 0.32 * ridge ** 7
    d *= 0.35 + 0.8 * np.clip((dust - 0.3) * 2.0, 0, 1)    # dark lanes
    d = np.clip(1 - np.exp(-1.9 * d), 0, 1)                 # a soft shoulder: no blown highlights

    # colour: black, indigo, deep purple, violet, a little magenta, pale lavender at the very densest
    stops = np.array([0.0, 0.18, 0.36, 0.55, 0.72, 0.86, 1.0])
    cols = np.array([[3, 2, 9], [10, 6, 28], [26, 11, 62], [52, 20, 108], [88, 34, 148], [140, 70, 190], [205, 160, 235]], np.float32)
    rgb = np.stack([np.interp(d, stops, cols[:, c]) for c in range(3)], -1)
    blue = np.clip(mask * fbm(500, 5) ** 2 * 0.9 - d * 0.6, 0, 1)   # a cold blue in the thin parts, for depth
    rgb += blue[..., None] * np.array([20, 34, 90], np.float32)

    # stars: many faint, some with a soft halo, six bright with thin spikes
    stars = np.zeros((H, W), np.float32)
    n = 9000
    sx, sy = rng.integers(0, W, n), rng.integers(0, H, n)
    np.add.at(stars, (sy, sx), np.clip(rng.pareto(2.6, n) * 0.18 + 0.05, 0, 1.4))
    starim = Image.fromarray(np.clip(stars * 255, 0, 255).astype(np.uint8), 'L')
    soft = np.asarray(starim.filter(ImageFilter.GaussianBlur(1.1)), np.float32) / 255 * 3.2
    halo = np.asarray(starim.filter(ImageFilter.GaussianBlur(5)), np.float32) / 255 * 6
    bright = np.zeros((H, W), np.float32)
    for _ in range(6):
        x, y = int(rng.integers(80, W - 80)), int(rng.integers(80, H - 80))
        r, L = rng.uniform(0.5, 1.0), int(rng.uniform(26, 70))
        for k in range(-L, L + 1):
            f = (1 - abs(k) / L) ** 3 * r
            bright[y, x + k] += f
            bright[y + k, x] += f
        bright[y - 2:y + 3, x - 2:x + 3] += 1.4 * r
    brightim = Image.fromarray(np.clip(bright * 255, 0, 255).astype(np.uint8), 'L')
    bright = (np.asarray(brightim.filter(ImageFilter.GaussianBlur(1.3)), np.float32) / 255 * 1.6
              + np.asarray(brightim.filter(ImageFilter.GaussianBlur(9)), np.float32) / 255 * 1.2)
    tint = np.where(rng.random((H, W)) < 0.5, 1.0, 0.0)[..., None]
    starcol = tint * np.array([0.9, 0.92, 1.0]) + (1 - tint) * np.array([1.0, 0.88, 1.0])
    starlight = np.clip((soft + 0.35 * halo + bright)[..., None] * starcol * 255, 0, 255)
    return 255 - (255 - np.clip(rgb, 0, 255)) * (255 - starlight) / 255   # screen
