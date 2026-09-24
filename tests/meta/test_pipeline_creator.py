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
           "permalink": "https://x.com/LuxAlgo/status/2102498561636094324"}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_claim_refuses_before_the_network_without_confirm():
    mod = _module()

    def handler(request):
        raise AssertionError(f"reached the network: {request.url}")

    with pytest.raises(mod.CreatorError, match="confirm"):
        mod.claim(_client(handler), "twitter", 3, "p497i3fy", confirm=False)
    with pytest.raises(mod.CreatorError, match="outlet"):
        mod.claim(_client(handler), "linkedin", 3, "p497i3fy", confirm=True)


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
        mod.claim(_client(refused, mutate=True), "reddit", 7, "", confirm=True)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_claim_routes_are_writes_with_a_closed_body_and_nothing_else():
    """The gate: both routes are declared, their body may carry link_slug and
    nothing more, and no rule on them moves money (no required_flags)."""
    from qa.safety import EndpointRegistry

    rules = {r.id: r for r in EndpointRegistry.load().rules}
    for outlet in ("twitter", "reddit"):
        rule = rules[f"creator.{outlet}_lead_reply"]
        assert rule.path == f"/api/v1/creator/{outlet}-leads/{{lead_id}}/reply"
        assert list(rule.methods) == ["POST"]
        assert rule.closed_body is True
        assert set(rule.executable_params) == {"link_slug"}
        assert not rule.required_flags


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_creator_routes_speak_as_the_creator_account_or_not_at_all(monkeypatch):
    """REPLY-0058 (2026-09-24): the creator queues belong to tg_expire76, and
    our trusted key is account expire76 -- a lead it claims is credited to the
    wrong account and `?status=claimed` reads empty. So creator.py speaks with
    QA_CREATOR_KEY, the key minted on tg_expire76 itself, and without one it
    refuses: falling back to the trusted key is the defect, not a default."""
    from qa.config import identities

    monkeypatch.setenv("QA_CREATOR_KEY", "k-creator")
    monkeypatch.setenv("QA_TRUSTED_KEY", "k-trusted")
    assert identities()["creator"].headers() == {"X-API-Key": "k-creator"}

    mod = _module()
    assert mod.identity().value == "k-creator"
    monkeypatch.setenv("QA_CREATOR_KEY", "")
    with pytest.raises(mod.CreatorError, match="QA_CREATOR_KEY"):
        mod.identity()
