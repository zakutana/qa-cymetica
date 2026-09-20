"""A refusal that does not say why leaves the caller nothing to ask for.

NEXUS turned away position-sizing questions about cloned bots with a bare
`QUERY_RESTRICTED` -- twice, with and without an instance id -- while giving
the same class of advice for event cards in full. We read that as a boundary
around bots and told them so as a gap rather than a defect (MSG-0029,
2026-09-20). Their answer corrected the premise: it is not a decision about
bots at all, but a wording filter that runs on the question text before NEXUS
sees it, and questions about clones tend to carry the words it looks for.
They reproduced it themselves and shipped the fix the same day.

What the refusal carries now, verified from outside with no credential at
11:4x UTC on 2026-09-20:

    error:     QUERY_RESTRICTED
    reason:    OTHER_USERS_DATA
    parameter: query
    hint:      "The wording of this parameter matched a restricted-topic
                filter. It is about the wording, not your identity or trust
                level. ..."

The distinction the hint draws is the one #93 is about in the other
direction: 401 says "who are you", 403 says "not for you", and a refusal that
says neither leaves an agent unable to tell "you may not" from "ask this a
different way". `reason` is a fixed label from their own vocabulary, never
free text, so nothing internal rides out with it.

This check exists because the fix is theirs to keep. The vocabulary may grow
-- that is their business and this does not police it -- but a refusal that
goes back to carrying no reason at all is a regression in a thing we asked
for and they built.

SAFE. One tools/call with a deliberately restricted wording, and one ordinary
call as the control, both read-only and both anonymous.
"""

from __future__ import annotations

from qa.client import McpError
from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

# Their own words for it, from the message that shipped the fix. Listed so a
# new label reads as new rather than as a failure; the check asserts that a
# reason is PRESENT and is a bare label, not that it is one of these.
KNOWN = ("OTHER_USERS_DATA", "PLATFORM_SECURITY", "PROPRIETARY_METHODS",
         "COMPANY_CONFIDENTIAL", "RESTRICTED_TOPIC")

# The wording they used to reproduce it: a clone copying a top trader.
RESTRICTED = "a clone that copies a top trader, how much should it size"
ORDINARY = "bitcoin"


def refusal_of(error: McpError) -> dict:
    """The tool-level payload inside the error, if it carries one.

    A tool failure arrives double-encoded, like every other MCP answer: the
    refusal is a JSON STRING inside `content[0].text`, not a dict one level
    down. The first version of this looked for a dict and found the envelope,
    so the check read "some other reason than the filter" over a payload that
    said QUERY_RESTRICTED in plain sight -- and said Inconclusive rather than
    failed, which is rule 10 doing its job while the reading was wrong.
    """
    import json

    payload = getattr(error, "payload", None)
    if not isinstance(payload, dict):
        return {}
    for key in ("error", "detail", "result"):
        inner = payload.get(key)
        if isinstance(inner, dict):
            payload = inner
            break
    content = payload.get("content")
    if isinstance(content, list) and content and isinstance(content[0], dict):
        text = content[0].get("text")
        if isinstance(text, str):
            try:
                decoded = json.loads(text)
            except ValueError:
                return payload
            if isinstance(decoded, dict):
                return decoded
    return payload


@qa(component="mcp.tools_call", tier=SafetyTier.SAFE, surface="mcp")
def test_a_restricted_query_says_which_rule_it_tripped(mcp_anon):
    """The refusal names its reason, the field, and that it is about wording."""
    try:
        answer = mcp_anon.call("search_markets", {"query": ORDINARY})
    except McpError as exc:
        raise Inconclusive(
            f"the control query was refused too, so this cannot tell a "
            f"restricted wording from a tool that is simply down: {exc}")
    if not answer:
        raise Inconclusive("the control query returned nothing, so the tool "
                           "is not answering and no refusal can be read")

    try:
        mcp_anon.call("search_markets", {"query": RESTRICTED})
    except McpError as exc:
        body = refusal_of(exc)
    else:
        raise Inconclusive(
            "the wording they used to reproduce the filter is no longer "
            "refused, so there is no refusal to read a reason off -- their "
            "filter's scope is theirs to set, and this is not a defect")

    if str(body.get("error") or "") != "QUERY_RESTRICTED":
        raise Inconclusive(
            f"the call failed for some other reason than the filter, so this "
            f"says nothing about how a refusal is worded: {str(body)[:160]}")

    reason = body.get("reason")
    missing = [k for k in ("reason", "parameter", "hint") if not body.get(k)]
    loose = (isinstance(reason, str)
             and (" " in reason.strip() or reason != reason.upper()))

    conclude(Measurement(
        verdict="failed" if (missing or loose) else "passed",
        reason=(
            f"QUERY_RESTRICTED carries no {', '.join(missing)}, so a caller "
            f"cannot tell 'you may not' from 'ask this a different way'"
            if missing else
            f"the reason is free text rather than a label ({reason!r}), which "
            f"is what keeps internal wording from riding out with a refusal"
            if loose else
            f"the refusal names reason {reason!r} on parameter "
            f"{body.get('parameter')!r} and a hint saying it is about the "
            f"wording"
            + ("" if reason in KNOWN else
               f"; {reason!r} is not one of the five labels they published, "
               f"which is theirs to extend and not a defect")),
        left={"fields": sorted(k for k in ("reason", "parameter", "hint")
                               if body.get(k))},
        right={"fields": ["hint", "parameter", "reason"]},
        sources={"tool": "search_markets"}))
