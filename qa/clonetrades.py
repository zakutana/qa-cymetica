"""Pure readings of a paper clone's trade record (2026-10-04).

The operator looked at the laboratory's experiments table -- paper clones up 10 %
to 33 % within 13 to 48 minutes -- and asked whether the bots really earned,
whether their trades can be verified, and whether it is fake or a bug. Every one
of those trades is a 5-minute up/down bet on BTC or ETH at a fixed stake that pays
+100 % or -100 % of the stake, and the arithmetic of every balance holds to the
cent. What does not hold is in here, one function per reading, so that
`tests/meta/test_pipeline_clone_trades.py` can refute each offline and
`tests/rest/test_a_paper_bot_trade_says_what_happened.py` can apply it live.

Nothing here makes a request.
"""

from __future__ import annotations

import re
from datetime import datetime

# A price more than 0.01 % from the reference is not the same moment's price.
# On 2026-10-03, where their exits were taken at the epoch's end, their price
# sat within 0.002 % of Binance spot (BTC within 1.40 USD at 84,889, ETH within
# 0.02 at 2,687), so the tolerance is five times the widest source gap seen.
TOLERANCE = 0.0001
PAUSE_REASONS = frozenset({"take_profit", "stop_loss"})


def _s(iso) -> int | None:
    """Unix seconds of an ISO timestamp (floor), or None."""
    if not isinstance(iso, str) or not iso:
        return None
    try:
        return int(datetime.fromisoformat(iso.replace("Z", "+00:00")).timestamp() // 1)
    except ValueError:
        return None


def _f(x) -> float | None:
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def epoch_bets(items: list) -> list[dict]:
    """The settled 5-minute bets of one activity feed, with what a reading needs.

    A row is read only when it is a closed `wta` trade carrying both prices and
    its epoch's bounds; anything else (arena legs, open bets) is not a bet whose
    settlement can be judged."""
    out = []
    for t in items or []:
        if not isinstance(t, dict) or t.get("trade_type") != "wta" or not t.get("is_closed"):
            continue
        entry, exit_ = _f(t.get("price_at_entry")), _f(t.get("price_at_exit"))
        end, closed = _s(t.get("epoch_end")), _s(t.get("closed_at"))
        if None in (entry, exit_, end, closed) or not entry or not exit_:
            continue
        out.append({
            "id": t.get("id"), "symbol": t.get("symbol"), "side": t.get("side"),
            "entry": entry, "exit": exit_, "is_winner": bool(t.get("is_winner")),
            "profit_usdc": _f(t.get("profit_usdc")), "amount_usdc": _f(t.get("amount_usdc")),
            "exit_reason": t.get("exit_reason"), "resolution_path": t.get("resolution_path"),
            "epoch_id": t.get("epoch_id"), "epoch_start": t.get("epoch_start"),
            "epoch_end": t.get("epoch_end"), "closed_at": t.get("closed_at"),
            "executed_at": t.get("executed_at"),
            "epoch_end_s": end, "closed_s": closed,
        })
    return out


def settlement_reading(bet: dict, ref_end: float | None, ref_closed: float | None,
                       tol: float = TOLERANCE) -> dict | None:
    """One bet against the market's price at its epoch's end.

    `ref_end` is the reference price at `epoch_end` (the last trade of the
    epoch's last second), `ref_closed` the reference price at the second the
    bet was closed. Returns None when the epoch-end reference is missing: a
    bet we could not price is unread, not passed.

    * off_end    -- the exit is not the price at the epoch's end;
    * at_closed  -- ...and it is the price at the moment the bet was closed;
    * due        -- the result the bet's own entry and the epoch-end price give
                    (None when the move is inside the tolerance either way);
    * flipped    -- that result is not the one the record pays.
    """
    if not ref_end:
        return None
    off = (bet["exit"] - ref_end) / ref_end
    at_closed = bool(ref_closed) and abs(bet["exit"] - ref_closed) / ref_closed <= tol
    move = (ref_end - bet["entry"]) / bet["entry"]
    due = None if abs(move) <= tol else ((move > 0) == (bet["side"] == "buy"))
    return {
        "id": bet["id"], "symbol": bet["symbol"], "side": bet["side"], "epoch_id": bet["epoch_id"],
        "epoch_end": bet["epoch_end"], "closed_at": bet["closed_at"],
        "late_s": bet["closed_s"] - bet["epoch_end_s"],
        "entry": bet["entry"], "exit": bet["exit"], "ref_end": ref_end, "ref_closed": ref_closed,
        "off_end_pct": round(100 * off, 4), "off_end": abs(off) > tol,
        "at_closed": bool(abs(off) > tol and at_closed),
        "due": due, "paid_win": bet["is_winner"],
        "flipped": due is not None and due != bet["is_winner"],
        "resolution_path": bet["resolution_path"], "exit_reason": bet["exit_reason"],
    }


def judge_settlement(readings: list[dict]) -> dict:
    """The readings that fail, grouped the way a report states them."""
    off = [r for r in readings if r["off_end"]]
    return {
        "judged": len(readings),
        "off_end": off,
        "at_closed": [r for r in off if r["at_closed"]],
        "flipped": [r for r in readings if r["flipped"]],
        "max_ok_off_pct": max((abs(r["off_end_pct"]) for r in readings if not r["off_end"]), default=None),
    }


def pause_reason_on_full_term(bets: list[dict]) -> list[dict]:
    """Bets labelled as closed by a take-profit or stop-loss that ran to their
    epoch's end. A 5-minute bet that was held to the end of its epoch was not
    exited by a stop: the label is the bot's pause reason written onto it."""
    return [b for b in bets
            if b.get("exit_reason") in PAUSE_REASONS and b["closed_s"] >= b["epoch_end_s"]]


def _indicator_words(species: dict) -> list[str]:
    words = []
    for ind in species.get("primary_indicators") or []:
        name = ind.get("name") if isinstance(ind, dict) else None
        if isinstance(name, str) and name:
            head = re.split(r"[_\s%]", name)[0]
            if len(head) >= 3 and head not in words:
                words.append(head)
    return words


def _decision_flagged(c, species_by_id: dict):
    """(the flag, the species) when the platform answered `differs_from_display` as a boolean
    beside a species in the list; None otherwise."""
    if not (isinstance(c, dict) and isinstance(c.get("live_decision_source"), dict)):
        return None
    flag = c["live_decision_source"].get("differs_from_display")
    sp = species_by_id.get(c.get("source_id"))
    return (flag, sp) if isinstance(flag, bool) and sp else None


def decision_source_unread(clones: list[dict], species_by_id: dict) -> list:
    """Differing clones whose species carries no readable primary_indicators: their description
    cannot be held against them, so they are unread, never clean (deep pass 2026-10-10, B06)."""
    out = []
    for c in clones or []:
        seen = _decision_flagged(c, species_by_id)
        if seen and seen[0] is True and not _indicator_words(seen[1]):
            out.append(c.get("id"))
    return out


def decision_source_reads(clones: list[dict], species_by_id: dict) -> int:
    """How many clones `decision_source_contradictions` could actually judge: the platform
    answered `differs_from_display` as a boolean AND the clone's species is in the list -- and,
    for a clone that differs, the species carries indicators its description can be held to.
    Zero is an unread population, not a clean one."""
    unread = set(decision_source_unread(clones, species_by_id))
    return sum(1 for c in clones or []
               if _decision_flagged(c, species_by_id) and c.get("id") not in unread)


def decision_verdict(found: list, judged: int, unread: list) -> str:
    """The decision-source check's verdict: `failed` on any contradiction; otherwise
    `inconclusive` while a differing clone is unread or nothing was judged -- the clones that
    could carry the defect were not read, so the rest reading clean is no pass (deep pass
    2026-10-11, B06) -- and `passed` only then."""
    if found:
        return "failed"
    if unread or not judged:
        return "inconclusive"
    return "passed"


def decision_source_contradictions(clones: list[dict], species_by_id: dict) -> list[dict]:
    """Clones whose own `live_decision_source` says they decide on another rule
    than the one their species is described by.

    A clone is counted when the platform marks its decision source as differing
    from what is displayed (`differs_from_display` true) AND its species'
    description names one of its own primary indicators -- the description says
    the bot trades on that indicator, the field says the clone does not."""
    found = []
    for c in clones or []:
        lds = c.get("live_decision_source") if isinstance(c, dict) else None
        if not isinstance(lds, dict) or lds.get("differs_from_display") is not True:
            continue
        sp = species_by_id.get(c.get("source_id"))
        if not sp:
            continue
        text = str(sp.get("description") or "").lower()
        # As a word: "ema" inside "systematic", "rsi" inside "persistent" named nothing
        # (deep pass 2026-10-11, B05). A digit may follow ("EMA20").
        named = [w for w in _indicator_words(sp)
                 if re.search(rf"(?<![a-z0-9]){re.escape(w.lower())}(?![a-z])", text)]
        if not named:
            continue
        found.append({
            "clone": c.get("id"), "species": sp.get("name") or c.get("source_name"),
            "description": sp.get("description"), "named": named,
            "indicators": [i.get("name") for i in sp.get("primary_indicators") or [] if isinstance(i, dict)],
            "decides_on": lds.get("label"), "strategy_symbol": lds.get("strategy_symbol"),
        })
    return found
