"""The live build board's headline tile, against the column beneath it.

`/build-it-better` opens with five counters -- Requests, Building now,
Shipped, Shipped inside 24 h, Median build time -- and immediately under them
four columns: REQUESTED, QUEUED, BUILDING, SHIPPED. Same page, same data,
read in one glance.

Measured 2026-09-20, twelve minutes before ET-26036's 24-hour deadline
expired: the tile said **Building now 1** while the BUILDING column said
**0**, and the only request sat in QUEUED. Their API agreed with the column
and not with the tile -- `GET /api/v1/build-it-better/requests` returned
stats {"total":1,"requested":0,"funded":1,"building":0,"shipped":0} and the
item read stage "funded", queue_status "queued", shipped_at null.

The page's own script says why:

    text($('bs-building'), (s.funded || 0) + (s.building || 0));

The tile is funded plus building, so a request that is only funded -- queued,
not started -- is displayed as building, while the column filters
`b.stage === 'building'` and does not. A requester reads the tile and is told
their build is running when it is still in the queue.

WHAT THIS CHECK ASSERTS. That the page computes its "Building now" tile from
the building count alone. It reads the served HTML and looks for the tile's
assignment, and it is deliberately narrow:

  * it fails when that assignment adds `funded` (or any other stage) to
    `building` -- the defect measured;
  * it passes when the tile is `s.building` alone, whatever else the page
    does;
  * it is INCONCLUSIVE when the page no longer carries an assignment it can
    read at all -- a rewritten front end is not evidence of a fix, and rule 8
    says a failed read is not an empty one. The same day this was written, a
    sibling check nearly filed a false report by treating "I could not find
    it" as "it is not there". Also inconclusive when the tile is handed
    something that names no stage: a bare name is followed once to its
    assignment, and one that leads nowhere, or a call whose body is
    elsewhere, is not read (deep pass of 2026-09-21, A15 -- `nb` passed).

WHY IT IS READ OFF THE SCRIPT. The tile's value is computed in the browser,
so the number itself is not in the HTML and no GET can see it. What IS in the
HTML is the arithmetic that produces it, which is the defect itself rather
than a symptom of it. That makes the check brittle against a refactor on
purpose: it goes inconclusive rather than green when it stops being able to
read, and a run that cannot read says so.

Not filed as a UI defect and not one. The number is wrong about the
platform's own state, on the surface the product leads with, and the API is
right -- so the correction belongs to whoever wrote that line, not to a
stylesheet.

SAFE. One GET of a public page, no key.
"""

from __future__ import annotations

import re

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

BOARD_PAGE = "/build-it-better"
API = "/api/v1/build-it-better/requests"
# The tile is written by `text($('bs-building'), <expression>);` -- the id is
# the anchor, because it is the one part a translation or a restyle will not
# touch, and the expression after it is what this check reads.
TILE = re.compile(
    r"""\$\(\s*['"]bs-building['"]\s*\)\s*,\s*(.{0,160}?)\s*\)\s*;""", re.S)
# Any stage name other than `building` appearing inside that expression.
OTHER_STAGES = ("funded", "requested", "queued", "shipped", "total")
# The one stage the tile may count, as a word: `s.building`, `s['building']`.
BUILDING = re.compile(r"\bbuilding\b")
# A field read inside the expression: `s.funded`, `s['in_progress']` -- not a
# method call such as `.toLocaleString()`.
FIELD = re.compile(r"""\.\s*([A-Za-z_]\w*)\b(?!\s*\()|\[\s*['"](\w+)['"]\s*\]""")
# A bare name, which says nothing about what it holds until it is followed.
NAME = re.compile(r"[A-Za-z_$][\w$]*")


def resolve(page: str, expression: str, before: int) -> str | None:
    """The expression the tile actually shows, or None if it cannot be read.

    Deep pass of 2026-09-21, A15. Written as `const nb = s.funded +
    s.building; text($('bs-building'), nb);` the tile's argument is `nb`: no
    stage word in it, and the check passed on the very arithmetic it exists
    to catch. So a bare name is followed ONE step, to its nearest assignment
    earlier in the page. A name with no such assignment, or one that leads
    only to another name, is not read -- and an unread tile is inconclusive,
    never a pass.
    """
    if NAME.fullmatch(expression):
        return _assignment(page, expression, before)
    # A01/C04, deep pass of 2026-09-22 evening: only a WHOLE-expression name
    # was followed, so `(s.building || 0) + nf` with `const nf = s.funded`
    # passed, and so did `(s.building || 0) + countOf(s)`. Every free name is
    # followed now -- not a field, not the object a field hangs off -- and a
    # call whose body is elsewhere is not read.
    for called in CALL.finditer(expression):
        if called.group(1) not in PURE_CALLS:
            return None
    resolved = expression
    for name in sorted(set(FREE.findall(expression)) - WORDS - PURE_CALLS):
        value = _assignment(page, name, before)
        if value is None:
            return None
        resolved = re.sub(r"(?<![\w$.])" + re.escape(name) + r"(?![\w$(.\[])",
                          f"({value})", resolved)
    return resolved


