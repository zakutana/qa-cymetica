"""The Hot headlines study: does a basket that has just entered Hot keep rising?

Pure functions over the diary `scripts/hot_watch.py` writes. No I/O.

What Hot is, measured 2026-09-21: `/api/v1/headlines?filter=hot` ranks
headlines by `hotidx.hot`, the trailing-24 h return AT READ TIME of a
price-weighted index of the headline's "related assets" -- `stock_members` or
`crypto_members`, whichever `hot_class` names. Hot belongs to the BASKET: two
headlines 36 h apart on one basket show one identical number. So an entry
here is a basket (its fingerprint) appearing in the hot top 100, not a
headline being published.

Prices come from their own index (`stock_px` / `crypto_px`), read on every
round from the hot tab and from the newest 500 wire rows, which reach back
about 56 h. That is the whole of the path; nothing here re-prices a member.
NEX-0054 advised replicating the member basket 1/N from our own spot feed,
and `preview_card_basket` resolved only 1-3 of 4-6 crypto members of the hot
baskets we tried, so the index is the one price we can follow for every
basket -- price-weighted, not 1/N, and said so wherever a number is printed.

A missing observation is never a zero. A forward return with no round near
its horizon is `unobserved`; an entry after a gap in the rounds is not an
entry, because we do not know when it came in.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from qa.fomo import _at, _wilson

GAP_MINUTES = 40          # the previous round must be this close to call an entry
ONCE_HOURS = 24           # one entry per basket per day
TOLERANCE_MINUTES = 30    # a horizon is read off a round this close to it

CLASSES = ("crypto", "stocks")

# NEX-0055 (2026-09-21 08:43), the rule as Nexus specified it.
RULE = {
    "hot_class": "crypto",
    "min_ret_24h": 6.0,
    "min_members": 3,
    "max_rank": 3,
    "max_age_minutes": 60,
    "max_minutes_in_hot": 30,
    "take_profit": 8.0,
    "stop": -4.0,
    "hold_hours": 24.0,
    "cost_round_trip": 0.20,
    "max_overlap": 0.5,
    "min_trades": 100,
    "min_t": 1.65,
    "confirm_rounds": 0,
}

# NEX-0057 (2026-09-21 10:36), his revision once the first 100 minutes showed
# baskets entering Hot near its bottom (ranks 6-100), so rank <= 3 never
# fired: drop the rank gate, require the basket still in Hot at the next
# round and enter there, and either take +4-5 % or hold ~12 h. His
# volatility-scaled stop is not here yet -- it needs the basket's own ATR.
VARIANTS = {
    "NEX-0055": dict(RULE),
    "NEX-0057a": {**RULE, "max_rank": None, "confirm_rounds": 1},
    "NEX-0057b": {**RULE, "max_rank": None, "confirm_rounds": 1,
                  "take_profit": 5.0},
    "NEX-0057c": {**RULE, "max_rank": None, "confirm_rounds": 1,
                  "hold_hours": 12.0},
    # His stop: about -1.0 to -1.5x the basket's hourly ATR, never tighter
    # than -4 %, the target twice the stop so the 2:1 holds.
    "NEX-0057d": {**RULE, "max_rank": None, "confirm_rounds": 1,
                  "vol_stop": True},
}

VOL_LOOKBACK_HOURS = 6.0
VOL_MULTIPLE = 1.25


def basket_fp(members, cls: str) -> str | None:
    """`cls:` + the sorted members; None for an empty basket."""
    names = sorted({str(m) for m in members or [] if m})
    return f"{cls}:{','.join(names)}" if names else None


def _cls_key(cls: str) -> str:
    return "crypto" if cls == "crypto" else "stock"


def _rounds(rows) -> list[dict]:
    out = [r for r in rows if r.get("type") == "round" and _at(r.get("at"))]
    return sorted(out, key=lambda r: _at(r["at"]))


def _headlines(rows) -> dict:
    return {r["id"]: r for r in rows
            if r.get("type") == "headline" and r.get("id") is not None}


def _fp(head: dict | None, cls: str) -> str | None:
    if not head:
        return None
    return head.get(f"{_cls_key(cls)}_fp")


def _hot_rows(rnd: dict) -> list[dict]:
    out = []
    for row in rnd.get("hot") or []:
        if isinstance(row, (list, tuple)) and len(row) >= 6:
            out.append({"row": row[0], "rank": row[1], "hot": row[2],
                        "cls": row[3], "px": row[4], "ret": row[5]})
    return out


def _px_at(rnd: dict, row_id, cls: str):
    """The row's index price for `cls` in one round, from hot or the wire."""
    for h in _hot_rows(rnd):
        if h["row"] == row_id and h["cls"] == cls and h["px"]:
            return float(h["px"])
    for w in rnd.get("wire") or []:
        if isinstance(w, (list, tuple)) and len(w) >= 3 and w[0] == row_id:
            px = w[2] if cls == "crypto" else w[1]
            return float(px) if isinstance(px, (int, float)) and px > 0 else None
    return None


