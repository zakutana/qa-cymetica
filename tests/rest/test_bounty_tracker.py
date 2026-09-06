"""The reporting channel itself, as three collectible checks.

Three ledger rows had `scripts/bounty.py` in their `checks` field. pytest does
not collect a script, so those rows sat outside the verification machinery
entirely: permanently un-adjudicated, while still displaying a state. Two of
them displayed VERIFIED FIXED.

The channel has to be trustworthy before anything travelling through it counts,
so it gets checks like everything else:

    CYM-bounty-filing-unauthenticated  can anyone file as anyone?
    (CYM-own-reports-unverified was the second. It is gone: what that check
     measures is OUR re-check backlog, so it is evidence now and holds no
     finding against the vendor.)
    CYM-tracker-closure-rate           do their closures carry evidence?

The third one is also where the critique landed: it compared 20 rows the
server returned against the 23 it claimed to hold. A rate whose denominator is
not the thing counted is not a measurement, so the population is named,
row-derived, and travels in the Measurement.
"""

from __future__ import annotations

import hashlib
import os

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude, required
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


FILING_MESSAGE = "/api/v1/bounty/filing-message"


def _wallet_is_verified(rest, wallet: str):
    """Whether the platform treats this wallet as proven. Evidence, not a verdict.

    A wallet nobody has proved ownership of is still nameable by anyone, which
    is the residual exposure their fix leaves open by design -- but closing it
    means signing once with the wallet's key, which is the operator's action
    and not something a check can or should do.
    """
    response = rest.get(FILING_MESSAGE, params={"wallet_address": wallet,
                                                "title": "verification status"})
    if response.status_code != 200:
        return f"unknown (HTTP {response.status_code})"
    body = response.json()
    for key in ("wallet_verified", "verified", "is_verified"):
        if key in body:
            return bool(body[key])
    return body.get("note", "not stated")


@qa(component="rest.support", tier=SafetyTier.SAFE, surface="rest",
    claim="bounty-filing-unauthenticated")
def test_attribution_to_a_wallet_is_provable(rest_anon):
    """Can a filing be attributed to a wallet its author does not control?

    This check asked the wrong question until 2026-09-05. It POSTed an empty
    body and demanded 401/403, reading the 422 as "filing is not gated". But
    an empty body names no wallet, so there is nothing to attribute and
    nothing for an attribution gate to refuse -- 422 is the correct answer to
    it, and the check was failing a design decision rather than a defect.
    Open intake is deliberate on their side: anonymous, rate-limited per IP,
    with a 24h duplicate-title gate.

    Report #47's actual subject was that `hunter_name` and `wallet_address`
    are body fields, so a filing could be attributed to someone else. They
    shipped the fix in d12ea54a9: naming a VERIFIED wallet without proof is
    refused with 401 WALLET_SIGNATURE_REQUIRED, where proof is either an
    EIP-191 signature over a deterministic message or a session owning the
    profile.

    What is asserted here is that mechanism, because it is what makes
    attribution provable, and it can be read without signing anything and
    without filing a probe report. Deliberately NOT asserted by trying to
    spoof a verified wallet: the only wallet we may name is our own, ours is
    still unverified, and a successful spoof attempt would create a junk
    report in their tracker to prove a point their own note concedes.
    """
    wallet = os.environ.get("QA_WALLET_ADDRESS", "")
    if not wallet:
        conclude(Measurement(
            verdict="inconclusive",
            reason="QA_WALLET_ADDRESS is not set, so no attribution can be "
                   "asked about",
            claim_id="bounty-filing-unauthenticated"))
        return

    title = "attribution probe"
    first = rest_anon.get(FILING_MESSAGE,
                          params={"wallet_address": wallet, "title": title})
    if first.status_code != 200:
        conclude(Measurement(
            verdict="failed",
            reason=(f"the endpoint that makes attribution provable answers "
                    f"HTTP {first.status_code}; without a deterministic "
                    f"message to sign there is no way to prove a filing is "
                    f"yours"),
            left=first.status_code, right=200,
            sources={"endpoint": f"GET {FILING_MESSAGE}"},
            claim_id="bounty-filing-unauthenticated"))
        return

    message = required(first.json(), "message_to_sign", f"GET {FILING_MESSAGE}")
    digest = hashlib.sha256(title.strip().encode()).hexdigest()

    # Each property below is what stops a different attack. Binding the wallet
    # stops signing for someone else; binding the title hash stops a captured
    # signature being replayed onto a different report; determinism is what
    # lets a signature be produced offline and checked by anyone.
    broken = []
    if wallet.lower() not in message:
        broken.append("the message does not name the wallet it attributes to")
    if digest not in message:
        broken.append("the message is not bound to the report title, so a "
                      "captured signature would re-file anything")
    again = rest_anon.get(FILING_MESSAGE,
                          params={"wallet_address": wallet, "title": title})
    if again.status_code != 200 or again.json().get("message_to_sign") != message:
        broken.append("the message is not deterministic, so it cannot be "
                      "produced offline")
    other = rest_anon.get(FILING_MESSAGE,
                          params={"wallet_address": wallet, "title": title + "!"})
    if other.status_code == 200 and other.json().get("message_to_sign") == message:
        broken.append("two different titles produce the same message")

    conclude(Measurement(
        verdict="failed" if broken else "passed",
        reason=("; ".join(broken) if broken else
                "attribution is provable: the signing message names the wallet, "
                "is bound to sha256(title), and is deterministic"),
        left=broken, right=f"GET {FILING_MESSAGE}",
        sources={"endpoint": FILING_MESSAGE, "fix": "commit d12ea54a9"},
        # Recorded, not asserted: whether OUR wallet has been verified is our
        # action, not their defect. While it is unverified we remain nameable.
        population={"our_wallet_verified": _wallet_is_verified(rest_anon, wallet),
                    "title_sha256": digest},
        claim_id="bounty-filing-unauthenticated",
    ))


@qa(component="rest.support", tier=SafetyTier.SAFE, surface="rest")
def test_reports_they_closed_have_been_rechecked_by_us(rest_trusted):
    """Their closing a report is a claim. Ours is the check that follows it.

    This measures OUR backlog, not their behaviour, and that distinction was
    wrong here until 2026-09-05: the result was bound to the finding
    CYM-own-reports-unverified, so a list of re-checks WE owed stood on the
    dashboard as an open defect against the vendor, carrying report #53. Our
    unfinished work is not their bug however true the number is.

    So it is evidence now: recorded every run and visible, but unable to mint
    or hold a finding. What it says is still worth knowing -- it is the only
    thing standing between "they closed 20 reports" and "20 reports are
    fixed" -- but the party it indicts is us.
    """
    wallet = os.environ.get("QA_WALLET_ADDRESS", "")
    if not wallet:
        conclude(Measurement(
            verdict="inconclusive",
            reason="QA_WALLET_ADDRESS is not set, so we cannot list our own "
                   "reports. An unset identity is not an empty result.",
            role="evidence",
        ))
        return

    response = rest_trusted.get(MINE, params={"wallet_address": wallet})
    if response.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"my-reports answered HTTP {response.status_code}; a failed "
                   f"read is not an empty tracker",
            right=response.status_code, role="evidence",
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
        role="evidence",
        left=unchecked, right=sorted(adjudicated),
        # The denominator is what this read actually returned, named, so it
        # cannot silently become the server's own claimed total.
        population={"reports_returned": len(rows), "closed": len(closed),
                    "server_total": response.json().get("total")},
        sources={"endpoint": f"GET {MINE}", "wallet": "<redacted>"},
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
