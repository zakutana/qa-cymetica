"""The casino department's judgement, with no network in it: what one Agent Casino table says about
itself, compared with itself.

Every comparison here was first a defect found by hand on 2026-11-01 (docs/agent-casino-test-2026-11-01.md):
a table's own answer holds the standings, the owner's trade list, the coach's log, the public feed of
changes and the settings, and a test of the casino is whether they tell one story. `contradictions`
returns what does not; `scripts/casino.py` reads the tables, keeps the diary and does the writes.

A comparison that cannot be made says nothing (a table with no seat of ours has no trade list): a
missing reading is not a contradiction and not an agreement either, and the tick counts what it read.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

# Their /risk route: "trade size L %, stop loss L %, take profit 4 x L % (at least 5 %)".
RISK_FLOOR_TAKE = 5.0
# A tune and its row in the public feed are written apart by a second or two.
FEED_WINDOW_S = 15
CENTS = 0.02
ROI_POINTS = 0.1
# "it checks every 10 minutes": two and a half of those without a row is more than a late check.
CADENCE_MAX_MIN = 25
ET10_PENDING_HOURS = 6
FIVE_RULE = "tunes once the bot has 5 closed trades"
FIVE = 5

# One of ours to a table (the operator's own rule, MSG-0293), at most this many tables at once.
MAX_RUNNING = 6
# The least tried first. A coach on, B coach off, C Risk at its ends, D an owner's stop loss the
# coach then has to live with, E a bot already at another table (the suspicion behind #234).
VARIANTS = ("A", "B", "C1", "C10", "D", "E")

_STOP = re.compile(r"stop loss ([\d.]+) → ([\d.]+) %")
_TAKE = re.compile(r"take profit ([\d.]+) → ([\d.]+) %")
_LANE = re.compile(r"\b(PERP|CLOB) (\S+) (on|off)\b")
_LOSSES = re.compile(r"(\d+) losses in a row on ([A-Za-z0-9/]+): (-?[\d.]+) USDC")
_NONE_YET = re.compile(r"no trade for \d+ min \(none yet\)")
_LANES = {"PERP": "perpetual", "CLOB": "clob"}


def _when(value) -> datetime | None:
    if not isinstance(value, str) or not value:
        return None
    try:
        at = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return at if at.tzinfo else at.replace(tzinfo=timezone.utc)


def _number(value) -> float | None:
    return float(value) if isinstance(value, (int, float)) and not isinstance(value, bool) else None


def _found(key: str, table: dict, what: str, **fields) -> dict:
    return {"key": key, "table_id": table.get("id"), "what": what, **fields}


def my_seat_ids(table: dict) -> set:
    """Every seat the table names as the caller's: `my_seat` carries only the first (#210)."""
    seats = [table.get("my_seat"), *(table.get("my_seats") or [])]
    return {s.get("seat_id") for s in seats if isinstance(s, dict) and s.get("seat_id") is not None}


def _my_id(table: dict):
    seat = table.get("my_seat")
    return seat.get("seat_id") if isinstance(seat, dict) else None


def _tunes(table: dict) -> list[dict]:
    """The coach's TUNED rows, oldest first."""
    rows = [r for r in table.get("my_tune_log") or []
            if isinstance(r, dict) and r.get("kind") == "TUNED" and r.get("by") == "NEXUS" and _when(r.get("at"))]
    return sorted(rows, key=lambda r: _when(r["at"]))


def _closed(table: dict) -> list[dict]:
    """The owner's closed trades, newest first."""
    rows = [t for t in table.get("your_trades") or []
            if isinstance(t, dict) and t.get("closed") and _when(t.get("at"))]
    return sorted(rows, key=lambda t: _when(t["at"]), reverse=True)


def _feed(table: dict, seat_id, by: str | None = None) -> list[dict]:
    return [c for c in table.get("changes") or [] if isinstance(c, dict) and c.get("seat_id") == seat_id
            and _when(c.get("at")) and (by is None or c.get("by") == by)]


