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
#
# And +15 and +30 minutes before the first hour (2026-09-22). A stop can only
# fire at a point we read, so with the first point at an hour every stop in
# `stop_study` was an hour late, and the median first verified price sat 67
# minutes after the flag. These two narrow both.
HORIZONS_HOURS = (0.25, 0.5) + tuple(float(h) for h in range(1, 25))

# How late a checkpoint may still be taken. The loop ticks every twenty
# minutes and their memecoin-terminal caches for three, so an hour is either
# caught close to its mark or not at all -- filling it later would file a
# price under a time it was not read at. Deliberately not generous.
#
# This is the CAP. Each horizon's own window is half of it (`due_tolerance`):
# a +15 min checkpoint read forty minutes late is a +55 min reading, and the
# 0.75 h an hourly mark can afford would have filed it under +15.
DUE_TOLERANCE_HOURS = 0.75
DEFAULT_HIT_THRESHOLD = 20.0


def due_tolerance(hours: float) -> float:
    """How late a checkpoint at `hours` may be taken: half the horizon, never
    more than `DUE_TOLERANCE_HOURS`. The writer offers a horizon only inside
    it and the reader drops what falls outside it -- one rule, both sides."""
    return min(float(hours) / 2.0, DUE_TOLERANCE_HOURS)


def closes_at(signal: dict, label: str) -> datetime | None:
    """When the window of `signal`'s checkpoint `label` ("0.25h", "3h") shuts:
    the horizon plus its `due_tolerance`. None when either cannot be read."""
    when = _at(signal.get("at"))
    try:
        hours = float(str(label).rstrip("h"))
    except ValueError:
        return None
    if when is None:
        return None
    return when + timedelta(hours=hours + due_tolerance(hours))


def by_closing(pairs: list[tuple[dict, str]]) -> list[tuple[dict, str]]:
    """Due (signal, label) pairs, the window that shuts first first -- the
    order a round spends a capped number of quotes in (fomo_watch.quote_cap).
    Unreadable ones last; otherwise the order they came in."""
    last = datetime.max.replace(tzinfo=timezone.utc)
    return sorted(pairs, key=lambda pair: closes_at(pair[0], pair[1]) or last)


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
    `due_tolerance(horizon)`; after that it stays an unfilled gap, which
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
            if ripe <= moment < ripe + timedelta(hours=due_tolerance(hours)):
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
              tolerance: float | None = None) -> bool:
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
    if tolerance is None:
        tolerance = due_tolerance(hours)
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


def _depth_at_signals(rows: list[dict]) -> dict[str, dict]:
    """Signal key -> the depth a buyer had when it fired: the signal's own
    quote, or else the newest reading of the token (a `depth` seed, an
    earlier signal's checkpoint) taken no later than the signal. Joined blind
    to case, as `_depth_by_token` is. Never a reading from after it."""
    readings: dict[str, list[tuple[datetime, dict]]] = {}
    for row in rows or []:
        kind = row.get("type")
        if kind == "depth":
            token = str(row.get("token_address") or "").lower()
        elif kind == "checkpoint":
            token = str(row.get("key") or "").rsplit(":", 1)[0].lower()
        else:
            continue
        when = _at(row.get("at"))
        if not token or when is None or (
                "liquidity_usd" not in row and "listed" not in row):
            continue
        readings.setdefault(token, []).append((when, row))
    out: dict[str, dict] = {}
    for key, signal in _signals(rows).items():
        if "liquidity_usd" in signal or "listed" in signal:
            out[key] = signal
            continue
        fired = _at(signal.get("at"))
        token = str(key).rsplit(":", 1)[0].lower()
        before = [(when, row) for when, row in readings.get(token) or ()
                  if fired is not None and when <= fired]
        if before:
            out[key] = max(before, key=lambda item: item[0])[1]
    return out


