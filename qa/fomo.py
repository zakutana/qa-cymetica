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



def _hours(label) -> float | None:
    try:
        return float(str(label or "").rstrip("h"))
    except ValueError:
        return None


def read_late(signal: dict | None, checkpoint: dict,
              tolerance: float = DUE_TOLERANCE_HOURS) -> bool:
    """Was this checkpoint read further from its own label than the writer
    would ever have allowed?

    `due_checkpoints` has refused to back-fill a stale hour since 2026-09-13.
    The 85 rows written before it did are still in the diary and cannot be
    taken out of it -- rule 4 -- and the biggest of them, +1262.3%, is a price
    read 2.61 hours after its signal and filed under `1h`. Both timestamps are
    on the rows, so the reader can drop what the writer now refuses.

    A row whose timestamps cannot be read is NOT late: nothing here can tell,
    and a gap is not a loss.
    """
    hours = _hours(checkpoint.get("horizon"))
    taken = _at(checkpoint.get("at"))
    fired = _at((signal or {}).get("at"))
    if hours is None or taken is None or fired is None:
        return False
    return abs((taken - fired).total_seconds() / 3600.0 - hours) > tolerance


def _signals(rows: list[dict]) -> dict[str, dict]:
    return {r["key"]: r for r in rows or []
            if r.get("type") == "signal" and r.get("key")}


def in_time(rows: list[dict]) -> list[dict]:
    """`rows` without the checkpoints filed under an hour they were not read
    in. Everything downstream reads this, never the raw diary."""
    signals = _signals(rows)
    return [r for r in rows or []
            if r.get("type") != "checkpoint"
            or not read_late(signals.get(r.get("key")), r)]


# What a pair has to hold before a return measured on it is a return anybody
# could have taken. Sixty of our own measured tokens, re-quoted live on
# 2026-09-14: the deciles of `liquidity_usd` run 0.00, 0.29, 0.64, 0.79, 4.17,
# 15.20 and then jump straight to 1953, 5197, 8981, 68933. Half dust, half
# pool, and nothing in between -- so the threshold sits in the empty band and
# the answer does not depend on where exactly in it. $100 keeps 21 of the 49
# quoted, $1000 keeps 20.
MIN_LIQUIDITY_USD = 1000.0
MIN_VOLUME_H24 = 1000.0


def tradeable(depth: dict | None, min_liquidity: float = MIN_LIQUIDITY_USD,
              min_volume: float = MIN_VOLUME_H24) -> bool | None:
    """Could this pair be bought and sold? True, False, or **None** for never
    quoted -- three states, because unknown is not a verdict.

    Both sides of the trade: a pool with depth and no volume cannot be got
    out of, and a pool drained after a day of real volume (ASTRO, live:
    `liquidity_usd 0.0` against `volume_h24 243951`) cannot be got out of
    either. A mark is what somebody would pay now.
    """
    if depth is None:
        return None
    if depth.get("listed") is False:
        return False  # their terminal does not know the token any more
    liquidity, volume = depth.get("liquidity_usd"), depth.get("volume_h24")
    if not isinstance(liquidity, (int, float)) or not isinstance(volume, (int, float)):
        return None
    return liquidity >= min_liquidity and volume >= min_volume


def _depth_by_token(rows: list[dict]) -> dict[str, dict]:
    """Token -> the newest row that says anything about its depth, over both
    the `depth` seeds and the checkpoints, which have carried the same fields
    hourly since 2026-09-14. Lowercased on both sides: a Solana address is
    case-sensitive base58 and `signal_key` lowercases it, so a join that is
    not blind to case matches nothing and reads as "never quoted".
    """
    newest: dict[str, dict] = {}
    for row in rows or []:
        kind = row.get("type")
        if kind == "depth":
            token = str(row.get("token_address") or "").lower()
        elif kind == "checkpoint":
            token = str(row.get("key") or "").rsplit(":", 1)[0].lower()
        else:
            continue
        if not token or ("liquidity_usd" not in row and "listed" not in row):
            continue
        if str(row.get("at") or "") >= str(newest.get(token, {}).get("at") or ""):
            newest[token] = row
    return newest


