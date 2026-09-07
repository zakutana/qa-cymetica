"""How many CLOB pairs are there? Counted from `total`, not from one page.

Report #52 has now been wrong twice, in two different ways, and both failures
were ours.

First it compared llms.txt against mcp.json's blurb -- prose against prose, a
check that could not fail and therefore verified nothing. That check was
retired and replaced with this file, which counts the live catalogue instead.

Then this file counted `len(pairs)` from a default `list_clob_pairs` call and
reported "200 vs 568". The response carries `total`, `limit` and `offset` in
the same object the pairs came out of; the count was a page size. The vendor
answered on 2026-09-05 that the tool defaults to limit=200 with a max of 2000
and that `total` reads 569. Verified here before accepting it: limit=2000
returns 569 rows, offset=200 returns the next window, and `total` is 569 in
every response.

The lesson is narrower than "read the docs" and worth stating exactly: a count
of a collection must come from the field that states its size, or from a
traversal proven complete. `len()` of whatever arrived is neither. The
pagination contract is asserted below as its own check, so a count can never
quietly stand in for the catalogue again.
"""

from __future__ import annotations

import json
import re

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

# Anchored on the phrase, not on a value. Two forms are legitimate, and the
# difference is what the sentence PROMISES: an exact figure must equal the
# catalogue, a floor ("500+") must only be a true lower bound. The vendor said
# on 2026-09-05 they are replacing the exact form with the floor form, in the
# same commit that resolved #50 -- so this reads both rather than going
# unmeasurable the moment their fix ships.
EXACT = re.compile(r"trade on ([\d,]+) CLOB pairs", re.I)
FLOOR = re.compile(r"trade on ([\d,]+)\+\s*(?:CLOB )?pairs", re.I)

MAX_LIMIT = 2000


def _page(mcp, arguments: dict):
    """One `list_clob_pairs` response, unwrapped, or a reason it is unusable."""
    payload = mcp.call_raw("list_clob_pairs", arguments)
    result = payload.get("result") or {}
    if result.get("isError"):
        return None, "list_clob_pairs returned an error"
    try:
        body = json.loads((result.get("content") or [{}])[0].get("text", ""))
        return body["result"], None
    except (ValueError, KeyError, IndexError) as exc:
        return None, (f"list_clob_pairs answered in a shape this check cannot "
                      f"read ({type(exc).__name__})")


@qa(component="rest.clob", tier=SafetyTier.SAFE, surface="mcp",
    claim="clob_pair_count")
def test_clob_pair_count_matches_the_catalogue(mcp_anon, rest_anon):
    """The document's number against the size the catalogue states for itself."""
    page, why = _page(mcp_anon, {"limit": MAX_LIMIT})
    if page is None:
        conclude(Measurement(verdict="inconclusive", reason=why,
                             claim_id="clob_pair_count"))
        return

    total = page.get("total")
    if not isinstance(total, int):
        conclude(Measurement(
            verdict="inconclusive",
            reason=("list_clob_pairs no longer states a `total`, so the size of "
                    "the catalogue cannot be read from it -- and counting the "
                    "rows returned would measure the page, not the catalogue"),
            population={"keys": sorted(page)}, claim_id="clob_pair_count"))
        return

    document = rest_anon.get("/llms.txt")
    text = document.text if document.status_code == 200 else ""
    # Floor first: "568+" also matches the exact pattern, and reading it as an
    # exact figure would turn a true statement into a failure.
    floor, exact = FLOOR.search(text), EXACT.search(text)

    if floor is not None:
        claimed = int(floor.group(1).replace(",", ""))
        conclude(Measurement(
            verdict="passed" if total >= claimed else "failed",
            reason=(f"llms.txt promises at least {claimed} CLOB pairs; "
                    f"list_clob_pairs states total={total}."),
            left=f"{claimed}+", right=total,
            sources={"document": "/llms.txt", "catalogue": "MCP list_clob_pairs"},
            population={"total": total, "floor": claimed},
            claim_id="clob_pair_count"))
        return

    if exact is None:
        conclude(Measurement(
            verdict="inconclusive",
            reason=("llms.txt no longer states a CLOB pair count in any form, "
                    "so there is nothing to compare the catalogue against"),
            left=total, sources={"catalogue": "MCP list_clob_pairs"},
            claim_id="clob_pair_count"))
        return

    claimed = int(exact.group(1).replace(",", ""))
    conclude(Measurement(
        verdict="passed" if claimed == total else "failed",
        reason=(f"How many CLOB pairs exist? llms.txt states {claimed} exactly; "
                f"list_clob_pairs states total={total}."),
        left=claimed, right=total,
        sources={"document": "/llms.txt", "catalogue": "MCP list_clob_pairs"},
        population={"total": total, "returned": len(page.get("pairs") or [])},
        claim_id="clob_pair_count"))


