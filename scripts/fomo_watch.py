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


def _feed(client, chain: str, hot_only: bool = True) -> dict:
    """One read of their signals feed. `hot_only=False` is everything the
    round lists -- the pool the control group is drawn from (2026-09-19: 40
    rows on Solana, 11 of them hot)."""
    params = {"chain": chain, "filter": "hot"} if hot_only else {"chain": chain}
    response = client.get(SIGNALS_PATH, params=params)
    if response.status_code != 200:
        raise FeedError(
            f"{SIGNALS_PATH} (chain={chain}) answered HTTP "
            f"{response.status_code}; a failed read is not an empty feed")
    body = response.json() or {}
    return body if isinstance(body, dict) else {}


def _hot_rows(client, chain: str) -> list[dict]:
    return _feed(client, chain).get("rows") or []


# Their own claim, kept each time it changes: the number our measurement of
# hot-against-control is held to (qa/fomo.py, the study).
CALIBRATION_FIELDS = ("target_multiple", "horizon_hours", "base_rate", "brier",
                      "brier_base", "n_samples", "sufficient", "method")


def _claim(calibration) -> dict | None:
    if not isinstance(calibration, dict):
        return None
    claim = {k: calibration.get(k) for k in CALIBRATION_FIELDS
             if calibration.get(k) is not None}
    hot = ((calibration.get("type_precision") or {}).get("hot")
           if isinstance(calibration.get("type_precision"), dict) else None)
    if isinstance(hot, dict):
        for ours, theirs in (("hot_precision", "precision"), ("hot_n", "n"),
                             ("hot_hits", "hits"), ("hot_ci_low", "ci_low"),
                             ("hot_ci_high", "ci_high"),
                             # Without this the figure outlives the caveat it
                             # was published with (2026-09-21).
                             ("hot_sufficient", "sufficient")):
            if hot.get(theirs) is not None:
                claim[ours] = hot[theirs]
    return claim or None


def _note_claim(rows: list[dict], chain: str, calibration, now) -> bool:
    claim = _claim(calibration)
    if claim is None:
        return False
    last = None
    for row in rows:
        if row.get("type") == "calibration" and row.get("chain") == chain:
            last = row
    # Unchanged only when the two claims are EQUAL, both ways. Compared one
    # way -- every field of the new one matching the stored row -- a version
    # that stopped publishing a field matched on what was left and was never
    # written (L04, deep pass of 2026-09-19).
    stored = ({k: v for k, v in last.items()
               if k not in ("type", "at", "chain")} if last else None)
    if stored == claim:
        return False
    rows.append(_append({"type": "calibration", "at": now.isoformat(),
                         "chain": chain, **claim}))
    return True


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
    controlled = {r["key"] for r in rows if r.get("type") == "control"
                  and r.get("key")}
    control = 0
    for chain in CHAINS:
        try:
            body = _feed(client, chain)
        except Exception as exc:  # noqa: BLE001 -- one chain failing is not the round
            errors.append({"chain": chain, "error": str(exc)[:200]})
            continue
        hot_rows = body.get("rows") or []
        _note_claim(rows, chain, body.get("calibration"), now)
        unidentified += sum(
            1 for row in hot_rows or []
            if isinstance(row, dict) and row.get("hot")
            and not str(row.get("token_address") or "").strip())
        before = len(added)
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
        # The control group, matched to this chain's round in number and in
        # time: as many coins the same feed listed and did NOT call hot as it
        # did call, right now. A round that called nothing draws nothing -- a
        # control from a quiet hour measures a different market.
        called = len(added) - before
        if called:
            try:
                listed = _feed(client, chain, hot_only=False).get("rows") or []
            except Exception as exc:  # noqa: BLE001 -- the study, not the signal
                errors.append({"chain": chain, "control": True,
                               "error": str(exc)[:200]})
                listed = []
            for row in fomo.pick_control(listed, called, controlled, at=now,
                                         hot_keys=tracked):
                key = fomo.control_key(row.get("token_address"), now)
                quote = None
                try:
                    quote = _quote(client, row.get("token_address"))
                except Exception:  # noqa: BLE001 -- price stays None
                    pass
                price = (quote or {}).get("price_usd")
                price = float(price) if isinstance(price, (int, float)) else None
                _append({
                    "type": "control", "at": now.isoformat(), "key": key,
                    "token_address": row.get("token_address"),
                    "symbol": row.get("symbol"), "chain": chain,
                    "conviction": row.get("conviction"), "price_usd": price,
                    **_depth(quote), **_radar(row),
                })
                controlled.add(key)
                control += 1
    return {"added": len(added), "signals": added, "errors": errors,
            "unidentified": unidentified, "control": control}


