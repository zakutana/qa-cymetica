"""An agent with no key can do step 1 of their own overnight loop.

Cymetica published `/guides/nexus-lab-loop` on 2026-09-12. Its step 0 says,
verbatim:

    Everything below is one endpoint: https://cymetica.com/mcp/v1 (JSON-RPC
    2.0 ...). The ground-truth tools need no key. Deep research needs a
    platform key -- create one at /account and send it as X-API-Key: evt_....

and its code block marks the header `# only for keyed tools`. Step 1 is headed
"Ground truth first (no key)" and names exactly three tools in its table:
`list_backtest_surfaces`, `get_backtest_models`, `get_strategy_returns`.

So the promise is not about a field or a count -- it is that a caller holding
no credential can complete the first step of the loop they are telling agents
to run. That is what this measures, and nothing else.

**It asks one question and takes any answer as a yes.** A tool that answers, a
tool that rejects our arguments, a tool that fails for its own reasons -- all
of those are the promise kept: none of them is a refusal for want of a key. It
fails only when the caller is turned away *because it has no credential*, and
the two ways that happens are both counted, because from the agent's side they
are the same wall:

  * the call is refused -- HTTP 401/403, or an error naming authentication;
  * the tool is not on the anonymous surface at all, so the call comes back
    unknown. `test_anonymous_receives_only_public_tools` already measures what
    anon is *served*; this one is about what anon can *do*.

Keeping the two apart in the reason matters for the report: "you refuse it"
and "you do not serve it to me" want different fixes, and it is theirs to
choose. Deliberately NOT asserted: that there are five surfaces, and the field
set of any answer. Both are theirs to change, and a check that pins them would
fail on a fix -- three times in one day on 2026-09-08, which is the memory
`a-check-encodes-the-fix-its-author-imagined`.
"""

from __future__ import annotations

import json
import re

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

# The three the guide's step-1 table names, in its order.
GROUND_TRUTH = (
    ("list_backtest_surfaces", {}),
    ("get_backtest_models", {}),
    # The guide's own example passes a slug: {"name":"get_strategy_returns",
    # "arguments":{"strategy":"<slug>"}}. Which slug does not matter here --
    # a slug they do not know is answered with their own not-found, which is
    # the promise kept. It is a real one so that the ordinary path is the one
    # exercised: `truth` ranked it top on 2026-09-12.
    ("get_strategy_returns", {"strategy": "stockbull-blue"}),
)

# Words an answer uses when the CREDENTIAL is what was wrong. Narrow on
# purpose: "invalid strategy" and "unknown slug" are not in here, because
# being told our argument is wrong means we were let in.
#
# **These are matched against a FAILURE and never against a body.** The first
# version of this check ran them over the whole JSON-RPC envelope, and both
# `list_backtest_surfaces` and `get_backtest_models` came back `success: true`
# and were reported as refusing us -- because a surface's row names its own
# `auth`, exactly as the guide's table promises it will ("the question each
# answers, its API and auth"). The vocabulary of authentication is the SUBJECT
# of those two tools, so a body-wide match can only ever be a false
# accusation, and it was one command short of a report. Memory
# `extract-from-text-anchor-on-markup`, in a new disguise: anchor on the
# structure that says the call failed, then read the words.
REFUSED_FOR_AUTH = re.compile(
    r"\b(unauthori[sz]ed|unauthenticated|authentication|api[_ -]?key|"
    r"forbidden|requires? (?:a )?(?:key|credential|token)|"
    r"permission denied|not authori[sz]ed)\b", re.I)

# What their surface says when a name is not one of its tools. Matched on the
# SHAPE of the word, not on a whole message, because the message is theirs.
NOT_SERVED = re.compile(r"\b(tool[_ ]?not[_ ]?found|unknown tool|"
                        r"no such tool|method not found)\b", re.I)


def failure_text(payload: dict) -> str | None:
    """What the answer said when it FAILED, or None when it did not fail.

    Three ways their transport reports a failure and one way it reports
    success, so this is the only place that decides which happened:

      * a JSON-RPC `error` beside the result;
      * `result.isError`, their tool-level failure flag;
      * `success: false` inside the double-encoded body content[0].text.

    Anything else is an answer, however much of it reads like an error
    message -- and for these three tools a great deal of it does.
    """
    if "error" in payload:
        return json.dumps(payload["error"], ensure_ascii=False)
    result = payload.get("result")
    if not isinstance(result, dict):
        return None

    content = result.get("content") or []
    text = content[0].get("text") if content and isinstance(content[0], dict) else None
    if result.get("isError"):
        return text or json.dumps(result, ensure_ascii=False)
    if isinstance(text, str):
        try:
            inner = json.loads(text)
        except json.JSONDecodeError:
            return None
        if isinstance(inner, dict) and inner.get("success") is False:
            return text
    return None


