"""Retail index v5: the pure part. Rules are in `outbox/retail-index/RESULT.md`, written before the first run.

Nothing here touches the network or a clock: `outbox/retail-index/fetch.py` reads the public sources and writes
the weekly table, and every function below takes that table (or a parsed answer) and returns numbers. Dates are
proleptic ordinals; a week is labelled by the Monday `W` after it and holds the days `[W-7, W)`, so a row only has
what was known at `W`, the same keying as Cymetica's own series.
"""

from __future__ import annotations

import math
import random
from datetime import date, datetime, timezone
from statistics import median

# ---- dates ---------------------------------------------------------------------------------

DAY = 1
WEEK = 7


def ordinal(text: str) -> int:
    return date.fromisoformat(text[:10]).toordinal()


def iso(o: int) -> str:
    return date.fromordinal(o).isoformat()


def ordinal_of_epoch(ts: float) -> int:
    return datetime.fromtimestamp(ts, timezone.utc).date().toordinal()


def monday_on_or_before(o: int) -> int:
    return o - date.fromordinal(o).weekday()


def week_grid(first_monday: int, last_monday: int) -> list[int]:
    return list(range(first_monday, last_monday + 1, WEEK))


# ---- daily -> weekly -----------------------------------------------------------------------

def week_sum(daily: dict, W: int, min_days: int = 6):
    vals = [daily[d] for d in range(W - 7, W) if daily.get(d) is not None]
    return sum(vals) * 7 / len(vals) if len(vals) >= min_days else None


def week_mean(daily: dict, W: int, min_days: int = 5):
    vals = [daily[d] for d in range(W - 7, W) if daily.get(d) is not None]
    return sum(vals) / len(vals) if len(vals) >= min_days else None


def week_last(daily: dict, W: int):
    for d in range(W - 1, W - 8, -1):
        if daily.get(d) is not None:
            return daily[d]
    return None


def fill_forward(daily: dict, first: int, last: int) -> dict:
    """Calendar days from `first` to `last`, a missing day carrying the last known value."""
    out, cur = {}, None
    for d in range(first, last + 1):
        if daily.get(d) is not None:
            cur = daily[d]
        if cur is not None:
            out[d] = cur
    return out


# ---- parsers: the JSON a source returned -> plain dicts --------------------------------------

def parse_coinbase_candles(rows) -> dict:
    """Coinbase Exchange daily candles [time, low, high, open, close, volume] -> {day: (close, usd_volume)}."""
    out = {}
    for c in rows or []:
        try:
            t, close, vol = int(c[0]), float(c[4]), float(c[5])
        except (TypeError, ValueError, IndexError):
            continue
        if t % 86400 == 0 and close > 0 and vol >= 0:
            out[ordinal_of_epoch(t)] = (close, vol * close)
    return out


def parse_binance_weeks(rows) -> dict:
    """Binance 1w klines -> {monday_open: (close, quote_volume)}."""
    out = {}
    for k in rows or []:
        try:
            out[ordinal_of_epoch(int(k[0]) / 1000)] = (float(k[4]), float(k[7]))
        except (TypeError, ValueError, IndexError):
            continue
    return out


def parse_upbit_weeks(rows) -> dict:
    """Upbit weekly candles -> {monday_open: (close_krw, traded_value_krw)}."""
    out = {}
    for c in rows or []:
        try:
            out[ordinal(c["candle_date_time_utc"])] = (float(c["trade_price"]), float(c["candle_acc_trade_price"]))
        except (TypeError, ValueError, KeyError):
            continue
    return out


def parse_funding(rows) -> dict:
    """Binance funding rows [{fundingTime ms, fundingRate}] -> {day: mean rate per 8 h}."""
    by_day: dict[int, list[float]] = {}
    for r in rows or []:
        try:
            by_day.setdefault(ordinal_of_epoch(int(r["fundingTime"]) / 1000), []).append(float(r["fundingRate"]))
        except (TypeError, ValueError, KeyError):
            continue
    return {d: sum(v) / len(v) for d, v in by_day.items()}


