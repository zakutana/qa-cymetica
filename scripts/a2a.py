"""The a2a channel, from our side of it.

Until 2026-09-08 nothing in scripts/ had ever sent an a2a message. The only
sender in the repository was one check posting one fixed sentence, so the long
question of 2026-09-07 19:32 -- the one that got them to route a2a to a human,
and produced three reports -- exists nowhere and cannot be read back. Their
answer is on the journal. Ours is not, and never was.

    python scripts/a2a.py send --text-file q.md          compose, send nothing
    python scripts/a2a.py send --text-file q.md --confirm
    python scripts/a2a.py list
    python scripts/a2a.py show ET-22498

`--confirm` is the operator's condition, stated on 2026-09-08 when they were
asked whether this should be able to send on its own: yes, but only when they
say so in the moment. Without it the message is composed, printed and dropped.
Nothing is written to the journal either -- an intent recorded for a message
that never left would have the journal claim we asked them something we did
not.

Two events per send, and keyed on OUR id rather than theirs. That is rule 9,
and the reason is the case the record exists for: a POST that times out has no
server id, and the text must survive it. `unknown` is settled by a later read
of the inbox, never by editing.

Reading their side is `scripts/bounty.py fetch_inbox`, which this does not
duplicate: `list` and `show` read the journal that the inbox read fills.
"""

from __future__ import annotations

import argparse
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa.client import build_client, install_client_guard  # noqa: E402
from qa.console import printable  # noqa: E402
from qa.config import identities, load_dotenv  # noqa: E402
from qa.crew import crew_brake  # noqa: E402
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier  # noqa: E402
from qa.state import append_event, journal_path, read_events  # noqa: E402

SOURCE = "scripts/a2a.py"
CHANNEL = "a2a"
SEND = "/api/v1/bounty/a2a/send"
AGENT_ID = "expire76-qa"