def sellable(rows: list[dict], min_liquidity: float = MIN_LIQUIDITY_USD,
             min_volume: float = MIN_VOLUME_H24) -> tuple[list[dict], dict]:
    """`rows` without every signal nobody could have bought, and the three
    counts.

    [operator 2026-09-14] *"proc to zobrazuje coiny co se neda obchodvat nebo
    prodavat? ty jsou uplne zbytecne"*. They are worse than useless: over a
    live sample they carry the entire good news, taking the median from
    -22.8% to +0.0% and the mean from +15% to +766%.

    Applied here, once, upstream of everything -- a hit rate over one
    population beside a P&L over another describes nothing.

    Judged on the depth WHEN THE SIGNAL FIRED (V3, 2026-09-23). The newest
    reading was a look into the future: a coin that rugged at hour six was
    taken out of its own history, and its loss with it. What the pool held at
    the exit is the sale's business -- `capped_return` -- and the two land
    together: the depth at the signal alone let the rugs back in at the dust
    prints they rugged to, and read the stop study at +85 917 %.
    """
    depth = _depth_at_signals(rows)
    verdicts = {key: tradeable(row, min_liquidity, min_volume)
                for key, row in depth.items()}

    # `depth` seeds and anything not a signal's own row are no trade, and
    # stay; a checkpoint goes with its signal.
    kept = [row for row in rows or []
            if row.get("type") == "depth"
            or verdicts.get(row.get("key")) is not False]
    # Counted in SIGNALS, not tokens, because they are printed on one strip
    # beside "signals tracked" and a coin can go hot more than once. Three
    # counts in tokens under a total in signals is two units in one row, and
    # the reader has no way to see it.
    signals = [r for r in rows or [] if r.get("type") == "signal"]
    verdict_of = [verdicts.get(r.get("key")) for r in signals]
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


# The stake every descriptive reader here sells: the plan's headline clip
# (V3, 2026-09-23) and `ten_dollars`'s. The cap below is in dollars, so a
# return needs a size before a pool can cap it.
SALE_CLIP_USD = 10.0


def capped_return(ret, reading: dict, clip_usd: float = SALE_CLIP_USD):
    """`ret` as far as the pool at `reading` could pay it: a sale of the
    clip fetches at most half its liquidity -- the quote side -- as in
    `ten_dollars`. A reading with no liquidity on it (the diary before
    2026-09-14) cannot say, and the return stands."""
    if not isinstance(ret, (int, float)):
        return ret
    liquidity = (reading or {}).get("liquidity_usd")
    if not isinstance(liquidity, (int, float)) or isinstance(liquidity, bool):
        return ret
    return min(ret, (liquidity / 2.0 / clip_usd - 1.0) * 100.0)


def _after_switch(rows: list[dict]) -> set[int]:
    """The `id()` of every checkpoint read at or after the point its signal's
    pair changed (`switch_at`): their prices are another pair's, not this
    coin's, and pay no gain (`_no_pair_gain`). The readings before the switch
    are the coin's own and stand."""
    signals = _signals(rows)
    per: dict[str, list[dict]] = {}
    for row in rows or []:
        if row.get("type") == "checkpoint" and row.get("key") in signals:
            per.setdefault(row["key"], []).append(row)
    out: set[int] = set()
    for key, checkpoints in per.items():
        ordered = [signals[key]] + sorted(
            checkpoints, key=lambda c: _hours(c.get("horizon")) or 0.0)
        cut = switch_at(ordered)
        if cut is not None:
            out.update(id(r) for r in ordered[cut:])
    return out


def _no_pair_gain(ret, row: dict, after: set[int]):
    """`ret`, unless `row` was read on another pair than the signal's: then
    at most zero, as `ten_dollars` pays a switched pair (B03, deep pass of
    2026-09-28, 3/3 -- `stats` and `basket` printed PUMP at +31 273 437 %)."""
    if id(row) in after and isinstance(ret, (int, float)):
        return min(ret, 0.0)
    return ret


def c_token(checkpoint: dict) -> str:
    """The token a checkpoint belongs to, off its key.

    `signal_key` is `<token>:<hour>`, so the token is everything before the
    last colon -- an address never contains one, and rsplit keeps this right
    if the hour format ever grows.
    """
    return str(checkpoint.get("key") or "").rsplit(":", 1)[0]


def stats(rows: list[dict], hit_threshold: float = DEFAULT_HIT_THRESHOLD,
         top: int = 5, min_liquidity: float = MIN_LIQUIDITY_USD,
         min_volume: float = MIN_VOLUME_H24,
         clip_usd: float = SALE_CLIP_USD) -> dict:
    """Per horizon: how many resolved, hit rate, mean/median return, the best
    and worst performers. `hit_threshold` is a parameter, not a constant
    baked into the read -- what counts as "it worked" is the operator's call,
    not a number this function assumes silently. Each return is what
    `clip_usd` could have been sold for at that reading (`capped_return`).
    """
    rows, _ = usable(rows, min_liquidity, min_volume)
    signals = {r["key"]: r for r in rows
              if r.get("type") == "signal" and r.get("key")}
    after = _after_switch(rows)
    by_horizon: dict[str, list[dict]] = {}
    for row in rows:
        if row.get("type") != "checkpoint":
            continue
        ret = _no_pair_gain(capped_return(row.get("return_pct"), row, clip_usd),
                            row, after)
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
            # The worst are taken from what the best did not already claim.
            # Two slices of one ranking overlap whenever the ranking is
            # shorter than both together: at seven tokens, three of the five
            # "worst" were also among the five "best", live on 7h.
            "bottom": list(reversed(ranked_tokens[top:][-top:])),
        }
    return out