@qa(component="rest.clob", tier=SafetyTier.SAFE, surface="mcp")
def test_list_clob_pairs_paginates_consistently(mcp_anon):
    """`total` must describe the collection, not the page that carried it.

    This is the check that would have stopped the false report. It asserts the
    property the earlier count assumed without ever testing: that a default
    call is a WINDOW onto something larger, and that the window and the whole
    are distinguishable from the response itself.
    """
    first, why = _page(mcp_anon, {})
    if first is None:
        conclude(Measurement(verdict="inconclusive", reason=why))
        return

    total, limit = first.get("total"), first.get("limit")
    rows = len(first.get("pairs") or [])
    if not all(isinstance(v, int) for v in (total, limit)):
        conclude(Measurement(
            verdict="inconclusive",
            reason="the response states no total/limit, so pagination cannot "
                   "be checked",
            population={"keys": sorted(first)}))
        return

    # The identity field, taken from the data rather than assumed. The first
    # version of this check keyed on "symbol", which no pair carries -- every
    # row read as None, the two pages "overlapped" on that single None, and it
    # reported a pagination bug that did not exist. An extractor that finds
    # nothing must not be allowed to reach a verdict, so a missing key is
    # Inconclusive here rather than a comparison of absences.
    page_rows = first.get("pairs") or []
    key = next((k for k in ("pair", "id", "symbol")
                if page_rows and all(r.get(k) is not None for r in page_rows)),
               None)
    if key is None:
        conclude(Measurement(
            verdict="inconclusive",
            reason=("no field identifies a pair uniquely in every row, so "
                    "pages cannot be compared for overlap"),
            population={"keys": sorted(page_rows[0]) if page_rows else []}))
        return

    problems = []
    if rows != min(limit, total):
        problems.append(f"a default call returned {rows} rows but states "
                        f"limit={limit} and total={total}")

    if total == rows == limit:
        # The one input where this check cannot see its own subject. The
        # docstring's contract is "that the window and the whole are
        # distinguishable from the response itself" -- and when total, limit
        # and rows are the same number they are not: `total` could be the
        # collection size or the page size and nothing here separates them.
        # Probe past the window rather than concluding either way.
        beyond, why = _page(mcp_anon, {"limit": limit, "offset": rows})
        if beyond is None:
            conclude(Measurement(
                verdict="inconclusive",
                reason=(f"a default call returned {rows} rows with "
                        f"total={total} and limit={limit}, so the window and "
                        f"the collection are the same number and cannot be "
                        f"told apart; the probe past it could not be read: {why}"),
                population={"rows": rows, "total": total, "limit": limit}))
            return
        if beyond.get("pairs"):
            problems.append(
                f"total={total} equals the page size ({limit}) while "
                f"offset={rows} returns {len(beyond['pairs'])} more rows, so "
                f"`total` describes the window and not the collection")

    if total > rows:
        nxt, why = _page(mcp_anon, {"limit": limit, "offset": rows})
        if nxt is None:
            problems.append(f"the second page could not be read: {why}")
        else:
            if nxt.get("total") != total:
                problems.append(f"total changed between pages: {total} then "
                                f"{nxt.get('total')}")
            following = nxt.get("pairs") or []
            if not following:
                problems.append(f"offset={rows} returned nothing although "
                                f"total={total}")
            overlap = ({r.get(key) for r in page_rows}
                       & {r.get(key) for r in following})
            if overlap:
                problems.append(f"{len(overlap)} pair(s) appear on both pages, "
                                f"so paging by offset does not traverse the "
                                f"collection exactly once: {sorted(overlap)[:5]}")

    conclude(Measurement(
        verdict="failed" if problems else "passed",
        reason=("; ".join(problems) if problems else
                f"list_clob_pairs windows a collection of {total} in pages of "
                f"{limit}, and says so in every response"),
        left=problems, right=total,
        sources={"catalogue": "MCP list_clob_pairs"},
        population={"total": total, "page": limit, "first_page_rows": rows}))
