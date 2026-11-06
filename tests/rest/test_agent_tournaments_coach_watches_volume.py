"""The NEXUS coach lets a seat in 1st place lose its prize on volume and never says so (2026-11-06).

Table 78: our seat finished #1, did not reach the minimum volume ($51.47 traded, /rules min_volume: 3/7 of the
capital on a 1-day Flash table) and took only its buy-in back. Its coach log has 20 entries, the last "no change ·
no closed trade since; rank 1" repeated 19 times; not one mentions volume. Table 80 the same at +4.99 %.

**The rule.** A seat with the coach on that finishes 1st without qualifying, whose coach log never mentions volume
or qualifying, was not coached towards the one thing that decided its prize.

VERDICTS. failed: such a table among the last WINDOW. passed: such tables exist and each coach log speaks of volume
or qualifying (the coach said it, whatever it then did). inconclusive: a read failed, or no recent table of ours
finished 1st unqualified with the coach on. The window moves, so an old table stops counting once it is out of it.

NOT asserted: that the coach could have made the volume (the daily allowance of 20 trades may stop it), only that
it never said so.
SAFE: GETs only; the key is sent by the client in the header and never printed or recorded.
"""

from __future__ import annotations

import json

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

CLAIM = "agent-tournaments-coach-watches-volume"
BASE = "/api/v1/agent-tournaments"
WINDOW = 30
WORDS = ("volume", "qualif")


def _json(client, url: str):
    try:
        got = client.get(url)
    except Exception as exc:  # noqa: BLE001 - a failed read is not an empty read (rule 8)
        raise Inconclusive(f"{url} could not be read ({type(exc).__name__})")
    if got.status_code == 404:
        return None
    if got.status_code != 200:
        raise Inconclusive(f"{url} answered HTTP {got.status_code}")
    try:
        return got.json()
    except Exception as exc:  # noqa: BLE001
        raise Inconclusive(f"{url} did not answer JSON ({type(exc).__name__})")


def first_unqualified(table: dict) -> dict | None:
    """Our seat's result row when it finished 1st without qualifying, with the coach's log present."""
    if table.get("status") != "done" or not table.get("my_tune_log"):
        return None
    mine = {s.get("seat_id") for s in table.get("my_seats") or [] if isinstance(s, dict)}
    if isinstance(table.get("my_seat"), dict):
        mine.add(table["my_seat"].get("seat_id"))
    for row in (table.get("results") or {}).get("ranked") or []:
        if row.get("seat_id") in mine and row.get("rank") == 1 and row.get("qualified") is False:
            return row
    return None


def speaks_of_volume(table: dict) -> bool:
    text = json.dumps(table.get("my_tune_log") or [], ensure_ascii=False).lower()
    return any(w in text for w in WORDS)


@qa(component="rest.agent_tournaments", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_agent_tournaments_coach_watches_volume(rest_trusted):
    """Our recent tables that ended 1st and unqualified: did the coach ever speak of volume?"""
    lobby = _json(rest_trusted, f"{BASE}/lobby") or {}
    newest = max((t.get("id") or 0 for t in lobby.get("tables") or []), default=0)
    if not newest:
        raise Inconclusive("the lobby lists no table")
    cases = {}
    for table_id in range(max(1, newest - WINDOW), newest + 1):
        table = _json(rest_trusted, f"{BASE}/tables/{table_id}")
        row = first_unqualified(table) if isinstance(table, dict) else None
        if row:
            cases[table_id] = {"roi_pct": row.get("roi_pct"), "volume_usdc": row.get("volume_usdc"),
                               "coach_entries": len(table.get("my_tune_log") or []), "speaks_of_volume": speaks_of_volume(table)}
    if not cases:
        raise Inconclusive(f"no table of ours among {newest - WINDOW}..{newest} finished 1st unqualified with the coach on")
    silent = {k: v for k, v in cases.items() if not v["speaks_of_volume"]}
    conclude(Measurement(
        verdict="failed" if silent else "passed",
        reason=(f"{len(silent)} of {len(cases)} recent tables where our seat finished 1st without qualifying have a coach "
                f"log that never mentions volume or qualifying: {sorted(silent)}"),
        left={"tables": cases},
        right={"words_looked_for": list(WORDS)},
        population={"window": [newest - WINDOW, newest]},
        sources={"tables": f"GET {BASE}/tables/{{id}} results.ranked, my_tune_log", "rule": "GET /rules min_volume",
                 "credential": "X-API-Key, trusted tier (value never recorded)"},
        claim_id=CLAIM))
