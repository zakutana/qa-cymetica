"""Build the correspondence ledger: which messages said what about which finding.

Every message to and from the vendor lives as a file -- outbox/ for ours,
inbox/ for theirs, pasted verbatim. This walks both, splits each message into
its sections, and attaches the relevant section to each finding it discusses.

The point is that opening a finding on the dashboard shows the actual words
exchanged about it, not a summary of them. A summary of an artifact is not the
artifact, and that applies to our own summaries too.

    python scripts/thread.py
"""

from __future__ import annotations

import json
import re
import sys
from datetime import date, datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yaml  # noqa: E402

OUTBOX = REPO_ROOT / "outbox"
INBOX = REPO_ROOT / "inbox"
OUT = REPO_ROOT / "state" / "thread.json"

RULE = re.compile(r"^[═─]{10,}$", re.M)


def parse(path: Path) -> dict | None:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        return None
    _, front, body = text.split("---", 2)
    try:
        meta = yaml.safe_load(front) or {}
    except yaml.YAMLError:
        return None
    # PyYAML turns bare ISO timestamps into datetime objects, which do not
    # survive json.dumps. Normalise every scalar back to a string here so the
    # rest of the pipeline only ever sees text.
    for key, value in list(meta.items()):
        if isinstance(value, (datetime, date)):
            meta[key] = value.isoformat()

    meta["body"] = body.strip()
    try:
        meta["file"] = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
    except ValueError:
        meta["file"] = str(path).replace("\\", "/")
    return meta


def ingest(dirs) -> int:
    """Turn every message file into exactly one journal event.

    thread.py used to rebuild the correspondence by scanning directories on
    every run, with `delivered` defaulting to True. Both consequences
    happened: moving a message into archive/ deleted a vendor reply and three
    reported findings from the record, and every outbound message claimed to
    have been delivered whether or not anybody had sent it.

    A message is now an EVENT, keyed by its frontmatter id. Where the file
    sits afterwards is filing, not evidence -- ingesting the archive adds
    nothing, because the event is already there.

    Delivery is a claim somebody made. It is true only when the message says
    `delivered: true`, or when a reply refers to it -- which is the one
    receipt this channel actually produces.
    """
    from qa.state import append_event

    messages = []
    for directory in dirs:
        directory = Path(directory)
        if not directory.exists():
            continue
        for path in sorted(directory.glob("*.md")):
            meta = parse(path)
            if meta is not None:
                messages.append(meta)

    acknowledged = {m.get("reply_to") for m in messages if m.get("reply_to")}

    added = 0
    for meta in sorted(messages, key=lambda m: (
            str(m.get("sent_at") or m.get("received_at") or ""),
            str(m.get("id") or ""))):
        msg_id = meta.get("id")
        if not msg_id:
            continue
        inbound = meta.get("direction") == "in"
        at = meta.get("sent_at") or meta.get("received_at") or meta.get("composed_at")
        if not at:
            at = datetime.fromtimestamp(
                Path(meta["file"]).stat().st_mtime, timezone.utc
            ).isoformat(timespec="seconds")

        event = {
            "type": "reply" if inbound else "message",
            "at": str(at),
            "by": "vendor" if inbound else "operator",
            "source": "scripts/thread.py",
            "msg_id": msg_id,
            "findings": list(meta.get("findings") or []),
            "origin": meta["file"],
        }
        if inbound:
            event["reply_to"] = meta.get("reply_to")
            # Their words, captured verbatim in the file itself.
            event["evidence_id"] = meta.get("evidence_id") or f"inbox:{msg_id}"
        else:
            event["delivered"] = bool(
                meta.get("delivered") is True or msg_id in acknowledged)

        if append_event(event) == "appended":
            added += 1
    return added


# Only TOP-LEVEL headings start a new block. Sub-headings inside a section --
# OBSERVED, CHECK, SCOPE, WHY THIS IS NOT COSMETIC -- are part of the finding's
# argument and must travel with it, or the excerpt attached to a finding is a
# title with nothing under it.
TOP_HEADING = re.compile(r"^\d+\.\s+[A-Z]")
STANDALONE = (
    "ASKS",
    "WHAT I WILL DO WITH YOUR ANSWERS",
    "SCOPE OF THIS REQUEST",
)


