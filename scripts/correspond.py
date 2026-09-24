"""The Telegram conversation, as a record with ids.

Ticket ET-22498 set off the whole 2026-09-07 walk of /build. Three reports came
out of it. What we asked in it exists nowhere: `git log -S "ET-22498"` finds the
string in a comment in outbox/reports.yaml and a line in DEEP-PASS.md, and the
text itself died with the session that wrote it. The bounty API is recorded down
to the last first-pass auto-reply; Telegram was not recorded at all.

Two commands write, two read:

    python scripts/correspond.py sent --text-file msg.md --via ET-22498
    python scripts/correspond.py reply --to MSG-0003 --text-file answer.md
    python scripts/correspond.py list
    python scripts/correspond.py show ET-22498

What this is NOT. These events move neither axis and the fold does not read
them: a chat with the vendor is not a filing on a report, and the display state
of a finding must stay traceable to a run or to the bounty API. `--findings` is
accepted so `show` can say which rows a message was about, and is deliberately
advisory -- if a later session wires it into qa/fold.py, the states it produces
will be ones no run and no report can account for.

The operator confirms; nothing here guesses. A message they forget to confirm
leaves no trace at all, which is their decision, made on 2026-09-08 when asked
whether an unsent draft should be stored. It should not.
"""

from __future__ import annotations

import argparse
import difflib
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa.console import printable  # noqa: E402
from qa.state import append_event, journal_path, read_events  # noqa: E402

SOURCE = "scripts/correspond.py"
CHANNEL = "telegram"

# [operator 2026-09-13] every message we draft for them opens with our handle,
# because they paste what we write verbatim and an answer has to land on us.
HANDLE = "@EventTraderQABot"


def opens_with_handle(text: str) -> bool:
    """Whether a message OPENS with our handle, not whether it mentions it.

    A report that names the bot three paragraphs down is not a message
    addressed to us, so the check is anchored at the start. Leading
    whitespace is forgiven; anything else before it is not.
    """
    return str(text or "").lstrip().lower().startswith(HANDLE.lower())

