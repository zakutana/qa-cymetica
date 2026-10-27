"""The Quant Lab search's result rows fit the grid their list is drawn in (2026-10-27, ET-32976).

The Quant Lab's Experiments page (cymetica.com/company/app/experiments) draws its search results
(quantsearch.js, "THROWN OUT" / "CLEARED THE BAR" rows) with the same `.qrow` row as its bot list
(quantlab.js). The stylesheet lays `.qrow` out as a grid whose FIRST track is a fixed narrow one:
`22px minmax(0,1fr) 70px 80px ...`, built for the rank cell the bot list draws first
(`<span class="rk">`). The search rows draw no such cell, so their name cell lands in the 22 px
track and the return in the wide one.

**What was seen when this was written** (2026-10-27, signed in, 1315 px and a 1960 px screen):
"stockbull_blue · DOT" and "lost 3.09% on the held-back period (59 trades)" are set in a column 22
px wide, one to three characters a line, down the left of the card; the -3.09% sits 776 px to the
right. The results of a search are unreadable. The cause is the page's own script and stylesheet,
both public.

**The rule.** Every script the page loads that draws a `.qrow` row draws, as its first cell, the
one the stylesheet's first track is sized for (`.rk`); or the stylesheet's first `.qrow` track is
not a narrow fixed one (under 60 px).

NOT asserted: colours, spacing, any number in a result, or the signed-in data.

SAFE: GETs only, the page's public HTML, scripts and stylesheet.
"""

from __future__ import annotations

import re

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

CLAIM = "quant-search-rows-fit-the-list-grid"
PAGE = "/company/app/experiments"
_SRC = re.compile(r"""<(?:script|link)\b[^>]*?(?:src|href)=["']([^"']+\.(?:js|css)[^"']*)["']""", re.I)
_QROW_RULE = re.compile(r"\.qrow\s*\{[^}]*?grid-template-columns\s*:\s*([^;}]+)", re.I)
_FIRST_CHILD = re.compile(r"""<\w+\s+class=["']([^"']*)["']""")


def first_track_px(css: str) -> float | None:
    """The width in px of the first grid track of the plain `.qrow { grid-template-columns }`
    rule, or None when it is not a plain px track or the rule is not there."""
    m = _QROW_RULE.search(css or "")
    if not m:
        return None
    first = m.group(1).strip().split()[0]
    px = re.fullmatch(r"(\d+(?:\.\d+)?)px", first)
    return float(px.group(1)) if px else None


def row_first_cells(script: str) -> list[str]:
    """For every `.qrow` row a script draws, the class list of its first child element."""
    out = []
    for m in re.finditer(r"""class=\\?["']qrow\b""", script or ""):
        child = _FIRST_CHILD.search(script[m.end(): m.end() + 700])
        out.append(child.group(1) if child else "")
    return out


@qa(component="rest.company", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_quant_search_rows_fit_the_list_grid(rest_trusted):
    """Each script's `.qrow` rows against the stylesheet's grid."""
    page = rest_trusted.get(PAGE)
    if page.status_code != 200:
        raise Inconclusive(f"{PAGE} answered HTTP {page.status_code}")
    assets = [a for a in _SRC.findall(page.text) if a.startswith("/static/company/") or "/static/company/" in a]
    texts = {}
    for a in assets:
        r = rest_trusted.get(a if a.startswith("http") else a)
        if r.status_code != 200:
            raise Inconclusive(f"{a} answered HTTP {r.status_code}")
        texts[a.split("?")[0]] = r.text
    css = "\n".join(t for a, t in texts.items() if a.endswith(".css"))
    track = first_track_px(css)
    if not _QROW_RULE.search(css):
        raise Inconclusive("the stylesheet has no `.qrow` grid rule; the layout this judges is not where it was read")
    rows = {a: row_first_cells(t) for a, t in texts.items() if a.endswith(".js") and "qrow" in t}
    rows = {a: cells for a, cells in rows.items() if cells}
    if not rows:
        raise Inconclusive("no script on the page draws a `.qrow` row")
    narrow = track is not None and track < 60
    bad = {a: [c for c in cells if not re.search(r"\brk\b", c)] for a, cells in rows.items()}
    bad = {a: cs for a, cs in bad.items() if cs}
    failed = narrow and bool(bad)
    conclude(Measurement(
        verdict="failed" if failed else "passed",
        reason=(f"the stylesheet's `.qrow` grid starts with a {track:g}px track (the rank cell, `.rk`), and "
                + "; ".join(f"{a} draws {len(cs)} row template(s) whose first cell is "
                            f"{sorted(set(cs))} not `.rk`, so the name cell falls in that {track:g}px track"
                            for a, cs in bad.items())
                if failed else
                f"every `.qrow` row the page's scripts draw starts with the cell the grid is sized for "
                f"(first track {track if track is not None else 'not a narrow fixed one'}): "
                + "; ".join(f"{a} {len(c)} row(s)" for a, c in rows.items())),
        left={"rows_whose_first_cell_is_not_rk": sum(len(v) for v in bad.values())},
        right={"allowed": 0, "first_track_px": track},
        population={"rows_by_script": {a: len(c) for a, c in rows.items()},
                    "first_cells": {a: c for a, c in rows.items()}},
        sources={"page": PAGE, "scripts": ", ".join(rows), "style": "/static/company/xp.css"},
        claim_id=CLAIM))
