"""The async a2a lane delivers the investigation its agent card promises.

THE CONTRACT. /.well-known/agent-card.json, `communication_guide.async_endpoint`
(read 2026-09-26): POST /api/v1/bounty/a2a/send, "response_time": "1-10
minutes (NEXUS investigates source code, DB, or on-chain state)", polled at
GET /api/v1/bounty/a2a/inbox/{agent_id}. And every automatic first pass the
lane sends ends: "Your message remains queued for review; any deeper
investigation reply is posted to this same inbox".

WHAT WAS SEEN (2026-09-26, MSG-0075): since 24 Sep one of our ten a2a
messages got a reply beyond the automatic first pass (A2A-0006, 44 min
later). The six sent 07:25-09:38 UTC that day had only the first pass after
two to four hours, and the first pass was off-topic -- a question about
build paths got the Gem Screener product blurb.

WHAT IS READ. Our own sends from the journal (`a2a_intent` / `a2a_outcome`,
accepted, their server id in `via`) -- what we asked and when, which only we
know -- and their replies from the live inbox, paired by
`parent_message_id` (or `metadata.in_reply_to`), the way scripts/bounty.py
pairs them.

WHAT IT ASSERTS. Each of the newest five messages that are due got a reply
that is not automatic (`metadata.auto` is not true) within an hour. An hour is
six times their ten minutes: slack, not the promise. The newest five, not
every one ever sent, so a fix clears it (a check over a growing log can never
go green). Fewer than three due messages is inconclusive.

SAFE: one GET. It sends nothing; the messages are the ones the operator had
us send.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

INBOX = "/api/v1/bounty/a2a/inbox/{agent_id}"
AGENT_ID = "expire76-qa"
JOURNAL = Path(__file__).resolve().parents[2] / "state" / "journal" / "events.jsonl"
DUE_AFTER = timedelta(hours=1)
WINDOW = 5
MIN_JUDGED = 3


def _moment(value):
    try:
        when = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        return None
    return when if when.tzinfo else when.replace(tzinfo=timezone.utc)


def unanswered(sent: list[dict], replies: list[dict], now: datetime,
               due_after: timedelta = DUE_AFTER, window: int = WINDOW):
    """(the messages judged, those with no non-automatic reply in time).

    `sent`: {"id", "at"}; `replies`: {"reply_to", "at", "auto"}. A reply
    whose `auto` is None was not classified by them and is not counted as
    automatic."""
    due = sorted((s for s in sent if now - s["at"] >= due_after),
                 key=lambda s: s["at"])[-window:]
    missing = []
    for s in due:
        if not any(r["reply_to"] == s["id"] and r["auto"] is not True
                   and r["at"] is not None
                   and timedelta(0) <= r["at"] - s["at"] <= due_after
                   for r in replies):
            missing.append(s)
    return due, missing


def _our_sends() -> list[dict]:
    rows = [json.loads(line) for line in JOURNAL.read_text(encoding="utf-8").splitlines()
            if line.strip()]
    out = []
    for row in rows:
        if (row.get("type") == "a2a_outcome" and row.get("outcome") == "accepted"
                and row.get("via")):
            when = _moment(row.get("server_created_at") or row.get("at"))
            if when:
                out.append({"id": str(row["via"]), "ours": row.get("msg_id"), "at": when})
    return out


@qa(component="rest.support", tier=SafetyTier.SAFE, surface="rest",
    claim="async-a2a-investigation-arrives")
def test_an_async_message_gets_the_investigation_its_card_promises(rest_trusted):
    """Each recent async message gets more than the automatic first pass."""
    inbox = rest_trusted.get(INBOX.format(agent_id=AGENT_ID),
                             params={"unread_only": "false"})
    if inbox.status_code != 200:
        raise Inconclusive(f"the inbox answered HTTP {inbox.status_code}; "
                           f"a failed read is not an empty inbox")
    try:
        messages = inbox.json().get("messages") or []
    except ValueError:
        raise Inconclusive("the inbox answered 200 with a body that is not JSON")

    replies = []
    for m in messages:
        meta = m.get("metadata") or {}
        parent = m.get("parent_message_id") or meta.get("in_reply_to")
        if parent:
            replies.append({"reply_to": str(parent), "at": _moment(m.get("created_at")),
                            "auto": meta.get("auto") if "auto" in meta else None})

    now = datetime.now(timezone.utc)
    judged, missing = unanswered(_our_sends(), replies, now)
    if len(judged) < MIN_JUDGED:
        raise Inconclusive(f"{len(judged)} async message(s) of ours are due "
                           f"(sent over {DUE_AFTER} ago); {MIN_JUDGED} are needed")
    names = lambda rows: ", ".join(f"{s.get('ours') or s['id']} ({s['at']:%d.%m %H:%M} UTC)"
                                   for s in rows)
    if missing:
        verdict = "failed"
        reason = (f"{len(missing)} of our {len(judged)} newest due async messages "
                  f"got nothing but the automatic first pass within {DUE_AFTER} "
                  f"(the card promises 1-10 minutes): {names(missing)}")
    else:
        verdict = "passed"
        reason = (f"each of our {len(judged)} newest due async messages got a "
                  f"reply beyond the first pass within {DUE_AFTER}: {names(judged)}")
    conclude(Measurement(
        verdict=verdict, reason=reason,
        left={"judged": len(judged), "without_investigation": len(missing)},
        right={"without_investigation": 0},
        population={"inbox_messages": len(messages), "replies_paired": len(replies),
                    "judged": [s.get("ours") for s in judged]},
        sources={"inbox": INBOX, "ours": "state/journal/events.jsonl (a2a_outcome)",
                 "promise": "/.well-known/agent-card.json communication_guide.async_endpoint"},
        claim_id="async-a2a-investigation-arrives"))
