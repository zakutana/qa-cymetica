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
from datetime import datetime, timezone
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


def open_session(mode: str = "session", note: str | None = None) -> dict:
    """Start one, and say which kind it is: a session, or a night."""
    rows = load()
    record = {"type": "session", "state": "open", "at": _now(),
              "session": _next_id(rows), "mode": mode}
    if note:
        record["note"] = note
    return _append(record)


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
    return _append({"type": "session", "state": "closed", "at": _now(),
                    "session": session, "lessons": list(lessons),
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


def may_ask(asked: int, pass_running: bool) -> tuple[bool, str]:
    """Whether another question may go to Nexus now.

    Not while a deep pass is running. That pass verifies #85 (the newest answer
    that names a tool), #86 (the last five questions) and #87 (the newest
    trade) -- so a question asked mid-run changes the subject the pass is
    measuring, and the verdict it sends the vendor is then about something
    else. Ours to wait; theirs to receive one true answer.
    """
    if pass_running:
        return False, ("a deep pass is running: it is verifying #85, #86 and "
                       "#87 over these very answers. Ask after it finishes")
    cap = CAPS["questions_per_session"]
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
