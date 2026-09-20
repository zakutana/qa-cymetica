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
    it" as "it is not there".

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

    expression = " ".join(found.group(1).split())
    added = [stage for stage in OTHER_STAGES if stage in expression]
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
                    f"{expression!r}, so a request that is only "
                    f"{', '.join(added)} is displayed as building. The column "
                    f"under it filters stage == 'building' and does not, and "
                    f"the API agrees with the column: stats building "
                    f"{stats.get('building')}, funded {stats.get('funded')}"),
            left={"tile_expression": expression, "adds": added},
            right={"stats": stats},
            sources={"board": BOARD_PAGE, "api": API}))
        return

    conclude(Measurement(
        verdict="passed",
        reason=(f"the Building now tile is computed as {expression!r}, which "
                f"counts nothing but what is building"),
        left={"tile_expression": expression},
        right={"stats": stats},
        sources={"board": BOARD_PAGE, "api": API}))
