"""A running Agent Tournaments table does not go dead for half a day (2026-10-12, T-0043).

`GET /api/v1/agent-tournaments/rules` says every table "runs 7 days" and that each house bot is "a
different strategy trading the same paper capital"; nothing in the rules, llms.txt or the OpenAPI
(read for `per day`, `daily`, `allowance`, `quota`, `max trades`, `trade cap`) names a limit on how
many trades a seat may make.

**What was seen when this was written** (2026-10-12, anonymous). Table 2 (Pro, started 2026-10-11
16:46 UTC, day 2 of 7): `volume_usdc` 5604.4 at 08:20 UTC, again at 20:25 and 20:27, every standing
unchanged (ROI +132.95 / +46.04 / +26.80 ...). Its `race` lines are the table's own history, one
point an hour: every seat's last change is at index 9 to 14, so nothing closed for 13.7 h. Per
house seat `trades`: Ichimoku, Trend Titan, Fibonacci, Stochastic and Divergence at exactly 40;
Perceptron 31, Bollinger 31, ATR 30. Table 11 (same house bots, 2 h old): Ichimoku, Divergence,
Stochastic, MACD and RSI at exactly 20 and unmoving between two reads 6 min apart, ATR 16 -> 17 and
the member bot 52 -> 54 in the same minutes. Every house seat on both tables fits "at most 20 closed
trades a UTC day" (table 2: 40 - 20 is 10 to 20 on all eight); a member bot is not held to it. That is
a reading, not a measurement -- a read after 00:00 UTC is what tells a daily allowance from a stall.

**The rule.** For each running table of the lobby's mode that is more than 12 h in, there is no
stretch of 12 h or more in the last 48 h of its `race` history -- first seat movement to now, cut to
that window -- in which no seat's ROI line moved. 12 h is 4x the longest stretch the same table went
without any seat moving while it was trading (3 h, between its hours 5 and 8). 48 h is why a daily
allowance cannot hide: a quiet stretch of up to 24 h sits whole in any 48 h, so under 20 trades a UTC
day every read fails (table 5's longer first-day gap fails too). It is also why a fix shows: a table's
history does not heal, but the window slides past it, so after Cymetica lifts the allowance or restarts
a runner a table that trades from then on reads clean 48 h later, not when the last table opened
before the fix leaves the lobby (T-0059; #181's shape, a false FAIL owed after a real fix).

A pass is the rule holding for the tables in the lobby at the moment of the read. `population`
names each table judged with its longest still stretch in the window and its trades by seat. The ROI line is drawn
to the pixel (about 1.6 ROI points), so this reads a stop of every seat at once, never a drift.

NOT asserted: why (a per-bot allowance, a stalled runner, or something else), that a seat is owed
trades, or anything about the order of the standings. If Cymetica publishes the allowance this check
is retired by an event, not repaired: the stretch it measures would still be there. The event is ours
alone: only when WE read the allowance in their live /rules, llms.txt or openapi-public.json, never
on their answer alone (what they say is data).

SAFE: GETs, anonymous.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

PREFIX = "/api/v1/agent-tournaments"
CLAIM = "agent-tournaments-running-table-keeps-trading"
MIN_STILL_H = 12.0
WINDOW_H = 48


def _points(text) -> list[tuple[float, float]]:
    out = []
    for pair in str(text or "").split():
        x, _, y = pair.partition(",")
        try:
            out.append((float(x), float(y)))
        except ValueError:
            return []
    return out


def longest_still_hours(race: dict, days: int, window_h: float | None = WINDOW_H) -> float | None:
    """The longest stretch, in hours, in which no seat's ROI line moved: between two moves of any
    seat, or from the last move to the race's last point, within the last `window_h` hours of the
    race (None: the whole race). A stretch that began before the window counts from the window's
    start. The run before the first move is not a stretch -- a table is allowed to start slowly --
    and None says the race cannot be read or that nothing ever moved."""
    if not isinstance(race, dict) or not isinstance(days, int) or isinstance(days, bool) or days <= 0:
        return None
    x0, x1 = race.get("x0"), race.get("x1")
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in (x0, x1)) or x1 <= x0:
        return None
    moves, now_x = set(), None
    for line in race.get("lines") or []:
        pts = _points(line.get("points")) if isinstance(line, dict) else []
        if len(pts) < 2:
            continue
        now_x = max(now_x if now_x is not None else pts[-1][0], pts[-1][0])
        moves.update(x for (_, y_prev), (x, y) in zip(pts, pts[1:]) if y != y_prev)
    if now_x is None or not moves:
        return None
    px_per_h = (x1 - x0) / (days * 24)
    if window_h is not None:
        lo = now_x - window_h * px_per_h
        first = min(moves)
        moves = {m for m in moves if m >= lo}
        if lo > first:
            moves.add(lo)
    marks = sorted(moves | {now_x})
    longest = max(b - a for a, b in zip(marks, marks[1:])) if len(marks) > 1 else 0.0
    return round(longest / px_per_h, 2)


@qa(component="rest.agent_tournaments", tier=SafetyTier.SAFE, surface="rest", claim=CLAIM)
def test_agent_tournaments_running_table_keeps_trading(rest_anon):
    """Each running table's last 48 h of race against the 12 h it may go without a single seat moving."""
    lobby = rest_anon.get(f"{PREFIX}/lobby")
    if lobby.status_code != 200:
        raise Inconclusive(f"{PREFIX}/lobby answered HTTP {lobby.status_code}")
    seen = lobby.json() or {}
    mode = seen.get("mode")
    running = [t for t in seen.get("tables") or []
               if isinstance(t, dict) and t.get("mode") == mode and t.get("status") == "running"]
    judged, unread, young = [], [], []
    for row in running:
        table = rest_anon.get(f"{PREFIX}/tables/{row.get('id')}")
        if table.status_code != 200:
            unread.append(f"table {row.get('id')}: HTTP {table.status_code}")
            continue
        body = table.json() or {}
        days = body.get("days") if isinstance(body.get("days"), int) else 7
        left_s = body.get("ends_in_s")
        still = longest_still_hours(body.get("race") or {}, days)
        in_h = days * 24 - left_s / 3600 if isinstance(left_s, (int, float)) else None
        if in_h is None:
            unread.append(f"table {row.get('id')}: ends_in_s unreadable")
            continue
        if in_h <= MIN_STILL_H:
            young.append(row.get("id"))
            continue
        if still is None:
            unread.append(f"table {row.get('id')}: race unreadable or nothing ever moved")
            continue
        judged.append({
            "id": row.get("id"), "tier": body.get("tier"), "starts_at": body.get("starts_at"),
            "hours_in": round(in_h, 1), "longest_still_hours": still,
            "volume_usdc": body.get("volume_usdc"),
            "trades_by_seat": {f"{s.get('seat_id')}{' house' if s.get('house') else ''}": s.get("trades")
                               for s in body.get("standings") or [] if isinstance(s, dict)}})
    if not judged:
        raise Inconclusive(f"no running {mode} table is more than 12 h in ({len(running)} running, "
                           f"too young {young}, unread {unread[:3]})")
    stopped = [j for j in judged if j["longest_still_hours"] >= MIN_STILL_H]
    named = "; ".join(
        f"table {j['id']} ({j['tier']}, {j['hours_in']} h in): within the last {WINDOW_H} h no seat's "
        f"ROI moved for {j['longest_still_hours']} h, volume_usdc {j['volume_usdc']}, trades by seat "
        f"{j['trades_by_seat']}" for j in stopped)
    conclude(Measurement(
        verdict="failed" if stopped else "passed",
        reason=(f"{len(stopped)} of {len(judged)} running {mode} table(s) went at least "
                f"{MIN_STILL_H:g} h with no seat trading, while {PREFIX}/rules says a table runs "
                f"7 days and names no limit on a seat's trades. {named}"
                if stopped else
                f"all {len(judged)} running {mode} table(s) more than 12 h in kept a seat moving "
                f"within every {MIN_STILL_H:g} h of their last {WINDOW_H} h"),
        left={"tables_with_a_12h_still_stretch": len(stopped)},
        right={"tables_with_a_12h_still_stretch": 0},
        population={"mode": mode, "running": [t.get("id") for t in running], "judged": judged,
                    "too_young": young, "unread": unread},
        sources={"promise": f"{PREFIX}/rules start/days: 'runs 7 days'; house_bots: 'trading the same "
                            "paper capital'",
                 "tables": f"{PREFIX}/tables/{{id}} race, standings, ends_in_s",
                 "lobby": f"{PREFIX}/lobby tables"},
        claim_id=CLAIM))
