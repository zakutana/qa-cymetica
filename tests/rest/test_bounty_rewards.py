"""The bug-bounty reward programme, as the platform's own data describes it.

Announced in the support channels: every verified bug report earns its
reporter 1000 ET10, including a backlog of already-filed reports, paid
on-chain on a daily cycle once the reporter qualifies.

The tracker has the schema to express exactly that. Each report carries
`reward_amount`, `reward_currency` and `paid_at` -- an award and a payment,
which is the right shape, because the announcement makes them separate events:
the award is earned on verification, the payment waits until the reporter
holds ET10 and some gas.

Both checks below read only the platform's own numbers against the platform's
own numbers. Neither depends on anything we were told privately, and neither
asserts that anybody owes us anything -- that is not ours to measure. What is
measurable is whether the platform can say, from its own API, what a report
earned and whether it has been paid.
"""

from __future__ import annotations

import re

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude, required

TRACKER = "/api/v1/bounty/reports"
STATS = "/api/v1/bounty/stats"
LEADERBOARD = "/api/v1/bounty/leaderboard"

CLOSED = frozenset({"fixed", "resolved", "completed", "closed", "paid"})

# Where an agent would look. The platform publishes these for machine readers
# and already describes its OTHER earning programme -- ET10 revenue share --
# across agent-card.json and agent-skills.json, so this is a question about
# consistency, not about whether they document things.
DISCOVERY = {
    "llms.txt": "/llms.txt",
    "agent-card.json": "/.well-known/agent-card.json",
    "agent-skills.json": "/.well-known/agent-skills.json",
    "openapi.json": "/openapi.json",
    "mcp.json": "/.well-known/mcp.json",
}

# A description of THIS programme, not merely a mention of the token. "ET10"
# alone matches the asset, which is documented all over; what has to be
# findable is that filing a bug earns one.
PROGRAMME = re.compile(
    r"(bug|report|bounty)[^.\n]{0,80}(reward|earn|payout|1000\s*ET10)"
    r"|(reward|earn|payout|1000\s*ET10)[^.\n]{0,80}(bug report|bug you|per bug)",
    re.I)


@qa(component="rest.support", tier=SafetyTier.SAFE, surface="rest",
    claim="bounty-rewards-unrecorded")