def resolve(client, now=None) -> dict:
    """One round: whatever has crossed a horizon gets checkpointed."""
    now = now or _now()
    rows = load()
    signals = [r for r in rows if r.get("type") == "signal" and r.get("key")]
    done: dict[str, set[str]] = {}
    for row in rows:
        if row.get("type") == "checkpoint" and row.get("key"):
            done.setdefault(row["key"], set()).add(row.get("horizon", "?"))

    # One quote per coin per round. A coin hot in consecutive hours is several
    # signals due at the same moment, and the price is the same for all of
    # them: 262 quotes for 89 coins in one round of 2026-09-19, which was most
    # of the loop's first live tick. A failed read is remembered as failed for
    # the round too -- asking again a second later is not a second opinion.
    quoted: dict[str, object] = {}

    def quote_once(address):
        token = str(address or "").lower()
        if token not in quoted:
            try:
                quoted[token] = _quote(client, address)
            except Exception as exc:  # noqa: BLE001 -- re-raised per reading
                quoted[token] = exc
        said = quoted[token]
        if isinstance(said, Exception):
            raise said
        return said

    # A signal that fired with no price is quoted once more, as its own
    # `entry` row carrying the moment it was read -- never written onto the
    # signal, whose horizons are counted from when IT fired. A failed read
    # writes nothing, so the next round inside the hour tries again.
    retried = {r["key"] for r in rows if r.get("type") == "entry" and r.get("key")}
    entries = 0
    for signal in fomo.entry_retries(signals, retried, now=now):
        # `_listing`, not `_quote`: `_quote` answers None on a 503, and a
        # retry spent on an outage would be written as a coin with no price.
        try:
            quote = _listing(client, signal.get("token_address"))
        except Exception:  # noqa: BLE001 -- rule 8: not a coin with no price
            continue
        price = (quote or {}).get("price_usd")
        _append({"type": "entry", "at": now.isoformat(), "key": signal["key"],
                 "price_usd": float(price) if isinstance(price, (int, float))
                 else None, **_depth(quote)})
        entries += 1

    written = []
    for signal, horizon in fomo.due_checkpoints(signals, done, now=now):
        try:
            quote = quote_once(signal.get("token_address"))
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

    # The study (qa/fomo.py): hot signals past their first day, and the
    # control group at every hour a hot signal is read. Its own row type, so
    # the memecoin tab above never reads it.
    studied: dict[str, set[str]] = {}
    for row in rows:
        if row.get("type") == "study" and row.get("key"):
            studied.setdefault(row["key"], set()).add(row.get("horizon", "?"))
    controls = [r for r in rows if r.get("type") == "control" and r.get("key")]
    study = [(pair, "hot") for pair in fomo.due_checkpoints(
                 signals, studied, now=now,
                 horizons=fomo.STUDY_HORIZONS_HOURS)]
    study += [(pair, "control") for pair in fomo.due_checkpoints(
                  controls, studied, now=now,
                  horizons=fomo.CONTROL_HORIZONS_HOURS)]
    readings = []
    for (signal, horizon), group in study:
        try:
            quote = quote_once(signal.get("token_address"))
        except Exception as exc:  # noqa: BLE001
            readings.append({"key": signal["key"], "horizon": horizon,
                             "error": str(exc)[:200]})
            continue
        price = (quote or {}).get("price_usd")
        price = float(price) if isinstance(price, (int, float)) else None
        readings.append(_append({
            "type": "study", "group": group, "at": now.isoformat(),
            "key": signal["key"], "horizon": horizon, "price_usd": price,
            "return_pct": fomo.return_since_signal(signal.get("price_usd"),
                                                   price),
            **_depth(quote),
        }))
    return {"checked": len(written), "checkpoints": written,
            "studied": len(readings), "entries": entries}


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


# The three questions the study asks, slowest first: their own label (3x in
# 72 h), and two that answer sooner while the 72-hour windows fill.
READOUTS = ((3.0, 72.0), (2.0, 24.0), (1.5, 6.0))


def reading(rows: list[dict] | None = None, now=None) -> dict:
    """Hot against control at each readout, and their newest claim per chain.
    Reads the diary only -- no call."""
    rows = load() if rows is None else rows
    claims: dict[str, dict] = {}
    for row in rows:
        if row.get("type") == "calibration" and row.get("chain"):
            claims[row["chain"]] = row
    # The trades themselves stay out: this dict is stored in the lab diary
    # every few hours, and a thousand trades a copy is not a reading.
    stops = [{k: v for k, v in fomo.stop_study(
                 rows, stop_pct=s, target_pct=t, now=now).items()
              if k != "trades"} for s, t in STOPS]
    return {"readouts": [fomo.compare(rows, multiple=m, within_hours=h, now=now)
                         for m, h in READOUTS],
            "claims": claims, "stops": stops, "entries": fomo.entries(rows)}


