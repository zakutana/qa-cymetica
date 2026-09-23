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
KINDS = ("session", "truth", "surface", "cycle", "n_eff", "tournament",
         "gate", "tick", "entry", "resolved", "fomo_reading")
MAX_LESSONS = 3
MAX_NEXT = 8
ID = re.compile(r"^LAB-(\d{4})$")

# What the laboratory may spend, per ROLLING DAY. Nexus's own guide is explicit
# that an open-ended night "drifts, burns calls, and gives you no way to judge
# what it found" -- so there is a ceiling, and a pace under it (NIGHT below).
#
# Per session until 2026-09-19: eight questions and three rooms a session,
# twelve questions a night. Then the operator made the laboratory a /loop that
# ticks every twenty minutes all day, and a per-session count either stopped
# it before lunch or reset whenever a session opened -- five rooms in six days
# against their fifty. The two numbers below are ours, not theirs: fifty
# running over a five-day window is ten new rooms a day, and a question an
# hour on average keeps a question in flight for most of the day without
# spending one on every tick.
CAPS = {
    "questions_per_day": 24,
    # 10 -> 25 on 2026-09-21, with one room per card. Ten was fifty over a
    # five-day window, and it never bound -- eight rooms in eleven days, held
    # back by one room per ANSWER. It is a ceiling, not a quota: the operator,
    # on the plan, "pořád by room měl vzniknout jen na základě slibné teorie
    # nebo backtestu" -- the gate is the bar.
    "new_rooms_per_day": 25,
    # [operator 2026-09-12] *"musime testvoat aspon 50 strategii najednou"*.
    # Raised from 6 at 15% on 2026-09-12, and their reason is right for a
    # reason they did not give: a verdict takes a five-to-seven-day window, so
    # six at a time is six verdicts a week and knowing which of Nexus's ideas
    # pay needs dozens. The count is the weaker brake -- fifty at 2% is the
    # whole book -- so what actually holds is the ceiling on what may be
    # deployed at once: always dry powder, and one bad night cannot take it all.
    # 50 -> 125 on 2026-09-21: 25 a day over the five-day window. "Aspoň 50" is
    # a floor, so this keeps it; the per-room stake follows by itself
    # (total_exposure / running_experiments, 0.48% of the book) under the same
    # 60% ceiling, and share_of_free_cash stays the operator's 2%.
    "running_experiments": 125,
    "share_of_free_cash": 0.02,
    "total_exposure": 0.60,
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
                 until: str | None = None, day: str | None = None) -> dict:
    """Start one, and say which kind it is: a session, a night, or a loop's day.

    A night carries the hour it will end. Without it an open night looks
    exactly like a session somebody forgot to close, and the reminder would nag
    at every session start for the fourteen hours the thing is doing precisely
    what it was told. A loop's session carries the UTC DAY it stands for: a
    loop has no last tick to close it with, so the next day's first tick does.
    """
    rows = load()
    record = {"type": "session", "state": "open", "at": _now(),
              "session": _next_id(rows), "mode": mode}
    if note:
        record["note"] = note
    if until:
        record["until"] = until
    if day:
        record["day"] = day
    return _append(record)


ENTRY_KINDS = ("log", "lesson", "next")


def note_entry(session: str, text: str, kind: str = "log") -> dict:
    """One line of the laboratory's diary, in whoever-ran-the-tick's words.

    [operator 2026-09-19] asked for a laboratory that keeps a diary -- where it
    stopped, what it has tested. The counts are written by the tick itself;
    this is the other half, the judgement: what a question was for, what an
    answer changed, what to try next. `lesson` and `next` are what the day's
    close carries forward, at most three and eight of them.
    """
    if kind not in ENTRY_KINDS:
        raise LabError(f"an entry is one of {', '.join(ENTRY_KINDS)}, not {kind!r}")
    words = " ".join(str(text or "").split())
    if not words:
        raise LabError("an empty diary line says nothing")
    return _append({"type": "entry", "at": _now(), "session": session,
                    "kind": kind, "text": words[:600]})


def entries(rows: list[dict] | None = None, session: str | None = None,
            kind: str | None = None) -> list[dict]:
    rows = load() if rows is None else rows
    return [r for r in rows if r.get("type") == "entry"
            and (session is None or r.get("session") == session)
            and (kind is None or r.get("kind") == kind)]


def note_tick(said: dict) -> dict:
    """What one loop tick did, in counts -- the half of the diary no judgement
    is needed for, so the next tick can read where this one stopped."""
    return _append({"type": "tick", "at": _now(), **said})


def note_fomo_reading(said: dict) -> dict:
    """Hot against control, as `fomo_watch.py report` computed it -- written
    every few hours, so whether the radar predicts a pump can be watched
    moving rather than recomputed from a diary nobody keeps."""
    return _append({"type": "fomo_reading", "at": _now(), **said})


def last_fomo_reading(rows: list[dict] | None = None) -> dict | None:
    rows = load() if rows is None else rows
    seen = [r for r in rows if r.get("type") == "fomo_reading"]
    return seen[-1] if seen else None


def note_hot_reading(said: dict) -> dict:
    """The Hot headlines study as `hot_watch.py report` computed it. Its own
    diary is not snapshotted, so this line is the copy that outlives the disk."""
    return _append({"type": "hot_reading", "at": _now(), **said})


def last_hot_reading(rows: list[dict] | None = None) -> dict | None:
    rows = load() if rows is None else rows
    seen = [r for r in rows if r.get("type") == "hot_reading"]
    return seen[-1] if seen else None


def last_tick(rows: list[dict] | None = None) -> dict | None:
    rows = load() if rows is None else rows
    seen = [r for r in rows if r.get("type") == "tick"]
    return seen[-1] if seen else None


def note_resolved(found: list[dict], rows: list[dict] | None = None) -> list[dict]:
    """Positions that resolved on their own, each written ONCE.

    `resolved_without_us` only reports; before 2026-09-19 nothing wrote what it
    found, so the same position was printed on every status and counted in no
    ledger of what the laboratory earned.
    """
    rows = load() if rows is None else rows
    seen = {str(r.get("position_id")) for r in rows if r.get("type") == "resolved"}
    written = []
    for row in found or []:
        position = str(row.get("position_id") or "")
        if not position or position in seen:
            continue
        seen.add(position)
        written.append(_append({"type": "resolved", "at": _now(), **row}))
    return written


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


def note_n_eff(said: dict) -> dict:
    """One reading of `n_eff` over the real open book, so the reminder can
    read it back without touching the network itself."""
    return _append({"type": "n_eff", "at": _now(), **said})


