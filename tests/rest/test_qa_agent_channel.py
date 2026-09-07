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
import time

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

# Asked of the async half in the same run, so the two are compared on answers
# to the same kind of question rather than on whatever the inbox happened to
# hold. Deliberately answerable from their own published data.
ASYNC_PROBE = ("What currency does the bounty programme pay rewards in, and "
               "what is the flat amount per verified bug?")

# Their first-pass answered in about a second when measured by hand. This is
# slack for a slow morning, not an expectation; polling stops at the reply, and
# running out of it is inconclusive rather than a defect on their side.
REPLY_WAIT_SECONDS = 25


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


def tagging_gap(automated: list) -> tuple[int | None, list]:
    """(index where they began tagging, the ones since that are not tagged).

    Their rule, self-calibrated. Pulled out of the check so it can be held
    against cases the live inbox does not currently contain -- this check has
    been wrong three times in one day, twice in a way its own docstring
    contradicted, and each time the live data happened to agree with the
    mistake. See tests/meta/test_pipeline_check_quality.py.
    """
    def tagged(message) -> bool:
        return isinstance((message.get("metadata") or {}).get("is_answer"), bool)

    ordered = sorted(automated, key=lambda m: m.get("created_at") or "")
    started = next((i for i, m in enumerate(ordered) if tagged(m)), None)
    if started is None:
        return None, []
    return started, [m for m in ordered[started:] if not tagged(m)]


@qa(component="rest.support", tier=SafetyTier.SAFE, surface="rest",
    claim="a2a-first-pass-contract")