def _assignment(page: str, name: str, before: int) -> str | None:
    """A name's nearest assignment earlier in the page, if it is not merely
    another name."""
    assigned = list(re.finditer(
        r"(?<![\w$.])" + re.escape(name) + r"\s*=(?![=>])\s*([^;]{1,160}?)\s*;",
        page[:before], re.S))
    if not assigned:
        return None
    value = " ".join(assigned[-1].group(1).split())
    return None if NAME.fullmatch(value) else value


# A name standing alone in the expression -- not after a dot, not the object a
# field or index hangs off, not a call.
FREE = re.compile(r"(?<![\w$.'\"])([A-Za-z_$][\w$]*)(?![\w$]|\s*[.(\[])")
# A call of a free function, not a method: `countOf(s)`, not `.toLocaleString()`.
CALL = re.compile(r"(?<![\w$.])([A-Za-z_$][\w$]*)\s*\(")
# Calls that only convert the number they are given.
PURE_CALLS = frozenset({"Number", "parseInt", "parseFloat", "String"})
WORDS = frozenset({"true", "false", "null", "undefined", "NaN", "Infinity"})


@qa(component="rest.build_it_better", tier=SafetyTier.SAFE, surface="rest")
def test_the_boards_building_tile_counts_only_what_is_building(rest_anon):
    """One GET of the board page, and the arithmetic behind one number."""
    page = rest_anon.get(BOARD_PAGE)
    if page.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"{BOARD_PAGE} answered HTTP {page.status_code}, and a "
                   f"failed read is not a page without the defect",
            sources={"board": BOARD_PAGE}))
        return

    found = TILE.search(page.text)
    if not found:
        conclude(Measurement(
            verdict="inconclusive",
            reason="the board page no longer carries a readable assignment "
                   "for its Building now tile, so what the tile counts could "
                   "not be established from the served HTML",
            sources={"board": BOARD_PAGE}))
        return

    tile = " ".join(found.group(1).split())
    expression = resolve(page.text, tile, found.start())
    if expression is None or (not BUILDING.search(expression) and not any(
            stage in expression for stage in OTHER_STAGES)):
        # A pass is promised only for a tile that IS the building count, so
        # an argument that names no stage at all -- an unfollowed name, a
        # call whose body is elsewhere -- has not been read.
        conclude(Measurement(
            verdict="inconclusive",
            reason=(f"the board's Building now tile is computed as {tile!r}"
                    + (f", which is {expression!r}" if expression
                       and expression != tile else "")
                    + ", which names no stage this check can read, so what "
                      "the tile counts could not be established from the "
                      "served HTML"),
            left={"tile_expression": tile, "resolved": expression},
            sources={"board": BOARD_PAGE}))
        return
    # A14, deep pass of 2026-09-22: every field the expression reads that is
    # not `building` is added to it, whatever it is called -- a list of five
    # names let `+ s.pending` pass. A method call is not a field.
    fields = {a or b for a, b in FIELD.findall(expression)} - {"building"}
    added = sorted(fields | {stage for stage in OTHER_STAGES
                             if stage in expression})
    # Quoted as the page wrote it, and through the name when it used one.
    shown = (repr(expression) if expression == tile
             else f"{tile!r}, which is {expression!r}")
    # What the platform says about itself, quoted beside the arithmetic so a
    # reader of the verdict can see both halves.
    stats = {}
    board = rest_anon.get(API)
    if board.status_code == 200:
        stats = (board.json() or {}).get("stats") or {}

    if added:
        conclude(Measurement(
            verdict="failed",
            reason=(f"the board's Building now tile is computed as "
                    f"{shown}, so a request that is only "
                    f"{', '.join(added)} is displayed as building. The column "
                    f"under it filters stage == 'building' and does not, and "
                    f"the API agrees with the column: stats building "
                    f"{stats.get('building')}, funded {stats.get('funded')}"),
            left={"tile_expression": expression, "tile": tile, "adds": added},
            right={"stats": stats},
            sources={"board": BOARD_PAGE, "api": API}))
        return

    conclude(Measurement(
        verdict="passed",
        reason=(f"the Building now tile is computed as {shown}, which "
                f"counts nothing but what is building"),
        left={"tile_expression": expression, "tile": tile},
        right={"stats": stats},
        sources={"board": BOARD_PAGE, "api": API}))
