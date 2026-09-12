"""The register of what has already been tested, keyed on the basket.

[operator 2026-09-12] *"dyt jsem jasne na zacaktu rikal ze se v laboratori ma
vest denik at vi co uz se testovalo atd ne, dyt to je kriticka cast."*

They had said it at the start and what got built was a diary of SESSIONS --
opened, closed, three lessons -- which records our own activity and answers a
question nobody asked. This answers theirs: **which basket, over which window,
with what result.** Without it every night re-grinds the same candidates and
months of work accumulate nothing.

    fingerprint   one basket, one id, however the legs are written down
    already       has this been asked, recently enough to still be true?
    record        one answer, compactly, with what was lost from it
    best          the clean readings, risk-adjusted, for the search to climb

`state/backtests.jsonl` is gitignored for the reason the other diaries are: it
is appended to while a run may be in flight and a dirty tree costs a level-V
run. `scripts/keep.py snapshot` copies it into audits/lab/, which is what stops
months of work living on one disk.

Size, since this is the file that grows: a row is roughly 200 bytes, so a night
of three hundred backtests is 60 kB and a month is under 2 MB. The patrol's
ceilings are the alarm if a search ever goes wider than that.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from qa.state import file_lock, state_dir

REGISTER = "backtests.jsonl"

# Theirs, from the tool's own description: 2-20 legs, and the window is one of
# these five. Refused here rather than at their server, so a mistyped window
# never becomes a call -- and never becomes a row that looks like an answer.
MIN_LEGS, MAX_LEGS = 2, 20
PERIODS = (7, 30, 90, 180, 365)

# How long a reading stays true. The window SLIDES: a 7-day backtest taken
# yesterday covers a different week today, while a year barely moves. A tenth
# of its own window, and never more than a month or nothing would ever refresh.
STALE_FRACTION = 0.1
STALE_MIN_DAYS, STALE_MAX_DAYS = 1.0, 30.0


# Theirs: "30/min per IP", from the backtest API document. Kept on our side of
# the wire, so a night that searches hard is refused by nobody, and so the pace
# is a number in one place rather than a habit.
PER_MINUTE = 30
WINDOW_SECONDS = 60.0


class BacktestError(ValueError):
    """A basket the register refuses before anything is called or written."""


def next_slot(recent: list[float], now: float, limit: int = PER_MINUTE,
              window: float = WINDOW_SECONDS) -> float:
    """Seconds to wait before the next call, given when the recent ones went.

    Monotonic seconds, not wall clock: a night runs for hours and a clock that
    steps backwards would hand out a free burst.
    """
    inside = sorted(t for t in recent if now - t < window)
    if len(inside) < limit:
        return 0.0
    return max(0.0, window - (now - inside[-limit]))


def path() -> Path:
    return state_dir() / REGISTER


def stale_after(period_days: float) -> float:
    """Days a reading over this window stays usable."""
    return min(max(float(period_days) * STALE_FRACTION, STALE_MIN_DAYS),
               STALE_MAX_DAYS)


def legs_of(constituents) -> list[tuple[str, float]]:
    """The basket in one form, so two spellings of it cannot be two baskets.

    Sorted, upper-cased and renormalised to sum to one -- their own tool says
    "weights are renormalized", so 1:1 and 0.5:0.5 are the same call and must
    not be two rows. Rounded, because a float that differs in the twelfth place
    is the same basket and would otherwise defeat the whole register.
    """
    legs = []
    for leg in constituents or []:
        symbol = str((leg or {}).get("symbol") or "").strip().upper()
        try:
            weight = float((leg or {}).get("weight"))
        except (TypeError, ValueError):
            raise BacktestError(f"leg {leg!r} has no readable weight")
        if not symbol:
            raise BacktestError(f"leg {leg!r} has no symbol")
        if weight <= 0:
            raise BacktestError(f"{symbol} carries weight {weight}")
        legs.append((symbol, weight))

    if not MIN_LEGS <= len(legs) <= MAX_LEGS:
        raise BacktestError(
            f"a basket is {MIN_LEGS}-{MAX_LEGS} legs, not {len(legs)}")
    if len({symbol for symbol, _ in legs}) != len(legs):
        raise BacktestError("the same symbol twice in one basket")

    total = sum(weight for _, weight in legs)
    return sorted((symbol, round(weight / total, 6)) for symbol, weight in legs)


def fingerprint(constituents, period_days: int, include_fees: bool = False,
                starting_capital: float = 1000.0) -> str:
    """One id per question asked of their backtest, not per time we asked it."""
    if int(period_days) not in PERIODS:
        raise BacktestError(
            f"period_days is one of {PERIODS}, not {period_days}")
    material = json.dumps({"legs": legs_of(constituents),
                           "period_days": int(period_days),
                           "include_fees": bool(include_fees),
                           "starting_capital": round(float(starting_capital), 2)},
                          sort_keys=True)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def load() -> list[dict]:
    target = path()
    if not target.is_file():
        return []
    out = []
    for line in target.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            # A half-written line is normal while another process appends, and
            # it may not cost us the rest of the register.
            continue
        if isinstance(row, dict) and row.get("fp"):
            out.append(row)
    return out


def _number(payload: dict, *names):
    """A figure they gave, or None. Never a zero standing in for a silence."""
    for name in names:
        value = payload.get(name)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return round(float(value), 4)
    return None


def record(constituents, period_days: int, answer: dict, why: str = "",
           include_fees: bool = False, starting_capital: float = 1000.0,
           now: datetime | None = None) -> dict:
    """One answer, written down compactly and once.

    `lost` is what their answer says it could not price. A basket measured
    without one of its legs is a measurement of a DIFFERENT basket, so it is
    kept -- re-asking it would only lose the leg again -- and held out of the
    ranking rather than silently compared with clean readings.
    """
    answer = answer or {}
    lost = sorted({str(s) for key in ("unresolved_symbols", "dropped_symbols")
                   for s in (answer.get(key) or [])})
    row = {
        "fp": fingerprint(constituents, period_days, include_fees, starting_capital),
        "at": (now or datetime.now(timezone.utc)).isoformat(timespec="seconds"),
        "p": int(period_days),
        "legs": [[symbol, weight] for symbol, weight in legs_of(constituents)],
        "r": _number(answer, "total_return_pct"),
        "s": _number(answer, "sharpe_ratio"),
        "d": _number(answer, "max_drawdown_pct"),
        "pts": _number(answer, "n_points"),
    }
    if include_fees:
        row["fees"] = True
    if lost:
        row["lost"] = lost
    if why:
        row["why"] = why[:120]

    target = path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(target):
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def _at(value) -> datetime | None:
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)


def already(fp: str, rows: list[dict] | None = None,
            now: datetime | None = None) -> dict | None:
    """The newest reading of this exact question, if it is still true.

    None means ask them. It does NOT mean nobody ever asked: a stale row is
    still in the file, and the caller that wants the history reads `load`.
    """
    moment = now or datetime.now(timezone.utc)
    newest = None
    for row in (load() if rows is None else rows):
        if row.get("fp") != fp:
            continue
        when = _at(row.get("at"))
        if when is None:
            continue
        if newest is None or when > _at(newest["at"]):
            newest = row
    if newest is None:
        return None
    age = (moment - _at(newest["at"])).total_seconds() / 86400.0
    return newest if age <= stale_after(newest.get("p") or 30) else None


def best(rows: list[dict], now: datetime | None = None,
         limit: int = 20) -> list[dict]:
    """The clean, still-true readings, risk-adjusted, best first.

    Held out: anything whose basket lost a leg, and anything with no Sharpe --
    their own contract is that a strategy with no runs returns a note and never
    a fabricated number, and ranking a silence as a zero would be us doing what
    they refused to. Same rule as `qa.lab.rank`, and for the same reason.
    """
    moment = now or datetime.now(timezone.utc)
    seen: dict[str, dict] = {}
    for row in rows:
        if row.get("lost") or row.get("s") is None:
            continue
        when = _at(row.get("at"))
        if when is None:
            continue
        if (moment - when).total_seconds() / 86400.0 > stale_after(row.get("p") or 30):
            continue
        held = seen.get(row["fp"])
        if held is None or when > _at(held["at"]):
            seen[row["fp"]] = row
    return sorted(seen.values(),
                  key=lambda r: (-(r["s"] or 0.0), r.get("d") or 0.0))[:limit]
