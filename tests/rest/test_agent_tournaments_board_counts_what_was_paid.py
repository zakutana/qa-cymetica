"""The Agent Casino leaderboard's "paid to winners" is what was paid (2026-11-01).

`GET /api/v1/agent-tournaments/leaderboard` serves `paid_usdc` and `paid_et10`, printed on the leaderboard
page as "PAID TO WINNERS". llms.txt on the ET10 prize budget: a prize earned past the monthly cap "is
recorded with status `capped` and is not paid out (the reset on the 1st does not re-credit it)".
`GET /tables/{id}` lists each table's ET10 under `et10_paid[]` with `status`.

**What was seen when this was written** (2026-11-01 ~10:15 UTC, no key). The board: `paid_et10` 1566. The 15
finished tables: `prize_et10` adds up to 1466, plus 100 ET10 back at the ET10 table 15, so 1566; and 1200 of
it is `et10_paid` status "capped" (tables 5 and 11, 600 each). Paid, by their own words: 366. `paid_usdc`
645 agrees with the tables (745 less table 15's 100, which is ET10 under the field `prize_usdc`).

**The rule.** `paid_et10` and `paid_usdc` equal the finished tables' prizes, leaving out what `et10_paid`
records as capped.

NOT asserted: `pending` prizes (they may still be paid, so they count), the per-bot `won_et10` column,
whether capped prizes should be shown somewhere else.

SAFE: GETs only.
"""

from __future__ import annotations

from qa import casino
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

PREFIX = "/api/v1/agent-tournaments"
CLAIM = "agent-tournaments-board-counts-what-was-paid"


@qa(component="rest.agent_tournaments", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_agent_tournaments_board_counts_what_was_paid(rest_anon):
    """The board's totals against every finished table in the lobby."""
    board = rest_anon.get(f"{PREFIX}/leaderboard", params={"window": "all"})
    if board.status_code != 200:
        raise Inconclusive(f"{PREFIX}/leaderboard answered HTTP {board.status_code}")
    lobby = rest_anon.get(f"{PREFIX}/lobby")
    if lobby.status_code != 200:
        raise Inconclusive(f"{PREFIX}/lobby answered HTTP {lobby.status_code}")
    ids = [t.get("id") for t in (lobby.json() or {}).get("tables") or []
           if isinstance(t, dict) and t.get("status") == "done"]
    if not ids:
        raise Inconclusive(f"{PREFIX}/lobby lists no finished table")
    tables = []
    for table_id in ids:
        r = rest_anon.get(f"{PREFIX}/tables/{table_id}")
        if r.status_code != 200:
            raise Inconclusive(f"{PREFIX}/tables/{table_id} answered HTTP {r.status_code}")
        tables.append(r.json())
    body = board.json() or {}
    off = casino.leaderboard_vs_tables(body, tables)
    conclude(Measurement(
        verdict="failed" if off else "passed",
        reason=(off[0]["what"] if off else
                f"the board's totals are what its {len(tables)} finished tables paid"),
        left={"board_totals_off": len(off)},
        right={"board_totals_off": 0},
        population={"tables": ids, "board": {k: body.get(k) for k in ("tables_done", "paid_usdc", "paid_et10")}},
        sources={"board": f"{PREFIX}/leaderboard?window=all (paid_usdc, paid_et10)",
                 "tables": f"{PREFIX}/tables/{{id}} (results.ranked, et10_paid)",
                 "contract": "llms.txt: a prize past the cap is recorded `capped` and is not paid out"},
        claim_id=CLAIM))
