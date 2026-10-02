"""scripts/creator.py: claiming a reply-queue lead the way the dashboard's
"Reply with this page" button does.

[operator 2026-09-24, in chat] the X picks carried generic cymetica.com links;
the dashboard's own button mints a tracked link for that one reply
(cymetica.com/c/<slug>), so clicks can be counted per thread. The button is
`POST /api/v1/creator/{twitter,reddit}-leads/{lead_id}/reply` with a body of
`{link_slug}` (ClaimBody in /openapi-public.json): it marks the lead claimed
and returns `reply_slug` and `suggested_reply`. It posts nothing to X or
Reddit -- the operator still posts by hand.

A write, so it goes through the same gate every write does: a rule in
components.yaml with a closed body, MUTATE turned on for their host only by
the command, and `confirm` checked before anything reaches the network.
"""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import httpx
import pytest

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent


def _module():
    spec = importlib.util.spec_from_file_location(
        "creator_mod", REPO / "scripts" / "creator.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _client(handler, mutate=False):
    """At the tier a real claim runs at when `mutate`: the guard refuses a
    POST from a SAFE test, which is what it is for."""
    from qa.client import build_mock_client
    from qa.safety import EndpointRegistry

    registry = EndpointRegistry.load()
    if mutate:
        registry.mutate_enabled = True
        registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    return build_mock_client(handler, registry=registry, timeout=5.0)


CLAIMED = {"id": 3, "status": "claimed", "reply_slug": "znn8eicp",
           "suggested_reply": "TradingView alerts can fire straight into real "
                              "orders on EventTrader (paper first). How I set "
                              "it up: https://cymetica.com/c/znn8eicp",
           "permalink": "https://x.com/LuxAlgo/status/2102498561636094324",
           "reply_page_slug": "p497i3fy"}


def _chat():
    spec = importlib.util.spec_from_file_location(
        "chat_mod", REPO / "scripts" / "chat.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


DEGEN_PAGE = (
    "<h3>Price a launch, spend nothing</h3><pre data-prompt-text>Price a memecoin launch "
    "(launch_estimate_cost): show the cost breakdown, and stop before spending anything.</pre>"
    "<h3>Make a fund from today&#39;s news</h3><pre data-prompt-text>Build an AI index basket "
    "(build_ai_index_basket), paper-trade $500 into it and turn it into an event card.</pre>"
    "<h3>Sign my bot</h3><pre data-prompt-text>Assign my cloned bot with arena_assign_bot and "
    "trade one epoch.</pre>")

SSE_BODY = (
    'event: session\ndata: {"session_id": "s-1", "conversation_id": "c-1"}\n\n'
    'event: status\ndata: {"state": "thinking"}\n\n'
    'event: text\ndata: {"content": "Pricing "}\n\n'
    'event: tool_start\ndata: {"name": "launch_estimate_cost"}\n\n'
    'event: tool_result\ndata: {"name": "launch_estimate_cost", "result": {"total": 12}}\n\n'
    'event: text\ndata: {"content": "done."}\n\n'
    'event: done\ndata: {"usage": {"input_tokens": 10, "output_tokens": 5}}\n\n')


def _chat_handler(seen, *, simulation_mode=True, is_sim_mode=True, body=SSE_BODY, status=200):
    def handler(request):
        path = request.url.path
        if request.method == "GET" and path == "/degen":
            return httpx.Response(200, text=DEGEN_PAGE)
        if request.method == "GET" and path == "/api/v1/account/me":
            return httpx.Response(200, json={"simulation_mode": simulation_mode})
        if request.method == "GET" and path == "/api/v1/nexus/subscription":
            return httpx.Response(200, json={"is_sim_mode": is_sim_mode})
        if request.method == "POST" and path == "/api/v1/chat/stream":
            seen.append(json.loads(request.content or b"{}"))
            return httpx.Response(status, text=body,
                                  headers={"content-type": "text/event-stream"})
        raise AssertionError(f"unexpected request {request.method} {path}")
    return handler


def _the_chat_asks_one_paper_prompt_the_way_the_page_does(tmp_path, monkeypatch):
    """NEXT 2026-09-24 (ET-28541): the site's NEXUS acts on the account, with no
    confirmation to approve, so every floor is before the POST: confirm, a prompt that
    exists on /degen and creates nothing public and no arena order, and an account that
    says paper twice. The body is the documented one and nothing else."""
    from tests.meta.test_guard_is_real import as_mutate_tier

    mod = _chat()
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))

    def never(request):
        raise AssertionError(f"reached the network: {request.url}")

    with pytest.raises(mod.ChatError, match="confirm"):
        mod.ask(_client(never, mutate=True), 1, confirm=False)

    # The page's prompts, read the way a browser would, unescaped, numbered from 1.
    found = mod.prompts(DEGEN_PAGE)
    assert [p["n"] for p in found] == [1, 2, 3] and found[1]["title"] == "Make a fund from today's news"
    assert "stop before spending anything." in found[0]["text"]
    # What may not be sent: a public artifact, an arena order, a tool that spends.
    assert mod.refusal_for(found[0]["text"]) is None
    assert "public" in (mod.refusal_for(found[1]["text"]) or ""), "a prompt that publishes a card was allowed"
    assert "arena" in (mod.refusal_for(found[2]["text"]) or "")

    seen = []
    with as_mutate_tier():
        for n in (2, 3, 4):
            with pytest.raises(mod.ChatError):
                mod.ask(_client(_chat_handler(seen), mutate=True), n, confirm=True)
        assert seen == [], "a refused prompt reached the stream"
        for mode, sub in ((False, True), (True, False), (None, True)):
            with pytest.raises(mod.ChatError, match="paper"):
                mod.ask(_client(_chat_handler(seen, simulation_mode=mode, is_sim_mode=sub), mutate=True),
                        1, confirm=True)
        assert seen == [], "an account that is not paper twice was sent a prompt"
        said = mod.ask(_client(_chat_handler(seen), mutate=True), 1, confirm=True)
    assert seen == [{"message": found[0]["text"], "current_page": "/degen"}], seen
    assert said["done"] is True and said["tools"] == ["launch_estimate_cost"], said
    assert said["text"] == "Pricing done." and said["session_id"] == "s-1", said
    assert said["usage"] == {"input_tokens": 10, "output_tokens": 5}, said

    # The diary says what was asked before it says what came back.
    rows = mod.load()
    assert [(r["type"], r["id"]) for r in rows] == [("intent", "CHT-0001"), ("outcome", "CHT-0001")], rows
    assert rows[0]["n"] == 1 and rows[1]["outcome"] == "accepted", rows

    # A stream that stops without `done`, one with an error, and a refusal are each said.
    events = mod.parse_sse(SSE_BODY.replace('event: done\ndata: {"usage": {"input_tokens": 10, "output_tokens": 5}}\n\n', ""))
    assert mod.summarise(events)["done"] is False
    broken = mod.summarise(mod.parse_sse('event: error\ndata: {"error": "limit", "message": "no more"}\n\n'))
    assert broken["error"] == "no more" and broken["done"] is False, broken
    capped = mod.summarise(mod.parse_sse('event: usage_limit\ndata: {"message": "cap"}\n\n'))
    assert capped["usage_limit"] is True, capped
    with as_mutate_tier(), pytest.raises(mod.ChatError, match="402"):
        mod.ask(_client(_chat_handler([], status=402, body="{}"), mutate=True), 1, confirm=True)
    assert mod.load()[-1]["outcome"] == "refused", mod.load()[-1]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_claim_refuses_before_the_network_without_confirm(tmp_path, monkeypatch):
    _the_chat_asks_one_paper_prompt_the_way_the_page_does(tmp_path, monkeypatch)
    mod = _module()

    def handler(request):
        raise AssertionError(f"reached the network: {request.url}")

    with pytest.raises(mod.CreatorError, match="confirm"):
        mod.claim(_client(handler), "twitter", 3, "p497i3fy", confirm=False)
    with pytest.raises(mod.CreatorError, match="outlet"):
        mod.claim(_client(handler), "linkedin", 3, "p497i3fy", confirm=True)
    # MSG-0061 (2026-09-25): a claim with no page answered 200 and attached
    # the account's only page, Chartink, and its pitch to leads about Kalshi,
    # MQL5, Topstep and Tradezella. The default "" was how every call site
    # opted out of choosing, so there is no default and no empty page.
    for empty in ("", "  ", None):
        with pytest.raises(mod.CreatorError, match="page"):
            mod.claim(_client(handler), "twitter", 3, empty, confirm=True)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_claim_posts_the_documented_body_and_returns_the_tracked_link():
    from tests.meta.test_guard_is_real import as_mutate_tier

    mod = _module()
    seen = []

    def handler(request):
        seen.append((request.method, request.url.path,
                     json.loads(request.content or b"{}")))
        return httpx.Response(200, json=CLAIMED)

    with as_mutate_tier():
        said = mod.claim(_client(handler, mutate=True), "twitter", 3,
                         "p497i3fy", confirm=True)
    assert seen == [("POST", "/api/v1/creator/twitter-leads/3/reply",
                     {"link_slug": "p497i3fy"})], seen
    assert said["reply_slug"] == "znn8eicp"
    assert mod.tracked_url(said["reply_slug"]) == "https://cymetica.com/c/znn8eicp"

    # A refusal is said, with their reason, never read as a claim.
    def refused(request):
        return httpx.Response(409, json={"detail": "lead already claimed"})

    with as_mutate_tier(), pytest.raises(mod.CreatorError, match="409"):
        mod.claim(_client(refused, mutate=True), "reddit", 7, "p497i3fy", confirm=True)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_503_or_a_timeout_is_settled_by_reading_the_lead_back():
    """ET-27021 (2026-09-24): claims on leads 109 and 83 answered 503 and 97
    timed out, and all three had committed; creator.py printed "claim
    refused". A 5xx or a timeout is outcome-unknown: read the claimed leads
    back and say what is there, never retry blind and never call it refused."""
    from tests.meta.test_guard_is_real import as_mutate_tier

    mod = _module()
    posts = []

    def committed(request):
        if request.method == "POST":
            posts.append(request.url.path)
            return httpx.Response(503, json={"error": {"code": "SERVICE_UNAVAILABLE"}})
        assert request.url.params.get("status") == "claimed,replied"
        return httpx.Response(200, json={"leads": [CLAIMED]})

    with as_mutate_tier():
        said = mod.claim(_client(committed, mutate=True), "twitter", 3,
                         "p497i3fy", confirm=True)
    assert said["reply_slug"] == "znn8eicp" and said["settled_by_read"] is True
    assert posts == ["/api/v1/creator/twitter-leads/3/reply"], "retried blind"

    lost_posts = []

    def lost(request):
        if request.method == "POST":
            lost_posts.append(request.url.path)
            raise httpx.ReadTimeout("timed out", request=request)
        return httpx.Response(200, json={"leads": []})

    with as_mutate_tier(), pytest.raises(mod.CreatorError, match="not claimed"):
        mod.claim(_client(lost, mutate=True), "twitter", 3, "p497i3fy",
                  confirm=True)
    # The timeout path is never retried blind either (deep pass G04, 3/3).
    assert lost_posts == ["/api/v1/creator/twitter-leads/3/reply"], lost_posts

    # A lead already claimed with ANOTHER page is not this claim settled: a
    # re-claim that 503s over it printed the old page's link as its own
    # (deep pass 2026-09-25, B05).
    def elsewhere(request):
        if request.method == "POST":
            return httpx.Response(503, json={})
        return httpx.Response(200, json={"leads": [
            dict(CLAIMED, reply_page_slug="tf6kmemt")]})

    with as_mutate_tier(), pytest.raises(mod.CreatorError, match="tf6kmemt"):
        mod.claim(_client(elsewhere, mutate=True), "twitter", 3, "p497i3fy",
                  confirm=True)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_mark_posted_sends_the_reply_url_and_only_a_status_link(tmp_path):
    """[operator 2026-09-24, in chat] rewards stayed at 0 because no reply had
    been marked posted: "Mark posted with the link to your reply. The team's
    checker confirms it is displayed and credits the reward." The route is
    POST /api/v1/creator/{outlet}-leads/{lead_id}/posted, PostedBody
    {reply_url}. A reward is credited against that URL, so only a link to one
    post is sent: an x.com / twitter.com status for X, a reddit.com comment
    for Reddit -- refused before the network otherwise, and without confirm."""
    from tests.meta.test_guard_is_real import as_mutate_tier

    mod = _module()

    def untouched(request):
        raise AssertionError(f"reached the network: {request.url}")

    reply = "https://x.com/ZakutanskyA/status/2103174083198202333"
    with pytest.raises(mod.CreatorError, match="confirm"):
        mod.posted(_client(untouched), "twitter", 83, reply, confirm=False)
    for bad in ("", "https://x.com/ZakutanskyA", "https://cymetica.com/c/s2jvpj7j",
                "https://evil.example/status/1"):
        with pytest.raises(mod.CreatorError, match="reply_url"):
            mod.posted(_client(untouched), "twitter", 83, bad, confirm=True)
    # Reddit is exercised too (deep pass G01, 3/3): a thread URL has no
    # comment id, so it is not our reply and a reward on it is a false claim.
    for bad in ("https://www.reddit.com/r/solana/comments/1abc23/some_title/",
                "https://www.reddit.com/r/solana/comments/1abc23/"):
        with pytest.raises(mod.CreatorError, match="reply_url"):
            mod.posted(_client(untouched), "reddit", 7, bad, confirm=True)

    seen = []

    def handler(request):
        seen.append((request.method, request.url.path,
                     json.loads(request.content or b"{}")))
        return httpx.Response(200, json={"id": 83, "status": "replied",
                                         "reply_url": reply})

    with as_mutate_tier():
        said = mod.posted(_client(handler, mutate=True), "twitter", 83, reply,
                          confirm=True)
    assert seen == [("POST", "/api/v1/creator/twitter-leads/83/posted",
                     {"reply_url": reply})], seen
    assert said["status"] == "replied"

    # X's own copy-link form carries ?s=..&t=..; it is the same one post, sent
    # without the query (deep pass R04, 3/3). A reddit comment link passes.
    seen.clear()
    with as_mutate_tier():
        mod.posted(_client(handler, mutate=True), "twitter", 83,
                   reply + "?s=46&t=AbC", confirm=True)
        mod.posted(_client(handler, mutate=True), "reddit", 7,
                   "https://www.reddit.com/r/solana/comments/1abc23/some_title/kx9f2ab/",
                   confirm=True)
    assert [s[2]["reply_url"] for s in seen] == [
        reply, "https://www.reddit.com/r/solana/comments/1abc23/some_title/kx9f2ab/"]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_claim_routes_are_writes_with_a_closed_body_and_nothing_else():
    """The gate: both routes are declared, their body may carry link_slug and
    nothing more, and no rule on them moves money (no required_flags)."""
    from qa.safety import EndpointRegistry

    rules = {r.id: r for r in EndpointRegistry.load().rules}
    for outlet in ("twitter", "reddit"):
        for route, field in (("reply", "link_slug"), ("posted", "reply_url")):
            rule = rules[f"creator.{outlet}_lead_{route}"]
            assert rule.path == f"/api/v1/creator/{outlet}-leads/{{lead_id}}/{route}"
            assert list(rule.methods) == ["POST"]
            assert rule.closed_body is True
            # The wall lets through executable | inert (qa/safety.py), so
            # "nothing more" means both sets (deep pass G03, 3/3).
            assert set(rule.executable_params) | set(rule.inert_params) == {field}
            assert not rule.required_flags
    # 2026-10-02: the chat stream is a write too -- the NEXUS that acts on the account.
    chat = rules["chat.stream"]
    assert chat.path == "/api/v1/chat/stream" and list(chat.methods) == ["POST"]
    assert chat.closed_body is True
    assert set(chat.executable_params) | set(chat.inert_params) == {"message", "session_id", "current_page"}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_creator_routes_speak_as_the_operators_own_account(monkeypatch):
    """REPLY-0058 (2026-09-24) tied the creator queues to tg_expire76 and a key
    minted on it. On 2026-09-25 the queue answered the operator's own key
    (account expire76) with the same 50 leads and the same counts, and the
    operator retired the tg_expire76 key: creator.py speaks with the trusted
    key, and there is no creator identity left to fall back to."""
    from qa.config import identities

    monkeypatch.setenv("QA_CREATOR_KEY", "k-old")
    monkeypatch.setenv("QA_TRUSTED_KEY", "k-trusted")
    assert "creator" not in identities(), "the tg_expire76 key is retired"

    mod = _module()
    assert mod.identity().value == "k-trusted"
    # And the client every request goes through is built with it -- the
    # REPLY-0058 defect was the client, not the helper (deep pass G02, 3/3).
    import qa.client as qa_client
    built = []
    monkeypatch.setattr(qa_client, "build_client",
                        lambda identity, *a, **k: built.append(identity) or object())
    for mutate in (False, True):
        mod._client(mutate)
    assert [i.value for i in built] == ["k-trusted", "k-trusted"], built
    monkeypatch.setenv("QA_TRUSTED_KEY", "")
    with pytest.raises(mod.CreatorError, match="QA_TRUSTED_KEY"):
        mod.identity()
