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
}


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
    best-ranked row stands for the basket."""
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
                            "at": rnd["at"], "rank": h["rank"], "hot": h["hot"],
                            "px": h["px"], "ret": h["ret"],
                            "published_at": head.get("published_at"),
                            "members": head.get(f"{_cls_key(h['cls'])}_members") or [],
                            "event_card_id": head.get("event_card_id")})
        prev, prev_fps = rnd, set(here)
    return out


def forward(rows, row_id, cls: str, t0, px0: float, hours: float,
            tolerance_minutes: float = TOLERANCE_MINUTES) -> float | None:
    """Percent return of the row's index from `px0` at `t0` to `t0 + hours`,
    read off the round nearest the horizon within the tolerance; None if no
    such round priced it."""
    t0 = _at(t0) if not isinstance(t0, datetime) else t0
    target = t0 + timedelta(hours=hours)
    best = None
    for rnd in _rounds(rows):
        off = abs(_at(rnd["at"]) - target)
        if off > timedelta(minutes=tolerance_minutes):
            continue
        px = _px_at(rnd, row_id, cls)
        if px and (best is None or off < best[0]):
            best = (off, px)
    if best is None or not px0:
        return None
    return round((best[1] / float(px0) - 1.0) * 100.0, 6)


def _summary(values: list[float], unobserved: int) -> dict:
    n = len(values)
    if not n:
        return {"n": 0, "unobserved": unobserved, "mean": None, "median": None,
                "up": 0, "up_ci": None}
    ordered = sorted(values)
    mid = n // 2
    median = ordered[mid] if n % 2 else (ordered[mid - 1] + ordered[mid]) / 2
    up = sum(1 for v in values if v > 0)
    return {"n": n, "unobserved": unobserved,
            "mean": round(sum(values) / n, 6), "median": round(median, 6),
            "up": up, "up_ci": _wilson(up, n)}


def follow(found: list[dict], rows, horizons=(6.0, 24.0)) -> dict:
    """Per class, per horizon: the index's return after entry."""
    out = {}
    for cls in CLASSES:
        mine = [e for e in found if e["cls"] == cls]
        per = []
        for h in horizons:
            values, missing = [], 0
            for e in mine:
                r = forward(rows, e["row"], cls, e["at"], e["px"], h)
                if r is None:
                    missing += 1
                else:
                    values.append(r)
            per.append({"hours": h, **_summary(values, missing)})
        out[cls] = per
    return out


def control(rows, found: list[dict], horizons=(6.0, 24.0), headlines=None) -> dict:
    """The same horizons for baskets of the same class that were on the wire
    at an entry's round and NOT in hot: what any basket did meanwhile."""
    rounds = {r["at"]: r for r in _rounds(rows)}
    heads = _headlines(headlines if headlines is not None else rows)
    out = {}
    for cls in CLASSES:
        picked: dict[tuple, tuple] = {}
        for e in (x for x in found if x["cls"] == cls):
            rnd = rounds.get(e["at"])
            if not rnd:
                continue
            in_hot = {_fp(heads.get(h["row"]), h["cls"]) for h in _hot_rows(rnd)}
            for w in rnd.get("wire") or []:
                fp = _fp(heads.get(w[0]), cls)
                px = _px_at({"wire": [w]}, w[0], cls)
                if fp and px and fp not in in_hot and (fp, e["at"]) not in picked:
                    picked[(fp, e["at"])] = (w[0], px)
        per = []
        for h in horizons:
            values, missing = [], 0
            for (fp, at), (row, px) in picked.items():
                r = forward(rows, row, cls, at, px, h)
                if r is None:
                    missing += 1
                else:
                    values.append(r)
            per.append({"hours": h, **_summary(values, missing)})
        out[cls] = per
    return out


def _qualifies(e: dict, rule: dict) -> bool:
    if e["cls"] != rule["hot_class"]:
        return False
    if not isinstance(e.get("ret"), (int, float)) or e["ret"] < rule["min_ret_24h"]:
        return False
    if len(e.get("members") or []) < rule["min_members"]:
        return False
    if not isinstance(e.get("rank"), int) or e["rank"] > rule["max_rank"]:
        return False
    published = _at(e.get("published_at"))
    if published is None:
        return False
    return _at(e["at"]) - published <= timedelta(minutes=rule["max_age_minutes"])


def _overlap(a, b) -> float:
    a, b = set(a or []), set(b or [])
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def nexus_rule(rows, headlines=None, rule: dict | None = None) -> dict:
    """NEX-0055, run over the diary. Entries are ours (an entry is at most one
    round, GAP_MINUTES, into Hot -- inside his 30 minutes); exits are read at
    the first ROUND past a level, at the price that round saw, never at the
    level itself: we see the path only every tick."""
    rule = {**RULE, **(rule or {})}
    rounds = _rounds(rows)
    found = [e for e in entries(rows, headlines) if _qualifies(e, rule)]
    trades, open_, skipped, held_rows = [], 0, 0, set()
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
        exit_, gross, closed_at = None, None, None
        for rnd in rounds:
            when = _at(rnd["at"])
            if when <= t0:
                continue
            if when > end + timedelta(minutes=TOLERANCE_MINUTES):
                break
            px = _px_at(rnd, e["row"], e["cls"])
            if not px:
                continue
            move = (px / float(e["px"]) - 1.0) * 100.0
            if move >= rule["take_profit"]:
                exit_, gross, closed_at = "take_profit", move, when
                break
            if move <= rule["stop"]:
                exit_, gross, closed_at = "stop", move, when
                break
            if when >= end - timedelta(minutes=TOLERANCE_MINUTES):
                exit_, gross, closed_at = "time", move, when
                break
        held_rows.add(e["row"])
        holding.append((end, e["members"]))
        if exit_ is None:
            open_ += 1
            continue
        gross = round(gross, 6)
        trades.append({"row": e["row"], "fp": e["fp"], "at": e["at"],
                       "closed_at": closed_at.isoformat(timespec="seconds"),
                       "exit": exit_, "gross": gross,
                       "net": round(gross - rule["cost_round_trip"], 6)})
    return {"entries": len(found), "open": open_, "skipped_overlap": skipped,
            "trades": trades, **rule_verdict(trades, rule)}


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