def sellable(rows: list[dict], min_liquidity: float = MIN_LIQUIDITY_USD,
             min_volume: float = MIN_VOLUME_H24) -> tuple[list[dict], dict]:
    """`rows` without every token nobody could trade, and the three counts.

    [operator 2026-09-14] *"proc to zobrazuje coiny co se neda obchodvat nebo
    prodavat? ty jsou uplne zbytecne"*. They are worse than useless: over a
    live sample they carry the entire good news, taking the median from
    -22.8% to +0.0% and the mean from +15% to +766%.

    Applied here, once, upstream of everything -- a hit rate over one
    population beside a P&L over another describes nothing.
    """
    depth = _depth_by_token(rows)
    verdicts = {token: tradeable(row, min_liquidity, min_volume)
                for token, row in depth.items()}

    def token_of(row: dict) -> str | None:
        if row.get("type") == "depth":
            return str(row.get("token_address") or "").lower() or None
        key = row.get("key")
        return str(key).rsplit(":", 1)[0].lower() if key else None

    kept = [row for row in rows or []
            if verdicts.get(token_of(row) or "", None) is not False]
    # Counted in SIGNALS, not tokens, because they are printed on one strip
    # beside "signals tracked" and a coin can go hot more than once. Three
    # counts in tokens under a total in signals is two units in one row, and
    # the reader has no way to see it.
    signals = [r for r in rows or [] if r.get("type") == "signal"]
    verdict_of = [verdicts.get(token_of(r) or "") for r in signals]
    counts = {
        "n_tradeable": sum(1 for v in verdict_of if v is True),
        "n_untradeable": sum(1 for v in verdict_of if v is False),
        "n_depth_unknown": sum(1 for v in verdict_of if v is None),
        "min_liquidity": min_liquidity, "min_volume": min_volume,
    }
    return kept, counts


def usable(rows: list[dict], min_liquidity: float = MIN_LIQUIDITY_USD,
           min_volume: float = MIN_VOLUME_H24) -> tuple[list[dict], dict]:
    """The one door every reader here comes through: checkpoints filed under
    an hour they were not read in are dropped, then tokens nobody could trade
    in.

    The late count is taken HERE, before the drop -- `_positions` used to take
    it and now receives rows this function has already cleaned, which would
    read as "none were late".
    """
    signals = _signals(rows)
    late = sum(1 for r in rows or []
               if r.get("type") == "checkpoint"
               and read_late(signals.get(r.get("key")), r))
    kept, counts = sellable(in_time(rows), min_liquidity, min_volume)
    # `tracked` is how many signals there ARE, counted before the drop. Taken
    # after it, the page's "signals tracked" would shrink every time the
    # filter bit -- a total that moves with a filter is not a total.
    return kept, {**counts, "late_readings": late,
                  "tracked": len(_signals(rows))}


def c_token(checkpoint: dict) -> str:
    """The token a checkpoint belongs to, off its key.

    `signal_key` is `<token>:<hour>`, so the token is everything before the
    last colon -- an address never contains one, and rsplit keeps this right
    if the hour format ever grows.
    """
    return str(checkpoint.get("key") or "").rsplit(":", 1)[0]


def stats(rows: list[dict], hit_threshold: float = DEFAULT_HIT_THRESHOLD,
         top: int = 5, min_liquidity: float = MIN_LIQUIDITY_USD,
         min_volume: float = MIN_VOLUME_H24) -> dict:
    """Per horizon: how many resolved, hit rate, mean/median return, the best
    and worst performers. `hit_threshold` is a parameter, not a constant
    baked into the read -- what counts as "it worked" is the operator's call,
    not a number this function assumes silently.
    """
    rows, _ = usable(rows, min_liquidity, min_volume)
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


