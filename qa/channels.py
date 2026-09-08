"""One reader over all three channels we talk to Cymetica on.

The operator, 2026-09-08: *"je v tom bordel a mam v tom chaos."* Three channels
with three shapes and no way to hold the state of them in your head. The fix is
not a fourth store -- they already meet in one place:

    bug reports   filing_intent / filing_outcome / vendor_status / verification_*
    telegram      telegram_sent / telegram_reply
    a2a           a2a_intent / a2a_outcome / message(origin=a2a)

all of it the append-only journal. So this is a library that reads it, and the
CLI, the alert and any skill go through here rather than each growing their own
idea of what "unanswered" means. That is the `.claude/hooks/open_threads.py`
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
            real = not event.get("auto") and bool(event.get("kind"))
            theirs.append(("a2a", event, real))

    out = []
    for (channel, our_id), sent in ours.items():
        answers = [e for c, e, real in theirs
                   if c == channel and str(e.get("reply_to") or "") == our_id and real]
        answers.sort(key=lambda e: str(e.get("at") or ""))
        row = {"channel": channel, "question_id": sent.get("msg_id"),
               "asked_at": sent.get("at"), "answer_id": None, "minutes": None}
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
        report[channel] = {"asked": len(rows), "n": len(timed),
                           "median_minutes": median,
                           "unanswered": sum(1 for r in rows
                                             if r["minutes"] is None)}
    report["conclusive"] = all(report[c]["n"] >= ENOUGH for c in (TELEGRAM, A2A))
    return report


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
    import importlib.util
    from pathlib import Path

    path = Path(__file__).resolve().parent.parent / "scripts" / "a2a.py"
    spec = importlib.util.spec_from_file_location("a2a_channels", path)
    a2a = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(a2a)
    threads = a2a.threads(events)
    return {
        "unanswered": [t["msg_id"] for t in a2a.open_threads(events)],
        "threads": len(threads),
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


def state(events: list[dict] | None = None) -> dict:
    """The three channels in one shape, so a report cannot quietly omit one."""
    events = read_events() if events is None else events
    heard = inbound(events)
    last = {}
    for row in heard:
        last[row["channel"]] = row["at"]

    out = {BUG: _bug(events), TELEGRAM: _telegram(events), A2A: _a2a(events)}
    for name, channel in out.items():
        channel["last_from_them"] = last.get(name)
        channel["heard"] = sum(1 for row in heard if row["channel"] == name)
    return out
