"""Derive findings from measured data. Nothing here is hand-written prose.

Three sources feed the findings list:

  1. failed reconciliation checks  -- the platform contradicting itself
  2. the reachability inventory    -- documented endpoints that do not answer
  3. the MCP tool surface          -- declared trust tier vs the tier served

Rule followed throughout: where one observation admits two explanations, the
finding says so rather than picking the more dramatic one. A 404 on an endpoint
llms.txt documents is EITHER a missing endpoint OR a stale document, and which
one it is has to come from them -- collapsing the two into "broken endpoint"
would be exactly the kind of merged-layer summary the methodology rejects.
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yaml  # noqa: E402

STATE = REPO_ROOT / "state"
CLAIMS = REPO_ROOT / "tests" / "reconciliation" / "claims.yaml"

SEVERITY_ORDER = ["S0-CUSTODY", "S1-INTEGRITY", "S2-MEASUREMENT",
                  "S3-CONTRACT", "S4-COSMETIC"]


def latest_run() -> dict | None:
    runs = sorted((STATE / "runs").glob("run-*.json"))
    if not runs:
        return None
    return json.loads(runs[-1].read_text(encoding="utf-8"))


def load_inventory() -> dict | None:
    path = STATE / "inventory.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def load_bounty() -> dict | None:
    path = STATE / "bounty.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def load_claims() -> dict:
    return yaml.safe_load(CLAIMS.read_text(encoding="utf-8"))


def _parse_failure(text: str) -> dict:
    """Pull the two compared values out of our own assertion message."""
    out: dict[str, str] = {}
    for match in re.finditer(r"^\s*E?\s*(\w+)\s+= (.+)$", text or "", re.M):
        name, value = match.group(1), match.group(2).strip()
        if name not in ("QUESTION", "CLAIM", "SEVERITY", "RELATION", "DRIFT", "NOTE"):
            out[name] = value
    return out


# ---------------------------------------------------------------------------
def from_reconciliation(run: dict, claims: dict) -> list[dict]:
    by_id = {c["id"]: c for c in claims["claims"]}
    grouped: dict[str, list[dict]] = defaultdict(list)

    for result in run.get("results", []):
        if result["outcome"] != "failed" or "test_sources_agree" not in result["nodeid"]:
            continue
        match = re.search(r"\[([^\]]+)\]", result["nodeid"])
        if not match:
            continue
        param = match.group(1)
        claim_id, _, pair = param.partition("::")
        grouped[claim_id].append({
            "pair": pair,
            "nodeid": result["nodeid"],
            "values": _parse_failure(result.get("failure_repr", "")),
            "evidence_ids": result.get("evidence_ids", []),
        })

    findings = []
    for claim_id, pairs in sorted(grouped.items()):
        claim = by_id.get(claim_id, {})
        values: dict[str, str] = {}
        for entry in pairs:
            values.update(entry["values"])
        findings.append({
            "id": f"CYM-{claim_id}",
            "kind": "contradiction",
            "severity": claim.get("severity", "S3-CONTRACT"),
            "title": claim.get("question", claim_id),
            "component": claim.get("component", "reconciliation"),
            "section": _section_for_component(claim.get("component", "")),
            "detail": values,
            "note": " ".join((claim.get("note") or "").split()) or None,
            "checks": [p["nodeid"] for p in pairs],
            "failing_pairs": len(pairs),
            "evidence_ids": sorted({e for p in pairs for e in p["evidence_ids"]}),
        })
    return findings


COMPONENT_TO_SECTION = {
    "rest.agents": "agents",
    "mcp.tools_list": "mcp",
    "mcp.protocol": "mcp",
    "mcp.trust_ladder": "identity_trust",
    "rest.clob": "clob",
    "platform.status": "swaps",
    "platform.ai_native_proof": "provenance",
    "discovery.wellknown": "discovery",
    "reconciliation": "discovery",
}


def _section_for_component(component: str) -> str:
    return COMPONENT_TO_SECTION.get(component, "discovery")


# ---------------------------------------------------------------------------
def from_inventory(inventory: dict) -> list[dict]:
    findings: list[dict] = []

    missing: list[dict] = []
    method: list[dict] = []
    for section in inventory["sections"]:
        for entry in section.get("endpoint_detail", []):
            row = {"path": entry["path"], "section": section["id"],
                   "section_title": section["title"],
                   "sources": entry.get("sources", []),
                   "status_anon": entry.get("status_anon"),
                   "status_trusted": entry.get("status_trusted")}
            if entry.get("verdict") == "missing":
                missing.append(row)
            elif entry.get("verdict") == "method":
                method.append(row)

    if missing:
        findings.append({
            "id": "CYM-documented-404",
            "kind": "documentation",
            "severity": "S3-CONTRACT",
            "title": f"{len(missing)} endpoints the platform documents return 404",
            "component": "discovery.llmstxt",
            "section": "discovery",
            "note": (
                "This does not establish which of two things is true. Either the "
                "endpoints were removed and the documents are stale, or the "
                "documents are aspirational and these were never built. An agent "
                "following llms.txt cannot tell the difference, and neither can "
                "we -- the platform has to say which."
            ),
            "detail": {r["path"]: f"404 (documented in {', '.join(r['sources'])})"
                       for r in sorted(missing, key=lambda r: r["path"])},
            "affected_sections": sorted({r["section"] for r in missing}),
            "checks": ["scripts/inventory.py"],
            "evidence_ids": [],
        })

    if method:
        findings.append({
            "id": "CYM-documented-405",
            "kind": "documentation",
            "severity": "S4-COSMETIC",
            "title": f"{len(method)} documented URLs exist but reject the documented method",
            "component": "discovery.llmstxt",
            "section": "mcp",
            "note": (
                "llms.txt renders MCP tools as fetchable URLs of the form "
                "/mcp/v1/tools/<name>. They answer 405: the resource exists, the "
                "shape in the document does not. Low severity on its own, but it "
                "is the same document that carries the tool names and counts."
            ),
            "detail": {r["path"]: "405 Method Not Allowed"
                       for r in sorted(method, key=lambda r: r["path"])},
            "affected_sections": sorted({r["section"] for r in method}),
            "checks": ["scripts/inventory.py"],
            "evidence_ids": [],
        })

    return findings


# ---------------------------------------------------------------------------
def from_tool_surface(inventory: dict) -> list[dict]:
    tools = inventory.get("tools", {})
    declared: dict[str, str] = tools.get("declared", {})
    anon = set(tools.get("served_anon", []))
    if not declared or not anon:
        return []

    public = {name for name, tier in declared.items() if tier == "unknown"}
    above = sorted(anon - public)
    if not above:
        return []

    by_tier: dict[str, list[str]] = defaultdict(list)
    for name in above:
        by_tier[declared.get(name, "undeclared")].append(name)

    return [{
        "id": "CYM-anon-tool-surface",
        "kind": "authorization",
        "severity": "S0-CUSTODY",
        "title": (
            f"An unauthenticated caller is served all {len(anon)} MCP tools, "
            f"including {len(above)} above the tier declared for them"
        ),
        "component": "mcp.trust_ladder",
        "section": "identity_trust",
        "note": (
            "mcp.json assigns every tool a trust_tier and llms.txt states "
            "'anonymous = PUBLIC tools'. An anonymous tools/list returns the "
            "full set anyway, including tools declared allied. SCOPE: this "
            "establishes the ADVERTISED surface only. It does not show that "
            "calling those tools without a key succeeds -- that is a separate "
            "check, and the distinction matters."
        ),
        "detail": {
            f"declared {tier} but served anonymously": ", ".join(sorted(names))
            for tier, names in sorted(by_tier.items())
        },
        "checks": ["scripts/inventory.py"],
        "evidence_ids": [],
    }]


# ---------------------------------------------------------------------------
def from_bounty(bounty: dict) -> list[dict]:
    """The vendor's own tracker, read as data rather than as a verdict."""
    statuses = bounty.get("statuses", {})
    total = bounty.get("total", 0)
    if not total:
        return []

    findings: list[dict] = []
    reports = bounty.get("reports", [])

    # 1. Every item is closed and no item carries a platform-set validated_at.
    unvalidated = [r for r in reports if not r.get("validated_at")]
    if set(statuses) <= {"fixed", "resolved", "closed"} and len(unvalidated) == total:
        findings.append({
            "id": "CYM-tracker-closure-rate",
            "kind": "process",
            "severity": "S2-MEASUREMENT",
            "title": (
                f"All {total} reports in the public bounty tracker read "
                f"'fixed', and validated_at is null on every one"
            ),
            "component": "rest.support",
            "section": "support",
            "note": (
                "A queue with a 100% closure rate and no open, triaged, "
                "disputed or wont_fix item is not a queue -- it is either a "
                "filtered view or a tracker that does not retain unresolved "
                "items. The schema HAS validated_at, triaged_at and "
                "severity_confirmed fields; none is populated on any record. "
                "SCOPE: this says nothing about whether the underlying fixes "
                "are real. It says the tracker records no evidence that anyone "
                "checked."
            ),
            "detail": {
                "status distribution": ", ".join(f"{k}={v}" for k, v in statuses.items()),
                "validated_at populated": f"0 of {total}",
                "closed with no notes, no ticket, no PR link":
                    str(bounty.get("closed_without_recorded_evidence", 0)),
            },
            "checks": ["scripts/bounty.py"],
            "evidence_ids": [],
        })

    # 2. Our own reports were closed by them and never re-verified by us.
    mine = [r for r in reports if r.get("hunter_name") == "expire76"]
    if mine:
        findings.append({
            "id": "CYM-own-reports-unverified",
            "kind": "process",
            "severity": "S3-CONTRACT",
            "title": (
                f"{len(mine)} reports filed under our hunter name were closed by "
                f"the platform and have never been re-verified by us"
            ),
            "component": "rest.support",
            "section": "support",
            "note": (
                "The resolution notes are specific -- they name files, line "
                "numbers and commit hashes. That is better than most vendors "
                "provide and it is worth crediting. It is still a claim: the "
                "commits are not inspectable from here, validated_at is null, "
                "and our own records still list these as open with "
                "last_regression_run: null. Correct state is FIX_CLAIMED, not "
                "fixed. Note also that all six are UI defects in arena.js, "
                "outside this project's API/MCP scope -- re-verifying them "
                "needs the browser suite, not this one."
            ),
            "detail": {
                f"#{r['id']}": f"{r['status']}, fixed_at={str(r.get('fixed_at'))[:19]}, "
                               f"validated_at={r.get('validated_at')}"
                for r in sorted(mine, key=lambda r: r["id"])
            },
            "checks": ["scripts/bounty.py"],
            "evidence_ids": [],
        })

    return findings


def build() -> dict:
    run = latest_run()
    inventory = load_inventory()
    bounty = load_bounty()
    findings: list[dict] = []

    if run:
        findings += from_reconciliation(run, load_claims())
    if inventory:
        findings += from_tool_surface(inventory)
        findings += from_inventory(inventory)
    if bounty:
        findings += from_bounty(bounty)

    findings.sort(key=lambda f: (SEVERITY_ORDER.index(f["severity"]), f["id"]))

    for finding in findings:
        finding.setdefault("state", "OPEN")
        finding.setdefault("first_seen_run", run["run_id"] if run else None)
        finding.setdefault("reported_at", None)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "run_id": run["run_id"] if run else None,
        "platform_fingerprint": run.get("platform_fingerprint") if run else None,
        "findings": findings,
        "by_severity": {
            severity: sum(1 for f in findings if f["severity"] == severity)
            for severity in SEVERITY_ORDER
        },
    }


if __name__ == "__main__":
    data = build()
    out = STATE / "findings.json"
    out.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"-> {out.relative_to(REPO_ROOT)}")
    for finding in data["findings"]:
        print(f"  {finding['severity']:<15} {finding['id']:<28} {finding['title']}")
