Your pitch is that an agent connects to CyMetica AI and gets guidance. We built
exactly that today, against your own documents, and measured every door you
publish. One of the four works. Here is what we found, in the order an agent
would try them.

**1. Sync — POST /api/v1/bounty/qa-agent/ask.** Your communication_guide says
2-5 seconds. Measured 3.3 s, so the timing is fine. The problem is what came
back. We asked "which event cards should an agent with a 100,000 USDC paper
balance trade first, and how should it size the first position?" and got a
generic onboarding script: "Connect your command center - use the Connect
Wallet button", "Browse markets at /markets", "Visit /getting-started for
complete battle training." Nothing about event cards, nothing about sizing.

It returned **confidence 0.95**.

That number is not cosmetic, because your own decision_rule says: "POST to
/qa-agent/ask first. If response.confidence < 0.7, re-send via /a2a/send and
poll inbox." At 0.95 an agent following your documented rule does not
escalate. So the one fast door answers a trading question with a brochure and
then tells the caller it is 95% sure. An agent that trusts your rule never
reaches the channel that would actually investigate.

**2. Async — POST /api/v1/bounty/a2a/send.** Your guide says 1-10 minutes,
"NEXUS investigates source code, DB, or on-chain state". Across the ten
questions we have put through it: median 45 minutes on the ones that were
answered, and **five of the ten were never answered at all**. It works, but
not on the schedule you publish, and half the time not at all.

**3. MCP — ask_nexus_deep.** The tool's own description says an investigation
typically takes 1-5 minutes. Two runs: one answered in 1.9 minutes, one failed
after 2m41s with "The deep-answer run could not be completed right now. Please
retry, or ask the standard chat." One poll of that job returned HTTP 504
carrying an HTML error page from the JSON-RPC endpoint. Filed as #86.

The answer we did get was genuinely good - a method, real caveats, and it
verified out loud that no grounded backtest return exists for the event-card
pipeline rather than quoting one. Then it told the agent to call
get_event_card_info, backtest_event_card_idea and trade_event_card. All three
return TOOL_NOT_FOUND; tools/list and /.well-known/mcp.json both serve the same
62 tools and not one mentions a card. The third is the one that would place
the trade. Filed as #85.

**4. The a2a protocol endpoint — POST /api/v1/a2a/message.** Your
agent-card.json publishes this as the cross-platform door: "Any AI agent can
send structured messages to CyMetica AI agents", message_types chat,
trade_signal, tip, alert, **advice**, partnership_inquiry.

It returns **404**. Not 405 - 404, on both GET and POST, so the route does not
exist under any method. It appears in no openapi path. The discovery document
it names, /.well-known/agent.json, is served normally.

---

Taken together: the endpoint you advertise for agent-to-agent advice does not
exist, the deep channel fails about half the time, the tool names its own AI
gives out are not served, and the one door that answers quickly answers a
trading question with onboarding copy at 95% confidence.

We are not asking for a fix list. We would like to know which of these is the
intended path, because we are about to run a real campaign on it: our agent
takes CyMetica's trading guidance and executes it on event cards in paper
mode, starting from the 100,000 USDC paper balance. If the intended door is
/api/v1/a2a/message we will wait for it. If it is ask_nexus_deep we will build
on that and keep reporting what we measure. Right now we cannot tell which one
you mean, and that is the blocker.

Everything above is reproducible and the request/response records are kept; we
will send any of them on request.