def parse_coinmetrics(rows) -> dict:
    """Coin Metrics rows -> {asset: {metric: {day: float}}}."""
    out: dict = {}
    for r in rows or []:
        try:
            day = ordinal(r["time"])
        except (KeyError, ValueError):
            continue
        for k, v in r.items():
            if k in ("asset", "time") or v is None:
                continue
            try:
                out.setdefault(r["asset"], {}).setdefault(k, {})[day] = float(v)
            except ValueError:
                continue
    return out


def parse_fx(rates: dict) -> dict:
    """Frankfurter {"2017-01-02": {"KRW": 1207.69}} -> {day: KRW per USD}."""
    out = {}
    for k, v in (rates or {}).items():
        try:
            out[ordinal(k)] = float(v["KRW"])
        except (KeyError, TypeError, ValueError):
            continue
    return out


def parse_fng(rows) -> dict:
    """alternative.me [{value, timestamp}] -> {day: value}."""
    out = {}
    for r in rows or []:
        try:
            out[ordinal_of_epoch(int(r["timestamp"]))] = float(r["value"])
        except (KeyError, TypeError, ValueError):
            continue
    return out


# ---- the weekly table ----------------------------------------------------------------------

def read_table(text: str) -> dict:
    """`data/weekly.csv` text -> {column: [value or None]}; `week` holds ordinals."""
    lines = [ln for ln in text.splitlines() if ln.strip()]
    head = lines[0].split(",")
    cols: dict[str, list] = {h: [] for h in head}
    for ln in lines[1:]:
        for h, v in zip(head, ln.split(",")):
            cols[h].append(ordinal(v) if h == "week" else (float(v) if v != "" else None))
    return cols


def index_csv(table: dict, result: dict) -> str:
    """The index as CSV text: week, index, families behind it, zone, and each family's score."""
    fams = list(FAMILIES)
    out = ["week,index,nfam,zone," + ",".join(fams)]
    for i, w in enumerate(table["week"]):
        v = result["index"][i]
        row = [iso(w), "" if v is None else f"{v:.2f}", str(result["nfam"][i]), zone(v) or ""]
        row += ["" if result["families"][f][i] is None else f"{result['families'][f][i]:.2f}" for f in fams]
        out.append(",".join(row))
    return "\n".join(out) + "\n"


# ---- the index -----------------------------------------------------------------------------

# family -> [(table column, detrend?)]. Equal weight per family, equal weight per member.
FAMILIES = {
    "turnover": [("cb_turn", True), ("up_turn", True), ("bn_turn", True)],
    "users": [("users_btc", True), ("users_eth", True)],
    "premia": [("kimchi", False), ("cb_prem", False)],
    "leverage": [("fund", False)],
    "chase": [("breadth", False), ("froth", False)],
}
PCT_WINDOW, PCT_MIN = 208, 52
DETREND_WINDOW, DETREND_MIN = 104, 26
ASLEEP, AWAKE_AT, SATURATED = 25.0, 40.0, 75.0


def detrend(x: list, window: int = DETREND_WINDOW, min_n: int = DETREND_MIN) -> list:
    """x divided by the median of its own previous `window` values (the current one is not in it)."""
    out = [None] * len(x)
    for i, v in enumerate(x):
        if v is None:
            continue
        past = [a for a in x[max(0, i - window):i] if a is not None]
        if len(past) < min_n:
            continue
        m = median(past)
        if m > 0:
            out[i] = v / m
    return out


def trailing_percentile(x: list, window: int = PCT_WINDOW, min_n: int = PCT_MIN) -> list:
    """Rank of each value among the trailing `window` weeks, itself included, ties half, 0 to 100."""
    out = [None] * len(x)
    for i, v in enumerate(x):
        if v is None:
            continue
        w = [a for a in x[max(0, i - window + 1):i + 1] if a is not None]
        if len(w) < min_n:
            continue
        less = sum(1 for a in w if a < v)
        eq = sum(1 for a in w if a == v)
        out[i] = 100.0 * (less + 0.5 * eq) / len(w)
    return out


def _mean(vals):
    vals = [v for v in vals if v is not None]
    return sum(vals) / len(vals) if vals else None