def test_the_automated_first_pass_is_tagged_as_they_documented(rest_trusted):
    """An automated reply must be machine-distinguishable from an answer.

    They stated the tag as `metadata.is_answer=false`. What the messages
    carried when this was written was `metadata.auto` and `metadata.kind`: the
    capability was there -- a caller COULD filter -- but not under the name
    they published, so a client written to their stated contract filtered
    nothing and treated a routing prompt as the answer.

    Third version. The first two were wrong the same way: neither measured the
    contract it named.

    v1 asked whether the key was PRESENT, so it went green the moment the
    field existed, whatever it said. A PASS verification for it reached their
    server on 2026-09-07 at 13:33.

    v2, written hours later on finding that, asked whether every auto-tagged
    message carried `is_answer: false` -- reading their contract as "automated
    implies not an answer". Their resolution on #67 says the opposite in as
    many words: "metadata.is_answer=true now set on every substantive answer
    (async first-pass, reviewer reply, cross-thread reply); the
    routing/preference prompt carries is_answer=false". Two questions that v2
    collapsed into one: `auto` and `kind` say HOW a message was produced,
    `is_answer` says WHETHER IT ANSWERS. A first pass is automated and it does
    answer -- ten of them carry `sources` -- so `true` is right, and v2 sent
    them a FAIL verification at 13:54 for behaving exactly as they said.

    What the inbox says, read before this was written: every message up to
    2026-09-06T08:47 carries `is_answer: null`, and all fifteen from
    2026-09-06T11:07 onward carry `true`. Their fix landed and has held for 27
    hours without exception.

    So this asks THEIR question. Find the first message that carries the tag;
    from there on, every one must. Self-calibrating, so there is no date
    constant to update the next time they ship, it cannot stay red on history
    nobody can now change, and it goes red the moment an untagged reply
    arrives after a tagged one. Zero tagged messages is the original defect
    and fails.
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

    ordered = sorted(auto, key=lambda m: m.get("created_at") or "")
    started, missing = tagging_gap(auto)
    if started is None:
        # The original defect: the field they published does not exist, so a
        # client written to their contract can filter nothing.
        conclude(Measurement(
            verdict="failed",
            reason=(f"none of the {len(auto)} automated repl(ies) carries "
                    f"metadata.is_answer, the field they documented as the way "
                    f"to tell a reply from an answer"),
            left=sorted({k for m in auto for k in (m.get("metadata") or {})}),
            right="metadata.is_answer",
            sources={"inbox": INBOX, "their_claim": "metadata.is_answer"},
            population={"messages": len(messages), "automated": len(auto)},
            claim_id="a2a-first-pass-contract"))
        return

    since = ordered[started:]
    untagged = [m.get("created_at") for m in missing]
    # Their rule, not ours: a first pass answers, so it is tagged true. The
    # routing prompt does not, and is tagged false. Reported either way,
    # because a first pass tagged false would be them contradicting their own
    # resolution and is worth seeing without being asserted here.
    answers = sum(1 for m in since
                  if (m.get("metadata") or {}).get("is_answer") is True)

    conclude(Measurement(
        verdict="failed" if untagged else "passed",
        reason=(f"{len(untagged)} automated repl(ies) since they began tagging "
                f"at {ordered[started].get('created_at')} carry no "
                f"metadata.is_answer: {', '.join(str(u) for u in untagged)}"
                if untagged else
                f"every one of the {len(since)} automated repl(ies) since "
                f"{ordered[started].get('created_at')} carries "
                f"metadata.is_answer ({answers} of them true, which is their "
                f"rule for a substantive answer)"),
        left=len(since) - len(untagged), right=len(since),
        sources={"inbox": INBOX,
                 "their_claim": "is_answer=true on every substantive answer; "
                                "false on the routing/preference prompt"},
        population={"messages": len(messages), "automated": len(auto),
                    "before_they_began_tagging": started,
                    "tagging_began": ordered[started].get("created_at"),
                    "untagged_since": untagged,
                    "kinds": sorted({(m.get("metadata") or {}).get("kind")
                                     for m in auto} - {None})},
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

    And it ASKS, rather than judging whatever the inbox happens to hold. On
    2026-09-07 they reported the async half grounded since 00:25; the newest
    reply we had was from 22:12 the evening before, so the check would have
    gone on failing against evidence older than the fix it was meant to judge,
    and no amount of re-running would have changed that -- reading an inbox
    does not put anything in it. A check that judges only fresh evidence has
    to be able to produce some. Clearing a finding needs a measurement taken
    after the claim, which is rule 7, and this is what that costs.

    Two questions per sweep, one to each half. Measuring the comparison the
    finding is named after, on evidence this run produced, is worth two.
    """
    sent = rest_anon.post(SEND, json={"from_agent_id": AGENT_ID,
                                      "content": ASYNC_PROBE})
    if sent.status_code != 200:
        conclude(Measurement(
            verdict="inconclusive",
            reason=f"the async channel answered HTTP {sent.status_code} to the "
                   f"question this check exists to have answered",
            claim_id="a2a-first-pass-not-grounded"))
        return
    asked = (sent.json().get("message") or {}).get("id")

    # The sync half goes now, while their async pipeline is working on the
    # question just sent, rather than after the reply has been waited for.
    # Sequentially this check took 62s, most of it two waits that do not
    # depend on each other. It also puts the two measurements within seconds
    # of each other, which a comparison between them wants anyway.
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

    # Their first-pass came back inside a second when measured by hand, so
    # this is slack rather than an expectation. Polling stops at the reply.
    reply = None
    deadline = time.monotonic() + REPLY_WAIT_SECONDS
    while reply is None and time.monotonic() < deadline:
        time.sleep(2.0)
        inbox = rest_trusted.get(INBOX.format(agent_id=AGENT_ID),
                                 params={"unread_only": "false"})
        if inbox.status_code != 200:
            conclude(Measurement(
                verdict="inconclusive",
                reason=f"the inbox answered HTTP {inbox.status_code}",
                claim_id="a2a-first-pass-not-grounded"))
            return
        messages = inbox.json().get("messages") or []
        first_pass = [m for m in messages
                      if (m.get("metadata") or {}).get("kind") == "first_pass"]
        # Matched to OUR message, not merely to the clock: two runs overlapping,
        # or anyone else on this agent id, would otherwise let one run judge
        # another's evidence.
        for m in first_pass:
            if (m.get("metadata") or {}).get("in_reply_to") == asked:
                reply = m
                break

    if reply is None:
        # Evidence, not inconclusive, and the distinction is load-bearing.
        # INCONCLUSIVE on a filed row opens a repair_check obligation
        # (qa/fold.py, gap 3) -- "a filed row whose check measures nothing is
        # a broken check wearing a resolved defect's clothes". That is right
        # when the check CANNOT measure, and wrong here: their agent thinking
        # for a while, or being down for an hour, is not our check breaking,
        # and the page would have told the operator to repair something that
        # works. An evidence-role measurement is recorded and moves no state,
        # so the row keeps whatever the last run that got an answer
        # established, which is exactly what we know.
        conclude(Measurement(
            verdict="inconclusive",
            role="evidence",
            reason=(f"asked {asked} and no first-pass reply arrived within "
                    f"{REPLY_WAIT_SECONDS}s. Their side, not ours, and not a "
                    f"defect: this run simply measured nothing about how the "
                    f"async half grounds an answer"),
            left=asked, right=REPLY_WAIT_SECONDS,
            sources={"asked": SEND, "inbox": INBOX},
            population={"first_pass_in_inbox": len(first_pass)},
            claim_id="a2a-first-pass-not-grounded"))
        return

    reply_sources = (reply.get("metadata") or {}).get("sources") or []
    async_grounded = _grounded(reply_sources, reply.get("confidence"))

    if not sync_grounded and not async_grounded:
        conclude(Measurement(
            verdict="inconclusive",
            reason=("neither half of the channel cites a source, so this is "
                    "not the asymmetry this claim is about -- the sync half "
                    "is the baseline it is measured against"),
            left={"sync": sync_sources, "async": reply_sources},
            right=CONFIDENCE_FLOOR,
            sources={"inbox": INBOX, "sync": ASK},
            population={"first_pass_in_inbox": len(first_pass)},
            claim_id="a2a-first-pass-not-grounded"))
        return

    conclude(Measurement(
        verdict="passed" if async_grounded else "failed",
        reason=(f"the async first-pass reply to {asked}, asked and answered "
                f"during this run, cites {len(reply_sources)} source(s) at "
                f"confidence {reply.get('confidence')}, while the sync half "
                f"cites {len(sync_sources)} at {sync_body.get('confidence')}"),
        left={"async": {"in_reply_to": asked,
                        "at": reply.get("created_at"),
                        "confidence": reply.get("confidence"),
                        "sources": reply_sources},
              "sync": {"confidence": sync_body.get("confidence"),
                       "sources": sync_sources}},
        right=CONFIDENCE_FLOOR,
        sources={"inbox": INBOX, "sync": ASK, "asked": SEND},
        population={"first_pass_in_inbox": len(first_pass)},
        claim_id="a2a-first-pass-not-grounded"))
