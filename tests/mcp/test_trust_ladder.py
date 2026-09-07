"""Trust ladder: does the tier a tool is declared at match the tier served?

Kept out of the generic reconciliation table on purpose. These compare a
DECLARED tier against a SERVED one, which the pairwise machinery would flatten
into "two numbers differ" -- and the whole value here is knowing which tools,
at which tier, in which direction.

Written after the vendor fixed the anonymous case (report #46: a falsy-default
on TrustLevel.UNKNOWN, which is IntEnum 0, escalated anonymous listings to the
full ALLIED set). The same question has to be asked one tier up, because a fix
that only corrects the tier it was reported at is not a fix for the class.
"""

from __future__ import annotations

import pytest

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude

# mcp.json assigns each tool one of these, lowest first. A caller at a given
# tier should receive that tier's tools and everything below it -- no more.
LADDER = ["unknown", "recognized", "trusted", "allied"]


def declared_by_tier(rest) -> dict[str, set[str]]:
    """Tools grouped by the tier the manifest declares for them.

    A tool whose tier we do not recognise used to be dropped here, silently
    shrinking the entitled set -- which makes the check quietly stricter and
    would read as the platform over-serving. An unrecognised tier is now
    named, so the answer is "we could not measure" rather than a finding.
    """
    manifest = rest.get("/.well-known/mcp.json").json()
    out: dict[str, set[str]] = {tier: set() for tier in LADDER}
    unrecognised: dict[str, str] = {}
    for tool in manifest.get("tools", []):
        tier = tool.get("trust_tier")
        if tier in out:
            out[tier].add(tool["name"])
        else:
            unrecognised[tool.get("name", "<unnamed>")] = tier
    if unrecognised:
        conclude(Measurement(
            verdict="inconclusive",
            reason=(f"mcp.json declares {len(unrecognised)} tool(s) at a tier "
                    f"this check does not know, so the entitled set cannot be "
                    f"computed: {unrecognised}"),
            left=sorted(unrecognised), right=LADDER,
            sources={"manifest": "/.well-known/mcp.json"},
        ))
    return out


SELF = "/mcp/v1/agents/me"


def own_tier(rest) -> tuple[str | None, str]:
    """The tier the PLATFORM assigns this caller, read from the platform.

    This is the whole difference between report #54 and a measurement. That
    report asserted over-serving from a tier taken out of OUR OWN config file
    -- the variable is named QA_TRUSTED_KEY, so the check demanded trusted
    entitlement. The vendor rejected it as invalid: the key is ALLIED on their
    side, and an ALLIED caller receiving allied tools is correct.

    They were right, and our labels could never have settled it. They then
    named the endpoint that can: it returns the caller's own trust_level, so
    the tier is now the platform's answer about itself and the check compares
    two of their statements instead of one of theirs against one of ours.
    """
    response = rest.get(SELF)
    if response.status_code != 200:
        return None, f"{SELF} answered HTTP {response.status_code}"
    tier = str((response.json() or {}).get("trust_level") or "").lower()
    if not tier:
        return None, f"{SELF} answered 200 but stated no trust_level"
    if tier not in LADDER:
        return None, f"{SELF} reports tier {tier!r}, which is not on the ladder {LADDER}"
    return tier, ""


REFUSAL_CLASSES = ("refused_authz", "refused_validation", "executed", "unknown")

_AUTHZ_WORDS = ("trust", "unauthor", "authoriz", "authenticat", "forbidden",
                "permission", "not allowed", "denied", "credential", "api key")
_VALIDATION_WORDS = ("required", "missing", "invalid", "validation", "schema",
                     "must be", "expected", "parameter", "field")


