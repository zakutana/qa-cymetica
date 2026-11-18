"""Two Agent Casino MCP tools still say ET10 goes to the top 3 (2026-11-18).

Since the build of 10 Nov 13:58 UTC `/rules` `et10_prizes` says ET10 goes to the top 2 qualified member seats
(85 / 42 at a 1-day table). The descriptions served by `tools/list` for `agent_tournaments_open_tables` ("1,000 ET10 on
top for the top 3") and `agent_tournament_create_table` ("the same ET10 on top for the top 3 as the lobby's tables") still
say three. An agent reads these descriptions, not the page.

**The rule.** When `/rules` says ET10 goes to the top 2, no served Agent Casino tool description says ET10 goes to the
top 3.

VERDICTS. failed: /rules says top 2 and at least one agent_tournament* tool description says top 3 / top three.
passed: /rules says top 2 and none does. inconclusive: a read failed, /rules does not say top 2, or no such tool is served.

NOT asserted: which of the two is the intended rule.
SAFE: tools/list and one GET; nothing is called.
"""

from __future__ import annotations

import re

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

CLAIM = "agent-tournament-tools-say-et10-goes-to-top-three"
THREE = re.compile(r"\btop\s+(?:three|3)\b", re.I)
TWO = re.compile(r"\btop\s+(?:two|2)\b", re.I)


@qa(component="mcp.tools_list", tier=SafetyTier.SAFE, surface="mcp", claim=CLAIM)
def test_agent_tournament_tools_say_et10_goes_to_top_three(mcp_trusted, rest_trusted):
    """/rules says top 2; every served Agent Casino tool description against it."""
    try:
        got = rest_trusted.get("/api/v1/agent-tournaments/rules")
        rules = got.json() if got.status_code == 200 else {}
    except Exception as exc:  # noqa: BLE001
        raise Inconclusive(f"/rules could not be read ({type(exc).__name__})")
    prizes = str(rules.get("et10_prizes") or "")
    if not TWO.search(prizes):
        raise Inconclusive(f"/rules et10_prizes does not say the top 2 (nothing to compare): {prizes[:120]!r}")
    tools = [t for t in mcp_trusted.tools_list() if str(t.get("name", "")).startswith("agent_tournament")]
    if not tools:
        raise Inconclusive("no agent_tournament tool is served")
    bad = {}
    for t in tools:
        text = str(t.get("description") or "")
        hit = THREE.search(text)
        if hit:
            bad[t["name"]] = text[max(0, hit.start() - 60):hit.end() + 20]
    conclude(Measurement(
        verdict="failed" if bad else "passed",
        reason=f"/rules gives ET10 to the top 2, and {len(bad)} of {len(tools)} Agent Casino tool descriptions say three: {bad}",
        left={"tools_saying_three": bad},
        right={"rules_et10_prizes": prizes[:160]},
        population={"tools_read": len(tools)},
        sources={"rules": "GET /api/v1/agent-tournaments/rules", "served": "tools/list"},
        claim_id=CLAIM))
