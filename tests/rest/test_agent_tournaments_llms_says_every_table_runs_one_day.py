"""llms.txt says every Agent Casino table runs one day and there are no 7-day tables (2026-11-18).

The Agent Casino entry of `/llms.txt` reads "Every table runs ONE day (Flash) ... There are no 7-day tables." The same
entry then lists live tables at 1H, 5H and 1D; `/lobby` lists open tables of 1 h, 5 h and 24 h; `/rules` carries
`week_tiers` (micro, pro) and `days: 7`, and the MCP tool `agent_tournament_create_table` offers "kind week (7 days)".

**The rule.** A statement that every table runs one day does not stand beside open tables of 1 h and 5 h.

VERDICTS. failed: llms.txt says every table runs ONE day and an open table runs under 24 h. passed: it does not say so,
or no open table runs under 24 h. inconclusive: a read failed or the entry is not found.

NOT asserted: whether 7-day tables exist (the sentence "There are no 7-day tables" against `week_tiers` is reported in
the same report, but is not what this measures).
SAFE: GETs only.
"""

from __future__ import annotations

import re

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

CLAIM = "agent-tournaments-llms-says-every-table-runs-one-day"
BASE = "/api/v1/agent-tournaments"
EVERY = re.compile(r"Every table runs ONE day", re.I)


@qa(component="rest.agent_tournaments", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_agent_tournaments_llms_says_every_table_runs_one_day(rest_trusted):
    """llms.txt's sentence against the lengths of the open tables."""
    try:
        llms = rest_trusted.get("/llms.txt")
        lobby = rest_trusted.get(f"{BASE}/lobby", params={"mode": "paper"})
        rules = rest_trusted.get(f"{BASE}/rules")
    except Exception as exc:  # noqa: BLE001
        raise Inconclusive(f"a read failed ({type(exc).__name__})")
    for name, got in (("llms.txt", llms), ("lobby", lobby), ("rules", rules)):
        if got.status_code != 200:
            raise Inconclusive(f"{name} answered HTTP {got.status_code}")
    if "Agent Casino" not in llms.text:
        raise Inconclusive("llms.txt has no Agent Casino entry")
    says = bool(EVERY.search(llms.text))
    short = sorted({(t.get("tier"), t.get("hours")) for t in (lobby.json().get("tables") or [])
                    if isinstance(t.get("hours"), (int, float)) and t["hours"] < 24})
    conclude(Measurement(
        verdict="failed" if says and short else "passed",
        reason=(f"llms.txt says 'Every table runs ONE day' = {says}; open tables under 24 h: {short}; "
                f"/rules week_tiers {rules.json().get('week_tiers')}"),
        left={"llms_says_every_table_runs_one_day": says},
        right={"open_tables_under_24h": short, "rules_week_tiers": rules.json().get("week_tiers")},
        population={"lobby_tables": len(lobby.json().get("tables") or [])},
        sources={"llms": "GET /llms.txt", "lobby": f"GET {BASE}/lobby?mode=paper", "rules": f"GET {BASE}/rules",
                 "credential": "X-API-Key, trusted tier (value never recorded)"},
        claim_id=CLAIM))
