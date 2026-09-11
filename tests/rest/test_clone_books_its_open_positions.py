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
of it is committed. The balance endpoint's own summary is "Get clone bot
balance with locked trades breakdown", and its breakdown says nothing is
locked.

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

THE CLAIM IS PRESENCE. It sums the stakes their /activity lists as open and
holds that against the locked figure their /balance reports for the same bot,
a comparison between two of their endpoints. A read that fails on either side
skips that bot rather than counting as zero.
"""

from __future__ import annotations

from qa.marks import Inconclusive, SafetyTier, qa
from qa.measure import Measurement, conclude

MY_CLONES = "/api/v1/cloned-bots/my-clones"
ACTIVITY = "/api/v1/cloned-bots/{id}/activity"
BALANCE = "/api/v1/cloned-bots/{id}/balance"
# Their balance is published to the cent; anything under that is rounding.
CENT = 0.01
MAX_PAGES = 10


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


def open_stake(items) -> float:
    """USDC staked in trades the feed says are still open."""
    total = 0.0
    for item in items:
        if item.get("is_closed") is False:
            total += float(item.get("amount_usdc") or item.get("usdc_amount") or 0)
    return round(total, 6)


@qa(component="rest.agents", tier=SafetyTier.SAFE, surface="rest")
def test_a_bot_counts_the_stakes_it_has_open(rest_trusted):
    """Money in an open position is locked, or the bot's limits are fiction."""
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

    checked, unread, mismatched = 0, [], []
    for bot in bots[:5]:
        items = _activity(rest_trusted, bot["id"])
        balance = rest_trusted.get(BALANCE.format(id=bot["id"]))
        if items is None or balance.status_code != 200:
            unread.append(bot["id"])
            continue
        try:
            locked = float(balance.json().get("locked_in_trades"))
        except (TypeError, ValueError):
            unread.append(bot["id"])
            continue
        checked += 1
        staked = open_stake(items)
        if staked > CENT and abs(locked - staked) > CENT:
            mismatched.append({
                "bot": bot["id"], "open_positions":
                    sum(1 for i in items if i.get("is_closed") is False),
                "open_stake": staked, "locked_in_trades": locked,
                "bot_balance": balance.json().get("bot_balance")})

    if not checked:
        raise Inconclusive(
            f"none of our {len(bots)} paper bot(s) could be read on both "
            f"{ACTIVITY} and {BALANCE} ({unread}), so there was nothing to "
            f"compare -- a failed read is not an empty book")

    conclude(Measurement(
        verdict="failed" if mismatched else "passed",
        reason=(
            "; ".join(
                f"bot {m['bot'][:8]} has {m['open_positions']} open position(s) "
                f"staking {m['open_stake']:.2f} USDC per {ACTIVITY}, while "
                f"{BALANCE} reports locked_in_trades {m['locked_in_trades']:.2f} "
                f"and bot_balance {m['bot_balance']}"
                for m in mismatched)
            + ". The open stakes are counted nowhere, so every limit computed "
              "off the balance -- stop-loss budget, max position -- sees money "
              "the bot has already committed"
            if mismatched else
            f"every one of the {checked} readable bot(s) locks what it has open"),
        left=[m["open_stake"] for m in mismatched],
        right=[m["locked_in_trades"] for m in mismatched],
        population={"bots": len(bots), "checked": checked,
                    "unread": unread, "mismatched": len(mismatched)},
        sources={"open": f"GET {ACTIVITY} (not in openapi)",
                 "locked": f"GET {BALANCE}"},
    ))