def refusal_class(payload: dict) -> tuple[str, str]:
    """How the platform refused, as a class rather than as a phrase.

    The old assertion was `"TRUST" in body.upper()` -- a check on the vendor's
    WORDING. Rewording their error message would have broken it, and a
    validation error that happened to contain the word "trust" would have
    passed it. What we need to know is the ORDER: does authorization run
    before the arguments are looked at?

    So a validation error is a FAILURE, not a pass. It means the call got far
    enough to have its arguments inspected, which is exactly where an
    unauthorized caller should never arrive (methodology 2.5). The vocabulary
    below only CLASSIFIES the refusal; an answer that fits no class is
    Inconclusive, never a quiet pass.
    """
    result = payload.get("result") or {}
    content = result.get("content") or [{}]
    text = str(content[0].get("text", "")) if content else ""
    body = f"{text} {payload.get('error', '')}".strip()
    lowered = body.lower()

    # "Executed" is the only branch that used to be decided by the ABSENCE of
    # two markers without reading the body it already holds -- and `isError`
    # is optional in MCP and defaults false. Their live refusal is
    # {"content":[{"text":"{\"error\": \"INSUFFICIENT_TRUST\"}"}],"isError":true};
    # served without the flag it classified as executed, and the check
    # concluded "an anonymous caller EXECUTED the tool" -- an S1
    # authorization-bypass accusation against a response whose own text
    # refuses the call. An HTTP error body reaches here the same way, because
    # rpc() does not raise for status.
    #
    # So the vocabulary is consulted first, and the absence of markers is only
    # believed when the text says nothing that sounds like a refusal.
    if not result.get("isError") and "error" not in payload:
        if any(word in lowered for word in _AUTHZ_WORDS):
            return "refused_authz", body
        if any(word in lowered for word in _VALIDATION_WORDS):
            return "refused_validation", body
        if "error" in lowered:
            # It says error and carries no flag: we cannot tell execution from
            # a refusal we do not have the vocabulary for. Never a quiet
            # accusation.
            return "unknown", body
        return "executed", body
    if any(word in lowered for word in _AUTHZ_WORDS):
        return "refused_authz", body
    if any(word in lowered for word in _VALIDATION_WORDS):
        return "refused_validation", body
    return "unknown", body


def entitled_up_to(declared: dict[str, set[str]], tier: str) -> set[str]:
    """Everything at `tier` and below."""
    return set().union(*(declared[t] for t in LADDER[: LADDER.index(tier) + 1]))


def _report(label: str, served: set[str], entitled: set[str],
            declared: dict[str, set[str]]) -> str:
    above = sorted(served - entitled)
    by_tier: dict[str, list[str]] = {}
    for name in above:
        for tier, names in declared.items():
            if name in names:
                by_tier.setdefault(tier, []).append(name)
    lines = [
        "",
        f"IDENTITY   {label}",
        f"SERVED     {len(served)} tools",
        f"ENTITLED   {len(entitled)} tools (its own tier and below, per mcp.json)",
        f"EXCESS     {len(above)} tools above the tier declared for them",
        "",
    ]
    for tier, names in sorted(by_tier.items()):
        lines.append(f"  declared {tier}: {', '.join(sorted(names))}")
    missing = sorted(entitled - served)
    if missing:
        lines += ["", f"  ALSO entitled but NOT served: {missing}"]
    return "\n".join(lines)


@qa(component="mcp.trust_ladder", tier=SafetyTier.SAFE, surface="mcp",
    ticket="CYM-anon-tool-surface", claim="anon-tool-surface")
def test_anonymous_receives_only_public_tools(mcp_anon, rest_anon):
    """The regression check for report #46. Must keep passing."""
    declared = declared_by_tier(rest_anon)
    served = mcp_anon.tool_names()
    entitled = declared["unknown"]
    assert served <= entitled, _report("anonymous", served, entitled, declared)


@qa(component="mcp.trust_ladder", tier=SafetyTier.SAFE, surface="mcp",
    claim="trusted-receives-nothing-above-its-tier")
