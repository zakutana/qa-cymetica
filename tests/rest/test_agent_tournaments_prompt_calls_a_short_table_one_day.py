"""The prompt for a 1H or 5H table says "1 day" (2026-11-18).

`GET /api/v1/agent-tournaments/tables/{id}/prompt` opens "Take a seat for me at Cymetica Agent Casino paper table #64
(Flash Micro 1H, 1 day, Flash)". The same table object says hours 1 and `days` 1: the 1-day Flash bucket. A 1-hour table
is not a 1-day table, and the prompt is the text an owner's agent relays.

**The rule.** A table that runs under 24 hours (`hours` < 24) is not called "1 day" in the first line of its prompt.

VERDICTS. failed: a table running under 24 h whose prompt's first line says "1 day". passed: such tables were read and
none does. inconclusive: a read failed, or no table under 24 h was found.

NOT asserted: any figure in the prompt (capital, max loss, minimum volume).
SAFE: GETs only, anonymous routes.
"""

from __future__ import annotations

import re

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

CLAIM = "agent-tournaments-prompt-calls-a-short-table-one-day"
BASE = "/api/v1/agent-tournaments"
ONE_DAY = re.compile(r"\b1 day\b", re.I)


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


def first_line(prompt: str) -> str:
    return (prompt or "").splitlines()[0] if prompt else ""


@qa(component="rest.agent_tournaments", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_agent_tournaments_prompt_calls_a_short_table_one_day(rest_trusted):
    """Every open table under 24 h, its prompt's first line against its hours."""
    ids: dict = {}
    for mode in ("paper", "live"):
        lobby = _json(rest_trusted, f"{BASE}/lobby", {"mode": mode})
        for t in (lobby.get("tables") or [])[:40]:
            # a finished table's prompt answers 409 table_closed: only tables still taking seats have one
            if isinstance(t.get("id"), int) and t.get("status") == "open":
                ids[t["id"]] = mode
    short: dict = {}
    for tid in sorted(ids, reverse=True)[:14]:
        table = _json(rest_trusted, f"{BASE}/tables/{tid}")
        hours = table.get("hours")
        if not isinstance(hours, (int, float)) or hours >= 24:
            continue
        line = first_line(str(_json(rest_trusted, f"{BASE}/tables/{tid}/prompt").get("prompt") or ""))
        short[tid] = {"hours": hours, "days": table.get("days"), "first_line": line[:140],
                      "says_one_day": bool(ONE_DAY.search(line))}
    if not short:
        raise Inconclusive("no open table under 24 hours was found to read")
    bad = {k: v for k, v in short.items() if v["says_one_day"]}
    conclude(Measurement(
        verdict="failed" if bad else "passed",
        reason=f"{len(bad)} of {len(short)} tables under 24 hours are called '1 day' in their prompt: {bad}",
        left={"tables_called_one_day": bad},
        right={"rule": "a table with hours < 24 is not called 1 day"},
        population={"short_tables_read": len(short)},
        sources={"lobby": f"GET {BASE}/lobby?mode=paper|live", "table": f"GET {BASE}/tables/{{id}}",
                 "prompt": f"GET {BASE}/tables/{{id}}/prompt",
                 "credential": "X-API-Key, trusted tier (value never recorded)"},
        claim_id=CLAIM))
