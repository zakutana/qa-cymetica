"""Does the credential the documents name actually open the routes they name?

agent-card.json lists two authentication schemes, bearer and `X-API-Key`.
agent-skills.json points the `et10-revenue-share` skill at GET
/api/v1/account/me with authentication_required true, and the
`portfolio-management` skill at GET /api/v1/account/me/portfolio the same way.

One of those two answers, and it is not the one an agent is sent to first.

Found while trying to answer a plain question -- am I eligible for the ET10
revenue share -- by following the platform's own machine-readable instructions
with the platform's own credential.
"""

from __future__ import annotations

import os

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

# Sibling routes under one prefix, both documented as authenticated, both
# reached with the identical header. Paired deliberately: the sibling is what
# turns "the key is wrong" into "the key is right and one route disagrees".
DOCUMENTED = "/api/v1/account/me"
SIBLING = "/api/v1/account/me/portfolio"


@qa(component="rest.account", tier=SafetyTier.SAFE, surface="rest",
    claim="account-me-rejects-its-documented-credential")
def test_the_documented_credential_opens_the_documented_route(rest_trusted):
    """An API key their own catalogue accepts must not be refused by a route
    their own catalogue sends an agent to.

    The comparison is what makes this a finding rather than a support
    question. If both routes refused, the honest reading would be that our key
    is not what we think it is -- so the sibling is called with the same
    client, in the same run, and it answers.
    """
    if not os.environ.get("QA_TRUSTED_KEY"):
        conclude(Measurement(
            verdict="inconclusive",
            reason="no credential is configured, so nothing can be asked",
            claim_id="account-me-rejects-its-documented-credential"))
        return

    documented = rest_trusted.get(DOCUMENTED)
    sibling = rest_trusted.get(SIBLING)

    if sibling.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=(f"the sibling route answered HTTP {sibling.status_code} "
                    f"too, so this cannot distinguish a route that refuses a "
                    f"good credential from a credential that is not good"),
            left=documented.status_code, right=sibling.status_code,
            claim_id="account-me-rejects-its-documented-credential"))
        return

    refused = documented.status_code in (401, 403)
    conclude(Measurement(
        verdict="failed" if refused else "passed",
        reason=(f"{DOCUMENTED} answers HTTP {documented.status_code} to the "
                f"same X-API-Key that opens {SIBLING} (HTTP 200) in the same "
                f"run. agent-skills.json sends the et10-revenue-share skill to "
                f"the first of those, so an agent following the catalogue to "
                f"check its own eligibility is refused"
                if refused else
                f"{DOCUMENTED} answers HTTP {documented.status_code} to the "
                f"credential the catalogue names"),
        left=f"{DOCUMENTED} -> {documented.status_code}",
        right=f"{SIBLING} -> {sibling.status_code}",
        sources={"schemes": "/.well-known/agent-card.json",
                 "skill": "/.well-known/agent-skills.json#et10-revenue-share"},
        population={"header": "X-API-Key", "same_client": True},
        claim_id="account-me-rejects-its-documented-credential"))
