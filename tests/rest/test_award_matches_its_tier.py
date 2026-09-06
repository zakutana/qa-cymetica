"""A recorded award and the tier published beside it must agree.

Report #63 asked the tracker to be able to say what a verified report had
earned. It can now: every report carries `reward_status`, `reward_amount`,
`reward_currency` and `eligible_reward_range`, and 35 awards are recorded.
That part worked.

What arrived with it is two statements about the same report that cannot both
be true. Each row publishes an `eligible_reward_range` keyed to its own
CONFIRMED severity -- 400,000-1,000,000 CYM for a critical -- and beside it an
award of 1,000 ET10. Different number, different currency, same row.

Which of the two is the real programme is not ours to decide, and this check
does not try. It asserts only that a row may not contradict itself: the award
is expressed in the currency of the range it publishes, and lands inside it.
Whichever way they resolve that -- correcting the amounts, or correcting the
range to describe the programme actually being paid -- the check goes green.
"""

from __future__ import annotations

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

TRACKER = "/api/v1/bounty/reports"
TIERS = "/api/v1/bounty/reward-tiers"


@qa(component="rest.support", tier=SafetyTier.SAFE, surface="rest",
    claim="award-contradicts-its-own-tier")
def test_a_recorded_award_agrees_with_the_tier_on_the_same_row(rest_anon):
    """Read both fields off one row and ask whether they can coexist."""
    page = rest_anon.get(TRACKER)
    if page.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"the public tracker answered HTTP {page.status_code}",
            claim_id="award-contradicts-its-own-tier"))
        return

    body = page.json()
    rows = body.get("reports") or body.get("data") or []

    # An award of zero is a RECORDED award, and one recorded against a
    # six-figure band is exactly the contradiction this check is for. Filtering
    # on truthiness collapsed 0, None and a missing key into one bucket and
    # dropped those rows out of the population -- the falsy-versus-absent
    # mistake qa/measure.py's readers exist to prevent.
    awarded = [r for r in rows
               if isinstance(r.get("reward_amount"), (int, float))]
    if not awarded:
        conclude(Measurement(
            verdict="inconclusive",
            reason=("no row records an award yet, so there is nothing to hold "
                    "against the tier published beside it"),
            population={"rows": len(rows)},
            claim_id="award-contradicts-its-own-tier"))
        return

    wrong_currency, outside, unmeasurable = [], [], []
    for r in awarded:
        band = r.get("eligible_reward_range") or {}
        low, high = band.get("min"), band.get("max")
        if not isinstance(low, (int, float)) or not isinstance(high, (int, float)):
            # No band, or one without numbers, means this row cannot be
            # adjudicated. Counted, never skipped: skipping it silently let a
            # tracker that DROPPED the field read as every award agreeing with
            # its tier, which would settle this finding by deleting the
            # evidence for it.
            unmeasurable.append(r.get("id"))
            continue
        if band.get("currency") and r.get("reward_currency") \
                and band["currency"] != r["reward_currency"]:
            wrong_currency.append(
                (r.get("id"), r.get("reward_currency"), band["currency"]))
        # BOTH bounds. Checking only the minimum meant an award above the
        # published maximum passed, while the invariant filed as #68 is that
        # the amount falls within [min, max].
        if not (low <= r["reward_amount"] <= high):
            outside.append((r.get("id"), r["reward_amount"], low, high,
                            band.get("severity")))

    measured = len(awarded) - len(unmeasurable)
    if not measured:
        conclude(Measurement(
            verdict="inconclusive",
            reason=(f"all {len(awarded)} awarded row(s) publish no usable "
                    f"eligible_reward_range, so nothing can be held against "
                    f"the tier -- the field this check reads is gone"),
            left=unmeasurable[:8], right=len(awarded),
            sources={"tracker": TRACKER, "tiers": TIERS},
            population={"rows": len(rows), "awarded": len(awarded),
                        "without_a_band": len(unmeasurable)},
            claim_id="award-contradicts-its-own-tier"))
        return

    problems = []
    if wrong_currency:
        problems.append(
            f"{len(wrong_currency)} row(s) record an award in one currency and "
            f"publish an entitlement in another "
            f"(e.g. #{wrong_currency[0][0]}: paid in {wrong_currency[0][1]}, "
            f"entitled in {wrong_currency[0][2]})")
    if outside:
        rid, amt, low, high, sev = outside[0]
        problems.append(
            f"{len(outside)} row(s) record an award outside the range they "
            f"publish for their own confirmed severity "
            f"(e.g. #{rid} at {sev}: {amt:.0f} recorded against {low}-{high})")
    if unmeasurable:
        problems.append(
            f"{len(unmeasurable)} awarded row(s) publish no usable "
            f"eligible_reward_range at all, so what they earned cannot be "
            f"checked against what they promise")

    conclude(Measurement(
        verdict="failed" if problems else "passed",
        reason=("; ".join(problems) if problems else
                f"all {measured} recorded awards sit inside the tier each "
                f"row publishes, in the same currency"),
        left=([r[0] for r in outside] + [r[0] for r in wrong_currency]
              + unmeasurable)[:8],
        right=measured,
        sources={"tracker": TRACKER, "tiers": TIERS},
        population={"rows": len(rows), "awarded": len(awarded),
                    "measured": measured, "without_a_band": len(unmeasurable),
                    "currency_mismatch": len(wrong_currency),
                    "below_published_minimum": len(outside)},
        claim_id="award-contradicts-its-own-tier"))
