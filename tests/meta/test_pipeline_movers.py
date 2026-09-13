"""The Movers Tournament: free, scored, no money moves -- and read for the
first time on 2026-09-13 as a free measurement of Nexus's own real
forward-return skill (their "NEXUS screen" reference row).

Fixtures below are the real response shape captured live that night:
`rules`/`round`/`leaderboard`/`my_entries`, `is_house` marking their own
automated entrant.
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
        "movers_mod", REPO / "scripts" / "movers.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _client(handler, timeout=5.0) -> httpx.Client:
    from qa.client import build_mock_client

    return build_mock_client(handler, timeout=timeout)


STATE = {
    "rules": {"max_picks": 5, "window_days": 7,
             "text": "Enter up to 5 universe symbols per round."},
    "round": {"round_anchor": "2026-09-11", "entries": 0, "traders": 1,
             "scores_after": "2026-09-18"},
    "leaderboard": [
        {"handle": "nexus", "picks": 250, "rounds": 12, "avg_pct": 29.92,
         "median_pct": 4.0, "best_pct": 340.0, "doublers": 17, "hit50": 40,
         "rank": 1, "is_house": True},
        {"handle": "someone_else", "picks": 30, "rounds": 3, "avg_pct": 2.1,
         "median_pct": 1.0, "best_pct": 10.0, "doublers": 0, "hit50": 5,
         "rank": 2, "is_house": False},
    ],
    "my_entries": [],
}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_round_state_reads_a_failed_response_as_a_failed_read():
    mod = _module()

    def ok(request):
        return httpx.Response(200, json=STATE)

    state = mod.round_state(_client(ok))
    assert state["round"]["round_anchor"] == "2026-09-11"

    def broken(request):
        return httpx.Response(500, text="upstream on fire")

    with pytest.raises(mod.MoversError):
        mod.round_state(_client(broken))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_already_entered_is_keyed_on_the_current_round_not_any_ever():
    mod = _module()

    assert mod.already_entered(STATE) is False, (
        "my_entries is empty this round -- must not read as entered")

    scored_round = {**STATE, "my_entries": [
        {"round_anchor": "2026-08-28", "symbols": ["BTC"]}]}
    assert mod.already_entered(scored_round) is False, (
        "an entry for a PAST round is not an entry for the current one"
    )

    current = {**STATE, "my_entries": [
        {"round_anchor": "2026-09-11", "symbols": ["BTC", "ETH"]}]}
    assert mod.already_entered(current) is True


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_house_row_is_the_nexus_reference_and_nothing_else():
    mod = _module()

    house = mod.house_row(STATE)
    assert house is not None and house["handle"] == "nexus"
    assert house["avg_pct"] == pytest.approx(29.92)

    assert mod.house_row({**STATE, "leaderboard": []}) is None


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_enter_refuses_before_the_network_and_only_the_flag_lets_it_through():
    """Picks come from Nexus, so `enter` takes them as an argument rather than
    choosing them (CLAUDE.md, "Who decides what to trade"). Both refusals
    below fire with NO request made at all -- `sent` stays empty."""
    mod = _module()
    sent = []

    def handler(request):
        sent.append(request)
        return httpx.Response(200, json={"ok": True})

    with pytest.raises(mod.MoversError, match="at most"):
        mod.enter(_client(handler), ["A", "B", "C", "D", "E", "F"], confirm=True)
    assert sent == [], "over the pick limit sent a request anyway"

    with pytest.raises(mod.MoversError, match="confirm"):
        mod.enter(_client(handler), ["BTC"], confirm=False)
    assert sent == [], "no confirm sent a request anyway"

    with pytest.raises(mod.MoversError, match="no symbol"):
        mod.enter(_client(handler), [], confirm=True)
    assert sent == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_enter_posts_the_shape_their_docs_name_and_not_the_one_we_guessed():
    """Cymetica documented the submission on 2026-09-13, in the new "Clone
    Tools & Tournaments" section, after the operator relayed MSG-0011:

        POST /api/v1/universe/movers/tournament/enter
        Body: {"symbols": ["AAPL", "NVDA"]} (1-5 symbols)

    This module had guessed the POST went to the tournament path ITSELF, and
    that guess was wrong -- which is the whole reason `movers.enter` was
    registered `probe_only` until the shape was confirmed rather than tried
    against a round that locks for a week. The test names both halves: the
    path is the documented one, and the body is `{"symbols": [...]}` with the
    symbols upper-cased as their universe writes them.
    """
    from qa.client import build_mock_client
    from qa.safety import EndpointRegistry

    from tests.meta.test_guard_is_real import as_mutate_tier

    mod = _module()
    sent = []

    def handler(request):
        sent.append(request)
        return httpx.Response(200, json={"ok": True})

    # At the tier a real submission runs at -- the guard refuses a POST from a
    # SAFE test, which is exactly what it is for, and the first draft of this
    # test tripped over it.
    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    client = build_mock_client(handler, registry=registry)
    try:
        with as_mutate_tier():
            mod.enter(client, ["aapl", " googl "], confirm=True)
    finally:
        client.close()

    assert len(sent) == 1
    assert sent[0].url.path == "/api/v1/universe/movers/tournament/enter", (
        "the POST must go to the documented /enter, not to the tournament "
        "path itself -- that was the guess, and it was wrong")
    assert json.loads(sent[0].content) == {"symbols": ["AAPL", "GOOGL"]}


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_enter_still_needs_allow_mutate_now_that_probe_only_is_gone():
    """`probe_only` came off once their docs named the shape (2026-09-13), so
    what has to still stand is the floor UNDER it: a POST is a MUTATE, and no
    MUTATE goes out without `--allow-mutate` having been turned on for that
    host on purpose. Driven through the REAL registry and the REAL
    SafetyTransport, not asserted about the yaml file's text -- if this ever
    goes green by default, an ordinary SAFE session could lock a round.
    """
    from qa.client import build_mock_client
    from qa.safety import EndpointRegistry, SafetyViolation

    from tests.meta.test_guard_is_real import as_mutate_tier

    mod = _module()
    sent = []

    def handler(request):
        sent.append(request)
        return httpx.Response(200, json={})

    registry = EndpointRegistry.load()          # mutate_enabled stays False
    client = build_mock_client(handler, registry=registry)
    try:
        with as_mutate_tier(), pytest.raises(SafetyViolation,
                                             match="allow-mutate"):
            mod.enter(client, ["BTC"], confirm=True)
    finally:
        client.close()
    assert sent == [], "the MUTATE floor must refuse before the network"