def standings_vs_trades(table: dict) -> list[dict]:
    """#234: the seat's standings row against the list the page prints under it, a finished table only."""
    seat_id = _my_id(table)
    ranked = ((table.get("results") or {}).get("ranked")) or []
    row = next((r for r in ranked if isinstance(r, dict) and r.get("seat_id") == seat_id), None)
    if table.get("status") != "done" or row is None or not table.get("your_trades"):
        return []
    closed = _closed(table)
    listed = {"trades": len(closed),
              "volume_usdc": round(sum(_number(t.get("amount_usdc")) or 0 for t in closed), 2),
              "pnl_usdc": round(sum(_number(t.get("pnl_usdc")) or 0 for t in closed), 2)}
    said = {k: row.get(k) for k in listed}
    if any(_number(v) is None for v in said.values()):
        return []
    if (said["trades"] == listed["trades"] and abs(said["volume_usdc"] - listed["volume_usdc"]) <= CENTS
            and abs(said["pnl_usdc"] - listed["pnl_usdc"]) <= CENTS):
        return []
    return [_found("standings_vs_trades", table, f"standings {said}, trade list {listed}",
                   seat_id=seat_id)]


def accounts(table: dict) -> list[dict]:
    """A finished table closes: pot = paid seats x buy-in, prizes = pot, ROI = P&L / capital, rank
    follows ROI, and a house bot is paid nothing."""
    ranked = [r for r in ((table.get("results") or {}).get("ranked")) or [] if isinstance(r, dict)]
    if table.get("status") != "done" or not ranked:
        return []
    out = []
    pot = _number(table.get("pot_usdc"))
    buyin, paid = _number(table.get("buyin_usdc")), _number(table.get("paid_seats"))
    if pot is not None and buyin is not None and paid is not None and abs(pot - buyin * paid) > CENTS:
        out.append(_found("pot_vs_paid_seats", table, f"pot {pot}, {paid:g} paid seats x {buyin:g}"))
    prizes = sum(_number(r.get("prize_usdc")) or 0 for r in ranked)
    if pot is not None and abs(prizes - pot) > CENTS:
        out.append(_found("prizes_vs_pot", table, f"prizes add up to {prizes:g}, pot {pot:g}"))
    capital = _number(table.get("capital_usdc"))
    for row in ranked:
        roi, pnl = _number(row.get("roi_pct")), _number(row.get("pnl_usdc"))
        if capital and roi is not None and pnl is not None and abs(pnl / capital * 100 - roi) > ROI_POINTS \
                and row.get("venue") in (None, "cymetica"):
            out.append(_found("roi_vs_pnl", table, f"seat {row.get('seat_id')}: ROI {roi:g} %, P&L {pnl:g} "
                                                   f"on capital {capital:g}", seat_id=row.get("seat_id")))
        if row.get("house") and (_number(row.get("prize_usdc")) or 0) > 0:
            out.append(_found("house_paid", table, f"house seat {row.get('seat_id')} was paid "
                                                   f"{row.get('prize_usdc')}", seat_id=row.get("seat_id")))
    order = sorted((r for r in ranked if _number(r.get("rank")) is not None), key=lambda r: r["rank"])
    rois = [_number(r.get("roi_pct")) for r in order]
    if any(a is not None and b is not None and a < b for a, b in zip(rois, rois[1:])):
        out.append(_found("rank_vs_roi", table, f"rank order reads ROI {rois}"))
    return out


def tune_vs_feed(table: dict) -> list[dict]:
    """Every tune of the owner's log is a row of the public feed, and the other way round."""
    seat_id = _my_id(table)
    if seat_id is None or table.get("my_tune_log") is None:
        return []
    tunes, feed = _tunes(table), _feed(table, seat_id, "NEXUS")
    out = []
    for tune in tunes:
        at = _when(tune["at"])
        if not any(abs((_when(c["at"]) - at).total_seconds()) <= FEED_WINDOW_S for c in feed):
            out.append(_found("tune_vs_feed", table, f"log has a tune at {tune['at']} ({tune.get('text')!r}), "
                                                     f"the public feed has no row for it", seat_id=seat_id))
    for row in feed:
        at = _when(row["at"])
        if not any(abs((_when(t["at"]) - at).total_seconds()) <= FEED_WINDOW_S for t in tunes):
            out.append(_found("tune_vs_feed", table, f"public feed has a NEXUS row at {row['at']} "
                                                     f"({row.get('what')}), the log has no tune", seat_id=seat_id))
    return out