# Ids are allocated over EVERY event, whatever its type: MSG-0000..0002 and
# REPLY-0001 are already taken by round one, migrated in as `message`/`reply`.
# The natural key would let a telegram_sent reuse MSG-0001 without complaint,
# and then two different things answer to one id in a journal that cannot be
# rewritten.
ID_PATTERN = re.compile(r"^(MSG|REPLY)-(\d{4})$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------
def next_msg_id(events: list[dict], prefix: str) -> str:
    highest = 0
    for event in events:
        matched = ID_PATTERN.match(str(event.get("msg_id") or ""))
        if matched and matched.group(1) == prefix:
            highest = max(highest, int(matched.group(2)))
    return f"{prefix}-{highest + 1:04d}"


def threads(events: list[dict]) -> dict[str, dict]:
    """Every message we sent, with the answers that name it, in journal order."""
    out: dict[str, dict] = {}
    for event in events:
        if event.get("type") == "telegram_sent":
            out[event["msg_id"]] = {"msg_id": event["msg_id"], "sent": event,
                                    "replies": []}
    for event in events:
        if event.get("type") == "telegram_reply":
            thread = out.get(event.get("reply_to"))
            if thread is not None:
                thread["replies"].append(event)
    return out


def orphan_replies(events: list[dict]) -> list[dict]:
    """Answers pointing at a message that is not there.

    `reply` refuses an unknown target, so these can only come from a hand-built
    event -- but dropping them silently is how a record starts lying, and this
    one exists because the last one did.
    """
    known = set(threads(events))
    return [e for e in events
            if e.get("type") == "telegram_reply" and e.get("reply_to") not in known]


def open_threads(events: list[dict]) -> list[dict]:
    return [t for t in threads(events).values() if not t["replies"]]


def match(events: list[dict], query: str) -> list[dict]:
    """Find a thread by our id, their ticket, or something that was said in it.

    Their id is the one that matters. The operator says "odpovedeli na
    ET-22498"; a lookup that only knows MSG-0003 sends them off to find our id
    first, which is the same as not having the record.
    """
    needle = query.strip().lower()
    if not needle:
        return []
    found = []
    for thread in threads(events).values():
        hay = [thread["msg_id"]]
        for event in (thread["sent"], *thread["replies"]):
            hay += [str(event.get("msg_id") or ""), str(event.get("via") or ""),
                    str(event.get("text") or ""), str(event.get("note") or "")]
        if any(needle in piece.lower() for piece in hay):
            found.append(thread)
    return found


def _age(at: str) -> str:
    try:
        then = datetime.fromisoformat(str(at))
    except ValueError:
        return ""
    if then.tzinfo is None:
        then = then.replace(tzinfo=timezone.utc)
    days = (datetime.now(timezone.utc) - then).days
    if days <= 0:
        return "today"
    return f"{days} day" if days == 1 else f"{days} days"


def summarise(thread: dict, width: int = 80) -> str:
    """One line: our id, their ticket, how old, and the first words of it."""
    sent = thread["sent"]
    marks = [thread["msg_id"]]
    if sent.get("via"):
        marks.append(str(sent["via"]))
    age = _age(sent.get("at", ""))
    if age:
        marks.append(age)
    text = " ".join(str(sent.get("text") or "").split())
    if len(text) > width:
        text = text[: width - 1] + "…"
    return f"{', '.join(marks)}  \"{text}\""


# ---------------------------------------------------------------------------
# Writing
# ---------------------------------------------------------------------------
def _text_from(args) -> str:
    """--text or --text-file.

    --text-file exists because this workspace is Windows and the shell is not:
    multi-line Czech through a quoted argument is a lottery, and CLAUDE.md
    forbids bash heredocs for content here after one silently corrupted a file.
    """
    if args.text_file:
        return Path(args.text_file).read_text(encoding="utf-8")
    return args.text or ""


def _append_or_die(event: dict) -> None:
    """`duplicate` is an error on this path, not idempotence.

    Everywhere else a repeated event is the same fact arriving twice. Here it is
    a message the operator was told was recorded and was not.
    """
    outcome = append_event(event)
    if outcome != "appended":
        raise SystemExit(
            f"refusing: {event['type']} {event['msg_id']} is already on the "
            f"journal, so this text would be dropped rather than stored.\n"
            f"  read it with: python scripts/correspond.py show {event['msg_id']}"
        )


def cmd_sent(args) -> int:
    events = read_events()
    text = _text_from(args)
    if not text.strip():
        raise SystemExit("refusing to record a message with no text.")

    event = {"type": "telegram_sent", "at": args.at or _now(), "by": "operator",
             "source": SOURCE, "msg_id": next_msg_id(events, "MSG"),
             "text": text, "origin": CHANNEL}
    if args.via:
        event["via"] = args.via
    if args.note:
        event["note"] = args.note
    if args.findings:
        event["findings"] = [f.strip() for f in args.findings.split(",") if f.strip()]
    _append_or_die(event)

    print(f"recorded as {event['msg_id']}"
          + (f" (their ref {event['via']})" if event.get("via") else ""))
    print(f"  journal  {journal_path()}")
    print("  the fold does not read this; there is nothing to re-fold")
    if not opens_with_handle(text):
        # Recorded regardless: this command records what the operator has
        # ALREADY sent, and a journal tidied to match the rule would no
        # longer match the thread. The notice is for the next message.
        print(f"  NOTE: this message does not open with {HANDLE}, which is "
              f"what [operator 2026-09-13] asks of every message we draft. "
              f"Recorded as sent, because it was.")
    # [operator 2026-09-24] in the channels skill: every Telegram message
    # has an a2a twin, until they revoke it. Printed here because this is the
    # one step every session takes when a message went out.
    print("  NOW its a2a twin, same text: python scripts/a2a.py send "
          "--text-file <the same file> --confirm")
    return 0


def cmd_reply(args) -> int:
    events = read_events()
    known = sorted(threads(events))
    if args.to not in known:
        close = difflib.get_close_matches(args.to, known, n=3, cutoff=0.3)
        hint = f"\n  did you mean: {', '.join(close)}" if close else ""
        listed = ", ".join(known[-10:]) if known else "none yet"
        raise SystemExit(
            f"no message {args.to!r} was ever recorded as sent, so this answer "
            f"would hang off nothing.{hint}\n  recorded: {listed}"
        )

    text = _text_from(args)
    if not text.strip():
        raise SystemExit("refusing to record a reply with no text.")

    event = {"type": "telegram_reply", "at": args.at or _now(), "by": "vendor",
             "source": SOURCE, "msg_id": next_msg_id(events, "REPLY"),
             "reply_to": args.to, "text": text, "origin": CHANNEL}
    if args.via:
        event["via"] = args.via
    if args.note:
        event["note"] = args.note
    _append_or_die(event)

    print(f"recorded as {event['msg_id']}, answering {args.to}")
    print(f"  journal  {journal_path()}")
    print("  the fold does not read this; there is nothing to re-fold")
    return 0


def cmd_list(args) -> int:
    events = read_events()
    every = list(threads(events).values())
    unanswered = [t for t in every if not t["replies"]]
    answered = [t for t in every if t["replies"]]

    if not every:
        print("no telegram correspondence recorded")
    if unanswered:
        print(f"unanswered ({len(unanswered)}):")
        for thread in unanswered:
            print(f"  {summarise(thread)}")
    if answered:
        print(f"answered ({len(answered)}):")
        for thread in answered:
            print(f"  {summarise(thread)} -> {len(thread['replies'])}")
    for stray in orphan_replies(events):
        print(f"  ! {stray['msg_id']} answers {stray.get('reply_to')!r}, "
              f"which was never recorded as sent")
    return 0


def cmd_show(args) -> int:
    events = read_events()
    found = match(events, args.query)
    if not found:
        raise SystemExit(f"nothing recorded matches {args.query!r}")
    for thread in found:
        for event in (thread["sent"], *thread["replies"]):
            who = "we sent" if event["type"] == "telegram_sent" else "they answered"
            marks = [event["msg_id"], event.get("at", "")]
            if event.get("via"):
                marks.append(f"their ref {event['via']}")
            if event.get("findings"):
                marks.append("about " + ", ".join(event["findings"]))
            print(f"--- {who}: {' | '.join(str(m) for m in marks)}")
            print(event.get("text") or "")
            if event.get("note"):
                print(f"[note] {event['note']}")
            print()
    return 0


def main(argv: list[str] | None = None) -> int:
    # The journal is full of their emoji and this is a Czech Windows console.
    # Without this, `show` dies mid-output on a cp1250 UnicodeEncodeError.
    printable()

    parser = argparse.ArgumentParser(prog="correspond.py", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    send = sub.add_parser("sent", help="record a message you have SENT on telegram")
    send.add_argument("--text")
    send.add_argument("--text-file")
    send.add_argument("--via", help="their ticket id, e.g. ET-22498")
    send.add_argument("--findings", help="comma-separated; advisory, never folded")
    send.add_argument("--note")
    # When it was actually sent, not when it was typed in here. Every telegram
    # event recorded before 2026-09-08 carries the moment of recording, with
    # the truth in a note no arithmetic can read -- so a comparison of this
    # channel against a2a had no telegram data at all.
    send.add_argument("--at", help="ISO time it was really sent")

    answer = sub.add_parser("reply", help="record THEIR answer to one of ours")
    answer.add_argument("--to", required=True, help="the MSG-NNNN it answers")
    answer.add_argument("--text")
    answer.add_argument("--text-file")
    answer.add_argument("--via")
    answer.add_argument("--note")
    answer.add_argument("--at", help="ISO time they really answered")

    sub.add_parser("list", help="what is unanswered, then what is answered")

    show = sub.add_parser("show", help="the full text, by our id, theirs, or a word")
    show.add_argument("query")

    args = parser.parse_args(argv)
    return {"sent": cmd_sent, "reply": cmd_reply,
            "list": cmd_list, "show": cmd_show}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
