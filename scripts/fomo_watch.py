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


class FeedError(RuntimeError):
    """Their signals endpoint did not answer. NOT an hour with nothing hot.

    It returned `[]` on any non-200 until the deep pass of 2026-09-13, so a
    503 and a quiet market were byte-identical in `capture()`'s result -- no
    error row, added 0, unidentified 0 -- and the per-chain `except` could
    never fire, because nothing raised. Rule 8 one level up from the row,
    in the module where `unidentified` had been added the same day for the
    identical reason one level down.
    """


def _hot_rows(client, chain: str) -> list[dict]:
    response = client.get(SIGNALS_PATH, params={"chain": chain, "filter": "hot"})
    if response.status_code != 200:
        raise FeedError(
            f"{SIGNALS_PATH} (chain={chain}) answered HTTP "
            f"{response.status_code}; a failed read is not an empty feed")
    body = response.json() or {}
    return body.get("rows") or []


class QuoteError(RuntimeError):
    """Their search endpoint did not answer. NOT a token they have stopped
    listing -- rule 8, one surface along from `FeedError`."""


def _listing(client, token_address: str) -> dict | None:
    """The matched row, or None when they answered 200 and did not know the
    token. Raises `QuoteError` on anything that is not a 200, because a 503
    and a delisting must never write the same row."""
    response = client.get(SEARCH_PATH, params={"q": token_address})
    if response.status_code != 200:
        raise QuoteError(f"{SEARCH_PATH} (q={token_address}) answered HTTP "
                         f"{response.status_code}; a failed read is not a "
                         f"token they have dropped")
    wanted = str(token_address or "").lower()
    for row in (response.json() or {}).get("rows") or []:
        if isinstance(row, dict) and str(row.get("address", "")).lower() == wanted:
            return row
    return None


def _quote(client, token_address: str) -> dict | None:
    """`search?q=<address>` -- confirmed live 2026-09-13: `{"rows": [{"address",
    "price_usd", ...}]}`. Matched on `address` because a symbol/name search
    can answer with more than one token; an address search should not, but a
    server that changes its mind about that is not this function's problem to
    guess at -- match, don't assume the first row."""
    response = client.get(SEARCH_PATH, params={"q": token_address})
    if response.status_code != 200:
        return None
    wanted = str(token_address or "").lower()
    for row in (response.json() or {}).get("rows") or []:
        if isinstance(row, dict) and str(row.get("address", "")).lower() == wanted:
            return row
    return None


# What a price has to carry to be a price somebody could have traded at.
# Read live 2026-09-14: MelonMusk, the single biggest return in the whole
# diary at +73848%, quotes a pair holding `liquidity_usd: 0.02` against
# `volume_h24: 0.25` -- two cents of depth and a quarter of a dollar traded
# all day. ASTRO, frozen at one price across six checkpoints, quotes
# `liquidity_usd: 0.0`. Neither is their defect: DexScreener repeats the last
# print until somebody trades again, and their terminal passes it through.
# It is ours, because we wrote the print down as a return and drew it. We had
# these fields in the same response the price came out of and kept only the
# price, so a year of diary cannot be re-judged. Kept from now on.
DEPTH_FIELDS = ("liquidity_usd", "volume_h24", "market_cap", "buys_h24",
                "sells_h24", "age_seconds", "dex")


def _depth(quote: dict | None) -> dict:
    return {k: (quote or {}).get(k) for k in DEPTH_FIELDS
            if (quote or {}).get(k) is not None}


# What the RADAR itself said when it fired, kept under its own prefix beside
# our reading of the same thing. Their tradeability gate (shipped 2026-09-14:
# hot only if `max_buy_5pct_usd` >= 500, the refused burst left as
# `hot_pressure`, `thin` beside it) reads their number at their moment; ours
# is a second quote from memecoin-terminal against another source. Without
# both, a row that got through the gate can never be told from one that
# simply moved between the two reads.
RADAR_FIELDS = ("liquidity_usd", "max_buy_5pct_usd", "hot_pressure", "thin",
                "signal_type", "conviction_kind", "token_age_seconds",
                "usd_invested", "qualified_buyers", "new_qualified_buyers_15m")


def _radar(row: dict | None) -> dict:
    return {f"radar_{k}": (row or {})[k] for k in RADAR_FIELDS
            if (row or {}).get(k) is not None}


def _price(client, token_address: str) -> float | None:
    price = (_quote(client, token_address) or {}).get("price_usd")
    return float(price) if isinstance(price, (int, float)) else None


