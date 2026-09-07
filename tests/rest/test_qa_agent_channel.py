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

# Asked of the sync half to establish the baseline the async half is measured
# against. Deliberately a question their own FAQ answers, so an ungrounded
# reply to it is about the channel and not about the question being obscure.
SYNC_PROBE = "What currency does the bounty programme pay rewards in?"


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
    #
    # Compared as NUMBERS, not as strings. The published figures were integers
    # and str(400000) matched a digit run of "400000"; on 2026-09-07 the
    # programme became a flat 1000.0 per verified bug, str() gave "1000.0",
    # the digit extractor gives "1000", and a channel answering "1000 ET10"
    # correctly was reported as unable to state its own reward range. Their
    # change, our failure -- a comparison that depends on how a number happens
    # to be spelled is not a measurement of what was said.
    said_currency = bool(re.search(rf"\b{re.escape(str(currency))}\b", text, re.I))

    spoken: set[float] = set()
    for run_of_digits in re.findall(r"\d[\d,]*", text.replace(" ", "")):
        try:
            spoken.add(float(run_of_digits.replace(",", "")))
        except ValueError:
            continue

    def _published(key):
        try:
            return float(critical[key])
        except (KeyError, TypeError, ValueError):
            return None

    said_range = any(_published(k) in spoken for k in ("min", "max")
                     if _published(k) is not None)

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


def _grounded(sources, confidence) -> bool:
    """One definition, applied to both halves of the channel."""
    return bool(sources) or (confidence or 0) >= CONFIDENCE_FLOOR


@qa(component="rest.support", tier=SafetyTier.PROBE, surface="rest",
    claim="a2a-first-pass-not-grounded")
def test_the_async_first_pass_is_grounded_like_the_sync_channel(rest_anon, rest_trusted):
    """They said async now gets "a substantive grounded first-pass reply".

    The claim is an ASYMMETRY -- that the sync half of one channel cites its
    sources and the async half does not -- so both halves are read in the same
    run, under one definition of grounded. The check used to assert the sync
    side from this docstring and measure only the async side, which meant a
    day when both stopped citing sources would still have been reported as the
    async half lagging. That is a different and larger defect, and filing it
    under this id would misstate it; it comes out inconclusive instead.

    It also used to judge every first_pass reply the inbox had ever held, and
    fail unless one of them was grounded. A reply that predates their fix is
    not evidence about their platform now: with no new message sent after a
    fix, the check would have gone on failing and a re-report would have said
    "still broken" about something repaired. Rule 7 needs the run to measure
    behaviour AFTER the claim, so the verdict is on the newest reply, with the
    older ones kept in `population` as context.

    Costs one question to the sync channel per sweep. Measuring the comparison
    the finding is named after is worth a question.
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

    sync = rest_anon.post(ASK, json={"question": SYNC_PROBE})
    if sync.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"the sync half answered HTTP {sync.status_code}, so there "
                   f"is nothing to hold the async half against",
            claim_id="a2a-first-pass-not-grounded"))
        return

    sync_body = sync.json()
    sync_sources = sync_body.get("sources") or []
    sync_grounded = _grounded(sync_sources, sync_body.get("confidence"))

    newest = max(first_pass, key=lambda m: str(m.get("created_at") or ""))
    newest_meta = newest.get("metadata") or {}
    newest_sources = newest_meta.get("sources") or []
    async_grounded = _grounded(newest_sources, newest.get("confidence"))

    grounded_all = [m for m in first_pass
                    if _grounded((m.get("metadata") or {}).get("sources"),
                                 m.get("confidence"))]

    if not sync_grounded and not async_grounded:
        conclude(Measurement(
            verdict="inconclusive",
            reason=("neither half of the channel cites a source, so this is "
                    "not the asymmetry this claim is about -- the sync half "
                    "is the baseline it is measured against"),
            left={"sync": sync_sources, "async": newest_sources},
            right=CONFIDENCE_FLOOR,
            sources={"inbox": INBOX, "sync": ASK},
            population={"first_pass": len(first_pass)},
            claim_id="a2a-first-pass-not-grounded"))
        return

    conclude(Measurement(
        verdict="passed" if async_grounded else "failed",
        reason=(f"the newest async first-pass reply ({newest.get('created_at')}) "
                f"cites {len(newest_sources)} source(s) at confidence "
                f"{newest.get('confidence')}, while the sync half cites "
                f"{len(sync_sources)} at {sync_body.get('confidence')}; "
                f"{len(grounded_all)} of {len(first_pass)} replies in the "
                f"inbox are grounded at all"),
        left={"async_newest": {"at": newest.get("created_at"),
                               "confidence": newest.get("confidence"),
                               "sources": newest_sources},
              "sync": {"confidence": sync_body.get("confidence"),
                       "sources": sync_sources}},
        right=CONFIDENCE_FLOOR,
        sources={"inbox": INBOX, "sync": ASK},
        population={"first_pass": len(first_pass),
                    "grounded": len(grounded_all)},
        claim_id="a2a-first-pass-not-grounded"))