def _chain(tunes: list[dict], pattern, name: str, owner_at: list[datetime], table: dict, seat_id) -> list[dict]:
    """A tune starts from the number the one before it left, unless the owner moved it in between."""
    out, last_to, last_at = [], None, None
    for tune in tunes:
        m = pattern.search(tune.get("text") or "")
        if not m:
            continue
        before, after, at = float(m.group(1)), float(m.group(2)), _when(tune["at"])
        touched = any(last_at is not None and last_at < o < at for o in owner_at)
        if last_to is not None and before != last_to and not touched:
            out.append(_found("tune_vs_settings", table, f"{name} tune starts from {before:g}, the one "
                                                         f"before left {last_to:g}", seat_id=seat_id))
        last_to, last_at = after, at
    return out


def tune_vs_settings(table: dict) -> list[dict]:
    """What the log says the coach did is what the seat's settings now say, unless the owner moved them
    after; and the tunes chain. A running table only: a finished one serves no settings."""
    seat_id, settings = _my_id(table), table.get("my_bot_settings")
    tunes = _tunes(table)
    if seat_id is None or not tunes:
        return []
    owner_at = [_when(c["at"]) for c in _feed(table, seat_id, "OWNER")]
    out = _chain(tunes, _STOP, "stop loss", owner_at, table, seat_id)
    out += _chain(tunes, _TAKE, "take profit", owner_at, table, seat_id)
    if table.get("status") != "running" or not isinstance(settings, dict):
        return out
    moved_after = max(owner_at, default=None)
    for pattern, field, name in ((_STOP, "stop_loss_pct", "stop loss"), (_TAKE, "take_profit_pct", "take profit")):
        hits = [(t, pattern.search(t.get("text") or "")) for t in tunes]
        hits = [(t, m) for t, m in hits if m]
        now = _number(settings.get(field))
        if hits and now is not None and now != float(hits[-1][1].group(2)) \
                and not (moved_after and moved_after > _when(hits[-1][0]["at"])):
            out.append(_found("tune_vs_settings", table, f"last tune left {name} at {hits[-1][1].group(2)}, "
                                                         f"the settings say {now:g}", seat_id=seat_id))
    lanes = settings.get("lanes")
    if isinstance(lanes, dict):
        last: dict[tuple, tuple] = {}
        for tune in tunes:
            for lane, symbol, state in _LANE.findall(tune.get("text") or ""):
                last[(lane, symbol.split("/")[0])] = (state, tune)
        for (lane, symbol), (state, tune) in last.items():
            row = lanes.get(_LANES[lane])
            if not isinstance(row, dict) or (moved_after and moved_after > _when(tune["at"])):
                continue
            listed = symbol in (row.get("scope") or [])
            if (state == "off") == listed:
                out.append(_found("tune_vs_settings", table, f"last tune turned {lane} {symbol} {state}, the "
                                                             f"lane reads {row}", seat_id=seat_id))
    return out


def tune_reason(table: dict) -> list[dict]:
    """The reason a tune gives is in the trades: "N losses in a row on X: -Y USDC", "(none yet)"."""
    seat_id, closed = _my_id(table), _closed(table)
    if seat_id is None or table.get("your_trades") is None:
        return []
    out = []
    for tune in _tunes(table):
        at, text = _when(tune["at"]), tune.get("text") or ""
        before = [t for t in closed if _when(t["at"]) <= at]
        m = _LOSSES.search(text)
        if m:
            count, symbols, total = int(m.group(1)), set(m.group(2).split("/")), float(m.group(3))
            last = before[:count]
            lost = [_number(t.get("pnl_usdc")) or 0 for t in last]
            if len(last) < count or any(p >= 0 for p in lost) or abs(sum(lost) - total) > CENTS \
                    or not {t.get("symbol") for t in last} <= symbols:
                out.append(_found("tune_reason", table, f"{text!r} at {tune['at']}, the last {count} closed "
                                                        f"trades were {lost}", seat_id=seat_id))
        if _NONE_YET.search(text) and before:
            out.append(_found("tune_reason", table, f"{text!r} at {tune['at']}, and {len(before)} trade(s) "
                                                    f"had closed by then", seat_id=seat_id))
    return out


def level_numbers(level: int) -> tuple[float, float, float]:
    """Size, stop loss and take profit that a Risk level means, by their /risk route."""
    return float(level), float(level), max(RISK_FLOOR_TAKE, 4.0 * level)


