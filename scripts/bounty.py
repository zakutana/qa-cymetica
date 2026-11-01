"""Read our inbox on the bounty API: their status on each report we filed, and the a2a messages they sent.

Their status is a CLAIM. Only our own re-run of the failing check can say a fix is real (scripts/sweep.py).

    python scripts/bounty.py        refresh state/bounty.json, record what changed, print what is new
"""

from __future__ import annotations

import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa.client import build_client, install_client_guard  # noqa: E402
from qa.config import identities, load_dotenv  # noqa: E402
from qa.console import printable  # noqa: E402
from qa.paths import append_event, file_lock, read_events, state_dir  # noqa: E402
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier  # noqa: E402

SOURCE = "scripts/bounty.py"
A2A_SOURCE = "scripts/bounty.py a2a-inbox"
A2A_INBOX = "/api/v1/bounty/a2a/inbox/{agent_id}"
# `limit` is undocumented; 200 is the most they accept (422 above it).
INBOX_LIMIT = 200

REPORT_FIELDS = (
    "id", "title", "status", "hunter_name", "wallet_address",
    "severity_reported", "severity_confirmed", "category",
    "created_at", "fixed_at", "validated_at", "triaged_at",
    "status_notes", "ticket_url", "fix_pr_url", "reward_amount",
)


def out_path() -> Path:
    return state_dir() / "bounty.json"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _client():
    ids = identities()
    return build_client(ids["trusted"] if ids["trusted"].present else ids["anon"],
                        EndpointRegistry.load(), timeout=60.0)


def classify_read(outcome) -> str:
    """What KIND of read this was. A 401 is a body with no reports in it, byte for byte what a tracker looks
    like when the vendor has closed everything, so the status is read before anything else."""
    if isinstance(outcome, Exception):
        return "unreachable"
    status = outcome.status_code
    if status == 401:
        return "unauthorized"
    if status == 403:
        return "forbidden"
    if status == 404:
        return "not_found"
    if status >= 500:
        return "server_error"
    if not 200 <= status < 300:
        return "malformed"
    try:
        body = outcome.json()
    except ValueError:
        return "malformed"
    return "ok" if isinstance(body, dict) else "malformed"


def fetch_our_reports(client=None, wallet: str | None = None, previous: dict | None = None) -> dict:
    """Our filed reports. GET /bounty/reports is a filtered public view; ours live behind my-reports.

    On anything but a clean read this returns the PREVIOUS snapshot marked stale, never an empty one: "we could
    not look" and "there is nothing there" are different facts. A status that changed goes onto the journal."""
    load_dotenv()
    wallet = wallet or os.environ.get("QA_WALLET_ADDRESS", "")
    at = _now()
    if not wallet:
        return {**(previous or {}), "klass": "unreachable", "error": "QA_WALLET_ADDRESS not set", "stale_from": at}

    owned = client is None
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        client = client or _client()
        try:
            response = client.get("/api/v1/bounty/my-reports", params={"wallet_address": wallet})
            klass, failure = classify_read(response), None
        except Exception as exc:  # noqa: BLE001
            response, klass, failure = None, "unreachable", f"{type(exc).__name__}: {exc}"
        finally:
            if owned:
                client.close()
    finally:
        CURRENT_TIER.reset(token)

    if klass != "ok":
        return {**(previous or {}), "klass": klass, "stale_from": at, **({"error": failure} if failure else {})}

    data = response.json()
    rows = data.get("reports") or data.get("data") or []

    last: dict = {}
    for event in read_events():
        if event.get("type") == "vendor_status" and event.get("report_id") is not None:
            last[event["report_id"]] = event.get("status")
    for report in sorted(rows, key=lambda r: r.get("id", 0)):
        report_id = report.get("id")
        if report_id is None or last.get(report_id) == report.get("status"):
            continue
        append_event({"type": "vendor_status", "at": at, "by": "agent", "source": SOURCE,
                      "report_id": report_id, "status": report.get("status"), "observed_at": at})

    return {"klass": "ok", "read_at": at, "rows_returned": len(rows), "total": data.get("total", len(rows)),
            "statuses": dict(Counter(r.get("status") for r in rows)),
            "reports": [{k: r.get(k) for k in REPORT_FIELDS}
                        for r in sorted(rows, key=lambda r: r.get("id", 0))]}


