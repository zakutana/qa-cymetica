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


def merge() -> dict:
    current = load("findings.json")
    ledger = load_ledger()
    rows: dict = ledger.setdefault("findings", {})

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    run_id = latest_run_id()
    seen_now = {f["id"] for f in current.get("findings", [])}

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

    # 2. Rows absent from this run: the check no longer reproduces.
    for finding_id, row in rows.items():
        if finding_id in seen_now:
            continue
        if row.get("verified_fixed_at"):
            row["state"] = "VERIFIED FIXED"
            continue
        row["verified_fixed_at"] = now
        row["verified_by_run"] = run_id
        row["state"] = "VERIFIED FIXED"
        row["thread"] = row.get("thread", [])

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
                  "THEY REPLIED": 3, "FIX CLAIMED": 4, "VERIFIED FIXED": 5}
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
    for row in as_findings(ledger):
        filed = ", ".join(f"#{f['report_id']}" for f in row.get("filed", [])) or "-"
        print(f"   {row.get('state', '?'):<16} {row['severity']:<15} "
              f"{filed:<8} {row['id']}")
