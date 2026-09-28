"""An Arena leg is judged on what its share would sell for.

NEXT.md, agreed 2026-09-22: a room may hold one team of their CyMetica-42
Arena, BLUE or RED, and `series_of` answered a gap for it because nothing read
a team's price. NEX-0076 said how a share pays: it does not -- "Arena share
positions persist", rolled over each epoch, and "You realize value by selling
the share back into the book at its live price", on a CLOB between $0.01 and
$1.00. So the price is the book's, read by the sampler every round like a
bot's P&L, and the verdict reads those rows.

The fixture is the body GET /api/v1/arena/orderbook/BLUE?levels=5&mode=paper
answered on 2026-09-28 (an empty ask side, prices as strings, eight bid
levels for a `levels` of five -- theirs, not trimmed here).
"""

from __future__ import annotations

import importlib
import importlib.util
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx
import pytest

from qa.marks import SafetyTier, qa

REPO = Path(__file__).resolve().parent.parent.parent
BOOK = "/api/v1/arena/orderbook/BLUE"
BLUE = {"symbol": "BLUE",
        "bids": [{"price": "0.55", "size": "0.31000000", "orders": 1},
                 {"price": "0.54", "size": "0.32000000", "orders": 1},
                 {"price": "0.53", "size": "49.51000000", "orders": 1},
                 {"price": "0.52", "size": "7.76000000", "orders": 1},
                 {"price": "0.51", "size": "21.28000000", "orders": 2},
                 {"price": "0.5", "size": "7.37000000", "orders": 1},
                 {"price": "0.49", "size": "32.88000000", "orders": 2},
                 {"price": "0.48", "size": "10.10000000", "orders": 2}],
        "asks": [], "best_bid": "0.55", "best_ask": None, "spread": None,
        "last_trade": "0.45", "sequence": 0}


def _write(path: Path, rows) -> None:
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")


