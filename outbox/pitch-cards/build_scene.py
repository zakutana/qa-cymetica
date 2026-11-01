"""The Den, from the render of Nexus at his holographic chart (outbox/quest/gen/lab-16x9.png, the original, 2560 x 1440):

    python outbox/pitch-cards/build_scene.py

scene.webp   the room alone: the baked glass pane painted out, Nexus gone, so it can fill any screen behind him
nexus.webp   Nexus cut out by hand-traced outline (2560 x 1440 coordinates below), to stand in FRONT of the card: the card
             sits under his finger and slides behind him when it is swiped to him. Left edge x=NX, top y=NY in the render.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = Path(__file__).resolve().parent
SRC = HERE.parent / "quest" / "gen" / "lab-16x9.png"
NX, NY = 1640, 280

# Nexus's outline in the render's pixels, down his face, over the collar and shoulder, along the arm to the fingertip,
# back under the fingers and thumb, down the arm and body to the floor; the far side is loose, nothing lingers there.
OUTLINE = [
    (2080, 301), (2030, 310), (1985, 332), (1955, 360), (1935, 390), (1925, 425), (1919, 465), (1921, 500), (1927, 545),
    (1940, 590), (1955, 635), (1967, 675), (1977, 692), (1995, 704), (2025, 705), (2042, 697), (2044, 712), (2040, 733),
    (2020, 742), (2005, 762), (1960, 775), (1922, 800),
    (1903, 777), (1887, 750), (1870, 727), (1853, 703), (1840, 690), (1827, 677), (1810, 667), (1800, 663), (1788, 655),
    (1773, 640), (1760, 625), (1752, 620), (1722, 598), (1715, 595), (1683, 587), (1670, 585), (1664, 590), (1664, 597),
    (1673, 610), (1703, 620), (1708, 628), (1717, 638), (1730, 643), (1728, 653), (1700, 697), (1697, 707), (1698, 713),
    (1687, 714), (1673, 720), (1669, 730), (1677, 743), (1690, 753), (1710, 762), (1720, 768), (1740, 783), (1755, 793),
    (1787, 815), (1800, 823), (1820, 840), (1840, 860), (1853, 865), (1858, 873), (1867, 887), (1867, 925), (1865, 935),
    (1862, 1050), (1855, 1120), (1852, 1160), (1855, 1180), (1842, 1200), (1835, 1225), (1805, 1280), (1780, 1340),
    (1765, 1400), (1760, 1440),
    (2305, 1440), (2302, 1420), (2285, 1360), (2278, 1320), (2280, 1285), (2298, 1250), (2302, 1210), (2310, 1170),
    (2328, 1130), (2352, 1090), (2378, 1045), (2400, 1000), (2416, 955), (2420, 938), (2445, 915), (2456, 890), (2450, 850),
    (2430, 815), (2400, 795), (2360, 783), (2330, 775), (2300, 757), (2245, 719), (2205, 720), (2205, 600), (2222, 570),
    (2227, 540), (2245, 460), (2242, 415), (2220, 360), (2185, 325), (2140, 310),
]
SEAM = 1300                          # right of this column the room is its own left side mirrored: Nexus stood there
MOON = (1122, 619, 125)              # x, y, radius with its halo


def plate(a: np.ndarray) -> np.ndarray:
    """Paint out the glass pane: each row blends from the room left of it to the room right of it, which keeps the
    window's horizontal bands; a light vertical blur takes out the row noise, and a few dim stars go back in."""
    out = a.astype(np.float32)
    x0, x1, y0, y1 = 1310, 1835, 290, 1000
    dark = a[540:560, 1825:1845].reshape(-1, 3).mean(axis=0)   # the night behind his hand, for the rows where the hand is on the right
    fill = np.zeros((y1 - y0, x1 - x0, 3), np.float32)
    ramp = np.linspace(0, 1, x1 - x0)[None, :, None]
    for y in range(y0, y1):
        left = a[y, x0 - 14:x0].reshape(-1, 3).mean(axis=0)
        right = dark if 560 <= y <= 900 else a[y, x1:x1 + 14].reshape(-1, 3).mean(axis=0)
        fill[y - y0] = left * (1 - ramp[0]) + right * ramp[0]
    k = 9
    fill = np.stack([np.apply_along_axis(lambda c: np.convolve(np.pad(c, k, mode="edge"), np.ones(2 * k + 1) / (2 * k + 1), mode="valid"), 0, fill[..., i]) for i in range(3)], -1)
    rng = np.random.default_rng(7)
    for _ in range(90):
        sx, sy = rng.integers(0, x1 - x0), rng.integers(190, 640)   # the window's rows
        fill[sy, sx] += rng.uniform(25, 90)
    # a soft edge, so the join does not show
    m = np.ones(fill.shape[:2], np.float32)
    e = 24
    m[:, :e] *= np.linspace(0, 1, e)
    m[:, -e:] *= np.linspace(1, 0, e)
    m[:e, :] *= np.linspace(0, 1, e)[:, None]
    m[-e:, :] *= np.linspace(1, 0, e)[:, None]
    out[y0:y1, x0:x1] = out[y0:y1, x0:x1] * (1 - m[..., None]) + fill * m[..., None]
    return np.clip(out, 0, 255).astype(np.uint8)


