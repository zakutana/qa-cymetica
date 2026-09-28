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
veto, and the reasons are in `git show 2ce72f21:docs/lab-plan.md` (the
finished plan, removed in plan v2, V7).
"""

from __future__ import annotations

import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from qa.state import file_lock, state_dir

NOTEBOOK = "lab.jsonl"
KINDS = ("session", "truth", "surface", "cycle", "n_eff", "tournament",
         "gate", "tick", "entry", "resolved", "fomo_reading", "answer_read",
         "proposal")
MAX_LESSONS = 3
MAX_NEXT = 8
ID = re.compile(r"^LAB-(\d{4})$")

# What the laboratory may spend. Nexus's own guide is explicit that an
# open-ended night "drifts, burns calls, and gives you no way to judge what it
# found" -- so there was a ceiling per session, then per rolling day
# (2026-09-19: a per-session count stopped the /loop before lunch or reset
# whenever a session opened), and since V5 there is none of ours at all.
#
# V5 of plan v2 (2026-09-23), "pás bez našich stropů": the operator's
# *"zadne limity, proste co je slibne a dava smysl to se jde hend otestvoat"*
# (laborator/SKILL.md). OUR count caps went; what each protected, and the
# brake that holds it now:
#
#   questions_per_day (24)   "an open-ended loop drifts and burns calls".
#                            Their own limits hold that now: ASKS_PER_HOUR
#                            (3 an hour, refusals counted), OUTSTANDING_BOUND
#                            (6 jobs of ours on their side) and backoff_until
#                            (the wait their failure asked for). The pace is
#                            theirs, measured, not a number we picked.
#   new_rooms_per_day (25)   "a ceiling, not a quota: the gate is the bar".
#                            The gate still is (qa.lab.gate), and money is the
#                            rest: `affordable` refuses past 60% of the book.
#   running_experiments (125) "past that nothing gets watched properly", and
#                            it set the stake (60% / 125). Each room now takes
#                            a FIXED share of the book, stake_share_of_book --
#                            the same 0.48%, a new reason -- so the 60% ceiling
#                            by itself stops the count at 125 and is the only
#                            count limit. Watching is the verdicts' job, one
#                            per room, whatever the count.
#
# [operator 2026-09-12] *"musime testvoat aspon 50 strategii najednou"*.
# Raised from 6 at 15% on 2026-09-12, and their reason is right for a reason
# they did not give: a verdict takes a five-to-seven-day window, so six at a
# time is six verdicts a week and knowing which of Nexus's ideas pay needs
# dozens. The count was always the weaker brake -- fifty at 2% is the whole
# book -- so what holds is the ceiling on what may be deployed at once: always
# dry powder, and one bad night cannot take it all. "Aspoň 50" is a floor, and
# 0.48% a room fits 125 under the ceiling; share_of_free_cash stays the
# operator's 2%, the per-order cap.
CAPS = {
    "stake_share_of_book": 0.0048,
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


# `feedback`, `acted` and `telegram` feed the morning report (plan v2, V11):
# what the operator said about it, what the manager changed because of it,
# and a message for Cymetica the report carries ready to paste.
ENTRY_KINDS = ("log", "lesson", "next", "feedback", "acted", "telegram")


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


# --- Nexus's credit ----------------------------------------------------------
#
# NEXT.md, agreed 2026-09-26: the tick reads GET /api/v1/nexus/usage -- the
# build allowance of Cymetica's plan on our account, readable with our key
# since ET-27414 -- and /lab shows it. Cymetica's credit, NOT the operator's
# Claude plan: CLAUDE.md keeps that one theirs to watch and nothing reads it.
# Nor does anything here act on a percentage of this one; it is shown.
#
# Their hourly deep-answer limit is not in /usage, so the questions it turned
# away are counted from the diary: nexus.py writes each as a `gave_up` row
# whose `error` says so (NEX-0048, NEX-0101, NEX-0102).
HOURLY_LIMIT = "hourly deep-answer limit"


def _units(value) -> float | None:
    """Their units are decimal strings ("0.650000")."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def credit_reading(status: int | None, body, why: str = "") -> dict:
    """One read of /usage, trimmed to what /lab shows. Anything short of a 200
    carrying both windows' `used_pct` is `read: False` with its reason and no
    number at all -- an unread credit is not an empty one (rule 8)."""
    if status != 200:
        return {"read": False, "why": why or f"HTTP {status}"}
    if not isinstance(body, dict):
        return {"read": False, "why": "the body is not a JSON object"}
    windows = {}
    for name in ("session", "week"):
        window = body.get(name)
        pct = window.get("used_pct") if isinstance(window, dict) else None
        if isinstance(pct, bool) or not isinstance(pct, (int, float)):
            return {"read": False, "why": f"no {name}.used_pct in the body"}
        windows[name] = {"pct": pct, "used": _units(window.get("used_units")),
                         "cap": _units(window.get("cap_units")),
                         "resets_at": window.get("resets_at")}
    items = body.get("items") if isinstance(body.get("items"), list) else None
    newest = next((i for i in items or [] if isinstance(i, dict)), None)
    return {"read": True, "as_of": body.get("as_of"),
            "plan": body.get("plan_name") or body.get("plan"), **windows,
            "warn_pct": body.get("warn_pct"), "critical_pct": body.get("critical_pct"),
            "items": len(items) if items is not None else None,
            "last_item": ({"label": newest.get("label") or newest.get("kind"),
                           "units": _units(newest.get("units")),
                           "at": newest.get("at")} if newest else None)}


def _kept_credits(rows: list[dict]) -> list[dict]:
    return [r["credit"] for r in rows
            if r.get("type") == "tick" and isinstance(r.get("credit"), dict)]


def credit_to_keep(reading, rows: list[dict]):
    """The reading as a tick row keeps it: whole when it moved since the last
    one kept whole, else only that it was read again and when. An unchanged
    plan read 72 times a day is ~31 KB a day into audits/lab, which git keeps
    for ever (CLAUDE.md, What we keep). An unread one is kept as it is."""
    if not isinstance(reading, dict) or not reading.get("read"):
        return reading
    last = next((c for c in reversed(_kept_credits(rows))
                 if c.get("read") and not c.get("same")), None)

    def body(credit):
        return {k: v for k, v in credit.items() if k != "as_of"}
    if last is not None and body(last) == body(reading):
        return {"read": True, "same": True, "as_of": reading.get("as_of")}
    return reading


def hourly_limit_refusals(nexus_rows: list[dict], now: datetime,
                          hours: float = 1.0) -> int:
    """Questions their deep lane turned away at its hourly limit within the
    last `hours`, each question once however many rows say so."""
    since = now - timedelta(hours=hours)
    turned = set()
    for row in nexus_rows:
        if HOURLY_LIMIT not in str(row.get("error") or "").lower():
            continue
        at = _at(row.get("at"))
        if at is not None and since < at <= now:
            turned.add(row.get("id") or row.get("job_id") or row.get("at"))
    return len(turned)


def credit_view(rows: list[dict], nexus_rows: list[dict], now: datetime) -> dict:
    """What /lab's credit line draws: the newest reading a tick took, under
    its own time; the newest attempt's failure, said beside it rather than
    turned into a number; and the hourly-limit refusals. Every field is
    always there, None when nothing was read."""
    tried = _kept_credits(rows)
    good = next((c for c in reversed(tried)
                 if c.get("read") and not c.get("same")), {})
    # A row that only says "read again, the same" dates the numbers.
    fresh = next((c for c in reversed(tried) if c.get("read")), {})
    newest = tried[-1] if tried else None
    session, week = good.get("session") or {}, good.get("week") or {}
    return {"plan": good.get("plan"),
            "session_pct": session.get("pct"), "session_resets": session.get("resets_at"),
            "week_pct": week.get("pct"), "week_resets": week.get("resets_at"),
            "warn_pct": good.get("warn_pct"), "critical_pct": good.get("critical_pct"),
            "items": good.get("items"),
            "last_item": (good.get("last_item") or {}).get("label"),
            "at": (fresh.get("as_of") or good.get("as_of")) if good else None,
            "unread": (None if newest is None or newest.get("read")
                       else str(newest.get("why") or "unread")),
            "refusals_hour": hourly_limit_refusals(nexus_rows, now, 1.0),
            "refusals_day": hourly_limit_refusals(nexus_rows, now, 24.0)}


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


