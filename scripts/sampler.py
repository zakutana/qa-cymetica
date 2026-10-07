"""What their API says about our bot and our cards, read on a timer.

docs/nexus-rooms-plan.md, P4. The Nexus tab's strategy panels show how a
strategy is doing, and our own records -- paper.jsonl, clones.jsonl -- only say
what WE did. Where a card's index stands now, what the bot has traded since we
switched it on, what it has locked: only their API says that. This reads it
into state/samples.jsonl, gitignored because it is written while a sweep may be
running (qa/rooms.py says the rest).

    python scripts/sampler.py once              one round, then stop
    python scripts/sampler.py run --every 600   a round every ten minutes
    python scripts/serve.py --sample 10         the same, inside the console

SAFE, GET only, through the guarded client, and only about what is ours by our
own records: the bots clones.jsonl says we cloned, the positions paper.jsonl
says we opened and have not closed, and the cards and Arena teams a strategy's
plan names while that strategy is not stopped (qa/rooms.py). Seven doors:

    my-clones              the bot's balance, P&L, trades, and its indicators
    {id}/balance           what is locked in open trades, and what is free
    {id}/activity          the bot's trades -- undocumented, read for display only
    event-cards/positions  each of our positions, live
    event-cards/{card}     what a card holds, and when it closes
    {card}/index-history   the card's index, for the chart
    arena/orderbook/{team} what a team's share would sell for, every round

Every round writes a `tick`, including a round in which every read failed: on
the night of 2026-09-10 a sampler hung for four hours behind `| tail` and
nothing said so. Each read has a timeout and the round has a cap, and a stall
costs a round, never the loop. A trade, the bot's configuration, a card's
description and an index point are written once, and again only when they
change.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import httpx  # noqa: E402

from qa import rooms  # noqa: E402
from qa.console import printable  # noqa: E402
from qa.safety import CURRENT_TIER, SafetyTier  # noqa: E402

BOTS = "/api/v1/cloned-bots/my-clones"
BALANCE = "/api/v1/cloned-bots/{id}/balance"
ACTIVITY = "/api/v1/cloned-bots/{id}/activity"
POSITIONS = "/api/v1/event-cards/positions"
HISTORY = "/api/v1/event-cards/{id}/index-history"
CARD = "/api/v1/event-cards/{id}"
ARENA_BOOK = "/api/v1/arena/orderbook/{team}"
TIMEOUT = 20.0
# A whole round may take this long; what is left unread waits for the next
# one. Five doors at a 20 s timeout each could otherwise hold a round for
# minutes, and the tick that says so would be the last thing written.
ROUND_SECONDS = 90.0
TRADE_FIELDS = ("symbol", "side", "trade_type", "amount_usdc", "profit_usdc",
                "is_closed", "exit_reason", "executed_at", "closed_at")
# execution_class is in the signature on purpose: a bot that stopped being a
# paper simulation is the one change to its configuration that must show.
CONFIG_FIELDS = ("strategy_type", "risk_profile", "primary_indicators",
                 "secondary_indicators", "execution_class")
POSITION_FIELDS = ("status", "current_index", "current_value_usdc",
                   "unrealized_pnl_usdc", "realized_pnl_usdc")
# What describes a card, written again only when it changes. Not its index:
# that moves on every read and has a door of its own.
CARD_FIELDS = ("title", "evcdx_symbol", "status", "tradeable_now",
               "trading_closes_at", "index_base", "basket")
BASKET_TOP = 5
# What the card door returns for a 404: they no longer know the card. That is
# a fact about the card, written as its status -- not a round that fails every
# ten minutes for as long as a plan names it.
MISSING = object()

_SCRIPTS: dict = {}


def _script(name: str):
    """clone.py and paper.py, for the one reader of each body they already own."""
    if name not in _SCRIPTS:
        spec = importlib.util.spec_from_file_location(
            f"sampler_{name}", REPO_ROOT / "scripts" / f"{name}.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        _SCRIPTS[name] = module
    return _SCRIPTS[name]


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def follow() -> dict:
    """What is ours to follow, by our own records: the bots we cloned, the
    positions we opened and have not closed, each with its card, and the cards
    a plan names in a room that is not stopped."""
    bots: list[str] = []
    clones = rooms.records("clones.jsonl")
    # A clone we released is deleted on their side ("Bot deleted"), and its
    # balance and activity answer 404 "Bot not found." -- ten of them marked
    # every round NOT ok from 28 Sep to 1 Oct.
    releasing = {row.get("id"): row.get("instance_id") for row in clones
                 if row.get("type") == "intent" and row.get("kind") == "release"}
    released = {releasing.get(row.get("id")) for row in clones
                if row.get("type") == "outcome" and row.get("kind") == "release"
                and row.get("outcome") == "accepted"}
    for row in clones:
        instance = row.get("clone_instance_id")
        if (row.get("type") == "outcome" and row.get("outcome") == "accepted"
                and instance and instance not in bots and instance not in released):
            bots.append(instance)
    paper = rooms.records("paper.jsonl")
    intents = {r.get("id"): r for r in paper if r.get("type") == "intent"}
    opened: dict[str, str] = {}
    closed: set = set()
    for row in paper:
        if row.get("type") != "outcome" or row.get("outcome") != "accepted":
            continue
        intent = intents.get(row.get("id")) or {}
        if intent.get("kind") == "close":
            closed.add(intent.get("position_id"))
        elif row.get("position_id"):
            opened[row["position_id"]] = intent.get("card_id")
    stored = rooms.load()
    status = {row.get("room"): row.get("status") for row in stored
              if row.get("type") == "status"}
    proposed: list[str] = []
    teams: list[str] = []
    for room, plan in rooms.plans(stored).items():
        if status.get(room) == "stopped":
            continue
        for leg in plan.get("legs") or []:
            if rooms.leg_kind(leg) == "arena":
                if rooms.leg_ref(leg) and rooms.leg_ref(leg) not in teams:
                    teams.append(rooms.leg_ref(leg))
            elif leg.get("card") and leg["card"] not in proposed:
                proposed.append(leg["card"])
    return {"bots": bots,
            "positions": {p: c for p, c in opened.items() if p not in closed},
            "cards": proposed, "teams": teams}


def _signature(row: dict, fields) -> str:
    return json.dumps([row.get(f) for f in fields], sort_keys=True, default=str)


def _seen(rows: list[dict]) -> dict:
    """The newest of what is written only on change: each trade, each bot's
    configuration, and the last index point on record for each card."""
    trades: dict[str, str] = {}
    configs: dict[str, str] = {}
    cards: dict[str, str] = {}
    points: dict[str, str] = {}
    for row in rows:
        kind = row.get("type")
        if kind == "trade":
            trades[row.get("trade_id")] = _signature(row, TRADE_FIELDS)
        elif kind == "config":
            configs[row.get("instance_id")] = _signature(row, CONFIG_FIELDS)
        elif kind == "card":
            cards[row.get("card_id")] = _signature(row, CARD_FIELDS)
        elif kind == "index":
            card = row.get("card_id")
            for point in row.get("points") or []:
                if isinstance(point, list) and point:
                    points[card] = max(points.get(card, ""), str(point[0]))
    return {"trades": trades, "configs": configs, "cards": cards, "points": points}


class _Reads:
    """Each door's verdict for this round, and the round's clock."""

    def __init__(self) -> None:
        self.started = time.monotonic()
        self.verdicts: dict[str, str] = {}

    def say(self, name: str, verdict: str) -> None:
        # A door read more than once in a round -- once per bot, once per
        # card -- keeps its worst verdict, so a failure is never hidden by a
        # success that came after it.
        if self.verdicts.get(name, "ok") == "ok":
            self.verdicts[name] = verdict

    def get(self, client, name: str, path: str, missing=None, **params):
        if time.monotonic() - self.started > ROUND_SECONDS:
            self.say(name, "skipped")
            return None
        try:
            response = client.get(path, params=params or None)
        except httpx.TimeoutException:
            self.say(name, "timeout")
            return None
        except httpx.HTTPError as exc:
            self.say(name, f"failed: {type(exc).__name__}")
            return None
        if response.status_code == 404 and missing is not None:
            self.say(name, "ok")
            return missing
        if response.status_code != 200:
            self.say(name, f"HTTP {response.status_code}")
            return None
        try:
            body = response.json()
        except ValueError:
            self.say(name, "unreadable")
            return None
        self.say(name, "ok")
        return body


def _bots(client, reads: _Reads, instances: list[str], seen: dict, at: str) -> list[dict]:
    if not instances:
        return []
    rows: list[dict] = []
    listed = reads.get(client, "bots", BOTS, mode="paper")
    theirs: dict[str, dict] = {}
    if listed is not None:
        found = _script("clone").clone_rows(listed)
        if found is None:
            reads.say("bots", "unreadable")
        for row in found or []:
            if isinstance(row, dict) and row.get("id") in instances:
                theirs[row["id"]] = row
    for instance in instances:
        balance = reads.get(client, "balance", BALANCE.format(id=instance))
        activity = reads.get(client, "activity", ACTIVITY.format(id=instance))
        mine = theirs.get(instance)
        if mine is not None:
            split = balance if isinstance(balance, dict) else {}
            rows.append({"type": "sample", "kind": "bot", "at": at,
                         "instance_id": instance,
                         "is_trading": mine.get("is_trading"),
                         "is_paper": mine.get("is_paper"),
                         "balance_usdc": mine.get("current_balance_usdc"),
                         "total_profit_usdc": mine.get("total_profit_usdc"),
                         "trades_executed": mine.get("trades_executed"),
                         "win_rate": mine.get("win_rate"),
                         "last_trade_at": mine.get("last_trade_at"),
                         "locked_usdc": split.get("locked_in_trades"),
                         "available_usdc": split.get("available"),
                         # Why it stopped, when the platform did it: `stop_loss` or
                         # `take_profit` is the band WE configured (qa.lab.bot_stops).
                         "status": mine.get("status"),
                         "auto_pause_reason": mine.get("auto_pause_reason"),
                         "auto_pause_pnl_pct": mine.get("auto_pause_pnl_pct"),
                         "auto_pause_at": mine.get("auto_pause_at")})
            economics = mine.get("execution_economics")
            config = {"type": "config", "at": at, "instance_id": instance,
                      "strategy_type": mine.get("strategy_type"),
                      "risk_profile": mine.get("risk_profile"),
                      "primary_indicators": mine.get("primary_indicators"),
                      "secondary_indicators": mine.get("secondary_indicators"),
                      "execution_class": (economics.get("execution_class")
                                          if isinstance(economics, dict) else None)}
            if _signature(config, CONFIG_FIELDS) != seen["configs"].get(instance):
                rows.append(config)
        items = activity.get("items") if isinstance(activity, dict) else None
        if activity is not None and not isinstance(items, list):
            reads.say("activity", "unreadable")
        for item in items or []:
            if not isinstance(item, dict) or not item.get("id"):
                continue
            trade = {"type": "trade", "at": at, "instance_id": instance,
                     "trade_id": item["id"], **{f: item.get(f) for f in TRADE_FIELDS}}
            if _signature(trade, TRADE_FIELDS) != seen["trades"].get(item["id"]):
                rows.append(trade)
    return rows


def _describe(card: str, body, at: str) -> dict:
    """What a card is: its name, what its basket holds, when it closes."""
    if body is MISSING:
        return {"type": "card", "at": at, "card_id": card,
                **{f: None for f in CARD_FIELDS}, "status": "not_found", "basket": []}
    held = []
    for item in body.get("basket") or []:
        if not isinstance(item, dict) or not item.get("symbol"):
            continue
        try:
            weight = float(item.get("weight"))
        except (TypeError, ValueError):
            continue
        held.append({"symbol": item["symbol"], "weight": weight})
    held.sort(key=lambda item: -item["weight"])
    return {"type": "card", "at": at, "card_id": card,
            **{f: body.get(f) for f in CARD_FIELDS}, "basket": held[:BASKET_TOP]}


def _cards(client, reads: _Reads, positions: dict, proposed: list[str], seen: dict,
           at: str) -> list[dict]:
    rows: list[dict] = []
    watched: list[str] = []
    if positions:
        live: dict[str, dict] = {}
        body = reads.get(client, "positions", POSITIONS)
        if body is not None:
            try:
                listed = _script("paper").position_rows(body)
            except Exception:  # noqa: BLE001 -- UnreadableBody, and whatever else
                reads.say("positions", "unreadable")
                listed = []
            live = {r.get("position_id"): r for r in listed if isinstance(r, dict)}
        for position, card in positions.items():
            row = live.get(position)
            if row is None:
                continue
            rows.append({"type": "sample", "kind": "position", "at": at,
                         "position_id": position, "card_id": row.get("card_id") or card,
                         **{f: row.get(f) for f in POSITION_FIELDS}})
            if row.get("status") == "open" and card and card not in watched:
                watched.append(card)
    # Every card of ours described -- the positions' and the plans' -- and a
    # card they no longer know is not asked for its history.
    gone: set[str] = set()
    for card in dict.fromkeys([c for c in positions.values() if c] + list(proposed)):
        body = reads.get(client, "card", CARD.format(id=card), missing=MISSING)
        if body is None:
            continue
        if body is not MISSING and not isinstance(body, dict):
            reads.say("card", "unreadable")
            continue
        if body is MISSING:
            gone.add(card)
        row = _describe(card, body, at)
        if _signature(row, CARD_FIELDS) != seen["cards"].get(card):
            rows.append(row)
    for card in dict.fromkeys(watched + list(proposed)):
        if card in gone:
            continue
        history = reads.get(client, "history", HISTORY.format(id=card))
        found = history.get("points") if isinstance(history, dict) else None
        if history is not None and not isinstance(found, list):
            reads.say("history", "unreadable")
        points = [[p.get("t"), p.get("index")] for p in found or []
                  if isinstance(p, dict) and p.get("t")]
        new = [p for p in points if str(p[0]) > seen["points"].get(card, "")]
        if new:
            rows.append({"type": "index", "at": at, "card_id": card, "points": new})
    return rows


def _price(value):
    """Their book quotes prices as strings ("0.55"); null is an empty side."""
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError(value)
    return float(value)


def _arena(client, reads: _Reads, teams: list[str], at: str) -> list[dict]:
    """Each team's book, one row a round: the price series an arena leg's
    verdict reads (NEX-0076: a share never pays out, it is sold back into
    this book). Written every round, not on change -- like a bot's P&L, a
    price that did not move is still a point in the window."""
    rows: list[dict] = []
    for team in teams:
        door = rooms.ARENA_DOOR.format(team=team)
        # mode=paper: our share is bought on paper (place_arena_order's
        # `mode: paper`), and the filter is their published way to see only
        # the orders a paper sell can meet.
        body = reads.get(client, door, ARENA_BOOK.format(team=team), mode="paper")
        if body is None:
            continue
        try:
            if not isinstance(body, dict) or "best_bid" not in body:
                raise ValueError("no best_bid")
            quote = {f: _price(body.get(f))
                     for f in ("best_bid", "best_ask", "last_trade")}
        except (TypeError, ValueError):
            reads.say(door, "unreadable")
            continue
        rows.append({"type": "sample", "kind": "arena", "at": at, "team": team,
                     **quote})
    return rows


def tick(client, every: float) -> list[dict]:
    """One round: read, write what changed, and always a tick. Never raises."""
    at = _now()
    reads = _Reads()
    rows: list[dict] = []
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        ours = follow()
        seen = _seen(rooms.load_samples())
        rows += _bots(client, reads, ours["bots"], seen, at)
        rows += _cards(client, reads, ours["positions"], ours["cards"], seen, at)
        rows += _arena(client, reads, ours["teams"], at)
    except Exception as exc:  # noqa: BLE001 -- a broken round is a failed round
        reads.say("round", f"broke: {type(exc).__name__}: {exc}"[:200])
    finally:
        CURRENT_TIER.reset(token)
    rows.append({"type": "tick", "at": at, "every": every,
                 "ok": all(v == "ok" for v in reads.verdicts.values()),
                 "reads": reads.verdicts,
                 "seconds": round(time.monotonic() - reads.started, 2),
                 "rows": len(rows)})
    try:
        rooms.append_samples(rows)
    except OSError as exc:
        print(f"[sample] could not write state/samples.jsonl: {exc}", file=sys.stderr)
    return rows


def _client():
    from qa.client import build_client, install_client_guard
    from qa.config import identities, load_dotenv
    from qa.safety import EndpointRegistry

    load_dotenv()
    install_client_guard()
    return build_client(identities()["trusted"], EndpointRegistry.load(),
                        timeout=TIMEOUT)


def run(stop: threading.Event | None, every: float, client=None,
        until: float | None = None) -> int:
    """Round after round until `stop` is set, or `until` seconds have passed.

    Nothing a round does can end the loop: a round that cannot even build its
    client is written down as a failed tick and tried again next time.
    """
    stop = stop or threading.Event()
    deadline = time.monotonic() + until if until else None
    rounds = 0
    while True:
        try:
            if client is None:
                client = _client()
            tick(client, every)
        except Exception as exc:  # noqa: BLE001 -- the loop outlives any one round
            try:
                rooms.append_samples([{
                    "type": "tick", "at": _now(), "every": every, "ok": False,
                    "reads": {"round": f"broke: {type(exc).__name__}: {exc}"[:200]}}])
            except OSError:
                pass
        rounds += 1
        if deadline is not None and time.monotonic() >= deadline:
            return rounds
        if stop.wait(every):
            return rounds


def main(argv: list[str] | None = None) -> int:
    printable()
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("once", help="one round, then stop")
    loop = sub.add_parser("run", help="a round every --every seconds")
    loop.add_argument("--every", type=float, default=600.0)
    loop.add_argument("--until", type=float, default=None,
                      help="stop after this many seconds")
    args = parser.parse_args(argv)

    if args.cmd == "once":
        rows = tick(_client(), every=600.0)
        last = rows[-1]
        print(("ok" if last["ok"] else "NOT ok") + f": {len(rows) - 1} row(s); "
              + ", ".join(f"{k} {v}" for k, v in last["reads"].items()))
        return 0 if last["ok"] else 1
    if args.every < 60:
        parser.error("--every is in seconds; under a minute is hammering them")
    rounds = run(None, args.every, until=args.until)
    print(f"{rounds} round(s) written to state/samples.jsonl")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
