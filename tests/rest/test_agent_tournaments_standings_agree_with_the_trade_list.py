"""On a finished Agent Casino table the standings and the owner's own trade list count the same trades (2026-11-01).

`GET /api/v1/agent-tournaments/tables/{id}`, read with the owner's key, carries the standings row
of every seat (`results.ranked[]`: `trades`, `volume_usdc`, `pnl_usdc`, `roi_pct`) and, for the seat
the key owns, `your_trades`, the list the table page shows as "Your trades". The page says under that
list: "N counted trades · $V volume (the same counts as the standings)", and the standings row of the
same seat is what the prize and the rank are paid from.

**What was seen when this was written** (2026-11-01 ~08:40 UTC, our key). Table 40 (Flash Micro 1H,
ended 2026-10-31 23:36 UTC), seat 143 "casino Trend Titan": `results.ranked` says `trades: 4`,
`volume_usdc: 24.85`, `pnl_usdc: -5.64`, `roi_pct: -22.5816`; `your_trades` lists 3 closed trades,
`amount_usdc` 3.37851 + 11.86989 + 7.6242 = 22.8726 and `pnl_usdc` -3.37851 - 11.86989 + 7.6242 =
-7.6242, which is -30.50 % of the $25 capital, the figure the page's "AT THE END" row prints. The
rank, the prize and the capital paid back ($19.36) follow the first set; the trade list shows the second.

**The rule.** For every finished table whose answer to our key names a seat of ours (`my_seat`) and
lists at least one trade, the count, the volume and the profit of `your_trades` equal that seat's
standings row: the same number of trades, volume and P&L within two cents.

NOT asserted: which side is right, any table still running (trades there close while we read), a seat
of ours that is not `my_seat` (the table lists the trades of one seat only), the page's wording.

SAFE: GETs only, our own seats with our key.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

PREFIX = "/api/v1/agent-tournaments"
CLAIM = "agent-tournaments-standings-agree-with-the-trade-list"
CENTS = 0.02


def disagreements(table: dict) -> list[dict]:
    """The seats of this table where the standings row and `your_trades` count differently. Empty
    when the table names no seat of ours, lists no trade, or the two agree."""
    mine = table.get("my_seat")
    trades = table.get("your_trades")
    if not isinstance(mine, dict) or not isinstance(trades, list) or not trades:
        return []
    ranked = ((table.get("results") or {}).get("ranked")) or []
    row = next((r for r in ranked if isinstance(r, dict) and r.get("seat_id") == mine.get("seat_id")), None)
    if row is None:
        return []
    closed = [t for t in trades if isinstance(t, dict) and t.get("closed")]
    listed = {"trades": len(closed),
              "volume_usdc": round(sum(float(t.get("amount_usdc") or 0) for t in closed), 2),
              "pnl_usdc": round(sum(float(t.get("pnl_usdc") or 0) for t in closed), 2)}
    said = {"trades": row.get("trades"), "volume_usdc": row.get("volume_usdc"), "pnl_usdc": row.get("pnl_usdc")}
    if any(not isinstance(v, (int, float)) or isinstance(v, bool) for v in said.values()):
        return []
    off = (said["trades"] != listed["trades"]
           or abs(said["volume_usdc"] - listed["volume_usdc"]) > CENTS
           or abs(said["pnl_usdc"] - listed["pnl_usdc"]) > CENTS)
    return ([{"table_id": table.get("id"), "seat_id": mine.get("seat_id"), "bot": mine.get("bot"),
              "standings": said, "trade_list": listed}] if off else [])


@qa(component="rest.agent_tournaments", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_agent_tournaments_standings_agree_with_the_trade_list(rest_trusted):
    """Every finished table our key sat at: its standings row against its own trade list."""
    lobby = rest_trusted.get(f"{PREFIX}/lobby")
    if lobby.status_code != 200:
        raise Inconclusive(f"{PREFIX}/lobby answered HTTP {lobby.status_code}")
    ids = sorted(t.get("id") for t in (lobby.json() or {}).get("tables") or []
                 if isinstance(t, dict) and t.get("status") == "done" and t.get("id") is not None)
    if not ids:
        raise Inconclusive(f"{PREFIX}/lobby lists no finished table")
    off, read = [], []
    for table_id in ids:
        r = rest_trusted.get(f"{PREFIX}/tables/{table_id}")
        if r.status_code != 200:
            raise Inconclusive(f"{PREFIX}/tables/{table_id} answered HTTP {r.status_code}")
        table = r.json()
        if table.get("status") != "done" or not table.get("your_trades"):
            continue
        read.append(table_id)
        off.extend(disagreements(table))
    if not read:
        raise Inconclusive(f"none of the {len(ids)} finished tables lists a trade of ours "
                           f"(tables {ids}); nothing to compare")
    named = "; ".join(f"table {d['table_id']} seat {d['seat_id']} ({d['bot']!r}): standings "
                      f"{d['standings']}, trade list {d['trade_list']}" for d in off)
    conclude(Measurement(
        verdict="failed" if off else "passed",
        reason=(f"{len(off)} of {len(read)} finished tables show a seat of ours with one set of numbers "
                f"in the standings and another in its own trade list: {named}"
                if off else
                f"on all {len(read)} finished tables the standings and the trade list agree"),
        left={"tables_disagreeing": len(off)},
        right={"tables_disagreeing": 0},
        population={"finished_tables": ids, "tables_compared": read, "disagreeing": off},
        sources={"table": f"{PREFIX}/tables/{{id}} (results.ranked[], your_trades, my_seat)",
                 "lobby": f"{PREFIX}/lobby (tables[], status done)",
                 "claim": "the page: 'N counted trades · $V volume (the same counts as the standings)'"},
        claim_id=CLAIM))
