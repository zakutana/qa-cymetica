"""The prompt an owner hands an agent for a LIVE table says it is a paper table (2026-11-18).

`GET /api/v1/agent-tournaments/tables/{id}/prompt` is the text a stranger's agent is told to follow. For the live tables
117 / 118 / 119 (mode live, $1 of real USDC from the EventTrader balance) it reads "Take a seat for me at Cymetica Agent
Casino paper table #117 (Live 1H, 1 day, Flash) ... Paper account only. Buy-in 1 paper USDC ... most I can lose 1 paper
USDC". `/rules` `live_note` and the table object say the buy-in is real USDC.

**The rule.** The prompt of a table whose mode is `live` does not call it a paper table, a paper account or a paper buy-in.

VERDICTS. failed: at least one live table's prompt says paper. passed: live tables were read and none does.
inconclusive: a read failed, or the lobby lists no live table (nothing to compare).

NOT asserted: the capital, the max loss or the minimum volume the prompt prints for a live table.
SAFE: GETs only, anonymous routes; nothing is seated or approved.
"""

from __future__ import annotations

import re

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

CLAIM = "agent-tournaments-live-table-prompt-says-paper"
BASE = "/api/v1/agent-tournaments"
PAPER = re.compile(r"\bpaper\s+(?:table|account|USDC)\b", re.I)


def _json(client, url: str, params: dict | None = None):
    try:
        got = client.get(url, params=params)
    except Exception as exc:  # noqa: BLE001 - a failed read is not an empty read (rule 8)
        raise Inconclusive(f"{url} could not be read ({type(exc).__name__})")
    if got.status_code != 200:
        raise Inconclusive(f"{url} answered HTTP {got.status_code}")
    try:
        return got.json()
    except Exception as exc:  # noqa: BLE001
        raise Inconclusive(f"{url} did not answer JSON ({type(exc).__name__})")


def paper_phrases(prompt: str) -> list[str]:
    return sorted({m.group(0).lower() for m in PAPER.finditer(prompt or "")})


@qa(component="rest.agent_tournaments", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_agent_tournaments_live_table_prompt_says_paper(rest_trusted):
    """Every live table's prompt, against the table's own mode."""
    lobby = _json(rest_trusted, f"{BASE}/lobby", {"mode": "live"})
    ids = [t.get("id") for t in (lobby.get("tables") or []) if t.get("mode") == "live"][:6]
    if not ids:
        raise Inconclusive("the live lobby lists no live table to read")
    said: dict = {}
    for i in ids:
        table = _json(rest_trusted, f"{BASE}/tables/{i}")
        if table.get("mode") != "live":
            continue
        found = paper_phrases(str(_json(rest_trusted, f"{BASE}/tables/{i}/prompt").get("prompt") or ""))
        if found:
            said[i] = found
    conclude(Measurement(
        verdict="failed" if said else "passed",
        reason=f"{len(said)} of {len(ids)} live tables' prompts call the table paper: {said}",
        left={"live_tables_whose_prompt_says_paper": said},
        right={"table_mode": "live", "live_note": "a $1 buy-in in real USDC from your EventTrader balance"},
        population={"live_tables_read": len(ids)},
        sources={"lobby": f"GET {BASE}/lobby?mode=live", "table": f"GET {BASE}/tables/{{id}}",
                 "prompt": f"GET {BASE}/tables/{{id}}/prompt",
                 "credential": "X-API-Key, trusted tier (value never recorded)"},
        claim_id=CLAIM))
