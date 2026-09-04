"""The @qa decorator.

One decorator rather than separate component/tier markers, because two markers
means someone eventually applies one and forgets the other -- and the one they
forget will be the tier.
"""

from __future__ import annotations

import pytest

from qa.safety import SafetyTier

__all__ = ["qa", "SafetyTier"]


def qa(
    *,
    component: str,
    tier: SafetyTier,
    surface: str = "rest",
    claim: str | None = None,
    ticket: str | None = None,
    volatile: bool = False,
):
    """Tag a test. Mandatory -- collection fails hard on an untagged test.

    component  dotted name from components.yaml; drives dashboard health
    tier       the most this test is permitted to do, enforced by the transport
    surface    discovery | mcp | rest | ws | chain | meta
    claim      CLM-#### this test settles
    ticket     BUG-#### whose regression check this is
    volatile   the value under test legitimately moves; a mismatch is
               inconclusive rather than a defect
    """

    def decorator(fn):
        fn = pytest.mark.qa_component(component)(fn)
        fn = pytest.mark.qa_tier(SafetyTier(tier).value)(fn)
        fn = pytest.mark.qa_surface(surface)(fn)
        if claim:
            fn = pytest.mark.qa_claim(claim)(fn)
        if ticket:
            fn = pytest.mark.qa_ticket(ticket)(fn)
        if volatile:
            fn = pytest.mark.qa_volatile(fn)
        return fn

    return decorator


class Inconclusive(Exception):
    """Neither pass nor fail: the measurement itself was not trustworthy.

    Raised when a snapshot window was exceeded, a cached response was older
    than the window, or the rate-limit budget cut a comparison short. Maps to
    AMBER on the dashboard and can never open a ticket -- a contradiction we
    cannot cleanly measure is not a contradiction we may report.
    """


def inconclusive(reason: str):
    raise Inconclusive(reason)