def compute_index(table: dict, drop_family: str | None = None) -> dict:
    """members, families, index and the number of families behind each week. `drop_family` leaves one family out."""
    n = len(table["week"])
    members: dict[str, list] = {}
    for fam, cols in FAMILIES.items():
        for col, trend in cols:
            x = table.get(col) or [None] * n
            members[col] = trailing_percentile(detrend(x) if trend else x)
    fams: dict[str, list] = {}
    for fam, cols in FAMILIES.items():
        fams[fam] = [_mean([members[c][i] for c, _ in cols]) for i in range(n)]
    index, nfam = [], []
    for i in range(n):
        vals = [fams[f][i] for f in FAMILIES if f != drop_family and fams[f][i] is not None]
        nfam.append(len(vals))
        index.append(sum(vals) / len(vals) if len(vals) >= 2 else None)
    return {"members": members, "families": fams, "index": index, "nfam": nfam}


def moving_mean(x: list, n: int = 4) -> list:
    """Mean of the last `n` weeks, only when all `n` exist. A reading aid added after the first back-test, so it is
    reported as post-hoc wherever it is scored: the rules in RESULT.md are the weekly index."""
    return [None if i < n - 1 or any(v is None for v in x[i - n + 1:i + 1]) else sum(x[i - n + 1:i + 1]) / n
            for i in range(len(x))]


def zone(v):
    if v is None:
        return None
    return "asleep" if v < ASLEEP else "waking" if v < AWAKE_AT else "active" if v < SATURATED else "saturated"


def awake_events(index: list) -> list[int]:
    """Positions where the index crosses up through 40 having been under 25 in the prior 26 weeks."""
    out = []
    for i in range(1, len(index)):
        if index[i] is None or index[i - 1] is None:
            continue
        if index[i - 1] < AWAKE_AT <= index[i]:
            prior = [v for v in index[max(0, i - 26):i] if v is not None]
            if prior and min(prior) < ASLEEP:
                out.append(i)
    return out


def runs_at_or_above(series: list, thr: float) -> list[tuple[int, int]]:
    out, start = [], None
    for i, v in enumerate(series):
        hot = v is not None and v >= thr
        if hot and start is None:
            start = i
        if not hot and start is not None:
            out.append((start, i - 1))
            start = None
    if start is not None:
        out.append((start, len(series) - 1))
    return out


# ---- statistics, in plain Python ----------------------------------------------------------------

def _ranks(vals: list[float]) -> list[float]:
    order = sorted(range(len(vals)), key=lambda i: vals[i])
    ranks = [0.0] * len(vals)
    i = 0
    while i < len(order):
        j = i
        while j + 1 < len(order) and vals[order[j + 1]] == vals[order[i]]:
            j += 1
        for k in range(i, j + 1):
            ranks[order[k]] = (i + j) / 2 + 1
        i = j + 1
    return ranks


def spearman(xs: list, ys: list):
    pairs = [(a, b) for a, b in zip(xs, ys) if a is not None and b is not None]
    if len(pairs) < 10:
        return None
    rx, ry = _ranks([p[0] for p in pairs]), _ranks([p[1] for p in pairs])
    mx, my = sum(rx) / len(rx), sum(ry) / len(ry)
    num = sum((a - mx) * (b - my) for a, b in zip(rx, ry))
    den = math.sqrt(sum((a - mx) ** 2 for a in rx) * sum((b - my) ** 2 for b in ry))
    return num / den if den else None


def forward_return(level: list, i: int, h: int):
    if i + h >= len(level) or level[i] is None or level[i + h] is None or level[i] <= 0:
        return None
    return level[i + h] / level[i] - 1