def capture(client, now=None) -> dict:
    """One round. Never raises: a call that fails leaves the diary as it was,
    which is the safe direction -- a signal missed this poll is caught by the
    next one, ten minutes later."""
    now = now or _now()
    rows = load()
    tracked = {r["key"] for r in rows if r.get("type") == "signal" and r.get("key")}
    added = []
    # A hot row carrying no token_address cannot be tracked -- `signal_key`
    # returns None and `new_signals` drops it, which is right: forty anonymous
    # curves must not collapse into one key. But dropping it silently makes
    # their outage of 2026-09-13 11:52 (every Robinhood row anonymous for six
    # minutes) indistinguishable from an hour when nothing went hot. Rule 8,
    # on a row rather than on a read: count what could not be identified.
    unidentified = 0
    # Errors have their OWN list. They used to go into `added` beside the
    # signals, so `added: 2` was satisfied by two failed chains and zero
    # signals written -- and the test that exists to prove a signal survives a
    # failed price lookup asserted exactly that number. L01, deep pass of
    # 2026-09-13. A count of signals counts signals.
    errors: list[dict] = []
    for chain in CHAINS:
        try:
            hot_rows = _hot_rows(client, chain)
        except Exception as exc:  # noqa: BLE001 -- one chain failing is not the round
            errors.append({"chain": chain, "error": str(exc)[:200]})
            continue
        unidentified += sum(
            1 for row in hot_rows or []
            if isinstance(row, dict) and row.get("hot")
            and not str(row.get("token_address") or "").strip())
        for row in fomo.new_signals(hot_rows, tracked, at=now):
            key = fomo.signal_key(row.get("token_address"), now)
            quote = None
            try:
                quote = _quote(client, row.get("token_address"))
            except Exception:  # noqa: BLE001 -- price stays None, not a crash
                pass
            price = (quote or {}).get("price_usd")
            price = float(price) if isinstance(price, (int, float)) else None
            signal = _append({
                "type": "signal", "at": now.isoformat(), "key": key,
                "token_address": row.get("token_address"),
                "symbol": row.get("symbol"), "chain": chain,
                "conviction": row.get("conviction"), "price_usd": price,
                **_depth(quote), **_radar(row),
            })
            tracked.add(key)
            added.append(signal)
    return {"added": len(added), "signals": added, "errors": errors,
            "unidentified": unidentified}


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
            quote = _quote(client, signal.get("token_address"))
        except Exception as exc:  # noqa: BLE001
            written.append({"key": signal["key"], "horizon": horizon,
                            "error": str(exc)[:200]})
            continue
        price = (quote or {}).get("price_usd")
        price = float(price) if isinstance(price, (int, float)) else None
        ret = fomo.return_since_signal(signal.get("price_usd"), price)
        written.append(_append({
            "type": "checkpoint", "at": now.isoformat(), "key": signal["key"],
            "horizon": horizon, "price_usd": price, "return_pct": ret,
            **_depth(quote),
        }))
    return {"checked": len(written), "checkpoints": written}


def depth(client, now=None, only_missing: bool = True) -> dict:
    """One round: read what each tracked token's pair is worth trading in.

    [operator 2026-09-14] *"proc to zobrazuje coiny co se neda obchodvat nebo
    prodavat? ty jsou uplne zbytecne"*. `resolve()` carries the same fields on
    every checkpoint from 2026-09-14, so a signal still inside its first day
    answers this by itself within the hour. This round is for the rest: the
    tokens whose 24h is over and which nothing will ever read again, and the
    first seeding of a diary written before the fields existed.

    `only_missing` keeps it cheap and repeatable -- a token that already has
    depth from a checkpoint or an earlier seed is not asked about again.
    """
    now = now or _now()
    rows = load()
    signals = {}
    for row in rows:
        if row.get("type") == "signal" and row.get("token_address"):
            signals[str(row["token_address"])] = row

    from qa import fomo

    known = fomo._depth_by_token(rows) if only_missing else {}
    written = failed = 0
    for address in sorted(signals):
        if address.lower() in known:
            continue
        try:
            quote = _listing(client, address)
        except Exception as exc:  # noqa: BLE001 -- rule 8: write nothing
            failed += 1
            print(f"[fomo] depth {address[:12]}: {exc}", file=sys.stderr)
            continue
        _append({"type": "depth", "at": now.isoformat(),
                 "token_address": address, "listed": quote is not None,
                 **_depth(quote)})
        written += 1
    return {"written": written, "failed": failed, "known": len(known),
            "tokens": len(signals)}


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
    sub.add_parser("depth", help="what each tracked token can be traded in")

    args = parser.parse_args(argv)
    return _run({"capture": capture, "resolve": resolve,
                 "depth": depth}[args.cmd])


if __name__ == "__main__":
    raise SystemExit(main())
