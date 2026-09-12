"""The laboratory's notebook: what a session did, what it learned, what is next.

The rooms hold the strategies and the correspondence; `state/nexus.jsonl` holds
what Nexus was asked. What none of them holds is the laboratory ITSELF -- that a
session happened, what it cost, what it learned, and what the next one should
pick up. A session with Nexus left no record of itself before 2026-09-12, which
is why the deep pass could not look back at it and why every session started
from whatever was in front of it.

    session   opened when a session starts, closed when it ends. An open row
              with no close is a session that died -- the patrol says so.
    truth     one ranked snapshot of their backtest surfaces, so a later
              session can see what the ranking looked like before an answer.
    surface   the tool catalogue as it stood, for the comparison against
              audits/nexus-baseline.json: their CEO says the core AI arrives
              within days, and a catalogue nobody snapshotted cannot be
              compared to anything.
    cycle     one pass of the loop, and what it did.

`state/lab.jsonl` is gitignored for the reason state/nexus.jsonl is: it is
appended to while a run may be in flight, and a dirty tree costs a level-V run.
`scripts/keep.py snapshot` copies it into audits/lab/ so months of it do not
live on one disk.

The caps are here rather than in the skill because a limit written in prose is
a limit the next session can talk itself out of. They are the operator's to
veto, and the reasons are in docs/lab-plan.md.
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from qa.state import file_lock, state_dir

NOTEBOOK = "lab.jsonl"
KINDS = ("session", "truth", "surface", "cycle")
MAX_LESSONS = 3
MAX_NEXT = 8
ID = re.compile(r"^LAB-(\d{4})$")

# What one session may spend. Nexus's own guide is explicit that an open-ended
# night "drifts, burns calls, and gives you no way to judge what it found".
CAPS = {
    "questions_per_session": 8,
    "questions_per_night": 12,
    "new_rooms_per_session": 3,
    "running_experiments": 6,
    "share_of_free_cash": 0.15,
}


class LabError(ValueError):
    """A write the notebook refuses, before anything is written."""


def path() -> Path:
    return state_dir() / NOTEBOOK


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
            # A half-written line is normal while another process appends.
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _append(record: dict) -> dict:
    target = path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(target):
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def _next_id(rows: list[dict]) -> str:
    used = [int(ID.match(str(r.get("session") or "")).group(1))
            for r in rows if ID.match(str(r.get("session") or ""))]
    return f"LAB-{max(used, default=0) + 1:04d}"


def open_session(mode: str = "session", note: str | None = None,
                 until: str | None = None) -> dict:
    """Start one, and say which kind it is: a session, or a night.

    A night carries the hour it will end. Without it an open night looks
    exactly like a session somebody forgot to close, and the reminder would nag
    at every session start for the fourteen hours the thing is doing precisely
    what it was told.
    """
    rows = load()
    record = {"type": "session", "state": "open", "at": _now(),
              "session": _next_id(rows), "mode": mode}
    if note:
        record["note"] = note
    if until:
        record["until"] = until
    return _append(record)


def night_running(rows: list[dict] | None = None,
                  now: datetime | None = None) -> tuple[str, str] | None:
    """An open night still inside the hours it was given, and until when."""
    rows = load() if rows is None else rows
    moment = now or datetime.now(timezone.utc)
    until = {}
    for row in rows:
        if (row.get("type") == "session" and row.get("mode") == "night"
                and row.get("until")):
            until[str(row.get("session"))] = str(row["until"])
    for session in open_sessions(rows):
        due = _at(until.get(session))
        if due and moment < due:
            return session, until[session]
    return None


def open_sessions(rows: list[dict] | None = None) -> list[str]:
    """Sessions opened and never closed -- a laboratory that died mid-run."""
    rows = load() if rows is None else rows
    opened, closed = [], set()
    for row in rows:
        if row.get("type") != "session":
            continue
        if row.get("state") == "open":
            opened.append(str(row.get("session")))
        elif row.get("state") == "closed":
            closed.add(str(row.get("session")))
    return [s for s in opened if s not in closed]


def close_session(session: str, lessons: list[str], nextup: list[str],
                  did: dict | None = None) -> dict:
    """End it, with at most three lessons and a queue the next one reads.

    Three, because a notebook that grows every run stops being read -- the same
    bound CLAUDE.md puts on memories, for the same reason. The queue is what
    replaces "where did we stop"; it is the whole of the handover.
    """
    if len(lessons) > MAX_LESSONS:
        raise LabError(
            f"at most {MAX_LESSONS} lessons per session, not {len(lessons)}. "
            f"A notebook that grows every run stops being read")
    if len(nextup) > MAX_NEXT:
        raise LabError(f"at most {MAX_NEXT} items in the queue, not {len(nextup)}")
    rows = load()
    if session not in open_sessions(rows):
        raise LabError(f"{session} is not an open session")
    # The mode is carried over from the row that opened it, so the morning can
    # read "was that a night?" off the close alone.
    mode = "session"
    for row in rows:
        if row.get("type") == "session" and row.get("session") == session:
            mode = str(row.get("mode") or mode)
    return _append({"type": "session", "state": "closed", "at": _now(),
                    "session": session, "mode": mode, "lessons": list(lessons),
                    "next": list(nextup), "did": did or {}})


def last_close(rows: list[dict] | None = None) -> dict | None:
    """The newest closed session: its lessons and its queue are the handover."""
    rows = load() if rows is None else rows
    closed = [r for r in rows
              if r.get("type") == "session" and r.get("state") == "closed"]
    return closed[-1] if closed else None


def note_truth(ranked: list[dict], evidence: list[str] | None = None) -> dict:
    """One ranked snapshot of their backtest surfaces."""
    return _append({"type": "truth", "at": _now(), "ranked": ranked,
                    "evidence_ids": list(evidence or [])})


def last_truth(rows: list[dict] | None = None) -> dict | None:
    rows = load() if rows is None else rows
    seen = [r for r in rows if r.get("type") == "truth"]
    return seen[-1] if seen else None


def note_surface(tools: list[str], evidence: str | None = None) -> dict:
    """The tool catalogue as it stands, for the before-and-after comparison."""
    record = {"type": "surface", "at": _now(), "tools": sorted(set(tools))}
    if evidence:
        record["evidence_id"] = evidence
    return _append(record)


def last_surface(rows: list[dict] | None = None) -> dict | None:
    rows = load() if rows is None else rows
    seen = [r for r in rows if r.get("type") == "surface"]
    return seen[-1] if seen else None


def note_cycle(did: dict) -> dict:
    return _append({"type": "cycle", "at": _now(), "did": did})


def may_ask(asked: int, pass_running: bool, mode: str = "session") -> tuple[bool, str]:
    """Whether another question may go to Nexus now.

    Not while a deep pass is running. That pass verifies #85 (the newest answer
    that names a tool), #86 (the last five questions) and #87 (the newest
    trade) -- so a question asked mid-run changes the subject the pass is
    measuring, and the verdict it sends the vendor is then about something
    else. Ours to wait; theirs to receive one true answer.

    A night gets the larger cap because it is hours long and paced two hours
    apart; a session gets eight because a person is waiting through them.
    """
    if pass_running:
        return False, ("a deep pass is running: it is verifying #85, #86 and "
                       "#87 over these very answers. Ask after it finishes")
    cap = CAPS["questions_per_night" if mode == "night"
               else "questions_per_session"]
    if asked >= cap:
        return False, (f"{asked} questions already this session, and the cap is "
                       f"{cap}: an open-ended loop drifts and burns calls, "
                       f"which is Cymetica's own warning about the night")
    return True, ""


def affordable(usdc: float, free_cash: float | None,
               running: int) -> tuple[bool, str]:
    """Whether one experiment may take this much, and how many may run at once.

    A share of what is FREE, not of the bankroll: the book already knows what
    is deployed. An unreadable book refuses -- rule 8, and the same refusal
    paper.py makes when it cannot read what is in the bots.
    """
    if free_cash is None:
        return False, ("the book could not be read, and an unreadable book is "
                       "not an empty one: no order goes out on it")
    if running >= CAPS["running_experiments"]:
        return False, (f"{running} experiments are already running and the cap "
                       f"is {CAPS['running_experiments']}: past that nothing "
                       f"gets watched properly")
    share = CAPS["share_of_free_cash"]
    ceiling = free_cash * share
    if usdc > ceiling:
        return False, (f"{usdc:.0f} is more than {share * 100:.0f}% of the "
                       f"{free_cash:.0f} free ({ceiling:.0f}). Percentages are "
                       f"what a verdict compares, so a smaller stake measures "
                       f"the same strategy")
    return True, f"{usdc:.0f} of {free_cash:.0f} free, {running} running"


POLLABLE_HOURS = 24


def outstanding(nexus_rows: list[dict], now: datetime | None = None,
                within_hours: int = POLLABLE_HOURS) -> list[str]:
    """Questions we asked and never wrote an answer or a give-up for.

    A foreground ask is killed at ten minutes by the tool that runs it while
    nexus.py waits fifteen, so the question is on their server and our end of
    it is missing. The next cycle polls these; nothing else would.

    Only the recent ones. Three questions from 2026-09-10 carry a question row
    and nothing else -- asked with --no-wait and never picked up -- and their
    investigations take one to five minutes by their own contract. Polling a
    two-day-old job id every cycle for ever would be a loop that cannot finish,
    which is the shape of the checks this repository spent a day repairing.
    """
    moment = now or datetime.now(timezone.utc)
    asked, finished = [], set()
    for row in nexus_rows:
        kind, ident = row.get("type"), str(row.get("id") or "")
        if not ident:
            continue
        if kind == "question":
            when = row.get("at")
            try:
                stamp = datetime.fromisoformat(str(when).replace("Z", "+00:00"))
            except (TypeError, ValueError):
                continue
            if stamp.tzinfo is None:
                stamp = stamp.replace(tzinfo=timezone.utc)
            if (moment - stamp).total_seconds() <= within_hours * 3600:
                asked.append(ident)
        elif kind in ("answer", "gave_up", "refused", "failed"):
            finished.add(ident)
    return [ident for ident in asked if ident not in finished]


# --- the night -------------------------------------------------------------
#
# [operator 2026-09-12] No scheduler, ever: they start everything themselves.
# A night is therefore one process with an end written into it, not a task that
# comes back tomorrow -- and these numbers are what keep it from behaving like
# one. Their own guide is the source of the pace: an open-ended loop "drifts,
# burns calls, and gives you no way to judge what it found".
NIGHT = {
    "tick_seconds": 600,          # how often it looks at the clock
    "cycle_seconds": 1800,        # pick answers up, sample, compare the catalogue
    "truth_seconds": 6 * 3600,    # re-rank their backtests when the snapshot ages
    "ask_seconds": 2 * 3600,      # two hours between questions, and the floor
                                  # under a backoff their failure did not size
    "max_hours": 14,              # `--until` further out than this is a typo
}
HHMM = re.compile(r"^([01]\d|2[0-3]):([0-5]\d)$")


def deadline(text: str, now: datetime | None = None) -> datetime:
    """The hour the operator will wake up, on the operator's own clock.

    Everything else in this repository is UTC, and this is the one place where
    it must not be: they type the time they will get up. `now` carries the zone
    -- the CLI passes the machine's, a test passes a fixed one -- so the hour
    means the same thing to both. Refused rather than guessed: anything that is
    not HH:MM, and anything more than half a day out, which is what a mistyped
    hour looks like and would run the machine through the next day.
    """
    moment = now or datetime.now().astimezone()
    match = HHMM.match(str(text).strip())
    if not match:
        raise LabError(f"--until wants HH:MM on your own clock, not {text!r}")
    due = moment.replace(hour=int(match.group(1)), minute=int(match.group(2)),
                         second=0, microsecond=0)
    if due <= moment:
        due += timedelta(days=1)
    hours = (due - moment).total_seconds() / 3600
    if hours > NIGHT["max_hours"]:
        raise LabError(
            f"{text} resolves to {due.isoformat(timespec='minutes')}, "
            f"{hours:.1f} hours away, and a night stops at "
            f"{NIGHT['max_hours']} hours. Name an hour before then")
    return due


def backoff_until(nexus_rows: list[dict], now: datetime | None = None):
    """When the lane may be tried again, after their side gave up on us.

    Their failures carry `retry_after_s` when they know; six in a row on
    2026-09-11 did. Without one, two hours -- the same pace the night keeps
    anyway. One answer since the last failure means the lane is open and there
    is nothing to wait for.
    """
    moment = now or datetime.now(timezone.utc)
    failed, answered = None, None
    for row in nexus_rows:
        when = _at(row.get("at"))
        if when is None:
            continue
        if row.get("type") == "gave_up":
            failed = (when, row)
        elif row.get("type") == "answer":
            answered = when
    if failed is None or (answered is not None and answered > failed[0]):
        return None
    seconds = failed[1].get("retry_after_s")
    wait = float(seconds) if isinstance(seconds, (int, float)) and seconds > 0 \
        else NIGHT["ask_seconds"]
    until = failed[0] + timedelta(seconds=wait)
    return until if until > moment else None


def night_tick(state: dict, now: datetime) -> dict:
    """What this tick of the night may do, and if nothing, which nothing.

    Pure, so the whole night can be replayed in a test in milliseconds. A deep
    pass stops the tick whole rather than only its question: picking an answer
    up WRITES it down, and #86 counts the last five questions over that very
    file -- a read that writes is a writer, and that mistake has been made here
    before. The skip reasons are counted and printed at dawn, because a night
    that was blocked for eight hours and a night that found nothing look
    identical without them.
    """
    if state.get("pass_running"):
        return {"do": [], "skipped": "pass"}

    def _stale(key: str, seconds: float) -> bool:
        last = state.get(key)
        return last is None or (now - last).total_seconds() >= seconds

    do = []
    if _stale("last_cycle", NIGHT["cycle_seconds"]):
        do.append("cycle")
    if _stale("last_truth", NIGHT["truth_seconds"]):
        do.append("truth")

    # The skip reason is the ASK's, whatever else the tick did. A tick that
    # cycled but could not ask is exactly the one worth counting: without it a
    # night held off by a backoff all night reads as a night with nothing to say.
    hold = state.get("hold_until")
    if not _stale("last_ask", NIGHT["ask_seconds"]):
        skipped = "too soon"
    elif hold is not None and now < hold:
        skipped = "backoff"
    elif state.get("asked", 0) >= CAPS["questions_per_night"]:
        skipped = "cap"
    elif not state.get("candidates"):
        skipped = "nothing to ask about"
    else:
        do.append("ask")
        skipped = ""
    return {"do": do, "skipped": skipped}


COVERAGE_FLOOR = 0.8


def _at(value) -> datetime | None:
    try:
        stamp = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return stamp if stamp.tzinfo else stamp.replace(tzinfo=timezone.utc)


def _points(rows) -> list[tuple[datetime, float]]:
    """Their index history, in the shape they publish: [{t, index}, ...]."""
    out = []
    for row in rows or []:
        if isinstance(row, dict):
            when, value = _at(row.get("t") or row.get("at")), row.get("index")
        elif isinstance(row, (list, tuple)) and len(row) >= 2:
            when, value = _at(row[0]), row[1]
        else:
            continue
        if when is not None and isinstance(value, (int, float)):
            out.append((when, float(value)))
    return sorted(out)


def formula_fingerprint() -> str:
    """The hash of the verdict's own source.

    Improving a derivation rewrites the past: a verdict recorded last week was
    produced by last week's formula, and a better one silently re-judging it is
    the defect `improving-a-derivation-rewrites-the-past` names. Every verdict
    carries the fingerprint of the code that made it, so a change is visible
    rather than retroactive.
    """
    import hashlib
    import inspect

    try:
        source = inspect.getsource(verdict)
    except (OSError, TypeError):  # pragma: no cover -- frozen or stripped
        return "unknown"
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:12]


def verdict(acceptance: dict, series: dict, now) -> dict:
    """Did the strategy do what it was accepted on? Numbers only, no opinion.

    The acceptance is written BEFORE the room goes running, so nothing here can
    be fitted to what happened. What it holds: the window, the stop, the legs
    as Nexus gave them (card, side, share, take-profit, stop), and optionally a
    benchmark card -- their own guide asks whether a strategy beats BTC, not
    whether it is merely positive.

    Four ways out, and three of them are not "it lost":

        open           the window has not closed yet
        inconclusive   the data does not cover the window (rule 8: a gap is
                       not a loss) or a leg never had an entry price
        refuted        it lost, or it lost to the benchmark, or its drawdown
                       went past the stop it was accepted with
        survived       none of the above
    """
    start = _at(acceptance.get("at"))
    days = float(acceptance.get("window_days") or 0)
    if start is None or days <= 0:
        return {"verdict": "inconclusive", "why": "the acceptance names no window",
                "coverage": 0.0, "formula": formula_fingerprint()}
    end = start + timedelta(days=days)
    moment = _at(now) or datetime.now(timezone.utc)
    if moment < end:
        return {"verdict": "open", "why": f"the window closes {end.isoformat()}",
                "closes_at": end.isoformat(), "coverage": None,
                "formula": formula_fingerprint()}

    legs, covered = [], []
    for leg in acceptance.get("legs") or []:
        inside = [(t, v) for t, v in _points(series.get(leg.get("card")))
                  if start <= t <= end]
        if len(inside) < 2:
            legs.append({**leg, "exit": None, "return_pct": None,
                         "why": "no index inside the window"})
            covered.append(0.0)
            continue
        span = (inside[-1][0] - inside[0][0]).total_seconds()
        covered.append(min(span / (end - start).total_seconds(), 1.0))
        entry = inside[0][1]
        way = -1.0 if str(leg.get("side")).lower() == "bear" else 1.0
        take, stop = leg.get("tp"), leg.get("sl")
        exit_kind, exit_value, curve = "window", inside[-1][1], []
        for when, value in inside:
            moved = way * (value / entry - 1.0) * 100.0
            curve.append((when, moved))
            if take is not None and moved >= float(take):
                exit_kind, exit_value = "tp", value
                break
            if stop is not None and moved <= float(stop):
                exit_kind, exit_value = "sl", value
                break
        legs.append({**leg, "exit": exit_kind, "entry_index": entry,
                     "exit_index": exit_value,
                     "return_pct": way * (exit_value / entry - 1.0) * 100.0,
                     "curve": curve})

    coverage = min(covered) if covered else 0.0
    scored = [leg for leg in legs if leg.get("return_pct") is not None]
    if not scored or coverage < COVERAGE_FLOOR:
        return {"verdict": "inconclusive", "legs": legs, "coverage": coverage,
                "why": (f"the index covers {coverage * 100:.0f}% of the window, "
                        f"under the {COVERAGE_FLOOR * 100:.0f}% a verdict needs "
                        f"-- a gap is not a loss"),
                "formula": formula_fingerprint()}

    weight = sum(float(leg.get("share") or 1.0) for leg in scored) or 1.0
    ret = sum(float(leg.get("share") or 1.0) * leg["return_pct"]
              for leg in scored) / weight

    # The portfolio's own path, so the drawdown is the one a holder felt: each
    # leg holds its last value between its own points, and a leg that exited
    # holds its exit.
    stamps = sorted({when for leg in scored for when, _ in leg["curve"]})
    running, drawdown, peak = [], 0.0, None
    for stamp in stamps:
        total = 0.0
        for leg in scored:
            moved = [m for w, m in leg["curve"] if w <= stamp]
            total += float(leg.get("share") or 1.0) * (
                moved[-1] if moved else 0.0)
        value = total / weight
        running.append(value)
        peak = value if peak is None else max(peak, value)
        drawdown = max(drawdown, peak - value)

    benchmark = None
    card = acceptance.get("benchmark_card")
    if card:
        marks = [(t, v) for t, v in _points(series.get(card))
                 if start <= t <= end]
        if len(marks) >= 2:
            benchmark = (marks[-1][1] / marks[0][1] - 1.0) * 100.0

    stop_pct = float(acceptance.get("stop_pct") or 0) or None
    if ret <= 0:
        why, ok = f"it returned {ret:+.2f}%", False
    elif benchmark is not None and ret <= benchmark:
        why, ok = (f"it returned {ret:+.2f}% against the benchmark's "
                   f"{benchmark:+.2f}%"), False
    elif stop_pct is not None and drawdown > stop_pct:
        why, ok = (f"its drawdown reached {drawdown:.2f}%, past the "
                   f"{stop_pct:.2f}% it was accepted with"), False
    else:
        why, ok = (f"it returned {ret:+.2f}% inside a {drawdown:.2f}% drawdown"
                   + (f", against the benchmark's {benchmark:+.2f}%"
                      if benchmark is not None else "")), True

    return {"verdict": "survived" if ok else "refuted", "why": why,
            "return_pct": ret, "max_drawdown_pct": drawdown,
            "benchmark_pct": benchmark, "coverage": coverage,
            "legs": [{k: v for k, v in leg.items() if k != "curve"}
                     for leg in legs],
            "window": {"from": start.isoformat(), "to": end.isoformat()},
            "formula": formula_fingerprint()}


def rank(rows: list[dict]) -> list[dict]:
    """Their strategy concepts, best risk-adjusted first.

    Sharpe before return, and a missing number is missing -- not zero. A
    strategy with no backtest rows is exactly what `get_strategy_returns`
    promises to say ("a strategy with no runs returns a note, never a
    fabricated number"), and sorting those to the bottom as if they had scored
    zero would be us fabricating it instead.
    """
    scored, unscored = [], []
    for row in rows:
        sharpe = row.get("sharpe")
        if isinstance(sharpe, (int, float)):
            scored.append(row)
        else:
            unscored.append({**row, "unranked": "no Sharpe in their answer"})
    scored.sort(key=lambda r: (-float(r["sharpe"]),
                               float(r.get("max_drawdown") or 0)))
    return scored + unscored