def _positions(rows: list[dict], clip_usd: float = SALE_CLIP_USD
               ) -> tuple[dict, dict]:
    """Every signal that had a price when it fired, marked at its newest
    reading -- for what the pool then could pay (`capped_return`) -- plus
    what had to be set aside to get there.

    One position per signal, not per token: a coin that goes hot in two
    consecutive hours was two entries at two prices, and a basket that bought
    both holds both. (`stats()` and `curves()` collapse to one row per token
    for the opposite reason -- a reader takes THOSE for a list of coins.)
    """
    rows = list(rows or [])
    signals = _signals(rows)
    after = _after_switch(rows)
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
                         "price_usd": price,
                         "return_pct": _no_pair_gain(
                             capped_return(ret, row, clip_usd), row, after),
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
           min_volume: float = MIN_VOLUME_H24,
           clip_usd: float = SALE_CLIP_USD) -> dict:
    """What an equal stake (`clip_usd`) in every signal, bought at the moment
    it fired, would sell for now.

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
    held, counts = _positions(rows, clip_usd)
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
    after = _after_switch(rows)
    for row in in_time(rows):
        if row.get("type") != "checkpoint":
            continue
        if isinstance(row.get("return_pct"), (int, float)):
            at_hour.setdefault(str(row.get("horizon")), []).append(
                _no_pair_gain(capped_return(row["return_pct"], row, clip_usd),
                              row, after))
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

    # A reading on another pair than the signal's pays no gain, as in `stats`
    # and `basket` (B03, deep pass of 2026-09-28): the line drew PUMP at
    # +504 772 % beside a table that paid it nothing.
    after = _after_switch(rows)
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
            hours = float(label.rstrip("h"))
        except ValueError:
            continue
        # The +15/+30 min points are for `stop_study`. This is the hourly
        # picture, drawn 24 hours wide; int(0.25) is hour 0, a slot the page
        # never draws and two readings would overwrite.
        if hours < 1:
            continue
        hour = int(hours)
        seen.setdefault(token, {})[hour] = _no_pair_gain(
            row.get("return_pct"), row, after)
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
                 at=None, hot_keys=()) -> list[dict]:
    """The coins a round listed and did not call hot, `how_many` of them.

    Chosen by the hash of the address, not by where they sit in the list:
    their order is theirs (by activity, by age -- whatever they sort by), and
    the first N of a sorted list is a sample of whatever the sort favours.
    A hash has no opinion, and the same round always picks the same coins.
    """
    import hashlib

    tracked = set(tracked_keys or ())
    # A coin the radar called hot EARLIER this hour is a signal already, and
    # drawing it as a control put the same coin at the same hour in both arms
    # (R08, deep pass of 2026-09-19). `hot_keys` are the signal keys tracked.
    hot = set(hot_keys or ())
    pool = []
    for row in listed or []:
        if not isinstance(row, dict) or row.get("hot"):
            continue
        key = control_key(row.get("token_address"), at)
        if key is None or key in tracked:
            continue
        if signal_key(row.get("token_address"), at) in hot:
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
            min_volume: float = MIN_VOLUME_H24,
            require_depth: bool = True) -> dict:
    """Hot against control: how many reached `multiple` x their entry inside
    `within_hours`, judged on the PEAK -- their label is "reached 3x inside
    72 h", so a coin that tripled at hour twenty and died by seventy-two did
    pump.

    Only windows that have fully passed: a hit can be seen early and a miss
    cannot, so counting open windows counts the early hits alone. Only coins
    somebody could have bought, judged on the depth read when the signal
    fired. A signal nothing was read for is unread, not a miss.

    `require_depth=False` drops that last condition: their calibration block
    is about every hot signal of the feed, not the ones deep enough to buy
    (A09, deep pass of 2026-09-22).
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
    paths: dict[str, list[tuple[float, dict]]] = {}
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
            paths.setdefault(key, []).append((hours, row))

    # C5 of the 2026-09-23 review: one period for both groups -- from when
    # both exist -- so hot signals of a week the control group never saw are
    # not set beside it.
    firsts = [min((t for t in (_at(s.get("at")) for s in signals.values())
                   if t is not None), default=None)
              for signals in entries.values()]
    period_from = (max(firsts) if all(t is not None for t in firsts)
                   else None)

    def token_of(key: str) -> str:
        return str(key).removeprefix(CONTROL_PREFIX).rsplit(":", 1)[0].lower()

    out = {"multiple": multiple, "within_hours": within_hours,
           "period_from": period_from.isoformat() if period_from else None}
    hot_keys = set(entries.get("hot") or {})
    for group, signals in entries.items():
        excluded = {"untradeable": 0, "depth_unknown": 0, "window_open": 0,
                    "unpriced": 0, "unread": 0, "before_period": 0,
                    "repeat_call": 0, "also_hot": 0}
        measured: dict[str, tuple] = {}
        for key, signal in signals.items():
            fired = _at(signal.get("at"))
            # Closed once its LAST reading could have been taken: the due
            # tolerance, as stop_study and ten_dollars wait for it (RM07,
            # deep pass of 2026-09-24) -- judged sooner, a coin whose multiple
            # came at the last point read as a miss.
            if fired is None or fired + timedelta(
                    hours=within_hours + due_tolerance(within_hours)) > moment:
                excluded["window_open"] += 1
                continue
            # A control drawn at :05 that went hot at :25 is the same coin at
            # the same hour in both arms -- the case R08 guarded only the
            # other way round (RM06, deep pass of 2026-09-24).
            if group == "control" and \
                    str(key).removeprefix(CONTROL_PREFIX) in hot_keys:
                excluded["also_hot"] += 1
                continue
            if period_from is not None and fired < period_from:
                excluded["before_period"] += 1
                continue
            # Three states, as tradeable() says: never quoted for depth is
            # unknown, not untradeable (R07, deep pass of 2026-09-19).
            can = tradeable(signal, min_liquidity, min_volume)
            if require_depth and can is not True:
                excluded["untradeable" if can is False
                         else "depth_unknown"] += 1
                continue
            entry = signal.get("price_usd")
            if not isinstance(entry, (int, float)) or entry <= 0:
                excluded["unpriced"] += 1
                continue
            if key not in peaks:
                excluded["unread"] += 1
                continue
            ordered = [signal] + [r for _, r in sorted(
                paths.get(key) or [], key=lambda item: item[0])]
            # A switched pair is a rug (all 60 on record, 2026-09-23), not a
            # coin to leave out: its peak is read on the pair it was bought
            # on, up to the switch -- the other pair's prices were never this
            # coin's, as `ten_dollars` pays them no gain.
            peak = peaks[key]
            cut = switch_at(ordered)
            if cut is not None:
                peak = max([entry] + [r["price_usd"] for r in ordered[1:cut]])
            # One coin, one call: the first measured call of each coin. A coin
            # called hot five times is one coin, not five hits or misses.
            token = token_of(key)
            hit = peak / entry >= multiple
            if token in measured:
                excluded["repeat_call"] += 1
                if fired < measured[token][0]:
                    measured[token] = (fired, hit, cut is not None)
                continue
            measured[token] = (fired, hit, cut is not None)
        n = len(measured)
        hits = sum(1 for _, hit, _ in measured.values() if hit)
        switched = sum(1 for _, _, moved in measured.values() if moved)
        out[group] = {"n": n, "hits": hits, "unit": "coin",
                      "rate": hits / n if n else None,
                      "ci": _wilson(hits, n), "excluded": excluded,
                      "switched": switched}
    hot, control = out["hot"]["rate"], out["control"]["rate"]
    out["lift"] = (hot / control) if hot is not None and control else None
    return out