def test_credentialed_caller_receives_nothing_above_its_own_tier(mcp_trusted, rest_trusted, rest_anon):
    """Served tools must not exceed the tier the platform says we hold.

    Both sides of this comparison are now the vendor's own statements: the
    tier from GET /mcp/v1/agents/me, the entitlement from mcp.json's per-tool
    trust_tier. Nothing here depends on what we call our key.
    """
    tier, why = own_tier(rest_trusted)
    if tier is None:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"cannot read the tier the platform assigns us: {why}",
            sources={"identity": SELF},
            claim_id="trusted-receives-nothing-above-its-tier"))
        return

    declared = declared_by_tier(rest_anon)
    served = mcp_trusted.tool_names()
    entitled = entitled_up_to(declared, tier)
    above = sorted(served - entitled)

    conclude(Measurement(
        verdict="failed" if above else "passed",
        reason=(f"the platform states this caller is {tier.upper()}; it is served "
                f"{len(served)} tools, {len(above)} of them declared above {tier}"),
        left=above, right=tier,
        sources={"tier_from": SELF, "entitlement_from": "/.well-known/mcp.json"},
        population={"served": len(served), "entitled_at_" + tier: len(entitled),
                    "declared_total": sum(len(v) for v in declared.values())},
        claim_id="trusted-receives-nothing-above-its-tier"))


@qa(component="mcp.trust_ladder", tier=SafetyTier.SAFE, surface="mcp")
def test_every_served_tool_is_declared_somewhere(mcp_trusted, rest_anon):
    """A served tool that no manifest tier claims cannot be adjudicated at all.

    Without this the check above has a blind spot in our favour: an undeclared
    tool falls outside every tier set, so it can never count as excess. That
    is the reverse of the failure it is meant to catch -- serving something
    the catalogue never described.
    """
    declared = declared_by_tier(rest_anon)
    everything = set().union(*declared.values())
    undeclared = sorted(mcp_trusted.tool_names() - everything)

    conclude(Measurement(
        verdict="failed" if undeclared else "passed",
        reason=(f"{len(undeclared)} served tool(s) carry no trust_tier in "
                f"mcp.json, so no tier can be checked for them"),
        left=undeclared, right=len(everything),
        sources={"catalogue": "/.well-known/mcp.json", "served": "tools/list"}))


@qa(component="mcp.trust_ladder", tier=SafetyTier.SAFE, surface="mcp")
def test_higher_tier_is_a_superset_of_lower(mcp_anon, mcp_trusted):
    """Authentication must not REDUCE what you can see.

    Worth asserting because the handoff recorded the opposite on 2026-08-28:
    27 tools at TRUSTED against 46 anonymous. We never measured that ourselves,
    so it is recorded here as a check rather than as a finding.
    """
    anon = mcp_anon.tool_names()
    trusted = mcp_trusted.tool_names()
    lost = sorted(anon - trusted)
    assert not lost, (
        f"\nA TRUSTED key sees {len(trusted)} tools; anonymous sees {len(anon)}.\n"
        f"These {len(lost)} are served anonymously but NOT to the credentialed "
        f"caller:\n  {lost}"
    )


@qa(component="mcp.trust_ladder", tier=SafetyTier.PROBE, surface="mcp")
@pytest.mark.parametrize("tool", ["place_order", "create_aib_fund",
                                  "get_deposit_address"])
def test_call_time_authorization_holds_for_anonymous(mcp_anon, tool):
    """Listing a tool is not the same as being allowed to call it.

    The vendor's resolution on #46 claimed call-time authorization was
    unaffected by the listing bug. This is that claim as a standing check:
    empty arguments, so nothing can execute whatever the answer, and we read
    only the error class.
    """
    payload = mcp_anon.call_raw(tool, {})
    klass, body = refusal_class(payload)

    verdicts = {
        "refused_authz": ("passed",
                          "authorization ran first and refused the call"),
        "refused_validation": ("failed",
                               "the call reached ARGUMENT VALIDATION, so "
                               "authorization did not run first -- an "
                               "unauthorized caller must never get this far"),
        "executed": ("failed", "an anonymous caller EXECUTED the tool"),
        "unknown": ("inconclusive",
                    "the refusal fits no class we recognise, so it does not "
                    "establish that the gate held"),
    }
    verdict, why = verdicts[klass]

    conclude(Measurement(
        verdict=verdict,
        reason=f"anonymous tools/call on {tool!r}: {klass} -- {why}",
        left=klass, right="refused_authz",
        sources={"tool": tool, "identity": "anonymous"},
        population={"body": body[:300]},
        claim_id="call_time_authorization",
    ))