def test_verified_reports_record_what_they_earned(rest_anon):
    """A verified report has to say what it earned, separately from payment.

    Payment can legitimately be pending -- the announced programme holds
    unpaid rewards until the reporter qualifies, and that is what `paid_at`
    is for. The award is not pending: it is earned when the report is
    verified. If `reward_amount` is null on every closed report, the tracker
    cannot answer "what have I accrued", and neither can the reporter.
    """
    page = rest_anon.get(TRACKER)
    if page.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"the public tracker answered HTTP {page.status_code}",
            claim_id="bounty-rewards-unrecorded"))
        return

    body = page.json()
    rows = body.get("reports") or body.get("data") or []
    if not rows:
        conclude(Measurement(
            verdict="inconclusive",
            reason="the tracker returned no rows, so there is nothing to read",
            claim_id="bounty-rewards-unrecorded"))
        return

    if "reward_amount" not in rows[0] and "reward_status" not in rows[0]:
        conclude(Measurement(
            verdict="inconclusive",
            reason=("the tracker rows carry no reward field at all, so this "
                    "check cannot tell an unrecorded award from a schema that "
                    "never had one"),
            population={"fields": sorted(rows[0])},
            claim_id="bounty-rewards-unrecorded"))
        return

    closed = [r for r in rows if (r.get("status") or "").lower() in CLOSED]

    # Re-scoped 2026-09-05 after their answer (ET-22226) and the field that
    # shipped with it. They explained the architecture: the tracker and the
    # ET10 reward lane are two separate records, and payments live in the
    # lane. So demanding reward_amount on the tracker was asking the wrong
    # object for the answer, and that part of report #63 is withdrawn.
    #
    # What they added is reward_status, and it does distinguish a verified
    # report from an invalid one. It does not distinguish a PAID report from
    # one whose award was never recorded -- both read pending_award -- which
    # is the question a hunter actually has. Their own note says as much:
    # "pending_award means verified, award not yet recorded".
    #
    # So the invariant is narrowed to exactly what is still missing, and it
    # goes green the moment any report of ours reads as paid.
    # `awarded` and a truthy reward_amount are AWARD-side signals, and the
    # comment above states the green condition as "the moment any report of
    # ours reads as paid" -- so accepting them settled the check on exactly
    # the field the paragraph says is the wrong object. reward_amount was also
    # read as a flag, so a recorded award of 0.0 counted as no award.
    #
    # 2026-09-08: the operator was credited 27,000 ET10 for 27 reports while
    # every tracker row still read paid_at null. That is the answer, and it is
    # narrower than the report assumed: payment happens in the ET10 lane and
    # the tracker does not record it. So this measures the tracker's own
    # claim, and the reason says which record it is talking about -- it is a
    # reporting gap, not a missing payment, and the text must not imply
    # otherwise.
    settled = [r for r in closed
               if r.get("paid_at")
               or str(r.get("reward_status") or "").lower() in
               ("paid", "award_recorded", "rewarded")]

    stats = rest_anon.get(STATS)
    totals = stats.json() if stats.status_code == 200 else {}
    seen = sorted({str(r.get("reward_status")) for r in rows if r.get("reward_status")})

    conclude(Measurement(
        verdict="failed" if closed and not settled else "passed",
        reason=(f"{len(closed)} of the {len(rows)} public reports are closed "
                f"as fixed and {len(settled)} of them can be read as paid or "
                f"awarded. reward_status takes {seen or ['no value']}, so a "
                f"report that was paid and one whose award was never recorded "
                f"are indistinguishable"
                + (f"; stats still report bugs_fixed={totals.get('bugs_fixed')} "
                   f"and total_paid={totals.get('total_paid')}" if totals else "")),
        left=len(settled), right=len(closed),
        sources={"tracker": TRACKER, "totals": STATS, "their_ref": "ET-22226"},
        population={"rows_returned": len(rows), "closed": len(closed),
                    "reward_status_values": seen,
                    "bugs_fixed_per_stats": totals.get("bugs_fixed"),
                    "total_paid_per_stats": totals.get("total_paid")},
        claim_id="bounty-rewards-unrecorded"))


@qa(component="discovery.llmstxt", tier=SafetyTier.SAFE, surface="rest",
    claim="bounty-rewards-undocumented")
def test_the_reward_programme_is_discoverable_by_an_agent(rest_anon):
    """An earning programme an agent cannot find is one it cannot join.

    This platform's whole posture is that agents read its machine-readable
    surfaces and act on them -- and it already documents its other earning
    programme there, ET10 revenue share, in both agent-card.json and
    agent-skills.json with triggers and an endpoint. A bug-report reward
    announced only in a chat channel is invisible to precisely the readers
    those files exist for.

    Matched on the PROGRAMME, not on the token: "ET10" appears throughout as
    an asset, and finding that would say nothing about whether filing a bug
    earns anything.
    """
    found, unreadable = {}, {}
    for name, url in DISCOVERY.items():
        response = rest_anon.get(url)
        if response.status_code != 200:
            unreadable[name] = response.status_code
            continue
        match = PROGRAMME.search(response.text)
        if match:
            found[name] = match.group(0)[:120]

    if len(unreadable) == len(DISCOVERY):
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"none of the discovery documents could be read: {unreadable}",
            claim_id="bounty-rewards-undocumented"))
        return

    conclude(Measurement(
        verdict="passed" if found else "failed",
        reason=("the bug-report reward programme is described in "
                + ", ".join(sorted(found)) if found else
                "the bug-report reward programme appears in none of the "
                "machine-readable discovery surfaces, so an agent reading them "
                "cannot learn that filing a bug earns anything"),
        left=sorted(found) or [], right=sorted(DISCOVERY),
        sources={"searched": ", ".join(sorted(DISCOVERY))},
        population={"documents_read": len(DISCOVERY) - len(unreadable),
                    "unreadable": unreadable},
        claim_id="bounty-rewards-undocumented"))