# --- an entry read after the signal ------------------------------------------
#
# 748 of 2571 signals carried no price when they fired (2026-09-22): the
# terminal did not know the coin yet. `fomo_watch.resolve()` quotes each of
# them once more on the next round and writes an `entry` row with the moment
# IT was read. No reader here takes that price for the signal's: the horizons
# are counted from the signal, so a return from a later entry would credit it
# with minutes it never had. It is counted (`entries`) and nothing else, until
# a reader measures its own horizons from the entry's `at`.

# Only inside the first hour. Past it the coin has been read at +15 and +30
# min and at the hour by the checkpoints, and a retry is no longer an entry --
# and the backlog of old unpriced signals is not re-quoted on the first round.
ENTRY_RETRY_HOURS = 1.0


def entry_retries(signals: list[dict], retried_keys, now=None) -> list[dict]:
    """The unpriced signals still young enough to be quoted again, and not
    already quoted again."""
    moment = now or datetime.now(timezone.utc)
    retried = set(retried_keys or ())
    out = []
    for signal in signals or []:
        price, key = signal.get("price_usd"), signal.get("key")
        fired = _at(signal.get("at"))
        if not key or key in retried or fired is None:
            continue
        if isinstance(price, (int, float)) and price > 0:
            continue
        if fired <= moment < fired + timedelta(hours=ENTRY_RETRY_HOURS):
            out.append(signal)
    return out


