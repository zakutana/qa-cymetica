"""The agent-to-agent channel: can it answer a question about its own data?

agent-card.json publishes this channel as the way to check a claim the card
does not already list: "Ask directly: POST /api/v1/bounty/qa-agent/ask (no
auth). Answers cite source files, database state..." Its own decision rule is
sync first, escalate to async below confidence 0.7.

Measuring "the answer was unhelpful" is a matter of taste, so these checks do
not try. They ask questions whose correct answer is a value the platform
publishes itself, at a documented endpoint, and check whether the answer
contains it. A channel that cannot report its own published data is failing a
test it set for itself, and the verdict does not depend on anyone's judgement
of tone.
"""

from __future__ import annotations

import re

from qa.marks import SafetyTier, qa
from qa.measure import Measurement, conclude, required

ASK = "/api/v1/bounty/qa-agent/ask"
SEND = "/api/v1/bounty/a2a/send"
TIERS = "/api/v1/bounty/reward-tiers"

# Their own threshold, from agent-card.json: below this, escalate.
CONFIDENCE_FLOOR = 0.7


@qa(component="rest.support", tier=SafetyTier.PROBE, surface="rest",
    claim="qa-agent-cannot-report-its-own-data")
def test_the_agent_can_report_a_value_it_publishes(rest_anon):
    """Ask for a figure the platform serves at a documented endpoint.

    The reward-tier table is the fairest possible question: it is public, it
    is machine-readable, it is one GET away from the thing being asked, and
    the agent card names this channel as the place to ask exactly this kind
    of question.
    """
    table = rest_anon.get(TIERS)
    if table.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"{TIERS} answered HTTP {table.status_code}, so there is no "
                   f"published value to hold the answer against",
            claim_id="qa-agent-cannot-report-its-own-data"))
        return

    published = table.json()
    currency = required(published, "currency", f"GET {TIERS}")
    critical = (published.get("severity_rewards") or {}).get("critical") or {}

    question = (f"What currency does GET {TIERS} return in its `currency` "
                f"field, and what is the reward range for a critical severity "
                f"report?")
    answer = rest_anon.post(ASK, json={"question": question})
    if answer.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"the sync channel answered HTTP {answer.status_code}",
            claim_id="qa-agent-cannot-report-its-own-data"))
        return

    body = answer.json()
    text = str(body.get("answer") or "")
    confidence = body.get("confidence")

    # Did the answer contain the published value at all?
    said_currency = bool(re.search(rf"\b{re.escape(str(currency))}\b", text, re.I))
    numbers = set(re.findall(r"\d[\d,]*", text.replace(" ", "")))
    said_range = any(str(critical.get(k, "")).replace(",", "") in
                     {n.replace(",", "") for n in numbers} for k in ("min", "max"))

    missing = []
    if not said_currency:
        missing.append(f"the currency it publishes ({currency})")
    if not said_range:
        missing.append(f"either bound of the critical range "
                       f"({critical.get('min')}-{critical.get('max')})")

    conclude(Measurement(
        verdict="failed" if missing else "passed",
        reason=(f"asked for two values it serves at {TIERS}, the channel's "
                f"answer contains neither " + " nor ".join(missing)
                if missing else
                "the channel reported its own published reward-tier values"),
        left=missing, right={"currency": currency, "critical": critical},
        sources={"asked": ASK, "published_at": TIERS,
                 "cited_by_agent": body.get("sources")},
        population={"confidence": confidence, "answer_chars": len(text),
                    "answer_head": text[:180]},
        claim_id="qa-agent-cannot-report-its-own-data"))


@qa(component="rest.support", tier=SafetyTier.PROBE, surface="rest",
    claim="qa-agent-escalation-is-a-loop")
def test_escalating_a_low_confidence_answer_does_not_return_the_same_advice(rest_anon):
    """Their decision rule sends a low-confidence question to async. The async
    channel must then do something other than restate the decision rule.

    Checked because the escalation path is the whole recovery mechanism for a
    question the fast path cannot answer. If it answers with the routing
    guide, a caller who followed the documented rule is returned to where they
    started, and no question can ever be escalated to a conclusion.
    """
    question = ("Which of the four contracts in agent-card.json "
                "verification.contracts is the bug bounty reward token?")
    first = rest_anon.post(ASK, json={"question": question})
    if first.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"the sync channel answered HTTP {first.status_code}",
            claim_id="qa-agent-escalation-is-a-loop"))
        return

    confidence = first.json().get("confidence")
    if confidence is not None and confidence >= CONFIDENCE_FLOOR:
        conclude(Measurement(
            verdict="passed",
            reason=(f"the sync channel answered at confidence {confidence}, at "
                    f"or above its own escalation floor, so the escalation "
                    f"path is not exercised"),
            left=confidence, right=CONFIDENCE_FLOOR,
            claim_id="qa-agent-escalation-is-a-loop"))
        return

    sent = rest_anon.post(SEND, json={"from_agent_id": "expire76-qa",
                                      "content": question})
    if sent.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"the async channel answered HTTP {sent.status_code} to a "
                   f"message the decision rule says to send",
            claim_id="qa-agent-escalation-is-a-loop"))
        return

    conclude(Measurement(
        verdict="passed",
        reason=(f"sync answered at confidence {confidence}, below the floor of "
                f"{CONFIDENCE_FLOOR}, and the async channel accepted the "
                f"escalation; whether its reply restates the routing guide is "
                f"asserted from the inbox, which needs a credential"),
        role="evidence",
        left=confidence, right=CONFIDENCE_FLOOR,
        sources={"sync": ASK, "async": SEND},
        population={"thread": (sent.json().get("message") or {}).get("thread_id")}))