def _positions(rows: list[dict]) -> tuple[dict, dict]:
    """Every signal that had a price when it fired, marked at its newest
    reading, plus what had to be set aside to get there.

    One position per signal, not per token: a coin that goes hot in two
    consecutive hours was two entries at two prices, and a basket that bought
    both holds both. (`stats()` and `curves()` collapse to one row per token
    for the opposite reason -- a reader takes THOSE for a list of coins.)
    """
    rows = list(rows or [])
    signals = _signals(rows)
    per: dict[str, list[dict]] = {}
    for row in in_time(rows):
        if row.get("type") == "checkpoint" and row.get("key") in signals:
            per.setdefault(row["key"], []).append(row)

    stale = fresh = 0
    held: dict[str, dict] = {}
    for key, checkpoints in per.items():
        signal = signals[key]
        entry = signal.get("price_usd")
        if not isinstance(entry, (int, float)) or entry <= 0:
            continue  # never bought: nothing to mark, and never a 0% return
        previous = entry
        for row in sorted(checkpoints,
                          key=lambda c: _hours(c.get("horizon")) or 0.0):
            price, ret = row.get("price_usd"), row.get("return_pct")
            if not isinstance(ret, (int, float)):
                continue
            # A repeat is a price nobody traded at since we last looked, not a
            # coin standing still -- 304 of these read exactly 0.00% and set
            # the console's median at 1h to 0.0%.
            if price == previous:
                stale += 1
            else:
                fresh += 1
            previous = price
            held[key] = {"key": key, "symbol": signal.get("symbol"),
                         "conviction": signal.get("conviction"),
                         "chain": signal.get("chain"), "entry_price": entry,
                         "price_usd": price, "return_pct": ret,
                         "hours": _hours(row.get("horizon")),
                         "horizon": row.get("horizon")}
    return held, {"stale_readings": stale, "fresh_readings": fresh,
                  "in_play": len(signals)}


def _spread(returns: list[float], top: int) -> dict:
    """Mean, median, and the mean once the best `top` are taken out.

    The third is the one that matters and the reason the other two never ship
    alone. An equal-weight mean over memecoins is a single row: the live diary
    reads +494.7%, and -1.5% without its best five.
    """
    if not returns:
        return {"pnl_pct": None, "median_pct": None,
                "pnl_without_top_pct": None, "n": 0}
    ordered = sorted(returns)
    rest = ordered[:-top] if top and len(ordered) > top else []
    return {
        "n": len(ordered),
        "pnl_pct": sum(ordered) / len(ordered),
        "median_pct": median(ordered),
        "pnl_without_top_pct": sum(rest) / len(rest) if rest else None,
    }


DEFAULT_CONVICTION_MIN = 70.0


def basket(rows: list[dict], top: int = 5,
           conviction_min: float = DEFAULT_CONVICTION_MIN,
           min_liquidity: float = MIN_LIQUIDITY_USD,
           min_volume: float = MIN_VOLUME_H24) -> dict:
    """What an equal stake in every signal, bought at the moment it fired,
    would be worth now.

    [operator 2026-09-14] asked for exactly this, big, on the console, and in
    the same breath to check whether the numbers hold -- *"vypadaji az moc
    slibne"*. They do look promising and they are not: the headline is a mean,
    a mean over memecoins is one row, and the biggest row in the live diary
    (+73848%) sits in a pool carrying two cents of liquidity. So everything
    that qualifies it is computed here rather than left to whoever draws it --
    the mean without the best few, the median, how many signals had no price
    at all, and how many readings were the same number twice.
    """
    rows, filtered = usable(rows, min_liquidity, min_volume)
    held, counts = _positions(rows)
    marks = list(held.values())
    out = {**counts, **filtered, **_spread([m["return_pct"] for m in marks], top),
           "top": top,
           "n_priced": len(marks),
           "n_unpriced": counts["in_play"] - len(marks),
           "winners": sum(1 for m in marks if m["return_pct"] > 0),
           "losers": sum(1 for m in marks if m["return_pct"] < 0),
           "best": max(marks, key=lambda m: m["return_pct"]) if marks else None,
           "worst": min(marks, key=lambda m: m["return_pct"]) if marks else None,
           "by_horizon": []}

    # The same basket, entered only where THEIR own conviction score was high.
    # [operator 2026-09-14] *"a zopbraz tam jeste P&L jen kdyubychom
    # vstupovali do Conviction 70 a vic"* -- which is the question the whole
    # tab is for: their number is either worth something or it is decoration,
    # and the two baskets side by side answer it. A signal carrying no
    # conviction at all is not a low one and is not counted either way.
    picked = [m for m in marks
              if isinstance(m.get("conviction"), (int, float))
              and m["conviction"] >= conviction_min]
    out["high_conviction"] = {
        "min": conviction_min, **_spread([m["return_pct"] for m in picked], top),
        "winners": sum(1 for m in picked if m["return_pct"] > 0),
        "losers": sum(1 for m in picked if m["return_pct"] < 0),
        "unscored": sum(1 for m in marks
                        if not isinstance(m.get("conviction"), (int, float))),
    }

    # The same basket at each hour of the day, so the page can show whether
    # holding is what costs -- which it is: the median goes from -0.7% at an
    # hour to -24.7% at twenty-three.
    at_hour: dict[str, list[float]] = {}
    for row in in_time(rows):
        if row.get("type") != "checkpoint":
            continue
        if isinstance(row.get("return_pct"), (int, float)):
            at_hour.setdefault(str(row.get("horizon")), []).append(
                row["return_pct"])
    out["by_horizon"] = [
        {"horizon": label, **_spread(at_hour[label], top)}
        for label in sorted(at_hour, key=lambda h: _hours(h) or 0.0)]
    return out