def last_n_eff(rows: list[dict] | None = None) -> dict | None:
    rows = load() if rows is None else rows
    seen = [r for r in rows if r.get("type") == "n_eff"]
    return seen[-1] if seen else None


DAY_HOURS = 24


def _within(value, since: datetime) -> bool:
    """Is this row inside the window? An unreadable moment says YES.

    One reader for both caps, because they had the same inverted default in
    two places and a fix to one would have left the other. A moment we cannot
    read is not a moment outside the window -- it is a reading we did not
    take, and on a brake the safe answer is the one that keeps it on.
    """
    when = _at(value)
    return True if when is None else when > since


def asked_within(nexus_rows: list[dict], now: datetime | None = None,
                 hours: float = DAY_HOURS) -> int:
    """Questions put to Nexus in the last `hours`, whoever asked them.

    Counted off the diary rather than off a session, because a session is
    whatever was opened last: `_asked_this_session` read a question at nine
    and a session opened at ten as nothing asked.
    """
    moment = now or datetime.now(timezone.utc)
    since = moment - timedelta(hours=hours)
    # An unreadable stamp COUNTS. `(_at(...) or since) > since` compared false
    # for one, so a row whose moment we cannot read quietly admitted a 25th
    # question -- rule 8 inverted, on the side that spends. `nexus.py record
    # --at` takes the operator's free text straight into the diary, so it
    # needs no bug to produce one.
    return sum(1 for row in nexus_rows
               if row.get("type") == "question"
               and _within(row.get("at"), since))


def rooms_within(room_rows: list[dict], now: datetime | None = None,
                 hours: float = DAY_HOURS) -> int:
    """Strategy rooms opened in the last `hours` -- the day's room count."""
    moment = now or datetime.now(timezone.utc)
    since = moment - timedelta(hours=hours)
    return sum(1 for row in room_rows
               if row.get("type") == "strategy"
               and _within(row.get("at"), since))


def may_ask(asked: int, pass_running: bool) -> tuple[bool, str]:
    """Whether another question may go to Nexus now, given how many went in
    the last twenty-four hours.

    Not while a deep pass is running. That pass verifies #85 (the newest answer
    that names a tool), #86 (the last five questions) and #87 (the newest
    trade) -- so a question asked mid-run changes the subject the pass is
    measuring, and the verdict it sends the vendor is then about something
    else. Ours to wait; theirs to receive one true answer.
    """
    if pass_running:
        return False, ("a deep pass is running: it is verifying #85, #86 and "
                       "#87 over these very answers. Ask after it finishes")
    cap = CAPS["questions_per_day"]
    if asked >= cap:
        return False, (f"{asked} questions in the last 24 h, and the cap is "
                       f"{cap}: an open-ended loop drifts and burns calls, "
                       f"which is Cymetica's own warning about the night")
    return True, ""