def refresh_our_reports(client=None) -> dict:
    """Re-read our reports into state/bounty.json. A failed read keeps what the file held, marked stale."""
    out = out_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(out):
        data: dict = {}
        if out.exists():
            try:
                data = json.loads(out.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                data = {}
        ours = fetch_our_reports(client=client, previous=data.get("our_reports"))
        data["our_reports"] = ours
        data["our_reports_refreshed_at"] = _now()
        tmp = out.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, out)
    return ours


def fetch_inbox(client=None, agent_id: str | None = None) -> dict:
    """The a2a inbox, one journal event per message we have not seen. A refused inbox is not an empty one."""
    agent_id = agent_id or os.environ.get("QA_A2A_AGENT_ID", "expire76-qa")
    at = _now()
    owned = client is None
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        client = client or _client()
        try:
            response = client.get(A2A_INBOX.format(agent_id=agent_id),
                                  params={"unread_only": "false", "limit": INBOX_LIMIT})
            klass = classify_read(response)
        except Exception:  # noqa: BLE001
            response, klass = None, "unreachable"
        finally:
            if owned:
                client.close()
    finally:
        CURRENT_TIER.reset(token)

    if klass != "ok":
        return {"klass": klass, "rows_returned": None, "new": [], "at": at}
    data = response.json()
    messages = data.get("messages") or data.get("inbox") or []
    result = record_inbox(messages, klass=klass, at=at)
    # A page of exactly the limit may have cut older messages off.
    result["full"] = len(messages) >= INBOX_LIMIT
    return result


def record_inbox(messages: list[dict], klass: str = "ok", at: str | None = None) -> dict:
    """Their messages onto the journal, once each. A missing `kind` means unknown, never "human" or "robot"."""
    at = at or _now()
    seen = {str(e.get("msg_id")) for e in read_events() if e.get("type") == "message"}
    new: list[dict] = []
    for message in messages:
        msg_id = message.get("id")
        if not msg_id or str(msg_id) in seen:
            continue
        seen.add(str(msg_id))
        metadata = message.get("metadata") or {}
        record = {"type": "message", "at": message.get("created_at") or at, "by": "vendor",
                  "source": A2A_SOURCE, "msg_id": str(msg_id), "text": message.get("content") or "",
                  "origin": "a2a", "via": message.get("thread_id")}
        if "auto" in metadata or "kind" in metadata:
            record["auto"] = bool(metadata.get("auto"))
            record["kind"] = str(metadata["kind"]) if metadata.get("kind") else None
        # Their parent_message_id pairs a question with its answer; the thread id is one value per account.
        answers = message.get("parent_message_id") or metadata.get("in_reply_to")
        if answers:
            record["reply_to"] = str(answers)
        append_event(record)
        new.append({"msg_id": str(msg_id), "at": record["at"], "auto": bool(metadata.get("auto")),
                    "kind": metadata.get("kind"), "text": record["text"]})
    return {"klass": klass, "rows_returned": len(messages), "new": new, "at": at}


def main() -> int:
    printable()
    install_client_guard()
    ours = refresh_our_reports()
    print(f"tracker: {ours.get('klass')}, {ours.get('total')} report(s), {ours.get('statuses')}")
    inbox = fetch_inbox()
    if inbox["klass"] != "ok":
        print(f"a2a inbox: could not read it ({inbox['klass']}), which is not an empty inbox")
        return 1
    answers = [m for m in inbox["new"] if not m["auto"]]
    print(f"a2a inbox: {inbox['rows_returned']} message(s), {len(answers)} new repl(ies), "
          f"{len(inbox['new']) - len(answers)} new automated"
          + ("  -- the page is FULL: older messages may not have been read" if inbox.get("full") else ""))
    for message in answers:
        first = (message["text"] or "").strip().splitlines()
        print(f"  >> {message['at']}  {message['msg_id']}  {(first[0] if first else '')[:100]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
