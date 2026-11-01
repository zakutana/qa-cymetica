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

# Closed, in their published report_status enum: fixed and paid (a claim of a fix),
# invalid, duplicate, wontfix (they said no). `resolved`, `completed`, `closed` are not in it.
CLOSED = frozenset({"fixed", "paid", "invalid", "duplicate", "wontfix"})


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
        # A 404 is the defect this check exists for; a 429 or a 5xx on a
        # rate-limited endpoint we read three times in one test is our own
        # traffic coming back at us. Until 2026-09-07 both concluded `failed`,
        # so one transient filed "the endpoint that makes attribution provable
        # answers HTTP 429" against #47 -- while the REPEAT read thirty lines
        # below had already been given rule 8 for that exact case.
        transient = first.status_code == 429 or first.status_code >= 500
        conclude(Measurement(
            verdict="inconclusive" if transient else "failed",
            reason=(f"the endpoint that makes attribution provable answers "
                    f"HTTP {first.status_code}, which is a transient this "
                    f"check cannot tell from an outage, so nothing is "
                    f"established about attribution"
                    if transient else
                    f"the endpoint that makes attribution provable answers "
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
    # Case-folded on both sides. They echo the address lower-cased today, but
    # an EIP-191 message conventionally carries the EIP-55 checksummed form,
    # and the moment they adopt it a case-sensitive substring reads as "the
    # message does not name the wallet" about a message that names it.
    message_folded = message.lower()
    if wallet.lower() not in message_folded:
        broken.append("the message does not name the wallet it attributes to")
    if digest.lower() not in message_folded:
        broken.append("the message is not bound to the report title, so a "
                      "captured signature would re-file anything")
    # Rule 8, and the probe below already had it right. `again.status_code
    # != 200 or ...` filed "the message is not deterministic" on a transient
    # 503 -- three GETs to one rate-limited endpoint in a row -- so a failed
    # read accused their signing message of a defect it does not have, on a
    # row that is filed as #47 and could carry that fail to their server.
    again = rest_anon.get(FILING_MESSAGE,
                          params={"wallet_address": wallet, "title": title})
    if again.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"the repeat read of {FILING_MESSAGE} answered HTTP "
                   f"{again.status_code}, so determinism could not be tested; "
                   f"a read that failed is not a message that changed",
            sources={"endpoint": FILING_MESSAGE},
            claim_id="bounty-filing-unauthenticated"))
        return
    if again.json().get("message_to_sign") != message:
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
    if not closed:
        # "0 of 0 closed reports carry no evidence" is not a pass, it is a
        # measurement of nothing -- and the empty-rows case one branch above
        # already says so. Reachable: the page carries 20 of 42 rows, and as
        # reports move to `paid` the window can hold none that are closed.
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"none of the {len(rows)} rows this read returned is "
                   f"closed, so closure evidence was measured on nothing",
            population={"rows_returned": len(rows), "closed": 0,
                        "server_total": body.get("total")},
            claim_id="tracker-closure-rate",
        ))
        return
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