def covered(prev: dict | None, cur: dict, gap_minutes: float = GAP_MINUTES) -> bool:
    if prev is None:
        return False
    return (_at(cur["at"]) - _at(prev["at"])) <= timedelta(minutes=gap_minutes)


def entries(rows, headlines=None) -> list[dict]:
    """Baskets that appeared in the hot top 100 at a round whose previous round
    (within GAP_MINUTES) did not have them. One per basket per ONCE_HOURS; the
    best-ranked row stands for the basket. `absent_at` is that previous round:
    the entry came in after it, so `at - absent_at` is the most the diary can
    prove about how long the basket has been in Hot."""
    rounds = _rounds(rows)
    heads = _headlines(headlines if headlines is not None else rows)
    last_entry: dict[str, datetime] = {}
    out = []
    prev_fps: set | None = None
    prev = None
    for rnd in rounds:
        if rnd.get("hot") is None:
            # The hot read failed: a hole in what we saw, not an empty tab.
            continue
        here: dict[str, dict] = {}
        for h in _hot_rows(rnd):
            fp = _fp(heads.get(h["row"]), h["cls"])
            if fp and (fp not in here or h["rank"] < here[fp]["rank"]):
                here[fp] = h
        if prev is not None and prev_fps is not None and covered(prev, rnd):
            when = _at(rnd["at"])
            for fp, h in sorted(here.items(), key=lambda kv: kv[1]["rank"]):
                if fp in prev_fps:
                    continue
                seen = last_entry.get(fp)
                if seen and when - seen < timedelta(hours=ONCE_HOURS):
                    continue
                last_entry[fp] = when
                head = heads.get(h["row"]) or {}
                out.append({"fp": fp, "row": h["row"], "cls": h["cls"],
                            "at": rnd["at"], "absent_at": prev["at"],
                            "rank": h["rank"], "hot": h["hot"],
                            "px": h["px"], "ret": h["ret"],
                            "published_at": head.get("published_at"),
                            "members": head.get(f"{_cls_key(h['cls'])}_members") or [],
                            "event_card_id": head.get("event_card_id")})
        prev, prev_fps = rnd, set(here)
    return out


