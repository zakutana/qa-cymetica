"""One account has one plan, whichever Nexus endpoint is asked (2026-10-03).

While checking whether the operator's Pro plan had reached our key, two reads of the
SAME account (`expire76`, id 113) gave two answers:

    GET /api/v1/nexus/usage         plan "pro", plan_name "Pro", price_usdc "20.00"
    GET /api/v1/nexus/subscription  plan "free", tier "free", subscription null

The second endpoint carries the build plans itself: its `plans` list is the same
vocabulary (free / pro / max5 ...) and `build_plans_enabled` is true. So the word
`plan` means one thing in both, and an agent that reads the subscription endpoint is
told the account is on Free while it is on Pro -- the reading that made this session
tell its operator, wrongly, that the plan had not arrived.

This asserts: when both endpoints answer, and the subscription endpoint's own `plans`
list contains the plan code the usage endpoint names (so they share a vocabulary), the
two `plan` values are equal.

NOT asserted: which of the two is right, or what `is_premium` means (it may be the
older $9.99 Nexus premium, a different product). Only that a field called `plan`, in a
list of plans, does not name two different plans for one account.

SAFE: two GETs with the trusted key.
"""

from __future__ import annotations

import httpx

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

USAGE = "/api/v1/nexus/usage"
SUBSCRIPTION = "/api/v1/nexus/subscription"


def _read(client, path: str) -> dict:
    try:
        response = client.get(path)
    except httpx.HTTPError as exc:
        raise Inconclusive(f"{path} could not be read: {type(exc).__name__}")
    if response.status_code != 200:
        raise Inconclusive(f"{path} answered HTTP {response.status_code}; a failed read is not a plan")
    try:
        body = response.json()
    except ValueError:
        raise Inconclusive(f"{path} did not answer JSON")
    if not isinstance(body, dict):
        raise Inconclusive(f"{path} answered something that is not an object")
    return body


@qa(component="rest.support", tier=SafetyTier.SAFE, surface="rest")
def test_the_account_has_one_plan_on_every_nexus_endpoint(rest_trusted):
    """`plan` on /nexus/usage equals `plan` on /nexus/subscription for one account, when
    the subscription endpoint lists the usage endpoint's plan among its own plans."""
    usage = _read(rest_trusted, USAGE)
    subscription = _read(rest_trusted, SUBSCRIPTION)
    said_usage = usage.get("plan")
    said_subscription = subscription.get("plan")
    if not isinstance(said_usage, str) or not isinstance(said_subscription, str):
        raise Inconclusive(f"a plan is missing: usage {said_usage!r}, subscription {said_subscription!r}")
    listed = {p.get("code") for p in subscription.get("plans") or [] if isinstance(p, dict)}
    if said_usage not in listed:
        raise Inconclusive(
            f"{SUBSCRIPTION} does not list {said_usage!r} among its plans {sorted(c for c in listed if c)}, "
            f"so the two may not share a vocabulary")
    differ = said_usage != said_subscription
    conclude(Measurement(
        verdict="failed" if differ else "passed",
        reason=(f"one account, two plans: {USAGE} says {said_usage!r}, {SUBSCRIPTION} says "
                f"{said_subscription!r} (tier {subscription.get('tier')!r}, subscription "
                f"{subscription.get('subscription')!r})" if differ else
                f"both endpoints name the plan {said_usage!r}"),
        left={"usage_plan": said_usage, "subscription_plan": said_subscription},
        right={"usage_plan": said_usage, "subscription_plan": said_usage},
        population={"plans_listed_by_subscription": sorted(c for c in listed if c),
                    "subscription_tier": subscription.get("tier"),
                    "subscription_is_premium": subscription.get("is_premium"),
                    "usage_plan_name": usage.get("plan_name")},
        sources={"usage": USAGE, "subscription": SUBSCRIPTION}))
