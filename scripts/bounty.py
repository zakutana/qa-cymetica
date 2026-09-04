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

    closed = [r for r in reports if r.get("status") in ("fixed", "resolved", "closed")]
    unevidenced = [
        r for r in closed
        if all(r.get(field) in (None, "", []) for field in EVIDENCE_FIELDS)
    ]

    return {
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "total": payload.get("total", len(reports)),
        "statuses": dict(statuses),
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
