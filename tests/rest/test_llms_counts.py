"""What llms.txt says about its own sizes, after the vendor's 2026-09-05 reply.

Two findings were resolved there in different ways, and the difference is why
they need different checks rather than one shared one.

#50 (mcp_resource_count) was resolved by REMOVAL. llms.txt used to publish a
fixed "N tools, M resources" line, and no single number can be right for a
catalogue scoped to the caller's trust tier -- measured today, the same
manifest serves 35 tools anonymously and 56 to an ALLIED caller. They deleted
the figure and pointed at tools/list. That is the correct fix for this class,
because there was no in-place number that would have been true; but it leaves
the old check with nothing to read, and a check that reads nothing scores
Inconclusive forever while looking, on a dashboard, like a settled row.

#55 (llms_agent_count_self_consistent) was resolved by CORRECTION: 10 became
11 and the duplicate sentence was consolidated. The old check compared two
particular sentences to each other, so consolidation removes an operand and
it would have gone green by losing the thing it compared -- the same failure
mode the audit was written about.

So both are replaced by guards on the resolutions themselves. Each is anchored
to a PLACE in the document rather than to a value expected to be found there,
and each fails if the vendor regresses.
"""

from __future__ import annotations

import re

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

LLMS = "/llms.txt"
SPECIES = "/api/v1/agents/species"

# A fixed catalogue size stated as prose. Deliberately broader than the exact
# phrase they removed: the defect is any hardcoded size for a tier-scoped
# catalogue, however it comes to be worded.
FIXED_SIZE = re.compile(r"(\d+)\s+(?:MCP\s+)?(tools|resources|prompts)\b", re.I)

# Their replacement -- what makes a reader able to obtain the right number for
# themselves. Asserted rather than assumed.
POINTER = "tools/list"

# Any sentence stating how many agent species exist, anchored on the noun, so
# a new sentence in a new section is covered without editing this file.
AGENT_COUNT = re.compile(r"(\d+)\s+(?:AI\s+)?(?:trading\s+)?agent\s+species", re.I)


def _document(rest):
    response = rest.get(LLMS)
    if response.status_code != 200:
        return None, f"{LLMS} answered HTTP {response.status_code}"
    return response.text, None

MCP_ANCHORS = ("eventtrader-mcp", "MCP Server:")



@qa(component="mcp.protocol", tier=SafetyTier.SAFE, surface="rest",
    claim="mcp_resource_count")
def test_llms_states_no_fixed_size_for_a_tier_scoped_catalogue(rest_anon):
    """The MCP catalogue is per-tier, so llms.txt must not publish one size."""
    text, why = _document(rest_anon)
    if text is None:
        conclude(Measurement(verdict="inconclusive", reason=why,
                             claim_id="mcp_resource_count"))
        return

    # Only the lines that describe the MCP server itself. Counting every "N
    # tools" in the whole document would sweep up prose about other things and
    # fail for reasons that have nothing to do with the catalogue.
    #
    # These are their words, so an empty section means our anchors have gone
    # stale, not that they stopped stating a size -- see the guard below.
    section = [line for line in text.splitlines()
               if any(anchor in line for anchor in MCP_ANCHORS)]
    if not section:
        # Zero lines examined -- and the verdict below would then have read
        # "llms.txt states no fixed catalogue size", asserted about a section
        # never read. The anchors are two string literals of THEIRS: rename
        # the server or drop the heading and this empties, while POINTER is
        # searched over the whole 42KB document and stays true. This vendor
        # has removed the sentences behind #50 and #55 before, and the sibling
        # in this file already goes inconclusive when its operand disappears.
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"no line of llms.txt carries either anchor this check "
                   f"scopes on ({' or '.join(repr(a) for a in MCP_ANCHORS)}), "
                   f"so there was no section to read a catalogue size out of",
            population={"mcp_lines": 0, "doc_bytes": len(text)},
            sources={"document": LLMS},
            claim_id="mcp_resource_count"))
        return
    stated = sorted({f"{n} {noun.lower()}"
                     for line in section for n, noun in FIXED_SIZE.findall(line)})
    points_at_live = POINTER in text

    if stated:
        reason = ("llms.txt publishes a fixed catalogue size again: "
                  + ", ".join(stated))
    elif not points_at_live:
        reason = ("llms.txt states no fixed catalogue size, but no longer "
                  "points a reader at tools/list either, so there is now no "
                  "way to learn the catalogue for one's own tier")
    else:
        reason = ("llms.txt states no fixed catalogue size and directs the "
                  "reader to tools/list for their own tier")

    conclude(Measurement(
        verdict="failed" if (stated or not points_at_live) else "passed",
        reason=reason,
        left=stated, right=POINTER if points_at_live else None,
        sources={"document": LLMS},
        population={"mcp_lines": len(section), "doc_bytes": len(text)},
        claim_id="mcp_resource_count"))