def block_bootstrap_diff(flags: list, fwd: list, block: int = 13, draws: int = 2000, seed: int = 1):
    """Mean forward return where flagged minus where not, with a 95% moving-block bootstrap interval."""
    idx = [i for i in range(len(flags)) if flags[i] is not None and fwd[i] is not None]
    if not idx:
        return None
    f = [bool(flags[i]) for i in idx]
    r = [fwd[i] for i in idx]
    n = len(idx)

    def stat(ii):
        a = [r[k] for k in ii if f[k]]
        b = [r[k] for k in ii if not f[k]]
        return (sum(a) / len(a) - sum(b) / len(b)) if a and b else None

    obs = stat(range(n))
    if obs is None:
        return {"n": n, "flagged": sum(f), "diff": None, "lo": None, "hi": None}
    rng = random.Random(seed)
    got = []
    for _ in range(draws):
        ii = []
        while len(ii) < n:
            s = rng.randrange(0, max(1, n - block + 1))
            ii.extend(range(s, min(n, s + block)))
        v = stat(ii[:n])
        if v is not None:
            got.append(v)
    got.sort()
    lo = got[int(0.025 * len(got))] if got else None
    hi = got[int(0.975 * len(got)) - 1] if got else None
    return {"n": n, "flagged": sum(f), "diff": obs, "lo": lo, "hi": hi}


def zigzag(level: list, reversal: float = 0.4) -> list[tuple[int, str]]:
    """Turning points of a level series: a top is confirmed by a fall of `reversal` from the peak (to 60%),
    a bottom by a rise of the same size in log terms (+67%)."""
    thr = math.log(1 / (1 - reversal))
    pts = [(i, math.log(v)) for i, v in enumerate(level) if v is not None and v > 0]
    if len(pts) < 3:
        return []
    out = []
    mode = None
    hi_i = lo_i = ext_i = pts[0][0]
    hi = lo = ext = pts[0][1]
    for i, v in pts[1:]:
        if mode is None:
            if v > hi:
                hi_i, hi = i, v
            if v < lo:
                lo_i, lo = i, v
            # the first extreme of a series is where the data starts, not a turning point: it is not reported
            if hi - v >= thr:
                if hi_i != pts[0][0]:
                    out.append((hi_i, "top"))
                mode, ext_i, ext = "down", i, v
            elif v - lo >= thr:
                if lo_i != pts[0][0]:
                    out.append((lo_i, "bottom"))
                mode, ext_i, ext = "up", i, v
        elif mode == "up":
            if v > ext:
                ext_i, ext = i, v
            elif ext - v >= thr:
                out.append((ext_i, "top"))
                mode, ext_i, ext = "down", i, v
        else:
            if v < ext:
                ext_i, ext = i, v
            elif v - ext >= thr:
                out.append((ext_i, "bottom"))
                mode, ext_i, ext = "up", i, v
    return out


# ---- events and checks -----------------------------------------------------------------------

TOP_DATES = ("2018-01-15", "2021-05-17", "2021-11-08", "2024-12-16")
LOW_DATES = ("2018-12-17", "2022-11-21", "2023-09-04")
HALF = 6
TOP_MIN, LOW_MAX, SPEARMAN_MAX, SHARE_MAX, LEAVE_MAX = 70.0, 35.0, 0.40, 0.10, 15.0


def window_positions(weeks: list, center: int, half: int = HALF) -> list[int]:
    return [i for i, w in enumerate(weeks) if center - half * WEEK <= w <= center + half * WEEK]


def check_windows(series: list, weeks: list, nfam: list | None, dates: tuple, kind: str, half: int = HALF) -> list[dict]:
    """B1 (kind 'top': highest week >= 70) or B2 (kind 'low': lowest week <= 35) for each dated window."""
    out = []
    for d in dates:
        pos = [i for i in window_positions(weeks, ordinal(d), half) if series[i] is not None]
        if nfam is not None:
            pos = [i for i in pos if nfam[i] >= 2]
        if not pos:
            out.append({"date": d, "status": "not scorable", "value": None, "week": None, "thin": False})
            continue
        pick = max(pos, key=lambda i: series[i]) if kind == "top" else min(pos, key=lambda i: series[i])
        v = series[pick]
        ok = v >= TOP_MIN if kind == "top" else v <= LOW_MAX
        out.append({"date": d, "status": "pass" if ok else "fail", "value": round(v, 1), "week": iso(weeks[pick]),
                    "thin": bool(nfam is not None and nfam[pick] == 2)})
    return out


