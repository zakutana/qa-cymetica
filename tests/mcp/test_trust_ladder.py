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

# mcp.json assigns each tool one of these, lowest first. A caller at a given
# tier should receive that tier's tools and everything below it -- no more.
LADDER = ["unknown", "recognized", "trusted", "allied"]


def declared_by_tier(rest) -> dict[str, set[str]]:
    manifest = rest.get("/.well-known/mcp.json").json()
    out: dict[str, set[str]] = {tier: set() for tier in LADDER}
    for tool in manifest.get("tools", []):
        tier = tool.get("trust_tier")
        if tier in out:
            out[tier].add(tool["name"])
    return out


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
    ticket="CYM-anon-tool-surface")
def test_anonymous_receives_only_public_tools(mcp_anon, rest_anon):
    """The regression check for report #46. Must keep passing."""
    declared = declared_by_tier(rest_anon)
    served = mcp_anon.tool_names()
    entitled = declared["unknown"]
    assert served <= entitled, _report("anonymous", served, entitled, declared)


@qa(component="mcp.trust_ladder", tier=SafetyTier.SAFE, surface="mcp")
def test_trusted_receives_nothing_above_its_tier(mcp_trusted, rest_anon):
    """The same question one tier up, which report #46 did not cover."""
    declared = declared_by_tier(rest_anon)
    served = mcp_trusted.tool_names()
    entitled = entitled_up_to(declared, "trusted")
    assert served <= entitled, _report("TRUSTED", served, entitled, declared)


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
    result = payload.get("result", {})
    body = str(result.get("content", [{}])[0].get("text", "")) + str(payload.get("error", ""))

    assert result.get("isError"), (
        f"\nAnonymous tools/call on {tool!r} did not report an error.\n"
        f"Response: {str(payload)[:400]}"
    )
    assert "INSUFFICIENT_TRUST" in body.upper() or "TRUST" in body.upper(), (
        f"\nAnonymous tools/call on {tool!r} failed, but not with a trust error.\n"
        f"That is a different failure mode and does not establish the gate held.\n"
        f"Body: {body[:300]}"
    )