def _attempt(mcp, tool: str, arguments: dict) -> dict:
    """One anonymous call, classified. Never raises: an exception here is a
    reading we failed to take, and rule 8 says that is not an empty reading."""
    out: dict = {"tool": tool, "arguments": arguments}
    try:
        response = mcp.rpc("tools/call", {"name": tool, "arguments": arguments})
    except Exception as exc:  # noqa: BLE001 -- unreadable, not refused
        out["outcome"] = "unreadable"
        out["detail"] = f"{type(exc).__name__}: {exc}"[:200]
        return out

    out["status"] = response.status_code
    try:
        payload = response.json()
    except ValueError:
        out["outcome"] = "unreadable"
        out["detail"] = f"non-JSON body: {response.text[:120]!r}"
        return out

    if response.status_code in (401, 403):
        out["outcome"] = "refused"
        out["detail"] = f"HTTP {response.status_code}: {response.text[:200]!r}"
        return out

    failed = failure_text(payload)
    if failed is None:
        out["outcome"] = "answered"
        out["detail"] = json.dumps(payload, ensure_ascii=False)[:200]
        return out

    out["detail"] = failed[:300]
    if NOT_SERVED.search(failed):
        out["outcome"] = "not_served"
    elif REFUSED_FOR_AUTH.search(failed):
        out["outcome"] = "refused"
    else:
        # Their own failure, for their own reasons -- a rejected argument, a
        # slug they do not know, a bad minute on their side. We were let in,
        # which is the whole of what this check asks.
        out["outcome"] = "failed_on_its_own_terms"
    return out


def decide(attempts: list[dict]) -> tuple[str, str]:
    """verdict, reason. Pure, so the one branch that sends a vendor a pass can
    be held against its own inputs without calling their server.

    A wall is a wall whatever else happened, so a refusal still fails. But with
    no wall and a call we could not read, only some of the tools were measured
    and the claim is about all of them -- that concluded `passed`, with a reason
    that named two tools in a sentence beginning "all three". Their API dropped
    a TLS handshake at 20:55 on 2026-09-12, so the input is not hypothetical,
    and a pass from here is what a verification sends. Rule 8: a failed read is
    not an empty read, and it is not a clean bill of health either.
    """
    walls = [a for a in attempts if a["outcome"] in ("refused", "not_served")]
    answered = [a["tool"] for a in attempts
                if a["outcome"] in ("answered", "failed_on_its_own_terms")]

    if walls:
        refused = [a["tool"] for a in walls if a["outcome"] == "refused"]
        missing = [a["tool"] for a in walls if a["outcome"] == "not_served"]
        parts = []
        if refused:
            parts.append(f"{refused} refused an unauthenticated caller")
        if missing:
            parts.append(f"{missing} is not on the anonymous tool surface")
        return "failed", (
            '/guides/nexus-lab-loop says "The ground-truth tools need no key" '
            'and heads its step 1 "Ground truth first (no key)", but '
            + " and ".join(parts)
            + f"; {answered or 'none'} did answer")

    unreadable = [a for a in attempts if a["outcome"] == "unreadable"]
    if unreadable:
        return "inconclusive", (
            f"{[a['tool'] for a in unreadable]} could not be read "
            f"({[a['detail'] for a in unreadable]}), so a key was measured for "
            f"only {len(answered)} of the {len(attempts)} tools the guide names")

    return "passed", (
        f"all {len(answered)} ground-truth tools answered an unauthenticated "
        f"caller: {answered}")


@qa(component="mcp.tools_call", tier=SafetyTier.SAFE, surface="mcp",
    claim="ground_truth_needs_no_key")
def test_the_ground_truth_tools_answer_without_a_key(mcp_anon):
    """`/guides/nexus-lab-loop`: "The ground-truth tools need no key."

    Measured as the guide's own reader would meet it: three anonymous
    tools/call requests, in the order its step-1 table lists them.
    """
    attempts = [_attempt(mcp_anon, tool, args) for tool, args in GROUND_TRUTH]
    verdict, reason = decide(attempts)
    if verdict == "inconclusive":
        raise Inconclusive(reason)
    walls = [a for a in attempts if a["outcome"] in ("refused", "not_served")]

    conclude(Measurement(
        verdict=verdict,
        reason=reason,
        left=sorted(a["tool"] for a in walls),
        right={"promised": "no key", "tools": [t for t, _ in GROUND_TRUTH]},
        sources={"guide": "https://cymetica.com/guides/nexus-lab-loop",
                 "endpoint": "https://cymetica.com/mcp/v1"},
        population=attempts,
    ))
