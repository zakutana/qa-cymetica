"""The product pictures in art/: the ten already on the live site (/static/img/promo-art/, from outbox/promo-market/spec/art)
and four new ones for the products that borrow another product's picture today (promo/mine, 2026-10-26: Events ->
chart.svg, Airdrop Farmer -> infil.svg, Build it Better hub and Usage -> supply.svg). Agent Tournaments has its own
(casino.svg) though the live list gives it My Agents' agents.svg.

Same frame as the ten: 360 x 150, the dark ground with a corner glow, a faint grid, the product's motif on the right,
its glyph in a badge on the left and its address under it. The site's palette only.
"""
import shutil
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "art"
SRC = HERE.parent / "promo-market" / "spec" / "art"
CYAN, GREEN, BLUE, RED = "#00cfff", "#00ff88", "#3b82f6", "#ff4444"


def frame(key, path, c0, c1, motif, glyph):
    grid = "".join(f"M{x} 0V150 " for x in range(12, 360, 24)) + "".join(f"M0 {y}H360 " for y in range(6, 150, 24))
    i = "g" + key
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="720" height="300" viewBox="0 0 360 150" preserveAspectRatio="xMidYMid slice" aria-hidden="true">'
            f'<defs><linearGradient id="{i}b" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{c0}" stop-opacity=".16"/><stop offset=".6" stop-color="#0d1520" stop-opacity="0"/></linearGradient>'
            f'<linearGradient id="{i}v" x1="0" y1="1" x2="0" y2="0"><stop offset="0" stop-color="{c0}"/><stop offset="1" stop-color="{c1}"/></linearGradient>'
            f'<radialGradient id="{i}r" cx=".78" cy=".45" r=".6"><stop offset="0" stop-color="{c1}" stop-opacity=".22"/><stop offset="1" stop-color="{c1}" stop-opacity="0"/></radialGradient></defs>'
            f'<rect width="360" height="150" fill="#0a0e17"/><rect width="360" height="150" fill="url(#{i}b)"/><rect width="360" height="150" fill="url(#{i}r)"/>'
            f'<path d="{grid}" stroke="#e6edf7" stroke-opacity=".035"/>{motif.replace("GRAD", f"url(#{i}v)")}'
            f'<g transform="translate(22 22)"><rect width="46" height="46" rx="12" fill="#06090f" fill-opacity=".7" stroke="{c0}" stroke-opacity=".5"/>'
            f'<g transform="translate(11 11)" fill="none" stroke="{c0}" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"><svg width="24" height="24" viewBox="0 0 20 20">{glyph}</svg></g></g>'
            f'<text x="24" y="92" fill="#7f93ad" font-family="JetBrains Mono, monospace" font-size="10">cymetica.com{path}</text></svg>')


def events(c0, c1):
    """A timeline of events with the probability each one carries, as bars rising from it."""
    m = f'<path d="M190 112H350" stroke="{c0}" stroke-opacity=".5"/>'
    for k, (x, h) in enumerate(((204, 46), (234, 70), (264, 34), (294, 88), (324, 58))):
        col = GREEN if k % 2 == 0 else c1
        m += f'<rect x="{x - 7}" y="{112 - h}" width="14" height="{h}" rx="3" fill="GRAD" opacity="{.45 + k * .1:.2f}"/>'
        m += f'<circle cx="{x}" cy="112" r="4.5" fill="#0a0e17" stroke="{col}" stroke-width="1.6"/>'
        m += f'<text x="{x}" y="{106 - h}" fill="{col}" font-family="JetBrains Mono, monospace" font-size="8.5" text-anchor="middle">{20 + h // 2}%</text>'
    return m


def airdrop(c0, c1):
    """The farm from above: isometric plots, three of them lit, a pillar of light rising from each."""
    m = ""
    for r in range(4):
        for q in range(4):
            cx, cy = 272 + (q - r) * 20, 46 + (q + r) * 10
            lit = (r, q) in ((1, 2), (2, 0), (3, 3))
            m += (f'<path d="M{cx} {cy - 10}l20 10-20 10-20-10z" fill="{c0 if lit else c1}" fill-opacity="{.35 if lit else .06}" '
                  f'stroke="{c0}" stroke-opacity="{.8 if lit else .3}" stroke-width="1"/>')
            if lit:
                m += f'<rect x="{cx - 3}" y="{cy - 46}" width="6" height="40" rx="3" fill="GRAD" opacity=".75"/>'
                m += f'<circle cx="{cx}" cy="{cy - 50}" r="3" fill="{c0}"/>'
    return m