def capture(series: list, weeks: list, nfam: list | None, centers: list[int], kinds: list[str], half: int = HALF):
    """Share of scorable windows that pass (B1 for tops, B2 for lows)."""
    got = tot = 0
    for c, k in zip(centers, kinds):
        pos = [i for i in window_positions(weeks, c, half) if series[i] is not None and (nfam is None or nfam[i] >= 2)]
        if not pos:
            continue
        tot += 1
        v = max(series[i] for i in pos) if k == "top" else min(series[i] for i in pos)
        got += (v >= TOP_MIN) if k == "top" else (v <= LOW_MAX)
    return (got / tot) if tot else None, tot


def permutation_p(series: list, weeks: list, nfam: list | None, centers: list[int], kinds: list[str],
                  block: int = 13, draws: int = 2000, seed: int = 1):
    """Share of block shuffles of the same weeks that capture at least as many windows as the real order."""
    obs, tot = capture(series, weeks, nfam, centers, kinds)
    if obs is None:
        return None
    rng = random.Random(seed)
    n = len(series)
    blocks = [list(range(s, min(n, s + block))) for s in range(0, n, block)]
    at_least = 0
    for _ in range(draws):
        order = blocks[:]
        rng.shuffle(order)
        pos = [i for b in order for i in b]
        shuf = [series[i] for i in pos]
        nf = [nfam[i] for i in pos] if nfam is not None else None
        v, _t = capture(shuf, weeks, nf, centers, kinds)
        if v is not None and v >= obs:
            at_least += 1
    return at_least / draws


def drawdown_after(alt: list, i: int, h: int = 26):
    """Deepest fall from the running maximum within `h` weeks of week `i` (0.3 = fell 30%), or None with no level."""
    if alt[i] is None:
        return None
    peak, worst = alt[i], 1.0
    for t in range(i, min(len(alt), i + h + 1)):
        if alt[t] is None:
            continue
        peak = max(peak, alt[t])
        worst = min(worst, alt[t] / peak)
    return 1 - worst


def best_rise_after(alt: list, i: int, h: int = 26):
    if alt[i] is None:
        return None
    return max((alt[t] / alt[i] - 1 for t in range(i, min(len(alt), i + h + 1)) if alt[t] is not None), default=0.0)


def base_rates(alt: list, lo: int | None = None, hi: int | None = None, h: int = 26, fall: float = 0.30, rise: float = 0.50) -> dict:
    """How often ANY week is followed by such a fall / such a rise: what a signal has to beat. Only weeks with the
    whole horizon ahead of them count."""
    last = len(alt) - h - 1
    idx = [i for i in range(0, last + 1) if alt[i] is not None and (lo is None or i >= lo) and (hi is None or i <= hi)]
    if not idx:
        return {"weeks": 0, "fall": None, "rise": None}
    return {"weeks": len(idx), "fall": sum(drawdown_after(alt, i, h) >= fall for i in idx) / len(idx),
            "rise": sum(best_rise_after(alt, i, h) >= rise for i in idx) / len(idx)}


def saturated_outcomes(index: list, alt: list, h: int = 26, fall: float = 0.30) -> dict:
    """Each run at 75 and over: did the alt basket fall `fall` from its running maximum within `h` weeks of the start?"""
    res = []
    for a, b in runs_at_or_above(index, SATURATED):
        dd = drawdown_after(alt, a, h)
        if dd is None:
            continue
        res.append({"start": a, "end": b, "length": b - a + 1, "fell": dd >= fall, "drawdown": round(dd, 3)})
    return {"runs": res, "share": (sum(r["fell"] for r in res) / len(res)) if res else None}


def awake_outcomes(index: list, alt: list, h: int = 26, rise: float = 0.50) -> dict:
    res = []
    for i in awake_events(index):
        best = best_rise_after(alt, i, h)
        if best is None:
            continue
        res.append({"at": i, "rose": best >= rise, "best": round(best, 3)})
    return {"events": res, "share": (sum(r["rose"] for r in res) / len(res)) if res else None}


def top_zone_share(series: list) -> tuple:
    vals = [v for v in series if v is not None]
    if not vals:
        return None, 0
    longest = max((b - a + 1 for a, b in runs_at_or_above(series, SATURATED)), default=0)
    return sum(1 for v in vals if v >= SATURATED) / len(vals), longest