class _Index:
    """The rounds sorted ONCE, with each round's prices by (class, row).

    R01, deep pass of 2026-09-21: forward() re-sorted the whole diary for
    every basket it priced, and control() prices hundreds per entry round, so
    a reading grew about R^2.3. Built once per reading, read by bisection.
    A hot row's price wins over the wire's, as `_px_at` has it.
    """

    def __init__(self, rows):
        import bisect

        self._bisect = bisect
        self.rounds = _rounds(rows)
        self.times = [_at(r["at"]) for r in self.rounds]
        self.prices: list[dict] = []
        for rnd in self.rounds:
            here: dict = {}
            for w in rnd.get("wire") or []:
                if isinstance(w, (list, tuple)) and len(w) >= 3:
                    for cls, px in (("stocks", w[1]), ("crypto", w[2])):
                        if isinstance(px, (int, float)) and px > 0:
                            here[(cls, w[0])] = float(px)
            for h in _hot_rows(rnd):
                if h["px"]:
                    here[(h["cls"], h["row"])] = float(h["px"])
            self.prices.append(here)

    def last(self):
        return self.times[-1] if self.times else None

    def after(self, t0: datetime) -> int:
        """The position of the first round strictly after `t0`."""
        return self._bisect.bisect_right(self.times, t0)

    def price(self, i: int, cls: str, row_id, siblings=()) -> float | None:
        """The basket's price at round `i`: the row's own, else any sibling's."""
        here = self.prices[i]
        px = here.get((cls, row_id))
        if not px:
            px = next((here[(cls, s)] for s in siblings
                       if here.get((cls, s))), None)
        return px

    def forward(self, row_id, cls: str, t0, px0: float, hours: float,
                tolerance_minutes: float = TOLERANCE_MINUTES,
                siblings=()) -> float | None:
        t0 = _at(t0) if not isinstance(t0, datetime) else t0
        target = t0 + timedelta(hours=hours)
        slack = timedelta(minutes=tolerance_minutes)
        lo = self._bisect.bisect_left(self.times, target - slack)
        hi = self._bisect.bisect_right(self.times, target + slack)
        best = None
        for i in range(lo, hi):
            px = self.price(i, cls, row_id, siblings)
            off = abs(self.times[i] - target)
            if px and (best is None or off < best[0]):
                best = (off, px)
        if best is None or not px0:
            return None
        return round((best[1] / float(px0) - 1.0) * 100.0, 6)


def forward(rows, row_id, cls: str, t0, px0: float, hours: float,
            tolerance_minutes: float = TOLERANCE_MINUTES,
            siblings=()) -> float | None:
    """Percent return of the row's index from `px0` at `t0` to `t0 + hours`,
    read off the round nearest the horizon within the tolerance; None if no
    such round priced it. `siblings` are other headlines on the same basket:
    the price is the basket's, so any of them will do once the row itself has
    left the wire. One call builds its own index; a reading builds one."""
    return _Index(rows).forward(row_id, cls, t0, px0, hours,
                                tolerance_minutes, siblings)


def _summary(values: list[float], unobserved: int, open_: int = 0) -> dict:
    n = len(values)
    if not n:
        return {"n": 0, "unobserved": unobserved, "open": open_, "mean": None,
                "median": None, "up": 0, "up_ci": None}
    ordered = sorted(values)
    mid = n // 2
    median = ordered[mid] if n % 2 else (ordered[mid - 1] + ordered[mid]) / 2
    up = sum(1 for v in values if v > 0)
    return {"n": n, "unobserved": unobserved, "open": open_,
            "mean": round(sum(values) / n, 6), "median": round(median, 6),
            "up": up, "up_ci": _wilson(up, n)}


def _horizon(rows, items, cls: str, hours: float, index: "_Index | None" = None,
             heads: dict | None = None) -> dict:
    """`items` = [(row, at, px)]. A horizon the rounds have not reached yet is
    open; one they passed without pricing the row is unobserved."""
    index = index or _Index(rows)
    last = index.last()
    heads = heads if heads is not None else _headlines(rows)
    by_fp: dict[str, list] = {}
    for hid, head in heads.items():
        fp = _fp(head, cls)
        if fp:
            by_fp.setdefault(fp, []).append(hid)
    values, missing, open_ = [], 0, 0
    for row, at, px in items:
        fp = _fp(heads.get(row), cls)
        siblings = [h for h in by_fp.get(fp, ()) if h != row] if fp else []
        r = index.forward(row, cls, at, px, hours, siblings=siblings)
        if r is not None:
            values.append(r)
        elif last is None or _at(at) + timedelta(
                hours=hours, minutes=TOLERANCE_MINUTES) > last:
            open_ += 1
        else:
            missing += 1
    return {"hours": hours, **_summary(values, missing, open_)}