def curves(rows: list[dict], limit: int | None = 40,
           min_liquidity: float = MIN_LIQUIDITY_USD,
           min_volume: float = MIN_VOLUME_H24) -> list[dict]:
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
    rows, _ = usable(rows, min_liquidity, min_volume)
    newest: dict[str, dict] = {}
    for row in rows or []:
        if row.get("type") != "signal" or not row.get("key"):
            continue
        token = str(row["key"]).rsplit(":", 1)[0]
        if str(row["key"]) >= str(newest.get(token, {}).get("key", "")):
            newest[token] = row

    seen: dict[str, dict[int, float | None]] = {}
    # The price each hour, beside the return: a percentage cannot be checked
    # against anything, and "a memecoin" at 5.561e-06 and at 0.0452 are not
    # the same object. [operator 2026-09-14] asked to see what was bought.
    priced: dict[str, dict[int, float]] = {}
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
        if isinstance(row.get("price_usd"), (int, float)):
            priced.setdefault(token, {})[hour] = row["price_usd"]

    out = []
    for token, by_hour in seen.items():
        if not any(v is not None for v in by_hour.values()):
            continue
        signal = newest.get(token) or {}
        highest = max(h for h in by_hour)
        points = [(h, by_hour.get(h)) for h in range(1, highest + 1)]
        read = [v for _, v in points if v is not None]
        prices = priced.get(token) or {}
        out.append({
            "token": token,
            "symbol": signal.get("symbol") or "?",
            "conviction": signal.get("conviction"),
            "points": points,
            # The price the signal fired at, and the newest one actually READ
            # -- never the last slot in the series, since an hour nobody could
            # price is a gap. [operator 2026-09-14] asked for both as columns,
            # looked at them and had them taken out again ("sou zbytecne"), so
            # nothing draws these. They stay because a return is a ratio and
            # cannot be checked against anything on its own: this is what the
            # +73848% row turns out to be $0.00006 into a two-cent pool.
            "entry_price": signal.get("price_usd"),
            "last_price": prices[max(prices)] if prices else None,
            "last": read[-1] if read else None,
            "peak": max(read) if read else None,
            "trough": min(read) if read else None,
        })
    # Biggest mover first: the reader meets the story, not the alphabet.
    out.sort(key=lambda c: (c["peak"] if c["peak"] is not None else -1e9),
             reverse=True)
    return out if limit is None else out[:limit]


# --- the study: does `hot` predict a pump, against a control ---------------
#
# [operator 2026-09-19] asked the laboratory whether the radar can predict the
# memecoins that pump. A hit rate over the coins it called hot cannot answer
# that alone; their own feed's `calibration` block answers it with a number
# we can test -- `hot` reached 3x inside 72 h for 9.5% of 169, base rate 3.4%
# (read 2026-09-19). So the diary gains three row types, none of which any
# reader above looks at, so the memecoin tab is untouched:
#
#     control   a coin the same feed listed in the same round and did NOT
#               call hot, as many as it did call, keyed `control:<token>:<hour>`
#     study     a reading at a horizon, `group` hot or control: hot signals
#               from 30 h to 72 h (their hourly checkpoints stop at 24), and
#               controls at every horizon a hot signal is read at
#     calibration   their own claim, each time it changes
#
# Hourly sampling misses an intra-hour peak that their OHLCV labels catch, so
# our absolute rates run low against theirs. Both groups are sampled the same
# way, which is what makes the comparison between them fair.

STUDY_HORIZONS_HOURS = tuple(float(h) for h in range(30, 73, 6))
CONTROL_HORIZONS_HOURS = HORIZONS_HOURS + STUDY_HORIZONS_HOURS
CONTROL_PREFIX = "control:"


