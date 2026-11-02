"""An Agent Casino round is staked from the table's capital, not from the bot's own balance (2026-11-01).

`GET /api/v1/agent-tournaments/tables/{id}` carries `capital_usdc` (a Flash Micro table plays with $25, Pro
with $250), the owner's `your_trades[].amount_usdc` and, on a running table, `my_bot_settings` with
`ranges.trade_size_pct` [1, 10] and `fixed.max_position_pct`. The table page prints "$25 capital" under
every seat, ROI is counted against it, and the table's own Risk line reads "size 10 %".

**What was seen when this was written** (2026-11-01 19:11 UTC, our key). Table 62 (Flash Micro 1H, capital
$25, seat "casino Bollinger Bandit", Risk 10: `trade_size_pct` 10.0, `max_position_pct` 10.0): the first
round it opened was a BTC sell of `amount_usdc` 21.389063, 85.6 % of the table's capital, and it lost it:
`pnl_usdc` -21.389063, ROI -85.5563 %. 21.389063 is 10.0 % of 213.89, the bot's own paper balance
(`/api/v1/agent-tournaments/my-bots`: 216.27 afterwards). Table 40 (Flash Micro 1H, capital $25, seat
"casino Trend Titan"): three rounds of 3.37851, 7.6242 and 11.86989, 13.5 %, 30.5 % and 47.5 % of the
capital. The same bots on Pro tables (capital $250, balance near it) stake 4.5 to 8.7 %.

**The rule.** No round of ours is staked above 10 % of its table's capital, the top of the trade size their
own settings allow (1 to 10 %). Every table our key sat at that started after their fix
(`casino.FIX_RELEASED`), every round in `your_trades`: tables 40 and 62 stay as played, in the population.

**Named fixes, as readings:** the bot's stake is taken from the table's capital, so every round is within
10 % and this passes; or a bot is funded to the table's capital at the seat, so its balance is the capital
and this passes. Fewer than `ROUNDS` rounds read and none over is inconclusive.

NOT asserted: how a round is sized at all, which of the two fixes is right, rounds of a bot away from tables.

SAFE: GETs only, our own seats with our key.
"""

from __future__ import annotations

from qa import casino
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

PREFIX = "/api/v1/agent-tournaments"
CLAIM = "agent-tournaments-stake-stays-inside-the-tables-capital"
ROUNDS = 40


@qa(component="rest.agent_tournaments", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_agent_tournaments_stake_stays_inside_the_tables_capital(rest_trusted):
    """Every round of ours on every table our key sat at since the fix, against that table's capital."""
    lobby = rest_trusted.get(f"{PREFIX}/lobby")
    if lobby.status_code != 200:
        raise Inconclusive(f"{PREFIX}/lobby answered HTTP {lobby.status_code}")
    ids = sorted(t.get("id") for t in (lobby.json() or {}).get("tables") or []
                 if isinstance(t, dict) and t.get("id") is not None)
    if not ids:
        raise Inconclusive(f"{PREFIX}/lobby lists no table")
    over, rounds, read, before_the_fix = [], 0, [], []
    for table_id in ids:
        r = rest_trusted.get(f"{PREFIX}/tables/{table_id}")
        if r.status_code != 200:
            raise Inconclusive(f"{PREFIX}/tables/{table_id} answered HTTP {r.status_code}")
        table = r.json()
        trades = table.get("your_trades")
        if table.get("currency") != "USDC" or not isinstance(trades, list) or not trades:
            continue
        if not casino.played_after_the_fix(table):
            before_the_fix.extend(casino.oversized_stakes(table))
            continue
        read.append(table_id)
        rounds += len(trades)
        over.extend(casino.oversized_stakes(table))
    if not over and rounds < ROUNDS:
        raise Inconclusive(f"{rounds} rounds of ours read on {len(read)} tables since the fix and none over; {ROUNDS} "
                           f"would say the stakes stay inside the capital")
    named = "; ".join(f"table {d['table_id']}: {d['symbol']} round of {d['amount_usdc']} on a capital of "
                      f"{d['capital_usdc']:g} ({d['share_pct']:.1f} %)" for d in over)
    conclude(Measurement(
        verdict="failed" if over else "passed",
        reason=(f"{len(over)} of {rounds} rounds were staked above 10 % of the table's capital: {named}"
                if over else f"none of {rounds} rounds on {len(read)} tables was staked above 10 % of its capital"),
        left={"rounds_over_a_tenth": len(over)},
        right={"rounds_over_a_tenth": 0},
        population={"tables_read": read, "rounds": rounds, "over": over, "before_the_fix": before_the_fix},
        sources={"table": f"{PREFIX}/tables/{{id}} (capital_usdc, your_trades[].amount_usdc)",
                 "range": "my_bot_settings.ranges.trade_size_pct [1, 10], fixed.max_position_pct",
                 "claim": "the page: '$25 capital' under every seat, ROI against it"},
        claim_id=CLAIM))