def bib(c0, c1):
    """Blocks being stacked into an app: a tower of modules, the top one lowering into place."""
    m = ""
    rows = ((216, 104, 4), (230, 82, 3), (244, 60, 2))
    for x0, y, n in rows:
        for k in range(n):
            m += f'<rect x="{x0 + k * 30}" y="{y}" width="26" height="18" rx="3" fill="{c1}" fill-opacity=".14" stroke="{c0}" stroke-opacity=".6"/>'
            m += f'<path d="M{x0 + k * 30 + 6} {y + 9}h14" stroke="{c0}" stroke-opacity=".45"/>'
    m += f'<rect x="258" y="24" width="26" height="18" rx="3" fill="GRAD" opacity=".85"/>'
    m += f'<path d="M271 24V8 M240 8H330" stroke="{c0}" stroke-opacity=".6"/><path d="M330 8v100" stroke="{c0}" stroke-opacity=".3" stroke-dasharray="3 4"/>'
    m += f'<path d="M262 50l9 6 9-6" fill="none" stroke="{GREEN}" stroke-width="1.6"/>'
    return m


def usage(c0, c1):
    """A meter: the arc of what was used this month, and the split under it."""
    m = f'<path d="M216 112a56 56 0 0 1 112 0" fill="none" stroke="{c1}" stroke-opacity=".18" stroke-width="10" stroke-linecap="round"/>'
    m += f'<path d="M216 112a56 56 0 0 1 92.6-42.4" fill="none" stroke="GRAD" stroke-width="10" stroke-linecap="round"/>'
    m += f'<path d="M272 112l26-32" stroke="{c0}" stroke-width="2" stroke-linecap="round"/><circle cx="272" cy="112" r="5" fill="{c0}"/>'
    for k, (w, col) in enumerate(((58, GREEN), (38, c0), (22, BLUE))):
        m += f'<rect x="{338 - 8}" y="{36 + k * 14}" width="6" height="8" rx="2" fill="{col}"/>'
    m += f'<text x="272" y="100" fill="{c0}" font-family="JetBrains Mono, monospace" font-size="11" text-anchor="middle">68%</text>'
    return m


GLYPH = {
    "events": '<rect x="3.5" y="4.5" width="13" height="12" rx="2"/><path d="M3.5 8h13 M7 2.5v4 M13 2.5v4 M7 12.5l2 1.5 4-4"/>',
    "airdrop": '<path d="M10 17V10 M10 10c0-3 2-5 5.5-5.5C15.5 8 13 10 10 10z M10 12c0-2.4-1.6-4-4.5-4.4C5.5 10.4 7.5 12 10 12z M5 17h10"/>',
    "bib": '<path d="M12.5 3.5l4 4-2 2-4-4z M10.5 5.5 4 12l4 4 6.5-6.5 M6 14l-2.5 2.5"/>',
    "usage": '<path d="M3.5 14a6.5 6.5 0 0 1 13 0 M10 14l3-4"/><circle cx="10" cy="14" r="1.2" fill="currentColor"/>',
}
NEW = [("events", "/events", CYAN, GREEN, events),
       ("airdrop", "/airdrop-farmer", GREEN, CYAN, airdrop), ("bib", "/build-it-better", CYAN, BLUE, bib),
       ("usage", "/usage", CYAN, GREEN, usage)]


def main():
    OUT.mkdir(exist_ok=True)
    for f in SRC.glob("*.svg"):
        shutil.copyfile(f, OUT / f.name)
    for key, path, c0, c1, motif in NEW:
        (OUT / f"{key}.svg").write_text(frame(key, path, c0, c1, motif(c0, c1), GLYPH[key]), encoding="utf-8")
    print(sorted(p.name for p in OUT.glob("*.svg")))


if __name__ == "__main__":
    main()
