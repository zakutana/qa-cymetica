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

2026-09-06: they answered by zeroing every amount and marking all 20 rows
`reward_status: pending_award`, which retires the amount half honestly --
there is now no award to sit outside anything. The check had to be repaired to
see that, because it read any numeric reward_amount as a recorded award and so
reported "0 recorded against 25000-100000" about reports that had been awarded
nothing. That was our error.

The currency half survives, and needs no award to be judged: #68 still names
USDC for its award beside an entitlement published in CYM, and eighteen others
name ET10 beside the same CYM bands. A row that will pay in one currency and
promises in another contradicts itself whether or not anything has been paid.
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

    # `reward_status` is the tracker saying, in its own field, whether an award
    # exists. This check used to ignore it and read any numeric reward_amount
    # as a recorded award -- defensible when every row carried 1,000 ET10, and
    # wrong the moment they zeroed the amounts and marked all 20 rows
    # `pending_award`. It then reported "0 recorded against 25000-100000" on
    # every row: an award that disagrees with its band, asserted about reports
    # that have been awarded nothing. Our error, not theirs, and the shape the
    # sweep rule about whose bug it is exists to catch.
    #
    # A row is awarded when the tracker does not call it pending. The amount
    # may then legitimately be zero, and a zero award against a six-figure
    # band is still the contradiction this check is for.
    awarded = [r for r in rows
               if isinstance(r.get("reward_amount"), (int, float))
               and (r.get("reward_status") or "").strip() != "pending_award"]

    # The currency half does not need an award to be judged. A row saying "this
    # will be paid in USDC" beside a band reading "entitled to 25,000-100,000
    # CYM" contradicts itself whether or not anything has been paid, so it is
    # read across every row that declares both -- awarded or not.
    wrong_currency = []
    for r in rows:
        band = r.get("eligible_reward_range") or {}
        if band.get("currency") and r.get("reward_currency") \
                and band["currency"] != r["reward_currency"]:
            wrong_currency.append(
                (r.get("id"), r.get("reward_currency"), band["currency"]))

    outside, unmeasurable = [], []
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
        # BOTH bounds. Checking only the minimum meant an award above the
        # published maximum passed, while the invariant filed as #68 is that
        # the amount falls within [min, max].
        if not (low <= r["reward_amount"] <= high):
            outside.append((r.get("id"), r["reward_amount"], low, high,
                            band.get("severity")))

    measured = len(awarded) - len(unmeasurable)
    if not measured and not wrong_currency:
        conclude(Measurement(
            verdict="inconclusive",
            reason=(f"no row records an award to hold against its tier: "
                    f"{len(rows) - len(awarded)} of {len(rows)} are still "
                    f"pending_award and the rest publish no usable "
                    f"eligible_reward_range"),
            left=unmeasurable[:8], right=len(awarded),
            sources={"tracker": TRACKER, "tiers": TIERS},
            population={"rows": len(rows), "awarded": len(awarded),
                        "without_a_band": len(unmeasurable)},
            claim_id="award-contradicts-its-own-tier"))
        return

    problems = []
    # An absent currency on either side used to clear silently -- so deleting
    # the field was a way to pass, which is exactly what `unmeasurable` exists
    # to stop for the band. Counted the same way now.
    currency_unmeasurable = [r.get("id") for r in awarded
                             if not (r.get("reward_currency")
                                     and ((r.get("eligible_reward_range") or {})
                                          .get("currency")))]
    if wrong_currency:
        # Says "will be paid in", not "paid in": with every row pending_award
        # nothing has been paid, and the old wording asserted a payment that
        # had not happened.
        problems.append(
            f"{len(wrong_currency)} row(s) name one currency for the award and "
            f"publish the entitlement beside it in another "
            f"(e.g. #{wrong_currency[0][0]}: to be paid in "
            f"{wrong_currency[0][1]}, entitled in {wrong_currency[0][2]})")
    if outside:
        rid, amt, low, high, sev = outside[0]
        problems.append(
            f"{len(outside)} row(s) record an award outside the range they "
            f"publish for their own confirmed severity "
            f"(e.g. #{rid} at {sev}: {amt:.0f} recorded against {low}-{high})")
    # NOT a problem. The contract this check names is "a row may not
    # contradict itself", and a row with no band makes one statement, not two
    # -- so it cannot contradict itself. Counting it as a failure sent a FAIL
    # verification to #68 and #70 for a state the contract permits, while the
    # honest answer for a row that cannot be adjudicated is the one this same
    # function already gives eleven lines above: inconclusive. It stays in the
    # population, where the operator can see it.

    # The currency half, said out loud. `currency_unmeasurable` was computed
    # above and then read by nothing -- not the problems, not the population,
    # not the gate -- so the comment that introduces it ("Counted the same way
    # now") was false, and a tracker that dropped reward_currency from every
    # row would have passed this check with "no row names a currency its own
    # entitlement contradicts": deleting the evidence as a way to bank a
    # verification for #68 and #70. Audit, 2026-09-07.
    currency_measured = len(awarded) - len(currency_unmeasurable)
    if not problems and not currency_measured and awarded:
        conclude(Measurement(
            verdict="inconclusive",
            reason=(f"no row publishes a currency on both sides, so the half "
                    f"of this contract about currency could not be measured: "
                    f"{len(currency_unmeasurable)} of {len(awarded)} awarded "
                    f"row(s) name a currency for the award or for the "
                    f"entitlement, but not both"),
            left=currency_unmeasurable[:8], right=len(awarded),
            sources={"tracker": TRACKER, "tiers": TIERS},
            population={"rows": len(rows), "awarded": len(awarded),
                        "measured": measured,
                        "currency_unmeasurable": len(currency_unmeasurable)},
            claim_id="award-contradicts-its-own-tier"))
        return

    conclude(Measurement(
        verdict="failed" if problems else "passed",
        reason=("; ".join(problems) if problems else
                f"all {measured} recorded award(s) sit inside the tier each "
                f"row publishes, and of the {currency_measured} row(s) that "
                f"name a currency on both sides, none contradicts itself"),
        left=([r[0] for r in outside] + [r[0] for r in wrong_currency]
              + unmeasurable)[:8],
        right=measured,
        sources={"tracker": TRACKER, "tiers": TIERS},
        population={"rows": len(rows), "awarded": len(awarded),
                    "measured": measured, "without_a_band": len(unmeasurable),
                    "currency_mismatch": len(wrong_currency),
                    "currency_unmeasurable": len(currency_unmeasurable),
                    "below_published_minimum": len(outside)},
        claim_id="award-contradicts-its-own-tier"))
