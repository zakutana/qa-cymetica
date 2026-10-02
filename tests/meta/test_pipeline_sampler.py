"""SAMPLER: what their API says about our bot and our cards, on a timer.

docs/nexus-rooms-plan.md, P4. The operator asked for a panel beside each
strategy that shows how it is doing -- its trades, charts, the bot's
indicators and configuration. Our own records say what WE did; only their API
says what the bot did since and where a card's index stands. So the console
reads it every ten minutes into state/samples.jsonl, gitignored for the
reason state/nexus.jsonl is.

Four ways it could lie, each pinned here:

  * A STALL THAT LOOKS LIKE QUIET. On the night of 2026-09-10 a sampler hung
    for four hours behind `| tail` and nothing said so. Every round writes a
    `tick`, even one whose every read failed; each read has a timeout and the
    round a cap; and the panel says "stale" after three intervals without one.
  * A READ THAT BECOMES A WRITE. It sends GET and nothing else, only to the
    five doors it names, and only about the bot and the positions that are
    ours by our own records.
  * A SERIES THAT REPEATS ITSELF. A trade, the bot's configuration and an
    index point are each written once, and again only when they change.
  * TWO SAMPLERS. clone.py watch wrote into the committed clones.jsonl, which
    dirtied the tree every ten minutes; it now goes through the same round
    into the same file.
"""

from __future__ import annotations

import ast
import importlib.util
import json
import threading
import time
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx

from qa.marks import SafetyTier, qa
from tests.meta.test_pipeline_render import REPO, _lab_page
from tests.meta.test_pipeline_rooms import (
    INSTANCE, _answered, _bot_rows, _buy, _close, _write)

CARD = "card-a-1111"
BOTS = "/api/v1/cloned-bots/my-clones"
BALANCE = f"/api/v1/cloned-bots/{INSTANCE}/balance"
ACTIVITY = f"/api/v1/cloned-bots/{INSTANCE}/activity"
POSITIONS = "/api/v1/event-cards/positions"
HISTORY = f"/api/v1/event-cards/{CARD}/index-history"
CARD_PATH = f"/api/v1/event-cards/{CARD}"
PLANNED = "d432f8cd-dc3f-4563-ab44-07e34dbd2a0a"
GONE = "0ce239bf-2565-45b6-8eed-f9550646a1ca"
ELSEWHERE = "8eaedadc-229b-4d1b-8d1e-7ea74ac5bae2"


