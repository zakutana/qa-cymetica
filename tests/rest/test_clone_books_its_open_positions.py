"""A paper bot's open positions are money it no longer has.

Measured 2026-09-11 on our paper clone d778102d (a Perceptron Oracle clone,
funded with 1,000 practice USDC and enabled the evening before):

    GET /api/v1/cloned-bots/{id}/activity   six trades --
        two 5-minute WTA shorts, closed, -25.00 each
        four ARENA longs of 100.00 each, is_closed false
    GET /api/v1/cloned-bots/{id}/balance    bot_balance 950.0,
                                            locked_in_trades 0.0,
                                            available 950.0

950 is 1,000 less the 50 lost on the two closed trades. The 400 sitting in
four open positions is not deducted, not locked, and counted nowhere -- the
same bot, read through two of their own endpoints, says 950 is free while 400
of it is committed. Reported as #94.

This is #87's shape again, on the bot's arena lane: #87 was a paper position
opening and the paper balance not moving, and they fixed it for event cards.
It matters for the same reason. The bot's stop-loss and max-position limits
are computed off its balance, so a bot whose open stakes never leave the
balance can commit more than it holds, and a strategy that has spent most of
its capital looks, to every limit guarding it, like one that has spent none.

`/activity` is the endpoint their own bot page renders its trade history
from, and it is not in openapi-public.json -- so this reads an undocumented
route. That is its own small defect and the report says so; it is also the
only place the open positions can be seen.

Their fix, resolving #94 the same morning (ET-24612): the arena lane debited
the balance once at the end of its loop, behind a row lock that timed out, so
the trade rows persisted and the debit was lost. Each leg is now booked with
its trade row -- debit on entry, refund on a failed leg -- and our bot was
backfilled 950 -> 550. The stake leaves the balance instead of being locked
inside it, so locked_in_trades stays 0.

Until 2026-09-11 this check accepted only the lock, open stake equal to
locked_in_trades. That was the fix its author imagined, and it read their
real one as the defect: "counted nowhere" beside a balance that had dropped by
exactly the 400. A stake is counted when it is locked or when it has left the
balance, and a bot can hold some of each, so the check now works out how much
of what is open has left the balance -- what was funded, plus what closed
trades made or lost, less the balance -- adds what is locked, and fails on the
remainder: stake that is open and neither taken out nor locked. Their API
publishes no funded total (`capital` is null on my-clones), so that figure is
ours, the fund transfers clone.py recorded as accepted in state/clones.jsonl.
A bot we hold no transfer record for can pass only by the lock.

The first run of it, 2026-09-11 14:52, found the remainder on a leg placed
after their fix: switched back on at 14:29, the bot opened an ARENA long of
55.00 at 14:30:15, still open, while the balance stayed 550 -- the old four
legs taken out by the backfill, the new one neither taken out nor locked.

THE CLAIM IS PRESENCE: open stake, per their /activity, that their /balance
neither locks nor has taken out. A balance lower than funding, results and
open stakes explain is no verdict either way -- that bot is skipped and named
-- and a read that fails on either side skips that bot rather than counting
as zero.
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

REPO = Path(__file__).resolve().parent.parent.parent
MY_CLONES = "/api/v1/cloned-bots/my-clones"
ACTIVITY = "/api/v1/cloned-bots/{id}/activity"
BALANCE = "/api/v1/cloned-bots/{id}/balance"
# Their balance is published to the cent; anything under that is rounding.
CENT = 0.01
MAX_PAGES = 10


def _clones():
    """scripts/clone.py, whose records say what we moved into each bot."""
    spec = importlib.util.spec_from_file_location(
        "clone_records", REPO / "scripts" / "clone.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _activity(client, instance_id):
    """Every trade their activity feed lists for one bot, or None if unread."""
    items, seen, page = [], set(), 1
    while page <= MAX_PAGES:
        response = client.get(ACTIVITY.format(id=instance_id),
                              params={"page": page})
        if response.status_code != 200:
            return None
        body = response.json()
        batch = body.get("items") if isinstance(body, dict) else None
        if not isinstance(batch, list):
            return None
        fresh = [i for i in batch if isinstance(i, dict) and i.get("id") not in seen]
        if batch and not fresh:
            # The page parameter was ignored and the same page came back. The
            # feed cannot be walked, so what it holds cannot be summed.
            return None
        for item in fresh:
            seen.add(item.get("id"))
            items.append(item)
        if not body.get("has_more"):
            return items
        page += 1
    return None


def _usdc(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def open_stake(items) -> float | None:
    """USDC staked in trades the feed says are still open, or None when one
    of them cannot be read: an open trade with no amount we can read, or a
    trade that is neither open nor closed. Until the deep pass of 2026-09-11
    both read as zero -- a renamed amount field would have turned the 55.00
    leg into "nothing open" and passed #94 (V13, triage 3/3)."""
    total = 0.0
    for item in items:
        if item.get("is_closed") not in (True, False):
            return None
        if item.get("is_closed") is False:
            amount = _usdc(item.get("amount_usdc", item.get("usdc_amount")))
            if amount is None:
                return None
            total += amount
    return round(total, 6)


def realized(items) -> float | None:
    """What the trades the feed lists as closed made or lost, in USDC, or
    None when a closed trade's result cannot be read (it did not make zero)."""
    total = 0.0
    for item in items:
        if item.get("is_closed") is True:
            profit = _usdc(item.get("profit_usdc"))
            if profit is None:
                return None
            total += profit
    return round(total, 6)