def may_ask(pass_running: bool) -> tuple[bool, str]:
    """Whether another question may go to Nexus now, as far as OUR side goes.

    Not while a deep pass is running. That pass verifies #85 (the newest answer
    that names a tool), #86 (the last five questions) and #87 (the newest
    trade) -- so a question asked mid-run changes the subject the pass is
    measuring, and the verdict it sends the vendor is then about something
    else. Ours to wait; theirs to receive one true answer.

    The day's count of 24 went in V5 (2026-09-23): the pace is theirs now,
    `may_ask_now` -- ASKS_PER_HOUR, OUTSTANDING_BOUND and their backoff.
    """
    if pass_running:
        return False, ("a deep pass is running: it is verifying #85, #86 and "
                       "#87 over these very answers. Ask after it finishes")
    return True, ""


def may_ask_now(nexus_rows: list[dict], now: datetime | None = None,
                ignore_backoff: bool = False) -> tuple[bool, str]:
    """The pace, for a question asked by hand or by a loop tick -- THEIRS.

    A tick is a fresh process every twenty minutes, so it is read off the
    diary:

      * at most OUTSTANDING_BOUND jobs of ours on their side (REPLY-0037);
      * at most ASKS_PER_HOUR asks in a rolling hour, refused ones included;
      * the wait their own failure asked for (`backoff_until`).

    Two brakes of OURS went in V5 (2026-09-23), each covered by one above:

      * one question in flight at a time (IN_FLIGHT_HOURS, two hours): it kept
        the pick-up from splitting. Every question is polled by its own job id
        (`outstanding`, `cycle`), so nothing splits, and how many may wait on
        their side is their bound of six, not ours of one;
      * twenty minutes since the last question (the night's floor): the pace
        their deep lane can carry is ASKS_PER_HOUR, measured on 2026-09-21
        when the fourth ask of an hour came back "Hourly deep-answer limit
        reached" -- the floor never stopped that, the hourly count did.
    """
    moment = now or datetime.now(timezone.utc)
    # Their bound first: six outstanding of our own (REPLY-0037), over the day
    # they keep a queued job. Not a pace, so --now does not lift it -- a
    # seventh would be refused by them, and asking is what spends the slot
    # they reserved.
    held = outstanding(nexus_rows, moment, within_hours=POLLABLE_HOURS)
    if len(held) >= OUTSTANDING_BOUND:
        return False, (f"{len(held)} of our questions are outstanding on their "
                       f"side and their reserved lane bounds us at "
                       f"{OUTSTANDING_BOUND}: {', '.join(held[-3:])} first")
    # Every ask inside the last hour, refused or not: a refusal turns out to
    # cost them something, which is what their own hourly limit says. Not a
    # question the operator asked them in a browser (`lane: operator`,
    # `nexus.py record`): it never used their door.
    hour_ago = moment - timedelta(hours=1)
    # Nor one through the NEXUS bar (`lane: chat`, ask_nexus): 200 a minute on
    # our key, never their deep lane (deep pass 2026-09-24, R01).
    recent = [s for s in (_at(r.get("at")) for r in nexus_rows
                          if r.get("type") == "question"
                          and r.get("lane") not in ("operator", "chat"))
              if s is not None and s > hour_ago]
    if len(recent) >= ASKS_PER_HOUR:
        return False, (f"{len(recent)} question(s) went in the last hour and "
                       f"the cap is {ASKS_PER_HOUR}: their deep lane has an "
                       f"hourly limit of its own and a refusal counts against "
                       f"it")
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
               deployed: float = 0.0, parked: float = 0.0) -> tuple[bool, str]:
    """Whether one experiment may take this much, and how much may be out at once.

    A share of what is FREE, not of the bankroll: the book already knows what
    is deployed. An unreadable book refuses -- rule 8, and the same refusal
    paper.py makes when it cannot read what is in the bots.

    The total is the brake that matters, and since V5 the only one on how
    many run. Fifty at 2% is the whole book, so without a ceiling the count
    would be no limit at all.
    It is measured against the BOOK -- free plus what is out -- because that is
    what exposure means. Against the remainder it would walk down as we deploy
    and bind at 37.5%, under a number written as 60%.

    `parked` is money in paper clones that do not trade (V2, 2026-09-23): in
    the book, out of free cash, and not exposure. Left out, the book is only
    smaller -- the omission errs toward refusing.
    """
    if free_cash is None:
        return False, ("the book could not be read, and an unreadable book is "
                       "not an empty one: no order goes out on it")
    # `running` is said, not counted against: the 125-experiment cap went in
    # V5 (2026-09-23). A room takes a fixed share of the BOOK
    # (CAPS["stake_share_of_book"]), so the 60% ceiling below is the only
    # count limit -- it stops the laboratory at 125 rooms by itself.
    share = CAPS["share_of_free_cash"]
    ceiling = free_cash * share
    if usdc > ceiling:
        return False, (f"{usdc:.0f} is more than {share * 100:.0f}% of the "
                       f"{free_cash:.0f} free ({ceiling:.0f}). Percentages are "
                       f"what a verdict compares, so a smaller stake measures "
                       f"the same strategy")
    limit = CAPS["total_exposure"]
    book = free_cash + deployed + max(parked or 0.0, 0.0)
    if (deployed + usdc) > book * limit:
        return False, (f"{deployed:.0f} is already out and {usdc:.0f} more "
                       f"would pass {limit * 100:.0f}% of the {book:.0f} book "
                       f"(free, deployed and parked). There is always dry "
                       f"powder, so one bad night cannot take the book")
    return True, (f"{usdc:.0f} of {free_cash:.0f} free, {running} running, "
                  f"{deployed + usdc:.0f} out of the {book * limit:.0f} "
                  f"allowed on a {book:.0f} book")


POLLABLE_HOURS = 24
# IN_FLIGHT_HOURS (2) went in V5, 2026-09-23: one question held the next one
# back for up to two hours so the pick-up would not split. Each job is polled
# by its own id, so it does not; what bounds how many wait is theirs, below.
#
# How many jobs of ours may be outstanding on their side at once. Theirs, not
# ours: REPLY-0037 reserves a lane slot for this agent and bounds it at six.
# Counted over POLLABLE_HOURS because that is the window the same answer says
# they now hold a queued job for.
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
            # lane for two hours then, and a slot of OUTSTANDING_BOUND now.
            # `accepted` absent is an older row and stays as it was.
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


# --- what wakes the manager (plan v2, V6) -----------------------------------
#
# A /loop firing costs a model turn whatever the tick found, and on 2026-09-20
# the loop spent 533 calls on 35 firings. The tick now ends in one line naming
# what needs the manager, and a firing that reads `decide: none` stops there.
# Each constant says what it was set for, so a later change of context re-asks
# it rather than inheriting it.

# A question is his memory of what happened -- he remembers nothing -- so one
# is due when something happened he has not heard, or after this long without
# one. Set for a loop day of at most twenty working firings (V6's done-when):
# twelve by this clock, the rest for news, answers, gaps and the report. It is
# not a cap on him: their pace (may_ask_now) still decides whether one may go.
QUESTION_HOURS = 2.0
# The idle bug hunt of 2026-09-19, which every idle tick used to run. Eight
# hours was a cost; [operator 2026-09-25] took the cost away ("Me limity
# vubec neres"), so it is as often as a hunt can finish and be read.
HUNT_HOURS = 3.0
# The sweep of 2026-09-20 is "once a night": the first hunt of a local night,
# unless one ran inside this many hours. By day a sweep comes on their news
# instead (vendor_news below).
SWEEP_HOURS = 20.0
NIGHT_LOCAL_HOURS = range(0, 6)
# A held reason worth saying to the operator the first time it appears: an
# error from their side, or an id their API does not know.
GAP_HELD = re.compile(r"HTTP [45]\d\d|knows no card")
# What scripts/lab.py writes when a close only waits for a deep pass to end.
CLOSE_WAITS = "a deep pass is running"


def _door(error: str) -> str:
    return str(error).split(":", 1)[0].strip()


def new_gaps(said: dict, earlier: list[dict]) -> list[str]:
    """What went wrong for the first time: a door that did not fail on the
    tick before, or a held reason of the gap class no earlier tick carried.
    A held reason is retried and shown on every tick, so "first" is the
    whole of what makes it news."""
    before = earlier[-1] if earlier else {}
    failing = {_door(e) for e in before.get("errors") or []}
    gaps = [e for e in said.get("errors") or [] if _door(e) not in failing]
    # Every gap-class held line the tick saw, not only the six it shows
    # (RL04, deep pass of 2026-09-24); a tick row from before carries `held`.
    seen = {line for row in earlier
            for line in (row.get("gap_held") or []) + (row.get("held") or [])}
    held = said.get("gap_held")
    held = said.get("held") if held is None else held
    gaps += [line for line in held or []
             if GAP_HELD.search(str(line)) and line not in seen]
    # A close their side refused, the first time (RL01). One that only waits
    # for a deep pass to end is the pass working, not news.
    closes = {line for row in earlier for line in row.get("close_failed") or []}
    gaps += [line for line in said.get("close_failed") or []
             if CLOSE_WAITS not in line and line not in closes]
    return gaps