def follow(found: list[dict], rows, horizons=(6.0, 24.0)) -> dict:
    """Per class, per horizon: the index's return after entry."""
    out = {}
    index, heads = _Index(rows), _headlines(rows)
    for cls in CLASSES:
        mine = [(e["row"], e["at"], e["px"]) for e in found if e["cls"] == cls]
        out[cls] = [_horizon(rows, mine, cls, h, index, heads) for h in horizons]
    return out


def control(rows, found: list[dict], horizons=(6.0, 24.0), headlines=None) -> dict:
    """The same horizons for baskets of the same class that were on the wire
    at an entry's round and had NOT been in hot in the day before it: what a
    basket nobody called did meanwhile. Every such basket, not a sample of
    equal size -- a larger control costs nothing here, since no leg is priced.
    One that left Hot hours ago is excluded: it is the tail of the thing
    measured, not its absence. So is a day in which a hot read failed: what
    was in Hot then is unknown, and an unknown is not "not in Hot" (rule 8),
    so an entry with one in the day before it brings no control at all."""
    index = _Index(rows)
    ordered = index.rounds
    rounds = {r["at"]: r for r in ordered}
    heads = _headlines(headlines if headlines is not None else rows)
    seen_hot: dict[str, list[datetime]] = {}
    blind: list[datetime] = []
    for rnd in ordered:
        if rnd.get("hot") is None:
            blind.append(_at(rnd["at"]))
            continue
        for h in _hot_rows(rnd):
            fp = _fp(heads.get(h["row"]), h["cls"])
            if fp:
                seen_hot.setdefault(fp, []).append(_at(rnd["at"]))

    def lately(times, when: datetime) -> bool:
        return any(when - timedelta(hours=ONCE_HOURS) <= t <= when for t in times)

    def lately_hot(fp: str, when: datetime) -> bool:
        return lately(seen_hot.get(fp, ()), when)

    out = {}
    for cls in CLASSES:
        picked: dict[tuple, tuple] = {}
        for e in (x for x in found if x["cls"] == cls):
            rnd = rounds.get(e["at"])
            if not rnd:
                continue
            when = _at(e["at"])
            # B06, deep pass of 2026-09-21: a failed hot read added nothing to
            # seen_hot, so a basket hot only while we were blind joined the
            # control. The conservative variant: a failed hot read in the look-
            # back leaves EVERY basket unproven, not only those on that round's
            # wire -- measured the same day, 2056 of 2600 hot rows (79 %) had
            # their basket on the same round's wire, so the narrower reading
            # would still count a fifth of the unknowns as not-hot.
            if lately(blind, when):
                continue
            for w in rnd.get("wire") or []:
                fp = _fp(heads.get(w[0]), cls)
                px = _px_at({"wire": [w]}, w[0], cls)
                if (fp and px and not lately_hot(fp, when)
                        and (fp, e["at"]) not in picked):
                    picked[(fp, e["at"])] = (w[0], px)
        items = [(row, at, px) for (_, at), (row, px) in picked.items()]
        out[cls] = [_horizon(rows, items, cls, h, index, heads) for h in horizons]
    return out