def entries(rows: list[dict]) -> dict:
    """How many signals fired with no price, how many were quoted again, how
    many of those the retry priced, and how long after the signal."""
    signals = _signals(rows)
    unpriced = {k for k, s in signals.items()
                if not (isinstance(s.get("price_usd"), (int, float))
                        and s["price_usd"] > 0)}
    first: dict[str, dict] = {}
    for row in rows or []:
        if row.get("type") == "entry" and row.get("key") in unpriced:
            first.setdefault(row["key"], row)
    priced = {k: r for k, r in first.items()
              if isinstance(r.get("price_usd"), (int, float))
              and r["price_usd"] > 0}
    delays = []
    for key, row in priced.items():
        fired, read = _at(signals[key].get("at")), _at(row.get("at"))
        if fired is not None and read is not None:
            delays.append((read - fired).total_seconds() / 60.0)
    return {"signals": len(signals), "unpriced_at_signal": len(unpriced),
            "retried": len(first), "priced_on_retry": len(priced),
            "median_delay_min": median(delays) if delays else None}


# --- the stop study -----------------------------------------------------------
#
# NEXT.md, 2026-09-21: with no stop the gross expectation per hot signal was
# -0.72 %, with a -10 % stop +8.3 % -- and that simulation lived in a session.
# This is it in code, over the same diary, with what makes it an upper bound
# said beside every number it returns.

# Our clip: the lab's stake per room on 2026-09-21 (0.48 % of the book, 1 189
# USDC), the figure NEXT.md held against the radar's depth.
DEFAULT_CLIP_USD = 1189.0
# What `max_buy_5pct_usd` means: the buy that moves the price 5 %.
RADAR_IMPACT_PCT = 5.0
# Charged to a signal the radar published no depth for. A clip that fits
# inside `max_buy_5pct_usd` pays at most 5 % a side, so 10 % is the round trip
# NEXT.md reasoned with -- the ceiling for a clip that fits, a floor for one
# that does not.
DEFAULT_ROUND_TRIP_COST_PCT = 10.0

UNMEASURED_FILLS = (
    "fills between checkpoints are unmeasured: a stop or a target is taken "
    "at the first reading past it, not at its level, and the entry is the "
    "price quoted when the radar flagged -- so every positive figure is an "
    "upper bound")


def round_trip_cost(signal: dict, clip_usd: float = DEFAULT_CLIP_USD
                    ) -> tuple[float, bool]:
    """Percent lost buying and selling `clip_usd`, from the depth the radar
    published when it fired, and whether it had to be assumed.

    Price impact grows with size about linearly while the trade is small
    against the pool, so a clip a quarter of `max_buy_5pct_usd` moves the
    price about a quarter of 5 %, each way. Swap fees are not in it.
    """
    depth = signal.get("radar_max_buy_5pct_usd")
    if isinstance(depth, (int, float)) and depth > 0:
        return 2.0 * RADAR_IMPACT_PCT * clip_usd / depth, False
    return DEFAULT_ROUND_TRIP_COST_PCT, True


# How far a pair's age may drift from the clock between two readings before
# it is a different pair. Read off the real diary 2026-09-22: PUMP's age
# flipped 37.2 M <-> 17.6 M seconds hour by hour with its price 0.004 <-> 21,
# and 149 of 2481 read signals broke this way -- while `nub`'s rug (price
# /480, liquidity to three cents) kept time on one pair.
PAIR_AGE_SLACK_SECONDS = 3600.0


def switch_at(readings: list[dict]) -> int | None:
    """The index of the first reading on another pair, or None."""
    previous = None
    for index, row in enumerate(readings):
        age, when = row.get("age_seconds"), _at(row.get("at"))
        if not isinstance(age, (int, float)) or when is None:
            continue
        if previous is not None:
            elapsed = (when - previous[1]).total_seconds()
            if abs((age - previous[0]) - elapsed) > PAIR_AGE_SLACK_SECONDS:
                return index
        previous = (age, when)
    return None


