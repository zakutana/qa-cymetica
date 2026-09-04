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
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa.client import build_client, install_client_guard  # noqa: E402
from qa.config import identities  # noqa: E402
from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTier  # noqa: E402

OUT = REPO_ROOT / "state" / "bounty.json"

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
    data = fetch()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"-> {OUT.relative_to(REPO_ROOT)}")
    print(f"   total={data['total']}  statuses={data['statuses']}")
    print(f"   closed={data['closed']}  "
          f"without any recorded evidence={data['closed_without_recorded_evidence']}")