def risk_line_off_level(table: dict) -> list[dict]:
    """A line that claims the level ("as you set it", "where a bot starts") carries the level's numbers."""
    risk, line = table.get("my_risk"), table.get("my_coach_line")
    if table.get("status") != "running" or not isinstance(risk, dict) or not isinstance(line, dict):
        return []
    text, level = str(line.get("risk_line") or ""), risk.get("level")
    if "as you set it" not in text and "where a bot starts" not in text or not isinstance(level, int):
        return []
    have = tuple(_number(risk.get(k)) for k in ("trade_size_pct", "stop_loss_pct", "take_profit_pct"))
    if have == level_numbers(level) or None in have:
        return []
    return [_found("risk_line_off_level", table, f"{text!r}; Risk {level} means {level_numbers(level)}",
                   seat_id=_my_id(table))]


def allowance_vs_state(table: dict) -> list[dict]:
    """A bot with no new trade left today does not read as Trading (table 41, N and N2 of the test log)."""
    if table.get("status") != "running":
        return []
    seat_id = _my_id(table)
    row = next((r for r in table.get("standings") or [] if isinstance(r, dict) and r.get("seat_id") == seat_id), None)
    if row is None:
        return []
    used, cap = _number(row.get("trades_today")), _number(row.get("daily_allowance"))
    spent = row.get("allowance_used_up") is True or (used is not None and cap is not None and used >= cap)
    if not spent or row.get("bot_state") != "trading":
        return []
    return [_found("allowance_vs_state", table, f"{used:g}/{cap:g} today and the state reads "
                                                f"{row.get('bot_state_label')!r}", seat_id=seat_id)]


def pick_window(table: dict) -> list[dict]:
    """The pick closes when the table ends, and says so: "closes in 23H 59M" on a 1 hour table is false."""
    picks = table.get("picks")
    if not isinstance(picks, dict):
        return []
    left = _number(picks.get("closes_in_s"))
    if table.get("status") == "running":
        ends = _number(table.get("ends_in_s"))
        if picks.get("open") and left is not None and ends is not None and left > ends + 60:
            return [_found("pick_window", table, f"closes in {left:g} s, the table ends in {ends:g} s")]
    elif picks.get("open") is False and left and left > 0:
        return [_found("pick_window", table, f"closed, and closes_in_s still counts {left:g}")]
    return []


def pick_paid(table: dict) -> list[dict]:
    """A lone pick on a finished table comes back whole: won it is the whole pool, lost it is refunded."""
    picks = table.get("picks")
    mine = picks.get("my_pick") if isinstance(picks, dict) else None
    if table.get("status") != "done" or not isinstance(mine, dict) or picks.get("pickers") != 1:
        return []
    stake, paid = _number(mine.get("stake_usdc")), _number(mine.get("paid_usdc"))
    if stake is None or paid is None or abs(stake - paid) <= CENTS:
        return []
    return [_found("pick_paid", table, f"stake {stake:g}, paid {paid:g}, status {mine.get('status')!r}")]


def check_gaps(log: list[dict]) -> list[float]:
    """Minutes between the coach's rows, oldest first; a collapsed row ("same check x2 since") counts
    its own spread divided by its repeats."""
    rows = sorted((r for r in log or [] if isinstance(r, dict) and _when(r.get("at"))), key=lambda r: _when(r["at"]))
    gaps, last = [], None
    for row in rows:
        at, first = _when(row["at"]), _when(row.get("since")) or _when(row["at"])
        if last is not None:
            gaps.append((first - last).total_seconds() / 60)
        repeats = row.get("repeats")
        if isinstance(repeats, int) and repeats > 1 and first != at:
            gaps.extend([(at - first).total_seconds() / 60 / (repeats - 1)] * (repeats - 1))
        last = at
    return gaps


def check_cadence(table: dict) -> list[dict]:
    worst = max(check_gaps(table.get("my_tune_log") or []), default=None)
    if worst is None or worst <= CADENCE_MAX_MIN:
        return []
    return [_found("check_cadence", table, f"{worst:.0f} min between two coach rows; it says every 10 minutes",
                   seat_id=_my_id(table))]