def room(a: np.ndarray) -> np.ndarray:
    """The room with nobody in it, so it can fill any screen while Nexus and the card keep their own size. Everything right
    of SEAM is the left side mirrored, moon taken out of the copy: an octagonal window that closes, and a second desk."""
    p = plate(a).astype(np.float32)
    clean = p.copy()
    mx, my, r = MOON
    x0, x1, y0, y1 = mx - r, mx + r, my - r, my + r
    ramp = np.linspace(0, 1, x1 - x0)[:, None]
    for y in range(y0, y1):
        clean[y, x0:x1] = clean[y, x0 - 6:x0].mean(axis=0) * (1 - ramp) + clean[y, x1:x1 + 6].mean(axis=0) * ramp
    yy, xx = np.mgrid[y0:y1, x0:x1]
    m = np.clip((r - np.hypot(xx - mx, yy - my)) / 40, 0, 1)[..., None]
    clean[y0:y1, x0:x1] = p[y0:y1, x0:x1] * (1 - m) + clean[y0:y1, x0:x1] * m
    p[:, SEAM:] = clean[:, SEAM - 1:SEAM - 1 - (2560 - SEAM):-1]
    return np.clip(p, 0, 255).astype(np.uint8)


def nexus(a: np.ndarray) -> Image.Image:
    """Nexus alone: the outline feathered a little, and the baked pane's rim taken off his hand."""
    b = a.astype(np.float32).copy()
    for y in range(600, 900):
        l, r = 1783, 1801
        t = np.linspace(0, 1, r - l)[:, None]
        b[y, l:r] = b[y, l] * (1 - t) + b[y, r] * t
    # the render was enlarged to 2560 and is soft at this size: the edges of his shell are brought back, finest first
    im = Image.fromarray(np.clip(b, 0, 255).astype(np.uint8)).filter(ImageFilter.UnsharpMask(1.5, 110, 2)).filter(ImageFilter.UnsharpMask(4, 35, 3)).convert("RGBA")
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).polygon(OUTLINE, fill=255)
    mask = mask.filter(ImageFilter.GaussianBlur(1.1))
    im.putalpha(mask)
    return im.crop((NX, NY, 2560, 1440))


if __name__ == "__main__":
    src = np.asarray(Image.open(SRC).convert("RGB"))
    Image.fromarray(room(src)).save(HERE / "scene.webp", quality=92, method=6)
    nexus(src).save(HERE / "nexus.webp", quality=96, method=6)
    Image.fromarray(src[310:690, 1880:2260]).resize((192, 192), Image.LANCZOS).save(HERE / "nexus-face.webp", quality=92, method=6)
    for f in ("scene.webp", "nexus.webp", "nexus-face.webp"):
        print(f, (HERE / f).stat().st_size // 1024, "KB")
