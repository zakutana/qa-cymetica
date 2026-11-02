"""One reader over the three channels we talk to Cymetica on.

    bug reports   vendor_status on the journal, what we sent in state/filed.json
    telegram      telegram_sent / telegram_reply
    a2a           a2a_intent / a2a_outcome / message(origin=a2a)

`auto` is three-valued on purpose: True, False, or None for "we cannot tell". None is not False: a reader
that treats unknown as automated hides the one message it exists to surface.
"""

from __future__ import annotations

from qa.paths import load_filed, read_events

A2A = "a2a"
TELEGRAM = "telegram"
BUG = "bug"
# In their report_status enum: a claim of a fix (paid is engaging with the report as fixed), and "they said no".
FIX_CLAIMED = {"fixed", "paid"}
REJECTED = {"invalid", "duplicate", "wontfix"}


def last_verdict(row: dict, report_id) -> str | None:
    """Our last word on this report, as filed.json holds it."""
    sent = [v for v in row.get("verdicts_sent") or [] if v.get("report_id") == report_id]
    return sent[-1].get("verdict") if sent else None


def decide(result: str, status: str, newest: dict | None, fixed_at: str | None) -> str | None:
    """Which verdict this report is owed, or None."""
    status = str(status or "").lower()
    last = (newest or {}).get("verdict")
    if result == "inconclusive" or status in REJECTED:
        return None
    if result == "pass":
        return None if last == "pass" else "pass"
    if status not in FIX_CLAIMED and last != "pass":
        return None   # filed and failing: we said that when we filed it
    if last == "fail" and not (fixed_at and str(fixed_at) > str((newest or {}).get("at") or "")):
        return None
    return "fail"


def _preview(text, width: int = 90) -> str:
    flat = " ".join(str(text or "").split())
    return flat if len(flat) <= width else flat[: width - 1] + "…"


def inbound(events: list[dict]) -> list[dict]:
    """Every event that is THEM speaking, on any channel, oldest first."""
    out = []
    for event in events:
        kind = event.get("type")
        if kind == "message" and event.get("by") == "vendor":
            out.append({
                "channel": A2A, "at": event.get("at"), "id": event.get("msg_id"),
                "auto": True if event.get("auto") else (False if event.get("kind") else None),
                "kind": event.get("kind"), "answers": event.get("reply_to"),
                "preview": _preview(event.get("text")),
            })
        elif kind == "telegram_reply":
            out.append({
                "channel": TELEGRAM, "at": event.get("at"), "id": event.get("msg_id"), "auto": False,
                "kind": "human", "answers": event.get("reply_to"), "preview": _preview(event.get("text")),
            })
        elif kind == "vendor_status":
            out.append({
                "channel": BUG, "at": event.get("at"), "id": f"#{event.get('report_id')}:{event.get('status')}",
                "auto": False, "kind": "status", "answers": event.get("report_id"),
                "preview": f"#{event.get('report_id')} is now {event.get('status')}",
            })
    out.sort(key=lambda row: str(row["at"] or ""))
    return out


def pairs(events: list[dict]) -> list[dict]:
    """Each a2a question of ours beside their first REAL answer to it. The automated first pass is a receipt.

    Their `reply_to` names a message of OURS, with THEIR id for it. Where no a2a_intent exists (a send made by
    hand), that name is the only record the question was asked at all, so it counts as a question too."""
    ours, theirs = {}, []
    for event in events:
        kind = event.get("type")
        if kind == "a2a_outcome" and event.get("via"):
            ours[str(event["via"])] = event.get("msg_id")
        elif kind == "message" and event.get("by") == "vendor":
            real = not event.get("auto") and event.get("kind") != "first_pass"
            theirs.append((event, real))
    for event, _ in theirs:
        answered = event.get("reply_to")
        if answered and str(answered) not in ours:
            ours[str(answered)] = str(answered)
    answered = {str(event.get("reply_to")) for event, real in theirs if real and event.get("reply_to")}
    return [{"question_id": question, "answered": their_id in answered} for their_id, question in ours.items()]


def labels(events: list[dict]) -> dict[str, str]:
    """Their id for a message of ours: `MSG-0003 (ET-22498)`, because ET-22498 is what the operator says."""
    return {str(e.get("msg_id")): str(e["via"]) for e in events if e.get("type") == "telegram_sent" and e.get("via")}


def _telegram(events: list[dict]) -> dict:
    replied = {e.get("reply_to") for e in events if e.get("type") == "telegram_reply"}
    sent = [e.get("msg_id") for e in events if e.get("type") == "telegram_sent"]
    return {"unanswered": [m for m in sent if m not in replied], "threads": len(sent)}


def _a2a(events: list[dict]) -> dict:
    rows = pairs(events)
    outcome = {e.get("msg_id"): e.get("outcome") for e in events if e.get("type") == "a2a_outcome"}
    sent = [e.get("msg_id") for e in events if e.get("type") == "a2a_intent"]
    return {"unanswered": [r["question_id"] for r in rows if not r["answered"]], "threads": len(rows),
            "undelivered": [m for m in sent if outcome.get(m) != "accepted"]}


def _bug(events: list[dict]) -> dict:
    """Reports a verdict is owed on, by the status the journal last got and the check's last word. A row held for
    the operator's word waits on him, not on us."""
    status = {e.get("report_id"): e.get("status") for e in events if e.get("type") == "vendor_status"}
    owed, filed = [], 0
    for row in load_filed()["rows"]:
        if row.get("withdrawn"):
            continue
        for report_id in row.get("report_ids") or []:
            filed += 1
            now = status.get(report_id) or (row.get("their_status") or {}).get(str(report_id))
            last = last_verdict(row, report_id)
            if not row.get("hold") and decide(row.get("last_check") or "inconclusive", now,
                                              {"verdict": last} if last else None, None):
                owed.append(f"#{report_id}")
    return {"unanswered": sorted(set(owed)), "reports": filed}


def state(events: list[dict] | None = None) -> dict:
    """The channels in one shape, so a report cannot quietly omit one."""
    events = read_events() if events is None else events
    heard = inbound(events)
    last = {}
    for row in heard:
        last[row["channel"]] = row["at"]
    out = {BUG: _bug(events), TELEGRAM: _telegram(events), A2A: _a2a(events)}
    waiting = {BUG: "us", TELEGRAM: "them", A2A: "them"}
    for name, channel in out.items():
        channel["last_from_them"] = last.get(name)
        channel["heard"] = sum(1 for row in heard if row["channel"] == name)
        channel["waiting_on"] = waiting[name]
    return out