def _sampler(state_dir: Path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(state_dir))
    spec = importlib.util.spec_from_file_location(
        "sampler_under_test", REPO / "scripts" / "sampler.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _ours(state_dir: Path) -> None:
    """One bot of ours, one card position still open, and one we closed."""
    _write(state_dir / "clones.jsonl", _bot_rows())
    _write(state_dir / "paper.jsonl", [
        *_buy("TRD-0001", 900, "NEX-1", usdc=10.0, position="P-1"),
        *_buy("TRD-0002", 950, None, usdc=1.0, position="P-2"),
        *_close("TRD-0003", 1000, "P-2", 0.1)])


def _api(**over) -> dict:
    """Their five answers as the probe of 2026-09-11 read them, in miniature.

    Each list also carries something that is not ours -- a bot, a position --
    which the sampler must not follow.
    """
    bodies = {
        BOTS: [
            {"id": INSTANCE, "is_trading": True, "is_paper": True,
             "current_balance_usdc": 950.0, "total_profit_usdc": -50.0,
             "trades_executed": 2, "win_rate": 0.0,
             "last_trade_at": "2026-09-10T23:15:21+00:00",
             "strategy_type": "neural_ensemble", "risk_profile": "medium",
             "primary_indicators": [{"name": "rsi", "params": {"period": 14}}],
             "secondary_indicators": [{"name": "atr", "params": {"period": 14}}],
             "execution_economics": {"execution_class": "PAPER_SIMULATION"}},
            {"id": "not-ours", "is_trading": True, "is_paper": True,
             "current_balance_usdc": 5.0}],
        BALANCE: {"bot_balance": 550.0, "locked_in_trades": 0.0, "available": 550.0},
        ACTIVITY: {"items": [
            {"id": "T-1", "symbol": "ETH", "side": "sell", "trade_type": "wta",
             "amount_usdc": "25.000000", "profit_usdc": None, "is_closed": False,
             "exit_reason": None, "executed_at": "2026-09-10T23:15:21+00:00",
             "closed_at": None}], "has_more": False},
        POSITIONS: {"positions": [
            {"position_id": "P-1", "card_id": CARD, "status": "open",
             "current_index": 93.0, "current_value_usdc": 10.08,
             "unrealized_pnl_usdc": 0.08, "realized_pnl_usdc": 0.0},
            {"position_id": "P-9", "card_id": "card-z", "status": "open",
             "current_index": 50.0}], "count": 2},
        HISTORY: {"card_id": CARD, "interval": "5d", "points": [
            {"t": "2026-09-11T08:00:00+00:00", "index": 92.0, "share_price": 0.0092},
            {"t": "2026-09-11T09:00:00+00:00", "index": 93.0, "share_price": 0.0093}]},
        CARD_PATH: {"id": CARD, "title": "Pepeto DeFi... Bitcoin $250,000",
                    "evcdx_symbol": "EVCDX-PEPETO", "status": "live",
                    "tradeable_now": True,
                    "trading_closes_at": "2026-09-12T23:14:22+00:00",
                    "index_base": 100.0, "current_index": 93.0,
                    "basket": [{"symbol": "BCH", "name": "Bitcoin Cash",
                                "weight": 0.685, "asset_type": "crypto"},
                               {"symbol": "OKB", "weight": 0.315}]},
    }
    bodies.update(over)
    return bodies


def _client(bodies: dict, seen: list):
    """The guarded client over a transport that answers from `bodies` and
    carries nothing anywhere -- so a sampler that tried a write would be
    refused by the guard, and one that got past it would reach no one."""
    from qa.client import build_client
    from qa.config import identities
    from qa.safety import EndpointRegistry

    def answer(request):
        seen.append((request.method, request.url.path))
        body = bodies.get(request.url.path)
        if body is None:
            return httpx.Response(404, json={"detail": "not found"})
        return httpx.Response(200, json=body)

    return build_client(identities()["anon"], EndpointRegistry.load(),
                        base_url="https://cymetica.com",
                        inner=httpx.MockTransport(answer))


def _samples(state_dir: Path) -> list[dict]:
    target = state_dir / "samples.jsonl"
    if not target.exists():
        return []
    return [json.loads(line) for line in target.read_text(encoding="utf-8").splitlines()
            if line.strip()]


def _ticks(state_dir: Path) -> int:
    return sum(1 for row in _samples(state_dir) if row.get("type") == "tick")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_sampler_reads_its_six_doors_with_get_and_nothing_else(
        tmp_path, monkeypatch):
    sampler = _sampler(tmp_path, monkeypatch)
    _ours(tmp_path)
    seen: list = []
    rows = sampler.tick(_client(_api(), seen), every=600)

    assert {method for method, _ in seen} == {"GET"}, f"the sampler sent {seen}"
    assert sorted(path for _, path in seen) == sorted(
        [BOTS, BALANCE, ACTIVITY, POSITIONS, CARD_PATH, HISTORY]), (
        f"it read something that is not ours, or missed one of its six: {seen}")
    (card,) = [r for r in rows if r["type"] == "card"]
    assert (card["card_id"], card["status"], card["trading_closes_at"]) == (
        CARD, "live", "2026-09-12T23:14:22+00:00")
    assert card["basket"] == [{"symbol": "BCH", "weight": 0.685},
                              {"symbol": "OKB", "weight": 0.315}]
    (tick,) = [r for r in rows if r["type"] == "tick"]
    assert tick["ok"] is True and tick["every"] == 600
    (bot,) = [r for r in rows if r.get("kind") == "bot"]
    assert (bot["instance_id"], bot["balance_usdc"], bot["locked_usdc"],
            bot["available_usdc"]) == (INSTANCE, 950.0, 0.0, 550.0)
    assert [r["position_id"] for r in rows if r.get("kind") == "position"] == ["P-1"], (
        "a position that is not ours, or one we closed, was followed")
    # Asked of follow() itself: the closed P-2 shares P-1's card and their
    # mock does not list it, so a follow() that kept it changed no path and no
    # row and the lines above stayed green (P09, deep pass of 2026-09-11).
    assert list(sampler.follow()["positions"]) == ["P-1"], (
        "follow() keeps a position we closed")
    # 2026-10-01: ten clones released on 28 Sep ("Bot deleted") were still
    # followed, so every round read their balance and activity, got 404 "Bot
    # not found." and marked the whole round NOT ok for three days.
    with (tmp_path / "clones.jsonl").open("a", encoding="utf-8") as fh:
        for row in ({"id": "CLN-0090", "type": "intent", "kind": None,
                     "source_id": "x"},
                    {"id": "CLN-0090", "type": "outcome", "outcome": "accepted",
                     "clone_instance_id": "gone-1", "is_paper": True},
                    {"id": "CLN-0091", "type": "intent", "kind": "release",
                     "instance_id": "gone-1"},
                    {"id": "CLN-0091", "type": "outcome", "kind": "release",
                     "outcome": "accepted", "http_status": 200}):
            fh.write(json.dumps(row) + "\n")
    assert sampler.follow()["bots"] == [INSTANCE], (
        "follow() keeps a bot we released")
    assert [r["trade_id"] for r in rows if r["type"] == "trade"] == ["T-1"]
    (config,) = [r for r in rows if r["type"] == "config"]
    assert [i["name"] for i in config["primary_indicators"]] == ["rsi"]
    (index,) = [r for r in rows if r["type"] == "index"]
    assert [point[1] for point in index["points"]] == [92.0, 93.0]
    assert _samples(tmp_path) == rows, "what the round returned is not what it wrote"


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_trade_is_written_once_and_again_only_when_it_changes(tmp_path, monkeypatch):
    sampler = _sampler(tmp_path, monkeypatch)
    _ours(tmp_path)
    sampler.tick(_client(_api(), []), every=600)
    again = sampler.tick(_client(_api(), []), every=600)
    assert sorted({r["type"] for r in again}) == ["sample", "tick"], (
        "an unchanged trade, configuration or index point was written again")

    closed = {"items": [
        {"id": "T-1", "symbol": "ETH", "side": "sell", "trade_type": "wta",
         "amount_usdc": "25.000000", "profit_usdc": "-25.000000", "is_closed": True,
         "exit_reason": "epoch_resolved", "executed_at": "2026-09-10T23:15:21+00:00",
         "closed_at": "2026-09-10T23:20:12+00:00"}], "has_more": False}
    history = {"card_id": CARD, "points": [
        *_api()[HISTORY]["points"], {"t": "2026-09-11T10:00:00+00:00", "index": 94.0}]}
    third = sampler.tick(_client(_api(**{ACTIVITY: closed, HISTORY: history}), []),
                         every=600)
    (trade,) = [r for r in third if r["type"] == "trade"]
    assert (trade["trade_id"], trade["is_closed"], trade["profit_usdc"]) == (
        "T-1", True, "-25.000000")
    (index,) = [r for r in third if r["type"] == "index"]
    assert index["points"] == [["2026-09-11T10:00:00+00:00", 94.0]], (
        "points already on record were written a second time")


class _Slow(BaseHTTPRequestHandler):
    """Answers every GET, eventually: three seconds after it was asked."""

    def do_GET(self):  # noqa: N802 -- BaseHTTPRequestHandler's name
        time.sleep(3)
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b"{}")
        except OSError:
            pass

    def log_message(self, *args):
        pass


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_stalled_read_still_writes_a_tick_and_the_loop_goes_on(tmp_path, monkeypatch):
    """The night of 2026-09-10: a sampler hung for four hours and the pipe it
    printed into hid it.

    Here every read hangs for three seconds against a half-second timeout, on
    a real socket. The round must still write its tick, say which reads timed
    out and which it skipped, stay near its cap -- and the loop must go round
    again rather than die with the first failure.
    """
    from qa.client import build_client
    from qa.config import identities
    from qa.safety import EndpointRegistry

    sampler = _sampler(tmp_path, monkeypatch)
    _ours(tmp_path)
    monkeypatch.setattr(sampler, "ROUND_SECONDS", 1.2)
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Slow)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        client = build_client(
            identities()["anon"], EndpointRegistry.load(),
            base_url=f"http://127.0.0.1:{server.server_address[1]}", timeout=0.5)
        started = time.monotonic()
        rows = sampler.tick(client, every=600)
        took = time.monotonic() - started
        (tick,) = [r for r in rows if r["type"] == "tick"]
        assert tick["ok"] is False
        assert tick["reads"]["bots"] == "timeout", tick["reads"]
        assert "skipped" in tick["reads"].values(), (
            f"the round went on past its cap: {tick['reads']}")
        assert took < 5, f"one round took {took:.1f}s against a cap of 1.2s"

        stop = threading.Event()
        loop = threading.Thread(target=sampler.run, args=(stop, 0.2),
                                kwargs={"client": client}, daemon=True)
        loop.start()
        deadline = time.monotonic() + 20
        while time.monotonic() < deadline and _ticks(tmp_path) < 3:
            time.sleep(0.2)
        assert _ticks(tmp_path) >= 3, "the loop stopped going round after a stalled read"
        stop.set()
        loop.join(timeout=10)
        assert not loop.is_alive(), "the loop did not stop when it was asked to"
    finally:
        server.shutdown()
        server.server_close()


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_the_panel_says_stale_after_three_intervals_without_a_tick(tmp_path, monkeypatch):
    monkeypatch.setenv("QA_STATE_DIR", str(tmp_path))
    now = datetime.now(timezone.utc)

    def tick(minutes_ago: float, ok: bool = True) -> dict:
        return {"type": "tick", "at": (now - timedelta(minutes=minutes_ago)).isoformat(
            timespec="seconds"), "every": 600, "ok": ok, "reads": {}}

    never = _lab_page().build_rooms()["panels"]["general"]
    assert never["stale"] is None and never["sampled_at"] is None, (
        "a sampler that never ran read as fresh, or as stale")
    _write(tmp_path / "samples.jsonl", [tick(45)])
    general = _lab_page().build_rooms()["panels"]["general"]
    assert general["stale"] is True, "45 minutes without a tick, at every 10, is not fresh"
    _write(tmp_path / "samples.jsonl", [tick(45), tick(2, ok=False)])
    general = _lab_page().build_rooms()["panels"]["general"]
    assert (general["stale"], general["sampler_ok"]) == (False, False), (
        "a read that failed two minutes ago is fresh, and failed -- both must show")

    # Three intervals, pinned against `every`: 45 and 2 minutes at every=600
    # let any fixed threshold between them pass (P12, deep pass of 2026-09-11).
    def tick_every(minutes_ago: float, every: int) -> dict:
        return {"type": "tick", "at": (now - timedelta(minutes=minutes_ago)).isoformat(
            timespec="seconds"), "every": every, "ok": True, "reads": {}}

    for minutes, every, stale in ((4, 60, True), (2, 60, False),
                                  (29, 600, False), (31, 600, True)):
        _write(tmp_path / "samples.jsonl", [tick_every(minutes, every)])
        assert _lab_page().build_rooms()["panels"]["general"]["stale"] is stale, (
            f"{minutes} min without a tick at every={every}s should read "
            f"{'stale' if stale else 'fresh'}: stale is three intervals")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_bots_panel_carries_what_the_sampler_read_beside_the_old_samples(
        tmp_path, monkeypatch):
    sampler = _sampler(tmp_path, monkeypatch)
    _ours(tmp_path)
    _write(tmp_path / "nexus.jsonl", _answered("NEX-1", 0))
    from qa import rooms

    rooms.open_strategy("NEX-1", "Karta A a bot")
    sampler.tick(_client(_api(), []), every=600)

    panel = _lab_page().build_rooms()["panels"]["STR-0001"]
    (bot,) = panel["clones"]
    assert [s["balance"] for s in bot["samples"]] == [999.0, 950.0, 950.0, 950.0], (
        "the old samples in clones.jsonl and the sampler's are one series")
    assert (bot["locked"], bot["available"]) == (0.0, 550.0)
    assert [i["name"] for i in bot["config"]["primary_indicators"]] == ["rsi"]
    assert [a["trade_id"] for a in bot["activity"]] == ["T-1"]
    (trade,) = [t for t in panel["trades"] if t["id"] == "TRD-0001"]
    assert (trade["live_status"], trade["current_index"], trade["unrealized"]) == (
        "open", 93.0, 0.08)
    assert [point[1] for point in trade["series"]] == [92.0, 93.0]


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_both_launchers_start_the_sampler_and_the_old_watch_goes_through_it():
    for name in ("console.cmd", "console.sh"):
        text = (REPO / name).read_text(encoding="utf-8")
        # The command, not the comment above it: both files say "--sample 10"
        # in a rem/# line, so removing it from the real command stayed green
        # (P10, deep pass of 2026-09-11).
        commands = "\n".join(
            line for line in text.splitlines()
            if not line.strip().lower().startswith(("rem", "::", "#")))
        assert "--sample 10" in commands, f"{name} starts the console without its sampler"
        # A memecoin round a minute (plan v2, V4), now that a round's quotes
        # are capped by its interval (fomo_watch.quote_cap): with twenty
        # minutes the first verified price sat a median 67 minutes after the
        # flag, and the +15 min reading was mostly missed.
        assert "--fomo 1 " in commands + " ", f"{name} does not watch FOMO Radar every minute"

    serve = ast.parse((REPO / "scripts" / "serve.py").read_text(encoding="utf-8"))
    flags = {arg.value for node in ast.walk(serve) if isinstance(node, ast.Call)
             and getattr(node.func, "attr", None) == "add_argument"
             for arg in node.args if isinstance(arg, ast.Constant)}
    assert "--sample" in flags, "serve.py takes no --sample"

    clone = ast.parse((REPO / "scripts" / "clone.py").read_text(encoding="utf-8"))
    watch = next(node for node in ast.walk(clone)
                 if isinstance(node, ast.FunctionDef) and node.name == "watch")
    called = {getattr(call.func, "id", None) or getattr(call.func, "attr", None)
              for call in ast.walk(watch) if isinstance(call, ast.Call)}
    assert "_append" not in called, (
        "clone.py watch still writes its samples into the committed clones.jsonl")
    assert "run" in called, "clone.py watch does not go through the sampler's round"
    # Deep pass 2026-10-02 (T13): `run` by name was satisfied by `subprocess.run` or any
    # other `.run`, and a ban on `_append` does not stop a write by another helper. It is
    # the SAMPLER's run -- the module `watch` loads from scripts/sampler.py -- and nothing in
    # it names the committed record's helpers.
    sampler_run = [call for call in ast.walk(watch) if isinstance(call, ast.Call)
                   and isinstance(call.func, ast.Attribute) and call.func.attr == "run"
                   and isinstance(call.func.value, ast.Name) and call.func.value.id == "sampler"]
    assert sampler_run, "watch calls some `.run`, not the sampler's"
    assert {"_append_intent", "_append", "_capture"}.isdisjoint(called), (
        "clone.py watch writes through a helper of the committed clone record")


