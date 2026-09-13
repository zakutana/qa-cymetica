"""Watch FOMO Radar's `hot` signal, and check whether it actually predicts a
memecoin moving. `qa/fomo.py` holds the logic; this is the two live rounds.

Deliberately NOT `scripts/sampler.py`: that script's own charter is "only what
our own records say is ours" -- our account's bots, positions, cards. FOMO
Radar and memecoin-terminal are Cymetica's public, platform-wide surfaces, not
our account, so this is its own script with its own diary.

    capture()   one round: poll `hot` signals on both chains, track the new
                ones, with the price at that moment (memecoin-terminal).
    resolve()   one round: for every tracked signal whose horizon has come
                due, read the price again and compute OUR OWN return since
                the signal -- never their rolling %, which is relative to now.

Both are read-only GETs, SAFE tier, no key, on surfaces that answer live and
are absent from /api-docs (told to the operator 2026-09-13; see CLAUDE.md).
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from qa import fomo  # noqa: E402
from qa.state import file_lock, state_dir  # noqa: E402

SIGNALS_PATH = "/api/v1/clones/fomo-radar/signals"
SEARCH_PATH = "/api/v1/clones/memecoin-terminal/search"
CHAINS = ("robinhood", "solana")


def diary_path() -> Path:
    return state_dir() / "fomo_signals.jsonl"


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


def _append(row: dict) -> dict:
    path = diary_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    with file_lock(path):
        with open(path, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    return row


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _hot_rows(client, chain: str) -> list[dict]:
    response = client.get(SIGNALS_PATH, params={"chain": chain, "filter": "hot"})
    if response.status_code != 200:
        return []
    body = response.json() or {}
    return body.get("rows") or []


def _price(client, token_address: str) -> float | None:
    """`search?q=<address>` -- confirmed live 2026-09-13: `{"rows": [{"address",
    "price_usd", ...}]}`. Matched on `address` because a symbol/name search
    can answer with more than one token; an address search should not, but a
    server that changes its mind about that is not this function's problem to
    guess at -- match, don't assume the first row."""
    response = client.get(SEARCH_PATH, params={"q": token_address})
    if response.status_code != 200:
        return None
    body = response.json() or {}
    wanted = str(token_address or "").lower()
    for row in body.get("rows") or []:
        if isinstance(row, dict) and str(row.get("address", "")).lower() == wanted:
            price = row.get("price_usd")
            return float(price) if isinstance(price, (int, float)) else None
    return None


def capture(client, now=None) -> dict:
    """One round. Never raises: a call that fails leaves the diary as it was,
    which is the safe direction -- a signal missed this poll is caught by the
    next one, ten minutes later."""
    now = now or _now()
    rows = load()
    tracked = {r["key"] for r in rows if r.get("type") == "signal" and r.get("key")}
    added = []
    for chain in CHAINS:
        try:
            hot_rows = _hot_rows(client, chain)
        except Exception as exc:  # noqa: BLE001 -- one chain failing is not the round
            added.append({"chain": chain, "error": str(exc)[:200]})
            continue
        for row in fomo.new_signals(hot_rows, tracked, at=now):
            key = fomo.signal_key(row.get("token_address"), now)
            price = None
            try:
                price = _price(client, row.get("token_address"))
            except Exception:  # noqa: BLE001 -- price stays None, not a crash
                pass
            signal = _append({
                "type": "signal", "at": now.isoformat(), "key": key,
                "token_address": row.get("token_address"),
                "symbol": row.get("symbol"), "chain": chain,
                "conviction": row.get("conviction"), "price_usd": price,
            })
            tracked.add(key)
            added.append(signal)
    return {"added": len(added), "signals": added}


def resolve(client, now=None) -> dict:
    """One round: whatever has crossed a horizon gets checkpointed."""
    now = now or _now()
    rows = load()
    signals = [r for r in rows if r.get("type") == "signal" and r.get("key")]
    done: dict[str, set[str]] = {}
    for row in rows:
        if row.get("type") == "checkpoint" and row.get("key"):
            done.setdefault(row["key"], set()).add(row.get("horizon", "?"))

    written = []
    for signal, horizon in fomo.due_checkpoints(signals, done, now=now):
        try:
            price = _price(client, signal.get("token_address"))
        except Exception as exc:  # noqa: BLE001
            written.append({"key": signal["key"], "horizon": horizon,
                            "error": str(exc)[:200]})
            continue
        ret = fomo.return_since_signal(signal.get("price_usd"), price)
        written.append(_append({
            "type": "checkpoint", "at": now.isoformat(), "key": signal["key"],
            "horizon": horizon, "price_usd": price, "return_pct": ret,
        }))
    return {"checked": len(written), "checkpoints": written}


def tick(client) -> dict:
    """One round: capture, then resolve whatever is due. Capture first, so a
    signal that just crossed 1h in the same round it was caught still has to
    wait for the next tick -- never checkpointed against its own birth.

    Sets its own SAFE tier, the same way `scripts/sampler.py::tick` does --
    `run()` below is meant to live in a server's background thread, which
    starts with no tier in scope at all.
    """
    from qa.safety import CURRENT_TIER, SafetyTier

    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        return {"capture": capture(client), "resolve": resolve(client)}
    finally:
        CURRENT_TIER.reset(token)


def run(stop, every: float, client=None) -> int:
    """Round after round until `stop` is set. Nothing a round does can end the
    loop -- the same rule `scripts/sampler.py::run` follows, for the same
    reason: a script started once by the operator (`serve.py --fomo MINUTES`)
    must not die because one HTTP call somewhere failed.
    """
    import threading
    import time

    stop = stop or threading.Event()
    rounds = 0
    while True:
        try:
            if client is None:
                client = _client()
            tick(client)
        except Exception as exc:  # noqa: BLE001 -- the loop outlives any one round
            print(f"[fomo] round failed: {type(exc).__name__}: {exc}",
                 file=sys.stderr)
        rounds += 1
        if stop.wait(every):
            return rounds


def _client():
    from qa.client import build_client
    from qa.config import identities, load_dotenv
    from qa.safety import EndpointRegistry

    load_dotenv()
    return build_client(identities()["anon"], EndpointRegistry.load(), timeout=30.0)


def _run(cmd) -> int:
    from qa.safety import CURRENT_TIER, SafetyTier

    client = _client()
    token = CURRENT_TIER.set(SafetyTier.SAFE)
    try:
        result = cmd(client)
    finally:
        CURRENT_TIER.reset(token)
        client.close()
    # ensure_ascii=True: a token's own name can carry anything, and the
    # Windows console's default codepage cannot -- this is a status line, not
    # evidence, so ascii-escaping it is cheaper than a crash.
    print(json.dumps(result, ensure_ascii=True, indent=1)[:2000])
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("capture", help="poll hot signals, track the new ones")
    sub.add_parser("resolve", help="checkpoint whatever crossed a horizon")

    args = parser.parse_args(argv)
    return _run(capture) if args.cmd == "capture" else _run(resolve)


if __name__ == "__main__":
    raise SystemExit(main())
