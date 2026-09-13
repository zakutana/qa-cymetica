"""Does FOMO Radar's `hot` signal actually predict a memecoin moving?

Cymetica shipped `/fomo-radar` overnight, 2026-09-12/13, alongside
`/social-pulse` and `/memecoin-terminal`. Their own disclaimer: "an on-chain
track record is a description of the past, not a prediction." This module
measures whether that is true of their `hot` field specifically -- the one
that promises the most (a real-time momentum signal) and the one the operator
asked to be tested first.

Two calls, two surfaces:

    fomo-radar's `hot` signal        -- what got flagged, and when
    memecoin-terminal's `search`     -- the price at signal time and at each
                                         checkpoint, so the return is OURS,
                                         computed from the signal timestamp,
                                         not their rolling window relative to
                                         whenever we happen to ask

`state/fomo_signals.jsonl` holds two row types:

    signal      one row per (token, the hour it went hot) -- a token can go
                hot again later; that is a NEW signal, not an update. Keyed
                on the hour so one still-hot token is not re-tracked every
                poll of `capture()`.
    checkpoint  the price read again at a horizon after the signal, with the
                return WE computed from it.

Everything here is pure and reads no file and makes no call; `scripts/
fomo_watch.py` is the two live rounds (`capture`, `resolve`) that call these.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from statistics import median

# Every hour of the first day. [operator 2026-09-13] asked to SEE the curve
# rather than read a hit rate, and three readings draw two line segments: a
# coin that ran 900% in hour three and gave it all back by hour six is
# indistinguishable from one that never moved. A day is where it stops --
# these are bonding-curve launches, and what happens after 24h is a different
# question from whether the signal called the move.
HORIZONS_HOURS = tuple(float(h) for h in range(1, 25))

# How late a checkpoint may still be taken. The loop ticks every twenty
# minutes and their memecoin-terminal caches for three, so an hour is either
# caught close to its mark or not at all -- filling it later would file a
# price under a time it was not read at. Deliberately not generous.
DUE_TOLERANCE_HOURS = 0.75
DEFAULT_HIT_THRESHOLD = 20.0


def _at(value) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None


def signal_key(token_address: str, at) -> str | None:
    """One tracked signal per token per HOUR it went hot -- a token that stays
    hot for the whole poll interval is one signal, not one every ten minutes;
    a token that goes hot again next week is a new one."""
    when = _at(at)
    if not token_address or when is None:
        return None
    return f"{str(token_address).lower()}:{when.strftime('%Y-%m-%dT%H')}"


def new_signals(hot_rows: list[dict], tracked_keys, at=None) -> list[dict]:
    """Which of a live poll's `hot` rows are not already tracked.

    `hot_rows` is FOMO Radar's own signal rows, whatever else they carry --
    this reads only `token_address` and `hot`, keyed by the hour. A row this
    poll already tracked (same token, same hour) is not returned again, so a
    token that stays hot across several ten-minute polls is one signal.
    """
    at = at or datetime.now(timezone.utc)
    tracked = set(tracked_keys or ())
    out = []
    seen_this_poll: set[str] = set()
    for row in hot_rows or []:
        if not isinstance(row, dict) or not row.get("hot"):
            continue
        key = signal_key(row.get("token_address"), at)
        if key is None or key in tracked or key in seen_this_poll:
            continue
        seen_this_poll.add(key)
        out.append(row)
    return out


def due_checkpoints(signals: list[dict], done: dict[str, set[str]], now=None,
                    horizons=HORIZONS_HOURS) -> list[tuple[dict, str]]:
    """Which (signal, horizon) pairs have crossed their horizon and have no
    checkpoint yet. `done` maps a signal's key to the horizon LABELS
    ("1h", "6h", "24h") already recorded for it.

    A gap is not a loss: a signal whose `at` cannot be read is skipped, never
    treated as overdue.

    **And an hour that has gone is gone.** `resolve()` reads the price NOW and
    files it under the horizon it is handed, so offering a horizon that came
    round hours ago would write today's price into a slot it was never
    measured in. A horizon is due only while it is still within
    `DUE_TOLERANCE_HOURS`; after that it stays an unfilled gap, which
    `curves()` draws as a break in the line. Found 2026-09-13 when the
    horizons went hourly and 85 seven-hour-old signals suddenly had hours
    2 to 5 "due".
    """
    moment = now or datetime.now(timezone.utc)
    out = []
    for signal in signals or []:
        key = signal.get("key")
        when = _at(signal.get("at"))
        if key is None or when is None:
            continue
        recorded = done.get(key, set())
        for hours in horizons:
            label = f"{hours:g}h"
            if label in recorded:
                continue
            ripe = when + timedelta(hours=hours)
            if ripe <= moment < ripe + timedelta(hours=DUE_TOLERANCE_HOURS):
                out.append((signal, label))
    return out


def return_since_signal(signal_price, checkpoint_price) -> float | None:
    """Ours, not theirs: memecoin-terminal's own %-change fields are relative
    to NOW, not to the signal's timestamp. A missing or zero signal price is
    not a 0% return -- it is unmeasurable."""
    if not isinstance(signal_price, (int, float)) or signal_price <= 0:
        return None
    if not isinstance(checkpoint_price, (int, float)):
        return None
    return (checkpoint_price / signal_price - 1.0) * 100.0



def c_token(checkpoint: dict) -> str:
    """The token a checkpoint belongs to, off its key.

    `signal_key` is `<token>:<hour>`, so the token is everything before the
    last colon -- an address never contains one, and rsplit keeps this right
    if the hour format ever grows.
    """
    return str(checkpoint.get("key") or "").rsplit(":", 1)[0]


def stats(rows: list[dict], hit_threshold: float = DEFAULT_HIT_THRESHOLD,
         top: int = 5) -> dict:
    """Per horizon: how many resolved, hit rate, mean/median return, the best
    and worst performers. `hit_threshold` is a parameter, not a constant
    baked into the read -- what counts as "it worked" is the operator's call,
    not a number this function assumes silently.
    """
    signals = {r["key"]: r for r in rows
              if r.get("type") == "signal" and r.get("key")}
    by_horizon: dict[str, list[dict]] = {}
    for row in rows:
        if row.get("type") != "checkpoint":
            continue
        ret = row.get("return_pct")
        if not isinstance(ret, (int, float)):
            continue
        signal = signals.get(row.get("key"))
        by_horizon.setdefault(row.get("horizon", "?"), []).append({
            "key": row.get("key"),
            "symbol": (signal or {}).get("symbol") or row.get("symbol"),
            "conviction": (signal or {}).get("conviction"),
            "return_pct": ret,
        })

    out = {"tracked": len(signals), "hit_threshold": hit_threshold, "horizons": {}}
    for label, checkpoints in sorted(by_horizon.items()):
        returns = [c["return_pct"] for c in checkpoints]
        hits = sum(1 for r in returns if r >= hit_threshold)
        ranked = sorted(checkpoints, key=lambda c: c["return_pct"], reverse=True)
        # One ROW per token in best-and-worst. A coin still hot an hour later
        # is a second tracked signal -- right for the rate, which is a rate
        # over signals fired, and wrong for a list a reader takes as tokens:
        # the console showed the same coin twice at +1262.3% on 2026-09-13 and
        # five rows carried three coins. Newest signal per token wins, its
        # return being the one measured from the freshest entry price.
        seen, unique = set(), []
        for row in sorted(checkpoints, key=lambda c: str(c.get("key")),
                          reverse=True):
            token = str(c_token(row))
            if token in seen:
                continue
            seen.add(token)
            unique.append(row)
        ranked_tokens = sorted(unique, key=lambda c: c["return_pct"],
                               reverse=True)
        out["horizons"][label] = {
            "resolved": len(returns),
            "hit_rate": hits / len(returns) if returns else None,
            "mean_pct": sum(returns) / len(returns) if returns else None,
            "median_pct": median(returns) if returns else None,
            "top": ranked_tokens[:top],
            "bottom": (list(reversed(ranked_tokens[-top:]))
                       if len(ranked_tokens) > top else []),
        }
    return out


def curves(rows: list[dict], limit: int = 40) -> list[dict]:
    """One hourly series per token, for the console to draw.

    `stats()` answers whether the signal worked, in aggregate. A curve is a
    different question -- what the coin actually DID -- and needs the points
    rather than the summary. [operator 2026-09-13] asked to see the shape.

    Gaps stay gaps. An hour never sampled and an hour whose price could not be
    read are both `None`, never 0: half of these tokens are too new for any
    DEX pool, and a zero there would draw a coin sitting still when the truth
    is that nobody knows. The page can break the line instead.

    Newest signal wins per token, the same rule `stats()` uses for its tables,
    so a coin hot in two consecutive hours is one curve and not two.
    """
    newest: dict[str, dict] = {}
    for row in rows or []:
        if row.get("type") != "signal" or not row.get("key"):
            continue
        token = str(row["key"]).rsplit(":", 1)[0]
        if str(row["key"]) >= str(newest.get(token, {}).get("key", "")):
            newest[token] = row

    seen: dict[str, dict[int, float | None]] = {}
    for row in rows or []:
        if row.get("type") != "checkpoint" or not row.get("key"):
            continue
        token = str(row["key"]).rsplit(":", 1)[0]
        if str(row["key"]) != str(newest.get(token, {}).get("key")):
            continue
        label = str(row.get("horizon") or "")
        try:
            hour = int(float(label.rstrip("h")))
        except ValueError:
            continue
        seen.setdefault(token, {})[hour] = row.get("return_pct")

    out = []
    for token, by_hour in seen.items():
        if not any(v is not None for v in by_hour.values()):
            continue
        signal = newest.get(token) or {}
        highest = max(h for h in by_hour)
        points = [(h, by_hour.get(h)) for h in range(1, highest + 1)]
        read = [v for _, v in points if v is not None]
        out.append({
            "token": token,
            "symbol": signal.get("symbol") or "?",
            "conviction": signal.get("conviction"),
            "points": points,
            "last": read[-1] if read else None,
            "peak": max(read) if read else None,
            "trough": min(read) if read else None,
        })
    # Biggest mover first: the reader meets the story, not the alphabet.
    out.sort(key=lambda c: (c["peak"] if c["peak"] is not None else -1e9),
             reverse=True)
    return out[:limit]
