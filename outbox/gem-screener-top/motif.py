"""Write the Gem Screener's top motif into patch.css: small cut gems (the logo's diamond: table, crown facets, girdle,
pavilion) in a staggered tile with a few sparkles, in the site's cyan. The operator, 2026-10-18: "spis ten motiv udelej
z gemu z tech diamantu chapes" (after a plain diamond lattice). Replaces the tile wherever patch.css carries the
<!--gems--> marker, once for the header (stronger) and once for the band under it (fainter)."""
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent


def gem(x, y, s):
    p = lambda dx, dy: f"{x + dx * s:.1f} {y + dy * s:.1f}"
    return (f"M{p(-5, -6)} L{p(5, -6)} L{p(8, -2)} L{p(0, 8)} L{p(-8, -2)} Z "
            f"M{p(-8, -2)} L{p(8, -2)} "
            f"M{p(-5, -6)} L{p(-2.5, -2)} L{p(0, -6)} L{p(2.5, -2)} L{p(5, -6)} "
            f"M{p(-2.5, -2)} L{p(0, 8)} L{p(2.5, -2)}")


def sparkle(x, y, r):
    return (f"M{x} {y - r} Q{x} {y} {x + r} {y} Q{x} {y} {x} {y + r} Q{x} {y} {x - r} {y} Q{x} {y} {x} {y - r} Z")


def tile(stroke_op, spark_op):
    gems = " ".join(gem(*g) for g in ((28, 28, 1.25), (84, 76, 1.25), (86, 20, .75), (26, 84, .75)))
    sparks = " ".join(sparkle(*s) for s in ((58, 50, 4), (112 - 6, 92, 3)))
    return ("url(\"data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='112' height='104'><!--gems-->"
            f"<path d='{gems}' fill='none' stroke='%2300cfff' stroke-opacity='{stroke_op}' stroke-width='1.1' "
            "stroke-linejoin='round'/>"
            f"<path d='{sparks}' fill='%2300cfff' fill-opacity='{spark_op}'/></svg>\")")


css = (HERE / "patch.css").read_text(encoding="utf-8")
urls = re.findall(r'url\("data:image/svg\+xml;utf8,<svg[^"]*?<!--gems-->.*?</svg>"\)', css)
assert len(urls) == 2, f"expected the two <!--gems--> tiles, found {len(urls)}"
css = css.replace(urls[0], tile(".2", ".55"), 1).replace(urls[1], tile(".3", ".45"), 1)
(HERE / "patch.css").write_text(css, encoding="utf-8")
print("motif written")