def may_ask_now(nexus_rows: list[dict], now: datetime | None = None,
                ignore_backoff: bool = False) -> tuple[bool, str]:
    """The pace under the cap, for a question asked by hand or by a loop tick.

    The night held these three in its own loop state; a tick is a fresh
    process every twenty minutes, so they are read off the diary instead:

      * one question in flight at a time -- a second one splits the pick-up
        and Nexus answers the older context;
      * twenty minutes since the last one, the night's own floor;
      * the wait their own failure asked for (`backoff_until`).
    """
    moment = now or datetime.now(timezone.utc)
    # Their bound before our pace: six outstanding of our own (REPLY-0037),
    # over the day they keep a queued job. Not a pace, so --now does not lift
    # it -- a seventh would be refused by them, and asking is what spends the
    # slot they reserved.
    held = outstanding(nexus_rows, moment, within_hours=POLLABLE_HOURS)
    if len(held) >= OUTSTANDING_BOUND:
        return False, (f"{len(held)} of our questions are outstanding on their "
                       f"side and their reserved lane bounds us at "
                       f"{OUTSTANDING_BOUND}: {', '.join(held[-3:])} first")
    # In flight for PACING only while it is recent. A job their side lost, or
    # one whose every poll errors, is still polled for a late answer over
    # POLLABLE_HOURS -- but it held the lane for that whole day, sync door
    # included (R04, deep pass of 2026-09-19).
    waiting = outstanding(nexus_rows, moment, within_hours=IN_FLIGHT_HOURS)
    if waiting:
        return False, (f"{waiting[-1]} is still being answered; the next tick "
                       f"picks it up first")
    # The floor runs from the last question their side actually TOOK ON. One
    # they turned away outright -- failed, with a retry_after of their own --
    # spent nothing of theirs, and their wait replaces ours: NEX-0029 was
    # refused "at capacity, retry after 30 s" and our floor then held the
    # same question for eighteen minutes.
    refused = {r.get("id") for r in nexus_rows
               if r.get("type") == "gave_up"
               and str(r.get("status") or "").startswith("failed")
               and isinstance(r.get("retry_after_s"), (int, float))}
    # And one refused at the door, before any job existed (NEX-0074, their
    # wording filter): not taken on either, and the filter's own hint is to
    # ask again in different words. The hourly count below still has it.
    refused |= {r.get("id") for r in nexus_rows
                if r.get("type") == "question"
                and r.get("accepted") is False and not r.get("job_id")}
    # Not a question the operator asked them in a browser. `nexus.py record`
    # writes one so the answer survives a /clear, and the floor read it as
    # traffic of ours: recording at 14:00 stopped the laboratory asking
    # anything until 14:20, for a question that never used their door. The
    # floor is about THEIR side -- one in flight so the pick-up is not split,
    # and a pace their limit can carry -- and neither holds for a
    # conversation that happened on their website. The day's CAP still counts
    # it, deliberately: that one is about how much of their time we take.
    stamps = [_at(r.get("at")) for r in nexus_rows
              if r.get("type") == "question" and r.get("id") not in refused
              and r.get("lane") != "operator"]
    # Every ask inside the last hour, refused or not: a refusal turns out to
    # cost them something, which is what their own hourly limit says.
    hour_ago = moment - timedelta(hours=1)
    recent = [s for s in (_at(r.get("at")) for r in nexus_rows
                          if r.get("type") == "question"
                          and r.get("lane") != "operator")
              if s is not None and s > hour_ago]
    if len(recent) >= ASKS_PER_HOUR:
        return False, (f"{len(recent)} question(s) went in the last hour and "
                       f"the cap is {ASKS_PER_HOUR}: their deep lane has an "
                       f"hourly limit of its own and a refusal counts against "
                       f"it")

    last = max((s for s in stamps if s is not None), default=None)
    floor = NIGHT["ask_seconds"]
    if last is not None and (moment - last).total_seconds() < floor:
        minutes = int((moment - last).total_seconds() // 60)
        return False, (f"the last question went {minutes} min ago and the "
                       f"floor is {floor // 60}")
    # `ignore_backoff` is for the SHALLOW lane: the wait their deep lane
    # asked for is about the deep lane (REPLY-0018: a shared capacity window
    # on deep investigations), and their own advice is to ask the sync door
    # meanwhile. The pace above still holds on it.
    hold = None if ignore_backoff else backoff_until(nexus_rows, moment)
    if hold is not None:
        return False, (f"their side failed and asked for a wait until "
                       f"{hold.isoformat(timespec='minutes')}")
    return True, ""


def affordable(usdc: float, free_cash: float | None, running: int,
               deployed: float = 0.0) -> tuple[bool, str]:
    """Whether one experiment may take this much, and how much may be out at once.

    A share of what is FREE, not of the bankroll: the book already knows what
    is deployed. An unreadable book refuses -- rule 8, and the same refusal
    paper.py makes when it cannot read what is in the bots.

    The total is the brake that matters now that fifty may run. Fifty at 2% is
    the whole book, so without a ceiling the count would be no limit at all.
    It is measured against the BOOK -- free plus what is out -- because that is
    what exposure means. Against the remainder it would walk down as we deploy
    and bind at 37.5%, under a number written as 60%.
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
    limit = CAPS["total_exposure"]
    book = free_cash + deployed
    if (deployed + usdc) > book * limit:
        return False, (f"{deployed:.0f} is already out and {usdc:.0f} more "
                       f"would pass {limit * 100:.0f}% of the {book:.0f} book "
                       f"(free plus deployed). There is always dry powder, so "
                       f"one bad night cannot take the book")
    return True, (f"{usdc:.0f} of {free_cash:.0f} free, {running} running, "
                  f"{deployed + usdc:.0f} out of the {book * limit:.0f} "
                  f"allowed on a {book:.0f} book")


POLLABLE_HOURS = 24
# How long one question may hold the next one back. Their deep investigations
# take one to five minutes by their own contract and queue when the lane is
# full (REPLY-0019); two hours is far past both, and short of a lost day.
IN_FLIGHT_HOURS = 2
# How many jobs of ours may be outstanding on their side at once. Theirs, not
# ours: REPLY-0037 reserves a lane slot for this agent and bounds it at six.
# Counted over POLLABLE_HOURS because that is the window the same answer says
# they now hold a queued job for -- the pacing window above is shorter on
# purpose and no longer covers what their side still has.
OUTSTANDING_BOUND = 6
# Deep questions we may ASK in a rolling hour, refused ones included. Theirs
# is undocumented: on 2026-09-21 at 01:25 UTC the fourth question of an hour
# came back "Hourly deep-answer limit reached", after three refusals had each
# reset our twenty-minute floor to their own 30-second retry_after. Three is
# the twenty-minute cadence the loop actually runs at, and the cadence
# REPLY-0037 said would never reach a bound.
ASKS_PER_HOUR = 3


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
    asked, last = [], {}
    for row in nexus_rows:
        kind, ident = row.get("type"), str(row.get("id") or "")
        if not ident:
            continue
        if kind == "question":
            # Turned away before a job existed -- `nexus.py ask` writes
            # `accepted: false` with no job_id when their side refuses the
            # call itself (NEX-0074, the wording filter). There is nothing to
            # poll and nothing to wait for; counted in flight, it held the
            # lane for IN_FLIGHT_HOURS. `accepted` absent is an older row and
            # stays as it was.
            if row.get("accepted") is False and not row.get("job_id"):
                continue
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
            last[ident] = row

    def finished(ident: str) -> bool:
        # REPLY-0019: at capacity their deep lane QUEUES a job and runs it
        # when the window frees. Our give-up at fifteen minutes stays on the
        # record -- #86 measures their published window with it -- but a job
        # still queued or running then is theirs still working, and its
        # answer has to be picked up when it lands.
        row = last.get(ident)
        if row is None:
            return False
        if row.get("type") == "gave_up":
            return str(row.get("status") or "") not in STILL_WORKING
        return True
    return [ident for ident in asked if not finished(ident)]


STILL_WORKING = frozenset({"running", "queued", "pending"})


# --- the night -------------------------------------------------------------
#
# [operator 2026-09-12] No scheduler, ever: they start everything themselves.
# A night is therefore one process with an end written into it, not a task that
# comes back tomorrow -- and these numbers are what keep it from behaving like
# one. Their own guide is the source of the pace: an open-ended loop "drifts,
# burns calls, and gives you no way to judge what it found".
NIGHT = {
    "tick_seconds": 120,          # how often it looks at the clock
    "cycle_seconds": 1800,        # pick answers up, sample, compare the catalogue
    "truth_seconds": 6 * 3600,    # re-rank their backtests when the snapshot ages
    # Two clocks, because a backtest is free and a question is not. The search
    # runs on EVERY tick, bounded by their 30/min and by nothing of ours:
    # [operator 2026-09-12] *"celou noc budete delat backtesty nonstop"*, said
    # about a night that ran them twice. The question floor came down from two
    # hours to twenty minutes at the same time -- their own `retry_after` sets
    # the pace when they are down, and when they are up we should not be
    # throttling ourselves on top of a cap that already binds.
    "search_batch": 30,           # backtests per tick; their limit per minute
    "ask_seconds": 20 * 60,
    # And when their side refuses without saying when to come back, the wait
    # DOUBLES per refusal in the streak, up to this. Flat is wrong both ways:
    # twenty minutes spends a whole night's cap inside an outage like the one
    # of 2026-09-12 (six refusals over seventeen hours), and two hours
    # throttles a Nexus that is merely having a moment.
    "backoff_max_seconds": 4 * 3600,
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
    failed, answered, streak = None, None, 0
    for row in nexus_rows:
        # The wait is the DEEP lane's (REPLY-0018: a shared capacity window on
        # deep investigations). The sync door failing or answering says
        # nothing about it either way.
        if row.get("lane") == "shallow":
            continue
        when = _at(row.get("at"))
        if when is None:
            continue
        if row.get("type") == "gave_up":
            failed = (when, row)
            streak += 1
        elif row.get("type") == "answer":
            answered, streak = when, 0
    if failed is None or (answered is not None and answered > failed[0]):
        return None
    seconds = failed[1].get("retry_after_s")
    if isinstance(seconds, (int, float)) and seconds > 0:
        wait = float(seconds)
    else:
        # Theirs first, always. Ours only when they did not say, and then it
        # doubles per refusal so a long outage is waited out rather than
        # hammered through a night's whole question budget.
        wait = min(NIGHT["ask_seconds"] * (2 ** max(streak - 1, 0)),
                   NIGHT["backoff_max_seconds"])
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
    # The search is on its own clock -- every tick, while there is anything
    # left to walk -- because a backtest is a read that costs nothing but their
    # rate limit. A backoff their side asked for is about QUESTIONS; it may not
    # stop us reading.
    if state.get("pending"):
        do.append("search")
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
    elif state.get("asked", 0) >= CAPS["questions_per_day"]:
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


def _ref(leg: dict):
    """The key a leg's series is under: its `ref` -- a card's id, a bot's
    instance, a fund's symbol -- or, on a leg from before 2026-09-22, its
    `card`, which is the same id. So a card is judged on the same series,
    to the same number, whichever way its leg was written."""
    return leg.get("ref") or leg.get("card")


def bot_series(samples: list[dict], instance: str, funded: float | None
               ) -> list[dict]:
    """A paper bot's own index, from the sampler's rows: 100 at what went in,
    moved by what it made -- `100 * (1 + total_profit_usdc / funded)`.

    Not `balance_usdc` alone, although that is what the sampler reads off
    their my-clones row: since their fix of #94 a stake is debited from it
    when the bot OPENS a position, so a bot with 40% in a trade reads -40%
    and would be refuted past its stop on the first sample. What went in
    plus what it made does not depend on how they book a stake -- the
    reading `scripts/paper.py::capital_in_bots` already makes of the same
    fields. No funding on record, no series: a bot we cannot size is not
    judged at all.
    """
    try:
        base = float(funded or 0)
    except (TypeError, ValueError):
        return []
    if base <= 0:
        return []
    out = []
    for row in samples or []:
        if (not isinstance(row, dict) or row.get("kind") != "bot"
                or row.get("instance_id") != instance):
            continue
        try:
            profit = float(row.get("total_profit_usdc"))
        except (TypeError, ValueError):
            continue
        if row.get("at"):
            out.append({"t": row["at"], "index": 100.0 * (1.0 + profit / base)})
    return out


def fund_series(points) -> list[dict]:
    """Their fund history, `[{t, v}]` from get_fund_history, in the shape the
    verdict reads a card's index in."""
    out = []
    for point in points or []:
        if isinstance(point, dict) and point.get("t") and isinstance(
                point.get("v"), (int, float)) and not isinstance(point["v"], bool):
            out.append({"t": point["t"], "index": float(point["v"])})
    return out


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
        # Both halves of the formula since 2026-09-21: a verdict can now be
        # settled inside the window by _early, and a change there is a change
        # to what a verdict means.
        source = inspect.getsource(verdict) + inspect.getsource(_early)
    except (OSError, TypeError):  # pragma: no cover -- frozen or stripped
        return "unknown"
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:12]


