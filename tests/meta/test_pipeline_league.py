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
    # Deep pass 2026-10-11, B02: the sequence's reasoning is held to its numbers too -- the distance
    # it quotes, both ways, and the two lengths.
    seq_text = " ".join(f["name"] for f in league.answer_body(SEQ, 7)["reasoning"]["factors"])
    assert f": {_brute(a, b)}" in seq_text and f"({_brute(b, a)})" in seq_text, seq_text
    assert f"({len(a)} and {len(b)} bases" in seq_text, seq_text
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

    # 6. The script around it (deep pass 2026-10-10, R02, R03, T04). A write's outcome follows
    #    rule 9: a 5xx or a 2xx with no body may have landed and is `unknown`, never `rejected`;
    #    the answered set counts `unknown` and their `recent` list, so a possibly-landed answer is
    #    not POSTed again; and a failed read on /lab is said, never shown as zero (rule 8).
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "league_script", Path(__file__).resolve().parents[2] / "scripts" / "league.py")
    script = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(script)
    assert script.outcome_of(200, {"id": 1}) == "accepted"
    assert script.outcome_of(422, {"detail": "x"}) == "rejected"
    assert script.outcome_of(502, None) == "unknown", "a 5xx may have landed"
    assert script.outcome_of(200, None) == "unknown", "a 2xx with no body may have landed"
    # Deep pass 2026-10-11, B02: what a raised POST was. A timeout came after the request left and
    # may have landed (`unknown`, so answered_ids keeps it); only a connection never made is not_sent.
    import httpx

    request = httpx.Request("POST", "https://cymetica.com/api/v1/agent-league/puzzles/72/answers")
    assert script._outcome_of(httpx.ReadTimeout("slow", request=request)) == "unknown", (
        "a timeout after the POST left was read as never sent: the answer would go twice")
    assert script._outcome_of(httpx.ConnectError("refused", request=request)) == "not_sent"

    class Reply:
        def __init__(self, status, body):
            self.status_code, self._body = status, body

        def json(self):
            return self._body

    class Client:
        def __init__(self, status, body):
            self.reply = Reply(status, body)

        def get(self, url, params=None):
            return self.reply

    rows = [{"type": "outcome", "kind": "answer", "puzzle_id": 5, "outcome": "unknown"},
            {"type": "outcome", "kind": "answer", "puzzle_id": 6, "outcome": "accepted"},
            {"type": "outcome", "kind": "answer", "puzzle_id": 7, "outcome": "rejected"}]
    assert script.answered_ids(Client(200, {"recent": [{"puzzle_id": 8}]}), 2, rows) == {5, 6, 8}
    with pytest.raises(SystemExit):
        script.answered_ids(Client(503, None), 2, rows)
    lines = script.summary_lines(3, None, None)
    said = " | ".join(lines)
    assert "0 scored" not in said and "0 ET10" not in said, "a failed read was shown as zero"
    assert "unread" in lines[0] and "unread" in lines[2], lines
    seen = script.summary_lines(3, {"answers": 2, "mean_score": 0.99, "division_name": "D", "points": 5},
                                [{"amount_et10": 1000, "status": "credited"}])
    assert seen[0].startswith("3 answers sent, 2 scored") and seen[2].startswith("1000 ET10 credited"), seen

    # 7. Build it Better, the desk's own door (2026-10-11), the same shape one product over: five
    #    declared writes held to their body keys, the limits refused before a byte leaves, and the
    #    records of rule 9 -- with the one-time request token kept out of everything git tracks.
    bb = _bb_script()
    _bb_gate(bb)
    _bb_refusals(bb)
    _bb_records(bb)


# -- Build it Better: the desk files its own requests ------------------------------------------
#
# [operator 2026-10-11] "Ja nic podavat kebudu ty muzes sam klidne build it better podavat i ty
# featury". Their /openapi-public.json is the contract, read 2026-10-11: the 201 carries
# `request_token` once ("it is the X-BB-Token for accept/change/verdict"); accept takes no body,
# BBChangeIn is {changes}, BBVerdictIn is {verdict, note}, and the token rides as the X-BB-Token
# HEADER. llms.txt's "(request token in the body)" is the MCP tools' shape, not REST's. Withdraw is
# in llms.txt and the MCP tool list only, so it is declared in accept's shape: no body.