def pair_changed(readings: list[dict]) -> bool:
    """Did memecoin-terminal answer a different PAIR somewhere along these
    readings (the signal row first, then its checkpoints in order)? A reading
    without `age_seconds` or a readable `at` cannot say, and is skipped."""
    return switch_at(readings) is not None


def _first_exit(path, entry: float, stop: float, target_pct: float | None):
    """The first point of `path` at or past the stop or the target, as
    (why, point), or None."""
    for point in path:
        ret = (point[1]["price_usd"] / entry - 1.0) * 100.0
        if ret <= -stop:
            return "stop", point
        if target_pct is not None and ret >= target_pct:
            return "target", point
    return None


def stop_study(rows: list[dict], stop_pct: float, target_pct: float | None = None,
               cost_pct: float | None = None, now=None,
               clip_usd: float = DEFAULT_CLIP_USD, top: int = 5,
               min_liquidity: float = MIN_LIQUIDITY_USD,
               min_volume: float = MIN_VOLUME_H24) -> dict:
    """Buy every hot signal at its own price, sell at the first checkpoint at
    or past the stop (`stop_pct` below entry, a magnitude) or the target
    (`target_pct` above it), AT THAT CHECKPOINT'S PRICE; otherwise at the last
    checkpoint of the day.

    Through `usable()` like every reader here, so a checkpoint filed under an
    hour it was not read in is not on the path and a coin nobody could trade
    is not a trade -- judged, as there, on the depth when the signal fired.
    Only windows that have closed: an open one shows its early stops and none
    of its late recoveries. The entry is the signal's own price -- a retried
    `entry` row is never taken for it.

    The sale is `clip_usd` sold into the pool at the exit reading, for at
    most half its liquidity (`capped_return`), as `ten_dollars` sells. A path
    on which their terminal answered a different pair (`pair_changed`) is a
    rug and stays in, counted as `switched`, paying no gain.

    `cost_pct` is a fixed round trip for every trade; left out, each trade
    pays `round_trip_cost` from the radar's published depth.
    """
    moment = now or datetime.now(timezone.utc)
    stop = abs(float(stop_pct))
    last = max(HORIZONS_HOURS)
    kept, filtered = usable(rows, min_liquidity, min_volume)
    signals = _signals(kept)

    paths: dict[str, list[tuple[float, dict]]] = {}
    read: dict[str, list[tuple[float, dict]]] = {}
    for row in kept:
        if row.get("type") != "checkpoint" or row.get("key") not in signals:
            continue
        hours, price = _hours(row.get("horizon")), row.get("price_usd")
        if hours is None:
            continue
        read.setdefault(row["key"], []).append((hours, row))
        if isinstance(price, (int, float)):
            paths.setdefault(row["key"], []).append((hours, row))

    excluded = {"window_open": 0, "unpriced": 0, "unread": 0,
                "unread_at_end": 0}
    trades = []
    for key, signal in signals.items():
        fired = _at(signal.get("at"))
        if fired is None or fired + timedelta(
                hours=last + due_tolerance(last)) > moment:
            excluded["window_open"] += 1
            continue
        entry = signal.get("price_usd")
        if not isinstance(entry, (int, float)) or entry <= 0:
            excluded["unpriced"] += 1
            continue
        path = sorted(paths.get(key) or [], key=lambda item: item[0])
        if not path:
            excluded["unread"] += 1
            continue
        # Their terminal answering another pair for the same address is not
        # a move of this coin: PUMP at 0.004 and 21 in alternate hours put
        # +31 620 % a trade on the first run of this study. It was left out
        # until 2026-09-23 measured every switch on record as the main pool
        # drained -- a rug, kept below and paid no gain.
        ordered = [signal] + [r for _, r in sorted(read.get(key) or [],
                                                   key=lambda item: item[0])]
        cut = switch_at(ordered)
        if max(h for h, _ in read[key]) < last:
            # The loop never got to the end of this hold (RM05, deep pass of
            # 2026-09-24, 3/3): counted off a path cut short, a stop kept the
            # trades that fell early and dropped the ones that would have
            # ridden the day -- every exit is held to it. READ, not priced:
            # an end reading with no price is a coin that stopped trading,
            # and its stop is the loss the stop exists for.
            excluded["unread_at_end"] += 1
            continue
        # An exit found on the pair the coin was bought on, before the switch,
        # is a real fill and is kept, as `compare` reads the peak up to the
        # switch (R01, deep pass of 2026-09-28, 2/3). Only a path that
        # reached the switch without one is the rug below.
        found = None
        if cut is not None:
            before = {id(r) for r in ordered[1:cut]}
            found = _first_exit([p for p in path if id(p[1]) in before],
                                entry, stop, target_pct)
        switched = cut is not None and found is None
        found = found or _first_exit(path, entry, stop, target_pct)
        why, (hours, at_exit) = found or ("last", path[-1])
        if why == "last" and hours < last:
            # Held to the end means READ to the end (RM02, deep pass of
            # 2026-09-24, 3/3): a path the loop stopped reading was sold at
            # its last reading as if held the day -- 308 of 1333 trades,
            # clustered where the loop stopped, the -10 % study -12.1 %
            # where it is -18.8 %. `ten_dollars` calls it unread_at_24h.
            # With the check above, what reaches here read the end unpriced.
            excluded["unread_at_end"] += 1
            continue
        if cost_pct is not None:
            cost, assumed = float(cost_pct), False
        else:
            cost, assumed = round_trip_cost(signal, clip_usd)
        gross = capped_return(
            (at_exit["price_usd"] / entry - 1.0) * 100.0, at_exit, clip_usd)
        if switched:
            gross = min(gross, 0.0)
        depth = signal.get("radar_max_buy_5pct_usd")
        trades.append({
            "key": key, "symbol": signal.get("symbol"), "exit": why,
            "exit_hours": hours, "gross_pct": gross, "cost_pct": cost,
            "net_pct": gross - cost, "cost_assumed": assumed,
            "switched": switched,
            "thin": isinstance(depth, (int, float)) and depth < clip_usd,
            # A stop can only fire at a point: a path with one inside the
            # first hour, at or before the exit, is where the minutes counted.
            "dense": any(h < 1.0 for h, _ in path if h <= hours),
        })

    nets = [t["net_pct"] for t in trades]
    spread = _spread(nets, top)
    costs = [t["cost_pct"] for t in trades]
    return {
        "stop_pct": stop, "target_pct": target_pct, "n": len(trades),
        "mean_net_pct": spread["pnl_pct"], "median_net_pct": spread["median_pct"],
        "mean_net_without_top_pct": spread["pnl_without_top_pct"], "top": top,
        "mean_gross_pct": (sum(t["gross_pct"] for t in trades) / len(trades)
                           if trades else None),
        "wins": sum(1 for n in nets if n > 0),
        "win_rate": (sum(1 for n in nets if n > 0) / len(nets)) if nets else None,
        "exits": {k: sum(1 for t in trades if t["exit"] == k)
                  for k in ("stop", "target", "last")},
        "dense_before_exit": sum(1 for t in trades if t["dense"]),
        "cost": {"mode": "fixed" if cost_pct is not None else "radar depth",
                 "clip_usd": clip_usd,
                 "median_round_trip_pct": median(costs) if costs else None,
                 "assumed": sum(1 for t in trades if t["cost_assumed"]),
                 "thin": sum(1 for t in trades if t["thin"])},
        "switched": sum(1 for t in trades if t["switched"]),
        "excluded": {**excluded,
                     "untradeable": filtered.get("n_untradeable", 0),
                     "late_readings": filtered.get("late_readings", 0)},
        "caveat": UNMEASURED_FILLS,
        "trades": trades,
    }