# Stop -10 % alone, and with a +100 % target: the two NEXT.md of 2026-09-21
# reasoned about.
STOPS = ((10.0, None), (10.0, 100.0))


def _signed(value) -> str:
    return "-" if value is None else f"{value:+.1f}%"


def say_stops(said: dict) -> list[str]:
    """One line per stop rule and the caveat once. A reading stored before
    the study existed has no `stops`, and prints nothing here."""
    lines = []
    for out in said.get("stops") or []:
        rule = f"stop -{out['stop_pct']:g}%" + (
            f" / target +{out['target_pct']:g}%"
            if out.get("target_pct") is not None else ", no target")
        cost, exits = out.get("cost") or {}, out.get("exits") or {}
        lines.append(
            f"{rule}: n={out['n']}, net {_signed(out['mean_net_pct'])}/trade "
            f"(median {_signed(out['median_net_pct'])}, without best "
            f"{out.get('top', 5)} {_signed(out['mean_net_without_top_pct'])}),"
            f" win {_pct(out['win_rate'])}; exits {exits.get('stop', 0)} stop"
            f" / {exits.get('target', 0)} target / {exits.get('last', 0)} "
            f"at the last point; {out['dense_before_exit']} with a sub-hour "
            f"point before exit; round trip median "
            f"{_signed(cost.get('median_round_trip_pct'))} at "
            f"${cost.get('clip_usd', 0):,.0f} ({cost.get('assumed', 0)} "
            f"with no radar depth charged the default); "
            f"{(out.get('excluded') or {}).get('pair_changed', 0)} left out "
            f"where their terminal switched pair")
    if said.get("stops"):
        lines.append(said["stops"][0].get("caveat") or fomo.UNMEASURED_FILLS)
    entry = said.get("entries")
    if entry:
        lines.append(
            f"entries: {entry['unpriced_at_signal']} of {entry['signals']} "
            f"signals had no price when they fired; {entry['retried']} quoted "
            f"again, {entry['priced_on_retry']} priced"
            + (f" (median {entry['median_delay_min']:.0f} min later)"
               if entry.get("median_delay_min") is not None else "")
            + " -- a later entry, not used as the signal's")
    return lines


def _pct(value) -> str:
    return "-" if value is None else f"{value * 100:.1f}%"


def say_reading(said: dict) -> list[str]:
    lines = []
    for out in said["readouts"]:
        hot, control = out["hot"], out["control"]
        ci = hot.get("ci")
        lift = out.get("lift")
        lines.append(
            f"{out['multiple']:g}x inside {out['within_hours']:g} h: hot "
            f"{hot['hits']}/{hot['n']} ({_pct(hot['rate'])}"
            + (f", 95% {_pct(ci[0])}-{_pct(ci[1])}" if ci else "")
            + f"), control {control['hits']}/{control['n']} "
              f"({_pct(control['rate'])}), lift "
            + (f"{lift:.1f}x" if lift is not None else "-"))
    for chain, claim in sorted(said["claims"].items()):
        # Their own sufficiency flag travels with the number or the line
        # overstates them. On 2026-09-21 this printed "their claim: hot 11.2%
        # of 171" while the same block carried sufficient false, and that
        # sentence was one step from a filed report about a claim they do not
        # make. What they publish there is a count and an interval.
        enough = claim.get("hot_sufficient")
        lines.append(
            f"their figure ({chain}, {str(claim.get('at'))[:10]}): hot "
            f"{claim.get('hot_hits')}/{claim.get('hot_n')} reached "
            f"{claim.get('target_multiple')}x inside "
            f"{claim.get('horizon_hours')} h"
            + (f", 95% {_pct(claim.get('hot_ci_low'))}-"
               f"{_pct(claim.get('hot_ci_high'))}"
               if claim.get("hot_ci_low") is not None else "")
            + f", base rate {_pct(claim.get('base_rate'))}"
            + ("" if enough else " -- THEY MARK THIS SAMPLE INSUFFICIENT, so "
                                "it is a reading of theirs, not a claim"))
    return lines + say_stops(said)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("capture", help="poll hot signals, track the new ones")
    sub.add_parser("resolve", help="checkpoint whatever crossed a horizon")
    sub.add_parser("depth", help="what each tracked token can be traded in")
    sub.add_parser("report", help="hot against control: does hot predict a pump")

    args = parser.parse_args(argv)
    if args.cmd == "report":
        for line in say_reading(reading()):
            print(line)
        return 0
    return _run({"capture": capture, "resolve": resolve,
                 "depth": depth}[args.cmd])


if __name__ == "__main__":
    raise SystemExit(main())