@qa(component="meta.pipeline", tier=SafetyTier.SAFE, surface="meta")
def test_a_card_nexus_proposed_is_followed_and_described_only_when_it_changes(
        tmp_path, monkeypatch):
    """A proposal's cards are ours to watch too: its plan names them, and the
    panel shows how they moved since Nexus answered.

    Each is described by its own door -- its name, its basket, when it closes
    -- and that is written once and again only when it changes, never because
    its index moved. A plan in a stopped room is not followed. A card they no
    longer know is a row saying so, not a round that fails every ten minutes
    for as long as the plan stands.
    """
    sampler = _sampler(tmp_path, monkeypatch)
    _write(tmp_path / "nexus.jsonl", [*_answered("NEX-1", 0), *_answered("NEX-2", 100)])
    from qa import rooms

    rooms.open_strategy("NEX-1", "Proposed")
    rooms.open_strategy("NEX-2", "Stopped")
    rooms.set_plan("STR-0001", [{"card": PLANNED, "side": "bull", "share": 0.2},
                                {"card": GONE, "side": "bull", "share": 0.1}])
    rooms.set_plan("STR-0002", [{"card": ELSEWHERE, "side": "bull", "share": 0.1}])
    rooms.set_status("STR-0002", "stopped", "closed out")
    planned, history = (f"/api/v1/event-cards/{PLANNED}",
                        f"/api/v1/event-cards/{PLANNED}/index-history")
    described = {"id": PLANNED, "title": "Bitcoin's latest hack", "status": "live",
                 "tradeable_now": True, "trading_closes_at": "2026-09-12T07:44:00+00:00",
                 "index_base": 100.0, "current_index": 97.4,
                 "basket": [{"symbol": "BTC", "weight": 0.996}]}
    points = {"card_id": PLANNED,
              "points": [{"t": "2026-09-11T08:00:00+00:00", "index": 97.36}]}

    seen: list = []
    first = sampler.tick(_client({planned: described, history: points}, seen), every=600)
    paths = {path for _, path in seen}
    assert {planned, history, f"/api/v1/event-cards/{GONE}"} <= paths, paths
    assert not any(ELSEWHERE in path for path in paths), (
        "a plan in a stopped room is still followed")
    assert {method for method, _ in seen} == {"GET"}
    cards = {r["card_id"]: r for r in first if r["type"] == "card"}
    assert cards[PLANNED]["basket"] == [{"symbol": "BTC", "weight": 0.996}]
    assert "current_index" not in cards[PLANNED], (
        "the index is in the description, so every round would rewrite it")
    assert cards[GONE]["status"] == "not_found"
    (index,) = [r for r in first if r["type"] == "index"]
    assert index["card_id"] == PLANNED
    (tick,) = [r for r in first if r["type"] == "tick"]
    assert tick["ok"] is True, f"a card they no longer know failed the round: {tick}"

    moved = dict(described, current_index=99.0)
    again = sampler.tick(_client({planned: moved, history: points}, []), every=600)
    assert not [r for r in again if r["type"] in ("card", "index")], (
        "a card was described again although only its index moved")
    settled = dict(moved, status="settled", tradeable_now=False)
    third = sampler.tick(_client({planned: settled, history: points}, []), every=600)
    assert [r["status"] for r in third if r["type"] == "card"] == ["settled"]
