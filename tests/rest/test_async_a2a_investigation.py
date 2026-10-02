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
go green). Fewer than three due messages is inconclusive, and so is a
message whose only candidate answer names no parent: the card does not
promise that a reply names its parent, so it cannot be paired and is not a
miss (deep pass 2026-09-30, C02).

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
INBOX_LIMIT = 200  # their maximum: 422 above it; the default page is the 50 newest
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
               due_after: timedelta = DUE_AFTER, window: int = WINDOW,
               oldest: datetime | None = None):
    """(the messages judged, those with no investigation reply in time, those
    that cannot be told).

    `sent`: {"id", "at"}; `replies`: {"reply_to", "at", "auto", "kind"}. An
    investigation is `kind: "deep"` -- which they ALSO mark `auto: true`,
    since NEXUS writes it (deep pass 2026-09-27, R01, 3/3: every deep reply
    was read as the first pass) -- or a reply that is not automatic. A reply
    whose `auto` is None was not classified by them and is not counted as
    automatic; `first_pass` and `deep_failed` are not investigations.

    A reply with `reply_to` None names no parent (deep pass 2026-09-30, C02,
    3/3: six deep replies came back so on 2026-09-26). It cannot be paired,
    so a message with no reply of its own but such an investigation in its
    window is unsure, never missing.

    `oldest` is the time of the oldest message the inbox page returned (NEXT
    2026-10-01: the inbox gave only the 50 newest without a `limit`). A message
    sent before it has no reply on the page and may have had one on a page we
    did not read: unsure, never missing. A reply that IS on the page still
    answers it."""
    due = sorted((s for s in sent if now - s["at"] >= due_after),
                 key=lambda s: s["at"])[-window:]

    def in_time(r, s) -> bool:
        # `first_pass` and `deep_failed` are never investigations, whatever `auto` says
        # (deep pass 2026-10-02, T06: a reply of that kind with no `auto` key was counted
        # because only `auto is True` excluded one, against this function's own docstring).
        return (r["at"] is not None
                and r.get("kind") not in ("first_pass", "deep_failed")
                and (r.get("kind") == "deep" or r["auto"] is not True)
                and timedelta(0) <= r["at"] - s["at"] <= due_after)

    missing, unsure = [], []
    for s in due:
        if any(r["reply_to"] == s["id"] and in_time(r, s) for r in replies):
            continue
        if oldest is not None and s["at"] < oldest:
            unsure.append(s)
        elif any(r["reply_to"] is None and in_time(r, s) for r in replies):
            unsure.append(s)
        else:
            missing.append(s)
    return due, missing, unsure


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
                             params={"unread_only": "false", "limit": INBOX_LIMIT})
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
        replies.append({"reply_to": str(parent) if parent else None,
                        "at": _moment(m.get("created_at")),
                        "auto": meta.get("auto") if "auto" in meta else None,
                        "kind": meta.get("kind")})

    now = datetime.now(timezone.utc)
    # Without a limit the page holds the 50 newest; a full page may have cut
    # older messages off. What it cannot show is unsure, never missing.
    stamps = [r["at"] for r in replies if r["at"] is not None]
    oldest = min(stamps) if len(messages) >= INBOX_LIMIT and stamps else None
    judged, missing, unsure = unanswered(_our_sends(), replies, now, oldest=oldest)
    if len(judged) < MIN_JUDGED:
        raise Inconclusive(f"{len(judged)} async message(s) of ours are due "
                           f"(sent over {DUE_AFTER} ago); {MIN_JUDGED} are needed")
    names = lambda rows: ", ".join(f"{s.get('ours') or s['id']} ({s['at']:%d.%m %H:%M} UTC)"
                                   for s in rows)
    if missing:
        verdict = "failed"
        # Only a message with no investigation in its window at all, paired
        # or not: one naming no parent may be its answer (C02, 2026-09-30).
        reason = (f"{len(missing)} of our {len(judged)} newest due async messages "
                  f"got no investigation reply within {DUE_AFTER}, paired to them "
                  f"or naming no parent (the card promises 1-10 minutes): "
                  f"{names(missing)}")
    elif unsure:
        raise Inconclusive(
            f"{len(unsure)} of our {len(judged)} newest due async messages have "
            f"no reply paired to them, but an investigation naming no parent "
            f"arrived within {DUE_AFTER} of each and may be theirs: {names(unsure)}")
    else:
        verdict = "passed"
        reason = (f"each of our {len(judged)} newest due async messages got a "
                  f"reply beyond the first pass within {DUE_AFTER}: {names(judged)}")
    conclude(Measurement(
        verdict=verdict, reason=reason,
        left={"judged": len(judged), "without_investigation": len(missing)},
        right={"without_investigation": 0},
        population={"inbox_messages": len(messages),
                    "replies_paired": sum(1 for r in replies if r["reply_to"]),
                    "replies_unparented": sum(1 for r in replies if not r["reply_to"]),
                    "judged": [s.get("ours") for s in judged]},
        sources={"inbox": INBOX, "ours": "state/journal/events.jsonl (a2a_outcome)",
                 "promise": "/.well-known/agent-card.json communication_guide.async_endpoint"},
        claim_id="async-a2a-investigation-arrives"))