def vendor_news(events: list[dict]) -> dict:
    """The newest journal `seq` at which Cymetica moved, and what moved.

    Moved: a report's status changed (`vendor_status` is written on change
    only), a person answered on a2a, a Telegram answer was pasted in. Their
    automated a2a acknowledgements are not news. Whoever wrote the event --
    the console's --ask, this tick, a sweep -- it is the same news. A
    report's FIRST status is our filing reaching their tracker, not them
    moving (deep pass 2026-09-25, R02: #129's "pending" read as news).
    `items` is (seq, line) of the last twenty, for `news_since`.
    """
    seq, items, sighted = None, [], set()
    for event in events:
        kind = event.get("type")
        if kind == "vendor_status" and event.get("report_id") is not None:
            if event["report_id"] not in sighted:
                sighted.add(event["report_id"])
                continue
            line = f"#{event['report_id']} {event.get('status')}"
        elif kind == "telegram_reply" and event.get("by") == "vendor":
            line = str(event.get("msg_id") or "telegram")
        elif (kind == "message" and event.get("by") == "vendor"
              and event.get("auto") is not True):
            line = f"{event.get('origin') or 'a2a'} {event.get('msg_id')}"
        else:
            continue
        try:
            at = int(event.get("seq"))
        except (TypeError, ValueError):
            continue
        if seq is None or at > seq:
            seq = at
        items.append((at, line))
    return {"seq": seq, "lines": [line for _, line in items[-3:]],
            "items": items[-20:]}


def news_since(items, earlier: list[dict]) -> list[str]:
    """The news lines after the last sweep's baseline -- what woke this one.
    None without a baseline: the first tick sets it and announces nothing
    (deep pass 2026-09-25, R03: the last three lines ever were printed on
    every hunt sweep, a night sweep no news woke included)."""
    baseline = _news_baseline(earlier)
    if baseline is None:
        return []
    return [line for seq, line in items or [] if int(seq) > baseline]


def _news_baseline(earlier: list[dict]) -> int | None:
    """The journal seq the last sweep already covered: the `vendor_seq` of
    the newest tick that decided one, else the oldest tick that carried a
    `vendor_seq` at all -- so the first tick after this shipped sets the line
    rather than sweeping everything already in the journal."""
    for row in reversed(earlier):
        if "hunt sweep" in (row.get("decide") or []) and row.get("vendor_seq") is not None:
            return int(row["vendor_seq"])
    for row in earlier:
        if row.get("vendor_seq") is not None:
            return int(row["vendor_seq"])
    return None


def _last_decided(earlier: list[dict], prefix: str) -> datetime | None:
    for row in reversed(earlier):
        if any(str(item).startswith(prefix) for item in row.get("decide") or []):
            return _at(row.get("at"))
    return None


def decide(said: dict, earlier: list[dict], last_question: datetime | None,
           now: datetime, local_hour: int) -> list[str]:
    """What this tick needs the manager for, most urgent first; [] is none.

    `said` is the tick's own record, `earlier` the tick rows before it in
    order, `last_question` when the last question of ours went. Pure: the
    same diary always decides the same way, so a day can be replayed.
    """
    items: list[str] = []
    if said.get("morning_due"):
        items.append("report")
    if said.get("skipped"):
        # A deep pass or a night holds everything but the read-only report.
        return items
    if new_gaps(said, earlier):
        items.append("gap")
    items += [f"answer {origin}" for origin in said.get("answered") or []]

    if said.get("may_ask"):
        news = bool(said.get("verdicts") or said.get("resolved"))
        if not news and last_question is not None:
            news = any((row.get("verdicts") or row.get("resolved"))
                       and (_at(row.get("at")) or now) > last_question
                       for row in earlier)
        waited = (last_question is None or (now - last_question).total_seconds()
                  >= QUESTION_HOURS * 3600)
        if news or waited:
            items.append("question")

    # [operator 2026-09-25]: they work faster than a nightly sweep. Something
    # new from them since the last sweep is a sweep now, by day too.
    theirs = said.get("vendor_seq")
    baseline = _news_baseline(earlier)
    if theirs is not None and baseline is not None and int(theirs) > baseline:
        items.append("hunt sweep")

    if not items:
        hunted = _last_decided(earlier, "hunt")
        if hunted is None or (now - hunted).total_seconds() >= HUNT_HOURS * 3600:
            swept = _last_decided(earlier, "hunt sweep")
            night = local_hour in NIGHT_LOCAL_HOURS and (
                swept is None or (now - swept).total_seconds() >= SWEEP_HOURS * 3600)
            items.append("hunt sweep" if night else "hunt bugs")
    return items


def last_question_at(nexus_rows: list[dict]) -> datetime | None:
    """When our last question reached him: not one the operator asked in a
    browser (`lane: operator`), nor one turned away at their door before a
    job existed -- neither carried our record to him."""
    stamps = [_at(row.get("at")) for row in nexus_rows
              if row.get("type") == "question" and row.get("lane") != "operator"
              and not (row.get("accepted") is False and not row.get("job_id"))]
    stamps = [s for s in stamps if s is not None]
    return max(stamps) if stamps else None


def decide_line(items: list[str]) -> str:
    return "decide: " + (" + ".join(items) if items else "none")


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
    # hours to twenty minutes at the same time, and went altogether in V5
    # (2026-09-23): their hourly limit (ASKS_PER_HOUR) is the pace now.
    "search_batch": 30,           # backtests per tick; their limit per minute
    # When their side refuses without saying when to come back, the wait
    # starts here -- the old floor's twenty minutes, kept as backoff's base
    # because backoff stays -- and DOUBLES per refusal in the streak, up to
    # the maximum below. Flat is wrong both ways:
    "backoff_base_seconds": 20 * 60,
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


IN_FLIGHT = ("queued", "pending", "running", "processing", "in_progress")


