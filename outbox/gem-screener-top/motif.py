"""Write the Gem Screener's top motif into patch.css and crystal.svg: a crystal surface, as if looking into a cut gem --
a low-poly mesh of large faint facets in the site's cyan (a few in its green), brightest behind the logo (top left) and
fading right and down, with thin facet edges. Deterministic (seeded), 1920 x 560, repeated sideways on wider screens.

History, 2026-10-18: the Agent Tournaments honeycomb ("tu vymysli jiny pro gem screener"), then a plain diamond
lattice, then small gem icons ("spis ten motiv udelej z gemu z tech diamantu" -> "to je hnus ty diamanty"). Icons
tiled as wallpaper read as clip art; this keeps the gem as material, not as a picture of one."""
import math
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
W, H = 1920, 560
COLS, ROWS = 18, 7          # cells: about 107 x 80 px
LIGHT = (130, 20)           # where the light comes from: behind the logo


def mesh(fill_scale, edge_scale):
    rnd = random.Random(20261018)
    cw, rh = W / COLS, H / ROWS
    pts = {}
    for j in range(ROWS + 1):
        for i in range(COLS + 1):
            x, y = i * cw, j * rh
            if 0 < i < COLS:
                x += rnd.uniform(-.38, .38) * cw
            if 0 < j < ROWS:
                y += rnd.uniform(-.38, .38) * rh
            if i == COLS:  # the right edge repeats the left, so the tile joins when repeated sideways
                x = W
            pts[i, j] = (x, y)
    for j in range(ROWS + 1):  # make the seam match: right column = left column shifted by W
        pts[COLS, j] = (W, pts[0, j][1])

    def light(x, y):
        return .12 + .88 * math.exp(-((x - LIGHT[0]) / 720) ** 2 - ((y - LIGHT[1]) / 300) ** 2)

    faces, edges = [], []
    for j in range(ROWS):
        for i in range(COLS):
            a, b, c, d = pts[i, j], pts[i + 1, j], pts[i + 1, j + 1], pts[i, j + 1]
            tris = ((a, b, c), (a, c, d)) if (i + j) % 2 == 0 else ((a, b, d), (b, c, d))
            for t in tris:
                cx, cy = sum(p[0] for p in t) / 3, sum(p[1] for p in t) / 3
                L = light(cx, cy)
                op = min(.2, max(.006, L * (.25 + .75 * rnd.random()) * fill_scale))
                green = rnd.random() < .04  # a rare green facet; at 12% they read as muddy olive patches on navy
                col = "%2300ff88" if green else "%2300cfff"
                if green:
                    op *= .6
                d_ = "M" + " L".join(f"{p[0]:.0f} {p[1]:.0f}" for p in t) + "Z"
                faces.append(f"<path d='{d_}' fill='{col}' fill-opacity='{op:.3f}'/>")
                edges.append((d_, min(.22, (.03 + .14 * L) * edge_scale)))
    # edges grouped into a few opacity bands to keep the file small
    bands = {}
    for d_, op in edges:
        bands.setdefault(round(op, 2), []).append(d_)
    lines = "".join(f"<path d='{' '.join(ds)}' fill='none' stroke='%2300cfff' stroke-opacity='{op}' stroke-width='1'/>"
                    for op, ds in sorted(bands.items()))
    return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' viewBox='0 0 {W} {H}' "
            f"preserveAspectRatio='none'><!--motif-->{''.join(faces)}{lines}</svg>")


css = (HERE / "patch.css").read_text(encoding="utf-8")
slots = re.findall(r"url\(\"data:image/svg\+xml;utf8,<svg[^\"]*?<!--(?:motif|gems)-->.*?</svg>\"\)", css)
assert len(slots) == 2, f"expected the two motif slots, found {len(slots)}"
header, band = mesh(.4, .9), mesh(.4, .8)
css = css.replace(slots[0], f'url("data:image/svg+xml;utf8,{header}")', 1)
css = css.replace(slots[1], f'url("data:image/svg+xml;utf8,{band}")', 1)
(HERE / "patch.css").write_text(css, encoding="utf-8")
(HERE / "crystal.svg").write_text(header.replace("%23", "#"), encoding="utf-8")
print("motif written:", len(header), "chars per slot")