def funded(rows, instance_id) -> float | None:
    """Practice USDC we moved into one bot: the fund transfers clone.py
    recorded as accepted. None when we hold no accepted transfer for it."""
    asked = {r.get("id"): r.get("amount") for r in rows
             if r.get("type") == "intent" and r.get("kind") == "fund"
             and r.get("instance_id") == instance_id}
    moved = []
    for row in rows:
        if (row.get("type") == "outcome" and row.get("kind") == "fund"
                and row.get("outcome") == "accepted" and row.get("id") in asked):
            try:
                moved.append(float(asked[row["id"]]))
            except (TypeError, ValueError):
                return None
    return round(sum(moved), 6) if moved else None


def _legs(items) -> str:
    """The open legs, the way the report names them."""
    return ", ".join(
        f"{i.get('trade_type') or '?'} {i.get('symbol') or '?'} "
        f"{float(i.get('amount_usdc') or i.get('usdc_amount') or 0):.2f} "
        f"since {str(i.get('executed_at') or '?')[:19]}"
        for i in items if i.get("is_closed") is False)


@qa(component="rest.agents", tier=SafetyTier.SAFE, surface="rest")
def test_a_bot_counts_the_stakes_it_has_open(rest_trusted):
    """Money in an open position is locked or taken out, or the bot's limits
    are fiction."""
    listed = rest_trusted.get(MY_CLONES, params={"mode": "paper"})
    if listed.status_code != 200 or not isinstance(listed.json(), list):
        raise Inconclusive(
            f"{MY_CLONES} answered HTTP {listed.status_code} or a body that is "
            f"not a list, so there was no bot to read")
    bots = [r for r in listed.json() if isinstance(r, dict) and r.get("id")]
    if not bots:
        raise Inconclusive(
            "no paper clone of ours exists to read; `python scripts/clone.py "
            "clone ...` makes one, and a paper clone is free")

    records = _clones().load()
    checked, unread, unreconciled, mismatched = 0, [], [], []
    ways = {"nothing open": 0, "locked": 0, "counted": 0}
    for bot in bots[:5]:
        items = _activity(rest_trusted, bot["id"])
        balance = rest_trusted.get(BALANCE.format(id=bot["id"]))
        if items is None or balance.status_code != 200:
            unread.append(bot["id"])
            continue
        body = balance.json()
        try:
            locked = float(body.get("locked_in_trades"))
            held = float(body.get("bot_balance"))
        except (AttributeError, TypeError, ValueError):
            unread.append(bot["id"])
            continue
        staked = open_stake(items)
        if staked is None:
            # A trade we cannot read is not a stake of zero (V13).
            unread.append(bot["id"])
            continue
        if staked <= CENT:
            checked += 1
            ways["nothing open"] += 1
            continue
        if abs(locked - staked) <= CENT:
            checked += 1
            ways["locked"] += 1
            continue
        put_in = funded(records, bot["id"])
        if put_in is None:
            unreconciled.append(
                f"{bot['id'][:8]}: {staked:.2f} open and {locked:.2f} locked, "
                f"and no transfer of ours on record to tell how much was "
                f"taken out")
            continue
        made = realized(items)
        if made is None:
            unreconciled.append(
                f"{bot['id'][:8]}: a closed trade's result could not be read, "
                f"so what left the balance cannot be worked out")
            continue
        taken_out = round(put_in + made - held, 6)
        uncounted = round(staked - taken_out - locked, 6)
        if abs(uncounted) <= CENT:
            checked += 1
            ways["counted"] += 1
            continue
        if uncounted < -CENT or taken_out < -CENT:
            unreconciled.append(
                f"{bot['id'][:8]}: bot_balance {held:.2f} is not what "
                f"{put_in:.2f} funded, {made:+.2f} realized and {staked:.2f} "
                f"open can explain")
            continue
        checked += 1
        mismatched.append({
            "bot": bot["id"], "open_positions":
                sum(1 for i in items if i.get("is_closed") is False),
            "open_stake": staked, "locked_in_trades": locked,
            "bot_balance": held, "funded": put_in, "realized": made,
            "taken_out": taken_out, "uncounted": uncounted,
            "legs": _legs(items)})

    if not checked:
        raise Inconclusive(
            f"none of our {len(bots)} paper bot(s) could be judged -- unread "
            f"{unread}, unreconciled {unreconciled}. A failed read is not an "
            f"empty book, and a balance nothing explains is no verdict")

    conclude(Measurement(
        verdict="failed" if mismatched else "passed",
        reason=(
            "; ".join(
                f"bot {m['bot'][:8]} has {m['open_positions']} open position(s) "
                f"staking {m['open_stake']:.2f} USDC per {ACTIVITY} "
                f"({m['legs']}), while {BALANCE} reports bot_balance "
                f"{m['bot_balance']:.2f} and locked_in_trades "
                f"{m['locked_in_trades']:.2f}. Against the {m['funded']:.2f} we "
                f"funded and {m['realized']:+.2f} realized, {m['taken_out']:.2f} "
                f"of the stake has left the balance and "
                f"{m['locked_in_trades']:.2f} is locked, so {m['uncounted']:.2f} "
                f"is neither" for m in mismatched)
            + ". An open stake that is neither locked nor taken out is money "
              "every limit computed off the balance -- stop-loss budget, max "
              "position -- still counts as free"
            if mismatched else
            f"every one of the {checked} judged bot(s) counts what it has open: "
            + ", ".join(f"{n} {way}" for way, n in ways.items() if n)),
        left=[m["open_stake"] for m in mismatched],
        right=[round(m["taken_out"] + m["locked_in_trades"], 6) for m in mismatched],
        population={"bots": len(bots), "checked": checked,
                    "unread": unread, "unreconciled": unreconciled,
                    "mismatched": len(mismatched), **ways},
        sources={"open": f"GET {ACTIVITY} (not in openapi)",
                 "locked": f"GET {BALANCE}",
                 "funded": "accepted fund transfers in state/clones.jsonl "
                           "(scripts/clone.py)"},
    ))
