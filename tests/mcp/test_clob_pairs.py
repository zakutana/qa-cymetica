"""How many CLOB pairs are there? Counted, not quoted.

Report #52 asked why llms.txt says 568 pairs and mcp.json's blurb says 9. Both
of those are sentences, and the check that compared them was prose against
prose: it could not fail, so it verified nothing and eventually established a
PASSING state on a check with no ability to distinguish anything. Its check
was retired.

The plan recorded this as unresolvable "until a captured list_clob_pairs
response exists to count". It exists -- `list_clob_pairs` is a public-tier MCP
tool and answers. So the question stops being two documents disagreeing and
becomes a number against the catalogue that produces it.
"""

from __future__ import annotations

import json
import re

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

CLAIM = re.compile(r"trade on ([\d,]+) CLOB pairs", re.I)


@qa(component="rest.clob", tier=SafetyTier.SAFE, surface="mcp",
    claim="clob_pair_count")
def test_clob_pair_count_matches_the_catalogue(mcp_anon, rest_anon):
    """The document's number against the pairs the platform actually lists."""
    payload = mcp_anon.call_raw("list_clob_pairs", {})
    result = payload.get("result") or {}
    if result.get("isError"):
        conclude(Measurement(
            verdict="inconclusive",
            reason="list_clob_pairs returned an error, so there is no "
                   "catalogue to count",
            population={"response": str(payload)[:300]},
            claim_id="clob_pair_count"))
        return

    try:
        body = json.loads((result.get("content") or [{}])[0].get("text", ""))
        pairs = body["result"]["pairs"]
    except (ValueError, KeyError, IndexError) as exc:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"list_clob_pairs answered in a shape this check cannot "
                   f"count ({type(exc).__name__})",
            claim_id="clob_pair_count"))
        return

    document = rest_anon.get("/llms.txt")
    match = CLAIM.search(document.text) if document.status_code == 200 else None
    if match is None:
        conclude(Measurement(
            verdict="inconclusive",
            reason="llms.txt no longer states a CLOB pair count, so there is "
                   "nothing to compare the catalogue against",
            left=len(pairs), claim_id="clob_pair_count"))
        return

    claimed = int(match.group(1).replace(",", ""))
    listed = len(pairs)
    enabled = sum(1 for p in pairs if p.get("enabled"))

    conclude(Measurement(
        verdict="passed" if claimed == listed else "failed",
        reason=(f"How many CLOB pairs exist? llms.txt says {claimed}; "
                f"list_clob_pairs returns {listed} ({enabled} enabled)."),
        left=claimed, right=listed,
        sources={"document": "/llms.txt", "catalogue": "MCP list_clob_pairs"},
        population={"listed": listed, "enabled": enabled},
        claim_id="clob_pair_count"))
