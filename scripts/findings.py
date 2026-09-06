"""Propose candidate findings from one run record. Holds no state.

This file used to decide what state a finding was in, and it decided it from
the vendor's tracker: the branch at :539-550 read their status and nothing
else, so FIX CLAIMED could appear without anyone re-running anything. It also
scraped the finding's detail out of the pytest traceback, which is how a line
of OUR source once reached the vendor as evidence about THEIR platform. And it
carried `if False and method:`, a finding switched off by editing the
generator that produced it.

All three are gone. This module now answers exactly one question -- given this
run record, what does it propose? -- and the fold decides what that means.

A candidate needs three things to be true at once:

  * the check FAILED. Inconclusive is not a defect, it is a check that could
    not measure; skipped is not evidence of anything.
  * it failed in the CALL phase. A fixture blowing up in setup is our harness
    breaking, and filing it as a platform defect would be the sharpest way to
    lose the vendor's trust -- especially on the trust ladder test, where it
    would have gone out as an S0.
  * its measurement has role `verdict`. A prose-versus-prose comparison is
    evidence for a finding, never a finding by itself.
"""

from __future__ import annotations

import json
import sys
from collections import defaultdict
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import yaml  # noqa: E402

CLAIMS = REPO_ROOT / "tests" / "reconciliation" / "claims.yaml"

SEVERITY_ORDER = ["S0-CUSTODY", "S1-INTEGRITY", "S2-MEASUREMENT",
                  "S3-CONTRACT", "S4-COSMETIC"]

# Product-facing tags. Named after what the platform is from a user's side, not
# after how its routes are organised -- a finding should be placeable without
# knowing the URL layout.
# Ordered: the product as a user meets it first, the machinery underneath after.
TAG_ORDER = ["EXCHANGE", "BOTS", "ARENA", "MONEY", "FUNDS", "MCP", "DOCS", "PROCESS"]
TAGS = {
    "EXCHANGE": (
        "Exchange & markets",
        "The CLOB, price feeds, event cards, prediction pools. Where orders meet.",
        ["clob", "markets", "event_cards", "prediction_pools", "deadcoin"],
    ),
    "BOTS": (
        "Bots, skills & AgentBook",
        "Agent species, cloning, skills, backtests, the social/reputation layer.",
        ["agents", "agentbook", "backtest"],
    ),
    "ARENA": (
        "CyMetica-42 Arena",
        "Blue vs Red AI hedge-fund competition and betting on it.",
        ["arena"],
    ),
    "MONEY": (
        "Money in and out",
        "Deposits, withdrawals, balances, cross-chain swaps, token launches.",
        ["funding", "account", "swaps", "launchpad"],
    ),
    "FUNDS": (
        "Funds & prop desk",
        "Agent-created AIB funds, the Tuatara fund, funded trading accounts.",
        ["funds", "prop_desk"],
    ),
    "MCP": (
        "MCP & trust ladder",
        "The JSON-RPC surface other AI agents call, and the tiers meant to gate it.",
        ["mcp", "identity_trust", "ontology"],
    ),
    "DOCS": (
        "Manifests & documentation",
        "What an outside agent reads before it acts: llms.txt, OpenAPI, the "
        "well-known manifests. Nobody uses this daily, which is why it drifts.",
        ["discovery", "provenance", "realtime", "unmapped"],
    ),
    "PROCESS": (
        "Reporting channel & tracker",
        "The bounty API we file through and the tracker we read status from. "
        "It has to be trustworthy before anything travelling through it counts.",
        ["support"],
    ),
}
SECTION_TO_TAG = {
    section: tag for tag, (_, _, sections) in TAGS.items() for section in sections
}

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


def tag_for(section: str) -> str:
    return SECTION_TO_TAG.get(section, "DOCS")


def section_for(component: str) -> str:
    if component in COMPONENT_TO_SECTION:
        return COMPONENT_TO_SECTION[component]
    return component.split(".")[-1] if component else "unmapped"


def load_claims() -> dict:
    if not CLAIMS.exists():
        return {}
    data = yaml.safe_load(CLAIMS.read_text(encoding="utf-8")) or {}
    return {c["id"]: c for c in data.get("claims", [])}


def _is_candidate(result: dict) -> bool:
    role = result.get("role") or (result.get("measurement") or {}).get("role") or "verdict"
    return (result.get("outcome") == "failed"
            and result.get("phase") == "call"
            and role != "evidence"
            # A meta check failing is OUR machinery breaking, not their
            # platform. The first admissible run proposed two findings named
            # after the repo-consistency checks -- a stale dashboard offered as
            # a defect in Cymetica. Same class as the setup-phase exclusion:
            # the subject of the measurement has to be the platform.
            and result.get("surface") != "meta")