def _fresh(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    import qa.lab
    import qa.rooms
    import qa.state

    importlib.reload(qa.state)
    importlib.reload(qa.rooms)
    importlib.reload(qa.lab)
    return qa.rooms


def _script(name: str):
    spec = importlib.util.spec_from_file_location(
        f"{name}_arena_under_test", REPO / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _client(answer):
    """The guarded client over a transport that answers locally, so a read
    that became a write would be refused by the guard and reach no one."""
    from qa.client import build_client
    from qa.config import identities
    from qa.safety import EndpointRegistry

    return build_client(identities()["anon"], EndpointRegistry.load(),
                        base_url="https://cymetica.com",
                        inner=httpx.MockTransport(answer))


def _arena_room(state: Path, status: str = "running") -> None:
    _write(state / "rooms.jsonl", [
        {"type": "strategy", "id": "STR-0001", "origin": "NEX-0001",
         "title": "Arena BLUE", "kind": "arena", "ref": "BLUE",
         "at": "2026-09-28T08:00:00+00:00"},
        {"type": "plan", "room": "STR-0001", "at": "2026-09-28T08:00:00+00:00",
         "legs": [{"kind": "arena", "ref": "BLUE", "side": "bull", "share": 0.1}]},
        {"type": "status", "room": "STR-0001", "status": status,
         "why": "an arena room under test", "at": "2026-09-28T08:00:00+00:00"}])


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_sampler_reads_the_book_of_a_team_a_plan_names(tmp_path, monkeypatch):
    """A running room's arena leg puts its team on the sampler's round: one
    GET of that team's paper book, and a row with the best bid, the best ask
    and the last trade, as numbers. A team is never followed as a card."""
    _fresh(tmp_path, monkeypatch)
    _arena_room(tmp_path)
    sampler = _script("sampler")
    seen = []

    def answer(request):
        seen.append((request.method, request.url.path, dict(request.url.params)))
        if request.url.path == BOOK:
            return httpx.Response(200, json=BLUE)
        return httpx.Response(404, json={"detail": "not found"})

    followed = sampler.follow()
    assert followed["teams"] == ["BLUE"] and "BLUE" not in followed["cards"], followed

    rows = sampler.tick(_client(answer), every=600.0)

    assert [(m, p) for m, p, _ in seen] == [("GET", BOOK)], seen
    assert seen[0][2].get("mode") == "paper", seen
    (row,) = [r for r in rows if r.get("kind") == "arena"]
    assert (row["team"], row["best_bid"], row["best_ask"], row["last_trade"]) == (
        "BLUE", 0.55, None, 0.45), row
    assert rows[-1]["reads"] == {"arena BLUE": "ok"} and rows[-1]["ok"], rows[-1]

    # A stopped room's team is not read.
    _arena_room(tmp_path, status="stopped")
    assert sampler.follow()["teams"] == []


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_book_that_did_not_answer_writes_no_price(tmp_path, monkeypatch):
    """Rule 8 at the sampler: a 500, or a 200 with no `best_bid` in it, is a
    failed read -- said on the tick, and no row that a verdict could take for
    a price. A best bid of null IS an answer (nobody bids) and is written."""
    _fresh(tmp_path, monkeypatch)
    _arena_room(tmp_path)
    sampler = _script("sampler")

    for status, body, verdict in ((500, {"detail": "boom"}, "HTTP 500"),
                                  (200, {"symbol": "BLUE", "bids": []}, "unreadable")):
        rows = sampler.tick(_client(lambda request, s=status, b=body:
                                    httpx.Response(s, json=b)), every=600.0)
        assert not [r for r in rows if r.get("kind") == "arena"], rows
        assert rows[-1]["reads"] == {"arena BLUE": verdict}, rows[-1]
        assert not rows[-1]["ok"]

    empty = {**BLUE, "bids": [], "best_bid": None}
    rows = sampler.tick(_client(lambda request: httpx.Response(200, json=empty)),
                        every=600.0)
    (row,) = [r for r in rows if r.get("kind") == "arena"]
    assert row["best_bid"] is None and rows[-1]["ok"], rows


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_team_series_is_its_best_bid_and_skips_an_empty_book():
    """What a held share could be sold for is the best bid, not the last
    trade (0.45 in the fixture, ten cents under what the book would pay) and
    not a mid (their ask side was empty). A round with nobody bidding is no
    point -- a gap, never a price of zero."""
    from qa import lab

    samples = [
        {"type": "sample", "kind": "arena", "team": "BLUE",
         "at": "2026-09-28T10:00:00+00:00", "best_bid": 0.55, "best_ask": None,
         "last_trade": 0.45},
        {"type": "sample", "kind": "arena", "team": "RED",
         "at": "2026-09-28T10:00:00+00:00", "best_bid": 0.40},
        {"type": "sample", "kind": "arena", "team": "BLUE",
         "at": "2026-09-28T10:10:00+00:00", "best_bid": None},
        {"type": "sample", "kind": "bot", "instance_id": "BLUE",
         "at": "2026-09-28T10:15:00+00:00", "total_profit_usdc": 3.0},
        {"type": "sample", "kind": "arena", "team": "BLUE",
         "at": "2026-09-28T10:20:00+00:00", "best_bid": 0.6}]

    assert lab.arena_series(samples, "BLUE") == [
        {"t": "2026-09-28T10:00:00+00:00", "index": 0.55},
        {"t": "2026-09-28T10:20:00+00:00", "index": 0.6}]
    assert lab.arena_series(samples, "RED") == [
        {"t": "2026-09-28T10:00:00+00:00", "index": 0.40}]
    assert lab.arena_series([], "BLUE") == []


def _lab_room(tmp_path, monkeypatch):
    rooms = _fresh(tmp_path, monkeypatch)
    _write(tmp_path / "nexus.jsonl", [{
        "type": "answer", "id": "NEX-0001", "at": "2026-09-28T07:30:00+00:00",
        "text": "Hold BLUE through the next epoch. " + ("reasoning. " * 40)}])
    scripts_lab = _script("lab")
    room = rooms.open_strategy("NEX-0001", "Arena BLUE", kind="arena", ref="BLUE")
    rooms.set_plan(room["id"], [
        {"kind": "arena", "ref": "BLUE", "side": "bull", "share": 0.1}])
    rooms.set_acceptance(room["id"], 1.0, 10.0, "an arena room under test")
    rooms.set_status(room["id"], "running", "an arena room under test")
    opened = datetime.fromisoformat(rooms.acceptance_of(rooms.load(), room["id"])["at"])
    return scripts_lab, opened


def _round(opened, minutes, bid, verdict="ok"):
    at = (opened + timedelta(minutes=minutes)).isoformat()
    rows = [{"type": "tick", "at": at, "ok": verdict == "ok",
             "reads": {"arena BLUE": verdict}}]
    if verdict == "ok":
        rows.insert(0, {"type": "sample", "kind": "arena", "team": "BLUE", "at": at,
                        "best_bid": bid, "best_ask": None, "last_trade": 0.45})
    return rows


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_an_arena_room_is_judged_on_its_bids_and_waits_on_a_failed_read(
        tmp_path, monkeypatch):
    """With the sampler's rounds on record, an arena room's window closes on
    a verdict: bid 0.50 at the open, 0.60 at the close, +20%, survived -- and
    no team is ever read as a card. When the newest round's read of the book
    failed, the verdict waits for the next call (rule 8), because a round
    missing at the window's end would be judged as a window short of data."""
    scripts_lab, opened = _lab_room(tmp_path, monkeypatch)
    rounds = (_round(opened, 5, 0.50) + _round(opened, 720, 0.55)
              + _round(opened, 1435, 0.60))
    read = []
    monkeypatch.setattr(scripts_lab, "_history",
                        lambda client, card: read.append(card) or [])

    _write(tmp_path / "samples.jsonl", rounds + _round(opened, 1445, None, "HTTP 502"))
    said = scripts_lab.verdicts(now=opened + timedelta(days=2))
    assert [s["verdict"] for s in said] == ["waiting"], said
    assert "arena BLUE" in said[0]["why"] and "HTTP 502" in said[0]["why"], said

    _write(tmp_path / "samples.jsonl", rounds + _round(opened, 1445, 0.60))
    said = scripts_lab.verdicts(now=opened + timedelta(days=2))
    assert "BLUE" not in read, f"a team was read as a card: {read}"
    assert [s["verdict"] for s in said] == ["survived"], said
    (leg,) = said[0]["legs"]
    assert (leg["entry_index"], leg["exit_index"]) == (0.50, 0.60), leg
    assert leg["return_pct"] == pytest.approx(20.0), leg
