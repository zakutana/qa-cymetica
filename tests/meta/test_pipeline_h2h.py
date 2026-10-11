"""scripts/h2h.py: a head-to-head paper matchup, the way cymetica.com/h2h
starts one.

[operator 2026-09-24, in chat] "todle je zajimava vec udelej na to roomku a
hned vsehcny otestuj https://cymetica.com/h2h". The route is POST
/api/v1/head-to-head, CreateMatchup {original, improved, title?, days?,
start?, symbols?, bb_issue_id?, is_public?}; a side is {kind: clone|account,
ref}. Nothing moves money -- both sides are paper -- but `is_public`
defaults TRUE and publishes a share card at cymetica.com/h2h/{slug}, so we
always send it false: a public card is a publication, and those are the
operator's.

A write, so the same gate as every write: a rule in components.yaml with a
closed body, MUTATE on for their host only in the command, and `confirm`
checked before the network.
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
        "h2h_mod", REPO / "scripts" / "h2h.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _client(handler, mutate=False):
    from qa.client import build_mock_client
    from qa.safety import EndpointRegistry

    registry = EndpointRegistry.load()
    if mutate:
        registry.mutate_enabled = True
        registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    return build_mock_client(handler, registry=registry, timeout=5.0)


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_matchup_is_refused_early_never_public_and_carries_only_its_fields():
    """One guard for the one write (folded from two, deep pass 2026-09-24,
    tests/meta grows only by replacement): the refusals first, each before
    the network, then the one body that is sent."""
    from tests.meta.test_guard_is_real import as_mutate_tier

    mod = _module()

    def untouched(request):
        raise AssertionError(f"reached the network: {request.url}")

    with pytest.raises(mod.H2HError, match="confirm"):
        mod.create(_client(untouched), "clone:a", "clone:b", days=7, confirm=False)
    for side in ("a", "bot:a", "clone:", "account:x:y"):
        with pytest.raises(mod.H2HError, match="side"):
            mod.create(_client(untouched), side, "clone:b", days=7, confirm=True)
    with pytest.raises(mod.H2HError, match="itself"):
        mod.create(_client(untouched), "clone:a", "clone:a", days=7, confirm=True)
    for days in (0, 91):
        with pytest.raises(mod.H2HError, match="days"):
            mod.create(_client(untouched), "clone:a", "clone:b", days=days,
                       confirm=True)

    seen = []

    def handler(request):
        seen.append((request.method, request.url.path,
                     json.loads(request.content or b"{}")))
        # 201, as they answer a created matchup (2026-09-24): a 200-only
        # check reported ten created matchups as refused.
        return httpx.Response(201, json={"slug": "abc123", "status": "running",
                                         "is_public": False})

    with as_mutate_tier():
        said = mod.create(_client(handler, mutate=True), "clone:i-1", "clone:i-2",
                          days=7, title="Trend Titan vs Volume Viper",
                          confirm=True)
    assert seen == [("POST", "/api/v1/head-to-head", {
        "original": {"kind": "clone", "ref": "i-1"},
        "improved": {"kind": "clone", "ref": "i-2"},
        "days": 7, "title": "Trend Titan vs Volume Viper",
        "is_public": False})], seen
    assert said["slug"] == "abc123"

    # Deep pass 2026-10-11, R02: a 5xx may have created the matchup -- rule 9 calls that
    # unknown, never refused; a 4xx, or a refusal of ours before the network, is refused.
    def busy(request):
        return httpx.Response(503, text="upstream timeout")

    with as_mutate_tier(), pytest.raises(mod.H2HError) as raised:
        mod.create(_client(busy, mutate=True), "clone:i-1", "clone:i-2", days=7, confirm=True)
    assert raised.value.status == 503 and mod.error_outcome(raised.value) == "unknown"
    assert mod.error_outcome(mod.H2HError("matchup refused: HTTP 422", status=422)) == "refused"
    assert mod.error_outcome(mod.H2HError("pass confirm=True")) == "refused"

    from qa.safety import EndpointRegistry
    rule = {r.id: r for r in EndpointRegistry.load().rules}["head_to_head.create"]
    assert list(rule.methods) == ["POST"] and rule.closed_body is True
    assert set(rule.executable_params) >= {"original", "improved", "days",
                                           "title", "is_public"}
    assert not rule.required_flags