def _early(acceptance: dict, series: dict, start, moment) -> dict | None:
    """A verdict that is already settled inside the window, or None.

    2026-09-21, the operator: rooms that fail are dropped rather than carried
    to the end of a five-day window. Two things refute one early, both of them
    crossings we have SEEN on their own index, so neither needs the coverage a
    closed window does: the portfolio's drawdown going past the stop it was
    accepted with, or every leg out at its own take-profit or stop with the
    total at or under zero. Nothing survives early -- that is the close's to
    call. No history, no early verdict -- `verdicts()` asks with an empty
    series first, and that must stay "open".
    """
    legs = []
    for leg in acceptance.get("legs") or []:
        inside = [(t, v) for t, v in _points(series.get(_ref(leg)))
                  if start <= t <= moment]
        if len(inside) < 2:
            return None
        entry = inside[0][1]
        way = -1.0 if str(leg.get("side")).lower() == "bear" else 1.0
        take, stop = leg.get("tp"), leg.get("sl")
        exit_kind, curve = None, []
        for when, value in inside:
            moved = way * (value / entry - 1.0) * 100.0
            curve.append((when, moved))
            if take is not None and moved >= float(take):
                exit_kind = "tp"
                break
            if stop is not None and moved <= float(stop):
                exit_kind = "sl"
                break
        legs.append({**leg, "exit": exit_kind, "curve": curve,
                     "return_pct": curve[-1][1]})
    if not legs:
        return None

    weight = sum(float(leg.get("share") or 1.0) for leg in legs) or 1.0
    stamps = sorted({when for leg in legs for when, _ in leg["curve"]})
    peak, drawdown, value = None, 0.0, 0.0
    for stamp in stamps:
        value = sum(float(leg.get("share") or 1.0)
                    * ([m for w, m in leg["curve"] if w <= stamp] or [0.0])[-1]
                    for leg in legs) / weight
        peak = value if peak is None else max(peak, value)
        drawdown = max(drawdown, peak - value)
    clean = [{k: v for k, v in leg.items() if k != "curve"} for leg in legs]

    stop_pct = float(acceptance.get("stop_pct") or 0) or None
    if stop_pct is not None and drawdown > stop_pct:
        return {"verdict": "refuted", "return_pct": value,
                "max_drawdown_pct": drawdown, "legs": clean,
                "why": (f"its drawdown reached {drawdown:.2f}%, past the "
                        f"{stop_pct:.2f}% it was accepted with, before the "
                        f"window closed")}
    # Only a failure settles early. A win cannot: the benchmark keeps moving
    # after the last exit, and the close measures it over the whole window
    # (deep pass of 2026-09-21, two rounds of rule-change readers). A net loss
    # with every leg out is frozen, and the close refutes it the same way.
    if all(leg["exit"] for leg in legs) and value <= 0:
        return {"verdict": "refuted", "return_pct": value,
                "max_drawdown_pct": drawdown, "legs": clean,
                "why": (f"every leg reached its exit before the window "
                        f"closed, at {value:+.2f}%")}
    return None


def _inside(points, start, end):
    """A leg's points inside [start, end], with the value it held at `start`.

    They record the index when it moves. A last point before the window whose
    value the first point inside repeats is the value the whole stretch held
    (SPCX: 85 h, 99.870362 at both ends), so it stands at `start`. A value
    that moved across the gap moved at a time nobody knows, and stays out.
    """
    inside = [(t, v) for t, v in points if start <= t <= end]
    before = [(t, v) for t, v in points if t < start]
    if inside and before and inside[0][0] > start and before[-1][1] == inside[0][1]:
        inside.insert(0, (start, before[-1][1]))
    return inside


