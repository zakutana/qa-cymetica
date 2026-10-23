"""The flyer's deep space: a nebula in dark purple and its stars, 2160 x 2700 (the flyer at 2x), the same every time
for one seed. The operator, 2026-10-23: "aby to slunce bylo vic v dalce v hlubokem vesmiru a vic ten vesmir na
pozadi ... barvy takove temne fialove". Value noise in octaves (no scipy here), a band of cloud from the lower left
to the upper right, thickest round where the distant sun stands, dark lanes of dust, a soft shoulder so nothing
blows out, then the stars screened over it.
"""
import numpy as np
from PIL import Image, ImageFilter

W, H = 2160, 2700


def make(seed=7, strength=1.0):
    """The nebula as an RGB float array (0..255), H x W. `strength` scales the cloud's density: below 1 the space is
    darker and the purple only a trace ("vic ten deep vesmir tmavsi jen s minimem te fialove", 2026-10-23)."""
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
    d = np.clip(1 - np.exp(-1.9 * d * strength), 0, 1)      # a soft shoulder: no blown highlights

    # colour: the site's own dark, then deep navy and teal (the board's cyan, far off), a trace of violet only where the
    # cloud is densest ("top slad vsechny barvy", 2026-10-23: the purple of the fifth take fought the board's cyan)
    stops = np.array([0.0, 0.18, 0.36, 0.55, 0.72, 0.86, 1.0])
    cols = np.array([[2, 3, 8], [5, 10, 22], [8, 20, 40], [14, 36, 62], [28, 54, 96], [62, 74, 140], [150, 165, 220]], np.float32)
    rgb = np.stack([np.interp(d, stops, cols[:, c]) for c in range(3)], -1)
    teal = np.clip(mask * fbm(500, 5) ** 2 * 0.9 * strength - d * 0.6, 0, 1)   # a cold teal in the thin parts, for depth
    rgb += teal[..., None] * np.array([8, 40, 58], np.float32)

    # stars, as space has them: thousands of faint ones, thicker along the cloud's band; hundreds of clear ones with a
    # little halo; a dozen bright ones with short spikes. Each its own colour: white, blue-white, a few warm.
    palette = np.array([[1.0, 1.0, 1.0], [0.82, 0.9, 1.0], [0.78, 0.95, 1.0], [1.0, 0.92, 0.82]], np.float32)

    def scatter(n, lo, hi, power):
        xs, ys = rng.integers(0, W, n * 2), rng.integers(0, H, n * 2)
        keep = rng.random(n * 2) < (0.35 + 0.65 * mask[ys, xs])
        xs, ys = xs[keep][:n], ys[keep][:n]
        b = lo + (hi - lo) * rng.random(len(xs)) ** power
        c = palette[rng.choice(len(palette), len(xs), p=[0.45, 0.3, 0.15, 0.1])]
        layer = np.zeros((H, W, 3), np.float32)
        for ch in range(3):
            np.add.at(layer[..., ch], (ys, xs), b * c[:, ch])
        return layer

    def blur(layer, r):
        out = np.empty_like(layer)
        for ch in range(3):
            im = Image.fromarray(np.clip(layer[..., ch] * 255, 0, 255).astype(np.uint8), 'L').filter(ImageFilter.GaussianBlur(r))
            out[..., ch] = np.asarray(im, np.float32) / 255
        return out

    faint = scatter(26000, 0.06, 0.55, 3.0)
    clear = scatter(1100, 0.5, 1.0, 1.5)
    light = blur(faint, 0.75) * 3.0 + blur(clear, 1.1) * 4.5 + blur(clear, 5) * 5.0
    spikes = np.zeros((H, W), np.float32)
    for _ in range(12):
        x, y = int(rng.integers(90, W - 90)), int(rng.integers(90, H - 90))
        r, L = rng.uniform(0.45, 1.0), int(rng.uniform(20, 52))
        for k in range(-L, L + 1):
            f = (1 - abs(k) / L) ** 4 * r
            spikes[y, x + k] += f
            spikes[y + k, x] += f
        spikes[y - 2:y + 3, x - 2:x + 3] += 1.6 * r
    spikes = np.repeat(spikes[..., None], 3, -1) * np.array([0.92, 0.97, 1.0], np.float32)
    light += blur(spikes, 1.2) * 1.7 + blur(spikes, 10) * 1.6
    starlight = np.clip(light * 255, 0, 255)
    return 255 - (255 - np.clip(rgb, 0, 255)) * (255 - starlight) / 255   # screen
