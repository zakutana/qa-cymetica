"""The Hot headlines watch: what is in Hot every round, so a rule can be tested.

    python scripts/hot_watch.py capture   one round: the hot top 100 and the wire
    python scripts/hot_watch.py resolve   read the card behind each day-old entry
    python scripts/hot_watch.py report    entries, what they did after, NEX-0055

Started 2026-09-21, when the operator asked the laboratory to work out with
Nexus how to get into Hot rows before they move. What Hot is, and why the
diary has this shape, is in qa/hot.py. The short of it:

* Hot has no history. When a basket entered it, and what its index read at
  that moment, exist only if a round saw it -- hence a round every tick.
* The wire (`?limit=500`, about 56 h) carries the index price of every recent
  headline, so one read per round follows every entry through its whole day.
  Nothing is priced leg by leg.
* The card behind a row CAN be read afterwards: index-history has a point
  every few minutes since the card was minted. So it is read once, after the
  entry's day is out, instead of on every round.

SAFE reads only. The diary is state/hot_watch.jsonl, gitignored and not
snapshotted: at about 2 MB a day it would grow git for ever.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa import hot  # noqa: E402
from qa.fomo import _at  # noqa: E402
from qa.state import file_lock, state_dir  # noqa: E402

HEADLINES = "/api/v1/headlines"
HISTORY = "/api/v1/event-cards/{card}/index-history"
HOT_LIMIT = 100
WIRE_LIMIT = 500
CARDS_PER_RESOLVE = 20
READ_DEADLINE_S = 90.0
CARD_WINDOW_HOURS = (-1.0, 25.0)
# A card read that failed is tried again on a later resolve -- a 503 or a
# timeout is usually gone by the next tick -- but not for ever: a card they
# dropped answers 404 on every tick, and each of those is a GET for nothing.
# Three reads on three ticks separates the two; after that it is unobserved.
MAX_CARD_TRIES = 3


def diary_path() -> Path:
    return state_dir() / "hot_watch.jsonl"


def load() -> list[dict]:
    path = diary_path()
    if not path.is_file():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            out.append(row)
    return out


def _append(rows: list[dict]) -> None:
    if not rows:
        return
    path = diary_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(path):
        with open(path, "a", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _num(value, digits: int = 6):
    return round(float(value), digits) if isinstance(value, (int, float)) else None


def _read(client, params: dict) -> tuple[list | None, str | None]:
    """One read with a deadline for the WHOLE answer. httpx's timeout is
    between bytes, and on 2026-09-21 a `limit=500` answer trickling in hung a
    tick for fifteen minutes without ever tripping it."""
    import time

    started = time.monotonic()
    try:
        with client.stream("GET", HEADLINES, params=params) as response:
            if response.status_code != 200:
                return None, f"{params}: HTTP {response.status_code}"
            chunks = []
            for chunk in response.iter_bytes():
                chunks.append(chunk)
                if time.monotonic() - started > READ_DEADLINE_S:
                    return None, (f"{params}: past the {READ_DEADLINE_S:g}s "
                                  f"deadline for the whole answer")
            body = b"".join(chunks)
    except Exception as exc:  # noqa: BLE001 -- an unreadable answer is data
        return None, f"{params}: {type(exc).__name__}: {exc}"[:200]
    try:
        items = json.loads(body).get("items")
    except (ValueError, AttributeError):
        return None, f"{params}: not JSON"
    if not isinstance(items, list):
        return None, f"{params}: no items"
    return items, None


def _hot_row(rank: int, item: dict) -> list | None:
    idx = item.get("hotidx") or {}
    cls = idx.get("hot_class")
    if cls not in hot.CLASSES:
        return None
    key = "crypto" if cls == "crypto" else "stock"
    return [item.get("id"), rank, _num(idx.get("hot")), cls,
            _num(idx.get(f"{key}_px")), _num(idx.get(f"{key}_ret_24h"))]


def _wire_row(item: dict) -> list | None:
    idx = item.get("hotidx") or {}
    s_px, c_px = _num(idx.get("stock_px")), _num(idx.get("crypto_px"))
    if not (s_px or c_px):
        return None
    return [item.get("id"), s_px, c_px, _num(idx.get("stock_ret_24h")),
            _num(idx.get("crypto_ret_24h"))]


def _headline_row(item: dict, at: str) -> dict:
    idx = item.get("hotidx") or {}
    stock, crypto = idx.get("stock_members") or [], idx.get("crypto_members") or []
    return {"type": "headline", "at": at, "id": item.get("id"),
            "published_at": item.get("published_at"),
            "headline": item.get("headline"), "source": item.get("source"),
            "tags": item.get("tags") or [], "tickers": item.get("tickers") or [],
            "value_usd": item.get("value_usd"),
            "event_card_id": item.get("event_card_id"),
            "stock_members": stock, "crypto_members": crypto,
            "stock_fp": hot.basket_fp(stock, "stocks"),
            "crypto_fp": hot.basket_fp(crypto, "crypto")}


def capture(client, now=None, rows: list | None = None) -> dict:
    """One round. A failed hot read is written as `hot: null`, never as an
    empty tab: were it empty, the next round would call everything an entry.
    `rows`, when given, is the diary already read -- and what this round
    writes is appended to it too, so the caller's copy stays the file's."""
    at = (now or _now()).isoformat(timespec="seconds")
    hot_items, hot_err = _read(client, {"filter": "hot", "limit": HOT_LIMIT})
    wire_items, wire_err = _read(client, {"limit": WIRE_LIMIT})
    errors = [e for e in (hot_err, wire_err) if e]

    hot_rows = None
    if hot_items is not None:
        hot_rows = [r for r in (_hot_row(i + 1, it) for i, it in enumerate(hot_items)) if r]
    wire_rows = [r for r in (_wire_row(it) for it in wire_items or []) if r]

    diary = load() if rows is None else rows
    known = {r.get("id") for r in diary if r.get("type") == "headline"}
    fresh, seen = [], set()
    for item in (hot_items or []) + (wire_items or []):
        hid = item.get("id")
        if hid is None or hid in known or hid in seen or not item.get("hotidx"):
            continue
        seen.add(hid)
        fresh.append(_headline_row(item, at))

    written = fresh + [{"type": "round", "at": at, "ok": not errors,
                        "errors": errors, "hot": hot_rows, "wire": wire_rows}]
    _append(written)
    if rows is not None:
        rows.extend(written)
    return {"ok": not errors, "errors": errors, "headlines": len(fresh),
            "hot": len(hot_rows or []), "wire": len(wire_rows)}


def _points(body) -> list[list]:
    pts = body.get("points") if isinstance(body, dict) else None
    out = []
    for p in pts or []:
        if isinstance(p, dict) and _at(p.get("t")) and isinstance(p.get("index"), (int, float)):
            out.append([p["t"], p["index"]])
    return out


def _card_attempts(rows) -> dict:
    """(fp, entry_at) -> [ok row or None, failed attempts, a failed row]."""
    out: dict[tuple, list] = {}
    for r in rows:
        if r.get("type") != "card":
            continue
        slot = out.setdefault((r.get("fp"), r.get("entry_at")), [None, 0, None])
        if r.get("ok"):
            slot[0] = slot[0] or r
        else:
            slot[1] += 1
            slot[2] = slot[2] or r
    return out


def resolve(client, now=None, rows: list | None = None) -> dict:
    """Each entry whose day is out gets its card's history: read until one
    read succeeds, or MAX_CARD_TRIES have failed. Rule 8: a failed read is not
    a read, so it does not make the entry done."""
    now = now or _now()
    rows = load() if rows is None else rows
    done = {key for key, (ok, failed, _) in _card_attempts(rows).items()
            if ok or failed >= MAX_CARD_TRIES}
    due = [e for e in hot.entries(rows)
           if e.get("event_card_id") and (e["fp"], e["at"]) not in done
           and _at(e["at"]) + timedelta(hours=hot.RULE["hold_hours"]) <= now]
    written = []
    for e in due[:CARDS_PER_RESOLVE]:
        card = e["event_card_id"]
        row = {"type": "card", "at": now.isoformat(timespec="seconds"),
               "fp": e["fp"], "entry_at": e["at"], "card_id": card}
        try:
            response = client.get(HISTORY.format(card=card))
            ok = response.status_code == 200
            points = _points(response.json()) if ok else []
            row.update(ok=ok, status=response.status_code)
        except Exception as exc:  # noqa: BLE001
            points = []
            row.update(ok=False, status=f"{type(exc).__name__}: {exc}"[:160])
        lo = _at(e["at"]) + timedelta(hours=CARD_WINDOW_HOURS[0])
        hi = _at(e["at"]) + timedelta(hours=CARD_WINDOW_HOURS[1])
        row["points"] = [p for p in points if lo <= _at(p[0]) <= hi]
        written.append(row)
    _append(written)
    return {"cards": len(written), "due": len(due)}


def tick(client) -> dict:
    from qa.safety import CURRENT_TIER, SafetyTier

    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        # One read of the diary per tick (R11, deep pass of 2026-09-21).
        rows = load()
        return {"capture": capture(client, rows=rows),
                "resolve": resolve(client, rows=rows)}
    finally:
        CURRENT_TIER.reset(token)


def run(stop, every: float, client=None) -> int:
    """Round after round until `stop` is set, for `serve.py --hot MINUTES`.
    Nothing a round does ends the loop -- the rule fomo_watch.run and
    sampler.run follow: a console started once by the operator must not stop
    watching because one HTTP call failed."""
    import threading

    stop = stop or threading.Event()
    rounds = 0
    while True:
        try:
            if client is None:
                client = _client()
            tick(client)
        except Exception as exc:  # noqa: BLE001 -- the loop outlives any one round
            print(f"[hot] round failed: {type(exc).__name__}: {exc}",
                  file=sys.stderr)
        rounds += 1
        if stop.wait(every):
            return rounds


def card_follow(rows, horizons=(6.0, 24.0)) -> dict:
    """The card's own return over the same horizons, from its history.

    B07, deep pass of 2026-09-21: a card whose read failed, or whose history
    has no point near the entry or the horizon, was dropped and `unobserved`
    was a hard 0. It is unobserved now -- counted, never a zero -- unless the
    diary has not reached the horizon yet, which is open, as in hot.follow.

    Since resolve() retries a failed read, several rows can stand for one
    entry: it is ONE card, read off its ok row if any, else one failed row."""
    cards = [ok or failed for (_, entry_at), (ok, _, failed)
             in _card_attempts(rows).items() if _at(entry_at)]
    stamps = [t for t in (_at(r.get("at")) for r in rows) if t]
    last = max(stamps, default=None)
    slack = timedelta(minutes=hot.TOLERANCE_MINUTES)
    out = {}
    for h in horizons:
        values, missing, open_ = [], 0, 0
        for r in cards:
            t0 = _at(r["entry_at"])
            target = t0 + timedelta(hours=h)
            pts = [(_at(t), v) for t, v in r.get("points") or []] if r.get("ok") else []
            start = min(pts, key=lambda p: abs(p[0] - t0), default=None)
            end = min(pts, key=lambda p: abs(p[0] - target), default=None)
            if (start and end and start[1]
                    and abs(start[0] - t0) <= slack and abs(end[0] - target) <= slack):
                values.append(round((end[1] / start[1] - 1) * 100, 6))
            elif last is None or target + slack > last:
                open_ += 1
            else:
                missing += 1
        out[h] = hot._summary(values, missing, open_)
    return out


def reading(rows: list[dict] | None = None) -> dict:
    """Everything the report prints. Reads the diary only -- no call."""
    rows = load() if rows is None else rows
    rounds = [r for r in rows if r.get("type") == "round"]
    found = hot.entries(rows)
    return {"rounds": len(rounds),
            "first": rounds[0]["at"] if rounds else None,
            "last": rounds[-1]["at"] if rounds else None,
            "entries": {c: sum(1 for e in found if e["cls"] == c) for c in hot.CLASSES},
            "follow": hot.follow(found, rows),
            "control": hot.control(rows, found),
            "cards": card_follow(rows),
            "rules": {name: {k: v for k, v in hot.nexus_rule(rows, rule=rule).items()
                             if k != "trades"}
                      for name, rule in hot.VARIANTS.items()}}


def _pct(value) -> str:
    return "-" if value is None else f"{value:+.2f}%"


def say_reading(said: dict) -> list[str]:
    if not said or not said.get("rounds"):
        return ["  no round yet"]
    lines = [f"  {said['rounds']} round(s) {str(said['first'])[:16]} .. "
             f"{str(said['last'])[:16]}; entries crypto {said['entries']['crypto']}, "
             f"stocks {said['entries']['stocks']}  (their price-weighted index, not 1/N)"]
    for cls in hot.CLASSES:
        for mine, base in zip(said["follow"][cls], said["control"][cls]):
            lines.append(
                f"  {cls:6} +{mine['hours']:.0f}h: entered {_pct(mine['mean'])} mean, "
                f"{mine['up']}/{mine['n']} up ({mine.get('open', 0)} still open, "
                f"{mine['unobserved']} unseen) | "
                f"not in Hot {_pct(base['mean'])}, {base['up']}/{base['n']} up")
    for h, c in (said.get("cards") or {}).items():
        lines.append(f"  card   +{float(h):.0f}h: {_pct(c['mean'])} mean over {c['n']} "
                     f"({c.get('open', 0)} still open, {c.get('unobserved', 0)} unseen)")
    rules = said.get("rules") or {"NEX-0055": said.get("rule") or {}}
    for name, rule in rules.items():
        lines.append(f"  {name}: {rule.get('entries', 0)} qualifying entr(ies), "
                     f"{rule.get('open', 0)} open, {rule.get('unobserved', 0)} unseen "
                     f"-- {rule.get('verdict')}")
    return lines


def _client():
    from qa.client import build_client
    from qa.config import identities, load_dotenv
    from qa.safety import EndpointRegistry

    load_dotenv()
    return build_client(identities()["anon"], EndpointRegistry.load(), timeout=60.0)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    for name in ("capture", "resolve", "report"):
        sub.add_parser(name)
    args = parser.parse_args(argv)
    if args.cmd == "report":
        print("\n".join(say_reading(reading())))
        return 0
    from qa.safety import CURRENT_TIER, SafetyTier

    client = _client()
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        said = capture(client) if args.cmd == "capture" else resolve(client)
    finally:
        CURRENT_TIER.reset(token)
        client.close()
    print(json.dumps(said, ensure_ascii=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
