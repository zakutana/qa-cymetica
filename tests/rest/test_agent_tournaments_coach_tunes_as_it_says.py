"""The NEXUS coach tunes the way it tells the owner it does (2026-11-01).

`GET /tables/{id}`, read by the seat's owner, serves `my_coach_line.line`, printed as "What it did". On a
seat the coach has not looked at yet it reads: "The coach is on and has not changed anything yet: it checks
every 10 minutes and tunes once the bot has 5 closed trades." `my_tune_log` holds its tunes and `your_trades`
the closed trades.

**What was seen when this was written** (2026-11-01 ~10:30 UTC, our key). Table 46, 10:21 UTC: that sentence.
Tables 35, 31 and 45 the same morning, minutes after they started: "stop loss 5 → 4 % · rank 1 → 6" at 10:22
with 0 closed trades, "stop loss 5 → 4 % · rank 1 → 2" at 10:26 with 0, "stop loss 3 → 2.5 % · rank 1 → 2" at
10:26 with 0. Table 42: "stop loss 8 → 7 %" with 0. So the owner is told one rule and the bot gets another:
a rival's first trade moves its stop loss before it has traded.

**The rule.** While a seat of ours reads that sentence, no seat of ours has a tune with fewer than five closed
trades before it. The sentence only shows on a fresh seat, for about a minute: with none to read this is
inconclusive, never a pass.

NOT asserted: which of the two should change, whether a tune on rank alone is wise.

SAFE: GETs only, our own seats with our key.
"""

from __future__ import annotations

from qa import casino
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

PREFIX = "/api/v1/agent-tournaments"
CLAIM = "agent-tournaments-coach-tunes-as-it-says"
LOOK_AT = 14  # the newest running and finished tables


@qa(component="rest.agent_tournaments", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_agent_tournaments_coach_tunes_as_it_says(rest_trusted):
    """The coach's sentence on a fresh seat, against the tunes on all our newest seats."""
    lobby = rest_trusted.get(f"{PREFIX}/lobby")
    if lobby.status_code != 200:
        raise Inconclusive(f"{PREFIX}/lobby answered HTTP {lobby.status_code}")
    ids = sorted((t.get("id") for t in (lobby.json() or {}).get("tables") or []
                  if isinstance(t, dict) and t.get("status") in ("running", "done") and t.get("id") is not None),
                 reverse=True)[:LOOK_AT]
    said, off, read = [], [], []
    for table_id in ids:
        r = rest_trusted.get(f"{PREFIX}/tables/{table_id}")
        if r.status_code != 200:
            raise Inconclusive(f"{PREFIX}/tables/{table_id} answered HTTP {r.status_code}")
        table = r.json()
        if not isinstance(table.get("my_seat"), dict):
            continue
        read.append(table_id)
        if casino.FIVE_RULE in str((table.get("my_coach_line") or {}).get("line")):
            said.append(table_id)
        off += casino.coach_rule_vs_tunes(table)
    if not said:
        raise Inconclusive(f"none of our {len(read)} newest seats reads the coach's sentence now: "
                           f"it shows only on a fresh seat, for about a minute")
    named = "; ".join(f"table {o['table_id']}: {o['what']}" for o in off[:5])
    conclude(Measurement(
        verdict="failed" if off else "passed",
        reason=(f"table {said[0]} says the coach {casino.FIVE_RULE}, and {len(off)} of our {len(read)} newest seats "
                f"were tuned before that: {named}"
                if off else f"no seat of ours was tuned before five closed trades ({len(read)} read)"),
        left={"seats_tuned_before_five_trades": len(off)},
        right={"seats_tuned_before_five_trades": 0},
        population={"said_on": said, "tables": read, "off": off},
        sources={"table": f"{PREFIX}/tables/{{id}} (my_coach_line.line, my_tune_log, your_trades)"},
        claim_id=CLAIM))
