"""One reader over all three channels we talk to Cymetica on.

The operator, 2026-09-08: *"je v tom bordel a mam v tom chaos."* Three channels
with three shapes and no way to hold the state of them in your head. The fix is
not a fourth store -- they already meet in one place:

    bug reports   filing_intent / filing_outcome / vendor_status / verification_*
    telegram      telegram_sent / telegram_reply
    a2a           a2a_intent / a2a_outcome / message(origin=a2a)

all of it the append-only journal. So this is a library that reads it, and the
CLI, the alert and any skill go through here rather than each growing their own
idea of what "unanswered" means. That is the `.claude/hooks/start/open_threads.py`
pattern, and the reason for it is that two readers of one journal eventually
disagree and nobody can tell which is right.

The one judgement encoded here: **silence is never the default.** An automated
first pass is not worth waking anyone for -- 35 of the 39 a2a messages we hold
are the trophy-emoji routing prompt. But a message we cannot classify speaks,
and says it could not be classified. Every message recorded before 2026-09-08
is that case, because `fetch_inbox` read `metadata.auto` and threw it away, and
the journal cannot be rewritten to add it. A reader that treats unknown as
automated hides the one message it exists to surface.
"""

from __future__ import annotations

import json

from qa.state import ledger_path, read_events

A2A = "a2a"
TELEGRAM = "telegram"
BUG = "bug"
ROOMS = "rooms"


def _preview(text, width: int = 90) -> str:
    flat = " ".join(str(text or "").split())
    return flat if len(flat) <= width else flat[: width - 1] + "…"


def inbound(events: list[dict]) -> list[dict]:
    """Every event that is THEM speaking, on any channel, oldest first.

    `auto` is three-valued on purpose: True, False, or None for "we cannot
    tell". None is not False.
    """
    out = []
    for event in events:
        kind = event.get("type")
        if kind == "message" and event.get("by") == "vendor":
            out.append({
                "channel": A2A, "at": event.get("at"), "id": event.get("msg_id"),
                "auto": True if event.get("auto") else (
                    False if event.get("kind") else None),
                "kind": event.get("kind"),
                "answers": event.get("reply_to"),
                "preview": _preview(event.get("text")),
            })
        elif kind == "telegram_reply":
            out.append({
                "channel": TELEGRAM, "at": event.get("at"),
                "id": event.get("msg_id"), "auto": False, "kind": "human",
                "answers": event.get("reply_to"),
                "preview": _preview(event.get("text")),
            })
        elif kind == "vendor_status":
            # The bug channel speaks by moving a status, not by sending words.
            # Their sentences live in bounty.json's status_notes, which is
            # overwritten on every refresh and so cannot be a source here.
            out.append({
                "channel": BUG, "at": event.get("at"),
                "id": f"#{event.get('report_id')}:{event.get('status')}",
                "auto": False, "kind": "status",
                "answers": event.get("report_id"),
                "preview": f"#{event.get('report_id')} is now "
                           f"{event.get('status')}",
            })
    out.sort(key=lambda row: str(row["at"] or ""))
    return out


def new_lines(events: list[dict], seen: set) -> tuple[list[str], set]:
    """One line per thing worth waking the operator for, and the new watermark.

    Pure, so the alert can be tested without a subprocess and without a clock.
    """
    lines, marked = [], set(seen)
    for row in inbound(events):
        key = f"{row['channel']}|{row['id']}"
        if key in marked:
            continue
        marked.add(key)
        if row["auto"] is True:
            continue
        if row["channel"] == BUG:
            lines.append(f"[bug] {row['preview']}  ({row['at']})")
        elif row["channel"] == TELEGRAM:
            lines.append(f"[telegram] {row['id']} answers {row['answers']}: "
                         f"\"{row['preview']}\"")
        else:
            mark = row["kind"] or "kind unknown"
            lines.append(f"[a2a] {row['id']} ({mark}): \"{row['preview']}\"")
    return lines, marked


def room_lines(rows: list[dict], seen: set) -> tuple[list[str], set]:
    """One line per new note from the operator in the Nexus rooms, and the
    new watermark. Pure, like new_lines, and for the same reason.

    Our own notes never wake anyone: the alert is for what waits on us.
    """
    lines, marked = [], set(seen)
    for row in rows:
        if row.get("type") != "operator_note":
            continue
        key = f"{ROOMS}|{row.get('id')}"
        if key in marked:
            continue
        marked.add(key)
        lines.append(f"[room] {row.get('id')} in {row.get('room') or 'general'} "
                     f"from the operator: \"{_preview(row.get('text'))}\"")
    return lines, marked