def coach_rule_vs_tunes(table: dict) -> list[dict]:
    """A tune before five closed trades, while the coach says it tunes once the bot has five."""
    closed = _closed(table)
    for tune in _tunes(table):
        count = sum(1 for t in closed if _when(t["at"]) <= _when(tune["at"]))
        if count < FIVE:
            return [_found("coach_rule_vs_tunes", table, f"tuned at {tune['at']} with {count} closed trade(s): "
                                                         f"{tune.get('text')!r}", seat_id=_my_id(table))]
    return []


def et10_pending(table: dict, now: datetime) -> list[dict]:
    """A prize's ET10 still `pending` hours after the page wrote "PAID OUT" over it."""
    ends = _when(table.get("ends_at"))
    rows = [r for r in table.get("et10_paid") or [] if isinstance(r, dict) and r.get("status") == "pending"]
    if table.get("status") != "done" or not rows or ends is None or now - ends < timedelta(hours=ET10_PENDING_HOURS):
        return []
    return [_found("et10_pending", table, f"{len(rows)} ET10 prize(s) still pending "
                                          f"{(now - ends).total_seconds() / 3600:.0f} h after the end")]


def contradictions(table: dict, now: datetime | None = None, five_rule: bool = False) -> list[dict]:
    """Everything one table's own answer says against itself."""
    if not isinstance(table, dict):
        return []
    out = [*standings_vs_trades(table), *accounts(table), *tune_vs_feed(table), *tune_vs_settings(table),
           *tune_reason(table), *risk_line_off_level(table), *allowance_vs_state(table), *pick_window(table),
           *pick_paid(table), *check_cadence(table)]
    if five_rule:
        out += coach_rule_vs_tunes(table)
    if now is not None:
        out += et10_pending(table, now)
    return out


def stale_asks(my_seats: list[dict], my_agents: dict | None) -> list[dict]:
    """An ask `/my-seats` calls pending that the lobby's owner block no longer holds: it lapsed and the
    route an agent follows its seat by was never told. Seats 120-123, asked 2026-10-28."""
    if not isinstance(my_agents, dict) or not isinstance(my_agents.get("approve_all_ids"), list):
        return []
    open_ids = set(my_agents["approve_all_ids"])
    return [{"key": "lapsed_ask_reads_pending", "seat_id": s.get("seat_id"), "table_id": s.get("table_id"),
             "what": f"seat {s.get('seat_id')} reads pending, the owner block has no such ask"}
            for s in my_seats or [] if isinstance(s, dict) and s.get("seat_status") == "pending"
            and s.get("seat_id") not in open_ids]


def leaderboard_vs_tables(board: dict, tables: list[dict]) -> list[dict]:
    """The board's "paid to winners" against the sum of its finished tables. On an ET10 table
    `prize_usdc` holds ET10 (table 15: 100, its buy-in back, in the board's ET10). A prize recorded as
    `capped` "is not paid out" (their words, llms.txt), so it is not in what was paid."""
    done = [t for t in tables if isinstance(t, dict) and t.get("status") == "done"]
    usdc = et10 = capped = 0.0
    for table in done:
        for row in ((table.get("results") or {}).get("ranked")) or []:
            if isinstance(row, dict):
                prize = _number(row.get("prize_usdc")) or 0
                et10 += (_number(row.get("prize_et10")) or 0) + (prize if table.get("currency") == "ET10" else 0)
                usdc += 0 if table.get("currency") == "ET10" else prize
        capped += sum(_number(r.get("amount_et10")) or 0 for r in table.get("et10_paid") or []
                      if isinstance(r, dict) and r.get("status") == "capped")
    theirs = {"tables_done": board.get("tables_done"), "paid_usdc": board.get("paid_usdc"), "paid_et10": board.get("paid_et10")}
    ours = {"tables_done": len(done), "paid_usdc": round(usdc, 2), "paid_et10": round(et10 - capped, 2)}
    if all(_number(theirs[k]) is not None and abs(theirs[k] - ours[k]) <= CENTS for k in ours):
        return []
    return [{"key": "leaderboard_vs_tables", "table_id": None,
             "what": f"board says {theirs}, its tables add up to {ours} ({capped:g} ET10 capped, not paid)"}]


