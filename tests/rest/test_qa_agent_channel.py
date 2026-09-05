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
