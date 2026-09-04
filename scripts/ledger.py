"""Persistent finding ledger.

The bug this fixes: findings were derived fresh on every run from whatever was
currently failing, so a finding whose check started passing simply vanished --
taking with it the record that it had existed, been filed, and been verified.

That is backwards. A finding we verified fixed OURSELVES is the most valuable
record in the project: it is the only state that means "we checked", as opposed
to "they said". Losing it credits nobody and leaves nothing to regress against.

So every finding ever seen gets a permanent row here. A finding that stops
reproducing becomes VERIFIED FIXED, stamped with the run and timestamp that
verified it. If it ever reproduces again, that same row becomes REGRESSED --
which is only detectable because the row survived.

    python scripts/ledger.py      # merge the current run into the ledger
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

STATE = REPO_ROOT / "state"
LEDGER = STATE / "ledger.json"


# Findings WE withdrew, with the reason. A check that stops failing because we
# deleted it is not a fix, and crediting the vendor for one would be the same
# error as refusing to credit a real one -- just pointed the other way.
WITHDRAWN = {
    "CYM-mcp_tool_count":
        "Our check asserted the anonymous tool count equals the manifest total. "
        "That held only while tier gating was broken; once it was fixed, "
        "anonymous correctly returns 25 of 46 and our check reported their fix "
        "as a failure. Replaced by tests/mcp/test_trust_ladder.py.",
    "CYM-documented-405":
        "Measured our own probe method, not their contract. The original 18 were "
        "llms.txt rendering MCP tools as GET-able /mcp/v1/tools/<name> URLs, and "
        "those are gone. The 10 that remain are POST-only endpoints we probed "
        "with GET, where 405 is the correct answer.",
    "CYM-mcp_tool_names_documented_exist":
        "Never a defect. The check is INCONCLUSIVE, not failing: llms.txt no "
        "longer links any tool names, so there is nothing to verify. It entered "
        "the ledger from a run before the claim was rewritten.",
    "CYM-chain_count":
        "Our check compared 'settlement on 10 chains' against the 16 chains "
        "/api/v1/swap/chains supports for swaps. Two different mechanisms; "
        "netting them is the collapsed-layer defect we report in others.",
}

def load(name: str) -> dict:
    path = STATE / name
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}


def load_ledger() -> dict:
    if LEDGER.exists():
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    return {"findings": {}}


def latest_run_id() -> str | None:
    runs = sorted((STATE / "runs").glob("run-*.json"))
    if not runs:
        return None
    return json.loads(runs[-1].read_text(encoding="utf-8")).get("run_id")


def executed_nodeids() -> set[str]:
    """Which checks actually ran in the latest run record."""
    runs = sorted((STATE / "runs").glob("run-*.json"))
    if not runs:
        return set()
    run = json.loads(runs[-1].read_text(encoding="utf-8"))
    return {r["nodeid"] for r in run.get("results", [])}


def merge() -> dict:
    current = load("findings.json")
    ledger = load_ledger()
    rows: dict = ledger.setdefault("findings", {})

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    run_id = latest_run_id()
    seen_now = {f["id"] for f in current.get("findings", [])}

    # 0. Withdrawals apply unconditionally -- a finding we retracted stays
    #    retracted even if its check is still producing output.
    # 1. Findings observed in this run: create or refresh the row.
    for finding in current.get("findings", []):
        row = rows.setdefault(finding["id"], {
            "id": finding["id"],
            "first_seen": now,
            "first_seen_run": run_id,
        })
        row.update({
            "title": finding["title"],
            "severity": finding["severity"],
            "tag": finding.get("tag"),
            "kind": finding.get("kind"),
            "section": finding.get("section"),
            "component": finding.get("component"),
            "note": finding.get("note"),
            "detail": finding.get("detail"),
            "checks": finding.get("checks", []),
            "filed": finding.get("filed", []),
            "thread": finding.get("thread", []),
            "last_reproduced": now,
            "last_reproduced_run": run_id,
            "reproductions": row.get("reproductions", 0) + 1,
        })
        # A row that had been verified fixed and reproduces again is a regression.
        if row.get("verified_fixed_at"):
            row["regressed_at"] = now
            row["regressed_run"] = run_id
            row["verified_fixed_at"] = None
            row["state"] = "REGRESSED"
        else:
            row["state"] = finding["state"]

    # 2. Rows absent from this run.
    #
    #    Absence has two very different causes and conflating them is a defect:
    #    the check RAN and passed, or the check never ran because the selector
    #    did not include it. Only the first is a verification. Marking a finding
    #    fixed because a partial run skipped it would let a targeted re-run
    #    silently close everything it did not touch.
    executed = executed_nodeids()
    for finding_id, row in rows.items():
        if finding_id in seen_now:
            continue
        if finding_id in WITHDRAWN:
            row["state"] = "WITHDRAWN"
            row["withdrawn_reason"] = WITHDRAWN[finding_id]
            row["withdrawn_at"] = row.get("withdrawn_at") or now
            row.pop("verified_fixed_at", None)
            continue
        if row.get("verified_fixed_at"):
            row["state"] = "VERIFIED FIXED"
            continue

        checks = row.get("checks") or []
        ran = [c for c in checks if c in executed]
        if checks and not ran:
            # The check exists and did not run. State is unchanged and the row
            # is flagged, because "we did not look" must never read as "we
            # looked and it was fine".
            row["not_checked_in_last_run"] = True
            continue
        row.pop("not_checked_in_last_run", None)

        row["verified_fixed_at"] = now
        row["verified_by_run"] = run_id
        row["state"] = "VERIFIED FIXED"
        row["thread"] = row.get("thread", [])

    # 3. Refresh the filing status of every row from the live tracker.
    #    Rows carry a snapshot of what the vendor said when the row was
    #    written; a backfilled row froze that snapshot at backfill time and
    #    would otherwise keep displaying "pending" long after the report was
    #    triaged. Showing a stale vendor status next to our own verification
    #    makes the page contradict itself.
    bounty = load("bounty.json")
    live = {
        r["id"]: r.get("status")
        for r in (bounty.get("our_reports") or {}).get("reports", [])
    }
    refreshed = 0
    for row in rows.values():
        for entry in row.get("filed", []):
            current_status = live.get(entry.get("report_id"))
            if current_status and entry.get("status") != current_status:
                entry["status"] = current_status
                entry["status_seen_at"] = now
                refreshed += 1
    ledger["filing_status_refreshed"] = refreshed

    for finding_id, reason in WITHDRAWN.items():
        row = rows.get(finding_id)
        if row is not None:
            row["state"] = "WITHDRAWN"
            row["withdrawn_reason"] = reason
            row["withdrawn_at"] = row.get("withdrawn_at") or now
            row.pop("verified_fixed_at", None)

    ledger["updated_at"] = now
    ledger["run_id"] = run_id
    ledger["counts"] = {
        state: sum(1 for r in rows.values() if r.get("state") == state)
        for state in sorted({r.get("state") for r in rows.values()} - {None})
    }
    return ledger


def as_findings(ledger: dict) -> list[dict]:
    """Ledger rows in the shape the dashboard already renders."""
    order = ["S0-CUSTODY", "S1-INTEGRITY", "S2-MEASUREMENT", "S3-CONTRACT",
             "S4-COSMETIC"]
    state_rank = {"REGRESSED": 0, "NOT RAISED YET": 1, "RAISED": 2,
                  "THEY REPLIED": 3, "FIX CLAIMED": 4, "VERIFIED FIXED": 5,
                  "WITHDRAWN": 6}
    rows = list(ledger.get("findings", {}).values())
    rows.sort(key=lambda r: (
        state_rank.get(r.get("state"), 9),
        order.index(r["severity"]) if r.get("severity") in order else 9,
        r["id"],
    ))
    return rows


if __name__ == "__main__":
    ledger = merge()
    LEDGER.write_text(json.dumps(ledger, indent=2, ensure_ascii=False),
                      encoding="utf-8")
    print(f"-> {LEDGER.relative_to(REPO_ROOT)}")
    print(f"   {ledger['counts']}")
    print(f"   refreshed {ledger['filing_status_refreshed']} stale filing statuses")
    for row in as_findings(ledger):
        filed = ", ".join(f"#{f['report_id']}" for f in row.get("filed", [])) or "-"
        print(f"   {row.get('state', '?'):<16} {row['severity']:<15} "
              f"{filed:<8} {row['id']}")