def write_refusal(table: dict | None, seat_id) -> str | None:
    """Why a write to this seat may not go. Our floor before any POST: a paper USDC table, a seat of ours."""
    if not isinstance(table, dict):
        return "the table could not be read"
    if table.get("mode") != "paper":
        return f"table {table.get('id')} is mode {table.get('mode')!r}, not paper"
    if table.get("currency") != "USDC":
        return f"table {table.get('id')} is {table.get('currency')!r}, only paper USDC tables are written to"
    if seat_id not in my_seat_ids(table):
        return f"seat {seat_id} is not ours at table {table.get('id')}"
    return None


def variant_write(variant: str) -> tuple[str, dict] | None:
    """The one write a variant makes once its table runs, as (route under the seat, closed body)."""
    return {"B": ("coach", {"on": False}), "C1": ("risk", {"level": 1}), "C10": ("risk", {"level": 10}),
            "D": ("bot-settings", {"stop_loss_pct": 2.0})}.get(variant)


def next_asks(rows: list[dict], bots: list[dict], tables: list[dict], seated: set, spent: set,
              running: int) -> list[dict]:
    """One ask per open table, least tried variant first, a bot once a tick, nothing already tried.

    `seated`: instances at a table now, who sit out every variant but E (the variant is that they do
    not). `spent`: instances out of today's allowance, who cannot trade and would only repeat table 41."""
    tried = {(r.get("variant"), r.get("species"), r.get("tier")) for r in rows if r.get("type") == "experiment"}
    counts = {v: sum(1 for r in rows if r.get("type") == "experiment" and r.get("variant") == v) for v in VARIANTS}
    used: set = set()
    asks: list[dict] = []
    room = MAX_RUNNING - running
    for table in tables:
        if len(asks) >= room:
            break
        for variant in sorted(VARIANTS, key=lambda v: (counts[v], VARIANTS.index(v))):
            if variant == "E" and any(a["variant"] == "E" for a in asks):
                continue
            pool = [b for b in bots if b.get("instance_id") not in used and b.get("instance_id") not in spent
                    and ((b.get("instance_id") in seated) == (variant == "E"))
                    and (variant, b.get("species"), table.get("tier")) not in tried]
            if pool:
                bot = pool[0]
                asks.append({"table_id": table.get("id"), "tier": table.get("tier"), "variant": variant,
                             "instance_id": bot.get("instance_id"), "name": bot.get("name"),
                             "species": bot.get("species")})
                used.add(bot.get("instance_id"))
                counts[variant] += 1
                break
    return asks


def for_the_casino(bots: list[dict]) -> list[dict]:
    """The bots this department may seat and change: its own. A "lab" clone belongs to a running room,
    whose settings are not ours to move."""
    return [b for b in bots if isinstance(b, dict) and b.get("species")
            and str(b.get("name") or "").startswith(("casino ", "tournament "))]


def next_species(available: list[dict], ours: list[dict]) -> dict | None:
    """The first bot on offer no clone of ours is named after."""
    names = [str(b.get("name") or "") for b in ours]
    for row in available:
        if not any(str(row.get("name")) in name for name in names):
            return row
    return None


def new_keys(found: list[dict], rows: list[dict]) -> list[dict]:
    """What was found that nobody has dealt with: a key filed once is evidence afterwards, not news."""
    handled = {r.get("key") for r in rows if r.get("type") == "handled"}
    return [f for f in found if f.get("key") not in handled]


def roi_by_variant(rows: list[dict]) -> dict:
    """The finished seats per variant: does the coach earn anything, against itself off."""
    out: dict = {}
    for row in rows:
        if row.get("type") == "final" and _number(row.get("roi_pct")) is not None:
            out.setdefault(row.get("variant"), []).append(float(row["roi_pct"]))
    return {v: {"n": len(xs), "mean_roi": round(sum(xs) / len(xs), 2)} for v, xs in out.items()}


def decide(new: list[dict], asks: int, unstarted: list, ended: list, ends: list, now: datetime) -> str:
    """The tick's last line: the one thing to do. What is new comes first, a tick that files nothing
    would bury it under the next round."""
    if new:
        return f"decide: file {new[0].get('key')}"
    if asks:
        return f"decide: approve {asks}"
    if unstarted:
        return "decide: start " + " ".join(str(t) for t in unstarted)
    if ended:
        return f"decide: look {ended[0]}"
    times = sorted(t for t in (_when(e) for e in ends) if t is not None)
    return f"decide: quiet until {times[0]:%H:%M} UTC" if times else "decide: quiet"