# ---------------------------------------------------------------------------
# The comparison: which channel actually answers, and how fast
# ---------------------------------------------------------------------------
def _moment(at) -> "datetime | None":
    from datetime import datetime, timezone

    try:
        parsed = datetime.fromisoformat(str(at))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def pairs(events: list[dict]) -> list[dict]:
    """Each question of ours beside their first REAL answer to it.

    The automated first pass is not an answer and must never be timed as one.
    Cymetica said so in writing on 2026-09-08: *"the 2 to 6 second a2a first
    pass is a receipt, the same thing as the Ref: ET-xxxxx auto-ack you see on
    Telegram."* Timing the receipt would make a2a look a thousand times faster
    than Telegram, and it would be a NUMBER -- which is worse than an
    impression, because the point of measuring was to replace one.

    An unclassifiable message is not counted as an answer either. It is not
    evidence of speed, and guessing here would put the guess into a statistic.
    """
    ours, theirs = {}, []
    for event in events:
        kind = event.get("type")
        if kind == "telegram_sent":
            ours[("telegram", event["msg_id"])] = event
        elif kind == "a2a_outcome" and event.get("via"):
            intent = next((e for e in events if e.get("type") == "a2a_intent"
                           and e.get("msg_id") == event.get("msg_id")), None)
            if intent is not None:
                # Their id for our message is what their reply names.
                ours[("a2a", str(event["via"]))] = intent
        elif kind == "telegram_reply":
            theirs.append(("telegram", event, True))
        elif kind == "message" and event.get("by") == "vendor":
            # An answer unless it is automated or is the receipt. It used to
            # require a `kind`, and scripts/bounty.py wrote that key only when
            # it was truthy -- so every human reply they have sent arrived
            # with no kind at all and was discarded as unreal. The receipt is
            # excluded by name because that is what it is; absence of a label
            # is not evidence of anything.
            real = not event.get("auto") and event.get("kind") != "first_pass"
            theirs.append(("a2a", event, real))

    # Their `reply_to` names a message of OURS, with THEIR id for it. Where no
    # a2a_intent exists -- and none ever has, because scripts/a2a.py has never
    # been run -- that name is the only record the question was asked at all,
    # and eight threads sit in the journal that way. The moment we asked is
    # then taken from the automated receipt on the same thread, which by their
    # own description arrives within seconds of a send. It is marked as a
    # proxy, because a number that cannot say where it came from is how a
    # measurement turns back into an impression.
    for event in events:
        if event.get("type") != "message" or event.get("by") != "vendor":
            continue
        answered = event.get("reply_to")
        if not answered or ("a2a", str(answered)) in ours:
            continue
        receipts = [e for e in events
                    if e.get("type") == "message" and e.get("by") == "vendor"
                    and str(e.get("reply_to") or "") == str(answered)
                    and (e.get("auto") or e.get("kind") == "first_pass")]
        asked_at = min((str(r.get("at") or "") for r in receipts), default="")
        ours[("a2a", str(answered))] = {
            "msg_id": str(answered), "at": asked_at or None,
            "asked_at_from": "receipt" if asked_at else None,
        }

    out = []
    for (channel, our_id), sent in ours.items():
        answers = [e for c, e, real in theirs
                   if c == channel and str(e.get("reply_to") or "") == our_id and real]
        answers.sort(key=lambda e: str(e.get("at") or ""))
        row = {"channel": channel, "question_id": sent.get("msg_id"),
               "asked_at": sent.get("at"), "answer_id": None, "minutes": None,
               "asked_at_from": sent.get("asked_at_from") or "us"}
        if answers:
            asked, replied = _moment(sent.get("at")), _moment(answers[0].get("at"))
            row["answer_id"] = answers[0].get("msg_id")
            # Two events written in the same breath are not a latency. The four
            # telegram events we hold share one timestamp, because they were
            # typed in together on 2026-09-08 for a conversation held on the
            # 7th -- and the arithmetic read "answered in 0 minutes". A wrong
            # number is worse than none here: it displaces the impression it
            # was meant to correct. `correspond.py --at` is how a backdated
            # message stops being this case.
            same_breath = str(sent.get("at")) == str(answers[0].get("at"))
            if asked and replied and not same_breath:
                row["minutes"] = round((replied - asked).total_seconds() / 60)
            elif same_breath:
                row["untimed"] = "both recorded at the same moment"
        out.append(row)
    out.sort(key=lambda row: str(row["asked_at"] or ""))
    return out


ENOUGH = 5


def compare(events: list[dict] | None = None) -> dict:
    """Telegram against a2a, with the size of the evidence stated.

    `conclusive` is False until both channels have ENOUGH answered questions.
    Three answers on one evening is a demonstration; the operator asked for a
    comparison, and the difference between the two is the whole reason this
    exists rather than an opinion.
    """
    events = read_events() if events is None else events
    report = {}
    for channel in (TELEGRAM, A2A):
        rows = [r for r in pairs(events) if r["channel"] == channel]
        timed = sorted(r["minutes"] for r in rows if r["minutes"] is not None)
        median = None
        if timed:
            middle = len(timed) // 2
            median = (timed[middle] if len(timed) % 2
                      else round((timed[middle - 1] + timed[middle]) / 2))
        # Unanswered means NO ANSWER, not "no number". A pair recorded in one
        # breath has an answer_id and no minutes, and counting it here made
        # `compare` print "2 still unanswered" about two questions the vendor
        # had answered -- which the operator read on 2026-09-08. Untimed is its
        # own state and is reported as its own number.
        report[channel] = {"asked": len(rows), "n": len(timed),
                           "median_minutes": median,
                           "unanswered": sum(1 for r in rows
                                             if r["answer_id"] is None),
                           "answered_but_untimed": sum(
                               1 for r in rows
                               if r["answer_id"] is not None
                               and r["minutes"] is None)}
    report["conclusive"] = all(report[c]["n"] >= ENOUGH for c in (TELEGRAM, A2A))
    return report