@qa(component="rest.agents", tier=SafetyTier.SAFE, surface="rest",
    claim="llms_agent_count_self_consistent")
def test_every_agent_count_in_llms_matches_the_live_species_list(rest_anon):
    """Every stated species count, everywhere in the document, against live.

    Strictly stronger than the self-consistency check it replaces: that one
    compared two sentences to each other, so two sentences agreeing on a wrong
    number passed it, and consolidating them to one made it vacuous. This
    reads every occurrence and settles them all against the catalogue, so it
    fails on internal disagreement AND on agreed-upon drift.
    """
    text, why = _document(rest_anon)
    if text is None:
        conclude(Measurement(verdict="inconclusive", reason=why,
                             claim_id="llms_agent_count_self_consistent"))
        return

    catalogue = rest_anon.get(SPECIES)
    if catalogue.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"{SPECIES} answered HTTP {catalogue.status_code}, so the "
                   f"document's figures cannot be settled",
            claim_id="llms_agent_count_self_consistent"))
        return

    body = catalogue.json()
    live = body if isinstance(body, list) else (body.get("species") or [])
    if not live:
        # A 200 we could not parse is not a catalogue of zero. Both shapes we
        # know are handled above; a third would fall through to live_count 0
        # and report "llms.txt says 11, the catalogue lists 0" -- a sentence
        # that is obviously wrong to a reader and would be sent to the vendor
        # in earnest. The same principle as rule 8, one layer in: an empty
        # parse is not a measurement.
        conclude(Measurement(
            verdict="inconclusive",
            reason=(f"{SPECIES} answered 200 but no species could be read out "
                    f"of it (top-level keys: "
                    f"{sorted(body)[:6] if isinstance(body, dict) else type(body).__name__}), "
                    f"so the document's figures cannot be settled"),
            sources={"catalogue": SPECIES},
            claim_id="llms_agent_count_self_consistent"))
        return
    live_count = len(live)

    stated = [int(n) for n in AGENT_COUNT.findall(text)]
    if not stated:
        conclude(Measurement(
            verdict="inconclusive",
            reason=("llms.txt no longer states an agent species count "
                    "anywhere, so there is nothing to reconcile"),
            right=live_count, sources={"document": LLMS},
            claim_id="llms_agent_count_self_consistent"))
        return

    wrong = sorted({n for n in stated if n != live_count})
    conclude(Measurement(
        verdict="failed" if wrong else "passed",
        reason=(f"llms.txt states the species count in {len(stated)} place(s); "
                f"the live catalogue lists {live_count}"
                + (f", and {len(wrong)} disagree: {wrong}" if wrong
                   else ", and every one of them agrees")),
        left=sorted(set(stated)), right=live_count,
        sources={"document": LLMS, "catalogue": SPECIES},
        population={"occurrences": len(stated), "live_species": live_count},
        claim_id="llms_agent_count_self_consistent"))