# --- $10 into every hot signal -------------------------------------------------
#
# [operator 2026-09-23] asked whether $10 into every hot signal would have had
# the liquidity and the time to buy it all -- whether the strategy is real and
# could be executed. The plan's V3 answers it here, as a buyer lives it.

TEN_DOLLAR_CLIP = 10.0
TEN_DOLLAR_HOLD_HOURS = 24.0
# Their swap fee is not published per pool; the answer is given at several. The headline is
# the one with no swap fee: the operator, 2026-10-08, after the laboratory dropped every fee it
# had assumed on paper -- "1% u memecoinu taky vyhod". The price impact of the clip against the
# radar's depth stays in every figure: it is measured, not a fee.
HEADLINE_FEE_PCT = 0.0
SWAP_FEES_PCT = (HEADLINE_FEE_PCT, 0.5, 1.0, 2.0)


def ten_dollars(rows: list[dict], now=None, clip_usd: float = TEN_DOLLAR_CLIP,
                hold_hours: float = TEN_DOLLAR_HOLD_HOURS,
                fees_pct=SWAP_FEES_PCT, top: int = 5) -> dict:
    """$10 into every hot signal, held a day, no stop, net of fees.

    Every signal whose day has closed is asked, in the order a buyer meets
    them: did we have its PRICE when it fired; did the radar's depth THEN
    (`max_buy_5pct_usd`) take the clip -- the depth at entry decides the buy,
    never a later reading, which is how `sellable` took the coins that
    rugged later out of their own history; was it read at the end of the
    day. The sale is capped by what the pool held then -- half its
    liquidity, the quote side of the pool -- so a drained pool pays about
    nothing, as it would have; a path on which their terminal answered
    another pair (`pair_changed`, `switched` counts them) is kept, and pays
    no gain. Each
    side pays the swap fee and the price impact of the clip against the
    radar's depth; the answer is given at 0.5, 1 and 2 % a side.

    `could_buy_share` is "stihli bychom": of the hot signals, the share we
    had a price for and could have put $10 into when they fired.
    """
    moment = now or datetime.now(timezone.utc)
    kept = in_time(rows)
    signals = _signals(kept)
    exits: dict[str, dict] = {}
    read: dict[str, list[tuple[float, dict]]] = {}
    for row in kept:
        if row.get("type") != "checkpoint" or row.get("key") not in signals:
            continue
        hours = _hours(row.get("horizon"))
        if hours is None or hours > hold_hours:
            continue
        read.setdefault(row["key"], []).append((hours, row))
        if hours == hold_hours:
            exits[row["key"]] = row

    excluded = {"unpriced": 0, "depth_unknown": 0, "too_thin": 0,
                "unread_at_24h": 0}
    window_open, asked, could_buy, trades, latency = 0, 0, 0, [], []
    switched = 0
    for key, signal in signals.items():
        fired = _at(signal.get("at"))
        if fired is None or fired + timedelta(
                hours=hold_hours + due_tolerance(hold_hours)) > moment:
            window_open += 1
            continue
        asked += 1
        entry = signal.get("price_usd")
        depth = signal.get("radar_max_buy_5pct_usd")
        if not isinstance(entry, (int, float)) or entry <= 0:
            excluded["unpriced"] += 1
            continue
        if not isinstance(depth, (int, float)) or isinstance(depth, bool):
            excluded["depth_unknown"] += 1
            continue
        if depth < clip_usd:
            excluded["too_thin"] += 1
            continue
        could_buy += 1
        waited = signal.get("radar_first_buy_seconds_ago")
        if isinstance(waited, (int, float)) and not isinstance(waited, bool):
            latency.append(waited / 60.0)
        ordered = [signal] + [r for _, r in sorted(read.get(key) or [],
                                                   key=lambda item: item[0])]
        last = exits.get(key) or {}
        price = last.get("price_usd")
        if not isinstance(price, (int, float)) or price <= 0:
            excluded["unread_at_24h"] += 1
            continue
        proceeds = clip_usd * price / entry
        liquidity = last.get("liquidity_usd")
        if isinstance(liquidity, (int, float)) and not isinstance(liquidity, bool):
            proceeds = min(proceeds, liquidity / 2.0)
        # A path on which their terminal answered another pair used to be
        # left out, as their defect. Measured 2026-09-23: all 60 switches
        # since pairs were recorded were the main pool drained to nothing
        # (DexScreener: FRIES's pumpswap pool at $0, FIBONACCI with no pool
        # at all) -- a rug, a loss the buyer takes. So it stays in: the sale
        # is capped by the pool that is left, as above, and a switched pair
        # pays no GAIN, because its price is not one the buyer's pool paid.
        if pair_changed(ordered):
            switched += 1
            proceeds = min(proceeds, clip_usd)
        trades.append({"key": key, "symbol": signal.get("symbol"),
                       "proceeds_usd": proceeds,
                       "impact_pct": RADAR_IMPACT_PCT * clip_usd / depth})

    by_fee = {}
    for fee in fees_pct:
        nets = [(t["proceeds_usd"] / clip_usd * (1 - fee / 100.0) ** 2
                 * (1 - t["impact_pct"] / 100.0) ** 2 - 1.0) * 100.0
                for t in trades]
        spread = _spread(nets, top)
        by_fee[fee] = {"n": len(nets), "mean_net_pct": spread["pnl_pct"],
                       "median_net_pct": spread["median_pct"],
                       "mean_net_without_top_pct": spread["pnl_without_top_pct"],
                       "win_rate": (sum(1 for n in nets if n > 0) / len(nets)
                                    if nets else None)}
    return {"clip_usd": clip_usd, "hold_hours": hold_hours, "top": top,
            "signals": asked, "window_open": window_open, "bought": len(trades),
            "could_buy": could_buy,
            "could_buy_share": could_buy / asked if asked else None,
            "first_buy_to_quote_min": median(latency) if latency else None,
            "excluded": excluded, "switched": switched, "by_fee": by_fee}