def _ours_gave_up(row: dict) -> bool:
    """A give-up of OURS: their job still in flight when we stopped
    polling, or a read of ours that failed (`unread: ...`)."""
    status = str(row.get("status") or "").lower()
    return status in IN_FLIGHT or status.startswith("unread")


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
        # nothing about it either way -- nor does an answer the operator
        # pasted from their web chat (RL06, deep pass of 2026-09-24).
        if row.get("lane") in ("shallow", "operator"):
            continue
        when = _at(row.get("at"))
        if when is None:
            continue
        if row.get("type") == "gave_up" and _ours_gave_up(row):
            # Our patience ran out while their job was still going, or our
            # read failed: not a refusal of theirs (their_down_streak says
            # the same of these).
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
        wait = min(NIGHT["backoff_base_seconds"] * (2 ** max(streak - 1, 0)),
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
    # "too soon" (the twenty-minute floor) and "cap" (24 a day) went in V5;
    # their hourly limit and bound are `may_ask_now`'s, read off the diary.
    hold = state.get("hold_until")
    if hold is not None and now < hold:
        skipped = "backoff"
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


def bot_series(samples: list[dict], instance: str, funded: float | None,
               entry_at=None, entry_profit=None, restart: bool = False
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

    `entry_at`, when the funding moment is known, is a point at 100: what
    went in, before it traded. Bollinger Bandit (STR-0034) had made +33.6 on
    240 by its first reading and stood at +7.1 at the end -- +2.96% on what
    went in, read as -9.7% from the first reading (review of 2026-09-23). A
    funding before the window is outside it, and a room that took over a
    running bot starts from its first reading inside, as before.

    A RESTART -- a variant of V5 on a clone that ran before (`bot_restart`)
    -- passes `entry_profit`, what the bot had made by `entry_at`. Their
    `total_profit_usdc` is lifetime, so measured from the funding a variant
    would carry the previous setting's P&L. It enters at 100 on what the bot
    held then (went in + made so far) and moves only by what it made since;
    readings before the restart are the previous variant's. A restart whose
    profit is unknown (`restart=True`, `entry_profit=None`) is not sized, so
    not judged.
    """
    try:
        base = float(funded or 0)
    except (TypeError, ValueError):
        return []
    if base <= 0:
        return []
    if restart or entry_profit is not None:
        start = _at(entry_at)
        if entry_profit is None or start is None:
            return []
        held = base + float(entry_profit)
        if held <= 0:
            return []
        out = [{"t": start.isoformat(), "index": 100.0}]
        for row in samples or []:
            if (not isinstance(row, dict) or row.get("kind") != "bot"
                    or row.get("instance_id") != instance):
                continue
            when = _at(row.get("at"))
            try:
                profit = float(row.get("total_profit_usdc"))
            except (TypeError, ValueError):
                continue
            if when is not None and when > start:
                out.append({"t": row["at"], "index": 100.0 * (
                    1.0 + (profit - float(entry_profit)) / held)})
        return out
    out = [{"t": str(entry_at), "index": 100.0}] if entry_at else []
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


def book_series(index_points, entry_index, filled_at, closed_at=None,
                closed_value=None, until=None) -> list[dict]:
    """A card leg as OUR position saw it -- the plan's V2 of 2026-09-23.

    A paper position is worth units x their index (their sample: 0.02164 x
    231.30 = 5.0064, to the cent), so our book is their index rebased on our
    own fill: 100 at `filled_at` (`entry_index` from the buy's response, or
    their index there when the response did not carry it), then
    100 x index / entry at every point after it while we hold. From our
    close -- or their resolution -- on, the leg is worth `closed_value`, and
    frozen at it to `until`: what we sold for is what the leg made.

    Before, the verdict read their index from its first point inside the
    window: a card that moved before our order filled was credited with a
    move we never had, and a position sold on day two was judged as if held.
    """
    filled, closed = _at(filled_at), _at(closed_at)
    points = _points(index_points)
    if filled is None:
        return []
    try:
        entry = float(entry_index)
    except (TypeError, ValueError):
        entry = None
    if not entry:
        before = [v for t, v in points if t <= filled]
        after = [v for t, v in points if t > filled]
        entry = (before or after or [None])[-1 if before else 0]
    if not entry:
        return []
    out = [{"t": filled.isoformat(), "index": 100.0}]
    for when, value in points:
        if when <= filled:
            continue
        if closed is not None and when >= closed:
            break
        out.append({"t": when.isoformat(), "index": 100.0 * value / entry})
    if closed is not None and isinstance(closed_value, (int, float)):
        out.append({"t": closed.isoformat(), "index": float(closed_value)})
        stop = _at(until)
        if stop is not None and stop > closed:
            out.append({"t": stop.isoformat(), "index": float(closed_value)})
    return out


def _cost(leg: dict) -> float:
    """The live round trip a leg pays, in %: a card or a fund leg is bought
    and sold (GATE's 0.2% taker + 0.5% slippage each side); a bot's P&L is
    as their engine books it. An arena leg is charged nothing and judged bid
    to bid, so the spread paid on the way in is not counted against it."""
    kind = leg.get("kind") or "card"
    return GATE["round_trip_cost_pct"] if kind in ("card", "fund") else 0.0


def _net_of(gross_pct: float, cost_pct: float) -> float:
    return ((1.0 + gross_pct / 100.0) * (1.0 - cost_pct / 100.0) - 1.0) * 100.0


def fund_series(points) -> list[dict]:
    """Their fund history, `[{t, v}]` from get_fund_history, in the shape the
    verdict reads a card's index in."""
    out = []
    for point in points or []:
        if isinstance(point, dict) and point.get("t") and isinstance(
                point.get("v"), (int, float)) and not isinstance(point["v"], bool):
            out.append({"t": point["t"], "index": float(point["v"])})
    return out


def arena_series(samples: list[dict], team: str) -> list[dict]:
    """An Arena team's share, from the sampler's reads of its book, in the
    shape the verdict reads a card's index in.

    The best BID: NEX-0076 -- a share never pays out, "You realize value by
    selling the share back into the book at its live price" -- so what a
    held share is worth is what the book would pay for it now. Not the last
    trade (0.45 against a 0.55 bid on 2026-09-28: a price nobody is offering)
    and not a mid (their ask side was empty). A round with nobody bidding is
    no point, a gap and never a price of zero. A bear leg is read on the same
    bids, inverted by the verdict: nothing we have seen says a share can be
    sold short at all.
    """
    out = []
    for row in samples or []:
        if (not isinstance(row, dict) or row.get("kind") != "arena"
                or row.get("team") != team or not row.get("at")):
            continue
        bid = row.get("best_bid")
        if isinstance(bid, (int, float)) and not isinstance(bid, bool):
            out.append({"t": row["at"], "index": float(bid)})
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
        # And every helper they call to reach a number: a change inside one
        # is a change to what a verdict means, and a hash of the callers
        # alone would not move (A8's lesson, review of 2026-09-23).
        source = "".join(inspect.getsource(f) for f in (
            verdict, _early, _from_peak, _inside, bot_series, fund_series,
            arena_series, book_series, _cost, _net_of))
    except (OSError, TypeError):  # pragma: no cover -- frozen or stripped
        return "unknown"
    return hashlib.sha256(source.encode("utf-8")).hexdigest()[:12]


def leg_exit(points, entry_index, filled_at, side, tp, sl) -> dict | None:
    """The first time a held card leg's index, from our fill, reached its own
    take-profit or stop -- {exit, at, moved} -- or None. `tp` above zero and
    `sl` below it, in % in the leg's direction; a level he did not name never
    fires. Entry is the fill's own index when the buy's response gave one,
    else their first point at or after the fill."""
    if tp is None and sl is None:
        return None
    since = _at(filled_at)
    inside = [(t, v) for t, v in _points(points) if since is None or t >= since]
    try:
        entry = float(entry_index) if entry_index else None
    except (TypeError, ValueError):
        entry = None
    if entry is None and inside:
        entry = inside[0][1]
    if not entry:
        return None
    way = -1.0 if str(side).lower() == "bear" else 1.0
    for when, value in inside:
        moved = way * (value / entry - 1.0) * 100.0
        if tp is not None and moved >= float(tp):
            return {"exit": "tp", "at": when.isoformat(), "moved": round(moved, 3)}
        if sl is not None and moved <= float(sl):
            return {"exit": "sl", "at": when.isoformat(), "moved": round(moved, 3)}
    return None


def _from_peak(peak: float, value: float) -> float:
    """How far below its best the portfolio stands, in % of that best --
    both given as % returns on what went in. C8, review of 2026-09-23: the
    difference in percentage points read +50% -> +20% as a 30% drawdown
    where the holder lost 20%."""
    return max(0.0, (1.0 - (1.0 + value / 100.0) / (1.0 + peak / 100.0)) * 100.0)


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
                     "return_pct": _net_of(curve[-1][1], _cost(leg))})
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
        drawdown = max(drawdown, _from_peak(peak, value))
    clean = [{k: v for k, v in leg.items() if k != "curve"} for leg in legs]
    # What it stands at after the round trip each card or fund leg pays; the
    # drawdown above is on the gross path, where his stop is set.
    value = sum(float(leg.get("share") or 1.0) * leg["return_pct"]
                for leg in legs) / weight

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


def verdict(acceptance: dict, series: dict, now, closes: dict | None = None,
            stopped=None) -> dict:
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

    `stopped`, the moment the room was stopped by hand while it held its
    pick, ends the window there: it is judged over what it ran (V2 of the
    2026-09-23 plan -- a stopped room used to wait for a window that no
    longer meant anything).
    """
    start = _at(acceptance.get("at"))
    days = float(acceptance.get("window_days") or 0)
    if start is None or days <= 0:
        return {"verdict": "inconclusive", "why": "the acceptance names no window",
                "coverage": 0.0, "formula": formula_fingerprint()}
    end = start + timedelta(days=days)
    halted = _at(stopped)
    if halted is not None and start < halted < end:
        end = halted
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
        gross = way * (exit_value / entry - 1.0) * 100.0
        legs.append({**leg, "exit": exit_kind, "entry_index": entry,
                     "exit_index": exit_value,
                     "return_pct": _net_of(gross, _cost(leg)),
                     "gross_return_pct": gross, "curve": curve})

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
        drawdown = max(drawdown, _from_peak(peak, value))

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
        why, name = f"it returned {ret:+.2f}%", "refuted"
    elif benchmark is not None and ret <= benchmark:
        why, name = (f"it returned {ret:+.2f}% against the benchmark's "
                     f"{benchmark:+.2f}%"), "refuted"
    elif stop_pct is not None and drawdown > stop_pct:
        why, name = (f"its drawdown reached {drawdown:.2f}%, past the "
                     f"{stop_pct:.2f}% it was accepted with"), "refuted"
    elif card and benchmark is None:
        # Accepted against a benchmark that has no marks over the stretch:
        # beating it cannot be claimed, and a gap is not a loss either (C1,
        # review of 2026-09-23 -- on return alone, a room that lost to BTC
        # survived).
        why, name = (f"it returned {ret:+.2f}%, but its benchmark has no "
                     f"marks over the window, so beating it cannot be "
                     f"claimed"), "inconclusive"
    else:
        why, name = (f"it returned {ret:+.2f}% inside a {drawdown:.2f}% drawdown"
                     + (f", against the benchmark's {benchmark:+.2f}%"
                        if benchmark is not None else "")), "survived"

    return {"verdict": name, "why": why,
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


def _pearson(a, b) -> float | None:
    """None when the correlation is undefined -- too short, or either series
    is flat -- rather than a fabricated 0.0 or 1.0. A flat series (a card that
    has not moved) has no variance to correlate against anything.

    Two series keyed by day are paired on the days both have (C4, review of
    2026-09-23); two lists are taken as already aligned."""
    if isinstance(a, dict) and isinstance(b, dict):
        shared = sorted(set(a) & set(b))
        a, b = [a[k] for k in shared], [b[k] for k in shared]
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
    """When a line declares which he picks, only what such a line names;
    otherwise every name. Bots since R02 (2026-09-22); funds since NEX-0081
    (2026-09-23, one pick and five funds ranked below it in prose opened six
    rooms); cards since C7 (2026-09-23).

    A declaring line that names nothing -- "**The one pick:**", "# ONE PICK
    THAT CLEARS THE BAR" -- hands the declaration to the next line that names
    something, unless a heading comes first."""
    picked: set[str] = set()
    pending = section = False
    for line in str(text or "").split("\n"):
        heading = bool(_MD_HEADING.match(line))
        declares = bool(_PICKED.search(line) or (
            heading and _PICK_WORD.search(line)
            and not _RULED_OUT.search(_BRACKETED.sub("", line))))
        found = find(line)
        if heading:
            # A declaring HEADING that names nothing holds to the next
            # heading: NEX-0100's "## PICKS" over "**1 -- ...**" and "**2 --
            # ...**" had its second pick dropped (2026-09-25). Plural only:
            # "# ONE PICK ..." still hands itself to the next naming line.
            section = declares and not found and bool(
                re.search(r"\bpicks\b", line, re.I))
        rules_out = bool(_RULED_OUT.search(_BRACKETED.sub("", line)))
        if declares:
            picked.update(found)
            # A section holds its own items; it hands nothing to a stray line.
            pending = not found and not section
        elif section and found and _ITEM.match(line) and not rules_out:
            # Only the section's numbered items, never its prose or a line
            # that rules out -- "It beats Trend Titan", "- Excluded: ..."
            # (deep pass 2026-09-25, R04).
            picked.update(found)
        elif pending and found:
            picked.update(found)
            pending = False
        elif heading:
            pending = False
    if picked & set(names):
        return [name for name in names if name in picked]
    # A numbered list that names them IS his pick list (NEX-0098, 2026-09-25:
    # asked for five, he numbered five and discussed seven more in prose and
    # an inline "**Excluded:**"; all twelve were cloned). The first name of
    # each numbered item, in the answer's order.
    listed: list[str] = []
    for line in str(text or "").split("\n"):
        # A numbered item that rules out is not a pick (R10, same pass).
        if _NUMBERED.match(line) and not _RULED_OUT.search(_BRACKETED.sub("", line)):
            found = find(line)
            if found and found[0] not in listed:
                listed.append(found[0])
    if set(listed) & set(names):
        return [name for name in listed if name in names]
    return names


_NUMBERED = re.compile(r"^\s*\d+[.)]\s")
# An item of a list, as markdown or as NEX-0100's bold "**1 -- MACD Hunter**".
_ITEM = re.compile(r"^\s*(?:[-*•]\s+)?[*_`]*\s*\d+\s*(?:[.):]|--|[—–-])")


# A line that DECLARES which one he chooses -- "**Pick: MACD Hunter**",
# "**The one to clone: `Perceptron Oracle`**", "## Answer: clone ...",
# "**PICK 1 — `9ef04dc6…`**", "I would clone MACD Hunter". C7, review of
# 2026-09-23 (3/3): any line carrying "clone", "recommend" or "choose" counted,
# so NEX-0080's comparison of its pick with the four bots we already run --
# "it's the clone most likely to be uncorrelated" -- read as five picks.
_PICKED = re.compile(
    r"^[\s#>*_`-]*(?:\d+[.)]\s*)?[*_`\s]*"
    r"(?:(?:the|my|one|top)\s+)*"
    r"(?:picks?|choice|answer|recommendation|one to clone)"
    r"\b[^:\n—–]{0,12}[:—–]"
    r"|\bI(?:'d| would)\s+(?:pick|choose|clone|go with)\b",
    re.I)
# A markdown heading about his pick: "# ONE PICK THAT CLEARS THE BAR".
_PICK_WORD = re.compile(r"\bpicks?\b", re.I)


# "Take-profit: +20% from entry. Stop: -12% from entry.", "TP +8%, stop -4%",
# "take-profit **+12%** · stop **−7%**" -- markdown and a unicode minus
# between the word and the number, nothing else. "hard 24h stop", "Time stop:
# close at 7 days" and "stop set just outside ... 6.8%" are not levels.
_LEVEL_GAP = r"[\s*:_`]*"
_NUMBER = r"([+−-]?\s?\d+(?:\.\d+)?)\s*%"
_TAKE = re.compile(r"(?:take[- ]?profit|\bTP\b)" + _LEVEL_GAP + _NUMBER, re.I)
_STOP = re.compile(r"\b(?:stop(?:[- ]?loss)?|SL)\b" + _LEVEL_GAP + _NUMBER, re.I)


def exit_levels(text: str, picks: list[str]) -> dict[str, dict]:
    """His take-profit and stop for each pick, in % from entry -- the stop a
    fall, so below zero. A pick's levels are the first ones after a line that
    names it alone, before a line that names another; a level he states on
    the pick's own line is its own. What he did not state stays None.

    The plan's V2 of 2026-09-23: every room the launch opened carried tp and
    sl None although nearly every answer named both, so the criterion judged
    his idea without his exits."""
    wanted = {str(p).lower(): p for p in picks}
    out = {p: {"tp": None, "sl": None} for p in picks}
    current = None
    for line in str(text or "").split("\n"):
        lower = line.lower()
        named = [key for key in wanted if key in lower]
        if len(named) == 1:
            current = wanted[named[0]]
        elif named:
            current = None
        if current is None:
            continue
        levels = out[current]
        take, stop = _TAKE.search(line), _STOP.search(line)
        if take and levels["tp"] is None:
            levels["tp"] = abs(_level(take.group(1)))
        if stop and levels["sl"] is None:
            levels["sl"] = -abs(_level(stop.group(1)))
    return out


def _level(raw: str) -> float:
    return float(raw.replace("−", "-").replace(" ", ""))


def picked_cards(text: str, species=()) -> list[str]:
    """The cards an answer picks, first mention first: every id he names,
    less the species ids of bots (a bot is not a card, #91), less those he
    names only to rule out, and -- when a line declares his pick -- only what
    such a line names. The same reading `proposed_bots` and `proposed_funds`
    make, so the launch and the board cannot disagree about what he chose."""
    body = str(text or "")
    skip = {str(s).lower() for s in species or ()}

    def find(line: str) -> list[str]:
        return [c for c in CARD_ID.findall(line.lower()) if c not in skip]
    return _only_picked(body, find, _proposed(body.lower(), find))


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


def note_answer_read(origin: str) -> dict:
    """An answer the launch has read whole, with nothing of it left waiting.

    V5 (2026-09-23): answers are read once. Plan v1 measured 242 re-reads of
    answers that named nothing -- the same "names no card" line on every tick
    for a day. Only an answer with a pick still waiting is read again."""
    return _append({"type": "answer_read", "origin": str(origin), "at": _now()})


# --- V5: a paper bot's settings, walked in time on its one clone -----------
#
# REPLY-0049 (2026-09-23): one active paper clone per species per account; a
# second is 409 ALREADY_CLONED. So a species' settings are tried one after
# another on its ONE clone, never side by side: the grid is walked in time.
#
# WHY EVERY BODY IS WHOLE. A PATCH that sets a field cannot unset it. A fresh
# clone's stop_loss_pct, take_profit_pct, max_position_pct and
# min_ai_confidence are null (CLN-0018's response, 2026-09-22) and clone.py's
# floor sends numbers only, so a factor one variant moved would leak into
# every variant after it and "one factor at a time" would be false from the
# second variant on. Every variant's PATCH carries the whole grid -- the
# reference with exactly one factor moved -- so a variant is determined by its
# own body, whatever ran on the clone before it.
#
# THE REFERENCE is their default wherever they have one (the same response:
# max_open_positions 5, arena on, event cards and TGE off) and ours where
# theirs is unset, inside their bounds (update_bot_settings: SL 1-20, TP
# 5-100, max_position 1-50, confidence 0-1). The first variant IS the
# reference; the room his pick opened, at their defaults, is its control.
# catalog_trading_enabled is in every body, off, and never moved: it trades
# only a catalog_watchlist, and the watchlist is where money goes -- not a
# setting we tune (clone.py leaves it out of SAFE_SETTINGS on purpose).
#
# These are OUR rooms (origin OUR-...): the settings are our idea, measured
# beside his picks and never ranked above them, and each is put to him as a
# question (`lab.py brief`).
VARIANT_REFERENCE = {
    "stop_loss_pct": 10.0, "take_profit_pct": 20.0, "max_position_pct": 10.0,
    "max_open_positions": 5, "min_ai_confidence": 0.5,
    "event_card_trading_enabled": False, "arena_trading_enabled": True,
    "catalog_trading_enabled": False, "tge_trading_enabled": False,
}
# Each factor once either side of the reference, the toggles flipped once.
VARIANT_MOVES = (
    ("stop_loss_pct", 5.0), ("stop_loss_pct", 15.0),
    ("take_profit_pct", 10.0), ("take_profit_pct", 40.0),
    ("max_position_pct", 5.0), ("max_position_pct", 25.0),
    ("max_open_positions", 2), ("max_open_positions", 10),
    ("min_ai_confidence", 0.3), ("min_ai_confidence", 0.7),
    ("event_card_trading_enabled", True),
    ("arena_trading_enabled", False),
    ("tge_trading_enabled", True),
)
OUR_ID = re.compile(r"^OUR-(\d{4})$")


def variants() -> list[dict]:
    """The grid in the order it is walked: [{label, settings}], the reference
    first. Pure and deterministic -- the same list on every call."""
    out = [{"label": "reference", "settings": dict(VARIANT_REFERENCE)}]
    for field, value in VARIANT_MOVES:
        out.append({"label": f"{field}={value}",
                    "settings": {**VARIANT_REFERENCE, field: value}})
    return out


def next_variant(tried) -> dict | None:
    """The first variant of the grid not yet tried on a clone, or None when
    its walk is done. `tried` is every label already proposed for it,
    whatever became of the proposal: one their side refused is not proposed
    again on every tick -- its room says why it stopped."""
    done = {str(label) for label in tried or ()}
    return next((v for v in variants() if v["label"] not in done), None)


def note_proposal(kind: str, ref: str, instance: str, variant: dict,
                  why: str) -> dict:
    """One idea of OURS, OUR-NNNN -- what a room of our own lane opens from
    (`qa.rooms.open_strategy` asks `on_record`). The id is taken under the
    lock, in the step that writes it."""
    target = path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(target):
        used = [int(found.group(1)) for found in
                (OUR_ID.match(str(row.get("id") or "")) for row in load()
                 if row.get("type") == "proposal") if found]
        record = {"type": "proposal", "id": f"OUR-{max(used, default=0) + 1:04d}",
                  "at": _now(), "kind": kind, "ref": str(ref),
                  "instance": str(instance), "variant": variant["label"],
                  "settings": dict(variant["settings"]), "why": str(why)}
        with open(target, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def proposals(rows: list[dict] | None = None) -> list[dict]:
    rows = load() if rows is None else rows
    return [r for r in rows if r.get("type") == "proposal"]


def tried_variants(instance: str, rows: list[dict] | None = None) -> list[str]:
    """The labels already proposed for one clone, oldest first."""
    return [str(r.get("variant")) for r in proposals(rows)
            if str(r.get("instance")) == str(instance)]


def is_ours(origin) -> bool:
    """A room of our own lane: its origin is a proposal of ours, not his."""
    return bool(OUR_ID.match(str(origin or "")))


def restart_affordable(amount: float, free_cash: float | None,
                       deployed: float = 0.0, parked: float = 0.0
                       ) -> tuple[bool, str]:
    """Whether a paused clone's money may trade again under the ceiling.

    A variant spends no new money: the clone's practice balance was moved in
    once and sits PARKED while the bot is paused (V2 of 2026-09-23). Starting
    it again turns parked money into exposure, so the one count limit left
    since V5 -- 60% of the book -- is asked of it. `affordable`'s 2%-of-free
    per-order cap is not: it sizes a NEW stake, and a restart takes nothing
    from free cash."""
    if free_cash is None:
        return False, ("the book could not be read, and an unreadable book is "
                       "not an empty one: no bot starts on it")
    limit = CAPS["total_exposure"]
    book = free_cash + max(deployed or 0.0, 0.0) + max(parked or 0.0, 0.0)
    if deployed + amount > book * limit:
        return False, (f"{deployed:.0f} is already out and the {amount:.0f} "
                       f"parked in this clone would pass {limit * 100:.0f}% of "
                       f"the {book:.0f} book")
    return True, (f"{deployed + amount:.0f} out of the {book * limit:.0f} "
                  f"allowed on a {book:.0f} book")


def bot_restart(clone_rows, instance: str, since, samples=None) -> dict | None:
    """Where a bot leg of a room whose criterion was written at `since`
    enters, when that room runs on a RESTART of the clone -- a variant (V5).

    None for a room on the clone's first run (it enters at its funding, as
    before) and for a room that took over a bot already running (no start
    after its criterion; read as it always was). Otherwise the first accepted
    start at or after `since`, and what the bot had made by then: the start's
    own `bot_profit_usdc`, else the sampler's newest reading at or before it,
    else None -- a variant that cannot be sized is not judged."""
    moment = _at(since)
    answered = {row.get("id"): row for row in clone_rows or ()
                if row.get("type") == "outcome"}
    starts, pauses = [], []
    for row in clone_rows or ():
        done = answered.get(row.get("id")) or {}
        if (row.get("type") == "intent" and row.get("kind") in ("enable", "disable")
                and str(row.get("instance_id")) == str(instance)
                and done.get("outcome") == "accepted"):
            when = _at(done.get("at") or row.get("at"))
            if when is not None:
                (starts if row["kind"] == "enable" else pauses).append((when, row))
    before = [s for s in starts if moment is not None and s[0] < moment]
    after = sorted((s for s in starts if moment is not None and s[0] >= moment),
                   key=lambda s: s[0])
    if not before or not after:
        return None
    when, intent = after[0]
    # A pause between the criterion and that start means the start is a LATER
    # room's variant: this room took over a bot already running and ended.
    if any(moment <= at < when for at, _ in pauses):
        return None
    profit = _money(intent.get("bot_profit_usdc"))
    if profit is None:
        seen = [(_at(r.get("at")), _money(r.get("total_profit_usdc")))
                for r in samples or ()
                if isinstance(r, dict) and r.get("kind") == "bot"
                and str(r.get("instance_id")) == str(instance)]
        seen = sorted((at, p) for at, p in seen
                      if at is not None and at <= when and p is not None)
        profit = seen[-1][1] if seen else None
    return {"at": when.isoformat(), "profit": profit}


def answers_read(rows: list[dict] | None = None) -> set[str]:
    """Every answer the launch has marked read."""
    rows = load() if rows is None else rows
    return {str(r.get("origin")) for r in rows if r.get("type") == "answer_read"}


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


def funded(clone_rows) -> dict[str, float]:
    """What went into each paper clone: its accepted transfers, by instance --
    the base a bot's money is measured against."""
    asked = {row.get("id"): row for row in clone_rows or ()
             if row.get("type") == "intent" and row.get("kind") == "fund"}
    out: dict[str, float] = {}
    for row in clone_rows or ():
        intent = asked.get(row.get("id"))
        if (intent and row.get("type") == "outcome"
                and row.get("outcome") == "accepted"):
            amount = _money(intent.get("amount"))
            if amount is not None:
                key = str(intent.get("instance_id"))
                out[key] = out.get(key, 0.0) + amount
    return out


def funded_at(clone_rows) -> dict[str, str]:
    """When each paper clone was first funded: the time of its first accepted
    transfer, by instance -- the moment a bot enters at 100."""
    asked = {row.get("id"): row for row in clone_rows or ()
             if row.get("type") == "intent" and row.get("kind") == "fund"}
    out: dict[str, str] = {}
    for row in clone_rows or ():
        intent = asked.get(row.get("id"))
        if (intent and row.get("type") == "outcome"
                and row.get("outcome") == "accepted"):
            when = str(row.get("at") or intent.get("at") or "")
            key = str(intent.get("instance_id"))
            if when and (key not in out or when < out[key]):
                out[key] = when
    return out


def bot_stops(clone_rows, samples) -> list[dict]:
    """Every time a paper bot of ours stopped trading, and why.

    The plan's V2 (review of 2026-09-23): two bots stopped by themselves and
    nobody noticed. A stop is the step from trading -- a sampler reading that
    says so, or our own accepted start -- to a reading that says it does not.
    Its cause is one of three:

        ours          our accepted pause lies between the two
        their_guard   it stopped at a cumulative LOSS. Not documented --
                      their docs describe no automatic halt, and NEX-0049's
                      "the stop-loss and the pause are the same lever" is a
                      claim of Nexus's -- but every loss-side halt we have
                      stopped at a round share of what went in (Perceptron
                      Oracle -5.00% twice, MACD Hunter -10.00%)
        unexplained   neither -- a check and a report

    Pure over two loaded diaries; `after` and `before` bound the moment.
    """
    went_in = funded(clone_rows)
    answered = {row.get("id"): row for row in clone_rows or ()
                if row.get("type") == "outcome"}
    events: dict[str, list[tuple[str, str, dict]]] = {}
    for row in clone_rows or ():
        done = answered.get(row.get("id")) or {}
        if (row.get("type") == "intent" and row.get("kind") in ("enable", "disable")
                and done.get("outcome") == "accepted"):
            events.setdefault(str(row.get("instance_id")), []).append(
                (str(done.get("at") or row.get("at") or ""), row["kind"], row))
    for row in samples or ():
        if row.get("kind") == "bot" and row.get("instance_id"):
            events.setdefault(str(row["instance_id"]), []).append(
                (str(row.get("at") or ""), "sample", row))

    out = []
    for instance, seen in events.items():
        trading_since, paused = None, False
        for at, kind, row in sorted(seen, key=lambda e: e[0]):
            if kind == "enable":
                trading_since, paused = at, False
            elif kind == "disable":
                paused = True
            elif row.get("is_trading") is True:
                trading_since, paused = at, False
            elif row.get("is_trading") is False and trading_since is not None:
                profit = _money(row.get("total_profit_usdc"))
                if paused:
                    cause = "ours"
                elif profit is not None and profit < 0:
                    cause = "their_guard"
                else:
                    cause = "unexplained"
                base = went_in.get(instance)
                out.append({"instance": instance, "cause": cause,
                            "after": trading_since, "before": at,
                            "profit_usdc": profit, "funded_usdc": base,
                            "profit_pct": (profit / base * 100.0
                                           if profit is not None and base
                                           else None)})
                trading_since, paused = None, False
    return sorted(out, key=lambda s: s["before"])


def _sold_by_us(paper_rows) -> dict[str, float | None]:
    """position -> the P&L our own accepted close record realised (None when
    the record carries no figure). The close outcome often names no position;
    its intent does."""
    intents = {row.get("id"): row for row in paper_rows
               if row.get("type") == "intent"}
    out: dict[str, float | None] = {}
    for row in paper_rows:
        if row.get("type") != "outcome" or row.get("outcome") != "accepted":
            continue
        intent = intents.get(row.get("id")) or {}
        if row.get("kind") != "close" and intent.get("kind") != "close":
            continue
        position = intent.get("position_id") or row.get("position_id")
        if position:
            out[str(position)] = _money(row.get("realized_pnl_usdc"))
    return out


def picked_rooms(room_rows: list[dict], answers: list[dict]) -> set[str]:
    """The rooms that hold what their answer PICKED, read the way the launch
    reads it: a card room's card among `picked_cards`, a bot room's species
    among `proposed_bots` against the bot rooms that answer opened, a fund
    room's symbol among `proposed_funds`. A room opened from a whole answer
    (before 2026-09-21) holds all of it. One reading for the board, the
    verdicts and the archive, so the three cannot disagree about whose idea
    a room was."""
    texts = {str(a.get("id") or ""): str(a.get("text") or "")
             for a in answers if a.get("type") == "answer"}
    by_origin: dict[str, list[dict]] = {}
    for row in room_rows:
        if row.get("type") == "strategy":
            by_origin.setdefault(str(row.get("origin")), []).append(row)
    out: set[str] = set()
    for origin, opened in by_origin.items():
        text = texts.get(origin)
        if text is None:
            continue
        cards = set(picked_cards(text))
        bots = {row["name"] for row in proposed_bots(text, [
            {"name": r.get("title"), "id": r.get("ref")}
            for r in opened if r.get("kind") == "bot"])}
        funds = set(proposed_funds(text, [
            r.get("ref") for r in opened if r.get("kind") == "fund"]))
        for row in opened:
            kind = row.get("kind")
            if row.get("card"):
                chosen = str(row["card"]).lower() in cards
            elif kind == "bot":
                chosen = row.get("title") in bots
            elif kind == "fund":
                chosen = row.get("ref") in funds
            else:
                chosen = True       # a whole-answer room, or an arena team
            if chosen:
                out.add(str(row.get("id")))
    return out


def archived_rooms(room_rows: list[dict], answers: list[dict],
                   paper_rows: list[dict], clone_rows=()) -> set[str]:
    """Stopped rooms that are archived rather than judged -- derived, never
    written, so no status anywhere has to learn a new word.

    Stopped, with no verdict, and either never holding anything -- no order
    of ours accepted on its cards, no funding of its bots, and a fund or an
    Arena room holds nothing -- or not holding his pick (the launch opened
    STR-0011 and STR-0012 on cards NEX-0064 had ruled out). A stopped room
    that held his pick is not archived: it is judged up to its stop.
    """
    status: dict[str, str] = {}
    judged: set[str] = set()
    accepted_on: dict[str, dict] = {}
    for row in room_rows:
        if row.get("type") == "status":
            status[str(row.get("room"))] = str(row.get("status"))
        elif row.get("type") == "verdict":
            judged.add(str(row.get("room")))
        elif row.get("type") == "acceptance":
            accepted_on[str(row.get("room"))] = row
    intents = {r.get("id"): r for r in paper_rows
               if r.get("type") == "intent" and r.get("kind") != "close"}
    bought: set[tuple[str, str]] = set()
    for row in paper_rows:
        if (row.get("type") == "outcome" and row.get("outcome") == "accepted"
                and row.get("kind") != "close"):
            intent = intents.get(row.get("id")) or {}
            nexus = intent.get("nexus")
            origin = nexus.get("id") if isinstance(nexus, dict) else nexus
            bought.add((str(origin), str(intent.get("card_id") or "").lower()))
    went_in = funded(clone_rows)
    picks = picked_rooms(room_rows, answers)
    # The first room each bot ever ran in, by when the room opened: a fresh
    # clone's funding is what that room held (STR-0045, 2026-09-28).
    opened_at = {str(r.get("id")): str(r.get("at") or "") for r in room_rows
                 if r.get("type") == "strategy"}
    first_room: dict[str, str] = {}
    for room_id, row in accepted_on.items():
        for leg in row.get("legs") or []:
            if leg.get("kind") != "bot":
                continue
            ref = str(leg.get("ref"))
            known = first_room.get(ref)
            if known is None or opened_at.get(room_id, "") < opened_at.get(known, ""):
                first_room[ref] = room_id

    out: set[str] = set()
    for row in room_rows:
        if row.get("type") != "strategy":
            continue
        room = str(row.get("id"))
        if status.get(room) != "stopped" or room in judged:
            continue
        legs = (accepted_on.get(room) or {}).get("legs") or []
        cards = {str(row.get("card") or "").lower()} | {
            str(leg.get("card") or leg.get("ref") or "").lower()
            for leg in legs if (leg.get("kind") or "card") == "card"}
        if is_ours(row.get("origin")):
            # A room of ours (V5) is never his pick, so "not his pick" cannot
            # archive it -- that would archive every variant as it stopped. It
            # held something only if its restart went through: our variant
            # ran on the clone after its criterion was written.
            since = (accepted_on.get(room) or {}).get("at")
            ran = any(bot_restart(clone_rows, str(leg.get("ref")), since)
                      or (first_room.get(str(leg.get("ref"))) == room
                          and went_in.get(str(leg.get("ref"))))
                      for leg in legs if leg.get("kind") == "bot")
            if not ran:
                out.add(room)
            continue
        held = any((str(row.get("origin")), c) in bought for c in cards if c) \
            or any(went_in.get(str(leg.get("ref")))
                   for leg in legs if leg.get("kind") == "bot")
        if not held or room not in picks:
            out.add(room)
    return out


def board(answers: list[dict], notebook: list[dict], room_rows: list[dict],
          paper_rows: list[dict], sample_rows: list[dict],
          clone_rows: list[dict] | tuple = ()) -> list[dict]:
    """Every Nexus proposal that came to anything, and what it earned.

    [operator 2026-09-19] the goal is the strategies that earn the most, so
    each answer is followed to the money: the stake our paper orders credited
    to it (`intent.nexus.id`) on the cards it PICKED, what each of those
    positions made -- our own close record when we sold it, the sampler's
    newest reading otherwise -- the paper bots it picked on what went in and
    what they made, and each room's status and verdict. An answer the gate
    turned away is on the board with its numbers: "what has been tested" was
    the other half of what they asked for.

    C2 of the 2026-09-23 review: the stake of every buy was set against the
    P&L of the positions the sampler had read, and a card he ruled out that
    the launch bought by mistake was his -- NEX-0064 read +1.39% where his one
    pick made +4.17%. Only picks are his now, and the return is over the
    stake of the positions priced, with the count said.

    Best earner first, by return on the stake; then the rooms nothing has
    priced yet; then what the gate rejected. Pure over six loaded diaries.
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

    texts = {str(a.get("id") or ""): str(a.get("text") or "")
             for a in answers if a.get("type") == "answer"}
    picked = {origin: set(picked_cards(text)) for origin, text in texts.items()}
    accepted_on: dict[str, dict] = {}
    for row in room_rows:
        if row.get("type") == "acceptance":
            accepted_on[str(row.get("room"))] = row
    # A bot room is his when its species is what his answer picks. Its kind
    # read the way the report reads it (qa.rooms.room_kind): a kindless room
    # with bot legs is a bot room, and its money was never counted.
    from qa import rooms as rooms_store

    plans = rooms_store.plans(room_rows)

    def is_bot(r: dict) -> bool:
        return rooms_store.room_kind(r, plans.get(str(r.get("id")))) == "bot"

    his = picked_rooms(room_rows, answers)
    bot_rooms = {origin: [str(r.get("id")) for r in opened
                          if is_bot(r) and str(r.get("id")) in his]
                 for origin, opened in rooms_by.items()}

    intents = {r.get("id"): r for r in paper_rows
               if r.get("type") == "intent" and r.get("kind") != "close"}
    held: dict[str, tuple[str, float, str]] = {}
    for row in paper_rows:
        if (row.get("type") != "outcome" or row.get("outcome") != "accepted"
                or row.get("kind") == "close"):
            continue
        intent = intents.get(row.get("id"))
        if not intent:
            continue
        nexus = intent.get("nexus")
        origin = str((nexus.get("id") if isinstance(nexus, dict) else nexus)
                     or "")
        position = row.get("position_id") or intent.get("position_id")
        stake = _money(intent.get("usdc"))
        if (position and stake is not None and str(intent.get("card_id") or "")
                .lower() in picked.get(origin, ())):
            held[str(position)] = (origin, stake,
                                   str(intent.get("card_id") or "").lower())

    newest: dict[str, dict] = {}
    newest_bot: dict[str, dict] = {}
    for row in sample_rows:
        if row.get("kind") == "position":
            key, into = str(row.get("position_id") or ""), newest
        elif row.get("kind") == "bot":
            key, into = str(row.get("instance_id") or ""), newest_bot
        else:
            continue
        if str(row.get("at") or "") >= str(into.get(key, {}).get("at") or ""):
            into[key] = row

    sold = _sold_by_us(paper_rows)
    money: dict[str, dict] = {}
    # The same money by room, for the laboratory's report (V4): one answer
    # may open several rooms, and a product is a kind of room, not an answer.
    by_room: dict[str, dict] = {}

    def count(origin: str, stake: float, pnl: float | None,
              room: str | None = None) -> None:
        books = [money.setdefault(origin, {})]
        if room:
            books.append(by_room.setdefault(room, {}))
        for book in books:
            for key in ("stake", "pnl", "priced_stake"):
                book.setdefault(key, 0.0)
            for key in ("priced", "positions"):
                book.setdefault(key, 0)
            book["stake"] += stake
            book["positions"] += 1
            if pnl is not None:
                book["pnl"] += pnl
                book["priced"] += 1
                book["priced_stake"] += stake

    def card_room(origin: str, card: str) -> str | None:
        opened = rooms_by.get(origin) or []
        named = [r for r in opened if str(r.get("card") or "").lower() == card]
        whole = [r for r in opened if not r.get("card")
                 and r.get("kind") not in ("bot", "fund", "arena")]
        chosen = (named or whole or [None])[0]
        return str(chosen.get("id")) if chosen else None

    for position, (origin, stake, card) in held.items():
        if sold.get(position) is not None:
            pnl = sold[position]
        else:
            reading = newest.get(position) or {}
            pnl = _money(reading.get("realized_pnl_usdc"
                                     if reading.get("status") == "closed"
                                     else "unrealized_pnl_usdc"))
        count(origin, stake, pnl, card_room(origin, card))
    went_in = funded(clone_rows)
    # A room of ours (V5) is ours by construction, so its bot is counted too.
    for origin, opened_here in rooms_by.items():
        if is_ours(origin):
            bot_rooms[origin] = [str(r.get("id")) for r in opened_here
                                 if is_bot(r)]
    stopped_at = {}
    for row in room_rows:
        if row.get("type") == "status":
            stopped_at[str(row.get("room"))] = (
                _at(row.get("at")) if row.get("status") == "stopped" else None)

    def reading(instance: str, since=None, until=None) -> float | None:
        """The bot's lifetime profit at its newest reading inside the room's
        own run: a later variant on the same clone is not this room's."""
        best = None
        for row in sample_rows:
            if row.get("kind") != "bot" or str(row.get("instance_id")) != instance:
                continue
            when = _at(row.get("at"))
            if when is None or (since and when < since) or (until and when > until):
                continue
            if best is None or when >= best[0]:
                best = (when, row)
        return _money(best[1].get("total_profit_usdc")) if best else None

    for origin, room_ids in bot_rooms.items():
        for room_id in room_ids:
            criterion = accepted_on.get(room_id) or {}
            for leg in criterion.get("legs") or []:
                instance = str(leg.get("ref") or "")
                if leg.get("kind") != "bot" or not went_in.get(instance):
                    continue
                until = stopped_at.get(room_id)
                restart = bot_restart(clone_rows, instance, criterion.get("at"),
                                      sample_rows)
                if restart is None:
                    count(origin, went_in[instance],
                          reading(instance, until=until), room_id)
                elif restart["profit"] is not None:
                    # A variant: on what the bot held at its restart, and only
                    # what it made since.
                    now = reading(instance, _at(restart["at"]), until)
                    count(origin, went_in[instance] + restart["profit"],
                          None if now is None else now - restart["profit"],
                          room_id)

    out = []
    ours = [{"type": "answer", "id": origin,
             "at": min(str(r.get("at") or "") for r in opened)}
            for origin, opened in rooms_by.items() if is_ours(origin)]
    for answer in list(answers) + ours:
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
                     "return_pct"),
                 "money": by_room.get(str(r.get("id")))} for r in opened]
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
            "positions": cash["positions"] if cash else 0,
            "priced": cash["priced"] if cash else 0,
            "pnl_usdc": cash["pnl"] if priced else None,
            "pnl_pct": (cash["pnl"] / cash["priced_stake"] * 100.0
                        if priced and cash["priced_stake"] else None),
            "verdict": (said[0] if len(each) == 1 and said
                        else ", ".join(said) if said else None),
            "verdict_return_pct": (each[0]["verdict_return_pct"]
                                   if len(each) == 1 else None),
            "gates": [{"card": g.get("card"), "verdict": g.get("verdict"),
                       "why": g.get("why")} for g in gated]})

    def order(row):
        # A room of ours is never ranked above his picks (V5, the own lane):
        # his rows first, however they earned; ours after, in the same order.
        lane = 3 if is_ours(row["origin"]) else 0
        if row["pnl_pct"] is not None:
            return (lane, -row["pnl_pct"])
        if row["room"]:
            return (lane + 1, 0.0)
        return (lane + 2, 0.0)
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
