"""A bot at a 1-day table is not stopped for the whole table by the daily allowance, which resets inside it (2026-11-04).

The ask says "N trades left today (of 20, resets 00:00 UTC)", and a 1-day table holds a 00:00 UTC whatever its start.
ET-33648's answer says a seat's daily allowance starts with the table.

**What was seen when this was written** (2026-11-04 ~16:00 UTC, our key). Table 69 (Flash Micro, 1 day, ended 08:18 UTC),
seat "casino Divergence Dragon": 0 trades; `my_seat.idle` blocker DAILY_TRADE_CAP, "No trade for 24 h. 222 signals blocked:
the daily new-trade allowance was used up". The bot's own activity then has 20 rounds from 08 to 10 UTC, the first hours
after the table ended. Table 74, "casino Fibonacci Phoenix": the same, 46 signals blocked. Tables 75 and 77 at the same
time show 40 trades, two days of the allowance, so the reset itself works for other seats.

**The rule.** No seat of ours at a finished 1-day table reads 0 trades with the blocker DAILY_TRADE_CAP.

NOT asserted: how many trades a bot should make, or the other blockers (open positions, stake below the minimum).

SAFE: GETs only, our own seats with our key.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

PREFIX = "/api/v1/agent-tournaments"
CLAIM = "agent-tournaments-seat-keeps-its-allowance-across-the-reset"
NEWEST_TABLES = 12


@qa(component="rest.agent_tournaments", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_agent_tournaments_seat_keeps_its_allowance_across_the_reset(rest_trusted):
    """Our seats at finished 1-day tables, against the blocker their own panel names."""
    lobby = rest_trusted.get(f"{PREFIX}/lobby")
    if lobby.status_code != 200:
        raise Inconclusive(f"{PREFIX}/lobby answered HTTP {lobby.status_code}")
    done = [t for t in (lobby.json() or {}).get("tables") or []
            if isinstance(t, dict) and t.get("status") == "done" and t.get("hours") == 24 and t.get("mode") == "paper"]
    read, stopped = [], []
    for row in sorted(done, key=lambda t: t.get("id") or 0, reverse=True)[:NEWEST_TABLES]:
        answer = rest_trusted.get(f"{PREFIX}/tables/{row['id']}")
        if answer.status_code != 200:
            continue
        table = answer.json() or {}
        seat = table.get("my_seat")
        if not isinstance(seat, dict):
            continue
        ranked = [r for r in (table.get("results") or {}).get("ranked") or [] if r.get("seat_id") == seat.get("seat_id")]
        if not ranked:
            continue
        read.append(row["id"])
        idle = seat.get("idle") or {}
        if ranked[0].get("trades") == 0 and idle.get("blocker") == "DAILY_TRADE_CAP":
            stopped.append(f"table {row['id']} {seat.get('bot')!r}: {str(idle.get('headline'))[:90]}")
    if not read:
        raise Inconclusive("no finished 1-day table holds a seat of ours")
    conclude(Measurement(
        verdict="failed" if stopped else "passed",
        claim_id=CLAIM,
        left={"seats_stopped_by_the_allowance": len(stopped)},
        right={"seats_stopped_by_the_allowance": 0},
        reason=f"{len(stopped)} of {len(read)} of our seats at finished 1-day tables made no trade for the whole table, "
               f"blocked by a daily allowance that resets inside it: " + "; ".join(stopped),
        sources={"table": f"{PREFIX}/tables/{{id}} (my_seat.idle, results.ranked[].trades)", "lobby": f"{PREFIX}/lobby"},
        population={"tables": read},
    ))
