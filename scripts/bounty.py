"""Snapshot the platform's own bug tracker.

The bounty API is both our filing channel and our inbox: reports are posted to
POST /api/v1/bounty/reports/with-screenshots and their state comes back from
GET /api/v1/bounty/reports, which carries status, status_notes, severity_confirmed,
validated_at, triaged_at, fixed_at, ticket_url and fix_pr_url.

That makes it the one place where the platform tells us, in a machine-readable
form, that something is fixed. Which is exactly why the snapshot is kept and
diffed rather than believed: a status transition here is a CLAIM, and it enters
our ledger as FIX_CLAIMED. Only our own re-run of the failing check can move it
further.

    python scripts/bounty.py
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
from qa.config import identities  # noqa: E402
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier  # noqa: E402


def out_path() -> Path:
    """The snapshot, resolved through the QA_STATE_DIR seam at call time.

    It was a module constant built from REPO_ROOT, which is the one seam the
    whole project reads state behind and the only module that ignored it after
    open_checks.py was fixed. A test setting QA_STATE_DIR to a temp tree was
    handed the committed file instead -- and one written while reviewing this
    wrote its two-row fixture over the real snapshot, losing the vendor's
    status_notes until the next full fetch.
    """
    from qa.state import state_dir

    return state_dir() / "bounty.json"


# Fields that, if null, mean the platform recorded no evidence for a closure.
EVIDENCE_FIELDS = ["validated_at", "triaged_at", "severity_confirmed",
                   "ticket_url", "fix_pr_url", "status_notes"]


def probe_filing_auth() -> dict:
    """Does filing a report require a credential?

    Sent with an EMPTY body at both identities, so the request cannot create a
    record whatever the answer -- verified after the fact: the tracker total did
    not move. We read only the error CLASS. A validation error means the request
    passed authorization; a permission error means the gate held.
    """
    registry = EndpointRegistry.load()
    ids = identities()
    results: dict[str, dict] = {}

    token = CURRENT_TIER.set(SafetyTier.PROBE)
    try:
        for label in ("anon", "trusted"):
            identity = ids[label]
            if not identity.present:
                continue
            client = build_client(identity, registry)
            try:
                response = client.post("/api/v1/bounty/reports", json={})
                body = response.text[:400]
                results[label] = {
                    "status": response.status_code,
                    "error_class": classify_error(response.status_code, body),
                    "body": body,
                }
            except Exception as exc:  # noqa: BLE001
                results[label] = {"status": 0, "error_class": "unreachable",
                                  "body": f"{type(exc).__name__}: {exc}"}
            finally:
                client.close()
    finally:
        CURRENT_TIER.reset(token)

    bodies = {r["body"] for r in results.values()}
    return {
        "endpoint": "POST /api/v1/bounty/reports",
        "method": "empty body, error class only",
        "by_identity": results,
        "identical_across_identities": len(bodies) == 1 and len(results) > 1,
    }


def classify_error(status: int, body: str) -> str:
    """Deliberately coarse. The platform's taxonomy is not status-code driven.

    /mcp/v1/agents/me returns 422 for a missing credential, and MCP tool errors
    come back as HTTP 200 with isError set, so status alone cannot separate
    'you may not' from 'you sent nothing'. Where the two are indistinguishable
    we say so rather than guessing.
    """
    lowered = body.lower()
    if status in (401, 403) or "unauthor" in lowered or "forbidden" in lowered:
        return "PERMISSION"
    if status in (400, 422) and ("field required" in lowered or "missing" in lowered):
        return "VALIDATION"
    if status in (400, 422):
        return "VALIDATION_OR_UNKNOWN"
    if status == 404:
        return "NOT_FOUND"
    if 200 <= status < 300:
        return "ACCEPTED"
    return f"OTHER_{status}"


READ_CLASSES = ("ok", "unauthorized", "forbidden", "not_found", "malformed",
                "server_error", "unreachable")

REPORT_FIELDS = (
    "id", "title", "status", "hunter_name", "wallet_address",
    "severity_reported", "severity_confirmed", "category",
    "created_at", "fixed_at", "validated_at", "triaged_at",
    "status_notes", "ticket_url", "fix_pr_url", "reward_amount",
)


def classify_read(outcome) -> str:
    """What KIND of read this was.

    Nothing here ever looked at an HTTP status, so a 401 arrived as a body
    with no reports in it -- byte for byte what a tracker looks like when the
    vendor has closed everything. An expired key read as good news.
    """
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


def _capture(response) -> str | None:
    """Store the bytes a read rests on and return their id.

    Critique gap 2: FIX_CLAIMED is half of the strongest statement the
    dashboard makes, and it used to rest on a response nobody kept. The fold
    now refuses a filing transition whose event cites no evidence, so this is
    load-bearing rather than tidy.
    """
    from qa.evidence import EvidenceStore

    try:
        return EvidenceStore("script-bounty").capture(
            response.request, response, SafetyTier.SAFE)
    except Exception:  # noqa: BLE001 -- evidence must not break the read
        return None


def _printable(text: str, encoding: str | None = None) -> str:
    """Their words, reduced to what this terminal can actually show.

    The console codepage on this workspace is cp1250 and their automated
    replies open with a trophy emoji, so printing one through an un-pinned
    stdout raises UnicodeEncodeError. Every entry point pins utf-8, which is
    why this is a second line of defence -- but the input is a third party's
    and the failure is total: it would land between the read and the events
    the read is there to write, taking the snapshot down with it.

    Replaces rather than strips, so a mangled character is visible as one.
    The journal keeps the original; this is only for the terminal.
    """
    encoding = encoding or getattr(sys.stdout, "encoding", None) or "ascii"
    flat = " ".join((text or "").split())
    try:
        return flat.encode(encoding, errors="replace").decode(encoding, errors="replace")
    except LookupError:  # an encoding name Python does not know
        return flat.encode("ascii", errors="replace").decode("ascii")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _last_status_by_report() -> dict:
    """The newest status we have recorded for each report.

    From the journal, because that is where the claim lives. The snapshot in
    state/bounty.json is a projection of the same thing and could be rebuilt
    from these events, but not the other way round.
    """
    from qa.state import read_events

    last: dict = {}
    for event in read_events():
        if event.get("type") == "vendor_status" and event.get("report_id") is not None:
            last[event["report_id"]] = event.get("status")
    return last


def refresh_our_reports(client=None) -> dict:
    """Re-read our own reports and update just that half of the snapshot.

    `fetch_our_reports` appends the journal events and returns the rows; it
    does NOT write state/bounty.json, which only fetch() + __main__ do. The
    console's bell reads the vendor's status, notes and dates out of
    bounty.json (render._api_conversation), so an event without the snapshot
    beside it moves nothing an operator can see -- which is what serve.py
    --ask was doing: recording the change and leaving the page saying the old
    thing.

    Only the `our_reports` section, and deliberately: fetch() also probes the
    filing endpoint with empty POSTs at two identities, and a timer has no
    business doing that every quarter of an hour. One read-only GET, one
    section rewritten, the rest of the file left as the last full fetch left
    it.

    Rule 8 runs through it: the snapshot on disk is handed back as `previous`,
    so a read that fails returns those rows marked stale instead of an empty
    section. The first draft of this called fetch_our_reports() with no
    previous, and the first live invocation -- a read that happened to come
    back unreachable -- wrote 0 reports over 20 good ones. A failed read is
    not an empty read, and a refresher that forgets that is worse than no
    refresher.

    The read, the fetch and the write are held under one lock, the same one
    the journal uses. Without it this is a read-modify-write across a network
    call: a full `python scripts/bounty.py` completing inside that window --
    the sweep runs one -- would be undone the moment the refresher wrote its
    copy back, reverting statuses, filing_probe, qa_tracker, closed and
    leaderboard to whatever they were before the fetch while our_reports alone
    stayed current. A snapshot half of one read and half of another, with
    nothing malformed to notice it by.
    """
    from qa.state import file_lock

    out = out_path()
    out.parent.mkdir(parents=True, exist_ok=True)

    with file_lock(out):
        data: dict = {}
        if out.exists():
            try:
                data = json.loads(out.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                data = {}

        ours = fetch_our_reports(client=client, previous=data.get("our_reports"))
        data["our_reports"] = ours
        data["our_reports_refreshed_at"] = _now()

        tmp = out.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, out)
    return ours


A2A_INBOX = "/api/v1/bounty/a2a/inbox/{agent_id}"

# NOT "scripts/bounty.py". A vendor_read is keyed on at|source|klass, and this
# function runs in the same second as the tracker read, from the same file,
# usually with the same klass -- so sharing the source would make the second
# read a duplicate of the first and it would be silently dropped. The source
# says which surface was read, which is what the field is for.
A2A_SOURCE = "scripts/bounty.py a2a-inbox"


def fetch_inbox(client=None, agent_id: str | None = None) -> dict:
    """The other half of the inbound channel, and nobody was reading it.

    Correspondence with them arrives on two surfaces, not one. `my-reports`
    carries what they did to a report. The a2a inbox carries what they SAID --
    it is where a question sent to POST /a2a/send is answered, and their own
    onboarding message promises that "a human will review your message and
    reply personally" there.

    Nothing read it until 2026-09-07. bounty.py read my-reports and stopped;
    serve.py --ask runs bounty.py; the only other reader was a parser for an
    archive that stopped being written in round one (qa/messages.py, retired
    2026-09-09), and it said in its own docstring that correspondence now
    arrives through the bounty API -- true, but that API
    has two surfaces and we were reading one. Twenty-three messages had piled
    up, and the only reason any had been read was the operator asking out loud
    how a reply would be noticed. The answer was: it would not.

    One event per message, keyed by the message's own id, so re-reading the
    same inbox next sweep costs nothing and a reply cannot be missed twice.
    The automated first pass is flagged rather than dropped: 21 of those 23
    were routing prompts, and a channel that hides them hides the one real
    message with them.
    """
    import os

    from qa.state import append_event

    agent_id = agent_id or os.environ.get("QA_A2A_AGENT_ID", "expire76-qa")

    owned = client is None
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        if owned:
            ids = identities()
            client = build_client(
                ids["trusted"] if ids["trusted"].present else ids["anon"],
                EndpointRegistry.load(), timeout=60.0)
        try:
            response = client.get(A2A_INBOX.format(agent_id=agent_id),
                                  params={"unread_only": "false"})
            klass = classify_read(response)
            evidence_id = _capture(response)
        except Exception:  # noqa: BLE001
            response, klass, evidence_id = None, "unreachable", None
        finally:
            if owned:
                client.close()
    finally:
        CURRENT_TIER.reset(token)

    at = _now()
    messages = []
    if klass == "ok":
        data = response.json()
        messages = data.get("messages") or data.get("inbox") or []

    append_event({
        "type": "vendor_read", "at": at, "by": "agent", "source": A2A_SOURCE,
        "klass": klass, "evidence_id": evidence_id,
        "rows_returned": len(messages) if klass == "ok" else None,
    })

    # Rule 8. A refused inbox is not an empty one, and the quiet failure here
    # is the dangerous one: 401, nothing parsed, nothing written, a sweep that
    # says nothing -- indistinguishable from a vendor who has not replied.
    if klass != "ok":
        return {"klass": klass, "rows_returned": None, "new": [], "at": at}

    return record_inbox(messages, klass=klass, at=at, evidence_id=evidence_id)


def record_inbox(messages: list[dict], klass: str = "ok",
                 at: str | None = None, evidence_id: str | None = None) -> dict:
    """Their messages onto the journal, one event each, keyed on their id.

    Split out of fetch_inbox so the recording can be tested without the
    network -- which matters because everything downstream of it reads only
    what is written HERE, and the discriminator it drops is the discriminator
    qa/channels.py needs.
    """
    from qa.state import append_event

    at = at or _now()
    new: list[dict] = []
    for message in messages:
        msg_id = message.get("id")
        if not msg_id:
            continue
        metadata = message.get("metadata") or {}
        # append_event is the authority on whether we have seen this, not a
        # set built here: the journal keys a message on its id, so a second
        # reader cannot disagree with it.
        # auto, kind and the message it answers were read into `new` and then
        # dropped when this returned, so from the journal a routing prompt and
        # a human answer were the same row -- and an alert that fires on the
        # trophy emoji is one the operator learns to ignore. `reply_to` takes
        # their parent_message_id: the thread id is one value for the whole
        # account and pairs nothing, this pairs a question with its answer.
        #
        # The 39 messages recorded before 2026-09-08 carry none of these and
        # cannot be given them -- the journal is append-only. A missing `kind`
        # therefore means UNKNOWN, never "human" and never "robot".
        record = {
            "type": "message", "at": message.get("created_at") or at,
            "by": "vendor", "source": A2A_SOURCE, "msg_id": str(msg_id),
            "text": message.get("content") or "",
            "origin": "a2a", "via": message.get("thread_id"),
            # The capture their words came in (D6 of the review of
            # 2026-09-23): the keepset keeps what a `message` names, and it
            # named nothing, so the words stayed and their proof could go.
            "evidence_id": evidence_id,
        }
        # Written even when false or absent, which is the whole point: "the
        # vendor says this is a person" and "nobody classified this" were the
        # same row on the journal -- no key either way -- so every human
        # answer they have sent landed in the bucket that exists for the 39
        # messages written before there was a discriminator at all.
        if "auto" in metadata or "kind" in metadata:
            record["auto"] = bool(metadata.get("auto"))
            record["kind"] = (str(metadata["kind"])
                              if metadata.get("kind") else None)
        answers = message.get("parent_message_id") or metadata.get("in_reply_to")
        if answers:
            record["reply_to"] = str(answers)
        wrote = append_event(record)
        if wrote == "appended":
            new.append({"msg_id": str(msg_id),
                        "at": message.get("created_at") or at,
                        "auto": bool(metadata.get("auto")),
                        "kind": metadata.get("kind"),
                        "thread_id": message.get("thread_id"),
                        "text": message.get("content") or ""})

    return {"klass": klass, "rows_returned": len(messages), "new": new, "at": at}


def fetch_our_reports(client=None, wallet: str | None = None,
                      previous: dict | None = None) -> dict:
    """Our own filed reports -- THIS is the inbox.

    GET /api/v1/bounty/reports is a filtered public view: it returns only
    validated items, which is why every record in it reads "fixed". Our own
    submissions live behind /api/v1/bounty/my-reports?wallet_address=<addr>
    and are invisible in the public list until someone acts on them.

    Two consequences worth stating. A submission acknowledged with
    {"success": true, "report_id": N} is NOT retrievable at
    /api/v1/bounty/reports/N, so the id in the response cannot be used to
    confirm the write. And because the wallet address is the only key, anyone
    holding it can list that hunter's reports.

    On anything but a clean read this returns the PREVIOUS snapshot marked
    stale. It does not return an empty one, because "we could not look" and
    "there is nothing there" are different facts and only one of them is
    evidence.
    """
    import os

    from qa.state import append_event

    wallet = wallet or os.environ.get("QA_WALLET_ADDRESS", "")
    if not wallet:
        # The same shape as every other failed read, and for the same reason:
        # this return used to hand back a bare error with no rows, so a run
        # with no wallet in the environment wrote an empty our_reports over a
        # good one. "We could not look" is not "there is nothing there" --
        # this function's own docstring says so two paragraphs up, and the
        # klass != "ok" branch below already did it correctly.
        stale = dict(previous or {})
        stale.update({
            "klass": "unreachable",
            "error": "QA_WALLET_ADDRESS not set",
            "rows_returned": None,
            "stale_from": _now(),
        })
        return stale

    owned = client is None
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        if owned:
            ids = identities()
            client = build_client(
                ids["trusted"] if ids["trusted"].present else ids["anon"],
                EndpointRegistry.load(), timeout=60.0)
        try:
            response = client.get("/api/v1/bounty/my-reports",
                                  params={"wallet_address": wallet})
            klass = classify_read(response)
            evidence_id = _capture(response)
        except Exception as exc:  # noqa: BLE001
            response, klass, evidence_id = None, "unreachable", None
            failure = f"{type(exc).__name__}: {exc}"
        else:
            failure = None
        finally:
            if owned:
                client.close()
    finally:
        CURRENT_TIER.reset(token)

    at = _now()
    rows = []
    server_total = None
    if klass == "ok":
        data = response.json()
        rows = data.get("reports") or data.get("data") or []
        server_total = data.get("total", len(rows))

    append_event({
        "type": "vendor_read", "at": at, "by": "agent", "source": "scripts/bounty.py",
        "klass": klass, "evidence_id": evidence_id,
        "rows_returned": len(rows) if klass == "ok" else None,
        "server_total": server_total,
    })

    if klass != "ok":
        stale = dict(previous or {})
        stale.update({
            "klass": klass, "rows_returned": None, "stale_from": at,
            "evidence_id": evidence_id,
        })
        if failure:
            stale["error"] = failure
        return stale

    # Record CHANGES, not polls. One run appended one event per report
    # unconditionally, so 599 of the journal's 865 events were 28 reports
    # saying the same thing 27 times over -- and a poller on any useful
    # interval would have added 2,784 a day, burying the handful of events
    # that mean something under the ones that mean "we looked again".
    #
    # `vendor_read` above still fires every time: that a read happened, and
    # whether it succeeded, is the fact rule 8 rests on, and it is one event
    # rather than one per report.
    last = _last_status_by_report()
    for report in sorted(rows, key=lambda r: r.get("id", 0)):
        report_id = report.get("id")
        status = report.get("status")
        if report_id is None:
            # Nothing to compare it against and nothing to attach it to: the
            # journal keys a vendor_status by report_id, and
            # _last_status_by_report skips the None key, so an id-less row
            # would never match `last` and would append a fresh event on every
            # poll -- the poll-recording this loop exists to stop, at 96 a day
            # with serve.py --ask running. A row the tracker gave no id is not
            # a status change we can record; the vendor_read event above
            # already says the read happened.
            continue
        if report_id in last and last[report_id] == status:
            continue
        append_event({
            "type": "vendor_status", "at": at, "by": "agent",
            "source": "scripts/bounty.py", "report_id": report_id,
            "status": status, "observed_at": at,
            "evidence_id": evidence_id,
        })

    fields_sent = ["hunter_name", "steps_to_reproduce", "expected_behavior",
                   "actual_behavior", "url"]
    dropped = sorted({
        field for field in fields_sent
        for row in rows if not row.get(field)
    })

    return {
        "endpoint": "GET /api/v1/bounty/my-reports?wallet_address=<addr>",
        "klass": "ok",
        "read_at": at,
        "evidence_id": evidence_id,
        # Ours and theirs, side by side: they disagreed (20 vs 23), and a
        # closure rate computed over the wrong denominator is a made-up number.
        "rows_returned": len(rows),
        "server_total": server_total,
        "total": server_total,
        "statuses": dict(Counter(r.get("status") for r in rows)),
        "fields_sent_but_not_stored": dropped,
        "reports": [{k: r.get(k) for k in REPORT_FIELDS}
                    for r in sorted(rows, key=lambda r: r.get("id", 0))],
    }


def fetch_qa_tracker() -> dict:
    """The OTHER tracker -- /leaderboard/bugs, rendered server-side.

    This is where work actually happens: it carries pending / qa_testing /
    implementing / resolved / completed / rejected / wont_fix, Linear ticket
    links, comments and votes. The bounty API has none of that.

    Fetched by parsing the page's embedded allBugs array because no JSON
    endpoint for it exists (/api/v1/bugs and five other spellings all 404).
    """
    import json as _json
    import re as _re

    registry = EndpointRegistry.load()
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        client = build_client(identities()["anon"], registry,
                              base_url="https://cymetica.com")
        try:
            html = client.get("/leaderboard/bugs",
                              headers={"Accept": "text/html"}).text
        finally:
            client.close()
    except Exception as exc:  # noqa: BLE001
        return {"error": f"{type(exc).__name__}: {exc}"}
    finally:
        CURRENT_TIER.reset(token)

    rows: list = []
    decoder = _json.JSONDecoder()
    for match in _re.finditer(r"allBugs\s*=\s*", html):
        start = html.find("[", match.end())
        if start == -1 or start > match.end() + 3:
            continue
        try:
            parsed, _ = decoder.raw_decode(html[start:])
        except ValueError:
            continue
        if len(parsed) > len(rows):
            rows = parsed

    ids = [r.get("id") for r in rows if isinstance(r.get("id"), int)]
    return {
        "source": "https://cymetica.com/leaderboard/bugs (embedded allBugs)",
        "total": len(rows),
        "statuses": dict(Counter(r.get("status") for r in rows)),
        "source_channels": dict(Counter(r.get("source_channel") for r in rows)),
        "usernames": dict(Counter(r.get("username") for r in rows)),
        "id_range": [min(ids), max(ids)] if ids else None,
        "titles": [(r.get("title") or "").strip().lower() for r in rows],
        "has_linear_links": sum(1 for r in rows if r.get("linear_ticket_url")),
    }


def fetch() -> dict:
    install_client_guard()
    registry = EndpointRegistry.load()
    ids = identities()
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        client = build_client(ids["trusted"] if ids["trusted"].present else ids["anon"],
                              registry)
        try:
            payload = client.get("/api/v1/bounty/reports").json()
            leaderboard = client.get("/api/v1/bounty/leaderboard").json()
        finally:
            client.close()
    finally:
        CURRENT_TIER.reset(token)

    reports = payload.get("reports", [])
    statuses = Counter(r.get("status") for r in reports)
    filing_probe = probe_filing_auth()
    ours = fetch_our_reports()
    qa = fetch_qa_tracker()
    inbox = fetch_inbox()

    closed = [r for r in reports if r.get("status") in ("fixed", "resolved", "closed")]
    unevidenced = [
        r for r in closed
        if all(r.get(field) in (None, "", []) for field in EVIDENCE_FIELDS)
    ]

    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": payload.get("total", len(reports)),
        "statuses": dict(statuses),
        "filing_probe": filing_probe,
        "our_reports": ours,
        "qa_tracker": qa,
        "a2a_inbox": inbox,
        "closed": len(closed),
        "closed_without_recorded_evidence": len(unevidenced),
        "evidence_fields_checked": EVIDENCE_FIELDS,
        "reports": [
            {k: r.get(k) for k in (
                "id", "title", "status", "hunter_name", "severity_reported",
                "severity_confirmed", "created_at", "fixed_at", "validated_at",
                "triaged_at", "status_notes", "ticket_url", "fix_pr_url",
                "reward_amount", "paid_at", "is_duplicate",
            )}
            for r in reports
        ],
        "leaderboard": leaderboard.get("entries", []),
    }


if __name__ == "__main__":
    from qa.state import file_lock

    data = fetch()
    out = out_path()
    out.parent.mkdir(parents=True, exist_ok=True)
    # Under the same lock refresh_our_reports takes. A lock only one of two
    # writers holds is not a lock -- this is the write the refresher must not
    # be allowed to interleave with, and the one whose loss would be silent.
    with file_lock(out):
        out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"-> {out}")
    print(f"   total={data['total']}  statuses={data['statuses']}")
    print(f"   closed={data['closed']}  "
          f"without any recorded evidence={data['closed_without_recorded_evidence']}")

    # Said out loud, because the whole point of reading the inbox is that a
    # reply must not depend on somebody remembering to look. An automated
    # first pass is counted but not announced; a real one is announced.
    inbox = data.get("a2a_inbox") or {}
    if inbox.get("klass") != "ok":
        print(f"   a2a inbox: could not read it ({inbox.get('klass')}) -- "
              f"that is not an empty inbox")
    else:
        answers = [m for m in inbox.get("new") or [] if not m["auto"]]
        auto = len(inbox.get("new") or []) - len(answers)
        print(f"   a2a inbox: {inbox.get('rows_returned')} message(s), "
              f"{len(answers)} new repl(ies), {auto} new automated")
        for message in answers:
            first = (message["text"] or "").strip().splitlines()
            print(f"   >> {message['at']}  {message['msg_id']}")
            print(f"      {_printable(first[0] if first else '')[:100]}")
