Hi — starting an independent QA pass on the Cymetica / EventTrader API, MCP and
discovery surfaces. Read-only so far. Full report ready to send, but four
questions about the reporting channel itself first, because I would rather file
through your API than paste into chat, and I want to be sure attribution works
before I do.

1. FILING APPEARS TO BE UNAUTHENTICATED

POST /api/v1/bounty/reports with an empty body returns the same response with
no credential and with a TRUSTED-tier API key:

  HTTP 422 — {"detail":[{"type":"missing","loc":["body","title"] ...

A validation error, not a permission error, and byte-identical at both
identities. Same for /api/v1/bounty/reports/with-screenshots.

SCOPE — what this does not establish: I sent an empty body deliberately, so
this shows only that no authorization check runs before validation. It does not
show that a fully-populated anonymous POST is accepted. I have not tested that,
and I will not without your say-so, because the test would create a real record
in your tracker.

2. HOW IS hunter_name BOUND TO AN IDENTITY?

If filing needs no credential, then hunter_name looks like a form field a caller
sets freely. If that is so, anyone can file as any hunter, and reward
attribution rests on an unauthenticated string. I would rather be wrong about
this — please tell me what actually binds a report to a hunter.

3. THE TRACKER SHOWS 15 REPORTS AND ALL 15 READ "fixed"

GET /api/v1/bounty/reports returns no open, triaged, disputed or wont_fix item.
The schema carries validated_at, triaged_at and severity_confirmed; all three
are null on all 15 records.

Credit where due: the resolution notes on our own six reports are specific —
they name files, line numbers and commit hashes, which is more than most
vendors provide. The question is not whether work was done. It is that a queue
with a 100% closure rate and no populated validation field cannot be used to
measure anything. Is this a filtered view, or does the tracker not retain
unresolved items?

4. CONFIRM OUR ATTRIBUTION

Reports from us will carry:
  hunter_name     expire76
  wallet_address  0xde9CeAaB301A9e47b1bAcd448B3DDbbA85e83398

Please confirm both are correctly bound on your side, and that the six existing
expire76 reports are attributed to that wallet.

WHAT I WILL DO WITH YOUR ANSWERS

If the pipeline round-trips reliably, I will file through the API and poll
report status instead of sending prose. To be explicit about how I will treat
what comes back: a status change to "fixed" is recorded on my side as
FIX_CLAIMED, not as fixed. It moves to verified only after I re-run the exact
check that originally failed, against the live build, and it moves back to open
if that check still fails. I will report either outcome accurately, and I will
withdraw any claim of mine the moment it is shown wrong.

────────────────────────────────────────────────────────
SCOPE OF THIS REQUEST: read-only verification only. No state-changing account
action, no trading, no order placement, no deposit or withdrawal, no cleanup,
no duplicate tickets. This request excludes UI defects and all pending
authorization items.
────────────────────────────────────────────────────────


────────────────────────────────────────────────────────


Independent QA report #1 — Cymetica / EventTrader
Scope: REST API, MCP and the machine-readable discovery surfaces. No UI testing.
Method: read-only GET and JSON-RPC tools/list at two identities (no key, and a
TRUSTED-tier key). Every figure below was measured directly, not taken from a
document. Timestamps are UTC.

All checks are reproducible from a single command; each is given inline.

════════════════════════════════════════════════════════
1. AUTHORIZATION — the API key makes no difference to the MCP tool surface
════════════════════════════════════════════════════════

OBSERVED (2026-09-04T10:43:50Z)
  tools/list with no credential     -> HTTP 200, 46 tools
  tools/list with a TRUSTED key     -> HTTP 200, 46 tools
  The two sets are byte-for-byte identical.

  /.well-known/mcp.json assigns every tool a trust_tier. It declares 25 tools
  at trust_tier "unknown". An anonymous caller receives all 46 — that is 21
  tools above the tier your own manifest assigns them, including:

    declared "allied"     create_aib_fund, edit_aib_fund_basket,
                          list_my_aib_funds, register_webhook, subscribe_prices
    declared "trusted"    get_market_analytics, get_oracle_insights,
                          get_signal_history
    declared "recognized" place_order, get_deposit_address, get_positions,
                          get_order_history, get_agent_profile, get_rate_limits,
                          query_knowledge, submit_signal, submit_observation,
                          submit_feedback, request_feature, ask_nexus_deep,
                          get_deep_answer

  llms.txt states "anonymous = PUBLIC tools". That is not what the server does.

CHECK
  curl -s -X POST https://cymetica.com/mcp/v1 \
    -H 'Content-Type: application/json' \
    -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}' \
    | python -c "import json,sys;print(len(json.load(sys.stdin)['result']['tools']))"
  Expected per mcp.json + llms.txt: 25.  Actual: 46.

SCOPE — what this does NOT establish
  This is the ADVERTISED surface only. I have not called any of these tools
  without a key, so this does not show that an unauthenticated tools/call on
  place_order or create_aib_fund succeeds. Those are two different defects with
  very different severity and I am not merging them. Please answer them
  separately (asks 1 and 2).

  Also for the record, and explicitly labelled as reported-not-verified: a
  handoff note dated 2026-08-28 records 27 tools at TRUSTED. I did not measure
  that and cannot confirm it. I record it only because if the surface is
  changing between observations, that is itself worth knowing.

════════════════════════════════════════════════════════
2. DATA INTEGRITY — the agents llms.txt tells readers to clone do not exist
════════════════════════════════════════════════════════

OBSERVED
  llms.txt: "Clone any of 10 AI trading agents (DELTA, STAT, CORR, SENT, SYNC,
  CRASH, DREAD, GLOOM, FADE, VORTX)"

  GET /api/v1/agents/species returns 11 species:
  MACD, RSI, BOLL, VOL, TREND, STOCH, ICHI, FIB, ATR, DIV, PCPN

  The intersection of those two sets is EMPTY. Not one documented name resolves.
  GET /api/v1/agentbook/agents reports 8. mcp.json's description says 16.
  Four sources, four answers: 8 / 10 / 11 / 16.

CHECK
  curl -s https://cymetica.com/api/v1/agents/species \
    | python -c "import json,sys;print(sorted(a['symbol'] for a in json.load(sys.stdin)))"
  Expected per llms.txt: DELTA, STAT, CORR, ...  Actual: ATR, BOLL, DIV, ...

WHY THIS IS NOT COSMETIC
  An agent following your own documentation to clone "DELTA" cannot succeed.
  This is the single most prominently advertised action for AI callers.

════════════════════════════════════════════════════════
3. CONTRACT — documented endpoints and tools that return 404 / do not exist
════════════════════════════════════════════════════════

26 endpoints documented in llms.txt or agent-skills.json return 404. Among them:

  from agent-skills.json (each is a skill's declared endpoint):
    POST /api/v1/clob/order          404   (the spec has /clob/orders, plural)
    POST /api/v1/bots/clone          404   (the spec has /agents/clone)
    POST /api/v1/exchange/buy        404
    POST /api/v1/tuatara/discover    404

  from llms.txt:
    /api/v1/winner-takes-all/markets, /winner-takes-all/bet,
    /winner-takes-all/epochs, /api/v1/positions, /api/v1/account,
    /api/v1/cloned-bot/create, /cloned-bot/list, /api/v1/backtest/run,
    /api/v1/backtest/saved, /api/v1/agentbook/post, /api/v1/staking/pools,
    /api/v1/defi/pools, /api/v1/aerodrome/quote, /api/v1/base-dex/tokens,
    /api/v1/vaix/prices, /api/v1/perpetual/user/positions,
    /mcp/v1/prompts/{analyze_market,compare_markets,explain_probability,
    find_opportunities}, /mcp/v1/resources/docs/{api,getting-started}

Separately, llms.txt documents 11 MCP tools by name. 7 of them do not exist:
  MISSING  get_markets, get_price, get_trades, get_leaderboard,
           get_market_summary, get_trending_markets, get_featured_market
  PRESENT  get_market, get_prices, get_orderbook, search_markets

A further 18 documented URLs exist but reject the documented method (llms.txt
renders MCP tools as GET-able /mcp/v1/tools/<name> URLs; they answer 405).

DO NOT COLLAPSE THESE INTO ONE ANSWER
  A 404 has at least three distinct causes and they need different fixes:
    (a) the endpoint was removed and the document is stale
    (b) the endpoint was never built and the document is aspirational
    (c) the path in the document is a typo for a working endpoint
  "We'll update the docs" is only correct for (a) and (c). Please label each
  group, or at minimum tell me which of the four agent-skills.json entries are
  typos versus absent features.

════════════════════════════════════════════════════════
4. RECONCILIATION — the same quantity, different answers by source
════════════════════════════════════════════════════════

  quantity              llms.txt   mcp.json   live API        agent-card
  MCP tools                   11         46   46 (anon)              —
  MCP resources                4          5   —                      —
  CLOB pairs                   9        568   —                      —
  trading agents              10         16   11 species / 8 book    10
  settlement chains            —         10   16 (/swap/chains)      —
  commits                11,700+          —   21,840 (build-stats)   —
  agent skills                 —          —   —              13 vs 10*

  * /.well-known/agent-card.json lists 13 skills, /.well-known/agent-skills.json
    lists 10, and the two sets are not nested: 7 ids appear only in the first,
    4 only in the second.

  The commit figure is the one I would prioritise of these four: 11,700+ versus
  a live 21,840 is an 87% understatement of your own headline AI-authorship
  metric, and it is the number outside parties are most likely to quote.

════════════════════════════════════════════════════════
ASKS
════════════════════════════════════════════════════════

1. Is the identical 46-tool response to anonymous and TRUSTED callers intended?
   If yes, what is trust_tier in mcp.json describing?
2. Does an unauthenticated tools/call on a tool declared "allied" (e.g.
   create_aib_fund) pass authorization? A yes/no is enough — I have not tested
   it and will not without your confirmation that it is safe to probe.
3. Which agent symbol set is authoritative, and will llms.txt be corrected?
4. For the 26 404s: which are stale docs, which are unbuilt, which are typos?
5. Which is the correct CLOB pair count, 9 or 568?
6. For each accepted fix: what check will now fail loudly if it regresses? A
   fix repairs one instance; I am asking for the invariant that prevents the
   class. I will re-run the exact check that failed and report the result
   either way.

I do not record anything as fixed on your say-so. I record "verified against
<surface> at <time> by <check>", or I record that it is still reproducible.
Both outcomes get reported accurately, and I will withdraw any claim above the
moment it is shown wrong.

────────────────────────────────────────────────────────
SCOPE OF THIS REQUEST: read-only verification only. No state-changing account
action, no trading, no order placement, no deposit or withdrawal, no cleanup,
no duplicate tickets, and nothing outside the REST/MCP/discovery surfaces named
above. This request excludes UI defects and all pending authorization items.
────────────────────────────────────────────────────────
