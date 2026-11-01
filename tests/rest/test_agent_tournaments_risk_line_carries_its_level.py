"""A seat's Risk line carries the numbers of its level (2026-11-01).

`POST /api/v1/agent-tournaments/seats/{id}/risk`, in their OpenAPI: "trade size L %, stop loss L %, take
profit 4 x L % (at least 5 %)". `GET /tables/{id}`, read by the seat's owner, serves `my_risk` {level,
trade_size_pct, stop_loss_pct, take_profit_pct} and `my_coach_line.risk_line`, printed on the page as "Why
Risk reads so". Two of its sentences claim the level: "(the middle, where a bot starts)" and "as you set it".

**What was seen when this was written** (2026-11-01 ~10:30 UTC, our key, seats a few minutes old with no
coach tune and no owner change at that table). Table 43: "Risk reads 5 (the middle, where a bot starts):
size 5 %, stop loss 2.5 %, take profit 10 %." Table 45: the same with stop loss 3 %, take profit 20 %. Table
46: stop loss 2.5 %, take profit 20 %. Table 44: "Risk reads 8: size 8 %, stop loss 4 %, take profit 32 %, as
you set it": the owner set Risk 8 at another table, and the 4 % came from the coach there. Risk 5 means 5 %,
5 %, 20 %, which is what the two bots that had never sat read (tables 35, 31). So a bot's tuned numbers follow
it to its next table, under a sentence that says otherwise.

**The rule.** While `risk_line` says "where a bot starts" or "as you set it", the three numbers are those
of the level.

NOT asserted: whether numbers should follow a bot between tables (a line that says they did would pass),
a seat of another owner, a line that claims nothing.

SAFE: GETs only, our own seats with our key.
"""

from __future__ import annotations

from qa import casino
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

PREFIX = "/api/v1/agent-tournaments"
CLAIM = "agent-tournaments-risk-line-carries-its-level"


@qa(component="rest.agent_tournaments", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_agent_tournaments_risk_line_carries_its_level(rest_trusted):
    """Every running seat of ours: its Risk line's claim against its numbers."""
    lobby = rest_trusted.get(f"{PREFIX}/lobby")
    if lobby.status_code != 200:
        raise Inconclusive(f"{PREFIX}/lobby answered HTTP {lobby.status_code}")
    ids = [t.get("id") for t in (lobby.json() or {}).get("tables") or []
           if isinstance(t, dict) and t.get("status") == "running"]
    off, read = [], []
    for table_id in ids:
        r = rest_trusted.get(f"{PREFIX}/tables/{table_id}")
        if r.status_code != 200:
            raise Inconclusive(f"{PREFIX}/tables/{table_id} answered HTTP {r.status_code}")
        table = r.json()
        if isinstance(table.get("my_risk"), dict) and isinstance(table.get("my_coach_line"), dict):
            read.append(table_id)
            off += casino.risk_line_off_level(table)
    if not read:
        raise Inconclusive(f"our key holds no running seat at the {len(ids)} running tables; nothing to read")
    named = "; ".join(f"table {o['table_id']}: {o['what']}" for o in off[:5])
    conclude(Measurement(
        verdict="failed" if off else "passed",
        reason=(f"{len(off)} of {len(read)} running seats of ours claim a Risk level their numbers are not on: {named}"
                if off else f"on all {len(read)} running seats of ours the Risk line and its numbers agree"),
        left={"seats_off_their_level": len(off)},
        right={"seats_off_their_level": 0},
        population={"tables": read, "off": off},
        sources={"table": f"{PREFIX}/tables/{{id}} (my_risk, my_coach_line.risk_line)",
                 "contract": "OpenAPI POST /seats/{seat_id}/risk: trade size L %, stop loss L %, take profit 4 x L % (at least 5 %)"},
        claim_id=CLAIM))
