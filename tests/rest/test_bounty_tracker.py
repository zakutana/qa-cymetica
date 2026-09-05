"""The reporting channel itself, as three collectible checks.

Three ledger rows had `scripts/bounty.py` in their `checks` field. pytest does
not collect a script, so those rows sat outside the verification machinery
entirely: permanently un-adjudicated, while still displaying a state. Two of
them displayed VERIFIED FIXED.

The channel has to be trustworthy before anything travelling through it counts,
so it gets checks like everything else:

    CYM-bounty-filing-unauthenticated  can anyone file as anyone?
    CYM-own-reports-unverified         did we re-check what they closed?
    CYM-tracker-closure-rate           do their closures carry evidence?

The third one is also where the critique landed: it compared 20 rows the
server returned against the 23 it claimed to hold. A rate whose denominator is
not the thing counted is not a measurement, so the population is named,
row-derived, and travels in the Measurement.
"""

from __future__ import annotations

import os

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude
from qa.safety import CURRENT_TIER, SafetyTier as Tier

TRACKER = "/api/v1/bounty/reports"
MINE = "/api/v1/bounty/my-reports"

# Fields that, if null on a closed report, mean the closure records no
# evidence that anybody looked.
EVIDENCE_FIELDS = ("validated_at", "triaged_at", "severity_confirmed",
                   "ticket_url", "fix_pr_url", "status_notes")

CLOSED = frozenset({"fixed", "resolved", "completed", "closed"})


def _rows(response) -> list[dict]:
    body = response.json()
    return body.get("reports") or body.get("data") or []


@qa(component="rest.support", tier=SafetyTier.PROBE, surface="rest",
    claim="bounty-filing-unauthenticated")
def test_filing_a_report_requires_a_credential(rest_anon):
    """PROBE: an empty body, and we read only the class of the refusal.

    The question is whether authorization runs BEFORE validation. A 401 or 403
    means the door is locked. A 422 means the door is open and the form was
    merely incomplete -- which is how anyone can file a report under anyone
    else's hunter name, since the name is a field in the body.
    """
    response = rest_anon.post(TRACKER, json={})
    status = response.status_code

    if status in (401, 403):
        verdict, reason = "passed", f"filing is gated: HTTP {status} on an empty body"
    elif status == 422:
        verdict, reason = "failed", (
            "filing is not gated: an unauthenticated empty body reaches "
            "validation (HTTP 422), so authorization never ran"
        )
    elif 200 <= status < 300:
        verdict, reason = "failed", (
            f"an unauthenticated empty body was ACCEPTED (HTTP {status})"
        )
    else:
        verdict, reason = "inconclusive", (
            f"HTTP {status} is neither a refusal we recognise nor an acceptance"
        )

    conclude(Measurement(
        verdict=verdict, reason=reason,
        left="anonymous POST with an empty body", right=status,
        sources={"endpoint": f"POST {TRACKER}"},
        claim_id="bounty-filing-unauthenticated",
    ))


@qa(component="rest.support", tier=SafetyTier.SAFE, surface="rest",
    claim="own-reports-unverified")
def test_reports_they_closed_have_been_rechecked_by_us(rest_anon):
    """Their closing a report is a claim. Ours is the check that follows it.

    This fails while any report they marked closed has no adjudication of its
    own on our side -- which is the state the whole hardening plan exists to
    make visible rather than to paper over.
    """
    wallet = os.environ.get("QA_WALLET_ADDRESS", "")
    if not wallet:
        conclude(Measurement(
            verdict="inconclusive",
            reason="QA_WALLET_ADDRESS is not set, so we cannot list our own "
                   "reports. An unset identity is not an empty result.",
            claim_id="own-reports-unverified",
        ))
        return

    response = rest_anon.get(MINE, params={"wallet_address": wallet})
    if response.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"my-reports answered HTTP {response.status_code}; a failed "
                   f"read is not an empty tracker",
            right=response.status_code, claim_id="own-reports-unverified",
        ))
        return

    rows = _rows(response)
    closed = [r for r in rows if (r.get("status") or "").lower() in CLOSED]
    adjudicated = _adjudicated_report_ids()
    unchecked = sorted(r.get("id") for r in closed if r.get("id") not in adjudicated)

    conclude(Measurement(
        verdict="failed" if unchecked else "passed",
        reason=(f"{len(unchecked)} of {len(closed)} reports they closed have "
                f"never been re-checked by an admissible run of ours"),
        left=unchecked, right=sorted(adjudicated),
        # The denominator is what this read actually returned, named, so it
        # cannot silently become the server's own claimed total.
        population={"reports_returned": len(rows), "closed": len(closed),
                    "server_total": response.json().get("total")},
        sources={"endpoint": f"GET {MINE}", "wallet": "<redacted>"},
        claim_id="own-reports-unverified",
    ))


def _adjudicated_report_ids() -> set:
    """Report ids whose finding a level-V run has actually adjudicated."""
    from qa.state import ledger_path

    import json

    path = ledger_path()
    if not path.exists():
        return set()
    try:
        ledger = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return set()

    out = set()
    for row in (ledger.get("findings") or {}).values():
        if not ((row.get("check") or {}).get("adjudicated_by") or {}).get("run_id"):
            continue
        for report in (row.get("filing") or {}).get("reports", []):
            out.add(report.get("report_id"))
    return out


@qa(component="rest.support", tier=SafetyTier.SAFE, surface="rest",
    claim="tracker-closure-rate")
def test_closures_in_the_public_tracker_carry_evidence(rest_anon):
    """Every row in the public tracker read `fixed` with validated_at null.

    A closure with no evidence field set records that somebody changed a
    status, not that somebody verified anything. Counted over the rows this
    read returned -- the earlier version compared 20 returned rows against a
    server-claimed total of 23, which is a ratio of two different things.
    """
    response = rest_anon.get(TRACKER)
    if response.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"the public tracker answered HTTP {response.status_code}",
            right=response.status_code, claim_id="tracker-closure-rate",
        ))
        return

    body = response.json()
    rows = _rows(response)
    if not rows:
        conclude(Measurement(
            verdict="inconclusive",
            reason="the tracker returned no rows; there is nothing to measure",
            population={"rows_returned": 0, "server_total": body.get("total")},
            claim_id="tracker-closure-rate",
        ))
        return

    closed = [r for r in rows if (r.get("status") or "").lower() in CLOSED]
    unevidenced = [r.get("id") for r in closed
                   if not any(r.get(f) for f in EVIDENCE_FIELDS)]

    conclude(Measurement(
        verdict="failed" if unevidenced else "passed",
        reason=(f"{len(unevidenced)} of {len(closed)} closed reports carry no "
                f"evidence field at all ({', '.join(EVIDENCE_FIELDS)})"),
        left=sorted(i for i in unevidenced if i is not None),
        right=len(closed),
        population={"rows_returned": len(rows), "closed": len(closed),
                    "server_total": body.get("total")},
        sources={"endpoint": f"GET {TRACKER}"},
        claim_id="tracker-closure-rate",
    ))
