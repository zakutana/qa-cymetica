"""A bot with no new trade left today does not read as Trading (2026-11-01).

`/rules`, `daily_entries`: "Each bot strategy has a daily allowance of new trades (20 per UTC day ...). A
bot that has used it opens nothing new until 00:00 UTC". `GET /tables/{id}` serves per standings row
`trades_today`, `daily_allowance`, `allowance_used_up`, `bot_state` and `bot_state_label`, and for the owner
`my_seat.volume_short_usdc`, printed as "needs $0.44 more volume to qualify". A bot also trades away from the
tables, so it can arrive with its allowance gone, and nothing at the ask or at Approve says so.

**What was seen when this was written** (2026-11-01 10:21 UTC, our key). Table 46 (1 hour, ending 11:20
UTC), seat 202 "casino Trend Titan", a few seconds after it started: `trades_today` 20, `daily_allowance`
20, `allowance_used_up` true, `bot_state` "trading", `bot_state_label` "Trading", `bot_state_reason` null,
`my_seat.volume_short_usdc` 0.44, `daily_allowance_resets_at` 2026-11-02T00:00. The seat cannot trade before
its table ends. Tables 41 (two seats) showed the same at 08:11, and the coach then tuned them for "no trade
for 14 min" without saying why they did not trade.

**The rule.** A seat of ours whose row says the allowance is used up does not have `bot_state` "trading".

NOT asserted: that such a seat must be refused, what the state should be called, house bots.

SAFE: GETs only, our own seats with our key. A seat at its allowance is not always there to read:
without one this is inconclusive, never a pass.
"""

from __future__ import annotations

from qa import casino
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

PREFIX = "/api/v1/agent-tournaments"
CLAIM = "agent-tournaments-spent-bot-does-not-read-as-trading"


@qa(component="rest.agent_tournaments", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_agent_tournaments_spent_bot_does_not_read_as_trading(rest_trusted):
    """Every running seat of ours at its allowance: what its state says."""
    lobby = rest_trusted.get(f"{PREFIX}/lobby")
    if lobby.status_code != 200:
        raise Inconclusive(f"{PREFIX}/lobby answered HTTP {lobby.status_code}")
    ids = [t.get("id") for t in (lobby.json() or {}).get("tables") or []
           if isinstance(t, dict) and t.get("status") == "running"]
    off, spent = [], []
    for table_id in ids:
        r = rest_trusted.get(f"{PREFIX}/tables/{table_id}")
        if r.status_code != 200:
            raise Inconclusive(f"{PREFIX}/tables/{table_id} answered HTTP {r.status_code}")
        table = r.json()
        mine = table.get("my_seat") if isinstance(table.get("my_seat"), dict) else None
        row = next((s for s in table.get("standings") or [] if isinstance(s, dict) and mine
                    and s.get("seat_id") == mine.get("seat_id")), None)
        if row and row.get("allowance_used_up") is True:
            spent.append(table_id)
            off += casino.allowance_vs_state(table)
    if not spent:
        raise Inconclusive(f"no running seat of ours is at its allowance now ({len(ids)} running tables read)")
    named = "; ".join(f"table {o['table_id']}: {o['what']}" for o in off[:5])
    conclude(Measurement(
        verdict="failed" if off else "passed",
        reason=(f"{len(off)} of {len(spent)} seats of ours with no new trade left today read as trading: {named}"
                if off else f"all {len(spent)} seats of ours at their allowance say so in their state"),
        left={"spent_seats_reading_trading": len(off)},
        right={"spent_seats_reading_trading": 0},
        population={"spent_tables": spent, "off": off},
        sources={"table": f"{PREFIX}/tables/{{id}} (standings[].allowance_used_up, trades_today, bot_state)",
                 "rule": f"{PREFIX}/rules daily_entries"},
        claim_id=CLAIM))
