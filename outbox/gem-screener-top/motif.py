"""Write the Gem Screener's header motif into patch.css and rays.svg: light thrown by the logo's gem -- fine rays and a
few wide faint wedges fanning out from the gem's centre to the right, in the site's cyan, fading with distance, on a
near-black band so the logo is the brightest thing in it. Not stretched: drawn at 1920 x 130 and painted at that size.

History, 2026-10-18..21: the Agent Tournaments honeycomb, a diamond lattice, small gem icons ("to je hnus ty
diamanty"), a low-poly crystal mesh -- which Cymetica then built, brighter, over the header, the strip under it and
every panel ("tj nahovno ten novy vzhled ... to pozadi musi byt tmave jinak to logo na tom tak nevynikne"). This one
keeps the gem as the source of light, and leaves everything else dark."""
import math
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
W, H = 1920, 130
CX, CY = 68, 58      # the gem's centre in the header at 1440+ (the logo's left edge sits at x=32, 64 px tall)


def rays():
    out = [f"<defs><radialGradient id='f' gradientUnits='userSpaceOnUse' cx='{CX}' cy='{CY}' r='1250'>"
           "<stop offset='0' stop-color='%2300cfff' stop-opacity='.30'/>"
           "<stop offset='.35' stop-color='%2300cfff' stop-opacity='.13'/>"
           "<stop offset='1' stop-color='%2300cfff' stop-opacity='0'/></radialGradient>"
           f"<radialGradient id='w' gradientUnits='userSpaceOnUse' cx='{CX}' cy='{CY}' r='1100'>"
           "<stop offset='0' stop-color='%2300cfff' stop-opacity='.075'/>"
           "<stop offset='1' stop-color='%2300cfff' stop-opacity='0'/></radialGradient></defs>"]
    far = 2600
    # wide wedges: alternate angles, like the table of a brilliant cut seen from the girdle
    wedges = []
    for k, a0 in enumerate(range(-28, 28, 7)):
        if k % 2:
            continue
        a, b = math.radians(a0), math.radians(a0 + 7)
        wedges.append(f"M{CX} {CY} L{CX + far * math.cos(a):.0f} {CY + far * math.sin(a):.0f} "
                      f"L{CX + far * math.cos(b):.0f} {CY + far * math.sin(b):.0f} Z")
    out.append(f"<path d='{' '.join(wedges)}' fill='url(%23w)'/>")
    # hairlines, denser near the horizontal, each a little different
    lines = []
    for i, deg in enumerate((-31, -25, -20, -15.5, -11.5, -8, -4.5, -1.5, 1.5, 4.5, 8, 11.5, 15.5, 20, 25, 31)):
        r = math.radians(deg)
        lines.append(f"M{CX} {CY} L{CX + far * math.cos(r):.0f} {CY + far * math.sin(r):.0f}")
    out.append(f"<path d='{' '.join(lines)}' fill='none' stroke='url(%23f)' stroke-width='1'/>")
    # two sparkles on the strongest rays
    for x, y, r in ((520, 43, 3.2), (1130, 68, 2.4)):
        out.append(f"<path d='M{x} {y - r * 2} Q{x} {y} {x + r * 2} {y} Q{x} {y} {x} {y + r * 2} Q{x} {y} {x - r * 2} {y} "
                   f"Q{x} {y} {x} {y - r * 2} Z' fill='%2300cfff' fill-opacity='.30'/>")
    return (f"<svg xmlns='http://www.w3.org/2000/svg' width='{W}' height='{H}' viewBox='0 0 {W} {H}'>"
            f"<!--motif-->{''.join(out)}</svg>")


css = (HERE / "patch.css").read_text(encoding="utf-8")
slots = re.findall(r"url\(\"data:image/svg\+xml;utf8,<svg[^\"]*?<!--motif-->.*?</svg>\"\)", css)
assert len(slots) == 1, f"expected the one motif slot, found {len(slots)}"
svg = rays()
css = css.replace(slots[0], f'url("data:image/svg+xml;utf8,{svg}")', 1)
(HERE / "patch.css").write_text(css, encoding="utf-8")
(HERE / "rays.svg").write_text(svg.replace("%23", "#").replace("url(#", "url(#"), encoding="utf-8")
print("rays written:", len(svg), "chars")
