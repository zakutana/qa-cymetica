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
def test_an_entry_is_written_down_with_the_day_it_was_made(tmp_path,
                                                            monkeypatch):
    """A pick locks for seven days, and nothing recorded that we made it.

    The five picks entered on 2026-09-13 went into a round anchored
    2026-09-11 and came back priced at the anchor's close. That gap between
    WHEN we entered and WHICH close we got is the whole of the second Movers
    finding -- and after the POST it existed only in a terminal, because this
    module wrote nothing anywhere. `qa.lab` is where the laboratory's own
    diary lives, so the row goes there, carrying the moment of the entry
    beside the round it entered and the prices it was given.
    """
    import importlib

    import qa.state

    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    importlib.reload(qa.state)
    import qa.lab
    importlib.reload(qa.lab)

    mod = _module()
    row = mod.note_entry(
        anchor="2026-09-11",
        symbols=["AAPL", "GOOGL"],
        entries=[{"symbol": "AAPL", "entry_price_usd": 335.799987793},
                 {"symbol": "GOOGL", "entry_price_usd": 341.51001}],
        nexus_id="NEX-0027")

    assert row["type"] == "tournament"
    assert row["round_anchor"] == "2026-09-11"
    assert row["symbols"] == ["AAPL", "GOOGL"]
    assert row["nexus_id"] == "NEX-0027", "picks come from Nexus; say which answer"
    assert row["entry_prices"] == {"AAPL": 335.799987793, "GOOGL": 341.51001}
    assert row["at"], "the moment of the entry is the point of the row"

    # And it is really on disk, readable by the next session.
    back = [r for r in qa.lab.load() if r.get("type") == "tournament"]
    assert len(back) == 1 and back[0]["round_anchor"] == "2026-09-11"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_submitted_round_is_recorded_even_when_their_reply_is_thin(
        tmp_path, monkeypatch):
    """R05, deep pass of 2026-09-13, triage 3/3. The whole command, not the
    helper -- `cmd_enter` had no test anywhere.

    `note_entry` was called AFTER the `finally` that closes the client and
    resets the tier, and its anchor fell back to `round_state(client)` on that
    closed client. So a reply without `round_anchor` meant the POST had really
    locked a week-long round and the recording died with `RuntimeError:
    Cannot send a request, as the client has been closed` -- the exact defect
    note_entry was written that afternoon to prevent, reintroduced by its own
    call site. It worked on the day only because their reply carried the field.

    Their documented reply shape names no success body at all, so a thin one
    is the case to build for, not the surprising one.
    """
    import argparse
    import importlib

    import qa.state

    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    importlib.reload(qa.state)
    import qa.lab
    importlib.reload(qa.lab)

    mod = _module()
    seen = []

    def handler(request):
        seen.append(request)
        if request.method == "POST":
            return httpx.Response(200, json={"ok": True})   # no round_anchor
        return httpx.Response(200, json={"round": {"round_anchor": "2026-09-11"},
                                         "rules": {}, "leaderboard": [],
                                         "my_entries": []})

    from qa.client import build_mock_client
    from qa.safety import EndpointRegistry

    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    client = build_mock_client(handler, registry=registry)
    monkeypatch.setattr(mod, "build_client", lambda *a, **k: client,
                        raising=False)
    monkeypatch.setattr(mod, "_client", lambda: client, raising=False)

    import qa.client as qa_client
    monkeypatch.setattr(qa_client, "build_client", lambda *a, **k: client)

    args = argparse.Namespace(symbols=["aapl", " googl "], confirm=True,
                              nexus="NEX-0027")
    assert mod.cmd_enter(args) == 0

    rows = [r for r in qa.lab.load() if r.get("type") == "tournament"]
    assert len(rows) == 1, "a locked round with no record is the whole defect"
    assert rows[0]["round_anchor"] == "2026-09-11", (
        "the anchor must come from the GET taken before the POST, not from a "
        "fallback on a client that is already closed")
    assert rows[0]["symbols"] == ["AAPL", "GOOGL"], (
        "the record must carry what was SENT, not the raw arguments")


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