BB_BASE = "https://cymetica.com/api/v1/build-it-better/requests"
BB_RULES = {"build_it_better.file": {"app_url", "app_name", "improvements", "agent", "design_urls"},
            "build_it_better.accept": set(), "build_it_better.change": {"changes"},
            "build_it_better.verdict": {"verdict", "note"}, "build_it_better.withdraw": set()}


def _bb_script():
    import importlib.util
    from pathlib import Path

    spec = importlib.util.spec_from_file_location(
        "bb_script", Path(__file__).resolve().parents[2] / "scripts" / "bb.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _bb_gate(bb):
    """Five writes declared closed, exactly the keys the script builds: the exact bodies reach the
    transport underneath; an extra key, a token in a body, a query key or an undeclared path is
    refused before it gets there."""
    import httpx

    from qa.safety import CURRENT_TIER, EndpointRegistry, SafetyTransport, SafetyViolation

    registry = EndpointRegistry.load()
    declared = {r.id: set(r.executable_params) for r in registry.rules
                if r.component == "rest.build_it_better"}
    assert declared == BB_RULES, declared
    assert all(r.closed_body and not r.inert_params and r.methods == {"POST"}
               for r in registry.rules if r.id in BB_RULES)
    assert set(bb.FILE_KEYS) == BB_RULES["build_it_better.file"], bb.FILE_KEYS

    class Inner(httpx.BaseTransport):
        def handle_request(self, request):
            raise AssertionError("the request reached the network")

    registry.mutate_enabled = True
    registry.mutate_allowed_hosts = frozenset({"cymetica.com"})
    transport = SafetyTransport(Inner(), registry)
    filed = bb.file_body(app_name="Agent Tournaments", improvements="One line.\nTwo lines.",
                         design_urls=["https://cymetica.com/a.png"])
    assert filed == {"app_name": "Agent Tournaments", "improvements": "One line.\nTwo lines.",
                     "agent": "qa-cymetica desk", "design_urls": ["https://cymetica.com/a.png"]}, filed
    assert bb.verdict_body("pass", None) == {"verdict": "pass"}
    exact = ((BB_BASE, filed),
             (BB_BASE, bb.file_body(app_url="https://example.com/screener", improvements="One.")),
             (f"{BB_BASE}/ET-30773/accept", None),
             (f"{BB_BASE}/ET-30773/change", bb.change_body("Say on the page when a table is empty.")),
             (f"{BB_BASE}/ET-30773/verdict", bb.verdict_body("fail", "The lobby never fills.")),
             (f"{BB_BASE}/ET-30773/verdict", bb.verdict_body("pass", None)),
             (f"{BB_BASE}/ET-30773/withdraw", None))
    refused = ((BB_BASE, dict(filed, email="someone@example.com")),
               (BB_BASE, dict(filed, symbol="TOUR")),
               (f"{BB_BASE}/ET-30773/change", {"changes": "Say so.", "request_token": "bb_x"}),
               (f"{BB_BASE}/ET-30773/accept", {"request_token": "bb_x"}),
               (f"{BB_BASE}/ET-30773/withdraw?force=true", None),
               (f"{BB_BASE}/ET-30773/tokenize", {"symbol": "TOUR"}),
               (f"{BB_BASE}/ET-30773", {}),
               ("https://cymetica.com/api/v1/build-it-better/startups", {"startup_name": "x"}))
    token = CURRENT_TIER.set(SafetyTier.MUTATE)
    try:
        for url, body in exact:
            with pytest.raises(AssertionError, match="reached the network"):
                transport.handle_request(httpx.Request("POST", url, json=body))
        for url, body in refused:
            with pytest.raises(SafetyViolation):
                transport.handle_request(httpx.Request("POST", url, json=body))
        registry.mutate_enabled = False
        with pytest.raises(SafetyViolation):
            transport.handle_request(httpx.Request("POST", BB_BASE, json=filed))
    finally:
        CURRENT_TIER.reset(token)


def _bb_refusals(bb):
    """Their limits, refused before any body exists: 8,000 characters and 40 lines of
    improvements, 8 to 4,000 for a change, 4,000 for a note, and a fail that says why."""
    forty = "\n".join(f"item {i}" for i in range(40))
    assert bb.file_body(app_name="A", improvements=forty)["improvements"] == forty
    assert len(bb.file_body(app_name="A", improvements="x" * 8000)["improvements"]) == 8000
    for text in ("x" * 8001, forty + "\nitem 41", "", "  \n "):
        with pytest.raises(bb.Refused):
            bb.file_body(app_name="A", improvements=text)
    for kwargs in ({}, {"design_urls": ["C:/Users/me/mockup.png"]},
                   {"design_urls": [f"https://cymetica.com/{i}.png" for i in range(7)]}):
        with pytest.raises(bb.Refused):
            bb.file_body(improvements="One.", **({"app_name": "A"} if kwargs else {}), **kwargs)
    for text in ("x" * 4001, "short", ""):
        with pytest.raises(bb.Refused):
            bb.change_body(text)
    for verdict, note in (("fail", None), ("fail", ""), ("fail", "x" * 4001), ("maybe", "x"),
                          ("pass", "x" * 4001)):
        with pytest.raises(bb.Refused):
            bb.verdict_body(verdict, note)
    assert bb.ticket("ET-30773") == "ET-30773"
    for bad in ("ET-1/../startups", "30773", "ET-", "et-30773", "ET-1?x=1"):
        with pytest.raises(bb.Refused):
            bb.ticket(bad)


def _bb_records(bb):
    """The script end to end over httpx.MockTransport, never a live server: a dry run sends and
    records nothing, an over-long list is refused before any request, a 201 is an intent and an
    outcome with the token in bb_tokens.json alone, the token rides back as X-BB-Token, and a 409
    OPEN_REQUEST_EXISTS is `refused` naming their open ticket."""
    import json
    import secrets
    import subprocess
    import tempfile
    from pathlib import Path

    import httpx

    secret = secrets.token_urlsafe(24)
    sent = []

    def handler(request):
        body = json.loads(request.content) if request.content else None
        sent.append((request.method, request.url.path, request.headers.get("x-bb-token"), body))
        path = request.url.path
        if request.method == "POST" and path.endswith("/requests"):
            if body.get("app_name") == "Busy app":
                return httpx.Response(409, json={
                    "detail": "One open request per app.", "code": "OPEN_REQUEST_EXISTS",
                    "open_ticket": "ET-30773", "stage": "requested",
                    "your_text_was_not_filed": True, "improvements": body.get("improvements")})
            if body.get("app_name") == "Unsure app":
                return httpx.Response(201, json={"ticket": "ET-40002", "request_token": secret + "2"})
            return httpx.Response(201, json={
                "ticket": "ET-40001", "app_name": body.get("app_name"), "created": True,
                "is_idea": True, "stage": "requested", "spec_status": "proposed",
                "messages": [{"kind": "BB-REQUEST", "body": body.get("improvements")}],
                "request_token": secret, "message": f"Filed. Keep {secret}: it is shown once."})
        if path.endswith("/ET-40001/accept"):
            return httpx.Response(200, json={"ticket": "ET-40001", "stage": "funded",
                                             "spec_status": "accepted", "yours": True})
        if request.method == "GET" and path.endswith("/requests/ET-40001"):
            return httpx.Response(200, json={"ticket": "ET-40001", "app_name": "Agent Tournaments",
                                             "stage": "funded", "spec_status": "accepted",
                                             "messages": [], "yours": True})
        return httpx.Response(404, json={"detail": "not here"})

    with tempfile.TemporaryDirectory() as tmp, pytest.MonkeyPatch.context() as mp:
        state = Path(tmp)
        mp.setenv("QA_STATE_DIR", str(state))
        # The operator's session, said: under a company worker's QA_CREW_DEPT this script brakes
        # filings and refuses tickets the company did not file, and Bugs runs this test inside
        # its own run -- it aborted every worker sweep on 2026-10-12 (T-0007).
        mp.delenv("QA_CREW_DEPT", raising=False)
        mp.delenv("QA_CREW_TICKET", raising=False)
        mp.setattr(bb, "INNER", httpx.MockTransport(handler))
        wish = state / "wish.txt"
        wish.write_text("Every table says when it is empty.\nThe lobby counts free seats.\n",
                        encoding="utf-8")
        files = ["file", "--app-name", "Agent Tournaments", "--improvements-file", str(wish)]

        # A dry run prints the body, sends nothing and records nothing.
        assert bb.main(files) == 0 and bb.main(["accept", "ET-40001"]) == 0
        assert sent == [] and not (state / "bb.jsonl").exists()
        assert not (state / "bb_tokens.json").exists()

        # Over the limit: refused before any request, and nothing recorded either.
        long = state / "long.txt"
        long.write_text("x" * 8001, encoding="utf-8")
        assert bb.main(["file", "--app-name", "A", "--improvements-file", str(long), "--confirm"]) != 0
        assert sent == [] and not (state / "bb.jsonl").exists()

        # A 201: intent, then outcome, one id; the token kept in bb_tokens.json.
        assert bb.main(files + ["--confirm"]) == 0
        rows = bb.load()
        assert [r["type"] for r in rows] == ["intent", "outcome"], rows
        assert rows[0]["id"] == rows[1]["id"] == "BB-0001"
        assert rows[0]["body"] == {"app_name": "Agent Tournaments", "agent": "qa-cymetica desk",
                                   "improvements": wish.read_text(encoding="utf-8").strip()}
        assert rows[1]["outcome"] == "accepted" and rows[1]["ticket"] == "ET-40001", rows[1]
        assert rows[1]["token_held"] is True and rows[1]["evidence_id"], rows[1]
        assert json.loads((state / "bb_tokens.json").read_text(encoding="utf-8")) == {"ET-40001": secret}

        # Acting on it: the body is empty, the token is the X-BB-Token header.
        assert bb.main(["accept", "ET-40001", "--confirm"]) == 0
        assert sent[-1] == ("POST", "/api/v1/build-it-better/requests/ET-40001/accept", secret, None), sent[-1]
        assert bb.load()[-1]["outcome"] == "accepted" and bb.load()[-1]["kind"] == "accept"

        # One open request per app: 409 OPEN_REQUEST_EXISTS is `refused`, naming theirs.
        assert bb.main(["file", "--app-name", "Busy app", "--improvements-file", str(wish),
                        "--confirm"]) == 1
        last = bb.load()[-1]
        assert last["outcome"] == "refused" and last["open_ticket"] == "ET-30773", last
        assert last.get("ticket") is None and last["token_held"] is False, last

        # A 2xx that does not say whether it filed is `unknown` -- and a token it carries is
        # still kept: it is shown once, and there is no asking for it again.
        assert bb.main(["file", "--app-name", "Unsure app", "--improvements-file", str(wish),
                        "--confirm"]) == 1
        assert bb.load()[-1]["outcome"] == "unknown" and bb.load()[-1]["token_held"] is True
        assert bb.tokens()["ET-40002"] == secret + "2"

        # Ours, from the diary; and a ticket read back.
        mine = bb.mine(bb.load())
        assert [(m["ticket"], m["outcome"]) for m in mine] == [
            ("ET-40001", "accepted"), (None, "refused"), ("ET-40002", "unknown")], mine
        assert mine[0]["token_held"] is True and mine[1]["open_ticket"] == "ET-30773"
        assert bb.main(["get", "ET-40001"]) == 0 and sent[-1][:2] == (
            "GET", "/api/v1/build-it-better/requests/ET-40001")

        # The token is in bb_tokens.json and nowhere else: not the diary, not the evidence
        # (their 201 body and the accept's X-BB-Token header were both captured).
        assert list((state / "evidence").rglob("*.json")), "nothing was captured to scan"
        holders = sorted(str(p.relative_to(state)) for p in state.rglob("*")
                         if p.is_file() and secret in p.read_text(encoding="utf-8", errors="replace"))
        assert holders == ["bb_tokens.json"], holders

    # And that one file is one git does not track.
    repo = Path(__file__).resolve().parents[2]
    assert subprocess.run(["git", "-C", str(repo), "check-ignore", "-q", "state/bb_tokens.json"],
                          capture_output=True).returncode == 0, "state/bb_tokens.json is not gitignored"
    assert subprocess.run(["git", "-C", str(repo), "ls-files", "state/bb_tokens.json"],
                          capture_output=True, text=True).stdout.strip() == ""
