"""The tier we believe we hold, against the tier they serve us as.

`qa/config.py` declares an `expected_trust` for every identity -- "trusted" for
the credentialed one, "recognized" for the second, "unknown" for anonymous.
Nothing has ever asserted it. Grepped 2026-09-08: the field is written in four
places and read in none.

That matters more than a stale label. Every tier check in
tests/mcp/test_trust_ladder.py reasons about what a caller AT A GIVEN RUNG may
see -- "a credentialed caller receives nothing above its own tier", "higher tier
is a superset of lower". Those checks take the rung from the server, so they
stay honest; but the sentence a human reads afterwards, and the identity names
in .env, come from this file. When the two drift, the suite still passes and
every summary of it is wrong.

Found by reading GET /mcp/v1/agents/me for the first time on 2026-09-08: the
server reports `allied`, the top rung, while our config had said `trusted`
since round one. Most likely we earned it -- trust_score 10226, sixteen paid
reports -- which is exactly the kind of quiet promotion nothing here would have
noticed.

This is a check about OUR configuration, not their platform. It fails on our
drift, not on their defect, and that is the point.
"""

from __future__ import annotations

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

SELF = "/mcp/v1/agents/me"


@qa(component="mcp.trust_ladder", tier=SafetyTier.SAFE, surface="mcp")
def test_the_rung_we_claim_is_the_rung_they_serve_us(rest_trusted):
    """Our declared identity against theirs, on the endpoint /build names.

    /build tells an agent its rung is `trust_level` on GET /mcp/v1/agents/me.
    So this reads exactly what the page tells a reader to read.
    """
    from qa.config import identities

    response = rest_trusted.get(SELF)
    if response.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"{SELF} answered HTTP {response.status_code}, so the rung "
                   f"they serve us could not be read",
            sources={"self": SELF}))
        return

    body = response.json()
    served = body.get("trust_level")
    if not served:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"{SELF} answered 200 with no trust_level field, so there "
                   f"is nothing to hold our configuration against",
            population={"fields": len(body)}, sources={"self": SELF}))
        return

    declared = identities()["trusted"].expected_trust
    conclude(Measurement(
        verdict="passed" if declared == served else "failed",
        reason=(f"our credentialed identity is declared {declared!r} in "
                f"qa/config.py and served as {served!r} on {SELF}, so every "
                f"sentence we write about which rung we tested from is wrong"
                if declared != served else
                f"the rung we claim and the rung they serve are both "
                f"{served!r}"),
        left=declared, right=served,
        sources={"self": SELF, "config": "qa/config.py"}))