def _qualifies(e: dict, rule: dict) -> bool:
    if e["cls"] != rule["hot_class"]:
        return False
    if not isinstance(e.get("ret"), (int, float)) or e["ret"] < rule["min_ret_24h"]:
        return False
    if len(e.get("members") or []) < rule["min_members"]:
        return False
    if rule.get("max_rank") is not None and (
            not isinstance(e.get("rank"), int) or e["rank"] > rule["max_rank"]):
        return False
    # B05, deep pass of 2026-09-21: his second clock, time in Hot, was declared
    # and never read. The diary proves only an upper bound on it -- the entry
    # round minus the last covered round that saw the basket absent -- and
    # GAP_MINUTES lets that reach 40. Past his limit it is not his entry.
    limit = rule.get("max_minutes_in_hot")
    if limit is not None:
        absent = _at(e.get("absent_at"))
        if absent is None or _at(e["at"]) - absent > timedelta(minutes=limit):
            return False
    published = _at(e.get("published_at"))
    if published is None:
        return False
    return _at(e["at"]) - published <= timedelta(minutes=rule["max_age_minutes"])


def vol_stop(rows, row_id, cls: str, at, floor: float = -4.0) -> float:
    """-VOL_MULTIPLE x the basket's hourly ATR in percent, read off the rounds
    in the VOL_LOOKBACK_HOURS before `at`, never tighter than `floor`. A
    round-to-round move is scaled to an hour by sqrt(hour / step). Under three
    priced rounds there is no ATR, and the floor stands."""
    at = _at(at) if not isinstance(at, datetime) else at
    path = []
    for rnd in _rounds(rows):
        when = _at(rnd["at"])
        if at - timedelta(hours=VOL_LOOKBACK_HOURS) <= when <= at:
            px = _px_at(rnd, row_id, cls)
            if px:
                path.append((when, px))
    if len(path) < 3:
        return floor
    moves, steps = [], []
    for (t1, p1), (t2, p2) in zip(path, path[1:]):
        moves.append(abs(p2 / p1 - 1.0) * 100.0)
        steps.append((t2 - t1).total_seconds() / 3600.0)
    step = sum(steps) / len(steps)
    if step <= 0:
        return floor
    hourly = (sum(moves) / len(moves)) * math.sqrt(1.0 / step)
    return round(min(floor, -VOL_MULTIPLE * hourly), 6)


def _confirmed(e: dict, rounds: list[dict], heads: dict, n: int) -> dict | None:
    """The entry moved to the n-th following round, if the basket is still in
    Hot there and every round between is covered; None if it is not."""
    t = _at(e["at"])
    later = [r for r in rounds if _at(r["at"]) > t and r.get("hot") is not None]
    prev = next((r for r in rounds if r["at"] == e["at"]), None)
    for rnd in later[:n]:
        if prev is None or not covered(prev, rnd):
            return None
        fps = {_fp(heads.get(h["row"]), h["cls"]) for h in _hot_rows(rnd)}
        if e["fp"] not in fps:
            return None
        prev = rnd
    if len(later) < n:
        return None
    px = _px_at(prev, e["row"], e["cls"])
    return {**e, "at": prev["at"], "px": px} if px else None


