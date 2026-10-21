"""Write the Gem Screener's header motif into patch.css and rays.svg (kept under that name): light thrown by the logo's
gem, drawn soft -- blurred shafts of unequal width, a slow cloud of cyan haze that thins out away from the gem, a few
out-of-focus discs and two glints -- on a near-black band, so the logo is the brightest thing in it. No straight hairlines.

History, 2026-10-18..21: the Agent Tournaments honeycomb, a diamond lattice, small gem icons ("to je hnus ty
diamanty"), a low-poly crystal mesh -- which Cymetica then built over the header, the strip under it and every panel
("tj nahovno ten novy vzhled ... to pozadi musi byt tmave jinak to logo na tom tak nevynikne") -- then fine straight
rays from the gem ("husty napad jen to je moc takove geometricky ty rovne cary, chci at to vypada lip"). This one has
no line in it at all: everything is a soft edge."""
import math
import random
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
W, H = 1920, 130
CX, CY = 66, 46      # the gem's centre in the header when the logo's left edge sits at x=32 (it is 64 px tall, 14 px from the top)


def light():
    rnd = random.Random(20261021)
    defs = (
        "<defs>"
        f"<radialGradient id='f' gradientUnits='userSpaceOnUse' cx='{CX}' cy='{CY}' r='1300'>"
        "<stop offset='0' stop-color='%2300cfff' stop-opacity='.55'/>"
        "<stop offset='.25' stop-color='%2300cfff' stop-opacity='.26'/>"
        "<stop offset='1' stop-color='%2300cfff' stop-opacity='0'/></radialGradient>"
        f"<radialGradient id='m' gradientUnits='userSpaceOnUse' cx='{CX + 120}' cy='{CY}' r='980'>"
        "<stop offset='0' stop-color='white' stop-opacity='1'/>"
        "<stop offset='.55' stop-color='white' stop-opacity='.35'/>"
        "<stop offset='1' stop-color='white' stop-opacity='0'/></radialGradient>"
        "<mask id='k'><rect width='1920' height='130' fill='url(%23m)'/></mask>"
        # the whole picture fades in over its first 140 px, so on a wide screen (where it starts further right, at the
        # logo) there is no edge where it begins
        "<linearGradient id='l' x1='0' x2='140' y1='0' y2='0' gradientUnits='userSpaceOnUse'>"
        "<stop offset='0' stop-color='white' stop-opacity='0'/><stop offset='1' stop-color='white' stop-opacity='1'/></linearGradient>"
        "<mask id='e'><rect width='1920' height='130' fill='url(%23l)'/>"
        "<rect x='140' width='1780' height='130' fill='white'/></mask>"
        "<filter id='b' x='-5%' y='-80%' width='110%' height='260%'><feGaussianBlur stdDeviation='13'/></filter>"
        "<filter id='s' x='-50%' y='-50%' width='200%' height='200%'><feGaussianBlur stdDeviation='4'/></filter>"
        "<filter id='h' x='0' y='0' width='100%' height='100%'>"
        "<feTurbulence type='fractalNoise' baseFrequency='.007 .013' numOctaves='3' seed='7' result='n'/>"
        "<feColorMatrix in='n' values='0 0 0 0 0  0 0 0 0 .81  0 0 0 0 1  0 0 0 2.6 -1.2'/></filter>"
        "</defs>"
    )
    out = [defs]
    # a cloud of haze, thicker near the gem, thinning to the right
    out.append("<rect width='1920' height='130' filter='url(%23h)' mask='url(%23k)' opacity='.17'/>")
    # shafts: unequal width, angle and strength, blurred wide so no edge survives
    shafts = []
    far = 2400
    for deg, width, op in ((-24, 5.5, .50), (-13, 9.0, .75), (-5, 4.0, .60), (3, 11.0, .95), (11, 5.0, .55), (20, 8.0, .60), (31, 4.5, .40)):
        deg += rnd.uniform(-1.5, 1.5)
        a, b = math.radians(deg - width / 2), math.radians(deg + width / 2)
        shafts.append(f"<path d='M{CX} {CY} L{CX + far * math.cos(a):.0f} {CY + far * math.sin(a):.0f} "
                      f"L{CX + far * math.cos(b):.0f} {CY + far * math.sin(b):.0f} Z' fill='url(%23f)' fill-opacity='{op * .8:.3f}'/>")
    out.append(f"<g filter='url(%23b)'>{''.join(shafts)}</g>")
    # out-of-focus discs, as if the light were scattering on dust
    discs = []
    for x, y, r, op in ((330, 36, 15, .075), (505, 82, 24, .05), (690, 28, 11, .07), (880, 70, 17, .045), (1090, 46, 28, .035), (1330, 88, 13, .04)):
        discs.append(f"<circle cx='{x}' cy='{y}' r='{r}' fill='%2300cfff' fill-opacity='{op}'/>")
    out.append(f"<g filter='url(%23s)'>{''.join(discs)}</g>")
    # two glints, soft
    glints = []
    for x, y, r in ((520, 41, 2.6), (1140, 66, 2.0)):
        glints.append(f"<path d='M{x} {y - r * 2.4} Q{x} {y} {x + r * 2.4} {y} Q{x} {y} {x} {y + r * 2.4} Q{x} {y} {x - r * 2.4} {y} "
                      f"Q{x} {y} {x} {y - r * 2.4} Z' fill='%2300cfff' fill-opacity='.34'/>")
    out.append(f"<g filter='url(%23s)'>{''.join(glints)}</g>")
    return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' viewBox='0 0 {W} {H}'>"
            f"<!--motif-->{out[0]}<g mask='url(%23e)'>{''.join(out[1:])}</g></svg>")


css = (HERE / "patch.css").read_text(encoding="utf-8")
slots = re.findall(r"url\(\"data:image/svg\+xml;utf8,<svg[^\"]*?<!--motif-->.*?</svg>\"\)", css)
assert len(slots) == 1, f"expected the one motif slot, found {len(slots)}"
svg = light()
css = css.replace(slots[0], f'url("data:image/svg+xml;utf8,{svg}")', 1)
(HERE / "patch.css").write_text(css, encoding="utf-8")
(HERE / "rays.svg").write_text(svg.replace("%23", "#"), encoding="utf-8")
print("light written:", len(svg), "chars")