# Ours are numbered, theirs are hex, and both live in msg_id. Allocated over
# EVERY event for the reason correspond.py gives: two things answering to one
# id cannot be untangled in a journal that is append-only.
OUR_ID = re.compile(r"^A2A-(\d{4})$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def next_a2a_id(events: list[dict]) -> str:
    highest = 0
    for event in events:
        matched = OUR_ID.match(str(event.get("msg_id") or ""))
        if matched:
            highest = max(highest, int(matched.group(1)))
    return f"A2A-{highest + 1:04d}"


# ---------------------------------------------------------------------------
# Reading
# ---------------------------------------------------------------------------
def threads(events: list[dict]) -> dict[str, dict]:
    """What we sent, what became of it, and what they said back."""
    out: dict[str, dict] = {}
    for event in events:
        if event.get("type") == "a2a_intent":
            out[event["msg_id"]] = {"msg_id": event["msg_id"], "sent": event,
                                    "outcomes": [], "replies": []}
    for event in events:
        if event.get("type") == "a2a_outcome":
            thread = out.get(event.get("msg_id"))
            if thread is not None:
                thread["outcomes"].append(event)
    # Their reply names the id THEY gave our message, so the pairing runs
    # through the accepted outcome rather than through our own id.
    theirs = {o["via"]: t for t in out.values() for o in t["outcomes"] if o.get("via")}
    for event in events:
        if event.get("type") == "message" and event.get("origin") == "a2a":
            thread = theirs.get(event.get("reply_to"))
            if thread is not None:
                thread["replies"].append(event)
    return out


def delivery(thread: dict) -> str:
    """accepted, unknown, or refused -- the newest word on whether it landed."""
    if not thread["outcomes"]:
        return "unknown"
    return thread["outcomes"][-1].get("outcome") or "unknown"


def open_threads(events: list[dict]) -> list[dict]:
    return [t for t in threads(events).values() if not t["replies"]]


def match(events: list[dict], query: str) -> list[dict]:
    needle = query.strip().lower()
    if not needle:
        return []
    found = []
    for thread in threads(events).values():
        hay = [thread["msg_id"], str(thread["sent"].get("text") or "")]
        for outcome in thread["outcomes"]:
            hay.append(str(outcome.get("via") or ""))
        for reply in thread["replies"]:
            hay += [str(reply.get("msg_id") or ""), str(reply.get("text") or "")]
        if any(needle in piece.lower() for piece in hay):
            found.append(thread)
    return found


# ---------------------------------------------------------------------------
# Sending
# ---------------------------------------------------------------------------
def _client_for():
    """A real client. Replaced wholesale in tests, so nothing here is mocked."""
    load_dotenv()
    ids = identities()
    return build_client(ids["trusted"] if ids["trusted"].present else ids["anon"],
                        EndpointRegistry.load(), timeout=60.0)


def _capture(response) -> str | None:
    from qa.evidence import EvidenceStore

    try:
        return EvidenceStore("script-a2a").capture(
            response.request, response, SafetyTier.PROBE)
    except Exception:  # noqa: BLE001
        return None


def _text_from(args) -> str:
    if args.text_file:
        return Path(args.text_file).read_text(encoding="utf-8")
    return args.text or ""


def cmd_send(args) -> int:
    text = _text_from(args)
    if not text.strip():
        raise SystemExit("refusing to send a message with no text.")

    if not args.confirm:
        # Nothing on the journal either. An intent for a message that never
        # left would have the record claim we asked them something we did not.
        print("composed, NOT sent (no --confirm):")
        print(text.rstrip())
        print("\n  send it with the same command plus --confirm")
        return 0

    events = read_events()
    # The company's brake (docs/crew-plan.md): a worker sends at most three an hour. Not
    # applied to a session -- the operator's own sends are theirs.
    braked = crew_brake("a2a", events)
    if braked:
        print(f"refused, nothing sent: {braked}")
        return 2
    msg_id = next_a2a_id(events)
    at = _now()
    append_event({"type": "a2a_intent", "at": at, "by": "operator",
                  "source": SOURCE, "msg_id": msg_id, "text": text,
                  "origin": CHANNEL})

    payload = {"from_agent_id": AGENT_ID, "content": text}
    client = _client_for()
    token = CURRENT_TIER.set(SafetyTier.PROBE)
    try:
        try:
            response = client.post(SEND, json=payload)
        except Exception as exc:  # noqa: BLE001
            # A timeout does not mean they refused it; it means we stopped
            # listening. The text is already on the journal, which is the whole
            # point of writing the intent first.
            append_event({"type": "a2a_outcome", "at": _now(), "by": "agent",
                          "source": SOURCE, "msg_id": msg_id,
                          "outcome": "unknown",
                          "reason": f"{type(exc).__name__}: {exc} -- settle it "
                                    f"by reading the inbox, never by editing"})
            print(f"{msg_id}: sent, outcome UNKNOWN ({type(exc).__name__}). "
                  f"The text is on the journal.")
            return 1
    finally:
        CURRENT_TIER.reset(token)
        client.close()

    evidence_id = _capture(response)
    try:
        body = response.json()
    except ValueError:
        body = {}
    message = (body or {}).get("message") or {}
    their_id = message.get("id")
    accepted = 200 <= response.status_code < 300 and bool(their_id)

    outcome = {"type": "a2a_outcome", "at": _now(), "by": "agent",
               "source": SOURCE, "msg_id": msg_id,
               "outcome": "accepted" if accepted else "unknown",
               "http_status": response.status_code, "evidence_id": evidence_id}
    if their_id:
        outcome["via"] = str(their_id)
    if message.get("created_at"):
        # Their clock on our send: half of every latency we will ever measure.
        outcome["server_created_at"] = str(message["created_at"])
    append_event(outcome)

    print(f"{msg_id}: {outcome['outcome']} (HTTP {response.status_code})"
          + (f", their id {their_id}" if their_id else ""))
    print(f"  journal  {journal_path()}")
    print("  their answer arrives in the a2a inbox; scripts/bounty.py reads it")
    return 0


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------
def _preview(text: str, width: int = 80) -> str:
    flat = " ".join(str(text or "").split())
    return flat if len(flat) <= width else flat[: width - 1] + "…"


def cmd_list(args) -> int:
    events = read_events()
    every = list(threads(events).values())
    if not every:
        print("nothing has ever been sent on a2a from here")
        return 0
    for thread in every:
        state = delivery(thread)
        answers = len(thread["replies"])
        print(f"  {thread['msg_id']}  {state}, {answers} repl(ies)  "
              f"\"{_preview(thread['sent'].get('text'))}\"")
    return 0


def cmd_show(args) -> int:
    found = match(read_events(), args.query)
    if not found:
        raise SystemExit(f"nothing recorded matches {args.query!r}")
    for thread in found:
        sent = thread["sent"]
        print(f"--- we sent: {thread['msg_id']} | {sent.get('at')} | "
              f"{delivery(thread)}")
        print(sent.get("text") or "")
        print()
        for reply in thread["replies"]:
            mark = "automated" if reply.get("auto") else (reply.get("kind") or "kind unknown")
            print(f"--- they answered: {reply['msg_id']} | {reply.get('at')} | {mark}")
            print(reply.get("text") or "")
            print()
    return 0


def main(argv: list[str] | None = None) -> int:
    printable()

    parser = argparse.ArgumentParser(prog="a2a.py", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    send = sub.add_parser("send", help="ask them something on a2a")
    send.add_argument("--text")
    send.add_argument("--text-file")
    send.add_argument("--confirm", action="store_true",
                      help="actually send it; without this nothing leaves")

    sub.add_parser("list", help="what we sent, and whether it was answered")

    show = sub.add_parser("show", help="the full text, by our id, theirs, or a word")
    show.add_argument("query")

    args = parser.parse_args(argv)
    if args.command == "send" and args.confirm:
        install_client_guard()
    return {"send": cmd_send, "list": cmd_list, "show": cmd_show}[args.command](args)


if __name__ == "__main__":
    raise SystemExit(main())
