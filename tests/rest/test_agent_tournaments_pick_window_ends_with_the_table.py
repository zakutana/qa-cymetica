"""An Agent Casino pick says when it really closes (2026-11-01).

`GET /api/v1/agent-tournaments/tables/{id}` serves `picks` {open, closes_at, closes_in_s}, and the table
page prints "Pick the winner · closes in 23H 59M" from it. `/rules` says a pick is open "while the table
is open and for its first 24 hours". A Flash table can run 1 hour or 5.

**What was seen when this was written** (2026-11-01 ~10:30 UTC, no key needed). Table 44 (1 hour):
`ends_in_s` 2804, `picks.closes_in_s` 85604, `closes_at` 2026-11-02 10:05. Table 42, ended 09:11 the same
day: `picks.open` false and `closes_in_s` 78919, still counting towards a closing that already happened:
a pick does close when the table ends.

**The rule.** On a running table a pick's `closes_in_s` is not later than the table's `ends_in_s`; on a
finished table with `open` false, `closes_in_s` is not above zero.

NOT asserted: the sentence in /rules (which of the two is meant is theirs to say), the page's wording.

SAFE: GETs only.
"""

from __future__ import annotations

from qa import casino
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

PREFIX = "/api/v1/agent-tournaments"
CLAIM = "agent-tournaments-pick-window-ends-with-the-table"
LOOK_AT = 12  # the newest tables are enough: the window is the same field on every one


@qa(component="rest.agent_tournaments", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_agent_tournaments_pick_window_ends_with_the_table(rest_anon):
    """The pick window of the newest running and finished tables against their own clocks."""
    lobby = rest_anon.get(f"{PREFIX}/lobby")
    if lobby.status_code != 200:
        raise Inconclusive(f"{PREFIX}/lobby answered HTTP {lobby.status_code}")
    ids = sorted((t.get("id") for t in (lobby.json() or {}).get("tables") or []
                  if isinstance(t, dict) and t.get("status") in ("running", "done") and t.get("id") is not None),
                 reverse=True)[:LOOK_AT]
    if not ids:
        raise Inconclusive(f"{PREFIX}/lobby lists no running or finished table")
    off, read = [], []
    for table_id in ids:
        r = rest_anon.get(f"{PREFIX}/tables/{table_id}")
        if r.status_code != 200:
            raise Inconclusive(f"{PREFIX}/tables/{table_id} answered HTTP {r.status_code}")
        table = r.json()
        if not isinstance(table.get("picks"), dict):
            continue
        read.append(table_id)
        off += casino.pick_window(table)
    if not read:
        raise Inconclusive(f"none of tables {ids} serves a pick window")
    named = "; ".join(f"table {o['table_id']}: {o['what']}" for o in off[:5])
    conclude(Measurement(
        verdict="failed" if off else "passed",
        reason=(f"{len(off)} of {len(read)} tables say a pick closes later than it does: {named}"
                if off else f"on all {len(read)} tables the pick window ends with the table"),
        left={"tables_with_a_late_pick_window": len(off)},
        right={"tables_with_a_late_pick_window": 0},
        population={"tables": read, "off": off},
        sources={"table": f"{PREFIX}/tables/{{id}} (picks, ends_in_s, status)"},
        claim_id=CLAIM))