def labels(events: list[dict]) -> dict[str, str]:
    """Their id for a message of ours, where the record carries one.

    A display detail with one job: the session-start line says `MSG-0003
    (ET-22498)` because ET-22498 is what the operator says out loud, and a
    line that names only our own id sends them to grep. Kept here rather than
    in the hook so that naming a thread and deciding it is open come from the
    same module -- the drift this file exists to prevent.
    """
    out: dict[str, str] = {}
    for event in events:
        if event.get("type") == "telegram_sent" and event.get("via"):
            out[str(event.get("msg_id"))] = str(event["via"])
    return out


def _telegram(events: list[dict]) -> dict:
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parent.parent / "scripts" / "correspond.py"
    spec = importlib.util.spec_from_file_location("correspond_channels", path)
    correspond = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(correspond)
    return {
        "unanswered": [t["msg_id"] for t in correspond.open_threads(events)],
        "threads": len(correspond.threads(events)),
    }


def _a2a(events: list[dict]) -> dict:
    """What is open on a2a, counted the way `pairs()` counts it.

    `unanswered` used to come from `scripts/a2a.py::open_threads`, which keys
    on our own `a2a_intent` -- and that script has sent two questions in its
    life. So this returned an empty list while `compare()`, reading the same
    journal through `pairs()`, reported five open threads: one module, two
    answers to "unanswered", and the blind one was the shape the session-start
    hook and every status report read. The eight threads it could not see
    exist only in THEIR `reply_to`, because the send was made by hand.
    Architecture audit, 2026-09-20.

    `undelivered` still comes from the journalled sends, because that is the
    only place delivery is recorded at all -- a thread reconstructed from
    their receipt says nothing about whether ours landed.
    """
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parent.parent / "scripts" / "a2a.py"
    spec = importlib.util.spec_from_file_location("a2a_channels", path)
    a2a = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(a2a)
    threads = a2a.threads(events)
    rows = [row for row in pairs(events) if row["channel"] == A2A]
    return {
        "unanswered": [row["question_id"] for row in rows
                       if not row.get("answer_id")],
        "threads": len(rows),
        "undelivered": [m for m, t in threads.items()
                        if a2a.delivery(t) != "accepted"],
    }


def _bug(events: list[dict]) -> dict:
    """What the tracker owes us, read from the ledger rather than re-derived."""
    path = ledger_path()
    try:
        ledger = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        # Bootstrapping, or a state directory that holds only a journal. The
        # channel still has to answer; it just cannot say what is owed.
        return {"unanswered": [], "reports": 0}
    owed, filed = [], 0
    for fid, row in (ledger.get("findings") or {}).items():
        reports = (row.get("filing") or {}).get("reports") or []
        filed += len(reports)
        if [k for k, v in (row.get("obligations") or {}).items() if v]:
            owed.append(fid)
    return {"unanswered": owed, "reports": filed}


def _rooms() -> dict:
    """The operator's notes in the Nexus tab that no session has read yet.

    Not a vendor channel -- the operator writes these in the console -- but it
    is a place something waits for us, so it is reported with the rest.
    """
    from qa import rooms

    rows = rooms.load()
    notes = [r for r in rows if r.get("type") == "operator_note"]
    return {"unanswered": [r.get("id") for r in rooms.unread(rows)],
            "notes": len(notes),
            "last_note_at": max((str(r.get("at")) for r in notes), default=None)}


def state(events: list[dict] | None = None) -> dict:
    """The channels in one shape, so a report cannot quietly omit one.

    Four since 2026-09-11: the operator's notes in the Nexus rooms wait on us
    the way a bug obligation does, and a report that left them out would tell
    the operator nothing was waiting while their feedback sat unread.
    """
    events = read_events() if events is None else events
    heard = inbound(events)
    last = {}
    for row in heard:
        last[row["channel"]] = row["at"]

    out = {BUG: _bug(events), TELEGRAM: _telegram(events), A2A: _a2a(events),
           ROOMS: _rooms()}
    # Which side the outstanding items sit on, per channel. On the two chat
    # channels `unanswered` means a message of OURS nobody has replied to, so
    # it waits on them. On the bug channel it means a row carrying an
    # obligation, which is a debt of ours. The first version of this printed
    # "waiting on us" over all three, and told the operator to act on a
    # telegram thread that was sitting with the vendor.
    waiting = {BUG: "us", TELEGRAM: "them", A2A: "them", ROOMS: "us"}
    for name, channel in out.items():
        channel["last_from_them"] = last.get(name)
        channel["heard"] = sum(1 for row in heard if row["channel"] == name)
        channel["waiting_on"] = waiting[name]
    return out
