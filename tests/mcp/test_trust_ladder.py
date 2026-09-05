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

    if not result.get("isError") and "error" not in payload:
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
def test_trusted_receives_nothing_above_its_tier(mcp_trusted, rest_anon):
    """The same question one tier up, which report #46 did not cover.

    The tier is the platform's to state, not ours to assume. This check took
    the key's tier from OUR OWN configuration -- the file calls it "trusted",
    so the check demanded trusted-tier entitlement. The vendor rejected report
    #54 as invalid on exactly that point: the key is ALLIED on their side, and
    an ALLIED caller receiving allied tools is correct behaviour.

    They may be right, and our own labels cannot settle it. So while the
    platform gives us no way to read the tier IT assigns to a caller, this is
    Inconclusive -- naming the tools, so the question stays visible and
    answerable -- rather than a failure asserted on our own assumption.
    """
    declared = declared_by_tier(rest_anon)
    served = mcp_trusted.tool_names()
    entitled = entitled_up_to(declared, "trusted")
    above = sorted(served - entitled)

    if not above:
        conclude(Measurement(
            verdict="passed",
            reason="the credentialed caller receives nothing above the trusted tier",
            left=len(served), right=len(entitled),
            claim_id="trusted-receives-nothing-above-its-tier"))
        return

    by_tier: dict[str, list[str]] = {}
    for name in above:
        for tier_name, names in declared.items():
            if name in names:
                by_tier.setdefault(tier_name, []).append(name)

    conclude(Measurement(
        verdict="inconclusive",
        reason=(f"Our key is served {len(above)} tools above the trusted tier "
                f"({', '.join(f'{k}: {len(v)}' for k, v in sorted(by_tier.items()))}). "
                f"Whether that is over-serving or correct depends on the tier "
                f"the platform assigns this key, and it exposes no way to read "
                f"that -- get_trust_signal requires a parameter we cannot supply "
                f"for ourselves. Report #54 was rejected as invalid on the "
                f"grounds that the key is ALLIED, which would make this correct."),
        left=above, right=sorted(entitled),
        sources={"manifest": "/.well-known/mcp.json", "identity": "our API key"},
        population={"served": len(served), "entitled_at_trusted": len(entitled)},
        claim_id="trusted-receives-nothing-above-its-tier"))


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
