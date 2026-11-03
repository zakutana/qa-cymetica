"""The page keys most clips (black to clear, anim.js KEY_FS), so what matters is the picture AFTER the key, laid over a dark sky.
Compare original and slimmed clip through the same key: SSIM of the composite, and the error in the dark, hazy parts (where a codec blocks and bands first).
  python keycheck.py <name> <slim file> [glow]          (slim file in scratchpad/slim/final; glow = the Universe's key)"""
import shutil
import sys
from pathlib import Path

import numpy as np
from PIL import Image

import slim

SKY = np.array([10, 14, 26], np.float32) / 255
OUT = slim.OUT


def smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def keyed(rgb, glow):
    c = rgb.astype(np.float32) / 255
    m = c.max(axis=2)
    lo, hi, kg = (0.0, 0.45, 1.0) if glow else (0.025, 0.12, 0.0)
    a = smooth(lo, hi, m)
    c = c * (1 + (smooth(0.006, 0.024, m) - 1) * kg)[..., None]
    out_rgb = np.minimum(c, a[..., None]) * (1 - kg) + c * kg
    comp = out_rgb + (1 - a)[..., None] * SKY
    return np.clip(comp * 255, 0, 255), m


def frames(f, tag):
    d = OUT / ('kf-' + tag)
    shutil.rmtree(d, ignore_errors=True)
    d.mkdir()
    slim.run('-i', f, '-r', 5, '-pix_fmt', 'rgb24', d / '%04d.png')
    return sorted(d.glob('*.png'))


def main():
    name, f = sys.argv[1], OUT / 'final' / sys.argv[2]
    glow = 'glow' in sys.argv[3:]
    A, B = frames(slim.src(name), 'a'), frames(f, 'b')
    ss, mae_dark, p99, dark_n = [], [], [], 0
    for pa, pb in zip(A, B):
        ca, m = keyed(np.asarray(Image.open(pa).convert('RGB')), glow)
        cb, _ = keyed(np.asarray(Image.open(pb).convert('RGB')), glow)
        la, lb = ca.mean(axis=2), cb.mean(axis=2)
        ss.append(slim.ssim(la, lb))
        dark = m < 0.12
        if dark.sum():
            err = np.abs(ca - cb).mean(axis=2)[dark]
            mae_dark.append(err.mean())
            p99.append(np.percentile(err, 99))
    shutil.rmtree(OUT / 'kf-a', ignore_errors=True)
    shutil.rmtree(OUT / 'kf-b', ignore_errors=True)
    print(f'{name:16} {sys.argv[2]:18} keyed ssim mean {np.mean(ss):.4f} min {np.min(ss):.4f} | dark parts: mean abs err {np.mean(mae_dark):.2f}/255, p99 {np.mean(p99):.1f}, worst frame p99 {np.max(p99):.1f}')


main()