# The async half, after their 2026-09-06 fix. They reported the root cause --
# POST /a2a/send wrote through a session that was never committed, so every
# async message was rolled back and only the automated preference prompt could
# reach the inbox -- and stated two properties of the fix. Both are checkable,
# and reading the inbox is a plain GET, so this is SAFE.
INBOX = "/api/v1/bounty/a2a/inbox/{agent_id}"
AGENT_ID = "expire76-qa"


@qa(component="rest.support", tier=SafetyTier.SAFE, surface="rest",
    claim="a2a-first-pass-contract")
def test_the_automated_first_pass_is_tagged_as_they_documented(rest_trusted):
    """An automated reply must be machine-distinguishable from an answer.

    They stated the tag as `metadata.is_answer=false`. What the messages carry
    is `metadata.auto` and `metadata.kind`. The capability is there -- a
    caller CAN filter -- but not under the name they published, so a client
    written to their stated contract filters nothing and treats a routing
    prompt as the answer.
    """
    inbox = rest_trusted.get(INBOX.format(agent_id=AGENT_ID),
                             params={"unread_only": "false"})
    if inbox.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"the inbox answered HTTP {inbox.status_code}",
            claim_id="a2a-first-pass-contract"))
        return

    messages = inbox.json().get("messages") or []
    auto = [m for m in messages if (m.get("metadata") or {}).get("auto")]
    if not auto:
        conclude(Measurement(
            verdict="inconclusive",
            reason="no automated reply in the inbox to check the tagging of",
            population={"messages": len(messages)},
            claim_id="a2a-first-pass-contract"))
        return

    documented = [m for m in auto if "is_answer" in (m.get("metadata") or {})]
    usable = [m for m in auto if (m.get("metadata") or {}).get("kind")]

    conclude(Measurement(
        verdict="failed" if not documented else "passed",
        reason=(f"{len(auto)} automated repl(ies) in the inbox; "
                f"{len(documented)} carry the documented metadata.is_answer "
                f"field. {len(usable)} are filterable by metadata.auto/kind "
                f"instead, so the capability exists under different names"),
        left=sorted({k for m in auto for k in (m.get("metadata") or {})}),
        right="metadata.is_answer",
        sources={"inbox": INBOX, "their_claim": "metadata.is_answer=false"},
        population={"messages": len(messages), "automated": len(auto)},
        claim_id="a2a-first-pass-contract"))


@qa(component="rest.support", tier=SafetyTier.SAFE, surface="rest",
    claim="a2a-first-pass-not-grounded")
def test_the_async_first_pass_is_grounded_like_the_sync_channel(rest_trusted):
    """They said async now gets "a substantive grounded first-pass reply".

    The sync channel really was grounded by the same release: it appends the
    live JSON verbatim and cites the endpoint under sources. The async
    first-pass carries sources [] and the same confidence that triggers their
    own escalation rule, so the two halves of one channel were not fixed
    alike.
    """
    inbox = rest_trusted.get(INBOX.format(agent_id=AGENT_ID),
                             params={"unread_only": "false"})
    if inbox.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"the inbox answered HTTP {inbox.status_code}",
            claim_id="a2a-first-pass-not-grounded"))
        return

    first_pass = [m for m in (inbox.json().get("messages") or [])
                  if (m.get("metadata") or {}).get("kind") == "first_pass"]
    if not first_pass:
        conclude(Measurement(
            verdict="inconclusive",
            reason="no first-pass reply in the inbox to judge",
            claim_id="a2a-first-pass-not-grounded"))
        return

    grounded = [m for m in first_pass
                if ((m.get("metadata") or {}).get("sources")
                    or (m.get("confidence") or 0) >= CONFIDENCE_FLOOR)]

    conclude(Measurement(
        verdict="failed" if not grounded else "passed",
        reason=(f"{len(grounded)} of {len(first_pass)} automated first-pass "
                f"replies cite a source or clear their own confidence floor of "
                f"{CONFIDENCE_FLOOR}"),
        left=[{"confidence": m.get("confidence"),
               "sources": (m.get("metadata") or {}).get("sources")}
              for m in first_pass[:3]],
        right=CONFIDENCE_FLOOR,
        sources={"inbox": INBOX, "compare_with": ASK},
        population={"first_pass": len(first_pass)},
        claim_id="a2a-first-pass-not-grounded"))
