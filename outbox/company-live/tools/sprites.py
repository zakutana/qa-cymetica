"""Turn the pieces the operator generates with Gemini into the sprites the /company mockup composes live.

usage: python outbox/company-live/tools/sprites.py

Reads assets/gen/src/<name>.(jpg|png|webp), the names from gemini-prompts.md (O-room-qa, U-station-spire-green,
...). Sprites on a flat magenta background get it matted out against that known colour (glass keeps its own tint
and loses the pink), are cropped to what is left and saved as assets/gen/<name>.webp with alpha, at most 1024 px
wide; backgrounds and platforms are only resized. assets/gen/sprites.json lists what exists with the numbers the
page places them by: a room's floor (its left and right corners and its front corner), a station's base, the
orbits painted in the Universe background (its `calib`: the core and one ellipse per ring, cx cy rx ry). Nothing
here goes into git: assets/ is ignored, outbox/company-live/assets.json is the manifest.
"""
import json
import pathlib

import numpy as np
from PIL import Image

HERE = pathlib.Path(__file__).resolve().parent.parent
SRC, OUT = HERE / "assets" / "gen" / "src", HERE / "assets" / "gen"
K = np.array([255.0, 0.0, 255.0])


def matte(rgb):
    """alpha and colour of a picture shot over pure magenta"""
    a_rgb = rgb.astype(np.float32)
    R, G, B = a_rgb[..., 0], a_rgb[..., 1], a_rgb[..., 2]
    m = np.minimum(R, B) - G                      # how magenta a pixel is
    a = 1.0 - np.clip((m - 45.0) / 170.0, 0, 1)
    C = (a_rgb - (1 - a)[..., None] * K) / np.maximum(a, 1e-3)[..., None]
    C = np.clip(C, 0, 255)
    # what stays and still leans pink or violet (glass that reflected the background, thruster glow): pull red and
    # blue back to green, everywhere -- violet turns blue, and the palette has no purple to lose
    spill = np.clip(np.minimum(C[..., 0], C[..., 2]) - C[..., 1], 0, None)
    C[..., 0] -= spill
    C[..., 2] -= spill
    return np.dstack([C, a * 255]).astype(np.uint8)


def rings(k):
    """The orbits painted in the operator's U-background (2576 x 1438), inner to outer, as ellipses the page puts
    stations on. Measured 2026-10-18 where each ring crosses x = 1312 above and below the core (t, b); the rings are
    not concentric, so each is a member of one family fitted to the picture: centre between its crossings, a little
    right of the core as it grows, as wide as 1.92 times its height. A new background needs measuring again."""
    out = []
    for t, b in [(250, 784), (230, 856), (205, 992), (150, 1098), (113, 1170), (30, 1302)]:
        ry = (b - t) / 2
        out.append([round((1312 + 0.057 * ry) * k, 1), round((t + b) / 2 * k, 1), round(1.92 * ry * k, 1), round(ry * k, 1)])
    return {"core": [round(1312 * k, 1), round(450 * k, 1)], "rings": out}


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    meta = {}
    for f in sorted(SRC.glob("*")):
        if f.suffix.lower() not in (".jpg", ".jpeg", ".png", ".webp"):
            continue
        name = f.stem
        im = Image.open(f).convert("RGB")
        if name.startswith(("U-background", "O-platform")):
            k = min(1.0, 2600 / im.width)
            if k < 1:
                im = im.resize((round(im.width * k), round(im.height * k)), Image.LANCZOS)
            im.save(OUT / (name + ".webp"), quality=86)
            meta[name] = {"kind": "backdrop", "w": im.width, "h": im.height}
            if name == "U-background":
                meta[name]["calib"] = rings(k)
            continue
        sp = Image.fromarray(matte(np.asarray(im)), "RGBA")
        box = sp.getchannel("A").point(lambda v: 255 if v > 10 else 0).getbbox()
        sp = sp.crop(box)
        w = min(sp.width, 1024 if name.startswith(("O-room", "O-lot")) else 640)
        sp = sp.resize((w, round(sp.height * w / sp.width)), Image.LANCZOS)
        sp.save(OUT / (name + ".webp"), quality=88, method=6)
        A = np.asarray(sp.getchannel("A")) > 128
        ys, xs = np.nonzero(A)
        entry = {"kind": "sprite", "w": sp.width, "h": sp.height}
        if name.startswith(("O-room", "O-lot")):
            # the floor: its left and right corners are the outermost solid pixels, its front corner the lowest
            left = (int(xs.min()), int(ys[xs == xs.min()].mean()))
            right = (int(xs.max()), int(ys[xs == xs.max()].mean()))
            bottom = (int(xs[ys == ys.max()].mean()), int(ys.max()))
            entry.update({"left": left, "right": right, "bottom": bottom})
        else:
            # a station sits on its orbit by the middle of its base platform, two thirds down (looked at on the
            # background, scratchpad uv_test: the painted line then runs under the platform, not through the tower)
            entry.update({"anchor": [sp.width // 2, round(sp.height * 0.67)]})
        meta[name] = entry
        print(name, entry)
    (OUT / "sprites.json").write_text(json.dumps(meta, indent=1) + "\n", encoding="utf-8")
    print(len(meta), "pieces ->", OUT / "sprites.json")


if __name__ == "__main__":
    main()
