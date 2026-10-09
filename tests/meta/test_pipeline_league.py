"""The Agent League door: what we answer, what we refuse, and what the transport lets through.

[operator 2026-10-09] "Ucastni se" (their X post of 9 Oct: every Agent League puzzle pays 1,000 /
2,500 / 10,000 ET10, Phase 1, no deposits), and, asked why the writes were closed: "Proc by mely
byt zamcete? Normalne se povoluji". Two writes open -- enrol one player, answer a puzzle -- and
only the families that are exact arithmetic on the puzzle's own snapshot are answered at all.
"""

from __future__ import annotations

import functools
from datetime import datetime, timezone

import pytest

from qa.marks import SafetyTier, qa

SEQ = {"id": 72, "family": "sequence_similarity", "kind": "deterministic", "status": "open",
       "answer_type": "number", "closes_at": "2099-01-01T00:00:00+00:00",
       "snapshot": {"seq_a": "CTGGGAGTGCTATCTCAAGGTCCGGTTGCGTGGAAAATGAC",
                    "seq_b": "CTGGGGGTGCAATCTAAAGTTTCGGTTGCGGGAAAATGAC", "naive": 5,
                    "range": {"lo": 0, "hi": 15}}}
ARB = {"id": 85, "family": "cex_dex_arb", "kind": "deterministic", "status": "open",
       "answer_type": "number", "closes_at": "2099-01-01T00:00:00+00:00",
       "snapshot": {"token": "ETH", "cex_px": 2491.1746779818877, "dex_px": 2488.7235542772164,
                    "gas_gwei": 0.267903, "eth_usd": 2491.1746779818877, "gas_units": 150000,
                    "notional_usd": 10000.0, "bridge_cost_usd": 0.0, "chain": "ethereum",
                    "naive": -9.839, "range": {"lo": -59.84, "hi": 40.16}}}


def _brute(a: str, b: str) -> int:
    """An independent Levenshtein, the textbook recursion, to hold the module's against."""
    @functools.lru_cache(maxsize=None)
    def go(i: int, j: int) -> int:
        if i == 0 or j == 0:
            return i + j
        return min(go(i - 1, j) + 1, go(i, j - 1) + 1, go(i - 1, j - 1) + (a[i - 1] != b[j - 1]))
    return go(len(a), len(b))


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_league_answers_only_what_it_computes_exactly_and_only_once():
    """Two exact families, reasoning that is the computation, refusals around them, and a
    transport that holds the two writes to their declared fields."""
    import httpx

    from qa import league
    from qa.safety import (CURRENT_TIER, EndpointRegistry, SafetyTransport,
                           SafetyViolation)

    # 1. Levenshtein: the textbook cases, symmetric, and the real puzzle against a brute force.
    assert league.levenshtein("kitten", "sitting") == 3
    assert league.levenshtein("", "abc") == 3 and league.levenshtein("abc", "") == 3
    a, b = SEQ["snapshot"]["seq_a"], SEQ["snapshot"]["seq_b"]
    assert league.levenshtein(a, b) == league.levenshtein(b, a) == _brute(a, b)

    # 2. The net edge: DEX minus CEX in bps of the CEX price, minus gas (and any bridge) as
    #    bps of the notional -- the snapshot's own `naive` is the gap alone, -9.839.
    snap = ARB["snapshot"]
    gap = (snap["dex_px"] - snap["cex_px"]) / snap["cex_px"] * 1e4
    gas = snap["gas_gwei"] * 1e-9 * snap["gas_units"] * snap["eth_usd"] / snap["notional_usd"] * 1e4
    assert gap == pytest.approx(snap["naive"], abs=0.001)
    assert league.net_edge_bps(snap) == pytest.approx(gap - gas)
    assert league.net_edge_bps(dict(snap, bridge_cost_usd=10.0)) == pytest.approx(gap - gas - 10.0)

    # 3. The body: the answer is the computed value, and the reasoning is explained by THEIR rule
    #    (all three of data_used, two factors, one rejected option) and true to the numbers.
    for puzzle, expect in ((SEQ, float(_brute(a, b))), (ARB, gap - gas)):
        body = league.answer_body(puzzle, player_id=7)
        assert set(body) == {"player_id", "answer", "reasoning"} and body["player_id"] == 7
        assert body["answer"] == {"value": pytest.approx(expect)}
        assert league.explained(body["reasoning"]), body["reasoning"]
        assert all(key in puzzle["snapshot"] for key in body["reasoning"]["data_used"])
    arb_text = " ".join(f["name"] for f in league.answer_body(ARB, 7)["reasoning"]["factors"])
    assert f"{gap:.2f}" in arb_text and f"{gas:.2f}" in arb_text, arb_text
    assert not league.explained({"data_used": ["x"], "factors": [{"name": "one", "weight": 1}],
                                 "rejected_options": ["y"]}), "one factor is not explained"
    assert not league.explained({"data_used": [], "factors": [{}, {}], "rejected_options": ["y"]})
    assert not league.explained({"data_used": ["x"], "factors": [{}, {}], "rejected_options": []})

    # 4. Refusals: a closed or resolved puzzle, a family we cannot compute, a forecast, an
    #    answer already given, and a body the arithmetic could not honestly fill.
    now = datetime(2026, 10, 9, 12, 0, tzinfo=timezone.utc)
    assert league.refusal(SEQ, set(), now) is None and league.refusal(ARB, set(), now) is None
    assert "closed" in league.refusal(dict(SEQ, closes_at="2026-10-09T11:00:00+00:00"), set(), now)
    assert "open" in league.refusal(dict(SEQ, status="resolved"), set(), now)
    assert "family" in league.refusal(dict(SEQ, family="funding_basis"), set(), now)
    assert "number" in league.refusal(dict(SEQ, answer_type="probability"), set(), now)
    assert "already" in league.refusal(SEQ, {72}, now)
    assert league.refusal(dict(SEQ, snapshot={"seq_a": "ACGT"}), set(), now), "no seq_b: unreadable"
    far = dict(SEQ, snapshot=dict(SEQ["snapshot"], range={"lo": 0, "hi": 3}))
    assert "range" in league.refusal(far, set(), now), "a value outside the stated range is not sent"

    # 5. The transport: two rules, closed. Enrol carries name and kind; an answer carries its
    #    player, its answer and its reasoning -- and nothing else reaches them.
    class Inner(httpx.BaseTransport):
        def handle_request(self, request):
            raise AssertionError("the request reached the network")

    registry = EndpointRegistry.load()
    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    transport = SafetyTransport(Inner(), registry)
    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        for url, body in (("https://cymetica.com/api/v1/agent-league/players",
                           {"name": "qa-cymetica", "kind": "api", "sliders": {"a": 1}}),
                          ("https://cymetica.com/api/v1/agent-league/puzzles/72/answers",
                           {"player_id": 7, "answer": {"value": 3}, "reasoning": {}, "extra": 1}),
                          ("https://cymetica.com/api/v1/agent-league/problems",
                           {"title": "a problem we post"})):
            with pytest.raises(SafetyViolation):
                transport.handle_request(httpx.Request("POST", url, json=body))
        for url, body in (("https://cymetica.com/api/v1/agent-league/players",
                           {"name": "qa-cymetica", "kind": "api"}),
                          ("https://cymetica.com/api/v1/agent-league/puzzles/72/answers",
                           league.answer_body(SEQ, 7))):
            with pytest.raises(AssertionError, match="reached the network"):
                transport.handle_request(httpx.Request("POST", url, json=body))
    finally:
        CURRENT_TIER.reset(token)