def is_heading(line: str) -> bool:
    stripped = line.strip()
    if not stripped or len(stripped) > 200 or RULE.match(stripped):
        return False
    if TOP_HEADING.match(stripped):
        return True
    return any(stripped.upper().startswith(s) for s in STANDALONE)


def blocks(body: str) -> list[tuple[str, str]]:
    """Split a message into (heading, text) blocks."""
    out: list[tuple[str, str]] = []
    heading = ""
    buffer: list[str] = []

    for line in body.splitlines():
        if RULE.match(line.strip()):
            continue
        if is_heading(line):
            if heading or buffer:
                out.append((heading, "\n".join(buffer).strip()))
            heading = line.strip()
            buffer = []
        else:
            buffer.append(line)

    if heading or buffer:
        out.append((heading, "\n".join(buffer).strip()))
    return [(h, t) for h, t in out if h or t]


def build() -> dict:
    messages: list[dict] = []

    for folder, direction in ((OUTBOX, "out"), (INBOX, "in")):
        if not folder.exists():
            continue
        for path in sorted(folder.glob("*.md")):
            meta = parse(path)
            if meta is None:
                continue
            messages.append({
                "id": meta.get("id", path.stem),
                "direction": meta.get("direction", direction),
                "channel": meta.get("channel", "telegram"),
                "at": meta.get("sent_at") or meta.get("received_at"),
                "composed_at": meta.get("composed_at"),
                "delivered_as": meta.get("delivered_as"),
                "delivered": meta.get("delivered", True),
                "delivery_note": meta.get("delivery_note"),
                "reply_to": meta.get("reply_to"),
                "file": meta["file"],
                "findings": meta.get("findings", []) or [],
                "covers": meta.get("covers", {}) or {},
                "body": meta["body"],
                "blocks": blocks(meta["body"]),
                "chars": len(meta["body"]),
            })

    messages.sort(key=lambda m: (m["at"] or m["composed_at"] or "", m["id"]))

    by_finding: dict[str, list[dict]] = {}
    for message in messages:
        # covers maps a heading substring -> the finding ids that block discusses.
        matched: dict[str, list[str]] = {}
        for needle, ids in message["covers"].items():
            ids = ids if isinstance(ids, list) else [ids]
            for heading, text in message["blocks"]:
                if needle.lower() in heading.lower():
                    for fid in ids:
                        matched.setdefault(fid, []).append(f"{heading}\n\n{text}".strip())

        # Findings named in frontmatter but not mapped to a block still get the
        # message recorded -- with no excerpt rather than a wrong one.
        for fid in message["findings"]:
            matched.setdefault(fid, [])

        for fid, excerpts in matched.items():
            by_finding.setdefault(fid, []).append({
                "msg_id": message["id"],
                "direction": message["direction"],
                "channel": message["channel"],
                "at": message["at"],
                "delivered_as": message["delivered_as"],
                "delivered": message["delivered"],
                "delivery_note": message["delivery_note"],
                "file": message["file"],
                "excerpt": "\n\n".join(excerpts) if excerpts else None,
                "excerpt_missing_reason": None if excerpts else
                    "listed on the message but not mapped to a section",
            })

    for entries in by_finding.values():
        entries.sort(key=lambda e: e["at"] or "")

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "messages": [
            {k: v for k, v in m.items() if k != "blocks"} for m in messages
        ],
        "by_finding": by_finding,
        "counts": {
            "sent": sum(1 for m in messages if m["direction"] == "out"),
            "received": sum(1 for m in messages if m["direction"] == "in"),
            "awaiting_reply": sum(
                1 for m in messages if m["direction"] == "out" and m["at"]
            ) - sum(1 for m in messages if m["direction"] == "in"),
        },
    }


if __name__ == "__main__":
    data = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"-> {OUT.relative_to(REPO_ROOT)}")
    print(f"   {data['counts']['sent']} sent, {data['counts']['received']} received")
    for message in data["messages"]:
        state = "sent " + message["at"][:16] if message["at"] else "DRAFT (not sent)"
        print(f"   {message['direction']:>3}  {message['id']:<12} {state:<28} "
              f"{message['chars']:>6} chars")
    unmapped = [
        (fid, e["msg_id"]) for fid, entries in data["by_finding"].items()
        for e in entries if e["excerpt_missing_reason"]
    ]
    if unmapped:
        print(f"   {len(unmapped)} finding/message pairs have no excerpt "
              f"(add a covers: entry to the message frontmatter)")
