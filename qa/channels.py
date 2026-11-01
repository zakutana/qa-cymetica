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
REJECTED = {"invalid", "duplicate", "wontfix"}


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
    return {"unanswered": [r["question_id"] for r in rows if not r["answered"]], "threads": len(rows)}


def _bug() -> dict:
    """Reports where they claim a fix and we have not said it holds."""
    owed, filed = [], 0
    for row in load_filed()["rows"]:
        if row.get("withdrawn"):
            continue
        for report_id in row.get("report_ids") or []:
            filed += 1
            sent = [v for v in row.get("verdicts_sent") or [] if v.get("report_id") == report_id]
            status = str((row.get("their_status") or {}).get(str(report_id)) or "").lower()
            if status == "fixed" and not (sent and sent[-1].get("verdict") == "pass"):
                owed.append(f"#{report_id}")
    return {"unanswered": sorted(set(owed)), "reports": filed}


def state(events: list[dict] | None = None) -> dict:
    """The channels in one shape, so a report cannot quietly omit one."""
    events = read_events() if events is None else events
    heard = inbound(events)
    last = {}
    for row in heard:
        last[row["channel"]] = row["at"]
    out = {BUG: _bug(), TELEGRAM: _telegram(events), A2A: _a2a(events)}
    waiting = {BUG: "us", TELEGRAM: "them", A2A: "them"}
    for name, channel in out.items():
        channel["last_from_them"] = last.get(name)
        channel["heard"] = sum(1 for row in heard if row["channel"] == name)
        channel["waiting_on"] = waiting[name]
    return out