def _claim_of(result: dict) -> str:
    """What this result is a measurement OF -- never the test's file path."""
    claim = result.get("claim_id") or (result.get("measurement") or {}).get("claim_id")
    if claim:
        return claim.split("::")[0]
    name = result["nodeid"].rsplit("::", 1)[-1]
    return name[5:] if name.startswith("test_") else name


def _detail(results: list[dict]) -> dict:
    """The finding's numbers, taken from what the check deliberately measured.

    Never from `failure_repr`. That field is our traceback -- it contains our
    file paths, our assertion source and our variable names, and none of it is
    a statement about the platform.

    One row may declare many checks -- CYM-documented-404 declares 26 -- and
    taking the first non-null value of each field independently built a
    chimera: a reason from one measurement printed above a population from
    another, with the second failure invisible. That detail is what
    `_summary` puts on the page and what submit.py sends as the headline
    under "MEASURED VALUES (from the live service)", so the mixture went out
    as one reading.

    So: every reason is kept, and a number is kept only when every check that
    measured it agrees. A missing figure is honest; one check's figure
    labelled as the row's is not.
    """
    # By nodeid, so the same run always folds to the same detail. Run order is
    # collection order, and the repo-consistency guard re-folds to compare.
    ordered = sorted(results, key=lambda r: r.get("nodeid") or "")
    measurements = [r.get("measurement") or {} for r in ordered]

    detail: dict = {}

    for field in ("left", "right", "sources", "population"):
        values = [m[field] for m in measurements if m.get(field) is not None]
        if not values:
            continue
        if len(values) == 1:
            detail[field] = values[0]
        elif all(v == values[0] for v in values[1:]):
            detail[field] = values[0]
        elif field == "left" and all(isinstance(v, list) for v in values):
            # The one field that composes: `left` is the offending items, and
            # two checks each naming their own are one longer list of them.
            merged: list = []
            for value in values:
                for item in value:
                    if item not in merged:
                        merged.append(item)
            detail[field] = merged
        # Otherwise dropped. Two checks disagreeing about a number is not a
        # number about the row, and picking one would be picking at random.

    reasons: list[str] = []
    for measurement in measurements:
        reason = (measurement.get("reason") or "").strip()
        if reason and reason not in reasons:
            reasons.append(reason)
    if reasons:
        detail["reason"] = "; ".join(reasons)

    return detail


def candidates(run: dict | None) -> list[dict]:
    """What this run record proposes as findings. No states, no vendor data."""
    if run is None:
        return []

    claims = load_claims()
    grouped: dict[str, list[dict]] = defaultdict(list)
    for result in run.get("results", []):
        if _is_candidate(result):
            grouped[_claim_of(result)].append(result)

    out = []
    for claim_id, results in sorted(grouped.items()):
        claim = claims.get(claim_id, {})
        component = claim.get("component") or results[0].get("component") or "unknown"
        section = section_for(component)
        detail = _detail(results)
        # Only fields this run actually determined. Severity and title are
        # JUDGEMENTS, and a run does not make them -- claims.yaml does, or an
        # operator did when the row was created. Supplying defaults here
        # overwrote them on the first admissible run: CYM-anon-tool-surface
        # went from S0-CUSTODY to S3-CONTRACT because no claims.yaml entry
        # matched, silently downgrading a custody finding. A measurement may
        # update what it measured; it may not restate what it was never told.
        proposed = {
            "id": f"CYM-{claim_id}",
            "kind": "contradiction" if claim else "check_failure",
            "component": component,
            "section": section,
            "tag": tag_for(section),
            "detail": detail,
            "checks": sorted(r["nodeid"] for r in results),
            "evidence_ids": sorted({e for r in results for e in r.get("evidence_ids", [])}),
        }
        # Present only when claims.yaml states them, so an existing row keeps
        # the severity and title it was given.
        if claim.get("severity"):
            proposed["severity"] = claim["severity"]
        if claim.get("question"):
            proposed["title"] = claim["question"]
        if claim.get("note"):
            proposed["note"] = " ".join(claim["note"].split())
        # A brand-new row still needs both; the fold fills them at creation.
        proposed["default_severity"] = "S3-CONTRACT"
        proposed["default_title"] = detail.get("reason") or claim_id
        out.append(proposed)
    return out


if __name__ == "__main__":
    import argparse

    from qa.state import latest_admissible_run_id, load_run

    parser = argparse.ArgumentParser(prog="findings.py", description=__doc__)
    parser.add_argument("--run", dest="run_id", default=None)
    args = parser.parse_args()

    run_id = args.run_id or latest_admissible_run_id("R")
    if run_id is None:
        raise SystemExit("no admissible run record; nothing to propose")
    proposed = candidates(load_run(run_id))
    print(json.dumps(proposed, indent=2, ensure_ascii=False))
    print(f"\n{len(proposed)} candidates from {run_id}", file=sys.stderr)