def _overlap(a, b) -> float:
    a, b = set(a or []), set(b or [])
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def nexus_rule(rows, headlines=None, rule: dict | None = None) -> dict:
    """NEX-0055, run over the diary. Entries are ours, and qualify only if
    the last covered round that saw the basket absent is within his
    `max_minutes_in_hot` of the entry -- the one bound on time in Hot the
    diary proves. A `confirm_rounds` variant (NEX-0057, which keeps that
    clock and adds the persistence check) then trades one round later, so its
    trade can start up to one more round into Hot. Exits are read at the
    first ROUND past a level, at the price that round saw, never at the level
    itself: we see the path only every tick. The price is the basket's,
    through any headline on it, as `follow` reads it. A trade no round priced
    to an exit is open while the rounds have not passed its end, and
    unobserved once they have."""
    rule = {**RULE, **(rule or {})}
    index = _Index(rows)
    rounds = index.rounds
    last = index.last()
    slack = timedelta(minutes=TOLERANCE_MINUTES)
    heads = _headlines(headlines if headlines is not None else rows)
    by_fp: dict[str, list] = {}
    for hid, head in heads.items():
        for cls in CLASSES:
            fp = _fp(head, cls)
            if fp:
                by_fp.setdefault(fp, []).append(hid)
    found = [e for e in entries(rows, headlines) if _qualifies(e, rule)]
    if rule.get("confirm_rounds"):
        found = [c for c in (_confirmed(e, rounds, heads, rule["confirm_rounds"])
                             for e in found) if c]
    trades, open_, missing, skipped, held_rows = [], 0, 0, 0, set()
    holding: list[tuple[datetime, list]] = []
    for e in found:
        t0 = _at(e["at"])
        if e["row"] in held_rows:
            skipped += 1
            continue
        holding = [(end, m) for end, m in holding if end > t0]
        if any(_overlap(m, e["members"]) >= rule["max_overlap"] for _, m in holding):
            skipped += 1
            continue
        end = t0 + timedelta(hours=rule["hold_hours"])
        stop, target = rule["stop"], rule["take_profit"]
        if rule.get("vol_stop"):
            stop = vol_stop(rows, e["row"], e["cls"], t0, floor=rule["stop"])
            target = -2.0 * stop
        # B02, deep pass of 2026-09-21: exits read the entry's own row only, so
        # a trade whose row left the wire never exited and stayed open for
        # ever, where follow() read the same basket through a sibling.
        siblings = [h for h in by_fp.get(e["fp"], ()) if h != e["row"]]
        exit_, gross, closed_at = None, None, None
        for i in range(index.after(t0), len(rounds)):
            when = index.times[i]
            if when > end + slack:
                break
            px = index.price(i, e["cls"], e["row"], siblings)
            if not px:
                continue
            move = (px / float(e["px"]) - 1.0) * 100.0
            if move >= target:
                exit_, gross, closed_at = "take_profit", move, when
                break
            if move <= stop:
                exit_, gross, closed_at = "stop", move, when
                break
            if when >= end - slack:
                exit_, gross, closed_at = "time", move, when
                break
        held_rows.add(e["row"])
        holding.append((end, e["members"]))
        if exit_ is None:
            if last is None or end + slack > last:
                open_ += 1
            else:
                missing += 1
            continue
        gross = round(gross, 6)
        trades.append({"row": e["row"], "fp": e["fp"], "at": e["at"],
                       "closed_at": closed_at.isoformat(timespec="seconds"),
                       "exit": exit_, "gross": gross,
                       "net": round(gross - rule["cost_round_trip"], 6)})
    return {"entries": len(found), "open": open_, "unobserved": missing,
            "skipped_overlap": skipped, "trades": trades,
            **rule_verdict(trades, rule)}


def rule_verdict(trades: list[dict], rule: dict | None = None) -> dict:
    """His own falsification: N >= 100, then one-sided t on the net mean,
    expectancy and the sign of the mean."""
    rule = {**RULE, **(rule or {})}
    nets = [float(t["net"]) for t in trades]
    n = len(nets)
    if n < rule["min_trades"]:
        return {"n": n, "verdict": f"not yet: {n} of {rule['min_trades']} trades",
                "mean_net": round(sum(nets) / n, 6) if n else None, "t": None}
    mean = sum(nets) / n
    var = sum((x - mean) ** 2 for x in nets) / (n - 1)
    t = mean / math.sqrt(var / n) if var > 0 else (math.inf if mean > 0 else -math.inf)
    wins = [x for x in nets if x > 0]
    losses = [-x for x in nets if x <= 0]
    hit = len(wins) / n
    expectancy = (hit * (sum(wins) / len(wins) if wins else 0.0)
                  - (1 - hit) * (sum(losses) / len(losses) if losses else 0.0))
    rejected = t < rule["min_t"] or expectancy <= 0 or mean <= 0
    return {"n": n, "mean_net": round(mean, 6), "t": round(t, 3),
            "hit": round(hit, 4), "expectancy": round(expectancy, 6),
            "verdict": ("rejected" if rejected else "not rejected")
            + f": t {t:.2f} on {n} trades, mean {mean:+.2f} % net"}
