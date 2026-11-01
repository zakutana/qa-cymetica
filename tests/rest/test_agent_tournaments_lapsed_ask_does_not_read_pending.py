"""A seat ask that lapsed does not read as pending to the agent that made it (2026-11-01).

`/agent-casino` says "Each request lapses 24 hours after it was made". llms.txt tells an agent to follow
its ask with `GET /api/v1/agent-tournaments/seats/{id}` and `GET /my-seats`. `GET /lobby`, read by the owner,
carries `my_agents.asks` and `approve_all_ids`, the open asks the "Waiting for your OK" panel draws.

**What was seen when this was written** (2026-11-01 ~10:00 UTC, our key). Seats 120-123 at table 31, asked
on 2026-10-28 (SEAT-0011 to SEAT-0014 in our record), four days past their 24 hours: `/my-seats` says
`seat_status` "pending"; `/seats/120` says `status` "pending", `approve_url` "/agent-casino/approve/120",
`lapses_in_s` null; `/lobby` says `my_agents.asks` 0, `approve_all_ids` []; `/tables/31` lists no seat of
ours. So the owner's panel has dropped them and an agent polling its seat is never told.

**The rule.** A seat `/my-seats` calls pending is one of the owner's open asks in `/lobby`.

NOT asserted: what a lapsed seat should be called instead, or whether it stays listed.

SAFE: GETs only, our own seats with our key.
"""

from __future__ import annotations

from qa import casino
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

PREFIX = "/api/v1/agent-tournaments"
CLAIM = "agent-tournaments-lapsed-ask-does-not-read-pending"


@qa(component="rest.agent_tournaments", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_agent_tournaments_lapsed_ask_does_not_read_pending(rest_trusted):
    """Our seats /my-seats calls pending, against the owner's open asks in /lobby."""
    mine = rest_trusted.get(f"{PREFIX}/my-seats")
    if mine.status_code != 200:
        raise Inconclusive(f"{PREFIX}/my-seats answered HTTP {mine.status_code}")
    seats = [s for s in (mine.json() or {}).get("seats") or [] if isinstance(s, dict)]
    pending = [s.get("seat_id") for s in seats if s.get("seat_status") == "pending"]
    if not pending:
        raise Inconclusive(f"/my-seats lists no pending seat of ours ({len(seats)} seats); nothing to compare")
    lobby = rest_trusted.get(f"{PREFIX}/lobby")
    if lobby.status_code != 200:
        raise Inconclusive(f"{PREFIX}/lobby answered HTTP {lobby.status_code}")
    agents = (lobby.json() or {}).get("my_agents")
    if not isinstance(agents, dict) or not isinstance(agents.get("approve_all_ids"), list):
        raise Inconclusive("/lobby carries no owner block with approve_all_ids for our key")
    off = casino.stale_asks(seats, agents)
    conclude(Measurement(
        verdict="failed" if off else "passed",
        reason=(f"{len(off)} of {len(pending)} seats /my-seats calls pending are not open asks in /lobby "
                f"(approve_all_ids {agents['approve_all_ids']}): seats {[o['seat_id'] for o in off]}"
                if off else f"all {len(pending)} pending seats are open asks"),
        left={"pending_seats_no_open_ask": len(off)},
        right={"pending_seats_no_open_ask": 0},
        population={"pending": pending, "open_asks": agents["approve_all_ids"], "off": off},
        sources={"seats": f"{PREFIX}/my-seats (seat_status)", "owner": f"{PREFIX}/lobby (my_agents.asks, approve_all_ids)"},
        claim_id=CLAIM))