def verdict(acceptance: dict, series: dict, now, closes: dict | None = None
            ) -> dict:
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
        early = _early(acceptance, series, start, moment)
        if early is not None:
            return {**early, "early": True, "closes_at": end.isoformat(),
                    "formula": formula_fingerprint()}
        return {"verdict": "open", "why": f"the window closes {end.isoformat()}",
                "closes_at": end.isoformat(), "coverage": None,
                "formula": formula_fingerprint()}

    legs, covered, judged = [], [], []
    for leg in acceptance.get("legs") or []:
        # A card that closes inside the window is judged up to its close:
        # after it their index stops, and that is the end, not a gap.
        closed = _at((closes or {}).get(_ref(leg)))
        stop_at = min(end, closed) if closed and closed > start else end
        judged.append(stop_at)
        inside = _inside(_points(series.get(_ref(leg))), start, stop_at)
        if len(inside) < 2:
            legs.append({**leg, "exit": None, "return_pct": None,
                         "why": "no index inside the window"})
            covered.append(0.0)
            continue
        span = (inside[-1][0] - inside[0][0]).total_seconds()
        covered.append(min(span / (stop_at - start).total_seconds(), 1.0))
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
        # `curve` is a list of (datetime, float) points, kept only to compute
        # the portfolio drawdown below -- a leg that scored before overall
        # coverage came up short still carries one here, and record_verdict()
        # json.dumps this dict straight into the diary. Found live 2026-09-18
        # when STR-0003's verdict crashed on exactly this branch.
        return {"verdict": "inconclusive",
                "legs": [{k: v for k, v in leg.items() if k != "curve"}
                        for leg in legs],
                "coverage": coverage,
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
        # Over the stretch the legs were judged on, not the whole window: a
        # leg that closed on day two is not measured against five days of BTC.
        until = max(judged) if judged else end
        marks = [(t, v) for t, v in _points(series.get(card))
                 if start <= t <= until]
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


def _pearson(a: list[float], b: list[float]) -> float | None:
    """None when the correlation is undefined -- too short, or either series
    is flat -- rather than a fabricated 0.0 or 1.0. A flat series (a card that
    has not moved) has no variance to correlate against anything."""
    n = min(len(a), len(b))
    if n < 3:
        return None
    a, b = a[:n], b[:n]
    ma, mb = sum(a) / n, sum(b) / n
    cov = sum((x - ma) * (y - mb) for x, y in zip(a, b))
    va = sum((x - ma) ** 2 for x in a)
    vb = sum((y - mb) ** 2 for y in b)
    if va <= 0 or vb <= 0:
        return None
    return cov / (va * vb) ** 0.5


def n_eff(returns: dict[str, list[float]]) -> dict:
    """The effective number of independent bets in the open book.

        n_eff = N / (1 + (N-1)*rho)

    Nexus's own leading indicator, offered unprompted on 2026-09-12 when asked
    what breaks its own top-ranked strategy: average pairwise correlation of
    the open book as a warning that arrives BEFORE the drawdown does -- "when
    average pairwise correlation crosses ~0.6-0.7 the breadth collapses". It
    is the only thing Nexus has told us about risk in the whole book rather
    than in one card, and until now nothing built it.

    `returns` is one aligned series of period returns per open position,
    however the caller built the alignment -- this function does not fetch
    anything and does not know what a "room" or a "card" is, so it can be
    tested without a network and reused if the book is ever priced some other
    way.

    Fewer than two positions, or too few pairs to correlate (a flat series, or
    series too short), is inconclusive -- never a fabricated 1.0, and never
    the crash a real book would eventually cause. A gap here is the same kind
    of gap `qa.rooms.verdict` already refuses to read as a loss.
    """
    names = sorted(returns)
    if len(names) < 2:
        return {"verdict": "inconclusive", "why": "fewer than two open positions"}

    correlations = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            rho_ab = _pearson(returns[a], returns[b])
            if rho_ab is not None:
                correlations.append(rho_ab)

    if not correlations:
        return {"verdict": "inconclusive",
                "why": "every pair was too short or too flat to correlate"}

    n = len(names)
    rho = sum(correlations) / len(correlations)
    denom = 1 + (n - 1) * rho
    if denom <= 0:
        # Only reachable with a strongly negative average correlation, which
        # is the opposite of the risk this indicator watches for -- report the
        # book as maximally diversified rather than divide by zero or go
        # negative.
        return {"n": n, "rho": rho, "n_eff": float(n)}
    return {"n": n, "rho": rho, "n_eff": n / denom}


CARD_ID = re.compile(
    r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b")


def proposed_cards(text: str, known) -> dict[str, list[str]]:
    """The cards an answer names, split by whether they actually exist.

    Pure, and deliberately dull: it reads ids, it does not read intent. An
    answer that names no card proposes nothing to buy -- NEX-0018 and NEX-0026
    both named none, and NEX-0026 was the most useful answer Nexus has given
    us. "It said something wise" is not "it told us to buy something".

    `known` is the set of cards we have actually seen come back from their API.
    Nexus naming one is not evidence it exists: #91 is a card it invented, with
    a live-looking index and 90-day metrics, sitting beside two real ones whose
    numbers were right to six decimals. So an id it names and we have never
    seen is reported, never acted on.
    """
    seen: list[str] = []
    for found in CARD_ID.findall(str(text or "").lower()):
        if found not in seen:
            seen.append(found)
    have = {str(k).lower() for k in (known or ())}
    return {"actionable": [c for c in seen if c in have],
            "unknown": [c for c in seen if c not in have]}


_RULED_OUT = re.compile(
    r"\b(are out|is out|ruled out|rejected|disqualified|excluded|withheld|"
    r"not (?:a )?(?:long|pick|buy|fit|selected)|skip|avoid|pass on|"
    # NEX-0073: "**Why it edges the alternatives:** Fibonacci Phoenix ...".
    r"alternatives?|runners?-up|instead of)\b",
    re.I)
_BULLET = re.compile(r"^\s*(?:[-*•]|\d+[.)])\s")
_MD_HEADING = re.compile(r"^\s*#{1,6}\s")
# A qualifier in brackets describes the thing, not a verdict on it: NEX-0086's
# pick read "**FUND — X — mark/watch (... so this is a watch, not a buy)**".
_BRACKETED = re.compile(r"\([^()]*\)")


def ruled_out_cards(text: str) -> set[str]:
    """Cards the answer names only to rule them out.

    NEX-0064 recommended one card and put three under "**Why the other three
    ... are out:**"; reading every UUID as a proposal opened rooms on two of
    them. A heading -- a line that is not a bullet -- whose words rule out
    starts a section; the next heading ends it. A card every mention of which
    sits inside such a section is ruled out. One mention anywhere else, as in
    "open the position with card_id ...", keeps it a proposal.
    """
    return _ruled_out(str(text or "").lower(), CARD_ID.findall)


def _ruled_out(text: str, find) -> set[str]:
    """The section reading behind ruled_out_cards, for anything `find` picks
    out of a line -- cards by id, bots by species name, funds by symbol.

    A markdown heading ("# BOTS — RULED OUT") that rules out holds everything
    to the next markdown heading, prose included: NEX-0086 named six bots in
    a paragraph under one, and the paragraph closed the section.
    """
    inside = held = False
    mentioned: dict[str, bool] = {}
    for line in str(text or "").split("\n"):
        ruling = inside
        says = _RULED_OUT.search(_BRACKETED.sub("", line))
        if _MD_HEADING.match(line):
            ruling = inside = held = bool(says)
        elif line.strip() and not _BULLET.match(line) and not held:
            # A heading that rules out opens a section; one that names a card
            # without ruling it out ("**`9f9433ef`** -- NEAR ...") closes it.
            # A ruling line that names its cards itself ("Passed but not
            # selected: `849a695b`") rules those out and opens one too.
            ruling = inside = bool(says)
        for found in find(line):
            mentioned[found] = mentioned.get(found, False) or not ruling
    return {name for name, elsewhere in mentioned.items() if not elsewhere}


def _whole_names(names, flags: int, edge: str):
    """A finder for exact catalogue names in a line, longest first, each
    span taken once -- so a name inside a longer one ("MACD Hunter" in a
    hypothetical "MACD Hunter Pro") is not a second mention."""
    patterns = [(name, re.compile(rf"(?<![{edge}]){re.escape(name)}(?![{edge}])",
                                  flags))
                for name in sorted({str(n) for n in names if n}, key=len,
                                   reverse=True)]

    def find(line: str) -> list[str]:
        spans: list[tuple[int, int, str]] = []
        for name, pattern in patterns:
            for hit in pattern.finditer(line):
                if any(a < hit.end() and hit.start() < b for a, b, _ in spans):
                    continue
                spans.append((hit.start(), hit.end(), name))
        return [name for _, _, name in sorted(spans)]
    return find


def _proposed(text: str, find) -> list[str]:
    """Every name `find` sees, first mention first, less those he ruled out."""
    body = str(text or "")
    seen: list[str] = []
    for found in find(body):
        if found not in seen:
            seen.append(found)
    out = _ruled_out(body, find)
    return [name for name in seen if name not in out]


def proposed_bots(text: str, catalogue) -> list[dict]:
    """The bots an answer proposes to clone, as their catalogue rows.

    2026-09-22, the operator: "papírově jde spustit plno věcí kromě karet".
    A bot is named by its species name exactly as GET
    /api/v1/cloned-bots/available lists it -- twenty-two of them on that
    day -- as a whole name (case aside: it is prose), never as part of a
    longer word. A name he mentions only under a heading that rules it out
    is not a proposal, as with a card (NEX-0064). An invented name is
    nothing: there is no row to clone.
    """
    rows = [row for row in catalogue or ()
            if isinstance(row, dict) and row.get("name") and row.get("id")]
    by_name = {str(row["name"]): row for row in rows}
    # The finder hands back the catalogue's own spelling, whatever case the
    # answer wrote it in.
    find = _whole_names(by_name, re.I, "A-Za-z0-9")
    # R02, deep pass of 2026-09-22: a species he measures his pick against
    # ("It beats RSI Sniper and Trend Titan ...") is prose, not a pick. When
    # a line says which he picks, only the bots named on such a line are.
    names = _only_picked(text, find, _proposed(text, find))
    return [by_name[name] for name in names]


def _only_picked(text: str, find, names: list[str]) -> list[str]:
    """When a line says which he picks, only what that line names; otherwise
    every name. Bots since R02 (2026-09-22); funds since NEX-0081 (2026-09-23,
    one pick and five funds ranked below it in prose opened six rooms)."""
    picked = {name for line in str(text or "").split("\n")
              if _PICKED.search(line) for name in find(line)}
    if picked & set(names):
        return [name for name in names if name in picked]
    return names


# A line that says which one he chooses -- "**Pick: MACD Hunter**", "I would
# clone MACD Hunter", "my recommendation".
_PICKED = re.compile(r"\b(pick|my choice|recommend\w*|clone|go with|choose|"
                     r"chosen|select(?:ed)?)\b", re.I)


def proposed_funds(text: str, catalogue) -> list[str]:
    """The funds an answer proposes to watch, by the symbol list_funds gives.

    Exact and case-sensitive: a symbol is a code ("AIB-SPACE"), and prose
    that happens to say "event-card" is not the EVENT-CARD fund. The hyphen
    is part of a symbol, so AIB-AI is not read inside AIB-AIX.
    """
    symbols = [row.get("symbol") if isinstance(row, dict) else row
               for row in catalogue or ()]
    find = _whole_names(symbols, 0, "A-Za-z0-9_-")
    return _only_picked(text, find, _proposed(text, find))


# What "promising" means before a room opens. [operator 2026-09-19] asked for
# the promising ones as rooms, after a proper backtest; the bar itself is ours.
# Their own backtest of the card's basket, AFTER FEES, over the longest window
# it priced whole: positive, and at a Sharpe of at least half. Deliberately a
# low bar -- the room's own window is the real test, and this only keeps out
# what already lost money on their own numbers.
#
# The cost is the LIVE round trip, charged on their gross return: two fills at
# their 0.2% taker fee and 0.5% of slippage each side. Their backtest's own fee
# toggle is 2% + 0.5% per side, 5% a round trip -- "a deliberately conservative
# stress estimate, not the live fee schedule" (REPLY-0047, verified live
# 2026-09-22) -- and gating on it refused cards for a cost no trade pays.
# Sharpe is theirs, on the gross path either way.
GATE = {"periods": (30, 90), "min_sharpe": 0.5, "min_return_pct": 0.0,
        "round_trip_cost_pct": 1.4}


def _net(row: dict) -> float:
    """A reading's return after the live round trip. One their toggle already
    charged (`fees`) is taken as it stands, never charged twice."""
    ret = float(row["r"])
    if row.get("fees"):
        return ret
    return ((1 + ret / 100) * (1 - GATE["round_trip_cost_pct"] / 100) - 1) * 100


def gate(readings: list[dict]) -> dict:
    """Pass, reject, or unbacktestable -- from register rows (p, r, s, d, lost).

    The LONGEST window decides, because a good month inside a bad quarter is
    the quarter's result. A reading that lost a leg priced some other basket
    (`qa.backtests.record`) and is not read at all. Nothing priced whole is
    "unbacktestable" -- the absence of a test, not a failed one.
    """
    whole = [row for row in readings or []
             if isinstance(row, dict) and not row.get("lost")
             and isinstance(row.get("r"), (int, float))
             and isinstance(row.get("s"), (int, float))]
    if not whole:
        return {"verdict": "unbacktestable",
                "why": "their backtest priced no window of this basket whole"}
    longest = max(whole, key=lambda row: float(row.get("p") or 0))
    period, ret, sharpe = int(longest.get("p") or 0), _net(longest), longest["s"]
    said = {"period": period, "return_pct": ret, "sharpe": sharpe,
            "drawdown_pct": longest.get("d")}
    if ret <= GATE["min_return_pct"]:
        return {"verdict": "reject", **said,
                "why": f"{ret:+.1f}% over {period} days after fees"}
    if sharpe < GATE["min_sharpe"]:
        return {"verdict": "reject", **said,
                "why": (f"Sharpe {sharpe:.2f} over {period} days, under "
                        f"{GATE['min_sharpe']}")}
    return {"verdict": "pass", **said,
            "why": f"{ret:+.1f}% at Sharpe {sharpe:.2f} over {period} days "
                   f"after fees"}


def note_gate(origin: str, card: str, said: dict) -> dict:
    """What the launch path decided about one card of one answer -- written
    ONCE, so the next tick reads the decision instead of re-making it, and so
    the next question can tell Nexus how his idea measured."""
    return _append({"type": "gate", "at": _now(), "origin": origin,
                    "card": card, **said})


def gates(rows: list[dict] | None = None) -> dict[tuple[str, str], dict]:
    """(origin, card) -> the decision, newest wins."""
    rows = load() if rows is None else rows
    return {(str(r.get("origin")), str(r.get("card"))): r
            for r in rows if r.get("type") == "gate"}


def resolved_without_us(paper_rows: list[dict],
                        sample_rows: list[dict]) -> list[dict]:
    """A card that resolved on its own -- the last unmeasured link of "bet ->
    resolves -> paid".

    A close WE sent is already measured (#87 debits the buy, TRD-0005 measured
    the return on our own close). What nothing has ever caught is a card
    resolving BY ITSELF: we hold no close intent for it, and the sampler's own
    reading of the position flips from `open` to `closed` with a realised
    P&L. That flip is on this machine already -- the sampler polls their API
    every ten minutes -- it was simply never read against our own book.

    Pure over two already-loaded diaries, so it costs nothing to call from
    `lab.py status` on every run. Newest sample per position wins, the same
    rule `scripts/lab.py::_closed_on_their_side` uses.
    """
    # The close outcome itself often carries no position_id -- only its
    # intent does (`_deployed` in scripts/lab.py reads the same pair the same
    # way) -- so an accepted close is recognised from either row and the id
    # is read from whichever one has it.
    intents = {row["id"]: row for row in paper_rows
              if row.get("type") == "intent" and row.get("id")}
    closed_by_us: set[str] = set()
    for row in paper_rows:
        if row.get("type") != "outcome" or row.get("outcome") != "accepted":
            continue
        intent = intents.get(row.get("id"), {})
        if row.get("kind") == "close" or intent.get("kind") == "close":
            position = row.get("position_id") or intent.get("position_id")
            if position:
                closed_by_us.add(str(position))

    newest: dict[str, dict] = {}
    for row in sample_rows:
        if row.get("kind") != "position":
            continue
        position = row.get("position_id")
        at = str(row.get("at") or "")
        if not isinstance(position, str):
            continue
        if at >= str(newest.get(position, {}).get("at") or ""):
            newest[position] = row

    found = []
    for position, row in sorted(newest.items()):
        if row.get("status") != "closed" or position in closed_by_us:
            continue
        found.append({"position_id": position, "card_id": row.get("card_id"),
                      "realized_pnl_usdc": row.get("realized_pnl_usdc"),
                      "resolved_at": row.get("at")})
    return found


def _money(value) -> float | None:
    """Their amounts arrive as numbers or decimal strings; neither is zero
    when unreadable."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def board(answers: list[dict], notebook: list[dict], room_rows: list[dict],
          paper_rows: list[dict], sample_rows: list[dict]) -> list[dict]:
    """Every Nexus proposal that came to anything, and what it earned.

    [operator 2026-09-19] the goal is the strategies that earn the most, so
    each answer is followed to the money: the stake our paper orders credited
    to it (`intent.nexus.id`), the NEWEST reading of each of those positions --
    realised once closed, unrealised while open -- and the room's status and
    verdict. An answer the gate turned away is on the board with its numbers:
    "what has been tested" was the other half of what they asked for.

    Best earner first, by return on the stake; then the rooms nothing has
    priced yet; then what the gate rejected. Pure over five loaded diaries.
    """
    gates_by: dict[str, list[dict]] = {}
    for row in notebook:
        if row.get("type") == "gate":
            gates_by.setdefault(str(row.get("origin")), []).append(row)
    # One answer may open several rooms (one per card, 2026-09-21); keeping
    # only the last hid a refuted room behind a running one (R05).
    rooms_by: dict[str, list[dict]] = {}
    for r in room_rows:
        if r.get("type") == "strategy":
            rooms_by.setdefault(str(r.get("origin")), []).append(r)
    status, verdicts = {}, {}
    for row in room_rows:
        if row.get("type") == "status":
            status[row.get("room")] = row.get("status")
        elif row.get("type") == "verdict":
            verdicts[row.get("room")] = row

    intents = {r.get("id"): r for r in paper_rows
               if r.get("type") == "intent" and r.get("kind") != "close"}
    held: dict[str, tuple[str, float]] = {}
    for row in paper_rows:
        if (row.get("type") != "outcome" or row.get("outcome") != "accepted"
                or row.get("kind") == "close"):
            continue
        intent = intents.get(row.get("id"))
        if not intent:
            continue
        nexus = intent.get("nexus")
        origin = nexus.get("id") if isinstance(nexus, dict) else nexus
        position = row.get("position_id") or intent.get("position_id")
        stake = _money(intent.get("usdc"))
        if origin and position and stake is not None:
            held[str(position)] = (str(origin), stake)

    newest: dict[str, dict] = {}
    for row in sample_rows:
        if row.get("kind") != "position":
            continue
        position = str(row.get("position_id") or "")
        if position in held and str(row.get("at") or "") >= str(
                newest.get(position, {}).get("at") or ""):
            newest[position] = row

    money: dict[str, dict] = {}
    for position, (origin, stake) in held.items():
        book = money.setdefault(origin, {"stake": 0.0, "pnl": 0.0,
                                         "priced": 0, "positions": 0})
        book["stake"] += stake
        book["positions"] += 1
        reading = newest.get(position) or {}
        pnl = _money(reading.get("realized_pnl_usdc"
                                 if reading.get("status") == "closed"
                                 else "unrealized_pnl_usdc"))
        if pnl is not None:
            book["pnl"] += pnl
            book["priced"] += 1

    out = []
    for answer in answers:
        if answer.get("type") != "answer":
            continue
        origin = str(answer.get("id") or "")
        opened = rooms_by.get(origin) or []
        cash = money.get(origin)
        gated = gates_by.get(origin, [])
        if not (opened or cash or gated):
            continue
        each = [{"id": r.get("id"), "card": r.get("card"),
                 "title": r.get("title"), "status": status.get(r.get("id")),
                 "verdict": (verdicts.get(r.get("id")) or {}).get("verdict"),
                 "verdict_return_pct": (verdicts.get(r.get("id")) or {}).get(
                     "return_pct")} for r in opened]
        room_id = ", ".join(str(r["id"]) for r in each) if each else None
        priced = bool(cash and cash["priced"])
        statuses = sorted({r["status"] for r in each if r["status"]})
        said = [r["verdict"] for r in each if r["verdict"]]
        out.append({
            "origin": origin, "at": answer.get("at"), "room": room_id,
            "rooms": each,
            "title": each[0]["title"] if each else None,
            "status": (statuses[0] if len(statuses) == 1
                       else " / ".join(statuses) if statuses else None),
            "stake_usdc": cash["stake"] if cash else 0.0,
            "pnl_usdc": cash["pnl"] if priced else None,
            "pnl_pct": (cash["pnl"] / cash["stake"] * 100.0
                        if priced and cash["stake"] else None),
            "verdict": (said[0] if len(each) == 1 and said
                        else ", ".join(said) if said else None),
            "verdict_return_pct": (each[0]["verdict_return_pct"]
                                   if len(each) == 1 else None),
            "gates": [{"card": g.get("card"), "verdict": g.get("verdict"),
                       "why": g.get("why")} for g in gated]})

    def order(row):
        if row["pnl_pct"] is not None:
            return (0, -row["pnl_pct"])
        if row["room"]:
            return (1, 0.0)
        return (2, 0.0)
    return sorted(out, key=order)


THEIR_GIVE_UP = re.compile(r"^(failed|running|queued|pending)")


def their_down_streak(rows: list[dict]) -> int:
    """How many of the newest questions in a row THEIR channel failed to
    answer -- duplicated from, not sharing, #86's own live-check classifier
    (`tests/mcp/test_nexus_channel.py::did_not_answer`). That function's
    fingerprint may not move for a reminder-side refactor (rule 5), so this is
    the same distinction over the same two fields, kept independent on
    purpose: their `status: failed`, or a give-up still `running`/`queued`/
    `pending` at their own five-minute ceiling, counts; our own `unread:
    ReadTimeout` or `unknown` does not -- that is a failure of OUR reading,
    not of their channel.

    `scripts/processes.py::_lab_facts` had a looser version of this (any
    give-up counted, ours included) until this function replaced it.
    """
    asked = {r.get("id"): r for r in rows if r.get("type") == "question"}
    finished: dict[str, dict] = {}
    for row in rows:
        if row.get("type") in ("answer", "gave_up") and row.get("id") in asked:
            finished[row["id"]] = row

    streak = 0
    for question_id in reversed(list(asked)):
        row = finished.get(question_id)
        if row is None:
            continue
        if row.get("type") == "answer":
            break
        status = str(row.get("status") or "")
        if THEIR_GIVE_UP.match(status):
            streak += 1
        # else: a give-up on OUR side (a read failure) says nothing about
        # their channel -- skip it and keep reading backward, rather than
        # letting our own flaky read either inflate or erase the streak.
    return streak


def due(now=None, fomo_rows: list[dict] | None = None,
        tournament: dict | None = None, open_findings: int = 0) -> list[dict]:
    """What a loop tick should reach for, most perishable first.

    [operator 2026-09-13] the loop prompt never names a session and never
    changes; the tick works out for itself where it stopped. This is the part
    that can be wrong invisibly -- a tick told nothing is due does nothing,
    which looks exactly like a tick with nothing left to do.

    The order is by what EXPIRES, not by what is interesting:

    1. a memecoin checkpoint past its horizon. The only work here that cannot
       be done later: the price at +6h is gone at +7h, and the hole in the
       measurement is permanent.
    2. a finding waiting on a level-V verification. Their fix is a claim until
       a run says otherwise (rule 7), and the delay is ours, not theirs.
    3. an open tournament round we have not entered. Perishable weekly, and
       free.
    4. the tick. Never urgent, never finished, and the reason a quiet tick
       is still a working tick. It was `search --cap 8` until 2026-09-19,
       which recombined the same seven cards until it ran dry and never once
       asked Nexus; `lab.py tick` is the whole laboratory's step -- answers,
       launches, the search, the verdicts -- and says whether a question may
       go.

    Pure: every input is passed in, so a tick's plan can be tested without a
    diary, a network or a clock.
    """
    from qa import fomo

    moment = now or datetime.now(timezone.utc)
    items: list[dict] = []

    rows = fomo_rows or []
    signals = [r for r in rows if r.get("type") == "signal" and r.get("key")]
    done: dict[str, set[str]] = {}
    for row in rows:
        if row.get("type") == "checkpoint" and row.get("key"):
            done.setdefault(row["key"], set()).add(row.get("horizon", "?"))
    ripe = fomo.due_checkpoints(signals, done, now=moment)
    if ripe:
        items.append({
            "run": "python scripts/fomo_watch.py resolve",
            "why": f"{len(ripe)} memecoin checkpoint(s) past their horizon; "
                   f"the price that answers them is gone in an hour"})

    if open_findings:
        items.append({
            "run": "python scripts/verify.py",
            "why": f"{open_findings} finding(s) with a fix claimed and no "
                   f"level-V run behind it yet (rule 7)"})

    round_ = (tournament or {}).get("round") or {}
    anchor = round_.get("round_anchor")
    entered = any(e.get("round_anchor") == anchor
                  for e in (tournament or {}).get("my_entries") or []
                  if isinstance(e, dict))
    if anchor and round_.get("entries_open") and not entered:
        items.append({
            "run": "python scripts/movers.py status",
            "why": f"round {anchor} is open and we have not entered; picks "
                   f"come from Nexus, not from us"})

    # Always last and always present. A tick with nothing perishable still
    # has the exploration the operator asked the loop to continue, and a tick
    # that is handed an empty list stops for the wrong reason.
    items.append({
        "run": "python scripts/lab.py tick",
        "why": "standing work: pick answers up, launch what passes the gate, "
               "walk the search, close due verdicts -- and whether a question "
               "to Nexus may go"})
    return items