def control_key(token_address: str, at) -> str | None:
    key = signal_key(token_address, at)
    return f"{CONTROL_PREFIX}{key}" if key else None


def pick_control(listed: list[dict], how_many: int, tracked_keys,
                 at=None) -> list[dict]:
    """The coins a round listed and did not call hot, `how_many` of them.

    Chosen by the hash of the address, not by where they sit in the list:
    their order is theirs (by activity, by age -- whatever they sort by), and
    the first N of a sorted list is a sample of whatever the sort favours.
    A hash has no opinion, and the same round always picks the same coins.
    """
    import hashlib

    tracked = set(tracked_keys or ())
    pool = []
    for row in listed or []:
        if not isinstance(row, dict) or row.get("hot"):
            continue
        key = control_key(row.get("token_address"), at)
        if key is None or key in tracked:
            continue
        digest = hashlib.sha256(
            str(row["token_address"]).lower().encode("utf-8")).hexdigest()
        pool.append((digest, key, row))
    pool.sort(key=lambda item: item[0])
    out, seen = [], set()
    for _, key, row in pool:
        if key in seen:
            continue
        seen.add(key)
        out.append(row)
        if len(out) >= max(int(how_many), 0):
            break
    return out


def _wilson(hits: int, n: int, z: float = 1.96) -> tuple[float, float] | None:
    """95% interval on a rate. Two coins are not a measurement, and the
    interval is what says so."""
    if n <= 0:
        return None
    p = hits / n
    centre = (p + z * z / (2 * n)) / (1 + z * z / n)
    half = (z * ((p * (1 - p) + z * z / (4 * n)) / n) ** 0.5) / (1 + z * z / n)
    return max(0.0, centre - half), min(1.0, centre + half)


def compare(rows: list[dict], multiple: float = 3.0, within_hours: float = 72.0,
            now=None, min_liquidity: float = MIN_LIQUIDITY_USD,
            min_volume: float = MIN_VOLUME_H24) -> dict:
    """Hot against control: how many reached `multiple` x their entry inside
    `within_hours`, judged on the PEAK -- their label is "reached 3x inside
    72 h", so a coin that tripled at hour twenty and died by seventy-two did
    pump.

    Only windows that have fully passed: a hit can be seen early and a miss
    cannot, so counting open windows counts the early hits alone. Only coins
    somebody could have bought, judged on the depth read when the signal
    fired. A signal nothing was read for is unread, not a miss.
    """
    moment = now or datetime.now(timezone.utc)
    entries = {"hot": {}, "control": {}}
    for row in rows or []:
        kind, key = row.get("type"), row.get("key")
        if key and kind == "signal":
            entries["hot"][key] = row
        elif key and kind == "control":
            entries["control"][key] = row

    peaks: dict[str, float] = {}
    for row in in_time(rows):
        kind, key = row.get("type"), row.get("key")
        if kind == "checkpoint" or kind == "study":
            hours = _hours(row.get("horizon"))
            price = row.get("price_usd")
            if (hours is None or hours > within_hours
                    or not isinstance(price, (int, float))):
                continue
            if kind == "study" and row.get("group") not in ("hot", "control"):
                continue
            peaks[key] = max(peaks.get(key, price), price)

    out = {"multiple": multiple, "within_hours": within_hours}
    for group, signals in entries.items():
        n = hits = 0
        excluded = {"untradeable": 0, "window_open": 0, "unpriced": 0,
                    "unread": 0}
        for key, signal in signals.items():
            fired = _at(signal.get("at"))
            if fired is None or fired + timedelta(hours=within_hours) > moment:
                excluded["window_open"] += 1
                continue
            if tradeable(signal, min_liquidity, min_volume) is not True:
                excluded["untradeable"] += 1
                continue
            entry = signal.get("price_usd")
            if not isinstance(entry, (int, float)) or entry <= 0:
                excluded["unpriced"] += 1
                continue
            if key not in peaks:
                excluded["unread"] += 1
                continue
            n += 1
            hits += 1 if peaks[key] / entry >= multiple else 0
        out[group] = {"n": n, "hits": hits,
                      "rate": hits / n if n else None,
                      "ci": _wilson(hits, n), "excluded": excluded}
    hot, control = out["hot"]["rate"], out["control"]["rate"]
    out["lift"] = (hot / control) if hot is not None and control else None
    return out
